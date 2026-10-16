#!/usr/bin/env python3
"""Primary source and research-reference spacing checks, not served installation.

python -I -B docs/research/scripts/sol_c_a6_spacing_check.py --check
"""
from __future__ import annotations

import argparse
from decimal import Decimal, localcontext
import hashlib
import html
import importlib.util
import inspect
import math
from pathlib import Path
import re
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[3]
ARCHIVES = {
    'al': ('solc_a6_spacing_al.pdf', 'e8bc8ab8b029b5bc9aaf217f5aef167481610b1f04ad30820a6329370d32b1e4'),
    'steel': ('solc_a6_spacing_steel.pdf', '7fb5f22ed956c764f2079431101387ef792a86d426335ae4ce202a982ad6ec34'),
    'ni': ('solc_a6_spacing_ni.pdf', '9ceee36095cd4363239a0457f305e65970deeb1c813c2114546c7b63848f9569'),
    'ghosh': ('ghosh2017_solc_spacing.pdf', '446c2a8e16af32377d070d81a5ccf71e6059a58f3b38481951ecafd36463a5dd'),
    'ti': ('mizukami2020_solc_spacing.html', 'aa03cefa2f447d68b266bfec4f9787b53854d6590f9633d77d1c1eb0033fdd51'),
}


def need(ok, message):
    if not ok:
        raise AssertionError(message)


def compact(s):
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', s)).replace('−', '-').replace('‐', '-')


def primary_sources():
    """Read only primary equation/method pages; no simulation or measured pool data."""
    from pypdf import PdfReader
    contents = {}
    for name, (filename, digest) in ARCHIVES.items():
        path = ROOT / 'papers' / filename
        need(path.is_file(), 'missing primary source: ' + str(path))
        raw = path.read_bytes()
        need(hashlib.sha256(raw).hexdigest() == digest, 'source hash drift: ' + name)
        contents[name] = path
    al_reader = PdfReader(contents['al'])
    al = compact(al_reader.pages[12].extract_text())
    # These separately printed conclusions bind chemistry, units and coefficients;
    # the coefficient check is not a self-authored metadata comparison.
    for token in ('Al-10wt.%Si-0.45wt.%Mg:λ2=22(vL)-2/3',
                  'Al-10wt.%Si-1wt.%Mg:λ2=14(vL)-1.0',
                  'λ1=165', '[μm]', '[°C/s]', '[mm/s]'):
        need(token in al, 'Al primary conclusion transcription: ' + token)
    need('-0.4forbothalloys' in al, 'Al primary exponent missing')
    al_method = compact(al_reader.pages[5].extract_text())
    need('takingthetimederivative' in al_method and 'rightafter' in al_method,
         'Al local liquidus rate definition missing')
    steel_reader = PdfReader(contents['steel'])
    steel1 = compact(steel_reader.pages[15].extract_text())
    steel2 = compact(steel_reader.pages[16].extract_text())
    # The PDF encodes mathematical Greek letters as glyph names; the publisher
    # HTML independently displayed those variables. Numeric equation bytes bind here.
    need('(2)/u1D7061=80(/u1D700)-0.33' in steel1, 'steel Eq2 transcription')
    need('(6)/u1D7062=25(/u1D700)-0.28' in steel2, 'steel Eq6 transcription')
    need('between1450and1350°C' in steel2, 'steel cooling interval definition')
    ni = compact(PdfReader(contents['ni']).pages[3].extract_text())
    m = re.search(r'Secondaryspacing\(micron\)=([0-9]+\.[0-9]+)x\(Coolingrate,C/s\)-([0-9]+\.[0-9]+)', ni)
    need(m is not None, 'Mitchell primary Eq1 not found')
    ni_a, ni_n = map(float, m.groups())
    need((ni_a, ni_n) == (19.5, .63), 'Mitchell coefficient/exponent changed')
    ti = compact(html.unescape(re.sub(r'<[^>]+>', '', contents['ti'].read_text(encoding='utf-8'))))
    need('λ1=(-62CAl+699)T⋅-0.39' in ti and 'λ2=(-33CAl+366)T⋅-0.40' in ti,
         'Ti primary Eqs4/5 transcription')
    ghosh_reader = PdfReader(contents['ghosh'])
    table = compact(ghosh_reader.pages[7].extract_text())
    for token in ('EquilibriumPartitionCoefficient,ke0.48',
                  'EquilibriumFreezingRange,∆T0=Tl-Ts57K',
                  'LiquidDiffusionCoefficient,Dl3×10-9',
                  'Gibbs-Thomsoncoefficient,Γ3.65×10-7'):
        need(token in table, 'Ghosh Table2 row missing: ' + token)
    for page, token in ((11, 'PDAS=2.83(keΓ∆T0Dl)0.25G-0.5V-0.25'),
                        (12, 'PDAS=4.3(Γ∆T0Dl/ke)0.25G-0.5V-0.25')):
        need(token in compact(ghosh_reader.pages[page].extract_text()), 'Ghosh primary equation missing')
    # Feed PARSED source coefficients into the actual estimator, not duplicate
    # hand-entered literals that merely agree with the source assertions above.
    def parsed(pattern,text):
        match = re.search(pattern,text)
        need(match is not None,'coefficient parser: '+pattern)
        return tuple(map(float,match.groups()))
    ti_primary = parsed(r'λ1=\(-([0-9.]+)CAl\+([0-9.]+)\)T⋅-([0-9.]+)',ti)
    ti_secondary = parsed(r'λ2=\(-([0-9.]+)CAl\+([0-9.]+)\)T⋅-([0-9.]+)',ti)
    al_primary = parsed(r'λ1=([0-9.]+)\([^)]*\)-([0-9.]+)forbothalloys',al)
    al_secondary = parsed(r'0.45wt.%Mg:λ2=([0-9.]+)\(vL\)-([0-9]+)/([0-9]+)',al)
    al_alternative = parsed(r'1wt.%Mg:λ2=([0-9.]+)\(vL\)-([0-9.]+)',al)
    steel_primary = parsed(r'\(2\)/u1D7061=([0-9.]+)\(/u1D700\)-([0-9.]+)',steel1)
    steel_secondary = parsed(r'\(6\)/u1D7062=([0-9.]+)\(/u1D700\)-([0-9.]+)',steel2)
    def ghosh_number(pattern):
        return parsed(pattern,table)[0]
    def ghosh_scientific(pattern):
        a,b = parsed(pattern,table)
        return a*10**b
    eq7 = compact(ghosh_reader.pages[11].extract_text())
    eq8 = compact(ghosh_reader.pages[12].extract_text())
    return dict(ti_pdas=ti_primary,ti_sdas=ti_secondary,al_pdas=al_primary,
                al_sdas=(al_secondary[0],al_secondary[1]/al_secondary[2]),
                al_sdas_1mg=al_alternative,steel_pdas=steel_primary,steel_sdas=steel_secondary,
                ni_sdas=(ni_a,ni_n),
                ni_hunt=parsed(r'PDAS=([0-9.]+)\(keΓ∆T0Dl\)',eq7)[0],
                ni_kf=parsed(r'PDAS=([0-9.]+)\(Γ∆T0Dl/ke\)',eq8)[0],
                k=ghosh_number(r'EquilibriumPartitionCoefficient,ke([0-9.]+)'),
                dt=ghosh_number(r'∆T0=Tl-Ts([0-9.]+)K'),
                dl=ghosh_scientific(r'LiquidDiffusionCoefficient,Dl([0-9.]+)×10(-?[0-9]+)'),
                gamma=ghosh_scientific(r'Gibbs-Thomsoncoefficient,Γ([0-9.]+)×10(-?[0-9]+)'))


