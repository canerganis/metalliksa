"""Freeze of the user blind test (spec 4.5 items 2 and 3, 5 step 6).

Imports the inputs intake, the served arms, the statistics module (design checks only) and the store. It must not
import `lpbf_user_blind_targets` or `lpbf_user_blind_score` (AST test), and it asserts before its commit point that
neither module is loaded. Predictions are written to the freeze record only; the receipt carries no predicted value.
"""
from __future__ import annotations

import json
import sys

import lpbf_blind_stats as stats
from lpbf_served_arms import RESEARCH_MEMBER, SENSITIVITY_ARMS, served_arm
from lpbf_user_blind_preview import build_preview
from lpbf_user_blind_protocol import (
    FREEZE_SCHEMA, HONESTY, PROTOCOL_ID, RECEIPT_SCHEMA, RESEARCH_ARMS, SERVED_SOURCE_KIND, SERVED_SOURCE_LOCATOR,
    SERVED_SOURCE_REASON, TARGET_COLUMNS, TARGET_ALIASES, WORDING, BlindRefusal, canonical_bytes, canonical_sha256,
    protocol_sha256,
)
from lpbf_user_blind_store import index_entry, now_iso, sha256_bytes

FORBIDDEN_MODULES = ("lpbf_user_blind_targets", "lpbf_user_blind_score")
SCORER_FILES = ("python/lpbf_blind_stats.py", "python/lpbf_user_blind_score.py", "python/lpbf_user_blind_targets.py",
                "python/lpbf_spent_ledger.py")


def scorer_identity():
    from lpbf_user_blind_store import REPO_ROOT, scorer_source_hashes
    import numpy
    hashes = scorer_source_hashes([REPO_ROOT / p for p in SCORER_FILES])
    return {"scoreSourcesSha256": canonical_sha256(hashes), "files": hashes,
            "statsConstants": {"median": stats.MEDIAN_MAX, "p90": stats.P90_MAX, "meanSigned": stats.BIAS_MAX,
                               "maxApe": stats.MAXAPE_MAX, "nMin": stats.N_MIN, "sideMin": stats.SIDE_MIN,
                               "uMax": stats.U_MAX, "leverageHighCut": stats.LEVERAGE_HIGH_CUT,
                               "leverageLowCut": dict(stats.LEVERAGE_LOW_CUT), "uMRelFloor": stats.U_M_REL_FLOOR,
                               "uMFUm": dict(stats.U_M_F_UM), "bootB": stats.BOOT_B, "bootSeed": stats.BOOT_SEED},
            "protocolSha256": protocol_sha256(), "numpy": numpy.__version__}


class _ColumnsLoaded:
    def __init__(self, columns):
        self.columns_loaded = list(columns)


def assert_prediction_phase(columns_loaded):
    """No target column loaded and no targets parser or scorer in this process (spec 5 step 6, ENG-17)."""
    targets = {c: c for c in TARGET_COLUMNS if c.startswith(("depth", "width"))}
    for c, aliases in TARGET_ALIASES.items():
        if c.startswith(("depth", "width")):
            for i, a in enumerate(aliases):
                targets[f"{c}#{i}"] = a
    stats.assert_no_target_loaded(_ColumnsLoaded(columns_loaded), {"whitelist": {"targets": targets}})
    loaded = [m for m in FORBIDDEN_MODULES if m in sys.modules]
    if loaded:
        raise RuntimeError("targets parser or scorer loaded in the freeze process")


def _value(arm):
    if arm["status"] == "ok":
        return {"value_um": arm["depth_um"], "width_um": arm["width_um"], "status": "ok", "reasonCode": None,
                "reasonClass": None, "extentStatus": arm["extentStatus"], "warnings": [],
                "sourceEvidenceKind": SERVED_SOURCE_KIND, "sourceReason": SERVED_SOURCE_REASON,
                "sourceReasonText": WORDING["servedValueLabel"], "sourceLocator": SERVED_SOURCE_LOCATOR}
    return {"value_um": None, "width_um": None, "status": "failed", "reasonCode": arm.get("reason", "SERVED_EXCEPTION"),
            "reasonClass": "failed", "extentStatus": arm.get("extentStatus"), "warnings": [],
            "sourceEvidenceKind": SERVED_SOURCE_KIND, "sourceReason": SERVED_SOURCE_REASON,
            "sourceReasonText": WORDING["servedValueLabel"], "sourceLocator": SERVED_SOURCE_LOCATOR}


def _safe(fn, *a):
    try:
        return fn(*a)
    except Exception:  # one condition's solver exception is a failed arm, never a job failure (spec 3.2 item 3)
        return {"status": "failed", "reason": "SERVED_EXCEPTION", "extentStatus": None}


