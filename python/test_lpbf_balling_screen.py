"""Balling / track-instability screen (lpbf_defect_diagnostics.balling_screen).

The screen replaced the frozen steady-Rosenthal L/W > 3.8 flag on top of Wave B (f3ba9896): Eagar-Tsai
liquidus L/W, Moderate > pi*sqrt(3/2) (Yadroitsev et al. 2010 Eq. 13 bound, Gusarov et al. 2007 mechanism, advisory).
The former High band (> 5.5, empirical, Hofmann 316L, in-sample) was removed in P7b (2026-10-14): its edge survives
only as the recorded evidence bin HOFMANN_EVIDENCE_LW_EDGES[2]. These tests are self-contained: the calibration
counts are recomputed from the committed Wave B dataset comparison record.
"""
import contextlib
import io
import json
import math
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from lpbf_defect_diagnostics import (  # noqa: E402
    BALLING_LW_MODERATE, BALLING_SCREEN_EVIDENCE, BALLING_SCREEN_MODEL_ID, HOFMANN_EVIDENCE_LW_EDGES,
    balling_high_band_applicable, balling_screen, defect_diagnostics)

# The recorded Hofmann evidence edge (not a served band since P7b).
BALLING_LW_HIGH = HOFMANN_EVIDENCE_LW_EDGES[2]
from lpbf_thermal_solver import calculate_meltpool_physics  # noqa: E402

RECORD = os.path.join(HERE, "..", "docs", "LPBF_DATASET_COMPARISON_2026-10-07_waveb-physics.json")


def _run(material, P, v, d, preheat=80.0, heat_source=None):
    with contextlib.redirect_stdout(io.StringIO()):
        return calculate_meltpool_physics(material, P, v, d, preheat, 40.0, 100.0, heat_source=heat_source)


class ScreenFunction(unittest.TestCase):
    def test_exported_provenance_drops_unverified_2010_citation(self):
        # The Gusarov & Smurov 2010 paper was never read; no exported provenance title may credit it.
        screen = balling_screen(500.0, 100.0, 40.0, "computed")
        result = defect_diagnostics(100.0, 150.0, 1000.0, 50.0, 20.0, balling=screen)
        titles = [entry["title"] for entry in result["provenance"]]
        self.assertTrue(any("Yadroitsev et al. (2010) Eq. 13" in t and "Gusarov et al. (2007)" in t for t in titles), titles)
        self.assertFalse(any("Gusarov & Smurov" in t for t in titles), titles)

    def test_thresholds(self):
        self.assertAlmostEqual(BALLING_LW_MODERATE, 3.8476, places=4)  # pi*sqrt(3/2)
        s = balling_screen(500.0, 100.0, 40.0, "computed")
        self.assertEqual(s["moderateThreshold"], 3.848)
        # P7b (2026-10-14): no High band; the served threshold is null and the evidence edge stays 5.5.
        self.assertIsNone(s["highThreshold"])
        self.assertIn("Yadroitsev et al. 2010", s["basis"])
        self.assertIn("Gusarov et al. 2007", s["basis"])
        self.assertIn("no High band since P7b", s["basis"])
        self.assertEqual(BALLING_LW_HIGH, 5.5)

    def test_bands_and_boundaries(self):
        # P7b: the former High band (> 5.5) is Moderate for every alloy and every unlabelled call.
        cases = [(384.7, "stable"), (385.0, "moderate"), (550.0, "moderate"), (550.1, "moderate")]
        for L, band in cases:
            s = balling_screen(L, 100.0, 40.0, "computed")
            self.assertEqual(s["band"], band, L)
            self.assertEqual(s["modelId"], BALLING_SCREEN_MODEL_ID)
            self.assertFalse(s["experimentalValidation"])
            self.assertFalse(s["highBandApplicable"])
            json.dumps(s, allow_nan=False)
        self.assertEqual(balling_screen(600.0, 100.0, 40.0, "computed")["verdictEffect"], "advisory")
        self.assertEqual(balling_screen(600.0, 100.0, 40.0, "computed", material_name="Inconel 718")["band"], "moderate")
        self.assertEqual(balling_screen(600.0, 100.0, 40.0, "computed", material_name="316L Stainless Steel")["band"],
                         "moderate")
        self.assertFalse(balling_high_band_applicable("316L Stainless Steel"))
        self.assertFalse(balling_high_band_applicable(None))
        self.assertEqual(balling_screen(450.0, 100.0, 40.0, "computed")["verdictEffect"], "advisory")
        self.assertEqual(balling_screen(300.0, 100.0, 40.0, "computed")["verdictEffect"], "none")

    def test_no_depth_exemption(self):
        # The D/W < 1.2 clause of the first draft is not applied: a deep pool above 5.5 is still Moderate (P7b).
        self.assertEqual(balling_screen(600.0, 100.0, 250.0, "computed")["band"], "moderate")
        self.assertEqual(balling_screen(600.0, 100.0, 250.0, "computed")["hofmannBalledFractionInBand"], "69/71")

    def test_unresolved_extent_has_no_band(self):
        for status in ("width-floor-applied", "heuristic-width-fallback", "search-box-limited", None):
            s = balling_screen(900.0, 100.0, 40.0, status)
            self.assertIsNone(s["band"])
            self.assertIn("not resolved", s["reason"])
        self.assertIsNone(balling_screen(900.0, 0.0, 40.0, "computed")["band"])

    def test_defect_diagnostics_only_bands_with_the_screen(self):
        plain = defect_diagnostics(100, 150, 1000, 50, 20)
        self.assertIsNone(plain["balling"]["risk"])
        self.assertEqual(plain["balling"]["lengthToWidth"], 10.0)
        for L, risk in ((300.0, "low"), (450.0, "moderate"), (600.0, "moderate")):
            r = defect_diagnostics(100, 50, 1000, 50, 20, balling=balling_screen(L, 100.0, 40.0, "computed"))
            self.assertEqual(r["balling"]["risk"], risk)
            # The given geometry's L/W is still reported, the band comes from the Eagar-Tsai screen.
            self.assertEqual(r["balling"]["lengthToWidth"], 10.0)
        with self.assertRaises(ValueError):
            defect_diagnostics(100, 50, 1000, 50, 20, balling={"band": "high"})


