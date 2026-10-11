"""Tests for tools/lpbf_nist_2716_thermography_comparison.py.

Self-contained: the measured input is the committed derived table
data/benchmark/nist-amb2022-03/derived/thermography-signal-metrics-v1.json (pinned by size and SHA-256 in the
tool and in derived/manifest.json); the 550 MB raw NIST file is not needed. Synthetic inputs are built in a
temporary directory by the helpers below (origin: this file).

Run from python/:  python -B test_lpbf_nist_2716_thermography_comparison.py
"""
import copy
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

PYTHON_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PYTHON_DIR))
sys.path.insert(0, str(PYTHON_DIR / "tools"))

import lpbf_nist_2716_thermography_comparison as tool  # noqa: E402

REQUIRED_TOP = {"schema", "generatedAt", "quick", "implementationFingerprint", "honesty", "dataset", "labels",
                "derivability", "measured", "modelInputs", "kernels", "model", "comparison", "limits", "checks"}


def _all_rows(doc):
    c = doc["comparison"]
    return c["trendRows"] + c["rankRows"] + c["unavailableRows"]


class ComparisonToolTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="nist2716-")
        cls.out = Path(cls.tmp) / "cmp.json"
        tool.main(["--quick", "--generated-at", "2026-10-06", "--out", str(cls.out)])
        cls.raw = cls.out.read_bytes()
        cls.doc = json.loads(cls.raw.decode("utf-8"))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_a_hash_gate_refuses_tampered_byte(self):
        root = Path(tempfile.mkdtemp(prefix="nist2716-tamper-"))
        try:
            for name in (tool.DERIVED_NAME, tool.MANIFEST_NAME):
                shutil.copy2(tool.DATA_DIR / name, root / name)
            tool.read_verified(root)  # untouched copy passes
            target = root / tool.DERIVED_NAME
            data = bytearray(target.read_bytes())
            data[-3] ^= 0x01
            target.write_bytes(bytes(data))
            with self.assertRaisesRegex(ValueError, "size or SHA-256 mismatch"):
                tool.read_verified(root)
            with self.assertRaises(ValueError):
                tool.build_document(True, "x", root, fingerprint_test=False)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_b_raw_input_pins_must_match_nerdm(self):
        root = Path(tempfile.mkdtemp(prefix="nist2716-pins-"))
        try:
            shutil.copy2(tool.DATA_DIR / tool.DERIVED_NAME, root / tool.DERIVED_NAME)
            manifest = json.loads((tool.DATA_DIR / tool.MANIFEST_NAME).read_text(encoding="utf-8"))
            manifest["inputs"][0]["sha256"] = "0" * 64
            (root / tool.MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "raw-input pins differ"):
                tool.read_verified(root)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_c_tool_pins_equal_committed_manifest(self):
        manifest = json.loads((tool.DATA_DIR / tool.MANIFEST_NAME).read_text(encoding="utf-8"))
        data = (tool.DATA_DIR / tool.DERIVED_NAME).read_bytes()
        self.assertEqual(tool.PINNED[tool.DERIVED_NAME], (hashlib.sha256(data).hexdigest(), len(data)))
        self.assertEqual((manifest["derived"]["sha256"], manifest["derived"]["bytes"]), tool.PINNED[tool.DERIVED_NAME])

    def test_d_record_shape_labels_and_statuses(self):
        self.assertTrue(REQUIRED_TOP <= set(self.doc))
        self.assertEqual(self.doc["schema"], "lpbf-nist-2716-thermography-comparison-1")
        self.assertEqual(self.doc["labels"], tool.LABELS)
        self.assertIs(self.doc["labels"]["experimentalValidation"], False)
        self.assertIs(self.doc["labels"]["opticalOperatorMatched"], False)
        self.assertIs(self.doc["labels"]["modelAcceptance"], False)
        self.assertIsNone(self.doc["labels"]["nistResidual"])
        self.assertIsNone(self.doc["labels"]["temperatureConversion"])
        self.assertEqual(self.doc["labels"]["appOutputs"], "screening, unvalidated")
        for r in _all_rows(self.doc):
            self.assertIn(r["status"], tool.ALLOWED_STATUS, r["id"])
            if r["status"] == "unavailable":
                self.assertTrue(r["reason"], r["id"])
        text = self.raw.decode("utf-8")
        self.assertNotIn('"compared"', text)
        self.assertNotIn('"experimentalValidation": true', text)
        self.assertNotIn(b"\r", self.raw)
        self.assertNotIn(b"\r", self.out.with_suffix(".md").read_bytes())

    def test_e_fingerprint_field_equals_expected(self):
        expected = (PYTHON_DIR / "lpbf_implementation_fingerprint.expected").read_text(encoding="utf-8").strip()
        self.assertEqual(self.doc["implementationFingerprint"], expected)
        # P6 containment bump pin (2026-10-11, 7870aae6 -> 807d74b3); the P1 pins were c61ab6a8 then 7870aae6.
        self.assertTrue(expected.startswith("807d74b3"))
        checks = {c["id"]: c for c in self.doc["checks"]}
        self.assertEqual(checks["A2-physics-fingerprint"]["result"], "skipped")  # --quick does not run the test
        self.assertIn("--quick", checks["A2-physics-fingerprint"]["detail"])

    def test_f_checks_computed(self):
        checks = {c["id"]: c["result"] for c in self.doc["checks"]}
        self.assertEqual(checks, {"A1-input-pins": "pass", "A2-physics-fingerprint": "skipped",
                                  "A9-no-temperature": "pass", "A10-labels": "pass", "A11-determinism": "pass",
                                  "A12-runtime": "pass"})

    def test_g_quick_kernels_and_missing_kernels_are_unavailable(self):
        self.assertEqual(self.doc["kernels"], ["eagar-tsai"])
        ids = {r["id"]: r for r in self.doc["comparison"]["unavailableRows"]}
        for k in ("rosenthal", "goldak"):
            self.assertEqual(ids[f"kernel-{k}"]["status"], "unavailable")
        for rid in ("absolute-length-or-dwell", "cooling-rate", "time-above-melting", "peak-temperature",
                    "transient-enthalpy-reference", "pads-vs-kernels", "radiance-temperature-bracket"):
            self.assertEqual(ids[rid]["status"], "unavailable")

    def test_h_trend_arithmetic_from_shown_inputs(self):
        cases = self.doc["measured"]["cases"]
        model = self.doc["model"]
        rows = [r for r in self.doc["comparison"]["trendRows"] if r["status"] == "sensitivity-only"]
        self.assertEqual(len(rows), 6 * len(tool.PAIRS))
        for r in rows:
            m, b = cases[r["caseId"]]["metrics"][r["measuredMetric"]], cases["0"]["metrics"][r["measuredMetric"]]
            self.assertAlmostEqual(r["measured"]["ratio"], m["mean"] / b["mean"], delta=1e-5)
            mk = r["models"]["eagar-tsai"]
            q = r["modelQuantity"]
            ratio = model[r["caseId"]]["eagar-tsai"][q] / model["0"]["eagar-tsai"][q]
            self.assertAlmostEqual(mk["ratio"], ratio, delta=1e-5)
            self.assertAlmostEqual(mk["ratioDifference"], mk["ratio"] - r["measured"]["ratio"], delta=1e-5)
            self.assertIs(mk["signAgreement"], (mk["ratio"] > 1) == (r["measured"]["ratio"] > 1)
                          if abs(mk["ratio"] - 1) > 1e-9 and abs(r["measured"]["ratio"] - 1) > 1e-9
                          else mk["signAgreement"])
            delta = abs(r["measured"]["ratio"] - 1)
            limit = max(r["measured"]["ratioSd"], r["measured"]["quantumRel"])
            if abs(delta - limit) > 1e-5:  # exactly one quantum is "not resolved"; the record is rounded to 6 digits
                self.assertIs(r["measured"]["changeResolved"], delta > limit, r["id"])
            else:
                self.assertIs(r["measured"]["changeResolved"], False, r["id"])

    def test_i_rank_rows(self):
        rows = self.doc["comparison"]["rankRows"]
        self.assertEqual(len(rows), len(tool.PAIRS))
        for r in rows:
            self.assertEqual(r["status"], "sensitivity-only")
            self.assertEqual(r["n"], 7)
            self.assertTrue(-1.0 <= r["spearmanRho"] <= 1.0)

    def test_j_determinism_with_generated_at(self):
        out2 = Path(self.tmp) / "cmp2.json"
        tool.main(["--quick", "--generated-at", "2026-10-06", "--out", str(out2)])
        self.assertEqual(out2.read_bytes(), self.raw)
        self.assertEqual(out2.with_suffix(".md").read_bytes(), self.out.with_suffix(".md").read_bytes())

    def test_k_committed_record_is_current(self):
        """The committed docs record equals a fresh full run (needs the fingerprint test; about 15 s)."""
        # The current record (fingerprint cda80143, keyhole-regime bump; numbers equal the balling-screen record,
        # only the fingerprint differs); the earlier records are kept as history.
        # Current record: fingerprint 807d74b3 (P6 containment bump, 2026-10-11; fingerprint only, every column equals
        # the P1 follow-on record because P6 moves no geometry, length or dwell). The earlier records are kept as
        # history.
        committed = PYTHON_DIR.parent / "docs" / "LPBF_NIST_2716_THERMOGRAPHY_COMPARISON_2026-10-11_p6-containment.json"
        doc = tool.build_document(False, "2026-10-11")
        self.assertEqual(tool.serialize(doc), committed.read_text(encoding="utf-8"))
        self.assertEqual(tool.render_markdown(doc), committed.with_suffix(".md").read_text(encoding="utf-8"))
        self.assertEqual(doc["kernels"], list(tool.KERNELS))
        self.assertEqual({c["id"]: c["result"] for c in doc["checks"]}["A2-physics-fingerprint"], "pass")


