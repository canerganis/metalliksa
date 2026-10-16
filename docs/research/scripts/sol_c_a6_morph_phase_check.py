"""Research-only A6 morphology/phase arithmetic. No served imports or data sets."""
from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
import hashlib
import itertools
import json
import math
from pathlib import Path
import re


@dataclass(frozen=True)
class Binary:
    c: float
    k: float
    m: float
    d: float
    gamma: float
    nuclei: float
    activation: float


# wt-percent-based source coefficients. m is a positive magnitude here.
PARAMS = {
    # Explicit freezing-range-closed surrogate, not a correction of printed m=.088.
    "ti64": Binary(10, .838, 50*.838/(10*(1-.838)), 9.5e-9, 2.2e-7, 5e14, 8),
    "alsi10mg": Binary(10, .13, 6.5, 3e-9, 9e-8, 2e15, 8),
    "in718": Binary(5, .48, 10.5, 3e-9, 3.65e-7, 2.65e14, 0),
    "in625": Binary(5, .48, 10.5, 3e-9, 3.65e-7, 2.65e14, 0),
    "316l": Binary(.029, .17, 84.3, 2e-9, 1.9e-7, 1e13, 8),
}
SOURCE_LOCATORS = {
    "ti64": "https://arxiv.org/html/1809.01056#S3.T6",
    "alsi10mg": "https://arxiv.org/html/2003.09757v1#S5.T2",
    "ni5nb": "https://arxiv.org/html/1705.06669#S2.T2",
    "316l": "https://doi.org/10.1016/j.matdes.2020.109395 Table 7",
    "hunt": "https://doi.org/10.1016/j.addma.2023.103802 Eqs 2,3,7,8",
    "tip": "https://doi.org/10.1038/s41467-025-60162-0 Eq 6",
    "km": "https://doi.org/10.3390/met8080633 Eq 19, section 4.1",
    "eutectic": "https://doi.org/10.3390/met12101711 Table 1",
    "ternary_phases": "https://doi.org/10.2320/matertrans.MT-M2022165 section 4.3",
    "atomic_weights": "https://ciaaw.org/abridged-atomic-weights.htm Mg and Si rows",
}
KM_TRANSUS_C = 998.0
KM_MS_C = 575.0
KM_COEFFICIENT = .005
KM_RATE_K_S = 410.0


def positive(*values: float) -> None:
    if any(not math.isfinite(v) or v <= 0 for v in values):
        raise ValueError("nonphysical-input")


def morphology(p: Binary, g: float, rate: float, *, cooling=True,
               current=True, compatible_field=True, absolute_stability_limit=None) -> dict:
    positive(p.c, p.m, p.d, p.gamma, g, rate)
    if not 0 < p.k < 1 or not math.isfinite(p.nuclei) or p.nuclei < 0:
        raise ValueError("nonphysical-input")
    if not math.isfinite(p.activation) or p.activation < 0:
        raise ValueError("nonphysical-input")
    if not cooling:
        raise ValueError("invalid-interface-sample")
    if not current:
        raise ValueError("stale-parent-input")
    if not compatible_field:
        raise ValueError("keyhole-field-inconsistent")
    q = p.m * p.c * (1-p.k)
    freezing = q/p.k
    chi = freezing * rate / (p.d*g)
    tip = math.sqrt(8*q*p.gamma*rate/p.d)
    # The planar index remains numeric when no dendritic grain model applies.
    if chi <= 1 or tip > freezing or (absolute_stability_limit is not None and rate >= absolute_stability_limit):
        return dict(chi=chi,tip_K=tip,radius_m=None,extended=None,fraction=None,
                    grain_class=None,warnings=[],reason="outside-dendritic-growth-domain")
    radius = 0.0 if tip <= p.activation else tip/(3*g)*(1-(p.activation/tip)**3)
    extended = 4*math.pi/3 * p.nuclei*radius**3
    fraction = -math.expm1(-extended)
    grain_class = "columnar" if fraction <= .0049 else "equiaxed" if fraction >= .49 else "mixed"
    warnings = []
    if chi <= 1:
        warnings.append("outside-dendritic-stability-domain")
    if tip > freezing:
        warnings.append("tip-undercooling-exceeds-binary-freezing-range")
    return dict(chi=chi, tip_K=tip, radius_m=radius, extended=extended,
                fraction=fraction, grain_class=grain_class, warnings=warnings)


