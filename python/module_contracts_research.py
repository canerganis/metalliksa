"""Source-bounded Module SDK contract for the Research Hub and its reachable panels."""

from typing import Mapping, Tuple

from module_contract import (
    FORBIDDEN_CLAIM_KEYS,
    OWNER_UNASSIGNED,
    PENDING_ORACLE_CEILING,
    Authority,
    Evidence,
    Lifecycle,
    ModuleContract,
    Operation,
    Oracle,
    OutputSchema,
    TestRefs,
    View,
)


CONTRACT_VERSION = "0.1.0"
_REGISTRY_ENVELOPE = ("registryId", "revision", "savedAt", "snapshot")
_SNAPSHOT = ("schemaVersion", "briefs", "sources", "findings", "integrations", "feedback")
_ACTION_RESULT = ("id", "errors")


def _local(operation_id: str, inputs: Tuple[str, ...], outputs: Tuple[str, ...]) -> Operation:
    return Operation(
        id=operation_id,
        route=None,
        method=None,
        authority=Authority(
            kind="browser-local",
            exception_reason=(
                "ResearchHub reads/writes the Zustand research store, browser drafts, static catalog or "
                "downloads locally; it does not dispatch this action to a server."
            ),
        ),
        undeclared_input=inputs,
        output=OutputSchema(fields=outputs, status_key=None),
    )


def _remote(operation_id: str, method: str, route: str, timeout_ms: int,
            inputs: Tuple[str, ...], outputs: Tuple[str, ...]) -> Operation:
    return Operation(
        id=operation_id,
        method=method,
        route=route,
        authority=Authority(kind="node-provider", timeout_ms=timeout_ms),
        undeclared_input=inputs,
        output=OutputSchema(fields=outputs, status_key=None),
    )


_WORKER_TIMEOUT_MS = 20000  # server/lpbfWorkerBridge.ts requestTimeoutMs default (same value as module_registry)
_BLIND_REQUEST_KEYS = (
    "jobType", "schema", "metadata", "inputsCsvBase64", "inputsFileName", "previewSha256", "overlapSha256",
    "acknowledgements", "freezeKey", "confirmation", "revealConfirmation", "targetsCsvBase64", "targetsFileName",
    "declarations", "acceptCommitmentMismatch", "name", "attempt", "page", "pageSize",
)


def _worker_remote(operation_id: str, method: str, route: str, worker_method: str,
                   inputs: Tuple[str, ...], outputs: Tuple[str, ...]) -> Operation:
    """A bound lpbf-worker route (the Your blind test tab); same authority as the _worker entries of module_registry."""
    return Operation(
        id=operation_id,
        method=method,
        route=route,
        authority=Authority(kind="lpbf-worker", worker_method=worker_method, timeout_ms=_WORKER_TIMEOUT_MS),
        undeclared_input=inputs,
        output=OutputSchema(fields=outputs, status_key=None),
    )


_SOURCE_FIELDS = ("briefId", "title", "authors", "year", "doi", "url", "sourceType", "confidence", "notes")
_FINDING_FIELDS = (
    "briefId", "sourceId", "materialId", "materialName", "property", "value", "unit", "rangeLow", "rangeHigh",
    "uncertainty", "uncertaintyDescription", "conditions", "locator", "evidenceType", "confidence", "limitations",
    "validationReference", "targetModule", "reviewNote",
)


