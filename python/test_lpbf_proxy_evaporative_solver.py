"""Independent numerical/contract checks for the 316L and IN718 proxy evaporative CPU path."""
import json
import math
from pathlib import Path
import subprocess
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lpbf_proxy_evaporative_solver as solver  # noqa: E402
from lpbf_proxy_evaporation import validate_config  # noqa: E402
from lpbf_proxy_vapor_profiles import PROFILES  # noqa: E402
from lpbf_proxy_evaporative_solver import run, _accepted_step  # noqa: E402

R = 8.31446261815324
REFUSAL = ("The model's recoil/capillary onset criterion was exceeded; surface deformation "
           "and keyhole geometry are not resolved, so depth, length and volume are not reported.")
# material: (key, Tv, Lv, M, liquidus, low, high, sigma, model id, schema, onset power W)
ALLOYS = {
    "316L Stainless Steel": ("ss316l", 3122., 6.336e6, .056, 1723., 3022., 3522., 1.87,
                             "ss316l-gan2021-ss316-proxy-fixed-surface-evaporation-v1",
                             "lpbf-ss316l-evaporative-result-v1", 200.),
    "Inconel 718": ("in718", 3183., 374.3e3/.0586934, .0586934, 1609., 3083., 3583., 1.882,
                    "in718-fang2021-ni-proxy-fixed-surface-evaporation-v1",
                    "lpbf-in718-evaporative-result-v1", 150.),
}


def scenario(alloy, /, **changes):
    material = alloy
    key, tv, lv, m, liq, low, high, sigma, *_rest, power = ALLOYS[material]
    raw = dict(material=material, backend="reference", surfaceMode="bare-plate",
               power_W=power, speed_mm_s=1000., beamDiameter_um=100.,
               preheat_C=80., mesh_um=20., maxDt_s=1e-6, trackLength_um=100.,
               cooling_s=2e-5, sourcePenetration_um=20.,
               evaporation=dict(transitionLow_K=low, transitionHigh_K=high,
                                ambientPressure_Pa=101325., returnFraction=.18,
                                maxTemperature_K=5000., surfaceTension_N_m=sigma))
    raw.update(changes)
    return raw


def evaporation(material):
    return validate_config(scenario(material)["evaporation"], ALLOYS[material][4], PROFILES[ALLOYS[material][0]])


def step(material, T, H, dt, *, dx, rho, cp, k, tt, hh, source=None):
    return _accepted_step(T, H, dt, dx=dx, rho=rho, cp=np.full_like(T, cp),
                          conductivity=np.full_like(T, k), temperatures=tt,
                          enthalpies=hh, reference_h=0., ambient_K=273.15,
                          evaporation=evaporation(material),
                          convection=0., emissivity=0., base_boundary=False, source_factory=source)


