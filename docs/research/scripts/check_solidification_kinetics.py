#!/usr/bin/env python3
"""Deterministic software counterexamples for the 2026-10-14 chain audit.

No experimental data, fitting, package installation or served-code mutation.
Run from any directory; default JSON goes to stdout, --output explicitly writes. This is a software audit,
not physical validation. All G/R/T inputs below are synthetic.
python -I -B docs/research/scripts/check_solidification_kinetics.py --check
The standalone future gate --require-served-coefficients rejects the current
legacy served constants until SOL-A1 installs the canonical coefficients.
"""
from __future__ import annotations

import argparse
import ast
import copy
import json
import math
from pathlib import Path
import sys
sys.dont_write_bytecode = True
# -I deliberately excludes the script directory; admit this resolved sibling only.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _solidification_check_common import emit, require

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "python"))

import kinetics_ttt_cct_solver as kinetics
import lpbf_cet_screening as cet
import lpbf_solidification_microstructure as micro
import lpbf_solidification_segregation as segregation
import solidification_front as front

HUNT_A_CANONICAL_SI = 1.1773863284676703e-3
KURZ_FISHER_A_CANONICAL_SI = 2.5821435943712695e-3


def coefficient_binding(tree):
    """Gate 4 binds actual served assignments AND their use in the PDAS producer.

    This narrow coefficient check does not admit any alloy or field sample. Copies
    of the served AST are exercised in memory only; no model/pin is changed.
    """
    names = {"PDAS_A_HUNT_SI": HUNT_A_CANONICAL_SI,
             "PDAS_A_KURZ_FISHER_SI": KURZ_FISHER_A_CANONICAL_SI}
    encoded = {target.id: ast.literal_eval(node.value)
               for node in tree.body if isinstance(node, ast.Assign)
               for target in node.targets if isinstance(target, ast.Name) and target.id in names}
    scope = {"__name__": "synthetic_coefficient_binding_probe"}
    exec(compile(tree, "<served-front-in-memory-probe>", "exec"), scope)
    gradient, rate = 1e7, .01
    x = gradient ** -.5 * rate ** -.25
    band = scope["pdas_band_um"](gradient, rate, "in718")["pdasBand_um"]
    return {"encodedConstants": encoded, "probeG_K_m": gradient, "probeR_m_s": rate,
            "probeBand_um": band,
            "accepted": all(encoded.get(name) == expected
                            and scope[name] == expected
                            for name, expected in names.items())
                        and band is not None
                        and math.isclose(band["hunt"], HUNT_A_CANONICAL_SI*x*1e6, rel_tol=1e-12)
                        and math.isclose(band["kurzFisher"], KURZ_FISHER_A_CANONICAL_SI*x*1e6, rel_tol=1e-12)}


def coefficient_gate_examples():
    tree = ast.parse((ROOT / "python/solidification_front.py").read_text(encoding="utf-8"))
    def substituted(hunt, kurz_fisher):
        mutated = copy.deepcopy(tree)
        for node in mutated.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in {"PDAS_A_HUNT_SI", "PDAS_A_KURZ_FISHER_SI"}:
                        node.value = ast.copy_location(ast.Constant(hunt if target.id == "PDAS_A_HUNT_SI" else kurz_fisher), node.value)
        return coefficient_binding(ast.fix_missing_locations(mutated))
    return {"currentServed": coefficient_binding(tree),
            "canonicalInMemoryControl": substituted(HUNT_A_CANONICAL_SI, KURZ_FISHER_A_CANONICAL_SI),
            "wrongHuntMutant": substituted(HUNT_A_CANONICAL_SI*1.01, KURZ_FISHER_A_CANONICAL_SI),
            "nonCanonicalPrecisionMutant": substituted(HUNT_A_CANONICAL_SI*(1+1e-13), KURZ_FISHER_A_CANONICAL_SI),
            "roundedCaptionKFMutant": substituted(HUNT_A_CANONICAL_SI, 2.6e-3),
            "scope": "Future SOL-A1 coefficient acceptance only; current served rejection is an expected unresolved defect. In-memory substitutions do not alter served source, model or fingerprint, and do not admit physical samples."}


def require_served_coefficients():
    parser = argparse.ArgumentParser(description="Standalone future gate 4: actual served coefficient acceptance")
    parser.add_argument("--require-served-coefficients", action="store_true", required=True)
    parser.parse_args()
    cases = coefficient_gate_examples()
    checks = {
        "independentHuntEquation": math.isclose(2.83*(.48*3.65e-7*57*3e-9)**.25, HUNT_A_CANONICAL_SI, rel_tol=1e-12),
        "independentKurzFisherEquation": math.isclose(4.3*(3.65e-7*57*3e-9/.48)**.25, KURZ_FISHER_A_CANONICAL_SI, rel_tol=1e-12),
        "actualServedAssignmentsAndProducer": cases["currentServed"]["accepted"],
        "canonicalInMemoryControl": cases["canonicalInMemoryControl"]["accepted"],
        "wrongHuntMutantRejected": not cases["wrongHuntMutant"]["accepted"],
        "nonCanonicalPrecisionMutantRejected": not cases["nonCanonicalPrecisionMutant"]["accepted"],
        "captionKFMutantRejected": not cases["roundedCaptionKFMutant"]["accepted"],
    }
    print(json.dumps({"gate": "future-SOL-A1-served-coefficients", "checks": checks,
                      "actualServedConstants": cases["currentServed"]["encodedConstants"],
                      "physicalValidation": False}, sort_keys=True))
    if not all(checks.values()):
        raise SystemExit("FAIL: served coefficients do not meet gate 4; canonical installation remains pending SOL-A1")


