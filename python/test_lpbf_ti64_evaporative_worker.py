"""Worker job type for the opt-in Ti-6Al-4V evaporative solver (SPEC_ti64_standard_integration C1).

Self-contained: the request is carried here, the solver runs for real in an isolated child
process through the same Queue path as every other job type, and the pinned strings are the
solver's own labels."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import lpbf_worker
from lpbf_worker import (
    TI64_EVAPORATIVE_JOB_TYPE,
    Queue,
    _enforce_ti64_evaporative_result,
    _validate_ti64_evaporative_request,
)

EVAPORATION = {
    "transitionLow_K": 3560.0, "transitionHigh_K": 4000.0, "ambientPressure_Pa": 101325.0,
    "returnFraction": 0.2, "maxTemperature_K": 5000.0, "surfaceTension_N_m": 1.65,
}
# Ti-6Al-4V bare plate, 150 W, 1000 mm/s, 80 um beam, 80 C preheat. A 100 um track keeps the test short;
# it is the declared track of this fixture, not a claim about the UI default (600 um).
JOB = {
    "jobType": TI64_EVAPORATIVE_JOB_TYPE,
    "config": {"power_W": 150.0, "speed_mm_s": 1000.0, "beamDiameter_um": 80.0, "preheat_C": 80.0,
               "trackLength_um": 100.0, "evaporation": EVAPORATION},
}
REFUSAL_REASON = ("The surface would deform into a vapor cavity at these settings. A fixed-surface model "
                  "cannot give melt depth here. Use a model with surface motion and melt flow for depth, "
                  "length and volume.")
WIDTH_WARNING = ("The surface would deform into a vapor cavity. This width is a fixed-surface isotherm "
                 "scenario and may not represent the melt pool.")


class Ti64EvaporativeWorkerTests(unittest.TestCase):
    def temporary_directory(self):
        return tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1])

    def test_request_is_strict_and_normalized_by_the_solver_validator(self):
        request, material = _validate_ti64_evaporative_request(JOB)
        self.assertEqual(request["jobType"], TI64_EVAPORATIVE_JOB_TYPE)
        config = request["config"]
        self.assertEqual((config["material"], config["surfaceMode"], config["backend"]),
                         ("Ti-6Al-4V", "bare-plate", "reference"))
        self.assertEqual(config["mesh_um"], 20.0)  # solver default, not a UI override
        self.assertEqual(material["name"], "Ti-6Al-4V")
        self.assertEqual(_validate_ti64_evaporative_request(request)[0], request)  # idempotent

        for bad in (
            [],
            {**JOB, "jobType": "transient-thermal"},
            {**JOB, "timeout_s": 20},
            {**JOB, "backend": "cpu"},
            {**JOB, "config": []},
            {**JOB, "config": {**JOB["config"], "timeout_s": 20}},
            {**JOB, "config": {**JOB["config"], "surfaceMode": "powder-layer"}},
            {**JOB, "config": {**JOB["config"], "material": "IN718"}},
            {**JOB, "config": {**JOB["config"], "power_W": True}},
            {**JOB, "config": {**JOB["config"], "power_W": float("nan")}},
            {**JOB, "config": {k: v for k, v in JOB["config"].items() if k != "evaporation"}},
        ):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                _validate_ti64_evaporative_request(bad)

    def test_queue_runs_the_solver_and_keeps_labels_and_refusal_verbatim(self):
        with self.temporary_directory() as tmp:
            queue = Queue(tmp, start=False)
            try:
                submitted = queue.submit(JOB)
                self.assertEqual(submitted["requestSummary"]["jobType"], TI64_EVAPORATIVE_JOB_TYPE)
                self.assertNotIn("backend", submitted["requestSummary"])
                queue.update(submitted["id"], status="running")
                queue.execute(submitted["id"])
                state = queue.get(submitted["id"])
                self.assertEqual(state["status"], "completed", state.get("error"))
                result = state["result"]
                self.assertEqual(result["jobType"], TI64_EVAPORATIVE_JOB_TYPE)
                self.assertEqual(result["settings"], json.loads((Path(tmp)/submitted["id"]/"input.json").read_text()))
                self.assertEqual(result["modelId"], "ti64-fixed-surface-evaporation-v1")
                self.assertIs(result["experimentalValidation"], False)
                self.assertIs(result["productionReady"], False)
                self.assertEqual(result["tier"], "Uncalibrated estimate")
                self.assertEqual(result["temperatureLabel"], "Conditional fixed-surface temperature estimate")
                self.assertNotIn("runKind", result)
                geometry = result["geometry"]
                self.assertTrue(result["gate"]["onset"])
                self.assertFalse(result["gate"]["geometryAvailable"])
                for key in ("depth_um", "length_um", "volume_um3"):
                    self.assertIsNone(geometry[key], key)
                self.assertEqual(geometry["refusalReason"], REFUSAL_REASON)
                self.assertEqual(geometry["widthLabel"], "Conditional fixed-surface liquidus width estimate")
                self.assertEqual(geometry["widthWarning"], WIDTH_WARNING)
                self.assertGreater(geometry["width_um"], 0)  # width is carried, not nulled or clipped
                energy = result["energy"]
                self.assertLessEqual(abs(energy["relativeResidual"]), 1e-9)
                self.assertGreater(energy["evaporative_J"], 0)
                self.assertEqual(result["provenance"]["inputs"], result["settings"]["config"])
                self.assertIn("runtime_s", result["provenance"])
            finally:
                queue.close()

    def test_cache_identity_follows_the_request_and_deduplicates_equal_requests(self):
        with self.temporary_directory() as tmp:
            queue = Queue(tmp, start=False)
            try:
                first = queue.submit(JOB)
                again = queue.submit(JOB)
                self.assertEqual(again["id"], first["id"])
                self.assertTrue(again["deduplicated"])
                other = queue.submit({**JOB, "config": {**JOB["config"], "power_W": 151.0}})
                self.assertNotEqual(other["id"], first["id"])
                repeat = queue.submit(JOB, execution_scope="repeat")
                self.assertNotEqual(repeat["id"], first["id"])
                with queue.connect() as c:
                    keys = {row["id"]: row["cache_key"] for row in c.execute("SELECT id, cache_key FROM jobs")}
                self.assertEqual(keys[first["id"]], keys[repeat["id"]])
                self.assertNotEqual(keys[first["id"]], keys[other["id"]])
            finally:
                queue.close()

    def test_refused_request_is_rejected_before_queueing(self):
        with self.temporary_directory() as tmp:
            queue = Queue(tmp, start=False)
            try:
                with self.assertRaises(ValueError):
                    queue.submit({**JOB, "config": {**JOB["config"], "surfaceMode": "powder-layer"}})
                with queue.connect() as c:
                    self.assertEqual(c.execute("SELECT count(*) FROM jobs").fetchone()[0], 0)
            finally:
                queue.close()

    def test_queued_job_can_be_cancelled(self):
        with self.temporary_directory() as tmp:
            queue = Queue(tmp, start=False)
            try:
                submitted = queue.submit(JOB)
                self.assertEqual(submitted["status"], "queued")
                cancelled = queue.cancel(submitted["id"])
                self.assertEqual(cancelled["status"], "cancelled")
                self.assertNotIn("result", cancelled)
            finally:
                queue.close()

    def test_timeout_uses_the_shared_job_timeout(self):
        long_job = {**JOB, "config": {**JOB["config"], "trackLength_um": 600.0}}  # about 20 s of CPU
        with self.temporary_directory() as tmp:
            queue = Queue(tmp, start=False)
            try:
                submitted = queue.submit(long_job)
                queue.update(submitted["id"], status="running")
                with patch.object(lpbf_worker, "DEFAULT_JOB_TIMEOUT_S", 0.5):
                    queue.execute(submitted["id"])
                state = queue.get(submitted["id"])
                self.assertEqual(state["status"], "timed_out")
                self.assertEqual(state["error"], "Simulation timeout")
                self.assertNotIn("result", state)
            finally:
                queue.close()

    def test_result_audit_rejects_a_filled_or_unbound_result(self):
        request, _ = _validate_ti64_evaporative_request(JOB)
        result = lpbf_worker._run_ti64_evaporative_job(JOB, None)
        _enforce_ti64_evaporative_result(result, request)
        for name, tamper in (
            ("filled depth", lambda r: r["geometry"].update(depth_um=50.0)),
            ("missing reason", lambda r: r["geometry"].update(refusalReason=None)),
            ("validated flag", lambda r: r.update(experimentalValidation=True)),
            ("open energy", lambda r: r["energy"].update(relativeResidual=1e-3)),
            ("other settings", lambda r: r["settings"]["config"].update(power_W=151.0)),
        ):
            copy = json.loads(json.dumps(result))
            tamper(copy)
            with self.subTest(name), self.assertRaises(ValueError):
                _enforce_ti64_evaporative_result(copy, request)


if __name__ == "__main__":
    unittest.main()
