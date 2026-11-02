#!/usr/bin/env python3
"""Tests for the Scheil research arm (python/research_scheil.py).

Self-contained: the fast tests use small synthetic run_point fixtures defined here (no pycalphad, no TDB
solve). They pin the bookkeeping, not any alloy physics. Real CALPHAD solves run only with
METALLIX_SLOW_TESTS=1 (or --slow): the IN625 C-free paired equilibrium + Scheil case on mc_ni (minutes).

    python python/test_research_scheil.py [--slow]
"""

import math
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import research_scheil as rs  # noqa: E402

SLOW = "--slow" in sys.argv or os.environ.get("METALLIX_SLOW_TESTS") == "1"
if "--slow" in sys.argv:
    sys.argv.remove("--slow")


# ------------------------------------------------------------------------------ synthetic fixtures
class ConstantKBinary:
    """Binary A-B with a linear liquidus T_L(C) = TM - M*C, constant k = C_S/C_L and a eutectic at C_E.

    Above the eutectic the lever rule gives the equilibrium of composition C at T; at or below T_E the
    liquid freezes completely into alpha (k*C_E) and beta (C_BETA). Exact Scheil path in the primary
    range: C_L = C0 (1 - fs)^(k - 1), i.e. T(fs) = TM - M*C0*(1 - fs)^(k - 1).
    """

    TM, M, C_E, C_BETA = 1000.0, 500.0, 0.3, 0.9

    def __init__(self, k):
        self.k = k
        self.t_e = self.TM - self.M * self.C_E

    def __call__(self, t, x):
        c = x["B"]
        k = self.k
        if t <= self.t_e:  # eutectic and below: everything solid
            ca = k * self.C_E
            if c <= ca:
                return {"vertices": [{"phase": "ALPHA", "amount": 1.0, "X": {"A": 1 - c, "B": c}}]}
            fb = (c - ca) / (self.C_BETA - ca)
            return {"vertices": [{"phase": "ALPHA", "amount": 1 - fb, "X": {"A": 1 - ca, "B": ca}},
                                 {"phase": "BETA", "amount": fb, "X": {"A": 1 - self.C_BETA, "B": self.C_BETA}}]}
        c_l = (self.TM - t) / self.M
        c_s = k * c_l
        if c >= c_l or c_l <= 0:
            return {"vertices": [{"phase": "LIQUID", "amount": 1.0, "X": {"A": 1 - c, "B": c}}]}
        if c <= c_s:
            return {"vertices": [{"phase": "ALPHA", "amount": 1.0, "X": {"A": 1 - c, "B": c}}]}
        q_l = (c - c_s) / (c_l - c_s)
        return {"vertices": [{"phase": "LIQUID", "amount": q_l, "X": {"A": 1 - c_l, "B": c_l}},
                             {"phase": "ALPHA", "amount": 1 - q_l, "X": {"A": 1 - c_s, "B": c_s}}]}

    def analytic_t(self, c0, fs):
        return self.TM - self.M * c0 * (1 - fs) ** (self.k - 1)


def scripted(liquid_by_t, solids=("S",)):
    """No-segregation fixture: liquid fraction from a function of T, every vertex at the input composition."""
    def run(t, x):
        q = liquid_by_t(t)
        if q is None:
            return None
        verts = [{"phase": "LIQUID", "amount": q, "X": dict(x)}] if q > 0 else []
        share = (1 - q) / len(solids)
        verts += [{"phase": s, "amount": share, "X": dict(x)} for s in solids if share > 0]
        return {"vertices": verts}
    return run


X0 = {"A": 0.95, "B": 0.05}


