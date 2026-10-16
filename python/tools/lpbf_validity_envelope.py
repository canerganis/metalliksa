#!/usr/bin/env python3
"""Validity envelope of the LPBF enthalpy-FV reference transient (WP-N2).

Sweeps alloy x mesh x nominal laser power power_W (absorbed = power_W x
absorptivity) with the standard-mode, reference backend, homogenised powder
layer and records, per case, whether run() completes
or stops at the boiling validity stop, plus width/depth/length and peak cell
temperature of completed cases.

Scope (also written into the JSON): this is a MODEL ENVELOPE of the reference
transient at these fixed settings. It is not a process window, not a product
specification and not experimental validation. The boiling stop is mesh
dependent (the peak cell temperature is), so a verdict at one mesh_um is not
converged evidence.

Usage (from python/, locked interpreter, PYTHONDONTWRITEBYTECODE=1):
    python -B tools/lpbf_validity_envelope.py --out ../docs/LPBF_VALIDITY_ENVELOPE_2026-10-04.json
    python -B tools/lpbf_validity_envelope.py --quick --out <json>
    python -B tools/lpbf_validity_envelope.py --alloy "Ti-6Al-4V" --mesh 20 --powers 60 80 --out <json>

The tool is resumable: the output file is rewritten after every case. A cached
completed or boiling-stop case is reused only if its input is identical and it carries
the current implementation fingerprint; records without an implementationHash,
"not-run (budget)" and "other-error" records are never reused (use --rerun to
recompute everything).
Each case runs in its own spawned process so a per-case wall-time budget
(--budget-s, default 900 s) can stop it and record "not-run (budget)".
"""

from __future__ import annotations

import argparse
import json
import multiprocessing
import os
import platform
import queue as queue_module
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SCHEMA = "lpbf-validity-envelope-1"
SCOPE = ("Model envelope of the enthalpy-FV reference transient with the homogenised powder layer "
         "at these fixed settings; the boiling validity stop is mesh-dependent; "
         "not a process window, not experimental validation.")

ALLOYS = ("Inconel 718", "Ti-6Al-4V", "316L Stainless Steel", "AlSi10Mg")
POWERS_20 = (40., 60., 80., 100., 120., 150., 200.)
POWERS_10 = (40., 60., 80., 100.)
BUDGET_S_DEFAULT = 900.0
CONSECUTIVE_BOILING_STOP = 2

COMPLETED = "completed"
BOILING_STOP = "boiling-stop"
OTHER_ERROR = "other-error"
NOT_RUN_BUDGET = "not-run (budget)"
NOT_RUN_MONOTONE = "not-run (higher power after two consecutive boiling stops)"
REUSABLE_STATUSES = (COMPLETED, BOILING_STOP)  # budget stops and errors are always retried


def classify_error(message: str) -> str:
    """Boiling validity stop vs any other error, from the ValueError message."""
    return BOILING_STOP if "boiling" in str(message).lower() else OTHER_ERROR


def default_plan() -> List[Tuple[str, float, Tuple[float, ...]]]:
    """The specified sweep: four alloys at 20 um; IN718 only at 10 um."""
    plan = [(alloy, 20., POWERS_20) for alloy in ALLOYS]
    plan.append(("Inconel 718", 10., POWERS_10))
    return plan


def build_plan(alloys: Optional[Sequence[str]] = None, meshes: Optional[Sequence[float]] = None,
               powers: Optional[Sequence[float]] = None, quick: bool = False
               ) -> List[Tuple[str, float, Tuple[float, ...]]]:
    if quick:
        return [("Inconel 718", 20., tuple(float(p) for p in powers) if powers else POWERS_20)]
    if not alloys and not meshes and not powers:
        return default_plan()
    if not alloys and meshes is None and powers:
        return [(a, m, tuple(float(p) for p in powers)) for a, m, _ in default_plan()]
    plan = []
    for alloy in (alloys or ALLOYS):
        for mesh in (meshes or (20., 10.)):
            if not alloys and mesh == 10. and alloy != "Inconel 718":
                continue
            default = POWERS_10 if mesh == 10. else POWERS_20
            plan.append((alloy, float(mesh), tuple(float(p) for p in powers) if powers else default))
    return plan


