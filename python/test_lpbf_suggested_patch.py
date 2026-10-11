"""Build Job suggestedPatch is verified against the served solver, not read off the literature box (G1 audit V15).

The old patch (box minimum power with maximum speed for a keyhole verdict) failed the served Tang overlap screen for
all four locked alloys. A patch is now returned only when the solver, re-run at the suggested point, gives a
printable verdict; otherwise suggestedPatch is None and suggestedPatchNote says why.
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
            th["defectDiagnostics"].update(
                lackOfFusionStatus="Pass" if passing(p, v, h, t, d) else "Fail",
                keyholePorosityRisk="Low (Conduction Mode)", ballingScreen=None,
                ballingInstabilityRisk="Stable Continuous Track (No Balling)", distortionIndex=0.3)
            th["processParameters"]["normalizedEnthalpy"] = 20.0
            return th

        evaluate.calls = calls
        return evaluate

    def test_every_candidate_failing_tang_drops_the_patch_with_a_reason(self):
        ev = self._evaluator(lambda *a: False)
        patch, note = _suggested_patch(self.th, "in718", "keyhole", "do-not-print", ev)
        self.assertIsNone(patch)
        self.assertIn("No parameter patch", note)
        self.assertIn("Tang", note)
        self.assertGreater(len(ev.calls), 1)  # the box corner was tried and rejected, then the grid

    def test_the_first_verified_candidate_is_returned_not_the_box_corner(self):
        corner_p, corner_v = self.box["powerMin_W"], self.box["speedMax_mm_s"]
        ev = self._evaluator(lambda p, v, h, t, d: not (p == corner_p and v == corner_v))
        patch, note = _suggested_patch(self.th, "in718", "keyhole", "do-not-print", ev)
        self.assertIsNotNone(patch)
        self.assertNotEqual((patch["laserPower_W"], patch["scanSpeed_mms"]), (corner_p, corner_v))
        self.assertTrue(self.box["powerMin_W"] <= patch["laserPower_W"] <= self.box["powerMax_W"])
        self.assertTrue(self.box["speedMin_mm_s"] <= patch["scanSpeed_mms"] <= self.box["speedMax_mm_s"])
        self.assertIn("Verified", note)

    def test_no_evaluator_offers_no_patch(self):
        patch, note = _suggested_patch(self.th, "in718", "lof_tang", "do-not-print", None)
        self.assertIsNone(patch)
        self.assertIn("not available", note)

    def test_printable_and_no_gate_cases_have_no_patch(self):
        ev = self._evaluator(lambda *a: True)
        self.assertEqual(_suggested_patch(self.th, "in718", "none", "printable", ev), (None, None))
        patch, note = _suggested_patch(self.th, "in718", "none", "inconclusive", ev)
        self.assertIsNone(patch)
        self.assertTrue(note)
        self.assertEqual(ev.calls, [])

    def test_downskin_dominant_gate_gets_no_parameter_patch(self):
        ev = self._evaluator(lambda *a: True)
        patch, note = _suggested_patch(self.th, "in718", "downskin", "do-not-print", ev)
        self.assertIsNone(patch)
        self.assertIn("downskin", note)
        self.assertEqual(ev.calls, [])


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

    def test_failing_downskin_with_lof_tang_dominant_says_the_job_stays_blocked_on_downskin(self):
        checked = 0
        for alloy in ALLOYS:
            p, v = LOF_POINT[alloy]
            job = _job(alloy, p, v, downskinOverhang_deg=70.0)
            gates = _gates(job)
            self.assertEqual(gates["downskin"], "fail", alloy)
            if gates["lof_tang"] != "fail":
                continue  # melt-pool extent not resolved for this alloy at this point (gate unavailable)
            checked += 1
            self.assertEqual(job["verdict"]["dominantGate"], "lof_tang", alloy)
            note = job["verdict"]["suggestedPatchNote"]
            self.assertIn("downskin", note, alloy)
            self.assertIn("stays do-not-print on downskin", note, alloy)
            self.assertIn("no power, speed, hatch or layer change fixes an overhang", note, alloy)
        self.assertGreaterEqual(checked, 1)

    def test_downskin_warning_note_says_risky(self):
        p, v = LOF_POINT["in718"]
        job = _job("in718", p, v, downskinOverhang_deg=50.0)
        self.assertEqual(_gates(job)["downskin"], "warn")
        self.assertIn("stays risky on downskin", job["verdict"]["suggestedPatchNote"])

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
        job = _job("in718", 210, 775, 90.0, 30.0)
        self.assertEqual(job["verdict"]["verdict"], "printable")
        self.assertIsNone(job["verdict"]["suggestedPatch"])
        self.assertIsNone(job["verdict"]["suggestedPatchNote"])


class StaleKeyholeAssumption(unittest.TestCase):
    def test_assumption_states_the_current_cuts_not_king_30(self):
        job = _job("in718", 285, 960, 110.0, 40.0)
        text = " ".join(job["assumptions"])
        self.assertNotIn("Keyhole uses King", text)
        self.assertIn("13.6", text)
        self.assertIn("provisional keyhole-mode label at 20", text)
        self.assertIn("Fabbro keyhole depth leg opens at the same onset (15)", text)
        self.assertIn("not a porosity boundary", text)


if __name__ == "__main__":
    unittest.main()
