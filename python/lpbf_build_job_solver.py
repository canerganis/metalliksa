#!/usr/bin/env python3
"""
Single LPBF Build Job engine: Rosenthal melt-pool screening + STL slicer + print verdict.

The industrial UI must display this verdict. TypeScript must not re-decide printability.
Melt-pool geometry for the verdict is regularized Rosenthal. Eagar–Tsai (`eagar-tsai-v2`) is opt-in on the thermal / Melt Pool 3D lab only — it does not change this verdict.
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
from lpbf_thermal_solver import ENTHALPY_TRANSITION, calculate_meltpool_physics
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
from kinetics_ttt_cct_solver import STEEL_ONLY_REASON, resolve_kinetics_alloy, solve_phase_transformation_kinetics

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
BUILD_JOB_KINETICS_COOLING_RATE_SOURCE = "thermal.solidificationKinetics.coolingRate_K_s"
# solidification_front.py clamps the front's median cooling rate to max(1.0, median) K/s when the
# front is degenerate (median 0). A reported rate at or below this floor is that clamp, not a
# computed build rate, wherever it was produced; the kinetics block is then unavailable.
SOLIDIFICATION_FRONT_COOLING_RATE_FLOOR_K_S = 1.0
DEGENERATE_FRONT_REASON = (
    "cooling rate is the 1 K/s floor of a degenerate solidification front, not a computed build rate"
)


def _finite_number(value):
    """float(value) for a finite int/float (bool excluded), else None."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    out = float(value)
    return out if math.isfinite(out) else None


def format_cooling_rate(rate):
    """Exact text for a rate in a reason: 1089047.0 -> "1089047", 2000.0000001 -> "2000.0000001"."""
    return str(int(rate)) if float(rate).is_integer() else repr(float(rate))


def _reported_cooling_rate(thermal):
    """The reported cooling rate (K/s, numerically equal to °C/s) if finite, else None."""
    return _finite_number((thermal.get("solidificationKinetics") or {}).get("coolingRate_K_s"))


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


def build_job_kinetics(alloy_id, thermal):
    """Kinetics block for a build job; unavailable (with reason) instead of a substitute alloy.

    ``status`` ("available" / "unavailable") is the field to trust. ``success: False`` on the
    unavailable block only keeps the solver-envelope shape; it does not mean the build job failed.
    The kinetics model is steel-only (kinetics_ttt_cct_solver, ``kineticsModel``): for an alloy whose
    solver result is not available (all four build-job alloys: none is a steel) the block is
    unavailable with the solver's reason, never a steel-template result.
    """
    reported = _reported_cooling_rate(thermal)
    kinetics_alloy = BUILD_JOB_KINETICS_ALLOY.get(alloy_id)
    degenerate = reported is not None and reported <= SOLIDIFICATION_FRONT_COOLING_RATE_FLOOR_K_S
    if kinetics_alloy is None or reported is None or degenerate:
        alloy_name = ALLOY_MATERIALS[alloy_id]["thermal"] if alloy_id in ALLOY_MATERIALS else str(alloy_id)
        if kinetics_alloy is None:
            reason = f"no kinetics model for {alloy_name}"
        elif reported is None:
            reason = "the build thermal result reports no finite cooling rate"
        else:
            reason = DEGENERATE_FRONT_REASON
        return _unavailable_kinetics_block(alloy_id, reason, reported, degenerate)
    registry_id = resolve_kinetics_alloy(kinetics_alloy)[0]
    block = solve_phase_transformation_kinetics(alloy_name=kinetics_alloy, cooling_rate_c_s=reported)
    model = block.get("kineticsModel") or {}
    if model.get("status") != "available":
        # e.g. "kinetics model is steel-only: Inconel 718 is not a steel"
        why = model.get("reason") or "the kinetics model has no result for this alloy"
        suffix = f": {kinetics_alloy} is not a steel" if why == STEEL_ONLY_REASON else ""
        return _unavailable_kinetics_block(alloy_id, why + suffix, reported, False)
    block["status"] = "available"
    block["alloyId"] = alloy_id
    block["buildCoolingRate_C_s"] = reported
    block["reportedCoolingRate_K_s"] = reported
    block["coolingRateSource"] = BUILD_JOB_KINETICS_COOLING_RATE_SOURCE
    block["buildCoolingRateCctRow"] = build_cooling_rate_cct_row(block.get("cctContinuousCoolingMap"), reported)
    block["buildRateMartensite"] = build_rate_martensite(
        registry_id, kinetics_alloy, block.get("calphadVsKineticsGap"), block["buildCoolingRateCctRow"])
    return block


