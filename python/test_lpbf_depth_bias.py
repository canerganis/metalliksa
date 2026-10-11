"""Self-contained pin of the depth-bias note: derived from the committed error-band summary, kernel-aware, and
consistent with the four Lane conditions per kernel. No served depth or regime number changes."""
import json
import re
import unittest
from pathlib import Path

import lpbf_depth_bias as db
from lpbf_thermal_solver import calculate_meltpool_physics

TS_FILE = Path(__file__).resolve().parent.parent / "src" / "utils" / "depthBiasWarning.ts"

# Observed Lane et al. Table 3 mean depths (um) and the served/observed ratio pinned per kernel (this repo, P1 bump
# 2026-10-11; the Rosenthal row before P1 was 0.686, 0.838, 1.271, 1.276: CBM moves further under, AMMT further over).
LANE_ROWS = (("CBM-A", 150.0, 400.0, 100.0, 151.53), ("CBM-B", 195.0, 800.0, 100.0, 91.25),
             ("AMMT-A", 137.9, 400.0, 170.0, 42.63), ("AMMT-B", 179.2, 800.0, 170.0, 35.98))
PINNED_RATIO = {
    "rosenthal": (0.446, 0.612, 1.450, 1.437),
    "eagar-tsai": (0.424, 0.564, 1.248, 1.145),
    "goldak": (0.461, 0.635, 1.494, 1.440),
}


def _geometry(P, v, d, kernel):
    res = calculate_meltpool_physics("Inconel 625", P, v, d, heat_source=kernel)
    return res, res["meltPoolGeometry"]


class LaneConditionsPerKernel(unittest.TestCase):
    def test_ratios_and_directions(self):
        for kernel, pins in PINNED_RATIO.items():
            for (name, P, v, d, obs), pin in zip(LANE_ROWS, pins):
                res, g = _geometry(P, v, d, kernel)
                self.assertAlmostEqual(g["depth_um"] / obs, pin, delta=0.01, msg=(kernel, name))
                self.assertEqual(res["processParameters"]["heatSource"], kernel)
                idx = res["processParameters"]["normalizedEnthalpy"]
                w = db.depth_bias_warning(g["regime"], res["material"], kernel, idx)
                if name.startswith("CBM"):
                    # The IN625 served label is Keyhole here (cut 13.6) but the error bands class by the 15 / 20 edges.
                    self.assertTrue(g["regime"].startswith("Keyhole"), g["regime"])
                    self.assertEqual(db.enthalpy_class(idx), "transition", (name, idx))
                    self.assertIn("cell Inconel 625 / " + kernel + " / transition", w["basis"])
                    self.assertLess(pin, 1.0)
                    self.assertEqual(w["direction"], db.UNDER, (kernel, name))
                else:
                    self.assertTrue(g["regime"].startswith("Conduction"), g["regime"])
                    self.assertEqual(db.enthalpy_class(idx), "conduction", (name, idx))
                    self.assertGreater(pin, 1.0)
                    self.assertEqual(w["direction"], db.OVER, (kernel, name))
                self.assertIn(db.KERNEL_LABELS[kernel], w["text"])
                self.assertIn("not a validated correction", w["text"])

    def test_attach_uses_served_kernel_and_touches_nothing_else(self):
        res, g = _geometry(150.0, 400.0, 100.0, "goldak")
        before = dict(g)
        db.attach_depth_bias_warning(res)
        after = res["meltPoolGeometry"]
        self.assertEqual({k: v for k, v in after.items() if k != "depthBiasWarning"}, before)
        self.assertIn("Goldak", after["depthBiasWarning"]["text"])
        self.assertIn("transition band", after["depthBiasWarning"]["text"])

    def test_lane_cbm_c_label_and_index_class_disagree_so_no_direction(self):
        # Lane CBM-C: 195 W, 1200 mm/s, 100 um, default preheat. Served Keyhole Mode (IN625 cut 13.6), index 13.94
        # (conduction by the 15 edge), measured underpredicted: the note must not claim a direction.
        for kernel in db.KERNEL_LABELS:
            res, g = _geometry(195.0, 1200.0, 100.0, kernel)
            idx = res["processParameters"]["normalizedEnthalpy"]
            self.assertTrue(g["regime"].startswith("Keyhole"), g["regime"])
            self.assertEqual(db.enthalpy_class(idx), "conduction", idx)
            w = db.depth_bias_warning(g["regime"], res["material"], kernel, idx)
            self.assertIsNone(w["direction"], kernel)
            self.assertIn("disagree", w["text"])
            self.assertIn("(keyhole)", w["text"])
            self.assertIn("conduction, dH/hs", w["text"])
            self.assertIn(f"dH/hs {idx:g}", w["text"])
            self.assertIn("No direction is given", w["text"])
            self.assertIn("n=18", w["text"]) if kernel == "rosenthal" else None  # bands at c61ab6a8 (P1): n=16 -> 18
            db.attach_depth_bias_warning(res)
            self.assertIsNone(res["meltPoolGeometry"]["depthBiasWarning"]["direction"])
        # Adjacent classes (IN625 keyhole label, transition index) keep the transition direction.
        self.assertEqual(db.depth_bias_warning("Keyhole Mode", "Inconel 625", "rosenthal", 17.1)["direction"], db.UNDER)
        # Context-free no-cell variant.
        w = db.depth_bias_warning("Keyhole Mode", "Inconel 718", "goldak", 10.0)
        self.assertIsNone(w["direction"])
        self.assertIn("disagree", w["text"])
        self.assertNotRegex(w["text"], "[\u2013\u2014]")

    def test_class_follows_index_edges_not_served_label(self):
        # CBM C style index 13.94 is below the 15 edge: conduction by the bands, whatever the served IN625 label says.
        self.assertEqual(db.enthalpy_class(13.94), "conduction")
        self.assertEqual(db.enthalpy_class(14.99), "conduction")
        self.assertEqual(db.enthalpy_class(15.0), "transition")
        self.assertEqual(db.enthalpy_class(19.99), "transition")
        self.assertEqual(db.enthalpy_class(20.0), "keyhole")
        self.assertEqual(db.TABLE["edges"], [15.0, 20.0])
        keyhole_label = "Keyhole Mode (x)"
        for idx, cls in ((13.94, "conduction"), (17.1, "transition"), (18.6, "transition")):
            w = db.depth_bias_warning(keyhole_label, "Inconel 625", "rosenthal", idx)
            self.assertIn(f"/ rosenthal / {cls}", w["basis"], idx)
            self.assertIn("Band class from the enthalpy index", w["basis"])
        # No index: falls back to the served label.
        w = db.depth_bias_warning(keyhole_label, "Inconel 625", "rosenthal")
        self.assertIn("/ rosenthal / keyhole", w["basis"])
        self.assertNotIn("Band class from the enthalpy index", w["basis"])
        self.assertEqual(db.depth_bias_warning(keyhole_label, "Inconel 625", "rosenthal", float("nan"))["basis"], w["basis"])
        # An index alone classes the track even when the label is unknown.
        self.assertIsNotNone(db.depth_bias_warning(None, "Inconel 625", "rosenthal", 17.0)["text"])


