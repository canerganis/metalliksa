"""Wave B rosenthal-keyhole cluster (LA-2, LA-3, LA-4, LA-5, LA-8). Self-contained; no GPU, no network."""
import contextlib
import io
import math
import sys
import unittest
from unittest import mock

import lpbf_thermal_solver as solver
from fabbro_keyhole import FABBRO_M, FABBRO_N, fabbro_keyhole_depth_m
from lpbf_defect_diagnostics import defect_diagnostics
from lpbf_part_porosity_aggregator import aggregate_part_porosity


def run(*args, **kwargs):
    with mock.patch.dict(sys.modules, {"powder_bed_raytracer": None}), contextlib.redirect_stdout(io.StringIO()):
        return solver.calculate_meltpool_physics(*args, **kwargs)


IN718_285 = ("Inconel 718", 285.0, 960.0, 80.0, 80.0, 40.0, 110.0)
NIST = ("Inconel 718", 285.0, 960.0, 67.0, 23.5, 40.0, 110.0)


class RosenthalExponentLA2(unittest.TestCase):
    P, K, V, A, R = 100.0, 20.0, 1.0, 5e-6, 28e-6

    def test_trailing_axis_exponent_is_one(self):
        # Rosenthal 1946: R + x = 0 on the trailing axis, so only the regularised 1/R prefactor remains.
        for x in (-1e-6, -30e-6, -200e-6):
            T = solver.rosenthal_temperature_C(x, 0.0, 0.0, 0.0, self.P, self.K, self.V, self.A, self.R)
            self.assertAlmostEqual(T, self.P / (2 * math.pi * self.K * math.hypot(x, self.R)), delta=1e-9 * T)

    def test_origin_is_prefactor_only(self):
        T0 = solver.rosenthal_temperature_C(0.0, 0.0, 0.0, 80.0, self.P, self.K, self.V, self.A, self.R)
        self.assertAlmostEqual(T0, 80.0 + self.P / (2 * math.pi * self.K * self.R), places=6)

    def test_unregularised_limit_unchanged(self):
        x, y, z = 40e-6, 15e-6, 10e-6
        R = math.sqrt(x * x + y * y + z * z)
        ref = self.P / (2 * math.pi * self.K * R) * math.exp(-self.V * (R + x) / (2 * self.A))
        T = solver.rosenthal_temperature_C(x, y, z, 0.0, self.P, self.K, self.V, self.A, 0.0)
        self.assertAlmostEqual(T, ref, delta=1e-12 * ref)

    def test_peak_at_beam_centre_and_above_liquidus_when_molten(self):
        tl = solver.THERMOPHYSICAL_DB["Inconel 718"]["liquidus_C"]
        for p, v in ((200, 1200), (150, 1500), (285, 960)):
            r = run("Inconel 718", p, v, 80.0, 80.0, 40.0, 110.0)
            self.assertEqual(r["meltPoolGeometry"]["peakOffset_um"], 0.0)
            if r["meltPoolGeometry"]["extentStatus"] == "computed":
                self.assertGreaterEqual(r["hydrodynamicsAndRecoil"]["peakTemperature_C"], tl)

    def test_in718_150_1500_resolved(self):
        r = run("Inconel 718", 150.0, 1500.0, 80.0, 80.0, 40.0, 110.0)
        g = r["meltPoolGeometry"]
        self.assertEqual(g["extentStatus"], "computed")
        # P1 (2026-10-11): no latent factor on the Rosenthal field, 68.3 -> 75.4 um.
        self.assertAlmostEqual(g["width_um"], 75.4, delta=0.2)
        self.assertGreater(r["solidificationKinetics"]["coolingRate_K_s"], 1.0e5)


class PeakTemperatureLabelD1(unittest.TestCase):
    """Lead decision D1: the reported Rosenthal peak is shown, labelled as a regularised singular-source value."""

    def test_rosenthal_peak_is_labelled_regularised_singular_source(self):
        r = run("Inconel 718", 200.0, 800.0, 80.0, 80.0, 40.0, 110.0)
        h = r["hydrodynamicsAndRecoil"]
        self.assertEqual(h["peakTemperatureBasis"], "regularised-singular-source-value")
        self.assertIn("T(0,0,0)", h["peakTemperatureNote"])
        self.assertIn("not a wall", h["peakTemperatureNote"])
        boiling = solver.THERMOPHYSICAL_DB["Inconel 718"]["boiling_C"]
        self.assertGreater(h["peakTemperature_C"], boiling)  # shown, not hidden
        self.assertTrue(h["peakExceedsVaporization"])
        self.assertEqual(h["surfaceTemperature_C"], round(boiling, 1))
        self.assertTrue(h["surfaceTemperatureBasis"].startswith("saturated at T_vap"))

    def test_et_goldak_peak_basis(self):
        for src in ("eagar-tsai", "goldak"):
            h = run(*NIST, heat_source=src)["hydrodynamicsAndRecoil"]
            self.assertEqual(h["peakTemperatureBasis"], "distributed-source-conduction-centre-value")

    def test_unsaturated_surface_basis(self):
        h = run("Inconel 718", 10.0, 2000.0, 80.0, 80.0, 40.0, 110.0)["hydrodynamicsAndRecoil"]
        self.assertFalse(h["peakExceedsVaporization"])
        self.assertEqual(h["surfaceTemperatureBasis"], "beam-centre field value below T_vap")
        self.assertEqual(h["surfaceTemperature_C"], h["peakTemperature_C"])


