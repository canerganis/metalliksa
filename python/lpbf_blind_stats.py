"""Blind test statistics: verbatim extraction of the MELT runner's pure statistical functions.

Source (no runtime import of either research branch; the code below is copied, not called):
  M  = research/ti64-primary e91d0fbd, python/tools/run_lpbf_melt_depth.py,
       git blob 2bff1378fc4d23d2528c6834ea096f541228906c
  P3 = research/p3-cavity-astra c4470b01, python/tools/run_lpbf_p3_cavity.py,
       git blob cc0f5528bca6fdca94bb4974b4fb3876795512a6
`PROVENANCE` names the source file and the 1-based line range of every extracted name. Each function body is the
source text unchanged, including its docstring and comments, so docstring references to sections and amendments are
those of the MELT and P3 pre-registrations. python/test_lpbf_blind_stats.py proves it: source hashes per function and
golden vectors produced by the original runner functions on synthetic data only.

One structural change, no behavioural change: the fragile flip block of the runner's `score_phase` (M 1852 to 1862) is
inline code there and is the body of `fragile_flips` here.

What this module is not:
  * No I/O, no git guards, no amendment pins, no research-branch or `lpbf_research_*` import. The only project import is
    the served `lpbf_public_datasets` (for `served_index`, as in the runner).
  * Status words stay the MELT words (PASS, FAIL, INCONCLUSIVE, EXPOSED_DESCRIPTIVE, DESCRIPTIVE_NOT_SCORED). The blind
    test words of the research hub spec section 7.3 are mapped at the report layer, never here.
  * The declared additions of the research hub spec (section 3.1 row, divergence list 7.7) are not in this file:
    per-alloy leverage cuts beyond Ti64 and AlSi10Mg, the widened `SERVED_NAME`, and the not-formed-track and
    measurement-loss handling around `reduce_conditions`. Callers add them outside the extracted code.
  * Not in the fingerprint manifest (`lpbf_simulation.IMPLEMENTATION_SOURCE_FILES`) and imported by no served module.
"""
from __future__ import annotations

import math
import statistics
from fractions import Fraction

import numpy as np

import lpbf_public_datasets as pds  # served: normalized_enthalpy, used by served_index only (M 53)