class ManufacturedTests(unittest.TestCase):
    def test_cooling_independent_ode_first_order_and_energy(self):
        for material, (key, tv, lv, mm, *_rest) in ALLOYS.items():
            def rhs(t):  # independent high-branch ODE with the constants typed above
                p = 101325.*math.exp((lv*mm/R)*(1/tv-1/t))
                return -.82*p*math.sqrt(mm/(2*math.pi*R*t))*lv/(4000.*1000.*.001)
            duration, ref = 2e-5, 4500.
            h_ref = duration/4096
            for _ in range(4096):
                a = rhs(ref); b = rhs(ref+h_ref*a/2); c = rhs(ref+h_ref*b/2); d = rhs(ref+h_ref*c)
                ref += h_ref*(a+2*b+2*c+d)/6
            self.assertGreater(ref, ALLOYS[material][6])  # stays on the closed-form branch
            errors = []
            for n in (10, 20, 40):
                T = np.full((1, 1, 1), 4500.)
                H = T*4e6
                initial = float(H.sum())*.001**3
                energy = 0.
                for _ in range(n):
                    out = step(material, T, H, duration/n, dx=.001, rho=4000., cp=1000., k=1.,
                               tt=np.array([273.15, 5000.]), hh=np.array([273150., 5e6]))
                    T, H = out["temperature"], out["enthalpy"]
                    self.assertEqual(out["dt_s"], duration/n)
                    energy += out["evaporative_J"]
                removed = initial-float(H.sum())*.001**3
                self.assertLess(abs(removed-energy)/energy, 1e-10)
                errors.append(abs(float(T.item())-ref))
            orders = [math.log(errors[i]/errors[i+1], 2) for i in (0, 1)]
            with self.subTest(material=material):
                self.assertGreater(min(orders), .8)
            print(material, "cooling errors/order:", errors, orders)

    def test_actual_field_conduction_refines(self):
        for material in ALLOYS:
            errors = []
            for n in (8, 16, 32):
                dx = 1/n
                x = (np.arange(n)+.5)*dx
                T = np.broadcast_to((300+np.cos(math.pi*x))[:, None, None], (n, 2, 2)).copy()
                H = T.copy()
                t = 0.
                while t < .01:
                    out = step(material, T, H, min(.1*dx**2, .01-t), dx=dx, rho=1., cp=1., k=1.,
                               tt=np.array([273.15, 5000.]), hh=np.array([273.15, 5000.]))
                    T, H = out["temperature"], out["enthalpy"]
                    t += out["dt_s"]
                expected = 300+np.exp(-math.pi**2*.01)*np.cos(math.pi*x)
                errors.append(float(np.sqrt(np.mean((T[:, 0, 0]-expected)**2))))
            self.assertTrue(errors[0] > errors[1] > errors[2] > 0.)
            print(material, "conduction refinement L2:", errors)

    def test_rejected_candidate_commits_nothing_to_onset_or_energy_ledger(self):
        material = "Inconel 718"
        dt0, dx, rho = 1e-6, .001, 4000.
        T = np.full((2, 2, 2), 3300.)
        H = T*1000.*rho
        good, bad = np.full_like(T, 1e12), np.full_like(T, 1e22)
        seen = []
        def rejecting(dt, passive, capacity):
            seen.append(dt)
            field = bad if dt >= dt0 else good
            return dt, field, passive+field, 1., 0
        def direct(dt, passive, capacity):
            return dt, good, passive+good, 1., 0
        tt, hh = np.array([273.15, 5000.]), np.array([273150., 5e6])
        retried = step(material, T, H, dt0, dx=dx, rho=rho, cp=1000., k=1., tt=tt, hh=hh, source=rejecting)
        reference = step(material, T, H, dt0/2, dx=dx, rho=rho, cp=1000., k=1., tt=tt, hh=hh, source=direct)
        self.assertEqual(seen, [dt0, dt0/2])
        self.assertEqual(retried["rejectedCandidates"], 1)
        self.assertEqual(retried["input_J"], float(good.sum())*dx**3*(dt0/2))
        for key in ("input_J", "base_J", "radiativeConvective_J", "evaporative_J", "diagnosticMass_kg", "dt_s"):
            self.assertEqual(retried[key], reference[key], key)
        self.assertTrue(np.array_equal(retried["enthalpy"], reference["enthalpy"]))
        ev = evaporation(material)
        onset = [solver.update_onset(None, solver.surface_state(out["temperature"][:, :, -1], ev), ev, 50e-6, out["dt_s"])
                 for out in (retried, reference)]
        self.assertEqual(onset[0], onset[1])

    def test_persistent_invalid_candidate_raises_without_clipping(self):
        T = np.full((1, 1, 1), 2000.)
        def source(dt, passive, capacity):
            field = np.full_like(T, float("nan"))
            return dt, field, passive+field, 1., 0
        with self.assertRaises(ValueError):
            step("316L Stainless Steel", T, T.copy(), 1e-6, dx=1., rho=1., cp=1., k=1.,
                 tt=np.array([273.15, 5000.]), hh=np.array([273.15, 5000.]), source=source)
        self.assertEqual(float(T.item()), 2000.)


