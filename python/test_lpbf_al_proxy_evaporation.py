"""Offline checks for the Al6061-proxy profile and Al-species vapor law (AlSi10Mg research model).

Software/numerical behaviour and source transcription only; not AlSi10Mg physical validation.
Pinned constants are transcribed here from Gan 2021 SI Table 1 (printed p. 20) and Table 2
(printed p. 21), Al6061 column, so the test does not trust the module's own numbers.
"""

import copy
from dataclasses import FrozenInstanceError
import math
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lpbf_al_proxy_evaporation as vapor  # noqa: E402
import lpbf_ti64_evaporation as ti64  # noqa: E402
from lpbf_material_registry import material  # noqa: E402

R = 8.31446261815324
TV, LV, M = 2792.0, 1.053e7, 0.027


def scenario(**changes):
    raw = dict(transitionLow_K=2800.0, transitionHigh_K=3200.0,
               ambientPressure_Pa=101325.0, returnFraction=0.18,
               surfaceTension_N_m=0.91, maxTemperature_K=5000.0)
    raw.update(changes)
    return raw


def psat(temperature):
    return 101325.0 * math.exp(LV * M / R * (1 / TV - 1 / temperature))


class ProfileTests(unittest.TestCase):
    def test_constants_match_gan_table_transcription(self):
        expected = {  # Table 1 (p. 20) and Table 2 (p. 21), Al6061.
            "density, solid branch": 2705.0, "density, liquid branch": 2415.0,
            "heat capacity, solid branch": "0.486T+725", "heat capacity, liquid branch": 1170.0,
            "thermal conductivity, solid branch": "0.091T+152.5", "thermal conductivity, liquid branch": 90.0,
            "solidus temperature": 873.0, "liquidus temperature": 915.0,
            "latent heat of melting": 3.8e5, "vaporization point": 2792.0,
            "latent heat of vaporization": 1.053e7, "molar mass": 0.027,
            "surface tension": 0.91, "thermocapillary coefficient": -3.5e-4, "emissivity": 0.1,
            "dynamic viscosity": 1e-3, "low vaporization threshold": 2800.0,
            "high vaporization threshold": 3200.0, "retro-diffusion coefficient": 0.18,
        }
        rows = {row["quantity"]: row for row in vapor.CONSTANTS}
        self.assertEqual(set(rows), set(expected))
        for name, value in expected.items():
            with self.subTest(name=name):
                self.assertEqual(rows[name]["value"], value)
                self.assertIn("printed p. 2", rows[name]["table"])
                self.assertTrue(rows[name]["locator"])
        self.assertIn("Valencia and Quested 2013", vapor.SOURCE_PROFILE["primarySourceCitedByGan"])
        self.assertEqual(vapor.SOURCE_PROFILE["disclosure"],
            "Thermal and vapour constants are Al6061 values (Gan 2021 SI Tables 1-2, citing Valencia and "
            "Quested 2013) used as an Al-rich proxy for AlSi10Mg; Mg and Si selective evaporation and the "
            "real AlSi10Mg composition are not modelled.")
        unused = vapor.SOURCE_PROFILE["recordedUnusedTable2"]
        self.assertEqual(unused["surfacePressureConstants_c2_d2"], (-1.02617e3, 3.80205e6))
        self.assertIn("not evaluated", unused["status"])

    def test_material_table_follows_gan_laws_and_registry_accepts_it(self):
        props = vapor.proxy_material_properties()
        props_again = vapor.proxy_material_properties()
        props_again["table"][0][1] = 1.0
        self.assertEqual(vapor.proxy_material_properties()["table"][0][1], 2705.0)  # fresh object
        m = material("AlSi10Mg", props)
        table = np.asarray(m["table"])
        for temperature in (273.15, 500.0, 873.0, 900.0, 914.0):
            k = np.interp(temperature, table[:, 0], table[:, 2])
            cp = np.interp(temperature, table[:, 0], table[:, 3])
            self.assertAlmostEqual(k, 0.091 * temperature + 152.5, places=9)
            self.assertAlmostEqual(cp, 0.486 * temperature + 725, places=9)
            self.assertEqual(np.interp(temperature, table[:, 0], table[:, 1]), 2705.0)
        for temperature in (915.0, 2000.0, 2792.0):
            self.assertEqual([np.interp(temperature, table[:, 0], table[:, c]) for c in (1, 2, 3)],
                             [2415.0, 90.0, 1170.0])
        self.assertEqual((m["solidus_K"], m["liquidus_K"], m["boiling_K"], m["latentHeat_J_kg"]),
                         (873.0, 915.0, 2792.0, 3.8e5))
        self.assertEqual((m["emissivity"], m["dGamma_dT"]), (0.1, -3.5e-4))
        self.assertEqual(m["absorptivity"], 0.30)  # AlSi10Mg authority, not Gan's 0.01 Fresnel floor
        self.assertIn("Leis", m["source"])

    def test_open_o8_registry_table_is_not_the_proxy(self):
        registry = material("AlSi10Mg")
        self.assertNotEqual(registry["table"], material("AlSi10Mg", vapor.proxy_material_properties())["table"])
        self.assertEqual(registry["latentHeat_J_kg"], 397000.0)  # unchanged OPEN O8 value


