"""Offline tests of the published-track error bands (python/lpbf_error_bands.py and tools/lpbf_error_bands.py).

Synthetic rows only: no dataset download, no solver run (the tool test injects a fake solver). The last class pins the
committed artefact to the numbers of the pre-declared exploratory evaluation. REPORTING ONLY; SCREENING ONLY; NOT
VALIDATION.
"""

import ast
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

PYTHON_DIR = Path(__file__).resolve().parent
REPO_ROOT = PYTHON_DIR.parent
sys.path.insert(0, str(PYTHON_DIR))  # not tools/: tools/lpbf_error_bands.py shares the loader's file name

import importlib.util  # noqa: E402

import lpbf_error_bands as eb  # noqa: E402

# tools/lpbf_error_bands.py shares its file name with the loader; load it under another module name
_spec = importlib.util.spec_from_file_location("lpbf_error_bands_tool", PYTHON_DIR / "tools" / "lpbf_error_bands.py")
T = importlib.util.module_from_spec(_spec)
sys.modules["lpbf_error_bands_tool"] = T
_spec.loader.exec_module(T)

FP = "f" * 64
REVISION = {"gitHead": "synthetic", "gitBranch": "synthetic", "dirtyTrackedPaths": 0, "python": "3"}
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "lpbf-error-band-sentences.json"


def solved_row(source, i, rel_depth, rel_width=0.0, material="316L Stainless Steel", enthalpy=17.0):
    meas_d, meas_w = 100.0 + i, 150.0 + i
    return {"source": source, "rowId": f"{source}-{i:03d}", "material": material, "power_W": 200.0 + i,
            "speed_mm_s": 900.0, "beamDiameter_um": 80.0, "preheat_C": 20.0, "layer_um": 0.0,
            "width_um": meas_w, "depth_um": meas_d, "balling": None, "enthalpy": enthalpy,
            "pred": {k: {"W": meas_w * (1 + rel_width), "D": meas_d * (1 + rel_depth), "status": "computed"}
                     for k in eb.KERNELS}}


def synthetic(offsets, n=10, spread=0.05, material="316L Stainless Steel", enthalpy=17.0):
    """{source: offset} -> rows whose relative depth error is offset + a deterministic spread of +-spread."""
    rows = []
    for source, off in offsets.items():
        for i in range(n):
            jitter = spread * (2.0 * i / (n - 1) - 1.0)
            rows.append(solved_row(source, i, off + jitter, material=material, enthalpy=enthalpy))
    return rows


def depth_cell(rows, kernel="eagar-tsai", family="316L", regime="transition"):
    res = eb.build_cells(rows)
    for c in res["cells"]:
        if (c["quantity"], c["kernel"], c["family"], c["regime"]) == ("depth", kernel, family, regime):
            return c
    raise AssertionError("cell not found")


