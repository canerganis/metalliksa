#!/usr/bin/env python3
"""Self-contained tests of G1.1 accepted-prefix plumbing (python/lpbf_accepted_prefix.py).

Requests are synthetic process settings matching the transient UI defaults; no measured data is read. The boiling case
stops after a few microseconds of simulated time, so the suite stays light on CPU.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import lpbf_accepted_prefix as ap  # noqa: E402
from lpbf_request_errors import LpbfRequestRefusal, run_thermal_request  # noqa: E402

UNKNOWN = "Uncertainty is unknown and may be large. Calibrate to your machine for better accuracy."
BASE = dict(material="Ti-6Al-4V", power_W=240, speed_mm_s=1200, beamDiameter_um=80, preheat_C=150, layer_um=40,
            hatch_um=100, mode="standard", backend="reference", strategy="stripe", stripeWidth_um=500,
            islandSize_um=200, mesh_um=20, maxDt_s=1e-6, tracks=1, layers=1, trackLength_um=600, dwell_s=.0002,
            cooling_s=.0005, packingFraction=.55, powderConductivityRatio=.12, convection_W_m2K=20, timeout_s=300,
            scanAngle_deg=0, layerRotation_deg=67, study="none")
COLD = dict(BASE, power_W=40, trackLength_um=200, cooling_s=.0001)


def run(data, **kw):
    return ap.run_with_accepted_prefix(dict(data), lambda *a: None, tempfile.mkdtemp(prefix="prefix-"), {}, **kw)


class BoilingPrefixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            run(BASE)
        except LpbfRequestRefusal as refusal:
            cls.refusal = refusal
        else:
            raise AssertionError("the synthetic hot case was expected to reach the boiling limit")
        frames = []
        p = ap.execution_settings(dict(BASE))
        points = ap.selected_points(p)
        try:
            run_thermal_request(dict(BASE), lambda *a: None, tempfile.mkdtemp(prefix="prefix-"), {},
                                local_history_observer=frames.append,
                                local_history_indices_ijk=[pt["ijk"] for pt in points])
        except LpbfRequestRefusal:
            pass
        cls.frames = frames

    def test_refusal_keeps_its_code_and_carries_the_prefix(self):
        self.assertEqual(self.refusal.code, "THERMAL_BOILING_LIMIT")
        prefix = self.refusal.detail["acceptedPrefix"]
        self.assertEqual(prefix["schema"], "lpbf-accepted-prefix-1")
        self.assertEqual(prefix["estimateTier"], "Physics estimate")
        self.assertEqual(prefix["tierLabel"], "Uncalibrated estimate")
        self.assertIn(UNKNOWN, prefix["explanation"])
        self.assertIn("Only the interval from 0 s to", prefix["explanation"])
        self.assertIn("The next step exceeded the conduction model's boiling limit.", prefix["explanation"])
        self.assertEqual(prefix["maximumLabel"], "maximum over the computed interval")
        json.dumps(prefix, allow_nan=False)

    def test_only_accepted_steps_enter_the_prefix(self):
        prefix = self.refusal.detail["acceptedPrefix"]
        self.assertEqual(prefix["acceptedSteps"], len(self.frames))
        self.assertEqual(prefix["firstRejectedStep"], {"index": len(self.frames) + 1,
                                                       "reasonCode": "THERMAL_BOILING_LIMIT"})
        self.assertEqual(prefix["computedInterval_s"], [0.0, self.frames[-1]["time_s"]])
        for index, point in enumerate(prefix["points"]):
            temps = [frame["cells"][index]["temperature_K"] for frame in self.frames]
            self.assertEqual(point["maximumOverComputedInterval_K"], max(temps))
            self.assertEqual(point["lastAcceptedTemperature_K"], temps[-1])
            self.assertLessEqual(point["history"][-1]["time_s"], prefix["computedInterval_s"][1])

    def test_prefix_survives_the_job_log_tail(self):
        from lpbf_request_errors import execution_refusal, refusal_frame
        frame = refusal_frame(self.refusal)
        self.assertLess(len(frame), 12000)
        log = chr(10).join(["x" * 3000, frame, "Last valid CPU state: diagnostic line", ""])
        parsed = execution_refusal(log[-16000:])
        self.assertEqual(parsed["detail"]["acceptedPrefix"]["acceptedSteps"],
                         self.refusal.detail["acceptedPrefix"]["acceptedSteps"])

    def test_the_track_start_point_heats_inside_the_interval(self):
        start = self.refusal.detail["acceptedPrefix"]["points"][0]
        self.assertEqual(start["id"], "surface-0pct")
        self.assertGreater(start["maximumOverComputedInterval_K"], 150 + 273.15 + 100)


class UnchangedOutcomeTests(unittest.TestCase):
    def test_completed_run_is_identical_with_the_recorder(self):
        def strip(result):
            result = json.loads(json.dumps(result))
            result["provenance"].pop("createdAt", None)
            result.pop("artifacts", None)
            return result
        plain = run_thermal_request(dict(COLD), lambda *a: None, tempfile.mkdtemp(prefix="prefix-"), {})
        recorded = run(COLD)
        self.assertEqual(strip(plain), strip(recorded))
        self.assertNotIn("acceptedPrefix", json.dumps(recorded))

    def test_ineligible_runs_are_not_observed(self):
        p = ap.execution_settings(dict(BASE, study="mesh"))
        self.assertFalse(ap.eligible(p))
        self.assertFalse(ap.eligible(ap.execution_settings(dict(BASE, mode="screening"))))
        self.assertTrue(ap.eligible(ap.execution_settings(dict(BASE))))


if __name__ == "__main__":
    unittest.main()
