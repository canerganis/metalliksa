#!/usr/bin/env python3
"""Spent-set descriptive record (research hub spec section 8.3). Python only; the browser renders the result.

Reads the spent ledger and the reasons catalogue, loads the rows of each SPENT public set through its pinned loader,
calls the one served definition (`lpbf_served_arms.served_arm`) and writes

  docs/LPBF_SPENT_DESCRIPTIVE_<date>.json        full record (rows, environment)
  docs/LPBF_SPENT_DESCRIPTIVE_<date>.view.json   slim record, schema lpbf-spent-descriptive-view-1, under 150 KB

This is a description of how the served model sits next to data that was already seen. It is not a test. No research
module is imported and no research request is ever made. The tool prints counts and hashes only, never a depth or a
width. `--check` re-derives the record and compares it with the committed files (everything except `generatedAt`).
It stays out of CI (6 significant digit floats from a solver run can differ across machines and library builds).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

PY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PY))
REPO = PY.parent
DOCS = REPO / "docs"
REASONS_PATH = REPO / "data" / "benchmark" / "spent-descriptive-reasons-v1.json"
DATE = "2026-10-17"
VIEW_SCHEMA = "lpbf-spent-descriptive-view-1"
FULL_SCHEMA = "lpbf-spent-descriptive-1"
REASONS_SCHEMA = "lpbf-spent-descriptive-reasons-1"
MAX_VIEW_BYTES = 150 * 1024
SIG_DIGITS = 6
CURVE_POINTS = 25
CURVE_LOW, CURVE_HIGH = 0.8, 1.25
MIN_GROUP_POINTS = 3
DEFAULT_PREHEAT_C = 25.0
BARE_PLATE_LAYER_UM = 40.0
SERVED_REASON_CODE = "SERVED_VALUE_KIND_NOT_PROVIDED"
SERVED_REASON_TEXT = "Unresolved: the served result does not yet list the source of each value."
BADGE = "Not validation: data already seen"
STATEMENT = ("These sets were already used while the model was developed or checked. This panel describes how the "
             "served model sits next to them. It does not test the model and it is not validation.")
RESEARCH_REASON = "RESEARCH_NOT_REQUESTED"
DIRECTION_RULE = ("model deeper when every signed difference in the bin is above zero, model shallower when every "
                  "one is below zero, mixed otherwise")

# Sets this release describes: ledger datasetId to the loader that supplies the rows.
SUPPORTED_SETS = ("nist-amb2022-03-optical", "lane-in625-amb2018-02", "ku-leuven-316l-2021", "ku-leuven-ti64-2021",
                  "totis-ti64-2021")
# Sets left out, with the reason recorded in the record's `deferred` list.
DEFERRED_SETS = (
    {"datasetId": "cunningham-ti64-2019",
     "reason": "Digitized figure data from a copyrighted journal: how it may be shown is not decided, and the "
               "vapour-depression quantity mapping needs a physics sign-off."},
    {"datasetId": "gan-keyhole-2021",
     "reason": "Same experiments as the Cunningham set, so it waits for the same decisions."},
    {"datasetId": "zhao-ti64-2020",
     "reason": "Not a spent set: it can enter only through a separate maintainer-approved ledger commit."},
)


class DescriptiveRefusal(ValueError):
    pass


# ------------------------------------------------------------------------------------------------
# small helpers
# ------------------------------------------------------------------------------------------------
def sha256_lf(path):
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def round_sig(x, digits=SIG_DIGITS):
    if x is None or isinstance(x, bool) or isinstance(x, int):
        return x
    if not math.isfinite(x):
        raise DescriptiveRefusal("non-finite number in the record")
    return float(f"{x:.{digits}g}")


def round_tree(obj):
    if isinstance(obj, float):
        return round_sig(obj)
    if isinstance(obj, dict):
        return {k: round_tree(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [round_tree(v) for v in obj]
    return obj


def canonical_bytes(obj):
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def percentile(sorted_vals, q):
    pos = (len(sorted_vals) - 1) * q / 100.0
    lo = int(math.floor(pos))
    hi = min(lo + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (pos - lo)


def log_space(lo, hi, n):
    a, b = math.log(lo), math.log(hi)
    return [math.exp(a + (b - a) * i / (n - 1)) for i in range(n)]


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


# ------------------------------------------------------------------------------------------------
# inputs: ledger, catalogue, rows, served call
# ------------------------------------------------------------------------------------------------
def load_reasons(path=REASONS_PATH):
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    if doc.get("schema") != REASONS_SCHEMA:
        raise DescriptiveRefusal("unknown reasons catalogue schema")
    for c in doc["codes"]:
        if c["expectedSign"] is not None or not c["sentence"].startswith("Candidate explanation, not tested:"):
            raise DescriptiveRefusal(f"catalogue code {c['code']} breaks the catalogue rules")
        if not (REPO / c["source"]).is_file():
            raise DescriptiveRefusal(f"catalogue code {c['code']} points to an untracked file")
    return doc


def admit(entry):
    """Spec 8.1 item 2: only SPENT entries outside the forbidden list, with a depth observable."""
    from lpbf_spent_ledger import FORBIDDEN_IDS
    did = entry.get("datasetId")
    if did in FORBIDDEN_IDS:
        raise DescriptiveRefusal(f"{did}: id is on the forbidden list")
    if entry.get("status") != "SPENT":
        raise DescriptiveRefusal(f"{did}: status {entry.get('status')} is not SPENT")
    if entry.get("observable") != "fusion-boundary-depth":
        raise DescriptiveRefusal(f"{did}: observable {entry.get('observable')} is not a melt-pool depth")
    return entry


def default_rows(entry):
    """(rows, loader provenance) of one supported set, filtered to the set's alloy. Pinned hashes verified by the loader."""
    import lpbf_public_datasets as pds
    from lpbf_spent_ledger import _protocol_alloy
    did = entry["datasetId"]
    if did == "lane-in625-amb2018-02":
        doc = pds.load_lane_in625()
    elif did in ("ku-leuven-316l-2021", "ku-leuven-ti64-2021"):
        doc = pds.load_ku_leuven_316l_ti64()
    elif did == "totis-ti64-2021":
        doc = pds.load_totis_ti64()
    elif did == "nist-amb2022-03-optical":
        from lpbf_process_window import _load_nist_table4
        doc = _load_nist_table4()
    else:
        raise DescriptiveRefusal(f"{did}: no loader in this release")
    rows = [r for r in doc["rows"] if _protocol_alloy(r.get("material")) == entry["alloy"]]
    return rows, doc["provenance"]


