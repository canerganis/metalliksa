"""Verify stale calibration identity without loading any measured rows or solver.

python -I -B docs/research/scripts/engine_est_artifact_check.py --check
Reads only existing aggregate fitted artefacts, summaries and source bytes.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def live_fingerprint():
    tree = ast.parse((ROOT / "python/lpbf_simulation.py").read_text(encoding="utf-8"))
    values = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in ("VERSION", "IMPLEMENTATION_SOURCE_FILES"):
                    values[target.id] = ast.literal_eval(node.value)
    schema = "lpbf-thermal-implementation-manifest-v3-canonical-utf8-crlf"
    h = hashlib.sha256((schema+"\0"+values["VERSION"]+"\0").encode())
    for relative in sorted(values["IMPLEMENTATION_SOURCE_FILES"]):
        raw = (ROOT / "python" / relative).read_bytes()
        # Every file in this manifest is registered text; no source import occurs.
        raw.decode("utf-8"); raw = raw.replace(b"\r\n", b"\n")
        name = relative.encode()
        h.update(len(name).to_bytes(4, "big")); h.update(name)
        h.update(len(raw).to_bytes(8, "big")); h.update(raw)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(); p.add_argument("--check", action="store_true", required=True); p.parse_args()
    live = live_fingerprint()
    assert live == (ROOT / "python/lpbf_implementation_fingerprint.expected").read_text().strip()
    art = json.loads((ROOT / "data/calibration/lpbf-meltpool-calibration-v1.json").read_text(encoding="utf-8"))
    summary = json.loads((ROOT / "data/calibration/lpbf-meltpool-calibration-v1.summary.json").read_text(encoding="utf-8"))
    assert art["implementationHash"] != live, "The dated stale-artifact diagnosis must be updated"
    assert art["contentSha256"] == summary["contentSha256"]
    # Evaluate the live guard through AST with only its required synthetic dependencies.
    # All earlier integrity checks pass for a manufactured artefact. The tested branch
    # must reject a stale hash, accept the matching hash, and reject tampering first.
    source = ast.parse((ROOT / "python/lpbf_calibration_layer.py").read_text(encoding="utf-8"))
    nodes = [n for n in source.body if isinstance(n, ast.FunctionDef) and n.name == "load_calibration"]
    class CheckError(Exception): pass
    class CheckStale(CheckError): pass
    class Stats:
        @staticmethod
        def canonical_sha256(obj): return "config-ok"
    fake = {"schema": "test", "contentSha256": "content-ok", "config": {}, "configSha256": "config-ok",
            "evidenceKind": "screening-only", "proposedEvidenceKind": None,
            "cells": [], "implementationHash": "old"}
    class FakePath:
        def __init__(self, path): pass
        def read_text(self, **kwargs): return json.dumps(fake)
    ns = {"Any": object, "Dict": dict, "Optional": __import__("typing").Optional,
          "DEFAULT_PATH": "unused", "CALIBRATION_SCHEMA": "test", "ARTEFACT_KEYS": set(fake),
          "Path": FakePath, "json": json, "CalibrationError": CheckError, "CalibrationStale": CheckStale,
          "artefact_content_sha256": lambda _: "content-ok", "st": Stats,
          "config_sha256": lambda _: "config-ok", "CALIBRATION_CONFIG": {}, "EVIDENCE_KIND": "screening-only"}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "live-load-calibration", "exec"), ns)
    loader = ns["load_calibration"]
    try: loader(expected_impl_hash=live)
    except CheckStale: pass
    else: raise AssertionError("Stale artefact accepted")
    fake["implementationHash"] = live
    assert loader(expected_impl_hash=live)["implementationHash"] == live
    fake["contentSha256"] = "tampered"
    try: loader(expected_impl_hash=live)
    except CheckError as exc: assert "tampered" in str(exc)
    else: raise AssertionError("Tampered artefact accepted")
    print(json.dumps({"check": "pass", "liveFingerprint": live, "artifactFingerprint": art["implementationHash"],
                      "guardCases": 3, "summaryCells": summary["cells"]}, indent=2))


if __name__ == "__main__": main()