class ThermalSolverWiring(unittest.TestCase):
    def test_companion_equals_eagar_tsai_run(self):
        for material, P, v, d in (("Inconel 718", 280, 940, 80), ("Ti-6Al-4V", 200, 1000, 80),
                                  ("316L Stainless Steel", 60, 2000, 50)):
            et = _run(material, P, v, d, heat_source="eagar-tsai")
            g = et["meltPoolGeometry"]
            for hs in ("rosenthal", "goldak"):
                s = _run(material, P, v, d, heat_source=hs)["defectDiagnostics"]["ballingScreen"]
                self.assertEqual(s, et["defectDiagnostics"]["ballingScreen"], (material, hs))
                self.assertEqual(s["extentStatus"], g["extentStatus"])
                if g["extentStatus"] == "computed":
                    self.assertAlmostEqual(s["lengthToWidth"], g["length_um"] / g["width_um"], delta=2e-3)

    def test_reference_cases(self):
        # (material, P, v, d, preheat) -> (band, Eagar-Tsai L/W) at the post-Wave-B geometry.
        # P7b (2026-10-14): the authority absorptivity and the melting-point / kernel-ledger k and cp shorten the
        # Eagar-Tsai pool, so the L/W of every case falls (P7a values 5.016, 5.068, 5.192, 4.064, 3.636).
        cases = {
            ("Inconel 718", 280, 940, 80, 80.0): ("stable", 3.542),
            ("Inconel 718", 285, 960, 67, 23.5): ("stable", 3.600),  # NIST AMB2022-03 continuous track
            ("Ti-6Al-4V", 280, 1200, 80, 80.0): ("moderate", 4.345),
            ("Ti-6Al-4V", 200, 1000, 80, 80.0): ("stable", 3.424),
            ("316L Stainless Steel", 200, 800, 80, 80.0): ("stable", 2.756),
        }
        for (m, P, v, d, pre), (band, lw) in cases.items():
            r = _run(m, P, v, d, pre)
            s = r["defectDiagnostics"]["ballingScreen"]
            self.assertEqual(s["band"], band, (m, P, v))
            self.assertAlmostEqual(s["lengthToWidth"], lw, delta=0.002)
            self.assertTrue(r["defectDiagnostics"]["ballingInstabilityRisk"].startswith(band.capitalize()))
            self.assertEqual(r["geometricDefectScreen"]["balling"]["screen"], s)
        # The Rosenthal L/W of the first case no longer drives balling (P1, 2026-10-11: 5.18 with the flat-absorptivity,
        # latent-free field; before P1 it was above 7; P7b, 2026-10-14: 3.71 with the melting-point k / cp).
        ros_lw = _run("Inconel 718", 280, 940, 80)["meltPoolGeometry"]["aspectRatio_L_over_W"]
        self.assertAlmostEqual(ros_lw, 3.71, delta=0.01)
        self.assertNotEqual(_run("Inconel 718", 280, 940, 80)["defectDiagnostics"]["ballingScreen"]["kernel"], "rosenthal")

    def test_process_map_has_no_balling_zone(self):
        r = _run("Inconel 718", 280, 940, 80)
        regimes = {pt["regime"] for pt in r["processWindowMap"]["grid"]}
        self.assertNotIn("Balling Instability Zone", regimes)
        self.assertIn("operating point only", r["processWindowMap"]["ballingNote"])

    def test_transient_path_has_no_pi_rule(self):
        with open(os.path.join(HERE, "lpbf_simulation.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertNotIn("balling (screening)", src)
        self.assertNotIn("math.pi*w", src)


@unittest.skipUnless(os.path.isfile(RECORD), "Wave B dataset comparison record not present")
class CalibrationEvidence(unittest.TestCase):
    """The evidence constants are the counts on the committed Wave B record (Hofmann 316L, Eagar-Tsai)."""

    @classmethod
    def setUpClass(cls):
        with open(RECORD, encoding="utf-8") as fh:
            rec = json.load(fh)
        cls.rec = rec
        cls.rows = [r for r in rec["rows"] if r["dataset"] == "hofmann-316l-2026"]

    def _lw(self, r):
        p = r["predictions"]["eagar-tsai"]
        return p["length_um"] / p["width_um"]

    def test_record_revision(self):
        self.assertEqual(self.rec["implementationHash"], BALLING_SCREEN_EVIDENCE["geometryImplementationHash"])
        self.assertEqual(len(self.rows), 677)
        self.assertTrue(all(r["predictions"]["eagar-tsai"]["extentStatus"] == "computed" for r in self.rows))

    def test_counts(self):
        pos = [r for r in self.rows if r["measured"]["balling"]]
        neg = [r for r in self.rows if not r["measured"]["balling"]]
        self.assertEqual((len(pos), len(neg)), (216, 461))
        for thr, key in ((BALLING_LW_HIGH, "highThresholdCounts"), (BALLING_LW_MODERATE, "moderateThresholdCounts")):
            tp = sum(self._lw(r) > thr for r in pos)
            fp = sum(self._lw(r) > thr for r in neg)
            self.assertEqual((tp, fp), (BALLING_SCREEN_EVIDENCE[key]["truePositive"],
                                        BALLING_SCREEN_EVIDENCE[key]["falsePositive"]), key)
        wins = sum((self._lw(a) > self._lw(b)) + 0.5 * (self._lw(a) == self._lw(b)) for a in pos for b in neg)
        self.assertAlmostEqual(wins / (len(pos) * len(neg)), BALLING_SCREEN_EVIDENCE["aucEagarTsaiLW"], places=3)

    def test_band_fractions(self):
        edges = {"stable (<= 3.85)": (-math.inf, BALLING_LW_MODERATE),
                 "moderate (3.85-4.5]": (BALLING_LW_MODERATE, 4.5),
                 "moderate (4.5-5.5]": (4.5, BALLING_LW_HIGH),
                 "high (> 5.5)": (BALLING_LW_HIGH, math.inf)}
        for name, (lo, hi) in edges.items():
            band = [r for r in self.rows if lo < self._lw(r) <= hi]
            got = f"{sum(r['measured']['balling'] for r in band)}/{len(band)}"
            self.assertEqual(got, BALLING_SCREEN_EVIDENCE["bandBalledFraction"][name], name)


if __name__ == "__main__":
    unittest.main()
