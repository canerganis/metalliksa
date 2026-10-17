"""Prediction phase intake of the user blind test: metadata, the inputs CSV, grades, block issues and design checks.

Research hub spec sections 4.1, 4.2, 4.3, 6.1 to 6.3 and 7.4. This module never imports the targets parser
(`lpbf_user_blind_targets`) or the scorer, and it calls no thermal solver: the only model call is the analytic served
index (`lpbf_public_datasets.normalized_enthalpy`), used for leverage bin counts.

Every refusal is a `BlindRefusal` with a closed code; messages cite rows (1-based file lines, the header is row 1) and
column names, never a cell value.
"""
from __future__ import annotations

import base64
import binascii
import csv
import io
import math
import re

import lpbf_blind_stats as stats
from lpbf_user_blind_protocol import (
    ALLOYS, BLOCK_LABEL_RE, CANONICAL_UNIT, CAPS, ENUMS, FILE_NAME_RE, FORMULA_START, ID_RE, INPUT_ALIASES,
    INPUT_COLUMNS, LAYER_RANGE, LEVERAGE_LOW_CUT, METADATA_SCHEMA, PREHEAT_RANGE, RANGES, SCORED_ALLOYS,
    SYNTHETIC_MARKER, TARGET_LIKE_EXACT, TARGET_LIKE_RE, UNITLESS_HEADERS, UNITS, WAVELENGTH_RANGE, BlindRefusal,
)

_ID = re.compile(ID_RE)
_FILE_NAME = re.compile(FILE_NAME_RE)
_BLOCK_LABEL = re.compile(BLOCK_LABEL_RE)
_TARGET_LIKE = re.compile(TARGET_LIKE_RE, re.IGNORECASE)
_PLAIN_DOT = re.compile(r"^[0-9]+(\.[0-9]+)?$|^\.[0-9]+$")
_PLAIN_COMMA = re.compile(r"^[0-9]+(,[0-9]+)?$|^,[0-9]+$")
_UNIT_SUFFIX = re.compile(r"^(?P<base>.*?)\s*(?:\((?P<b1>[^()]*)\)|\[(?P<b2>[^\[\]]*)\])\s*$")
_UNDERSCORE_UNIT = re.compile(r"^(?P<base>.+?)_(?P<unit>W|kW|mm_s|m_s|mm_min|um|mm)$", re.IGNORECASE)


# ---------------------------------------------------------------------------------------------- file handling
def check_file_name(name, field):
    if not isinstance(name, str) or not _FILE_NAME.match(name) or name[0] in FORMULA_START or name.startswith("."):
        raise BlindRefusal("FILE_NAME_INVALID", field=field)
    return name


def decode_upload(b64, field):
    """base64 field -> raw bytes, with the 350,000 character and 256 KiB caps."""
    if not isinstance(b64, str):
        raise BlindRefusal("METADATA_FIELD", field=field, message=f"Field '{field}' must be base64 text.")
    if len(b64) > CAPS["base64Chars"]:
        raise BlindRefusal("SIZE_CAP", field=field, cap="256 KiB")
    try:
        raw = base64.b64decode(b64, validate=True)
    except (binascii.Error, ValueError):
        raise BlindRefusal("FILE_NOT_CSV_UTF8", field=field) from None
    if len(raw) > CAPS["fileBytes"]:
        raise BlindRefusal("SIZE_CAP", field=field, cap="256 KiB")
    return raw


def decode_text(raw, field):
    """UTF-8 text with the BOM stripped; zip (xlsx) bytes and invalid UTF-8 refuse. At most 256 KiB (4.2 item 9)."""
    if len(raw) > CAPS["fileBytes"]:
        raise BlindRefusal("SIZE_CAP", field=field, cap="256 KiB")
    if raw[:4] == b"PK\x03\x04":
        raise BlindRefusal("FILE_NOT_CSV_UTF8", field=field)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise BlindRefusal("FILE_NOT_CSV_UTF8", field=field) from None
    if text.startswith("﻿"):
        text = text[1:]
    if "\x00" in text:
        raise BlindRefusal("FILE_NOT_CSV_UTF8", field=field)
    return text


DIALECTS = {"comma-dot": (",", "."), "semicolon-dot": (";", "."), "semicolon-comma": (";", ",")}


