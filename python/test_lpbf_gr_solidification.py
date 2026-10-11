#!/usr/bin/env python3
"""Self-contained tests for python/lpbf_gr_solidification.py and python/lpbf_cet_screening.py (screening only).

The point-integration pins (sections 5 to 7 of the spec) are numbers copied from the frozen Rosenthal screening solver
at its current revision. They move only with a frozen-solver bump (a planned, reviewed change), never silently.
All CET constants in this file are SYNTHETIC_* test values, not alloy data.
"""
import io
import json
import math
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import lpbf_cet_screening as cet  # noqa: E402
import lpbf_gr_solidification as gr  # noqa: E402
import lpbf_simulation  # noqa: E402
from lpbf_thermal_solver import rosenthal_temperature_C  # noqa: E402

SETTINGS = {"beamDiameter_um": 80, "layer_um": 40, "hatch_um": 110, "preheatTemp_C": 80}
SYNTHETIC_CET = {"a": 1.0e3, "n": 2.0, "N0": 1.0e15}


def req(mode="point", alloy="in718", **extra):
    body = {"mode": mode, "alloyId": alloy, **SETTINGS}
    body.update(extra)
    return body


class RosenthalCenterlineTests(unittest.TestCase):
    def test_hand_checkable_case(self):
        r = gr.rosenthal_centerline_tail(200, 20, 1250, 0, 1.0)
        self.assertAlmostEqual(r["xTail_um"], 1273.2395447351628, delta=1273.24 * 1e-9)
        self.assertAlmostEqual(r["xTail_um"], 200 / (2 * math.pi * 20 * 1250) * 1e6, delta=1e-6)
        self.assertAlmostEqual(r["G_K_m"], 981747.7042468102, delta=981747.7 * 1e-9)
        self.assertAlmostEqual(r["G_K_m"], 2 * math.pi * 20 * 1250 ** 2 / 200, delta=1e-3)
        self.assertEqual(r["R_m_s"], 1.0)
        self.assertAlmostEqual(r["GoverR_K_s_m2"], r["G_K_m"], places=6)
        self.assertAlmostEqual(r["GtimesR_K_s"], r["G_K_m"], places=6)

    def test_cross_check_against_frozen_rosenthal_function(self):
        r = gr.rosenthal_centerline_tail(200, 20, 1250, 0, 1.0)
        x = r["xTail_um"] * 1e-6
        for alpha in (5e-6, 1e-5):
            t = rosenthal_temperature_C(-x, 0, 0, 0.0, 200, 20, 1.0, alpha, 1e-12)
            self.assertAlmostEqual(t, 1250.0, delta=1e-6)
            h = 1e-8
            t_a = rosenthal_temperature_C(-x - h, 0, 0, 0.0, 200, 20, 1.0, alpha, 1e-12)
            t_b = rosenthal_temperature_C(-x + h, 0, 0, 0.0, 200, 20, 1.0, alpha, 1e-12)
            g_fd = (t_b - t_a) / (2 * h)
            self.assertAlmostEqual(g_fd / r["G_K_m"], 1.0, delta=1e-6)

    def test_refusals(self):
        for args in ((0, 20, 1250, 0, 1.0), (200, 0, 1250, 0, 1.0), (200, 20, 1250, 0, 0.0), (200, 20, 100, 100, 1.0),
                     (200, 20, 100, 500, 1.0), (float("nan"), 20, 1250, 0, 1.0)):
            with self.assertRaises(ValueError):
                gr.rosenthal_centerline_tail(*args)


