"""SOL-C estimate channel: routes, gates, labels and mutation checks (self-contained fixtures, no datasets).

Every fixture here is a manufactured field, a synthetic process point or a source constant; no measured melt-pool
row, bands file or external-data directory is read.
"""
from __future__ import annotations

import copy
import json
import math
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

import lpbf_solidification_estimates as se
import quantity_envelope as qe
from lpbf_thermal_solver import calculate_meltpool_physics, rosenthal_temperature_C

ROOT = Path(__file__).resolve().parents[1]
BASE = {"beamDiameter_um": 80.0, "preheat_C": 80.0, "layerThickness_um": 40.0, "hatch_um": 100.0,
        "heatSource": "rosenthal"}
CONDUCTION = {"ti6al4v": ("Ti-6Al-4V", 120.0, 1200.0), "alsi10mg": ("AlSi10Mg", 300.0, 1200.0),
              "in718": ("Inconel 718", 200.0, 900.0), "ss316l": ("316L Stainless Steel", 200.0, 900.0),
              "in625": ("Inconel 625", 150.0, 1200.0)}
_CACHE: dict = {}


def run(material, power, speed, heat_source="rosenthal", **options):
    key = (material, power, speed, heat_source, tuple(sorted(options.items())))
    if key not in _CACHE:
        _CACHE[key] = se.compute_solidification_estimates(
            {"params": {**BASE, "materialName": material, "power_W": power, "speed_mm_s": speed,
                        "heatSource": heat_source}, "options": options})
    return _CACHE[key]


# Independent analytic derivative of the live regularised Rosenthal field on its smooth, unclipped branch
# (the A6 thermal checker's oracle, rewritten here; it shares no code with the sampler).
class Manufactured:
    P, k, rho, cp, v, T0, TL, r = 60.0, 20.0, 7000.0, 700.0, 0.8, 80.0, 1400.0, 3e-5

    @property
    def alpha(self):
        return self.k / (self.rho * self.cp)

    def T(self, x, y, z):
        return rosenthal_temperature_C(x, y, z, self.T0, self.P, self.k, self.v, self.alpha, self.r)

    def grad(self, x, y, z):
        rr = math.sqrt(x * x + y * y + z * z)
        rr2 = rr * rr + self.r * self.r
        a = self.v / (2.0 * self.alpha)
        rise = self.P / (2 * math.pi * self.k * math.sqrt(rr2)) * math.exp(-a * (rr + x))
        return tuple(rise * (-q / rr2 - a * (q / rr + (i == 0))) for i, q in enumerate((x, y, z)))


def oracle_agrees(front, field, rtol=1e-5):
    """Sampler tuples agree with the analytic derivative and the analytic kinematics at every retained node.

    An empty or short retained set never agrees (a mutant that invalidates every tuple must not pass vacuously)."""
    if len(se.valid_samples(front)) < se.MIN_BRANCH_SAMPLES:
        return False
    for s in se.valid_samples(front):
        p = s["position_m"]
        gx, gy, gz = field.grad(p["x"], p["y"], p["z"])
        G = math.sqrt(gx * gx + gy * gy + gz * gz)
        R = field.v * gx / G
        expected = {"G_K_m": G, "R_m_s": R, "coolingRate_K_s": field.v * gx, "gOverR_K_s_m2": G * G / (field.v * gx)}
        for key, value in expected.items():
            if not math.isclose(s[key], value, rel_tol=rtol):
                return False
        if abs(s["gradient_K_m"]["gz"] - gz) > rtol * G:
            return False
    return True


def offaxis_agrees(gradient_fn, field, rtol=1e-6):
    """The served stencil against the analytic derivative at off-axis interior points (gy != 0)."""
    for point in ((-1.2e-4, 2.5e-5, 3e-5), (-6e-5, -4e-5, 1.5e-5), (-2e-4, 1e-5, 4e-5)):
        expected = field.grad(*point)
        got = gradient_fn(field.T, *point, 1e-8, False)
        if any(abs(g - e) > rtol * math.sqrt(sum(c * c for c in expected)) for g, e in zip(got, expected)):
            return False
    return True


