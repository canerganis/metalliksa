#!/usr/bin/env python3
"""Self-contained tests of the group 7 Murakami block (SPEC_engine_estimates_2026-10-17 group 7, Amendment 1 A1.4/A1.5).

All sizes, hardnesses, volumes and probabilities below are synthetic test scenarios typed for this file, not alloy
data. The oracle is the printed law sigma_w = C (HV + 120) / s^(1/6) with C 1.43 / 1.56.
"""
import math
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import input_validation as iv  # noqa: E402
import murakami_fatigue_screening as ms  # noqa: E402
import quantity_envelope as qe  # noqa: E402

TIER2_SENTENCE = "Uncertainty is unknown and may be large. Calibrate to your machine for better accuracy."
SCENARIO = {"defectSqrtArea_um": 150.0, "defectEvidence": "assumed-scenario", "defectLocation": "internal",
            "hardnessEvidence": "assumed-scenario"}


def run(scenario=None, hv=330.0, alloy="ti6al4v", defects=None, ct=None):
    return ms.evaluate_murakami_block(defects, hardness_HV=hv, ct_detection_threshold_um=ct, alloy_id=alloy,
                                      scenario=scenario)


def oracle(c, hv, s):
    return c * (hv + 120.0) / s ** (1.0 / 6.0)


class NoDefaultsTests(unittest.TestCase):
    def test_module_has_no_hardness_defaults_or_fallback(self):
        self.assertFalse(hasattr(ms, "ALLOY_HV_DEFAULTS"))
        self.assertFalse(hasattr(ms, "resolve_hardness_HV"))
        source = Path(ms.__file__).read_text(encoding="utf-8")
        self.assertNotIn("350.0", source)
        self.assertNotIn("generic_fallback", source)

    def test_every_route_without_hardness_refuses(self):
        for alloy in ("ti6al4v", "alsi10mg", "in718", "ss316l", "in625", "unknown-alloy", None):
            out = run({**SCENARIO, "hardnessEvidence": None}, hv=None, alloy=alloy)
            self.assertIsNone(out["fatigueLimit_MPa"], alloy)
            self.assertIn("hardness_HV", out["missingInputs"])
            self.assertIn("Missing: Vickers hardness", out["quantities"]["fatigueThreshold"]["validity"]["noValueText"])
            self.assertNotIn("alloyHvDefaults", out)

    def test_empty_request_is_data_not_supplied_with_constructive_text(self):
        out = run(None, hv=None)
        self.assertEqual(out["status"], "data_not_supplied")
        text = out["quantities"]["fatigueThreshold"]["validity"]["noValueText"]
        self.assertIn("Laser settings alone do not determine fatigue strength.", text)
        self.assertEqual(qe.container_problems(out, "c"), [])

    def test_location_and_evidence_kind_are_never_defaulted(self):
        for drop in ("defectLocation", "defectEvidence", "hardnessEvidence"):
            out = run({**SCENARIO, drop: None})
            self.assertIsNone(out["fatigueLimit_MPa"], drop)
            self.assertTrue(out["missingInputs"], drop)

    def test_nonpositive_or_nonfinite_inputs_raise(self):
        for bad in ({**SCENARIO, "defectSqrtArea_um": 0.0}, {**SCENARIO, "defectSqrtArea_um": float("nan")}):
            with self.assertRaises(iv.ValidationError):
                run(bad)
        with self.assertRaises(iv.ValidationError):
            run(SCENARIO, hv=-1.0)