class CetTests(unittest.TestCase):
    def test_critical_gradient_synthetic(self):
        kw = {"a": SYNTHETIC_CET["a"], "n": SYNTHETIC_CET["n"], "n0_m3": SYNTHETIC_CET["N0"]}
        g_col = cet.critical_gradient_K_m(0.1, 0.0066, **kw)
        g_eq = cet.critical_gradient_K_m(0.1, 0.49, **kw)
        self.assertAlmostEqual(g_col / 2.8614177e6, 1.0, delta=1e-7)
        self.assertAlmostEqual(g_eq / 6.130499e5, 1.0, delta=1e-6)
        hand = 10.0 / 3.0 * (4 * math.pi * 1e15 / (3 * -math.log(1 - 0.0066))) ** (1 / 3)
        self.assertAlmostEqual(g_col / hand, 1.0, delta=1e-12)

    def test_band_and_domain(self):
        self.assertEqual(cet.cet_band(3e6, 0.1, SYNTHETIC_CET)["band"], "columnar")
        self.assertEqual(cet.cet_band(1e6, 0.1, SYNTHETIC_CET)["band"], "mixed")
        self.assertEqual(cet.cet_band(5e5, 0.1, SYNTHETIC_CET)["band"], "equiaxed")
        kw = {"a": 1.0, "n": 2.0, "n0_m3": 1e15}
        for phi in (0.0, 1.0, -0.1):
            with self.assertRaises(ValueError):
                cet.critical_gradient_K_m(0.1, phi, **kw)
        for bad in ({"v_m_s": 0.0}, {"a": 0.0}, {"n": 0.0}, {"n0_m3": 0.0}):
            args = {"v_m_s": 0.1, "phi": 0.1, **kw}
            args.update(bad)
            with self.assertRaises(ValueError):
                cet.critical_gradient_K_m(**args)

    def test_cet_block_with_synthetic_override(self):
        blk = cet.cet_block("in718", {"bottom": None, "median": (3e6, 0.1), "tail": (5e5, 0.1)},
                            constants_override=SYNTHETIC_CET)
        self.assertEqual(blk["status"], "available")
        self.assertIsNone(blk["locations"]["bottom"])
        self.assertEqual(blk["locations"]["median"]["band"], "columnar")
        self.assertEqual(blk["locations"]["tail"]["band"], "equiaxed")

    def test_knapp_constants_reproduce_printed_limits(self):
        """Knapp 2019 p. 515 prints G^2 R limits of 1.52e11 (phi 0.0066) and 6.98e9 (phi 0.49) for these constants."""
        kw = {"a": 4.5, "n": 2.0, "n0_m3": 2.65e14}
        for phi, printed in ((0.0066, 1.52e11), (0.49, 6.98e9)):
            # G^n / V = const in the model, so G_crit^2 / V is independent of V.
            for v in (0.05, 0.4):
                g = cet.critical_gradient_K_m(v, phi, **kw)
                self.assertAlmostEqual(g * g / v / printed, 1.0, delta=0.01)
        s = cet.CET_SETS["in718"]["knapp2019"]["constants"]
        self.assertEqual((s["a"]["value"], s["n"]["value"], s["N0"]["value"]), (4.5, 2.0, 2.65e14))

    def test_in718_sets_sourced_and_labelled(self):
        st = cet.cet_constants("in718")
        self.assertEqual(st["status"], "available")
        self.assertEqual([x["id"] for x in st["sets"]], ["knapp2019", "polonsky2020"])
        for entry in st["sets"]:
            self.assertEqual(entry["transferLabel"], "EBM-calibrated, transferred to LPBF")
            self.assertIn("without an LPBF fit", entry["caveat"])
            for key in ("a", "n", "N0"):
                c = entry["constants"][key]
                self.assertTrue(c["verified"] and c["source"] and c["locator"], entry["id"] + "." + key)
        po = {x["id"]: x for x in st["sets"]}["polonsky2020"]["constants"]
        self.assertEqual((po["a"]["value"], po["n"]["value"], po["N0"]["value"]), (1.23e5, 3.13, 5.4e12))
        self.assertEqual(po["a"]["unit"], "K^n s/m")
        self.assertIn("lower", po["N0"]["locator"])

    def test_phi_source_on_every_set(self):
        sets = {x["id"]: x for x in cet.cet_constants("in718")["sets"]}
        for entry in sets.values():
            self.assertTrue(entry["phiSource"])
            self.assertIn("Hunt 1984", entry["phiSource"])
        self.assertEqual(sets["polonsky2020"]["phiSource"],
                         "Hunt 1984 via Knapp 2019 p. 514; not stated by Polonsky 2020")
        self.assertIn("Knapp 2019 p. 514", sets["knapp2019"]["phiSource"])

    def test_equation_verified_only_for_knapp(self):
        sets = cet.CET_SETS["in718"]
        self.assertIs(sets["knapp2019"]["equationVerified"], True)
        self.assertIs(sets["polonsky2020"]["equationVerified"], False)
        self.assertIs(cet.EQUATION_VERIFIED, False)  # Gaumann 2001 itself was not read
        self.assertIsNone(cet.EQUATION_LOCATOR)

    def test_cmsx4_is_reference_only(self):
        ref = cet.cet_constants("in718")["referenceOnly"]
        self.assertEqual((ref["constants"]["n"]["value"], ref["constants"]["a"]["value"]), (3.4, 1.25e6))
        self.assertIn("reference only", ref["label"])
        for entry in cet.cet_constants("in718")["sets"]:
            self.assertNotEqual(entry["constants"]["a"]["value"], 1.25e6)

    def test_registry_honesty_in625_and_unknown(self):
        for alloy in ("in625", "unknown-alloy"):
            st = cet.cet_constants(alloy)
            self.assertEqual(st["status"], "unavailable")
            self.assertTrue(st["reason"])
            self.assertEqual(st["sets"], [])
            blk = cet.cet_block(alloy, {"median": (1e6, 0.1)})
            self.assertEqual(blk["status"], "unavailable")
            self.assertEqual(blk["sets"], {})
        self.assertIn("IN625", cet.cet_constants("in625")["reason"])
        self.assertEqual(cet.CET_SETS["in625"], {})
        self.assertEqual(len(cet.cet_constants("in718")["candidateSources"]), 2)

    def test_cet_block_registry_has_both_sets(self):
        blk = cet.cet_block("in718", {"bottom": None, "median": (3e6, 0.1), "tail": (5e4, 0.1)})
        self.assertEqual(blk["status"], "available")
        self.assertEqual(set(blk["sets"]), {"knapp2019", "polonsky2020"})
        self.assertEqual(blk["locations"], {"bottom": None, "median": None, "tail": None})
        for entry in blk["sets"].values():
            self.assertIsNone(entry["locations"]["bottom"])
            self.assertEqual(entry["locations"]["median"]["band"], "columnar")
            self.assertEqual(entry["transferLabel"], "EBM-calibrated, transferred to LPBF")

    def test_incomplete_set_stays_out(self):
        partial = {"in718": {"x": {"label": "x", "constants": {
            "a": {"value": 1.0, "unit": "", "source": "X", "locator": "Y", "verified": True},
            "n": {"value": None, "unit": "", "source": None, "locator": None, "verified": False},
            "N0": {"value": 1.0, "unit": "", "source": "X", "locator": "Y", "verified": True}}}}}
        with mock.patch.object(cet, "CET_SETS", partial):
            self.assertEqual(cet.cet_constants("in718")["status"], "unavailable")