def positive(x):
    return isinstance(x, (int, float)) and math.isfinite(x) and x > 0


def raw_estimate(alloy, kind, g, r, *, coefficients, cooling_side=True, al=6., mg=.45):
    """Internal algebra only, NEVER an admitted value before estimate()'s gate."""
    if not cooling_side or not positive(g) or not positive(r):
        return None
    q = g * r
    if not positive(q):
        return None
    if alloy == 'ti6al4v':
        if not positive(al):
            return None
        slope,intercept,n = coefficients['ti_'+kind]
        a = intercept-slope*al
        return a * q ** -n * 1e-6 if a > 0 else None
    if alloy == 'alsi10mg':
        if kind == 'pdas':
            a,n=coefficients['al_pdas']
            return a * q ** -n * 1e-6
        if mg == .45:
            a,n=coefficients['al_sdas']
            return a * (1000 * r) ** -n * 1e-6
        if mg == 1.:
            a,n=coefficients['al_sdas_1mg']
            return a * (1000 * r) ** -n * 1e-6
        return None  # no invented interpolation between source chemistries
    if alloy == 'ss316l':
        a,n = coefficients['steel_'+kind]
        return a * q ** -n * 1e-6
    if alloy in ('in718', 'in625'):
        if kind == 'sdas':
            a,n = coefficients['ni_sdas']
            return a * q ** -n * 1e-6
        k,gamma,dt,dl = (coefficients[key] for key in ('k','gamma','dt','dl'))
        if not g * dl / dt < r < dt * dl / (k * gamma):
            return None
        return {name: p * z ** .25 * g ** -.5 * r ** -.25
                for name, p, z in (('hunt', coefficients['ni_hunt'], k * gamma * dt * dl),
                                   ('kurzFisher', coefficients['ni_kf'], gamma * dt * dl / k))}
    return None


