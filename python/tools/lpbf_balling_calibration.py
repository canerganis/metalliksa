#!/usr/bin/env python3
"""Balling-screen calibration table from a committed LPBF dataset comparison record.

Reads the per-row kernel predictions of docs/LPBF_DATASET_COMPARISON_*.json and reports, for the
Hofmann 316L balling flags (the only labelled balling set in the repo): AUC of each kernel's L/W, the
Youden threshold, the per-band balled fraction, TP/FP of candidate rules (including the shipped screen
lpbf_defect_diagnostics.balling_screen) and the rule counts on KU Leuven 316L+Ti64 (published REGIME
labels, no balling label), Lane IN625 and Totis Ti64 (no label). Comparison, not validation.

    python tools/lpbf_balling_calibration.py --record docs/LPBF_DATASET_COMPARISON_2026-10-07_waveb-physics.json \
        [--before <older record>] [--out docs/LPBF_BALLING_CALIBRATION_<date>.md]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from lpbf_defect_diagnostics import BALLING_LW_MODERATE, HOFMANN_EVIDENCE_LW_EDGES  # noqa: E402

# P7b: the served High band is gone; this calibration tool keeps scoring the recorded 5.5 evidence edge.
BALLING_LW_HIGH = HOFMANN_EVIDENCE_LW_EDGES[2]

HOFMANN = "hofmann-316l-2026"
KU = ("ku-leuven-316l-2021", "ku-leuven-ti64-2021")
LANE = ("lane-in625-2020",)
TOTIS = ("totis-ti64-2021",)
BINS = (0.0, 2.5, 3.0, 3.5, BALLING_LW_MODERATE, 4.2, 4.5, 5.0, BALLING_LW_HIGH, 6.0, math.inf)


def _ok(row, kernel="eagar-tsai"):
    p = row["predictions"][kernel]
    return p.get("extentStatus") == "computed" and p.get("length_um") and p.get("width_um")


def _lw(row, kernel="eagar-tsai"):
    p = row["predictions"][kernel]
    return p["length_um"] / p["width_um"]


def _dw(row):
    p = row["predictions"]["eagar-tsai"]
    return p["depth_um"] / p["width_um"]


def _auc(pairs):
    pos = [x for x, y in pairs if y]
    neg = [x for x, y in pairs if not y]
    if not pos or not neg:
        return None, len(pos), len(neg)
    wins = sum((a > b) + 0.5 * (a == b) for a in pos for b in neg)
    return wins / (len(pos) * len(neg)), len(pos), len(neg)


def analyse(record):
    rows = record["rows"]
    hof = [r for r in rows if r["dataset"] == HOFMANN]
    out = {"implementationHash": record.get("implementationHash"), "hofmannRows": len(hof)}
    auc = {}
    for k in ("rosenthal", "eagar-tsai", "goldak"):
        a_all = _auc([(_lw(r, k), r["measured"]["balling"]) for r in hof if _ok(r, k)])
        a_bare = _auc([(_lw(r, k), r["measured"]["balling"]) for r in hof if _ok(r, k) and r["inputs"]["layer_um"] == 0])
        auc[k] = {"all": a_all, "bare": a_bare}
    out["auc"] = auc
    he = [r for r in hof if _ok(r)]
    npos = sum(r["measured"]["balling"] for r in he)
    nneg = len(he) - npos
    best = (0.0, None)
    for t in sorted({round(_lw(r), 3) for r in he}):
        j = (sum(_lw(r) > t and r["measured"]["balling"] for r in he) / npos
             - sum(_lw(r) > t and not r["measured"]["balling"] for r in he) / nneg)
        if j > best[0]:
            best = (j, t)
    out["youden"] = {"J": round(best[0], 3), "threshold": best[1]}
    bins = {}
    for layer in (None, 0, 30, 60):
        sel = [r for r in he if layer is None or r["inputs"]["layer_um"] == layer]
        cells = []
        for a, b in zip(BINS, BINS[1:]):
            x = [r for r in sel if a < _lw(r) <= b]
            cells.append((a, b, sum(r["measured"]["balling"] for r in x), len(x)))
        bins["all" if layer is None else f"layer {layer} um"] = cells
    out["bins"] = bins
    rules = [(f"ET L/W > {t:g}", (lambda t: lambda r: _lw(r) > t)(t)) for t in (2.3, 3.85, 4.2, 4.5, 5.0, 5.5, 6.0)]
    rules += [(f"ET L/W > {t:g} and ET D/W < 1.2", (lambda t: lambda r: _lw(r) > t and _dw(r) < 1.2)(t))
              for t in (5.0, 5.5)]
    bare = [r for r in he if r["inputs"]["layer_um"] == 0]

    def other(ds, f):
        sel = [r for r in rows if r["dataset"] in ds and _ok(r)]
        return f"{sum(1 for r in sel if f(r))}/{len(sel)}"

    table = []
    for name, f in rules:
        table.append({
            "rule": name,
            "tp": sum(1 for r in he if f(r) and r["measured"]["balling"]), "positives": npos,
            "fp": sum(1 for r in he if f(r) and not r["measured"]["balling"]), "negatives": nneg,
            "bareTp": sum(1 for r in bare if f(r) and r["measured"]["balling"]),
            "bareFp": sum(1 for r in bare if f(r) and not r["measured"]["balling"]),
            "barePositives": sum(r["measured"]["balling"] for r in bare),
            "bareNegatives": len(bare) - sum(r["measured"]["balling"] for r in bare),
            "kuFlagged": other(KU, f), "laneFlagged": other(LANE, f), "totisFlagged": other(TOTIS, f),
        })
    out["rules"] = table
    rc = [r for r in hof if _ok(r, "rosenthal")]
    out["rosenthal38"] = {
        "computedRows": len(rc), "positives": sum(r["measured"]["balling"] for r in rc),
        "tp": sum(1 for r in rc if _lw(r, "rosenthal") > 3.8 and r["measured"]["balling"]),
        "fp": sum(1 for r in rc if _lw(r, "rosenthal") > 3.8 and not r["measured"]["balling"]),
    }
    sens = {}
    for scale in (0.9, 1.1):
        sens[str(scale)] = {
            "tp": sum(1 for r in he if _lw(r) * scale > BALLING_LW_HIGH and r["measured"]["balling"]),
            "fp": sum(1 for r in he if _lw(r) * scale > BALLING_LW_HIGH and not r["measured"]["balling"]),
        }
    out["highThresholdLWScaleSensitivity"] = sens
    spots = {}
    for s in sorted({r["inputs"]["beamDiameter_um"] for r in he}):
        sel = [r for r in he if r["inputs"]["beamDiameter_um"] == s]
        spots[f"{s:g}"] = {
            "tp": sum(1 for r in sel if _lw(r) > BALLING_LW_HIGH and r["measured"]["balling"]),
            "positives": sum(r["measured"]["balling"] for r in sel),
            "fp": sum(1 for r in sel if _lw(r) > BALLING_LW_HIGH and not r["measured"]["balling"]),
            "negatives": len(sel) - sum(r["measured"]["balling"] for r in sel),
        }
    out["highThresholdBySpot_um"] = spots
    return out


def _fmt_auc(a):
    return "n/a" if a[0] is None else f"{a[0]:.3f} ({a[1]}/{a[2]})"


def markdown(results):
    lines = ["# LPBF balling screen: calibration table (generated by `python/tools/lpbf_balling_calibration.py`)", "",
             "**Comparison, not validation.** Labels: Hofmann et al. 316L balling flag (Zenodo 10.5281/zenodo.16979848). "
             "KU Leuven rows carry published *regime* labels (conduction/transition/keyhole), not balling labels; Lane "
             "IN625 and Totis Ti64 carry no balling label. Kernel geometry: flat-plate absorptivity (estimated). "
             f"Shipped screen: Eagar–Tsai L/W > {BALLING_LW_MODERATE:.3f} Moderate (advisory); the former High edge "
             f"{BALLING_LW_HIGH} is scored here as recorded evidence only (no served High band since P7b). "
             "experimentalValidation=false.", ""]
    for label, r in results:
        lines += [f"## {label} (implementation {str(r['implementationHash'])[:8]})", "",
                  "| kernel | AUC L/W, all (pos/neg) | AUC L/W, bare plate |", "|---|---|---|"]
        for k, v in r["auc"].items():
            lines.append(f"| {k} | {_fmt_auc(v['all'])} | {_fmt_auc(v['bare'])} |")
        lines += ["", f"Youden threshold (Eagar–Tsai L/W): {r['youden']['threshold']} (J = {r['youden']['J']}). "
                  f"Retired rule Rosenthal L/W > 3.8 on the {r['rosenthal38']['computedRows']} Rosenthal-computed rows: "
                  f"TP {r['rosenthal38']['tp']}/{r['rosenthal38']['positives']}, "
                  f"FP {r['rosenthal38']['fp']}/{r['rosenthal38']['computedRows'] - r['rosenthal38']['positives']}.", "",
                  "| Eagar–Tsai L/W band | " + " | ".join(r["bins"].keys()) + " |",
                  "|---|" + "---|" * len(r["bins"])]
        keys = list(r["bins"].keys())
        for i in range(len(BINS) - 1):
            a, b = BINS[i], BINS[i + 1]
            cells = []
            for k in keys:
                _, _, bal, n = r["bins"][k][i]
                cells.append(f"{bal}/{n}" if n else "-")
            lines.append(f"| ({a:.2f}, {b:.2f}] | " + " | ".join(cells) + " |")
        lines += ["", "| rule | Hofmann TP | Hofmann FP | bare TP | bare FP | KU 316L+Ti64 flagged | Lane IN625 flagged | Totis flagged |",
                  "|---|---|---|---|---|---|---|---|"]
        for t in r["rules"]:
            lines.append(f"| {t['rule']} | {t['tp']}/{t['positives']} | {t['fp']}/{t['negatives']} | "
                         f"{t['bareTp']}/{t['barePositives']} | {t['bareFp']}/{t['bareNegatives']} | {t['kuFlagged']} | "
                         f"{t['laneFlagged']} | {t['totisFlagged']} |")
        s = r["highThresholdLWScaleSensitivity"]
        lines += ["", f"High threshold {BALLING_LW_HIGH} with all L/W scaled x0.9: TP {s['0.9']['tp']}, FP {s['0.9']['fp']}; "
                  f"x1.1: TP {s['1.1']['tp']}, FP {s['1.1']['fp']}. Per spot diameter (um): "
                  + "; ".join(f"{k}: TP {v['tp']}/{v['positives']} FP {v['fp']}/{v['negatives']}"
                              for k, v in r["highThresholdBySpot_um"].items()) + ".", ""]
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--record", required=True)
    ap.add_argument("--before", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    results = []
    for label, path in (("Before (earlier record)", args.before), ("Current record", args.record)):
        if path:
            with open(path, encoding="utf-8") as fh:
                results.append((f"{label}: {os.path.basename(path)}", analyse(json.load(fh))))
    md = markdown(results)
    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(md)
    else:
        sys.stdout.write(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