def call_served(alloy, power, speed, beam, preheat, layer):
    """One served call through lpbf_served_arms.served_arm (looked up at call time). Never raises on a solver error."""
    import lpbf_served_arms
    try:
        out = lpbf_served_arms.served_arm(alloy, power, speed, beam, preheat, layer)
    except Exception as exc:  # classified, not printed with values
        return {"status": "unavailable", "reason": type(exc).__name__, "index": None}
    return out


# ------------------------------------------------------------------------------------------------
# bins, deviation, groups
# ------------------------------------------------------------------------------------------------
def bin_defs(alloy):
    if alloy == "IN625":
        return (("below-13.6", "index below 13.6", None, 13.6), ("at-or-above-13.6", "index 13.6 or above", 13.6, None))
    return (("below-15", "index below 15", None, 15.0), ("15-to-20", "index 15 to below 20", 15.0, 20.0),
            ("at-or-above-20", "index 20 or above", 20.0, None))


def _in_bin(index, lo, hi):
    return index is not None and (lo is None or index >= lo) and (hi is None or index < hi)


def _stats(records):
    """records: [{status, diff, index}] -> n, failed, unavailable, median/p10/p90 of signed percent differences."""
    diffs = sorted(r["diff"] for r in records if r["diff"] is not None)
    out = {"n": len(diffs), "failed": sum(1 for r in records if r["status"] == "failed"),
           "unavailable": sum(1 for r in records if r["status"] == "unavailable")}
    if diffs:
        out.update(median_pct=percentile(diffs, 50), p10_pct=percentile(diffs, 10), p90_pct=percentile(diffs, 90))
    else:
        out.update(median_pct=None, p10_pct=None, p90_pct=None)
    return out


