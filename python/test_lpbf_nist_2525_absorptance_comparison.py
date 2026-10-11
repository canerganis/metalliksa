"""Tests for tools/lpbf_nist_2525_absorptance_comparison.py.

Run from python/:  python -B test_lpbf_nist_2525_absorptance_comparison.py
"""
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

PYTHON_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PYTHON_DIR))
sys.path.insert(0, str(PYTHON_DIR / "tools"))

import lpbf_nist_2525_absorptance_comparison as tool  # noqa: E402

_MISSING = object()
REQUIRED_TOP = {"schema", "generatedAt", "implementationFingerprint", "honesty", "dataset", "experiment", "measured",
                "measuredOnly", "models", "comparison", "labels", "limits", "checks"}


class ComparisonToolTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="nist2525-")
        cls.out = Path(cls.tmp) / "cmp.json"
        tool.main(["--quick", "--out", str(cls.out)])
        cls.doc = json.loads(cls.out.read_text(encoding="utf-8"))
        cls.rows = {r["id"]: r for r in cls.doc["comparison"]["rows"]}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_a_hash_gate_refuses_tampered_byte(self):
        root = Path(tempfile.mkdtemp(prefix="nist2525-tamper-"))
        try:
            for name in tool.PINNED:
                shutil.copy2(tool.SOURCE_DIR / name, root / name)
            tool.verify_inputs(root)  # untouched copy passes
            target = root / tool.AL_SPOT_AA
            data = bytearray(target.read_bytes())
            data[-2] ^= 0x01
            target.write_bytes(bytes(data))
            with self.assertRaises(ValueError):
                tool.verify_inputs(root)
            with self.assertRaises(ValueError):
                tool.build_document(True, "x", root)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_b_quick_record_shape_and_labels(self):
        self.assertTrue(REQUIRED_TOP <= set(self.doc))
        self.assertEqual(self.doc["schema"], "lpbf-nist-2525-absorptance-comparison-1")
        for r in self.doc["comparison"]["rows"]:
            self.assertIn(r["status"], tool.ALLOWED_STATUS)
            if r["status"] == "unavailable":
                self.assertTrue(r["reason"])
        self.assertEqual(self.doc["labels"], tool.LABELS)
        self.assertIs(self.doc["labels"]["nistResidual"], None)
        self.assertIs(self.doc["labels"]["experimentalValidation"], False)
        self.assertIs(self.doc["checks"]["inputHashesVerified"], True)
        self.assertIs(self.doc["checks"]["fingerprintCheckPassed"], True)
        self.assertNotIn("ray_paths", json.dumps(self.doc))
        md = self.out.with_suffix(".md").read_bytes()
        self.assertNotIn(b"\r", md)
        self.assertNotIn(b"\r", self.out.read_bytes())

    def test_c_flat_plate_difference(self):
        row = self.rows["ti64-spot-pre-keyhole-flat-plate"]
        self.assertEqual(row["status"], "compared")
        self.assertAlmostEqual(row["difference"], row["model"] - row["measured"], delta=1e-4)
        flat = self.doc["models"]["flatPlateAbsorptivity"]
        self.assertAlmostEqual(flat["difference_pp"], 100.0 * flat["value_fraction"] - flat["comparedWith"]["measuredMean_pct"], delta=1e-4)

    def test_d_depth_zero_matches_base(self):
        rt = self.doc["models"]["keyholeRayTracing"]
        self.assertEqual(rt["status"], "success")
        self.assertEqual(rt["sweep"][0]["keyhole_depth_um"], 0.0)
        self.assertLess(abs(rt["sweep"][0]["absorbed_fraction"] - rt["params"]["base_absorption"]), 0.02)
        self.assertEqual(len(rt["sweep"]), len(tool.DEPTHS_UM))

    def test_e_aluminium_rows_unavailable(self):
        al = [r for r in self.doc["comparison"]["rows"] if r["id"].startswith("al-")]
        self.assertGreaterEqual(len(al), 7)
        for r in al:
            self.assertEqual(r["status"], "unavailable")
            self.assertIn("SRM 1241c", r["reason"])
            self.assertIn("SRM 1241c", r["material"])
        self.assertIn("SRM 1241c", self.doc["measuredOnly"]["material"])

    def test_g_flat_plate_value_is_the_solver_resolution(self):
        """Call the solver itself with the powder-bed tracer pinned off; its eta_base must be the record value."""
        import contextlib
        import io
        authority = self.doc["models"]["flatPlateAbsorptivity"]["authority"]
        saved = sys.modules.get("powder_bed_raytracer", _MISSING)
        sys.modules["powder_bed_raytracer"] = None
        try:
            from lpbf_thermal_solver import calculate_meltpool_physics
            with contextlib.redirect_stdout(io.StringIO()):
                res = calculate_meltpool_physics("Ti-6Al-4V", 200.0, 700.0, 122.5, 20.0, 30.0, 100.0)
        finally:
            if saved is _MISSING:
                sys.modules.pop("powder_bed_raytracer", None)
            else:
                sys.modules["powder_bed_raytracer"] = saved
        self.assertAlmostEqual(res["processParameters"]["conductionAbsorptivity"],
                               authority["absorptivityOfRecord"], places=9)
        self.assertIn("powder_bed_raytracer", authority["solverRole"])
        self.assertEqual(self.rows["ti64-spot-pre-keyhole-flat-plate"]["modelId"], authority["origin"])
        self.assertEqual(self.doc["loaderUsed"], "lpbf_nist_mds2_2525_absorptance")
        self.assertIn("not recomputed", self.doc["measured"]["definition"])

    def test_h_single_compared_row_for_pre_keyhole_plateau(self):
        compared = [r for r in self.doc["comparison"]["rows"]
                    if r["status"] == "compared" and r["material"] == tool.TI64_MATERIAL
                    and r["quantity"].startswith("pre-keyhole")]
        self.assertEqual([r["id"] for r in compared], ["ti64-spot-pre-keyhole-flat-plate"])
        self.assertNotIn("ti64-spot-pre-keyhole-raytracer-flat", self.rows)
        self.assertIn("flatSelfConsistency", self.doc["models"]["keyholeRayTracing"])

    def test_i_energy_coupling_labelled_local(self):
        md = self.out.with_suffix(".md").read_text(encoding="utf-8")
        self.assertIn("Energy coupling, absorbed J / input J (derived locally", md)

    def test_j_present_scan_csv_is_verified_but_not_compared(self):
        loader = tool._load_loader()
        header = ",".join(loader.TI64_COLUMNS) + "\n"
        body = "".join(f"{i},{i * 4e-8:.8f},200,80,1.5,40,0,0,0\n" for i in range(5))
        fixture = (header + body).encode("utf-8")
        root = Path(tempfile.mkdtemp(prefix="nist2525-scan-"))
        entry = loader.ABSENT_FILES[tool.SCAN_NAME]
        saved = dict(entry)
        before = sys.modules.get("powder_bed_raytracer", _MISSING)
        try:
            (root / tool.SCAN_NAME).write_bytes(fixture)
            entry["sha256"] = hashlib.sha256(fixture).hexdigest()
            entry["bytes"] = len(fixture)
            res = tool.thermal_solver_scan(loader, root)
            self.assertEqual(res["status"], "unavailable")
            self.assertIn("scan-specific analysis windows", res["reason"])
            self.assertEqual(res["verifiedSamples"], 5)
            self.assertNotIn("eta_eff", res)
            self.assertIs(sys.modules.get("powder_bed_raytracer", _MISSING), before)
            # a present file that fails the pin is refused, not downgraded to "unavailable"
            (root / tool.SCAN_NAME).write_bytes(fixture[:-2] + b"1\n")
            with self.assertRaises(ValueError):
                tool.thermal_solver_scan(loader, root)
        finally:
            entry.clear()
            entry.update(saved)
            shutil.rmtree(root, ignore_errors=True)

    def test_k_committed_record_matches_full_regeneration(self):
        """The committed docs JSON/MD must equal a fresh full (non-quick) run byte for byte (~10 s on CPU)."""
        try:
            import warp  # noqa: F401
        except Exception as exc:  # the committed record was produced with the ray tracer available
            self.skipTest(f"SKIPPED: warp not importable ({type(exc).__name__}); use the locked interpreter")
        docs = PYTHON_DIR.parent / "docs"
        # Current record (fingerprint cda80143, keyhole-regime bump; numbers equal the balling-screen record,
        # only the fingerprint differs); the earlier records are kept as history.
        # Current record: fingerprint c61ab6a8 (P1 sourced-physics bump, 2026-10-11; the ray tracer and the flat
        # absorptivity do not move, the eta_eff row is renamed "effective absorptivity (flat after P1)"). The earlier
        # records are history. This stem was stale (red) on main since the in625-regime bump.
        stem = "LPBF_NIST_2525_ABSORPTANCE_COMPARISON_2026-10-11_p1-sourced"
        doc = tool.build_document(False, "2026-10-11")
        fresh_json = json.dumps(doc, sort_keys=True, indent=1, ensure_ascii=False) + "\n"
        self.assertEqual((docs / f"{stem}.json").read_bytes().replace(b"\r\n", b"\n"),
                         fresh_json.encode("utf-8"))
        self.assertEqual((docs / f"{stem}.md").read_bytes().replace(b"\r\n", b"\n"),
                         tool.render_markdown(doc).encode("utf-8"))

    def test_f_ti64_scan_unavailable_when_absent(self):
        if (tool.SOURCE_DIR / tool.SCAN_NAME).is_file():
            self.skipTest("scan CSV is present; branch exercised instead")
        row = self.rows["ti64-scan-before-during-keyhole"]
        self.assertEqual(row["status"], "unavailable")
        self.assertIn("not acquired", row["reason"])
        self.assertEqual(self.doc["models"]["thermalSolverEtaEff"]["ti64Scan"]["status"], "unavailable")
        self.assertEqual(self.doc["models"]["thermalSolverEtaEff"]["ti64Spot"]["status"], "unavailable")


if __name__ == "__main__":
    unittest.main()
