"""Independent numerical/contract checks for the opt-in evaporative CPU path."""
import copy
import json
import math
from pathlib import Path
import subprocess
import sys
import unittest

import numpy as np

from lpbf_ti64_evaporation import validate_config
from lpbf_ti64_evaporative_solver import run, _accepted_step, _thermal_table
from lpbf_material_registry import material
from lpbf_heat_source import source_limited_step


def scenario(**changes):
    raw = dict(material="Ti-6Al-4V", backend="reference", surfaceMode="bare-plate",
               power_W=160., speed_mm_s=800., beamDiameter_um=80.,
               preheat_C=80., mesh_um=40., maxDt_s=1e-6, trackLength_um=100.,
               cooling_s=2e-5, sourcePenetration_um=20.,
               evaporation=dict(transitionLow_K=3560., transitionHigh_K=4000.,
                                ambientPressure_Pa=101325., returnFraction=.2,
                                maxTemperature_K=5000., surfaceTension_N_m=1.65))
    raw.update(changes)
    return raw


def config():
    return validate_config(scenario()["evaporation"], 1933.15)


def step(T, H, dt, *, dx, rho, cp, k, tt, hh, source=None, base=False):
    return _accepted_step(T, H, dt, dx=dx, rho=rho, cp=np.full_like(T, cp),
                          conductivity=np.full_like(T, k), temperatures=tt,
                          enthalpies=hh, reference_h=0., ambient_K=273.15,
                          evaporation=config(), convection=0., emissivity=0.,
                          base_boundary=base, source_factory=source)


class ManufacturedTests(unittest.TestCase):
    def test_cooling_independent_ode_first_order_and_energy(self):
        # Independent high-branch ODE; no calls into production surface law.
        def rhs(t):
            p = 101325.*math.exp((9.255e6*.048/8.31446261815324)*(1/3560.-1/t))
            return -.8*p*math.sqrt(.048/(2*math.pi*8.31446261815324*t))*9.255e6/(4000.*1000.*.001)
        duration = 2e-5
        ref = 4500.
        h_ref = duration/4096
        for _ in range(4096):
            a = rhs(ref); b = rhs(ref+h_ref*a/2); c = rhs(ref+h_ref*b/2); d = rhs(ref+h_ref*c)
            ref += h_ref*(a+2*b+2*c+d)/6
        errors = []
        for n in (10, 20, 40):
            T = np.full((1, 1, 1), 4500.)
            H = T*4e6
            initial = float(H.sum())*.001**3
            energy = 0.
            for _ in range(n):
                out = step(T, H, duration/n, dx=.001, rho=4000., cp=1000.,
                           k=1., tt=np.array([273.15, 5000.]),
                           hh=np.array([273150., 5e6]))
                T, H = out["temperature"], out["enthalpy"]
                self.assertEqual(out["dt_s"], duration/n)
                energy += out["evaporative_J"]
            removed = initial-float(H.sum())*.001**3
            self.assertLess(abs(removed-energy)/energy, 1e-10)
            errors.append(abs(float(T.item())-ref))
        self.assertGreater(min(math.log(errors[i]/errors[i+1], 2) for i in (0, 1)), .8)
        print("cooling errors/order:", errors, math.log(errors[-2]/errors[-1], 2))

    def test_actual_field_conduction_refines(self):
        errors = []
        for n in (8, 16, 32):
            dx = 1/n
            x = (np.arange(n)+.5)*dx
            T = np.broadcast_to((300+np.cos(math.pi*x))[:, None, None], (n, 2, 2)).copy()
            H = T.copy()
            t = 0.
            while t < .01:
                out = step(T, H, min(.1*dx**2, .01-t), dx=dx, rho=1., cp=1.,
                           k=1., tt=np.array([273.15, 5000.]), hh=np.array([273.15, 5000.]))
                T, H = out["temperature"], out["enthalpy"]
                t += out["dt_s"]
            expected = 300+np.exp(-math.pi**2*.01)*np.cos(math.pi*x)
            errors.append(float(np.sqrt(np.mean((T[:, 0, 0]-expected)**2))))
        self.assertTrue(errors[0] > errors[1] > errors[2] > 0.)
        print("conduction refinement L2:", errors)

    def test_rejection_reintegrates_source_and_preserves_accepted_inputs(self):
        # A deliberately short manufactured enthalpy table forces rejection
        # below transition, without an evaporative sink masking the source.
        T = np.full((1, 1, 1), 3000.)
        H = T.copy()
        before = T.copy(), H.copy()
        calls = []
        def source(dt, passive, capacity):
            calls.append(dt)
            field = np.full_like(T, 1e9)
            return dt, field, passive+field, 1., 0
        out = step(T, H, 1e-6, dx=1., rho=1., cp=1., k=1.,
                   tt=np.array([273.15, 3001.]), hh=np.array([273.15, 3001.]), source=source)
        self.assertGreater(out["rejectedCandidates"], 0)
        self.assertTrue(all(a > b for a, b in zip(calls, calls[1:])))
        np.testing.assert_array_equal(T, before[0]); np.testing.assert_array_equal(H, before[1])
        self.assertAlmostEqual(out["input_J"], 1e9*out["dt_s"])
        self.assertLessEqual(float(out["temperature"].max()), 3001.)

    def test_persistent_invalid_candidate_raises_without_clipping(self):
        T = np.full((1, 1, 1), 5000.)
        H = T.copy()
        def source(dt, passive, capacity):
            field = np.full_like(T, float("nan"))
            return dt, field, passive+field, 1., 0
        with self.assertRaises(ValueError):
            step(T, H, 1e-6, dx=1., rho=1., cp=1., k=1.,
                 tt=np.array([273.15, 5000.]), hh=np.array([273.15, 5000.]), source=source)
        self.assertEqual(float(T.item()), 5000.)

    def test_rejected_actual_moving_source_reintegrates_its_spatial_field(self):
        dx = 40e-6
        axis = (np.arange(9)-4)*dx
        z = (np.arange(9)-8.5)*dx
        T = np.full((9, 9, 9), 3000.)
        H = T*4430.*526.
        segment = dict(start_s=0., end_s=.000125, start=[-50e-6, 0.], end=[50e-6, 0.])
        fields = []
        def moving_source(dt, passive, capacity):
            result = source_limited_step(axis, z, dx, segment, .00005, dt,
                                         0., 40e-6, 20e-6, 64., passive, capacity)
            fields.append((result[0], result[1].copy()))
            return result
        out = step(T, H, 1e-6, dx=dx, rho=4430., cp=526., k=6.7,
                   tt=np.array([273.15, 3001.]), hh=np.array([273.15, 3001.])*526.,
                   source=moving_source)
        self.assertGreater(out["rejectedCandidates"], 0)
        self.assertTrue(all(a[0] > b[0] for a, b in zip(fields, fields[1:])))
        self.assertGreater(float(np.linalg.norm(fields[0][1]-fields[-1][1])), 0.)
        self.assertAlmostEqual(out["input_J"], 64.*out["dt_s"], delta=1e-15)
        np.testing.assert_array_equal(T, np.full_like(T, 3000.))


