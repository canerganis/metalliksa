#!/usr/bin/env python3
"""Comparison of the LPBF screening kernels against two published single-track datasets.

COMPARISON, NOT VALIDATION: the Rosenthal, Eagar-Tsai and Goldak screening kernels of
``calculate_meltpool_physics`` are run on every row of the Hofmann 2026 316L table (677 tracks) and
the Totis/Vaglio 2021 Ti-6Al-4V table (80 tracks) and compared with the measured width and depth.
The material laws are estimated, absorptivity is the repo's assumed constant, and a failing
comparison is reported as it is -- nothing is fitted. The absorptivity sweep is a SENSITIVITY
bracket, never a calibrated value.

Usage (from python/, locked interpreter, PYTHONDONTWRITEBYTECODE=1):
    python -B tools/lpbf_dataset_comparison.py --out ../docs/LPBF_DATASET_COMPARISON_2026-10-05.json
    python -B tools/lpbf_dataset_comparison.py --quick --out <json>        # first 40 rows of each dataset
Options: --jobs N (worker processes, default 6), --ref-budget-s S (reference-transient total budget,
default 900), --skip-reference, --reuse-reference <record.json> (copy that record's referenceTransient block
instead of re-running the wall-clock-budgeted transient), --allow-raytracer (request the GPU powder ray
tracer explicitly, absorption_model="powder-raytrace"; default flat-plate), --view-out <path> (slim view record, default <out>.view.json), --include-wave2 (add the
2026-10-06 datasets: KU Leuven 316L/Ti-6Al-4V condition means and Lane 2020 IN625 tracks through the same kernels,
plus the NIST AMB2022-03 thermal and Simonds 2018 absorptance tables as reference targets whose model comparison
is recorded as unavailable). The companion .md is written next to the json.
    python -B tools/lpbf_dataset_comparison.py --include-wave2 --generated-at 2026-10-06 \
        --reuse-reference ../docs/LPBF_DATASET_COMPARISON_2026-10-05.json --out ../docs/LPBF_DATASET_COMPARISON_2026-10-06.json
Nothing is written under python/golden.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import math
import multiprocessing
import random
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SCHEMA = "lpbf-dataset-comparison-1"
KERNELS = ("rosenthal", "eagar-tsai", "goldak")
ABSORPTIVITY_VALUES = (0.30, 0.40, 0.50, 0.60)
DEFAULT_HATCH_UM = 100.0
NOMINAL_LAYER_FOR_BARE_UM = 30.0
GENERATED_AT_DEFAULT = "2026-10-05"
HONESTY_STATEMENT = ("comparison, not validation; screening kernels; estimated material laws; absorptivity "
                     "assumed (not measured); published single-track measurements, no replicate or "
                     "uncertainty model; a failing comparison is reported, not fitted away")
HEADER_MD = ("**Comparison of screening kernels against published single-track measurements; not experimental "
             "validation; estimated material laws; absorptivity assumed.**")
# Declared depth-datum sensitivity (zero served-value drift): the measured depth of these sources is taken from the
# substrate surface, a kernel depth from the free (powder) surface. The column is reported ALONGSIDE the served
# prediction and never replaces it.
PACKING_PHI = 0.60  # Trapp et al. 2017 (estimated packing density of about 60 %)
DEPTH_DATUM_SUBSTRATE_DATASETS = {
    "hofmann-316l-2026": "substrate surface (Hofmann et al. 2026, Fig. 2)",
    "totis-ti64-2021": "printed-base top surface under the powder layer (Vaglio et al. 2020, Fig. 1/2b)",
}
DEPTH_DATUM_WORDING = "geometric assumption (h_surface = φ·t); powder denudation not modelled"
REF_SOURCE_PENETRATION_UM = 40.0
REF_MESH_UM = 20.0
REF_TRACK_LENGTH_UM = 600.0
REF_POWER_LIMIT_W = 100.0
CI_REPLICATES = 1000
CI_SEED = 0
RAYTRACER_MODULE = "powder_bed_raytracer"
# Kept for older callers; since the 2026-10-06 tier-2 bump the solver never prints this message.
FALLBACK_WARNING_TEXT = "GPU Powder Bed Ray Tracing failed"
PYTHON_DIR = Path(__file__).resolve().parent.parent
RAYTRACER_STUB_NOTE = "reviewer stub: Eagar-Tsai hofmann-0001 171.0/119.6 -> 209.2/143.6 um at effective 0.65"


def pin_flat_plate(allow_raytracer: bool = False) -> None:
    """Defence in depth for the flat-plate path.

    Since the 2026-10-06 tier-2 bump calculate_meltpool_physics uses the flat-plate absorptivity unless
    absorption_model="powder-raytrace" is passed (this harness passes it only with --allow-raytracer). A None
    entry in sys.modules additionally makes any powder_bed_raytracer import fail loudly.
    """
    if not allow_raytracer:
        sys.modules[RAYTRACER_MODULE] = None


# ---------------------------------------------------------------------------------------------
# pure statistics (no solver)
# ---------------------------------------------------------------------------------------------
def depth_datum_correction_um(dataset: Any, layer_um: Optional[float]) -> Optional[Dict[str, Any]]:
    """Declared sensitivity column `depthDatumCorrection_um` = phi * t for powder-layer rows of sources whose depth
    datum is the substrate (None for bare rows and for every other source). A kernel depth from the powder surface
    minus this value is the sensitivity reading; the served depth is never changed."""
    datum = DEPTH_DATUM_SUBSTRATE_DATASETS.get(str(dataset))
    if datum is None or not layer_um or layer_um <= 0:
        return None
    return {"depthDatumCorrection_um": round(PACKING_PHI * float(layer_um), 3), "phi": PACKING_PHI,
            "datum": datum, "basis": DEPTH_DATUM_WORDING, "servedDepthUnchanged": True}


def _stats(pairs: Sequence[tuple]) -> Optional[Dict[str, float]]:
    """pairs of (predicted, measured). Returns None when empty."""
    if not pairs:
        return None
    rel = [(p - m) / m for p, m in pairs]
    n = len(pairs)
    return {
        "bias_pct": 100.0 * sum(rel) / n,
        "mape_pct": 100.0 * sum(abs(r) for r in rel) / n,
        "rmse_um": math.sqrt(sum((p - m) ** 2 for p, m in pairs) / n),
        "within30pct": sum(1 for r in rel if abs(r) <= 0.30) / n,
        "withinFactor2": sum(1 for p, m in pairs if 0.5 <= p / m <= 2.0) / n,
    }


def _set_key(row: Dict[str, Any]) -> tuple:
    """Parameter-set identity: replicates of one (dataset, power, speed, beam diameter, layer) share it."""
    i = row.get("inputs")
    if not i:
        return (row["rowId"],)
    return (row.get("dataset"), i["power_W"], i["speed_mm_s"], i["beamDiameter_um"], i["layer_um"])


def _percentile(sorted_vals: Sequence[float], q: float) -> float:
    """Linear-interpolation percentile (q in 0..100) of an ascending list."""
    pos = (len(sorted_vals) - 1) * q / 100.0
    lo = int(math.floor(pos))
    hi = min(lo + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (pos - lo)


def _cluster_bootstrap(items: Sequence[tuple], replicates: int = CI_REPLICATES, seed: int = CI_SEED) -> Dict[str, Any]:
    """Cluster bootstrap by parameter set. items = [(set_key, (pred_w, meas_w), (pred_d, meas_d)), ...].

    Resamples the distinct parameter sets with replacement (same draws for width and depth), `replicates`
    times with random.Random(seed); returns the 2.5/97.5 percentiles of bias_pct and mape_pct per quantity.
    """
    clusters: Dict[tuple, list] = {}
    for key, wp, dp in items:
        c = clusters.setdefault(key, [0, 0.0, 0.0, 0.0, 0.0])  # n, w_rel, w_abs, d_rel, d_abs
        wr, dr = (wp[0] - wp[1]) / wp[1], (dp[0] - dp[1]) / dp[1]
        c[0] += 1
        c[1] += wr
        c[2] += abs(wr)
        c[3] += dr
        c[4] += abs(dr)
    cl = list(clusters.values())
    k = len(cl)
    rng = random.Random(seed)
    idx = range(k)
    b = {"width": ([], []), "depth": ([], [])}
    for _ in range(replicates):
        n = wr = wa = dr = da = 0.0
        for i in rng.choices(idx, k=k):
            c = cl[i]
            n += c[0]
            wr += c[1]
            wa += c[2]
            dr += c[3]
            da += c[4]
        b["width"][0].append(100.0 * wr / n)
        b["width"][1].append(100.0 * wa / n)
        b["depth"][0].append(100.0 * dr / n)
        b["depth"][1].append(100.0 * da / n)
    out: Dict[str, Any] = {"n_parameterSets": k}
    for name, (bias, mape) in b.items():
        bias.sort()
        mape.sort()
        out[name] = {"bias_pct_ci95": [_percentile(bias, 2.5), _percentile(bias, 97.5)],
                     "mape_pct_ci95": [_percentile(mape, 2.5), _percentile(mape, 97.5)]}
    return out


def _cell(items: Sequence[tuple], excluded: int, with_ci: bool) -> Dict[str, Any]:
    cell = {"n": len(items), "nExcluded": excluded,
            "width": _stats([x[1] for x in items]), "depth": _stats([x[2] for x in items])}
    if with_ci and items:
        ci = _cluster_bootstrap(items)
        for name in ("width", "depth"):
            cell[name].update(ci[name])
            cell[name]["n_parameterSets"] = ci["n_parameterSets"]
    return cell


def _item(row: Dict[str, Any], kernel: str) -> tuple:
    pred = row["predictions"][kernel]
    return (_set_key(row), (pred["width_um"], row["measured"]["width_um"]),
            (pred["depth_um"], row["measured"]["depth_um"]))


def summarize(rows: Sequence[Dict[str, Any]], kernels: Sequence[str] = KERNELS,
              with_ci: bool = False) -> Dict[str, Any]:
    """{kernel: {regime|'all': {n, nExcluded, width: {...}, depth: {...}}}} from comparison rows.

    A row is used for statistics only if predictions[kernel].included is true; excluded rows are counted.
    Rows need regime.label, measured.width_um/depth_um and predictions[kernel].{width_um,depth_um,included}.
    with_ci adds cluster-bootstrap 95 % intervals by parameter set (needs row.inputs for the set key).
    """
    out: Dict[str, Any] = {}
    for k in kernels:
        per: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            for label in (r["regime"]["label"], "all"):
                slot = per.setdefault(label, {"items": [], "excl": 0})
                if not r["predictions"][k].get("included"):
                    slot["excl"] += 1
                    continue
                slot["items"].append(_item(r, k))
        out[k] = {label: _cell(s["items"], s["excl"], with_ci) for label, s in sorted(per.items())}
    return out


def add_common_cells(summary: Dict[str, Any], rows: Sequence[Dict[str, Any]],
                     kernels: Sequence[str] = KERNELS, with_ci: bool = False) -> None:
    """summary[kernel]['common'] = statistics over the rows where ALL kernels are included (like-for-like)."""
    common = [r for r in rows if all(r["predictions"][k].get("included") for k in kernels)]
    for k in kernels:
        summary[k]["common"] = _cell([_item(r, k) for r in common], len(rows) - len(common), with_ci)


def sensitivity_mape(rows: Sequence[Dict[str, Any]], by_value: Dict[float, Dict[str, Dict[str, Dict[str, Any]]]],
                     kernels: Sequence[str] = KERNELS) -> Dict[str, Any]:
    """by_value[a][rowId][kernel] -> prediction dict. Returns width/depth MAPE per absorptivity value."""
    out: Dict[str, Any] = {"values": sorted(by_value)}
    for k in kernels:
        wm, dm, nn = {}, {}, {}
        for a in sorted(by_value):
            wp, dp = [], []
            for r in rows:
                p = by_value[a][r["rowId"]][k]
                if p.get("included"):
                    wp.append((p["width_um"], r["measured"]["width_um"]))
                    dp.append((p["depth_um"], r["measured"]["depth_um"]))
            sw, sd = _stats(wp), _stats(dp)
            key = f"{a:.2f}"
            wm[key] = None if sw is None else sw["mape_pct"]
            dm[key] = None if sd is None else sd["mape_pct"]
            nn[key] = len(wp)
        out[k] = {"width_mape_pct_by_value": wm, "depth_mape_pct_by_value": dm, "n_included_by_value": nn}
    return out


# ---------------------------------------------------------------------------------------------
# solver calls
# ---------------------------------------------------------------------------------------------
def _predict(task: Dict[str, Any]) -> Dict[str, Any]:
    """Worker: one row, one kernel. Solver stdout is captured; calls whose result reports
    processParameters.absorptionModel == "flat-plate" are counted (returned as `_flatPlateCalls`, popped by
    the caller, never stored in the prediction)."""
    pin_flat_plate(bool(task.get("allowRaytracer")))
    absorption_model = "powder-raytrace" if task.get("allowRaytracer") else "flat-plate"
    from lpbf_thermal_solver import calculate_meltpool_physics
    row, kernel, overrides = task["row"], task["kernel"], task.get("overrides")
    layer = row["layer_um"] if row["layer_um"] and row["layer_um"] > 0 else NOMINAL_LAYER_FOR_BARE_UM
    captured = io.StringIO()
    try:
        with contextlib.redirect_stdout(captured):
            res = calculate_meltpool_physics(
                row["material"], row["power_W"], row["speed_mm_s"], row["beamDiameter_um"],
                row["preheat_C"], layer, row["hatch_um"] or DEFAULT_HATCH_UM,
                heat_source=kernel, prop_overrides=overrides, absorption_model=absorption_model)
        g = res["meltPoolGeometry"]
        status = g.get("extentStatus")
        return {"width_um": round(float(g["width_um"]), 3), "depth_um": round(float(g["depth_um"]), 3),
                "length_um": round(float(g["length_um"]), 3), "extentStatus": status,
                "extentNote": g.get("extentNote"), "included": status == "computed",
                "_flatPlateCalls": int(res["processParameters"].get("absorptionModel") == "flat-plate")}
    except Exception as exc:  # recorded as data
        return {"width_um": None, "depth_um": None, "length_um": None,
                "extentStatus": f"error: {type(exc).__name__}", "extentNote": str(exc)[:300], "included": False,
                "_flatPlateCalls": 0}


def _map(tasks: List[Dict[str, Any]], jobs: int) -> List[Dict[str, Any]]:
    if jobs <= 1:
        return [_predict(t) for t in tasks]
    ctx = multiprocessing.get_context("spawn")
    with ctx.Pool(jobs) as pool:
        return pool.map(_predict, tasks, chunksize=8)  # order preserved -> deterministic


def _ref_worker(raw: Dict[str, Any], result_path: str) -> None:
    import lpbf_simulation

    class _Q:  # results go through a file: robust on Windows spawn (no inherited queue handles)
        @staticmethod
        def put(obj):
            Path(result_path).write_text(json.dumps(obj), encoding="utf-8")

    q = _Q()
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            res = lpbf_simulation.run(raw)
        m = res["metrics"]
        q.put({"status": "completed", "width_um": m["width_um"], "depth_um": m["depth_um"],
               "length_um": m["length_um"], "peakTemperature_K": m["peakTemperature_K"]})
    except ValueError as exc:
        msg = str(exc)
        q.put({"status": "boiling-stop" if "boiling" in msg.lower() else "other-error", "message": msg[:400]})
    except Exception as exc:
        q.put({"status": "other-error", "message": f"{type(exc).__name__}: {exc}"[:400]})


def run_reference_transient(rows: Sequence[Dict[str, Any]], budget_s: float, per_case_s: float = 240.0) -> Dict[str, Any]:
    cand = [r for r in rows if r["dataset"].startswith("hofmann") and r["layer_um"] == 0
            and r["power_W"] <= REF_POWER_LIMIT_W]
    ctx = multiprocessing.get_context("spawn")
    started = time.perf_counter()
    out_rows = []
    for r in cand:
        left = budget_s - (time.perf_counter() - started)
        rec = {"rowId": r["rowId"], "power_W": r["power_W"], "speed_mm_s": r["speed_mm_s"],
               "beamDiameter_um": r["beamDiameter_um"],
               "measured": {"width_um": r["width_um"], "depth_um": r["depth_um"]}}
        if left <= 5.0:
            rec.update(status="not-run (budget)")
            out_rows.append(rec)
            continue
        raw = {"mode": "standard", "backend": "reference", "surfaceMode": "bare-plate",
               "barePlateGeometry": "square", "sourcePenetration_um": REF_SOURCE_PENETRATION_UM,
               "material": r["material"], "power_W": r["power_W"], "speed_mm_s": r["speed_mm_s"],
               "beamDiameter_um": r["beamDiameter_um"], "preheat_C": r["preheat_C"],
               "mesh_um": REF_MESH_UM, "trackLength_um": REF_TRACK_LENGTH_UM}
        result_path = Path(tempfile.mkdtemp(prefix="lpbf-dataset-ref-")) / "result.json"
        p = ctx.Process(target=_ref_worker, args=(raw, str(result_path)))
        t0 = time.perf_counter()
        p.start()
        p.join(min(per_case_s, left))
        if p.is_alive():
            p.terminate()
            p.join()
            rec.update(status="not-run (budget)", message="case exceeded the per-case/total wall budget")
        else:
            try:
                rec.update(json.loads(result_path.read_text(encoding="utf-8")))
            except Exception:
                rec.update(status="other-error", message="no result returned")
        shutil.rmtree(result_path.parent, ignore_errors=True)
        if rec.get("status") == "completed":
            rec["meshLimited"] = bool(rec["depth_um"] < 2.5 * REF_MESH_UM)
        out_rows.append(rec)
    n_done = sum(1 for x in out_rows if x["status"] == "completed")
    n_boil = sum(1 for x in out_rows if x["status"] == "boiling-stop")
    n_skip = sum(1 for x in out_rows if x["status"].startswith("not-run"))
    return {
        "settings": {"mode": "standard", "backend": "reference", "surfaceMode": "bare-plate",
                     "barePlateGeometry": "square", "sourcePenetration_um": REF_SOURCE_PENETRATION_UM,
                     "mesh_um": REF_MESH_UM, "trackLength_um": REF_TRACK_LENGTH_UM,
                     "preheat_C": 20.0, "totalBudget_s": budget_s, "perCaseBudget_s": per_case_s},
        "selection": f"Hofmann rows with t_powder = 0 (bare plate) and P <= {REF_POWER_LIMIT_W:.0f} W "
                     f"({len(cand)} rows); all other rows are not run with the reference transient.",
        "counts": {"candidates": len(cand), "completed": n_done, "boilingStop": n_boil, "notRun": n_skip},
        "rows": out_rows,
        "note": ("sourcePenetration_um = 40 is an arbitrary, unvalidated choice for the bare-plate volumetric "
                 "absorption depth; mesh 20 um is coarse relative to the 50-140 um spots and the result is not "
                 "mesh-converged: every completed case has depth <= 2 cells, so its width/depth are cell-quantised "
                 "(meshLimited = true) and carry almost no information about the measured track; a completed width of 0 means no resolved liquid extent. completed/boiling-stop is the reference transient's own validity stop; the "
                 "widths/depths are a model comparison, not validation. Rows beyond the budget were skipped, "
                 "not estimated."),
    }


# ---------------------------------------------------------------------------------------------
# document assembly
# ---------------------------------------------------------------------------------------------
def _round(o: Any) -> Any:
    if isinstance(o, float):
        return None if not math.isfinite(o) else round(o, 4)
    if isinstance(o, dict):
        return {k: _round(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_round(v) for v in o]
    return o


def _lf_sha256(path: Path) -> tuple:
    """(sha256 of the LF-normalised bytes, bytes): stable across autocrlf checkouts."""
    norm = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(norm).hexdigest(), norm


def probe_raytracer_importable() -> bool:
    """Separate-process probe: can powder_bed_raytracer be imported at all (no pin applied there)?"""
    code = f"import sys; sys.path.insert(0, {str(PYTHON_DIR)!r}); import {RAYTRACER_MODULE}"
    try:
        res = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True, timeout=180,
                             cwd=str(PYTHON_DIR))
        return res.returncode == 0
    except Exception:
        return False


def _pop_flat_plate(preds: Sequence[Dict[str, Any]]) -> int:
    return sum(int(p.pop("_flatPlateCalls", 0) or 0) for p in preds)


def build_limits(out_rows: Sequence[Dict[str, Any]], summary: Dict[str, Any],
                 absorption: Dict[str, Any], include_wave2: bool = False) -> List[str]:
    """Plain-language limits, with every number computed from the record (nothing hardcoded)."""
    n_rows = len(out_rows)
    lim: List[str] = []
    pooled = ", ".join(f"{k} {summary[k]['all']['n']} of {n_rows}" for k in KERNELS)
    com = summary[KERNELS[0]]["common"]
    lim.append(f"Kernels are compared on different included subsets (rows with extentStatus == 'computed'): pooled n = "
               f"{pooled}. Only summary.<kernel>.common (n = {com['n']}, the rows where all kernels are computed) is a "
               f"like-for-like comparison; pooled and per-regime figures of different kernels are not.")
    rc = summary["rosenthal"].get("conduction")
    if rc:
        lim.append(f"Rosenthal conduction statistics rest on {rc['n']} of {rc['n'] + rc['nExcluded']} conduction rows: "
                   "they are selected by the kernel's own output (only rows where Rosenthal resolves an extent "
                   "without heuristic fallback, search-box limitation or the 0.55 x beam-diameter width floor "
                   "are 'computed'), so they describe the rows it can resolve, not the regime.")
    et = summary["eagar-tsai"].get("keyhole", {}).get("depth")
    gk = summary["goldak"].get("keyhole", {}).get("depth")
    if et and gk:
        keys = ("bias_pct", "mape_pct", "rmse_um", "within30pct", "withinFactor2")
        same = all(et[x] == gk[x] for x in keys)
        lim.append(("Eagar-Tsai and Goldak keyhole-regime depth statistics are identical (bias "
                    f"{et['bias_pct']:+.1f} %, MAPE {et['mape_pct']:.1f} %)" if same else
                    "Eagar-Tsai and Goldak keyhole-regime depth statistics are near-identical (bias "
                    f"{et['bias_pct']:+.1f} / {gk['bias_pct']:+.1f} %, MAPE {et['mape_pct']:.1f} / {gk['mape_pct']:.1f} %)")
                   + " because both add the same Fabbro keyhole depth term; they are not independent evidence.")
    if include_wave2:
        lim.append("The measurements carry no uncertainty model: the pooled-summary datasets (Hofmann 316L, Totis "
                   "Ti-6Al-4V) provide no per-row measurement uncertainty; the wave 2 Lane IN625 rows carry Table 3 "
                   "per-track sigma (measured.widthSigma_um / depthSigma_um, the spread of N = 3 microscopy "
                   "measurements, not an uncertainty) and the statistics do not use it. The bootstrap intervals cover "
                   "resampling of parameter sets only, not measurement error, the estimated material laws or the "
                   "assumed absorptivity.")
    else:
        lim.append("The measurements carry no uncertainty model (neither dataset provides per-row measurement "
                   "uncertainty); the bootstrap intervals cover resampling of parameter sets only, not measurement "
                   "error, the estimated material laws or the assumed absorptivity.")
    hof = [r for r in out_rows if str(r["dataset"]).startswith("hofmann")]
    if hof:
        sets = len({_set_key(r) for r in hof})
        lim.append(f"Replicate rows are not independent: the Hofmann table has {len(hof)} rows but only {sets} distinct "
                   "parameter sets; the bootstrap intervals resample whole parameter sets (clusters), the point "
                   "statistics weight every row.")
    n_ball = sum(1 for r in out_rows if r["regime"]["label"] == "balling-flagged")
    lim.append(f"Balling-flagged rows ({n_ball}) are inside the pooled 'all' headline statistics; a continuous-track "
               "screening kernel is not meant to describe them.")
    n_totis = sum(1 for r in out_rows if str(r["dataset"]).startswith("totis"))
    lim.append(f"The Totis depth datum is the top of the printed base under the 25 um powder layer (Vaglio et al. 2020, "
               f"Fig. 1/2b; the workbook does not state it) and the Hofmann datum is the substrate surface (Fig. 2); "
               f"the kernels compute depth from the free surface, so the {n_totis} Totis and the Hofmann powder-layer "
               f"depths carry an offset, reported as the declared sensitivity column `sensitivity."
               f"depthDatumCorrection_um` = phi*t with phi = {PACKING_PHI:g} (" + DEPTH_DATUM_WORDING + "), never "
               f"applied to the served depth.")
    lim.append("The kernels ignore powder-layer thickness (identical predictions at 0/30/60 um; see "
               "assumptions.layer_um), so any trend with powder-layer thickness is in the measurements only.")
    lim.append(f"Absorption path: {absorption['path']} absorptivity_IR "
               f"({', '.join(f'{m} {a}' for m, a in absorption['absorptivity_by_material'].items())}); "
               + ("the GPU powder ray tracer was not used" if absorption["pinned"] else
                  "the ray-tracer path was not pinned") + "; with the ray tracer the predictions change.")
    lim.append("The reference-transient block depends on wall-clock budgets (total and per case): on a slower host "
               "rows can become 'not-run (budget)'. --reuse-reference copies the block of an earlier record instead.")
    return lim


def build_document(quick: bool, jobs: int, ref_budget_s: float, skip_reference: bool,
                   generated_at: str, allow_raytracer: bool = False,
                   reuse_reference: Optional[Path] = None, include_wave2: bool = False) -> Dict[str, Any]:
    pin_flat_plate(allow_raytracer)
    import lpbf_public_datasets as pd
    from lpbf_simulation import implementation_fingerprint
    from four_alloy_materials import thermal_props

    h = pd.load_hofmann_316l()
    t = pd.load_totis_ti64()
    cmu = pd.load_cmu_ti64()
    kl = pd.load_ku_leuven_in718()
    data_rows = h["rows"][:40] + t["rows"][:40] if quick else h["rows"] + t["rows"]
    w2 = load_wave2(pd) if include_wave2 else None
    if w2:
        data_rows = data_rows + w2["rows"]
    extra_rows = cmu["rows"] + kl["rows"]
    if quick:
        extra_rows = [r for dataset_id in ("cmu-ti64-st-2026", "cmu-ti64-mt-2026", "ku-leuven-in718-2021")
                      for r in [x for x in extra_rows if x["dataset"] == dataset_id][:40]]

    for r in data_rows:
        r["regime"] = pd.classify_regime(r["material"], r["power_W"], r["speed_mm_s"], r["beamDiameter_um"],
                                         r["preheat_C"], r["balling"])
        r["regime"]["dOverW"] = r["depth_um"] / r["width_um"]
        if r.get("publishedRegime"):
            r["regime"]["publishedLabel"] = r["publishedRegime"]

    tasks = [{"row": r, "kernel": k, "allowRaytracer": allow_raytracer} for r in data_rows for k in KERNELS]
    preds = _map(tasks, jobs)
    warn_by_kernel = {k: _pop_flat_plate(preds[j::len(KERNELS)]) for j, k in enumerate(KERNELS)}
    out_rows = []
    for i, r in enumerate(data_rows):
        p = {k: preds[i * len(KERNELS) + j] for j, k in enumerate(KERNELS)}
        measured = {"width_um": r["width_um"], "depth_um": r["depth_um"]}
        if r["area_um2"] is not None:
            measured["area_um2"] = r["area_um2"]
        if r["balling"] is not None:
            measured["balling"] = r["balling"]
        if r["height_um"] is not None:
            measured["height_um"] = r["height_um"]
        for key in ("widthSigma_um", "depthSigma_um", "sampleCount"):
            if r.get(key) is not None:
                measured[key] = r[key]
        out_row = {
            "dataset": r["dataset"], "rowId": r["rowId"],
            "inputs": {"material": r["material"], "power_W": r["power_W"], "speed_mm_s": r["speed_mm_s"],
                       "beamDiameter_um": r["beamDiameter_um"], "layer_um": r["layer_um"],
                       "preheat_C": r["preheat_C"]},
            "measured": measured, "regime": r["regime"], "predictions": p}
        datum = depth_datum_correction_um(r["dataset"], r["layer_um"])
        if datum is not None:  # additive key; predictions above are the served values
            out_row["sensitivity"] = datum
        out_rows.append(out_row)

    # Preserve the newly added source rows without fabricating missing process inputs or resolving
    # KU Leuven's unresolved width/depth units and half-width operator. These rows are explicitly excluded.
    for r in extra_rows:
        missing = ("power" if r.get("power_W") is None else None) or ("beam diameter" if r.get("beamDiameter_um") is None else None)
        if str(r["dataset"]).startswith("ku-leuven"):
            exclusion = "excluded: source width/depth units and width operator unresolved"
            measured = {"width_um": None, "depth_um": None}
            regime = {"label": "unclassified-source-dimensions-unresolved", "normalizedEnthalpy": None}
        else:
            exclusion = f"excluded: {missing} not reported" if missing else "excluded: beam diameter not reported"
            measured = {"width_um": r["width_um"], "depth_um": r["depth_um"]}
            regime = {"label": "unclassified-missing-process-input", "normalizedEnthalpy": None}
        predictions = {k: {"width_um": None, "depth_um": None, "length_um": None,
                           "extentStatus": exclusion, "extentNote": exclusion, "included": False}
                       for k in KERNELS}
        inputs = {"material": r["material"], "power_W": r.get("power_W"), "speed_mm_s": r["speed_mm_s"],
                  "beamDiameter_um": r.get("beamDiameter_um"), "layer_um": r.get("layer_um"),
                  "preheat_C": r.get("preheat_C")}
        out_rows.append({"dataset": r["dataset"], "rowId": r["rowId"], "inputs": inputs,
                         "measured": measured, "regime": regime, "predictions": predictions})

    # The pooled headline, its limits and the absorptivity sensitivity cover the 2026-10-05 dataset scope only;
    # wave 2 rows are scored per dataset in doc['wave2']['scorecard'] (their inputs carry unverified values).
    wave2_ids = set(WAVE2_SCORECARD_DATASETS) if w2 else set()
    pooled_rows = [r for r in out_rows if r["dataset"] not in wave2_ids]
    summary = summarize(pooled_rows, with_ci=True)
    add_common_cells(summary, pooled_rows, with_ci=True)
    breakdowns: Dict[str, Any] = {"byDataset": {}, "bySpotSize_um": {}, "byPowderLayer_um": {}}
    for ds in sorted({r["dataset"] for r in out_rows}):
        breakdowns["byDataset"][ds] = summarize([r for r in out_rows if r["dataset"] == ds])
    hof = [r for r in out_rows if r["dataset"].startswith("hofmann")]
    for d in sorted({r["inputs"]["beamDiameter_um"] for r in hof}):
        breakdowns["bySpotSize_um"][f"{d:g}"] = summarize([r for r in hof if r["inputs"]["beamDiameter_um"] == d])
    for L in sorted({r["inputs"]["layer_um"] for r in hof}):
        breakdowns["byPowderLayer_um"][f"{L:g}"] = summarize([r for r in hof if r["inputs"]["layer_um"] == L])

    cond_rows = [r for r in pooled_rows if r["regime"]["label"] == "conduction"]
    cond_data = {r["rowId"]: next(x for x in data_rows if x["rowId"] == r["rowId"]) for r in cond_rows}
    by_value: Dict[float, Dict[str, Dict[str, Any]]] = {}
    sens_warnings = 0
    for a in ABSORPTIVITY_VALUES:
        stasks = [{"row": cond_data[r["rowId"]], "kernel": k, "overrides": {"absorptivity_IR": a},
                   "allowRaytracer": allow_raytracer} for r in cond_rows for k in KERNELS]
        sp = _map(stasks, jobs)
        sens_warnings += _pop_flat_plate(sp)
        by_value[a] = {r["rowId"]: {k: sp[i * len(KERNELS) + j] for j, k in enumerate(KERNELS)}
                       for i, r in enumerate(cond_rows)}
    sens = sensitivity_mape(cond_rows, by_value)
    sens["label"] = ("SENSITIVITY, not a calibrated value: conduction-regime rows (regime assigned at the repo's "
                     "default absorptivity), absorptivity_IR overridden uniformly via prop_overrides; the "
                     "absorptivity actually acting in a physical track is unknown.")
    sens["rows"] = len(cond_rows)

    n_calls = len(tasks) + len(ABSORPTIVITY_VALUES) * len(cond_rows) * len(KERNELS)
    n_flat = sum(warn_by_kernel.values()) + sens_warnings
    abs_by_material = {pr["material"].replace(" Stainless Steel", ""): thermal_props(pr["material"])["absorptivity_IR"]
                       for pr in (h["provenance"], t["provenance"])}
    if w2:
        abs_by_material["Inconel 625"] = pd.screening_props("Inconel 625")["absorptivity_IR"]
    absorption = {
        "path": "flat-plate" if not allow_raytracer else "powder-raytrace (explicit opt-in)",
        "pinned": not allow_raytracer,
        "howPinned": ("calculate_meltpool_physics(absorption_model='flat-plate'), the solver default on every machine "
                      "since the 2026-10-06 tier-2 bump; sys.modules['powder_bed_raytracer'] = None is also set in "
                      "the main process and in every worker so any ray-tracer import fails loudly" if not allow_raytracer
                      else "--allow-raytracer: calculate_meltpool_physics(absorption_model='powder-raytrace'); the "
                      "ray tracer's errors propagate (no silent fallback)"),
        "raytracerModulePresent": (PYTHON_DIR / f"{RAYTRACER_MODULE}.py").is_file(),
        "raytracerImportable": probe_raytracer_importable(),
        "absorptivity_by_material": abs_by_material,
        "flatPlateCalls": n_flat,
        "flatPlateCallsByKernel": warn_by_kernel,
        "flatPlateCallsSensitivityRuns": sens_warnings,
        "solverCalls": n_calls,
        "note": ("flat-plate absorptivity_IR; the GPU powder ray tracer was not used; with it the predictions change "
                 f"({RAYTRACER_STUB_NOTE}). flatPlateCalls counts the solver results that report "
                 "processParameters.absorptionModel == 'flat-plate'; equal to solverCalls when every call took the "
                 "flat-plate path (failed calls report none)."
                 if not allow_raytracer else
                 "ray tracer requested explicitly (absorption_model='powder-raytrace'); flatPlateCalls is 0 when "
                 "every call used it."),
    }

    doc: Dict[str, Any] = {
        "schema": SCHEMA, "generatedAt": generated_at,
        "implementationHash": implementation_fingerprint(),
        "quick": bool(quick),
        "datasets": [
            {"id": p["id"], "doi": p["doi"], "license": p["license"], "url": p["url"], "sha256": p["fileSha256"],
             "rows": sum(1 for r in out_rows if r["dataset"] == p["id"]), "citation": p["citation"],
             "notes": p["caveats"], "source": p["source"], "materialKey": p["material"]}
            for p in (h["provenance"], t["provenance"])],
        "regimeFilter": {"rule": pd.REGIME_RULE, "parameters": pd.REGIME_PARAMETERS},
        "kernels": list(KERNELS),
        "assumptions": {
            "hatch_um": f"{DEFAULT_HATCH_UM:g} (neither dataset has a hatch: single tracks; the hatch only "
                        "enters the lack-of-fusion screen, not the width/depth/length extents)",
            "layer_um": f"t_powder 0 (bare plate) rows are passed with a nominal {NOMINAL_LAYER_FOR_BARE_UM:g} um "
                        "layer because the function requires a positive layer; width/depth/length do not depend "
                        "on it (checked at 10/30/60 um)",
            "preheat_C": "20 C assumed (not given by either dataset)",
            "absorptivity": ("the repo's absorptivity_IR authority (316L 0.30, Ti-6Al-4V 0.32: measured conduction-mode "
                             "bare-plate values since P7b; the regime index reads the convention constants 0.42 and "
                             "0.35), flat-plate"),
            "inclusionRule": "a row counts for statistics only when extentStatus == 'computed'",
            "powderBedRayTracer": ("calculate_meltpool_physics runs the optional GPU powder ray tracer only when "
                                   "absorption_model='powder-raytrace' is requested (tier-2 bump 2026-10-06); the "
                                   "default and this harness use the flat-plate absorptivity, so the ray tracer was "
                                   "not used; see `absorption`" if not allow_raytracer else
                                   "--allow-raytracer: the GPU powder ray tracer was requested explicitly "
                                   "(absorption_model='powder-raytrace'); see `absorption`"),
        },
        "absorption": absorption,
        "limits": build_limits(pooled_rows, summary, absorption, include_wave2=bool(w2)),
        "rows": out_rows,
        "summary": summary,
        "breakdowns": breakdowns,
        "absorptivitySensitivity": sens,
        "honesty": {"statement": HONESTY_STATEMENT, "experimentalValidation": False,
                    "measuredVsEstimated": "measured: dataset widths/depths; estimated: all material laws and the "
                                           "absorptivity; computed: kernel outputs"},
    }
    # Dataset catalog is additive: existing IDs and keys stay stable for the TypeScript consumer.
    extra_catalog = []
    for dataset_id, filename, digest, count, note in (
        ("cmu-ti64-st-2026", "STMeasurements.csv", pd.CMU_ST_TABLE_SHA256, 216,
         "ST source table has no power column; beam diameter is also unreported. No solver prediction is made."),
        ("cmu-ti64-mt-2026", "MTMeasurements.csv", pd.CMU_MT_TABLE_SHA256, 410,
         "Beam diameter, layer, preheat and absorptivity are unreported; no solver prediction is made."),
    ):
        extra_catalog.append({"id": dataset_id, "doi": pd.CMU_DOI, "license": "CC BY 4.0",
                              "url": "https://doi.org/" + pd.CMU_DOI, "sha256": digest,
                              "rows": sum(1 for r in out_rows if r["dataset"] == dataset_id),
                              "citation": pd.CMU_PROVENANCE["citation"], "notes": [note],
                              "source": {"file": filename, "rawSha256": pd.CMU_FILES[filename]["sha256"]},
                              "materialKey": "Ti-6Al-4V"})
    extra_catalog.append({"id": pd.KU_LEUVEN_PROVENANCE["id"], "doi": pd.KU_LEUVEN_PROVENANCE["doi"],
                          "license": "CC0", "url": pd.KU_LEUVEN_PROVENANCE["url"],
                          "sha256": pd.KU_LEUVEN_TABLE_SHA256,
                          "rows": sum(1 for r in out_rows if r["dataset"] == pd.KU_LEUVEN_PROVENANCE["id"]),
                          "citation": pd.KU_LEUVEN_PROVENANCE["citation"],
                          "notes": pd.KU_LEUVEN_PROVENANCE["caveats"],
                          "source": {"file": "Data_Inconel718.csv", "rawSha256": "029f5c6992bd261891b30966d3bcc01ff327cd2cf1c7a6963e94de075766e1e5"},
                          "materialKey": "Inconel 718"})
    doc["datasets"].extend(extra_catalog)
    if w2:
        doc["datasets"].extend(wave2_catalog(pd, w2, out_rows))
        doc["wave2"] = build_wave2_block(pd, w2, out_rows, jobs, allow_raytracer)
        doc["summaryScope"] = {
            "datasets": sorted({r["dataset"] for r in pooled_rows}), "rows": len(pooled_rows),
            "excludedWave2Datasets": sorted(wave2_ids), "excludedWave2Rows": len(out_rows) - len(pooled_rows),
            "note": ("summary, limits and absorptivitySensitivity cover the 2026-10-05 dataset scope only, so the "
                     "pooled headline is comparable to the 2026-10-05 record; wave 2 rows are scored per dataset in "
                     "wave2.scorecard because their inputs include unverified (KU Leuven beam diameter) or "
                     "legacy-estimated (IN625 properties) values.")}
        doc["limits"].extend(wave2_limits(pd, w2, out_rows))
        doc["regimeFilter"]["rule"] += (" Wave 2 rows (KU Leuven 316L/Ti-6Al-4V, Lane IN625) are classified by the same "
                                          "screening rule; the KU Leuven authors' own labels are kept verbatim in "
                                          "regime.publishedLabel and are not used for the statistics' regime split.")
        doc["assumptions"]["wave2"] = (
            "KU Leuven rows: beam diameter " + pd.KU_WAVE2_BEAM_STATUS + "; layer left unset ("
            + pd.KU_WAVE2_LAYER_STATUS + "; kernels ignore it); 20 C "
            "preheat assumed. Lane rows: bare plate (layer 0, passed as the nominal layer), Table 3 power, D4sigma spot "
            "as the 1/e^2 diameter, 20 C preheat assumed, IN625 properties from the solver's legacy-estimated secondary "
            "table. No kernel parameter was changed for these rows; sensitivities are reported separately.")
    ku_in718 = "KU Leuven IN718 (ku-leuven-in718-2021)" if w2 else "KU Leuven"
    doc["regimeFilter"]["rule"] += (" Added datasets without a reported beam diameter (CMU) or with unresolved measured "
                                      f"dimension units/operator ({ku_in718}) are labeled unclassified and excluded "
                                      "from kernel predictions; no regime label is inferred for them.")
    doc["assumptions"]["addedDatasetTreatment"] = (
        f"CMU ST has no power field; all CMU rows lack beam diameter. {ku_in718} source dimensions retain unresolved "
        "units and width operator. These rows have no numeric regime classification or kernel predictions and are "
        "excluded from MAPE/statistics; source observations remain in rows with explicit extentStatus reasons."
        + (" This applies to the IN718 file only: the wave 2 KU Leuven 316L/Ti-6Al-4V units were resolved from their "
           "raw '(1)' files (see the wave 2 catalog notes); the same raw-file check was not applied to the IN718 file "
           "in this record." if w2 else ""))
    if w2:
        doc["assumptions"]["hatch_um"] = (f"{DEFAULT_HATCH_UM:g} (no dataset in this record has a hatch: single tracks; "
                                          "the hatch only enters the lack-of-fusion screen, not the width/depth/length "
                                          "extents)")
        doc["assumptions"]["preheat_C"] = ("20 C assumed for every dataset (no dataset in this record states a "
                                           "build-plate or substrate temperature in the files read)")
        doc["assumptions"]["absorptivity"] = ("the repo's absorptivity_IR authority (316L 0.30, Ti-6Al-4V 0.32: "
                                              "measured conduction-mode bare-plate values since P7b; "
                                              f"IN625 {abs_by_material['Inconel 625']} measured, Deisenroth 2020, from "
                                              "the secondary table, wave 2 Lane rows only; the regime index reads the "
                                              "convention constants 0.42, 0.35 and 0.38), flat-plate")
    if reuse_reference is not None:
        sha, norm = _lf_sha256(reuse_reference)
        src = json.loads(norm.decode("utf-8"))
        if "referenceTransient" not in src:
            raise SystemExit(f"{reuse_reference} has no referenceTransient block to reuse")
        block = dict(src["referenceTransient"])
        block["reusedFrom"] = {"sha256": sha, "hashOf": "LF-normalised bytes of the source record",
                               "note": "block copied, not re-run: it depends on wall-clock budgets"}
        doc["referenceTransient"] = block
    elif not skip_reference:
        doc["referenceTransient"] = run_reference_transient(
            [r for r in data_rows if r["dataset"] not in wave2_ids], ref_budget_s)
    return _round(doc)


def _fmt(x: Any, digits: int = 1) -> str:
    return "-" if x is None else f"{x:.{digits}f}"


def _stat_cell(s: Optional[Dict[str, float]]) -> str:
    if s is None:
        return "- | - | - | -"
    return f"{s['bias_pct']:+.1f} | {s['mape_pct']:.1f} | {s['rmse_um']:.1f} | {100 * s['within30pct']:.0f}% / {100 * s['withinFactor2']:.0f}%"


def _ci(v: Optional[Sequence[float]], digits: int = 1) -> str:
    return "-" if not v else f"[{v[0]:.{digits}f}, {v[1]:.{digits}f}]"


def _ci_table(summ: Dict[str, Any]) -> List[str]:
    lines = ["| kernel | regime | n | parameter sets | W bias % CI95 | W MAPE % CI95 | D bias % CI95 | D MAPE % CI95 |",
             "|---|---|---|---|---|---|---|---|"]
    for k in KERNELS:
        for label, e in summ.get(k, {}).items():
            w, d = e["width"], e["depth"]
            if w is None or "bias_pct_ci95" not in w:
                continue
            lines.append(f"| {k} | {label} | {e['n']} | {w['n_parameterSets']} | {_ci(w['bias_pct_ci95'])} | "
                         f"{_ci(w['mape_pct_ci95'])} | {_ci(d['bias_pct_ci95'])} | {_ci(d['mape_pct_ci95'])} |")
    lines.append("")
    return lines


def _summary_table(title: str, summ: Dict[str, Any]) -> List[str]:
    lines = [f"### {title}", "",
             "| kernel | regime | n | excluded | W bias % | W MAPE % | W RMSE um | W within +-30% / x0.5-2 "
             "| D bias % | D MAPE % | D RMSE um | D within +-30% / x0.5-2 |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for k in KERNELS:
        for label, e in summ.get(k, {}).items():
            lines.append(f"| {k} | {label} | {e['n']} | {e['nExcluded']} | {_stat_cell(e['width'])} | {_stat_cell(e['depth'])} |")
    lines.append("")
    return lines


def load_wave2(pd: Any) -> Dict[str, Any]:
    ku = pd.load_ku_leuven_316l_ti64()
    lane = pd.load_lane_in625()
    return {"ku": ku, "lane": lane, "rows": ku["rows"] + lane["rows"]}


def wave2_catalog(pd: Any, w2: Dict[str, Any], out_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    ku, lane = w2["ku"]["provenance"], w2["lane"]["provenance"]
    out = []
    for alloy in ("316L", "Ti-6Al-4V"):
        dataset_id = pd.KU_WAVE2_DATASET_ID[alloy]
        files = [f for f in ku["sourceFiles"] if f["alloy"] == alloy]
        out.append({"id": dataset_id, "doi": " + ".join(f["doi"] for f in files), "license": ku["license"],
                    "url": files[0]["url"], "sha256": ku["fileSha256"],
                    "rows": sum(1 for r in out_rows if r["dataset"] == dataset_id), "citation": ku["citation"],
                    "notes": ku["caveats"] + [f"not compared: {x['rowId']} ({x['reason']})" for x in ku["notCompared"]
                                              if x["rowId"].startswith(dataset_id)],
                    "source": {"files": files, "retrieved": ku["retrieved"]},
                    "materialKey": pd.KU_WAVE2_MATERIAL[alloy], "evidenceKind": ku["evidenceKind"]})
    out.append({"id": lane["id"], "doi": lane["doi"], "license": lane["license"], "url": lane["url"],
                "sha256": lane["fileSha256"], "rows": sum(1 for r in out_rows if r["dataset"] == lane["id"]),
                "citation": lane["citation"], "notes": lane["caveats"],
                "source": dict(lane["source"], tableSha256ByName=lane["fileSha256ByName"]),
                "materialKey": lane["material"], "evidenceKind": lane["evidenceKind"]})
    return out


def _rerun_summary(rows: Sequence[Dict[str, Any]], jobs: int, allow_raytracer: bool,
                   accounting: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
    """Kernel statistics for a variant of the input rows (same kernels, same statistics, no fitting).
    Solver calls and flat-plate calls are added to `accounting` when given."""
    import lpbf_public_datasets as pd
    tasks = [{"row": r, "kernel": k, "allowRaytracer": allow_raytracer} for r in rows for k in KERNELS]
    preds = _map(tasks, jobs)
    n_flat = _pop_flat_plate(preds)
    if accounting is not None:
        accounting["solverCalls"] += len(tasks)
        accounting["flatPlateCalls"] += n_flat
    out_rows = []
    for i, r in enumerate(rows):
        regime = pd.classify_regime(r["material"], r["power_W"], r["speed_mm_s"], r["beamDiameter_um"],
                                    r["preheat_C"], r["balling"])
        out_rows.append({"dataset": r["dataset"], "rowId": r["rowId"],
                         "inputs": {"power_W": r["power_W"], "speed_mm_s": r["speed_mm_s"],
                                    "beamDiameter_um": r["beamDiameter_um"], "layer_um": r["layer_um"]},
                         "measured": {"width_um": r["width_um"], "depth_um": r["depth_um"]}, "regime": regime,
                         "predictions": {k: preds[i * len(KERNELS) + j] for j, k in enumerate(KERNELS)}})
    summ = summarize(out_rows, with_ci=True)
    add_common_cells(summ, out_rows, with_ci=True)
    return summ


WAVE2_SCORECARD_DATASETS = ("ku-leuven-316l-2021", "ku-leuven-ti64-2021", "lane-in625-2020")


def build_wave2_block(pd: Any, w2: Dict[str, Any], out_rows: Sequence[Dict[str, Any]], jobs: int,
                      allow_raytracer: bool) -> Dict[str, Any]:
    by_id = {r["rowId"]: r for r in out_rows}
    ku_rows = [dict(r, beamDiameter_um=pd.KU_WAVE2_BEAM_SENSITIVITY_UM) for r in w2["ku"]["rows"]]
    ammt = [r for r in w2["lane"]["rows"] if r["machine"] == "AMMT"]
    nominal = [dict(r, power_W=pd.LANE_NOMINAL_CASE_POWER_W[r["case"]]) for r in ammt]
    crosstab: Dict[str, Dict[str, int]] = {}
    for r in w2["ku"]["rows"]:
        if r["rowId"] not in by_id:
            continue
        published = r.get("publishedRegime") or "none"
        screened = by_id[r["rowId"]]["regime"]["label"]
        crosstab.setdefault(published, {}).setdefault(screened, 0)
        crosstab[published][screened] += 1
    scorecard = {}
    for ds in WAVE2_SCORECARD_DATASETS:
        rows = [r for r in out_rows if r["dataset"] == ds]
        if not rows:
            continue
        s = summarize(rows, with_ci=True)
        add_common_cells(s, rows, with_ci=True)
        scorecard[ds] = s
    all_ids = {r["rowId"] for r in out_rows}
    ku_rows = [r for r in ku_rows if r["rowId"] in all_ids]
    nominal = [r for r in nominal if r["rowId"] in all_ids]
    acct = {"solverCalls": 0, "flatPlateCalls": 0}
    ku_sens = {ds: _rerun_summary([r for r in ku_rows if r["dataset"] == ds], jobs, allow_raytracer, acct)
               for ds in ("ku-leuven-316l-2021", "ku-leuven-ti64-2021") if any(r["dataset"] == ds for r in ku_rows)}
    lane_sens = _rerun_summary(nominal, jobs, allow_raytracer, acct) if nominal else None
    return {
        "label": ("Wave 2 (2026-10-06): new open measured datasets run through the unchanged screening kernels; "
                  "comparison, not validation"),
        "scorecard": scorecard,
        "kuBeamDiameterSensitivity": {
            "label": ("SENSITIVITY on an unresolved input, not a fit: KU Leuven rows re-run with beam diameter "
                      f"{pd.KU_WAVE2_BEAM_SENSITIVITY_UM:g} um (the 37.5 um value read as a radius)"),
            "beamDiameter_um": pd.KU_WAVE2_BEAM_SENSITIVITY_UM, "rows": len(ku_rows), "byDataset": ku_sens},
        "laneNominalPowerSensitivity": {
            "label": ("SENSITIVITY on an unresolved input, not a fit: Lane AMMT rows re-run at the nominal case power "
                      "from the paper text (150 W case A, 195 W cases B/C) instead of the Table 3 power (137.9/179.2 W)"),
            "rows": len(nominal), "summary": lane_sens},
        "sensitivityRunAccounting": dict(acct, note=(
            "solver calls of the two wave 2 sensitivity re-runs, not included in absorption.solverCalls; "
            "flatPlateCalls counts those calls whose result reports absorptionModel 'flat-plate'")),
        "kuRegimeLabelCrosstab": {
            "label": ("rows: KU Leuven authors' published label; columns: the repo's screening classifier at the "
                      "primary inputs. Counts only; the published label is not a measured regime boundary."),
            "counts": crosstab},
        "laneTable4": w2["lane"]["provenance"]["table4"],
        "referenceTargets": pd.wave2_reference_targets(),
        "evidence": {"experimentalValidation": False, "opticalOperatorMatched": False,
                     "measured": "KU Leuven w/d exp, Lane Table 3/4 cross sections, NIST Table 2/3, Simonds Table III",
                     "estimated": "all material laws (IN625 legacy-estimated secondary), absorptivity, preheat",
                     "computed": "kernel outputs and statistics"},
    }


def wave2_limits(pd: Any, w2: Dict[str, Any], out_rows: Sequence[Dict[str, Any]]) -> List[str]:
    ku_ids = set(pd.KU_WAVE2_DATASET_ID.values())
    n_ku = sum(1 for r in out_rows if r["dataset"] in ku_ids)
    n_lane = sum(1 for r in out_rows if r["dataset"] == "lane-in625-2020")
    return [
        f"KU Leuven 316L/Ti-6Al-4V ({n_ku} condition means): the beam diameter is {pd.KU_WAVE2_BEAM_STATUS}; the "
        f"{pd.KU_WAVE2_BEAM_SENSITIVITY_UM:g} um re-run in wave2.kuBeamDiameterSensitivity shows how much the "
        "statistics move with it. Rows are condition means of 7 to 16 sections; the bootstrap resamples conditions, "
        "not sections.",
        f"Lane IN625 ({n_lane} tracks): AMMT kernel inputs use the Table 3 power (137.9/179.2 W). "
        + pd.LANE_POWER_QUESTION + " See wave2.laneNominalPowerSensitivity. IN625 properties are legacy estimates "
        f"(absorptivity_IR {pd.screening_props('Inconel 625')['absorptivity_IR']}).",
        "Wave 2 reference targets (NIST AMB2022-03 thermal Tables 2-3, Simonds 2018 Table III) have no like-for-like "
        "model comparison in the app; their comparison status is 'unavailable' with the reason recorded.",
        f"The pooled summary, its limits above and the absorptivity sensitivity exclude the {n_ku + n_lane} wave 2 rows "
        "(KU Leuven 316L/Ti-6Al-4V, Lane IN625; see summaryScope), so the pooled headline keeps the 2026-10-05 scope "
        "and is comparable to it. Per-dataset wave 2 figures are in wave2.scorecard; they are not pooled across "
        "materials.",
    ]


def render_markdown(doc: Dict[str, Any], view_name: Optional[str] = None,
                    view_sha256: Optional[str] = None) -> str:
    L = [f"# LPBF dataset comparison ({doc['generatedAt']})", "", HEADER_MD, "",
         f"Schema `{doc['schema']}`; implementation fingerprint `{doc['implementationHash']}`; "
         f"quick mode: {doc['quick']}. Honesty: {doc['honesty']['statement']}. `experimentalValidation` = false.", ""]
    if view_sha256:
        L += [f"Slim view record `{view_name}` (this record minus `breakdowns` and `referenceTransient.rows`; "
              f"sha256 of its LF bytes `{view_sha256}`).", ""]
    L += ["## Datasets", ""]
    for d in doc["datasets"]:
        L.append(f"- **{d['id']}** ({d['materialKey']}): DOI {d['doi']}, {d['license']}, {d['rows']} rows recorded, "
                 f"table sha256 `{d['sha256']}`. {d['citation']}")
        for n in d["notes"]:
            L.append(f"  - caveat: {n}")
    L += ["", "## Regime screening rule", "", doc["regimeFilter"]["rule"], "", "Row counts per regime: "
          + ", ".join(f"{k} {v['n'] + v['nExcluded']}" for k, v in doc["summary"]["rosenthal"].items()
                      if k != "common"), "",
          "## Assumptions", ""]
    for k, v in doc["assumptions"].items():
        L.append(f"- **{k}**: {v}")
    ab = doc["absorption"]
    L += ["", "## Absorption path", "",
          f"Path: **{ab['path']}** (pinned: {ab['pinned']}). {ab['howPinned']}.", "",
          f"Ray-tracer module present: {ab['raytracerModulePresent']}; importable in a separate probe process: "
          f"{ab['raytracerImportable']}. Absorptivity by material: "
          + ", ".join(f"{m} {a}" for m, a in ab["absorptivity_by_material"].items()) + ". "
          + (f"Flat-plate calls: {ab['flatPlateCalls']} of {ab['solverCalls']} solver calls "
             f"(by kernel, main run: " + ", ".join(f"{k} {v}" for k, v in ab["flatPlateCallsByKernel"].items()) + ")."
             if "flatPlateCalls" in ab else  # records written before the 2026-10-06 tier-2 bump
             f"Fallback warnings captured: {ab['fallbackWarnings']} of {ab['solverCalls']} solver calls "
             f"(by kernel, main run: " + ", ".join(f"{k} {v}" for k, v in ab["fallbackWarningsByKernel"].items()) + ")."),
          "",
          ab["note"], "", "## Limits", ""]
    for x in doc["limits"]:
        L.append(f"- {x}")
    n_sens = sum(1 for r in doc["rows"] if r.get("sensitivity"))
    if n_sens:
        by_layer: Dict[Any, int] = {}
        for r in doc["rows"]:
            if r.get("sensitivity"):
                key = (r["dataset"], r["sensitivity"]["depthDatumCorrection_um"])
                by_layer[key] = by_layer.get(key, 0) + 1
        L += ["", "## Depth-datum sensitivity column (declared; not applied to the served depth)", "",
              f"`rows[].sensitivity.depthDatumCorrection_um` = phi*t with phi = {PACKING_PHI:g} (Trapp 2017) on "
              f"{n_sens} powder-layer rows of sources whose measured depth starts at the substrate; "
              f"{DEPTH_DATUM_WORDING}. It is reported alongside the served `predictions` and never replaces them.", ""]
        L += [f"- {ds}: {n} rows, correction {c:g} um" for (ds, c), n in sorted(by_layer.items())]
    scope = doc.get("summaryScope")
    L += ["", "## Summary: kernel x regime (" + ("2026-10-05 dataset scope pooled; wave 2 rows excluded, see the "
          "wave 2 scorecard" if scope else "all datasets pooled") + ")", ""]
    if scope:
        L += [scope["note"] + f" Pooled rows: {scope['rows']}; excluded wave 2 rows: {scope['excludedWave2Rows']}.", ""]
    L += [
          "Bias = mean((pred-meas)/meas); rows with extentStatus other than `computed` are excluded and counted. "
          "Fractions: share of rows within +-30 % of the measurement / within the x0.5-2 band.", ""]
    L += _summary_table("Pooled (the `common` regime = rows where all kernels are computed)", doc["summary"])
    L += ["### Cluster-bootstrap 95 % intervals (pooled summary cells)", "",
          f"Distinct parameter sets (dataset, power, speed, beam diameter, layer) resampled with replacement, "
          f"{CI_REPLICATES} replicates, `random.Random({CI_SEED})`, percentile 2.5/97.5; replicates of one set stay "
          "together. The intervals cover this resampling only (no measurement uncertainty, no material-law "
          "uncertainty); they are in JSON `summary.<kernel>.<regime>.<width|depth>.{bias_pct_ci95, mape_pct_ci95, "
          "n_parameterSets}`.", ""]
    L += _ci_table(doc["summary"])
    for ds, s in doc["breakdowns"]["byDataset"].items():
        L += _summary_table(f"Dataset {ds}", s)
    for d, s in doc["breakdowns"]["bySpotSize_um"].items():
        L += _summary_table(f"Hofmann, spot {d} um", s)
    L += ["**Powder-layer breakdowns below:** the kernels ignore powder-layer thickness (identical predictions at "
          "0/30/60 um, see `assumptions.layer_um`), so any trend with powder-layer thickness in these tables is "
          "in the measurements only, not a kernel result.", ""]
    for p, s in doc["breakdowns"]["byPowderLayer_um"].items():
        L += _summary_table(f"Hofmann, powder layer {p} um", s)
    sens = doc["absorptivitySensitivity"]
    L += ["## Absorptivity sensitivity (SENSITIVITY, not a calibration)", "", sens["label"], "",
          f"Conduction rows: {sens['rows']}.", "",
          "| kernel | " + " | ".join(f"a={v:.2f} W MAPE %" for v in sens["values"]) + " | "
          + " | ".join(f"a={v:.2f} D MAPE %" for v in sens["values"]) + " | "
          + " | ".join(f"a={v:.2f} n" for v in sens["values"]) + " |",
          "|---|" + "---|" * (3 * len(sens["values"]))]
    for k in KERNELS:
        w = sens[k]["width_mape_pct_by_value"]
        d = sens[k]["depth_mape_pct_by_value"]
        n = sens[k]["n_included_by_value"]
        L.append(f"| {k} | " + " | ".join(_fmt(w[f'{v:.2f}']) for v in sens["values"]) + " | "
                 + " | ".join(_fmt(d[f'{v:.2f}']) for v in sens["values"]) + " | "
                 + " | ".join(str(n[f'{v:.2f}']) for v in sens["values"]) + " |")
    L += ["", "Included row counts vary with assumed absorptivity: each column uses only rows where the "
          "kernel resolves an extent. These are different evaluation subsets; lower width error can accompany "
          "higher depth error. Sensitivity, not calibration.", ""]
    if doc.get("wave2"):
        L += render_wave2_markdown(doc["wave2"])
    ref = doc.get("referenceTransient")
    if ref:
        c = ref["counts"]
        reused = ref.get("reusedFrom")
        L += ["## Reference transient (bare plate, low power)", "",
              "This block depends on wall-clock budgets (total and per case): on a slower or busier host cases can "
              "turn into 'not-run (budget)', so it is not guaranteed to reproduce; `--reuse-reference` copies the "
              "block of an earlier record instead of re-running it."
              + (f" This record's block was reused from a record with sha256 `{reused['sha256']}` (LF-normalised)."
                 if reused else ""), "",
              ref["selection"],
              f"Completed {c['completed']}, boiling stop {c['boilingStop']}, not run (budget) {c['notRun']} "
              f"of {c['candidates']}. {ref['note']}", "",
              "| row | P W | v mm/s | d um | status | W pred | W meas | D pred | D meas |",
              "|---|---|---|---|---|---|---|---|---|"]
        for r in ref["rows"]:
            L.append(f"| {r['rowId']} | {r['power_W']:g} | {r['speed_mm_s']:g} | {r['beamDiameter_um']:g} | {r['status']}{' (mesh-limited)' if r.get('meshLimited') else ''} | "
                     f"{_fmt(r.get('width_um'))} | {r['measured']['width_um']:.1f} | {_fmt(r.get('depth_um'))} | "
                     f"{r['measured']['depth_um']:.1f} |")
        L.append("")
    return "\n".join(L).rstrip("\n") + "\n"


def render_wave2_markdown(w: Dict[str, Any]) -> List[str]:
    L = ["## Wave 2 datasets (2026-10-06)", "", w["label"] + ". Per-dataset kernel x regime tables (regime = the "
         "repo's screening classifier) with cluster-bootstrap intervals:", ""]
    for ds, s in w["scorecard"].items():
        L += _summary_table(f"Wave 2 scorecard: {ds}", s)
        L += _ci_table(s)
    sens = w["kuBeamDiameterSensitivity"]
    L += ["### " + sens["label"], ""]
    for ds, s in sens["byDataset"].items():
        L += _summary_table(f"{ds} at beam diameter {sens['beamDiameter_um']:g} um", s)
    lp = w["laneNominalPowerSensitivity"]
    L += ["### " + lp["label"], ""]
    if lp["summary"]:
        L += _summary_table(f"Lane AMMT at nominal power ({lp['rows']} rows)", lp["summary"])
    acct = w.get("sensitivityRunAccounting")
    if acct:
        if "flatPlateCalls" in acct:
            L += [f"Sensitivity re-runs: {acct['solverCalls']} solver calls, {acct['flatPlateCalls']} flat-plate "
                  f"calls ({acct['note']}).", ""]
        else:  # records written before the 2026-10-06 tier-2 bump
            L += [f"Sensitivity re-runs: {acct['solverCalls']} solver calls, {acct['fallbackWarnings']} captured "
                  f"ray-tracer fallback warnings ({acct['note']}).", ""]
    ct = w["kuRegimeLabelCrosstab"]
    cols = sorted({c for v in ct["counts"].values() for c in v})
    L += ["### KU Leuven published regime label vs screening classifier", "", ct["label"], "",
          "| published / screening | " + " | ".join(cols) + " |", "|---|" + "---|" * len(cols)]
    for pub, v in sorted(ct["counts"].items()):
        L.append(f"| {pub} | " + " | ".join(str(v.get(c, 0)) for c in cols) + " |")
    L += ["", "### Lane 2020 Table 4 class summary (published, transcribed)", "",
          "| class | width um (N, Umean) | depth um (N, Umean) | length um (N, Umean) | "
          "cooling rate 1290-1190 C/s (N, Umean) | cooling-rate use |", "|---|---|---|---|---|---|"]
    for c in w["laneTable4"]:
        L.append(f"| {c['class']} | {c['width_mean_um']} ({c['width_N']}, {c['width_Umean_um']}) | {c['depth_mean_um']} "
                 f"({c['depth_N']}, {c['depth_Umean_um']}) | {c['length_mean_um']} ({c['length_N']}, "
                 f"{c['length_Umean_um']}) | {c['cr_1290_1190_mean_C_s']} ({c['cr_N']}, {c['cr_Umean_C_s']}) | "
                 f"{c.get('cooling_rate_use') or '-'} |")
    L += ["", "Umean is the standard uncertainty of the mean as labelled in Table 4 (Tables 5-7 give the uncertainty "
          "budgets for length, width and depth). Per the Table 4 caption, AMMT length and cooling rate come from the "
          "AMMT-20 us tracks only, so the AMMT class cooling rates are the same AMMT-20 us values that Table 3 "
          "footnote c says should not be used; they are flagged do-not-use. The paper calls all cooling rates "
          "exemplar, not reference data.", ""]
    for t in w["referenceTargets"]:
        src = t["source"]
        L += [f"### Reference target: {t['dataset']} ({t['kind']})", "",
              f"{t['citation']} Evidence kind: {t['evidenceKind']}. Source sha256 `{src['sha256']}` ({src['bytes']} B, "
              f"retrieved {src['retrieved']}); committed table sha256 `{t['tableSha256']}`.", ""]
        keys = [k for k in t["rows"][0].keys() if k != "tableRefs"]
        L += ["| " + " | ".join(keys) + " |", "|" + "---|" * len(keys)]
        for r in t["rows"]:
            L.append("| " + " | ".join("-" if r[k] is None else f"{r[k]:g}" if isinstance(r[k], float) else str(r[k])
                                       for k in keys) + " |")
        L += [""] + [f"- caveat: {c}" for c in t["caveats"]]
        L += ["", f"**Comparison: {t['comparison']['status']}.** {t['comparison']['reason']}", ""]
    return L


def make_view_record(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Drop non-rendered analysis detail from the browser payload for excluded public rows."""
    view = {k: v for k, v in doc.items() if k != "breakdowns"}
    if "referenceTransient" in view:
        view["referenceTransient"] = {k: v for k, v in view["referenceTransient"].items() if k != "rows"}
    excluded_datasets = {"cmu-ti64-st-2026", "cmu-ti64-mt-2026", "ku-leuven-in718-2021"}
    slim_rows = []
    compact_exclusions: Dict[tuple, int] = {}
    for row in view["rows"]:
        if row.get("dataset") not in excluded_datasets:
            slim_rows.append(row)
            continue
        status = row["predictions"]["rosenthal"]["extentStatus"]
        key = (row["regime"]["label"], status)
        compact_exclusions[key] = compact_exclusions.get(key, 0) + 1
    view["rows"] = slim_rows
    view["predictionExclusions"] = [
        {"regime": regime, "status": status, "count": count}
        for (regime, status), count in sorted(compact_exclusions.items())
    ]
    return view


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", required=True, help="output JSON path (the .md goes next to it)")
    ap.add_argument("--quick", action="store_true", help="first 40 rows of each dataset")
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--ref-budget-s", type=float, default=900.0)
    ap.add_argument("--skip-reference", action="store_true")
    ap.add_argument("--generated-at", default=GENERATED_AT_DEFAULT)
    ap.add_argument("--allow-raytracer", action="store_true",
                    help="request the GPU powder ray tracer explicitly (default: flat-plate)")
    ap.add_argument("--reuse-reference", default=None,
                    help="copy referenceTransient from this earlier record instead of re-running it")
    ap.add_argument("--view-out", default=None, help="slim view record path (default <out>.view.json)")
    ap.add_argument("--include-wave2", action="store_true",
                    help="add the 2026-10-06 datasets (KU Leuven 316L/Ti-6Al-4V, Lane IN625) and reference targets")
    a = ap.parse_args(argv)
    out = Path(a.out).resolve()
    if "golden" in out.parts:
        raise SystemExit("refusing to write under golden/")
    if a.reuse_reference and a.skip_reference:
        raise SystemExit("--reuse-reference and --skip-reference are mutually exclusive")
    view_out = Path(a.view_out).resolve() if a.view_out else out.with_suffix(".view.json")
    if "golden" in view_out.parts:
        raise SystemExit("refusing to write under golden/")
    t0 = time.perf_counter()
    doc = build_document(a.quick, a.jobs, a.ref_budget_s, a.skip_reference, a.generated_at,
                         allow_raytracer=a.allow_raytracer,
                         reuse_reference=Path(a.reuse_reference).resolve() if a.reuse_reference else None,
                         include_wave2=a.include_wave2)
    out.parent.mkdir(parents=True, exist_ok=True)
    view = make_view_record(doc)
    view_text = json.dumps(view, sort_keys=True, indent=1, ensure_ascii=False) + "\n"
    out.write_text(json.dumps(doc, sort_keys=True, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    view_out.write_text(view_text, encoding="utf-8", newline="\n")
    out.with_suffix(".md").write_text(
        render_markdown(doc, view_out.name, hashlib.sha256(view_text.encode("utf-8")).hexdigest()),
        encoding="utf-8", newline="\n")
    print(f"wrote {out}, {view_out.name} and .md in {time.perf_counter() - t0:.0f} s", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
