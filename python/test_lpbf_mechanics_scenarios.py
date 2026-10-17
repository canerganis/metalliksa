#!/usr/bin/env python3
"""Self-contained tests of the group 2 mechanics scenarios (python/lpbf_mechanics_scenarios.py, SPEC group 2 with
Amendment 1 A1.2/A1.3). Every modulus, expansion coefficient, yield and profile below is a synthetic scenario typed
for this file, not alloy data."""
import copy
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import lpbf_mechanics_scenarios as ms  # noqa: E402
import quantity_envelope as qe  # noqa: E402

UNKNOWN = "Uncertainty is unknown and may be large. Calibrate to your machine for better accuracy."
E, ALPHA, SY = 100.0, 1e-5, 500.0  # GPa, 1/K, MPa: yield strain 5e-3, thermal strain per K 1e-5
BAR = dict(elasticModulus_GPa=E, elasticModulusEvidence="assumed-scenario", thermalExpansion_per_K=ALPHA,
           thermalExpansionEvidence="assumed-scenario", returnYield_MPa=SY, returnYieldEvidence="assumed-scenario",
           returnTemperature_C=20.0, peakTemperature_C=1020.0)
BEAM = dict(profileEvidence="assumed-effective-profile-scenario", length_mm=30.0, thickness_mm=3.0,
            elasticModulus_GPa=E, releaseYield_MPa=SY, maxRotation_rad=0.1,
            profile=[{"from": 0.0, "to": 0.5, "strain": 0.0}, {"from": 0.5, "to": 1.0, "strain": -0.002}])


def run(bar=None, beam=None, solidus=1500.0):
    return ms.evaluate_mechanics({"bar": bar, "cantilever": beam}, alloy_id="ti6al4v", solidus_C=solidus)


class ConstrainedBarTests(unittest.TestCase):
    def test_return_mapping_matches_the_closed_form_around_both_thresholds(self):
        # q = E alpha dT; yield thresholds at q = sy (500 K) and q = 2 sy (1000 K).
        for dT in (400.0, 499.0, 500.0, 501.0, 750.0, 999.0, 1000.0, 1001.0, 1500.0):
            got = ms.constrained_bar_cycle(E * 1e9, ALPHA, SY * 1e6, dT)["stress_Pa"]
            self.assertAlmostEqual(got, ms.m1_closed_form(E * 1e9, ALPHA, SY * 1e6, dT), delta=1e-3, msg=dT)

    def test_saturation_flag_and_mandatory_sentences(self):
        hot = run(bar=dict(BAR, peakTemperature_C=20.0 + 700.0))  # q = 1.4 sy: not saturated
        self.assertFalse(hot["barScenario"]["saturatedAtYield"])
        sat = run(bar=BAR)  # dT = 1000 K: q = 2 sy, saturated
        q = sat["quantities"]["barStress"]
        self.assertTrue(sat["barScenario"]["saturatedAtYield"])
        self.assertAlmostEqual(q["value"], SY * 1e6, delta=1e-3)
        text = q["validity"]["explanation"]
        self.assertIn(ms.M1_SCOPE, text)
        self.assertIn(ms.M1_SATURATED, text)
        self.assertIn(UNKNOWN, text)
        self.assertNotIn(ms.M1_SATURATED, hot["quantities"]["barStress"]["validity"]["explanation"])
        self.assertEqual(q["validity"]["estimateTier"], "Physics estimate")
        self.assertEqual(qe.container_problems(sat, "c"), [])

    def test_hot_yield_is_not_final_saturation(self):
        out = run(bar=dict(BAR, peakTemperature_C=20.0 + 700.0))  # yields hot, returns to q - sy = 200 MPa
        self.assertTrue(out["barScenario"]["yielded"])
        self.assertFalse(out["barScenario"]["saturatedAtYield"])
        self.assertAlmostEqual(out["quantities"]["barStress"]["value"], 200e6, delta=1e-3)

    def test_refusals(self):
        for bad in (dict(BAR, returnYield_MPa=None), dict(BAR, elasticModulusEvidence=None),
                    dict(BAR, thermalExpansion_per_K=-1.0), dict(BAR, peakTemperature_C=0.0)):
            q = run(bar=bad)["quantities"]["barStress"]
            self.assertIsNone(q["value"], bad)
            self.assertIn("Supply those inputs", q["validity"]["noValueText"])
        melt = run(bar=dict(BAR, peakTemperature_C=1500.0))["quantities"]["barStress"]
        self.assertIsNone(melt["value"])
        self.assertIn("cannot cross the melt interval", melt["validity"]["noValueText"])
        self.assertEqual(run()["quantities"]["barStress"]["status"], "not-requested")


