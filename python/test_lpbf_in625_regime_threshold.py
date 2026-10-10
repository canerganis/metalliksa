"""Pins the IN625 regime-threshold harness on SYNTHETIC fixtures (own rows, own numbers).

Nothing here evaluates the real held-out split: the real ledger is only checked as a transcription (hash, counts,
label-blind split). Every geometry used for fitting or scoring below is synthetic. SCREENING ONLY, NOT VALIDATION.
Run from python/ with the locked interpreter:
    python -B -m unittest test_lpbf_in625_regime_threshold
"""

import copy
import io
import math
import sys
import unittest
from pathlib import Path
from unittest import mock

PYTHON_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PYTHON_DIR))
sys.path.insert(0, str(PYTHON_DIR / "tools"))

import lpbf_in625_regime_threshold as E  # noqa: E402


def _u(h, y, split="fit", uid=None):
    """Abstract synthetic unit: index h and label y are read through injected functions."""
    return {"unit_id": uid or f"syn-{h}", "split": split, "h": float(h), "y": bool(y)}


H = lambda u: u["h"]  # noqa: E731
Y = lambda u: u["y"]  # noqa: E731


def _geom(uid, split, power, speed, d4, width, depth, machine="EOS M270", source=E.MDS2_SOURCE_ID):
    """Synthetic ledger row with the real column set (made-up geometry)."""
    return {"unit_id": uid, "source": source, "campaign": "synthetic", "machine": machine,
            "machine_family": E.machine_family(machine), "power_W": float(power), "speed_mm_s": float(speed),
            "d4sigma_um": float(d4), "beam_diameter_source": "synthetic", "n_measurements": "2",
            "width_um": float(width), "depth_um": float(depth), "width_U_um": 5.0, "depth_U_um": 5.0,
            "uncertainty_kind": "synthetic", "split": split, "split_reason": "synthetic", "locator": "synthetic"}


def _synthetic_ledger():
    """Fit: keyhole iff D4sigma small (deep pools). Held-out: a mix. All numbers invented."""
    rows = []
    for i, d4 in enumerate((60, 70, 80, 90, 100, 110)):
        rows.append(_geom(f"fit-k{i}", "fit", 195, 800, d4, 120, 90 + 10 * (6 - i)))   # depth/(w/2) > 1
    for i, d4 in enumerate((130, 150, 170, 190, 210, 230, 250)):
        rows.append(_geom(f"fit-c{i}", "fit", 195, 800, d4, 150, 40))                 # depth/(w/2) < 1
    for i, d4 in enumerate((55, 75, 95)):
        rows.append(_geom(f"ho-k{i}", "heldout", 195, 800, d4, 110, 120, machine="AMMT"))
    for i, d4 in enumerate((140, 180, 220, 260)):
        rows.append(_geom(f"ho-c{i}", "heldout", 195, 800, d4, 140, 35, machine="AMMT"))
    rows.append(_geom("excl", "excluded", 195, 800, 100, 130, 90))
    return rows


