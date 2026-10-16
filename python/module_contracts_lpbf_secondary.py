"""Source-bounded Module SDK contracts for the LPBF optimizer and solidification views."""

from typing import Mapping

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
    QuantityDeclaration,
    TestRefs,
    View,
)


CONTRACT_VERSION = "0.2.0"


def _contract(seed: Mapping[str, str], operation, notes, sources) -> ModuleContract:
    operations = tuple(operation) if isinstance(operation, (tuple, list)) else (operation,)
    return ModuleContract(
        id=seed["id"],
        version=CONTRACT_VERSION if seed["id"] == "solidification-microstructure" else "0.1.0",
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
                "Oracle pending. This contract inventories software requests and screening outputs only; "
                "it asserts no validated process recommendation or physical applicability."
            ),
        ),
        tests=TestRefs(
            oracle=Oracle(status="pending"),
            schema="python/test_module_contract_lpbf_secondary.py",
            docs=f"docs/modules/{seed['id']}.md",
        ),
        migration_state="contracted",
        operations=operations,
        lifecycle=Lifecycle(background_work="none", resources=("fetch",)),
        legacy_notes=tuple(notes),
        source_refs=tuple(sources),
        seed_derived=("label", "description", "next", "maturity"),
    )


def build_lpbf_optimizer_contract(seed: Mapping[str, str]) -> ModuleContract:
    """Describe the visible optimizer request without flattening its nested bounds map."""
    if seed["id"] != "lpbf-optimizer":
        raise ValueError("LPBF optimizer contract must preserve the lpbf-optimizer seed identity")
    operation = Operation(
        id="bayesian-optimize",
        method="POST",
        route="/api/python/lpbf-bayesian-optimize",
        authority=Authority(
            kind="python-ipc",
            script="python/lpbf_bayesian_optimizer.py",
            timeout_ms=120000,
            warm=False,
        ),
        # paramBounds is a map of four two-number intervals, not four flat request keys.
        # String alloyId is also outside InputField's scalar vocabulary.
        undeclared_input=("alloyId", "paramBounds", "nIterations", "nWarmup", "seed", "beamDiameter_um", "preheatTemp_C"),
        output=OutputSchema(
            fields=("success", "error", "errorKind", "alloyId", "bestParams", "bestVerdict", "noPositiveScore", "bestScore",
                    "verdictCounts", "nInconclusive", "iterations", "converged", "elapsedMs", "nIterations", "nWarmup",
                    "surrogateSteps", "beamDiameter_um", "preheatTemp_C", "objective", "gateSummary", "keyholeGateNote"),
            status_key=None,
        ),
    )
    process_window = Operation(
        id="process-window",
        method="POST",
        route="/api/python/lpbf-process-window",
        authority=Authority(
            kind="python-ipc",
            script="python/lpbf_process_window.py",
            timeout_ms=60000,
            warm=False,
        ),
        # Axis arrays (powers, speeds) and the string alloyId are outside InputField's scalar vocabulary.
        undeclared_input=("alloyId", "beamDiameter_um", "layer_um", "hatch_um", "preheatTemp_C", "powers", "speeds",
                          "overlayBeamTolerance_pct"),
        output=OutputSchema(
            fields=("success", "error", "errorKind", "engine", "alloyId", "request", "grid", "cells", "counts",
                    "gridAdvisories", "overlay", "provenance", "cache", "computeMs", "originalComputeMs"),
            status_key=None,
        ),
    )
    return _contract(
        seed,
        (operation, process_window),
        notes=(
            "The view submits only on Run Optimization. Its body is alloyId (a solver alloy key derived from the "
            "active material name by src/utils/lpbfOptimizerAlloy.ts), nested paramBounds for laserPower_W (W), "
            "scanSpeed_mms (mm/s), hatch_um (µm), layer_um (µm), nIterations, nWarmup, beamDiameter_um (default 80 µm), "
            "preheatTemp_C (default 80 degC) and seed=42. Initial UI intervals are [100,500], [200,2000], [60,200] "
            "and [20,80]. These inputs remain undeclared rather than inventing a nested schema.",
            "alloyId is required and must resolve through four_alloy_materials; a missing or unknown alloy is refused "
            "with errorKind 'validation' (HTTP 422 via server/pythonDispatchStatus.ts) and no fallback alloy is used. "
            "nIterations must be an integer in 1-30 and is rejected, not clamped or truncated; nWarmup must be an "
            "integer >= 1; seed must be an integer; bounds must be finite with 0 < min < max and unknown paramBounds "
            "keys are rejected; beamDiameter_um must be > 0 and preheatTemp_C must be >= 0 and below the alloy solidus. "
            "When nWarmup >= nIterations every candidate is a random sample and the result reports surrogateSteps=0.",
            "Thermal-solver exceptions return success:false with errorKind 'solver' and surrogate/acquisition exceptions "
            "errorKind 'optimizer' (HTTP 200, body error); they are never scored as 0. The objective is the verdict score "
            "(printable 1, risky 0.5, do-not-print 0, inconclusive/geometry-unresolved 0) times normalised v*h. When no "
            "candidate scores above 0 the result has bestParams=null and noPositiveScore=true. bestScore and the UI's "
            "best candidate are heuristic software outputs, not a qualified process recommendation, experimental result "
            "or validated optimum. "
            "The optimizer output is a suggestion, not a qualified window: a printable verdict from the screening "
            "model is not a qualified or validated parameter set.",
            "process-window (first tab of the lab, nothing runs until Compute): POST /api/python/lpbf-process-window "
            "evaluates the same calculate_meltpool_physics -> compose_verdict pair as the optimizer objective on a "
            "power x speed grid (default 11 x 11 over 0.5 x literature-box minimum to 1.5 x maximum; 2-15 values per "
            "axis, at most 225 cells, P <= 1500 W, v <= 10000 mm/s, strictly increasing, no clamping, no fallback alloy). "
            "Required body: alloyId, beamDiameter_um, layer_um, hatch_um (all > 0) and preheatTemp_C (>= 0 and below the "
            "solidus); optional powers, speeds and overlayBeamTolerance_pct (default 10). Refusals use errorKind "
            "'validation' (HTTP 422). A cell whose solver call raises is reported as verdict 'error' and never coloured "
            "as a verdict; width and depth are given only when extentStatus is 'computed'. Responses are cached in an "
            "imported module (16-entry LRU keyed by the normalised request, the solver revision and the implementation "
            "hash) and report cache.hit with scope python-worker-process (each pool worker has its own cache, so the first identical requests may miss); the response also carries an evidence object (not listed in the output fields: the SDK reserves that name) with kind 'screening-only' and experimentalValidation false; incomplete results (error cells, unavailable datasets) are not cached.",
            "process-window overlay: published single-track measurements (Hofmann 316L, Totis Ti-6Al-4V, KU Leuven "
            "IN718 with unit-unresolved dimensions, NIST AMB2022-03 Table 4 IN718) are filtered to the request beam "
            "diameter within the tolerance and to the mapped P/v range, with hidden counts reported; each point gets the "
            "model verdict at its own P/v with the request's beam, layer, hatch and preheat. A loader that fails makes "
            "only its dataset 'unavailable'; AlSi10Mg has no source. The response is screening only "
            "(evidence.kind 'screening-only', experimentalValidation false); measurements are geometry, not print "
            "outcomes, and no overlay point carries a verdict colour.",
            "The script imports numpy and scipy at module load and has no dependency-unavailable envelope or "
            "fallback. Dispatch/IPC errors surface through the route/service failure path. The request has a "
            "120000 ms Python-IPC timeout and is not warm. The browser holds request/result/loading/error state; "
            "no interval, background loop or persisted worker resource is started by this view.",
        ),
        sources=(
            "src/components/LpbfBayesianOptimizerLab.tsx::LpbfBayesianOptimizerLab",
            "src/services/pythonComputationService.ts::PythonComputationService.runLpbfBayesianOptimization",
            "routes/physics.ts:73-74#120000",
            "python/lpbf_bayesian_optimizer.py::run_bayesian_optimization",
            "python/lpbf_bayesian_optimizer.py:285-300#nIterations",
            "src/components/LpbfProcessWindowMap.tsx::LpbfProcessWindowMap",
            "src/services/pythonComputationService.ts::PythonComputationService.runLpbfProcessWindow",
            "routes/physics.ts:87-87#60000",
            "python/lpbf_process_window.py::run_process_window",
            "python/lpbf_process_window.py:37-37#MAX_CELLS = 225",
        ),
    )


