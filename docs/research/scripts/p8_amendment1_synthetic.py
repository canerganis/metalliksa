"""Synthetic P8 Amendment 1 reproduction only; no runtime API or target data.

Loads only explicit immutable Python source blobs (no research runners).
Run with python -B; --check compares the committed synthetic fixture.
Astra owns the equations here; see the companion spec for their limitations.
"""
from __future__ import annotations

import argparse
import ast
import json
import math
from pathlib import Path
import subprocess
import sys
import types

from scipy.integrate import quad

BASE = "835466fa"
P3 = "c4470b017cfe533c74b23dc5712a2df720ae00c4"
REPO = Path(__file__).resolve().parents[3]
FIXTURE = Path(__file__).with_name("p8_amendment1_synthetic.json")
RG = 8.31446261815324
SB = 5.670374419e-8


def source_module(revision, path, name, functions=None):
    source = subprocess.check_output(
        ["git", "show", f"{revision}:{path}"], cwd=REPO, text=True, encoding="utf-8")
    module = types.ModuleType(name)
    sys.modules[name] = module
    if functions is not None:
        tree = ast.parse(source)
        source = ast.Module(body=[node for node in tree.body if isinstance(node, ast.FunctionDef)
                                 and node.name in functions], type_ignores=[])
        assert len(source.body) == len(functions)
        module.__dict__["math"] = math
    exec(compile(source, f"{revision}:{path}", "exec"), module.__dict__)
    return module


def mean_nodes(nodes, t0, tl, linear=False):
    def value(t):
        if linear and t > nodes[-1][0]:
            last = nodes[-1][0]
            slope = (nodes[-1][1] - value(last - 100)) / 100
            return nodes[-1][1] + slope * (t - last)
        if t <= nodes[0][0]:
            return nodes[0][1]
        for (a, fa), (b, fb) in zip(nodes, nodes[1:]):
            if t <= b:
                return fa + (fb-fa) * (t-a) / (b-a)
        return nodes[-1][1]
    knots = sorted({t0, tl, *[t for t, _ in nodes if t0 < t < tl]})
    return sum((b-a)*(value(a)+value(b))/2 for a, b in zip(knots, knots[1:]))/(tl-t0)


def gaussian_gain(v, d, k, alpha, x=0):
    """K/W; P6 Eq2, tan substitution, Gaussian radius d/2."""
    r = d/2
    def kernel(theta):
        u2 = math.tan(theta)**2
        return math.exp(-2*(x/r + v*r/(8*alpha)*u2)**2/(1+u2))
    return math.sqrt(2)/(math.pi**1.5*k*r)*quad(
        kernel, 0, math.pi/2, epsabs=1e-12, epsrel=2e-10, limit=240)[0]


def surface(s):
    """P6 beam-centre flat balance; this is a peak proxy, not spatial peak."""
    q = 2*s["A"]*s["P"]/(math.pi*(s["d"]/2)**2)
    tg = s["T0"] + s["A"]*s["P"]*gaussian_gain(s["v"], s["d"], s["K"], s["alpha"])
    h = q/(tg-s["T0"])
    b = s["Lv"]*s["M"]/RG
    def terms(t):
        ps = 101325*math.exp(b*(1/s["Tv"]-1/t))
        j = s["accommodation"]*.8*ps*math.sqrt(s["M"]/(2*math.pi*RG*t))
        return h*(t-s["T0"]), s["Lv"]*j, s["emissivity"]*SB*(t**4-s["T0"]**4), j, s["recoil"]*ps
    lo, hi = s["T0"], min(tg, .999*2*b)
    residual = lambda t: sum(terms(t)[:3])-q
    if residual(lo)>0 or residual(hi)<0:
        raise ValueError("SURFACE_BALANCE_NO_BRACKET")
    for _ in range(100):
        t = (lo+hi)/2
        f = residual(t)
        if abs(f) <= q*1e-10:
            break
        if f>0:
            hi=t
        else:
            lo=t
    else:
        raise ValueError("SURFACE_BALANCE_CONVERGENCE_FAILED")
    c, e, radiation, j, recoil = terms(t)
    return {"peakTemperatureProxy_K": t, "evaporationMassFlux_kg_m2_s": j,
            "recoilPressure_Pa": recoil, "lossFreeCenterTemperature_K": tg,
            "energyResidualRelative": (c+e+radiation-q)/q}


