"""Facade of the user blind test for the LPBF worker (spec 3.2, 3.2.1).

  * `USER_BLIND_RPC_TYPES` (estimate RPC, write free, solver free) and `USER_BLIND_JOB_TYPES` (queued, one child per job).
  * `validate_request(raw)`: closed payload per type; `BlindRefusal` (HTTP 422 through `rpc_error_response`).
  * `stage_request(p)`: submit-side checks, then every user document is staged in the blind store by hash; the job's
    `input.json` holds hashes only.
  * `run_job(input, folder)`: the child body. Silent by construction (descriptors 1 and 2 go to devnull, warnings are
    dropped); the only log lines are the two closed frames of `emit_progress` and `emit_error`.
  * `enforce_user_blind_job_result`: closed result keys, honesty literals, no predicted value in a job result.
  * `filter_blind_log`: keeps only the two closed frames.
  * `blind_document(result, name)`: the artifact branch, state gated (reveal or score before predictions are served).

Lazy imports per job type keep the freeze path free of the targets parser and the scorer.
"""
from __future__ import annotations

import io
import json
import math
import os
import re
import sys
import tarfile

from lpbf_user_blind_protocol import (
    ACKNOWLEDGEMENTS, ARTIFACT_NAMES, BUNDLE_SCHEMA, GET_SCHEMA, HONESTY, JOB_TIMEOUT_S, JOB_TYPES, LIST_SCHEMA,
    REQUEST_SCHEMA, REVEAL_PHRASE, REVEAL_SCHEMA, RPC_TYPES, BlindRefusal, canonical_bytes, canonical_sha256,
)
from lpbf_user_blind_store import Store, read_only, sha256_bytes, shared_host

USER_BLIND_RPC_TYPES = frozenset(RPC_TYPES)
USER_BLIND_JOB_TYPES = frozenset(JOB_TYPES)
BLIND_SUBMIT_ERROR_CODES = ("BLIND_SUBMIT_INTERNAL",)
BLIND_CHILD_ERROR_CODES = ("PREVIEW_DRIFT", "ACK_REQUIRED", "OVERLAP_CHANGED", "PREDICTOR_NOT_PINNED",
                           "PROTOCOL_CHANGED", "FREEZE_ALTERED", "FREEZE_UNKNOWN", "REVEAL_REQUIRED",
                           "STORE_READ_ONLY", "STORE_FULL", "STORE_LOCKED", "STORE_SHARED_HOST", "STORE_LOCK_DOMAIN",
                           "DOCUMENT_UNAVAILABLE", "SOLVER_EXCEPTION", "INTERNAL_ERROR")
PROGRESS_STAGES = ("predict", "score", "reveal", "bundle", "open")
_HEX = re.compile(r"^[0-9a-f]{64}$")

PAYLOADS = {
    "user-blind-preview": {"required": ("jobType", "schema", "metadata", "inputsCsvBase64", "inputsFileName"),
                           "optional": ()},
    "user-blind-list": {"required": ("jobType", "schema"), "optional": ("page", "pageSize")},
    "user-blind-get": {"required": ("jobType", "schema", "freezeKey"), "optional": ()},
    "user-blind-freeze": {"required": ("jobType", "schema", "metadata", "inputsCsvBase64", "inputsFileName",
                                       "previewSha256", "overlapSha256", "acknowledgements"), "optional": ()},
    "user-blind-reveal": {"required": ("jobType", "schema", "freezeKey", "confirmation"), "optional": ()},
    "user-blind-score": {"required": ("jobType", "schema", "freezeKey", "targetsCsvBase64", "targetsFileName",
                                      "declarations", "acceptCommitmentMismatch"), "optional": ()},
    "user-blind-bundle": {"required": ("jobType", "schema", "freezeKey"), "optional": ("revealConfirmation",)},
    "user-blind-open": {"required": ("jobType", "schema", "freezeKey", "name"), "optional": ("attempt",)},
}


def _store():
    return Store()


def _field_error(message, field):
    return BlindRefusal("METADATA_FIELD", field=field, message=message, detail={"field": field})