def read_csv(text, dialect, field):
    """Header and data rows as [(row number, cells)]. Header sniff first (DIALECT_MISMATCH at header level)."""
    sep, _dec = DIALECTS[dialect]
    first = text.split("\n", 1)[0]
    if sep == "," and ";" in first and "," not in first:
        raise BlindRefusal("DIALECT_MISMATCH", field=field, variant="header", found="semicolons",
                           declared="comma separated", choice="a semicolon format", detail={"row": 1})
    if sep == ";" and "," in first and ";" not in first:
        raise BlindRefusal("DIALECT_MISMATCH", field=field, variant="header", found="commas",
                           declared="semicolon separated", choice="the comma format", detail={"row": 1})
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=sep, strict=True)
    try:
        header = next(reader)
    except StopIteration:
        raise BlindRefusal("FILE_EMPTY", field=field) from None
    except csv.Error:
        raise BlindRefusal("CSV_MALFORMED", field=field, row=1, why="unterminated quote",
                           detail={"row": 1}) from None
    header = [h.strip() for h in header]
    return header, reader


def iter_rows(reader, header, field):
    rows = []
    while True:
        try:
            cells = next(reader)
        except StopIteration:
            break
        except csv.Error:
            raise BlindRefusal("CSV_MALFORMED", field=field, row=reader.line_num, why="unterminated quote",
                               detail={"row": reader.line_num}) from None
        if not cells or all(not c.strip() for c in cells):
            continue
        if len(cells) != len(header):
            raise BlindRefusal("CSV_MALFORMED", field=field, row=reader.line_num,
                               why="field count differs from the header", detail={"row": reader.line_num})
        rows.append((reader.line_num, [c.strip() for c in cells]))
        if len(rows) > CAPS["rows"]:
            raise BlindRefusal("SIZE_CAP", field=field, cap=f"{CAPS['rows']} rows")
    if not rows:
        raise BlindRefusal("FILE_EMPTY", field=field)
    return rows


def split_unit(header):
    """('Speed', 'm/s') for 'Speed (m/s)' or 'speed [m/s]'; (header, None) otherwise."""
    m = _UNIT_SUFFIX.match(header)
    if m and m.group("base").strip():
        return m.group("base").strip(), (m.group("b1") if m.group("b1") is not None else m.group("b2")).strip()
    return header, None


def map_header(header, columns, aliases, field, *, inputs):
    """Map header names to canonical columns. Returns {canonical: (index, header, unit factor, unit read)},
    alias echoes, labels, ignored headers (targets only)."""
    lookup = {}
    for canon in columns:
        lookup[canon.casefold()] = canon
        for a in aliases.get(canon, ()):
            lookup[a.casefold()] = canon
    mapped, echoes, labels, ignored = {}, [], [], []
    for i, name in enumerate(header):
        folded = name.casefold()
        canon = lookup.get(folded)
        factor, unit_read = 1.0, None
        if canon is None:
            base, unit = split_unit(name)
            base_canon = lookup.get(base.casefold()) or UNITLESS_HEADERS.get(base.casefold())
            if base_canon is None:
                for c in columns:
                    if base.casefold() == c.split("_")[0].casefold():
                        base_canon = c
                        break
            if unit is not None and base_canon in UNITS:
                table = UNITS[base_canon]
                if unit.casefold() not in table:
                    raise BlindRefusal("HEADER_UNIT_UNKNOWN", field=field, name=name, unit=unit,
                                       accepted=", ".join(table), detail={"column": name})
                canon, factor, unit_read = base_canon, table[unit.casefold()], unit
            elif unit is not None and base_canon is not None and base_canon not in UNITS and not inputs:
                if base_canon.endswith("_um") and unit.casefold() not in ("um", "µm", "micron"):
                    raise BlindRefusal("HEADER_UNIT_UNKNOWN", field=field, name=name, unit=unit,
                                       accepted="um", detail={"column": name})
                canon, unit_read = base_canon, unit
        if canon is None and inputs:
            if folded in TARGET_LIKE_EXACT or name in ("D", "W"):
                raise BlindRefusal("INPUTS_TARGET_COLUMN", field=field, name=name, token=name,
                                   detail={"column": name})
            hit = _TARGET_LIKE.search(name)
            if hit:
                raise BlindRefusal("INPUTS_TARGET_COLUMN", field=field, name=name, token=hit.group(0),
                                   detail={"column": name})
            raise BlindRefusal("INPUTS_UNKNOWN_COLUMN", field=field, name=name, detail={"column": name})
        if canon is None:
            ignored.append(name)
            continue
        if canon in mapped:
            raise BlindRefusal("AMBIGUOUS_ALIAS", field=field, a=mapped[canon][1], b=name, canonical=canon,
                               detail={"columns": [mapped[canon][1], name]})
        if unit_read is None and canon in UNITS:
            if folded in UNITLESS_HEADERS:
                labels.append(f"unit not stated, read as {CANONICAL_UNIT[canon]}")
                unit_read = None
        mapped[canon] = (i, name, factor, unit_read)
        if name != canon:
            echoes.append({"header": name, "canonical": canon, "unit": unit_read, "factor": factor})
    return mapped, echoes, labels, ignored