# Source file key, first line, last line (1-based, inclusive) of every extracted name. `fragile_flips` points
# at the inline block of the runner's `score_phase` that is its body.
PROVENANCE = {
    "INF": ("M", 69, 69),
    "MEDIAN_MAX": ("M", 134, 134),
    "P90_MAX": ("M", 134, 134),
    "BIAS_MAX": ("M", 134, 134),
    "MAXAPE_MAX": ("M", 134, 134),
    "N_MIN": ("M", 135, 135),
    "SIDE_MIN": ("M", 136, 136),
    "U_MAX": ("M", 137, 137),
    "LEVERAGE_LOW_CUT": ("M", 138, 138),
    "LEVERAGE_HIGH_CUT": ("M", 139, 139),
    "POWER_BAND": ("M", 140, 140),
    "BEAM_BAND_GRADE_B": ("M", 141, 141),
    "U_M_REL_FLOOR": ("M", 142, 142),
    "U_M_F_UM": ("M", 143, 143),
    "CV_POOL_MIN_CONDITIONS": ("M", 144, 144),
    "CV_POOL_MIN_DF": ("M", 144, 144),
    "BOOT_B": ("M", 145, 145),
    "BOOT_SEED": ("M", 145, 145),
    "FWHM_FACTOR": ("P3", 117, 117),
    "SERVED_NAME": ("M", 154, 154),
    "GRADE_RANK": ("M", 155, 155),
    "TIE_TOL": ("P3", 128, 128),
    "DP_SCALE": ("P3", 129, 129),
    "ENUMERATION_MAX_N": ("P3", 130, 130),
    "_fr": ("M", 240, 242),
    "rank_quantile_exact": ("M", 245, 259),
    "percentile90": ("M", 262, 263),
    "median_rank": ("M", 266, 267),
    "_to_float": ("M", 270, 271),
    "mean_signed_exact": ("M", 274, 277),
    "_le": ("M", 280, 284),
    "block_statistics": ("M", 287, 301),
    "p75": ("M", 304, 305),
    "bootstrap_intervals": ("M", 308, 338),
    "index_bins": ("M", 341, 343),
    "power_grade": ("M", 349, 356),
    "beam_grade": ("M", 359, 367),
    "block_grade": ("M", 370, 372),
    "u_m_default_um": ("M", 378, 381),
    "cv_pool": ("M", 384, 399),
    "resolution_qualifier": ("M", 402, 449),
    "beam_d_um": ("M", 666, 673),
    "TargetColumnRequested": ("P3", 1083, 1084),
    "_fold": ("M", 1036, 1037),
    "assert_no_target_loaded": ("M", 1390, 1396),
    "served_index": ("M", 1499, 1500),
    "_mean": ("M", 1563, 1564),
    "reduce_conditions": ("M", 1567, 1613),
    "_track_value": ("M", 1616, 1623),
    "arm_rels": ("M", 1626, 1641),
    "leverage_qualifier": ("M", 1644, 1650),
    "block_verdict": ("M", 1653, 1677),
    "served_bins": ("M", 1690, 1700),
    "fragile_flips": ("M", 1852, 1862),
    "signflip_p_enumerate": ("P3", 830, 853),
    "_dp_p": ("P3", 856, 870),
    "signflip_p_dp": ("P3", 873, 885),
    "signflip_p": ("P3", 888, 895),
    "paired_differences": ("P3", 901, 916),
}
# Source key: (commit, path, git blob id).
SOURCE_BLOBS = {
    "M": ("e91d0fbda10b9b01e974dd9838aae026e1cdd91c", "python/tools/run_lpbf_melt_depth.py",
          "2bff1378fc4d23d2528c6834ea096f541228906c"),
    "P3": ("c4470b017cfe533c74b23dc5712a2df720ae00c4", "python/tools/run_lpbf_p3_cavity.py",
           "cc0f5528bca6fdca94bb4974b4fb3876795512a6"),
}

INF = math.inf


# ----------------------------------------------------------------------------------------------
# Thresholds and constants fixed by the pre-registration
# ----------------------------------------------------------------------------------------------
MEDIAN_MAX, P90_MAX, BIAS_MAX, MAXAPE_MAX = "0.20", "0.35", "0.10", "0.50"      # as written, compared exactly
N_MIN = 12
SIDE_MIN = 4
U_MAX = 0.10
LEVERAGE_LOW_CUT = {"Ti64": 15.0, "AlSi10Mg": 15.0}          # Amendment 5 item 1.2 and Amendment 6 item 2.1
LEVERAGE_HIGH_CUT = 20.0
POWER_BAND = 0.05                                            # Amendment 6 item 4 (k = 1), declared, never refined
BEAM_BAND_GRADE_B = 0.05                                     # Amendment 6 item 5.3 (k = 1)
U_M_REL_FLOOR = 0.03
U_M_F_UM = {"bare_plate": 5.0, "powder_layer_or_am": 10.0}   # Amendment 6 item 9.3 (lead assumption, not sourced)
CV_POOL_MIN_CONDITIONS, CV_POOL_MIN_DF = 3, 3
BOOT_B, BOOT_SEED = 2000, 20261011
FWHM_FACTOR = math.sqrt(math.log(2.0) / 2.0)           # 0.588705: d_D4sigma = d_FWHM / f
SERVED_NAME = {"Ti64": "Ti-6Al-4V", "AlSi10Mg": "AlSi10Mg"}
GRADE_RANK = {"A": 3, "B": 2, "C": 1}
# Sign flip test constants (P3 128 to 130)
TIE_TOL = 1e-12
DP_SCALE = 1_000_000
ENUMERATION_MAX_N = 24


# ----------------------------------------------------------------------------------------------
# Statistics: exact rational comparison, +infinity rules (Amendments 2 and 3). Equals `melt_verdict` of the sim script.
# ----------------------------------------------------------------------------------------------
def _fr(x):
    """Exact rational value of a finite number as written (shortest round trip decimal): 0.1 means 1/10."""
    return Fraction(repr(float(x)))


