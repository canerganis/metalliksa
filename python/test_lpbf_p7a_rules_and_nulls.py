"""P7a planned bump (docs/research/SPEC_p7a_rules_and_nulls_2026-10-11.md): sourced verdict rules, advisories, nulls.

Self-contained: every fixture below is synthetic (hand-built thermal dicts or the served solver on synthetic process
inputs); no measured data is read. The geometry pins (REV0_PINS) were recorded at REV0 = ddd0b5ba (the P6 containment
head 09eccb8b, fingerprint 807d74b3..., plus the two cherry-picked G1 fixes that touch no manifest file) by running
calculate_meltpool_physics on the listed (alloy, P, v, beam, kernel) points at 80 C preheat, 40 um layer, 100 um
hatch, IR; they are served solver numbers on synthetic inputs, not measurements. P7a must keep them bit equal.

    python -B -m unittest test_lpbf_p7a_rules_and_nulls
"""
import copy
import hashlib
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import lpbf_build_job_solver as bj  # noqa: E402
import lpbf_thermal_solver as solver  # noqa: E402
import solidification_front as sf  # noqa: E402
from lpbf_defect_diagnostics import balling_screen  # noqa: E402
from marangoni_screening import marangoni_screening  # noqa: E402

# ---------------------------------------------------------------------------------------------------------------
# 1. Geometry bit equal (pinned at REV0; alloy|P|v|beam|kernel; W, D, L, cavity, dH/hs, regime, extent, field power,
#    first top-down contour point, first three process-map grid cells).
# ---------------------------------------------------------------------------------------------------------------
MATS = {"in718": "Inconel 718", "ti6al4v": "Ti-6Al-4V", "ss316l": "316L Stainless Steel", "in625": "Inconel 625",
        "alsi10mg": "AlSi10Mg"}
KH = "Keyhole Mode (melt-pool D/W > 0.5 screening onset)"


def _cell(color, depth, enth, p, regime, v, width, status="computed", flag=False):
    cell = {"color": color, "depth_um": depth, "extentStatus": status, "keyholeIndexLackOfFusion": flag,
            "normalizedEnthalpy": enth, "power_W": p, "regime": regime, "speed_mm_s": v, "width_um": width}
    if flag:
        cell["lackOfFusionNote"] = solver.KEYHOLE_INDEX_LOF_NOTE
    return cell


