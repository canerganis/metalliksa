"""Keyhole-regime planned physics bump: regime threshold 30 -> 20, porosity screen decoupled.

Self-contained: every number is pinned inline; nothing is read from a mock set. The geometry and grid fixtures were
re-recorded after the P1 planned bump (2026-10-11, flat absorptivity, no latent factor, depth = max(d_iso, Fabbro leg)
for every kernel; docs/research/SPEC_p1_sourced_served_physics_2026-10-11.md): the keyhole-regime and in625-regime bumps
kept every number, P1 moves the Rosenthal numbers and the grid, so the former "unchanged" fixtures now pin the post-P1
served values (recorded on the P1 tree, not re-fitted). Run from python/ with the locked interpreter:
    python -B -m unittest test_lpbf_keyhole_regime_bump
"""
import contextlib
import io
import math
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import lpbf_public_datasets as pds  # noqa: E402
import lpbf_thermal_solver as solver  # noqa: E402
from fabbro_keyhole import fabbro_keyhole_depth_m  # noqa: E402


def _run(*args, **kwargs):
    with contextlib.redirect_stdout(io.StringIO()):
        return solver.calculate_meltpool_physics(*args, **kwargs)


# Post-P1 Rosenthal results (recorded on the P1 tree, 2026-10-11; before P1, at 6f6f58f5 through 393cdbd1, they were
# 166.4/77.1/183.8/1306.8, 138.9/52.7/177.4/1010.5 and 109.6/35.6/152.3/718.4):
# (material, P_W, v_mm_s, d_um, preheat_C) -> (depth_um, vapor cavity depth_um, width_um, length_um, dH/hs)
P1_ROSENTHAL = {
    ("Inconel 718", 280, 940, 80, 80): (108.0, 44.2, 131.3, 680.6, 30.58),
    ("Ti-6Al-4V", 200, 900, 80, 150): (84.5, 24.3, 124.1, 511.1, 27.58),
    ("316L Stainless Steel", 200, 800, 70, 80): (58.2, 1.0, 117.9, 443.0, 24.02),
}
# Post-P1 process-map grid of IN718 200/800/80 (49 cells, P 80..540 W x v 300..2400 mm/s): width from the flat
# absorptivity, depth = max(w/2, Fabbro leg); the enthalpy column is unchanged by every bump.
P1_GRID_DEPTH_UM = [
    74.6, 59.8, 54.0, 50.9, 48.4, 46.8, 45.8,
    140.3, 72.9, 63.8, 58.8, 54.7, 52.1, 50.3,
    220.6, 126.1, 72.3, 65.7, 60.4, 56.9, 54.4,
    300.8, 171.9, 120.3, 86.4, 66.2, 61.9, 58.8,
    381.1, 217.7, 152.4, 117.2, 89.7, 66.5, 62.9,
    461.3, 263.6, 184.5, 141.9, 108.5, 87.9, 73.8,
    541.5, 309.4, 216.6, 166.6, 127.4, 103.1, 86.6,
]
P1_GRID_WIDTH_UM = [
    149.1, 119.7, 108.1, 101.8, 96.8, 93.7, 91.5,
    190.0, 145.8, 127.7, 117.6, 109.4, 104.2, 100.6,
    223.5, 167.9, 144.6, 131.5, 120.7, 113.7, 108.8,
    256.5, 190.0, 161.9, 145.8, 132.4, 123.7, 117.6,
    285.7, 209.8, 177.4, 158.8, 143.2, 133.0, 125.7,
    312.2, 227.9, 191.7, 170.8, 153.2, 141.6, 133.4,
    336.7, 244.7, 205.1, 182.0, 162.6, 149.8, 140.6,
]
PRE_GRID_ENTHALPY = [
    15.46, 10.93, 8.93, 7.73, 6.7, 5.99, 5.47,
    28.99, 20.5, 16.74, 14.5, 12.56, 11.23, 10.25,
    42.53, 30.07, 24.55, 21.26, 18.41, 16.47, 15.04,
    57.99, 41.0, 33.48, 28.99, 25.11, 22.46, 20.5,
    73.45, 51.94, 42.41, 36.73, 31.81, 28.45, 25.97,
    88.92, 62.87, 51.34, 44.46, 38.5, 34.44, 31.44,
    104.38, 73.81, 60.26, 52.19, 45.2, 40.43, 36.9,
]
# Post-P1 labels: T = Transition, L = Lack of Fusion Zone, K = Keyhole Mode (the lack-of-fusion cells follow the
# P1 grid depth; before P1 the string was TLLLLLLTTTLLLLKKTTTTTKKKTTTTKKKKKTTKKKKKKKKKKKKKK with the pre-bump labels)
P1_GRID_REGIME = "TLLLLLLKKLLLLLKKKKLLLKKKKKLLKKKKKKLKKKKKKKKKKKKKK"