def rank_quantile_exact(values, num, den):
    """Section 4.2 item 2: sorted ascending with +infinity last, h = (num/den)(n - 1); an integer h gives a(h); else
    +infinity when either neighbour is +infinity, else the linear interpolation. Fraction, math.inf or nan (empty)."""
    a = sorted(values)
    n = len(a)
    if n == 0:
        return math.nan
    top = num * (n - 1)
    lo, rem = divmod(top, den)
    if rem == 0:
        return INF if math.isinf(a[lo]) else _fr(a[lo])
    hi = lo + 1
    if math.isinf(a[lo]) or math.isinf(a[hi]):
        return INF
    return _fr(a[lo]) + Fraction(rem, den) * (_fr(a[hi]) - _fr(a[lo]))


def percentile90(values):
    return _to_float(rank_quantile_exact(values, 9, 10))


def median_rank(values):
    return _to_float(rank_quantile_exact(values, 1, 2))


def _to_float(x):
    return x if isinstance(x, float) else float(x)


def mean_signed_exact(rels):
    """Arithmetic mean of rel_c over the finite rows (a failed row is infinite and does not enter it)."""
    fin = [_fr(x) for x in rels if math.isfinite(x)]
    return sum(fin, Fraction(0)) / len(fin) if fin else math.nan


def _le(stat, thr):
    """stat <= thr as rational numbers; +infinity and nan never pass a finite threshold."""
    if isinstance(stat, float):
        return False
    return stat <= Fraction(thr)


def block_statistics(rels):
    """The four G3o statistics on rel_c values (+-infinity allowed for a model failure, APE = +infinity)."""
    ape = [abs(x) for x in rels]
    n = len(rels)
    med_x = rank_quantile_exact(ape, 1, 2)
    p90_x = rank_quantile_exact(ape, 9, 10)
    ms_x = mean_signed_exact(rels)
    max_x = INF if any(math.isinf(a) for a in ape) else (_fr(max(ape)) if ape else math.nan)
    ok = {"median": _le(med_x, MEDIAN_MAX), "p90": _le(p90_x, P90_MAX),
          "mean_signed": (False if isinstance(ms_x, float) else abs(ms_x) <= Fraction(BIAS_MAX)),
          "max_ape": _le(max_x, MAXAPE_MAX)}
    worst = max(range(n), key=lambda i: ape[i]) if n else None
    return {"n": n, "median": _to_float(med_x), "p75": p75(ape), "p90": _to_float(p90_x), "mean_signed": _to_float(ms_x),
            "max_ape": _to_float(max_x), "worst_index": worst, "n_failed": sum(1 for a in ape if math.isinf(a)),
            "thresholds_met": ok, "all_thresholds_met": all(ok.values())}


def p75(values):
    return _to_float(rank_quantile_exact(values, 3, 4))


def bootstrap_intervals(rels, B=BOOT_B, seed=BOOT_SEED):
    """Conditions-as-clusters bootstrap 95 percent interval of each statistic (descriptive). A point estimate whose
    interval crosses its threshold is labelled marginal; the verdict uses the point estimates."""
    n = len(rels)
    if n == 0:
        return {}
    rng = np.random.default_rng(seed)
    arr = list(rels)
    draws = {"median": [], "p90": [], "mean_signed": [], "max_ape": []}
    for _ in range(B):
        idx = rng.integers(0, n, n)
        sample = [arr[i] for i in idx]
        ape = [abs(x) for x in sample]
        draws["median"].append(median_rank(ape))
        draws["p90"].append(percentile90(ape))
        fin = [x for x in sample if math.isfinite(x)]
        draws["mean_signed"].append(math.fsum(fin) / len(fin) if fin else math.nan)
        draws["max_ape"].append(max(ape))
    out = {}
    thr = {"median": 0.20, "p90": 0.35, "mean_signed": 0.10, "max_ape": 0.50}
    for k, vals in draws.items():
        vals = sorted(v for v in vals if not math.isnan(v))
        if not vals:
            continue
        lo, hi = vals[int(0.025 * len(vals))], vals[min(len(vals) - 1, int(0.975 * len(vals)))]
        if k == "mean_signed":                                   # the threshold is on the absolute value
            marginal = lo <= -thr[k] <= hi or lo <= thr[k] <= hi
        else:
            marginal = lo <= thr[k] <= hi
        out[k] = {"lo": lo, "hi": hi, "marginal": bool(marginal)}
    return out


