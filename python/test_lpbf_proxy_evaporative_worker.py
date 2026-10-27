"""Worker job type for the opt-in 316L and IN718 proxy evaporative solver.

Self-contained: the requests are carried here, the solver runs for real through the same Queue
path as every other job type, and the pinned strings are the solver's own labels."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import lpbf_worker
from lpbf_worker import (
    PROXY_EVAPORATIVE_JOB_TYPE,
    Queue,
    _enforce_proxy_evaporative_result,
    _validate_proxy_evaporative_request,
)


def job(material, power, low, high, sigma):
    evaporation = {"transitionLow_K": low, "transitionHigh_K": high, "ambientPressure_Pa": 101325.0,
                   "returnFraction": 0.18, "maxTemperature_K": 5000.0, "surfaceTension_N_m": sigma}
    # Bare plate, 1000 mm/s, 100 um beam, 80 C preheat; a 100 um declared track keeps the test short.
    return {"jobType": PROXY_EVAPORATIVE_JOB_TYPE,
            "config": {"material": material, "power_W": power, "speed_mm_s": 1000.0, "beamDiameter_um": 100.0,
                       "preheat_C": 80.0, "trackLength_um": 100.0, "evaporation": evaporation}}


JOBS = {
    "ss316l-gan2021-ss316-proxy-fixed-surface-evaporation-v1": job("316L Stainless Steel", 200.0, 3022.0, 3522.0, 1.87),
    "in718-fang2021-ni-proxy-fixed-surface-evaporation-v1": job("Inconel 718", 150.0, 3083.0, 3583.0, 1.882),
}
REFUSAL_REASON = ("The model's recoil/capillary onset criterion was exceeded; surface deformation "
                  "and keyhole geometry are not resolved, so depth, length and volume are not reported.")


class ProxyEvaporativeWorkerTests(unittest.TestCase):
    def temporary_directory(self):
        return tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1])

    def test_request_is_strict_and_normalized_by_the_solver_validator(self):
        for model, base in JOBS.items():
            request, material = _validate_proxy_evaporative_request(base)
            config = request["config"]
            self.assertEqual((config["material"], config["surfaceMode"], config["backend"]),
                             (base["config"]["material"], "bare-plate", "reference"))
            self.assertTrue(material["materialId"].startswith("proxy:"))
            self.assertEqual(_validate_proxy_evaporative_request(request)[0], request)
            for bad in (
                [], {**base, "jobType": "alsi10mg-evaporative-surface"}, {**base, "timeout_s": 20},
                {**base, "config": {**base["config"], "surfaceMode": "powder-layer"}},
                {**base, "config": {**base["config"], "material": "AlSi10Mg"}},
                {**base, "config": {k: v for k, v in base["config"].items() if k != "material"}},
                {**base, "config": {**base["config"], "power_W": True}},
                {**base, "config": {k: v for k, v in base["config"].items() if k != "evaporation"}},
            ):
                with self.subTest(model=model, bad=bad), self.assertRaises(ValueError):
                    _validate_proxy_evaporative_request(bad)

    def test_queue_runs_the_solver_and_keeps_labels_and_refusal_verbatim(self):
        with self.temporary_directory() as tmp:
            queue = Queue(tmp, start=False)
            try:
                for model, base in JOBS.items():
                    submitted = queue.submit(base)
                    self.assertEqual(submitted["requestSummary"]["jobType"], PROXY_EVAPORATIVE_JOB_TYPE)
                    queue.update(submitted["id"], status="running")
                    queue.execute(submitted["id"])
                    state = queue.get(submitted["id"])
                    self.assertEqual(state["status"], "completed", state.get("error"))
                    result = state["result"]
                    self.assertEqual(result["modelId"], model)
                    self.assertIs(result["experimentalValidation"], False)
                    self.assertEqual(result["evidenceLabel"], "Unresolved")
                    self.assertEqual(result["evidence"]["unresolvedInputs"], ["transitionLow_K", "transitionHigh_K"])
                    self.assertTrue(result["gate"]["onset"])
                    for key in ("depth_um", "length_um", "volume_um3"):
                        self.assertIsNone(result["geometry"][key], key)
                    self.assertEqual(result["geometry"]["refusalReason"], REFUSAL_REASON)
                    self.assertGreater(result["energy"]["evaporative_J"], 0)
                    self.assertLessEqual(abs(result["energy"]["relativeResidual"]), 1e-9)
                    self.assertEqual(result["provenance"]["inputs"], result["settings"]["config"])
            finally:
                queue.close()

    def test_cache_identity_is_distinct_per_alloy_and_deduplicates(self):
        with self.temporary_directory() as tmp:
            queue = Queue(tmp, start=False)
            try:
                ids = set()
                for base in JOBS.values():
                    first = queue.submit(base)
                    self.assertTrue(queue.submit(base)["deduplicated"])
                    other = queue.submit({**base, "config": {**base["config"], "power_W": 151.0}})
                    self.assertNotEqual(other["id"], first["id"])
                    ids |= {first["id"], other["id"]}
                self.assertEqual(len(ids), 4)
            finally:
                queue.close()

    def test_timeout_uses_the_shared_job_timeout(self):
        base = next(iter(JOBS.values()))
        long_job = {**base, "config": {**base["config"], "trackLength_um": 600.0}}
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
        base = JOBS["in718-fang2021-ni-proxy-fixed-surface-evaporation-v1"]
        request, _ = _validate_proxy_evaporative_request(base)
        result = lpbf_worker._run_proxy_evaporative_job(base, None)
        _enforce_proxy_evaporative_result(result, request)
        for name, tamper in (
            ("filled depth", lambda r: r["geometry"].update(depth_um=50.0)),
            ("missing reason", lambda r: r["geometry"].update(refusalReason=None)),
            ("validated flag", lambda r: r.update(experimentalValidation=True)),
            ("dropped disclosure", lambda r: r.update(disclosure="IN718")),
            ("promoted label", lambda r: r.update(evidenceLabel="Literature estimate")),
            ("promoted evidence", lambda r: r["evidence"].update(label="Literature estimate")),
            ("other alloy model", lambda r: r.update(modelId="ss316l-gan2021-ss316-proxy-fixed-surface-evaporation-v1")),
            ("open energy", lambda r: r["energy"].update(relativeResidual=1e-3)),
            ("other settings", lambda r: r["settings"]["config"].update(power_W=301.0)),
        ):
            copy = json.loads(json.dumps(result))
            tamper(copy)
            with self.subTest(name), self.assertRaises(ValueError):
                _enforce_proxy_evaporative_result(copy, request)

    def test_result_audit_recomputes_the_label_from_inputs_and_checks_gate_flags(self):
        base = JOBS["in718-fang2021-ni-proxy-fixed-surface-evaporation-v1"]
        request, _ = _validate_proxy_evaporative_request(base)
        result = lpbf_worker._run_proxy_evaporative_job(base, None)
        self.assertTrue(result["gate"]["onset"])

        def relabel(r):  # label, evidence label and the unresolved list tampered together
            r["evidenceLabel"] = "Literature estimate"
            r["evidence"].update(label="Literature estimate", unresolvedInputs=[])

        def relabel_as_user_input(r):
            r["evidenceLabel"] = "User input"
            r["evidence"].update(label="User input", unresolvedInputs=[], userInputs=["transitionLow_K"])

        def open_gate(r):  # geometry flagged available while onset stays latched
            r["gate"]["geometryAvailable"] = True

        def open_gate_and_fill(r):
            open_gate(r)
            r["geometry"].update(depth_um=50.0, length_um=60.0, volume_um3=1e3, refusalReason=None)

        def unlatch_gate(r):  # onset cleared, availability still false
            r["gate"].update(onset=False, firstOnsetTime_s=None)

        for name, tamper in (
            ("relabelled together", relabel),
            ("relabelled as user input", relabel_as_user_input),
            ("gate open with onset", open_gate),
            ("gate open, extents filled, reason cleared", open_gate_and_fill),
            ("onset unlatched", unlatch_gate),
            ("label and gate together", lambda r: (relabel(r), open_gate_and_fill(r))),
        ):
            copy = json.loads(json.dumps(result))
            tamper(copy)
            with self.subTest(name), self.assertRaises(ValueError):
                _enforce_proxy_evaporative_result(copy, request)

        # Thresholds changed in the request, result left Unresolved: the label no longer follows the inputs.
        changed = json.loads(json.dumps(request))
        changed["config"]["evaporation"].update(transitionLow_K=3100.0, transitionHigh_K=3600.0)
        copy = json.loads(json.dumps(result))
        copy["settings"] = changed
        copy["provenance"]["inputs"] = changed["config"]
        with self.assertRaisesRegex(ValueError, "does not match the request inputs"):
            _enforce_proxy_evaporative_result(copy, changed)


if __name__ == "__main__":
    unittest.main()