class StatisticsTests(unittest.TestCase):
    def test_equal_source_weight_beats_row_count(self):  # 1
        rows = [solved_row("hofmann-316l-2026", i, 0.0) for i in range(10)]
        rows += [solved_row("trapp-316l-2017", i, 0.4) for i in range(30)]
        c = depth_cell(rows)
        # pooled (row-weighted) median is the large source's +0.4; equal source weight gives each source half the mass
        self.assertAlmostEqual(c["pooledMedian"], 0.4, places=5)
        self.assertAlmostEqual(c["median"], 0.0, places=5)
        per_src = {"hofmann-316l-2026": 10, "trapp-316l-2017": 30}
        weights = {s: n * (1.0 / n) for s, n in per_src.items()}
        self.assertEqual(weights["hofmann-316l-2026"], weights["trapp-316l-2017"])
        self.assertAlmostEqual(c["sourceMedian"]["trapp-316l-2017"], 0.4, places=5)
        self.assertAlmostEqual(c["sourceMedian"]["hofmann-316l-2026"], 0.0, places=5)

    def test_eligibility_keeps_n_and_sources(self):  # 2
        one_source = depth_cell(synthetic({"hofmann-316l-2026": 0.1}))
        nine_rows = depth_cell(synthetic({"hofmann-316l-2026": 0.1, "ku-leuven-316l-2021": 0.1}, n=5)[:9])
        two_row_source = depth_cell(synthetic({"hofmann-316l-2026": 0.1, "ku-leuven-316l-2021": 0.1}, n=10)[:12])
        for c, n, k in ((one_source, 10, 1), (nine_rows, 9, 2), (two_row_source, 12, 2)):
            self.assertFalse(c["eligible"])
            self.assertEqual(c["state"], "insufficient-data")
            self.assertEqual((c["n"], c["nSources"]), (n, k))
            self.assertTrue(c["sources"])
            self.assertIsNone(c["loso"])
        self.assertEqual(two_row_source["rowsPerSource"]["ku-leuven-316l-2021"], 2)

    def test_loso_coverage_and_state(self):  # 3
        shifted = depth_cell(synthetic({"hofmann-316l-2026": 0.0, "ku-leuven-316l-2021": 0.0, "trapp-316l-2017": 0.3}))
        cov = shifted["loso"]["coverageBySource"]
        self.assertEqual(cov["trapp-316l-2017"], 0.0)
        self.assertLess(shifted["loso"]["coverageEqualWeight"], 0.70)
        self.assertEqual(shifted["state"], "band-under-covers")
        same = depth_cell(synthetic({"hofmann-316l-2026": 0.1, "ku-leuven-316l-2021": 0.1, "trapp-316l-2017": 0.1}))
        self.assertGreaterEqual(same["loso"]["coverageEqualWeight"], 0.8)
        self.assertEqual(same["state"], "band")

    def test_widened_band_informative_and_sd_leak(self):  # 4
        wild = depth_cell(synthetic({"hofmann-316l-2026": -0.5, "ku-leuven-316l-2021": 0.6, "trapp-316l-2017": 0.0}))
        self.assertFalse(wild["widened"]["informative"])
        self.assertFalse(wild["widened"]["sdLeak"])
        tame = depth_cell(synthetic({"hofmann-316l-2026": 0.02, "ku-leuven-316l-2021": 0.0, "trapp-316l-2017": 0.01}))
        self.assertTrue(tame["widened"]["informative"])
        two = depth_cell(synthetic({"hofmann-316l-2026": 0.0, "ku-leuven-316l-2021": 0.3}))
        self.assertTrue(two["widened"]["sdLeak"])
        # a lower factor <= 0 (band reaching -100 % or below) can never be informative
        self.assertFalse(eb._informative(-1.2, 0.5))

    def test_regime_alloy_and_family_grouping(self):
        rows = synthetic({"lane-in625-2020": 0.0, "ghosh-in625-2018": 0.0}, material="Inconel 625", enthalpy=5.0)
        rows += synthetic({"nist-amb2022-03": 0.0}, material="Inconel 718", enthalpy=5.0)
        res = eb.build_cells(rows)
        keys = {(c["family"], c["regime"]) for c in res["cells"] if c["kernel"] == "eagar-tsai" and c["quantity"] == "depth"}
        self.assertIn(("Ni", "conduction"), keys)
        self.assertIn(("Inconel 718", "conduction"), keys)
        self.assertIn(("Ni", "all"), keys)
        ni = depth_cell(rows, family="Ni", regime="conduction")
        self.assertEqual(ni["alloys"], ["Inconel 625", "Inconel 718"])
        in718 = depth_cell(rows, family="Inconel 718", regime="conduction")
        self.assertTrue(in718["sentinelOnly"])
        self.assertEqual(eb.regime_class(14.99), "conduction")
        self.assertEqual(eb.regime_class(15.0), "transition")
        self.assertEqual(eb.regime_class(19.99), "transition")
        self.assertEqual(eb.regime_class(20.0), "keyhole")
        self.assertEqual(eb.regime_class(30.0), "keyhole")

    def test_unresolved_rows_are_excluded_and_counted(self):
        rows = synthetic({"hofmann-316l-2026": 0.0, "ku-leuven-316l-2021": 0.0})
        rows[0]["pred"]["goldak"]["status"] = "not-computed"
        res = eb.build_cells(rows)
        self.assertEqual(res["excluded"]["depth|goldak"], 1)
        self.assertEqual(res["excluded"]["width|goldak"], 1)
        self.assertNotIn("depth|eagar-tsai", res["excluded"])


def make_artefact(offsets=None):
    rows = synthetic(offsets or {"hofmann-316l-2026": 0.0, "ku-leuven-316l-2021": 0.0, "trapp-316l-2017": 0.3})
    prov = {s: {"doi": f"10.0/{s}", "tableSha256": "0" * 64} for s in {r["source"] for r in rows}}
    return rows, prov, T.build_artefact(rows, prov, impl_hash=FP, date="2026-10-07", revision=REVISION,
                                        tool_hash="1" * 64)


class LoaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows, cls.prov, cls.art = make_artefact()

    def write(self, art, name="bands.json"):
        p = Path(tempfile.mkdtemp()) / name
        p.write_text(T.dump_json(art), encoding="utf-8")
        return p

    def test_clean_artefact_loads(self):
        art = eb.load_bands(self.write(self.art), expected_impl_hash=FP)
        self.assertEqual(art["evidenceKind"], "screening-only")
        self.assertFalse(art["experimentalValidation"])
        self.assertEqual(art["labelPromotionProposed"], "none")

    def test_loader_refusals(self):  # 5
        unknown = copy.deepcopy(self.art)
        unknown["extra"] = 1
        with self.assertRaisesRegex(eb.BandsError, "unknown artefact keys"):
            eb.load_bands(self.write(unknown), expected_impl_hash=FP)
        edited = copy.deepcopy(self.art)
        edited["cells"][0]["median"] = 0.123
        with self.assertRaisesRegex(eb.BandsError, "contentSha256"):
            eb.load_bands(self.write(edited), expected_impl_hash=FP)
        drift = copy.deepcopy(self.art)
        drift["config"]["minRows"] = 3
        drift["contentSha256"] = eb.artefact_content_sha256(drift)
        with self.assertRaisesRegex(eb.BandsError, "configSha256"):
            eb.load_bands(self.write(drift), expected_impl_hash=FP)
        drift["configSha256"] = eb.canonical_sha256(drift["config"])
        drift["contentSha256"] = eb.artefact_content_sha256(drift)
        with self.assertRaisesRegex(eb.BandsError, "BANDS_CONFIG sha256 differs"):
            eb.load_bands(self.write(drift), expected_impl_hash=FP)
        promo = copy.deepcopy(self.art)
        promo["labelPromotionProposed"] = "Validated simulation"
        promo["contentSha256"] = eb.artefact_content_sha256(promo)
        with self.assertRaisesRegex(eb.BandsError, "screening-only"):
            eb.load_bands(self.write(promo), expected_impl_hash=FP)
        with self.assertRaises(eb.BandsStale):
            eb.load_bands(self.write(self.art), expected_impl_hash="a" * 64)
        with self.assertRaisesRegex(eb.BandsError, "missing"):
            eb.load_bands(Path(tempfile.mkdtemp()) / "nope.json", expected_impl_hash=FP)

    def test_stale_artefact_gives_available_false_without_exception(self):
        r = eb.load_bands_or_reason(self.write(self.art), expected_impl_hash="a" * 64)
        self.assertFalse(r["available"])
        self.assertTrue(r["stale"])
        r = eb.load_bands_or_reason(Path(tempfile.mkdtemp()) / "nope.json", expected_impl_hash=FP)
        self.assertFalse(r["available"])
        self.assertFalse(r["stale"])
        ok = eb.load_bands_or_reason(self.write(self.art), expected_impl_hash=FP)
        self.assertTrue(ok["available"])

    def test_band_for_uses_family_regime_and_quantity(self):
        c = eb.band_for(self.art, "eagar-tsai", "316L Stainless Steel", "transition", "depth")
        self.assertEqual((c["family"], c["regime"], c["quantity"]), ("316L", "transition", "depth"))
        self.assertIsNone(eb.band_for(self.art, "eagar-tsai", "AlSi10Mg", "transition", "depth"))
        self.assertIsNone(eb.band_for(self.art, "eagar-tsai", "316L Stainless Steel", "keyhole", "depth"))
        self.assertIsNone(eb.band_for(self.art, "rosenthal-x", "316L Stainless Steel", "transition", "depth"))


class SentenceTests(unittest.TestCase):
    def test_golden_sentences(self):  # 6
        fx = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(fx["labelLine"], eb.LABEL_LINE)
        self.assertEqual(eb.LABEL_LINE,
                         "Screening only · typical published-data error shown; transfer to another lab not established")
        seen = set()
        for case in fx["cases"]:
            got = eb.band_sentence(case["cell"], case["value_um"], case["quantity"], case.get("inputs"),
                                   material=case.get("material"))
            self.assertEqual(got, case["sentence"], case["name"])
            self.assertEqual(eb.band_short(case["cell"], case["quantity"]), case["short"], case["name"])
            seen.add(case["cell"]["state"] if case["cell"] else "missing")
        self.assertEqual(seen, {"band", "band-under-covers", "insufficient-data", "missing"})

    def test_every_sentence_keeps_the_honest_parts(self):
        fx = json.loads(FIXTURE.read_text(encoding="utf-8"))
        for case in fx["cases"]:
            s = case["sentence"]
            self.assertTrue(s.endswith(eb.LABEL_LINE), case["name"])
            self.assertIn("rows", s)
            self.assertIn("source", s)
            self.assertNotRegex(s, r"±")  # never a bare +/- x %
            if case["cell"] and case["cell"]["state"] != "insufficient-data":
                self.assertIn("held-out source fell inside", s)
                self.assertIn("per-source median", s)

    def test_rounding_is_half_up_and_signed(self):
        self.assertEqual(eb.fmt_pct(0.005), "+1")
        self.assertEqual(eb.fmt_pct(-0.005), "−1")
        self.assertEqual(eb.fmt_pct(0.0), "0")
        self.assertEqual(eb.fmt_pct(-0.2049), "−20")
        self.assertEqual(eb.fmt_cov(0.675), "68")
        self.assertEqual(eb._round_half_up(182.5), 183)