def index_bins(index, cut, high=LEVERAGE_HIGH_CUT):
    """Served normalized enthalpy index bin of a condition: below the cut, the transition, at or above 20."""
    return "below" if index < cut else ("at_or_above" if index >= high else "between")


# ----------------------------------------------------------------------------------------------
# Input metrology grade (Amendment 6 item 3): fixed once, from the data owner's text only, never from a depth
# ----------------------------------------------------------------------------------------------
def power_grade(facts):
    """A: delivered power at the workpiece, meter named, released uncertainty. B: measured without a released
    uncertainty or away from the workpiece. C: commanded. An unclear fact gives the lower grade."""
    if facts.get("basis") != "measured":                    # commanded, or unclear
        return "C"
    a_ok = (facts.get("meter_named") is True and facts.get("at_workpiece") is True
            and facts.get("released_uncertainty") is True)
    return "A" if a_ok else "B"


def beam_grade(facts):
    """A: measured at the work plane, definition stated, released uncertainty. B: measured without released
    uncertainty or away from the work plane. C: nominal; a definition that is unstated (read as 1/e2) is C."""
    if facts.get("basis") != "measured":
        return "C"
    if facts.get("definition_stated") is not True:           # unstated or unclear: read as 1/e2, flagged, grade C
        return "C"
    a_ok = facts.get("work_plane") is True and facts.get("released_uncertainty") is True
    return "A" if a_ok else "B"


def block_grade(power, beam):
    """The block grade is the lower of the power grade and the beam grade (A above B above C)."""
    return min((power, beam), key=lambda g: GRADE_RANK[g])


# ----------------------------------------------------------------------------------------------
# u_m default, resolution qualifier with the pooled coefficient of variation (Amendment 6 item 9)
# ----------------------------------------------------------------------------------------------
def u_m_default_um(d_obs_um, block_kind, am_substrate):
    """u_m / D_obs = max(f / D_obs, 0.03), that is u_m = max(f, 0.03 D_obs); f 5 um bare, 10 um powder layer or AM block."""
    f = U_M_F_UM["powder_layer_or_am" if (block_kind == "powder_layer" or am_substrate) else "bare_plate"]
    return max(f, U_M_REL_FLOOR * d_obs_um)


def cv_pool(replicated):
    """cv_pool = sqrt(sum (n_c - 1)(s_c / Dbar_c)^2 / sum (n_c - 1)) over the conditions with n_c >= 2.
    `replicated`: iterable of (track_depths) lists. Returns (cv_pool or None, number of conditions, pooled df)."""
    num, df, k = 0.0, 0, 0
    for depths in replicated:
        n = len(depths)
        if n < 2:
            continue
        mean = math.fsum(depths) / n
        s2 = math.fsum((x - mean) ** 2 for x in depths) / (n - 1)
        num += (n - 1) * s2 / mean ** 2
        df += n - 1
        k += 1
    if k < CV_POOL_MIN_CONDITIONS or df < CV_POOL_MIN_DF:
        return None, k, df
    return math.sqrt(num / df), k, df