class SummaryDerived(unittest.TestCase):
    def test_table_equals_summary(self):
        summary = json.loads(db.SUMMARY_PATH.read_text(encoding="utf-8"))
        self.assertEqual(db.TABLE, db.build_cells(summary))
        self.assertTrue(db.TABLE["cells"])

    def test_ti64_rosenthal_keyhole_has_no_clear_direction_after_p1(self):
        # Bands at c61ab6a8 (P1, 2026-10-11): the Rosenthal keyhole cell equals the Eagar-Tsai and Goldak cell
        # (-0.047, n=80: every kernel serves the same Fabbro leg there), below the 0.05 direction floor. Before P1 the
        # Rosenthal cell was +0.284 (OVER).
        w = db.depth_bias_warning("Keyhole Mode (x)", "Ti-6Al-4V", "rosenthal")
        self.assertIsNone(w["direction"])
        self.assertIn("No clear depth bias direction", w["text"])
        self.assertNotIn("underestimated", w["text"])
        self.assertEqual(db.TABLE["cells"]["Ti-6Al-4V|rosenthal|keyhole"], db.TABLE["cells"]["Ti-6Al-4V|eagar-tsai|keyhole"])

    def test_316l_keyhole_is_under_for_every_kernel(self):
        for kernel in db.KERNEL_LABELS:
            w = db.depth_bias_warning("Keyhole Mode (x)", "316L Stainless Steel", kernel)
            self.assertEqual(w["direction"], db.UNDER)
            self.assertTrue(w["text"].endswith(db.P1_UNDER_NOTE), kernel)

    def test_p1_notes_only_where_the_bump_moved_the_cell(self):
        # UNDER in the transition and keyhole bands carries the absorptance note (every kernel); Rosenthal OVER in the
        # conduction band carries the latent-heat note; other OVER cells carry neither.
        self.assertTrue(db.depth_bias_warning("Transition Mode", "Inconel 625", "goldak")["text"].endswith(db.P1_UNDER_NOTE))
        ro = db.depth_bias_warning("Conduction Mode (Stable)", "Inconel 625", "rosenthal")
        self.assertEqual(ro["direction"], db.OVER)
        self.assertTrue(ro["text"].endswith(db.P1_OVER_NOTE))
        gk = db.depth_bias_warning("Conduction Mode (Stable)", "Inconel 625", "goldak")
        self.assertEqual(gk["direction"], db.OVER)
        self.assertNotIn("2026-10-11", gk["text"])
        for t in (db.P1_UNDER_NOTE, db.P1_OVER_NOTE):
            self.assertNotRegex(t, "[–—]")
            self.assertNotIn(" - ", t)

    def test_few_tracks_and_missing_cells_give_no_direction(self):
        few = db.depth_bias_warning("Keyhole Mode (x)", "Inconel 625", "rosenthal")  # n=1
        self.assertIsNone(few["direction"])
        self.assertIn("Too few held-out tracks", few["text"])
        none = db.depth_bias_warning("Conduction Mode (Stable)", "Inconel 718", "goldak")
        self.assertIsNone(none["direction"])
        self.assertIn("No held-out check for this alloy and kernel", none["text"])

    def test_unknown_inputs_give_no_text(self):
        self.assertIsNone(db.depth_bias_warning(None, None, None)["text"])
        self.assertIsNone(db.depth_bias_warning("Transition Mode", "Inconel 625", None)["text"])

    def test_no_dashes_in_any_text(self):
        for kernel in db.KERNEL_LABELS:
            for alloy in ("316L Stainless Steel", "Inconel 625", "Inconel 718", "Ti-6Al-4V"):
                for regime in ("Conduction Mode", "Transition Mode", "Keyhole Mode"):
                    w = db.depth_bias_warning(regime, alloy, kernel)
                    for t in (w["text"], w["basis"]):
                        self.assertNotRegex(t, "[–—]")
                        self.assertNotIn(" - ", t.replace("pred / meas - 1", ""))
        for t in (db.DIRECTION_TEMPLATE, db.FEW_TEMPLATE, db.FLAT_TEMPLATE, db.NO_CHECK_TEMPLATE):
            self.assertNotRegex(t, "[–—]")


