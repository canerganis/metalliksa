#!/usr/bin/env python3
"""Deterministic software counterexamples for the 2026-10-14 chain audit.

No experimental data, fitting, package installation or served-code mutation.
Run from any directory; default JSON goes to stdout, --output explicitly writes. This is a software audit,
not physical validation. All G/R/T inputs below are synthetic.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import sys
sys.dont_write_bytecode = True
from _solidification_check_common import emit, require

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
    col = cases["CET_source_limits_software_reproduction"]["columnar"]
    eq = cases["CET_source_limits_software_reproduction"]["equiaxed"]
    checks = {
        "HuntEquationArithmeticExpectedValue": math.isclose(hunt_oracle, 1.1773863284676703e-3, rel_tol=1e-12),
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