class ToolTests(unittest.TestCase):
    def test_check_reproduces_the_artefact_byte_for_byte(self):  # 7
        def fake(task):
            r = task["row"]
            f = {"eagar-tsai": 1.1, "goldak": 0.9, "rosenthal": 1.4}[task["kernel"]]
            return {"W": r["width_um"] * f, "D": r["depth_um"] * f, "status": "computed", "enthalpy": 17.0}

        inputs = []
        for src, mat in (("hofmann-316l-2026", "316L Stainless Steel"), ("ku-leuven-316l-2021", "316L Stainless Steel"),
                         ("trapp-316l-2017", "316L Stainless Steel")):
            for i in range(10):
                inputs.append({"dataset": src, "rowId": f"{src}-{i}", "material": mat, "power_W": 200.0 + i,
                               "speed_mm_s": 800.0, "beamDiameter_um": 80.0, "preheat_C": 20.0, "layer_um": 0.0,
                               "width_um": 150.0 + i, "depth_um": 100.0 + 2 * i, "balling": None})
        prov = {s: {"doi": f"10/{s}", "tableSha256": "2" * 64} for s in {r["dataset"] for r in inputs}}
        rows1 = T.solve_rows(inputs, solver=fake)
        rows2 = T.solve_rows(inputs, solver=fake)
        self.assertEqual(rows1, rows2)
        a1 = T.build_artefact(rows1, prov, impl_hash=FP, date="2026-10-07", revision=REVISION, tool_hash="1" * 64)
        a2 = T.build_artefact(rows2, prov, impl_hash=FP, date="2026-10-07", revision=REVISION, tool_hash="1" * 64)
        out1 = T.render_outputs(a1, T.rows_document(rows1, FP))
        out2 = T.render_outputs(a2, T.rows_document(rows2, FP))
        self.assertEqual(out1, out2)
        root = Path(tempfile.mkdtemp())
        T.write_outputs(root, out1)
        self.assertEqual(T.check_outputs(root, expected_impl_hash=FP), [])
        # the tool wrote every output in its canonical byte form (LF only)
        for rel in out1:
            self.assertNotIn(b"\r", (root / rel).read_bytes())
        # drift is detected: an edited row, a stale fingerprint, a hand-edited summary
        rows_path = root / eb.ROWS_REL_PATH
        doc = json.loads(rows_path.read_text(encoding="utf-8"))
        doc["rows"][0]["depth_um"] += 1.0
        rows_path.write_text(T.dump_rows(doc), encoding="utf-8")
        self.assertTrue(any("rowsSha256" in p for p in T.check_outputs(root, expected_impl_hash=FP)))
        T.write_outputs(root, out1)
        self.assertTrue(any("live fingerprint" in p for p in T.check_outputs(root, expected_impl_hash="a" * 64)))
        s_path = root / eb.SUMMARY_REL_PATH
        s = json.loads(s_path.read_text(encoding="utf-8"))
        s["cells"][0]["median"] = 0.5
        s_path.write_text(T.dump_json(s), encoding="utf-8")
        self.assertTrue(any("summary" in p for p in T.check_outputs(root, expected_impl_hash=FP)))

    def test_summary_drops_row_level_loso_bands_and_keeps_the_label(self):
        _rows, _prov, art = make_artefact()
        summary = eb.summary_of(art)
        self.assertEqual(summary["schema"], eb.SUMMARY_SCHEMA)
        self.assertEqual(summary["labelLine"], eb.LABEL_LINE)
        self.assertEqual(summary["evidenceKind"], "screening-only")
        for c in summary["cells"]:
            if c["loso"]:
                self.assertNotIn("bands", c["loso"])
        self.assertEqual(len(summary["cells"]), len(art["cells"]))


