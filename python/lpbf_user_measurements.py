"""Import of the user's OWN single-track measurements for a planned experiment (``lpbf_next_experiment`` plan).

The user prints the proposed tracks, measures width and depth, fills ``measurement_template.csv`` and imports it
here. The import joins on ``track_id`` with identical power / speed / spot to the plan, validates the numbers and
writes ``.runtime/user-calibration/<source-id>/rows.json`` with provenance. Those rows can then be passed to the
calibration scorecard tool (``--user-source``) as one extra trainable source, in a private output directory.

Honesty rules:
- a row label is exactly ``Measured (user-supplied)``: it describes the user's own data only, it is not promoted and
  says nothing about the screening model;
- width and depth must be finite and positive; a blank cell excludes the track with a reason, nothing is imputed;
- a track whose power / speed / spot differs from the plan, an unknown or repeated track id, and a malformed
  number are refused (no partial import);
- the source id must match ``^user-[a-z0-9-]{3,40}$`` and must not collide with an existing source or an existing
  import directory.

SCREENING ONLY. Nothing here touches the frozen physics.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from lpbf_calibration_config import CALIBRATION_CONFIG, USER_SOURCE_ID_PATTERN

ROWS_SCHEMA = "lpbf-user-measurements-1"
PLAN_SCHEMA = "lpbf-next-experiment-plan-1"
ROW_LABEL = "Measured (user-supplied)"
EVIDENCE_KIND = "screening-only"
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ROOT = REPO_ROOT / ".runtime" / "user-calibration"
TEMPLATE_COLUMNS = ("track_id", "power_W", "speed_mm_s", "spot_um", "width_um", "depth_um", "notes")
# Optional measurement-method columns (machine calibration plans add them to the template). Blank means "not stated";
# nothing is imputed. A filled row carries them in ``row["method"]``; a row with none filled has no ``method`` key.
METHOD_COLUMNS = ("depthDatum", "beamDiameterDefinition", "measuredPowerW", "crossSectionLocation", "replicates")


class UserMeasurementError(ValueError):
    """The measurement file cannot be imported; nothing was written."""


def known_source_ids() -> List[str]:
    roles = CALIBRATION_CONFIG["dataRoles"]
    return sorted(set(roles["trainable"]) | set(roles["catalogSentinels"]))


def check_source_id(source_id: str, existing_sources: Optional[Sequence[str]] = None) -> str:
    if not isinstance(source_id, str) or not re.match(USER_SOURCE_ID_PATTERN, source_id):
        raise UserMeasurementError(f"source id {source_id!r} must match {USER_SOURCE_ID_PATTERN}")
    taken = set(known_source_ids()) | set(existing_sources or ())
    if source_id in taken:
        raise UserMeasurementError(f"source id {source_id!r} collides with an existing source")
    return source_id


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _plan_points(plan: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    if not isinstance(plan, dict) or plan.get("schema") != PLAN_SCHEMA:
        raise UserMeasurementError(f"plan schema must be {PLAN_SCHEMA}")
    pts = plan.get("points")
    if not isinstance(pts, list) or not pts:
        raise UserMeasurementError("plan has no points")
    out: Dict[str, Dict[str, Any]] = {}
    for p in pts:
        tid = p.get("trackId")
        if not isinstance(tid, str) or tid in out:
            raise UserMeasurementError(f"plan has a missing or repeated track id: {tid!r}")
        out[tid] = p
    return out


def _num(text: Any, what: str, tid: str) -> float:
    try:
        v = float(str(text).strip())
    except ValueError as exc:
        raise UserMeasurementError(f"{tid}: {what} {text!r} is not a number") from exc
    return v


def parse_measurement_csv(text: str) -> List[Dict[str, str]]:
    reader = csv.DictReader(io.StringIO(text.lstrip("﻿")))
    need = {"track_id", "power_W", "speed_mm_s", "spot_um", "width_um", "depth_um"}
    if reader.fieldnames is None or not need <= set(reader.fieldnames):
        raise UserMeasurementError(f"measurement CSV needs the columns {sorted(need)}")
    return [dict(r) for r in reader]


def _method_block(r: Dict[str, str], tid: str) -> Optional[Dict[str, Any]]:
    """The filled optional method columns of one CSV row as a dict, or None when none is filled."""
    block: Dict[str, Any] = {}
    for col in METHOD_COLUMNS:
        raw = (r.get(col) or "").strip()
        if not raw:
            continue
        if col == "measuredPowerW":
            v = _num(raw, col, tid)
            if not (math.isfinite(v) and v > 0):
                raise UserMeasurementError(f"{tid}: {col} must be finite and positive, got {raw!r} "
                                           "(leave the cell blank if not measured)")
            block[col] = v
        elif col == "replicates":
            v = _num(raw, col, tid)
            if not (math.isfinite(v) and v >= 1 and v == int(v)):
                raise UserMeasurementError(f"{tid}: {col} must be a whole number >= 1, got {raw!r}")
            block[col] = int(v)
        else:
            block[col] = raw
    return block or None


def build_rows(plan: Dict[str, Any], csv_rows: Sequence[Dict[str, str]], source_id: str) -> Dict[str, Any]:
    """Join, validate, return {'rows': [...], 'excluded': [...]}; raises UserMeasurementError on any inconsistency."""
    pts = _plan_points(plan)
    material = plan.get("material")
    if not isinstance(material, str) or not material:
        raise UserMeasurementError("plan has no material")
    rows: List[Dict[str, Any]] = []
    excluded: List[Dict[str, str]] = []
    seen = set()
    for r in csv_rows:
        tid = (r.get("track_id") or "").strip()
        if not tid:
            continue  # a wholly blank line is not a track
        if tid in seen:
            raise UserMeasurementError(f"track id {tid} appears more than once in the measurement file")
        seen.add(tid)
        p = pts.get(tid)
        if p is None:
            raise UserMeasurementError(f"track id {tid} is not in the plan")
        for col, key, what in (("power_W", "power_W", "power"), ("speed_mm_s", "speed_mm_s", "speed"),
                               ("spot_um", "beamDiameter_um", "spot diameter")):
            got = _num(r.get(col), what, tid)
            if got != float(p[key]):
                raise UserMeasurementError(f"{tid}: {what} {got:g} differs from the plan ({float(p[key]):g}); "
                                           "the join needs identical power, speed and spot")
        w_raw, d_raw = (r.get("width_um") or "").strip(), (r.get("depth_um") or "").strip()
        if not w_raw or not d_raw:
            missing = " and ".join(n for n, v in (("width_um", w_raw), ("depth_um", d_raw)) if not v)
            excluded.append({"trackId": tid, "reason": f"missing {missing}: excluded, never imputed"})
            continue
        w, d = _num(w_raw, "width_um", tid), _num(d_raw, "depth_um", tid)
        for name, v in (("width_um", w), ("depth_um", d)):
            if not (math.isfinite(v) and v > 0):
                raise UserMeasurementError(f"{tid}: {name} must be finite and positive, got {v!r} "
                                           "(leave the cell blank to exclude the track)")
        row = {"rowId": f"{source_id}-{tid}", "trackId": tid, "source": source_id, "material": material,
               "power_W": float(p["power_W"]), "speed_mm_s": float(p["speed_mm_s"]),
               "beamDiameter_um": float(p["beamDiameter_um"]), "preheat_C": float(p["preheat_C"]),
               "layer_um": float(p["layer_um"]), "hatch_um": None, "width_um": w, "depth_um": d,
               "balling": None, "publishedLabel": None, "catalog": False, "label": ROW_LABEL}
        method = _method_block(r, tid)
        if method is not None:
            row["method"] = method
        rows.append(row)
    for tid in sorted(set(pts) - seen):
        excluded.append({"trackId": tid, "reason": "no row in the measurement file: excluded, never imputed"})
    if not rows:
        raise UserMeasurementError("no usable measurement rows (every track is blank or excluded)")
    return {"rows": rows, "excluded": sorted(excluded, key=lambda e: e["trackId"])}


def _utc_now_iso() -> str:
    """Import time in UTC with millisecond precision (read by the blind test exposure check)."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def import_measurements(plan_path: Any, measurements_path: Any, source_id: str, *, out_root: Any = None,
                        existing_sources: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    """Validate, write ``<out_root>/<source_id>/rows.json`` and return the document that was written."""
    check_source_id(source_id, existing_sources)
    plan_bytes = Path(plan_path).read_bytes()
    meas_bytes = Path(measurements_path).read_bytes()
    try:
        plan = json.loads(plan_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UserMeasurementError(f"plan is not valid JSON: {exc}") from exc
    built = build_rows(plan, parse_measurement_csv(meas_bytes.decode("utf-8")), source_id)
    root = Path(out_root) if out_root is not None else DEFAULT_ROOT
    target = root / source_id
    if target.exists():
        raise UserMeasurementError(f"{target} already exists: refusing to overwrite an earlier import")
    doc = {"schema": ROWS_SCHEMA, "sourceId": source_id, "label": ROW_LABEL, "evidenceKind": EVIDENCE_KIND,
           "material": plan["material"],
           "provenance": {"planSha256": _sha256_bytes(plan_bytes), "planSchema": plan["schema"],
                          "importedAt": _utc_now_iso(),
                          "measurementsSha256": _sha256_bytes(meas_bytes),
                          "statement": ("single-track widths and depths supplied by the user from their own prints; "
                                        "joined to the plan on track_id with identical power, speed and spot; not "
                                        "independently verified; no per-row measurement uncertainty")},
           "nRows": len(built["rows"]), "nExcluded": len(built["excluded"]),
           "rows": built["rows"], "excluded": built["excluded"]}
    target.mkdir(parents=True, exist_ok=False)
    (target / "rows.json").write_text(json.dumps(doc, sort_keys=True, indent=1, allow_nan=False) + "\n",
                                      encoding="utf-8", newline="\n")
    return doc


def load_user_rows(path: Any) -> Dict[str, Any]:
    """Read and re-validate a ``rows.json`` written by :func:`import_measurements` (used by the scorecard hook)."""
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise UserMeasurementError(f"cannot read user rows {path}: {exc}") from exc
    if not isinstance(doc, dict) or doc.get("schema") != ROWS_SCHEMA:
        raise UserMeasurementError(f"{path}: schema must be {ROWS_SCHEMA}")
    sid = doc.get("sourceId")
    if not isinstance(sid, str) or not re.match(USER_SOURCE_ID_PATTERN, sid):
        raise UserMeasurementError(f"{path}: bad source id {sid!r}")
    if sid in known_source_ids():
        raise UserMeasurementError(f"{path}: source id {sid!r} collides with an existing source")
    rows = doc.get("rows")
    if not isinstance(rows, list) or not rows:
        raise UserMeasurementError(f"{path}: no rows")
    for r in rows:
        if r.get("source") != sid or r.get("label") != ROW_LABEL or r.get("catalog") is not False:
            raise UserMeasurementError(f"{path}: row {r.get('rowId')!r} is not a user-supplied row of {sid}")
        for k in ("power_W", "speed_mm_s", "beamDiameter_um", "preheat_C", "layer_um", "width_um", "depth_um"):
            v = r.get(k)
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0:
                raise UserMeasurementError(f"{path}: row {r.get('rowId')!r} has a bad {k}")
        if not (r["width_um"] > 0 and r["depth_um"] > 0):
            raise UserMeasurementError(f"{path}: row {r.get('rowId')!r} width/depth must be positive")
    return doc
