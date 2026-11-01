"""Scoring phase intake of the user blind test: the targets CSV (spec 4.4, 6.1).

Exact join on the frozen key set, `depth_status` rules, ranges with unit hints, repeated-input check. Refusals cite rows
and columns, never a value: a range hint is computed from the value but never prints it.
"""
from __future__ import annotations

import math

from lpbf_user_blind_inputs import decode_text, iter_rows, map_header, parse_number, read_csv, check_id
from lpbf_user_blind_protocol import (
    DEPTH_STATUS, INPUT_ALIASES, TARGET_ALIASES, TARGET_COLUMNS, TARGET_RANGES, BlindRefusal,
)

REPEATABLE_INPUTS = ("power_W", "speed_mm_s", "spot_um", "power_u_k1_W")


def _key_text(key_columns, key):
    return ", ".join(f"{c} {v}" for c, v in zip(key_columns, key))


def parse_targets(raw_bytes, freeze, field="targetsCsvBase64"):
    """Returns {"byOrdinal": {frozen ordinal: target}, "ignored": [header names]}. Raises BlindRefusal."""
    md = freeze["metadata"]
    text = decode_text(raw_bytes, field)
    header, reader = read_csv(text, md["csvDialect"], field)
    columns = tuple(TARGET_COLUMNS) + REPEATABLE_INPUTS
    aliases = dict(TARGET_ALIASES)
    for c in REPEATABLE_INPUTS:
        aliases[c] = INPUT_ALIASES.get(c, ())
    mapped, _echo, _labels, ignored = map_header(header, columns, aliases, field, inputs=False)
    key_columns = list(freeze["keyColumns"])
    for need in key_columns + ["depth_um"]:
        if need not in mapped:
            raise BlindRefusal("TARGETS_COLUMN_MISSING", field=field, name=need,
                               aliases=", ".join(aliases.get(need, ())) or "none", detail={"column": need})
    ignored += [mapped[c][1] for c in ("condition_id", "track_id", "section_id") if c in mapped and c not in key_columns]
    data = iter_rows(reader, header, field)
    frozen = {tuple(r[c] for c in key_columns): r for r in freeze["rows"]}
    dialect = md["csvDialect"]
    per_row = md["depthUncertainty"]["basis"] == "per-row"
    seen, dup, extra, out = {}, [], [], {}
    for line, cells in data:
        def cell(c):
            return cells[mapped[c][0]] if c in mapped else ""
        key = []
        for c in key_columns:
            v = cell(c)
            if not v:
                raise BlindRefusal("ID_INVALID", field=field, row=line, col=mapped[c][1],
                                   detail={"row": line, "column": mapped[c][1]})
            key.append(check_id(v, line, mapped[c][1], field))
        key = tuple(key)
        if key in seen:
            dup.append(key)
            continue
        seen[key] = line
        row = frozen.get(key)
        if row is None:
            extra.append(key)
            continue
        status = cell("depth_status").strip().lower() or "measured"
        if status not in DEPTH_STATUS:
            raise BlindRefusal("TARGET_STATUS_UNKNOWN", field=field, row=line, detail={"row": line})
        depth_cell, width_cell, u_cell = cell("depth_um"), cell("width_um"), cell("depth_u_um")
        target = {"row": line, "status": status, "depth_um": None, "width_um": None, "u_um": None}
        if status == "measured":
            if not depth_cell:
                raise BlindRefusal("TARGET_DEPTH_INVALID", field=field, row=line, detail={"row": line})
            d = parse_number(depth_cell, dialect, line, mapped["depth_um"][1], field)
            if not d > 0:
                raise BlindRefusal("TARGET_DEPTH_INVALID", field=field, row=line, detail={"row": line})
            _range(d, "depth_um", line, mapped["depth_um"][1], field)
            target["depth_um"] = d
            if width_cell:
                w = parse_number(width_cell, dialect, line, mapped["width_um"][1], field)
                _range(w, "width_um", line, mapped["width_um"][1], field)
                target["width_um"] = w
            if u_cell:
                u = parse_number(u_cell, dialect, line, mapped["depth_u_um"][1], field)
                if not (0 < u < d):
                    raise BlindRefusal("TARGET_OUT_OF_RANGE", field=field, row=line, col=mapped["depth_u_um"][1],
                                       lo="above 0", hi="below the row's depth_um",
                                       hint="Check the uncertainty column.",
                                       detail={"row": line, "column": mapped["depth_u_um"][1]})
                target["u_um"] = u
            elif per_row:
                raise BlindRefusal("U_PER_ROW_MISSING", field=field, row=line, detail={"row": line})
        elif depth_cell:
            raise BlindRefusal("TARGET_STATUS_CONFLICT", field=field, row=line, status=status, detail={"row": line})
        for c in REPEATABLE_INPUTS:
            v = cell(c)
            if c not in mapped or not v:
                continue
            x = parse_number(v, dialect, line, mapped[c][1], field) * mapped[c][2]
            ref = {"power_W": row["P_W"], "speed_mm_s": row["v_mm_s"], "spot_um": row["d_declared_um"],
                   "power_u_k1_W": row["P_u_k1_W"]}[c]
            if ref is None or not math.isclose(x, ref, rel_tol=1e-9, abs_tol=1e-9):
                raise BlindRefusal("INPUT_REPEAT_MISMATCH", field=field, row=line, col=mapped[c][1],
                                   detail={"row": line, "column": mapped[c][1]})
        out[row["ordinal"]] = target
    missing = [k for k in frozen if k not in seen]
    if missing or extra or dup:
        first = (missing or extra or dup)[0]
        raise BlindRefusal("TARGETS_KEYS_MISMATCH", field=field, m=len(missing), e=len(extra), d=len(dup),
                           first=_key_text(key_columns, first),
                           detail={"missing": len(missing), "extra": len(extra), "duplicate": len(dup)})
    # track-not-formed must cover every section of its track; u per condition constant.
    rows_by_track, u_by_cond = {}, {}
    for r in freeze["rows"]:
        rows_by_track.setdefault((r["condition"], r["track"]), []).append(r["ordinal"])
    for (_cond, track), ords in rows_by_track.items():
        sts = [out[o]["status"] for o in ords]
        if "track-not-formed" in sts and any(s != "track-not-formed" for s in sts):
            bad = next(out[o]["row"] for o in ords if out[o]["status"] != "track-not-formed")
            raise BlindRefusal("TARGET_STATUS_CONFLICT", field=field, variant="track", row=bad, detail={"row": bad})
    for r in freeze["rows"]:
        t = out[r["ordinal"]]
        if t["status"] == "measured" and per_row:
            prev = u_by_cond.setdefault(r["condition"], t["u_um"])
            if not math.isclose(prev, t["u_um"], rel_tol=1e-12):
                raise BlindRefusal("U_PER_ROW_VARIES", field=field, id=r["condition"], detail={"condition": r["condition"]})
    return {"byOrdinal": out, "ignored": ignored}


def _range(x, col, line, header, field):
    lo, hi = TARGET_RANGES[col]
    if lo <= x <= hi:
        return
    hint = ("values look like millimetres; enter micrometres" if x < lo
            else "values look like nanometres or a wrong column")
    raise BlindRefusal("TARGET_OUT_OF_RANGE", field=field, row=line, col=header, lo=f"{lo:g}", hi=f"{hi:g}",
                       hint=hint, detail={"row": line, "column": header})
