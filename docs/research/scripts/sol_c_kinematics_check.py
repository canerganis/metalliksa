#!/usr/bin/env python3
"""RC2 independent component/norm/projection checks; no material/measurement imports.

python -I -B docs/research/scripts/sol_c_kinematics_check.py --check
All dimensional fixture parameters are manufactured software inputs, not alloy data.
Extract only named production functions by AST: never import the material authority,
read measured rows, run the served thermal result, or change production source.
"""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import math
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
FRONT = ROOT / "python/solidification_front.py"
THERMAL = ROOT / "python/lpbf_thermal_solver.py"


def extract(path, names, mutations=None):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    nodes = [copy.deepcopy(n) for n in tree.body
             if isinstance(n, ast.FunctionDef) and n.name in names]
    if {n.name for n in nodes} != set(names):
        raise AssertionError("Production function inventory changed")
    if mutations:
        for node in nodes:
            for child in ast.walk(node):
                if isinstance(child, ast.Assign):
                    for target in child.targets:
                        if isinstance(target, ast.Name) and target.id in mutations:
                            child.value = ast.parse(mutations[target.id], mode="eval").body
    scope = {"math": math}
    module = ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)] + nodes,
                        type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), str(path), "exec"), scope)
    return scope


NAMES = ("_t_scalar", "_grad_T", "_binary_z_liquidus", "map_solidification_front")


def norm(values):
    return math.sqrt(sum(v * v for v in values))


def relative(actual, reference):
    return abs(actual - reference) / max(abs(reference), 1e-30)


def gaussian(x, y, z):
    # Anisotropic level sets, every axis nonzero off the centre plane.
    return 300.0 + 1800.0 * math.exp(-((x / 160e-6)**2 + (y / 90e-6)**2 + (z / 65e-6)**2))


def gaussian_gradient(x, y, z):
    rise = gaussian(x, y, z) - 300.0
    return tuple(-2.0 * q * rise / length**2
                 for q, length in zip((x, y, z), (160e-6, 90e-6, 65e-6)))


def stencil_checks(scope):
    point = (-80e-6, 25e-6, 30e-6)
    expected = gaussian_gradient(*point)
    hs = (4e-6, 2e-6, 1e-6)
    errors = [[relative(a, e) for a, e in zip(scope["_grad_T"](gaussian, *point, h), expected)]
              for h in hs]
    # Central differences have O(h^2) truncation: halve h -> about fourfold decrease.
    orders = [[math.log(errors[j][i] / errors[j + 1][i], 2.0) for i in range(3)] for j in range(2)]
    # Nonzero surface derivative, deliberately unlike an adiabatic symmetric field:
    # detects the historical incorrect 2h denominator at z=0.
    def surface(x, y, z):
        return 500.0 + 2e6*x + 3e6*y + 4e6*z + 2e10*z*z
    surface_hs = (8e-6, 4e-6, 2e-6)
    surface_errors = [relative(scope["_grad_T"](surface, 0.0, 0.0, 0.0, h)[2], 4e6) for h in surface_hs]
    return {"h_m": hs, "componentRelativeErrors": errors, "observedOrders": orders,
            "surfaceRelativeErrors": surface_errors,
            "passed": all(1.95 < p < 2.05 for row in orders for p in row)
                      and max(errors[-1]) < 3e-4
                      and all(1.95 < surface_errors[i]/surface_errors[i+1] < 2.05 for i in range(2))}


def sampler_check(scope):
    captured = []
    original = scope["_grad_T"]
    def capture(fn, x, y, z, h):
        value = original(fn, x, y, z, h)
        captured.append((x, y, z, value))
        return value
    scope["_grad_T"] = capture
    try:
        result = scope["map_solidification_front"](gaussian, 1200.0, 0.8, 133.2e-6, 100e-6, 0.2e-6, n_samples=9)
    finally:
        scope["_grad_T"] = original
    if result is None or len(captured) != len(result["samples"]):
        return {"passed": False, "reason": "manufactured sample inventory not recovered"}
    errors = {name: [] for name in ("gx", "gy", "gz", "G", "nx", "R", "cooling", "G_over_R", "levelResidual")}
    for (x, y, z, got_grad), sample in zip(captured, result["samples"]):
        exact_grad = gaussian_gradient(x, y, z)
        G = norm(exact_grad)
        nx = exact_grad[0] / G
        R = 0.8 * nx
        expected = (G, nx, R, 0.8*exact_grad[0], G/R)
        actual = (sample["G_K_m"], sample["n_x"], sample["R_m_s"], sample["coolingRate_K_s"], sample["g_over_r"])
        for name, a, e in zip(("gx", "gy", "gz"), got_grad, exact_grad):
            errors[name].append(abs(a-e)/G if e == 0.0 else relative(a, e))
        for name, a, e in zip(("G", "nx", "R", "cooling", "G_over_R"), actual, expected):
            errors[name].append(relative(a, e))
        errors["levelResidual"].append(abs(gaussian(x, y, z)-1200.0))
    maxes = {k: max(v) for k, v in errors.items()}
    return {"samples": len(captured), "maxRelativeErrors": {k: v for k, v in maxes.items() if k != "levelResidual"},
            "maxLiquidusResidual_K": maxes["levelResidual"],
            "passed": all(v < 5e-5 for k, v in maxes.items() if k != "levelResidual")
                      and maxes["levelResidual"] < 0.1}


