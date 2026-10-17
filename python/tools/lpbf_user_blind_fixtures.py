#!/usr/bin/env python3
"""Regenerate the synthetic TypeScript fixtures of the user blind test (tests/fixtures/lpbf-user-blind-*.SYNTHETIC.json).

Synthetic data only: 12 invented Ti-6Al-4V conditions with invented depths from a closed formula, no measurement. The
documents are produced by the real Python code path in a temporary store, so the TypeScript validators are checked
against what Python writes. Prints file names only.
"""
from __future__ import annotations

import base64
import json
import os
import sys
import tempfile
from pathlib import Path

PY = Path(__file__).resolve().parents[1]
REPO = PY.parent
sys.path.insert(0, str(PY))
OUT = REPO / "tests" / "fixtures"
TITLE = "Synthetic fixture, not measured data"


def synthetic_files():
    inputs = ["condition_id,track_id,power_W,speed_mm_s,spot_um"]
    targets = ["condition_id,track_id,depth_um,width_um"]
    i = 0
    for P in (120, 200, 300, 400):
        for v in (400, 800, 1400):
            i += 1
            for t in (1, 2, 3):
                inputs.append(f"c{i},c{i}t{t},{P},{v},80")
                targets.append(f"c{i},c{i}t{t},{20 + P * P / v / 2 + t:.1f},{90 + t}")
    md = json.loads((REPO / "data" / "blind" / "templates" / "blind_metadata_v1.json").read_text(encoding="utf-8"))
    md["blockLabel"] = "Synthetic fixture block"
    md["replication"]["tracksPerCondition"] = 3
    return md, ("\n".join(inputs) + "\n").encode(), ("\n".join(targets) + "\n").encode()


def main():
    tmp = Path(tempfile.mkdtemp(prefix="blind-fixtures-"))
    os.environ["METALLIKSA_USER_BLIND_ROOT"] = str(tmp / "store")
    os.environ["METALLIKSA_JOB_ROOT"] = str(tmp / "jobs")
    import lpbf_user_blind as ub
    from lpbf_user_blind_protocol import REQUEST_SCHEMA as S, REVEAL_PHRASE
    md, inputs, targets = synthetic_files()
    b64 = base64.b64encode(inputs).decode()
    preview = ub.rpc({"jobType": "user-blind-preview", "schema": S, "metadata": md, "inputsCsvBase64": b64,
                      "inputsFileName": "inputs.csv"})

    def job(p):
        staged = ub.stage_request(ub.validate_request(p))
        folder = tmp / "jobs" / os.urandom(16).hex()
        folder.mkdir(parents=True)
        return ub.run_job(staged, folder)

    receipt = job({"jobType": "user-blind-freeze", "schema": S, "metadata": md, "inputsCsvBase64": b64,
                   "inputsFileName": "inputs.csv", "previewSha256": preview["previewSha256"],
                   "overlapSha256": preview["overlapSha256"],
                   "acknowledgements": {a: True for a in preview["acknowledgementsRequired"]}})
    key = receipt["freezeKey"]
    score = job({"jobType": "user-blind-score", "schema": S, "freezeKey": key,
                 "targetsCsvBase64": base64.b64encode(targets).decode(), "targetsFileName": "targets.csv",
                 "declarations": {"viewedPredictionsBeforeFinalisingTargets": "no"}, "acceptCommitmentMismatch": False})
    store = ub.Store()
    report = json.loads(store.read_record(store.record_dir(key, "score", 1), "score.json"))
    reveal = job({"jobType": "user-blind-reveal", "schema": S, "freezeKey": key, "confirmation": REVEAL_PHRASE})
    lst = ub.rpc({"jobType": "user-blind-list", "schema": S})
    got = ub.rpc({"jobType": "user-blind-get", "schema": S, "freezeKey": key})
    docs = {"preview": preview, "receipt": receipt, "score-result": score, "report": report, "reveal-result": reveal,
            "list": lst, "get": got}
    OUT.mkdir(parents=True, exist_ok=True)
    for name, doc in docs.items():
        path = OUT / f"lpbf-user-blind-{name}.SYNTHETIC.json"
        path.write_text(json.dumps({"_title": TITLE, "document": doc}, indent=1, sort_keys=True) + "\n",
                        encoding="utf-8", newline="\n")
        print(path.relative_to(REPO).as_posix())


if __name__ == "__main__":
    main()
