"""Synthetic P8 Amendment 4 reproduction; historical filename, no target data.

Loads only explicit immutable Python source blobs (no research runners).
Run with python -I; --check compares the committed synthetic fixture.
Astra owns the equations here; see the companion spec for their limitations.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import types

from scipy.integrate import quad
from scipy.optimize import brentq, minimize_scalar
from scipy.special import i0e, iv, kv, kvp
import numpy as np
import importlib.util


def sibling_module(name):
    """Load only a named adjacent source file, also under isolated Python."""
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


kernel = sibling_module("p8_cavity_kernel")
provenance_data = sibling_module("p8_input_provenance")

BASE = "835466fa"
P3 = "c4470b017cfe533c74b23dc5712a2df720ae00c4"
REPO = Path(__file__).resolve().parents[3]
FIXTURE = Path(__file__).with_name("p8_amendment1_synthetic.json")
RG = 8.31446261815324
SB = 5.670374419e-8
SOURCE_HASHES={}


def source_module(revision, path, name):
    source = subprocess.check_output(
        ["git", "show", f"{revision}:{path}"], cwd=REPO, text=True, encoding="utf-8")
    SOURCE_HASHES[f"{revision}:{path}"]=hashlib.sha256(source.replace("\r\n","\n").encode("utf-8")).hexdigest()
    module = types.ModuleType(name)
    sys.modules[name] = module
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


def gaussian_gain(v, d, k, alpha, x=0, tolerance=2e-10, z=0):
    """K/W; P6 Eq2, tan substitution, Gaussian radius d/2."""
    r = d/2
    def kernel(theta):
        u2 = math.tan(theta)**2
        return math.exp(-2*(x/r + v*r/(8*alpha)*u2)**2/(1+u2)-2*(z/r)**2/u2)
    return math.sqrt(2)/(math.pi**1.5*k*r)*quad(
        kernel, 0, math.pi/2, epsabs=1e-12, epsrel=tolerance, limit=240)[0]


def surface(s):
    """P6 beam-centre flat balance; this is a peak proxy, not spatial peak."""
    q = 2*s["A"]*s["P"]/(math.pi*(s["d"]/2)**2)
    tg = s["T0"] + s["A"]*s["P"]*gaussian_gain(s["v"], s["d"], s["K"], s["alpha"])
    h = q/(tg-s["T0"])
    b = s["Lv"]*s["M"]/RG
    def terms(t):
        ps = 101325*math.exp(b*(1/s["Tv"]-1/t))
        j = s["accommodation"]*s["effectiveNetFactor"]*ps*math.sqrt(s["M"]/(2*math.pi*RG*t))
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
    derivative=h+e*(b/t**2-1/(2*t))+4*s["emissivity"]*SB*t**3
    assert h>0 and derivative>0
    refined=gaussian_gain(s["v"],s["d"],s["K"],s["alpha"],tolerance=1e-12)
    gain=gaussian_gain(s["v"],s["d"],s["K"],s["alpha"])
    difference=abs(refined-gain)/refined
    assert difference<=1e-8
    return {"peakTemperatureProxy_K": t, "evaporationMassFlux_kg_m2_s": j,
            "recoilPressure_Pa": recoil, "lossFreeCenterTemperature_K": tg,
            "absorbedCenterFlux_W_m2":q,"conductiveAdmittance_W_m2K":h,
            "monotonicDerivative_W_m2K":derivative,"surfaceGainRefinementRelative":difference,
            "evaporationEnergyFlux_W_m2":e,"conductionFlux_W_m2":c,"radiationFlux_W_m2":radiation,
            "effectiveAccommodation":s["accommodation"]*s["effectiveNetFactor"],
            "effectiveNetFactor":s["effectiveNetFactor"],"evaporationAccommodation":s["accommodation"],
            "energyResidualRelative": (c+e+radiation-q)/q}


def marangoni(s):
    alpha = s["kl"]/(s["rhol"]*s["cpl"])
    ma = -s["slope"]*s["L"]*s["deltaT"]/(s["mu"]*alpha)
    u = (abs(s["slope"])*s["deltaT"]/math.sqrt(s["rhol"]*s["mu"]*s["L"]))**(2/3)
    return {"marangoniNumber": ma, "surfaceVelocityScale_m_s": u,
            "liquidPecletScale": u*s["L"]/alpha,
            "surfaceTensionSlope_N_mK":s["slope"],"viscosity_Pa_s":s["mu"],
            "deltaTemperature_K":s["deltaT"],"length_m":s["L"],
            "flowDirection":("outward" if s["slope"]<0 else "inward")
                if s["slope"]!=0 and s["deltaT"]>0 else "none"}


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
                deltaT=500., L=80e-6, Lm=p["latent_heat_fusion_J_kg"],onsetMethod="dwell",
                accommodation=1.,effectiveNetFactor=.8, recoil=.6, emissivity=.3 if ti else .35)


def arms(registry, alloy, s):
    result = [("nominal", s)]
    def add(name, **patch):
        arm = {**s, **patch}
        arm["alpha"] = arm["K"]/(arm["rho"]*arm["cp"])
        if "d" in patch and "L" not in patch:
            arm["L"]=arm["d"]
        if not ti and "mu" not in patch:
            arm["mu"] = 10**(-.8022+658.34/(arm["Tl"]+arm["deltaT"]/2))*1e-3
        result.append((name, arm))
    ti = alloy == "ti6al4v"
    for a in ([.26, .33] if ti else [.28, .4, .14]):
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
            add(f"melt_front_{tag}",K=(kn[-1][1]+64)/2,cp=(cn[-1][1]+1180)/2,rho=(2696+rhol)/2,rhol=rhol,cpl=1180.)
        for lf in [397000.,500000.]:
            add(f"enthalpy_cp_{lf:g}",cp=s["cp"]+lf/(s["Tl"]-s["T0"]))
        add("srv",K=107.5,cp=1045.,rho=2680.)
        add("vapour_o8",Tv=2477.605213217703,Lv=6823019.62479557,M=.024889589126757754)
    for factor in [.95,1.05]:
        add(f"power_{factor:g}",P=s["P"]*factor)
        add(f"beam_{factor:g}",d=s["d"]*factor)
    for method in ["O1","O3"]:
        add(f"onset_{method}",onsetMethod=method)
    for slope in ([-.00014,-.00024] if ti else [-.0786e-3,-.244e-3]):
        add(f"slope_{slope:g}",slope=slope)
    if ti:
        add("viscosity_mohr",mu=.004)
        add("slope_viscosity_gan",slope=-2.6e-4,mu=.00266)
    for delta in [250.,1000.]:
        add(f"deltaT_{delta:g}",deltaT=delta)
    for factor in [.5,2.]:
        add(f"length_{factor:g}",L=s["d"]*factor)
    add("accommodation_effective_0.82",effectiveNetFactor=.82)
    return result


def gaussian_floor(s, order=512, samples=65):
    """Independent finite-Gaussian liquidus envelope, no served extent helpers.

    y=0 maximizes every positive time-kernel term; x>0 decreases every term.
    A stationary Gaussian surface profile bounds the moving field at every x,
    hence its i0e tail provides a deterministic rear exclusion boundary. The
    stationary point-power bound Q/(2*pi*K*z) gives a deterministic depth cap.
    Refine every local x maximum continuously, then bisect its depth crossing.
    Grid/quadrature doubling checks numerical completeness, not experimental
    validity or a proof that a grid contains every extremum.
    """
    q=s["A"]*s["P"];a=s["d"]/2;dt=s["Tl"]-s["T0"]
    if q==0:
        return dict(depth_m=0.,peakX_m=0.,status="no-melting",rearBound_m=0.)
    stationary=q/(math.sqrt(2*math.pi)*s["K"]*a)
    if stationary<=dt:
        return dict(depth_m=0.,peakX_m=0.,status="no-melting",rearBound_m=0.)
    left=-2*a
    while stationary*float(i0e((left/a)**2))>=dt:
        left*=2
    nodes,weights=np.polynomial.legendre.leggauss(order)
    theta=(nodes+1)*math.pi/4;weights=weights*math.pi/4
    u2=np.tan(theta)**2;speed=s["v"]*a/(8*s["alpha"])
    pref=q*math.sqrt(2)/(math.pi**1.5*s["K"]*a)
    def peak(z):
        def field(xs):
            xs=np.asarray(xs)
            exponent=-2*(xs[...,None]/a+speed*u2)**2/(1+u2)-2*(z/a)**2/u2
            return pref*(np.exp(exponent)@weights)
        xs=np.linspace(left,0,samples);ys=field(xs)
        candidates=[(float(ys[0]),left),(float(ys[-1]),0.)]
        for i in range(1,samples-1):
            if ys[i]>=ys[i-1] and ys[i]>=ys[i+1]:
                opt=minimize_scalar(lambda x:-float(field(x)),bounds=(xs[i-1],xs[i+1]),
                    method="bounded",options={"xatol":1e-13,"maxiter":100})
                assert opt.success
                candidates.append((-float(opt.fun),float(opt.x)))
        return max(candidates)
    surface_peak=peak(0)
    if surface_peak[0]<=dt:
        return dict(depth_m=0.,peakX_m=surface_peak[1],status="no-melting",rearBound_m=left)
    lo=0.;hi=q/(2*math.pi*s["K"]*dt)
    assert peak(hi)[0]<dt
    for _ in range(80):
        mid=(lo+hi)/2
        if peak(mid)[0]>=dt:lo=mid
        else:hi=mid
        if hi-lo<=1e-13:break
    else:raise RuntimeError("Gaussian envelope depth bisection failed")
    depth=(lo+hi)/2
    return dict(depth_m=depth,peakX_m=peak(depth)[1],status="computed",rearBound_m=left)


def material(s):
    return kernel.Material("synthetic",s["K"],s["rho"],s["cp"],s["Tl"],s["Tv"],s["A"],
                           s["Lv"],s["M"],s["Lm"],s["cpl"],s["T0"])


def onset_power(s):
    mat=material(s);method=s["onsetMethod"]
    if method=="O2":
        raise ValueError("GEOMETRIC_THRESHOLD_NOT_INCEPTION")
    if method=="O3":return kernel.onset_power(mat,s["v"],s["d"],method="gaussian_peak")
    onset=kernel.onset_power(mat,s["v"],s["d"])
    if method=="O1":onset*=2*(s["Tv"]-s["T0"])/(kernel.threshold_temperature(mat)-s["T0"])
    return onset


def evaluate(s):
    onset=onset_power(s)
    solution=kernel.solve_e(s["P"],s["v"],s["d"],s["K"],s["Tv"]-s["T0"],s["alpha"],s["A"],
                           closure="cylinder_exact",P_star=onset)
    e=solution.selected_e_m;ac=kernel.specular_cone(e/s["d"],s["A"])
    w=1-math.exp(-2);p=1-w
    if s["P"]<=onset:qs=s["A"]*s["P"];qc=0.
    else:
        qs=s["A"]*(p*s["P"]+w*onset)
        qc=w*(ac*s["P"]-s["A"]*onset)
    qabs=qs+qc;chi=qc/qabs if qabs else 0.
    photons=qabs-kernel.total_absorptance(e/s["d"],s["A"])*s["P"]
    assert abs(photons)<=1e-10*max(1.,qabs)
    floor0=gaussian_floor(s);floor=gaussian_floor(s,1024,129)
    floor_difference=abs(floor["depth_m"]-floor0["depth_m"])
    assert floor_difference<=max(2e-11,1e-6*floor["depth_m"])
    if s["P"]<=onset:
        depths=[floor0["depth_m"],floor["depth_m"]];dispatch="gaussian-below-onset"
    else:
        depths=[kernel.melt_depth_from_e(e,qabs,s["v"],s["K"],s["Tl"]-s["T0"],s["alpha"],
                  chi=chi,observable="envelope",order=n,x_samples=m) for n,m in [(32,65),(64,129)]]
        dispatch="conditional-line-above-onset"
    depth_difference=abs(depths[1]-depths[0])/max(depths[1],1e-12)
    assert depth_difference<=.01
    g24=kernel.thermal_g(solution.Pe,"cylinder_exact");lam=solution.Pe/2
    g32=-2*math.pi*lam*math.fsum([float(iv(0,lam)**2*kvp(0,lam)/kv(0,lam))]+
             [2*(-1)**n*float(iv(n,lam)**2*kvp(n,lam)/kv(n,lam)) for n in range(1,33)])
    gdiff=abs(g32-g24)/abs(g32);assert gdiff<=1e-8
    roots=[]
    for root in solution.roots if s["P"]>onset else []:
        residual=kernel.energy_balance_residual(root.e_m,s["P"],s["v"],s["d"],s["K"],
                       s["Tv"]-s["T0"],s["alpha"],s["A"],closure="cylinder_exact",P_star=onset)
        assert abs(residual)<=max(1e-6,1e-8*max(1.,qabs))
        roots.append(dict(R=root.R,depth_um=root.e_m*1e6,scalarRelaxation=root.stability,
                          cavityEnergyResidual_W=residual,selected=bool(root.e_m==e)))
    stable=[r for r in solution.roots if r.stability=="stable"]
    assert stable and e==min(r.e_m for r in stable)
    wall=s["K"]*(s["Tv"]-s["T0"])*g24*e
    return dict(peclet=solution.Pe,powerOverOnset=s["P"]/onset,onsetPower_W=onset,
                cavityDepth_um=e*1e6,conditionalMeltDepth_um=depths[1]*1e6,
                conductionDepth_um=floor["depth_m"]*1e6,linkedMeltDepth_um=max(depths[1],floor["depth_m"])*1e6,
                surfacePower_W=qs,cavityPower_W=qc,absorbedPower_W=qabs,lineFraction=chi,
                cavityLedgerRatio=qc/wall if wall>0 else None,
                photonResidual_W=photons,cylinderHarmonicDifference=gdiff,
                meltDepthRefinementRelative=depth_difference,meltDepthCoarse_m=depths[0],meltDepthRefined_m=depths[1],
                conductionRefinement_m=floor_difference,
                conductionPeakX_m=floor["peakX_m"],conductionRearBound_m=floor["rearBound_m"],
                conductionStatus=floor["status"],linkDispatch=dispatch,
                controllingLeg="conduction" if s["P"]<=onset else
                    ("equal" if depths[1]==floor["depth_m"] else
                     "conditional-link" if depths[1]>floor["depth_m"] else "conduction"),
                rootCount=len(roots),roots=roots,rootTopologyStatus="computed" if s["P"]>onset else "NOT_APPLICABLE",
                selectedBranch="lowest-strictly-stable" if s["P"]>onset else None,
                modeledAboveOnset=s["P"]>onset,**marangoni(s),**surface(s))

CAVITY_FIELDS={"peclet","powerOverOnset","onsetPower_W","cavityDepth_um","rootCount","roots",
 "selectedBranch","rootTopologyStatus","modeledAboveOnset","cylinderHarmonicDifference"}
LINK_FIELDS={"conditionalMeltDepth_um","conductionDepth_um","linkedMeltDepth_um","surfacePower_W",
 "cavityPower_W","absorbedPower_W","lineFraction","cavityLedgerRatio","photonResidual_W",
 "meltDepthRefinementRelative","meltDepthCoarse_m","meltDepthRefined_m","conductionRefinement_m","conductionPeakX_m","conductionRearBound_m",
 "conductionStatus","linkDispatch","controllingLeg"}
MARANGONI_FIELDS=set(marangoni(dict(kl=1.,rhol=1.,cpl=1.,slope=-1.,L=1.,deltaT=1.,mu=1.)))
MODULE_FIELDS={"cavity":CAVITY_FIELDS,"meltDepthLink":LINK_FIELDS,"marangoni":MARANGONI_FIELDS}


NON_SURFACE_VALIDATION = "Not experimentally validated; research diagnostic/model only."
SURFACE_VALIDATION = ("Falsified flat non-receding HKL closure against an open IN625 mass-loss test; "
                      "numeric closure artefacts only, no physical prediction or blind-validation pass.")


def consistency_status(module, *, above_onset=True, peclet=3., aspect=1.,
                       source_transfer=False, hard_failure=False):
    """Availability is independent; inRange never implies experimental validity."""
    if hard_failure or module == "surfaceBalance":
        return "outOfRange"
    if source_transfer or (module in {"cavity","meltDepthLink"} and
                           (peclet < 2 or (above_onset and aspect < .5))):
        return "extrapolated"
    return "inRange"


def input_scope_reasons(module, provenance):
    """Classify actual coefficient/source scopes without borrowing another arm."""
    reasons=[]
    for key in provenance_data.PHYSICAL_INPUTS[module]:
        record=provenance[key]
        if record["sourceEvidenceKind"]=="Unresolved":reasons.append(key+": physical scope not established")
        scope=record["scope"].lower()
        if record["kind"]=="alloyTransfer" or "transferred" in scope or "molten-wall" in scope:
            reasons.append(key+": source/material-state transfer")
        temperature=record["referenceTemperature_K"];limits=record["sourceRange_K"]
        if temperature is not None and limits is not None and not limits[0]<=temperature<=limits[1]:
            reasons.append(key+": reference temperature outside source range")
    return reasons


def field_shape_policy(ratio, floor, excess, shape):
    """Declared disclosure convention; no experimental threshold inference."""
    resolution = max(2e-5, 1e-6 * abs(floor))  # um; Gaussian refinement bound
    share = shape / excess if ratio > 1 and excess > resolution else None
    below_near = .999 <= ratio <= 1.
    dominant = share is not None and shape > resolution and share >= .5
    return dict(nearOnset=bool(below_near or dominant), fieldShapeShare=share,
                excessResolution_um=resolution,
                nearOnsetTrigger="below-or-at-onset-0.1-percent" if below_near else
                    "field-shape-share-at-least-half" if dominant else None)


def field_shape_diagnostic(s, output):
    """Same-absorbed-power point counterfactual; not an alternate prediction."""
    if not output["modeledAboveOnset"]:
        return dict(applicable=False, reason="Gaussian dispatch at or below inception",
                    **field_shape_policy(output["powerOverOnset"], output["conductionDepth_um"], 0., 0.))
    point = kernel.melt_depth_from_e(0.,output["absorbedPower_W"],s["v"],s["K"],
        s["Tl"]-s["T0"],s["alpha"],chi=0.,observable="envelope",order=64,x_samples=129)*1e6
    excess = output["conditionalMeltDepth_um"]-output["conductionDepth_um"]
    shape = point-output["conductionDepth_um"]
    return dict(applicable=True,samePowerPointDepth_um=point,fieldShapeExcess_um=shape,
        conditionalExcessOverGaussian_um=excess,
        **field_shape_policy(output["powerOverOnset"], output["conductionDepth_um"], excess, shape),
        caveat="Counterfactual decomposition at the same absorbed power; no physical validation.")


def independent_point_depth(s, power):
    """Stationary-x condition of Q exp[-beta(x+r)]/(2 pi K r).

    Set u=-x/r, r=u/(beta(1-u)), then solve beta L(1-u) exp(-u)/u=1.
    This uses neither the conditional-field optimizer nor its depth bisection.
    """
    beta=s["v"]/(2*s["alpha"])
    length=s["A"]*power/(2*math.pi*s["K"]*(s["Tl"]-s["T0"]))
    u=brentq(lambda value:beta*length*(1-value)*math.exp(-value)-value,
             0.,1.,xtol=1e-14)
    radius=u/(beta*(1-u))
    return radius*math.sqrt(1-u*u)*1e6


def value_provenance(module, values, inputs):
    """Determine support from actual physical dependencies, separately from validity."""
    echoes={"surfaceTensionSlope_N_mK":"slope","viscosity_Pa_s":"mu",
            "deltaTemperature_K":"deltaT","length_m":"L",
            "effectiveNetFactor":"effectiveNetFactor","evaporationAccommodation":"accommodation"}
    conventions={"selectedBranch","rootTopologyStatus","modeledAboveOnset","flowDirection",
                 "conductionStatus","linkDispatch","controllingLeg","roots"}
    thermal=("K","cp","rho")
    inception=thermal+("A","Tv","Lv","M")
    floor=thermal+("A","Tl")
    records={}
    for key in values:
        dependencies=provenance_data.PHYSICAL_INPUTS[module]
        if key in echoes:dependencies=(echoes[key],)
        elif key=="peclet":dependencies=thermal
        elif module=="cavity":dependencies=inception
        elif module=="meltDepthLink":
            dependencies=(floor if key.startswith("conduction") else inception if key in {
                "surfacePower_W","cavityPower_W","absorbedPower_W","lineFraction",
                "cavityLedgerRatio","photonResidual_W"} else inception+("Tl",))
        elif module=="marangoni" and key=="surfaceVelocityScale_m_s":
            dependencies=("slope","deltaT","rhol","mu","L")
        elif module=="surfaceBalance":
            dependencies=tuple(k for k in dependencies if k!="recoil")
            if key=="recoilPressure_Pa":dependencies=dependencies+("recoil",)
            if key=="effectiveAccommodation":dependencies=("accommodation","effectiveNetFactor")
            if key=="absorbedCenterFlux_W_m2":dependencies=("A",)
            if key in {"conductiveAdmittance_W_m2K","surfaceGainRefinementRelative"}:dependencies=thermal
            if key=="lossFreeCenterTemperature_K":dependencies=thermal+("A",)
        if key in conventions:
            records[key]=dict(sourceEvidenceKind=None,dependsOn=[],weakestInputs=[])
        else:
            evidence,weak=provenance_data.evidence_kind(inputs,dependencies)
            records[key]=dict(sourceEvidenceKind=evidence,dependsOn=list(dependencies),weakestInputs=weak)
    return records


def band(values,nominal):
    fields={}
    for key,value in nominal.items():
        if isinstance(value,(int,float)) and not isinstance(value,bool) and value is not None:
            successful=[(name,o[key]) for name,o in values if isinstance(o.get(key),(int,float)) and not isinstance(o[key],bool)]
            if not successful:continue
            low=min(successful,key=lambda pair:pair[1]);high=max(successful,key=lambda pair:pair[1])
            fields[key]=dict(min=low[1],nominal=value,max=high[1],minArmId=low[0],maxArmId=high[0],successfulArms=len(successful))
    categories={}
    for key in ["rootCount","modeledAboveOnset","flowDirection","controllingLeg","conductionStatus","linkDispatch","selectedBranch"]:
        if key in nominal:
            counts={}
            for _,o in values:
                label=str(o[key]);counts[label]=counts.get(label,0)+1
            categories[key]=counts
    return dict(fields=fields,categoricalSupport=categories)


def render_fixture(value, level=0):
    """Keep repeated metadata records compact; preserve the full parsed fixture."""
    if isinstance(value,dict):
        if not value:return "{}"
        if ("sourceId" in value and "kind" in value) or ("sourceEvidenceKind" in value and "dependsOn" in value):
            return json.dumps(value,allow_nan=False,separators=(",",":"))
        entries=["  "*(level+1)+json.dumps(key)+": "+render_fixture(item,level+1) for key,item in value.items()]
        return "{\n"+",\n".join(entries)+"\n"+"  "*level+"}"
    if isinstance(value,list):
        if not value:return "[]"
        return "[\n"+",\n".join("  "*(level+1)+render_fixture(item,level+1) for item in value)+"\n"+"  "*level+"]"
    return json.dumps(value,allow_nan=False)


def run():
    registry=source_module(BASE,"python/four_alloy_materials.py","p8_registry_fixture")
    points=[];bands=[]
    for alloy in ["ti6al4v","alsi10mg"]:
        for power in [100.,200.,400.]:
            s=nominal(registry,alloy,power);nom=evaluate(s)
            if power!=200:
                points.append(dict(alloy=alloy,power_W=power,values=nom))
                continue
            modules={"cavity":CAVITY_FIELDS,"meltDepthLink":LINK_FIELDS,"marangoni":MARANGONI_FIELDS,
                "surfaceBalance":set(nom)-CAVITY_FIELDS-LINK_FIELDS-MARANGONI_FIELDS}
            records={key:[] for key in modules}
            for name,arm in arms(registry,alloy,s):
                local_m=name.startswith(("slope_","viscosity_","deltaT_","length_"))
                local_surface=name.startswith("accommodation_")
                if local_m:output={**nom,**marangoni(arm)};applicable=["marangoni"]
                elif local_surface:output={**nom,**surface(arm)};applicable=["surfaceBalance"]
                else:
                    output=nom if name=="nominal" else evaluate(arm)
                    applicable=["cavity","meltDepthLink","surfaceBalance"]
                    if name.startswith("onset_"):applicable=["cavity","meltDepthLink"]
                    if name=="nominal" or any(arm[k]!=s[k] for k in ["kl","rhol","cpl","slope","mu","L","deltaT"]):
                        applicable.append("marangoni")
                for module in applicable:
                    row=dict(armId=name,provenance=provenance_data.arm_provenance(alloy,name),
                        inputProvenance=provenance_data.input_provenance(alloy,name,arm,s),
                        inputs=arm,values={k:output[k] for k in sorted(modules[module])},
                        consistencyStatus=consistency_status(module,
                            above_onset=output["modeledAboveOnset"],peclet=output["peclet"],
                            aspect=output["cavityDepth_um"]*1e-6/arm["d"],source_transfer=bool(input_scope_reasons(
                                module,provenance_data.input_provenance(alloy,name,arm,s)))),
                        validationStatus=SURFACE_VALIDATION if module=="surfaceBalance" else NON_SURFACE_VALIDATION,
                        experimentalValidation=False,moduleEvidenceCeiling="screening-only")
                    row["valueProvenance"]=value_provenance(module,row["values"],row["inputProvenance"])
                    row["provenance"]=provenance_data.changed_input_provenance(
                        alloy,name,arm,s,row["inputProvenance"])
                    row["inputScopeReasons"]=input_scope_reasons(module,row["inputProvenance"])
                    if module=="meltDepthLink":row["fieldShapeDiagnostics"]=field_shape_diagnostic(arm,output)
                    records[module].append(row)
            point=dict(alloy=alloy,power_W=power,values=nom,modules={})
            for module,rows in records.items():
                module_band=band([(r["armId"],r["values"]) for r in rows],{k:nom[k] for k in sorted(modules[module])})
                by_id={row["armId"]:row for row in rows}
                for key,field in module_band["fields"].items():
                    field["sourceEvidence"]={position:by_id[field[position+"ArmId"] if position!="nominal" else "nominal"]["valueProvenance"][key]
                        for position in ("min","nominal","max")}
                    field["armProvenance"]={position:by_id[field[position+"ArmId"] if position!="nominal" else "nominal"]["provenance"]
                        for position in ("min","nominal","max")}
                statuses={}
                for row in rows:statuses[row["consistencyStatus"]]=statuses.get(row["consistencyStatus"],0)+1
                module_band.update(armIds=[r["armId"] for r in rows],successfulArms=len(rows),failedArms=[],
                    armResults=rows,statusSupport=statuses,
                    validationStatus=SURFACE_VALIDATION if module=="surfaceBalance" else NON_SURFACE_VALIDATION,
                    experimentalValidation=False,moduleEvidenceCeiling="screening-only")
                if module in {"cavity","meltDepthLink"}:
                    support=sum(r["inputs"]["P"]>onset_power(r["inputs"]) for r in rows)
                    module_band["modeledOnsetSupport"]=dict(above=support,total=len(rows),unresolved=0,
                       arms=[dict(armId=r["armId"],modeledAboveOnset=r["inputs"]["P"]>onset_power(r["inputs"]),
                                  provenance=r["provenance"]) for r in rows],
                       caveat="Positive-depression inception scenarios only; equal-weight conventions, not a calibrated probability. O2 geometric threshold is excluded.")
                    if module=="meltDepthLink":
                        crossing=0<support<len(rows)
                        module_band["bandCrossesOnset"]=crossing
                        for row in rows:
                            diagnostic=row["fieldShapeDiagnostics"]
                            diagnostic["warningRequired"]=diagnostic["nearOnset"] or crossing
                point["modules"][module]=module_band
            points.append(dict(alloy=alloy,power_W=power,values=nom))
            bands.append(dict(alloy=alloy,power_W=power,modules=point["modules"]))
    assert all("onset_O2" not in module["armIds"] for item in bands for module in item["modules"].values())
    al_state=nominal(registry,"alsi10mg",200.)
    al_inputs=provenance_data.input_provenance("alsi10mg","nominal",al_state,al_state)
    support=value_provenance("cavity",{"onsetPower_W":1.,"cavityDepth_um":1.},al_inputs)
    assert "Tl" not in support["onsetPower_W"]["dependsOn"]
    legacy_inputs=provenance_data.input_provenance("alsi10mg","srv",al_state,al_state)
    support=value_provenance("surfaceBalance",{"absorbedCenterFlux_W_m2":1.},legacy_inputs)
    assert support["absorbedCenterFlux_W_m2"]["sourceEvidenceKind"]=="Literature estimate"
    assert support["absorbedCenterFlux_W_m2"]["dependsOn"]==["A"]
    geometric=[];field_steps=[]
    for alloy in ["ti6al4v","alsi10mg"]:
        state=nominal(registry,alloy,200.);pstar=onset_power(state)
        geometric.append(dict(alloy=alloy,armId="onset_O2",event="geometric-R-about-1",
            thresholdPower_W=kernel.piston_threshold_sensitivity(material(state),state["v"],state["d"]),
            thresholdToInceptionRatio=kernel.piston_threshold_sensitivity(material(state),state["v"],state["d"])/pstar,
            includedInInceptionEnvelope=False,includedInSupport=False,
            cavityDepth_um=None,linkedMeltDepth_um=None,
            provenance=provenance_data.arm_provenance(alloy,"onset_O2"),
            inputProvenance=provenance_data.input_provenance(alloy,"onset_O2",{**state,"onsetMethod":"O2"},state)))
        side_records=[]
        for side,factor in [("below",1-1e-9),("at",1.),("above",1+1e-9)]:
            near={**state,"P":pstar*factor};value=evaluate(near)
            if side!="above":
                assert value["cavityDepth_um"]==0. and value["linkedMeltDepth_um"]==value["conductionDepth_um"]
                assert value["controllingLeg"]=="conduction" and value["roots"]==[]
            else:
                assert value["cavityDepth_um"]>0. and value["controllingLeg"]=="conditional-link"
            side_records.append(dict(side=side,powerFactor=factor,inputs=near,values=value,
                                     fieldShapeDiagnostics=field_shape_diagnostic(near,value)))
        at=side_records[1]["values"];point=kernel.melt_depth_from_e(0.,state["A"]*pstar,state["v"],state["K"],
            state["Tl"]-state["T0"],state["alpha"],chi=0.,observable="envelope",order=64,x_samples=129)*1e6
        step=point-at["conductionDepth_um"]
        analytic_point=independent_point_depth(state,pstar)
        assert abs(analytic_point-point)*1e-6<=1e-13
        assert step>0 and math.isclose(side_records[2]["values"]["linkedMeltDepth_um"],point,rel_tol=1e-8)
        field_steps.append(dict(alloy=alloy,onsetPower_W=pstar,relativeBracket=1e-9,records=side_records,
            atOnsetGaussianDepth_um=at["conductionDepth_um"],aboveOnsetPointLimitDepth_um=point,
            independentPointLimitDepth_um=analytic_point,pointLimitIndependentDifference_m=abs(analytic_point-point)*1e-6,
            fieldShapeStep_um=step,pointToGaussianRatio=point/at["conductionDepth_um"],
            aboveOnsetFieldChanged=False,cause="Finite Gaussian below/at onset versus singular surface-point limit above onset."))
    field_warning_checks=[]
    for alloy, expected in (("ti6al4v",False),("alsi10mg",True)):
        link=next(item for item in bands if item["alloy"]==alloy)["modules"]["meltDepthLink"]
        nominal_row=next(row for row in link["armResults"] if row["armId"]=="nominal")
        assert nominal_row["fieldShapeDiagnostics"]["nearOnset"] is expected
        field_warning_checks.append(dict(case=alloy+"-nominal-200W",expectedNearOnset=expected,
            diagnostics=nominal_row["fieldShapeDiagnostics"]))
        if alloy=="alsi10mg":
            above=[row for row in link["armResults"] if row["inputs"]["P"]>onset_power(row["inputs"])]
            assert len(above)==22 and all(row["fieldShapeDiagnostics"]["nearOnset"] for row in above)
            ht=next(row for row in link["armResults"] if row["armId"]=="state_HT")
            assert ht["fieldShapeDiagnostics"]["nearOnset"] and ht["fieldShapeDiagnostics"]["fieldShapeShare"] is None
            field_warning_checks.append(dict(case="alsi10mg-state_HT-below",expectedNearOnset=True,
                powerOverOnset=ht["inputs"]["P"]/onset_power(ht["inputs"]),diagnostics=ht["fieldShapeDiagnostics"]))
    for case,ratio,floor,excess,shape,expected in [
        ("share-boundary",1.3,10.,4.,2.,True),
        ("share-below-boundary",1.3,10.,4.,1.999,False),
        ("unresolved-excess",1.3,10.,1e-7,1e-7,False),
        ("no-positive-shape-excess",1.3,10.,4.,-1.,False),
        ("below-window-inside",.9995,10.,0.,0.,True),
        ("below-window-boundary",.999,10.,0.,0.,True),
        ("below-window-outside",.998,10.,0.,0.,False)]:
        policy=field_shape_policy(ratio,floor,excess,shape)
        assert policy["nearOnset"] is expected,case
        field_warning_checks.append(dict(case=case,powerOverOnset=ratio,gaussianFloor_um=floor,
            conditionalExcess_um=excess,pointExcess_um=shape,expectedNearOnset=expected,diagnostics=policy))
    status_checks=[]
    for name,parameters,expected in [
        ("source-transfer",dict(source_transfer=True),"extrapolated"),
        ("low-aspect",dict(aspect=.308),"extrapolated"),
        ("low-Pe",dict(peclet=.577),"extrapolated"),
        ("below-onset-transfer",dict(above_onset=False,aspect=0.,source_transfer=True),"extrapolated"),
        ("below-onset-resolved-zero",dict(above_onset=False,aspect=0.),"inRange"),
        ("hard-failure",dict(hard_failure=True),"outOfRange"),
        ("admitted-synthetic-tuple",dict(),"inRange")]:
        actual=consistency_status("cavity",**parameters);assert actual==expected
        status_checks.append(dict(case=name,parameters=parameters,status=actual,
            insideRangeSentenceEligible=actual=="inRange",validationStatus=NON_SURFACE_VALIDATION))
    gain=gaussian_gain(0,80e-6,20,1e-5)
    assert math.isclose(gain,1/(math.sqrt(2*math.pi)*20*40e-6),rel_tol=1e-10)
    s=nominal(registry,"ti6al4v",200.)
    zero=marangoni({**s,"slope":0.})
    assert zero["marangoniNumber"]==zero["surfaceVelocityScale_m_s"]==zero["liquidPecletScale"]==0
    zero_delta=marangoni({**s,"deltaT":0.})
    assert zero_delta["marangoniNumber"]==zero_delta["surfaceVelocityScale_m_s"]==0
    assert zero_delta["flowDirection"]=="none"
    positive=marangoni({**s,"slope":-s["slope"]})
    assert positive["marangoniNumber"]==-marangoni(s)["marangoniNumber"]
    assert positive["surfaceVelocityScale_m_s"]==marangoni(s)["surfaceVelocityScale_m_s"]
    assert positive["flowDirection"]=="inward" and marangoni(s)["flowDirection"]=="outward"
    disabled=surface({**s,"accommodation":0.,"emissivity":0.})
    assert math.isclose(disabled["peakTemperatureProxy_K"],disabled["lossFreeCenterTemperature_K"],rel_tol=1e-9)
    no_melt=[]
    no_melt.append(dict(power_W=0.,gaussianFloor=gaussian_floor({**s,"P":0.})))
    for power in [5.,10.,20.]:
        item=evaluate({**s,"P":power});no_melt.append(dict(power_W=power,values=item))
        if power<=10:assert item["conductionDepth_um"]==0
        assert item["linkDispatch"]=="gaussian-below-onset"
        assert item["conditionalMeltDepth_um"]==item["conductionDepth_um"]
    onset_checks=[]
    gaussian_crosschecks=[]
    et=source_module(BASE,"python/eagar_tsai_solver.py","p8_et_fixture")
    for alloy in ["ti6al4v","alsi10mg"]:
        state=nominal(registry,alloy,200.);a=state["d"]/2;t=a/state["v"]
        field=et.EagarTsaiField(state["T0"]-273.15,state["A"]*state["P"],state["K"],state["alpha"],a).bind_speed(state["v"])
        for x,z in [(0.,0.),(-a,a/2),(-2*a,a)]:
            independent_field=state["A"]*state["P"]*gaussian_gain(state["v"],state["d"],state["K"],state["alpha"],x=x,z=z)
            et_field=field.temperature_C(x,0.,z)-(state["T0"]-273.15)
            relative=abs(independent_field-et_field)/independent_field
            assert relative<=1e-5
            gaussian_crosschecks.append(dict(alloy=alloy,x_m=x,z_m=z,independentRise_K=independent_field,
                unchangedEtRise_K=et_field,relativeDifference=relative))
        independent=state["A"]*4*math.sqrt(state["alpha"])/(math.pi**1.5*state["K"])*quad(
            lambda u:1/(a*a+8*state["alpha"]*u*u),0,math.sqrt(t),epsabs=1e-8,epsrel=1e-12)[0]
        primary=(kernel.threshold_temperature(material(state))-state["T0"])/onset_power(state)
        difference=abs(primary-independent)/independent
        assert difference<=1e-10
        limit=state["A"]/(math.sqrt(2*math.pi)*state["K"]*a)
        assert independent<=limit
        onset_checks.append(dict(alloy=alloy,independentTransientGain_K_W=independent,
            formulaGain_K_W=primary,relativeDifference=difference,stationaryLimitGain_K_W=limit))
    folds=[]
    for absorptance in [.18,.32]:
        rs=np.linspace(.2,1.,1601);hs=np.array([r/kernel.total_absorptance(r,absorptance) for r in rs])
        falling=np.flatnonzero(np.diff(hs)<0);j=int(falling[len(falling)//2]);scenario=float((hs[j]+hs[j+1])/2)
        roots=kernel._scan_roots(scenario,absorptance,"specular_cone",2049)
        assert len(roots)>=3 and [r.stability for r in roots]==["stable","unstable","stable"]
        folds.append(dict(absorptance=absorptance,S=scenario,roots=[dict(R=float(r.R),scalarRelaxation=r.stability) for r in roots],
            selectedR=float(min(r.R for r in roots if r.stability=="stable"))))
    h=lambda r:r/kernel.total_absorptance(r,.18)
    fold=minimize_scalar(lambda r:-h(r),bounds=(.3,.4),method="bounded",options={"xatol":1e-13})
    tangent=kernel._scan_roots(h(float(fold.x)),.18,"specular_cone",2049)
    assert any(r.stability=="neutral" for r in tangent)
    folds.append(dict(absorptance=.18,S=h(float(fold.x)),kind="tangent",
        roots=[dict(R=float(r.R),scalarRelaxation=r.stability) for r in tangent],
        selectedR=float(min(r.R for r in tangent if r.stability=="stable"))))
    contradictions=[]
    for alloy in ["ti6al4v","alsi10mg"]:
        state=nominal(registry,alloy,200.);pstar=onset_power(state);threshold=kernel.threshold_temperature(material(state))
        at_onset=surface({**state,"P":pstar})
        b=state["Lv"]*state["M"]/RG
        ps=101325*math.exp(b*(1/state["Tv"]-1/threshold))
        j=state["accommodation"]*state["effectiveNetFactor"]*ps*math.sqrt(state["M"]/(2*math.pi*RG*threshold))
        flux=at_onset["conductiveAdmittance_W_m2K"]*(threshold-state["T0"])+state["Lv"]*j+state["emissivity"]*SB*(threshold**4-state["T0"]**4)
        reached=flux*math.pi*(state["d"]/2)**2/(2*state["A"])
        assert math.isclose(surface({**state,"P":reached})["peakTemperatureProxy_K"],threshold,rel_tol=1e-9)
        contradictions.append(dict(alloy=alloy,onsetPower_W=pstar,thresholdTemperature_K=threshold,
          surfaceAtCavityOnset=at_onset,surfaceThresholdPower_W=reached,surfaceToCavityOnsetRatio=reached/pstar,
          validationStatus=SURFACE_VALIDATION,experimentalValidation=False,
          scope="Surface-derived comparison artefacts; cavity/link validationStatus stays independent."))
    t=1823.;gamma=1.30e-5;dh=-166200.;activity=.001
    def sigma(temp):return -4.3e-4*temp-RG*temp*gamma*math.log1p(.00318*activity*math.exp(-dh/(RG*temp)))
    b=.00318*activity*math.exp(-dh/(RG*t))
    derivative=-4.3e-4-RG*gamma*math.log1p(b)-gamma*dh/t*b/(1+b)
    assert math.isclose(derivative,(sigma(t+.01)-sigma(t-.01))/.02,rel_tol=1e-8)
    for gamma,dh,k1 in [(1.30e-5,-166200.,.00318),(2.03e-5,-146300.,.0138)]:
        zero_activity=k1*0.*math.exp(-dh/(RG*t))
        clean=-4.3e-4-RG*gamma*math.log1p(zero_activity)-gamma*dh/t*zero_activity/(1+zero_activity)
        assert clean==-4.3e-4
    kernel_bytes=Path(kernel.__file__).read_text(encoding="utf-8").replace("\r\n","\n").encode("utf-8")
    script_bytes=Path(__file__).read_text(encoding="utf-8").replace("\r\n","\n").encode("utf-8")
    provenance_bytes=Path(provenance_data.__file__).read_text(encoding="utf-8").replace("\r\n","\n").encode("utf-8")
    return dict(evidence="synthetic software reproduction; not experimental validation",sourceBase=BASE,
       sourceP3=P3,sourceP3Blob="b762dc6268b82f15f9e1fe529845b5e3e9013415",
       kernelAmendment="p8-amendment3-kernel-2026-10-15",modelIdentity="p8-research-synthetic-v4",
       belowOnsetPolicy="Gaussian floor dispatch; above-onset point/line field has a residual discontinuity at P* despite continuous energy allocation",
       kernelCanonicalLfSha256=hashlib.sha256(kernel_bytes).hexdigest(),
       scriptCanonicalLfSha256=hashlib.sha256(script_bytes).hexdigest(),
       provenanceCanonicalLfSha256=hashlib.sha256(provenance_bytes).hexdigest(),sourceCanonicalLfSha256=SOURCE_HASHES,
       bandMethod="module-local one-at-a-time union; no interactions, confidence interval, error bar or bounds",
       labels=dict(cavity="conditional scalar cavity hypothesis; numerical relaxation is not keyhole stability",
          meltDepthLink="conditional thermal construction; Gaussian finite-source dispatch below onset",
          marangoni="diagnostic scales from assumed deltaT and length; not a transport correction",
          surfaceBalance="falsified flat HKL closure against IN625 mass-loss test; Ti/Al transfer; T, evaporation and recoil are closure artefacts"),
       tolerances=dict(replay="abs(a-b) <= max(absTol, relTol*max(abs(a),abs(b)))",
          relative=2e-6,absolute=1e-7,rootScanResidual="2e-9 max(1,S)",
          cavityEnergyAbsolute_W=1e-6,cavityEnergyRelative=1e-8,photonRelative=1e-10,
          surfaceFluxRelative=1e-10,cylinderRelative=1e-8,surfaceGainRelative=1e-8,
          meltDepthRefinementRelative=.01,depthBisectionAbsolute_m=1e-14,depthBisectionRelative=1e-11,
          gaussianFloorConvergenceAbsolute_m=2e-11,gaussianFloorConvergenceRelative=1e-6,
          extremumTieBreak="first manifest arm among equal values"),
       points=points,bands=bands,noMeltLimits=no_melt,onsetSurfaceContradictions=contradictions,
       geometricThresholdDiagnostics=geometric,fieldShapeStepChecks=field_steps,
       fieldShapeWarningChecks=field_warning_checks,
       statusSemanticsChecks=status_checks,secondaryAlloyManifests=provenance_data.secondary_manifests(registry),
       independentTransientChecks=onset_checks,gaussianFieldCrosschecks=gaussian_crosschecks,syntheticRootTopology=folds)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--check",action="store_true")
    args=parser.parse_args(); result=run()
    if args.check:
        pinned=json.loads(FIXTURE.read_text(encoding="utf-8"))
        def compare(a,b,path=""):
            if isinstance(a,float):
                if (".inputs." in path or ".inputProvenance." in path or path.startswith(".tolerances.")
                    or path.endswith((".power_W",".relativeBracket",".powerFactor"))):
                    assert a==b,(path,a,b)
                else:
                    assert math.isclose(a,b,rel_tol=2e-6,abs_tol=1e-7),(path,a,b)
            elif isinstance(a,dict):
                assert a.keys()==b.keys()
                for k in a: compare(a[k],b[k],path+"."+k)
            elif isinstance(a,list):
                assert len(a)==len(b)
                for index,(x,y) in enumerate(zip(a,b)): compare(x,y,path+f"[{index}]")
            else: assert a==b,(a,b)
        compare(result,pinned)
        print("PASS: six synthetic points with module-local per-arm roots/bands and analytic/energy/Gaussian limits")
    else:
        rendered=render_fixture(result)+"\n"
        assert json.loads(rendered)==result
        FIXTURE.write_text(rendered,encoding="utf-8",newline="\n")
        print(f"Wrote synthetic fixture: {len(result['points'])} points with full module-local arm records")
