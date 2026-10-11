"""P1 planned physics bump (2026-10-11): sourced forms for the served melt-pool depth path.

docs/research/SPEC_p1_sourced_served_physics_2026-10-11.md section 5. SELF-CONTAINED and SYNTHETIC: every material here
is a synthetic property set passed through prop_overrides (not an alloy, not measured), every hand value is computed
in this file from those inputs, and no measured depth enters. Nothing here is validation. Run from python/:
    python -B -m unittest test_lpbf_p1_sourced_depth_path
"""
import contextlib
import io
import json
import math
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import lpbf_thermal_solver as solver  # noqa: E402
from eagar_tsai_solver import EagarTsaiField  # noqa: E402
from fabbro_keyhole import (ENTHALPY_KEYHOLE as FABBRO_RAMP_FULL, ENTHALPY_ONSET as FABBRO_RAMP_START, FABBRO_M,  # noqa: E402
                            FABBRO_N, fabbro_keyhole_depth_m)
from goldak_solver import GoldakField, seed_goldak_axes  # noqa: E402

KERNELS = ("rosenthal", "eagar-tsai", "goldak")
BASE_MATERIAL = "Inconel 718"  # only the key; every property below overrides it
# SYNTHETIC property set (spec section 5, test 1): rho 8000, k 10 / 30, cp 400 / 700, T_liq 1300, T_boil 2800, Lf 2.9e5, A 0.4
SYNTH = {
    "liquidus_C": 1300.0, "solidus_C": 1250.0, "boiling_C": 2800.0, "density_kg_m3": 8000.0,
    "density_liquid_kg_m3": 7400.0, "thermal_conductivity_W_mK": 10.0, "thermal_conductivity_liquid_W_mK": 30.0,
    "specific_heat_J_kgK": 400.0, "specific_heat_liquid_J_kgK": 700.0, "latent_heat_fusion_J_kg": 2.9e5,
    "latent_heat_vap_J_kg": 6.0e6, "absorptivity_IR": 0.4, "absorptivity_Green": 0.6, "M_molar_kg_mol": 0.058,
    "surface_tension_N_m": 1.7, "d_gamma_dT_N_mK": -4.0e-4, "viscosity_Pa_s": 0.005, "thermal_expansion_1_K": 13e-6,
    "youngs_modulus_GPa": 200.0, "poissons_ratio": 0.3, "pdas_A1": 80.0, "sdas_B1": 42.0,
}
T0 = 20.0
LAYER_UM, HATCH_UM = 40.0, 100.0


def _run(P, v_mm_s, d_um, kernel, props=None, **kw):
    with contextlib.redirect_stdout(io.StringIO()):
        return solver.calculate_meltpool_physics(BASE_MATERIAL, P, v_mm_s, d_um, T0, LAYER_UM, HATCH_UM,
                                                 prop_overrides=dict(props or SYNTH), heat_source=kernel, **kw)


def _derived(props=SYNTH):
    rho, k_s, k_l = props["density_kg_m3"], props["thermal_conductivity_W_mK"], props["thermal_conductivity_liquid_W_mK"]
    cp_s, cp_l = props["specific_heat_J_kgK"], props["specific_heat_liquid_J_kgK"]
    k_th, cp = 0.5 * (k_s + k_l), 0.5 * (cp_s + cp_l)
    return {"rho": rho, "k_s": k_s, "cp_s": cp_s, "k_th": k_th, "cp": cp, "alpha_th": k_th / (rho * cp),
            "alpha_s": k_s / (rho * cp_s), "T_liq": props["liquidus_C"], "T_vap": props["boiling_C"],
            "A": props["absorptivity_IR"]}


def _index(P, v, d, props=SYNTH):
    """dH/hs exactly as the solver forms it (flat A, solid k and cp, r = d/2, T0 floored at 50 K)."""
    m = _derived(props)
    r = d / 2.0
    return m["A"] * P / (m["rho"] * m["cp_s"] * max(50.0, m["T_liq"] - T0) * math.sqrt(math.pi * m["alpha_s"] * v * r ** 3))


def _power_for_index(target, v, d, props=SYNTH):
    return target / _index(1.0, v, d, props)


def _ramp(idx):
    if idx < FABBRO_RAMP_START:
        return 0.0
    if idx < FABBRO_RAMP_FULL:
        return (idx - FABBRO_RAMP_START) / (FABBRO_RAMP_FULL - FABBRO_RAMP_START)
    return 1.0


