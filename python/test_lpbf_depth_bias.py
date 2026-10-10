"""Self-contained pin of the depth-bias note on the four Lane conditions. No served depth or regime number changes."""
import re
import unittest
from pathlib import Path

import lpbf_depth_bias as db
from lpbf_thermal_solver import calculate_meltpool_physics

TS_FILE = Path(__file__).resolve().parent.parent / "src" / "utils" / "depthBiasWarning.ts"


def _geometry(P, v, d):
    res = calculate_meltpool_physics("Inconel 625", P, v, d)
    return res, res["meltPoolGeometry"]


class LaneConditions(unittest.TestCase):
    def test_cbm_tracks_warn_underestimated(self):
        for P, v in ((150.0, 400.0), (195.0, 800.0)):
            res, g = _geometry(P, v, 100.0)
            self.assertTrue(g["regime"].startswith(("Transition", "Keyhole")), g["regime"])
            w = db.depth_bias_warning(g["regime"], res["material"])
            self.assertEqual(w["direction"], "likely-underestimated")
            self.assertIn("not a validated correction", w["text"])

    def test_ammt_tracks_get_conduction_note(self):
        for P, v in ((137.9, 400.0), (179.2, 800.0)):
            res, g = _geometry(P, v, 170.0)
            self.assertTrue(g["regime"].startswith("Conduction"), g["regime"])
            w = db.depth_bias_warning(g["regime"], res["material"])
            self.assertEqual(w["direction"], "may-overestimate")
            self.assertIn("1.25 to 1.3 times", w["text"])

    def test_stated_ratio_range_brackets_served_over_observed(self):
        # Observed Lane et al. Table 3 mean depths (um); texts must describe the served depth_um, not a research model.
        cases = (("CBM-A", 150.0, 400.0, 100.0, 151.53), ("CBM-B", 195.0, 800.0, 100.0, 91.25),
                 ("AMMT-A", 137.9, 400.0, 170.0, 42.63), ("AMMT-B", 179.2, 800.0, 170.0, 35.98))
        under = re.search(r"about ([\d.]+) to ([\d.]+) times the observed depth", db.UNDER_TEXT)
        over = re.search(r"by about ([\d.]+) to ([\d.]+) times for the served depth", db.OVER_TEXT)
        self.assertIsNotNone(under)
        self.assertIsNotNone(over)
        tol = 0.02
        for name, P, v, d, obs in cases:
            _, g = _geometry(P, v, d)
            ratio = g["depth_um"] / obs
            lo, hi = map(float, (under if name.startswith("CBM") else over).groups())
            self.assertLess(ratio, 1.0) if name.startswith("CBM") else self.assertGreater(ratio, 1.0)
            self.assertTrue(lo - tol <= ratio <= hi + tol, (name, ratio, lo, hi))

    def test_attach_touches_nothing_else(self):
        res, g = _geometry(150.0, 400.0, 100.0)
        before = dict(g)
        db.attach_depth_bias_warning(res)
        after = res["meltPoolGeometry"]
        self.assertEqual({k: v for k, v in after.items() if k != "depthBiasWarning"}, before)

    def test_no_note_for_other_alloy_conduction_and_unknown(self):
        self.assertIsNone(db.depth_bias_warning("Conduction Mode (Stable)", "Inconel 718")["direction"])
        self.assertIsNone(db.depth_bias_warning(None, None)["direction"])
        self.assertEqual(db.depth_bias_warning("Keyhole Mode (x)", "Inconel 718")["direction"], "likely-underestimated")

    def test_no_dashes_in_text(self):
        for t in (db.UNDER_TEXT, db.OVER_TEXT, db.UNDER_BASIS, db.OVER_BASIS):
            self.assertNotRegex(t, "[–—]")
            self.assertNotIn(" - ", t)


class TsMirror(unittest.TestCase):
    def test_texts_equal_typescript(self):
        src = TS_FILE.read_text(encoding="utf-8")
        for const, py in (("DEPTH_BIAS_UNDER_TEXT", db.UNDER_TEXT), ("DEPTH_BIAS_UNDER_BASIS", db.UNDER_BASIS),
                          ("DEPTH_BIAS_OVER_TEXT", db.OVER_TEXT), ("DEPTH_BIAS_OVER_BASIS", db.OVER_BASIS)):
            m = re.search(r"export const " + const + r" =\s*((?:\"(?:[^\"\\]|\\.)*\"\s*\+?\s*)+);", src)
            self.assertIsNotNone(m, const)
            ts = "".join(re.findall(r"\"((?:[^\"\\]|\\.)*)\"", m.group(1)))
            self.assertEqual(ts, py, const)


if __name__ == "__main__":
    unittest.main()
