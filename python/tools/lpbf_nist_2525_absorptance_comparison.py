#!/usr/bin/env python3
"""Offline comparison of app absorptivity / keyhole ray tracing with NIST mds2-2525 measured absorptance.

COMPARISON, NOT VALIDATION. NIST measured the time-resolved absolute laser absorptance of polished
bare Ti-6Al-4V (SRM 654b, ~300 um thin coupon, 1070 nm, 1/e^2 spot 122.5 um, 7 deg incidence, argon).
This tool puts three application models next to those measurements and reports every difference as a
number. Nothing is fitted: the absorptivity, cavity shape and every other model input are the
application's own values, and the keyhole-depth sweep is a SENSITIVITY bracket, never a calibration.
Where the application cannot represent the experiment the record says ``unavailable`` with the reason.

Usage (from python/, locked interpreter, PYTHONDONTWRITEBYTECODE=1):
    python -B tools/lpbf_nist_2525_absorptance_comparison.py \
        --out ../docs/LPBF_NIST_2525_ABSORPTANCE_COMPARISON_2026-10-06.json
    python -B tools/lpbf_nist_2525_absorptance_comparison.py --quick --out <json>
Options: --quick (few rays), --generated-at, --data-dir.  The companion .md is written next to the JSON.
The ray-tracing mesh is not stored and the ray paths are never stored.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path
from statistics import mean, median, stdev
from typing import Any, Dict, List, Optional

PYTHON_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PYTHON_DIR))

SCHEMA = "lpbf-nist-2525-absorptance-comparison-1"
GENERATED_AT_DEFAULT = "2026-10-06"
DATASET_DIR = PYTHON_DIR.parent / "data" / "benchmark" / "nist-mds2-2525-ti64-absorptance"
SOURCE_DIR = DATASET_DIR / "official"
ALLOWED_STATUS = ("compared", "sensitivity-only", "unavailable")

HONESTY_STATEMENT = (
    "comparison, not validation; NIST values are measured for the NIST experiment only (polished bare "
    "Ti-6Al-4V, ~300 um coupon, argon); application outputs are screening and unvalidated; the "
    "ray-tracing sweep over prescribed cavity depth is a sensitivity bracket, not a calibration; nothing "
    "was tuned to the data; where the application cannot represent the experiment the record says "
    "unavailable and no number is forced")
HEADER_MD = ("**Comparison of application absorptivity and prescribed-cavity ray tracing against NIST "
             "mds2-2525 measured laser absorptance; not experimental validation; application outputs "
             "are screening and unvalidated; nothing was tuned.**")

LABELS = {
    "experimentalValidation": False,
    "opticalOperatorMatched": False,
    "modelAcceptance": False,
    "nistResidual": None,
    "evidenceKindMeasuredFor": "NIST experiment only",
    "appOutputs": "screening, unvalidated",
}

SPOT_NAME = "Spot on Bare Metal_Calibrated Absorption Data.csv"
SCAN_NAME = "Scan on Bare Metal_Calibrated Absorption Data.csv"
UNCERTAINTY_PDF = "Absorption_Uncertainty_Analysis.pdf"
AL_SPOT_AA = "Al_Spot_AA_ASR_Results.csv"
AL_SCAN_AA = "Al_Scan_AA_MWD_ASR_Results.csv"
AL_SPOT_TDW = "Al_Spot_TDW_Results.csv"
AL_SPOT_TDA = "Al_Spot_TDA_Results.csv"
AL_SCAN_TDA = "Al_Scan_TDA_v2_Results.csv"
README_NAME = "2525_README_v200.txt"
AL_MATERIAL = "aluminium (NIST SRM 1241c)"
TI64_MATERIAL = "Ti-6Al-4V (NIST SRM 654b)"

# Pins from the NIST NERDm record; independent of any loader.  Refuse to run on mismatch.
PINNED = {
    SPOT_NAME: ("0e96b220852d762fde846e406cc44c6fc874cef22e7e41db7f4025dbcc9ca274", 6497288),
    AL_SPOT_AA: ("4429f08ff3f571ab871fdbaf072e0c67aaef346259a3f2ca8744927ad6419ffb", 242),
    AL_SCAN_AA: ("d3732fcddaaee046105aa90eb82547ffd0fe61edb425fc1e8f019c6f73ed0b4d", 364),
    AL_SPOT_TDW: ("06b280222eab5f82eb9dcfb0689f20a5011c16e115548cd94ce120e5a97b4f5c", 2169),
    AL_SPOT_TDA: ("3f0b6812f98535f5ffbb0e2fed31f084ad9a7f9cc393c04a43ed57f0bb14bf69", 2292050),
    AL_SCAN_TDA: ("3af3478b463b867ed3c78ef6e60c75f9d613607b236933f3f9df08113884a6a8", 2493685),
    README_NAME: ("936f4c166b448f4b5a27d1e2b2465f9c2db1be073a7bffd54d45eb4259120a65", 21907),
}
ABSENT = {
    SCAN_NAME: ("1c64f24e84c274d9f9ae27fb09e79b86cda2fda5bee4b67da3567c8a59ca499d", None),
    UNCERTAINTY_PDF: ("98ead678e3a8f6696650302dbf29660f2a886a62ba677453dd130c222755e28d", None),
}
ABSENT_REASON = "file not acquired (NIST download unavailable; no archived copy with the official SHA-256)"

EXPERIMENT = {
    "material": TI64_MATERIAL,
    "wavelengthNm": 1070.0,
    "beamRadius1overE2_um": 61.25,
    "spotDiameter1overE2_um": 122.5,
    "spotDiameterUncertainty_um": 3.0,
    "incidenceAngle_deg": 7.0,
    "surface": "polished bare metal (no powder)",
    "coupon": "~300 um thin Ti-6Al-4V coupon (not a semi-infinite plate)",
    "atmosphere": "argon",
    "detector": "integrating sphere, 40 ns resolution",
    "stationaryPulse_ms": 2.0,
    "scan_mm_s": 700.0,
    "source": "NIST mds2-2525 README v2.0.0 and NERDm record",
}

# --- ray-tracing sensitivity settings ---------------------------------------------------------
DEPTHS_UM = (0, 25, 50, 100, 150, 200, 300, 400, 600)
RT_NX = RT_NY = 96
RT_DX = RT_DY = 4e-6  # mesh extent (96-1)*4 um = 380 um = 6.2 beam radii
RT_MAX_BOUNCES = 16
RT_SEED = 0
RT_RAYS_FULL = 20000
RT_RAYS_QUICK = 2000
RT_UI_RAYS = 1000


# ---------------------------------------------------------------------------------------------
# input hash gate
# ---------------------------------------------------------------------------------------------
def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_verified(name: str, root: Path = SOURCE_DIR) -> bytes:
    """Return the bytes of a pinned file after checking size and SHA-256; refuse on mismatch."""
    if name not in PINNED:
        raise ValueError(f"not a pinned NIST mds2-2525 input: {name}")
    sha, size = PINNED[name]
    path = Path(root) / name
    if not path.is_file():
        raise FileNotFoundError(f"pinned NIST input missing: {path}")
    data = path.read_bytes()
    if len(data) != size or sha256_hex(data) != sha:
        raise ValueError(f"NIST mds2-2525 input {name}: size or SHA-256 mismatch; refusing to run")
    return data


def verify_inputs(root: Path = SOURCE_DIR) -> Dict[str, Dict[str, Any]]:
    """Recompute SHA-256 and size of every input read; raises ValueError on any mismatch."""
    out = {}
    for name in PINNED:
        data = read_verified(name, root)
        out[name] = {"sha256": sha256_hex(data), "bytes": len(data), "pinnedSha256": PINNED[name][0]}
    return out


def _load_loader():
    """The verified loader is required; there is no unvalidated private CSV reader."""
    import lpbf_nist_mds2_2525_absorptance as loader  # noqa: WPS433
    return loader


# ---------------------------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------------------------
def _round(value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, float):
        return float(f"{value:.6g}") if math.isfinite(value) else None
    if isinstance(value, dict):
        return {k: _round(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_round(v) for v in value]
    return value


def unavailable(reason: str, **extra: Any) -> Dict[str, Any]:
    out = {"status": "unavailable", "reason": reason}
    out.update(extra)
    return out


def read_fingerprint() -> str:
    return (PYTHON_DIR / "lpbf_implementation_fingerprint.expected").read_text(encoding="utf-8").strip()


def run_fingerprint_test() -> bool:
    proc = subprocess.run([sys.executable, "-B", "test_lpbf_implementation_fingerprint.py"],
                          cwd=str(PYTHON_DIR), capture_output=True, text=True, timeout=600)
    return proc.returncode == 0


# ---------------------------------------------------------------------------------------------
# models
# ---------------------------------------------------------------------------------------------
def flat_plate_authority() -> Dict[str, Any]:
    """Which Ti-6Al-4V absorptivity_IR calculate_meltpool_physics resolves, found programmatically.

    The solver resolves material properties as ``thermal_props(name) or
    SECONDARY_THERMOPHYSICAL_DB.get(name)``; the same lookup is repeated here
    through the solver module's own namespace, so a change in either table is
    reflected in the record without editing this tool.
    """
    from four_alloy_materials import thermal_props
    import lpbf_thermal_solver as solver
    import lpbf_material_registry as registry
    name = "Ti-6Al-4V"
    primary = solver.thermal_props(name)
    fallback = solver.SECONDARY_THERMOPHYSICAL_DB.get(name)
    resolved = primary or fallback
    if resolved is None:
        raise ValueError("lpbf_thermal_solver does not resolve Ti-6Al-4V; flat-plate comparison impossible")
    resolved_value = float(resolved["absorptivity_IR"])
    origin = ("lpbf_thermal_solver.thermal_props('Ti-6Al-4V')['absorptivity_IR'] (four_alloy_materials)"
              if primary else
              "lpbf_thermal_solver.SECONDARY_THERMOPHYSICAL_DB['Ti-6Al-4V']['absorptivity_IR'] (fallback table)")
    four = float(thermal_props(name)["absorptivity_IR"])
    reg = float(registry.material(name)["absorptivity"])
    secondary = {key: v.get("absorptivity_IR") for key, v in solver.SECONDARY_THERMOPHYSICAL_DB.items()}
    secondary_has_ti64 = name in solver.SECONDARY_THERMOPHYSICAL_DB
    note = ("the secondary inline table has no Ti-6Al-4V entry, so no legacy value competes with the resolved one"
            if not secondary_has_ti64 else
            "the secondary inline table also lists Ti-6Al-4V; it is used only if thermal_props returns nothing")
    return {
        "absorptivityOfRecord": resolved_value,
        "origin": origin,
        "solverRole": ("flat-plate eta_base_flat of calculate_meltpool_physics: the solver's default absorptivity "
                       "on every machine since the 2026-10-06 tier-2 bump (powder_bed_raytracer's effective "
                       "absorptivity is used only with an explicit absorption_model='powder-raytrace')"),
        "fourAlloyMaterials": four,
        "materialRegistry": reg,
        "secondaryInlineTable": {"entries": secondary, "containsTi64": secondary_has_ti64, "note": note},
        "allEqual": len({resolved_value, four, reg}) == 1,
    }


def run_ray_tracing(power_W: float, base_absorption: float, num_rays: int) -> Dict[str, Any]:
    try:
        from lpbf_keyhole_raytracing import compute_keyhole_raytracing
    except Exception as exc:  # warp missing
        return unavailable(f"keyhole ray tracer not importable: {type(exc).__name__}: {exc}")
    rows = []
    meta: Dict[str, Any] = {}
    for depth in DEPTHS_UM:
        params = {"power_W": power_W, "beam_radius_um": EXPERIMENT["beamRadius1overE2_um"],
                  "base_absorption": base_absorption, "keyhole_depth_um": float(depth), "device": "cpu",
                  "seed": RT_SEED, "num_rays": num_rays, "max_bounces": RT_MAX_BOUNCES,
                  "nx": RT_NX, "ny": RT_NY, "dx": RT_DX, "dy": RT_DY, "ui_ray_limit": RT_UI_RAYS}
        res = compute_keyhole_raytracing(params)
        paths = res["ray_paths"]
        segs = [len(p["points"]) - 1 for p in paths]
        total = res["total_input_W"]
        meta = {"model_id": res["model_id"], "warp_version": res["warp_version"], "device": res["device"],
                "limitations": res["limitations"], "inputs": res["inputs"], "sampling": res["sampling"]}
        rows.append({
            "keyhole_depth_um": float(depth),
            "absorbed_fraction": res["absorption_efficiency"],
            "standard_error": res["sampling"]["absorption_efficiency_standard_error"],
            "escaped_fraction": res["total_escaped_W"] / total,
            "truncated_fraction": res["total_truncated_W"] / total,
            "total_absorbed_W": res["total_absorbed_W"],
            "energy_balance_relative_error": res["energy_balance_relative_error"],
            "bounceStatsSampledRays": {
                "n_rays_sampled": len(segs),
                "mean_path_segments": mean(segs) if segs else None,
                "max_path_segments": max(segs) if segs else None,
                "fraction_at_bounce_limit": (sum(1 for s in segs if s >= RT_MAX_BOUNCES) / len(segs)) if segs else None,
                "scope": "unbiased 1000-ray subset drawn by the UI stream; segments = surface hits plus the "
                         "final escape segment",
            },
        })
    extent_um = (RT_NX - 1) * RT_DX * 1e6
    return {"status": "success", "model_id": meta["model_id"], "warp_version": meta["warp_version"],
            "device": meta["device"], "params": {
                "power_W": power_W, "beam_radius_um": EXPERIMENT["beamRadius1overE2_um"],
                "base_absorption": base_absorption, "num_rays": num_rays, "max_bounces": RT_MAX_BOUNCES,
                "seed": RT_SEED, "nx": RT_NX, "ny": RT_NY, "dx_m": RT_DX, "dy_m": RT_DY,
                "meshExtent_um": extent_um, "meshExtent_in_beam_radii": extent_um / EXPERIMENT["beamRadius1overE2_um"],
                "cavityShape": "prescribed Gaussian, sigma = beam radius / 1.5, depth = sweep value",
                "incidence": "normal (the 7 deg experimental incidence is not represented)"},
            "limitations": meta["limitations"], "sweepKind": "SENSITIVITY (not calibration)",
            "sweep": rows,
            "directPrediction": unavailable(
                "the application does not solve the cavity depth (no free surface) and the Ti-6Al-4V "
                "X-ray cavity depth is not among the pinned files, so there is no depth to feed the ray tracer"),
            }


def bracket(sweep: List[Dict[str, Any]], measured_pct: float) -> Dict[str, Any]:
    """Depth intervals of the sweep whose absorbed fraction crosses the measured percentage."""
    pts = [(r["keyhole_depth_um"], 100.0 * r["absorbed_fraction"]) for r in sweep]
    intervals = []
    for (d0, e0), (d1, e1) in zip(pts, pts[1:]):
        if (e0 - measured_pct) * (e1 - measured_pct) <= 0.0:
            intervals.append([d0, d1])
    lo, hi = min(e for _, e in pts), max(e for _, e in pts)
    if intervals:
        verdict = f"sweep brackets the measured keyhole-phase mean between prescribed depths {intervals}"
    elif hi < measured_pct:
        verdict = "no prescribed depth in the sweep reaches the measured keyhole-phase mean"
    else:
        verdict = "every prescribed depth in the sweep exceeds the measured keyhole-phase mean"
    return {"measured_pct": measured_pct, "sweepRange_pct": [lo, hi], "bracketingDepthIntervals_um": intervals,
            "verdict": verdict,
            "note": "information only: the real cavity is neither Gaussian nor static, so a bracketing depth is "
                    "not a prediction and not a calibration"}


SCAN_NOT_COMPARED_REASON = (
    "scan CSV present and hash-verified, but no comparison is made: scan-specific analysis windows for a "
    "700 mm/s trace have not been defined or reviewed (the spot-pulse windows counted from first laser-on do not "
    "apply), so the thermal solver is not run and no number is reported")


def thermal_solver_scan(loader, root: Path) -> Dict[str, Any]:
    """Ti-6Al-4V scan case.

    Absent file -> unavailable.  Present file -> verified strictly through the loader (a size/SHA-256 or parse
    failure raises; the run is refused, never downgraded), then still reported as unavailable because no
    scan-specific windows exist.  The thermal solver is not run here and sys.modules is never touched.
    """
    path = Path(root) / SCAN_NAME
    if not path.is_file():
        return unavailable(f"Ti-6Al-4V scan CSV {SCAN_NAME}: {ABSENT_REASON}")
    series = loader.load_ti64_scan_series(root)  # raises on hash/size/parse failure
    return unavailable(SCAN_NOT_COMPARED_REASON, verifiedSamples=len(series["time_s"]))


# ---------------------------------------------------------------------------------------------
# document
# ---------------------------------------------------------------------------------------------
def build_document(quick: bool, generated_at: str, root: Path = SOURCE_DIR) -> Dict[str, Any]:
    hashes = verify_inputs(root)  # refuse to run on any mismatch
    loader = _load_loader()
    summary = loader.summarize_ti64_spot(loader.load_ti64_spot_series(root))
    al = loader.load_al_tables(root)
    loader_used = "lpbf_nist_mds2_2525_absorptance"

    pre, key = summary["pre_keyhole_mean_pct"], summary["keyhole_mean_pct"]
    med_power = summary["input_power_median_W"]
    unc_w = summary["absorbed_uncertainty_median_W"]

    measured = {
        "material": TI64_MATERIAL, "file": SPOT_NAME, "evidenceKind": "measured (NIST experiment only)",
        "definition": "RelativeAbsorption (%) is NIST column 6 ('Percent absorption'; README: input minus "
                      "backscattered power, divided by input power, x 100) per 40 ns sample, used as published "
                      "and not recomputed here; window means are plain means of that column inside local windows",
        "summary": {k: v for k, v in summary.items()},
        "uncertainty": {
            "column": "AbsAbsorptionUncertainty (W), NIST column 5: absolute expanded uncertainty of the absorbed "
                      "power per the README ('--' before laser on)",
            "median_W": unc_w,
            "median_as_pp_of_median_input": (100.0 * unc_w / med_power) if unc_w is not None else None,
            "note": "the NIST uncertainty-analysis PDF is not acquired; this is the per-sample column median only",
        },
    }

    measured_only: Dict[str, Any] = {
        "material": AL_MATERIAL,
        "spotAverageAbsorption": {"material": AL_MATERIAL, "rows": al["spot_average_absorption"]["rows"]},
        "scanAverageAbsorptionAndMeltPool": {"material": AL_MATERIAL, "rows": al["scan_average_absorption"]["rows"]},
        "spotMeltPoolWidthSeries": {"material": AL_MATERIAL, "rows": len(al["spot_melt_pool_width"]["time_s"]),
                                    "max_width_um": max(al["spot_melt_pool_width"]["melt_pool_width_um"])},
        "spotTdaLocalSummary": al["spot_tda_summary"],
        "scanTdaLocalSummary": al["scan_tda_summary"],
    }
    measured_only["note"] = ("aluminium NIST SRM 1241c; not Ti-6Al-4V and not any alloy of the application; "
                             "retrievable here only, never compared with a model")

    # model 1: flat-plate absorptivity of record
    authority = flat_plate_authority()
    base = authority["absorptivityOfRecord"]
    model_pct = 100.0 * base
    diff_pp = model_pct - pre
    flat = {"quantity": "Ti-6Al-4V flat-plate absorptivity_IR", "value_fraction": base, "value_pct": model_pct,
            "authority": authority,
            "comparedWith": {"measuredMean_pct": pre, "measuredStd_pct": summary["pre_keyhole_std_pct"],
                             "window_ms": summary["pre_keyhole_window_ms"]},
            "difference_pp": diff_pp, "difference_relative_pct": 100.0 * diff_pp / pre}

    # model 2: keyhole ray tracing
    n_rays = RT_RAYS_QUICK if quick else RT_RAYS_FULL
    rt = run_ray_tracing(med_power, base, n_rays)
    if rt["status"] == "success":
        rt["flatSelfConsistency"] = {
            "depth0_absorbed_pct": 100.0 * rt["sweep"][0]["absorbed_fraction"],
            "base_absorption_pct": model_pct,
            "difference_pp": 100.0 * rt["sweep"][0]["absorbed_fraction"] - model_pct,
            "note": "normal incidence; empirical law A = a(1 + 0.5(1 - cos)) reduces to a at cos = 1; the 7 deg "
                    "incidence is not represented",
        }
        rt["bracket"] = bracket(rt["sweep"], key)

    # model 3: thermal solver
    thermal_spot = unavailable(
        "stationary 2 ms pulse is not representable by the moving-source kernels of calculate_meltpool_physics "
        "(scan speed must be > 0; a near-zero speed is not a valid substitute and was not run)")
    thermal_scan = thermal_solver_scan(loader, root)

    # headline comparison rows
    al_reason = ("the application's locked alloy set (Ti-6Al-4V, 316L, AlSi10Mg, IN718; IN625 screening) has no "
                 "aluminium SRM 1241c; AlSi10Mg is a different alloy and is not substituted")
    rows: List[Dict[str, Any]] = []

    def al_row(rid, quantity, value, unit, extra=""):
        return {"id": rid, "quantity": quantity, "material": AL_MATERIAL, "measured": value, "measuredUnit": unit,
                "model": None, "modelId": None, "difference": None, "status": "unavailable",
                "reason": al_reason + extra}

    rows.append({"id": "ti64-spot-pre-keyhole-flat-plate", "quantity": "pre-keyhole absorptance, Ti-6Al-4V stationary pulse",
                 "material": TI64_MATERIAL, "measured": pre, "measuredStd": summary["pre_keyhole_std_pct"],
                 "measuredUnit": "%", "model": model_pct, "modelUnit": "%",
                 "modelId": authority["origin"], "difference": diff_pp,
                 "differenceUnit": "percentage points (model - measured)",
                 "differenceRelative_pct": 100.0 * diff_pp / pre, "status": "compared",
                 "reason": "flat polished surface before any cavity: the like-for-like comparison; 7 deg incidence, "
                           "thin coupon and temperature dependence not represented by the constant"})
    if rt["status"] == "success":
        sw = rt["sweep"]
        rows.append({"id": "ti64-spot-keyhole-raytracer-sensitivity", "quantity": "keyhole-phase absorptance, prescribed-depth sweep",
                     "material": TI64_MATERIAL, "measured": key, "measuredStd": summary["keyhole_std_pct"],
                     "measuredUnit": "%",
                     "model": {"min_pct": 100.0 * min(r["absorbed_fraction"] for r in sw),
                               "max_pct": 100.0 * max(r["absorbed_fraction"] for r in sw),
                               "depths_um": [r["keyhole_depth_um"] for r in sw]},
                     "modelUnit": "%", "modelId": rt["model_id"], "difference": None, "status": "sensitivity-only",
                     "reason": rt["bracket"]["verdict"] + "; SENSITIVITY over prescribed depth, not calibration"})
    else:
        rows.append({"id": "ti64-spot-keyhole-raytracer-sensitivity", "quantity": "keyhole-phase absorptance, prescribed-depth sweep",
                     "material": TI64_MATERIAL, "measured": key, "measuredUnit": "%", "model": None,
                     "modelId": None, "difference": None, "status": "unavailable", "reason": rt["reason"]})
    rows.append({"id": "ti64-spot-keyhole-direct", "quantity": "keyhole-phase absorptance, direct prediction (no prescribed depth)",
                 "material": TI64_MATERIAL, "measured": key, "measuredStd": summary["keyhole_std_pct"], "measuredUnit": "%",
                 "model": None, "modelId": None, "difference": None, "status": "unavailable",
                 "reason": rt["directPrediction"]["reason"] if rt["status"] == "success" else rt["reason"]})
    rows.append({"id": "ti64-spot-thermal-solver-eta-eff", "quantity": "effective absorptivity (flat after P1), Ti-6Al-4V stationary pulse",
                 "material": TI64_MATERIAL, "measured": key, "measuredUnit": "%", "model": None,
                 "modelId": "lpbf_thermal_solver.calculate_meltpool_physics", "difference": None,
                 "status": "unavailable", "reason": thermal_spot["reason"]})
    rows.append({"id": "ti64-scan-before-during-keyhole", "quantity": "Ti-6Al-4V scan (700 mm/s) before/during-keyhole absorptance",
                 "material": TI64_MATERIAL, "measured": None, "measuredUnit": "%", "model": None,
                 "modelId": "lpbf_thermal_solver.calculate_meltpool_physics", "difference": None,
                 "status": "unavailable", "reason": thermal_scan["reason"]})
    rows.append({"id": "ti64-absorption-uncertainty-analysis", "quantity": "NIST published absorptance uncertainty analysis",
                 "material": TI64_MATERIAL, "measured": None, "measuredUnit": None, "model": None, "modelId": None,
                 "difference": None, "status": "unavailable",
                 "reason": f"{UNCERTAINTY_PDF}: {ABSENT_REASON}; only the per-sample uncertainty column is used"})
    rows.append({"id": "ti64-spot-energy-coupling", "quantity": "absorbed J / input J over the 2 ms pulse (measured context)",
                 "material": TI64_MATERIAL, "measured": 100.0 * summary["energy_coupling_fraction"], "measuredUnit": "%",
                 "model": None, "modelId": None, "difference": None, "status": "unavailable",
                 "reason": "no model counterpart: the application has no time-resolved stationary-pulse absorption model"})
    # aluminium
    sp = {r["description"]: r for r in al["spot_average_absorption"]["rows"]}
    sc = {r["description"]: r for r in al["scan_average_absorption"]["rows"]}
    for rid, quantity, tbl, desc in (
            ("al-spot-before-keyhole", "Al spot absorptance before keyhole", sp, "Average Absorption before keyhole"),
            ("al-spot-during-keyhole", "Al spot absorptance during keyhole", sp, "Average Absorption during keyhole"),
            ("al-scan-before-keyhole", "Al scan absorptance before keyhole", sc, "Average Absorption before keyhole"),
            ("al-scan-during-keyhole", "Al scan absorptance during keyhole", sc, "Average Absorption during keyhole"),
            ("al-scan-max-depth", "Al scan maximum melt-pool depth", sc, "Melt Pool Depth - Maximum"),
            ("al-scan-max-width", "Al scan maximum melt-pool width", sc, "Melt Pool Width - Maximum")):
        r = tbl[desc]
        row = al_row(rid, quantity, r["value"], r["unit"])
        row["measuredStd"] = r["std_dev"]
        rows.append(row)
    w = al["spot_melt_pool_width"]
    rows.append(al_row("al-spot-melt-pool-width-vs-time", "Al spot melt-pool width vs time (TDW; value shown is the series maximum)",
                       max(w["melt_pool_width_um"]), "micrometer",
                       "; additionally a stationary source is not representable by the moving-source kernels"))

    limits = [
        "The NIST coupon is ~300 um thin; the application's conduction kernels and the flat-plate absorptivity "
        "assume a semi-infinite plate, so late-pulse heat accumulation and absorptance differ in kind.",
        "The NIST source is stationary for 2 ms; the thermal-solver absorptivity logic is moving-source only, so "
        "the stationary pulse has no thermal-solver counterpart (not run at a fake speed).",
        "The ray tracer uses a prescribed Gaussian cavity with a fixed depth per run, not a solved keyhole; the "
        "real cavity is dynamic and not Gaussian, so a bracketing depth is not a prediction.",
        "The ray tracer's angular absorption law is empirical (A = a(1 + 0.5(1 - cos theta))), not complex-index "
        "Fresnel optics, and ray power still in flight at the 16-bounce limit is reported as truncated, never as "
        "absorbed or escaped.",
        "The experimental 7 deg incidence is not modelled (rays at normal incidence); the flat-plate absorptivity "
        "is a constant with no angle or temperature dependence.",
        "NIST absorptance was measured on polished bare metal in argon, not on powder; no powder-bed claim is made.",
        "Aluminium (SRM 1241c) before/during-keyhole averages carry three-run standard deviations only and are "
        "not comparable with any application alloy.",
        "Pre-keyhole (0.05-0.80 ms) and keyhole (0.90-2.00 ms) windows are local analysis windows chosen in this "
        "work from the first laser-on sample, not NIST-published phase boundaries; the sub-microsecond leading-edge "
        "spike is excluded by starting the first window at 0.05 ms.",
        "The Ti-6Al-4V scan CSV and the NIST uncertainty-analysis PDF were not acquired; the scan comparison and "
        "the NIST uncertainty budget are unavailable.",
        "The measured uncertainty is the per-sample column median (W) only; no replicate Ti-6Al-4V runs are in "
        "the pinned files, so the window std is a within-trace sample spread, not a run-to-run uncertainty.",
        "Sampling standard errors of the ray tracer exclude geometry, bounce truncation and model error.",
        "No model input was tuned to the data; any disagreement above is the application's, reported as found.",
    ]

    dataset = {
        "id": "nist-mds2-2525",
        "title": "Asynchronous AM Bench 2022 Challenge Data: Real-time, simultaneous absorptance and "
                 "high-speed Xray imaging",
        "doi": "10.18434/mds2-2525", "version": "1.3.2", "license": "https://www.nist.gov/open/license",
        "citation": ("Simonds, B. J., Tanner, J., Artusio-Glimpse, A., Williams, P. A., Parab, N., Zhao, C., & Sun, T. "
                     "(2022). Asynchronous AM Bench 2022 Challenge Data: Real-time, simultaneous absorptance and "
                     "high-speed Xray imaging (v1.3.2). National Institute of Standards and Technology. "
                     "https://doi.org/10.18434/mds2-2525 (constructed from the NERDm record fields)"),
        "files": {n: {"sha256": h["sha256"], "bytes": h["bytes"]} for n, h in hashes.items()},
        "absentFiles": {n: {"officialSha256": sha, "reason": ABSENT_REASON}
                        for n, (sha, _) in ABSENT.items() if not (Path(root) / n).is_file()},
    }

    doc = {
        "schema": SCHEMA, "generatedAt": generated_at, "quick": quick,
        "implementationFingerprint": read_fingerprint(),
        "honesty": HONESTY_STATEMENT, "loaderUsed": loader_used,
        "dataset": dataset, "experiment": EXPERIMENT, "measured": measured, "measuredOnly": measured_only,
        "models": {"flatPlateAbsorptivity": flat, "keyholeRayTracing": rt,
                   "thermalSolverEtaEff": {"ti64Spot": thermal_spot, "ti64Scan": thermal_scan}},
        "comparison": {"rows": rows},
        "labels": dict(LABELS),
        "limits": limits,
        "checks": {"fingerprintCheckPassed": run_fingerprint_test(), "inputHashesVerified": True},
    }
    return _round(doc)


# ---------------------------------------------------------------------------------------------
# markdown
# ---------------------------------------------------------------------------------------------
def _fmt(value: Any, digits: int = 4) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.{digits}g}"
    return str(value)


def render_markdown(doc: Dict[str, Any]) -> str:
    out: List[str] = []
    a = out.append
    a(f"# LPBF NIST mds2-2525 absorptance comparison ({doc['generatedAt']})")
    a("")
    a(HEADER_MD)
    a("")
    a(f"Schema `{doc['schema']}`; implementation fingerprint `{doc['implementationFingerprint']}`; quick mode: "
      f"{doc['quick']}; fingerprint test passed: {doc['checks']['fingerprintCheckPassed']}; loader: "
      f"`{doc['loaderUsed']}`. Honesty: {doc['honesty']}. `experimentalValidation` = false, "
      f"`opticalOperatorMatched` = false, `modelAcceptance` = false, `nistResidual` = null.")
    a("")
    a("## Dataset")
    a("")
    d = doc["dataset"]
    a(f"{d['title']}, DOI {d['doi']}, version {d['version']}, license {d['license']}.")
    a("")
    a(f"Citation: {d['citation']}")
    a("")
    a("| File | Bytes | SHA-256 |")
    a("| --- | ---: | --- |")
    for n, f in d["files"].items():
        a(f"| {n} | {f['bytes']} | `{f['sha256']}` |")
    a("")
    for n, f in d["absentFiles"].items():
        a(f"- Not acquired: `{n}` (official SHA-256 `{f['officialSha256']}`): {f['reason']}.")
    a("")
    e = doc["experiment"]
    a(f"Experiment: {e['material']}, {e['wavelengthNm']:g} nm, 1/e^2 spot diameter {e['spotDiameter1overE2_um']} um "
      f"(+/- {e['spotDiameterUncertainty_um']} um), {e['incidenceAngle_deg']:g} deg incidence, {e['surface']}, "
      f"{e['coupon']}, {e['atmosphere']}, {e['detector']}.")
    a("")
    a("## Measured summary (Ti-6Al-4V stationary 2 ms pulse; measured for the NIST experiment only)")
    a("")
    m = doc["measured"]
    s = m["summary"]
    a("| Quantity | Value | Unit |")
    a("| --- | ---: | --- |")
    for label, val, unit in (
            ("Median input power while on", s["input_power_median_W"], "W"),
            (f"Pre-keyhole mean, window {s['pre_keyhole_window_ms']} ms (local)", s["pre_keyhole_mean_pct"], "%"),
            ("Pre-keyhole sample std", s["pre_keyhole_std_pct"], "%"),
            (f"Keyhole-phase mean, window {s['keyhole_window_ms']} ms (local)", s["keyhole_mean_pct"], "%"),
            ("Keyhole-phase sample std", s["keyhole_std_pct"], "%"),
            ("Transition time (local rule)", s.get("transition_time_ms"), "ms"),
            ("Energy coupling, absorbed J / input J (derived locally, trapezoid over laser-on samples)", 100.0 * s["energy_coupling_fraction"], "%"),
            ("Median per-sample absorbed-power uncertainty", m["uncertainty"]["median_W"], "W"),
            ("... as percentage points of median input", m["uncertainty"]["median_as_pp_of_median_input"], "pp")):
        a(f"| {label} | {_fmt(val)} | {unit} |")
    a("")
    a(m["definition"] + ". " + s["window_definition"])
    a("")
    a("## Headline comparison (measured vs model)")
    a("")
    a("| Quantity | Measured | Model | Difference | Status |")
    a("| --- | ---: | ---: | ---: | --- |")
    for r in doc["comparison"]["rows"]:
        if r["status"] == "unavailable":
            continue
        meas = _fmt(r["measured"]) + (f" +/- {_fmt(r.get('measuredStd'))}" if r.get("measuredStd") is not None else "") \
            + f" {r['measuredUnit']}"
        if isinstance(r["model"], dict):
            mod = f"{_fmt(r['model']['min_pct'])} to {_fmt(r['model']['max_pct'])} {r['modelUnit']} (sweep)"
        else:
            mod = f"{_fmt(r['model'])} {r.get('modelUnit', '')}"
        diff = "-" if r["difference"] is None else f"{_fmt(r['difference'])} ({r['differenceUnit']})"
        a(f"| {r['quantity']} | {meas} | {mod} | {diff} | {r['status']} |")
    a("")
    fp = doc["models"]["flatPlateAbsorptivity"]
    a(f"Flat-plate absorptivity of record: {_fmt(fp['value_pct'])} % (origin: {fp['authority']['origin']}). "
      f"Model minus measured = {_fmt(fp['difference_pp'])} percentage points "
      f"({_fmt(fp['difference_relative_pct'])} % relative). "
      f"Note: {fp['authority']['secondaryInlineTable']['note']}. Solver role: {fp['authority']['solverRole']}.")
    a("")
    rt = doc["models"]["keyholeRayTracing"]
    a("## Ray-tracing sensitivity sweep (prescribed Gaussian cavity; SENSITIVITY, not calibration)")
    a("")
    if rt["status"] == "success":
        p = rt["params"]
        a(f"Model `{rt['model_id']}`, Warp {rt['warp_version']}, device {rt['device']}, power "
          f"{_fmt(p['power_W'])} W (measured median), beam radius {p['beam_radius_um']} um, base absorption "
          f"{_fmt(p['base_absorption'])}, {p['num_rays']} rays, {p['max_bounces']} max bounces, seed {p['seed']}, mesh "
          f"{p['nx']}x{p['ny']} at {p['dx_m'] * 1e6:g} um (extent {_fmt(p['meshExtent_um'])} um = "
          f"{_fmt(p['meshExtent_in_beam_radii'])} beam radii).")
        a("")
        a("| Depth (um) | Absorbed (%) | Std err (pp) | Escaped (%) | Truncated (%) | Mean segments | At bounce limit (%) |")
        a("| ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
        for r in rt["sweep"]:
            b = r["bounceStatsSampledRays"]
            a(f"| {_fmt(r['keyhole_depth_um'])} | {_fmt(100 * r['absorbed_fraction'])} | {_fmt(100 * r['standard_error'])} | "
              f"{_fmt(100 * r['escaped_fraction'])} | {_fmt(100 * r['truncated_fraction'])} | "
              f"{_fmt(b['mean_path_segments'])} | {_fmt(100 * b['fraction_at_bounce_limit'])} |")
        a("")
        c = rt["flatSelfConsistency"]
        a(f"Flat self-consistency: depth 0 gives {_fmt(c['depth0_absorbed_pct'])} % against base {_fmt(c['base_absorption_pct'])} % "
          f"({_fmt(c['difference_pp'])} pp); {c['note']}.")
        a("")
        a(f"Bracket: {rt['bracket']['verdict']} (sweep range {_fmt(rt['bracket']['sweepRange_pct'][0])} to "
          f"{_fmt(rt['bracket']['sweepRange_pct'][1])} %); {rt['bracket']['note']}.")
    else:
        a(f"Unavailable: {rt['reason']}")
    a("")
    a("## Unavailable")
    a("")
    a("| Item | Material | Reason |")
    a("| --- | --- | --- |")
    for r in doc["comparison"]["rows"]:
        if r["status"] == "unavailable":
            meas = "" if r["measured"] is None else f" (measured {_fmt(r['measured'])} {r['measuredUnit']})"
            a(f"| {r['quantity']}{meas} | {r['material']} | {r['reason']} |")
    a("")
    a("## Limits")
    a("")
    for item in doc["limits"]:
        a(f"- {item}")
    a("")
    return "\n".join(out)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", required=True, help="JSON output path (companion .md written next to it)")
    ap.add_argument("--quick", action="store_true", help="fewer rays")
    ap.add_argument("--generated-at", default=GENERATED_AT_DEFAULT)
    ap.add_argument("--data-dir", default=str(SOURCE_DIR))
    args = ap.parse_args(argv)
    out = Path(args.out)
    if "golden" in out.resolve().parts:
        raise SystemExit("refusing to write under golden/")
    doc = build_document(args.quick, args.generated_at, Path(args.data_dir))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, sort_keys=True, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    out.with_suffix(".md").write_text(render_markdown(doc), encoding="utf-8", newline="\n")
    print(f"wrote {out} and {out.with_suffix('.md')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
