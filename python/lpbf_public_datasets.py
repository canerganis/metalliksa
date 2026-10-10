#!/usr/bin/env python3
"""Typed loaders for public single-track melt-pool datasets and transcribed literature tables (comparison inputs only).

Sources (all measured; nothing here is a calibration or a validation). Licence status per source:

* Hofmann et al. 2026, 316L single tracks (Zenodo 10.5281/zenodo.16979848), 677 rows. CC BY 4.0.
* Totis / Vaglio et al. 2021, Ti-6Al-4V single tracks (Mendeley Data
  10.17632/s9438vb5xd.1), 80 rows (8 powers x 10 speeds, n = 1 per cell). CC BY 4.0.
* CMU KiltHub Ti-6Al-4V melt-pool tables (10.1184/R1/25696293.v1). CC BY 4.0.
* KU Leuven (Coen) Figshare CSVs: IN718 (10.6084/m9.figshare.15035706.v1) and, wave 2, 316L / Ti-6Al-4V
  (see KU_WAVE2_FILES). CC0.
* Wave 2 transcriptions (numeric table values with citation; the source documents are not committed):
  Lane et al. 2020 IN625 Tables 3-4 (PMC author manuscript; no licence stated, PMC text-mining / fair-use
  permissions), NIST AMB2022-03 results document Tables 1-3 (no licence stated; NIST publication, US public
  domain by inference, not confirmed), Simonds et al. 2018 Table III (US Government work, stated in the
  manuscript).

The committed small derived tables live in ``data/benchmark/``; the loaders read them by
default and verify their SHA-256 against the pinned values below. The raw Hofmann CSV and the
Totis ``Allegati.zip`` / ``Data.xlsx`` can be parsed too (stdlib only: csv, zipfile, xml.etree;
no new dependency) and ``build`` regenerates the committed tables from them.

Units are normalised to the repo's process inputs: power W, speed mm/s, lengths um.
``preheat_C`` is an ASSUMPTION (20 C room temperature): no dataset here states a build-plate
temperature in the files read.

Regime screening (``classify_regime``) is an a-priori classifier from process inputs and the
dataset's own balling flag. It is NOT the papers' regime definition.
"""

from __future__ import annotations

import csv
import hashlib
import io
import math
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

REPO_ROOT = Path(__file__).resolve().parent.parent
HOFMANN_DIR = REPO_ROOT / "data" / "benchmark" / "hofmann-316l-2026"
TOTIS_DIR = REPO_ROOT / "data" / "benchmark" / "totis-ti64-2021"
HOFMANN_TABLE = HOFMANN_DIR / "meltpool_geometry.csv"
TOTIS_TABLE = TOTIS_DIR / "tracks.csv"

# SHA-256 of the committed derived tables (verified at load) -- see build_*_table().
HOFMANN_TABLE_SHA256 = "d4bbc7a60b536118586f44b64beb0fa20f94133f6d1a8d0fdcf726003720c3d8"
TOTIS_TABLE_SHA256 = "3b5794f3a25a5f67fa0d8d1ab006834205ef820b046c24deb15836025825d623"
CMU_DIR = REPO_ROOT / "data" / "benchmark" / "cmu-ti64-2026"
CMU_ST_TABLE = CMU_DIR / "st_measurements.csv"
CMU_MT_TABLE = CMU_DIR / "mt_measurements.csv"
KU_LEUVEN_DIR = REPO_ROOT / "data" / "benchmark" / "ku-leuven-in718-2021"
KU_LEUVEN_TABLE = KU_LEUVEN_DIR / "measurements.csv"
# SHA-256 pins for the compact committed derivative files (set by build_*_table).
CMU_ST_TABLE_SHA256 = "7f415afb20cd8e1698efcbc4948654ed4b95bb4fc1854b5c1e7f45e9874a1f90"
CMU_MT_TABLE_SHA256 = "d8d318fd673c69ad250a9d44cc7b37b71d3706cde7ad93539049454aedf09c57"
KU_LEUVEN_TABLE_SHA256 = "d8731ecc5cd027e697e4fbd7f9dabb634c197f0325f4282eb3c86ce9ff9d512b"

ASSUMED_PREHEAT_C = 20.0

HOFMANN_SOURCE = {
    "raw_file": "MeltpoolGeometryData.csv",
    "raw_bytes": 29660,
    "raw_md5": "2c107f3ac12cd38a0f1eb9f75a469000",
    "raw_sha256": "5dd0629b3add839997fd54c3e4d89f90c1f2e4e5e717bede2c72e0c58cefd417",
}
TOTIS_SOURCE = {
    "raw_file": "Allegati.zip :: Allegati/Data.xlsx",
    "raw_bytes": 20097,
    "raw_sha256": "3211cbaa9fe29f1126ea25666cb6de902335aa4cd974dc0918d1c247a31c1e42",
}

HOFMANN_PROVENANCE = {
    "id": "hofmann-316l-2026",
    "depthDatum": "substrate-surface (paper Fig. 2)",
    "beamDefinition": "not stated; 1/e2 assumed",
    "depthDatumNote": ("penetration_depth_um is measured from the original substrate surface (powder/substrate "
                       "interface) to the melt-pool bottom and weld_width_um at that surface (Hofmann et al. 2026, "
                       "Fig. 2 'Schematic melt pool parametrisation' and Sec. 2.2). For t_powder > 0 the consolidated "
                       "layer above the datum is NOT part of the depth. Spot: Gaussian single-mode, focus 50 um, "
                       "defocused to 80/110/140 um (Sec. 2.1); the diameter definition is not stated (1/e2 assumed). "
                       "PSD D10/D50/D90 = 17.5/30.4/46.6 um (Table 1); packing not stated."),
    "doi": "10.5281/zenodo.16979848",
    "url": "https://zenodo.org/records/16979848",
    "license": "CC BY 4.0",
    "citation": ("Hofmann et al., melt-pool geometry data for 316L single tracks (Aconity Midi), Zenodo "
                 "10.5281/zenodo.16979848 (v1, 2025-08-28); associated paper Materials & Design 262 (2026) "
                 "115459, doi:10.1016/j.matdes.2026.115459."),
    "material": "316L Stainless Steel",
    "caveats": [
        "Measured cross-sections from micrographs; the uncertainty budget is not stated in the files read.",
        "The d_laser column is the laser spot DIAMETER in mm; the diameter definition (1/e^2 or other) is not "
        "stated on the Zenodo record or in the paper (Sec. 2.1 gives a single-mode Gaussian beam, 50 um focus "
        "diameter, defocused to 80-140 um): treated as 1/e^2 by assumption.",
        "Depth datum (settled from the paper, Fig. 2 and Sec. 2.2): penetration depth is measured from the original "
        "substrate surface, not from the powder surface; for t_powder > 0 a model that computes depth from the free "
        "(powder) surface is offset by the layer height above the datum (geometric assumption h_surface = phi*t, "
        "phi = 0.60 packing from Trapp 2017; powder denudation not modelled).",
        "Absorptivity is not measured; the comparison uses the repo's estimated 316L absorptivity.",
        "Build-plate temperature is not given: 20 C is an assumption.",
        "t_powder = 0 rows are bare plate; t_powder 30/60 um are powder layers (the packing is not stated).",
        "The CSV header calls the area column 'um' although the values are um^2 (width x depth scale confirms).",
        "677 rows contain repeated parameter sets (623 distinct) -- replicates are kept as separate rows.",
        "Where the width/depth are taken along the track and whether the section is at steady state is not "
        "stated in the files read.",
        "316L thermophysical properties used by the models are estimated, not measured.",
    ],
}
TOTIS_PROVENANCE = {
    "id": "totis-ti64-2021",
    "depthDatum": "printed-base top surface (paper Fig. 1/2b)",
    "beamDefinition": "1/e2 (stated)",
    "depthDatumNote": ("depth_um is measured from the top surface of the printed Ti-6Al-4V base (below the 25 um "
                       "powder layer) to the track bottom; height_um is above that surface (Vaglio et al. 2020, "
                       "Fig. 1 and Fig. 2(b), Sec. 1.3). Spot 50 um at 1/e2 (M2 1.08, 1070 nm; Sec. 2). The base was "
                       "printed in the same job (Table 3), not a wrought plate."),
    "doi": "10.17632/s9438vb5xd.1",
    "url": "https://data.mendeley.com/datasets/s9438vb5xd/1",
    "license": "CC BY 4.0",
    "citation": ("Totis, Vaglio et al., single-track Ti6Al4V SEM images and geometrical data (Concept Laser M2, "
                 "50 um laser spot), Mendeley Data, 10.17632/s9438vb5xd.1 (v1, 2021-04-26); related article "
                 "Data in Brief, doi:10.1016/j.dib.2020.106443."),
    "material": "Ti-6Al-4V",
    "caveats": [
        "Tracks were made on a 25 um powder layer over a printed Ti-6Al-4V base (not a bare plate, not a "
        "semi-infinite wrought substrate); the 50 um spot is taken as 1/e^2 from the research note.",
        "The workbook does not state the depth reference line, but the associated paper does (Vaglio et al. 2020, "
        "Fig. 1 and Fig. 2(b), Sec. 1.3): depth is measured from the top of the printed base under the 25 um powder "
        "layer, height above it. A model that computes depth from the powder surface is offset by the layer height "
        "above the datum (geometric assumption h_surface = phi*t, phi = 0.60; powder denudation not modelled).",
        "One track per (power, speed) cell: no replicates, no scatter estimate.",
        "Absorptivity is not measured; the comparison uses the repo's estimated Ti-6Al-4V absorptivity.",
        "Build-plate temperature is not given: 20 C is an assumption.",
        "No balling flag in the workbook: the regime classifier uses inputs only for this dataset.",
        "Width, depth and height are SEM-derived values read from the workbook sheets 'Track width (W)', "
        "'Track depth (D)', 'Track height (H)', 'Contact angle' (microhardness sheet not used).",
        "Ti-6Al-4V thermophysical properties used by the models are estimated, not measured.",
    ],
}

