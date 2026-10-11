"""Tier 1 build-job verdict policy (python/lpbf_build_job_solver.py compose_verdict).

- The balling screen (Eagar-Tsai L/W, lpbf_defect_diagnostics.balling_screen; replaced the frozen
  steady-Rosenthal L/W > 3.8 flag): High (> 5.5) makes a verdict risky, never do-not-print; Moderate
  (> 3.85) is an advisory with no verdict effect; an unresolved Eagar-Tsai extent makes the gate unavailable.
- Recoater / distortion flags are alloy/layer advisories independent of P, v and hatch: reported, never
  verdict-driving, never the dominant gate.
- P7a (2026-10-11): the verdict uses sourced criteria only: do-not-print on the Tang unit criterion, risky when the
  served regime classifier says keyhole mode (cut 20, IN625 13.6), otherwise printable; balling High (316L only), the
  level 30, the Tang margin 0.80, the literature box and downskin are advisories; recoater and distortion are
  not-evaluated (no sourced stress model). Keyhole mode never gives do-not-print (the former 35 edge is gone). Since
  the 2026-10-06 tier-2 bump dH uses the flat-plate absorptivity on every machine, so the IN718 280/940 end-to-end
  case (dH/hs 30.58, keyhole mode) is risky everywhere.

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
    # P7a: a clean case is a conduction-regime pool with Tang 0.5 (no margin advisory) and null stress values.
    dd.update(lackOfFusionStatus="Pass", tangIndex_hW_tD=0.5, lackOfFusionOverlapIndex=0.5,
              lackOfFusionMarginAdvisory=False, keyholePorosityRisk="Negligible (legacy screening level)",
              ballingInstabilityRisk="Stable Continuous Track (No Balling)", ballingScreen=STABLE_BALLING,
              recoaterCrashRisk="unavailable: no sourced stress model", distortionIndex=None,
              effectiveResidualStress_MPa=None)
    th["processParameters"]["normalizedEnthalpy"] = 12.0
    th["meltPoolGeometry"]["regime"] = "Conduction Mode (Stable)"
    for k, v in flags.items():
        if k == "normalizedEnthalpy":
            th["processParameters"][k] = v
        elif k == "regime":
            th["meltPoolGeometry"][k] = v
        else:
            dd[k] = v
    return th


KEYHOLE_MODE = "Keyhole Mode (melt-pool D/W > 0.5 screening onset)"


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

    def test_only_balling_high_is_an_advisory_with_screen_reason(self):
        # P7a: balling High is an advisory (unsourced screening threshold), never risky.
        out = compose_verdict(_clean(ballingScreen=HIGH_BALLING), "in718")
        self.assertEqual(out["verdict"], "printable")
        gates = {g["id"]: g["status"] for g in out["gates"]}
        self.assertEqual(gates["balling"], "advisory")
        self.assertEqual(out["blockingGates"], [])
        self.assertEqual(out["riskGates"], [])
        self.assertEqual(out["dominantGate"], "none")
        line = next(r for r in out["advisories"] if "alling" in r)
        self.assertIn("unsourced screening threshold", line)
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
        self.assertEqual(out["unavailableGates"], ["recoater", "distortion", "balling"])  # P7a: stress gates listed too
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
        line = next(r for r in out["advisories"] if r.startswith("Advisory: balling screen High"))
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
        self.assertEqual(compose_verdict(th, "in718")["advisoryGates"], ["balling"])  # P7a: advisory, not risk

    def test_recoater_distortion_are_not_evaluated_and_keep_printable(self):
        # P7a: no sourced stress model; the gates are not-evaluated even when an old payload carries a number.
        out = compose_verdict(_clean(recoaterCrashRisk=HIGH_RECOATER, distortionIndex=7.59), "in718")
        self.assertEqual(out["verdict"], "printable")
        self.assertEqual(out["dominantGate"], "none")
        self.assertIsNone(out["suggestedPatch"])
        gates = {g["id"]: g for g in out["gates"]}
        for gid in ADVISORY_GATES:
            self.assertEqual(gates[gid]["status"], "not-evaluated", gid)
            self.assertIsNone(gates[gid]["required"])
            self.assertIn("no sourced stress model", gates[gid]["reason"])
        self.assertEqual(out["notEvaluatedGates"], list(ADVISORY_GATES))
        self.assertEqual(out["unavailableGates"], list(ADVISORY_GATES))
        self.assertEqual(out["advisoryGates"], [])
        self.assertEqual(out["advisories"], [])
        self.assertEqual(out["blockingGates"], [])
        self.assertEqual(out["riskGates"], [])
        self.assertTrue(out["reasons"][0].startswith("Melt pool passes the Tang overlap criterion"), out["reasons"])

    def test_advisories_do_not_change_any_verdict(self):
        cases = [
            {}, {"ballingScreen": HIGH_BALLING}, {"ballingScreen": MODERATE_BALLING}, {"lackOfFusionStatus": "Warning"},
            {"lackOfFusionStatus": "Fail"}, {"keyholePorosityRisk": "High", "normalizedEnthalpy": 32.0},
            {"keyholePorosityRisk": "High", "normalizedEnthalpy": 40.0, "regime": KEYHOLE_MODE},
        ]
        for flags in cases:
            plain = compose_verdict(_clean(**flags), "in718")
            adv = compose_verdict(_clean(recoaterCrashRisk=HIGH_RECOATER, distortionIndex=7.59, **flags), "in718")
            self.assertEqual(plain["verdict"], adv["verdict"], flags)
            self.assertEqual(plain["dominantGate"], adv["dominantGate"], flags)
            self.assertEqual(plain["suggestedPatch"], adv["suggestedPatch"], flags)

    def test_keyhole_mode_is_risky_never_do_not_print(self):
        # P7a: the served regime classifier drives risky; the level 30 and the former 35 edge drive nothing.
        for dh in (20.0, 35.0, 35.01, 60.0):
            out = compose_verdict(_clean(normalizedEnthalpy=dh, regime=KEYHOLE_MODE), "in718")
            self.assertEqual(out["verdict"], "risky", dh)
            self.assertEqual(out["blockingGates"], [])
            self.assertEqual(out["riskGates"], ["keyhole"])
            self.assertEqual(out["dominantGate"], "keyhole")
        # The legacy level without the keyhole-mode regime label is an advisory only.
        out = compose_verdict(_clean(keyholePorosityRisk="High", normalizedEnthalpy=35.01), "in718")
        self.assertEqual(out["verdict"], "printable")
        self.assertEqual({g["id"]: g["status"] for g in out["gates"]}["keyhole"], "advisory")

    def test_transition_band_is_an_advisory_without_verdict_effect(self):
        # P7a: the 15 to cut band (Zhao 2020) and the legacy level 30 are advisories; the gate's required is the cut.
        out = compose_verdict(_clean(normalizedEnthalpy=17.0, regime="Transition Mode"), "in718")
        self.assertEqual(out["verdict"], "printable")
        gates = {g["id"]: g["status"] for g in out["gates"]}
        self.assertEqual(gates["keyhole"], "advisory")
        self.assertIn("keyhole", out["advisoryGates"])
        self.assertEqual(out["riskGates"], [])
        self.assertEqual(out["blockingGates"], [])
        self.assertEqual(out["dominantGate"], "none")
        adv = next(a for a in out["advisories"] if a.startswith("Advisory: transition band"))
        self.assertIn("ΔH/hₛ = 17.0 in 15 to 20", adv)
        self.assertIn("porosity unresolved", adv)
        gate = next(g for g in out["gates"] if g["id"] == "keyhole")
        self.assertEqual((gate["measured"], gate["required"]), (17.0, 20.0))
        self.assertIn("mode onset, not a porosity boundary", gate["basis"])
        self.assertIn("never do-not-print", gate["note"])
        high = compose_verdict(_clean(keyholePorosityRisk="High", normalizedEnthalpy=32.0), "in718")
        self.assertEqual(high["verdict"], "printable")
        adv = next(a for a in high["advisories"] if a.startswith("Advisory: keyhole porosity legacy level"))
        self.assertIn("unsourced screening threshold, legacy porosity level kept for continuity", adv)

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
        self.assertEqual(gates["recoater"], "not-evaluated")  # P7a: no sourced stress model
        self.assertEqual(gates["distortion"], "not-evaluated")
        self.assertEqual(v["blockingGates"], [])  # P7a: keyhole mode never blocks
        return v, dh

    def _assert_flat_risky(self, v, dh):
        # Tier-2 bump (2026-10-06): dH uses the flat-plate absorptivity on every machine: ~30.6, keyhole mode -> risky.
        self.assertAlmostEqual(dh, 30.58, delta=0.01)
        self.assertEqual(v["verdict"], "risky", (dh, v["reasons"]))
        self.assertEqual(v["riskGates"], ["keyhole"])
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
