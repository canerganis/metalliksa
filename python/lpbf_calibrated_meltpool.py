#!/usr/bin/env python3
"""Opt-in calibrated melt-pool mode (screening only, not validation): JSON CLI behind
POST /api/python/lpbf-calibrated-meltpool.

Input keys mirror ``lpbf_thermal_solver.py`` (material, laserPower_W, scanSpeed_mm_s, beamDiameter_um, preheatTemp_C,
layerThickness_um, hatchSpacing_um, laserWavelength, heatSource, sulfur_ppm, absorptionModel, thermalSliceBackend) plus
``"calibrationMode": true``. The output is the contract of ``lpbf_calibration_layer.apply_calibration``: the unchanged
screening result, and a calibrated block that exists only for cells whose gate status is ``enabled``. A missing or
stale artefact never fails the request: the screening result is returned with ``calibrated.available = false`` and
the reason.

``--status`` prints the artefact state and the enabled cells without running a solver.
"""

from __future__ import annotations

import json
import sys
from typing import Any, Dict

import lpbf_calibration_layer as layer


def _read_input() -> Dict[str, Any]:
    if len(sys.argv) > 1 and sys.argv[1].strip().startswith("{"):
        return json.loads(sys.argv[1])
    if not sys.stdin.isatty():
        raw = sys.stdin.read()
        if raw.strip():
            return json.loads(raw)
    return {}


# --- Group 9 status display (SPEC_engine_estimates_2026-10-17 group 9): what the user sees beside the calibration ---

STALE_TEXT = ("This calibration was fitted to an earlier physics version. The uncalibrated model result is shown "
              "separately. Refit the calibration with the current engine before using calibrated dimensions.")
NO_CELL_TEXT = ("This calibration has no eligible {quantity} fit for {alloy} and {kernel}. Import suitable measurements "
                "and fit a new calibration.")
UNAVAILABLE_TEXT = ("The calibration artefact cannot be read. The uncalibrated model result is shown separately. "
                    "Restore or refit the calibration artefact.")
NOT_REQUESTED_TEXT = "Calibrated dimensions were not requested. Turn on calibration mode to see the calibration status."
CELL_STATUS_TEXT = {
    "within-source-only": "fitted within one source only, not across sources",
    "rejected": "the fit did not pass its predeclared gates",
    "no-data": "no published measurements were available for this fit",
    "enabled": "eligible",
}
UNKNOWN = "Uncertainty is unknown and may be large. Calibrate to your machine for better accuracy."
PARENT_TEXT = ("Uncalibrated estimate: about {width} micrometres wide and {depth} micrometres deep from the {kernel} "
               "screening model. {warning}" + UNKNOWN)
PARENT_REFUSED_TEXT = ("The screening model did not form a melt-pool extent for these settings, so no uncalibrated "
                       "width or depth is shown. Check absorbed power, speed and preheat.")


def _sig2(value):
    rounded = float(f"{value:.2g}")
    return f"{rounded:f}".rstrip("0").rstrip(".")


def inspect_artifact(path=None):
    """(state, artefact or None, detail): integrity-checked read that tells stale apart from unreadable.

    The artefact is first verified against its own recorded implementation hash (content, config and evidence checks
    unchanged), then compared with the live fingerprint. Nothing is edited or re-fitted."""
    import json as _json
    target = path or layer.DEFAULT_PATH
    try:
        with open(target, encoding="utf-8") as handle:
            recorded = _json.loads(handle.read()).get("implementationHash")
        art = layer.load_calibration(target, expected_impl_hash=recorded)
    except Exception as exc:  # a status display never fails the request; the reason is shown
        return "unavailable", None, str(exc)
    try:
        layer.load_calibration(target)
    except layer.CalibrationStale as exc:
        return "stale", art, str(exc)
    except layer.CalibrationError as exc:
        return "unavailable", None, str(exc)
    return "ready", art, None


def calibration_status(material: str, kernel: str, *, requested: bool = True, path=None) -> Dict[str, Any]:
    """Artefact state and the requested alloy/kernel cell statuses with their constructive texts (no number)."""
    if not requested:
        return {"artifact": {"state": "not-requested", "text": NOT_REQUESTED_TEXT}, "cells": {}, "enabledCellCount": None}
    state, art, detail = inspect_artifact(path)
    out: Dict[str, Any] = {"artifact": {"state": state, "detail": detail,
                                        "calibrationId": art.get("calibrationId") if art else None,
                                        "text": STALE_TEXT if state == "stale" else UNAVAILABLE_TEXT
                                        if state == "unavailable" else None},
                           "cells": {}, "enabledCellCount": len(layer.enabled_cells(art)) if art else None}
    if art is None:
        return out
    for quantity in ("width", "depth"):
        cell = next((c for c in art.get("cells", []) if c["kernel"] == kernel and c["material"] == material
                     and c["quantity"] == quantity), None)
        status = cell["status"] if cell else "no-data"
        eligible = status == "enabled" and state == "ready"
        out["cells"][quantity] = {
            "status": status, "statusText": CELL_STATUS_TEXT.get(status, status), "eligible": eligible,
            "text": None if eligible else (STALE_TEXT if state == "stale" and status == "enabled" else
                                           NO_CELL_TEXT.format(quantity=quantity, alloy=material, kernel=kernel)),
        }
    return out


