#!/usr/bin/env python3
"""
LPBF process-window map (screening only, not validation).

Evaluates the frozen Rosenthal-screening melt-pool model plus compose_verdict on a P x v grid for one
alloy and one (beam, layer, hatch, preheat) setting, exactly as the Bayesian optimizer's objective does
(calculate_meltpool_physics -> compose_verdict, no clamping, no fallback alloy). The grid is overlaid with
published single-track measurements (geometry only, never print outcomes), each of which also gets a model
verdict computed at its own P/v with the request's settings.

Nothing here re-decides printability: verdicts, gates and reasons are the compose_verdict output verbatim
(Tang bump, 2026-10-27: inconclusive when geometry is not resolved or a verdict input is null; risky when the Tang
overlap index on modelled geometry is above 1.0 or in keyhole mode; otherwise printable, a screening result that does
not establish fusion adequacy; never do-not-print; the literature box, balling, the level 30, the Tang margin and
downskin are advisories). Each cell carries tangIndex. Results stay screening only (experimentalValidation false).
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import lpbf_process_window_cache as _cache
from lpbf_job_cache import BUILD_JOB_MODEL_ID, BUILD_JOB_SOLVER_REVISION

REPO_ROOT = Path(__file__).resolve().parent.parent
NIST_TABLE4_PATH = REPO_ROOT / "data" / "benchmark" / "nist-amb2022-03-optical" / "table4-aggregate-v2.json"

MAX_POWER_W = 1500.0
MAX_SPEED_MM_S = 10000.0
MIN_AXIS_POINTS = 2
MAX_AXIS_POINTS = 15
DEFAULT_AXIS_POINTS = 11
MAX_CELLS = 225
DEFAULT_BEAM_TOLERANCE_PCT = 10.0
DEFAULT_RANGE_LOW_FACTOR = 0.5
DEFAULT_RANGE_HIGH_FACTOR = 1.5
VERDICTS = ("printable", "risky", "do-not-print", "inconclusive")

EVIDENCE_STATEMENT = (
    "Screening only. Verdicts come from the frozen Rosenthal melt-pool screening model and compose_verdict at "
    "flat-plate absorptivity; they are not an experimental validation, a qualified process window or a print "
    "recommendation. Overlaid measurements are published single-track geometry, not print outcomes."
)
NO_SOURCE_NOTE = "No measurement dataset for this alloy is wired into the repository; no overlay is shown."

# alloy id -> datasets whose published measurements may be overlaid. Lane (IN625) is registered under its own
# alloy: IN625 is not one of the four supported alloys, so it is never selected by a supported request.
DATASET_REGISTRY: Dict[str, List[Dict[str, str]]] = {
    "ss316l": [{"id": "hofmann-316l-2026", "label": "Hofmann 2026 (316L single tracks)", "loader": "load_hofmann_316l"}],
    "ti6al4v": [{"id": "totis-ti64-2021", "label": "Totis 2021 (Ti-6Al-4V single tracks)", "loader": "load_totis_ti64"}],
    "in718": [
        {"id": "ku-leuven-in718-2021", "label": "KU Leuven 2021 (IN718, dimensions unit-unresolved)",
         "loader": "load_ku_leuven_in718"},
        {"id": "nist-amb2022-03-table4", "label": "NIST AMB2022-03 Table 4 (IN718 bare plate)", "loader": "@nist-table4"},
    ],
    "alsi10mg": [],
    "in625": [{"id": "lane-in625-2020", "label": "Lane 2020 (IN625 bare plate)", "loader": "load_lane_in625"}],
}


def _refuse(kind: str, message: str) -> Dict[str, Any]:
    return {"success": False, "errorKind": kind, "error": message}


def _finite(value: Any) -> Any:
    """JSON-safe number: non-finite floats become None (never NaN/Infinity in the response)."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _num(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number (got {value!r}).")
    x = float(value)
    if not math.isfinite(x):
        raise ValueError(f"{name} must be finite (got {value!r}).")
    return x


