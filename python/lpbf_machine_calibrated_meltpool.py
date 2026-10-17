#!/usr/bin/env python3
"""Machine-calibrated melt-pool depth (screening, user data): JSON CLI behind
POST /api/python/lpbf-machine-calibrated-meltpool and GET /api/python/lpbf-machine-calibration/status.

The user's own tracks were fitted by ``python/tools/lpbf_machine_calibration.py fit`` into an artefact under
``.runtime/machine-calibration/<user-id>/machine-calibration.json``. This module only reads those artefacts (it never
writes, never fits, never opens a path taken from a request): an artefact is selected by its ``machineCalibrationId``
and found by scanning the artefact root, so a request cannot point the server at any other file.

Input keys mirror ``lpbf_thermal_solver.py`` (material, laserPower_W, scanSpeed_mm_s, beamDiameter_um, preheatTemp_C,
layerThickness_um, hatchSpacing_um, laserWavelength, heatSource, sulfur_ppm, absorptionModel, thermalSliceBackend) plus
``"machineCalibration": "<machineCalibrationId>"``. The output is the contract of
``lpbf_machine_calibration.apply_machine_calibration``: the unchanged screening result and a ``machineCalibrated``
block. The block is "empirical machine offset" language only (never an absorptivity), and it carries the evidence kind
"calibrated-simulation" with the scope "this machine, user data" only when the gate passed and every one of the user's
tracks has the method fields filled; otherwise the value is "screening-only" and the block lists the missing fields.
Nothing here says "validated"; ``experimentalValidation`` is false. A missing, stale or tampered artefact never fails
the request: the screening result is returned with ``machineCalibrated.available = false`` and the reason.

``--status`` (or the JSON input ``{"action": "status"}``) prints the artefacts found and the eligible cells without
running a solver.
"""

from __future__ import annotations

import contextlib
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import lpbf_machine_calibration as mc
from lpbf_machine_calibration_config import MACHINE_CALIBRATION_CONFIG, config_sha256

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTEFACT_NAME = "machine-calibration.json"
ROOT_ENV = "LPBF_MACHINE_CALIBRATION_DIR"
ID_PATTERN = re.compile(r"^mc-[0-9a-f]{12}$")
ENGINE = "lpbf_machine_calibrated_meltpool"
SCHEMA = "lpbf-machine-calibrated-meltpool-1"
KERNELS = ("rosenthal", "eagar-tsai", "goldak")
PRIVACY = ("Your measurements stay on this computer (.runtime/machine-calibration/), are not sent anywhere, do not "
           "change the published-track calibration or the scorecard, and do not become validation evidence.")
POSITIVE_KEYS = ("laserPower_W", "scanSpeed_mm_s", "beamDiameter_um", "layerThickness_um", "hatchSpacing_um")


def artefact_root() -> Path:
    override = os.environ.get(ROOT_ENV)
    return Path(override) if override else REPO_ROOT / ".runtime" / "machine-calibration"


def _refuse(message: str, kind: str = "validation") -> Dict[str, Any]:
    return {"success": False, "errorKind": kind, "error": message}


# --------------------------------------------------------------------------------------------------------------
# discovery (read only)
# --------------------------------------------------------------------------------------------------------------
def _artefact_paths(root: Path) -> List[Path]:
    if not root.is_dir():
        return []
    return sorted(p for p in root.glob(f"*/{ARTEFACT_NAME}") if p.is_file())


def _raw_id(path: Path) -> Optional[str]:
    """Id of an artefact that failed verification, for display only. Never trusted for serving."""
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    mcid = doc.get("machineCalibrationId") if isinstance(doc, dict) else None
    return mcid if isinstance(mcid, str) and ID_PATTERN.match(mcid) else None


def _summary(art: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "machineCalibrationId": art["machineCalibrationId"], "userSourceId": art["userSourceId"],
        "material": art["material"], "generatedAt": art["generatedAt"], "nTracks": art["nTracks"],
        "contentSha256": art["contentSha256"], "state": "ready", "reason": None, "experimentalValidation": False,
        "cells": [{"kernel": c["kernel"], "quantity": c["quantity"], "status": c["status"],
                   "evidenceKind": c["evidenceKind"], "evidenceScope": c["evidenceScope"],
                   "evidenceLabel": c["evidenceLabel"], "missingMethodFields": c["missingMethodFields"],
                   "reasonText": c["reasonText"]} for c in art["cells"]],
    }


