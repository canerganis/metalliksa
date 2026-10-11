#!/usr/bin/env python3
"""Regime-dependent absorptivity evaluation harness (research, SCREENING ONLY, NOT VALIDATION).

Implements exactly docs/research/PREDECLARED_regime_absorptivity_2026-10-09.md (as amended by Amendment 1) and its
machine-readable copy python/lpbf_regime_absorptivity_config.py. Nothing frozen is edited: the candidate law lives in
python/lpbf_regime_absorptivity_kernel.py, which rebuilds the kernel composition from the frozen building blocks with the
absorptivity passed in as an input.

Stages (section 9 of the pre-registration):
  --stage inputs    stage 1, input-only record (no kernel output)
  --stage baseline  stage 2, parity check, baseline run and frozen scoring populations (no candidate output)
  --stage run       stage 3, all arms, all metrics, the mechanical verdict; refuses to start unless the stage-1 and
                    stage-2 records are committed and their hashes match

Usage (repo root, PYTHONDONTWRITEBYTECODE=1):
    python -B python/tools/lpbf_regime_absorptivity_eval.py --stage inputs   --date 2026-10-09
    python -B python/tools/lpbf_regime_absorptivity_eval.py --stage baseline --date 2026-10-09 --jobs 12
    python -B python/tools/lpbf_regime_absorptivity_eval.py --stage run      --date 2026-10-09 --jobs 12
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import itertools
import json
import math
import multiprocessing
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

TOOLS_DIR = Path(__file__).resolve().parent
PYTHON_DIR = TOOLS_DIR.parent
REPO_ROOT = PYTHON_DIR.parent
sys.path.insert(0, str(PYTHON_DIR))

import lpbf_calibration_stats as st  # noqa: E402

st.pin_flat_plate()  # flat-plate path, before the solver module is imported

import lpbf_regime_absorptivity_config as C  # noqa: E402
import lpbf_regime_absorptivity_kernel as K  # noqa: E402

CFG = C.CONFIG
KERNELS: Tuple[str, ...] = tuple(CFG["kernels"])
VERDICT_SOURCES: List[str] = list(CFG["dataRoles"]["meltPoolSources"])
TRAINABLE: List[str] = list(CFG["dataRoles"]["trainableClass"])
MAN = CFG["sourceManifest"]["sources"]
H_ON = float(CFG["law"]["H_on"])
PHI = float(CFG["sourceManifest"]["depthDatumPhi"])
BOOT_B = int(CFG["metrics"]["bootstrap"]["B"])
BOOT_SEED = int(CFG["metrics"]["bootstrap"]["seed"])
MAX_UNDEF = int(CFG["metrics"]["bootstrap"]["maxUndefined"])
Z90 = float(CFG["metrics"]["pi90"]["z"])
ALPHA = float(CFG["metrics"]["intervalScore"]["alpha"])
IS_MARGIN = float(CFG["metrics"]["intervalScore"]["margin"])
DW_KEY = float(CFG["metrics"]["regime"]["dw_keyhole_threshold"])
LABEL_I_SOURCES: List[str] = list(CFG["metrics"]["regime"]["labelSetISources"])
KU_SOURCES: List[str] = list(CFG["dataRoles"]["kuSources"])
NOMINAL_LAYER_UM = float(CFG["rows"]["bareLayerNominal_um"])
DEFAULT_HATCH_UM = float(CFG["rows"]["defaultHatch_um"])
PREHEAT_C = float(CFG["rows"]["preheat_C"])
ENVELOPE = tuple(CFG["law"]["envelope"])
Q_LIST = ("depth", "width")
PRIMARY = CFG["nuisance"]["primary"]
SOURCE_MATERIAL = {"hofmann-316l-2026": "316L Stainless Steel", "ku-leuven-316l-2021": "316L Stainless Steel",
                   "totis-ti64-2021": "Ti-6Al-4V", "ku-leuven-ti64-2021": "Ti-6Al-4V",
                   "lane-in625-2020": "Inconel 625", "ghosh-in625-2018": "Inconel 625"}
STAGE1_SCHEMA = "lpbf-regime-absorptivity-stage1-1"
STAGE2_SCHEMA = "lpbf-regime-absorptivity-stage2-1"
RESULT_SCHEMA = "lpbf-regime-absorptivity-result-1"
EVIDENCE = CFG["labels"]["evidence"]


# ---------------------------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------------------------
def fmt(x: float) -> str:
    return f"{x:g}"


def jsonable(o: Any) -> Any:
    if isinstance(o, dict):
        return {str(k): jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [jsonable(v) for v in o]
    if isinstance(o, (np.floating, float)):
        f = float(o)
        return f if math.isfinite(f) else None
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return jsonable(o.tolist())
    return o


def dump_json(obj: Any) -> str:
    return json.dumps(jsonable(obj), sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(Path(p).read_bytes())


def lf_sha(b: bytes) -> str:
    """Record hash over LF-normalised bytes, so a CRLF checkout (core.autocrlf) does not change it."""
    return sha256_bytes(b.replace(bytes([13, 10]), bytes([10])))


def git(*args: str) -> str:
    r = subprocess.run(["git", *args], cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=120)
    return r.stdout.strip()


# ---------------------------------------------------------------------------------------------
# policies
# ---------------------------------------------------------------------------------------------
def law_policy(A_kh: float, H_s: float, fabbro: bool = False) -> Tuple:
    return ("law", float(A_kh), H_ON, float(H_s), bool(fabbro))


def gan_policy(material: str) -> Optional[Tuple]:
    g = CFG["arms"]["G"]
    am = g["Am"].get(material)
    if am is None:
        return None
    return ("gan", float(g["eta_max"]), float(g["rate"]), float(am), float(g["deltaT_floor_K"]))


ARM_LAW = {"A0": law_policy(0.70, 5.0), "S1": law_policy(0.62, 5.0), "S2": law_policy(0.79, 5.0),
           "S3": law_policy(0.70, 2.5), "S4": law_policy(0.70, 10.0), "K": law_policy(0.70, 5.0, True)}
ARMS = ("A0", "S1", "S2", "S3", "S4", "G", "K", "F")
F_GRID = [float(CFG["arms"]["F"]["H_s_grid"]["start"]) + 0.5 * i
          for i in range(int(round((CFG["arms"]["F"]["H_s_grid"]["stop"] - CFG["arms"]["F"]["H_s_grid"]["start"]) / 0.5)) + 1)]


# ---------------------------------------------------------------------------------------------
# stage 1: rows and inputs (no kernel output)
# ---------------------------------------------------------------------------------------------
def kernel_args(material: str, power: float, speed: float, beam: float, preheat: float,
                layer_raw: Optional[float]) -> Tuple:
    layer = layer_raw if (layer_raw is not None and layer_raw > 0) else NOMINAL_LAYER_UM
    return (material, float(power), float(speed), float(beam), float(preheat), float(layer), DEFAULT_HATCH_UM)


def _pos(x: Any) -> bool:
    return x is not None and isinstance(x, (int, float)) and math.isfinite(x) and x > 0


def build_row(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Stage-1 row from a raw row: {rowId, source, role, material, axis, variants{vk:(P,v,d)}, preheat_C, layer_um,
    width_um, depth_um, t_um, balling, publishedLabel, extra}."""
    src = raw["source"]
    gate = dict(MAN.get(src, {}).get("gate", {"depth": False, "width": False}))
    reasons: List[str] = []
    w, d = raw.get("width_um"), raw.get("depth_um")
    valid_w, valid_d = _pos(w), _pos(d)
    if not valid_w:
        reasons.append("width missing, nonpositive or nonfinite")
    if not valid_d:
        reasons.append("depth missing, nonpositive or nonfinite")
    t = float(raw.get("t_um") or 0.0)
    balling = raw.get("balling")
    variants: Dict[str, Any] = {}
    for vk, (P, v, dia) in raw["variants"].items():
        args = kernel_args(raw["material"], P, v, dia, raw.get("preheat_C", PREHEAT_C), raw.get("layer_um"))
        H = K.flat_enthalpy(raw["material"], P, v, dia, raw.get("preheat_C", PREHEAT_C))
        variants[vk] = {"power_W": float(P), "speed_mm_s": float(v), "beamDiameter_um": float(dia),
                        "preheat_C": float(args[4]), "layer_input_um": args[5], "hatch_um": args[6],
                        "H": float(H), "affected": bool(H > H_ON),
                        "cluster": "|".join([src, fmt(P), fmt(v), fmt(dia), fmt(args[5])])}
    d_layer = (float(d) + PHI * t) if valid_d else None
    row = {"rowId": raw["rowId"], "source": src, "role": raw["role"], "material": raw["material"],
           "axis": raw.get("axis"), "t_um": t, "balling": balling, "publishedLabel": raw.get("publishedLabel"),
           "width_um": float(w) if valid_w else None, "depth_published_um": float(d) if valid_d else None,
           "depth_layer_um": d_layer, "inputValid": {"width": valid_w, "depth": valid_d}, "invalidReasons": reasons,
           "gate": gate,
           "eligible": {"depth": bool(valid_d and gate.get("depth")),
                        "width": bool(valid_w and gate.get("width") and balling != 1)},
           "variants": variants,
           "dwPublished": (float(d) / float(w)) if (valid_w and valid_d) else None,
           "dwLayer": (d_layer / float(w)) if (valid_w and valid_d) else None}
    row.update(raw.get("extra") or {})
    return row


def variant_key(row: Dict[str, Any], g: Dict[str, Any]) -> str:
    ax = row.get("axis")
    if ax == "kuBeam":
        return fmt(g["kuBeam_um"])
    if ax == "ghoshSpot":
        return fmt(g["ghoshSpot_um"])
    if ax == "lanePower":
        return g["lanePower"]
    return "base"


def source_variant_key(source: str, g: Dict[str, Any]) -> str:
    if source in KU_SOURCES:
        return fmt(g["kuBeam_um"])
    if source == "ghosh-in625-2018":
        return fmt(g["ghoshSpot_um"])
    if source == "lane-in625-2020":
        return g["lanePower"]
    return "base"