class KeyholeScreenLA3(unittest.TestCase):
    def test_no_risk_verdict_mode_indicator_only(self):
        for w, d, mode in ((155.0, 107.8, "keyhole-mode"), (262.2, 296.8, "keyhole-mode"),
                           (100.0, 150.0, "keyhole-mode"), (100.0, 46.0, "conduction-mode"), (100.0, 50.0, "conduction-mode")):
            kh = defect_diagnostics(w, d, 300.0, 50.0, 20.0)["keyhole"]
            self.assertIsNone(kh["risk"], (w, d))
            self.assertEqual(kh["kingModeIndicator"], mode, (w, d))
            self.assertNotIn("stable conduction", kh["reason"])

    def test_provenance_is_king_not_cunningham(self):
        res = defect_diagnostics(155.0, 107.8, 300.0, 50.0, 20.0)
        urls = [p["url"] for p in res["provenance"]]
        self.assertIn("https://doi.org/10.1016/j.jmatprotec.2014.06.005", urls)
        self.assertNotIn("https://doi.org/10.1126/science.aav4687", urls)
        self.assertTrue(any("universal keyhole" in s for s in res["limitations"]))

    def test_aggregate_keeps_null_risk_out_of_porosity(self):
        agg = aggregate_part_porosity([defect_diagnostics(100.0, 150.0, 300.0, 50.0, 20.0)])
        self.assertEqual(agg["mechanismCounts"]["keyhole"], 0)

    def test_aggregate_dimensions_unresolved(self):
        self.assertIsNone(defect_diagnostics(500, 200, 1000, 50, 20, aggregate=True)["keyhole"]["kingModeIndicator"])


class FabbroLA4(unittest.TestCase):
    ARGS = (285.0, 0.96, 80e-6, 11.4, 3.0e-6, 2850.0, 80.0, 0.38, 40.0)

    def test_eq2_closed_form_and_eq3_identity(self):
        P, v, d, k, a, Tv, T0, A, H = self.ARGS
        out = fabbro_keyhole_depth_m(*self.ARGS)
        Pe = v * d / (2 * a)
        e = A * P / (k * (Tv - T0) * (FABBRO_M * Pe + FABBRO_N))
        self.assertAlmostEqual(out["depth_m"], e, delta=1e-15)
        R = out["R0"] / (1.0 + v / out["V0_m_s"])  # eq. 3 is the same expression
        self.assertAlmostEqual(out["aspectRatio_e_over_d"], R, delta=1e-12)

    def test_peclet_fit_range_flag(self):
        self.assertFalse(fabbro_keyhole_depth_m(*self.ARGS)["pecletInFitRange"])  # Pe = 12.8
        slow = list(self.ARGS)
        slow[1] = 0.3
        self.assertTrue(fabbro_keyhole_depth_m(*slow)["pecletInFitRange"])

    def test_solver_labels(self):
        kh = run(*NIST, heat_source="goldak")["keyholeModel"]
        self.assertIn("not Fabbro keyhole A(R)", kh["absorptivityBasis"])
        self.assertTrue(kh["pecletInFitRange"] in (True, False))
        self.assertAlmostEqual(kh["fabbroDepth_um"], 123.9, delta=0.1)  # depth unchanged by LA-4


class LatentHeatFactorLA5(unittest.TestCase):
    def test_et_goldak_get_absorbed_power(self):
        for src in ("eagar-tsai", "goldak"):
            pp = run(*NIST, heat_source=src)["processParameters"]
            self.assertEqual(pp["latentHeatPowerFactor"], 1.0)
            self.assertAlmostEqual(pp["fieldPower_W"], pp["conductionAbsorptivity"] * 285.0, delta=0.2)

    def test_rosenthal_factor_exported(self):
        # P1 (2026-10-11): the uncited 1/(1 + 0.55 St) Rosenthal factor was removed; the field is exactly A P.
        pp = run(*IN718_285)["processParameters"]
        self.assertEqual(pp["latentHeatPowerFactor"], 1.0)
        self.assertGreater(pp["stefanNumber"], 0.0)
        self.assertAlmostEqual(pp["fieldPower_W"], pp["conductionAbsorptivity"] * 285.0, delta=0.2)
        self.assertIn("1/(1+0.55 St)", pp["latentHeatPowerFactorBasis"])

    def test_nist_goldak_width(self):
        self.assertAlmostEqual(run(*NIST, heat_source="goldak")["meltPoolGeometry"]["width_um"], 128.5, delta=0.5)


class IncrementAndRecoilLA8(unittest.TestCase):
    def test_model_id_is_fabbro_for_rosenthal_too(self):
        # P1 (2026-10-11): the Rosenthal increment heuristic-keyhole-increment-v1 was removed; every kernel serves the
        # Fabbro leg with the ramp still labelled uncited.
        kh = run(*IN718_285)["keyholeModel"]
        self.assertEqual(kh["modelId"], "fabbro-keyhole-v1")
        self.assertIn("uncited", kh["basis"])

    def test_recoil_continuous(self):
        dH = 6.4e6 * 0.0587
        lo, hi = (solver.knight_recoil_pressure_kPa(t, 2850.0, dH) for t in (2279.0, 2280.0))
        self.assertAlmostEqual(lo, 2.149, delta=0.005)
        self.assertLess(hi - lo, 0.05)
        temps = [500.0 + 50.0 * i for i in range(48)]
        vals = [solver.knight_recoil_pressure_kPa(t, 2850.0, dH) for t in temps]
        self.assertTrue(all(b >= a for a, b in zip(vals, vals[1:])))
        self.assertAlmostEqual(solver.knight_recoil_pressure_kPa(2850.0, 2850.0, dH), 0.54 * 101.325, delta=1e-9)


if __name__ == "__main__":
    unittest.main()
