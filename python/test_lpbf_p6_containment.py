"""P6 containment bump (2026-10-11, docs/research/SPEC_p6_containment_2026-10-11.md): regression tests.

Self-contained: every served number is checked on a SYNTHETIC property set (prop_overrides) or on analytic
fields; no measured datum is read. The two served alloy identities below are used only to select the sourced
vapour temperature table entry (316L) or its absence (Inconel 718); their authority properties are overridden.

Covers: no clipping (surface temperature equals the served peak or is null, never the authority boiling point),
no constant recoil (null in conduction, transition and keyhole cases; onset status strings), no fallback G
(null with a reason when the served depth comes from the Fabbro keyhole leg or fewer than 3 interface samples;
no floors; no incline multiplier; the one-sided surface derivative), the Eagar peak against an independent
scipy quadrature of the P6 derivation Eq. 2 to 1e-4 relative, and null where T_v is unsourced.
"""
import math
import unittest

from scipy.integrate import quad
from scipy.optimize import minimize_scalar

import lpbf_thermal_solver as solver
import solidification_front as sf
from eagar_tsai_solver import eagar_tsai_surface_maximum

# SYNTHETIC property set (rho 8000, k 10/30, cp 400/700, T_liq 1300 C, T_boil 2800 C authority value, A 0.4).
SYNTH = {
    "liquidus_C": 1300.0, "solidus_C": 1250.0, "boiling_C": 2800.0, "M_molar_kg_mol": 0.056,
    "density_kg_m3": 8000.0, "density_liquid_kg_m3": 7500.0,
    "thermal_conductivity_W_mK": 10.0, "thermal_conductivity_liquid_W_mK": 30.0,
    "specific_heat_J_kgK": 400.0, "specific_heat_liquid_J_kgK": 700.0,
    "latent_heat_fusion_J_kg": 2.9e5, "latent_heat_vap_J_kg": 6.3e6,
    "absorptivity_IR": 0.4, "surface_tension_N_m": 1.7, "d_gamma_dT_N_mK": -4.0e-4,
    "viscosity_Pa_s": 6.0e-3, "thermal_expansion_1_K": 1.6e-5, "youngs_modulus_GPa": 190.0,
    "poissons_ratio": 0.3, "sdas_B1": 40.0,
}
SOURCED = "316L Stainless Steel"   # sourced T_v 3086 K (Khairallah 2016 p.38); properties overridden below
UNSOURCED = "Inconel 718"          # no sourced T_v (lead decision); properties overridden below


def run(material, P, v, d=80.0, T0=80.0, **kw):
    return solver.calculate_meltpool_physics(material, P, v, d, T0, 40.0, 100.0, prop_overrides=SYNTH, **kw)


def _gaussian_field_T(point_m, power_W, absorptivity, speed_m_s, radius_m, k, alpha, ambient_C):
    """P6 derivation Eq. 1 to 2 (the sketch kernel, independent of eagar_tsai_solver): tan(theta) substitution."""
    x, y, z = point_m
    length = max(radius_m, math.sqrt(x * x + y * y + z * z))
    X, Y, Z = x / length, y / length, z / length
    radius2 = (radius_m / length) ** 2
    b = speed_m_s * length / (8.0 * alpha)

    def kernel(theta):
        u2 = math.tan(theta) ** 2
        exponent = -2.0 * ((X + b * u2) ** 2 + Y * Y) / (radius2 + u2)
        if Z:
            exponent -= 2.0 * Z * Z / u2
        return math.exp(exponent) * (1.0 + u2) / (radius2 + u2)

    points = [math.atan(math.sqrt(-X / b))] if X < 0 and b > 0 else None
    integral = quad(kernel, 0.0, math.pi / 2.0, epsabs=1e-12, epsrel=2e-9, points=points, limit=240)[0]
    scale = math.sqrt(2.0) * absorptivity * power_W / (math.pi ** 1.5 * k * length)
    return ambient_C + scale * integral


