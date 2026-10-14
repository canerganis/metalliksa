"""Current material-route inventory is explicit and cannot admit a surrogate alloy."""

import hashlib
import json
import unittest

from four_alloy_materials import (
    ALLOY_MATERIALS, FOUR_ALLOY_IDS, THERMAL_NAME,
    canonical_material_source, resolve_alloy_id,
)
from in625_thermal_material import (
    in625_lpbf_thermal_snapshot, validate_in625_screening_admission,
)
from lpbf_build_job_material_snapshot import build_material_property_snapshot
from lpbf_job_cache import BUILD_JOB_SOLVER_REVISION
from lpbf_material_capabilities import capability_for, material_capability_report
from lpbf_material_registry import material


class MaterialCapabilityAuditTests(unittest.TestCase):
    def test_four_existing_alloys_reflect_actual_build_and_transient_snapshots(self):
        report = material_capability_report()
        self.assertEqual(report["schemaVersion"], 1)
        self.assertEqual(set(report["alloys"]), set(FOUR_ALLOY_IDS) | {"in625"})
        for alloy_id in FOUR_ALLOY_IDS:
            with self.subTest(alloy_id=alloy_id):
                row = report["alloys"][alloy_id]
                names = ALLOY_MATERIALS[alloy_id]
                expected_build, expected_sha = build_material_property_snapshot(
                    alloy_id, names["thermal"], names["slicer"]
                )
                expected_transient = material(THERMAL_NAME[alloy_id])
                authority_snapshot, authority_revision_sha256 = canonical_material_source(alloy_id)
                self.assertTrue(row["buildJob"]["available"])
                self.assertEqual(row["buildJob"]["modelId"], "rosenthal-screening-v1")
                self.assertEqual(row["buildJob"]["solverRevision"], BUILD_JOB_SOLVER_REVISION)
                self.assertEqual(row["buildJob"]["effectiveThermal"], expected_build["thermal"])
                self.assertEqual(row["buildJob"]["effectiveSlicer"], expected_build["slicer"])
                self.assertEqual(row["buildJob"]["materialPropertySha256"], expected_sha)
                self.assertEqual(row["buildJob"]["authority"], authority_snapshot["authority"])
                self.assertEqual(row["buildJob"]["authorityRevisionSha256"], authority_revision_sha256)
                self.assertTrue(row["fullTransient"]["available"])
                self.assertEqual(expected_transient["materialAuthority"], authority_snapshot["authority"])
                self.assertEqual(expected_transient["materialAuthorityRevisionSha256"], authority_revision_sha256)
                self.assertEqual(row["fullTransient"]["authority"], authority_snapshot["authority"])
                self.assertEqual(row["fullTransient"]["authorityRevisionSha256"], authority_revision_sha256)
                self.assertEqual(row["fullTransient"]["provenanceClass"], "estimated-legacy")
                self.assertEqual(row["fullTransient"]["materialRevisionSha256"],
                                 expected_transient["materialRevisionSha256"])
                self.assertEqual(row["fullTransient"]["propertyTable"], expected_transient["table"])
                self.assertEqual(row["fullTransient"]["modelTemperatureCoverage_K"],
                                 expected_transient["temperatureCoverage_K"])
                self.assertIsNone(row["fullTransient"]["sourceValidityRange_K"])
                self.assertTrue(row["marangoniAdapter"]["inputsPresent"])
                self.assertTrue(row["inherentStrainAdapter"]["inputsPresent"])
                self.assertEqual(row["marangoniAdapter"]["modelQualification"], "open")
                self.assertEqual(row["samePhysicsGpuQualification"], "open")
                self.assertFalse(row["boundedFusionEnthalpyScreening"]["available"])
                # P7b (2026-10-14): one authority value for every model (the former per-table duplicates are gone);
                # the dH/hs index reads the separate convention constant, which differs for the measured alloys.
                cross = row["crossModelAbsorptivity"]
                self.assertEqual(len({cross[k] for k in ("buildJobIR", "transient", "marangoni", "inherentStrain")}), 1)
                self.assertEqual(cross["buildJobIR"], cross["authority"]["value"])
                self.assertEqual(cross["indexConvention"], expected_build["thermal"]["absorptivity_index_IR"])
                self.assertEqual(row["kernelLedger"] is not None, alloy_id in ("ti6al4v", "alsi10mg"))

    def test_in625_is_bounded_screening_only_and_preserves_distinct_sources(self):
        row = capability_for("Inconel-625")
        snapshot = in625_lpbf_thermal_snapshot()
        self.assertEqual(row["admission"], "thermal-screening-only")
        self.assertFalse(row["buildJob"]["available"])
        self.assertFalse(row["fullTransient"]["available"])
        self.assertEqual(resolve_alloy_id("IN625"), None)
        with self.assertRaisesRegex(ValueError, "thermophysical data missing"):
            material("IN625")
        self.assertEqual(row["solidBulkTable"]["temperatureCoverage_C"], [-18.0, 982.0])
        self.assertEqual(row["solidBulkTable"]["endpointValues"]["high"], {
            "thermal_conductivity_W_mK": 25.2,
            "specific_heat_J_kgK": 645.0,
        })
        self.assertTrue(row["boundedFusionEnthalpyScreening"]["available"])
        self.assertEqual(row["boundedFusionEnthalpyScreening"]["snapshot"], snapshot)
        admission = row["boundedFusionEnthalpyScreening"]["admission"]
        self.assertTrue(admission["accepted"])
        self.assertEqual(admission["scope"], "bounded-fusion-enthalpy-screening")
        self.assertEqual(admission["materialRevisionSha256"], snapshot["materialRevisionSha256"])
        self.assertFalse(admission["fullTransientAdmitted"])
        self.assertFalse(admission["experimentalValidation"])
        self.assertEqual(row["boundedFusionEnthalpyScreening"]["modelTemperatureCoverage_K"],
                         [273.15, 1623.15])
        self.assertIsNone(row["boundedFusionEnthalpyScreening"]["sourceValidityRange_K"])
        self.assertTrue(row["barePlateThermalField"]["available"])
        self.assertEqual(row["barePlateThermalField"]["temperatureCoverage_K"], [273.15, 1623.15])
        self.assertEqual(row["barePlateThermalField"]["density"]["kg_m3"], 8440.0)
        self.assertIn("not lot-matched", row["barePlateThermalField"]["density"]["basis"])
        self.assertEqual(row["barePlateThermalField"]["gpuDevicePolicy"], "explicit cuda:N; no CPU fallback")
        self.assertFalse(row["barePlateThermalField"]["experimentalValidation"])
        self.assertEqual(row["samePhysicsGpuQualification"], "bounded-bare-plate-numerical-parity-only")
        self.assertNotEqual(row["solidBulkTable"]["source"], snapshot["source"])
        self.assertFalse(row["marangoniAdapter"]["inputsPresent"])
        self.assertFalse(row["inherentStrainAdapter"]["inputsPresent"])

    def test_in625_bounded_admission_rejects_modified_identity_source_or_model_inputs(self):
        snapshot = in625_lpbf_thermal_snapshot()
        accepted = validate_in625_screening_admission(snapshot)
        self.assertTrue(accepted["accepted"])
        self.assertIsNone(accepted["sourceValidityRange_K"])
        for field, value in (
            ("materialId", "in718"),
            ("source", "https://example.invalid/borrowed-source"),
            ("solidus_K", snapshot["solidus_K"] + 1),
        ):
            changed = dict(snapshot)
            changed[field] = value
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "digest mismatch"):
                validate_in625_screening_admission(changed)

        wrong_but_rehashed = dict(snapshot)
        wrong_but_rehashed["materialId"] = "in718"
        wrong_but_rehashed.pop("materialRevisionSha256")
        payload = json.dumps(wrong_but_rehashed, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=True, allow_nan=False).encode("utf-8")
        wrong_but_rehashed["materialRevisionSha256"] = hashlib.sha256(payload).hexdigest()
        with self.assertRaisesRegex(ValueError, "pinned source scope"):
            validate_in625_screening_admission(wrong_but_rehashed)

    def test_report_is_json_serializable_and_caller_mutation_cannot_change_authorities(self):
        report = material_capability_report()
        self.assertEqual(json.loads(json.dumps(report, allow_nan=False)), report)
        report["alloys"]["in718"]["buildJob"]["effectiveThermal"]["absorptivity_IR"] = 999
        self.assertNotEqual(material_capability_report()["alloys"]["in718"]["buildJob"]["effectiveThermal"]["absorptivity_IR"], 999)

    def test_executed_in718_build_job_and_transient_bind_same_authority_revision(self):
        from lpbf_build_job_solver import solve_lpbf_build_job

        result = solve_lpbf_build_job({
            "alloyId": "in718", "laserPower_W": 200, "scanSpeed_mm_s": 900,
            "beamDiameter_um": 80, "preheatTemp_C": 100,
            "layerThickness_um": 30, "hatchSpacing_um": 100,
            "preset": "nozzle", "bypassCache": True,
        })
        transient = material(THERMAL_NAME["in718"])
        self.assertTrue(result["success"], result.get("error"))
        self.assertEqual(result["materialAuthority"], transient["materialAuthority"])
        self.assertEqual(result["materialAuthorityRevisionSha256"],
                         transient["materialAuthorityRevisionSha256"])

    def test_identity_resolution_rejects_unsupported_alloys_without_fallback(self):
        self.assertEqual(capability_for("Ti-6Al-4V")["alloyId"], "ti6al4v")
        self.assertEqual(capability_for("IN625")["alloyId"], "in625")
        for value in ("CoCrMo", "Hastelloy", "", None):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "Unsupported LPBF alloy"):
                capability_for(value)


if __name__ == "__main__":
    unittest.main()
