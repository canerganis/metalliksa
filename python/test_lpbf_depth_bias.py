"""Self-contained pin of the depth-bias note: derived from the committed error-band summary, kernel-aware, and
consistent with the four Lane conditions per kernel. No served depth or regime number changes."""
import json
import re
import unittest
from pathlib import Path

import lpbf_depth_bias as db
from lpbf_thermal_solver import calculate_meltpool_physics

TS_FILE = Path(__file__).resolve().parent.parent / "src" / "utils" / "depthBiasWarning.ts"

# Observed Lane et al. Table 3 mean depths (um) and the served/observed ratio pinned per kernel (this repo, 2026-10-11).
LANE_ROWS = (("CBM-A", 150.0, 400.0, 100.0, 151.53), ("CBM-B", 195.0, 800.0, 100.0, 91.25),
             ("AMMT-A", 137.9, 400.0, 170.0, 42.63), ("AMMT-B", 179.2, 800.0, 170.0, 35.98))
PINNED_RATIO = {
    "rosenthal": (0.686, 0.838, 1.271, 1.276),
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

    def test_ti64_rosenthal_keyhole_is_over_not_under(self):
        w = db.depth_bias_warning("Keyhole Mode (x)", "Ti-6Al-4V", "rosenthal")
        self.assertEqual(w["direction"], db.OVER)
        self.assertNotIn("underestimated", w["text"])

    def test_316l_keyhole_is_under_for_every_kernel(self):
        for kernel in db.KERNEL_LABELS:
            self.assertEqual(db.depth_bias_warning("Keyhole Mode (x)", "316L Stainless Steel", kernel)["direction"], db.UNDER)

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
        pairs = (("DEPTH_BIAS_DIRECTION_TEMPLATE", db.DIRECTION_TEMPLATE), ("DEPTH_BIAS_FEW_TEMPLATE", db.FEW_TEMPLATE),
                 ("DEPTH_BIAS_FLAT_TEMPLATE", db.FLAT_TEMPLATE), ("DEPTH_BIAS_NO_CHECK_TEMPLATE", db.NO_CHECK_TEMPLATE),
                 ("DEPTH_BIAS_BASIS_TEMPLATE", db.BASIS_TEMPLATE), ("DEPTH_BIAS_BASIS_NO_CHECK", db.BASIS_NO_CHECK))
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