class CoreBookkeeping(unittest.TestCase):
    def test_label_is_research_literature_estimate(self):
        path = rs.scheil_path(ConstantKBinary(0.2), 980.0, X0, step_c=2.0)
        self.assertEqual(path["label"]["evidenceKind"], "Literature estimate")
        self.assertEqual(path["label"]["maturity"], "Research")
        self.assertIs(path["label"]["validated"], False)
        self.assertIs(path["label"]["servedOutput"], False)

    def test_constant_k_matches_analytic_scheil(self):
        fx = ConstantKBinary(0.2)
        path = rs.scheil_path(fx, 980.0, X0, step_c=0.5, min_step_c=0.01, bracket_c=0.05, max_fs_jump=0.01)
        self.assertEqual(path["status"], "complete")
        for q in (0.5, 0.8):
            got = path["thresholdTemperatures"].get(f"{q:g}") or None
            if got is None:  # 0.8 is a key only if listed; compute from the curve instead
                pts = [p for p in path["curve"] if p["fractionSolid"] >= q]
                t = pts[0]["temperatureC"]
            else:
                t = got["midpointC"]
            self.assertAlmostEqual(t, fx.analytic_t(0.05, q), delta=0.5)
        # first solid at the liquidus of C0 (975 C) within the bracket
        onset = path["temperatureOnset"]["bracketC"]
        self.assertLessEqual(onset[0], 975.0 + 1e-9)
        self.assertGreaterEqual(onset[1] + 1e-9, 975.0 - 0.05)

    def test_eutectic_terminal_jump_is_a_jump(self):
        fx = ConstantKBinary(0.2)
        path = rs.scheil_path(fx, 980.0, X0, step_c=2.0)
        self.assertEqual(path["stopReason"], "liquid-exhausted")
        ex = path["temperatureExhaustion"]
        self.assertLessEqual(ex["bracketC"][0], fx.t_e)
        self.assertGreaterEqual(ex["bracketC"][1], fx.t_e)
        self.assertLessEqual(ex["bracketWidthK"], rs.DEFAULT_MIN_STEP_C + 1e-12)
        fs_e = 1 - (fx.C_E / 0.05) ** (1 / (fx.k - 1))
        self.assertAlmostEqual(ex["fractionSolidJump"], 1 - fs_e, delta=0.01)
        self.assertEqual(ex["phasesFormed"], ["ALPHA", "BETA"])
        self.assertTrue(path["pathInventory"]["ok"], path["pathInventory"])
        self.assertLess(path["pathInventory"]["maxAbsError"], 1e-12)

    def test_scheil_wider_than_lever_rule(self):
        fx = ConstantKBinary(0.2)
        path = rs.scheil_path(fx, 980.0, X0, step_c=1.0)
        lever_solidus = fx.TM - fx.M * 0.05 / fx.k  # C_S = C0
        self.assertLess(path["thresholdTemperatures"]["0.999"]["midpointC"], lever_solidus)

    def test_k_equal_one_no_segregation(self):
        fx = ConstantKBinary(1.0)
        path = rs.scheil_path(fx, 980.0, X0, step_c=2.0)
        self.assertEqual(path["stopReason"], "liquid-exhausted")
        ex = path["temperatureExhaustion"]["bracketC"]
        self.assertTrue(ex[0] <= 975.0 <= ex[1], ex)
        self.assertEqual(path["solidVertexCount"], 1)
        self.assertTrue(path["pathInventory"]["ok"])

    def test_two_solids_in_one_step_use_same_liquid_weight(self):
        # 0.8 liquid + 0.1 + 0.1 solid: the new solid is 0.20, not 0.19 (running-update error)
        def run(t, x):
            if t >= 1000:
                return {"vertices": [{"phase": "LIQUID", "amount": 1.0, "X": dict(x)}]}
            return {"vertices": [{"phase": "LIQUID", "amount": 0.8, "X": {"A": 0.5, "B": 0.5}},
                                 {"phase": "S1", "amount": 0.1, "X": {"A": 0.7, "B": 0.3}},
                                 {"phase": "S2", "amount": 0.1, "X": {"A": 0.3, "B": 0.5 + 0.2}}]}
        path = rs.scheil_path(run, 1001.0, {"A": 0.5, "B": 0.5}, step_c=2.0, min_step_c=2.0, bracket_c=5.0,
                              max_fs_jump=0.5, max_calls=2)
        self.assertAlmostEqual(path["curve"][1]["fractionSolid"], 0.2, places=12)
        self.assertAlmostEqual(path["phaseTotals"]["S1"], 0.1, places=12)
        self.assertAlmostEqual(path["phaseTotals"]["S2"], 0.1, places=12)

    def test_phase_order_does_not_change_result(self):
        fx = ConstantKBinary(0.2)

        def reversed_fx(t, x):
            r = fx(t, x)
            return {"vertices": list(reversed(r["vertices"]))}
        a = rs.scheil_path(fx, 980.0, X0, step_c=2.0)
        b = rs.scheil_path(reversed_fx, 980.0, X0, step_c=2.0)
        self.assertEqual(a["thresholdTemperatures"], b["thresholdTemperatures"])
        for ph in a["phaseTotals"]:
            self.assertAlmostEqual(a["phaseTotals"][ph], b["phaseTotals"][ph], places=13)

    def test_never_forces_fraction_solid_one(self):
        # solver stops converging below 990 C: path stops with liquid left, no fs = 1 point is added
        run = scripted(lambda t: None if t < 990 else max(0.0, min(1.0, (t - 980) / 20.0)))
        path = rs.scheil_path(run, 1001.0, X0, step_c=2.0)
        self.assertEqual(path["status"], "incomplete")
        self.assertEqual(path["stopReason"], "non-convergence")
        self.assertGreater(path["residualLiquidFraction"], 0.0)
        self.assertLess(max(p["fractionSolid"] for p in path["curve"]), 1.0)
        self.assertIsNone(path["temperatureExhaustion"])
        self.assertIsNone(path["thresholdTemperatures"]["0.999"])
        self.assertTrue(path["pathInventory"]["ok"])

    def test_failed_step_is_rolled_back_not_booked(self):
        fails = {"left": 1}
        base = scripted(lambda t: 1.0 if t >= 1000 else 0.99)

        def run(t, x):
            if abs(t - 999.0) < 1e-9 and fails["left"]:
                fails["left"] -= 1
                return None
            return base(t, x)
        path = rs.scheil_path(run, 1001.0, X0, step_c=1.0, min_step_c=0.25, max_fs_jump=1.0, max_calls=6)
        temps = [p["temperatureC"] for p in path["curve"]]
        self.assertEqual(fails["left"], 0)
        self.assertNotIn(999.0, temps)
        self.assertIn(999.5, temps)
        self.assertGreaterEqual(path["rejectedOrRefinedSteps"], 1)
        self.assertTrue(path["pathInventory"]["ok"])

    def test_negative_or_nan_amount_rejected(self):
        for bad in (-0.1, float("nan")):
            def run(t, x, bad=bad):
                if t >= 1000:
                    return {"vertices": [{"phase": "LIQUID", "amount": 1.0, "X": dict(x)}]}
                return {"vertices": [{"phase": "LIQUID", "amount": 1.1, "X": dict(x)},
                                     {"phase": "S", "amount": bad, "X": dict(x)}]}
            path = rs.scheil_path(run, 1001.0, X0, step_c=2.0, min_step_c=0.5)
            self.assertEqual(path["stopReason"], "invalid-solver-output")
            self.assertEqual(path["residualLiquidFraction"], 1.0)

    def test_inventory_not_closed_rejected(self):
        def run(t, x):
            if t >= 1000:
                return {"vertices": [{"phase": "LIQUID", "amount": 1.0, "X": dict(x)}]}
            return {"vertices": [{"phase": "LIQUID", "amount": 0.5, "X": dict(x)},
                                 {"phase": "S", "amount": 0.5, "X": {"A": 0.9, "B": 0.1}}]}
        path = rs.scheil_path(run, 1001.0, X0, step_c=2.0, min_step_c=0.5)
        self.assertEqual(path["stopReason"], "inventory-not-closed")
        self.assertEqual(path["status"], "incomplete")

    def test_two_liquids_stop(self):
        def run(t, x):
            if t >= 1000:
                return {"vertices": [{"phase": "LIQUID", "amount": 1.0, "X": dict(x)}]}
            return {"vertices": [{"phase": "LIQUID", "amount": 0.5, "X": {"A": 0.9, "B": 0.1}},
                                 {"phase": "LIQUID", "amount": 0.5, "X": {"A": 1.0, "B": 0.0}}]}
        path = rs.scheil_path(run, 1001.0, X0, step_c=2.0)
        self.assertEqual(path["stopReason"], "multiple-liquid-phases")
        self.assertEqual(path["solverCalls"], 2)  # fatal: no step halving
        self.assertEqual(path["residualLiquidFraction"], 1.0)

    def test_gas_phase_stops(self):
        def run(t, x):
            if t >= 1000:
                return {"vertices": [{"phase": "LIQUID", "amount": 1.0, "X": dict(x)}]}
            return {"vertices": [{"phase": "LIQUID", "amount": 0.9, "X": dict(x)},
                                 {"phase": "GAS", "amount": 0.1, "X": dict(x)}]}
        path = rs.scheil_path(run, 1001.0, X0, step_c=2.0)
        self.assertEqual(path["stopReason"], "gas-phase-formed")

    def test_threshold_exact_equality_counts_at_that_step(self):
        # fs reaches exactly 0.5 at 999 C and stays; the 0.5 crossing bracket is [999, 1000]
        run = scripted(lambda t: 1.0 if t > 999.5 else 0.5 if t > 990 else 0.5)
        path = rs.scheil_path(run, 1000.0, X0, step_c=1.0, min_step_c=1.0, bracket_c=1.0, max_fs_jump=1.0,
                              max_calls=3)
        self.assertEqual(path["thresholdTemperatures"]["0.5"]["bracketC"], [999.0, 1000.0])
        self.assertIsNone(path["thresholdTemperatures"]["0.9"])

    def test_threshold_brackets_are_refined(self):
        fx = ConstantKBinary(0.2)
        path = rs.scheil_path(fx, 980.0, X0, step_c=2.0, bracket_c=0.5)
        for q, b in path["thresholdTemperatures"].items():
            self.assertIsNotNone(b, q)
            self.assertLessEqual(b["bracketWidthK"], 0.5 + 1e-12, q)

    def test_start_must_be_fully_liquid(self):
        path = rs.scheil_path(ConstantKBinary(0.2), 970.0, X0, step_c=2.0)
        self.assertEqual(path["stopReason"], "start-not-fully-liquid")
        self.assertEqual(path["status"], "incomplete")

    def test_trace_clamp_is_reported(self):
        x0 = {"A": 0.95 - 1e-8, "B": 0.05, "C": 1e-8}
        run = scripted(lambda t: 1.0 if t >= 1000 else 0.0)
        path = rs.scheil_path(run, 1001.0, x0, step_c=2.0)
        self.assertGreater(path["conditionClampUses"], 0)
        self.assertIsNotNone(path["conditionClampNote"])
        self.assertGreater(path["conditionClampMaxChange"], 0.0)


