"""Build Job suggestedPatch is verified against the served solver, not read off the literature box (G1 audit V15).

The old patch (box minimum power with maximum speed for a keyhole verdict) failed the served Tang overlap screen for
all four locked alloys. A patch is now returned only when the solver, re-run at the suggested point, gives a
printable verdict; otherwise suggestedPatch is None and suggestedPatchNote says why. P7a (2026-10-11): printable
means the Tang unit criterion passes, the geometry is resolved and the point is below the keyhole-mode cut; the
advisories at the suggested point are returned as the third element (suggestedPatchAdvisories).
"""
import copy
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from four_alloy_materials import LITERATURE_PV_WINDOWS  # noqa: E402
from lpbf_build_job_solver import _suggested_patch, solve_lpbf_build_job  # noqa: E402
from lpbf_thermal_solver import calculate_meltpool_physics  # noqa: E402

ALLOYS = ("in718", "ss316l", "ti6al4v", "alsi10mg")
# A keyhole-prone point and a lack-of-fusion point per alloy (both outside the printable region).
KEYHOLE_POINT = {"in718": (520, 400), "ss316l": (500, 300), "ti6al4v": (400, 400), "alsi10mg": (500, 400)}
LOF_POINT = {"in718": (90, 1400), "ss316l": (100, 1500), "ti6al4v": (80, 1500), "alsi10mg": (100, 2000)}


def _job(alloy, power, speed, hatch=100.0, layer=30.0, beam=80.0, **extra):
    return solve_lpbf_build_job({
        "alloyId": alloy, "laserPower_W": power, "scanSpeed_mm_s": speed, "hatchSpacing_um": hatch,
        "layerThickness_um": layer, "beamDiameter_um": beam, "bypassCache": True, **extra})


def _gates(job):
    return {g["id"]: g["status"] for g in job["verdict"]["gates"]}


def _thermal():
    return calculate_meltpool_physics(
        material_name="in718", laser_power_W=280.0, scan_speed_mm_s=940.0, beam_diameter_um=80.0,
        preheat_temp_C=80.0, layer_thickness_um=40.0, hatch_spacing_um=100.0, laser_wavelength="IR_1064nm")


