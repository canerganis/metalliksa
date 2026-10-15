"""R-IPC: the isolated P8 research lane in python/persistent_ipc_service.py (integration contract 2026-10-15, 3.3,
13.7 item 2, P-8, R-TR-13 lane side).

Deterministic lane tests use the thread-pool factory pattern of the _AffinityLane tests in test_calphad_model_cache
(no processes): a run timeout recycles only the research lane and leaves the shared pool untouched; queue and run
timeouts answer exit 124 with the research timeout envelope; a queued research request is superseded; the lane is
never prestarted; a research payload with an ``action`` key never reaches the shared pool; a result carrying
"recycleWorker": true replaces the worker before the next request. One test runs the real script in a real lane
worker process. This file imports no research module (R-ISO-1): it talks to the lane through the IPC service only.
"""

from __future__ import annotations

import json
import os
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock

import persistent_ipc_service as ipc

HERE = Path(__file__).resolve().parent
RESEARCH = "lpbf_research_models"
RESEARCH_SCRIPT = f"python/{RESEARCH}.py"
STALE_STDOUT = json.dumps({"success": False, "errorKind": "validation", "reasonCode": "RESEARCH_CODE_STALE",
                           "problems": [], "recycleWorker": True})


class _FakePool:
    """Thread pool stand-in for a lane (records kills)."""

    def __init__(self, log):
        self.inner = ThreadPoolExecutor(1)
        self.log = log
        self.killed = False

    def submit(self, fn, *args):
        return self.inner.submit(fn, *args)

    def shutdown(self, wait=False, cancel_futures=True):
        self.killed = True
        self.log.append(self)
        self.inner.shutdown(wait=False, cancel_futures=True)


class _SharedPoolSentinel:
    def __init__(self):
        self.submitted = []

    def submit(self, *args):
        self.submitted.append(args)
        raise AssertionError("a research request reached the shared pool")


def _registry():
    """A ConcurrentModuleRegistry without warm-up or processes; lanes use thread pools."""
    reg = ipc.ConcurrentModuleRegistry.__new__(ipc.ConcurrentModuleRegistry)
    reg.script_dir = ipc.SCRIPT_DIR
    reg.num_workers = 1
    reg.modules, reg.compiled_code, reg.import_times = {}, {}, {}
    reg.stats_lock, reg.fallback_lock = threading.Lock(), threading.Lock()
    reg.request_count, reg.active_jobs, reg.total_duration_ms = 0, 0, 0.0
    reg.start_time = time.time()
    reg.pool = _SharedPoolSentinel()
    reg.affinity_lanes, reg.affinity_lock = {}, threading.Lock()
    reg.pools, reg.kills = [], []

    def factory_for(name):
        def factory():
            pool = _FakePool(reg.kills)
            reg.pools.append((name, pool))
            return pool
        return factory

    def lane(name):
        with reg.affinity_lock:
            if name not in reg.affinity_lanes:
                reg.affinity_lanes[name] = ipc._AffinityLane(name, factory_for(name), (ipc._worker_noop, 0.0))
            return reg.affinity_lanes[name]
    reg._affinity_lane = lane
    return reg


def _script_returning(*outputs, delay=0.0):
    """A stand-in for _worker_run_script that answers the given stdout texts in order (the last repeats)."""
    calls = []

    def fake(full_path, input_str, args):
        calls.append(os.path.basename(full_path))
        time.sleep(delay)
        text = outputs[min(len(calls) - 1, len(outputs) - 1)]
        return {"stdout": text, "stderr": "", "exitCode": 2 if '"validation"' in text else 0}
    fake.calls = calls
    return fake


class IsolatedLaneConfiguration(unittest.TestCase):
    def test_constants(self):
        self.assertEqual(ipc.ISOLATED_SCRIPT_NAMES, frozenset({RESEARCH}))
        self.assertIn(RESEARCH, ipc.AFFINITY_SCRIPT_NAMES)
        self.assertIn(RESEARCH, ipc.ALLOWED_SCRIPT_NAMES)
        self.assertNotIn(RESEARCH, ipc.WARM_MODULE_NAMES)

    def test_the_research_lane_is_never_prestarted(self):
        reg = _registry()
        reg.start_affinity_pools()
        self.assertNotIn(RESEARCH, reg.affinity_lanes)
        self.assertEqual([name for name, _ in reg.pools], sorted(ipc.AFFINITY_SCRIPT_NAMES - {RESEARCH}))


