#!/usr/bin/env python3
"""Capture real SOL-A Python payloads for cross-tier contract checks.

Requests are synthetic process examples, not experimental validation. CALPHAD
captures belong to SOL-B. Only elapsed timings are removed; identities, reason
codes, sources and computed values remain producer output.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PYTHON = Path(__file__).resolve().parents[1]
if str(PYTHON) not in sys.path:
    sys.path.insert(0, str(PYTHON))
FIXTURE_DIR = PYTHON.parent / "tests" / "fixtures" / "solidification-payloads"
TIMING_KEYS = frozenset(("computeTimeMs", "computeMs", "pythonDurationMs"))


def without_timings(value):
    """JSON-normalize producer output, excluding explicitly volatile timings."""
    if isinstance(value, dict):
        return {key: without_timings(item) for key, item in value.items() if key not in TIMING_KEYS}
    if isinstance(value, (list, tuple)):
        return [without_timings(item) for item in value]
    return value


def generate_payloads():
    from lpbf_gr_solidification import run_gr_solidification
    from lpbf_thermal_solver import calculate_meltpool_physics
    from lpbf_worker_rpc import _rpc_solidification_microstructure
    from test_lpbf_build_job import (
        kinetics_fixture_blocks, microstructure_fixture_blocks, segregation_fixture_blocks,
    )

    payloads = {}
    materials = {
        "in718": "Inconel 718", "in625": "Inconel 625", "ss316l": "316L Stainless Steel",
        "alsi10mg": "AlSi10Mg", "ti6al4v": "Ti-6Al-4V",
    }
    for alloy, material in materials.items():
        thermal = calculate_meltpool_physics(material, 150, 1200, 80, 80, 40, 110, heat_source="rosenthal")
        payloads[f"thermal-{alloy}"] = thermal["solidificationKinetics"]
    keyhole = calculate_meltpool_physics("Inconel 718", 285, 960, 80, 80, 40, 110, heat_source="rosenthal")
    payloads["thermal-keyhole"] = keyhole["solidificationKinetics"]
    payloads["build-job-kinetics"] = kinetics_fixture_blocks()
    payloads["build-job-microstructure"] = microstructure_fixture_blocks()
    payloads["build-job-segregation"] = segregation_fixture_blocks()
    common = {"beamDiameter_um": 80, "layer_um": 40, "hatch_um": 110, "preheatTemp_C": 80}
    for alloy, name in (("in718", "in718"), ("ti6al4v", "ti6al4v"), ("unknown alloy", "unknown")):
        payloads[f"gr-point-{name}"] = run_gr_solidification({
            "mode": "point", "alloyId": alloy, "power_W": 150, "speed_mm_s": 1200, **common,
        })
    payloads["gr-map-in718"] = run_gr_solidification({
        "mode": "map", "alloyId": "in718", "powers": [150, 285], "speeds": [960, 1200], **common,
    })
    params = {
        "materialName": "Inconel 718", "power_W": 150, "speed_mm_s": 1200,
        "beamDiameter_um": 80, "preheat_C": 80, "layerThickness_um": 40,
        "hatch_um": 110, "heatSource": "rosenthal",
    }
    payloads["worker-result"] = _rpc_solidification_microstructure({"payload": {"params": params}})
    payloads["worker-cfd-refused"] = _rpc_solidification_microstructure({"payload": {
        "params": params, "cfdResult": {"solidificationMicrostructure": {
            "meanG_K_m": 1.0e6, "meanR_m_s": 0.01,
        }},
    }})
    return without_timings(payloads)


def serialized_payloads():
    return {name + ".json": json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False,
                                       allow_nan=False) + "\n"
            for name, payload in generate_payloads().items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="Regenerate committed SOL-A fixtures")
    mode.add_argument("--check", action="store_true", help="Check committed SOL-A fixtures (the default)")
    args = parser.parse_args()
    expected = serialized_payloads()
    if args.write:
        FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
        for name, content in expected.items():
            (FIXTURE_DIR / name).write_text(content, encoding="utf-8", newline="\n")
        print(f"Wrote {len(expected)} SOL-A fixtures to {FIXTURE_DIR}")
    else:
        actual = {path.name: path.read_text(encoding="utf-8") for path in FIXTURE_DIR.glob("*.json")}
        if actual != expected:
            parser.exit(1, "SOL-A fixtures are stale; rerun with --write\n")
        print(f"PASS: {len(expected)} SOL-A fixtures match the real Python producers")


if __name__ == "__main__":
    main()
