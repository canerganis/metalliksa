"""Worker job type for the opt-in AlSi10Mg (Al6061 proxy) evaporative solver.

Self-contained: the request is carried here, the solver runs for real through the same Queue
path as every other job type, and the pinned strings are the solver's own labels."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import lpbf_worker
from lpbf_worker import (
    ALSI10MG_EVAPORATIVE_JOB_TYPE,
    Queue,
    _enforce_alsi10mg_evaporative_result,
    _validate_alsi10mg_evaporative_request,
)

EVAPORATION = {
    "transitionLow_K": 2800.0, "transitionHigh_K": 3200.0, "ambientPressure_Pa": 101325.0,
    "returnFraction": 0.18, "maxTemperature_K": 5000.0, "surfaceTension_N_m": 0.91,
}
# AlSi10Mg bare plate, 300 W, 1300 mm/s, 100 um beam, 80 C preheat; a 100 um declared track keeps the test short.
JOB = {
    "jobType": ALSI10MG_EVAPORATIVE_JOB_TYPE,
    "config": {"power_W": 300.0, "speed_mm_s": 1300.0, "beamDiameter_um": 100.0, "preheat_C": 80.0,
               "trackLength_um": 100.0, "evaporation": EVAPORATION},
}
DISCLOSURE = ("Thermal and vapour constants are Al6061 values (Gan 2021 SI Tables 1-2, citing Valencia and "
              "Quested 2013) used as an Al-rich proxy for AlSi10Mg; Mg and Si selective evaporation and the "
              "real AlSi10Mg composition are not modelled.")
REFUSAL_REASON = ("The surface would deform into a vapor cavity at these settings. A fixed-surface model "
                  "cannot give melt depth here. Use a model with surface motion and melt flow for depth, "
                  "length and volume.")


class AlSi10MgEvaporativeWorkerTests(unittest.TestCase):
    def temporary_directory(self):
        return tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1])

    def test_request_is_strict_and_normalized_by_the_solver_validator(self):
        request, material = _validate_alsi10mg_evaporative_request(JOB)
        config = request["config"]
        self.assertEqual((config["material"], config["surfaceMode"], config["backend"]),
                         ("AlSi10Mg", "bare-plate", "reference"))
        self.assertEqual(material["materialId"], "proxy:gan2021-al6061-for-alsi10mg")
        self.assertEqual(_validate_alsi10mg_evaporative_request(request)[0], request)
        for bad in (
            [], {**JOB, "jobType": "ti64-evaporative-surface"}, {**JOB, "timeout_s": 20},
            {**JOB, "config": {**JOB["config"], "surfaceMode": "powder-layer"}},
            {**JOB, "config": {**JOB["config"], "material": "Ti-6Al-4V"}},
            {**JOB, "config": {**JOB["config"], "power_W": True}},
            {**JOB, "config": {k: v for k, v in JOB["config"].items() if k != "evaporation"}},
        ):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                _validate_alsi10mg_evaporative_request(bad)

    def test_queue_runs_the_solver_and_keeps_labels_and_refusal_verbatim(self):
        with self.temporary_directory() as tmp:
            queue = Queue(tmp, start=False)
            try:
                submitted = queue.submit(JOB)
                self.assertEqual(submitted["requestSummary"]["jobType"], ALSI10MG_EVAPORATIVE_JOB_TYPE)
                queue.update(submitted["id"], status="running")
                queue.execute(submitted["id"])
                state = queue.get(submitted["id"])
                self.assertEqual(state["status"], "completed", state.get("error"))
                result = state["result"]
                self.assertEqual(result["modelId"], "alsi10mg-al6061-proxy-fixed-surface-evaporation-v1")
                self.assertIs(result["experimentalValidation"], False)
                self.assertEqual(result["disclosure"], DISCLOSURE)
                self.assertTrue(result["gate"]["onset"])
                for key in ("depth_um", "length_um", "volume_um3"):
                    self.assertIsNone(result["geometry"][key], key)
                self.assertEqual(result["geometry"]["refusalReason"], REFUSAL_REASON)
                self.assertGreater(result["energy"]["evaporative_J"], 0)
                self.assertLessEqual(abs(result["energy"]["relativeResidual"]), 1e-9)
                self.assertEqual(result["provenance"]["inputs"], result["settings"]["config"])
            finally:
                queue.close()

    def test_cache_identity_is_distinct_and_deduplicates(self):
        with self.temporary_directory() as tmp:
            queue = Queue(tmp, start=False)
            try:
                first = queue.submit(JOB)
                self.assertTrue(queue.submit(JOB)["deduplicated"])
                other = queue.submit({**JOB, "config": {**JOB["config"], "power_W": 301.0}})
                self.assertNotEqual(other["id"], first["id"])
                self.assertEqual(queue.cancel(first["id"])["status"], "cancelled")
            finally:
                queue.close()

    def test_timeout_uses_the_shared_job_timeout(self):
        long_job = {**JOB, "config": {**JOB["config"], "trackLength_um": 600.0}}
        with self.temporary_directory() as tmp:
            queue = Queue(tmp, start=False)
            try:
                submitted = queue.submit(long_job)
                queue.update(submitted["id"], status="running")
                with patch.object(lpbf_worker, "DEFAULT_JOB_TIMEOUT_S", 0.5):
                    queue.execute(submitted["id"])
                state = queue.get(submitted["id"])
                self.assertEqual(state["status"], "timed_out")
                self.assertNotIn("result", state)
            finally:
                queue.close()

    def test_result_audit_rejects_a_filled_relabelled_or_unbound_result(self):
        request, _ = _validate_alsi10mg_evaporative_request(JOB)
        result = lpbf_worker._run_alsi10mg_evaporative_job(JOB, None)
        _enforce_alsi10mg_evaporative_result(result, request)
        for name, tamper in (
            ("filled depth", lambda r: r["geometry"].update(depth_um=50.0)),
            ("missing reason", lambda r: r["geometry"].update(refusalReason=None)),
            ("validated flag", lambda r: r.update(experimentalValidation=True)),
            ("dropped disclosure", lambda r: r.update(disclosure="AlSi10Mg")),
            ("open energy", lambda r: r["energy"].update(relativeResidual=1e-3)),
            ("other settings", lambda r: r["settings"]["config"].update(power_W=301.0)),
        ):
            copy = json.loads(json.dumps(result))
            tamper(copy)
            with self.subTest(name), self.assertRaises(ValueError):
                _enforce_alsi10mg_evaporative_result(copy, request)


if __name__ == "__main__":
    unittest.main()