def validate_request(raw):
    """Closed payload of one request type (spec 3.2.1). Returns a shallow copy."""
    if not isinstance(raw, dict):
        raise _field_error("The request must be an object.", "request")
    jt = raw.get("jobType")
    if jt not in PAYLOADS:
        raise _field_error("Unknown blind request type.", "jobType")
    shape = PAYLOADS[jt]
    for k in raw:
        if k not in shape["required"] and k not in shape["optional"]:
            raise _field_error(f"Unknown metadata field '{k}'.", k)
    for k in shape["required"]:
        if k not in raw:
            raise _field_error(f"Missing required field '{k}'.", k)
    if raw["schema"] != REQUEST_SCHEMA:
        raise _field_error(f"Field 'schema' has a value this form does not accept ({REQUEST_SCHEMA}).", "schema")
    if "freezeKey" in raw and (not isinstance(raw["freezeKey"], str) or not _HEX.match(raw["freezeKey"])):
        raise BlindRefusal("FREEZE_UNKNOWN", field="freezeKey")
    for h in ("previewSha256", "overlapSha256"):
        if h in raw and (not isinstance(raw[h], str) or not _HEX.match(raw[h])):
            raise _field_error(f"Field '{h}' has a value this form does not accept (64 lower-case hex).", h)
    if jt == "user-blind-list":
        for k, lo, hi in (("page", 0, 10_000), ("pageSize", 1, 50)):
            if k in raw and (type(raw[k]) is not int or not lo <= raw[k] <= hi):
                raise _field_error(f"Field '{k}' has a value this form does not accept ({lo} to {hi}).", k)
    if jt == "user-blind-freeze":
        acks = raw["acknowledgements"]
        if not isinstance(acks, dict) or any(k not in ACKNOWLEDGEMENTS or acks[k] is not True for k in acks):
            raise _field_error("Field 'acknowledgements' has a value this form does not accept (true flags of the "
                               "listed names).", "acknowledgements")
    if jt == "user-blind-reveal" and not isinstance(raw["confirmation"], str):
        raise BlindRefusal("CONFIRMATION_PHRASE", field="confirmation")
    if jt == "user-blind-bundle" and "revealConfirmation" in raw and not isinstance(raw["revealConfirmation"], str):
        raise BlindRefusal("CONFIRMATION_PHRASE", field="revealConfirmation")
    if jt == "user-blind-score":
        d = raw["declarations"]
        if (not isinstance(d, dict) or set(d) != {"viewedPredictionsBeforeFinalisingTargets"}
                or d["viewedPredictionsBeforeFinalisingTargets"] not in ("no", "yes", "unsure")):
            raise _field_error("Field 'declarations' has a value this form does not accept "
                               "(viewedPredictionsBeforeFinalisingTargets: no, yes or unsure).", "declarations")
        if type(raw["acceptCommitmentMismatch"]) is not bool:
            raise _field_error("Field 'acceptCommitmentMismatch' has a value this form does not accept (true or "
                               "false).", "acceptCommitmentMismatch")
    if jt == "user-blind-open":
        if raw["name"] not in ARTIFACT_NAMES:
            raise _field_error("Field 'name' has a value this form does not accept.", "name")
        if "attempt" in raw and (type(raw["attempt"]) is not int or raw["attempt"] < 1):
            raise _field_error("Field 'attempt' has a value this form does not accept (1 or more).", "attempt")
    return dict(raw)


# ---------------------------------------------------------------------------------------------- estimate RPC
def rpc(raw, job_root=None):
    p = validate_request(raw)
    jt = p["jobType"]
    if jt not in USER_BLIND_RPC_TYPES:
        raise _field_error("This request type is queued, not an estimate.", "jobType")
    store = _store()
    if jt == "user-blind-preview":
        from lpbf_user_blind_preview import build_preview
        preview, _ctx = build_preview(store, p["metadata"], p["inputsCsvBase64"], p["inputsFileName"])
        return preview
    if jt == "user-blind-list":
        return list_tests(store, p.get("page", 0), p.get("pageSize", 20))
    return get_test(store, p["freezeKey"], job_root)


def _freeze_doc(store, key):
    d = store.freeze_dir(key)
    return json.loads(store.read_record(d, "freeze.json"))


def _score_doc(store, key, n):
    return json.loads(store.read_record(store.record_dir(key, "score", n), "score.json"))


