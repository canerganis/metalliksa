"""Shared, git-independent utilities for software-only solidification audit checks."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def source_identity(paths):
    """UTF-8 source content identity; canonical LF bytes, never checkout HEAD."""
    return {str(p.relative_to(ROOT)).replace("\\", "/"):
            hashlib.sha256(p.read_text(encoding="utf-8").replace("\r\n", "\n")
                           .replace("\r", "\n").encode("utf-8")).hexdigest()
            for p in sorted(set(paths))}


def emit(report, paths):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Software-only check: stdout by default, no implicit file writes")
    parser.add_argument("--output", type=Path, help="Explicit JSON destination (may refresh a tracked artifact)")
    args = parser.parse_args()
    report.update(checkKind="synthetic software and algebra checks", experimentalValidation=False,
                  readsMeasuredMeltPoolDepths=False, sourceIdentityAlgorithm="sha256-utf8-lf-v1",
                  sourceSha256=source_identity(list(paths) + [Path(__file__)]))
    rendered = json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
        print(json.dumps({"output": str(args.output), "checks": report["checks"]}, sort_keys=True))
    else:
        print(rendered, end="")


def require(checks):
    failed = [name for name, passed in checks.items() if passed is not True]
    if failed:
        raise AssertionError("Software audit failed: " + ", ".join(failed))
