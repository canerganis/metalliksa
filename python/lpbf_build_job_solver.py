#!/usr/bin/env python3
"""
Single LPBF Build Job engine: Rosenthal melt-pool screening + STL slicer + print verdict.

The industrial UI must display this verdict. TypeScript must not re-decide printability.
Melt-pool geometry for the verdict is regularized Rosenthal. Eagar–Tsai (`eagar-tsai-v2`) is opt-in on the thermal / Melt Pool 3D lab only — it does not change this verdict.

P7a (2026-10-11): the verdict uses sourced criteria, the regime classifier and validity guards only (ladder in
compose_verdict); every unsourced edge is an advisory with the status text "unsourced screening threshold".
"""

import json
import math
import sys
import time

from four_alloy_materials import (
    ALLOY_MATERIALS,
    LITERATURE_PV_WINDOWS,
    canonical_material_source,
    evaluate_literature_pv,
    resolve_alloy_id,
)
from lpbf_build_job_schema import LpbfBuildJobRequest
from lpbf_build_job_material_snapshot import (
    MATERIAL_PROPERTY_REVISION,
    build_ambench_material_property_snapshot,
    build_build_job_identity,
    build_material_property_snapshot,
)
from lpbf_job_cache import (
    BUILD_JOB_MODEL_ID,
    BUILD_JOB_SOLVER_REVISION,
    build_cache_key,
    cache_get,
    cache_put,
)
from lpbf_screening_uq import apply_uq_prop_scales, run_screening_uq
from four_alloy_materials import ABSORPTIVITY_BASIS_UNSOURCED, kernel_properties
from lpbf_defect_diagnostics import BALLING_LW_MODERATE
from fabbro_keyhole import ENTHALPY_KEYHOLE as FABBRO_ENTHALPY_KEYHOLE  # read-only: printed ramp follows the real constants
from fabbro_keyhole import ENTHALPY_ONSET as FABBRO_ENTHALPY_ONSET
from lpbf_thermal_solver import (
    ENTHALPY_KEYHOLE,
    ENTHALPY_KEYHOLE_IN625,
    ENTHALPY_TRANSITION,
    KEYHOLE_MODE_ONSET_STATEMENT,
    LOF_MARGIN_BASIS,
    POROSITY_SCREEN_HIGH_AT,
    STRESS_UNAVAILABLE_REASON,
    calculate_meltpool_physics,
    keyhole_cut_basis,
    regime_keyhole_cut,
)
from murakami_fatigue_screening import (
    build_qualification_block,
    evaluate_murakami_block,
    parse_defect_sqrt_areas_text,
)
from nist_ambench_2018_02 import (
    IN625_VALIDATION_PROPS,
    coverage_for_alloy,
    run_ambench_validation,
)
from stl_slicer_build_time_solver import solve_slicer
from lpbf_part_porosity_aggregator import aggregate_part_porosity
from lpbf_scanner_kinematics import calculate_scanner_kinematics
from lpbf_solidification_microstructure import project_build_job_microstructure
from lpbf_solidification_segregation import build_job_segregation
import alloy_registry

# Hatch/layer used with literature-box mid P–v when LoF is the dominant gate.
# Matches src/utils/lpbfDemoVectors.ts printable demos (inputs only).
_LOF_HT = {
    "ti6al4v": {"hatch_um": 100, "layer_um": 30, "beamDiameter_um": 80},
    "ss316l": {"hatch_um": 90, "layer_um": 30, "beamDiameter_um": 80},
    "alsi10mg": {"hatch_um": 110, "layer_um": 30, "beamDiameter_um": 100},
    "in718": {"hatch_um": 90, "layer_um": 30, "beamDiameter_um": 80},
}

DEFAULT_PROCESS_SEED = 42

# Build-job alloy id -> phase-transformation kinetics model (kinetics_ttt_cct_solver,
# alloy_registry DOMAIN_KINETICS) of the SAME alloy. The kinetics registry has no model for
# 316L (austenitic stainless) or AlSi10Mg (Al-Si-Mg); AISI 4140 and Al 7075 are different
# alloys, so those build jobs carry an explicit unavailable kinetics block, never a
# substituted alloy's result.
BUILD_JOB_KINETICS_ALLOY = {"in718": "Inconel 718", "ti6al4v": "Ti-6Al-4V"}
BUILD_JOB_KINETICS_COOLING_RATE_SOURCE = None


