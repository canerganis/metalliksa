"""G1.1 accepted-prefix plumbing for the transient thermal job (SPEC_engine_estimates_2026-10-17 G1.1, unchanged by
Amendment 1).

The fixed-domain enthalpy solver (python/lpbf_simulation.py, pinned) stops at the material boiling limit; that stop is
model admission and stays. This opt-in channel outside the pinned manifest attaches the solver's existing read-only
local-history observer to a few declared points of the first track, keeps only ACCEPTED steps (the observer runs after
a step passes every validity check, so the rejected step never reaches it), and, when the run is refused with
THERMAL_BOILING_LIMIT, attaches the prefix to the refusal: computed interval [0, last accepted time], accepted step
count, the first rejected step index and reason, and per point the temperature history and its maximum over the
computed interval. Nothing changes for a completed run: the observer is read-only and its record is discarded.

The values are a Tier 2 "Uncalibrated estimate" of a temperature history over a partial interval; the maximum is
labelled "maximum over the computed interval", never the final-process peak. The missing remainder is a physics gap
(evaporation model), not a software result.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

SCHEMA = "lpbf-accepted-prefix-1"
POINT_FRACTIONS = (0.0, 0.25, 0.5, 0.75)
# The prefix travels in the refusal frame of the job log, whose stored tail is 16000 characters (lpbf_worker).
MAX_HISTORY_POINTS = 16
UNKNOWN = "Uncertainty is unknown and may be large. Calibrate to your machine for better accuracy."
OBSERVER_REFUSAL = "Local history supports standard reference powder-layer runs only"
MATERIAL_NAMES = {"ti6al4v": "Ti-6Al-4V", "alsi10mg": "AlSi10Mg", "in718": "Inconel 718",
                  "ss316l": "316L Stainless Steel", "in625": "Inconel 625"}
NO_VALUE_TEXT = ("A complete temperature history needs an evaporation model with compatible material properties. The "
                 "current run stopped at the boiling limit. You can inspect the computed interval or select a model "
                 "that includes the missing physics.")


def _sig(value: float, digits: int = 2) -> str:
    rounded = float(f"{value:.{digits}g}")
    return f"{rounded:.{digits}g}" if abs(rounded) < 1e-3 or abs(rounded) >= 1e6 else f"{rounded:f}".rstrip("0").rstrip(".")


def execution_settings(raw: Dict[str, Any]) -> Dict[str, Any]:
    """The validated settings the reference transient will actually use (the same grid-policy switch as run())."""
    from lpbf_simulation import validate
    p, _ = validate(raw)
    automatic = p["mode"] == "standard" and p["surfaceMode"] == "powder-layer" and p["backend"] == "auto"
    mesh_study = (p["study"] == "mesh" and p["mode"] == "standard" and p["surfaceMode"] == "powder-layer"
                  and p["backend"] in ("auto", "reference"))
    if (automatic or mesh_study) and p.get("powderGridPolicy") != "layer-conforming":
        p, _ = validate(dict(raw, backend="reference", powderGridPolicy="layer-conforming"))
    return p


def eligible(p: Dict[str, Any]) -> bool:
    return (p["mode"] == "standard" and p["backend"] == "reference" and p["study"] == "none"
            and p["surfaceMode"] == "powder-layer" and p.get("thermalModelId") != "layered-plate-enthalpy-v1")


def selected_points(p: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Declared observation points: surface cells along the first track at its start and at 25, 50 and 75 percent of
    its length, and the cell two cells below the start, first deposited layer. Observation settings, not physics."""
    import numpy as np
    from lpbf_core_physics import calculate_mesh_domain, scan_segments
    domain = calculate_mesh_domain(p)
    nx, ny, nz, dx, span, substrate = (domain[k] for k in ("nx", "ny", "nz", "dx", "span", "substrate_depth"))
    axis = (np.arange(nx) + .5) * dx - span / 2
    axis_y = (np.arange(ny) + .5) * dx - ny * dx / 2
    z = (np.arange(nz) + .5) * dx - substrate
    surface = p["layer_um"] * 1e-6
    top = int(np.flatnonzero(z < surface)[-1])
    segment = scan_segments(p)[0][0]
    start, end = np.array(segment["start"]), np.array(segment["end"])
    points = []
    for fraction in POINT_FRACTIONS:
        xy = start + fraction * (end - start)
        i, j = int(np.argmin(np.abs(axis - xy[0]))), int(np.argmin(np.abs(axis_y - xy[1])))
        points.append({"id": f"surface-{int(fraction * 100)}pct", "ijk": (i, j, top)})
    first = points[0]["ijk"]
    points.append({"id": "below-track-start-2-cells", "ijk": (first[0], first[1], max(0, top - 2))})
    unique, seen = [], set()
    for point in points:
        if point["ijk"] not in seen:
            seen.add(point["ijk"])
            unique.append(point)
    return unique


