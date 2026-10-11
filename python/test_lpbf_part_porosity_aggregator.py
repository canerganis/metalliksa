"""Pins the honest labelling and the unit of the part porosity aggregator (a heuristic screening index)."""
import unittest

from lpbf_defect_diagnostics import defect_diagnostics
from lpbf_part_porosity_aggregator import aggregate_part_porosity

CLEAN = {"lackOfFusion": {"status": "covered-geometrically", "riskScreened": False},
         "keyhole": {"risk": None}, "balling": {"risk": None}}


class Aggregator(unittest.TestCase):
    def test_clean_input_reports_only_the_prior_in_percent(self):
        agg = aggregate_part_porosity([CLEAN] * 3, powder_gas_prior_percent=0.01)
        idx = agg["screeningIndex"]
        self.assertAlmostEqual(idx["mean_percent"], 99.99, places=3)  # 0.01 % prior, not 1 %
        self.assertAlmostEqual(agg["porosity"]["mean_fraction"], 0.0001, places=6)
        self.assertEqual(idx["spread_lower_percent"], idx["spread_upper_percent"])

    def test_labels_and_keys(self):
        agg = aggregate_part_porosity([CLEAN, dict(CLEAN, balling={"risk": "high"})])
        idx = agg["screeningIndex"]
        self.assertIn("not a measured or predicted relative density", idx["label"])
        self.assertEqual(idx["evidenceLabel"], "Screening only")
        self.assertNotIn("relativeDensity", agg)
        self.assertNotIn("p05_percent", idx)
        self.assertNotIn("CI", idx["spreadBasis"].replace("confidence interval", ""))
        self.assertLessEqual(idx["spread_lower_percent"], idx["mean_percent"])
        self.assertGreaterEqual(idx["spread_upper_percent"], idx["mean_percent"])

    def test_confidence_is_not_high_for_many_samples(self):
        agg = aggregate_part_porosity([CLEAN] * 50)
        self.assertEqual(agg["confidence"], "unassessed")
        self.assertEqual(agg["sampleCount"], 50)

    def test_gas_prior_is_not_the_dominant_mechanism(self):
        self.assertEqual(aggregate_part_porosity([CLEAN] * 5)["dominantMechanism"], "none")
        self.assertEqual(aggregate_part_porosity([dict(CLEAN, balling={"risk": "high"})])["dominantMechanism"], "balling")

    def test_covered_pass_scores_above_tang_fail_with_real_diagnostics(self):
        # Real defect_diagnostics() output, not a hand-built status: W 150, D 80, hatch 90, layer 30 is covered
        # (Tang index 0.43); W 150, D 80, hatch 160, layer 30 fails the overlap screen (Tang index 1.28).
        covered = defect_diagnostics(150.0, 80.0, 400.0, 90.0, 30.0)
        failed = defect_diagnostics(150.0, 80.0, 400.0, 160.0, 30.0)
        self.assertIs(covered["lackOfFusion"]["riskScreened"], False)
        self.assertIs(failed["lackOfFusion"]["riskScreened"], True)
        pass_idx = aggregate_part_porosity([covered])["screeningIndex"]["mean_percent"]
        fail_idx = aggregate_part_porosity([failed])["screeningIndex"]["mean_percent"]
        self.assertAlmostEqual(pass_idx, 99.99, places=3)  # only the 0.01 % prior
        self.assertAlmostEqual(fail_idx, 94.99, places=3)  # prior plus the 5 % lack-of-fusion penalty
        self.assertGreater(pass_idx, fail_idx)
        self.assertEqual(aggregate_part_porosity([failed])["mechanismCounts"]["lackOfFusion"], 1)
        self.assertEqual(aggregate_part_porosity([covered])["mechanismCounts"]["lackOfFusion"], 0)

    def test_marginal_and_unresolved_overlap_are_not_full_penalties(self):
        marginal = dict(CLEAN, lackOfFusion={"status": "marginal", "riskScreened": None})  # shape of an index == 1.0 result
        agg = aggregate_part_porosity([marginal])
        self.assertAlmostEqual(agg["screeningIndex"]["mean_percent"], 100.0 - 0.01 - 2.5, places=3)
        self.assertEqual(agg["mechanismCounts"]["lackOfFusion"], 0)
        unresolved = defect_diagnostics(500, 200, 1000, 50, 20, aggregate=True)
        self.assertAlmostEqual(aggregate_part_porosity([unresolved])["screeningIndex"]["mean_percent"], 99.99, places=3)

    def test_zero_extent_counts_as_lack_of_fusion(self):
        agg = aggregate_part_porosity([defect_diagnostics(0.0, 0.0, 0.0, 90.0, 30.0)])
        self.assertEqual(agg["mechanismCounts"]["lackOfFusion"], 1)
        self.assertAlmostEqual(agg["screeningIndex"]["mean_percent"], 94.99, places=3)

    def test_no_keyhole_penalty_and_unsourced_label(self):
        agg = aggregate_part_porosity([dict(CLEAN, keyhole={"risk": "high"})])
        self.assertEqual(agg["mechanismCounts"]["keyhole"], 0)
        self.assertAlmostEqual(agg["screeningIndex"]["mean_percent"], 99.99, places=3)
        idx = agg["screeningIndex"]
        self.assertIn("nsourced", idx["label"])
        self.assertIn("unsourced", idx["basis"].lower())
        self.assertNotIn("keyhole 2 %", idx["basis"])

    def test_empty_input_errors(self):
        self.assertIn("error", aggregate_part_porosity([]))


if __name__ == "__main__":
    unittest.main()