def km_quench(history, *, fully_melted: bool, beta0=1.0):
    """History rows are increasing time in seconds and absolute temperature in K."""
    if not fully_melted:
        raise ValueError("missing-full-melt-initialization")
    if not math.isfinite(beta0) or not 0 <= beta0 <= 1:
        raise ValueError("nonphysical-input")
    if len(history) < 2:
        raise ValueError("missing-thermal-history")
    for t, temp in history:
        if not math.isfinite(t):
            raise ValueError("nonphysical-input")
        positive(temp)
    transus, ms, coefficient = KM_TRANSUS_C+273.15, KM_MS_C+273.15, KM_COEFFICIENT
    if history[0][1] < transus:
        raise ValueError("missing-beta-initialization")
    checked = []
    for (t0, a), (t1, b) in zip(history, history[1:]):
        if t1 <= t0:
            raise ValueError("nonphysical-input")
        if b > a:
            raise ValueError("reheating-needs-competing-kinetics")
        # Strict research-scenario gate, not a universal source kinetic threshold:
        # extend rapid cooling below Ms to exclude omitted holds/dissolution.
        if a <= transus and (a-b)/(t1-t0) < KM_RATE_K_S:
            raise ValueError("slow-cooling-needs-competing-kinetics")
        if min(a, transus) > max(b, ms):
            checked.append((a-b)/(t1-t0))
    if history[-1][1] < ms and (not checked or min(checked) < KM_RATE_K_S):
        raise ValueError("slow-cooling-needs-competing-kinetics")
    martensite = beta0 * -math.expm1(-coefficient*max(0, ms-history[-1][1]))
    return martensite, beta0-martensite


def al_constituents(c=10.0, k=.13, ce=12.6, *, complete=True):
    positive(c, ce)
    if not math.isfinite(k) or not 0 < k < 1:
        raise ValueError("nonphysical-input")
    if c > ce:
        raise ValueError("hypereutectic-needs-primary-silicon-model")
    if not complete:
        raise ValueError("partial-path-needs-temperature")
    residual = (ce/c)**(1/(k-1))
    return 1-residual, residual


def al_equilibrium_limit(c_si=.10, c_mg=.003):
    if any(not math.isfinite(x) or x < 0 for x in (c_si,c_mg)) or c_si+c_mg >= 1:
        raise ValueError("nonphysical-input")
    mg, si = 24.305,28.085
    bound_si = c_mg*si/(2*mg)
    if bound_si > c_si:
        raise ValueError("silicon-deficit-needs-different-phase-set")
    f_mg2si = c_mg+bound_si
    f_si = c_si-bound_si
    return 1-f_si-f_mg2si, f_si, f_mg2si


def close(a, b, *, rtol=1e-10, atol=1e-14):
    assert math.isclose(a, b, rel_tol=rtol, abs_tol=atol), (a, b)


def rejects(call, reason=None):
    try:
        call()
    except ValueError as error:
        if reason is not None:
            assert str(error) == reason, (reason, str(error))
    else:
        raise AssertionError("negative case unexpectedly accepted")


