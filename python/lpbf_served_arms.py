"""Single definition of the served melt-pool arm for the user blind test and the spent-set descriptive record.

Research hub spec (docs/research/SPEC_research_hub_data_2026-10-14.md) section 3.1, row `lpbf_served_arms.py`, and 3.6.

`served_arm` reproduces the thermal call of the Build Job (`lpbf_build_job_solver._solve_lpbf_build_job_core`, the
`calculate_meltpool_physics(...)` call after the material snapshot) without importing `lpbf_build_job_solver`, whose
import loads about 21 further project modules and lazily the machine-calibrated block. The parity test
(`test_lpbf_served_arms.py`) compares this function with `solve_lpbf_build_job(..., bypassCache=True)` in the test
process only.

What it is not:
  * Not in `lpbf_simulation.IMPLEMENTATION_SOURCE_FILES`; nothing served imports it. It changes no served value.
  * It holds no research code and imports no `lpbf_research_*` module (spec 7.6, R13). The research arm of protocol 1
    is the constant `RESEARCH_NOT_REQUESTED`.
  * Flat-plate absorption and the default CPU slice backend always, so the powder ray tracer and the Warp backend are
    never reached.

The served-closure pin (`data/blind/served-closure-pin-v1.json`) lists every project module this arm loads that is not
in the fingerprint manifest, hashed through `lpbf_source_identity.canonical_source_bytes` (LF and CRLF hash alike).
"""
from __future__ import annotations

import hashlib
import json
import platform
from pathlib import Path

from four_alloy_materials import ALLOY_MATERIALS, canonical_material_source, resolve_alloy_id
from lpbf_build_job_material_snapshot import build_build_job_identity, build_material_property_snapshot
from lpbf_job_cache import BUILD_JOB_MODEL_ID, BUILD_JOB_SOLVER_REVISION
from lpbf_public_datasets import normalized_enthalpy
from lpbf_thermal_solver import calculate_meltpool_physics

PYTHON_DIR = Path(__file__).resolve().parent
REPO_ROOT = PYTHON_DIR.parent
CLOSURE_PIN_PATH = REPO_ROOT / "data" / "blind" / "served-closure-pin-v1.json"
CLOSURE_PIN_SCHEMA = "lpbf-served-closure-pin-1"

# Build Job request defaults (`lpbf_build_job_schema.LpbfBuildJobRequest`, `lpbf_build_job_solver.DEFAULT_PROCESS_SEED`).
# Copied, not imported (importing lpbf_build_job_solver is what this module avoids); the parity test checks equality.
BUILD_JOB_HATCH_UM = 110.0
BUILD_JOB_LAYER_UM = 40.0
BUILD_JOB_WAVELENGTH = "IR_1064nm"
DEFAULT_PROCESS_SEED = 42
# include_process_map=False skips the 49-cell process window grid only; the parity test proves the geometry is
# identical to the Build Job call, which runs with the grid (spec 3.1: X is False only when that test passes).
INCLUDE_PROCESS_MAP = False

# Protocol alloy names (metadata vocabulary) to the served path.
PROTOCOL_ALLOYS = ("Ti-6Al-4V", "AlSi10Mg", "316L", "IN718", "IN625")
BUILD_JOB_ALLOY = {"Ti-6Al-4V": "ti6al4v", "AlSi10Mg": "alsi10mg", "316L": "ss316l", "IN718": "in718"}
IN625_THERMAL_NAME = "Inconel 625"
IN625_REASON = "IN625_DIRECT_THERMAL_PATH"

RESEARCH_MEMBER = {"requested": False, "reasonCode": "RESEARCH_NOT_REQUESTED",
                   "contract": "research/p8-research-arm 14e13ea8"}

# Sensitivity arms (MELT POWER_BAND and BEAM_BAND_GRADE_B, both 0.05).
SENSITIVITY_ARMS = (("served:P-5%", 0.95, 1.0), ("served:P+5%", 1.05, 1.0),
                    ("served:d-5%", 1.0, 0.95), ("served:d+5%", 1.0, 1.05))


