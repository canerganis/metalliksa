#!/usr/bin/env python3
"""SOL-C spacing source/producer check; no measured pool data or solver run.

python -I docs/research/scripts/sol_c_spacing_check.py --check
Requires the local-only primary PDF recorded in sol_c_spacing_sources.md and pypdf.
Missing/changed source fails; no receipt regeneration or network fallback.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import html
import math
from pathlib import Path
import re
import sys
import types
import unicodedata

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
PDF = ROOT / "papers/ghosh2017_solc_spacing.pdf"
SHA256 = "446c2a8e16af32377d070d81a5ccf71e6059a58f3b38481951ecafd36463a5dd"


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def compact(text):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", text)).replace("−", "-")


def source_parameters(table):
    text = compact(table)
    patterns = {
        "k": r"EquilibriumPartitionCoefficient,ke([0-9.]+)",
        "dt": r"EquilibriumFreezingRange,∆T0=Tl-Ts([0-9.]+)K",
        "dl": r"LiquidDiffusionCoefficient,Dl([0-9.]+)×10(-?[0-9]+)m2s-1",
        "gamma": r"Gibbs-Thomsoncoefficient,Γ([0-9.]+)×10(-?[0-9]+)Km",
    }
    out = {}
    for name, pattern in patterns.items():
        match = re.search(pattern, text)
        require(match is not None, "unmatched primary Table 2 row: " + name)
        out[name] = float(match[1] + "e" + match[2]) if len(match.groups()) == 2 else float(match[1])
    return out


def law_check(front, params, prefactors):
    """Fourth-power dimensional identity, independent of producer power sequence."""
    for alloy in ("in718", "in625"):
        for speed in (.005, .01, .03, .1, .3):
            gradient = 1e7
            result = front.pdas_band_um(gradient, speed, alloy)
            require(result["pdasBand_um"] is not None, "source-line sample refused")
            for model, prefix in prefactors.items():
                spacing = result["pdasBand_um"][model] * 1e-6
                left = spacing ** 4 * gradient ** 2 * speed
                right = prefix ** 4 * params["gamma"] * params["dt"] * params["dl"]
                right *= params["k"] if model == "hunt" else 1.0 / params["k"]
                require(math.isclose(left, right, rel_tol=1e-12), model + " fourth-power identity failed")


def extract_actual_producer():
    """Compile production AST bodies/constants only; execute no repository imports."""
    functions = {"_finite_positive", "pdas_on_source_line", "pdas_vcs_m_s", "pdas_above_vcs",
                 "pdas_below_vab", "_reason", "pdas_band_um"}
    constants = {"CANONICAL_ALLOY_IDS", "MODEL_ID", "GHOSH2017_SOURCE", "PDAS_A_HUNT_SI",
                 "PDAS_A_KURZ_FISHER_SI", "PDAS_SOURCE_K_E", "PDAS_SOURCE_GAMMA_K_M",
                 "PDAS_SOURCE_DELTA_T0_K", "PDAS_SOURCE_D_L_M2_S", "PDAS_SOURCE_LINE_G_K_M",
                 "PDAS_LINE_RELATIVE_TOLERANCE", "PDAS_VAB_M_S", "PDAS_X_RANGE",
                 "PDAS_COOLING_RANGE_K_S", "PDAS_ALLOY_IDS"}
    path = ROOT / "python/solidification_front.py"
    nodes, found_functions, found_constants = [], set(), set()
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.FunctionDef) and node.name in functions:
            nodes.append(node)
            found_functions.add(node.name)
        elif isinstance(node, ast.Assign):
            targets = {target.id for target in node.targets if isinstance(target, ast.Name)}
            if targets & constants:
                require(targets <= constants, "mixed assignment crossed AST extraction boundary")
                ast.literal_eval(node.value)  # Refuse executable/nonliteral initializers.
                nodes.append(node)
                found_constants.update(targets)
    require(found_functions == functions and found_constants == constants, "production AST inventory changed")
    future = ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)
    module = ast.Module(body=[future] + nodes, type_ignores=[])
    front = types.ModuleType("sol_c_actual_spacing_ast")
    front.__dict__["math"] = math
    exec(compile(ast.fix_missing_locations(module), str(path), "exec"), front.__dict__)
    return front


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", required=True)
    parser.parse_args()
    from pypdf import PdfReader

    require(PDF.is_file(), "missing local primary PDF: " + str(PDF))
    require(hashlib.sha256(PDF.read_bytes()).hexdigest() == SHA256, "primary PDF hash changed")
    pages = PdfReader(PDF).pages
    params = source_parameters(pages[7].extract_text())
    require(params == {"k": .48, "dt": 57., "dl": 3e-9, "gamma": 3.65e-7}, "primary Table 2 transcription drift")
    eq7, eq8 = compact(pages[11].extract_text()), compact(pages[12].extract_text())
    m7 = re.search(r"PDAS=([0-9.]+)\(keΓ∆T0Dl\)0\.25G-0\.5V-0\.25,\(7\)", eq7)
    m8 = re.search(r"PDAS=([0-9.]+)\(Γ∆T0Dl/ke\)0\.25G-0\.5V-0\.25\.\(8\)", eq8)
    require(m7 is not None and m8 is not None, "source equation structure changed")
    prefixes = {"hunt": float(m7[1]), "kurzFisher": float(m8[1])}
    require(prefixes == {"hunt": 2.83, "kurzFisher": 4.3}, "source prefactor transcription drift")
    section31 = compact(pages[8].extract_text())
    require("fixedvalueofG=107Km-1" in section31, "source fixed-G declaration missing")
    require(all(token in compact(pages[13].extract_text()) for token in ("0.0004", "0.0012", "Figure6")), "source Fig 6 range locator missing")
    cooling = re.search(r"operatingcoolingrates.*?between([0-9]+)×10([0-9]+)Ks-1to([0-9]+)×10([0-9]+)Ks-1", eq7)
    require(cooling is not None, "source operating cooling-rate interval missing")
    cooling_range = (float(cooling[1] + "e" + cooling[2]), float(cooling[3] + "e" + cooling[4]))
    require("Vab=∆T0Dl/(keΓ)" in section31, "source absolute-stability formula missing")
    # This archive prints a coarse 1 m/s on PDF10. SPEC's approximately 0.98
    # is the two-decimal evaluation of that formula, not a verbatim printed value.
    vab = round(params["dt"] * params["dl"] / (params["k"] * params["gamma"]), 2)
    ti_html = ROOT / "papers/mizukami2020_solc_spacing.html"
    require(ti_html.is_file(), "missing local documentary Ti source")
    require(hashlib.sha256(ti_html.read_bytes()).hexdigest() == "aa03cefa2f447d68b266bfec4f9787b53854d6590f9633d77d1c1eb0033fdd51", "Ti source hash changed")
    ti_text = compact(html.unescape(re.sub(r"<[^>]+>", "", ti_html.read_text(encoding="utf-8"))))
    require("λ1=(-62CAl+699)T⋅-0.39" in ti_text, "Ti documentary Eq 4 transcription drift")
    require("λ2=(-33CAl+366)T⋅-0.40" in ti_text, "Ti documentary Eq 5 transcription drift")

    front = extract_actual_producer()
    bindings = {"PDAS_SOURCE_K_E": params["k"], "PDAS_SOURCE_GAMMA_K_M": params["gamma"],
                "PDAS_SOURCE_DELTA_T0_K": params["dt"], "PDAS_SOURCE_D_L_M2_S": params["dl"],
                "PDAS_SOURCE_LINE_G_K_M": 1e7, "PDAS_X_RANGE": (4e-4, 1.2e-3),
                "PDAS_COOLING_RANGE_K_S": cooling_range, "PDAS_VAB_M_S": vab,
                "PDAS_LINE_RELATIVE_TOLERANCE": 1e-12}
    for name, expected in bindings.items():
        require(getattr(front, name) == expected, "production/source binding drift: " + name)
    require(front.PDAS_A_HUNT_SI == 1.1773863284676703e-3, "noncanonical Hunt precision")
    require(front.PDAS_A_KURZ_FISHER_SI == 2.5821435943712695e-3, "noncanonical KF precision")
    law_check(front, params, prefixes)
    for alloy in ("ti6al4v", "alsi10mg", "ss316l"):
        result = front.pdas_band_um(1e7, .01, alloy)
        require(result["pdasBand_um"] is None and result["reasons"][0]["code"] == "missing-source-bound-model", "unsupported alloy admitted")
    for gradient, speed in ((2e7, .01), (5e7, .0012), (1e6, 1.5), (1e7, .004), (1e7, .31), (1e7, 0), (1e7, float("nan"))):
        require(front.pdas_band_um(gradient, speed, "in718")["pdasBand_um"] is None, "invalid/domain sample admitted")
    require(not front.pdas_on_source_line(2e7), "off-line predicate lost")
    require(not front.pdas_above_vcs(5e7, .0012), "planar-side predicate lost")
    require(not front.pdas_below_vab(1.5), "absolute-stability predicate lost")

    # Mutate only the AST-extracted in-memory constant. The independent source identity
    # must detect wrong runtime arithmetic; no repository file is changed.
    original = front.PDAS_A_HUNT_SI
    front.PDAS_A_HUNT_SI = 9.56e-4
    try:
        law_check(front, params, prefixes)
    except AssertionError:
        pass
    else:
        raise AssertionError("caption coefficient mutant escaped source identity")
    finally:
        front.PDAS_A_HUNT_SI = original
    print("PASS: primary Ni PDF rows/equations, documentary Ti equations, actual PDAS producer fourth-power identity, all-five/domain refusal, coefficient mutant; physical validation NOT performed")


if __name__ == "__main__":
    main()
