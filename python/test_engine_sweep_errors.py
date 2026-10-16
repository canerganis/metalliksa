"""Self-contained admission regressions; no measured data, GPU or external files."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import lpbf_bayesian_optimizer as bayes
import lpbf_build_job_solver as build
import lpbf_machine_calibrated_meltpool as machine
import lpbf_worker as worker
import lpbf_worker_rpc as rpc
from stl_slicer_build_time_solver import solve_slicer, create_box_triangles


class SweepAdmissionTests(unittest.TestCase):
    def assert_refusal(self, result, code, field):
        self.assertFalse(result["success"])
        self.assertEqual(result["errorKind"], "validation")
        self.assertEqual(result["code"], code)
        self.assertEqual(result["field"], field)
        self.assertIsInstance(result["error"], str)
        self.assertTrue(result["error"])

    def test_slicer_never_reports_an_in625_mass_using_in718(self):
        for material in ("Inconel 625", "IN625", "unobtainium"):
            with self.subTest(material=material):
                result = solve_slicer({"material": material})
                self.assert_refusal(result, "UNSUPPORTED_SLICER_MATERIAL", "material")
                self.assertNotIn("meshMetrics", result)
                self.assertIn("Select", result["error"])

    def test_supported_slicer_materials_still_use_their_own_density(self):
        from four_alloy_materials import slicer_props
        for material in ("Ti-6Al-4V", "AlSi10Mg", "Inconel 718", "316L Stainless Steel"):
            result = solve_slicer({"material": material, "customTriangles": create_box_triangles(0, 0, 0, 10, 10, 10)})
            metrics = result["meshMetrics"]
            self.assertEqual(metrics["estimatedPartMass_g"], round(metrics["estimatedSolidVolume_cm3"] * slicer_props(material)["density_gcm3"], 1))

    def test_optimizer_unsupported_alloy_has_an_actionable_code(self):
        result = bayes._run_from_payload({"alloyId": "in625"})
        self.assert_refusal(result, "UNSUPPORTED_OPTIMIZER_ALLOY", "alloyId")
        self.assertIn("Select", result["error"])

    def test_build_job_unsupported_alloy_is_not_a_completed_job(self):
        result = build.solve_lpbf_build_job({"alloyId": "in625"})
        self.assert_refusal(result, "UNSUPPORTED_BUILD_JOB_ALLOY", "alloyId")
        with self.assertRaises(ValueError) as raised:
            worker.validate_build_job_request({"alloyId": "in625"})
        reply = worker.rpc_error_response({"id": 1}, raised.exception)
        self.assertEqual(reply["validation"]["error"]["code"], result["code"])
        with tempfile.TemporaryDirectory() as directory, patch.object(worker, "capabilities", return_value={}):
            queue = worker.Queue(root=directory, start=False)
            with self.assertRaises(ValueError):
                queue.submit({"jobType": "build-job", "alloyId": "in625"})
            with queue.connect() as db:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0], 0)
            queue.close()

    def test_machine_selection_is_explained_without_internal_id_syntax(self):
        result = machine.run({"material": "Inconel 718"})
        self.assert_refusal(result, "MACHINE_CALIBRATION_REQUIRED", "machineCalibration")
        self.assertIn("Select", result["error"])
        self.assertNotIn("GET /api", result["error"])

    def test_estimate_and_submit_validation_keep_missing_table_structured(self):
        for invoke in (lambda: rpc._estimate({"payload": {"material": "Inconel 625"}}),
                       lambda: worker.validate_thermal_request({"material": "Inconel 625"})):
            with self.assertRaises(ValueError) as raised:
                invoke()
            reply = worker.rpc_error_response({"id": 2}, raised.exception)
            env = reply["validation"]
            self.assertEqual(env["error"]["code"], "MISSING_THERMOPHYSICAL_TABLE")
            self.assertIn("Supply", env["error"]["message"])

    def test_real_boiling_stop_is_structured_at_the_unpinned_execution_boundary(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "input.json").write_text(json.dumps({"material": "Inconel 718", "power_W": 280,
                "speed_mm_s": 940, "preheat_C": 200, "mode": "standard", "backend": "reference"}))
            (root / "capabilities.json").write_text("{}")
            output = io.StringIO()
            with patch.object(worker.sys, "argv", ["worker", "--execute", folder]), contextlib.redirect_stdout(output):
                with self.assertRaises(SystemExit) as stopped:
                    worker.main()
            self.assertEqual(stopped.exception.code, 1)
            self.assertFalse((root / "result.json").exists())
        refused = worker._execution_refusal(output.getvalue())
        self.assertEqual(refused["code"], "THERMAL_BOILING_LIMIT")
        self.assertIn("Reduce laser power", refused["message"])
        self.assertIn("specific enthalpy", refused["detail"]["diagnostic"])
        self.assertIn("Last valid CPU state:", output.getvalue())

    def test_failed_job_exposes_structured_refusal_and_plain_message(self):
        from lpbf_request_errors import refusal_frame
        from lpbf_request_errors import LpbfRequestRefusal as ValidationError
        err = ValidationError("THERMAL_BOILING_LIMIT", "power_W", "Reduce laser power.", {"diagnostic": "raw"})
        log = "raw diagnostic\n" + refusal_frame(err) + "\nLast valid CPU state: example\n"
        self.assertEqual(worker._execution_failure_message(log, 1), "Reduce laser power.")
        self.assertEqual(worker._execution_refusal(log)["code"], "THERMAL_BOILING_LIMIT")
        self.assertIsNone(worker._execution_refusal('{"refusal":{"error":"malformed"}}'))
        self.assertIsNone(worker._execution_refusal('{"refusal":"malformed"}'))
        with tempfile.TemporaryDirectory() as directory, patch.object(worker, "capabilities", return_value={}):
            queue = worker.Queue(root=directory, start=False)
            job = "a" * 32
            folder = Path(directory) / job
            folder.mkdir()
            (folder / "input.json").write_text("{}")
            with queue.connect() as db:
                db.execute("INSERT INTO jobs VALUES (?,?,?,?,?,?,?)", (job, "key", "failed", .1, log, "raw", 0.))
            result = queue.get(job)
            queue.close()
        self.assertEqual(result["error"], "Reduce laser power.")
        self.assertEqual(result["refusal"]["code"], "THERMAL_BOILING_LIMIT")
        self.assertEqual(result["log"], log)


if __name__ == "__main__":
    unittest.main()