def outcome(fn):
    try:
        return {"returned": fn()}
    except Exception as exc:
        return {"exceptionType": type(exc).__name__, "message": str(exc)}


def main():
    if "--require-served-coefficients" in sys.argv[1:]:
        require_served_coefficients()
        return
    source_names = (
        "kinetics_ttt_cct_solver.py", "lpbf_cet_screening.py",
        "lpbf_solidification_microstructure.py", "lpbf_solidification_segregation.py",
        "solidification_front.py", "alloy_registry.py",
        "alloy_data_kinetics_uq_fatigue.py", "alloy_data_calphad_battery_icme.py",
        "four_alloy_materials.py", "physical_constants.py", "hardness_conversion_e140.py", "input_validation.py",
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
            "solidificationRate_R_m_s": 0.0,
            "solidificationRate_R_mm_s": 0.1,
            "coolingRate_K_s": 100.0,
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
        "columnar": cet.critical_gradient_K_m(1.0, cet.PHI_COLUMNAR, a=consts["a"], n=consts["n"], n0_m3=consts["N0"]) ** 2,
        "equiaxed": cet.critical_gradient_K_m(1.0, cet.PHI_EQUIAXED, a=consts["a"], n=consts["n"], n0_m3=consts["N0"]) ** 2,
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

    # Predeclared primary-form arithmetic independent of served constants/coefficient.
    hunt_oracle = 2.83 * (0.48 * 3.65e-7 * 57.0 * 3e-9) ** 0.25
    kurz_fisher_oracle = 4.3 * (3.65e-7 * 57.0 * 3e-9 / 0.48) ** 0.25
    coefficient_cases = coefficient_gate_examples()
    cases["gate4ServedCoefficientBinding"] = coefficient_cases
    col = cases["CET_source_limits_software_reproduction"]["columnar"]
    eq = cases["CET_source_limits_software_reproduction"]["equiaxed"]
    checks = {
        "HuntEquationArithmeticExpectedValue": math.isclose(hunt_oracle, HUNT_A_CANONICAL_SI, rel_tol=1e-12),
        "KurzFisherEquationArithmeticExpectedValue": math.isclose(kurz_fisher_oracle, KURZ_FISHER_A_CANONICAL_SI, rel_tol=1e-12),
        "gate4CurrentServedCoefficientsRejectedPendingSOL_A1": coefficient_cases["currentServed"]["accepted"] is False,
        "gate4CanonicalServedASTControlAccepted": coefficient_cases["canonicalInMemoryControl"]["accepted"],
        "gate4WrongServedHuntMutantRejected": coefficient_cases["wrongHuntMutant"]["accepted"] is False,
        "gate4NonCanonicalPrecisionMutantRejected": coefficient_cases["nonCanonicalPrecisionMutant"]["accepted"] is False,
        "gate4RoundedCaptionKFMutantRejected": coefficient_cases["roundedCaptionKFMutant"]["accepted"] is False,
        "KnappPrintedColumnarWithin2Percent": abs(col/1.52e11-1) <= .02,
        "KnappPrintedEquiaxedWithin2Percent": abs(eq/6.98e9-1) <= .02,
        "HuntArithmeticWithinRoundedSource3PerMille":abs(hunt_oracle/1.18e-3-1)<=.003,
        "servedHuntCoefficientMismatchReproduced":abs(front.PDAS_A_HUNT_SI/hunt_oracle-1)>.18,
        "sameGRMorphologyDisagreement":cases["synthetic_same_GR_different_morphology_rules"]["solidification_front"] != cases["synthetic_same_GR_different_morphology_rules"]["cfd_helper"],
        "zeroMixedFractionReproduced":cases["synthetic_same_GR_different_morphology_rules"]["cfd_fractions"]["mixed"]==0,
        "positiveLowRateObsoleteFloor":cases["synthetic_positive_low_R_projection_false_floor"]["status"]=="degenerate-floor",
        "in625MisclassifiedAsIN718":cases["in625_phase_note_identity"]["alloyClass"]=="IN718",
        "Ti64LiquidusSwitchReproduced":cases["Ti64_liquidus_cooling_only_phase_note"]["expected"]=="beta_to_alpha_prime_martensite",
        "unverifiedCETStillListed":any(not row["equationVerified"] for row in cases["CET_equation_verification_not_gate"]),
        "absoluteZeroExplicitException":cases["direct_kinetics_absolute_zero_aging"].get("exceptionType")=="ZeroDivisionError",
    }
    for name in ("Ti-6Al-4V", "Inconel 718"):
        row=cases["direct_kinetics_"+name]
        checks["unsupportedLSW_"+name]=row["kineticsModel_status"]=="unavailable" and row["lswLast"]["meanRadius_nm"]>0 and row["lswLast"]["precipitationHardening_MPa"]>0
    for name in ("AlSi10Mg", "Inconel 625", "316L SS"):
        checks["unsupportedAlloyExplicitException_"+name]=cases["direct_kinetics_alloy_support_"+name].get("exceptionType")=="ValidationError"
    for aid in ("ti6al4v", "alsi10mg", "ss316l"):
        checks["segregationNotApplicable_"+aid]=cases["segregation_priority_support_"+aid]["status"]=="not-applicable"
    checks["printedKnappConstantsRetained"]=consts=={"a":4.5,"n":2.,"N0":2.65e14}
    checks["nonpositiveCETGradientAccepted"] = cet.cet_band(0.0,.1,consts)["band"]=="equiaxed" and cet.cet_band(-1.0,.1,consts)["band"]=="equiaxed"
    checks["nonfiniteCETGradientAccepted"] = cases["CET_nonfinite_gradient_accepted"]["band"]=="mixed" and cet.cet_band(math.inf,.1,consts)["band"]=="columnar"
    cases["independentHuntArithmetic"]={"formula":"2.83*(k_e*Gamma*DeltaT0*D_l)^0.25", "inputs":{"k_e":.48,"Gamma_K_m":3.65e-7,"DeltaT0_K":57,"D_l_m2_s":3e-9},"expected_A_SI":hunt_oracle,"served_A_SI":front.PDAS_A_HUNT_SI,"roundedSource_A_SI":1.18e-3,"roundedRelativeTolerance":.003}
    cases["independentKurzFisherArithmetic"] = {
        "formula": "4.3*(Gamma*DeltaT0*D_l/k_e)^0.25", "sourceLocator": "S04 Eq.8/Table2; Fig.6 caption rounded alternative",
        "inputs": {"k_e": .48, "Gamma_K_m": 3.65e-7, "DeltaT0_K": 57, "D_l_m2_s": 3e-9},
        "expected_A_SI": kurz_fisher_oracle, "canonical_A_SI": KURZ_FISHER_A_CANONICAL_SI,
        "display_A_SI": 2.5821e-3, "caption_A_SI": 2.6e-3,
        "captionRelativeDifferenceFromEquation": 2.6e-3/kurz_fisher_oracle-1,
        "served_A_SI": front.PDAS_A_KURZ_FISHER_SI,
        "decision": "Use full Eq.8 value in future SOL-A1 arithmetic; shorter representations are display only. Current served rounded caption value remains unchanged in this documentary check work."}
    cases["CET_source_limits_software_reproduction"].update(printedColumnar=1.52e11,printedEquiaxed=6.98e9,relativeTolerance=.02)
    stability_cases = []
    for gradient, rate in ((5e7, 1.2e-3), (1e6, 1.5)):
        vcs = gradient * 3e-9 / 57.0
        vab = 57.0 * 3e-9 / (0.48 * 3.65e-7)
        served = front.pdas_band_um(gradient, rate, "in718")
        stability_cases.append({
            "G_K_m": gradient, "R_m_s": rate, "Vcs_m_s": vcs, "Vab_m_s": vab,
            "sourceStableCellularRange": vcs < rate < vab,
            "fixedSourceGradient": math.isclose(gradient, 1e7, rel_tol=1e-12),
            "served": served,
        })
    cases["PDAS_sourceStabilityCounterexamples"] = stability_cases
    checks["PDAS_planarSideStillServed"] = not stability_cases[0]["sourceStableCellularRange"] and stability_cases[0]["served"]["pdasOutOfRange"] is False and stability_cases[0]["served"]["pdasBand_um"] is not None
    checks["PDAS_absoluteStabilitySideStillServed"] = not stability_cases[1]["sourceStableCellularRange"] and stability_cases[1]["served"]["pdasOutOfRange"] is False and stability_cases[1]["served"]["pdasBand_um"] is not None
    require(checks)
    report = {
        "schema": "solidification-kinetics-software-audit-2",
        "baselinePolicy":"Expected-defect assertions against served source, not future implementation acceptance.",
        "experimentalValidation": False,
        "scope": "synthetic counterexamples and source-form software reproduction only; no physical or blind validation",
        "checks": checks,
        "cases": cases,
    }
    emit(report, [ROOT/"python"/n for n in source_names]+[Path(__file__)])


if __name__ == "__main__":
    main()
