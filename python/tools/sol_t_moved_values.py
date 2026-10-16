"""Synthetic SOL-T moved-value receipt; never reads measured rows or overlays."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "python"))


def capture_verdict(result, alloy_id):
    """Only IN625's served refusal is an admitted capture outcome."""
    from lpbf_build_job_solver import compose_verdict
    try:
        return compose_verdict(result, alloy_id)["verdict"]
    except ValueError as exc:
        if alloy_id != "in625":
            raise
        return {"verdictStatus": "refused", "error": f"{type(exc).__name__}: {exc}"}


def capture():
    from four_alloy_materials import thermal_props
    from lpbf_thermal_solver import (SECONDARY_THERMOPHYSICAL_DB, calculate_meltpool_physics,
                                     resolve_conduction_kernel)
    from lpbf_simulation import implementation_fingerprint
    names = {"ti6al4v": "Ti-6Al-4V", "in718": "Inconel 718", "ss316l": "316L Stainless Steel",
             "alsi10mg": "AlSi10Mg", "in625": "Inconel 625"}
    endpoints, rows = {}, {}
    for aid, name in names.items():
        props = thermal_props(name) or SECONDARY_THERMOPHYSICAL_DB[name]
        endpoints[aid] = {"solidus_K": props["solidus_C"] + 273.15,
                          "liquidus_K": props["liquidus_C"] + 273.15,
                          "conduction20C": resolve_conduction_kernel(name, props, None, 20)[:4]}
        for kernel in ("rosenthal", "eagar-tsai", "goldak"):
            for power in (80, 150, 220, 300, 380, 460, 540):
                for speed in (300, 600, 900, 1200, 1600, 2000, 2400):
                    result = calculate_meltpool_physics(name, power, speed, 80, 80, 40, 100,
                                                       heat_source=kernel)
                    rows[f"{aid}/{kernel}/{power}/{speed}"] = {
                        key: result[key] for key in ("meltPoolGeometry", "processParameters",
                                                     "processWindowMap", "defectDiagnostics")}
                    rows[f"{aid}/{kernel}/{power}/{speed}"]["verdict"] = capture_verdict(result, aid)
    return {"schema": "sol-t-moved-values-1", "scope": "Synthetic software outputs; moved-value record, no invariance or accuracy claim",
            "revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "implementationHash": implementation_fingerprint(), "endpoints": endpoints, "rows": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path, required=True)
    args = parser.parse_args()
    data = capture()
    args.capture.write_text(json.dumps(data, indent=1, allow_nan=False) + "\n", encoding="utf-8")
    print(f"wrote {len(data['rows'])} synthetic cases: {args.capture}")


if __name__ == "__main__":
    main()