def _field_only_d_iso(P, v, d, kernel, props=SYNTH):
    """Liquidus depth of the conduction field built here from the served field classes at A P (no solver call)."""
    m = _derived(props)
    r = d / 2.0
    P_geom = m["A"] * P
    if kernel == "eagar-tsai":
        f = EagarTsaiField(T0, P_geom, m["k_th"], m["alpha_th"], r).bind_speed(v)
        T_field = f.temperature_C
    elif kernel == "goldak":
        s = seed_goldak_axes(r)
        f = GoldakField(T0, P_geom, m["rho"], m["cp"], m["alpha_th"], s["af_m"], s["ar_m"], s["b_m"], s["c_m"]).bind_speed(v)
        T_field = f.temperature_C
    else:
        r_reg = max(r / math.sqrt(2.0), 8e-6)

        def T_field(x, y, z):
            return solver.rosenthal_temperature_C(x, y, z, T0, P_geom, m["k_th"], v, m["alpha_th"], r_reg)
    idx = _index(P, v, d, props)
    fab = fabbro_keyhole_depth_m(P, v, d, m["k_s"], m["alpha_s"], m["T_vap"], T0, m["A"], idx)
    denom = m["rho"] * m["cp"] * max(50.0, m["T_liq"] - T0) * v
    w_an = math.sqrt(max(1e-12, (8.0 / (math.pi * math.e)) * (P_geom / denom)))
    s_hw = max(d * 1.8, w_an * 1.8, 50e-6)
    s_len = max(d * 3.0, w_an * 4.5, 80e-6)
    s_dep = max(d * 2.2, w_an * 2.0, 40e-6, fab["depth_m"] * 1.35)
    T_field(0.0, 0.0, 0.0)
    x_peak = solver._axial_peak_x(T_field, -s_len * 1.4 * 8.0, s_len)
    ext = solver._liquidus_extent(T_field, m["T_liq"], x_peak, s_len, s_hw, s_dep, d, r, w_an, idx)
    return max(ext["d_iso"], 4e-6), fab["depth_m"], ext["extent_status"]


class FieldPower(unittest.TestCase):
    def test_field_power_is_flat_absorptivity_every_kernel(self):
        v, d = 0.8, 80e-6
        for target in (8.0, 18.0, 40.0):
            P = _power_for_index(target, v, d)
            for k in KERNELS:
                r = _run(P, v * 1e3, d * 1e6, k)
                pp = r["processParameters"]
                self.assertAlmostEqual(pp["normalizedEnthalpy"], target, delta=0.01, msg=(target, k))
                self.assertEqual(pp["effectiveAbsorptivity"], 0.4, (target, k))
                self.assertEqual(pp["conductionAbsorptivity"], 0.4, (target, k))
                self.assertEqual(pp["latentHeatPowerFactor"], 1.0, (target, k))
                self.assertAlmostEqual(pp["fieldPower_W"], round(0.4 * P, 2), delta=0.005, msg=(target, k))
                self.assertIn("multi-reflection ramp", pp["effectiveAbsorptivityBasis"])
                self.assertIn("No kernel represents the measured absorptance rise", pp["effectiveAbsorptivityBasis"])
                self.assertIn("1/(1+0.55 St)", pp["latentHeatPowerFactorBasis"])


