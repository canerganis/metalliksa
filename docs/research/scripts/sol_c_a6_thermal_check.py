"""A6 research-only thermal sweep and tier oracle. No served channel is installed.

python -I -B docs/research/scripts/sol_c_a6_thermal_check.py --check
Stdlib only. Fixture numbers are manufactured, not alloy data or measured rows.
The live Rosenthal function is extracted by AST; no production module is imported.
"""
from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass, replace
import hashlib
import json
import math
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "python/lpbf_thermal_solver.py"


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def production_field():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef)
             and node.name == "rosenthal_temperature_C"]
    require(len(nodes) == 1, "live field function missing")
    module = ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)]
                        + nodes, type_ignores=[])
    scope = {"math": math}
    exec(compile(ast.fix_missing_locations(module), str(SOURCE), "exec"), scope)
    return scope["rosenthal_temperature_C"]


@dataclass(frozen=True)
class Inputs:
    power: float = 300.0
    absorption: float = 0.4
    conductivity: float = 25.0
    capacity: float = 600.0
    density: float = 8000.0
    speed: float = 0.8
    base: float = 300.0
    solidus: float = 1100.0
    liquidus: float = 1200.0
    radius: float = 35e-6


def admitted(p):
    return (all(math.isfinite(v) for v in vars(p).values()) and
            min(p.power, p.conductivity, p.capacity, p.density, p.speed, p.radius) > 0
            and 0 < p.absorption <= 1 and p.liquidus > p.base and p.liquidus > p.solidus
            and min(p.base,p.solidus) > -273.15)


def ofat(p):
    """Declared A6 scenarios, not confidence limits; no source attribution."""
    require(admitted(p), "nonphysical input")
    arms = [("nominal", p)]
    for name, endpoints in {
        "conductivity": (0.8*p.conductivity, 1.2*p.conductivity),
        "capacity": (0.8*p.capacity, 1.2*p.capacity),
        "density": (0.95*p.density, 1.05*p.density),
        "absorption": (0.8*p.absorption, min(1.0, 1.2*p.absorption)),
        # Quarter of the nominal freezing interval, not absolute Celsius.
        "liquidus": (p.liquidus-0.25*(p.liquidus-p.solidus), p.liquidus+0.25*(p.liquidus-p.solidus)),
    }.items():
        for index, value in enumerate(endpoints):
            arm = replace(p, **{name: value})
            require(admitted(arm), "invalid sensitivity arm")
            arms.append((f"{name}:{index}", arm))
    return arms


def temperature(source, p, x, y=0.0, z=0.0):
    return source(x, y, z, p.base, p.power*p.absorption, p.conductivity,
                  p.speed, p.conductivity/(p.density*p.capacity), p.radius)


def gradient(p, x, y, z):
    """Independent derivative on the live field's smooth, unclipped branch only."""
    r = math.sqrt(x*x+y*y+z*z)
    require(r > 0, "singular derivative")
    rr2 = r*r+p.radius*p.radius
    a = p.speed*p.density*p.capacity/(2*p.conductivity)
    require(2*p.conductivity/(p.density*p.capacity) > 1e-16, "diffusivity floor outside oracle")
    require(-45 < -a*(r+x) < 20, "exponent clip outside smooth oracle")
    rise = p.power*p.absorption/(2*math.pi*p.conductivity*math.sqrt(rr2))*math.exp(-a*(r+x))
    return tuple(rise*(-q/rr2-a*(q/r+(i == 0))) for i, q in enumerate((x, y, z)))


def kinematics(g, speed):
    require(speed > 0 and math.isfinite(speed), "invalid speed")
    require(all(math.isfinite(c) for c in g), "nonfinite gradient")
    G = math.sqrt(sum(c*c for c in g))
    require(G > 0 and g[0] > 0, "not a solidifying tuple")
    R = speed*g[0]/G
    return G, R, speed*g[0], G/R


def tail(source, p):
    """Rear surface crossing; manufactured simple branch only, not a served sampler."""
    require(admitted(p), "invalid field")
    lo, hi = -0.02, -1e-12
    require(temperature(source, p, lo) < p.liquidus < temperature(source, p, hi), "no liquidus crossing")
    for _ in range(70):
        mid = (lo+hi)/2
        if temperature(source, p, mid) < p.liquidus:
            lo = mid
        else:
            hi = mid
    return (lo+hi)/2


def location(source, p):
    x = 0.5*tail(source, p)
    lo, hi = 0.0, 0.02
    require(temperature(source,p,x,z=lo) > p.liquidus > temperature(source,p,x,z=hi), "depth bracket")
    for _ in range(70):
        mid = (lo+hi)/2
        if temperature(source,p,x,z=mid) > p.liquidus:
            lo = mid
        else:
            hi = mid
    return x, 0.0, (lo+hi)/2


def summary(source, p):
    # A single identified interior tuple tests sweep recomputation; A5 branch medians
    # are tested separately by sol_c_contract_check, never claimed by this fixture.
    point = location(source,p)
    require(abs(temperature(source, p, *point)-p.liquidus) < 1e-8, "root residual")
    return kinematics(gradient(p, *point), p.speed)


