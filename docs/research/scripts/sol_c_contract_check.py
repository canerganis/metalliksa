"""Amendment 5 algebra/aggregation/envelope check, not a served SOL-C implementation.

Run: python -I -B docs/research/scripts/sol_c_contract_check.py --check
Stdlib only; no solver imports, physical rows, source downloads or output files.
Dimensional test numbers below are manufactured, never material constants.
"""
from __future__ import annotations

import argparse
import importlib.util
import itertools
import json
import math
from pathlib import Path
import random
import statistics
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]


def require(test, message):
    if not test:
        raise AssertionError(message)


def intervals(box, speed):
    """Conservative positive-solidification box enclosure; no independence claim."""
    require(math.isfinite(speed) and speed > 0, "invalid speed")
    require(len(box) == 3 and all(math.isfinite(a) and math.isfinite(b) and a <= b
                                for a, b in box), "invalid component interval")
    require(box[0][0] > 0, "normal sign unresolved")
    square_bounds = [(0 if a <= 0 <= b else min(a*a, b*b), max(a*a, b*b))
                     for a, b in box]
    g2lo = sum(a for a, _ in square_bounds)
    g2hi = sum(b for _, b in square_bounds)
    glo, ghi = math.sqrt(g2lo), math.sqrt(g2hi)
    xlo, xhi = box[0]
    # R and G/R use interval arithmetic. Wide bounds retain covariance safely;
    # cooling is simplified first to v*gx and does not double-count the norm.
    return ((glo, ghi), (speed*xlo/ghi, speed*xhi/glo),
            (speed*xlo, speed*xhi), (g2lo/(speed*xhi), g2hi/(speed*xlo)))


def local(vector, speed):
    g = math.sqrt(sum(c*c for c in vector))
    r = speed*vector[0]/g
    return g, r, speed*vector[0], g/r


def check():
    registry_path = ROOT / "python/quantity_envelope.py"
    spec = importlib.util.spec_from_file_location("sol_c_envelope_readonly", registry_path)
    registry = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(registry)
    reasons = {"invalid-interface-sample", "nonphysical-input", "insufficient-sample-support",
               "missing-source-constant", "missing-source-bound-model", "parent-unavailable",
               "outside-source-model-domain", "keyhole-field-inconsistent", "stale-parent-input",
               "incompatible-liquidus-parent", "missing-thermal-history", "solver-error", "not-requested"}
    require(reasons <= set(registry.REASON_CODES), "new/renamed reason code")
    definitions = {"thermalGradient": ("liquidus-front-thermal-gradient", "K/m"),
                   "normalSpeed": ("liquidus-front-normal-speed", "m/s"),
                   "coolingRate": ("liquidus-front-cooling-rate", "K/s"),
                   "gOverR": ("liquidus-front-g-over-r", "K*s/m^2"),
                   "pdas": ("pdas-model-alternatives", "m"), "sdas": ("sdas", "m")}
    for definition, unit in definitions.values():
        require(registry.QUANTITY_DEFINITIONS[definition]["unit"] == unit, "wire unit changed")
    for definition in ("front-morphology", "solid-state-transformation"):
        require(not registry.QUANTITY_DEFINITIONS[definition]["categories"], "category admission changed")
    require(set(registry.UNCERTAINTY_KINDS) >= {"numerical-refinement", "parameter-sensitivity",
                                             "model-alternatives"}, "uncertainty vocabulary changed")

    rng = random.Random(51016)
    count = 0
    for _ in range(80):
        centre = (rng.uniform(1e5, 8e6), rng.uniform(-4e6, 4e6), rng.uniform(-8e6, 8e6))
        widths = [rng.uniform(.01, .4)*abs(c) for c in centre]
        box = tuple((c-w, c+w) for c, w in zip(centre, widths))
        v = rng.uniform(.1, 2)
        bands = intervals(box, v)
        # Independent point evaluation at all corners and random interior points.
        vectors = list(itertools.product(*box))
        vectors += [tuple(rng.uniform(a, b) for a, b in box) for _ in range(12)]
        for vector in vectors:
            vals = local(vector, v)
            require(all(lo*(1-1e-14) <= q <= hi*(1+1e-14)
                        for q, (lo, hi) in zip(vals, bands)), "band fails enclosure")
            require(math.isclose(vals[0]*vals[1], v*vector[0], rel_tol=1e-14), "kinematics")
            count += 1

    # Counterexample forces local nonlinear evaluation before aggregation.
    gs, rs = (1., 2., 100., 101.), (101., 100., 2., 1.)
    cooling = [g*r for g, r in zip(gs, rs)]
    wrong = statistics.median(gs)*statistics.median(rs)
    right = statistics.median(cooling)
    require(wrong > max(cooling) and right == 150.5, "median mutant survived")
    lower, upper = [q*.8 for q in cooling], [q*1.3 for q in cooling]
    for factors in itertools.product((0., .5, 1.), repeat=4):
        median = statistics.median([a+f*(b-a) for a, b, f in zip(lower, upper, factors)])
        require(statistics.median(lower) <= median <= statistics.median(upper), "median enclosure")

    refused = 0
    for bad in ((((-1., 1.), (1., 2.), (3., 4.)), 1.),
                (((0., 0.), (1., 2.), (3., 4.)), 1.),
                (((1., 2.), (1., 2.), (3., 4.)), 0.),
                (((1., math.inf), (1., 2.), (3., 4.)), 1.)):
        try:
            intervals(*bad)
        except AssertionError:
            refused += 1
    require(refused == 4, "invalid-input/sign mutant survived")
    # Fault injection: a wrong norm can preserve G*R but must fail G/R.
    vector, v = (2., 3., -6.), .8
    truth = local(vector, v)
    wrong_g = abs(vector[0])
    wrong_r = v*vector[0]/wrong_g
    require(math.isclose(wrong_g*wrong_r, truth[2]), "cancellation fixture invalid")
    require(not math.isclose(wrong_g/wrong_r, truth[3], rel_tol=1e-3), "norm mutant survived")
    return {"result": "PASS", "scope": "prospective-contract-software-only",
            "enclosed_vector_evaluations": count, "median_interval_cases": 81,
            "invalid_cases_refused": refused, "mutants_rejected": ["separate-medians", "wrong-norm-cancellation"],
            "served_channel_validated": False, "physical_validation": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", required=True, action="store_true")
    parser.parse_args()
    print(json.dumps(check(), sort_keys=True, allow_nan=False))