class TrappingTests(unittest.TestCase):
    PINS = [
        ("in718", 0.0684, 0.31, 0.549419, 0.035377),
        ("in718", 0.0684, 0.23, 0.576072, 0.028673),
        ("in718", 0.014, 0.31, 0.473765, 0.057196),
        ("in718", 0.2318, 0.23, 0.726072, 0.004100),
        ("in718", 0.2318, 0.31, 0.685308, 0.008357),
        ("in625", 0.0684, 0.31, 0.598573, 0.016631),
        ("in625", 0.0684, 0.23, 0.622319, 0.012855),
    ]

    def test_arithmetic(self):
        from lpbf_solidification_segregation import (
            aziz_partition_coefficient, binary_laves_inputs, scheil_eutectic_fraction)
        inp = {a: binary_laves_inputs(a) for a in ("in718", "in625")}
        self.assertEqual(inp["in718"], {"k_e": 0.45, "C_e_wt": 23.1, "Nb_nominal_wt": 5.125})
        self.assertEqual(inp["in625"], {"k_e": 0.51, "C_e_wt": 18.9, "Nb_nominal_wt": 3.65})
        for alloy, expect_f in (("in718", 0.064723), ("in625", 0.034875)):
            i = inp[alloy]
            self.assertAlmostEqual(scheil_eutectic_fraction(i["Nb_nominal_wt"], i["C_e_wt"], i["k_e"]), expect_f, delta=1e-6)
        for alloy, r, vd, k_exp, f_exp in self.PINS:
            i = inp[alloy]
            k = aziz_partition_coefficient(i["k_e"], r, vd)
            self.assertAlmostEqual(k, k_exp, delta=1e-6)
            self.assertAlmostEqual(scheil_eutectic_fraction(i["Nb_nominal_wt"], i["C_e_wt"], k), f_exp, delta=1e-6)

    def test_unknown_alloy_refused(self):
        from lpbf_solidification_segregation import SegregationModelError, binary_laves_inputs
        with self.assertRaises(SegregationModelError):
            binary_laves_inputs("ti6al4v")

    def test_laves_trapping_function(self):
        out = gr.laves_trapping("in625", {"bottom": None, "median": 0.0684, "tail": None})
        self.assertEqual(out["sampledArcUpperBound"]["location"], "median")
        self.assertEqual(out["sampledArcUpperBound"]["f"], 0.0166)
        self.assertIsNone(out["atTail"])
        self.assertIn("not established", out["note"])
        self.assertEqual(gr.laves_trapping("in718", {"median": 0.0})["status"], "unavailable")


class PointIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p718 = gr.run_gr_solidification(req(power_W=285, speed_mm_s=960))
        cls.cond = gr.run_gr_solidification(req(power_W=120, speed_mm_s=1000))
        cls.p625 = gr.run_gr_solidification(req(alloy="in625", power_W=120, speed_mm_s=1000))

    def rel(self, a, b, tol):
        self.assertAlmostEqual(a / b, 1.0, delta=tol)

    def test_in718_keyhole_point(self):
        # P6 containment (2026-10-11): at 285 W / 960 mm/s the served depth comes from the Fabbro keyhole leg, so the
        # thermal block serves null G/R with a reason and the point is unavailable (the pre-P6 pins were G 16981196 /
        # R 0.0943 / cooling 1600948 at the median, from the conduction field on a keyhole-leg depth).
        r = self.p718
        self.assertTrue(r["success"])
        pt = r["point"]
        self.assertEqual(pt["status"], "unavailable")
        self.assertIn("Fabbro keyhole leg", pt["reason"])
        f = pt["front"]
        self.assertIsNone(f["median"])
        self.assertIsNone(f["tail"])
        self.assertIsNone(f["bottom"])
        self.assertIsNone(f["R_range_m_s"])
        self.assertIn("not G_median", f["coolingBasis"])
        self.assertEqual(pt["rosenthalCenterline"]["status"], "unavailable")
        self.assertEqual(pt["cet"]["status"], "unavailable")
        self.assertEqual(pt["laves"]["status"], "unavailable")
        self.assertEqual(pt["morphology"]["basis"], "hunt-g-over-r-screening")
        self.assertEqual(pt["morphology"]["bands"], {"bottom": None, "median": None, "tail": None})
        self.assertIn("not a CET prediction", pt["morphology"]["label"])
        self.assertEqual(r["counts"], {"available": 0, "screening-fallback": 0, "degenerate-floor": 0,
                                       "unavailable": 1, "error": 0})

    def test_response_envelope(self):
        r = self.cond   # P6: the 285/960 point is unavailable (keyhole leg); the envelope is checked on the conduction point
        self.assertEqual(r["schema"], gr.SCHEMA)
        self.assertEqual(r["engine"], gr.ENGINE)
        self.assertEqual(r["evidence"]["kind"], "screening-only")
        self.assertIs(r["evidence"]["experimentalValidation"], False)
        self.assertEqual(r["counts"], {"available": 1, "screening-fallback": 0, "degenerate-floor": 0,
                                       "unavailable": 0, "error": 0})
        self.assertEqual(r["cet"]["constantsStatus"]["status"], "available")
        self.assertEqual(len(r["cet"]["constantsStatus"]["sets"]), 2)
        self.assertIs(r["cet"]["equationVerified"], False)
        self.assertEqual(r["point"]["cet"]["status"], "available")
        self.assertEqual(set(r["point"]["cet"]["sets"]), {"knapp2019", "polonsky2020"})
        self.assertEqual(r["point"]["morphology"]["basis"], "hunt-g-over-r-screening")
        self.assertIs(r["provenance"]["frozenFilesModified"], False)
        self.assertEqual(r["laves"]["V_D_m_s"], [0.23, 0.31])
        self.assertEqual(r["limits"], gr.LIMITS)
        text = json.dumps(r).lower()
        for banned in ("validated", "measured", "predicted grain structure"):
            if banned == "validated":
                # only the negated forms may appear
                self.assertNotIn(" validated ", text.replace("not validated", ""))
            else:
                self.assertNotIn(banned, text)

    def test_conduction_point(self):
        pt = self.cond["point"]
        f = pt["front"]
        # Pinned on the P1 tree (pre-P1: 30629747 / 0.1479, 12380206 / 0.4204, 55295265 / 0.0214).
        self.assertEqual((f["median"]["G_K_m"], f["median"]["R_m_s"]), (27593695.0, 0.1387))
        self.assertEqual((f["tail"]["G_K_m"], f["tail"]["R_m_s"]), (10657436.0, 0.4076))
        self.assertEqual((f["bottom"]["G_K_m"], f["bottom"]["R_m_s"]), (50434919.0, 0.0226))
        self.assertIsNone(pt["regimeNote"])

    def test_in625_point(self):
        r = self.p625
        f = r["point"]["front"]
        # P6 (2026-10-11): the former 195 W / 800 mm/s point now serves null G/R (Fabbro keyhole leg; its P1 pins were
        # 19393766 / 0.1005, 6701551 / 0.3233, 36221417 / 0.0196), so a conduction point (120 W / 1000 mm/s) is pinned.
        self.assertEqual(f["median"]["G_K_m"], 28457032.0)
        self.assertAlmostEqual(f["median"]["R_m_s"], 0.1355, places=12)
        self.assertEqual((f["tail"]["G_K_m"], f["tail"]["R_m_s"]), (11017877.0, 0.3972))
        self.assertEqual((f["bottom"]["G_K_m"], f["bottom"]["R_m_s"]), (52031697.0, 0.0219))
        self.assertEqual(r["materialEvidence"]["provenanceClass"], "legacy-estimated-secondary")
        self.assertIn("not established", r["point"]["laves"]["note"])
        self.assertEqual(r["point"]["cet"]["status"], "unavailable")
        self.assertEqual(r["point"]["cet"]["sets"], {})
        self.assertEqual(r["cet"]["constantsStatus"]["status"], "unavailable")
        self.assertIn("IN625", r["point"]["cet"]["reason"])


