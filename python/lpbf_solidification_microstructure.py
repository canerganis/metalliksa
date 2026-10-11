"""
lpbf_solidification_microstructure.py  — Phase 8
================================================
Python-side solidification microstructure helpers for LPBF.

Provides:
  compute_screening_field_microstructure(params)
    → RPC route "solidification-microstructure" when no CFD result is supplied.
      Runs lpbf_thermal_solver.calculate_meltpool_physics for the named material
      and projects thermal["solidificationKinetics"] (for heatSource=rosenthal and
      the Build Job's inputs, the same numbers the Build Job projects). Missing,
      unknown or physically impossible inputs give status "unavailable": no
      defaults, no surrogate alloy.
  compute_solidification_microstructure(params, material, cfd_result)
    → RPC route "solidification-microstructure". Uses the CFD
      solidificationMicrostructure sub-dict (meanG_K_m, meanR_m_s, ...) when
      present. Without CFD data it returns status "unavailable": G and R are
      never estimated from default constants.
  project_build_job_microstructure(thermal)
    → Build-job projection of thermal["solidificationKinetics"] (the conduction
      field G/R from solidification_front); numbers are copied, not recomputed.

P7a (2026-10-11): the legacy CFD-path correlations λ₁ = 80 G^-0.5 R^-0.25 and λ₂ = 64.5 Ṫ^-0.33
(unsourced prefactors, unreachable: no caller supplies a CFD result) are deleted; the CFD path
serves PDAS_um and SDAS_um as None with a reason. The numbers shown by the build job and by the
Microstructure Lab come from solidification_front via thermal["solidificationKinetics"]: the
PDAS scalar is null, a sourced Ni-Nb band (pdasBand_um, Ghosh 2017) is served for IN625/IN718
inside its validity range, SDAS is null.

Hunt G/R morphology criterion:
    G/R > 1×10⁸  K·s/m²  → columnar
    G/R < 1×10⁶  K·s/m²  → equiaxed
    in between             → mixed (columnar+equiaxed coexistence)
"""

import math
from typing import Any, Dict


# ---------------------------------------------------------------------------
# Hunt G/R morphology (the former Hunt-Lu / Kirkwood prefactors 80 and 64.5 were unsourced and are deleted, P7a)
# ---------------------------------------------------------------------------

G_OVER_R_COLUMNAR = 1.0e8   # K·s/m²  — above this: columnar
G_OVER_R_EQUIAXED = 1.0e6   # K·s/m²  — below this: equiaxed
CFD_SPACING_UNAVAILABLE_REASON = (
    "PDAS and SDAS are not served on the CFD path since P7a (2026-10-11): the former prefactors 80 um (K/m)^0.5 "
    "(m/s)^0.25 and 64.5 um (K/s)^0.33 had no source"
)


def hunt_morphology(G_Km: float, R_ms: float) -> str:
    """Return 'columnar', 'equiaxed', or 'mixed' based on Hunt G/R criterion."""
    R_safe = max(R_ms, 1.0e-9)
    ratio = G_Km / R_safe
    if ratio > G_OVER_R_COLUMNAR:
        return "columnar"
    elif ratio < G_OVER_R_EQUIAXED:
        return "equiaxed"
    return "mixed"


def morphology_fractions(G_Km: float, R_ms: float) -> Dict[str, float]:
    """Return columnar/equiaxed/mixed fractions as a soft transition model."""
    R_safe = max(R_ms, 1.0e-9)
    log_gr = math.log10(max(1.0, G_Km / R_safe))
    log_col = math.log10(G_OVER_R_COLUMNAR)   # 8
    log_eq  = math.log10(G_OVER_R_EQUIAXED)   # 6
    # Soft sigmoid transition across the 2-decade window
    if log_gr >= log_col:
        f_col, f_eq = 1.0, 0.0
    elif log_gr <= log_eq:
        f_col, f_eq = 0.0, 1.0
    else:
        t = (log_gr - log_eq) / (log_col - log_eq)   # 0→equiaxed, 1→columnar
        f_col = t
        f_eq  = 1.0 - t
    f_mix = 1.0 - f_col - f_eq
    return {"columnar": round(f_col, 4), "equiaxed": round(f_eq, 4), "mixed": round(max(0.0, f_mix), 4)}


