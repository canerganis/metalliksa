"""Tier 2 planned-physics bump (2026-10-06): flat-plate absorptivity by default on every machine,
peak-anchored liquidus extent search, alloy/layer/preheat-only distortion labelling, King 2014 DOI.

Self-contained: the GPU modules (powder_bed_raytracer, warp_thermal_solver) are replaced by stubs
in sys.modules, so these tests give the same answer with and without Warp/CUDA installed.
"""

import contextlib
import io
import json
import math
import sys
import types
import unittest

import lpbf_thermal_solver as solver
from four_alloy_materials import LITERATURE_MELT_POOL_CASES
from lpbf_build_job_solver import compose_verdict

GPU_MODULES = ("powder_bed_raytracer", "warp_thermal_solver")


@contextlib.contextmanager
def gpu_modules(mode):
    """mode 'absent': imports fail (no Warp). mode 'stub': importable fakes that return values a
    silent GPU branch would pick up (raytraced A = 0.9, slices of 9999 C) and count their calls; the
    stub's (plane, plane_value) arguments are left in gpu_modules.slice_planes on exit."""
    saved = {name: sys.modules.get(name, KeyError) for name in GPU_MODULES}
    calls = {"raytrace": 0, "slice": 0}
    slice_planes = []
    try:
        if mode == "absent":
            for name in GPU_MODULES:
                sys.modules[name] = None
        else:
            rt = types.ModuleType("powder_bed_raytracer")

            def calculate_powder_bed_absorptivity(beam_radius_um, base_absorptivity):
                calls["raytrace"] += 1
                return {"effective_absorptivity": 0.9}
            rt.calculate_powder_bed_absorptivity = calculate_powder_bed_absorptivity
            ws = types.ModuleType("warp_thermal_solver")

            def compute_rosenthal_slice_warp(span_a, span_b, na, nb, plane, plane_value, *args):
                calls["slice"] += 1
                slice_planes.append((plane, plane_value))
                return [9999.0] * (na * nb)
            ws.compute_rosenthal_slice_warp = compute_rosenthal_slice_warp
            sys.modules["powder_bed_raytracer"] = rt
            sys.modules["warp_thermal_solver"] = ws
        yield calls
    finally:
        gpu_modules.slice_planes = list(slice_planes)
        for name, value in saved.items():
            if value is KeyError:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = value


def run(*args, **kwargs):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        result = solver.calculate_meltpool_physics(*args, **kwargs)
    return result, out.getvalue()


IN718_280 = ("Inconel 718", 280.0, 940.0, 80.0, 80.0, 40.0, 100.0)
IN718_287 = ("Inconel 718", 287.34, 1231.49, 80.0, 80.0, 40.0, 100.0)