def resolution_qualifier(conditions, block_kind, am_substrate):
    """Median over conditions of U_c = 2 sqrt(s_t^2 / n_t + u_m^2) / D_obs,c at most 0.10 (the k = 2 value, scored).
    conditions: list of dicts with `track_depths` (per track means) and optionally `u_m_um` (released).
    A condition with fewer than 2 tracks uses s_t = cv_pool D_obs,c; if cv_pool cannot be formed the qualifier is
    `not_evaluable`, which is a qualifier not met. u_m defaults to max(f, 0.03 D_obs,c), is never zero, is fixed per
    condition, and the block is scored at 1 times the default only; 2 times is reported descriptively."""
    from scipy.stats import t as student_t
    needs_pool = any(len(c["track_depths"]) < 2 for c in conditions)
    cvp, k_rep, df_rep = cv_pool([c["track_depths"] for c in conditions])
    out = {"cv_pool": cvp, "n_replicated_conditions": k_rep, "pooled_df": df_rep, "needs_pool": needs_pool,
           "u_m_assumed": False, "track_counts": [len(c["track_depths"]) for c in conditions]}
    if needs_pool and cvp is None:
        out.update(status="not_evaluable", median_U=None, median_U_2x_descriptive=None, median_U_t_descriptive=None,
                   reason=(f"single track conditions need cv_pool, which needs at least {CV_POOL_MIN_CONDITIONS} "
                           f"conditions with 2 or more tracks and pooled degrees of freedom of at least "
                           f"{CV_POOL_MIN_DF}; got {k_rep} and {df_rep}"))
        return out
    Us, U2, Ut, rows = [], [], [], []
    for c in conditions:
        depths = c["track_depths"]
        n = len(depths)
        d_obs = math.fsum(depths) / n
        if n >= 2:
            s2 = math.fsum((x - d_obs) ** 2 for x in depths) / (n - 1)
        else:
            s2 = (cvp * d_obs) ** 2
        u_rel = c.get("u_m_um")
        if u_rel is None:
            u_m = u_m_default_um(d_obs, block_kind, am_substrate)
            out["u_m_assumed"] = True
        else:
            u_m = float(u_rel)
            if not u_m > 0:
                raise ValueError("u_m must be positive (never 0)")
        U = 2.0 * math.sqrt(s2 / n + u_m ** 2) / d_obs
        U_2x = 2.0 * math.sqrt(s2 / n + (2.0 * u_m) ** 2) / d_obs
        U_t = (float(student_t.ppf(0.975, n - 1)) * math.sqrt(s2 / n + u_m ** 2) / d_obs) if n >= 2 else None
        Us.append(U)
        U2.append(U_2x)
        if U_t is not None:
            Ut.append(U_t)
        rows.append({"n_t": n, "D_obs_um": d_obs, "u_m_um": u_m, "U": U, "U_2x": U_2x, "U_t": U_t})
    med = statistics.median(Us)
    out.update(status="met" if med <= U_MAX else "not_met", median_U=med,
               median_U_2x_descriptive=statistics.median(U2),
               median_U_t_descriptive=statistics.median(Ut) if Ut else None, per_condition=rows,
               reason=None if med <= U_MAX else f"median U_c {med:.4f} above {U_MAX}")
    return out


# ----------------------------------------------------------------------------------------------
# Beam definition (M 666 to 673; FWHM_FACTOR from P3 117)
# ----------------------------------------------------------------------------------------------
def beam_d_um(value_um, definition):
    """d is the D4sigma diameter: 1/e2 and D4sigma as released, FWHM / 0.588705, an unstated definition read as 1/e2
    (flagged, grade C)."""
    if definition in ("1/e2", "D4sigma", "unstated"):
        return float(value_um)
    if definition == "FWHM":
        return float(value_um) / FWHM_FACTOR
    raise ValueError(f"unresolved beam definition {definition!r}")


# ----------------------------------------------------------------------------------------------
# Prediction phase guard (P3 1083 to 1084, M 1036 to 1037, M 1390 to 1396)
# ----------------------------------------------------------------------------------------------
class TargetColumnRequested(PermissionError):
    """A column outside the phase whitelist was requested (for example a target column in the prediction phase)."""


def _fold(name):
    return name.casefold() if isinstance(name, str) else name


def assert_no_target_loaded(source, amendment):
    """Section 6 item 5: the prediction process asserts that no target column was loaded."""
    targets = {_fold(h) for h in amendment["whitelist"]["targets"].values()}
    hit = [c for c in source.columns_loaded if _fold(c) in targets]
    if hit:
        raise TargetColumnRequested(f"target column(s) {hit} were loaded in the prediction phase")
    return True


# ----------------------------------------------------------------------------------------------
# Served index of a row (M 1499 to 1500)
# ----------------------------------------------------------------------------------------------
def served_index(alloy, row, T0_K):
    return pds.normalized_enthalpy(SERVED_NAME[alloy], row["P_W"], row["v_mm_s"], row["d_um"], T0_K - 273.15)


