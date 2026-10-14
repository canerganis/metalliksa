"""Source-bounded synthetic coupling checks; never opens physical datasets.

Run from any directory with Python's standard library only:
    python -B docs/research/scripts/check_solidification_coupling.py
This is software/algebra evidence, not a numerical-convergence or blind test.
"""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
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
    def field(x, y, z):
        return liquidus + scale * (1 - (x / a) ** 2 - (z / b) ** 2) * (1 + 0.8 * x / a)
    mapped = front.map_solidification_front(field, liquidus, speed, a, 2 * b, 2e-7)
    assert mapped and mapped["nPoints"] >= 3
    g, r, cooling = mapped["G_median_K_m"], mapped["R_median_m_s"], mapped["coolingRate_median_K_s"]
    wrapped = wrapper["_loc_entry"](g, r, derive=True, cooling=cooling)
    synthetic_low_rate = {
        "solidificationKinetics": {
            "usedFieldMap": True, "gradientSource": "conduction-field-interface",
            "thermalGradient_G_K_m": 1e5, "solidificationRate_R_m_s": 5e-5,
            "solidificationRate_R_mm_s": 0.05, "coolingRate_K_s": 5.0,
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
        "schema": "solidification-coupling-audit-1",
        "evidenceKind": "Screening only",
        "moduleMaturity": "Research",
        "checkKind": "synthetic software and algebra checks",
        "experimentalValidation": False,
        "readsMeasuredMeltPoolDepths": False,
        "sourceHead": subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip(),
        "sourceSha256": {str(p.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
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
        "genuineLowPositiveRateProjection": {
            "input": synthetic_low_rate,
            "status": low_rate["status"], "reason": low_rate.get("reason"),
            "interpretation": "Projection still treats a true small positive front speed as an old clamp floor, although P6 removed the upstream clamps."
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
            "localKinematicIdentity": all(abs(s["coolingRate_K_s"] - s["G_K_m"] * s["R_m_s"]) < 1e-10 for s in mapped["samples"]),
            "aggregateAliasMismatchReproduced": abs(wrapped["GtimesR_K_s"] / (g * r) - 1) > 0.05,
            "obsoleteFloorMisclassificationReproduced": low_rate["status"] == "degenerate-floor",
            "cfdFluidVelocityCounterexample": legacy_cfd_speed != level_set_speed,
            "zeroMixedFractionReproduced": mix["mixed"] == 0.0,
        },
        "limits": ["No thermal solver or measured dataset imported.", "Manufactured fields do not establish real-alloy applicability.",
                   "No package installed.", "No mesh/time-step convergence, browser execution, or blind experiment test performed."]
    }
    if not all(result["checks"].values()):
        raise SystemExit("A documented defect did not reproduce; review the current sources before changing this audit.")
    output = Path(__file__).with_suffix(".json")
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output.relative_to(ROOT)), "checks": result["checks"]}, sort_keys=True))


if __name__ == "__main__":
    main()
