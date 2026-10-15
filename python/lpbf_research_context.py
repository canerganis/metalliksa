"""P8 research route: the immutable research context (integration contract 2026-10-15, sections 3.4 and 3.8).

The research process re-derives the unrounded conduction tuple (K, cp, rho_k, alpha, A0, Tl) from the same public
resolver the served solver calls (lpbf_thermal_solver.resolve_conduction_kernel), with the same property lookup and
the same expression order as calculate_meltpool_physics, which it never calls. SI conversions happen once, here:
speed / 1000, diameter / 1e6, preheat + 273.15 (P8 spec section 2.1).

Served material data is read through a PropertyProvider, so transport tests can substitute a fixed synthetic property
set (R-TR-11) without touching served data. Research only: no served module may import this file (guard R-ISO-1).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Callable, Mapping

from lpbf_research_cache import canonical_sha256

IR_WAVELENGTH = "IR_1064nm"
PROPERTY_CONTEXT_KINDS = ("nominal", "build-job-snapshot")


@dataclass(frozen=True)
class PropertyProvider:
    """Served material lookups the research route reads (all pure functions of their arguments)."""
    base_properties: Callable[[str], Mapping | None]            # thermal_props(name) or SECONDARY_THERMOPHYSICAL_DB
    resolve_alloy_id: Callable[[str], str | None]               # four_alloy_materials.resolve_alloy_id
    alloy_thermal_name: Callable[[str], str | None]             # ALLOY_MATERIALS[aid]["thermal"]
    material_snapshot: Callable[[str], tuple]                   # canonical alloy id -> (snapshot, sha256)
    conduction_kernel: Callable[[str, dict, Any, float], tuple]  # resolve_conduction_kernel
    index_absorptivity: Callable[[str, Mapping, Any, str], float]
    wavelengths: tuple                                          # served laser wavelength enum
    absorption_models: tuple                                    # served absorption model enum


def served_property_provider() -> PropertyProvider:
    """The served lookups, imported on first use (the served solver module is never imported by a served path
    through this file, which no served module imports)."""
    import lpbf_thermal_solver as solver
    from four_alloy_materials import ALLOY_MATERIALS, resolve_alloy_id
    from lpbf_build_job_material_snapshot import build_material_property_snapshot

    def base_properties(material: str):
        return solver.thermal_props(material) or solver.SECONDARY_THERMOPHYSICAL_DB.get(material)

    def alloy_thermal_name(alloy_id: str):
        entry = ALLOY_MATERIALS.get(alloy_id)
        return None if entry is None else entry["thermal"]

    def material_snapshot(alloy_id: str):
        entry = ALLOY_MATERIALS[alloy_id]
        return build_material_property_snapshot(alloy_id, entry["thermal"], entry["slicer"])

    def index_absorptivity(wavelength, base, overrides, material):
        return float(solver.resolve_index_absorptivity(wavelength, base, overrides, material)[0])

    return PropertyProvider(
        base_properties=base_properties,
        resolve_alloy_id=resolve_alloy_id,
        alloy_thermal_name=alloy_thermal_name,
        material_snapshot=material_snapshot,
        conduction_kernel=solver.resolve_conduction_kernel,
        index_absorptivity=index_absorptivity,
        wavelengths=("IR_1064nm", "Green_515nm"),
        absorption_models=tuple(solver.ABSORPTION_MODELS),
    )


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({k: _freeze(v) for k, v in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(v) for v in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {k: _thaw(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_thaw(v) for v in value]
    return value


@dataclass(frozen=True)
class ConductionTuple:
    conductivity_W_mK: float
    specificHeat_J_kgK: float
    density_kg_m3: float
    diffusivity_m2_s: float
    wallAbsorptance: float | None
    liquidus_K: float
    propertyConvention: str

    def hex_tuple(self) -> tuple:
        values = (self.conductivity_W_mK, self.specificHeat_J_kgK, self.density_kg_m3, self.diffusivity_m2_s,
                  self.wallAbsorptance, self.liquidus_K)
        return tuple(None if v is None else float(v).hex() for v in values)


@dataclass(frozen=True)
class ResearchContext:
    """Immutable research inputs for one request; no field is a shared mutable object."""
    material: str
    alloyId: str | None
    power_W: float
    speed_m_s: float
    beamDiameter_m: float
    preheat_K: float
    preheat_C: float
    laserWavelength: str
    absorptionModel: str
    conduction: ConductionTuple
    indexAbsorptance: float | None
    propertyContextKind: str
    propertySetSha256: str
    tupleEqualsNominal: bool          # the 3.8 item 4 override gate input: resolved tuple equals the nominal tuple
    properties: Mapping[str, Any]     # read-only resolved property dict after the property context is applied

    def property_dict(self) -> dict:
        """A fresh mutable copy (never the context's own mapping)."""
        return _thaw(self.properties)


def si_process(process: Mapping[str, Any]) -> dict:
    """Contract 3.4: SI conversions done once, exactly speed / 1000, diameter / 1e6, preheat + 273.15."""
    preheat_C = float(process["preheatTemp_C"])
    return {
        "power_W": float(process["laserPower_W"]),
        "speed_m_s": float(process["scanSpeed_mm_s"]) / 1000.0,
        "beamDiameter_m": float(process["beamDiameter_um"]) / 1e6,
        "preheat_C": preheat_C,
        "preheat_K": preheat_C + 273.15,
    }


def conduction_tuple(provider: PropertyProvider, material: str, props: Mapping, prop_overrides: Any,
                     preheat_C: float) -> ConductionTuple:
    """Contract 3.8 items 2 and 3, the expression order of lpbf_thermal_solver.py:922-924 and :943."""
    k_th, cp, rho_k, convention = provider.conduction_kernel(material, props, prop_overrides, preheat_C)[:4]
    alpha = k_th / (rho_k * cp)
    a0 = props.get("absorptivity_IR")
    return ConductionTuple(
        conductivity_W_mK=k_th, specificHeat_J_kgK=cp, density_kg_m3=rho_k, diffusivity_m2_s=alpha,
        wallAbsorptance=None if a0 is None else float(a0),
        liquidus_K=float(props["liquidus_C"]) + 273.15,
        propertyConvention=str(convention),
    )


def resolve(request: Mapping[str, Any], provider: PropertyProvider) -> ResearchContext:
    """Build the context from an already checked request (lpbf_research_models runs the request checks first)."""
    process = request["process"]
    material = process["material"]
    si = si_process(process)
    base = provider.base_properties(material)
    if base is None:
        raise ValueError(f"unknown material {material!r}")
    props = dict(base)
    prop_overrides = None
    context = request["propertyContext"]
    kind = context["kind"]
    if kind == "build-job-snapshot":
        alloy_id = provider.resolve_alloy_id(context["alloyId"])
        snapshot, _sha = provider.material_snapshot(alloy_id)
        thermal = dict(snapshot["thermal"])
        props.update(thermal)
        prop_overrides = thermal
    elif kind != "nominal":
        raise ValueError(f"unknown property context kind {kind!r}")
    tuple_now = conduction_tuple(provider, material, props, prop_overrides, si["preheat_C"])
    if prop_overrides is None:
        equals_nominal = True
    else:
        nominal = conduction_tuple(provider, material, dict(base), None, si["preheat_C"])
        equals_nominal = nominal.hex_tuple() == tuple_now.hex_tuple()
    index_a = None
    if "absorptivity_IR" in props:
        index_a = provider.index_absorptivity(IR_WAVELENGTH, base, prop_overrides, material)
        if not math.isfinite(index_a):
            index_a = None
    return ResearchContext(
        material=material,
        alloyId=provider.resolve_alloy_id(material),
        power_W=si["power_W"], speed_m_s=si["speed_m_s"], beamDiameter_m=si["beamDiameter_m"],
        preheat_K=si["preheat_K"], preheat_C=si["preheat_C"],
        laserWavelength=process["laserWavelength"], absorptionModel=process["absorptionModel"],
        conduction=tuple_now,
        indexAbsorptance=index_a,
        propertyContextKind=kind,
        propertySetSha256=canonical_sha256(props),
        tupleEqualsNominal=equals_nominal,
        properties=_freeze(props),
    )