def _gate(gid, status, measured, required, unit, note):
    return {
        "id": gid,
        "status": status,
        "measured": measured,
        "required": required,
        "unit": unit,
        "note": note,
    }


def _suggested_patch(thermal, alloy_id, dominant_gate, verdict):
    if verdict == "printable" or dominant_gate in (None, "none"):
        return None
    box = LITERATURE_PV_WINDOWS[alloy_id]
    mid_p = int(round((box["powerMin_W"] + box["powerMax_W"]) / 2.0))
    mid_v = int(round((box["speedMin_mm_s"] + box["speedMax_mm_s"]) / 2.0))
    pp = thermal["processParameters"]
    cur_h = float(pp["hatchSpacing_um"])
    cur_t = float(pp["layerThickness_um"])
    cur_d = float(pp["beamDiameter_um"])
    ht = _LOF_HT.get(alloy_id, {"hatch_um": 100, "layer_um": 30, "beamDiameter_um": cur_d})
    if dominant_gate == "keyhole":
        return {
            "laserPower_W": int(box["powerMin_W"]),
            "scanSpeed_mms": int(box["speedMax_mm_s"]),
            "hatch_um": int(round(cur_h)),
            "layer_um": int(round(cur_t)),
            "beamDiameter_um": int(round(cur_d)),
        }
    if dominant_gate in ("lof_tang", "lof_wh", "lof_dt", "downskin"):
        return {
            "laserPower_W": mid_p,
            "scanSpeed_mms": mid_v,
            "hatch_um": ht["hatch_um"],
            "layer_um": ht["layer_um"],
            "beamDiameter_um": ht["beamDiameter_um"],
        }
    return {
        "laserPower_W": mid_p,
        "scanSpeed_mms": mid_v,
        "hatch_um": int(round(cur_h)),
        "layer_um": int(round(cur_t)),
        "beamDiameter_um": int(round(cur_d)),
    }


# Gates whose result is a function of the melt-pool W/D/L extent. When the thermal solver
# reports ``extentStatus != "computed"`` (heuristic fallback, width floor, search-box limit)
# these are unavailable: a verdict must not be built from screening-heuristic numbers.
GEOMETRY_DEPENDENT_GATES = ("lof_tang", "lof_wh", "lof_dt", "balling")

