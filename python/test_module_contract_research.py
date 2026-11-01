import json
import unittest
from pathlib import Path

import module_registry
from module_contract import ModuleContract, contract_from_dict
from module_contracts_research import build_research_hub_contract


ROOT = Path(__file__).resolve().parents[1]


class ResearchHubContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rows = json.loads((ROOT / "python" / "module_registry_seed.json").read_text(encoding="utf-8"))
        cls.seed = next(row for row in rows if row["id"] == "research-hub")
        cls.contract = build_research_hub_contract(cls.seed)
        cls.operations = {operation.id: operation for operation in cls.contract.operations}

    def test_builder_preserves_research_hub_seed_and_reachable_modes(self):
        contract = self.contract

        self.assertIsInstance(contract, ModuleContract)
        self.assertEqual((contract.id, contract.workspace, contract.label, contract.description,
                          contract.next, contract.maturity),
                         ("research-hub", "evidence", self.seed["label"], self.seed["description"],
                          self.seed["next"], self.seed["scope"]))
        self.assertEqual(contract.seed_derived, ("label", "description", "next", "maturity"))
        self.assertEqual(contract.view.component, "src/components/AdvancedResearchHub.tsx")
        self.assertEqual(contract.view.export, "AdvancedResearchHub")
        self.assertEqual(set(self.operations), {
            "select-workflow-tab", "select-research-brief", "select-extraction-source",
            "edit-form-draft", "use-search-metadata", "filter-saved-sources",
            "create-brief", "search-crossref-metadata", "register-source", "edit-source", "save-extraction",
            "revise-extraction", "review-extraction", "link-reviewed-finding", "compare-findings",
            "flag-finding-conflict", "record-feedback", "check-server-registry", "save-server-revision",
            "read-server-revision", "apply-reviewed-server-merge", "import-registry-json",
            "export-registry-json", "export-browser-recovery-copy", "browse-measured-track-catalog",
            "validate-measured-track-intake", "download-blind-test-templates", "edit-blind-test-metadata",
            "check-blind-test-headers", "render-blind-test-report", "export-blind-test-report",
            "blind-test-estimate", "blind-test-job-submit", "blind-test-job-poll", "blind-test-job-artifact",
        })
        self.assertEqual(contract.tests.oracle.status, "pending")
        self.assertEqual(contract.evidence.ceiling, "screening-only")
        self.assertEqual(contract.evidence.emits, ())
        self.assertEqual(contract.lifecycle.background_work, "server-job")
        self.assertEqual(contract.lifecycle.resources, ("fetch", "interval"))

    def test_server_and_crossref_authorities_match_live_routes_and_deadlines(self):
        search = self.operations["search-crossref-metadata"]
        check = self.operations["check-server-registry"]
        save = self.operations["save-server-revision"]
        revision = self.operations["read-server-revision"]

        self.assertEqual((search.method, search.route, search.authority.kind, search.authority.timeout_ms),
                         ("GET", "/api/research/search", "node-provider", 20000))
        self.assertEqual((check.method, check.route, check.authority.timeout_ms),
                         ("GET", "/api/research/registry", 12000))
        self.assertEqual((save.method, save.route, save.authority.timeout_ms),
                         ("PUT", "/api/research/registry", 12000))
        self.assertEqual((revision.method, revision.route, revision.undeclared_input),
                         ("GET", "/api/research/registry/revisions/:revision", ("revision",)))
        self.assertEqual(save.undeclared_input, ("registryId", "expectedRevision", "snapshot"))

        service = (ROOT / "src/services/researchRegistrySync.ts").read_text(encoding="utf-8")
        search_view = (ROOT / "src/components/research/ResearchSourcesPanel.tsx").read_text(encoding="utf-8")
        search_route = (ROOT / "routes/research.ts").read_text(encoding="utf-8")
        provider = (ROOT / "server/researchSearch.ts").read_text(encoding="utf-8")
        self.assertIn("timeoutMs: 12000", service)
        self.assertIn("expectedRevision: remote.revision, snapshot", service)
        self.assertIn("request(`/revisions/${revision}`)", service)
        self.assertIn("setTimeout(() => controller.abort(), 20000)", search_view)
        self.assertIn("fetch(`/api/research/search?q=", search_view)
        self.assertIn("setTimeout(() => controller.abort(), 12000)", search_route)
        self.assertIn("activeRequests >= 3", search_route)
        self.assertIn("api.crossref.org/works", provider)

    def test_blind_test_routes_use_worker_authorities_and_local_checks(self):
        expected = {
            "blind-test-estimate": ("POST", "/api/lpbf/estimate", "estimate"),
            "blind-test-job-submit": ("POST", "/api/lpbf/jobs", "submit"),
            "blind-test-job-poll": ("GET", "/api/lpbf/jobs/:id", "get"),
            "blind-test-job-artifact": ("GET", "/api/lpbf/jobs/:id/artifacts/:name", "artifact"),
        }
        for operation_id, (method, route, worker_method) in expected.items():
            operation = self.operations[operation_id]
            self.assertEqual((operation.method, operation.route, operation.authority.kind,
                              operation.authority.worker_method), (method, route, "lpbf-worker", worker_method))
        for operation_id in ("download-blind-test-templates", "edit-blind-test-metadata", "check-blind-test-headers",
                             "render-blind-test-report", "export-blind-test-report"):
            operation = self.operations[operation_id]
            self.assertEqual((operation.route, operation.method, operation.authority.kind),
                             (None, None, "browser-local"))
        notes = " ".join(self.contract.legacy_notes)
        self.assertNotIn("No polling, interval, server job or background analysis", notes)
        self.assertIn("Only the Your blind test tab polls", notes)

    def test_ui_actions_track_store_payloads_and_distinguish_user_labels(self):
        local = {operation_id: self.operations[operation_id] for operation_id in (
            "save-extraction", "review-extraction", "link-reviewed-finding", "record-feedback",
            "import-registry-json", "export-registry-json", "export-browser-recovery-copy",
        )}
        self.assertEqual(local["save-extraction"].undeclared_input[-3:],
                         ("validationReference", "targetModule", "reviewNote"))
        self.assertEqual(local["review-extraction"].undeclared_input, ("id", "note"))
        self.assertEqual(local["record-feedback"].undeclared_input,
                         ("findingId", "outcome", "experimentOrJobReference", "note"))
        self.assertEqual(set(local["export-registry-json"].output.fields),
                         {"schemaVersion", "briefs", "sources", "findings", "integrations", "feedback"})
        self.assertIn("browserDrafts", local["export-browser-recovery-copy"].output.fields)
        self.assertTrue(all(operation.route is None and operation.method is None
                            and operation.authority.kind == "browser-local" for operation in local.values()))

        store = (ROOT / "src/store/useResearchStore.ts").read_text(encoding="utf-8")
        extraction = (ROOT / "src/components/research/ResearchExtractionPanel.tsx").read_text(encoding="utf-8")
        registry = (ROOT / "src/components/research/ResearchRegistryPanel.tsx").read_text(encoding="utf-8")
        self.assertIn("state.addFinding(input)", extraction)
        self.assertIn("state.reviseFinding(draft.editId, input)", extraction)
        self.assertIn("reviewStatus: 'reviewed'", store)
        self.assertIn("input.outcome === 'contradicts'", store)
        self.assertIn("No automatic validation promotion was made.", registry)
        self.assertIn("measured", " ".join(self.contract.legacy_notes))
        self.assertIn("not independent", self.contract.evidence.note)

    def test_sources_resolve_with_only_parent_generated_doc_exempted(self):
        generated_doc = module_registry.module_doc_path("research-hub")
        self.assertEqual(self.contract.tests.docs, generated_doc)
        problems = module_registry.contract_ref_problems(
            self.contract, root=ROOT, generated=frozenset({generated_doc})
        )
        self.assertEqual(problems, [])

    def test_contract_roundtrip_and_wrong_seed_guard(self):
        self.assertEqual(contract_from_dict(self.contract.to_dict()), self.contract)
        wrong_seed = {**self.seed, "id": "experimental-data"}
        with self.assertRaises(ValueError):
            build_research_hub_contract(wrong_seed)


if __name__ == "__main__":
    unittest.main()