class FrozenGuardTests(unittest.TestCase):
    def test_no_frozen_file_imports_the_error_band_modules(self):  # 8
        import lpbf_simulation
        offenders = []
        for name in lpbf_simulation.IMPLEMENTATION_SOURCE_FILES:
            path = PYTHON_DIR / name
            if path.suffix != ".py" or not path.is_file():
                continue
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                mods = []
                if isinstance(node, ast.Import):
                    mods = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    mods = [node.module]
                if any(m.startswith("lpbf_error_bands") for m in mods):
                    offenders.append(name)
        self.assertEqual(offenders, [])
        self.assertNotIn("lpbf_error_bands.py", lpbf_simulation.IMPLEMENTATION_SOURCE_FILES)


class CommittedArtefactTests(unittest.TestCase):
    """The committed artefact equals the pre-declared exploratory numbers (scratchpad bands_results.json, rounded)."""

    @classmethod
    def setUpClass(cls):
        cls.art = eb.load_bands(REPO_ROOT / eb.ARTEFACT_REL_PATH)  # also fails when stale against the live fingerprint

    def cell(self, quantity, kernel, family, regime):
        for c in self.art["cells"]:
            if (c["quantity"], c["kernel"], c["family"], c["regime"]) == (quantity, kernel, family, regime):
                return c
        raise AssertionError((quantity, kernel, family, regime))

    def test_eagar_tsai_316l_depth_all(self):
        c = self.cell("depth", "eagar-tsai", "316L", "all")
        # P7b bands (2026-10-14, 36cd9d4a): the 316L authority 0.30 and the melting-point k / cp shrink every pool, so
        # the cell moves to a deeper underprediction (P1 values: n 731 / 432, median -0.20, p10 -0.43, p90 +0.41,
        # coverage 0.68, source medians +0.07 / -0.28 / -0.37); one Hofmann row leaves the computed set.
        self.assertEqual((c["n"], c["nSets"], c["nSources"]), (730, 431, 3))
        self.assertAlmostEqual(c["median"], -0.44, places=2)
        self.assertAlmostEqual(c["p10"], -0.61, places=2)
        self.assertAlmostEqual(c["p90"], -0.02, places=2)
        self.assertAlmostEqual(c["loso"]["coverageEqualWeight"], 0.65, places=2)
        self.assertEqual(c["state"], "band-under-covers")
        self.assertAlmostEqual(c["sourceMedian"]["hofmann-316l-2026"], -0.28, places=2)
        self.assertAlmostEqual(c["sourceMedian"]["ku-leuven-316l-2021"], -0.49, places=2)
        self.assertAlmostEqual(c["sourceMedian"]["trapp-316l-2017"], -0.55, places=2)

    def test_no_depth_cell_reaches_the_coverage_floor_and_five_width_cells_pass(self):
        # P7b bands (2026-10-14): one depth cell reaches the coverage floor (Eagar-Tsai 316L conduction, a descriptive
        # record at the new fingerprint, not evidence for the bump) and seven width cells pass (P1: none and five).
        depth_ok = sorted((c["kernel"], c["family"], c["regime"]) for c in self.art["cells"]
                          if c["quantity"] == "depth" and c["state"] == "band" and c["family"] in ("316L", "Ti64", "Ni"))
        self.assertEqual(depth_ok, [("eagar-tsai", "316L", "conduction")])
        width_ok = sorted((c["kernel"], c["family"], c["regime"]) for c in self.art["cells"]
                          if c["quantity"] == "width" and c["state"] == "band"
                          and c["family"] in ("316L", "Ti64", "Ni"))  # family cells; the per-alloy Ni views repeat them
        self.assertEqual(width_ok, [("eagar-tsai", "316L", "all"), ("eagar-tsai", "316L", "keyhole"),
                                    ("eagar-tsai", "Ni", "all"), ("goldak", "316L", "keyhole"), ("goldak", "Ni", "all"),
                                    ("rosenthal", "316L", "keyhole"), ("rosenthal", "Ni", "all")])

    def test_evidence_fields_and_sources(self):
        self.assertEqual(self.art["evidenceKind"], "screening-only")
        self.assertFalse(self.art["experimentalValidation"])
        names = {s["source"]: s for s in self.art["sources"]}
        self.assertTrue(names["nist-amb2022-03"]["sentinel"])
        self.assertTrue(names["trapp-316l-2017"]["digitized"])
        self.assertEqual(self.art["rowCount"], sum(s["rows"] for s in self.art["sources"]))


if __name__ == "__main__":
    unittest.main()