class IsolatedLane(unittest.TestCase):
    def setUp(self):
        self.reg = _registry()

    def run_async(self, payload, timeout_ms):
        box = {}
        t = threading.Thread(target=lambda: box.setdefault(
            "out", self.reg.execute_script(RESEARCH_SCRIPT, payload, [], timeout_ms)), daemon=True)
        t.start()
        return t, box

    def test_a_research_request_runs_in_its_own_lane_never_the_shared_pool(self):
        fake = _script_returning('{"success": true}')
        with mock.patch.object(ipc, "_worker_run_script", fake):
            out = self.reg.execute_script(RESEARCH_SCRIPT, {"stage": "nominal"}, [], 5000)
            meta = self.reg.execute_script(RESEARCH_SCRIPT, {"action": "list_databases"}, [], 5000)
        for result in (out, meta):
            self.assertEqual(result["concurrency"], f"affinity_pool:{RESEARCH}")
            self.assertEqual(result["exitCode"], 0)
        self.assertEqual(self.reg.pool.submitted, [])  # the metadata exemption never applies to research
        self.assertEqual(fake.calls, [f"{RESEARCH}.py", f"{RESEARCH}.py"])

    def test_a_run_timeout_recycles_only_the_research_lane(self):
        calphad = self.reg._affinity_lane("calphad_solver")
        calphad.prestart()
        calphad_pool = calphad.pool
        shared = self.reg.pool
        with mock.patch.object(ipc, "_worker_run_script", _script_returning('{"success": true}', delay=3.0)):
            out = self.reg.execute_script(RESEARCH_SCRIPT, {"stage": "band"}, [], 1000)
        self.assertEqual(out["exitCode"], 124)
        self.assertEqual(json.loads(out["stdout"]), {"success": False, "errorKind": "research",
                                                     "reasonCode": "RESEARCH_TIMEOUT", "timeoutKind": "run"})
        self.assertIn("timed out", out["stderr"])
        lane = self.reg.affinity_lanes[RESEARCH]
        self.assertEqual(lane.snapshot()["runTimeouts"], 1)
        self.assertEqual(lane.generation, 2)  # replaced
        self.assertIs(calphad.pool, calphad_pool)  # the calphad lane is untouched
        self.assertFalse(calphad_pool.killed)
        self.assertIs(self.reg.pool, shared)  # the shared pool is untouched
        self.assertEqual(shared.submitted, [])

    def test_a_queue_timeout_answers_the_queue_envelope_and_keeps_the_worker(self):
        with mock.patch.object(ipc, "_worker_run_script", _script_returning('{"success": true}', delay=1.5)):
            blocker = self.run_async({"supersedeKey": "a"}, 10000)
            deadline = time.monotonic() + 10
            while not (self.reg.affinity_lanes.get(RESEARCH) and self.reg.affinity_lanes[RESEARCH].running):
                self.assertLess(time.monotonic(), deadline)
                time.sleep(0.005)
            out = self.reg.execute_script(RESEARCH_SCRIPT, {"supersedeKey": "b"}, [], 1000)
            blocker[0].join(10)
        self.assertEqual(out["exitCode"], 124)
        self.assertEqual(json.loads(out["stdout"])["timeoutKind"], "queue")
        self.assertIn("never started", out["stderr"])
        lane = self.reg.affinity_lanes[RESEARCH]
        self.assertEqual((lane.generation, lane.snapshot()["queueTimeouts"]), (1, 1))
        self.assertEqual(blocker[1]["out"]["exitCode"], 0)

    def test_a_queued_research_request_is_superseded_by_a_newer_one_with_the_same_key(self):
        with mock.patch.object(ipc, "_worker_run_script", _script_returning('{"success": true}', delay=0.8)):
            running = self.run_async({"supersedeKey": "p8-research:melt-pool", "n": 1}, 20000)
            deadline = time.monotonic() + 10
            while not (self.reg.affinity_lanes.get(RESEARCH) and self.reg.affinity_lanes[RESEARCH].running):
                self.assertLess(time.monotonic(), deadline)
                time.sleep(0.005)
            stale = self.run_async({"supersedeKey": "p8-research:melt-pool", "n": 2}, 20000)
            while self.reg.affinity_lanes[RESEARCH].snapshot()["queued"] < 1:
                self.assertLess(time.monotonic(), deadline)
                time.sleep(0.005)
            latest = self.run_async({"supersedeKey": "p8-research:melt-pool", "n": 3}, 20000)
            for t, _ in (running, stale, latest):
                t.join(20)
        self.assertEqual(json.loads(stale[1]["out"]["stdout"])["status"], "superseded")
        self.assertEqual(latest[1]["out"]["exitCode"], 0)
        self.assertEqual(running[1]["out"]["exitCode"], 0)

    def test_recycle_worker_flag_replaces_the_worker_before_the_next_request(self):  # R-TR-13 lane side
        fake = _script_returning(STALE_STDOUT, '{"success": true}')
        with mock.patch.object(ipc, "_worker_run_script", fake):
            first = self.reg.execute_script(RESEARCH_SCRIPT, {"stage": "nominal"}, [], 5000)
            lane = self.reg.affinity_lanes[RESEARCH]
            pools_after_first = [p for name, p in self.reg.pools if name == RESEARCH]
            second = self.reg.execute_script(RESEARCH_SCRIPT, {"stage": "nominal"}, [], 5000)
        self.assertEqual(first["exitCode"], 2)
        self.assertTrue(first.get("workerRecycled"))
        self.assertEqual(len(pools_after_first), 2)  # the stale worker was replaced at once
        self.assertTrue(pools_after_first[0].killed)
        self.assertIs(lane.pool, pools_after_first[1])  # the next request ran in the fresh worker
        self.assertEqual(second["exitCode"], 0)
        self.assertNotIn("workerRecycled", second)
        self.assertEqual(lane.snapshot()["recycles"], 1)

    def test_no_recycle_without_the_flag_and_never_for_a_non_isolated_lane(self):
        self.assertFalse(ipc._requests_worker_recycle({"stdout": '{"success": true, "note": "recycleWorker"}'}))
        self.assertFalse(ipc._requests_worker_recycle({"stdout": '{"recycleWorker": "yes"}'}))
        self.assertFalse(ipc._requests_worker_recycle({"stdout": "not json recycleWorker"}))
        self.assertTrue(ipc._requests_worker_recycle({"stdout": STALE_STDOUT}))
        with mock.patch.object(ipc, "_worker_run_script", _script_returning(STALE_STDOUT)):
            out = self.reg.execute_script("python/calphad_solver.py", {"x": 1}, [], 5000)
        self.assertNotIn("workerRecycled", out)
        self.assertEqual(self.reg.affinity_lanes["calphad_solver"].snapshot()["recycles"], 0)

    def test_calphad_timeouts_keep_their_empty_stdout(self):
        with mock.patch.object(ipc, "_worker_run_script", _script_returning("{}", delay=3.0)):
            out = self.reg.execute_script("python/calphad_solver.py", {"x": 1}, [], 1000)
        self.assertEqual((out["exitCode"], out["stdout"]), (124, ""))


class RealResearchWorker(unittest.TestCase):
    """The real dispatch script in a real lane worker process (spawned, the research module imported at init)."""

    def test_the_real_script_answers_from_its_own_lane_process(self):
        reg = ipc.ConcurrentModuleRegistry(ipc.SCRIPT_DIR, num_workers=1)
        self.addCleanup(reg.shutdown)
        self.assertNotIn(RESEARCH, reg.get_status()["affinityPools"])
        out = reg.execute_script(RESEARCH_SCRIPT, {"schemaVersion": "p8-research-request-v1", "action": "x"}, [],
                                 120000)
        self.assertEqual(out["concurrency"], f"affinity_pool:{RESEARCH}")
        self.assertEqual(out["exitCode"], 2, out["stderr"][-800:])
        parsed = json.loads(out["stdout"])
        self.assertEqual((parsed["errorKind"], parsed["reasonCode"]), ("validation", "RESEARCH_REQUEST_INVALID"))
        self.assertIn("/action", [p["pointer"] for p in parsed["problems"]])
        self.assertIn(RESEARCH, reg.get_status()["affinityPools"])


if __name__ == "__main__":
    unittest.main()
