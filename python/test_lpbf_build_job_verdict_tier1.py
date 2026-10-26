"""Tier 1 build-job verdict policy (python/lpbf_build_job_solver.py compose_verdict).

- The balling screen (Eagar-Tsai L/W, lpbf_defect_diagnostics.balling_screen; replaced the frozen
  steady-Rosenthal L/W > 3.8 flag): High (> 5.5) makes a verdict risky, never do-not-print; Moderate
  (> 3.85) is an advisory with no verdict effect; an unresolved Eagar-Tsai extent makes the gate unavailable.
- Recoater / distortion flags are alloy/layer advisories independent of P, v and hatch: reported, never
  verdict-driving, never the dominant gate.
- P7a (2026-10-11): the verdict uses sourced criteria only: do-not-print on the Tang unit criterion, risky when the
  served regime classifier says keyhole mode (cut 20, IN625 13.6), otherwise printable; balling High (316L only), the
  level 30, the Tang margin 0.80, the literature box and downskin are advisories; recoater and distortion are
  not-evaluated (no sourced stress model). Keyhole mode never gives do-not-print (the former 35 edge is gone).
- Tang advisory bump (2026-10-27): the Tang index above 1.0 on modelled geometry is an advisory (lof_tang status
  "advisory"), never blocking and never dominant; a null Tang, width or depth or an unresolved geometry stays
  inconclusive; the keyhole regime and every other gate are unchanged. Since
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

from lpbf_build_job_solver import ADVISORY_GATES, TANG_OVERLAP_ADVISORY, compose_verdict, solve_lpbf_build_job  # noqa: E402
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
# _base_thermal() geometry, Tang index, dH/hs and regime read on the pre-bump tree (Tang advisory bump, 2026-10-27).
PRE_BUMP_BASE = {"width_um": 106.8, "depth_um": 90.9, "tang": 1.071, "dh": 30.58,
                 "regime": "Keyhole Mode (melt-pool D/W > 0.5 screening onset)"}


class ComposeVerdictTier1(unittest.TestCase):
    def test_clean_case_is_printable(self):
        out = compose_verdict(_clean(), "in718")
        self.assertEqual(out["verdict"], "printable")
        self.assertEqual(out["blockingGates"], [])
        self.assertEqual(out["advisories"], [])

    def test_only_balling_high_is_an_advisory_with_screen_reason(self):
        # P7a: balling was an advisory (unsourced screening threshold), never risky. P7b (2026-10-14): the High band is
        # removed; the former High L/W (6.0) is the Moderate advisory and the gate requirement is the 3.848 bound.
        self.assertEqual(HIGH_BALLING["band"], "moderate")
        out = compose_verdict(_clean(ballingScreen=HIGH_BALLING), "in718")
        self.assertEqual(out["verdict"], "printable")
        gates = {g["id"]: g["status"] for g in out["gates"]}
        self.assertEqual(gates["balling"], "advisory")
        self.assertEqual(out["blockingGates"], [])
        self.assertEqual(out["riskGates"], [])
        self.assertEqual(out["dominantGate"], "none")
        line = next(r for r in out["advisories"] if "alling" in r)
        self.assertTrue(line.startswith("Advisory: balling screen Moderate"), line)
        self.assertIn("Eagar–Tsai L/W = 6.00 > 3.85", line)
        self.assertIn("Yadroitsev et al. 2010", line)
        self.assertIn("It does not change the verdict", line)
        gate = next(g for g in out["gates"] if g["id"] == "balling")
        self.assertEqual((gate["measured"], gate["required"]), (6.0, 3.848))
        self.assertIn("no High band since P7b", gate["basis"])
        self.assertFalse(any("High" in a for a in out["advisories"]))

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
        # P7b (2026-10-14): the recall and spot-size disclosure lives in the screen note (served as evidence text), the
        # High advisory line is gone; an older payload carrying band "high" is reported as the Moderate advisory.
        from lpbf_build_job_solver import BALLING_SCREEN_NOTE
        self.assertIn("69/216 balled tracks above the former edge, 3/38 at a 140 um spot", BALLING_SCREEN_NOTE)
        legacy = dict(HIGH_BALLING, band="high")
        out = compose_verdict(_clean(ballingScreen=legacy), "in718")
        self.assertEqual(out["verdict"], "printable")
        self.assertTrue(any(r.startswith("Advisory: balling screen Moderate") for r in out["advisories"]))

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
        self.assertTrue(out["reasons"][0].startswith("No verdict-driving gate is raised"), out["reasons"])
        self.assertIn("Screening result; fusion adequacy is not established.", out["reasons"][0])

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

    def test_lof_fail_is_an_advisory_never_blocking(self):
        # Tang advisory bump (2026-10-27): was do-not-print on lof_tang (P7a).
        out = compose_verdict(_clean(lackOfFusionStatus="Fail"), "in718")
        self.assertEqual(out["verdict"], "printable")
        self.assertEqual(out["blockingGates"], [])
        self.assertIn("lof_tang", out["advisoryGates"])
        self.assertTrue(any(a.startswith(TANG_OVERLAP_ADVISORY) for a in out["advisories"]))


class TangAdvisory(unittest.TestCase):
    """Tang advisory bump (2026-10-27), design section 4: synthetic Tang values on a real resolved IN718 pool."""

    def _tang(self, value, **flags):
        return compose_verdict(_clean(tangIndex_hW_tD=value, lackOfFusionOverlapIndex=value,
                                      lackOfFusionStatus="Fail" if value is not None and value > 1.0 else "Pass",
                                      lackOfFusionMarginAdvisory=value is not None and 0.80 < value <= 1.0, **flags),
                               "in718")

    def _has_tang_advisory(self, out):
        return any(a.startswith(TANG_OVERLAP_ADVISORY) for a in out["advisories"])

    def test_tang_105_conduction_is_printable_with_the_advisory(self):
        out = self._tang(1.05)
        self.assertEqual(out["verdict"], "printable")
        self.assertTrue(self._has_tang_advisory(out))
        self.assertTrue(any(r.startswith(TANG_OVERLAP_ADVISORY) for r in out["reasons"]))
        gate = next(g for g in out["gates"] if g["id"] == "lof_tang")
        self.assertEqual((gate["status"], gate["measured"], gate["required"]), ("advisory", 1.05, 1.0))
        self.assertIn("Harkin 2023 Eq. 5", gate["basis"])
        self.assertIn("modelled geometry", gate["basis"])
        self.assertNotIn("lof_tang", out["blockingGates"])
        self.assertNotEqual(out["dominantGate"], "lof_tang")
        self.assertIn("lof_tang", out["advisoryGates"])
        self.assertIn("fusion adequacy is not established", out["headline"])
        self.assertEqual(out["verdictBasis"], "model-geometry-advisory-keyhole-screen")

    def test_tang_105_in_keyhole_mode_is_risky_with_the_advisory(self):
        out = self._tang(1.05, normalizedEnthalpy=25.0, regime=KEYHOLE_MODE)
        self.assertEqual(out["verdict"], "risky")
        self.assertEqual(out["dominantGate"], "keyhole")
        self.assertEqual(out["riskGates"], ["keyhole"])
        self.assertEqual(out["blockingGates"], [])
        self.assertTrue(self._has_tang_advisory(out))
        # At dH/hs >= 15 the advisory also carries the keyhole depth-bias note.
        from lpbf_build_job_solver import KEYHOLE_DEPTH_BIAS_LOF_NOTE
        self.assertTrue(any(KEYHOLE_DEPTH_BIAS_LOF_NOTE in a for a in out["advisories"]))

    def test_threshold_is_strictly_above_one(self):
        at = self._tang(1.0)
        self.assertFalse(self._has_tang_advisory(at))
        self.assertEqual(next(g for g in at["gates"] if g["id"] == "lof_tang")["status"], "pass")
        above = self._tang(1.001)
        self.assertTrue(self._has_tang_advisory(above))
        self.assertEqual(above["verdict"], "printable")

    def test_margin_080_unchanged(self):
        self.assertFalse(self._tang(0.80)["lackOfFusionMarginAdvisory"])
        out = self._tang(0.81)
        self.assertTrue(out["lackOfFusionMarginAdvisory"])
        self.assertTrue(any(a.startswith("Advisory: Tang margin") for a in out["advisories"]))
        self.assertFalse(self._has_tang_advisory(out))
        # Above 1.0 the overlap advisory is raised instead of the margin advisory, as before.
        self.assertFalse(self._tang(1.05)["lackOfFusionMarginAdvisory"])

    def test_null_tang_width_or_depth_stays_inconclusive(self):
        out = self._tang(None)
        self.assertEqual(out["verdict"], "inconclusive")
        self.assertEqual(next(g for g in out["gates"] if g["id"] == "lof_tang")["status"], "not-evaluated")
        self.assertFalse(self._has_tang_advisory(out))
        for key in ("width_um", "depth_um"):
            th = _clean(tangIndex_hW_tD=1.05, lackOfFusionOverlapIndex=1.05, lackOfFusionStatus="Fail")
            th["meltPoolGeometry"][key] = None
            self.assertEqual(compose_verdict(th, "in718")["verdict"], "inconclusive", key)

    def test_unresolved_geometry_stays_inconclusive(self):
        th = _clean(tangIndex_hW_tD=1.05, lackOfFusionOverlapIndex=1.05, lackOfFusionStatus="Fail")
        th["meltPoolGeometry"]["extentStatus"] = "width-floor-applied"
        out = compose_verdict(th, "in718")
        self.assertEqual(out["verdict"], "inconclusive")
        self.assertEqual(next(g for g in out["gates"] if g["id"] == "lof_tang")["status"], "unavailable")
        self.assertFalse(self._has_tang_advisory(out))

    def test_keyhole_classification_unchanged_at_the_cuts(self):
        # Shared cut 20.0 and the separately calibrated Inconel 625 cut 13.6 (not transferred to IN718).
        from lpbf_thermal_solver import ENTHALPY_KEYHOLE, ENTHALPY_KEYHOLE_IN625, classify_enthalpy_regime
        self.assertEqual((ENTHALPY_KEYHOLE, ENTHALPY_KEYHOLE_IN625), (20.0, 13.6))
        self.assertTrue(classify_enthalpy_regime(20.0, "in718").startswith("Keyhole Mode"))
        self.assertEqual(classify_enthalpy_regime(19.99, "in718"), "Transition Mode")
        self.assertEqual(classify_enthalpy_regime(13.6, "in718"), "Conduction Mode (Stable)")
        self.assertTrue(classify_enthalpy_regime(13.6, "Inconel 625").startswith("Keyhole Mode"))
        self.assertEqual(classify_enthalpy_regime(13.59, "Inconel 625"), "Conduction Mode (Stable)")
        for dh, expect in ((19.99, "printable"), (20.0, "risky")):
            out = self._tang(1.05, normalizedEnthalpy=dh, regime=classify_enthalpy_regime(dh, "in718"))
            self.assertEqual(out["verdict"], expect, dh)
            self.assertTrue(self._has_tang_advisory(out))

    def test_real_pool_numbers_equal_the_pre_bump_values(self):
        # IN718 280/940/80 um, preheat 80 C, layer 40, hatch 100 (the _base_thermal case): the bump changes labels and
        # the verdict only. PRE_BUMP_BASE was read on the pre-bump tree (fc585b4a, fingerprint 13203cac...).
        th = _base_thermal()
        dd = th["defectDiagnostics"]
        self.assertEqual(dd["lackOfFusionStatus"], "Fail")
        self.assertEqual(dd["lackOfFusionRisk"], "Tang overlap advisory: index > 1 using modelled geometry")
        self.assertEqual(PRE_BUMP_BASE, {
            "width_um": th["meltPoolGeometry"]["width_um"], "depth_um": th["meltPoolGeometry"]["depth_um"],
            "tang": dd["tangIndex_hW_tD"], "dh": th["processParameters"]["normalizedEnthalpy"],
            "regime": th["meltPoolGeometry"]["regime"]})


class In718EndToEnd(unittest.TestCase):
    # P7b (2026-10-14): the smaller IN718 pool (authority 0.32, melting-point k / cp; W 106.8 um) fails Tang at a 100 um
    # hatch, so the end-to-end keyhole case uses an 80 um hatch (Tang 0.75, below the 0.80 margin advisory).
    PAYLOAD = {"alloyId": "in718", "laserPower_W": 280, "scanSpeed_mm_s": 940, "hatchSpacing_um": 80,
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
        # The Rosenthal L/W (5.18 after P1, 2026-10-11; ~7.1 before; 3.71 after P7b, 2026-10-14, melting-point k / cp)
        # no longer drives balling; the Eagar-Tsai L/W (5.02 at Wave B, 3.54 after P7b) is Stable.
        ros_lw = float(th["meltPoolGeometry"]["aspectRatio_L_over_W"])
        self.assertAlmostEqual(ros_lw, 3.71, delta=0.01)
        screen = th["defectDiagnostics"]["ballingScreen"]
        self.assertEqual(screen["band"], "stable")
        self.assertAlmostEqual(screen["lengthToWidth"], 3.542, delta=0.01)
        # Balling and recoater/distortion never block; keyhole is the only possible blocking gate here (P7b: the
        # Eagar-Tsai L/W is Stable, so the balling gate passes).
        gates = {g["id"]: g["status"] for g in v["gates"]}
        self.assertEqual(gates["balling"], "pass")
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

    def test_in718_280_940_at_the_former_hatch_100_is_risky_with_the_tang_advisory(self):
        # P7b (2026-10-14): at the pre-P7b 100 um hatch the shallower pool (W 106.8 um) has a Tang index above 1.0.
        # Tang advisory bump (2026-10-27): that is an advisory now (was do-not-print on lof_tang); the keyhole regime
        # makes the case risky.
        res = solve_lpbf_build_job({**self.PAYLOAD, "hatchSpacing_um": 100})
        self.assertTrue(res["success"], res.get("error"))
        v = res["verdict"]
        self.assertEqual(v["verdict"], "risky", v["reasons"])
        self.assertEqual(v["blockingGates"], [])
        self.assertEqual(v["riskGates"], ["keyhole"])
        self.assertIn("lof_tang", v["advisoryGates"])
        self.assertTrue(any(a.startswith(TANG_OVERLAP_ADVISORY) for a in v["advisories"]))

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