class IntegrationTests(unittest.TestCase):
    def test_table_continuation_preserves_registry(self):
        m = material("Ti-6Al-4V"); saved = copy.deepcopy(m)
        tt, hh = _thermal_table(m, 5000.)
        self.assertEqual(m, saved)
        self.assertEqual(tt[-1], 5000.)
        self.assertAlmostEqual((hh[-1]-hh[-2])/(tt[-1]-tt[-2]), 930.)
        self.assertEqual(m["boiling_K"], 3560.15)

    def test_strict_request_boundary(self):
        invalid = [dict(material="Inconel 718"), dict(backend="auto"),
                   dict(surfaceMode="powder-layer"), dict(layers=2), dict(tracks=2),
                   dict(evaporationModel=True), dict(marangoniMultiplier=2.2),
                   dict(thermalModelId="layered-plate-enthalpy-v1"), dict(properties={}),
                   dict(measurements=[]), dict(power_W=True), dict(mesh_um="40"),
                   dict(maxDt_s=float("nan")), dict(study="mesh"), dict(timeout_s=20.)]
        for change in invalid:
            with self.subTest(change=change), self.assertRaises(ValueError):
                run(scenario(**change))
        missing = scenario(); del missing["evaporation"]
        with self.assertRaises(ValueError): run(missing)

    def test_zero_flux_contract_and_geometry(self):
        result = run(scenario(power_W=10.))
        self.assertEqual(result["modelId"], "ti64-fixed-surface-evaporation-v1")
        self.assertFalse(result["experimentalValidation"])
        self.assertFalse(result["productionReady"])
        self.assertEqual(result["tier"], "Uncalibrated estimate")
        self.assertEqual(result["energy"]["evaporative_J"], 0.)
        self.assertEqual(result["diagnosticEmittedMass_kg"], 0.)
        self.assertTrue(result["gate"]["geometryAvailable"])
        self.assertIsNotNone(result["geometry"]["depth_um"])
        self.assertIn("snapshot", result["geometry"]["basis"])
        self.assertNotIn("defects", result)
        self.assertGreater(result["acceptedStepCount"], 0)
        self.assertAlmostEqual(result["acceptedTime_s"], .000125+.00002)
        self.assertEqual(len(result["provenance"]["implementationHash"]), 64)
        self.assertEqual(len(result["provenance"]["defaultImplementationHash"]), 64)
        self.assertEqual(set(result["provenance"]["moduleSha256"]),
                         {"lpbf_ti64_evaporative_solver.py", "lpbf_ti64_evaporation.py"})
        json.dumps(result, allow_nan=False)

    def test_moving_source_energy_positive_evaporation_and_onset_refusal(self):
        raw = scenario()
        result = run(raw)
        zero = copy.deepcopy(raw)
        zero["evaporation"].update(transitionLow_K=4900., transitionHigh_K=5000.)
        reference = run(zero)
        self.assertGreater(result["energy"]["evaporative_J"], 0.)
        self.assertGreater(result["diagnosticEmittedMass_kg"], 0.)
        self.assertEqual(reference["energy"]["evaporative_J"], 0.)
        self.assertEqual(reference["diagnosticEmittedMass_kg"], 0.)
        self.assertAlmostEqual(result["energy"]["input_J"], reference["energy"]["input_J"], delta=1e-12)
        self.assertLess(result["energy"]["stored_J"], reference["energy"]["stored_J"])
        self.assertLessEqual(result["energy"]["relativeResidual"], 1e-9)
        self.assertLessEqual(reference["energy"]["relativeResidual"], 1e-9)
        for output in (result, reference):
            energy = output["energy"]
            losses = energy["base_J"]+energy["radiativeConvective_J"]+energy["evaporative_J"]
            independent = abs(energy["input_J"]-losses-energy["stored_J"])/max(
                abs(energy["input_J"]), abs(losses), abs(energy["stored_J"]), 1e-12)
            self.assertLessEqual(independent, 1e-9)
            self.assertEqual(energy["relativeResidual"], independent)
        self.assertTrue(reference["gate"]["geometryAvailable"])
        self.assertGreater(reference["geometry"]["volume_um3"], 0.)
        self.assertLessEqual(result["peakTemperature_K"], 5000.)
        self.assertLess(result["fieldSummary"]["maximumFinalTemperature_K"], 3560.)
        self.assertTrue(result["gate"]["onset"])
        for key in ("depth_um", "length_um", "volume_um3"):
            self.assertIsNone(result["geometry"][key])
        self.assertIn("fixed-surface", result["geometry"]["widthLabel"])
        self.assertIsNotNone(result["gate"]["firstOnsetTime_s"])
        self.assertLess(result["fieldSummary"]["minimumFinalTemperature_K"],
                        result["fieldSummary"]["maximumFinalTemperature_K"])
        print("actual moving-source acceptance:", result["energy"], result["peakTemperature_K"], result["gate"])

    def test_missing_tension_refuses_geometry_with_active_evaporation(self):
        raw = scenario(); del raw["evaporation"]["surfaceTension_N_m"]
        result = run(raw)
        self.assertTrue(result["gate"]["unresolvedGeometry"])
        self.assertIsNone(result["geometry"]["depth_um"])
        self.assertIn("surface tension", result["geometry"]["refusalReason"])

    def test_cli_round_trip_and_failure(self):
        script = Path(__file__).with_name("lpbf_ti64_evaporative_solver.py")
        proc = subprocess.run([sys.executable, str(script)], input=json.dumps(scenario(power_W=10.)),
                              text=True, capture_output=True, check=True)
        result = json.loads(proc.stdout)
        self.assertEqual(result["modelId"], "ti64-fixed-surface-evaporation-v1")
        self.assertEqual(proc.stderr, "")
        proc = subprocess.run([sys.executable, str(script)], input='{"invalid":true}',
                              text=True, capture_output=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(json.loads(proc.stdout)["status"], "error")


if __name__ == "__main__":
    unittest.main()