def _direction(diffs):
    if not diffs:
        return None
    if all(d > 0 for d in diffs):
        return "model deeper"
    if all(d < 0 for d in diffs):
        return "model shallower"
    return "mixed"


def deviation_block(records, alloy):
    bins = []
    for bid, label, lo, hi in bin_defs(alloy):
        sub = [r for r in records if _in_bin(r["index"], lo, hi)]
        stats = _stats(sub)
        stats.update(id=bid, label=label, direction=_direction([r["diff"] for r in sub if r["diff"] is not None]))
        bins.append(stats)
    return {"all": _stats(records), "bins": bins}


def row_inputs(row, entry, beam_um):
    preheat = row.get("preheat_C")
    layer_row = row.get("layer_um")
    return {"power_W": float(row["power_W"]), "speed_mm_s": float(row["speed_mm_s"]), "beam_um": float(beam_um),
            "preheat_C": float(preheat) if _num(preheat) else DEFAULT_PREHEAT_C,
            "preheatBasis": "row" if _num(preheat) else "assumed 25 C",
            "layer_um": float(layer_row) if _num(layer_row) and layer_row > 0 else BARE_PLATE_LAYER_UM,
            "layerBasis": "powder layer from the loader, served model is flat-plate" if _num(layer_row) and layer_row > 0
            else "bare plate default"}


def evaluate_rows(rows, entry, beam_override_um=None):
    """Per-row served result and signed percent difference. Order follows the rows."""
    out = []
    axis = entry["curveAxis"]
    for r in rows:
        beam = beam_override_um if beam_override_um is not None else r["beamDiameter_um"]
        inp = row_inputs(r, entry, beam)
        served = call_served(entry["alloy"], inp["power_W"], inp["speed_mm_s"], inp["beam_um"], inp["preheat_C"],
                             inp["layer_um"])
        measured = r.get("depth_um")
        sd = r.get("depthSigma_um")
        status = served["status"]
        pred = served.get("depth_um") if status == "ok" else None
        diff = None
        if status == "ok" and _num(measured) and measured > 0:
            diff = 100.0 * (pred - measured) / measured
        elif status == "ok":
            status = "unavailable"
        out.append({"rowId": r["rowId"], "inputs": inp, "x": inp["speed_mm_s"] if axis == "speed" else inp["power_W"],
                    "measured_um": float(measured) if _num(measured) else None,
                    "measuredSd_um": float(sd) if _num(sd) else None,
                    "served_um": pred, "status": status, "reason": served.get("reason"),
                    "index": served.get("index") if _num(served.get("index")) else None, "diff": diff})
    return out


def group_key(ev, axis):
    i = ev["inputs"]
    fixed = i["speed_mm_s"] if axis == "power" else i["power_W"]
    return (fixed, i["beam_um"], i["preheat_C"], i["layer_um"])


def build_groups(evals, entry, role):
    axis = entry["curveAxis"]
    buckets = {}
    for ev in evals:
        buckets.setdefault(group_key(ev, axis), []).append(ev)
    groups = []
    for key in sorted(buckets):
        members = buckets[key]
        inp = members[0]["inputs"]
        fixed_name = "speed_mm_s" if axis == "power" else "power_W"
        gid = f"{role}-{fixed_name.split('_')[0]}{key[0]:g}-d{key[1]:g}-T{key[2]:g}-L{key[3]:g}"
        xs = [m["x"] for m in members]
        curve = None
        if len(members) >= MIN_GROUP_POINTS and min(xs) < max(xs):
            curve = []
            for x in log_space(CURVE_LOW * min(xs), CURVE_HIGH * max(xs), CURVE_POINTS):
                p = x if axis == "power" else inp["power_W"]
                v = inp["speed_mm_s"] if axis == "power" else x
                s = call_served(entry["alloy"], p, v, inp["beam_um"], inp["preheat_C"], inp["layer_um"])
                curve.append({"x": x, "depth_um": s.get("depth_um") if s["status"] == "ok" else None,
                              "index": s.get("index") if _num(s.get("index")) else None, "status": s["status"]})
        points = sorted(members, key=lambda m: m["x"])
        groups.append({
            "id": gid, "beamRole": role,
            "fixed": {fixed_name: key[0], "beam_um": key[1], "preheat_C": key[2], "preheatBasis": inp["preheatBasis"],
                      "layer_um": key[3], "layerBasis": inp["layerBasis"]},
            "curve": curve,
            "points": [{"rowId": m["rowId"], "x": m["x"], "measured_um": m["measured_um"],
                        "measuredSd_um": m["measuredSd_um"], "served_um": m["served_um"], "index": m["index"],
                        "diffPct": m["diff"], "status": m["status"]} for m in points],
        })
    return groups