def load_morphology():
    spec=importlib.util.spec_from_file_location('solc_a7_morph',Path(__file__).with_name('sol_c_a6_morph_phase_check.py'))
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module


MORPH = load_morphology()
ALIASES = {'ti6al4v':'ti64','ss316l':'316l','alsi10mg':'alsi10mg','in718':'in718','in625':'in625'}


def estimate(alloy,kind,g,r,*,coefficients,**kwargs):
    """Every PDAS/SDAS value passes its own named binary capillary screening gate.

    None maps to outside-source-model-domain for a scale/stability failure; the
    caller must retain raw diagnostics but must not display them as estimates.
    """
    if alloy not in ALIASES or kind not in ('pdas','sdas'):
        return None
    value=raw_estimate(alloy,kind,g,r,coefficients=coefficients,**kwargs)
    if value is None:
        return None
    cutoff=MORPH.capillary_cutoff(MORPH.PARAMS[ALIASES[alloy]],g,r)
    if cutoff is None:
        return None
    values=value.values() if isinstance(value,dict) else [value]
    return value if all(v >= cutoff for v in values) else None


def source_outside(alloy, q, r, *, al=6., process='lpbf', g=1e7):
    if alloy == 'ti6al4v':
        return process != 'eb-ingot' or al not in (2.9, 4., 4.3, 5., 5.7) or not 1 <= q <= 100
    if alloy == 'alsi10mg':
        return process != 'directional-casting' or not (.05 <= q <= 10.75 and .300 <= 1000*r <= 1.240)
    if alloy == 'ss316l':
        return process != 'cladding' or not 115 <= q <= 5204
    if alloy in ('in718', 'in625'):
        x = g ** -.5 * r ** -.25
        return not (math.isclose(g, 1e7, rel_tol=1e-12) and 4e-4 <= x <= 1.2e-3 and 5e4 <= q <= 3e6)
    return True


def decimal_reference(a, x, n):
    """Independent high-precision exp(log) path, not float ** repeated."""
    with localcontext() as ctx:
        ctx.prec = 50
        aa, xx, nn = map(lambda v: Decimal(str(v)), (a, x, n))
        return float(aa * (-nn * xx.ln()).exp() * Decimal('0.000001'))


