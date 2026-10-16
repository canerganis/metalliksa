#!/usr/bin/env python3
"""Verify SOL-T against archived source bytes and independently extracted text.

Run: python -I docs/research/scripts/check_sol_t_sources.py --check
No network, solver execution, measured-pool rows, implicit writes or regeneration.
Requires Poppler/Xpdf pdftotext; cropped mixed pages require pypdf.
Prerequisite: restore the untracked local papers/ PDF archive from lawful copies
matching papers/INDEX.md hashes. PDFs are not distributed with this repository.
This authenticates local transcriptions, not source correctness or physical validity.
"""
from __future__ import annotations

import argparse
import ast
import copy
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[3]
RESEARCH = ROOT / "docs/research"
MANIFESTS = ("sol_t_ti_al_checks.json", "sol_t_in718_316_checks.json", "sol_t_in625_checks.json")
RECORDS = RESEARCH / "sol_t_admission_records.json"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical_hash(path):
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def page_text(path, page, crop=None):
    require(page >= 1, "PDF page must be one-based")
    if crop is not None:
        # Mixed property/validation page: never construct its full text string.
        from pypdf import PdfReader
        reader = PdfReader(path, strict=True)
        parts = []

        def visitor(text, cm, tm, font, size):
            # Affine transform into PDF bottom-left page coordinates.
            x = tm[4] * cm[0] + tm[5] * cm[2] + cm[4]
            y = tm[4] * cm[1] + tm[5] * cm[3] + cm[5]
            if crop["x_min"] < x < crop["x_max"] and crop["y_min"] < y < crop["y_max"]:
                parts.append(text)

        reader.pages[page - 1].extract_text(visitor_text=visitor)
        return " ".join(parts)
    command = shutil.which("pdftotext")
    require(command is not None, "pdftotext is required; no silent extraction skip")
    result = subprocess.run([command, "-f", str(page), "-l", str(page), "-raw", "-enc", "UTF-8", str(path), "-"],
                            capture_output=True, check=True, timeout=30)
    return result.stdout.decode("utf-8", errors="strict")


def extract_check(text, check):
    text = unicodedata.normalize("NFKC", text)
    matches = list(re.finditer(check["regex"], text, re.I | re.S))
    require(len(matches) == 1, f"{check['id']}: expected one anchored source match, found {len(matches)}")
    groups = matches[0].groupdict()
    for key, expected in check.get("expected", {}).items():
        require(key in groups and groups[key] is not None, f"{check['id']}: missing {key}")
        actual = groups[key].strip().replace("−", "-")
        try:
            equal = Decimal(actual) == Decimal(str(expected))
        except Exception:
            equal = re.sub(r"\s+", " ", actual) == re.sub(r"\s+", " ", str(expected))
        require(equal, f"{check['id']}: source {key} differs from the recorded transcription")
    if "Ts" in groups and "Tl" in groups:
        require(check["unit"] in ("K", "degC"), f"{check['id']}: unknown temperature unit")
        offset = Decimal("273.15") if check["unit"] == "degC" else Decimal(0)
        ts, tl = Decimal(groups["Ts"]), Decimal(groups["Tl"])
        require(0 < ts + offset < tl + offset, f"{check['id']}: invalid endpoint order")
        groups.update(Ts_K=str(ts + offset), Tl_K=str(tl + offset), interval_K=str(tl - ts),
                      conversion={"rule": "degC-plus-273.15" if check["unit"] == "degC" else "literal-K",
                                  "offset_K": str(offset)})
    return groups


def source_checks():
    extracted, hashes, checks = {}, {}, {}
    for manifest in MANIFESTS:
        data = json.loads((RESEARCH / manifest).read_text(encoding="utf-8-sig"))
        sources = data if isinstance(data, list) else data["sources"]
        for source in sources:
            path = (ROOT / source["path"]).resolve()
            require(path.is_relative_to((ROOT / "papers").resolve()), "Only archived papers/ sources allowed")
            require(path.suffix.lower() == ".pdf", "Only PDF source inputs allowed")
            require(path.is_file(), f"Local archive prerequisite missing: {source['path']}; restore lawful bytes matching papers/INDEX.md")
            require(not re.search(r"leis2021|hyer2020|aboulkhair2016|ruckh2025|gong2014|ullah|wimmer2020", path.name, re.I),
                    "Forbidden source")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            require(digest == source["sha256"], f"{source['id']}: archived PDF bytes changed")
            hashes[source["id"]] = digest
            for check in source["checks"]:
                require(check["id"] not in extracted, f"Duplicate check ID {check['id']}")
                text = unicodedata.normalize("NFKC", page_text(path, check["page"], check.get("crop")))
                extracted[check["id"]] = {**extract_check(text, check),
                                           "_sourceId": source["id"], "_unit": check.get("unit")}
                checks[check["id"]] = (text, check)
    return extracted, hashes, checks