def _finite_number(value):
    """float(value) for a finite int/float (bool excluded), else None."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    out = float(value)
    return out if math.isfinite(out) else None


def format_cooling_rate(rate):
    """Exact text for a rate in a reason: 1089047.0 -> "1089047", 2000.0000001 -> "2000.0000001"."""
    return str(int(rate)) if float(rate).is_integer() else repr(float(rate))


def build_cooling_rate_cct_row(cct_map, rate):
    """Select the CCT map row nearest (log10) to the build cooling rate; never extrapolate.

    A rate that is not a finite positive number, or lies outside the tabulated CCT cooling rates,
    gives status "unavailable" with the reason (the exact comparison for the range case), so a
    slow-cooling row is never reported for a much faster LPBF cool. At an exact log-midpoint tie
    the first row in map order wins; the solver's map is ascending, so that is the slower rate.
    """
    usable = []
    for i, row in enumerate(cct_map or []):
        r = _finite_number(row.get("coolingRate_C_s")) if isinstance(row, dict) else None
        if r is not None and r > 0.0:
            usable.append((i, r))
    rate = _finite_number(rate)
    out = {
        "selection": "nearest-log10-cooling-rate-within-map-range",
        "buildCoolingRate_C_s": rate,
        "mapRange_C_s": [min(r for _, r in usable), max(r for _, r in usable)] if usable else None,
        "rowIndex": None,
        "rowCoolingRate_C_s": None,
    }
    if rate is None or rate <= 0.0 or not usable:
        out.update(status="unavailable",
                   reason="no finite positive build cooling rate or no CCT map rows to select from")
        return out
    lo, hi = out["mapRange_C_s"]
    if rate > hi:
        out.update(status="unavailable",
                   reason=f"build cooling rate {format_cooling_rate(rate)} °C/s is above the CCT map "
                          f"maximum {format_cooling_rate(hi)} °C/s; no row is extrapolated")
        return out
    if rate < lo:
        out.update(status="unavailable",
                   reason=f"build cooling rate {format_cooling_rate(rate)} °C/s is below the CCT map "
                          f"minimum {format_cooling_rate(lo)} °C/s; no row is extrapolated")
        return out
    index, row_rate = min(usable, key=lambda item: abs(math.log10(item[1]) - math.log10(rate)))
    out.update(status="selected", reason=None, rowIndex=index, rowCoolingRate_C_s=row_rate)
    return out


def build_rate_martensite(registry_id, alloy_name, gap, cct_row):
    """Martensite fraction and verdict at the build rate, or unavailable with the reason.

    Withheld when the alloy's registry Ms is a non-physical placeholder (alloy_registry
    KINETICS_PLACEHOLDERS), when no CCT row was selected for the build rate (the CCT map is not
    extrapolated), and when the kinetics result has no martensite fraction: the Li (1998) model
    gives one (Koistinen-Marburger at 25 C) only when no diffusional start is reached above Ms.
    """
    reality = (gap or {}).get("kineticRealityAtSelectedCooling") or {}
    out = {"status": "unavailable", "reason": None, "predictedMartensite_pct": None, "verdict": None,
           "coolingRate_C_s": _finite_number(reality.get("coolingRate_C_s"))}
    if (registry_id, "Ms_C") in alloy_registry.KINETICS_PLACEHOLDERS:
        out["reason"] = (f"the kinetics registry Ms of {alloy_name} is a non-physical placeholder (the alloy "
                         "does not form martensite on quenching); no martensite fraction or "
                         "martensite-based verdict is reported")
        return out
    if (cct_row or {}).get("status") != "selected":
        out["reason"] = (f"{(cct_row or {}).get('reason') or 'no CCT row selected'}; the steel-type "
                         "martensite fraction and verdict are not reported at this rate either")
        return out
    pct = _finite_number(reality.get("predictedMartensite_pct"))
    if pct is None:
        out["reason"] = "the kinetics result has no finite martensite fraction"
        return out
    out.update(status="available", predictedMartensite_pct=pct, verdict=reality.get("verdict"))
    return out


def _unavailable_kinetics_block(alloy_id, reason, reported, degenerate):
    return {
        "success": False,  # legacy envelope shape; "status" is authoritative
        "status": "unavailable",
        "reason": reason,
        "alloyId": alloy_id,
        "alloy": None,
        "buildCoolingRate_C_s": None if degenerate else reported,
        "reportedCoolingRate_K_s": reported,
        "coolingRateSource": BUILD_JOB_KINETICS_COOLING_RATE_SOURCE,
        "cctContinuousCoolingMap": None,
        "calphadVsKineticsGap": None,
        "buildCoolingRateCctRow": None,
        "buildRateMartensite": None,
    }


MURAKAMI_SCENARIO_KEYS = ("defectSqrtArea_um", "defectEvidence", "defectLocation", "hardnessEvidence", "loadRatio",
                          "cycleTarget", "specimenOrientation", "defectIsLongCrack", "defectSampling",
                          "ctDetectionMethod")


def _murakami_block(data, alloy_id):
    """Group 7 block from the explicit request fields only; no hardness, size or cycle default exists."""
    return evaluate_murakami_block(
        data.get("defectSqrtAreas_um"),
        hardness_HV=data.get("hardness_HV"),
        ct_detection_threshold_um=data.get("ctDetectionThreshold_um"),
        alloy_id=alloy_id,
        defect_paste=data.get("defectSqrtAreasPaste"),
        scenario={key: data.get(key) for key in MURAKAMI_SCENARIO_KEYS},
    )


def _mechanics_block(data, thermal):
    from lpbf_mechanics_scenarios import evaluate_mechanics
    solidus = ((thermal.get("processParameters") or {}).get("solidus_C")
               if isinstance(thermal, dict) else None)
    if solidus is None:
        from four_alloy_materials import thermal_props
        props = thermal_props(ALLOY_MATERIALS[data["alloyId"]]["thermal"]) if data.get("alloyId") in ALLOY_MATERIALS \
            else None
        solidus = props.get("solidus_C") if props else None
    return evaluate_mechanics(data.get("mechanicsScenario"), alloy_id=data.get("alloyId"), solidus_C=solidus)


def build_job_kinetics(alloy_id, thermal, front_parent=None, process=None, options=None, prop_overrides=None):
    """Kinetics block for a build job; never a substitute alloy or a steel model.

    ``status`` is the field to trust. The legacy CCT keys stay null: a single-pass cooling average cannot select a CCT
    row and no admitted CCT model exists for these alloys. ``estimates`` (quantity envelope v2, SPEC engine estimates
    group 8) carries the path cooling observable at a named subsolidus interval on the build's own captured front
    parent, and for Ti-6Al-4V the first-pass KM reference and the isothermal dissolution reference, all Tier 2. Without
    a captured parent every estimate is no-value with missing-thermal-history.
    """
    from quantity_envelope import reason, reason_text
    from lpbf_kinetics_estimates import build_kinetics_estimates
    block = _unavailable_kinetics_block(alloy_id, reason_text("missing-thermal-history"), None, False)
    block["reasons"] = [reason("missing-thermal-history")]
    block["coolingRateSource"] = None
    if process is None:
        return block
    estimates = build_kinetics_estimates(alloy_id, thermal, front_parent, process, options=options,
                                         prop_overrides=prop_overrides)
    block["estimates"] = estimates
    block["alloy"] = ALLOY_MATERIALS[alloy_id]["thermal"] if alloy_id in ALLOY_MATERIALS else None
    cooling = estimates["quantities"]["pathCoolingRate"]
    if cooling["value"] is not None:
        interval = estimates["coolingInterval"]
        source = (estimates["modelId"] + ": single-pass path average between " + format(interval["high_C"], "g")
                  + " C and " + format(interval["low_C"], "g") + " C")
        block.update(status="partial", success=True, reason=None, reasons=[],
                     buildCoolingRate_C_s=cooling["value"], reportedCoolingRate_K_s=cooling["value"],
                     coolingRateSource=source)
    elif estimates["status"] != "unavailable":
        block.update(status="partial", success=True)
    return block


def _gate(gid, status, measured, required, unit, note, basis=None):
    out = {
        "id": gid,
        "status": status,
        "measured": measured,
        "required": required,
        "unit": unit,
        "note": note,
    }
    if basis is not None:
        out["basis"] = basis
    return out


# Number of power and speed levels per axis in the suggested-patch grid search over the literature box.
PATCH_GRID_LEVELS = 5


def _patch_dict(power, speed, hatch, layer, beam):
    return {
        "laserPower_W": int(round(power)),
        "scanSpeed_mms": int(round(speed)),
        "hatch_um": int(round(hatch)),
        "layer_um": int(round(layer)),
        "beamDiameter_um": int(round(beam)),
    }


def _patch_candidates(thermal, alloy_id, dominant_gate):
    """Ordered candidate points: the literature-box heuristic first, then a P-v grid over the box nearest the
    current point, current hatch/layer/beam before the per-alloy conduction set (_LOF_HT). Each is a patch dict."""
    box = LITERATURE_PV_WINDOWS[alloy_id]
    pp = thermal["processParameters"]
    cur_p = float(pp["laserPower_W"])
    cur_v = float(pp["scanSpeed_mm_s"])
    cur_h = float(pp["hatchSpacing_um"])
    cur_t = float(pp["layerThickness_um"])
    cur_d = float(pp["beamDiameter_um"])
    ht = _LOF_HT.get(alloy_id, {"hatch_um": 100, "layer_um": 30, "beamDiameter_um": cur_d})
    mid_p = (box["powerMin_W"] + box["powerMax_W"]) / 2.0
    mid_v = (box["speedMin_mm_s"] + box["speedMax_mm_s"]) / 2.0
    out = []
    if dominant_gate == "keyhole":
        out.append(_patch_dict(box["powerMin_W"], box["speedMax_mm_s"], cur_h, cur_t, cur_d))
    elif dominant_gate in ("lof_tang", "lof_wh", "lof_dt"):
        out.append(_patch_dict(mid_p, mid_v, ht["hatch_um"], ht["layer_um"], ht["beamDiameter_um"]))
    else:
        out.append(_patch_dict(mid_p, mid_v, cur_h, cur_t, cur_d))
    p_span = max(1e-9, box["powerMax_W"] - box["powerMin_W"])
    v_span = max(1e-9, box["speedMax_mm_s"] - box["speedMin_mm_s"])
    n = PATCH_GRID_LEVELS
    grid = [
        (box["powerMin_W"] + p_span * i / (n - 1), box["speedMin_mm_s"] + v_span * j / (n - 1))
        for i in range(n) for j in range(n)
    ]
    grid.sort(key=lambda pv: ((pv[0] - cur_p) / p_span) ** 2 + ((pv[1] - cur_v) / v_span) ** 2)
    for hatch, layer, beam in ((cur_h, cur_t, cur_d), (ht["hatch_um"], ht["layer_um"], ht["beamDiameter_um"])):
        out.extend(_patch_dict(p, v, hatch, layer, beam) for p, v in grid)
    seen, unique = set(), []
    for cand in out:
        key = tuple(sorted(cand.items()))
        if key not in seen:
            seen.add(key)
            unique.append(cand)
    return unique


def _verified_patch(thermal, alloy_id, dominant_gate, verdict, evaluate=None):
    """(patch, note, advisories). A patch is suggested only when the served solver, re-run at the suggested point,
    returns a printable verdict under the current ladder (Tang bump, 2026-10-27): geometry resolved, verdict inputs not
    null, Tang overlap index at or below 1.0 on modelled geometry, below the keyhole-mode cut. The literature box is
    only the search range (a display range, not a window); the box, balling, the keyhole level 30, the Tang margin and
    downskin are advisories, reported for the suggested point in the third element. The note states the Tang index of
    the point and that fusion adequacy is not established; a point is never called fusion verified.
    Selection prefers the first printable candidate with zero advisories, else the first printable one. Without an
    evaluator (hand-built thermal input, UQ samples) no patch is offered.
    The downskin caveat of the note is added by _suggested_patch."""
    if verdict == "printable":
        return None, None, []
    if dominant_gate in (None, "none"):
        if verdict == "inconclusive":
            # P7a merge-gate fix: an inconclusive verdict has no dominant gate by construction; say why no patch
            # is searched instead of claiming that no gate fails.
            return None, ("The verdict is inconclusive (geometry not resolved or a verdict-driving input null), so "
                          "no parameter patch is searched: a patch would be verified against unresolved numbers."), []
        return None, "No verdict-driving gate is raised, so there is no parameter change to suggest.", []
    if evaluate is None:
        return None, "No parameter patch: the solver was not available to verify a suggested point.", []
    first = None
    for cand in _patch_candidates(thermal, alloy_id, dominant_gate):
        th = evaluate(cand["laserPower_W"], cand["scanSpeed_mms"], cand["hatch_um"], cand["layer_um"],
                      cand["beamDiameter_um"])
        check = compose_verdict(th, alloy_id)
        if check["verdict"] != "printable":
            continue
        if not check["advisories"]:
            first = (cand, check)
            break
        if first is None:
            first = (cand, check)
    if first is not None:
        cand, check = first
        advisories = list(check["advisories"])
        keyhole_gate = next(g for g in check["gates"] if g["id"] == "keyhole")
        note = (
            f"Re-run by the solver at the suggested point: geometry resolved, below the keyhole-mode cut (ΔH/hₛ "
            f"{keyhole_gate['measured']} < {keyhole_gate['required']}), Tang overlap index "
            f"{check['lofGeometry']['tangIndex']} on modelled geometry (at or below 1.0); verdict "
            f"{check['verdict']} (screening result; fusion adequacy is not established). "
            "The literature box is a search range (display range, not a window). Downskin, if requested, is unchanged "
            "by these parameters. Advisories at the suggested point: "
            + ("; ".join(advisories) if advisories else "none")
        )
        return cand, note, advisories
    return None, (
        "No parameter patch: no point of a "
        f"{PATCH_GRID_LEVELS}x{PATCH_GRID_LEVELS} power-speed grid over the {alloy_id} literature search range (display "
        "range, not a window), with the current or the per-alloy conduction hatch, layer and beam, has a Tang overlap "
        "index at or below 1.0 below the keyhole-mode cut with resolved geometry (printable verdict) in the served "
        "solver."
    ), []


def _suggested_patch(thermal, alloy_id, dominant_gate, verdict, evaluate=None, gates=None):
    """(patch, note, advisories) from _verified_patch, plus the downskin caveat (a6f57f66, kept under P7a). Since P7a
    the downskin gate is an advisory (never fail or warn, never dominant), so when it is raised while another gate
    drives the verdict, a power, speed, hatch or layer patch cannot clear the overhang: the note says the downskin
    advisory stays whatever the patch does. Older payload gate statuses fail/warn get the former wording."""
    patch, note, advisories = _verified_patch(thermal, alloy_id, dominant_gate, verdict, evaluate)
    if verdict == "printable" or dominant_gate == "downskin":
        return patch, note, advisories
    down = next((g for g in (gates or []) if g.get("id") == "downskin"
                 and g.get("status") in ("advisory", "fail", "warn")), None)
    if down is not None:
        where = "" if down.get("measured") is None else f" at {down['measured']} deg"
        if down["status"] == "advisory":
            stays = "the downskin advisory stays"
        else:
            stays = f"the job stays {'do-not-print' if down['status'] == 'fail' else 'risky'} on downskin"
        note = (f"{note or ''} The downskin gate is {down['status']}{where}, and no power, speed, hatch or layer change "
                f"fixes an overhang: {stays}{' even with this patch' if patch else ''}.").strip()
    return patch, note, advisories


# Gates whose result is a function of the melt-pool W/D/L extent. When the thermal solver
# reports ``extentStatus != "computed"`` (heuristic fallback, width floor, search-box limit)
# these are unavailable: a verdict must not be built from screening-heuristic numbers.
GEOMETRY_DEPENDENT_GATES = ("lof_tang", "lof_wh", "lof_dt", "balling")

# P7a (2026-10-11, docs/research/SPEC_p7a_rules_and_nulls_2026-10-11.md) and the Tang bump (2026-10-27,
# docs/LPBF_IMPLEMENTATION_BUMP_2026-10-27_tang-advisory.reasons.md, physics gate finding 1): ladder inconclusive
# (geometry not resolved or a verdict-driving input null: the Tang index, width, depth or dH/hs) > risky (Tang overlap
# index above 1.0 on modelled geometry, or the served regime is keyhole mode; every applying cause is reported) >
# printable. The Tang index uses the sourced geometric unit bound (Harkin 2023 Eq. 5) on modelled, not measured,
# geometry, so it indicates a possible lack of fusion (lof_tang status "warn", a risk gate), never a blocking gate:
# no rule of this ladder issues do-not-print. Everything else is an advisory ("unsourced screening threshold").
VERDICT_BASIS = "model-geometry-tang-keyhole-risk-screen"
UNSOURCED_SCREENING_THRESHOLD = "unsourced screening threshold"
# Stress and distortion gates: not evaluated since P7a (no sourced stress model; G1 audit B08, B09). They are advisory
# gates, listed in unavailableGates, and never make the verdict inconclusive.
ADVISORY_GATES = ("recoater", "distortion")
STRESS_GATES_NOT_EVALUATED_NOTE = (
    "not evaluated since P7a (2026-10-11): " + STRESS_UNAVAILABLE_REASON + "; the former index 0.72 E alpha dT / (1 - nu) "
    "x (layer / 40 um) / 420 MPa used unsourced constants and is not served; advisory gate, never a verdict input "
    "(never counted as pass or fail)"
)
# Kept for older payloads and the process-window grid note (the former alloy/layer index, no longer served).
PARAMETER_INDEPENDENT_ADVISORY_NOTE = (
    "alloy/layer advisory independent of P, v and hatch: the former distortion index depended only on "
    "alloy properties, preheat and layer thickness (not on P, v or hatch); it does not change the verdict"
)
TANG_CRITERION_BASIS = (
    "Tang criterion as quoted in Harkin 2023 Eq. 5, primary not in the library; sourced for measured melt pool "
    "geometry; with analytic geometry Harkin 2023 Eq. 9 to 11 and Conclusions find the unit value problematic "
    "(Ti-6Al-4V, one machine); here applied to modelled geometry (model width and a depth merged from the conduction "
    "and Fabbro legs, not a measured half-ellipse), so since 2026-10-27 an index above 1.0 indicates a risk, never a "
    "blocking gate"
)
# The Tang risk reason of the physics gate, finding 1 (verbatim).
TANG_RISK_REASON = (
    "Modelled geometry indicates possible lack of fusion (Tang overlap index above 1.0); not an experimentally "
    "established defect."
)
FUSION_NOT_ESTABLISHED = "Screening result; fusion adequacy is not established."
LOF_DIAGNOSTIC_BASIS = (UNSOURCED_SCREENING_THRESHOLD + " removed: the former required values 1.05 (W/h) and 1.15 "
                        "(D/t) had no source, so required is null and the status is always pass; diagnostic ratio only, "
                        "the Tang overlap index is the lack-of-fusion screen (P7a, G1 audit V20; risk, not blocking, since 2026-10-27)")
KEYHOLE_LEVEL_30_ADVISORY_BASIS = (UNSOURCED_SCREENING_THRESHOLD + ", legacy porosity level kept for continuity, not a "
                                   "porosity boundary")
ZHAO_BAND_ADVISORY_BASIS = ("no pore condition below 15 in Zhao 2020 (0 of 35), not evidence of safety; Ti-6Al-4V pores "
                            "at 16 to 28 for v <= 445 mm/s")
LITERATURE_PV_ADVISORY_BASIS = (
    UNSOURCED_SCREENING_THRESHOLD + ": P-v display range, no table or figure for any edge; windows depend on spot size "
    "and layer thickness (Hofmann 2026 Fig. 5, PDF p.5); a single track window does not ensure bulk printing (Vaglio "
    "and Totis 2020)"
)
DOWNSKIN_ADVISORY_BASIS = (UNSOURCED_SCREENING_THRESHOLD + ": no primary source with a locator retrieved (SWP 2.8); "
                           "reported limits depend on alloy and exposure strategy")
BALLING_HIGH_ADVISORY_BASIS = (
    UNSOURCED_SCREENING_THRESHOLD + " (Moderate 3.85, a Yadroitsev et al. 2010 Eq. 13 cylinder-bound proxy applied to "
    "the model pool L/W, is the only advisory band); no High band since P7b (2026-10-14): the former in-sample 316L "
    "edge 5.5 (Hofmann 2026, Zenodo 16979848) was fitted on the Eagar-Tsai geometry of the fitting commit, and P7b "
    "changed that geometry (absorptivity authority, melting-point and kernel-ledger properties)"
)
# P1 (2026-10-11): at dH/hs >= ENTHALPY_TRANSITION the served depth is the Fabbro leg with a flat absorptivity, so
# transition and keyhole depth is biased low (keyhole absorptance A(R) not modelled).
KEYHOLE_DEPTH_BIAS_LOF_NOTE = (
    f"At dH/hs >= {ENTHALPY_TRANSITION:g} the transition and keyhole depth is biased low because the keyhole "
    "absorptance A(R) is not modelled, so a lack-of-fusion fail in this regime may be a model artefact."
)
BALLING_SCREEN_NOTE = (
    "Eagar-Tsai aspect-ratio screen (model L/W uncertainty about +-10 %); the Hofmann 2026 316L single tracks "
    "(Zenodo 10.5281/zenodo.16979848) are recorded evidence per L/W bin, not a threshold since P7b (the former "
    "in-sample High edge was fitted on a geometry P7b changed); low recall is documented there (69/216 balled tracks "
    "above the former edge, 3/38 at a 140 um spot), so a low L/W is not balling-cleared; not a demonstrated balling "
    "prediction for any alloy; an advisory since P7a, never a verdict input"
)
BALLING_LITERATURE_NOTE = (
    "pi*sqrt(3/2) segmental-cylinder bound of Yadroitsev et al. 2010 (J. Mater. Process. Technol. 210:1624, "
    "doi 10.1016/j.jmatprotec.2010.05.010, Eq. 13; D is the cylinder diameter, applied here to the model pool L/W); "
    "mechanism Gusarov, Yadroitsev, Bertrand & Smurov 2007 (Appl. Surf. Sci. 254:975, "
    "doi 10.1016/j.apsusc.2007.08.074: Plateau-Rayleigh break-up when the track length exceeds its circumference)"
)
# The High/Moderate thresholds were calibrated on flat-plate-absorptivity Eagar-Tsai geometry; the
# Eagar-Tsai L/W scales roughly as sqrt(A), so another absorption model is disclosed, never re-banded.
BALLING_CALIBRATION_ABSORPTION_MODEL = "flat-plate"
_LEGACY_BALLING_BANDS = (("High", "high"), ("Moderate", "moderate"), ("Stable", "stable"))


def _balling_screen_of(def_):
    """(band, screen) from defectDiagnostics.ballingScreen; a thermal dict without the screen (hand-built
    test input) falls back to the ballingInstabilityRisk prefix with no L/W."""
    screen = def_.get("ballingScreen")
    if isinstance(screen, dict):
        return screen.get("band"), screen
    risk = str(def_.get("ballingInstabilityRisk") or "")
    for prefix, band in _LEGACY_BALLING_BANDS:
        if risk.startswith(prefix):
            return band, {}
    return None, {}


def _alloy_thermal_name(alloy_id):
    return ALLOY_MATERIALS[alloy_id]["thermal"] if alloy_id in ALLOY_MATERIALS else str(alloy_id)


def _keyhole_mode(geometry):
    """True when the served regime classifier says keyhole mode (classify_enthalpy_regime label)."""
    return str(geometry.get("regime") or "").startswith("Keyhole Mode")


def compose_verdict(thermal, alloy_id, extras=None):
    extras = extras or {}
    geometry = thermal["meltPoolGeometry"]
    extent_status = str(geometry.get("extentStatus") or "not-reported")
    extent_note = geometry.get("extentNote")
    geometry_resolved = extent_status == "computed"
    geometry_reason = None
    if not geometry_resolved:
        geometry_reason = (
            f"melt-pool geometry not resolved ({extent_status}): "
            f"{extent_note if extent_note else 'no extentNote reported'}"
        )
    # P6 containment (2026-10-11): a null gate input is "not evaluated", never pass or fail. Peak temperature, recoil,
    # Marangoni, denudation and G/R are not verdict inputs; the inputs read here are geometry and defect numbers.
    not_evaluated = {}
    W = _finite_number(thermal["meltPoolGeometry"].get("width_um"))
    D = _finite_number(thermal["meltPoolGeometry"].get("depth_um"))
    h = float(thermal["processParameters"]["hatchSpacing_um"])
    t = float(thermal["processParameters"]["layerThickness_um"])
    width_over_hatch = None if W is None else W / max(1e-6, h)
    depth_over_layer = None if D is None else D / max(1e-6, t)
    def_ = thermal["defectDiagnostics"]
    tang = _finite_number(def_.get("tangIndex_hW_tD", def_.get("lackOfFusionOverlapIndex")))
    if tang is None or W is None or D is None:
        for gid in ("lof_tang", "lof_wh", "lof_dt"):
            not_evaluated[gid] = "lack-of-fusion input (Tang index, width or depth) is null"
    lof_status = def_.get("lackOfFusionStatus")
    # One lack-of-fusion screen, the Tang unit criterion (served status Fail, or the index itself above 1.0 for a
    # hand-built dict). Since the Tang bump (2026-10-27) lof_fail makes the verdict risky (never do-not-print). The
    # 0.80 margin is an advisory flag only (the former "Warning" status of older payloads too).
    lof_fail = "lof_tang" not in not_evaluated and (lof_status == "Fail" or (tang is not None and tang > 1.0))
    lof_margin = ("lof_tang" not in not_evaluated and not lof_fail
                  and (bool(def_.get("lackOfFusionMarginAdvisory")) or lof_status == "Warning"
                       or (tang is not None and tang > 0.80)))
    dh = _finite_number(thermal["processParameters"].get("normalizedEnthalpy"))
    keyhole_mode = _keyhole_mode(geometry)
    keyhole_cut = _finite_number(geometry.get("regimeKeyholeThreshold"))
    if keyhole_cut is None:
        keyhole_cut = regime_keyhole_cut(_alloy_thermal_name(alloy_id))
    keyhole_basis = geometry.get("regimeKeyholeCutBasis") or keyhole_cut_basis(_alloy_thermal_name(alloy_id))
    if dh is None:
        not_evaluated["keyhole"] = "normalised enthalpy is null"
        keyhole_mode = False
    keyhole_level30 = dh is not None and dh >= POROSITY_SCREEN_HIGH_AT
    keyhole_band = dh is not None and ENTHALPY_TRANSITION <= dh < keyhole_cut
    balling_band, balling = _balling_screen_of(def_)
    balling_high = balling_band == "high"
    balling_moderate = balling_band == "moderate"
    balling_unavailable = balling_band is None
    balling_lw = balling.get("lengthToWidth")
    balling_lw_text = "n/a" if balling_lw is None else f"{float(balling_lw):.2f}"
    absorption_model = thermal["processParameters"].get("absorptionModel")
    balling_absorption_note = None
    if absorption_model not in (None, BALLING_CALIBRATION_ABSORPTION_MODEL) and balling_band is not None:
        balling_absorption_note = (
            f"Balling screen absorptivity: this run uses the {absorption_model} absorption model, but the L/W "
            f"thresholds were calibrated on {BALLING_CALIBRATION_ABSORPTION_MODEL} absorptivity (Eagar–Tsai L/W "
            "scales roughly as sqrt(A)); the band is reported unchanged."
        )
    win = evaluate_literature_pv(
        alloy_id,
        float(thermal["processParameters"]["laserPower_W"]),
        float(thermal["processParameters"]["scanSpeed_mm_s"]),
    )

    downskin_angle = extras.get("downskinOverhang_deg")
    # P7a: the downskin angles 45 and 55 are unsourced screening thresholds; one advisory above 45, no verdict effect.
    downskin_advisory = downskin_angle is not None and float(downskin_angle) > 45.0

    if not geometry_resolved:
        # Geometry-derived flags are heuristic here: neutralise them so no reason, verdict or
        # dominant gate is built from screening-substitute W/D/L numbers.
        lof_fail = lof_margin = balling_high = balling_moderate = False

    reasons = []
    if not geometry_resolved:
        reasons.append(
            f"Lack-of-fusion (Tang h/W, t/D, W/h, D/t) and balling (L/W) gates unavailable: "
            f"{geometry_reason.rstrip('.')}. "
            "No print / do-not-print verdict is issued from heuristic geometry."
        )
    if not_evaluated:
        reasons.append(
            "Gate(s) not evaluated because their input is null (P6 containment): "
            + "; ".join(f"{gid} ({why})" for gid, why in sorted(not_evaluated.items()))
            + ". A null input is never counted as pass or fail."
        )
    if lof_fail:
        tang_reason = (
            f"{TANG_RISK_REASON} Index (h/W)²+(t/D)² = {tang:.3f} (risk above 1.0, Harkin 2023 Eq. 5); "
            f"W/h = {width_over_hatch:.2f}, D/t = {depth_over_layer:.2f}. {TANG_CRITERION_BASIS}."
        )
        if dh is not None and dh >= ENTHALPY_TRANSITION:
            tang_reason += " " + KEYHOLE_DEPTH_BIAS_LOF_NOTE
        reasons.append(tang_reason)
    if keyhole_mode:
        reasons.append(
            f"Keyhole mode by the served regime classifier: ΔH/hₛ = {dh} at or above the cut {keyhole_cut:g} "
            f"({geometry.get('regime')}). A regime label, not a porosity claim: {keyhole_basis}."
        )
    if geometry_resolved and balling_unavailable:
        reasons.append(
            f"Balling screen unavailable: Eagar–Tsai melt-pool extent not resolved "
            f"({balling.get('extentStatus', 'not reported')}); no balling band is assigned and the verdict does "
            "not include a balling screen."
        )
    advisories = []
    if lof_margin:
        advisories.append(
            f"Advisory: Tang margin — (h/W)²+(t/D)² = {tang:.3f} is above 0.80 ({LOF_MARGIN_BASIS}). "
            "It does not change the verdict."
        )
    if keyhole_level30:
        advisories.append(
            f"Advisory: keyhole porosity legacy level — ΔH/hₛ = {dh} ≥ {POROSITY_SCREEN_HIGH_AT:g} "
            f"({KEYHOLE_LEVEL_30_ADVISORY_BASIS}; {KEYHOLE_MODE_ONSET_STATEMENT}). It does not change the verdict."
        )
    if keyhole_band:
        advisories.append(
            f"Advisory: transition band — ΔH/hₛ = {dh} in {ENTHALPY_TRANSITION:g} to {keyhole_cut:g} "
            f"({ZHAO_BAND_ADVISORY_BASIS}); porosity unresolved, this index does not resolve it. It does not change "
            "the verdict."
        )
    if balling_absorption_note and geometry_resolved:
        advisories.append("Advisory: " + balling_absorption_note)
    # P7b: no High band exists any more; an older payload carrying band "high" is reported as the Moderate advisory.
    if balling_moderate or balling_high:
        advisories.append(
            f"Advisory: balling screen Moderate — Eagar–Tsai L/W = {balling_lw_text} > 3.85, the "
            f"{BALLING_LITERATURE_NOTE}; {balling.get('hofmannBalledFractionInBand') or 'n/a'} Hofmann 316L tracks "
            "in this band balled (316L only, L/W uncertainty about +-10 %). It does not change the verdict."
        )
    if downskin_advisory:
        advisories.append(
            f"Advisory: downskin overhang {float(downskin_angle):.1f}° from vertical is above 45° "
            f"({DOWNSKIN_ADVISORY_BASIS}); expect support or stripe reorient. It does not change the verdict."
        )
    if not win["inside"]:
        box = win["box"]
        advisories.append(
            f"Advisory: P–v is outside the {alloy_id} literature display range "
            f"({box['powerMin_W']}–{box['powerMax_W']} W, {box['speedMin_mm_s']}–{box['speedMax_mm_s']} mm/s): "
            f"{LITERATURE_PV_ADVISORY_BASIS}. It does not change the verdict."
        )

    # Ladder (Tang bump, 2026-10-27, physics gate finding 1): Tang above 1.0 or keyhole mode -> risky; a null Tang,
    # width, depth or dH/hs input or an unresolved geometry -> inconclusive below; never do-not-print.
    verdict = "printable"
    if lof_fail or keyhole_mode:
        verdict = "risky"
    verdict_gate_not_evaluated = "lof_tang" in not_evaluated or "keyhole" in not_evaluated
    if not geometry_resolved or verdict_gate_not_evaluated:
        verdict = "inconclusive"

    if not reasons:
        reasons.append(
            f"No verdict-driving gate is raised; regime: {geometry.get('regime') or 'not reported'}. "
            f"{FUSION_NOT_ESTABLISHED} VED is not used as the sole criterion."
        )

    n_adv = len(advisories)
    advisory_word = "advisory" if n_adv == 1 else "advisories"
    inconclusive_headline = (
        f"Inconclusive — melt-pool geometry not resolved ({extent_status}); see reasons" if not geometry_resolved
        else "Inconclusive — a verdict-driving gate was not evaluated (null input, never pass or fail); see reasons"
    )
    risk_causes = []
    if lof_fail:
        risk_causes.append("possible lack of fusion (Tang overlap index above 1.0 on modelled geometry)")
    if keyhole_mode:
        risk_causes.append("keyhole mode by the regime classifier")
    headline = {
        "printable": (f"Printable — screening result, fusion adequacy is not established ({n_adv} {advisory_word}); "
                      "see advisories"),
        "risky": (f"Risky — {' and '.join(risk_causes)}; {FUSION_NOT_ESTABLISHED[0].lower()}{FUSION_NOT_ESTABLISHED[1:-1]}; "
                  "qualify with coupon builds before flight hardware"),
        "inconclusive": inconclusive_headline,
    }[verdict]

    balling_screened = geometry_resolved and not balling_unavailable
    if geometry_resolved and balling_unavailable:
        # A verdict without the balling screen is not balling-cleared: say so in the headline.
        headline += " (balling not screened: Eagar–Tsai extent not computed)"

    lw = None if width_over_hatch is None else round(width_over_hatch, 3)
    dt = None if depth_over_layer is None else round(depth_over_layer, 3)
    tang_r = None if tang is None else round(tang, 3)
    tang_status = "warn" if lof_fail else "pass"
    kh_status = ("warn" if keyhole_mode else "advisory" if (keyhole_band or keyhole_level30) else "pass")
    ball_status = ("advisory" if (balling_high or balling_moderate)
                   else "unavailable" if balling_unavailable else "pass")
    lit_status = "pass" if win["inside"] else "advisory"
    ds_status = "advisory" if downskin_advisory else "pass"
    ball_measured = None if balling_lw is None else round(float(balling_lw), 2)

    gates = [
        _gate(
            "lof_tang",
            tang_status,
            tang_r,
            1.0,
            "1",
            "Tang overlap index (h/W)²+(t/D)² on modelled melt-pool geometry — above 1.0 → warn (risky: possible lack "
            "of fusion, not an experimentally established defect), never blocking (never do-not-print). Index above "
            "0.80: margin advisory only.",
            basis=TANG_CRITERION_BASIS,
        ),
        _gate(
            "lof_wh",
            "pass",
            lw,
            None,
            "1",
            "Diagnostic melt-pool width / hatch (W/h). Informational, never a gate; no sourced threshold; the Tang index "
            "is the lack-of-fusion screen.",
            basis=LOF_DIAGNOSTIC_BASIS,
        ),
        _gate(
            "lof_dt",
            "pass",
            dt,
            None,
            "1",
            "Diagnostic melt-pool depth / layer (D/t). Informational, never a gate; no sourced threshold; the Tang index "
            "is the lack-of-fusion screen.",
            basis=LOF_DIAGNOSTIC_BASIS,
        ),
        _gate(
            "keyhole",
            kh_status,
            dh,
            keyhole_cut,
            "1",
            f"Keyhole mode by the served regime classifier on ΔH/hₛ (cut {keyhole_cut:g}): warn (risky), never "
            f"do-not-print. Advisories: {ENTHALPY_TRANSITION:g} to cut transition band (Zhao 2020), legacy level "
            f"≥ {POROSITY_SCREEN_HIGH_AT:g} (unsourced screening threshold). Porosity unresolved.",
            basis=keyhole_basis,
        ),
        _gate(
            "balling",
            ball_status,
            ball_measured,
            round(BALLING_LW_MODERATE, 3),
            "1",
            "Eagar–Tsai liquidus L/W (beam-size aware, whatever kernel the job uses for W/D): Moderate (> 3.85 = "
            "π√(3/2), Yadroitsev et al. 2010 Eq. 13 / Gusarov et al. 2007 mechanism) → advisory; no High band since "
            "P7b; Eagar–Tsai extent not computed → unavailable. Aspect-ratio screen, not a demonstrated balling "
            "prediction; no verdict effect.",
            basis=BALLING_HIGH_ADVISORY_BASIS,
        ),
        _gate(
            "literature_pv",
            lit_status,
            1.0 if win["inside"] else 0.0,
            1.0,
            "inside",
            "Four-alloy published P–v display range (screening envelope, not OEM machine limits); outside → advisory, "
            "no verdict effect.",
            basis=LITERATURE_PV_ADVISORY_BASIS,
        ),
        _gate(
            "recoater",
            "not-evaluated",
            None,
            None,
            "index",
            "Recoater-crash flag: not evaluated (no sourced stress model since P7a). Advisory gate, never a verdict input.",
            basis=STRESS_UNAVAILABLE_REASON,
        ),
        _gate(
            "distortion",
            "not-evaluated",
            None,
            None,
            "index",
            "Distortion index: not evaluated (no sourced stress model since P7a). Advisory gate, never a verdict input.",
            basis=STRESS_UNAVAILABLE_REASON,
        ),
        _gate(
            "downskin",
            ds_status,
            None if downskin_angle is None else round(float(downskin_angle), 1),
            45.0,
            "deg",
            "Overhang from vertical: > 45° advisory (unsourced screening threshold), no verdict effect. Omitted angle → pass.",
            basis=DOWNSKIN_ADVISORY_BASIS,
        ),
    ]
    unavailable_gates = []
    for g in gates:
        if g["id"] in not_evaluated:
            g["status"] = "not-evaluated"
            g["measured"] = None
            g["reason"] = f"not evaluated: {not_evaluated[g['id']]} (never counted as pass or fail)"
        elif g["id"] in ADVISORY_GATES:
            g["reason"] = STRESS_GATES_NOT_EVALUATED_NOTE
            unavailable_gates.append(g["id"])
    if geometry_resolved and balling_unavailable:
        for g in gates:
            if g["id"] == "balling":
                g["reason"] = f"Eagar–Tsai melt-pool extent not resolved ({balling.get('extentStatus', 'not reported')})"
        unavailable_gates.append("balling")
    if not geometry_resolved:
        for g in gates:
            if g["id"] in GEOMETRY_DEPENDENT_GATES:
                g["status"] = "unavailable"
                g["measured"] = None
                g["reason"] = geometry_reason
                unavailable_gates.append(g["id"])
    geometry_independent_fail_gates = (
        [g["id"] for g in gates if g["status"] == "fail"] if not geometry_resolved else []
    )
    if geometry_independent_fail_gates:
        reasons.append(
            "Geometry-independent gate(s) already failing: "
            + ", ".join(geometry_independent_fail_gates)
            + " (these do not depend on the unresolved melt-pool extent)."
        )
    # Advisories last, after every verdict-driving reason.
    reasons.extend(advisories)
    dominant = "none"
    for g in gates:
        if g["status"] == "fail":
            dominant = g["id"]
            break
    if dominant == "none":
        for g in gates:
            if g["status"] == "warn":
                dominant = g["id"]
                break

    patch, patch_note, patch_advisories = _suggested_patch(
        thermal, alloy_id, dominant, verdict, extras.get("patchEvaluator"), gates)
    return {
        "verdict": verdict,
        "verdictBasis": VERDICT_BASIS,
        "headline": headline,
        "reasons": reasons,
        "lofGeometry": {
            "widthOverHatch": lw,
            "depthOverLayer": dt,
            "tangIndex": tang_r,
            "hOverW": None if W is None else round(h / max(1e-6, W), 3),
            "tOverD": None if D is None else round(t / max(1e-6, D), 3),
        },
        "lackOfFusionMarginAdvisory": bool(lof_margin),
        "literatureWindow": win,
        "gates": gates,
        "dominantGate": dominant,
        "suggestedPatch": patch,
        "suggestedPatchNote": patch_note,
        "suggestedPatchAdvisories": patch_advisories,
        "geometryResolved": geometry_resolved,
        "extentStatus": extent_status,
        "extentNote": extent_note,
        "verdictReason": geometry_reason,
        "unavailableGates": unavailable_gates,
        "ballingScreened": balling_screened,
        "ballingAbsorptionModel": absorption_model if balling_screened else None,
        "geometryIndependentFailGates": geometry_independent_fail_gates,
        # Gates whose input was null (P6) or that have no sourced model (P7a stress gates): never pass or fail.
        "notEvaluatedGates": [g["id"] for g in gates if g["status"] == "not-evaluated"],
        # Verdict-driving gate ids ("fail" -> do-not-print, "warn" -> risky) and the advisory-only
        # gates that never change the verdict.
        "blockingGates": [g["id"] for g in gates if g["status"] == "fail"],
        "riskGates": [g["id"] for g in gates if g["status"] == "warn"],
        "advisoryGates": [g["id"] for g in gates if g["status"] == "advisory"],
        "advisories": advisories,
        "advisoryCount": n_adv,
    }


def _scan_strategy_assumptions(scan_strategy, stripe_width_mm, rotation_deg, dwell_ms):
    strat = (scan_strategy or "stripe").strip().lower().replace("_", "-")
    return [
        (
            f"Scan strategy screening default: {strat}; stripe width {stripe_width_mm} mm; "
            f"inter-layer rotation {rotation_deg}°; hatch dwell {dwell_ms} ms."
        ),
        "Strategy DOIs: 10.1115/1.4031649 (Cheng et al. residual stress / scan strategy); "
        "10.1016/j.jmapro.2020.01.039 (stripe / hatch strategy process effects); "
        "10.1016/j.jmrt.2022.04.055 (scan strategy on microstructure / defects); "
        "10.1016/j.matdes.2018.107552 (scan strategy design of LPBF parts).",
    ]


def solve_lpbf_build_job(data):
    """Build Job solve. An optional ``machineCalibration`` (a machine calibration id) adds a ``machineCalibrated`` block
    at the top level of the result, outside every golden-compared key. The block is reported next to the screening
    value; the verdict, the cache key and every other key are exactly those of the request without it."""
    machine_id = None
    if isinstance(data, dict) and "machineCalibration" in data:
        data = dict(data)
        machine_id = data.pop("machineCalibration")
    result = _solve_lpbf_build_job_core(data)
    if machine_id is None or not isinstance(result, dict) or result.get("success") is not True:
        return result
    return {**result, "machineCalibrated": _machine_calibrated_block(machine_id, data, result)}


def _machine_calibrated_block(machine_id, data, result):
    from lpbf_machine_calibrated_meltpool import build_job_block
    try:
        req = LpbfBuildJobRequest.model_validate(data).to_solver_dict()
        material = ALLOY_MATERIALS[result["alloyId"]]["thermal"]
        screening = ((result.get("thermal") or {}).get("meltPoolGeometry") or {}).get("depth_um")
        inputs = {
            "laserPower_W": req["laserPower_W"], "scanSpeed_mm_s": req["scanSpeed_mm_s"],
            "beamDiameter_um": req["beamDiameter_um"], "preheatTemp_C": req["preheatTemp_C"],
            "layerThickness_um": req["layerThickness_um"], "hatchSpacing_um": req["hatchSpacing_um"],
            "laserWavelength": req["laserWavelength"],
        }
    except Exception as exc:  # never fail the Build Job over the optional block
        return {"available": False, "usedForBuildJobVerdict": False, "experimentalValidation": False,
                "evidenceKind": "screening-only", "reasonText": [f"machine calibration not applied: {exc}"]}
    return build_job_block(machine_id, material, inputs, screening_depth_um=screening)


def _solve_lpbf_build_job_core(data):
    t0 = time.time()
    try:
        req = LpbfBuildJobRequest.model_validate(data if isinstance(data, dict) else {})
        data = req.to_solver_dict()
    except Exception as e:
        return {"success": False, "error": f"Invalid LPBF build-job payload: {e}"}

    # Normalize paste → defect list before cache key.
    if not data.get("defectSqrtAreas_um") and data.get("defectSqrtAreasPaste"):
        try:
            parsed = parse_defect_sqrt_areas_text(data.get("defectSqrtAreasPaste"))
        except ValueError as e:  # input_validation.ValidationError (inf / nan token)
            return {"success": False, "error": f"Invalid LPBF build-job payload: {e}"}
        if parsed:
            data["defectSqrtAreas_um"] = parsed

    requested_alloy = data.get("alloyId")
    if requested_alloy is None or not str(requested_alloy).strip():
        alloy_id = "in718"
    else:
        alloy_id = resolve_alloy_id(requested_alloy)
        if alloy_id is None:
            from lpbf_request_errors import refusal, SUPPORTED_ALLOYS_TEXT
            return refusal("UNSUPPORTED_BUILD_JOB_ALLOY", "alloyId",
                           f"This material is not supported by Build Job. Select {SUPPORTED_ALLOYS_TEXT}.")
    mats = ALLOY_MATERIALS[alloy_id]
    for field, canonical_name in (
        ("thermalMaterial", mats["thermal"]),
        ("slicerMaterial", mats["slicer"]),
    ):
        override = data.get(field)
        if override is None or not str(override).strip():
            continue
        override_alloy = resolve_alloy_id(override)
        if override_alloy != alloy_id:
            return {
                "success": False,
                "error": (
                    f"{field} {override!r} does not match requested LPBF alloy "
                    f"{alloy_id!r}; expected an alias of {canonical_name!r}."
                ),
            }

    # Aliases are accepted only as identity assertions; always pass the mapped
    # canonical name to the underlying solver so the requested alloy controls it.
    thermal_mat = mats["thermal"]
    slicer_mat = mats["slicer"]
    try:
        material_snapshot, material_property_sha256 = build_material_property_snapshot(
            alloy_id, thermal_mat, slicer_mat
        )
        material_authority_snapshot, material_authority_revision_sha256 = canonical_material_source(alloy_id)
        build_job_identity = build_build_job_identity(
            alloy_id,
            BUILD_JOB_MODEL_ID,
            BUILD_JOB_SOLVER_REVISION,
            material_property_sha256,
            material_snapshot["schemaVersion"],
        )
        ambench_snapshot, ambench_property_sha256 = (
            build_ambench_material_property_snapshot(IN625_VALIDATION_PROPS)
            if data.get("includeAmbench", False) else (None, None)
        )
    except (KeyError, TypeError, ValueError) as e:
        return {"success": False, "error": f"Invalid LPBF material properties: {e}"}

    bypass_cache = bool(data.get("bypassCache", False))
    cache_data = dict(data)
    cache_data["alloyId"] = alloy_id
    cache_data["thermalMaterial"] = thermal_mat
    cache_data["slicerMaterial"] = slicer_mat
    cache_data["materialPropertySha256"] = material_property_sha256
    cache_data["materialAuthorityRevisionSha256"] = material_authority_revision_sha256
    cache_data["buildJobIdentity"] = build_job_identity
    cache_data["amBenchMaterialPropertySha256"] = ambench_property_sha256
    try:
        cache_key = build_cache_key(cache_data)
    except (TypeError, ValueError) as e:
        return {"success": False, "error": f"Invalid LPBF build-job cache input: {e}"}
    if not bypass_cache:
        cached = cache_get(cache_key)
        if (
            cached is not None
            and cached.get("success") is True
            and cached.get("solverRevision") == BUILD_JOB_SOLVER_REVISION
            and cached.get("buildJobIdentity") == build_job_identity
            and cached.get("alloyId") == alloy_id
            and cached.get("materialPropertySha256") == material_property_sha256
            and cached.get("materialAuthorityRevisionSha256") == material_authority_revision_sha256
            and cached.get("materialPropertySnapshot") == material_snapshot
            and cached.get("amBenchMaterialPropertySha256") == ambench_property_sha256
            and cached.get("amBenchMaterialPropertySnapshot") == ambench_snapshot
        ):
            cached["computeTimeMs"] = round((time.time() - t0) * 1000.0, 1)
            if cached.get("thermal"):
                cached["thermal"]["computeTimeMs"] = cached["computeTimeMs"]
            return cached

    power = float(data.get("laserPower_W", 285.0))
    speed = float(data.get("scanSpeed_mm_s", data.get("scanSpeed_mms", 960.0)))
    beam = float(data.get("beamDiameter_um", 80.0))
    preheat = float(data.get("preheatTemp_C", 80.0))
    layer = float(data.get("layerThickness_um", 40.0))
    hatch = float(data.get("hatchSpacing_um", 110.0))
    wavelength = data.get("laserWavelength", "IR_1064nm")
    process_seed = int(data.get("processSeed", data.get("seed", DEFAULT_PROCESS_SEED)))

    incline_deg = float(data.get("inclineAngle_deg", data.get("surfaceIncline_deg", 0.0) or 0.0))
    downskin_deg = data.get("downskinOverhang_deg")
    if downskin_deg is None and incline_deg > 0:
        # Treat surface incline from horizontal as overhang from vertical when only one angle given.
        downskin_deg = max(0.0, 90.0 - incline_deg) if incline_deg <= 90 else incline_deg

    scan_strategy = data.get("scanStrategy", "stripe")
    stripe_width_mm = float(data.get("stripeWidth_mm", 5.0))
    rotation_deg = float(data.get("scanRotation_deg", 67.0))
    dwell_ms = float(data.get("hatchDwell_ms", 0.0))

    from lpbf_solidification_estimates import capture_front_parent
    with capture_front_parent() as front_slot:
        thermal = calculate_meltpool_physics(
            thermal_mat,
            power,
            speed,
            beam,
            preheat,
            layer,
            hatch,
            wavelength,
            incline_angle_deg=incline_deg,
            process_seed=process_seed,
            prop_overrides=material_snapshot["thermal"],
        )
    front_parent = front_slot[0] if len(front_slot) == 1 else None
    slicer = solve_slicer(
        {
            "preset": data.get("preset", "nozzle"),
            "material": slicer_mat,
            "_materialPropertiesSnapshot": material_snapshot["slicer"],
            "laserPower_W": power,
            "scanSpeed_mms": speed,
            "layerThickness_um": layer,
            "hatchSpacing_um": hatch,
            "recoatTimePerLayer_s": data.get("recoatTimePerLayer_s", 9.0),
            "customTriangles": data.get("customTriangles"),
            "cadAssetName": data.get("cadAssetName", ""),
            "triangleCountNative": data.get("triangleCountNative"),
            "maxTriangles": data.get("maxTriangles"),
        }
    )
    if slicer.get("error"):
        return {"success": False, "error": slicer["error"]}

    def _patch_thermal(p_w, v_mms, hatch_um, layer_um, beam_um):
        # Re-runs the served solver at a suggested point so a patch is verified, not read off the literature box.
        # P7b: the full frozen snapshot is passed (precedence rule (ii): a ledger alloy still takes its Kirchhoff
        # kernel at this job's preheat); the grid is skipped on the internal re-run.
        return calculate_meltpool_physics(
            thermal_mat,
            p_w,
            v_mms,
            beam_um,
            preheat,
            layer_um,
            hatch_um,
            wavelength,
            incline_angle_deg=incline_deg,
            process_seed=process_seed,
            prop_overrides=material_snapshot["thermal"],
            include_process_map=False,
        )

    decision = compose_verdict(
        thermal,
        alloy_id,
        extras={"downskinOverhang_deg": downskin_deg, "patchEvaluator": _patch_thermal},
    )

    # --- Faz 3: literature-default Monte Carlo UQ (lazy; default off) ---
    # UQ samples thermal+verdict only — slicer is NOT re-run inside MC.
    uq_block = None
    enable_uq = bool(data.get("enableUq", False))
    uq_n = int(data.get("uqSamples", 96))
    if enable_uq:
        base_props = material_snapshot["thermal"]
        # P7b: a ledger alloy's kernel (Kirchhoff mean at this job's preheat) is materialised into explicit kernel keys
        # so the UQ conductivity and density scales reach the conduction kernel (precedence rule (i)); None otherwise.
        uq_kernel = kernel_properties(thermal_mat, preheat + 273.15, float(base_props["liquidus_C"]) + 273.15)

        def _thermal_runner(p_w, beam_um, scale_overrides):
            concrete = apply_uq_prop_scales(base_props, scale_overrides, kernel=uq_kernel)
            return calculate_meltpool_physics(
                thermal_mat,
                p_w,
                speed,
                beam_um,
                preheat,
                layer,
                hatch,
                wavelength,
                incline_angle_deg=incline_deg,
                process_seed=process_seed,
                prop_overrides={**base_props, **concrete},
                include_process_map=False,
            )

        def _verdict_runner(th):
            return compose_verdict(th, alloy_id, extras={"downskinOverhang_deg": downskin_deg})

        uq_block = run_screening_uq(
            base_power_W=power,
            base_beam_um=beam,
            thermal_runner=_thermal_runner,
            verdict_fn=_verdict_runner,
            n_samples=uq_n,
            seed=process_seed,
        )
        decision["uq"] = {
            "P_printable": uq_block["P_printable"],
            "normalizedEnthalpy": uq_block["normalizedEnthalpy"],
            "dominantUncertainty": uq_block["dominantUncertainty"],
            "nSamples": uq_block["nSamples"],
        }

    # --- Faz 4a: NIST AM-Bench (lazy; default off) ---
    ambench = None
    if bool(data.get("includeAmbench", False)):

        def _amb_thermal(p_w, v_mms, beam_um, overrides):
            return calculate_meltpool_physics(
                "Inconel 718",
                p_w,
                v_mms,
                beam_um,
                25.0,
                40.0,
                100.0,
                "IR_1064nm",
                incline_angle_deg=0.0,
                process_seed=process_seed,
                prop_overrides=overrides,
            )

        ambench = run_ambench_validation(
            _amb_thermal, material_props=ambench_snapshot["thermal"]
        )
        ambench["alloyCoverage"] = coverage_for_alloy(alloy_id)

    # --- Faz 4b/c: Murakami + qualification template ---
    try:
        murakami = _murakami_block(data, alloy_id)
    except ValueError as e:  # input_validation.ValidationError: a non-finite or nonpositive scenario value
        return {"success": False, "error": f"Invalid LPBF build-job payload: {e}"}
    input_hash = cache_key[:16]
    qualification = build_qualification_block(
        alloy_id,
        input_hash=input_hash,
        git_sha=data.get("gitSha"),
    )

    elapsed = round((time.time() - t0) * 1000.0, 1)
    thermal["computeTimeMs"] = elapsed

    assumptions = [
        "Melt-pool field is regularized Rosenthal (not volumetric Goldak FEA).",
        "LoF screen is the Tang overlap index (h/W)²+(t/D)² on modelled geometry: above 1 risky (possible lack of "
        "fusion, not an established defect), never do-not-print (2026-10-27); VED is not the sole criterion.",
        (
            f"Regime labels use ΔH/hs cuts: vapor-depression onset {ENTHALPY_TRANSITION:g} (Cunningham 2019) and a "
            f"provisional keyhole-mode cut {ENTHALPY_KEYHOLE:g} ({ENTHALPY_KEYHOLE_IN625:g} for Inconel 625, fitted on "
            "NIST mds2-2923 tracks), a mode onset and not a porosity boundary. The verdict (Tang advisory bump "
            "2026-10-27) is risky when the Tang overlap index on modelled geometry is above 1.0 or in keyhole mode, "
            "otherwise printable (a screening result; fusion adequacy is not established); never do-not-print. The level "
            f"{POROSITY_SCREEN_HIGH_AT:g}, the Tang margin 0.80, the literature box, the balling Moderate band and the "
            "downskin angles are unsourced screening thresholds reported as advisories (the balling High band was "
            "removed in P7b). The Fabbro keyhole depth leg "
            f"opens at the same onset ({FABBRO_ENTHALPY_ONSET:g}) and reaches full weight at "
            f"{FABBRO_ENTHALPY_KEYHOLE:g} through an unsourced linear ramp (P3)."
        ),
        "Slicer uses live customTriangles when present; otherwise a demo CAD preset.",
        "No artificial peak-T / PDAS / residual-stress display ceilings; alloy M_molar drives recoil.",
        "P7a (2026-10-11): residual stress and the distortion index are unavailable (no sourced stress model; Mercelis "
        "and Kruth 2006 supports a yield cap only); the PDAS scalar is null and a sourced Ni-Nb band (Ghosh 2017 Hunt "
        "to Kurz-Fisher) is served for IN625/IN718 inside its validity range; SDAS is null for every alloy.",
        "Marangoni characteristic length uses the same thermal melt-pool width (geometrySource=thermal).",
        f"Deterministic processSeed={process_seed} for reproducible screening extras.",
        "Request validated with Pydantic; customTriangles capped at maxTriangles (default 12000).",
        "Hash cache keys alloy+P/v/h/t/d+seed+strategy+mesh+UQ/NIST/Murakami flags.",
        "Default job skips UQ and NIST AM-Bench (opt-in via enableUq / includeAmbench).",
    ]
    assumptions.extend(
        _scan_strategy_assumptions(scan_strategy, stripe_width_mm, rotation_deg, dwell_ms)
    )
    pp_served = thermal.get("processParameters", {})
    if pp_served.get("effectiveConductivity_W_mK") is not None:
        convention = pp_served.get("propertyConvention")
        if convention == "kernel-ledger-kirchhoff":
            convention_text = ("the Kirchhoff integral mean of the sourced solid k(T) and cp(T) from the job preheat to "
                               "the liquidus (kernel ledger, evaluated per call)")
        elif convention == "melting-point":
            convention_text = "melting-point k and cp"
        else:
            convention_text = "the equal-weight solid/liquid k and cp blend (unsourced; no melting-point source for this alloy)"
        assumptions.append(
            f"P7b (2026-10-14, sourcing correction, not validation): the conduction field uses {convention_text} with "
            f"the kernel density {pp_served.get('kernelDensity_kg_m3')} kg/m3; King ΔH/hs and the Fabbro leg stay on "
            "the room temperature solid thermophysics (propertyConventionBasis, solidConductivityBasis)."
        )
    assumptions.append(
        "P7b (2026-10-14): the field absorptivity is the measured conduction-mode authority where one exists "
        f"(absorptivityBasis); the ΔH/hs regime index reads the separate index convention constant "
        f"{pp_served.get('indexAbsorptivity')} (absorptivityIndexBasis), so regime labels, the Fabbro onset weight and "
        "the porosity advisory class are classification neutral; the process-map grid is the served Rosenthal field "
        "extent per cell (gridKernel)."
    )
    if pp_served.get("absorptivityBasis") == ABSORPTIVITY_BASIS_UNSOURCED:
        assumptions.append(
            f"Absorptivity: {ABSORPTIVITY_BASIS_UNSOURCED} (no measured conduction-mode value in the library for this "
            "alloy or wavelength)."
        )
    if abs(incline_deg) > 1e-6:
        assumptions.append(
            f"Surface incline θ={incline_deg:.1f}° is echoed only: since P6 (2026-10-11) R = v·n_x on the rear "
            "liquidus of the conduction field with no incline multiplier (an inclined surface needs the velocity "
            "vector and the normal in one frame)."
        )
    assumptions.append(
        "P6 containment (2026-10-11): peak temperature (loss-free Eagar-Tsai surface maximum, served only below a "
        "sourced vapour temperature), recoil pressure (not served), Marangoni number, denudation width and the "
        "interface G/R/cooling rate/PDAS/SDAS are null with a reason where unsupported; none of them is a verdict "
        "input, and a null gate input is reported as not evaluated, never as pass or fail."
    )
    if uq_block:
        assumptions.append(
            f"UQ: literature-default MC n={uq_block['nSamples']} "
            f"(P±{uq_block['bands']['power_rel']*100:.0f}%, A±{uq_block['bands']['absorptivity_rel']*100:.0f}%); "
            "Spearman sensitivity proxy; slicer not re-run in MC. Not machine-calibrated."
        )
    if ambench:
        assumptions.append(
            "NIST AMB2018-02 IN625 CBM Table 4 attached for screening MAPE "
            f"(doi:{ambench['source']['doi']}); four-alloy direct coverage is limited."
        )
    assumptions.append(
        "Murakami/qualification blocks are SCREENING ONLY; defect √area, hardness and location are never defaulted."
    )

    microstructure = project_build_job_microstructure(thermal)
    result = {
        "success": True,
        "engine": "lpbf_build_job",
        "modelId": BUILD_JOB_MODEL_ID,
        "solverRevision": BUILD_JOB_SOLVER_REVISION,
        "buildJobIdentity": build_job_identity,
        "assumptions": assumptions,
        "alloyId": alloy_id,
        "materialPropertySchemaVersion": material_snapshot["schemaVersion"],
        "materialPropertyRevision": MATERIAL_PROPERTY_REVISION,
        "materialPropertySha256": material_property_sha256,
        "materialPropertySnapshot": material_snapshot,
        "materialAuthority": material_authority_snapshot["authority"],
        "materialAuthorityRevisionSha256": material_authority_revision_sha256,
        "amBenchMaterialPropertySha256": ambench_property_sha256,
        "amBenchMaterialPropertySnapshot": ambench_snapshot,
        "processSeed": process_seed,
        "scanStrategy": {
            "id": scan_strategy,
            "stripeWidth_mm": stripe_width_mm,
            "rotation_deg": rotation_deg,
            "hatchDwell_ms": dwell_ms,
        },
        "computeTimeMs": elapsed,
        "thermal": thermal,
        "slicer": slicer,
        "kinematics": calculate_scanner_kinematics(speed, max(50.0, float(stripe_width_mm * 1000.0))),
        "microstructure": microstructure,
        # Nb segregation / terminal gamma-Laves screening (composition-only; G/R copied from microstructure).
        "segregation": build_job_segregation(alloy_id, microstructure),
        "kinetics": build_job_kinetics(
            alloy_id, thermal, front_parent,
            {"power_W": power, "speed_mm_s": speed, "beamDiameter_um": beam, "preheat_C": preheat,
             "layerThickness_um": layer, "hatch_um": hatch},
            {"coolingInterval_C": data.get("kineticsCoolingInterval_C"), "isothermalHold": data.get("isothermalHold")},
            material_snapshot["thermal"]),
        "porosity": aggregate_part_porosity(
            uq_block.pop("defectSamples", []) if uq_block else [thermal.get("geometricDefectScreen", {})]
        ),
        "verdict": decision,
        "uq": uq_block,
        "ambench": ambench,
        "murakami": murakami,
        "qualification": qualification,
        # Group 2 scenarios: outside the verdict, the recoater gate and the legacy stress/distortion keys.
        "mechanicsScenarios": _mechanics_block(data, thermal),
    }
    return cache_put(cache_key, result)


def main():
    raw = sys.stdin.read().strip()
    if not raw:
        print(json.dumps({"error": "Empty payload provided to LPBF build-job solver."}))
        sys.exit(1)
    try:
        data = json.loads(raw)
    except Exception as e:
        print(json.dumps({"error": f"Invalid JSON input: {str(e)}"}))
        sys.exit(1)
    result = solve_lpbf_build_job(data)
    if not result.get("success"):
        print(json.dumps(result))
        sys.exit(1)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