def _operations() -> Tuple[Operation, ...]:
    return (
        _local("select-workflow-tab", ("activeTab",), ("activeTab",)),
        _local("select-research-brief", ("activeBriefId",), ("activeBriefId", "activeSourceId")),
        _local("select-extraction-source", ("activeSourceId",), ("activeSourceId", "activeTab")),
        _local("edit-form-draft", ("key", "value"), ("drafts",)),
        _local("use-search-metadata", ("source",), ("sourceDraft", "errors")),
        _local("filter-saved-sources", ("filter",), ("visibleSources",)),
        _local("create-brief", ("question", "alloy", "process", "method", "dataType"), _ACTION_RESULT),
        _remote("search-crossref-metadata", "GET", "/api/research/search", 20000,
                ("q",), ("provider", "retrievedAt", "scope", "items")),
        _local("register-source", _SOURCE_FIELDS, _ACTION_RESULT),
        _local("edit-source", ("id",) + _SOURCE_FIELDS, _ACTION_RESULT),
        _local("save-extraction", _FINDING_FIELDS, _ACTION_RESULT),
        _local("revise-extraction", ("id",) + _FINDING_FIELDS, _ACTION_RESULT),
        _local("review-extraction", ("id", "note"), _ACTION_RESULT),
        _local("link-reviewed-finding", ("id", "target"), _ACTION_RESULT),
        _local("compare-findings", ("compareA", "compareB"), ("comparison",)),
        _local("flag-finding-conflict", ("id", "otherId", "flagged"), _ACTION_RESULT),
        _local("record-feedback", ("findingId", "outcome", "experimentOrJobReference", "note"), _ACTION_RESULT),
        _remote("check-server-registry", "GET", "/api/research/registry", 12000,
                (), _REGISTRY_ENVELOPE),
        _remote("save-server-revision", "PUT", "/api/research/registry", 12000,
                ("registryId", "expectedRevision", "snapshot"), _REGISTRY_ENVELOPE),
        _remote("read-server-revision", "GET", "/api/research/registry/revisions/:revision", 12000,
                ("revision",), _REGISTRY_ENVELOPE),
        # apply() does not return a value; this is the browser snapshot after acceptServerSnapshot commits it.
        _local("apply-reviewed-server-merge", ("choices",), _SNAPSHOT),
        _local("import-registry-json", ("value",), ("errors",)),
        _local("export-registry-json", (), _SNAPSHOT),
        _local("export-browser-recovery-copy", (), _SNAPSHOT + ("browserDrafts",)),
        _local("browse-measured-track-catalog", (), ("cases",)),
        _local("validate-measured-track-intake", ("row",), ("ok", "reason")),
        # Your blind test tab (spec research_hub_data section 3.4). Browser checks are convenience only; the worker
        # repeats every check and is the only authority for numbers, statuses and labels.
        _local("download-blind-test-templates", (), ("inputsCsv", "targetsCsv", "metadataJson")),
        _local("edit-blind-test-metadata", ("field", "value"), ("draft",)),
        _local("check-blind-test-headers", ("fileHead", "csvDialect"), ("issues", "warnings", "mapped")),
        _local("render-blind-test-report", ("report",), ("reportView",)),
        _local("export-blind-test-report", ("name", "attempt"), ("download",)),
        _worker_remote("blind-test-estimate", "POST", "/api/lpbf/estimate", "estimate",
                       _BLIND_REQUEST_KEYS, ("schema", "honesty")),
        _worker_remote("blind-test-job-submit", "POST", "/api/lpbf/jobs", "submit",
                       _BLIND_REQUEST_KEYS, ("id",)),
        _worker_remote("blind-test-job-poll", "GET", "/api/lpbf/jobs/:id", "get",
                       ("id",), ("id", "result", "error", "blindError")),
        _worker_remote("blind-test-job-artifact", "GET", "/api/lpbf/jobs/:id/artifacts/:name", "artifact",
                       ("id", "name"), ("content",)),
    )