class StatusBranchTests(unittest.TestCase):
    """Synthetic thermal dicts (SYNTHETIC: not solver output)."""

    @staticmethod
    def thermal(**kin):
        base = {"thermalGradient_G_K_m": 1.0e7, "solidificationRate_R_m_s": 0.07, "solidificationRate_R_mm_s": 70.0,
                "coolingRate_K_s": 7.0e5, "usedFieldMap": True, "gradientSource": "solidification-front-v1"}
        base.update(kin)
        return {"solidificationKinetics": base,
                "meltPoolGeometry": {"regime": "Conduction Mode", "extentStatus": "computed"},
                "processParameters": {"fieldPower_W": 200.0, "effectiveConductivity_W_mK": 20.0, "normalizedEnthalpy": 10.0}}

    def test_fallback(self):
        b = gr.couple_thermal_block(self.thermal(usedFieldMap=False, gradientSource="tail-length-fallback"), "in718",
                                    preheat_C=80, speed_mm_s=960)
        self.assertEqual(b["status"], "screening-fallback")
        self.assertIsNone(b["front"]["bottom"])
        self.assertIsNone(b["front"]["tail"])
        self.assertTrue(b["reason"])
        self.assertEqual(b["laves"]["sampledArcUpperBound"]["location"], "median")
        self.assertEqual(b["morphology"]["bands"]["median"], "Columnar dendritic (Hunt G/R screening)")

    def test_degenerate(self):
        b = gr.couple_thermal_block(self.thermal(solidificationRate_R_mm_s=0.1, solidificationRate_R_m_s=0.0001,
                                                 coolingRate_K_s=1.0), "in718", preheat_C=80, speed_mm_s=960)
        self.assertEqual(b["status"], "degenerate-floor")
        self.assertIsNone(b["front"]["median"]["GoverR_K_s_m2"])
        self.assertIsNone(b["front"]["median"]["huntBand"])
        self.assertEqual(b["laves"]["status"], "unavailable")
        self.assertEqual(b["cet"]["status"], "unavailable")
        self.assertEqual(set(b["morphology"]["bands"].values()), {None})
        self.assertTrue(b["reason"])

    def test_missing_kinetics(self):
        b = gr.couple_thermal_block({"meltPoolGeometry": {}}, "in718", preheat_C=80, speed_mm_s=960)
        self.assertEqual(b["status"], "unavailable")
        self.assertEqual(b["laves"]["status"], "unavailable")

    def test_synthetic_cet_switches_basis(self):
        t = self.thermal()
        t["solidificationKinetics"]["tail"] = {"x_um": -1000.0, "z_um": 10.0, "G_K_m": 4.0e6, "R_m_s": 0.2}
        t["solidificationKinetics"]["bottom"] = {"x_um": -500.0, "z_um": 80.0, "G_K_m": 2.0e7, "R_m_s": 0.01}
        b = gr.couple_thermal_block(t, "in718", preheat_C=80, speed_mm_s=960, cet_constants_override=SYNTHETIC_CET)
        self.assertEqual(b["cet"]["status"], "available")
        self.assertEqual(b["morphology"]["basis"], "cet-gaumann2001")
        self.assertIn(b["cet"]["locations"]["median"]["band"], ("columnar", "mixed", "equiaxed"))