def _axis_from_request(raw: Any, name: str, cap: float, unit: str) -> List[float]:
    if not isinstance(raw, list):
        raise ValueError(f"{name} must be an array of numbers.")
    if not (MIN_AXIS_POINTS <= len(raw) <= MAX_AXIS_POINTS):
        raise ValueError(f"{name} needs {MIN_AXIS_POINTS} to {MAX_AXIS_POINTS} values (got {len(raw)}); it is not truncated or padded.")
    values = [_num(v, f"{name}[{i}]") for i, v in enumerate(raw)]
    for i, v in enumerate(values):
        if not v > 0:
            raise ValueError(f"{name}[{i}] must be > 0 {unit} (got {v:g}).")
        if v > cap:
            raise ValueError(f"{name}[{i}] must be <= {cap:g} {unit} (got {v:g}); it is not clamped.")
    if any(b <= a for a, b in zip(values, values[1:])):
        raise ValueError(f"{name} must be strictly increasing (min < max, no duplicates); it is not re-sorted.")
    return values


def _linspace(lo: float, hi: float, n: int) -> List[float]:
    return [round(lo + (hi - lo) * i / (n - 1), 2) for i in range(n)]


def validate_request(data: Any) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Return (normalized, None) or (None, refusal). Mirrors the optimizer: strict numbers, no fallbacks."""
    from four_alloy_materials import LITERATURE_PV_WINDOWS, resolve_alloy_id, thermal_props
    if not isinstance(data, dict):
        return None, _refuse("validation", "Request body must be a JSON object.")
    alloy_id = data.get("alloyId")
    if alloy_id is None or str(alloy_id).strip() == "":
        return None, _refuse("validation", "alloyId is required; no default alloy is assumed.")
    resolved = resolve_alloy_id(alloy_id)
    if resolved is None or resolved not in LITERATURE_PV_WINDOWS:
        return None, _refuse(
            "validation",
            f"Unknown alloy '{alloy_id}': not resolvable by four_alloy_materials; no fallback alloy is used.")
    try:
        beam = _num(data.get("beamDiameter_um"), "beamDiameter_um")
        layer = _num(data.get("layer_um"), "layer_um")
        hatch = _num(data.get("hatch_um"), "hatch_um")
        preheat = _num(data.get("preheatTemp_C"), "preheatTemp_C")
        tol = _num(data.get("overlayBeamTolerance_pct", DEFAULT_BEAM_TOLERANCE_PCT), "overlayBeamTolerance_pct")
    except ValueError as e:
        return None, _refuse("validation", str(e))
    for name, value in (("beamDiameter_um", beam), ("layer_um", layer), ("hatch_um", hatch)):
        if not value > 0:
            return None, _refuse("validation", f"{name} must be > 0 (got {value:g}).")
    solidus = float(thermal_props(resolved)["solidus_C"])
    if not (0 <= preheat < solidus):
        return None, _refuse(
            "validation", f"preheatTemp_C must be finite, >= 0 and below the {resolved} solidus ({solidus:g} C).")
    if not (0 <= tol <= 100):
        return None, _refuse("validation", f"overlayBeamTolerance_pct must be between 0 and 100 (got {tol:g}).")

    box = LITERATURE_PV_WINDOWS[resolved]
    default_p = (DEFAULT_RANGE_LOW_FACTOR * box["powerMin_W"], DEFAULT_RANGE_HIGH_FACTOR * box["powerMax_W"])
    default_v = (DEFAULT_RANGE_LOW_FACTOR * box["speedMin_mm_s"], DEFAULT_RANGE_HIGH_FACTOR * box["speedMax_mm_s"])
    try:
        if data.get("powers") is None:
            powers = _linspace(default_p[0], default_p[1], DEFAULT_AXIS_POINTS)
            power_basis = "default"
        else:
            powers = _axis_from_request(data["powers"], "powers", MAX_POWER_W, "W")
            power_basis = "request"
        if data.get("speeds") is None:
            speeds = _linspace(default_v[0], default_v[1], DEFAULT_AXIS_POINTS)
            speed_basis = "default"
        else:
            speeds = _axis_from_request(data["speeds"], "speeds", MAX_SPEED_MM_S, "mm/s")
            speed_basis = "request"
    except ValueError as e:
        return None, _refuse("validation", str(e))
    if len(powers) * len(speeds) > MAX_CELLS:
        return None, _refuse("validation", f"At most {MAX_CELLS} cells are allowed (got {len(powers) * len(speeds)}).")
    normalized = {
        "alloyId": resolved, "beamDiameter_um": beam, "layer_um": layer, "hatch_um": hatch,
        "preheatTemp_C": preheat, "overlayBeamTolerance_pct": tol, "powers": powers, "speeds": speeds,
    }
    context = {
        "literatureBox": dict(box),
        "rangeBasis": {
            "power": {"basis": power_basis, "min_W": powers[0], "max_W": powers[-1], "n": len(powers),
                      "rule": (f"{DEFAULT_RANGE_LOW_FACTOR} x literature-box minimum to {DEFAULT_RANGE_HIGH_FACTOR} x maximum "
                               "(LITERATURE_PV_WINDOWS)") if power_basis == "default" else "request"},
            "speed": {"basis": speed_basis, "min_mm_s": speeds[0], "max_mm_s": speeds[-1], "n": len(speeds),
                      "rule": (f"{DEFAULT_RANGE_LOW_FACTOR} x literature-box minimum to {DEFAULT_RANGE_HIGH_FACTOR} x maximum "
                               "(LITERATURE_PV_WINDOWS)") if speed_basis == "default" else "request"},
        },
    }
    normalized["_context"] = context
    return normalized, None


def _evaluate(resolved: str, power: float, speed: float, norm: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Exactly the optimizer's _obj body: calculate_meltpool_physics then compose_verdict."""
    import lpbf_build_job_solver as build_job
    import lpbf_thermal_solver as thermal_solver
    th = thermal_solver.calculate_meltpool_physics(
        material_name=resolved,
        laser_power_W=float(power),
        scan_speed_mm_s=float(speed),
        beam_diameter_um=norm["beamDiameter_um"],
        preheat_temp_C=norm["preheatTemp_C"],
        layer_thickness_um=norm["layer_um"],
        hatch_spacing_um=norm["hatch_um"],
        laser_wavelength="IR_1064nm",
        include_process_map=False)
    vd = build_job.compose_verdict(th, resolved)
    if vd.get("verdict") not in VERDICTS:
        raise ValueError(f"unknown verdict {vd.get('verdict')!r} from compose_verdict")
    return th, vd