ENTHALPY_TRANSITION = 15.0
ENTHALPY_KEYHOLE = 20.0
# Mirror of lpbf_thermal_solver.ENTHALPY_KEYHOLE_IN625 (planned bump in625-regime, 2026-10-11).
ENTHALPY_KEYHOLE_IN625 = 13.6
REGIME_RULE = (
    "Screening classifier, not the papers' regime definition. Inputs: normalised enthalpy "
    "dH/h_s = eta*P / (rho*cp_s*max(50, T_liq-T0)*sqrt(pi*alpha_s*v*r^3)) (same form as "
    "lpbf_thermal_solver.py, flat-plate absorptivity_IR of the material authority, solid k/cp, r = d/2) "
    "and the dataset's own balling flag. balling == 1 -> 'balling-flagged' (Hofmann only); otherwise "
    "dH/h_s < 15 -> 'conduction', 15 <= dH/h_s < 20 -> 'transition', >= 20 -> 'keyhole'; "
    "Inconel 625: dH/h_s < 13.6 -> 'conduction', >= 13.6 -> 'keyhole', no transition band "
    "(derivation: lpbf_thermal_solver.REGIME_THRESHOLD_BASIS). "
    "Measured D/W is recorded next to the label but not used for it."
)
REGIME_PARAMETERS = {"transitionEnthalpy": ENTHALPY_TRANSITION, "keyholeEnthalpy": ENTHALPY_KEYHOLE,
                     "keyholeEnthalpyByAlloy": {"Inconel 625": ENTHALPY_KEYHOLE_IN625},
                     "balledLabel": "balling-flagged", "assumedPreheat_C": ASSUMED_PREHEAT_C}


def keyhole_cut(material: str) -> float:
    """Mirror of lpbf_thermal_solver.regime_keyhole_cut."""
    return ENTHALPY_KEYHOLE_IN625 if "625" in str(material or "").lower() else ENTHALPY_KEYHOLE


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Union[str, Path]) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------------------------
# Hofmann 316L
# ---------------------------------------------------------------------------------------------
HOFMANN_TABLE_COLUMNS = ["index", "P_laser_W", "v_scan_mm_s", "d_laser_mm", "t_powder_um",
                         "weld_width_um", "penetration_depth_um", "molten_area_um2", "balling"]


