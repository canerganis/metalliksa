"""Offline checks for the 316L (Gan SS316) and IN718 (Fang thermal + pure-Ni vapor) proxy profiles and vapor law.

Software/numerical behaviour and source transcription only; not physical validation.
Pinned constants are typed here from the sources (Gan 2021 SI Table 1 p. 20 SS316 column;
Fang 2021 SI Tables 2, 4, 7; Knapp 2019 Table 3 Ni row; NIST Ni 58.6934; Mills 2002 IN718
Table 1), so the test does not trust the module's own numbers.
"""

import copy
from dataclasses import FrozenInstanceError
import math
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lpbf_al_proxy_evaporation as al  # noqa: E402
import lpbf_proxy_evaporation as vapor  # noqa: E402
from lpbf_proxy_vapor_profiles import IN718_PROFILE, PROFILES, SS316L_PROFILE  # noqa: E402
import lpbf_ti64_evaporation as ti64  # noqa: E402
from lpbf_material_registry import material  # noqa: E402

R = 8.31446261815324
# key: (Tv, Lv J/kg, M kg/mol, liquidus, low, high, sigma)
CASES = {
    "ss316l": (3122.0, 6.336e6, 0.056, 1723.0, 3022.0, 3522.0, 1.87),
    "in718": (3183.0, 374.3e3 / 0.0586934, 0.0586934, 1609.0, 3083.0, 3583.0, 1.882),
}


def scenario(key, **changes):
    tv, lv, m, liq, low, high, sigma = CASES[key]
    raw = dict(transitionLow_K=low, transitionHigh_K=high, ambientPressure_Pa=101325.0,
               returnFraction=0.18, surfaceTension_N_m=sigma, maxTemperature_K=5000.0)
    raw.update(changes)
    return raw


def psat(key, temperature):
    tv, lv, m = CASES[key][:3]
    return 101325.0 * math.exp(lv * m / R * (1 / tv - 1 / temperature))


def config(key, **changes):
    return vapor.validate_config(scenario(key, **changes), CASES[key][3], PROFILES[key])