def marangoni(s):
    alpha = s["kl"]/(s["rhol"]*s["cpl"])
    ma = -s["slope"]*s["d"]*s["deltaT"]/(s["mu"]*alpha)
    u = (abs(s["slope"])*s["deltaT"]/math.sqrt(s["rhol"]*s["mu"]*s["d"]))**(2/3)
    return {"marangoniNumber": ma, "surfaceVelocityScale_m_s": u,
            "liquidPecletScale": u*s["d"]/alpha}


def nominal(registry, alloy, power):
    p = registry.thermal_props(alloy)
    kp = registry.kernel_properties(alloy, 293.15)
    ti = alloy == "ti6al4v"
    return dict(P=power, v=.8, d=80e-6, T0=293.15, Tl=kp["T_liq_K"],
                K=kp["kernel_conductivity_W_mK"], cp=kp["kernel_specific_heat_J_kgK"],
                rho=kp["kernel_density_kg_m3"], alpha=kp["alpha_m2_s"], A=p["absorptivity_IR"],
                Tv=3560. if ti else 2743., Lv=9.255e6 if ti else 284000/.0269815384,
                M=.048 if ti else .0269815384, kl=p["thermal_conductivity_liquid_W_mK"],
                cpl=p["specific_heat_liquid_J_kgK"], rhol=p["density_liquid_kg_m3"],
                slope=-.00019 if ti else p["d_gamma_dT_N_mK"],
                mu=.005 if ti else 10**(-.8022+658.34/(kp["T_liq_K"]+250))*1e-3,
                deltaT=500., accommodation=1., recoil=.6, emissivity=.3 if ti else .35)


def arms(registry, alloy, s):
    result = [("nominal", s)]
    def add(name, **patch):
        arm = {**s, **patch}
        arm["alpha"] = arm["K"]/(arm["rho"]*arm["cp"])
        if not ti:
            arm["mu"] = 10**(-.8022+658.34/(arm["Tl"]+250))*1e-3
        result.append((name, arm))
    ti = alloy == "ti6al4v"
    for a in ([.26, .33] if ti else [.28, .4, .14, .18]):
        add(f"absorptance_{a:g}", A=a)
    num = registry.PROPERTY_LEDGER[alloy]["numeric"]
    if ti:
        def front(name, **liquid):
            kl=liquid.get("kl",s["kl"]); cp=liquid.get("cpl",s["cpl"]); rho=liquid.get("rhol",s["rhol"])
            ts=num["T_sol_K"]
            add(name, K=(.0136*ts+1.3097+kl)/2, cp=(.1734*ts+452.72+cp)/2,
                rho=(s["rho"]+rho)/2, **liquid)
        front("melt_front_means")
        for field, values in (("kl",[28.7,33.4]),("cpl",[831.,1126.]),("rhol",[3920.,4123.])):
            for value in values:
                front(f"melt_front_{field}_{value:g}", **{field:value})
        add("enthalpy_cp", cp=s["cp"]+290000/(s["Tl"]-s["T0"]))
        add("srv", K=18.25, cp=728., rho=4430.)
        for tv in [3360.,3760.]:
            add(f"vapour_{tv:g}", Tv=tv)
    else:
        for state in ["HT_low","HT","AB_unrelaxed"]:
            kp=registry.kernel_properties(alloy,s["T0"],state=state)
            add(f"state_{state}", K=kp["kernel_conductivity_W_mK"],cp=kp["kernel_specific_heat_J_kgK"])
        kn=num["k_s_nodes_W_mK"]["AB"]; cn=num["cp_s_nodes_J_kgK"]["AB"]
        add("linear_last_100K",K=mean_nodes(kn,s["T0"],s["Tl"],True),cp=mean_nodes(cn,s["T0"],s["Tl"],True))
        add("cp_fetni_end",cp=mean_nodes(cn+[[800.15,1230.]],s["T0"],s["Tl"]))
        for tl in [863.15,872.15]:
            kp=registry.kernel_properties(alloy,s["T0"],T_liq_K=tl)
            add(f"liquidus_{tl:g}",Tl=tl,K=kp["kernel_conductivity_W_mK"],cp=kp["kernel_specific_heat_J_kgK"])
        for rho in [2620.,2715.]:
            add(f"rho_s_{rho:g}",rho=rho)
        for tag,rhol in [("assael",2603-.241*s["Tl"]),("adc12",2492-.2652*(s["Tl"]-865))]:
            add(f"melt_front_{tag}",K=(kn[-1][1]+64)/2,cp=(cn[-1][1]+1170)/2,rho=(2696+rhol)/2,rhol=rhol,cpl=1170.)
        for lf in [397000.,500000.]:
            add(f"enthalpy_cp_{lf:g}",cp=s["cp"]+lf/(s["Tl"]-s["T0"]))
        add("srv",K=107.5,cp=1045.,rho=2680.)
        add("vapour_o8",Tv=2477.605213217703,Lv=6823019.62479557,M=.024889589126757754)
    for factor in [.95,1.05]:
        add(f"power_{factor:g}",P=s["P"]*factor)
        add(f"beam_{factor:g}",d=s["d"]*factor)
    return result