class VaporLawTests(unittest.TestCase):
    def setUp(self):
        self.config = vapor.validate_config(scenario(), 915.0)

    def test_high_law_matches_independent_maxwellian_quadrature_and_units(self):
        nodes, weights = np.polynomial.legendre.leggauss(160)
        speed = 6.0 * (nodes + 1.0)
        integral = float(np.sum(6.0 * weights * speed * np.exp(-speed**2 / 2.0)))
        for temperature in [3200.0, 3800.0, 5000.0]:
            with self.subTest(temperature=temperature):
                pressure = psat(temperature)
                density = pressure * M / (R * temperature)
                thermal_speed = math.sqrt(R * temperature / M)
                expected = 0.82 * density * thermal_speed / math.sqrt(2 * math.pi) * integral
                state = vapor.surface_state(temperature, self.config)
                actual = float(state["mass_flux_kg_m2_s"])
                self.assertLessEqual(abs(actual / expected - 1), 1e-8)
                self.assertAlmostEqual(float(state["heat_flux_W_m2"]) / actual, LV)
                self.assertAlmostEqual(float(state["recoil_pressure_Pa"]) / pressure, 0.59)

    def test_below_transition_is_exact_zero_at_positive_temperatures(self):
        state = vapor.surface_state(np.array([1.0, 300.0, 915.0, 2792.0, 2800.0]), self.config)
        for key in ["mass_flux_kg_m2_s", "heat_flux_W_m2", "heat_flux_derivative_W_m2K"]:
            np.testing.assert_array_equal(state[key], np.zeros(5))
        np.testing.assert_array_equal(state["recoil_pressure_Pa"], np.full(5, 101325.0))

    def test_bridge_matches_independent_cubic_and_is_monotone(self):
        high, width = 3200.0, 400.0
        mass = .82 * psat(high) * math.sqrt(M / (2 * math.pi * R * high))
        mass_slope = mass * (LV * M / R / high**2 - .5 / high)
        recoil = .59 * psat(high)
        recoil_slope = recoil * LV * M / R / high**2
        for fraction in [.001, .1, .5, .9, .999]:
            state = vapor.surface_state(2800 + width * fraction, self.config)
            for key, low_value, high_value, slope in [
                ("mass_flux_kg_m2_s", 0, mass, mass_slope),
                ("recoil_pressure_Pa", 101325, recoil, recoil_slope),
            ]:
                a = 3 * (high_value - low_value) - width * slope
                b = width * slope - 2 * (high_value - low_value)
                self.assertAlmostEqual(float(state[key]) / (low_value + a * fraction**2 + b * fraction**3), 1.0, places=12)
                self.assertGreaterEqual(a, 0)
                self.assertGreaterEqual(2 * a + 3 * b, 0)

    def test_bridge_endpoint_values_and_slopes_are_continuous(self):
        epsilon = 1e-4
        heat_scale = (.82 * psat(3200) * math.sqrt(M / (2 * math.pi * R * 3200))
                      * (LV * M / R / 3200**2 - .5 / 3200) * LV)
        pressure_scale = .59 * psat(3200) * LV * M / R / 3200**2
        for boundary in [2800.0, 3200.0]:
            state = vapor.surface_state([boundary - epsilon, boundary, boundary + epsilon], self.config)
            heat, slope = state["heat_flux_W_m2"], state["heat_flux_derivative_W_m2K"]
            self.assertLess(abs(float(heat[2] - heat[0])), 3 * epsilon * heat_scale)  # no value jump
            self.assertLess(abs(float(slope[0] - slope[2])) / heat_scale, 1e-6)
            self.assertLess(abs(float((heat[2] - heat[0]) / (2 * epsilon) - slope[1])) / heat_scale, 1e-6)
            pressure = state["recoil_pressure_Pa"]
            left, right = (pressure[1] - pressure[0]) / epsilon, (pressure[2] - pressure[1]) / epsilon
            self.assertLess(abs(float(left - right)) / pressure_scale, 1e-6)

    def test_high_heat_derivative_matches_finite_difference(self):
        temperatures = np.array([3300.0, 4000.0, 4900.0])
        derivative = (vapor.surface_state(temperatures + .001, self.config)["heat_flux_W_m2"]
                      - vapor.surface_state(temperatures - .001, self.config)["heat_flux_W_m2"]) / .002
        np.testing.assert_allclose(vapor.surface_state(temperatures, self.config)["heat_flux_derivative_W_m2K"],
                                   derivative, rtol=1e-8)

    def test_malformed_temperatures_and_foreign_config_fail_without_clipping(self):
        for temperatures in [-1, 0, float("nan"), float("inf"), 5000.001, True, "3500",
                             [True, 3500], np.array([3500 + 0j]), np.array([300, np.nan])]:
            with self.subTest(temperatures=temperatures), self.assertRaises(ValueError):
                vapor.surface_state(temperatures, self.config)
        ti_config = ti64.validate_config(dict(scenario(), transitionLow_K=3560.0, transitionHigh_K=4000.0), 1923.0)
        with self.assertRaises(ValueError):
            vapor.surface_state(3500.0, ti_config)  # a Ti config never yields an Al flux