class SuggestedPatchUnit(unittest.TestCase):
    def setUp(self):
        self.th = _thermal()
        self.box = LITERATURE_PV_WINDOWS["in718"]

    def _evaluator(self, passing):
        """Stub solver: real thermal result, with the Tang flag failing unless passing(P, v, h, t, d)."""
        calls = []

        def evaluate(p, v, h, t, d):
            calls.append((p, v, h, t, d))
            th = copy.deepcopy(self.th)
            th["processParameters"].update(laserPower_W=p, scanSpeed_mm_s=v, hatchSpacing_um=h,
                                           layerThickness_um=t, beamDiameter_um=d)
            ok = passing(p, v, h, t, d)
            th["defectDiagnostics"].update(
                lackOfFusionStatus="Pass" if ok else "Fail", tangIndex_hW_tD=0.5 if ok else 1.2,
                lackOfFusionOverlapIndex=0.5 if ok else 1.2, lackOfFusionMarginAdvisory=False,
                keyholePorosityRisk="Negligible", ballingScreen=None,
                ballingInstabilityRisk="Stable Continuous Track (No Balling)", distortionIndex=None)
            # P7a: a conduction-regime stub (the real 280/940 result is keyhole mode and would be rejected).
            th["processParameters"]["normalizedEnthalpy"] = 12.0
            th["meltPoolGeometry"]["regime"] = "Conduction Mode (Stable)"
            return th

        evaluate.calls = calls
        return evaluate

    def test_every_candidate_failing_tang_drops_the_patch_with_a_reason(self):
        ev = self._evaluator(lambda *a: False)
        patch, note, adv = _suggested_patch(self.th, "in718", "keyhole", "risky", ev)
        self.assertIsNone(patch)
        self.assertEqual(adv, [])
        self.assertIn("No parameter patch", note)
        self.assertIn("Tang", note)
        self.assertGreater(len(ev.calls), 1)  # the box corner was tried and rejected, then the grid

    def test_the_first_verified_candidate_is_returned_not_the_box_corner(self):
        corner_p, corner_v = self.box["powerMin_W"], self.box["speedMax_mm_s"]
        ev = self._evaluator(lambda p, v, h, t, d: not (p == corner_p and v == corner_v))
        patch, note, adv = _suggested_patch(self.th, "in718", "keyhole", "risky", ev)
        self.assertIsNotNone(patch)
        self.assertEqual(adv, [])  # the conduction stub inside the box carries no advisory
        self.assertNotEqual((patch["laserPower_W"], patch["scanSpeed_mms"]), (corner_p, corner_v))
        self.assertTrue(self.box["powerMin_W"] <= patch["laserPower_W"] <= self.box["powerMax_W"])
        self.assertTrue(self.box["speedMin_mm_s"] <= patch["scanSpeed_mms"] <= self.box["speedMax_mm_s"])
        self.assertIn("Verified", note)

    def test_no_evaluator_offers_no_patch(self):
        patch, note, adv = _suggested_patch(self.th, "in718", "lof_tang", "do-not-print", None)
        self.assertIsNone(patch)
        self.assertEqual(adv, [])
        self.assertIn("not available", note)

    def test_printable_and_no_gate_cases_have_no_patch(self):
        ev = self._evaluator(lambda *a: True)
        self.assertEqual(_suggested_patch(self.th, "in718", "none", "printable", ev), (None, None, []))
        patch, note, adv = _suggested_patch(self.th, "in718", "none", "inconclusive", ev)
        self.assertIsNone(patch)
        # P7a merge-gate fix: the note names the inconclusive verdict, not a passing gate set.
        self.assertIn("inconclusive", note)
        self.assertIn("no parameter patch is searched", note)
        self.assertNotIn("No sourced gate fails", note)
        self.assertEqual(ev.calls, [])
        _, risky_note, _ = _suggested_patch(self.th, "in718", "none", "risky", ev)
        self.assertIn("No sourced gate fails", risky_note)

    def test_downskin_is_never_dominant_so_no_patch_is_triggered(self):
        # P7a: downskin is an advisory; a verdict with downskin alone is printable and gets no patch.
        from lpbf_build_job_solver import compose_verdict
        th = self._evaluator(lambda *a: True)(280.0, 940.0, 100.0, 40.0, 80.0)
        out = compose_verdict(th, "in718", extras={"downskinOverhang_deg": 60.0, "patchEvaluator": self._evaluator(lambda *a: True)})
        self.assertEqual(out["verdict"], "printable")
        self.assertEqual(out["dominantGate"], "none")
        self.assertIsNone(out["suggestedPatch"])
        self.assertEqual(out["suggestedPatchAdvisories"], [])
        self.assertTrue(any(a.startswith("Advisory: downskin") for a in out["advisories"]))