class CaptureTransparency(unittest.TestCase):
    def test_served_thermal_result_is_identical_with_and_without_capture(self):
        for material in ("Ti-6Al-4V", "AlSi10Mg", "Inconel 718", "316L Stainless Steel", "Inconel 625"):
            for source in se.HEAT_SOURCES:
                with self.subTest(material=material, source=source):
                    plain = calculate_meltpool_physics(material, 200.0, 900.0, 80.0, heat_source=source,
                                                       include_process_map=False)
                    captured, parent = se.served_solve(material, {**BASE, "power_W": 200.0, "speed_mm_s": 900.0},
                                                       source)
                    self.assertEqual(json.dumps(plain, sort_keys=True, default=repr),
                                     json.dumps(captured, sort_keys=True, default=repr))
                    self.assertEqual(parent["T_liq"], plain["solidificationKinetics"]["inputProvenance"]
                                     ["liquidus_K"]["defaultValue"] - se.KELVIN)

    def test_capture_restores_the_served_function(self):
        import lpbf_thermal_solver as solver
        before = solver.evaluate_solidification
        with se.capture_front_parent():
            self.assertIsNot(solver.evaluate_solidification, before)
        self.assertIs(solver.evaluate_solidification, before)


class Kinematics(unittest.TestCase):
    def setUp(self):
        self.field = Manufactured()
        self.front = se.sample_front(self.field.T, self.field.TL, self.field.v, 4e-4, 1e-4)

    def test_sampler_matches_the_independent_analytic_oracle(self):
        self.assertEqual(self.front["status"], "sampled")
        self.assertEqual(len(se.valid_samples(self.front)), se.NODE_COUNT)
        self.assertTrue(oracle_agrees(self.front, self.field))
        for s in se.valid_samples(self.front):
            self.assertLess(abs(s["root"]["residual_K"]), 1e-6)
            self.assertTrue(s["numericallyResolved"])

    def test_mutated_derivatives_and_projection_fail_the_oracle(self):
        real = se.gradient
        mutants = {
            "no transverse": lambda T, x, y, z, h, s: (real(T, x, y, z, h, s)[0], 0.0, real(T, x, y, z, h, s)[2]),
            "depth sign": lambda T, x, y, z, h, s: (real(T, x, y, z, h, s)[0], real(T, x, y, z, h, s)[1],
                                                    -0.5 * real(T, x, y, z, h, s)[2]),
            "depth halved": lambda T, x, y, z, h, s: tuple(c * (0.5 if i == 2 else 1.0)
                                                           for i, c in enumerate(real(T, x, y, z, h, s))),
        }
        for name, mutant in mutants.items():
            with self.subTest(name), mock.patch.object(se, "gradient", mutant):
                front = se.sample_front(self.field.T, self.field.TL, self.field.v, 4e-4, 1e-4, refine=False)
                # y = 0 symmetry hides a dropped transverse derivative on the slice; the off-axis check exposes it.
                self.assertFalse(oracle_agrees(front, self.field) and offaxis_agrees(se.gradient, self.field), name)
        self.assertTrue(offaxis_agrees(real, self.field))

        def r_equals_scan_speed(g, v):
            out = real_kin(g, v)
            out["R"] = v
            return out
        real_kin = se.kinematics
        with mock.patch.object(se, "kinematics", r_equals_scan_speed):
            front = se.sample_front(self.field.T, self.field.TL, self.field.v, 4e-4, 1e-4, refine=False)
            self.assertFalse(oracle_agrees(front, self.field))

    def test_refusals(self):
        for g in ((0.0, 0.0, 0.0), (-1.0, 0.0, -5.0), (float("nan"), 0.0, 1.0)):
            with self.subTest(g=g), self.assertRaisesRegex(ValueError, "invalid-interface-sample"):
                se.kinematics(g, 1.0)
        cold = se.sample_front(lambda x, y, z: 20.0, 1400.0, 1.0, 4e-4, 1e-4)
        self.assertEqual(cold["status"], "no-crossing")

    def test_every_tuple_is_solidifying_and_open_interval(self):
        branch = self.front["branch"]
        for s in se.valid_samples(self.front):
            self.assertGreater(s["gradient_K_m"]["gx"], 0.0)
            self.assertTrue(branch["xTail_m"] < s["position_m"]["x"] < branch["xBottom_m"])