class Pairing(unittest.TestCase):
    IDENT = {"tdbSha256": "abc", "phases": ["FCC_A1", "LIQUID"], "usedMoleFractions": {"A": 0.95, "B": 0.05},
             "pressurePa": 101325.0, "calcOptions": {}, "seeded": False, "pycalphadVersion": "0.11.2"}
    EQ = {"criticalTemperatures": {"liquidusC": 975.1, "solidusC": 900.0},
          "criticalTemperatureStatus": {"liquidusC": {"bracketC": [974.9, 975.3]},
                                        "solidusC": {"bracketC": [899.8, 900.2]}}}

    def test_signed_deltas(self):
        path = rs.scheil_path(ConstantKBinary(0.2), 980.0, X0, step_c=1.0)
        cmp_ = rs.compare_with_equilibrium(path, self.IDENT, self.EQ, dict(self.IDENT))
        self.assertAlmostEqual(cmp_["deltaFirstSolidK"], cmp_["scheilT0_001C"] - 975.1, places=12)
        self.assertLess(cmp_["deltaLastSolidK"], 0.0)
        self.assertEqual(cmp_["label"]["evidenceKind"], "Literature estimate")

    def test_identity_mismatch_refused(self):
        path = rs.scheil_path(ConstantKBinary(0.2), 980.0, X0, step_c=2.0)
        for key, val in (("tdbSha256", "def"), ("phases", ["LIQUID"]), ("calcOptions", {"pdens": 60}),
                         ("usedMoleFractions", {"A": 0.9, "B": 0.1})):
            other = dict(self.IDENT)
            other[key] = val
            with self.assertRaises(rs.ScheilInputError):
                rs.compare_with_equilibrium(path, self.IDENT, self.EQ, other)