class EagarPeakAgainstIndependentQuadrature(unittest.TestCase):
    def test_surface_maximum_matches_the_derivation_quadrature_to_1e_4(self):
        # Blend k and alpha of the synthetic set exactly as the solver forms them.
        k = 0.5 * (10.0 + 30.0)
        cp = 0.5 * (400.0 + 700.0)
        alpha = k / (8000.0 * cp)
        for P, v in ((20.0, 1.0), (100.0, 0.8), (300.0, 1.5), (50.0, 0.05)):
            served = eagar_tsai_surface_maximum(80.0, 0.4 * P, k, alpha, 40e-6, v)
            axis = lambda X, P=P, v=v: -_gaussian_field_T((X * 40e-6, 0.0, 0.0), P, 0.4, v, 40e-6, k, alpha, 80.0)
            grid = [-8.0 * i / 256 for i in range(257)]
            best = min(grid, key=axis)
            out = minimize_scalar(axis, bounds=(best - 0.1, min(0.0, best + 0.1)), method="bounded",
                                  options={"xatol": 1e-10})
            independent = -out.fun
            self.assertAlmostEqual(served["T_C"] / independent, 1.0, delta=1e-4, msg=(P, v))
            self.assertAlmostEqual(served["x_m"] / 40e-6, out.x, delta=2e-3, msg=(P, v))
            self.assertLessEqual(served["x_m"], 0.0)
            self.assertGreaterEqual(served["T_C"], served["beamCentre_T_C"])

    def test_stationary_limit_is_analytic(self):
        k, alpha = 20.0, 4.5e-6
        out = eagar_tsai_surface_maximum(80.0, 76.0, k, alpha, 40e-6, 1e-6)
        exact = 80.0 + 76.0 / (math.sqrt(2.0 * math.pi) * k * 40e-6)
        self.assertAlmostEqual(out["T_C"] / exact, 1.0, delta=5e-4)
        self.assertAlmostEqual(out["x_m"], 0.0, delta=1e-7)

    def test_served_peak_is_the_same_maximum_for_every_kernel(self):
        peaks = {}
        for src in ("rosenthal", "eagar-tsai", "goldak"):
            r = run(SOURCED, 20.0, 1500.0, heat_source=src)
            h = r["hydrodynamicsAndRecoil"]
            self.assertEqual(h["peakTemperatureBasis"], "eagar-tsai-loss-free-surface-maximum")
            self.assertEqual(h["peakTemperatureModelId"], "eagar-tsai-v2")
            self.assertIsNotNone(h["peakTemperature_C"], src)
            peaks[src] = (h["peakTemperature_C"], h["peakLocation_x_um"])
            pp = r["processParameters"]
            expected = eagar_tsai_surface_maximum(80.0, pp["fieldPower_W"], pp["effectiveConductivity_W_mK"],
                                                  pp["effectiveConductivity_W_mK"] / (8000.0 * pp["effectiveSpecificHeat_J_kgK"]),
                                                  40e-6, 1.5)
            self.assertAlmostEqual(h["peakTemperature_C"], round(expected["T_C"], 1), delta=0.11, msg=src)
            self.assertLess(h["peakTemperature_C"], h["vaporTemperatureSourced_C"])
        self.assertEqual(len(set(peaks.values())), 1, peaks)


class SourcedVapourTemperature(unittest.TestCase):
    def test_table_matches_the_sources_and_has_no_proxy(self):
        self.assertEqual(solver.SOURCED_VAPOR_TEMPERATURE_K["ti6al4v"]["T_K"], 3560.0)   # Gan 2021 SI Table 1 p.20
        self.assertEqual(solver.SOURCED_VAPOR_TEMPERATURE_K["ss316l"]["T_K"], 3086.0)    # Khairallah 2016 p.38
        self.assertEqual(set(solver.SOURCED_VAPOR_TEMPERATURE_K), {"ti6al4v", "ss316l"})
        for name in ("Inconel 718", "AlSi10Mg", "Inconel 625", "CoCrMo", "Hastelloy X", "Pure Copper (Cu-OF)",
                     "Scalmalloy (Al-Mg-Sc-Zr)", "Unobtainium"):
            self.assertIsNone(solver.sourced_vapor_temperature(name), name)
        self.assertEqual(solver.sourced_vapor_temperature("Ti-6Al-4V ELI")["T_K"], 3560.0)
        self.assertEqual(solver.sourced_vapor_temperature("316L")["T_C"], 3086.0 - 273.15)

    def test_fabbro_onset_lies_3_5_to_4_4_percent_above_tv_for_the_gan_alloys(self):
        # Fabbro 2020 App. A: T_th = T_v / (1 - ln(2 p_amb / ((1 + beta) p0)) / c), c = L_v M / (R T_v), p_amb = p0.
        R = 8.314462618
        for Tv, Lv, M in ((3560.0, 9.255e6, 0.048), (3122.0, 6.336e6, 0.056), (2792.0, 1.053e7, 0.027)):
            c = Lv * M / (R * Tv)
            ratio = 1.0 / (1.0 - math.log(2.0 / 1.2) / c)
            self.assertTrue(1.035 <= ratio <= 1.044, (Tv, ratio))

    def test_null_where_tv_is_unsourced(self):
        for P in (20.0, 200.0):
            h = run(UNSOURCED, P, 1500.0)["hydrodynamicsAndRecoil"]
            self.assertIsNone(h["peakTemperature_C"])
            self.assertIsNone(h["surfaceTemperature_C"])
            self.assertIsNone(h["peakExceedsVaporization"])
            self.assertIsNone(h["vaporTemperatureSourced_K"])
            self.assertIn("no sourced vapour temperature", h["peakUnavailableReason"])
            self.assertIn("no sourced vapour temperature", h["vaporTemperatureUnavailableReason"])
            self.assertIsNone(h["recoilOnsetStatus"])
            self.assertIn("not evaluated", h["recoilOnsetUnavailableReason"])
            self.assertIsNone(h["marangoniNumber"])
            self.assertIn("unavailable", h["marangoniUnavailableReason"])

    def test_served_below_and_null_above_the_sourced_tv(self):
        below = run(SOURCED, 20.0, 1500.0)["hydrodynamicsAndRecoil"]
        self.assertEqual(below["vaporTemperatureSourced_K"], 3086.0)
        self.assertIn("Khairallah", below["vaporTemperatureSource"])
        self.assertIs(below["peakExceedsVaporization"], False)
        self.assertEqual(below["recoilOnsetStatus"], "below Fabbro 2020 App A onset")
        self.assertIsNone(below["peakUnavailableReason"])
        self.assertIsNotNone(below["marangoniNumber"])
        above = run(SOURCED, 200.0, 1500.0)["hydrodynamicsAndRecoil"]
        self.assertIsNone(above["peakTemperature_C"])
        self.assertIs(above["peakExceedsVaporization"], True)
        self.assertEqual(above["recoilOnsetStatus"], "above onset, no wall closure")
        self.assertIn("impossible situation", above["peakUnavailableReason"])
        self.assertIn("p.348-s", above["peakUnavailableReason"])
        self.assertIsNone(above["marangoniNumber"])


