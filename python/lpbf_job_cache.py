#!/usr/bin/env python3
"""
In-process hash cache for LPBF build-job results.

Same effective material + process + complete mesh + flags → hit.
Survives across IPC calls within one Python worker process.
"""

from __future__ import annotations

import copy
import hashlib
import json
import time
from typing import Any, Dict, Optional, Tuple

# key -> (stored_at_monotonic, result_dict)
_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_HITS = 0
_MISSES = 0
_MAX_ENTRIES = 64

# Increment when build-job solver behavior changes so a warm worker cannot
# return results produced by an earlier implementation for identical inputs.
BUILD_JOB_SOLVER_REVISION = "lpbf-build-job-p1-sourced-v21"
BUILD_JOB_MODEL_ID = "rosenthal-screening-v1"


def cache_stats() -> Dict[str, Any]:
    return {
        "entries": len(_CACHE),
        "hits": _HITS,
        "misses": _MISSES,
        "hitRate": round(_HITS / max(1, _HITS + _MISSES), 4),
    }


def clear_cache() -> None:
    global _HITS, _MISSES
    _CACHE.clear()
    _HITS = 0
    _MISSES = 0


def mesh_fingerprint(triangles: Any, cad_name: str = "", native_count: Any = None) -> Optional[str]:
    if not triangles:
        return None
    h = hashlib.sha256()
    n = len(triangles)
    h.update(str(n).encode("utf-8"))
    if native_count is not None:
        h.update(str(native_count).encode("utf-8"))
    h.update((cad_name or "").encode("utf-8"))
    # Every effective triangle matters: interior-only edits can change slices.
    for tri in triangles:
        h.update(json.dumps(tri, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8"))
    return h.hexdigest()


def build_cache_key(data: Dict[str, Any]) -> str:
    """Canonical SHA-256 hex (full) from process + flags + mesh fingerprint."""
    enable_uq = bool(data.get("enableUq", False))
    include_amb = bool(data.get("includeAmbench", False))
    defects = data.get("defectSqrtAreas_um")
    if isinstance(defects, list):
        defects_norm = [round(float(x), 6) for x in defects]
    else:
        defects_norm = None
    build_job_identity = data.get("buildJobIdentity")
    build_job_identity_sha256 = (
        build_job_identity.get("sha256") if isinstance(build_job_identity, dict) else None
    )
    payload = {
        "alloyId": data.get("alloyId") or "in718",
        "thermalMaterial": data.get("thermalMaterial"),
        "slicerMaterial": data.get("slicerMaterial"),
        "materialPropertySha256": data.get("materialPropertySha256"),
        "materialAuthorityRevisionSha256": data.get("materialAuthorityRevisionSha256"),
        "buildJobIdentitySha256": build_job_identity_sha256,
        "amBenchMaterialPropertySha256": data.get("amBenchMaterialPropertySha256") if include_amb else None,
        "P": round(float(data.get("laserPower_W", 0)), 6),
        "v": round(float(data.get("scanSpeed_mm_s", data.get("scanSpeed_mms", 0))), 6),
        "h": round(float(data.get("hatchSpacing_um", 0)), 6),
        "t": round(float(data.get("layerThickness_um", 0)), 6),
        "d": round(float(data.get("beamDiameter_um", 0)), 6),
        "preheat": round(float(data.get("preheatTemp_C", 0)), 6),
        "wavelength": data.get("laserWavelength", "IR_1064nm"),
        "seed": int(data.get("processSeed", data.get("seed", 42))),
        "strategy": data.get("scanStrategy", "stripe"),
        "stripe": round(float(data.get("stripeWidth_mm", 5.0)), 6),
        "rotation": round(float(data.get("scanRotation_deg", 67.0)), 6),
        "dwell": round(float(data.get("hatchDwell_ms", 0.0)), 6),
        "incline": round(float(data.get("inclineAngle_deg", data.get("surfaceIncline_deg", 0.0) or 0.0)), 6),
        "downskin": data.get("downskinOverhang_deg"),
        "preset": data.get("preset", "nozzle"),
        "cad": data.get("cadAssetName", ""),
        "meshFp": mesh_fingerprint(
            data.get("customTriangles"),
            str(data.get("cadAssetName") or ""),
            data.get("triangleCountNative"),
        ),
        "maxTris": int(data.get("maxTriangles") or 12000),
        "recoatTimePerLayer_s": data.get("recoatTimePerLayer_s", 9.0),
        "enableUq": enable_uq,
        "uqSamples": int(data.get("uqSamples", 64)) if enable_uq else 0,
        "includeAmbench": include_amb,
        "defects": defects_norm,
        "hv": data.get("hardness_HV"),
        "ctThresh": data.get("ctDetectionThreshold_um"),
        "gitSha": data.get("gitSha"),
        "solverRevision": BUILD_JOB_SOLVER_REVISION,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def cache_get(key: str) -> Optional[Dict[str, Any]]:
    global _HITS, _MISSES
    entry = _CACHE.get(key)
    if entry is None:
        _MISSES += 1
        return None
    stored_at, result = entry
    _HITS += 1
    age_ms = round((time.monotonic() - stored_at) * 1000.0, 1)
    out = copy.deepcopy(result)
    out["cache"] = {
        "hit": True,
        "key": key[:16],
        "ageMs": age_ms,
        "stats": cache_stats(),
    }
    return out


def cache_put(key: str, result: Dict[str, Any]) -> Dict[str, Any]:
    if len(_CACHE) >= _MAX_ENTRIES:
        # Drop oldest
        oldest_key = min(_CACHE.items(), key=lambda kv: kv[1][0])[0]
        del _CACHE[oldest_key]
    stored = copy.deepcopy(result)
    # Strip prior cache meta before storing
    stored.pop("cache", None)
    _CACHE[key] = (time.monotonic(), stored)
    out = copy.deepcopy(stored)
    out["cache"] = {
        "hit": False,
        "key": key[:16],
        "ageMs": 0.0,
        "stats": cache_stats(),
    }
    return out
