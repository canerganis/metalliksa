"""Pins the regime-absorptivity evaluation harness on a tiny SYNTHETIC fixture (own rows, pinned numbers).

The fixture rows are synthetic and carry real source ids only so the harness roles apply; none of the numbers here is a
dataset result. SCREENING ONLY, NOT VALIDATION."""

import math
import sys
import unittest
from pathlib import Path

import numpy as np

PYTHON_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PYTHON_DIR))
sys.path.insert(0, str(PYTHON_DIR / "tools"))

import lpbf_calibration_stats as st  # noqa: E402

st.pin_flat_plate()
import lpbf_regime_absorptivity_eval as E  # noqa: E402
import lpbf_regime_absorptivity_kernel as K  # noqa: E402
import lpbf_thermal_solver as ts  # noqa: E402

A0 = E.ARM_LAW["A0"]

# Served meltPoolGeometry (width_um, depth_um, extentStatus) recorded at the pre-P1 revision 393cdbd1 (fingerprint
# 0d52d7f7) with the locked interpreter, before the P1 planned bump of 2026-10-11 edited the solver. Self-contained pin
# of the frozen pre-P1 baseline that lpbf_regime_absorptivity_kernel keeps reproducing.
PRE_P1_SERVED = {
    (("316L Stainless Steel", 300.0, 800.0, 80.0, 20.0, 30.0, 100.0), "eagar-tsai"): (148.4, 111.7, "computed"),
    (("316L Stainless Steel", 300.0, 800.0, 80.0, 20.0, 30.0, 100.0), "goldak"): (142.4, 111.7, "computed"),
    (("316L Stainless Steel", 300.0, 800.0, 80.0, 20.0, 30.0, 100.0), "rosenthal"): (192.5, 152.8, "computed"),
    (("Ti-6Al-4V", 150.0, 1200.0, 95.0, 20.0, 30.0, 100.0), "eagar-tsai"): (109.4, 37.9, "computed"),
    (("Ti-6Al-4V", 150.0, 1200.0, 95.0, 20.0, 30.0, 100.0), "goldak"): (88.3, 44.4, "computed"),
    (("Ti-6Al-4V", 150.0, 1200.0, 95.0, 20.0, 30.0, 100.0), "rosenthal"): (82.0, 39.6, "computed"),
}


class LawAndParity(unittest.TestCase):
    def test_law_properties(self):
        f = lambda H: K.absorptivity_law(H, 0.42, 0.70, 15.0, 5.0)
        self.assertEqual(f(10.0), 0.42)
        self.assertEqual(f(15.0), 0.42)
        self.assertAlmostEqual(f(20.0), 0.70 - 0.28 * math.exp(-1.0), places=12)
        self.assertAlmostEqual(f(20.0), 0.5970, places=4)
        self.assertLess(f(1000.0), 0.70 + 1e-12)
        self.assertTrue(all(f(h) <= f(h + 1) for h in range(0, 60)))
        self.assertEqual(K.absorptivity_law(30.0, 0.75, 0.70, 15.0, 5.0), 0.75)  # A_flat >= A_kh

    def test_baseline_mode_reproduces_the_frozen_function(self):
        # The kernel is frozen as the PRE-P1 served path (P1 planned bump 2026-10-11): the reference is a self-contained
        # fixture of calculate_meltpool_physics outputs recorded at 393cdbd1 / pin 0d52d7f7 (width_um, depth_um,
        # extentStatus), not a live call. The live solver differs from it on purpose after P1 (Rosenthal rows).
        for (args, k), ref in PRE_P1_SERVED.items():
            mine = K.meltpool_wd(*args, kernel=k)
            self.assertEqual((mine["W_um"], mine["D_um"], mine["status"]), ref, (args, k))

    def test_baseline_differs_from_the_live_solver_after_p1(self):
        args = ("316L Stainless Steel", 300.0, 800.0, 80.0, 20.0, 30.0, 100.0)
        mine = K.meltpool_wd(*args, kernel="rosenthal")
        live = ts.calculate_meltpool_physics(*args, heat_source="rosenthal", absorption_model="flat-plate")["meltPoolGeometry"]
        self.assertEqual((mine["W_um"], mine["D_um"]), PRE_P1_SERVED[(args, "rosenthal")][:2])
        self.assertNotEqual((mine["W_um"], mine["D_um"]), (live["width_um"], live["depth_um"]))
        self.assertEqual(live["width_um"], 142.2)  # A P field, no ramp, no latent factor (P1 tree)
        self.assertEqual(K.PRE_P1_KEYHOLE_INCREMENT_FULL_AT, 30.0)
        self.assertFalse(hasattr(ts, "KEYHOLE_INCREMENT_FULL_AT"))

    def test_candidate_pinned_numbers(self):
        args = ("316L Stainless Steel", 300.0, 800.0, 80.0, 20.0, 30.0, 100.0)
        base = K.meltpool_wd(*args, kernel="eagar-tsai")
        cand = K.meltpool_wd(*args, kernel="eagar-tsai", policy=A0)
        self.assertEqual((base["W_um"], base["D_um"]), (148.4, 111.7))
        self.assertGreater(base["H"], 15.0)
        self.assertGreater(cand["A_cond"], 0.42)
        self.assertGreaterEqual(cand["W_um"], base["W_um"])
        self.assertAlmostEqual(cand["A_cond"], K.absorptivity_law(base["H"], 0.42, 0.7, 15.0, 5.0), places=12)