class FitRule(unittest.TestCase):
    def test_separable_midpoint(self):
        units = [_u(h, False) for h in (5, 8, 11)] + [_u(h, True) for h in (14, 19, 25)]
        fit = E.fit_threshold(units, H, Y)
        self.assertAlmostEqual(fit["threshold"], 12.5)
        self.assertEqual(fit["fitBalancedAccuracy"], 1.0)
        self.assertEqual((fit["nFitKeyhole"], fit["nFitNotKeyhole"]), (3, 3))

    def test_overlap_matches_brute_force(self):
        hs = [3, 6, 9, 10, 12, 13, 15, 18, 21, 30]
        ys = [0, 0, 1, 0, 0, 1, 1, 0, 1, 1]
        units = [_u(h, y) for h, y in zip(hs, ys)]
        fit = E.fit_threshold(units, H, Y)
        grid = [0.5 * (a + b) for a, b in zip(hs[:-1], hs[1:])]
        best = max(E.confusion(hs, [bool(y) for y in ys], c)["balancedAccuracy"] for c in grid)
        self.assertAlmostEqual(fit["fitBalancedAccuracy"], best)
        self.assertAlmostEqual(fit["threshold"], 12.5)  # BA 0.8 at 12.5 and 16.5 is lower; brute force pins it

    def test_tie_break_widest_gap_then_lower(self):
        # Two perfect cuts are impossible; build equal-BA candidates: labels N K N K with gaps 2 and 6.
        units = [_u(10, False), _u(12, True), _u(18, False), _u(24, True)]
        fit = E.fit_threshold(units, H, Y)
        # candidates 11 (BA .75), 15 (BA .5), 21 (BA .75): equal BA, gaps 2 and 6 -> 21
        self.assertAlmostEqual(fit["threshold"], 21.0)
        units = [_u(10, False), _u(14, True), _u(18, False), _u(22, True)]
        fit = E.fit_threshold(units, H, Y)
        self.assertAlmostEqual(fit["threshold"], 12.0)  # equal BA and equal gap -> lower
        self.assertEqual(fit["nTiedMaxBA"], 2)

    def test_rejects_non_fit_units(self):
        units = [_u(5, False), _u(20, True), _u(30, True, split="heldout")]
        with self.assertRaises(ValueError):
            E.fit_threshold(units, H, Y)

    def test_degenerate(self):
        with self.assertRaises(E.DegenerateFit):
            E.fit_threshold([_u(5, False), _u(9, False)], H, Y)
        with self.assertRaises(E.DegenerateFit):
            E.fit_threshold([_u(5, False), _u(5, True)], H, Y)

    def test_adoption_rounding_and_loo(self):
        self.assertEqual(E.adopted(13.249), 13.2)
        units = [_u(h, False) for h in (5, 8, 11)] + [_u(h, True) for h in (14, 19, 25)]
        loo = E.leave_one_out_thresholds(units, H, Y)
        self.assertEqual(len(loo), 6)
        self.assertEqual(loo[2], 11.0)  # drop 11 -> midpoint of 8 and 14
        self.assertEqual(loo[3], 15.0)  # drop 14 -> midpoint of 11 and 19


class HeldoutIsolation(unittest.TestCase):
    """Held-out geometry and labels never reach the threshold choice."""

    def test_scrambling_heldout_geometry_leaves_threshold_unchanged(self):
        ledger = _synthetic_ledger()
        a = E.analyse(ledger)
        scrambled = copy.deepcopy(ledger)
        for u in scrambled:
            if u["split"] != "fit":
                u["depth_um"], u["width_um"] = u["width_um"] * 3.0, u["depth_um"] / 3.0  # flips every label
        b = E.analyse(scrambled)
        self.assertEqual(a["fit"], b["fit"])
        self.assertEqual(a["adoptedThreshold"], b["adoptedThreshold"])
        self.assertEqual(a["looThresholds"], b["looThresholds"])
        self.assertEqual(a["sensitivities"]["preheat27C"]["threshold"], b["sensitivities"]["preheat27C"]["threshold"])
        # ...while the held-out score does change, so the scramble really reached the scored labels.
        self.assertNotEqual(a["arms"]["F_fitted"]["balancedAccuracy"], b["arms"]["F_fitted"]["balancedAccuracy"])

    def test_no_heldout_label_is_read_before_the_fit_returns(self):
        events = []
        real_truth, real_fit = E.truth_keyhole, E.fit_threshold

        def spy_truth(u):
            events.append(("label", u["split"]))
            return real_truth(u)

        def spy_fit(*args, **kwargs):
            out = real_fit(*args, **kwargs)
            events.append(("fit-done", None))
            return out

        with mock.patch.object(E, "truth_keyhole", spy_truth), mock.patch.object(E, "fit_threshold", spy_fit):
            E.analyse(_synthetic_ledger())
        first_fit_done = events.index(("fit-done", None))
        before = [s for kind, s in events[:first_fit_done] if kind == "label"]
        self.assertTrue(before)
        self.assertTrue(all(s == "fit" for s in before), before)

    def test_excluded_units_never_fitted_or_scored(self):
        ledger = _synthetic_ledger()
        a = E.analyse(ledger)
        b = E.analyse([u for u in ledger if u["split"] != "excluded"])
        self.assertEqual(a["fit"], b["fit"])
        self.assertEqual(a["arms"], b["arms"])
        self.assertEqual(a["counts"]["excluded"], 1)