def parse_number(cell, dialect, row, col, field):
    _sep, dec = DIALECTS[dialect]
    if dec == "." and "," in cell and _PLAIN_COMMA.match(cell):
        raise BlindRefusal("DIALECT_MISMATCH", field=field, row=row, col=col, detail={"row": row, "column": col})
    pattern = _PLAIN_DOT if dec == "." else _PLAIN_COMMA
    if not pattern.match(cell):
        raise BlindRefusal("NUMBER_INVALID", field=field, row=row, col=col, detail={"row": row, "column": col})
    value = float(cell.replace(",", "."))
    if not math.isfinite(value):
        raise BlindRefusal("NUMBER_INVALID", field=field, row=row, col=col, detail={"row": row, "column": col})
    return value


def check_id(cell, row, col, field):
    if not _ID.match(cell) or cell[0] in FORMULA_START:
        raise BlindRefusal("ID_INVALID", field=field, row=row, col=col, detail={"row": row, "column": col})
    if SYNTHETIC_MARKER.casefold() in cell.casefold():
        raise BlindRefusal("SYNTHETIC_EXAMPLE_ROW", field=field, row=row, detail={"row": row})
    return cell


# ---------------------------------------------------------------------------------------------- metadata (4.1)
METADATA_SHAPE = {
    "schema": "str", "blockLabel": "str", "mode": "enum", "alloy": "enum", "quantity": "enum",
    "depthBoundary": "enum", "measurementMethod": "enum", "depthDatum": "enum", "reduction": "enum",
    "crossSectionLocation": "enum", "wavelength_nm": "num", "preheat_C": "num?", "preheatBasis": "enum",
    "atmosphere": "enum", "csvDialect": "enum", "targetCommitment": "commit?",
    "beam": {"diameter_um": "num?", "quantity": "enum", "definition": "enum", "basis": "enum", "profile": "enum",
             "uncertaintyReleased": "bool", "u_k1_um": "num?"},
    "power": {"basis": "enum", "meterNamed": "bool", "uncertaintyReleased": "bool", "u_k1_rel": "num?"},
    "substrate": {"kind": "enum", "layerThickness_um": "num?", "amSubstrate": "bool", "thickness_mm": "num?",
                  "surfacePreparation": "enum", "alsi10mgState": "enum?"},
    "replication": {"tracksPerCondition": "int", "sectionsPerTrack": "int", "rowsAreSeparateTracks": "bool"},
    "depthUncertainty": {"basis": "enum", "u_um": "num?", "coverageFactor": "enum"},
    "chemistry": {"basis": "enum", "sulfur_ppm": "num?", "oxygen_ppm": "num?"},
    "independence": {"predictionsViewedBeforeFreeze": "enum", "dataPreviouslyPublished": "enum",
                     "publishedDoi": "doi?", "usedForMachineCalibration": "bool"},
}
DEFAULTS = {
    "quantity": "melt-pool-depth", "depthDatum": "unresolved", "crossSectionLocation": "unstated",
    "csvDialect": "comma-dot", "targetCommitment": None, "preheatBasis": "set-point", "atmosphere": "unstated",
    "measurementMethod": "other", "depthBoundary": "other",
    "beam": {"diameter_um": None, "definition": "unstated", "basis": "nominal", "profile": "unknown",
             "uncertaintyReleased": False, "u_k1_um": None},
    "power": {"basis": "commanded", "meterNamed": False, "uncertaintyReleased": False, "u_k1_rel": None},
    "substrate": {"layerThickness_um": None, "amSubstrate": False, "thickness_mm": None,
                  "surfacePreparation": "unstated", "alsi10mgState": None},
    "replication": {"rowsAreSeparateTracks": False},
    "depthUncertainty": {"basis": "not-released", "u_um": None, "coverageFactor": 1},
    "chemistry": {"basis": "unstated", "sulfur_ppm": None, "oxygen_ppm": None},
    "independence": {"dataPreviouslyPublished": "unknown", "publishedDoi": None},
}
REQUIRED = {"mode", "alloy", "reduction", "wavelength_nm", "beam.quantity", "substrate.kind",
            "replication.tracksPerCondition", "replication.sectionsPerTrack", "preheat_C",
            "independence.predictionsViewedBeforeFreeze", "independence.usedForMachineCalibration"}
_DOI = re.compile(r"^10\.\d{4,9}/[^\s]{1,200}$")


def _meta_error(message, field):
    return BlindRefusal("METADATA_FIELD", field=field, message=message, detail={"field": field})


