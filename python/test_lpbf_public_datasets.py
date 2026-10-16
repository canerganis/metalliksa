"""Tests for the public single-track dataset loaders, regime screen and comparison statistics.

No solver is run here (the comparison summary is exercised on a tiny synthetic prediction set).
"""

import json
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "tools"))

import lpbf_public_datasets as pds  # noqa: E402
import lpbf_dataset_comparison as cmp  # noqa: E402

COMMITTED_JSON = Path(__file__).resolve().parent.parent / "docs" / "LPBF_DATASET_COMPARISON_2026-10-05.json"


class LoaderTests(unittest.TestCase):
    def test_hofmann_rows_units_and_ranges(self):
        d = pds.load_hofmann_316l()
        rows = d["rows"]
        self.assertEqual(len(rows), 677)
        self.assertEqual(d["provenance"]["fileSha256"], pds.HOFMANN_TABLE_SHA256)
        self.assertEqual(d["provenance"]["doi"], "10.5281/zenodo.16979848")
        self.assertEqual(d["provenance"]["license"], "CC BY 4.0")
        self.assertTrue(all(r["material"] == "316L Stainless Steel" for r in rows))
        self.assertEqual({r["beamDiameter_um"] for r in rows}, {50.0, 80.0, 110.0, 140.0})
        self.assertEqual({r["layer_um"] for r in rows}, {0.0, 30.0, 60.0})
        self.assertTrue(all(50.0 <= r["power_W"] <= 500.0 for r in rows))
        self.assertTrue(all(225.0 <= r["speed_mm_s"] <= 1500.0 for r in rows))
        self.assertTrue(all(50.0 < r["width_um"] < 400.0 and 10.0 < r["depth_um"] < 600.0 for r in rows))
        self.assertEqual(sum(r["balling"] for r in rows), 216)
        self.assertEqual(len({r["rowId"] for r in rows}), 677)
        self.assertTrue(all(r["preheat_C"] == 20.0 for r in rows))
        self.assertEqual(rows[0]["rowId"], "hofmann-0001")
        self.assertEqual((rows[0]["power_W"], rows[0]["speed_mm_s"], rows[0]["width_um"]), (500.0, 900.0, 211.662))

    def test_totis_rows_units_and_ranges(self):
        d = pds.load_totis_ti64()
        rows = d["rows"]
        self.assertEqual(len(rows), 80)
        self.assertEqual(d["provenance"]["fileSha256"], pds.TOTIS_TABLE_SHA256)
        self.assertEqual(d["provenance"]["doi"], "10.17632/s9438vb5xd.1")
        self.assertTrue(all(r["material"] == "Ti-6Al-4V" and r["beamDiameter_um"] == 50.0
                            and r["layer_um"] == 25.0 for r in rows))
        self.assertEqual(sorted({r["power_W"] for r in rows}), [50.0 * i for i in range(1, 9)])
        self.assertEqual(sorted({r["speed_mm_s"] for r in rows}), [250.0 * i for i in range(1, 11)])
        self.assertTrue(all(r["width_um"] > 30 and r["depth_um"] > 3 for r in rows))
        cell = next(r for r in rows if r["power_W"] == 400 and r["speed_mm_s"] == 250)
        self.assertAlmostEqual(cell["depth_um"], 1076.27118644068, places=6)
        self.assertAlmostEqual(cell["width_um"], 242.017874875869, places=6)

    def test_material_keys_exist_in_authority(self):
        from four_alloy_materials import thermal_props
        for m in ("316L Stainless Steel", "Ti-6Al-4V"):
            self.assertIsNotNone(thermal_props(m))

    def test_non_committed_path_reports_its_own_digest(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / "meltpool_geometry.csv"
            bad.write_bytes(pds.HOFMANN_TABLE.read_bytes() + b"\n")
            # a non-committed path is not pinned, but the digest reported must differ
            d = pds.load_hofmann_316l(bad)
            self.assertNotEqual(d["provenance"]["fileSha256"], pds.HOFMANN_TABLE_SHA256)


class RegimeTests(unittest.TestCase):
    def test_hand_computed_enthalpy_and_labels(self):
        # 316L (rho 7990, k 16.3, cp 500, T_liq 1450 C since SOL-T, eta 0.42), 100 W, 1000 mm/s, d 50 um, T0 20 C:
        # alpha = 4.080e-6 m2/s; denom = rho cp 1430 sqrt(pi alpha v r^3); dH/hs = 17.02 x 1380 / 1430 = 16.43
        # (17.02 at the pre-SOL-T 1400 C).
        a = pds.classify_regime("316L Stainless Steel", 100, 1000, 50, 20.0, 0)
        self.assertAlmostEqual(a["normalizedEnthalpy"], 16.43, delta=0.02)
        self.assertEqual(a["label"], "transition")
        b = pds.classify_regime("Ti-6Al-4V", 50, 2500, 50, 20.0, None)
        self.assertLess(b["normalizedEnthalpy"], 15.0)
        self.assertEqual(b["label"], "conduction")
        c = pds.classify_regime("Ti-6Al-4V", 400, 250, 50, 20.0, None)
        self.assertGreater(c["normalizedEnthalpy"], 30.0)
        self.assertEqual(c["label"], "keyhole")

    def test_balling_flag_overrides(self):
        r = pds.classify_regime("316L Stainless Steel", 100, 1000, 50, 20.0, 1)
        self.assertEqual(r["label"], "balling-flagged")
        self.assertAlmostEqual(r["normalizedEnthalpy"], 16.43, delta=0.02)


class SummaryTests(unittest.TestCase):
    @staticmethod
    def _row(i, label, meas_w, meas_d, preds):
        return {"rowId": f"r{i}", "regime": {"label": label},
                "measured": {"width_um": meas_w, "depth_um": meas_d},
                "predictions": {"rosenthal": preds}}

    def test_synthetic_summary(self):
        ok = lambda w, d: {"width_um": w, "depth_um": d, "included": True}  # noqa: E731
        rows = [
            self._row(1, "conduction", 100.0, 50.0, ok(110.0, 40.0)),    # +10 %, -20 %
            self._row(2, "conduction", 100.0, 50.0, ok(70.0, 100.0)),    # -30 %, +100 %
            self._row(3, "conduction", 100.0, 50.0, {"width_um": 1.0, "depth_um": 1.0, "included": False}),
            self._row(4, "keyhole", 200.0, 300.0, ok(250.0, 100.0)),
        ]
        s = cmp.summarize(rows, kernels=("rosenthal",))["rosenthal"]
        c = s["conduction"]
        self.assertEqual((c["n"], c["nExcluded"]), (2, 1))
        self.assertAlmostEqual(c["width"]["bias_pct"], -10.0)
        self.assertAlmostEqual(c["width"]["mape_pct"], 20.0)
        self.assertAlmostEqual(c["width"]["rmse_um"], math.sqrt((100 + 900) / 2))
        self.assertEqual(c["width"]["within30pct"], 1.0)      # |-30 %| <= 30 %
        self.assertAlmostEqual(c["depth"]["bias_pct"], 40.0)
        self.assertEqual(c["depth"]["within30pct"], 0.5)  # -20 % in, +100 % out
        self.assertEqual(c["depth"]["withinFactor2"], 1.0)    # ratios 0.8 and 2.0 inside [0.5, 2]
        self.assertEqual((s["all"]["n"], s["all"]["nExcluded"]), (3, 1))
        self.assertEqual(s["keyhole"]["depth"]["withinFactor2"], 0.0)  # 100/300 < 0.5

    def test_empty_slot_has_null_stats(self):
        rows = [self._row(1, "conduction", 100.0, 50.0, {"width_um": None, "depth_um": None, "included": False})]
        s = cmp.summarize(rows, kernels=("rosenthal",))["rosenthal"]["conduction"]
        self.assertEqual((s["n"], s["nExcluded"], s["width"], s["depth"]), (0, 1, None, None))


class BootstrapAndCommonTests(unittest.TestCase):
    @staticmethod
    def _row(i, power, pw, pd_, included=True, kernels=("rosenthal", "goldak")):
        return {"rowId": f"r{i}", "dataset": "hofmann", "regime": {"label": "conduction"},
                "inputs": {"power_W": power, "speed_mm_s": 500.0, "beamDiameter_um": 80.0, "layer_um": 30.0},
                "measured": {"width_um": 100.0, "depth_um": 50.0},
                "predictions": {k: {"width_um": pw, "depth_um": pd_, "included": included} for k in kernels}}

    def _rows(self):
        # parameter sets: P=100 (two replicate rows), P=200, P=300 (one row excluded for goldak)
        rows = [self._row(1, 100.0, 110.0, 40.0), self._row(2, 100.0, 90.0, 60.0),
                self._row(3, 200.0, 130.0, 50.0), self._row(4, 300.0, 70.0, 55.0)]
        rows[3]["predictions"]["goldak"]["included"] = False
        return rows

    def test_set_key_groups_replicates(self):
        rows = self._rows()
        self.assertEqual(cmp._set_key(rows[0]), cmp._set_key(rows[1]))
        self.assertNotEqual(cmp._set_key(rows[0]), cmp._set_key(rows[2]))

    def test_bootstrap_is_deterministic_and_brackets_the_point_estimate(self):
        rows = self._rows()
        a = cmp.summarize(rows, kernels=("rosenthal",), with_ci=True)["rosenthal"]["all"]
        b = cmp.summarize(rows, kernels=("rosenthal",), with_ci=True)["rosenthal"]["all"]
        self.assertEqual(a, b)
        w = a["width"]
        self.assertEqual(w["n_parameterSets"], 3)
        lo, hi = w["bias_pct_ci95"]
        self.assertLessEqual(lo, w["bias_pct"] + 1e-9)
        self.assertGreaterEqual(hi, w["bias_pct"] - 1e-9)
        self.assertLessEqual(w["mape_pct_ci95"][0], w["mape_pct_ci95"][1])
        # per-set mean relative width errors are 0, +30 % and -30 %: any resample mean stays inside
        self.assertGreaterEqual(lo, -30.0 - 1e-9)
        self.assertLessEqual(hi, 30.0 + 1e-9)
        # one parameter set (two replicate rows, +10 % and -10 %) => degenerate interval at the point value
        one = cmp.summarize(rows[:2], kernels=("rosenthal",), with_ci=True)["rosenthal"]["all"]["width"]
        self.assertEqual(one["n_parameterSets"], 1)
        self.assertAlmostEqual(one["bias_pct_ci95"][0], 0.0)
        self.assertAlmostEqual(one["bias_pct_ci95"][1], 0.0)
        self.assertAlmostEqual(one["mape_pct_ci95"][0], 10.0)
        self.assertAlmostEqual(one["mape_pct_ci95"][1], 10.0)

    def test_without_ci_cells_keep_the_old_shape(self):
        w = cmp.summarize(self._rows(), kernels=("rosenthal",))["rosenthal"]["all"]["width"]
        self.assertNotIn("bias_pct_ci95", w)
        self.assertNotIn("n_parameterSets", w)

    def test_percentile_interpolates(self):
        self.assertEqual(cmp._percentile([0.0, 10.0], 50.0), 5.0)
        self.assertEqual(cmp._percentile([1.0, 2.0, 3.0], 100.0), 3.0)

    def test_common_cell_uses_rows_where_all_kernels_are_computed(self):
        rows = self._rows()
        s = cmp.summarize(rows, kernels=("rosenthal", "goldak"))
        cmp.add_common_cells(s, rows, kernels=("rosenthal", "goldak"), with_ci=True)
        for k in ("rosenthal", "goldak"):
            c = s[k]["common"]
            self.assertEqual((c["n"], c["nExcluded"]), (3, 1))
            self.assertEqual(c["width"]["n_parameterSets"], 2)
        self.assertEqual(s["rosenthal"]["all"]["n"], 4)
        self.assertEqual(s["goldak"]["all"]["n"], 3)


class AbsorptionPinTests(unittest.TestCase):
    def setUp(self):
        self._saved = sys.modules.get("powder_bed_raytracer", "absent")
        sys.modules.pop("powder_bed_raytracer", None)

    def tearDown(self):
        sys.modules.pop("powder_bed_raytracer", None)
        if self._saved != "absent":
            sys.modules["powder_bed_raytracer"] = self._saved

    def test_pin_blocks_the_raytracer_import_and_flag_unpins(self):
        cmp.pin_flat_plate(allow_raytracer=True)
        self.assertNotIn("powder_bed_raytracer", sys.modules)
        cmp.pin_flat_plate()
        self.assertIsNone(sys.modules["powder_bed_raytracer"])
        with self.assertRaises(ImportError):
            from powder_bed_raytracer import calculate_powder_bed_absorptivity  # noqa: F401

    def test_pinned_solver_call_takes_flat_plate_and_counts_it(self):
        row = {"material": "316L Stainless Steel", "power_W": 200.0, "speed_mm_s": 800.0,
               "beamDiameter_um": 80.0, "preheat_C": 20.0, "layer_um": 30.0, "hatch_um": 100.0}
        res = cmp._predict({"row": row, "kernel": "eagar-tsai"})
        self.assertEqual(res["_flatPlateCalls"], 1)  # result reports absorptionModel 'flat-plate'
        self.assertIsNotNone(res["width_um"])


class CommittedComparisonTests(unittest.TestCase):
    def test_committed_json_honesty_and_shape(self):
        self.assertTrue(COMMITTED_JSON.exists(), "run tools/lpbf_dataset_comparison.py first")
        doc = json.loads(COMMITTED_JSON.read_text(encoding="utf-8"))
        self.assertEqual(doc["schema"], "lpbf-dataset-comparison-1")
        self.assertIs(doc["honesty"]["experimentalValidation"], False)
        self.assertIn("not validation", doc["honesty"]["statement"])
        self.assertEqual(doc["kernels"], ["rosenthal", "eagar-tsai", "goldak"])
        expected_dataset_hashes = {
            pds.HOFMANN_TABLE_SHA256, pds.TOTIS_TABLE_SHA256,
            pds.CMU_ST_TABLE_SHA256, pds.CMU_MT_TABLE_SHA256, pds.KU_LEUVEN_TABLE_SHA256,
        }
        self.assertEqual({d["sha256"] for d in doc["datasets"]}, expected_dataset_hashes)
        by_id = {d["id"]: d for d in doc["datasets"]}
        self.assertEqual({key: by_id[key]["rows"] for key in (
            "cmu-ti64-st-2026", "cmu-ti64-mt-2026", "ku-leuven-in718-2021")},
            ({"cmu-ti64-st-2026": 0, "cmu-ti64-mt-2026": 40, "ku-leuven-in718-2021": 40}
             if doc["quick"] else
             {"cmu-ti64-st-2026": 216, "cmu-ti64-mt-2026": 410, "ku-leuven-in718-2021": 48}))
        if not doc["quick"]:
            self.assertEqual(len(doc["rows"]), 1431)
            self.assertEqual({d["id"] for d in doc["datasets"]}, {
                "hofmann-316l-2026", "totis-ti64-2021", "cmu-ti64-st-2026",
                "cmu-ti64-mt-2026", "ku-leuven-in718-2021"})
        for r in doc["rows"]:
            for k in doc["kernels"]:
                p = r["predictions"][k]
                self.assertEqual(p["included"], p["extentStatus"] == "computed")
        excluded_source_rows = [r for r in doc["rows"] if r["dataset"].startswith(("cmu-ti64-", "ku-leuven-"))]
        self.assertTrue(all(not r["predictions"][k]["included"]
                            for r in excluded_source_rows for k in doc["kernels"]))
        expected_source_rows = (("cmu-ti64-st-2026", 0), ("cmu-ti64-mt-2026", 40),
                                ("ku-leuven-in718-2021", 40)) if doc["quick"] else (
                                ("cmu-ti64-st-2026", 216), ("cmu-ti64-mt-2026", 410),
                                ("ku-leuven-in718-2021", 48))
        for dataset_id, count in expected_source_rows:
            self.assertEqual(sum(r["dataset"] == dataset_id for r in excluded_source_rows), count)
            for kernel in doc["kernels"]:
                cell = doc["breakdowns"]["byDataset"][dataset_id][kernel]["all"]
                self.assertEqual((cell["n"], cell["nExcluded"]), (0, count))
                self.assertIsNone(cell["width"])
                self.assertIsNone(cell["depth"])
        self.assertEqual(doc["absorptivitySensitivity"]["values"], [0.3, 0.4, 0.5, 0.6])
        ab = doc["absorption"]
        self.assertEqual((ab["path"], ab["pinned"]), ("flat-plate", True))
        self.assertEqual(ab["fallbackWarnings"], ab["solverCalls"])
        self.assertEqual(ab["absorptivity_by_material"], {"316L": 0.42, "Ti-6Al-4V": 0.35})
        self.assertGreaterEqual(len(doc["limits"]), 8)
        for k in doc["kernels"]:
            c = doc["summary"][k]["common"]
            self.assertEqual(c["n"] + c["nExcluded"], len(doc["rows"]))
            for regime, cell in doc["summary"][k].items():
                for q in ("width", "depth"):
                    if cell[q] is not None:
                        lo, hi = cell[q]["mape_pct_ci95"]
                        self.assertLessEqual(lo, hi, (k, regime, q))

    def test_view_record_is_the_record_minus_breakdowns_and_reference_rows(self):
        view_path = COMMITTED_JSON.with_suffix(".view.json")
        self.assertTrue(view_path.exists())
        doc = json.loads(COMMITTED_JSON.read_text(encoding="utf-8"))
        view = json.loads(view_path.read_text(encoding="utf-8"))
        self.assertNotIn("breakdowns", view)
        self.assertNotIn("rows", view["referenceTransient"])
        self.assertEqual(view["referenceTransient"]["counts"], doc["referenceTransient"]["counts"])
        for k in doc:
            if k not in ("breakdowns", "referenceTransient"):
                if k != "rows":
                    self.assertEqual(view[k], doc[k], k)
        compact_datasets = {"cmu-ti64-st-2026", "cmu-ti64-mt-2026", "ku-leuven-in718-2021"}
        compact_count = sum(row["dataset"] in compact_datasets for row in doc["rows"])
        self.assertEqual(len(view["rows"]), len(doc["rows"]) - compact_count)
        self.assertFalse(any(row["dataset"] in compact_datasets for row in view["rows"]))
        self.assertEqual(sum(item["count"] for item in view["predictionExclusions"]), compact_count)
        for row in view["rows"]:
            source = next(item for item in doc["rows"] if item["dataset"] == row["dataset"] and item["rowId"] == row["rowId"])
            self.assertEqual(row, source)


if __name__ == "__main__":
    unittest.main()
