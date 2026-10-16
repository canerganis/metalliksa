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


def _leaves(value, path=""):
    if isinstance(value, dict):
        for key, item in value.items():
            yield from _leaves(item, f"{path}.{key}" if path else key)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _leaves(item, f"{path}[{index}]")
    else:
        yield path, value


def compare(before, after):
    """Moved-value summary per alloy: every changed leaf is counted, W/D extremes and class changes are named."""
    if set(before["rows"]) != set(after["rows"]):
        raise ValueError("the two captures do not cover the same cases")
    out = {"schema": "sol-t-moved-values-compare-1",
           "scope": "Synthetic software outputs; a moved-value record, not an invariance or accuracy claim",
           "before": {"revision": before["revision"], "implementationHash": before["implementationHash"]},
           "after": {"revision": after["revision"], "implementationHash": after["implementationHash"]},
           "cases": len(before["rows"]), "endpoints": {"before": before["endpoints"], "after": after["endpoints"]},
           "alloys": {}}
    for case in sorted(before["rows"]):
        aid = case.split("/")[0]
        entry = out["alloys"].setdefault(aid, {
            "cases": 0, "casesWithAnyChange": 0, "changedLeavesByBlock": {}, "regimeChanges": [],
            "extentStatusChanges": [], "verdictChanges": [], "width_um": None, "depth_um": None})
        entry["cases"] += 1
        b, a = before["rows"][case], after["rows"][case]
        old, new = dict(_leaves(b)), dict(_leaves(a))
        changed = sorted(k for k in set(old) | set(new) if old.get(k, "<absent>") != new.get(k, "<absent>"))
        if changed:
            entry["casesWithAnyChange"] += 1
        for key in changed:
            block = key.split(".")[0].split("[")[0]
            entry["changedLeavesByBlock"][block] = entry["changedLeavesByBlock"].get(block, 0) + 1
        gb, ga = b["meltPoolGeometry"], a["meltPoolGeometry"]
        for name in ("regime", "extentStatus"):
            if gb.get(name) != ga.get(name):
                entry[f"{name}Changes"].append({"case": case, "before": gb.get(name), "after": ga.get(name)})
        if b["verdict"] != a["verdict"]:
            entry["verdictChanges"].append({"case": case, "before": b["verdict"], "after": a["verdict"]})
        for name in ("width_um", "depth_um"):
            x, y = gb.get(name), ga.get(name)
            if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
                if x != y:
                    entry.setdefault(f"{name}NonNumericChanges", []).append({"case": case, "before": x, "after": y})
                continue
            delta = round(y - x, 6)
            slot = entry[name] or {"min": None, "max": None, "changedCases": 0}
            slot["changedCases"] += delta != 0
            if slot["min"] is None or delta < slot["min"]["delta"]:
                slot["min"] = {"case": case, "before": x, "after": y, "delta": delta}
            if slot["max"] is None or delta > slot["max"]["delta"]:
                slot["max"] = {"case": case, "before": x, "after": y, "delta": delta}
            entry[name] = slot
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path)
    parser.add_argument("--compare", type=Path, nargs=2, metavar=("BEFORE", "AFTER"))
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.compare:
        before, after = (json.loads(path.read_text(encoding="utf-8")) for path in args.compare)
        text = json.dumps(compare(before, after), indent=1, allow_nan=False) + "\n"
        if args.out:
            args.out.write_text(text, encoding="utf-8", newline="\n")
            print(f"wrote {args.out}")
        else:
            print(text)
        return
    if not args.capture:
        parser.error("--capture or --compare is required")
    data = capture()
    args.capture.write_text(json.dumps(data, indent=1, allow_nan=False) + "\n", encoding="utf-8")
    print(f"wrote {len(data['rows'])} synthetic cases: {args.capture}")


if __name__ == "__main__":
    main()
