"""Exposure facts for the user blind test (spec 6.4): overlap with other tests on this computer, with the calibration
stores, with the spent ledger and with Build Job history.

Read only. Every reader keeps alloy, power, speed and beam only and drops measured fields at parse, so no width or
depth value from a calibration store or a published set can reach an output. Tuples match at the 1 % rule.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from lpbf_user_blind_store import REPO_ROOT, Store, parse_time, tuples_match, utc_iso


def _alloy_of(material):
    from lpbf_spent_ledger import _protocol_alloy
    return _protocol_alloy(material)


def _matches(alloy, tuples, other_alloy, other_tuples):
    if alloy != other_alloy:
        return 0
    return sum(1 for t in tuples if any(tuples_match(t, o) for o in other_tuples))


def store_exposures(store, alloy, tuples, exclude_key=None):
    """Other tests on this computer that were revealed or scored: [{freezeKey, kind, seq, at, nConditions}]."""
    entries = store.index_entries() or []
    by_key = {e["freezeKey"]: e for e in entries}
    ledger = store.ledger()
    out = []
    for e in ledger:
        if e.get("event") not in ("revealed", "scored") or e.get("freezeKey") in (None, exclude_key):
            continue
        idx = by_key.get(e["freezeKey"])
        if idx is None:
            continue
        k = _matches(alloy, tuples, idx["alloy"], [tuple(t) for t in idx["tuples"]])
        if k:
            out.append({"freezeKey": e["freezeKey"], "kind": e["event"], "seq": e["seq"], "at": e["at"],
                        "nConditions": k})
    return out


def _calibration_roots():
    user_root = REPO_ROOT / ".runtime" / "user-calibration"
    mc = os.environ.get("LPBF_MACHINE_CALIBRATION_DIR")
    mc_root = Path(mc) if mc else REPO_ROOT / ".runtime" / "machine-calibration"
    return user_root, mc_root


def _mtime_iso(path):
    return utc_iso(datetime.fromtimestamp(path.stat().st_mtime, timezone.utc))


def calibration_exposures(alloy, tuples, roots=None):
    """[{storeId, kind, at, nConditions}] for user-calibration imports and machine-calibration artefacts."""
    user_root, mc_root = roots or _calibration_roots()
    out, sources = [], {}
    if user_root.is_dir():
        for p in sorted(user_root.glob("*/rows.json")):
            try:
                doc = json.loads(p.read_text(encoding="utf-8"))
                rows = [(float(r["power_W"]), float(r["speed_mm_s"]), float(r["beamDiameter_um"]))
                        for r in doc.get("rows", [])]
                mat = _alloy_of(doc.get("material"))
            except (OSError, ValueError, KeyError, TypeError):
                continue
            sources[doc.get("sourceId") or p.parent.name] = (mat, rows)
            k = _matches(alloy, tuples, mat, rows)
            if k:
                imported = utc_iso((doc.get("provenance") or {}).get("importedAt"))
                out.append({"storeId": p.parent.name, "kind": "user-calibration", "at": imported or _mtime_iso(p),
                            "timeBasis": "import time" if imported else "file modification time (no import time)",
                            "nConditions": k})
    if mc_root.is_dir():
        for p in sorted(mc_root.glob("*/machine-calibration.json")):
            try:
                art = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            mat = _alloy_of(art.get("material"))
            rows = list((sources.get(art.get("userSourceId")) or (None, []))[1])
            for cell in art.get("cells") or []:
                for t in (cell.get("tracks") or []) if isinstance(cell, dict) else []:
                    key = t.get("key") if isinstance(t, dict) else None
                    if isinstance(key, list) and len(key) == 3:
                        rows.append(tuple(float(x) for x in key))
            k = _matches(alloy, tuples, mat, rows)
            if k:
                generated = utc_iso(art.get("generatedAt"))
                out.append({"storeId": art.get("machineCalibrationId") or p.parent.name, "kind": "machine-calibration",
                            "at": generated or _mtime_iso(p),
                            "timeBasis": "artefact time" if generated else "file modification time",
                            "nConditions": k})
    return out


def spent_set_exposures(alloy, tuples):
    """[{datasetId, nConditions}] for spent-ledger sets with a loader (inputs only)."""
    from lpbf_spent_ledger import spent_condition_tuples
    out = []
    for ds, rows in spent_condition_tuples().items():
        k = sum(1 for t in tuples if any(a == alloy and tuples_match(t, (P, v, d)) for a, P, v, d in rows))
        if k:
            out.append({"datasetId": ds, "nConditions": k})
    return out


_BUILD_JOB_ALLOY = {"ti6al4v": "Ti-6Al-4V", "alsi10mg": "AlSi10Mg", "ss316l": "316L", "in718": "IN718"}


def build_job_history(alloy, tuples, before=None, job_root=None):
    """Completed Build Jobs on this workstation with the same setting (partial check, Build Job history only)."""
    root = Path(job_root) if job_root else Path(os.environ.get("METALLIKSA_JOB_ROOT",
                                                               str(REPO_ROOT / ".lpbf-jobs")))
    if not root.is_dir():
        return []
    from four_alloy_materials import resolve_alloy_id
    n, latest = 0, None
    matched = set()
    for d in root.iterdir():
        inp, res = d / "input.json", d / "result.json"
        if not res.is_file() or not inp.is_file():
            continue
        try:
            p = json.loads(inp.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(p, dict) or p.get("jobType") != "build-job":
            continue
        a = _BUILD_JOB_ALLOY.get(resolve_alloy_id(p.get("alloyId") or "in718") or "")
        if a != alloy:
            continue
        at = _mtime_iso(res)
        if before is not None and parse_time(at) >= before:
            continue
        try:
            t = (float(p.get("laserPower_W", 285.0)), float(p.get("scanSpeed_mm_s") or p.get("scanSpeed_mms") or 960.0),
                 float(p.get("beamDiameter_um", 80.0)))
        except (TypeError, ValueError):
            continue
        for i, c in enumerate(tuples):
            if tuples_match(c, t):
                matched.add(i)
                latest = max(latest or at, at)
    n = len(matched)
    return [{"source": "build-job-history", "nConditions": n, "latestAt": latest}] if n else []


def preview_overlap(store, alloy, tuples):
    """Overlap block of the preview (counts and ids only)."""
    return {"earlierTests": [{"freezeKey": e["freezeKey"], "kind": e["kind"], "nConditions": e["nConditions"]}
                             for e in store_exposures(store, alloy, tuples)],
            "publishedSets": spent_set_exposures(alloy, tuples),
            "calibrationStores": [{"storeId": e["storeId"], "kind": e["kind"], "nConditions": e["nConditions"]}
                                  for e in calibration_exposures(alloy, tuples)],
            "buildJobHistory": [{"nConditions": e["nConditions"]} for e in build_job_history(alloy, tuples)]}
