#!/usr/bin/env python3
"""Self-contained tests of group 8 first pass (python/lpbf_kinetics_estimates.py and the Build Job kinetics block).

Synthetic fields below are manufactured analytic test functions, not alloy data. Salsi Table 3 knots are the source
rows already recorded in docs/research/SPEC_engine_estimates_2026-10-17.md (ECK-6); no other constant is introduced.
"""
import math
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import lpbf_kinetics_estimates as ke  # noqa: E402
import quantity_envelope as qe  # noqa: E402

TIER2_SENTENCE = "Uncertainty is unknown and may be large. Calibrate to your machine for better accuracy."
TP, AMP, LENGTH, V = 100.0, 2000.0, 1e-4, 1.0


def synthetic_field(x, y, z):
    """Monotone decay behind the source: T = TP + AMP exp(x / LENGTH) for x <= 0."""
    return TP + AMP * math.exp(min(x, 0.0) / LENGTH)


def analytic_time(level, x0=0.0):
    return (x0 - LENGTH * math.log((level - TP) / AMP)) / V


class DissolutionTests(unittest.TestCase):
    def test_spec_reference_value_at_500C_one_hour(self):
        self.assertAlmostEqual(ke.dissolved_fraction(500.0, 3600.0)["dissolved"], 0.72, places=12)

    def test_fit_passes_through_both_source_times_at_every_knot(self):
        for T, a, t30, t90 in ke.SALSI_TABLE3:
            k, p = ke.dissolution_parameters(a, t30, t90)
            self.assertAlmostEqual(-math.expm1(-k * t30 ** p), 0.3, places=12)
            self.assertAlmostEqual(-math.expm1(-k * t90 ** p), 0.9, places=12)
            self.assertAlmostEqual(ke.dissolved_fraction(T, t90)["dissolved"], 0.9 * a, places=12)

    def test_outside_source_range_and_non_knot_refuse(self):
        for T in (320.0, 399.9, 700.1):
            with self.assertRaises(ValueError):
                ke.dissolved_fraction(T, 3600.0, interpolate=True)
        with self.assertRaises(ValueError):
            ke.dissolved_fraction(600.0, 3600.0)
        interpolated = ke.dissolved_fraction(600.0, 3600.0, interpolate=True)
        self.assertEqual(interpolated["basis"], "interpolated-scenario")
        self.assertAlmostEqual(interpolated["a_eq"], 0.9)
        self.assertAlmostEqual(interpolated["t30_s"], 485.0)

    def test_hold_splitting_is_not_used_as_a_varying_path(self):
        # Hold-time monotonicity only: a longer hold never dissolves less.
        values = [ke.dissolved_fraction(700.0, t)["dissolved"] for t in (10.0, 100.0, 1000.0, 1e5)]
        self.assertEqual(values, sorted(values))
        self.assertLessEqual(values[-1], 1.0)


class PathTests(unittest.TestCase):
    SAMPLE = {"position_m": {"x": 0.0, "z": 0.0}}

    def test_average_rate_matches_the_analytic_crossings(self):
        out = ke.path_cooling(synthetic_field, self.SAMPLE, V, 1500.0, 300.0)
        expected = (1500.0 - 300.0) / (analytic_time(300.0) - analytic_time(1500.0))
        self.assertAlmostEqual(out["rate_K_s"] / expected, 1.0, places=9)

    def test_reheating_path_is_refused(self):
        def bumped(x, y, z):
            return synthetic_field(x, y, z) + (400.0 if -3e-4 < x < -2e-4 else 0.0)
        with self.assertRaises(ValueError) as ctx:
            ke.path_cooling(bumped, self.SAMPLE, V, 1500.0, 150.0)
        self.assertEqual(str(ctx.exception), "reheating-needs-segment-rates")

    def test_unreached_level_is_refused(self):
        with self.assertRaises(ValueError) as ctx:
            ke.path_cooling(synthetic_field, self.SAMPLE, V, 1500.0, 50.0)  # below the asymptote TP
        self.assertEqual(str(ctx.exception), "missing-crossing")

    def test_interval_must_be_subsolidus_and_above_preheat(self):
        props = {"solidus_C": 1000.0}
        self.assertEqual(ke._interval(None, props, 80.0)[:2], ((1000.0, 105.0), "declared-default"))
        for bad in ({"high_C": 1200.0, "low_C": 300.0}, {"high_C": 500.0, "low_C": 50.0},
                    {"high_C": 300.0, "low_C": 500.0}, {"high_C": "x", "low_C": 1}):
            interval, _, text = ke._interval(bad, props, 80.0)
            self.assertIsNone(interval, bad)
            self.assertIn("subsolidus temperature interval", text)