# P7b (2026-10-14, sourcing correction): the geometry pins move with the absorptivity authority (IN718 0.32, Ti-6Al-4V
# 0.32, 316L 0.30), the melting-point / kernel-ledger k and cp and the field-extent grid (B17); dH/hs, the regime and
# the field-power-to-A relation are bit equal (index convention). REV0 rows: 119.3/57.9/490.3/0.0 (field 76.0),
# 132.1/105.9/685.9/47.8 (98.0), 114.8/57.8/722.5/0.0 (147.0).
REV0_PINS = {
    "in718|200|800|80|rosenthal": {
        "W": 96.0, "D": 46.5, "L": 286.1, "cav": 0.0, "dh": 23.67, "regime": KH, "extent": "computed",
        "fieldPower": 64.0, "contour0": {"x_um": 14.0, "y_um": 0.0},
        "grid0": [_cell("#f59e0b", 40.9, 15.46, 80, "Lack of Fusion Zone", 300, 83.5),
                  _cell("#f59e0b", 29.9, 10.93, 80, "Lack of Fusion Zone", 600, 62.0),
                  _cell("#f59e0b", 24.7, 8.93, 80, "Lack of Fusion Zone", 900, 51.4)]},
    "ti6al4v|280|1200|80|eagar-tsai": {
        "W": 128.8, "D": 96.8, "L": 559.6, "cav": 40.5, "dh": 31.96, "regime": KH, "extent": "computed",
        "fieldPower": 89.6, "contour0": {"x_um": 43.9, "y_um": 0.1},
        "grid0": [_cell("#f59e0b", 55.1, 18.26, 80, "Lack of Fusion Zone", 300, 112.3),
                  _cell("#f59e0b", 40.4, 12.91, 80, "Lack of Fusion Zone", 600, 83.2),
                  _cell("#f59e0b", 33.4, 10.54, 80, "Lack of Fusion Zone", 900, 69.1)]},
    "ss316l|350|1500|100|goldak": {
        "W": 85.1, "D": 42.4, "L": 403.2, "cav": 0.0, "dh": 17.98, "regime": "Transition Mode", "extent": "computed",
        "fieldPower": 105.0, "contour0": {"x_um": 17.5, "y_um": 0.0},
        "grid0": [_cell("#f59e0b", 34.1, 9.19, 80, "Lack of Fusion Zone", 300, 70.3),
                  _cell("#10b981", None, 6.5, 80, "Optimal Conduction", 600, None, "width-floor-applied"),
                  _cell("#10b981", None, 5.31, 80, "Optimal Conduction", 900, None, "width-floor-applied")]},
    # REV0 rows: 117.2/65.1/491.6/8.3 (76.0), 97.2/49.0/107.2/0.0 (27.0; AlSi10Mg 0.18 to 0.30 deeper, Amendment 1),
    # 93.5/13.4/170.0/0.0 width-floor-applied (18.0; the field with A 0.30 and the kernel ledger resolves this point).
    "in625|200|800|80|rosenthal": {
        "W": 97.5, "D": 58.3, "L": 308.1, "cav": 11.0, "dh": 25.62, "regime": KH, "extent": "computed",
        "fieldPower": 68.0, "contour0": {"x_um": 14.0, "y_um": 0.0},
        "grid0": [_cell("#f59e0b", 42.2, 16.74, 80, "Lack of Fusion Zone", 300, 86.3, flag=True),
                  _cell("#f59e0b", 30.8, 11.83, 80, "Lack of Fusion Zone", 600, 63.8),
                  _cell("#f59e0b", 25.4, 9.66, 80, "Lack of Fusion Zone", 900, 52.9)]},
    "alsi10mg|150|600|80|rosenthal": {
        "W": 121.4, "D": 60.9, "L": 130.2, "cav": 0.0, "dh": 8.48, "regime": "Conduction Mode (Stable)",
        "extent": "computed", "fieldPower": 45.0, "contour0": {"x_um": 46.2, "y_um": 0.4},
        "grid0": [_cell("#f59e0b", 33.1, 6.39, 80, "Lack of Fusion Zone", 300, 66.2),
                  _cell("#f59e0b", 29.7, 4.52, 80, "Lack of Fusion Zone", 600, 59.6),
                  _cell("#f59e0b", 27.4, 3.69, 80, "Lack of Fusion Zone", 900, 54.4)]},
    # Former fallback point: resolved since P7b (the AlSi10Mg field absorbs 0.30); its grid corner stays unresolved.
    "alsi10mg|100|400|170|eagar-tsai": {
        "W": 113.6, "D": 24.0, "L": 170.0, "cav": 0.0, "dh": 2.23, "regime": "Conduction Mode (Stable)",
        "extent": "computed", "fieldPower": 30.0, "contour0": {"x_um": 49.7, "y_um": 0.5},
        "grid0": [_cell("#10b981", None, 2.06, 80, "Optimal Conduction", 300, None, "heuristic-width-fallback"),
                  _cell("#10b981", None, 1.46, 80, "Optimal Conduction", 600, None, "heuristic-width-fallback"),
                  _cell("#10b981", None, 1.19, 80, "Optimal Conduction", 900, None, "heuristic-width-fallback")]},
}

# DOI strings that resolve to the wrong paper or to nothing (G1 sweep 1.4 and 6.2): denied everywhere in src/ and python/.
DENIED_DOIS = ("10.1016/j.actamat.2010.02.008", "10.1007/s00170-014-6721-3", "10.1108/13552541211218112",
               "10.1016/j.actamat.2016.03.044", "10.1016/j.ijheatmasstransfer.2020.120801")
# DOIs that resolve to the named paper but are not window sources: denied in the literature-box file only.
NOT_WINDOW_SOURCE_DOIS = ("10.1016/j.jmatprotec.2015.01.025", "10.1016/j.jmatprotec.2017.05.042")
# sha256 of python/fabbro_keyhole.py with CRLF folded to LF (P7a must not touch it: its hashed G12 observation).
FABBRO_KEYHOLE_SHA256 = "21d1b9a8ed205518e42fd4b8d6e1a804bb7a2ce4a4cb2f86a0fd5adc5d1d7200"


def _run(key):
    aid, p, v, beam, kern = key.split("|")
    return solver.calculate_meltpool_physics(MATS[aid], float(p), float(v), float(beam), 80.0, 40.0, 100.0,
                                             "IR_1064nm", heat_source=kern)


class GeometryBitEqual(unittest.TestCase):
    def test_geometry_bit_equal(self):
        for key, pin in REV0_PINS.items():
            th = _run(key)
            g, pp = th["meltPoolGeometry"], th["processParameters"]
            got = {"W": g["width_um"], "D": g["depth_um"], "L": g["length_um"], "cav": g["keyholeVaporCavityDepth_um"],
                   "dh": pp["normalizedEnthalpy"], "regime": g["regime"], "extent": g["extentStatus"],
                   "fieldPower": pp["fieldPower_W"], "contour0": th["geometricContours"]["topDownXY"][0],
                   "grid0": th["processWindowMap"]["grid"][:3]}
            self.assertEqual(got, pin, key)
            self.assertEqual(solver.ENTHALPY_TRANSITION, 15.0)
            self.assertEqual(solver.ENTHALPY_KEYHOLE, 20.0)
            self.assertEqual(solver.ENTHALPY_KEYHOLE_IN625, 13.6)


