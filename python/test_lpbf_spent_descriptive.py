"""Spent-set descriptive producer (research hub spec 8.3). Structure, counts, hashes and labels only.

No test here asserts or prints a measured value. The full re-derivation (`--check`) runs only with
LPBF_SPENT_DESCRIPTIVE_FULL=1 and stays out of CI.
"""
import ast
import copy
import hashlib
import json
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

import lpbf_served_arms
import lpbf_spent_ledger as ledger
from tools import lpbf_spent_descriptive as tool

PY_DIR = Path(__file__).resolve().parent
DOCS = tool.REPO / "docs"
BANNED = re.compile(r"\b(validated|accuracy|rank|score|pass|fail)\b", re.I)
DASHES = re.compile("[–—]")
VIEWS = sorted(DOCS.glob("LPBF_SPENT_DESCRIPTIVE_*.view.json"))


def _walk(obj, keys=None, strings=None):
    keys = [] if keys is None else keys
    strings = [] if strings is None else strings
    if isinstance(obj, dict):
        for k, v in obj.items():
            keys.append(k)
            _walk(v, keys, strings)
    elif isinstance(obj, list):
        for v in obj:
            _walk(v, keys, strings)
    elif isinstance(obj, str):
        strings.append(obj)
    return keys, strings


def synthetic_entry(**over):
    e = copy.deepcopy(ledger.load_ledger()["entries"][0])
    e.update(datasetId="synthetic-set", alloy="316L", curveAxis="speed", tableSha256="0" * 64)
    e.update(over)
    return e


def synthetic_rows():
    rows = []
    for p in (100.0, 200.0):
        for i, v in enumerate((400.0, 800.0, 1200.0)):
            rows.append({"rowId": f"s-{int(p)}-{i}", "power_W": p, "speed_mm_s": v, "beamDiameter_um": 80.0,
                         "preheat_C": None, "layer_um": 0.0, "depth_um": 50.0 + i * 5, "width_um": 100.0 + i})
    return rows


def stub_served(alloy, P_W, v_mm_s, d_1e2_um, T0_C, layer_um=40.0, **_):
    return {"status": "ok", "depth_um": P_W / (v_mm_s ** 0.5) * 3.0, "width_um": 90.0, "extentStatus": "computed",
            "index": P_W / v_mm_s * 10.0, "reasonLabel": None}


STUB_IDENTITY = ({"servedClosurePinSha256": "a" * 64, "implementationFingerprint": "b" * 64, "alloys": {}},
                 {"316L": {"python": "x"}})


def with_served(fn, body):
    original = lpbf_served_arms.served_arm
    lpbf_served_arms.served_arm = fn
    try:
        return body()
    finally:
        lpbf_served_arms.served_arm = original


