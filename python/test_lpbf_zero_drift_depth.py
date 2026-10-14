"""Zero-served-value-drift depth package (2026-10-07): depth-datum / spot provenance, the declared datum-sensitivity
column, the Gan Supplementary Data 1 ingestion flags and the Fabbro half-maximum-diameter diagnostic.

Self-contained: committed CSVs, committed provenance text and the (fingerprint-pinned) solver only; no network. Nothing
here may change a served value: the sensitivity column is reported next to the served prediction, and the Fabbro FWHM
depth is computed outside the frozen files and labelled "diagnostic, not served".
"""

import hashlib
import json
import math
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tools"))

import lpbf_dataset_comparison as cmp  # noqa: E402
import lpbf_keyhole_benchmark as kb  # noqa: E402
import lpbf_keyhole_literature as kl  # noqa: E402
import lpbf_public_datasets as pds  # noqa: E402

REPO = HERE.parent
RECORD = REPO / "docs" / "LPBF_KEYHOLE_BEAM_CONVENTION_2026-10-07.json"
ATTR = {"hofmann": REPO / "data" / "benchmark" / "hofmann-316l-2026" / "LICENSE-ATTRIBUTION.md",
        "totis": REPO / "data" / "benchmark" / "totis-ti64-2021" / "LICENSE-ATTRIBUTION.md"}


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class DatumProvenanceTests(unittest.TestCase):
    def test_data_files_keep_their_pins(self):
        self.assertEqual(_sha(pds.HOFMANN_TABLE), pds.HOFMANN_TABLE_SHA256)
        self.assertEqual(_sha(pds.TOTIS_TABLE), pds.TOTIS_TABLE_SHA256)
        self.assertEqual(pds.load_hofmann_316l()["provenance"]["fileSha256"], pds.HOFMANN_TABLE_SHA256)
        self.assertEqual(pds.load_totis_ti64()["provenance"]["fileSha256"], pds.TOTIS_TABLE_SHA256)

    def test_loader_provenance_states_datum_and_spot_definition(self):
        h = pds.load_hofmann_316l()["provenance"]
        t = pds.load_totis_ti64()["provenance"]
        self.assertEqual(h["depthDatum"], "substrate-surface (paper Fig. 2)")
        self.assertEqual(h["beamDefinition"], "not stated; 1/e2 assumed")
        self.assertEqual(t["depthDatum"], "printed-base top surface (paper Fig. 1/2b)")
        self.assertEqual(t["beamDefinition"], "1/e2 (stated)")
        self.assertIn("25 um powder layer", t["depthDatumNote"])
        self.assertTrue(any("Fig. 1 and Fig. 2(b)" in c for c in t["caveats"]))
        self.assertFalse(any("do not say" in c for c in t["caveats"]), "the unknown-datum caveat must be gone")

    def test_attribution_files_carry_the_settled_facts(self):
        hof = ATTR["hofmann"].read_text(encoding="utf-8")
        tot = ATTR["totis"].read_text(encoding="utf-8")
        for needle in ("original substrate surface", "Fig. 2", "1/e^2 remains an assumption", "50 um focus"):
            self.assertIn(needle, hof)
        for needle in ("top surface of the printed Ti-6Al-4V base", "Fig. 2(b)", "1/e^2 classical definition",
                       "25 um powder layer"):
            self.assertIn(needle, tot)


