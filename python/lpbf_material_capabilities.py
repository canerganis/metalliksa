"""Read-only, machine-readable inventory of current LPBF material authorities.

Capability means a code path has inputs, not that its predictions are validated.
Each model retains its own constitutive inputs; this report never merges them.
"""

import json

from four_alloy_materials import (
    ALLOY_MATERIALS, FOUR_ALLOY_IDS, LITERATURE_MELT_POOL_CASES, PROPERTY_LEDGER,
    THERMAL_NAME, absorptivity_authority, canonical_material_source, inherent_strain_props,
    kernel_ledger_sha256, kernel_properties, marangoni_props, resolve_alloy_id, PROPERTY_PROVENANCE,
)
from in625_thermal_material import (
    SOLID_TEMPERATURE_RANGE_C, SOURCE_URL, in625_lpbf_thermal_snapshot,
    in625_solid_thermal_at_celsius, validate_in625_screening_admission,
)
from lpbf_build_job_material_snapshot import build_material_property_snapshot
from lpbf_job_cache import BUILD_JOB_SOLVER_REVISION
from lpbf_material_registry import catalog, material


SCHEMA_VERSION = 1


def _four_alloy_capability(alloy_id):
    names = ALLOY_MATERIALS[alloy_id]
    build_snapshot, build_sha = build_material_property_snapshot(
        alloy_id, names["thermal"], names["slicer"]
    )
    authority_snapshot, authority_revision_sha256 = canonical_material_source(alloy_id)
    transient = material(THERMAL_NAME[alloy_id])
    marangoni = marangoni_props(alloy_id)
    inherent_strain = inherent_strain_props(alloy_id)
    comparison = next(case for case in LITERATURE_MELT_POOL_CASES
                      if case["alloy_id"] == alloy_id)
    return {
        "alloyId": alloy_id,
        "displayName": THERMAL_NAME[alloy_id],
        "admission": "existing-four-alloy-screening",
        "buildJob": {
            "available": True,
            "modelId": "rosenthal-screening-v1",
            "solverRevision": BUILD_JOB_SOLVER_REVISION,
            "authority": authority_snapshot["authority"],
            "authorityRevisionSha256": authority_revision_sha256,
            "materialPropertySha256": build_sha,
            "thermalName": names["thermal"],
            "slicerName": names["slicer"],
            "effectiveThermal": build_snapshot["thermal"],
            "effectiveSlicer": build_snapshot["slicer"],
            "sourceValidityRange_K": None,
            "evidenceStatus": "estimated-screening-inputs-unvalidated",
        },
        "fullTransient": {
            "available": True,
            "authority": transient["materialAuthority"],
            "authorityRevisionSha256": transient["materialAuthorityRevisionSha256"],
            "materialRevisionSha256": transient["materialRevisionSha256"],
            "provenanceClass": transient["provenanceClass"],
            "modelTemperatureCoverage_K": transient["temperatureCoverage_K"],
            "sourceValidityRange_K": None,
            "propertyTableColumns": ["T_K", "rho_kg_m3", "k_W_mK", "Cp_J_kgK", "viscosity_Pa_s"],
            "propertyTable": transient["table"],
            "solidus_K": transient["solidus_K"],
            "liquidus_K": transient["liquidus_K"],
            "boiling_K": transient["boiling_K"],
            "latentHeat_J_kg": transient["latentHeat_J_kg"],
            "absorptivity": transient["absorptivity"],
            "emissivity": transient["emissivity"],
            "dGamma_dT": transient["dGamma_dT"],
            "evidenceStatus": "estimated-legacy-model-unvalidated",
        },
        "marangoniAdapter": {
            "inputsPresent": True,
            "authority": "four_alloy_materials.marangoni_props",
            "inputs": marangoni,
            "modelQualification": "open",
        },
        "inherentStrainAdapter": {
            "inputsPresent": True,
            "authority": "four_alloy_materials.inherent_strain_props",
            "inputs": inherent_strain,
            "modelQualification": "open",
        },
        "boundedFusionEnthalpyScreening": {
            "available": False,
            "reason": "Dedicated bounded fusion-enthalpy route currently exists only for IN625.",
        },
        "comparisonFixture": {
            "id": comparison["id"],
            "check": comparison["check"],
            "source": comparison["source"],
            "doi": comparison["doi"],
            "widthDepthBasis": comparison.get("widthDepthBasis"),
            # True only for a cited, measured track; typical or asymptotic W/D are not "published".
            "publishedWidthDepthPresent": (comparison["publishedWidth_um"] is not None
                                           and comparison["publishedDepth_um"] is not None
                                           and comparison.get("widthDepthBasis") == "published-measurement"),
            "evidenceStatus": "screening-fixture-not-independent-validation",
        },
        "crossModelAbsorptivity": {
            "buildJobIR": build_snapshot["thermal"]["absorptivity_IR"],
            "transient": transient["absorptivity"],
            "marangoni": marangoni["absorptivity"],
            "inherentStrain": inherent_strain["absorptivity"],
            # P7b (2026-10-14): one authority value for every model (the former per-table duplicates are deleted); the
            # dH/hs regime index reads the separate convention constant absorptivity_index_IR.
            "indexConvention": build_snapshot["thermal"]["absorptivity_index_IR"],
            "authority": absorptivity_authority(alloy_id),
            "note": ("One authority value since P7b (a sourcing correction, not validation); the regime index reads "
                     "the index convention constant."),
        },
        # P7b: the kernel ledger (Ti-6Al-4V, AlSi10Mg) that the conduction kernel reduces per call (Kirchhoff mean at
        # the request preheat); the 293.15 K evaluation is the test anchor, not the served value at every preheat.
        "kernelLedger": None if alloy_id not in PROPERTY_LEDGER else {
            "authority": "four_alloy_materials.PROPERTY_LEDGER",
            "kernelLedgerSha256": kernel_ledger_sha256(alloy_id),
            "numeric": PROPERTY_LEDGER[alloy_id]["numeric"],
            "text": PROPERTY_LEDGER[alloy_id]["text"],
            "kernelAt293_15K": kernel_properties(alloy_id, 293.15),
            "evidenceKind": "Literature estimate",
            "evidenceStatus": "sourcing-correction-not-validation",
        },
        "crossModelDGammaDT": {
            "buildJob": build_snapshot["thermal"]["d_gamma_dT_N_mK"],
            "transient": transient["dGamma_dT"],
            "marangoniPure": marangoni["d_gamma_dT_pure_N_mK"],
            "provenance": PROPERTY_PROVENANCE.get(alloy_id, {}).get("d_gamma_dT_N_mK"),
        },
        "emissivityProvenance": PROPERTY_PROVENANCE["*"]["emissivity"],
        "samePhysicsGpuQualification": "open",
    }