def build_raw(defaults: Dict[str, Any], alloy: str, power_W: float, mesh_um: float) -> Dict[str, Any]:
    raw = dict(defaults)
    raw.update(mode="standard", backend="reference", material=alloy,
               power_W=float(power_W), mesh_um=float(mesh_um))
    return raw


def _summarise_completed(result: Dict[str, Any]) -> Dict[str, Any]:
    metrics = result["metrics"]
    diagnostics = result.get("numericalDiagnostics") or {}
    keep = ("peakMeltCellCount", "peakMeltTime_s", "peakMeltStep", "meltPoolObservedSteps",
            "minimumCapturedSourceFraction", "maximumEnthalpyIncrement_K", "maximumTimestep_s",
            "sourceTimestepRetries")
    return dict(
        width_um=metrics["width_um"], depth_um=metrics["depth_um"], length_um=metrics["length_um"],
        peakTemperature_K=metrics["peakTemperature_K"],
        thermalGradient_K_m=metrics.get("thermalGradient_K_m"),
        coolingRate_K_s=metrics.get("coolingRate_K_s"),
        # SOL-T D13: the per-value label and the parent liquidus convention travel with the legacy event means.
        transientFrontEvidence={
            name: {"status": q.get("status"), "sourceEvidenceKind": q.get("sourceEvidenceKind"),
                   "labelSources": q.get("labelSources")}
            for name, q in ((result.get("transientFrontDiagnostics") or {}).get("quantities") or {}).items()
            if name in ("thermalGradient_K_m", "coolingRate_K_s")} or None,
        energyBalanceRelativeError=result["energyBalance"]["relativeError"],
        numericalDiagnosticsSummary={k: diagnostics.get(k) for k in keep},
        implementationHash=result["provenance"]["implementationHash"],
        inputHash=result["provenance"]["inputHash"],
        label=result.get("label"), validationStatus=result.get("validationStatus"),
    )


def run_case(raw: Dict[str, Any], run_fn: Callable[..., Dict[str, Any]],
             validate_fn: Optional[Callable[[Dict[str, Any]], Any]] = None) -> Dict[str, Any]:
    """Run one case in-process and return its outcome record (no input echo)."""
    started = time.perf_counter()
    try:
        if validate_fn is not None:
            validate_fn(raw)
        result = run_fn(raw)
    except ValueError as exc:
        message = str(exc)
        return dict(status=classify_error(message), message=message[:800],
                    wall_s=round(time.perf_counter() - started, 3))
    except Exception as exc:  # recorded as data, never silenced
        return dict(status=OTHER_ERROR, message=f"{type(exc).__name__}: {exc}"[:800],
                    wall_s=round(time.perf_counter() - started, 3))
    outcome = dict(status=COMPLETED, wall_s=round(time.perf_counter() - started, 3))
    outcome.update(_summarise_completed(result))
    return outcome


def _worker(raw: Dict[str, Any], queue: Any) -> None:  # runs in a spawned process
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    from lpbf_simulation import run, validate
    queue.put(run_case(raw, run, validate))


POLL_S = 0.5


def collect_outcome(queue: Any, process: Any, budget_s: float, started: float,
                    poll_s: float = POLL_S) -> Dict[str, Any]:
    """Wait for the worker's outcome. A worker that exits without reporting (segfault, OOM kill) is
    recorded at once as other-error with its exit code; only a real timeout is not-run (budget)."""
    deadline = started + budget_s
    while True:
        remaining = deadline - time.perf_counter()
        if remaining <= 0:
            process.terminate()
            process.join(30)
            return dict(status=NOT_RUN_BUDGET, wall_s=round(time.perf_counter() - started, 3),
                        message=f"stopped after the {budget_s:g} s per-case budget")
        try:
            return queue.get(timeout=min(poll_s, remaining))
        except queue_module.Empty:
            pass
        if process.exitcode is not None:
            try:  # the result may have been queued just before the worker exited
                return queue.get(timeout=1.0)
            except queue_module.Empty:
                return dict(status=OTHER_ERROR, wall_s=round(time.perf_counter() - started, 3),
                            message=f"worker process exited with code {process.exitcode} before reporting a result")


