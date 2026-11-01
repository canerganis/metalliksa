"""Kill every blind mutation at each step and check the store recovers with no manual action (spec 3.5 item 5).

A spawned child replaces the module-level fault hook `lpbf_user_blind_store._fault` (never an environment switch in
production code) with one that exits the process hard at the chosen step. The parent then runs the next mutation and
checks: every committed record has exactly one ledger event, no ledger event points to a missing record, the chain
verifies and the condition index equals the committed freezes. Native folder only; the drvfs (/mnt) variant under WSL
is not run here (spec phase 2 acceptance, recorded as not run on this machine). Synthetic data, stub solver.
"""
import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import test_lpbf_user_blind as tub

PY = Path(__file__).resolve().parent
STEPS = ("after-staging-write", "after-lock", "after-rename", "during-ledger-append", "after-ledger-append",
         "during-index-append")
CHILD = r"""
import base64, json, os, sys
sys.path.insert(0, sys.argv[1])
import lpbf_user_blind_store as store_mod
import lpbf_user_blind_freeze as ufreeze
import test_lpbf_user_blind as tub
ufreeze.served_arm = tub.stub_served_arm
ufreeze.FORBIDDEN_MODULES = ()
step, payload = sys.argv[2], json.loads(open(sys.argv[3]).read())
def fault(name):
    if name == step:
        os._exit(9)
store_mod._fault = fault
import lpbf_user_blind as ub
staged = ub.stage_request(ub.validate_request(payload))
folder = os.path.join(os.environ["METALLIKSA_JOB_ROOT"], "f" * 32)
os.makedirs(folder, exist_ok=True)
ub.run_job(staged, folder)
"""


def invariants(test, store):
    from lpbf_user_blind_store import Store
    st = Store(store)
    test.assertTrue(st.verify_chain()["ok"])
    ledger = st.ledger()
    committed = st.committed_records()
    for event, _key, rel in committed:
        n = [e for e in ledger if e.get("record") == rel]
        test.assertEqual(len(n), 1, rel)
        test.assertEqual(n[0]["event"], event)
    rels = {rel for _e, _k, rel in committed}
    for e in ledger:
        if e.get("record"):
            test.assertIn(e["record"], rels, "dangling ledger event")
    test.assertEqual(sorted(json.dumps(x, sort_keys=True) for x in (st.index_entries() or [])),
                     sorted(json.dumps(x, sort_keys=True) for x in st._derived_index()))


class CrashMatrix(tub.BlindCase):
    def _payloads(self):
        conds = tub.conditions()
        md, raw = tub.metadata(), tub.inputs_csv(conds)
        pv = self.preview(md, raw)
        freeze = {"jobType": "user-blind-freeze", "schema": tub.S, "metadata": md, "inputsCsvBase64": tub.b64(raw),
                  "inputsFileName": "inputs.csv", "previewSha256": pv["previewSha256"],
                  "overlapSha256": pv["overlapSha256"],
                  "acknowledgements": {a: True for a in pv["acknowledgementsRequired"]}}
        return conds, freeze

    def _kill(self, step, payload):
        p = self.tmp / "payload.json"
        p.write_text(json.dumps(payload))
        env = {**os.environ, "PYTHONPATH": str(PY)}
        out = subprocess.run([sys.executable, "-B", "-c", CHILD, str(PY), step, str(p)], env=env,
                             capture_output=True, text=True, timeout=120)
        return out.returncode

    def _next_mutation(self):
        """Any mutation triggers reconciliation under the lock: a fresh freeze of other synthetic inputs."""
        conds = [(c[0], c[1] * 1.21, c[2], c[3]) for c in tub.conditions()]
        self.freeze(md=tub.metadata(blockLabel="Recovery synthetic block"), conds=conds)

    def test_freeze_killed_at_each_step(self):
        for step in STEPS:
            with self.subTest(step=step):
                self.tearDown()
                self.setUp()
                _conds, freeze = self._payloads()
                rc = self._kill(step, freeze)
                self.assertEqual(rc, 9, step)
                self._next_mutation()
                invariants(self, self.tmp / "store")
                # A retry of the killed freeze succeeds (or finds its committed record) with no manual step.
                staged = tub.ub.stage_request(tub.ub.validate_request(dict(freeze)))
                d = self.tmp / "jobs" / ("e" * 32)
                d.mkdir(exist_ok=True)
                tub.ub.run_job(staged, d)
                invariants(self, self.tmp / "store")

    def test_reveal_score_and_bundle_killed_at_each_step(self):
        steps = [s for s in STEPS if s != "during-index-append"]   # only freezes append to the index
        for kind in ("reveal", "score", "bundle"):
            for step in steps:
                with self.subTest(kind=kind, step=step):
                    self.tearDown()
                    self.setUp()
                    conds, freeze = self._payloads()
                    rec = self.job(freeze)
                    key = rec["freezeKey"]
                    payload = {"reveal": {"jobType": "user-blind-reveal", "schema": tub.S, "freezeKey": key,
                                          "confirmation": tub.proto.REVEAL_PHRASE},
                               "score": {"jobType": "user-blind-score", "schema": tub.S, "freezeKey": key,
                                         "targetsCsvBase64": tub.b64(tub.targets_csv(conds)),
                                         "targetsFileName": "targets.csv",
                                         "declarations": {"viewedPredictionsBeforeFinalisingTargets": "no"},
                                         "acceptCommitmentMismatch": False},
                               "bundle": {"jobType": "user-blind-bundle", "schema": tub.S, "freezeKey": key,
                                          "revealConfirmation": tub.proto.REVEAL_PHRASE}}[kind]
                    self.assertEqual(self._kill(step, payload), 9)
                    self._next_mutation()
                    invariants(self, self.tmp / "store")
                    self.job(payload)                                 # the retried mutation succeeds
                    invariants(self, self.tmp / "store")


if __name__ == "__main__":
    unittest.main()