def thermal_name(alloy):
    if alloy == "IN625":
        return IN625_THERMAL_NAME
    aid = BUILD_JOB_ALLOY.get(alloy)
    if aid is None:
        raise ValueError(f"alloy {alloy!r} has no served melt-pool path")
    return ALLOY_MATERIALS[aid]["thermal"]


def _snapshot(alloy):
    if alloy not in BUILD_JOB_ALLOY:
        raise ValueError(f"alloy {alloy!r} has no served melt-pool path")
    aid = resolve_alloy_id(BUILD_JOB_ALLOY[alloy])
    mats = ALLOY_MATERIALS[aid]
    snapshot, prop_sha = build_material_property_snapshot(aid, mats["thermal"], mats["slicer"])
    _, authority_sha = canonical_material_source(aid)
    identity = build_build_job_identity(aid, BUILD_JOB_MODEL_ID, BUILD_JOB_SOLVER_REVISION, prop_sha,
                                        snapshot["schemaVersion"])
    return aid, mats, snapshot, prop_sha, authority_sha, identity


def served_index(alloy, P_W, v_mm_s, d_1e2_um, T0_C):
    """Unrounded normalized enthalpy dH/h_s (the MELT runner's leverage convention)."""
    return float(normalized_enthalpy(thermal_name(alloy), P_W, v_mm_s, d_1e2_um, T0_C))


def served_arm(alloy, P_W, v_mm_s, d_1e2_um, T0_C, layer_um=BUILD_JOB_LAYER_UM, *, include_process_map=None):
    """One served prediction. Returns {status: ok, depth_um, width_um, extentStatus, fabbroDepth_um, index, ...} or
    {status: failed, reason}. Raises only on a programming error; a solver exception is the caller's to classify."""
    pm = INCLUDE_PROCESS_MAP if include_process_map is None else bool(include_process_map)
    if alloy == "IN625":
        thermal = calculate_meltpool_physics(IN625_THERMAL_NAME, float(P_W), float(v_mm_s), float(d_1e2_um),
                                             float(T0_C), float(layer_um), BUILD_JOB_HATCH_UM, BUILD_JOB_WAVELENGTH,
                                             incline_angle_deg=0.0, process_seed=DEFAULT_PROCESS_SEED,
                                             include_process_map=pm)
        evidence = (thermal.get("materialEvidence") or {}).get("provenanceClass")
        extra = {"reasonLabel": IN625_REASON, "materialEvidence": evidence, "buildJobIdentity": None}
    else:
        _aid, mats, snapshot, _sha, _auth, identity = _snapshot(alloy)
        thermal = calculate_meltpool_physics(mats["thermal"], float(P_W), float(v_mm_s), float(d_1e2_um),
                                             float(T0_C), float(layer_um), BUILD_JOB_HATCH_UM, BUILD_JOB_WAVELENGTH,
                                             incline_angle_deg=0.0, process_seed=DEFAULT_PROCESS_SEED,
                                             prop_overrides=snapshot["thermal"], include_process_map=pm)
        extra = {"reasonLabel": None, "materialEvidence": None, "buildJobIdentity": identity["sha256"]}
    geometry = thermal.get("meltPoolGeometry") or {}
    extent = geometry.get("extentStatus")
    fabbro = (thermal.get("keyholeModel") or {}).get("fabbroDepth_um")
    index = served_index(alloy, P_W, v_mm_s, d_1e2_um, T0_C)
    base = {"extentStatus": extent, "index": index,
            "fabbroDepth_um": float(fabbro) if isinstance(fabbro, (int, float)) else None, **extra}
    if extent != "computed":
        return {"status": "failed", "reason": "EXTENT_NOT_COMPUTED", **base}
    return {"status": "ok", "depth_um": float(geometry["depth_um"]), "width_um": float(geometry["width_um"]), **base}


def sensitivity_arms(alloy, P_W, v_mm_s, d_1e2_um, T0_C, layer_um=BUILD_JOB_LAYER_UM):
    """Served at P x 0.95, P x 1.05, d x 0.95 and d x 1.05; each value as served_arm returns it."""
    return {name: served_arm(alloy, P_W * fp, v_mm_s, d_1e2_um * fd, T0_C, layer_um)
            for name, fp, fd in SENSITIVITY_ARMS}


