"""Offline numerical checks for the declared Ti-species vapor scenario.

These tests establish software/numerical behavior, not Ti64 physical validation.
"""

import copy
from dataclasses import FrozenInstanceError
import math
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lpbf_ti64_evaporation as vapor  # noqa: E402


def scenario(**changes):
    raw = dict(transitionLow_K=3560.0, transitionHigh_K=4000.0,
               ambientPressure_Pa=101325.0, returnFraction=0.2,
               surfaceTension_N_m=1.65, maxTemperature_K=5000.0)
    raw.update(changes)
    return raw


class VaporLawTests(unittest.TestCase):
    def setUp(self):
        self.config = vapor.validate_config(scenario(), 1923.0)

    def test_high_law_matches_independent_maxwellian_quadrature_and_units(self):
        # Omitting sqrt(T), molecular mass or the return factor breaks this check.
        nodes, weights = np.polynomial.legendre.leggauss(160)
        speed = 6.0 * (nodes + 1.0)  # Dimensionless normal speed, 0..12.
        integral = float(np.sum(6.0 * weights * speed * np.exp(-speed**2 / 2.0)))
        for temperature in [4000.0, 4500.0, 5000.0]:
            with self.subTest(temperature=temperature):
                pressure = 101325.0 * math.exp(
                    9.255e6 * 0.048 / 8.31446261815324 * (1 / 3560.0 - 1 / temperature))
                density = pressure * 0.048 / (8.31446261815324 * temperature)
                thermal_speed = math.sqrt(8.31446261815324 * temperature / 0.048)
                expected = 0.8 * density * thermal_speed / math.sqrt(2 * math.pi) * integral
                state = vapor.surface_state(temperature, self.config)
                actual = float(state["mass_flux_kg_m2_s"])
                self.assertLessEqual(abs(actual / expected - 1), 1e-8)
                self.assertAlmostEqual(float(state["heat_flux_W_m2"]) / actual, 9.255e6)
                self.assertAlmostEqual(float(state["recoil_pressure_Pa"]) / pressure, 0.6)
        self.assertTrue(vapor.SOURCE_PROFILE["sourceId"])

    def test_below_transition_is_exact_zero_at_positive_temperatures(self):
        state = vapor.surface_state(np.array([1.0, 300.0, 1923.0, 3560.0]), self.config)
        for key in ["mass_flux_kg_m2_s", "heat_flux_W_m2", "heat_flux_derivative_W_m2K"]:
            np.testing.assert_array_equal(state[key], np.zeros(4))
        np.testing.assert_array_equal(state["recoil_pressure_Pa"], np.full(4, 101325.0))

    def test_bridge_matches_independent_cubic_and_analytic_flux_derivative(self):
        high = 4000.0
        width = 440.0
        pressure = 101325 * math.exp(9.255e6 * .048 / 8.31446261815324 * (1 / 3560 - 1 / high))
        mass = .8 * pressure * math.sqrt(.048 / (2 * math.pi * 8.31446261815324 * high))
        mass_slope = mass * (9.255e6 * .048 / 8.31446261815324 / high**2 - .5 / high)
        recoil = .6 * pressure
        recoil_slope = recoil * 9.255e6 * .048 / 8.31446261815324 / high**2
        for fraction in [.001, .1, .5, .9, .999]:
            state = vapor.surface_state(3560 + width * fraction, self.config)
            for key, low_value, high_value, slope in [
                ("mass_flux_kg_m2_s", 0, mass, mass_slope),
                ("recoil_pressure_Pa", 101325, recoil, recoil_slope),
            ]:
                a = 3 * (high_value - low_value) - width * slope
                b = width * slope - 2 * (high_value - low_value)
                expected = low_value + a * fraction**2 + b * fraction**3
                self.assertAlmostEqual(float(state[key]) / expected, 1.0, places=12)
                self.assertGreaterEqual(a, 0)  # Endpoint constraints prove derivative >= 0.
                self.assertGreaterEqual(2 * a + 3 * b, 0)
            a = 3 * mass - width * mass_slope
            b = width * mass_slope - 2 * mass
            derivative = (2 * a * fraction + 3 * b * fraction**2) / width * 9.255e6
            self.assertAlmostEqual(float(state["heat_flux_derivative_W_m2K"]) / derivative, 1, places=12)

    def test_bridge_endpoint_values_and_slopes_are_continuous(self):
        epsilon = 1e-4
        # Normalize both endpoints by the nonzero high-end physical slope. An
        # absolute 0.01 W/m2K bound at low is dimensionally inappropriate: the
        # right derivative is O(epsilon) for this C1, non-C2 bridge.
        high_pressure = 101325 * math.exp(9.255e6 * .048 / 8.31446261815324 * (1 / 3560 - 1 / 4000))
        pressure_scale = .6 * high_pressure * 9.255e6 * .048 / 8.31446261815324 / 4000**2
        heat_scale = (.8 * high_pressure * math.sqrt(.048 / (2 * math.pi * 8.31446261815324 * 4000))
                      * (9.255e6 * .048 / 8.31446261815324 / 4000**2 - .5 / 4000) * 9.255e6)
        for boundary in [3560.0, 4000.0]:
            state = vapor.surface_state([boundary - epsilon, boundary, boundary + epsilon], self.config)
            heat = state["heat_flux_W_m2"]
            slope = state["heat_flux_derivative_W_m2K"]
            self.assertLess(abs(float(slope[0] - slope[2])) / heat_scale, 1e-6)
            self.assertLess(abs(float((heat[2] - heat[0]) / (2 * epsilon) - slope[1])) / heat_scale, 1e-6)
            pressure = state["recoil_pressure_Pa"]
            left = (pressure[1] - pressure[0]) / epsilon
            right = (pressure[2] - pressure[1]) / epsilon
            self.assertLess(abs(float(left - right)) / pressure_scale, 1e-6)

    def test_high_heat_derivative_matches_independent_finite_difference(self):
        temperatures = np.array([4100.0, 4500.0, 4900.0])
        step = .001
        derivative = (vapor.surface_state(temperatures + step, self.config)["heat_flux_W_m2"]
                      - vapor.surface_state(temperatures - step, self.config)["heat_flux_W_m2"]) / (2 * step)
        np.testing.assert_allclose(vapor.surface_state(temperatures, self.config)["heat_flux_derivative_W_m2K"],
                                   derivative, rtol=1e-8)

    def test_input_arrays_and_shape_are_preserved(self):
        temperatures = np.array([[300., 3700.], [4000., 5000.]])
        saved = temperatures.copy()
        temperatures.flags.writeable = False
        state = vapor.surface_state(temperatures, self.config)
        np.testing.assert_array_equal(temperatures, saved)
        for array in state.values():
            self.assertEqual(array.shape, temperatures.shape)
            self.assertFalse(np.shares_memory(array, temperatures))
            self.assertTrue(np.isfinite(array).all())

    def test_malformed_temperatures_fail_without_clipping(self):
        for temperatures in [-1, 0, float("nan"), float("inf"), 5000.001, True,
                             "4500", [True, 4500], [300, "4500"], np.array([False]),
                             np.array([4500 + 0j]), np.array([300, np.nan])]:
            with self.subTest(temperatures=temperatures), self.assertRaises(ValueError):
                vapor.surface_state(temperatures, self.config)


