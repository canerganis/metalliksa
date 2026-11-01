import json
from pathlib import Path
import unittest

from module_contract import contract_from_dict
from module_contracts_dataset_view import build_dataset_view_contract
from module_registry import contract_ref_problems


class DatasetViewContractTests(unittest.TestCase):
    def setUp(self):
        seed = json.loads(Path(__file__).with_name("module_registry_seed.json").read_text())
        self.contract = build_dataset_view_contract(next(r for r in seed if r["id"] == "lpbf-dataset-comparison"))

    def test_local_read_only_authority_has_no_fabricated_deadline_or_solver(self):
        self.assertEqual([o.id for o in self.contract.operations],
                         ["display-comparison-record", "display-spent-descriptive-record"])
        for operation in self.contract.operations:
            self.assertEqual(operation.authority.kind, "browser-local")
            self.assertIsNone(operation.authority.timeout_ms)
            self.assertIsNone(operation.authority.script)
            self.assertIsNone(operation.route)
            self.assertIsNone(operation.method)
        self.assertEqual(self.contract.lifecycle.background_work, "none")

    def test_nested_view_inputs_are_not_fake_numeric_fields(self):
        operation, spent = self.contract.operations
        self.assertEqual(spent.input, ())
        self.assertTrue(spent.input_problems({"laserPower_W": 300}))
        self.assertEqual(spent.output.fields, ("datasets", "curves", "deviation", "notes", "honesty"))
        self.assertIsNone(spent.output.status_key)
        self.assertEqual(operation.input, ())
        self.assertEqual(operation.input_problems({"document": {}, "kernel": "goldak", "enabledRegimes": []}), [])
        self.assertTrue(operation.input_problems({"laserPower_W": 300}))

    def test_display_does_not_promote_record_measurements_to_solver_validation(self):
        self.assertEqual(self.contract.evidence.ceiling, "screening-only")
        self.assertEqual(self.contract.evidence.emits, ())
        self.assertEqual(self.contract.tests.oracle.status, "pending")
        self.assertIn("validated", self.contract.evidence.forbidden_claims)
        self.assertEqual(contract_from_dict(self.contract.to_dict()), self.contract)

    def test_sources_resolve_and_missing_malformed_record_limits_are_declared(self):
        self.assertEqual(contract_ref_problems(self.contract,
            generated=frozenset((self.contract.tests.docs,))), [])
        notes = " ".join(self.contract.legacy_notes)
        self.assertIn("absent record", notes)
        self.assertIn("malformed", notes)
        self.assertIn("not a fresh remote source verification", notes)
        self.assertIn("spent descriptive record is loaded lazily through a non-eager import.meta.glob", notes)
        self.assertIn("its absence renders the panel's empty state", notes)


if __name__ == "__main__":
    unittest.main()