def evaluate(p3, et, extent, s):
    mat=p3.Material("synthetic",s["K"],s["rho"],s["cp"],s["Tl"],s["Tv"],s["A"],s["Lv"],s["M"],0.,s["cpl"],s["T0"])
    onset=p3.onset_power(mat,s["v"],s["d"])
    solution=p3.solve_e(s["P"],s["v"],s["d"],s["K"],s["Tv"]-s["T0"],s["alpha"],s["A"],closure="cylinder_exact",P_star=onset)
    e=solution.selected_e_m
    ac=p3.specular_cone(e/s["d"],s["A"])
    w=1-math.exp(-2); p=1-w
    if s["P"]<=onset:
        qs=s["A"]*s["P"]; qc=0.
    else:
        qs=s["A"]*(p*s["P"]+w*onset)
        qc=w*(ac*s["P"]-s["A"]*onset)
    depths=[]
    for order,samples in [(32,65),(64,129)]:
        depths.append(p3.melt_depth_from_e(e,qs+qc,s["v"],s["K"],s["Tl"]-s["T0"],s["alpha"],chi=qc/(qs+qc),observable="envelope",order=order,x_samples=samples))
    assert abs(depths[1]-depths[0])/max(depths[1],1e-12)<=.01
    # Reuse only the immutable ET field and three pure extent helpers; never
    # import the full thermal solver, its catalogs, target runners or served leg.
    field=et.EagarTsaiField(s["T0"]-273.15,s["A"]*s["P"],s["K"],s["alpha"],s["d"]/2).bind_speed(s["v"])
    width=math.sqrt(8/(math.pi*math.e)*s["A"]*s["P"]/(s["rho"]*s["cp"]*(s["Tl"]-s["T0"])*s["v"]))
    length=max(s["d"]*3,width*4.5,80e-6)
    peak=extent._axial_peak_x(field.temperature_C,-length*1.4*8,length)
    floor=extent._liquidus_extent(field.temperature_C,s["Tl"]-273.15,peak,length,
                                 max(s["d"]*1.8,width*1.8,50e-6),
                                 max(s["d"]*2.2,width*2,40e-6),s["d"],s["d"]/2,width,0.)
    assert floor["extent_status"]=="computed",floor["extent_status"]
    return dict(peclet=solution.Pe,powerOverOnset=s["P"]/onset,onsetPower_W=onset,
                cavityDepth_um=e*1e6,conditionalMeltDepth_um=depths[1]*1e6,
                conductionDepth_um=floor["d_iso"]*1e6,
                linkedMeltDepth_um=max(depths[1],floor["d_iso"])*1e6,
                **marangoni(s),**surface(s))