class SuggestedPatchEndToEnd(unittest.TestCase):
    def _assert_verified(self, alloy, job):
        """Re-run the suggested patch and check it. Returns True when a non-null patch was verified."""
        verdict = job["verdict"]
        self.assertIn("suggestedPatchNote", verdict)
        patch = verdict["suggestedPatch"]
        if patch is None:
            self.assertTrue(verdict["suggestedPatchNote"])
            return False
        again = _job(alloy, patch["laserPower_W"], patch["scanSpeed_mms"], patch["hatch_um"], patch["layer_um"],
                     patch["beamDiameter_um"])
        gates = _gates(again)
        self.assertEqual(gates["lof_tang"], "pass", (alloy, patch))
        self.assertIn(gates["keyhole"], ("pass", "advisory"), (alloy, patch))
        self.assertEqual(again["verdict"]["verdict"], "printable", (alloy, patch))
        # P7a: the advisories of the re-run are the ones reported with the patch.
        self.assertEqual(verdict["suggestedPatchAdvisories"], again["verdict"]["advisories"], (alloy, patch))
        self.assertIn("Advisories at the suggested point:", verdict["suggestedPatchNote"])
        return True

    def test_keyhole_dominant_patches_pass_tang_and_keyhole_for_all_alloys(self):
        verified = 0
        for alloy in ALLOYS:
            p, v = KEYHOLE_POINT[alloy]
            job = _job(alloy, p, v)
            self.assertTrue(job["success"], alloy)
            self.assertIn(job["verdict"]["verdict"], ("risky", "do-not-print"), alloy)
            verified += self._assert_verified(alloy, job)
        # Not vacuous: the e2e check must have re-run at least one real non-null patch across the alloys.
        self.assertGreaterEqual(verified, 1)

    def test_lack_of_fusion_patches_pass_tang_and_keyhole_for_all_alloys(self):
        verified = 0
        for alloy in ALLOYS:
            p, v = LOF_POINT[alloy]
            job = _job(alloy, p, v)
            self.assertTrue(job["success"], alloy)
            verified += self._assert_verified(alloy, job)
        self.assertGreaterEqual(verified, 1)

    def test_a_non_null_verified_patch_exists_across_alloys_and_cases(self):
        verified = 0
        for alloy in ALLOYS:
            for point in (KEYHOLE_POINT[alloy], LOF_POINT[alloy]):
                verified += self._assert_verified(alloy, _job(alloy, *point))
        self.assertGreaterEqual(verified, 1)

    def test_downskin_advisory_with_lof_tang_dominant_says_the_advisory_stays(self):
        # P7a: downskin is an advisory (never fail); the a6f57f66 caveat still says a patch cannot clear the overhang.
        checked = 0
        for alloy in ALLOYS:
            p, v = LOF_POINT[alloy]
            job = _job(alloy, p, v, downskinOverhang_deg=70.0)
            gates = _gates(job)
            self.assertEqual(gates["downskin"], "advisory", alloy)
            if gates["lof_tang"] != "fail":
                continue  # melt-pool extent not resolved for this alloy at this point (gate unavailable)
            checked += 1
            self.assertEqual(job["verdict"]["dominantGate"], "lof_tang", alloy)
            note = job["verdict"]["suggestedPatchNote"]
            self.assertIn("downskin", note, alloy)
            self.assertIn("the downskin advisory stays", note, alloy)
            self.assertIn("no power, speed, hatch or layer change fixes an overhang", note, alloy)
        self.assertGreaterEqual(checked, 1)

    def test_downskin_50_deg_note_says_the_advisory_stays(self):
        p, v = LOF_POINT["in718"]
        job = _job("in718", p, v, downskinOverhang_deg=50.0)
        self.assertEqual(_gates(job)["downskin"], "advisory")
        self.assertIn("the downskin advisory stays", job["verdict"]["suggestedPatchNote"])

    def test_the_old_box_corner_is_never_returned_unless_it_passes(self):
        # The pre-fix keyhole patch: box minimum power, maximum speed, current hatch/layer.
        for alloy in ALLOYS:
            box = LITERATURE_PV_WINDOWS[alloy]
            corner = _job(alloy, box["powerMin_W"], box["speedMax_mm_s"], 100.0, 30.0)
            if _gates(corner)["lof_tang"] == "pass":
                continue
            p, v = KEYHOLE_POINT[alloy]
            patch = _job(alloy, p, v)["verdict"]["suggestedPatch"]
            if patch is not None:
                self.assertNotEqual((patch["laserPower_W"], patch["scanSpeed_mms"], patch["hatch_um"]),
                                    (box["powerMin_W"], box["speedMax_mm_s"], 100), alloy)

    def test_printable_job_has_no_patch_and_no_note(self):
        # P7a: 210/775 (dH/hs 25.3) is keyhole mode, so risky. P7b (2026-10-14): the smaller IN718 pool (authority
        # 0.32, melting-point k / cp) fails Tang at 165/775/90/30 (1.564), so the printable point is 150/700/50/20
        # (dH/hs 18.98, Tang 0.56) and the risky point keeps a 50 um hatch and 20 um layer (Tang 0.379).
        job = _job("in718", 150, 700, 50.0, 20.0)
        self.assertEqual(job["verdict"]["verdict"], "printable")
        self.assertIsNone(job["verdict"]["suggestedPatch"])
        self.assertIsNone(job["verdict"]["suggestedPatchNote"])
        self.assertEqual(job["verdict"]["suggestedPatchAdvisories"], [])
        risky = _job("in718", 210, 775, 50.0, 20.0)
        self.assertEqual(risky["verdict"]["verdict"], "risky")
        self.assertEqual(risky["verdict"]["dominantGate"], "keyhole")


class StaleKeyholeAssumption(unittest.TestCase):
    def test_assumption_states_the_current_cuts_not_king_30(self):
        job = _job("in718", 285, 960, 110.0, 40.0)
        text = " ".join(job["assumptions"])
        self.assertNotIn("Keyhole uses King", text)
        self.assertIn("13.6", text)
        self.assertIn("provisional keyhole-mode cut 20", text)  # P7a wording
        self.assertIn("a mode onset and not a porosity boundary", text)
        self.assertIn("Fabbro keyhole depth leg opens at the same onset (15)", text)
        self.assertIn("not a porosity boundary", text)


if __name__ == "__main__":
    unittest.main()
