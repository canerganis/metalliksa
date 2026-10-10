"""Depth-bias note for the served melt-pool depth (reporting only, outside the frozen LPBF physics).

The note is derived from the committed error-band summary (data/calibration/lpbf-meltpool-error-bands-v1.summary.json)
for the alloy, the heat-source kernel actually served and the regime class of the served label. Relative error there is
pred / meas - 1 on published single tracks (positive = the kernel over-predicts). Where the summary has no cell for
that alloy and kernel the note says so and gives no direction. It reads no solver internals, changes no regime
threshold and no depth number, and claims nothing validated (experimentalValidation stays false).

The TypeScript mirror is src/utils/depthBiasWarning.ts; python/test_lpbf_depth_bias.py pins its table and templates
equal to this module and to the summary.
"""
import json
from pathlib import Path
from typing import Any, Dict, Optional

SUMMARY_PATH = Path(__file__).resolve().parent.parent / "data" / "calibration" / "lpbf-meltpool-error-bands-v1.summary.json"

UNDER = "may-underestimate"
OVER = "may-overestimate"

# Below this many held-out tracks the median is reported but no direction is given.
MIN_N_FOR_DIRECTION = 5
# Below this absolute median relative error no direction is given.
MIN_ABS_MEDIAN_FOR_DIRECTION = 0.05

KERNEL_LABELS = {"rosenthal": "Rosenthal", "eagar-tsai": "Eagar-Tsai", "goldak": "Goldak"}

DIRECTION_TEMPLATE = (
    "Depth {verb} for this alloy and kernel in the {regime} band. On published single tracks the {kernel} "
    "kernel on {alloy} {action} the depth by a median of {pct}% (n={n}, {sources} source{plural}). This is a screening "
    "note, not a validated correction, and transfer to another machine is not established."
)
FEW_TEMPLATE = (
    "Too few held-out tracks to give a direction: the {kernel} kernel on {alloy} in the {regime} band has n={n} "
    "(median {action} the depth by {pct}%). This is a screening note, not a validated correction."
)
FLAT_TEMPLATE = (
    "No clear depth bias direction: the {kernel} kernel on {alloy} in the {regime} band has a median depth error of "
    "{pct}% (n={n}, {sources} source{plural}). This is a screening note, not a validated correction."
)
NO_CHECK_TEMPLATE = (
    "No held-out check for this alloy and kernel ({kernel} on {alloy}, {regime} band), so no direction of the depth "
    "error is given."
)
BASIS_TEMPLATE = (
    "Error-band summary {bands_id}, cell {alloy} / {kernel_id} / {regime}: relative error pred / meas - 1, equal source "
    "weight, digitized figures included, screening only."
)
BASIS_NO_CHECK = "Error-band summary {bands_id} has no depth cell for this alloy, kernel and regime band."


def build_cells(summary: Dict[str, Any]) -> Dict[str, Any]:
    """{bandsId, cells: {"alloy|kernel|regime": [median, n, nSources]}} from the summary (single-alloy depth cells)."""
    cells: Dict[str, list] = {}
    for c in summary.get("cells", []):
        alloys = c.get("alloys") or []
        if c.get("quantity") != "depth" or len(alloys) != 1 or c.get("regime") not in ("conduction", "transition", "keyhole"):
            continue
        key = f"{alloys[0]}|{c['kernel']}|{c['regime']}"
        cells[key] = [round(float(c["median"]), 3), int(c["n"]), int(c["nSources"])]
    return {"bandsId": summary.get("bandsId"), "cells": cells}


def _load() -> Dict[str, Any]:
    try:
        return build_cells(json.loads(SUMMARY_PATH.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return {"bandsId": None, "cells": {}}


TABLE = _load()


def _alloy(material_name: Optional[str]) -> Optional[str]:
    m = str(material_name or "").lower()
    if "316" in m:
        return "316L Stainless Steel"
    if "625" in m:
        return "Inconel 625"
    if "718" in m:
        return "Inconel 718"
    if "ti-6al-4v" in m or "ti64" in m or "6al" in m:
        return "Ti-6Al-4V"
    return None


def _regime_class(regime: Optional[str]) -> Optional[str]:
    r = str(regime or "").lower()
    for name in ("conduction", "transition", "keyhole"):
        if r.startswith(name):
            return name
    return None


def _kernel(heat_source: Optional[str]) -> Optional[str]:
    k = str(heat_source or "").strip().lower().replace("_", "-")
    for name in KERNEL_LABELS:
        if k.startswith(name):
            return name
    return None


def depth_bias_warning(regime: Optional[str], material_name: Optional[str], heat_source: Optional[str],
                       table: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """{direction, text, basis}. direction is None when no direction can be given; text is None only when the regime
    class, alloy or kernel is unknown."""
    t = table if table is not None else TABLE
    rc, alloy, kernel = _regime_class(regime), _alloy(material_name), _kernel(heat_source)
    if rc is None or alloy is None or kernel is None:
        return {"direction": None, "text": None, "basis": None}
    fields = {"regime": rc, "alloy": alloy, "kernel": KERNEL_LABELS[kernel]}
    cell = t["cells"].get(f"{alloy}|{kernel}|{rc}")
    if cell is None:
        return {"direction": None, "text": NO_CHECK_TEMPLATE.format(**fields),
                "basis": BASIS_NO_CHECK.format(bands_id=t["bandsId"])}
    median, n, n_sources = cell
    fields.update(n=n, pct=round(abs(median) * 100), sources=n_sources, plural="" if n_sources == 1 else "s",
                  action="overpredicted" if median > 0 else "underpredicted")
    basis = BASIS_TEMPLATE.format(bands_id=t["bandsId"], alloy=alloy, kernel_id=kernel, regime=rc)
    if n < MIN_N_FOR_DIRECTION:
        return {"direction": None, "text": FEW_TEMPLATE.format(**fields), "basis": basis}
    if abs(median) < MIN_ABS_MEDIAN_FOR_DIRECTION:
        return {"direction": None, "text": FLAT_TEMPLATE.format(**fields), "basis": basis}
    verb = "may be overestimated" if median > 0 else "may be underestimated"
    return {"direction": OVER if median > 0 else UNDER, "text": DIRECTION_TEMPLATE.format(verb=verb, **fields), "basis": basis}


def attach_depth_bias_warning(result: Dict[str, Any]) -> Dict[str, Any]:
    """Add meltPoolGeometry.depthBiasWarning to a solver result dict in place (no other key touched). The kernel is the
    one the solver reports it served (processParameters.heatSource)."""
    geometry = result.get("meltPoolGeometry")
    if isinstance(geometry, dict):
        params = result.get("processParameters") or {}
        geometry["depthBiasWarning"] = depth_bias_warning(geometry.get("regime"), result.get("material"), params.get("heatSource"))
    return result