def _cell(resolved: str, i_p: int, i_v: int, power: float, speed: float, norm: Dict[str, Any]) -> Dict[str, Any]:
    base = {"iP": i_p, "iV": i_v, "power_W": power, "speed_mm_s": speed}
    try:
        th, vd = _evaluate(resolved, power, speed, norm)
        geo = th.get("meltPoolGeometry") or {}
        pp = th.get("processParameters") or {}
        dd = th.get("defectDiagnostics") or {}
        balling = dd.get("ballingScreen") if isinstance(dd.get("ballingScreen"), dict) else {}
        extent_status = str(vd.get("extentStatus") or geo.get("extentStatus") or "not-reported")
        computed = extent_status == "computed"
        cell = {
            **base,
            "verdict": vd["verdict"],
            "headline": vd["headline"],
            "dominantGate": vd.get("dominantGate"),
            "blockingGates": list(vd.get("blockingGates") or []),
            "riskGates": list(vd.get("riskGates") or []),
            "advisoryGates": list(vd.get("advisoryGates") or []),
            "unavailableGates": list(vd.get("unavailableGates") or []),
            "tangIndex": _finite((vd.get("lofGeometry") or {}).get("tangIndex")) if computed else None,
            "reasons": list(vd.get("reasons") or []),
            "extentStatus": extent_status,
            "insideLiteratureBox": bool((vd.get("literatureWindow") or {}).get("inside")),
            "normalizedEnthalpy": _finite(pp.get("normalizedEnthalpy")),
            "ballingBand": balling.get("band"),
            "width_um": _finite(geo.get("width_um")) if computed else None,
            "depth_um": _finite(geo.get("depth_um")) if computed else None,
            "error": None,
        }
        return {"cell": cell, "absorptionModel": pp.get("absorptionModel")}
    except Exception as e:  # a failed cell is an error, never coloured as a verdict
        message = f"{type(e).__name__}: {e}"
        return {"cell": {
            **base, "verdict": "error", "headline": f"Solver error: {message}", "dominantGate": None,
            "blockingGates": [], "riskGates": [], "advisoryGates": [], "unavailableGates": [], "tangIndex": None,
            "reasons": [],
            "extentStatus": None, "insideLiteratureBox": None, "normalizedEnthalpy": None, "ballingBand": None,
            "width_um": None, "depth_um": None, "error": message}, "absorptionModel": None}


