"""Read-only, synthetic physics checks for the Ti64 SOL-C consultation.

Run: python -I -B docs/research/scripts/check_sol_c_ti64_keyhole_consult.py --check
No datasets, fixtures, research runners, process maps or output files are loaded.
The independent oracles are an analytic Rosenthal gradient, a Neumann heat
kernel, and a time-integral derivation of the finite-dwell Gaussian temperature.
Passing is numerical verification, not experimental validation.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "python"))

import numpy as np
from scipy.integrate import quad
from scipy.optimize import minimize_scalar

import lpbf_solidification_estimates as sol
from four_alloy_materials import kernel_properties, thermal_props


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def close(actual, expected, tolerance=1e-8):
    require(math.isfinite(actual) and math.isfinite(expected), "nonfinite comparison")
    require(abs(actual - expected) <= tolerance * max(abs(expected), 1e-20),
            f"{actual} != {expected} within relative {tolerance}")


def load_p8_kernel():
    spec = importlib.util.spec_from_file_location(
        "consult_p8_kernel", Path(__file__).with_name("p8_cavity_kernel.py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def gaussian_gain_time_integral(k, alpha, radius, absorptivity, speed, x, age=None):
    """Independent half-space surface Green function, integrated over source age.

    The 2D convolution of normalized q=2Q/(pi*a^2) exp(-2r^2/a^2)
    with the heat kernel leaves Q/[pi*(a^2/2+4*alpha*t)]. The Neumann
    surface factor is sqrt(alpha)/(k*sqrt(pi*t)). Substitute t=u^2
    to remove its integrable endpoint singularity. age=None is a moving
    source for the entire past; finite age with speed=0 is the dwell model.
    """
    def integrand(u):
        spread = radius**2 / 2 + 4 * alpha * u*u
        return (2 * absorptivity * math.sqrt(alpha) / (k * math.pi**1.5 * spread)
                * math.exp(-(x + speed*u*u)**2 / spread))
    upper = math.inf if age is None else math.sqrt(age)
    return quad(integrand, 0, upper, epsabs=1e-8, epsrel=1e-10, limit=160)[0]


def p8_checks():
    p8 = load_p8_kernel()
    results = []
    for alloy in ("ti6al4v", "alsi10mg"):
        props = thermal_props(alloy)
        kp = kernel_properties(alloy, 293.15)
        ti = alloy == "ti6al4v"
        mat = p8.Material(
            alloy, kp["kernel_conductivity_W_mK"], kp["kernel_density_kg_m3"],
            kp["kernel_specific_heat_J_kgK"], kp["T_liq_K"], 3560. if ti else 2743.,
            props["absorptivity_IR"], 9.255e6 if ti else 284000 / .0269815384,
            .048 if ti else .0269815384, props["latent_heat_fusion_J_kg"],
            props["specific_heat_liquid_J_kgK"])
        v, d = .8, 80e-6
        a = d / 2
        threshold = p8.threshold_temperature(mat)
        # Independent pressure inversion: .6*p_sat(Tstar) = p_ambient.
        exponent = mat.Lv * mat.Mw / 8.31446261815324 * (1 / mat.Tv - 1 / threshold)
        close(.6 * math.exp(exponent), 1.)
        # This time-domain integral does not call the P8 gain or its atan form.
        dwell_gain = gaussian_gain_time_integral(mat.K, mat.alpha, a, mat.A0, 0., 0., a/v)
        pstar = (threshold - mat.T0) / dwell_gain
        close(p8.onset_power(mat, v, d), pstar)
        stationary = gaussian_gain_time_integral(mat.K, mat.alpha, a, mat.A0, 0., 0.)
        close(stationary, mat.A0 / (math.sqrt(2*math.pi) * mat.K * a))
        peak = minimize_scalar(
            lambda eta: -gaussian_gain_time_integral(
                mat.K, mat.alpha, a, mat.A0, v, eta*a),
            bounds=(-4., 0.), method="bounded", options={"xatol": 1e-10})
        require(peak.success and -3.99 < peak.x < -.001, "moving peak not interior")
        moving_pstar = (threshold - mat.T0) / -peak.fun
        close(p8.onset_power(mat, v, d, "gaussian_peak"), moving_pstar, 2e-8)
        ke_at_pstar = mat.A0*pstar / ((mat.Tm-mat.T0)*math.pi*mat.rho*mat.cp
                                            * math.sqrt(mat.alpha*v*a**3))
        results.append(dict(alloy=alloy, speed_m_s=v, diameter_m=d,
                            preheat_K=mat.T0, conductivity_W_mK=mat.K,
                            cp_J_kgK=mat.cp, density_kg_m3=mat.rho, absorptivity=mat.A0,
                            threshold_K=threshold, dwell_Pstar_W=pstar,
                            moving_Gaussian_Pstar_W=moving_pstar,
                            Ke_at_Pstar_same_tuple=ke_at_pstar))
    return results


def enthalpy_oracle(props, power, speed, diameter, preheat):
    """Algebraically reduced SI expression: denominator contains sqrt(rho*cp*k)."""
    capacity = props["density_kg_m3"] * props["specific_heat_J_kgK"]
    return (props["absorptivity_index_IR"] * power
            / ((props["liquidus_C"] - preheat)
               * math.sqrt(math.pi * capacity * props["thermal_conductivity_W_mK"]
                           * speed * (diameter/2)**3)))


def front_oracle(parent, thermal, process):
    kp = kernel_properties("ti6al4v", process["preheat_C"] + 273.15)
    k, alpha = kp["kernel_conductivity_W_mK"], kp["alpha_m2_s"]
    q = thermal["processParameters"]["conductionAbsorptivity"] * process["power_W"]
    v = process["speed_mm_s"] * 1e-3
    regularizer = max(process["beamDiameter_um"] * 1e-6 / (2*math.sqrt(2)), 8e-6)
    front = sol.sample_front(parent["T_fn"], parent["T_liq"], parent["v_scan"],
                             parent["x_rear"], parent["search_depth"])
    rows = sol.valid_samples(front)
    require(len(rows) == 32, "default branch lost samples")
    error = 0.
    for row in rows:
        xyz = row["position_m"]
        position = np.array([xyz["x"], xyz["y"], xyz["z"]])
        radius = float(np.linalg.norm(position))
        beta = v / (2*alpha)
        rise = q * math.exp(-beta*(radius + position[0])) / (
            2*math.pi*k*math.sqrt(radius**2 + regularizer**2))
        analytic = rise * (-position/(radius**2 + regularizer**2)
                           - beta*(position/radius + np.array([1., 0., 0.])))
        close(process["preheat_C"] + rise, parent["T_liq"], 1e-10)
        numeric = np.array([row["gradient_K_m"][key] for key in ("gx", "gy", "gz")])
        relative = float(np.linalg.norm(numeric-analytic) / np.linalg.norm(analytic))
        error = max(error, relative)
        require(relative < 2e-5, "sample derivative fails independent analytic oracle")
        growth = v * analytic[0] / float(np.linalg.norm(analytic))
        close(row["R_m_s"], growth, 2e-5)
        close(row["coolingRate_K_s"], v*analytic[0], 2e-5)
        require(0 < growth <= v, "not a rear solidifying point")
    return dict(summary=sol.thermal_summary(front), branch=front["branch"],
                analyticGradientMaxRelativeError=error)


def served_checks():
    props = thermal_props("ti6al4v")
    rows = []
    default_front = None
    cases = [(p, v, 80., 80.) for v in (700., 940., 1200.) for p in (100., 150., 200., 280.)]
    cases += [(280., 940., 80., 25.), (280., 940., 80., 200.), (280., 940., 160., 80.)]
    for power, speed, beam, preheat in cases:
        process = dict(power_W=power, speed_mm_s=speed, beamDiameter_um=beam,
                       preheat_C=preheat, layerThickness_um=40., hatch_um=100.)
        thermal, parent = sol.served_solve("Ti-6Al-4V", process, "rosenthal")
        h = enthalpy_oracle(props, power, speed*1e-3, beam*1e-6, preheat)
        close(thermal["processParameters"]["normalizedEnthalpy"], round(h, 2), 1e-10)
        capacity = props["density_kg_m3"] * props["specific_heat_J_kgK"]
        pe = speed*1e-3 * beam*1e-6 / (2*props["thermal_conductivity_W_mK"]/capacity)
        blend = min(1., max(0., (h-15.)/15.))
        fabbro = (props["absorptivity_IR"]*power*blend
                  / (props["thermal_conductivity_W_mK"]*(props["boiling_C"]-preheat)
                     * (2.4*pe + 3.)))
        # Independent global centre-plane depth maximum, not the served four-probe extent.
        front = sol.sample_front(parent["T_fn"], parent["T_liq"], parent["v_scan"],
                                 parent["x_rear"], parent["search_depth"], count=8, refine=False)
        require(front["branch"] is not None, "synthetic process did not melt")
        depth = front["branch"]["zBottom_m"]
        kp = kernel_properties("ti6al4v", preheat + 273.15)
        ke_kernel = (props["absorptivity_IR"]*power
                     / ((props["liquidus_C"]-preheat)*math.pi*kp["kernel_density_kg_m3"]
                        * kp["kernel_specific_heat_J_kgK"]
                        * math.sqrt(kp["alpha_m2_s"]*speed*1e-3*(beam*1e-6/2)**3)))
        # Well separated examples only; no hard boundary is inferred from this check.
        require(abs(fabbro-depth) > 1e-6, "case too close to depth crossover for this oracle")
        require(parent["depth_from_keyhole_leg"] == (fabbro > depth),
                "served controlling leg disagrees with independent depth maximum")
        rows.append(dict(power_W=power, speed_mm_s=speed, diameter_um=beam,
                         preheat_C=preheat, H=h, Ke_same_RT_tuple=h/math.sqrt(math.pi),
                         Ke_kernel_flat_absorption=ke_kernel,
                         fabbro_blend=blend, fabbro_Pe=pe, fabbro_depth_um=fabbro*1e6,
                         global_conduction_depth_um=depth*1e6,
                         keyhole_controls=parent["depth_from_keyhole_leg"]))
        if (power, speed, beam, preheat) == (280., 940., 80., 200.):
            default_front = front_oracle(parent, thermal, process)
    require(any(row["keyhole_controls"] for row in rows), "no keyhole case exercised")
    require(any(not row["keyhole_controls"] for row in rows), "no conduction case exercised")
    # Radius cubed and mm/s conversion errors must change the independent result.
    nominal = enthalpy_oracle(props, 280., .94, 80e-6, 80.)
    close(enthalpy_oracle(props, 280., .94, 160e-6, 80.), nominal/2**1.5)
    close(enthalpy_oracle(props, 280., 940., 80e-6, 80.), nominal/math.sqrt(1000))
    payload = {"params": dict(materialName="Ti-6Al-4V", power_W=280., speed_mm_s=940.,
                              beamDiameter_um=80., preheat_C=200.,
                              layerThickness_um=40., hatch_um=100.)}
    refused = sol.compute_solidification_estimates(payload)
    surrogate = sol.compute_solidification_estimates(
        {**payload, "options": {"conductionSurrogate": True}})
    require(all(q["value"] is None for q in refused["quantities"].values()),
            "the reported default-refusal behavior changed")
    require(surrogate["surrogate"] == "conduction-field", "surrogate identity lost")
    for key, summary in default_front["summary"].items():
        close(surrogate["quantities"][key]["value"], summary["median"])
    return dict(cases=rows, defaultFront=default_front,
                existingDefaultAllNull=True,
                surrogateValues={key: q["value"] for key, q in surrogate["quantities"].items()})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", required=True)
    parser.parse_args()
    result = dict(p8=p8_checks(), served=served_checks())
    print(json.dumps(result, indent=2, allow_nan=False))
    print("PASS: independent SI, Gaussian normalization, pressure, switch and front-gradient checks")


if __name__ == "__main__":
    main()
