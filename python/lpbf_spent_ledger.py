"""Loader and checks for data/benchmark/spent-ledger-v1.json (schema lpbf-spent-ledger-1).

Research hub spec section 8.1. Used by the user blind test exposure check (6.4 item 5) and the spent-set descriptive
producer (section 8). Metadata only: the ledger holds no measured value. `spent_condition_tuples` reads the inputs of
the committed open sets through their pinned loaders and drops every measured field at once; nothing here returns,
prints or logs a depth or width.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LEDGER_PATH = REPO_ROOT / "data" / "benchmark" / "spent-ledger-v1.json"
SCHEMA = "lpbf-spent-ledger-1"
STATUSES = ("SPENT", "EXPOSED", "EXPOSED-LOW", "CLEAN", "UNUSABLE")
OBSERVABLES = ("fusion-boundary-depth", "vapour-depression-depth", "keyhole-boundary-depth")
TRANSCRIPTION = ("table", "digitized-figure", "derived-from-raw-images")
REQUIRED = ("datasetId", "title", "doi", "alloy", "observable", "datum", "beam", "powerBasis", "substrate",
            "digitized", "status", "spentBy", "sameExperimentsAs", "loader", "tableSha256", "curveAxis", "locator",
            "licence", "attribution", "licenceFile", "transcription", "inputsInferred", "usedInServedDevelopment")
# Spec 8.1 item 2: never admitted to the descriptive producer.
FORBIDDEN_IDS = ("bitharas", "leis", "hyer", "aboulkhair", "ruckh", "gong", "ullah", "wimmer", "huang",
                 "ku-leuven-in718", "hann", "nist-mds2-2923-in718", "cmu")


class SpentLedgerError(ValueError):
    pass


def validate_entry(e):
    if not isinstance(e, dict):
        raise SpentLedgerError("ledger entry must be an object")
    missing = [k for k in REQUIRED if k not in e]
    if missing:
        raise SpentLedgerError(f"entry {e.get('datasetId')!r} misses {missing}")
    extra = [k for k in e if k not in REQUIRED]
    if extra:
        raise SpentLedgerError(f"entry {e.get('datasetId')!r} has unknown keys {extra}")
    if e["status"] not in STATUSES or e["observable"] not in OBSERVABLES or e["transcription"] not in TRANSCRIPTION:
        raise SpentLedgerError(f"entry {e['datasetId']!r} has a value outside the closed vocabulary")
    for k in ("licence", "attribution", "licenceFile"):
        if not isinstance(e[k], str) or not e[k].strip():
            raise SpentLedgerError(f"entry {e['datasetId']!r} needs {k}")
    if e["licenceFile"] != "none" and not (REPO_ROOT / e["licenceFile"]).is_file():
        raise SpentLedgerError(f"entry {e['datasetId']!r}: licence file {e['licenceFile']} is not committed")
    beam = e["beam"]
    if not isinstance(beam, dict) or beam.get("status") not in ("stated", "assumed", "unverified"):
        raise SpentLedgerError(f"entry {e['datasetId']!r} beam must be an object with a status")
    return e


def load_ledger(path=LEDGER_PATH):
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    if doc.get("schema") != SCHEMA or not isinstance(doc.get("entries"), list):
        raise SpentLedgerError("unknown spent ledger schema")
    ids = [validate_entry(e)["datasetId"] for e in doc["entries"]]
    if len(set(ids)) != len(ids):
        raise SpentLedgerError("duplicate datasetId")
    return doc


def ledger_sha256(path=LEDGER_PATH):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def spent_dois(path=LEDGER_PATH):
    """{normalised DOI: datasetId} of SPENT and EXPOSED entries."""
    out = {}
    for e in load_ledger(path)["entries"]:
        if e["status"] in ("SPENT", "EXPOSED", "EXPOSED-LOW") and isinstance(e.get("doi"), str):
            out[e["doi"].strip().lower()] = e["datasetId"]
    return out


def _protocol_alloy(material):
    m = str(material or "").lower()
    if "625" in m:
        return "IN625"
    if "718" in m:
        return "IN718"
    if "316" in m:
        return "316L"
    if "alsi" in m:
        return "AlSi10Mg"
    if "ti" in m and "6al" in m.replace("-", ""):
        return "Ti-6Al-4V"
    return None


def _inputs_only(rows, keep=None):
    out = []
    for r in rows:
        alloy = _protocol_alloy(r.get("material"))
        if keep is not None and alloy != keep:
            continue
        out.append((alloy, float(r["power_W"]), float(r["speed_mm_s"]), float(r["beamDiameter_um"])))
    return out


def _loader_tuples(dataset_id):
    import lpbf_public_datasets as pds
    if dataset_id == "lane-in625-amb2018-02":
        return _inputs_only(pds.load_lane_in625()["rows"])
    if dataset_id == "ku-leuven-316l-2021":
        return _inputs_only(pds.load_ku_leuven_316l_ti64()["rows"], keep="316L")
    if dataset_id == "ku-leuven-ti64-2021":
        return _inputs_only(pds.load_ku_leuven_316l_ti64()["rows"], keep="Ti-6Al-4V")
    if dataset_id == "totis-ti64-2021":
        return _inputs_only(pds.load_totis_ti64()["rows"])
    if dataset_id == "nist-amb2022-03-optical":
        from lpbf_process_window import _load_nist_table4
        return _inputs_only(_load_nist_table4()["rows"])
    if dataset_id == "cunningham-ti64-2019":
        from lpbf_keyhole_literature import load_cunningham_depths
        return _inputs_only(load_cunningham_depths()["rows"])
    return []


@lru_cache(maxsize=1)
def spent_condition_tuples():
    """{datasetId: [(alloy, P_W, v_mm_s, d_um)]} for SPENT and EXPOSED entries with a loader. Inputs only."""
    out = {}
    for e in load_ledger()["entries"]:
        if e["status"] not in ("SPENT", "EXPOSED", "EXPOSED-LOW"):
            continue
        try:
            out[e["datasetId"]] = _loader_tuples(e["datasetId"])
        except Exception:  # a loader that cannot verify its pinned file contributes no tuple
            out[e["datasetId"]] = []
    return out
