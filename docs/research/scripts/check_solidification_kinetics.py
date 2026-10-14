#!/usr/bin/env python3
"""Deterministic software counterexamples for the 2026-10-14 chain audit.

No experimental data, fitting, package installation or served-code mutation.
Run from any directory; JSON goes next to this script. This is a software audit,
not physical validation. All G/R/T inputs below are synthetic.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "python"))

import kinetics_ttt_cct_solver as kinetics
import lpbf_cet_screening as cet
import lpbf_solidification_microstructure as micro
import lpbf_solidification_segregation as segregation
import solidification_front as front


def outcome(fn):
    try:
        return {"returned": fn()}
    except Exception as exc:
        return {"exceptionType": type(exc).__name__, "message": str(exc)}


def main():
    source_names = (
        "kinetics_ttt_cct_solver.py", "lpbf_cet_screening.py",
        "lpbf_solidification_microstructure.py", "lpbf_solidification_segregation.py",
        "solidification_front.py", "alloy_registry.py",
    )
    cases = {}
    cases["synthetic_same_GR_different_morphology_rules"] = {
        "inputs": {"G_K_m": 1.0e6, "R_m_s": 0.1},
        "solidification_front": front.hunt_morphology(1.0e7),
        "cfd_helper": micro.hunt_morphology(1.0e6, 0.1),
        "cfd_fractions": micro.morphology_fractions(1.0e6, 0.1),
        "note": "The middle of the CFD transition gives mixed=0 despite morphology=mixed.",
    }
    cases["synthetic_positive_low_R_projection_false_floor"] = micro.project_build_job_microstructure({
        "solidificationKinetics": {
            "thermalGradient_G_K_m": 1.0e6,
            "solidificationRate_R_m_s": 5.0e-5,
            "solidificationRate_R_mm_s": 0.05,
            "coolingRate_K_s": 50.0,
            "usedFieldMap": True,
            "gradientSource": front.GRADIENT_SOURCE_CONDUCTION_INTERFACE,
        }
    })
    cases["in625_phase_note_identity"] = front.phase_transformation_note("Inconel 625", 1.0e5)
    cases["Ti64_liquidus_cooling_only_phase_note"] = front.phase_transformation_note("Ti-6Al-4V", 1.0e5)
    sets = cet.cet_constants("in718")["sets"]
    cases["CET_equation_verification_not_gate"] = [
        {"id": row["id"], "equationVerified": row["equationVerified"]} for row in sets
    ]
    consts = {name: cet.CET_SETS["in718"]["knapp2019"]["constants"][name]["value"]
              for name in ("a", "n", "N0")}
    cases["CET_nonfinite_gradient_accepted"] = cet.cet_band(math.nan, 0.1, consts)
    cases["CET_source_limits_software_reproduction"] = {
        "quantity": "Gcrit**2 / R in K**2 s / m**3 (Knapp Eq.12)",
        "columnar": cet.critical_gradient_K_m(1.0, cet.PHI_COLUMNAR, a=4.5, n=2.0, n0_m3=2.65e14) ** 2,
        "equiaxed": cet.critical_gradient_K_m(1.0, cet.PHI_EQUIAXED, a=4.5, n=2.0, n0_m3=2.65e14) ** 2,
    }
    for name in ("Ti-6Al-4V", "Inconel 718"):
        result = kinetics.solve_phase_transformation_kinetics(name, cooling_rate_c_s=1.0e5, aging_temp_c=720.0)
        cases["direct_kinetics_" + name] = {
            "kineticsModel_status": result["kineticsModel"]["status"],
            "kineticsModel_reason": result["kineticsModel"]["reason"],
            "criticalTransformationTemperatures": result["criticalTransformationTemperatures"],
            "lswFirst": result["lswPrecipitateCoarsening"][0],
            "lswLast": result["lswPrecipitateCoarsening"][-1],
            "lswNote": result["kineticsModel"]["lswPrecipitateCoarsening"]["note"],
        }
    cases["direct_kinetics_absolute_zero_aging"] = outcome(
        lambda: kinetics.solve_phase_transformation_kinetics("Ti-6Al-4V", aging_temp_c=-273.15)
    )
    for name in ("AlSi10Mg", "Inconel 625", "316L SS"):
        def resolve(n=name):
            kinetics.solve_phase_transformation_kinetics(n)
            return "model returned"
        cases["direct_kinetics_alloy_support_" + name] = outcome(resolve)
    for aid in ("ti6al4v", "alsi10mg", "ss316l"):
        cases["segregation_priority_support_" + aid] = segregation.segregation_estimate(aid)

    report = {
        "schema": "solidification-kinetics-software-audit-1",
        "evidenceKind": "Screening only",
        "moduleMaturity": "Research",
        "experimentalValidation": False,
        "scope": "synthetic counterexamples and source-form software reproduction only; no physical or blind validation",
        "revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "sourceSha256": {name: hashlib.sha256((ROOT / "python" / name).read_bytes()).hexdigest()
                         for name in source_names},
        "cases": cases,
    }
    target = Path(__file__).with_suffix(".json")
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Wrote {target.name}: {len(cases)} synthetic/software checks; not physical validation")


if __name__ == "__main__":
    main()
