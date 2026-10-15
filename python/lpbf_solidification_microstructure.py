"""SOL-A1 consumer projections of the source-bounded thermal front envelope.

No local morphology classifier, spacing formula, floor or legacy CFD numerical path is served.
"""
import math
from typing import Any, Dict


def _finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


_BUILD_JOB_PROJECTION_NOTE = "thermal.solidificationKinetics"
_SCREENING_PROJECTION_NOTE = _BUILD_JOB_PROJECTION_NOTE


def _refused_front(code: str) -> Dict[str, Any]:
    from quantity_envelope import container, input_record, reason, unavailable
    from solidification_front import FRONT_QUANTITIES
    inputs = {"frontRequest": input_record("declaredAssumption", "request:front-admission",
              status="outOfRange", declaration_locator="python/lpbf_solidification_microstructure.py",
              scope="unadmitted-front-request")}
    return container({name: unavailable(definition, [reason(code)], depends_on=("frontRequest",))
                      for name, (definition, _) in FRONT_QUANTITIES.items()}, input_provenance=inputs)


def project_build_job_microstructure(thermal: Dict[str, Any], *, note: str = _BUILD_JOB_PROJECTION_NOTE) -> Dict[str, Any]:
    """Copy the admitted front container, without a second estimate or legacy-key fallback."""
    import copy

    kin = thermal.get("solidificationKinetics") if isinstance(thermal, dict) else None
    if isinstance(kin, dict) and isinstance(kin.get("quantities"), dict):
        block = copy.deepcopy({key: kin[key] for key in ("quantityEnvelopeSchema", "moduleEvidenceCeiling",
                                                         "moduleMaturity", "quantities", "inputProvenance",
                                                         "modelId", "alloyId") if key in kin})
    else:
        block = _refused_front("parent-unavailable")
    states = [q.get("status") for q in block["quantities"].values()]
    block["status"] = ("computed" if all(s == "computed" for s in states) else
                       "partial" if any(s in ("computed", "partial") for s in states) else "unavailable")
    geometry = thermal.get("meltPoolGeometry") or {}
    process = thermal.get("processParameters") or {}
    block.update(schema="lpbf-solidification-microstructure-2", source="thermal.solidificationKinetics",
                 regime=geometry.get("regime"), normalizedEnthalpy=process.get("normalizedEnthalpy"))
    return block


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
    block = project_build_job_microstructure({})
    block.update(source="none", heatSourceModel=heat_source if isinstance(heat_source, str) else None)
    block.update(_refused_front("nonphysical-input"))
    return block


def compute_screening_field_microstructure(params: Any) -> Dict[str, Any]:
    """Validate process inputs and project the thermal front envelope without recomputation."""
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
    """Refuse the retired CFD numerical path, including an explicitly empty CFD payload."""
    block = project_build_job_microstructure({})
    block["source"] = "none"
    block.update(_refused_front("quarantined-legacy-path"))
    return block