class Aggregation(unittest.TestCase):
    def test_weighted_median_definitions(self):
        self.assertEqual(se.weighted_median([1.0, 2.0, 3.0, 4.0], [1, 1, 1, 1]), 2.5)
        self.assertEqual(se.weighted_median([1.0, 2.0, 3.0], [1, 1, 5]), 3.0)
        self.assertEqual(se.weighted_median([3.0, 1.0, 2.0], [1, 1, 1]), 2.0)

    def test_local_outputs_are_summarized_not_separate_medians(self):
        rows = [{"valid": True, "weight_m": 1.0, "G_K_m": g, "R_m_s": r, "coolingRate_K_s": g * r,
                 "gOverR_K_s_m2": g / r} for g, r in ((1e6, 0.4), (2e6, 0.1), (4e6, 0.2), (8e6, 0.05))]
        summary = se.thermal_summary({"samples": rows})
        separate = summary["thermalGradient"]["median"] * summary["normalSpeed"]["median"]
        self.assertNotAlmostEqual(summary["coolingRate"]["median"] / separate, 1.0, places=3)
        self.assertEqual(summary["coolingRate"]["median"], se.weighted_median([r["coolingRate_K_s"] for r in rows],
                                                                              [1.0] * 4))

    def test_below_three_samples_has_no_branch_summary(self):
        rows = [{"valid": True, "weight_m": 1.0, "G_K_m": 1.0, "R_m_s": 1.0, "coolingRate_K_s": 1.0,
                 "gOverR_K_s_m2": 1.0}] * 2
        self.assertIsNone(se.thermal_summary({"samples": rows}))


class Spacing(unittest.TestCase):
    def test_mitchell_sdas_fails_the_ni_capillary_gate(self):
        value, tag, raw = se.gated_spacing("in718", "sdas", 1e7, 0.1)
        self.assertIsNone(value)
        self.assertEqual(tag, "below-capillary-limit")
        self.assertAlmostEqual(raw * 1e6, 19.5 * 1e6 ** -0.63, places=12)

    def test_removing_the_capillary_gate_would_admit_the_tiny_scale(self):
        with mock.patch.object(se, "capillary_cutoff", lambda p, G, R: 0.0):
            value, tag, _ = se.gated_spacing("in718", "sdas", 1e7, 0.1)
        self.assertIsNotNone(value)

    def test_every_alloy_and_spacing_has_a_tiny_output_refusal(self):
        for alloy in se.SPACING:
            for kind in ("pdas", "sdas"):
                with self.subTest(alloy=alloy, kind=kind):
                    G, R = 2e7, 0.2
                    real = se.raw_spacing(alloy, kind, G, R)
                    tiny = {"hunt": 1e-12, "kurzFisher": 1e-12} if isinstance(real, dict) else 1e-12
                    with mock.patch.object(se, "raw_spacing", lambda *args, **kw: tiny):
                        value, tag, raw = se.gated_spacing(alloy, kind, G, R)
                    self.assertIsNone(value)
                    self.assertEqual(tag, "below-capillary-limit")
                    self.assertEqual(raw, tiny)  # kept only as a rejected-model diagnostic

    def test_source_law_algebra(self):
        self.assertAlmostEqual(se.raw_spacing("ti6al4v", "pdas", 1e6, 0.1) * 1e6, (699 - 62 * 6) * 1e5 ** -0.39)
        self.assertAlmostEqual(se.raw_spacing("alsi10mg", "sdas", 1e6, 0.1) * 1e6, 22 * 100 ** (-2 / 3))
        self.assertAlmostEqual(se.raw_spacing("ss316l", "pdas", 1e6, 0.1) * 1e6, 80 * 1e5 ** -0.33)
        ni = se.raw_spacing("in718", "pdas", 1e7, 0.05)
        x = 1e7 ** -0.5 * 0.05 ** -0.25
        self.assertEqual(ni, {"hunt": se.NI_HUNT_A * x, "kurzFisher": se.NI_KF_A * x})
        self.assertIsNone(se.raw_spacing("in718", "pdas", 1e7, 0.99))  # above the binary absolute stability

    def test_capillary_cut_low_g_limit(self):
        p = dict(se.PROXIES["in718"])
        cut = se.capillary_cutoff(p, 1e-9, 0.1)
        self.assertAlmostEqual(cut * 1e6, 0.087, places=3)