# ---------------------------------------------------------------------------
# Main public API
# ---------------------------------------------------------------------------

_UNAVAILABLE_NO_CFD_REASON = (
    "no CFD solidification data (solidificationMicrostructure.meanG_K_m); "
    "G and R are not estimated from default constants"
)

_MICROSTRUCTURE_DOI = {
    "pdas": "10.1007/BF02648950",                 # Hunt & Lu 1996, Metall. Mater. Trans. A 27, 611
    "sdas": "10.1016/0025-5416(85)90319-2",       # Kirkwood 1985, Mater. Sci. Eng. 73, L1
    "morphology": "10.1016/0025-5416(84)90201-5", # Hunt 1984, Mater. Sci. Eng. 65, 75
}

_FALLBACK_REASON = (
    "thermal.solidificationKinetics used the tail-length heuristic (G = ΔT/x_rear, R = v·cosθ), "
    "not the liquidus field map; treat G/R/PDAS/SDAS as screening only"
)

# Until P6 (2026-10-11) solidification_front.evaluate_solidification clamped R to >= 1e-4 m/s and the cooling rate
# to >= 1 K/s; P6 removed the floors (null with a reason instead). The projection keeps detecting values at or
# below those bounds (archived payloads, synthetic fixtures) and never shows them as a computed result.
R_FLOOR_M_S = 1.0e-4
COOLING_FLOOR_K_S = 1.0

_DEGENERATE_FLOOR_REASON = (
    "solidification front degenerate: floor-clamped R/cooling "
    "(R <= 1e-4 m/s or cooling <= 1 K/s), not a computed value"
)

_KEYHOLE_REGIME_NOTE = "Keyhole Mode: outside the conduction regime of the G/R field"

_MICROSTRUCTURE_DISCLAIMER = (
    "G from grad(T) at mushy-zone front; R from U·n_front. "
    "PDAS/SDAS are not served on this path (unsourced prefactors deleted, P7a). "
    "Morphology is Hunt G/R criterion with soft transition band."
)


def _finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


_BUILD_JOB_PROJECTION_NOTE = (
    "Build-job microstructure is a projection of the thermal block's "
    "conduction-field G/R; no second estimate."
)

_SCREENING_PROJECTION_NOTE = (
    "Screening-field projection of python/lpbf_thermal_solver solidificationKinetics for the selected "
    "heat source and the inputs sent here; no second estimate. It equals the Build Job projection only "
    "for heatSource=rosenthal with the Build Job's inputs."
)