# ---------------------------------------------------------------------------------------------------------------
# Hand-built thermal dicts for compose_verdict (no solver call).
# ---------------------------------------------------------------------------------------------------------------
def _thermal(tang=0.5, dh=12.0, regime="Conduction Mode (Stable)", power=200.0, speed=800.0, extent="computed",
             balling=None, w=120.0, d=60.0, lof_status=None, margin=None, cut=20.0, distortion=None):
    if lof_status is None:
        lof_status = "Fail" if tang > 1.0 else "Pass"
    if margin is None:
        margin = bool(0.80 < tang <= 1.0)
    return {
        "processParameters": {"laserPower_W": power, "scanSpeed_mm_s": speed, "hatchSpacing_um": 100.0,
                              "layerThickness_um": 40.0, "beamDiameter_um": 80.0, "normalizedEnthalpy": dh,
                              "absorptionModel": "flat-plate"},
        "meltPoolGeometry": {"width_um": w, "depth_um": d, "length_um": 400.0, "extentStatus": extent,
                             "extentNote": None, "regime": regime, "regimeKeyholeThreshold": cut},
        "defectDiagnostics": {"lackOfFusionStatus": lof_status, "tangIndex_hW_tD": tang,
                              "lackOfFusionOverlapIndex": tang, "lackOfFusionMarginAdvisory": margin,
                              "keyholePorosityRisk": "Negligible", "ballingInstabilityRisk": "Stable",
                              "ballingScreen": balling if balling is not None else balling_screen(300.0, 100.0, 40.0, "computed"),
                              "recoaterCrashRisk": solver.STRESS_UNAVAILABLE_REASON,
                              "effectiveResidualStress_MPa": None, "distortionIndex": distortion},
    }


def _gates(out):
    return {g["id"]: g for g in out["gates"]}


