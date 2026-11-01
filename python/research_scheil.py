#!/usr/bin/env python3
"""Research arm: Scheil-Gulliver solidification path on an open TDB, paired with the equilibrium path.

Research only. Not imported by any served route, worker or LPBF solver, and not part of
``calphad_solver``'s served output (that module keeps its own ``scheil_gulliver``). Every result
carries RESEARCH_LABEL: evidenceKind "Literature estimate", maturity "Research", validated False.
It is a CALPHAD calculation on an open database, not a measurement, and the Scheil limit is not the
LPBF solidification path (no undercooling, no solute trapping, no evaporation, no cooling rate).

Model (design brief answered by Codex Astra, 2026-11-02; implementation and choices here):
  * complete mixing in the liquid, no diffusion in the solid, local equilibrium at the interface;
  * per accepted step only the remaining liquid L_n is equilibrated at the new temperature; with the
    raw equilibrium vertices (liquid amount q_L, every solid vertex amount q_p and composition x_p):
        L_{n+1} = L_n * q_L,   dS_p = L_n * q_p,   f_s = 1 - L.
    Every solid vertex of a step is weighted with the same L_n (no running update between phases)
    and is kept with its own composition (same-name vertices are not merged);
  * fractions are moles of atoms (pycalphad basis), not mass or volume fractions.

Numerical honesty rules:
  * every step's raw vertices must close the inventory of the composition that was solved
    (sum q = 1 and sum q x = x_input, absolute 1e-7, relative 1e-3 for components >= 1e-6);
    the whole path is rebuilt independently from the stored solid vertices plus the residual
    liquid and compared with the starting composition (absolute 1e-6);
  * a failed, invalid or non-conserving solve is never booked: the step is halved and retried from
    the last accepted state; when the minimum step still fails the path stops with a reason;
  * the residual liquid is kept; fraction solid is never forced to 1;
  * fraction-solid thresholds are reported as temperature brackets (first crossing on cooling);
    a step that crosses a threshold is refined to at most ``bracket_c`` before it is accepted;
  * a liquid miscibility gap or a GAS phase stops the path (out of scope of this closed,
    single-liquid model).

Pure core ``scheil_path`` takes a ``run_point(T_C, x_liquid) -> {"vertices": [...]} | None``
callable and needs no pycalphad (fast tests use small synthetic fixtures). ``run_case`` does the
real paired calculation with pycalphad; it is slow and is exercised only with METALLIX_SLOW_TESTS=1.

    python python/research_scheil.py --case in625_c0 --steps 2,1 --out result.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

SCHEMA = "metalliksa.research-scheil.v1"

RESEARCH_LABEL: Dict[str, Any] = {
    "evidenceKind": "Literature estimate",
    "maturity": "Research",
    "validated": False,
    "servedOutput": False,
    "method": "CALPHAD calculation",
    "methodDetail": ("pycalphad Gibbs energy minimisation on an open TDB; Scheil-Gulliver limit (complete liquid "
                     "mixing, no solid diffusion, local interface equilibrium). Not measured, not an LPBF "
                     "solidification path, not validated against experiment."),
}

FS_THRESHOLDS: Tuple[float, ...] = (0.001, 0.5, 0.9, 0.99, 0.999)
ONSET_FRACTION_SOLID = 1e-8
INITIAL_LIQUID_MIN = 1.0 - 1e-8
INVENTORY_STEP_ABS_TOL = 1e-7
INVENTORY_PATH_ABS_TOL = 1e-6
INVENTORY_TRACE_MIN = 1e-6
INVENTORY_TRACE_REL_TOL = 1e-3
LIQUID_ABSENT = 1e-9             # a liquid amount at or below this is treated as no liquid
LIQUID_MERGE_TOL = 1e-6          # liquid vertices closer than this in every component are one liquid
CONDITION_MIN_MOLE_FRACTION = 1e-6  # lower bound of a liquid-composition condition (each use is reported)
DEFAULT_STEP_C = 2.0
DEFAULT_MIN_STEP_C = 0.0625
DEFAULT_BRACKET_C = 0.5
DEFAULT_MAX_FS_JUMP = 0.05
DEFAULT_RESIDUAL_STOP = 1e-4     # below this residual liquid the path stops; T_0.999 is reached first
DEFAULT_MAX_CALLS = 10000
DEFAULT_TIME_LIMIT_S = 1800.0
PRESSURE_PA = 101325.0


class ScheilInputError(ValueError):
    """A request this research arm refuses (missing element, mismatched identity, bad input)."""


# --------------------------------------------------------------------------------------- core
def _finite_nonneg(value: Any) -> bool:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(f) and f >= 0.0


def _is_liquid(name: str) -> bool:
    return "LIQUID" in name.upper()


def _is_gas(name: str) -> bool:
    return name.upper().startswith("GAS")


def inventory_error(vertices: Sequence[Dict[str, Any]], x_input: Dict[str, float]) -> Dict[str, Any]:
    """Independent closure of one equilibrium: sum q and sum q*x against the solved composition."""
    total = sum(float(vx["amount"]) for vx in vertices)
    worst_abs = abs(total - 1.0)
    worst_rel = 0.0
    worst_comp = None
    for comp, x_in in x_input.items():
        rebuilt = sum(float(vx["amount"]) * float(vx["X"].get(comp, 0.0)) for vx in vertices)
        err = abs(rebuilt - x_in)
        if err > worst_abs:
            worst_abs, worst_comp = err, comp
        if x_in >= INVENTORY_TRACE_MIN:
            worst_rel = max(worst_rel, err / x_in)
    ok = (worst_abs <= INVENTORY_STEP_ABS_TOL and worst_rel <= INVENTORY_TRACE_REL_TOL)
    return {"ok": ok, "sumAmounts": total, "maxAbsError": worst_abs, "maxRelError": worst_rel,
            "worstComponent": worst_comp}


def classify_point(res: Optional[Dict[str, Any]], x_input: Dict[str, float]) -> Dict[str, Any]:
    """Validate one run_point result. Returns {"ok": True, ...parsed} or {"ok": False, "reason": ...}."""
    if res is None:
        return {"ok": False, "reason": "non-convergence"}
    vertices = res.get("vertices")
    if not isinstance(vertices, list) or not vertices:
        return {"ok": False, "reason": "invalid-solver-output", "detail": "no vertices"}
    comps = sorted(x_input)
    clean: List[Dict[str, Any]] = []
    for vx in vertices:
        name = str(vx.get("phase", "")).strip()
        amount = vx.get("amount")
        xs = vx.get("X") or {}
        if not name or not _finite_nonneg(amount):
            return {"ok": False, "reason": "invalid-solver-output", "detail": f"bad amount for {name!r}"}
        if any(not _finite_nonneg(xs.get(c, 0.0)) for c in comps):
            return {"ok": False, "reason": "invalid-solver-output", "detail": f"bad composition for {name!r}"}
        if float(amount) == 0.0:
            continue
        clean.append({"phase": name, "amount": float(amount), "X": {c: float(xs.get(c, 0.0)) for c in comps}})
    inv = inventory_error(clean, x_input)
    if not inv["ok"]:
        return {"ok": False, "reason": "inventory-not-closed", "inventory": inv}
    gas = [vx for vx in clean if _is_gas(vx["phase"]) and vx["amount"] > LIQUID_ABSENT]
    if gas:
        return {"ok": False, "reason": "gas-phase-formed", "fatal": True,
                "detail": "a GAS phase formed: not a closed single-liquid solidification problem"}
    liquids = [vx for vx in clean if _is_liquid(vx["phase"])]
    solids = [vx for vx in clean if not _is_liquid(vx["phase"])]
    q_liq = sum(vx["amount"] for vx in liquids)
    x_liq: Dict[str, float] = {}
    if q_liq > LIQUID_ABSENT:
        significant = [vx for vx in liquids if vx["amount"] > LIQUID_ABSENT]
        ref = significant[0]["X"]
        for vx in significant[1:]:
            if max(abs(vx["X"][c] - ref[c]) for c in comps) > LIQUID_MERGE_TOL:
                return {"ok": False, "reason": "multiple-liquid-phases", "fatal": True,
                        "detail": "two liquids of different composition: the single-liquid model does not "
                                  "average them"}
        x_liq = {c: sum(vx["amount"] * vx["X"][c] for vx in liquids) / q_liq for c in comps}
    return {"ok": True, "qLiquid": q_liq, "xLiquid": x_liq, "solids": solids, "inventory": inv}


def _clamped_condition(x_liq: Dict[str, float]) -> Tuple[Dict[str, float], float]:
    """Liquid composition as a solver condition: components below the floor are raised to it and the
    rest renormalised. Returns the condition and the largest absolute change (0 when unclamped)."""
    raised = {c: max(CONDITION_MIN_MOLE_FRACTION, float(x)) for c, x in x_liq.items()}
    total = sum(raised.values())
    cond = {c: val / total for c, val in raised.items()}
    change = max(abs(cond[c] - float(x_liq[c])) for c in x_liq)
    if all(float(x_liq[c]) >= CONDITION_MIN_MOLE_FRACTION for c in x_liq):
        return dict(x_liq), 0.0
    return cond, change


def scheil_path(
    run_point: Callable[[float, Dict[str, float]], Optional[Dict[str, Any]]],
    start_c: float,
    x0: Dict[str, float],
    step_c: float = DEFAULT_STEP_C,
    min_step_c: float = DEFAULT_MIN_STEP_C,
    bracket_c: float = DEFAULT_BRACKET_C,
    max_fs_jump: float = DEFAULT_MAX_FS_JUMP,
    residual_stop: float = DEFAULT_RESIDUAL_STOP,
    max_calls: int = DEFAULT_MAX_CALLS,
    time_limit_s: float = DEFAULT_TIME_LIMIT_S,
    t_floor_c: float = -273.15,
    thresholds: Sequence[float] = FS_THRESHOLDS,
) -> Dict[str, Any]:
    """Scheil-Gulliver path from a fully liquid start. Pure function of ``run_point``.

    ``run_point(T_C, x)`` returns {"vertices": [{"phase", "amount", "X": {comp: x}}, ...]} for one
    closed equilibrium of composition ``x`` at T_C, or None when it did not converge.
    """
    if step_c <= 0 or min_step_c <= 0 or min_step_c > step_c:
        raise ScheilInputError("need 0 < min_step_c <= step_c")
    comps = sorted(x0)
    x0f = {c: float(x0[c]) for c in comps}
    if abs(sum(x0f.values()) - 1.0) > 1e-9 or any(v < 0 for v in x0f.values()):
        raise ScheilInputError("x0 must be non-negative mole fractions summing to 1")
    thresholds = tuple(sorted(float(q) for q in thresholds))
    t_start = time.perf_counter()
    calls = 0
    retries = 0
    clamp_uses = 0
    clamp_max_change = 0.0
    stop_detail: Optional[str] = None

    # ---- verify the start is fully liquid
    cond0, ch0 = _clamped_condition(x0f)
    first = classify_point(run_point(float(start_c), cond0), cond0)
    calls += 1
    if ch0 > 0:
        clamp_uses += 1
        clamp_max_change = max(clamp_max_change, ch0)
    if not first["ok"] or first["qLiquid"] < INITIAL_LIQUID_MIN:
        why = first.get("reason") if not first["ok"] else (
            f"liquid fraction {first['qLiquid']:.10g} < {INITIAL_LIQUID_MIN} at the start temperature")
        return _result("start-not-fully-liquid", why, start_c, x0f, comps, [], [], 1.0, x0f, {}, None,
                       None, [], calls, retries, clamp_uses, clamp_max_change, t_start, step_c, min_step_c,
                       bracket_c, max_fs_jump, residual_stop, thresholds)

    t_c = float(start_c)
    liquid = 1.0
    x_liq = dict(first["xLiquid"]) if first["xLiquid"] else dict(x0f)
    curve: List[Dict[str, Any]] = [{"temperatureC": t_c, "fractionSolid": 0.0, "liquidX": dict(x_liq),
                                    "newSolidPhases": []}]
    solid_vertices: List[Dict[str, Any]] = []
    crossings: Dict[str, Dict[str, Any]] = {}
    onset: Optional[Dict[str, Any]] = None
    exhaustion: Optional[Dict[str, Any]] = None
    events: List[Dict[str, Any]] = []
    seen_phases: set = set()
    step = float(step_c)
    reason = "step-limit"

    while True:
        if calls >= max_calls:
            reason = "step-limit"
            break
        if time.perf_counter() - t_start > time_limit_s:
            reason = "time-limit"
            break
        t_new = t_c - step
        if t_new < t_floor_c:
            reason = "temperature-floor"
            break
        cond, change = _clamped_condition(x_liq)
        point = classify_point(run_point(t_new, cond), cond)
        calls += 1
        if change > 0:
            clamp_uses += 1
            clamp_max_change = max(clamp_max_change, change)
        if not point["ok"]:
            if not point.get("fatal") and step > min_step_c:
                step = max(min_step_c, step / 2.0)
                retries += 1
                continue
            reason = point["reason"]
            stop_detail = point.get("detail") or (
                f"{point['reason']} at {t_new:.4f} C after halving the step to {step:g} C")
            break
        q_liq = point["qLiquid"]
        exhausted = q_liq <= LIQUID_ABSENT
        fs_old = 1.0 - liquid
        fs_new = 1.0 - liquid * (0.0 if exhausted else q_liq)
        crosses = [q for q in thresholds if fs_old < q <= fs_new]
        crosses_onset = onset is None and fs_new > ONSET_FRACTION_SOLID
        refine = step > min_step_c and (
            exhausted or (fs_new - fs_old) > max_fs_jump
            or ((crosses or crosses_onset) and step > bracket_c))
        if refine:
            step = max(min_step_c, step / 2.0)
            retries += 1
            continue
        # ---- accept the step (nothing above this line changed the state)
        new_phases = []
        for vx in point["solids"]:
            amount = liquid * vx["amount"]
            solid_vertices.append({"temperatureC": t_new, "phase": vx["phase"], "amount": amount,
                                   "X": dict(vx["X"])})
            if vx["phase"] not in seen_phases:
                seen_phases.add(vx["phase"])
                new_phases.append(vx["phase"])
                events.append({"event": "phase-appears", "phase": vx["phase"], "bracketC": [t_new, t_c]})
        for q in crosses:
            crossings[_q_key(q)] = {"fractionSolid": q, "bracketC": [t_new, t_c],
                                    "midpointC": (t_new + t_c) / 2.0, "bracketWidthK": t_c - t_new}
        if crosses_onset:
            onset = {"bracketC": [t_new, t_c], "midpointC": (t_new + t_c) / 2.0, "bracketWidthK": t_c - t_new,
                     "definition": f"first accepted temperature with fraction solid > {ONSET_FRACTION_SOLID:g}"}
        if exhausted:
            discarded = liquid * q_liq
            exhaustion = {"bracketC": [t_new, t_c], "midpointC": (t_new + t_c) / 2.0,
                          "bracketWidthK": t_c - t_new, "fractionSolidJump": liquid - discarded,
                          "liquidBeforeX": dict(x_liq),
                          "phasesFormed": sorted({vx["phase"] for vx in point["solids"]}),
                          "discardedLiquidBelowThreshold": discarded,
                          "note": ("the remaining liquid froze inside one minimum-size step: an invariant-like "
                                   "terminal reaction resolved to the bracket, shown as a jump, not smoothed")}
            liquid = discarded
            if liquid > 0:
                # the sub-threshold liquid stays in the inventory with its own composition when known
                x_liq = point["xLiquid"] or x_liq
            t_c = t_new
            curve.append({"temperatureC": t_c, "fractionSolid": 1.0 - liquid, "liquidX": None,
                          "newSolidPhases": new_phases})
            reason = "liquid-exhausted"
            break
        liquid *= q_liq
        x_liq = dict(point["xLiquid"])
        t_c = t_new
        curve.append({"temperatureC": t_c, "fractionSolid": 1.0 - liquid, "liquidX": dict(x_liq),
                      "newSolidPhases": new_phases})
        step = min(float(step_c), step * 2.0)
        if liquid < residual_stop:
            reason = "residual-liquid-below-stop"
            stop_detail = f"residual liquid {liquid:.3g} < {residual_stop:g}; not treated as zero"
            break

    return _result(reason, stop_detail, start_c, x0f, comps, curve, solid_vertices, liquid, x_liq, crossings,
                   onset, exhaustion, events, calls, retries, clamp_uses, clamp_max_change, t_start, step_c,
                   min_step_c, bracket_c, max_fs_jump, residual_stop, thresholds)


def _q_key(q: float) -> str:
    return f"{q:g}"


def path_inventory(solid_vertices: Sequence[Dict[str, Any]], residual_liquid: float,
                   residual_x: Dict[str, float], x0: Dict[str, float]) -> Dict[str, Any]:
    """Rebuild the start composition from every stored solid vertex plus the residual liquid."""
    total = sum(v["amount"] for v in solid_vertices) + residual_liquid
    errs = {}
    for c, xc in x0.items():
        rebuilt = sum(v["amount"] * v["X"].get(c, 0.0) for v in solid_vertices) + residual_liquid * residual_x.get(c, 0.0)
        errs[c] = abs(rebuilt - xc)
    worst = max([abs(total - 1.0)] + list(errs.values()))
    rel = max([errs[c] / x0[c] for c in x0 if x0[c] >= INVENTORY_TRACE_MIN] or [0.0])
    return {"ok": worst <= INVENTORY_PATH_ABS_TOL and rel <= INVENTORY_TRACE_REL_TOL,
            "maxAbsError": worst, "maxRelError": rel, "perComponentAbsError": errs,
            "toleranceAbs": INVENTORY_PATH_ABS_TOL, "toleranceRel": INVENTORY_TRACE_REL_TOL}


def _result(reason, detail, start_c, x0, comps, curve, solid_vertices, liquid, x_liq, crossings, onset,
            exhaustion, events, calls, retries, clamp_uses, clamp_max_change, t_start, step_c, min_step_c,
            bracket_c, max_fs_jump, residual_stop, thresholds) -> Dict[str, Any]:
    temps = {}
    for q in thresholds:
        temps[_q_key(q)] = crossings.get(_q_key(q))  # None: threshold not reached
    t_001 = crossings.get(_q_key(0.001))
    t_999 = crossings.get(_q_key(0.999))
    rng = None
    if t_001 and t_999:
        rng = {"valueK": t_001["midpointC"] - t_999["midpointC"],
               "boundsK": [t_001["bracketC"][0] - t_999["bracketC"][1], t_001["bracketC"][1] - t_999["bracketC"][0]],
               "definition": "T(fs=0.001) - T(fs=0.999), midpoints of the brackets; boundsK from the bracket ends"}
    phase_totals: Dict[str, float] = {}
    for v in solid_vertices:
        phase_totals[v["phase"]] = phase_totals.get(v["phase"], 0.0) + v["amount"]
    inventory = path_inventory(solid_vertices, liquid, x_liq or {}, x0) if curve else None
    complete = reason in ("liquid-exhausted", "residual-liquid-below-stop")
    if inventory is not None and not inventory["ok"]:
        complete = False
    return {
        "schema": SCHEMA,
        "label": dict(RESEARCH_LABEL),
        "status": "complete" if complete else "incomplete",
        "stopReason": reason,
        "stopDetail": detail,
        "fractionBasis": "moles of atoms",
        "temperatureInitialC": float(start_c),
        "temperatureOnset": onset,
        "thresholdTemperatures": temps,
        "solidificationRange_0.1_99.9": rng,
        "temperatureExhaustion": exhaustion,
        "temperatureLastValidC": curve[-1]["temperatureC"] if curve else None,
        "residualLiquidFraction": liquid,
        "residualLiquidX": dict(x_liq) if liquid > 0 and x_liq else None,
        "finalFractionSolid": 1.0 - liquid,
        "phaseTotals": dict(sorted(phase_totals.items())),
        "events": events,
        "curve": curve,
        "solidVertexCount": len(solid_vertices),
        "pathInventory": inventory,
        "solverCalls": calls,
        "rejectedOrRefinedSteps": retries,
        "conditionClampUses": clamp_uses,
        "conditionClampMaxChange": clamp_max_change,
        "conditionClampNote": (f"a liquid component below {CONDITION_MIN_MOLE_FRACTION:g} was raised to it for the "
                               "solver condition; the closure check uses the composition actually solved")
        if clamp_uses else None,
        "settings": {"stepC": step_c, "minStepC": min_step_c, "bracketC": bracket_c, "maxFsJump": max_fs_jump,
                     "residualStop": residual_stop, "thresholds": list(thresholds),
                     "stepInventoryTolAbs": INVENTORY_STEP_ABS_TOL},
        "components": comps,
        "elapsedS": round(time.perf_counter() - t_start, 3),
    }


# --------------------------------------------------------------------------- equilibrium pairing
def compare_with_equilibrium(scheil: Dict[str, Any], scheil_identity: Dict[str, Any],
                             equilibrium: Dict[str, Any], equilibrium_identity: Dict[str, Any]) -> Dict[str, Any]:
    """Signed differences between the Scheil thresholds and the equilibrium liquidus/solidus.

    Refuses (ScheilInputError) when the two calculations do not share the TDB hash, phase set, used
    composition, pressure and calculation options. Equilibrium liquidus (lowest T with liquid >= 0.999)
    pairs with Scheil T(fs=0.001); equilibrium solidus (lowest T with liquid > 0.001) with T(fs=0.999).
    """
    keys = ("tdbSha256", "phases", "usedMoleFractions", "pressurePa", "calcOptions", "seeded", "pycalphadVersion")
    mismatched = [k for k in keys if scheil_identity.get(k) != equilibrium_identity.get(k)]
    if mismatched:
        raise ScheilInputError(f"Scheil and equilibrium identities differ in {', '.join(mismatched)}; "
                               "refusing to compare unpaired calculations")
    ct = equilibrium.get("criticalTemperatures") or {}
    st = equilibrium.get("criticalTemperatureStatus") or {}
    liq, sol = ct.get("liquidusC"), ct.get("solidusC")
    t001 = (scheil.get("thresholdTemperatures") or {}).get(_q_key(0.001))
    t999 = (scheil.get("thresholdTemperatures") or {}).get(_q_key(0.999))
    out = {
        "label": dict(RESEARCH_LABEL),
        "pairing": "same TDB hash, phase set, used composition, pressure and calculation options",
        "equilibriumLiquidusC": liq,
        "equilibriumLiquidusBracketC": (st.get("liquidusC") or {}).get("bracketC"),
        "equilibriumSolidusC": sol,
        "equilibriumSolidusBracketC": (st.get("solidusC") or {}).get("bracketC"),
        "equilibriumRangeK": (liq - sol) if liq is not None and sol is not None else None,
        "scheilT0_001C": t001["midpointC"] if t001 else None,
        "scheilT0_999C": t999["midpointC"] if t999 else None,
        "scheilRangeK": (scheil.get("solidificationRange_0.1_99.9") or {}).get("valueK"),
    }
    out["deltaFirstSolidK"] = (out["scheilT0_001C"] - liq) if (t001 and liq is not None) else None
    out["deltaLastSolidK"] = (out["scheilT0_999C"] - sol) if (t999 and sol is not None) else None
    out["note"] = ("delta = Scheil - equilibrium. The first-solid pair should agree to within the brackets "
                   "(same thermodynamics); the last-solid difference is the segregation effect of the Scheil "
                   "limit. A wider Scheil range is expected but not required.")
    return out


# --------------------------------------------------------------------------------- cases
# Nominal design scenarios (wt%), not measured batch analyses. Elements given are never dropped.
CASES: Dict[str, Dict[str, Any]] = {
    "in625_c0": {
        "alloy": "IN625 nominal, C-free",
        "wtPct": {"Ni": 61.0, "Cr": 21.5, "Mo": 9.0, "Nb": 3.6, "Fe": 4.9},
        "databaseId": "mc_ni",
        "compositionSource": ("Special Metals INCONEL alloy 625 bulletin, Table 1 limits (Cr 20-23, Mo 8-10, "
                              "Nb+Ta 3.15-4.15, Fe <= 5); same scenario as python/test_calphad_matcalc_open.py "
                              "IN625 and the calphad_solver ALLOY_KNOWN_DEVIATIONS record. Nb+Ta realised as "
                              "Nb 3.6, Ta 0 (mc_ni has no Ta); Si, Mn, Al, Ti, C, P, S not included."),
        "tGridC": (1100.0, 1450.0, 10.0),
        "scheilFloorC": 1000.0,
    },
    "in625_c005": {
        "alloy": "IN625 nominal, 0.05 C",
        "wtPct": {"Ni": 60.95, "Cr": 21.5, "Mo": 9.0, "Nb": 3.6, "Fe": 4.9, "C": 0.05},
        "databaseId": "mc_ni",
        "compositionSource": "as in625_c0 with C 0.05 wt% taken from Ni",
        "tGridC": (1100.0, 1450.0, 10.0),
        "scheilFloorC": 1000.0,
    },
    "ti64_mc_ti": {
        "alloy": "Ti-6Al-4V ideal ternary",
        "wtPct": {"Ti": 90.0, "Al": 6.0, "V": 4.0},
        "databaseId": "mc_ti",
        "compositionSource": "nominal Ti-6Al-4V; C, Fe, O, N, H are not in mc_ti and are not represented",
        "tGridC": (1500.0, 1750.0, 10.0),
        # mc_ti header: optimised for 773-2000 K; below 1000 C the path is far outside the solidification range
        "scheilFloorC": 1000.0,
    },
    "alsi10mg_cost507": {
        "alloy": "AlSi10Mg ideal ternary",
        "wtPct": {"Al": 89.675, "Si": 10.0, "Mg": 0.325},
        "databaseId": "cost507",
        "compositionSource": ("mid-points of the 3D Systems LaserForm AlSi10Mg(A) Rev D ranges Si 9-11, Mg 0.20-0.45; "
                              "Fe, Ti and other impurities not represented"),
        "tGridC": (450.0, 700.0, 5.0),
        "scheilFloorC": 400.0,
    },
}


def prepare_case(case_id: str) -> Dict[str, Any]:
    """Resolve database and composition without pycalphad; refuses missing elements (never drops them)."""
    if case_id not in CASES:
        raise ScheilInputError(f"unknown case {case_id!r}; known: {', '.join(sorted(CASES))}")
    case = CASES[case_id]
    return prepare_composition(case["wtPct"], case["databaseId"], case_id=case_id, alloy=case["alloy"],
                               composition_source=case["compositionSource"], t_grid_c=case["tGridC"],
                               scheil_floor_c=case.get("scheilFloorC"))


def prepare_composition(wt_pct: Dict[str, float], database_id: str, case_id: str = "custom", alloy: str = "",
                        composition_source: str = "", t_grid_c: Tuple[float, float, float] = (1100.0, 1450.0, 10.0),
                        scheil_floor_c: Optional[float] = None) -> Dict[str, Any]:
    import calphad_solver as cs
    wt, at = cs.normalize_composition(wt_pct)
    base = cs.base_element(at)
    resolved = cs.resolve_database([e.upper() for e in at], preferred_id=database_id, base=base)
    if not resolved.get("ok"):
        raise ScheilInputError(f"{resolved.get('kind')}: {resolved.get('reason')}")
    entry = cs._entry_by_id(database_id) or {}
    limits = entry.get("testedLimitsWtPct") or {}
    outside = cs.outside_tested_limits(wt, limits) if limits else []
    with open(resolved["path"], "rb") as fh:
        sha = hashlib.sha256(fh.read()).hexdigest()
    return {"caseId": case_id, "alloy": alloy, "wtPct": wt, "atFrac": at, "databaseId": database_id,
            "databaseName": resolved["name"], "tdbPath": resolved["path"], "tdbFile": os.path.basename(resolved["path"]),
            "tdbSha256": sha, "databaseSource": entry.get("source"), "databaseLicence": _licence(database_id),
            "outsideTestedLimits": outside, "testedLimitsWtPct": dict(limits), "compositionSource": composition_source,
            "tGridC": list(t_grid_c),
            "scheilFloorC": float(scheil_floor_c) if scheil_floor_c is not None else float(t_grid_c[0])}


def _licence(database_id: str) -> str:
    if database_id.startswith("mc_"):
        return ("ODbL 1.0 / DbCL 1.0 (MatCalc open databases, TU Wien); see "
                "python/databases/MATCALC_OPEN_DATABASES_LICENSE.md")
    if database_id == "cost507":
        return "COST 507 round II database as distributed by opencalphad.com; terms as stated in its file header"
    return "see the database catalogue entry"


def run_case(prep: Dict[str, Any], steps_c: Sequence[float] = (2.0,), time_limit_s: float = DEFAULT_TIME_LIMIT_S,
             max_calls: int = DEFAULT_MAX_CALLS) -> Dict[str, Any]:
    """Paired equilibrium + Scheil calculation with pycalphad (slow)."""
    import calphad_solver as cs
    from pycalphad import variables as v
    if not cs.PYCALPHAD_AVAILABLE:
        raise ScheilInputError("pycalphad is not installed")
    t0 = time.perf_counter()
    t_min, t_max, t_step = prep["tGridC"]
    eq = cs.solve_pycalphad_equilibrium(
        prep["alloy"] or prep["caseId"], prep["wtPct"], prep["atFrac"], t_min, t_max, t_step, prep["tdbPath"],
        prep["databaseName"], db_id=prep["databaseId"], scheil=False, boundary_refinement=True,
        min_refine_step_c=0.5)
    eq_s = time.perf_counter() - t0

    dbf, info = cs.load_database_with_info(prep["tdbPath"])
    entry = cs._entry_by_id(prep["databaseId"]) or {}
    excluded = dict(entry.get("excludedPhases") or {})
    phases = [p for p in dbf.phases.keys() if p not in excluded]
    calc_opts = entry.get("calcOptions") or None
    seeded = bool(entry.get("startingPointSeeding"))
    at = {k.upper(): float(val) for k, val in prep["atFrac"].items()}
    comps = sorted(at)
    dep = sorted(comps, key=lambda c: at[c], reverse=True)[0]
    indep = sorted(c for c in comps if c != dep)
    all_comps = list(comps) + (["VA"] if "VA" in dbf.elements else [])
    # the same condition keys and composition bounds as solve_pycalphad_equilibrium (model cache is shared)
    used = {c: max(1e-5, min(0.999, at[c])) for c in indep}
    used[dep] = 1.0 - sum(used.values())
    base_cond = {v.P: PRESSURE_PA, v.T: [1000.0]}
    for c in indep:
        base_cond[v.X(c)] = used[c]
    runner = cs._EquilibriumRunner(dbf, info.get("sha256", ""), all_comps, phases, base_cond, calc_opts, seeded)
    probe = runner.run(base_cond, as_dataset=runner.workspace is not None)
    eq_comps = [str(c) for c in probe.component.values]

    def run_point(t_c: float, x: Dict[str, float]) -> Optional[Dict[str, Any]]:
        cond = dict(base_cond)
        cond[v.T] = [float(t_c) + cs.ZERO_CELSIUS_K]
        for c in indep:
            cond[v.X(c)] = float(x[c])
        try:
            eq_r = runner.run(cond)
            gm, mu, ph, nps, xr = cs._flat_point_arrays(eq_r, 1)
        except Exception as err:  # a failed call is a non-converged point, never a value
            sys.stderr.write(f"[research_scheil] equilibrium failed at {t_c:.3f} C: {err}\n")
            return None
        if xr is None or not math.isfinite(float(gm[0])):
            return None
        vertices = []
        for j, (name, amount) in enumerate(zip(ph[0], nps[0])):
            name_s = str(name).strip()
            if not name_s:
                continue
            a = float(amount)
            if not math.isfinite(a):
                return {"vertices": [{"phase": name_s, "amount": float("nan"), "X": {}}]}
            vertices.append({"phase": name_s, "amount": a,
                             "X": {eq_comps[i]: float(xr[0, j, i]) for i in range(len(eq_comps)) if eq_comps[i] != "VA"}})
        return {"vertices": vertices}

    ident = {"tdbSha256": info.get("sha256"), "phases": sorted(phases), "usedMoleFractions": used,
             "pressurePa": PRESSURE_PA, "calcOptions": dict(calc_opts or {}), "seeded": seeded,
             "pycalphadVersion": cs.PYCALPHAD_VERSION}
    # The equilibrium identity is read back from what the equilibrium result reports about itself.
    eq_comp_adj = eq.get("compositionAdjustments") or {}
    eq_used = {c: float((eq_comp_adj.get(c) or {}).get("usedMoleFraction", at[c])) for c in indep}
    eq_used[dep] = 1.0 - sum(eq_used.values())
    eq_excluded = {e["phase"] for e in (eq.get("excludedPhases") or [])}
    eq_ident = {"tdbSha256": (eq.get("modelCache") or {}).get("databaseSha256"),
                "phases": sorted(p for p in dbf.phases.keys() if p not in eq_excluded),
                "usedMoleFractions": eq_used, "pressurePa": PRESSURE_PA,
                "calcOptions": dict(eq.get("pycalphadCalcOptions") or {}),
                "seeded": bool(eq.get("startingPointSeeding")), "pycalphadVersion": cs.PYCALPHAD_VERSION}

    liq_status = (eq.get("criticalTemperatureStatus") or {}).get("liquidusC") or {}
    runs = []
    if liq_status.get("status") != "bisected":
        scheil_runs_note = "equilibrium liquidus not refined; no Scheil start temperature"
    else:
        scheil_runs_note = None
        start_c = float(liq_status["bracketC"][1]) + 1.0
        if runner.lock is not None:
            runner.lock.acquire()
        try:
            for s in steps_c:
                path = scheil_path(run_point, start_c, used, step_c=float(s), time_limit_s=time_limit_s,
                                   max_calls=max_calls, t_floor_c=prep["scheilFloorC"])
                path["comparison"] = compare_with_equilibrium(path, ident, eq, eq_ident)
                path["liquidOutsideTestedLimits"] = liquid_outside_tested_limits(
                    path["curve"], prep.get("testedLimitsWtPct") or {})
                runs.append(path)
        finally:
            if runner.lock is not None:
                runner.lock.release()
    convergence = None
    if len(runs) >= 2:
        a, b = runs[-2], runs[-1]
        diffs = {}
        for q in FS_THRESHOLDS:
            ta, tb = a["thresholdTemperatures"].get(_q_key(q)), b["thresholdTemperatures"].get(_q_key(q))
            diffs[_q_key(q)] = (tb["midpointC"] - ta["midpointC"]) if ta and tb else None
        convergence = {"steps": [a["settings"]["stepC"], b["settings"]["stepC"]], "thresholdShiftK": diffs,
                       "target": "<= 1 K between the last two runs (Astra brief); a target, not a pass claim"}
    return {
        "schema": SCHEMA,
        "label": dict(RESEARCH_LABEL),
        "case": {k: prep[k] for k in prep if k not in ("tdbPath",)},
        "identity": ident,
        "equilibrium": {
            "criticalTemperatures": {k: (eq.get("criticalTemperatures") or {}).get(k)
                                     for k in ("liquidusC", "solidusC", "freezingRangeC")},
            "status": {k: (eq.get("criticalTemperatureStatus") or {}).get(k) for k in ("liquidusC", "solidusC")},
            "compositionAdjustments": eq_comp_adj,
            "elapsedS": round(eq_s, 2),
        },
        "scheilRuns": [{k: r[k] for k in r if k != "curve"} | {"curveSample": _sample_curve(r["curve"])}
                       for r in runs],
        "scheilNote": scheil_runs_note,
        "convergence": convergence,
        "elapsedS": round(time.perf_counter() - t0, 2),
    }


def liquid_outside_tested_limits(curve: Sequence[Dict[str, Any]], limits: Dict[str, float]) -> List[Dict[str, Any]]:
    """Elements whose enriched Scheil liquid exceeds the database's tested wt% limit: first temperature and maximum."""
    if not limits:
        return []
    out: Dict[str, Dict[str, Any]] = {}
    for p in curve:
        x = p.get("liquidX")
        if not x:
            continue
        masses = {c.upper(): float(x[c]) * _atomic_weight(c) for c in x}
        total = sum(masses.values())
        for el, m in masses.items():
            lim = limits.get(el)
            if lim is None or total <= 0:
                continue
            wt = 100.0 * m / total
            if wt > lim:
                rec = out.setdefault(el, {"element": el, "testedUpToWtPct": float(lim), "firstExceededAtC": p["temperatureC"],
                                          "firstFractionSolid": p["fractionSolid"], "maxLiquidWtPct": wt})
                rec["maxLiquidWtPct"] = max(rec["maxLiquidWtPct"], wt)
    return [out[k] for k in sorted(out)]