class ProfileTests(unittest.TestCase):
    def test_ss316_constants_match_gan_table1_transcription(self):
        expected = {
            "density, solid branch": 7950.0, "density, liquid branch": 6881.0,
            "heat capacity, solid branch": "0.24T+420.8", "heat capacity, liquid branch": 790.0,
            "thermal conductivity, solid branch": "0.0146T+10.3", "thermal conductivity, liquid branch": 26.9,
            "solidus temperature": 1658.0, "liquidus temperature": 1723.0, "latent heat of melting": 2.6e5,
            "vaporization point": 3122.0, "latent heat of vaporization": 6.336e6, "molar mass": 0.056,
            "surface tension": 1.87, "thermocapillary coefficient": -4.9e-4, "emissivity": 0.3,
            "dynamic viscosity": 8e-3, "retro-diffusion coefficient": 0.18, "absorptivity": 0.30,
        }
        rows = {row["quantity"]: row for row in SS316L_PROFILE.sourceProfile["constants"]}
        self.assertEqual(set(rows), set(expected))
        for name, value in expected.items():
            with self.subTest(name=name):
                self.assertEqual(rows[name]["value"], value)
                self.assertTrue(rows[name]["locator"] and rows[name]["source"])
                if name != "absorptivity":
                    self.assertIn("printed p. 2", rows[name]["locator"])
        self.assertIn("Trapp", rows["absorptivity"]["source"])
        self.assertEqual(SS316L_PROFILE.sourceProfile["recordedUnused"]["minimalAbsorptivity"], 0.33)

    def test_in718_constants_match_fang_knapp_nist_mills_transcription(self):
        rows = {row["quantity"]: row for row in IN718_PROFILE.sourceProfile["constants"]}
        self.assertEqual(rows["density"]["value"], 8100.0)
        self.assertEqual(rows["thermal conductivity and heat capacity nodes"]["value"],
                         [[293.0, 10.31, 362.0], [373.0, 11.88, 378.0], [473.0, 13.6, 400.0], [673.0, 16.6, 412.0],
                          [873.0, 20.1, 460.0], [1073.0, 26.3, 544.0], [1573.0, 30.75, 583.0]])
        self.assertEqual((rows["solidus temperature"]["value"], rows["liquidus temperature"]["value"],
                          rows["latent heat of fusion"]["value"], rows["emissivity"]["value"]),
                         (1533.0, 1609.0, 2.72e5, 0.45))
        self.assertEqual((rows["Ni boiling point"]["value"], rows["Ni heat of vaporization"]["value"],
                          rows["Ni molar mass"]["value"]), (3183.0, 374.3e3, 0.0586934))
        self.assertIn("Ni", rows["Ni boiling point"]["locator"])
        self.assertAlmostEqual(IN718_PROFILE.latentHeat_J_kg, 6.3772e6, delta=100)
        self.assertEqual(rows["surface tension"]["value"], 1.882)
        self.assertIn("1336 C", rows["surface tension"]["locator"])
        self.assertEqual(rows["absorptivity"]["value"], 0.32)
        unused = IN718_PROFILE.sourceProfile["recordedUnused"]
        self.assertEqual((unused["fangBoilingPoint_K"], unused["fangEvaporatingSpeciesMolarMass_kg_mol"]),
                         (3120.0, 166.534e-3))
        self.assertIn("not used", unused["status"])

    def test_material_tables_follow_sources_and_registry_accepts_them(self):
        m = material("316L Stainless Steel", SS316L_PROFILE.materialProperties())
        table = np.asarray(m["table"])
        for t in (273.15, 800.0, 1658.0, 1700.0, 1722.0):
            self.assertAlmostEqual(np.interp(t, table[:, 0], table[:, 2]), 0.0146 * t + 10.3, places=9)
            self.assertAlmostEqual(np.interp(t, table[:, 0], table[:, 3]), 0.24 * t + 420.8, places=9)
        for t in (1723.0, 2500.0, 3122.0):
            self.assertEqual([np.interp(t, table[:, 0], table[:, c]) for c in (1, 2, 3)], [6881.0, 26.9, 790.0])
        self.assertEqual((m["solidus_K"], m["liquidus_K"], m["boiling_K"], m["absorptivity"], m["emissivity"]),
                         (1658.0, 1723.0, 3122.0, 0.30, 0.3))
        m = material("Inconel 718", IN718_PROFILE.materialProperties())
        table = np.asarray(m["table"])
        self.assertEqual(np.interp(1000.0, table[:, 0], table[:, 2]), 20.1 + (26.3 - 20.1) * 127 / 200)
        for t in (1573.0, 1609.0, 2500.0, 3183.0):
            self.assertEqual([np.interp(t, table[:, 0], table[:, c]) for c in (1, 2, 3)], [8100.0, 30.75, 583.0])
        self.assertEqual((m["solidus_K"], m["liquidus_K"], m["boiling_K"], m["latentHeat_J_kg"], m["absorptivity"],
                          m["emissivity"], m["dGamma_dT"]), (1533.0, 1609.0, 3183.0, 2.72e5, 0.32, 0.45, -1.1e-4))
        props = IN718_PROFILE.materialProperties()
        props["table"][0][1] = 1.0
        self.assertEqual(IN718_PROFILE.materialProperties()["table"][0][1], 8100.0)  # fresh object

    def test_disclosures_name_transfers_and_unmodelled_physics(self):
        for profile, phrase in ((SS316L_PROFILE, "SS316 values"), (IN718_PROFILE, "pure Ni")):
            for text in (phrase, "selective evaporation", "composition change", "plume and keyhole geometry",
                         "not an observed keyhole"):
                self.assertIn(text, profile.disclosure)
        self.assertIn("constant above 1573 K", IN718_PROFILE.disclosure)

    def test_generic_law_reproduces_the_alsi10mg_proxy_law_bitwise(self):
        # Proof that the AlSi10Mg proxy is expressible with this module without numeric change.
        defaults = dict(transitionLow_K=2800.0, transitionHigh_K=3200.0, ambientPressure_Pa=101325.0,
                        returnFraction=0.18, maxTemperature_K=5000.0, surfaceTension_N_m=0.91)
        basis = {k: dict(kind="sourced", note="test") for k in vapor.SCENARIO_KEYS}
        profile = vapor.make_profile(key="al", target_alloy="AlSi10Mg", vaporization_K=2792.0, latent_heat_J_kg=1.053e7,
                                     molar_mass_kg_mol=0.027, disclosure="test", source_profile={},
                                     scenario_defaults=defaults, scenario_basis=basis, material_properties=dict)
        temperatures = np.linspace(300.0, 5000.0, 4001)
        generic = vapor.surface_state(temperatures, vapor.validate_config(defaults, 915.0, profile))
        original = al.surface_state(temperatures, al.validate_config(defaults, 915.0))
        for key in original:
            self.assertTrue(np.array_equal(generic[key], original[key]), key)


