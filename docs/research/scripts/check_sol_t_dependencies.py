#!/usr/bin/env python3
"""Independent AST/analytic-integral oracle for SOL-T reference scalar moves.

python -I docs/research/scripts/check_sol_t_dependencies.py --check
No served imports/execution, network, goldens, measured data, or file writes.
Companion source-check prerequisite: lawful local papers/ PDFs matching
papers/INDEX.md hashes; those archive bytes are not distributed by Git.
Decimal antiderivatives integrate the source ledger independently of its runtime
trapezoidal reduction. Comparison budget: 5e-15 relative + 1e-18 absolute,
solely for printed binary64 rounding, never a physical acceptance tolerance.
"""
from __future__ import annotations

import argparse
import ast
from decimal import Decimal, localcontext
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
D = lambda x: Decimal(str(x))


def literal(node):
    if isinstance(node, ast.Dict): return {literal(k): literal(v) for k, v in zip(node.keys, node.values)}
    if isinstance(node, (ast.List, ast.Tuple)): return [literal(v) for v in node.elts]
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Div, ast.Add, ast.Sub, ast.Mult)):
        a, b = literal(node.left), literal(node.right)
        if isinstance(node.op, ast.Div): return D(a) / D(b)
        if isinstance(node.op, ast.Add): return D(a) + D(b)
        if isinstance(node.op, ast.Sub): return D(a) - D(b)
        return D(a) * D(b)
    return ast.literal_eval(node)


def table(name):
    tree = ast.parse((ROOT / "python/four_alloy_materials.py").read_text(encoding="utf-8"))
    return literal(next(n.value for n in tree.body if isinstance(n, ast.Assign)
                        and any(isinstance(t, ast.Name) and t.id == name for t in n.targets)))


def mean(nodes, low, high, extrapolate=False):
    """Integrate affine segments analytically, with constant endpoint tails."""
    low, high = D(low), D(high)
    points = [(D(t), D(v)) for t, v in nodes]
    cuts = sorted({low, high, *(t for t, _ in points if low < t < high)})
    integral = D(0)
    for a, b in zip(cuts, cuts[1:]):
        midpoint = (a + b) / 2
        if midpoint < points[0][0]:
            slope, intercept = D(0), points[0][1]
        elif midpoint > points[-1][0]:
            if extrapolate:
                # P8's explicit last-100-K slope, not a new material fit.
                t1, v1 = points[-1]
                v0 = value(points, t1 - 100)
                slope = (v1 - v0) / 100
                intercept = v1 - slope * t1
            else:
                slope, intercept = D(0), points[-1][1]
        else:
            (t0, v0), (t1, v1) = next((p, q) for p, q in zip(points, points[1:]) if p[0] <= midpoint <= q[0])
            slope = (v1 - v0) / (t1 - t0)
            intercept = v0 - slope * t0
        integral += slope * (b*b - a*a) / 2 + intercept * (b-a)
    return integral / (high-low)


def value(points, temperature):
    if temperature <= points[0][0]: return points[0][1]
    if temperature >= points[-1][0]: return points[-1][1]
    (t0, v0), (t1, v1) = next((p, q) for p, q in zip(points, points[1:]) if p[0] <= temperature <= q[0])
    return v0 + (v1-v0) * (temperature-t0) / (t1-t0)


def reductions(ledger, endpoints, preheat="293.15"):
    out = {}
    t0 = D(preheat)
    for aid in ("ti6al4v", "alsi10mg"):
        num = ledger[aid]["numeric"]
        ts, tl = map(D, endpoints[aid])
        rho = D(num["kernel_density_kg_m3"])
        if aid == "ti6al4v":
            forms = [num["k_s_linear_W_mK"], num["cp_s_linear_J_kgK"]]
            # Integral of a linear form, evaluated via antiderivative.
            k, cp = [(D(f["slope"])*(tl*tl-t0*t0)/2 + D(f["intercept"])*(tl-t0))/(tl-t0) for f in forms]
            out[aid] = dict(K=k, cp=cp, rho=rho, alpha=k/(rho*cp), Tl_C=tl-D("273.15"),
                            front_K=(D(forms[0]["slope"])*ts+D(forms[0]["intercept"])+D(num["liquid"]["k_W_mK"]))/2,
                            front_cp=(D(forms[1]["slope"])*ts+D(forms[1]["intercept"])+D(num["liquid"]["cp_J_kgK"]))/2,
                            enthalpy_cp=cp+D(num["latent_heat_fusion_J_kg"])/(tl-t0))
        else:
            states = {}
            for state in ("AB", "HT", "HT_low", "AB_unrelaxed"):
                base = "HT" if state.startswith("HT") else "AB"
                kn = num["k_s_nodes_W_mK"][base]
                if state == "AB_unrelaxed": kn = kn[:2]
                k = mean(kn, t0, tl) * (D(num["HT_low_factor"]) if state == "HT_low" else 1)
                cp = mean(num["cp_s_nodes_J_kgK"][base], t0, tl)
                states[state] = dict(K=k, cp=cp, rho=rho, alpha=k/(rho*cp))
            k, cp = states["AB"]["K"], states["AB"]["cp"]
            out[aid] = dict(**states["AB"], Tl_C=tl-D("273.15"), states=states,
                            enthalpy_cp397=cp+D(397000)/(tl-t0), enthalpy_cp500=cp+D(500000)/(tl-t0),
                            front_rho_assael=(rho+D(2603)-D(".241")*tl)/2,
                            front_rho_adc12=(rho+D(2492)-D(".2652")*(tl-865))/2)
            kn, cn = num["k_s_nodes_W_mK"]["AB"], num["cp_s_nodes_J_kgK"]["AB"]
            out[aid]["linear_last_100K"] = dict(K=mean(kn,t0,tl,True),cp=mean(cn,t0,tl,True))
            out[aid]["cp_fetni_end"] = mean(cn+[[800.15,1230]],t0,tl)
    return out