class Statistics(unittest.TestCase):
    def test_skill_matches_paired_skill_and_counts_undefined(self):
        rng = np.random.default_rng(3)
        meas = rng.uniform(100, 200, 24)
        base = meas * rng.uniform(0.6, 1.4, 24)
        cand = meas * rng.uniform(0.8, 1.2, 24)
        cl = np.array([f"c{i // 2}" for i in range(24)])
        ref = st.paired_skill(cand, base, meas, np.ones(24, bool), cl, 1000, 0)
        mine = E.skill_stats(np.abs(cand - meas) / meas, np.abs(base - meas) / meas, cl)
        self.assertAlmostEqual(mine["skill"], ref["skill"], places=12)
        self.assertEqual(mine["ci95"], ref["ci95"])
        self.assertEqual(mine["undefined"], 0)
        zero = E.skill_stats(np.array([0.1, 0.2, 0.1]), np.zeros(3), np.array(["a", "b", "c"]))
        self.assertIsNone(zero["skill"])
        self.assertFalse(zero["ciEvaluable"])

    def test_pooled_skill_point_estimate_and_determinism(self):
        a1, b1 = np.array([0.1, 0.1, 0.1, 0.1]), np.array([0.2, 0.2, 0.2, 0.2])
        a2, b2 = np.array([0.3, 0.3, 0.3]), np.array([0.3, 0.3, 0.3])
        parts = {"s2": (a2, b2, np.array(["x", "y", "z"])), "s1": (a1, b1, np.array(["a", "b", "c", "d"]))}
        r = E.pooled_skill(parts)
        self.assertAlmostEqual(r["skill"], 1.0 - (0.1 + 0.3) / (0.2 + 0.3), places=12)
        self.assertEqual(r["sources"], ["s1", "s2"])
        self.assertEqual(r, E.pooled_skill(parts))

    def test_pi_params_and_interval_score_hand_values(self):
        pp = E.pi_params({"a": np.array([0.1, 0.3]), "b": np.array([-0.1, 0.1])})
        self.assertTrue(pp["defined"])
        self.assertTrue(pp["sbFlag"])
        self.assertAlmostEqual(pp["mu"], 0.1, places=12)
        self.assertAlmostEqual(pp["sigma"], math.sqrt(0.02), places=12)  # var 0.02 each, two sources: s_b = 0
        self.assertFalse(E.pi_params({"a": np.array([0.1, 0.2])})["defined"])
        self.assertFalse(E.pi_params({"a": np.array([0.1]), "b": np.array([0.2])})["defined"])
        self.assertFalse(E.pi_params({"a": np.array([0.1, 0.1]), "b": np.array([0.1, 0.1])})["defined"])  # sigma 0
        meas = np.array([100.0, 100.0])
        pred = np.array([100.0, 100.0])
        out = E.interval_stats(meas, pred, np.array([True, True]), 0.0, 0.1)
        self.assertEqual(out["k"], 2)
        self.assertAlmostEqual(out["meanIntervalScore"], 2 * E.Z90 * 0.1, places=12)
        miss = E.interval_stats(np.array([100.0]), np.array([50.0]), np.array([True]), 0.0, 0.1)
        lo, hi = math.log(50.0) - E.Z90 * 0.1, math.log(50.0) + E.Z90 * 0.1
        self.assertEqual(miss["k"], 0)
        self.assertAlmostEqual(miss["meanIntervalScore"], (hi - lo) + 20.0 * (math.log(100.0) - hi), places=9)
        unres = E.interval_stats(np.array([100.0, 100.0]), np.array([100.0, np.nan]), np.array([True, False]), 0.0, 0.1)
        self.assertEqual((unres["k"], unres["n"], unres["nIntervalScore"], unres["nUnresolved"]), (1, 2, 1, 1))

    def test_verdict_order_and_overall_rule(self):
        ok = {"evaluable": True, "pass": True}
        bad = {"evaluable": True, "pass": False}
        ne = {"evaluable": False, "pass": False}
        base = {"C1": ok, "C2": ok, "C3": ok, "C4": ok, "C5": ok, "C6": ok}
        self.assertEqual(E.kernel_verdict(base), "PASS")
        self.assertEqual(E.kernel_verdict({**base, "C5": ne}), "INCONCLUSIVE")
        self.assertEqual(E.kernel_verdict({**base, "C5": ne, "C1": bad}), "FAIL")  # FAIL precedes not-evaluable
        self.assertEqual(E.kernel_verdict({**base, "C6": bad}), "FAIL")
        self.assertEqual(E.kernel_verdict({**base, "early": "INCONCLUSIVE", "C1": bad}), "INCONCLUSIVE")
        v = lambda a, b, c: {"eagar-tsai": {"g1": a, "g2": a}, "goldak": {"g1": b, "g2": b}, "rosenthal": {"g1": c, "g2": c}}
        self.assertEqual(E.overall_decision(v("PASS", "PASS", "PASS"), False)["result"], "PASS")
        self.assertEqual(E.overall_decision(v("PASS", "FAIL", "PASS"), False)["result"], "FAIL (mixed)")
        self.assertEqual(E.overall_decision(v("FAIL", "FAIL", "FAIL"), False)["result"], "FAIL")
        self.assertEqual(E.overall_decision(v("PASS", "INCONCLUSIVE", "PASS"), False)["result"], "INCONCLUSIVE")
        split = {"eagar-tsai": {"g1": "PASS", "g2": "FAIL"}, "goldak": {"g1": "FAIL", "g2": "FAIL"},
                 "rosenthal": {"g1": "FAIL", "g2": "FAIL"}}
        self.assertEqual(E.overall_decision(split, False)["result"], "INCONCLUSIVE")
        self.assertEqual(E.overall_decision(v("PASS", "PASS", "PASS"), True)["result"], "INVALID")