class AdmissibleInterval(unittest.TestCase):
    """Amendment B1: the held-out-admissible interval is every cut with the same held-out confusion as T_F."""

    hs = [4.0, 7.5, 9.0, 12.0, 12.0, 14.0, 17.0, 23.0]
    ys = [False, False, False, False, True, True, True, True]

    def _units(self):
        return [_u(h, y, split="heldout", uid=f"ho{i}") for i, (h, y) in enumerate(zip(self.hs, self.ys))]

    def test_interval_brackets_and_matches_brute_force(self):
        iv = E.heldout_admissible_interval(self._units(), 13.0, H)
        self.assertEqual((iv["lowerExclusive"], iv["upperInclusive"]), (12.0, 14.0))
        self.assertEqual(iv["upperUnit"], "ho5")
        ref = E.confusion(self.hs, self.ys, 13.0)
        same = lambda c: {k: v for k, v in E.confusion(self.hs, self.ys, c).items() if k != "threshold"} == \
            {k: v for k, v in ref.items() if k != "threshold"}  # noqa: E731
        for c in (12.0001, 12.5, 13.9, 14.0):
            self.assertTrue(same(c), c)
        for c in (12.0, 11.9, 14.0001, 16.0):
            self.assertFalse(same(c), c)

    def test_cut_on_a_unit_and_ties(self):
        iv = E.heldout_admissible_interval(self._units(), 12.0, H)  # both 12.0 units are called keyhole
        self.assertEqual((iv["lowerExclusive"], iv["upperInclusive"]), (9.0, 12.0))

    def test_unbounded_sides(self):
        iv = E.heldout_admissible_interval(self._units(), 2.0, H)
        self.assertIsNone(iv["lowerExclusive"])
        self.assertEqual(iv["upperInclusive"], 4.0)
        iv = E.heldout_admissible_interval(self._units(), 30.0, H)
        self.assertEqual(iv["lowerExclusive"], 23.0)
        self.assertIsNone(iv["upperInclusive"])
        self.assertIn("-inf", E.licensed_claim(E.heldout_admissible_interval(self._units(), 2.0, H), 2.0))

    def test_reads_no_label(self):
        units = [{"unit_id": f"x{i}", "split": "heldout", "h": h} for i, h in enumerate(self.hs)]
        iv = E.heldout_admissible_interval(units, 13.0, H)
        self.assertEqual((iv["lowerExclusive"], iv["upperInclusive"]), (12.0, 14.0))

    def test_analyse_reports_interval_and_claim(self):
        a = E.analyse(_synthetic_ledger())
        iv = a["heldoutAdmissibleInterval"]
        self.assertEqual(iv["threshold"], a["adoptedThreshold"])
        self.assertEqual(iv["nHeldout"], a["counts"]["heldout"])
        lo, hi = iv["lowerExclusive"], iv["upperInclusive"]
        self.assertTrue((lo is None or lo < a["adoptedThreshold"]) and (hi is None or a["adoptedThreshold"] <= hi))
        self.assertIn("fit-split point estimate", a["licensedClaimIfPass"])
        self.assertIn("not a held-out-validated value", a["licensedClaimIfPass"])


