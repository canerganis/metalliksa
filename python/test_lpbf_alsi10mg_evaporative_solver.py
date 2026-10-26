"""Independent numerical/contract checks for the AlSi10Mg (Al6061 proxy) evaporative CPU path."""
import copy
import json
import math
from pathlib import Path
import subprocess
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lpbf_alsi10mg_evaporative_solver as solver  # noqa: E402
from lpbf_al_proxy_evaporation import validate_config  # noqa: E402
from lpbf_alsi10mg_evaporative_solver import run, _accepted_step  # noqa: E402

R = 8.31446261815324
DISCLOSURE = ("Thermal and vapour constants are Al6061 values (Gan 2021 SI Tables 1-2, citing Valencia and "
              "Quested 2013) used as an Al-rich proxy for AlSi10Mg; Mg and Si selective evaporation and the "
              "real AlSi10Mg composition are not modelled.")


def scenario(**changes):
    raw = dict(material="AlSi10Mg", backend="reference", surfaceMode="bare-plate",
               power_W=300., speed_mm_s=1300., beamDiameter_um=100.,
               preheat_C=80., mesh_um=20., maxDt_s=1e-6, trackLength_um=100.,
               cooling_s=2e-5, sourcePenetration_um=20.,
               evaporation=dict(transitionLow_K=2800., transitionHigh_K=3200.,
                                ambientPressure_Pa=101325., returnFraction=.18,
                                maxTemperature_K=5000., surfaceTension_N_m=.91))
    raw.update(changes)
    return raw


def step(T, H, dt, *, dx, rho, cp, k, tt, hh, source=None):
    return _accepted_step(T, H, dt, dx=dx, rho=rho, cp=np.full_like(T, cp),
                          conductivity=np.full_like(T, k), temperatures=tt,
                          enthalpies=hh, reference_h=0., ambient_K=273.15,
                          evaporation=validate_config(scenario()["evaporation"], 915.),
                          convection=0., emissivity=0., base_boundary=False, source_factory=source)


class ManufacturedTests(unittest.TestCase):
    def test_cooling_independent_ode_first_order_and_energy(self):
        # Independent high-branch ODE (Al6061 constants typed here); no production law calls.
        def rhs(t):
            p = 101325.*math.exp((1.053e7*.027/R)*(1/2792.-1/t))
            return -.82*p*math.sqrt(.027/(2*math.pi*R*t))*1.053e7/(4000.*1000.*.001)
        duration, ref = 2e-5, 4000.
        h_ref = duration/4096
        for _ in range(4096):
            a = rhs(ref); b = rhs(ref+h_ref*a/2); c = rhs(ref+h_ref*b/2); d = rhs(ref+h_ref*c)
            ref += h_ref*(a+2*b+2*c+d)/6
        self.assertGreater(ref, 3200.)  # the whole reference stays on the closed-form branch
        errors = []
        for n in (10, 20, 40):
            T = np.full((1, 1, 1), 4000.)
            H = T*4e6
            initial = float(H.sum())*.001**3
            energy = 0.
            for _ in range(n):
                out = step(T, H, duration/n, dx=.001, rho=4000., cp=1000., k=1.,
                           tt=np.array([273.15, 5000.]), hh=np.array([273150., 5e6]))
                T, H = out["temperature"], out["enthalpy"]
                self.assertEqual(out["dt_s"], duration/n)
                energy += out["evaporative_J"]
            removed = initial-float(H.sum())*.001**3
            self.assertLess(abs(removed-energy)/energy, 1e-10)
            errors.append(abs(float(T.item())-ref))
        orders = [math.log(errors[i]/errors[i+1], 2) for i in (0, 1)]
        self.assertGreater(min(orders), .8)
        print("cooling errors/order:", errors, orders)

    def test_actual_field_conduction_refines(self):
        errors = []
        for n in (8, 16, 32):
            dx = 1/n
            x = (np.arange(n)+.5)*dx
            T = np.broadcast_to((300+np.cos(math.pi*x))[:, None, None], (n, 2, 2)).copy()
            H = T.copy()
            t = 0.
            while t < .01:
                out = step(T, H, min(.1*dx**2, .01-t), dx=dx, rho=1., cp=1., k=1.,
                           tt=np.array([273.15, 5000.]), hh=np.array([273.15, 5000.]))
                T, H = out["temperature"], out["enthalpy"]
                t += out["dt_s"]
            expected = 300+np.exp(-math.pi**2*.01)*np.cos(math.pi*x)
            errors.append(float(np.sqrt(np.mean((T[:, 0, 0]-expected)**2))))
        self.assertTrue(errors[0] > errors[1] > errors[2] > 0.)
        print("conduction refinement L2:", errors)

    def test_persistent_invalid_candidate_raises_without_clipping(self):
        T = np.full((1, 1, 1), 2000.)
        def source(dt, passive, capacity):
            field = np.full_like(T, float("nan"))
            return dt, field, passive+field, 1., 0
        with self.assertRaises(ValueError):
            step(T, T.copy(), 1e-6, dx=1., rho=1., cp=1., k=1.,
                 tt=np.array([273.15, 5000.]), hh=np.array([273.15, 5000.]), source=source)
        self.assertEqual(float(T.item()), 2000.)


