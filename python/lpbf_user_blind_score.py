"""Score of the user blind test (spec 4.5 items 5 and 6, 5 step 11, 6.4, section 7).

Verifies the freeze, joins the targets, reduces sections to tracks to conditions, computes the MELT statistics per arm
with the extracted functions (`lpbf_blind_stats`), applies the blindness rule and writes the report and the comparison
CSV in one committed directory. Frozen predictions are never recomputed. Python is the only authority for every
number and status in the report; TypeScript renders it.
"""
from __future__ import annotations

import csv
import io
import json
import math

import lpbf_blind_stats as stats
from lpbf_served_arms import predictor_identity
from lpbf_user_blind_overlap import build_job_history, calibration_exposures, spent_set_exposures, store_exposures
from lpbf_user_blind_protocol import (
    DATA_LABEL, DIVERGENCES, HONESTY, LEVERAGE_LOW_CUT, LOSS_STATUS, PROTOCOL_ID, REGISTERED_ALLOYS, REPORT_SCHEMA,
    SERVED_SOURCE_KIND,
    SERVED_SOURCE_LOCATOR, SERVED_SOURCE_REASON, STATS_ALLOY_KEY, THRESHOLDS, USER_TIER, WORDING, BlindRefusal,
    canonical_bytes, canonical_sha256, protocol_sha256, text_cell_safe, wording_sha256,
)
from lpbf_user_blind_store import sha256_bytes
from lpbf_user_blind_targets import parse_targets

STATUS_MAP = {"PASS": "thresholds-met", "FAIL": "threshold-not-met", "INCONCLUSIVE": "inconclusive",
              "EXPOSED_DESCRIPTIVE": "descriptive-exposed", "DESCRIPTIVE_NOT_SCORED": "descriptive-not-scored"}
SERVED_ARMS = ("served", "served:P-5%", "served:P+5%", "served:d-5%", "served:d+5%")
STAT_NAMES = {"median": "median APE", "p90": "90th percentile APE", "mean_signed": "mean signed error",
              "max_ape": "maximum APE"}


def load_freeze(store, key):
    d = store.freeze_dir(key)
    if not (d / "freeze.json").is_file():
        raise BlindRefusal("FREEZE_UNKNOWN", field="freezeKey")
    data = store.read_record(d, "freeze.json")
    doc = json.loads(data)
    from lpbf_user_blind_freeze import freeze_key_of
    if doc.get("freezeKey") != key or freeze_key_of(doc["metadata"], doc["rows"], doc["predictorIdentity"]) != key:
        raise BlindRefusal("FREEZE_ALTERED")
    return doc, data


def _num(x):
    return x if (x is None or math.isfinite(x)) else ("inf" if x > 0 else "-inf")