class FlatDefaultTest(unittest.TestCase):
    def test_in718_280_940_flat_enthalpy(self):
        with gpu_modules("stub") as calls:
            result, stdout = run(*IN718_280)
        pp = result["processParameters"]
        self.assertEqual(calls, {"raytrace": 0, "slice": 0})
        self.assertEqual(stdout, "")
        self.assertEqual(pp["absorptionModel"], "flat-plate")
        self.assertEqual(pp["thermalSliceBackend"], "cpu")
        # P7b (2026-10-14): the field absorptivity is the IN718 authority 0.32 (Deisenroth 2026); the index reads the
        # convention constant 0.38, so dH/hs 30.58 is unchanged.
        self.assertEqual(pp["conductionAbsorptivity"], 0.32)
        self.assertEqual(pp["indexAbsorptivity"], 0.38)
        self.assertAlmostEqual(pp["normalizedEnthalpy"], 30.58, delta=0.01)
        # P1 (2026-10-11): the multi-reflection ramp is gone, effectiveAbsorptivity is the flat value (was 0.884).
        self.assertAlmostEqual(pp["effectiveAbsorptivity"], 0.32, delta=0.001)
        self.assertTrue(result["defectDiagnostics"]["keyholePorosityRisk"].startswith("High"))

    def test_enthalpy_formula_pi_inside_root(self):
        # King 2014 Eq. (2.6) form in the repo convention (r = d/2, hs = rho cp_s (T_liq - T0)).
        props = solver.THERMOPHYSICAL_DB["Inconel 718"]
        rho, cp_s, k_s = props["density_kg_m3"], props["specific_heat_J_kgK"], props["thermal_conductivity_W_mK"]
        alpha = k_s / (rho * cp_s)
        r = 40e-6
        # P7b: the index reads the convention constant absorptivity_index_IR (0.38), not the authority 0.32.
        expected = props["absorptivity_index_IR"] * 280.0 / (rho * cp_s * (props["liquidus_C"] - 80.0)
                                   * math.sqrt(math.pi * alpha * 0.94 * r ** 3))
        result, _ = run(*IN718_280)
        self.assertAlmostEqual(result["processParameters"]["normalizedEnthalpy"], round(expected, 2), places=6)

    def test_raytrace_opt_in_keeps_enthalpy_flat(self):
        with gpu_modules("stub") as calls:
            result, _ = run(*IN718_280, absorption_model="powder-raytrace")
        pp = result["processParameters"]
        self.assertEqual(calls["raytrace"], 1)
        self.assertEqual(pp["absorptionModel"], "powder-raytrace")
        self.assertEqual(pp["conductionAbsorptivity"], 0.9)
        self.assertAlmostEqual(pp["normalizedEnthalpy"], 30.58, delta=0.01)
        flat_result, _ = run(*IN718_280)
        self.assertEqual([p["normalizedEnthalpy"] for p in result["processWindowMap"]["grid"]],
                         [p["normalizedEnthalpy"] for p in flat_result["processWindowMap"]["grid"]])

    def test_raytrace_opt_in_without_gpu_fails_loudly(self):
        with gpu_modules("absent"):
            with self.assertRaises(ImportError):
                run(*IN718_280, absorption_model="powder-raytrace")
            with self.assertRaises(ImportError):
                run(*IN718_280, thermal_slice_backend="warp")

    def test_invalid_options(self):
        with self.assertRaises(ValueError):
            run(*IN718_280, absorption_model="raytrace-maybe")
        with self.assertRaises(ValueError):
            run(*IN718_280, thermal_slice_backend="cuda")
        with self.assertRaises(ValueError):
            run(*IN718_280, heat_source="eagar-tsai", thermal_slice_backend="warp")

    def test_warp_slice_opt_in(self):
        with gpu_modules("stub") as calls:
            result, _ = run(*IN718_280, thermal_slice_backend="warp")
        self.assertEqual(calls["slice"], 2)
        self.assertEqual(result["processParameters"]["thermalSliceBackend"], "warp")
        self.assertEqual(set(result["thermalSlices"]["xz"]["T_C"]), {9999.0})
        # xz at y = 0; the yz plane sits at the axial peak x_peak, like the CPU sampler.
        planes = gpu_modules.slice_planes
        self.assertEqual(planes[0], (1, 0.0))
        self.assertEqual(planes[1][0], 2)
        self.assertAlmostEqual(planes[1][1] * 1e6, result["meltPoolGeometry"]["peakOffset_um"], delta=0.06)


class HostIndependenceTest(unittest.TestCase):
    """Same result whether the GPU modules are importable (stubbed) or absent, when not requested."""

    def test_identical_with_and_without_gpu_modules(self):
        cases = (
            dict(args=IN718_280),
            dict(args=IN718_287),
            dict(args=("Ti-6Al-4V", 200.0, 900.0, 80.0, 150.0, 30.0, 100.0)),
            dict(args=("316L Stainless Steel", 200.0, 800.0, 70.0, 80.0, 30.0, 100.0)),
            dict(args=("Ti-6Al-4V", 280.0, 1200.0, 70.0, 200.0, 30.0, 120.0), kwargs={"heat_source": "eagar-tsai"}),
            dict(args=("316L Stainless Steel", 370.0, 600.0, 60.0, 25.0, 50.0, 90.0), kwargs={"heat_source": "goldak"}),
        )
        for case in cases:
            kwargs = case.get("kwargs", {})
            with gpu_modules("absent"):
                without, _ = run(*case["args"], **kwargs)
            with gpu_modules("stub") as calls:
                with_gpu, _ = run(*case["args"], **kwargs)
            self.assertEqual(calls, {"raytrace": 0, "slice": 0}, case)
            self.assertEqual(json.dumps(without, sort_keys=True), json.dumps(with_gpu, sort_keys=True), case)

    def test_real_environment_matches_stubbed_absent(self):
        # On a CUDA host this exercises the real Warp import path; elsewhere it is the plain path.
        real, _ = run(*IN718_280)
        with gpu_modules("absent"):
            absent, _ = run(*IN718_280)
        self.assertEqual(json.dumps(real, sort_keys=True), json.dumps(absent, sort_keys=True))