def _check_value(kind, value, path):
    optional = kind.endswith("?")
    kind = kind.rstrip("?")
    if value is None:
        if optional:
            return None
        raise _meta_error(f"Missing required field '{path}'.", path)
    if kind == "str":
        if not isinstance(value, str):
            raise _meta_error(f"Field '{path}' has a value this form does not accept (text).", path)
        return value
    if kind == "bool":
        if type(value) is not bool:
            raise _meta_error(f"Field '{path}' has a value this form does not accept (true or false).", path)
        return value
    if kind == "num":
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise _meta_error(f"Field '{path}' has a value this form does not accept (a finite number).", path)
        return float(value)
    if kind == "int":
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 20:
            raise _meta_error(f"Field '{path}' has a value this form does not accept (a whole number 1 to 20).",
                              path)
        return value
    if kind == "enum":
        allowed = ENUMS[path]
        if isinstance(value, bool) or value not in allowed:
            raise _meta_error(f"Field '{path}' has a value this form does not accept (one of "
                              f"{', '.join(str(a) for a in allowed)}).", path)
        return value
    if kind == "doi":
        if not isinstance(value, str) or not _DOI.match(value):
            raise _meta_error(f"Field '{path}' has a value this form does not accept (a DOI such as 10.1234/abc).",
                              path)
        return value
    if kind == "commit":
        if (not isinstance(value, dict) or set(value) != {"sha256"} or not isinstance(value["sha256"], str)
                or not re.fullmatch(r"[0-9a-f]{64}", value["sha256"])):
            raise _meta_error(f"Field '{path}' has a value this form does not accept ({{sha256: 64 lower-case hex}}).",
                              path)
        return {"sha256": value["sha256"]}
    raise AssertionError(kind)


def _normalize(shape, defaults, raw, prefix):
    if not isinstance(raw, dict):
        raise _meta_error(f"Field '{prefix or 'metadata'}' must be an object.", prefix or "metadata")
    for key in raw:
        if key not in shape:
            path = f"{prefix}.{key}" if prefix else key
            raise _meta_error(f"Unknown metadata field '{path}'.", path)
    out = {}
    for key, kind in shape.items():
        path = f"{prefix}.{key}" if prefix else key
        sub_defaults = defaults.get(key) if isinstance(defaults, dict) else None
        if isinstance(kind, dict):
            value = raw.get(key, {} if isinstance(sub_defaults, dict) else None)
            if value is None:
                raise _meta_error(f"Missing required field '{path}'.", path)
            out[key] = _normalize(kind, sub_defaults or {}, value, path)
            continue
        if key in raw:
            value = raw[key]
        elif isinstance(defaults, dict) and key in defaults:
            value = defaults[key]
        elif path == "preheat_C":
            raise BlindRefusal("PREHEAT_MISSING", field=path)
        elif path in REQUIRED:
            raise _meta_error(f"Missing required field '{path}'.", path)
        else:
            value = None
        if path in REQUIRED and value is None:
            if path == "preheat_C":
                raise BlindRefusal("PREHEAT_MISSING", field=path)
            raise _meta_error(f"Missing required field '{path}'.", path)
        out[key] = _check_value(kind, value, path)
    return out


def normalize_metadata(raw):
    """Closed metadata with conservative defaults filled in. Raises BlindRefusal."""
    md = _normalize(METADATA_SHAPE, DEFAULTS, raw, "")
    if md["schema"] != METADATA_SCHEMA:
        raise _meta_error(f"Field 'schema' has a value this form does not accept ({METADATA_SCHEMA}).", "schema")
    label = md["blockLabel"]
    if not _BLOCK_LABEL.match(label) or label[0] in FORMULA_START:
        raise _meta_error("Field 'blockLabel' has a value this form does not accept (1 to 80 letters, digits, "
                          "spaces and . _ ( ) / -, not starting with = + - @).", "blockLabel")
    if md["alloy"] not in ALLOYS:
        raise BlindRefusal("ALLOY_NOT_SERVED", field="alloy", alloy="This alloy")
    lo, hi = WAVELENGTH_RANGE
    if not lo <= md["wavelength_nm"] <= hi:
        raise BlindRefusal("WAVELENGTH_OUT_OF_SCOPE", field="wavelength_nm")
    if not PREHEAT_RANGE[0] <= md["preheat_C"] <= PREHEAT_RANGE[1]:
        raise _meta_error("Field 'preheat_C' has a value this form does not accept (-50 to 1000 C).", "preheat_C")
    sub = md["substrate"]
    if sub["kind"] == "powder-layer":
        layer = sub["layerThickness_um"]
        if layer is None or not LAYER_RANGE[0] <= layer <= LAYER_RANGE[1]:
            raise _meta_error("Field 'substrate.layerThickness_um' has a value this form does not accept "
                              "(5 to 200 um for a powder layer).", "substrate.layerThickness_um")
    elif sub["layerThickness_um"] is not None:
        raise _meta_error("Field 'substrate.layerThickness_um' has a value this form does not accept (null for a "
                          "bare plate).", "substrate.layerThickness_um")
    if md["alloy"] == "AlSi10Mg":
        if sub["alsi10mgState"] is None:
            sub["alsi10mgState"] = "unstated"
    elif sub["alsi10mgState"] is not None:
        raise _meta_error("Field 'substrate.alsi10mgState' has a value this form does not accept (null unless the "
                          "alloy is AlSi10Mg).", "substrate.alsi10mgState")
    beam = md["beam"]
    if beam["diameter_um"] is not None and not 1.0 <= beam["diameter_um"] <= 1000.0:
        raise _meta_error("Field 'beam.diameter_um' has a value this form does not accept (1 to 1000 um).",
                          "beam.diameter_um")
    du = md["depthUncertainty"]
    if du["basis"] == "block" and (du["u_um"] is None or not du["u_um"] > 0):
        raise _meta_error("Field 'depthUncertainty.u_um' has a value this form does not accept (a positive number "
                          "when the basis is block).", "depthUncertainty.u_um")
    ind = md["independence"]
    if ind["dataPreviouslyPublished"] == "yes" and md["mode"] == "pre-measurement":
        raise _meta_error("Published data cannot be a pre-measurement test; choose post-measurement.",
                          "independence.dataPreviouslyPublished")
    if md["targetCommitment"] is not None and md["mode"] != "post-measurement":
        raise _meta_error("Field 'targetCommitment' has a value this form does not accept (only in "
                          "post-measurement mode).", "targetCommitment")
    return md