class BuildJobKineticsTests(unittest.TestCase):
    VECTORS = {"ti6al4v": (240, 1200, 150), "alsi10mg": (350, 1300, 160)}

    @classmethod
    def setUpClass(cls):
        from lpbf_build_job_solver import solve_lpbf_build_job
        cls.jobs = {}
        for alloy, (p, v, t) in cls.VECTORS.items():
            extra = {"isothermalHold": {"temperature_C": 500, "time_s": 3600}} if alloy == "ti6al4v" else {}
            cls.jobs[alloy] = solve_lpbf_build_job(dict(
                alloyId=alloy, laserPower_W=p, scanSpeed_mm_s=v, beamDiameter_um=80, preheatTemp_C=t,
                layerThickness_um=40, hatchSpacing_um=100, bypassCache=True, **extra))["kinetics"]

    def test_containers_are_valid_v2_and_tier_two(self):
        for alloy, k in self.jobs.items():
            e = k["estimates"]
            self.assertEqual(qe.container_problems(e, "e"), [], alloy)
            q = e["quantities"]["pathCoolingRate"]
            self.assertGreater(q["value"], 0)
            self.assertEqual(q["validity"]["estimateTier"], "Physics estimate")
            self.assertIn(TIER2_SENTENCE, q["validity"]["explanation"])
            self.assertIn("does not determine the final phases", q["validity"]["explanation"])
            self.assertEqual(k["status"], "partial")
            self.assertEqual(k["buildCoolingRate_C_s"], q["value"])
            # A single average never selects a CCT row or a steel martensite fraction.
            self.assertIsNone(k["cctContinuousCoolingMap"])
            self.assertIsNone(k["buildCoolingRateCctRow"])
            self.assertIsNone(k["buildRateMartensite"])

    def test_interval_is_named_per_alloy_never_ti_transus_elsewhere(self):
        ti, al = self.jobs["ti6al4v"]["estimates"], self.jobs["alsi10mg"]["estimates"]
        self.assertEqual(al["coolingInterval"]["rule"], "solidus-to-preheat-plus-25K-v1")
        self.assertEqual(al["coolingInterval"]["low_C"], 185.0)
        record = al["inputProvenance"]["coolingInterval"]
        self.assertEqual(record["kind"], "declaredAssumption")
        self.assertIn("declared convention: solidus to preheat plus 25 K", record["scope"])
        self.assertIn(f"{al['coolingInterval']['high_C']:g} C to 185 C", record["scope"])
        self.assertNotEqual(al["coolingInterval"]["high_C"], 998.0)
        self.assertIn(f"{al['coolingInterval']['high_C']:g} C", al["quantities"]["pathCoolingRate"]["validity"]
                      ["explanation"])
        self.assertEqual(ti["coolingInterval"]["low_C"], 175.0)

    def test_ti_km_first_pass_and_dissolution_reference(self):
        q = self.jobs["ti6al4v"]["estimates"]["quantities"]
        self.assertAlmostEqual(q["kmAlphaMFraction"]["value"], 1.0 - math.exp(-0.005 * (575.0 - 175.0)), places=12)
        text = q["kmAlphaMFraction"]["validity"]["explanation"]
        self.assertIn("Ms and km are literature assumptions adopted by Salsi et al. from their reference [10].", text)
        self.assertNotIn("fitted source parameter", text)
        self.assertAlmostEqual(q["tiMartensiteDissolution"]["value"], 0.72, places=12)
        self.assertEqual(q["tiMartensiteDissolution"]["fractionBasis"], "reaction-progress")
        self.assertEqual(q["tiMartensiteDissolution"]["validity"]["displaySignificantDigits"], 1)

    def test_other_alloys_refuse_phase_quantities_constructively(self):
        q = self.jobs["alsi10mg"]["estimates"]["quantities"]
        self.assertNotIn("kmAlphaMFraction", q)
        self.assertNotIn("tiMartensiteDissolution", q)
        self.assertIsNone(q["phaseTransformation"]["value"])
        self.assertIn("same-alloy reaction model", q["phaseTransformation"]["validity"]["noValueText"])

    def test_no_parent_means_no_numbers(self):
        from lpbf_build_job_solver import build_job_kinetics
        legacy = build_job_kinetics("ti6al4v", {})
        self.assertEqual(legacy["status"], "unavailable")
        self.assertNotIn("estimates", legacy)
        block = build_job_kinetics("ti6al4v", {"processParameters": {}}, None,
                                   {"power_W": 240.0, "speed_mm_s": 1200.0, "beamDiameter_um": 80.0,
                                    "preheat_C": 150.0, "layerThickness_um": 40.0, "hatch_um": 100.0})
        q = block["estimates"]["quantities"]
        self.assertIsNone(q["pathCoolingRate"]["value"])
        self.assertEqual(q["pathCoolingRate"]["reasons"][0]["code"], "missing-thermal-history")
        self.assertIsNone(q["kmAlphaMFraction"]["value"])
        self.assertIsNone(block["buildCoolingRate_C_s"])
        self.assertEqual(qe.container_problems(block["estimates"], "e"), [])

    def test_hold_gates(self):
        from lpbf_kinetics_estimates import _dissolution_quantity
        from lpbf_solidification_estimates import Builder
        for hold, needle in ((None, "Enter an isothermal hold"), ({"temperature_C": 800, "time_s": 10}, "400 to 700 C"),
                             ({"temperature_C": 600, "time_s": 10}, "not a source knot"),
                             ({"temperature_C": 500, "time_s": -1}, "positive hold time")):
            b = Builder(ke.MODEL_ID)
            _dissolution_quantity(b, hold)
            q = b.quantities["tiMartensiteDissolution"]
            self.assertIsNone(q["value"], hold)
            self.assertIn(needle, q["validity"]["noValueText"])

    def test_reheating_gate_removal_is_detected(self):
        # With the monotonicity check removed a bumped path would yield a number: the gate is what refuses it.
        def bumped(x, y, z):
            return synthetic_field(x, y, z) + (400.0 if -3e-4 < x < -2e-4 else 0.0)
        sample = {"position_m": {"x": 0.0, "z": 0.0}}
        with self.assertRaises(ValueError):
            ke.path_cooling(bumped, sample, V, 1500.0, 150.0)
        original = ke.path_crossings

        def ungated(T_fn, x0, z0, v, levels, ratio=ke.PATH_RATIO):
            return original(lambda x, y, z: min(T_fn(x, y, z), synthetic_field(x, y, z)), x0, z0, v, levels, ratio)
        with mock.patch.object(ke, "path_crossings", ungated):
            self.assertGreater(ke.path_cooling(bumped, sample, V, 1500.0, 150.0)["rate_K_s"], 0)


if __name__ == "__main__":
    unittest.main()