def make_grid(lane_active: bool) -> List[Dict[str, Any]]:
    nz = CFG["nuisance"]
    lanes = list(nz["lanePower"]) if lane_active else ["table3"]
    out = []
    for ku, gh, datum, lane in itertools.product(nz["kuBeam_um"], nz["ghoshSpot_um"], nz["datum"], lanes):
        out.append({"kuBeam_um": float(ku), "ghoshSpot_um": float(gh), "datum": datum, "lanePower": lane})
    return out


def grid_key(g: Dict[str, Any]) -> str:
    return f"ku{fmt(g['kuBeam_um'])}|gh{fmt(g['ghoshSpot_um'])}|{g['datum']}|{g['lanePower']}"


def meas_value(row: Dict[str, Any], q: str, g: Dict[str, Any]) -> Optional[float]:
    if q == "width":
        return row["width_um"]
    return row["depth_layer_um"] if g["datum"] == "layer" else row["depth_published_um"]


def meas_dw(row: Dict[str, Any], g: Dict[str, Any]) -> Optional[float]:
    return row["dwLayer"] if g["datum"] == "layer" else row["dwPublished"]


def load_raw_rows() -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Raw rows from the sha256-pinned loaders and their provenance (table hashes)."""
    import lpbf_public_datasets as pd
    import lpbf_literature_datasets as L
    import lpbf_keyhole_literature as KL

    raws: List[Dict[str, Any]] = []
    prov: Dict[str, Any] = {}

    h = pd.load_hofmann_316l()
    prov["hofmann-316l-2026"] = {"tableSha256": h["provenance"]["fileSha256"], "doi": h["provenance"]["doi"]}
    for r in h["rows"]:
        raws.append({"rowId": r["rowId"], "source": "hofmann-316l-2026", "role": "verdict", "material": r["material"],
                     "axis": None, "variants": {"base": (r["power_W"], r["speed_mm_s"], r["beamDiameter_um"])},
                     "preheat_C": r["preheat_C"], "layer_um": r["layer_um"], "width_um": r["width_um"],
                     "depth_um": r["depth_um"], "t_um": r["layer_um"], "balling": r["balling"]})
    t = pd.load_totis_ti64()
    prov["totis-ti64-2021"] = {"tableSha256": t["provenance"]["fileSha256"], "doi": t["provenance"]["doi"]}
    for r in t["rows"]:
        raws.append({"rowId": r["rowId"], "source": "totis-ti64-2021", "role": "verdict", "material": r["material"],
                     "axis": None, "variants": {"base": (r["power_W"], r["speed_mm_s"], r["beamDiameter_um"])},
                     "preheat_C": r["preheat_C"], "layer_um": r["layer_um"], "width_um": r["width_um"],
                     "depth_um": r["depth_um"], "t_um": MAN["totis-ti64-2021"]["datumLayer_um"], "balling": None})
    ku_by: Dict[str, Dict[str, Any]] = {}
    for beam in CFG["nuisance"]["kuBeam_um"]:
        ku = pd.load_ku_leuven_316l_ti64(beam_diameter_um=float(beam))
        for r in ku["rows"]:
            e = ku_by.setdefault(r["rowId"], {"rowId": r["rowId"], "source": r["dataset"], "role": "verdict",
                                              "material": r["material"], "axis": "kuBeam", "variants": {},
                                              "preheat_C": r["preheat_C"], "layer_um": r["layer_um"],
                                              "width_um": r["width_um"], "depth_um": r["depth_um"],
                                              "t_um": MAN[r["dataset"]]["datumLayer_um"], "balling": None,
                                              "publishedLabel": r.get("publishedRegime")})
            e["variants"][fmt(float(beam))] = (r["power_W"], r["speed_mm_s"], float(beam))
        prov["ku-leuven-316l-2021"] = prov["ku-leuven-ti64-2021"] = {"tableSha256": ku["provenance"]["fileSha256"]}
    raws.extend(ku_by.values())
    lane_by: Dict[str, Dict[str, Any]] = {}
    for key, nominal in (("table3", False), ("nominal", True)):
        la = pd.load_lane_in625(use_nominal_power=nominal)
        prov["lane-in625-2020"] = {"tableSha256": la["provenance"]["fileSha256"], "doi": la["provenance"]["doi"]}
        for r in la["rows"]:
            e = lane_by.setdefault(r["rowId"], {"rowId": r["rowId"], "source": "lane-in625-2020", "role": "verdict",
                                                "material": r["material"], "axis": "lanePower", "variants": {},
                                                "preheat_C": r["preheat_C"], "layer_um": r["layer_um"],
                                                "width_um": r["width_um"], "depth_um": r["depth_um"], "t_um": 0.0,
                                                "balling": None})
            e["variants"][key] = (r["power_W"], r["speed_mm_s"], r["beamDiameter_um"])
    raws.extend(lane_by.values())
    gh_by: Dict[str, Dict[str, Any]] = {}
    for spot in CFG["nuisance"]["ghoshSpot_um"]:
        g = L.load_ghosh_in625(beam_diameter_um=float(spot))
        prov["ghosh-in625-2018"] = {"tableSha256": g["provenance"]["fileSha256"], "doi": g["provenance"]["doi"]}
        for r in g["rows"]:
            e = gh_by.setdefault(r["rowId"], {"rowId": r["rowId"], "source": "ghosh-in625-2018", "role": "verdict",
                                              "material": r["material"], "axis": "ghoshSpot", "variants": {},
                                              "preheat_C": r["preheat_C"], "layer_um": r["layer_um"],
                                              "width_um": r["width_um"], "depth_um": r["depth_um"], "t_um": 0.0,
                                              "balling": None})
            e["variants"][fmt(float(spot))] = (r["power_W"], r["speed_mm_s"], float(spot))
    raws.extend(gh_by.values())
    tr = L.load_trapp_316l_tracks()
    prov["trapp-316l-2017"] = {"tableSha256": tr["provenance"]["fileSha256"], "doi": tr["provenance"]["doi"]}
    for r in tr["rows"]:
        if r["depth_um"] is None:
            continue  # no plotted depth (the 117 W row): excluded from D6
        raws.append({"rowId": r["rowId"], "source": "trapp-316l-2017", "role": "diagnostic", "material": r["material"],
                     "axis": None, "variants": {"base": (r["power_W"], r["speed_mm_s"], r["beamDiameter_um"])},
                     "preheat_C": r["preheat_C"], "layer_um": r["layer_um"], "width_um": r["width_um"],
                     "depth_um": r["depth_um"], "t_um": 0.0, "balling": None})
    cu = KL.load_cunningham_depths()
    prov["cunningham-ti64-2019"] = {"tableSha256": cu["provenance"]["fileSha256"],
                                    "linesSha256": cu["provenance"]["linesFileSha256"]}
    for r in cu["rows"]:
        if r["beamDiameter_um"] != CFG["dataRoles"]["cunninghamSpot_um"] or r["regimeReported"] is None:
            continue
        raws.append({"rowId": r["rowId"], "source": "cunningham-ti64-2019", "role": "diagnostic",
                     "material": r["material"], "axis": None,
                     "variants": {"base": (r["power_W"], r["speed_mm_s"], r["beamDiameter_um"])},
                     "preheat_C": r["preheat_C"], "layer_um": 0.0, "width_um": None,
                     "depth_um": r["vaporDepressionDepth_um"], "t_um": 0.0, "balling": None,
                     "extra": {"cunninghamLabel": r["regimeReported"], "nearBoundary": bool(r["regimeNearBoundary"])}})
    # catalog sentinels: reported separately, never in the verdict
    from meltpool_literature_catalog import TRACKS
    for c in TRACKS:
        if c.get("kind") != "measured":
            continue
        sid = "guo-316l-2024" if c["id"].startswith("guo") else ("nist-amb2022-03-in718" if c["id"].startswith("nist") else None)
        if sid is None:
            continue
        raws.append({"rowId": c["id"], "source": sid, "role": "sentinel", "material": c["material"], "axis": None,
                     "variants": {"base": (c["laserPower_W"], c["scanSpeed_mm_s"], c["beamDiameter_um"])},
                     "preheat_C": c["preheatTemp_C"], "layer_um": 0.0, "width_um": c["width_um"],
                     "depth_um": c["depth_um"], "t_um": 0.0, "balling": None})
    return raws, prov


def build_stage1(raws: Sequence[Dict[str, Any]], prov: Optional[Dict[str, Any]] = None, date: str = "") -> Dict[str, Any]:
    rows = [build_row(r) for r in raws]
    summary: Dict[str, Any] = {}
    lane_aff = False
    for s in sorted({r["source"] for r in rows}):
        sr = [r for r in rows if r["source"] == s]
        per: Dict[str, Any] = {}
        for vk in sorted({vk for r in sr for vk in r["variants"]}):
            vr = [r for r in sr if vk in r["variants"]]
            ent = {"rows": len(vr), "affected": sum(1 for r in vr if r["variants"][vk]["affected"]),
                   "clusters": len({r["variants"][vk]["cluster"] for r in vr})}
            for q in Q_LIST:
                el = [r for r in vr if r["eligible"][q]]
                ent[f"eligible_{q}"] = len(el)
                ent[f"eligibleAffected_{q}"] = sum(1 for r in el if r["variants"][vk]["affected"])
                ent[f"eligibleAffectedClusters_{q}"] = len({r["variants"][vk]["cluster"] for r in el
                                                          if r["variants"][vk]["affected"]})
            per[vk] = ent
            if s == "lane-in625-2020" and ent["affected"] > 0:
                lane_aff = True
        summary[s] = per
    return {"schema": STAGE1_SCHEMA, "date": date, "evidence": EVIDENCE,
            "labels": CFG["labels"], "configSha256": C.config_sha256(),
            "preregistrationCommit": CFG["preregistration"]["commit"],
            "note": "input-only record: no kernel output", "tableProvenance": prov or {},
            "laneAxisActive": bool(lane_aff), "grid": make_grid(lane_aff), "sourceSummary": summary, "rows": rows}


# ---------------------------------------------------------------------------------------------
# kernel tasks (parallel)
# ---------------------------------------------------------------------------------------------
def _quiet_frozen(args: Tuple, kernel: str) -> Tuple:
    import lpbf_thermal_solver as ts
    material, P, v, d, preheat, layer, hatch = args
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            res = ts.calculate_meltpool_physics(material, P, v, d, preheat, layer, hatch, heat_source=kernel,
                                                absorption_model="flat-plate")
        g = res["meltPoolGeometry"]
        return float(g["width_um"]), float(g["depth_um"]), str(g.get("extentStatus"))
    except Exception as exc:  # recorded as data
        return None, None, f"error: {type(exc).__name__}"


def _solve(task: Tuple) -> Tuple:
    policy, kernel, args = task
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            r = K.meltpool_wd(*args, kernel=kernel, policy=policy)
        return r["W_um"], r["D_um"], r["status"], r["A_cond"]
    except Exception as exc:
        return None, None, f"error: {type(exc).__name__}", None


def _parity_task(task: Tuple) -> Tuple:
    kernel, args = task
    mine = _solve((None, kernel, args))
    frozen = _quiet_frozen(args, kernel)
    return mine[:3], frozen


def _init_worker() -> None:
    st.pin_flat_plate()


def pmap(fn: Callable, tasks: Sequence[Any], jobs: int) -> List[Any]:
    if jobs <= 1 or len(tasks) < 8:
        return [fn(t) for t in tasks]
    ctx = multiprocessing.get_context("spawn")
    with ctx.Pool(jobs, initializer=_init_worker) as pool:
        return pool.map(fn, tasks, chunksize=max(1, len(tasks) // (jobs * 8)))


def pkey(policy: Optional[Tuple]) -> str:
    return "baseline" if policy is None else "|".join(str(x) for x in policy)


def args_of(row: Dict[str, Any], vk: str) -> Tuple:
    v = row["variants"][vk]
    return (row["material"], v["power_W"], v["speed_mm_s"], v["beamDiameter_um"], v["preheat_C"],
            v["layer_input_um"], v["hatch_um"])


def valid_res(res: Any) -> bool:
    return (res is not None and res[2] == "computed" and res[0] is not None and res[1] is not None
            and math.isfinite(res[0]) and math.isfinite(res[1]) and res[0] > 0 and res[1] > 0)


# ---------------------------------------------------------------------------------------------
# statistics
# ---------------------------------------------------------------------------------------------
def skill_stats(a_err: np.ndarray, b_err: np.ndarray, cluster: np.ndarray, B: int = BOOT_B,
                seed: int = BOOT_SEED) -> Dict[str, Any]:
    """Same bootstrap scheme as lpbf_calibration_stats.paired_skill, with the undefined-replicate count (7.1.2)."""
    n = int(a_err.size)
    if n == 0:
        return {"skill": None, "ci95": None, "ciEvaluable": False, "mapeCand": None, "mapeBase": None, "n": 0,
                "nClusters": 0, "undefined": None}
    ids, inv = np.unique(np.asarray(cluster), return_inverse=True)
    sa, sb = np.bincount(inv, weights=a_err), np.bincount(inv, weights=b_err)
    cn = np.bincount(inv).astype(float)
    ma_pt, mb_pt = float(a_err.mean()), float(b_err.mean())
    skill = None if mb_pt <= 0 else 1.0 - ma_pt / mb_pt
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(ids), size=(B, len(ids)))
    ma = sa[draws].sum(axis=1) / cn[draws].sum(axis=1)
    mb = sb[draws].sum(axis=1) / cn[draws].sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        sk = np.where(mb > 0, 1.0 - ma / mb, np.nan)
    ok = np.isfinite(sk)
    undef = int(B - ok.sum())
    ci = None
    if undef <= MAX_UNDEF and ok.any():
        ci = [float(np.percentile(sk[ok], 2.5)), float(np.percentile(sk[ok], 97.5))]
    return {"skill": skill, "ci95": ci, "ciEvaluable": ci is not None, "mapeCand": ma_pt, "mapeBase": mb_pt, "n": n,
            "nClusters": int(len(ids)), "undefined": undef}


def pooled_skill(parts: Dict[str, Tuple[np.ndarray, np.ndarray, np.ndarray]], B: int = BOOT_B,
                 seed: int = BOOT_SEED) -> Dict[str, Any]:
    """Equal-source-weight pooled skill, stratified cluster bootstrap (one default_rng stream, sources sorted)."""
    srcs = sorted(parts)
    if not srcs:
        return {"skill": None, "ci95": None, "ciEvaluable": False, "sources": [], "undefined": None}
    rng = np.random.default_rng(seed)
    mas, mbs, pa, pb = [], [], [], []
    for s in srcs:
        a, b, cl = parts[s]
        ids, inv = np.unique(np.asarray(cl), return_inverse=True)
        sa, sb = np.bincount(inv, weights=a), np.bincount(inv, weights=b)
        cn = np.bincount(inv).astype(float)
        draws = rng.integers(0, len(ids), size=(B, len(ids)))
        mas.append(sa[draws].sum(axis=1) / cn[draws].sum(axis=1))
        mbs.append(sb[draws].sum(axis=1) / cn[draws].sum(axis=1))
        pa.append(float(a.mean()))
        pb.append(float(b.mean()))
    num, den = np.mean(mas, axis=0), np.mean(mbs, axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        sk = np.where(den > 0, 1.0 - num / den, np.nan)
    ok = np.isfinite(sk)
    undef = int(B - ok.sum())
    ci = None
    if undef <= MAX_UNDEF and ok.any():
        ci = [float(np.percentile(sk[ok], 2.5)), float(np.percentile(sk[ok], 97.5))]
    mb_mean = float(np.mean(pb))
    pt = None if mb_mean <= 0 else 1.0 - float(np.mean(pa)) / mb_mean
    return {"skill": pt, "ci95": ci, "ciEvaluable": ci is not None, "sources": srcs, "undefined": undef}


def coverage_diff_ci(in_c: np.ndarray, in_b: np.ndarray, cluster: np.ndarray, B: int = BOOT_B,
                     seed: int = BOOT_SEED) -> Optional[List[float]]:
    if in_c.size == 0:
        return None
    ids, inv = np.unique(np.asarray(cluster), return_inverse=True)
    sc, sb = np.bincount(inv, weights=in_c.astype(float)), np.bincount(inv, weights=in_b.astype(float))
    cn = np.bincount(inv).astype(float)
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(ids), size=(B, len(ids)))
    d = (sc[draws].sum(axis=1) - sb[draws].sum(axis=1)) / cn[draws].sum(axis=1)
    return [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))]


def pi_params(resid_by_source: Dict[str, np.ndarray]) -> Dict[str, Any]:
    """M5 pool parameters. Returns {'defined': bool, 'reason'?, 'mu', 'sigma', 'sbFlag'}."""
    pool = {j: r for j, r in resid_by_source.items() if r.size > 0}
    if len(pool) < 2:
        return {"defined": False, "reason": "fewer than 2 pool sources with rows"}
    if not any(r.size >= 2 for r in pool.values()):
        return {"defined": False, "reason": "no pool source with n_j >= 2"}
    m = np.array([r.mean() for r in pool.values()])
    v = np.array([r.var(ddof=1) for r in pool.values() if r.size >= 2])
    sb = float(np.std(m, ddof=1)) if len(pool) >= 3 else 0.0
    sigma = math.sqrt(float(v.mean()) + sb * sb)
    if not sigma > 0:
        return {"defined": False, "reason": "sigma = 0"}
    return {"defined": True, "mu": float(m.mean()), "sigma": sigma, "sbFlag": len(pool) < 3,
            "poolSources": sorted(pool), "poolN": {j: int(r.size) for j, r in sorted(pool.items())}}


def interval_stats(meas: np.ndarray, pred: np.ndarray, resolved: np.ndarray, mu: float, sigma: float,
                   z: float = Z90) -> Dict[str, Any]:
    """Coverage (unresolved rows are misses) and mean log interval score (unresolved left out)."""
    n = int(meas.size)
    inside = np.zeros(n, dtype=bool)
    is_vals = []
    if n:
        with np.errstate(invalid="ignore", divide="ignore"):
            c = np.log(np.where(resolved, pred, 1.0)) + mu
        lo, hi = c - z * sigma, c + z * sigma
        y = np.log(meas)
        inside = resolved & (y >= lo) & (y <= hi)
        sc = (hi - lo) + (2.0 / ALPHA) * np.maximum(lo - y, 0.0) + (2.0 / ALPHA) * np.maximum(y - hi, 0.0)
        is_vals = sc[resolved]
    k = int(inside.sum())
    return {"inside": inside, "coverage": (k / n) if n else None, "k": k, "n": n,
            "wilson95": st.wilson(k, n) if n else None,
            "meanIntervalScore": float(np.mean(is_vals)) if len(is_vals) else None,
            "nIntervalScore": int(len(is_vals)), "nUnresolved": int(n - resolved.sum())}


# ---------------------------------------------------------------------------------------------
# stage 2: parity, baseline, frozen populations
# ---------------------------------------------------------------------------------------------
def unique_tasks(rows: Sequence[Dict[str, Any]], policy: Optional[Tuple], kernels: Sequence[str] = KERNELS,
                 only_affected: bool = False, roles: Optional[Sequence[str]] = None) -> List[Tuple]:
    seen = set()
    out = []
    for r in rows:
        if roles is not None and r["role"] not in roles:
            continue
        for vk, v in r["variants"].items():
            if only_affected and not v["affected"]:
                continue
            a = args_of(r, vk)
            for k in kernels:
                key = (k, a)
                if key not in seen:
                    seen.add(key)
                    out.append((policy, k, a))
    return out


PRE_P1_FINGERPRINT = "0d52d7f707b98fc588c0972c1c198315d3c1071ed1c7ad7ab91616e69b5248e8"


def _live_is_pre_p1() -> Tuple[bool, str]:
    from lpbf_simulation import implementation_fingerprint
    live = implementation_fingerprint()
    return live == PRE_P1_FINGERPRINT, live


def _parity_text(par: Dict[str, Any]) -> str:
    if par["ok"] is None:
        return "not applicable (frozen pre-P1 kernel, live solver is post-P1; no live-solver check was run)"
    return f"{'pass' if par['ok'] else 'FAIL'}, {par['nChecked']} kernel inputs, max rel err {par['maxRelErr']:.2e}"


def run_baseline(stage1: Dict[str, Any], jobs: int = 1) -> Dict[str, Any]:
    rows = stage1["rows"]
    tasks = unique_tasks(rows, None)
    ptasks = [(k, a) for (_, k, a) in tasks]
    rtol = CFG["parity"]["rtol"]
    fails, max_rel = [], 0.0
    res_by: Dict[Tuple, Tuple] = {}
    # The kernel is frozen as the pre-P1 served path (P1 planned bump, 2026-10-11). Parity against the live solver
    # only holds on a tree at the pre-P1 fingerprint; on any later tree the baseline is computed from the frozen
    # kernel alone and the parity block records why no live check was made (it is not a pass against the live solver).
    pre_p1, live = _live_is_pre_p1()
    if not pre_p1:
        for t in tasks:
            res_by[(t[1], t[2])] = _solve(t)[:3]
        baseline_only: Dict[str, Any] = {}
        for r in rows:
            baseline_only[r["rowId"]] = {vk: {k: list(res_by[(k, args_of(r, vk))]) for k in KERNELS} for vk in r["variants"]}
        return {"baseline": baseline_only,
                "parity": {"ok": None, "status": "not-applicable", "nChecked": 0, "maxRelErr": None, "rtol": rtol, "failures": [], "nFailures": 0,
                           "skipped": ("live-solver parity not applicable: the kernel is frozen as the pre-P1 served path "
                                       f"(fingerprint {PRE_P1_FINGERPRINT[:8]}); live fingerprint {live[:8]} is post-P1 "
                                       "(2026-10-11), the baseline comes from the frozen kernel alone")}}
    par = pmap(_parity_task, ptasks, jobs)
    for (kernel, a), (mine, frozen) in zip(ptasks, par):
        ok = mine[2] == frozen[2]
        if mine[0] is not None and frozen[0] is not None:
            for x, y in ((mine[0], frozen[0]), (mine[1], frozen[1])):
                rel = abs(x - y) / max(abs(y), 1e-300)
                max_rel = max(max_rel, rel)
                if rel > rtol:
                    ok = False
        elif (mine[0] is None) != (frozen[0] is None):
            ok = False
        if not ok:
            fails.append({"kernel": kernel, "args": list(a), "mine": list(mine), "frozen": list(frozen)})
        res_by[(kernel, a)] = mine
    baseline: Dict[str, Any] = {}
    for r in rows:
        baseline[r["rowId"]] = {vk: {k: list(res_by[(k, args_of(r, vk))]) for k in KERNELS} for vk in r["variants"]}
    return {"baseline": baseline,
            "parity": {"ok": not fails, "nChecked": len(ptasks), "maxRelErr": max_rel, "rtol": rtol,
                       "failures": fails[:20], "nFailures": len(fails)}}


def _clusters(rows: Sequence[Dict[str, Any]], vk: str) -> int:
    return len({r["variants"][vk]["cluster"] for r in rows})


def freeze_populations(stage1: Dict[str, Any], baseline: Dict[str, Any]) -> Dict[str, Any]:
    """P_all and P per (source, variant, kernel, quantity), from the baseline only (rule 6)."""
    pops: Dict[str, Any] = {}
    for r in stage1["rows"]:
        if r["role"] != "verdict":
            continue
        for vk, v in r["variants"].items():
            for k in KERNELS:
                base_ok = valid_res(baseline[r["rowId"]][vk][k])
                for q in Q_LIST:
                    if r["eligible"][q] and base_ok:
                        e = pops.setdefault(r["source"], {}).setdefault(vk, {}).setdefault(k, {}).setdefault(
                            q, {"all": [], "affected": []})
                        e["all"].append(r["rowId"])
                        if v["affected"]:
                            e["affected"].append(r["rowId"])
    return pops


def _arr(rows_by_id: Dict[str, Any], ids: Sequence[str], q: str, g: Dict[str, Any], vk: str, k: str,
         base: Dict[str, Any]) -> Dict[str, np.ndarray]:
    meas, pb, cl = [], [], []
    for i in ids:
        r = rows_by_id[i]
        meas.append(meas_value(r, q, g))
        res = base[i][vk][k]
        pb.append(res[1] if q == "depth" else res[0])
        cl.append(r["variants"][vk]["cluster"])
    return {"meas": np.array(meas, float), "base": np.array(pb, float), "cluster": np.array(cl)}


def grid_sets(stage1: Dict[str, Any], baseline: Dict[str, Any], pops: Dict[str, Any]) -> Dict[str, Any]:
    """E, E_W, T, C4 populations and PI pool memberships per grid reading and kernel (stage 2)."""
    rows_by_id = {r["rowId"]: r for r in stage1["rows"]}
    elig = CFG["eligibility"]
    out: Dict[str, Any] = {}
    for g in stage1["grid"]:
        gk = grid_key(g)
        og: Dict[str, Any] = {}
        for k in KERNELS:
            E, E_W, removed, detail = [], [], {}, {}
            for s in VERDICT_SOURCES:
                vk = source_variant_key(s, g)
                d_ent = pops.get(s, {}).get(vk, {}).get(k, {}).get("depth", {"all": [], "affected": []})
                ids = d_ent["affected"]
                info = {"nDepthRows": len(ids), "nDepthClusters": len({rows_by_id[i]["variants"][vk]["cluster"] for i in ids})}
                mape = None
                if ids:
                    a = _arr(rows_by_id, ids, "depth", g, vk, k, baseline)
                    mape = float(np.mean(np.abs(a["base"] - a["meas"]) / a["meas"]))
                info["baselineDepthMape"] = mape
                if info["nDepthRows"] < elig["minRows"] or info["nDepthClusters"] < elig["minClusters"]:
                    removed[s] = {"q": "depth", "reason": "fewer than 5 rows or 3 clusters in P(depth)"}
                elif not (mape and mape > 0):
                    removed[s] = {"q": "depth", "reason": "baseline depth MAPE is 0 on P(depth)"}
                else:
                    E.append(s)
                if MAN[s]["gate"]["width"]:
                    w_ids = pops.get(s, {}).get(vk, {}).get(k, {}).get("width", {"affected": []})["affected"]
                    info["nWidthRows"] = len(w_ids)
                    info["nWidthClusters"] = len({rows_by_id[i]["variants"][vk]["cluster"] for i in w_ids})
                    wm = None
                    if w_ids:
                        a = _arr(rows_by_id, w_ids, "width", g, vk, k, baseline)
                        wm = float(np.mean(np.abs(a["base"] - a["meas"]) / a["meas"]))
                    info["baselineWidthMape"] = wm
                    if s in E:
                        if info["nWidthRows"] >= elig["minRows"] and info["nWidthClusters"] >= elig["minClusters"] and wm and wm > 0:
                            E_W.append(s)
                        else:
                            removed[s + ":width"] = {"q": "width", "reason": "fewer than 5 rows or 3 clusters, or zero baseline width MAPE"}
                detail[s] = info
            T = [s for s in E if s in TRAINABLE]
            # label set populations
            c4i: Dict[str, List[str]] = {}
            for s in LABEL_I_SOURCES:
                vk = source_variant_key(s, g)
                ids = pops.get(s, {}).get(vk, {}).get(k, {}).get("depth", {"affected": []})["affected"]
                sel = [i for i in ids if rows_by_id[i]["eligible"]["width"]]
                if sel:
                    c4i[s] = sel
            c4ii: Dict[str, List[str]] = {}
            for s in KU_SOURCES:
                vk = source_variant_key(s, g)
                ids = pops.get(s, {}).get(vk, {}).get(k, {}).get("depth", {"affected": []})["affected"]
                sel = [i for i in ids if rows_by_id[i].get("publishedLabel")]
                if sel:
                    c4ii[s] = sel
            # PI pools
            pi: Dict[str, Any] = {}
            for s in VERDICT_SOURCES:
                for q in Q_LIST:
                    pool = {}
                    for j in TRAINABLE:
                        if j == s:
                            continue
                        vj = source_variant_key(j, g)
                        n = len(pops.get(j, {}).get(vj, {}).get(k, {}).get(q, {"all": []})["all"])
                        if n:
                            pool[j] = n
                    pi.setdefault(s, {})[q] = {"pool": pool,
                                               "structurallyDefined": len(pool) >= 2 and any(n >= 2 for n in pool.values())}
            og[k] = {"E": E, "E_W": E_W, "T": T, "removed": removed, "detail": detail,
                     "inconclusiveEarly": bool(len(E) < elig["minSourcesInE"] or not T),
                     "c4": {"i": c4i, "ii": c4ii}, "piPools": pi}
        out[gk] = og
    return out


def build_stage2(stage1: Dict[str, Any], stage1_sha: str, jobs: int = 1, date: str = "",
                 fingerprint: Optional[str] = None) -> Dict[str, Any]:
    run = run_baseline(stage1, jobs)
    pops = freeze_populations(stage1, run["baseline"])
    gsets = grid_sets(stage1, run["baseline"], pops)
    return {"schema": STAGE2_SCHEMA, "date": date, "evidence": EVIDENCE, "labels": CFG["labels"],
            "configSha256": C.config_sha256(), "stage1Sha256": stage1_sha, "fingerprint": fingerprint,
            "note": "baseline and frozen populations only: no candidate output, no skill, coverage, accuracy or interval score",
            "parity": run["parity"], "baseline": run["baseline"], "populations": pops, "gridSets": gsets}


# ---------------------------------------------------------------------------------------------
# stage 3 evaluator
# ---------------------------------------------------------------------------------------------
class Evaluator:
    def __init__(self, stage1: Dict[str, Any], stage2: Dict[str, Any], cand: Dict[str, Dict[Tuple, Tuple]]):
        self.s1, self.s2 = stage1, stage2
        self.rows = {r["rowId"]: r for r in stage1["rows"]}
        self.base = stage2["baseline"]
        self.pops = stage2["populations"]
        self.gsets = stage2["gridSets"]
        self.cand = cand  # policy key -> {(kernel, args): result}
        self._fcache: Dict[Tuple, float] = {}

    # ---- predictions
    def res(self, policy: Optional[Tuple], rid: str, vk: str, k: str) -> Optional[Tuple]:
        if policy is None:
            return tuple(self.base[rid][vk][k])
        row = self.rows[rid]
        if policy[0] == "law" and not row["variants"][vk]["affected"]:
            return tuple(self.base[rid][vk][k])  # identical by construction; D4 verifies it for A0
        return self.cand[pkey(policy)].get((k, args_of(row, vk)))

    def arrays(self, ids: Sequence[str], q: str, g: Dict[str, Any], vk: str, k: str,
               policy: Optional[Tuple]) -> Dict[str, Any]:
        meas, pb, pc, ok, cl = [], [], [], [], []
        for i in ids:
            r = self.rows[i]
            meas.append(meas_value(r, q, g))
            b = self.base[i][vk][k]
            pb.append(b[1] if q == "depth" else b[0])
            c = self.res(policy, i, vk, k)
            good = valid_res(c)
            ok.append(good)
            pc.append((c[1] if q == "depth" else c[0]) if good else np.nan)
            cl.append(r["variants"][vk]["cluster"])
        return {"ids": list(ids), "meas": np.array(meas, float), "base": np.array(pb, float),
                "cand": np.array(pc, float), "ok": np.array(ok, bool), "cluster": np.array(cl)}

    @staticmethod
    def errs(a: Dict[str, Any]) -> Tuple[np.ndarray, np.ndarray]:
        b = np.abs(a["base"] - a["meas"]) / a["meas"]
        with np.errstate(invalid="ignore"):
            c = np.where(a["ok"], np.abs(np.where(a["ok"], a["cand"], a["meas"]) - a["meas"]) / a["meas"], 1.0)
        return c, b

    def pop_ids(self, s: str, g: Dict[str, Any], k: str, q: str, which: str) -> Tuple[str, List[str]]:
        vk = source_variant_key(s, g)
        return vk, list(self.pops.get(s, {}).get(vk, {}).get(k, {}).get(q, {"all": [], "affected": []})[which])

    # ---- per source metrics on P and P_all
    def source_metrics(self, s: str, g: Dict[str, Any], k: str, q: str, policy: Optional[Tuple],
                       which: str = "affected") -> Dict[str, Any]:
        vk, ids = self.pop_ids(s, g, k, q, which)
        a = self.arrays(ids, q, g, vk, k, policy)
        if not ids:
            return {"n": 0}
        c_err, b_err = self.errs(a)
        sk = skill_stats(c_err, b_err, a["cluster"])
        with np.errstate(invalid="ignore"):
            rel_b = (a["base"] - a["meas"]) / a["meas"]
            rel_c = (a["cand"] - a["meas"]) / a["meas"]
        sk.update({"biasBase": float(np.mean(rel_b)),
                   "biasCand": float(np.mean(rel_c[a["ok"]])) if a["ok"].any() else None,
                   "nUnresolved": int((~a["ok"]).sum())})
        return sk

    def parts(self, srcs: Sequence[str], g: Dict[str, Any], k: str, q: str, policy_of: Callable[[str], Optional[Tuple]]):
        out = {}
        for s in srcs:
            vk, ids = self.pop_ids(s, g, k, q, "affected")
            a = self.arrays(ids, q, g, vk, k, policy_of(s))
            c_err, b_err = self.errs(a)
            out[s] = (c_err, b_err, a["cluster"])
        return out

    # ---- regime
    def regime_accuracy(self, label_set: str, g: Dict[str, Any], k: str, policy_of: Callable[[str], Optional[Tuple]],
                        arm_is_base: bool = False) -> Dict[str, Any]:
        sets = self.gsets[grid_key(g)][k]["c4"][label_set]
        per = {}
        for s, ids in sets.items():
            vk = source_variant_key(s, g)
            pol = None if arm_is_base else policy_of(s)
            correct = 0
            for i in ids:
                r = self.rows[i]
                res = self.res(pol, i, vk, k)
                if label_set == "i":
                    truth = meas_dw(r, g) >= DW_KEY
                else:
                    truth = r["publishedLabel"] == "keyhole"
                if valid_res(res):
                    pred = (res[1] / res[0]) >= DW_KEY
                    correct += int(pred == truth)
            per[s] = {"n": len(ids), "accuracy": correct / len(ids)}
        acc = float(np.mean([v["accuracy"] for v in per.values()])) if per else None
        return {"accuracy": acc, "perSource": per, "nSources": len(per)}

    def index_control(self, label_set: str, g: Dict[str, Any], k: str) -> Optional[float]:
        sets = self.gsets[grid_key(g)][k]["c4"][label_set]
        accs = []
        for s, ids in sets.items():
            vk = source_variant_key(s, g)
            c = 0
            for i in ids:
                r = self.rows[i]
                truth = (meas_dw(r, g) >= DW_KEY) if label_set == "i" else (r["publishedLabel"] == "keyhole")
                c += int((r["variants"][vk]["H"] >= CFG["metrics"]["regime"]["indexControl"]["keyholeFromH"]) == truth)
            accs.append(c / len(ids))
        return float(np.mean(accs)) if accs else None

    # ---- PI90
    def pool_resid(self, s: str, q: str, g: Dict[str, Any], k: str, policy: Optional[Tuple]) -> Dict[str, np.ndarray]:
        pool = self.gsets[grid_key(g)][k]["piPools"][s][q]["pool"]
        out = {}
        for j in sorted(pool):
            vj, ids = self.pop_ids(j, g, k, q, "all")
            a = self.arrays(ids, q, g, vj, k, policy)
            with np.errstate(invalid="ignore"):
                ok = a["ok"] & (a["cand"] > 0) if policy is not None else (a["base"] > 0)
            pred = a["cand"] if policy is not None else a["base"]
            out[j] = np.log(a["meas"][ok] / pred[ok])
        return out

    def c5_entry(self, s: str, q: str, g: Dict[str, Any], k: str, policy: Optional[Tuple]) -> Dict[str, Any]:
        vk, ids = self.pop_ids(s, g, k, q, "affected")
        a = self.arrays(ids, q, g, vk, k, policy)
        pp_b = pi_params(self.pool_resid(s, q, g, k, None))
        pp_c = pi_params(self.pool_resid(s, q, g, k, policy))
        out: Dict[str, Any] = {"n": len(ids), "piBase": {kk: vv for kk, vv in pp_b.items()},
                               "piCand": {kk: vv for kk, vv in pp_c.items()}}
        if not (pp_b["defined"] and pp_c["defined"]) or not ids:
            out["qualifies"] = False
            return out
        ones = np.ones(len(ids), bool)
        ib = interval_stats(a["meas"], a["base"], ones, pp_b["mu"], pp_b["sigma"])
        ic = interval_stats(a["meas"], a["cand"], a["ok"], pp_c["mu"], pp_c["sigma"])
        ib0 = interval_stats(a["meas"], a["base"], ones, 0.0, pp_b["sigma"])
        ic0 = interval_stats(a["meas"], a["cand"], a["ok"], 0.0, pp_c["sigma"])
        out.update({
            "qualifies": len(ids) >= CFG["criteria"]["C5"]["minRowsPerQuantity"],
            "coverageBase": ib["coverage"], "coverageCand": ic["coverage"],
            "wilsonBase": ib["wilson95"], "wilsonCand": ic["wilson95"],
            "coverageDiffCi95": coverage_diff_ci(ic["inside"], ib["inside"], a["cluster"]),
            "meanIsBase": ib["meanIntervalScore"], "meanIsCand": ic["meanIntervalScore"],
            "nIsCand": ic["nIntervalScore"], "nUnresolvedCand": ic["nUnresolved"],
            "uncentred": {"coverageBase": ib0["coverage"], "coverageCand": ic0["coverage"],
                          "meanIsBase": ib0["meanIntervalScore"], "meanIsCand": ic0["meanIntervalScore"]}})
        cov_ok = (ic["coverage"] >= ib["coverage"] - CFG["criteria"]["C5"]["coverageDrop"])
        is_ok = (ic["meanIntervalScore"] is not None and ib["meanIntervalScore"] is not None
                 and ic["meanIntervalScore"] <= IS_MARGIN * ib["meanIntervalScore"])
        out["coverageOk"], out["intervalScoreOk"] = bool(cov_ok), bool(is_ok)
        return out

    # ---- criteria for one (kernel, reading, arm)
    def criteria(self, k: str, g: Dict[str, Any], policy_of: Callable[[str], Optional[Tuple]]) -> Dict[str, Any]:
        sets = self.gsets[grid_key(g)][k]
        E, E_W, T = sets["E"], sets["E_W"], sets["T"]
        out: Dict[str, Any] = {"E": E, "E_W": E_W, "T": T}
        if sets["inconclusiveEarly"]:
            out["early"] = "INCONCLUSIVE"
        per: Dict[str, Any] = {}
        for s in VERDICT_SOURCES:
            per[s] = {}
            for q in Q_LIST:
                if MAN[s]["gate"][q]:
                    per[s][q] = {"P": self.source_metrics(s, g, k, q, policy_of(s)),
                                 "Pall": self.source_metrics(s, g, k, q, policy_of(s), "all")}
        out["perSource"] = per
        # C1
        c1_srcs = {s: per[s]["depth"]["P"].get("skill") for s in E}
        out["C1"] = {"evaluable": True, "pass": all((v is not None and v > 0) for v in c1_srcs.values()) if E else False,
                     "skills": c1_srcs}
        # C2
        pooled_d = pooled_skill(self.parts(T, g, k, "depth", policy_of)) if T else {"ciEvaluable": False}
        out["C2"] = {"evaluable": bool(pooled_d.get("ciEvaluable")),
                     "pass": bool(pooled_d.get("ci95") and pooled_d["ci95"][0] > 0), "pooled": pooled_d}
        # C3
        c3_per = {s: per[s]["width"]["P"].get("skill") for s in E_W}
        thr = CFG["criteria"]["C3"]["perSourceWidthSkillMin"]
        pooled_w = pooled_skill(self.parts(E_W, g, k, "width", policy_of)) if E_W else {"ciEvaluable": False}
        c3_eval = bool(E_W) and bool(pooled_w.get("ciEvaluable"))
        c3_pass = bool(E_W) and all((v is not None and v >= thr) for v in c3_per.values()) and bool(
            pooled_w.get("ci95") and pooled_w["ci95"][0] >= CFG["criteria"]["C3"]["pooledWidthSkillCiLowerMin"])
        out["C3"] = {"evaluable": c3_eval, "pass": c3_pass, "perSource": c3_per, "pooled": pooled_w}
        # C4
        c4: Dict[str, Any] = {}
        for ls in ("i", "ii"):
            if sets["c4"][ls]:
                base = self.regime_accuracy(ls, g, k, policy_of, arm_is_base=True)
                cand = self.regime_accuracy(ls, g, k, policy_of)
                c4[ls] = {"base": base, "cand": cand, "indexControl": self.index_control(ls, g, k),
                          "pass": bool(cand["accuracy"] >= base["accuracy"])}
        out["C4"] = {"evaluable": bool(c4), "pass": all(v["pass"] for v in c4.values()) if c4 else False, "sets": c4}
        # C5
        c5: Dict[str, Any] = {}
        qualifying_depth = 0
        for s in E:
            for q in Q_LIST:
                if q == "width" and s not in E_W:
                    continue
                ent = self.c5_entry(s, q, g, k, policy_of(s))
                c5.setdefault(s, {})[q] = ent
                if ent.get("qualifies") and q == "depth":
                    qualifying_depth += 1
        gated = [(s, q) for s, d in c5.items() for q, e in d.items() if e.get("qualifies")]
        out["C5"] = {"evaluable": qualifying_depth > 0,
                     "pass": all(c5[s][q]["coverageOk"] and c5[s][q]["intervalScoreOk"] for s, q in gated) if gated else False,
                     "entries": c5, "nGatedPairs": len(gated)}
        # C6
        unresolved, only_cand, total = [], 0, 0
        for s in VERDICT_SOURCES:
            for q in Q_LIST:
                vk, ids = self.pop_ids(s, g, k, q, "all")
                pol = policy_of(s)
                for i in ids:
                    total += 1
                    if not valid_res(self.res(pol, i, vk, k)):
                        unresolved.append([s, q, i])
        for r in self.s1["rows"]:
            if r["role"] != "verdict":
                continue
            vk = variant_key(r, g)
            if not valid_res(self.res(None, r["rowId"], vk, k)) and valid_res(self.res(policy_of(r["source"]), r["rowId"], vk, k)):
                only_cand += 1
        out["C6"] = {"evaluable": True, "pass": not unresolved, "nRowsChecked": total, "nUnresolved": len(unresolved),
                     "unresolved": unresolved[:50], "rowsResolvedOnlyByCandidate": only_cand}
        out["verdict"] = kernel_verdict(out)
        return out


def kernel_verdict(c: Dict[str, Any]) -> str:
    if c.get("early"):
        return "INCONCLUSIVE"
    for name in ("C1", "C2", "C3", "C4", "C5", "C6"):
        e = c[name]
        if e["evaluable"] and not e["pass"]:
            return "FAIL"
    for name in ("C2", "C3", "C4", "C5"):
        if not c[name]["evaluable"]:
            return "INCONCLUSIVE"
    return "PASS"


def overall_decision(verdicts: Dict[str, Dict[str, str]], invalid: bool) -> Dict[str, Any]:
    """verdicts[kernel][gridKey] -> PASS | FAIL | INCONCLUSIVE."""
    if invalid:
        return {"result": "INVALID", "reason": "parity or D4 failed: no verdict"}
    per_kernel = {}
    consistent = True
    for k, d in verdicts.items():
        vals = set(d.values())
        per_kernel[k] = sorted(vals)
        if len(vals) > 1:
            consistent = False
    if not consistent:
        return {"result": "INCONCLUSIVE", "reason": "rejected: unresolved input (a kernel verdict differs across the grid)",
                "perKernel": per_kernel}
    single = {k: v[0] for k, v in per_kernel.items()}
    vals = list(single.values())
    if all(v == "PASS" for v in vals):
        return {"result": "PASS", "reason": "all kernels PASS under every reading", "perKernel": single}
    if any(v == "FAIL" for v in vals):
        mixed = any(v == "PASS" for v in vals)
        return {"result": "FAIL (mixed)" if mixed else "FAIL",
                "reason": "at least one kernel FAILs, verdicts identical across the grid", "perKernel": single}
    return {"result": "INCONCLUSIVE", "reason": "eligibility or evaluability not met", "perKernel": single}


# ---------------------------------------------------------------------------------------------
# arm F (fitted H_s)
# ---------------------------------------------------------------------------------------------
def fit_hs(ev: Evaluator, k: str, g: Dict[str, Any], held_out: str) -> Dict[str, Any]:
    """Arm F: H_s on the grid minimising the equal-source-weight depth MAPE on P(k, g, j, depth) of the training
    sources (the other trainable-class sources; ghosh: all five). Ties go to the larger H_s."""
    train = [j for j in TRAINABLE if j != held_out]
    srcs = [j for j in train if ev.pop_ids(j, g, k, "depth", "affected")[1]]
    best, best_hs = None, None
    for hs in F_GRID:
        pol = law_policy(0.70, hs)
        errs = []
        for j in srcs:
            key = (k, grid_key(g), j, hs)
            if key not in ev._fcache:
                vk, ids = ev.pop_ids(j, g, k, "depth", "affected")
                c_err, _ = ev.errs(ev.arrays(ids, "depth", g, vk, k, pol))
                ev._fcache[key] = float(c_err.mean())
            errs.append(ev._fcache[key])
        loss = float(np.mean(errs)) if errs else float("inf")
        if best is None or loss < best - 1e-12:
            best, best_hs = loss, hs
        elif abs(loss - best) <= 1e-12:
            best_hs = hs  # grid ascends, so the tie goes to the larger H_s
    return {"H_s": best_hs, "loss": best, "trainSources": srcs}


# ---------------------------------------------------------------------------------------------
# diagnostics
# ---------------------------------------------------------------------------------------------
def d2_absorptance_shape() -> Dict[str, Any]:
    import lpbf_literature_datasets as L
    pts = [r for r in L.load_trapp_absorptivity()["rows"]
           if r["series"].startswith("316L-disc-v") and not (r["flag"] and "penetrated" in r["flag"])]
    p = ARM_LAW["A0"]
    cand_err, flat_err = [], []
    for r in pts:
        H = K.flat_enthalpy("316L Stainless Steel", r["power_W"], r["speed_mm_s"], 60.0, PREHEAT_C)
        a = K.absorptivity_law(H, 0.42, p[1], p[2], p[3])
        cand_err.append(abs(a - r["absorptivity"]))
        flat_err.append(abs(0.42 - r["absorptivity"]))
    return {"n": len(pts), "maeLaw": float(np.mean(cand_err)), "maeFlat": float(np.mean(flat_err)),
            "note": "digitized, context only; 316L disc series at 100/500/1500 mm/s, non-penetrated points"}


def dw_accuracy(rows: Sequence[Dict[str, Any]], pick: Callable[[Dict[str, Any]], Optional[Tuple]], g: Dict[str, Any]) -> Optional[float]:
    c = n = 0
    for r in rows:
        res = pick(r)
        dw = meas_dw(r, g)
        if dw is None:
            continue
        n += 1
        if valid_res(res):
            c += int(((res[1] / res[0]) >= DW_KEY) == (dw >= DW_KEY))
    return (c / n) if n else None


def diagnostics(ev: Evaluator, g0: Dict[str, Any], a0_all: Dict[str, Dict[Tuple, Tuple]]) -> Dict[str, Any]:
    p0 = ARM_LAW["A0"]
    out: Dict[str, Any] = {}
    cun = [r for r in ev.s1["rows"] if r["source"] == "cunningham-ti64-2019"]
    d1, d5 = {}, {}
    for k in KERNELS:
        for tag, pol in (("baseline", None), ("A0", p0)):
            got = [(r, ev.res(pol, r["rowId"], "base", k)) for r in cun]
            cont = [valid_res(res) and res[1] >= r["depth_published_um"] for r, res in got]
            d1[f"{k}:{tag}"] = {"n": len(cun), "share": float(np.mean(cont)) if cun else None}
            def acc(sub):
                c = 0
                for r, res in sub:
                    truth = r["cunninghamLabel"] == "keyhole"
                    if valid_res(res):
                        c += int(((res[1] / res[0]) >= DW_KEY) == truth)
                return (c / len(sub)) if sub else None
            d5[f"{k}:{tag}"] = {"all": acc(got), "nAll": len(got),
                                "nearBoundaryFalse": acc([(r, x) for r, x in got if not r["nearBoundary"]]),
                                "nNearBoundaryFalse": sum(1 for r, _ in got if not r["nearBoundary"])}
    out["D1"], out["D5"] = d1, d5
    out["D2"] = d2_absorptance_shape()
    vals = [res[3] for k in KERNELS for (kk, a), res in a0_all.items() if kk == k and res[3] is not None]
    out["D3"] = {"min": float(min(vals)), "max": float(max(vals)),
                 "insideEnvelope": bool(min(vals) >= ENVELOPE[0] - 1e-12 and max(vals) <= ENVELOPE[1] + 1e-12),
                 "n": len(vals), "envelope": list(ENVELOPE)}
    # D4: non-affected rows identical to baseline (every role, every kernel)
    bad = []
    for r in ev.s1["rows"]:
        for vk, v in r["variants"].items():
            if v["affected"]:
                continue
            for k in KERNELS:
                c = a0_all.get((k, args_of(r, vk)))
                b = tuple(ev.base[r["rowId"]][vk][k])
                if c is None or tuple(c[:3]) != b:
                    bad.append([r["rowId"], vk, k])
    out["D4"] = {"pass": not bad, "nViolations": len(bad), "violations": bad[:20]}
    # D6 Trapp
    tr = [r for r in ev.s1["rows"] if r["source"] == "trapp-316l-2017"]
    d6 = {}
    for k in KERNELS:
        ent = {"nRows": len(tr)}
        for which in ("all", "affected"):
            sel = [r for r in tr if which == "all" or r["variants"]["base"]["affected"]]
            if not sel:
                continue
            for q in Q_LIST:
                meas = np.array([meas_value(r, q, g0) for r in sel], float)
                rb = [tuple(ev.base[r["rowId"]]["base"][k]) for r in sel]
                rc = [ev.res(p0, r["rowId"], "base", k) for r in sel]
                ok = np.array([valid_res(x) for x in rc], bool)
                idx = 1 if q == "depth" else 0
                pb = np.array([x[idx] if valid_res(x) else np.nan for x in rb], float)
                pc = np.array([x[idx] if valid_res(x) else np.nan for x in rc], float)
                b_err = np.abs(np.nan_to_num(pb, nan=0.0) - meas) / meas
                c_err = np.where(ok, np.abs(np.nan_to_num(pc, nan=0.0) - meas) / meas, 1.0)
                cl = np.array([r["variants"]["base"]["cluster"] for r in sel])
                ent[f"{which}:{q}"] = skill_stats(c_err, b_err, cl)
            ent[f"{which}:dwAccuracyBase"] = dw_accuracy(sel, lambda r: tuple(ev.base[r["rowId"]]["base"][k]), g0)
            ent[f"{which}:dwAccuracyA0"] = dw_accuracy(sel, lambda r: ev.res(p0, r["rowId"], "base", k), g0)
        d6[k] = ent
    out["D6"] = d6
    # D7 ungated widths (primary reading)
    d7 = {}
    ungated = [s for s in KU_SOURCES + ["totis-ti64-2021"] if not MAN[s]["gate"]["width"]]
    for k in KERNELS:
        d7[k] = {}
        for s in ungated:
            vk = source_variant_key(s, g0)
            sel = [r for r in ev.s1["rows"] if r["source"] == s and r["inputValid"]["width"]
                   and r["variants"][vk]["affected"] and valid_res(ev.res(None, r["rowId"], vk, k))]
            if not sel:
                continue
            meas = np.array([r["width_um"] for r in sel], float)
            pb = np.array([ev.base[r["rowId"]][vk][k][0] for r in sel], float)
            rc = [ev.res(p0, r["rowId"], vk, k) for r in sel]
            ok = np.array([valid_res(x) for x in rc], bool)
            pc = np.array([x[0] if valid_res(x) else np.nan for x in rc], float)
            b_err = np.abs(pb - meas) / meas
            c_err = np.where(ok, np.abs(np.nan_to_num(pc, nan=0.0) - meas) / meas, 1.0)
            cl = np.array([r["variants"][vk]["cluster"] for r in sel])
            ent = skill_stats(c_err, b_err, cl)
            ent["dwAccuracyBase"] = dw_accuracy(sel, lambda r: tuple(ev.base[r["rowId"]][vk][k]), g0)
            ent["dwAccuracyA0"] = dw_accuracy(sel, lambda r: ev.res(p0, r["rowId"], vk, k), g0)
            d7[k][s] = ent
    out["D7"] = d7
    # sentinels: MAPE only
    sent = {}
    for k in KERNELS:
        for s in sorted({r["source"] for r in ev.s1["rows"] if r["role"] == "sentinel"}):
            sel = [r for r in ev.s1["rows"] if r["source"] == s and r["inputValid"]["width"] and r["inputValid"]["depth"]]
            for q in Q_LIST:
                meas = np.array([r[f"{q}_um"] if q == "width" else r["depth_published_um"] for r in sel], float)
                idx = 1 if q == "depth" else 0
                pb = np.array([ev.base[r["rowId"]]["base"][k][idx] for r in sel], float)
                rc = [ev.res(p0, r["rowId"], "base", k) for r in sel]
                pc = np.array([x[idx] if valid_res(x) else np.nan for x in rc], float)
                aff = np.array([r["variants"]["base"]["affected"] for r in sel], bool)
                def mape(p, m):
                    return float(np.mean(np.abs(p - m) / m)) if m.size else None
                sent[f"{k}:{s}:{q}"] = {"n": len(sel), "nAffected": int(aff.sum()), "mapeBase": mape(pb, meas),
                                        "mapeA0": mape(np.nan_to_num(pc, nan=0.0), meas),
                                        "mapeBaseAffected": mape(pb[aff], meas[aff]) if aff.any() else None,
                                        "mapeA0Affected": mape(np.nan_to_num(pc[aff], nan=0.0), meas[aff]) if aff.any() else None}
    out["sentinels"] = sent
    return out


# ---------------------------------------------------------------------------------------------
# stage 3
# ---------------------------------------------------------------------------------------------
def candidate_task_sets(stage1: Dict[str, Any], arms: Sequence[str] = ARMS) -> Dict[str, List[Tuple]]:
    rows = stage1["rows"]
    verdict = [r for r in rows if r["role"] == "verdict"]
    sets: Dict[str, List[Tuple]] = {}
    sets["A0"] = unique_tasks(rows, ARM_LAW["A0"])  # every row, to verify D4
    for arm in ("S1", "S2", "S3", "S4", "K"):
        if arm in arms:
            sets[arm] = unique_tasks(verdict, ARM_LAW[arm], only_affected=True)
    gan = []
    seen = set()
    for r in verdict:
        pol = gan_policy(r["material"])
        if pol is None:
            continue
        for vk in r["variants"]:
            for k in KERNELS:
                key = (pol, k, args_of(r, vk))
                if key not in seen:
                    seen.add(key)
                    gan.append(key)
    if "G" in arms:
        sets["G"] = gan
    f = []
    seenf = set()
    for hs in F_GRID:
        pol = law_policy(0.70, hs)
        if pol in ARM_LAW.values():
            continue  # A0, S3, S4 already have their own task sets
        for t in unique_tasks(verdict, pol, only_affected=True):
            if (t[0], t[1], t[2]) not in seenf:
                seenf.add((t[0], t[1], t[2]))
                f.append(t)
    if "F" in arms:
        sets["F"] = f
    return sets


def run_candidates(stage1: Dict[str, Any], jobs: int, arms: Sequence[str] = ARMS) -> Dict[str, Dict[Tuple, Tuple]]:
    sets = candidate_task_sets(stage1, arms)
    cache: Dict[str, Dict[Tuple, Tuple]] = {}
    for name, tasks in sets.items():
        res = pmap(_solve, tasks, jobs)
        for (pol, k, a), r in zip(tasks, res):
            cache.setdefault(pkey(pol), {})[(k, a)] = r
    return cache


def make_policy_of(arm: str, ev: Evaluator, k: str, g: Dict[str, Any], fits: Dict[str, Any]) -> Callable[[str], Optional[Tuple]]:
    if arm in ARM_LAW:
        p = ARM_LAW[arm]
        return lambda s: p
    if arm == "G":
        return lambda s: gan_policy(SOURCE_MATERIAL[s])
    if arm == "F":
        def pol(s: str) -> Optional[Tuple]:
            key = (k, grid_key(g), s)
            if key not in fits:
                fits[key] = fit_hs(ev, k, g, s)
            return law_policy(0.70, fits[key]["H_s"])
        return pol
    raise ValueError(arm)


def run_stage3(stage1: Dict[str, Any], stage2: Dict[str, Any], jobs: int,
               cand: Optional[Dict[str, Dict[Tuple, Tuple]]] = None, arms: Sequence[str] = ARMS) -> Dict[str, Any]:
    if cand is None:
        cand = run_candidates(stage1, jobs, arms)
    ev = Evaluator(stage1, stage2, cand)
    grid = stage1["grid"]
    a0_all = cand[pkey(ARM_LAW["A0"])]
    fits: Dict[Tuple, Any] = {}
    results: Dict[str, Any] = {}
    for arm in arms:
        results[arm] = {}
        for g in grid:
            gk = grid_key(g)
            results[arm][gk] = {}
            for k in KERNELS:
                pof = make_policy_of(arm, ev, k, g, fits)
                results[arm][gk][k] = ev.criteria(k, g, pof)
    g0 = {"kuBeam_um": PRIMARY["kuBeam_um"], "ghoshSpot_um": PRIMARY["ghoshSpot_um"], "datum": PRIMARY["datum"],
          "lanePower": PRIMARY["lanePower"]}
    diag = diagnostics(ev, g0, a0_all)
    verdicts = {k: {grid_key(g): results["A0"][grid_key(g)][k]["verdict"] for g in grid} for k in KERNELS}
    invalid = (stage2["parity"]["ok"] is False) or (not diag["D4"]["pass"])
    decision = overall_decision(verdicts, invalid)
    robustness = None
    if decision["result"] == "PASS":
        failing = []
        for arm in [a for a in CFG["robustnessArms"] if a in results]:
            for g in grid:
                for k in KERNELS:
                    r = results[arm][grid_key(g)][k]
                    for c in CFG["robustnessCriteria"]:
                        e = r[c]
                        if e["evaluable"] and not e["pass"]:
                            failing.append([arm, grid_key(g), k, c])
        names = sorted({f[0] for f in failing})
        robustness = {"label": "PASS (robust)" if not failing else "PASS (endpoint-sensitive)", "failingArms": names,
                      "failures": failing[:40]}
        decision["robustness"] = robustness
    # arm summary on the stored rule (reported; only A0 can produce PASS)
    arm_rule = {arm: {k: {grid_key(g): results[arm][grid_key(g)][k]["verdict"] for g in grid} for k in KERNELS}
                for arm in arms}
    hypothesis = None
    if "F" in arms and decision["result"] != "PASS":
        f_pass = all(v == "PASS" for k in KERNELS for v in arm_rule["F"][k].values())
        if f_pass:
            hypothesis = "arm F passes the rule while A0 does not: record as a hypothesis for a NEW pre-registration, not a PASS"
    return {"results": results, "diagnostics": diag, "kernelVerdicts": verdicts, "decision": decision,
            "armRule": arm_rule, "fFits": {"|".join(map(str, k)): v for k, v in fits.items()},
            "fHypothesis": hypothesis}


# ---------------------------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------------------------
def _ci(ci: Any) -> str:
    return "n/a" if not ci else f"[{ci[0]:.3f}, {ci[1]:.3f}]"


def _p(x: Any, d: int = 3) -> str:
    return "n/a" if x is None else (f"{x:.{d}f}" if isinstance(x, (int, float)) else str(x))


def render_markdown(doc: Dict[str, Any]) -> str:
    dec = doc["decision"]
    L = [f"# Regime-dependent absorptivity: results ({doc['date']})", "",
         f"**{EVIDENCE}.** Screening evaluation, not validation. experimentalValidation=false, "
         "validationStatus=unvalidated, productionReady=false.", "",
         f"## Decision: {dec['result']}", "", f"Reason: {dec['reason']}.", ""]
    if "robustness" in dec and dec["robustness"]:
        L += [f"Robustness label: {dec['robustness']['label']}.", ""]
    if doc.get("fHypothesis"):
        L += [doc["fHypothesis"], ""]
    L += ["Computed mechanically from the pre-registered rule "
          f"(`{CFG['preregistration']['doc']}`, Amendment 1 commit `{CFG['preregistration']['commit'][:8]}`). "
          "Only arm A0 can produce PASS; no result text claims the law improves depth on every source.", ""]
    L += ["## Kernel verdict by reading (arm A0)", "", "| kernel | " + " | ".join(doc["gridKeys"]) + " |",
          "|---|" + "---|" * len(doc["gridKeys"])]
    for k in KERNELS:
        L.append(f"| {k} | " + " | ".join(doc["kernelVerdicts"][k][gk] for gk in doc["gridKeys"]) + " |")
    L.append("")
    gk0 = doc["primaryGridKey"]
    res = doc["results"]["A0"][gk0]
    L += [f"## Criteria, primary reading `{gk0}`", "", "| kernel | E | T | C1 | C2 | C3 | C4 | C5 | C6 | verdict |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for k in KERNELS:
        r = res[k]
        def c(n):
            e = r.get(n)
            return "n/a" if not e else (("pass" if e["pass"] else "FAIL") if e["evaluable"] else "not evaluable")
        L.append(f"| {k} | {len(r['E'])} | {len(r['T'])} | {c('C1')} | {c('C2')} | {c('C3')} | {c('C4')} | {c('C5')} | {c('C6')} | {r['verdict']} |")
    L += ["", f"## Depth and width, arm A0 against the baseline, primary reading `{gk0}`", "",
          "| kernel | source | quantity | n (P) | clusters | MAPE base | MAPE A0 | skill | CI95 | bias base | bias A0 |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for k in KERNELS:
        for s, d in res[k]["perSource"].items():
            for q, e in d.items():
                m = e["P"]
                if not m.get("n"):
                    continue
                ci = m["ci95"]
                L.append(f"| {k} | {s} | {q} | {m['n']} | {m['nClusters']} | {_p(m['mapeBase'])} | {_p(m['mapeCand'])} | "
                         f"{_p(m['skill'])} | {('[' + _p(ci[0]) + ', ' + _p(ci[1]) + ']') if ci else 'n/a'} | "
                         f"{_p(m['biasBase'])} | {_p(m['biasCand'])} |")
    L += ["", "## Pooled significance endpoints (C2 depth, C3 width), arm A0, primary reading", ""]
    for k in KERNELS:
        p2, p3 = res[k]["C2"]["pooled"], res[k]["C3"]["pooled"]
        L.append(f"- {k}: pooled depth skill {_p(p2.get('skill'))} CI95 {_ci(p2.get('ci95'))}; pooled width skill {_p(p3.get('skill'))} CI95 {_ci(p3.get('ci95'))}")
    L += ["", "## Arms against the same rule (reported; only A0 can produce PASS)", "",
          "| arm | " + " | ".join(KERNELS) + " |", "|---|" + "---|" * len(KERNELS)]
    for arm, d in doc["armRule"].items():
        L.append(f"| {arm} | " + " | ".join(
            ",".join(sorted(set(d[k].values()))) for k in KERNELS) + " |")
    dg = doc["diagnostics"]
    L += ["", "## Diagnostics (not in the verdict)", "",
          f"- D2 absorptance shape (Trapp 316L discs, digitized): n={dg['D2']['n']}, MAE law {_p(dg['D2']['maeLaw'])}, MAE flat 0.42 {_p(dg['D2']['maeFlat'])}",
          f"- D3 envelope: A(H) in [{_p(dg['D3']['min'])}, {_p(dg['D3']['max'])}], inside [0.25, 0.80]: {dg['D3']['insideEnvelope']}",
          f"- D4 conduction identity: {'pass' if dg['D4']['pass'] else 'FAIL'} ({dg['D4']['nViolations']} violations)",
          f"- Parity (stage 2): {_parity_text(doc['parity'])}",
          f"- D1 containment, D5 Cunningham regime agreement, D6 Trapp geometry, D7 ungated widths and the catalog sentinels are in the JSON record.", ""]
    for key, v in dg["D1"].items():
        L.append(f"  - D1 {key}: {_p(v['share'])} of {v['n']}")
    for key, v in dg["D5"].items():
        L.append(f"  - D5 {key}: accuracy {_p(v['all'])} (n={v['nAll']}), non-boundary {_p(v['nearBoundaryFalse'])} (n={v['nNearBoundaryFalse']})")
    L += ["", "## Provenance", "",
          f"- config sha256 `{doc['configSha256']}`; pre-registration LF sha256 `{CFG['preregistration']['sha256Lf']}`",
          f"- repo commit `{doc['repoCommit']}`; frozen implementation fingerprint `{doc['fingerprint']}`",
          f"- stage-1 record sha256 `{doc['stage1Sha256']}`; stage-2 record sha256 `{doc['stage2Sha256']}`",
          f"- bootstrap B={BOOT_B}, seed {BOOT_SEED}; lane axis active: {doc['laneAxisActive']}; grid readings: {len(doc['gridKeys'])}",
          "- dataset table sha256s: " + "; ".join(f"{s} `{v.get('tableSha256')}`" for s, v in sorted(doc['tableProvenance'].items()) if v.get('tableSha256')),
          "", "## What this does not show", "",
          "- It is a screening comparison on published single tracks, not validation. No evidence label is promoted.",
          "- Totis width is reported only (the open text of Vaglio 2020 does not print the W definition); KU Leuven width is reported only.",
          "- Inconel 718 and AlSi10Mg have no eligible held-out source; this evaluation says nothing about them.",
          "- Default kernels only: interaction with the calibration layer is out of scope.", ""]
    return "\n".join(L)


# ---------------------------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------------------------
def committed(path: Path) -> bool:
    rel = str(path.resolve().relative_to(REPO_ROOT)).replace("\\", "/")
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", rel], cwd=str(REPO_ROOT), capture_output=True)
    if tracked.returncode != 0:
        return False
    return git("status", "--porcelain", "--", rel) == ""


def paths(date: str, out_dir: Path) -> Dict[str, Path]:
    return {"stage1": out_dir / f"RESULT_regime_absorptivity_stage1_{date}.json",
            "stage2": out_dir / f"RESULT_regime_absorptivity_stage2_{date}.json",
            "json": out_dir / f"RESULTS_regime_absorptivity_{date}.json",
            "md": out_dir / f"RESULTS_regime_absorptivity_{date}.md"}


def current_fingerprint() -> str:
    import lpbf_simulation
    return lpbf_simulation.implementation_fingerprint()


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--stage", choices=("inputs", "baseline", "run", "render"), required=True)
    ap.add_argument("--date", default="2026-10-09")
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--out-dir", default=str(REPO_ROOT / "docs" / "research"))
    args = ap.parse_args(argv)
    out_dir = Path(args.out_dir)
    P = paths(args.date, out_dir)
    if args.stage == "inputs":
        raws, prov = load_raw_rows()
        s1 = build_stage1(raws, prov, args.date)
        P["stage1"].write_text(dump_json(s1), encoding="utf-8", newline="\n")
        print(f"stage 1 written: {P['stage1']} rows={len(s1['rows'])} laneAxisActive={s1['laneAxisActive']} "
              f"grid={len(s1['grid'])}")
        return 0
    if args.stage == "render":  # re-render the markdown from the written JSON record (no recomputation)
        doc = json.loads(P["json"].read_bytes())
        P["md"].write_text(render_markdown(doc), encoding="utf-8", newline="\n")
        print(f"markdown re-rendered: {P['md']}")
        return 0
    fp = current_fingerprint()
    if fp != C.FROZEN_FINGERPRINT:
        print(f"STOP: implementation fingerprint {fp} differs from the pin {C.FROZEN_FINGERPRINT}", file=sys.stderr)
        return 2
    s1_bytes = P["stage1"].read_bytes()
    s1 = json.loads(s1_bytes)
    if args.stage == "baseline":
        if not committed(P["stage1"]):
            print("STOP: the stage-1 record must be committed before stage 2", file=sys.stderr)
            return 2
        s2 = build_stage2(s1, lf_sha(s1_bytes), args.jobs, args.date, fp)
        P["stage2"].write_text(dump_json(s2), encoding="utf-8", newline="\n")
        print(f"stage 2 written: {P['stage2']} parity {_parity_text(s2['parity'])}")
        return 3 if s2["parity"]["ok"] is False else 0
    # stage 3
    for key in ("stage1", "stage2"):
        if not committed(P[key]):
            print(f"STOP: the {key} record must be committed before the candidate runs", file=sys.stderr)
            return 2
    s2_bytes = P["stage2"].read_bytes()
    s2 = json.loads(s2_bytes)
    if s2["stage1Sha256"] != lf_sha(s1_bytes):
        print("STOP: stage-2 record does not match the stage-1 record hash", file=sys.stderr)
        return 2
    if s2["configSha256"] != C.config_sha256() or s1["configSha256"] != C.config_sha256():
        print("STOP: config hash differs from the one in the stage records", file=sys.stderr)
        return 2
    out = run_stage3(s1, s2, args.jobs)
    gks = [grid_key(g) for g in s1["grid"]]
    doc = {"schema": RESULT_SCHEMA, "date": args.date, "evidence": EVIDENCE, "labels": CFG["labels"],
           "configSha256": C.config_sha256(), "preregistrationCommit": CFG["preregistration"]["commit"],
           "preregistrationSha256Lf": CFG["preregistration"]["sha256Lf"], "repoCommit": git("rev-parse", "HEAD"),
           "fingerprint": fp, "stage1Sha256": lf_sha(s1_bytes), "stage2Sha256": lf_sha(s2_bytes),
           "tableProvenance": s1["tableProvenance"], "bootstrap": {"B": BOOT_B, "seed": BOOT_SEED},
           "laneAxisActive": s1["laneAxisActive"], "gridKeys": gks, "primaryGridKey": gks[0],
           "parity": s2["parity"], **out}
    P["json"].write_text(dump_json(doc), encoding="utf-8", newline="\n")
    P["md"].write_text(render_markdown(jsonable(doc)), encoding="utf-8", newline="\n")
    print(f"stage 3 written: {P['json']}  decision={out['decision']['result']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