class ProducerRulesTests(unittest.TestCase):
    def synthetic_ledger(self, **over):
        return {"schema": ledger.SCHEMA, "entries": [synthetic_entry(**over)]}

    def build(self, led, served=stub_served):
        calls = []

        def rows_source(entry):
            calls.append(entry["datasetId"])
            return synthetic_rows(), {"fileSha256": entry["tableSha256"], "citation": "Synthetic citation"}

        view, full = with_served(served, lambda: tool.build_record(
            ledger=led, rows_source=rows_source, identity=STUB_IDENTITY, generated_at="2026-01-01T00:00:00Z"))
        return view, full, calls

    def test_refuses_a_set_that_is_not_spent_before_reading_rows(self):
        for status in ("EXPOSED", "EXPOSED-LOW", "CLEAN", "UNUSABLE"):
            calls = []
            led = self.synthetic_ledger(status=status)
            with self.assertRaises(tool.DescriptiveRefusal):
                tool.build_record(ledger=led, rows_source=lambda e: calls.append(1), identity=STUB_IDENTITY)
            self.assertEqual(calls, [])

    def test_refuses_forbidden_ids_even_when_spent(self):
        for did in ledger.FORBIDDEN_IDS:
            led = self.synthetic_ledger()
            led["entries"][0]["datasetId"] = did
            with self.assertRaises(tool.DescriptiveRefusal):
                tool.build_record(ledger=led, rows_source=lambda e: ([], {}), identity=STUB_IDENTITY)

    def test_refuses_a_non_depth_observable(self):
        led = self.synthetic_ledger(observable="vapour-depression-depth")
        with self.assertRaises(tool.DescriptiveRefusal):
            tool.build_record(ledger=led, rows_source=lambda e: ([], {}), identity=STUB_IDENTITY)

    def test_refuses_a_table_whose_hash_differs_from_the_ledger(self):
        led = self.synthetic_ledger()
        with self.assertRaises(tool.DescriptiveRefusal):
            tool.build_record(ledger=led, rows_source=lambda e: (synthetic_rows(), {"fileSha256": "f" * 64}),
                              identity=STUB_IDENTITY)

    def test_stub_record_structure_and_determinism(self):
        led = self.synthetic_ledger()
        v1, f1, calls = self.build(led)
        v2, f2, _ = self.build(led)
        self.assertEqual(tool.canonical_bytes(v1), tool.canonical_bytes(v2))
        self.assertEqual(tool.canonical_bytes(f1), tool.canonical_bytes(f2))
        self.assertEqual(calls, ["synthetic-set"])
        s, = v1["sets"]
        self.assertEqual(len(s["groups"]), 2)
        for g in s["groups"]:
            self.assertEqual(len(g["curve"]), tool.CURVE_POINTS)
            self.assertEqual(len(g["points"]), 3)
            xs = [p["x"] for p in g["curve"]]
            self.assertAlmostEqual(xs[0], 0.8 * 400.0, places=3)
            self.assertAlmostEqual(xs[-1], 1.25 * 1200.0, places=1)
        dev = s["deviation"][0]
        self.assertEqual(dev["all"]["n"], 6)
        self.assertEqual(sum(b["n"] for b in dev["bins"]), 6)
        self.assertEqual(v1["modelMap"][0]["setId"], "synthetic-set")
        self.assertEqual(v1["spentLedgerSha256"], hashlib.sha256(tool.canonical_bytes(led)).hexdigest())

    def test_stub_sensitivity_beam_adds_a_second_curve_group(self):
        led = self.synthetic_ledger()
        led["entries"][0]["beam"] = {**led["entries"][0]["beam"], "status": "unverified", "sensitivity_um": 160.0}
        v, _f, _c = self.build(led)
        roles = sorted({g["beamRole"] for g in v["sets"][0]["groups"]})
        self.assertEqual(roles, ["primary", "sensitivity"])
        self.assertEqual([d["beamRole"] for d in v["sets"][0]["deviation"]], ["primary", "sensitivity"])
        self.assertIn("BEAM_ASSUMED_OR_UNVERIFIED", [n["code"] for n in v["sets"][0]["notes"]])

    def test_failed_and_unavailable_are_counted_not_dropped(self):
        led = self.synthetic_ledger()

        def mixed(alloy, P_W, v_mm_s, *a, **k):
            if v_mm_s == 400.0:
                return {"status": "failed", "reason": "EXTENT_NOT_COMPUTED", "index": 20.0}
            if v_mm_s == 800.0:
                raise RuntimeError("solver")
            return stub_served(alloy, P_W, v_mm_s, *a, **k)

        v, _f, _c = self.build(led, served=mixed)
        d = v["sets"][0]["deviation"][0]["all"]
        self.assertEqual((d["n"], d["failed"], d["unavailable"]), (2, 2, 2))
        self.assertIn("EXTENT_NOT_COMPUTED", [n["code"] for n in v["sets"][0]["notes"]])

    def test_percentile_direction_and_bins(self):
        self.assertEqual(tool.percentile([1.0, 2.0, 3.0], 50), 2.0)
        self.assertEqual(tool._direction([1, 2]), "model deeper")
        self.assertEqual(tool._direction([-1, -2]), "model shallower")
        self.assertEqual(tool._direction([-1, 2]), "mixed")
        self.assertIsNone(tool._direction([]))
        self.assertEqual([b[0] for b in tool.bin_defs("IN625")], ["below-13.6", "at-or-above-13.6"])
        self.assertEqual(len(tool.bin_defs("316L")), 3)

    def test_producer_imports_no_research_module(self):
        tree = ast.parse((PY_DIR / "tools" / "lpbf_spent_descriptive.py").read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                mods = [node.module or ""]
            for m in mods:
                self.assertNotIn("lpbf_research", m)


class CatalogueTests(unittest.TestCase):
    def test_catalogue_rules(self):
        cat = tool.load_reasons()
        self.assertIsNone(cat["reviewedBy"])
        codes = [c["code"] for c in cat["codes"]]
        self.assertEqual(sorted(codes), sorted(tool.RULES))
        for c in cat["codes"]:
            self.assertIsNone(c["expectedSign"])
            self.assertTrue(c["sentence"].startswith("Candidate explanation, not tested:"))
            self.assertTrue((tool.REPO / c["source"]).is_file())
            self.assertFalse(BANNED.search(c["sentence"]))
            self.assertFalse(DASHES.search(c["sentence"]))
        deferred = {d["code"]: d["reason"] for d in cat["deferred"]}
        for code in ("KEYHOLE_LEG_SCALING", "CONDUCTION_LEG_BIAS"):
            self.assertEqual(deferred[code], "physics sign-off pending")
        self.assertFalse(set(deferred) & set(codes))


@unittest.skipUnless(VIEWS, "no committed spent descriptive view record")
class CommittedViewRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = VIEWS[-1]
        cls.raw = cls.path.read_bytes()
        cls.view = json.loads(cls.raw)

    def test_schema_honesty_and_research(self):
        v = self.view
        self.assertEqual(v["schema"], tool.VIEW_SCHEMA)
        self.assertEqual(v["research"], {"requested": False, "reasonCode": "RESEARCH_NOT_REQUESTED"})
        h = v["honesty"]
        self.assertEqual(h["label"], "Not validation: data already seen")
        self.assertIs(h["experimentalValidation"], False)
        self.assertEqual(h["labelPromotionProposed"], "none")
        self.assertEqual(h["evidenceKind"], "screening-only")
        self.assertIs(h["spentOnly"], True)

    def test_size_under_cap_and_canonical(self):
        self.assertLess(len(self.raw), 150 * 1024)
        self.assertEqual(self.raw, tool.canonical_bytes(self.view))

    def test_no_banned_tokens_or_dashes(self):
        keys, strings = _walk(self.view)
        for text in keys + strings:
            self.assertFalse(BANNED.search(text), text[:60])
            self.assertFalse(DASHES.search(text))

    def test_sets_are_spent_and_not_forbidden(self):
        ids = [s["id"] for s in self.view["sets"]]
        self.assertEqual(sorted(ids), sorted(tool.SUPPORTED_SETS))
        for s in self.view["sets"]:
            self.assertEqual(s["spent"]["status"], "SPENT")
            self.assertNotIn(s["id"], ledger.FORBIDDEN_IDS)
            self.assertEqual(s["measuredSource"]["label"], "Measured")
            self.assertEqual(s["servedSource"]["label"], "Unresolved")
            self.assertEqual(s["servedSource"]["reasonCode"], "SERVED_VALUE_KIND_NOT_PROVIDED")
        self.assertIn("cunningham-ti64-2019", {d["datasetId"] for d in self.view["deferred"]})

    def test_notes_follow_their_rules(self):
        by = {s["id"]: s for s in self.view["sets"]}
        codes = {k: [n["code"] for n in s["notes"]] for k, s in by.items()}
        self.assertNotIn("DATUM_UNSTATED", codes["totis-ti64-2021"])
        self.assertIn("POWDER_LAYER_FLAT_PLATE_MODEL", codes["totis-ti64-2021"])
        self.assertNotIn("POWER_NOMINAL", codes["totis-ti64-2021"])
        for k in ("ku-leuven-316l-2021", "ku-leuven-ti64-2021"):
            self.assertIn("DATUM_UNSTATED", codes[k])
            self.assertNotIn("POWDER_LAYER_FLAT_PLATE_MODEL", codes[k])
        self.assertIn("POWER_NOMINAL", codes["lane-in625-amb2018-02"])
        self.assertIn("LEGACY_PROPERTIES_IN625", codes["lane-in625-amb2018-02"])
        self.assertIn("USED_IN_SERVED_DEVELOPMENT", codes["nist-amb2022-03-optical"])
        for s in self.view["sets"]:
            for n in s["notes"]:
                self.assertTrue(n["sentence"].startswith("Candidate explanation, not tested:"))

    def test_ku_beam_unverified_with_a_75_sensitivity_curve(self):
        for k in ("ku-leuven-316l-2021", "ku-leuven-ti64-2021"):
            s = next(x for x in self.view["sets"] if x["id"] == k)
            self.assertEqual(s["beam"]["value_um"], 37.5)
            self.assertEqual(s["beam"]["status"], "unverified")
            self.assertEqual(s["beam"]["sensitivity_um"], 75)
            sens = [g for g in s["groups"] if g["beamRole"] == "sensitivity"]
            self.assertTrue(sens)
            self.assertTrue(all(g["fixed"]["beam_um"] == 75 for g in sens))
            self.assertTrue(any(g["curve"] for g in sens))

    def test_in625_has_two_bins_at_13_6(self):
        s = next(x for x in self.view["sets"] if x["id"] == "lane-in625-amb2018-02")
        for d in s["deviation"]:
            self.assertEqual([b["id"] for b in d["bins"]], ["below-13.6", "at-or-above-13.6"])
        row = next(m for m in self.view["modelMap"] if m["setId"] == s["id"])
        self.assertEqual(len(row["bins"]), 2)

    def test_curves_have_25_points_and_groups_at_least_three_rows(self):
        for s in self.view["sets"]:
            for g in s["groups"]:
                if g["curve"] is not None:
                    self.assertEqual(len(g["curve"]), 25)
                    self.assertGreaterEqual(len(g["points"]), 3)
                for p in g["curve"] or []:
                    self.assertIn(p["status"], ("ok", "failed", "unavailable"))

    def test_counts_match_the_loader_rows(self):
        for s in self.view["sets"]:
            primary = [g for g in s["groups"] if g["beamRole"] == "primary"]
            self.assertEqual(sum(len(g["points"]) for g in primary), s["provenance"]["rows"])
            dev = s["deviation"][0]["all"]
            self.assertEqual(dev["n"] + dev["failed"] + dev["unavailable"], s["provenance"]["rows"])

    def test_hashes_current_against_live_files(self):
        v = self.view
        from lpbf_simulation import implementation_fingerprint
        self.assertEqual(v["implementationHash"], implementation_fingerprint())
        self.assertEqual(v["servedIdentity"]["servedClosurePinSha256"], lpbf_served_arms.pin_sha256())
        self.assertEqual(v["spentLedgerSha256"], ledger.ledger_sha256())
        self.assertEqual(v["reasonsCatalogSha256"], tool.sha256_lf(tool.REASONS_PATH))
        entries = {e["datasetId"]: e for e in ledger.load_ledger()["entries"]}
        for s in v["sets"]:
            self.assertEqual(s["provenance"]["tableSha256"], entries[s["id"]]["tableSha256"])


@unittest.skipUnless(os.environ.get("LPBF_SPENT_DESCRIPTIVE_FULL") == "1" and VIEWS,
                     "set LPBF_SPENT_DESCRIPTIVE_FULL=1 to re-derive the record (local only, not in CI)")
class FullRederivationTests(unittest.TestCase):
    def test_check_is_current(self):
        date = VIEWS[-1].name.split("_")[-1].replace(".view.json", "")
        done = subprocess.run([sys.executable, "-B", str(PY_DIR / "tools" / "lpbf_spent_descriptive.py"), "--check",
                               "--date", date], capture_output=True, text=True, cwd=PY_DIR)
        self.assertEqual(done.returncode, 0, done.stdout[-400:])


if __name__ == "__main__":
    unittest.main()
