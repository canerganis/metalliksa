"""Tests for python/lpbf_blind_stats.py, the verbatim extraction of the MELT runner's pure statistical functions.

Everything here is synthetic: no measured value and no data file is read. Synthetic ids carry the word `synthetic`.

Three layers show that the extraction changed no behaviour:
  1. Source identity. Every extracted function, class and constant line hashes to the SHA-256 of the same line range
     of the original blob (`GOLDEN_SOURCE_SHA256`).
  2. Golden vectors. `GOLDEN_VECTORS` holds the outputs of the ORIGINAL runner functions on the synthetic cases of
     `build_cases()`. They were produced by `--write-golden`: the original files are written with `git show` into a
     temp folder and run in a child process that never imports lpbf_blind_stats. The fragile flip block is inline code
     in the runner's `score_phase`, so its vectors come from `score_phase` itself on synthetic predictions and
     targets, compared with the extracted functions composed the same way (`_extracted_score`).
  3. Live check, when the research commits are in this checkout: the child runs again and its output must equal the
     extracted outputs in this interpreter exactly, and the golden vectors.

Served index cases replace the module's `pds` with a recorder on both sides, so the vectors pin the call (served alloy
name, P, v, d, T0 in C) and not served physics, which may move in a served bump without touching this extraction.

Golden values are exact in the generating environment (`GOLDEN_ENV`). With another numpy or scipy version (the Student t
quantile of the resolution qualifier, the bootstrap generator) floats are compared at a relative 1e-12; everything else
stays exact. The live check is always exact.

Regenerate (only when a case is added): python -B test_lpbf_blind_stats.py --write-golden
"""
from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import inspect
import json
import math
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace

PYTHON_DIR = Path(__file__).resolve().parent
REPO_DIR = PYTHON_DIR.parent
THIS_FILE = Path(__file__).resolve()
MODULE_FILE = PYTHON_DIR / "lpbf_blind_stats.py"
CHILD_MODE = __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "--child"

if not CHILD_MODE:
    sys.path.insert(0, str(PYTHON_DIR))
    import lpbf_blind_stats as bs  # noqa: E402

INF = math.inf
NAN = math.nan

# The original files the child process imports: (commit, path, git blob id, folder in the temp dir). The MELT runner
# imports its sibling P3 runner and sketch at e91d0fbd; the sign flip functions are taken from the P3 runner at c4470b01
# (their text is identical in both P3 blobs).
ORIGINAL_FILES = (
    ("e91d0fbda10b9b01e974dd9838aae026e1cdd91c", "python/tools/run_lpbf_melt_depth.py",
     "2bff1378fc4d23d2528c6834ea096f541228906c", "e91d0fbd"),
    ("e91d0fbda10b9b01e974dd9838aae026e1cdd91c", "python/tools/run_lpbf_p3_cavity.py",
     "ffd96300d3af6a3b8e18ca3651a6f81d02637f7e", "e91d0fbd"),
    ("e91d0fbda10b9b01e974dd9838aae026e1cdd91c", "python/tools/p3_cavity_model_sketch.py",
     "b762dc6268b82f15f9e1fe529845b5e3e9013415", "e91d0fbd"),
    ("c4470b017cfe533c74b23dc5712a2df720ae00c4", "python/tools/run_lpbf_p3_cavity.py",
     "cc0f5528bca6fdca94bb4974b4fb3876795512a6", "c4470b01"),
)
SOURCE_FILE_OF = {"M": ("e91d0fbd", "python/tools/run_lpbf_melt_depth.py"),
                  "P3": ("c4470b01", "python/tools/run_lpbf_p3_cavity.py")}
FRAGILE_FIRST_LINE = '    flips = {"input": [], "property": []}'