class ConfigurationTests(unittest.TestCase):
    def test_configuration_is_immutable_and_detached(self):
        raw = scenario()
        config = vapor.validate_config(raw, 1923)
        raw["returnFraction"] = .8
        self.assertEqual(config.returnFraction, .2)
        with self.assertRaises((FrozenInstanceError, AttributeError, TypeError)):
            config.returnFraction = .8
        with self.assertRaises(TypeError):
            vapor.SOURCE_PROFILE["sourceId"] = "other"

    def test_sigma_is_optional_and_not_defaulted(self):
        raw = scenario()
        del raw["surfaceTension_N_m"]
        self.assertIsNone(vapor.validate_config(raw, 1923).surfaceTension_N_m)

    def test_unknown_missing_nonobject_and_nonnumeric_configuration_fails(self):
        for raw in [None, [], True, dict(scenario(), surprise=0)]:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                vapor.validate_config(raw, 1923)
        for key in scenario():
            for bad in [True, False, "1", None, float("nan"), float("inf")]:
                with self.subTest(key=key, bad=bad), self.assertRaises(ValueError):
                    vapor.validate_config(scenario(**{key: bad}), 1923)
            if key != "surfaceTension_N_m":
                raw = scenario()
                del raw[key]
                with self.subTest(missing=key), self.assertRaises(ValueError):
                    vapor.validate_config(raw, 1923)

    def test_configuration_range_and_analytic_bridge_guards(self):
        for changes in [dict(returnFraction=-.001), dict(returnFraction=1),
                        dict(ambientPressure_Pa=0), dict(surfaceTension_N_m=0),
                        dict(transitionLow_K=1900), dict(transitionLow_K=4000),
                        dict(transitionHigh_K=5001), dict(maxTemperature_K=6001),
                        dict(transitionHigh_K=6000, maxTemperature_K=6000),
                        dict(ambientPressure_Pa=1e9), dict(ambientPressure_Pa=300000),
                        dict(transitionLow_K=1923)]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                vapor.validate_config(scenario(**changes), 1923)
        for liquidus in [True, "1923", 0, -1, float("nan"), 3600]:
            with self.subTest(liquidus=liquidus), self.assertRaises(ValueError):
                vapor.validate_config(scenario(), liquidus)
        self.assertEqual(vapor.validate_config(scenario(returnFraction=0), 1923).returnFraction, 0)