class RegimeThresholds(unittest.TestCase):
    def test_regime_thresholds(self):
        c = solver.classify_enthalpy_regime
        self.assertEqual(c(14.99), "Conduction Mode (Stable)")
        self.assertEqual(c(15.0), "Transition Mode")
        self.assertEqual(c(19.99), "Transition Mode")
        self.assertEqual(c(20.0), "Keyhole Mode (melt-pool D/W > 0.5 screening onset)")
        self.assertTrue(c(30.0).startswith("Keyhole Mode"))
        self.assertEqual(solver.ENTHALPY_TRANSITION, 15.0)
        self.assertEqual(solver.ENTHALPY_KEYHOLE, 20.0)
        # P1 (2026-10-11) removed the Rosenthal increment and its 30 band edge.
        self.assertFalse(hasattr(solver, "KEYHOLE_INCREMENT_FULL_AT"))
        self.assertEqual(solver.POROSITY_SCREEN_NEGLIGIBLE_BELOW, 15.0)
        self.assertEqual(solver.POROSITY_SCREEN_HIGH_AT, 30.0)

    def test_king_conversion_316l(self):
        # King et al. 2014 Table 3: A = 0.4, rho = 7980 kg/m3, hs = 1.2e6 J/kg, D = 5.38e-6 m2/s, sigma = D4sigma / 4
        # (r = 2 sigma in the repo convention); threshold 30 +/- 4. App 316L: rho 7990, cp 500, T_liq 1400 C,
        # k 16.3, A 0.42, T0 20 C.
        a_k, rho_k, hs_k, d_k = 0.4, 7980.0, 1.2e6, 5.38e-6
        rho, cp, t_liq, k, a_app, t0 = 7990.0, 500.0, 1400.0, 16.3, 0.42, 20.0
        alpha = k / (rho * cp)
        factor = (a_k / a_app) * (rho * cp * (t_liq - t0)) / (rho_k * hs_k) * math.sqrt(alpha / d_k) * 2.0 ** 1.5
        self.assertAlmostEqual(factor, 1.351, delta=0.001)
        lo, mid, hi = 26.0 / factor, 30.0 / factor, 34.0 / factor
        self.assertAlmostEqual(lo, 19.3, delta=0.1)
        self.assertAlmostEqual(mid, 22.2, delta=0.1)
        self.assertAlmostEqual(hi, 25.2, delta=0.1)
        self.assertTrue(lo - 0.1 <= solver.ENTHALPY_KEYHOLE <= hi)
        # the solver's own 316L properties are the ones used above
        props = solver.THERMOPHYSICAL_DB["316L Stainless Steel"]
        self.assertEqual((props["density_kg_m3"], props["specific_heat_J_kgK"], props["liquidus_C"]),
                         (rho, cp, t_liq))

    def test_cunningham_red_line_brackets_threshold(self):
        # Cunningham 2019 Fig. 3A red (melt-pool transition) line, Ti-6Al-4V 95 um 1/e2, digitized:
        # P = 0.08448 v + 102.13 (W, mm/s); app index with the app's own Ti-6Al-4V properties, preheat 20 C.
        idx = [pds.normalized_enthalpy("Ti-6Al-4V", 0.08448 * v + 102.13, v, 95.0, 20.0)
               for v in range(400, 1201, 100)]
        self.assertTrue(all(17.2 <= x <= 20.1 for x in idx), idx)
        median = sorted(idx)[len(idx) // 2]
        self.assertGreaterEqual(solver.ENTHALPY_KEYHOLE, median)


class PinnedNumerics(unittest.TestCase):
    """Served numbers pinned at the P1 tree (the keyhole-regime and in625-regime label bumps changed no number)."""

    def test_rosenthal_geometry_pinned_post_p1(self):
        for (mat, p, v, d, t0), (depth, cavity, width, length, enth) in P1_ROSENTHAL.items():
            res = _run(mat, p, v, d, t0)
            geo = res["meltPoolGeometry"]
            self.assertEqual(geo["depth_um"], depth, mat)
            self.assertEqual(geo["keyholeVaporCavityDepth_um"], cavity, mat)
            self.assertEqual(geo["width_um"], width, mat)
            self.assertEqual(geo["length_um"], length, mat)
            self.assertEqual(res["processParameters"]["normalizedEnthalpy"], enth, mat)
            # P1: depth is the conduction isotherm depth or the Fabbro leg, whichever is larger, for every kernel.
            self.assertEqual(geo["depth_um"], max(round(depth - cavity, 1), res["keyholeModel"]["fabbroDepth_um"]), mat)

    def test_process_map_grid_pinned_post_p1(self):
        grid = _run("Inconel 718", 200, 800, 80, 80)["processWindowMap"]["grid"]
        self.assertEqual([c["normalizedEnthalpy"] for c in grid], PRE_GRID_ENTHALPY)
        self.assertEqual([c["depth_um"] for c in grid], P1_GRID_DEPTH_UM)
        self.assertEqual([c["width_um"] for c in grid], P1_GRID_WIDTH_UM)
        labels = {"T": ("Transition", "#38bdf8"), "L": ("Lack of Fusion Zone", "#f59e0b"), "K": ("Keyhole Mode", "#ef4444"),
                  "C": ("Optimal Conduction", "#10b981")}
        self.assertEqual("".join(next(k for k, lab in labels.items() if lab[0] == c["regime"]) for c in grid), P1_GRID_REGIME)
        for c, want in zip(grid, P1_GRID_REGIME):
            self.assertEqual((c["regime"], c["color"]), labels[want], c)
            # the Tang lack-of-fusion override reads the pinned grid width and depth (hatch 100 um, layer 40 um)
            tang = (100.0 / c["width_um"]) ** 2 + (40.0 / c["depth_um"]) ** 2
            self.assertEqual(want == "L", tang > 1.0, c)
            if want != "L":
                self.assertEqual(want, "C" if c["normalizedEnthalpy"] < 15.0 else ("K" if c["normalizedEnthalpy"] >= 20.0 else "T"), c)
        # the regime label still uses the 15 / 20 cuts: cells with 20 <= dH/hs <= 30 are Keyhole Mode, not Transition
        self.assertTrue(all(c["regime"] != "Transition" for c in grid if c["normalizedEnthalpy"] >= 20.0))

    def test_regime_basis_text(self):
        res = _run("Inconel 718", 280, 940, 80, 80)
        self.assertEqual(res["meltPoolGeometry"]["regimeBasis"], solver.REGIME_THRESHOLD_BASIS)
        self.assertEqual(res["processWindowMap"]["regimeBasis"], solver.REGIME_THRESHOLD_BASIS)
        self.assertIn("Keyhole mode is not keyhole porosity", solver.REGIME_THRESHOLD_BASIS)
        self.assertIn("transferred, not derived, for IN718/AlSi10Mg and the other alloys", solver.REGIME_THRESHOLD_BASIS)
        self.assertIn("Inconel 625 uses its own cut: < 13.6 conduction, >= 13.6 keyhole mode", solver.REGIME_THRESHOLD_BASIS)

    def test_regime_material_notes_and_wording(self):
        # A low index must not read as an assurance; the threshold is a provisional screening choice.
        self.assertIn("provisional screening choice", solver.REGIME_THRESHOLD_BASIS)
        self.assertIn("not a derived exact threshold", solver.REGIME_THRESHOLD_BASIS)
        self.assertIn("a low index is not an assurance", solver.REGIME_THRESHOLD_BASIS)
        expect = {"Inconel 625": solver.REGIME_MATERIAL_NOTE_IN625,
                  "Inconel 718": "threshold not validated for this alloy",
                  "AlSi10Mg": "threshold not validated for this alloy"}
        for mat, note in expect.items():
            self.assertEqual(solver.regime_material_note(mat), note, mat)
            self.assertEqual(_run(mat, 200, 800, 80, 80)["meltPoolGeometry"]["regimeMaterialNote"], note, mat)
        for mat in ("Ti-6Al-4V", "316L Stainless Steel"):
            self.assertIn("derived for this alloy", solver.regime_material_note(mat))

    def test_fabbro_unchanged(self):
        nist = fabbro_keyhole_depth_m(285.0, 0.960, 67e-6, 11.4, 11.4 / (8190.0 * 435.0), 2850.0, 23.5, 0.38, 35.0)
        self.assertAlmostEqual(nist["depth_m"] * 1e6, 123.9, delta=0.05)
        model = _run("Inconel 718", 285, 960, 67, 23.5, 40.0, 110.0, heat_source="eagar-tsai")["keyholeModel"]
        self.assertIn("under-predicts Ti-6Al-4V", model["depthBenchmarkNote"])
        self.assertIn("Cause not resolved; candidate mechanisms", model["depthBenchmarkNote"])
        self.assertIn("beam-diameter convention", model["depthBenchmarkNote"])
        self.assertIn("no vaporisation heat sink", model["depthBenchmarkNote"])
        self.assertIn(model["depthBenchmarkNote"], model["basis"])


# IN625 per-alloy cut (planned bump in625-regime, 2026-10-11). IN625 Rosenthal results at 80 C preheat, recorded on the
# P1 tree (before P1 the rows were 41.1/85.1/389.9/0.0, 104.0/163.1/501.2/24.8, 76.5/125.7/562.5/15.6, 47.3/97.6/209.9/0.0,
# 48.4/100.9/388.2/0.0): (P_W, v_mm_s, d_um) -> (dH/hs, pre-in625-bump family, depth_um, width_um, length_um, cavity_um)
P1_IN625 = {
    (195, 1200, 100): (14.6, "Conduction", 45.7, 94.5, 473.9, 0.0),
    (150, 400, 100): (19.45, "Transition", 67.6, 139.3, 379.1, 0.0),
    (195, 800, 100): (17.88, "Transition", 55.8, 115.2, 478.1, 0.0),
    (100, 400, 100): (12.96, "Conduction", 53.4, 110.1, 254.9, 0.0),
    (195, 800, 170): (8.06, "Conduction", 54.4, 113.1, 473.1, 0.0),
}
# Process-map grid of IN625 195/800/100 (C conduction, T transition, K keyhole, L lack of fusion); enthalpy unchanged by
# every bump, depth and labels recorded on the P1 tree.
PRE_IN625_GRID_ENTHALPY = [
    11.98, 8.47, 6.91, 5.99, 5.19, 4.64, 4.23, 22.45, 15.88, 12.96, 11.23, 9.72, 8.7, 7.94,
    32.93, 23.29, 19.01, 16.47, 14.26, 12.76, 11.64, 44.91, 31.76, 25.93, 22.45, 19.45, 17.39, 15.88,
    56.88, 40.22, 32.84, 28.44, 24.63, 22.03, 20.11, 68.86, 48.69, 39.76, 34.43, 29.82, 26.67, 24.35,
    80.84, 57.16, 46.67, 40.42, 35.0, 31.31, 28.58,
]
# Before the in625-regime bump the labels were CLLLLLLKTCLLLLKKTTLLLKKKKTTTKKKKKKKKKKKKKKKKKKKKK; after P1 (grid depth
# changed, so the lack-of-fusion cells move too) they are:
P1_IN625_GRID_REGIME = "CCLLLLLKKCCLLLKKKKKLLKKKKKKKKKKKKKKKKKKKKKKKKKKKK"
P1_IN625_GRID_DEPTH_UM = [
    79.5, 66.4, 61.4, 58.8, 56.7, 55.4, 54.6, 98.3, 78.0, 69.9, 65.5, 62.0, 59.8, 58.3,
    193.9, 88.0, 77.5, 71.6, 66.8, 63.8, 61.7, 264.4, 146.2, 85.3, 78.0, 72.0, 68.2, 65.5,
    334.9, 185.1, 127.9, 87.6, 76.8, 72.2, 69.0, 405.4, 224.1, 154.9, 118.3, 88.9, 76.1, 72.4,
    476.0, 263.1, 181.8, 138.9, 105.6, 85.2, 75.6,
]
# The 13 held-out units of the declared run (docs/research/RESULTS_in625_regime_2026-10-11.md section 5):
# (unit, app index at 20 C, measured depth over half width). Truth: keyhole when the ratio > 1.
HELD_OUT_IN625 = [
    ("mds2-ammt-row14", 4.17, 0.34), ("mds2-ammt-row13", 5.57, 0.41), ("lane2020-AMMT-C", 5.78, 0.57),
    ("lane2020-AMMT-B", 7.08, 0.59), ("lane2020-AMMT-A", 7.70, 0.57), ("mds2-ammt-row12", 7.91, 0.55),
    ("mds2-ammt-row11", 9.88, 0.68), ("mds2-ammt-row10", 12.67, 0.81), ("lane2020-CBM-C", 13.94, 1.20),
    ("lane2020-CBM-B", 17.07, 1.37), ("lane2020-CBM-A", 18.57, 1.77), ("mds2-ammt-row09", 23.86, 1.31),
    ("mds2-ammt-row08", 48.28, 2.92),
]
KEYHOLE_LABEL = "Keyhole Mode (melt-pool D/W > 0.5 screening onset)"


class In625RegimeCut(unittest.TestCase):
    def test_cut_values_and_other_alloys_unchanged(self):
        self.assertEqual(solver.ENTHALPY_KEYHOLE_IN625, 13.6)
        self.assertEqual(solver.regime_keyhole_cut("Inconel 625"), 13.6)
        for mat in (None, "Inconel 718", "Ti-6Al-4V", "316L Stainless Steel", "AlSi10Mg", "Hastelloy X", "CoCrMo"):
            self.assertEqual(solver.regime_keyhole_cut(mat), 20.0, mat)
        c = solver.classify_enthalpy_regime
        self.assertEqual(c(13.59, "Inconel 625"), "Conduction Mode (Stable)")
        for x in (13.6, 14.99, 15.0, 19.99, 20.0, 60.0):
            self.assertEqual(c(x, "Inconel 625"), KEYHOLE_LABEL, x)
        for mat in (None, "Inconel 718", "316L Stainless Steel"):
            self.assertEqual(c(14.99, mat), "Conduction Mode (Stable)")
            self.assertEqual(c(15.0, mat), "Transition Mode")
            self.assertEqual(c(19.99, mat), "Transition Mode")
            self.assertEqual(c(20.0, mat), KEYHOLE_LABEL)
        # the transition cut is shared and not moved (it also starts the Fabbro leg ramp)
        self.assertEqual(solver.ENTHALPY_TRANSITION, 15.0)

    def test_held_out_scores_pinned(self):
        # Truth fixed before the run (depth > half width); the cut lies in the held-out-admissible interval.
        self.assertTrue(12.667 < solver.ENTHALPY_KEYHOLE_IN625 <= 13.937)
        errors_in625 = sum((x >= solver.regime_keyhole_cut("Inconel 625")) != (r > 1.0) for _, x, r in HELD_OUT_IN625)
        errors_shared = sum((x >= solver.ENTHALPY_KEYHOLE) != (r > 1.0) for _, x, r in HELD_OUT_IN625)
        self.assertEqual((errors_in625, errors_shared), (0, 3))
        self.assertEqual(sum(r > 1.0 for _, _, r in HELD_OUT_IN625), 5)

    def test_geometry_pinned_post_p1_and_label_follows_the_cut(self):
        for (p, v, d), (h, fam, depth, width, length, cavity) in P1_IN625.items():
            res = _run("Inconel 625", p, v, d, 80, heat_source="rosenthal")
            g = res["meltPoolGeometry"]
            self.assertEqual(res["processParameters"]["normalizedEnthalpy"], h)
            self.assertEqual((g["depth_um"], g["width_um"], g["length_um"], g["keyholeVaporCavityDepth_um"]),
                             (depth, width, length, cavity), (p, v, d))
            want = "Keyhole" if h >= 13.6 else "Conduction"
            self.assertTrue(g["regime"].startswith(want), (p, v, d, g["regime"]))
            self.assertEqual(g["regimeKeyholeThreshold"], 13.6)
            self.assertEqual(g["regimeMaterialNote"], solver.REGIME_MATERIAL_NOTE_IN625)
            self.assertEqual(res["processWindowMap"]["regimeKeyholeThreshold"], 13.6)
        self.assertEqual(_run("Inconel 718", 200, 800, 80, 80)["meltPoolGeometry"]["regimeKeyholeThreshold"], 20.0)

    def test_in625_grid_labels_follow_the_cut_numbers_pinned_post_p1(self):
        grid = _run("Inconel 625", 195, 800, 100, 80, heat_source="rosenthal")["processWindowMap"]["grid"]
        self.assertEqual([c["normalizedEnthalpy"] for c in grid], PRE_IN625_GRID_ENTHALPY)
        self.assertEqual([c["depth_um"] for c in grid], P1_IN625_GRID_DEPTH_UM)
        got = []
        for c, want in zip(grid, P1_IN625_GRID_REGIME):
            tang = (100.0 / c["width_um"]) ** 2 + (40.0 / c["depth_um"]) ** 2
            if tang > 1.0:
                self.assertEqual(c["regime"], "Lack of Fusion Zone")
                got.append("L")
            elif c["normalizedEnthalpy"] >= 13.6:
                self.assertEqual((c["regime"], c["color"]), ("Keyhole Mode", "#ef4444"))
                got.append("K")
            else:
                self.assertEqual((c["regime"], c["color"]), ("Optimal Conduction", "#10b981"))
                got.append("C")
        self.assertEqual("".join(got), P1_IN625_GRID_REGIME)
        self.assertNotIn("Transition", [c["regime"] for c in grid])
        # the IN625 cut: every non-lack-of-fusion cell with 13.6 <= dH/hs < 20 is Keyhole Mode (shared cut would say Transition)
        self.assertTrue(any(13.6 <= c["normalizedEnthalpy"] < 20.0 and c["regime"] == "Keyhole Mode" for c in grid))

    def test_lane_conditions_at_20c(self):
        # Lane et al. 2020 conditions as served by the app at 20 C: CBM (100 um) keyhole, AMMT (170 um) conduction.
        for p, v, d, fam in ((150, 400, 100, "Keyhole"), (195, 800, 100, "Keyhole"), (195, 1200, 100, "Keyhole"),
                             (137.9, 400, 170, "Conduction"), (179.2, 800, 170, "Conduction")):
            g = _run("Inconel 625", p, v, d, 20, heat_source="rosenthal")["meltPoolGeometry"]
            self.assertTrue(g["regime"].startswith(fam), (p, v, d, g["regime"]))

    def test_public_dataset_mirror(self):
        self.assertEqual(pds.ENTHALPY_KEYHOLE_IN625, solver.ENTHALPY_KEYHOLE_IN625)
        self.assertEqual(pds.REGIME_PARAMETERS["keyholeEnthalpyByAlloy"], {"Inconel 625": 13.6})
        families = {"conduction": "Conduction", "transition": "Transition", "keyhole": "Keyhole"}
        for p, v, d, t0 in ((195, 1200, 100, 80.0), (195, 1200, 100, 20.0), (150, 400, 100, 20.0), (100, 400, 100, 80.0)):
            lab = pds.classify_regime("Inconel 625", p, v, d, t0, None)
            full = _run("Inconel 625", p, v, d, t0)
            self.assertTrue(full["meltPoolGeometry"]["regime"].startswith(families[lab["label"]]), (p, v, d, t0, lab))
            self.assertNotEqual(lab["label"], "transition")


class PorosityDecoupled(unittest.TestCase):
    def test_porosity_labels_decoupled(self):
        # Regime keyhole (24.02 >= 20) but porosity only "Possible" (15 <= 24.02 < 30).
        res = _run("316L Stainless Steel", 200, 800, 70, 80)
        self.assertEqual(res["processParameters"]["normalizedEnthalpy"], 24.02)
        self.assertTrue(res["meltPoolGeometry"]["regime"].startswith("Keyhole Mode"))
        risk = res["defectDiagnostics"]["keyholePorosityRisk"]
        self.assertTrue(risk.startswith("Possible"), risk)
        self.assertIs(res["defectDiagnostics"]["keyholePorosityResolved"], False)
        self.assertIn("legacy screening level", risk)
        self.assertIn("porosity unresolved", risk)
        self.assertIn("not evidence of safety", res["defectDiagnostics"]["keyholePorosityBasis"])
        self.assertIn("independent of the regime threshold", res["defectDiagnostics"]["keyholePorosityBasis"])
        high = _run("Inconel 718", 280, 940, 80, 80)
        self.assertEqual(high["processParameters"]["normalizedEnthalpy"], 30.58)
        self.assertTrue(high["defectDiagnostics"]["keyholePorosityRisk"].startswith("High"))
        low = _run("Inconel 718", 150, 1500, 80, 80)
        self.assertLess(low["processParameters"]["normalizedEnthalpy"], 15.0)
        self.assertTrue(low["defectDiagnostics"]["keyholePorosityRisk"].startswith("Negligible"))

    def test_porosity_band_edges_at_inline_indices(self):
        # The label uses exactly POROSITY_SCREEN_* ; check 14.9 / 15 / 25 / 29.99 / 30 against those constants.
        def band(x):
            if x < solver.POROSITY_SCREEN_NEGLIGIBLE_BELOW:
                return "Negligible"
            return "Possible" if x < solver.POROSITY_SCREEN_HIGH_AT else "High"
        self.assertEqual([band(x) for x in (14.9, 15.0, 25.0, 29.99, 30.0)],
                         ["Negligible", "Possible", "Possible", "Possible", "High"])


class MirrorConstants(unittest.TestCase):
    def test_mirror_constants(self):
        self.assertEqual(pds.ENTHALPY_KEYHOLE, solver.ENTHALPY_KEYHOLE)
        self.assertEqual(pds.ENTHALPY_TRANSITION, solver.ENTHALPY_TRANSITION)
        # (material, P, v, d, preheat, expected family or None = only mirror agreement is checked)
        cases = [("316L Stainless Steel", 100, 1500, 70, 80.0, "Conduction"),
                 ("316L Stainless Steel", 200, 800, 70, 80.0, "Keyhole"),
                 ("316L Stainless Steel", 200, 1000, 70, 80.0, "Keyhole"),
                 ("Inconel 718", 280, 940, 80, 80.0, "Keyhole"),
                 ("Inconel 718", 200, 800, 80, 80.0, "Keyhole"),
                 ("Inconel 718", 150, 1500, 80, 80.0, "Conduction"),
                 ("Ti-6Al-4V", 200, 900, 80, 150.0, "Keyhole"),
                 ("Ti-6Al-4V", 200, 1500, 80, 80.0, None),
                 ("AlSi10Mg", 350, 1300, 80, 80.0, None),
                 ("Inconel 625", 250, 900, 80, 80.0, None)]
        families = {"conduction": "Conduction", "transition": "Transition", "keyhole": "Keyhole"}
        for mat, p, v, d, t0, fam in cases:
            lab = pds.classify_regime(mat, p, v, d, t0, None)
            full = _run(mat, p, v, d, t0)
            self.assertAlmostEqual(lab["normalizedEnthalpy"], full["processParameters"]["normalizedEnthalpy"], delta=0.006)
            mapped = families[lab["label"]]
            self.assertTrue(full["meltPoolGeometry"]["regime"].startswith(mapped), (mat, p, v, lab))
            if fam:
                self.assertEqual(mapped, fam, (mat, p, v, lab))


if __name__ == "__main__":
    unittest.main()