def list_tests(store, page=0, page_size=20):
    info = store.info() or {}
    keys = store.freeze_keys()
    entries = []
    for key in keys:
        try:
            doc = _freeze_doc(store, key)
        except (BlindRefusal, ValueError, OSError):
            entries.append({"freezeKey": key, "state": "unreadable"})
            continue
        scores = store.numbered(key, "score")
        latest = None
        if scores:
            try:
                rep = _score_doc(store, key, scores[-1])
                latest = {"served": rep["arms"]["served"]["status"], "blindness": rep["blindness"]["status"]}
            except (BlindRefusal, ValueError, OSError, KeyError):
                latest = None
        state = "scored" if scores else ("revealed" if store.numbered(key, "reveal") else "frozen")
        entries.append({"freezeKey": key, "blockLabel": doc["metadata"]["blockLabel"], "alloy": doc["metadata"]["alloy"],
                        "createdAt": doc["createdAt"], "counts": doc["counts"], "state": state,
                        "attempts": len(scores), "latestStatus": latest})
    entries.sort(key=lambda e: e.get("createdAt") or "", reverse=True)
    start = page * page_size
    chain = store.verify_chain()
    return {"schema": LIST_SCHEMA, "entries": entries[start:start + page_size], "total": len(entries), "page": page,
            "readOnly": read_only(), "sharedHost": shared_host(), "storeId": info.get("storeId"),
            "lockDomain": info.get("lockDomain"), "ledgerOk": chain["ok"],
            "incompleteStaging": len(store.incomplete_staging()) if store.root.is_dir() else 0, "honesty": HONESTY}


def _job_present(job_root, job_id):
    if not job_root or not isinstance(job_id, str) or not re.fullmatch(r"[0-9a-f]{32}", job_id):
        return False
    return (os.path.join(str(job_root), job_id, "result.json") and
            os.path.isfile(os.path.join(str(job_root), job_id, "result.json")))


def get_test(store, key, job_root=None):
    doc = _freeze_doc(store, key)
    ledger = [e for e in store.ledger() if e.get("freezeKey") == key]
    job_of = {e.get("record"): e.get("jobId") for e in ledger}
    from lpbf_user_blind_freeze import receipt
    rec = receipt(doc, store)
    docs = []
    freeze_job = job_of.get(f"freezes/{key}")
    docs.append({"name": "blind-receipt.json", "attempt": None, "jobId": freeze_job,
                 "jobRecordPresent": _job_present(job_root, freeze_job)})
    gate = store.reveal_or_score_exists(key)
    if gate:
        docs.append({"name": "blind-freeze.json", "attempt": None, "jobId": freeze_job,
                     "jobRecordPresent": _job_present(job_root, freeze_job)})
    attempts = []
    for n in store.numbered(key, "score"):
        d = store.record_dir(key, "score", n)
        jid = job_of.get(f"freezes/{key}/score-{n}")
        try:
            rep_bytes = store.read_record(d, "score.json")
            rep = json.loads(rep_bytes)
            csv_bytes = store.read_record(d, "comparison.csv")
        except (BlindRefusal, ValueError, OSError):
            attempts.append({"n": n, "state": "unreadable"})
            continue
        attempts.append({"n": n, "targetsSha256": rep["targetsSha256"], "blindness": rep["blindness"]["status"],
                         "statuses": {a: v["status"] for a, v in rep["arms"].items()},
                         "reportSha256": sha256_bytes(rep_bytes)})
        for name, data in (("blind-report.json", rep_bytes), ("blind-comparison.csv", csv_bytes)):
            docs.append({"name": name, "attempt": n, "sha256": sha256_bytes(data), "size": len(data), "jobId": jid,
                         "jobRecordPresent": _job_present(job_root, jid)})
    for n in store.numbered(key, "bundle"):
        d = store.record_dir(key, "bundle", n)
        jid = job_of.get(f"freezes/{key}/bundles/bundle-{n}")
        try:
            data = store.read_record(d, "bundle.tar")
        except (BlindRefusal, OSError):
            continue
        docs.append({"name": "blind-bundle.tar", "attempt": n, "sha256": sha256_bytes(data), "size": len(data),
                     "jobId": jid, "jobRecordPresent": _job_present(job_root, jid)})
    reveals = [{"seq": e["seq"], "at": e["at"], "jobId": e.get("jobId")} for e in ledger if e.get("event") == "revealed"]
    return {"schema": GET_SCHEMA, "freezeKey": key, "receipt": rec, "revealEvents": reveals, "attempts": attempts,
            "documents": docs, "readOnly": read_only(), "sharedHost": shared_host(), "honesty": HONESTY}