def discover(root: Optional[Path] = None, *, expected_impl_hash: Optional[str] = None
             ) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """Return (summaries, verified artefacts by id). Stale and invalid artefacts appear in the summaries with a reason
    and are never served."""
    root = artefact_root() if root is None else Path(root)
    summaries: List[Dict[str, Any]] = []
    verified: Dict[str, Dict[str, Any]] = {}
    for path in _artefact_paths(root):
        art, info = mc.try_load_machine_calibration(path, expected_impl_hash=expected_impl_hash)
        if art is not None:
            if art["machineCalibrationId"] in verified:
                summaries.append({"machineCalibrationId": art["machineCalibrationId"], "state": "invalid",
                                  "reason": "duplicate machineCalibrationId; the first artefact is used", "cells": []})
                continue
            verified[art["machineCalibrationId"]] = art
            summaries.append(_summary(art))
        else:
            summaries.append({"machineCalibrationId": _raw_id(path), "state": "stale" if info["stale"] else "invalid",
                              "reason": info["reason"], "cells": []})
    return summaries, verified


MACHINE_WIDTH_TEXT = ("This machine calibration estimates depth only. A width calibration with suitable measurements is "
                      "needed to estimate width.")


def status(root: Optional[Path] = None, *, expected_impl_hash: Optional[str] = None) -> Dict[str, Any]:
    summaries, _ = discover(root, expected_impl_hash=expected_impl_hash)
    ready = [s for s in summaries if s["state"] == "ready"]
    state = "ready" if ready else ("none" if not summaries else "unavailable")
    cfg = MACHINE_CALIBRATION_CONFIG
    return {
        "success": True, "engine": ENGINE, "schema": SCHEMA, "status": state, "artefacts": summaries,
        "configSha256": config_sha256(cfg), "eligibleCells": cfg["eligibleCells"],
        "notEligibleReasons": cfg["notEligibleReasons"], "methodFieldsRequired": cfg["methodFields"]["required"],
        "evidence": cfg["evidence"], "experimentalValidation": False, "privacy": PRIVACY,
        "note": ("empirical machine offset fitted to the user's own tracks; it is not an absorptivity and not a "
                 "validation. Fit with python/tools/lpbf_machine_calibration.py."),
    }


