"""Blind job types through the real LPBF worker queue and child processes (spec 3.2, 11.1 item 7).

The served arm in the child is replaced by a noisy stub through a test-only `sitecustomize.py` placed on PYTHONPATH
for the spawned children: it returns sentinel predicted depths and also prints them to stdout and stderr (Python and
os.write on descriptors 1 and 2) and emits them in a warning. The test then scans progress.log, the sqlite log and
error columns and the worker get() response for them. Synthetic data only.
"""
import base64
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import test_lpbf_user_blind as tub

PY = Path(__file__).resolve().parent
SENTINEL = "4321.98765"
SITECUSTOMIZE = r'''
import os, sys
if os.environ.get("BLIND_TEST_STUB_DIR"):
    sys.path.insert(0, os.environ["BLIND_TEST_STUB_DIR"])
    import warnings
    import lpbf_user_blind_freeze as f
    from lpbf_served_arms import served_index
    SENT = float("4321.98765")
    def noisy(alloy, P, v, d, T0, layer=40.0, **kw):
        print("served depth", SENT, flush=True)
        os.write(1, b"fd1 4321.98765\n")
        os.write(2, b"fd2 4321.98765\n")
        warnings.warn("depth 4321.98765")
        if os.environ.get("BLIND_TEST_STUB_RAISE"):
            raise RuntimeError("solver blew up at 4321.98765")
        return {"status": "ok", "depth_um": SENT + P * 1e-6, "width_um": SENT / 3, "extentStatus": "computed",
                "fabbroDepth_um": SENT / 2, "index": served_index(alloy, P, v, d, T0), "reasonLabel": None,
                "materialEvidence": None, "buildJobIdentity": None}
    f.served_arm = noisy
'''