# ----------------------------------------------------------------------------------------------
# Scoring phase: the only phase that reads targets
# ----------------------------------------------------------------------------------------------
def _mean(xs):
    return math.fsum(xs) / len(xs)


def reduce_conditions(rows, depth_map, rows_are_tracks=False):
    """Tracks versus sections (section 1): a track depth is the mean of its sections, a condition depth the mean of its
    independent tracks. Sections are never replicates. Rows without a track key are one track each. Predictions of a
    condition are the mean of its track predictions; a failed track fails the condition for that arm, an unavailable
    track makes the arm unavailable for it. A target that is missing or not positive refuses (no row is dropped for
    looking at a target)."""
    groups = {}
    for r in rows:
        if r["track"] is None and not rows_are_tracks and r["section"] is None:
            if r["condition"] in groups:                            # repeated rows are duplicates, never independent tracks
                raise ValueError(f"condition {r['condition']!r}: repeated rows without a track key and without an "
                                 "owner-text locator that each row is a separate track")
        groups.setdefault(r["condition"], {}).setdefault(r["track"] if r["track"] is not None else f"row{r['ordinal']}",
                                                         []).append(r)
    out = []
    for cond, tracks in groups.items():
        depths, track_preds, indices, first = [], [], [], None
        u_set = {r.get("u_m_um") for trows in tracks.values() for r in trows}
        if len(u_set) > 1:
            raise ValueError(f"condition {cond!r}: a released u_m differs within the condition")
        u_rel = next(iter(u_set))
        for key, trows in tracks.items():
            vals = []
            for r in trows:
                d = (depth_map.get(r["ordinal"]) or {}).get("depth_um")
                if d is None or not d > 0:
                    raise ValueError(f"row {r['ordinal']}: depth is missing or not positive")
                vals.append(d)
            depths.append(_mean(vals))
            track_preds.append({a: _track_value([r["pred"][a] for r in trows]) for a in trows[0]["pred"]})
            indices.append(_mean([r["index"] for r in trows]))
            first = first or trows[0]
        pred = {}
        for a in track_preds[0]:
            vals = [tp[a] for tp in track_preds]
            if any(isinstance(v, dict) and v["status"] == "failed" for v in vals):
                pred[a] = {"status": "failed", "reason": next(v["reason"] for v in vals if isinstance(v, dict))}
            elif any(isinstance(v, dict) for v in vals):
                pred[a] = {"status": "unavailable", "reason": next(v["reason"] for v in vals if isinstance(v, dict))}
            else:
                pred[a] = _mean(vals)
        out.append({"condition": cond, "beam_setting": first["beam_setting"], "P_W": first["P_W"],
                    "v_mm_s": first["v_mm_s"], "d_um": first["d_um"], "index": _mean(indices), "n_tracks": len(tracks),
                    "track_depths": depths, "D_obs_um": _mean(depths), "u_m_um": u_rel, "pred": pred,
                    "ledger": next(iter(tracks.values()))[0].get("ledger", {}),
                    "convergence": next(iter(tracks.values()))[0].get("convergence")})
    return out


def _track_value(vals):
    for v in vals:
        if isinstance(v, dict) and v["status"] == "failed":
            return v
    for v in vals:
        if isinstance(v, dict):
            return v
    return _mean(vals)


def arm_rels(conds, arm_id):
    """rel_c = (D_pred - D_obs)/D_obs per condition; a model failure is +infinity, an unavailable condition is left out of
    that arm (listed). Returns (rels, names, unavailable names)."""
    rels, names, unavailable = [], [], []
    for c in conds:
        p = c["pred"][arm_id]
        if isinstance(p, dict):
            if p["status"] == "failed":
                rels.append(INF)
                names.append(c["condition"])
            else:
                unavailable.append(c["condition"])
            continue
        rels.append((p - c["D_obs_um"]) / c["D_obs_um"])
        names.append(c["condition"])
    return rels, names, unavailable