class DepthPath(unittest.TestCase):
    # 6 synthetic (P, v, d) points spanning dH/hs about 5 to 45 and Pe about 0.5 to 25 (Pe = v d / (2 alpha_s),
    # alpha_s = 3.125e-6 m2/s): (v m/s, d m, target index)
    POINTS = ((0.1, 40e-6, 5.0), (0.3, 60e-6, 12.0), (0.8, 80e-6, 18.0), (1.2, 100e-6, 27.0), (0.5, 120e-6, 36.0),
              (1.5, 100e-6, 45.0))

    def test_depth_is_max_of_isotherm_and_fabbro_every_kernel(self):
        pes = []
        for v, d, target in self.POINTS:
            P = _power_for_index(target, v, d)
            for k in KERNELS:
                d_iso, e, status = _field_only_d_iso(P, v, d, k)
                r = _run(P, v * 1e3, d * 1e6, k)
                g = r["meltPoolGeometry"]
                self.assertEqual(g["extentStatus"], status, (target, k))
                self.assertAlmostEqual(g["depth_um"], max(d_iso, e) * 1e6, delta=0.05, msg=(target, k))
                self.assertAlmostEqual(g["keyholeVaporCavityDepth_um"], max(0.0, e - d_iso) * 1e6, delta=0.05, msg=(target, k))
                self.assertAlmostEqual(r["keyholeModel"]["fabbroDepth_um"], e * 1e6, delta=0.05, msg=(target, k))
                pes.append(r["keyholeModel"]["peclet"])
        self.assertLess(min(pes), 1.0)
        self.assertGreater(max(pes), 20.0)

    def test_hand_computed_fabbro_leg(self):
        # Spec section 5 test 2 (Amendment 2 values): P 200 W, v 0.8 m/s, d 80 um, T0 20 C, synthetic set.
        alpha_s = 10.0 / (8000.0 * 400.0)                        # 3.125e-6 m2/s
        Pe = 0.8 * 80e-6 / (2.0 * alpha_s)                       # 10.24
        e_unramped = 0.4 * 200.0 / (10.0 * (2800.0 - 20.0) * (FABBRO_M * Pe + FABBRO_N))
        self.assertAlmostEqual(Pe, 10.24, places=12)
        self.assertAlmostEqual(e_unramped * 1e6, 104.36, delta=0.01)
        idx = _index(200.0, 0.8, 80e-6)
        self.assertAlmostEqual(idx, 27.55, delta=0.01)
        ramp = _ramp(idx)
        self.assertAlmostEqual(ramp, 0.837, delta=0.001)
        e_served_hand = e_unramped * ramp * 1e6                    # 87.30 um
        self.assertAlmostEqual(e_served_hand, 87.30, delta=0.05)
        for k in KERNELS:
            r = _run(200.0, 800.0, 80.0, k)
            self.assertAlmostEqual(r["keyholeModel"]["fabbroDepth_um"], e_served_hand, delta=0.5, msg=k)
            self.assertAlmostEqual(r["keyholeModel"]["peclet"], Pe, delta=0.005, msg=k)

    def test_no_increment_constants_remain(self):
        for name in ("KEYHOLE_INCREMENT_FULL_AT", "KEYHOLE_INCREMENT_MODEL_ID", "KEYHOLE_INCREMENT_BASIS"):
            self.assertFalse(hasattr(solver, name), name)
        for k in KERNELS:
            kh = _run(200.0, 800.0, 80.0, k)["keyholeModel"]
            self.assertEqual(kh["modelId"], "fabbro-keyhole-v1", k)
            for needle in ("lower bound", "A(R)", "Fabbro 2020"):
                self.assertIn(needle, kh["basis"], (k, needle))
            self.assertNotIn("uncited screening heuristic: extra depth", kh["basis"], k)
            self.assertIn("not Fabbro keyhole A(R)", kh["absorptivityBasis"])

    def test_fabbro_eq2_against_source_numbers(self):
        # Eq. 2 e = A P / (k (Tv - T0)(m Pe + n)); eq. 3 R = R0 / (1 + V / V0) is the same expression; synthetic input
        # above the ramp (index 45, scale 1).
        P, v, d, k, a, Tv, A = 150.0, 0.6, 70e-6, 12.0, 4.0e-6, 2700.0, 0.35
        out = fabbro_keyhole_depth_m(P, v, d, k, a, Tv, T0, A, 45.0)
        Pe = v * d / (2.0 * a)
        e = A * P / (k * (Tv - T0) * (FABBRO_M * Pe + FABBRO_N))
        self.assertAlmostEqual(out["depth_m"], e, delta=1e-15)
        self.assertAlmostEqual(out["aspectRatio_e_over_d"], out["R0"] / (1.0 + v / out["V0_m_s"]), delta=1e-12)
        self.assertAlmostEqual(out["R0"], A * P / (FABBRO_N * d * k * (Tv - T0)), delta=1e-12)
        self.assertAlmostEqual(out["V0_m_s"], 2.0 * FABBRO_N * a / (FABBRO_M * d), delta=1e-12)
        # pecletInFitRange on a Rosenthal result: Pe 14 (v d = 2 alpha_s 14) False, Pe 5 True (alpha_s 3.125e-6)
        alpha_s = _derived()["alpha_s"]
        for pe, want in ((14.0, False), (5.0, True)):
            v_pe = 2.0 * alpha_s * pe / 80e-6
            r = _run(200.0, v_pe * 1e3, 80.0, "rosenthal")
            self.assertAlmostEqual(r["keyholeModel"]["peclet"], pe, delta=0.01)
            self.assertIs(r["keyholeModel"]["pecletInFitRange"], want, pe)

    def test_kernel_parity_of_keyhole_leg(self):
        legs = {k: _run(200.0, 800.0, 80.0, k)["keyholeModel"] for k in KERNELS}
        self.assertEqual(len({legs[k]["fabbroDepth_um"] for k in KERNELS}), 1, legs)
        self.assertEqual(len({legs[k]["peclet"] for k in KERNELS}), 1)
        self.assertEqual(len({legs[k]["absorptivity"] for k in KERNELS}), 1)