# ---------------------------------------------------------------------------------------------- inputs CSV (4.2)
def parse_inputs(raw_bytes, metadata, field="inputsCsvBase64"):
    """Rows, conditions and conversions from the inputs file. Header checked before any data row is parsed."""
    text = decode_text(raw_bytes, field)
    dialect = metadata["csvDialect"]
    header, reader = read_csv(text, dialect, field)
    mapped, echoes, labels, _ignored = map_header(header, INPUT_COLUMNS, INPUT_ALIASES, field, inputs=True)
    beam_block = metadata["beam"]["diameter_um"]
    for need in ("power_W", "speed_mm_s"):
        if need not in mapped:
            raise BlindRefusal("INPUTS_COLUMN_MISSING", field=field, name=need,
                               aliases=", ".join(INPUT_ALIASES[need]), detail={"column": need})
    if "spot_um" not in mapped and beam_block is None:
        raise BlindRefusal("BEAM_MISSING", field=field)
    if "section_id" in mapped and "track_id" not in mapped:
        raise BlindRefusal("SECTION_WITHOUT_TRACK", field=field, row=2, detail={"row": 2})
    if "condition_id" not in mapped and "track_id" not in mapped:
        raise BlindRefusal("INPUTS_COLUMN_MISSING", field=field, name="condition_id or track_id",
                           aliases="condition, track", detail={"column": "condition_id"})
    columns_loaded = [mapped[c][1] for c in INPUT_COLUMNS if c in mapped]
    data = iter_rows(reader, header, field)

    def cell(cells, canon):
        return cells[mapped[canon][0]] if canon in mapped else ""

    beam = metadata["beam"]
    rows = []
    for line, cells in data:
        rec = {"ordinal": line}
        for idc in ("condition_id", "track_id", "section_id"):
            v = cell(cells, idc)
            if idc in mapped and not v:
                raise BlindRefusal("ID_INVALID", field=field, row=line, col=mapped[idc][1],
                                   detail={"row": line, "column": mapped[idc][1]})
            rec[idc] = check_id(v, line, mapped[idc][1], field) if v else None
        nums = {}
        for canon in ("power_W", "speed_mm_s", "spot_um", "power_u_k1_W"):
            if canon not in mapped:
                continue
            v = cell(cells, canon)
            if not v:
                if canon == "power_u_k1_W" or (canon == "spot_um" and beam_block is not None):
                    continue
                raise BlindRefusal("NUMBER_INVALID", field=field, row=line, col=mapped[canon][1],
                                   detail={"row": line, "column": mapped[canon][1]})
            x = parse_number(v, dialect, line, mapped[canon][1], field) * mapped[canon][2]
            lo, hi, unit = RANGES[canon]
            if not lo <= x <= hi:
                hint = ""
                if canon == "speed_mm_s" and x < lo * 10:
                    hint = "Speed looks like m/s; enter mm/s or label the column Speed (m/s)."
                elif canon == "spot_um" and x < lo:
                    hint = "Spot looks like mm; enter um or label the column Spot (mm)."
                elif canon == "power_W" and x < lo:
                    hint = "Power looks like kW; enter W or label the column Power (kW)."
                raise BlindRefusal("OUT_OF_RANGE", field=field, row=line, col=mapped[canon][1], lo=f"{lo:g}",
                                   hi=f"{hi:g}", unit=unit, hint=hint, detail={"row": line, "column": mapped[canon][1]})
            nums[canon] = x
        spot = nums.get("spot_um", beam_block)
        if spot is None:
            raise BlindRefusal("BEAM_MISSING", field=field)
        d_declared = float(spot)
        d_diameter = d_declared * (2.0 if beam["quantity"] == "radius" else 1.0)
        d_1e2 = stats.beam_d_um(d_diameter, beam["definition"])
        rec.update(P_W=nums["power_W"], v_mm_s=nums["speed_mm_s"], d_declared_um=d_declared,
                   beamQuantity=beam["quantity"], beamDefinition=beam["definition"], d_1e2_um=d_1e2,
                   conversion={"quantityFactor": 2.0 if beam["quantity"] == "radius" else 1.0,
                               "definitionFactor": d_1e2 / d_diameter if d_diameter else 1.0,
                               "powerFactor": mapped["power_W"][2], "speedFactor": mapped["speed_mm_s"][2],
                               "spotFactor": mapped["spot_um"][2] if "spot_um" in mapped else 1.0},
                   P_u_k1_W=nums.get("power_u_k1_W"))
        rows.append(rec)
    structure = _structure(rows, metadata, mapped, field)
    return {"header": header, "columnsLoaded": columns_loaded, "aliases": echoes, "labels": labels,
            "keyColumns": [c for c in ("condition_id", "track_id", "section_id") if c in mapped],
            "rows": structure["rows"], "conditions": structure["conditions"], "counts": structure["counts"],
            "dialect": dialect}


