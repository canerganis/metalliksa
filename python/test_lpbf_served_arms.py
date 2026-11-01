"""Served arm of the user blind test: parity with the Build Job, closure pin, identity (spec 3.1, 3.6, 11.1 item 2).

Real solver, synthetic conditions only (no measured data).
"""
import ast
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import lpbf_served_arms as s

PY = Path(__file__).resolve().parent
REPO = PY.parent
CONDITIONS = ((150.0, 600.0, 70.0), (250.0, 900.0, 80.0), (350.0, 1300.0, 100.0))


class ServedParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from lpbf_build_job_solver import DEFAULT_PROCESS_SEED, solve_lpbf_build_job
        cls.solve = staticmethod(solve_lpbf_build_job)
        cls.seed = DEFAULT_PROCESS_SEED

    def test_defaults_match_the_build_job(self):
        from lpbf_build_job_schema import LpbfBuildJobRequest
        req = LpbfBuildJobRequest.model_validate({})
        self.assertEqual(self.seed, s.DEFAULT_PROCESS_SEED)
        self.assertEqual(req.hatchSpacing_um, s.BUILD_JOB_HATCH_UM)
        self.assertEqual(req.layerThickness_um, s.BUILD_JOB_LAYER_UM)

    def test_depth_width_extent_equal_build_job_for_three_conditions_per_alloy(self):
        for alloy in ("Ti-6Al-4V", "AlSi10Mg", "316L", "IN718"):
            for P, v, d in CONDITIONS:
                with self.subTest(alloy=alloy, P=P, v=v):
                    ref = self.solve({"alloyId": alloy, "laserPower_W": P, "scanSpeed_mm_s": v, "beamDiameter_um": d,
                                      "preheatTemp_C": 80.0, "bypassCache": True})
                    g = ref["thermal"]["meltPoolGeometry"]
                    arm = s.served_arm(alloy, P, v, d, 80.0)
                    self.assertEqual(arm["extentStatus"], g["extentStatus"])
                    if g["extentStatus"] == "computed":
                        self.assertEqual(arm["depth_um"], g["depth_um"])
                        self.assertEqual(arm["width_um"], g["width_um"])
                        self.assertEqual(arm["status"], "ok")
                    else:
                        self.assertEqual(arm["status"], "failed")
                    self.assertEqual(arm["buildJobIdentity"], ref["buildJobIdentity"]["sha256"])

    def test_process_map_flag_gives_identical_geometry(self):
        for alloy in ("Ti-6Al-4V", "AlSi10Mg"):
            for P, v, d in CONDITIONS:
                a = s.served_arm(alloy, P, v, d, 80.0, include_process_map=False)
                b = s.served_arm(alloy, P, v, d, 80.0, include_process_map=True)
                self.assertEqual((a["depth_um"], a["width_um"], a["extentStatus"]),
                                 (b["depth_um"], b["width_um"], b["extentStatus"]))

    def test_in625_direct_path_and_label(self):
        from lpbf_thermal_solver import calculate_meltpool_physics
        arm = s.served_arm("IN625", 195.0, 800.0, 100.0, 25.0)
        ref = calculate_meltpool_physics("Inconel 625", 195.0, 800.0, 100.0, 25.0, 40.0, 110.0, "IR_1064nm",
                                         process_seed=42)
        self.assertEqual(arm["depth_um"], ref["meltPoolGeometry"]["depth_um"])
        self.assertEqual(arm["materialEvidence"], "legacy-estimated-secondary")
        self.assertEqual(arm["reasonLabel"], "IN625_DIRECT_THERMAL_PATH")
        self.assertIsNone(arm["buildJobIdentity"])

    def test_index_is_the_unrounded_normalized_enthalpy(self):
        from lpbf_public_datasets import normalized_enthalpy
        arm = s.served_arm("Ti-6Al-4V", 250.0, 900.0, 80.0, 80.0)
        self.assertEqual(arm["index"], normalized_enthalpy("Ti-6Al-4V", 250.0, 900.0, 80.0, 80.0))

    def test_sensitivity_arms_perturb_power_and_beam_by_five_percent(self):
        arms = s.sensitivity_arms("Ti-6Al-4V", 250.0, 900.0, 80.0, 80.0)
        self.assertEqual(set(arms), {"served:P-5%", "served:P+5%", "served:d-5%", "served:d+5%"})
        self.assertEqual(arms["served:P+5%"]["depth_um"],
                         s.served_arm("Ti-6Al-4V", 250.0 * 1.05, 900.0, 80.0, 80.0)["depth_um"])
        self.assertEqual(arms["served:d-5%"]["depth_um"],
                         s.served_arm("Ti-6Al-4V", 250.0, 900.0, 80.0 * 0.95, 80.0)["depth_um"])

    def test_unknown_alloy_refused(self):
        with self.assertRaises(ValueError):
            s.served_arm("CuCrZr", 200.0, 800.0, 80.0, 80.0)