class SplitRule(unittest.TestCase):
    def test_split_ignores_geometry(self):
        key = E.condition_key("EOS M270", 195, 800, 100)
        held = [E.condition_key("EOS M270 (CBM)", 195, 800, 100)]
        self.assertEqual(E.assign_split(E.MDS2_SOURCE_ID, "EOS M270", key, held)[0], "excluded")
        self.assertEqual(E.assign_split(E.MDS2_SOURCE_ID, "EOS M270", E.condition_key("EOS M270", 195, 800, 101), held)[0],
                         "fit")
        self.assertEqual(E.assign_split(E.MDS2_SOURCE_ID, "AMMT", key, held)[0], "heldout")
        self.assertEqual(E.assign_split(E.LANE_SOURCE_ID, "AMMT", key, held)[0], "heldout")
        with self.assertRaises(ValueError):
            E.assign_split("other", "AMMT", key, held)

    def test_committed_ledger_is_the_transcription(self):
        rows = E.build_ledger_rows()
        text = E.ledger_csv_text(rows)
        self.assertEqual(text.encode("utf-8"), E.LEDGER_CSV.read_bytes())
        self.assertEqual(E._sha256_file(E.LEDGER_CSV), E.LEDGER_SHA256)
        ledger = E.load_ledger(verify=True)
        counts = {s: sum(1 for u in ledger if u["split"] == s) for s in ("fit", "heldout", "excluded")}
        self.assertEqual(counts, {"fit": 56, "heldout": 13, "excluded": 1})
        excluded = [u for u in ledger if u["split"] == "excluded"][0]
        # the workbook stores this spot as 100.00000000000001; condition keys round to 0.1 um
        self.assertEqual(E.condition_key(excluded["machine"], excluded["power_W"], excluded["speed_mm_s"],
                                         excluded["d4sigma_um"]), ("EOS M270", 195.0, 800.0, 100.0))
        self.assertTrue(all(u["machine_family"] == "EOS M270" for u in ledger if u["split"] == "fit"))

    def test_split_is_unchanged_when_ledger_geometry_is_perturbed(self):
        rows = E.build_ledger_rows()
        held_keys = [E.condition_key(u["machine"], float(u["power_W"]), float(u["speed_mm_s"]), float(u["d4sigma_um"]))
                     for u in rows if u["source"] == E.LANE_SOURCE_ID]
        for u in rows:
            key = E.condition_key(u["machine"], float(u["power_W"]), float(u["speed_mm_s"]), float(u["d4sigma_um"]))
            self.assertEqual(E.assign_split(u["source"], u["machine"], key, held_keys)[0], u["split"])


class ConventionAndTruth(unittest.TestCase):
    def test_weaver_factor_pinned(self):
        self.assertAlmostEqual(E.repo_per_weaver_factor(), 0.724291, places=5)
        self.assertAlmostEqual(E.WEAVER_THRESHOLD * E.repo_per_weaver_factor(), 21.7287, places=3)

    def test_weaver_index_ratio_equals_factor(self):
        for p, v, d in ((150, 400, 100), (195, 800, 167), (122, 200, 322)):
            u = {"power_W": p, "speed_mm_s": v, "d4sigma_um": d}
            self.assertAlmostEqual(E.repo_index(u) / E.weaver_index(u), E.repo_per_weaver_factor(), places=9)

    def test_app_index_pins(self):
        cbm_a = {"power_W": 150, "speed_mm_s": 400, "d4sigma_um": 100}
        self.assertAlmostEqual(E.repo_index(cbm_a), 18.5689, places=3)
        self.assertAlmostEqual(E.repo_index(cbm_a, preheat_C=80.0), 19.4462, places=3)  # the brief's 19.45 is 80 C

    def test_truth_is_strict(self):
        self.assertFalse(E.truth_keyhole({"depth_um": 50.0, "width_um": 100.0}))
        self.assertTrue(E.truth_keyhole({"depth_um": 50.01, "width_um": 100.0}))
        self.assertFalse(E.truth_keyhole_secondary({"depth_um": 50.0, "d4sigma_um": 100.0}))
        self.assertTrue(E.truth_keyhole_secondary({"depth_um": 60.0, "d4sigma_um": 100.0}))

    def test_ambiguity(self):
        base = {"depth_um": 52.0, "width_um": 100.0, "depth_U_um": 5.0, "width_U_um": 2.0}
        self.assertTrue(E.is_ambiguous(base))
        far = dict(base, depth_um=80.0)
        self.assertFalse(E.is_ambiguous(far))