class TsMirror(unittest.TestCase):
    def test_templates_and_table_equal_typescript(self):
        src = TS_FILE.read_text(encoding="utf-8")
        pairs = (("DEPTH_BIAS_DISAGREE_TEMPLATE", db.DISAGREE_TEMPLATE),
                 ("DEPTH_BIAS_DISAGREE_NO_CELL_TEMPLATE", db.DISAGREE_NO_CELL_TEMPLATE),
                 ("DEPTH_BIAS_DIRECTION_TEMPLATE", db.DIRECTION_TEMPLATE), ("DEPTH_BIAS_FEW_TEMPLATE", db.FEW_TEMPLATE),
                 ("DEPTH_BIAS_FLAT_TEMPLATE", db.FLAT_TEMPLATE), ("DEPTH_BIAS_NO_CHECK_TEMPLATE", db.NO_CHECK_TEMPLATE),
                 ("DEPTH_BIAS_BASIS_TEMPLATE", db.BASIS_TEMPLATE), ("DEPTH_BIAS_BASIS_NO_CHECK", db.BASIS_NO_CHECK),
                 ("DEPTH_BIAS_P1_UNDER_NOTE", db.P1_UNDER_NOTE), ("DEPTH_BIAS_P1_OVER_NOTE", db.P1_OVER_NOTE))
        for const, py in pairs:
            m = re.search(r"export const " + const + r" =\s*((?:\"(?:[^\"\\]|\\.)*\"\s*\+?\s*)+);", src)
            self.assertIsNotNone(m, const)
            ts = "".join(re.findall(r"\"((?:[^\"\\]|\\.)*)\"", m.group(1)))
            self.assertEqual(ts, py, const)
        cells = {m.group(1): [float(m.group(2)), int(m.group(3)), int(m.group(4))]
                 for m in re.finditer(r'^\s*"([^"]+\|[^"]+\|[^"]+)": \[(-?[\d.]+), (\d+), (\d+)\],$', src, re.M)}
        self.assertEqual(cells, db.TABLE["cells"])
        self.assertIn(f'DEPTH_BIAS_BANDS_ID = "{db.TABLE["bandsId"]}"', src)
        self.assertIn(f"MIN_N_FOR_DIRECTION = {db.MIN_N_FOR_DIRECTION};", src)
        lo, hi = db.TABLE["edges"]
        self.assertIn(f"DEPTH_BIAS_ENTHALPY_EDGES: readonly [number, number] = [{lo}, {hi}];", src)
        m = re.search(r"export const DEPTH_BIAS_CLASS_BASIS =\s*((?:\"(?:[^\"\\]|\\.)*\"\s*\+?\s*)+);", src)
        self.assertIsNotNone(m)
        self.assertEqual("".join(re.findall(r"\"((?:[^\"\\]|\\.)*)\"", m.group(1))), db.CLASS_BASIS)


if __name__ == "__main__":
    unittest.main()