class FallbackAndSymmetry(unittest.TestCase):
    def test_fallback_floor_is_half_width(self):
        for k in KERNELS:
            g = _run(20.0, 2500.0, 200.0, k)["meltPoolGeometry"]
            self.assertEqual(g["extentStatus"], "heuristic-width-fallback", k)
            # depth - cavity is d_iso (the floor); width / 2 is the substituted half width. Both are served rounded to
            # 0.1 um, so the comparison tolerance is the rounding sum (0.05 + 0.025).
            self.assertAlmostEqual(g["depth_um"] - g["keyholeVaporCavityDepth_um"], g["width_um"] / 2.0, delta=0.075, msg=k)
            self.assertIn("Rosenthal symmetry", g["extentNote"], k)
            self.assertIn("not resolved", g["extentNote"], k)

    def test_rosenthal_field_yz_symmetry(self):
        m = _derived()
        for i in range(5):
            for j in range(5):
                x, y = -60e-6 + 25e-6 * i, 5e-6 + 15e-6 * j
                a = solver.rosenthal_temperature_C(x, y, 0.0, T0, 80.0, m["k_th"], 0.8, m["alpha_th"], 20e-6)
                b = solver.rosenthal_temperature_C(x, 0.0, y, T0, 80.0, m["k_th"], 0.8, m["alpha_th"], 20e-6)
                self.assertEqual(a, b, (x, y))


class LatentFree(unittest.TestCase):
    def test_latent_free_geometry(self):
        for k in KERNELS:
            lo = _run(200.0, 800.0, 80.0, k, props={**SYNTH, "latent_heat_fusion_J_kg": 0.0})
            hi = _run(200.0, 800.0, 80.0, k, props={**SYNTH, "latent_heat_fusion_J_kg": 5.0e5})
            for block in ("meltPoolGeometry", "geometricContours", "keyholeModel", "solidificationKinetics",
                          "hydrodynamicsAndRecoil", "thermalSlices", "defectDiagnostics"):
                self.assertEqual(json.dumps(lo[block], sort_keys=True), json.dumps(hi[block], sort_keys=True), (k, block))
            self.assertEqual(lo["processWindowMap"]["grid"], hi["processWindowMap"]["grid"], k)
            pl, ph = dict(lo["processParameters"]), dict(hi["processParameters"])
            self.assertEqual(pl.pop("stefanNumber"), 0.0)
            self.assertGreater(ph.pop("stefanNumber"), 0.0)
            self.assertEqual(pl, ph, k)


# SYNTHETIC grid fixture: regime labels of the 49 process-map cells for the synthetic set at the 200 W / 800 mm/s / 80 um
# operating point (hatch 100 um, layer 40 um); C conduction, T transition, K keyhole, L lack of fusion. Recorded on the P1
# tree from the synthetic property set above (not an alloy).
SYNTHETIC_GRID_REGIME = "TLLLLLLKKTLLLLKKKKLLLKKKKKLLKKKKKKKKKKKKKKKKKKKKK"


class ProcessMapProxy(unittest.TestCase):
    def test_process_map_proxy(self):
        m = _derived()
        r = _run(200.0, 800.0, 80.0, "rosenthal")
        grid = r["processWindowMap"]["grid"]
        self.assertEqual(len(grid), 49)
        d_beam = 80e-6
        labels = {"Optimal Conduction": "C", "Transition": "T", "Keyhole Mode": "K", "Lack of Fusion Zone": "L"}
        got = []
        for c in grid:
            P, v = float(c["power_W"]), float(c["speed_mm_s"]) * 1e-3
            w = math.sqrt((8.0 / (math.pi * math.e)) * (0.4 * P / (m["rho"] * m["cp"] * (m["T_liq"] - T0) * v)) + d_beam ** 2) * 1e6
            self.assertAlmostEqual(c["width_um"], w, delta=0.05, msg=c)
            idx = _index(P, v, d_beam)
            self.assertAlmostEqual(c["normalizedEnthalpy"], idx, delta=0.006, msg=c)
            e = fabbro_keyhole_depth_m(P, v, d_beam, m["k_s"], m["alpha_s"], m["T_vap"], T0, 0.4, idx)["depth_m"] * 1e6
            self.assertAlmostEqual(c["depth_um"], max(0.5 * c["width_um"], e), delta=0.1, msg=c)
            got.append(labels[c["regime"]])
            # P1 follow-on: additive keyhole-index flag, regime string and colour unchanged.
            flag = c["regime"] == "Lack of Fusion Zone" and idx >= solver.ENTHALPY_KEYHOLE
            self.assertEqual(c["keyholeIndexLackOfFusion"], flag, msg=c)
            self.assertEqual("lackOfFusionNote" in c, flag, msg=c)
            if flag:
                self.assertIn("not as lack of fusion", c["lackOfFusionNote"])
                self.assertEqual(c["color"], "#f59e0b")
        self.assertEqual("".join(got), SYNTHETIC_GRID_REGIME)


