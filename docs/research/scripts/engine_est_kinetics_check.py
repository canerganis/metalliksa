"""Source-bound, research-only kinetics replay. No served imports, measurements or network.

Run: python -I docs/research/scripts/engine_est_kinetics_check.py --check
Requires the local author-hosted Salsi PDF named in engine_est_cet_kinetics.md,
and Poppler pdftotext. Missing/changed source bytes fail, never silently skip.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, localcontext
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[3]
PDF = ROOT / "papers/engine_est_salsi2018.pdf"
SHA256 = "afd81903615318de59b3f0b853e88c1dde87eab075f9aab0624d0cedccebbc94"


def source_page(page: int) -> str:
    proc = subprocess.run(["pdftotext", "-f", str(page), "-l", str(page),
                           "-raw", "-enc", "UTF-8", str(PDF), "-"],
                          capture_output=True, check=True)
    return proc.stdout.decode("utf-8").replace("\u2212", "-")


def read_parameters():
    if hashlib.sha256(PDF.read_bytes()).hexdigest() != SHA256:
        raise AssertionError("Source bytes changed: obtain/authenticate the specified author copy")
    p12, p14 = source_page(12), source_page(14)
    ms = float(re.search(r"Tm = (\d+)\s*\u25e6C and km = ([\d.]+)", p12)[1])
    km = float(re.search(r"Tm = (\d+)\s*\u25e6C and km = ([\d.]+)", p12)[2])
    # Source provenance check: adopted assumptions, not a fit by Salsi.
    normalized = " ".join(p12.split())
    assert re.search(r"assuming Tm = 575\s*\u25e6C and km = 0\.005 as in \[10\]", normalized)
    references = " ".join(source_page(20).split())
    assert re.search(r"10\. Charles Murgau, C\.; Pederson, R\.; Lindgren, L\.", references)
    # This author copy contains an old, overlapping text layer. Select the final
    # publisher Table 3 layer, whose visible rows were also checked in a render.
    table = p14.split("Table 3.", 1)[1].split("The model has been tested", 1)[0]
    points = [(float(t), float(eq), float(ti), float(tf)) for t, eq, ti, tf in
              re.findall(r"(?m)^(400|500|700) ([\d.]+) (\d+) (\d+)\s*$", table)]
    assert len(points) == 3, "Cannot recover the three visible Table 3 parameter rows"
    assert "Xi = 0.3, Xf = 0.9" in table
    return ms, km, points


def fit_jmak(t30, t90):
    if not 0 < t30 < t90:
        raise ValueError("Need positive ordered transformation times")
    p = math.log(math.log(.1) / math.log(.7)) / math.log(t90 / t30)
    k = -math.log(.7) / t30 ** p
    return k, p


def interpolate(points, temperature):
    if not math.isfinite(temperature) or not points[0][0] <= temperature <= points[-1][0]:
        raise ValueError("Missing temperature-supported dissolution parameters")
    for a, b in zip(points, points[1:]):
        if a[0] <= temperature <= b[0]:
            w = (temperature - a[0]) / (b[0] - a[0])
            return tuple(x + w * (y - x) for x, y in zip(a[1:], b[1:]))
    raise AssertionError("Temperature bracket missing")


def dissolution(points, temperature, seconds):
    if not math.isfinite(seconds) or seconds < 0:
        raise ValueError("Need a finite nonnegative hold time")
    eq, t30, t90 = interpolate(points, temperature)
    k, p = fit_jmak(t30, t90)
    # Relative to the martensite entering this one isothermal hold, not a
    # phase fraction of an unspecified initial specimen.
    return eq * -math.expm1(-k * seconds ** p)


def km_fraction(ms, km, temperature):
    return -math.expm1(-km * max(0., ms - temperature))


def independent_integral(k, p, t, steps):
    # Numerically integrate the distinct hazard ODE dS/dt=-p*k*t^(p-1)*S.
    # The log-survival integral uses a trapezoidal mesh, not the JMAK exp input.
    # Quadratic time map regularizes the integrable t=0 hazard for p<1.
    h = 1. / steps
    total = 0.
    for i in range(steps + 1):
        u = i * h
        hazard = 0. if i == 0 else p * k * (t * u * u) ** (p - 1.) * 2 * t * u
        total += hazard * (.5 if i in (0, steps) else 1.)
    return -math.expm1(-h * total)


def cet_boundary(p, rate, target, morphology):
    """Invert the named A7 envelope, retaining its physical gates at the root."""
    if not 0 < target < 1 or not math.isfinite(rate) or rate <= 0:
        raise ValueError("nonphysical-input")
    q = p.m * p.c * (1-p.k)
    tip = math.sqrt(8 * q * p.gamma * rate / p.d)
    if p.nuclei <= 0 or tip <= p.activation:
        return None  # No activated positive-density population, no boundary.
    g = tip / 3 * (1-(p.activation/tip)**3) * (
        4*math.pi*p.nuclei/(3*(-math.log1p(-target))))**(1/3)
    state = morphology(p, g, rate)
    return g if state["fraction"] is not None else None


def radius_integral(p, gradient, rate, steps):
    """Independent integration of dendrite growth speed through undercooling.

    v_tip(delta)=D*delta^2/(8*Q*Gamma), d(delta)/dt=G*R.
    Midpoint quadrature does not use the integrated radius expression or Gcrit.
    """
    q = p.m * p.c * (1-p.k)
    tip = math.sqrt(8*q*p.gamma*rate/p.d)
    if tip <= p.activation:
        return 0.
    dtemp = (tip-p.activation)/steps
    return sum(p.d*(p.activation+(i+.5)*dtemp)**2/(8*q*p.gamma)
               *dtemp/(gradient*rate) for i in range(steps))


def check_cet():
    # Import the source-only research model, never the served physics engine.
    path = Path(__file__).with_name("sol_c_a6_morph_phase_check.py")
    spec = importlib.util.spec_from_file_location("_engine_est_a7_research", path)
    model = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = model  # Required by the source-only dataclass.
    spec.loader.exec_module(model)
    assert set(model.PARAMS) == {"ti64", "alsi10mg", "in718", "in625", "316l"}
    from dataclasses import replace
    roots = {}
    for alloy, p in model.PARAMS.items():
        q = p.m*p.c*(1-p.k)
        limit = q/p.k
        if p.eutectic_ce is not None:
            limit = min(limit, p.m*(p.eutectic_ce-p.c))
        tip = (limit+p.activation)/2
        rate = tip*tip*p.d/(8*q*p.gamma)
        boundaries = []
        for target in (.0049, .49):
            gradient = cet_boundary(p, rate, target, model.morphology)
            assert gradient is not None, (alloy, "manufactured active point failed")
            state = model.morphology(p, gradient, rate)
            coarse = radius_integral(p, gradient, rate, 400)
            fine = radius_integral(p, gradient, rate, 800)
            assert abs(fine-state["radius_m"]) < abs(coarse-state["radius_m"])
            assert math.isclose(fine, state["radius_m"], rel_tol=5e-7)
            numeric_fraction = -math.expm1(-4*math.pi/3*p.nuclei*fine**3)
            assert math.isclose(numeric_fraction, target, rel_tol=2e-6)
            # Distinct numerical root solve using only quadrature and impingement.
            low, high = gradient/4, gradient*4
            for _ in range(42):
                mid = (low+high)/2
                radius = radius_integral(p, mid, rate, 80)
                fraction = -math.expm1(-4*math.pi/3*p.nuclei*radius**3)
                if fraction > target:
                    low = mid
                else:
                    high = mid
            assert math.isclose((low+high)/2, gradient, rel_tol=5e-5)
            boundaries.append(gradient)
            # Planar-stable points must still refuse the grain envelope.
            planar_g = 2*(q/p.k)*rate/p.d
            assert model.morphology(p, planar_g, rate)["fraction"] is None
        assert boundaries[0] > boundaries[1] > 0
        roots[alloy] = {"R_m_s": rate, "Gcrit_K_m": boundaries}
        assert cet_boundary(replace(p, nuclei=0.), rate, .49, model.morphology) is None
        assert cet_boundary(replace(p, activation=2*tip), rate, .49, model.morphology) is None
        # A formally inverted boundary can itself become planar-stable.
        assert cet_boundary(replace(p, nuclei=1e100), rate, .49, model.morphology) is None
        # No solutal dendrite tip above its own P, even if algebra yields roots.
        invalid_rate = (2*q/p.k)**2*p.d/(8*q*p.gamma)
        assert cet_boundary(p, invalid_rate, .49, model.morphology) is None
        if p.eutectic_ce is not None:
            eutectic_tip = p.m*(p.eutectic_ce-p.c)
            eutectic_rate = (1.01*eutectic_tip)**2*p.d/(8*q*p.gamma)
            assert cet_boundary(p, eutectic_rate, .49, model.morphology) is None
    return roots


def check():
    ms, km, points = read_parameters()
    report = {"sourceSha256": SHA256, "sourceRows": points, "dissolvedAtOneHour": {}}
    for t, eq, t30, t90 in points:
        k, p = fit_jmak(t30, t90)
        assert 0 < eq <= 1 and p > .5 and k > 0
        # Parameter round-trip smoke checks, not independent model evidence.
        for secs, progress in ((t30, .3), (t90, .9)):
            assert math.isclose(dissolution(points, t, secs), eq * progress, rel_tol=2e-14)
        # Off-fit-point numerical ODE check and mesh refinement.
        secs = math.sqrt(t30 * t90)
        exact = dissolution(points, t, secs) / eq
        coarse = independent_integral(k, p, secs, 1500)
        fine = independent_integral(k, p, secs, 3000)
        assert abs(fine - exact) < 1e-6 and abs(fine - exact) < abs(coarse - exact)
        # Competing implementation mistakes change the result materially.
        assert not math.isclose(-math.expm1(-k * secs), exact, rel_tol=.01)
        assert not math.isclose(dissolution(points, t, secs / 3600) / eq, exact, rel_tol=.01)
        assert dissolution(points, t, 0) == 0
        report["dissolvedAtOneHour"][str(t)] = dissolution(points, t, 3600.)
    # Precision smoke comparison of the SAME KM expression in Decimal.
    for preheat in (25., 150., 300., 550.):
        evaluation = preheat + 25.
        with localcontext() as ctx:
            ctx.prec = 50
            expected = 1 - (-Decimal(str(km)) * max(Decimal(0), Decimal(str(ms - evaluation)))).exp()
        actual = km_fraction(ms, km, evaluation)
        assert math.isclose(actual, float(expected), rel_tol=1e-14, abs_tol=1e-15)
    assert km_fraction(ms, km, ms) == 0
    assert km_fraction(ms, km, ms + 1) == 0
    assert km_fraction(ms, km, 175) < km_fraction(ms, km, 50)
    # Partition a constant-temperature hold: equivalent-time restart must
    # reproduce an uninterrupted hold. This catches treating every step as new.
    k, p = fit_jmak(points[1][2], points[1][3])
    state = 0.
    for delta_t in (100., 200., 300., 400.):
        tau = (-math.log1p(-state) / k) ** (1/p) if state else 0.
        state = -math.expm1(-k * (tau + delta_t) ** p)
    assert math.isclose(state, -math.expm1(-k * 1000 ** p), rel_tol=1e-14)
    for temp, secs in ((399., 1.), (701., 1.), (500., -1.), (math.nan, 1.)):
        try:
            dissolution(points, temp, secs)
        except ValueError:
            continue
        raise AssertionError("Invalid input incorrectly admitted")
    report["kmAtPreheat150_plus25C"] = km_fraction(ms, km, 175.)
    report["cetBoundaryChecks"] = check_cet()
    report["checks"] = "PASS: source extraction and adopted-[10] attribution, independent JMAK hazard ODE/refinement, unit/exponent mutations, hold restart, refusal inputs, five-alloy CET radius quadrature and boundary inversion with activation/chi/tip/eutectic gates"
    report["smokeOnly"] = "JMAK fitted-point round trips; KM Decimal precision comparison. Literal fraction asserts removed."
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", required=True)
    parser.parse_args()
    check()
