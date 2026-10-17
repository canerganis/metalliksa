"""Group 8 first pass: thermal-history observables and Ti-6Al-4V reaction-progress references for the Build Job.

Authority: docs/research/SPEC_engine_estimates_2026-10-17.md group 8 ("Executable models and required inputs") and
Amendment 1 A1.6 (KM attribution only). Not pinned: no thermal manifest file is touched; the field is the one the
Build Job's own served solve hands to solidification_front (captured by lpbf_solidification_estimates).

- Path cooling observable (all alloys): on each retained rear-branch material point, the single-pass conduction path
  T(x0 - v t, 0, z0) from its solidification; q = (Thi - Tlo) / (t(Tlo) - t(Thi)) between the first downward
  crossings of a named subsolidus interval, weighted median over the points. The interval is shown explicitly; the
  default is the declared convention [solidus, preheat + 25 K], never Ti's transus interval for other alloys.
  Refused on reheating (nonmonotonic path), an unresolved crossing or failed refinement.
- Ti KM first pass: the SOL-C channel's own KM quantity (rule finite-25K-above-preheat-v1, Salsi Eq. 19).
- Ti isothermal martensite dissolution: Salsi et al. 2018 Table 3 (PDF14) knots (T C, a_eq, t30 s, t90 s);
  X(t) = 1 - exp(-k t^p), p = ln[ln(0.1)/ln(0.7)] / ln(t90/t30), k = -ln(0.7) / t30^p, d = a_eq X(t). Exact knots, or
  a separately flagged linear interpolation of a_eq, t30, t90 on [400, 700] C. Refused outside that range.

Every value is Tier 2 ("Uncalibrated estimate"): the thermal parent and the source parameters are transfers. Other
alloys get constructive no-value texts for phase quantities; no steel model, placeholder or zero is substituted.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import quantity_envelope as qe

MODEL_ID = "build-job-kinetics-estimates-v1"
PATH_RULE = "single-pass-conduction-path-v1"
DEFAULT_INTERVAL_RULE = "solidus-to-preheat-plus-25K-v1"
PATH_RATIO = 1.15
PATH_FIRST_STEP_M = 1e-7
PATH_MAX_M = 1.0
TIME_TOLERANCE_REL = 1e-3
KELVIN = 273.15

SALSI_TABLE3 = ((400.0, 0.25, 500.0, 1200.0), (500.0, 0.80, 520.0, 3600.0), (700.0, 1.00, 450.0, 3000.0))
SALSI_TABLE3_LOCATOR = ("Salsi, Chiumenti and Cervera 2018, Metals 8, 633, doi 10.3390/met8080633, author PDF14 "
                        "Table 3 (T, dissolvable fraction, t30, t90; hardness-derived interpretation), PDF5 Eqs. 3-9")
DISSOLUTION_RANGE_C = (400.0, 700.0)

PATH_TEXT = ("A cooling rate needs a computed or measured time-temperature path at a named material point. The "
             "selected path does not cross the interval cleanly. {detail}")
REHEAT_TEXT = ("This path reheats inside the interval. A nonmonotonic history needs segment-specific rates and "
               "times, not one average.")
INTERVAL_TEXT = ("Select a subsolidus temperature interval: the upper temperature at or below the solidus and the "
                 "lower one above the preheat.")
HOLD_TEXT = ("Enter an isothermal hold temperature and time to see the dissolved fraction of the martensite entering "
             "the hold.")
HOLD_RANGE_TEXT = ("The source kinetic data cover 400 to 700 C. Another positive, physically applicable kinetic data "
                   "set is needed outside that range.")
HOLD_KNOT_TEXT = ("The hold temperature is not a source knot (400, 500 or 700 C). Select a knot, or explicitly select "
                  "the interpolated scenario.")
JMAK_TEXT = ("This transformation estimate needs the starting phase amounts and a same-alloy reaction model with "
             "temperature-dependent transformation times. Supply these inputs with a time-temperature history, or "
             "select an explicitly labelled isothermal reaction scenario.")
NO_PATH_TEXT = ("A cooling rate needs a computed or measured time-temperature path. No thermal parent was captured "
                "for this build.")


def _se():
    import lpbf_solidification_estimates as se
    return se


def _sig(value: float, digits: int = 2) -> str:
    if value == 0:
        return "0"
    rounded = float(f"{value:.{digits}g}")
    return f"{rounded:.{digits}g}" if abs(rounded) < 1e-3 or abs(rounded) >= 1e6 else f"{rounded:f}".rstrip("0").rstrip(".")


# --- Path cooling observable ---------------------------------------------------------------------------------------

def _bisect(fn, lo, hi, iterations=200):
    f_lo = fn(lo)
    for _ in range(iterations):
        mid = 0.5 * (lo + hi)
        if mid in (lo, hi):
            break
        f_mid = fn(mid)
        if (f_mid > 0) == (f_lo > 0):
            lo, f_lo = mid, f_mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def path_crossings(T_fn, x0: float, z0: float, v: float, levels_C: Sequence[float], ratio: float = PATH_RATIO
                   ) -> List[float]:
    """Times [s] of the first downward crossings of ``levels_C`` (descending) on T(x0 - v t, 0, z0).

    Raises ValueError("reheating-needs-segment-rates") on any rise before the last level is crossed and
    ValueError("missing-crossing") when the path never reaches it."""
    se = _se()
    def temp(s):
        return se._t(T_fn, x0 - s, 0.0, z0)
    s_prev, t_prev = 0.0, temp(0.0)
    s = PATH_FIRST_STEP_M
    times: List[float] = []
    pending = list(levels_C)
    while s <= PATH_MAX_M and pending:
        t_now = temp(s)
        if t_now > t_prev:
            raise ValueError("reheating-needs-segment-rates")
        while pending and t_prev >= pending[0] > t_now:
            level = pending.pop(0)
            root = _bisect(lambda u, level=level: temp(u) - level, s_prev, s)
            times.append(root / v)
        s_prev, t_prev = s, t_now
        s *= ratio
    if pending:
        raise ValueError("missing-crossing")
    return times


def path_cooling(T_fn, sample: Mapping[str, Any], v: float, high_C: float, low_C: float) -> Dict[str, float]:
    """q over [low, high] on one material path, with a step-ratio refinement check."""
    x0, z0 = sample["position_m"]["x"], sample["position_m"]["z"]
    coarse = path_crossings(T_fn, x0, z0, v, (high_C, low_C))
    fine = path_crossings(T_fn, x0, z0, v, (high_C, low_C), ratio=math.sqrt(PATH_RATIO))
    duration = coarse[1] - coarse[0]
    if not duration > 0:
        raise ValueError("zero-duration")
    if any(abs(a - b) > TIME_TOLERANCE_REL * max(abs(a), 1e-300) for a, b in zip(coarse, fine)):
        raise ValueError("refinement-failed")
    return {"rate_K_s": (high_C - low_C) / duration, "timeHigh_s": coarse[0], "timeLow_s": coarse[1]}


# --- Ti isothermal dissolution -------------------------------------------------------------------------------------

def dissolution_parameters(a_eq: float, t30: float, t90: float) -> Tuple[float, float]:
    """(k [s^-p], p) of X = 1 - exp(-k t^p) through X(t30) = 0.3 and X(t90) = 0.9."""
    p = math.log(math.log(0.1) / math.log(0.7)) / math.log(t90 / t30)
    k = -math.log(0.7) / t30 ** p
    return k, p


def dissolution_knot(temperature_C: float, interpolate: bool) -> Tuple[float, float, float, str]:
    """(a_eq, t30, t90, basis) at the hold temperature; raises ValueError(tag) outside the admitted set."""
    lo, hi = DISSOLUTION_RANGE_C
    if not lo <= temperature_C <= hi:
        raise ValueError("outside-source-range")
    for T, a, t30, t90 in SALSI_TABLE3:
        if temperature_C == T:
            return a, t30, t90, "source-knot"
    if not interpolate:
        raise ValueError("not-a-source-knot")
    for (T0, a0, p0, q0), (T1, a1, p1, q1) in zip(SALSI_TABLE3, SALSI_TABLE3[1:]):
        if T0 <= temperature_C <= T1:
            w = (temperature_C - T0) / (T1 - T0)
            return a0 + w * (a1 - a0), p0 + w * (p1 - p0), q0 + w * (q1 - q0), "interpolated-scenario"
    raise ValueError("outside-source-range")


def dissolved_fraction(temperature_C: float, time_s: float, interpolate: bool = False) -> Dict[str, Any]:
    a, t30, t90, basis = dissolution_knot(temperature_C, interpolate)
    k, p = dissolution_parameters(a, t30, t90)
    progress = -math.expm1(-k * time_s ** p)
    return {"dissolved": a * progress, "a_eq": a, "t30_s": t30, "t90_s": t90, "k": k, "p": p,
            "reactionProgress": progress, "basis": basis}


# --- Assembly ------------------------------------------------------------------------------------------------------

def _interval(request_interval: Any, props: Mapping[str, Any], preheat_C: float
              ) -> Tuple[Optional[Tuple[float, float]], str, Optional[str]]:
    """(interval or None, selection, refusal text)."""
    solidus = float(props["solidus_C"])
    if request_interval is None:
        return (solidus, preheat_C + 25.0), "declared-default", None
    try:
        high, low = float(request_interval["high_C"]), float(request_interval["low_C"])
    except (TypeError, KeyError, ValueError):
        return None, "requested", INTERVAL_TEXT
    if not (math.isfinite(high) and math.isfinite(low) and preheat_C < low < high <= solidus):
        return None, "requested", INTERVAL_TEXT
    return (high, low), "requested", None


def build_kinetics_estimates(alloy: str, thermal: Mapping[str, Any], parent: Optional[Mapping[str, Any]],
                             process: Mapping[str, float], *, options: Optional[Mapping[str, Any]] = None,
                             prop_overrides: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """v2 container: pathCoolingRate, plus kmAlphaMFraction and tiMartensiteDissolution for Ti-6Al-4V, or a
    phaseTransformation no-value for the other alloys."""
    se = _se()
    opts = dict(options or {})
    request = se.projection_request(alloy, process, "rosenthal")
    state = None
    if parent is not None:
        try:
            state = se.front_state(request, thermal, parent, prop_overrides=prop_overrides, support_resolutions=False)
        except se.StaleParent:
            state = None
    b = state["builder"] if state else se.Builder(MODEL_ID)
    b.model_id = MODEL_ID
    if state is None:
        b.add_input("frontSamples", se._record("declaredAssumption", "front-samples:none", status="outOfRange",
                                               declaration="python/lpbf_kinetics_estimates.py",
                                               scope="no captured thermal parent matching the estimate kernel"))
        b.add_input("preheat_C", qe.process_input_record("preheat_C"))
    front_ok = state is not None and state["blocked"] is None
    blocked = state["blocked"] if state else ("missing-thermal-history", NO_PATH_TEXT)
    rows = state["rows"] if state else []
    props = dict(request["props"])
    if prop_overrides:
        props.update(prop_overrides)
    preheat = float(process["preheat_C"])
    interval, selection, interval_refusal = _interval(opts.get("coolingInterval_C"), props, preheat)
    if interval is not None:
        b.add_input("coolingInterval", se._record(
            "declaredAssumption" if selection == "declared-default" else "userInput",
            f"cooling-interval:{interval[0]!r}:{interval[1]!r}", status="inRange",
            declaration=("python/lpbf_kinetics_estimates.py#DEFAULT_INTERVAL_RULE" if selection == "declared-default"
                         else "request"),
            scope=(f"{interval[0]:g} C to {interval[1]:g} C; " + (
                "declared convention: solidus to preheat plus 25 K" if selection == "declared-default"
                else "interval selected by the user"))))
    else:
        b.add_input("coolingInterval", se._record("userInput", "cooling-interval:invalid", status="outOfRange",
                                                  declaration="request", scope="invalid interval"))
    depends = ("frontSamples", "coolingInterval")
    if interval is None:
        b.no_value("pathCoolingRate", "path-average-cooling-rate", "nonphysical-input", parent="coolingInterval",
                   depends_on=depends, text=interval_refusal)
    elif not front_ok:
        b.no_value("pathCoolingRate", "path-average-cooling-rate", "parent-unavailable"
                   if blocked[0] != "missing-thermal-history" else "missing-thermal-history",
                   parent="frontSamples", depends_on=depends, text=blocked[1])
    else:
        kept, values, refused, detail = [], [], {}, []
        for sample in rows:
            try:
                out = path_cooling(parent["T_fn"], sample, parent["v_scan"], interval[0], interval[1])
            except ValueError as exc:
                refused[str(exc)] = refused.get(str(exc), 0) + 1
                continue
            kept.append(sample)
            values.append(out["rate_K_s"])
            detail.append({"sampleId": sample["sampleId"], **out})
        support = {"retained": len(kept), "refusedByReason": refused, "pathRule": PATH_RULE,
                   "intervalSelection": selection, "interval_C": list(interval)}
        if len(kept) < se.MIN_BRANCH_SAMPLES:
            tag = max(refused, key=refused.get) if refused else "missing-crossing"
            text = REHEAT_TEXT if tag == "reheating-needs-segment-rates" else PATH_TEXT.format(
                detail=f"Refused paths: {', '.join(sorted(refused)) or 'none'}.")
            b.no_value("pathCoolingRate", "path-average-cooling-rate", "missing-thermal-history",
                       parent="frontSamples", depends_on=depends, text=text, params={"gate": tag},
                       extra_validity={"localSupport": support})
        else:
            rate = se.weighted_median(values, [s["weight_m"] for s in kept])
            path_kind = "single-pass conduction-surrogate" if state["surrogate"] else "single-pass"
            b.value("pathCoolingRate", "path-average-cooling-rate", rate, depends_on=depends,
                    sources=[se.SRC_GHOSH_KINEMATICS, se.SRC_EAGAR_TSAI],
                    explanation=(f"{se.TIER2_LABEL}: the average cooling rate is about {_sig(rate)} K/s between "
                                 f"{interval[0]:g} C and {interval[1]:g} C on the selected {path_kind} path. This "
                                 f"cooling rate does not determine the final phases. {se.UNKNOWN}"),
                    construction=("(Thi - Tlo) / (t(Tlo) - t(Thi)) per retained material path, weighted median; "
                                  "crossings bisected and checked at a finer step ratio; no interval."),
                    extra_validity={"localSupport": support, "paths": detail[:8]})
    if alloy == "ti6al4v":
        se._km_quantity(b, rows, front_ok, blocked if state else ("missing-thermal-history", se.KM_MISSING_TEXT),
                        parent or {}, request)
        _dissolution_quantity(b, opts.get("isothermalHold"))
    else:
        b.add_input("phaseSelectionModel", se._record(
            "declaredAssumption", f"phase-model:{alloy}", status="outOfRange",
            declaration="python/lpbf_kinetics_estimates.py", scope="no admitted same-alloy reaction model"))
        b.no_value("phaseTransformation", "solid-state-transformation", "missing-source-bound-model",
                   parent="phaseSelectionModel", depends_on=("phaseSelectionModel",),
                   text=se.PHASE_NO_MODEL_TEXT.get(alloy, JMAK_TEXT))
    out = qe.container(b.quantities, input_provenance=b.inputs, schema=qe.ENVELOPE_SCHEMA_V2,
                       default=not (state and state["surrogate"]))
    statuses = [q["status"] for q in b.quantities.values()]
    out.update(modelId=MODEL_ID, status=("computed" if all(s == "computed" for s in statuses) else
                                         "partial" if any(s == "computed" for s in statuses) else "unavailable"),
               surrogate="conduction-field" if state and state["surrogate"] else None,
               coolingInterval={"high_C": interval[0], "low_C": interval[1], "selection": selection,
                                "rule": DEFAULT_INTERVAL_RULE if selection == "declared-default" else "requested"}
               if interval else None)
    return out


def _dissolution_quantity(b, hold: Any) -> None:
    se = _se()
    b.add_input("dissolutionModel", se._record(
        "sourceModelAssumption", "salsi2018-table3-dissolution", status="extrapolated", locator=SALSI_TABLE3_LOCATOR,
        scope="heat-treatment hardness-derived kinetic parameters for wrought/AM Ti-6Al-4V martensite dissolution; "
              "transferred to this LPBF state"))
    name, definition = "tiMartensiteDissolution", "ti-martensite-dissolution-fraction"
    if not isinstance(hold, dict):
        b.no_value(name, definition, "not-requested", parent="dissolutionModel", depends_on=("dissolutionModel",),
                   text=HOLD_TEXT, status="not-requested")
        return
    try:
        T, t = float(hold.get("temperature_C")), float(hold.get("time_s"))
    except (TypeError, ValueError):
        T = t = float("nan")
    interpolate = hold.get("interpolate") is True
    b.add_input("isothermalHold", se._record(
        "userInput", f"hold:{T!r}:{t!r}:{interpolate}", status="inRange", declaration="request",
        scope=f"isothermal hold {T:g} C for {t:g} s entered by the user"
              + ("; interpolated-temperature scenario selected" if interpolate else "")))
    depends = ("dissolutionModel", "isothermalHold")
    if not (math.isfinite(T) and math.isfinite(t) and t > 0):
        b.no_value(name, definition, "nonphysical-input", parent="isothermalHold", depends_on=depends,
                   text="Enter a finite hold temperature in C and a positive hold time in seconds.")
        return
    try:
        result = dissolved_fraction(T, t, interpolate)
    except ValueError as exc:
        text = HOLD_RANGE_TEXT if str(exc) == "outside-source-range" else HOLD_KNOT_TEXT
        b.no_value(name, definition, "outside-source-model-domain", parent="dissolutionModel", depends_on=depends,
                   text=text, params={"gate": str(exc)})
        return
    own = [se._warn("domain-extrapolation", "Source kinetic parameters are a hardness-derived heat-treatment "
                                            "interpretation, transferred to this LPBF state")]
    if result["basis"] == "interpolated-scenario":
        own.append(se._warn("domain-extrapolation", f"{T:g} C is between source knots; a_eq, t30 and t90 are "
                                                    "linearly interpolated as a declared model convention"))
    shown = _sig(result["dissolved"], 1)
    b.value(name, definition, result["dissolved"], depends_on=depends,
            sources=[qe.source_ref("salsi2018-table3", SALSI_TABLE3_LOCATOR, "primary-read")],
            own_warnings=own, fraction_basis="reaction-progress",
            explanation=(f"{se.TIER2_LABEL}: about {shown} of the martensite entering this isothermal hold has "
                         "dissolved in the selected Ti-6Al-4V model. This is a reaction-progress estimate based on "
                         "source heat-treatment parameters. It does not predict precipitate size, strength or the "
                         f"complete final phase inventory. {se.UNKNOWN}"),
            construction="JMAK through the source t30 and t90 times, scaled by a_eq; no interval.",
            extra_validity={"hold": {"temperature_C": T, "time_s": t}, "parameters": result})