def _setting(r):
    return (r["P_W"], r["v_mm_s"], r["d_1e2_um"])


def _structure(rows, metadata, mapped, field):
    has_cond, has_track, has_section = "condition_id" in mapped, "track_id" in mapped, "section_id" in mapped
    rep = metadata["replication"]
    # Track ids keep one setting (MELT rule for derived conditions and a sanity rule otherwise).
    track_setting = {}
    for r in rows:
        if r["track_id"] is not None:
            key = (r["condition_id"], r["track_id"]) if has_cond else r["track_id"]
            prev = track_setting.setdefault(key, (_setting(r), r["ordinal"]))
            if prev[0] != _setting(r):
                raise BlindRefusal("CONDITION_INCONSISTENT", field=field, variant="track", id=r["track_id"],
                                   detail={"rows": [prev[1], r["ordinal"]]})
    if not has_cond:
        order = {}
        for r in rows:
            s = _setting(r)
            if s not in order:
                order[s] = f"C{len(order) + 1:03d}"
            r["condition"] = order[s]
    else:
        for r in rows:
            r["condition"] = r["condition_id"]
    by_cond = {}
    for r in rows:
        by_cond.setdefault(r["condition"], []).append(r)
    settings = {}
    for cid, rs in by_cond.items():
        if any(_setting(x) != _setting(rs[0]) for x in rs):
            raise BlindRefusal("CONDITION_INCONSISTENT", field=field, id=cid,
                               detail={"rows": [x["ordinal"] for x in rs][:5]})
        s = _setting(rs[0])
        if s in settings:
            raise BlindRefusal("CONDITION_DUPLICATE_SETTING", field=field, a=settings[s], b=cid,
                               detail={"conditions": [settings[s], cid]})
        settings[s] = cid
        if len(rs) > 1 and not has_track and not rep["rowsAreSeparateTracks"]:
            raise BlindRefusal("REPEATED_ROWS_NO_TRACK", field=field, id=cid,
                               detail={"rows": [x["ordinal"] for x in rs][:5]})
    if len(by_cond) > CAPS["conditions"]:
        raise BlindRefusal("SIZE_CAP", field=field, cap=f"{CAPS['conditions']} conditions")
    seen = {}
    for r in rows:
        r["track"] = r["track_id"] if has_track else (f"row{r['ordinal']}" if rep["rowsAreSeparateTracks"] else None)
        r["section"] = r["section_id"]
        key = (r["condition"], r["track"], r["section_id"])
        if key in seen:
            raise BlindRefusal("DUPLICATE_KEY", field=field, a=seen[key], b=r["ordinal"],
                               detail={"rows": [seen[key], r["ordinal"]]})
        seen[key] = r["ordinal"]
    mismatch = []
    tracks_total, sections_total = 0, 0
    for cid, rs in by_cond.items():
        tracks = {}
        for r in rs:
            tracks.setdefault(r["track"] if r["track"] is not None else "_one", []).append(r)
        tracks_total += len(tracks)
        sections_total += len(rs)
        n_sec = {len(v) for v in tracks.values()}
        if len(tracks) != rep["tracksPerCondition"] or n_sec != {rep["sectionsPerTrack"]}:
            mismatch.append(cid)
    if mismatch:
        raise BlindRefusal("REPLICATION_MISMATCH", field=field, k=rep["tracksPerCondition"],
                           m=rep["sectionsPerTrack"], list=", ".join(mismatch[:10]),
                           detail={"conditions": mismatch[:50]})
    clean = [{k: r[k] for k in ("ordinal", "condition", "track", "section", "condition_id", "track_id", "section_id",
                                "P_W", "v_mm_s", "d_declared_um", "beamQuantity", "beamDefinition", "d_1e2_um",
                                "conversion", "P_u_k1_W")} for r in rows]
    conditions = []
    for cid, rs in by_cond.items():
        r0 = rs[0]
        conditions.append({"condition": cid, "P_W": r0["P_W"], "v_mm_s": r0["v_mm_s"], "d_1e2_um": r0["d_1e2_um"],
                           "d_declared_um": r0["d_declared_um"], "rows": [x["ordinal"] for x in rs],
                           "nTracks": len({x["track"] for x in rs}), "nRows": len(rs)})
    return {"rows": clean, "conditions": conditions,
            "counts": {"rows": len(rows), "conditions": len(by_cond), "tracks": tracks_total,
                       "sections": sections_total if has_section else 0}}


