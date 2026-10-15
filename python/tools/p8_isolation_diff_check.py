#!/usr/bin/env python3
"""P8 branch-scoped isolation diff (integration contract 2026-10-15, P-2 and 13.11).

Checks that the P8 commits themselves, the range P8_BASE..HEAD by default, touch no file of the
frozen LPBF manifest (lpbf_simulation.IMPLEMENTATION_SOURCE_FILES, read from git objects at both
ends of the range), none of the served entry modules listed below, and leave the thermal-solver
route block of routes/physics.ts unchanged (the 150-character rule of
python/test_lpbf_calibration_frozen.py T-FRZ-3).

This is a phase G tool run once over the P8 range, never a permanent test. P8_BASE is the
commit phase B started from; it changes only by an explicit lead decision.

Usage (from the repository root or python/):
    python -B python/tools/p8_isolation_diff_check.py [--range <base>..<head>]
Exit 0 when every check passes, 1 when one fails, 2 on a usage or git error.
"""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from pathlib import Path

# Written by the first phase B commit: the commit phase B starts from (contract 13.11 item 1).
P8_BASE = "14e13ea898ffc40bd39a950b191a365a615ef04e"

REPO_ROOT = Path(__file__).resolve().parents[2]

SERVED_ENTRY_MODULES = (
    "python/lpbf_build_job_solver.py",
    "python/lpbf_build_job_material_snapshot.py",
    "python/lpbf_build_job_schema.py",
    "python/lpbf_job_cache.py",
    "python/lpbf_worker.py",
    "python/lpbf_process_window.py",
    "python/lpbf_bayesian_optimizer.py",
    "python/lpbf_screening_uq.py",
    "python/lpbf_gr_solidification.py",
    "python/lpbf_solidification_microstructure.py",
    "python/lpbf_calibrated_meltpool.py",
    "python/lpbf_calibration_layer.py",
    "python/lpbf_machine_calibrated_meltpool.py",
    "python/lpbf_machine_calibration.py",
    "src/store/useLpbfBuildJobStore.ts",
    "src/utils/lpbfBuildJobIdentity.ts",
)
THERMAL_ROUTE = 'physicsRouter.post("/api/python/lpbf-thermal-solver"'
ROUTE_BLOCK_CHARS = 150


class GitError(RuntimeError):
    pass


def _git(*args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=str(REPO_ROOT), capture_output=True, text=True,
                          encoding="utf-8", timeout=120)
    if proc.returncode != 0:
        raise GitError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def manifest_at(rev: str) -> tuple:
    """IMPLEMENTATION_SOURCE_FILES parsed (not imported) from python/lpbf_simulation.py at rev."""
    tree = ast.parse(_git("show", f"{rev}:python/lpbf_simulation.py"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "IMPLEMENTATION_SOURCE_FILES"
                                                for t in node.targets):
            return tuple(ast.literal_eval(node.value))
    raise GitError(f"IMPLEMENTATION_SOURCE_FILES not found in python/lpbf_simulation.py at {rev}")


def route_block(text: str) -> str | None:
    norm = text.replace("\r\n", "\n")
    at = norm.find(THERMAL_ROUTE)
    return None if at < 0 else norm[at:at + ROUTE_BLOCK_CHARS]


def check(base: str, head: str) -> dict:
    base_sha = _git("rev-parse", "--verify", f"{base}^{{commit}}").strip()
    head_sha = _git("rev-parse", "--verify", f"{head}^{{commit}}").strip()
    changed = sorted(p for p in _git("diff", "--name-only", base_sha, head_sha).splitlines() if p)
    manifest = {f"python/{name}" for name in manifest_at(base_sha) + manifest_at(head_sha)}
    manifest_hits = sorted(set(changed) & manifest)
    served_hits = sorted(set(changed) & set(SERVED_ENTRY_MODULES))
    old_block = route_block(_git("show", f"{base_sha}:routes/physics.ts"))
    new_block = route_block(_git("show", f"{head_sha}:routes/physics.ts"))
    route_ok = old_block is not None and old_block == new_block
    return {
        "range": f"{base_sha}..{head_sha}",
        "p8Base": P8_BASE,
        "changedFiles": len(changed),
        "manifestFilesChanged": manifest_hits,
        "servedEntryModulesChanged": served_hits,
        "thermalRouteBlockUnchanged": route_ok,
        "pass": not manifest_hits and not served_hits and route_ok,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--range", default=f"{P8_BASE}..HEAD", help="<base>..<head> (default P8_BASE..HEAD)")
    args = parser.parse_args(argv)
    if args.range.count("..") != 1 or "..." in args.range:
        print("--range must have the form <base>..<head>", file=sys.stderr)
        return 2
    base, head = args.range.split("..")
    try:
        report = check(base or P8_BASE, head or "HEAD")
    except GitError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