def build_research_hub_contract(seed: Mapping[str, str]) -> ModuleContract:
    """Build the Research Hub contract from its seed row without registering or editing outputs."""
    if seed["id"] != "research-hub":
        raise ValueError("Research Hub contract must preserve the research-hub seed identity")
    return ModuleContract(
        id=seed["id"],
        version=CONTRACT_VERSION,
        owner=OWNER_UNASSIGNED,
        workspace=seed["workspace"],
        label=seed["label"],
        description=seed["description"],
        next=seed["next"],
        maturity=seed["scope"],
        navigation="listed",
        view=View(component=seed["viewComponent"], export=seed["viewExport"]),
        evidence=Evidence(
            emits=(),
            ceiling=PENDING_ORACLE_CEILING,
            forbidden_claims=FORBIDDEN_CLAIM_KEYS,
            note=(
                "Oracle pending. Bibliographic metadata, user-entered finding labels, user review and feedback are "
                "traceability records; they are not independent experimental validation or solver qualification."
            ),
        ),
        tests=TestRefs(
            oracle=Oracle(status="pending"),
            schema="python/test_module_contract_research.py",
            docs="docs/modules/research-hub.md",
        ),
        migration_state="contracted",
        operations=_operations(),
        lifecycle=Lifecycle(background_work="server-job", resources=("fetch", "interval")),
        legacy_notes=(
            "The rendered child modes are Research brief, Literature & sources, Data extraction, Registry & feedback, "
            "Measured track catalog, and Your blind test. Briefs, sources, findings, review, comparison, module links, conflicts and "
            "feedback are user-driven browser-store operations. Data extraction transcribes a reported value and "
            "unit plus material, composition, process, machine, parameters, powder condition, heat treatment, "
            "measurement method, source locator, uncertainty, limitations, evidence type, confidence, validation "
            "reference and target. Because the SDK cannot represent the nested conditions map or variable unit, "
            "those request keys remain undeclared rather than receiving fabricated scalar fields.",
            "The browser persists snapshots and string-valued form drafts in localStorage. A detected competing-tab "
            "write, parse error, unavailable storage or quota issue pauses writes and keeps the in-memory records for "
            "a recovery-copy export. Normal export contains schemaVersion and briefs/sources/findings/integrations/feedback; "
            "the recovery copy also includes browserDrafts. JSON import is capped at 10 MiB, validates the snapshot, "
            "merges by record id, and refuses changed records with an existing id while preserving existing data.",
            "Server sync is explicit: Check reads the current envelope and may read a saved ancestor revision; "
            "Apply reviewed combination changes only browser state; Save sends registryId, expectedRevision and snapshot "
            "to create a new compare-and-swap revision. The server stores immutable numbered JSON revisions on its "
            "local filesystem, has no registry-specific accounts or per-record access control (the server's "
            "global login boundary still applies), caps JSON/snapshot size at 10 MiB and uses a "
            "write lock. A 409 requires rechecking; storage/busy errors do not reset saved data. The history endpoint "
            "exists but this hub does not call it. Current and selected server revision exports are browser downloads.",
            "Crossref is the only search provider called by this hub. Search sends q to the local same-origin route; "
            "the server queries Crossref bibliographic metadata (maximum 12 items), not full text. Browser cancellation "
            "timeout is 20000 ms; the server aborts the upstream request at 12000 ms and limits concurrent searches "
            "to three. Airgap refusal is 403; provider errors/rate limits surface as 4xx/5xx. Search metadata only "
            "prefills a source draft; the user must inspect the original source and save it. The Open Crossref control "
            "navigates directly to search.crossref.org. No LLM, automatic extraction, literature full-text fetch, or "
            "materials/physics analysis endpoint is called by these child modes.",
            "Source confidence, finding confidence, evidenceType (including measured), reviewStatus=reviewed and "
            "validationReference are user-entered/reviewed labels. Review checks completeness, source linkage, locator, "
            "method, limitations and rationale; a validated/calibrated-simulation label only requires a supplied "
            "reference string. Neither review nor a DOI syntax check independently verifies source content or validates "
            "a solver. Contradictory feedback withdraws the review and module link; supporting feedback does not promote "
            "evidence automatically. Comparison is descriptive formatting of two saved records, not statistical or "
            "physical analysis. Module links expose reviewed evidence and do not replace solver inputs.",
            "The Measured track catalog displays committed literature-case rows. Its candidate intake form performs "
            "local completeness and positive-number checks and rejects recognizable solver-echo labels; it does not "
            "resolve the DOI, persist a record, edit the catalog, fit a solver or validate measurements. The separate "
            "research-registry history API and other application providers are not called from this view.",
            "Network requests occur only after explicit search/check/save/revision-export actions. Fetch deadline timers "
            "clear in request finally blocks; source search aborts on unmount, while registry sync lives outside "
            "the component. Downloads schedule URL revocation after one second, without an unmount timer cleanup. "
            "The lifecycle vocabulary has no timeout resource, so these are described here rather than mislabeled as intervals. Only the Your blind test "
            "tab polls: while the hub is visible it follows its own queued blind jobs (freeze, reveal, score, bundle and open) with one request to "
            "GET /api/lpbf/jobs/:id per step, pauses when the hub is hidden, resumes from the job ids kept in the browser after a reload, and stops "
            "when each job ends. A job starts only from a button press. No other tab polls or launches background work.",
        "The Your blind test tab lets a user freeze the app's served predictions for their own tracks and later score their own measurements "
            "against them. Python is the only authority for every number, status and label: the browser renders the documents, checks file headers "
            "before upload (convenience only, the worker repeats every check), hashes a targets file with SubtleCrypto and never computes a "
            "statistic. The tab uses the bound worker routes POST /api/lpbf/estimate (preview, list, get), POST /api/lpbf/jobs, "
            "GET /api/lpbf/jobs/:id and GET /api/lpbf/jobs/:id/artifacts/:name, all same-origin. User values are labelled Measured (user-supplied) "
            "with Trust tier Declared, served model values are labelled Unresolved, and the module ceiling stays Screening only. The research arm "
            "is not requested in this version and the tab has no research opt-in. The browser keeps only the metadata draft, queued job ids and "
            "receipt summaries; it never stores file text, predictions or measurements.",
        ),
        source_refs=(
            "src/components/AdvancedResearchHub.tsx::AdvancedResearchHub",
            "src/components/AdvancedResearchHub.tsx::tabs",
            "src/components/AdvancedResearchHub.tsx::exportRegistry",
            "src/components/research/ResearchControls.tsx::useDraft",
            "src/components/research/BlindTestPanel.tsx::BlindTestPanel",
            "src/components/research/BlindTestMetadataForm.tsx::BlindTestMetadataForm",
            "src/components/research/BlindTestInputsStep.tsx::BlindTestInputsStep",
            "src/components/research/BlindTestTargetsStep.tsx::BlindTestTargetsStep",
            "src/components/research/BlindTestReportView.tsx::BlindTestReportView",
            "src/data/lpbfUserBlind.ts::checkedBlindReport",
            "src/services/lpbfUserBlindClient.ts::createBlindClient",
            "src/store/useUserBlindStore.ts::useUserBlindStore",
            "python/lpbf_user_blind.py::validate_request",
            "src/components/research/ResearchSourcesPanel.tsx::ResearchSourcesPanel",
            "src/components/research/ResearchSourcesPanel.tsx:19-24#api/research/search",
            "src/components/research/ResearchExtractionPanel.tsx::ResearchExtractionPanel",
            "src/components/research/ResearchExtractionPanel.tsx:15-20#state.addFinding(input)",
            "src/components/research/ResearchRegistryPanel.tsx::ResearchRegistryPanel",
            "src/components/research/ResearchRegistryPanel.tsx:11-16#compareResearchFindings",
            "src/components/research/ResearchRegistryPanel.tsx:32-32#state.addFeedback",
            "src/components/research/ResearchSyncPanel.tsx::ResearchSyncPanel",
            "src/components/research/ResearchSyncPanel.tsx:21-26#researchRegistrySync.check",
            "src/components/research/ResearchSyncPanel.tsx:32-34#readRevision",
            "src/components/MeltPoolMeasuredTrackPanel.tsx::validateMeasuredTrackIntake",
            "src/components/MeltPoolMeasuredTrackPanel.tsx::MeltPoolMeasuredTrackPanel",
            "src/store/useResearchStore.ts:112-124#addBrief",
            "src/store/useResearchStore.ts:131-148#reviseFinding",
            "src/store/useResearchStore.ts:149-180#addFeedback",
            "src/store/useResearchStore.ts:181-205#exportSnapshot",
            "src/services/researchRegistrySync.ts:15-21#timeoutMs: 12000",
            "src/services/researchRegistrySync.ts:45-46#/revisions/${base.revision}",
            "src/services/researchRegistrySync.ts:73-80#expectedRevision",
            "routes/research.ts:7-15#activeRequests >= 3",
            "routes/research.ts:15-31#controller.abort()",
            "routes/researchRegistry.ts:17-29#api/research/registry",
            "server/researchSearch.ts:13-28#api.crossref.org",
            "server/researchEvidenceRegistry.ts:26-26#One local, unauthenticated registry",
            "server/researchEvidenceRegistry.ts:163-165#save(registryId",
            "src/types/research.ts:43-68#export interface ResearchFinding",
            "src/utils/researchRegistry.ts:33-50#export function validateResearchFinding",
            "src/utils/researchRegistry.ts:52-83#export function researchReviewIssues",
            "src/utils/researchRegistry.ts:85-94#export function compareResearchFindings",
            "src/utils/researchRegistry.ts:95-142#export function parseResearchSnapshot",
            "src/data/meltPoolLiteratureCases.ts:92-156#MELT_POOL_LITERATURE_CASES",
            "src/data/meltPoolLiteratureCases.ts:157-167#MEASURED_TRACK_INTAKE_FIELDS",
        ),
        seed_derived=("label", "description", "next", "maturity"),
    )
