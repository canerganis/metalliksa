#!/usr/bin/env python3
"""Keyhole regime / keyhole-porosity screening of the app vs published x-ray measurements (comparison, not validation).

Reads only committed data (python/lpbf_keyhole_literature.py, pinned CSVs) and evaluates the app's screening WITHOUT
changing it. Schema 2 (keyhole-regime bump) reports the two rule sets side by side: ``legacy_15_30`` (hard-coded 15 / 30,
the rule before the bump) and ``current`` (imported from lpbf_thermal_solver: 15 / 20):

* the normalised-enthalpy index dH/hs with the regime thresholds (lpbf_public_datasets.classify_regime, the
  process-map regime label; same formula and thresholds as lpbf_thermal_solver.classify_enthalpy_regime),
* the solver's keyholePorosityRisk label prefix (Negligible / Possible / High; independent of the regime threshold),
* the King D/W > 0.5 keyhole-mode indicator of the geometric defect screen, per kernel (rosenthal, eagar-tsai),
* the Fabbro keyhole depth (keyholeModel.fabbroDepth_um) and the melt-pool depth of each kernel.

against Cunningham 2019 (Ti-6Al-4V vapor-depression depth and Fig. 3A regime lines) and Zhao 2020 (Ti-6Al-4V
keyhole-porosity boundary and pore observations), and puts the published scaling laws (Gan 2021 keyhole number,
Huang 2022 normalised enthalpy product, Hann 2011 vaporization-enthalpy transition) on the same cases. Gan, Huang and
Hann measured cases are not app materials and are only used for relation checks.

Also: a held-out D/W > 0.5 check on other datasets (Hofmann 316L, Totis Ti-6Al-4V, Lane IN625, KU Leuven), the King 2014
-> repo-convention conversion printed from code, and a Gan Supplementary Data 1 cross-check of the digitized Cunningham
depths.

Usage (from python/, locked interpreter):
    python -B tools/lpbf_keyhole_benchmark.py [--out ../docs/LPBF_KEYHOLE_BENCHMARK_2026-10-07_keyhole-regime.json] [--no-kernels]
Writes <out>.json, <out>.md and <out stem>.view.json. Deterministic: no timestamps, fixed rounding.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

PYTHON_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PYTHON_DIR))

import lpbf_keyhole_literature as kl  # noqa: E402
import lpbf_public_datasets as pds  # noqa: E402
import lpbf_thermal_solver as solver  # noqa: E402

SCHEMA = "lpbf-keyhole-benchmark-2"
GENERATED_AT = "2026-10-07"
TITLE_TAG = "keyhole-regime bump"  # markdown title tag of the committed 2026-10-07 record; --title-tag for later records
DEFAULT_OUT = PYTHON_DIR.parent / "docs" / "LPBF_KEYHOLE_BENCHMARK_2026-10-07_keyhole-regime.json"
# Rule before the keyhole-regime bump (hard-coded on purpose) and the rule the solver applies now.
LEGACY_TRANSITION = 15.0
LEGACY_KEYHOLE = 30.0
CURRENT_TRANSITION = solver.ENTHALPY_TRANSITION
CURRENT_KEYHOLE = solver.ENTHALPY_KEYHOLE
RULES = {"legacy_15_30": (LEGACY_TRANSITION, LEGACY_KEYHOLE), "current": (CURRENT_TRANSITION, CURRENT_KEYHOLE)}
SENSITIVITY_THRESHOLDS = (15.0, 17.5, 18.0, 20.0, 22.0, 25.0, 30.0)
REPORT_THRESHOLDS = (15.0, 20.0, 30.0)  # per-source sensitivity (keyhole-mode recall) and specificity are reported here
HELD_OUT_DW = 0.5  # melt-pool depth / width above which a track is keyhole mode (King 2014, Cunningham 2019)
KERNELS = ("rosenthal", "eagar-tsai")
LAYER_UM, HATCH_UM = 30.0, 100.0  # irrelevant to the single-track keyhole quantities; recorded
# Fabbro 2020 Sec. 3.4: his d is the uniform / half-maximum diameter; FWHM = sqrt(ln2 / 2) x the 1/e2 diameter = 0.5887 d.
FWHM_OVER_1E2 = math.sqrt(math.log(2.0) / 2.0)
FABBRO_FWHM_LABEL = "diagnostic, not served"
FABBRO_FWHM_BASIS = ("fabbroDepthFwhm_um = fabbro_keyhole_depth_m with d = sqrt(ln2/2) x the 1/e2 beam diameter, same "
                     "absorptivity, properties and dH/hs ramp as the served call (Fabbro 2020 Sec. 3.4: his d is the "
                     "half-maximum diameter). Diagnostic, not served: the served fabbroDepth_um keeps the 1/e2 diameter "
                     "(D-3a record: the FWHM convention breaks the vapour <= melt-depth bound on IN718/316L).")
BEAM_CONVENTION_SCHEMA = "lpbf-keyhole-beam-convention-1"
DEFAULT_BEAM_CONVENTION_OUT = PYTHON_DIR.parent / "docs" / "LPBF_KEYHOLE_BEAM_CONVENTION_2026-10-07.json"
REGIMES3 = ("conduction", "transition", "keyhole")
LINE_SPEEDS = tuple(range(400, 1201, 100))
HONESTY = ("Comparison of the app's existing screening with published Ti-6Al-4V x-ray measurements; digitized figure "
           "values (read uncertainty recorded per row); app thermophysical properties and flat absorptivity are the "
           "app's estimates, not the papers' values; not experimental validation; this report changes no solver number.")


def r3(x: Optional[float]) -> Optional[float]:
    return None if x is None else round(float(x), 3)


# ---------------------------------------------------------------------------------------------------------------
# pure helpers
# ---------------------------------------------------------------------------------------------------------------
def confusion(truth: Sequence[str], pred: Sequence[str], classes: Sequence[str]) -> Dict[str, Any]:
    m = {t: {p: 0 for p in classes} for t in classes}
    for t, p in zip(truth, pred):
        m[t][p] += 1
    n = len(truth)
    correct = sum(m[c][c] for c in classes)
    recall = {c: (r3(m[c][c] / sum(m[c].values())) if sum(m[c].values()) else None) for c in classes}
    return {"rowsAreReported_columnsArePredicted": m, "n": n, "correct": correct,
            "accuracy": r3(correct / n) if n else None, "recallPerReportedClass": recall}


def depth_stats(pairs: Iterable[tuple]) -> Optional[Dict[str, Any]]:
    """pairs of (predicted, measured, tolerance)."""
    pairs = [(p, m, t) for p, m, t in pairs if p is not None and m is not None]
    if not pairs:
        return None
    err = [p - m for p, m, _ in pairs]
    rel = [abs(p - m) / m for p, m, _ in pairs if m > 0]
    ratio = [p / m for p, m, _ in pairs if m > 0]
    return {"n": len(pairs), "bias_um": r3(statistics.fmean(err)), "mae_um": r3(statistics.fmean(abs(e) for e in err)),
            "rmse_um": r3(math.sqrt(statistics.fmean(e * e for e in err))),
            "mape_pct": r3(100 * statistics.fmean(rel)) if rel else None,
            "medianRatioPredOverMeas": r3(statistics.median(ratio)) if ratio else None,
            "withinTolerance": sum(1 for p, m, t in pairs if abs(p - m) <= t),
            "underpredicted": sum(1 for e in err if e < 0)}


def summary(values: Sequence[float]) -> Optional[Dict[str, float]]:
    v = [x for x in values if x is not None]
    if not v:
        return None
    return {"n": len(v), "min": r3(min(v)), "median": r3(statistics.median(v)), "max": r3(max(v))}


def regime_label(h: float, transition: float, keyhole: float) -> str:
    return "conduction" if h < transition else "transition" if h < keyhole else "keyhole"


def porosity_prefix(h: float) -> str:
    """Prefix of the solver's keyholePorosityRisk label (Negligible / Possible / High), from the solver's constants."""
    return ("Negligible" if h < solver.POROSITY_SCREEN_NEGLIGIBLE_BELOW else
            "Possible" if h < solver.POROSITY_SCREEN_HIGH_AT else "High")


def porosity_prefix_legacy(h: float) -> str:
    return "Negligible" if h < LEGACY_TRANSITION else "Low-Moderate" if h < LEGACY_KEYHOLE else "High"


def ti64_props() -> Dict[str, Any]:
    p = pds.screening_props(kl.APP_MATERIAL_TI64)
    return {k: p[k] for k in ("density_kg_m3", "thermal_conductivity_W_mK", "specific_heat_J_kgK", "liquidus_C",
                              "boiling_C", "absorptivity_IR")}


def ye_eta_min_ti64() -> Dict[str, Any]:
    import lpbf_literature_datasets as lit
    d = lit.load_ye_min_absorptivity()
    row = next(r for r in d["rows"] if r["material"] == kl.APP_MATERIAL_TI64)
    return {"value": row["absorptivity"], "locator": row["locator"], "dataset": d["provenance"]["id"],
            "fileSha256": d["provenance"]["fileSha256"]}


def index_block(P: float, v: float, spot: float, preheat: float, props: Dict[str, Any], eta_min: float) -> Dict[str, Any]:
    reg = pds.classify_regime(kl.APP_MATERIAL_TI64, P, v, spot, preheat, None)
    h = reg["normalizedEnthalpy"]
    gan = kl.gan_keyhole_number(P, v, spot, props["density_kg_m3"], props["specific_heat_J_kgK"],
                                props["thermal_conductivity_W_mK"], props["liquidus_C"], preheat, eta_min)
    return {"appIndex_dHhs": r3(h), "appRegime": regime_label(h, CURRENT_TRANSITION, CURRENT_KEYHOLE),
            "appRegimeLegacy_15_30": regime_label(h, LEGACY_TRANSITION, LEGACY_KEYHOLE),
            "appPorosityRiskByIndex": porosity_prefix(h),
            "appPorosityRiskLegacy": porosity_prefix_legacy(h),
            "ganKe": r3(gan["Ke"]), "ganEta": r3(gan["eta"]), "ganRegime": kl.gan_regime(gan["Ke"]),
            "ganKeyholeDepth_um": r3(kl.gan_keyhole_depth_um(gan["Ke"], spot)),
            "huangProduct_betaYe": r3(kl.huang_enthalpy_product(P, v, spot, eta_min)),
            "huangProduct_betaAppFlat": r3(kl.huang_enthalpy_product(P, v, spot, props["absorptivity_IR"])),
            "hannRegime": kl.hann_regime(reg["normalizedEnthalpy"])}


def kernel_block(P: float, v: float, spot: float, preheat: float) -> Dict[str, Any]:
    from lpbf_thermal_solver import calculate_meltpool_physics
    out: Dict[str, Any] = {}
    for k in KERNELS:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            res = calculate_meltpool_physics(kl.APP_MATERIAL_TI64, P, v, spot, preheat, LAYER_UM, HATCH_UM,
                                             heat_source=k, absorption_model="flat-plate")
        g = res["meltPoolGeometry"]
        gs = res.get("geometricDefectScreen") or {}
        out[k] = {"depth_um": r3(g["depth_um"]), "width_um": r3(g["width_um"]),
                  "dOverW": r3(g["depth_um"] / g["width_um"]) if g["width_um"] else None,
                  "extentStatus": g.get("extentStatus"), "solverRegime": g.get("regime"),
                  "kingModeIndicator": (gs.get("keyhole") or {}).get("kingModeIndicator"),
                  "keyholeVaporCavityDepth_um": r3(g.get("keyholeVaporCavityDepth_um")),
                  "fabbroDepth_um": r3(res["keyholeModel"]["fabbroDepth_um"]),
                  "solverIndex_dHhs": r3(res["processParameters"]["normalizedEnthalpy"]),
                  "keyholePorosityRisk": res["defectDiagnostics"]["keyholePorosityRisk"]}
    return out


# ---------------------------------------------------------------------------------------------------------------
# Fabbro half-maximum-diameter diagnostic (computed here from the frozen Fabbro function; nothing served changes)
# ---------------------------------------------------------------------------------------------------------------
def fabbro_fwhm_diagnostic(material: str, power_W: float, speed_mm_s: float, spot_um: float, preheat_C: float,
                           heat_source: str = "eagar-tsai") -> Dict[str, Any]:
    """Run the unchanged solver once, record the exact arguments of its fabbro_keyhole_depth_m call, and repeat that
    call with d = FWHM (sqrt(ln2/2) x the 1/e2 diameter). Returns the served depth (equal to
    keyholeModel.fabbroDepth_um), the FWHM depth, and the scope flag

    aspectRatioInScope = (e / d_FWHM >= 1) and (2 <= Pe <= 10), with e and Pe both on the FWHM basis (Fabbro's own d);
    the served-basis aspect ratio and Peclet flag are returned next to it."""
    from lpbf_thermal_solver import calculate_meltpool_physics
    from fabbro_keyhole import fabbro_keyhole_depth_m as fabbro_fn
    captured: List[tuple] = []

    def recorder(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        captured.append(args)
        return fabbro_fn(*args, **kwargs)

    original = solver.fabbro_keyhole_depth_m
    solver.fabbro_keyhole_depth_m = recorder
    try:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            res = calculate_meltpool_physics(material, power_W, speed_mm_s, spot_um, preheat_C, LAYER_UM, HATCH_UM,
                                             heat_source=heat_source, absorption_model="flat-plate")
    finally:
        solver.fabbro_keyhole_depth_m = original
    # Since P1 (2026-10-11) the solver also evaluates the leg for the 49 process-map grid cells after the operating
    # point; the operating-point call is the first one and the only one at the requested power and speed.
    if not captured or captured[0][0] != float(power_W) or captured[0][1] != float(speed_mm_s) * 1e-3:
        raise RuntimeError(f"expected the first fabbro_keyhole_depth_m call at the operating point, saw {captured[:1]}")
    args = list(captured[0])
    served = fabbro_fn(*args)
    args[2] = args[2] * FWHM_OVER_1E2
    fwhm = fabbro_fn(*args)
    d_fwhm_m = max(8e-6, args[2])
    r_fwhm = fwhm["depth_m"] / d_fwhm_m
    return {"fabbroDepth_um": r3(res["keyholeModel"]["fabbroDepth_um"]),
            "fabbroDepthFwhm_um": r3(fwhm["depth_m"] * 1e6),
            "beamDiameterFwhm_um": r3(d_fwhm_m * 1e6),
            "aspectRatioFwhm_e_over_dFwhm": r3(r_fwhm), "pecletFwhm": r3(fwhm["peclet"]),
            "pecletInFitRangeFwhm": fwhm["pecletInFitRange"],
            "aspectRatioServed_e_over_d1e2": r3(served["aspectRatio_e_over_d"]),
            "pecletServed": r3(served["peclet"]), "pecletInFitRangeServed": served["pecletInFitRange"],
            "aspectRatioInScope": bool(r_fwhm >= 1.0 and fwhm["pecletInFitRange"]),
            "label": FABBRO_FWHM_LABEL}


def beam_convention_record() -> Dict[str, Any]:
    """Additive diagnostic record: served Fabbro depth vs the half-maximum-diameter diagnostic on the Ti-6Al-4V
    literature sets (Cunningham 2019 vapour-depression depths, Zhao 2020 boundary depths), with the scope flag."""
    cun = kl.load_cunningham_depths()["rows"]
    zb = kl.load_zhao_boundary()["rows"]
    sets = (("cunningham95", [r for r in cun if r["beamDiameter_um"] == 95.0], "vaporDepressionDepth_um"),
            ("cunningham140", [r for r in cun if r["beamDiameter_um"] == 140.0], "vaporDepressionDepth_um"),
            ("zhaoBoundaryBare", [r for r in zb if r["setting"] == "bare"], "keyholeDepth_um"),
            ("zhaoBoundaryPowder", [r for r in zb if r["setting"] == "powder"], "keyholeDepth_um"))
    out_sets: Dict[str, Any] = {}
    cases: List[Dict[str, Any]] = []
    for name, rows, meas in sets:
        diag = []
        for r in rows:
            d = fabbro_fwhm_diagnostic(kl.APP_MATERIAL_TI64, r["power_W"], r["speed_mm_s"], r["beamDiameter_um"],
                                       r["preheat_C"])
            diag.append((r, d))
            cases.append({"set": name, "rowId": r["rowId"], "power_W": r["power_W"], "speed_mm_s": r["speed_mm_s"],
                          "beamDiameter_um": r["beamDiameter_um"], "measuredDepth_um": r[meas],
                          "fabbroDepth_um": d["fabbroDepth_um"], "fabbroDepthFwhm_um": d["fabbroDepthFwhm_um"],
                          "aspectRatioFwhm": d["aspectRatioFwhm_e_over_dFwhm"], "pecletFwhm": d["pecletFwhm"],
                          "aspectRatioInScope": d["aspectRatioInScope"]})
        out_sets[name] = {
            "n": len(rows),
            "servedFabbro": depth_stats((d["fabbroDepth_um"], r[meas], 0.0) for r, d in diag),
            "fabbroFwhmDiagnostic": depth_stats((d["fabbroDepthFwhm_um"], r[meas], 0.0) for r, d in diag),
            "aspectRatioInScope": f"{sum(d['aspectRatioInScope'] for _, d in diag)}/{len(diag)}",
            "rowsWithServedFabbroDepth": sum(1 for r, d in diag if d["fabbroDepth_um"] > 0)}
    return {"schema": BEAM_CONVENTION_SCHEMA, "generatedAt": GENERATED_AT, "label": FABBRO_FWHM_LABEL,
            "basis": FABBRO_FWHM_BASIS, "fwhmOver1e2": round(FWHM_OVER_1E2, 5),
            "scopeRule": "aspectRatioInScope = (e / d_FWHM >= 1) and (2 <= Pe <= 10), FWHM basis (Fabbro 2020 Sec. 2.1)",
            "servedValuesChanged": False, "sets": out_sets, "cases": cases,
            "note": ("Cunningham and Gan Supplementary Data 1 are the same experiments (not independent). Measured "
                     "depths are digitized; 20 C preheat assumed for every row. The FWHM diagnostic is not served.")}


# ---------------------------------------------------------------------------------------------------------------
# held-out check, King conversion, Gan Data 1 cross-check
# ---------------------------------------------------------------------------------------------------------------
def _binary_block(rows: Sequence[tuple]) -> Dict[str, Any]:
    """rows of (index, keyholeMode D/W > 0.5). Accuracy and recalls per rule set; sensitivity over thresholds."""
    n = len(rows)
    kh = [h for h, k in rows if k]
    nk = [h for h, k in rows if not k]
    out: Dict[str, Any] = {"n": n, "keyholeModeRows": len(kh), "notKeyholeRows": len(nk)}
    for name, (_, keyhole) in RULES.items():
        tp = sum(h >= keyhole for h in kh)
        tn = sum(h < keyhole for h in nk)
        out[name] = {"threshold": keyhole, "correct": tp + tn, "accuracy": r3((tp + tn) / n) if n else None,
                     "keyholeModeRecall": f"{tp}/{len(kh)}", "notKeyholeRecall": f"{tn}/{len(nk)}"}
    per: Dict[str, Any] = {}
    for t in REPORT_THRESHOLDS:
        tp, fn = sum(h >= t for h in kh), sum(h < t for h in kh)
        tn, fp = sum(h < t for h in nk), sum(h >= t for h in nk)
        per[f"{t:g}"] = {"truePositive": tp, "falseNegative": fn, "trueNegative": tn, "falsePositive": fp,
                         "sensitivity": r3(tp / len(kh)) if kh else None,
                         "specificity": r3(tn / len(nk)) if nk else None}
    out["perThreshold"] = per
    out["sensitivityAccuracy"] = {str(t): r3((sum(h >= t for h in kh) + sum(h < t for h in nk)) / n) if n else None
                                  for t in SENSITIVITY_THRESHOLDS}
    out["indexOfKeyholeModeRows"] = summary(kh)
    out["indexOfNotKeyholeRows"] = summary(nk)
    return out


def _held_out_rows(rows: Iterable[Dict[str, Any]], spot_scale: float = 1.0) -> List[tuple]:
    out = []
    for r in rows:
        if None in (r.get("power_W"), r.get("speed_mm_s"), r.get("beamDiameter_um"), r.get("width_um"),
                    r.get("depth_um")) or r["width_um"] <= 0:
            continue
        h = pds.normalized_enthalpy(r["material"], r["power_W"], r["speed_mm_s"], r["beamDiameter_um"] * spot_scale,
                                    r.get("preheat_C") or 20.0)
        out.append((h, r["depth_um"] / r["width_um"] > HELD_OUT_DW))
    return out


def held_out_check() -> Dict[str, Any]:
    """Binary keyhole mode (measured melt-pool D/W > 0.5) vs the app index on datasets NOT used to choose the
    threshold. Reported, not tuned: KU Leuven labels are the authors' own and its beam diameter is unverified (the
    37.5 um reading is the loader's, 75 um is a sensitivity reading), so KU is inconclusive and not a gate."""
    hof = pds.load_hofmann_316l()["rows"]
    ku = pds.load_ku_leuven_316l_ti64()["rows"]
    ku316 = [r for r in ku if r["material"].startswith("316")]
    kuti = [r for r in ku if not r["material"].startswith("316")]
    out: Dict[str, Any] = {
        "criterion": "measured melt-pool depth/width > 0.5 = keyhole mode (binary); legacy 15/30 vs current rule",
        "hofmann316l": _binary_block(_held_out_rows(hof)),
        "hofmann316lBySpot_um": {str(int(d)): _binary_block(_held_out_rows([r for r in hof if r["beamDiameter_um"] == d]))
                                 for d in sorted({r["beamDiameter_um"] for r in hof})},
        "totisTi64": _binary_block(_held_out_rows(pds.load_totis_ti64()["rows"])),
        "laneIn625LegacyProps": _binary_block(_held_out_rows(pds.load_lane_in625()["rows"])),
        "kuLeuven316l_spot37.5um_unverified": _binary_block(_held_out_rows(ku316)),
        "kuLeuven316l_spot75um_sensitivity": _binary_block(_held_out_rows(ku316, 2.0)),
        "kuLeuvenTi64_spot37.5um_unverified": _binary_block(_held_out_rows(kuti)),
        "kuLeuvenTi64_spot75um_sensitivity": _binary_block(_held_out_rows(kuti, 2.0)),
        "notes": ["KU Leuven labels are the authors' own (their conduction includes D/W up to 0.63) and the beam "
                  "diameter is unverified (37.5 vs 75 um changes the index by 2.83x): inconclusive, not a gate.",
                  "Lane IN625 uses the app's legacy-estimated IN625 properties: keyhole-mode tracks sit below the "
                  "index cut for any threshold, i.e. the index under-reads IN625.",
                  "Zhao boundary at low speed (v <= 425 mm/s) sits at index 15.0-18.9 (keyhole porosity begins at "
                  "the keyhole-mode onset there): consistent, not used.",
                  "Moving 30 -> 20 trades specificity for sensitivity: it adds true keyhole-mode calls and false "
                  "positives (Hofmann 316L +109 true, +59 false), still catches 0/10 Lane IN625 keyhole-mode tracks, "
                  "and costs KU Leuven Ti-6Al-4V (37.5 um reading) 3 rows, 14 -> 11: an unresolved counter-finding.",
                  "Cunningham and Gan data are the same measurements and the derivation inputs; they are not "
                  "independent validation. The threshold 20 is a provisional screening choice."],
    }
    return out


def king_conversion(red_line_index: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """King et al. 2014 Table 3 constants (316L) -> repo convention, from code (constants from published_relations.csv).

    H_King / H_app = (A_K / A_app) * (rho cp (T_liq - T0))_app / (rho_K hs_K) * sqrt(alpha_app / D_K) * 2^1.5 for the same
    P, v and beam (r = 2 sigma, sigma = D4sigma / 4)."""
    king = next(r for r in kl.load_relations()["rows"] if r["relation"] == "king2014-keyhole-threshold-316l")
    c = king["constants"]
    props = pds.screening_props("316L Stainless Steel")
    t0 = kl.ASSUMED_PREHEAT_C
    rho, cp, k = props["density_kg_m3"], props["specific_heat_J_kgK"], props["thermal_conductivity_W_mK"]
    app_hs = rho * cp * (props["liquidus_C"] - t0)
    alpha = k / (rho * cp)
    factor = ((c["A"] / props["absorptivity_IR"]) * app_hs / (c["rho_kg_m3"] * c["hs_J_kg"])
              * math.sqrt(alpha / c["D_m2_s"]) * 2.0 ** 1.5)
    lo, mid, hi = ((c["center"] + sgn * c["halfwidth"]) / factor for sgn in (-1, 0, 1))
    out: Dict[str, Any] = {
        "source": king["locator"], "kingConstants": c,
        "densityUnitNote": ("King's Table 3 prints density as '7.98 kg/m3' (verified on the rendered page image of the "
                            "accepted manuscript, OSTI 1502044); the physical value is 7.98 g/cm3 = 7980 kg/m3, so the "
                            "unit was corrected here, not taken as printed"),
        "app316lProperties": {"density_kg_m3": rho, "specific_heat_J_kgK": cp, "liquidus_C": props["liquidus_C"],
                              "thermal_conductivity_W_mK": k, "absorptivity_IR": props["absorptivity_IR"], "T0_C": t0},
        "factorHKingOverHApp": r3(factor),
        "kingThresholdInAppUnits": {"low": r3(lo), "mid": r3(mid), "high": r3(hi)},
        "note": ("Convention conversion at equal P, v and beam (r = 2 sigma), conditional on the app absorptivity, 20 C "
                 "preheat and the app 316L property set; the app absorptivity enters the index linearly, so the "
                 "converted threshold is consistent with the app's estimated absorptivity, not with the true one. "
                 "The Cunningham red-line range is the app index along speed (400-1200 mm/s), not a confidence "
                 "interval; the chosen 20 is a provisional screening choice, not a derived exact threshold.")}
    if red_line_index:
        rlo, rhi = red_line_index["min"], red_line_index["max"]
        olo, ohi = max(lo, rlo), min(hi, rhi)
        out["cunninghamRedLineIndexRange"] = {"low": rlo, "high": rhi}
        out["intervalOverlap"] = {"low": r3(olo), "high": r3(ohi), "empty": bool(olo > ohi)}
        out["chosenKeyholeThreshold"] = CURRENT_KEYHOLE
        out["chosenInsideBothIntervals"] = bool(olo - 0.05 <= CURRENT_KEYHOLE <= ohi + 0.05)
    return out


def gan_data1_cross_check(cun_rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Gan Supplementary Data 1 Ti-6Al-4V keyhole depths vs our digitized Cunningham Fig. 3B/3C depths (same
    measurements, Gan ref. 2): matched by spot, speed (<1 mm/s) and power (< 6 W)."""
    g = kl.load_gan_data1_ti64()["rows"]
    diffs, unmatched = [], 0
    for r in cun_rows:
        best = min(g, key=lambda x: (abs(x["beamDiameter_um"] - r["beamDiameter_um"]) > 1,
                                     abs(x["speed_mm_s"] - r["speed_mm_s"]) > 1,
                                     abs(x["power_W"] - r["power_W"])))
        if (abs(best["beamDiameter_um"] - r["beamDiameter_um"]) < 1 and abs(best["speed_mm_s"] - r["speed_mm_s"]) < 1
                and abs(best["power_W"] - r["power_W"]) < 6):
            diffs.append(r["vaporDepressionDepth_um"] - best["keyholeDepth_um"])
        else:
            unmatched += 1
    return {"ganRows": len(g), "digitizedRows": len(cun_rows), "matched": len(diffs), "unmatched": unmatched,
            "digitizedMinusGan_um": {"median": r3(statistics.median(diffs)),
                                     "meanAbs": r3(statistics.fmean(abs(d) for d in diffs)),
                                     "maxAbs": r3(max(abs(d) for d in diffs))} if diffs else None,
            "note": ("Same measurements (Gan ref. 2 = Cunningham 2019); a read-quality check of the digitization, not "
                     "a second dataset. Gan Supplementary Data 2 lists r0 = 75 um for the 140 um cases (Data 1 and SI "
                     "Eqs. 23/37: r0 = d/2 = 70 um): Gan-internal inconsistency, recorded and not used.")}


# ---------------------------------------------------------------------------------------------------------------
# evaluation
# ---------------------------------------------------------------------------------------------------------------
def evaluate(run_kernels: bool = True) -> Dict[str, Any]:
    props = ti64_props()
    ye = ye_eta_min_ti64()
    eta_min = ye["value"]
    cun = kl.load_cunningham_depths()
    zb = kl.load_zhao_boundary()
    zp = kl.load_zhao_pores()
    lines = kl.cunningham_lines()

    def case(row: Dict[str, Any]) -> Dict[str, Any]:
        out = {k: row[k] for k in ("dataset", "rowId", "power_W", "speed_mm_s", "beamDiameter_um", "preheat_C",
                                   "regimeReported", "locator", "digitized")}
        out.update(index_block(row["power_W"], row["speed_mm_s"], row["beamDiameter_um"], row["preheat_C"], props,
                               eta_min))
        if run_kernels:
            out["kernels"] = kernel_block(row["power_W"], row["speed_mm_s"], row["beamDiameter_um"], row["preheat_C"])
        return out

    cun_cases = []
    for r in cun["rows"]:
        c = case(r)
        c.update(vaporDepressionDepth_um=r["vaporDepressionDepth_um"], depthSd_um=r["depthSd_um"],
                 readUncertainty_um=r["readUncertainty_um"], regimeNearBoundary=r["regimeNearBoundary"])
        cun_cases.append(c)
    zb_cases = []
    for r in zb["rows"]:
        c = case(r)
        c.update(setting=r["setting"], keyholeDepth_um=r["keyholeDepth_um"],
                 depthReadUncertainty_um=r["depthReadUncertainty_um"])
        zb_cases.append(c)
    zp_cases = []
    for r in zp["rows"]:
        c = case(r)
        c.update(barePlatePores=r["barePlatePores"], powderBedPores=r["powderBedPores"])
        zp_cases.append(c)

    # ---- regime confusion on Cunningham 95 um (Fig. 3A labels): in-sample (derivation set of the new threshold) ----
    lab = [c for c in cun_cases if c["regimeReported"]]
    truth = [c["regimeReported"] for c in lab]
    t2 = ["keyhole" if t == "keyhole" else "not-keyhole" for t in truth]
    clear = [c for c in lab if not c["regimeNearBoundary"]]
    conf: Dict[str, Any] = {}
    for rule, key in (("legacy_15_30", "appRegimeLegacy_15_30"), ("current", "appRegime")):
        conf[rule] = {
            "appIndex3Class": confusion(truth, [c[key] for c in lab], REGIMES3),
            "appIndexKeyholeOnly": confusion(t2, ["keyhole" if c[key] == "keyhole" else "not-keyhole" for c in lab],
                                             ("keyhole", "not-keyhole")),
            "appIndex3ClassExcludingNearBoundary": confusion([c["regimeReported"] for c in clear],
                                                             [c[key] for c in clear], REGIMES3)}
    conf["ganKe_1.4_6"] = confusion(truth, [c["ganRegime"] for c in lab], REGIMES3)
    conf["hann_HvHs_12.34"] = confusion(t2, [c["hannRegime"] for c in lab], ("keyhole", "not-keyhole"))
    if run_kernels:
        for k in KERNELS:
            conf[f"kingDW05_{k}"] = confusion(
                t2, ["keyhole" if c["kernels"][k]["kingModeIndicator"] == "keyhole-mode" else "not-keyhole"
                     for c in lab], ("keyhole", "not-keyhole"))

    # ---- boundary lines: app index / Ke / Huang along the Cunningham lines ----
    line_rows = []
    for v in LINE_SPEEDS:
        row = {"speed_mm_s": v}
        for name in ("blue-dashed", "red-dashed"):
            P = lines[name]["slope"] * v + lines[name]["intercept"]
            ib = index_block(P, v, 95.0, kl.ASSUMED_PREHEAT_C, props, eta_min)
            row[name] = {"power_W": r3(P), "appIndex_dHhs": ib["appIndex_dHhs"], "ganKe": ib["ganKe"],
                         "huangProduct_betaYe": ib["huangProduct_betaYe"]}
        h_blue = row["blue-dashed"]["appIndex_dHhs"] / row["blue-dashed"]["power_W"]
        row["appPowerAt_dHhs15_W"] = r3(CURRENT_TRANSITION / h_blue)
        row["appPowerAt_dHhs30_W"] = r3(LEGACY_KEYHOLE / h_blue)
        row["appPowerAt_dHhs20_W"] = r3(CURRENT_KEYHOLE / h_blue)
        row["ratio_appKeyholePower_over_redLine"] = r3(row["appPowerAt_dHhs30_W"] / row["red-dashed"]["power_W"])
        row["ratio_appKeyholePowerCurrent_over_redLine"] = r3(row["appPowerAt_dHhs20_W"] / row["red-dashed"]["power_W"])
        row["ratio_appTransitionPower_over_blueLine"] = r3(row["appPowerAt_dHhs15_W"] / row["blue-dashed"]["power_W"])
        line_rows.append(row)

    # ---- Zhao: pores and boundary ----
    def pore_counts(cs):
        n = len(cs)
        return {"n": n,
                "appHigh_dHhs_ge_30": sum(c["appPorosityRiskByIndex"] == "High" for c in cs),
                "appPossible_15_30": sum(c["appPorosityRiskByIndex"] == "Possible" for c in cs),
                "appNegligible_lt_15": sum(c["appPorosityRiskByIndex"] == "Negligible" for c in cs),
                "legacyLowModerate_15_30": sum(c["appPorosityRiskLegacy"] == "Low-Moderate" for c in cs),
                "ganKe_gt_16": sum(c["ganKe"] > kl.GAN_KE_STABLE_MAX for c in cs),
                "ganKe_gt_30": sum(c["ganKe"] > kl.GAN_KE_CHAOTIC_MIN for c in cs),
                "huangBetaYe_gt_5": sum(c["huangProduct_betaYe"] > kl.HUANG_TI64_THRESHOLD -
                                        kl.HUANG_TI64_THRESHOLD_HALFWIDTH for c in cs),
                "huangBetaYe_gt_8": sum(c["huangProduct_betaYe"] > kl.HUANG_TI64_THRESHOLD for c in cs),
                "appIndex": summary([c["appIndex_dHhs"] for c in cs]),
                "ganKe": summary([c["ganKe"] for c in cs]),
                "huangProduct_betaYe": summary([c["huangProduct_betaYe"] for c in cs])}
    pores = {"all": pore_counts(zp_cases),
             "barePlatePores": pore_counts([c for c in zp_cases if c["barePlatePores"]]),
             "powderBedPores": pore_counts([c for c in zp_cases if c["powderBedPores"]])}
    boundary = {}
    for s in ("bare", "powder"):
        cs = sorted([c for c in zb_cases if c["setting"] == s], key=lambda c: c["speed_mm_s"])
        boundary[s] = {"n": len(cs), "appIndex": summary([c["appIndex_dHhs"] for c in cs]),
                       "ganKe": summary([c["ganKe"] for c in cs]),
                       "huangProduct_betaYe": summary([c["huangProduct_betaYe"] for c in cs]),
                       "huangProduct_betaAppFlat": summary([c["huangProduct_betaAppFlat"] for c in cs]),
                       "appIndexAlongBoundary": [[c["speed_mm_s"], c["power_W"], c["appIndex_dHhs"]] for c in cs],
                       "boundaryPointsAppAlreadyHigh": sum(c["appPorosityRiskByIndex"] == "High" for c in cs),
                       "boundaryPointsAppBelow15": sum(c["appIndex_dHhs"] < CURRENT_TRANSITION for c in cs)}

    # ---- depth ----
    depth: Dict[str, Any] = {}
    def tol(c, key_unc, sd_key=None):
        return (c.get(key_unc) or 0.0) + ((c.get(sd_key) or 0.0) if sd_key else 0.0)
    for name, cs, meas, unc, sd in (("cunningham95", [c for c in cun_cases if c["beamDiameter_um"] == 95.0],
                                     "vaporDepressionDepth_um", "readUncertainty_um", "depthSd_um"),
                                    ("cunningham140", [c for c in cun_cases if c["beamDiameter_um"] == 140.0],
                                     "vaporDepressionDepth_um", "readUncertainty_um", "depthSd_um"),
                                    ("zhaoBoundaryBare", [c for c in zb_cases if c["setting"] == "bare"],
                                     "keyholeDepth_um", "depthReadUncertainty_um", None),
                                    ("zhaoBoundaryPowder", [c for c in zb_cases if c["setting"] == "powder"],
                                     "keyholeDepth_um", "depthReadUncertainty_um", None)):
        block = {"ganEq2": depth_stats((c["ganKeyholeDepth_um"], c[meas], tol(c, unc, sd)) for c in cs)}
        if run_kernels:
            block["appFabbro"] = depth_stats((c["kernels"]["eagar-tsai"]["fabbroDepth_um"], c[meas], tol(c, unc, sd))
                                             for c in cs)
            for k in KERNELS:
                block[f"appMeltPoolDepth_{k}_vsVaporDepth"] = depth_stats(
                    (c["kernels"][k]["depth_um"], c[meas], tol(c, unc, sd)) for c in cs)
        # Diagnostic only: factor s on the app-property Ke that would put each measured depth on Gan Eq. (2),
        # s = (e/r0 / 0.4 + 1.4) / Ke. A spread around one value means a property-set offset; a trend means more.
        block["ganKeScaleToFitEq2"] = summary(
            [((c[meas] / (c["beamDiameter_um"] / 2.0)) / kl.GAN_ASPECT_SLOPE + kl.GAN_ASPECT_OFFSET) / c["ganKe"]
             for c in cs if c[meas] is not None])
        depth[name] = block

    # ---- Hann self-consistency (printed relation vs printed tables) ----
    hann = kl.load_hann_welds()
    hann_rows = []
    for r in hann["rows"]:
        pred = kl.hann_depth_relation_as_printed(r["dHhsPrinted"])
        hann_rows.append({"rowId": r["rowId"], "dHhsPrinted": r["dHhsPrinted"], "deltaStarPrinted": r["deltaStarPrinted"],
                          "deltaStarFromPrintedRelation": r3(pred),
                          "relErrorPct": r3(100 * (pred - r["deltaStarPrinted"]) / r["deltaStarPrinted"])})
    hann_check = {"rows": hann_rows,
                  "withinClaimed10pct": sum(abs(x["relErrorPct"]) <= 10 for x in hann_rows), "n": len(hann_rows)}

    # ---- automatic findings (numbers only; the narrative is in the .md) ----
    red = [row["red-dashed"]["appIndex_dHhs"] for row in line_rows]
    blue = [row["blue-dashed"]["appIndex_dHhs"] for row in line_rows]
    findings = {
        "appIndexAtCunninghamRedLine": summary(red), "appIndexAtCunninghamBlueLine": summary(blue),
        "appKeyholeThreshold": CURRENT_KEYHOLE, "appKeyholeThresholdLegacy": LEGACY_KEYHOLE,
        "appTransitionThreshold": CURRENT_TRANSITION,
        "appIndexAtZhaoBoundary": summary([c["appIndex_dHhs"] for c in zb_cases]),
        "zhaoPoreCasesAppHigh": f"{pores['all']['appHigh_dHhs_ge_30']}/{pores['all']['n']}",
        "zhaoPoreCasesAppPossible": f"{pores['all']['appPossible_15_30']}/{pores['all']['n']}",
        "keyholeThresholdTooHighForTi64Legacy": bool(max(red) < LEGACY_KEYHOLE),
        "keyholeThresholdTooHighForTi64": bool(max(red) < CURRENT_KEYHOLE),
        "singleIndexThresholdFitsZhaoBoundary": False if (max(c["appIndex_dHhs"] for c in zb_cases) /
                                                           min(c["appIndex_dHhs"] for c in zb_cases)) > 1.5 else True,
        "publicDatasetsConstantsEqualSolver": bool(pds.ENTHALPY_KEYHOLE == CURRENT_KEYHOLE and
                                                   pds.ENTHALPY_TRANSITION == CURRENT_TRANSITION),
    }
    if run_kernels:
        ix_agree = all(abs(c["kernels"][k]["solverIndex_dHhs"] - c["appIndex_dHhs"]) < 0.05
                       for c in cun_cases + zb_cases + zp_cases for k in KERNELS)
        findings["solverIndexEqualsProcessMapIndex"] = ix_agree
        risk_agree = all(c["kernels"][k]["keyholePorosityRisk"].startswith(c["appPorosityRiskByIndex"])
                         for c in cun_cases + zb_cases + zp_cases for k in KERNELS)
        findings["solverPorosityRiskEqualsIndexBands"] = risk_agree
        findings["solverRegimeFamilyEqualsIndexRegime"] = all(
            c["kernels"][k]["solverRegime"].lower().startswith(c["appRegime"])
            for c in cun_cases + zb_cases + zp_cases for k in KERNELS)

    from lpbf_simulation import implementation_fingerprint
    doc = {
        "schema": SCHEMA, "generatedAt": GENERATED_AT, "honesty": HONESTY,
        "implementationHash": implementation_fingerprint(),
        "appScreening": {
            "index": "lpbf_public_datasets.classify_regime / lpbf_thermal_solver.classify_enthalpy_regime",
            "rule": pds.REGIME_RULE, "transitionThreshold": CURRENT_TRANSITION,
            "keyholeThreshold": CURRENT_KEYHOLE, "legacyKeyholeThreshold": LEGACY_KEYHOLE,
            "regimeThresholdBasis": solver.REGIME_THRESHOLD_BASIS,
            "porosityRisk": ("lpbf_thermal_solver keyholePorosityRisk (independent of the regime threshold): "
                             "<15 Negligible, 15-30 Possible (advisory), >=30 High; the legacy label for 15-30 was "
                             "Low-Moderate"),
            "geometricIndicator": "lpbf_defect_diagnostics King D/W > 0.5 kingModeIndicator (label only)",
            "keyholeDepth": "keyholeModel.fabbroDepth_um (Fabbro 2020 eq. 2, flat absorptivity, 15->30 ramp)",
            "kernels": list(KERNELS) if run_kernels else [], "layer_um": LAYER_UM, "hatch_um": HATCH_UM,
            "material": kl.APP_MATERIAL_TI64, "materialProperties": props, "absorptionModel": "flat-plate"},
        "publishedRelationInputs": {
            "ganEtaMin": ye, "ganProperties": "app Ti-6Al-4V properties (Gan's values are SI-only)",
            "huangHm_J_mm3": kl.HUANG_HM_TI64_J_MM3, "huangBeta": {"ye": eta_min, "appFlat": props["absorptivity_IR"]},
            "hannHvHsTi64": kl.HANN_HV_HS_TI64},
        "datasets": {name: {k: v for k, v in fn()["provenance"].items()}
                     for name, fn in kl.LOADERS.items()},
        "crossCheckDatasets": {"gan-keyhole-2021-supplementary-data1": kl.load_gan_data1_ti64()["provenance"]},
        "relations": kl.load_relations()["rows"],
        "confusion": conf, "heldOut": held_out_check(),
        "kingConversion": king_conversion(findings["appIndexAtCunninghamRedLine"]),
        "ganData1Check": gan_data1_cross_check(cun["rows"]),
        "cunninghamLines": line_rows, "zhaoPores": pores, "zhaoBoundary": boundary,
        "depth": depth, "hannRelationCheck": hann_check, "findings": findings,
        "notEvaluatedByApp": {
            "gan-keyhole-2021": "Al6061 not in the app material authority",
            "huang-al7a77-2022": "Al7A77 / pure Al not in the app material authority",
            "hann-ss304-2011": "AISI 304 not in the app material authority; welding scale"},
        "cases": {"cunningham": cun_cases, "zhaoBoundary": zb_cases, "zhaoPores": zp_cases},
    }
    return doc


def view(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Read-only summary a scorecard / process-window panel could show (not wired to any UI)."""
    f = doc["findings"]
    cur = doc["confusion"]["current"]["appIndex3Class"]
    leg = doc["confusion"]["legacy_15_30"]["appIndex3Class"]
    return {
        "schema": "lpbf-keyhole-benchmark-view-2", "generatedAt": doc["generatedAt"], "readOnly": True,
        "evidenceKind": "Literature comparison (screening only; digitized published measurements)",
        "label": "Keyhole regime screening vs published x-ray data (legacy 15/30 vs current 15/20)",
        "honesty": doc["honesty"], "implementationHash": doc["implementationHash"],
        "sources": [{"id": k, "doi": v.get("doi"), "rows": v.get("rows")} for k, v in doc["datasets"].items()],
        "regimeConfusion": {"rule": "app dH/hs 15/20 vs Cunningham 2019 Fig. 3A (95 um, Ti-6Al-4V; in-sample, the "
                                    "derivation set of the 20)",
                            "matrix": cur["rowsAreReported_columnsArePredicted"], "accuracy": cur["accuracy"],
                            "n": cur["n"],
                            "legacy_15_30": {"matrix": leg["rowsAreReported_columnsArePredicted"],
                                             "accuracy": leg["accuracy"], "n": leg["n"]}},
        "keyholeThreshold": {"app": f["appKeyholeThreshold"], "legacy": f["appKeyholeThresholdLegacy"],
                             "appIndexAtPublishedKeyholeLine": f["appIndexAtCunninghamRedLine"],
                             "kingConvertedInterval": doc["kingConversion"]["kingThresholdInAppUnits"],
                             "intervalOverlap": doc["kingConversion"].get("intervalOverlap")},
        "heldOut": {k: {"n": v["n"], "legacy": v["legacy_15_30"]["correct"], "current": v["current"]["correct"]}
                    for k, v in doc["heldOut"].items() if isinstance(v, dict) and "legacy_15_30" in v},
        "porosity": {"zhaoPoreCasesFlaggedHigh": f["zhaoPoreCasesAppHigh"],
                     "zhaoPoreCasesPossible": f["zhaoPoreCasesAppPossible"],
                     "appIndexAlongPublishedPorosityBoundary": f["appIndexAtZhaoBoundary"]},
        "depth": {k: (v.get("appFabbro") or {}).get("mape_pct") for k, v in doc["depth"].items()},
        "physicsBump": "keyhole-regime (threshold 30 -> 20; porosity screen decoupled; Fabbro unchanged)",
        "evidenceNote": "docs/LPBF_KEYHOLE_THRESHOLD_EVIDENCE_2026-10-07.md",
    }


# ---------------------------------------------------------------------------------------------------------------
# markdown
# ---------------------------------------------------------------------------------------------------------------
def _matrix_md(conf: Dict[str, Any], classes: Sequence[str]) -> List[str]:
    m = conf["rowsAreReported_columnsArePredicted"]
    L = ["| reported \\ predicted | " + " | ".join(classes) + " |", "|---|" + "---|" * len(classes)]
    for t in classes:
        L.append(f"| {t} | " + " | ".join(str(m[t][p]) for p in classes) + " |")
    L.append(f"\nn = {conf['n']}, correct = {conf['correct']}, accuracy = {conf['accuracy']}, recall per reported "
             f"class = {conf['recallPerReportedClass']}.")
    return L


def _rule_rows(doc: Dict[str, Any], key: str, classes: Sequence[str]) -> List[str]:
    out: List[str] = []
    for rule in ("legacy_15_30", "current"):
        out += ["", f"**{rule}**", ""] + _matrix_md(doc["confusion"][rule][key], classes)
    return out


def to_markdown(doc: Dict[str, Any]) -> str:
    f = doc["findings"]
    L = [f"# LPBF keyhole screening vs published x-ray measurements, {TITLE_TAG} ({doc['generatedAt']})", "",
         f"**{doc['honesty']}**", "",
         f"Schema `{doc['schema']}`; implementation fingerprint `{doc['implementationHash']}`. Generated by "
         "`python/tools/lpbf_keyhole_benchmark.py` from the pinned CSVs of `python/lpbf_keyhole_literature.py`. Both rule "
         f"sets are reported: `legacy_15_30` (the rule before the bump) and `current` (15 / {f['appKeyholeThreshold']:g}, "
         "imported from `lpbf_thermal_solver`). The earlier record "
         "`LPBF_KEYHOLE_BENCHMARK_2026-10-07.*` (schema 1, legacy rule only) is kept.", "",
         "## Data", "", "| dataset | rows | file | digitized | SI needed |", "|---|---|---|---|---|"]
    for name, p in doc["datasets"].items():
        dig = "yes" if "digitized" in p["file"] else "no (printed values)"
        L.append(f"| {name} (doi:{p['doi']}) | {p['rows']} | `{p['file']}` | {dig} | {p.get('supplementaryNeeded', '')} |")
    for name, p in doc["crossCheckDatasets"].items():
        L.append(f"| {name} (doi:{p['doi']}), cross-check only | {p['rows']} | `{p['file']}` | no (published values) | |")
    L += ["", f"Published relations transcribed: {len(doc['relations'])} (`published_relations.csv`, each with a "
          "locator). Gan's and Huang's Ti-6Al-4V points are Cunningham/Zhao data and were not ingested again.", "",
          "App screening evaluated: " + doc["appScreening"]["rule"], "",
          "Regime threshold basis (solver): " + doc["appScreening"]["regimeThresholdBasis"], "",
          "## Regime confusion: Cunningham 2019 Fig. 3B cases (Ti-6Al-4V, 95 um), labels from the Fig. 3A lines", "",
          "In-sample for the new threshold (the Fig. 3A red line is one of its two derivation inputs).", ""]
    c = doc["confusion"]
    L += ["### App dH/hs, 3 classes"] + _rule_rows(doc, "appIndex3Class", REGIMES3)
    L += ["", "### Excluding cases within the read uncertainty of a line"] + \
        _rule_rows(doc, "appIndex3ClassExcludingNearBoundary", REGIMES3)
    L += ["", "### Keyhole vs not-keyhole (app index)"] + _rule_rows(doc, "appIndexKeyholeOnly", ("keyhole", "not-keyhole"))
    L += ["", "### Gan 2021 keyhole number (Ke < 1.4 / 1.4-6 / > 6), app properties, eta from Eq. 6 with Ye 2019 Am", ""] + \
        _matrix_md(c["ganKe_1.4_6"], REGIMES3)
    L += ["", "### Other keyhole vs not-keyhole rules", "",
          "| rule | n | correct | accuracy | keyhole recall | not-keyhole recall |", "|---|---|---|---|---|---|"]
    for k in [k for k in c if k.startswith(("hann", "kingDW05"))]:
        x = c[k]
        L.append(f"| {k} | {x['n']} | {x['correct']} | {x['accuracy']} | {x['recallPerReportedClass']['keyhole']} | "
                 f"{x['recallPerReportedClass']['not-keyhole']} |")
    k = doc["kingConversion"]
    L += ["", "## Threshold derivation (from code)", "",
          f"King et al. 2014 Table 3 (316L, {k['source']}): H_King / H_app = **{k['factorHKingOverHApp']}** at equal P, "
          f"v and beam (r = 2 sigma). King 30 +/- 4 corresponds to app index {k['kingThresholdInAppUnits']['mid']} "
          f"({k['kingThresholdInAppUnits']['low']} to {k['kingThresholdInAppUnits']['high']}). Cunningham 2019 Fig. 3A "
          f"red line (Ti-6Al-4V 95 um): app index {k['cunninghamRedLineIndexRange']['low']} to "
          f"{k['cunninghamRedLineIndexRange']['high']} along speed (a range, not a confidence interval). Overlap {k['intervalOverlap']['low']} to "
          f"{k['intervalOverlap']['high']}; chosen threshold {k['chosenKeyholeThreshold']:g} "
          f"(inside both: {k['chosenInsideBothIntervals']}); a provisional screening choice. {k['densityUnitNote']}. "
          f"{k['note']}", "",
          "## Held-out check (not used to choose the threshold): measured melt-pool D/W > 0.5 = keyhole mode", ""]
    ho = doc["heldOut"]
    L += ["| dataset | n | legacy 15/30 correct | current correct | current accuracy | keyhole-mode recall legacy -> current | "
          "not-keyhole recall legacy -> current |", "|---|---|---|---|---|---|---|"]

    def ho_row(name: str, x: Dict[str, Any]) -> str:
        return (f"| {name} | {x['n']} | {x['legacy_15_30']['correct']} | {x['current']['correct']} | "
                f"{x['current']['accuracy']} | {x['legacy_15_30']['keyholeModeRecall']} -> "
                f"{x['current']['keyholeModeRecall']} | {x['legacy_15_30']['notKeyholeRecall']} -> "
                f"{x['current']['notKeyholeRecall']} |")
    for name, x in ho.items():
        if isinstance(x, dict) and "legacy_15_30" in x:
            L.append(ho_row(name, x))
    for spot, x in ho["hofmann316lBySpot_um"].items():
        L.append(ho_row(f"hofmann316l, spot {spot} um", x))
    L += ["", "Sensitivity (keyhole-mode recall) and specificity (not-keyhole recall) per source at 15 / 20 / 30 "
          "(TP / FN / TN / FP):", "", "| dataset | threshold | TP | FN | TN | FP | sensitivity | specificity |",
          "|---|---|---|---|---|---|---|---|"]
    for name, x in ho.items():
        if isinstance(x, dict) and "perThreshold" in x:
            for t, v in x["perThreshold"].items():
                L.append(f"| {name} | {t} | {v['truePositive']} | {v['falseNegative']} | {v['trueNegative']} | "
                         f"{v['falsePositive']} | {v['sensitivity']} | {v['specificity']} |")
    L += ["", "Accuracy vs threshold (reported, not tuned):", "",
          "| dataset | " + " | ".join(f"{t:g}" for t in SENSITIVITY_THRESHOLDS) + " |",
          "|---|" + "---|" * len(SENSITIVITY_THRESHOLDS)]
    for name in ("hofmann316l", "totisTi64"):
        L.append(f"| {name} | " + " | ".join(str(ho[name]["sensitivityAccuracy"][str(t)]) for t in SENSITIVITY_THRESHOLDS)
                 + " |")
    L += [""] + [f"- {n}" for n in ho["notes"]]
    L += ["", "## Published transition lines vs the app thresholds (95 um, Ti-6Al-4V, 20 C)", "",
          "| v mm/s | blue P W | app dH/hs at blue | red P W | app dH/hs at red | Gan Ke at red | app P at dH/hs=30 | "
          "app P30 / red P | app P at dH/hs=20 | app P20 / red P |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in doc["cunninghamLines"]:
        L.append(f"| {r['speed_mm_s']} | {r['blue-dashed']['power_W']} | {r['blue-dashed']['appIndex_dHhs']} | "
                 f"{r['red-dashed']['power_W']} | {r['red-dashed']['appIndex_dHhs']} | {r['red-dashed']['ganKe']} | "
                 f"{r['appPowerAt_dHhs30_W']} | {r['ratio_appKeyholePower_over_redLine']} | "
                 f"{r['appPowerAt_dHhs20_W']} | {r['ratio_appKeyholePowerCurrent_over_redLine']} |")
    L += ["", f"App index at the red (keyhole-domain) line: {f['appIndexAtCunninghamRedLine']}; app keyhole "
          f"threshold {f['appKeyholeThreshold']} (legacy {f['appKeyholeThresholdLegacy']}). At the blue (conduction-limit) "
          f"line: {f['appIndexAtCunninghamBlueLine']}; app transition threshold {f['appTransitionThreshold']}.", "",
          "## Keyhole porosity: Zhao 2020 (Ti-6Al-4V, ~100 um)", "",
          "The porosity screen is a proxy independent of the regime threshold (Negligible < 15, Possible 15-30, High >= 30); "
          "no single index cut separates pores from stable keyholes.", "",
          "| subset | n | app High (>=30) | app Possible (15-30) | app <15 | legacy Low-Moderate | Gan Ke>16 | Gan Ke>30 | "
          "Huang(beta=Am)>5 | >8 |", "|---|---|---|---|---|---|---|---|---|---|"]
    for k, x in doc["zhaoPores"].items():
        L.append(f"| pores observed: {k} | {x['n']} | {x['appHigh_dHhs_ge_30']} | {x['appPossible_15_30']} | "
                 f"{x['appNegligible_lt_15']} | {x['legacyLowModerate_15_30']} | {x['ganKe_gt_16']} | "
                 f"{x['ganKe_gt_30']} | {x['huangBetaYe_gt_5']} | {x['huangBetaYe_gt_8']} |")
    L += ["", "Index values ON the published porosity boundary (a single threshold of any index would be constant here):",
          "", "| setting | n | app dH/hs min/median/max | Gan Ke min/median/max | Huang (beta=Am) min/median/max | "
          "boundary points app already calls High |", "|---|---|---|---|---|---|"]
    for s_, x in doc["zhaoBoundary"].items():
        fmt = lambda d: f"{d['min']} / {d['median']} / {d['max']}"
        L.append(f"| {s_} | {x['n']} | {fmt(x['appIndex'])} | {fmt(x['ganKe'])} | {fmt(x['huangProduct_betaYe'])} | "
                 f"{x['boundaryPointsAppAlreadyHigh']} |")
    L += ["", "## Depth (unchanged by the bump)", "", "Measured quantity is the vapor-depression (keyhole) depth. The app "
          "melt-pool depth is listed only as a consistency check (a melt pool must contain the vapor depression).", "",
          "| set | predictor | n | bias um | MAE um | MAPE % | median pred/meas | within tolerance | underpredicted |",
          "|---|---|---|---|---|---|---|---|---|"]
    for s_, block in doc["depth"].items():
        for k, x in block.items():
            if x and k != "ganKeScaleToFitEq2":
                L.append(f"| {s_} | {k} | {x['n']} | {x['bias_um']} | {x['mae_um']} | {x['mape_pct']} | "
                         f"{x['medianRatioPredOverMeas']} | {x['withinTolerance']} | {x['underpredicted']} |")
    L += ["", "Gan Eq. (2) with app properties: factor on Ke that would put each measured depth on the published line "
          "(diagnostic of the property-set offset):", ""]
    for s_, block in doc["depth"].items():
        L.append(f"- {s_}: {block['ganKeScaleToFitEq2']}")
    g = doc["ganData1Check"]
    L += ["", "## Gan Supplementary Data 1 vs the digitized Cunningham depths", "",
          f"{g['matched']} of {g['digitizedRows']} digitized rows match a Gan Data 1 Ti-6Al-4V row ({g['ganRows']} rows; "
          f"same spot and speed, power within 6 W). Digitized minus Gan depth: {g['digitizedMinusGan_um']}. {g['note']}"]
    h = doc["hannRelationCheck"]
    L += ["", "## Hann 2011 depth relation, as printed, vs Hann's own Tables 3-4", "",
          f"{h['withinClaimed10pct']} of {h['n']} printed (dH/hs, delta*) pairs are within the claimed +/-10% of the "
          "printed piecewise relation; the printed form cannot be the curve the tables follow (likely a typesetting "
          "error). It is recorded, not used for a verdict.", "",
          "| case | dH/hs | delta* printed | delta* from printed relation | error % |", "|---|---|---|---|---|"]
    for r in h["rows"]:
        L.append(f"| {r['rowId']} | {r['dHhsPrinted']} | {r['deltaStarPrinted']} | {r['deltaStarFromPrintedRelation']} | "
                 f"{r['relErrorPct']} |")
    L += ["", "## Findings (computed)", "", "```json", json.dumps(f, indent=2, sort_keys=True), "```", "",
          "Narrative, limits and the bump record: `docs/LPBF_KEYHOLE_THRESHOLD_EVIDENCE_2026-10-07.md`.", ""]
    return "\n".join(L)


def main(argv: Optional[List[str]] = None) -> int:
    global GENERATED_AT, TITLE_TAG
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--no-kernels", action="store_true", help="index-only (no solver calls)")
    ap.add_argument("--beam-convention", action="store_true",
                    help="write the additive Fabbro half-maximum-diameter diagnostic record instead "
                         "(default out: docs/LPBF_KEYHOLE_BEAM_CONVENTION_2026-10-07.json)")
    ap.add_argument("--generated-at", default=GENERATED_AT, help="record date written as generatedAt (default 2026-10-07)")
    ap.add_argument("--title-tag", default=TITLE_TAG,
                    help="bump name in the markdown title (default 'keyhole-regime bump', the committed 2026-10-07 record)")
    a = ap.parse_args(argv)
    GENERATED_AT = a.generated_at
    TITLE_TAG = a.title_tag
    if a.beam_convention:
        out = Path(a.out) if a.out != str(DEFAULT_OUT) else DEFAULT_BEAM_CONVENTION_OUT
        out.write_text(json.dumps(beam_convention_record(), indent=1, sort_keys=True) + "\n", encoding="utf-8",
                       newline="\n")
        return 0
    text = json.dumps(evaluate(run_kernels=not a.no_kernels), indent=1, sort_keys=True) + "\n"
    doc = json.loads(text)  # .md and .view.json are rendered from the committed (key-sorted) JSON
    out = Path(a.out)
    out.write_text(text, encoding="utf-8", newline="\n")
    out.with_suffix(".md").write_text(to_markdown(doc), encoding="utf-8", newline="\n")
    out.with_name(out.stem + ".view.json").write_text(json.dumps(view(doc), indent=1, sort_keys=True) + "\n",
                                                      encoding="utf-8", newline="\n")
    print(json.dumps(doc["findings"], indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
