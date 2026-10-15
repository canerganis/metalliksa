import unittest
from pathlib import Path

import module_registry as mr
from module_contract import contract_from_dict

DOC = Path(__file__).resolve().parent.parent / "docs" / "modules" / "solidification-microstructure.md"


class SolidificationMicrostructureRegistryContractTests(unittest.TestCase):
    """Self-contained: reads only the committed seed, the builder and the generated module page."""

    @classmethod
    def setUpClass(cls):
        cls.contracts = {c.id: c for c in mr.build_registry()}
        cls.contract = cls.contracts["solidification-microstructure"]

    def test_module_is_contracted_not_legacy(self):
        self.assertIn("solidification-microstructure", mr.CONTRACTED_BUILDERS)
        self.assertNotIn("solidification-microstructure", mr.LEGACY_OPERATIONS)
        self.assertEqual(self.contract.migration_state, "contracted")

    def test_operations_match_the_routes_the_view_calls(self):
        ops = {op.id: op for op in self.contract.operations}
        self.assertEqual(set(ops), {"solidification-microstructure", "gr-solidification"})
        worker = ops["solidification-microstructure"]
        self.assertEqual((worker.method, worker.route, worker.authority.kind,
                          worker.authority.worker_method, worker.authority.timeout_ms),
                         ("POST", "/api/python/lpbf-solidification-microstructure", "lpbf-worker",
                          "solidification-microstructure", 20000))
        gr = ops["gr-solidification"]
        self.assertEqual((gr.method, gr.route, gr.authority.kind, gr.authority.script,
                          gr.authority.timeout_ms, gr.authority.warm),
                         ("POST", "/api/python/lpbf-gr-solidification", "python-ipc",
                          "python/lpbf_gr_solidification.py", 60000, False))
        for op in ops.values():
            self.assertIsNone(op.output.status_key)
            self.assertNotIn("evidence", op.output.fields)  # reserved by the SDK; named in the notes
        self.assertLessEqual({"regime", "quantities", "quantityEnvelopeSchema"}, set(worker.output.fields))

    def test_screening_ceiling_and_no_emitted_status(self):
        self.assertEqual(self.contract.evidence.ceiling, "screening-only")
        self.assertEqual(self.contract.evidence.emits, ())
        self.assertEqual(self.contract.tests.oracle.status, "pending")
        self.assertEqual(self.contract.tests.docs, "docs/modules/solidification-microstructure.md")
        self.assertEqual(contract_from_dict(self.contract.to_dict()), self.contract)
        notes = " ".join(self.contract.legacy_notes)
        self.assertIn("SDK-reserved", notes)
        self.assertIn("experimental validation", notes)

    def test_every_reference_resolves(self):
        generated = frozenset(mr.module_doc_path(c.id) for c in self.contracts.values()
                              if c.migration_state == "contracted")
        self.assertEqual(mr.contract_ref_problems(self.contract, generated=generated), [])

    def test_committed_doc_states_inputs_outputs_and_limits(self):
        text = DOC.read_text(encoding="utf-8")
        for needle in ("`solidification-microstructure`", "`gr-solidification`", "sourceChecks",
                       "lpbf-solidification-microstructure-2", "Ceiling: screening-only"):
            self.assertIn(needle, text)
        stray = [ln for ln in text.splitlines() if "\u2014" in ln and not ln.startswith("\u2014 = ")]
        self.assertEqual(stray, [])


if __name__ == "__main__":
    unittest.main()