def project_build_job_microstructure(thermal: Dict[str, Any], *, note: str = _BUILD_JOB_PROJECTION_NOTE) -> Dict[str, Any]:
    """
    Project thermal["solidificationKinetics"] into the build-job microstructure block.

    The numbers are copied from the thermal block (conduction-field G/R from
    solidification_front.evaluate_solidification); no second Hunt-Lu / Kirkwood
    estimate is made here. When the thermal block carries no finite G/R/cooling
    rate the block is reported as unavailable instead of falling back to constants.

    status:
      "available"          usedFieldMap is True (liquidus field-map G/R).
      "screening-fallback" usedFieldMap is not True or gradientSource is
                           "tail-length-fallback" (G = ΔT/x_rear, R = v·cosθ
                           heuristic); the numbers are still copied, never
                           recomputed, and carry the reason.
      "degenerate-floor"   usedFieldMap is True but R <= 1e-4 m/s or cooling
                           <= 1 K/s: the frozen front mapper clamped R and the
                           cooling rate to their floors (no rear liquidus sample
                           with a positive scan-direction normal). The numbers
                           (and the PDAS/SDAS/morphology derived from the floors)
                           are copied but are not a computed result; consumers
                           must render this like "unavailable" and show the reason.
                           Detection uses R_mm_s/1e3, which thermal rounds to 0.1 mm/s,
                           so R up to about 1.5e-4 m/s is indistinguishable from the floor.
    R is taken from solidificationRate_R_mm_s / 1e3 when present (the thermal
    block rounds R_m_s to 3 decimals, about 1 % at 0.03 m/s); this is a unit
    conversion of the same thermal value, not a second estimate.
    """
    kin = thermal.get("solidificationKinetics") if isinstance(thermal, dict) else None
    if (
        isinstance(kin, dict)
        and _finite_number(kin.get("thermalGradient_G_K_m"))
        and _finite_number(kin.get("solidificationRate_R_m_s"))
        and _finite_number(kin.get("coolingRate_K_s"))
    ):
        base_disclaimer = kin.get("disclaimer") or ""
        gradient_source = kin.get("gradientSource")
        used_field_map = kin.get("usedFieldMap")
        is_fallback = used_field_map is not True or gradient_source == "tail-length-fallback"
        r_mm_s = kin.get("solidificationRate_R_mm_s")
        r_m_s = r_mm_s / 1.0e3 if _finite_number(r_mm_s) else kin["solidificationRate_R_m_s"]
        is_degenerate = (
            not is_fallback
            and (r_m_s <= R_FLOOR_M_S * (1.0 + 1.0e-9) or kin["coolingRate_K_s"] <= COOLING_FLOOR_K_S)
        )
        geometry = thermal.get("meltPoolGeometry") if isinstance(thermal.get("meltPoolGeometry"), dict) else {}
        params = thermal.get("processParameters") if isinstance(thermal.get("processParameters"), dict) else {}
        regime = geometry.get("regime")
        regime_note = _KEYHOLE_REGIME_NOTE if isinstance(regime, str) and regime.startswith("Keyhole") else None
        block = {
            "status": "screening-fallback" if is_fallback else ("degenerate-floor" if is_degenerate else "available"),
            "source": "thermal.solidificationKinetics",
            "modelId": kin.get("modelId"),
            "gradientSource": gradient_source,
            "usedFieldMap": used_field_map,
            "regime": regime,
            "normalizedEnthalpy": params.get("normalizedEnthalpy"),
            "regimeNote": regime_note,
            "G_K_m": kin["thermalGradient_G_K_m"],
            "R_m_s": r_m_s,
            "coolingRate_K_s": kin["coolingRate_K_s"],
            # P7a: the PDAS scalar is null; the sourced Ni-Nb band (IN625/IN718, Ghosh 2017) or the reason is carried.
            "PDAS_um": kin.get("primaryDendriteArmSpacing_PDAS_um"),
            "pdasBand_um": kin.get("pdasBand_um"),
            "pdasBasis": kin.get("pdasBasis"),
            "pdasOutOfRange": kin.get("pdasOutOfRange"),
            "pdasUnavailableReason": kin.get("pdasUnavailableReason"),
            "SDAS_um": kin.get("secondaryDendriteArmSpacing_SDAS_um"),
            "sdasUnavailableReason": kin.get("sdasUnavailableReason"),
            "morphology": kin.get("microstructureMorphology"),
            "g_over_r_ratio": kin.get("g_over_r_ratio"),
            "doi": kin.get("doi"),
            "disclaimer": (base_disclaimer + " " + note).strip(),
        }
        if is_fallback:
            block["reason"] = _FALLBACK_REASON
            block["disclaimer"] = (
                block["disclaimer"]
                + " This operating point used the tail-length heuristic, not the liquidus field map "
                "(see reason): the G,R wording above does not apply."
            ).strip()
        if is_degenerate:
            block["reason"] = _DEGENERATE_FLOOR_REASON
            block["disclaimer"] = (
                block["disclaimer"]
                + " R and the cooling rate sit on the solver clamp floors (see reason): the values above, "
                "and the PDAS/SDAS/morphology derived from them, are not a computed result."
            ).strip()
        return block
    # P6 containment (2026-10-11): the thermal block serves null G/R with its own reason (served depth from the
    # Fabbro keyhole leg, or fewer than 3 interface samples); carry that reason instead of a generic one.
    thermal_reason = kin.get("unavailableReason") if isinstance(kin, dict) else None
    return {
        "status": "unavailable",
        "reason": (f"thermal.solidificationKinetics unavailable: {thermal_reason}"
                   if isinstance(thermal_reason, str) and thermal_reason
                   else "thermal.solidificationKinetics missing or non-finite"),
        "G_K_m": None,
        "R_m_s": None,
        "coolingRate_K_s": None,
        "PDAS_um": None,
        "pdasBand_um": None,
        "pdasUnavailableReason": (kin.get("pdasUnavailableReason") if isinstance(kin, dict) else None) or thermal_reason,
        "SDAS_um": None,
        "sdasUnavailableReason": kin.get("sdasUnavailableReason") if isinstance(kin, dict) else None,
        "morphology": None,
    }