def _front_declarations(prefix):
    from solidification_front import FRONT_QUANTITIES
    from quantity_envelope import QUANTITY_STATUSES, QUANTITY_SOURCE_EVIDENCE_KINDS, REASON_CODES
    return tuple(QuantityDeclaration(path=f"{prefix}.{name}", definition=definition, unit=unit,
                                     statuses=QUANTITY_STATUSES, source_evidence_kinds=QUANTITY_SOURCE_EVIDENCE_KINDS,
                                     reason_codes=REASON_CODES)
                 for name, (definition, unit) in FRONT_QUANTITIES.items())


def _gr_dependent_declarations():
    from quantity_envelope import QUANTITY_STATUSES, QUANTITY_SOURCE_EVIDENCE_KINDS, REASON_CODES
    return tuple(QuantityDeclaration(path=f"{prefix}.{kind}.quantities.{name}", definition=definition, unit="1",
                                     statuses=QUANTITY_STATUSES, source_evidence_kinds=QUANTITY_SOURCE_EVIDENCE_KINDS,
                                     reason_codes=REASON_CODES,
                                     fraction_basis="microconstituent" if kind == "laves" else None)
                 for prefix in ("point", "cells")
                 for kind, name, definition in (("cet", "class", "cet-class"),
                                                ("laves", "fraction", "laves-trapped-scheil-fraction")))


