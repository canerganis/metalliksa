"""Pins the honest labelling and the unit of the part porosity aggregator (a heuristic screening index)."""
import unittest

from lpbf_part_porosity_aggregator import aggregate_part_porosity

CLEAN = {"lackOfFusion": {"status": "adequate"}, "keyhole": {"risk": None}, "balling": {"risk": None}}


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

    def test_empty_input_errors(self):
        self.assertIn("error", aggregate_part_porosity([]))


if __name__ == "__main__":
    unittest.main()