# ---------------------------------------------------------------------------------------------- grades and issues
def grades(md):
    p, b = md["power"], md["beam"]
    power = stats.power_grade({"basis": "measured" if p["basis"].startswith("measured") else "commanded",
                               "meter_named": p["meterNamed"], "at_workpiece": p["basis"] == "measured-at-workpiece",
                               "released_uncertainty": p["uncertaintyReleased"]})
    beam = stats.beam_grade({"basis": "measured" if b["basis"].startswith("measured") else "nominal",
                             "definition_stated": b["definition"] != "unstated",
                             "work_plane": b["basis"] == "measured-work-plane",
                             "released_uncertainty": b["uncertaintyReleased"]})
    return {"power": power, "beam": beam, "block": stats.block_grade(power, beam)}


ISSUE_TEXT = {
    "DATUM_NOT_ORIGINAL_SURFACE": "depth datum is not the original surface",
    "REDUCTION_UNUSABLE": "reduction mismatch (maximum only or a single selected section)",
    "SECTIONS_WITHOUT_TRACK": "sections released without a track key",
    "PLATE_THICKNESS_NOT_RELEASED": "plate thickness not released",
    "ATMOSPHERE_UNSTATED": "atmosphere not stated",
    "SURFACE_PREPARATION_UNSTATED": "surface preparation not stated",
    "INDEPENDENCE_NOT_ESTABLISHED": "independence from spent data not established",
    "BOUNDARY_NOT_ETCHED": "boundary is not an etched fusion boundary",
    "LOCATION_NEAR_ENDS_OR_UNSTATED": "cross-section location near track ends or not stated",
    "BEAM_PROFILE_NOT_GAUSSIAN": "beam profile is top-hat or ring (the served model is Gaussian)",
    "LOSSES_ABOVE_20_PERCENT": "measurement losses above 20 % of frozen tracks or conditions",
}


def block_issues(md, parsed=None):
    issues = []
    if md["depthDatum"] != "original-surface":
        issues.append("DATUM_NOT_ORIGINAL_SURFACE")
    if md["reduction"] in ("maximum-only", "single-selected-section"):
        issues.append("REDUCTION_UNUSABLE")
    if parsed is not None and md["reduction"] == "per-section-raw" and "track_id" not in parsed["keyColumns"]:
        issues.append("SECTIONS_WITHOUT_TRACK")
    if md["substrate"]["thickness_mm"] is None:
        issues.append("PLATE_THICKNESS_NOT_RELEASED")
    if md["atmosphere"] == "unstated":
        issues.append("ATMOSPHERE_UNSTATED")
    if md["substrate"]["surfacePreparation"] == "unstated":
        issues.append("SURFACE_PREPARATION_UNSTATED")
    if md["independence"]["dataPreviouslyPublished"] == "unknown":
        issues.append("INDEPENDENCE_NOT_ESTABLISHED")
    if md["depthBoundary"] != "etched-fusion-boundary":
        issues.append("BOUNDARY_NOT_ETCHED")
    if md["crossSectionLocation"] in ("near-track-start-or-end", "unstated"):
        issues.append("LOCATION_NEAR_ENDS_OR_UNSTATED")
    if md["beam"]["profile"] in ("top-hat", "ring"):
        issues.append("BEAM_PROFILE_NOT_GAUSSIAN")
    return issues