def run_checks():
    # Parse bounded source-table receipts, instead of comparing repeated runtime literals.
    receipt = Path(__file__).resolve().parents[1]/"sol_c_a6_morph_source_extracts.json"
    raw_receipt = receipt.read_bytes()
    source_identity = hashlib.sha256(raw_receipt).hexdigest()
    extracted = json.loads(raw_receipt)["sources"]
    def number(source,key):
        rows = [row for row in extracted[source]["excerpt"].splitlines() if row.startswith(key)]
        assert len(rows)==1,(source,key)
        field = rows[0].split("|")[-1].strip()
        scientific = re.match(r"([+-]?[0-9.]+)\s*×\s*10\^([+-]?[0-9]+)",field)
        if scientific:
            return float(scientific[1])*10**int(scientific[2])
        return float(re.match(r"[+-]?[0-9.]+",field)[0])
    mappings = {
        "ti64": ("ti64",("Alloy Mass", "Equilibrium Partition", None, "Liquid Diffusion", "Gibbs-Thomson")),
        "alsi10mg": ("alsi10mg",(None,"Partition coefficient","Liquids slope","Solute diffusivity","Gibbs-Thomson")),
        "in718": ("ni5nb",("Initial alloy","Equilibrium Partition","Liquidus Slope","Liquid Diffusion","Gibbs-Thomson")),
        "in625": ("ni5nb",("Initial alloy","Equilibrium Partition","Liquidus Slope","Liquid Diffusion","Gibbs-Thomson")),
        "316l": ("316l",("equilibrium concentration","partition coefficient","slope of liquidus","liquid diffusivity","Gibbs-Thomson")),
    }
    for alloy,(source,keys) in mappings.items():
        p=PARAMS[alloy]
        for actual,key in zip((p.c,p.k,p.m,p.d,p.gamma),keys):
            if key is not None:
                close(actual,abs(number(source,key)))
    close(PARAMS["ti64"].nuclei,number("ti_nucleation","Maximum density"))
    close(PARAMS["ti64"].activation,number("ti_nucleation","Average nucleation"))
    source_p=number("ti64","Equilibrium Freezing Range")
    ti=PARAMS["ti64"]
    close(ti.m*ti.c*(1-ti.k)/ti.k,source_p)
    assert abs(abs(number("ti64","Liquidus Slope"))-ti.m) > 1
    close(PARAMS["alsi10mg"].nuclei,number("alsi10mg","Inoculant density"))
    close(number("al_eutectic","Eutectic composition"),12.6)
    for phrase in ("Tm = 575 C","km = 0.005","T_beta_trans = 998 C","410 C/s"):
        assert phrase in extracted["km"]["excerpt"]
    km_text = extracted["km"]["excerpt"]
    close(KM_TRANSUS_C,float(re.search(r"T_beta_trans = ([0-9.]+)",km_text)[1]))
    close(KM_MS_C,float(re.search(r"Tm = ([0-9.]+)",km_text)[1]))
    close(KM_COEFFICIENT,float(re.search(r"km = ([0-9.]+)",km_text)[1]))
    close(KM_RATE_K_S,float(re.search(r"slower than ([0-9.]+) C/s",km_text)[1]))
    source_km=float(re.search(r"km = ([0-9.]+)",extracted["km"]["excerpt"])[1])
    source_ms=float(re.search(r"Tm = ([0-9.]+)",extracted["km"]["excerpt"])[1])
    for phrase in ("phi = 0.49","phi = 0.0049","n = 2"):
        assert phrase in extracted["hunt"]["excerpt"]
    assert all("https://" in v for v in SOURCE_LOCATORS.values())
    examples = {}
    for alloy, p in PARAMS.items():
        # 316L's carbon-only binary law has a narrower physical R domain.
        reference_rate = .01 if alloy=="316l" else .1
        result = morphology(p, 1e6, reference_rate)
        examples[alloy] = {k: result[k] for k in ("chi", "tip_K", "fraction", "grain_class", "warnings")}
        # Radius oracle: independent Simpson integration of v_e/(R G) d(DeltaT).
        # The kinetic constant is separately reconstructed from dimensions Q,Gamma,D.
        kinetic = p.d/(8*p.m*p.c*(1-p.k)*p.gamma)
        high, low = result["tip_K"], p.activation
        integrated = 0.0
        if high > low:
            n = 200
            step = (high-low)/n
            terms = []
            for j in range(n+1):
                dt = low + j*step
                w = 1 if j in (0,n) else 4 if j%2 else 2
                terms.append(w*kinetic*dt*dt/(reference_rate*1e6))
            integrated = math.fsum(terms)*step/3
        close(result["radius_m"], integrated)
        # Unit oracle: compute constitutional ratio using mm/s, K/mm, mm2/s.
        p_kelvin = p.m*p.c*(1-p.k)/p.k
        chi_mm = p_kelvin*(reference_rate*1000)/((p.d*1e6)*(1e6/1000))
        close(result["chi"], chi_mm)
        assert 0 <= result["fraction"] <= 1
        for bad in (math.nan, math.inf, 0, -1):
            rejects(lambda: morphology(p,bad,.1))
            rejects(lambda: morphology(p,1e6,bad))
        rejects(lambda: morphology(p,1e6,.1,cooling=False), "invalid-interface-sample")
        rejects(lambda: morphology(p,1e6,.1,current=False), "stale-parent-input")
        rejects(lambda: morphology(p,1e6,.1,compatible_field=False), "keyhole-field-inconsistent")
    # True-fraction threshold differs from extended fraction; detect wrong-threshold mutant.
    p = PARAMS["in718"]
    base = morphology(p,1e6,.1)
    for target, expected in ((.0048,"columnar"),(.0055,"mixed"),(.48,"mixed"),(.50,"equiaxed")):
        n0 = -math.log1p(-target)/(4*math.pi/3*base["radius_m"]**3)
        observed = morphology(replace(p,nuclei=n0),1e6,.1)
        close(observed["fraction"],target)
        assert observed["grain_class"] == expected
    assert morphology(replace(p,nuclei=0),1e6,.1)["fraction"] == 0
    assert morphology(replace(p,activation=1e6),1e6,.1)["fraction"] == 0
    rejects(lambda: morphology(replace(p,k=1),1e6,.1))
    rejects(lambda: morphology(replace(p,nuclei=-1),1e6,.1))
    planar = morphology(p,1e12,.001)
    assert planar["chi"] < 1 and planar["fraction"] is None
    absolute = morphology(p,1e6,1,absolute_stability_limit=.98)
    assert absolute["chi"] > 1 and absolute["fraction"] is None
    # A declared joint box: monotone extremes enclose the full explicit corner sweep.
    corners = [morphology(replace(p,nuclei=n,activation=a),g,r)["fraction"]
               for g,r,n,a in itertools.product((5e5,2e6),(.02,.08),(1e10,1e15),(0,20))]
    lower = morphology(replace(p,nuclei=1e10,activation=20),2e6,.02)["fraction"]
    upper = morphology(replace(p,nuclei=1e15,activation=0),5e5,.08)["fraction"]
    close(min(corners),lower)
    close(max(corners),upper)
    # Local nonlinear evaluation is essential, even on perfectly paired thermal inputs.
    local = [morphology(p,g,r)["fraction"] for g,r in ((2e5,.08),(2e6,.008))]
    aggregate = math.fsum(local)/2
    unpaired = morphology(p,1.1e6,.044)["fraction"]
    assert abs(aggregate-unpaired) > .01
    # KM independent depletion ODE via 10,000 equal undercooling increments.
    history = [(0,1700+273.15),(.7,1000+273.15),(.9,800+273.15),
               (1.125,575+273.15),(1.675,25+273.15)]
    alpha, beta = km_quench(history,fully_melted=True)
    close(alpha,.9360721387932924)
    independent_beta = 1.0
    dx = (source_ms-25)/10000
    z = -source_km*dx
    rk4_decay = 1+z+z*z/2+z*z*z/6+z**4/24
    for _ in range(10000):
        independent_beta *= rk4_decay
    close(beta,independent_beta,rtol=1e-10)
    close(alpha+beta,1)
    alpha_half,beta_half = km_quench(history,fully_melted=True,beta0=.5)
    close(alpha_half,alpha/2)
    close(alpha_half+beta_half,.5)
    # Identical front cooling can precede a slow subsolidus path: must not inherit G*R.
    slow = list(history)
    slow[2:] = [(2.7,800+273.15),(4.95,575+273.15),(10.45,25+273.15)]
    rejects(lambda: km_quench(slow,fully_melted=True),"slow-cooling-needs-competing-kinetics")
    slow_below_ms = history[:4]+[(2.125,500+273.15),(2.6,25+273.15)]
    rejects(lambda: km_quench(slow_below_ms,fully_melted=True),"slow-cooling-needs-competing-kinetics")
    held_below_ms = history[:4]+[(1.3,500+273.15),(2.3,500+273.15),(2.8,25+273.15)]
    rejects(lambda: km_quench(held_below_ms,fully_melted=True),"slow-cooling-needs-competing-kinetics")
    rejects(lambda: km_quench(history,fully_melted=False),"missing-full-melt-initialization")
    reheated = history + [(2,200+273.15)]
    rejects(lambda: km_quench(reheated,fully_melted=True),"reheating-needs-competing-kinetics")
    # Scheil independent explicit mass-balance integration until CL reaches Ce.
    primary,eutectic = al_constituents()
    liquid, solute_liquid, solute_solid = 1.0,10.0,0.0
    ds = 1e-6
    while solute_liquid/liquid < 12.6:
        cl = solute_liquid/liquid
        step = min(ds,liquid)
        removed = .13*cl*step
        solute_solid += removed
        solute_liquid -= removed
        liquid -= step
    close(1-liquid,primary,rtol=0,atol=2e-6)
    close(solute_liquid+solute_solid,10,rtol=0,atol=3e-11)
    close(primary+eutectic,1)
    close(al_constituents(12.6)[0],0)
    rejects(lambda: al_constituents(13),"hypereutectic-needs-primary-silicon-model")
    rejects(lambda: al_constituents(complete=False),"partial-path-needs-temperature")
    for bad in (0,-1,math.inf,math.nan):
        rejects(lambda: al_constituents(bad))
    # Independent atom-inventory oracle for 1 g initial ternary sample.
    f_al,f_si,f_mg2si = al_equilibrium_limit()
    source_mg=float(extracted["atomic_weights"]["excerpt"].splitlines()[0].split("|")[3].split()[0])
    source_si=float(extracted["atomic_weights"]["excerpt"].splitlines()[1].split("|")[3].split()[0])
    formula_moles = f_mg2si/(2*source_mg+source_si)
    close(2*formula_moles*source_mg,.003)
    close(formula_moles*source_si+f_si,.10)
    close(f_al,.897)
    close(f_al+f_si+f_mg2si,1)
    close(al_equilibrium_limit(.1,0)[1],.1)
    rejects(lambda: al_equilibrium_limit(.0001,.01),"silicon-deficit-needs-different-phase-set")
    for a,b in ((math.nan,.003),(.1,math.inf),(.1,-1),(.9,.2)):
        rejects(lambda: al_equilibrium_limit(a,b))
    return {"status":"pass", "primary_extract_receipt_sha256":source_identity,
            "source_authentication":"bounded browser/search primary extraction, not original PDF bytes",
            "morphology_reference_G_K_m":1e6,"morphology_reference_R_m_s":.1,
            "316l_reference_R_m_s":.01,
            "morphology":examples,"ti64_quench_alpha_m":alpha,"ti64_quench_beta":beta,
            "alsi10mg_primary_alpha_mass":primary,"alsi10mg_eutectic_constituent_mass":eutectic,
            "alsi10mg_terminal_equilibrium_limit_mass":{"alphaAl":f_al,"Si":f_si,"Mg2Si":f_mg2si},
            "checks":"source transcription, independent integration, unit scaling, joint box, local pairing, negative cases",
            "physical_validation":False,"served_implementation_tested":False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check",action="store_true",required=True)
    parser.parse_args()
    print(json.dumps(run_checks(),indent=2,allow_nan=False))
