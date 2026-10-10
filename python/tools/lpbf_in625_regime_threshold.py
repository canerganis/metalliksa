#!/usr/bin/env python3
"""IN625 per-alloy keyhole-mode threshold on the app's normalised enthalpy (research, SCREENING ONLY, NOT VALIDATION).

Implements docs/research/PREDECLARED_in625_regime_2026-10-11.md. Nothing frozen is edited and nothing here changes a
depth number: the harness only reads the app index (lpbf_public_datasets.normalized_enthalpy, the same formula as
lpbf_thermal_solver.py) and the committed measured melt-pool geometry.

Commands (repo root, PYTHONDONTWRITEBYTECODE=1):
    python -B python/tools/lpbf_in625_regime_threshold.py build-ledger
        Transcribes the IN625 unit ledger (process inputs, measured width and depth, uncertainties, split) from the
        committed NIST mds2-2923 workbook and the committed Lane 2020 tables. No index, no label, no fit.
    python -B python/tools/lpbf_in625_regime_threshold.py run --declared-run
        The one declared run. Refuses to start unless the declaration and this runner are committed and unmodified,
        the ledger hash matches the pin, and no results file exists yet.

The threshold is fitted ONLY on units whose split is "fit" (fit_threshold rejects anything else). Held-out labels are
computed after the fit and are used only to score.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

TOOLS_DIR = Path(__file__).resolve().parent
PYTHON_DIR = TOOLS_DIR.parent
REPO_ROOT = PYTHON_DIR.parent
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

import lpbf_public_datasets as pds  # noqa: E402

# ---- Declaration constants (section numbers refer to the PREDECLARED file) ------------------------------------------
DECLARATION = REPO_ROOT / "docs" / "research" / "PREDECLARED_in625_regime_2026-10-11.md"
RESULTS_JSON = REPO_ROOT / "docs" / "research" / "RESULTS_in625_regime_2026-10-11.json"
LEDGER_DIR = REPO_ROOT / "data" / "benchmark" / "in625-regime-ledger-2026-10-11"
LEDGER_CSV = LEDGER_DIR / "units.csv"
LEDGER_SHA256 = "6957b6f3c9ac809b2a7221f4e07be7c26c410d873e8f01e8b2ca04b5a088424a"
MDS2_WORKBOOK = REPO_ROOT / "data" / "benchmark" / "nist-mds2-2923-in718" / "official" / "Master_TrackList_Measurements.xlsx"
MDS2_WORKBOOK_SHA256 = "6cd32669f5c84cdb9e90890ba40ddc5548c85b0dbb95cf038f2f6fc69da67a52"

MATERIAL = "Inconel 625"
PREHEAT_C = 20.0               # section 3: repo dataset convention (pds.ASSUMED_PREHEAT_C), bare plates
PREHEAT_SENSITIVITY_C = 27.0   # Weaver 2022 Table 2 T0 = 300.15 K, sensitivity only
BASELINE_KEYHOLE_CUT = 20.0    # lpbf_thermal_solver.ENTHALPY_KEYHOLE at b22657f5
BASELINE_TRANSITION_CUT = 15.0  # lpbf_thermal_solver.ENTHALPY_TRANSITION at b22657f5 (not evaluated)

# Section 4: regime truth (morphology). Primary: King et al. 2014 Sec. 5.2, depth greater than half width.
# Secondary (sensitivity): Weaver et al. 2022 Sec. 4.1, depth greater than the spot radius D4sigma/2.
TRUTH_RATIO_CUT = 1.0

# Section 3: Weaver et al. 2022 convention (Eq. 3, Eq. 4, Table 2, Fig. 6 caption A = 0.4), sigma = D4sigma/4.
WEAVER_CONVENTION = {"A": 0.4, "rho_kg_m3": 8440.0, "cp_J_kgK": 719.92, "k_W_mK": 28.78,
                     "Tm_K": 1563.15, "T0_K": 300.15}
WEAVER_THRESHOLD = 30.0        # Weaver 2022 Sec. 4.2 ("approximately 30", from King 2014 316L)
KING_BAND = (26.0, 34.0)       # King 2014 Sec. 5.3 / 5.6, 30 +/- 4

# Section 7: PASS rule constants.
PASS_MIN_BA = 0.80
PASS_MIN_BA_GAIN = 0.15
PASS_MIN_ERROR_REDUCTION = 2
PASS_LOO_MIN_BA = 0.75
MIN_HELDOUT_PER_CLASS = 3
MIN_FIT_PER_CLASS = 5
ADOPTION_DECIMALS = 1

LANE_SOURCE_ID = "lane-in625-2020"
MDS2_SOURCE_ID = "nist-mds2-2923"
LANE_CBM_MACHINE = "EOS M270 (CBM)"   # Lane 2020 Sec. 1: "an EOS M270 commercial build machine (CBM)"
# mds2 README: depth/width variability along a track estimated at 2 % / 5 %; reused for the Lane ambiguity band only.
WIDTH_VARIABILITY = 0.02
DEPTH_VARIABILITY = 0.05

LEDGER_COLUMNS = ["unit_id", "source", "campaign", "machine", "machine_family", "power_W", "speed_mm_s", "d4sigma_um",
                  "beam_diameter_source", "n_measurements", "width_um", "depth_um", "width_U_um", "depth_U_um",
                  "uncertainty_kind", "split", "split_reason", "locator"]


# ---- Ledger (transcription only; no index, no label) ----------------------------------------------------------------
def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(Path(path).read_bytes())


def machine_family(machine: str) -> str:
    return "EOS M270" if machine.startswith("EOS M270") else machine


def condition_key(machine: str, power_W: float, speed_mm_s: float, d4sigma_um: float) -> Tuple[str, float, float, float]:
    return (machine_family(machine), round(float(power_W), 1), round(float(speed_mm_s), 1), round(float(d4sigma_um), 1))


def assign_split(source: str, machine: str, key: Tuple[str, float, float, float],
                 heldout_keys: Iterable[Tuple[str, float, float, float]]) -> Tuple[str, str]:
    """Section 5. Label-blind: uses only source, machine and the process condition, never width or depth."""
    if source == LANE_SOURCE_ID:
        return "heldout", "Lane 2020 (separately published AM-Bench 2018 campaign)"
    if source == MDS2_SOURCE_ID and machine == "AMMT":
        return "heldout", "mds2-2923 AMMT (measured spot, different machine)"
    if source == MDS2_SOURCE_ID and machine_family(machine) == "EOS M270":
        if key in set(heldout_keys):
            return "excluded", "same machine and process condition as a held-out Lane CBM unit"
        return "fit", "mds2-2923 EOS M270 (estimated spot)"
    raise ValueError(f"no split rule for source {source!r}, machine {machine!r}")


def _sheet_rows(cells: Dict[str, str]) -> List[List[str]]:
    rows: Dict[int, Dict[int, str]] = {}
    for ref, value in cells.items():
        col = re.match(r"[A-Z]+", ref).group(0)
        rows.setdefault(int(ref[len(col):]), {})[pds._col_index(ref)] = value
    width = max(max(r) for r in rows.values())
    return [[rows[r].get(c, "") for c in range(1, width + 1)] for r in sorted(rows)]


MDS2_SUMMARY_HEADERS = {
    "material": "Material", "machine": "Machine", "d4sigma": "Estimated D4σ Spot Diameter (µm)",
    "power": "Laser Power (W)", "speed": "Scan Speed (mm/s)", "n": "no. of measurements",
    "width": "Average Width (µm)", "width_U": "Width: Combined, Expanded uncertainty (µm); U (k=2)",
    "depth": "Average Depth (µm)", "depth_U": "Depth: Combined, Expanded uncertainty (µm); U (k-2)",
}


def mds2_in625_rows(workbook: Path = MDS2_WORKBOOK) -> List[Dict[str, str]]:
    data = Path(workbook).read_bytes()
    if _sha256_bytes(data) != MDS2_WORKBOOK_SHA256:
        raise ValueError("mds2-2923 workbook sha256 mismatch")
    table = _sheet_rows(pds._read_xlsx_grids(data)["Summary"])
    header = {name: i for i, name in enumerate(table[0]) if name}
    missing = [h for h in MDS2_SUMMARY_HEADERS.values() if h not in header]
    if missing:
        raise ValueError(f"mds2 Summary headers missing: {missing}")
    out = []
    for line, row in enumerate(table[1:], start=2):
        if row[header["Material"]] != "IN625":
            continue
        item = {k: row[header[h]] for k, h in MDS2_SUMMARY_HEADERS.items()}
        item["sheet_row"] = str(line)
        out.append(item)
    return out


def build_ledger_rows() -> List[Dict[str, str]]:
    lane = pds.load_lane_in625(verify=True)
    lane_inputs: Dict[str, Dict[str, Any]] = {}
    for r in lane["rows"]:
        cls = f"{r['machine']}-{r['case']}"
        inp = (r["table3Power_W"], r["speed_mm_s"], r["beamDiameter_um"])
        if cls in lane_inputs and lane_inputs[cls]["inputs"] != inp:
            raise ValueError(f"Lane Table 3 inputs differ within class {cls}")
        lane_inputs[cls] = {"inputs": inp}
    lane_units = []
    for s in lane["provenance"]["table4"]:
        cls = s["class"]
        machine = "AMMT" if cls.startswith("AMMT") else LANE_CBM_MACHINE
        power, speed, d4 = lane_inputs[cls]["inputs"]
        w, d = float(s["width_mean_um"]), float(s["depth_mean_um"])
        uw = math.hypot(2.0 * float(s["width_Umean_um"]), WIDTH_VARIABILITY * w)
        ud = math.hypot(2.0 * float(s["depth_Umean_um"]), DEPTH_VARIABILITY * d)
        lane_units.append({"unit_id": f"lane2020-{cls}", "source": LANE_SOURCE_ID, "campaign": "AMB2018-02",
                           "machine": machine, "power_W": f"{power:g}", "speed_mm_s": f"{speed:g}",
                           "d4sigma_um": f"{d4:g}", "beam_diameter_source": "measured (Lane 2020 Table 1)",
                           "n_measurements": f"{s['width_N']}/{s['depth_N']}", "width_um": s["width_mean_um"],
                           "depth_um": s["depth_mean_um"], "width_U_um": f"{uw:.4f}", "depth_U_um": f"{ud:.4f}",
                           "uncertainty_kind": "2 x Table 4 Umean (+) mds2 README variability 2 %/5 %",
                           "locator": f"Lane 2020 Table 4 class {cls}; power, speed, D4sigma from Table 3"})
    heldout_keys = [condition_key(u["machine"], float(u["power_W"]), float(u["speed_mm_s"]), float(u["d4sigma_um"]))
                    for u in lane_units]
    units = []
    for u in lane_units:
        key = condition_key(u["machine"], float(u["power_W"]), float(u["speed_mm_s"]), float(u["d4sigma_um"]))
        u["split"], u["split_reason"] = assign_split(u["source"], u["machine"], key, heldout_keys)
        units.append(u)
    for r in mds2_in625_rows():
        machine = r["machine"]
        key = condition_key(machine, float(r["power"]), float(r["speed"]), float(r["d4sigma"]))
        split, reason = assign_split(MDS2_SOURCE_ID, machine, key, heldout_keys)
        tag = "ammt" if machine == "AMMT" else "eos"
        units.append({"unit_id": f"mds2-{tag}-row{int(r['sheet_row']):02d}", "source": MDS2_SOURCE_ID,
                      "campaign": "Weaver 2022 spot-size series", "machine": machine, "power_W": r["power"],
                      "speed_mm_s": r["speed"], "d4sigma_um": r["d4sigma"],
                      "beam_diameter_source": "measured" if machine == "AMMT" else "estimated (caustic model)",
                      "n_measurements": r["n"], "width_um": r["width"], "depth_um": r["depth"],
                      "width_U_um": r["width_U"], "depth_U_um": r["depth_U"], "uncertainty_kind": "U (k=2) as published",
                      "split": split, "split_reason": reason,
                      "locator": f"mds2-2923 Master_TrackList_Measurements.xlsx, sheet Summary, row {r['sheet_row']}"})
    for u in units:
        u["machine_family"] = machine_family(u["machine"])
    return units


def ledger_csv_text(units: Sequence[Dict[str, str]]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=LEDGER_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for u in units:
        writer.writerow({k: u[k] for k in LEDGER_COLUMNS})
    return buf.getvalue()


def load_ledger(path: Path = LEDGER_CSV, verify: bool = True) -> List[Dict[str, Any]]:
    data = Path(path).read_bytes()
    if verify and _sha256_bytes(data) != LEDGER_SHA256:
        raise ValueError(f"ledger sha256 mismatch: {_sha256_bytes(data)} != pinned {LEDGER_SHA256}")
    rows = list(csv.DictReader(io.StringIO(data.decode("utf-8"))))
    if not rows or list(rows[0].keys()) != LEDGER_COLUMNS:
        raise ValueError("ledger columns differ from LEDGER_COLUMNS")
    out = []
    for r in rows:
        item: Dict[str, Any] = dict(r)
        for k in ("power_W", "speed_mm_s", "d4sigma_um", "width_um", "depth_um", "width_U_um", "depth_U_um"):
            item[k] = float(r[k])
        out.append(item)
    return out


# ---- Index, convention, truth --------------------------------------------------------------------------------------
def repo_index(unit: Dict[str, Any], preheat_C: float = PREHEAT_C, power_W: Optional[float] = None) -> float:
    """App normalised enthalpy (repo convention: r = D4sigma/2, flat A, solid k and cp, hs = rho cp (T_liq - T0))."""
    return pds.normalized_enthalpy(MATERIAL, float(unit["power_W"] if power_W is None else power_W),
                                   float(unit["speed_mm_s"]), float(unit["d4sigma_um"]), preheat_C)


def repo_per_weaver_factor(preheat_C: float = PREHEAT_C) -> float:
    """H_repo / H_Weaver for the same P, u and D4sigma (section 3). Weaver: sigma = D4sigma/4, Table 2 properties."""
    props = pds.screening_props(MATERIAL)
    w = WEAVER_CONVENTION
    d_weaver = w["k_W_mK"] / (w["rho_kg_m3"] * w["cp_J_kgK"])
    alpha_repo = props["thermal_conductivity_W_mK"] / (props["density_kg_m3"] * props["specific_heat_J_kgK"])
    hs_weaver = w["rho_kg_m3"] * w["cp_J_kgK"] * (w["Tm_K"] - w["T0_K"])
    hs_repo = props["density_kg_m3"] * props["specific_heat_J_kgK"] * max(50.0, props["liquidus_C"] - preheat_C)
    return ((props["absorptivity_IR"] / w["A"]) * (hs_weaver / hs_repo) * math.sqrt(d_weaver / alpha_repo)
            * (0.25 / 0.5) ** 1.5)


def weaver_index(unit: Dict[str, Any]) -> float:
    """Weaver 2022 Eq. 3 with Eq. 4 and Table 2 (A = 0.4, Fig. 6), sigma = D4sigma/4."""
    w = WEAVER_CONVENTION
    sigma = float(unit["d4sigma_um"]) * 1e-6 / 4.0
    d = w["k_W_mK"] / (w["rho_kg_m3"] * w["cp_J_kgK"])
    hs = w["rho_kg_m3"] * w["cp_J_kgK"] * (w["Tm_K"] - w["T0_K"])
    u = float(unit["speed_mm_s"]) * 1e-3
    return w["A"] * float(unit["power_W"]) / (hs * math.sqrt(math.pi * d * u * sigma ** 3))


def half_width_ratio(unit: Dict[str, Any]) -> float:
    return float(unit["depth_um"]) / (0.5 * float(unit["width_um"]))


def spot_radius_ratio(unit: Dict[str, Any]) -> float:
    return float(unit["depth_um"]) / (0.5 * float(unit["d4sigma_um"]))


def truth_keyhole(unit: Dict[str, Any]) -> bool:
    """Primary truth (section 4): depth greater than half width (King 2014 Sec. 5.2)."""
    return half_width_ratio(unit) > TRUTH_RATIO_CUT


def truth_keyhole_secondary(unit: Dict[str, Any]) -> bool:
    """Secondary truth (section 4): depth greater than the spot radius D4sigma/2 (Weaver 2022 Sec. 4.1)."""
    return spot_radius_ratio(unit) > TRUTH_RATIO_CUT


def is_ambiguous(unit: Dict[str, Any]) -> bool:
    """Ratio interval (expanded uncertainty, first-order) contains the cut 1.0."""
    ratio = half_width_ratio(unit)
    rel = math.hypot(float(unit["depth_U_um"]) / float(unit["depth_um"]), float(unit["width_U_um"]) / float(unit["width_um"]))
    return abs(ratio - TRUTH_RATIO_CUT) <= ratio * rel


# ---- Fit (fit split only) -------------------------------------------------------------------------------------------
class DegenerateFit(ValueError):
    pass


def predict_keyhole(index: float, threshold: float) -> bool:
    return index >= threshold


def confusion(indices: Sequence[float], labels: Sequence[bool], threshold: float) -> Dict[str, Any]:
    tp = fn = tn = fp = 0
    for h, y in zip(indices, labels):
        p = predict_keyhole(h, threshold)
        if y and p:
            tp += 1
        elif y:
            fn += 1
        elif p:
            fp += 1
        else:
            tn += 1
    pos, neg = tp + fn, tn + fp
    recall = tp / pos if pos else None
    spec = tn / neg if neg else None
    ba = 0.5 * (recall + spec) if pos and neg else None
    return {"threshold": threshold, "tp": tp, "fn": fn, "tn": tn, "fp": fp, "n": pos + neg, "errors": fn + fp,
            "keyholeRecall": recall, "nonKeyholeSpecificity": spec, "balancedAccuracy": ba}


def fit_threshold(fit_units: Sequence[Dict[str, Any]], index_fn=None, label_fn=None) -> Dict[str, Any]:
    """Section 6. Maximise balanced accuracy on the fit split over the midpoints between consecutive distinct fit
    indices; ties: widest gap between the two bracketing fit indices, then the lower threshold."""
    index_fn = index_fn or repo_index
    label_fn = label_fn or truth_keyhole
    if any(u.get("split") != "fit" for u in fit_units):
        raise ValueError("fit_threshold accepts fit-split units only")
    pairs = sorted((index_fn(u), bool(label_fn(u))) for u in fit_units)
    n_pos = sum(1 for _, y in pairs if y)
    n_neg = len(pairs) - n_pos
    if n_pos < 1 or n_neg < 1:
        raise DegenerateFit(f"fit split needs both classes (keyhole {n_pos}, not keyhole {n_neg})")
    distinct = sorted({h for h, _ in pairs})
    if len(distinct) < 2:
        raise DegenerateFit("fit split has a single distinct index value")
    indices = [h for h, _ in pairs]
    labels = [y for _, y in pairs]
    best = None
    for lo, hi in zip(distinct[:-1], distinct[1:]):
        c = 0.5 * (lo + hi)
        ba = confusion(indices, labels, c)["balancedAccuracy"]
        key = (round(ba, 12), round(hi - lo, 12), -c)
        if best is None or key > best[0]:
            best = (key, c, lo, hi, ba)
    _, c, lo, hi, ba = best
    n_ties = sum(1 for a, b in zip(distinct[:-1], distinct[1:])
                 if abs(confusion(indices, labels, 0.5 * (a + b))["balancedAccuracy"] - ba) < 1e-12)
    return {"threshold": c, "bracketLower": lo, "bracketUpper": hi, "fitBalancedAccuracy": ba,
            "fitConfusion": confusion(indices, labels, c), "nFit": len(pairs), "nFitKeyhole": n_pos,
            "nFitNotKeyhole": n_neg, "nTiedMaxBA": n_ties}


def adopted(threshold: float) -> float:
    return round(threshold, ADOPTION_DECIMALS)


def heldout_admissible_interval(units: Sequence[Dict[str, Any]], threshold: float, index_fn=None) -> Dict[str, Any]:
    """Section 7 (amendment B1). Every cut c with lowerExclusive < c <= upperInclusive gives the same held-out
    predictions as `threshold` (call keyhole if index >= c), hence the same confusion; a cut outside it moves at least
    one unit across, which changes tp/fn or tn/fp. Reads indices only, no label. None means unbounded on that side."""
    index_fn = index_fn or repo_index
    pairs = sorted((index_fn(u), u["unit_id"]) for u in units)
    below = [p for p in pairs if p[0] < threshold]
    above = [p for p in pairs if p[0] >= threshold]
    lo = below[-1] if below else (None, None)
    hi = above[0] if above else (None, None)
    return {"threshold": threshold, "lowerExclusive": lo[0], "lowerUnit": lo[1], "upperInclusive": hi[0],
            "upperUnit": hi[1], "nHeldout": len(pairs),
            "definition": "every cut c with lowerExclusive < c <= upperInclusive gives the same held-out confusion "
                          "as the adopted cut (keyhole if index >= c)"}


def licensed_claim(interval: Dict[str, Any], t_f: float) -> str:
    """Section 12 (amendment B1): the only statement a PASS licenses."""
    lo = "-inf" if interval["lowerExclusive"] is None else f"{interval['lowerExclusive']:.2f}"
    hi = "+inf" if interval["upperInclusive"] is None else f"{interval['upperInclusive']:.2f}"
    return (f"The IN625 depth > half-width onset on the app index lies in ({lo}, {hi}] (held-out-admissible "
            f"interval); T_F = {t_f:.1f} is the fit-split point estimate, not a held-out-validated value.")


def leave_one_out_thresholds(fit_units: Sequence[Dict[str, Any]], index_fn=None,
                             label_fn=None) -> List[Optional[float]]:
    out: List[Optional[float]] = []
    for i in range(len(fit_units)):
        rest = [u for j, u in enumerate(fit_units) if j != i]
        try:
            out.append(adopted(fit_threshold(rest, index_fn, label_fn)["threshold"]))
        except DegenerateFit:
            out.append(None)
    return out


# ---- Verdict --------------------------------------------------------------------------------------------------------
def evaluate_pass(cand: Dict[str, Any], base: Dict[str, Any], cand_secondary: Dict[str, Any],
                  base_secondary: Dict[str, Any], loo_heldout_ba: Sequence[Optional[float]],
                  n_fit_keyhole: int, n_fit_not: int) -> Dict[str, Any]:
    """Section 7. cand/base are confusion() dicts on the held-out split (primary truth); *_secondary use the
    secondary truth. loo_heldout_ba are held-out BA values of the leave-one-out refit thresholds."""
    n_pos_h = cand["tp"] + cand["fn"]
    n_neg_h = cand["tn"] + cand["fp"]
    p4 = (n_pos_h >= MIN_HELDOUT_PER_CLASS and n_neg_h >= MIN_HELDOUT_PER_CLASS
          and n_fit_keyhole >= MIN_FIT_PER_CLASS and n_fit_not >= MIN_FIT_PER_CLASS)
    items = {"P4_classes_present": p4}
    if not p4:
        return {"verdict": "INCONCLUSIVE", "items": items}
    ba_c, ba_b = cand["balancedAccuracy"], base["balancedAccuracy"]
    items["P1_min_ba"] = ba_c >= PASS_MIN_BA
    items["P2_ba_gain"] = (ba_c - ba_b) >= PASS_MIN_BA_GAIN - 1e-12
    items["P3_error_reduction"] = cand["errors"] <= base["errors"] - PASS_MIN_ERROR_REDUCTION
    s_c, s_b = cand_secondary["balancedAccuracy"], base_secondary["balancedAccuracy"]
    items["P5_secondary_truth_not_worse"] = (s_c is not None and s_b is not None and s_c >= s_b)
    items["P6_loo_robust"] = bool(loo_heldout_ba) and all(b is not None and b >= PASS_LOO_MIN_BA for b in loo_heldout_ba)
    verdict = "PASS" if all(items.values()) else "FAIL"
    return {"verdict": verdict, "items": items}


# ---- Declared run ---------------------------------------------------------------------------------------------------
def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=True).stdout


def _require_committed(paths: Sequence[Path]) -> None:
    for p in paths:
        rel = p.relative_to(REPO_ROOT).as_posix()
        if not _git("ls-files", rel).strip():
            raise SystemExit(f"refusing to run: {rel} is not committed")
        if _git("status", "--porcelain", "--", rel).strip():
            raise SystemExit(f"refusing to run: {rel} has uncommitted changes")


def _arm(units: Sequence[Dict[str, Any]], threshold: float, label_fn=None, index_fn=None) -> Dict[str, Any]:
    label_fn = label_fn or truth_keyhole
    index_fn = index_fn or repo_index
    return confusion([index_fn(u) for u in units], [bool(label_fn(u)) for u in units], threshold)


def analyse(ledger: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Fit on the fit split, then score on the held-out split. Pure function of the ledger."""
    fit_units = [u for u in ledger if u["split"] == "fit"]
    held = [u for u in ledger if u["split"] == "heldout"]
    excluded = [u for u in ledger if u["split"] == "excluded"]

    # 1. Fit on the fit split only. Nothing from `held` is touched before this returns.
    fit = fit_threshold(fit_units)
    t_f = adopted(fit["threshold"])
    loo = leave_one_out_thresholds(fit_units)

    # 2. Score on the held-out split.
    factor = repo_per_weaver_factor()
    t_s = WEAVER_THRESHOLD * factor
    arms = {"F_fitted": _arm(held, t_f), "B_current_20": _arm(held, BASELINE_KEYHOLE_CUT),
            "S_weaver30_converted": _arm(held, t_s), "D_current_15_descriptive": _arm(held, BASELINE_TRANSITION_CUT)}
    secondary = {"F_fitted": _arm(held, t_f, truth_keyhole_secondary),
                 "B_current_20": _arm(held, BASELINE_KEYHOLE_CUT, truth_keyhole_secondary)}
    loo_ba = [(_arm(held, t)["balancedAccuracy"] if t is not None else None) for t in loo]
    verdict = evaluate_pass(arms["F_fitted"], arms["B_current_20"], secondary["F_fitted"], secondary["B_current_20"],
                            loo_ba, fit["nFitKeyhole"], fit["nFitNotKeyhole"])
    interval = heldout_admissible_interval(held, t_f)

    # 3. Sensitivities (reported, not part of the verdict).
    unamb = [u for u in held if not is_ambiguous(u)]
    t0_index = lambda u: repo_index(u, PREHEAT_SENSITIVITY_C)  # noqa: E731
    fit27 = fit_threshold(fit_units, index_fn=t0_index)
    nominal = lambda u: repo_index(u, power_W=pds.LANE_NOMINAL_CASE_POWER_W[u["unit_id"][-1]]  # noqa: E731
                                   if (u["source"] == LANE_SOURCE_ID and u["machine"] == "AMMT") else None)
    sens = {
        "unambiguousOnly": {"n": len(unamb), "F_fitted": _arm(unamb, t_f), "B_current_20": _arm(unamb, BASELINE_KEYHOLE_CUT)},
        "preheat27C": {"threshold": adopted(fit27["threshold"]),
                       "F_fitted": _arm(held, adopted(fit27["threshold"]), index_fn=t0_index),
                       "B_current_20": _arm(held, BASELINE_KEYHOLE_CUT, index_fn=t0_index)},
        "laneAmmtNominalPower": {"F_fitted": _arm(held, t_f, index_fn=nominal),
                                 "B_current_20": _arm(held, BASELINE_KEYHOLE_CUT, index_fn=nominal)},
    }
    per_unit = [{"unitId": u["unit_id"], "split": u["split"], "repoIndex": repo_index(u), "weaverIndex": weaver_index(u),
                 "halfWidthRatio": half_width_ratio(u), "spotRadiusRatio": spot_radius_ratio(u),
                 "truthKeyhole": truth_keyhole(u), "truthKeyholeSecondary": truth_keyhole_secondary(u),
                 "ambiguous": is_ambiguous(u)} for u in ledger]
    return {"counts": {"fit": len(fit_units), "heldout": len(held), "excluded": len(excluded)},
            "fit": fit, "adoptedThreshold": t_f, "looThresholds": loo, "looHeldoutBA": loo_ba,
            "weaverToRepoFactor": factor, "weaverThresholdInRepoUnits": t_s,
            "kingBandInRepoUnits": [KING_BAND[0] * factor, KING_BAND[1] * factor],
            "arms": arms, "secondaryTruth": secondary, "verdict": verdict,
            "heldoutAdmissibleInterval": interval,
            "licensedClaimIfPass": licensed_claim(interval, t_f), "sensitivities": sens,
            "transitionCutConsequence": ("adopted keyhole cut is below the transition cut 15: the IN625 transition band "
                                         "would be empty" if t_f < BASELINE_TRANSITION_CUT else "none"),
            "units": per_unit}