SCREENING_FIELD_SCOPE = (
    "Screening-field G/R from python/lpbf_thermal_solver for the selected heat source. With heatSource=rosenthal "
    "and the Build Job's inputs these are the same numbers the Build Job projects; Goldak/Eagar-Tsai fields give "
    "different G/R. Not in-situ tracking; not validated"
)

ABSOLUTE_ZERO_C = -273.15

# (payload key, calculate_meltpool_physics argument) in call order.
_SCREENING_INPUTS = (
    ("power_W", "laser_power_W"),
    ("speed_mm_s", "scan_speed_mm_s"),
    ("beamDiameter_um", "beam_diameter_um"),
    ("preheat_C", "preheat_temp_C"),
    ("layerThickness_um", "layer_thickness_um"),
    ("hatch_um", "hatch_spacing_um"),
)


def _unavailable_screening(reason: str, heat_source: Any = None) -> Dict[str, Any]:
    return {
        "status": "unavailable",
        "reason": reason,
        "source": "none",
        "heatSourceModel": heat_source if isinstance(heat_source, str) else None,
        "G_K_m": None,
        "R_m_s": None,
        "coolingRate_K_s": None,
        "PDAS_um": None,
        "SDAS_um": None,
        "morphology": None,
        "doi": None,
        "disclaimer": _MICROSTRUCTURE_DISCLAIMER_SCREENING,
        "scope": SCREENING_FIELD_SCOPE,
    }


_MICROSTRUCTURE_DISCLAIMER_SCREENING = (
    "Screening conduction-field G/R with Hunt G/R morphology bands; PDAS as the sourced Ni-Nb band or null, SDAS null (P7a). "
    "Not in-situ front tracking, not calibrated, not experimentally validated."
)