class ExportedConstants(unittest.TestCase):
    def test_regime_names_exported(self):
        self.assertEqual(solver.ENTHALPY_TRANSITION, 15.0)
        self.assertEqual(solver.ENTHALPY_KEYHOLE, 20.0)
        import lpbf_error_bands as eb
        self.assertEqual(eb.ENTHALPY_TRANSITION, 15.0)
        self.assertEqual(eb.ENTHALPY_KEYHOLE, 20.0)


class StaleCalibrations(unittest.TestCase):
    """A calibration artefact pinned to a foreign implementationHash is refused as stale by the existing checks
    (lpbf_machine_calibration.load_machine_calibration, lpbf_calibration_layer.load_calibration); a re-pin fires them."""

    FOREIGN = "f" * 64

    def test_stale_machine_calibration_refused(self):
        # Synthetic user rows and a synthetic solver (same helpers as test_lpbf_machine_calibration): the artefact is
        # pinned to a foreign implementationHash, exactly what a stored user fit looks like after the P1 re-pin.
        import lpbf_machine_calibration as mc
        import lpbf_machine_calibrated_meltpool as mcm
        import test_lpbf_machine_calibration as T
        from lpbf_simulation import implementation_fingerprint
        live = implementation_fingerprint()
        self.assertNotEqual(live, self.FOREIGN)
        art = mc.build_artefact(T.user_doc(T.UNIFORM, noise=T.NOISE), solver_call=T.fake_solver,
                                implementation_hash=self.FOREIGN, generated_at="2026-10-11T00:00:00+00:00",
                                code_revision="synthetic")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "synthetic-machine" / mcm.ARTEFACT_NAME
            mc.write_artefact(art, path)
            self.assertEqual(mc.load_machine_calibration(path, expected_impl_hash=self.FOREIGN)["machineCalibrationId"],
                             art["machineCalibrationId"])
            with self.assertRaises(mc.MachineCalibrationStale):
                mc.load_machine_calibration(path)
            loaded, info = mc.try_load_machine_calibration(path)
            self.assertIsNone(loaded)
            self.assertTrue(info["stale"])
            self.assertIn("re-fit after the physics bump", info["reason"])
            summaries, verified = mcm.discover(Path(tmp))
            self.assertEqual(verified, {})
            self.assertEqual([s["state"] for s in summaries], ["stale"])
            block = mcm.build_job_block(art["machineCalibrationId"], "316L Stainless Steel",
                                        {"laserPower_W": 200.0, "scanSpeed_mm_s": 800.0, "beamDiameter_um": 80.0}, root=Path(tmp))
            self.assertIs(block["available"], False)
            self.assertIn("stale", json.dumps(block).lower())

    def test_stale_committed_calibration_refused(self):
        import lpbf_calibration_layer as cl
        # The committed v1 artefact against a foreign hash, and against the live fingerprint (stale since d92d1a3a).
        with self.assertRaises(cl.CalibrationStale):
            cl.load_calibration(cl.DEFAULT_PATH, expected_impl_hash=self.FOREIGN)
        with self.assertRaises(cl.CalibrationStale):
            cl.load_calibration(cl.DEFAULT_PATH)
        art = json.loads(Path(cl.DEFAULT_PATH).read_text(encoding="utf-8"))
        self.assertEqual(cl.load_calibration(cl.DEFAULT_PATH, expected_impl_hash=art["implementationHash"])["schema"],
                         art["schema"])


if __name__ == "__main__":
    unittest.main()
