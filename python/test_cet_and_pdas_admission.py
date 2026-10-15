#!/usr/bin/env python3
"""PDAS source-model admission (SOL-A1) and, from SOL-A A2 on, the CET masks and source checks.

Authority: solidification integration contract 6.3 (the five named pairs, the three independent predicate tests) and
SPEC_solidification_2026-10-14.md 5.2, gate 4 and Amendment 3 A3.A2 (one canonical coefficient precision) and A3.A4
(the fixed-G line, Vcs and Vab as separate predicates). Synthetic (G, R) pairs only; no measured datum is read. A
passing synthetic direct-function point is source-model arithmetic, never a served sample or a physical test.

The CET masks and source checks of contract 4.7 belong to the A2 lane (lpbf_cet_screening.py) and are added here.

    python -B -m unittest test_cet_and_pdas_admission
"""
import ast
import math
import unittest
from pathlib import Path

import solidification_front as sf

HUNT_A_CANONICAL_SI = 1.1773863284676703e-3
KURZ_FISHER_A_CANONICAL_SI = 2.5821435943712695e-3

# Contract 6.3 (G in K/m, R in m/s): expected admission booleans per pair.
PAIRS = {
    1: (1e7, 0.05, {"onSourceLine": True, "xInRange": True, "coolingInRange": True, "aboveVcs": True,
                    "belowVab": True}),
    2: (2e7, 0.01, {"onSourceLine": False, "xInRange": True, "coolingInRange": True, "aboveVcs": True,
                    "belowVab": True}),
    3: (5e6, 0.05, {"onSourceLine": False, "xInRange": True, "coolingInRange": True, "aboveVcs": True,
                    "belowVab": True}),
    4: (5e7, 0.0012, {"onSourceLine": False, "xInRange": True, "coolingInRange": True, "aboveVcs": False,
                      "belowVab": True}),
    5: (1e6, 1.5, {"onSourceLine": False, "xInRange": True, "coolingInRange": True, "aboveVcs": True,
                   "belowVab": False}),
}
RETURN_KEYS = {"pdasBand_um", "pdasOutOfRange", "reasons", "admission", "x", "coolingRate_K_s", "vcs_m_s", "alloyId",
               "sources", "modelId"}


class CanonicalCoefficients(unittest.TestCase):
    def test_served_literals_are_the_canonical_binary64_values(self):
        tree = ast.parse((Path(sf.__file__)).read_text(encoding="utf-8"))
        encoded = {target.id: ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                   for target in node.targets
                   if isinstance(target, ast.Name) and target.id in ("PDAS_A_HUNT_SI", "PDAS_A_KURZ_FISHER_SI")}
        self.assertEqual(encoded, {"PDAS_A_HUNT_SI": HUNT_A_CANONICAL_SI,
                                   "PDAS_A_KURZ_FISHER_SI": KURZ_FISHER_A_CANONICAL_SI})
        self.assertEqual(sf.PDAS_A_HUNT_SI, HUNT_A_CANONICAL_SI)
        self.assertEqual(sf.PDAS_A_KURZ_FISHER_SI, KURZ_FISHER_A_CANONICAL_SI)

    def test_independent_equations_reproduce_them(self):
        k_e, gamma, dt0, d_l = 0.48, 3.65e-7, 57.0, 3e-9
        self.assertTrue(math.isclose(2.83 * (k_e * gamma * dt0 * d_l) ** 0.25, HUNT_A_CANONICAL_SI, rel_tol=1e-12))
        self.assertTrue(math.isclose(4.3 * (gamma * dt0 * d_l / k_e) ** 0.25, KURZ_FISHER_A_CANONICAL_SI,
                                     rel_tol=1e-12))
        self.assertEqual((sf.PDAS_SOURCE_K_E, sf.PDAS_SOURCE_GAMMA_K_M, sf.PDAS_SOURCE_DELTA_T0_K,
                          sf.PDAS_SOURCE_D_L_M2_S), (k_e, gamma, dt0, d_l))

    def test_the_served_producer_uses_them(self):
        # The kinetics probe point (G 1e7, R 0.01, in718): x = 1e-3 exactly in exact arithmetic.
        out = sf.pdas_band_um(1e7, 0.01, "in718")
        x = 1e7 ** -0.5 * 0.01 ** -0.25
        self.assertTrue(math.isclose(out["pdasBand_um"]["hunt"], HUNT_A_CANONICAL_SI * x * 1e6, rel_tol=1e-12))
        self.assertTrue(math.isclose(out["pdasBand_um"]["kurzFisher"], KURZ_FISHER_A_CANONICAL_SI * x * 1e6,
                                     rel_tol=1e-12))
        for stale in (9.56e-4, 1.18e-3, 2.6e-3):
            self.assertFalse(math.isclose(out["pdasBand_um"]["hunt"] / (x * 1e6), stale, rel_tol=1e-9))
            self.assertFalse(math.isclose(out["pdasBand_um"]["kurzFisher"] / (x * 1e6), stale, rel_tol=1e-9))