class SyntheticInputTest(unittest.TestCase):
    """Synthetic derived table (copy of the committed one with edited case means) under patched pins."""

    def _build(self, edit):
        root = Path(tempfile.mkdtemp(prefix="nist2716-syn-"))
        self.addCleanup(shutil.rmtree, root, True)
        rec = json.loads((tool.DATA_DIR / tool.DERIVED_NAME).read_text(encoding="utf-8"))
        edit(rec)
        data = (json.dumps(rec, sort_keys=True, indent=1) + "\n").encode("utf-8")
        (root / tool.DERIVED_NAME).write_bytes(data)
        manifest = json.loads((tool.DATA_DIR / tool.MANIFEST_NAME).read_text(encoding="utf-8"))
        sha = hashlib.sha256(data).hexdigest()
        manifest["derived"].update({"sha256": sha, "bytes": len(data)})
        (root / tool.MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")
        with mock.patch.dict(tool.PINNED, {tool.DERIVED_NAME: (sha, len(data))}):
            return tool.build_document(True, "syn", root, fingerprint_test=False)

    def test_missing_measured_metric_is_unavailable_with_reason(self):
        def edit(rec):
            for c in rec["cases"]:
                if c["caseId"] == "2.1":
                    c["metrics"]["tat1000_frames"] = None
        doc = self._build(edit)
        row = next(r for r in doc["comparison"]["trendRows"] if r["id"] == "trend-2.1-tat1000_frames")
        self.assertEqual(row["status"], "unavailable")
        self.assertIn("missing", row["reason"])
        rank = next(r for r in doc["comparison"]["rankRows"] if r["id"] == "rank-tat1000_frames-eagar-tsai")
        self.assertEqual(rank["status"], "unavailable")
        self.assertTrue(rank["reason"])

    def test_kernel_failure_is_unavailable_not_forced(self):
        real = tool.run_kernel

        def fake(case, kernel):
            if case["laserPower_W"] == 245.0:
                return tool.unavailable("kernel extentStatus 'no-melt': synthetic")
            return real(case, kernel)
        with mock.patch.object(tool, "run_kernel", side_effect=fake):
            doc = self._build(lambda rec: None)
        row = next(r for r in doc["comparison"]["trendRows"] if r["id"] == "trend-3.2-lsatTemporal_um")
        self.assertEqual(row["models"]["eagar-tsai"]["status"], "unavailable")
        self.assertIn("synthetic", row["models"]["eagar-tsai"]["reason"])
        self.assertTrue(all(r["status"] == "unavailable" for r in doc["comparison"]["rankRows"]))

    def test_planted_temperature_key_fails_a9(self):
        def edit(rec):
            for c in rec["cases"]:
                c["metrics"]["tat4095_frames"] = dict(c["metrics"]["tat4095_frames"], peak_C=1400.0)
        doc = self._build(edit)
        self.assertEqual({c["id"]: c["result"] for c in doc["checks"]}["A9-no-temperature"], "fail")


class SpearmanTest(unittest.TestCase):
    def test_known_values(self):
        self.assertAlmostEqual(tool.spearman([1, 2, 3, 4], [10, 20, 30, 40]), 1.0)
        self.assertAlmostEqual(tool.spearman([1, 2, 3, 4], [4, 3, 2, 1]), -1.0)
        # ties get average ranks: ranks x = 1,2,3,4; y = 1.5,1.5,3,4
        self.assertAlmostEqual(tool.spearman([1, 2, 3, 4], [5, 5, 6, 7]), 0.9486832980505138)
        self.assertIsNone(tool.spearman([1, 2], [1, 2]))
        self.assertIsNone(tool.spearman([1, 2, 3], [5, 5, 5]))

    def test_ranks(self):
        self.assertEqual(tool._ranks([3.0, 1.0, 3.0, 2.0]), [3.5, 1.0, 3.5, 2.0])
        self.assertEqual(copy.copy(tool._ranks([])), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