def leverage_qualifier(conds, alloy):
    """Section 5 item 4 on the served index of the measured inputs (never P*): at least 4 conditions below the cut and at
    least 4 at or above 20."""
    cut = LEVERAGE_LOW_CUT[alloy]
    below = sum(1 for c in conds if c["index"] < cut)
    above = sum(1 for c in conds if c["index"] >= LEVERAGE_HIGH_CUT)
    return {"cut": cut, "n_below": below, "n_at_or_above_20": above, "ok": below >= SIDE_MIN and above >= SIDE_MIN}


def block_verdict(rels, *, leverage_ok, resolution_status, issues=(), exposed=False, scored=True):
    """Verdict precedence (section 5 as overridden by Amendment 6): exposure overrides all; a block that is not scored is
    descriptive; INCONCLUSIVE for n < 12 or a block level metadata item; FAIL for any of the four thresholds with
    leverage and resolution reported as qualifiers; INCONCLUSIVE when all four thresholds are met and leverage or the
    resolution qualifier (including `not_evaluable`) is not met; otherwise PASS."""
    stats = block_statistics(rels)
    out = {"stats": stats, "qualifiers": {"leverage_ok": bool(leverage_ok), "resolution": resolution_status},
           "issues": list(issues)}
    if exposed:
        out.update(status="EXPOSED_DESCRIPTIVE", reason="a target was read before the prediction hash (section 5 item 6)")
    elif not scored:
        out.update(status="DESCRIPTIVE_NOT_SCORED", reason="powder layer block without a same-setup absorptance or a "
                   "declared P5 bias (Amendment 6 item 6)")
    elif stats["n"] < N_MIN or issues:
        out.update(status="INCONCLUSIVE", reason="; ".join([f"n = {stats['n']} < {N_MIN}"] * (stats["n"] < N_MIN) + list(issues)))
    elif not stats["all_thresholds_met"]:
        failed = [k for k, v in stats["thresholds_met"].items() if not v]
        out.update(status="FAIL", reason="threshold failure: " + ", ".join(failed))
    elif not leverage_ok or resolution_status != "met":
        why = ([] if leverage_ok else ["leverage"]) + ([] if resolution_status == "met" else
                                                       ["resolution " + resolution_status.replace("_", " ")])
        out.update(status="INCONCLUSIVE", reason="all four thresholds met; qualifier not met: " + ", ".join(why))
    else:
        out.update(status="PASS", reason="all four thresholds met, leverage and resolution met")
    return out


def served_bins(conds, rels_by_name, alloy):
    """n and mean signed relative error of the three served index bins (Amendment 4 item 5)."""
    cut = LEVERAGE_LOW_CUT[alloy]
    out = {}
    for name in ("below", "between", "at_or_above"):
        vals = [rels_by_name[c["condition"]] for c in conds if c["condition"] in rels_by_name
                and index_bins(c["index"], cut) == name]
        fin = [v for v in vals if math.isfinite(v)]
        out[name] = {"n": len(vals), "mean_signed": (math.fsum(fin) / len(fin)) if fin else None,
                     "n_failed": len(vals) - len(fin)}
    return out


def fragile_flips(per_arm, candidate, nominal_status):
    """The fragile flip block of the runner's `score_phase` (M 1852 to 1862), unchanged, as a function. `per_arm` maps
    arm id to {"spec": {"kind": ...}, "verdict": {"status": ...}, ...}; `nominal_status` is the candidate's status.
    Returns {"input": [arm ids], "property": [arm ids]}."""
    flips = {"input": [], "property": []}
    if nominal_status == "PASS":
        for aid, e in per_arm.items():
            if not aid.startswith(candidate + "|"):
                continue
            kind_a = e["spec"]["kind"]               # joint beam and power arms: input; property and absorptance arms:
            if e["verdict"]["status"] != "PASS":     # property; single-setting beam arms and descriptive arms: neither
                if kind_a in ("power", "beam"):
                    flips["input"].append(aid)
                elif kind_a in ("property", "absorptance"):
                    flips["property"].append(aid)
    return flips