def compute_screening_field_microstructure(params: Any) -> Dict[str, Any]:
    """
    Screening-field solidification microstructure for the Microstructure Lab.

    params: materialName (THERMOPHYSICAL_DB / four-alloy thermal name, e.g.
    "Inconel 718"), power_W, speed_mm_s, beamDiameter_um, preheat_C,
    layerThickness_um, hatch_um and optional heatSource ("rosenthal" when
    absent; "eagar-tsai" or "goldak"). Every input is required (no defaults);
    power, speed, beam, layer and hatch must be > 0 and preheat_C must be above
    -273.15 C and below the alloy liquidus (otherwise status "unavailable").

    The numbers are thermal["solidificationKinetics"] from
    lpbf_thermal_solver.calculate_meltpool_physics, projected by
    project_build_job_microstructure (status "available" for the liquidus field
    map, "screening-fallback" for the tail-length heuristic, "degenerate-floor"
    when R/cooling sit on the solver clamp floors). Nothing is
    estimated here. Missing or unusable inputs return status "unavailable" with
    a reason instead of raising.
    """
    if not isinstance(params, dict):
        return _unavailable_screening("params object missing")
    material_name = params.get("materialName")
    heat_source = params.get("heatSource", "rosenthal")
    if heat_source is None:
        heat_source = "rosenthal"
    if not isinstance(material_name, str) or not material_name.strip():
        return _unavailable_screening("materialName missing: no default or surrogate alloy is used", heat_source)
    values: Dict[str, float] = {}
    for key, _ in _SCREENING_INPUTS:
        value = params.get(key)
        if not _finite_number(value):
            return _unavailable_screening(f"{key} missing or not a finite number: no default is used", heat_source)
        values[key] = float(value)

    from lpbf_thermal_solver import SECONDARY_THERMOPHYSICAL_DB, calculate_meltpool_physics
    from four_alloy_materials import thermal_props

    # Physical input checks (the UI bounds are not the contract): every geometry/process input > 0 and the
    # preheat above absolute zero and below the alloy liquidus.
    for key in ("power_W", "speed_mm_s", "beamDiameter_um", "layerThickness_um", "hatch_um"):
        if values[key] <= 0.0:
            return _unavailable_screening(f"{key} must be finite and positive (got {values[key]:g})", heat_source)
    if values["preheat_C"] <= ABSOLUTE_ZERO_C:
        return _unavailable_screening(
            f"preheat_C must be above absolute zero ({ABSOLUTE_ZERO_C} C) (got {values['preheat_C']:g})", heat_source)
    props = thermal_props(material_name) or SECONDARY_THERMOPHYSICAL_DB.get(material_name)
    liquidus_c = props.get("liquidus_C") if isinstance(props, dict) else None
    if _finite_number(liquidus_c) and values["preheat_C"] >= liquidus_c:
        return _unavailable_screening(
            f"preheat_C must be below the alloy liquidus ({liquidus_c:g} C) (got {values['preheat_C']:g})", heat_source)

    try:
        thermal = calculate_meltpool_physics(
            material_name,
            values["power_W"],
            values["speed_mm_s"],
            values["beamDiameter_um"],
            values["preheat_C"],
            values["layerThickness_um"],
            values["hatch_um"],
            heat_source=heat_source,
        )
    except ValueError as exc:
        return _unavailable_screening(str(exc), heat_source)

    from solidification_front import (
        G_OVER_R_COLUMNAR as _FRONT_COLUMNAR,
        G_OVER_R_CELLULAR as _FRONT_CELLULAR,
        G_OVER_R_PLANAR as _FRONT_PLANAR,
    )

    block = project_build_job_microstructure(thermal, note=_SCREENING_PROJECTION_NOTE)
    process = thermal.get("processParameters") if isinstance(thermal.get("processParameters"), dict) else {}
    block.update({
        "heatSourceModel": thermal.get("heatSourceModel"),
        "materialName": thermal.get("material", material_name),
        "inputs": {key: values[key] for key, _ in _SCREENING_INPUTS},
        "absorptivity": {
            "effective": process.get("effectiveAbsorptivity"),
            "conduction": process.get("conductionAbsorptivity"),
        },
        # Hunt G/R bands (K s / m^2) read from solidification_front, the module that classifies morphology.
        "morphologyBands_G_over_R": {
            "planar": _FRONT_PLANAR,
            "cellular": _FRONT_CELLULAR,
            "columnar": _FRONT_COLUMNAR,
        },
        "scope": SCREENING_FIELD_SCOPE,
    })
    if "materialEvidence" in thermal:
        block["materialEvidence"] = thermal["materialEvidence"]
    return block