class OnsetTests(unittest.TestCase):
    def setUp(self):
        self.config = vapor.validate_config(scenario(), 1923)

    def state(self, excess, mass=1.0):
        return {"mass_flux_kg_m2_s": np.array([mass]),
                "recoil_pressure_Pa": np.array([101325.0 + excess])}

    def test_below_equal_above_threshold_use_radius_and_require_active_mass(self):
        # r=50 um gives 66000 Pa: passing diameter instead would miss equality.
        for excess, expected in [(65999., False), (66000., True), (66001., True)]:
            with self.subTest(excess=excess):
                gate = vapor.update_onset(None, self.state(excess), self.config, 50e-6, 0)
                self.assertEqual(gate["onset"], expected)
                self.assertEqual(gate["geometryAvailable"], not expected)
                self.assertEqual(gate["firstOnsetTime_s"], 0.0 if expected else None)
        self.assertFalse(vapor.update_onset(None, self.state(1e6, mass=0), self.config, 50e-6, 0)["onset"])

    def test_missing_sigma_active_only_and_cooling_latches(self):
        raw = scenario()
        del raw["surfaceTension_N_m"]
        config = vapor.validate_config(raw, 1923)
        cold = vapor.surface_state([300.0], config)
        clear = vapor.update_onset(None, cold, config, 50e-6, 0)
        self.assertTrue(clear["geometryAvailable"])
        active = vapor.surface_state([3700.0], config)
        unresolved = vapor.update_onset(clear, active, config, 50e-6, .1)
        self.assertTrue(unresolved["unresolvedGeometry"])
        self.assertFalse(unresolved["onset"])
        self.assertEqual(unresolved["firstUnresolvedTime_s"], .1)
        cooled = vapor.update_onset(unresolved, cold, config, 50e-6, .2)
        self.assertEqual(cooled, unresolved)

    def test_onset_cooling_and_discarded_candidate_do_not_mutate_previous(self):
        clear = vapor.update_onset(None, self.state(0), self.config, 50e-6, 0)
        snapshot = copy.deepcopy(clear)
        candidate = vapor.update_onset(clear, self.state(66000), self.config, 50e-6, .1)
        self.assertEqual(clear, snapshot)  # Discarding candidate cannot latch accepted state.
        self.assertTrue(candidate["onset"])
        cold = vapor.surface_state([300], self.config)
        cooled = vapor.update_onset(candidate, cold, self.config, 50e-6, .2)
        self.assertEqual(cooled, candidate)
        self.assertIsNot(cooled, candidate)

    def test_gate_uses_any_active_surface_cell_and_preserves_state(self):
        state = {"mass_flux_kg_m2_s": np.array([0., 1., 2.]),
                 "recoil_pressure_Pa": np.array([1e9, 101325., 167325.])}
        snapshot = copy.deepcopy(state)
        gate = vapor.update_onset(None, state, self.config, 50e-6, .1)
        self.assertTrue(gate["onset"])
        for key in state:
            np.testing.assert_array_equal(state[key], snapshot[key])

    def test_invalid_gate_inputs_fail(self):
        for radius, time in [(0, 0), (-1, 0), (True, 0), ("0.1", 0), (1, -1),
                             (1, True), (1, float("nan")), (float("inf"), 0)]:
            with self.subTest(radius=radius, time=time), self.assertRaises(ValueError):
                vapor.update_onset(None, self.state(0), self.config, radius, time)
        for state in [{}, self.state(-200000), self.state(0, -1), self.state(0, float("nan")),
                      {"mass_flux_kg_m2_s": [1, 2], "recoil_pressure_Pa": [101325]}]:
            with self.subTest(state=state), self.assertRaises(ValueError):
                vapor.update_onset(None, state, self.config, 50e-6, 0)

    def test_inconsistent_previous_gate_fails_and_extreme_threshold_is_not_clipped(self):
        valid = vapor.update_onset(None, self.state(0), self.config, 50e-6, 0)
        for previous in [True, {}, dict(valid, onset=1), dict(valid, onset=True),
                         dict(valid, geometryAvailable=False), dict(valid, firstOnsetTime_s=.1),
                         dict(valid, onset=True, geometryAvailable=False, firstOnsetTime_s=2)]:
            with self.subTest(previous=previous), self.assertRaises(ValueError):
                vapor.update_onset(previous, self.state(0), self.config, 50e-6, 1)
        with self.assertRaises(ValueError):
            vapor.update_onset(None, self.state(66000), self.config, 1e-320, 0)


if __name__ == "__main__":
    unittest.main()