class CantileverTests(unittest.TestCase):
    def test_two_half_section_profile_matches_the_amendment_reference(self):
        out = run(beam=BEAM)
        scenario = out["cantileverScenario"]
        H = 3e-3
        self.assertAlmostEqual(scenario["curvature_1_m"], 1.5 * -0.002 / H, places=9)  # kappa = 1.5 e / H
        tip = out["quantities"]["tipDeflection"]
        self.assertAlmostEqual(tip["value"], 1.5 * -0.002 / H * 0.03 ** 2 / 2, places=12)
        self.assertAlmostEqual(out["quantities"]["tipDeflectionOverThickness"]["value"], abs(tip["value"]) / H)
        self.assertIn(ms.M2_SCOPE, tip["validity"]["explanation"])
        self.assertNotIn(ms.M2_UNIFORM, tip["validity"]["explanation"])
        self.assertEqual(qe.container_problems(out, "c"), [])

    def test_uniform_profile_gives_zero_curvature_with_its_scope_sentence(self):
        uniform = dict(BEAM, profile=[{"from": 0.0, "to": 1.0, "strain": -0.003}])
        q = run(beam=uniform)["quantities"]["tipDeflection"]
        self.assertEqual(q["value"], 0.0)
        self.assertIn(ms.M2_UNIFORM, q["validity"]["explanation"])

    def test_independent_quadrature_of_a_linear_profile(self):
        # eps*(z) = a z on [-H/2, H/2] gives kappa = a exactly; approximate it by 400 thin segments.
        H, a, n = 3e-3, 0.5, 400
        segments = []
        for i in range(n):
            z_mid = (-0.5 + (i + 0.5) / n) * H
            segments.append({"from": i / n, "to": (i + 1) / n, "strain": a * z_mid})
        kappa = ms.section_release(H, segments, 1e11)["curvature_1_m"]
        self.assertAlmostEqual(kappa / a, 1.0, delta=1e-5)

    def test_gates(self):
        cases = {
            "m1 provenance": dict(BEAM, profileEvidence="m1-derived"),
            "missing evidence": dict(BEAM, profileEvidence=None),
            "gap in profile": dict(BEAM, profile=[{"from": 0.0, "to": 0.4, "strain": 0.0},
                                                  {"from": 0.5, "to": 1.0, "strain": -0.002}]),
            "no rotation limit": dict(BEAM, maxRotation_rad=None),
            "large rotation": dict(BEAM, maxRotation_rad=1e-3),
            "plastic release": dict(BEAM, releaseYield_MPa=10.0),
            "unmatched calibration": dict(BEAM, profileEvidence="matched-build-calibration",
                                          calibrationIdentity={"buildId": "B1"}),
        }
        for name, beam in cases.items():
            q = run(beam=beam)["quantities"]["tipDeflection"]
            self.assertIsNone(q["value"], name)
            self.assertTrue(q["validity"]["noValueText"], name)
        self.assertIn("cannot determine cantilever bending",
                      run(beam=cases["m1 provenance"])["quantities"]["tipDeflection"]["validity"]["noValueText"])
        identity = {k: "x" for k in ms.CALIBRATION_KEYS}
        matched = run(beam=dict(BEAM, profileEvidence="matched-build-calibration", calibrationIdentity=identity))
        self.assertIsNotNone(matched["quantities"]["tipDeflection"]["value"])

    def test_rotation_gate_removal_is_detected(self):
        beam = dict(BEAM, maxRotation_rad=1e-3)
        self.assertIsNone(run(beam=beam)["quantities"]["tipDeflection"]["value"])
        self.assertIsNotNone(run(beam=dict(beam, maxRotation_rad=10.0))["quantities"]["tipDeflection"]["value"])

    def test_never_used_by_the_verdict(self):
        out = run(bar=BAR, beam=BEAM)
        self.assertFalse(out["usedForBuildJobVerdict"])
        self.assertIn("distortionIndex", out["legacyKeysUnchanged"])


if __name__ == "__main__":
    unittest.main()