class VaporLawTests(unittest.TestCase):
    def test_high_law_matches_independent_maxwellian_quadrature(self):
        nodes, weights = np.polynomial.legendre.leggauss(160)
        speed = 6.0 * (nodes + 1.0)
        integral = float(np.sum(6.0 * weights * speed * np.exp(-speed**2 / 2.0)))
        for key in CASES:
            tv, lv, m, liq, low, high, sigma = CASES[key]
            for temperature in [high, 4000.0, 5000.0]:
                with self.subTest(key=key, temperature=temperature):
                    pressure = psat(key, temperature)
                    density = pressure * m / (R * temperature)
                    expected = 0.82 * density * math.sqrt(R * temperature / m) / math.sqrt(2 * math.pi) * integral
                    state = vapor.surface_state(temperature, config(key))
                    actual = float(state["mass_flux_kg_m2_s"])
                    self.assertLessEqual(abs(actual / expected - 1), 1e-8)
                    self.assertAlmostEqual(float(state["heat_flux_W_m2"]) / actual, lv)
                    self.assertAlmostEqual(float(state["recoil_pressure_Pa"]) / pressure, 0.59)

    def test_below_transition_is_exact_zero(self):
        for key in CASES:
            tv, lv, m, liq, low = CASES[key][:5]
            state = vapor.surface_state(np.array([1.0, 300.0, liq, tv - 200, low]), config(key))
            for name in ["mass_flux_kg_m2_s", "heat_flux_W_m2", "heat_flux_derivative_W_m2K"]:
                np.testing.assert_array_equal(state[name], np.zeros(5))
            np.testing.assert_array_equal(state["recoil_pressure_Pa"], np.full(5, 101325.0))

    def test_bridge_matches_independent_cubic_and_is_monotone(self):
        for key in CASES:
            tv, lv, m, liq, low, high = CASES[key][:6]
            width = high - low
            mass = .82 * psat(key, high) * math.sqrt(m / (2 * math.pi * R * high))
            mass_slope = mass * (lv * m / R / high**2 - .5 / high)
            recoil = .59 * psat(key, high)
            recoil_slope = recoil * lv * m / R / high**2
            for fraction in [.001, .1, .5, .9, .999]:
                state = vapor.surface_state(low + width * fraction, config(key))
                for name, low_value, high_value, slope in [("mass_flux_kg_m2_s", 0, mass, mass_slope),
                                                           ("recoil_pressure_Pa", 101325, recoil, recoil_slope)]:
                    a = 3 * (high_value - low_value) - width * slope
                    b = width * slope - 2 * (high_value - low_value)
                    with self.subTest(key=key, fraction=fraction, name=name):
                        self.assertAlmostEqual(float(state[name]) / (low_value + a * fraction**2 + b * fraction**3),
                                               1.0, places=12)
                        self.assertGreaterEqual(a, 0)
                        self.assertGreaterEqual(2 * a + 3 * b, 0)

    def test_value_and_derivative_continuity_at_both_thresholds(self):
        epsilon = 1e-4
        for key in CASES:
            tv, lv, m, liq, low, high = CASES[key][:6]
            heat_scale = (.82 * psat(key, high) * math.sqrt(m / (2 * math.pi * R * high))
                          * (lv * m / R / high**2 - .5 / high) * lv)
            pressure_scale = .59 * psat(key, high) * lv * m / R / high**2
            for boundary in [low, high]:
                with self.subTest(key=key, boundary=boundary):
                    state = vapor.surface_state([boundary - epsilon, boundary, boundary + epsilon], config(key))
                    heat, slope = state["heat_flux_W_m2"], state["heat_flux_derivative_W_m2K"]
                    self.assertLess(abs(float(heat[2] - heat[0])), 3 * epsilon * heat_scale)
                    self.assertLess(abs(float(slope[0] - slope[2])) / heat_scale, 1e-6)
                    self.assertLess(abs(float((heat[2] - heat[0]) / (2 * epsilon) - slope[1])) / heat_scale, 1e-6)
                    p = state["recoil_pressure_Pa"]
                    left, right = (p[1] - p[0]) / epsilon, (p[2] - p[1]) / epsilon
                    self.assertLess(abs(float(left - right)) / pressure_scale, 1e-6)

    def test_high_heat_derivative_matches_finite_difference(self):
        temperatures = np.array([3700.0, 4200.0, 4900.0])
        for key in CASES:
            c = config(key)
            derivative = (vapor.surface_state(temperatures + .001, c)["heat_flux_W_m2"]
                          - vapor.surface_state(temperatures - .001, c)["heat_flux_W_m2"]) / .002
            np.testing.assert_allclose(vapor.surface_state(temperatures, c)["heat_flux_derivative_W_m2K"],
                                       derivative, rtol=1e-8)

    def test_malformed_temperatures_and_foreign_configs_fail_without_clipping(self):
        c = config("ss316l")
        for temperatures in [-1, 0, float("nan"), float("inf"), 5000.001, True, "3500",
                             [True, 3500], np.array([3500 + 0j]), np.array([300, np.nan])]:
            with self.subTest(temperatures=temperatures), self.assertRaises(ValueError):
                vapor.surface_state(temperatures, c)
        ti_config = ti64.validate_config(dict(scenario("ss316l"), transitionLow_K=3560.0, transitionHigh_K=4000.0), 1923.0)
        al_config = al.validate_config(dict(scenario("ss316l"), transitionLow_K=2800.0, transitionHigh_K=3200.0), 915.0)
        for foreign in (ti_config, al_config):
            with self.assertRaises(ValueError):
                vapor.surface_state(3500.0, foreign)
        # The profile is bound into the config: the same scenario gives different laws per alloy.
        same = dict(transitionLow_K=3083.0, transitionHigh_K=3583.0)
        self.assertNotEqual(float(vapor.surface_state(4000.0, config("ss316l", **same))["mass_flux_kg_m2_s"]),
                            float(vapor.surface_state(4000.0, config("in718", **same))["mass_flux_kg_m2_s"]))