class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results, cls.references = {}, {}
        for material in ALLOYS:
            cls.results[material] = run(scenario(material))
            zero = scenario(material)
            zero["evaporation"] = dict(zero["evaporation"], transitionLow_K=4900., transitionHigh_K=5000.)
            cls.references[material] = run(zero)

    def test_proxy_material_labels_and_unresolved_evidence(self):
        for material, (key, tv, lv, mm, liq, *_r, model, schema, power) in ALLOYS.items():
            with self.subTest(material=material):
                result = self.results[material]
                profile = PROFILES[key]
                self.assertEqual((result["modelId"], result["schema"], result["alloy"]), (model, schema, material))
                self.assertIs(result["experimentalValidation"], False)
                self.assertIs(result["productionReady"], False)
                self.assertEqual(result["disclosure"], profile.disclosure)
                self.assertIn(profile.disclosure, result["warnings"])
                self.assertIn("Research model", result["researchLabel"])
                self.assertEqual(result["evidenceLabel"], "Unresolved")
                self.assertEqual(result["evidence"]["unresolvedInputs"], ["transitionLow_K", "transitionHigh_K"])
                self.assertIn(result["evidence"]["summary"], result["warnings"])
                m = result["provenance"]["material"]
                self.assertTrue(m["materialId"].startswith("proxy:"))
                self.assertEqual((m["liquidus_K"], m["boiling_K"]), (liq, tv))
                self.assertEqual(set(result["provenance"]["moduleSha256"]),
                                 {"lpbf_proxy_evaporative_solver.py", "lpbf_proxy_evaporation.py",
                                  "lpbf_proxy_vapor_profiles.py", "lpbf_ti64_evaporative_solver.py",
                                  "lpbf_ti64_evaporation.py"})
                json.dumps(result, allow_nan=False)

    def test_moving_source_energy_positive_evaporation_and_onset_refusal(self):
        for material in ALLOYS:
            with self.subTest(material=material):
                result, reference = self.results[material], self.references[material]
                self.assertGreater(result["energy"]["evaporative_J"], 0.)
                self.assertGreater(result["diagnosticEmittedMass_kg"], 0.)
                self.assertEqual(reference["energy"]["evaporative_J"], 0.)
                self.assertAlmostEqual(result["energy"]["input_J"], reference["energy"]["input_J"], delta=1e-12)
                self.assertLess(result["energy"]["stored_J"], reference["energy"]["stored_J"])
                for output in (result, reference):
                    e = output["energy"]
                    losses = e["base_J"]+e["radiativeConvective_J"]+e["evaporative_J"]
                    independent = abs(e["input_J"]-losses-e["stored_J"])/max(
                        abs(e["input_J"]), abs(losses), abs(e["stored_J"]), 1e-12)
                    self.assertLessEqual(independent, 1e-9)
                    self.assertEqual(e["relativeResidual"], independent)
                self.assertTrue(result["gate"]["onset"])
                for key in ("depth_um", "length_um", "volume_um3"):
                    self.assertIsNone(result["geometry"][key])
                self.assertEqual(result["geometry"]["refusalReason"], REFUSAL)
                self.assertIn(result["geometry"]["widthWarning"], result["warnings"])
                self.assertGreater(result["geometry"]["width_um"], 0.)
                self.assertTrue(reference["gate"]["geometryAvailable"])
                self.assertGreater(reference["geometry"]["depth_um"], 0.)
                self.assertIsNone(reference["geometry"]["refusalReason"])
                print(material, "moving-source acceptance:", result["energy"]["relativeResidual"],
                      result["peakTemperature_K"], result["gate"]["firstOnsetTime_s"])

    def test_peak_near_scenario_ceiling_warning(self):
        # NIST AMB2022-03 IN718 case from the spec: 285 W, 960 mm/s, 67 um beam, 600 um track, 80 C.
        hot = run(scenario("Inconel 718", power_W=285., speed_mm_s=960., beamDiameter_um=67.,
                           trackLength_um=600., cooling_s=.0005))
        gap = 5000.-hot["peakTemperature_K"]
        self.assertLessEqual(gap, solver.PEAK_NEAR_CEILING_MARGIN_K)
        notes = [w for w in hot["warnings"] if "scenario ceiling" in w]
        self.assertEqual(len(notes), 1)
        self.assertIn(f"{gap:.0f} K below the scenario ceiling 5000 K", notes[0])
        self.assertIn("computational limit, not a physical validity limit", notes[0])
        self.assertIn("surface motion, melt flow and plume", notes[0])
        self.assertIn("presentation choice and not a physical threshold", notes[0])
        for material in ALLOYS:  # the cooler class cases stay well below the margin
            self.assertLess(self.results[material]["peakTemperature_K"], 5000.-solver.PEAK_NEAR_CEILING_MARGIN_K)
            self.assertFalse([w for w in self.results[material]["warnings"] if "scenario ceiling" in w], material)

    def test_missing_tension_refuses_geometry_with_active_evaporation(self):
        raw = scenario("Inconel 718"); del raw["evaporation"]["surfaceTension_N_m"]
        result = run(raw)
        self.assertTrue(result["gate"]["unresolvedGeometry"])
        self.assertIsNone(result["geometry"]["depth_um"])
        self.assertIn("surface tension", result["geometry"]["refusalReason"])
        self.assertEqual(result["evidence"]["inputBasis"]["surfaceTension_N_m"]["status"], "omitted")

    def test_strict_request_boundary(self):
        for material in ALLOYS:
            invalid = [dict(material="Ti-6Al-4V"), dict(material="AlSi10Mg"), dict(material="316L"),
                       dict(material=None), dict(backend="auto"), dict(surfaceMode="powder-layer"), dict(layers=2),
                       dict(evaporationModel=True), dict(properties={}), dict(power_W=True),
                       dict(mesh_um="40"), dict(maxDt_s=float("nan")), dict(timeout_s=20.)]
            for change in invalid:
                with self.subTest(material=material, change=change), self.assertRaises(ValueError):
                    solver._request(scenario(material, **change))
            missing = scenario(material); del missing["evaporation"]
            with self.assertRaises(ValueError):
                solver._request(missing)
        unnamed = scenario("Inconel 718"); del unnamed["material"]
        with self.assertRaises(ValueError):
            solver._request(unnamed)

    def test_cli_round_trip_and_failure(self):
        script = Path(__file__).with_name("lpbf_proxy_evaporative_solver.py")
        for material, spec in ALLOYS.items():
            proc = subprocess.run([sys.executable, str(script)], input=json.dumps(scenario(material, power_W=20.)),
                                  text=True, capture_output=True, check=True)
            result = json.loads(proc.stdout)
            self.assertEqual(result["modelId"], spec[8])
            self.assertEqual(result["energy"]["evaporative_J"], 0.)
            self.assertEqual(proc.stderr, "")
        proc = subprocess.run([sys.executable, str(script)], input='{"invalid":true}', text=True, capture_output=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(json.loads(proc.stdout)["status"], "error")
        proc = subprocess.run([sys.executable, str(script)], input=json.dumps(scenario("Inconel 718", power_W=-1.)),
                              text=True, capture_output=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(json.loads(proc.stdout)["modelId"], ALLOYS["Inconel 718"][8])


if __name__ == "__main__":
    unittest.main()