class Predicates(unittest.TestCase):
    """A3.A4: the three predicates are tested directly and independently."""

    def test_fixed_g_line_predicate(self):
        self.assertTrue(sf.pdas_on_source_line(1e7))
        self.assertTrue(sf.pdas_on_source_line(1e7 * (1 + 5e-13)))
        self.assertFalse(sf.pdas_on_source_line(1e7 * (1 + 1e-11)))
        self.assertFalse(sf.pdas_on_source_line(2e7))
        self.assertFalse(sf.pdas_on_source_line(5e6))
        for bad in (float("nan"), float("inf"), 0.0, -1e7, True, "1e7", None):
            self.assertFalse(sf.pdas_on_source_line(bad), bad)

    def test_vcs_predicate(self):
        self.assertFalse(sf.pdas_above_vcs(5e7, 0.0012))      # Vcs 2.6315789e-3 m/s
        self.assertTrue(sf.pdas_above_vcs(2e7, 0.01))         # Vcs 1.0526316e-3 m/s
        self.assertAlmostEqual(sf.pdas_vcs_m_s(5e7), 5e7 * 3e-9 / 57.0, delta=1e-18)
        self.assertFalse(sf.pdas_above_vcs(5e7, sf.pdas_vcs_m_s(5e7)), "strict: R = Vcs is not above")

    def test_vab_predicate(self):
        self.assertFalse(sf.pdas_below_vab(1.5))
        self.assertTrue(sf.pdas_below_vab(0.01))
        self.assertFalse(sf.pdas_below_vab(0.98), "strict: R = Vab is not below")


class NamedPairs(unittest.TestCase):
    """Contract 6.3: the line rule alone decides pairs 2 and 3; 4 and 5 also fail Vcs and Vab."""

    def test_pairs_through_pdas_band_um(self):
        for alloy in ("in625", "in718"):
            for pair, (g, r, admission) in PAIRS.items():
                out = sf.pdas_band_um(g, r, alloy)
                self.assertEqual(set(out), RETURN_KEYS)
                self.assertEqual(out["admission"], admission, (alloy, pair))
                self.assertEqual(out["alloyId"], alloy)
                if pair == 1:
                    self.assertFalse(out["pdasOutOfRange"])
                    self.assertEqual(out["reasons"], [])
                    self.assertEqual(sorted(out["pdasBand_um"]), ["hunt", "kurzFisher"])
                    self.assertEqual([s["id"] for s in out["sources"]], ["ghosh2017"])
                else:
                    self.assertIsNone(out["pdasBand_um"], (alloy, pair))
                    self.assertIs(out["pdasOutOfRange"], True)
                    self.assertEqual(out["reasons"], [{"code": "outside-source-model-domain", "params": admission,
                                                       "parent": None}])
                    self.assertEqual(out["sources"], [])

    def test_a_box_plus_vcs_vab_mutant_would_admit_pairs_2_and_3(self):
        for pair in (2, 3):
            admission = PAIRS[pair][2]
            mutant = all(value for key, value in admission.items() if key != "onSourceLine")
            self.assertTrue(mutant, pair)
            self.assertIsNone(sf.pdas_band_um(PAIRS[pair][0], PAIRS[pair][1], "in718")["pdasBand_um"], pair)

    def test_ti64_alsi10mg_316l_never_get_a_band(self):
        for alloy in ("ti6al4v", "alsi10mg", "ss316l"):
            for g, r, _ in PAIRS.values():
                out = sf.pdas_band_um(g, r, alloy)
                self.assertIsNone(out["pdasBand_um"], alloy)
                self.assertIsNone(out["pdasOutOfRange"], alloy)
                self.assertIsNone(out["admission"], alloy)
                self.assertEqual([item["code"] for item in out["reasons"]], ["missing-source-bound-model"])

    def test_only_canonical_ids_are_accepted(self):
        for alias in ("Inconel 718", "Inconel 625", "inconel", "IN718", "", None, 718):
            out = sf.pdas_band_um(1e7, 0.05, alias)
            self.assertIsNone(out["pdasBand_um"], alias)
            self.assertIsNone(out["alloyId"], alias)
            self.assertEqual([item["code"] for item in out["reasons"]], ["unknown-alloy-alias"], alias)

    def test_nonphysical_inputs_are_refused_before_comparison(self):
        nan, inf = float("nan"), float("inf")
        for g, r, cooling in ((nan, 0.05, None), (1e7, nan, None), (inf, 0.05, None), (1e7, -0.05, None),
                              (0.0, 0.05, None), (1e7, 0.0, None), (True, 0.05, None), ("1e7", 0.05, None),
                              (1e7, 0.05, nan), (1e7, 0.05, -1.0), (1e7, 0.05, 0.0)):
            out = sf.pdas_band_um(g, r, "in718", cooling)
            self.assertIsNone(out["pdasBand_um"], (g, r, cooling))
            self.assertIsNone(out["admission"], (g, r, cooling))
            self.assertEqual([item["code"] for item in out["reasons"]], ["nonphysical-input"], (g, r, cooling))

    def test_an_explicit_cooling_rate_outside_the_source_range_is_refused(self):
        for cooling in (1e4, 5e6):
            out = sf.pdas_band_um(1e7, 0.05, "in718", cooling)
            self.assertIsNone(out["pdasBand_um"], cooling)
            self.assertFalse(out["admission"]["coolingInRange"], cooling)


if __name__ == "__main__":
    unittest.main()