class ConfigurationTests(unittest.TestCase):
    def test_configuration_is_immutable_and_detached(self):
        raw = scenario("in718")
        c = vapor.validate_config(raw, 1609.0, IN718_PROFILE)
        raw["returnFraction"] = .8
        self.assertEqual(c.returnFraction, .18)
        with self.assertRaises((FrozenInstanceError, AttributeError, TypeError)):
            c.returnFraction = .8
        with self.assertRaises(TypeError):
            IN718_PROFILE.sourceProfile["sourceId"] = "other"
        with self.assertRaises(TypeError):
            IN718_PROFILE.scenarioDefaults["transitionLow_K"] = 1.0

    def test_bad_inputs_fail(self):
        for raw in [None, [], True, dict(scenario("ss316l"), surprise=0)]:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                vapor.validate_config(raw, 1723.0, SS316L_PROFILE)
        with self.assertRaises(ValueError):
            vapor.validate_config(scenario("ss316l"), 1723.0, "ss316l")
        for key in scenario("ss316l"):
            for bad in [True, "1", None, float("nan"), float("inf")]:
                with self.subTest(key=key, bad=bad), self.assertRaises(ValueError):
                    vapor.validate_config(scenario("ss316l", **{key: bad}), 1723.0, SS316L_PROFILE)
        for changes in [dict(returnFraction=1), dict(ambientPressure_Pa=0), dict(transitionLow_K=1700),
                        dict(transitionLow_K=3522), dict(transitionHigh_K=5001), dict(maxTemperature_K=6001),
                        dict(ambientPressure_Pa=1e9)]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                vapor.validate_config(scenario("ss316l", **changes), 1723.0, SS316L_PROFILE)
        with self.assertRaises(ValueError):
            vapor.make_profile(key="x", target_alloy="x", vaporization_K=1.0, latent_heat_J_kg=1.0,
                               molar_mass_kg_mol=1.0, disclosure="", source_profile={},
                               scenario_defaults={}, scenario_basis={}, material_properties=dict)


