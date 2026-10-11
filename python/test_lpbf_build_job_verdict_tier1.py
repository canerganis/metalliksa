"""Tier 1 build-job verdict policy (python/lpbf_build_job_solver.py compose_verdict).

- The balling screen (Eagar-Tsai L/W, lpbf_defect_diagnostics.balling_screen; replaced the frozen
  steady-Rosenthal L/W > 3.8 flag): High (> 5.5) makes a verdict risky, never do-not-print; Moderate
  (> 3.85) is an advisory with no verdict effect; an unresolved Eagar-Tsai extent makes the gate unavailable.
- Recoater / distortion flags are alloy/layer advisories independent of P, v and hatch: reported, never
  verdict-driving, never the dominant gate.
- The keyhole rule (High and dH > 35 -> do-not-print) is unchanged; since the 2026-10-06 tier-2 bump dH uses
  the flat-plate absorptivity on every machine, so the IN718 280/940 end-to-end case is risky everywhere.

Thermal inputs are real calculate_meltpool_physics output (in-repo frozen solver); only the defect
flags under test are overwritten so each case isolates one gate.
"""
import copy
import os
import sys
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from lpbf_build_job_solver import ADVISORY_GATES, compose_verdict, solve_lpbf_build_job  # noqa: E402
from lpbf_defect_diagnostics import balling_screen  # noqa: E402
from lpbf_thermal_solver import calculate_meltpool_physics  # noqa: E402

_BASE = None


def _base_thermal():
    """A real computed-extent IN718 thermal result inside the literature P-v box."""
    global _BASE
    if _BASE is None:
        _BASE = calculate_meltpool_physics(
            material_name="in718", laser_power_W=280.0, scan_speed_mm_s=940.0, beam_diameter_um=80.0,
            preheat_temp_C=80.0, layer_thickness_um=40.0, hatch_spacing_um=100.0,
            laser_wavelength="IR_1064nm")
    return copy.deepcopy(_BASE)


def _clean(**flags):
    """Real thermal result with every verdict-driving flag passing, then `flags` applied."""
    th = _base_thermal()
    assert th["meltPoolGeometry"]["extentStatus"] == "computed", th["meltPoolGeometry"]["extentStatus"]
    dd = th["defectDiagnostics"]
    dd.update(lackOfFusionStatus="Pass", keyholePorosityRisk="Low (Conduction Mode)",
              ballingInstabilityRisk="Stable Continuous Track (No Balling)", ballingScreen=STABLE_BALLING,
              recoaterCrashRisk="Low (Safe Thermal Stress Window)", distortionIndex=0.3)
    th["processParameters"]["normalizedEnthalpy"] = 20.0
    for k, v in flags.items():
        if k == "normalizedEnthalpy":
            th["processParameters"][k] = v
        else:
            dd[k] = v
    return th


# Eagar-Tsai L, W, D (um) chosen to land in each band of the screen.
STABLE_BALLING = balling_screen(300.0, 100.0, 40.0, "computed")
MODERATE_BALLING = balling_screen(450.0, 100.0, 40.0, "computed")
HIGH_BALLING = balling_screen(600.0, 100.0, 40.0, "computed")
UNRESOLVED_BALLING = balling_screen(80.0, 44.0, 10.0, "width-floor-applied")
HIGH_RECOATER = "High (Blade Collision & Part Curl Risk)"