class ThresholdScenarioTests(unittest.TestCase):
    def test_value_matches_printed_law_and_is_tier_two(self):
        for location, c in (("internal", 1.56), ("surface", 1.43)):
            out = run({**SCENARIO, "defectLocation": location})
            self.assertAlmostEqual(out["fatigueLimit_MPa"], oracle(c, 330.0, 150.0), places=9)
            q = out["quantities"]["fatigueThreshold"]
            self.assertAlmostEqual(q["value"], oracle(c, 330.0, 150.0) * 1e6, delta=1e-3)
            self.assertEqual(q["unit"], "Pa")
            v = q["validity"]
            self.assertEqual(v["estimateTier"], "Physics estimate")
            self.assertEqual(v["tierLabel"], "Uncalibrated estimate")
            self.assertEqual(v["displaySignificantDigits"], 2)
            self.assertIsNone(v["estimateBand"])
            self.assertTrue(v["explanation"].startswith("Uncalibrated estimate: about "))
            self.assertIn(TIER2_SENTENCE, v["explanation"])
            self.assertIn("R = -1 threshold scenario", v["explanation"])
            self.assertIn("Assumed defect scenario.", v["explanation"])
            self.assertEqual(qe.container_problems(out, "c"), [])

    def test_typed_scenario_is_echoed_with_assumed_provenance(self):
        out = run(SCENARIO)
        echo = out["scenarioEcho"]
        self.assertEqual((echo["defectSqrtArea_um"], echo["hardness_HV"], echo["defectLocation"]),
                         (150.0, 330.0, "internal"))
        self.assertEqual(echo["defectEvidence"], "assumed-scenario")
        record = out["inputProvenance"]["defectSqrtArea"]
        self.assertEqual(record["kind"], "userInput")
        self.assertIn("assumed scenario typed by the user", record["scope"])
        self.assertEqual(out["quantities"]["fatigueThreshold"]["sourceEvidenceKind"], "User input")

    def test_short_crack_limit_is_a_hard_gate(self):
        self.assertIsNotNone(run({**SCENARIO, "defectSqrtArea_um": 999.0})["fatigueLimit_MPa"])
        for s in (1000.0, 1001.0):
            out = run({**SCENARIO, "defectSqrtArea_um": s})
            self.assertIsNone(out["fatigueLimit_MPa"], s)
            self.assertIn("1000 micrometre screening limit",
                          out["quantities"]["fatigueThreshold"]["validity"]["noValueText"])
        with mock.patch.object(ms, "SHORT_CRACK_LIMIT_UM", float("inf")):
            self.assertIsNotNone(run({**SCENARIO, "defectSqrtArea_um": 1000.0})["fatigueLimit_MPa"])

    def test_identified_long_crack_refuses_below_the_limit(self):
        out = run({**SCENARIO, "defectIsLongCrack": True})
        self.assertIsNone(out["fatigueLimit_MPa"])
        self.assertIn("long crack", out["quantities"]["fatigueThreshold"]["validity"]["noValueText"])

    def test_load_ratio_other_than_minus_one_refuses(self):
        self.assertIsNotNone(run({**SCENARIO, "loadRatio": -1.0})["fatigueLimit_MPa"])
        out = run({**SCENARIO, "loadRatio": 0.1})
        self.assertIsNone(out["fatigueLimit_MPa"])
        self.assertIn("mean-stress model", out["quantities"]["fatigueThreshold"]["validity"]["noValueText"])

    def test_cycle_target_gets_no_cycle_specific_number(self):
        out = run({**SCENARIO, "cycleTarget": 1e8})
        self.assertIsNone(out["cycleTarget"]["value"])
        self.assertIn("No fatigue strength is given at 1e+08 cycles", out["cycleTarget"]["text"])
        self.assertIn("not a fatigue strength at a stated cycle count",
                      out["quantities"]["fatigueThreshold"]["validity"]["explanation"])

    def test_ti_size_domain_warning_is_quantitative_per_orientation(self):
        def warnings(out):
            return [w["detail"] for w in out["quantities"]["fatigueThreshold"]["validity"]["domainWarnings"]]
        inside = warnings(run({**SCENARIO, "defectSqrtArea_um": 150.0}))  # in both source ranges
        self.assertFalse(any("size-domain extrapolation" in w for w in inside))
        vertical_only = warnings(run({**SCENARIO, "defectSqrtArea_um": 250.0}))
        self.assertTrue(any("horizontal specimen study reports 75 to 200" in w for w in vertical_only))
        self.assertFalse(any("vertical specimen" in w for w in vertical_only))
        chosen = warnings(run({**SCENARIO, "defectSqrtArea_um": 250.0, "specimenOrientation": "vertical"}))
        self.assertFalse(any("size-domain extrapolation" in w for w in chosen))

    def test_other_alloys_say_support_is_not_established(self):
        for alloy in ("alsi10mg", "in718", "ss316l"):
            details = " ".join(w["detail"] for w in run(SCENARIO, alloy=alloy)["quantities"]["fatigueThreshold"]
                               ["validity"]["domainWarnings"])
            self.assertIn("Size-domain support is not established for this alloy and state. The supplied size is "
                          "150 micrometres.", details)


