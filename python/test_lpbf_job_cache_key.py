#!/usr/bin/env python3
"""Self-contained tests that every Build Job request field that can change an output reaches the cache key.

Values are synthetic test scenarios (sizes, hardness, ratios, intervals), not alloy data."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import lpbf_job_cache as cache  # noqa: E402

# One distinct pair of admissible values per explicitly keyed field (each pair must give two different keys).
EXPLICIT_PAIRS = {
    "alloyId": ("ti6al4v", "alsi10mg"), "thermalMaterial": ("A", "B"), "slicerMaterial": ("A", "B"),
    "laserPower_W": (200.0, 201.0), "scanSpeed_mm_s": (900.0, 901.0), "scanSpeed_mms": (900.0, 901.0),
    "beamDiameter_um": (80.0, 81.0), "preheatTemp_C": (80.0, 81.0), "layerThickness_um": (40.0, 41.0),
    "hatchSpacing_um": (100.0, 101.0), "laserWavelength": ("IR_1064nm", "Green_532nm"), "preset": ("nozzle", "x"),
    "customTriangles": ([[[0, 0, 0], [1, 0, 0], [0, 1, 0]]], [[[0, 0, 0], [2, 0, 0], [0, 1, 0]]]),
    "cadAssetName": ("a", "b"), "maxTriangles": (100, 101),
    "recoatTimePerLayer_s": (9.0, 10.0), "processSeed": (42, 43), "seed": (1, 2), "scanStrategy": ("stripe", "island"),
    "stripeWidth_mm": (5.0, 6.0), "scanRotation_deg": (67.0, 90.0), "hatchDwell_ms": (0.0, 1.0),
    "inclineAngle_deg": (0.0, 10.0), "surfaceIncline_deg": (None, 10.0), "downskinOverhang_deg": (None, 45.0),
    "enableUq": (False, True), "uqSamples": (64, 96), "includeAmbench": (False, True),
    "defectSqrtAreas_um": ([40.0], [41.0]), "hardness_HV": (330.0, 331.0), "ctDetectionThreshold_um": (10.0, 11.0),
    "gitSha": ("a", "b"),
}
BASE = {"enableUq": True}  # uqSamples is keyed only when UQ is on


class CacheKeyCoverageTests(unittest.TestCase):
    def test_every_request_field_is_keyed_or_explicitly_non_semantic(self):
        names = set(cache.request_field_names())
        self.assertTrue(cache.EXPLICITLY_KEYED_FIELDS <= names, cache.EXPLICITLY_KEYED_FIELDS - names)
        self.assertTrue(cache.NON_SEMANTIC_FIELDS <= names)
        self.assertEqual(cache.NON_SEMANTIC_FIELDS, {"bypassCache"})
        # Every explicitly keyed field needs a test pair here, so a new explicit entry cannot go unchecked.
        self.assertEqual(set(EXPLICIT_PAIRS), set(cache.EXPLICITLY_KEYED_FIELDS))

    def test_explicit_fields_change_the_key(self):
        for name, (a, b) in EXPLICIT_PAIRS.items():
            with self.subTest(name):
                self.assertNotEqual(cache.build_cache_key({**BASE, name: a}), cache.build_cache_key({**BASE, name: b}))

    def test_every_other_request_field_changes_the_key(self):
        generic = cache.generically_keyed_fields()
        # Independent of the helper: a filter added inside generically_keyed_fields() must not drop a field.
        self.assertEqual(set(generic), set(cache.request_field_names()) - set(cache.EXPLICITLY_KEYED_FIELDS)
                         - {"bypassCache"})
        for name in ("defectSqrtArea_um", "defectEvidence", "defectLocation", "hardnessEvidence", "loadRatio",
                     "cycleTarget", "specimenOrientation", "defectIsLongCrack", "defectSampling",
                     "ctDetectionMethod", "kineticsCoolingInterval_C", "isothermalHold", "mechanicsScenario",
                     "defectSqrtAreasPaste"):
            self.assertIn(name, generic)
        for name in generic:
            with self.subTest(name):
                self.assertNotEqual(cache.build_cache_key({name: "A"}), cache.build_cache_key({name: "B"}))
                self.assertNotEqual(cache.build_cache_key({}), cache.build_cache_key({name: {"x": 1}}))

    def test_non_semantic_field_does_not_change_the_key(self):
        self.assertEqual(cache.build_cache_key({"bypassCache": True}), cache.build_cache_key({"bypassCache": False}))


class ScenarioCacheRegressionTests(unittest.TestCase):
    """Two requests differing in one scenario field, the second after a warm cache, must differ in their result."""

    COMMON = dict(alloyId="ti6al4v", laserPower_W=240, scanSpeed_mm_s=1200, beamDiameter_um=80, preheatTemp_C=150,
                  layerThickness_um=40, hatchSpacing_um=100, hardness_HV=330.0, hardnessEvidence="assumed-scenario",
                  defectSqrtArea_um=100.0, defectEvidence="assumed-scenario", defectLocation="internal")

    @classmethod
    def setUpClass(cls):
        from lpbf_build_job_solver import solve_lpbf_build_job
        cls.solve = staticmethod(solve_lpbf_build_job)
        cls.base = solve_lpbf_build_job(dict(cls.COMMON))  # warms the cache

    def test_base_value(self):
        self.assertAlmostEqual(self.base["murakami"]["fatigueLimit_MPa"], 1.56 * 450.0 / 100.0 ** (1 / 6), places=9)

    def test_murakami_scenario_fields_are_not_served_from_cache(self):
        for extra in ({"loadRatio": 0.1}, {"defectIsLongCrack": True}, {"defectLocation": "surface"},
                      {"defectSqrtArea_um": 1000.0}, {"cycleTarget": 1e8}, {"specimenOrientation": "vertical"},
                      {"defectEvidence": "measured"}, {"ctDetectionThreshold_um": 12.0}):
            with self.subTest(extra):
                out = self.solve({**self.COMMON, **extra})
                self.assertFalse(out["cache"]["hit"], extra)
                self.assertNotEqual(out["murakami"], self.base["murakami"], extra)
        # A field that does not change this output (no CT threshold to describe) is still keyed: a miss, not a hit.
        self.assertFalse(self.solve({**self.COMMON, "ctDetectionMethod": "POD"})["cache"]["hit"])
        refused = self.solve({**self.COMMON, "loadRatio": 0.1})["murakami"]
        self.assertIsNone(refused["fatigueLimit_MPa"])
        self.assertIsNone(self.solve({**self.COMMON, "defectIsLongCrack": True})["murakami"]["fatigueLimit_MPa"])

    def test_kinetics_and_mechanics_fields_are_not_served_from_cache(self):
        hold = self.solve({**self.COMMON, "isothermalHold": {"temperature_C": 500, "time_s": 3600}})
        self.assertFalse(hold["cache"]["hit"])
        self.assertAlmostEqual(hold["kinetics"]["estimates"]["quantities"]["tiMartensiteDissolution"]["value"], 0.72)
        interval = self.solve({**self.COMMON, "kineticsCoolingInterval_C": {"high_C": 900.0, "low_C": 400.0}})
        self.assertFalse(interval["cache"]["hit"])
        self.assertEqual(interval["kinetics"]["estimates"]["coolingInterval"]["high_C"], 900.0)
        bar = {"elasticModulus_GPa": 110.0, "elasticModulusEvidence": "assumed-scenario",
               "thermalExpansion_per_K": 9e-6, "thermalExpansionEvidence": "assumed-scenario",
               "returnYield_MPa": 900.0, "returnYieldEvidence": "assumed-scenario",
               "returnTemperature_C": 25.0, "peakTemperature_C": 900.0}
        mech = self.solve({**self.COMMON, "mechanicsScenario": {"bar": bar}})
        self.assertFalse(mech["cache"]["hit"])
        self.assertIsNotNone(mech["mechanicsScenarios"]["quantities"]["barStress"]["value"])

    def test_identical_request_still_hits(self):
        self.assertTrue(self.solve(dict(self.COMMON))["cache"]["hit"])


if __name__ == "__main__":
    unittest.main()