class NoClippingNoConstantRecoil(unittest.TestCase):
    def test_surface_equals_the_served_peak_or_is_null_never_the_authority_boiling_point(self):
        for material in (SOURCED, UNSOURCED):
            for P, v in ((20.0, 1500.0), (100.0, 1200.0), (200.0, 800.0), (400.0, 500.0)):
                for src in ("rosenthal", "eagar-tsai", "goldak"):
                    h = run(material, P, v, heat_source=src)["hydrodynamicsAndRecoil"]
                    self.assertEqual(h["surfaceTemperature_C"], h["peakTemperature_C"], (material, P, v, src))
                    self.assertNotEqual(h["surfaceTemperature_C"], SYNTH["boiling_C"])
                    self.assertNotEqual(h["surfaceTemperature_C"], round(SYNTH["boiling_C"], 1))
                    if h["peakTemperature_C"] is not None:
                        self.assertLess(h["peakTemperature_C"], h["vaporTemperatureSourced_C"])
                        self.assertIn("no clipping", h["surfaceTemperatureBasis"])
                    else:
                        self.assertTrue(h["surfaceTemperatureBasis"].startswith("unavailable"))

    def test_recoil_is_null_in_every_regime_and_the_function_is_gone(self):
        self.assertFalse(hasattr(solver, "knight_recoil_pressure_kPa"))
        seen = set()
        for P, v in ((60.0, 1500.0), (120.0, 1000.0), (400.0, 400.0)):
            r = run(SOURCED, P, v)
            dh = r["processParameters"]["normalizedEnthalpy"]
            seen.add(r["meltPoolGeometry"]["regime"].split(" ")[0])
            h = r["hydrodynamicsAndRecoil"]
            self.assertIsNone(h["knudsenRecoilPressure_kPa"], dh)
            self.assertIn("54.72", h["recoilPressureUnavailableReason"])
            self.assertIn(h["recoilOnsetStatus"], ("below Fabbro 2020 App A onset", "above onset, no wall closure"))
            self.assertIn("A10 to A12", h["recoilOnsetBasis"])
            self.assertIsNone(h["powderDenudationWidth_um"])
            self.assertIn("B05", h["powderDenudationUnavailableReason"])
        self.assertEqual(seen, {"Conduction", "Transition", "Keyhole"}, seen)

    def test_marangoni_direction_survives_a_null_number(self):
        r = run(UNSOURCED, 200.0, 800.0, sulfur_ppm=80.0)
        m = r["marangoniModel"]
        self.assertEqual(m["flowDirection"], "inward")
        self.assertGreater(m["dGamma_dT_N_mK"], 0.0)
        self.assertIsNone(m["surfaceVelocity_m_s"])
        self.assertIsNone(m["pecletMarangoni"])
        self.assertIsNotNone(m["marangoniUnavailableReason"])