def build_solidification_microstructure_contract(seed: Mapping[str, str]) -> ModuleContract:
    """Describe the view's worker request and its explicit unavailable/screening outcomes."""
    if seed["id"] != "solidification-microstructure":
        raise ValueError("Solidification contract must preserve the solidification-microstructure seed identity")
    operation = Operation(
        id="solidification-microstructure",
        method="POST",
        route="/api/python/lpbf-solidification-microstructure",
        authority=Authority(
            kind="lpbf-worker",
            worker_method="solidification-microstructure",
            timeout_ms=20000,
        ),
        quantities=_front_declarations("quantities"),
        # The view sends one nested params object; no SDK map type exists to describe it truthfully.
        undeclared_input=("params",),
        output=OutputSchema(
            fields=("schema", "status", "source", "modelId", "alloyId", "quantityEnvelopeSchema",
                    "moduleEvidenceCeiling", "moduleMaturity", "quantities", "inputProvenance", "regime",
                    "normalizedEnthalpy", "heatSourceModel", "materialName", "inputs", "absorptivity",
                    "materialEvidence", "scope"),
            status_key=None,
            transport_values=(("status", ("computed", "partial", "unavailable", "failed", "not-requested")),),
        ),
    )
    # SOL-C opt-in estimate channel (RC1): a quantity envelope v2 container with typed estimate fields. Its quantity
    # set and definitions depend on the alloy (single PDAS correlation or the Ni model alternatives, KM, Al phase
    # references), so no v1 QuantityDeclaration describes it; python/test_lpbf_solidification_estimates.py and the
    # TypeScript parser validate every payload with the v2 envelope rules instead.
    estimates_operation = Operation(
        id="solidification-estimates",
        method="POST",
        route="/api/python/lpbf-solidification-estimates",
        authority=Authority(
            kind="lpbf-worker",
            worker_method="solidification-estimates",
            timeout_ms=20000,
        ),
        undeclared_input=("params", "options"),
        output=OutputSchema(
            fields=("schema", "channelId", "modelId", "status", "alloyId", "materialName", "heatSourceModel",
                    "request", "options", "surrogate", "surrogateIdentity", "default", "thermalParent", "front", "inputSensitivityRun",
                    "phaseContext", "refusal", "quantityEnvelopeSchema", "moduleEvidenceCeiling", "moduleMaturity",
                    "quantities", "inputProvenance"),
            status_key=None,
            transport_values=(("status", ("computed", "partial", "unavailable")),),
        ),
    )
    gr_operation = Operation(
        id="gr-solidification",
        method="POST",
        route="/api/python/lpbf-gr-solidification",
        authority=Authority(
            kind="python-ipc",
            script="python/lpbf_gr_solidification.py",
            timeout_ms=60000,
            warm=False,
        ),
        quantities=(_front_declarations("point.front.quantities") + _front_declarations("cells.front.quantities")
                    + _gr_dependent_declarations()),
        # Axis arrays (powers, speeds) and the string mode/alloyId are outside InputField's scalar vocabulary.
        undeclared_input=("mode", "alloyId", "beamDiameter_um", "layer_um", "hatch_um", "preheatTemp_C", "power_W",
                          "speed_mm_s", "powers", "speeds"),
        output=OutputSchema(
            fields=("success", "error", "errorKind", "engine", "schema", "mode", "alloyId", "materialName", "request",
                    "grid", "point", "cells", "counts", "cet", "laves", "materialEvidence", "limits", "provenance",
                    "computeMs"),
            status_key=None,
        ),
    )
    return _contract(
        seed,
        (operation, estimates_operation, gr_operation),
        notes=(
            "The worker returns lpbf-solidification-microstructure-2. Quantities are copied from the Python thermal "
            "front container with SI values, coded reasons and input provenance; no second estimate or flat-key fallback.",
            "At SOL-A1 every default front quantity is unavailable for Ti64, AlSi10Mg, 316L, IN718 and IN625 because "
            "no source-admitted liquidus is installed. The cfdResult branch is refused with quarantined-legacy-path.",
            "The independent G/R request returns lpbf-gr-solidification-2 with computed, partial, unavailable, failed "
            "or not-requested transport statuses. Cells carry a front envelope and CET/Laves envelopes. Default LPBF "
            "CET is unavailable with outside-source-model-domain; sourceChecks distinguish equation reading, algebra "
            "reproduction and printed-limit comparison. No Hunt morphology bands or analytic liquidus bypass are served.",
            "The opt-in estimate channel returns lpbf-solidification-estimates-1, a quantity envelope v2 container: per "
            "quantity estimateTier (Estimated, Physics estimate shown as Uncalibrated estimate, or no-value), display "
            "precision, closed value warnings separate from blocking reasons, and an input sensitivity range that is "
            "never an error bar. Default thermal results and Build Job read nothing from it.",
            "Evidence remains screening-only and Research. The response-level G/R evidence object is SDK-reserved; "
            "per-quantity source labels never imply experimental validation.",
        ),
        sources=(
            "src/components/SolidificationMicrostructureLab.tsx::SolidificationMicrostructureLab",
            "src/components/SolidificationMicrostructureLab.tsx::solidificationRequest",
            "src/services/pythonComputationService.ts::PythonComputationService.computeSolidificationMicrostructure",
            "routes/lpbfSimulation.ts:22-37#solidification-microstructure",
            "routes/lpbfSimulation.ts:34#solidification-estimates",
            "server/lpbfWorkerBridge.ts:59#requestTimeoutMs ?? 20000",
            "python/lpbf_worker_rpc.py::_rpc_solidification_microstructure",
            "python/lpbf_solidification_microstructure.py::compute_screening_field_microstructure",
            "python/lpbf_solidification_microstructure.py::project_build_job_microstructure",
            "python/lpbf_solidification_microstructure.py::compute_solidification_microstructure",
            "python/lpbf_worker_rpc.py::_rpc_solidification_estimates",
            "python/lpbf_solidification_estimates.py::compute_solidification_estimates",
            "python/lpbf_gr_solidification.py::run_gr_solidification",
            "src/components/GrSolidificationMapCard.tsx::GrSolidificationMapCard",
            "routes/physics.ts:93-93#60000",
        ),
    )