class PeakAnchoredExtentTest(unittest.TestCase):
    def test_in718_287_1231_is_computed(self):
        result, _ = run(*IN718_287)
        g = result["meltPoolGeometry"]
        self.assertEqual(g["extentStatus"], "computed")
        self.assertIsNone(g["extentNote"])
        # Wave B LA-2: with the prefactor-only regularisation the Rosenthal field peaks at the beam centre
        # (x_peak = 0), so the reported T(0,0,0) is the axial maximum and is above liquidus. Tier 2 values
        # were 148.3 / 116.6 / 1191.7 um with x_peak < 0 (exponent damped by r_reg).
        self.assertEqual(g["peakOffset_um"], 0.0)
        # P1 (2026-10-11): flat absorptivity, no latent factor, depth = max(d_iso, Fabbro leg); Wave B values were
        # 158.5 / 123.5 / 1266.3 um.
        # P7b (2026-10-14): authority 0.32 and melting-point k / cp 29.6 / 720 (P1 values were 116.5 / 71.6 / 695.1).
        self.assertAlmostEqual(g["width_um"], 94.9, delta=0.2)
        self.assertAlmostEqual(g["depth_um"], 60.3, delta=0.2)
        self.assertAlmostEqual(g["length_um"], 403.1, delta=0.5)
        # P6 (2026-10-11): IN718 has no sourced vapour temperature, so the peak and the Rosenthal axial maximum are null.
        self.assertIsNone(result["hydrodynamicsAndRecoil"]["peakTemperature_C"])
        self.assertIsNone(g["axialFieldMaximum_C"])
        self.assertNotEqual(compose_verdict(result, "in718")["verdict"], "inconclusive")
        # The distributed sources (Eagar-Tsai, Goldak) still peak behind the beam centre.
        for source in ("eagar-tsai", "goldak"):
            other, _ = run(*IN718_287, heat_source=source)
            self.assertEqual(other["meltPoolGeometry"]["extentStatus"], "computed", source)
            self.assertLess(other["meltPoolGeometry"]["peakOffset_um"], 0.0, source)

    def test_in718_280_940_geometry(self):
        result, _ = run(*IN718_280)
        g = result["meltPoolGeometry"]
        self.assertEqual(g["extentStatus"], "computed")
        # P1 (2026-10-11): 131.3 / 108.0 / 680.6 um (Wave B LA-2: 183.8 / 166.4 / 1306.8; Tier 2: 175.2 / 159.7 / 1250.5).
        # P7b (2026-10-14): authority 0.32 and melting-point k / cp (P1 values 131.3 / 108.0 / 680.6).
        self.assertAlmostEqual(g["width_um"], 106.8, delta=0.2)
        self.assertAlmostEqual(g["depth_um"], 90.9, delta=0.2)
        self.assertAlmostEqual(g["length_um"], 395.9, delta=0.5)

    def test_axial_peak_locator(self):
        def field(x, y, z):
            return 1000.0 - ((x + 30e-6) * 1e6) ** 2 - (y * 1e6) ** 2 - (z * 1e6) ** 2
        self.assertAlmostEqual(solver._axial_peak_x(field, -400e-6, 50e-6) * 1e6, -30.0, delta=1e-3)

        def monotone_front(x, y, z):  # maximum at the scan end: never anchored ahead of x = 0 wrongly
            return 1000.0 - abs(x) * 1e6
        self.assertAlmostEqual(solver._axial_peak_x(monotone_front, -400e-6, 50e-6) * 1e6, 0.0, delta=1e-3)

    def test_unmelted_field_keeps_heuristic_fallback(self):
        # 10 W: after Wave B LA-2 the 20 W case peaks at 1839.9 C, above liquidus, so it no longer tests this.
        result, _ = run("Inconel 718", 10.0, 2000.0, 80.0, 80.0, 40.0, 100.0)
        g = result["meltPoolGeometry"]
        self.assertEqual(g["extentStatus"], "heuristic-width-fallback")
        # P6: the Rosenthal axial maximum is the regularised value and is served null; the field itself stays
        # below liquidus at its axial peak (the extent status above says so).
        self.assertIsNone(result["meltPoolGeometry"]["axialFieldMaximum_C"])

    def test_regularised_peak_is_no_longer_served(self):
        # Until P6 the reported peak was T(0,0,0) of the Rosenthal field, the regularised point-source value
        # T0 + P/(2 pi k r_reg) (21 250.8 C on the G11 IN718 200/800/80 payload after P1). P6 (2026-10-11) serves the
        # loss-free Eagar-Tsai surface maximum only below a sourced vapour temperature; IN718 has none, so the peak,
        # the surface temperature and the Rosenthal axial maximum are null with reasons, and nothing is clipped.
        result, _ = run("Inconel 718", 200.0, 800.0, 80.0, 80.0, 40.0, 110.0)
        h = result["hydrodynamicsAndRecoil"]
        self.assertIsNone(h["peakTemperature_C"])
        self.assertIsNone(h["surfaceTemperature_C"])
        self.assertIsNone(h["knudsenRecoilPressure_kPa"])
        self.assertIsNone(result["meltPoolGeometry"]["axialFieldMaximum_C"])
        self.assertEqual(h["peakTemperatureBasis"], "eagar-tsai-loss-free-surface-maximum")
        self.assertIn("no sourced vapour temperature", h["peakUnavailableReason"])
        self.assertNotEqual(h["surfaceTemperature_C"], solver.THERMOPHYSICAL_DB["Inconel 718"]["boiling_C"])

    def test_cross_sections_anchored_at_axial_peak(self):
        # Whenever the extent is computed, the transverse contour, the hatch-overlap contours and the
        # yz thermal slice must show the melt pool (they are taken at x_peak, not at x = 0).
        cases = (
            dict(args=IN718_287),
            dict(args=IN718_280),
            dict(args=("Inconel 718", 200.0, 800.0, 80.0, 80.0, 40.0, 110.0)),
            dict(args=IN718_287, kwargs={"heat_source": "eagar-tsai"}),
            dict(args=IN718_287, kwargs={"heat_source": "goldak"}),
        )
        t_liq = solver.THERMOPHYSICAL_DB["Inconel 718"]["liquidus_C"]
        for case in cases:
            result, _ = run(*case["args"], **case.get("kwargs", {}))
            self.assertEqual(result["meltPoolGeometry"]["extentStatus"], "computed", case)
            contours = result["geometricContours"]
            self.assertGreater(max(p["z_depth_um"] for p in contours["transverseYZ"]), 0.0, case)
            for track in contours["multiTrackHatchOverlap"]:
                self.assertGreater(max(p["z_depth_um"] for p in track["contour"]), 0.0, case)
            self.assertGreaterEqual(max(result["thermalSlices"]["yz"]["T_C"]), t_liq, case)


