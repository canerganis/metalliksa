"""Real SOL-C estimate-channel payloads for the TypeScript parser and panel tests.

``--write`` regenerates tests/fixtures/solidification-estimates/*.json from the real Python channel on synthetic
requests (no dataset, bands row or measured melt-pool value is read); ``--check`` requires the committed files to
equal a fresh generation byte for byte (python/test_lpbf_solidification_estimates.py runs the check).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "python"))

from tools.fixture_compare import serialized_equal  # cross-platform float noise tolerance, see that module

OUT = ROOT / "tests" / "fixtures" / "solidification-estimates"
BASE = {"beamDiameter_um": 80.0, "preheat_C": 80.0, "layerThickness_um": 40.0, "hatch_um": 100.0,
        "heatSource": "rosenthal"}
CASES = {
    # Ti64 at 200 W / 1000 mm/s: the Fabbro keyhole leg sets the served depth, so the default refuses Q-T.
    # The conduction-field surrogate is on by default there (maintainer decision on the Astra keyhole consult).
    "ti64-keyhole-default": ({"materialName": "Ti-6Al-4V", "power_W": 200.0, "speed_mm_s": 1000.0}, {}),
    "ti64-keyhole-surrogate-off": ({"materialName": "Ti-6Al-4V", "power_W": 200.0, "speed_mm_s": 1000.0},
                                   {"conductionSurrogate": False}),
    "ti64-surrogate-sensitivity": ({"materialName": "Ti-6Al-4V", "power_W": 200.0, "speed_mm_s": 1000.0},
                                   {"conductionSurrogate": True, "inputSensitivity": True}),
    "ti64-conduction": ({"materialName": "Ti-6Al-4V", "power_W": 120.0, "speed_mm_s": 1200.0}, {}),
    "alsi10mg-conduction": ({"materialName": "AlSi10Mg", "power_W": 300.0, "speed_mm_s": 1200.0}, {}),
    "in718-conduction": ({"materialName": "Inconel 718", "power_W": 200.0, "speed_mm_s": 900.0}, {}),
    "ss316l-conduction": ({"materialName": "316L Stainless Steel", "power_W": 200.0, "speed_mm_s": 900.0}, {}),
    "unknown-alloy": ({"materialName": "Unobtainium", "power_W": 200.0, "speed_mm_s": 900.0}, {}),
}


def generate():
    from lpbf_solidification_estimates import compute_solidification_estimates
    out = {}
    for name, (params, options) in CASES.items():
        payload = compute_solidification_estimates({"params": {**BASE, **params}, "options": options})
        out[name] = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    files = generate()
    if args.write:
        OUT.mkdir(parents=True, exist_ok=True)
        for name, text in files.items():
            (OUT / f"{name}.json").write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {len(files)} fixtures to {OUT}")
        return 0
    stale = [name for name, text in files.items()
             if not (OUT / f"{name}.json").exists()
             or (OUT / f"{name}.json").read_text(encoding="utf-8").replace("\r\n", "\n") != text
             and not serialized_equal((OUT / f"{name}.json").read_text(encoding="utf-8").replace("\r\n", "\n"), text)]
    if stale:
        print("stale fixtures: " + ", ".join(stale))
        return 1
    print(f"{len(files)} fixtures current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
