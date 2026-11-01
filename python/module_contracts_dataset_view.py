"""Contract for the read-only, committed LPBF comparison record view."""
from module_contract import (
    Authority, Evidence, FORBIDDEN_CLAIM_KEYS, Lifecycle, ModuleContract,
    Operation, Oracle, OWNER_UNASSIGNED, OutputSchema, TestRefs, View,
)


def build_dataset_view_contract(seed):
    return ModuleContract(
        id=seed["id"], version="0.1.0", owner=OWNER_UNASSIGNED,
        workspace=seed["workspace"], label=seed["label"],
        description=seed["description"], next=seed["next"], maturity=seed["scope"],
        navigation="listed", view=View(component=seed["viewComponent"], export=seed["viewExport"]),
        operations=(Operation(
            id="display-comparison-record", route=None, method=None,
            authority=Authority(kind="browser-local", exception_reason=
                "Read-only committed JSON display and local plot filtering; no solver or server operation."),
            undeclared_input=("document", "kernel", "enabledRegimes"),
            output=OutputSchema(fields=("datasets", "rows", "summary", "honesty"), status_key=None),
        ), Operation(
            id="display-spent-descriptive-record", route=None, method=None,
            authority=Authority(kind="browser-local", exception_reason=
                "Read-only committed JSON display of spent public sets and local curve toggling; no solver, "
                "server or research request."),
            undeclared_input=("record", "selectedSet", "curveXAxis"),
            output=OutputSchema(fields=("datasets", "curves", "deviation", "notes", "honesty"), status_key=None),
        )),
        evidence=Evidence(emits=(), ceiling="screening-only", forbidden_claims=FORBIDDEN_CLAIM_KEYS,
            note="No numerical oracle is declared for this view. Published measurements are displayed alongside "
                 "screening predictions; rendering them does not validate a solver or establish independent evidence."),
        tests=TestRefs(oracle=Oracle(status="pending"),
                      schema="python/test_module_contract_dataset_view.py",
                      docs="docs/modules/lpbf-dataset-comparison.md"),
        migration_state="contracted", lifecycle=Lifecycle(background_work="none"),
        legacy_notes=(
            "The operation describes a local view, not a request/response endpoint. Output fields name consumed "
            "record sections. The SDK scalar input schema cannot express the nested document or dynamic kernel "
            "and regime selections; these are undeclaredInput, with runtime validation in checkedDatasetComparison.",
            "Vite eagerly bundles the committed .view.json record. An absent record produces NoComparisonRecord; "
            "malformed committed bytes throw during checkedDatasetComparison rather than producing an empty success. "
            "The spent descriptive record is loaded lazily through a non-eager import.meta.glob in its own chunk, "
            "and its absence renders the panel's empty state.",
            "No fetch, solver, timer, worker or archive mutation runs in this module. Filters change plotted rows "
            "and axis scales locally; error statistics, provenance, hashes and uncertainty figures are read from JSON.",
            "Record dataset hashes and citations are displayed provenance, not a fresh remote source verification. "
            "Prediction exclusions and honesty statements remain visible; the view does not upgrade evidence status.",
        ),
        source_refs=(
            "src/data/lpbfDatasetComparisonRecord.ts",
            "src/data/lpbfDatasetComparison.ts::checkedDatasetComparison",
            "src/components/3d-distortion-lab/LpbfDatasetComparisonLab.tsx::DatasetComparisonView",
            "src/components/3d-distortion-lab/LpbfDatasetComparisonLab.tsx::NoComparisonRecord",
            "src/data/lpbfSpentDescriptiveRecord.ts",
            "src/data/lpbfSpentDescriptive.ts::checkedSpentDescriptive",
            "src/components/3d-distortion-lab/SpentSetDescriptivePanel.tsx::SpentSetDescriptivePanel",
            "tests/lpbf-spent-descriptive.test.tsx",
            "tests/lpbf-dataset-comparison.test.ts",
            "tests/lpbf-dataset-comparison-lab.test.tsx",
        ),
        seed_derived=("label", "description", "next", "maturity"),
    )