# ------------------------------------------------------------------------------------------------
# Served-closure pin and predictor identity (spec 3.6)
# ------------------------------------------------------------------------------------------------
def canonical_file_sha256(path):
    from lpbf_source_identity import canonical_source_bytes
    path = Path(path)
    rel = path.resolve().relative_to(REPO_ROOT).as_posix()
    return hashlib.sha256(canonical_source_bytes(rel, path.read_bytes())).hexdigest()


def load_closure_pin(path=CLOSURE_PIN_PATH):
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    if doc.get("schema") != CLOSURE_PIN_SCHEMA or not isinstance(doc.get("files"), list):
        raise ValueError("served-closure pin has an unknown schema")
    return doc


def closure_pin_document(files):
    """Pin document for repo-relative paths (sorted), with each canonical sha256."""
    entries = [{"path": p, "sha256": canonical_file_sha256(REPO_ROOT / p)} for p in sorted(set(files))]
    return {"schema": CLOSURE_PIN_SCHEMA,
            "note": ("Project modules the served blind-test arm loads that are not in "
                     "lpbf_simulation.IMPLEMENTATION_SOURCE_FILES. A change is a reviewed commit."),
            "files": entries}


def pin_sha256(path=CLOSURE_PIN_PATH):
    """sha256 of the pin file with CRLF read as LF (checkout independent)."""
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def closure_status(path=CLOSURE_PIN_PATH):
    """{pinSha256, files [{path, liveSha256, pinnedSha256}], mismatched [paths]} against the live files."""
    doc = load_closure_pin(path)
    files, bad = [], []
    for e in doc["files"]:
        target = REPO_ROOT / e["path"]
        live = canonical_file_sha256(target) if target.is_file() else None
        files.append({"path": e["path"], "liveSha256": live, "pinnedSha256": e["sha256"]})
        if live != e["sha256"]:
            bad.append(e["path"])
    return {"pinSha256": pin_sha256(path), "files": files, "mismatched": bad}


def predictor_identity(alloy, *, pin_path=CLOSURE_PIN_PATH):
    """Predictor identity of spec 3.6 for one alloy. Pure reads; no solver call."""
    import numpy
    import scipy
    from lpbf_fingerprint_pin import read_pinned_fingerprint
    from lpbf_simulation import implementation_fingerprint
    ident = {
        "implementationFingerprint": implementation_fingerprint(),
        "pinnedFingerprint": read_pinned_fingerprint(),
        "servedClosure": {k: v for k, v in closure_status(pin_path).items() if k != "mismatched"},
        "buildJobSolverRevision": BUILD_JOB_SOLVER_REVISION,
        "buildJobModelId": BUILD_JOB_MODEL_ID,
        "alloy": alloy,
        "research": dict(RESEARCH_MEMBER),
        "heatSource": "rosenthal",
        "absorptionModel": "flat-plate",
        "includeProcessMap": INCLUDE_PROCESS_MAP,
        "python": platform.python_version(),
        "numpy": numpy.__version__,
        "scipy": scipy.__version__,
    }
    if alloy == "IN625":
        ident.update(materialPropertySha256=None, materialAuthorityRevisionSha256=None, buildJobIdentitySha256=None,
                     servedPath=IN625_REASON)
    else:
        _aid, _m, _s, prop_sha, auth_sha, identity = _snapshot(alloy)
        ident.update(materialPropertySha256=prop_sha, materialAuthorityRevisionSha256=auth_sha,
                     buildJobIdentitySha256=identity["sha256"], servedPath="build-job-thermal")
    return ident


def unpinned_reasons(identity):
    """Why an identity cannot freeze (empty list when pinned)."""
    out = []
    if identity["implementationFingerprint"] != identity["pinnedFingerprint"]:
        out.append("implementation fingerprint differs from python/lpbf_implementation_fingerprint.expected")
    for f in identity["servedClosure"]["files"]:
        if f["liveSha256"] != f["pinnedSha256"]:
            out.append(f["path"])
    return out
