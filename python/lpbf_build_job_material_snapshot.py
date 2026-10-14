"""Effective material inputs consumed by the LPBF build-job thermal and slicer paths.

The digest identifies input content only; it is not a provenance or validation claim.
"""

import hashlib
import json
import math

from four_alloy_materials import (INDEX_FULL_SET_KEYS, INDEX_KEY_IR, MELT_KEYS, kernel_ledger_sha256,
                                  resolve_alloy_id, slicer_props, thermal_props)


MATERIAL_PROPERTY_SCHEMA_VERSION = 1
MATERIAL_PROPERTY_REVISION = "build-job-effective-properties-v1"
BUILD_JOB_IDENTITY_SCHEMA_VERSION = 1

# Keep this list aligned with property reads in lpbf_thermal_solver. Optional
# properties are materialized with the same defaults as that solver. P7b (2026-10-14): the physical keys are the
# authority's INDEX_FULL_SET_KEYS (a manifest constant) plus the index convention key absorptivity_index_IR, so the
# snapshot freezes the index constant for every Build Job material and the solver's full-set rule reads it (rule 1).
_THERMAL_REQUIRED = INDEX_FULL_SET_KEYS + (INDEX_KEY_IR,)
# P7b: melting-point k and cp (absent means the solver blends) and the kernel density (AlSi10Mg 2696) are frozen when
# the authority carries them. No kernel K / cp key is frozen: the ledger alloys' kernel is evaluated per call at the
# job's own preheat (the snapshot digest must not depend on a process input); the ledger's numeric identity is frozen
# as kernelLedgerSha256 instead.
_THERMAL_OPTIONAL = MELT_KEYS + ("kernel_density_kg_m3",)


def _effective_thermal(thermal):
    """Freeze exactly the thermal solver's required and defaulted reads."""
    effective = {key: thermal[key] for key in _THERMAL_REQUIRED}
    effective.update({key: thermal[key] for key in _THERMAL_OPTIONAL if key in thermal})
    effective.update({
        "thermal_conductivity_liquid_W_mK": thermal.get(
            "thermal_conductivity_liquid_W_mK", thermal["thermal_conductivity_W_mK"]
        ),
        "specific_heat_liquid_J_kgK": thermal.get(
            "specific_heat_liquid_J_kgK", thermal["specific_heat_J_kgK"]
        ),
        "density_liquid_kg_m3": thermal.get("density_liquid_kg_m3", thermal["density_kg_m3"]),
        "M_molar_kg_mol": thermal.get("M_molar_kg_mol", 0.055),
        # unused since P7a (2026-10-11): the solver reads neither; kept so materialPropertySha256 does not move.
        "pdas_A1": thermal.get("pdas_A1", 75.0),
        "sdas_B1": thermal.get("sdas_B1", 40.0),
    })
    for key, value in effective.items():
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
            raise ValueError(f"Non-finite build-job thermal property: {key}")
    base = thermal["base"]
    if not isinstance(base, str) or not base:
        raise ValueError("Invalid build-job base metal")
    return {"base": base, **effective}


def _digest(snapshot):
    raw = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_material_property_snapshot(alloy_id, thermal_name, slicer_name):
    """Copy and validate effective build-job inputs before lookup or solver use."""
    thermal = thermal_props(thermal_name)
    slicer = slicer_props(slicer_name)
    if not thermal or not slicer:
        raise ValueError(f"Missing build-job material properties for {alloy_id!r}")
    density = slicer["density_gcm3"]
    if isinstance(density, bool) or not isinstance(density, (float, int)) or not math.isfinite(density):
        raise ValueError("Non-finite build-job slicer density")
    snapshot = {
        "schemaVersion": MATERIAL_PROPERTY_SCHEMA_VERSION,
        "alloyId": alloy_id,
        "thermal": _effective_thermal(thermal),
        "slicer": {"density_gcm3": density},
    }
    ledger_sha = kernel_ledger_sha256(alloy_id)
    if ledger_sha is not None:
        # P7b: the kernel ledger's numeric projection is part of the Build Job material identity (ledger alloys only).
        snapshot["kernelLedgerSha256"] = ledger_sha
    return snapshot, _digest(snapshot)


def build_build_job_identity(
    alloy_id,
    model_id,
    solver_revision,
    material_property_sha256,
    material_property_schema_version=MATERIAL_PROPERTY_SCHEMA_VERSION,
    material_property_revision=MATERIAL_PROPERTY_REVISION,
):
    """Hash canonical model and effective-property identity independently of properties."""
    canonical_alloy_id = resolve_alloy_id(alloy_id)
    if canonical_alloy_id is None:
        raise ValueError(f"Unsupported LPBF alloy identity: {alloy_id!r}")
    for field, value in (("modelId", model_id), ("solverRevision", solver_revision),
                         ("materialPropertyRevision", material_property_revision)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Invalid build-job identity {field}")
    if (isinstance(material_property_schema_version, bool)
            or not isinstance(material_property_schema_version, int)
            or material_property_schema_version < 1):
        raise ValueError("Invalid material property snapshot schema version")
    if (not isinstance(material_property_sha256, str)
            or len(material_property_sha256) != 64
            or any(char not in "0123456789abcdef" for char in material_property_sha256)):
        raise ValueError("Invalid material property snapshot SHA-256")
    identity = {
        "schemaVersion": BUILD_JOB_IDENTITY_SCHEMA_VERSION,
        "alloyId": canonical_alloy_id,
        "modelId": model_id,
        "solverRevision": solver_revision,
        "materialPropertySchemaVersion": material_property_schema_version,
        "materialPropertyRevision": material_property_revision,
        "materialPropertySha256": material_property_sha256,
    }
    return {**identity, "sha256": _digest(identity)}


def build_ambench_material_property_snapshot(in625_props):
    """Identify the separate IN625 bare-plate comparison inputs, not a build alloy."""
    snapshot = {
        "schemaVersion": MATERIAL_PROPERTY_SCHEMA_VERSION,
        "scope": "amb2018-02-in625-bare-plate-screening",
        "provenanceClass": "screening-assumption-unverified",
        "propertySource": "nist_ambench_2018_02.IN625_VALIDATION_PROPS",
        "alloyId": "in625",
        "thermal": _effective_thermal(in625_props),
    }
    return snapshot, _digest(snapshot)