class DatumSensitivityColumnTests(unittest.TestCase):
    ROWS = [  # three inline Hofmann-like rows (bare, 30 um, 60 um) and one Totis row
        ("hofmann-316l-2026", 0.0), ("hofmann-316l-2026", 30.0), ("hofmann-316l-2026", 60.0), ("totis-ti64-2021", 25.0)]

    def test_phi_times_t_for_substrate_datum_powder_rows(self):
        got = [cmp.depth_datum_correction_um(ds, t) for ds, t in self.ROWS]
        self.assertIsNone(got[0])  # bare plate: datum is the surface
        self.assertEqual([g["depthDatumCorrection_um"] for g in got[1:]], [18.0, 36.0, 15.0])
        self.assertTrue(all(g["phi"] == 0.60 and g["servedDepthUnchanged"] for g in got[1:]))
        self.assertEqual(cmp.PACKING_PHI, 0.60)

    def test_wording_and_other_sources(self):
        g = cmp.depth_datum_correction_um("hofmann-316l-2026", 30.0)
        self.assertEqual(g["basis"], "geometric assumption (h_surface = φ·t); powder denudation not modelled")
        for ds in ("nist-amb2022-03", "ku-leuven-316l-ti64-2021", "lane-in625-amb2018-02", "cmu-ti64-st-2026"):
            self.assertIsNone(cmp.depth_datum_correction_um(ds, 30.0), ds)
        self.assertIsNone(cmp.depth_datum_correction_um("hofmann-316l-2026", None))

    def test_helper_is_pure_and_the_limit_text_reports_the_column(self):
        rows = [{"dataset": "totis-ti64-2021", "predictions": {"eagar-tsai": {"depth_um": 77.0}}}]
        before = json.dumps(rows, sort_keys=True)
        cmp.depth_datum_correction_um(rows[0]["dataset"], 25.0)
        self.assertEqual(json.dumps(rows, sort_keys=True), before)
        out_rows = [{"dataset": "totis-ti64-2021", "regime": {"label": "conduction"}}]
        stub = {k: {"all": {"n": 0}, "common": {"n": 0}} for k in cmp.KERNELS}
        text = " ".join(cmp.build_limits(out_rows, stub, {"path": "flat-plate", "absorptivity_by_material": {},
                                                          "pinned": True, "raytracerModulePresent": False,
                                                          "raytracerImportable": False,
                                                          "howPinned": "x", "note": "x"}))
        self.assertIn("depthDatumCorrection_um", text)
        self.assertIn("never applied to the served depth", text)


class GanData1Tests(unittest.TestCase):
    def test_71_rows_pinned_and_flagged_not_independent(self):
        self.assertEqual(_sha(kl.GAN_DATA1_TABLE), kl.GAN_DATA1_SHA256)
        self.assertEqual(kl.GAN_DATA1_XLSX_SHA256, "b52d9173eb3a63983dd87c56b2720abd419a200e9594b863218de13da6a7597a")
        d = kl.load_gan_data1_ti64()
        self.assertEqual(len(d["rows"]), 71)
        self.assertEqual(d["provenance"]["doi"], "10.1038/s41467-021-22704-0")
        self.assertIn("CC BY 4.0", d["provenance"]["license"])
        self.assertIs(d["provenance"]["independentOfCunningham2019"], False)
        self.assertTrue(all(r["independentOfCunningham2019"] is False and r["sameExperimentsAs"] == "cunningham-ti64-2019"
                            for r in d["rows"]))
        attr = (REPO / "data" / "benchmark" / "gan-keyhole-2021" / "LICENSE-ATTRIBUTION.md").read_text(encoding="utf-8")
        self.assertIn("CC BY 4.0", attr)
        self.assertIn("10.1038/s41467-021-22704-0", attr)
        self.assertIn("same experiments as Cunningham 2019", attr)


