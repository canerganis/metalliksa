"""Source-bounded synthetic CALPHAD checks; stdlib only, no solver/data imports.

Extracts the pure Scheil kernel and the actual liquid-reporting adapter with AST.
Exercises synthetic conserved tie lines and raw phase vertices; no database solver
call or measured melt-pool quantity is read or executed. Package versions are metadata only.
Run: python -I -B docs/research/scripts/check_solidification_thermodynamics.py --check
"""
from __future__ import annotations

import ast
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import time
import sys
from types import SimpleNamespace
sys.dont_write_bytecode = True
# -I deliberately excludes the script directory; admit this resolved sibling only.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _solidification_check_common import emit, require
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
    assert result["status"] == "complete" and result["firstStepUnresolved"] is True
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
        "firstStepUnresolved":result["firstStepUnresolved"],
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



def callback_oracle(row, nominal):
    """Independent lever-rule validation, never back-solves a solid composition."""
    phases = [(row["liquid"], row["liquidX"])] if row["liquid"] else []
    phases += [(amount,row["phasesX"][phase]) for phase,amount in row["phases"].items()]
    amount_error=abs(sum(amount for amount,x in phases)-1)
    composition_error=max(abs(sum(x.values())-1) for amount,x in phases)
    negative=any(amount<0 or any(v<0 or v>1 or not math.isfinite(v) for v in x.values()) for amount,x in phases)
    inventory={c:sum(amount*x.get(c,0) for amount,x in phases) for c in nominal}
    residual=max(abs(inventory[c]-nominal[c]) for c in nominal)
    return {"phaseAmountSumError":amount_error,"phaseCompositionSumError":composition_error,
            "nonphysicalComposition":negative,"elementInventory":inventory,"maximumElementResidual":residual,
            "valid":amount_error<=1e-12 and composition_error<=1e-12 and not negative and residual<=1e-12}


def production_point_adapter_examples(text):
    """Execute the actual nested adapter on raw synthetic vertices, no DB/pycalphad calls."""
    tree=ast.parse(text)
    outer=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="_solve_with_runner")
    nodes=[n for n in ast.walk(outer) if isinstance(n,ast.FunctionDef) and n.name in {"point_equilibria","run_point"}]
    class FakeNP:
        @staticmethod
        def isfinite(value):
            return [math.isfinite(v) for v in value] if isinstance(value,list) else math.isfinite(value)
        all=staticmethod(all)
    class Cube:
        def __init__(self,rows):self.rows=rows
        def __getitem__(self,key):
            i,j,k=key;return self.rows[i][j][k]
    scope={"Any":Any,"Optional":Optional,"Dict":Dict,"List":List,"math":math,"np":FakeNP,
           "sys":sys,"conditions":{},"indep_comps":["B"],"eq_comps":["A","B"],
           "v":SimpleNamespace(T="T",X=lambda c:c),"ZERO_CELSIUS_K":273.15,
           "runner":SimpleNamespace(run=lambda conditions:None)}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(SOURCE),"exec"),scope)
    cases={}
    for label,names,amounts,xs in [
        ("positiveLowLiquid",["LIQUID","SOLID"],[.0005,.9995],[[.8,.2],[.8,.2]]),
        ("hiddenSecondLiquidVertex",["LIQUID","LIQUID","SOLID"],[.2,.0005,.7995],[[.8,.2],[.4,.6],[.8,.2]])]:
        scope["_flat_point_arrays"]=lambda _eq,_n,ns=names,am=amounts,x=xs:([0.],[[0.,0.]],[ns],[am],Cube([x]))
        row=scope["point_equilibria"]([1000])[0]
        wrapped=scope["run_point"](1000,{"A":.8,"B":.2})
        cases[label]={"rawPhaseNames":names,"rawPhaseAmounts":amounts,"rawLiquidVertexCount":names.count("LIQUID"),
                      "servedAdapter":row,"servedRunPointAccepted":wrapped is not None}
    return cases


