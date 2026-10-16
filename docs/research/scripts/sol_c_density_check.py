"""Check primary manufacturer density rows against live served AST constants.

Run: python -I docs/research/scripts/sol_c_density_check.py --check
Reads only the five named local manufacturer PDFs and two source ASTs; no solver imports.
Missing PDFs, dependency, hash or row mismatch fails. This is provenance/arithmetic QA,
not a measurement, a high-temperature density law or validation of the thermal field.
"""
from __future__ import annotations

import argparse
import ast
from decimal import Decimal
import hashlib
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
SOURCES = {
    "ti6al4v": ("sol_c_timet_ti64_properties.pdf", 5,
                 "f9bcc879445c07259d5388598bea8b69f667d9180269b40b12dce28b57a7c507",
                 r"Density The density of TIMETAL 6-4 is 0\.160 lbs/cu\. in\. \((\d+\.\d+) gm/cc\)", "4.43"),
    "in718": ("sol_c_ati718_bar.pdf", 0,
               "234b2bc76e5f92e8d98b75f9231949236234fcf35f7c168afaceec82ad2b5855",
               r"Density: 0\.296 lbs/in3 ; (\d+\.\d+) gm/cm3", "8.19"),
    "ss316l": ("sol_c_aksteel316l.pdf", 1,
                "0b3d06f93a882e882822b18ef8aacff30ee6c3448d2ce56627a1332234f2f152",
                r"Density, 0\.29 lbs/in3 (\d+\.\d+) g/cm3", "7.99"),
    "in625": ("sol_c_smc625.pdf", 1,
               "f5379cccfe1fe760ebdc20e3f590e709e5acd1c0063d212d4ae5fd6568496d98",
               r"Density, lb/cu in[^0-9]*0\.305 gram/cc[^0-9]*(\d+\.\d+)", "8.44"),
}
ALTERNATIVE = ("sol_c_timet_ti64_datasheet.pdf", 0,
               "824684f7d5603af19e0d0862e1af1289f4ea64ae7fac7f54e649ae0f80040822",
               r"Density 72 22 0\.160 lb in-3 (\d+\.\d+) g cm-3", "4.42")


def assignment(path: Path, name: str) -> ast.AST:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    matches = [n.value for n in tree.body if isinstance(n, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == name for t in n.targets)]
    if len(matches) != 1:
        raise AssertionError(f"Expected one top-level {name} assignment in {path.name}")
    return matches[0]


def dict_item(node: ast.AST, key: str) -> ast.AST:
    if not isinstance(node, ast.Dict):
        raise AssertionError("Expected literal dictionary")
    matches = [v for k, v in zip(node.keys, node.values) if isinstance(k, ast.Constant) and k.value == key]
    if len(matches) != 1:
        raise AssertionError(f"Expected one literal key {key}")
    return matches[0]


def numeric(node: ast.AST) -> Decimal:
    value = ast.literal_eval(node)
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise AssertionError("Density must be a numeric AST literal")
    return Decimal(str(value))


def parse_density(text: str, pattern: str) -> Decimal:
    matches = re.findall(pattern, re.sub(r"\s+", " ", text))
    if len(matches) != 1:
        raise AssertionError(f"Expected exactly one density row, found {len(matches)}")
    return Decimal(matches[0])


def require_equal(source_g_cm3: Decimal, served_kg_m3: Decimal) -> None:
    # Exact SI definitions: 1 gram = 1e-3 kg; (1 cm)^3 = (1e-2 m)^3.
    converted = source_g_cm3 * Decimal("1e-3") / Decimal("1e-2") ** 3
    if converted != served_kg_m3:
        raise AssertionError(f"Source conversion {converted} differs from served {served_kg_m3}")


def must_fail(call) -> None:
    try:
        call()
    except AssertionError:
        return
    raise AssertionError("Negative mutation was not detected")


def read_row(record) -> tuple[Decimal, str]:
    from pypdf import PdfReader
    name, page, sha, pattern, expected = record
    path = ROOT / "papers" / name
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != sha:
        raise AssertionError(f"Source PDF hash changed: {name}")
    text = PdfReader(path).pages[page].extract_text()
    extracted = parse_density(text, pattern)
    if extracted != Decimal(expected):
        raise AssertionError(f"Source row changed: {name}")
    return extracted, text


def check() -> None:
    four = assignment(ROOT / "python/four_alloy_materials.py", "_THERMAL")
    ledger = assignment(ROOT / "python/four_alloy_materials.py", "PROPERTY_LEDGER")
    secondary = assignment(ROOT / "python/lpbf_thermal_solver.py", "SECONDARY_THERMOPHYSICAL_DB")
    for alloy, record in SOURCES.items():
        rho, text = read_row(record)
        material = dict_item(secondary, "Inconel 625") if alloy == "in625" else dict_item(four, alloy)
        served = numeric(dict_item(material, "density_kg_m3"))
        require_equal(rho, served)
        if alloy == "ti6al4v":
            kernel = dict_item(dict_item(ledger, alloy), "numeric")
            require_equal(rho, numeric(dict_item(kernel, "kernel_density_kg_m3")))
        must_fail(lambda: require_equal(rho, served + Decimal("1")))
        must_fail(lambda: require_equal(rho + Decimal("0.01"), served))
        # Source-row negative test changes only the captured metric cell, not the expected receipt.
        mutated = re.sub(r"\s+", " ", text)
        mutated = re.sub(record[3], lambda m: m.group(0).replace(m.group(1), "99.99"), mutated)
        must_fail(lambda: require_equal(parse_density(mutated, record[3]), served))
        print(f"PASS {alloy}: extracted {rho} g/cm3; live served AST {served} kg/m3")
    other, _ = read_row(ALTERNATIVE)
    if other == Decimal(SOURCES["ti6al4v"][4]):
        raise AssertionError("TIMET alternative must remain explicitly distinct")
    print("PASS: 5 source PDFs; 4 density bindings plus Ti64 kernel binding; 12 negative mismatches; Ti64 alternative retained")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", required=True)
    parser.parse_args()
    check()