# --------------------------------------------------------------------------------------------------------------
# run
# --------------------------------------------------------------------------------------------------------------
def _validate(data: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(data, dict):
        return _refuse("The payload must be a JSON object.")
    mcid = data.get("machineCalibration")
    if not isinstance(mcid, str) or not ID_PATTERN.match(mcid):
        from lpbf_request_errors import refusal
        return refusal("MACHINE_CALIBRATION_REQUIRED", "machineCalibration",
                       "Select a machine calibration before running this model. "
                       "If none is available, import and fit your machine measurements in Machine calibration.")
    material = data.get("material")
    if not isinstance(material, str) or not material.strip():
        return _refuse("material is required (for example '316L Stainless Steel'); no substitute alloy is used.")
    kernel = data.get("heatSource") or data.get("heat_source") or "rosenthal"
    if kernel not in KERNELS:
        return _refuse(f"heatSource must be one of {list(KERNELS)}.")
    for key in POSITIVE_KEYS:
        if key in data:
            v = data[key]
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0:
                return _refuse(f"{key} must be a finite number above 0.")
    if "preheatTemp_C" in data:
        v = data["preheatTemp_C"]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= -273.15:
            return _refuse("preheatTemp_C must be a finite number above -273.15.")
    return None


def run(data: Dict[str, Any], *, root: Optional[Path] = None, solver: Optional[Callable[..., Dict[str, Any]]] = None,
        expected_impl_hash: Optional[str] = None) -> Dict[str, Any]:
    bad = _validate(data)
    if bad is not None:
        return bad
    data = dict(data)
    if "scanSpeed_mm_s" not in data and "scanSpeed_mms" in data:
        data["scanSpeed_mm_s"] = data["scanSpeed_mms"]
        if not (isinstance(data["scanSpeed_mm_s"], (int, float)) and math.isfinite(data["scanSpeed_mm_s"])
                and data["scanSpeed_mm_s"] > 0):
            return _refuse("scanSpeed_mms must be a finite number above 0.")
    kernel = data.get("heatSource") or data.get("heat_source") or "rosenthal"
    summaries, verified = discover(root, expected_impl_hash=expected_impl_hash)
    art = verified.get(data["machineCalibration"])
    out = mc.apply_machine_calibration(data, kernel, art, solver=solver)
    if art is None:
        match = next((s for s in summaries if s.get("machineCalibrationId") == data["machineCalibration"]), None)
        out["machineCalibrated"]["machineCalibrationId"] = data["machineCalibration"]
        out["machineCalibrated"]["reasonText"] = [
            (match["reason"] if match else "machine calibration artefact not found on this computer")]
        out["machineCalibrated"]["stale"] = bool(match and match["state"] == "stale")
    out.update({"success": True, "engine": ENGINE, "schema": SCHEMA, "privacy": PRIVACY})
    # Group 9: the machine model corrects depth only; width needs its own fit and gate.
    out["machineCalibrated"]["widthText"] = MACHINE_WIDTH_TEXT
    return out


def build_job_block(machine_calibration_id: Any, thermal_material: str, inputs: Dict[str, Any], *,
                    screening_depth_um: Optional[float] = None, root: Optional[Path] = None,
                    solver: Optional[Callable[..., Dict[str, Any]]] = None,
                    expected_impl_hash: Optional[str] = None) -> Dict[str, Any]:
    """The ``machineCalibrated`` block of a Build Job result. Never raises, never feeds the verdict: it is reported
    next to the screening value. Computed on the frozen Rosenthal flat-plate path with the default material properties,
    which is the path the artefact was fitted on."""
    try:
        if not isinstance(machine_calibration_id, str) or not ID_PATTERN.match(machine_calibration_id):
            raise ValueError("machineCalibration must be a machine calibration id like 'mc-0123456789ab'")
        _, verified = discover(root, expected_impl_hash=expected_impl_hash)
        art = verified.get(machine_calibration_id)
        out = mc.apply_machine_calibration({**inputs, "material": thermal_material}, "rosenthal", art, solver=solver)
        block = out["machineCalibrated"]
        if art is None:
            block["machineCalibrationId"] = machine_calibration_id
            block["reasonText"] = ["machine calibration artefact not found, stale or invalid on this computer"]
    except Exception as exc:  # the Build Job result must survive any problem here
        block = {"available": False, "quantity": "depth", "depth_um": None, "depthBand_um": None, "width_um": None,
                 "evidenceKind": MACHINE_CALIBRATION_CONFIG["evidence"]["screening"], "evidenceScope": None,
                 "missingMethodFields": [], "reasons": [], "reasonText": [f"machine calibration not applied: {exc}"],
                 "usedForBuildJobVerdict": False}
    block["usedForBuildJobVerdict"] = False
    block["screeningDepth_um"] = screening_depth_um
    block["basis"] = ("frozen Rosenthal flat-plate depth at the default absorptivity and default material properties, "
                      "times the empirical machine offset; the Build Job verdict uses the screening geometry only")
    block["experimentalValidation"] = False
    return block


# --------------------------------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------------------------------
def _read_input() -> Dict[str, Any]:
    if len(sys.argv) > 1 and sys.argv[1].strip().startswith("{"):
        return json.loads(sys.argv[1])
    if not sys.stdin.isatty():
        raw = sys.stdin.read()
        if raw.strip():
            return json.loads(raw)
    return {}


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "--status":
        print(json.dumps(status(), allow_nan=False))
        return
    try:
        data = _read_input()
    except Exception as exc:
        print(json.dumps(_refuse(f"Invalid JSON: {exc}")))
        sys.exit(2)
    # Solver imports (for example NVIDIA Warp) print banners to stdout; keep stdout for the one JSON document only.
    with contextlib.redirect_stdout(sys.stderr):
        try:
            if isinstance(data, dict) and data.get("action") == "status":
                result = status()
            else:
                result = run(data)
            text = json.dumps(result, allow_nan=False)
        except Exception as exc:
            result = _refuse(f"{type(exc).__name__}: {exc}", "engine")
            text = json.dumps(result)
    print(text)
    if result.get("errorKind") == "validation":
        sys.exit(2)
    if result.get("errorKind"):
        sys.exit(1)


if __name__ == "__main__":
    main()