class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = run(scenario())
        zero = scenario()
        zero["evaporation"] = dict(zero["evaporation"], transitionLow_K=4900., transitionHigh_K=5000.)
        cls.reference = run(zero)

    def test_proxy_material_and_labels(self):
        result = self.result
        self.assertEqual(result["modelId"], "alsi10mg-al6061-proxy-fixed-surface-evaporation-v1")
        self.assertEqual(result["schema"], "lpbf-alsi10mg-evaporative-result-v1")
        self.assertIs(result["experimentalValidation"], False)
        self.assertIs(result["productionReady"], False)
        self.assertEqual(result["disclosure"], DISCLOSURE)
        self.assertIn(DISCLOSURE, result["warnings"])
        self.assertIn("Research model", result["researchLabel"])
        m = result["provenance"]["material"]
        self.assertEqual(m["materialId"], "proxy:gan2021-al6061-for-alsi10mg")
        self.assertEqual((m["solidus_K"], m["liquidus_K"], m["boiling_K"], m["latentHeat_J_kg"]),
                         (873.0, 915.0, 2792.0, 3.8e5))
        self.assertEqual(result["geometry"]["liquidus_K"], 915.0)
        self.assertEqual(set(result["provenance"]["moduleSha256"]),
                         {"lpbf_alsi10mg_evaporative_solver.py", "lpbf_al_proxy_evaporation.py",
                          "lpbf_ti64_evaporative_solver.py", "lpbf_ti64_evaporation.py"})
        self.assertEqual(result["provenance"]["vaporSource"]["proxyAlloy"], "Al6061")
        json.dumps(result, allow_nan=False)

    def test_moving_source_energy_positive_evaporation_and_onset_refusal(self):
        result, reference = self.result, self.reference
        self.assertGreater(result["energy"]["evaporative_J"], 0.)
        self.assertTrue(math.isfinite(result["energy"]["evaporative_J"]))
        self.assertGreater(result["diagnosticEmittedMass_kg"], 0.)
        self.assertEqual(reference["energy"]["evaporative_J"], 0.)
        self.assertAlmostEqual(result["energy"]["input_J"], reference["energy"]["input_J"], delta=1e-12)
        self.assertLess(result["energy"]["stored_J"], reference["energy"]["stored_J"])
        for output in (result, reference):
            energy = output["energy"]
            losses = energy["base_J"]+energy["radiativeConvective_J"]+energy["evaporative_J"]
            independent = abs(energy["input_J"]-losses-energy["stored_J"])/max(
                abs(energy["input_J"]), abs(losses), abs(energy["stored_J"]), 1e-12)
            self.assertLessEqual(independent, 1e-9)
            self.assertEqual(energy["relativeResidual"], independent)
        self.assertTrue(result["gate"]["onset"])
        self.assertIsNotNone(result["gate"]["firstOnsetTime_s"])
        for key in ("depth_um", "length_um", "volume_um3"):
            self.assertIsNone(result["geometry"][key])
        self.assertIn("Use a model with surface motion and melt flow", result["geometry"]["refusalReason"])
        self.assertIn(result["geometry"]["widthWarning"], result["warnings"])
        self.assertGreater(result["geometry"]["width_um"], 0.)
        self.assertLessEqual(result["peakTemperature_K"], 5000.)
        print("actual moving-source acceptance:", result["energy"], result["peakTemperature_K"], result["gate"])

    def test_zero_flux_contract_keeps_geometry(self):
        reference = self.reference
        self.assertTrue(reference["gate"]["geometryAvailable"])
        self.assertGreater(reference["geometry"]["depth_um"], 0.)
        self.assertGreater(reference["geometry"]["volume_um3"], 0.)
        self.assertIsNone(reference["geometry"]["refusalReason"])
        self.assertEqual(reference["diagnosticEmittedMass_kg"], 0.)

    def test_missing_tension_refuses_geometry_with_active_evaporation(self):
        raw = scenario(); del raw["evaporation"]["surfaceTension_N_m"]
        result = run(raw)
        self.assertTrue(result["gate"]["unresolvedGeometry"])
        self.assertIsNone(result["geometry"]["depth_um"])
        self.assertIn("surface tension", result["geometry"]["refusalReason"])

    def test_strict_request_boundary(self):
        invalid = [dict(material="Ti-6Al-4V"), dict(material="Inconel 718"), dict(backend="auto"),
                   dict(surfaceMode="powder-layer"), dict(layers=2), dict(evaporationModel=True),
                   dict(properties={}), dict(measurements=[]), dict(power_W=True),
                   dict(mesh_um="40"), dict(maxDt_s=float("nan")), dict(timeout_s=20.)]
        for change in invalid:
            with self.subTest(change=change), self.assertRaises(ValueError):
                solver._request(scenario(**change))
        missing = scenario(); del missing["evaporation"]
        with self.assertRaises(ValueError):
            solver._request(missing)

    def test_cli_round_trip_and_failure(self):
        script = Path(__file__).with_name("lpbf_alsi10mg_evaporative_solver.py")
        proc = subprocess.run([sys.executable, str(script)], input=json.dumps(scenario(power_W=20.)),
                              text=True, capture_output=True, check=True)
        result = json.loads(proc.stdout)
        self.assertEqual(result["modelId"], "alsi10mg-al6061-proxy-fixed-surface-evaporation-v1")
        self.assertEqual(result["energy"]["evaporative_J"], 0.)
        self.assertEqual(proc.stderr, "")
        proc = subprocess.run([sys.executable, str(script)], input='{"invalid":true}',
                              text=True, capture_output=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(json.loads(proc.stdout)["status"], "error")


if __name__ == "__main__":
    unittest.main()