class ClosureAndPins(unittest.TestCase):
    def test_executed_closure_matches_the_pin_and_excludes_forbidden_modules(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("lpbf_user_blind_cli", PY / "tools" / "lpbf_user_blind.py")
        cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli)
        loaded = cli.loaded_served_modules()
        for bad in ("lpbf_build_job_solver.py", "lpbf_machine_calibrated_meltpool.py", "powder_bed_raytracer.py",
                    "warp_thermal_solver.py"):
            self.assertNotIn(bad, loaded)
        self.assertFalse([m for m in loaded if m.startswith("lpbf_research_")])
        from lpbf_simulation import IMPLEMENTATION_SOURCE_FILES
        pinned = {e["path"] for e in s.load_closure_pin()["files"]}
        outside = {f"python/{m}" for m in loaded if m not in IMPLEMENTATION_SOURCE_FILES}
        self.assertEqual(outside, pinned)

    def test_pin_matches_live_files_and_no_research_member(self):
        st = s.closure_status()
        self.assertEqual(st["mismatched"], [])
        self.assertFalse([f for f in st["files"] if "lpbf_research_" in f["path"]])

    def test_pin_hash_is_newline_independent(self):
        from lpbf_source_identity import canonical_source_bytes
        src = (PY / "lpbf_served_arms.py").read_bytes().replace(b"\r\n", b"\n")
        self.assertEqual(canonical_source_bytes("python/x.py", src),
                         canonical_source_bytes("python/x.py", src.replace(b"\n", b"\r\n")))

    def test_identity_carries_live_fingerprint_equal_to_pin(self):
        ident = s.predictor_identity("Ti-6Al-4V")
        self.assertEqual(ident["implementationFingerprint"], ident["pinnedFingerprint"])
        self.assertEqual(ident["research"], {"requested": False, "reasonCode": "RESEARCH_NOT_REQUESTED",
                                             "contract": "research/p8-research-arm 14e13ea8"})
        self.assertEqual(s.unpinned_reasons(ident), [])

    def test_one_byte_edit_of_a_closure_file_names_that_file(self):
        doc = s.load_closure_pin()
        tmp = Path(tempfile.mkdtemp())
        try:
            pin = tmp / "pin.json"
            entry = doc["files"][0]
            doc["files"][0] = {**entry, "sha256": "0" * 64}
            pin.write_text(json.dumps(doc))
            st = s.closure_status(pin)
            self.assertEqual(st["mismatched"], [entry["path"]])
        finally:
            shutil.rmtree(tmp)

    def test_manifest_untouched_and_not_imported_by_served_modules(self):
        from lpbf_simulation import IMPLEMENTATION_SOURCE_FILES
        self.assertNotIn("lpbf_served_arms.py", IMPLEMENTATION_SOURCE_FILES)
        for rel in IMPLEMENTATION_SOURCE_FILES:
            p = PY / rel
            if p.suffix != ".py" or not p.is_file():
                continue
            tree = ast.parse(p.read_bytes())
            names = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
            names |= {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
            self.assertFalse({x for x in names if x and x.startswith(("lpbf_user_blind", "lpbf_served_arms"))}, rel)

    def test_pin_check_command_is_current(self):
        out = subprocess.run([sys.executable, "-B", str(PY / "tools" / "lpbf_user_blind.py"), "pin-served-closure",
                              "--check"], capture_output=True, text=True, cwd=str(PY))
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        out = subprocess.run([sys.executable, "-B", str(PY / "tools" / "lpbf_user_blind.py"), "export-protocol",
                              "--check"], capture_output=True, text=True, cwd=str(PY))
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)


if __name__ == "__main__":
    unittest.main()
