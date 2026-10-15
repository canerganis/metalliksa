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
    def test_source_set_algebra_reproduced(self):
        for entry in cet.CET_SETS["in718"].values():
            a, n, n0 = (entry["constants"][key]["value"] for key in ("a", "n", "N0"))
            for v in (0.05, 0.4):
                for phi in (cet.PHI_COLUMNAR, cet.PHI_EQUIAXED):
                    g = cet.critical_gradient_K_m(v, phi, a=a, n=n, n0_m3=n0)
                    rhs = a * ((-4 * math.pi * n0 / (3 * math.log(1-phi)))**(1/3) / (n+1))**n
                    self.assertAlmostEqual((g**n / v) / rhs, 1.0, places=12)

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
        blk = cet.cet_block("in718", {"median": (3e6, 0.1)}, constants_override=SYNTHETIC_CET)
        self.assertEqual(blk["status"], "unavailable")
        self.assertEqual(blk["reasons"][0]["code"], "outside-source-model-domain")

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
        self.assertNotIn("equationVerified", cet.criterion_view())
        self.assertEqual(cet.criterion_view()["sourceChecks"]["equationRead"]["status"], "not-read")
        sets = {x["id"]: x for x in cet.cet_constants("in718")["sets"]}
        self.assertEqual(sets["knapp2019"]["sourceChecks"]["printedLimitComparison"]["status"], "agrees")
        self.assertEqual(sets["polonsky2020"]["sourceChecks"]["printedLimitComparison"]["status"], "not-available")

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
        self.assertEqual(len(cet.cet_constants("in718")["sets"]), 2)
        block = cet.cet_block("in718", {"median": (3e6, 0.1)})
        self.assertEqual(block["status"], "unavailable")
        self.assertEqual(block["sets"], {})

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
    def test_all_five_alloys_project_null_front_without_bypass(self):
        from quantity_envelope import envelope_problems
        for alloy in gr.SUPPORTED:
            out = gr.run_gr_solidification(req(alloy=alloy, power_W=150, speed_mm_s=1200))
            self.assertTrue(out["success"], out)
            self.assertEqual(out["schema"], "lpbf-gr-solidification-2")
            point = out["point"]
            self.assertEqual(point["status"], "unavailable")
            self.assertEqual(envelope_problems(point), [])
            self.assertNotIn("rosenthalCenterline", point)
            self.assertNotIn("morphology", point)
            self.assertEqual(point["cet"]["quantities"]["class"]["reasons"][0]["code"], "outside-source-model-domain")
            self.assertEqual(point["laves"]["quantities"]["fraction"]["reasons"][0]["code"], "parent-unavailable")

    def test_map_counts_and_error_cell(self):
        out = gr.run_gr_solidification(req(mode="map", powers=[100, 150], speeds=[960, 1200]))
        self.assertEqual(out["grid"]["nCells"], 4)
        self.assertEqual(out["counts"]["unavailable"], 4)
        with mock.patch.object(gr, "_thermal", side_effect=ValueError("synthetic solver failure")):
            failed = gr.run_gr_solidification(req(power_W=150, speed_mm_s=1200))["point"]
        self.assertEqual(failed["status"], "failed")
        self.assertTrue(all(q["status"] == "failed" for q in failed["front"]["quantities"].values()))
        self.assertEqual(failed["front"]["quantities"]["thermalGradient"]["reasons"][0]["code"], "solver-error")

    def test_invalid_requests_and_aliases(self):
        for bad in ({}, req(alloy="unknown", power_W=150, speed_mm_s=1200),
                    req(power_W=0, speed_mm_s=1200), req(power_W=150, speed_mm_s=True),
                    req(mode="map", powers=[100]*30, speeds=[100]*30)):
            self.assertFalse(gr.run_gr_solidification(bad)["success"])
        self.assertEqual(gr.resolve_gr_alloy("Ti-6Al-4V"), "ti6al4v")
        self.assertEqual(gr.resolve_gr_alloy("Inconel 625"), "in625")
        self.assertIsNone(gr.resolve_gr_alloy("IN718 and Ti64"))