def additional_examples(kernel,text):
    nominal={"A":.8,"B":.2}
    invalid_cases=[]
    for amounts,x in [(.4,{"A":.8,"B":.2}),(18.5,{"A":1.1,"B":-.1})]:
        callback={"liquid":0.,"liquidX":{},"phases":{"SOLID":amounts},"phasesX":{"SOLID":x}}
        result=kernel(lambda t,used:callback,1000,nominal,step_c=.01)
        oracle=callback_oracle(callback,nominal)
        invalid_cases.append({"callback":callback,"independentOracle":oracle,"servedStatus":result["status"],
                              "firstStepUnresolved":result["firstStepUnresolved"],
                              "servedIdentityResidual":result["massBalanceMaxAbsError"],
                              "reportedPhaseAmounts":result["phaseAmounts"]})
    # A fully conserved callback reaches the 0.1% stop, leaving liquid .03**2=.0009.
    conserved={"liquid":.03,"liquidX":nominal,"phases":{"SOLID":.97},"phasesX":{"SOLID":nominal}}
    stop=kernel(lambda t,used:conserved,1000,nominal,step_c=.01)
    control=callback_oracle(conserved,nominal)
    mutated=dict(conserved,phasesX={"SOLID":{"A":.7,"B":.3}})
    mutant=callback_oracle(mutated,nominal)
    # Extract and execute the served request clamp expression, not a duplicated floor rule.
    tree=ast.parse(text)
    clamp=next(n.value for n in ast.walk(tree) if isinstance(n,ast.Assign) and isinstance(n.value,ast.Call)
               and ast.unparse(n.value)=="max(1e-05, min(0.999, active_at_frac[comp]))")
    requested=4.78e-11
    used=eval(compile(ast.Expression(clamp),str(SOURCE),"eval"),{"active_at_frac":{"MO":requested},"comp":"MO"})
    clamped_nominal={"A":1-used,"B":used}
    out=kernel(lambda t,x:{"liquid":0.,"liquidX":{},"phases":{"SOLID":1.},"phasesX":{"SOLID":dict(x)}},1000,clamped_nominal,step_c=.01)
    adapter=production_point_adapter_examples(text)
    checks={
        "invalidCallbackIdentityCannotFire":all(c["servedStatus"]=="complete" and c["servedIdentityResidual"]<=1e-12 and not c["independentOracle"]["valid"] for c in invalid_cases),
        "independentOracleAcceptsConservedControl":control["valid"],
        "reportedInventoryMatchesIndependentTwoStepLedger":abs(stop["phaseAmounts"]["SOLID"]-.97*(1+.03))<=5e-7 and abs(stop["remainingLiquidFraction"]-.03**2)<=5e-7,
        "phaseCompositionMutantDetected":not mutant["valid"] and mutant["maximumElementResidual"]>.09,
        "positiveResidualLiquidCalledComplete":stop["status"]=="complete" and abs(stop["remainingLiquidFraction"]-.0009)<=5e-7 and not stop["firstStepUnresolved"],
        "actualRequestClampBeforeKernel":used==1e-5 and out["clampedSteps"]==0 and out["massBalanceMaxAbsError"]<=1e-12,
        "actualPointAdapterDropsPositiveLiquid":adapter["positiveLowLiquid"]["servedAdapter"]["liquid"]==0,
        "actualPointAdapterHidesMiscibilityVertex":adapter["hiddenSecondLiquidVertex"]["servedAdapter"]["liquidVertices"]==1 and adapter["hiddenSecondLiquidVertex"]["servedRunPointAccepted"],
    }
    return {"checks":checks,"invalidCallbackExamples":invalid_cases,"independentConservationControl":control,
            "independentTwoStepLedger":{"expectedSolidAmount":.97*(1+.03),"expectedRemainingLiquidAmount":.03**2,"expectedElementInventory":nominal,"reportedSolidAmount":stop["phaseAmounts"]["SOLID"]},
            "phaseCompositionMutant":mutant,"positiveResidualLiquidStop":{"remainingLiquidFraction":stop["remainingLiquidFraction"],"terminationReason":stop["terminationReason"],"reportedStatus":stop["status"],"firstStepUnresolved":stop["firstStepUnresolved"]},
            "servedRequestClamp":{"requestedMoleFraction":requested,"usedMoleFraction":used,"enrichmentFactor":used/requested,"kernelClampedSteps":out["clampedSteps"],"identityResidual":out["massBalanceMaxAbsError"]},
            "actualPointAdapterSyntheticVertices":adapter,"tolerances":{"callbackInventoryAbsolute":1e-12,"sixDecimalInventoryAbsolute":5e-7},
            "limitations":["Checks reproduce served defects; passing does not claim fixes implemented.","No database equilibrium calculation or measured dataset read.","The extracted kernel floor is distinct from the served request clamp."]}

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
    output = {"schema":"solidification-thermodynamics-software-audit-2",
              "baselinePolicy":"Expected-defect assertions against served source, not future implementation acceptance.",
              "source": "python/calphad_solver.py",
              "historicalMinus028ExponentPresent": historical_exponent,
              "cutoffCounterexample": cutoff_example(kernel),
              "kernelOnlyClampedCompositionExample": clamped_composition_example(kernel),
              "databaseSourceInventory": db_rows,
              "environmentPackages":{"pycalphad":{"version":importlib.metadata.version("pycalphad"),"license":importlib.metadata.metadata("pycalphad").get("License")}, "scheil":{"version":importlib.metadata.version("scheil"),"license":importlib.metadata.metadata("scheil").get("License")}},
              "servedSolverImported": False, "datasetsRead": False,
              "physicalValidationPerformed": False}
    output.update(additional_examples(kernel, text))
    checks=output["checks"]
    checks["lowLiquidCutoffDefectReproduced"]=output["cutoffCounterexample"]["reportedPhaseAmountSum"] == .9995
    checks["minus028Retired"]=not historical_exponent
    require(checks)
    emit(output, [SOURCE,Path(__file__)]+[ROOT/"python/databases"/r["file"] for r in db_rows])


if __name__ == "__main__":
    main()