class Morphology(unittest.TestCase):
    def test_durga_true_fraction_classes(self):
        self.assertEqual([se.cet_class(f) for f in (0.0048, 0.0055, 0.48, 0.50)],
                         ["columnar", "mixed", "mixed", "equiaxed"])
        self.assertAlmostEqual(-math.expm1(-0.0066), 0.0065782676, places=9)
        self.assertEqual(se.cet_class(-math.expm1(-0.0066)), "mixed")  # extended 0.0066 is not the true 0.0049 cut

    def test_aluminium_tip_at_the_eutectic_is_refused_and_slow_growth_is_admitted(self):
        fast = se.morphology("alsi10mg", 1e6, 0.1)
        self.assertEqual(fast["refusal"], "tip-reaches-eutectic")
        self.assertAlmostEqual(fast["tip_K"], 36.84, places=2)
        self.assertGreater(fast["chi"], 1.0)
        slow = se.morphology("alsi10mg", 1e5, 0.001)
        self.assertIsNone(slow["refusal"])
        self.assertIn(slow["class"], ("columnar", "mixed", "equiaxed"))

    def test_planar_stable_point_keeps_chi_and_refuses_the_grain_model(self):
        planar = se.morphology("in718", 1e9, 1e-4)
        self.assertLessEqual(planar["chi"], 1.0)
        self.assertIsNone(planar["fraction"])

    def test_peclet_diagnostic_in_every_alloy(self):
        for alloy in se.PROXIES:
            with self.subTest(alloy=alloy):
                m = se.morphology(alloy, 1e7, 0.05)
                p = se.PROXIES[alloy]
                self.assertAlmostEqual(m["tipRadius_m"], 4 * p["gamma"] / m["tip_K"])
                self.assertAlmostEqual(m["peclet"], 0.05 * m["tipRadius_m"] / (2 * p["d"]))

    def test_316l_tip_bound(self):
        self.assertIsNone(se.morphology("ss316l", 1e7, 0.05)["refusal"])
        self.assertIsNotNone(se.morphology("ss316l", 1e7, 0.2)["refusal"])


class Phases(unittest.TestCase):
    def test_km_arithmetic(self):
        self.assertAlmostEqual(se.km_fraction(50.0), 0.92756024, places=8)
        self.assertEqual(se.km_fraction(575.0), 0.0)

    def test_km_path_gates(self):
        sample = {"position_m": {"x": 0.0, "z": 0.0}}
        hot = lambda x, y, z: 80.0 + 1700.0 * math.exp(x / 1e-3)  # monotone cooling behind the source
        path = se.km_path(hot, sample, 1.0, 80.0)
        self.assertAlmostEqual(se._t(hot, -path["time_s"], 0.0, 0.0), 105.0, places=5)
        reheating = lambda x, y, z: 1700.0 if x > -1e-4 else 1800.0
        with self.assertRaisesRegex(ValueError, "reheating"):
            se.km_path(reheating, sample, 1.0, 80.0)
        slow = lambda x, y, z: 80.0 + 1700.0 * math.exp(x / 1e-3)
        with self.assertRaisesRegex(ValueError, "slow-cooling"):
            se.km_path(slow, sample, 1e-4, 80.0)
        cold = lambda x, y, z: 900.0
        with self.assertRaisesRegex(ValueError, "missing-beta-initialization"):
            se.km_path(cold, sample, 1.0, 80.0)

    def test_al_references(self):
        eq = se.al_equilibrium()
        self.assertAlmostEqual(eq["alphaAl"], 0.8955, places=12)
        self.assertAlmostEqual(eq["Si"], 0.097400072, places=8)
        self.assertAlmostEqual(eq["Mg2Si"], 0.007099928, places=8)
        sc = se.al_scheil()
        self.assertAlmostEqual(sc["primaryAlphaAl"], 0.23328924, places=8)
        with self.assertRaisesRegex(ValueError, "hypereutectic"):
            se.al_scheil(13.0)


class Tier(unittest.TestCase):
    def test_tier_rule_and_its_caps(self):
        self.assertEqual(se.estimate_tier(False, [], True, True), "no-value")
        self.assertEqual(se.estimate_tier(True, [], True, True), "Estimated")
        self.assertEqual(se.estimate_tier(True, [], False, True), "Physics estimate")
        self.assertEqual(se.estimate_tier(True, [], True, False), "Physics estimate")
        for code in qe.TIER_CAPPING_WARNING_CODES:
            self.assertEqual(se.estimate_tier(True, [code], True, True), "Physics estimate", code)
        for code in qe.NON_CAPPING_WARNING_CODES:
            self.assertEqual(se.estimate_tier(True, [code], True, True), "Estimated", code)

    def test_an_in_domain_closure_with_a_complete_band_reaches_estimated(self):
        b = se.Builder()
        b.add_input("absorptivity", qe.input_record("sourceDefault", "x", status="inRange", source_locator="loc"))
        band = {"lower": 0.9e7, "upper": 1.2e7, "unit": "K/m", "construction": "ofat",
                "inputRanges": [{"name": "absorptivity", "unit": "1", "nominal": 0.3, "lower": 0.15, "upper": 0.45}],
                "armIds": ["nominal", "absorptivity:low", "absorptivity:high"],
                "unknownComponents": ["model-error", "input-interactions"]}
        q = b.value("thermalGradient", "liquidus-front-thermal-gradient", 1e7, depends_on=("absorptivity",),
                    sources=[se.SRC_GHOSH_KINEMATICS], explanation="x", construction="y", band=band)
        self.assertEqual(q["validity"]["estimateTier"], "Estimated")
        c = qe.container(b.quantities, input_provenance=b.inputs, schema=qe.ENVELOPE_SCHEMA_V2)
        self.assertEqual(qe.container_problems(c, "c"), [])
        laundered = copy.deepcopy(c)
        laundered["inputProvenance"]["absorptivity"]["status"] = "extrapolated"
        self.assertTrue(any("caps the value" in p for p in qe.container_problems(laundered, "c")))