class WorkerBlindJobs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="blind-worker-"))
        (cls.tmp / "site").mkdir()
        (cls.tmp / "site" / "sitecustomize.py").write_text(SITECUSTOMIZE)
        cls.env = mock.patch.dict(os.environ, {
            "METALLIKSA_USER_BLIND_ROOT": str(cls.tmp / "store"), "METALLIKSA_JOB_ROOT": str(cls.tmp / "jobs"),
            "PYTHONPATH": str(cls.tmp / "site"), "BLIND_TEST_STUB_DIR": str(PY), "METALLIKSA_READ_ONLY": "",
            "METALLIKSA_HOST": ""})
        cls.env.start()
        import lpbf_worker
        import lpbf_worker_rpc
        cls.w, cls.rpcmod = lpbf_worker, lpbf_worker_rpc
        cls.q = lpbf_worker.Queue(root=cls.tmp / "jobs")

    @classmethod
    def tearDownClass(cls):
        cls.q.close()
        cls.env.stop()

        def onerror(func, p, _exc):
            try:
                os.chmod(p, 0o666)
                func(p)
            except OSError:
                pass  # Windows may still hold the sqlite file for a moment; the temp dir is left behind
        shutil.rmtree(cls.tmp, onerror=onerror)

    def rpc(self, method, payload):
        try:
            return self.rpcmod.dispatch({"id": 1, "method": method, "payload": payload}, self.q, lambda q: {})
        except Exception as e:
            return self.w.rpc_error_response({"id": 1}, e)

    def wait(self, jid, limit=120):
        t = time.monotonic()
        while time.monotonic() - t < limit:
            g = self.rpc("get", jid)
            if g.get("status") not in ("queued", "running"):
                return g
            time.sleep(0.2)
        self.fail("job did not finish")

    def jobs_count(self):
        with sqlite3.connect(self.tmp / "jobs" / "queue.sqlite") as c:
            return c.execute("SELECT count(*) FROM jobs").fetchone()[0]

    def freeze_payload(self, conds, label="Synthetic worker block"):
        md = tub.metadata(blockLabel=label)
        raw = tub.inputs_csv(conds)
        pv = self.rpc("estimate", {"jobType": "user-blind-preview", "schema": tub.S, "metadata": md,
                                   "inputsCsvBase64": tub.b64(raw), "inputsFileName": "inputs.csv"})
        return {"jobType": "user-blind-freeze", "schema": tub.S, "metadata": md, "inputsCsvBase64": tub.b64(raw),
                "inputsFileName": "inputs.csv", "previewSha256": pv["previewSha256"],
                "overlapSha256": pv["overlapSha256"],
                "acknowledgements": {a: True for a in pv["acknowledgementsRequired"]}}

    def scan(self, jid, text_extra=""):
        folder = self.tmp / "jobs" / jid
        log = (folder / "progress.log").read_text(errors="replace")
        with sqlite3.connect(self.tmp / "jobs" / "queue.sqlite") as c:
            row = c.execute("SELECT log, error FROM jobs WHERE id=?", (jid,)).fetchone()
        blob = log + str(row[0]) + str(row[1]) + json.dumps(self.rpc("get", jid)) + text_extra
        self.assertNotIn(SENTINEL, blob)
        self.assertNotIn("4321.9", blob)
        for line in log.splitlines():
            obj = json.loads(line)
            self.assertIn(set(obj), ({"blindProgress"}, {"blindError"}))

    def test_full_flow_validation_leak_scan_gates_and_rpc_reads(self):
        conds = tub.conditions()
        n0 = self.jobs_count()
        bad = self.rpc("submit", {**self.freeze_payload(conds), "acknowledgements": {}})
        self.assertEqual(bad["errorKind"], "validation")
        self.assertEqual(bad["validation"]["error"]["code"], "ACK_REQUIRED")
        bad = self.rpc("submit", {**self.freeze_payload(conds), "extraKey": 1})
        self.assertEqual(bad["validation"]["error"]["code"], "METADATA_FIELD")
        self.assertEqual(self.jobs_count(), n0)                      # no job row for a refusal
        j = self.rpc("submit", self.freeze_payload(conds))
        p = json.loads((self.tmp / "jobs" / j["id"] / "input.json").read_text())
        self.assertNotIn("inputsCsvBase64", p)
        self.assertNotIn("metadata", p)
        self.assertEqual(p["timeout_s"], 180.0)
        g = self.wait(j["id"])
        self.assertEqual(g["status"], "completed", g.get("error"))
        self.assertEqual(g["requestSummary"], {"jobType": "user-blind-freeze", "schema": tub.S, "freezeKey": None})
        self.scan(j["id"])
        key = g["result"]["freezeKey"]
        again = self.rpc("submit-repeat", self.freeze_payload(conds))
        self.assertNotEqual(again["id"], j["id"])                     # blind mutations never deduplicated
        self.assertEqual(self.wait(again["id"])["result"]["alreadyFrozen"], True)
        # artifact gate
        r = self.rpc("artifact", {"id": j["id"], "name": "blind-freeze.json"})
        self.assertEqual(r["validation"]["error"]["code"], "REVEAL_REQUIRED")
        r = self.rpc("artifact", {"id": j["id"], "name": "thermal-history.csv"})
        self.assertIn("error", r)
        rec = self.rpc("artifact", {"id": j["id"], "name": "blind-receipt.json"})
        self.assertNotIn(SENTINEL, base64.b64decode(rec["content"]).decode())
        self.assertIn("Blind tests are not archivable", self.rpc("capture", j["id"])["error"])
        self.assertIsNone(self.w._archive_run_kind("user-blind-freeze"))
        # write-free reads: 100 polls create no job and no folder
        folders = len(list((self.tmp / "jobs").iterdir()))
        rows = self.jobs_count()
        t = time.monotonic()
        for _ in range(50):
            self.rpc("estimate", {"jobType": "user-blind-list", "schema": tub.S})
            self.rpc("estimate", {"jobType": "user-blind-get", "schema": tub.S, "freezeKey": key})
        per_call = (time.monotonic() - t) / 100
        self.assertEqual(len(list((self.tmp / "jobs").iterdir())), folders)
        self.assertEqual(self.jobs_count(), rows)
        self.assertLess(per_call, 0.1)
        # score through the queue, report served from the store with the hash the result declares
        tg = tub.b64(tub.targets_csv(conds))
        s = self.rpc("submit", {"jobType": "user-blind-score", "schema": tub.S, "freezeKey": key,
                                "targetsCsvBase64": tg, "targetsFileName": "targets.csv",
                                "declarations": {"viewedPredictionsBeforeFinalisingTargets": "no"},
                                "acceptCommitmentMismatch": False})
        g2 = self.wait(s["id"])
        self.assertEqual(g2["status"], "completed", g2.get("error"))
        self.scan(s["id"])
        rep = self.rpc("artifact", {"id": s["id"], "name": "blind-report.json"})
        import hashlib
        self.assertEqual(hashlib.sha256(base64.b64decode(rep["content"])).hexdigest(), g2["result"]["reportSha256"])
        got = self.rpc("estimate", {"jobType": "user-blind-get", "schema": tub.S, "freezeKey": key})
        self.assertIn("blind-freeze.json", [d["name"] for d in got["documents"]])
        self.assertNotIn(SENTINEL, json.dumps(got))
        # open job deduplicated
        o1 = self.rpc("submit", {"jobType": "user-blind-open", "schema": tub.S, "freezeKey": key,
                                 "name": "blind-report.json", "attempt": 1})
        self.wait(o1["id"])
        o2 = self.rpc("submit", {"jobType": "user-blind-open", "schema": tub.S, "freezeKey": key,
                                 "name": "blind-report.json", "attempt": 1})
        self.assertEqual(o1["id"], o2["id"])

    def test_solver_exception_with_sentinel_never_reaches_logs(self):
        with mock.patch.dict(os.environ, {"BLIND_TEST_STUB_RAISE": "1"}):
            conds = [(c[0], c[1] * 1.37, c[2], c[3]) for c in tub.conditions()]
            j = self.rpc("submit", self.freeze_payload(conds, "Raising synthetic block"))
            g = self.wait(j["id"])
        self.assertEqual(g["status"], "completed", g.get("error"))
        arms = {a["id"]: a for a in g["result"]["armsFrozen"]}
        self.assertEqual(arms["served"]["reasonCodes"], ["SERVED_EXCEPTION"])
        self.scan(j["id"])

    def test_failed_child_has_a_fixed_message(self):
        conds = [(c[0], c[1] * 1.53, c[2], c[3]) for c in tub.conditions()]
        payload = self.freeze_payload(conds, "Failing synthetic block")
        import lpbf_user_blind as ub
        staged = ub.stage_request(ub.validate_request(payload))
        staged["inputsSha256"] = "0" * 64                            # upload missing: the child must refuse
        job = os.urandom(16).hex()
        folder = self.tmp / "jobs" / job
        folder.mkdir()
        (folder / "input.json").write_text(json.dumps(staged))
        with self.q.connect() as c:
            c.execute("INSERT INTO jobs VALUES (?,?,?,?,?,?,?)", (job, "k" * 64, "queued", 0., "", None, time.time()))
        g = self.wait(job)
        self.assertEqual(g["status"], "failed")
        self.assertEqual(g["blindError"], "FREEZE_UNKNOWN")
        self.assertEqual(g["error"], tub.proto.REFUSALS["FREEZE_UNKNOWN"])


if __name__ == "__main__":
    unittest.main()