def run():
    registry=source_module(BASE,"python/four_alloy_materials.py","p8_registry_fixture")
    p3=source_module(P3,"python/tools/p3_cavity_model_sketch.py","p8_cavity_fixture")
    et=source_module(BASE,"python/eagar_tsai_solver.py","p8_et_fixture")
    extent=source_module(BASE,"python/lpbf_thermal_solver.py","p8_extent_fixture",
                         {"_binary_extent","_axial_peak_x","_liquidus_extent"})
    points=[]; bands=[]
    for alloy in ["ti6al4v","alsi10mg"]:
        for power in [100.,200.,400.]:
            s=nominal(registry,alloy,power)
            values=evaluate(p3,et,extent,s)
            points.append(dict(alloy=alloy,power_W=power,values=values))
            if power==200:
                manifest=arms(registry,alloy,s)
                outputs=[evaluate(p3,et,extent,arm) for _,arm in manifest]
                bands.append(dict(alloy=alloy,power_W=power,armIds=[name for name,_ in manifest],
                                  successfulArms=len(outputs),failedArms=[],
                                  cavityExistsArms=sum(o["powerOverOnset"]>1 for o in outputs),
                                  fields={key:dict(min=min(o[key] for o in outputs),nominal=values[key],max=max(o[key] for o in outputs),
                                                   minArmId=manifest[min(range(len(outputs)),key=lambda i:outputs[i][key])][0],
                                                   maxArmId=manifest[max(range(len(outputs)),key=lambda i:outputs[i][key])][0])
                                          for key in values if key!="energyResidualRelative"}))
    # Independent limiting/identity checks; no measurement or fitted tolerance.
    gain=gaussian_gain(0,80e-6,20,1e-5)
    assert math.isclose(gain,1/(math.sqrt(2*math.pi)*20*40e-6),rel_tol=1e-10)
    for point in points:
        assert abs(point["values"]["energyResidualRelative"])<=1e-10
    s=nominal(registry,"ti6al4v",200.)
    zero=marangoni({**s,"slope":0.})
    assert all(v==0 for v in zero.values())
    disabled=surface({**s,"accommodation":0.,"emissivity":0.})
    assert math.isclose(disabled["peakTemperatureProxy_K"],disabled["lossFreeCenterTemperature_K"],rel_tol=1e-9)
    # Independently differentiate the sourced Belton temperature relation.
    t=1823.; gamma=1.30e-5; dh=-166200.; activity=.001
    def sigma(temp):
        return -4.3e-4*temp-RG*temp*gamma*math.log1p(.00318*activity*math.exp(-dh/(RG*temp)))
    b=.00318*activity*math.exp(-dh/(RG*t))
    derivative=-4.3e-4-RG*gamma*math.log1p(b)-gamma*dh/t*b/(1+b)
    independent=(sigma(t+.01)-sigma(t-.01))/.02
    assert math.isclose(derivative,independent,rel_tol=1e-8)
    return dict(evidence="synthetic software reproduction; not experimental validation",sourceBase=BASE,sourceP3=P3,
                bandMethod="one-at-a-time union; no interactions or statistical coverage",points=points,bands=bands)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--check",action="store_true")
    args=parser.parse_args(); result=run()
    if args.check:
        pinned=json.loads(FIXTURE.read_text(encoding="utf-8"))
        def compare(a,b):
            if isinstance(a,float):
                assert math.isclose(a,b,rel_tol=2e-8,abs_tol=1e-7),(a,b)
            elif isinstance(a,dict):
                assert a.keys()==b.keys()
                for k in a: compare(a[k],b[k])
            elif isinstance(a,list):
                assert len(a)==len(b)
                for x,y in zip(a,b): compare(x,y)
            else: assert a==b,(a,b)
        compare(result,pinned)
        print("PASS: six synthetic points, two full declared arm envelopes and analytic/energy limits")
    else:
        FIXTURE.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf-8")
        print(f"Wrote synthetic fixture: {len(result['points'])} points; bands {[len(b['armIds']) for b in result['bands']]}")