def _fixture_raws(mode: str):
    """Synthetic raw rows. mode 'near_a0': measured = candidate prediction x a fixed wobble; 'near_base': measured =
    baseline prediction x the same wobble."""
    policy = A0 if mode == "near_a0" else None
    specs = [("hofmann-316l-2026", "316L Stainless Steel", None, 30.0, 80.0),
             ("totis-ti64-2021", "Ti-6Al-4V", None, 25.0, 50.0),
             ("ku-leuven-316l-2021", "316L Stainless Steel", "kuBeam", 60.0, 37.5),
             ("ku-leuven-ti64-2021", "Ti-6Al-4V", "kuBeam", 60.0, 37.5)]
    raws = []
    for si, (sid, mat, axis, layer, beam) in enumerate(specs):
        for i in range(7):
            P = 150.0 + 75.0 * i
            v = 800.0 + 40.0 * si
            ref = K.meltpool_wd(mat, P, v, beam, 20.0, layer if layer > 0 else 30.0, 100.0, "eagar-tsai", policy)
            wob = 1.0 + 0.03 * ((i % 5) - 2)
            variants = {"base": (P, v, beam)} if axis is None else {"37.5": (P, v, 37.5), "75": (P, v, 75.0)}
            label = None
            if axis == "kuBeam":
                label = "keyhole" if ref["D_um"] / ref["W_um"] >= 0.5 else "transition"
            raws.append({"rowId": f"{sid}-{i:02d}", "source": sid, "role": "verdict", "material": mat, "axis": axis,
                         "variants": variants, "preheat_C": 20.0, "layer_um": layer if sid.startswith("hofmann") else None,
                         "width_um": ref["W_um"] * wob, "depth_um": ref["D_um"] * wob, "t_um": layer,
                         "balling": 0 if sid.startswith("hofmann") else None, "publishedLabel": label})
    return raws


class TinyPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = {}
        for mode in ("near_a0", "near_base"):
            s1 = E.build_stage1(_fixture_raws(mode), {}, "test")
            s2 = E.build_stage2(s1, "0" * 64, 1, "test", E.C.FROZEN_FINGERPRINT)
            cls.out[mode] = (s1, s2, E.run_stage3(s1, s2, 1, arms=("A0", "S3")))

    def test_stage1_has_no_kernel_output_and_axes(self):
        s1, s2, _ = self.out["near_a0"]
        self.assertFalse(s1["laneAxisActive"])
        self.assertEqual(len(s1["grid"]), 8)
        self.assertNotIn("baseline", s1)
        for r in s1["rows"]:
            self.assertNotIn("W_um", str(r["variants"]))
        r0 = s1["rows"][0]
        self.assertAlmostEqual(r0["depth_layer_um"], r0["depth_published_um"] + 0.6 * 30.0, places=9)
        self.assertTrue(r0["eligible"]["width"])  # hofmann width gated, balling 0
        totis = [r for r in s1["rows"] if r["source"] == "totis-ti64-2021"][0]
        self.assertFalse(totis["eligible"]["width"])  # width unconfirmed at stage 0
        self.assertTrue(totis["eligible"]["depth"])
        for r in s1["rows"]:
            self.assertEqual(r["variants"][next(iter(r["variants"]))]["affected"],
                             r["variants"][next(iter(r["variants"]))]["H"] > 15.0)

    def test_stage2_parity_and_frozen_populations(self):
        s1, s2, _ = self.out["near_a0"]
        self.assertTrue(s2["parity"]["ok"])
        self.assertEqual(s2["parity"]["maxRelErr"], 0.0)
        self.assertNotIn("skill", str(s2["gridSets"]).lower())
        pops = s2["populations"]
        pa = pops["hofmann-316l-2026"]["base"]["eagar-tsai"]["depth"]
        self.assertTrue(set(pa["affected"]) <= set(pa["all"]))
        self.assertEqual(len(pa["all"]), 7)
        self.assertNotIn("width", pops["totis-ti64-2021"]["base"]["eagar-tsai"])
        gs = s2["gridSets"][E.grid_key(s1["grid"][0])]["eagar-tsai"]
        self.assertGreaterEqual(len(gs["E"]), 2)
        self.assertEqual(gs["E_W"], ["hofmann-316l-2026"])
        self.assertEqual(set(gs["T"]), set(gs["E"]))

    def test_conduction_identity_and_envelope(self):
        _, _, r = self.out["near_a0"]
        self.assertTrue(r["diagnostics"]["D4"]["pass"])
        self.assertTrue(r["diagnostics"]["D3"]["insideEnvelope"])

    def test_candidate_beats_baseline_when_measurements_follow_it(self):
        s1, _, r = self.out["near_a0"]
        gk = E.grid_key(s1["grid"][0])
        for k in E.KERNELS:
            c = r["results"]["A0"][gk][k]
            self.assertTrue(c["C6"]["pass"])
            self.assertGreater(c["perSource"]["hofmann-316l-2026"]["depth"]["P"]["skill"], 0.0, k)
            self.assertGreaterEqual(c["C2"]["pooled"]["skill"], 0.0)
        # Fabbro dominates the Eagar-Tsai and Goldak depth of the other sources, so only width moves there:
        # skill is exactly 0 and C1 (strictly > 0 on every source) fails, as pre-registered weakness 3 predicts
        c = r["results"]["A0"][gk]["eagar-tsai"]
        self.assertEqual(c["C1"]["skills"]["totis-ti64-2021"], 0.0)
        self.assertFalse(c["C1"]["pass"])
        self.assertNotIn(r["decision"]["result"], ("INVALID",))

    def test_candidate_loses_when_measurements_follow_the_baseline(self):
        s1, _, r = self.out["near_base"]
        gk = E.grid_key(s1["grid"][0])
        for k in E.KERNELS:
            c = r["results"]["A0"][gk][k]
            self.assertFalse(c["C1"]["pass"], k)
            self.assertEqual(c["verdict"], "FAIL")
        self.assertTrue(r["decision"]["result"].startswith("FAIL"))

    def test_pinned_fixture_numbers(self):
        s1, _, r = self.out["near_a0"]
        gk = E.grid_key(s1["grid"][0])
        c = r["results"]["A0"][gk]["eagar-tsai"]
        pins = {k: (round(c["perSource"][s]["depth"]["P"]["mapeCand"], 6), c["perSource"][s]["depth"]["P"]["n"])
                for k, s in (("hofmann", "hofmann-316l-2026"), ("totis", "totis-ti64-2021"))}
        self.assertEqual(pins, PINNED_DEPTH)
        self.assertEqual(r["decision"]["result"], PINNED_DECISION["near_a0"])
        self.assertEqual(self.out["near_base"][2]["decision"]["result"], PINNED_DECISION["near_base"])


PINNED_DEPTH = {"hofmann": (0.035236, 6), "totis": (0.039321, 7)}
PINNED_DECISION = {"near_a0": "FAIL", "near_base": "FAIL"}  # C1 needs skill > 0 on every source; C5 not evaluable (7 rows)

if __name__ == "__main__":
    unittest.main()