def _conf(tp, fn, tn, fp):
    pos, neg = tp + fn, tn + fp
    return {"tp": tp, "fn": fn, "tn": tn, "fp": fp, "errors": fn + fp,
            "balancedAccuracy": 0.5 * (tp / pos + tn / neg) if pos and neg else None}


class PassRule(unittest.TestCase):
    good_loo = [0.9] * 10

    def test_clear_improvement_passes(self):
        v = E.evaluate_pass(_conf(5, 0, 8, 0), _conf(2, 3, 8, 0), _conf(5, 0, 8, 0), _conf(2, 3, 8, 0),
                            self.good_loo, 20, 30)
        self.assertEqual(v["verdict"], "PASS", v)

    def test_trivial_classifiers_fail(self):
        always = _conf(5, 0, 0, 8)   # calls everything keyhole
        never = _conf(0, 5, 8, 0)
        base = _conf(2, 3, 8, 0)
        for cand in (always, never):
            v = E.evaluate_pass(cand, base, cand, base, self.good_loo, 20, 30)
            self.assertEqual(v["verdict"], "FAIL")
            self.assertFalse(v["items"]["P1_min_ba"])

    def test_small_gain_fails(self):
        v = E.evaluate_pass(_conf(4, 1, 8, 0), _conf(3, 2, 8, 0), _conf(4, 1, 8, 0), _conf(3, 2, 8, 0),
                            self.good_loo, 20, 30)
        self.assertEqual(v["verdict"], "FAIL")
        self.assertFalse(v["items"]["P3_error_reduction"])

    def test_good_baseline_cannot_be_beaten(self):
        v = E.evaluate_pass(_conf(5, 0, 8, 0), _conf(5, 0, 7, 1), _conf(5, 0, 8, 0), _conf(5, 0, 7, 1),
                            self.good_loo, 20, 30)
        self.assertEqual(v["verdict"], "FAIL")

    def test_secondary_truth_and_loo_items(self):
        v = E.evaluate_pass(_conf(5, 0, 8, 0), _conf(2, 3, 8, 0), _conf(2, 3, 8, 0), _conf(5, 0, 8, 0),
                            self.good_loo, 20, 30)
        self.assertFalse(v["items"]["P5_secondary_truth_not_worse"])
        v = E.evaluate_pass(_conf(5, 0, 8, 0), _conf(2, 3, 8, 0), _conf(5, 0, 8, 0), _conf(2, 3, 8, 0),
                            [0.9, 0.7], 20, 30)
        self.assertFalse(v["items"]["P6_loo_robust"])
        v = E.evaluate_pass(_conf(5, 0, 8, 0), _conf(2, 3, 8, 0), _conf(5, 0, 8, 0), _conf(2, 3, 8, 0),
                            [0.9, None], 20, 30)
        self.assertFalse(v["items"]["P6_loo_robust"])

    def test_inconclusive_when_a_class_is_thin(self):
        v = E.evaluate_pass(_conf(2, 0, 8, 0), _conf(0, 2, 8, 0), _conf(2, 0, 8, 0), _conf(0, 2, 8, 0),
                            self.good_loo, 20, 30)
        self.assertEqual(v["verdict"], "INCONCLUSIVE")
        v = E.evaluate_pass(_conf(5, 0, 8, 0), _conf(2, 3, 8, 0), _conf(5, 0, 8, 0), _conf(2, 3, 8, 0),
                            self.good_loo, 4, 30)
        self.assertEqual(v["verdict"], "INCONCLUSIVE")


class RunGuard(unittest.TestCase):
    def test_run_needs_the_declared_flag(self):
        with self.assertRaises(SystemExit):
            E.main(["run"])

    def test_baseline_matches_solver(self):
        import lpbf_thermal_solver as solver
        self.assertEqual(solver.ENTHALPY_KEYHOLE, E.BASELINE_KEYHOLE_CUT)
        self.assertEqual(solver.ENTHALPY_TRANSITION, E.BASELINE_TRANSITION_CUT)


if __name__ == "__main__":
    unittest.main()