def _atomic_weight(el: str) -> float:
    import calphad_solver as cs
    return cs._atomic_weight(el[0].upper() + el[1:].lower())


def _sample_curve(curve: List[Dict[str, Any]], every_k: float = 5.0) -> List[Dict[str, Any]]:
    """Fraction solid vs T roughly every ``every_k`` plus the last point (liquid compositions dropped)."""
    out, last_t = [], None
    for i, p in enumerate(curve):
        if last_t is None or last_t - p["temperatureC"] >= every_k or i == len(curve) - 1:
            out.append({"temperatureC": round(p["temperatureC"], 4), "fractionSolid": round(p["fractionSolid"], 7)})
            last_t = p["temperatureC"]
    return out


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--case", required=True, choices=sorted(CASES))
    ap.add_argument("--steps", default="2", help="comma-separated Scheil start steps in K, e.g. 2,1")
    ap.add_argument("--time-limit-s", type=float, default=DEFAULT_TIME_LIMIT_S)
    ap.add_argument("--max-calls", type=int, default=DEFAULT_MAX_CALLS)
    ap.add_argument("--out", help="write the JSON result here (default: stdout)")
    args = ap.parse_args(argv)
    prep = prepare_case(args.case)
    result = run_case(prep, [float(s) for s in args.steps.split(",") if s.strip()], args.time_limit_s, args.max_calls)
    text = json.dumps(result, indent=2, sort_keys=False, default=float)
    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text + "\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