def tier(nominal, arms):
    if nominal is None:
        return "no-value", None
    require(all(math.isfinite(q) and q > 0 for q in nominal), "invalid nominal")
    if arms is None or len(arms) != 10 or any(arm is None for arm in arms):
        return "Physics estimate", None
    require(all(len(a) == len(nominal) and all(math.isfinite(q) and q > 0 for q in a)
                for a in arms), "bad sweep result")
    return "Estimated", tuple((min(row), max(row)) for row in zip(nominal, *arms))


def check():
    source = production_field()
    p = Inputs()
    arms = ofat(p)
    require(len(arms) == 11, "OFAT coverage")
    rows = [summary(source, arm) for _, arm in arms]
    reached, bands = tier(rows[0], rows[1:])
    require(reached == "Estimated", "tier1 unavailable")
    # Independent five-point derivatives and lab-frame time difference. These do
    # not derive their references by reusing gradient() or G*R cancellation.
    point = (-100e-6, 18e-6, 25e-6)
    h = 0.2e-6
    numeric = []
    for axis in range(3):
        values = []
        for offset in (-2, -1, 1, 2):
            q = list(point)
            q[axis] += offset*h
            values.append(temperature(source, p, *q))
        numeric.append((values[0]-8*values[1]+8*values[2]-values[3])/(12*h))
    exact = gradient(p, *point)
    require(all(math.isclose(a,b,rel_tol=2e-8) for a,b in zip(numeric,exact)), "live field derivative mismatch")
    dt = 1e-9
    observed_cooling = -(temperature(source,p,point[0]-p.speed*dt,*point[1:])
                         - temperature(source,p,point[0]+p.speed*dt,*point[1:]))/(2*dt)
    require(math.isclose(observed_cooling,kinematics(exact,p.speed)[2],rel_tol=1e-7), "lab-frame oracle")
    # Arm root must move. Reusing a nominal coordinate is a detectable error.
    q = replace(p, absorption=p.absorption*1.2)
    require(abs(tail(source,q)-tail(source,p)) > 1e-6, "root movement fixture")
    stale = kinematics(gradient(q,*location(source,p)),q.speed)
    require(not math.isclose(stale[0],summary(source,q)[0],rel_tol=.01), "fixed-root mutant survived")
    for name in ("capacity", "density"):
        changed = summary(source,replace(p,**{name:1.1*getattr(p,name)}))
        require(not math.isclose(changed[0],rows[0][0],rel_tol=1e-4), "diffusivity parent not exercised")
    # Celsius/Kelvin offset invariance includes the sweep, not just a gradient.
    kelvin = replace(p,base=p.base+273.15,solidus=p.solidus+273.15,liquidus=p.liquidus+273.15)
    require(all(math.isclose(a,b,rel_tol=1e-12) for a,b in zip(rows[0],summary(source,kelvin))), "temperature scale")
    require(all(math.isclose(a.liquidus+273.15,b.liquidus,abs_tol=1e-10)
                for (_,a),(_,b) in zip(arms,ofat(kelvin))), "absolute-temperature sweep mutant survived")
    require(all(lo <= row[i] <= hi for i,(lo,hi) in enumerate(bands) for row in rows), "scenario interval")
    require(tier(rows[0],None) == ("Physics estimate",None), "missing interval discarded valid physics")
    require(tier(rows[0],[]) == ("Physics estimate",None), "empty sweep incorrectly promoted")
    require(tier(rows[0],rows[1:-1]) == ("Physics estimate",None), "incomplete sweep incorrectly promoted")
    require(tier(rows[0],[None]) == ("Physics estimate",None), "failed arm discarded nominal")
    require(tier(None,None) == ("no-value",None), "invented nominal")
    refused = 0
    for vector in ((0,0,0),(-1,2,3),(float("nan"),2,3)):
        try:
            kinematics(vector,p.speed)
        except AssertionError:
            refused += 1
    require(refused == 3, "melting/zero/nonfinite accepted")
    for bad in (replace(p,absorption=1.2),replace(p,density=0),replace(p,speed=-1)):
        require(not admitted(bad), "bad parent admitted")
    try:
        gradient(p,.02,0,0)
    except AssertionError:
        pass
    else:
        raise AssertionError("clipped-branch derivative falsely claimed")
    require(kinematics((2,3,-6),.8) == (7,.8*2/7,1.6,7/(.8*2/7)), "independent 2,3,6 triangle oracle")
    # Point populations and prediction error are different objects.
    require(statistics.median([1,2,100,101])*statistics.median([101,100,2,1]) != 150.5,
            "aggregation counterexample")
    return {"result":"PASS", "scope":"A6-research-only", "ofat_fields":len(arms),
            "quantities":4, "tiers_tested":["Estimated","Physics estimate","no-value"],
            "rejected_mutants":["fixed-root","absolute-Celsius-range","melting-side","invalid-parent"],
            "nominal_fixture":rows[0],"ofat_intervals":bands,
            "source_sha256":hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
            "physical_validation":False,"served_channel_installed":False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check",action="store_true",required=True)
    parser.parse_args()
    print(json.dumps(check(),sort_keys=True,allow_nan=False))