class StatisticsAndInspectionTests(unittest.TestCase):
    MAXIMA = [40.0, 55.0, 62.0, 48.0, 70.0]
    DESIGN = {"design": "comparable-independent-block-maxima", "blockVolume_mm3": 10.0, "targetVolume_mm3": 1000.0,
              "targetProbability": 0.5}

    def test_individual_pores_give_only_the_observed_maximum(self):
        out = run({**SCENARIO, "defectSqrtArea_um": None, "defectEvidence": "measured"}, defects=self.MAXIMA)
        self.assertEqual(out["observedMaximum"]["value_um"], 70.0)
        self.assertEqual(out["observedMaximum"]["label"], "observed in supplied data")
        self.assertIsNone(out["quantities"]["gumbelLargest"]["value"])
        self.assertIn("cannot establish the part-wide maximum",
                      out["quantities"]["gumbelLargest"]["validity"]["noValueText"])
        self.assertEqual(out["scenarioEcho"]["defectSqrtAreaBasis"], "largest supplied defect")

    def test_block_maxima_quantile_matches_an_independent_calculation(self):
        out = run({**SCENARIO, "defectEvidence": "measured", "defectSampling": self.DESIGN}, defects=self.MAXIMA)
        n = len(self.MAXIMA)
        mean = sum(self.MAXIMA) / n
        std = math.sqrt(sum((x - mean) ** 2 for x in self.MAXIMA) / (n - 1))
        beta = std * math.sqrt(6) / math.pi
        mu = mean - 0.5772156649015329 * beta
        p_block = 0.5 ** (10.0 / 1000.0)
        expected = mu - beta * math.log(-math.log(p_block))
        q = out["quantities"]["gumbelLargest"]
        self.assertAlmostEqual(q["value"], expected * 1e-6, delta=1e-15)
        # P(max of 100 blocks <= x) = F(x)^100 = 0.5.
        cdf = math.exp(-math.exp(-(expected - mu) / beta))
        self.assertAlmostEqual(cdf ** 100, 0.5, places=12)
        self.assertEqual(q["validity"]["estimateTier"], "Physics estimate")
        self.assertEqual(qe.container_problems(out, "c"), [])

    def test_inadmissible_designs_refuse(self):
        for bad in ({**self.DESIGN, "targetProbability": None}, {**self.DESIGN, "targetVolume_mm3": 1.0},
                    {**self.DESIGN, "design": "individual-pores"}):
            out = run({**SCENARIO, "defectEvidence": "measured", "defectSampling": bad}, defects=self.MAXIMA)
            self.assertIsNone(out["quantities"]["gumbelLargest"]["value"], bad)
        same = run({**SCENARIO, "defectEvidence": "measured", "defectSampling": self.DESIGN}, defects=[50.0] * 4)
        self.assertIsNone(same["quantities"]["gumbelLargest"]["value"])
        self.assertIn("Zero empirical variance", same["quantities"]["gumbelLargest"]["validity"]["noValueText"])
        two = run({**SCENARIO, "defectEvidence": "measured", "defectSampling": self.DESIGN}, defects=[40.0, 50.0])
        self.assertIsNone(two["quantities"]["gumbelLargest"]["value"])

    def test_ct_threshold_is_an_echo_without_tier(self):
        none = run(SCENARIO)["ctDetectionThreshold"]
        self.assertIsNone(none["value_um"])
        self.assertIn("Add the CT detection threshold and its validation method", none["text"])
        bare = run(SCENARIO, ct=12.0)["ctDetectionThreshold"]
        self.assertEqual(bare["value_um"], 12.0)
        self.assertIn("without a validation method", bare["label"])
        echoed = run({**SCENARIO, "ctDetectionMethod": "POD 90/95 on drilled holes"}, ct=12.0)["ctDetectionThreshold"]
        self.assertEqual(echoed["method"], "POD 90/95 on drilled holes")
        self.assertNotIn("estimateTier", echoed)


if __name__ == "__main__":
    unittest.main()