# ------------------------------------------------------------------------------------------------
# notes from the catalogue
# ------------------------------------------------------------------------------------------------
def _rule_used(ctx):
    return bool(ctx["entry"]["usedInServedDevelopment"])


def _rule_beam(ctx):
    return ctx["entry"]["beam"]["status"] in ("assumed", "unverified")


def _rule_datum(ctx):
    return str(ctx["entry"]["datum"]).lower().startswith("not stated")


def _rule_power(ctx):
    return "not resolved" in str(ctx["entry"]["powerBasis"]).lower()


def _rule_legacy(ctx):
    return ctx["entry"]["alloy"] == "IN625"


def _rule_powder(ctx):
    rows = ctx["rows"]
    return bool(rows) and all(_num(r.get("layer_um")) and r["layer_um"] > 0 for r in rows)


def _rule_extent(ctx):
    return any(e["reason"] == "EXTENT_NOT_COMPUTED" for e in ctx["evals"])


def _rule_research(ctx):
    return True


RULES = {"USED_IN_SERVED_DEVELOPMENT": _rule_used, "BEAM_ASSUMED_OR_UNVERIFIED": _rule_beam,
         "DATUM_UNSTATED": _rule_datum, "POWER_NOMINAL": _rule_power, "LEGACY_PROPERTIES_IN625": _rule_legacy,
         "POWDER_LAYER_FLAT_PLATE_MODEL": _rule_powder, "EXTENT_NOT_COMPUTED": _rule_extent,
         "RESEARCH_NOT_REQUESTED": _rule_research}


def notes_for(ctx, reasons):
    out = []
    for c in reasons["codes"]:
        rule = RULES.get(c["code"])
        if rule is None:
            raise DescriptiveRefusal(f"catalogue code {c['code']} has no rule")
        if rule(ctx):
            out.append({"code": c["code"], "sentence": c["sentence"], "source": c["source"], "locator": c["locator"]})
    return out


# ------------------------------------------------------------------------------------------------
# record
# ------------------------------------------------------------------------------------------------
def build_set(entry, rows, loader_prov, reasons):
    admit(entry)
    if loader_prov.get("fileSha256") != entry["tableSha256"]:
        raise DescriptiveRefusal(f"{entry['datasetId']}: loader table hash differs from the ledger")
    evals = evaluate_rows(rows, entry)
    groups = build_groups(evals, entry, "primary")
    deviation = [{"arm": "served", "beamRole": "primary", "beam_um": entry["beam"]["value_um"],
                  **deviation_block(evals, entry["alloy"])}]
    sens = entry["beam"].get("sensitivity_um")
    sens_evals = []
    if sens is not None:
        sens_evals = evaluate_rows(rows, entry, beam_override_um=sens)
        groups += build_groups(sens_evals, entry, "sensitivity")
        deviation.append({"arm": "served", "beamRole": "sensitivity", "beam_um": sens,
                          **deviation_block(sens_evals, entry["alloy"])})
    ctx = {"entry": entry, "rows": rows, "evals": evals + sens_evals}
    notes = notes_for(ctx, reasons)
    spent_by = [{"event": s["event"], "record": s["record"], "date": s["date"]} for s in entry["spentBy"]]
    view_set = {
        "id": entry["datasetId"], "title": entry["title"], "alloy": entry["alloy"], "observable": entry["observable"],
        "curveAxis": entry["curveAxis"],
        "provenance": {"citation": loader_prov.get("citation") or entry["attribution"], "doi": entry["doi"],
                       "licence": entry["licence"], "attribution": entry["attribution"],
                       "licenceFile": entry["licenceFile"], "tableSha256": entry["tableSha256"],
                       "rows": len(rows), "locator": entry["locator"], "loader": entry["loader"],
                       "datum": entry["datum"], "substrate": entry["substrate"], "powerBasis": entry["powerBasis"],
                       "transcription": entry["transcription"]},
        "spent": {"status": entry["status"], "spentBy": spent_by,
                  "usedInServedDevelopment": entry["usedInServedDevelopment"]},
        "beam": {"value_um": entry["beam"]["value_um"], "status": entry["beam"]["status"],
                 "definition": entry["beam"]["definition"], "sensitivity_um": sens},
        "measuredSource": {"label": "Measured", "transcription": entry["transcription"], "locator": entry["locator"]},
        "servedSource": {"label": "Unresolved", "reasonCode": SERVED_REASON_CODE, "reasonText": SERVED_REASON_TEXT},
        "groups": groups, "deviation": deviation, "notes": notes,
    }
    return view_set


