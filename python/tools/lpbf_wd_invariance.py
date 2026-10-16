"""Synthetic W/D invariance snapshot (SPEC_solidification_integration_2026-10-15.md, contract 3.5 item 2).

--capture OUT  calls calculate_meltpool_physics and compose_verdict directly for five alloys x three heat sources x
               the 49-cell synthetic grid (P 80..540 W, v 300..2400 mm/s, beam 80 um, preheat 80 C, layer 40 um,
               hatch 100 um) and writes one canonical JSON file with every float encoded by float.hex.
--compare A B  exit 0 only if the two files are byte-identical, else list the first 20 differing keys and exit 1.

Never calls the process-window endpoint, a dataset loader, or reads measured rows or bands files.
"""
import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

ALLOYS = [("Ti-6Al-4V", "ti6al4v"), ("AlSi10Mg", "alsi10mg"), ("Inconel 718", "in718"),
          ("316L Stainless Steel", "ss316l"), ("Inconel 625", "in625")]
SOURCES = ("rosenthal", "eagar-tsai", "goldak")
POWERS = [80 + i * (540 - 80) / 6 for i in range(7)]
SPEEDS = [300 + i * (2400 - 300) / 6 for i in range(7)]
FIELDS = ("meltPoolGeometry", "processParameters", "defectDiagnostics")


def enc(x):
    if isinstance(x, bool) or x is None or isinstance(x, (int, str)):
        return x
    if isinstance(x, float):
        return "f:" + x.hex()
    if isinstance(x, dict):
        return {str(k): enc(v) for k, v in sorted(x.items(), key=lambda kv: str(kv[0]))}
    if isinstance(x, (list, tuple)):
        return [enc(v) for v in x]
    if hasattr(x, "item"):
        return enc(x.item())
    return "repr:" + repr(x)


def digest(x):
    return hashlib.sha256(json.dumps(enc(x), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def capture(out):
    from lpbf_thermal_solver import calculate_meltpool_physics
    from lpbf_build_job_solver import compose_verdict
    cases = {}
    for name, aid in ALLOYS:
        for src in SOURCES:
            for P in POWERS:
                for v in SPEEDS:
                    key = f"{aid}|{src}|P={P.hex()}|v={v.hex()}"
                    t = calculate_meltpool_physics(name, P, v, 80.0, preheat_temp_C=80.0, layer_thickness_um=40.0,
                                                   hatch_spacing_um=100.0, heat_source=src)
                    geo = t["meltPoolGeometry"]
                    rec = {f: enc(t[f]) for f in FIELDS}
                    rec["processWindowGrid"] = enc((t.get("processWindowMap") or {}).get("grid"))
                    rec["regime"] = enc(geo.get("regime"))
                    rec["extentStatus"] = enc(geo.get("extentStatus"))
                    try:
                        vd = compose_verdict(t, aid)
                        rec["verdict"] = enc(vd.get("verdict"))
                        rec["verdictSha256"] = digest(vd)
                    except Exception as e:  # in625 is refused
                        rec["verdict"] = {"exception": type(e).__name__, "message": str(e)}
                        rec["verdictSha256"] = None
                    rec["thermalSansSolidificationKineticsSha256"] = digest(
                        {k: val for k, val in t.items() if k != "solidificationKinetics"})
                    cases[key] = rec
    data = json.dumps({"cases": cases}, sort_keys=True, separators=(",", ":")) + "\n"
    with open(out, "wb") as f:
        f.write(data.encode())
    print(f"cases {len(cases)} sha256 {hashlib.sha256(data.encode()).hexdigest()}")


def compare(a, b):
    ba, bb = open(a, "rb").read(), open(b, "rb").read()
    ca, cb = json.loads(ba)["cases"], json.loads(bb)["cases"]
    if ba == bb:
        print(f"byte-equal {len(ca)} cases")
        return 0
    diffs = []
    for k in sorted(set(ca) | set(cb)):
        if k not in ca or k not in cb:
            diffs.append(f"{k}: present in only one file")
            continue
        for f in sorted(set(ca[k]) | set(cb[k])):
            if ca[k].get(f) != cb[k].get(f):
                diffs.append(f"{k}: {f}")
    print(f"DIFFERENT: {len(diffs)} differing fields (first 20)")
    for d in diffs[:20]:
        print(" ", d)
    return 1


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--capture", metavar="OUT")
    ap.add_argument("--compare", nargs=2, metavar=("A", "B"))
    a = ap.parse_args()
    if a.capture:
        capture(a.capture)
        return 0
    if a.compare:
        return compare(*a.compare)
    ap.error("one of --capture or --compare required")


if __name__ == "__main__":
    sys.exit(main())