def literal_table(path, name):
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    assignment = next(n for n in tree.body if isinstance(n, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == name for t in n.targets))
    return ast.literal_eval(assignment.value)


def numeric_constant(path, name):
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    node = next(n.value for n in tree.body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == name for t in n.targets))
    return Decimal(str(ast.literal_eval(node)))


def validate_records(data, extracted, hashes):
    require(data["schema"] == "sol-t-amendment-4-v1", "Wrong admission schema")
    require(data["installed"] is False, "Documentation must not claim installation")
    fields = {"id", "sourceCheck", "admissionClass", "sourceChemistry", "chemistryMatch", "transfer", "uncertainty",
              "solidusDefinition", "liquidusDefinition", "method", "rate", "cycle", "direction", "pairingStatus",
              "scope", "refusedScope", "sourceId", "parentIdentity", "endpoint_K", "original", "decision", "conversion"}
    records = data["records"]
    require({r["id"] for r in records} == {"ti6al4v", "alsi10mg", "in718", "ss316l", "in625"}, "Five-alloy coverage")
    require(len(records) == 5, "Duplicate alloy")
    pattern_pairs = [("knapp718-pair", "smc718-celsius-pair"),
                     ("gan316-pair", "mills316-adopted-pair"),
                     ("gan625-paired-inputs", "sabau2020-paired-prescription")]
    require(data["conversionPatternChecks"] == [list(pair) for pair in pattern_pairs], "Conversion pattern evidence coverage")
    for kelvin, celsius in pattern_pairs:
        k, c = extracted[kelvin], extracted[celsius]
        require(k["_unit"] == "K" and c["_unit"] == "degC" and
                all(Decimal(c[key]) - Decimal(k[key]) == Decimal("0.15") for key in ("Ts_K", "Tl_K")),
                "Compiled integer-273 cross-check pattern changed")
    baseline = literal_table("python/four_alloy_materials.py", "_THERMAL")
    for r in records:
        require(fields <= r.keys(), f"{r['id']}: incomplete A2.1/RT6 record")
        for field in fields - {"endpoint_K", "original", "parentIdentity", "sourceChemistry", "uncertainty", "conversion"}:
            require(isinstance(r[field], str) and r[field].strip(), f"{r['id']}: empty/nontext {field}")
        require(r["decision"] == "admit-nominal-research-convention", "Unexpected admission policy")
        require(r["chemistryMatch"] == "not-established", "No source establishes specimen chemistry match")
        require(r["sourceId"] in hashes, f"{r['id']}: unknown source hash")
        actual = extracted[r["sourceCheck"]]
        require(actual["_sourceId"] == r["sourceId"], f"{r['id']}: source/check ownership mismatch")
        require(actual["_unit"] == r["original"]["unit"], f"{r['id']}: original temperature-unit label mismatch")
        conversion = r["conversion"]
        require(conversion.get("sameLineageKChecks") == {"ti6al4v": [], "alsi10mg": [],
                "in718": ["knapp718-pair"], "ss316l": ["gan316-pair"],
                "in625": ["gan625-paired-inputs"]}[r["id"]], "Same-lineage rendering disclosure coverage")
        if r["id"] == "ti6al4v":
            require(conversion["rule"] == "compiled-K-integer-273-interpretation" and
                    Decimal(str(conversion["offset_K"])) == Decimal("0.15"), "Ti conversion must disclose interpretation")
            require(conversion["interpretation"].strip(), "Missing Ti interpretation disclosure")
            require([Decimal(actual[k]) - Decimal(273) for k in ("Ts", "Tl")] ==
                    list(map(lambda v: Decimal(str(v)), conversion["interpreted_C"])), "Ti inferred Celsius pair")
            endpoint = [Decimal(actual[k]) + Decimal("0.15") for k in ("Ts_K", "Tl_K")]
        else:
            require(conversion["rule"] == actual["conversion"]["rule"] and
                    Decimal(str(conversion["offset_K"])) == Decimal(actual["conversion"]["offset_K"]),
                    f"{r['id']}: recorded conversion differs from extracted units")
            endpoint = [Decimal(actual[k]) for k in ("Ts_K", "Tl_K")]
        require(endpoint == [Decimal(str(v)) for v in r["endpoint_K"]],
                f"{r['id']}: proposed endpoints differ from disclosed source conversion")
        for rendering in conversion.get("sameLineageKChecks", []):
            other = extracted[rendering]
            require(other["_unit"] == "K" and all(endpoint[i] - Decimal(other[k]) == Decimal("0.15")
                    for i, k in enumerate(("Ts_K", "Tl_K"))), f"{r['id']}: integer-273 rendering mismatch")
        require([Decimal(actual[k]) for k in ("Ts", "Tl")] == [Decimal(str(v)) for v in r["original"]["values"]],
                f"{r['id']}: original units/numbers drifted")
        require(r["parentIdentity"]["sourceSha256"] == hashes[r["sourceId"]], f"{r['id']}: parent hash")
        require(r["parentIdentity"]["recordId"] == f"SOL-T-A4-{r['id']}", "Parent record ID")
        require(r["parentIdentity"]["endpoint_K"] == r["endpoint_K"], "Parent endpoint identity")
        require(r["parentIdentity"]["conversion"] == conversion, "Parent conversion identity")
        require(r["uncertainty"]["type"] == "not-quantified", "No invented convention/transfer CI")
        if r["id"] != "in625":
            old = baseline[r["id"]]
            for k, scalar in zip(("solidus_C", "liquidus_C"), r["baseline_C"]):
                require(Decimal(str(old[k])) == Decimal(str(scalar)), f"{r['id']}: live baseline changed")
        else:
            for name, scalar in zip(("IN625_SOLIDUS_K", "IN625_LIQUIDUS_K"), r["baseline_C"]):
                actual_k = numeric_constant("python/in625_thermal_material.py", name)
                require(actual_k == Decimal(str(scalar)) + Decimal("273.15"), "IN625 baseline authority mismatch")
        for i in range(2):
            old_k = Decimal(str(r["baseline_C"][i])) + Decimal("273.15")
            require(Decimal(str(r["delta_K"][i])) == Decimal(str(r["endpoint_K"][i])) - old_k,
                    f"{r['id']}: moved endpoint arithmetic")
    for binding in data["sourceCodeBindings"]:
        require(canonical_hash(ROOT / binding["path"]) == binding["canonicalSha256"], f"{binding['path']}: source changed")
    require((ROOT / "python/lpbf_implementation_fingerprint.expected").read_text().strip() == data["servedPin"], "Served pin changed")