def model_map(sets, ledger_by_id):
    """One row per experiment: sets that share sameExperimentsAs form one row keyed by the experiment."""
    rows, seen = [], {}
    for s in sets:
        entry = ledger_by_id[s["id"]]
        key = entry["sameExperimentsAs"] or s["id"]
        primary = next(d for d in s["deviation"] if d["beamRole"] == "primary")
        cells = [{"id": b["id"], "label": b["label"], "direction": b["direction"], "n": b["n"]} for b in primary["bins"]]
        if key in seen:
            seen[key]["alsoSets"].append(s["id"])
            continue
        row = {"key": key, "setId": s["id"], "label": s["title"], "alsoSets": [], "bins": cells}
        seen[key] = row
        rows.append(row)
    return rows


def served_identity(alloys):
    import lpbf_served_arms as arms
    ident = {a: arms.predictor_identity(a) for a in alloys}
    first = ident[alloys[0]]
    return {
        "servedClosurePinSha256": arms.pin_sha256(),
        "implementationFingerprint": first["implementationFingerprint"],
        "buildJobSolverRevision": first["buildJobSolverRevision"], "buildJobModelId": first["buildJobModelId"],
        "heatSource": first["heatSource"], "absorptionModel": first["absorptionModel"],
        "includeProcessMap": first["includeProcessMap"],
        "alloys": {a: {"servedPath": i["servedPath"], "materialPropertySha256": i["materialPropertySha256"],
                       "buildJobIdentitySha256": i["buildJobIdentitySha256"]} for a, i in ident.items()},
    }, {a: {"python": i["python"], "numpy": i["numpy"], "scipy": i["scipy"]} for a, i in ident.items()}


