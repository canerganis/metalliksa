#!/usr/bin/env python3
"""Replay manually verified endpoint transcriptions, not a solver or PDF extractor.

No network, imports of served physics, depth observations, or implicit writes.
Default: JSON on stdout. --output PATH writes; --check [PATH] rejects drift.
--verify-pdfs DIR optionally checks the seven named, non-blind source PDFs.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RECEIPT = Path(__file__).with_suffix(".json")
SPEC = "docs/research/SPEC_solidification_2026-10-14.md"


def source(filename, sha256, url, locator, kind):
    return dict(filename=filename, sha256=sha256, url=url, locator=locator, kind=kind,
                verification="direct source text; relevant property paragraph/table checked")


SOURCES = {
    "MP01": source("gan2021_SI.pdf", "22a8d2dc870bbd83f6bd3330899437911733f9335d52758d95a328bd6993d6e5",
                   "https://doi.org/10.1038/s41467-021-22704-0",
                   "SI PDF20 Supplementary Table1 Ti64 row; PDF23 reference13",
                   "primary-model-prescription; upstream compiled handbook, not primary measurement"),
    "MP02": source("brandt2007.pdf", "505f04de097d31d97ca92a35821233f198ac59aca8ff3ffc27c4ce9cb011d0f7",
                   "https://doi.org/10.1007/s10765-006-0144-0",
                   "PDF14/printed1442 TableII AlSi-10 heating/cooling; PDF3,5,7-8 methods",
                   "primary four-probe resistivity measurement; Al9Si0.6Mg family transfer"),
    "MP03": source("pottlacher2002.pdf", "4a200f08e598a1457e1597a254e194fd2b37e63ee7f21b8e9af2829772a5422a",
                   "https://doi.org/10.1034/j.1600-0692.2002.310301.x",
                   "PDF3/printed163 first paragraph DTA; PDF1-2 chemistry; PDF7 pulse uncertainty",
                   "primary DTA; source-batch to nominal IN718 family transfer"),
    "MP04": source("sabau2020_melt_properties_dnb.pdf", "726e52b0b58ee77bed424101d4111a0813b7bcce9de0225b346c0c2a065e7377",
                   "https://d-nb.info/1214552161/34",
                   "PDF7/printed1269 Setup of STLF Simulation Model and Material Properties, thermophysical paragraph",
                   "primary constitutive-model prescription; literature/JMatPro endpoint origin unresolved"),
    "MP05": source("solidification_pichler2020_srm316l.pdf", "ae90ec5c55b1e4145ad8f70f3b77d3656ec6cbcc83c0684bc33e4cfef57266ff",
                   "https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=928362",
                   "PDF6 Table2; PDF5 Table1 chemistry; PDF9-10 Results, evaporation caveat",
                   "primary DSC/enthalpy measurement; liquidus proxy biased by evaporation"),
    "MP06": source("cieslak1988.pdf", "3000e7b842a7cbf94357bac0acf1499f073a62a7f3d2dacc3f414b3b0d08a7ae",
                   "https://doi.org/10.1007/BF02645056",
                   "PDF2/printed2320 TableI chemistry; PDF3/printed2321 TableII, alloys5-8",
                   "primary heating DTA; deliberately varied C/Si in Alloy625 family"),
    "MP07": source("3dsystems_alsi10mg_revd.pdf", "bbdb825f1427a30bafdda1974be98f81734930535997fd3209a0f6349edb8613",
                   "https://www.3dsystems.com/sites/default/files/2023-12/3d-systems-laserform-alsi10mga-mds-letter-us-revd-web.pdf",
                   "PDF2 Thermal Properties and footnote16; 3DS-10104D|10-23",
                   "manufacturer literature-based declaration; not primary melt-point measurement"),
}

# Keep visual inspection distinct from plain-text reading; neither means validation.
for _sid in ("MP01", "MP02", "MP06", "MP07"):
    SOURCES[_sid]["verification"] += "; relevant source page/table visually checked"


def pair(ts, tl, unit):
    if unit not in ("K", "degC"):
        raise ValueError("Unsupported source unit")
    offset = 273.15 if unit == "degC" else 0.0
    if not (math.isfinite(ts) and math.isfinite(tl) and 0 < ts + offset < tl + offset):
        raise ValueError("Invalid source endpoint order")
    return {"original": {"Ts": ts, "Tl": tl, "unit": unit},
            "Ts_K": round(ts + offset, 8), "Tl_K": round(tl + offset, 8),
            "meltingInterval_K": round(tl - ts, 8)}


def record(aid, name, sid, ts, tl, unit, admission, chemistry, transfer, uncertainty):
    return dict(alloyId=aid, alloy=name, sourceId=sid, **pair(ts, tl, unit),
                admission=admission, sourceChemistry=chemistry, transfer=transfer,
                uncertainty=uncertainty, experimentalValidation=False)


def records():
    return [
        record("ti6al4v", "Ti-6Al-4V", "MP01", 1877, 1933, "K",
               "admitted-fixed-front-literature-model",
               "Named nominal Ti64; source-specific measured batch chemistry not established",
               "Nominal material-name model convention; not measured endpoints or exact specimen chemistry",
               {"type": "not-quantified", "note": "Neither endpoint measurement nor batch-transfer uncertainty quantified"}),
        record("alsi10mg", "AlSi10Mg", "MP02", 567, 599, "degC",
               "admitted-fixed-front-explicit-family-transfer",
               {"Si_wt_pct": 9.0, "Mg_wt_pct": 0.6, "balance": "Al"},
               "Heating pair, Al9Si0.6Mg -> nominal AlSi10Mg. Mg exceeds MP07 product range0.2-0.45wt%; exact-composition claim refused",
               {"type": "not-quantified", "note": "Endpoint and chemistry-transfer uncertainty unknown; conductivity6% is inapplicable",
                "cycleAlternative": pair(549, 596, "degC"), "alternativeKind": "cycle/method sensitivity, not CI"}),
        record("in718", "IN718", "MP03", 1528, 1610, "K",
               "admitted-fixed-front-explicit-family-transfer",
               {"Mo_wt_pct": 4.34, "C_wt_pct": 0.01, "Nb_wt_pct": 5.09, "Ni_wt_pct": 54.29,
                "Cr_wt_pct": 17.27, "Fe_wt_pct": 16.78, "Al_wt_pct": 0.59, "Ti_wt_pct": 0.76,
                "Co_wt_pct": 0.51, "Cu_wt_pct": 0.01, "Mn_wt_pct": 0.18, "S_wt_pct": 0.00, "Si_wt_pct": 0.18},
               "Source-batch to nominal IN718; Mo4.34 outside quoted commercial2.8-3.3wt%; C0.01 differs preset0.04",
               {"type": "not-quantified", "note": "DTA endpoint/transfer uncertainty not quantified; pulse3% is not DTA uncertainty",
                "pulseAlternative": pair(1580, 1610, "K"), "alternativeKind": "approximate fast-pulse method, not CI"}),
        record("in625", "IN625", "MP04", 1290, 1350, "degC",
               "admitted-fixed-front-literature-model",
               "Named nominal IN625; model batch chemistry not established",
               "Reproduce source fixed constitutive interval, not measured or database-assessed specimen endpoints",
               {"type": "not-quantified", "note": "Literature/JMatPro origin unresolved; no quantified model/batch uncertainty"}),
        record("ss316l", "316L", "MP05", 1675, 1708, "K",
               "not-admissible-default-liquidus; operational-proxy-only",
               {"coverage": "major elements only; certified trace chemistry in MP05 Table1 must be preserved when using this batch",
                "C_wt_pct": 0.026, "Cr_wt_pct": 17.803, "Ni_wt_pct": 12.471, "Mo_wt_pct": 2.188,
                "Mn_wt_pct": 1.593, "Si_wt_pct": 0.521, "Fe_wt_pct": 64.71},
               "Certified SRM316L batch; evaporative Mn/Cr change means Tl is not initial-material true liquidus",
               {"type": "source-expanded-measurement-uncertainty", "Ts_K": 15, "Tl_K": 30, "coverageFactor": 2,
                "note": "Applies only to measured operational temperatures; does not remove bias or bound specimen transfer"}),
    ]


def read_endpoint_literals(path, dictionary, aliases):
    """Inspect only literal endpoint AST nodes; never execute the served modules."""
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    table = next(n.value for n in tree.body if isinstance(n, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == dictionary for t in n.targets))
    out = {}
    for key, value in zip(table.keys, table.values):
        if key is None or not isinstance(key, ast.Constant) or key.value not in aliases:
            continue
        endpoints = {ast.literal_eval(k): ast.literal_eval(v) for k, v in zip(value.keys, value.values)
                     if isinstance(k, ast.Constant) and k.value in ("solidus_C", "liquidus_C")}
        out[aliases[key.value]] = pair(endpoints["solidus_C"], endpoints["liquidus_C"], "degC")
    return out


def text_sha(path):
    data = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def build():
    rows = records()
    snapshot = read_endpoint_literals("python/four_alloy_materials.py", "_THERMAL",
                                    {x: x for x in ("ti6al4v", "alsi10mg", "in718", "ss316l")})
    snapshot.update(read_endpoint_literals("python/lpbf_thermal_solver.py", "SECONDARY_THERMOPHYSICAL_DB",
                                          {"Inconel 625": "in625"}))
    expected_c = {"ti6al4v": (1604, 1660), "alsi10mg": (557, 595), "in718": (1260, 1336),
                  "in625": (1290, 1350), "ss316l": (1375, 1400)}
    for row in rows:
        aid = row["alloyId"]
        current = snapshot[aid]
        row["reviewedServedPair"] = current
        row["proposedMinusServed_K"] = {k: round(row[k] - current[k], 8) for k in ("Ts_K", "Tl_K")}
        admitted = row["admission"].startswith("admitted-")
        row["afterAdoptingAmendmentAtFirstBump"] = {
            "thermal_G_R_cooling_G_over_R": "eligible-screening-with-field-and-sample-gates" if admitted else "unavailable-default",
            "pdas": "conditional-transferred-Ni-Nb-only" if aid in ("in625", "in718") else "unavailable",
            "sdas_morphology_CET_phase_note": "unavailable-default",
            "calphadCoupling": "unavailable-until-independent-identity-reconciliation",
        }
    alternatives = {
        "IN625_MP06": [dict(sourceAlloy=f"Alloy{i}", **pair(ts, tl, "degC"),
                                repeatSD_K={"Ts": ss, "Tl": sl}, C_wt_pct=c, Si_wt_pct=si, Nb_wt_pct=nb)
                        for i, ts, tl, ss, sl, c, si, nb in
                        [(5,1308.0,1363.3,2.2,0.5,0.009,0.03,3.61),
                         (6,1289.3,1362.0,2.6,0.8,0.038,0.03,3.60),
                         (7,1287.8,1356.0,2.4,0.8,0.008,0.38,3.57),
                         (8,1275.7,1352.0,0.6,0.0,0.035,0.46,3.53)]],
        "AlSi10Mg_MP07": dict(**pair(557,596,"degC"), admission="datasheet-disclosure-only; not selected physical front"),
    }
    checks = {
        "five_unique_served_alloys": len(rows) == len({r["alloyId"] for r in rows}) == 5,
        "reviewed_served_endpoint_literals_unchanged": all(snapshot[a] == pair(*values,"degC") for a,values in expected_c.items()),
        "all_source_ids_resolve": all(r["sourceId"] in SOURCES for r in rows),
        "all_source_hashes_valid": all(len(s["sha256"]) == 64 and all(c in "0123456789abcdef" for c in s["sha256"]) for s in SOURCES.values()),
        "all_pairs_ordered": all(0 < r["Ts_K"] < r["Tl_K"] for r in rows),
        "unit_roundtrip": all(pair(r["original"]["Ts"],r["original"]["Tl"],r["original"]["unit"])["Tl_K"] == r["Tl_K"] for r in rows),
        "four_qualified_fronts_not_five_true_measurements": sum(r["admission"].startswith("admitted-") for r in rows) == 4,
        "316L_evaporation_biased_proxy_refused": rows[4]["afterAdoptingAmendmentAtFirstBump"]["thermal_G_R_cooling_G_over_R"] == "unavailable-default",
        "Al_heating_pair_not_mixed_with_cooling": (rows[1]["Ts_K"],rows[1]["Tl_K"]) == (840.15,872.15),
        "IN718_DTA_not_pulse_solidus": rows[2]["Ts_K"] == 1528,
        "Cieslak_alternatives_preserve_pairing": len(alternatives["IN625_MP06"]) == 4,
        "no_experimental_validation_claim": all(r["experimentalValidation"] is False for r in rows),
    }
    if not all(checks.values()):
        raise ValueError("Ledger checks failed: " + ", ".join(k for k,v in checks.items() if not v))
    paths = [SPEC, "python/four_alloy_materials.py", "python/lpbf_thermal_solver.py",
             "python/lpbf_material_registry.py", str(Path(__file__).relative_to(ROOT)).replace("\\","/")]
    return dict(schemaVersion=1, reviewedBaselineHead="7146e11e008e19a9601b058169030458304a3795",
                checkKind="manual source transcription and deterministic arithmetic/admission replay, not PDF extraction or physics validation",
                servedCodeModified=False, experimentalValidation=False, sources=SOURCES, alloys=rows,
                sourceAlternatives=alternatives, checks=checks,
                uncertaintyRule="Never infer transfer error/CI from method spread, family envelope or thermal/CALPHAD difference",
                couplingRule="Report both parents; same admitted chemistry/interface or separately recompute full thermal parent; never average",
                historicalIN718Gap=dict(range_K=[35,46], status="prior gate report; not reproduced here; not a tolerance or uncertainty"),
                blindAccess=dict(cleanBlindAccessCertified=False, measuredDepthsUsed=False, forbiddenPapersOpened=False,
                                 incident="Broad text searches accidentally exposed existing depth-result JSON; excluded from decisions; not a blind validation run"),
                sourceIdentityAlgorithm="sha256-utf8-lf-v1", sourceSha256={p: text_sha(ROOT/p) for p in paths})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--output", type=Path)
    action.add_argument("--check", type=Path, nargs="?", const=RECEIPT)
    parser.add_argument("--verify-pdfs", type=Path, help="Directory containing exactly named allowed source copies; no recursive scan")
    args = parser.parse_args()
    rendered = json.dumps(build(), indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    if args.verify_pdfs:
        for s in SOURCES.values():
            path = args.verify_pdfs / s["filename"]
            if hashlib.sha256(path.read_bytes()).hexdigest() != s["sha256"]:
                raise SystemExit("Source PDF hash mismatch: " + s["filename"])
    if args.check:
        if args.check.read_text(encoding="utf-8").replace("\r\n","\n") != rendered:
            raise SystemExit("Ledger receipt differs; review source/decision changes before regenerating")
        print("PASS: 12 replay checks; exact JSON receipt" + ("; 7 source PDF hashes" if args.verify_pdfs else ""))
    elif args.output:
        args.output.write_text(rendered, encoding="utf-8")
        print("Wrote " + str(args.output))
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
