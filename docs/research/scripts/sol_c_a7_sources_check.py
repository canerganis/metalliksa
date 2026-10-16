"""Authenticate bounded A7 primary-source bytes and their research-model bindings.

python -I -B docs/research/scripts/sol_c_a7_sources_check.py --check
Requires pypdf and the ignored, local source files. No network or served imports.
This is transcription/authentication evidence, never experimental validation.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import importlib.util
import json
import math
from pathlib import Path
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET

from pypdf import PdfReader

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
PAPERS = ROOT / 'papers'
PINS = {
    'salsi2018.pdf': '28475f8b718348de4e95e3f346eb71c0fc32a9b54291fe0250927f53dd04342e',
    'ghosh2018.pdf': '69fd832ac49dfd5aef60a6593fbae9c9b9c78ba97a352ab17eafe927dd8b98fe',
    'azizi2020.pdf': '5f9cef2724474e0a5efcb81753a2ff532149e9d68a5b6844c7dd7f773f8c9ff6',
    'gerstgrasser2021.pdf': '2a2b051020ed9886f08c83dccf70a22af885e1a9fd654fb9d29a5eabe48f0dc9',
    'eutectic2022.pdf': '565a88453e47f2791319c8205e819a9e6f8d365b62f4a5fecefdf66035b02247',
    'yaokawa2023.pdf': '78639bf256dd4d0dc7a2abd96ff26e2d3e7a47422ffa32fd38079fcb13e3f237',
    'brooke_jats.xml': 'a48b59f54920346aa60800f7ea9ef00864d6d743e480a9f1606a98d2ab50a1ad',
    'brooke_pmc.html': 'af5cd5271ba44e1f409c5bf656c06ddbb095d8e420d4f437e5f1e7e80882856c',
}


def require(test, message):
    if not test:
        raise AssertionError(message)


def compact(text):
    text = unicodedata.normalize('NFKC', text).replace('−', '-').replace('◦', '°')
    return re.sub(r'\s+', '', text)


def capture(text, pattern):
    matches = re.findall(pattern, text)
    require(len(matches) == 1, 'bounded source row missing/ambiguous: '+pattern)
    return float(matches[0])


def scientific(text, pattern):
    matches = re.findall(pattern, text)
    require(len(matches) == 1, 'bounded scientific row missing/ambiguous: '+pattern)
    coefficient, exponent = matches[0]
    return float(coefficient)*10**int(exponent)


def page(name, number):
    return compact(PdfReader(PAPERS / ('solc_a7_'+name+'.pdf')).pages[number-1].extract_text())


def load_research_model():
    path = ROOT / 'docs/research/scripts/sol_c_a6_morph_phase_check.py'
    spec = importlib.util.spec_from_file_location('a7_source_bound_morph', path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def close(actual, expected, name):
    require(math.isclose(actual, expected, rel_tol=1e-13), 'source/runtime drift: '+name)


def math_value(node, variables):
    """Restricted MathML interpreter for the selected final RHS of Brooke Eq6."""
    tag = node.tag.rsplit('}', 1)[-1]
    children = list(node)
    if tag == 'mn':
        return float(node.text)
    if tag == 'mi':
        return variables[node.text]
    if tag == 'mfrac':
        return math_value(children[0], variables)/math_value(children[1], variables)
    if tag == 'msup':
        return math_value(children[0], variables)**math_value(children[1], variables)
    if tag in {'mrow', 'mfenced'}:
        product, divide = 1.0, False
        for child in children:
            if child.tag.rsplit('}', 1)[-1] == 'mo':
                require(child.text == '/', 'unsupported MathML operator')
                divide = True
            else:
                value = math_value(child, variables)
                product = product/value if divide else product*value
                divide = False
        require(not divide, 'incomplete MathML division')
        return product
    raise AssertionError('unsupported selected MathML tag: '+tag)


def check():
    for suffix, expected in PINS.items():
        path = PAPERS / ('solc_a7_'+suffix)
        require(path.is_file(), 'restore local primary source: '+path.name)
        require(hashlib.sha256(path.read_bytes()).hexdigest() == expected, 'source byte drift: '+path.name)
    model = load_research_model()

    # Salsi: only the equation/rate paragraph and the stated fit parameters.
    km9, km12 = page('salsi2018',9), page('salsi2018',12)
    require('(1-exp[-km(Tm-T)])β0m(19)' in km9, 'Salsi Eq19 form drift')
    ms = capture(km12,r'assumingTm=([\d.]+)°C')
    coefficient = capture(km12,r'andkm=([\d.]+)asin\[10\]')
    gate = capture(km9,r'Forcoolingratesslowerthan([\d.]+)°C/s')
    close(model.KM_MS_C,ms,'KM Ms')
    close(model.KM_COEFFICIENT,coefficient,'KM coefficient')
    close(model.KM_RATE_K_S,gate,'KM rate gate')
    transus = capture(page('salsi2018',10),r'Tβtrans=([\d.]+)°C')
    close(model.KM_TRANSUS_C,transus,'KM beta transus')
    require('martensiteormassive' in page('salsi2018',8),'Salsi martensite/massive-alpha scope')

    ti = page('ghosh2018',15).split('Thenumericalconstants')[0]
    require(ti.startswith('Table6:'),'Ghosh bounded Table6 locator')
    ti_values = {
        'c': capture(ti,r'AlloyMassFraction\(c0\)([\d.]+)%'),
        'k': capture(ti,r'EquilibriumPartitionCoefficient\(ke\)([\d.]+)'),
        'printed_m': capture(ti,r'LiquidusSlope\(ml\)(-[\d.]+)K%'),
        'freezing': capture(ti,r'EquilibriumFreezingRange\(∆T0\)([\d.]+)K'),
        'd': scientific(ti,r'LiquidDiffusionCoefficient\(Dl\)([\d.]+)×10(-?\d+)m2'),
        'gamma': scientific(ti,r'Gibbs-Thomsoncoefficient\(Γ\)([\d.]+)×10(-?\d+)Km'),
    }
    close(ti_values['printed_m'],-.088,'Ti printed slope, never silently corrected')
    close(ti_values['freezing'],50.,'Ti printed freezing range')
    for name in ('c','k','d','gamma'):
        close(getattr(model.PARAMS['ti64'],name),ti_values[name],'Ti '+name)
    closure = ti_values['freezing']*ti_values['k']/(ti_values['c']*(1-ti_values['k']))
    close(model.PARAMS['ti64'].m,closure,'Ti explicitly freezing-range-closed surrogate slope')
    require(not math.isclose(closure,abs(ti_values['printed_m']),rel_tol=.01),'Ti closure disguised as printed slope')

    al = page('azizi2020',9).split('TABLEII:')[1].split('Contactangle')[0]
    al_values = {
        'source_c': capture(al,r'Chemicalcomposition\(wt.%\)Al:99.5,Si:([\d.]+)'),
        'k': capture(al,r'Partitioncoefficient,ke([\d.]+)'),
        'm': capture(al,r'Liquidsslope\(oCwt.%\-1\)([\d.]+)'),
        'd': scientific(al,r'Solutediffusivity\(liquid;m2s-1\)([\d.]+)×10(-?\d+)'),
        'gamma': scientific(al,r'Gibbs-Thomsoncoefficient\(Km\)([\d.]+)×10(-?\d+)'),
        'nuclei': scientific(al,r'Inoculantdensity,Np\(m-3\)([\d.]+)×10(-?\d+)'),
    }
    close(al_values['source_c'],.5,'Al source composition')
    close(model.PARAMS['alsi10mg'].c,10.,'declared Al concentration transfer')
    for name in ('k','m','d','gamma','nuclei'):
        close(getattr(model.PARAMS['alsi10mg'],name),al_values[name],'Al '+name)

    steel = page('gerstgrasser2021',7).split('Table7materialparameters')[1].split('Table8')[0]
    steel_values = {
        'c': capture(steel,r'equilibriumconcentrationC0\[wt%\]([\d.]+)'),
        'k': capture(steel,r'partitioncoefficientatequilibriumke\[-\]([\d.]+)'),
        'm': abs(capture(steel,r'slopeofliquiduslinemLe\[°C/wt%\](-[\d.]+)')),
        'd': scientific(steel,r'liquiddiffusivityDL\[m2/s\]([\d.]+)⋅10(-?\d+)'),
        'gamma': scientific(steel,r'Gibbs-ThomsoncoefficientΓ\[Km\]([\d.]+)⋅10(-?\d+)'),
    }
    for name,value in steel_values.items():
        close(getattr(model.PARAMS['316l'],name),value,'316L '+name)

    eutectic = page('eutectic2022',5).split('Table1.Materialproperties')[1].split('Theexperimentalfeedstock')[0]
    ce = capture(eutectic,r'EutecticcompositionwE′\(wt.%\)([\d.]+)')
    close(ce,12.6,'Al eutectic composition')
    # ce is positional; inspect its actual Python default rather than duplicate it.
    close(model.al_constituents.__defaults__[2],ce,'eutectic runtime default')
    close(model.PARAMS['alsi10mg'].eutectic_ce,ce,'mandatory primary-tip eutectic gate')
    phases = page('yaokawa2023',9).split('4.3Concentration')[1]
    require('diamondstructureSi' in phases and 'Mg2Si' in phases and 'leverruleforthreephases' in phases,
            'Yaokawa section4.3 three-phase basis missing')
    require('Alphase' in phases,'Yaokawa aluminium phase missing')

    # Original JATS and independent PMC HTML representations must agree on the
    # complete token sequence, not just contain the desired numerical factor.
    jats = ET.parse(PAPERS/'solc_a7_brooke_jats.xml')
    equation = jats.find('.//disp-formula[@id="Equ6"]')
    require(equation is not None,'Brooke JATS Eq6 missing')
    equation_math = next(child for child in equation if child.tag.rsplit('}',1)[-1] == 'math')
    markup = (PAPERS/'solc_a7_brooke_pmc.html').read_text(encoding='utf-8')
    match = re.search(r'<table[^>]+id="Equ6">.*?(<math.*?</math>)',markup,re.S)
    require(match is not None,'Brooke PMC Eq6 missing')
    html_math = ET.fromstring(match.group(1))
    require(compact(''.join(equation_math.itertext())) == compact(''.join(html_math.itertext())),
            'Brooke JATS/HTML equation disagreement')
    equal_indices = [i for i,child in enumerate(equation_math) if child.text == '=']
    rhs = list(equation_math)[equal_indices[-1]+1:]
    require(len(rhs) == 1,'Brooke Eq6 final RHS structure drift')
    pc_jats = [compact(''.join(p.itertext())) for p in jats.findall('.//p')
               if 'where the solutal Peclet' in ''.join(p.itertext())]
    pc_html = re.search(r'<p[^>]*>where the solutal Peclet.*?</p>',markup,re.S)
    require(len(pc_jats) == 1 and pc_html is not None,'Brooke Peclet paragraph missing')
    pc_text = compact(html.unescape(re.sub('<[^>]*>','',pc_html.group(0))))
    denominator = capture(pc_jats[0],r'Pc=RV/(\d+)D')
    close(capture(pc_text,r'Pc=RV/(\d+)D'),denominator,'Brooke Peclet HTML agreement')
    for alloy,p in model.PARAMS.items():
        rate = .02
        output = model.morphology(p,1e5,rate)
        source_tip = math_value(rhs[0],dict(Q=p.m*p.c*(1-p.k),V=rate,Γ=p.gamma,D=p.d))
        close(output['tip_K'],source_tip,alloy+' Brooke Eq6 runtime')
        close(output['peclet'],rate*output['tip_radius_m']/(denominator*p.d),alloy+' Brooke Pc runtime')
    return dict(result='PASS',scope='bounded-primary-source-authentication-and-research-binding',
                pdfs_verified=6,brooke_formats_verified=['primary-JATS','PMC-HTML'],
                source_pins=PINS,ti_printed_m=ti_values['printed_m'],ti_surrogate_m=closure,
                source_alloy_transfer={'Azizi_Si_wt_pct':[al_values['source_c'],model.PARAMS['alsi10mg'].c]},
                absent_pdf_not_authenticated=['Durga/Lindwall2023','Gao2025'],
                physical_validation=False,served_channel_validated=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true',required=True)
    parser.parse_args()
    print(json.dumps(check(),sort_keys=True,allow_nan=False))
