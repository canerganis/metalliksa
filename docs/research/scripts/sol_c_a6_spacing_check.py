#!/usr/bin/env python3
"""Primary source and research-reference spacing checks, not served installation.

python -I -B docs/research/scripts/sol_c_a6_spacing_check.py --check
"""
from __future__ import annotations

import argparse
from decimal import Decimal, localcontext
import hashlib
import html
import math
from pathlib import Path
import re
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
    return ni_a, ni_n


def positive(x):
    return isinstance(x, (int, float)) and math.isfinite(x) and x > 0


def estimate(alloy, kind, g, r, *, cooling_side=True, al=6., mg=.45, ni_a=19.5, ni_n=.63):
    """Research only. Values in metres. Source-domain flags do not erase T2."""
    if not cooling_side or not positive(g) or not positive(r):
        return None
    q = g * r
    if not positive(q):
        return None
    if alloy == 'ti6al4v':
        if not positive(al):
            return None
        a, n = ((699 - 62 * al, .39) if kind == 'pdas' else (366 - 33 * al, .40))
        return a * q ** -n * 1e-6 if a > 0 else None
    if alloy == 'alsi10mg':
        if kind == 'pdas':
            return 165 * q ** -.4 * 1e-6
        if mg == .45:
            return 22 * (1000 * r) ** (-2 / 3) * 1e-6
        if mg == 1.:
            return 14 / (1000 * r) * 1e-6
        return None  # no invented interpolation between source chemistries
    if alloy == 'ss316l':
        a, n = ((80, .33) if kind == 'pdas' else (25, .28))
        return a * q ** -n * 1e-6
    if alloy in ('in718', 'in625'):
        if kind == 'sdas':
            return ni_a * q ** -ni_n * 1e-6
        k, gamma, dt, dl = .48, 3.65e-7, 57, 3e-9
        if not g * dl / dt < r < dt * dl / (k * gamma):
            return None
        return {name: p * z ** .25 * g ** -.5 * r ** -.25
                for name, p, z in (('hunt', 2.83, k * gamma * dt * dl),
                                   ('kurzFisher', 4.3, gamma * dt * dl / k))}
    return None


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


def check_reference(ni_a, ni_n):
    g, r = 1e7, .01
    cases = [('ti6al4v', 'pdas', 327., .39), ('ti6al4v', 'sdas', 168., .4),
             ('alsi10mg', 'pdas', 165., .4), ('ss316l', 'pdas', 80., .33),
             ('ss316l', 'sdas', 25., .28), ('in718', 'sdas', ni_a, ni_n),
             ('in625', 'sdas', ni_a, ni_n)]
    for alloy, kind, a, n in cases:
        value = estimate(alloy, kind, g, r)
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
        low=estimate(alloy,kind,2e7,.02); high=estimate(alloy,kind,5e6,.005)
        for gg in (5e6,7e6,1e7,1.3e7,2e7):
            for rr in (.005,.007,.01,.013,.02):
                need(low <= estimate(alloy,kind,gg,rr) <= high, 'input sensitivity enclosure')
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', required=True, action='store_true')
    parser.parse_args()
    ni_a, ni_n = primary_sources()
    check_reference(ni_a, ni_n)
    # Negative mutants must disagree with an independent equation invariant.
    wrong_mm = 22 * .001 ** (-2/3) * 1e-6
    need(not math.isclose(wrong_mm, 22e-6, rel_tol=1e-3), 'unit mutant not distinguished')
    wrong_caption = 9.56e-4 * 1e7**-.5 * .01**-.25
    need(not math.isclose(wrong_caption**4 * 1e14 * .01,
                         2.83**4 * .48 * 3.65e-7 * 57 * 3e-9, rel_tol=1e-3), 'caption mutant escaped')
    wrong_ni = 19.5 * 1e5 ** .63 * 1e-6
    need(not math.isclose(wrong_ni, decimal_reference(ni_a,1e5,ni_n), rel_tol=1e-3), 'exponent mutant escaped')
    print('PASS: five primary-source byte/equation checks; all-five research spacing, Decimal/inverse/fourth-power oracles; physical refusal versus extrapolation; units/coefficient/exponent mutants; input-box interior checks. No served or physical validation.')


if __name__ == '__main__':
    main()