class DistortionLabelAndDoiTest(unittest.TestCase):
    def test_recoater_label_not_evaluated(self):
        # P7a (2026-10-11): the index (7.59 here before P7a) is no longer served; the gate is not-evaluated.
        result, _ = run(*IN718_280)
        dd = result["defectDiagnostics"]
        self.assertIsNone(dd["distortionIndex"])
        self.assertIsNone(dd["effectiveResidualStress_MPa"])
        self.assertTrue(dd["recoaterCrashRisk"].startswith("unavailable: no sourced stress model"))
        self.assertIn("unavailable since P7a", dd["distortionIndexBasis"])
        verdict = compose_verdict(result, "in718")
        recoater = next(g for g in verdict["gates"] if g["id"] == "recoater")
        self.assertEqual(recoater["status"], "not-evaluated")

    def test_distortion_independent_of_scan(self):
        # P7a: null for every scan setting (nothing is computed).
        a, _ = run(*IN718_280)
        b, _ = run("Inconel 718", 150.0, 600.0, 80.0, 80.0, 40.0, 120.0)
        self.assertIsNone(a["defectDiagnostics"]["distortionIndex"])
        self.assertEqual(a["defectDiagnostics"]["distortionIndex"], b["defectDiagnostics"]["distortionIndex"])
        self.assertEqual(a["defectDiagnostics"]["recoaterCrashRisk"], b["defectDiagnostics"]["recoaterCrashRisk"])

    def test_king_doi_and_typical_labels(self):
        for case in LITERATURE_MELT_POOL_CASES:
            self.assertNotEqual(case["doi"], "10.1016/j.jmatprotec.2014.04.021")
            self.assertIn("widthDepthBasis", case)
            if case["id"] in ("ss316l-king-window", "in718-eos-like"):
                self.assertEqual(case["doi"], "10.1016/j.jmatprotec.2014.06.005")
                self.assertEqual(case["widthDepthBasis"], "typical-not-published")
                self.assertIn("not a published measurement", case["source"])


if __name__ == "__main__":
    unittest.main()