def labels_from_metadata(md):
    out = []
    b, p = md["beam"], md["power"]
    if b["definition"] == "unstated":
        out.append("beam definition unstated (read as 1/e2)")
    if b["quantity"] == "radius":
        out.append("beam size declared as radius (doubled)")
    if b["profile"] == "unknown":
        out.append("beam profile not stated (Gaussian assumed by the served model)")
    if p["u_k1_rel"] is not None and p["u_k1_rel"] > 0.05:
        out.append("declared power uncertainty exceeds the 5 % fragility band")
    ch = md["chemistry"]
    out.append("S and O certified" if (ch["basis"] == "certified-heat-analysis" and ch["sulfur_ppm"] is not None
                                       and ch["oxygen_ppm"] is not None) else "S and O flagged missing")
    if md["preheatBasis"] == "nominal-ambient":
        out.append("plate temperature is nominal ambient")
    if md["depthUncertainty"]["basis"] == "not-released":
        out.append("u_m assumed (lead assumption, not sourced)")
    if md["alloy"] not in SCORED_ALLOYS:
        out.append(f"{md['alloy']}: shown for information; thresholds are registered for Ti-6Al-4V and AlSi10Mg only")
    if md["alloy"] == "IN625":
        out.append("served direct thermal path (IN625, legacy-estimated properties)")
    if md["alloy"] == "AlSi10Mg" and md["substrate"]["alsi10mgState"] in ("heat-treated", "unstated"):
        out.append("plate state differs from the as-built property convention")
    if md["substrate"]["kind"] == "bare-plate":
        out.append("bare plate: layer argument 40 um passed")
    out.append("research arm not requested")
    return out


def design_checks(md, parsed, served_index):
    """Counts and qualifier reachability from inputs only (no depth)."""
    conds = parsed["conditions"]
    n = len(conds)
    alloy = md["alloy"]
    leverage = {"cut": None, "nBelow": None, "nAtOrAbove20": None, "ok": "not evaluable"}
    if alloy in LEVERAGE_LOW_CUT:
        cut = LEVERAGE_LOW_CUT[alloy]
        idx = [served_index(alloy, c["P_W"], c["v_mm_s"], c["d_1e2_um"], md["preheat_C"]) for c in conds]
        below = sum(1 for x in idx if x < cut)
        above = sum(1 for x in idx if x >= stats.LEVERAGE_HIGH_CUT)
        leverage = {"cut": cut, "nBelow": below, "nAtOrAbove20": above,
                    "ok": below >= stats.SIDE_MIN and above >= stats.SIDE_MIN}
    single = [c for c in conds if c["nTracks"] < 2]
    replicated = [c for c in conds if c["nTracks"] >= 2]
    df = sum(c["nTracks"] - 1 for c in replicated)
    if single and (len(replicated) < stats.CV_POOL_MIN_CONDITIONS or df < stats.CV_POOL_MIN_DF):
        resolution = {"evaluable": False,
                      "reason": (f"single-track conditions need at least {stats.CV_POOL_MIN_CONDITIONS} replicated "
                                 f"conditions with pooled degrees of freedom of at least {stats.CV_POOL_MIN_DF}")}
    else:
        resolution = {"evaluable": True, "reason": None}
    powder = md["substrate"]["kind"] == "powder-layer" or md["substrate"]["amSubstrate"]
    u_note = None
    if md["depthUncertainty"]["basis"] == "not-released":
        u_note = (f"with u_m not released, a condition needs a measured depth of at least "
                  f"{200 if powder else 100} um for U_c at most 0.10 even with no track scatter")
    return {"nConditions": n, "nMinMet": n >= stats.N_MIN, "leverage": leverage, "resolution": resolution,
            "uMNote": u_note}


def best_reachable(md, issues, checks, exposure_reasons):
    """Best status the design can reach, with reasons, and the acknowledgements it requires."""
    reasons, acks = [], []
    if exposure_reasons:
        return {"status": "descriptive-exposed", "reasons": list(exposure_reasons)}, ["exposedDescriptive"]
    if md["substrate"]["kind"] == "powder-layer":
        return ({"status": "descriptive-not-scored", "reasons": ["powder layer (the served model is flat-plate)"]},
                ["powderLayerDescriptive"])
    if md["alloy"] not in SCORED_ALLOYS:
        return ({"status": "descriptive-not-scored",
                 "reasons": ["thresholds are registered for Ti-6Al-4V and AlSi10Mg only"]},
                ["predeterminedInconclusive"])
    if not checks["nMinMet"]:
        reasons.append(f"fewer than {stats.N_MIN} conditions")
    reasons += [ISSUE_TEXT[i] for i in issues]
    lev = checks["leverage"]
    if lev["ok"] is not True:
        reasons.append("leverage counts below 4 on either side of the served index cuts")
    if not checks["resolution"]["evaluable"]:
        reasons.append(checks["resolution"]["reason"])
    if md["reduction"] == "condition-mean-released":
        reasons.append("one row per condition cannot form the track scatter the resolution rule needs")
    if reasons:
        return {"status": "inconclusive", "reasons": reasons}, ["predeterminedInconclusive"]
    return {"status": "thresholds-met", "reasons": []}, []