def uncalibrated_parent(screening: Dict[str, Any], kernel: str) -> Dict[str, Any]:
    """The served screening width/depth as a Tier 2 parent beside the calibration, when its own extent passed."""
    geometry = (screening or {}).get("meltPoolGeometry") or {}
    width, depth = geometry.get("width_um"), geometry.get("depth_um")
    ok = (geometry.get("extentStatus") == "computed"
          and all(isinstance(v, (int, float)) and not isinstance(v, bool) and v == v and 0 < v < float("inf")
                  for v in (width, depth)))
    if not ok:
        return {"estimateTier": "no-value", "tierLabel": "No value", "width_um": None, "depth_um": None,
                "displaySignificantDigits": None, "domainWarnings": [], "uncertaintyStatement": None,
                "explanation": None, "noValueText": PARENT_REFUSED_TEXT}
    warnings = ["Transferred inputs: the thermophysical, absorptivity and endpoint inputs of this screening model "
                "are transfers, so the result is not calibrated to any machine."]
    regime = str(geometry.get("regime") or "")
    if regime.lower().startswith("keyhole"):
        warnings.insert(0, "Keyhole regime: this conduction screening model does not resolve the vapor cavity. Depth "
                           "may be strongly misestimated.")
    return {"estimateTier": "Physics estimate", "tierLabel": "Uncalibrated estimate", "width_um": width,
            "depth_um": depth, "displaySignificantDigits": 2, "domainWarnings": warnings,
            "uncertaintyStatement": UNKNOWN,
            "explanation": PARENT_TEXT.format(width=_sig2(width), depth=_sig2(depth), kernel=kernel,
                                              warning=""),
            "noValueText": None, "regime": regime or None}


def _material_name(data: Dict[str, Any]) -> str:
    from four_alloy_materials import resolve_alloy_id
    names = {"ti6al4v": "Ti-6Al-4V", "alsi10mg": "AlSi10Mg", "in718": "Inconel 718", "ss316l": "316L Stainless Steel",
             "in625": "Inconel 625"}
    raw = str(data.get("material") or "")
    try:
        return names.get(resolve_alloy_id(raw), raw)
    except Exception:  # an unknown alias keeps the request text; the solver refuses it on its own
        return raw


def status() -> Dict[str, Any]:
    try:
        calib = layer.load_calibration()
    except layer.CalibrationStale as exc:
        return {"status": "stale", "calibrationAvailable": False, "reason": str(exc), "enabledCells": [],
                "overview": status_overview()}
    except layer.CalibrationError as exc:
        return {"status": "unavailable", "calibrationAvailable": False, "reason": str(exc), "enabledCells": [],
                "overview": status_overview()}
    return {"status": "ready", "calibrationAvailable": True, "calibrationId": calib["calibrationId"],
            "enabledCells": layer.enabled_cells(calib), "evidenceKind": layer.EVIDENCE_KIND,
            "label": layer.LABEL}


def status_overview() -> Dict[str, Any]:
    """Artefact state plus every cell status before a calibration is requested (group 9 item 2)."""
    state, art, detail = inspect_artifact()
    cells = ([{"kernel": c["kernel"], "material": c["material"], "quantity": c["quantity"], "status": c["status"],
               "statusText": CELL_STATUS_TEXT.get(c["status"], c["status"])} for c in art.get("cells", [])]
             if art else [])
    return {"state": state, "detail": detail, "text": STALE_TEXT if state == "stale" else UNAVAILABLE_TEXT
            if state == "unavailable" else None, "calibrationId": art.get("calibrationId") if art else None,
            "enabledCellCount": sum(1 for c in cells if c["status"] == "enabled") if art else None, "cells": cells}


def run(data: Dict[str, Any]) -> Dict[str, Any]:
    kernel = data.get("heatSource") or data.get("heat_source") or "rosenthal"
    reason = None
    calib = None
    if data.get("calibrationMode") is not True:
        reason = "calibrationMode was not requested"
    else:
        try:
            calib = layer.load_calibration()
        except layer.CalibrationStale:
            reason = "calibration stale for this physics version"
        except layer.CalibrationError as exc:
            reason = f"calibration artefact unavailable: {exc}"
    if calib is not None:
        out = layer.apply_calibration(data, kernel, calib)
    else:
        spec = layer.solver_kwargs(data)
        screening = layer._default_solver()(*spec["args"], heat_source=kernel, **spec["kwargs"])
        out = {"screening": screening, "evidenceKind": layer.EVIDENCE_KIND,
               "calibrated": {"available": False, "reason": reason, "width_um": None, "depth_um": None},
               "calibration": None, "outsideTrainingEnvelope": False, "envelopeNotes": []}
    # Group 9: status display only; neither block changes the screening or calibrated numbers above.
    out["calibrationStatus"] = calibration_status(_material_name(data), kernel,
                                                  requested=data.get("calibrationMode") is True)
    out["uncalibratedParent"] = uncalibrated_parent(out.get("screening"), kernel)
    return out


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--status":
        print(json.dumps(status()))
        sys.exit(0)
    try:
        print(json.dumps(run(_read_input()), indent=2))
    except Exception as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        sys.exit(1)
