"""Keyhole benchmark report v2 (docs/LPBF_KEYHOLE_BENCHMARK_2026-10-07_keyhole-regime.*): the committed report is
reproducible from the committed data and pins the headline numbers of both rule sets (legacy 15/30 and current 15/20).

Self-contained and fast: the index-only evaluation (no solver) is recomputed in full and compared with the committed
JSON; the .md and .view.json are regenerated from the committed JSON and compared byte-for-byte; three cases are
re-run through the frozen kernels when the implementation fingerprint matches the report (else skipped, with reason).
The depth tables must equal the schema-1 record (docs/LPBF_KEYHOLE_BENCHMARK_2026-10-07.json, kept): the bump changes
no depth.
"""

import json
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tools"))

import lpbf_keyhole_benchmark as kb  # noqa: E402
import lpbf_keyhole_literature as kl  # noqa: E402

REPORT = HERE.parent / "docs" / "LPBF_KEYHOLE_BENCHMARK_2026-10-07_keyhole-regime.json"
OLD_REPORT = HERE.parent / "docs" / "LPBF_KEYHOLE_BENCHMARK_2026-10-07.json"
# SOL-T (2026-10-16) moved the served 316L endpoints (1375 / 1400 -> 1385 / 1450 C). The 2026-10-07 record stays the
# historical record of the keyhole-regime bump and is reproduced at the pre-SOL-T 316L endpoints; the SOL-T record is
# reproduced at the served properties.
SOLT_REPORT = HERE.parent / "docs" / "LPBF_KEYHOLE_BENCHMARK_2026-10-16_solt.json"
PRE_SOLT_316L = {"solidus_C": 1375.0, "liquidus_C": 1400.0}


def _pre_solt_props(material, _served=kb.pds.screening_props):
    props = _served(material)
    return {**props, **PRE_SOLT_316L} if material == "316L Stainless Steel" else props
INDEX_KEYS = ("appIndex_dHhs", "appRegime", "appRegimeLegacy_15_30", "appPorosityRiskByIndex", "appPorosityRiskLegacy",
              "ganKe", "ganEta", "ganRegime", "ganKeyholeDepth_um", "huangProduct_betaYe", "huangProduct_betaAppFlat",
              "hannRegime")


class CommittedReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(REPORT.read_text(encoding="utf-8"))
        with mock.patch.object(kb.pds, "screening_props", _pre_solt_props):
            cls.idx = kb.evaluate(run_kernels=False)

    def test_schema_and_data_pins(self):
        self.assertEqual(self.doc["schema"], "lpbf-keyhole-benchmark-2")
        self.assertEqual(self.doc["schema"], kb.SCHEMA)
        self.assertEqual(self.doc["generatedAt"], "2026-10-07")
        for name, prov in self.doc["datasets"].items():
            self.assertEqual(prov["fileSha256"], kl.LOADERS[name]()["provenance"]["fileSha256"], name)
        self.assertEqual(self.doc["crossCheckDatasets"]["gan-keyhole-2021-supplementary-data1"]["fileSha256"],
                         kl.GAN_DATA1_SHA256)
        self.assertEqual(len(self.doc["cases"]["cunningham"]), 69)
        self.assertEqual(len(self.doc["cases"]["zhaoBoundary"]), 20)
        self.assertEqual(len(self.doc["cases"]["zhaoPores"]), 35)
        self.assertEqual((kb.LEGACY_TRANSITION, kb.LEGACY_KEYHOLE), (15.0, 30.0))
        self.assertEqual((kb.CURRENT_TRANSITION, kb.CURRENT_KEYHOLE), (15.0, 20.0))

    def test_index_evaluation_is_reproduced_exactly(self):
        for group in ("cunningham", "zhaoBoundary", "zhaoPores"):
            for a, b in zip(self.doc["cases"][group], self.idx["cases"][group]):
                self.assertEqual(a["rowId"], b["rowId"])
                for k in INDEX_KEYS:
                    self.assertEqual(a[k], b[k], (group, a["rowId"], k))
        for key in ("cunninghamLines", "zhaoPores", "zhaoBoundary", "hannRelationCheck", "heldOut", "ganData1Check"):
            self.assertEqual(self.doc[key], self.idx[key], key)
        # P7b (2026-10-14): king_conversion reads the index convention constant (absorptivity_index_IR 0.42, the value
        # the cut 20 was derived with) and lists the physical authority (0.30) next to it; every number of the committed
        # 2026-10-07 record reproduces, only the property listing carries the new key names.
        want = dict(self.doc["kingConversion"])
        got = dict(self.idx["kingConversion"])
        self.assertEqual(want.pop("app316lProperties")["absorptivity_IR"], 0.42)
        props = got.pop("app316lProperties")
        self.assertEqual((props["absorptivity_index_IR"], props["absorptivity_IR_physical_not_used"]), (0.42, 0.30))
        self.assertEqual(want, got)
        for k in ("legacy_15_30", "current", "ganKe_1.4_6", "hann_HvHs_12.34"):
            self.assertEqual(self.doc["confusion"][k], self.idx["confusion"][k], k)
        for name, block in self.idx["depth"].items():
            self.assertEqual(self.doc["depth"][name]["ganEq2"], block["ganEq2"], name)
            self.assertEqual(self.doc["depth"][name]["ganKeScaleToFitEq2"], block["ganKeScaleToFitEq2"], name)

    def test_cunningham_confusion_legacy_and_current(self):
        m = lambda rule: self.doc["confusion"][rule]["appIndex3Class"]  # noqa: E731
        self.assertEqual(m("legacy_15_30")["rowsAreReported_columnsArePredicted"],
                         {"conduction": {"conduction": 1, "transition": 0, "keyhole": 0},
                          "transition": {"conduction": 1, "transition": 3, "keyhole": 0},
                          "keyhole": {"conduction": 0, "transition": 15, "keyhole": 26}})
        self.assertEqual((m("legacy_15_30")["n"], m("legacy_15_30")["correct"], m("legacy_15_30")["accuracy"]),
                         (46, 30, 0.652))
        self.assertEqual(m("current")["rowsAreReported_columnsArePredicted"],
                         {"conduction": {"conduction": 1, "transition": 0, "keyhole": 0},
                          "transition": {"conduction": 1, "transition": 3, "keyhole": 0},
                          "keyhole": {"conduction": 0, "transition": 4, "keyhole": 37}})
        self.assertEqual((m("current")["n"], m("current")["correct"]), (46, 41))
        near = lambda rule: self.doc["confusion"][rule]["appIndex3ClassExcludingNearBoundary"]  # noqa: E731
        self.assertEqual((near("legacy_15_30")["correct"], near("legacy_15_30")["n"]), (30, 44))
        self.assertEqual((near("current")["correct"], near("current")["n"]), (41, 44))
        b = lambda rule: self.doc["confusion"][rule]["appIndexKeyholeOnly"]  # noqa: E731
        self.assertEqual((b("legacy_15_30")["correct"], b("current")["correct"]), (31, 42))
        self.assertEqual((b("legacy_15_30")["rowsAreReported_columnsArePredicted"]["keyhole"]["keyhole"],
                          b("current")["rowsAreReported_columnsArePredicted"]["keyhole"]["keyhole"]), (26, 37))

    def test_held_out_check(self):
        ho = self.doc["heldOut"]
        pairs = {"hofmann316l": (677, 511, 561), "totisTi64": (80, 69, 74), "laneIn625LegacyProps": (23, 13, 13),
                 "kuLeuven316l_spot37.5um_unverified": (44, 41, 43), "kuLeuven316l_spot75um_sensitivity": (44, 26, 34),
                 "kuLeuvenTi64_spot37.5um_unverified": (14, 14, 11), "kuLeuvenTi64_spot75um_sensitivity": (14, 3, 8)}
        for name, (n, leg, cur) in pairs.items():
            self.assertEqual((ho[name]["n"], ho[name]["legacy_15_30"]["correct"], ho[name]["current"]["correct"]),
                             (n, leg, cur), name)
        spots = {"50": (175, 132, 144), "80": (187, 137, 148), "110": (161, 122, 129), "140": (154, 120, 140)}
        for spot, (n, leg, cur) in spots.items():
            x = ho["hofmann316lBySpot_um"][spot]
            self.assertEqual((x["n"], x["legacy_15_30"]["correct"], x["current"]["correct"]), (n, leg, cur), spot)
        self.assertEqual(ho["hofmann316l"]["sensitivityAccuracy"],
                         {"15.0": 0.731, "17.5": 0.808, "18.0": 0.815, "20.0": 0.829, "22.0": 0.833, "25.0": 0.815,
                          "30.0": 0.755})
        self.assertEqual(ho["totisTi64"]["sensitivityAccuracy"],
                         {"15.0": 0.9, "17.5": 0.925, "18.0": 0.925, "20.0": 0.925, "22.0": 0.912, "25.0": 0.912,
                          "30.0": 0.863})
        self.assertEqual(ho["hofmann316l"]["current"]["keyholeModeRecall"], "306/335")

    def test_threshold_derivation_block(self):
        k = self.doc["kingConversion"]
        self.assertAlmostEqual(k["factorHKingOverHApp"], 1.351, delta=0.001)
        self.assertAlmostEqual(k["kingThresholdInAppUnits"]["mid"], 22.2, delta=0.05)
        self.assertAlmostEqual(k["kingThresholdInAppUnits"]["low"], 19.3, delta=0.06)
        self.assertAlmostEqual(k["kingThresholdInAppUnits"]["high"], 25.2, delta=0.06)
        self.assertFalse(k["intervalOverlap"]["empty"])
        self.assertTrue(k["chosenInsideBothIntervals"])
        self.assertEqual(k["chosenKeyholeThreshold"], 20.0)
        g = self.doc["ganData1Check"]
        self.assertEqual((g["matched"], g["unmatched"], g["ganRows"]), (69, 0, 71))
        self.assertEqual(g["digitizedMinusGan_um"], {"median": 0.797, "meanAbs": 2.486, "maxAbs": 20.42})

    def test_headline_numbers(self):
        f = self.doc["findings"]
        self.assertEqual(f["appIndexAtCunninghamRedLine"], {"n": 9, "min": 17.293, "median": 17.662, "max": 20.005})
        self.assertEqual(f["appIndexAtCunninghamBlueLine"], {"n": 9, "min": 12.962, "median": 13.922, "max": 16.928})
        self.assertEqual(f["appIndexAtZhaoBoundary"], {"n": 20, "min": 15.0, "median": 24.942, "max": 62.424})
        self.assertEqual(f["zhaoPoreCasesAppHigh"], "19/35")
        self.assertEqual(f["zhaoPoreCasesAppPossible"], "16/35")
        self.assertTrue(f["keyholeThresholdTooHighForTi64Legacy"])
        self.assertFalse(f["keyholeThresholdTooHighForTi64"])
        self.assertFalse(f["singleIndexThresholdFitsZhaoBoundary"])
        self.assertTrue(f["publicDatasetsConstantsEqualSolver"])
        self.assertTrue(f["solverIndexEqualsProcessMapIndex"])
        self.assertTrue(f["solverPorosityRiskEqualsIndexBands"])
        self.assertTrue(f["solverRegimeFamilyEqualsIndexRegime"])
        pores = self.doc["zhaoPores"]["all"]
        self.assertEqual((pores["appHigh_dHhs_ge_30"], pores["appPossible_15_30"], pores["appNegligible_lt_15"]),
                         (19, 16, 0))
        self.assertEqual(self.doc["depth"]["cunningham95"]["appFabbro"]["mape_pct"], 44.785)
        self.assertEqual(self.doc["hannRelationCheck"]["withinClaimed10pct"], 3)

    def test_depth_tables_equal_the_schema_1_record(self):
        old = json.loads(OLD_REPORT.read_text(encoding="utf-8"))
        self.assertEqual(old["schema"], "lpbf-keyhole-benchmark-1")
        for name, block in old["depth"].items():
            for key, stats in block.items():
                self.assertEqual(self.doc["depth"][name][key], stats, (name, key))
        self.assertEqual(old["zhaoBoundary"], self.doc["zhaoBoundary"])
        for key in ("n", "bias_um", "mae_um", "mape_pct", "medianRatioPredOverMeas"):
            self.assertEqual(self.doc["depth"]["cunningham95"]["appFabbro"][key],
                             old["depth"]["cunningham95"]["appFabbro"][key])

    def test_markdown_and_view_are_regenerated_byte_for_byte(self):
        md = REPORT.with_suffix(".md").read_text(encoding="utf-8")
        self.assertEqual(md, kb.to_markdown(self.doc))
        view = json.loads(REPORT.with_name(REPORT.stem + ".view.json").read_text(encoding="utf-8"))
        self.assertEqual(view, json.loads(json.dumps(kb.view(self.doc))))
        self.assertTrue(view["readOnly"])
        self.assertIn("not experimental validation", view["honesty"])

    def test_three_cases_reproduce_through_the_frozen_kernels(self):
        from lpbf_simulation import implementation_fingerprint
        if implementation_fingerprint() != self.doc["implementationHash"]:
            self.skipTest("frozen LPBF implementation changed since the report; regenerate it with "
                          "tools/lpbf_keyhole_benchmark.py (kernel spot-check skipped, index checks still ran)")
        cases = [self.doc["cases"]["cunningham"][0], self.doc["cases"]["cunningham"][-1],
                 self.doc["cases"]["zhaoBoundary"][5]]
        for c in cases:
            got = json.loads(json.dumps(kb.kernel_block(c["power_W"], c["speed_mm_s"], c["beamDiameter_um"],
                                                        c["preheat_C"])))
            self.assertEqual(got, c["kernels"], c["rowId"])