class ComposeVerdictTier1(unittest.TestCase):
    def test_clean_case_is_printable(self):
        out = compose_verdict(_clean(), "in718")
        self.assertEqual(out["verdict"], "printable")
        self.assertEqual(out["blockingGates"], [])
        self.assertEqual(out["advisories"], [])

    def test_only_balling_high_is_risky_with_screen_reason(self):
        out = compose_verdict(_clean(ballingScreen=HIGH_BALLING), "in718")
        self.assertEqual(out["verdict"], "risky")
        gates = {g["id"]: g["status"] for g in out["gates"]}
        self.assertEqual(gates["balling"], "warn")
        self.assertEqual(out["blockingGates"], [])
        self.assertEqual(out["riskGates"], ["balling"])
        self.assertEqual(out["dominantGate"], "balling")
        line = next(r for r in out["reasons"] if "alling" in r)
        self.assertIn("Eagar–Tsai L/W = 6.00 (> 5.5", line)
        self.assertIn("Eagar-Tsai aspect-ratio screen calibrated on Hofmann 2026 316L single tracks", line)
        self.assertIn("10.5281/zenodo.16979848", line)
        self.assertIn("not a demonstrated balling prediction", line)
        gate = next(g for g in out["gates"] if g["id"] == "balling")
        self.assertEqual((gate["measured"], gate["required"]), (6.0, 5.5))

    def test_balling_moderate_is_an_advisory_without_verdict_effect(self):
        out = compose_verdict(_clean(ballingScreen=MODERATE_BALLING), "in718")
        self.assertEqual(out["verdict"], "printable")
        self.assertEqual(out["dominantGate"], "none")
        self.assertEqual(out["advisoryGates"], ["balling"])
        self.assertEqual(out["riskGates"], [])
        (adv,) = out["advisories"]
        self.assertTrue(adv.startswith("Advisory: balling screen Moderate"), adv)
        self.assertIn("Gusarov, Yadroitsev, Bertrand & Smurov 2007", adv)
        self.assertNotIn("Gusarov & Smurov 2010", adv)
        self.assertIn("10.1016/j.apsusc.2007.08.074", adv)
        self.assertIn("Yadroitsev et al. 2010", adv)
        self.assertIn("42/130", adv)
        self.assertIn("does not change the verdict", adv)

    def test_balling_unavailable_when_eagar_tsai_extent_unresolved(self):
        out = compose_verdict(_clean(ballingScreen=UNRESOLVED_BALLING), "in718")
        self.assertEqual(out["verdict"], "printable")
        gate = next(g for g in out["gates"] if g["id"] == "balling")
        self.assertEqual(gate["status"], "unavailable")
        self.assertIn("width-floor-applied", gate["reason"])
        self.assertEqual(out["unavailableGates"], ["balling"])
        self.assertTrue(any(r.startswith("Balling screen unavailable") for r in out["reasons"]))
        # A printable verdict without the screen is not balling-cleared: the headline and flag say so.
        self.assertFalse(out["ballingScreened"])
        self.assertIsNone(out["ballingAbsorptionModel"])
        self.assertTrue(out["headline"].startswith("Printable"), out["headline"])
        self.assertIn("balling not screened", out["headline"])

    def test_screened_verdict_headline_has_no_balling_note(self):
        out = compose_verdict(_clean(ballingScreen=STABLE_BALLING), "in718")
        self.assertTrue(out["ballingScreened"])
        self.assertNotIn("balling not screened", out["headline"])

    def test_high_reason_discloses_recall_and_spot_dependence(self):
        out = compose_verdict(_clean(ballingScreen=HIGH_BALLING), "in718")
        line = next(r for r in out["reasons"] if r.startswith("Balling screen High"))
        self.assertIn("69/216 balled tracks flagged overall, 3/38 at a 140 um spot", line)

    def test_non_flat_plate_absorption_is_disclosed_not_rebanded(self):
        th = _clean(ballingScreen=MODERATE_BALLING)
        th["processParameters"]["absorptionModel"] = "powder-raytrace"
        out = compose_verdict(th, "in718")
        self.assertEqual(out["verdict"], "printable")
        self.assertEqual(out["ballingAbsorptionModel"], "powder-raytrace")
        self.assertEqual(out["advisoryGates"], ["balling"])
        note = next(a for a in out["advisories"] if "absorptivity" in a)
        self.assertIn("calibrated on flat-plate absorptivity", note)
        flat = compose_verdict(_clean(ballingScreen=MODERATE_BALLING), "in718")
        self.assertFalse(any("absorptivity:" in a for a in flat["advisories"]))

    def test_legacy_risk_string_without_screen_still_maps(self):
        th = _clean()
        del th["defectDiagnostics"]["ballingScreen"]
        th["defectDiagnostics"]["ballingInstabilityRisk"] = "High Balling Risk (legacy)"
        self.assertEqual(compose_verdict(th, "in718")["riskGates"], ["balling"])

    def test_only_recoater_distortion_high_keeps_printable(self):
        out = compose_verdict(_clean(recoaterCrashRisk=HIGH_RECOATER, distortionIndex=7.59), "in718")
        self.assertEqual(out["verdict"], "printable")
        self.assertEqual(out["dominantGate"], "none")
        self.assertIsNone(out["suggestedPatch"])
        gates = {g["id"]: g["status"] for g in out["gates"]}
        self.assertEqual(gates["recoater"], "advisory")
        self.assertEqual(gates["distortion"], "advisory")
        self.assertEqual(out["advisoryGates"], list(ADVISORY_GATES))
        self.assertEqual(out["blockingGates"], [])
        self.assertEqual(out["riskGates"], [])
        # Advisories are visible in reasons, last, and say why they do not change the verdict.
        self.assertEqual(out["reasons"][-2:], out["advisories"])
        self.assertTrue(out["reasons"][0].startswith("Conduction-mode melt pool"))
        for a in out["advisories"]:
            self.assertTrue(a.startswith("Advisory:"), a)
            self.assertIn("not on P, v or hatch", a)
            self.assertIn("does not change the verdict", a)

    def test_advisories_do_not_change_any_verdict(self):
        cases = [
            {}, {"ballingScreen": HIGH_BALLING}, {"ballingScreen": MODERATE_BALLING}, {"lackOfFusionStatus": "Warning"},
            {"lackOfFusionStatus": "Fail"}, {"keyholePorosityRisk": "High", "normalizedEnthalpy": 32.0},
            {"keyholePorosityRisk": "High", "normalizedEnthalpy": 40.0},
        ]
        for flags in cases:
            plain = compose_verdict(_clean(**flags), "in718")
            adv = compose_verdict(_clean(recoaterCrashRisk=HIGH_RECOATER, distortionIndex=7.59, **flags), "in718")
            self.assertEqual(plain["verdict"], adv["verdict"], flags)
            self.assertEqual(plain["dominantGate"], adv["dominantGate"], flags)
            self.assertEqual(plain["suggestedPatch"], adv["suggestedPatch"], flags)

    def test_keyhole_rule_unchanged(self):
        self.assertEqual(compose_verdict(_clean(keyholePorosityRisk="High", normalizedEnthalpy=35.0), "in718")["verdict"], "risky")
        out = compose_verdict(_clean(keyholePorosityRisk="High", normalizedEnthalpy=35.01), "in718")
        self.assertEqual(out["verdict"], "do-not-print")
        self.assertEqual(out["blockingGates"], ["keyhole"])
        self.assertEqual(out["dominantGate"], "keyhole")

    def test_keyhole_possible_band_is_an_advisory_without_verdict_effect(self):
        # Keyhole-regime bump: the porosity screen "Possible" band (15 <= dH/hs < 30) is advisory only; the
        # numeric gate (High at 30, do-not-print above 35) is unchanged and the regime threshold (20) is separate.
        possible = ("Possible (15 <= dH/hs < 30; not resolved by this index: Zhao 2020 Ti-6Al-4V pores "
                    "observed at dH/hs 16-28 for v <= 445 mm/s)")
        out = compose_verdict(_clean(keyholePorosityRisk=possible, normalizedEnthalpy=25.0), "in718")
        self.assertEqual(out["verdict"], "printable")
        gates = {g["id"]: g["status"] for g in out["gates"]}
        self.assertEqual(gates["keyhole"], "advisory")
        self.assertIn("keyhole", out["advisoryGates"])
        self.assertEqual(out["riskGates"], [])
        self.assertEqual(out["blockingGates"], [])
        self.assertEqual(out["dominantGate"], "none")
        adv = next(a for a in out["advisories"] if "keyhole porosity possible" in a)
        self.assertTrue(adv.startswith("Advisory:"), adv)
        self.assertIn("ΔH/hₛ 25.0 in 15–30", adv)
        self.assertIn("porosity unresolved", adv)
        gate = next(g for g in out["gates"] if g["id"] == "keyhole")
        self.assertEqual((gate["measured"], gate["required"]), (25.0, 30.0))
        self.assertIn("regime keyhole-mode onset (ΔH/hₛ = 20) is separate", gate["note"])
        high = "High (screening proxy dH/hs >= 30; not a porosity boundary)"
        self.assertEqual(compose_verdict(_clean(keyholePorosityRisk=high, normalizedEnthalpy=30.0), "in718")["verdict"], "risky")
        self.assertEqual(compose_verdict(_clean(keyholePorosityRisk=high, normalizedEnthalpy=35.01), "in718")["verdict"], "do-not-print")
        reason = next(r for r in compose_verdict(_clean(keyholePorosityRisk=high, normalizedEnthalpy=30.0), "in718")["reasons"]
                      if r.startswith("Keyhole porosity screen High"))
        self.assertIn("legacy screening level ≥ 30; porosity unresolved, not a porosity boundary", reason)

    def test_lof_fail_still_do_not_print(self):
        out = compose_verdict(_clean(lackOfFusionStatus="Fail"), "in718")
        self.assertEqual(out["verdict"], "do-not-print")
        self.assertIn("lof_tang", out["blockingGates"])