def run_case_with_budget(raw: Dict[str, Any], budget_s: float) -> Dict[str, Any]:
    ctx = multiprocessing.get_context("spawn")
    queue = ctx.Queue()
    process = ctx.Process(target=_worker, args=(raw, queue))
    started = time.perf_counter()
    process.start()
    outcome = collect_outcome(queue, process, budget_s, started)
    process.join(60)
    return outcome


def case_key(alloy: str, mesh_um: float, power_W: float) -> str:
    return f"{alloy}|{mesh_um:g}|{power_W:g}"


def _git_head(repo: Path) -> Optional[str]:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(repo), capture_output=True,
                             text=True, timeout=30, check=True)
        return out.stdout.strip() or None
    except Exception:
        return None


def _tree_dirty(repo: Path) -> Optional[bool]:
    """True if the python/ tree (tracked changes or untracked files) differs from HEAD; None if unknown."""
    try:
        out = subprocess.run(["git", "status", "--porcelain", "--", "."], cwd=str(repo), capture_output=True,
                             text=True, timeout=30, check=True)
        return bool(out.stdout.strip())
    except Exception:
        return None


def environment_record(fingerprint: Optional[str]) -> Dict[str, Any]:
    import numpy
    python_dir = Path(__file__).resolve().parent.parent
    return dict(python=sys.version.split()[0], numpy=numpy.__version__, platform=platform.platform(),
                gitHead=_git_head(python_dir), treeDirty=_tree_dirty(python_dir),
                implementationFingerprint=fingerprint)