def _grid_advisories(cells: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Parameter-independent gates listed once: advisory in every evaluated cell (older payloads), or since P7a
    not evaluated in every cell (recoater and distortion: no sourced stress model, listed in unavailableGates)."""
    from lpbf_build_job_solver import ADVISORY_GATES, PARAMETER_INDEPENDENT_ADVISORY_NOTE, STRESS_GATES_NOT_EVALUATED_NOTE
    live = [c for c in cells if c["verdict"] != "error"]
    out = []
    if not live:
        return out
    for gate in ADVISORY_GATES:
        if all(gate in c["advisoryGates"] for c in live):
            out.append({"gate": gate, "note": PARAMETER_INDEPENDENT_ADVISORY_NOTE, "cells": len(live)})
            for c in live:
                c["advisoryGates"] = [g for g in c["advisoryGates"] if g != gate]
        elif all(gate in c["unavailableGates"] for c in live):
            out.append({"gate": gate, "note": STRESS_GATES_NOT_EVALUATED_NOTE, "cells": len(live)})
    return out


# ---------------------------------------------------------------------------------------------------------
# Measurement overlay
# ---------------------------------------------------------------------------------------------------------
def _load_nist_table4() -> Dict[str, Any]:
    from lpbf_nist_in718_comparison import RESULTS_URL, TRANSCRIPTION_ARTIFACT_SHA256
    raw = NIST_TABLE4_PATH.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != TRANSCRIPTION_ARTIFACT_SHA256:
        raise ValueError(f"NIST Table 4 transcription sha256 mismatch: {digest} != {TRANSCRIPTION_ARTIFACT_SHA256}")
    doc = json.loads(raw.decode("utf-8"))
    exp = doc.get("experiment") or {}
    rows = []
    for c in doc["cases"]:
        rows.append({
            "dataset": "nist-amb2022-03-table4", "rowId": f"nist-amb2022-03-case-{c['caseNumber']}",
            "material": doc.get("material"), "power_W": float(c["laserPower_W"]),
            "speed_mm_s": float(c["scanSpeed_mm_s"]), "beamDiameter_um": float(c["beamDiameterD4sigma_um"]),
            "layer_um": 0.0, "preheat_C": exp.get("substrateAndChamberTemperature_C"),
            "width_um": float(c["widthMean_um"]), "depth_um": float(c["depthMean_um"]),
            "widthSigma_um": float(c["widthStdDev_um"]), "depthSigma_um": float(c["depthStdDev_um"]),
        })
    prov = {
        "id": "nist-amb2022-03-table4", "doi": doc.get("doi"), "url": RESULTS_URL, "license": "NIST publication (transcribed values)",
        "citation": (f"{doc.get('publishedResultsLocation')}; means of {doc['measurement']['countPerCondition']} "
                     "ex-situ optical cross-sections per condition; local transcription, not NIST raw data."),
        "material": doc.get("material"),
        "caveats": [doc.get("transcriptionNote", ""), doc["measurement"].get("uncertainty", ""),
                    "Bare plate, no powder layer; beam diameter is D4sigma."],
        "fileSha256": digest,
    }
    return {"rows": rows, "provenance": prov}


def _run_loader(spec: Dict[str, str]) -> Dict[str, Any]:
    if spec["loader"] == "@nist-table4":
        return _load_nist_table4()
    import lpbf_public_datasets
    return getattr(lpbf_public_datasets, spec["loader"])()


def _point_record(row: Dict[str, Any], verdict: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "datasetId": row["dataset"], "rowId": row["rowId"], "power_W": row["power_W"], "speed_mm_s": row["speed_mm_s"],
        "beamDiameter_um": row.get("beamDiameter_um"), "layer_um": row.get("layer_um"), "preheat_C": row.get("preheat_C"),
        "measuredWidth_um": _finite(row.get("width_um")), "measuredDepth_um": _finite(row.get("depth_um")),
        "modelVerdict": verdict,
    }


def _model_verdict(resolved: str, power: float, speed: float, norm: Dict[str, Any], memo: Dict[Tuple[float, float], Dict[str, Any]]) -> Dict[str, Any]:
    key = (power, speed)
    if key not in memo:
        out = _cell(resolved, -1, -1, power, speed, norm)["cell"]
        memo[key] = {
            "verdict": out["verdict"], "dominantGate": out["dominantGate"], "extentStatus": out["extentStatus"],
            "modelWidth_um": out["width_um"], "modelDepth_um": out["depth_um"], "error": out["error"]}
    return dict(memo[key])


def _overlay(resolved: str, norm: Dict[str, Any]) -> Dict[str, Any]:
    tol = norm["overlayBeamTolerance_pct"]
    beam = norm["beamDiameter_um"]
    lo_b, hi_b = beam * (1 - tol / 100.0), beam * (1 + tol / 100.0)
    p_lo, p_hi, v_lo, v_hi = norm["powers"][0], norm["powers"][-1], norm["speeds"][0], norm["speeds"][-1]
    specs = DATASET_REGISTRY.get(resolved, [])
    memo: Dict[Tuple[float, float], Dict[str, Any]] = {}
    datasets = []
    for spec in specs:
        entry = {"id": spec["id"], "label": spec["label"], "status": "available", "reason": None, "points": [],
                 "nRows": 0, "nShown": 0, "hiddenByBeam": 0, "hiddenNoBeam": 0, "hiddenOutsideRange": 0}
        try:
            loaded = _run_loader(spec)
            prov = loaded["provenance"]
            entry.update(material=prov.get("material"), doi=prov.get("doi"), url=prov.get("url"),
                         license=prov.get("license"), citation=prov.get("citation"),
                         caveats=list(prov.get("caveats") or []))
            rows = loaded["rows"]
            entry["nRows"] = len(rows)
            for row in rows:
                b = row.get("beamDiameter_um")
                if b is None:
                    entry["hiddenNoBeam"] += 1
                    continue
                if not (lo_b <= float(b) <= hi_b):
                    entry["hiddenByBeam"] += 1
                    continue
                if not (p_lo <= row["power_W"] <= p_hi and v_lo <= row["speed_mm_s"] <= v_hi):
                    entry["hiddenOutsideRange"] += 1
                    continue
                entry["points"].append(_point_record(row, _model_verdict(resolved, row["power_W"], row["speed_mm_s"], norm, memo)))
            entry["nShown"] = len(entry["points"])
        except Exception as e:  # only this dataset becomes unavailable
            entry.update(status="unavailable", reason=f"{type(e).__name__}: {e}", points=[], nShown=0)
        datasets.append(entry)
    return {
        "beamTolerance_pct": tol, "beamWindow_um": [round(lo_b, 3), round(hi_b, 3)],
        "note": None if specs else NO_SOURCE_NOTE, "datasets": datasets,
        "measurementKind": "published single-track geometry (width/depth), not print outcomes",
    }


# ---------------------------------------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------------------------------------
def run_process_window(data: Any) -> Dict[str, Any]:
    t0 = time.time()
    norm, refusal = validate_request(data)
    if refusal is not None:
        return refusal
    context = norm.pop("_context")
    resolved = norm["alloyId"]
    impl_hash = _cache.implementation_hash()
    revision = BUILD_JOB_SOLVER_REVISION
    key = _cache.make_key(norm, revision, impl_hash)
    cached = _cache.get(key)
    if cached is not None:
        cached["cache"] = {"hit": True, "key": key, "scope": "python-worker-process"}
        cached["originalComputeMs"] = cached.get("computeMs")
        cached["computeMs"] = round((time.time() - t0) * 1000.0, 1)
        return cached

    results = [_cell(resolved, i, j, p, v, norm)
               for i, p in enumerate(norm["powers"]) for j, v in enumerate(norm["speeds"])]
    cells = [r["cell"] for r in results]
    absorption = next((r["absorptionModel"] for r in results if r["absorptionModel"]), None)
    counts = {k: 0 for k in (*VERDICTS, "error")}
    for c in cells:
        counts[c["verdict"]] += 1
    advisories = _grid_advisories(cells)
    response = {
        "success": True,
        "engine": "lpbf_process_window",
        "alloyId": resolved,
        "request": {k: norm[k] for k in ("alloyId", "beamDiameter_um", "layer_um", "hatch_um", "preheatTemp_C",
                                          "overlayBeamTolerance_pct")},
        "grid": {"powers_W": norm["powers"], "speeds_mm_s": norm["speeds"], "nP": len(norm["powers"]),
                 "nV": len(norm["speeds"]), "nCells": len(cells), "literatureBox": context["literatureBox"],
                 "rangeBasis": context["rangeBasis"]},
        "cells": cells,
        "counts": counts,
        "gridAdvisories": advisories,
        "overlay": _overlay(resolved, norm),
        "evidence": {"kind": "screening-only", "experimentalValidation": False, "statement": EVIDENCE_STATEMENT},
        "provenance": {"modelId": BUILD_JOB_MODEL_ID, "solverRevision": revision,
                       "implementationHash": impl_hash, "absorptionModel": absorption},
        "cache": {"hit": False, "key": key, "scope": "python-worker-process"},
    }
    response["computeMs"] = round((time.time() - t0) * 1000.0, 1)
    # Only complete results are cached: a solver error or an unavailable dataset may be transient.
    complete = counts["error"] == 0 and all(d["status"] == "available" for d in response["overlay"]["datasets"])
    response["cache"]["stored"] = complete
    if complete:
        _cache.put(key, response)
    return response


def main() -> None:
    raw = sys.stdin.read().strip()
    if not raw:
        print(json.dumps(_refuse("validation", "Empty payload.")))
        return
    try:
        data = json.loads(raw)
    except Exception as e:
        print(json.dumps(_refuse("validation", f"Invalid JSON: {e}")))
        return
    # Solver imports (e.g. NVIDIA Warp) print banners to stdout; keep stdout for the one JSON document only.
    with contextlib.redirect_stdout(sys.stderr):
        try:
            result = run_process_window(data)
        except Exception as e:  # unexpected engine failure still yields exactly one JSON document
            result = _refuse("engine", f"{type(e).__name__}: {e}")
    print(json.dumps(result, allow_nan=False))


if __name__ == "__main__":
    main()
