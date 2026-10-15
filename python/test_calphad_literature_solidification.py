"""IN718 / IN625 requests carry a read-only literature estimate (unavailable or successful CALPHAD result); CALPHAD fields are unchanged."""
import importlib.util
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

import calphad_solver
import lpbf_solidification_segregation as seg
from quantity_envelope import envelope_problems

HERE = Path(__file__).resolve().parent
# With pycalphad installed (default runtime since the MatCalc TDBs), the subprocess runs a real IN718/IN625
# equilibrium that takes minutes on a loaded machine; run it only in the slow lane.
HAS_PYCALPHAD = importlib.util.find_spec("pycalphad") is not None
SLOW = os.environ.get("METALLIX_SLOW_TESTS") == "1"
IN718 = {"Ni": 52.5, "Cr": 19.0, "Fe": 18.5, "Nb": 5.1, "Mo": 3.0, "Ti": 0.9, "Al": 0.5, "C": 0.04}
IN625 = {"Ni": 61.0, "Cr": 21.5, "Mo": 9.0, "Nb": 3.65, "Fe": 4.0, "Ti": 0.2, "Al": 0.2, "C": 0.05}
SS316L = {"Fe": 65.5, "Cr": 17.0, "Ni": 12.0, "Mo": 2.5, "Mn": 2.0, "Si": 0.75, "C": 0.03}


def run(name, elements, alloy_id=None):
    payload = {"name": name, "elements": elements, "unit": "wt_pct", "tMin": 500, "tMax": 1450, "tStep": 50}
    if alloy_id:
        payload["literatureAlloyId"] = alloy_id
    proc = subprocess.run([sys.executable, str(HERE / "calphad_solver.py"), "-"], input=json.dumps(payload),
                          capture_output=True, text=True, cwd=str(HERE), timeout=900 if HAS_PYCALPHAD else 120)
    return json.loads(proc.stdout)


class LiteratureSolidificationTests(unittest.TestCase):
    def test_block_matches_segregation_estimate_for_in718(self):
        b = calphad_solver.literature_solidification_block("in718")
        est = seg.segregation_estimate("in718")
        self.assertEqual(b["status"], "computed")
        self.assertFalse(b["isCalphad"])
        self.assertEqual(b["quantities"], est["quantities"])
        self.assertEqual(envelope_problems(b), [])
        self.assertNotIn("evidenceLabel", b)
        self.assertIn("weld", b["source"])
        self.assertIn("not LPBF", b["source"])
        ks = {k["id"]: k for k in b["kValues"]}
        self.assertEqual(set(ks), {"k_gamma_Nb", "k_gamma_C"})
        for k in ks.values():
            self.assertTrue(k["citation"] and k["locator"])
            self.assertEqual(k["value"], est["constants"][k["id"]]["value"])
        self.assertEqual(b["band"], est["band"])
        self.assertTrue(b["validity"]["outsideSourceRegime"])
        self.assertIn("upper bound", b["upperBoundNote"])
        self.assertIn("rapid-solidification", b["rapidSolidificationNote"])

    def test_block_matches_segregation_estimate_for_in625(self):
        b = calphad_solver.literature_solidification_block("IN625")
        est = seg.segregation_estimate("in625")
        self.assertEqual(b["alloyId"], "in625")
        ks = {k["id"]: k for k in b["kValues"]}
        self.assertEqual(set(ks), {"k_gamma_Nb", "k_gamma_Nb_slopes"})
        self.assertIn("Cieslak", ks["k_gamma_Nb"]["citation"])
        self.assertEqual(b["quantities"], est["quantities"])
        self.assertEqual(envelope_problems(b), [])
        self.assertNotIn("evidenceLabel", b)
        self.assertEqual(b["kSensitivity"], est["kSensitivity"])

    def test_other_ids_are_refused(self):
        for aid in (None, "", "ss316l", "316l", "ti6al4v", "in738"):
            self.assertIsNone(calphad_solver.literature_solidification_block(aid))

    @unittest.skipIf(HAS_PYCALPHAD and not SLOW, "real CALPHAD solve; set METALLIX_SLOW_TESTS=1")
    def test_response_field_and_unchanged_calphad_status(self):
        base = run("Inconel 718", IN718)
        with_lit = run("Inconel 718", IN718, "in718")
        self.assertEqual(base["status"], with_lit["status"])
        self.assertNotIn("literatureSolidification", base)
        lit = with_lit.pop("literatureSolidification")
        self.assertEqual(lit["alloyId"], "in718")
        self.assertTrue(all(q["sourceEvidenceKind"] == "Unresolved" for q in lit["quantities"].values()))
        self.assertTrue(lit["source"])
        # every CALPHAD field is identical with and without the literature block
        for key in ("provenance",):
            base.pop(key, None)
            with_lit.pop(key, None)
        self.assertEqual(base, with_lit)
        lit625 = run("Inconel 625", IN625, "in625")
        self.assertEqual(lit625["literatureSolidification"]["alloyId"], "in625")

    def test_attached_next_to_a_successful_calphad_result_without_touching_it(self):
        """The default interpreter has no pycalphad, so a successful result is simulated; the attach helper is the same code main() calls."""
        ok = {"status": "computed", "success": True, "criticalTemperatures": {"liquidusC": 1350.4},
              "scheilSolidification": {"status": "pycalphad-scheil-gulliver", "phaseAmounts": {"LAVES": 0.0086}},
              "knownDeviations": [{"systemId": "in718", "notes": ["Do not use the Scheil LAVES amount"]}]}
        before = json.loads(json.dumps(ok))
        out = calphad_solver.attach_literature_solidification(ok, "in718")
        lit = out.pop("literatureSolidification")
        self.assertEqual(lit, calphad_solver.literature_solidification_block("in718"))
        self.assertEqual(out, before)
        self.assertEqual(calphad_solver.attach_literature_solidification(dict(before), "in625")["literatureSolidification"]["alloyId"], "in625")
        for aid in (None, "ss316l", "316l", "in718x"):
            self.assertNotIn("literatureSolidification", calphad_solver.attach_literature_solidification(dict(before), aid))

    @unittest.skipIf(HAS_PYCALPHAD and not SLOW, "real CALPHAD solve; set METALLIX_SLOW_TESTS=1")
    def test_316l_and_unknown_ids_get_no_block(self):
        for alloy_id in (None, "ss316l", "in718x"):
            res = run("316L", SS316L, alloy_id)
            self.assertNotIn("literatureSolidification", res)

    def test_ts_fixture_is_current(self):
        """tests/calphad-literature-solidification.test.tsx renders this file; regenerate with --write-fixture."""
        self.assertEqual(json.loads(FIXTURE.read_text(encoding="utf-8")), fixture_blocks())


FIXTURE = HERE.parent / "tests" / "fixtures" / "calphad-literature-solidification.json"


def fixture_blocks():
    return {aid: calphad_solver.literature_solidification_block(aid) for aid in ("in718", "in625")}


if __name__ == "__main__":
    if "--write-fixture" in sys.argv:
        FIXTURE.write_text(json.dumps(fixture_blocks(), indent=1, sort_keys=True) + chr(10), encoding="utf-8")
        sys.exit(0)
    unittest.main()