class SolTReport(unittest.TestCase):
    """The SOL-T dated record reproduces the index-only evaluation at the served properties and its companions."""

    def test_index_evaluation_and_companions_reproduce(self):
        doc = json.loads(SOLT_REPORT.read_text(encoding="utf-8"))
        idx = kb.evaluate(run_kernels=False)
        self.assertEqual(doc["generatedAt"], "2026-10-16")
        for group in ("cunningham", "zhaoBoundary", "zhaoPores"):
            for a, b in zip(doc["cases"][group], idx["cases"][group]):
                for k in INDEX_KEYS:
                    self.assertEqual(a[k], b[k], (group, a["rowId"], k))
        for key in ("cunninghamLines", "zhaoPores", "zhaoBoundary", "hannRelationCheck", "heldOut", "ganData1Check",
                    "kingConversion"):
            self.assertEqual(doc[key], idx[key], key)
        with mock.patch.object(kb, "TITLE_TAG", "solt"), mock.patch.object(kb, "GENERATED_AT", "2026-10-16"):
            self.assertEqual(SOLT_REPORT.with_suffix(".md").read_text(encoding="utf-8"), kb.to_markdown(doc))
        view = json.loads(SOLT_REPORT.with_name(SOLT_REPORT.stem + ".view.json").read_text(encoding="utf-8"))
        self.assertEqual(view, json.loads(json.dumps(kb.view(doc))))
        self.assertEqual(doc["kingConversion"]["app316lProperties"]["liquidus_C"], 1450.0)


if __name__ == "__main__":
    unittest.main()