def negative_controls(data, extracted, hashes, checks):
    rejected = 0
    for mutation in ("value", "hash", "missing-field", "unit", "cycle", "transfer", "source-reassignment", "empty-cycle", "conversion", "missing-conversion"):
        mutant = copy.deepcopy(data)
        record = mutant["records"][0]
        if mutation == "value": record["endpoint_K"][0] += 1
        if mutation == "hash": record["parentIdentity"]["sourceSha256"] = "0" * 64
        if mutation == "missing-field": del record["solidusDefinition"]
        if mutation == "unit": record["original"]["unit"] = "degC"
        if mutation == "cycle": record["chemistryMatch"] = "established"
        if mutation == "transfer": record["uncertainty"]["type"] = "confidence-interval"
        if mutation == "source-reassignment":
            record["sourceId"] = "MP04"
            record["parentIdentity"]["sourceSha256"] = hashes["MP04"]
        if mutation == "empty-cycle": record["cycle"] = ""
        if mutation == "conversion": record["conversion"]["offset_K"] = 0
        if mutation == "missing-conversion": del record["conversion"]
        try:
            validate_records(mutant, extracted, hashes)
        except ValueError:
            rejected += 1
        else:
            raise ValueError(f"Undetected record mutation: {mutation}")
    # Change the extracted source itself, not the expected record: proves checks are source-sensitive.
    for check_id, (text, check) in checks.items():
        match = re.search(check["regex"], text, re.I | re.S)
        if check.get("expected"):
            group = next(iter(check["expected"]))
            lo, hi = match.span(group)
        else:
            lo, hi = match.span()
        mutant_text = text[:lo] + "SOURCE_MUTATED" + text[hi:]
        try:
            extract_check(mutant_text, check)
        except ValueError:
            rejected += 1
        else:
            raise ValueError(f"Undetected source mutation: {check_id}")
    return rejected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", required=True)
    parser.parse_args()
    extracted, hashes, checks = source_checks()
    data = json.loads(RECORDS.read_text(encoding="utf-8"))
    validate_records(data, extracted, hashes)
    rejected = negative_controls(data, extracted, hashes, checks)
    print(f"PASS: {len(hashes)} source identities, {len(checks)} PDF assertions, 5 admissions, {rejected} negative controls")
    print("Scope: source transcription + unit/identity/metadata checks; no physical validation or installation claim")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, subprocess.SubprocessError, ImportError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