# ---------------------------------------------------------------------------------------------- submit staging
def stage_request(p, store=None):
    """Submit side (worker main process). Returns the hashes-only job input. Raises BlindRefusal."""
    store = store or _store()
    jt = p["jobType"]
    if jt not in USER_BLIND_JOB_TYPES:
        raise _field_error("This request type is an estimate, not a job.", "jobType")
    store.check_mutation_allowed()
    base = {"jobType": jt, "schema": REQUEST_SCHEMA, "timeout_s": JOB_TIMEOUT_S[jt]}
    if jt == "user-blind-freeze":
        from lpbf_user_blind_freeze import check_submit
        if "research" in p:
            raise _field_error("Unknown metadata field 'research'.", "research")
        preview, ctx = check_submit(store, p)
        store.check_caps(len(ctx["inputsBytes"]) + len(ctx["metadataBytes"]))
        with store.lock():
            md_sha = store.put_upload(ctx["metadataBytes"], "metadata.json")
            in_sha = store.put_upload(ctx["inputsBytes"], "inputs.csv")
        return {**base, "metadataSha256": md_sha, "inputsSha256": in_sha, "inputsFileName": p["inputsFileName"],
                "previewSha256": p["previewSha256"], "overlapSha256": p["overlapSha256"],
                "acknowledgements": dict(p["acknowledgements"])}
    key = p["freezeKey"]
    if not (store.freeze_dir(key) / "freeze.json").is_file():
        raise BlindRefusal("FREEZE_UNKNOWN", field="freezeKey")
    if jt == "user-blind-reveal":
        if p["confirmation"] != REVEAL_PHRASE:
            raise BlindRefusal("CONFIRMATION_PHRASE", field="confirmation")
        return {**base, "freezeKey": key}
    if jt == "user-blind-bundle":
        confirm = p.get("revealConfirmation")
        if confirm is not None and confirm != REVEAL_PHRASE:
            raise BlindRefusal("CONFIRMATION_PHRASE", field="revealConfirmation")
        if confirm is None and not store.reveal_or_score_exists(key):
            raise BlindRefusal("REVEAL_REQUIRED")
        return {**base, "freezeKey": key, "revealConfirmed": confirm is not None}
    if jt == "user-blind-open":
        out = {**base, "freezeKey": key, "name": p["name"], "attempt": p.get("attempt")}
        _resolve_document(store, out, p["name"])
        return out
    # score
    from lpbf_user_blind_inputs import check_file_name, decode_upload
    from lpbf_user_blind_score import load_freeze
    from lpbf_user_blind_targets import parse_targets
    check_file_name(p["targetsFileName"], "targetsFileName")
    raw = decode_upload(p["targetsCsvBase64"], "targetsCsvBase64")
    targets_sha = sha256_bytes(raw)
    freeze, _ = load_freeze(store, key)
    try:
        parse_targets(raw, freeze)
        commit = freeze["metadata"].get("targetCommitment")
        if commit is not None and commit["sha256"] != targets_sha:
            if not p["acceptCommitmentMismatch"]:
                raise BlindRefusal("COMMITMENT_MISMATCH", field="targetsCsvBase64")
    except BlindRefusal as refusal:
        try:
            with store.lock():
                store.append("score-refused", freeze_key=key, hashes={"targets": targets_sha},
                             extra={"code": refusal.code})
        except BlindRefusal:
            pass
        raise
    with store.lock():
        if commit is not None and commit["sha256"] != targets_sha:
            store.append("commitment-mismatch", freeze_key=key, hashes={"targets": targets_sha})
        store.put_upload(raw, "targets.csv")
    return {**base, "freezeKey": key, "targetsSha256": targets_sha, "targetsFileName": p["targetsFileName"],
            "declarations": dict(p["declarations"]), "acceptCommitmentMismatch": p["acceptCommitmentMismatch"]}


def job_cache_key(p):
    return canonical_sha256(p)


# ---------------------------------------------------------------------------------------------- child (silent)
_LOG_FD = None


def _frame(obj):
    if _LOG_FD is None:
        return
    os.write(_LOG_FD, json.dumps(obj, separators=(",", ":")).encode("ascii") + b"\n")