# ----------------------------------------------------------------------------------------------
# Exact paired sign flip test (P3 830 to 895)
# ----------------------------------------------------------------------------------------------
def signflip_p_enumerate(D, tol=TIE_TOL):
    """Exact one sided paired sign-flip p = P(T_flip >= T_obs), T = sum D, over all 2^n sign assignments of the nonzero
    D_i (n <= 24). Computed as exact counting by splitting the nonzero magnitudes in two halves: the assignments with
    T_flip >= T_obs are the subsets S of magnitudes with sum(S) <= sum of the magnitudes carrying a negative sign.
    A relative tolerance of 1e-12 on ties."""
    D = [x for x in D if abs(x) > tol]
    n = len(D)
    if n > ENUMERATION_MAX_N:
        raise ValueError("enumeration is declared for up to 24 nonzero differences")
    if n == 0:
        return 1.0
    m = [abs(x) for x in D]
    neg = math.fsum(abs(x) for x in D if x < 0)
    limit = neg + 1e-12 * math.fsum(m)
    half = n // 2

    def subset_sums(items):
        s = np.zeros(1)
        for x in items:
            s = np.concatenate([s, s + x])
        return s
    a, b = subset_sums(m[:half]), np.sort(subset_sums(m[half:]))
    counts = np.searchsorted(b, limit - a, side="right")
    return float(int(counts.sum()) / 2 ** n)


def _dp_p(int_magnitudes, int_negative_sum):
    """P(random subset sum <= L) on integer magnitudes, float64 probability mass, L = sum of the negative-sign items."""
    L = int(int_negative_sum)
    if L > 400_000_000:
        raise ValueError("dynamic programming table too large for the declared resolution")
    f = np.zeros(L + 1)
    f[0] = 1.0
    for m in int_magnitudes:
        if m <= 0:
            continue
        shifted = 0.5 * f[:max(0, L + 1 - m)] if m <= L else None
        f *= 0.5
        if shifted is not None:
            f[m:] += shifted
    return float(f.sum())


def signflip_p_dp(D, scale=DP_SCALE, tol=TIE_TOL):
    """Exact dynamic programming above 24 nonzero differences: D scaled to integers at 1e-6, p computed once with
    every magnitude rounded down and once rounded up, the larger p is taken (section 5.3 item 7)."""
    D = [x for x in D if abs(x) > tol]
    if not D:
        return {"p": 1.0, "p_down": 1.0, "p_up": 1.0}
    out = {}
    for name, rnd in (("p_down", math.floor), ("p_up", math.ceil)):
        ints = [int(rnd(abs(x) * scale)) for x in D]
        neg = sum(i for i, x in zip(ints, D) if x < 0)
        out[name] = _dp_p(ints, neg)
    out["p"] = max(out["p_down"], out["p_up"])
    return out


def signflip_p(D, tol=TIE_TOL):
    """p for the declared statistic, enumeration for up to 24 nonzero differences, DP above."""
    nz = [x for x in D if abs(x) > tol]
    if len(nz) <= ENUMERATION_MAX_N:
        p = signflip_p_enumerate(nz, tol)
        return {"p": p, "method": "enumeration", "n_nonzero": len(nz)}
    dp = signflip_p_dp(nz, tol=tol)
    return {**dp, "method": "dp_rounded_down_and_up", "n_nonzero": len(nz)}


# ----------------------------------------------------------------------------------------------
# Paired differences (P3 901 to 916)
# ----------------------------------------------------------------------------------------------
def paired_differences(r_flat, r_arm, arm_failed):
    """D_i = r_flat - r_arm (positive when the arm is closer). Tied +infinity rows give 0. A numerical failure of the arm
    (r_arm = +infinity with a finite flat error) gives minus the largest finite |D_j| of the block (0 if none)."""
    D, pending = [], []
    for i, (rf, ra, failed) in enumerate(zip(r_flat, r_arm, arm_failed)):
        if failed and math.isfinite(rf):
            D.append(None)
            pending.append(i)
        elif math.isinf(rf) or math.isinf(ra):
            D.append(0.0)                                   # tie: missed onset, none observed, or both undefined
        else:
            D.append(rf - ra)
    largest = max([abs(x) for x in D if x is not None] or [0.0])
    for i in pending:
        D[i] = -largest
    return D