def declared_run() -> Dict[str, Any]:
    import lpbf_thermal_solver as solver
    if (solver.ENTHALPY_KEYHOLE, solver.ENTHALPY_TRANSITION) != (BASELINE_KEYHOLE_CUT, BASELINE_TRANSITION_CUT):
        raise SystemExit("solver cuts differ from the declared baseline")
    result = analyse(load_ledger(verify=True))
    hashes = {p.relative_to(REPO_ROOT).as_posix(): _sha256_file(p) for p in
              (DECLARATION, Path(__file__).resolve(), LEDGER_CSV, MDS2_WORKBOOK, PYTHON_DIR / "lpbf_public_datasets.py",
               PYTHON_DIR / "lpbf_thermal_solver.py")}
    return {"declaration": DECLARATION.relative_to(REPO_ROOT).as_posix(), "gitHead": _git("rev-parse", "HEAD").strip(),
            "experimentalValidation": False, "screeningOnly": True, "hashes": hashes, **result}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build-ledger")
    b.add_argument("--out", default=str(LEDGER_CSV))
    r = sub.add_parser("run")
    r.add_argument("--declared-run", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "build-ledger":
        text = ledger_csv_text(build_ledger_rows())
        out = Path(a.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(text.encode("utf-8"))
        print(f"wrote {out} sha256 {_sha256_bytes(text.encode('utf-8'))}")
        return 0
    if not a.declared_run:
        raise SystemExit("the run is the one declared run: pass --declared-run")
    if RESULTS_JSON.exists():
        raise SystemExit(f"refusing to run: {RESULTS_JSON.name} already exists (one declared run)")
    _require_committed([DECLARATION, Path(__file__).resolve(), LEDGER_CSV])
    result = declared_run()
    RESULTS_JSON.write_text(json.dumps(result, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    iv = result["heldoutAdmissibleInterval"]
    print(json.dumps({"verdict": result["verdict"], "adoptedThreshold": result["adoptedThreshold"],
                      "heldoutAdmissibleInterval": [iv["lowerExclusive"], iv["upperInclusive"]]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
