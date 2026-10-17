"""Shared Murakami constants and input rejection (engine-fix lane: audit defect 7).

Oracle: Murakami (2002) sigma_w = C (HV + 120) / sqrt(area)^(1/6) with C = 1.43
surface, 1.41 sub-surface (touching the surface), 1.56 interior. The numbers below
are computed independently with the closed form (HV 380, sqrt(area) 50 um), not by
calling the code under test; the audit quotes 372.5 vs 406.4 MPa for the same case.
"""

import math
import unittest

import input_validation as iv
import lpbf_fatigue_fracture as ff
import lpbf_worker
import lpbf_worker_rpc
import murakami_constants as mc
import murakami_fatigue_screening as ms
from lpbf_build_job_schema import LpbfBuildJobRequest

HV, AREA = 380.0, 50.0
SIXTH = math.exp(math.log(AREA) / 6.0)  # sqrt(area)^(1/6), independent of the module


def oracle(c):
    return c * (HV + 120.0) / SIXTH


class ConstantsTest(unittest.TestCase):
    def test_constant_values(self):
        self.assertEqual(dict(mc.MURAKAMI_C), {"surface": 1.43, "subsurface": 1.41, "internal": 1.56})

    def test_location_spellings(self):
        for text, canon in (("surface", "surface"), (" Surface ", "surface"), ("sub-surface", "subsurface"),
                            ("subsurface", "subsurface"), ("internal", "internal"), ("INTERIOR", "internal")):
            self.assertEqual(mc.classify_location(text), canon)

    def test_unknown_location_is_rejected(self):
        for bad in ("embedded", "", None, 3):
            with self.assertRaises(iv.ValidationError) as ctx:
                mc.classify_location(bad)
            self.assertEqual(ctx.exception.code, iv.OUT_OF_RANGE)
            self.assertEqual(ctx.exception.field, "location")


class ScreeningEngineTest(unittest.TestCase):
    def test_internal_uses_1_56_not_1_43(self):
        self.assertAlmostEqual(ms.murakami_fatigue_limit_MPa(AREA, HV, "internal"), oracle(1.56), places=9)
        self.assertAlmostEqual(oracle(1.56), 406.4, places=1)  # audit value

    def test_surface_uses_1_43_not_1_41(self):
        self.assertAlmostEqual(ms.murakami_fatigue_limit_MPa(AREA, HV, "surface"), oracle(1.43), places=9)
        self.assertAlmostEqual(oracle(1.43), 372.5, places=1)  # audit value
        self.assertAlmostEqual(ms.murakami_fatigue_limit_MPa(AREA, HV, "sub-surface"), oracle(1.41), places=9)

    def test_evaluate_block_reports_the_standard_constants(self):
        # One explicitly chosen defect and location: the named-location leaf uses that location's constant.
        for location, c in (("internal", 1.56), ("surface", 1.43)):
            block = ms.evaluate_murakami_block([AREA], hardness_HV=HV, scenario={
                "defectEvidence": "measured", "hardnessEvidence": "measured", "defectLocation": location})
            self.assertEqual(block["status"], "screening_estimate")
            self.assertAlmostEqual(block["fatigueLimit_MPa"], oracle(c), places=9)
            self.assertEqual(block["defectLocation"], location)

    def test_nonpositive_inputs_are_rejected_not_clamped(self):
        for area, hv in ((0.0, HV), (-5.0, HV), (AREA, 0.0), (AREA, -1.0), (float("nan"), HV), (AREA, float("inf"))):
            with self.assertRaises(iv.ValidationError, msg=(area, hv)):
                ms.murakami_fatigue_limit_MPa(area, hv, "internal")
        with self.assertRaises(iv.ValidationError):
            ms.evaluate_murakami_block([-3.0], hardness_HV=HV)

    def test_paste_rejects_inf_and_nan_tokens(self):
        self.assertEqual(ms.parse_defect_sqrt_areas_text("40, 55; -3 0 abc"), [40.0, 55.0])
        for text in ("40 inf 50", "40, nan", "-inf 40", "Infinity"):
            with self.assertRaises(iv.ValidationError, msg=text) as ctx:
                ms.parse_defect_sqrt_areas_text(text)
            self.assertEqual(ctx.exception.code, iv.NON_FINITE)

    def test_build_job_request_rejects_nonpositive_defects_and_hardness(self):
        LpbfBuildJobRequest.model_validate({"defectSqrtAreas_um": [10.0, 40.0], "hardness_HV": 380})
        for bad in ({"defectSqrtAreas_um": [10.0, 0.0]}, {"defectSqrtAreas_um": [-1.0]},
                    {"defectSqrtAreas_um": [float("nan")]}, {"hardness_HV": 0}, {"hardness_HV": -5}):
            with self.assertRaises(Exception, msg=bad):
                LpbfBuildJobRequest.model_validate(bad)