class Channel(unittest.TestCase):
    def test_default_thermal_values_are_uncalibrated_estimates_for_every_alloy(self):
        for alloy, (material, power, speed) in CONDUCTION.items():
            with self.subTest(alloy=alloy):
                r = run(material, power, speed)
                self.assertEqual(qe.container_problems(r, "c"), [])
                self.assertEqual(r["quantityEnvelopeSchema"], qe.ENVELOPE_SCHEMA_V2)
                for name in ("thermalGradient", "normalSpeed", "coolingRate", "gOverR"):
                    q = r["quantities"][name]
                    self.assertIsNotNone(q["value"], name)
                    v = q["validity"]
                    self.assertEqual(v["estimateTier"], "Physics estimate")
                    self.assertEqual(v["tierLabel"], "Uncalibrated estimate")
                    self.assertEqual(v["displaySignificantDigits"], 2)
                    self.assertIsNone(v["estimateBand"])
                    self.assertEqual(v["uncertaintyStatement"], qe.UNCERTAINTY_STATEMENT_TIER2)
                    self.assertIn("domain-extrapolation", {w["code"] for w in v["domainWarnings"]})
                    self.assertTrue(v["explanation"].startswith("Uncalibrated estimate"))
                    self.assertEqual(q["physicalValidation"], qe.PHYSICAL_VALIDATION)
                cooling = r["quantities"]["coolingRate"]["value"]
                rows = se.valid_samples(r["front"])
                self.assertEqual(cooling, se.weighted_median([s["coolingRate_K_s"] for s in rows],
                                                             [s["weight_m"] for s in rows]))

    def test_family_transfer_warning_on_alsi10mg_and_316l(self):
        for alloy in ("alsi10mg", "ss316l"):
            r = run(*CONDUCTION[alloy])
            codes = {w["code"] for w in r["quantities"]["thermalGradient"]["validity"]["domainWarnings"]}
            self.assertIn("alloy-family-transfer", codes, alloy)

    def test_keyhole_leg_default_is_the_labelled_conduction_surrogate(self):
        # Ti64 specimen default case (280 W, 940 mm/s, 80 um, preheat 200 C): the Fabbro leg sets the served depth.
        r = se.compute_solidification_estimates({"params": {**BASE, "materialName": "Ti-6Al-4V", "power_W": 280.0,
                                                            "speed_mm_s": 940.0, "preheat_C": 200.0}})
        self.assertEqual(qe.container_problems(r, "c"), [])
        self.assertTrue(r["thermalParent"]["keyholeLegSetsDepth"])
        self.assertEqual(r["surrogate"], "conduction-field")
        self.assertEqual(r["surrogateIdentity"]["id"], se.SURROGATE_ID)
        self.assertEqual(r["surrogateIdentity"]["selection"], "default")
        self.assertIs(r["default"], False)  # never the default physical arm, never a computed keyhole front
        self.assertTrue(r["inputProvenance"]["frontSamples"]["sourceId"].startswith(f"front-samples-{se.SURROGATE_ID}:"))
        for name, q in r["quantities"].items():
            with self.subTest(name):
                if name in ("thermalGradient", "normalSpeed", "coolingRate", "gOverR", "pdas", "sdas",
                            "planarStabilityIndex", "equiaxedEnvelopeFraction", "cetClass", "kmAlphaMFraction"):
                    self.assertIsNotNone(q["value"])
                if q["value"] is not None:
                    self.assertEqual(q["validity"]["estimateTier"], "Physics estimate")
                    details = [w["detail"] for w in q["validity"]["domainWarnings"]]
                    self.assertEqual(details[0], se.KEYHOLE_SURROGATE_WARNING)
        stripped = copy.deepcopy(r)
        stripped["quantities"]["pdas"]["validity"]["domainWarnings"] = [
            w for w in stripped["quantities"]["pdas"]["validity"]["domainWarnings"] if w["code"] != "domain-extrapolation"]
        self.assertTrue(qe.container_problems(stripped, "c"))

    def test_the_surrogate_can_be_turned_off(self):
        off = run("Ti-6Al-4V", 200.0, 1000.0, conductionSurrogate=False)
        self.assertEqual(qe.container_problems(off, "c"), [])
        g = off["quantities"]["thermalGradient"]
        self.assertIsNone(g["value"])
        self.assertEqual(g["reasons"][0]["code"], "keyhole-field-inconsistent")
        self.assertIn("conduction-field surrogate", g["validity"]["noValueText"])
        self.assertIsNone(off["surrogate"])
        explicit = run("Ti-6Al-4V", 200.0, 1000.0, conductionSurrogate=True)
        self.assertEqual(explicit["surrogateIdentity"]["selection"], "requested")
        q = explicit["quantities"]["thermalGradient"]
        self.assertTrue(q["validity"]["explanation"].startswith("Uncalibrated estimate from a conduction-field"))

    def test_refusals_still_refuse_with_the_surrogate_on(self):
        # Microstructure gate: IN718 SDAS fails the capillary gate on a keyhole-leg case with the surrogate on.
        ni = se.compute_solidification_estimates({"params": {**BASE, "materialName": "Inconel 718", "power_W": 280.0,
                                                             "speed_mm_s": 940.0}})
        self.assertTrue(ni["thermalParent"]["keyholeLegSetsDepth"])
        self.assertEqual(ni["surrogate"], "conduction-field")
        self.assertIsNone(ni["quantities"]["sdas"]["value"])
        self.assertEqual(ni["quantities"]["sdas"]["reasons"][0]["code"], "outside-source-model-domain")
        self.assertEqual(ni["quantities"]["phaseInventory"]["reasons"][0]["code"], "missing-source-bound-model")
        # Invalid derivatives: a zero-gradient field gives no eligible tuple and no summary, keyhole warning or not.
        with mock.patch.object(se, "gradient", lambda *args: (0.0, 0.0, 0.0)):
            bad = se.compute_solidification_estimates({"params": {**BASE, "materialName": "Ti-6Al-4V",
                                                                  "power_W": 280.0, "speed_mm_s": 940.0}})
        self.assertEqual(qe.container_problems(bad, "c"), [])
        for name in ("thermalGradient", "pdas", "kmAlphaMFraction"):
            self.assertIsNone(bad["quantities"][name]["value"], name)
        # Missing phase history: a slow scan fails the KM cooling-history gate under the surrogate.
        slow = se.compute_solidification_estimates({"params": {**BASE, "materialName": "Ti-6Al-4V", "power_W": 200.0,
                                                               "speed_mm_s": 200.0}})
        km = slow["quantities"]["kmAlphaMFraction"]
        self.assertIsNone(km["value"])
        self.assertEqual(km["reasons"][0]["code"], "missing-thermal-history")

    def test_insufficient_interface_support_refuses_on_the_keyhole_leg_with_the_surrogate_on(self):
        # Too few valid interface points (two of the required three) on a keyhole-leg case with the surrogate on.
        # The Al eutectic gate is deliberately not forced onto the keyhole leg: it is not reachable at 370 to 500 W.
        real = se.valid_samples
        with mock.patch.object(se, "valid_samples", lambda front: real(front)[:2]):
            few = se.compute_solidification_estimates({"params": {**BASE, "materialName": "Ti-6Al-4V",
                                                                  "power_W": 280.0, "speed_mm_s": 940.0}})
        self.assertTrue(few["thermalParent"]["keyholeLegSetsDepth"])
        self.assertEqual(few["surrogate"], "conduction-field")
        self.assertEqual(qe.container_problems(few, "c"), [])
        for name in ("thermalGradient", "normalSpeed", "coolingRate", "gOverR"):
            q = few["quantities"][name]
            self.assertIsNone(q["value"], name)
            self.assertEqual(q["reasons"][0]["code"], "insufficient-sample-support", name)
        self.assertIsNone(few["quantities"]["pdas"]["value"])
        self.assertEqual(few["quantities"]["thermalGradient"]["validity"]["noValueText"], se.FEW_POINTS_TEXT)
        self.assertEqual(len(few["quantities"]["thermalGradient"]["validity"]["localPoints"]), 2)

    def test_constructive_no_value_texts(self):
        al = run(*CONDUCTION["alsi10mg"])
        self.assertEqual(al["quantities"]["equiaxedEnvelopeFraction"]["validity"]["noValueText"], se.AL_EUTECTIC_TEXT)
        ni = run(*CONDUCTION["in718"])
        self.assertEqual(ni["quantities"]["sdas"]["validity"]["noValueText"], se.CAPILLARY_TEXT)
        self.assertEqual(ni["quantities"]["phaseInventory"]["validity"]["noValueText"], se.PHASE_NO_MODEL_TEXT["in718"])
        for r in (al, ni, run(*CONDUCTION["ss316l"])):
            for name, q in r["quantities"].items():
                if q["value"] is None:
                    self.assertTrue(q["validity"]["noValueText"], name)
                    self.assertNotEqual(q["validity"]["noValueText"], "Unavailable")

    def test_ti64_km_and_al_phase_routes(self):
        ti = run(*CONDUCTION["ti6al4v"])
        km = ti["quantities"]["kmAlphaMFraction"]
        self.assertAlmostEqual(km["value"], se.km_fraction(105.0))
        self.assertEqual(km["evaluation"]["temperature_K"], 80.0 + 25.0 + se.KELVIN)
        self.assertNotIn("retained beta", km["validity"]["explanation"].replace("not an estimate of retained beta", ""))
        al = run(*CONDUCTION["alsi10mg"])
        self.assertEqual(al["quantities"]["equilibriumPhaseInventory"]["fractionBasis"], "mass")
        self.assertIn("microconstituent-not-phase", {w["code"] for w in al["quantities"]["scheilMicroconstituents"]
                                                     ["validity"]["domainWarnings"]})
        sdas = ti["quantities"]["sdas"]
        self.assertIn(se.SECONDARY_ARMS, sdas["validity"]["explanation"])

    def test_mutated_payloads_are_rejected_by_the_v2_validator(self):
        base = run(*CONDUCTION["ti6al4v"])
        mutations = {
            "tier laundering": lambda c: c["quantities"]["thermalGradient"]["validity"].update(
                estimateTier="Estimated"),
            "lost inherited warning": lambda c: c["quantities"]["thermalGradient"]["validity"].update(
                domainWarnings=[]),
            "warning as reason": lambda c: c["quantities"]["sdas"]["reasons"].append(
                {"code": "domain-extrapolation", "params": {}, "parent": None}),
            "precision": lambda c: c["quantities"]["coolingRate"]["validity"].update(displaySignificantDigits=4),
            "statement": lambda c: c["quantities"]["gOverR"]["validity"].update(uncertaintyStatement="Fine."),
            "km offset": lambda c: c["quantities"]["kmAlphaMFraction"]["evaluation"].update(offset_K=20.0),
            "retained beta": lambda c: c["quantities"]["kmAlphaMFraction"].update(
                residual={"retainedBeta": 0.1, "beta0": 1.0, "preExistingConstituent": 0.0}),
            "nucleation note": lambda c: c["quantities"]["equiaxedEnvelopeFraction"]["validity"].pop(
                "nucleationScenarioNote"),
            "stale samples": lambda c: c["inputProvenance"]["frontSamples"].update(sourceId="front-samples:other"),
            "v1 schema": lambda c: c.update(quantityEnvelopeSchema=qe.ENVELOPE_SCHEMA),
        }
        for name, mutate in mutations.items():
            with self.subTest(name):
                payload = copy.deepcopy(base)
                mutate(payload)
                self.assertTrue(qe.container_problems(payload, "c"), name)

    def test_v1_registry_stays_closed(self):
        for definition in qe.V2_NEW_DEFINITIONS:
            self.assertNotIn(definition, qe.QUANTITY_DEFINITIONS)

    def test_refusals(self):
        self.assertEqual(se.compute_solidification_estimates({"params": {**BASE, "materialName": "Unobtainium",
                                                                         "power_W": 1, "speed_mm_s": 1}})
                         ["refusal"]["code"], "unknown-alloy-alias")
        bad = se.compute_solidification_estimates({"params": {**BASE, "materialName": "AlSi10Mg", "power_W": -1,
                                                              "speed_mm_s": 900}})
        self.assertEqual(bad["refusal"]["code"], "nonphysical-input")
        self.assertEqual(qe.container_problems(bad, "c"), [])

    def test_input_sensitivity_is_auxiliary_full_field_and_capped(self):
        r = run(*CONDUCTION["alsi10mg"], inputSensitivity=True)
        run_record = r["inputSensitivityRun"]
        self.assertTrue(run_record["complete"])
        self.assertEqual(len(run_record["arms"]), 10)
        absorptivity = next(row for row in run_record["inputRanges"] if row["name"] == "absorptivity")
        self.assertAlmostEqual(absorptivity["lower"], 0.5 * absorptivity["nominal"])
        self.assertAlmostEqual(absorptivity["upper"], min(1.0, 1.5 * absorptivity["nominal"]))
        g = r["quantities"]["thermalGradient"]
        self.assertIsNone(g["validity"]["estimateBand"])
        aux = g["validity"]["inputSensitivity"]
        self.assertLessEqual(aux["lower"], g["value"])
        self.assertGreaterEqual(aux["upper"], g["value"])
        self.assertIn("input-interactions", aux["unknownComponents"])
        tl_low, tl_high = (run_record["arms"][f"liquidus_K:{side}"]["summary"]["thermalGradient"]
                           for side in ("low", "high"))
        self.assertNotEqual(tl_low, tl_high)  # the threshold arm recomputed its own branch
        self.assertEqual(qe.container_problems(r, "c"), [])