def emit_progress(stage, k, n):
    if stage in PROGRESS_STAGES and type(k) is int and type(n) is int:
        _frame({"blindProgress": {"stage": stage, "k": k, "n": n}})


def emit_error(code):
    _frame({"blindError": code if code in BLIND_CHILD_ERROR_CODES else "INTERNAL_ERROR"})


def silence():
    """Redirect descriptors 1 and 2 to devnull for the whole job; keep a saved copy for the closed frames."""
    global _LOG_FD
    import warnings
    sys.stdout.flush()
    sys.stderr.flush()
    _LOG_FD = os.dup(1)
    devnull = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull, 1)
    os.dup2(devnull, 2)
    os.close(devnull)
    warnings.simplefilter("ignore")


def run_job(input_data, folder):
    """Child body. Returns the job result (no predicted value). Raises BlindRefusal for a closed child code."""
    from pathlib import Path
    job_id = Path(folder).name
    store = _store()
    jt = input_data["jobType"]
    job = {**input_data, "jobId": job_id}
    if jt == "user-blind-freeze":
        from lpbf_user_blind_freeze import run_freeze
        rec = run_freeze(store, job, progress=lambda k, n: emit_progress("predict", k, n))
        return {**rec, "documents": [{"name": "blind-receipt.json", "attempt": None}], "provenance": {}}
    if jt == "user-blind-reveal":
        return {**reveal(store, job["freezeKey"], job_id, via="reveal"), "provenance": {}}
    if jt == "user-blind-score":
        return {**run_score(store, job), "provenance": {}}
    if jt == "user-blind-bundle":
        return {**run_bundle(store, job), "provenance": {}}
    if jt == "user-blind-open":
        doc = _resolve_document(store, job, job["name"])
        return {"freezeKey": job["freezeKey"], "name": job["name"], "attempt": doc["attempt"], "sha256": doc["sha256"],
                "size": doc["size"], "honesty": HONESTY, "provenance": {}}
    raise BlindRefusal("INTERNAL_ERROR")


def reveal(store, key, job_id, via):
    with store.lock():
        n = (store.numbered(key, "reveal") or [0])[-1] + 1
        scores_before = len(store.numbered(key, "score"))
        from lpbf_user_blind_store import now_iso
        doc = {"schema": REVEAL_SCHEMA, "freezeKey": key, "revealedAt": now_iso(), "scoreAttemptsBefore": scores_before,
               "via": via, "jobId": job_id}
        data = canonical_bytes(doc)
        staging = store.stage({"reveal.json": data})
        store.commit(staging, store.record_dir(key, "reveal", n))
        entry = store.append("revealed", freeze_key=key, job_id=job_id, record=f"freezes/{key}/reveal-{n}",
                             hashes={"reveal": sha256_bytes(data)})
    emit_progress("reveal", 1, 1)
    return {"freezeKey": key, "revealN": n, "ledgerSeq": entry["seq"],
            "documents": [{"name": "blind-freeze.json", "attempt": None}], "honesty": HONESTY}


def run_score(store, job):
    from lpbf_user_blind_score import comparison_csv, load_freeze, score
    key = job["freezeKey"]
    freeze, freeze_bytes = load_freeze(store, key)
    targets = store.get_upload(job["targetsSha256"], "targets.csv")
    commit = freeze["metadata"].get("targetCommitment")
    matched = None if commit is None else commit["sha256"] == job["targetsSha256"]
    if matched is False and not job["acceptCommitmentMismatch"]:
        raise BlindRefusal("COMMITMENT_MISMATCH")
    ledger = store.ledger()
    frozen_entry = next((e for e in ledger if e.get("event") == "frozen" and e.get("freezeKey") == key), None)
    earlier = []
    for n in store.numbered(key, "score"):
        earlier.append(_score_doc(store, key, n)["targetsSha256"])
    if job["targetsSha256"] in earlier:
        n = earlier.index(job["targetsSha256"]) + 1
        return _score_result(store, key, n, already=True)
    emit_progress("score", 0, 1)
    report = score(store, job, freeze, freeze_bytes, targets, job["targetsSha256"], matched, len(earlier) + 1,
                   earlier, frozen_entry, ledger)
    with store.lock():
        earlier_now = [_score_doc(store, key, n)["targetsSha256"] for n in store.numbered(key, "score")]
        if job["targetsSha256"] in earlier_now:
            return _score_result(store, key, earlier_now.index(job["targetsSha256"]) + 1, already=True)
        n = len(earlier_now) + 1
        if n != report["attempt"]["n"]:
            report = score(store, job, freeze, freeze_bytes, targets, job["targetsSha256"], matched, n, earlier_now,
                           frozen_entry, store.ledger())
        rep_bytes = canonical_bytes(report)
        csv_bytes = comparison_csv(report, sha256_bytes(rep_bytes))
        staging = store.stage({"score.json": rep_bytes, "comparison.csv": csv_bytes})
        store.commit(staging, store.record_dir(key, "score", n))
        store.append("scored", freeze_key=key, job_id=job["jobId"], record=f"freezes/{key}/score-{n}",
                     hashes={"report": sha256_bytes(rep_bytes), "targets": job["targetsSha256"],
                             "comparison": sha256_bytes(csv_bytes)})
    emit_progress("score", 1, 1)
    return _score_result(store, key, n, already=False)