# Gates reported as advisories only: they never change the verdict, the dominant gate or an
# optimizer score. The frozen solver's distortion index (and the recoater flag derived from it,
# High when index > 2.0) is a function of alloy properties, preheat and layer thickness only,
# not of P, v or hatch, so it cannot discriminate between process parameter sets.
ADVISORY_GATES = ("recoater", "distortion")
PARAMETER_INDEPENDENT_ADVISORY_NOTE = (
    "alloy/layer advisory independent of P, v and hatch: the frozen distortion index depends only on "
    "alloy properties, preheat and layer thickness (not on P, v or hatch); it does not change the verdict"
)
# P1 (2026-10-11): at dH/hs >= ENTHALPY_TRANSITION the served depth is the Fabbro leg with a flat absorptivity, so
# transition and keyhole depth is biased low (keyhole absorptance A(R) not modelled).
KEYHOLE_DEPTH_BIAS_LOF_NOTE = (
    f"At dH/hs >= {ENTHALPY_TRANSITION:g} the transition and keyhole depth is biased low because the keyhole "
    "absorptance A(R) is not modelled, so a lack-of-fusion fail in this regime may be a model artefact."
)
BALLING_SCREEN_NOTE = (
    "Eagar-Tsai aspect-ratio screen calibrated on Hofmann 2026 316L single tracks (Zenodo 10.5281/zenodo.16979848; "
    "High threshold 5.5 chosen in-sample, model L/W uncertainty about +-10 %; low recall and spot-size dependent: "
    "69/216 balled tracks flagged overall, 3/38 at a 140 um spot, so a track below 5.5 is not balling-cleared); "
    "not a demonstrated balling prediction for other alloys; reported as risky, never do-not-print"
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
    W = float(thermal["meltPoolGeometry"]["width_um"])
    D = float(thermal["meltPoolGeometry"]["depth_um"])
    h = float(thermal["processParameters"]["hatchSpacing_um"])
    t = float(thermal["processParameters"]["layerThickness_um"])
    width_over_hatch = W / max(1e-6, h)
    depth_over_layer = D / max(1e-6, t)
    tang = float(
        thermal["defectDiagnostics"].get(
            "tangIndex_hW_tD",
            thermal["defectDiagnostics"].get("lackOfFusionOverlapIndex", 0.0),
        )
    )

    def_ = thermal["defectDiagnostics"]
    lof_fail = def_["lackOfFusionStatus"] == "Fail"
    lof_warn = def_["lackOfFusionStatus"] == "Warning"
    keyhole_high = str(def_["keyholePorosityRisk"]).startswith("High")
    keyhole_possible = str(def_["keyholePorosityRisk"]).startswith("Possible")
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
    # The frozen solver no longer bands recoaterCrashRisk (alloy/layer/preheat-only index, not evaluated
    # from scan parameters); the advisory keeps its documented threshold on the unchanged index.
    recoater_high = float(def_["distortionIndex"]) > 2.0
    distortion_high = float(def_["distortionIndex"]) >= 0.65
    dh = float(thermal["processParameters"]["normalizedEnthalpy"])
    win = evaluate_literature_pv(
        alloy_id,
        float(thermal["processParameters"]["laserPower_W"]),
        float(thermal["processParameters"]["scanSpeed_mm_s"]),
    )

    downskin_angle = extras.get("downskinOverhang_deg")
    downskin_fail = False
    downskin_warn = False
    if downskin_angle is not None:
        # Overhang from vertical: >45° downskin needs support / parameter change in screening.
        if float(downskin_angle) > 55.0:
            downskin_fail = True
        elif float(downskin_angle) > 45.0:
            downskin_warn = True

    if not geometry_resolved:
        # Geometry-derived flags are heuristic here: neutralise them so no reason, verdict or
        # dominant gate is built from screening-substitute W/D/L numbers.
        lof_fail = lof_warn = balling_high = balling_moderate = False

    reasons = []
    if not geometry_resolved:
        reasons.append(
            f"Lack-of-fusion (Tang h/W, t/D, W/h, D/t) and balling (L/W) gates unavailable: "
            f"{geometry_reason.rstrip('.')}. "
            "No print / do-not-print verdict is issued from heuristic geometry."
        )
    if lof_fail:
        reasons.append(
            f"Lack of fusion (Tang): (h/W)²+(t/D)² = {tang:.3f} (need ≤1.0); "
            f"W/h = {width_over_hatch:.2f}, D/t = {depth_over_layer:.2f}."
        )
        if dh >= ENTHALPY_TRANSITION:
            reasons[-1] += " " + KEYHOLE_DEPTH_BIAS_LOF_NOTE
    elif lof_warn:
        reasons.append(
            f"Tang overlap marginal: (h/W)²+(t/D)² = {tang:.3f} (pass ≤0.80)."
        )
    if keyhole_high:
        reasons.append(f"Keyhole porosity screen High: ΔH/hₛ = {dh} (legacy screening level ≥ 30; porosity unresolved, not a porosity boundary).")
    if balling_high:
        reasons.append(
            f"Balling screen High: Eagar–Tsai L/W = {balling_lw_text} (> {balling.get('highThreshold', 5.5)}; "
            f"{balling.get('hofmannBalledFractionInBand') or 'n/a'} Hofmann 316L tracks above it balled) — "
            f"{BALLING_SCREEN_NOTE}."
        )
    elif geometry_resolved and balling_unavailable:
        reasons.append(
            f"Balling screen unavailable: Eagar–Tsai melt-pool extent not resolved "
            f"({balling.get('extentStatus', 'not reported')}); no balling band is assigned and the verdict does "
            "not include a balling screen."
        )
    advisories = []
    if keyhole_possible:
        advisories.append(
            f"Advisory: keyhole porosity possible (legacy screening level, ΔH/hₛ {dh} in 15–30); Zhao 2020 "
            "Ti-6Al-4V pores at 16–28 for v ≤ 445 mm/s; porosity unresolved, this index does not resolve it."
        )
    if balling_absorption_note and geometry_resolved:
        advisories.append("Advisory: " + balling_absorption_note)
    if balling_moderate:
        advisories.append(
            f"Advisory: balling screen Moderate — Eagar–Tsai L/W = {balling_lw_text} > 3.85, the "
            f"{BALLING_LITERATURE_NOTE}; {balling.get('hofmannBalledFractionInBand') or 'n/a'} Hofmann 316L tracks "
            "in this band balled (316L only, L/W uncertainty about +-10 %). It does not change the verdict."
        )
    if recoater_high:
        advisories.append(
            f"Advisory: recoater crash / part curl flag High (distortion index {def_['distortionIndex']} > 2.0) — "
            f"{PARAMETER_INDEPENDENT_ADVISORY_NOTE}."
        )
    if distortion_high:
        advisories.append(
            f"Advisory: inherent-strain distortion index {def_['distortionIndex']} (≥0.65) — "
            f"{PARAMETER_INDEPENDENT_ADVISORY_NOTE}."
        )
    if downskin_fail:
        reasons.append(
            f"Downskin overhang {float(downskin_angle):.1f}° from vertical exceeds 55° screening gate."
        )
    elif downskin_warn:
        reasons.append(
            f"Downskin overhang {float(downskin_angle):.1f}° is marginal (45–55°); expect support or stripe reorient."
        )
    if not win["inside"]:
        box = win["box"]
        reasons.append(
            f"P–v is outside the {alloy_id} literature box "
            f"({box['powerMin_W']}–{box['powerMax_W']} W, {box['speedMin_mm_s']}–{box['speedMax_mm_s']} mm/s)."
        )

    # recoater_high / distortion_high are advisories (ADVISORY_GATES) and are deliberately absent here.
    verdict = "printable"
    if lof_fail or downskin_fail or (keyhole_high and dh > 35):
        verdict = "do-not-print"
    elif lof_warn or keyhole_high or balling_high or downskin_warn or (not win["inside"]):
        verdict = "risky"
    if not geometry_resolved:
        verdict = "inconclusive"

    if not reasons:
        reasons.append(
            "Conduction-mode melt pool with Tang hatch/layer overlap above LoF gates. "
            "VED is not used as the sole criterion."
        )

    headline = {
        "printable": "Printable — stay in the conduction window",
        "risky": "Risky — qualify with coupon builds before flight hardware",
        "do-not-print": "Do not print — change P, v, h, or t before a build",
        "inconclusive": f"Inconclusive — melt-pool geometry not resolved ({extent_status}); see reasons",
    }[verdict]

    balling_screened = geometry_resolved and not balling_unavailable
    if geometry_resolved and balling_unavailable:
        # A verdict without the balling screen is not balling-cleared: say so in the headline.
        headline += " (balling not screened: Eagar–Tsai extent not computed)"

    lw = round(width_over_hatch, 3)
    dt = round(depth_over_layer, 3)
    tang_r = round(tang, 3)
    tang_status = "fail" if lof_fail else ("warn" if lof_warn else "pass")
    kh_status = ("fail" if (keyhole_high and dh > 35) else "warn" if keyhole_high
                 else "advisory" if keyhole_possible else "pass")
    ball_status = ("warn" if balling_high else "advisory" if balling_moderate
                   else "unavailable" if balling_unavailable else "pass")
    lit_status = "pass" if win["inside"] else "warn"
    rec_status = "advisory" if recoater_high else "pass"
    dist_status = "advisory" if distortion_high else "pass"
    ds_status = "fail" if downskin_fail else ("warn" if downskin_warn else "pass")
    ball_measured = None if balling_lw is None else round(float(balling_lw), 2)

    gates = [
        _gate(
            "lof_tang",
            tang_status,
            tang_r,
            1.0,
            "1",
            "Tang LoF index (h/W)²+(t/D)² — pass ≤0.80, fail >1.0. Primary hatch/layer fusion gate.",
        ),
        _gate(
            "lof_wh",
            tang_status,
            lw,
            1.05,
            "1",
            "Diagnostic melt-pool width / hatch (W/h). Informational; Tang index is the gate.",
        ),
        _gate(
            "lof_dt",
            tang_status,
            dt,
            1.15,
            "1",
            "Diagnostic melt-pool depth / layer (D/t). Informational; Tang index is the gate.",
        ),
        _gate(
            "keyhole",
            kh_status,
            dh,
            30.0,
            "1",
            "Keyhole-porosity legacy screening level on ΔH/hₛ (porosity unresolved, not a porosity boundary): High ≥ 30 → warn, "
            "High and > 35 → fail, 15–30 → advisory. The regime keyhole-mode onset (ΔH/hₛ = 20) is separate.",
        ),
        _gate(
            "balling",
            ball_status,
            ball_measured,
            5.5,
            "1",
            "Eagar–Tsai liquidus L/W (beam-size aware, whatever kernel the job uses for W/D): High (> 5.5, "
            "empirical, Hofmann 316L, in-sample) → warn (risky); Moderate (> 3.85 = π√(3/2), Yadroitsev et al. "
            "2010 Eq. 13 / Gusarov et al. 2007 mechanism) → advisory, no verdict effect; Eagar–Tsai extent not computed → "
            "unavailable. Aspect-ratio screen, not a demonstrated balling prediction.",
        ),
        _gate(
            "literature_pv",
            lit_status,
            1.0 if win["inside"] else 0.0,
            1.0,
            "inside",
            "Inside four-alloy published P–v box (screening envelope, not OEM machine limits).",
        ),
        _gate(
            "recoater",
            rec_status,
            float(def_["distortionIndex"]),
            None,
            "index",
            "Recoater-crash heuristic from residual-stress index (High when > 2.0) — not a blade FEA. "
            "Advisory only: " + PARAMETER_INDEPENDENT_ADVISORY_NOTE + ".",
        ),
        _gate(
            "distortion",
            dist_status,
            float(def_["distortionIndex"]),
            0.65,
            "index",
            "Inherent-strain distortion screening (≥0.65 advisory) — not Goldak FEA. "
            "Advisory only: " + PARAMETER_INDEPENDENT_ADVISORY_NOTE + ".",
        ),
        _gate(
            "downskin",
            ds_status,
            None if downskin_angle is None else round(float(downskin_angle), 1),
            45.0,
            "deg",
            "Overhang from vertical: >45° warn, >55° fail. Omitted angle → pass.",
        ),
    ]
    unavailable_gates = []
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

    return {
        "verdict": verdict,
        "headline": headline,
        "reasons": reasons,
        "lofGeometry": {
            "widthOverHatch": lw,
            "depthOverLayer": dt,
            "tangIndex": tang_r,
            "hOverW": round(h / max(1e-6, W), 3),
            "tOverD": round(t / max(1e-6, D), 3),
        },
        "literatureWindow": win,
        "gates": gates,
        "dominantGate": dominant,
        "suggestedPatch": _suggested_patch(thermal, alloy_id, dominant, verdict),
        "geometryResolved": geometry_resolved,
        "extentStatus": extent_status,
        "extentNote": extent_note,
        "verdictReason": geometry_reason,
        "unavailableGates": unavailable_gates,
        "ballingScreened": balling_screened,
        "ballingAbsorptionModel": absorption_model if balling_screened else None,
        "geometryIndependentFailGates": geometry_independent_fail_gates,
        # Verdict-driving gate ids ("fail" -> do-not-print, "warn" -> risky) and the advisory-only
        # gates that never change the verdict (see ADVISORY_GATES).
        "blockingGates": [g["id"] for g in gates if g["status"] == "fail"],
        "riskGates": [g["id"] for g in gates if g["status"] == "warn"],
        "advisoryGates": [g["id"] for g in gates if g["status"] == "advisory"],
        "advisories": advisories,
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
            return {
                "success": False,
                "error": (
                    f"Unsupported LPBF alloy identity: {requested_alloy!r}. "
                    "No surrogate alloy was submitted."
                ),
            }
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

    decision = compose_verdict(
        thermal,
        alloy_id,
        extras={"downskinOverhang_deg": downskin_deg},
    )

    # --- Faz 3: literature-default Monte Carlo UQ (lazy; default off) ---
    # UQ samples thermal+verdict only — slicer is NOT re-run inside MC.
    uq_block = None
    enable_uq = bool(data.get("enableUq", False))
    uq_n = int(data.get("uqSamples", 96))
    if enable_uq:
        base_props = material_snapshot["thermal"]

        def _thermal_runner(p_w, beam_um, scale_overrides):
            concrete = apply_uq_prop_scales(base_props, scale_overrides)
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
    murakami = evaluate_murakami_block(
        data.get("defectSqrtAreas_um"),
        hardness_HV=data.get("hardness_HV"),
        ct_detection_threshold_um=data.get("ctDetectionThreshold_um"),
        alloy_id=alloy_id,
        defect_paste=data.get("defectSqrtAreasPaste"),
    )
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
        "LoF gate is Tang (h/W)²+(t/D)² ≤ 1; VED is not the sole criterion.",
        "Keyhole uses King ΔH/hs ≈ 30.",
        "Slicer uses live customTriangles when present; otherwise a demo CAD preset.",
        "No artificial peak-T / PDAS / residual-stress display ceilings; alloy M_molar drives recoil.",
        "Marangoni characteristic length uses the same thermal melt-pool width (geometrySource=thermal).",
        f"Deterministic processSeed={process_seed} for reproducible screening extras.",
        "Request validated with Pydantic; customTriangles capped at maxTriangles (default 12000).",
        "Hash cache keys alloy+P/v/h/t/d+seed+strategy+mesh+UQ/NIST/Murakami flags.",
        "Default job skips UQ and NIST AM-Bench (opt-in via enableUq / includeAmbench).",
    ]
    assumptions.extend(
        _scan_strategy_assumptions(scan_strategy, stripe_width_mm, rotation_deg, dwell_ms)
    )
    if thermal.get("processParameters", {}).get("effectiveConductivity_W_mK") is not None:
        assumptions.append(
            "Effective k/Cp blend solid↔liquid for Rosenthal geometry; King ΔH/hs stays on solid thermophysics."
        )
    if abs(incline_deg) > 1e-6:
        assumptions.append(
            f"Solidification rate R = v·cos(θ) with surface incline θ={incline_deg:.1f}°."
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
        "Murakami/qualification blocks are SCREENING ONLY; defect √area not invented when absent."
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
        "kinetics": build_job_kinetics(alloy_id, thermal),
        "porosity": aggregate_part_porosity(
            uq_block.pop("defectSamples", []) if uq_block else [thermal.get("geometricDefectScreen", {})]
        ),
        "verdict": decision,
        "uq": uq_block,
        "ambench": ambench,
        "murakami": murakami,
        "qualification": qualification,
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