def _read_hofmann_raw_rows(text: str) -> List[List[str]]:
    """Parse either the raw Zenodo CSV (quoted header with a blank first column) or the committed table."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    first = lines[0]
    if first.startswith("index,"):
        body = lines[1:]
    else:
        body = lines[1:]  # raw header is one quoted pseudo-field; the data rows are plain
    return [row for row in csv.reader(body)]


def _hofmann_rows(rows: List[List[str]]) -> List[Dict[str, Any]]:
    out = []
    for r in rows:
        if len(r) != 9:
            raise ValueError(f"Hofmann row has {len(r)} fields, expected 9: {r}")
        idx = int(r[0])
        d_mm = float(r[3])
        t_powder = float(r[4])
        out.append({
            "dataset": HOFMANN_PROVENANCE["id"],
            "rowId": f"hofmann-{idx:04d}",
            "material": HOFMANN_PROVENANCE["material"],
            "power_W": float(r[1]),
            "speed_mm_s": float(r[2]),
            "beamDiameter_um": round(d_mm * 1000.0, 6),
            "layer_um": t_powder,
            "preheat_C": ASSUMED_PREHEAT_C,
            "width_um": float(r[5]),
            "depth_um": float(r[6]),
            "area_um2": float(r[7]),
            "balling": int(float(r[8])),
            "height_um": None,
            "hatch_um": None,
        })
    return out


def load_hofmann_316l(path: Optional[Union[str, Path]] = None, verify: bool = True) -> Dict[str, Any]:
    """Return {"rows": [...], "provenance": {...}}. Default: committed derived table, sha256 verified."""
    src = Path(path) if path is not None else HOFMANN_TABLE
    data = src.read_bytes()
    digest = sha256_bytes(data)
    is_committed = Path(src).resolve() == HOFMANN_TABLE.resolve()
    if verify and is_committed and digest != HOFMANN_TABLE_SHA256:
        raise ValueError(f"Hofmann table sha256 mismatch: {digest} != {HOFMANN_TABLE_SHA256}")
    rows = _hofmann_rows(_read_hofmann_raw_rows(data.decode("utf-8-sig")))
    prov = dict(HOFMANN_PROVENANCE)
    prov.update(file=str(src.name), fileSha256=digest, rows=len(rows), source=dict(HOFMANN_SOURCE),
                columns={"P_laser_W": "W", "v_scan_mm_s": "mm/s",
                         "d_laser_mm": "mm (spot diameter; definition unconfirmed)",
                         "t_powder_um": "um", "weld_width_um": "um", "penetration_depth_um": "um",
                         "molten_area_um2": "um^2 (source header says um)", "balling": "0/1 flag from the dataset"})
    return {"rows": rows, "provenance": prov}


def build_hofmann_table(raw_csv: Union[str, Path], out: Union[str, Path] = HOFMANN_TABLE) -> str:
    """Rewrite the raw CSV as a clean table (values copied verbatim as text). Returns its sha256."""
    text = Path(raw_csv).read_bytes().decode("utf-8-sig")
    rows = _read_hofmann_raw_rows(text)
    buf = io.StringIO(newline="")
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(HOFMANN_TABLE_COLUMNS)
    for r in rows:
        w.writerow(r)
    data = buf.getvalue().encode("utf-8")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_bytes(data)
    return sha256_bytes(data)


# ---------------------------------------------------------------------------------------------
# Totis Ti-6Al-4V (xlsx via stdlib)
# ---------------------------------------------------------------------------------------------
_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
       "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
TOTIS_SHEETS = {"Track width (W)": "width_um", "Track depth (D)": "depth_um", "Track height (H)": "height_um",
                "Contact angle (ϑ)": "contactAngle_deg"}
TOTIS_TABLE_COLUMNS = ["power_W", "speed_mm_s", "width_um", "depth_um", "height_um", "contact_angle_deg"]
TOTIS_BEAM_UM = 50.0
TOTIS_LAYER_UM = 25.0


def _col_index(ref: str) -> int:
    letters = re.match(r"[A-Z]+", ref).group(0)
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n


def _read_xlsx_grids(xlsx_bytes: bytes) -> Dict[str, Dict[str, str]]:
    """{sheet name: {cell ref: text value}} using only zipfile + ElementTree."""
    zf = zipfile.ZipFile(io.BytesIO(xlsx_bytes))
    shared = []
    if "xl/sharedStrings.xml" in zf.namelist():
        for si in ET.fromstring(zf.read("xl/sharedStrings.xml")).findall("m:si", _NS):
            shared.append("".join(t.text or "" for t in si.iter("{%s}t" % _NS["m"])))
    wb = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    target = {rel.get("Id"): rel.get("Target") for rel in rels}
    sheets: Dict[str, Dict[str, str]] = {}
    for sh in wb.find("m:sheets", _NS):
        name = sh.get("name")
        rid = sh.get("{%s}id" % _NS["r"])
        root = ET.fromstring(zf.read("xl/" + target[rid]))
        cells: Dict[str, str] = {}
        for c in root.iter("{%s}c" % _NS["m"]):
            v = c.find("m:v", _NS)
            if v is None or v.text is None:
                continue
            cells[c.get("r")] = shared[int(v.text)] if c.get("t") == "s" else v.text
        sheets[name] = cells
    return sheets


def _totis_rows_from_xlsx(xlsx_bytes: bytes) -> List[Dict[str, Any]]:
    grids = _read_xlsx_grids(xlsx_bytes)
    rows: Dict[tuple, Dict[str, Any]] = {}
    for sheet, field in TOTIS_SHEETS.items():
        if sheet not in grids:
            raise ValueError(f"Totis workbook lacks sheet {sheet!r}; found {sorted(grids)}")
        cells = grids[sheet]
        speeds = {}  # column letter -> speed
        for ref, val in cells.items():
            m = re.fullmatch(r"([A-Z]+)4", ref)
            if m and _col_index(ref) >= 3:
                speeds[m.group(1)] = float(val)
        for r in range(5, 13):
            power = float(cells[f"B{r}"])
            for col, speed in speeds.items():
                ref = f"{col}{r}"
                if ref in cells:
                    rows.setdefault((power, speed), {})[field] = float(cells[ref])
    out = []
    for (power, speed) in sorted(rows):
        v = rows[(power, speed)]
        out.append({"power_W": power, "speed_mm_s": speed, **v})
    if len(out) != 80 or any(len(v) != 6 for v in out):
        raise ValueError(f"Totis workbook parse produced {len(out)} cells; expected 80 complete")
    return out


def _totis_typed(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    typed = []
    for i, r in enumerate(rows, 1):
        typed.append({
            "dataset": TOTIS_PROVENANCE["id"],
            "rowId": f"totis-{int(r['power_W']):03d}W-{int(r['speed_mm_s']):04d}mms",
            "material": TOTIS_PROVENANCE["material"],
            "power_W": r["power_W"],
            "speed_mm_s": r["speed_mm_s"],
            "beamDiameter_um": TOTIS_BEAM_UM,
            "layer_um": TOTIS_LAYER_UM,
            "preheat_C": ASSUMED_PREHEAT_C,
            "width_um": r["width_um"],
            "depth_um": r["depth_um"],
            "area_um2": None,
            "balling": None,
            "height_um": r["height_um"],
            "contactAngle_deg": r["contactAngle_deg"],
            "hatch_um": None,
        })
    return typed


def _totis_rows_from_csv(text: str) -> List[Dict[str, Any]]:
    out = []
    for r in csv.DictReader(io.StringIO(text)):
        out.append({"power_W": float(r["power_W"]), "speed_mm_s": float(r["speed_mm_s"]),
                    "width_um": float(r["width_um"]), "depth_um": float(r["depth_um"]),
                    "height_um": float(r["height_um"]), "contactAngle_deg": float(r["contact_angle_deg"])})
    return out


def load_totis_ti64(path_or_zip: Optional[Union[str, Path]] = None, verify: bool = True) -> Dict[str, Any]:
    """Return {"rows": [...], "provenance": {...}}. Accepts the committed CSV (default), Data.xlsx or Allegati.zip."""
    src = Path(path_or_zip) if path_or_zip is not None else TOTIS_TABLE
    suffix = src.suffix.lower()
    data = src.read_bytes()
    digest = sha256_bytes(data)
    if suffix == ".zip":
        with zipfile.ZipFile(src) as zf:
            xbytes = zf.read("Allegati/Data.xlsx")
        raw_rows = _totis_rows_from_xlsx(xbytes)
    elif suffix == ".xlsx":
        raw_rows = _totis_rows_from_xlsx(data)
    else:
        if verify and src.resolve() == TOTIS_TABLE.resolve() and digest != TOTIS_TABLE_SHA256:
            raise ValueError(f"Totis table sha256 mismatch: {digest} != {TOTIS_TABLE_SHA256}")
        raw_rows = _totis_rows_from_csv(data.decode("utf-8-sig"))
    rows = _totis_typed(raw_rows)
    prov = dict(TOTIS_PROVENANCE)
    prov.update(file=src.name, fileSha256=digest, rows=len(rows), source=dict(TOTIS_SOURCE),
                columns={"power_W": "W", "speed_mm_s": "mm/s", "width_um": "um (SEM cross-section)",
                         "depth_um": "um (from the printed-base top surface, paper Fig. 1/2b)", "height_um": "um",
                         "contactAngle_deg": "deg"})
    return {"rows": rows, "provenance": prov}


def build_totis_table(zip_or_xlsx: Union[str, Path], out: Union[str, Path] = TOTIS_TABLE) -> str:
    src = Path(zip_or_xlsx)
    if src.suffix.lower() == ".zip":
        with zipfile.ZipFile(src) as zf:
            xbytes = zf.read("Allegati/Data.xlsx")
    else:
        xbytes = src.read_bytes()
    rows = _totis_rows_from_xlsx(xbytes)
    buf = io.StringIO(newline="")
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(TOTIS_TABLE_COLUMNS)
    for r in rows:
        w.writerow([int(r["power_W"]),
                    int(r["speed_mm_s"]), repr(r["width_um"]), repr(r["depth_um"]),
                    repr(r["height_um"]), repr(r["contactAngle_deg"])])
    data = buf.getvalue().encode("utf-8")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_bytes(data)
    return sha256_bytes(data)


# ---------------------------------------------------------------------------------------------
# CMU Ti-6Al-4V variability and KU Leuven IN718 (comparison-only source records)
# ---------------------------------------------------------------------------------------------
CMU_DOI = "10.1184/R1/25696293.v1"
CMU_FILES = {
    "STMeasurements.csv": {
        "header": ["Slice", "Orientation (degrees)", "Velocity (mm/s)", "Width (um)", "Depth (um)", "Cap (um)"],
        "id": "cmu-ti64-st-2026", "sha256": "2e6db89484a91b8c8c5112bc1f68dbe7388dfddea19d92428e4ae160e0372e5c",
        "rows": 216, "has_power": False,
    },
    "MTMeasurements.csv": {
        "header": ["Slice", "Orientation (degrees)", "Power (W)", "Velocity (mm/s)", "Width (um)", "Depth (um)", "Cap (um)"],
        "id": "cmu-ti64-mt-2026", "sha256": "871a915a3850754af3174c2cd14295d3351ab745bed4f3a9a4bc31d8dd693743",
        "rows": 410, "has_power": True,
    },
}
KU_LEUVEN_PROVENANCE = {
    "id": "ku-leuven-in718-2021", "doi": "10.6084/m9.figshare.15035706.v1",
    "url": "https://doi.org/10.6084/m9.figshare.15035706.v1", "license": "CC0",
    "citation": "KU Leuven IN718 melt-pool measurements, Figshare, 10.6084/m9.figshare.15035706.v1.",
    "material": "Inconel 718",
    "caveats": ["Source CSV does not state units for w exp/d exp; article describes half-width, so dimensions are retained as source values and excluded from numeric comparison until resolved.",
                 "48 numbered conditions; 38 contain both dimensions and 10 have missing dimensions.",
                 "Condition means, not individual cross-sections; source sample counts vary.",
                 "Paper reports 37.5 um spot and 60 um powder layer; preheat and measured absorptivity are not reported."],
}
CMU_PROVENANCE = {
    "id": "cmu-ti64-2026", "doi": CMU_DOI, "url": "https://doi.org/" + CMU_DOI,
    "license": "CC BY 4.0", "citation": "CMU KiltHub, Ti-6Al-4V melt-pool variability, 10.1184/R1/25696293.v1.",
    "material": "Ti-6Al-4V",
    "caveats": ["STMeasurements.csv has no power column; power is not inferred.",
                 "Neither CMU table reports beam diameter, layer thickness, preheat or absorptivity; rows are source measurements only and excluded from kernel prediction.",
                 "Slice is an index and does not establish independent process conditions; ST measurements were not used in the manuscript."],
}
CMU_TABLE_COLUMNS = ["dataset", "source_file", "source_row", "slice", "orientation_deg", "power_W", "speed_mm_s", "width_um", "depth_um", "cap_um"]
KU_TABLE_COLUMNS = ["sample", "power_W", "speed_mm_s", "source_width", "source_depth", "sample_count"]


def _finite_or_none(value: str, label: str) -> Optional[float]:
    if not value.strip():
        return None
    try:
        number = float(value)
    except ValueError as exc:
        raise ValueError(f"invalid numeric {label}") from exc
    if not math.isfinite(number):
        raise ValueError(f"nonfinite numeric {label}")
    return None if number == -1 else number


def parse_cmu_table(text: str, filename: str) -> List[Dict[str, Any]]:
    """Parse the publisher CSV strictly; ST genuinely lacks power, so it stays missing."""
    spec = CMU_FILES.get(filename)
    if spec is None or len(text) > 2_000_000:
        raise ValueError(f"unsupported CMU table: {filename}")
    reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
    if reader.fieldnames != spec["header"]:
        raise ValueError(f"unexpected CMU columns or units in {filename}")
    out = []
    for line, item in enumerate(reader, 2):
        def value(column): return _finite_or_none(item[column], f"{filename}:{line}:{column}")
        sl, orient = value("Slice"), value("Orientation (degrees)")
        power = value("Power (W)") if spec["has_power"] else None
        speed, width, depth, cap = (value(name) for name in ("Velocity (mm/s)", "Width (um)", "Depth (um)", "Cap (um)"))
        if sl is None or sl < 1 or not sl.is_integer() or orient is None or not 0 <= orient < 360:
            raise ValueError(f"invalid slice/orientation at {filename}:{line}")
        if speed is None or speed <= 0 or (spec["has_power"] and (power is None or power <= 0)):
            raise ValueError(f"invalid process input at {filename}:{line}")
        if width is None or width <= 0 or depth is None or depth <= 0 or cap is None or cap < 0:
            raise ValueError(f"invalid measured geometry at {filename}:{line}")
        out.append({"source_file": filename, "source_row": line, "slice": int(sl), "orientation_deg": orient,
                    "power_W": power, "speed_mm_s": speed, "width_um": width, "depth_um": depth, "cap_um": cap})
    return out


def parse_ku_leuven_table(text: str) -> List[Dict[str, Any]]:
    """Parse numbered observations while preserving ambiguous geometry as source values."""
    if len(text) > 2_000_000:
        raise ValueError("KU Leuven table is oversized")
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=";", strict=True)
    header = next(reader, None)
    if not header or header[:7] != ["Sample", "P", "v", "", "w exp", "d exp", "R exp"]:
        raise ValueError("unexpected KU Leuven columns")
    out = []
    for line, cells in enumerate(reader, 2):
        if len(cells) < 7 or not cells[0].strip().isdigit():
            continue  # source summary/model rows are not numbered observations
        if len(cells) < 6:
            raise ValueError(f"invalid KU Leuven field count at row {line}")
        sample = _finite_or_none(cells[0], f"row:{line}:Sample")
        if sample is None:
            continue
        if not sample.is_integer() or sample < 1:
            raise ValueError(f"invalid sample number at row {line}")
        power, speed = _finite_or_none(cells[1], "P"), _finite_or_none(cells[2], "v")
        if power is None or power <= 0 or speed is None or speed <= 0:
            raise ValueError(f"invalid process input at row {line}")
        w = _finite_or_none(cells[4].replace(",", "."), "w exp")
        d = _finite_or_none(cells[5].replace(",", "."), "d exp")
        # The source has ragged trailing summary columns; sample count is not used as an observation.
        n = int(cells[-1]) if cells[-1].strip().isdigit() else None
        out.append({"sample": int(sample), "power_W": power, "speed_mm_s": speed,
                    "source_width": w, "source_depth": d, "sample_count": int(n) if n is not None else None})
    return out


def _write_table(columns: List[str], rows: List[Dict[str, Any]], out: Path) -> str:
    buf = io.StringIO(newline="")
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(columns)
    for row in rows:
        writer.writerow(["" if row.get(c) is None else row.get(c) for c in columns])
    payload = buf.getvalue().encode("utf-8")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(payload)
    return sha256_bytes(payload)


def build_cmu_table(st_csv: Union[str, Path], mt_csv: Union[str, Path], st_out: Path = CMU_ST_TABLE,
                    mt_out: Path = CMU_MT_TABLE) -> tuple:
    st, mt = parse_cmu_table(Path(st_csv).read_text(encoding="utf-8-sig"), "STMeasurements.csv"), parse_cmu_table(Path(mt_csv).read_text(encoding="utf-8-sig"), "MTMeasurements.csv")
    for rows, dataset in ((st, "cmu-ti64-st-2026"), (mt, "cmu-ti64-mt-2026")):
        for row in rows:
            row["dataset"] = dataset
    return (_write_table(CMU_TABLE_COLUMNS, st, st_out), _write_table(CMU_TABLE_COLUMNS, mt, mt_out))


def build_ku_leuven_table(source: Union[str, Path], out: Path = KU_LEUVEN_TABLE) -> str:
    return _write_table(KU_TABLE_COLUMNS, parse_ku_leuven_table(Path(source).read_text(encoding="utf-8-sig")), out)


def _load_pinned_csv(path: Union[str, Path], expected: str, columns: List[str], label: str) -> List[Dict[str, str]]:
    src = Path(path)
    data = src.read_bytes()
    digest = sha256_bytes(data)
    if not expected:
        raise ValueError(f"{label} table sha256 pin is not configured")
    if digest != expected:
        raise ValueError(f"{label} table sha256 mismatch: {digest} != {expected}")
    reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig"), newline=""), strict=True)
    if reader.fieldnames != columns:
        raise ValueError(f"unexpected {label} derived table columns")
    return list(reader)


def load_cmu_ti64(verify: bool = True) -> Dict[str, Any]:
    """Return strict ST/MT records; missing power/beam inputs remain missing."""
    rows = []
    hashes = {}
    for path, digest, file in ((CMU_ST_TABLE, CMU_ST_TABLE_SHA256, "STMeasurements.csv"),
                               (CMU_MT_TABLE, CMU_MT_TABLE_SHA256, "MTMeasurements.csv")):
        records = _load_pinned_csv(path, digest if verify else "", CMU_TABLE_COLUMNS, file)
        hashes[path.name] = sha256_file(path)
        for index, item in enumerate(records, 1):
            power = float(item["power_W"]) if item["power_W"] else None
            rows.append({"dataset": item["dataset"], "rowId": f"{item['dataset']}-{index:04d}", "material": CMU_PROVENANCE["material"],
                         "power_W": power, "speed_mm_s": float(item["speed_mm_s"]), "beamDiameter_um": None,
                         "layer_um": None, "preheat_C": None, "width_um": float(item["width_um"]),
                         "depth_um": float(item["depth_um"]), "area_um2": None, "balling": None,
                         "height_um": float(item["cap_um"]), "hatch_um": None, "slice": int(item["slice"]),
                         "orientation_deg": float(item["orientation_deg"]), "sourceFile": file})
    prov = dict(CMU_PROVENANCE)
    prov.update(file="STMeasurements.csv + MTMeasurements.csv", fileSha256=None, fileSha256ByName=hashes,
                rows=len(rows), source={"raw_sha256": dict((f, CMU_FILES[f]["sha256"]) for f in CMU_FILES)},
                columns={"power_W": "W (absent for ST)", "speed_mm_s": "mm/s", "width_um": "um", "depth_um": "um", "beamDiameter_um": "not reported"})
    return {"rows": rows, "provenance": prov}


def load_ku_leuven_in718(verify: bool = True) -> Dict[str, Any]:
    records = _load_pinned_csv(KU_LEUVEN_TABLE, KU_LEUVEN_TABLE_SHA256 if verify else "", KU_TABLE_COLUMNS, "KU Leuven")
    rows = []
    for item in records:
        w = float(item["source_width"]) if item["source_width"] else None
        d = float(item["source_depth"]) if item["source_depth"] else None
        rows.append({"dataset": KU_LEUVEN_PROVENANCE["id"], "rowId": f"ku-leuven-{int(item['sample']):02d}",
                     "material": KU_LEUVEN_PROVENANCE["material"], "power_W": float(item["power_W"]),
                     "speed_mm_s": float(item["speed_mm_s"]), "beamDiameter_um": 37.5, "layer_um": 60.0,
                     "preheat_C": ASSUMED_PREHEAT_C, "width_um": None, "depth_um": None,
                     "sourceWidthValue": w, "sourceDepthValue": d, "sourceDimensionUnits": "unresolved",
                     "sampleCount": int(item["sample_count"]) if item["sample_count"] else None,
                     "area_um2": None, "balling": None, "height_um": None, "hatch_um": None})
    prov = dict(KU_LEUVEN_PROVENANCE)
    prov.update(file=KU_LEUVEN_TABLE.name, fileSha256=sha256_file(KU_LEUVEN_TABLE), rows=len(rows),
                source={"raw_sha256": "029f5c6992bd261891b30966d3bcc01ff327cd2cf1c7a6963e94de075766e1e5"},
                columns={"P": "W", "v": "mm/s", "w exp": "units unresolved; half-width operator unresolved", "d exp": "units unresolved"})
    return {"rows": rows, "provenance": prov}


# ---------------------------------------------------------------------------------------------
# Wave 2 (2026-10-06): KU Leuven 316L / Ti-6Al-4V, Lane 2020 IN625, NIST AMB2022-03 thermal targets,
# Simonds 2018 316L absorptance. Retrieval date of every source below: 2026-10-06.
# ---------------------------------------------------------------------------------------------
WAVE2_RETRIEVED = "2026-10-06"

KU_WAVE2_DIR = REPO_ROOT / "data" / "benchmark" / "ku-leuven-316l-ti64-2021"
KU_WAVE2_SOURCE_DIR = KU_WAVE2_DIR / "source"
KU_WAVE2_TABLE = KU_WAVE2_DIR / "conditions.csv"
KU_WAVE2_TABLE_SHA256 = "e031aead71bf64c70a35ae05d64c0c576d33c2ae757a1e5bda68b5da532ac831"
KU_WAVE2_ARTICLE = {
    "doi": "10.1016/j.jmatprotec.2022.117547",
    "citation": ("V. Coen, L. Goossens, B. Van Hooreweder, 'Methodology and experimental validation of analytical "
                 "melt pool models for laser powder bed fusion', J. Mater. Process. Technol. 304 (2022) 117547, "
                 "doi:10.1016/j.jmatprotec.2022.117547 (article not read: publisher returned HTTP 403)."),
}
# One record per Figshare item (all CC0, uploader Viktor Coen, published 2021-07-22). md5 is Figshare's
# computed_md5; sha256/bytes were computed locally on the 2026-10-06 download.
KU_WAVE2_FILES = [
    {"alloy": "316L", "role": "raw-sections", "file": "Data Stainless Steel 316L (1).csv",
     "doi": "10.6084/m9.figshare.15035733.v1", "url": "https://ndownloader.figshare.com/files/28914423",
     "bytes": 13265, "md5": "a8a7a365dcf26ac3480181c87dd4f510",
     "sha256": "3f740254deb645fa2c27f64686bc47d1e606a49a8d457a8046516c121a46a13b"},
    {"alloy": "316L", "role": "processed", "file": "Data Stainless Steel 316L (2).csv",
     "doi": "10.6084/m9.figshare.15035703.v1", "url": "https://ndownloader.figshare.com/files/28914396",
     "bytes": 6127, "md5": "43b448c9f5d78560f209ebb18666745c",
     "sha256": "9d55aca22193e8bb9f5a5656497a0abbb987d1b2b2cd091d21b4a25764fc9225"},
    {"alloy": "Ti-6Al-4V", "role": "raw-sections", "file": "Data Ti-6Al-4V (1).csv",
     "doi": "10.6084/m9.figshare.15035709.v1", "url": "https://ndownloader.figshare.com/files/28914390",
     "bytes": 4746, "md5": "f03ed22aa39c0ba98107a94d6030043a",
     "sha256": "2bac87febd59c8ea8022e088cb308026bbedbfd0c627c03c05df2a0747c59705"},
    {"alloy": "Ti-6Al-4V", "role": "processed", "file": "Data Ti-6Al-4V (2).csv",
     "doi": "10.6084/m9.figshare.15035712.v2", "url": "https://ndownloader.figshare.com/files/28914477",
     "bytes": 1759, "md5": "12815f222f8b2d49ebe8288906191e73",
     "sha256": "62ceb073a80d4b6b4e524d94cc88e07b8cabc3e54f3cab252d82ca7a90c3ad98"},
]
KU_WAVE2_MATERIAL = {"316L": "316L Stainless Steel", "Ti-6Al-4V": "Ti-6Al-4V"}
KU_WAVE2_DATASET_ID = {"316L": "ku-leuven-316l-2021", "Ti-6Al-4V": "ku-leuven-ti64-2021"}
# Beam diameter: NOT read from the paywalled article. 37.5 um is the value the repo's 2026-10-05 KU Leuven IN718
# record attributes to the same paper ("Paper reports 37.5 um spot"); whether it is a diameter or a radius and its
# definition (1/e^2, D4sigma, FWHM) are unverified. KU_WAVE2_BEAM_SENSITIVITY_UM is the radius reading (x2).
KU_WAVE2_BEAM_DIAMETER_UM = 37.5
KU_WAVE2_BEAM_SENSITIVITY_UM = 75.0
KU_WAVE2_BEAM_STATUS = ("unverified: 37.5 um carried from the 2026-10-05 KU Leuven IN718 record ('Paper reports 37.5 um "
                        "spot'); the article (doi:10.1016/j.jmatprotec.2022.117547) could not be read (HTTP 403), so "
                        "diameter vs radius and the beam-size definition are not confirmed")
KU_WAVE2_PROCESSED_REQUIRED = ["Sample", "P", "v", "w exp", "d exp", "R exp", "melting regime"]
KU_WAVE2_TABLE_COLUMNS = ["alloy", "sample", "power_W", "speed_mm_s", "w_exp_um", "d_exp_um", "R_exp",
                          "published_regime", "raw_sections_n", "raw_mean_width_um", "raw_mean_depth_um"]
KU_WAVE2_LAYER_STATUS = ("not stated in the files read; the 2026-10-05 KU Leuven IN718 record cites a 60 um powder "
                         "layer from the Coen article, which could not be read here (HTTP 403), so it is not carried "
                         "over to these rows")
KU_WAVE2_PROVENANCE = {
    "license": "CC0",
    "citation": ("V. Coen (KU Leuven), melt-pool measurement CSVs for 316L and Ti-6Al-4V, Figshare (CC0, 2021-07-22): "
                 "316L 10.6084/m9.figshare.15035733.v1 (raw) and 15035703.v1 (processed); Ti-6Al-4V 15035709.v1 (raw) "
                 "and 15035712.v2 (processed). Manuscript: " + KU_WAVE2_ARTICLE["citation"]),
    "evidenceKind": "published measurement (open dataset, measured cross-sections)",
    "caveats": [
        "Only the measured 'w exp', 'd exp', 'R exp' columns and the authors' 'melting regime' label are read from the "
        "processed '(2)' files; their 'model' and 'error' columns (analytical-model outputs) are excluded by name.",
        "Units: the raw '(1)' files tag every section row with 'um' (micrometre sign); the processed '(2)' files carry no "
        "units. 316L 'w exp'/'d exp' equal the arithmetic means of the raw sections; Ti-6Al-4V values differ from the raw "
        "means by a few um (see raw_mean_* columns), so the processing step is not fully reproduced here.",
        "Width operator: 'Width' in the raw files; the authors' R = d/w with keyhole for R > 1 implies full width "
        "(inference, the article was not read).",
        "Regime labels are the authors' published labels ('melting regime' column), kept verbatim; they are not "
        "a strict function of R exp and are not the repo's screening classifier.",
        "Beam diameter " + KU_WAVE2_BEAM_STATUS + ".",
        "Powder layer " + KU_WAVE2_LAYER_STATUS + " (the kernels ignore layer thickness, so there is no numeric "
        "effect). Preheat and absorptivity are not stated in the files read; 20 C preheat is an assumption.",
        "Conditions blank in the processed file (316L 600 W at 400/500/1000/1100 mm/s) carry no exp value and are not "
        "compared, although the raw file has partial sections for some of them.",
        "Condition means: per-condition section count is taken from the raw file (raw_sections_n); the trailing "
        "'nb. of samples' column of the processed file belongs to its regime-summary block and is not used.",
    ],
}


def _ku_text(data: bytes) -> str:
    # The Figshare CSVs are single-byte encoded (the unit cell is b'\xb5m'); latin-1 maps every byte.
    return data.decode("latin-1")


def verify_ku_wave2_sources(source_dir: Union[str, Path] = KU_WAVE2_SOURCE_DIR) -> Dict[str, str]:
    """sha256-check the four committed Figshare CSVs; raises ValueError on a missing or changed file."""
    out = {}
    for spec in KU_WAVE2_FILES:
        path = Path(source_dir) / spec["file"]
        if not path.is_file():
            raise FileNotFoundError(f"KU Leuven source file missing: {path}")
        data = path.read_bytes()
        digest = sha256_bytes(data)
        if digest != spec["sha256"] or len(data) != spec["bytes"]:
            raise ValueError(f"KU Leuven source sha256 mismatch for {spec['file']}: {digest}")
        out[spec["file"]] = digest
    return out


def parse_ku_leuven_processed(text: str) -> Dict[str, Any]:
    """Measured columns only from a processed '(2)' CSV. Model/error columns are located and excluded by name."""
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=";", strict=True)
    header = [h.strip() for h in next(reader)]
    index = {}
    for name in KU_WAVE2_PROCESSED_REQUIRED:
        if header.count(name) != 1:
            raise ValueError(f"KU Leuven processed header lacks a unique {name!r} column")
        index[name] = header.index(name)
    excluded = [h for h in header if "model" in h.lower() or "error" in h.lower()]
    if not excluded:
        raise ValueError("KU Leuven processed header has no model/error columns; unexpected file layout")
    rows = []
    for line, cells in enumerate(reader, 2):
        if not cells or not cells[0].strip().isdigit():
            continue
        cells = cells + [""] * (len(header) - len(cells))

        def num(name):
            raw = cells[index[name]].strip().replace(",", ".")
            if not raw:
                return None
            value = float(raw)
            if not math.isfinite(value):
                raise ValueError(f"nonfinite {name} at line {line}")
            return value
        power, speed = num("P"), num("v")
        if power is None or power <= 0 or speed is None or speed <= 0:
            raise ValueError(f"invalid process input at line {line}")
        w, d = num("w exp"), num("d exp")
        if (w is None) != (d is None) or (w is not None and (w <= 0 or d <= 0)):
            raise ValueError(f"inconsistent measured geometry at line {line}")
        label = cells[index["melting regime"]].strip() or None
        if label not in (None, "conduction", "transition", "keyhole"):
            raise ValueError(f"unexpected regime label {label!r} at line {line}")
        rows.append({"sample": int(cells[0]), "power_W": power, "speed_mm_s": speed, "w_exp_um": w,
                     "d_exp_um": d, "R_exp": num("R exp"), "published_regime": label})
    return {"rows": rows, "excludedColumns": excluded}


def parse_ku_leuven_raw_sections(text: str) -> List[Dict[str, Any]]:
    """Per-section depth/width from a raw '(1)' CSV (blocks: Power -> Scanning Speed columns -> Depth;Width)."""
    power = None
    blocks: List[tuple] = []  # (start column, speed)
    out = []
    for line, raw_line in enumerate(text.splitlines(), 1):
        cells = raw_line.split(";")
        first = cells[1].strip() if len(cells) > 1 else ""
        if first == "Power":
            power = float(cells[2])
            blocks = []
            continue
        if first == "Scanning Speed":
            blocks = [(j - 1, float(cells[j + 1])) for j, c in enumerate(cells) if c.strip() == "Scanning Speed"]
            continue
        if first == "Depth":
            for s, _ in blocks:
                if cells[s + 1].strip() != "Depth" or cells[s + 2].strip() != "Width":
                    raise ValueError(f"unexpected KU Leuven raw column order at line {line}")
            continue
        for s, speed in blocks:
            if s < len(cells) and cells[s].strip().isdigit():
                if power is None:
                    raise ValueError(f"section row before a Power block at line {line}")
                if cells[s + 3].strip() != "µm":
                    raise ValueError(f"unexpected unit {cells[s + 3]!r} at line {line}")
                depth = float(cells[s + 1]) if cells[s + 1].strip() else None
                width = float(cells[s + 2]) if cells[s + 2].strip() else None
                out.append({"power_W": power, "speed_mm_s": speed, "section": int(cells[s]),
                            "depth_um": depth, "width_um": width, "sourceLine": line})
    return out


def build_ku_wave2_table(source_dir: Union[str, Path] = KU_WAVE2_SOURCE_DIR, out: Path = KU_WAVE2_TABLE) -> str:
    """Rebuild conditions.csv from the committed (sha-verified) source CSVs; returns its sha256."""
    verify_ku_wave2_sources(source_dir)
    rows = []
    for alloy in ("316L", "Ti-6Al-4V"):
        specs = {s["role"]: s for s in KU_WAVE2_FILES if s["alloy"] == alloy}
        processed = parse_ku_leuven_processed(_ku_text((Path(source_dir) / specs["processed"]["file"]).read_bytes()))
        sections = parse_ku_leuven_raw_sections(_ku_text((Path(source_dir) / specs["raw-sections"]["file"]).read_bytes()))
        for r in processed["rows"]:
            both = [s for s in sections if s["power_W"] == r["power_W"] and s["speed_mm_s"] == r["speed_mm_s"]
                    and s["depth_um"] is not None and s["width_um"] is not None]
            rows.append({"alloy": alloy, "sample": r["sample"], "power_W": f"{r['power_W']:g}",
                         "speed_mm_s": f"{r['speed_mm_s']:g}",
                         "w_exp_um": "" if r["w_exp_um"] is None else repr(r["w_exp_um"]),
                         "d_exp_um": "" if r["d_exp_um"] is None else repr(r["d_exp_um"]),
                         "R_exp": "" if r["R_exp"] is None else repr(r["R_exp"]),
                         "published_regime": r["published_regime"] or "",
                         "raw_sections_n": len(both),
                         "raw_mean_width_um": f"{sum(s['width_um'] for s in both) / len(both):.4f}" if both else "",
                         "raw_mean_depth_um": f"{sum(s['depth_um'] for s in both) / len(both):.4f}" if both else ""})
    return _write_table(KU_WAVE2_TABLE_COLUMNS, rows, Path(out))


def load_ku_leuven_316l_ti64(verify: bool = True, beam_diameter_um: float = KU_WAVE2_BEAM_DIAMETER_UM) -> Dict[str, Any]:
    """Condition-mean rows with both measured w exp and d exp (others are listed in provenance['notCompared'])."""
    records = _load_pinned_csv(KU_WAVE2_TABLE, KU_WAVE2_TABLE_SHA256 if verify else sha256_file(KU_WAVE2_TABLE),
                               KU_WAVE2_TABLE_COLUMNS, "KU Leuven 316L/Ti-6Al-4V")
    rows, not_compared = [], []
    for item in records:
        alloy = item["alloy"]
        row_id = f"{KU_WAVE2_DATASET_ID[alloy]}-{int(item['sample']):02d}"
        if not item["w_exp_um"] or not item["d_exp_um"]:
            not_compared.append({"rowId": row_id, "reason": "w exp / d exp blank in the processed source file"})
            continue
        rows.append({"dataset": KU_WAVE2_DATASET_ID[alloy], "rowId": row_id, "material": KU_WAVE2_MATERIAL[alloy],
                     "power_W": float(item["power_W"]), "speed_mm_s": float(item["speed_mm_s"]),
                     "beamDiameter_um": beam_diameter_um, "layer_um": None, "preheat_C": ASSUMED_PREHEAT_C,
                     "width_um": float(item["w_exp_um"]), "depth_um": float(item["d_exp_um"]),
                     "area_um2": None, "balling": None, "height_um": None, "hatch_um": None,
                     "publishedRegime": item["published_regime"] or None,
                     "sampleCount": int(item["raw_sections_n"]) if item["raw_sections_n"] else None})
    prov = dict(KU_WAVE2_PROVENANCE)
    prov.update(id="ku-leuven-316l-ti64-2021", file=KU_WAVE2_TABLE.name, fileSha256=sha256_file(KU_WAVE2_TABLE),
                rows=len(rows), notCompared=not_compared, sourceFiles=[dict(s) for s in KU_WAVE2_FILES],
                retrieved=WAVE2_RETRIEVED, beamDiameter_um=beam_diameter_um, beamDiameterStatus=KU_WAVE2_BEAM_STATUS,
                columns={"w_exp_um": "um (full width, inferred)", "d_exp_um": "um", "R_exp": "d/w",
                         "published_regime": "authors' label, verbatim"})
    return {"rows": rows, "provenance": prov}


# ---- Lane et al. 2020 (AMB2018-02 IN625 bare-plate single tracks), Tables 3 and 4 ----------------------------
LANE_DIR = REPO_ROOT / "data" / "benchmark" / "lane-in625-amb2018-02"
LANE_TRACKS_TABLE = LANE_DIR / "table3_tracks.csv"
LANE_SUMMARY_TABLE = LANE_DIR / "table4_summary.csv"
LANE_TRACKS_TABLE_SHA256 = "32fe10fb8606a49cdc59e1e3753b40e6be9ea9751dae9ec8ac95c217e6d16179"
LANE_SUMMARY_TABLE_SHA256 = "b3eaf59e1b3e7aa2b989449095b4a7f7f5ba6d3188e77604fe8151eb1b9843d5"
LANE_SOURCE = {
    "doi": "10.1007/s40192-020-00169-1", "pmcid": "PMC8194244", "nihmsid": "NIHMS1686029",
    "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC8194244/",
    "retrievalUrl": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id=8194244",
    "retrieved": WAVE2_RETRIEVED, "bytes": 185979,
    "sha256": "19757c67b91aeee5b4575722482103649dc98d03167bced14d64244f5313b460",
    "hashOf": "PMC JATS XML returned by NCBI efetch (two fetches gave identical bytes); not committed",
}
LANE_POWER_QUESTION = (
    "Fig. 2 caption: 'Laser power values indicated are the applied laser power'; Table 3 lists 137.9/179.2 W for the "
    "AMMT cases and the Section 2 case definitions give 150/195 W. Whether these are applied vs commanded powers is "
    "not stated explicitly, and the Fig. 2 image was not read. Status: UNRESOLVED.")
LANE_PROVENANCE = {
    "id": "lane-in625-2020", "doi": LANE_SOURCE["doi"], "url": LANE_SOURCE["url"],
    "license": ("not stated as a licence: PMC author manuscript (NIHMS1686029), PMC permissions text 'available for "
                "text mining ... fair use'; NIST-authored; numeric table values transcribed with citation"),
    "citation": ("B. Lane et al., 'Measurements of melt pool geometry and cooling rates of individual laser traces on "
                 "IN625 bare plates', Integr. Mater. Manuf. Innov. 9(1) (2020), doi:10.1007/s40192-020-00169-1, "
                 "PMC8194244, Tables 3 and 4 (AM-Bench AMB2018-02)."),
    "material": "Inconel 625",
    "evidenceKind": "published measurement (table transcription)",
    "caveats": [
        "Width and depth are Table 3 'Cross Section (um)' track means (N = 3 microscopy measurements per track, sigma "
        "= spread, not an uncertainty); the first Cross Section column is width, the second depth (their CBM means "
        "reproduce Table 4 Class Width/Depth).",
        "Bare IN625 plate, no powder; preheat not stated (20 C assumed). Spot sizes are D4sigma diameters (CBM 100 um, "
        "AMMT 170 um, Table 1); for a Gaussian beam D4sigma equals the 1/e^2 diameter the kernels take.",
        "AMMT power: " + LANE_POWER_QUESTION + " Kernel inputs use the Table 3 values; a nominal-power sensitivity is "
        "reported separately.",
        "AMMT cooling rates: Table 3 footnote c says they 'should not be used' (motion blur / calibration range); they "
        "are stored flagged do-not-use. AMMT 1290-1000 C cooling rates are blank (footnote b). AMMT-100us case C "
        "emittance 0.519 is assumed (footnote a). The conclusions call all cooling rates exemplar, not reference data.",
        "AMMT-100us and AMMT-20us tracks are different physical tracks made under nominally the same conditions "
        "(paper Fig. 7); CBM case A is described as near or at keyholing.",
        "IN625 kernel properties come from lpbf_thermal_solver.SECONDARY_THERMOPHYSICAL_DB (provenance class "
        "'legacy-estimated-secondary', absorptivity_IR 0.38 estimated), not from a measured property set.",
    ],
}
LANE_TRACK_COLUMNS = ["machine", "integration_time_us", "track", "case", "power_W", "nominal_case_power_W",
                      "speed_mm_s", "d4sigma_um", "video_frames", "effective_emittance_mean",
                      "effective_emittance_sigma", "length_mean_um", "length_sigma_um", "cr_1290_1190_mean_C_s",
                      "cr_1290_1190_sigma_C_s", "cr_1290_1000_mean_C_s", "cr_1290_1000_sigma_C_s", "width_mean_um",
                      "width_sigma_um", "depth_mean_um", "depth_sigma_um", "footnotes", "cooling_rate_use"]
LANE_SUMMARY_PUBLISHED_COLUMNS = ["class", "cr_1290_1190_mean_C_s", "cr_N", "cr_Umean_C_s", "length_mean_um",
                                  "length_N", "length_Umean_um", "width_mean_um", "width_N", "width_Umean_um",
                                  "depth_mean_um", "depth_N", "depth_Umean_um"]
LANE_SUMMARY_COLUMNS = LANE_SUMMARY_PUBLISHED_COLUMNS + ["cooling_rate_use"]
LANE_TABLE4_COOLING_RATE_USE = {
    "AMMT": "do-not-use (same AMMT-20us values as Table 3, footnote c)",
    "CBM": "exemplar, not reference (paper conclusions)",
}
LANE_NOMINAL_CASE_POWER_W = {"A": 150.0, "B": 195.0, "C": 195.0}  # paper text, Section 2 (case definitions)


def _jats_tables(xml_bytes: bytes) -> Dict[str, List[List[str]]]:
    """{label: rows of cell text} for every table-wrap in a JATS XML document (stdlib only)."""
    root = ET.fromstring(xml_bytes)
    out = {}
    for tw in root.iter("table-wrap"):
        label = tw.find("label")
        key = re.sub(r"\s+", " ", "".join(label.itertext())).strip().rstrip(":. ") if label is not None else tw.get("id", "")
        rows = []
        for tr in tw.iter("tr"):
            rows.append([re.sub(r"\s+", " ", "".join(c.itertext())).strip() for c in tr if c.tag in ("td", "th")])
        out[key] = rows
    return out


def build_lane_tables(xml_path: Union[str, Path], tracks_out: Path = LANE_TRACKS_TABLE,
                      summary_out: Path = LANE_SUMMARY_TABLE) -> tuple:
    """Regenerate the two CSVs from the PMC XML (sha256-checked). Values are copied as published strings."""
    data = Path(xml_path).read_bytes()
    if sha256_bytes(data) != LANE_SOURCE["sha256"]:
        raise ValueError("Lane PMC XML sha256 mismatch")
    tables = _jats_tables(data)
    t3, t4 = tables["Table 3"], tables["Table 4"]
    tracks = []
    for cells in t3:
        if len(cells) != 20 or cells[0] not in ("CBM", "AMMT"):
            continue
        flags = sorted({f for c in cells[8:] for f in "abc" if c.endswith(f) and (c == f or c[:-1][-1:].isdigit())})
        clean = [c[:-1] if c and c[-1] in "abc" and c[:-1][-1:].isdigit() else ("" if c in ("a", "b", "c") else c)
                 for c in cells]
        machine = cells[0]
        tracks.append({
            "machine": machine, "integration_time_us": clean[7], "track": clean[1], "case": clean[2],
            "power_W": clean[3], "nominal_case_power_W": f"{LANE_NOMINAL_CASE_POWER_W[clean[2]]:g}",
            "speed_mm_s": clean[4], "d4sigma_um": clean[5], "video_frames": clean[6],
            "effective_emittance_mean": clean[8], "effective_emittance_sigma": clean[9],
            "length_mean_um": clean[10], "length_sigma_um": clean[11],
            "cr_1290_1190_mean_C_s": clean[12], "cr_1290_1190_sigma_C_s": clean[13],
            "cr_1290_1000_mean_C_s": clean[14], "cr_1290_1000_sigma_C_s": clean[15],
            "width_mean_um": clean[16], "width_sigma_um": clean[17], "depth_mean_um": clean[18],
            "depth_sigma_um": clean[19], "footnotes": "".join(flags),
            "cooling_rate_use": ("do-not-use (Table 3 footnote c)" if machine == "AMMT"
                                 else "exemplar, not reference (paper conclusions)")})
    summary = []
    for cells in t4:
        if len(cells) == 13 and re.fullmatch(r"(AMMT|CBM)-[ABC]", cells[0]):
            item = dict(zip(LANE_SUMMARY_PUBLISHED_COLUMNS, cells))
            item["cooling_rate_use"] = LANE_TABLE4_COOLING_RATE_USE[cells[0].split("-")[0]]
            summary.append(item)
    if len(tracks) != 23 or len(summary) != 6:
        raise ValueError(f"Lane table parse: {len(tracks)} tracks / {len(summary)} classes (expected 23 / 6)")
    return (_write_table(LANE_TRACK_COLUMNS, tracks, Path(tracks_out)),
            _write_table(LANE_SUMMARY_COLUMNS, summary, Path(summary_out)))


def load_lane_in625(verify: bool = True, use_nominal_power: bool = False) -> Dict[str, Any]:
    """23 per-track rows (Table 3) with width/depth means; Table 4 class summary in provenance['table4']."""
    tracks = _load_pinned_csv(LANE_TRACKS_TABLE, LANE_TRACKS_TABLE_SHA256 if verify else sha256_file(LANE_TRACKS_TABLE),
                              LANE_TRACK_COLUMNS, "Lane Table 3")
    summary = _load_pinned_csv(LANE_SUMMARY_TABLE,
                               LANE_SUMMARY_TABLE_SHA256 if verify else sha256_file(LANE_SUMMARY_TABLE),
                               LANE_SUMMARY_COLUMNS, "Lane Table 4")
    rows = []
    for t in tracks:
        tag = f"{t['machine'].lower()}{t['integration_time_us']}"
        power = float(t["nominal_case_power_W"] if use_nominal_power else t["power_W"])
        rows.append({"dataset": LANE_PROVENANCE["id"], "rowId": f"lane-in625-{tag}-t{int(t['track']):02d}-{t['case']}",
                     "material": LANE_PROVENANCE["material"], "power_W": power,
                     "speed_mm_s": float(t["speed_mm_s"]), "beamDiameter_um": float(t["d4sigma_um"]),
                     "layer_um": 0.0, "preheat_C": ASSUMED_PREHEAT_C,
                     "width_um": float(t["width_mean_um"]), "depth_um": float(t["depth_mean_um"]),
                     "widthSigma_um": float(t["width_sigma_um"]), "depthSigma_um": float(t["depth_sigma_um"]),
                     "area_um2": None, "balling": None, "height_um": None, "hatch_um": None,
                     "machine": t["machine"], "case": t["case"], "table3Power_W": float(t["power_W"]),
                     "coolingRateUse": t["cooling_rate_use"], "source": "Lane 2020 Table 3"})
    prov = dict(LANE_PROVENANCE)
    prov.update(file=f"{LANE_TRACKS_TABLE.name} + {LANE_SUMMARY_TABLE.name}",
                fileSha256=sha256_file(LANE_TRACKS_TABLE), fileSha256ByName={
                    LANE_TRACKS_TABLE.name: sha256_file(LANE_TRACKS_TABLE),
                    LANE_SUMMARY_TABLE.name: sha256_file(LANE_SUMMARY_TABLE)},
                rows=len(rows), source=dict(LANE_SOURCE), table4=summary, powerInput=(
                    "nominal case power from the paper text (sensitivity)" if use_nominal_power else "Table 3 power"))
    return {"rows": rows, "provenance": prov}


# ---- NIST AMB2022-03 Measurement and Result Descriptions v1.0, Tables 1-3 (IN718 thermal targets) ------------
NIST_THERMAL_DIR = REPO_ROOT / "data" / "benchmark" / "nist-amb2022-03-thermal-targets"
NIST_THERMAL_TABLE = NIST_THERMAL_DIR / "tables2_3_thermal.csv"
NIST_THERMAL_TABLE_SHA256 = "296b526f49fd484cb482c9f3db733ecd62283ad50eb6e529750a0b30f2f81426"
NIST_THERMAL_SOURCE = {
    "title": "AMB2022-03 Benchmark Measurements and Challenge Results (Measurement and Result Descriptions v1.0)",
    "url": ("https://www.nist.gov/system/files/documents/2022/07/27/"
            "AMB2022-03Measurement%20and%20%20Result%20Descriptions_v1.0.pdf"),
    "documentDate": "last updated 07/21/2022 (page 1)", "retrieved": WAVE2_RETRIEVED,
    "bytes": 1195056, "sha256": "dea3feddec2bc23281ae86c6fd9cee4d0a934a4304501fe0c038f24c7dbc9db0",
    "license": "not stated on the document; NIST publication (US public domain by inference, not confirmed)",
}
NIST_THERMAL_COLUMNS = ["case", "power_W", "speed_mm_s", "d4sigma_um", "TTAM_s", "TSCR_C_s", "TLCR_C_s", "TTCR_C_s"]
NIST_THERMAL_PROVENANCE = {
    "id": "nist-amb2022-03-thermal-2022", "citation": (
        "NIST AM-Bench, 'AMB2022-03 Benchmark Measurements and Challenge Results' (Measurement and Result Descriptions "
        "v1.0, 2022): Table 1 (process cases), Table 2 (TTAM, TSCR, TLCR), Table 3 (TTCR, supplementary), page 2 and 4."),
    "material": "Inconel 718", "evidenceKind": "published measurement (thermography-derived, table transcription)",
    "caveats": [
        "Thermography of bare IN718 single tracks; each value is the mean of three tracks over 30 centerline pixels at a "
        "nominally steady-state location (page 2).",
        "Processing assumptions stated on page 2: no undercooling, and emissivity set so the apparent solidification "
        "inflection equals the IN718 solidus/liquidus midpoint. The TTAM challenge definition on page 1 gives that "
        "midpoint as 'assumed to be 1298 C'; the explicit 'Ttrans = 1298 C' with emissivity 0.5 on page 7 belongs to "
        "the pad PTAM/PSCR processing. Page 3 notes the measurement error in TAM and SCR may be greatest at the "
        "largest spot size (case 1.2).",
        "TTCR is listed as supplementary data 'for reference', not a challenge quantity (Table 3); its definition is in "
        "the separate challenge-description document, which was not transcribed here.",
        "Same seven cases as the IN718 optical width/depth record already in the app (NIST mds2-2718 / AMB2022-03 "
        "Table 4); process parameters agree with lpbf_nist_in718_comparison.CASE_PROCESS.",
    ],
}


def build_nist_thermal_table(pdf_path: Union[str, Path], out: Path = NIST_THERMAL_TABLE) -> str:
    """Regenerate from the PDF (needs the optional pypdf package; only used for rebuilding)."""
    data = Path(pdf_path).read_bytes()
    if sha256_bytes(data) != NIST_THERMAL_SOURCE["sha256"]:
        raise ValueError("AMB2022-03 results PDF sha256 mismatch")
    import pypdf  # optional, rebuild only
    reader = pypdf.PdfReader(io.BytesIO(data))
    p2, p4 = reader.pages[1].extract_text(), reader.pages[3].extract_text()
    sci = r"(\d\.\d+E[+-]\d+)"
    t1 = {m[0]: m[1:] for m in re.findall(rf"(?m)(\d(?:\.\d)?) (\d+) (\d+) (\d+) ?$", p2)}
    t2 = {m[0]: m[1:] for m in re.findall(rf"(?m)^(\d(?:\.\d)?) {sci} {sci} {sci} ?$", p4)}
    t3_text = p4.split("Table 3")[1]
    t3 = dict(re.findall(rf"(?m)^(\d(?:\.\d)?) {sci} ?$", t3_text))
    cases = ["0", "1.1", "1.2", "2.1", "2.2", "3.1", "3.2"]
    if not all(c in t1 and c in t2 and c in t3 for c in cases):
        raise ValueError("AMB2022-03 PDF table parse incomplete")
    rows = [{"case": c, "power_W": t1[c][0], "speed_mm_s": t1[c][1], "d4sigma_um": t1[c][2], "TTAM_s": t2[c][0],
             "TSCR_C_s": t2[c][1], "TLCR_C_s": t2[c][2], "TTCR_C_s": t3[c]} for c in cases]
    return _write_table(NIST_THERMAL_COLUMNS, rows, Path(out))


def load_nist_amb2022_03_thermal(verify: bool = True) -> Dict[str, Any]:
    records = _load_pinned_csv(NIST_THERMAL_TABLE,
                               NIST_THERMAL_TABLE_SHA256 if verify else sha256_file(NIST_THERMAL_TABLE),
                               NIST_THERMAL_COLUMNS, "AMB2022-03 thermal")
    rows = [{"case": r["case"], "power_W": float(r["power_W"]), "speed_mm_s": float(r["speed_mm_s"]),
             "d4sigma_um": float(r["d4sigma_um"]), "TTAM_s": float(r["TTAM_s"]), "TSCR_C_s": float(r["TSCR_C_s"]),
             "TLCR_C_s": float(r["TLCR_C_s"]), "TTCR_C_s": float(r["TTCR_C_s"]),
             "tableRefs": {"process": "Table 1", "TTAM/TSCR/TLCR": "Table 2", "TTCR": "Table 3 (supplementary)"}}
            for r in records]
    prov = dict(NIST_THERMAL_PROVENANCE)
    prov.update(file=NIST_THERMAL_TABLE.name, fileSha256=sha256_file(NIST_THERMAL_TABLE), rows=len(rows),
                source=dict(NIST_THERMAL_SOURCE))
    return {"rows": rows, "provenance": prov}


# ---- Simonds et al. 2018 Phys. Rev. Applied 10, 044061, Table III (316L stationary-spot absorptance) ----------
SIMONDS_DIR = REPO_ROOT / "data" / "benchmark" / "simonds-316l-2018"
SIMONDS_TABLE = SIMONDS_DIR / "table3_absorptance.csv"
SIMONDS_TABLE_SHA256 = "e5fbaeb037371935c167d3e0e1740a348427313c886f7aab2ee439ee3c789db0"
SIMONDS_SOURCE = {
    "doi": "10.1103/PhysRevApplied.10.044061", "pmcid": "PMC7047776", "nihmsid": "NIHMS1541713",
    "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC7047776/",
    "retrievalUrl": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id=7047776",
    "retrieved": WAVE2_RETRIEVED, "bytes": 127169,
    "sha256": "aaf9a603e57e95d37c7db39cbceda30cef7a6edf78f5b8626628aa68f95e86f8",
    "hashOf": "PMC JATS XML returned by NCBI efetch (two fetches gave identical bytes); not committed",
}
SIMONDS_COLUMNS = ["E_in_J", "avg_irradiance_MW_cm2", "W_weld_um", "L_weld_um", "E_abs_J", "eta_coupling",
                   "time_to_melt_ms", "time_to_keyhole_ms"]
SIMONDS_PROVENANCE = {
    "id": "simonds-316l-2018", "doi": SIMONDS_SOURCE["doi"], "url": SIMONDS_SOURCE["url"],
    "license": ("US Government work: the PMC manuscript states 'This work of the U.S. Government is not subject to "
                "U.S. copyright' (acknowledgments)"),
    "citation": ("B. J. Simonds et al., 'Time-Resolved Absorptance and Melt Pool Dynamics during Intense Laser "
                 "Irradiation of a Metal', Phys. Rev. Applied 10, 044061 (2018), doi:10.1103/PhysRevApplied.10.044061, "
                 "PMC7047776, Table III (integrating-sphere optical results)."),
    "material": "316L Stainless Steel (NIST SRM 1155a)",
    "evidenceKind": "published measurement (table transcription)",
    "caveats": [
        "Stationary 10 ms laser spot welds (1070 nm, 303 um top-hat, full width at 1/e^2), polished SRM 1155a disc "
        "(RMS roughness 79 +- 20 nm), no powder, no scanning: not a scan-track coupling value.",
        "eta_coupling is the average coupling efficiency over the weld (E_abs / E_in) from the integrating sphere; "
        "time-to-keyhole is defined in the paper as the time absorptance reaches 0.40 after the initial rise; '-' "
        "(no keyhole reached) is stored as blank.",
        "The Table III caption names W_weld width and L_weld 'length' without defining the direction; keyhole rows have "
        "L > W, so L may be a penetration length. It is stored but not used.",
        "Power-meter uncertainty 3 % (stated); per-row uncertainties are not in Table III.",
    ],
}


def build_simonds_table(xml_path: Union[str, Path], out: Path = SIMONDS_TABLE) -> str:
    data = Path(xml_path).read_bytes()
    if sha256_bytes(data) != SIMONDS_SOURCE["sha256"]:
        raise ValueError("Simonds PMC XML sha256 mismatch")
    t = _jats_tables(data)["TABLE III"]
    rows = [dict(zip(SIMONDS_COLUMNS, ["" if c == "–" else c for c in cells]))
            for cells in t if len(cells) == 8 and re.fullmatch(r"\d+(\.\d+)?", cells[0])]
    if len(rows) != 10:
        raise ValueError(f"Simonds Table III parse produced {len(rows)} rows (expected 10)")
    return _write_table(SIMONDS_COLUMNS, rows, Path(out))


def load_simonds_316l(verify: bool = True) -> Dict[str, Any]:
    records = _load_pinned_csv(SIMONDS_TABLE, SIMONDS_TABLE_SHA256 if verify else sha256_file(SIMONDS_TABLE),
                               SIMONDS_COLUMNS, "Simonds Table III")
    rows = [{k: (float(v) if v else None) for k, v in r.items()} for r in records]
    prov = dict(SIMONDS_PROVENANCE)
    prov.update(file=SIMONDS_TABLE.name, fileSha256=sha256_file(SIMONDS_TABLE), rows=len(rows),
                source=dict(SIMONDS_SOURCE))
    return {"rows": rows, "provenance": prov}


def wave2_reference_targets() -> List[Dict[str, Any]]:
    """(c) and (d) as reference targets; the comparison is marked unavailable with the reason."""
    nist, sim = load_nist_amb2022_03_thermal(), load_simonds_316l()
    return [
        {"dataset": nist["provenance"]["id"], "kind": "thermal targets (IN718 single tracks)",
         "evidenceKind": nist["provenance"]["evidenceKind"], "citation": nist["provenance"]["citation"],
         "source": nist["provenance"]["source"], "tableSha256": nist["provenance"]["fileSha256"],
         "caveats": nist["provenance"]["caveats"],
         # TTAM is carried in ms here so the record's 4-decimal rounding keeps every published digit (1.22E-03 s).
         "rows": [{"case": r["case"], "power_W": r["power_W"], "speed_mm_s": r["speed_mm_s"],
                   "d4sigma_um": r["d4sigma_um"], "TTAM_ms": round(r["TTAM_s"] * 1e3, 6), "TSCR_C_s": r["TSCR_C_s"],
                   "TLCR_C_s": r["TLCR_C_s"], "TTCR_C_s": r["TTCR_C_s"], "tableRefs": r["tableRefs"]}
                  for r in nist["rows"]],
         "comparison": {"status": "unavailable", "reason": (
             "No like-for-like model comparison exists in the app for these quantities. The screening kernels report "
             "solidificationKinetics.coolingRate_K_s as G x R at their solidification-front points, not the surface "
             "centerline cooling rate just below the solidus (TSCR) or above the liquidus (TLCR), and no reviewed "
             "operator converts a kernel melt-pool length into a time above 1298 C at the surface centerline (TTAM). "
             "Adding such an operator is a model change that needs its own review; nothing was computed here.")}},
        {"dataset": sim["provenance"]["id"], "kind": "absorptance targets (316L stationary spot welds)",
         "evidenceKind": sim["provenance"]["evidenceKind"], "citation": sim["provenance"]["citation"],
         "source": sim["provenance"]["source"], "tableSha256": sim["provenance"]["fileSha256"],
         "caveats": sim["provenance"]["caveats"], "rows": sim["rows"],
         "comparison": {"status": "unavailable", "reason": (
             "The app has no stationary-spot (non-scanning) absorptance model: the kernels take a moving source and a "
             "constant flat-plate absorptivity_IR (316L 0.42, estimated), so there is no like-for-like prediction of a "
             "10 ms, 303 um top-hat spot's average coupling efficiency. Not computed.")}},
    ]


# ---------------------------------------------------------------------------------------------
# Regime screening
# ---------------------------------------------------------------------------------------------
def screening_props(material: str) -> Dict[str, Any]:
    """Material properties for the screening classifier: the four-alloy authority first, then the solver's
    SECONDARY_THERMOPHYSICAL_DB (same lookup order as calculate_meltpool_physics; IN625 is legacy-estimated there).
    Unknown names raise; there is no default material."""
    from four_alloy_materials import thermal_props
    props = thermal_props(material)
    if props is None:
        from lpbf_thermal_solver import SECONDARY_THERMOPHYSICAL_DB
        props = SECONDARY_THERMOPHYSICAL_DB.get(material)
    if props is None:
        raise ValueError(f"Unsupported material {material!r}")
    return props


def normalized_enthalpy(material: str, power_W: float, speed_mm_s: float, beam_diameter_um: float,
                        preheat_C: float) -> float:
    """dH/h_s with flat-plate absorptivity (same formula as lpbf_thermal_solver.py, King/Rubenchik)."""
    props = screening_props(material)
    v = speed_mm_s * 1e-3
    r = beam_diameter_um * 1e-6 / 2.0
    rho = props["density_kg_m3"]
    k_s = props["thermal_conductivity_W_mK"]
    cp_s = props["specific_heat_J_kgK"]
    alpha_s = k_s / (rho * cp_s)
    denom = rho * cp_s * max(50.0, props["liquidus_C"] - preheat_C) * math.sqrt(math.pi * alpha_s * v * r ** 3)
    return props["absorptivity_IR"] * power_W / max(1e-9, denom)


def classify_regime(material: str, power_W: float, speed_mm_s: float, beam_diameter_um: float,
                    preheat_C: float, balling: Optional[int] = None) -> Dict[str, Any]:
    h = normalized_enthalpy(material, power_W, speed_mm_s, beam_diameter_um, preheat_C)
    if balling == 1:
        label = "balling-flagged"
    elif h >= keyhole_cut(material):
        label = "keyhole"
    elif h >= ENTHALPY_TRANSITION:
        label = "transition"
    else:
        label = "conduction"
    return {"label": label, "normalizedEnthalpy": h}


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Rebuild the committed small derived tables from the raw downloads.")
    ap.add_argument("--hofmann-raw", help="MeltpoolGeometryData.csv")
    ap.add_argument("--totis-raw", help="Allegati.zip or Data.xlsx")
    a = ap.parse_args(argv)
    if a.hofmann_raw:
        print("hofmann table sha256", build_hofmann_table(a.hofmann_raw), "raw sha256", sha256_file(a.hofmann_raw))
    if a.totis_raw:
        print("totis table sha256", build_totis_table(a.totis_raw))
    return 0


if __name__ == "__main__":
    sys.exit(main())