class ConfigurationTests(unittest.TestCase):
    def test_configuration_is_immutable_and_detached(self):
        raw = scenario()
        config = vapor.validate_config(raw, 915)
        raw["returnFraction"] = .8
        self.assertEqual(config.returnFraction, .18)
        with self.assertRaises((FrozenInstanceError, AttributeError, TypeError)):
            config.returnFraction = .8
        with self.assertRaises(TypeError):
            vapor.SOURCE_PROFILE["sourceId"] = "other"

    def test_sigma_optional_and_bad_inputs_fail(self):
        raw = scenario(); del raw["surfaceTension_N_m"]
        self.assertIsNone(vapor.validate_config(raw, 915).surfaceTension_N_m)
        for raw in [None, [], True, dict(scenario(), surprise=0)]:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                vapor.validate_config(raw, 915)
        for key in scenario():
            for bad in [True, "1", None, float("nan"), float("inf")]:
                with self.subTest(key=key, bad=bad), self.assertRaises(ValueError):
                    vapor.validate_config(scenario(**{key: bad}), 915)
        for changes in [dict(returnFraction=1), dict(ambientPressure_Pa=0), dict(transitionLow_K=900),
                        dict(transitionLow_K=3200), dict(transitionHigh_K=5001), dict(maxTemperature_K=6001),
                        dict(ambientPressure_Pa=1e9)]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                vapor.validate_config(scenario(**changes), 915)


class OnsetTests(unittest.TestCase):
    def setUp(self):
        self.config = vapor.validate_config(scenario(), 915)

    def state(self, excess, mass=1.0):
        return {"mass_flux_kg_m2_s": np.array([mass]), "recoil_pressure_Pa": np.array([101325.0 + excess])}

    def test_threshold_uses_radius_with_equality_latching(self):
        # 2*0.91/50e-6 = 36400 Pa; using the diameter would give 18200 Pa.
        for excess, expected in [(36399., False), (36400., True), (36401., True)]:
            with self.subTest(excess=excess):
                gate = vapor.update_onset(None, self.state(excess), self.config, 50e-6, 0)
                self.assertEqual(gate["onset"], expected)
                self.assertEqual(gate["geometryAvailable"], not expected)
        self.assertFalse(vapor.update_onset(None, self.state(1e6, mass=0), self.config, 50e-6, 0)["onset"])

    def test_latch_survives_cooling_and_candidate_does_not_mutate_previous(self):
        clear = vapor.update_onset(None, self.state(0), self.config, 50e-6, 0)
        snapshot = copy.deepcopy(clear)
        candidate = vapor.update_onset(clear, self.state(36400), self.config, 50e-6, .1)
        self.assertEqual(clear, snapshot)
        cooled = vapor.update_onset(candidate, vapor.surface_state([300], self.config), self.config, 50e-6, .2)
        self.assertEqual(cooled, candidate)
        self.assertTrue(cooled["onset"])

    def test_missing_sigma_latches_unresolved(self):
        raw = scenario(); del raw["surfaceTension_N_m"]
        config = vapor.validate_config(raw, 915)
        gate = vapor.update_onset(None, vapor.surface_state([3000.0], config), config, 50e-6, .1)
        self.assertTrue(gate["unresolvedGeometry"])
        self.assertFalse(gate["geometryAvailable"])


if __name__ == "__main__":
    unittest.main()
