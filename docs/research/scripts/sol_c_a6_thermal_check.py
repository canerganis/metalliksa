"""A7 research-only rear-branch thermal sweep and tier oracle. No served channel is installed.

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
import inspect

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
    """A7 declared input scenarios, not error/confidence limits or source ranges."""
    require(admitted(p), "nonphysical input")
    arms = [("nominal", p)]
    for name, endpoints in {
        "conductivity": (0.8*p.conductivity, 1.2*p.conductivity),
        "capacity": (0.8*p.capacity, 1.2*p.capacity),
        "density": (0.95*p.density, 1.05*p.density),
        "absorption": (0.5*p.absorption, min(1.0, 1.5*p.absorption)),
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


def depth(source, p, x):
    lo, hi = 0.0, .02
    require(temperature(source,p,x,z=lo) >= p.liquidus-1e-8, "outside liquidus branch")
    for _ in range(65):
        mid = (lo+hi)/2
        if temperature(source,p,x,z=mid) > p.liquidus:
            lo = mid
        else:
            hi = mid
    return (lo+hi)/2


def branch_nodes(source, p, count=32):
    """A5 rear slice: open equal-x nodes, explicit chord-length cell weights."""
    rear = tail(source,p)
    lo, hi = rear, 0.0
    for _ in range(60):
        mid = (lo+hi)/2
        if gradient(p,mid,0,depth(source,p,mid))[0] > 0:
            lo = mid
        else:
            hi = mid
    bottom = (lo+hi)/2
    edges = [(bottom+(rear-bottom)*i/count,0.0,
              depth(source,p,bottom+(rear-bottom)*i/count)) for i in range(count+1)]
    points = [(bottom+(rear-bottom)*(i+.5)/count,0.0,
               depth(source,p,bottom+(rear-bottom)*(i+.5)/count)) for i in range(count)]
    weights = [math.dist(a,b) for a,b in zip(edges,edges[1:])]
    return points, weights


def weighted_median(values, weights):
    require(len(values) == len(weights) >= 3, "branch needs three samples")
    require(all(math.isfinite(w) and w > 0 for w in weights), "invalid branch weights")
    pairs = sorted(zip(values,weights))
    half = sum(weights)/2
    cumulative = 0.0
    for i,(value,weight) in enumerate(pairs):
        cumulative += weight
        if math.isclose(cumulative,half,rel_tol=1e-14):
            return (value+pairs[i+1][0])/2
        if cumulative > half:
            return value
    raise AssertionError("weighted median missing")


def aggregate(rows, weights):
    return tuple(weighted_median(column,weights) for column in zip(*rows))


def summary(source, p):
    points, weights = branch_nodes(source,p)
    require(all(abs(temperature(source,p,*point)-p.liquidus) < 1e-7 for point in points),
            "arm root residual")
    return aggregate([kinematics(gradient(p,*point),p.speed) for point in points],weights)


def independent_summary(p, count=32):
    """Independent isotherm parameterization in radius, finite-difference tuples.

    On T=TL, x(r)=log(C/(TL-T0)/sqrt(r*r+b*b))/a-r. No field root,
    gradient(), branch_nodes(), kinematics() or weighted_median() is reused.
    """
    a = p.speed*p.density*p.capacity/(2*p.conductivity)
    c = p.power*p.absorption/(2*math.pi*p.conductivity)
    def xof(r):
        return math.log(c/((p.liquidus-p.base)*math.sqrt(r*r+p.radius*p.radius)))/a-r
    def bisect(fn, lo, hi):
        flo = fn(lo)
        require(flo*fn(hi) < 0,"independent radial bracket")
        for _ in range(75):
            mid = (lo+hi)/2
            if flo*fn(mid) > 0:
                lo = mid
            else:
                hi = mid
        return (lo+hi)/2
    rear_r = math.sqrt((c/(p.liquidus-p.base))**2-p.radius**2)
    front_r = bisect(lambda r:xof(r)-r,1e-15,rear_r)
    # z'(r)=0 iff r-x dx/dr=0. This is independent of the gradient-root implementation.
    bottom_r = bisect(lambda r:r-xof(r)*(-1-r/(a*(r*r+p.radius*p.radius))),front_r,rear_r)
    bottom_x, rear_x = xof(bottom_r), -rear_r
    def point_at(f):
        x = bottom_x+(rear_x-bottom_x)*f
        if f == 0:
            r = bottom_r
        elif f == 1:
            r = rear_r
        else:
            r = bisect(lambda r:xof(r)-x,bottom_r,rear_r)
        return (x,0.0,math.sqrt(max(0,r*r-x*x)))
    edges = [point_at(i/count) for i in range(count+1)]
    weights = [math.dist(u,v) for u,v in zip(edges,edges[1:])]
    def field(point):
        r = math.sqrt(sum(q*q for q in point))
        return p.base+c/math.sqrt(r*r+p.radius*p.radius)*math.exp(-a*(r+point[0]))
    rows = []
    for i in range(count):
        point = point_at((i+.5)/count)
        h = 1e-8
        components = []
        for axis in range(3):
            vals = []
            for offset in (-2,-1,1,2):
                q = list(point)
                q[axis] += offset*h
                vals.append(field(q))
            components.append((vals[0]-8*vals[1]+8*vals[2]-vals[3])/(12*h))
        norm = math.hypot(*components)
        rate = p.speed*components[0]/norm
        rows.append((norm,rate,p.speed*components[0],norm/rate))
    # Weighted medians minimize sum w |x_i-m|. Exhaustive candidates are cheap,
    # and independent of the cumulative-weight implementation under test.
    result = []
    for column in zip(*rows):
        costs = [(sum(w*abs(v-candidate) for v,w in zip(column,weights)),candidate)
                 for candidate in column]
        best = min(cost for cost,_ in costs)
        minimizers = [v for cost,v in costs if math.isclose(cost,best,rel_tol=1e-12)]
        result.append((min(minimizers)+max(minimizers))/2)
    return tuple(result)


def tier(nominal, arms, *, route_outside=False, family_transfer=False):
    if nominal is None:
        return "no-value", None
    require(all(math.isfinite(q) and q > 0 for q in nominal), "invalid nominal")
    if route_outside or family_transfer or arms is None or len(arms) != 10 or any(arm is None for arm in arms):
        return "Physics estimate", None
    require(all(len(a) == len(nominal) and all(math.isfinite(q) and q > 0 for q in a)
                for a in arms), "bad sweep result")
    return "Estimated", tuple((min(row), max(row)) for row in zip(nominal, *arms))


def check():
    source = production_field()
    p = Inputs()
    arms = ofat(p)
    require(len(arms) == 11, "OFAT coverage")
    require(arms[7][1].absorption == .5*p.absorption and arms[8][1].absorption == 1.5*p.absorption,
            "A7 absorptivity range")
    require(ofat(replace(p,absorption=.8))[8][1].absorption == 1,"absorptivity physical cap")
    rows = [summary(source, arm) for _, arm in arms]
    references = [independent_summary(arm) for _,arm in arms]
    def assert_summaries(candidate):
        for (_,arm),reference in zip(arms,references):
            actual = candidate(source,arm)
            require(all(math.isclose(a,b,rel_tol=2e-7) for a,b in zip(actual,reference)),
                    "independent branch median oracle")
        # The physical Rosenthal branch is monotone, so its medians can select
        # the same node. Exercise the actual aggregate() with a nonmonotone
        # local-output population as well, rather than pretending it differs.
        synthetic = [(1.,101.,101.,1/101),(2.,100.,200.,.02),
                     (100.,2.,200.,50.),(101.,1.,101.,101.)]
        require(aggregate(synthetic,[1.,1.,1.,1.]) == (51.,51.,150.5,25.01),
                "local-before-aggregation oracle")
    assert_summaries(summary)
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
    # Mutate the actual summary dependency, then run the same independent oracle.
    # Residual rejection or mismatched values both kill a stale-root implementation.
    def killed(replacement_name, replacement):
        original = globals()[replacement_name]
        globals()[replacement_name] = replacement
        try:
            assert_summaries(summary)
        except AssertionError:
            return True
        finally:
            globals()[replacement_name] = original
        return False
    original_nodes = branch_nodes
    require(killed("branch_nodes",lambda field,arm:original_nodes(field,p)),"stale-root mutant survived")
    require(killed("aggregate",lambda tuples,weights:tuple(sum(c)/len(c) for c in zip(*tuples))),
            "mean-for-weighted-median mutant survived")
    def separate_medians(tuples,weights):
        g = weighted_median([row[0] for row in tuples],weights)
        r = weighted_median([row[1] for row in tuples],weights)
        return g,r,g*r,g/r
    require(killed("aggregate",separate_medians),"separate-median mutant survived")
    for name in ("capacity", "density"):
        changed = summary(source,replace(p,**{name:1.1*getattr(p,name)}))
        require(not math.isclose(changed[0],rows[0][0],rel_tol=1e-4), "diffusivity parent not exercised")
    # Celsius/Kelvin offset invariance includes the sweep, not just a gradient.
    kelvin = replace(p,base=p.base+273.15,solidus=p.solidus+273.15,liquidus=p.liquidus+273.15)
    require(all(math.isclose(a,b,rel_tol=1e-12) for a,b in zip(rows[0],summary(source,kelvin))), "temperature scale")
    require(all(math.isclose(a.liquidus+273.15,b.liquidus,abs_tol=1e-10)
                for (_,a),(_,b) in zip(arms,ofat(kelvin))), "absolute-temperature sweep mutant survived")
    # Reference extrema are independently recomputed arm medians, not the rows
    # that the interval constructor just consumed.
    expected = tuple((min(c),max(c)) for c in zip(*references))
    require(all(math.isclose(a,c,rel_tol=2e-7) and math.isclose(b,d,rel_tol=2e-7)
                for (a,b),(c,d) in zip(bands,expected)),"independent OFAT extrema")
    require(tier(rows[0],None) == ("Physics estimate",None), "missing interval discarded valid physics")
    require(tier(rows[0],[]) == ("Physics estimate",None), "empty sweep incorrectly promoted")
    require(tier(rows[0],rows[1:-1]) == ("Physics estimate",None), "incomplete sweep incorrectly promoted")
    require(tier(rows[0],[None]) == ("Physics estimate",None), "failed arm discarded nominal")
    require(tier(None,None) == ("no-value",None), "invented nominal")
    def assert_tier(fn):
        for flags in ({"route_outside":True},{"family_transfer":True}):
            require(fn(rows[0],rows[1:],**flags) == ("Physics estimate",None),
                    "transferred/outside route incorrectly promoted")
        require(fn(rows[0],rows[1:])[0] == "Estimated","in-domain tier1 lost")
    assert_tier(tier)
    # Compile an actual mutant of tier(), disabling its route caps.
    tree = ast.parse(inspect.getsource(tier))
    class RemoveCaps(ast.NodeTransformer):
        def visit_Name(self,node):
            if isinstance(node.ctx,ast.Load) and node.id in {"route_outside","family_transfer"}:
                return ast.copy_location(ast.Constant(False),node)
            return node
    mutant_scope = dict(globals())
    exec(compile(ast.fix_missing_locations(RemoveCaps().visit(tree)),"tier-cap-mutant","exec"),mutant_scope)
    try:
        assert_tier(mutant_scope["tier"])
    except AssertionError:
        pass
    else:
        raise AssertionError("disabled-tier-cap mutant survived")
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
    require(weighted_median([1,2,100,101],[1,1,1,1]) == 51,"even median midpoint")
    require(weighted_median([1,2,100,101],[1,1,10,1]) == 100,"length-weight median")
    return {"result":"PASS", "scope":"A7-research-only", "ofat_fields":len(arms),
            "samples_per_arm":32,"weighting":"liquidus-cell-chord-length",
            "quantities":4, "tiers_tested":["Estimated","Physics estimate","no-value"],
            "rejected_mutants":["stale-root","mean-for-weighted-median","separate-medians",
                                "disabled-tier-cap","absolute-Celsius-range","melting-side","invalid-parent"],
            "nominal_fixture":rows[0],"input_sensitivity_ranges":bands,
            "source_sha256":hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
            "physical_validation":False,"served_channel_installed":False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check",action="store_true",required=True)
    parser.parse_args()
    print(json.dumps(check(),sort_keys=True,allow_nan=False))