def _clean(obj):
    """JSON-safe copy: +-inf become the strings 'inf' and '-inf' (the report is canonical JSON, NaN refused)."""
    if isinstance(obj, float):
        if math.isnan(obj):
            return None
        return _num(obj)
    if isinstance(obj, dict):
        return {str(k): _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    return obj


def blindness(store, freeze, md, declarations, commitment_matched, attempt_n, first_targets_sha, targets_sha,
              frozen_entry, at_score_ledger):
    """Status of spec 6.4 with reasons, reveal events, overlap and exposures after commitment."""
    key = freeze["freezeKey"]
    tuples = [(c["P_W"], c["v_mm_s"], c["d_1e2_um"]) for c in freeze["conditions"]]
    frozen_seq = frozen_entry["seq"] if frozen_entry else 0
    frozen_at = frozen_entry["at"] if frozen_entry else freeze["createdAt"]
    committed = commitment_matched is True
    reasons, statuses, after = [], [], []

    def exposure(status, reason, before_freeze, item):
        if committed and not before_freeze and item in (2, 3, 7):
            after.append({"status": status, "reason": reason})
        else:
            statuses.append(status)
            reasons.append(reason)

    ind = md["independence"]
    if ind["predictionsViewedBeforeFreeze"] in ("yes", "unsure") or declarations.get(
            "viewedPredictionsBeforeFinalisingTargets") in ("yes", "unsure"):
        statuses.append("not-blind-predictions-viewed")
        reasons.append("you declared that you viewed predictions for these conditions")
    reveals = [e for e in at_score_ledger if e.get("event") == "revealed" and e.get("freezeKey") == key]
    n_reveal_records = len(store.numbered(key, "reveal"))
    if reveals or n_reveal_records:
        exposure("not-blind-predictions-revealed", "the frozen predictions were revealed before this score", False, 2)
    for e in store_exposures(store, md["alloy"], tuples, exclude_key=key):
        exposure("not-blind-earlier-test-overlap",
                 f"{e['nConditions']} conditions match a test on this computer that was {e['kind']}",
                 e["seq"] < frozen_seq, 3)
    if attempt_n > 1 and first_targets_sha is not None and targets_sha != first_targets_sha:
        statuses.append("not-blind-rescored-changed-targets")
        reasons.append("this attempt uses a targets file that differs from attempt 1")
    from lpbf_spent_ledger import spent_dois
    doi = (ind["publishedDoi"] or "").strip().lower()
    dois = spent_dois()
    if doi and doi in dois:
        statuses.append("not-blind-data-already-used-by-app")
        reasons.append(f"the DOI is in this app's spent ledger ({dois[doi]})")
    for e in spent_set_exposures(md["alloy"], tuples):
        statuses.append("not-blind-data-already-used-by-app")
        reasons.append(f"{e['nConditions']} conditions match the published set {e['datasetId']}")
    for e in build_job_history(md["alloy"], tuples, before_iso=frozen_at):
        statuses.append("not-blind-app-history")
        reasons.append(f"{e['nConditions']} conditions match Build Job history before the freeze (partial check, "
                       "Build Job history only)")
    if ind["usedForMachineCalibration"]:
        statuses.append("not-blind-used-for-calibration")
        reasons.append("you declared that these conditions were used for machine calibration")
    for e in calibration_exposures(md["alloy"], tuples):
        exposure("not-blind-used-for-calibration", f"tuple overlap with calibration store {e['storeId']}",
                 str(e["at"]) < str(frozen_at), 7)
    labels = []
    if statuses:
        status = statuses[0]
    elif committed:
        status = "blind-committed"
    elif md["mode"] == "pre-measurement":
        status = "blind-prospective-declared"
    else:
        status = "blind-retrospective-declared"
    if ind["dataPreviouslyPublished"] == "yes" and status in ("blind-committed", "blind-prospective-declared"):
        status = "blind-retrospective-declared"
    if ind["dataPreviouslyPublished"] == "yes" and not (doi and doi in dois):
        labels.append(f"published data, not in this app's spent ledger (DOI {ind['publishedDoi']})"
                      if ind["publishedDoi"] else "published data, not in this app's spent ledger (DOI not given)")
    return {"status": status, "statuses": sorted(set(statuses)), "reasons": reasons,
            "revealEvents": [{"seq": e["seq"], "at": e["at"]} for e in reveals],
            "exposuresAfterCommitment": after}, labels


def _rows_for_reduce(freeze, targets, alloy_key):
    """Rows in the shape of stats.reduce_conditions, with not-formed and lost rows separated (D1, D11)."""
    preds = {c["condition"]: c for c in freeze["conditions"]}
    md = freeze["metadata"]
    du = md["depthUncertainty"]
    k = du["coverageFactor"]
    rows, depth_map, lost, not_formed = [], {}, [], set()
    for r in freeze["rows"]:
        t = targets[r["ordinal"]]
        if t["status"] in LOSS_STATUS:
            lost.append({"row": r, "status": t["status"]})
            continue
        if t["status"] == "track-not-formed":
            not_formed.add(r["condition"])
            continue
        c = preds[r["condition"]]
        u = (t["u_um"] / k if du["basis"] == "per-row" else (du["u_um"] / k if du["basis"] == "block" else None))
        pred = {}
        for arm, v in c["pred"].items():
            if v["status"] == "ok":
                pred[arm] = float(v["value_um"])
            elif v["status"] == "failed":
                pred[arm] = {"status": "failed", "reason": v["reasonCode"]}
            else:
                pred[arm] = {"status": "unavailable", "reason": v["reasonCode"]}
        rows.append({"ordinal": r["ordinal"], "condition": r["condition"], "track": r["track"], "section": r["section"],
                     "beam_setting": "nominal", "P_W": r["P_W"], "v_mm_s": r["v_mm_s"], "d_um": r["d_1e2_um"],
                     "index": c["indexUnrounded"], "u_m_um": u, "pred": pred,
                     "ledger": {"widthObs": t["width_um"]}})
        depth_map[r["ordinal"]] = {"depth_um": t["depth_um"]}
    return rows, depth_map, lost, not_formed


def _loss_counts(freeze, targets):
    rows = freeze["rows"]
    by_track, by_cond = {}, {}
    for r in rows:
        st = targets[r["ordinal"]]["status"]
        by_track.setdefault((r["condition"], r["track"]), []).append(st)
        by_cond.setdefault(r["condition"], []).append(st)
    lost_sections = sum(1 for r in rows if targets[r["ordinal"]]["status"] in LOSS_STATUS)
    lost_tracks = sum(1 for v in by_track.values() if all(s in LOSS_STATUS for s in v))
    lost_conds = sum(1 for v in by_cond.values() if all(s in LOSS_STATUS for s in v))
    return ({"sections": f"{lost_sections} of {len(rows)} frozen", "tracks": f"{lost_tracks} of {len(by_track)} frozen",
             "conditions": f"{lost_conds} of {len(by_cond)} frozen"},
            lost_tracks / max(1, len(by_track)) > 0.20 or lost_conds / max(1, len(by_cond)) > 0.20,
            (lost_sections, lost_tracks, lost_conds))


def score(store, job, freeze, freeze_bytes, targets_bytes, targets_sha, commitment_matched, attempt_n,
          earlier_targets, frozen_entry, ledger_now):
    """Compute the report document (no write). `earlier_targets`: targets sha256 of attempts 1 .. n-1 in order."""
    from lpbf_user_blind_inputs import ISSUE_TEXT as issue_text
    md = freeze["metadata"]
    alloy = md["alloy"]
    if freeze.get("protocolId") == PROTOCOL_ID and freeze.get("protocolSha256") != protocol_sha256():
        raise BlindRefusal("PROTOCOL_CHANGED")
    targets = {int(k): v for k, v in parse_targets(targets_bytes, freeze)["byOrdinal"].items()}
    alloy_key = STATS_ALLOY_KEY.get(alloy, "Ti64")
    rows, depth_map, lost, not_formed = _rows_for_reduce(freeze, targets, alloy_key)
    conds = stats.reduce_conditions(rows, depth_map) if rows else []
    have = {c["condition"] for c in conds}
    cmap = {c["condition"]: c for c in freeze["conditions"]}
    lost_conditions = {c for c in cmap if c not in have and c not in not_formed}
    for cid in sorted(not_formed):
        if cid in have:
            c = next(x for x in conds if x["condition"] == cid)
            c["pred"] = {a: {"status": "failed", "reason": "TRACK_NOT_FORMED"} for a in c["pred"]}
            c["notFormed"] = True
        else:
            f = cmap[cid]
            conds.append({"condition": cid, "P_W": f["P_W"], "v_mm_s": f["v_mm_s"], "d_um": f["d_1e2_um"],
                          "index": f["indexUnrounded"], "n_tracks": 0, "track_depths": [], "D_obs_um": None,
                          "u_m_um": None, "ledger": {}, "notFormed": True,
                          "pred": {a: {"status": "failed", "reason": "TRACK_NOT_FORMED"} for a in f["pred"]}})
    conds.sort(key=lambda c: list(cmap).index(c["condition"]))
    exclusions, losses_issue, (ls, lt, lc) = _loss_counts(freeze, targets)
    issues = list(freeze["blockIssues"]) + (["LOSSES_ABOVE_20_PERCENT"] if losses_issue else [])
    bl, bl_labels = blindness(store, freeze, md, job["declarations"], commitment_matched, attempt_n,
                              earlier_targets[0] if earlier_targets else None, targets_sha, frozen_entry, ledger_now)
    exposed = bl["status"].startswith("not-blind")
    powder = md["substrate"]["kind"] == "powder-layer"
    scoped = [c for c in conds if c.get("D_obs_um") is not None]
    resolution = stats.resolution_qualifier(
        [{"track_depths": c["track_depths"], "u_m_um": c["u_m_um"]} for c in scoped],
        "powder_layer" if powder else "bare_plate", md["substrate"]["amSubstrate"]) if scoped else {
        "status": "not_evaluable", "reason": "no measured condition", "u_m_assumed": False}
    leverage = leverage_for(conds, alloy)
    not_scored_reason = None
    if powder:
        not_scored_reason = "powder layer (the served model is flat-plate)"
    arms_out, rels_by_arm = {}, {}
    issue_sentences = [issue_text[i] for i in issues]
    for arm in SERVED_ARMS:
        rels, names, unavailable = stats.arm_rels(conds, arm)
        rels_by_arm[arm] = dict(zip(names, rels))
        verdict = stats.block_verdict(rels, leverage_ok=leverage["ok"], resolution_status=resolution["status"],
                                      issues=issue_sentences, exposed=exposed, scored=not_scored_reason is None)
        status = STATUS_MAP[verdict["status"]]
        if status == "descriptive-exposed":
            reason = "; ".join(bl["reasons"]) or "exposure"
            sentence = WORDING["status"][status].format(reason=reason)
        elif status == "descriptive-not-scored":
            reason = not_scored_reason
            sentence = WORDING["status"][status].format(reason=reason)
        elif status == "threshold-not-met":
            failed = [STAT_NAMES[k] for k, v in verdict["stats"]["thresholds_met"].items() if not v]
            reason = ", ".join(failed)
            sentence = WORDING["status"][status].format(list=reason)
        elif status == "inconclusive":
            reason = verdict["reason"]
            sentence = WORDING["status"][status].format(reason=reason)
        else:
            reason = None
            sentence = WORDING["status"][status]
        s = verdict["stats"]
        arm_doc = {"status": status, "sentence": sentence, "reason": reason,
                   "coverage": {"k": len(rels), "n": len(conds), "unavailable": len(unavailable)},
                   "stats": {"n": s["n"], "median": s["median"], "p75": s["p75"], "p90": s["p90"],
                             "meanSigned": s["mean_signed"], "maxApe": s["max_ape"], "nFailed": s["n_failed"],
                             "nNotFormed": sum(1 for c in conds if c.get("notFormed")),
                             "thresholdsMet": {"median": s["thresholds_met"]["median"],
                                               "p90": s["thresholds_met"]["p90"],
                                               "meanSigned": s["thresholds_met"]["mean_signed"],
                                               "maxApe": s["thresholds_met"]["max_ape"]},
                             "allThresholdsMet": s["all_thresholds_met"]},
                   "unavailableConditions": unavailable}
        if arm == "served":
            boot = stats.bootstrap_intervals(rels) if rels else {}
            arm_doc["bootstrap95"] = boot
            arm_doc["marginal"] = [k for k, v in boot.items() if v.get("marginal")]
            if alloy in LEVERAGE_LOW_CUT:
                arm_doc["servedBins"] = served_bins_for(conds, rels_by_arm[arm], alloy)
        arms_out[arm] = arm_doc
    for arm in ("research:melt-link", "research:cavity"):
        arms_out[arm] = {"status": "unavailable", "sentence": WORDING["status"]["unavailable"].format(
            reason=WORDING["researchReason"]), "reason": "RESEARCH_NOT_REQUESTED",
            "coverage": {"k": 0, "n": len(conds), "unavailable": len(conds)}, "stats": None,
            "unavailableConditions": [c["condition"] for c in conds]}
    labels = list(freeze["labels"]) + bl_labels
    served = arms_out["served"]
    if served["status"] == "thresholds-met" or (served["stats"]["allThresholdsMet"] and not exposed):
        flips = [a for a in SERVED_ARMS[1:] if not arms_out[a]["stats"]["allThresholdsMet"]]
        if served["stats"]["allThresholdsMet"] and flips:
            labels.append("input-fragile")
        fragile = {"input": "evaluated", "inputFlips": flips, "property": "not evaluated"}
    else:
        fragile = {"input": "not evaluated (the served arm does not meet all four thresholds)", "inputFlips": [],
                   "property": "not evaluated"}
    labels.append("property sensitivity not evaluated")
    for m in served.get("marginal", []):
        labels.append(f"marginal: {m}")
    if resolution.get("u_m_assumed"):
        labels.append("u_m assumed (lead assumption, not sourced)")
    if not_formed:
        labels.append(f"track not formed in {len(not_formed)} conditions: counted as model misses")
    if ls:
        labels.append(f"measurement losses: {ls} sections, {lt} tracks, {lc} conditions excluded")
    if commitment_matched is False:
        labels.append("commitment not matched")
    predictor_now = predictor_identity(alloy)
    from lpbf_user_blind_freeze import scorer_identity
    scorer_now = scorer_identity()
    pred_changed = canonical_sha256(predictor_now) != canonical_sha256(freeze["predictorIdentity"])
    scorer_changed = scorer_now["scoreSourcesSha256"] != freeze["scorerIdentity"]["scoreSourcesSha256"] or (
        scorer_now["numpy"] != freeze["scorerIdentity"]["numpy"])
    if pred_changed:
        labels.append("predictor changed since freeze; this result scores the frozen predictions")
    if scorer_changed:
        labels.append("scoring code changed since freeze; this result uses the scorer present at score time")
    ledger_rows = []
    for c in conds:
        f = cmap[c["condition"]]
        tier = {"sourceEvidenceKind": DATA_LABEL, "tier": USER_TIER,
                "sourceLocator": {"targetsSha256": targets_sha, "condition": c["condition"]}}
        preds = {}
        for arm in ("served", *SERVED_ARMS[1:], "research:melt-link", "research:cavity", "context:fabbro"):
            v = f["pred"][arm]
            entry = {"value_um": v["value_um"], "status": v["status"], "reasonCode": v["reasonCode"]}
            if arm.startswith(("served", "context")):
                entry.update(sourceEvidenceKind=SERVED_SOURCE_KIND, sourceReason=SERVED_SOURCE_REASON,
                             sourceLocator=SERVED_SOURCE_LOCATOR)
            rel = rels_by_arm.get(arm, {}).get(c["condition"])
            entry["rel"] = rel
            preds[arm] = entry
        widths = [targets[r["ordinal"]]["width_um"] for r in freeze["rows"] if r["condition"] == c["condition"]
                  and targets[r["ordinal"]]["width_um"] is not None]
        ledger_rows.append({
            "condition": c["condition"], "P_W": f["P_W"], "v_mm_s": f["v_mm_s"], "d_1e2_um": f["d_1e2_um"],
            "indexBin": f["indexBin"], "nTracks": c["n_tracks"], "trackDepths_um": c["track_depths"],
            "D_obs_um": c["D_obs_um"], "observed": tier, "notFormed": bool(c.get("notFormed")), "pred": preds,
            "widthObs_um": (sum(widths) / len(widths)) if widths else None,
            "widthModel_um": f["pred"]["served"].get("width_um"),
            "inputSensitivityRange_um": _sens_range(f["pred"]),
        })
    applied = set(freeze["divergences"]) | ({"D1"} if ls else set()) | ({"D11"} if not_formed else set())
    report = {
        "schema": REPORT_SCHEMA, "protocolId": PROTOCOL_ID, "title": WORDING["reportTitle"],
        "banner": WORDING["banner"], "freezeKey": freeze["freezeKey"], "freezeSha256": sha256_bytes(freeze_bytes),
        "targetsSha256": targets_sha,
        "commitment": {"declared": md.get("targetCommitment") is not None, "matched": commitment_matched},
        "attempt": {"n": attempt_n, "earlierTargetsSha256": list(earlier_targets)},
        "blindness": {**bl, "sentence": _blind_sentence(bl)},
        "predictor": {"atFreeze": freeze["predictorIdentity"], "atScore": predictor_now,
                      "changedSinceFreeze": pred_changed},
        "scorer": {"atFreeze": freeze["scorerIdentity"], "atScore": scorer_now, "changedSinceFreeze": scorer_changed},
        "divergences": [{**d, "applied": d["id"] in applied} for d in DIVERGENCES],
        "wordingSha256": wording_sha256(),
        "thresholds": {**THRESHOLDS, "alloyNote": "; ".join(
            [WORDING["alloyScope"].format(alloy=alloy)]
            + ([] if alloy in REGISTERED_ALLOYS else [WORDING["thresholdsReused"].format(alloy=alloy)]))},
        "grades": freeze["grades"], "blockIssues": issues, "resolution": _clean(_res_doc(resolution)),
        "leverage": leverage, "arms": arms_out,
        "commonSubset": {"k": served["coverage"]["k"], "note": "research arm not requested; the common subset is the "
                         "served arm's scope"},
        "labels": list(dict.fromkeys(labels)), "fragile": fragile, "ledger": ledger_rows,
        "excluded": {"inputs": [], "targets": [{"row": x["row"]["ordinal"], "condition": x["row"]["condition"],
                                                "track": x["row"]["track"], "section": x["row"]["section"],
                                                "status": x["status"]} for x in lost]},
        "exclusions": exclusions, "lostConditions": sorted(lost_conditions),
        "notFormed": {"conditions": sorted(not_formed)},
        "userValueLabel": {"sourceEvidenceKind": DATA_LABEL, "tier": USER_TIER},
        "servedValueLabel": {"sourceEvidenceKind": SERVED_SOURCE_KIND, "reason": SERVED_SOURCE_REASON,
                             "text": WORDING["servedValueLabel"]},
        "honesty": HONESTY,
    }
    return _clean(report)


def leverage_for(conds, alloy):
    """MELT leverage_qualifier with the per-alloy low cut of the protocol record (declared addition, D6); IN625 has
    no low cut and is not evaluable (a step 5 qualifier: it never hides a threshold failure)."""
    if alloy in ("Ti-6Al-4V", "AlSi10Mg"):
        return stats.leverage_qualifier(conds, STATS_ALLOY_KEY[alloy])
    cut = LEVERAGE_LOW_CUT.get(alloy)
    if cut is None:
        return {"cut": None, "n_below": None, "n_at_or_above_20": None, "ok": False,
                "reason": "leverage not evaluable for IN625 (no low cut; the served IN625 rule is two-class at 13.6)"}
    below = sum(1 for c in conds if c["index"] < cut)
    above = sum(1 for c in conds if c["index"] >= stats.LEVERAGE_HIGH_CUT)
    return {"cut": cut, "n_below": below, "n_at_or_above_20": above,
            "ok": below >= stats.SIDE_MIN and above >= stats.SIDE_MIN}


def served_bins_for(conds, rels_by_name, alloy):
    """stats.served_bins with the per-alloy low cut of the protocol record."""
    cut = LEVERAGE_LOW_CUT[alloy]
    out = {}
    for name in ("below", "between", "at_or_above"):
        vals = [rels_by_name[c["condition"]] for c in conds if c["condition"] in rels_by_name
                and stats.index_bins(c["index"], cut) == name]
        fin = [v for v in vals if math.isfinite(v)]
        out[name] = {"n": len(vals), "mean_signed": (math.fsum(fin) / len(fin)) if fin else None,
                     "n_failed": len(vals) - len(fin)}
    return out


def _sens_range(pred):
    vals = [pred[a]["value_um"] for a in SERVED_ARMS if pred[a]["status"] == "ok"]
    if len(vals) < len(SERVED_ARMS):
        return None
    return {"min_um": min(vals), "max_um": max(vals), "note": ("served at power and beam each 5 % lower and higher; "
                                                              "an input sensitivity range, not an error bar")}


def _res_doc(res):
    keep = ("status", "median_U", "median_U_2x_descriptive", "median_U_t_descriptive", "cv_pool",
            "n_replicated_conditions", "pooled_df", "u_m_assumed", "reason")
    out = {k: res.get(k) for k in keep}
    if res.get("u_m_assumed"):
        out["leadAssumption"] = "u_m = max(f, 0.03 D) with f 5 um bare plate or 10 um powder or AM block (not sourced)"
    return out


def _blind_sentence(bl):
    t = WORDING["blindness"][bl["status"]]
    k = next((r.split(" ")[0] for r in bl["reasons"] if "conditions match a test" in r), "some")
    ident = next((r.rsplit("(", 1)[-1].rstrip(")") for r in bl["reasons"] if "(" in r), "")
    if "store" in (bl["reasons"][0] if bl["reasons"] else ""):
        ident = bl["reasons"][0].rsplit(" ", 1)[-1]
    return t.format(k=k, id=ident)


# ---------------------------------------------------------------------------------------------- comparison CSV (4.5.6)
CSV_HEADER = ("condition_id", "P_W", "v_mm_s", "d_1e2_um", "index_bin", "n_tracks", "D_obs_um", "arm", "arm_status",
              "D_pred_um", "rel_signed_fraction", "ape_fraction", "band_min_um", "band_nominal_um", "band_max_um",
              "consistency_status", "source_evidence_kind", "excluded_status", "labels")


def comparison_csv(report, report_sha):
    buf = io.StringIO()
    pre = [WORDING["banner"], "experimentalValidation=false appValidation=false labelPromotionProposed=none "
           "evidenceKind=screening-only dataLabel=" + DATA_LABEL, report["title"], f"freezeKey {report['freezeKey']}",
           f"reportSha256 {report_sha}", f"blindness {report['blindness']['status']}: {report['blindness']['sentence']}"]
    for arm, a in report["arms"].items():
        pre.append(f"arm {arm} {a['status']}: {a['sentence']}")
    pre.append("labels: " + " | ".join(report["labels"]))
    for d in report["divergences"]:
        if d["applied"]:
            pre.append(f"divergence {d['id']}: {d['rule']}")
    pre.append(WORDING["relNote"])
    for line in pre:
        buf.write("# " + line.replace("\r", " ").replace("\n", " ") + "\n")
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(CSV_HEADER)
    labels = " | ".join(report["labels"])
    for row in report["ledger"]:
        for arm, p in row["pred"].items():
            arm_status = report["arms"].get(arm, {}).get("status", "context")
            rel = p.get("rel")
            ape = (abs(rel) if isinstance(rel, (int, float)) else ("inf" if rel in ("inf", "-inf") else None))
            src = p.get("sourceEvidenceKind", "")
            w.writerow([text_cell_safe(x) if x is not None else "" for x in (
                row["condition"], row["P_W"], row["v_mm_s"], row["d_1e2_um"], row["indexBin"], row["nTracks"],
                row["D_obs_um"], arm, arm_status if p["status"] != "failed" else "failed", p["value_um"], rel, ape,
                None, None, None, None, src, None, labels)])
    for x in report["excluded"]["targets"]:
        w.writerow([text_cell_safe(v) if v is not None else "" for v in (
            x["condition"], None, None, None, None, None, None, "", "", None, None, None, None, None, None, None,
            DATA_LABEL, x["status"], labels)])
    return buf.getvalue().encode("utf-8")