def build_record(ledger=None, reasons=None, rows_source=None, identity=None, generated_at=None):
    """Returns (view, full). Raises DescriptiveRefusal before any loading when an entry is not admissible."""
    from lpbf_spent_ledger import load_ledger, ledger_sha256, LEDGER_PATH
    default_ledger = ledger is None
    ledger = load_ledger() if default_ledger else ledger
    reasons = reasons if reasons is not None else load_reasons()
    rows_source = rows_source or default_rows
    by_id = {e["datasetId"]: e for e in ledger["entries"]}
    chosen = [e for e in ledger["entries"] if e["datasetId"] in SUPPORTED_SETS or e["datasetId"] not in
              {d["datasetId"] for d in DEFERRED_SETS}]
    for e in chosen:
        admit(e)  # refuses before any row is read
    sets, full_rows = [], {}
    for e in chosen:
        rows, prov = rows_source(e)
        s = build_set(e, rows, prov, reasons)
        sets.append(s)
        full_rows[e["datasetId"]] = [{"rowId": r["rowId"], "loaderRow": {k: r.get(k) for k in
                                      ("power_W", "speed_mm_s", "beamDiameter_um", "preheat_C", "layer_um",
                                       "depth_um", "width_um")}} for r in rows]
    ident_pair = identity if identity is not None else served_identity(sorted({e["alloy"] for e in chosen}))
    served_ident, env = ident_pair
    from lpbf_simulation import implementation_fingerprint
    impl = served_ident.get("implementationFingerprint") or implementation_fingerprint()
    deferred = [dict(d) for d in DEFERRED_SETS]
    gen = generated_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    view = {
        "schema": VIEW_SCHEMA, "generatedAt": gen, "implementationHash": impl, "servedIdentity": served_ident,
        "research": {"requested": False, "reasonCode": RESEARCH_REASON},
        "spentLedgerSha256": ledger_sha256(LEDGER_PATH) if default_ledger else hashlib.sha256(canonical_bytes(ledger)).hexdigest(),
        "reasonsCatalogSha256": sha256_lf(REASONS_PATH),
        "honesty": {"label": BADGE, "statement": STATEMENT, "experimentalValidation": False,
                    "labelPromotionProposed": "none", "evidenceKind": "screening-only", "spentOnly": True},
        "arms": [
            {"id": "served", "label": "Served model (flat-plate Rosenthal, build job thermal path)",
             "sourceLabel": "Unresolved", "reasonCode": SERVED_REASON_CODE, "reasonText": SERVED_REASON_TEXT},
            {"id": "research", "label": "Research model", "availability": f"unavailable: {RESEARCH_REASON}"},
        ],
        "sets": sets, "modelMap": model_map(sets, by_id), "directionRule": DIRECTION_RULE, "deferred": deferred,
    }
    view = round_tree(view)
    full = round_tree({**view, "schema": FULL_SCHEMA, "environment": env, "rows": full_rows})
    return view, full


def _strip_time(rec):
    return {k: v for k, v in rec.items() if k != "generatedAt"}


def output_paths(date, out_dir=DOCS):
    d = Path(out_dir)
    return d / f"LPBF_SPENT_DESCRIPTIVE_{date}.json", d / f"LPBF_SPENT_DESCRIPTIVE_{date}.view.json"


def summary_lines(view, full_bytes, view_bytes):
    lines = [f"view bytes {len(view_bytes)}", f"full bytes {len(full_bytes)}",
             f"implementationHash {view['implementationHash']}",
             f"servedClosurePinSha256 {view['servedIdentity']['servedClosurePinSha256']}",
             f"spentLedgerSha256 {view['spentLedgerSha256']}", f"reasonsCatalogSha256 {view['reasonsCatalogSha256']}"]
    for s in view["sets"]:
        curves = sum(1 for g in s["groups"] if g["curve"])
        lines.append(f"{s['id']}: rows {s['provenance']['rows']} groups {len(s['groups'])} curves {curves} "
                     f"notes {len(s['notes'])}")
    return lines


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="re-derive and compare with the committed files")
    ap.add_argument("--date", default=DATE)
    ap.add_argument("--out-dir", default=str(DOCS))
    a = ap.parse_args(argv)
    # Flat-plate pin as in lpbf_dataset_comparison.pin_flat_plate(allow_raytracer=False).
    sys.modules["powder_bed_raytracer"] = None
    view, full = build_record()
    view_bytes, full_bytes = canonical_bytes(view), canonical_bytes(full)
    if len(view_bytes) >= MAX_VIEW_BYTES:
        print(f"view record is {len(view_bytes)} bytes, over the {MAX_VIEW_BYTES} byte cap")
        return 2
    full_path, view_path = output_paths(a.date, a.out_dir)
    if a.check:
        ok = True
        for path, rec in ((full_path, full), (view_path, view)):
            if not path.is_file():
                print(f"{path.name}: missing")
                ok = False
                continue
            current = json.loads(path.read_text(encoding="utf-8"))
            same = canonical_bytes(_strip_time(current)) == canonical_bytes(_strip_time(rec))
            print(f"{path.name}: {'current' if same else 'differs from the re-derivation'}")
            ok &= same
        return 0 if ok else 1
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_bytes(full_bytes)
    view_path.write_bytes(view_bytes)
    for line in summary_lines(view, full_bytes, view_bytes):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
