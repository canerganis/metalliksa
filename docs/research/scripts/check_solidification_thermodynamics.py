"""Source-bounded synthetic CALPHAD checks; stdlib only, no solver/data imports.

Extracts the existing pure Scheil kernel and constants with AST. The callback
emulates the actual liquid-reporting cutoff using a synthetic, conserved binary
tie line. No dataset or measured melt-pool quantity is read or executed.
Run: python docs/research/scripts/check_solidification_thermodynamics.py
"""
from __future__ import annotations

import ast
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import time
from typing import Any, Callable, Dict, List, Optional


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "python/calphad_solver.py"


def load_kernel():
    text = SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(text)
    selected = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id.startswith("SCHEIL_") for t in node.targets
        ):
            selected.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name == "scheil_gulliver":
            selected.append(node)
    namespace = dict(time=time, math=math, Any=Any, Callable=Callable, Dict=Dict,
                     List=List, Optional=Optional)
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(SOURCE), "exec"), namespace)
    return namespace["scheil_gulliver"], text


def cutoff_example(kernel):
    # Raw equilibrium: equal binary compositions, fL=0.0005, fS=0.9995.
    # Every atom balance is exact before application of the reporting cutoff.
    composition = {"A": 0.8, "B": 0.2}
    raw_liquid = 0.0005
    raw_solid = 1.0 - raw_liquid

    def callback(_temperature, _composition):
        # calphad_solver.py point_equilibria only collects LIQUID when >0.001.
        reported_liquid = raw_liquid if raw_liquid > 0.001 else 0.0
        return {"liquid": reported_liquid, "liquidX": composition if reported_liquid else {},
                "phases": {"SOLID": raw_solid}, "phasesX": {"SOLID": composition}}

    result = kernel(callback, 1000.0, composition, step_c=0.01)
    amount_sum = sum(result["phaseAmounts"].values()) + result["remainingLiquidFraction"]
    independent_balance = max(abs(raw_solid * composition[c] - composition[c]) for c in composition)
    assert result["status"] == "complete"
    assert result["points"][-1]["fractionSolid"] == 1.0
    assert abs(amount_sum - 0.9995) < 1e-12
    assert result["massBalanceMaxAbsError"] == 0.0
    assert independent_balance > 0.0
    return {
        "kind": "synthetic software counterexample, not experimental validation",
        "rawEquilibriumLiquidFraction": raw_liquid,
        "rawEquilibriumSolidFraction": raw_solid,
        "rawEquilibriumAtomBalanceMaxAbsError": 0.0,
        "reportedStatus": result["status"],
        "reportedTerminationReason": result["terminationReason"],
        "reportedFractionSolid": result["points"][-1]["fractionSolid"],
        "reportedRemainingLiquidFraction": result["remainingLiquidFraction"],
        "reportedPhaseAmountSum": amount_sum,
        "reportedMassBalanceMaxAbsError": result["massBalanceMaxAbsError"],
        "independentAtomBalanceErrorUsingReportedPhaseAmounts": independent_balance,
    }


def clamped_composition_example(kernel):
    requested = {"A": 1.0 - 1e-8, "B": 1e-8}

    def callback(_temperature, used):
        return {"liquid": 0.0, "liquidX": {}, "phases": {"SOLID": 1.0},
                "phasesX": {"SOLID": dict(used)}}

    result = kernel(callback, 1000.0, requested, step_c=0.01)
    assert result["status"] == "complete" and result["clampedSteps"] == 1
    assert result["massBalanceMaxAbsError"] > 9e-7
    return {"kind": "synthetic software policy check, not a real alloy",
            "requestedMoleFractionB": requested["B"],
            "usedSolidMoleFractionB": result["points"][-1]["solidX"]["B"],
            "reportedStatus": result["status"], "clampedSteps": result["clampedSteps"],
            "reportedMassBalanceMaxAbsError": result["massBalanceMaxAbsError"],
            "note": "Complete is a termination status, not a conservation gate."}


def main():
    kernel, text = load_kernel()
    parser = ast.parse(text)
    historical_exponent = any(isinstance(n, ast.Constant) and n.value == -0.28 for n in ast.walk(parser))
    # Unary minus is represented as a UnaryOp, so check it separately.
    historical_exponent |= any(isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub)
                               and isinstance(n.operand, ast.Constant) and n.operand.value == 0.28
                               for n in ast.walk(parser))
    catalog = next(n for n in parser.body if isinstance(n, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == "OPEN_TDB_CATALOG" for t in n.targets))
    # Replace only the two status name references with their literal strings.
    class StatusLiterals(ast.NodeTransformer):
        def visit_Name(self, node):
            if node.id in {"DB_STATUS_ASSESSMENT", "DB_STATUS_TEST_FIXTURE"}:
                return ast.copy_location(ast.Constant("assessment" if node.id.endswith("ASSESSMENT") else "test-fixture"), node)
            return node
    entries = ast.literal_eval(StatusLiterals().visit(catalog.value))
    db_rows = []
    for entry in entries:
        if entry["id"] not in {"cost507", "mc_ti", "mc_ni", "mc_fe"}:
            continue
        path = ROOT / "python/databases" / entry["fileName"]
        db_text = path.read_text(encoding="utf-8", errors="replace")
        db_rows.append({"id": entry["id"], "file": entry["fileName"],
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "licenseNoticeODbL": "opendatacommons.org/licenses/odbl/1.0" in db_text,
                        "explicitFreeUseNotice": "It may be used freely" in db_text,
                        "elements": entry["elements"],
                        "testedLimitsWtPct": entry.get("testedLimitsWtPct"),
                        "excludedPhases": entry.get("excludedPhases", {}),
                        "scopeFlag": entry.get("scopeFlag")})
    output = {"source": "python/calphad_solver.py",
              "evidenceKind": "Screening only",
              "moduleMaturity": "Research",
              "sourceSha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
              "historicalMinus028ExponentPresent": historical_exponent,
              "cutoffCounterexample": cutoff_example(kernel),
              "clampedCompositionExample": clamped_composition_example(kernel),
              "databaseSourceInventory": db_rows,
              "pycalphadInstalledVersion": importlib.metadata.version("pycalphad"),
              "pycalphadInstalledLicense": importlib.metadata.metadata("pycalphad").get("License"),
              "servedSolverImported": False, "datasetsRead": False,
              "physicalValidationPerformed": False}
    destination = Path(__file__).with_suffix(".json")
    destination.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(destination.relative_to(ROOT)),
                      "cutoffCounterexampleReproduced": True,
                      "historicalMinus028ExponentPresent": historical_exponent}))


if __name__ == "__main__":
    main()
