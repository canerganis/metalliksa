"""Spent ledger checks (research hub spec 8.1): schema, closed vocabulary, licence fields. Metadata only."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

import lpbf_spent_ledger as ledger


class SpentLedgerTests(unittest.TestCase):
    def setUp(self):
        self.doc = ledger.load_ledger()
        self.entries = self.doc["entries"]

    def test_schema_and_required_keys(self):
        self.assertEqual(self.doc["schema"], ledger.SCHEMA)
        self.assertEqual(len(self.entries), 6)
        for e in self.entries:
            self.assertEqual(set(e), set(ledger.REQUIRED))

    def test_closed_vocabulary(self):
        for e in self.entries:
            self.assertIn(e["status"], ledger.STATUSES)
            self.assertIn(e["observable"], ledger.OBSERVABLES)
            self.assertIn(e["transcription"], ledger.TRANSCRIPTION)
            self.assertIn(e["curveAxis"], ("speed", "power"))
            self.assertIn(e["beam"]["status"], ("stated", "assumed", "unverified"))
            self.assertIsInstance(e["usedInServedDevelopment"], bool)

    def test_licence_fields_and_files_exist(self):
        for e in self.entries:
            for k in ("licence", "attribution", "licenceFile"):
                self.assertTrue(e[k].strip())
            if e["licenceFile"] != "none":
                self.assertTrue((ledger.REPO_ROOT / e["licenceFile"]).is_file())

    def test_no_forbidden_id_in_the_ledger(self):
        for e in self.entries:
            self.assertNotIn(e["datasetId"], ledger.FORBIDDEN_IDS)

    def test_ledger_holds_no_measured_columns(self):
        banned = {"depth_um", "width_um", "rows", "measured"}
        for e in self.entries:
            self.assertFalse(banned & set(e))

    def test_entry_without_licence_or_with_unknown_key_is_refused(self):
        bad = copy.deepcopy(self.entries[0])
        bad["licence"] = " "
        with self.assertRaises(ledger.SpentLedgerError):
            ledger.validate_entry(bad)
        extra = copy.deepcopy(self.entries[0])
        extra["surprise"] = 1
        with self.assertRaises(ledger.SpentLedgerError):
            ledger.validate_entry(extra)
        outside = copy.deepcopy(self.entries[0])
        outside["status"] = "MAYBE"
        with self.assertRaises(ledger.SpentLedgerError):
            ledger.validate_entry(outside)

    def test_unknown_schema_and_duplicate_ids_are_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "l.json"
            p.write_text(json.dumps({"schema": "other", "entries": []}), encoding="utf-8")
            with self.assertRaises(ledger.SpentLedgerError):
                ledger.load_ledger(p)
            p.write_text(json.dumps({"schema": ledger.SCHEMA, "entries": [self.entries[0], self.entries[0]]}),
                         encoding="utf-8")
            with self.assertRaises(ledger.SpentLedgerError):
                ledger.load_ledger(p)

    def test_hash_ignores_line_endings(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d) / "a.json", Path(d) / "b.json"
            a.write_bytes(b"{\n}\n")
            b.write_bytes(b"{\r\n}\r\n")
            self.assertEqual(ledger.ledger_sha256(a), ledger.ledger_sha256(b))


if __name__ == "__main__":
    unittest.main()