class NoFallbackGNoFloorsNoIncline(unittest.TestCase):
    def test_keyhole_leg_depth_gives_null_with_reason(self):
        r = run(SOURCED, 400.0, 500.0)
        g = r["meltPoolGeometry"]
        self.assertGreater(g["keyholeVaporCavityDepth_um"], 0.0)
        k = r["solidificationKinetics"]
        self.assertIsNone(k["gradientSource"])
        self.assertIs(k["usedFieldMap"], False)
        self.assertIn("Fabbro keyhole leg", k["unavailableReason"])
        for key in ("thermalGradient_G_K_m", "thermalGradient_G_K_um", "solidificationRate_R_m_s",
                    "solidificationRate_R_mm_s", "coolingRate_K_s", "coolingRate_log10", "g_over_r_ratio",
                    "microstructureMorphology", "primaryDendriteArmSpacing_PDAS_um",
                    "secondaryDendriteArmSpacing_SDAS_um", "phaseTransformation", "thermalGradientTail_G_K_m"):
            self.assertIsNone(k[key], key)
        self.assertNotIn("solidificationCosTheta", k)

    def test_conduction_case_is_the_conduction_field_interface(self):
        r = run(SOURCED, 100.0, 1200.0)
        self.assertEqual(r["meltPoolGeometry"]["keyholeVaporCavityDepth_um"], 0.0)
        k = r["solidificationKinetics"]
        self.assertEqual(k["gradientSource"], "conduction-field-interface")
        self.assertIs(k["usedFieldMap"], True)
        self.assertIsNone(k["unavailableReason"])
        self.assertIn("rear liquidus", k["interface"])
        self.assertGreater(k["thermalGradient_G_K_m"], 0.0)
        self.assertAlmostEqual(k["coolingRate_log10"], math.log10(k["coolingRate_K_s"]), delta=0.01)

    def test_cold_field_is_null_not_tail_length(self):
        out = sf.evaluate_solidification(lambda x, y, z: 0.0, T_liq=1300.0, v_scan=1.0, x_rear=2e-4,
                                         search_depth=2e-4, r_beam=4e-5, sdas_B1=40.0, material_name="x",
                                         t_surface=2000.0, T_sol=1250.0, x_front=8e-5, cos_theta=1.0, pdas_A1=75.0)
        self.assertIsNone(out["thermalGradient_G_K_m"])
        self.assertIsNone(out["gradientSource"])
        self.assertIn("fewer than 3", out["unavailableReason"])
        self.assertNotEqual(out["gradientSource"], "tail-length-fallback")
        r = run(UNSOURCED, 5.0, 3000.0)
        self.assertEqual(r["meltPoolGeometry"]["extentStatus"], "heuristic-width-fallback")
        self.assertIsNone(r["solidificationKinetics"]["thermalGradient_G_K_m"])
        self.assertIn("fewer than 3", r["solidificationKinetics"]["unavailableReason"])

    def test_no_floor_on_r_cooling_or_g_over_r(self):
        # Analytic liquidus plane with a weak +x gradient: n_x = b / sqrt(a^2 + b^2) = 5e-5, so R = v n_x = 5e-5 m/s,
        # below the former 1e-4 m/s floor; cooling = G R = 1e7 * 5e-5 = 500 K/s; G/R = 2e11.
        a, b = 1.0e7, 500.0

        def plane(x, y, z):
            return 1300.0 + 1.0 - a * z + b * x

        out = sf.evaluate_solidification(plane, T_liq=1300.0, v_scan=1.0, x_rear=20e-6, search_depth=8e-6,
                                         r_beam=4.8e-6, sdas_B1=40.0, material_name="x")
        nx = b / math.hypot(a, b)
        self.assertAlmostEqual(out["solidificationRate_R_m_s"], nx, delta=1e-9)
        self.assertLess(out["solidificationRate_R_m_s"], 1.0e-4)
        self.assertAlmostEqual(out["thermalGradient_G_K_m"], math.hypot(a, b), delta=1.0)
        self.assertAlmostEqual(out["coolingRate_K_s"], math.hypot(a, b) * nx, delta=1e-3)
        self.assertAlmostEqual(out["g_over_r_ratio"], math.hypot(a, b) / nx, delta=1e3)

    def test_incline_does_not_multiply_r(self):
        base = run(SOURCED, 100.0, 1200.0)["solidificationKinetics"]
        tilted = run(SOURCED, 100.0, 1200.0, incline_angle_deg=80.0)["solidificationKinetics"]
        self.assertEqual(base, tilted)
        self.assertNotIn("solidificationCosTheta", tilted)
        m = sf.map_solidification_front(lambda x, y, z: 1300.0 + 1.0 - 1.0e7 * z + 1.0e5 * x, 1300.0, 1.0,
                                        20e-6, 8e-6, h_m=5e-7, cos_theta=0.05)
        self.assertIsNotNone(m)
        for s in m["samples"]:
            self.assertAlmostEqual(s["R_m_s"], s["n_x"], delta=1e-12)

    def test_surface_derivative_is_one_sided_not_halved(self):
        def field(x, y, z):
            return 2000.0 - 3.0e6 * z
        gx, gy, gz = sf._grad_T(field, 0.0, 0.0, 0.0, 1e-7)
        self.assertAlmostEqual(gz, -3.0e6, delta=1.0)   # the former form returned -1.5e6
        gx, gy, gz = sf._grad_T(field, 0.0, 0.0, 1e-6, 1e-7)
        self.assertAlmostEqual(gz, -3.0e6, delta=1.0)