def _builder_with_rows(G, R, n=5):
    b = se.Builder()
    b.add_input("frontSamples", qe.input_record("derived", "front-samples:manufactured", status="inRange",
                                                source_locator="manufactured tuples", source_evidence_kind="Literature estimate"))
    rows = [{"valid": True, "weight_m": 1.0, "G_K_m": G * (1 + 0.01 * i), "R_m_s": R, "coolingRate_K_s": G * R,
             "gOverR_K_s_m2": G / R, "sampleId": f"m:{i}"} for i in range(n)]
    return b, rows


class DirectWarnings(unittest.TestCase):
    def test_spacing_family_transfer_warning_is_emitted(self):
        for alloy in ("alsi10mg", "ss316l"):
            with self.subTest(alloy=alloy):
                b, rows = _builder_with_rows(5e6, 0.5)
                se._spacing_quantities(b, alloy, rows, True, None)
                expected = f"{se.SPACING[alloy]['domain']} transferred to {se.ALLOY_NAMES[alloy]}"
                for name in ("pdas", "sdas"):
                    q = b.quantities[name]
                    self.assertIsNotNone(q["value"], name)
                    self.assertIn({"code": "alloy-family-transfer", "detail": expected}, q["validity"]["domainWarnings"])
        b, rows = _builder_with_rows(5e6, 0.5)
        se._spacing_quantities(b, "ti6al4v", rows, True, None)
        self.assertFalse(any(w["detail"].endswith("transferred to Ti-6Al-4V")
                             for w in b.quantities["pdas"]["validity"]["domainWarnings"]))

    def test_peclet_warning_is_emitted_only_above_the_screening_trigger(self):
        b, rows = _builder_with_rows(1e6, 0.01)
        se._morphology_quantities(b, "in718", rows, True, None)
        q = b.quantities["equiaxedEnvelopeFraction"]
        self.assertIsNotNone(q["value"])
        pe = max(se.morphology("in718", r["G_K_m"], r["R_m_s"])["peclet"] for r in rows)
        self.assertGreaterEqual(pe, 0.1)
        codes = [w["code"] for w in q["validity"]["domainWarnings"]]
        self.assertIn("low-peclet-tip-law", codes)
        self.assertIn("low-peclet-tip-law", [w["code"] for w in b.quantities["cetClass"]["validity"]["domainWarnings"]])
        b, rows = _builder_with_rows(1e6, 1e-3)
        se._morphology_quantities(b, "in718", rows, True, None)
        q = b.quantities["equiaxedEnvelopeFraction"]
        self.assertIsNotNone(q["value"])
        self.assertNotIn("low-peclet-tip-law", [w["code"] for w in q["validity"]["domainWarnings"]])


class Fixtures(unittest.TestCase):
    def test_committed_ts_fixtures_are_current(self):
        result = subprocess.run([sys.executable, "-B", str(ROOT / "python/tools/solidification_estimate_fixtures.py"),
                                 "--check"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