def predict_condition(alloy, c, T0_C, layer_um):
    served = _safe(served_arm, alloy, c["P_W"], c["v_mm_s"], c["d_1e2_um"], T0_C, layer_um)
    pred = {"served": _value(served)}
    for name, fp, fd in SENSITIVITY_ARMS:
        pred[name] = _value(_safe(served_arm, alloy, c["P_W"] * fp, c["v_mm_s"], c["d_1e2_um"] * fd, T0_C, layer_um))
    for name in RESEARCH_ARMS:
        pred[name] = {"value_um": None, "status": "unavailable", "reasonCode": "RESEARCH_NOT_REQUESTED",
                      "reasonClass": "unavailable", "extentStatus": None, "warnings": []}
    fab = served.get("fabbroDepth_um")
    pred["context:fabbro"] = {"value_um": fab, "status": "ok" if fab is not None else "unavailable",
                              "reasonCode": None if fab is not None else "FABBRO_NOT_COMPUTED",
                              "reasonClass": None, "extentStatus": None, "warnings": [],
                              "sourceEvidenceKind": SERVED_SOURCE_KIND, "sourceReason": SERVED_SOURCE_REASON,
                              "sourceLocator": SERVED_SOURCE_LOCATOR}
    index = served.get("index")
    if index is None:
        from lpbf_served_arms import served_index
        index = served_index(alloy, c["P_W"], c["v_mm_s"], c["d_1e2_um"], T0_C)
    return pred, float(index)


def freeze_key_of(metadata, rows, identity):
    return canonical_sha256({"protocolId": PROTOCOL_ID, "metadata": metadata, "rows": rows,
                             "predictorIdentity": identity})


def _check_acks(context, acknowledgements):
    missing = [a for a in context["acks"] if acknowledgements.get(a) is not True]
    if missing:
        best = context["best"]
        raise BlindRefusal("ACK_REQUIRED", status=best["status"], reason="; ".join(best["reasons"]) or "exposure",
                           detail={"required": context["acks"]})


def check_submit(store, p):
    """Submit-side checks (spec 5 step 5): re-run the preview, then OVERLAP_CHANGED, ACK_REQUIRED, PREVIEW_DRIFT."""
    preview, context = build_preview(store, p["metadata"], p["inputsCsvBase64"], p["inputsFileName"])
    if preview["overlapSha256"] != p["overlapSha256"]:
        raise BlindRefusal("OVERLAP_CHANGED", k=sum(e["nConditions"] for v in preview["overlap"].values() for e in v))
    _check_acks(context, p["acknowledgements"])
    if preview["previewSha256"] != p["previewSha256"]:
        raise BlindRefusal("PREVIEW_DRIFT")
    if context["unpinned"]:
        raise BlindRefusal("PREDICTOR_NOT_PINNED", files=", ".join(context["unpinned"][:5]),
                           detail={"files": context["unpinned"]})
    return preview, context