class MapAndValidationTests(unittest.TestCase):
    def test_small_map_matches_points(self):
        r = gr.run_gr_solidification(req("map", powers=[120, 285], speeds=[800, 960]))
        self.assertTrue(r["success"])
        self.assertEqual(len(r["cells"]), 4)
        self.assertEqual(sum(r["counts"].values()), 4)
        self.assertEqual((r["grid"]["nP"], r["grid"]["nV"], r["grid"]["nCells"]), (2, 2, 4))
        order = [(c["iP"], c["iV"]) for c in r["cells"]]
        self.assertEqual(order, [(0, 0), (0, 1), (1, 0), (1, 1)])
        for c in r["cells"]:
            body = {k: v for k, v in c.items() if k not in ("iP", "iV", "power_W", "speed_mm_s")}
            self.assertEqual(body, gr.evaluate_point("in718", c["power_W"], c["speed_mm_s"], SETTINGS))

    def test_default_grid(self):
        norm, refusal = gr.validate_request(req("map"))
        self.assertIsNone(refusal)
        self.assertEqual(len(norm["powers"]), 11)
        self.assertEqual(len(norm["speeds"]), 11)
        self.assertEqual((norm["powers"][0], norm["powers"][-1]), (60.0, 450.0))
        self.assertEqual((norm["speeds"][0], norm["speeds"][-1]), (275.0, 1500.0))

    def test_refusals(self):
        cases = [
            {k: v for k, v in req(power_W=200, speed_mm_s=800).items() if k != "alloyId"},
            req(alloy="ti6al4v", power_W=200, speed_mm_s=800),
            req("map", alloy="in625"),
            req("map", powers=[200, 100], speeds=[500, 800]),
            req("map", powers=[float(10 + i) for i in range(16)], speeds=[float(100 + i) for i in range(15)]),
            req(power_W=200, speed_mm_s=800, preheatTemp_C=1260),
            req("bogus", power_W=200, speed_mm_s=800),
            req(power_W=0, speed_mm_s=800),
            req(power_W=200, speed_mm_s=20000),
            req(power_W=200, speed_mm_s=800, beamDiameter_um=0),
        ]
        for body in cases:
            r = gr.run_gr_solidification(body)
            self.assertFalse(r["success"], body)
            self.assertEqual(r["errorKind"], "validation", body)
        self.assertIn("IN625", gr.run_gr_solidification(req("map", alloy="in625"))["error"])

    def test_alloy_resolution(self):
        for raw, expect in (("in718", "in718"), ("Inconel 718", "in718"), ("IN625", "in625"), ("inconel 625", "in625"),
                            ("ti6al4v", None), (None, None)):
            self.assertEqual(gr.resolve_gr_alloy(raw), expect, raw)


class MainTests(unittest.TestCase):
    def run_main(self, stdin_text):
        proc = subprocess.run([sys.executable, "-B", str(HERE / "lpbf_gr_solidification.py")], input=stdin_text,
                              capture_output=True, text=True, cwd=str(HERE))
        return proc

    def test_stdin_json(self):
        proc = self.run_main(json.dumps(req(power_W=200, speed_mm_s=900)))
        doc = json.loads(proc.stdout)
        self.assertTrue(doc["success"])
        self.assertEqual(doc["mode"], "point")

    def test_empty_stdin(self):
        proc = self.run_main("")
        doc = json.loads(proc.stdout)
        self.assertFalse(doc["success"])
        self.assertEqual(doc["errorKind"], "validation")

    def test_main_in_process(self):
        buf = io.StringIO()
        with mock.patch("sys.stdin", io.StringIO("not json")), redirect_stdout(buf):
            gr.main()
        self.assertEqual(json.loads(buf.getvalue())["errorKind"], "validation")


class FrozenGuardTests(unittest.TestCase):
    def test_new_modules_not_in_frozen_list(self):
        names = {Path(f).name for f in lpbf_simulation.IMPLEMENTATION_SOURCE_FILES}
        self.assertNotIn("lpbf_gr_solidification.py", names)
        self.assertNotIn("lpbf_cet_screening.py", names)


if __name__ == "__main__":
    unittest.main()
