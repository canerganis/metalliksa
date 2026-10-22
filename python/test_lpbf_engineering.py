"""Numerical verification only. Synthetic fixtures are never experimental truth."""
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
import numpy as np
from lpbf_material_registry import catalog, material, enthalpy_table


def supplied_snapshot(name):
    """A registry snapshot reused as user-supplied properties. endpointAdmission is the registry's own admission
    decision for its table, not a property a user supplies, so it is removed like the identity fields."""
    snapshot = copy.deepcopy(material(name))
    snapshot.pop("endpointAdmission", None)
    return snapshot
from lpbf_simulation import validate, run, transient, scan_segments, fingerprint
from lpbf_verification import compare, convergence
from lpbf_worker import Queue, capabilities

CASE = dict(mode="standard", backend="reference", power_W=40, mesh_um=40, trackLength_um=200,
            cooling_s=.0001, dwell_s=0)


class Verification(unittest.TestCase):
    def test_openfoam_case_uses_uniform_layer_conforming_powder_grid(self):
        from lpbf_core_physics import calculate_mesh_domain
        from lpbf_openfoam import generate_case
        p, m = validate({**CASE, "backend": "openfoam-thermal", "layer_um": 80,
                         "mesh_um": 25, "layers": 3})
        domain = calculate_mesh_domain(p)
        self.assertAlmostEqual(domain["dx"], 20e-6)
        with tempfile.TemporaryDirectory() as tmp:
            generate_case(p, m, tmp)
            block = (Path(tmp)/"system"/"blockMeshDict").read_text()
        self.assertIn(f"({domain['nxy']} {domain['nxy']} {domain['nz']})", block)
        layer_m = p["layer_um"]*1e-6
        bottom = -domain["substrate_depth"]
        for layer in range(p["layers"]+1):
            face = (layer*layer_m-bottom)/domain["dx"]
            self.assertAlmostEqual(face, round(face), places=10)
        legacy = dict(p)
        legacy.pop("powderGridPolicy")
        with tempfile.TemporaryDirectory() as tmp, self.assertRaisesRegex(
                ValueError, "require a layer-conforming grid"):
            generate_case(legacy, m, tmp)

    def test_active_gradient_excludes_future_powder(self):
        from lpbf_simulation import active_gradient
        x,y,z = np.meshgrid(np.arange(4.),np.arange(4.),np.arange(5.),indexing="ij")
        active = z < 3
        temperature = 300+2*x+3*y+4*z
        temperature[~active] = -1e9  # Deliberately unrelated inactive storage.
        gradient = active_gradient(temperature,active,1.)
        np.testing.assert_allclose(gradient[active], math.sqrt(29),rtol=1e-12)
        np.testing.assert_array_equal(gradient[~active],0.)

    def test_balance_failure_cannot_be_published_or_restored(self):
        from lpbf_evidence import enforce_thermal_balances, thermal_audits
        result = run(CASE)
        for audit,key in (("massBalance","final_kg"),("phaseAudit","solidVolume_m3"),("energyBalance","stored_J")):
            broken = copy.deepcopy(result); broken[audit][key] += 1.
            with self.assertRaisesRegex(ValueError,"failed"): enforce_thermal_balances(broken)
        p,m = validate(CASE)
        with self.assertRaisesRegex(ValueError,"audit failed"):
            thermal_audits(np.zeros((1,3)),np.ones(1),p,m,np.array([1.1]))
        with tempfile.TemporaryDirectory() as tmp:
            queue = Queue(tmp,start=False); job = queue.submit(CASE)
            broken = copy.deepcopy(result); broken["massBalance"]["relativeError"] = .1
            (Path(tmp)/job["id"]/"result.json").write_text(json.dumps(broken))
            queue.update(job["id"],status="completed")
            rejected = queue.get(job["id"])
            self.assertEqual(rejected["status"],"failed")
            self.assertIn("massBalance failed",rejected["error"])
            self.assertNotIn("result",rejected)
            self.assertNotEqual(queue.submit(CASE)["id"],job["id"])

    def test_resolved_field_artifacts(self):
        from lpbf_evidence import FieldRecorder
        with tempfile.TemporaryDirectory() as folder:
            r = run(CASE, artifact_dir=folder)
            metadata = json.loads((Path(folder)/r["fieldSeries"]).read_text())
            self.assertGreater(len(metadata["frames"]), 2)
            measured_frames = [f for f in metadata["frames"] if "geometry" in f]
            self.assertTrue(measured_frames)
            self.assertEqual(metadata["boiling_K"],r["material"]["boiling_K"])
            self.assertTrue(any(abs((f["geometry"]["along_m"][1]-f["geometry"]["along_m"][0])*1e6-r["metrics"]["length_um"])<1e-8 for f in measured_frames))
            self.assertEqual(metadata["cells"], r["discretization"]["cells"])
            xyz = np.fromfile(Path(folder)/metadata["coordinates"], dtype="<f4").reshape(-1,3)
            self.assertEqual(len(xyz), metadata["cells"])
            for frame, history in zip(metadata["frames"], r["thermalHistory"]):
                values = np.fromfile(Path(folder)/frame["path"], dtype="<f4")
                self.assertEqual(len(values), len(xyz))
                self.assertTrue(np.isfinite(values).all())
                self.assertAlmostEqual(float(values.max()), history["peak_K"], delta=.001)
                self.assertEqual(frame["time_s"], history["time_s"])
            recorder = FieldRecorder(folder, xyz, metadata["spacing_m"], material("Inconel 718"))
            with self.assertRaises(ValueError): recorder.record(0, [float("nan")]*len(xyz), 0)
            with self.assertRaises(ValueError): recorder.record(0, [300], 0)

    def test_invalid_process(self):
        for patch in ({"power_W": float("nan")}, {"speed_mm_s": -1}, {"tracks": 1.5},
                      {"mesh_um": True}, {"mode": "validated"}, {"backend": "evil;rm"},
                      {"absorptivity": 2}, {"material": "unknown"}, {"preheat_C": 1200, "material": "AlSi10Mg"},
                      {"mode": "calibration"}, {"injected": "command"}):
            with self.subTest(patch=patch), self.assertRaises(ValueError): validate(patch)

    def test_catalog_and_missing_data(self):
        self.assertEqual(len(catalog()), 15)
        for item in catalog():
            if item["available"]:
                m = material(item["name"])
                self.assertEqual(m["quality"], "estimated")
            else:
                with self.assertRaises(ValueError): material(item["name"])

    def test_material_revision_identity_is_deterministic_and_provenance_labeled(self):
        aliases = (("Ti-6Al-4V", "Ti64", "ti6al4v"),
                   ("316L Stainless Steel", "SS316L", "ss316l"),
                   ("AlSi10Mg", "ALSI10MG", "alsi10mg"),
                   ("Inconel 718", "IN718", "in718"))
        for canonical, alias, alloy_id in aliases:
            with self.subTest(alloy=alloy_id):
                first, second = material(canonical), material(alias)
                self.assertEqual(first["materialId"], alloy_id)
                self.assertEqual(second["materialId"], alloy_id)
                self.assertEqual(first["materialRevisionSha256"], second["materialRevisionSha256"])
                self.assertEqual(first["materialRevisionSha256"], material(canonical)["materialRevisionSha256"])
                self.assertEqual(first["materialIdentitySchemaVersion"], 1)
                self.assertEqual(first["provenanceClass"], "estimated-legacy")
                snapshot = dict(first)
                digest = snapshot.pop("materialRevisionSha256")
                encoded = json.dumps(snapshot, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True, allow_nan=False).encode("utf-8")
                self.assertEqual(digest, hashlib.sha256(encoded).hexdigest())

    def test_shared_reference_thermal_inputs_use_si_units(self):
        from lpbf_core_physics import thermal_si_inputs
        p, m = validate({"mode": "standard", "material": "Inconel 718", "power_W": 123,
                         "speed_mm_s": 125, "beamDiameter_um": 74, "preheat_C": 37,
                         "layer_um": 37, "hatch_um": 91, "absorptivity": .37})
        self.assertEqual(thermal_si_inputs(p, m), {
            "preheat_K": 310.15, "layer_m": 37e-6, "speed_m_s": .125,
            "absorbed_power_W": 123*.37,
        })

    def test_supplied_material_revision_changes_with_source_and_is_unverified(self):
        supplied = supplied_snapshot("Inconel 718")
        for key in ("materialId", "provenanceClass", "materialIdentitySchemaVersion", "materialRevisionSha256",
                    "materialAuthority", "materialAuthorityRevisionSha256"):
            supplied.pop(key)
        supplied["source"] = "Unit-test source record"
        first = material("Inconel 718", supplied)
        repeated = material("IN718", supplied)
        changed = copy.deepcopy(supplied)
        changed["source"] = "Different unit-test source record"
        revised = material("Inconel 718", changed)
        self.assertEqual(first["materialId"], "in718")
        self.assertEqual(first["materialRevisionSha256"], repeated["materialRevisionSha256"])
        self.assertNotEqual(first["materialRevisionSha256"], revised["materialRevisionSha256"])
        self.assertEqual(first["provenanceClass"], "user-supplied-unverified")
        self.assertEqual(first["quality"], "user-supplied-unverified")
        self.assertNotIn("sourceValidityRange_K", first)

    def test_source_validity_range_is_separate_and_must_cover_model_table(self):
        supplied = supplied_snapshot("Inconel 718")
        for key in ("materialId", "provenanceClass", "materialIdentitySchemaVersion", "materialRevisionSha256",
                    "materialAuthority", "materialAuthorityRevisionSha256"):
            supplied.pop(key)
        supplied["source"] = "Bounded synthetic unit-test source"
        coverage = [supplied["table"][0][0], supplied["table"][-1][0]]
        supplied["sourceValidityRange_K"] = coverage
        accepted = material("Inconel 718", supplied)
        self.assertEqual(accepted["sourceValidityRange_K"], coverage)
        self.assertEqual(accepted["temperatureCoverage_K"], coverage)
        without_validity = copy.deepcopy(supplied)
        without_validity.pop("sourceValidityRange_K")
        self.assertNotEqual(accepted["materialRevisionSha256"],
                            material("Inconel 718", without_validity)["materialRevisionSha256"])

        for invalid in ([coverage[0] + 1, coverage[1]], [coverage[0], coverage[1] - 1],
                        [True, coverage[1]], [coverage[0], float("inf")], [coverage[0]]):
            bad = copy.deepcopy(supplied)
            bad["sourceValidityRange_K"] = invalid
            with self.subTest(validity=invalid), self.assertRaises(ValueError):
                material("Inconel 718", bad)

    def test_supplied_identity_is_rederived_but_authority_claims_are_rejected(self):
        canonical = supplied_snapshot("Inconel 718")
        for key in ("materialAuthority", "materialAuthorityRevisionSha256"):
            supplied = copy.deepcopy(canonical)
            for identity in ("materialId", "provenanceClass", "materialIdentitySchemaVersion", "materialRevisionSha256",
                             "materialAuthority", "materialAuthorityRevisionSha256"):
                supplied.pop(identity)
            supplied["source"] = "Unit-test source record"
            supplied[key] = canonical[key]
            with self.subTest(claim=key), self.assertRaisesRegex(ValueError, "Unknown material property fields"):
                material("Inconel 718", supplied)
        tolerated = copy.deepcopy(canonical)
        for identity in ("materialAuthority", "materialAuthorityRevisionSha256"):
            tolerated.pop(identity)
        tolerated["source"] = "Unit-test source record"
        tolerated["materialRevisionSha256"] = "0" * 64  # copied identity metadata must be recomputed, never trusted
        self.assertNotEqual(material("Inconel 718", tolerated)["materialRevisionSha256"], "0" * 64)

    def test_supplied_data_for_additional_alloy(self):
        # Synthetic table exercises schema only; explicitly marked synthetic source.
        supplied = supplied_snapshot("Inconel 718")
        for key in ("materialId", "provenanceClass", "materialIdentitySchemaVersion", "materialRevisionSha256",
                    "materialAuthority", "materialAuthorityRevisionSha256"):
            supplied.pop(key)
        supplied["source"] = "Synthetic unit-test table, NOT measured IN625 properties"
        p, m = validate({"material": "Inconel 625", "properties": supplied})
        self.assertEqual(m["name"], "Inconel 625")
        self.assertEqual(m["quality"], "user-supplied-unverified")
        bad = copy.deepcopy(supplied); bad["table"][1][2] = -5
        with self.assertRaises(ValueError): material("Inconel 625", bad)
        bad = copy.deepcopy(supplied); bad["table"][1][2] = True
        with self.assertRaises(ValueError): material("Inconel 625", bad)

    def test_enthalpy_latent_heat_and_inverse(self):
        m = material("Inconel 718"); t, h = enthalpy_table(m)
        self.assertTrue((np.diff(h) > 0).all())
        energy = np.interp(m["liquidus_K"], t, h)-np.interp(m["solidus_K"], t, h)
        self.assertGreater(energy, m["latentHeat_J_kg"])
        for temperature in (353.15, m["solidus_K"], m["liquidus_K"], 2000):
            self.assertAlmostEqual(float(np.interp(np.interp(temperature, t, h), h, t)), temperature, places=8)

    def test_energy_and_physical_bounds(self):
        p, m = validate(CASE); r = transient(p, m)
        self.assertLess(r["energyBalance"]["relativeError"], 1e-10)
        expected = p["power_W"]*m["absorptivity"]*(p["trackLength_um"]*1e-6)/(p["speed_mm_s"]*.001)
        self.assertAlmostEqual(r["energyBalance"]["input_J"], expected, places=10)
        self.assertLess(r["metrics"]["peakTemperature_K"], m["boiling_K"])
        self.assertGreater(r["metrics"]["volume_um3"], 0)
        self.assertIsNone(r["metrics"]["keyholeDepth_um"])
        self.assertIsNone(r["metrics"]["recoilPressure_Pa"])
        self.assertGreater(r["metrics"]["coolingRate_K_s"], 0)
        json.dumps(r, allow_nan=False)

    def test_boil_is_failure_not_clipping(self):
        p, m = validate({**CASE, "power_W": 1000})
        with self.assertRaisesRegex(ValueError, "validity") as raised:
            transient(p, m)
        message = str(raised.exception)
        self.assertIn("specific enthalpy", message)
        self.assertIn("J/kg", message)
        self.assertIn("cell=", message)
        self.assertIn("dt=", message)
        self.assertIn("source rate", message)
        self.assertIn("W/m³", message)

    def test_no_source_conservation_operator(self):
        # Zero power is used only internally to verify equilibrium, not accepted by public API.
        p, m = validate(CASE); p["power_W"] = 0
        r = transient(p, m)
        self.assertEqual(r["energyBalance"]["stored_J"], 0)
        self.assertAlmostEqual(r["metrics"]["peakTemperature_K"], p["preheat_C"]+273.15)

    def test_source_domain_truncation_is_rejected_by_shared_capture_gate(self):
        from lpbf_core_physics import integrated_source
        from lpbf_heat_source import MINIMUM_SOURCE_CAPTURE_FRACTION, require_source_capture
        dx = 40e-6
        axis = np.array([100e-6, 140e-6])
        z = np.array([-20e-6, 20e-6, 60e-6])
        segment = {"start": [0., 0.], "end": [0., 0.], "start_s": 0., "end_s": 1.}
        _, capture = integrated_source(axis, z, dx, segment, 0., 1e-6, 80e-6,
                                       40e-6, 80e-6, 10.)
        self.assertLess(capture, MINIMUM_SOURCE_CAPTURE_FRACTION)
        with self.assertRaisesRegex(ValueError, "Gaussian source capture .* below the 99% minimum"):
            require_source_capture(capture, MINIMUM_SOURCE_CAPTURE_FRACTION)

    def test_scan_rotation_and_dwell(self):
        p, _ = validate({"tracks": 2, "layers": 2, "layerRotation_deg": 90})
        scans, end = scan_segments(p)
        self.assertEqual(len(scans), 4)
        self.assertGreater(scans[1]["start_s"], scans[0]["end_s"])
        self.assertGreater(scans[0]["end"][0], scans[0]["start"][0])
        self.assertLess(scans[1]["end"][0], scans[1]["start"][0])
        self.assertAlmostEqual(scans[2]["end"][0], scans[2]["start"][0])

    def test_multiple_tracks_layers_energy(self):
        p, m = validate({**CASE, "power_W": 10, "tracks": 2, "layers": 2,
                         "hatch_um": 80, "dwell_s": .00002})
        r = transient(p, m)
        duration = p["trackLength_um"]*1e-6/(p["speed_mm_s"]*.001)*4
        self.assertAlmostEqual(r["energyBalance"]["input_J"], p["power_W"]*m["absorptivity"]*duration, places=9)
        self.assertLess(r["energyBalance"]["relativeError"], 1e-10)
        self.assertEqual(len(r["scanPath"]), 4)

    def test_final_time_roundoff_does_not_create_substep(self):
        p, m = validate({**CASE, "mesh_um": 20, "maxDt_s": 5e-8,
                         "layer_um": 40, "powderGridPolicy": "layer-conforming"})
        result = transient(p, m)
        self.assertGreater(result["discretization"]["minimumDt_s"], p["maxDt_s"] * 0.5)
        self.assertLess(result["energyBalance"]["relativeError"], 1e-10)

    def test_three_mesh_study_is_not_validation(self):
        r = run({**CASE, "power_W": 10, "study": "mesh"})
        self.assertEqual(len(r["convergenceStudy"]["results"]), 3)
        self.assertEqual(r["convergenceStudy"]["checks"]["width_um"]["status"], "inconclusive")
        self.assertEqual(r["convergenceStudy"]["protocol"], "layer-aligned-three-grid-cpu-reference-v2-celik-ratio")
        self.assertEqual(r["convergenceStudy"]["cellsPerLayer"], [1, 2, 3])
        self.assertEqual(r["settings"]["powderGridPolicy"], "layer-conforming")
        self.assertEqual(r["settings"]["backend"], "reference")
        self.assertEqual(r["validationStatus"], "unvalidated")

    def test_standard_reference_run_aligns_powder_surface_and_source(self):
        r = run({**CASE, "backend": "auto", "mesh_um": 25, "layer_um": 80,
                 "layers": 3, "power_W": 60})
        self.assertEqual(r["requestedBackend"], "auto")
        self.assertEqual(r["settings"]["backend"], "reference")
        self.assertEqual(r["settings"]["powderGridPolicy"], "layer-conforming")
        self.assertEqual(r["coreContract"]["modelId"],
                         "stationary-enthalpy-conduction-layer-conforming-v1")
        self.assertAlmostEqual(r["discretization"]["mesh_m"], 20e-6)
        diagnostics = r["numericalDiagnostics"]
        self.assertAlmostEqual(diagnostics["maximumSurfaceOffset_um"], 0.0, places=10)
        self.assertGreaterEqual(diagnostics["minimumCapturedSourceFraction"], .99)
        self.assertLess(r["energyBalance"]["relativeError"], 1e-10)

    def test_failed_fine_mesh_preserves_requested_result_and_fails_study_closed(self):
        progress = []

        def synthetic_level(p, material, report=None, artifact_dir=None):
            if p["mesh_um"] < 15:
                raise ValueError("Gaussian source capture 54.851% is below the 99% minimum")
            report(0., "trial started")
            report(1., "trial completed")
            mesh_m = p["mesh_um"]*1e-6
            return dict(metrics=dict(width_um=100., depth_um=40., volume_um3=100000.,
                                     length_um=180., peakTemperature_K=1800.),
                        discretization=dict(mesh_m=mesh_m, meanDt_s=1e-7))

        with patch("lpbf_simulation.transient", side_effect=synthetic_level), \
                patch("lpbf_simulation.enforce_thermal_balances"), \
                patch("lpbf_simulation.write_artifacts"), \
                patch("lpbf_simulation.build_core_contract", return_value={"modelId": "test"}):
            r = run({**CASE, "mesh_um": 20, "study": "mesh", "backend": "auto"},
                    report=lambda fraction, message: progress.append(fraction))

        study = r["convergenceStudy"]
        self.assertEqual(r["metrics"]["width_um"], 100.)
        self.assertEqual(study["status"], "failed")
        self.assertIsNone(study["spacings"][2])
        self.assertIsNone(study["results"][2])
        self.assertIn("54.851%", study["checks"]["width_um"]["reason"])
        self.assertEqual(study["checks"]["width_um"]["status"], "failed")
        self.assertEqual(r["requestedBackend"], "auto")
        self.assertEqual(r["settings"]["backend"], "reference")
        self.assertNotEqual(r["provenance"]["inputHash"], r["provenance"]["executionInputHash"])
        self.assertEqual(progress, sorted(progress))

    def test_measurement_statistics(self):
        r = compare([110., 90.], [100., 100.])
        self.assertEqual(r["rmse_um"], 10)
        self.assertEqual(r["bias_um"], 0)
        self.assertAlmostEqual(r["calibrationFactor"], 20000/20200)
        self.assertIsNone(compare([0.], [100.])["calibrationFactor"])
        self.assertEqual(compare([0.], [100.])["errors_pct"], [-100.])
        for x in (-1, True, float("inf")):
            with self.assertRaises(ValueError): compare([x], [100.])

    def test_convergence_known_second_order(self):
        r = convergence([1.16, 1.04, 1.01], [.4, .2, .1])
        self.assertAlmostEqual(r["observedOrder"], 2)
        self.assertEqual(convergence([1, 1, 1], [4, 2, 1])["status"], "inconclusive")
        self.assertEqual(convergence([1, 2, 1], [4, 2, 1])["status"], "inconclusive")

    def test_fallback_is_honest(self):
        r = run({"mode": "high-fidelity"})
        self.assertEqual(r["label"], "Screening only")
        self.assertEqual(r["effectiveMode"], "screening")
        self.assertFalse(r["productionReady"])
        self.assertEqual(r["validationStatus"], "unvalidated")
        self.assertNotIn("thermalHistory", r)

    def test_cache_key_and_queue_cancel(self):
        from lpbf_simulation import implementation_fingerprint
        p, m = validate(CASE)
        self.assertEqual(fingerprint(p, m), fingerprint(dict(reversed(list(p.items()))), m))
        q = {**p, "maxDt_s": p["maxDt_s"]*.5}
        self.assertNotEqual(fingerprint(p, m), fingerprint(q, m))
        self.assertRegex(implementation_fingerprint(), r"^[0-9a-f]{64}$")
        test_root = Path(__file__).resolve().parents[1]/".lpbf-jobs"
        test_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=test_root) as tmp:
            queue = Queue(tmp, start=False)
            first = queue.submit(CASE); second = queue.submit(CASE)
            self.assertEqual(first["id"], second["id"]); self.assertTrue(second["deduplicated"]); self.assertFalse(second["cacheHit"])
            self.assertEqual(queue.cancel(first["id"])["status"], "cancelled")
            queue.finish_running(first["id"], status="timed_out", error="Racing timeout fixture")
            self.assertEqual(queue.get(first["id"])["status"], "cancelled")
            third = queue.submit(CASE); self.assertNotEqual(third["id"], first["id"])
            queue.update(third["id"], status="running")
            restarted = Queue(tmp, start=False)
            self.assertEqual(restarted.get(third["id"])["status"], "failed")

    def test_implementation_provenance_is_input_independent(self):
        first = run({"mode": "screening", "power_W": 20})
        second = run({"mode": "screening", "power_W": 30})
        self.assertNotEqual(first["provenance"]["inputHash"], second["provenance"]["inputHash"])
        self.assertEqual(first["provenance"]["implementationHash"],
                         second["provenance"]["implementationHash"])

    def test_nested_schema_and_measurement_evidence(self):
        from lpbf_evidence import PROCESS_KEYS
        p, _ = validate(CASE)
        row = dict(width_um=50., depth_um=45., source="Synthetic schema fixture")
        for patch in ({"measurements": {}}, {"measurements": [dict(row, width_um=True)]},
                      {"measurements": [dict(row, unknown=1)]}, {"emissivity": float("inf")}):
            with self.assertRaises(ValueError): validate({**CASE, **patch})
        vector = {k:p[k] for k in PROCESS_KEYS}
        matched = dict(row, processVector=vector, uncertainty_um=dict(width_um=2., depth_um=3.), independentHoldout=False)
        r = run({**CASE, "measurements": [matched]})
        self.assertEqual(r["measurementEvidence"][0]["sameProcessVector"], "matched")
        self.assertIsNotNone(r["measurementComparison"]["width_um"]["calibrationFactor"])
        unmatched = run({**CASE, "measurements": [row]})
        self.assertIsNone(unmatched["measurementComparison"]["width_um"]["calibrationFactor"])
        matched["processVector"]["power_W"] += 1
        with self.assertRaisesRegex(ValueError,"does not match"): validate({**CASE,"measurements":[matched]})

    def test_mass_and_phase_partition_with_deposition(self):
        p,m = validate({**CASE,"power_W":10,"layers":2,"layer_um":30,"mesh_um":20})
        r = transient(p,m)
        self.assertGreater(r["massBalance"]["deposited_kg"],0)
        self.assertLess(r["massBalance"]["relativeError"],1e-12)
        a = r["phaseAudit"]
        self.assertAlmostEqual((a["liquidVolume_m3"]+a["solidVolume_m3"])/a["activeVolume_m3"],1.)
        self.assertTrue(0 <= a["minFraction"] <= a["maxFraction"] <= 1)
        self.assertIsNone(a["interfaceConservation"])

    def test_artifact_manifest_and_corrupt_cache(self):
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            q = Queue(tmp,start=False)
            job = q.submit(CASE); folder = Path(tmp)/job["id"]
            r = run(CASE,artifact_dir=folder)
            self.assertTrue(any(a["path"] == "thermal-history.csv" for a in r["artifacts"]))
            for a in r["artifacts"]:
                self.assertEqual(hashlib.sha256((folder/a["path"]).read_bytes()).hexdigest(),a["sha256"])
            (folder/"result.json").write_text(json.dumps(r))
            q.update(job["id"],status="completed")
            self.assertTrue(q.submit(CASE)["cacheHit"])
            (folder/"thermal-history.csv").write_text("corrupted")
            self.assertNotEqual(q.submit(CASE)["id"],job["id"])

    def test_source_depth_independent_of_mesh(self):
        from lpbf_openfoam import generate_case
        for mesh in (20,40,60):
            p,m = validate({**CASE,"mesh_um":mesh,"layer_um":30})
            with tempfile.TemporaryDirectory() as tmp:
                generate_case(p,m,tmp)
                values = (Path(tmp)/"thermalInput.dat").read_text().splitlines()[0].split()
                self.assertAlmostEqual(float(values[8]),30e-6)

    def test_manufactured_conduction_second_order(self):
        from lpbf_simulation import conduction_rate
        errors = []
        for n in (12,24,48):
            dx = 1./n
            x,y,z = np.meshgrid(*[(np.arange(n)+.5)*dx]*3,indexing="ij")
            T = 300+np.sin(np.pi*x)*np.sin(np.pi*y)*np.sin(np.pi*z)
            rates = conduction_rate(T,np.full(T.shape,2.),np.ones(T.shape,bool),dx)
            exact = -6*np.pi**2*(T-300)
            errors.append(float(np.sqrt(np.mean((rates[1:-1,1:-1,1:-1]-exact[1:-1,1:-1,1:-1])**2))))
            self.assertLess(abs(float(rates.sum())),1e-8)
        self.assertGreater(errors[0]/errors[1],3.5)
        self.assertGreater(errors[1]/errors[2],3.5)

    def test_joint_conduction_rate_and_diagonal_reuse_face_operator(self):
        from lpbf_heat_source import conduction_diagonal
        from lpbf_simulation import conduction_rate, _conduction_rate_and_diagonal

        rng = np.random.default_rng(20260927)
        shape = (17, 13, 11)
        temperature = rng.uniform(300.0, 2600.0, shape)
        conductivity = rng.uniform(8.0, 42.0, shape)
        active = rng.random(shape) > 0.18
        dx = 7.5e-6

        expected_rate = conduction_rate(temperature, conductivity, active, dx)
        expected_diagonal = conduction_diagonal(conductivity, active, dx)
        actual_rate, actual_diagonal = _conduction_rate_and_diagonal(
            temperature, conductivity, active, dx
        )

        np.testing.assert_array_equal(actual_rate, expected_rate)
        np.testing.assert_array_equal(actual_diagonal, expected_diagonal)
        self.assertLess(abs(float(np.sum(actual_rate))), 1e-6 * float(np.sum(np.abs(actual_rate))))

    def test_heterogeneous_conduction_operator_is_symmetric_and_flux_balanced(self):
        from lpbf_simulation import conduction_rate

        dx = 2.5e-4
        shape = (6, 5, 5)
        i, j, k_index = np.indices(shape)
        conductivity = np.where(i < 3, 12.0, 37.0) * (1.0 + 0.05 * j)
        active = k_index < 3
        rng = np.random.default_rng(20260924)
        left = rng.normal(size=shape) * active
        right = rng.normal(size=shape) * active
        left_rate = conduction_rate(left, conductivity, active, dx)
        right_rate = conduction_rate(right, conductivity, active, dx)

        # Harmonic face coupling must define a symmetric operator, even across
        # conductivity jumps, and internal faces must cancel globally.
        self.assertAlmostEqual(
            float(np.sum(left * right_rate)),
            float(np.sum(right * left_rate)),
            delta=1e-8 * max(1.0, abs(float(np.sum(left * right_rate)))),
        )
        left_flux_scale = float(np.sum(np.abs(left_rate)))
        right_flux_scale = float(np.sum(np.abs(right_rate)))
        self.assertAlmostEqual(float(left_rate.sum()), 0.0, delta=1e-13 * left_flux_scale)
        self.assertAlmostEqual(float(right_rate.sum()), 0.0, delta=1e-13 * right_flux_scale)
        np.testing.assert_array_equal(left_rate[~active], 0.0)

        # Assemble the production half-cell isothermal base and the single
        # convective-radiative top-plane sink, then check the volume-integrated
        # power equals the external boundary power exactly.
        temperature = 300.0 + 20.0 * i + 8.0 * j + 15.0 * k_index
        reference_K = 300.0
        emissivity = 0.35
        convection_W_m2K = 18.0
        sigma = 5.670374419e-8
        rate = conduction_rate(temperature, conductivity, active, dx)
        bottom = 2.0 * conductivity[:, :, 0] * (temperature[:, :, 0] - reference_K) / dx**2
        top_temperature = temperature[:, :, 2]
        top_loss = (
            convection_W_m2K * (top_temperature - reference_K)
            + emissivity * sigma * (top_temperature**4 - reference_K**4)
        ) / dx
        rate[:, :, 0] -= bottom
        rate[:, :, 2] -= top_loss
        cell_volume = dx**3
        boundary_power_W = (float(bottom.sum()) + float(top_loss.sum())) * cell_volume
        integrated_rate_W = float(rate.sum()) * cell_volume
        self.assertAlmostEqual(
            integrated_rate_W,
            -boundary_power_W,
            delta=1e-12 * max(abs(integrated_rate_W), abs(boundary_power_W)),
        )

    def test_heterogeneous_conduction_timestep_refinement_converges(self):
        from lpbf_simulation import conduction_rate

        dx = 2.5e-4
        shape = (6, 5, 5)
        i, j, k_index = np.indices(shape)
        conductivity = np.where(i < 3, 12.0, 37.0) * (1.0 + 0.05 * j)
        active = k_index < 3
        initial = 300.0 + 20.0 * i + 8.0 * j + 15.0 * k_index
        initial[~active] = 300.0
        capacity_J_m3K = 8.4e6
        reference_K = 300.0
        emissivity = 0.35
        convection_W_m2K = 18.0
        sigma = 5.670374419e-8

        def evolve(dt):
            temperature = initial.copy()
            for _ in range(round(0.004 / dt)):
                rate = conduction_rate(temperature, conductivity, active, dx)
                rate[:, :, 0] -= (
                    2.0 * conductivity[:, :, 0] * (temperature[:, :, 0] - reference_K) / dx**2
                )
                top_temperature = temperature[:, :, 2]
                rate[:, :, 2] -= (
                    convection_W_m2K * (top_temperature - reference_K)
                    + emissivity * sigma * (top_temperature**4 - reference_K**4)
                ) / dx
                temperature[active] += dt * rate[active] / capacity_J_m3K
            return temperature

        fine = evolve(0.004 / 128)
        coarse_error = float(np.linalg.norm((evolve(0.0005) - fine)[active]))
        refined_error = float(np.linalg.norm((evolve(0.00025) - fine)[active]))
        self.assertGreater(coarse_error, refined_error)
        self.assertGreater(coarse_error / refined_error, 1.7)

    def test_exact_latent_heat_integral(self):
        m = material("Inconel 718"); t,h = enthalpy_table(m)
        from lpbf_material_registry import property_at
        mask = (t>=m["solidus_K"]) & (t<=m["liquidus_K"])
        cp = property_at(m,t[mask],3)
        sensible = float(np.sum(np.diff(t[mask])*(cp[:-1]+cp[1:])/2))
        total = float(h[mask][-1]-h[mask][0])
        self.assertAlmostEqual(total-sensible,m["latentHeat_J_kg"],places=6)

    def test_stripe_and_island_timing(self):
        for strategy in ("stripe","island"):
            p,m = validate({**CASE,"strategy":strategy,"tracks":3,"layers":2,"islandSize_um":100,"scanAngle_deg":35})
            scans,end = scan_segments(p)
            length = sum(np.linalg.norm(np.array(s["end"])-s["start"]) for s in scans)
            self.assertAlmostEqual(length, p["trackLength_um"]*1e-6*6)
            for a,b in zip(scans,scans[1:]): self.assertAlmostEqual(b["start_s"]-a["end_s"],p["dwell_s"])
            self.assertAlmostEqual(end,length/(p["speed_mm_s"]*.001)+len(scans)*p["dwell_s"]+p["cooling_s"])
            self.assertEqual({s["track"] for s in scans},{0,1,2})
            if strategy == "island": self.assertEqual(len(scans),12)

    def test_unresolved_layer_rejected(self):
        p,m = validate({**CASE,"layer_um":30,"layers":2})
        aligned = transient(p,m)
        self.assertAlmostEqual(aligned["discretization"]["mesh_m"], 30e-6)
        self.assertAlmostEqual(aligned["numericalDiagnostics"]["maximumSurfaceOffset_um"], 0., places=10)
        legacy = dict(p)
        legacy.pop("powderGridPolicy")
        with self.assertRaisesRegex(ValueError,"each powder layer"):
            transient(legacy,m)

    @unittest.skipUnless(os.name != "nt" and capabilities()["openfoamThermal"], "Requires compiled OpenFOAM 14 worker")
    def test_openfoam_against_independent_reference(self):
        from lpbf_openfoam import thermal
        p, m = validate(CASE)
        a, b = transient(p, m), thermal(p, m)
        self.assertLess(b["energyBalance"]["relativeError"], 1e-10)
        for key in ("length_um", "width_um", "depth_um", "volume_um3"):
            self.assertAlmostEqual(a["metrics"][key]/b["metrics"][key], 1., places=8)
        self.assertLess(abs(a["metrics"]["peakTemperature_K"]-b["metrics"]["peakTemperature_K"])/a["metrics"]["peakTemperature_K"], .01)
        self.assertGreater(b["metrics"]["coolingRate_K_s"], 0)
        for key in ("thermalGradient_K_m", "solidificationRate_m_s", "coolingRate_K_s"):
            self.assertLess(abs(a["metrics"][key]/b["metrics"][key]-1), .01, key)
        # Misaligned layer surface previously applied radiative losses to multiple cell planes.
        p.update(power_W=10, tracks=2, layers=2, layer_um=45, dwell_s=.00002)
        multi = thermal(p, m)
        ref_multi = transient(p,m)
        self.assertLess(abs(multi["energyBalance"]["losses_J"]-ref_multi["energyBalance"]["losses_J"])/max(ref_multi["energyBalance"]["losses_J"],1e-12),.02)
        duration = p["trackLength_um"]*1e-6/(p["speed_mm_s"]*.001)*4
        self.assertAlmostEqual(multi["energyBalance"]["input_J"], p["power_W"]*m["absorptivity"]*duration, places=9)
        p.update(strategy="island",islandSize_um=100,tracks=2,layers=1,layer_um=40)
        island = thermal(p,m)
        reference = transient(p,m)
        self.assertAlmostEqual(island["energyBalance"]["input_J"],reference["energyBalance"]["input_J"],places=10)
        self.assertLess(abs(island["metrics"]["peakTemperature_K"]-reference["metrics"]["peakTemperature_K"])/reference["metrics"]["peakTemperature_K"],.02)


if __name__ == "__main__": unittest.main(verbosity=2)