def run_freeze(store, job, progress=lambda k, n: None):
    """Child side. `job` is the hashes-only input.json of a user-blind-freeze job."""
    import base64
    md_bytes = store.get_upload(job["metadataSha256"], "metadata.json")
    inputs = store.get_upload(job["inputsSha256"], "inputs.csv")
    metadata_raw = json.loads(md_bytes)
    preview, context = build_preview(store, metadata_raw, base64.b64encode(inputs).decode("ascii"),
                                     job["inputsFileName"])
    if context["unpinned"]:
        raise BlindRefusal("PREDICTOR_NOT_PINNED", files=", ".join(context["unpinned"][:5]))
    if preview["previewSha256"] != job["previewSha256"] and preview["overlapSha256"] == job["overlapSha256"]:
        raise BlindRefusal("PREVIEW_DRIFT")
    md, parsed, identity = context["metadata"], context["parsed"], context["identity"]
    T0 = md["preheat_C"]
    layer = md["substrate"]["layerThickness_um"] if md["substrate"]["kind"] == "powder-layer" else 40.0
    conditions, n = [], len(parsed["conditions"])
    for k, c in enumerate(parsed["conditions"]):
        pred, index = predict_condition(md["alloy"], c, T0, layer)
        cut = stats.LEVERAGE_LOW_CUT.get({"Ti-6Al-4V": "Ti64", "AlSi10Mg": "AlSi10Mg"}.get(md["alloy"], ""))
        bin_ = stats.index_bins(index, cut) if cut is not None else None
        conditions.append({**{x: c[x] for x in ("condition", "P_W", "v_mm_s", "d_1e2_um", "d_declared_um",
                                                 "nTracks", "nRows", "rows")},
                           "indexUnrounded": index, "indexBin": bin_, "pred": pred})
        progress(k + 1, n)
    assert_prediction_phase(parsed["columnsLoaded"])
    rows = parsed["rows"]
    key = freeze_key_of(md, rows, identity)
    predictions = {c["condition"]: c["pred"] for c in conditions}
    record = {
        "schema": FREEZE_SCHEMA, "protocolId": PROTOCOL_ID, "protocolSha256": protocol_sha256(), "freezeKey": key,
        "createdAt": now_iso(), "createdAtNote": "local clock, not verified",
        "metadata": md, "metadataSha256": job["metadataSha256"], "inputsSha256": job["inputsSha256"],
        "inputsFileName": job["inputsFileName"], "previewSha256": preview["previewSha256"],
        "overlapSha256": preview["overlapSha256"], "columnsLoaded": parsed["columnsLoaded"],
        "keyColumns": parsed["keyColumns"], "targetColumnsRead": False, "rows": rows, "conditions": conditions,
        "counts": parsed["counts"], "acknowledgements": job["acknowledgements"], "excludedInputs": [],
        "designChecks": context["checks"], "grades": preview["grades"], "blockIssues": context["issues"],
        "labels": context["labels"], "predictorIdentity": identity, "scorerIdentity": scorer_identity(),
        "predictionsSha256": canonical_sha256(predictions), "research": dict(RESEARCH_MEMBER),
        "divergences": preview["divergences"], "honesty": HONESTY,
    }
    data = canonical_bytes(record)
    staging = store.stage({"freeze.json": data})
    with store.lock():
        target = store.freeze_dir(key)
        if target.exists():
            existing = json.loads(store.read_record(target, "freeze.json"))
            return receipt(existing, store, already=True)
        # Re-derive the acknowledgements and the overlap against the store as it is now (spec 5 step 6).
        now_preview, now_ctx = build_preview(store, metadata_raw, base64.b64encode(inputs).decode("ascii"),
                                             job["inputsFileName"])
        if now_preview["overlapSha256"] != job["overlapSha256"]:
            raise BlindRefusal("OVERLAP_CHANGED", k=sum(e["nConditions"] for v in now_preview["overlap"].values()
                                                         for e in v))
        _check_acks(now_ctx, job["acknowledgements"])
        assert_prediction_phase(parsed["columnsLoaded"])
        store.commit(staging, target)
        entry = store.append("frozen", freeze_key=key, job_id=job.get("jobId"), record=f"freezes/{key}",
                             hashes={"freeze": sha256_bytes(data), "inputs": job["inputsSha256"],
                                     "metadata": job["metadataSha256"], "predictions": record["predictionsSha256"]})
        store.append_index(index_entry(record))
    return receipt(record, store, entry=entry)


def receipt(record, store, already=False, entry=None):
    """Receipt (spec 4.5 item 3). No predicted value."""
    key = record["freezeKey"]
    freeze_sha = sha256_bytes(canonical_bytes(record))
    if entry is None:
        entry = next((e for e in store.ledger() if e.get("event") == "frozen" and e.get("freezeKey") == key), None)
    arms = []
    for arm in ("served", "served:P-5%", "served:P+5%", "served:d-5%", "served:d+5%", "research:melt-link",
                "research:cavity", "context:fabbro"):
        vals = [c["pred"][arm] for c in record["conditions"]]
        codes = sorted({v["reasonCode"] for v in vals if v["status"] != "ok" and v["reasonCode"]})
        arms.append({"id": arm, "available": sum(1 for v in vals if v["status"] == "ok"), "of": len(vals),
                     "reasonCodes": codes})
    commitment = record["metadata"].get("targetCommitment")
    return {
        "schema": RECEIPT_SCHEMA, "freezeKey": key, "freezeSha256": freeze_sha,
        "predictionsSha256": record["predictionsSha256"], "inputsSha256": record["inputsSha256"],
        "metadataSha256": record["metadataSha256"], "previewSha256": record["previewSha256"],
        "targetCommitmentSha256": commitment["sha256"] if commitment else None, "createdAt": record["createdAt"],
        "alreadyFrozen": bool(already), "blockLabel": record["metadata"]["blockLabel"],
        "alloy": record["metadata"]["alloy"], "counts": record["counts"],
        "acknowledgements": record["acknowledgements"], "excludedInputs": record["excludedInputs"],
        "designChecks": record["designChecks"], "grades": record["grades"], "blockIssues": record["blockIssues"],
        "labels": record["labels"], "armsFrozen": arms, "predictorIdentity": record["predictorIdentity"],
        "scorerIdentity": record["scorerIdentity"], "ledgerSeq": entry["seq"] if entry else None,
        "ledgerEntryHash": entry["entryHash"] if entry else None, "predictionsWithheld": True,
        "receiptLine": WORDING["receiptLine"], "anchorAdvice": WORDING["anchorAdvice"], "honesty": HONESTY,
    }