def rosenthal_checks(scope):
    source = extract(THERMAL, ("rosenthal_temperature_C",))["rosenthal_temperature_C"]
    # No physical alloy assignment: arbitrary smooth numerical regression fixture.
    params = (300.0, 100.0, 25.0, 0.8, 6e-6, 35e-6)
    def field(x, y, z):
        return source(x, y, z, *params)
    def exact(x, y, z):
        r = norm((x, y, z))
        rr2 = r*r + params[-1]**2
        a = params[3]/(2.0*params[4])
        rise = params[1]/(2*math.pi*params[2]*math.sqrt(rr2))*math.exp(-a*(r+x))
        # Independent closed-form differentiation of the recorded regularized field.
        return tuple(rise*(-q/rr2-a*(q/r+(1.0 if i == 0 else 0.0)))
                     for i, q in enumerate((x, y, z)))
    points = ((-100e-6, 18e-6, 25e-6), (-150e-6, -25e-6, 42e-6), (-60e-6, 8e-6, 14e-6))
    all_errors, orders = [], []
    for point in points:
        expected = exact(*point)
        errors = [[relative(a, e) for a, e in zip(scope["_grad_T"](field, *point, h), expected)]
                  for h in (0.8e-6, 0.4e-6, 0.2e-6)]
        all_errors.append(errors[-1])
        orders.extend(math.log(errors[i][j]/errors[i+1][j], 2.0) for i in range(2) for j in range(3))
    return {"componentRelativeErrors": all_errors, "orderRange": [min(orders), max(orders)],
            "passed": max(v for row in all_errors for v in row) < 2e-4
                      and all(1.9 < p < 2.1 for p in orders)}


def frame_checks():
    x, y, z = -80e-6, 25e-6, 30e-6
    speed, drift, dt = 0.8, 2e5, 1e-9
    grad = gaussian_gradient(x, y, z)
    G = norm(grad)
    expected_dt = -speed*grad[0]+drift
    def laboratory(t):
        return gaussian(x-speed*t, y, z)+drift*t
    observed_dt = (laboratory(dt)-laboratory(-dt))/(2*dt)
    exact_speed = (speed*grad[0]-drift)/G
    observed_speed = -observed_dt/G
    return {"laboratory_dTdt_K_s": observed_dt, "independent_dTdt_K_s": expected_dt,
            "normalSpeed_m_s": observed_speed, "beamFrame_dTdt_K_s": drift,
            "fluidVelocity_m_s": 0.0, "interfaceMovingInStaticFluid": exact_speed != 0.0,
            "passed": relative(observed_dt, expected_dt) < 1e-7
                      and relative(observed_speed, exact_speed) < 1e-7
                      and not math.isclose(exact_speed, 0.0)
                      and not math.isclose(exact_speed, speed*grad[0]/G, rel_tol=1e-3)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", required=True)
    parser.parse_args()
    scope = extract(FRONT, NAMES)
    checks = {"stencils": stencil_checks(scope), "actualSampler": sampler_check(scope),
              "actualRosenthalField": rosenthal_checks(scope), "frameAndTransient": frame_checks()}
    mutations = {
        "zero-y-gradient": {"dTdy": "0.0"},
        "half-z-gradient": {"dTdz": "0.5 * ((_t_scalar(T_fn, x, y, z+h)-_t_scalar(T_fn, x, y, z-h))/(2*h) if z-h >= 0 else (_t_scalar(T_fn, x, y, z+h)-_t_scalar(T_fn, x, y, z))/h)"},
        "double-norm": {"g_mag": "2 * math.sqrt(gx*gx+gy*gy+gz*gz)"},
        "omit-normal-projection": {"R_loc": "float(v_scan)"},
        "reverse-x-gradient": {"dTdx": "-(_t_scalar(T_fn,x+h,y,z)-_t_scalar(T_fn,x-h,y,z))/(2*h)"},
    }
    rejected = {}
    for name, mutation in mutations.items():
        mutant = extract(FRONT, NAMES, mutation)
        # Off-axis derivative check makes zero-y visible despite sampler y=0 symmetry.
        point = (-80e-6, 25e-6, 30e-6)
        exact = gaussian_gradient(*point)
        got = mutant["_grad_T"](gaussian, *point, 0.2e-6)
        components_ok = all(relative(a,e) < 5e-5 for a,e in zip(got,exact))
        rejected[name] = not (components_ok and sampler_check(mutant)["passed"])
    report = {"gate": "SOL-C-RC2", "evidenceKind": "manufactured-software-verification",
              "sourceFunctions": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in (FRONT, THERMAL)},
              "checks": checks, "mutationsRejected": rejected,
              "passed": all(c["passed"] for c in checks.values()) and all(rejected.values()),
              "limits": ["No experimental validation or alloy-specific uncertainty calibration.",
                         "Actual source functions are extracted, not the served request/envelope/channel.",
                         "Goldak/Eagar-Tsai derivative references and runtime transported tuples remain integration gates.",
                         "No aggregate-median, phase, morphology or spacing admission is inferred."]}
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