def _provenance():
    """PROVENANCE of the extracted module, read from its source without importing it (the child must not import it)."""
    tree = ast.parse(MODULE_FILE.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and [getattr(t, "id", None) for t in node.targets] == ["PROVENANCE"]:
            return ast.literal_eval(node.value)
    raise AssertionError("PROVENANCE not found in lpbf_blind_stats.py")


PROV = _provenance()
CONSTANT_NAMES = tuple(n for n in PROV if n == n.upper())


# ----------------------------------------------------------------------------------------------
# Synthetic inputs
# ----------------------------------------------------------------------------------------------
def _up(x):
    return math.nextafter(x, math.inf)


TWELVE_REL = [0.05, -0.12, 0.08, 0.15, -0.03, 0.11, -0.07, 0.02, 0.19, -0.16, 0.04, 0.09]   # all four thresholds met
TWELVE_APE = [abs(x) for x in TWELVE_REL]
FAIL12 = [0.25] * 12                                                                           # median and bias fail
# Exact threshold boundaries: each *_AT set sits on one threshold and meets all four; each *_ABOVE set moves that one
# statistic to the next representable value above and fails it alone.
MEDIAN_AT = [0.01, -0.01, 0.02, -0.02, 0.03, 0.20, -0.20, 0.21, -0.21, 0.22, -0.22, 0.25]
MEDIAN_ABOVE = [0.01, -0.01, 0.02, -0.02, 0.03, _up(0.20), -_up(0.20), 0.21, -0.21, 0.22, -0.22, 0.25]
P90_AT = [0.01, -0.01, 0.02, -0.02, 0.03, -0.03, 0.04, -0.04, 0.05, 0.35, -0.35, 0.40]
P90_ABOVE = [0.01, -0.01, 0.02, -0.02, 0.03, -0.03, 0.04, -0.04, 0.05, _up(0.35), -_up(0.35), 0.40]
BIAS_AT_POS, BIAS_ABOVE_POS = [0.1] * 12, [_up(0.1)] * 12
BIAS_AT_NEG, BIAS_ABOVE_NEG = [-0.1] * 12, [-_up(0.1)] * 12
MAX_AT = [0.5, 0.01, -0.01, 0.02, -0.02, 0.03, -0.03, 0.04, -0.04, 0.05, -0.05, -0.05]
MAX_ABOVE = [_up(0.5)] + MAX_AT[1:]
BOUNDARY_SETS = (("median", MEDIAN_AT, MEDIAN_ABOVE), ("p90", P90_AT, P90_ABOVE),
                 ("mean_signed", BIAS_AT_POS, BIAS_ABOVE_POS), ("mean_signed", BIAS_AT_NEG, BIAS_ABOVE_NEG),
                 ("max_ape", MAX_AT, MAX_ABOVE))
D24 = [((-1) ** i) * (0.01 * (i + 1)) for i in range(24)]
D25 = D24 + [0.3]
D30 = [(-1.0 if i % 3 == 0 else 1.0) * (0.001 * (i + 1) + 0.0003) for i in range(30)]
FAILED = {"status": "failed", "reason": "synthetic solver failure"}
UNAVAILABLE = {"status": "unavailable", "reason": "synthetic arm unavailable"}
LOCATED = ("alloy", "block_kind", "am_substrate", "T0_K", "atmosphere", "surface_preparation", "thickness_mm",
           "chemistry_S_O")


def _row(ordinal, cond, track, section, pred, *, index=10.0, u=None, ledger=None, conv=None):
    r = {"ordinal": ordinal, "condition": cond, "track": track, "section": section, "beam_setting": "A",
         "P_W": 200.0, "v_mm_s": 1000.0, "d_um": 80.0, "u_m_um": u, "index": index, "pred": pred}
    if ledger is not None:
        r["ledger"] = ledger
    if conv is not None:
        r["convergence"] = conv
    return r


def _amendment(alloy, block_kind, *, exposed, track_key, rows_are_tracks):
    """A synthetic run amendment in the closed form the runner validates (metadata only, no data file is opened)."""
    inputs = {"P_W": "synthetic P", "v_mm_s": "synthetic v", "condition": "synthetic condition"}
    if track_key:
        inputs.update(track="synthetic track", section="synthetic section")
    consts = {"block_id": "SYNTHETIC-BLOCK", "alloy": alloy, "block_kind": block_kind, "am_substrate": False,
              "T0_K": 293.15, "atmosphere": "synthetic argon", "surface_preparation": "synthetic ground",
              "thickness_mm": 10.0, "chemistry_S_O": "certified", "locators": {k: "synthetic locator" for k in LOCATED}}
    if alloy == "Ti64":
        ca = {"commit": "d2ba34951d369764ce0c57fdbc0455a4303d3960", "substrate_state": None,
              "substrate_state_locator": None}
    else:
        ca = {"commit": "61ced164703a000976d4306fab661a21806e0d1c", "substrate_state": "AB",
              "substrate_state_locator": "synthetic locator"}
    return {
        "whitelist": {"file": "synthetic_inputs.csv", "sheet": None, "inputs": inputs,
                      "targets": {"depth_um": "synthetic depth"}, "constants": consts, "target_source": None},
        "served_commit": "0" * 40, "p1_commit": "0" * 40, "p3_verdict_commit": "0" * 40,
        "constants_amendment": ca, "candidate_arm": "S1",
        "beam": {"kind": "measured", "focus_offset": None,
                 "settings": {"A": {"value_um": 80.0, "definition": "1/e2", "locator": "synthetic locator",
                                    "u_k1_um": None}}},
        "powder_absorptance_or_p5_bias": None,
        "datum_statement": {"datum": "original_surface", "locator": "synthetic locator",
                            "figure_viewed_by_custodial_reader": False},
        "track_section_protocol": {"reduction": "per_track_mean_of_sections" if track_key else "track_value_released",
                                   "sections_per_track": 2, "etchant": "synthetic", "boundary_selection": "synthetic",
                                   "blind_to_settings": True,
                                   "rows_are_separate_tracks_locator": ("synthetic locator" if rows_are_tracks
                                                                        else None)},
        "grades": {"power": "B", "beam": "B", "block": "B", "power_facts": {"basis": "measured"},
                   "beam_facts": {"basis": "measured", "definition_stated": True}},
        "cavity_physics_statement": "not scored",
        "exposure_exclusions": {"labels": [], "exposed_before_prediction_hash": exposed,
                                "independent_of_spent_data": True},
        "data_hashes": {"synthetic_inputs.csv": "0" * 64},
    }


def _scenario(alloy, conds, arms, *, block_kind="bare_plate", exposed=False, track_key=True, rows_are_tracks=False,
              issues=()):
    """(prediction, targets) of a synthetic block. `conds`: dicts with `index`, `tracks` (section depths per track),
    optional `u_m` and `pred` {arm: factor, "failed", "unavailable" or (factor, {track index: "failed"|"unavailable"})}.
    A predicted depth is factor times the nominal condition depth."""
    rows, targets, ordinal = [], {}, 2
    for ci, c in enumerate(conds):
        cond = f"synthetic-c{ci + 1:02d}"
        track_means = [math.fsum(s) / len(s) for s in c["tracks"]]
        d_nom = math.fsum(track_means) / len(track_means)
        for ti, sections in enumerate(c["tracks"]):
            pred = {}
            for aid, _kind in arms:
                spec = c["pred"][aid]
                factor, per_track = (spec if isinstance(spec, tuple) else (spec, {}))
                state = per_track.get(ti, factor if isinstance(factor, str) else None)
                if state == "failed":
                    pred[aid] = dict(FAILED)
                elif state == "unavailable":
                    pred[aid] = dict(UNAVAILABLE)
                else:
                    pred[aid] = factor * d_nom
            for si, depth in enumerate(sections):
                rows.append(_row(ordinal, cond, f"t{ti + 1}" if track_key else None,
                                 f"s{si + 1}" if track_key else None, pred, index=c["index"], u=c.get("u_m")))
                targets[ordinal] = {"depth_um": depth, "width_um": None, "cap_um": None}
                ordinal += 1
    prediction = {"run_amendment": _amendment(alloy, block_kind, exposed=exposed, track_key=track_key,
                                              rows_are_tracks=rows_are_tracks),
                  "candidate_arm": "S1", "p3_pass_on_record": False, "block_level_issues": list(issues),
                  "arms": [{"arm_id": aid, "base": "S1", "kind": kind, "label": f"synthetic {aid}"}
                           for aid, kind in arms],
                  "rows": rows, "excluded": []}
    return prediction, targets


ERR14 = [0.05, -0.04, 0.03, -0.06, 0.02, 0.07, -0.05, 0.01, -0.02, 0.04, -0.03, 0.06, -0.01, 0.0]
ARMS_A = (("C0", "nominal"), ("S1", "nominal"), ("C0-srv", "descriptive"), ("S1-srv", "descriptive"),
          ("S1|power:0.95", "power"), ("S1|power:1.05", "power"), ("S1|beam:joint0", "beam"),
          ("S1|beam:joint1", "beam"), ("S1|beam:A:0", "beam_single"), ("S1|prop:synthetic_set", "property"),
          ("S1|prop:srv", "descriptive"), ("S1|abs:synthetic_lo", "absorptance"))


def _scenario_pass_with_flips():
    """Ti64, 14 conditions, 2 tracks (2 and 1 sections): nominal PASS; power 0.95 and joint beam 1 flip (input), the
    property set flips (property); a single-setting beam arm and a descriptive arm fail without a flip."""
    idx = [8.0, 9.0, 10.0, 11.0, 12.0, 16.0, 17.0, 18.0, 19.0, 21.0, 23.0, 25.0, 27.0, 30.0]
    conds = []
    for i, (x, e) in enumerate(zip(idx, ERR14)):
        d = 150.0 + 10.0 * i
        pred = {"C0": 0.7, "S1": 1 + e, "C0-srv": 0.75, "S1-srv": 1 + e, "S1|power:0.95": 1 + e - 0.12,
                "S1|power:1.05": (1 + e + 0.02, {1: "unavailable"} if i == 2 else {}), "S1|beam:joint0": 1 + e,
                "S1|beam:joint1": (1 + e, {0: "failed"} if i == 4 else {}), "S1|beam:A:0": 0.6,
                "S1|prop:synthetic_set": 1 + e + 0.3, "S1|prop:srv": 0.5, "S1|abs:synthetic_lo": 1 + e}
        conds.append({"index": x, "tracks": [[d * 1.01, d * 0.99], [d * 1.005]], "pred": pred})
    return _scenario("Ti64", conds, ARMS_A)


def _scenario_fail_alsi():
    """AlSi10Mg, 13 single-track conditions: nominal FAIL (bias), resolution not evaluable (no cv_pool), one failed and
    one unavailable condition."""
    arms = (("C0", "nominal"), ("S1", "nominal"), ("S1|power:0.95", "power"), ("S1|prop:srv", "property"),
            ("S1|abs:0.14", "absorptance"))
    idx = [6.0, 9.0, 12.0, 14.0, 15.0, 16.0, 18.0, 20.0, 22.0, 24.0, 26.0, 28.0, 31.0]
    conds = []
    for i, x in enumerate(idx):
        e = ERR14[i]
        pred = {"C0": 0.8, "S1": "failed" if i == 6 else 1.15 + e, "S1|power:0.95": 1 + e, "S1|prop:srv": 1 + e,
                "S1|abs:0.14": "unavailable" if i == 1 else 1 + e}
        conds.append({"index": x, "tracks": [[120.0 + 7.0 * i]], "pred": pred})
    return _scenario("AlSi10Mg", conds, arms)


def _scenario_leverage_not_met():
    """Ti64, rows are separate tracks without a track key (3 per condition): thresholds met, leverage not met."""
    arms = (("C0", "nominal"), ("S1", "nominal"), ("S1|power:0.95", "power"))
    idx = [5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 21.0, 22.0, 23.0]
    conds = [{"index": x, "tracks": [[200.0 + 5 * i], [202.0 + 5 * i], [198.5 + 5 * i]],
              "pred": {"C0": 0.85, "S1": 1 + ERR14[i], "S1|power:0.95": 1 + ERR14[i] - 0.2}} for i, x in enumerate(idx)]
    return _scenario("Ti64", conds, arms, track_key=False, rows_are_tracks=True)


def _scenario_exposed():
    arms = (("C0", "nominal"), ("S1", "nominal"), ("S1|power:0.95", "power"))
    idx = [8.0, 9.0, 10.0, 11.0, 16.0, 17.0, 18.0, 19.0, 21.0, 23.0, 25.0, 27.0]
    conds = [{"index": x, "tracks": [[160.0 + 4 * i], [163.0 + 4 * i]],
              "pred": {"C0": 0.7, "S1": 1 + ERR14[i], "S1|power:0.95": 0.8}} for i, x in enumerate(idx)]
    return _scenario("Ti64", conds, arms, exposed=True)


def _scenario_small_with_issue():
    arms = (("C0", "nominal"), ("S1", "nominal"))
    idx = [8.0, 9.0, 10.0, 11.0, 16.0, 17.0, 18.0, 21.0, 23.0, 25.0, 27.0]
    conds = [{"index": x, "tracks": [[160.0 + 4 * i], [163.0 + 4 * i]], "pred": {"C0": 0.7, "S1": 1 + ERR14[i]}}
             for i, x in enumerate(idx)]
    return _scenario("Ti64", conds, arms, issues=("synthetic block issue",))


def _scenario_powder_not_scored():
    """Ti64 powder layer without an absorptance or a P5 bias: descriptive, not scored; u_m released on half."""
    arms = (("C0", "nominal"), ("S1", "nominal"), ("S1|power:0.95", "power"))
    idx = [8.0, 9.0, 10.0, 11.0, 16.0, 17.0, 18.0, 19.0, 21.0, 23.0, 25.0, 27.0]
    conds = [{"index": x, "tracks": [[90.0 + 3 * i], [92.0 + 3 * i]], "u_m": 4.0 if i % 2 else None,
              "pred": {"C0": 0.7, "S1": 1 + ERR14[i], "S1|power:0.95": 0.8}} for i, x in enumerate(idx)]
    return _scenario("Ti64", conds, arms, block_kind="powder_layer")


SCENARIOS = {"score-pass-with-flips": _scenario_pass_with_flips, "score-fail-alsi": _scenario_fail_alsi,
             "score-leverage-not-met": _scenario_leverage_not_met, "score-exposed": _scenario_exposed,
             "score-small-with-issue": _scenario_small_with_issue,
             "score-powder-not-scored": _scenario_powder_not_scored}


def build_cases():
    """Every golden case: {"id", "fn", "args", "kwargs"}. Inputs are synthetic and built the same way on both sides."""
    cases = []

    def add(cid, fn, *args, **kwargs):
        cases.append({"id": cid, "fn": fn, "args": list(args), "kwargs": kwargs})

    add("constants", "__constants__")
    for i, x in enumerate((0.1, 0.35, 1, 2.5e-7, -0.2, 1e22)):
        add(f"fr-{i}", "_fr", x)
    for i, x in enumerate((Fraction(1, 3), 0.25, INF, Fraction(-7, 2))):
        add(f"to-float-{i}", "_to_float", x)
    for i, (s, t) in enumerate(((Fraction(1, 5), "0.20"), (Fraction(repr(_up(0.2))), "0.20"), (INF, "0.50"),
                                (NAN, "0.50"), (Fraction(7, 20), "0.35"), (Fraction(-1, 10), "0.10"))):
        add(f"le-{i}", "_le", s, t)
    rq = (([], 1, 2), ([0.3], 1, 2), ([0.3], 9, 10), ([0.1, 0.2, 0.3], 1, 2), ([0.1, 0.2, 0.3, 0.4], 1, 2),
          ([0.4, 0.1, 0.3, 0.2], 9, 10), ([0.1, 0.2, INF], 1, 2), ([0.1, 0.2, 0.3, INF], 1, 2),
          ([0.1, 0.2, INF, INF], 1, 2), ([0.1, INF], 1, 2), ([INF, INF, INF], 1, 2), ([INF], 9, 10),
          (TWELVE_APE, 1, 2), (TWELVE_APE, 9, 10), (TWELVE_APE, 3, 4), (TWELVE_APE[:11] + [INF], 9, 10),
          (TWELVE_APE[:10] + [INF, INF], 9, 10), ([3, 1, 2], 1, 2), ([-0.2, 0.1], 1, 2), ([0.05] * 7, 9, 10))
    for i, (vals, num, den) in enumerate(rq):
        add(f"rank-quantile-{i:02d}", "rank_quantile_exact", vals, num, den)
    for name in ("percentile90", "median_rank", "p75"):
        for i, vals in enumerate(([], TWELVE_APE, TWELVE_APE[:11] + [INF], [0.1, 0.2, 0.3, 0.4, 0.5])):
            add(f"{name}-{i}", name, vals)
    for i, vals in enumerate(([0.1, -0.05, 0.2], [0.1, INF], [INF], [], [-0.1] * 12, TWELVE_REL, [0.1, -INF])):
        add(f"mean-signed-{i}", "mean_signed_exact", vals)
    stats_sets = [TWELVE_REL, TWELVE_REL[:11] + [INF], [], [INF] * 3, [0.3] * 12, FAIL12]
    for _key, at, above in BOUNDARY_SETS:
        stats_sets += [at, above]
    for i, vals in enumerate(stats_sets):
        add(f"block-statistics-{i:02d}", "block_statistics", vals)
    fourteen = TWELVE_REL + [INF, -0.21]
    add("bootstrap-twelve", "bootstrap_intervals", TWELVE_REL)
    add("bootstrap-fourteen-inf", "bootstrap_intervals", fourteen)
    add("bootstrap-empty", "bootstrap_intervals", [])
    add("bootstrap-all-inf", "bootstrap_intervals", [INF] * 3)
    add("bootstrap-custom", "bootstrap_intervals", TWELVE_REL, B=50, seed=7)
    add("bootstrap-marginal", "bootstrap_intervals", MEDIAN_AT)
    for i, (args, kw) in enumerate((((10.0, 15.0), {}), ((15.0, 15.0), {}), ((19.999, 15.0), {}), ((20.0, 15.0), {}),
                                    ((25.0, 15.0), {}), ((12.0, 10.0), {"high": 12.0}), ((11.0, 10.0, 12.0), {}))):
        add(f"index-bins-{i}", "index_bins", *args, **kw)
    power_facts = ({}, {"basis": "commanded"}, {"basis": "measured"}, {"basis": "Measured"},
                   {"basis": "measured", "meter_named": True, "at_workpiece": True, "released_uncertainty": True},
                   {"basis": "measured", "meter_named": True, "at_workpiece": True, "released_uncertainty": "yes"},
                   {"basis": "measured", "meter_named": True, "at_workpiece": False, "released_uncertainty": True},
                   {"basis": None})
    for i, f in enumerate(power_facts):
        add(f"power-grade-{i}", "power_grade", f)
    beam_facts = ({}, {"basis": "nominal"}, {"basis": "measured"}, {"basis": "measured", "definition_stated": "yes"},
                  {"basis": "measured", "definition_stated": True},
                  {"basis": "measured", "definition_stated": True, "work_plane": True, "released_uncertainty": True},
                  {"basis": "measured", "definition_stated": True, "work_plane": True},
                  {"basis": "measured", "definition_stated": False, "work_plane": True, "released_uncertainty": True})
    for i, f in enumerate(beam_facts):
        add(f"beam-grade-{i}", "beam_grade", f)
    for p in "ABC":
        for b in "ABC":
            add(f"block-grade-{p}{b}", "block_grade", p, b)
    for i, args in enumerate(((100.0, "bare_plate", False), (300.0, "bare_plate", False),
                              (100.0, "powder_layer", False), (100.0, "bare_plate", True),
                              (500.0, "powder_layer", True), (166.0, "bare_plate", False))):
        add(f"u-m-default-{i}", "u_m_default_um", *args)
    pools = ([], [[100.0, 104.0]], [[100.0, 104.0], [200.0, 190.0], [150.0, 151.0]], [[100.0, 104.0], [200.0, 190.0]],
             [[100.0, 104.0, 98.0], [200.0, 190.0, 195.0]], [[100.0], [100.0, 102.0], [100.0, 101.0], [90.0, 95.0]],
             [[100.0, 100.0], [50.0, 50.0], [70.0, 70.0]], [[120.0, 121.0, 119.5, 122.0], [80.0, 82.0], [60.0, 61.0]])
    for i, rep in enumerate(pools):
        add(f"cv-pool-{i}", "cv_pool", rep)
    rep3 = [{"track_depths": [150.0, 151.0]}, {"track_depths": [200.0, 198.0]}, {"track_depths": [180.0, 183.0, 181.0]}]
    res_cases = (
        ("all-replicated", rep3, "bare_plate", False),
        ("released-u-m", [dict(c, u_m_um=4.0) for c in rep3], "bare_plate", False),
        ("singles-with-pool", rep3 + [{"track_depths": [170.0]}], "bare_plate", False),
        ("singles-without-pool", [{"track_depths": [150.0]}, {"track_depths": [200.0, 198.0]},
                                  {"track_depths": [170.0]}], "bare_plate", False),
        ("not-met", [{"track_depths": [100.0, 140.0]}, {"track_depths": [200.0, 150.0]},
                     {"track_depths": [120.0, 180.0]}], "bare_plate", False),
        ("u-m-zero", [dict(c, u_m_um=0.0) for c in rep3], "bare_plate", False),
        ("powder-layer", rep3, "powder_layer", False),
        ("am-mixed-release", [rep3[0], dict(rep3[1], u_m_um=6.0), rep3[2]], "bare_plate", True),
        ("u-m-text", [dict(c, u_m_um="5") for c in rep3], "bare_plate", False),
    )
    for name, conds, kind, am in res_cases:
        add(f"resolution-{name}", "resolution_qualifier", conds, kind, am)
    for i, args in enumerate(((80, "1/e2"), (80.0, "D4sigma"), (80.0, "unstated"), (47.0964, "FWHM"),
                              (80.0, "fwhm"), (80.0, "radius"), ("80", "1/e2"))):
        add(f"beam-d-{i}", "beam_d_um", *args)
    amend = {"whitelist": {"targets": {"depth_um": "Depth (um)", "width_um": "synthetic width"}}}
    for i, cols in enumerate((["P", "v"], ["P", "v", "depth (UM)"], ["SYNTHETIC WIDTH", 7, "Depth (um)"], [])):
        add(f"no-target-loaded-{i}", "assert_no_target_loaded", SimpleNamespace(columns_loaded=cols), amend)
    add("fold-0", "_fold", "Depth (UM)")
    add("fold-1", "_fold", 7)
    for i, vals in enumerate(([1.0, 2.0, 4.0], [0.1] * 3, [1, 2])):
        add(f"mean-{i}", "_mean", vals)
    for i, vals in enumerate(([1.0, 2.0], [dict(UNAVAILABLE), dict(FAILED), 1.0], [dict(UNAVAILABLE), 1.0], [3.0])):
        add(f"track-value-{i}", "_track_value", vals)
    srow = {"P_W": 200.0, "v_mm_s": 1000.0, "d_um": 80.0}
    for i, args in enumerate((("Ti64", srow, 293.15), ("AlSi10Mg", srow, 353.15), ("316L", srow, 293.15),
                              ("Ti64", srow, 300))):
        add(f"served-index-{i}", "served_index", *args)
    _reduce_cases(add)
    conds_r = [{"condition": "c1", "D_obs_um": 100.0, "pred": {"S1": 110.0}},
               {"condition": "c2", "D_obs_um": 200.0, "pred": {"S1": dict(FAILED)}},
               {"condition": "c3", "D_obs_um": 150.0, "pred": {"S1": dict(UNAVAILABLE)}},
               {"condition": "c4", "D_obs_um": 80.0, "pred": {"S1": 60.0}}]
    add("arm-rels-0", "arm_rels", conds_r, "S1")
    add("arm-rels-1", "arm_rels", conds_r, "C0")
    add("arm-rels-2", "arm_rels", [], "S1")
    add("arm-rels-3", "arm_rels", conds_r[3:], "S1")
    for i, (idx, alloy) in enumerate((([5, 8, 10, 14.999, 20, 21, 30, 40], "Ti64"),
                                      ([5, 8, 10, 15, 20, 21, 30, 40], "Ti64"),
                                      ([15, 15, 15, 15, 20, 20, 20, 20, 1, 2, 3, 4], "AlSi10Mg"),
                                      ([1, 2, 3, 4, 19.999, 20, 21, 22], "AlSi10Mg"),
                                      ([1, 2, 3, 4, 20, 21, 22, 23], "IN625"))):
        add(f"leverage-{i}", "leverage_qualifier", [{"index": x} for x in idx], alloy)
    verdicts = (
        ("exposed", TWELVE_REL, dict(leverage_ok=True, resolution_status="met", issues=["synthetic issue"],
                                     exposed=True, scored=False)),
        ("not-scored", TWELVE_REL, dict(leverage_ok=True, resolution_status="met", issues=["synthetic issue"],
                                        scored=False)),
        ("n11", TWELVE_REL[:11], dict(leverage_ok=True, resolution_status="met")),
        ("issues", TWELVE_REL, dict(leverage_ok=True, resolution_status="met",
                                    issues=("synthetic issue A", "synthetic issue B"))),
        ("n11-issues", TWELVE_REL[:11], dict(leverage_ok=True, resolution_status="met", issues=["synthetic issue"])),
        ("n11-fail", FAIL12[:11], dict(leverage_ok=True, resolution_status="met")),
        ("fail-median", FAIL12, dict(leverage_ok=True, resolution_status="met")),
        ("fail-several", [0.6, -0.6] * 6, dict(leverage_ok=True, resolution_status="met")),
        ("fail-inf", TWELVE_REL[:11] + [INF], dict(leverage_ok=True, resolution_status="met")),
        ("leverage-not-met", TWELVE_REL, dict(leverage_ok=False, resolution_status="met")),
        ("resolution-not-met", TWELVE_REL, dict(leverage_ok=True, resolution_status="not_met")),
        ("resolution-not-evaluable-and-leverage", TWELVE_REL, dict(leverage_ok=False,
                                                                   resolution_status="not_evaluable")),
        ("pass", TWELVE_REL, dict(leverage_ok=True, resolution_status="met")),
        ("in625-like-threshold-fail", FAIL12, dict(leverage_ok=False, resolution_status="met")),
        ("in625-like-all-met", TWELVE_REL, dict(leverage_ok=False, resolution_status="met")),
        ("leverage-truthy", TWELVE_REL, dict(leverage_ok=1, resolution_status="met")),
        ("empty", [], dict(leverage_ok=True, resolution_status="met")),
        ("exposed-empty", [], dict(leverage_ok=True, resolution_status="met", exposed=True)),
    )
    for name, rels, kw in verdicts:
        add(f"verdict-{name}", "block_verdict", rels, **kw)
    bins_conds = [{"condition": f"c{i}", "index": x} for i, x in enumerate((5, 14.9, 15, 17, 19.99, 20, 25, 30))]
    bins_rels = {"c0": 0.1, "c1": INF, "c2": -0.05, "c3": 0.02, "c5": INF, "c6": 0.04}
    add("served-bins-0", "served_bins", bins_conds, bins_rels, "Ti64")
    add("served-bins-1", "served_bins", bins_conds, bins_rels, "AlSi10Mg")
    add("served-bins-2", "served_bins", bins_conds, {"c5": INF, "c6": INF, "c7": INF}, "Ti64")
    add("served-bins-3", "served_bins", bins_conds, bins_rels, "316L")
    enum_sets = ([], [0.0, 1e-13], [0.1], [-0.1], [0.1, 0.2], [0.2, -0.1], [0.1, 0.1, -0.1], [0.3, -0.3], D24, D25)
    for i, vals in enumerate(enum_sets):
        add(f"signflip-enumerate-{i:02d}", "signflip_p_enumerate", vals)
    add("signflip-enumerate-tol", "signflip_p_enumerate", [0.1, 0.05], tol=0.06)
    for i, args in enumerate((([1, 2, 3], 3), ([0, 5, 2], 2), ([4], 3), ([1], 400_000_001), ([2, 2], 0))):
        add(f"dp-p-{i}", "_dp_p", *args)
    for i, (args, kw) in enumerate((((D30,), {}), (([],), {}), (([1e-13],), {}), ((D30,), {"scale": 1000}))):
        add(f"signflip-dp-{i}", "signflip_p_dp", *args, **kw)
    for i, vals in enumerate(([0.1, 0.2, -0.05, 0.0], D30[:26], D24 + [0.0] * 3, D25)):
        add(f"signflip-p-{i}", "signflip_p", vals)
    pds_cases = (([0.2, 0.1, 0.3], [0.1, 0.15, 0.05], [False, False, False]),
                 ([INF, 0.2, 0.1], [0.1, INF, 0.05], [False, True, False]),
                 ([0.2, 0.3], [INF, 0.1], [True, False]),
                 ([0.2, 0.3], [INF, INF], [True, True]),
                 ([INF], [INF], [True]),
                 ([0.1, 0.2, 0.3], [0.05], [False, False]))
    for i, args in enumerate(pds_cases):
        add(f"paired-differences-{i}", "paired_differences", *args)
    for name, build in SCENARIOS.items():
        add(name, "__score__", *build())
    return cases


def _reduce_cases(add):
    p = {"S1": 110.0, "C0": 90.0}
    rows = [_row(2, "c1", "t1", "s1", p, index=8.0), _row(3, "c1", "t1", "s2", p, index=8.0),
            _row(4, "c1", "t2", "s1", p, index=8.0), _row(5, "c2", "t1", "s1", {"S1": 210.0, "C0": 180.0}, index=22.0),
            _row(6, "c2", "t2", "s1", {"S1": 212.0, "C0": 181.0}, index=22.5)]
    depths = {2: {"depth_um": 101.0}, 3: {"depth_um": 99.0}, 4: {"depth_um": 104.0}, 5: {"depth_um": 200.0},
              6: {"depth_um": 205.0, "width_um": 150.0}}
    add("reduce-sections", "reduce_conditions", rows, depths)
    mixed = [_row(2, "c1", "t1", "s1", {"S1": dict(FAILED), "C0": dict(UNAVAILABLE)}),
             _row(3, "c1", "t2", "s1", {"S1": 100.0, "C0": 95.0}),
             _row(4, "c1", "t3", "s1", {"S1": dict(UNAVAILABLE), "C0": dict(FAILED)})]
    add("reduce-failed-unavailable", "reduce_conditions", mixed, {2: {"depth_um": 100.0}, 3: {"depth_um": 102.0},
                                                                  4: {"depth_um": 98.0}})
    no_track = [_row(2, "c1", None, None, p), _row(3, "c1", None, None, p), _row(4, "c2", None, None, p)]
    nt_depths = {2: {"depth_um": 100.0}, 3: {"depth_um": 104.0}, 4: {"depth_um": 90.0}}
    add("reduce-repeated-without-track", "reduce_conditions", no_track, nt_depths)
    add("reduce-repeated-rows-are-tracks", "reduce_conditions", no_track, nt_depths, True)
    add("reduce-section-without-track", "reduce_conditions",
        [_row(2, "c1", None, "s1", p), _row(3, "c1", None, "s2", p)], {2: {"depth_um": 100.0}, 3: {"depth_um": 104.0}})
    add("reduce-missing-depth", "reduce_conditions", rows, {k: v for k, v in depths.items() if k != 4})
    add("reduce-zero-depth", "reduce_conditions", rows, {**depths, 3: {"depth_um": 0.0}})
    add("reduce-negative-depth", "reduce_conditions", rows, {**depths, 3: {"depth_um": -5.0}})
    add("reduce-none-entry", "reduce_conditions", rows, {**depths, 5: None})
    add("reduce-nan-depth", "reduce_conditions", rows, {**depths, 6: {"depth_um": NAN}})
    add("reduce-u-m-differs", "reduce_conditions", [_row(2, "c1", "t1", "s1", p, u=4.0),
                                                    _row(3, "c1", "t2", "s1", p, u=5.0)],
        {2: {"depth_um": 100.0}, 3: {"depth_um": 101.0}})
    add("reduce-u-m-released", "reduce_conditions", [_row(2, "c1", "t1", "s1", p, u=4.0),
                                                     _row(3, "c1", "t2", "s1", p, u=4.0)],
        {2: {"depth_um": 100.0}, 3: {"depth_um": 101.0}})
    add("reduce-ledger-convergence", "reduce_conditions",
        [_row(2, "c1", "t1", "s1", p, ledger={"S1": {"synthetic": 1.0}}, conv={"rel_diff": 0.001, "flag": False}),
         _row(3, "c1", "t2", "s1", p, ledger={"S1": {"synthetic": 2.0}})],
        {2: {"depth_um": 100.0}, 3: {"depth_um": 99.0}})
    add("reduce-empty", "reduce_conditions", [], {})


# ----------------------------------------------------------------------------------------------
# Canonical form of an output: exact types and values, dict order kept
# ----------------------------------------------------------------------------------------------
class Raised:
    def __init__(self, exc):
        self.kind, self.message = type(exc).__name__, str(exc)


def canon(x):
    t = type(x)
    if x is None or t in (bool, int, str):
        return x
    if t is float:
        return {"$f": repr(x)}
    if t is Fraction:
        return {"$q": f"{x.numerator}/{x.denominator}"}
    if t is list:
        return [canon(v) for v in x]
    if t is tuple:
        return {"$t": [canon(v) for v in x]}
    if t is dict:
        if all(type(k) is str and not k.startswith("$") for k in x):
            return {k: canon(v) for k, v in x.items()}
        return {"$d": [[canon(k), canon(v)] for k, v in x.items()]}
    if t is Raised:
        return {"$raises": [x.kind, x.message]}
    if t.__module__ == "numpy":
        return {"$np": [t.__name__, repr(x.item())]}
    raise TypeError(f"no canonical form for {t!r}")


def dumps(x):
    return json.dumps(canon(x), separators=(",", ":"), ensure_ascii=True)


class _RecordingPds:
    """Stands in for the served `lpbf_public_datasets` in the served index cases: records the call."""

    @staticmethod
    def normalized_enthalpy(*args):
        return {"normalized_enthalpy_called_with": list(args)}


def _sign_test(ref_rels, cand_rels):
    """The runner's `sign_test` (M 1680 to 1687, not extracted), composed from the extracted functions."""
    ref = [abs(x) for x in ref_rels]
    cand = [abs(x) for x in cand_rels]
    D = bs.paired_differences(ref, cand, [math.isinf(c) for c in cand])
    res = bs.signflip_p(D)
    return {"p": res["p"], "n_nonzero": res.get("n_nonzero"), "improves": bool(res["p"] <= 0.05)}


def _extracted_score(prediction, targets):
    """The statistics path of the runner's `score_phase` (M 1833 to 1890), composed from the extracted functions."""
    a = prediction["run_amendment"]
    consts = a["whitelist"]["constants"]
    alloy, kind = consts["alloy"], consts["block_kind"]
    candidate = prediction["candidate_arm"]
    rows = prediction["rows"]
    rows_are_tracks = a["track_section_protocol"]["rows_are_separate_tracks_locator"] is not None
    conds = bs.reduce_conditions(rows, targets, rows_are_tracks)
    exposed = bool(a["exposure_exclusions"]["exposed_before_prediction_hash"])
    scored = not (kind == "powder_layer" and a["powder_absorptance_or_p5_bias"] is None)
    issues = list(prediction["block_level_issues"])
    res = bs.resolution_qualifier([{"track_depths": c["track_depths"], "u_m_um": c["u_m_um"]} for c in conds], kind,
                                  consts["am_substrate"])
    lev = bs.leverage_qualifier(conds, alloy)
    per_arm = {}
    for spec in prediction["arms"]:
        rels, names, unavailable = bs.arm_rels(conds, spec["arm_id"])
        v = bs.block_verdict(rels, leverage_ok=lev["ok"], resolution_status=res["status"], issues=issues,
                             exposed=exposed, scored=scored)
        per_arm[spec["arm_id"]] = {"spec": spec, "verdict": v, "names": names, "rels": rels, "unavailable": unavailable}
    cand = per_arm[candidate]
    flips = bs.fragile_flips(per_arm, candidate, cand["verdict"]["status"])
    paired = {}
    for ref in ("C0", "S1"):
        if ref == candidate:
            continue
        cmap, rmap = dict(zip(cand["names"], cand["rels"])), dict(zip(per_arm[ref]["names"], per_arm[ref]["rels"]))
        keys = [n for n in cand["names"] if n in rmap]
        paired[ref] = _sign_test([rmap[k] for k in keys], [cmap[k] for k in keys]) if keys else {"p": 1.0,
                                                                                               "improves": False}
    rel_by_name = dict(zip(cand["names"], cand["rels"]))
    stats = cand["verdict"]["stats"]
    boot = bs.bootstrap_intervals(cand["rels"]) if cand["rels"] else {}
    arms = {aid: {"kind": e["spec"]["kind"], "label": e["spec"]["label"], "status": e["verdict"]["status"],
                  "reason": e["verdict"]["reason"], **{k: e["verdict"]["stats"][k] for k in
                  ("n", "median", "p75", "p90", "mean_signed", "max_ape", "n_failed", "thresholds_met")},
                  "unavailable_conditions": e["unavailable"]} for aid, e in per_arm.items()}
    return {"status": cand["verdict"]["status"], "fragile": flips, "resolution": res, "leverage": lev,
            "added_value": paired,
            "candidate": {"statistics": stats, "qualifiers": cand["verdict"]["qualifiers"],
                          "reason": cand["verdict"]["reason"], "bootstrap_95": boot},
            "bins": bs.served_bins(conds, rel_by_name, alloy), "input_fragile": bool(flips["input"]),
            "property_fragile": bool(flips["property"]), "u_m_assumed": res["u_m_assumed"],
            "worst_condition": cand["names"][stats["worst_index"]] if stats["worst_index"] is not None else None,
            "track_counts": [c["n_tracks"] for c in conds], "marginal": [k for k, v in boot.items() if v["marginal"]],
            "arms": arms}


def _project_score(r):
    """The same fields, read from the original `score_phase` result."""
    b = r["block"]
    return {"status": r["status"], "fragile": r["fragile"], "resolution": r["resolution"], "leverage": r["leverage"],
            "added_value": r["added_value"], "candidate": r["candidate"], "bins": b["bins"],
            "input_fragile": b["input_fragile"], "property_fragile": b["property_fragile"],
            "u_m_assumed": b["u_m_assumed"], "worst_condition": b["worst_condition"], "track_counts": b["track_counts"],
            "marginal": b["marginal"], "arms": r["arms"]}


class _ExtractedSide:
    def get(self, name):
        return getattr(bs, name)

    def score(self, prediction, targets):
        return _extracted_score(prediction, targets)

    def pds_holder(self):
        return bs


class _OriginalSide:
    def __init__(self, melt, p3):
        self.mods = {"M": melt, "P3": p3}

    def get(self, name):
        return getattr(self.mods[PROV[name][0]], name)

    def score(self, prediction, targets):
        return _project_score(self.mods["M"].score_phase(prediction, targets))

    def pds_holder(self):
        return self.mods["M"]


def run_case(case, side):
    fn = case["fn"]
    args, kwargs = copy.deepcopy(case["args"]), copy.deepcopy(case["kwargs"])
    try:
        if fn == "__constants__":
            out = {n: side.get(n) for n in CONSTANT_NAMES}
        elif fn == "__score__":
            out = side.score(*args)
        elif fn == "served_index":
            holder = side.pds_holder()
            saved, holder.pds = holder.pds, _RecordingPds
            try:
                out = side.get(fn)(*args, **kwargs)
            finally:
                holder.pds = saved
        else:
            out = side.get(fn)(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001  (a raised exception is part of the behaviour under test)
        out = Raised(exc)
    return dumps(out)


# ----------------------------------------------------------------------------------------------
# Original runner: git show into a temp folder, run in a child process
# ----------------------------------------------------------------------------------------------
class OriginalUnavailable(Exception):
    pass


def _git_blob_id(data):
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def _materialize_originals(tmp):
    if shutil.which("git") is None:
        raise OriginalUnavailable("git is not on PATH")
    for commit, rel, blob, folder in ORIGINAL_FILES:
        res = subprocess.run(["git", "-C", str(REPO_DIR), "show", f"{commit}:{rel}"], capture_output=True)
        if res.returncode != 0:
            raise OriginalUnavailable(f"{commit[:8]}:{rel} is not in this checkout")
        if _git_blob_id(res.stdout) != blob:
            raise AssertionError(f"{commit[:8]}:{rel} is not blob {blob}")
        dest = Path(tmp) / folder / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(res.stdout)


def run_original_child():
    """Outputs of the original runner functions on every case, from a child process that never imports
    lpbf_blind_stats. Raises OriginalUnavailable when git or a research commit is missing."""
    with tempfile.TemporaryDirectory(prefix="blind-stats-original-") as tmp:
        _materialize_originals(tmp)
        out = Path(tmp) / "vectors.json"
        res = subprocess.run([sys.executable, "-B", str(THIS_FILE), "--child", tmp, str(out)], cwd=str(PYTHON_DIR),
                             capture_output=True, text=True, timeout=900)
        if res.returncode != 0:
            raise AssertionError(f"original child failed:\n{res.stdout[-4000:]}\n{res.stderr[-4000:]}")
        return json.loads(out.read_text(encoding="utf-8"))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _child_main(tmp, out_path):
    tmp = Path(tmp)
    # The original runner puts its own python/ and python/tools/ in front of sys.path; the served modules it imports
    # (lpbf_thermal_solver, lpbf_public_datasets, eagar_tsai_solver, fabbro_keyhole) come from this checkout.
    melt = _load("run_lpbf_melt_depth", tmp / "e91d0fbd" / "python" / "tools" / "run_lpbf_melt_depth.py")
    p3 = _load("run_lpbf_p3_cavity_c4470b01", tmp / "c4470b01" / "python" / "tools" / "run_lpbf_p3_cavity.py")
    assert "lpbf_blind_stats" not in sys.modules
    side = _OriginalSide(melt, p3)
    texts = {"M": (tmp / "e91d0fbd" / SOURCE_FILE_OF["M"][1]).read_bytes().decode("utf-8").split("\n"),
             "P3": (tmp / "c4470b01" / SOURCE_FILE_OF["P3"][1]).read_bytes().decode("utf-8").split("\n")}
    source = {name: hashlib.sha256(("\n".join(texts[src][a - 1:b]) + "\n").encode("utf-8")).hexdigest()
              for name, (src, a, b) in PROV.items()}
    vectors = [[c["id"], run_case(c, side)] for c in build_cases()]
    assert "lpbf_blind_stats" not in sys.modules
    import numpy
    import scipy
    env = {"python": platform.python_version(), "numpy": numpy.__version__, "scipy": scipy.__version__}
    Path(out_path).write_text(json.dumps({"env": env, "source_sha256": source, "vectors": vectors}), encoding="utf-8")


def _write_golden():
    data = run_original_child()
    text = THIS_FILE.read_text(encoding="utf-8")
    begin, end = "# --- BEGIN GOLDEN (written by --write-golden; do not edit) ---\n", "# --- END GOLDEN ---\n"
    i, j = text.index(begin) + len(begin), text.index(end)
    body = ["GOLDEN_ENV = " + json.dumps(data["env"]), "GOLDEN_SOURCE_SHA256 = {"]
    body += [f'    "{k}": "{v}",' for k, v in data["source_sha256"].items()]
    body += ["}", 'GOLDEN_VECTORS = r"""']
    for cid, out in data["vectors"]:
        if '"""' in out or " " in cid:
            raise AssertionError(f"case {cid}: not embeddable")
        body.append(f"{cid} {out}")
    body.append('"""')
    THIS_FILE.write_text(text[:i] + "\n".join(body) + "\n" + text[j:], encoding="utf-8", newline="\n")
    print(f"{len(data['vectors'])} golden vectors written ({data['env']})")


# --- BEGIN GOLDEN (written by --write-golden; do not edit) ---
GOLDEN_ENV = {"python": "3.12.10", "numpy": "2.2.6", "scipy": "1.15.3"}
GOLDEN_SOURCE_SHA256 = {
    "INF": "3c99ec6b0ec0cb98d29aee2f817d451c2a68f3e31f397c667ca982392a518171",
    "MEDIAN_MAX": "c21c581ea4d6719b25b0d5e8fc55112cf2e53ba5b050226e894335cf06c03681",
    "P90_MAX": "c21c581ea4d6719b25b0d5e8fc55112cf2e53ba5b050226e894335cf06c03681",
    "BIAS_MAX": "c21c581ea4d6719b25b0d5e8fc55112cf2e53ba5b050226e894335cf06c03681",
    "MAXAPE_MAX": "c21c581ea4d6719b25b0d5e8fc55112cf2e53ba5b050226e894335cf06c03681",
    "N_MIN": "26c8246b9b48ce57002ffa5a86ade7cc0335a633b7318da93f94e6cb11886f2c",
    "SIDE_MIN": "f561edfd65024d5dfafb4f3eb02360cb54a8f002195a1ca983012de3fd961bdb",
    "U_MAX": "88a729ec6e93066e4128123aadf2fdf9ae5c1d505742b3be582fa92706b259f6",
    "LEVERAGE_LOW_CUT": "51e00b0e6deb9799b2a80c539d9461cf681e66bd87b9453d137d9f5f0aaa700e",
    "LEVERAGE_HIGH_CUT": "c7a81f8e5977819d063a1f6172772b1fe934c488f24983a6bf66313c51731882",
    "POWER_BAND": "eca820e56479f0414703ae4e161a918bb6c15538136adeaa5e799928f95cd54a",
    "BEAM_BAND_GRADE_B": "fb1941d66b99aa2129a637a69b39b6ca1bc082581ca8939c91016543ea617c2e",
    "U_M_REL_FLOOR": "17094e48d868c017385db046ecce386e1611f98fe58698a7189ff19057613394",
    "U_M_F_UM": "61046dcc72bce41ce367fb22eac3ea1358f3f313642d1ac4d53a1376f3b55f3b",
    "CV_POOL_MIN_CONDITIONS": "54b41fd3a1a08a87d47c1864838d839a5337e9d9851a8523bc07f09fe27927f4",
    "CV_POOL_MIN_DF": "54b41fd3a1a08a87d47c1864838d839a5337e9d9851a8523bc07f09fe27927f4",
    "BOOT_B": "10c507fb994d51b1f8de2e66bcf3cc0ca445eae4e0c06ae97bff15a759fe801e",
    "BOOT_SEED": "10c507fb994d51b1f8de2e66bcf3cc0ca445eae4e0c06ae97bff15a759fe801e",
    "FWHM_FACTOR": "8f730e336e55390ea5a4fb8eff8a74bdf2f6dc5448ea8b56225b976bff57e74e",
    "SERVED_NAME": "eef65ed1c1eb26a630c4fe30f4547cf6f7b19ea16c3825576d1518799616df38",
    "GRADE_RANK": "e238dc9881c225be63a7e72b764ccb5d293ae951a13f061dbf208c5e4c02ff86",
    "TIE_TOL": "d628c9574434e0e094dbe673ef7714259eb6a6d1e6158d9c356c9d47cfbaae24",
    "DP_SCALE": "a5c31de0e502808a171d5997211568cc8547b0dec4f98b558a145114d9c9bb51",
    "ENUMERATION_MAX_N": "5f302ee7945849421588f002ce18ffce3585aa4a715f024c968e998e853e5c8c",
    "_fr": "e559de815ce1bc093647992ad4ae7eac6709d28721a29025ff9864b61a37a449",
    "rank_quantile_exact": "1ca53808b65caac6218688b00375f664decf083932d0ca9e8b363ddbba7d447c",
    "percentile90": "3f8e3168ac76a530013da081e514f8bac1891290a5d6ba957edeca3c29679af5",
    "median_rank": "b88a650a216d16b55ddee882e5fe25fc8f38ccf4d60ebd6369301fff5d02924e",
    "_to_float": "7455d7df8142cba3ec8ede05e697f2d4a605d52d992d5fcb40bd263bc9eb4d09",
    "mean_signed_exact": "402847a9b213354accf21ce67ebfa06a845240083d8d929d6efb016863728088",
    "_le": "36e51e5be920223c799aa8bf8738264e68e1e67488f6dafd437445b12de0017b",
    "block_statistics": "514122f2e838c7f140a050038e4cffadac37c24f0d3a297c54845ec4a66011d4",
    "p75": "7ae90a7736e7b86338d7ecb9e35830735fcc0fd89a96c8d6ab9703e9174d681a",
    "bootstrap_intervals": "c4443d51b2fd45fe6ccc05f9f4fb4e121090032a96428e4947a9ddef965213c3",
    "index_bins": "824e5a49220575aa71552ea0b5cff01581ef3cc9e6fc5968e37695ccd3e76ec7",
    "power_grade": "9a24edeaecf96eb2fb4b7795ce0956e5f1671d258e1db3e9828198123cfa641c",
    "beam_grade": "f2887b909b1e22dd2e0baed764bc1c7d3051480f97d947e4425d72fdd97ca24f",
    "block_grade": "b3e2449be7d39699b68115c30a6c48bf4193ff6e8fcac0dcf2f802123e8e8e9b",
    "u_m_default_um": "a0a54d922917ee59b150c4f23d9e62955f8caeea0487a44fcfc42bd1961a7c04",
    "cv_pool": "d43b8033641ac6c6a9d1e68a2e2e93bb5b16521fcee80f59fbf0d847be7094eb",
    "resolution_qualifier": "5ca6b5fd915f03e88d1e1e156bfe7bc5c9ec6c2915463cd597ee0a537b58fd97",
    "beam_d_um": "0f5ebab1032a7d14e41c4463e3b0454b90428ead0b937f63273ae0615885219a",
    "TargetColumnRequested": "cf436942dd04b3007de8c3703d31066f882a26848b2a698fdfdb6e5023c0ca99",
    "_fold": "eba5abdf0459c6d5db335cd06bf214b193ab174d1dae2c6a35e0524cb4ee224a",
    "assert_no_target_loaded": "88a14d40451065b3f92a4545c439bdd321714999d6c397d553fe1f3903306e0d",
    "served_index": "da378f1d3a059d340714b240ed813d19af7f8412302b6c3a81ec30049d6279d8",
    "_mean": "6dd6df1cdf22b6fef5f45a0f0a10f86e19977b9f0d8e2d8f1d8d99de02f7acab",
    "reduce_conditions": "a77bcd616eb8f6e958bd7a68bd4c2dc9ced08b0308a32c8e05f6d67d5d62c272",
    "_track_value": "4755c7c438a70012186eb0039d182d5dc31968460ae58149701c9e7d56e54e3e",
    "arm_rels": "09662615715705ba8709deae0761c69a3a714c66e68efd9eedf35bea3012a5d7",
    "leverage_qualifier": "d1780caca1c795f43f1fa95dc9010514070c0a17c56f301258effba5694f0edb",
    "block_verdict": "b50636fdc5e058b19df6cf7e1e3cba997389d3a31604f38ea91596de415e74f9",
    "served_bins": "9c8bc3325267e14b42a8bc7e1dddfd39947d92493b104c5aadddb0d9379e3897",
    "fragile_flips": "a374518263183f544e2e85a0e8866f24acf7b2178d4ac1f38b6e2dcb8229d45b",
    "signflip_p_enumerate": "7d5efdd3c1267b4a0d7c0ebb78ab33ae3b5464cb1b33c8bcd2d340f917aa4de7",
    "_dp_p": "d10907c9879cd9ccbbca33817f19372b138641305cb94cfec7e84077c4b4ccaf",
    "signflip_p_dp": "dc27a4a4a8562b0c0926f88f15653179b757c53bc83b91c4615a5d6df6718c14",
    "signflip_p": "01645c76e616d2afc9d19f4379f2e67658fc68dbf8382c2bf3a80d38fe5c1b45",
    "paired_differences": "e8517b4914a959ad304f3b75d3e3af976da57fd884663660e3b709f858ccc499",
}
GOLDEN_VECTORS = r"""
constants {"INF":{"$f":"inf"},"MEDIAN_MAX":"0.20","P90_MAX":"0.35","BIAS_MAX":"0.10","MAXAPE_MAX":"0.50","N_MIN":12,"SIDE_MIN":4,"U_MAX":{"$f":"0.1"},"LEVERAGE_LOW_CUT":{"Ti64":{"$f":"15.0"},"AlSi10Mg":{"$f":"15.0"}},"LEVERAGE_HIGH_CUT":{"$f":"20.0"},"POWER_BAND":{"$f":"0.05"},"BEAM_BAND_GRADE_B":{"$f":"0.05"},"U_M_REL_FLOOR":{"$f":"0.03"},"U_M_F_UM":{"bare_plate":{"$f":"5.0"},"powder_layer_or_am":{"$f":"10.0"}},"CV_POOL_MIN_CONDITIONS":3,"CV_POOL_MIN_DF":3,"BOOT_B":2000,"BOOT_SEED":20261011,"FWHM_FACTOR":{"$f":"0.5887050112577373"},"SERVED_NAME":{"Ti64":"Ti-6Al-4V","AlSi10Mg":"AlSi10Mg"},"GRADE_RANK":{"A":3,"B":2,"C":1},"TIE_TOL":{"$f":"1e-12"},"DP_SCALE":1000000,"ENUMERATION_MAX_N":24}
fr-0 {"$q":"1/10"}
fr-1 {"$q":"7/20"}
fr-2 {"$q":"1/1"}
fr-3 {"$q":"1/4000000"}
fr-4 {"$q":"-1/5"}
fr-5 {"$q":"10000000000000000000000/1"}
to-float-0 {"$f":"0.3333333333333333"}
to-float-1 {"$f":"0.25"}
to-float-2 {"$f":"inf"}
to-float-3 {"$f":"-3.5"}
le-0 true
le-1 false
le-2 false
le-3 false
le-4 true
le-5 true
rank-quantile-00 {"$f":"nan"}
rank-quantile-01 {"$q":"3/10"}
rank-quantile-02 {"$q":"3/10"}
rank-quantile-03 {"$q":"1/5"}
rank-quantile-04 {"$q":"1/4"}
rank-quantile-05 {"$q":"37/100"}
rank-quantile-06 {"$q":"1/5"}
rank-quantile-07 {"$q":"1/4"}
rank-quantile-08 {"$f":"inf"}
rank-quantile-09 {"$f":"inf"}
rank-quantile-10 {"$f":"inf"}
rank-quantile-11 {"$f":"inf"}
rank-quantile-12 {"$q":"17/200"}
rank-quantile-13 {"$q":"159/1000"}
rank-quantile-14 {"$q":"51/400"}
rank-quantile-15 {"$q":"187/1000"}
rank-quantile-16 {"$f":"inf"}
rank-quantile-17 {"$q":"2/1"}
rank-quantile-18 {"$q":"-1/20"}
rank-quantile-19 {"$q":"1/20"}
percentile90-0 {"$f":"nan"}
percentile90-1 {"$f":"0.159"}
percentile90-2 {"$f":"0.187"}
percentile90-3 {"$f":"0.46"}
median_rank-0 {"$f":"nan"}
median_rank-1 {"$f":"0.085"}
median_rank-2 {"$f":"0.095"}
median_rank-3 {"$f":"0.3"}
p75-0 {"$f":"nan"}
p75-1 {"$f":"0.1275"}
p75-2 {"$f":"0.1525"}
p75-3 {"$f":"0.4"}
mean-signed-0 {"$q":"1/12"}
mean-signed-1 {"$q":"1/10"}
mean-signed-2 {"$f":"nan"}
mean-signed-3 {"$f":"nan"}
mean-signed-4 {"$q":"-1/10"}
mean-signed-5 {"$q":"7/240"}
mean-signed-6 {"$q":"1/10"}
block-statistics-00 {"n":12,"median":{"$f":"0.085"},"p75":{"$f":"0.1275"},"p90":{"$f":"0.159"},"mean_signed":{"$f":"0.029166666666666667"},"max_ape":{"$f":"0.19"},"worst_index":8,"n_failed":0,"thresholds_met":{"median":true,"p90":true,"mean_signed":true,"max_ape":true},"all_thresholds_met":true}
block-statistics-01 {"n":12,"median":{"$f":"0.095"},"p75":{"$f":"0.1525"},"p90":{"$f":"0.187"},"mean_signed":{"$f":"0.023636363636363636"},"max_ape":{"$f":"inf"},"worst_index":11,"n_failed":1,"thresholds_met":{"median":true,"p90":true,"mean_signed":true,"max_ape":false},"all_thresholds_met":false}
block-statistics-02 {"n":0,"median":{"$f":"nan"},"p75":{"$f":"nan"},"p90":{"$f":"nan"},"mean_signed":{"$f":"nan"},"max_ape":{"$f":"nan"},"worst_index":null,"n_failed":0,"thresholds_met":{"median":false,"p90":false,"mean_signed":false,"max_ape":false},"all_thresholds_met":false}
block-statistics-03 {"n":3,"median":{"$f":"inf"},"p75":{"$f":"inf"},"p90":{"$f":"inf"},"mean_signed":{"$f":"nan"},"max_ape":{"$f":"inf"},"worst_index":0,"n_failed":3,"thresholds_met":{"median":false,"p90":false,"mean_signed":false,"max_ape":false},"all_thresholds_met":false}
block-statistics-04 {"n":12,"median":{"$f":"0.3"},"p75":{"$f":"0.3"},"p90":{"$f":"0.3"},"mean_signed":{"$f":"0.3"},"max_ape":{"$f":"0.3"},"worst_index":0,"n_failed":0,"thresholds_met":{"median":false,"p90":true,"mean_signed":false,"max_ape":true},"all_thresholds_met":false}
block-statistics-05 {"n":12,"median":{"$f":"0.25"},"p75":{"$f":"0.25"},"p90":{"$f":"0.25"},"mean_signed":{"$f":"0.25"},"max_ape":{"$f":"0.25"},"worst_index":0,"n_failed":0,"thresholds_met":{"median":false,"p90":true,"mean_signed":false,"max_ape":true},"all_thresholds_met":false}
block-statistics-06 {"n":12,"median":{"$f":"0.2"},"p75":{"$f":"0.2125"},"p90":{"$f":"0.22"},"mean_signed":{"$f":"0.023333333333333334"},"max_ape":{"$f":"0.25"},"worst_index":11,"n_failed":0,"thresholds_met":{"median":true,"p90":true,"mean_signed":true,"max_ape":true},"all_thresholds_met":true}
block-statistics-07 {"n":12,"median":{"$f":"0.20000000000000004"},"p75":{"$f":"0.2125"},"p90":{"$f":"0.22"},"mean_signed":{"$f":"0.023333333333333334"},"max_ape":{"$f":"0.25"},"worst_index":11,"n_failed":0,"thresholds_met":{"median":false,"p90":true,"mean_signed":true,"max_ape":true},"all_thresholds_met":false}
block-statistics-08 {"n":12,"median":{"$f":"0.035"},"p75":{"$f":"0.125"},"p90":{"$f":"0.35"},"mean_signed":{"$f":"0.0375"},"max_ape":{"$f":"0.4"},"worst_index":11,"n_failed":0,"thresholds_met":{"median":true,"p90":true,"mean_signed":true,"max_ape":true},"all_thresholds_met":true}
block-statistics-09 {"n":12,"median":{"$f":"0.035"},"p75":{"$f":"0.125"},"p90":{"$f":"0.35000000000000003"},"mean_signed":{"$f":"0.0375"},"max_ape":{"$f":"0.4"},"worst_index":11,"n_failed":0,"thresholds_met":{"median":true,"p90":false,"mean_signed":true,"max_ape":true},"all_thresholds_met":false}
block-statistics-10 {"n":12,"median":{"$f":"0.1"},"p75":{"$f":"0.1"},"p90":{"$f":"0.1"},"mean_signed":{"$f":"0.1"},"max_ape":{"$f":"0.1"},"worst_index":0,"n_failed":0,"thresholds_met":{"median":true,"p90":true,"mean_signed":true,"max_ape":true},"all_thresholds_met":true}
block-statistics-11 {"n":12,"median":{"$f":"0.10000000000000002"},"p75":{"$f":"0.10000000000000002"},"p90":{"$f":"0.10000000000000002"},"mean_signed":{"$f":"0.10000000000000002"},"max_ape":{"$f":"0.10000000000000002"},"worst_index":0,"n_failed":0,"thresholds_met":{"median":true,"p90":true,"mean_signed":false,"max_ape":true},"all_thresholds_met":false}
block-statistics-12 {"n":12,"median":{"$f":"0.1"},"p75":{"$f":"0.1"},"p90":{"$f":"0.1"},"mean_signed":{"$f":"-0.1"},"max_ape":{"$f":"0.1"},"worst_index":0,"n_failed":0,"thresholds_met":{"median":true,"p90":true,"mean_signed":true,"max_ape":true},"all_thresholds_met":true}
block-statistics-13 {"n":12,"median":{"$f":"0.10000000000000002"},"p75":{"$f":"0.10000000000000002"},"p90":{"$f":"0.10000000000000002"},"mean_signed":{"$f":"-0.10000000000000002"},"max_ape":{"$f":"0.10000000000000002"},"worst_index":0,"n_failed":0,"thresholds_met":{"median":true,"p90":true,"mean_signed":false,"max_ape":true},"all_thresholds_met":false}
block-statistics-14 {"n":12,"median":{"$f":"0.035"},"p75":{"$f":"0.05"},"p90":{"$f":"0.05"},"mean_signed":{"$f":"0.0375"},"max_ape":{"$f":"0.5"},"worst_index":0,"n_failed":0,"thresholds_met":{"median":true,"p90":true,"mean_signed":true,"max_ape":true},"all_thresholds_met":true}
block-statistics-15 {"n":12,"median":{"$f":"0.035"},"p75":{"$f":"0.05"},"p90":{"$f":"0.05"},"mean_signed":{"$f":"0.037500000000000006"},"max_ape":{"$f":"0.5000000000000001"},"worst_index":0,"n_failed":0,"thresholds_met":{"median":true,"p90":true,"mean_signed":true,"max_ape":false},"all_thresholds_met":false}
bootstrap-twelve {"median":{"lo":{"$f":"0.045"},"hi":{"$f":"0.135"},"marginal":false},"p90":{"lo":{"$f":"0.108"},"hi":{"$f":"0.19"},"marginal":false},"mean_signed":{"lo":{"$f":"-0.02666666666666667"},"hi":{"$f":"0.08416666666666667"},"marginal":false},"max_ape":{"lo":{"$f":"0.12"},"hi":{"$f":"0.19"},"marginal":false}}
bootstrap-fourteen-inf {"median":{"lo":{"$f":"0.06"},"hi":{"$f":"0.155"},"marginal":false},"p90":{"lo":{"$f":"0.141"},"hi":{"$f":"inf"},"marginal":true},"mean_signed":{"lo":{"$f":"-0.05416666666666667"},"hi":{"$f":"0.075"},"marginal":false},"max_ape":{"lo":{"$f":"0.16"},"hi":{"$f":"inf"},"marginal":true}}
bootstrap-empty {}
bootstrap-all-inf {"median":{"lo":{"$f":"inf"},"hi":{"$f":"inf"},"marginal":false},"p90":{"lo":{"$f":"inf"},"hi":{"$f":"inf"},"marginal":false},"max_ape":{"lo":{"$f":"inf"},"hi":{"$f":"inf"},"marginal":false}}
bootstrap-custom {"median":{"lo":{"$f":"0.04"},"hi":{"$f":"0.14"},"marginal":false},"p90":{"lo":{"$f":"0.108"},"hi":{"$f":"0.19"},"marginal":false},"mean_signed":{"lo":{"$f":"-0.028333333333333335"},"hi":{"$f":"0.08750000000000001"},"marginal":false},"max_ape":{"lo":{"$f":"0.12"},"hi":{"$f":"0.19"},"marginal":false}}
bootstrap-marginal {"median":{"lo":{"$f":"0.02"},"hi":{"$f":"0.215"},"marginal":true},"p90":{"lo":{"$f":"0.209"},"hi":{"$f":"0.25"},"marginal":false},"mean_signed":{"lo":{"$f":"-0.06916666666666667"},"hi":{"$f":"0.115"},"marginal":true},"max_ape":{"lo":{"$f":"0.21"},"hi":{"$f":"0.25"},"marginal":false}}
index-bins-0 "below"
index-bins-1 "between"
index-bins-2 "between"
index-bins-3 "at_or_above"
index-bins-4 "at_or_above"
index-bins-5 "at_or_above"
index-bins-6 "between"
power-grade-0 "C"
power-grade-1 "C"
power-grade-2 "B"
power-grade-3 "C"
power-grade-4 "A"
power-grade-5 "B"
power-grade-6 "B"
power-grade-7 "C"
beam-grade-0 "C"
beam-grade-1 "C"
beam-grade-2 "C"
beam-grade-3 "C"
beam-grade-4 "B"
beam-grade-5 "A"
beam-grade-6 "B"
beam-grade-7 "C"
block-grade-AA "A"
block-grade-AB "B"
block-grade-AC "C"
block-grade-BA "B"
block-grade-BB "B"
block-grade-BC "C"
block-grade-CA "C"
block-grade-CB "C"
block-grade-CC "C"
u-m-default-0 {"$f":"5.0"}
u-m-default-1 {"$f":"9.0"}
u-m-default-2 {"$f":"10.0"}
u-m-default-3 {"$f":"10.0"}
u-m-default-4 {"$f":"15.0"}
u-m-default-5 {"$f":"5.0"}
cv-pool-0 {"$t":[null,0,0]}
cv-pool-1 {"$t":[null,1,1]}
cv-pool-2 {"$t":[{"$f":"0.02649486886407853"},3,3]}
cv-pool-3 {"$t":[null,2,2]}
cv-pool-4 {"$t":[null,2,4]}
cv-pool-5 {"$t":[{"$f":"0.02385011051599832"},3,3]}
cv-pool-6 {"$t":[{"$f":"0.0"},3,3]}
cv-pool-7 {"$t":[{"$f":"0.01178867162912343"},3,5]}
resolution-all-replicated {"cv_pool":{"$f":"0.007322929136420767"},"n_replicated_conditions":3,"pooled_df":4,"needs_pool":false,"u_m_assumed":true,"track_counts":[2,2,3],"status":"met","median_U":{"$f":"0.0608359067518056"},"median_U_2x_descriptive":{"$f":"0.12042012934021615"},"median_U_t_descriptive":{"$f":"0.3864967432574668"},"per_condition":[{"n_t":2,"D_obs_um":{"$f":"150.5"},"u_m_um":{"$f":"5.0"},"U":{"$f":"0.06677658220013881"},"U_2x":{"$f":"0.13305637471429094"},"U_t":{"$f":"0.4242384625170754"}},{"n_t":2,"D_obs_um":{"$f":"199.0"},"u_m_um":{"$f":"5.97"},"U":{"$f":"0.0608359067518056"},"U_2x":{"$f":"0.12042012934021615"},"U_t":{"$f":"0.3864967432574668"}},{"n_t":3,"D_obs_um":{"$f":"181.33333333333334"},"u_m_um":{"$f":"5.44"},"U":{"$f":"0.0607833451851995"},"U_2x":{"$f":"0.12039358393163281"},"U_t":{"$f":"0.13076481304058074"}}],"reason":null}
resolution-released-u-m {"cv_pool":{"$f":"0.007322929136420767"},"n_replicated_conditions":3,"pooled_df":4,"needs_pool":false,"u_m_assumed":false,"track_counts":[2,2,3],"status":"met","median_U":{"$f":"0.045177226939134216"},"median_U_2x_descriptive":{"$f":"0.08876982696801201"},"median_U_t_descriptive":{"$f":"0.26326142828659765"},"per_condition":[{"n_t":2,"D_obs_um":{"$f":"150.5"},"u_m_um":{"$f":"4.0"},"U":{"$f":"0.053569818925571756"},"U_2x":{"$f":"0.10651973117529169"},"U_t":{"$f":"0.34033454348095477"}},{"n_t":2,"D_obs_um":{"$f":"199.0"},"u_m_um":{"$f":"4.0"},"U":{"$f":"0.04143824749364483"},"U_2x":{"$f":"0.081027716063302"},"U_t":{"$f":"0.26326142828659765"}},{"n_t":3,"D_obs_um":{"$f":"181.33333333333334"},"u_m_um":{"$f":"4.0"},"U":{"$f":"0.045177226939134216"},"U_2x":{"$f":"0.08876982696801201"},"U_t":{"$f":"0.09719095940488395"}}],"reason":null}
resolution-singles-with-pool {"cv_pool":{"$f":"0.007322929136420767"},"n_replicated_conditions":3,"pooled_df":4,"needs_pool":true,"u_m_assumed":true,"track_counts":[2,2,3,1],"status":"met","median_U":{"$f":"0.06129877737943354"},"median_U_2x_descriptive":{"$f":"0.12065529021470373"},"median_U_t_descriptive":{"$f":"0.3864967432574668"},"per_condition":[{"n_t":2,"D_obs_um":{"$f":"150.5"},"u_m_um":{"$f":"5.0"},"U":{"$f":"0.06677658220013881"},"U_2x":{"$f":"0.13305637471429094"},"U_t":{"$f":"0.4242384625170754"}},{"n_t":2,"D_obs_um":{"$f":"199.0"},"u_m_um":{"$f":"5.97"},"U":{"$f":"0.0608359067518056"},"U_2x":{"$f":"0.12042012934021615"},"U_t":{"$f":"0.3864967432574668"}},{"n_t":3,"D_obs_um":{"$f":"181.33333333333334"},"u_m_um":{"$f":"5.44"},"U":{"$f":"0.0607833451851995"},"U_2x":{"$f":"0.12039358393163281"},"U_t":{"$f":"0.13076481304058074"}},{"n_t":1,"D_obs_um":{"$f":"170.0"},"u_m_um":{"$f":"5.1"},"U":{"$f":"0.06176164800706147"},"U_2x":{"$f":"0.12089045108919132"},"U_t":null}],"reason":null}
resolution-singles-without-pool {"cv_pool":null,"n_replicated_conditions":1,"pooled_df":1,"needs_pool":true,"u_m_assumed":false,"track_counts":[1,2,1],"status":"not_evaluable","median_U":null,"median_U_2x_descriptive":null,"median_U_t_descriptive":null,"reason":"single track conditions need cv_pool, which needs at least 3 conditions with 2 or more tracks and pooled degrees of freedom of at least 3; got 1 and 1"}
resolution-not-met {"cv_pool":{"$f":"0.24246778623573054"},"n_replicated_conditions":3,"pooled_df":3,"needs_pool":false,"u_m_assumed":true,"track_counts":[2,2,2],"status":"not_met","median_U":{"$f":"0.3435921354681384"},"median_U_2x_descriptive":{"$f":"0.37267799624996495"},"median_U_t_descriptive":{"$f":"2.182876009543039"},"per_condition":[{"n_t":2,"D_obs_um":{"$f":"120.0"},"u_m_um":{"$f":"5.0"},"U":{"$f":"0.3435921354681384"},"U_2x":{"$f":"0.37267799624996495"},"U_t":{"$f":"2.182876009543039"}},{"n_t":2,"D_obs_um":{"$f":"175.0"},"u_m_um":{"$f":"5.25"},"U":{"$f":"0.291946318800605"},"U_2x":{"$f":"0.3098913568675714"},"U_t":{"$f":"1.8547648493640807"}},{"n_t":2,"D_obs_um":{"$f":"150.0"},"u_m_um":{"$f":"5.0"},"U":{"$f":"0.40551750201988135"},"U_2x":{"$f":"0.4216370213557839"},"U_t":{"$f":"2.576294202435564"}}],"reason":"median U_c 0.3436 above 0.1"}
resolution-u-m-zero {"$raises":["ValueError","u_m must be positive (never 0)"]}
resolution-powder-layer {"cv_pool":{"$f":"0.007322929136420767"},"n_replicated_conditions":3,"pooled_df":4,"needs_pool":false,"u_m_assumed":true,"track_counts":[2,2,3],"status":"not_met","median_U":{"$f":"0.11072220842923232"},"median_U_2x_descriptive":{"$f":"0.2208025919278941"},"median_U_t_descriptive":{"$f":"0.641687322701707"},"per_condition":[{"n_t":2,"D_obs_um":{"$f":"150.5"},"u_m_um":{"$f":"10.0"},"U":{"$f":"0.13305637471429094"},"U_2x":{"$f":"0.2658637744018944"},"U_t":{"$f":"0.8453207693036037"}},{"n_t":2,"D_obs_um":{"$f":"199.0"},"u_m_um":{"$f":"10.0"},"U":{"$f":"0.10100377508664211"},"U_2x":{"$f":"0.2012561245678471"},"U_t":{"$f":"0.641687322701707"}},{"n_t":3,"D_obs_um":{"$f":"181.33333333333334"},"u_m_um":{"$f":"10.0"},"U":{"$f":"0.11072220842923232"},"U_2x":{"$f":"0.2208025919278941"},"U_t":{"$f":"0.23819960616801078"}}],"reason":"median U_c 0.1107 above 0.1"}
resolution-am-mixed-release {"cv_pool":{"$f":"0.007322929136420767"},"n_replicated_conditions":3,"pooled_df":4,"needs_pool":false,"u_m_assumed":true,"track_counts":[2,2,3],"status":"not_met","median_U":{"$f":"0.11072220842923232"},"median_U_2x_descriptive":{"$f":"0.2208025919278941"},"median_U_t_descriptive":{"$f":"0.388386060668678"},"per_condition":[{"n_t":2,"D_obs_um":{"$f":"150.5"},"u_m_um":{"$f":"10.0"},"U":{"$f":"0.13305637471429094"},"U_2x":{"$f":"0.2658637744018944"},"U_t":{"$f":"0.8453207693036037"}},{"n_t":2,"D_obs_um":{"$f":"199.0"},"u_m_um":{"$f":"6.0"},"U":{"$f":"0.06113329176179115"},"U_2x":{"$f":"0.12102105104313865"},"U_t":{"$f":"0.388386060668678"}},{"n_t":3,"D_obs_um":{"$f":"181.33333333333334"},"u_m_um":{"$f":"10.0"},"U":{"$f":"0.11072220842923232"},"U_2x":{"$f":"0.2208025919278941"},"U_t":{"$f":"0.23819960616801078"}}],"reason":"median U_c 0.1107 above 0.1"}
resolution-u-m-text {"cv_pool":{"$f":"0.007322929136420767"},"n_replicated_conditions":3,"pooled_df":4,"needs_pool":false,"u_m_assumed":false,"track_counts":[2,2,3],"status":"met","median_U":{"$f":"0.055998331660764025"},"median_U_2x_descriptive":{"$f":"0.11072220842923232"},"median_U_t_descriptive":{"$f":"0.32557379846619255"},"per_condition":[{"n_t":2,"D_obs_um":{"$f":"150.5"},"u_m_um":{"$f":"5.0"},"U":{"$f":"0.06677658220013881"},"U_2x":{"$f":"0.13305637471429094"},"U_t":{"$f":"0.4242384625170754"}},{"n_t":2,"D_obs_um":{"$f":"199.0"},"u_m_um":{"$f":"5.0"},"U":{"$f":"0.05124642727228929"},"U_2x":{"$f":"0.10100377508664211"},"U_t":{"$f":"0.32557379846619255"}},{"n_t":3,"D_obs_um":{"$f":"181.33333333333334"},"u_m_um":{"$f":"5.0"},"U":{"$f":"0.055998331660764025"},"U_2x":{"$f":"0.11072220842923232"},"U_t":{"$f":"0.12047068728930811"}}],"reason":null}
beam-d-0 {"$f":"80.0"}
beam-d-1 {"$f":"80.0"}
beam-d-2 {"$f":"80.0"}
beam-d-3 {"$f":"79.99999847016933"}
beam-d-4 {"$raises":["ValueError","unresolved beam definition 'fwhm'"]}
beam-d-5 {"$raises":["ValueError","unresolved beam definition 'radius'"]}
beam-d-6 {"$f":"80.0"}
no-target-loaded-0 true
no-target-loaded-1 {"$raises":["TargetColumnRequested","target column(s) ['depth (UM)'] were loaded in the prediction phase"]}
no-target-loaded-2 {"$raises":["TargetColumnRequested","target column(s) ['SYNTHETIC WIDTH', 'Depth (um)'] were loaded in the prediction phase"]}
no-target-loaded-3 true
fold-0 "depth (um)"
fold-1 7
mean-0 {"$f":"2.3333333333333335"}
mean-1 {"$f":"0.10000000000000002"}
mean-2 {"$f":"1.5"}
track-value-0 {"$f":"1.5"}
track-value-1 {"status":"failed","reason":"synthetic solver failure"}
track-value-2 {"status":"unavailable","reason":"synthetic arm unavailable"}
track-value-3 {"$f":"3.0"}
served-index-0 {"normalized_enthalpy_called_with":["Ti-6Al-4V",{"$f":"200.0"},{"$f":"1000.0"},{"$f":"80.0"},{"$f":"20.0"}]}
served-index-1 {"normalized_enthalpy_called_with":["AlSi10Mg",{"$f":"200.0"},{"$f":"1000.0"},{"$f":"80.0"},{"$f":"80.0"}]}
served-index-2 {"$raises":["KeyError","'316L'"]}
served-index-3 {"normalized_enthalpy_called_with":["Ti-6Al-4V",{"$f":"200.0"},{"$f":"1000.0"},{"$f":"80.0"},{"$f":"26.850000000000023"}]}
reduce-sections [{"condition":"c1","beam_setting":"A","P_W":{"$f":"200.0"},"v_mm_s":{"$f":"1000.0"},"d_um":{"$f":"80.0"},"index":{"$f":"8.0"},"n_tracks":2,"track_depths":[{"$f":"100.0"},{"$f":"104.0"}],"D_obs_um":{"$f":"102.0"},"u_m_um":null,"pred":{"S1":{"$f":"110.0"},"C0":{"$f":"90.0"}},"ledger":{},"convergence":null},{"condition":"c2","beam_setting":"A","P_W":{"$f":"200.0"},"v_mm_s":{"$f":"1000.0"},"d_um":{"$f":"80.0"},"index":{"$f":"22.25"},"n_tracks":2,"track_depths":[{"$f":"200.0"},{"$f":"205.0"}],"D_obs_um":{"$f":"202.5"},"u_m_um":null,"pred":{"S1":{"$f":"211.0"},"C0":{"$f":"180.5"}},"ledger":{},"convergence":null}]
reduce-failed-unavailable [{"condition":"c1","beam_setting":"A","P_W":{"$f":"200.0"},"v_mm_s":{"$f":"1000.0"},"d_um":{"$f":"80.0"},"index":{"$f":"10.0"},"n_tracks":3,"track_depths":[{"$f":"100.0"},{"$f":"102.0"},{"$f":"98.0"}],"D_obs_um":{"$f":"100.0"},"u_m_um":null,"pred":{"S1":{"status":"failed","reason":"synthetic solver failure"},"C0":{"status":"failed","reason":"synthetic arm unavailable"}},"ledger":{},"convergence":null}]
reduce-repeated-without-track {"$raises":["ValueError","condition 'c1': repeated rows without a track key and without an owner-text locator that each row is a separate track"]}
reduce-repeated-rows-are-tracks [{"condition":"c1","beam_setting":"A","P_W":{"$f":"200.0"},"v_mm_s":{"$f":"1000.0"},"d_um":{"$f":"80.0"},"index":{"$f":"10.0"},"n_tracks":2,"track_depths":[{"$f":"100.0"},{"$f":"104.0"}],"D_obs_um":{"$f":"102.0"},"u_m_um":null,"pred":{"S1":{"$f":"110.0"},"C0":{"$f":"90.0"}},"ledger":{},"convergence":null},{"condition":"c2","beam_setting":"A","P_W":{"$f":"200.0"},"v_mm_s":{"$f":"1000.0"},"d_um":{"$f":"80.0"},"index":{"$f":"10.0"},"n_tracks":1,"track_depths":[{"$f":"90.0"}],"D_obs_um":{"$f":"90.0"},"u_m_um":null,"pred":{"S1":{"$f":"110.0"},"C0":{"$f":"90.0"}},"ledger":{},"convergence":null}]
reduce-section-without-track [{"condition":"c1","beam_setting":"A","P_W":{"$f":"200.0"},"v_mm_s":{"$f":"1000.0"},"d_um":{"$f":"80.0"},"index":{"$f":"10.0"},"n_tracks":2,"track_depths":[{"$f":"100.0"},{"$f":"104.0"}],"D_obs_um":{"$f":"102.0"},"u_m_um":null,"pred":{"S1":{"$f":"110.0"},"C0":{"$f":"90.0"}},"ledger":{},"convergence":null}]
reduce-missing-depth {"$raises":["ValueError","row 4: depth is missing or not positive"]}
reduce-zero-depth {"$raises":["ValueError","row 3: depth is missing or not positive"]}
reduce-negative-depth {"$raises":["ValueError","row 3: depth is missing or not positive"]}
reduce-none-entry {"$raises":["ValueError","row 5: depth is missing or not positive"]}
reduce-nan-depth {"$raises":["ValueError","row 6: depth is missing or not positive"]}
reduce-u-m-differs {"$raises":["ValueError","condition 'c1': a released u_m differs within the condition"]}
reduce-u-m-released [{"condition":"c1","beam_setting":"A","P_W":{"$f":"200.0"},"v_mm_s":{"$f":"1000.0"},"d_um":{"$f":"80.0"},"index":{"$f":"10.0"},"n_tracks":2,"track_depths":[{"$f":"100.0"},{"$f":"101.0"}],"D_obs_um":{"$f":"100.5"},"u_m_um":{"$f":"4.0"},"pred":{"S1":{"$f":"110.0"},"C0":{"$f":"90.0"}},"ledger":{},"convergence":null}]
reduce-ledger-convergence [{"condition":"c1","beam_setting":"A","P_W":{"$f":"200.0"},"v_mm_s":{"$f":"1000.0"},"d_um":{"$f":"80.0"},"index":{"$f":"10.0"},"n_tracks":2,"track_depths":[{"$f":"100.0"},{"$f":"99.0"}],"D_obs_um":{"$f":"99.5"},"u_m_um":null,"pred":{"S1":{"$f":"110.0"},"C0":{"$f":"90.0"}},"ledger":{"S1":{"synthetic":{"$f":"1.0"}}},"convergence":{"rel_diff":{"$f":"0.001"},"flag":false}}]
reduce-empty []
arm-rels-0 {"$t":[[{"$f":"0.1"},{"$f":"inf"},{"$f":"-0.25"}],["c1","c2","c4"],["c3"]]}
arm-rels-1 {"$raises":["KeyError","'C0'"]}
arm-rels-2 {"$t":[[],[],[]]}
arm-rels-3 {"$t":[[{"$f":"-0.25"}],["c4"],[]]}
leverage-0 {"cut":{"$f":"15.0"},"n_below":4,"n_at_or_above_20":4,"ok":true}
leverage-1 {"cut":{"$f":"15.0"},"n_below":3,"n_at_or_above_20":4,"ok":false}
leverage-2 {"cut":{"$f":"15.0"},"n_below":4,"n_at_or_above_20":4,"ok":true}
leverage-3 {"cut":{"$f":"15.0"},"n_below":4,"n_at_or_above_20":3,"ok":false}
leverage-4 {"$raises":["KeyError","'IN625'"]}
verdict-exposed {"stats":{"n":12,"median":{"$f":"0.085"},"p75":{"$f":"0.1275"},"p90":{"$f":"0.159"},"mean_signed":{"$f":"0.029166666666666667"},"max_ape":{"$f":"0.19"},"worst_index":8,"n_failed":0,"thresholds_met":{"median":true,"p90":true,"mean_signed":true,"max_ape":true},"all_thresholds_met":true},"qualifiers":{"leverage_ok":true,"resolution":"met"},"issues":["synthetic issue"],"status":"EXPOSED_DESCRIPTIVE","reason":"a target was read before the prediction hash (section 5 item 6)"}
verdict-not-scored {"stats":{"n":12,"median":{"$f":"0.085"},"p75":{"$f":"0.1275"},"p90":{"$f":"0.159"},"mean_signed":{"$f":"0.029166666666666667"},"max_ape":{"$f":"0.19"},"worst_index":8,"n_failed":0,"thresholds_met":{"median":true,"p90":true,"mean_signed":true,"max_ape":true},"all_thresholds_met":true},"qualifiers":{"leverage_ok":true,"resolution":"met"},"issues":["synthetic issue"],"status":"DESCRIPTIVE_NOT_SCORED","reason":"powder layer block without a same-setup absorptance or a declared P5 bias (Amendment 6 item 6)"}
verdict-n11 {"stats":{"n":11,"median":{"$f":"0.08"},"p75":{"$f":"0.135"},"p90":{"$f":"0.16"},"mean_signed":{"$f":"0.023636363636363636"},"max_ape":{"$f":"0.19"},"worst_index":8,"n_failed":0,"thresholds_met":{"median":true,"p90":true,"mean_signed":true,"max_ape":true},"all_thresholds_met":true},"qualifiers":{"leverage_ok":true,"resolution":"met"},"issues":[],"status":"INCONCLUSIVE","reason":"n = 11 < 12"}
verdict-issues {"stats":{"n":12,"median":{"$f":"0.085"},"p75":{"$f":"0.1275"},"p90":{"$f":"0.159"},"mean_signed":{"$f":"0.029166666666666667"},"max_ape":{"$f":"0.19"},"worst_index":8,"n_failed":0,"thresholds_met":{"median":true,"p90":true,"mean_signed":true,"max_ape":true},"all_thresholds_met":true},"qualifiers":{"leverage_ok":true,"resolution":"met"},"issues":["synthetic issue A","synthetic issue B"],"status":"INCONCLUSIVE","reason":"synthetic issue A; synthetic issue B"}
verdict-n11-issues {"stats":{"n":11,"median":{"$f":"0.08"},"p75":{"$f":"0.135"},"p90":{"$f":"0.16"},"mean_signed":{"$f":"0.023636363636363636"},"max_ape":{"$f":"0.19"},"worst_index":8,"n_failed":0,"thresholds_met":{"median":true,"p90":true,"mean_signed":true,"max_ape":true},"all_thresholds_met":true},"qualifiers":{"leverage_ok":true,"resolution":"met"},"issues":["synthetic issue"],"status":"INCONCLUSIVE","reason":"n = 11 < 12; synthetic issue"}
verdict-n11-fail {"stats":{"n":11,"median":{"$f":"0.25"},"p75":{"$f":"0.25"},"p90":{"$f":"0.25"},"mean_signed":{"$f":"0.25"},"max_ape":{"$f":"0.25"},"worst_index":0,"n_failed":0,"thresholds_met":{"median":false,"p90":true,"mean_signed":false,"max_ape":true},"all_thresholds_met":false},"qualifiers":{"leverage_ok":true,"resolution":"met"},"issues":[],"status":"INCONCLUSIVE","reason":"n = 11 < 12"}
verdict-fail-median {"stats":{"n":12,"median":{"$f":"0.25"},"p75":{"$f":"0.25"},"p90":{"$f":"0.25"},"mean_signed":{"$f":"0.25"},"max_ape":{"$f":"0.25"},"worst_index":0,"n_failed":0,"thresholds_met":{"median":false,"p90":true,"mean_signed":false,"max_ape":true},"all_thresholds_met":false},"qualifiers":{"leverage_ok":true,"resolution":"met"},"issues":[],"status":"FAIL","reason":"threshold failure: median, mean_signed"}
verdict-fail-several {"stats":{"n":12,"median":{"$f":"0.6"},"p75":{"$f":"0.6"},"p90":{"$f":"0.6"},"mean_signed":{"$f":"0.0"},"max_ape":{"$f":"0.6"},"worst_index":0,"n_failed":0,"thresholds_met":{"median":false,"p90":false,"mean_signed":true,"max_ape":false},"all_thresholds_met":false},"qualifiers":{"leverage_ok":true,"resolution":"met"},"issues":[],"status":"FAIL","reason":"threshold failure: median, p90, max_ape"}
verdict-fail-inf {"stats":{"n":12,"median":{"$f":"0.095"},"p75":{"$f":"0.1525"},"p90":{"$f":"0.187"},"mean_signed":{"$f":"0.023636363636363636"},"max_ape":{"$f":"inf"},"worst_index":11,"n_failed":1,"thresholds_met":{"median":true,"p90":true,"mean_signed":true,"max_ape":false},"all_thresholds_met":false},"qualifiers":{"leverage_ok":true,"resolution":"met"},"issues":[],"status":"FAIL","reason":"threshold failure: max_ape"}
verdict-leverage-not-met {"stats":{"n":12,"median":{"$f":"0.085"},"p75":{"$f":"0.1275"},"p90":{"$f":"0.159"},"mean_signed":{"$f":"0.029166666666666667"},"max_ape":{"$f":"0.19"},"worst_index":8,"n_failed":0,"thresholds_met":{"median":true,"p90":true,"mean_signed":true,"max_ape":true},"all_thresholds_met":true},"qualifiers":{"leverage_ok":false,"resolution":"met"},"issues":[],"status":"INCONCLUSIVE","reason":"all four thresholds met; qualifier not met: leverage"}
verdict-resolution-not-met {"stats":{"n":12,"median":{"$f":"0.085"},"p75":{"$f":"0.1275"},"p90":{"$f":"0.159"},"mean_signed":{"$f":"0.029166666666666667"},"max_ape":{"$f":"0.19"},"worst_index":8,"n_failed":0,"thresholds_met":{"median":true,"p90":true,"mean_signed":true,"max_ape":true},"all_thresholds_met":true},"qualifiers":{"leverage_ok":true,"resolution":"not_met"},"issues":[],"status":"INCONCLUSIVE","reason":"all four thresholds met; qualifier not met: resolution not met"}
verdict-resolution-not-evaluable-and-leverage {"stats":{"n":12,"median":{"$f":"0.085"},"p75":{"$f":"0.1275"},"p90":{"$f":"0.159"},"mean_signed":{"$f":"0.029166666666666667"},"max_ape":{"$f":"0.19"},"worst_index":8,"n_failed":0,"thresholds_met":{"median":true,"p90":true,"mean_signed":true,"max_ape":true},"all_thresholds_met":true},"qualifiers":{"leverage_ok":false,"resolution":"not_evaluable"},"issues":[],"status":"INCONCLUSIVE","reason":"all four thresholds met; qualifier not met: leverage, resolution not evaluable"}
verdict-pass {"stats":{"n":12,"median":{"$f":"0.085"},"p75":{"$f":"0.1275"},"p90":{"$f":"0.159"},"mean_signed":{"$f":"0.029166666666666667"},"max_ape":{"$f":"0.19"},"worst_index":8,"n_failed":0,"thresholds_met":{"median":true,"p90":true,"mean_signed":true,"max_ape":true},"all_thresholds_met":true},"qualifiers":{"leverage_ok":true,"resolution":"met"},"issues":[],"status":"PASS","reason":"all four thresholds met, leverage and resolution met"}
verdict-in625-like-threshold-fail {"stats":{"n":12,"median":{"$f":"0.25"},"p75":{"$f":"0.25"},"p90":{"$f":"0.25"},"mean_signed":{"$f":"0.25"},"max_ape":{"$f":"0.25"},"worst_index":0,"n_failed":0,"thresholds_met":{"median":false,"p90":true,"mean_signed":false,"max_ape":true},"all_thresholds_met":false},"qualifiers":{"leverage_ok":false,"resolution":"met"},"issues":[],"status":"FAIL","reason":"threshold failure: median, mean_signed"}
verdict-in625-like-all-met {"stats":{"n":12,"median":{"$f":"0.085"},"p75":{"$f":"0.1275"},"p90":{"$f":"0.159"},"mean_signed":{"$f":"0.029166666666666667"},"max_ape":{"$f":"0.19"},"worst_index":8,"n_failed":0,"thresholds_met":{"median":true,"p90":true,"mean_signed":true,"max_ape":true},"all_thresholds_met":true},"qualifiers":{"leverage_ok":false,"resolution":"met"},"issues":[],"status":"INCONCLUSIVE","reason":"all four thresholds met; qualifier not met: leverage"}
verdict-leverage-truthy {"stats":{"n":12,"median":{"$f":"0.085"},"p75":{"$f":"0.1275"},"p90":{"$f":"0.159"},"mean_signed":{"$f":"0.029166666666666667"},"max_ape":{"$f":"0.19"},"worst_index":8,"n_failed":0,"thresholds_met":{"median":true,"p90":true,"mean_signed":true,"max_ape":true},"all_thresholds_met":true},"qualifiers":{"leverage_ok":true,"resolution":"met"},"issues":[],"status":"PASS","reason":"all four thresholds met, leverage and resolution met"}
verdict-empty {"stats":{"n":0,"median":{"$f":"nan"},"p75":{"$f":"nan"},"p90":{"$f":"nan"},"mean_signed":{"$f":"nan"},"max_ape":{"$f":"nan"},"worst_index":null,"n_failed":0,"thresholds_met":{"median":false,"p90":false,"mean_signed":false,"max_ape":false},"all_thresholds_met":false},"qualifiers":{"leverage_ok":true,"resolution":"met"},"issues":[],"status":"INCONCLUSIVE","reason":"n = 0 < 12"}
verdict-exposed-empty {"stats":{"n":0,"median":{"$f":"nan"},"p75":{"$f":"nan"},"p90":{"$f":"nan"},"mean_signed":{"$f":"nan"},"max_ape":{"$f":"nan"},"worst_index":null,"n_failed":0,"thresholds_met":{"median":false,"p90":false,"mean_signed":false,"max_ape":false},"all_thresholds_met":false},"qualifiers":{"leverage_ok":true,"resolution":"met"},"issues":[],"status":"EXPOSED_DESCRIPTIVE","reason":"a target was read before the prediction hash (section 5 item 6)"}
served-bins-0 {"below":{"n":2,"mean_signed":{"$f":"0.1"},"n_failed":1},"between":{"n":2,"mean_signed":{"$f":"-0.015000000000000001"},"n_failed":0},"at_or_above":{"n":2,"mean_signed":{"$f":"0.04"},"n_failed":1}}
served-bins-1 {"below":{"n":2,"mean_signed":{"$f":"0.1"},"n_failed":1},"between":{"n":2,"mean_signed":{"$f":"-0.015000000000000001"},"n_failed":0},"at_or_above":{"n":2,"mean_signed":{"$f":"0.04"},"n_failed":1}}
served-bins-2 {"below":{"n":0,"mean_signed":null,"n_failed":0},"between":{"n":0,"mean_signed":null,"n_failed":0},"at_or_above":{"n":3,"mean_signed":null,"n_failed":3}}
served-bins-3 {"$raises":["KeyError","'316L'"]}
signflip-enumerate-00 {"$f":"1.0"}
signflip-enumerate-01 {"$f":"1.0"}
signflip-enumerate-02 {"$f":"0.5"}
signflip-enumerate-03 {"$f":"1.0"}
signflip-enumerate-04 {"$f":"0.25"}
signflip-enumerate-05 {"$f":"0.5"}
signflip-enumerate-06 {"$f":"0.5"}
signflip-enumerate-07 {"$f":"0.75"}
signflip-enumerate-08 {"$f":"0.5723321437835693"}
signflip-enumerate-09 {"$raises":["ValueError","enumeration is declared for up to 24 nonzero differences"]}
signflip-enumerate-tol {"$f":"0.5"}
dp-p-0 {"$f":"0.625"}
dp-p-1 {"$f":"0.5"}
dp-p-2 {"$f":"0.5"}
dp-p-3 {"$raises":["ValueError","dynamic programming table too large for the declared resolution"]}
dp-p-4 {"$f":"0.25"}
signflip-dp-0 {"p_down":{"$f":"0.03566874470561743"},"p_up":{"$f":"0.035558111034333706"},"p":{"$f":"0.03566874470561743"}}
signflip-dp-1 {"p":{"$f":"1.0"},"p_down":{"$f":"1.0"},"p_up":{"$f":"1.0"}}
signflip-dp-2 {"p":{"$f":"1.0"},"p_down":{"$f":"1.0"},"p_up":{"$f":"1.0"}}
signflip-dp-3 {"p_down":{"$f":"0.036622037179768085"},"p_up":{"$f":"0.03551947884261608"},"p":{"$f":"0.036622037179768085"}}
signflip-p-0 {"p":{"$f":"0.25"},"method":"enumeration","n_nonzero":3}
signflip-p-1 {"p_down":{"$f":"0.06937934458255768"},"p_up":{"$f":"0.06897957623004913"},"p":{"$f":"0.06937934458255768"},"method":"dp_rounded_down_and_up","n_nonzero":26}
signflip-p-2 {"p":{"$f":"0.5723321437835693"},"method":"enumeration","n_nonzero":24}
signflip-p-3 {"p_down":{"$f":"0.41335758566856384"},"p_up":{"$f":"0.41335758566856384"},"p":{"$f":"0.41335758566856384"},"method":"dp_rounded_down_and_up","n_nonzero":25}
paired-differences-0 [{"$f":"0.1"},{"$f":"-0.04999999999999999"},{"$f":"0.25"}]
paired-differences-1 [{"$f":"0.0"},{"$f":"-0.05"},{"$f":"0.05"}]
paired-differences-2 [{"$f":"-0.19999999999999998"},{"$f":"0.19999999999999998"}]
paired-differences-3 [{"$f":"-0.0"},{"$f":"-0.0"}]
paired-differences-4 [{"$f":"0.0"}]
paired-differences-5 [{"$f":"0.05"}]
score-pass-with-flips {"status":"PASS","fragile":{"input":["S1|power:0.95","S1|beam:joint1"],"property":["S1|prop:synthetic_set"]},"resolution":{"cv_pool":{"$f":"0.003526717113149786"},"n_replicated_conditions":14,"pooled_df":14,"needs_pool":false,"u_m_assumed":true,"track_counts":[2,2,2,2,2,2,2,2,2,2,2,2,2,2],"status":"met","median_U":{"$f":"0.060206938696402486"},"median_U_2x_descriptive":{"$f":"0.12010360305666257"},"median_U_t_descriptive":{"$f":"0.382500844815153"},"per_condition":[{"n_t":2,"D_obs_um":{"$f":"150.375"},"u_m_um":{"$f":"5.0"},"U":{"$f":"0.06668718576934854"},"U_2x":{"$f":"0.13309431461097543"},"U_t":{"$f":"0.42367051784091175"}},{"n_t":2,"D_obs_um":{"$f":"160.39999999999998"},"u_m_um":{"$f":"5.0"},"U":{"$f":"0.06254332271313941"},"U_2x":{"$f":"0.12478799005682599"},"U_t":{"$f":"0.3973441316449465"}},{"n_t":2,"D_obs_um":{"$f":"170.425"},"u_m_um":{"$f":"5.11275"},"U":{"$f":"0.060206938696402486"},"U_2x":{"$f":"0.12010360305666257"},"U_t":{"$f":"0.382500844815153"}},{"n_t":2,"D_obs_um":{"$f":"180.45"},"u_m_um":{"$f":"5.413499999999999"},"U":{"$f":"0.06020693869640248"},"U_2x":{"$f":"0.12010360305666255"},"U_t":{"$f":"0.38250084481515295"}},{"n_t":2,"D_obs_um":{"$f":"190.475"},"u_m_um":{"$f":"5.71425"},"U":{"$f":"0.060206938696402486"},"U_2x":{"$f":"0.1201036030566626"},"U_t":{"$f":"0.38250084481515306"}},{"n_t":2,"D_obs_um":{"$f":"200.5"},"u_m_um":{"$f":"6.015"},"U":{"$f":"0.06020693869640248"},"U_2x":{"$f":"0.12010360305666257"},"U_t":{"$f":"0.38250084481515295"}},{"n_t":2,"D_obs_um":{"$f":"210.52499999999998"},"u_m_um":{"$f":"6.315749999999999"},"U":{"$f":"0.06020693869640248"},"U_2x":{"$f":"0.12010360305666255"},"U_t":{"$f":"0.382500844815153"}},{"n_t":2,"D_obs_um":{"$f":"220.54999999999998"},"u_m_um":{"$f":"6.616499999999999"},"U":{"$f":"0.06020693869640248"},"U_2x":{"$f":"0.12010360305666258"},"U_t":{"$f":"0.382500844815153"}},{"n_t":2,"D_obs_um":{"$f":"230.575"},"u_m_um":{"$f":"6.917249999999999"},"U":{"$f":"0.06020693869640248"},"U_2x":{"$f":"0.12010360305666257"},"U_t":{"$f":"0.38250084481515295"}},{"n_t":2,"D_obs_um":{"$f":"240.6"},"u_m_um":{"$f":"7.218"},"U":{"$f":"0.0602069386964025"},"U_2x":{"$f":"0.12010360305666258"},"U_t":{"$f":"0.38250084481515306"}},{"n_t":2,"D_obs_um":{"$f":"250.625"},"u_m_um":{"$f":"7.51875"},"U":{"$f":"0.060206938696402486"},"U_2x":{"$f":"0.12010360305666257"},"U_t":{"$f":"0.38250084481515306"}},{"n_t":2,"D_obs_um":{"$f":"260.65"},"u_m_um":{"$f":"7.819499999999999"},"U":{"$f":"0.06020693869640248"},"U_2x":{"$f":"0.12010360305666257"},"U_t":{"$f":"0.382500844815153"}},{"n_t":2,"D_obs_um":{"$f":"270.67499999999995"},"u_m_um":{"$f":"8.120249999999999"},"U":{"$f":"0.060206938696402486"},"U_2x":{"$f":"0.12010360305666258"},"U_t":{"$f":"0.38250084481515306"}},{"n_t":2,"D_obs_um":{"$f":"280.7"},"u_m_um":{"$f":"8.421"},"U":{"$f":"0.060206938696402486"},"U_2x":{"$f":"0.12010360305666258"},"U_t":{"$f":"0.382500844815153"}}],"reason":null},"leverage":{"cut":{"$f":"15.0"},"n_below":5,"n_at_or_above_20":5,"ok":true},"added_value":{"C0":{"p":{"$f":"6.103515625e-05"},"n_nonzero":14,"improves":true}},"candidate":{"statistics":{"n":14,"median":{"$f":"0.03500000000000001"},"p75":{"$f":"0.05000000000000006"},"p90":{"$f":"0.06000000000000003"},"mean_signed":{"$f":"0.005000000000000018"},"max_ape":{"$f":"0.07000000000000013"},"worst_index":5,"n_failed":0,"thresholds_met":{"median":true,"p90":true,"mean_signed":true,"max_ape":true},"all_thresholds_met":true},"qualifiers":{"leverage_ok":true,"resolution":"met"},"reason":"all four thresholds met, leverage and resolution met","bootstrap_95":{"median":{"lo":{"$f":"0.02000000000000005"},"hi":{"$f":"0.05000000000000007"},"marginal":false},"p90":{"lo":{"$f":"0.047000000000000014"},"hi":{"$f":"0.07000000000000013"},"marginal":false},"mean_signed":{"lo":{"$f":"-0.014999999999999994"},"hi":{"$f":"0.025000000000000033"},"marginal":false},"max_ape":{"lo":{"$f":"0.05000000000000007"},"hi":{"$f":"0.07000000000000013"},"marginal":false}}},"bins":{"below":{"n":5,"mean_signed":{"$f":"3.95516952522712e-17"},"n_failed":0},"between":{"n":4,"mean_signed":{"$f":"0.002500000000000021"},"n_failed":0},"at_or_above":{"n":5,"mean_signed":{"$f":"0.011999999999999997"},"n_failed":0}},"input_fragile":true,"property_fragile":true,"u_m_assumed":true,"worst_condition":"synthetic-c06","track_counts":[2,2,2,2,2,2,2,2,2,2,2,2,2,2],"marginal":[],"arms":{"C0":{"kind":"nominal","label":"synthetic C0","status":"FAIL","reason":"threshold failure: median, mean_signed","n":14,"median":{"$f":"0.30000000000000004"},"p75":{"$f":"0.30000000000000004"},"p90":{"$f":"0.3000000000000001"},"mean_signed":{"$f":"-0.30000000000000004"},"max_ape":{"$f":"0.3000000000000001"},"n_failed":0,"thresholds_met":{"median":false,"p90":true,"mean_signed":false,"max_ape":true},"unavailable_conditions":[]},"S1":{"kind":"nominal","label":"synthetic S1","status":"PASS","reason":"all four thresholds met, leverage and resolution met","n":14,"median":{"$f":"0.03500000000000001"},"p75":{"$f":"0.05000000000000006"},"p90":{"$f":"0.06000000000000003"},"mean_signed":{"$f":"0.005000000000000018"},"max_ape":{"$f":"0.07000000000000013"},"n_failed":0,"thresholds_met":{"median":true,"p90":true,"mean_signed":true,"max_ape":true},"unavailable_conditions":[]},"C0-srv":{"kind":"descriptive","label":"synthetic C0-srv","status":"FAIL","reason":"threshold failure: median, mean_signed","n":14,"median":{"$f":"0.25"},"p75":{"$f":"0.25000000000000006"},"p90":{"$f":"0.25000000000000006"},"mean_signed":{"$f":"-0.25"},"max_ape":{"$f":"0.25000000000000006"},"n_failed":0,"thresholds_met":{"median":false,"p90":true,"mean_signed":false,"max_ape":true},"unavailable_conditions":[]},"S1-srv":{"kind":"descriptive","label":"synthetic S1-srv","status":"PASS","reason":"all four thresholds met, leverage and resolution met","n":14,"median":{"$f":"0.03500000000000001"},"p75":{"$f":"0.05000000000000006"},"p90":{"$f":"0.06000000000000003"},"mean_signed":{"$f":"0.005000000000000018"},"max_ape":{"$f":"0.07000000000000013"},"n_failed":0,"thresholds_met":{"median":true,"p90":true,"mean_signed":true,"max_ape":true},"unavailable_conditions":[]},"S1|power:0.95":{"kind":"power","label":"synthetic S1|power:0.95","status":"FAIL","reason":"threshold failure: mean_signed","n":14,"median":{"$f":"0.11500000000000002"},"p75":{"$f":"0.1475"},"p90":{"$f":"0.16700000000000004"},"mean_signed":{"$f":"-0.11499999999999998"},"max_ape":{"$f":"0.18"},"n_failed":0,"thresholds_met":{"median":true,"p90":true,"mean_signed":false,"max_ape":true},"unavailable_conditions":[]},"S1|power:1.05":{"kind":"power","label":"synthetic S1|power:1.05","status":"PASS","reason":"all four thresholds met, leverage and resolution met","n":13,"median":{"$f":"0.030000000000000044"},"p75":{"$f":"0.06000000000000003"},"p90":{"$f":"0.07800000000000011"},"mean_signed":{"$f":"0.0230769230769231"},"max_ape":{"$f":"0.09000000000000008"},"n_failed":0,"thresholds_met":{"median":true,"p90":true,"mean_signed":true,"max_ape":true},"unavailable_conditions":["synthetic-c03"]},"S1|beam:joint0":{"kind":"beam","label":"synthetic S1|beam:joint0","status":"PASS","reason":"all four thresholds met, leverage and resolution met","n":14,"median":{"$f":"0.03500000000000001"},"p75":{"$f":"0.05000000000000006"},"p90":{"$f":"0.06000000000000003"},"mean_signed":{"$f":"0.005000000000000018"},"max_ape":{"$f":"0.07000000000000013"},"n_failed":0,"thresholds_met":{"median":true,"p90":true,"mean_signed":true,"max_ape":true},"unavailable_conditions":[]},"S1|beam:joint1":{"kind":"beam","label":"synthetic S1|beam:joint1","status":"FAIL","reason":"threshold failure: max_ape","n":14,"median":{"$f":"0.03999999999999999"},"p75":{"$f":"0.05750000000000001"},"p90":{"$f":"0.0670000000000001"},"mean_signed":{"$f":"0.0038461538461538602"},"max_ape":{"$f":"inf"},"n_failed":1,"thresholds_met":{"median":true,"p90":true,"mean_signed":true,"max_ape":false},"unavailable_conditions":[]},"S1|beam:A:0":{"kind":"beam_single","label":"synthetic S1|beam:A:0","status":"FAIL","reason":"threshold failure: median, p90, mean_signed","n":14,"median":{"$f":"0.4"},"p75":{"$f":"0.4"},"p90":{"$f":"0.4"},"mean_signed":{"$f":"-0.39999999999999997"},"max_ape":{"$f":"0.4"},"n_failed":0,"thresholds_met":{"median":false,"p90":false,"mean_signed":false,"max_ape":true},"unavailable_conditions":[]},"S1|prop:synthetic_set":{"kind":"property","label":"synthetic S1|prop:synthetic_set","status":"FAIL","reason":"threshold failure: median, p90, mean_signed","n":14,"median":{"$f":"0.3050000000000001"},"p75":{"$f":"0.3375"},"p90":{"$f":"0.3570000000000001"},"mean_signed":{"$f":"0.30500000000000005"},"max_ape":{"$f":"0.37"},"n_failed":0,"thresholds_met":{"median":false,"p90":false,"mean_signed":false,"max_ape":true},"unavailable_conditions":[]},"S1|prop:srv":{"kind":"descriptive","label":"synthetic S1|prop:srv","status":"FAIL","reason":"threshold failure: median, p90, mean_signed","n":14,"median":{"$f":"0.5"},"p75":{"$f":"0.5"},"p90":{"$f":"0.5"},"mean_signed":{"$f":"-0.5"},"max_ape":{"$f":"0.5"},"n_failed":0,"thresholds_met":{"median":false,"p90":false,"mean_signed":false,"max_ape":true},"unavailable_conditions":[]},"S1|abs:synthetic_lo":{"kind":"absorptance","label":"synthetic S1|abs:synthetic_lo","status":"PASS","reason":"all four thresholds met, leverage and resolution met","n":14,"median":{"$f":"0.03500000000000001"},"p75":{"$f":"0.05000000000000006"},"p90":{"$f":"0.06000000000000003"},"mean_signed":{"$f":"0.005000000000000018"},"max_ape":{"$f":"0.07000000000000013"},"n_failed":0,"thresholds_met":{"median":true,"p90":true,"mean_signed":true,"max_ape":true},"unavailable_conditions":[]}}}
score-fail-alsi {"status":"FAIL","fragile":{"input":[],"property":[]},"resolution":{"cv_pool":null,"n_replicated_conditions":0,"pooled_df":0,"needs_pool":true,"u_m_assumed":false,"track_counts":[1,1,1,1,1,1,1,1,1,1,1,1,1],"status":"not_evaluable","median_U":null,"median_U_2x_descriptive":null,"median_U_t_descriptive":null,"reason":"single track conditions need cv_pool, which needs at least 3 conditions with 2 or more tracks and pooled degrees of freedom of at least 3; got 0 and 0"},"leverage":{"cut":{"$f":"15.0"},"n_below":4,"n_at_or_above_20":6,"ok":true},"added_value":{"C0":{"p":{"$f":"0.056884765625"},"n_nonzero":12,"improves":false}},"candidate":{"statistics":{"n":13,"median":{"$f":"0.16999999999999998"},"p75":{"$f":"0.2"},"p90":{"$f":"0.21799999999999997"},"mean_signed":{"$f":"0.15999999999999992"},"max_ape":{"$f":"inf"},"worst_index":6,"n_failed":1,"thresholds_met":{"median":true,"p90":true,"mean_signed":false,"max_ape":false},"all_thresholds_met":false},"qualifiers":{"leverage_ok":true,"resolution":"not_evaluable"},"reason":"threshold failure: mean_signed, max_ape","bootstrap_95":{"median":{"lo":{"$f":"0.12999999999999998"},"hi":{"$f":"0.2"},"marginal":true},"p90":{"lo":{"$f":"0.18799999999999992"},"hi":{"$f":"inf"},"marginal":true},"mean_signed":{"lo":{"$f":"0.1376923076923076"},"hi":{"$f":"0.18307692307692303"},"marginal":false},"max_ape":{"lo":{"$f":"0.2"},"hi":{"$f":"inf"},"marginal":true}}},"bins":{"below":{"n":4,"mean_signed":{"$f":"0.1449999999999999"},"n_failed":0},"between":{"n":3,"mean_signed":{"$f":"0.19499999999999998"},"n_failed":1},"at_or_above":{"n":6,"mean_signed":{"$f":"0.15833333333333327"},"n_failed":0}},"input_fragile":false,"property_fragile":false,"u_m_assumed":false,"worst_condition":"synthetic-c07","track_counts":[1,1,1,1,1,1,1,1,1,1,1,1,1],"marginal":["median","p90","max_ape"],"arms":{"C0":{"kind":"nominal","label":"synthetic C0","status":"FAIL","reason":"threshold failure: mean_signed","n":13,"median":{"$f":"0.19999999999999996"},"p75":{"$f":"0.2"},"p90":{"$f":"0.2"},"mean_signed":{"$f":"-0.19999999999999996"},"max_ape":{"$f":"0.20000000000000004"},"n_failed":0,"thresholds_met":{"median":true,"p90":true,"mean_signed":false,"max_ape":true},"unavailable_conditions":[]},"S1":{"kind":"nominal","label":"synthetic S1","status":"FAIL","reason":"threshold failure: mean_signed, max_ape","n":13,"median":{"$f":"0.16999999999999998"},"p75":{"$f":"0.2"},"p90":{"$f":"0.21799999999999997"},"mean_signed":{"$f":"0.15999999999999992"},"max_ape":{"$f":"inf"},"n_failed":1,"thresholds_met":{"median":true,"p90":true,"mean_signed":false,"max_ape":false},"unavailable_conditions":[]},"S1|power:0.95":{"kind":"power","label":"synthetic S1|power:0.95","status":"INCONCLUSIVE","reason":"all four thresholds met; qualifier not met: resolution not evaluable","n":13,"median":{"$f":"0.039999999999999966"},"p75":{"$f":"0.05"},"p90":{"$f":"0.060000000000000095"},"mean_signed":{"$f":"0.005384615384615402"},"max_ape":{"$f":"0.07000000000000015"},"n_failed":0,"thresholds_met":{"median":true,"p90":true,"mean_signed":true,"max_ape":true},"unavailable_conditions":[]},"S1|prop:srv":{"kind":"property","label":"synthetic S1|prop:srv","status":"INCONCLUSIVE","reason":"all four thresholds met; qualifier not met: resolution not evaluable","n":13,"median":{"$f":"0.039999999999999966"},"p75":{"$f":"0.05"},"p90":{"$f":"0.060000000000000095"},"mean_signed":{"$f":"0.005384615384615402"},"max_ape":{"$f":"0.07000000000000015"},"n_failed":0,"thresholds_met":{"median":true,"p90":true,"mean_signed":true,"max_ape":true},"unavailable_conditions":[]},"S1|abs:0.14":{"kind":"absorptance","label":"synthetic S1|abs:0.14","status":"INCONCLUSIVE","reason":"all four thresholds met; qualifier not met: resolution not evaluable","n":12,"median":{"$f":"0.03500000000000003"},"p75":{"$f":"0.05250000000000001"},"p90":{"$f":"0.0600000000000001"},"mean_signed":{"$f":"0.009166666666666684"},"max_ape":{"$f":"0.07000000000000015"},"n_failed":0,"thresholds_met":{"median":true,"p90":true,"mean_signed":true,"max_ape":true},"unavailable_conditions":["synthetic-c02"]}}}
score-leverage-not-met {"status":"INCONCLUSIVE","fragile":{"input":[],"property":[]},"resolution":{"cv_pool":{"$f":"0.007780134985620047"},"n_replicated_conditions":12,"pooled_df":24,"needs_pool":false,"u_m_assumed":true,"track_counts":[3,3,3,3,3,3,3,3,3,3,3,3],"status":"met","median_U":{"$f":"0.06065759971021383"},"median_U_2x_descriptive":{"$f":"0.12033014816105297"},"median_U_t_descriptive":{"$f":"0.13049429348498373"},"per_condition":[{"n_t":3,"D_obs_um":{"$f":"200.16666666666666"},"u_m_um":{"$f":"6.005"},"U":{"$f":"0.06084904843433616"},"U_2x":{"$f":"0.12042676901488385"},"U_t":{"$f":"0.13090616217270462"}},{"n_t":3,"D_obs_um":{"$f":"205.16666666666666"},"u_m_um":{"$f":"6.154999999999999"},"U":{"$f":"0.06080844099818853"},"U_2x":{"$f":"0.12040625605270756"},"U_t":{"$f":"0.13081880232471133"}},{"n_t":3,"D_obs_um":{"$f":"210.16666666666666"},"u_m_um":{"$f":"6.305"},"U":{"$f":"0.060770672844430135"},"U_2x":{"$f":"0.1203871865190177"},"U_t":{"$f":"0.13073755069977927"}},{"n_t":3,"D_obs_um":{"$f":"215.16666666666666"},"u_m_um":{"$f":"6.454999999999999"},"U":{"$f":"0.060735485807940706"},"U_2x":{"$f":"0.12036942816316179"},"U_t":{"$f":"0.1306618519004787"}},{"n_t":3,"D_obs_um":{"$f":"220.16666666666666"},"u_m_um":{"$f":"6.6049999999999995"},"U":{"$f":"0.06070265036116464"},"U_2x":{"$f":"0.12035286353415028"},"U_t":{"$f":"0.13059121213812777"}},{"n_t":3,"D_obs_um":{"$f":"225.16666666666666"},"u_m_um":{"$f":"6.755"},"U":{"$f":"0.060671961891285375"},"U_2x":{"$f":"0.12033738803770665"},"U_t":{"$f":"0.13052519122377967"}},{"n_t":3,"D_obs_um":{"$f":"230.16666666666666"},"u_m_um":{"$f":"6.904999999999999"},"U":{"$f":"0.06064323752914229"},"U_2x":{"$f":"0.12032290828439932"},"U_t":{"$f":"0.1304633957461878"}},{"n_t":3,"D_obs_um":{"$f":"235.16666666666666"},"u_m_um":{"$f":"7.055"},"U":{"$f":"0.060616313438515965"},"U_2x":{"$f":"0.12030934068008356"},"U_t":{"$f":"0.13040547324017385"}},{"n_t":3,"D_obs_um":{"$f":"240.16666666666666"},"u_m_um":{"$f":"7.204999999999999"},"U":{"$f":"0.06059104249106221"},"U_2x":{"$f":"0.12029661021888233"},"U_t":{"$f":"0.13035110718465187"}},{"n_t":3,"D_obs_um":{"$f":"245.16666666666666"},"u_m_um":{"$f":"7.3549999999999995"},"U":{"$f":"0.060567292265528525"},"U_2x":{"$f":"0.12028464944612821"},"U_t":{"$f":"0.13030001269829017"}},{"n_t":3,"D_obs_um":{"$f":"250.16666666666666"},"u_m_um":{"$f":"7.504999999999999"},"U":{"$f":"0.06054494332064308"},"U_2x":{"$f":"0.1202733975644651"},"U_t":{"$f":"0.13025193282393158"}},{"n_t":3,"D_obs_um":{"$f":"255.16666666666666"},"u_m_um":{"$f":"7.654999999999999"},"U":{"$f":"0.06052388769977107"},"U_2x":{"$f":"0.12026279966096956"},"U_t":{"$f":"0.13020663531162138"}}],"reason":null},"leverage":{"cut":{"$f":"15.0"},"n_below":9,"n_at_or_above_20":3,"ok":false},"added_value":{"C0":{"p":{"$f":"0.000244140625"},"n_nonzero":12,"improves":true}},"candidate":{"statistics":{"n":12,"median":{"$f":"0.040000000000000105"},"p75":{"$f":"0.05250000000000021"},"p90":{"$f":"0.06000000000000012"},"mean_signed":{"$f":"0.006666666666666694"},"max_ape":{"$f":"0.07000000000000021"},"worst_index":5,"n_failed":0,"thresholds_met":{"median":true,"p90":true,"mean_signed":true,"max_ape":true},"all_thresholds_met":true},"qualifiers":{"leverage_ok":false,"resolution":"met"},"reason":"all four thresholds met; qualifier not met: leverage","bootstrap_95":{"median":{"lo":{"$f":"0.02500000000000006"},"hi":{"$f":"0.05500000000000018"},"marginal":false},"p90":{"lo":{"$f":"0.0490000000000001"},"hi":{"$f":"0.07000000000000021"},"marginal":false},"mean_signed":{"lo":{"$f":"-0.017500000000000043"},"hi":{"$f":"0.03083333333333343"},"marginal":false},"max_ape":{"lo":{"$f":"0.050000000000000246"},"hi":{"$f":"0.07000000000000021"},"marginal":false}}},"bins":{"below":{"n":9,"mean_signed":{"$f":"0.0011111111111111295"},"n_failed":0},"between":{"n":0,"mean_signed":null,"n_failed":0},"at_or_above":{"n":3,"mean_signed":{"$f":"0.023333333333333386"},"n_failed":0}},"input_fragile":false,"property_fragile":false,"u_m_assumed":true,"worst_condition":"synthetic-c06","track_counts":[3,3,3,3,3,3,3,3,3,3,3,3],"marginal":[],"arms":{"C0":{"kind":"nominal","label":"synthetic C0","status":"FAIL","reason":"threshold failure: mean_signed","n":12,"median":{"$f":"0.15000000000000002"},"p75":{"$f":"0.15000000000000002"},"p90":{"$f":"0.15000000000000002"},"mean_signed":{"$f":"-0.15000000000000002"},"max_ape":{"$f":"0.15000000000000002"},"n_failed":0,"thresholds_met":{"median":true,"p90":true,"mean_signed":false,"max_ape":true},"unavailable_conditions":[]},"S1":{"kind":"nominal","label":"synthetic S1","status":"INCONCLUSIVE","reason":"all four thresholds met; qualifier not met: leverage","n":12,"median":{"$f":"0.040000000000000105"},"p75":{"$f":"0.05250000000000021"},"p90":{"$f":"0.06000000000000012"},"mean_signed":{"$f":"0.006666666666666694"},"max_ape":{"$f":"0.07000000000000021"},"n_failed":0,"thresholds_met":{"median":true,"p90":true,"mean_signed":true,"max_ape":true},"unavailable_conditions":[]},"S1|power:0.95":{"kind":"power","label":"synthetic S1|power:0.95","status":"FAIL","reason":"threshold failure: mean_signed","n":12,"median":{"$f":"0.18499999999999997"},"p75":{"$f":"0.23249999999999998"},"p90":{"$f":"0.24899999999999997"},"mean_signed":{"$f":"-0.19333333333333327"},"max_ape":{"$f":"0.26"},"n_failed":0,"thresholds_met":{"median":true,"p90":true,"mean_signed":false,"max_ape":true},"unavailable_conditions":[]}}}
score-exposed {"status":"EXPOSED_DESCRIPTIVE","fragile":{"input":[],"property":[]},"resolution":{"cv_pool":{"$f":"0.011659770857942191"},"n_replicated_conditions":12,"pooled_df":12,"needs_pool":false,"u_m_assumed":true,"track_counts":[2,2,2,2,2,2,2,2,2,2,2,2],"status":"met","median_U":{"$f":"0.062188226238991576"},"median_U_2x_descriptive":{"$f":"0.12110894723060384"},"median_U_t_descriptive":{"$f":"0.3950881673940927"},"per_condition":[{"n_t":2,"D_obs_um":{"$f":"161.5"},"u_m_um":{"$f":"5.0"},"U":{"$f":"0.06464586073628824"},"U_2x":{"$f":"0.12522444839725502"},"U_t":{"$f":"0.4107017709390776"}},{"n_t":2,"D_obs_um":{"$f":"165.5"},"u_m_um":{"$f":"5.0"},"U":{"$f":"0.06308342301456527"},"U_2x":{"$f":"0.12219787562632438"},"U_t":{"$f":"0.4007754441490093"}},{"n_t":2,"D_obs_um":{"$f":"169.5"},"u_m_um":{"$f":"5.085"},"U":{"$f":"0.0625560442591243"},"U_2x":{"$f":"0.12129822205353843"},"U_t":{"$f":"0.39742495292887053"}},{"n_t":2,"D_obs_um":{"$f":"173.5"},"u_m_um":{"$f":"5.205"},"U":{"$f":"0.0624418207068233"},"U_2x":{"$f":"0.12123935406122498"},"U_t":{"$f":"0.396699279008241"}},{"n_t":2,"D_obs_um":{"$f":"177.5"},"u_m_um":{"$f":"5.325"},"U":{"$f":"0.06233504317490713"},"U_2x":{"$f":"0.12118439506643394"},"U_t":{"$f":"0.3960209104173521"}},{"n_t":2,"D_obs_um":{"$f":"181.5"},"u_m_um":{"$f":"5.444999999999999"},"U":{"$f":"0.06223508160311214"},"U_2x":{"$f":"0.1211330069887891"},"U_t":{"$f":"0.3953858443188507"}},{"n_t":2,"D_obs_um":{"$f":"185.5"},"u_m_um":{"$f":"5.5649999999999995"},"U":{"$f":"0.062141370874871"},"U_2x":{"$f":"0.12108488747241856"},"U_t":{"$f":"0.3947904904693347"}},{"n_t":2,"D_obs_um":{"$f":"189.5"},"u_m_um":{"$f":"5.685"},"U":{"$f":"0.06205340298165653"},"U_2x":{"$f":"0.12103976545583628"},"U_t":{"$f":"0.39423162143862683"}},{"n_t":2,"D_obs_um":{"$f":"193.5"},"u_m_um":{"$f":"5.805"},"U":{"$f":"0.06197072026418521"},"U_2x":{"$f":"0.12099739736895952"},"U_t":{"$f":"0.3937063296704493"}},{"n_t":2,"D_obs_um":{"$f":"197.5"},"u_m_um":{"$f":"5.925"},"U":{"$f":"0.06189290956520305"},"U_2x":{"$f":"0.12095756385793491"},"U_t":{"$f":"0.3932119903344732"}},{"n_t":2,"D_obs_um":{"$f":"201.5"},"u_m_um":{"$f":"6.045"},"U":{"$f":"0.06181959715648681"},"U_2x":{"$f":"0.12092006695577998"},"U_t":{"$f":"0.3927462290970384"}},{"n_t":2,"D_obs_um":{"$f":"205.5"},"u_m_um":{"$f":"6.165"},"U":{"$f":"0.06175044432547791"},"U_2x":{"$f":"0.12088472763088788"},"U_t":{"$f":"0.3923068940825869"}}],"reason":null},"leverage":{"cut":{"$f":"15.0"},"n_below":4,"n_at_or_above_20":4,"ok":true},"added_value":{"C0":{"p":{"$f":"0.000244140625"},"n_nonzero":12,"improves":true}},"candidate":{"statistics":{"n":12,"median":{"$f":"0.04000000000000003"},"p75":{"$f":"0.052500000000000074"},"p90":{"$f":"0.06000000000000005"},"mean_signed":{"$f":"0.00666666666666669"},"max_ape":{"$f":"0.07000000000000006"},"worst_index":5,"n_failed":0,"thresholds_met":{"median":true,"p90":true,"mean_signed":true,"max_ape":true},"all_thresholds_met":true},"qualifiers":{"leverage_ok":true,"resolution":"met"},"reason":"a target was read before the prediction hash (section 5 item 6)","bootstrap_95":{"median":{"lo":{"$f":"0.025000000000000053"},"hi":{"$f":"0.05500000000000004"},"marginal":false},"p90":{"lo":{"$f":"0.04900000000000003"},"hi":{"$f":"0.07000000000000006"},"marginal":false},"mean_signed":{"lo":{"$f":"-0.01750000000000001"},"hi":{"$f":"0.03083333333333339"},"marginal":false},"max_ape":{"lo":{"$f":"0.05000000000000011"},"hi":{"$f":"0.07000000000000006"},"marginal":false}}},"bins":{"below":{"n":4,"mean_signed":{"$f":"-0.004999999999999963"},"n_failed":0},"between":{"n":4,"mean_signed":{"$f":"0.012500000000000037"},"n_failed":0},"at_or_above":{"n":4,"mean_signed":{"$f":"0.012499999999999997"},"n_failed":0}},"input_fragile":false,"property_fragile":false,"u_m_assumed":true,"worst_condition":"synthetic-c06","track_counts":[2,2,2,2,2,2,2,2,2,2,2,2],"marginal":[],"arms":{"C0":{"kind":"nominal","label":"synthetic C0","status":"EXPOSED_DESCRIPTIVE","reason":"a target was read before the prediction hash (section 5 item 6)","n":12,"median":{"$f":"0.30000000000000004"},"p75":{"$f":"0.30000000000000004"},"p90":{"$f":"0.3000000000000001"},"mean_signed":{"$f":"-0.30000000000000004"},"max_ape":{"$f":"0.3000000000000001"},"n_failed":0,"thresholds_met":{"median":false,"p90":true,"mean_signed":false,"max_ape":true},"unavailable_conditions":[]},"S1":{"kind":"nominal","label":"synthetic S1","status":"EXPOSED_DESCRIPTIVE","reason":"a target was read before the prediction hash (section 5 item 6)","n":12,"median":{"$f":"0.04000000000000003"},"p75":{"$f":"0.052500000000000074"},"p90":{"$f":"0.06000000000000005"},"mean_signed":{"$f":"0.00666666666666669"},"max_ape":{"$f":"0.07000000000000006"},"n_failed":0,"thresholds_met":{"median":true,"p90":true,"mean_signed":true,"max_ape":true},"unavailable_conditions":[]},"S1|power:0.95":{"kind":"power","label":"synthetic S1|power:0.95","status":"EXPOSED_DESCRIPTIVE","reason":"a target was read before the prediction hash (section 5 item 6)","n":12,"median":{"$f":"0.19999999999999996"},"p75":{"$f":"0.2"},"p90":{"$f":"0.20000000000000004"},"mean_signed":{"$f":"-0.19999999999999996"},"max_ape":{"$f":"0.20000000000000004"},"n_failed":0,"thresholds_met":{"median":true,"p90":true,"mean_signed":false,"max_ape":true},"unavailable_conditions":[]}}}
score-small-with-issue {"status":"INCONCLUSIVE","fragile":{"input":[],"property":[]},"resolution":{"cv_pool":{"$f":"0.011773793666519967"},"n_replicated_conditions":11,"pooled_df":11,"needs_pool":false,"u_m_assumed":true,"track_counts":[2,2,2,2,2,2,2,2,2,2,2],"status":"met","median_U":{"$f":"0.06223508160311214"},"median_U_2x_descriptive":{"$f":"0.1211330069887891"},"median_U_t_descriptive":{"$f":"0.3953858443188507"},"per_condition":[{"n_t":2,"D_obs_um":{"$f":"161.5"},"u_m_um":{"$f":"5.0"},"U":{"$f":"0.06464586073628824"},"U_2x":{"$f":"0.12522444839725502"},"U_t":{"$f":"0.4107017709390776"}},{"n_t":2,"D_obs_um":{"$f":"165.5"},"u_m_um":{"$f":"5.0"},"U":{"$f":"0.06308342301456527"},"U_2x":{"$f":"0.12219787562632438"},"U_t":{"$f":"0.4007754441490093"}},{"n_t":2,"D_obs_um":{"$f":"169.5"},"u_m_um":{"$f":"5.085"},"U":{"$f":"0.0625560442591243"},"U_2x":{"$f":"0.12129822205353843"},"U_t":{"$f":"0.39742495292887053"}},{"n_t":2,"D_obs_um":{"$f":"173.5"},"u_m_um":{"$f":"5.205"},"U":{"$f":"0.0624418207068233"},"U_2x":{"$f":"0.12123935406122498"},"U_t":{"$f":"0.396699279008241"}},{"n_t":2,"D_obs_um":{"$f":"177.5"},"u_m_um":{"$f":"5.325"},"U":{"$f":"0.06233504317490713"},"U_2x":{"$f":"0.12118439506643394"},"U_t":{"$f":"0.3960209104173521"}},{"n_t":2,"D_obs_um":{"$f":"181.5"},"u_m_um":{"$f":"5.444999999999999"},"U":{"$f":"0.06223508160311214"},"U_2x":{"$f":"0.1211330069887891"},"U_t":{"$f":"0.3953858443188507"}},{"n_t":2,"D_obs_um":{"$f":"185.5"},"u_m_um":{"$f":"5.5649999999999995"},"U":{"$f":"0.062141370874871"},"U_2x":{"$f":"0.12108488747241856"},"U_t":{"$f":"0.3947904904693347"}},{"n_t":2,"D_obs_um":{"$f":"189.5"},"u_m_um":{"$f":"5.685"},"U":{"$f":"0.06205340298165653"},"U_2x":{"$f":"0.12103976545583628"},"U_t":{"$f":"0.39423162143862683"}},{"n_t":2,"D_obs_um":{"$f":"193.5"},"u_m_um":{"$f":"5.805"},"U":{"$f":"0.06197072026418521"},"U_2x":{"$f":"0.12099739736895952"},"U_t":{"$f":"0.3937063296704493"}},{"n_t":2,"D_obs_um":{"$f":"197.5"},"u_m_um":{"$f":"5.925"},"U":{"$f":"0.06189290956520305"},"U_2x":{"$f":"0.12095756385793491"},"U_t":{"$f":"0.3932119903344732"}},{"n_t":2,"D_obs_um":{"$f":"201.5"},"u_m_um":{"$f":"6.045"},"U":{"$f":"0.06181959715648681"},"U_2x":{"$f":"0.12092006695577998"},"U_t":{"$f":"0.3927462290970384"}}],"reason":null},"leverage":{"cut":{"$f":"15.0"},"n_below":4,"n_at_or_above_20":4,"ok":true},"added_value":{"C0":{"p":{"$f":"0.00048828125"},"n_nonzero":11,"improves":true}},"candidate":{"statistics":{"n":11,"median":{"$f":"0.04000000000000003"},"p75":{"$f":"0.05000000000000007"},"p90":{"$f":"0.05999999999999998"},"mean_signed":{"$f":"0.0018181818181818381"},"max_ape":{"$f":"0.07000000000000006"},"worst_index":5,"n_failed":0,"thresholds_met":{"median":true,"p90":true,"mean_signed":true,"max_ape":true},"all_thresholds_met":true},"qualifiers":{"leverage_ok":true,"resolution":"met"},"reason":"n = 11 < 12; synthetic block issue","bootstrap_95":{"median":{"lo":{"$f":"0.020000000000000063"},"hi":{"$f":"0.05000000000000011"},"marginal":false},"p90":{"lo":{"$f":"0.04000000000000003"},"hi":{"$f":"0.07000000000000006"},"marginal":false},"mean_signed":{"lo":{"$f":"-0.02272727272727272"},"hi":{"$f":"0.025454545454545507"},"marginal":false},"max_ape":{"lo":{"$f":"0.05000000000000003"},"hi":{"$f":"0.07000000000000006"},"marginal":false}}},"bins":{"below":{"n":4,"mean_signed":{"$f":"-0.004999999999999963"},"n_failed":0},"between":{"n":3,"mean_signed":{"$f":"0.013333333333333364"},"n_failed":0},"at_or_above":{"n":4,"mean_signed":{"$f":"-5.204170427930421e-18"},"n_failed":0}},"input_fragile":false,"property_fragile":false,"u_m_assumed":true,"worst_condition":"synthetic-c06","track_counts":[2,2,2,2,2,2,2,2,2,2,2],"marginal":[],"arms":{"C0":{"kind":"nominal","label":"synthetic C0","status":"INCONCLUSIVE","reason":"n = 11 < 12; synthetic block issue","n":11,"median":{"$f":"0.30000000000000004"},"p75":{"$f":"0.30000000000000004"},"p90":{"$f":"0.3000000000000001"},"mean_signed":{"$f":"-0.30000000000000004"},"max_ape":{"$f":"0.3000000000000001"},"n_failed":0,"thresholds_met":{"median":false,"p90":true,"mean_signed":false,"max_ape":true},"unavailable_conditions":[]},"S1":{"kind":"nominal","label":"synthetic S1","status":"INCONCLUSIVE","reason":"n = 11 < 12; synthetic block issue","n":11,"median":{"$f":"0.04000000000000003"},"p75":{"$f":"0.05000000000000007"},"p90":{"$f":"0.05999999999999998"},"mean_signed":{"$f":"0.0018181818181818381"},"max_ape":{"$f":"0.07000000000000006"},"n_failed":0,"thresholds_met":{"median":true,"p90":true,"mean_signed":true,"max_ape":true},"unavailable_conditions":[]}}}
score-powder-not-scored {"status":"DESCRIPTIVE_NOT_SCORED","fragile":{"input":[],"property":[]},"resolution":{"cv_pool":{"$f":"0.013342477043137922"},"n_replicated_conditions":12,"pooled_df":12,"needs_pool":false,"u_m_assumed":true,"track_counts":[2,2,2,2,2,2,2,2,2,2,2,2],"status":"not_met","median_U":{"$f":"0.12691964911949188"},"median_U_2x_descriptive":{"$f":"0.2512644382475117"},"median_U_t_descriptive":{"$f":"0.8063335233941936"},"per_condition":[{"n_t":2,"D_obs_um":{"$f":"91.0"},"u_m_um":{"$f":"10.0"},"U":{"$f":"0.2208763872773822"},"U_2x":{"$f":"0.44010954713188544"},"U_t":{"$f":"1.4032502990949418"}},{"n_t":2,"D_obs_um":{"$f":"94.0"},"u_m_um":{"$f":"4.0"},"U":{"$f":"0.0877256516088864"},"U_2x":{"$f":"0.17153739889996913"},"U_t":{"$f":"0.5573300449897121"}},{"n_t":2,"D_obs_um":{"$f":"97.0"},"u_m_um":{"$f":"10.0"},"U":{"$f":"0.2072139303323895"},"U_2x":{"$f":"0.41288627617527396"},"U_t":{"$f":"1.3164513115220589"}},{"n_t":2,"D_obs_um":{"$f":"100.0"},"u_m_um":{"$f":"4.0"},"U":{"$f":"0.0824621125123532"},"U_2x":{"$f":"0.16124515496597097"},"U_t":{"$f":"0.5238902422903293"}},{"n_t":2,"D_obs_um":{"$f":"103.0"},"u_m_um":{"$f":"10.0"},"U":{"$f":"0.19514321594409495"},"U_2x":{"$f":"0.3888346484369085"},"U_t":{"$f":"1.2397648273557254"}},{"n_t":2,"D_obs_um":{"$f":"106.0"},"u_m_um":{"$f":"4.0"},"U":{"$f":"0.07779444576637096"},"U_2x":{"$f":"0.15211807072261413"},"U_t":{"$f":"0.4942360776323862"}},{"n_t":2,"D_obs_um":{"$f":"109.0"},"u_m_um":{"$f":"10.0"},"U":{"$f":"0.18440138754350258"},"U_2x":{"$f":"0.36743090632111536"},"U_t":{"$f":"1.1715208919049513"}},{"n_t":2,"D_obs_um":{"$f":"112.0"},"u_m_um":{"$f":"4.0"},"U":{"$f":"0.07362688617174394"},"U_2x":{"$f":"0.1439688883624741"},"U_t":{"$f":"0.46775914490207976"}},{"n_t":2,"D_obs_um":{"$f":"115.0"},"u_m_um":{"$f":"10.0"},"U":{"$f":"0.17478044558471112"},"U_2x":{"$f":"0.3482605981652311"},"U_t":{"$f":"1.1103980627620844"}},{"n_t":2,"D_obs_um":{"$f":"118.0"},"u_m_um":{"$f":"4.0"},"U":{"$f":"0.0698831461969095"},"U_2x":{"$f":"0.13664843641183982"},"U_t":{"$f":"0.443974781601974"}},{"n_t":2,"D_obs_um":{"$f":"121.0"},"u_m_um":{"$f":"10.0"},"U":{"$f":"0.16611364663009737"},"U_2x":{"$f":"0.3309914775950543"},"U_t":{"$f":"1.0553370017986752"}},{"n_t":2,"D_obs_um":{"$f":"124.0"},"u_m_um":{"$f":"4.0"},"U":{"$f":"0.06650170363899452"},"U_2x":{"$f":"0.1300364152951379"},"U_t":{"$f":"0.4224921308792979"}}],"reason":"median U_c 0.1269 above 0.1"},"leverage":{"cut":{"$f":"15.0"},"n_below":4,"n_at_or_above_20":4,"ok":true},"added_value":{"C0":{"p":{"$f":"0.000244140625"},"n_nonzero":12,"improves":true}},"candidate":{"statistics":{"n":12,"median":{"$f":"0.04000000000000002"},"p75":{"$f":"0.05250000000000001"},"p90":{"$f":"0.06"},"mean_signed":{"$f":"0.006666666666666654"},"max_ape":{"$f":"0.07000000000000002"},"worst_index":5,"n_failed":0,"thresholds_met":{"median":true,"p90":true,"mean_signed":true,"max_ape":true},"all_thresholds_met":true},"qualifiers":{"leverage_ok":true,"resolution":"not_met"},"reason":"powder layer block without a same-setup absorptance or a declared P5 bias (Amendment 6 item 6)","bootstrap_95":{"median":{"lo":{"$f":"0.02499999999999999"},"hi":{"$f":"0.05500000000000001"},"marginal":false},"p90":{"lo":{"$f":"0.04899999999999998"},"hi":{"$f":"0.07000000000000002"},"marginal":false},"mean_signed":{"lo":{"$f":"-0.01750000000000003"},"hi":{"$f":"0.030833333333333327"},"marginal":false},"max_ape":{"lo":{"$f":"0.050000000000000024"},"hi":{"$f":"0.07000000000000002"},"marginal":false}}},"bins":{"below":{"n":4,"mean_signed":{"$f":"-0.0050000000000000305"},"n_failed":0},"between":{"n":4,"mean_signed":{"$f":"0.012500000000000015"},"n_failed":0},"at_or_above":{"n":4,"mean_signed":{"$f":"0.01249999999999998"},"n_failed":0}},"input_fragile":false,"property_fragile":false,"u_m_assumed":true,"worst_condition":"synthetic-c06","track_counts":[2,2,2,2,2,2,2,2,2,2,2,2],"marginal":[],"arms":{"C0":{"kind":"nominal","label":"synthetic C0","status":"DESCRIPTIVE_NOT_SCORED","reason":"powder layer block without a same-setup absorptance or a declared P5 bias (Amendment 6 item 6)","n":12,"median":{"$f":"0.30000000000000004"},"p75":{"$f":"0.3000000000000001"},"p90":{"$f":"0.3000000000000001"},"mean_signed":{"$f":"-0.30000000000000004"},"max_ape":{"$f":"0.3000000000000001"},"n_failed":0,"thresholds_met":{"median":false,"p90":true,"mean_signed":false,"max_ape":true},"unavailable_conditions":[]},"S1":{"kind":"nominal","label":"synthetic S1","status":"DESCRIPTIVE_NOT_SCORED","reason":"powder layer block without a same-setup absorptance or a declared P5 bias (Amendment 6 item 6)","n":12,"median":{"$f":"0.04000000000000002"},"p75":{"$f":"0.05250000000000001"},"p90":{"$f":"0.06"},"mean_signed":{"$f":"0.006666666666666654"},"max_ape":{"$f":"0.07000000000000002"},"n_failed":0,"thresholds_met":{"median":true,"p90":true,"mean_signed":true,"max_ape":true},"unavailable_conditions":[]},"S1|power:0.95":{"kind":"power","label":"synthetic S1|power:0.95","status":"DESCRIPTIVE_NOT_SCORED","reason":"powder layer block without a same-setup absorptance or a declared P5 bias (Amendment 6 item 6)","n":12,"median":{"$f":"0.19999999999999998"},"p75":{"$f":"0.19999999999999998"},"p90":{"$f":"0.2"},"mean_signed":{"$f":"-0.19999999999999996"},"max_ape":{"$f":"0.20000000000000004"},"n_failed":0,"thresholds_met":{"median":true,"p90":true,"mean_signed":false,"max_ape":true},"unavailable_conditions":[]}}}
"""
# --- END GOLDEN ---


def golden_vectors():
    out = {}
    for line in GOLDEN_VECTORS.strip("\n").split("\n"):
        if line:
            cid, value = line.split(" ", 1)
            out[cid] = value
    return out


def _same_env():
    import numpy
    import scipy
    return numpy.__version__ == GOLDEN_ENV.get("numpy") and scipy.__version__ == GOLDEN_ENV.get("scipy")


def _close(a, b):
    """Equality with floats at a relative 1e-12 (used only when numpy or scipy differ from GOLDEN_ENV)."""
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) == {"$f"} and set(b) == {"$f"}:
            x, y = float(a["$f"]), float(b["$f"])
            if x == y or (math.isnan(x) and math.isnan(y)):
                return True
            return math.isfinite(x) and math.isfinite(y) and abs(x - y) <= 1e-12 * max(abs(x), abs(y))
        return list(a) == list(b) and all(_close(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_close(x, y) for x, y in zip(a, b))
    return a == b


def _matches_golden(got, want, exact):
    return got == want if exact else _close(json.loads(got), json.loads(want))


# ----------------------------------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------------------------------
class GoldenVectorTests(unittest.TestCase):
    def test_every_case_has_a_golden_vector(self):
        ids = [c["id"] for c in build_cases()]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(sorted(ids), sorted(golden_vectors()))
        self.assertGreaterEqual(len(ids), 150)

    def test_extracted_functions_reproduce_the_original_vectors(self):
        golden, exact = golden_vectors(), _same_env()
        bad = [c["id"] for c in build_cases() if not _matches_golden(run_case(c, _ExtractedSide()), golden[c["id"]],
                                                                     exact)]
        self.assertEqual(bad, [], f"extracted output differs from the original runner (exact={exact})")

    def test_every_extracted_name_is_exercised(self):
        fns = {c["fn"] for c in build_cases()}
        uncovered = [n for n in PROV if n not in CONSTANT_NAMES and n not in fns
                     and n not in ("fragile_flips", "TargetColumnRequested")]
        self.assertEqual(uncovered, [])
        golden = golden_vectors()
        self.assertIn('"$raises":["TargetColumnRequested"', golden["no-target-loaded-1"])
        self.assertIn('"fragile":{"input":["S1|power:0.95","S1|beam:joint1"],"property":["S1|prop:synthetic_set"]}',
                      golden["score-pass-with-flips"])


class SourceIdentityTests(unittest.TestCase):
    def test_provenance_matches_module_and_golden(self):
        self.assertEqual(bs.PROVENANCE, PROV)
        self.assertEqual(set(PROV), set(GOLDEN_SOURCE_SHA256))
        for name in PROV:
            self.assertTrue(hasattr(bs, name), name)
        self.assertEqual(bs.SOURCE_BLOBS["M"][2], ORIGINAL_FILES[0][2])
        self.assertEqual(bs.SOURCE_BLOBS["P3"][2], ORIGINAL_FILES[3][2])
        doc = bs.__doc__
        for blob in (ORIGINAL_FILES[0][2], ORIGINAL_FILES[3][2]):
            self.assertIn(blob, doc)

    def test_every_extracted_segment_is_the_original_text(self):
        lines = MODULE_FILE.read_text(encoding="utf-8").split("\n")
        line_hashes = {hashlib.sha256((ln + "\n").encode("utf-8")).hexdigest() for ln in lines}
        for name, want in GOLDEN_SOURCE_SHA256.items():
            with self.subTest(name=name):
                if name in CONSTANT_NAMES:
                    self.assertIn(want, line_hashes)
                    continue
                src = inspect.getsource(getattr(bs, name))
                if name == "fragile_flips":
                    body = src.split("\n")
                    i = body.index(FRAGILE_FIRST_LINE)
                    a, b = PROV[name][1:]
                    src = "\n".join(body[i:i + b - a + 1]) + "\n"
                self.assertEqual(hashlib.sha256(src.encode("utf-8")).hexdigest(), want)


class RuleTests(unittest.TestCase):
    """Hand-derived checks of the rules the research hub spec (11.1 item 1) names, independent of the vectors."""

    def test_rank_quantile_infinity_rule(self):
        q = bs.rank_quantile_exact
        self.assertEqual(q([0.1, 0.2, INF], 1, 2), Fraction(1, 5))            # integer h on a finite value
        self.assertEqual(q([0.1, 0.2, 0.3, INF], 1, 2), Fraction(1, 4))       # finite neighbours interpolate
        self.assertEqual(q([0.1, 0.2, INF, INF], 1, 2), INF)                  # an infinite neighbour gives +inf
        self.assertEqual(q([0.1, INF], 1, 2), INF)
        self.assertEqual(q([INF, INF, INF], 1, 2), INF)
        self.assertTrue(math.isnan(q([], 1, 2)))
        self.assertEqual(q([0.4, 0.1, 0.3, 0.2], 9, 10), Fraction(37, 100))

    def test_threshold_boundaries_are_exact(self):
        for key, at, above in BOUNDARY_SETS:
            with self.subTest(statistic=key, values=at[:3]):
                self.assertTrue(bs.block_statistics(at)["all_thresholds_met"])
                met = bs.block_statistics(above)["thresholds_met"]
                self.assertFalse(met[key])
                self.assertTrue(all(v for k, v in met.items() if k != key))

    def test_mean_signed_over_finite_rows_and_max_ape_infinite(self):
        self.assertEqual(bs.mean_signed_exact([0.1, INF, -0.3]), Fraction(-1, 10))
        s = bs.block_statistics(TWELVE_REL[:11] + [INF])
        self.assertEqual((s["max_ape"], s["n_failed"], s["worst_index"]), (INF, 1, 11))
        self.assertFalse(s["thresholds_met"]["max_ape"])
        self.assertEqual(s["mean_signed"], float(bs.mean_signed_exact(TWELVE_REL[:11])))

    def test_bootstrap_is_deterministic(self):
        sig = inspect.signature(bs.bootstrap_intervals).parameters
        self.assertEqual((sig["B"].default, sig["seed"].default), (2000, 20261011))
        first = bs.bootstrap_intervals(TWELVE_REL)
        self.assertEqual(first, bs.bootstrap_intervals(TWELVE_REL))
        self.assertEqual(list(first), ["median", "p90", "mean_signed", "max_ape"])
        self.assertNotEqual(first, bs.bootstrap_intervals(TWELVE_REL, seed=1))
        self.assertEqual(bs.bootstrap_intervals([]), {})

    def test_cv_pool_minimums_and_not_evaluable(self):
        self.assertEqual(bs.cv_pool([[100.0, 104.0], [200.0, 190.0]]), (None, 2, 2))
        cvp, k, df = bs.cv_pool([[100.0, 104.0], [200.0, 190.0], [150.0, 151.0]])
        self.assertEqual((k, df), (3, 3))
        self.assertGreater(cvp, 0.0)
        res = bs.resolution_qualifier([{"track_depths": [150.0]}, {"track_depths": [200.0, 198.0]}], "bare_plate",
                                      False)
        self.assertEqual(res["status"], "not_evaluable")
        self.assertIsNone(res["median_U"])

    def test_u_m_floor_and_assumed_label(self):
        self.assertEqual(bs.u_m_default_um(100.0, "bare_plate", False), 5.0)
        self.assertEqual(bs.u_m_default_um(300.0, "bare_plate", False), max(5.0, 0.03 * 300.0))
        self.assertEqual(bs.u_m_default_um(100.0, "powder_layer", False), 10.0)
        self.assertEqual(bs.u_m_default_um(100.0, "bare_plate", True), 10.0)
        conds = [{"track_depths": [150.0, 151.0]}, {"track_depths": [200.0, 198.0]}]
        self.assertTrue(bs.resolution_qualifier(conds, "bare_plate", False)["u_m_assumed"])
        released = [dict(c, u_m_um=4.0) for c in conds]
        self.assertFalse(bs.resolution_qualifier(released, "bare_plate", False)["u_m_assumed"])
        with self.assertRaises(ValueError):
            bs.resolution_qualifier([dict(c, u_m_um=0.0) for c in conds], "bare_plate", False)

    def test_grade_tables(self):
        self.assertEqual(bs.beam_grade({"basis": "measured"}), "C")                     # unstated definition is C
        self.assertEqual(bs.beam_grade({"basis": "measured", "definition_stated": True}), "B")
        self.assertEqual(bs.beam_grade({"basis": "measured", "definition_stated": True, "work_plane": True,
                                        "released_uncertainty": True}), "A")
        self.assertEqual(bs.beam_grade({"basis": "nominal", "definition_stated": True}), "C")
        self.assertEqual(bs.power_grade({"basis": "commanded"}), "C")
        self.assertEqual(bs.power_grade({"basis": "measured"}), "B")
        self.assertEqual(bs.power_grade({"basis": "measured", "meter_named": True, "at_workpiece": True,
                                         "released_uncertainty": True}), "A")
        self.assertEqual(bs.block_grade("A", "C"), "C")
        self.assertEqual(bs.block_grade("B", "A"), "B")

    def test_reduction_refuses_repeated_rows_without_a_track_key(self):
        p = {"S1": 100.0}
        rows = [_row(2, "c1", None, None, p), _row(3, "c1", None, None, p)]
        depths = {2: {"depth_um": 100.0}, 3: {"depth_um": 101.0}}
        with self.assertRaises(ValueError):
            bs.reduce_conditions(rows, depths)
        conds = bs.reduce_conditions(rows, depths, rows_are_tracks=True)
        self.assertEqual((conds[0]["n_tracks"], conds[0]["D_obs_um"]), (2, 100.5))
        with self.assertRaises(ValueError):
            bs.reduce_conditions(rows[:1], {2: {"depth_um": 0.0}})

    def test_status_precedence_matrix(self):
        v = bs.block_verdict
        ok = dict(leverage_ok=True, resolution_status="met")
        matrix = (
            (v(TWELVE_REL, **ok, issues=["i"], exposed=True, scored=False), "EXPOSED_DESCRIPTIVE"),
            (v(TWELVE_REL, **ok, issues=["i"], scored=False), "DESCRIPTIVE_NOT_SCORED"),
            (v(FAIL12[:11], **ok), "INCONCLUSIVE"),
            (v(TWELVE_REL, **ok, issues=["i"]), "INCONCLUSIVE"),
            (v(FAIL12, **ok), "FAIL"),
            (v(FAIL12, leverage_ok=False, resolution_status="not_evaluable"), "FAIL"),
            (v(TWELVE_REL, leverage_ok=False, resolution_status="met"), "INCONCLUSIVE"),
            (v(TWELVE_REL, leverage_ok=True, resolution_status="not_met"), "INCONCLUSIVE"),
            (v(TWELVE_REL, leverage_ok=True, resolution_status="not_evaluable"), "INCONCLUSIVE"),
            (v(TWELVE_REL, **ok), "PASS"),
        )
        self.assertEqual([m["status"] for m, _ in matrix], [s for _, s in matrix])
        # An IN625 block (leverage not evaluable, passed as leverage_ok False): a threshold failure stays a failure,
        # all four met is inconclusive. The report layer maps FAIL to threshold-not-met.
        self.assertEqual(v(FAIL12, leverage_ok=False, resolution_status="met")["reason"],
                         "threshold failure: median, mean_signed")
        self.assertEqual(v(TWELVE_REL, leverage_ok=False, resolution_status="met")["reason"],
                         "all four thresholds met; qualifier not met: leverage")

    def test_fragile_flips(self):
        def arm(kind, status):
            return {"spec": {"kind": kind}, "verdict": {"status": status}}
        per_arm = {"S1": arm("nominal", "PASS"), "S1|power:0.95": arm("power", "FAIL"),
                   "S1|beam:joint0": arm("beam", "INCONCLUSIVE"), "S1|beam:A:0": arm("beam_single", "FAIL"),
                   "S1|prop:x": arm("property", "FAIL"), "S1|abs:lo": arm("absorptance", "PASS"),
                   "S1|prop:srv": arm("descriptive", "FAIL"), "S10|power:0.95": arm("power", "FAIL"),
                   "S1-srv": arm("power", "FAIL")}
        self.assertEqual(bs.fragile_flips(per_arm, "S1", "PASS"),
                         {"input": ["S1|power:0.95", "S1|beam:joint0"], "property": ["S1|prop:x"]})
        self.assertEqual(bs.fragile_flips(per_arm, "S1", "FAIL"), {"input": [], "property": []})
        self.assertEqual(bs.fragile_flips(per_arm, "S1", "INCONCLUSIVE"), {"input": [], "property": []})

    def test_score_scenarios(self):
        got = {name: _extracted_score(*build()) for name, build in SCENARIOS.items()}
        self.assertEqual(got["score-pass-with-flips"]["status"], "PASS")
        self.assertEqual(got["score-pass-with-flips"]["fragile"],
                         {"input": ["S1|power:0.95", "S1|beam:joint1"], "property": ["S1|prop:synthetic_set"]})
        self.assertEqual(got["score-pass-with-flips"]["arms"]["S1|power:1.05"]["unavailable_conditions"],
                         ["synthetic-c03"])
        self.assertEqual(got["score-fail-alsi"]["status"], "FAIL")
        self.assertEqual(got["score-fail-alsi"]["resolution"]["status"], "not_evaluable")
        self.assertEqual(got["score-fail-alsi"]["fragile"], {"input": [], "property": []})
        self.assertEqual(got["score-leverage-not-met"]["status"], "INCONCLUSIVE")
        self.assertFalse(got["score-leverage-not-met"]["leverage"]["ok"])
        self.assertEqual(got["score-exposed"]["status"], "EXPOSED_DESCRIPTIVE")
        self.assertEqual(got["score-small-with-issue"]["candidate"]["reason"], "n = 11 < 12; synthetic block issue")
        self.assertEqual(got["score-powder-not-scored"]["status"], "DESCRIPTIVE_NOT_SCORED")
        self.assertTrue(got["score-powder-not-scored"]["u_m_assumed"])

    def test_sign_flip_small_enumerations(self):
        e = bs.signflip_p_enumerate
        self.assertEqual((e([]), e([0.1]), e([-0.1]), e([0.1, 0.2]), e([0.2, -0.1])), (1.0, 0.5, 1.0, 0.25, 0.5))
        self.assertEqual(bs.signflip_p([0.1, 0.2, 0.0])["method"], "enumeration")
        self.assertEqual(bs.signflip_p(D25)["method"], "dp_rounded_down_and_up")
        with self.assertRaises(ValueError):
            e(D25)
        self.assertAlmostEqual(bs.signflip_p_dp([0.1, 0.2, -0.05])["p"], e([0.1, 0.2, -0.05]), places=12)
        self.assertEqual(bs.paired_differences([0.2, 0.3], [INF, 0.1], [True, False]), [-0.19999999999999998,
                                                                                       0.19999999999999998])

    def test_fwhm_factor_and_beam_conversion(self):
        self.assertEqual(bs.FWHM_FACTOR, math.sqrt(math.log(2.0) / 2.0))
        self.assertEqual(round(bs.FWHM_FACTOR, 6), 0.588705)
        self.assertEqual(bs.beam_d_um(80.0, "FWHM"), 80.0 / bs.FWHM_FACTOR)
        self.assertEqual(bs.beam_d_um(80, "unstated"), 80.0)
        with self.assertRaises(ValueError):
            bs.beam_d_um(40.0, "radius")

    def test_no_target_loaded_guard(self):
        amend = {"whitelist": {"targets": {"depth_um": "Depth (um)"}}}
        self.assertTrue(bs.assert_no_target_loaded(SimpleNamespace(columns_loaded=["P", "v"]), amend))
        with self.assertRaises(bs.TargetColumnRequested) as ctx:
            bs.assert_no_target_loaded(SimpleNamespace(columns_loaded=["P", "DEPTH (UM)"]), amend)
        self.assertIsInstance(ctx.exception, PermissionError)

    def test_served_index_is_the_served_call(self):
        import lpbf_public_datasets as pds
        self.assertIs(bs.pds, pds)
        row = {"P_W": 200.0, "v_mm_s": 1000.0, "d_um": 80.0}
        self.assertEqual(bs.served_index("Ti64", row, 293.15),
                         pds.normalized_enthalpy("Ti-6Al-4V", 200.0, 1000.0, 80.0, 293.15 - 273.15))
        self.assertEqual(bs.served_index("AlSi10Mg", row, 353.15),
                         pds.normalized_enthalpy("AlSi10Mg", 200.0, 1000.0, 80.0, 353.15 - 273.15))


class IsolationTests(unittest.TestCase):
    MANIFEST_SOURCE = PYTHON_DIR / "lpbf_simulation.py"
    SERVED_PATH = ("lpbf_build_job_solver.py", "lpbf_public_datasets.py", "lpbf_job_cache.py",
                   "lpbf_build_job_material_snapshot.py", "four_alloy_materials.py")

    def _manifest(self):
        tree = ast.parse(self.MANIFEST_SOURCE.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.Assign) and [getattr(t, "id", None) for t in node.targets] == [
                    "IMPLEMENTATION_SOURCE_FILES"]:
                return ast.literal_eval(node.value)
        raise AssertionError("IMPLEMENTATION_SOURCE_FILES not found")

    def test_outside_the_fingerprint_manifest(self):
        manifest = self._manifest()
        self.assertIn("lpbf_thermal_solver.py", manifest)
        self.assertNotIn("lpbf_blind_stats.py", manifest)
        self.assertFalse(any("blind" in f for f in manifest))

    def test_no_served_module_imports_it(self):
        files = [f for f in self._manifest() if f.endswith(".py")] + list(self.SERVED_PATH)
        checked = 0
        for name in files:
            path = PYTHON_DIR / name
            if not path.exists():
                continue
            checked += 1
            self.assertNotIn("lpbf_blind_stats", path.read_text(encoding="utf-8"), name)
        self.assertGreater(checked, 20)

    def test_imports_and_calls(self):
        tree = ast.parse(MODULE_FILE.read_text(encoding="utf-8"))
        mods = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                mods.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                mods.add(node.module)
        self.assertEqual(mods, {"__future__", "math", "statistics", "fractions", "numpy", "lpbf_public_datasets",
                                "scipy.stats"})
        calls = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        self.assertFalse(calls & {"open", "exec", "eval", "__import__", "compile"})
        text = MODULE_FILE.read_text(encoding="utf-8")
        self.assertFalse(any(m.startswith("lpbf_research") for m in mods))
        for needle in ("lpbf-research-models", "/api/python/", "subprocess", "sys.path"):
            self.assertNotIn(needle, text)

    def test_import_loads_no_solver(self):
        code = ("import sys, lpbf_blind_stats; print(sorted(m for m in sys.modules if m.startswith(('lpbf', 'four_', "
                "'run_', 'p3_', 'eagar', 'fabbro', 'warp', 'powder'))))")
        res = subprocess.run([sys.executable, "-B", "-c", code], cwd=str(PYTHON_DIR), capture_output=True, text=True,
                             timeout=120)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(res.stdout.strip(), "['lpbf_blind_stats', 'lpbf_public_datasets']")


class LiveOriginalTests(unittest.TestCase):
    def test_original_runner_reproduces_extracted_outputs(self):
        try:
            data = run_original_child()
        except OriginalUnavailable as exc:
            if os.environ.get("CI"):
                # The research commits are not on the public remote. The embedded vectors and source hashes, asserted
                # by GoldenVectorTests and SourceIdentityTests, are the guard; assert them here too instead of skipping.
                golden, exact = golden_vectors(), _same_env()
                self.assertTrue(all(_matches_golden(run_case(c, _ExtractedSide()), golden[c["id"]], exact)
                                    for c in build_cases()))
                return
            self.skipTest(f"original runner not available ({exc}); the embedded golden vectors are the guard")
        self.assertEqual(data["source_sha256"], GOLDEN_SOURCE_SHA256)
        extracted = {c["id"]: run_case(c, _ExtractedSide()) for c in build_cases()}
        original = dict(data["vectors"])
        self.assertEqual(sorted(original), sorted(extracted))
        self.assertEqual([k for k in extracted if extracted[k] != original[k]], [])
        golden, exact = golden_vectors(), data["env"]["numpy"] == GOLDEN_ENV.get("numpy") and \
            data["env"]["scipy"] == GOLDEN_ENV.get("scipy")
        self.assertEqual([k for k in original if not _matches_golden(original[k], golden[k], exact)], [])


if __name__ == "__main__":
    if CHILD_MODE:
        _child_main(sys.argv[2], sys.argv[3])
    elif len(sys.argv) > 1 and sys.argv[1] == "--write-golden":
        _write_golden()
    else:
        unittest.main()