class PrefixRecorder:
    """Read-only local-history observer: running maxima and a thinned history per point, accepted steps only."""

    def __init__(self, points: List[Dict[str, Any]]):
        self.points = points
        self.steps = 0
        self.last_time = 0.0
        self.stride = 1
        self.cells: List[Dict[str, Any]] = [{"max": -math.inf, "tmax": 0.0, "last": None, "history": [],
                                             "coordinate": None} for _ in points]

    def __call__(self, frame: Dict[str, Any]) -> None:
        self.steps += 1
        self.last_time = float(frame["time_s"])
        keep = (self.steps - 1) % self.stride == 0
        for slot, cell in zip(self.cells, frame["cells"]):
            T = float(cell["temperature_K"])
            slot["coordinate"] = cell["coordinate_m"]
            slot["last"] = T
            if T > slot["max"]:
                slot["max"], slot["tmax"] = T, self.last_time
            if keep:
                slot["history"].append((self.last_time, T))
        if len(self.cells[0]["history"]) > 2 * MAX_HISTORY_POINTS:
            for slot in self.cells:
                slot["history"] = slot["history"][::2]
            self.stride *= 2

    def prefix(self, p: Dict[str, Any], reason_code: str) -> Dict[str, Any]:
        alloy = str(p.get("material"))
        end = self.last_time
        texts = (f"Uncalibrated estimate of the temperature at the selected points for {alloy} from the stated "
                 f"transient model. {UNKNOWN} Only the interval from 0 s to {_sig(end, 3)} s was computed. The next "
                 "step exceeded the conduction model's boiling limit.")
        points = []
        for point, slot in zip(self.points, self.cells):
            if slot["last"] is None:
                continue
            points.append({
                "id": point["id"], "cellIndex": list(point["ijk"]), "coordinate_m": slot["coordinate"],
                "maximumOverComputedInterval_K": slot["max"], "timeOfMaximum_s": slot["tmax"],
                "lastAcceptedTemperature_K": slot["last"],
                "history": [{"time_s": t, "temperature_K": T} for t, T in slot["history"]],
            })
        has = self.steps > 0 and bool(points)
        return {
            "schema": SCHEMA,
            "estimateTier": "Physics estimate" if has else "no-value",
            "tierLabel": "Uncalibrated estimate" if has else "No value",
            "displaySignificantDigits": 2 if has else None,
            "uncertaintyStatement": UNKNOWN if has else None,
            "observable": "temperature history at declared points over the computed interval",
            "maximumLabel": "maximum over the computed interval",
            "computedInterval_s": [0.0, end],
            "acceptedSteps": self.steps,
            "firstRejectedStep": {"index": self.steps + 1, "reasonCode": reason_code},
            "points": points,
            "pointRule": "surface cells at the start and at 25, 50 and 75 percent of the first track and one cell two "
                         "cells below the start, first layer (declared observation points)",
            "domainWarnings": [
                "Fixed-domain conduction with a boiling stop: no evaporation, recoil, melt flow or surface motion.",
                "Material properties are the solver's estimated laws; their transfers apply to this history.",
            ],
            "explanation": texts if has else None,
            "noValueText": None if has else NO_VALUE_TEXT,
            "completeHistoryText": NO_VALUE_TEXT,
        }


def run_with_accepted_prefix(raw: Dict[str, Any], report, folder, capabilities, *, solver=None, **options):
    """run_thermal_request with the prefix recorder attached on eligible runs; THERMAL_BOILING_LIMIT refusals carry
    ``detail.acceptedPrefix``. Every other outcome is exactly that of run_thermal_request."""
    from lpbf_request_errors import LpbfRequestRefusal, run_thermal_request
    recorder = None
    try:
        p = execution_settings(raw)
        if eligible(p) and not (capabilities or {}).get("openfoamThermal"):
            recorder = PrefixRecorder(selected_points(p))
    except Exception:  # an inadmissible request is refused by the solver itself below
        recorder, p = None, None
    if recorder is None:
        return run_thermal_request(raw, report, folder, capabilities, solver=solver, **options)
    try:
        return run_thermal_request(raw, report, folder, capabilities, solver=solver,
                                   local_history_observer=recorder,
                                   local_history_indices_ijk=[pt["ijk"] for pt in recorder.points], **options)
    except LpbfRequestRefusal as refusal:
        if refusal.code == "THERMAL_BOILING_LIMIT":
            refusal.detail["acceptedPrefix"] = recorder.prefix(p, refusal.code)
        raise
    except ValueError as error:
        if OBSERVER_REFUSAL in str(error):
            return run_thermal_request(raw, report, folder, capabilities, solver=solver, **options)
        raise
