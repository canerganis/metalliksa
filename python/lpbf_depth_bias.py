"""Depth-bias note for the served melt-pool depth (reporting only, outside the frozen LPBF physics).

The note is derived from the committed error-band summary (data/calibration/lpbf-meltpool-error-bands-v1.summary.json)
for the alloy, the heat-source kernel actually served and the regime class of the track's normalized enthalpy index
(dH/hs, processParameters.normalizedEnthalpy) cut at the summary's own pre-declared edges (config.thresholds, 15 / 20).
The served regime label is used only when the index is missing, because the served label can move (the IN625 keyhole
cut is 13.6) while the bands were built on the fixed edges. Relative error there is
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
DISAGREE_TEMPLATE = (
    "No depth bias direction: the served regime label ({label}) and the error-band class from the enthalpy index "
    "({regime}, dH/hs {index}) disagree here. For context only, the {kernel} kernel on {alloy} in the {regime} band has a "
    "median depth error of {pct}% ({action}, n={n}, {sources} source{plural}). No direction is given. This is a screening "
    "note, not a validated correction."
)
DISAGREE_NO_CELL_TEMPLATE = (
    "No depth bias direction: the served regime label ({label}) and the error-band class from the enthalpy index "
    "({regime}, dH/hs {index}) disagree here, and there is no held-out check for {kernel} on {alloy} in the {regime} band. "
    "No direction is given."
)
# P1 planned bump (2026-10-11): appended to the direction text of the cells the bump moved against measurement.
# UNDER cells in the transition and keyhole bands (every kernel shares the flat-absorptivity Fabbro leg there);
# OVER cells of the Rosenthal kernel in the conduction band (its field lost the latent-heat cut).
P1_UNDER_NOTE = (" After 2026-10-11 no kernel represents the measured absorptance rise, so transition and keyhole "
                 "depth is biased low in all three kernels.")
P1_OVER_NOTE = (" The conduction field carries no latent-heat cut since 2026-10-11, so conduction-mode depth from "
                "the Rosenthal kernel is higher than before.")
BASIS_TEMPLATE = (
    "Error-band summary {bands_id}, cell {alloy} / {kernel_id} / {regime}: relative error pred / meas - 1, equal source "
    "weight, digitized figures included, screening only."
)
CLASS_BASIS = (" Band class from the enthalpy index dH/hs: conduction below {lo}, transition {lo} to {hi}, "
               "keyhole at {hi} or above.")
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
    return {"bandsId": summary.get("bandsId"), "cells": cells, "edges": _edges(summary)}


def _edges(summary: Dict[str, Any]) -> list:
    th = (summary.get("config") or {}).get("thresholds") or []
    return [float(th[0]), float(th[1])] if len(th) == 2 else [15.0, 20.0]


def _load() -> Dict[str, Any]:
    try:
        return build_cells(json.loads(SUMMARY_PATH.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return {"bandsId": None, "cells": {}, "edges": [15.0, 20.0]}


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


def enthalpy_class(enthalpy: Any, edges: Optional[list] = None) -> Optional[str]:
    """Error-band class of the normalized enthalpy index: < lo conduction, < hi transition, else keyhole."""
    try:
        e = float(enthalpy)
    except (TypeError, ValueError):
        return None
    if e != e:
        return None
    lo, hi = edges if edges is not None else TABLE["edges"]
    return "conduction" if e < lo else ("transition" if e < hi else "keyhole")


def _kernel(heat_source: Optional[str]) -> Optional[str]:
    k = str(heat_source or "").strip().lower().replace("_", "-")
    for name in KERNEL_LABELS:
        if k.startswith(name):
            return name
    return None


def labels_contradict(label_class: Optional[str], index_class: Optional[str]) -> bool:
    """True when the served label and the index class are conduction vs keyhole (two steps apart). Adjacent classes
    (the IN625 label has no transition band, so transition vs keyhole is expected) keep their direction."""
    return {label_class, index_class} == {"conduction", "keyhole"}


def depth_bias_warning(regime: Optional[str], material_name: Optional[str], heat_source: Optional[str],
                       enthalpy: Any = None, table: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """{direction, text, basis}. The class comes from the enthalpy index when given, else from the served label.
    direction is None when no direction can be given; text is None only when the class, alloy or kernel is unknown."""
    t = table if table is not None else TABLE
    by_index = enthalpy_class(enthalpy, t.get("edges"))
    rc = by_index or _regime_class(regime)
    alloy, kernel = _alloy(material_name), _kernel(heat_source)
    if rc is None or alloy is None or kernel is None:
        return {"direction": None, "text": None, "basis": None}
    classed_by = ""
    if by_index is not None:
        lo, hi = t.get("edges") or [15.0, 20.0]
        classed_by = CLASS_BASIS.format(lo=f"{lo:g}", hi=f"{hi:g}")
    fields = {"regime": rc, "alloy": alloy, "kernel": KERNEL_LABELS[kernel]}
    cell = t["cells"].get(f"{alloy}|{kernel}|{rc}")
    label_cls = _regime_class(regime)
    if by_index is not None and labels_contradict(label_cls, by_index):
        fields.update(label=label_cls, index=f"{float(enthalpy):g}")
        basis = (BASIS_TEMPLATE.format(bands_id=t["bandsId"], alloy=alloy, kernel_id=kernel, regime=rc) if cell
                 else BASIS_NO_CHECK.format(bands_id=t["bandsId"])) + classed_by
        if cell is None:
            return {"direction": None, "text": DISAGREE_NO_CELL_TEMPLATE.format(**fields), "basis": basis}
        median, n, n_sources = cell
        fields.update(n=n, pct=round(abs(median) * 100), sources=n_sources, plural="" if n_sources == 1 else "s",
                      action="overpredicted" if median > 0 else "underpredicted")
        return {"direction": None, "text": DISAGREE_TEMPLATE.format(**fields), "basis": basis}
    if cell is None:
        return {"direction": None, "text": NO_CHECK_TEMPLATE.format(**fields),
                "basis": BASIS_NO_CHECK.format(bands_id=t["bandsId"]) + classed_by}
    median, n, n_sources = cell
    fields.update(n=n, pct=round(abs(median) * 100), sources=n_sources, plural="" if n_sources == 1 else "s",
                  action="overpredicted" if median > 0 else "underpredicted")
    basis = BASIS_TEMPLATE.format(bands_id=t["bandsId"], alloy=alloy, kernel_id=kernel, regime=rc) + classed_by
    if n < MIN_N_FOR_DIRECTION:
        return {"direction": None, "text": FEW_TEMPLATE.format(**fields), "basis": basis}
    if abs(median) < MIN_ABS_MEDIAN_FOR_DIRECTION:
        return {"direction": None, "text": FLAT_TEMPLATE.format(**fields), "basis": basis}
    verb = "may be overestimated" if median > 0 else "may be underestimated"
    text = DIRECTION_TEMPLATE.format(verb=verb, **fields)
    if median < 0 and rc in ("transition", "keyhole"):
        text += P1_UNDER_NOTE
    elif median > 0 and rc == "conduction" and kernel == "rosenthal":
        text += P1_OVER_NOTE
    return {"direction": OVER if median > 0 else UNDER, "text": text, "basis": basis}


def attach_depth_bias_warning(result: Dict[str, Any]) -> Dict[str, Any]:
    """Add meltPoolGeometry.depthBiasWarning to a solver result dict in place (no other key touched). The kernel is the
    one the solver reports it served (processParameters.heatSource)."""
    geometry = result.get("meltPoolGeometry")
    if isinstance(geometry, dict):
        params = result.get("processParameters") or {}
        geometry["depthBiasWarning"] = depth_bias_warning(geometry.get("regime"), result.get("material"), params.get("heatSource"),
                                                           params.get("normalizedEnthalpy"))
    return result