class In718EndToEnd(unittest.TestCase):
    PAYLOAD = {"alloyId": "in718", "laserPower_W": 280, "scanSpeed_mm_s": 940, "hatchSpacing_um": 100,
               "layerThickness_um": 40, "beamDiameter_um": 80, "preheatTemp_C": 80, "bypassCache": True,
               "enableUq": False, "includeAmbench": False}

    def setUp(self):
        # Give each test a clean import table and restore it after (the tests below install their own
        # powder_bed_raytracer stand-ins; nothing touches the real GPU module).
        patcher = mock.patch.dict(sys.modules)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _check(self, res):
        self.assertTrue(res["success"], res.get("error"))
        v = res["verdict"]
        th = res["thermal"]
        dh = float(th["processParameters"]["normalizedEnthalpy"])
        self.assertEqual(th["meltPoolGeometry"]["extentStatus"], "computed")
        # The Rosenthal L/W (5.18 after P1, 2026-10-11; ~7.1 before) no longer drives balling; the Eagar-Tsai L/W (~5.02, Wave B) is Moderate.
        ros_lw = float(th["meltPoolGeometry"]["aspectRatio_L_over_W"])
        self.assertAlmostEqual(ros_lw, 5.18, delta=0.01)
        self.assertGreater(ros_lw, 3.8)
        screen = th["defectDiagnostics"]["ballingScreen"]
        self.assertEqual(screen["band"], "moderate")
        self.assertAlmostEqual(screen["lengthToWidth"], 5.016, delta=0.01)
        # Balling and recoater/distortion never block; keyhole is the only possible blocking gate here.
        gates = {g["id"]: g["status"] for g in v["gates"]}
        self.assertEqual(gates["balling"], "advisory")
        self.assertNotIn("balling", v["riskGates"])
        self.assertEqual(gates["recoater"], "advisory")
        self.assertEqual(gates["distortion"], "advisory")
        self.assertTrue(set(v["blockingGates"]) <= {"keyhole"}, v["blockingGates"])
        return v, dh

    def _assert_flat_risky(self, v, dh):
        # Tier-2 bump (2026-10-06): dH uses the flat-plate absorptivity on every machine: ~30.6 -> risky.
        self.assertAlmostEqual(dh, 30.58, delta=0.01)
        self.assertEqual(v["verdict"], "risky", (dh, v["reasons"]))
        self.assertEqual(v["blockingGates"], [])

    def test_in718_280_940_keyhole_warns_but_does_not_block(self):
        v, dh = self._check(solve_lpbf_build_job(dict(self.PAYLOAD)))
        self._assert_flat_risky(v, dh)

    def test_in718_280_940_without_ray_tracer_is_risky(self):
        sys.modules["powder_bed_raytracer"] = None  # GPU module not importable
        v, dh = self._check(solve_lpbf_build_job(dict(self.PAYLOAD)))
        self._assert_flat_risky(v, dh)

    def test_in718_280_940_importable_ray_tracer_is_not_used_by_default(self):
        # Before the tier-2 bump an importable tracer (0.588 for IN718 / 80 um) silently raised dH to ~47.3
        # (do-not-print on CUDA hosts only). It is now an explicit opt-in that the build job does not request.
        import types
        stub = types.ModuleType("powder_bed_raytracer")
        stub.calculate_powder_bed_absorptivity = mock.Mock(return_value={"effective_absorptivity": 0.588})
        sys.modules["powder_bed_raytracer"] = stub
        v, dh = self._check(solve_lpbf_build_job(dict(self.PAYLOAD)))
        stub.calculate_powder_bed_absorptivity.assert_not_called()
        self._assert_flat_risky(v, dh)

class KeyholeDepthBiasLofNote(unittest.TestCase):
    def test_note_text_names_the_unmodelled_absorptance_and_the_cut(self):
        from lpbf_build_job_solver import KEYHOLE_DEPTH_BIAS_LOF_NOTE
        from lpbf_thermal_solver import ENTHALPY_TRANSITION
        self.assertIn("biased low", KEYHOLE_DEPTH_BIAS_LOF_NOTE)
        self.assertIn("A(R)", KEYHOLE_DEPTH_BIAS_LOF_NOTE)
        self.assertIn(f"{ENTHALPY_TRANSITION:g}", KEYHOLE_DEPTH_BIAS_LOF_NOTE)


if __name__ == "__main__":
    unittest.main()