class FabbroFwhmDiagnosticTests(unittest.TestCase):
    def test_fwhm_constant(self):
        self.assertAlmostEqual(kb.FWHM_OVER_1E2, 0.58871, delta=1e-5)
        self.assertAlmostEqual(kb.FWHM_OVER_1E2, math.sqrt(math.log(2.0) / 2.0), places=12)
        self.assertEqual(kb.FABBRO_FWHM_LABEL, "diagnostic, not served")

    def test_nist_case_served_unchanged_and_fwhm_value(self):
        d = kb.fabbro_fwhm_diagnostic("Inconel 718", 285.0, 960.0, 67.0, 23.5)
        # P7b (2026-10-14): the leg scales with the authority A 0.32 / 0.38 (P1: 123.9 / 195.4).
        self.assertEqual(d["fabbroDepth_um"], 104.4)  # served value, bit-equal to the solver's keyholeModel
        self.assertAlmostEqual(d["fabbroDepthFwhm_um"], 164.6, delta=0.3)
        self.assertTrue(d["aspectRatioInScope"])
        self.assertEqual(d["label"], "diagnostic, not served")

    def test_served_value_equals_solver_output(self):
        import contextlib
        import io
        from lpbf_thermal_solver import calculate_meltpool_physics
        with contextlib.redirect_stdout(io.StringIO()):
            res = calculate_meltpool_physics("Ti-6Al-4V", 231.0, 400.0, 95.0, 20.0, 30.0, 100.0,
                                             heat_source="eagar-tsai", absorption_model="flat-plate")
        d = kb.fabbro_fwhm_diagnostic("Ti-6Al-4V", 231.0, 400.0, 95.0, 20.0)
        self.assertEqual(d["fabbroDepth_um"], res["keyholeModel"]["fabbroDepth_um"])
        # Cunningham row (Ti64 231 W / 400 mm/s / 95 um / 20 C): harness value 299.4 um within +-5 %
        # P7b (2026-10-14): 299.4 x 0.32 / 0.35 = 273.7 (the Ti-6Al-4V authority 0.32).
        self.assertAlmostEqual(d["fabbroDepthFwhm_um"], 273.7, delta=0.05 * 273.7)
        self.assertGreater(d["fabbroDepthFwhm_um"], d["fabbroDepth_um"])
        # the recorder is removed again: the solver binding is the original function
        from fabbro_keyhole import fabbro_keyhole_depth_m
        import lpbf_thermal_solver as solver
        self.assertIs(solver.fabbro_keyhole_depth_m, fabbro_keyhole_depth_m)

    def test_scope_flag_false_for_in718_conduction_case(self):
        d = kb.fabbro_fwhm_diagnostic("Inconel 718", 150.0, 1500.0, 80.0, 20.0)
        self.assertFalse(d["aspectRatioInScope"])
        self.assertEqual(d["fabbroDepth_um"], 0.0)


class CommittedBeamConventionRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(RECORD.read_text(encoding="utf-8"))

    def test_record_shape_and_honesty(self):
        self.assertEqual(self.doc["schema"], kb.BEAM_CONVENTION_SCHEMA)
        self.assertIs(self.doc["servedValuesChanged"], False)
        self.assertEqual(self.doc["label"], "diagnostic, not served")
        self.assertEqual({k: v["n"] for k, v in self.doc["sets"].items()},
                         {"cunningham95": 46, "cunningham140": 23, "zhaoBoundaryBare": 9, "zhaoBoundaryPowder": 11})
        self.assertEqual(len(self.doc["cases"]), 89)

    def test_headline_numbers_match_the_d3a_record(self):
        s = self.doc["sets"]["cunningham95"]
        self.assertAlmostEqual(s["servedFabbro"]["medianRatioPredOverMeas"], 0.62, delta=0.01)
        self.assertAlmostEqual(s["fabbroFwhmDiagnostic"]["medianRatioPredOverMeas"], 1.00, delta=0.01)
        self.assertAlmostEqual(s["servedFabbro"]["mape_pct"], 45.0, delta=1.0)
        self.assertAlmostEqual(s["fabbroFwhmDiagnostic"]["mape_pct"], 26.0, delta=1.0)

    def test_served_column_of_the_record_equals_the_committed_keyhole_benchmark(self):
        bench = json.loads((REPO / "docs" / "LPBF_KEYHOLE_BENCHMARK_2026-10-07_keyhole-regime.json")
                           .read_text(encoding="utf-8"))
        served = {c["rowId"]: c["kernels"]["eagar-tsai"]["fabbroDepth_um"] for c in bench["cases"]["cunningham"]}
        for c in self.doc["cases"]:
            if c["set"].startswith("cunningham"):
                self.assertEqual(c["fabbroDepth_um"], served[c["rowId"]], c["rowId"])


if __name__ == "__main__":
    unittest.main()