class AxialMaximumPolicy(unittest.TestCase):
    def test_rosenthal_axial_maximum_is_null_and_distributed_sources_follow_the_tv_policy(self):
        ros = run(SOURCED, 20.0, 1500.0)["meltPoolGeometry"]
        self.assertIsNone(ros["axialFieldMaximum_C"])
        self.assertIn("regularised", ros["axialFieldMaximumUnavailableReason"])
        for src in ("eagar-tsai", "goldak"):
            low = run(SOURCED, 20.0, 1500.0, heat_source=src)["meltPoolGeometry"]
            self.assertIsNotNone(low["axialFieldMaximum_C"], src)
            self.assertIsNone(low["axialFieldMaximumUnavailableReason"])
            high = run(SOURCED, 300.0, 800.0, heat_source=src)["meltPoolGeometry"]
            self.assertIsNone(high["axialFieldMaximum_C"], src)
            self.assertIn("sourced vapour temperature", high["axialFieldMaximumUnavailableReason"])
            unsourced = run(UNSOURCED, 20.0, 1500.0, heat_source=src)["meltPoolGeometry"]
            self.assertIsNone(unsourced["axialFieldMaximum_C"], src)


class BuildJobNullInputs(unittest.TestCase):
    def test_null_gate_inputs_are_not_evaluated_never_pass_or_fail(self):
        import copy
        from lpbf_build_job_solver import compose_verdict
        th = run(UNSOURCED, 150.0, 1200.0)
        base = compose_verdict(th, "in718")
        self.assertEqual(base["notEvaluatedGates"], [])
        nulled = copy.deepcopy(th)
        nulled["defectDiagnostics"]["tangIndex_hW_tD"] = None
        nulled["defectDiagnostics"]["lackOfFusionOverlapIndex"] = None
        nulled["defectDiagnostics"]["distortionIndex"] = None
        out = compose_verdict(nulled, "in718")
        self.assertEqual(out["verdict"], "inconclusive")
        self.assertIn("not evaluated", out["headline"])
        by_id = {g["id"]: g for g in out["gates"]}
        for gid in ("lof_tang", "lof_wh", "lof_dt", "recoater", "distortion"):
            self.assertEqual(by_id[gid]["status"], "not-evaluated", gid)
            self.assertIsNone(by_id[gid]["measured"])
            self.assertIn("never counted as pass or fail", by_id[gid]["reason"])
        self.assertEqual(sorted(out["notEvaluatedGates"]), ["distortion", "lof_dt", "lof_tang", "lof_wh", "recoater"])
        self.assertEqual(out["blockingGates"], [])
        self.assertNotIn("recoater", out["advisoryGates"])
        self.assertTrue(any("not evaluated" in r for r in out["reasons"]))
        self.assertIsNone(out["lofGeometry"]["tangIndex"])

    def test_kinetics_and_microstructure_carry_the_thermal_reason(self):
        from lpbf_build_job_solver import build_job_kinetics
        from lpbf_solidification_microstructure import project_build_job_microstructure
        th = run(UNSOURCED, 400.0, 500.0)
        self.assertIsNone(th["solidificationKinetics"]["coolingRate_K_s"])
        micro = project_build_job_microstructure(th)
        self.assertEqual(micro["status"], "unavailable")
        self.assertIn("Fabbro keyhole leg", micro["reason"])
        kin = build_job_kinetics("in718", th)
        self.assertEqual(kin["status"], "unavailable")
        self.assertIn("Fabbro keyhole leg", kin["reason"])


if __name__ == "__main__":
    unittest.main()