class Ladder(unittest.TestCase):
    def test_ladder(self):
        for dh, regime in ((12.0, "Conduction Mode (Stable)"), (60.0, KH), (17.0, "Transition Mode")):
            out = bj.compose_verdict(_thermal(tang=1.05, dh=dh, regime=regime), "in718")
            self.assertEqual(out["verdict"], "do-not-print", (dh, regime))
            self.assertEqual(out["dominantGate"], "lof_tang")
            self.assertEqual(out["blockingGates"], ["lof_tang"])  # lof_wh / lof_dt are diagnostics, never fail
            self.assertIn("Tang unit criterion", out["headline"])
        out = bj.compose_verdict(_thermal(tang=0.5, dh=25.0, regime=KH), "in718")
        self.assertEqual(out["verdict"], "risky")
        self.assertEqual(out["dominantGate"], "keyhole")
        self.assertEqual(out["riskGates"], ["keyhole"])
        self.assertEqual(out["blockingGates"], [])
        self.assertIn("keyhole mode", out["headline"])
        # dH/hs 40 in keyhole mode never gives do-not-print (the inverted former test).
        out = bj.compose_verdict(_thermal(tang=0.5, dh=40.0, regime=KH), "in718")
        self.assertEqual(out["verdict"], "risky")
        self.assertEqual(out["blockingGates"], [])
        self.assertTrue(any("legacy level" in a for a in out["advisories"]))
        for dh, regime in ((12.0, "Conduction Mode (Stable)"), (17.0, "Transition Mode")):
            out = bj.compose_verdict(_thermal(tang=0.5, dh=dh, regime=regime), "in718")
            self.assertEqual(out["verdict"], "printable", (dh, regime))
            self.assertEqual(out["verdictBasis"], "sourced-criteria-only")
            self.assertEqual(out["dominantGate"], "none")
            self.assertTrue(out["reasons"][0].startswith("Melt pool passes the Tang overlap criterion; regime:"), out["reasons"])
            self.assertIn("no sourced gate fails", out["headline"])
        out = bj.compose_verdict(_thermal(tang=0.85, dh=12.0), "in718")
        self.assertEqual(out["verdict"], "printable")
        self.assertTrue(out["lackOfFusionMarginAdvisory"])
        self.assertTrue(any(a.startswith("Advisory: Tang margin") for a in out["advisories"]))
        out = bj.compose_verdict(_thermal(tang=0.5, dh=16.0, regime="Transition Mode"), "in718")
        self.assertEqual(out["verdict"], "printable")
        self.assertTrue(any(a.startswith("Advisory: transition band") for a in out["advisories"]))
        self.assertEqual(_gates(out)["keyhole"]["status"], "advisory")
        # Outside the box, balling High (316L) and downskin 60 degrees alone: printable plus advisories.
        out = bj.compose_verdict(_thermal(tang=0.5, power=5000.0, speed=10.0), "in718")
        self.assertEqual(out["verdict"], "printable")
        self.assertEqual(_gates(out)["literature_pv"]["status"], "advisory")
        self.assertTrue(any("literature display range" in a for a in out["advisories"]))
        # P7b (2026-10-14): no High band; the former High L/W is the Moderate advisory for every alloy.
        high = balling_screen(600.0, 100.0, 40.0, "computed", material_name="316L Stainless Steel")
        out = bj.compose_verdict(_thermal(tang=0.5, balling=high), "ss316l")
        self.assertEqual(out["verdict"], "printable")
        self.assertEqual(_gates(out)["balling"]["status"], "advisory")
        self.assertTrue(any(a.startswith("Advisory: balling screen Moderate") for a in out["advisories"]))
        self.assertFalse(any(a.startswith("Advisory: balling screen High") for a in out["advisories"]))
        out = bj.compose_verdict(_thermal(tang=0.5), "in718", extras={"downskinOverhang_deg": 60.0})
        self.assertEqual(out["verdict"], "printable")
        self.assertEqual(_gates(out)["downskin"]["status"], "advisory")
        self.assertTrue(any(a.startswith("Advisory: downskin") for a in out["advisories"]))
        self.assertEqual(out["advisoryCount"], len(out["advisories"]))
        # Unresolved geometry gives inconclusive for every combination.
        for kw in ({"tang": 1.05}, {"tang": 0.5, "dh": 40.0, "regime": KH}, {"tang": 0.5}, {"tang": 0.9, "balling": high}):
            out = bj.compose_verdict(_thermal(extent="heuristic-width-fallback", **kw), "in718")
            self.assertEqual(out["verdict"], "inconclusive", kw)
            self.assertEqual(out["blockingGates"], [], kw)

    def test_advisory_texts_and_basis(self):
        high = balling_screen(600.0, 100.0, 40.0, "computed", material_name="316L Stainless Steel")
        out = bj.compose_verdict(_thermal(tang=0.85, dh=16.0, regime="Transition Mode", power=5000.0, speed=10.0,
                                          balling=high), "ss316l", extras={"downskinOverhang_deg": 60.0})
        gates = _gates(out)
        for gid in ("literature_pv", "balling", "downskin", "lof_wh", "lof_dt"):
            self.assertIn("unsourced screening threshold", gates[gid]["basis"] + gates[gid]["note"], gid)
        for gid in ("literature_pv", "balling", "downskin"):
            self.assertEqual(gates[gid]["status"], "advisory", gid)
        self.assertIsNone(gates["lof_wh"]["required"])
        self.assertIsNone(gates["lof_dt"]["required"])
        self.assertIn("Tang criterion as quoted in Harkin 2023 Eq. 5", gates["lof_tang"]["basis"])
        self.assertIn("mode onset, not a porosity boundary", gates["keyhole"]["basis"])
        self.assertIn("22.2 (19.3 to 25.2)", gates["keyhole"]["basis"])  # 316L, pinned king_conversion numbers
        self.assertEqual(gates["keyhole"]["required"], 20.0)
        ti = _gates(bj.compose_verdict(_thermal(tang=0.5), "ti6al4v"))["keyhole"]["basis"]
        self.assertIn("17.3 to 20.0", ti)
        self.assertIn("(12.67, 13.94]", solver.keyhole_cut_basis("Inconel 625"))
        self.assertIn("transferred", _gates(bj.compose_verdict(_thermal(tang=0.5), "in718"))["keyhole"]["basis"])
        text = " ".join(out["reasons"] + out["advisories"] + [g.get("basis", "") + g["note"] for g in out["gates"]])
        self.assertNotIn("22.8", text)
        self.assertNotIn("35", _gates(out)["keyhole"]["note"])
        # The pinned conversion numbers come from the tool, not from a re-derivation.
        sys.path.insert(0, os.path.join(HERE, "tools"))
        import lpbf_keyhole_benchmark as kb
        conv = kb.king_conversion()["kingThresholdInAppUnits"]
        self.assertEqual((round(conv["low"], 1), round(conv["mid"], 1), round(conv["high"], 1)), (19.3, 22.2, 25.2))
        # P7b (2026-10-14): the conversion reads the index convention constant 0.42; the physical authority is 0.30.
        self.assertEqual(kb.king_conversion()["app316lProperties"]["absorptivity_index_IR"], 0.42)
        self.assertEqual(kb.king_conversion()["app316lProperties"]["absorptivity_IR_physical_not_used"], 0.30)

    def test_lof_single_rule(self):
        for p, v, h, t in ((200.0, 800.0, 100.0, 40.0), (150.0, 1200.0, 110.0, 40.0), (300.0, 600.0, 90.0, 30.0),
                           (80.0, 2000.0, 120.0, 50.0)):
            th = solver.calculate_meltpool_physics("Inconel 718", p, v, 80.0, 80.0, t, h, "IR_1064nm")
            dd = th["defectDiagnostics"]
            self.assertIn(dd["lackOfFusionStatus"], ("Pass", "Fail"), (p, v))
            self.assertEqual(dd["lackOfFusionStatus"], "Fail" if dd["tangIndex_hW_tD"] > 1.0 else "Pass")
            self.assertEqual(dd["lackOfFusionMarginAdvisory"], bool(0.80 < dd["tangIndex_hW_tD"] <= 1.0))
            self.assertIn("unsourced screening threshold 0.80", dd["lackOfFusionMarginBasis"])
        self.assertTrue(bj.compose_verdict(_thermal(tang=0.85), "in718")["lackOfFusionMarginAdvisory"])
        self.assertFalse(bj.compose_verdict(_thermal(tang=0.5), "in718")["lackOfFusionMarginAdvisory"])
        self.assertEqual(_gates(bj.compose_verdict(_thermal(tang=0.85), "in718"))["lof_tang"]["status"], "pass")
        # Legacy "Warning" payloads map to pass plus the margin advisory, never warn.
        out = bj.compose_verdict(_thermal(tang=0.85, lof_status="Warning", margin=False), "in718")
        self.assertEqual(out["verdict"], "printable")
        self.assertTrue(out["lackOfFusionMarginAdvisory"])

    def test_balling_high_band_316l_only(self):
        # P7b (2026-10-14, V09): the P7a 316L-only High band is removed for every alloy (highBandApplicable False, the
        # served highThreshold null); Moderate (3.85) and Stable stay.
        s316 = balling_screen(600.0, 100.0, 40.0, "computed", material_name="316L Stainless Steel")
        self.assertEqual((s316["band"], s316["highBandApplicable"], s316["verdictEffect"]), ("moderate", False, "advisory"))
        for mat in ("Inconel 718", "Ti-6Al-4V", "AlSi10Mg", "Inconel 625"):
            other = balling_screen(600.0, 100.0, 40.0, "computed", material_name=mat)
            self.assertEqual((other["band"], other["highBandApplicable"]), ("moderate", False), mat)
        self.assertEqual(balling_screen(385.0, 100.0, 40.0, "computed", material_name="Inconel 718")["band"], "moderate")
        self.assertEqual(balling_screen(384.7, 100.0, 40.0, "computed", material_name="Inconel 718")["band"], "stable")
        self.assertAlmostEqual(s316["moderateThreshold"], 3.848, places=3)
        self.assertIsNone(s316["highThreshold"])
        out316 = bj.compose_verdict(_thermal(tang=0.5, balling=s316), "ss316l")
        self.assertEqual(out316["verdict"], "printable")
        self.assertFalse(any("High" in a for a in out316["advisories"]))
        out718 = bj.compose_verdict(_thermal(tang=0.5, balling=balling_screen(600.0, 100.0, 40.0, "computed",
                                                                                 material_name="Inconel 718")), "in718")
        self.assertFalse(any("High" in a for a in out718["advisories"]))
        self.assertTrue(any(a.startswith("Advisory: balling screen Moderate") for a in out718["advisories"]))

    def test_suggested_patch_acceptance(self):
        box = bj.LITERATURE_PV_WINDOWS["in718"]
        base = _thermal(tang=0.5, dh=25.0, regime=KH, power=520.0, speed=400.0)
        calls = []

        def make(rule):
            def evaluate(p, v, h, t, d):
                calls.append((p, v, h, t, d))
                kw = rule(p, v, h, t, d)
                th = _thermal(power=p, speed=v, **kw)
                th["processParameters"].update(hatchSpacing_um=h, layerThickness_um=t, beamDiameter_um=d)
                return th
            return evaluate

        # (a) first candidate: below the cut, Tang 0.9, outside the box -> accepted with the box advisory.
        far = lambda p, v, h, t, d: {"tang": 0.9, "dh": 12.0, "power": p}  # noqa: E731
        ev = make(lambda p, v, h, t, d: {"tang": 0.9, "dh": 12.0})
        base_far = copy.deepcopy(base)
        # Force every candidate outside the box by shrinking the evaluated power below the box minimum.
        ev_out = make(lambda p, v, h, t, d: {"tang": 0.9, "dh": 12.0})

        def ev_outside(p, v, h, t, d):
            th = ev_out(p, v, h, t, d)
            th["processParameters"]["laserPower_W"] = box["powerMin_W"] - 50.0
            return th
        patch, note, adv = bj._suggested_patch(base_far, "in718", "keyhole", "risky", ev_outside)
        self.assertIsNotNone(patch)
        self.assertTrue(any("literature display range" in a for a in adv), adv)
        self.assertTrue(any("Tang margin" in a for a in adv), adv)
        self.assertIn("Advisories at the suggested point:", note)
        self.assertIn("Tang unit criterion passes", note)
        self.assertIn("below the keyhole-mode cut", note)
        del ev, far
        # (b) a keyhole-mode candidate (Tang 0.5) is rejected; a Tang 1.2 candidate is rejected; all rejected -> null.
        calls.clear()
        patch, note, adv = bj._suggested_patch(base, "in718", "keyhole", "risky",
                                               make(lambda p, v, h, t, d: {"tang": 0.5, "dh": 30.0, "regime": KH}))
        self.assertIsNone(patch)
        self.assertEqual(adv, [])
        self.assertIn("No parameter patch", note)
        self.assertIn("keyhole-mode cut", note)
        self.assertGreater(len(calls), 1)
        patch, note, adv = bj._suggested_patch(base, "in718", "keyhole", "risky",
                                               make(lambda p, v, h, t, d: {"tang": 1.2, "dh": 12.0}))
        self.assertIsNone(patch)
        # (c) a later zero-advisory candidate wins over an earlier printable one with advisories.
        calls.clear()
        patch, note, adv = bj._suggested_patch(
            base, "in718", "keyhole", "risky",
            make(lambda p, v, h, t, d: {"tang": 0.9 if len(calls) <= 3 else 0.5, "dh": 12.0}))
        self.assertIsNotNone(patch)
        self.assertEqual(adv, [])
        self.assertTrue(note.endswith("Advisories at the suggested point: none"), note)
        self.assertEqual((patch["laserPower_W"], patch["scanSpeed_mms"]), tuple(int(round(x)) for x in calls[3][:2]))
        # (d) dominant keyhole starts from the box minimum power and maximum speed candidate.
        self.assertEqual(calls[0][:2], (box["powerMin_W"], box["speedMax_mm_s"]))
        # (e) printable or no dominant gate: no patch, no calls; no evaluator: no patch with the reason.
        self.assertEqual(bj._suggested_patch(base, "in718", "none", "printable", make(lambda *a: {}))[0], None)
        self.assertIn("not available", bj._suggested_patch(base, "in718", "keyhole", "risky", None)[1])

    def test_stress_not_evaluated(self):
        th = solver.calculate_meltpool_physics("Inconel 718", 200.0, 800.0, 80.0, 80.0, 40.0, 100.0, "IR_1064nm")
        dd = th["defectDiagnostics"]
        self.assertIsNone(dd["effectiveResidualStress_MPa"])
        self.assertIsNone(dd["distortionIndex"])
        self.assertTrue(dd["recoaterCrashRisk"].startswith("unavailable: no sourced stress model"))
        self.assertIn("Mercelis and Kruth 2006", dd["distortionIndexBasis"])
        self.assertNotIn("elastic_stress_max_mpa", open(os.path.join(HERE, "lpbf_thermal_solver.py"), encoding="utf-8").read())
        out = bj.compose_verdict(th, "in718")
        gates = _gates(out)
        for gid in ("recoater", "distortion"):
            self.assertEqual(gates[gid]["status"], "not-evaluated", gid)
            self.assertIsNone(gates[gid]["required"])
            self.assertIsNone(gates[gid]["measured"])
            self.assertIn("no sourced stress model", gates[gid]["reason"])
            self.assertIn(gid, out["unavailableGates"])
            self.assertIn(gid, out["notEvaluatedGates"])
        self.assertNotEqual(out["verdict"], "inconclusive")
        # Every other gate passing: still printable, not inconclusive.
        out = bj.compose_verdict(_thermal(tang=0.5), "in718")
        self.assertEqual(out["verdict"], "printable")
        self.assertEqual(out["notEvaluatedGates"], ["recoater", "distortion"])
        self.assertFalse(any("recoater" in a or "distortion" in a for a in out["advisories"]))

    def test_advisories_never_make_inconclusive(self):
        high = balling_screen(600.0, 100.0, 40.0, "computed", material_name="316L Stainless Steel")
        for kw, extras in (({"tang": 0.5}, {}), ({"tang": 0.5, "dh": 25.0, "regime": KH}, {}), ({"tang": 1.05}, {}),
                           ({"tang": 0.85, "dh": 16.0, "regime": "Transition Mode"}, {"downskinOverhang_deg": 60.0}),
                           ({"tang": 0.5, "dh": 35.0, "regime": KH, "balling": high, "power": 5000.0}, {"downskinOverhang_deg": 50.0})):
            plain = bj.compose_verdict(_thermal(**kw), "ss316l", extras=extras)
            self.assertNotEqual(plain["verdict"], "inconclusive", kw)
            gates = _gates(plain)
            for gid in ("recoater", "distortion", "literature_pv", "balling", "downskin", "lof_wh", "lof_dt"):
                self.assertIn(gates[gid]["status"], ("pass", "advisory", "not-evaluated"), (gid, kw))
            # The verdict equals the verdict without any advisory or not-evaluated gate: only Tang and the regime count.
            expect = "do-not-print" if kw.get("tang", 0.5) > 1.0 else ("risky" if kw.get("regime", "") == KH else "printable")
            self.assertEqual(plain["verdict"], expect, kw)
            self.assertEqual(sorted((set(plain["blockingGates"]) | set(plain["riskGates"])) - {"lof_tang", "keyhole"}), [], kw)

    def test_pdas_band(self):
        x = (1e6 ** -0.5) * (0.5 ** -0.25)
        band = sf.pdas_band_um(1e6, 0.5, "in718")
        self.assertIsNotNone(band["pdasBand_um"])
        self.assertEqual(sorted(band["pdasBand_um"]), ["hunt", "kurzFisher"])
        self.assertAlmostEqual(band["pdasBand_um"]["hunt"], 9.56e-4 * x * 1e6, delta=1e-9 * 1.137)
        self.assertAlmostEqual(band["pdasBand_um"]["kurzFisher"], 2.6e-3 * x * 1e6, delta=1e-9 * 3.092)
        self.assertAlmostEqual(band["pdasBand_um"]["hunt"], 1.137, places=3)
        self.assertAlmostEqual(band["pdasBand_um"]["kurzFisher"], 3.092, places=3)
        self.assertFalse(band["pdasOutOfRange"])
        self.assertIn("Ghosh", band["pdasBasis"])
        self.assertNotIn("2.1e-3", band["pdasBasis"])
        self.assertIsNotNone(sf.pdas_band_um(1e6, 0.5, "Inconel 625")["pdasBand_um"])
        # x below 4e-4 (G 1e7, R 0.5: 3.76e-4), above 1.2e-3 (G 1e5, R 0.5: 3.76e-3) and cooling outside 5e4 to 3e6.
        for G, R, cool in ((1e7, 0.5, None), (1e5, 0.5, None), (1e6, 0.5, 1e4), (1e6, 0.5, 5e6)):
            out = sf.pdas_band_um(G, R, "in718", cool)
            self.assertIsNone(out["pdasBand_um"], (G, R, cool))
            self.assertTrue(out["pdasOutOfRange"], (G, R, cool))
            self.assertIn("validity range", out["pdasUnavailableReason"])
        for alloy in ("316L Stainless Steel", "Ti-6Al-4V", "AlSi10Mg", "ss316l"):
            out = sf.pdas_band_um(1e6, 0.5, alloy)
            self.assertIsNone(out["pdasBand_um"], alloy)
            self.assertIsNone(out["pdasOutOfRange"], alloy)
            self.assertIn("no sourced PDAS parameters", out["pdasUnavailableReason"])
        # evaluate_solidification: no scalar, SDAS null for every alloy, the former keywords still accepted.
        from eagar_tsai_solver import EagarTsaiField
        field = EagarTsaiField(80.0, 76.0, 25.0, 5.5e-6, 40e-6).bind_speed(0.8)
        for mat in ("Inconel 718", "316L Stainless Steel", "Ti-6Al-4V"):
            kin = sf.evaluate_solidification(field.temperature_C, T_liq=1336.0, T_sol=1260.0, t_surface=2400.0, v_scan=0.8,
                                             x_rear=-150e-6, x_front=50e-6, search_depth=80e-6, r_beam=40e-6, cos_theta=1.0,
                                             pdas_A1=1.0, sdas_B1=50.0, material_name=mat)
            self.assertIsNone(kin["primaryDendriteArmSpacing_PDAS_um"], mat)
            self.assertIsNone(kin["secondaryDendriteArmSpacing_SDAS_um"], mat)
            self.assertIn("no sourced SDAS prefactor", kin["sdasUnavailableReason"])
            self.assertIn("pdasBand_um", kin)
        for mat in ("Inconel 718", "316L Stainless Steel", "AlSi10Mg", "Inconel 625"):
            th = solver.calculate_meltpool_physics(mat, 150.0, 1200.0, 80.0, 80.0, 40.0, 100.0, "IR_1064nm")
            kin = th["solidificationKinetics"]
            self.assertIsNone(kin["primaryDendriteArmSpacing_PDAS_um"], mat)
            self.assertIsNone(kin["secondaryDendriteArmSpacing_SDAS_um"], mat)
            if mat in ("Inconel 718", "Inconel 625") and kin["thermalGradient_G_K_m"] is not None:
                self.assertIsNotNone(kin["pdasOutOfRange"], mat)
            else:
                self.assertIsNone(kin["pdasBand_um"], mat)

    def test_citations(self):
        hits = []
        for sub in ("src", "python"):
            for dirpath, _dirs, files in os.walk(os.path.join(ROOT, sub)):
                if "node_modules" in dirpath or "__pycache__" in dirpath:
                    continue
                for name in files:
                    if not name.endswith((".py", ".ts", ".tsx", ".json")) or name == os.path.basename(__file__):
                        continue
                    path = os.path.join(dirpath, name)
                    try:
                        text = open(path, encoding="utf-8").read()
                    except UnicodeDecodeError:
                        continue
                    for doi in DENIED_DOIS:
                        if doi in text:
                            hits.append((os.path.relpath(path, ROOT), doi))
        self.assertEqual(hits, [])
        out = marangoni_screening(-3.7e-4, 5e-3, 5.5e-6, 7400.0, 50e-6, 2500.0, 1336.0, 15.0)
        self.assertIsNone(out["doi"])
        self.assertIn("unsourced screening values", out["basis"])
        th = solver.calculate_meltpool_physics("Inconel 718", 200.0, 800.0, 80.0, 80.0, 40.0, 100.0, "IR_1064nm")
        self.assertIsNone(th["marangoniModel"]["doi"])
        self.assertIn("unsourced screening values", th["marangoniModel"]["basis"])
        schema = open(os.path.join(ROOT, "src", "utils", "lpbfFourAlloySchema.ts"), encoding="utf-8").read()
        for doi in DENIED_DOIS + NOT_WINDOW_SOURCE_DOIS:
            self.assertNotIn(doi, schema, doi)
        self.assertIn("10.1007/s00170-014-6297-2", schema)
        self.assertIn("related literature, no edge of this display range is taken from it", schema)

    def test_fabbro_basis_text(self):
        self.assertIn("unsourced", solver.FABBRO_BASIS)
        self.assertIn("P3", solver.FABBRO_BASIS)
        self.assertNotIn("(P2)", solver.FABBRO_BASIS.split("k_s is")[0])
        self.assertIn("Gan 2021 Eq. 2", solver.FABBRO_BASIS)
        self.assertEqual(solver.FABBRO_ONSET_RAMP_FULL_AT, 30.0)
        self.assertEqual(solver.POROSITY_SCREEN_HIGH_AT, 30.0)
        raw = open(os.path.join(HERE, "fabbro_keyhole.py"), "rb").read().replace(b"\r\n", b"\n")
        self.assertEqual(hashlib.sha256(raw).hexdigest(), FABBRO_KEYHOLE_SHA256)

    def test_labels_unchanged(self):
        th = solver.calculate_meltpool_physics("Inconel 625", 200.0, 800.0, 80.0, 80.0, 40.0, 100.0, "IR_1064nm")
        self.assertEqual(th["materialEvidence"]["validationStatus"], "unvalidated")
        self.assertIs(th["defectDiagnostics"]["ballingScreen"]["experimentalValidation"], False)
        self.assertIs(th["defectDiagnostics"]["keyholePorosityResolved"], False)
        # Existing label tests stay in the tree and are not edited by P7a.
        for name in ("test_lpbf_keyhole_regime_bump.py", "test_lpbf_claims_wording.py"):
            path = os.path.join(HERE, name)
            if os.path.exists(path):
                self.assertNotIn("P7a", open(path, encoding="utf-8").read(), name)

    def test_assumptions_and_revision(self):
        from lpbf_job_cache import BUILD_JOB_SOLVER_REVISION
        # P7b (2026-10-14): v25.
        self.assertEqual(BUILD_JOB_SOLVER_REVISION, "lpbf-build-job-p7b-sourced-constants-v25")
        job = bj.solve_lpbf_build_job({"alloyId": "in718", "laserPower_W": 285, "scanSpeed_mm_s": 960,
                                       "hatchSpacing_um": 110, "layerThickness_um": 40, "bypassCache": True})
        text = " ".join(job["assumptions"])
        self.assertIn("a mode onset and not a porosity boundary", text)
        self.assertIn("do-not-print on the Tang unit criterion, risky in keyhole mode, otherwise printable", text)
        self.assertIn("unsourced screening thresholds reported as advisories", text)
        self.assertNotIn("do-not-print above 35", text)
        self.assertEqual(job["verdict"]["verdictBasis"], "sourced-criteria-only")
        self.assertIn("suggestedPatchAdvisories", job["verdict"])
        micro = job["microstructure"]
        self.assertIn("pdasBand_um", micro)
        self.assertIsNone(micro.get("SDAS_um"))


if __name__ == "__main__":
    unittest.main()