def close(actual, expected, label):
    expected = D(expected)
    if abs(D(actual)-expected) > abs(expected)*D("5e-15") + D("1e-18"):
        raise ValueError(f"{label}: actual {actual} != recorded {expected}")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check",action="store_true",required=True)
    parser.parse_args()
    data=json.loads((ROOT/"docs/research/sol_t_admission_records.json").read_text(encoding="utf-8"))
    old={r["id"]:[D(v)+D("273.15") for v in r["baseline_C"]] for r in data["records"]}
    new={r["id"]:r["endpoint_K"] for r in data["records"]}
    ledger=table("PROPERTY_LEDGER")
    before,after=reductions(ledger,old),reductions(ledger,new)
    examples={
      ("before","ti6al4v"):{"K":"16.44854","cp":"645.74021","alpha":"5.749972908328388e-6","Tl_C":"1660"},
      ("after","ti6al4v"):{"K":"16.44854","cp":"645.74021","alpha":"5.749972908328388e-6","Tl_C":"1660","front_K":"28.31947","front_cp":"854.108905","enthalpy_cp":"822.5694782926829"},
      ("before","alsi10mg"):{"K":"152.52434782608697","cp":"1020.0826086956522","alpha":"5.54605210495764e-5","Tl_C":"595"},
      ("after","alsi10mg"):{"K":"152.63126079447323","cp":"1020.8488773747841","alpha":"5.545773756739041e-5","Tl_C":"599","enthalpy_cp397":"1706.513816925734","enthalpy_cp500":"1884.4067357512954","front_rho_assael":"2544.405925","front_rho_adc12":"2593.05191"}}
    checks=0
    for (when,aid),quantities in examples.items():
        for key,expected in quantities.items():
            close((before if when=="before" else after)[aid][key],expected,f"{when}/{aid}/{key}"); checks+=1
    state_pins={"HT":["198.22556131260797","1056.8229706390327","6.957248632602764e-5"],
                "HT_low":["166.8760199857965","1056.8229706390327","5.856953836692351e-5"],
                "AB_unrelaxed":["117.89170984455959","1020.8488773747841","4.283531087864317e-5"]}
    for state,pins in state_pins.items():
        for key,pin in zip(("K","cp","alpha"),pins):
            close(after["alsi10mg"]["states"][state][key],pin,f"Al/{state}/{key}"); checks+=1
    # Independently derived denominators and source unchanged properties.
    for aid,expected in {"ti6al4v":"1640","alsi10mg":"579","in718":"1316","ss316l":"1430","in625":"1330"}.items():
        close(D(new[aid][1])-D("293.15"),expected,f"{aid}/Tl-T0"); checks+=1
    thermal=table("_THERMAL")
    for aid,rho,absorptivity in (("ti6al4v",4430,".32"),("alsi10mg",2696,".3")):
        close(after[aid]["rho"],rho,aid+"/unchanged-kernel-density"); checks+=1
        close(thermal[aid]["absorptivity_IR"],absorptivity,aid+"/unchanged-field-absorptivity"); checks+=1
    for aid,pins in {"alsi10mg":["10447.368421052632","12406.25"],"ss316l":["10800","4153.846153846154"]}.items():
        latent=D(thermal[aid]["latent_heat_fusion_J_kg"])
        for ends,pin in zip((old,new),pins):
            close(latent/(D(ends[aid][1])-D(ends[aid][0])),pin,aid+"/mushy-slope"); checks+=1
    # Negative controls change the parsed physical input and threshold separately.
    for field in ("slope","intercept"):
        mutant=json.loads(json.dumps(ledger,default=float))
        mutant["ti6al4v"]["numeric"]["k_s_linear_W_mK"][field]+=1
        if reductions(mutant,new)["ti6al4v"]["K"]==after["ti6al4v"]["K"]:
            raise ValueError("Undetected AST coefficient mutation")
    mutant=dict(new,alsi10mg=[840.15,868.15])
    if reductions(ledger,mutant)["alsi10mg"]["K"]==after["alsi10mg"]["K"]:
        raise ValueError("Undetected stale-liquidus mutation")
    print(f"PASS: {checks} source-AST/Decimal reference scalar checks; 3 negative controls")
    print("Scope: prospective T0=293.15 K reductions; no installed solver/parity/bands claim")


if __name__=="__main__":
    try:
        with localcontext() as context:
            context.prec=40
            main()
    except (ValueError,KeyError,OSError,StopIteration) as exc:
        print(f"FAIL: {exc}",file=sys.stderr)
        sys.exit(1)