def _in625_capability():
    screening = in625_lpbf_thermal_snapshot()
    screening_admission = validate_in625_screening_admission(screening)
    low_c, high_c = SOLID_TEMPERATURE_RANGE_C
    registry = next(row for row in catalog() if row["name"] == "Inconel 625")
    return {
        "alloyId": "in625",
        "displayName": "Inconel 625",
        "admission": "thermal-screening-only",
        "buildJob": {
            "available": False,
            "reason": "IN625 is absent from the locked four-alloy build-job identity and slicer map.",
        },
        "fullTransient": {
            "available": registry["available"],
            "reason": "No source-backed five-property table through an independently supported boiling temperature, with the required optical and flow inputs.",
            "requiredPropertyTableColumns": ["T_K", "rho_kg_m3", "k_W_mK", "Cp_J_kgK", "viscosity_Pa_s"],
            "futureRoute": "A complete sourced user-supplied table can be evaluated separately; no default IN625 transient material is admitted.",
        },
        "solidBulkTable": {
            "available": True,
            "authority": "in625_thermal_material.in625_solid_thermal_at_celsius",
            "source": SOURCE_URL,
            "sourceLocators": {
                "specificHeat": "Table 2 (calculated values)",
                "conductivity": "Table 3 (annealed bulk material measurements)",
            },
            "temperatureCoverage_C": [low_c, high_c],
            "properties": ["specific_heat_J_kgK", "thermal_conductivity_W_mK"],
            "endpointValues": {
                "low": in625_solid_thermal_at_celsius(low_c),
                "high": in625_solid_thermal_at_celsius(high_c),
            },
            "evidenceStatus": "source-bounded-bulk-solid-only",
        },
        "boundedFusionEnthalpyScreening": {
            "available": screening_admission["accepted"],
            "admission": screening_admission,
            "authority": "in625_thermal_material.in625_lpbf_thermal_snapshot",
            "snapshot": screening,
            "modelTemperatureCoverage_K": screening["temperatureCoverage_K"],
            "sourceValidityRange_K": None,
            "evidenceStatus": screening["validationStatus"],
        },
        "barePlateThermalField": {
            "available": True,
            "authority": "in625_bareplate_field.run_cpu/run_cuda",
            "model": "3D bounded enthalpy conduction; bare substrate; adiabatic faces",
            "temperatureCoverage_K": screening["temperatureCoverage_K"],
            "density": {
                "kg_m3": 8440.0,
                "basis": "constant supplier-bulletin assumption; not lot-matched",
                "source": "https://www.specialmetals.com/documents/technical-bulletins/inconel/inconel-alloy-625.pdf",
            },
            "sourceInput": "explicit absorbed W; no absorptivity is inferred",
            "gpuDevicePolicy": "explicit cuda:N; no CPU fallback",
            "experimentalValidation": False,
            "evidenceStatus": screening["validationStatus"],
        },
        "marangoniAdapter": {"inputsPresent": False, "modelQualification": "unavailable"},
        "inherentStrainAdapter": {"inputsPresent": False, "modelQualification": "unavailable"},
        "samePhysicsGpuQualification": "bounded-bare-plate-numerical-parity-only",
        "samePhysicsGpuQualificationScope": "No powder-bed, full-transient, melt-flow, experimental-validation, or production qualification.",
        "modelBoundary": "The solid bulletin table and Sabau/JMatPro enthalpy model are separate authorities; this bare-plate path is screening-only and does not admit a full LPBF transient material.",
    }


def material_capability_report():
    """Snapshot current configured inputs without mutating any solver or registry."""
    return {
        "schemaVersion": SCHEMA_VERSION,
        "kind": "lpbf-material-authority-capability-audit",
        "claimBoundary": "Input availability and content identity do not establish experimental validation or source quality.",
        "alloys": {**{aid: _four_alloy_capability(aid) for aid in FOUR_ALLOY_IDS},
                   "in625": _in625_capability()},
    }


def capability_for(name):
    """Resolve only a known identity; never use a surrogate alloy."""
    alloy_id = resolve_alloy_id(name)
    if alloy_id is None and isinstance(name, str):
        compact = "".join(name.strip().lower().split()).replace("-", "")
        if compact in ("in625", "inconel625"):
            alloy_id = "in625"
    if alloy_id is None:
        raise ValueError("Unsupported LPBF alloy identity; no surrogate capability is returned")
    return material_capability_report()["alloys"][alloy_id]


if __name__ == "__main__":
    print(json.dumps(material_capability_report(), sort_keys=True, indent=2, allow_nan=False))