class FractureEngineTest(unittest.TestCase):
    def setUp(self):
        self.engine = ff.MurakamiFatigueEngine("Ti-6Al-4V")

    def test_both_engines_share_the_same_constants_and_formula(self):
        hv = self.engine.alloy.hardness_HV
        for location in ("surface", "sub-surface", "internal"):
            raw = self.engine.calculate_fatigue_limit(AREA, location)["murakami_raw_MPa"]
            self.assertAlmostEqual(raw, ms.murakami_fatigue_limit_MPa(AREA, hv, location), delta=0.05)
        self.assertEqual(self.engine.murakami_geometric_constant("surface"), 1.43)
        self.assertEqual(self.engine.murakami_geometric_constant("sub-surface"), 1.41)
        self.assertEqual(self.engine.murakami_geometric_constant("internal"), 1.56)

    def test_stress_ratio_one_is_rejected_not_a_division_by_zero(self):
        for method in (
            lambda: self.engine.simulate_paris_crack_growth(40.0, 200.0, stress_ratio_R=1.0),
            lambda: self.engine.simulate_paris_crack_growth(40.0, 200.0, stress_ratio_R=1.5),
            lambda: self.engine.calculate_fatigue_limit(40.0, "internal", 1.0),
            lambda: self.engine.generate_kitagawa_takahashi_curve("internal", 1.0),
        ):
            with self.assertRaises(iv.ValidationError) as ctx:
                method()
            self.assertEqual(ctx.exception.code, iv.OUT_OF_RANGE)
            self.assertEqual(ctx.exception.field, "stressRatio_R")

    def test_zero_amplitude_and_bad_sqrt_area_are_rejected(self):
        for kwargs, field in (({"cyclic_stress_amplitude_MPa": 0.0}, "stressAmplitude_MPa"),
                              ({"cyclic_stress_amplitude_MPa": -10.0}, "stressAmplitude_MPa"),
                              ({"initial_defect_sqrt_area_um": -5.0}, "sqrtArea_um"),
                              ({"initial_defect_sqrt_area_um": 0.0}, "sqrtArea_um")):
            args = {"initial_defect_sqrt_area_um": 40.0, "cyclic_stress_amplitude_MPa": 200.0, "stress_ratio_R": 0.1}
            args.update(kwargs)
            with self.assertRaises(iv.ValidationError) as ctx:
                self.engine.simulate_paris_crack_growth(**args)
            self.assertEqual(ctx.exception.field, field)
        with self.assertRaises(iv.ValidationError):
            self.engine.calculate_fatigue_limit(-5.0)

    def test_valid_inputs_still_work(self):
        res = self.engine.simulate_paris_crack_growth(80.0, 280.0, stress_ratio_R=0.1)
        self.assertEqual(res["status"], "fractured")
        self.assertIn("fatigue_limit_corrected_MPa", self.engine.calculate_fatigue_limit(45.0, "sub-surface", 0.1))

    def test_worker_rpc_relays_the_validation_envelope(self):
        for payload, field in (({"stressRatio_R": 1.0}, "stressRatio_R"),
                               ({"stressAmplitude_MPa": 0}, "stressAmplitude_MPa"),
                               ({"sqrtArea_um": -4}, "sqrtArea_um")):
            request = {"id": 9, "method": "fatigue-fracture", "payload": dict({"alloyName": "Ti-6Al-4V"}, **payload)}
            with self.assertRaises(iv.ValidationError) as ctx:
                lpbf_worker_rpc.dispatch(request, None, lambda q: {})
            reply = lpbf_worker.rpc_error_response(request, ctx.exception)
            self.assertEqual(reply["errorKind"], "validation")
            self.assertEqual(reply["validation"]["error"]["field"], field)
            self.assertIs(reply["validation"]["success"], False)


if __name__ == "__main__":
    unittest.main()