def check_reference(coefficients, estimator=estimate):
    def estimate(*args,**kwargs):
        return estimator(*args,coefficients=coefficients,**kwargs)
    ni_a,ni_n=coefficients['ni_sdas']
    g, r = 1e7, .01
    cases = [('ti6al4v', 'pdas', 327., .39), ('ti6al4v', 'sdas', 168., .4),
             ('alsi10mg', 'pdas', 165., .4), ('ss316l', 'pdas', 80., .33),
             ('ss316l', 'sdas', 25., .28), ('in718', 'sdas', ni_a, ni_n),
             ('in625', 'sdas', ni_a, ni_n)]
    for alloy, kind, a, n in cases:
        # Source-law algebra is checked independently EVEN when the gate refuses
        # its tiny output. A refused raw result is never promoted to a value.
        value = raw_estimate(alloy, kind, g, r,coefficients=coefficients)
        expected = decimal_reference(a, g*r, n)
        need(math.isclose(value, expected, rel_tol=2e-14), 'independent Decimal reference: '+alloy+kind)
        # Invert the cooling law; this detects wrong exponent sign and um/m units.
        q_back = math.exp(math.log(a / (value * 1e6)) / n)
        need(math.isclose(q_back, 1e5, rel_tol=2e-14), 'inverse cooling rate failed')
    # Al secondary law uses mm/s. R=.001 m/s is 1mm/s, hence 22 or 14 um.
    need(math.isclose(estimate('alsi10mg', 'sdas', 1e6, .001), 22e-6, rel_tol=1e-14), 'Al mm/s conversion')
    need(math.isclose(estimate('alsi10mg', 'sdas', 1e6, .001, mg=1.), 14e-6, rel_tol=1e-14), 'Al second chemistry')
    need(estimate('alsi10mg','sdas',g,r,mg=.7) is None, 'invented chemistry interpolation')
    for alloy in ('in718', 'in625'):
        values = estimate(alloy, 'pdas', g, r)
        for name, p, factor in (('hunt', 2.83, .48), ('kurzFisher', 4.3, 1/.48)):
            left = values[name] ** 4 * g**2 * r
            right = p**4 * 3.65e-7 * 57 * 3e-9 * factor
            need(math.isclose(left, right, rel_tol=1e-13), 'independent fourth-power Ghosh identity')
        need(estimate(alloy,'pdas',5e7,.0012) is None, 'planar side admitted')
        need(estimate(alloy,'pdas',1e6,1.5) is None, 'absolute stability admitted')
        need(source_outside(alloy, 2e5, .01, g=2e7), 'off-line missing warning')
        need(estimate(alloy,'pdas',2e7,.01) is not None, 'off-line T2 erased')
    for alloy in ('ti6al4v','alsi10mg','ss316l','in718','in625'):
        for kind in ('pdas','sdas'):
            for bad in (0., -1., float('nan'), float('inf'), None):
                need(estimate(alloy,kind,bad,r) is None, 'invalid G admitted')
                need(estimate(alloy,kind,g,bad) is None, 'invalid R admitted')
            need(estimate(alloy,kind,g,r,cooling_side=False) is None, 'melting front admitted')
    need(estimate('ti6al4v','pdas',g,r,al=12) is None, 'negative Ti coefficient floored')
    # An actual independent interior grid must lie in an analytical monotone box.
    # This box is a numerical fixture, not a fabricated specimen uncertainty range.
    for alloy, kind, _, _ in cases:
        # At this lower-gradient fixture even the Ni secondary route is physical
        # under its explicitly transferred binary capillary screening model.
        low=estimate(alloy,kind,200,.002); high=estimate(alloy,kind,50,.0005)
        need(low is not None and high is not None,'admitted box unexpectedly refused')
        for gg in (50,70,100,130,200):
            for rr in (.0005,.0007,.001,.0013,.002):
                need(low <= estimate(alloy,kind,gg,rr) <= high, 'input sensitivity enclosure')
    for alloy in ALIASES:
        p=MORPH.PARAMS[ALIASES[alloy]]
        cutoff=MORPH.capillary_cutoff(p,1e7,.1)
        # Independent sign balance, not merely comparing a function to itself.
        drive=p.m*p.c*(1-p.k)/p.k*.1/p.d-1e7
        need(drive-p.gamma*(2*math.pi/(.9*cutoff))**2 < 0,'subcritical perturbation grew')
        need(drive-p.gamma*(2*math.pi/(1.1*cutoff))**2 > 0,'supercritical perturbation suppressed')
        for kind in ('pdas','sdas'):
            tiny=dict(coefficients)
            tiny.update(ti_pdas=(0,1e-12,.39),ti_sdas=(0,1e-12,.4),
                        al_pdas=(1e-12,.4),al_sdas=(1e-12,2/3),
                        steel_pdas=(1e-12,.33),steel_sdas=(1e-12,.28),
                        ni_sdas=(1e-12,.63),ni_hunt=1e-12,ni_kf=1e-12)
            need(estimator(alloy,kind,1e7,.1,coefficients=tiny) is None,'capillary gate bypass '+alloy+kind)
    for alloy in ('in718','in625'):
        for cooling in (1e5,1e6,1e7):
            need(estimate(alloy,'sdas',cooling/.1,.1) is None,'Mitchell nanometres admitted')
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', required=True, action='store_true')
    parser.parse_args()
    coefficients=primary_sources()
    check_reference(coefficients)
    # Mutate the ACTUAL functions used by estimate(), not unrelated expressions.
    for old,new in [('1000 * r','r'),('q ** -n','q ** n')]:
        scope=dict(globals())
        text=inspect.getsource(raw_estimate)
        need(old in text,'mutation site missing')
        exec(compile(text.replace(old,new),'raw-estimator-mutant','exec'),scope)
        exec(compile(inspect.getsource(estimate),'estimator-mutant','exec'),scope)
        try:
            check_reference(coefficients,scope['estimate'])
        except (AssertionError,TypeError):
            pass
        else:
            raise AssertionError('live estimator mutant survived: '+old)
    scope=dict(globals())
    text=inspect.getsource(estimate).replace('all(v >= cutoff for v in values)','True')
    exec(compile(text,'gate-mutant','exec'),scope)
    try:
        check_reference(coefficients,scope['estimate'])
    except AssertionError:
        pass
    else:
        raise AssertionError('live capillary-gate mutant survived')
    changed=dict(coefficients,ni_hunt=9.56e-4)
    try:
        check_reference(changed)
    except (AssertionError,TypeError):
        pass
    else:
        raise AssertionError('actual prefactor mutant survived')
    print('PASS: parsed primary coefficients drive estimate; all-five capillary gates; independent Decimal/inverse/fourth-power/sign-balance references; actual estimator unit/exponent/prefactor/gate mutants rejected. Research only, not served or physical validation.')


if __name__ == '__main__':
    main()