def _score_result(store, key, n, already):
    d = store.record_dir(key, "score", n)
    rep_bytes = store.read_record(d, "score.json")
    rep = json.loads(rep_bytes)
    return {"freezeKey": key, "attempt": n, "alreadyScored": already, "reportSha256": sha256_bytes(rep_bytes),
            "statuses": {"blindness": rep["blindness"]["status"],
                         **{a: v["status"] for a, v in rep["arms"].items()}},
            "documents": [{"name": "blind-report.json", "attempt": n}, {"name": "blind-comparison.csv", "attempt": n}],
            "honesty": HONESTY}


def _tar_bytes(members):
    """Deterministic tar: sorted names, mtime 0, uid and gid 0, mode 0644."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.USTAR_FORMAT) as tar:
        for name in sorted(members):
            data = members[name]
            info = tarfile.TarInfo(name)
            info.size, info.mtime, info.uid, info.gid, info.mode = len(data), 0, 0, 0, 0o644
            info.uname = info.gname = ""
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def bundle_members(store, key):
    d = store.freeze_dir(key)
    freeze_bytes = store.read_record(d, "freeze.json")
    freeze = json.loads(freeze_bytes)
    members = {"freeze.json": freeze_bytes, "freeze.json.sha256": (sha256_bytes(freeze_bytes) + "\n").encode(),
               "metadata.json": store.get_upload(freeze["metadataSha256"], "metadata.json"),
               "inputs.csv": store.get_upload(freeze["inputsSha256"], "inputs.csv")}
    for n in store.numbered(key, "reveal"):
        b = store.read_record(store.record_dir(key, "reveal", n), "reveal.json")
        members[f"reveal-{n}.json"] = b
    for n in store.numbered(key, "score"):
        sd = store.record_dir(key, "score", n)
        b = store.read_record(sd, "score.json")
        rep = json.loads(b)
        members[f"score-{n}.json"] = b
        members[f"comparison-{n}.csv"] = store.read_record(sd, "comparison.csv")
        members[f"targets-{n}.csv"] = store.get_upload(rep["targetsSha256"], "targets.csv")
    lines = [canonical_bytes(e) + b"\n" for e in store.ledger() if e.get("freezeKey") == key]
    members["ledger-excerpt.jsonl"] = b"".join(lines)
    manifest = {"schema": BUNDLE_SCHEMA, "freezeKey": key,
                "files": [{"name": k, "sha256": sha256_bytes(v), "size": len(v)} for k, v in sorted(members.items())],
                "honesty": HONESTY,
                "note": ("Local export. It holds your measurements and the frozen predictions. The ledger excerpt "
                         "lists this test's events only.")}
    members["bundle-manifest.json"] = canonical_bytes(manifest)
    return members


def run_bundle(store, job):
    key = job["freezeKey"]
    if not store.reveal_or_score_exists(key):
        if not job.get("revealConfirmed"):
            raise BlindRefusal("REVEAL_REQUIRED")
        reveal(store, key, job["jobId"], via="bundle")
    emit_progress("bundle", 0, 1)
    data = _tar_bytes(bundle_members(store, key))
    with store.lock():
        n = (store.numbered(key, "bundle") or [0])[-1] + 1
        staging = store.stage({"bundle.tar": data})
        store.commit(staging, store.record_dir(key, "bundle", n))
        store.append("bundle-exported", freeze_key=key, job_id=job["jobId"],
                     record=f"freezes/{key}/bundles/bundle-{n}", hashes={"bundle": sha256_bytes(data)})
    emit_progress("bundle", 1, 1)
    return {"freezeKey": key, "bundleN": n, "sha256": sha256_bytes(data), "size": len(data),
            "documents": [{"name": "blind-bundle.tar", "attempt": n}], "honesty": HONESTY}


# ---------------------------------------------------------------------------------------------- documents
def _resolve_document(store, result, name):
    """Bytes and identity of one served document, through the reveal-or-score gate."""
    key = result["freezeKey"]
    if name == "blind-receipt.json":
        from lpbf_user_blind_freeze import receipt
        data = canonical_bytes(receipt(_freeze_doc(store, key), store))
        return {"data": data, "sha256": sha256_bytes(data), "size": len(data), "attempt": None,
                "type": "application/json"}
    if name in ("blind-freeze.json", "blind-bundle.tar") and not store.reveal_or_score_exists(key):
        raise BlindRefusal("REVEAL_REQUIRED")
    if name == "blind-freeze.json":
        data = store.read_record(store.freeze_dir(key), "freeze.json")
        return {"data": data, "sha256": sha256_bytes(data), "size": len(data), "attempt": None,
                "type": "application/json"}
    prefix, fname, ctype = {"blind-report.json": ("score", "score.json", "application/json"),
                            "blind-comparison.csv": ("score", "comparison.csv", "text/csv"),
                            "blind-bundle.tar": ("bundle", "bundle.tar", "application/x-tar")}[name]
    numbers = store.numbered(key, prefix)
    n = result.get("attempt") if prefix == "score" else result.get("bundleN", result.get("attempt"))
    if n is None:
        n = numbers[-1] if numbers else None
    if n not in numbers:
        raise BlindRefusal("DOCUMENT_UNAVAILABLE")
    data = store.read_record(store.record_dir(key, prefix, n), fname)
    return {"data": data, "sha256": sha256_bytes(data), "size": len(data), "attempt": n, "type": ctype}


def blind_document(result, name, job_type):
    """Artifact branch for a completed blind job. `result` is the validated job result."""
    if name not in ARTIFACT_NAMES:
        raise ValueError("Artifact unavailable")
    if job_type == "user-blind-open" and name != result.get("name"):
        raise ValueError("Artifact unavailable")
    doc = _resolve_document(_store(), result, name)
    if job_type == "user-blind-open" and doc["sha256"] != result.get("sha256"):
        raise ValueError("Artifact integrity failed")
    return doc


# ---------------------------------------------------------------------------------------------- enforcement
RESULT_KEYS = {
    "user-blind-freeze": None,  # the receipt keys plus documents and provenance
    "user-blind-reveal": {"freezeKey", "revealN", "ledgerSeq", "documents", "honesty", "provenance"},
    "user-blind-score": {"freezeKey", "attempt", "alreadyScored", "reportSha256", "statuses", "documents", "honesty",
                         "provenance"},
    "user-blind-bundle": {"freezeKey", "bundleN", "sha256", "size", "documents", "honesty", "provenance"},
    "user-blind-open": {"freezeKey", "name", "attempt", "sha256", "size", "honesty", "provenance"},
}
RECEIPT_KEYS = {"schema", "freezeKey", "freezeSha256", "predictionsSha256", "inputsSha256", "metadataSha256",
                "previewSha256", "targetCommitmentSha256", "createdAt", "alreadyFrozen", "blockLabel", "alloy", "counts",
                "acknowledgements", "excludedInputs", "designChecks", "grades", "blockIssues", "labels", "armsFrozen",
                "predictorIdentity", "scorerIdentity", "ledgerSeq", "ledgerEntryHash", "predictionsWithheld",
                "receiptLine", "anchorAdvice", "honesty", "documents", "provenance", "runKind"}
PREDICTION_KEYS = {"pred", "value_um", "depth_um", "width_um", "D_obs_um", "trackDepths_um", "ledger", "D_pred_um",
                   "rel"}


def _walk(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield path + "/" + str(k), k, v
            yield from _walk(v, path + "/" + str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _walk(v, f"{path}/{i}")


def _numbers(obj):
    for _p, _k, v in _walk(obj):
        if isinstance(v, float):
            yield v


def assert_no_prediction(obj, predicted=()):
    """Raise ValueError when a prediction-like key, or one of the frozen predicted numbers, is in `obj`."""
    for path, k, _v in _walk(obj):
        if k in PREDICTION_KEYS and "/predictorIdentity" not in path and "/scorerIdentity" not in path:
            raise ValueError(f"prediction-like key in a blind result ({k})")
    pset = {float(x) for x in predicted if isinstance(x, (int, float)) and math.isfinite(x)}
    if pset and any(v in pset for v in _numbers(obj)):
        raise ValueError("a frozen predicted value appears in a blind result")


def _predicted_values(key):
    try:
        doc = _freeze_doc(_store(), key)
    except Exception:
        return []
    out = []
    for c in doc["conditions"]:
        for v in c["pred"].values():
            for f in ("value_um", "width_um"):
                if isinstance(v.get(f), (int, float)):
                    out.append(v[f])
    return out


def enforce_user_blind_job_result(result, params):
    jt = params.get("jobType")
    if jt not in USER_BLIND_JOB_TYPES or not isinstance(result, dict):
        raise ValueError("blind job result has an unknown type")
    allowed = RECEIPT_KEYS if jt == "user-blind-freeze" else RESULT_KEYS[jt]
    extra = set(result) - allowed - {"runKind"}
    if extra:
        raise ValueError(f"blind job result has unknown keys {sorted(extra)}")
    if result.get("honesty") != HONESTY:
        raise ValueError("blind job result honesty literals differ")
    key = result.get("freezeKey")
    if not isinstance(key, str) or not _HEX.match(key):
        raise ValueError("blind job result has no freeze key")
    if jt in ("user-blind-reveal", "user-blind-score", "user-blind-bundle", "user-blind-open") and \
            key != params.get("freezeKey"):
        raise ValueError("blind job result names another freeze")
    assert_no_prediction(result, _predicted_values(key))
    return result


_FRAME_KEYS = ({"blindProgress"}, {"blindError"})


def filter_blind_log(text):
    out = []
    for line in (text or "").splitlines():
        keep = False
        try:
            obj = json.loads(line)
            if isinstance(obj, dict) and set(obj) == {"blindProgress"}:
                bp = obj["blindProgress"]
                keep = (isinstance(bp, dict) and set(bp) == {"stage", "k", "n"} and bp["stage"] in PROGRESS_STAGES
                        and type(bp["k"]) is int and type(bp["n"]) is int)
            elif isinstance(obj, dict) and set(obj) == {"blindError"}:
                keep = obj["blindError"] in BLIND_CHILD_ERROR_CODES
        except (ValueError, TypeError):
            keep = False
        out.append(line if keep else "[blind: line dropped]")
    return "\n".join(out) + ("\n" if out else "")


def blind_failure_message(text):
    """Job `error` text: the fixed message of the child's code, never an exception message."""
    from lpbf_user_blind_protocol import REFUSALS
    for line in reversed((text or "").splitlines()):
        try:
            obj = json.loads(line)
        except (ValueError, TypeError):
            continue
        if isinstance(obj, dict) and set(obj) == {"blindError"} and obj["blindError"] in BLIND_CHILD_ERROR_CODES:
            return {"code": obj["blindError"], "message": REFUSALS.get(obj["blindError"], REFUSALS["INTERNAL_ERROR"])}
    return {"code": "INTERNAL_ERROR", "message": REFUSALS["INTERNAL_ERROR"]}


def child_main(input_data, folder):
    """Entry used by lpbf_worker --execute for blind types. Returns the process exit code."""
    silence()
    try:
        result = run_job(input_data, folder)
        result["provenance"] = dict(result.get("provenance") or {})
        tmp = os.path.join(str(folder), "result.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(json.dumps(result, allow_nan=False))
        os.replace(tmp, os.path.join(str(folder), "result.json"))
        return 0
    except BlindRefusal as e:
        emit_error(e.code if e.code in BLIND_CHILD_ERROR_CODES else "INTERNAL_ERROR")
        return 1
    except BaseException:  # noqa: BLE001 - every exception maps to a fixed code; no text reaches the log
        emit_error("INTERNAL_ERROR")
        return 1