def load_existing(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if data.get("schema") == SCHEMA else {}


def write_document(path: Path, document: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(document, indent=2, sort_keys=False, allow_nan=False) + "\n", encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def new_document(environment: Dict[str, Any], budget_s: float) -> Dict[str, Any]:
    return dict(schema=SCHEMA, scope=SCOPE, generatedFor="2026-10-04",
                fixedSettings="DEFAULTS with mode=standard, backend=reference; see each case's input",
                perCaseBudget_s=budget_s, environment=environment, cases=[])


def sweep(plan: Sequence[Tuple[str, float, Sequence[float]]], defaults: Dict[str, Any],
          document: Dict[str, Any], out_path: Optional[Path],
          case_runner: Callable[[Dict[str, Any]], Dict[str, Any]], rerun: bool = False,
          log: Callable[[str], None] = lambda s: None, fingerprint: Optional[str] = None) -> Dict[str, Any]:
    """Run the plan, rewriting out_path after each case. Resumes from document['cases'].

    A cached case is reused only if its status is completed or boiling-stop, its input is equal and,
    when a fingerprint is given, its implementationHash equals it (a record without a hash is
    recomputed). "not-run (budget)" and "other-error" records are always retried. Cases recomputed
    with a fingerprint carry that implementationHash (also boiling stops, which have no solver
    provenance)."""
    existing = {case_key(c["alloy"], c["mesh_um"], c["power_W"]): c for c in document.get("cases", [])}
    cases: List[Dict[str, Any]] = []
    for alloy, mesh, powers in plan:
        consecutive = 0
        for power in sorted(powers):
            raw = build_raw(defaults, alloy, power, mesh)
            key = case_key(alloy, mesh, power)
            prior = existing.get(key)
            if consecutive >= CONSECUTIVE_BOILING_STOP:
                record = dict(alloy=alloy, mesh_um=float(mesh), power_W=float(power), input=raw,
                              status=NOT_RUN_MONOTONE, wall_s=0.0)
            elif (prior is not None and not rerun and prior.get("input") == raw
                  and prior.get("status") in REUSABLE_STATUSES
                  and (fingerprint is None or prior.get("implementationHash") == fingerprint)):
                record = prior
                log(f"reuse {key}: {record['status']}")
            else:
                outcome = case_runner(raw)
                record = dict(alloy=alloy, mesh_um=float(mesh), power_W=float(power), input=raw)
                record.update(outcome)
                if fingerprint is not None:
                    record.setdefault("implementationHash", fingerprint)
                log(f"{key}: {record['status']} ({record.get('wall_s')} s)")
            if record["status"] == BOILING_STOP:
                consecutive += 1
            elif record["status"] != NOT_RUN_MONOTONE:
                consecutive = 0
            cases.append(record)
            document["cases"] = _merged(cases, existing)
            if out_path is not None:
                write_document(out_path, document)
    document["cases"] = _merged(cases, existing)
    document["summary"] = summarise(document["cases"])
    document["totalCaseWall_s"] = round(sum(c.get("wall_s", 0.0) for c in document["cases"]), 1)
    if out_path is not None:
        write_document(out_path, document)
    return document


def _merged(done: Sequence[Dict[str, Any]], existing: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Cases of this plan plus earlier cases (from other plans) kept for resumability."""
    seen = {case_key(c["alloy"], c["mesh_um"], c["power_W"]) for c in done}
    merged = list(done) + [c for k, c in existing.items() if k not in seen]
    order = {name: i for i, name in enumerate(ALLOYS)}
    return sorted(merged, key=lambda c: (order.get(c["alloy"], len(order)), c["alloy"], -c["mesh_um"], c["power_W"]))


def summarise(cases: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Per alloy x mesh: highest completed power, first boiling-stop power and its metrics."""
    groups: Dict[Tuple[str, float], List[Dict[str, Any]]] = {}
    for case in cases:
        groups.setdefault((case["alloy"], case["mesh_um"]), []).append(case)
    rows = []
    for (alloy, mesh), group in groups.items():
        group = sorted(group, key=lambda c: c["power_W"])
        done = [c for c in group if c["status"] == COMPLETED]
        stops = [c for c in group if c["status"] == BOILING_STOP]
        top = done[-1] if done else None
        rows.append(dict(
            alloy=alloy, mesh_um=mesh,
            highestCompletedPower_W=top["power_W"] if top else None,
            firstBoilingStopPower_W=stops[0]["power_W"] if stops else None,
            peakTemperature_K=top["peakTemperature_K"] if top else None,
            width_um=top["width_um"] if top else None,
            depth_um=top["depth_um"] if top else None,
            length_um=top["length_um"] if top else None,
            notRunBudget=[c["power_W"] for c in group if c["status"] == NOT_RUN_BUDGET],
            otherErrors=[c["power_W"] for c in group if c["status"] == OTHER_ERROR]))
    return rows


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", required=True, help="output JSON path (rewritten after every case)")
    parser.add_argument("--alloy", action="append", help="alloy name (repeatable); default: the four alloys")
    parser.add_argument("--mesh", action="append", type=float, help="mesh_um (repeatable)")
    parser.add_argument("--powers", nargs="+", type=float, help="powers in W")
    parser.add_argument("--quick", action="store_true", help="Inconel 718, 20 um only")
    parser.add_argument("--budget-s", type=float, default=BUDGET_S_DEFAULT, help="per-case wall-time budget")
    parser.add_argument("--rerun", action="store_true", help="recompute cases already in --out")
    args = parser.parse_args(argv)

    from lpbf_simulation import DEFAULTS, implementation_fingerprint
    out_path = Path(args.out)
    environment = environment_record(implementation_fingerprint())
    document = load_existing(out_path) or new_document(environment, args.budget_s)
    document["environment"] = environment
    document["perCaseBudget_s"] = args.budget_s
    document.pop("sessionWall_s", None)
    plan = build_plan(args.alloy, args.mesh, args.powers, args.quick)
    started = time.perf_counter()
    sweep(plan, dict(DEFAULTS), document, out_path,
          lambda raw: run_case_with_budget(raw, args.budget_s), rerun=args.rerun,
          log=lambda s: print(s, flush=True), fingerprint=environment["implementationFingerprint"])
    print(f"wrote {out_path} in {time.perf_counter() - started:.1f} s this session; "
          f"cumulative case wall time {document['totalCaseWall_s']} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
