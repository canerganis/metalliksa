"""Source-bounded synthetic coupling checks; never opens physical datasets.

Run from any directory with Python's standard library only:
    python -B docs/research/scripts/check_solidification_coupling.py
This is software/algebra evidence, not a numerical-convergence or blind test.
"""
from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path
import sys
import math
sys.dont_write_bytecode = True
from _solidification_check_common import emit, require

ROOT = Path(__file__).resolve().parents[3]
PYTHON = ROOT / "python"
sys.path.insert(0, str(PYTHON))


def load(name):
    spec = importlib.util.spec_from_file_location(name, PYTHON / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source_functions(path, names):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    selected = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    scope = {"Any": object, "Dict": dict, "math": __import__("math")}
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), "exec"), scope)
    return scope


def main():
    front = load("solidification_front")
    projection = load("lpbf_solidification_microstructure")
    wrapper = source_functions(PYTHON / "lpbf_gr_solidification.py", {"_is_num", "_loc_entry"})
    a, b, scale, speed, liquidus = 1e-3, 2e-4, 100.0, 1.0, 1700.0
    # Analytic manufactured field: exact rear ellipse, spatially varying amplitude.
    # Units: x,y,z m; T K; speed m/s. No heat-source/alloy parameter fit.
    # Rounding probe below matches the producer: R_m_s=round(1e-4,3)=0, R_mm_s=round(1e-4*1000,1)=0.1.
    def field(x, y, z):
        return liquidus + scale * (1 - (x / a) ** 2 - (z / b) ** 2) * (1 + 0.8 * x / a)
    positions = []
    original_gradient = front._grad_T
    def capture_gradient(fn, x, y, z, h):
        gradient = original_gradient(fn, x, y, z, h)
        if gradient[0] > 0:
            positions.append((x, z))
        return gradient
    front._grad_T = capture_gradient
    mapped = front.map_solidification_front(field, liquidus, speed, a, 2 * b, 2e-7)
    front._grad_T = original_gradient
    # Independent analytical derivative at the original, unrounded sample coordinates.
    analytic_cooling = [speed * scale * (-2*x/a**2*(1+0.8*x/a)
                        + (1-(x/a)**2-(z/b)**2)*0.8/a) for x,z in positions]
    analytic_residual = max(abs(s["G_K_m"]*s["R_m_s"]/q-1)
                            for s,q in zip(mapped["samples"], analytic_cooling))
    mutant_residual = max(abs(s["G_K_m"]*speed/q-1)
                         for s,q in zip(mapped["samples"], analytic_cooling))
    even = front.map_solidification_front(field, liquidus, speed, a, 2*b, 2e-7, n_samples=8)
    # Deliberately nonmonotone paired values: no alloy/process applicability claim.
    pairs = list(zip([1e5,2e7,1e6,8e7,3e5,1e7,4e6,6e7],
                     [1,.01,.8,.02,.5,.04,.3,.06]))
    upper_median = lambda xs: sorted(xs)[len(xs)//2]
    mg, mr = upper_median([g for g,r in pairs]), upper_median([r for g,r in pairs])
    local_labels = [front.hunt_morphology(g/r) for g,r in pairs]
    aggregate_label = front.hunt_morphology(mg/mr)
    import lpbf_cet_screening as cet
    import lpbf_solidification_segregation as segregation
    consts = {"a":4.5,"n":2.,"N0":2.65e14}
    local_cet = [cet.cet_band(g,r,consts)["band"] for g,r in pairs]
    aggregate_cet = cet.cet_band(mg,mr,consts)["band"]
    local_k = [segregation.aziz_partition_coefficient(.48,r,.5) for g,r in pairs]
    median_k = segregation.aziz_partition_coefficient(.48,mr,.5)
    paired = {"samples":[{"G_K_m":g,"R_m_s":r} for g,r in pairs],
              "separateUpperMedians":{"G_K_m":mg,"R_m_s":mr},
              "localMorphology":local_labels,"aggregateMorphology":aggregate_label,
              "localCET":local_cet,"aggregateCET":aggregate_cet,
              "localTrapping_k":local_k,"trappingAtMedianR":median_k,
              "meanLocalTrapping_k":sum(local_k)/len(local_k),
              "note":"Morphology/CET distributions and mean k differ from one median result. Scalar upper-median k does commute with upper-median R because this k(V) is monotone."}
    assert mapped and mapped["nPoints"] >= 3
    g, r, cooling = mapped["G_median_K_m"], mapped["R_median_m_s"], mapped["coolingRate_median_K_s"]
    wrapped = wrapper["_loc_entry"](g, r, derive=True, cooling=cooling)
    synthetic_low_rate = {
        "solidificationKinetics": {
            "usedFieldMap": True, "gradientSource": "conduction-field-interface",
            "thermalGradient_G_K_m": 1e5, "solidificationRate_R_m_s": 0.0,
            "solidificationRate_R_mm_s": 0.1, "coolingRate_K_s": 10.0,
        }
    }
    low_rate = projection.project_build_job_microstructure(synthetic_low_rate)
    # A translating planar level set T=Tl+G*(x-v*t) solidifies with R=v
    # even when liquid velocity U=0. This disproves U.n as an interface speed.
    planar_gradient, planar_speed, liquid_velocity = 1e6, 0.1, 0.0
    partial_time_derivative = -planar_gradient * planar_speed
    level_set_speed = -partial_time_derivative / planar_gradient
    legacy_cfd_speed = max(1e-6, liquid_velocity)
    mix = projection.morphology_fractions(1e7, 1.0)
    manifest_tree = ast.parse((PYTHON / "lpbf_simulation.py").read_text(encoding="utf-8"))
    manifest = next(ast.literal_eval(n.value) for n in manifest_tree.body
                    if isinstance(n, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == "IMPLEMENTATION_SOURCE_FILES" for t in n.targets))
    targets = ["calphad_solver.py", "lpbf_solidification_segregation.py",
               "lpbf_solidification_microstructure.py", "lpbf_gr_solidification.py",
               "lpbf_cet_screening.py", "solidification_front.py", "kinetics_ttt_cct_solver.py"]
    sources = [PYTHON / t for t in targets] + [PYTHON / "lpbf_simulation.py",
               PYTHON / "openfoam/meltPoolFoam/solidificationModel.H"]
    result = {
        "schema": "solidification-coupling-audit-2",
        "baselinePolicy":"Expected-defect assertions against served source, not future implementation acceptance.",
        "checkKind": "synthetic software and algebra checks",
        "experimentalValidation": False,
        "readsMeasuredMeltPoolDepths": False,
        "analyticCoolingOracle": {"definition":"v*dT/dx at unrounded original sample positions in laboratory frame; translating quasi-steady field", "relativeTolerance":3e-6,"maximumRelativeResidual":analytic_residual,"R_equals_scanSpeed_mutantResidual":mutant_residual},
        "evenCountFront": {"sampleCount":even["nPoints"],"productOfUpperMedians_K_s":even["G_median_K_m"]*even["R_median_m_s"],"maximumLocalCooling_K_s":max(s["coolingRate_K_s"] for s in even["samples"])},
        "nonmonotonePairedEvaluation":paired,
        "manufacturedFront": {
            "fieldDefinition": "T=1700+100*(1-(x/0.001)^2-(z/0.0002)^2)*(1+0.8*x/0.001), y-independent",
            "scanSpeed_m_s": speed, "sampleCount": mapped["nPoints"],
            "medianG_K_m": g, "medianR_m_s": r, "medianLocalCooling_K_s": cooling,
            "productOfMedians_K_s": g * r,
            "wrapperGtimesR_K_s": wrapped["GtimesR_K_s"],
            "aliasRelativeMismatch": wrapped["GtimesR_K_s"] / (g * r) - 1,
            "perSampleKinematicMaximumResidual_K_s": max(abs(s["coolingRate_K_s"] - s["G_K_m"] * s["R_m_s"]) for s in mapped["samples"]),
            "samples": mapped["samples"],
            "interpretation": "Local G*R is internally consistent; separate statistic cooling is not the product of the displayed median G and R. Wrapper GtimesR aliases a different statistic."
        },
        "transportRoundingPositiveRateProjection": {
            "input": synthetic_low_rate, "fixtureType":"synthetic transport-rounding probe, not a real served low-rate run",
            "status": low_rate["status"], "reason": low_rate.get("reason"),
            "interpretation": "Projection still treats a true small positive front speed (represented by R_mm_s=0.1, R_m_s rounded to 0 by the producer) as an old clamp floor, although P6 removed the upstream clamps."
        },
        "stationaryLiquidMovingPlanarInterface": {
            "manufacturedField": "T=Tl+G*(x-v*t); normal points along +x into liquid",
            "partialTimeDerivative_K_s": partial_time_derivative,
            "gradient_K_m": planar_gradient, "liquidVelocity_m_s": liquid_velocity,
            "levelSetInterfaceSpeed_m_s": level_set_speed, "legacyCfdReportedSpeed_m_s": legacy_cfd_speed,
            "interpretation": "Fluid velocity is not interface migration speed; floor gives 1e-6 for a manufactured interface migrating at 0.1 m/s."
        },
        "legacyCfdMorphologyFractions": {
            "input": {"G_K_m": 1e7, "R_m_s": 1.0}, "fractions": mix,
            "interpretation": "A mixed label produces zero mixed fraction; complement interpolation is not a grain-volume model."
        },
        "implementationManifest": {"manifestCount": len(manifest), "targetMembership": {t: t in manifest for t in targets},
            "legacyCfdHeaderMember": "openfoam/meltPoolFoam/solidificationModel.H" in manifest},
        "checks": {
            "analyticCoolingOracle": analytic_residual <= 3e-6,
            "R_equals_scanSpeed_mutantDetected": mutant_residual > .1,
            "evenUpperMedianPairExceedsLocalMaximum": even["G_median_K_m"]*even["R_median_m_s"] > max(s["coolingRate_K_s"] for s in even["samples"]),
            "pairedMorphologyDistributionDiffers": any(label != aggregate_label for label in local_labels),
            "pairedCETDistributionDiffers": any(label != aggregate_cet for label in local_cet),
            "pairedMeanTrappingDiffers":abs(sum(local_k)/len(local_k)-median_k)>1e-3,
            "localKinematicIdentityAccountingOnly": all(abs(s["coolingRate_K_s"] - s["G_K_m"] * s["R_m_s"]) < 1e-10 for s in mapped["samples"]),
            "aggregateAliasMismatchReproduced": abs(wrapped["GtimesR_K_s"] / (g * r) - 1) > 0.05,
            "obsoleteFloorMisclassificationReproduced": low_rate["status"] == "degenerate-floor",
            "cfdFluidVelocityCounterexample": legacy_cfd_speed != level_set_speed,
            "zeroMixedFractionReproduced": mix["mixed"] == 0.0,
        },
        "limits": ["No thermal solver or measured dataset imported.", "Manufactured fields do not establish real-alloy applicability.",
                   "No package installed.", "No mesh/time-step convergence, browser execution, or blind experiment test performed."]
    }
    require(result["checks"])
    emit(result, sources + [Path(__file__), PYTHON/"lpbf_cet_screening.py", PYTHON/"alloy_registry.py", PYTHON/"alloy_data_kinetics_uq_fatigue.py", PYTHON/"alloy_data_calphad_battery_icme.py", PYTHON/"four_alloy_materials.py", PYTHON/"physical_constants.py"])


if __name__ == "__main__":
    main()