class CasePreparation(unittest.TestCase):
    """Database and composition checks without pycalphad (reads TDB headers and the catalogue only)."""

    def test_missing_element_refused_not_dropped(self):
        with self.assertRaises(rs.ScheilInputError) as ctx:
            rs.prepare_composition({"Ni": 60.0, "Cr": 21.5, "Mo": 9.0, "Nb": 3.5, "Ta": 0.1, "Fe": 4.9}, "mc_ni")
        self.assertIn("TA", str(ctx.exception).upper())

    def test_in625_flags_tested_limits_and_licence(self):
        prep = rs.prepare_case("in625_c0")
        flagged = {f.get("element", "").upper() for f in prep["outsideTestedLimits"]}
        self.assertTrue({"CR", "MO"} <= flagged, prep["outsideTestedLimits"])
        self.assertIn("ODbL", prep["databaseLicence"])
        self.assertEqual(len(prep["tdbSha256"]), 64)

    def test_enriched_liquid_outside_tested_limits_flagged(self):
        curve = [{"temperatureC": 1650.0, "fractionSolid": 0.0, "liquidX": {"TI": 0.86, "AL": 0.10, "V": 0.04}},
                 {"temperatureC": 1600.0, "fractionSolid": 0.6, "liquidX": {"TI": 0.75, "AL": 0.13, "V": 0.12}},
                 {"temperatureC": 1590.0, "fractionSolid": 1.0, "liquidX": None}]
        flags = rs.liquid_outside_tested_limits(curve, {"AL": 30.0, "V": 5.0})
        self.assertEqual([f["element"] for f in flags], ["V"])
        self.assertEqual(flags[0]["firstExceededAtC"], 1600.0)
        self.assertGreater(flags[0]["maxLiquidWtPct"], 5.0)
        self.assertEqual(rs.liquid_outside_tested_limits(curve, {}), [])

    def test_ti64_iron_refused_on_mc_ti(self):
        with self.assertRaises(rs.ScheilInputError):
            rs.prepare_composition({"Ti": 89.9, "Al": 6.0, "V": 4.0, "Fe": 0.1}, "mc_ti")


@unittest.skipUnless(SLOW, "real CALPHAD solve: set METALLIX_SLOW_TESTS=1 or pass --slow")
class SlowIn625(unittest.TestCase):
    def test_in625_c0_paired(self):
        import calphad_solver as cs
        if not cs.PYCALPHAD_AVAILABLE:
            self.skipTest("pycalphad not installed")
        res = rs.run_case(rs.prepare_case("in625_c0"), steps_c=(2.0,))
        run = res["scheilRuns"][0]
        self.assertTrue(run["pathInventory"]["ok"], run["pathInventory"])
        cmp_ = run["comparison"]
        # same thermodynamics: first solid within a few K of the equilibrium liquidus
        self.assertLess(abs(cmp_["deltaFirstSolidK"]), 2.0, cmp_)
        self.assertIsNotNone(run["thresholdTemperatures"]["0.999"], run["stopReason"])
        self.assertTrue(math.isfinite(cmp_["deltaLastSolidK"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