def compute_solidification_microstructure(
    params: Dict[str, Any],
    material: Dict[str, Any],
    cfd_result: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """
    Compute solidification microstructure metrics from CFD solidification data.

    Parameters
    ----------
    params   : LPBF process parameters (kept for the RPC signature; not used to
               estimate G/R)
    material : Alloy properties (kept for the RPC signature; not used to
               estimate G/R)
    cfd_result : Optional output from cfd_multiphysics(); the
                 solidificationMicrostructure sub-dict from the OpenFOAM JSON
                 supplies G and R.

    Returns
    -------
    With CFD data: status "available" and keys
        source, G_K_m, maxG_K_m, R_m_s, maxR_m_s, coolingRate_K_s,
        PDAS_um, SDAS_um, morphology, morphologyFractions,
        frontCellCount, graftAnnotation
    Without CFD data: status "unavailable", source "none", a reason, and None
    for every numeric field (no default-constant estimate is ever returned).
    """
    cfd_solid = {}
    if cfd_result and isinstance(cfd_result.get("solidificationMicrostructure"), dict):
        cfd_solid = cfd_result["solidificationMicrostructure"]

    if not bool(cfd_solid.get("meanG_K_m")):
        return {
            "status": "unavailable",
            "source": "none",
            "reason": _UNAVAILABLE_NO_CFD_REASON,
            "G_K_m": None,
            "maxG_K_m": None,
            "R_m_s": None,
            "maxR_m_s": None,
            "coolingRate_K_s": None,
            "PDAS_um": None,
            "SDAS_um": None,
            "morphology": None,
            "morphologyFractions": None,
            "frontCellCount": None,
            "doi": dict(_MICROSTRUCTURE_DOI),
            "disclaimer": _MICROSTRUCTURE_DISCLAIMER,
            "graftAnnotation": "covers: python/lpbf_solidification_microstructure.py",
        }

    G    = float(cfd_solid["meanG_K_m"])
    R    = float(cfd_solid["meanR_m_s"])
    Tdot = float(cfd_solid.get("meanCoolingRate_K_s", G * R))
    maxG = float(cfd_solid.get("maxG_K_m", G))
    maxR = float(cfd_solid.get("maxR_m_s", R))
    front_cells = int(cfd_solid.get("frontCellCount", 0))
    source = "openfoam-solidification-model-v1"

    # ---- Morphology (PDAS/SDAS not served: unsourced prefactors deleted, P7a) ----
    morph = hunt_morphology(G, R)
    fracs = morphology_fractions(G, R)

    # ---- Validate physical bounds (unit-test oracle; CFD path only) --------
    assert 1.0e3 <= G <= 1.0e10, f"G={G:.3e} K/m out of physical range [1e3, 1e10]"
    assert 1.0e-6 <= R <= 2.0,   f"R={R:.3e} m/s out of physical range [1e-6, 2]"
    total_frac = fracs["columnar"] + fracs["equiaxed"] + fracs["mixed"]
    assert abs(total_frac - 1.0) < 0.01, f"Morphology fractions sum {total_frac:.4f} ≠ 1"

    return {
        "status": "available",
        "source": source,
        "G_K_m": round(G, 2),
        "maxG_K_m": round(maxG, 2),
        "R_m_s": round(R, 6),
        "maxR_m_s": round(maxR, 6),
        "coolingRate_K_s": round(Tdot, 2),
        "PDAS_um": None,
        "SDAS_um": None,
        "spacingUnavailableReason": CFD_SPACING_UNAVAILABLE_REASON,
        "morphology": morph,
        "morphologyFractions": fracs,
        "frontCellCount": front_cells,
        "doi": dict(_MICROSTRUCTURE_DOI),
        "disclaimer": _MICROSTRUCTURE_DISCLAIMER,
        "graftAnnotation": "covers: python/lpbf_solidification_microstructure.py",
    }