class EvidenceLabelTests(unittest.TestCase):
    def normalized(self, key, **changes):
        raw = scenario(key, **changes)
        return {k: float(v) for k, v in raw.items()}

    def test_unsourced_threshold_defaults_make_the_label_unresolved_and_name_them(self):
        for key in CASES:
            evidence = vapor.scenario_evidence(self.normalized(key), PROFILES[key])
            self.assertEqual(evidence["label"], "Unresolved")
            self.assertEqual(evidence["unresolvedInputs"], ["transitionLow_K", "transitionHigh_K"])
            self.assertIn("transitionLow_K and transitionHigh_K", evidence["summary"])
            self.assertEqual(evidence["inputBasis"]["transitionLow_K"]["kind"], "unsourced")
        self.assertEqual(vapor.scenario_evidence(self.normalized("ss316l"), SS316L_PROFILE)
                         ["inputBasis"]["returnFraction"]["kind"], "sourced")
        self.assertEqual(vapor.scenario_evidence(self.normalized("in718"), IN718_PROFILE)
                         ["inputBasis"]["returnFraction"]["kind"], "transferred")

    def test_unresolved_precedes_user_input_and_user_thresholds_become_user_input(self):
        evidence = vapor.scenario_evidence(self.normalized("in718", returnFraction=0.1), IN718_PROFILE)
        self.assertEqual((evidence["label"], evidence["userInputs"]), ("Unresolved", ["returnFraction"]))
        evidence = vapor.scenario_evidence(self.normalized("in718", transitionLow_K=3100.0, transitionHigh_K=3600.0),
                                           IN718_PROFILE)
        self.assertEqual((evidence["label"], evidence["unresolvedInputs"], evidence["userInputs"]),
                         ("User input", [], ["transitionLow_K", "transitionHigh_K"]))
        raw = self.normalized("ss316l"); del raw["surfaceTension_N_m"]
        self.assertEqual(vapor.scenario_evidence(raw, SS316L_PROFILE)["inputBasis"]["surfaceTension_N_m"]["status"],
                         "omitted")


class OnsetTests(unittest.TestCase):
    def state(self, excess, mass=1.0):
        return {"mass_flux_kg_m2_s": np.array([mass]), "recoil_pressure_Pa": np.array([101325.0 + excess])}

    def test_threshold_uses_radius_with_equality_latching(self):
        c = config("ss316l")  # 2*1.87/50e-6 = 74800 Pa
        for excess, expected in [(74799., False), (74800., True), (74801., True)]:
            with self.subTest(excess=excess):
                gate = vapor.update_onset(None, self.state(excess), c, 50e-6, 0)
                self.assertEqual(gate["onset"], expected)
                self.assertEqual(gate["geometryAvailable"], not expected)

    def test_latch_survives_cooling_and_candidate_does_not_mutate_previous(self):
        c = config("in718")
        clear = vapor.update_onset(None, self.state(0), c, 50e-6, 0)
        snapshot = copy.deepcopy(clear)
        candidate = vapor.update_onset(clear, self.state(75280), c, 50e-6, .1)
        self.assertEqual(clear, snapshot)
        cooled = vapor.update_onset(candidate, vapor.surface_state([300], c), c, 50e-6, .2)
        self.assertEqual(cooled, candidate)
        self.assertTrue(cooled["onset"])

    def test_missing_sigma_latches_unresolved(self):
        raw = scenario("in718"); del raw["surfaceTension_N_m"]
        c = vapor.validate_config(raw, 1609.0, IN718_PROFILE)
        gate = vapor.update_onset(None, vapor.surface_state([3300.0], c), c, 50e-6, .1)
        self.assertTrue(gate["unresolvedGeometry"])
        self.assertFalse(gate["geometryAvailable"])


if __name__ == "__main__":
    unittest.main()
