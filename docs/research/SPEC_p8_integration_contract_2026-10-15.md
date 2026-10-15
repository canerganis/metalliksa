# P8 integration contract: opt-in research route, isolation, transport, panel and labels

Date: 2026-10-15. Owner: system architect (Opus). Scope: the engineering items 2, 7, 11, 12, 13, 14, 17, 18 and 20 and the UI/caption part of item 6 of the lead-owned gate verdict `../Metalliksa-1/.orchestra/reports/p8_gate_verdict_2026-10-15.md`.
Base: branch `research/p8-research-arm`. Its code is identical to main `835466fa` (the branch adds documents only), so every `file:line` below is a line of `835466fa`.
Companion: `docs/research/SPEC_p8_research_arm_2026-10-14.md` (base and Amendments 1 to 3; physics owner Astra; Amendment 3 is `78607f3e`). Amendment 2 landed on this branch as `1c76a2fd` while this contract was written; the contract is aligned with it. Amendment 2 (header and B9) assigns to this contract the transport, gating, caching, provenance vocabulary, field names, reason-code serialization and availability enums, and lists eight physics requirements the final schema must carry (0.2). This file does not edit the physics spec. Where this contract still needs a physics decision it says so in section 12; the re-gate reconciles both files.

Status: re-gated 2026-10-15, APPROVE_WITH_CHANGES (`../Metalliksa-1/.orchestra/reports/p8_regate_verdict_2026-10-15.md`). Revision 1 (section 13) applies the architect's share of R1 to R15 and records the maintainer's label decisions. Revision 2 fixes the residuals of the lead check at `e6934ffd` (Phase A GO) in place, marked "Rev. 2". Nothing is implemented; no code, pin, golden, allowlist or test changes in these commits.

W-1: every English user-facing string in this contract (panel text, labels, help, sentences, captions, n/a texts, option messages, difference statements) is a draft awaiting maintainer approval W-1, except text quoted verbatim from the P8 spec. Tests pin the approved wording, not these drafts.

## 0. Decision

The research arm becomes a separate computation behind a new route, `POST /api/python/lpbf-research-models`, run by a new dispatch script `python/lpbf_research_models.py` in its own single-process IPC lane. It is computed only when the Research model panel sends an explicit request.

1. It never runs inside `calculate_meltpool_physics` and never rides in a served payload. `result.researchModels` and `job.thermal.researchModels` are dropped; the block is the `researchModels` member of the research route response.
2. No served module imports research code (an AST guard enforces it).
3. The research process re-derives the unrounded thermal tuple (K, cp, rho_k, alpha, A0, Tl) from the same public resolver the served solver calls (`resolve_conduction_kernel`, `python/lpbf_thermal_solver.py:288-364`). A test pins float.hex equality with the served internals.
4. Consequence: no file of the frozen manifest, no fingerprint pin, golden, Build Job revision, job cache key or parity allowlist changes. Served outputs are byte-identical whether or not research is requested. There is no served bump.

### 0.1 Parts of the P8 spec this contract supersedes (on re-gate acceptance)

| P8 spec location | Replaced by |
|---|---|
| Section 2, first paragraph: `result.researchModels` on the thermal result and `job.thermal.researchModels` | Section 3.5 here: the block is a member of the research route response. The block's internal schema stays Astra's, with the renames of section 7 and the provenance changes of section 6. |
| Section 8 items "Append after served computation", "Typed transport and panel" (attach and panel parts, Rev. 1 R9), "Additive-output frozen bump", "Parity before goldens", "Parity-tool policy", "Frozen calibration assertions", and the worker-restart and revision parts of "Checks/rollout" | Sections 3, 4, 10 and 11 |
| A1 first sentence: `researchOptions` on both the standalone thermal and the Build Job requests | `researchOptions` travels only in the research route request (3.4) |
| A4 "Responsive UI" paragraph, the cache location "in the Python worker", and "Build Job cache integration correction" | Sections 3.6 and 4 |
| A6 "Build Job cache-hit overlay tests" and the section 9.1 cache sentence ("change only researchOptions on a warm served job") | Section 10.3 tests |
| Implementer "Fable" | Owners in section 11 |
| Section 2: the `ResearchField` literal `evidenceKind: "Literature estimate"` (Rev. 1, R4, R13) | `sourceEvidenceKind` per value and the decided output label rule (6.1, 6.2, 13.12) |
| Section 2: the seven container `uiSentence` texts for keyholeCavity, meltDepthLink, marangoni and surfaceBalance (Rev. 1, R5) | W-1 drafts in 13.4 |
| Section 2.1, 2.2, A2, A3 field lists, the A3 label "Peak surface temperature (flat HKL proxy)" and the A3 help text (Rev. 1, R4, R5) | The closed runtime field list and fixture map in 13.3; labels and help in 13.4 |
| A1 `ResearchNumericBand` (Rev. 1, R4) | extended by 5.3, 5.4 (descriptor manifest, ties, per-extreme provenance), 3.5 (`pending`) and 13.5 |
| A5 sentences "Flat HKL", "Low Pe", "Below onset" and the ungated "Inside declared range" (Rev. 1, R5, R7) | Amendment 2 B2 and B5 texts, Amendment 3 C3 meanings, and the 13.6 eligibility and drafts |
| A6 "schema p8-research-v2" (Rev. 1, R4) | `p8-research-v3` (section 7) |

The physics content (sections 3 to 7, A2, A3, the physics of A4 and A5, and Amendment 2 B1 to B8) is untouched. Where the spec's field lists and this contract's names differ (section 7), this contract's names apply, as Amendment 2 B9 assigns.

### 0.2 Amendment 2 B9 requirements and where this contract carries them

| B9 item | Requirement | Carried by |
|---|---|---|
| (1) | Distinct source, assumption, user and derived provenance, with phase and reference temperature, for each arm, input and extremum | 5.3, 6.1, 6.3, 4.7, 13.5 |
| (2) | Module-local arm and event manifests, field-specific failures, deterministic ties, per-arm root arrays, counts and branch support, a non-statistical caption | 5.1 to 5.5, 3.6 (whole arm records cached), 4.7 |
| (3) | Unconditional onset-mismatch diagnostics; separate photon-split and wall-conduction ledgers | 7.2 (`onsetMismatch`, `wallConductionPower_W`, `cavityLedgerRatio`), 13.15 (`fieldShapeStep`), 9.2 |
| (4) | Falsified surface-closure status on every dependent surface diagnostic, with shipped references | 6.1, 9.2, D2 in section 8 |
| (5) | O8 band and note, feedstock, route, enthalpy and extrapolation scope, Mg-aware depth sensitivities | 5.1 (own `o8` manifest; O8 vapour arm in the cavity manifest), 9.2 |
| (6) | Independent Gaussian-floor method identity, resolved no-melting zero, below-onset dispatch | 3.8, 7.2 (`floorFieldModelId`, `floorExtractorId`, `conductionStatus`) |
| (7) | Fe-mode replacement semantics with the direct input preserved but inactive | 4.2, 7.2 (`slopeBaseline`), 9.3 rule 7 |
| (8) | An admissible coherent 0.82 net-evaporation sensitivity | 7.2 (`evaporationConvention`, `netEvaporationFactor`), 9.3 rule 8 |

## 1. Opt-in gating (gate item 2)

### 1.1 Rule

Research is computed only when the research route receives a request. Only the Research model panel sends one, and only after the user presses **Run research models**. No served route, worker job, internal caller, page load or input edit sends one.

### 1.2 Mechanism (structural, not a flag)

1. No file in `lpbf_simulation.IMPLEMENTATION_SOURCE_FILES` (`python/lpbf_simulation.py:44-81`) is edited. `calculate_meltpool_physics` keeps its signature (`python/lpbf_thermal_solver.py:834-851`) and body through the final return (`:1617-1624`), so every caller below runs the same bytes as at `835466fa`.
2. Research code lives only in new modules with the prefix `lpbf_research_` (3.2). Guard R-ISO-1 (10.3) fails when any other `python/**/*.py` imports such a module, and when any research module references `calculate_meltpool_physics`. The second rule forbids recursion and hidden per-call cost.
3. The served route block `physicsRouter.post("/api/python/lpbf-thermal-solver"` (`routes/physics.ts:62-64`) is unchanged. The new route is appended after `routes/physics.ts:106`.
4. The research IPC lane is created lazily on the first research request and is never prestarted (3.3).

### 1.3 Internal callers

| # | Caller | Attach point | Reaches research? | Proof |
|---|---|---|---|---|
| 1 | Build Job main thermal call | `python/lpbf_build_job_solver.py:1016-1028` | no | file unchanged (R-ISO-2), import guard (R-ISO-1) |
| 2 | Build Job patch evaluator | `_patch_thermal` at `lpbf_build_job_solver.py:1048-1066`, passed to `compose_verdict` at `:1067-1071` | no | same |
| 3 | Screening UQ runner | `_thermal_runner` at `lpbf_build_job_solver.py:1084-1098`, `run_screening_uq` at `:1104` | no | same |
| 4 | AM-Bench runner | `_amb_thermal` at `lpbf_build_job_solver.py:1123-1136` | no | same |
| 5 | Process window | `_evaluate` at `python/lpbf_process_window.py:175-188` (default 11 x 11, `MAX_CELLS` 225 at `:36-37`; route timeout 60 s at `routes/physics.ts:86-88`) | no | same |
| 6 | Bayesian optimizer | `_obj` at `python/lpbf_bayesian_optimizer.py:248-258` | no | same |
| 7 | G/R solidification route | `_thermal` at `python/lpbf_gr_solidification.py:322-326` | no | same |
| 8 | Build Job microstructure projection | `python/lpbf_solidification_microstructure.py:324-350` | no | same |
| 9 | Calibrated melt-pool route | `_default_solver` at `python/lpbf_calibration_layer.py:125-127` | no | same |
| 10 | Machine calibration | `python/lpbf_machine_calibration.py:68-72` and `:559-560` | no | same |
| 11 | Standalone route entry | `__main__` at `python/lpbf_thermal_solver.py:1626-1672` (call at `:1661`) | no | frozen file unchanged (P-1, P-2) |
| 12 | Melt Pool lab live re-solve | `solvePhysics` at `src/components/3d-distortion-lab/MeltPool3DCrossSectionLab.tsx:158-211`, 200 ms debounce at `:214-219`, then `pythonComputationService.ts:696-720` and `/api/python/lpbf-thermal-solver` | no | the panel has its own state and request; the only host edit is a ref write of the served request signature (4.6). R-UI-9: a research option edit sends zero thermal-solver calls; a process edit sends zero research calls |
| 13 | Build Job store debounce | `src/store/useLpbfBuildJobStore.ts:311-337` | no | research state lives in a separate store (4.5); R-UI-10 |
| 14 | Offline tools (not served) | `python/generate_ml_dataset.py:24`, `python/run_in718_solver_branch_sensitivity_pilot.py:185`, `python/tools/lpbf_calibration_fit.py:181`, `lpbf_calibration_heldout.py:125`, `lpbf_dataset_comparison.py:261`, `lpbf_error_bands.py:111`, `lpbf_keyhole_benchmark.py:171` | no | files unchanged |

The reviewer's cost finding (an envelope of about 0.9 to 3.5 s against 0.02 to 0.5 s for the served call; the default process window estimated at 220 to 340 s against its 60 s timeout) cannot occur: no row above evaluates a research arm.

### 1.4 Bit-identity statement

1. When no research request is made, no research module is imported in any process. Served outputs are byte-identical: the frozen files are unchanged and the existing T-HTTP-1 digests hold (`python/test_lpbf_calibration_frozen.py:55-59`, `:125-136`). The served request path runs the same code: the served-infrastructure edits are constant definitions and a prestart filter in `python/persistent_ipc_service.py`, evaluated at daemon start, one guard on the affinity branch that served thermal requests never enter (3.3), and one set entry in `server/processOrchestrator.ts:186-196`. Served timing is a measured check (P-7), not a byte claim.
2. When research is requested, served bytes are still identical: research runs in another process and returns another response. A served request never waits in a research queue and never shares a research process, lock or cache. It can share CPU cores; the research lane is one process at below-normal OS priority (3.7 item 6).

### 1.5 No channel to served code (Rev. 1, R3)

The research route offers no channel to served code. No served route, solver call, worker job or internal caller can send options to it or receive values from it, and the closed request schema `p8-research-request-v1` admits no member for any other lane. A lane that needs an opt-in served-side diagnostic (for example SOL-C, which needs the served heat source that this request deliberately excludes) defines its own route, request and cache; it cannot ride on P8's transport, cache or schema. P8 is not a served bump, holds no pin slot, leaves the manifest at 36 files and does not edit `python/test_phase6a_leaf_modules.py`. The matching amendment of the solidification integration plan belongs to its owner.

## 2. Files touched

| File | Change | Frozen? | Guarded path (`scripts/check_ceiling_review.py` `PROTECTED_PATHS`)? |
|---|---|---|---|
| `python/lpbf_research_models.py` | new dispatch script | no | no |
| `python/lpbf_research_context.py`, `lpbf_research_cache.py`, `lpbf_research_codes.py`, `lpbf_research_manifest.py`, `lpbf_research_arm.py` | new modules | no | no |
| `python/lpbf_research_identity.expected` | new research pin | no | no |
| `python/persistent_ipc_service.py` | allowlist entry, isolated lane, prestart filter, metadata guard; for isolated lanes only, the timeout envelope and `recycleWorker` (Rev. 2) | no | no |
| `server/processOrchestrator.ts` | `DISPATCHABLE_SCRIPTS` entry | no | no |
| `routes/physics.ts` | route appended after line 106 | no | no |
| `python/module_registry.py`, `src/generated/moduleRegistry.json`, `src/generated/moduleRegistry.ts` | one operation, regenerated output | no | no |
| `src/services/pythonComputationService.ts` | new method `solveLpbfResearchModels` | no | no |
| `src/types/lpbfResearchModels.ts` | new closed types and response guard | no | no |
| `src/store/useLpbfResearchModelStore.ts` | new session store | no | no |
| `src/components/3d-distortion-lab/ResearchModelPanel.tsx` | new panel | no | no |
| `MeltPool3DCrossSectionLab.tsx`, `IndustrialLPBFDecisionLab.tsx` | panel mount; served-signature ref in the Melt Pool lab | no | no |
| new tests (10.3) | new files | no | no |

No guarded path is touched, so no `Ceiling-Review` trailer is needed. The existing import guard `FORBIDDEN_MANIFEST_IMPORTS` (`python/test_lpbf_implementation_fingerprint.py:23`, a guarded file) is not edited; the research guard lives in a new test file.

## 3. Transport and attach point (gate item 11)

### 3.1 Route

Appended to `routes/physics.ts` after line 106:

```ts
// P8 research models: research only, explicit opt-in. A NEW route; /api/python/lpbf-thermal-solver is untouched.
physicsRouter.post("/api/python/lpbf-research-models", (req: Request, res: Response) => {
  if (Buffer.byteLength(JSON.stringify(req.body ?? null), "utf8") > 65536) {
    return res.status(413).json({ success: false, errorKind: "research-request",
      reasonCode: "RESEARCH_REQUEST_INVALID", problems: [{ pointer: "", rule: "too-large", limit: 65536 }] });
  }
  return handleResearchDispatch(req.body, res, 30000);   // Rev. 1, R14: see below
});
```

`handleResearchDispatch` (Rev. 1, R14; Rev. 2) is a research-only wrapper beside `handlePythonDispatch` (`routes/physics.ts:11-34`), which it leaves unchanged. It calls `physicsDeps.runPythonScript` itself and answers every timeout with HTTP 504 and `{success: false, errorKind: "research", reasonCode: "RESEARCH_TIMEOUT", timeoutKind}`, so the timeout reaches the client as a code, not as stderr text:

| timeoutKind | Source | How the wrapper recognises it | Effect on the research worker and cache |
|---|---|---|---|
| `queue` | lane queue timeout (`persistent_ipc_service.py:833-836`): never started | exit code 124 with the isolated-lane stdout envelope of 3.3 item 5 (`"timeoutKind": "queue"`) | nothing ran; the worker is not replaced; the cache is kept |
| `run` | lane run timeout (`persistent_ipc_service.py:837-840`) | exit code 124 with the envelope `"timeoutKind": "run"` | the worker was killed and replaced; its cache is empty |
| `reply` | no IPC reply within `timeoutMs` plus grace (UNIX socket `server/processOrchestrator.ts:431-432`, HTTP `:530`), rethrown as "Python IPC request may already have run, so it was not retried" (`:627`) | a thrown error whose message contains "got no reply within" | unknown: the request may still finish in the worker and cache its arms |
| `adhoc` | ad-hoc spawn killed (`server/processOrchestrator.ts:562-565`) | a thrown error whose message starts with "Ad-hoc Python execution timed out after" | no persistent worker exists; nothing was cached |

The two thrown-message markers are matched as literals; the route test asserts that both literals still occur in `server/processOrchestrator.ts`, so a rename there fails the test instead of turning a timeout into a generic 500. The wrapper adds `channel` from `PythonExecResult` (`processOrchestrator.ts:211-218`) to every body, so the client knows when the ad-hoc path served the request. Every other outcome is mapped exactly as `handlePythonDispatch` maps it.

Registry: `python/module_registry.py` adds, in the `"3d-distortion-lab"` operation list (`:162-181`), `_op("lpbf-research-models", "POST", "/api/python/lpbf-research-models", _py("lpbf_research_models", _RESEARCH_TIMEOUT_MS, warm=False))` with `_RESEARCH_TIMEOUT_MS = 30000` beside `_PHYSICS_TIMEOUT_MS` (`:123`), and the generated files are regenerated. The route is bound, so `routes/AUTHORITY_ALLOWLIST.json` does not grow (`tests/route-authority.test.ts`). `lpbf_research_models` joins `DISPATCHABLE_SCRIPTS` (`server/processOrchestrator.ts:186-196`) and `ALLOWED_SCRIPT_NAMES` (`python/persistent_ipc_service.py:107-117`); `tests/persistent-ipc-auth.test.ts` and `python/test_persistent_ipc_security.py` keep both equal to the route literals. It is not a warm module (`WARM_MODULE_NAMES`, `:95-101`), so `python/module_warm_parity.ceiling.json` is unaffected.

### 3.2 Dispatch script and modules

| Module | Responsibility |
|---|---|
| `lpbf_research_models.py` | Reads stdin, runs request checks, runs the stage protocol, serializes strictly, sets the exit code. Holds no module-level state: the IPC worker executes it in a fresh namespace per request (`python/persistent_ipc_service.py:459-515`, namespace at `:491-499`). Heavy work stays under `if __name__ == "__main__"`. |
| `lpbf_research_context.py` | Builds the immutable `ResearchContext` from the request (3.4, 3.8). |
| `lpbf_research_cache.py` | Process-local LRU, `cacheInstanceId`, identity hashes, `RESEARCH_SOURCE_FILES`, priority lowering. |
| `lpbf_research_codes.py` | Reason-code registry, English texts, option-rule texts, leaf labels, served-difference templates (sections 7 to 9). |
| `lpbf_research_manifest.py` | Per-module arm manifests, deduplication, arm descriptors (section 5). |
| `lpbf_research_arm.py` | Physics evaluator under Astra's contract. Entry points are per module and per arm: `evaluate_arm(module_id, context, arm) -> ArmRecord` and `aggregate(module_id, manifest, arm_records) -> container`. |

`RESEARCH_SOURCE_FILES` is the tuple of these six `.py` files. O8 and every other constant are embedded literals in research modules (covered by the research hash); the runtime reads no JSON (gate minor 8, Amendment 2 B9 last paragraph). A test compares the literals with the committed `docs/research/scripts/alsi10mg_vapour_o8.json`. The runtime never imports anything under `docs/research/scripts/`, including the local kernel snapshot `p8_cavity_kernel.py`; the evaluator is a port, checked against the committed fixture `p8_amendment1_synthetic.json` (content `p8-research-synthetic-v2`).

### 3.3 IPC lane

Edits to `python/persistent_ipc_service.py`:

1. New constant `ISOLATED_SCRIPT_NAMES = frozenset({"lpbf_research_models"})`, independent of `METALLIX_IPC_AFFINITY`.
2. `AFFINITY_SCRIPT_NAMES` (`:126-127`) becomes the existing expression `| ISOLATED_SCRIPT_NAMES`. `_affinity_name` (`:764-766`) then routes research to its own `_AffinityLane` (`:552-681`): one worker process, one job at a time, a queued request superseded by a newer request with the same `supersedeKey` (`:626-638`), one deadline for queue plus run, and a run timeout that kills and replaces only that worker (`:663-669`, `recycle` at `:594`).
3. `start_affinity_pools` (`:784-790`) iterates `AFFINITY_SCRIPT_NAMES.difference(ISOLATED_SCRIPT_NAMES)`, so the research lane is never prestarted.
4. The metadata exemption (`:876-877`) applies only when `affinity not in ISOLATED_SCRIPT_NAMES`, so a research payload carrying an `action` key can never reach the shared pool or its in-process fallback (`:934-990`). Served thermal requests have `affinity is None` and never evaluate this guard.
5. (Rev. 2) For `ISOLATED_SCRIPT_NAMES` only, the queue-timeout and run-timeout replies of `_execute_affinity` (`:833-840`) keep exit code 124 and add a stdout envelope `{"success": false, "errorKind": "research", "reasonCode": "RESEARCH_TIMEOUT", "timeoutKind": "queue" or "run"}`; calphad replies are unchanged. The same function honours `recycleWorker` (13.7 item 2).

The served thermal solver keeps the shared pool (`execute_script`, `:844-915`). Research never takes the in-process fallback, because the affinity branch returns first (`:878-880`).

Ad-hoc spawn fallback (`server/processOrchestrator.ts:647-650`): every research request is then a fresh process with a cold cache. Results are unchanged; the client detects it (3.5 rule 6).

### 3.4 Request schema (`p8-research-request-v1`, closed at every level)

```jsonc
{
  "schemaVersion": "p8-research-request-v1",
  "supersedeKey": "p8-research:melt-pool",    // or "p8-research:build-job"; 1 to 128 characters
  "clientRequestId": "melt-pool:17",           // opaque, 1 to 128 characters, echoed back
  "stage": "nominal",                          // "describe" | "nominal" | "band" (describe: Rev. 1, R10, 13.9)
  "timeBudgetMs": 1500,                        // band stage only: integer 250 to 8000, or null (finish every arm)
  "process": {
    "material": "Ti-6Al-4V",                   // a served material name
    "laserPower_W": 200, "scanSpeed_mm_s": 800, "beamDiameter_um": 80, "preheatTemp_C": 20,
    "laserWavelength": "IR_1064nm",            // served enum
    "absorptionModel": "flat-plate"            // "flat-plate" | "powder-raytrace"
  },
  "propertyContext": { "kind": "nominal" },
  // or { "kind": "build-job-snapshot", "alloyId": "ti6al4v", "materialPropertySha256": "<64 lowercase hex>" }
  "researchOptions": { "marangoni": {}, "surfaceBalance": {}, "ranges": {} }   // A1 member, optional
}
```

Request-level checks (refusal without a block, 9.3):

1. The body is a JSON object; `schemaVersion` matches exactly; every key is known.
2. Numbers are JSON numbers and finite. Booleans are refused where a number is expected (Python `bool` is an `int` subclass).
3. `laserPower_W`, `scanSpeed_mm_s`, `beamDiameter_um` are greater than zero. P = 0 stays an evaluator-only limit (P8 spec section 3).
4. `material` resolves through the served lookup `thermal_props(name) or SECONDARY_THERMOPHYSICAL_DB.get(name)` (`python/lpbf_thermal_solver.py:869`).
5. `laserWavelength` and `absorptionModel` are members of the served enums. A non-IR wavelength or the powder model is accepted here and reported per module as `WAVELENGTH_UNSUPPORTED` or `POWDER_CONTEXT_UNSUPPORTED` (P8 spec section 3).
6. `stage`, `timeBudgetMs`, `supersedeKey` and `clientRequestId` obey their rules.
7. `propertyContext`: for `build-job-snapshot`, `alloyId` must resolve (`resolve_alloy_id`, `python/four_alloy_materials.py:63`) to the alloy whose thermal name (`ALLOY_MATERIALS`, `four_alloy_materials.py:33`) equals `process.material`, and the recomputed `build_material_property_snapshot` (`python/lpbf_build_job_material_snapshot.py:61`) must hash to `materialPropertySha256`, else `PROPERTY_SNAPSHOT_MISMATCH`.
8. `researchOptions` structure: object shapes, known keys and value types only. Numeric limits, presets, modes and ranges are checked per module (9.3), so a bad surface option never blanks the cavity, link or Marangoni models.

SI conversions happen once in `lpbf_research_context.py`, exactly as P8 spec section 2.1: speed / 1000, diameter / 1e6, preheat + 273.15.

Not in the request: hatch, layer, incline, seed, the served sulfur slider, the served heat source and the thermal slice backend. Changing any of them never makes a research result stale.

### 3.5 Response schema (`p8-research-response-v1`) and stage protocol

```jsonc
{
  "success": true,
  "schemaVersion": "p8-research-response-v1",
  "clientRequestId": "melt-pool:17",
  "requestKey": "<sha256 hex, 3.6>",
  "stage": "nominal",                          // "describe" | "nominal" | "band"; a describe response has the 13.9 shape
  "progress": { "armsTotal": 41, "armsDone": 12, "complete": false },
  "researchModels": { },                       // the closed block; null only for an incomplete band stage
  "labels": { "<field path>": "<English label>" },
  "identity": {
    "researchImplementationSha256": "<hex>", "servedImplementationFingerprint": "<hex>",
    "researchSchemaVersion": "p8-research-v3", // block schema with the names and wrappers of sections 5 to 9
    "propertySetSha256": "<hex>", "propertyContextKind": "nominal"
  },
  "cache": { "cacheInstanceId": "<uuid4 hex>", "armsHit": 30, "armsComputed": 11 },
  "computeMs": 812.4                           // volatile, excluded from every equality check
}
```

Protocol:

1. `stage: "nominal"` evaluates the nominal arm of every module and returns all seven containers. Every band is in pending form: `completeness: "pending"`, min and max null with `BAND_PENDING`, `successfulArms` and `totalArms` null, `failedArms` empty. `pending` is a new availability enum value, owned by this contract (B9).
2. `stage: "band"` with budget b builds the manifests (section 5) and looks up every arm key. It computes uncached arms in a fixed order (modules keyholeCavity, meltDepthLink, marangoni, surfaceBalance, alSi10MgVapourMgAware; manifest order inside each; Rev. 1, R14) and stops starting new arms once the elapsed time reaches b. It always computes at least one uncached arm, so every request makes progress.
3. When every arm is available, it aggregates (cached under the aggregate key) and returns the full block with `complete`, `partial` or `unavailable` bands, and `progress.complete = true`.
4. Otherwise it returns `researchModels: null` with the progress counts. A partial envelope is never sent or shown.
5. `timeBudgetMs: null` computes every remaining arm in one request, bounded by the route timeout.
6. Client fallback: when two consecutive band responses carry different `cacheInstanceId`, or `armsDone` does not increase, the client sends one band request with `timeBudgetMs: null`.
7. The nominal arm records are the same cache entries the band stage uses. A nominal leaf value is byte-identical in the nominal and the complete response (R-TR-6).
8. Determinism: for one `requestKey`, `researchModels` and `labels` are byte-identical between cold and warm runs.
9. A meltDepthLink arm reads the keyholeCavity record of the same scenario; the cavity arm is always evaluated first and the link arm key includes the cavity arm key.
10. Within one request every arm record is held in a request-local map from lookup or computation until aggregation, so LRU eviction during a request cannot lose a record (Rev. 1, R14).
11. `stage: "describe"` evaluates no arm; it returns the control definitions, defaults, provenance, labels and option problems for the given material and options (13.9).

Outcomes and HTTP status:

| Outcome | stdout | Exit | HTTP |
|---|---|---|---|
| Request refused | `{"success": false, "errorKind": <the literal mapped to 422 at server/pythonDispatchStatus.ts:15>, "reasonCode": "RESEARCH_REQUEST_INVALID" or "PROPERTY_SNAPSHOT_MISMATCH" or "RESEARCH_CODE_STALE", "problems": [OptionProblem]}` | 2 | 422 |
| Request-scope research failure (a bug outside any module, or an oversize response) | `{"success": false, "errorKind": "research", "reasonCode": "RESEARCH_EVALUATION_FAILED" or "RESEARCH_SERIALIZATION_FAILED" or "RESEARCH_RESPONSE_TOO_LARGE"}`; traceback on stderr only | 0 | 200 (`pythonDispatchStatus`, `server/pythonDispatchStatus.ts:11-16`) |
| Crash before any stdout | empty; stderr | nonzero | 500 (`routes/physics.ts:18-24`) |
| Timeout (`queue`, `run`, `reply` or `adhoc`) | lane: the 3.3 item 5 envelope with stderr "Execution timed out ..." (`persistent_ipc_service.py:833-840`); reply and ad-hoc: a thrown error | 124 or none | 504 with `RESEARCH_TIMEOUT` and `timeoutKind` from `handleResearchDispatch` (3.1) |
| Superseded while queued | `{"success": false, "status": "superseded", ...}` (`persistent_ipc_service.py:826-832`) | 0 | 200; the client ignores it |

### 3.6 Cache

Location: a module-level `OrderedDict` in `python/lpbf_research_cache.py`, inside the single research lane process. It survives between requests because imported modules stay in `sys.modules`; it is empty after a daemon restart, after a lane recycle (timeout or worker death) and in every ad-hoc spawn. It is never persisted and never shared with served code. It is never held in the dispatch script, whose namespace is fresh per request.

Bounds (Rev. 1, R14): the LRU holds two complete requests at the arm cap, so two hosts can alternate without evicting each other: at least 2 x (80 arms x 5 banded modules + 5 aggregates + 1) = 812 entries, rounded to 1024, and at most 128 MiB measured as the UTF-8 length of each entry's canonical JSON at insert; the oldest entries are evicted until both bounds hold. Phase C records actual record sizes and confirms or raises the byte bound (D-12).

Entries: one arm record per (module, arm), and one aggregate per module. Successful arms and arms failed with a deterministic code (classes C3 to C9 of 9.1) are cached. Every cached arm record is finite-only, because non-finite leaves are converted at arm time (13.10); the encoder never meets NaN. `RESEARCH_EVALUATION_FAILED`, `RESEARCH_SERIALIZATION_FAILED` and timeouts are never cached.

Canonical encoding: sorted keys, floats as `float.hex`, integers in decimal, strings as given, null. NaN and infinity are refused at encode.

Keys:

| Key | Contents |
|---|---|
| identity prefix | `researchImplementationSha256`, `servedImplementationFingerprint`, research schema version, module revision id |
| arm key | sha256 of the identity prefix, module id, canonical module input tuple (5.2, every input's value and source id) and numeric method settings |
| link arm key | the arm key fields plus the cavity arm key of the same scenario |
| aggregate key | sha256 of the identity prefix, module id, band method id and the ordered list of (armId, arm key) |
| `requestKey` | sha256 of the identity prefix, canonical process subset, `propertyContext`, `propertySetSha256` and canonical `researchOptions` including follow flags |

Staleness rules:

1. Code. `researchImplementationSha256 = lpbf_source_identity.fingerprint_sources(PYTHON_DIR, RESEARCH_SOURCE_FILES, RESEARCH_VERSION)` (`python/lpbf_source_identity.py:87`) and `servedImplementationFingerprint = lpbf_simulation.implementation_fingerprint()` (`python/lpbf_simulation.py:283-287`) are recorded when `lpbf_research_cache` is imported and recomputed for every request. If either differs from its import-time value, the request is refused with `RESEARCH_CODE_STALE`, because a live IPC worker keeps the old modules in `sys.modules` (gate 11(b), last point). If recomputation costs more than 20 ms per request (measured in phase B), a stat-based gate (mtime and size of the listed files) decides when to rehash.
2. Material. `propertySetSha256` is the sha256 of the canonical resolved property dict after the property context is applied.
3. Options. Every option, preset, mode, range and follow flag is in the module tuples and the `requestKey`.
4. Manifest. The aggregate key lists every ordered arm key.
5. There is no time-based expiry.

Research pin: `python/lpbf_research_identity.expected` holds `researchImplementationSha256`. R-ID-1 checks it. A research code change regenerates it deliberately with a small tool modelled on `python/lpbf_fingerprint_pin.py`. It is not a guarded path and is not the served fingerprint.

Rollout: restart the dev server, which restarts the IPC daemon. `lpbf_worker.py` needs no restart, because the Build Job path is untouched; `BUILD_JOB_SOLVER_REVISION` stays `lpbf-build-job-p7b-sourced-constants-v25` (`src/store/useLpbfBuildJobStore.ts:24`).

### 3.7 Failure isolation

1. Process. Research runs only in the research lane process or its own ad-hoc process. A crash, hang or memory growth there cannot reach the served shared pool or the `lpbf_worker.py` job children (`python/lpbf_worker.py:1014-1027`, `:1165-1199`).
2. Time. The route timeout is 30000 ms; the lane deadline covers queue and run, and a run timeout recycles only the research worker. The default band budget is 1500 ms, checked before each arm starts.
3. Arm and module. Every arm evaluation is wrapped. An unexpected exception becomes a failed arm with `RESEARCH_EVALUATION_FAILED` (not cached) plus one stderr line with module, arm id and traceback. A failure while assembling one module makes that module unavailable with `RESEARCH_EVALUATION_FAILED`; the other six containers are still returned.
4. Non-finite values (Rev. 1, R11). Immediately after each arm evaluation, every non-finite numeric leaf becomes null with `NONFINITE_RESULT`, a field-specific failure of that arm, before the record is cached or aggregated (13.10). A second recursive pass before serialization does the same for any value, band or note slot; then `json.dumps(..., allow_nan=False)`. If that still raises, the script prints the `RESEARCH_SERIALIZATION_FAILED` envelope. The served serializers (`python/lpbf_worker.py:1220`, `python/lpbf_thermal_solver.py:1669`) never see research data, which removes gate finding 11(c).
5. Size. The research response is capped at 4 MiB (far below `MAX_IPC_RESPONSE_BYTES`, `server/processOrchestrator.ts:20`); above it the request fails with `RESEARCH_RESPONSE_TOO_LARGE`. Phase C records actual sizes (gate minor 14).
6. CPU. The research process lowers its own priority once per process: `os.nice(10)` on POSIX, `SetPriorityClass(GetCurrentProcess(), BELOW_NORMAL_PRIORITY_CLASS)` through `ctypes` on Windows. No new dependency. At most one research process runs at a time.
7. UI. Research errors render only inside the Research model panel. They never set the Melt Pool lab's `errorMsg` (`MeltPool3DCrossSectionLab.tsx:117`) or the Build Job store error (`useLpbfBuildJobStore.ts:273-281`).

### 3.8 Research context (the attach point that replaces the solver hook)

`lpbf_research_context.resolve(request) -> ResearchContext` (frozen dataclass, no shared mutable objects):

1. `base = thermal_props(material) or SECONDARY_THERMOPHYSICAL_DB.get(material)`; `props = dict(base)`; for a build-job snapshot, `props.update(snapshot["thermal"])` and `prop_overrides = snapshot["thermal"]`, else `prop_overrides = None`. This repeats `python/lpbf_thermal_solver.py:869-874`.
2. `k_th, cp, rho_k, convention, ... = resolve_conduction_kernel(material, props, prop_overrides, preheat_C)` and `alpha = k_th / (rho_k * cp)`, the same expression order as `:922-924`. The unrounded values are kept; the rounded display echoes are never read.
3. `A0 = float(props["absorptivity_IR"])` as at `:943` for the IR wavelength; the index absorptivity is read only for the disclosure module; `Tl = props["liquidus_C"] + 273.15`.
4. The section 3 override gate of the P8 spec is applied to `prop_overrides` (equality of the resolved tuple with the nominal tuple decides admission; semantics of partial overrides are Astra's, gate minor 15).

Verified on this branch with the public resolver at preheat 20 C: Ti-6Al-4V gives K 16.44854, cp 645.74021, rho_k 4430.0, alpha 5.749972908328388e-06, A0 0.32, Tl 1660.0 C; AlSi10Mg gives K 152.52434782608697, cp 1020.0826086956522, rho_k 2696.0, alpha 5.54605210495764e-05, A0 0.3, Tl 595.0 C; both with convention `kernel-ledger-kirchhoff`. These equal the P8 spec section 3 values. For the four Build Job alloys (`alsi10mg`, `in718`, `ss316l`, `ti6al4v`) the build-job snapshot resolves to exactly the nominal tuple.

The research conduction floor never reads a served-kernel value. Amendment 2 (section 2.2 and B5) forbids reusing served `d_iso` and defines an independent extractor (`p8-gaussian-liquidus-envelope-v2`) over the unchanged `eagar-tsai-v2` field; the research process computes it from the request tuple. The research block is therefore independent of the served heat source, and the cache key needs no served-kernel identity (gate 9(b)); the extractor identity and its settings are part of every cavity arm tuple (5.2).

## 4. UI contract (gate items 12, 13 and the caption part of 6)

### 4.1 Placement

1. Melt Pool lab: `<ResearchModelPanel host="melt-pool" />` between `CalibratedMeltpoolPanel` (`MeltPool3DCrossSectionLab.tsx:1217-1222`) and the Solidification section (`:1224`).
2. Build Job Decision lab: after the served notices (`IndustrialLPBFDecisionLab.tsx:636-638`), rendered only when `job` from `useLpbfBuildJobPython` (`:55-56`) is non-null. That hook already returns null for a job that is not aligned with the current inputs (`useLpbfBuildJobStore.ts:339-346`).
3. New file `src/components/3d-distortion-lab/ResearchModelPanel.tsx`, reachable from both labs, so `tests/component-reachability.test.ts` needs no `SHARED.json` entry.
4. Static demo: the panel renders its header and the sentence "Research models need the local engine; the static demo has no recorded research result." and dispatches nothing. No demo snapshot is recorded; `scripts/demo/` is unchanged (`src/demo/demoFetch.ts:3-4` would answer a missing snapshot with a 404 anyway).

### 4.2 Panel layout

1. Header exactly **Research model**; the panel is collapsed by default.
2. Scope line: "Separate from the served result. Research values never change the served tiles, verdict or exports."
3. Inputs section (collapsed): the A2 and A3 controls, presets and ranges, each with its provenance label and reset button (section 6), help text bound by `aria-describedby`. In a Belton mode (Amendment 2 B8) the direct slope control and its range are disabled and kept in the store, the active clean-Fe baseline is shown as a read-only value, the B8 help text is shown, and switching back to direct mode restores the saved direct value. The evaporation control offers the two conventions of 7.2 (accommodation with beta, or net factor).
4. Run bar: **Run research models**, **Cancel**, and a status line with `role="status"` and `aria-live="polite"`.
5. One section per container in the order of the P8 spec section 2 table: its `uiSentence`, the primary consistency sentence, a field table (label, nominal, scenario range, provenance), the English n/a reasons (9.2), and "Differences from the served result" (section 8). Evidence display (module labels, per-value source labels, the collapsed note) follows 13.8 (Rev. 1, R9).
6. Footer: short `requestKey`, short research implementation hash, and cache hits of the last response.

Statuses use neutral colours for every value; no green approval colour, as the P8 spec requires.

### 4.3 States and transitions

States: `idle`, `running-nominal`, `band-pending`, `complete`, `cancelled`, `stale`, `error`.

1. **Run** is enabled only when the latest `describe` response (13.9) for the current inputs reports no option problem; the client never evaluates a check or a default itself (Rev. 1, R10). Pressing it fixes the run identity (process subset, property context, options), increments the generation and sends the nominal stage.
2. On an accepted nominal response the panel shows the nominal values, shows "Computing scenario range: {armsDone} of {armsTotal}." with **Cancel**, and sends band requests one after another (each awaited) with budget 1500 ms until `complete`.
3. **Cancel** increments the generation, aborts the in-flight fetch and stops the loop; the state becomes `cancelled`. The nominal values stay, because they belong to the same identity. The band area reads "Scenario range not computed (cancelled). Run research models to compute it." No message is sent to the server.
4. Any change of a run-identity input (host process subset, property context, options, preset, ranges) increments the generation, aborts, stops the loop and hides every research value at once (state `stale`): "Inputs changed. Run research models to update." An old nominal or band is never shown beside new inputs.
5. A response is applied only when the generation matches, `clientRequestId` equals the one sent and, for band responses, `requestKey` equals the nominal response's `requestKey`.
6. Debounce: 300 ms after the last keystroke the panel sends a `describe` request (13.9) and shows its option problems inline. Typing never sends a nominal or band request; Python repeats every check on Run.
7. Errors are panel-local, worded from the registry (9.2), with **Retry**.
8. Unmount cancels.

### 4.4 Cancellation and timing guarantees

1. The screen reacts to Cancel immediately.
2. After a cancel at most one research request is still in flight, because the loop is sequential. A budgeted chunk ends within its budget plus one arm and its arm records stay cached for the next run. A null-budget fallback request (3.5 rule 6) can run until the route timeout; the re-gate measured 10 to 12 s at the default manifests and about 23 s at 50 cavity arms. No fallback request is sent after Cancel (Rev. 1, R14).
3. The next run's nominal request waits in the lane behind that one request at most.
4. In ad-hoc mode there is no persistent cache, so the band stage runs as one request (3.5 rule 6) and a cancel discards its result.
5. Per-arm times are not promised here; phase C measures them (P-7) and confirms or adjusts the default budget and the arm cap (dependency D-12).

### 4.5 State ownership (gate item 13)

New session store `src/store/useLpbfResearchModelStore.ts`. It holds the research options keyed by alloy id (Rev. 1, R10: presets are alloy-scoped, so a choice made for one alloy applies to every host showing that alloy and never to a host showing another), the per-host run state, and a bounded client result map (8 entries, keyed by the canonical request) so that switching labs with the same inputs shows a finished result without a rerun. It holds no process values: the Melt Pool host passes its local process state (the values sent at `MeltPool3DCrossSectionLab.tsx:164-175`); the Build Job host passes `specimen.lpbf`, `job.alloyId` and `job.materialPropertySha256`, with `laserWavelength` fixed to IR as in `useLpbfBuildJobStore.ts:109`.

Nothing research-related is written to `useLpbfBuildJobStore`. Unchanged: the `buildJobKey` payload, `evidenceKey` and `key` (`useLpbfBuildJobStore.ts:98-137`), `sameEvidence` (`:252-255`), the failure fallback (`:280`), `aligned` (`:307`), and the exports that read `build.job` (`src/components/LpbfEngineeringWorkspace.tsx:60` and `:117`, `src/components/EvidenceWorkspace.tsx:28`). R-UI-10 pins that research option edits, runs, failures and cancels leave `peekLpbfBuildJobKey()`, `lastKey`, `sessionEvidenceKey`, `job` and `aligned` unchanged and the exported JSON byte-identical. Research results are not added to the qualification, run-report or evidence exports in v1.

### 4.6 Served-result identity for the difference statements

The Melt Pool lab records, next to `setPyResult(res)` (`MeltPool3DCrossSectionLab.tsx:180`), the signature of the inputs that produced `pyResult` (material, P, v, d, T0, wavelength, heat source) in a ref. The panel substitutes served numbers into a difference statement only when that signature's research subset equals the panel's run identity; otherwise it renders the statement's fallback text. The Build Job host reads `job.thermal`, aligned by construction. This ref write is the only edit inside the live re-solve callback; it sends nothing.

### 4.7 Band caption and display rules (UI part of item 6)

Exact strings, pinned by R-UI-5:

| Situation | Text |
|---|---|
| Under every numeric band | Amendment 2 B3 sentence, verbatim: "Min / nominal / max is an envelope of named one-at-a-time scenarios. Interactions are not evaluated. It is not a confidence interval, an error bar, or a physical lower or upper bound." followed by "{n} named scenarios." |
| Degenerate echo band (min = nominal = max for an input echo) | "Unchanged in every declared scenario; this is not a known zero uncertainty." (B3) |
| Extremes | "Lowest: {minArmLabel}. Highest: {maxArmLabel}." Each arm label is followed by its `armProvenance` label, its `onsetEvent` when it is not the nominal event, and the phase and reference temperature of the changed inputs (6.3, 13.5), so a transferred or unsourced extreme (B3: `absorptance_0.14`, `srv`) is visible as such (Rev. 1, R6, minor note 11). |
| Ties | "{k} scenarios share the lowest value." (and "highest") when the tie count exceeds 1 |
| Partial | "{f} of {n} scenarios did not compute and are not in this range:" followed by the failed arms and their English reasons |
| Unavailable | "No scenario computed; no range is shown." |
| Pending | "Computing scenario range: {armsDone} of {armsTotal}." |
| Onset support (keyholeCavity only) | Astra's support sentence and disclaimer (P8 spec A4, with the B3 competing-convention warning), under the heading "Scenario support", followed by the counted arms whose provenance is not a sourced default, by label and provenance |

Display rules:

1. Show min, nominal and max as three numbers in that order; never "nominal ± x".
2. Show 4 significant digits on screen and the exact double in an expandable "Exact values" row (gate minor 19; the A5 rule "up to 6 significant digits" becomes the cap for the expanded note only).
3. Rendered panel text must not contain "uncertainty band", "confidence", "error bar", "±" or "probability", except inside the fixed disclaimer and the caption above. R-UI-6 scans the rendered text.

## 5. Manifest and dependency rule (gate item 7, schema part of item 15)

### 5.1 Per-module manifests

The single global manifest is replaced by module manifests:

| Manifest | Used by | Arms |
|---|---|---|
| cavity | keyholeCavity and meltDepthLink | nominal, absorptance, property tuples, vapour-source scenarios (including the O8 Mg-inclusive arm for AlSi10Mg, B7), the inception-convention arms O1 and O3 (each carrying its event, B3; O2 is excluded, Amendment 3 C1), process ±5% arms. Never a user Marangoni or surface endpoint and never a flow-only assumption arm. |
| marangoni | marangoni | every declared arm, deduplicated on the Marangoni input tuple, plus the flow-only assumption arms of B3 and user Marangoni endpoints. In a Belton mode no direct-slope endpoint enters (B8). |
| surfaceBalance | surfaceBalance | every declared arm, deduplicated on the surface input tuple, plus user surface endpoints |
| o8 | alSi10MgVapourMgAware | its own composition, route, enthalpy and boiling-constant arms (B7); never counted in cavity onset support |
| none | alSi10MgIndexDisclosure, unavailablePhysics | no band |

The declared arm lists per alloy, with sources and labels, are physics and come from Amendment 2 and its fixture. At 200 W the Amendment 3 fixture has, after this deduplication, Ti-6Al-4V 20 cavity/link arms (inception support 20 of 20; O2 outside), 17 Marangoni and 19 surface arms; AlSi10Mg 25 (22 of 25), 13 and 24. Amendment 3 C7 declares the secondary manifests: IN625 Marangoni 7, surface 8 (9 with the explicit `vapour_melt_in625_raoult` alternative); IN718 8 and 8; 316L 7 and 8 (Rev. 1, R15). This contract fixes how manifests are built, keyed and counted; 13.14 gives the rule for an alloy and module without a declared manifest.

### 5.2 Module input tuple and deduplication

Each module declares a closed input list in `lpbf_research_manifest.py`, taken from the inputs the Amendment 2 fixture records per arm. Example for the cavity manifest: alloy, P, v, d, T0, K, cp, rho_k, alpha, A0, Tl, Tv, Lv, M, beta_r, reference pressure, onset event, floor extractor identity, numeric settings. For every input the tuple holds (name, value as float.hex or string, sourceId). An arm's tuple is the module-local nominal with the arm's changes applied.

1. Arms with equal tuples are one scenario for that module. The first in declared order keeps its armId; later ids are listed in `aliasArmIds`.
2. sourceId is part of the tuple, so equal numbers from different sources stay distinct (A4 provenance rule). An arm that changes no input of the module aliases that module's nominal.
3. Consequences: a surface-only user range never changes the cavity manifest, its n, the onset support or any cavity cache key. A power arm aliases the Marangoni nominal while deltaT is a fixed input.

### 5.3 Arm descriptor (closed)

```ts
type ResearchArmDescriptor = {
  armId: string;   // fixture ids; user endpoints "user:<module>:<inputKey>:low" or ":high"
  family: "nominal" | "absorptance" | "property-tuple" | "vapour-source" | "onset-criterion"
        | "flow-assumption" | "composition" | "process" | "user-endpoint";
  label: string;   // short English, for example "Absorptance 0.26 (Ye 2019 Table 1)"
  onsetEvent: string | null;   // fixture values: "dwell" (nominal), "O1", "O3"; O2 is not an arm of the envelope (Rev. 1, R1)
  armProvenance: ResearchInputProvenance;   // Rev. 1, R6: the fixture's per-arm provenance record (13.5)
  changes: {
    input: string;
    value: ResearchField<number | string>;
    nominalAnchor: ResearchField<number | string> | null;   // the module-local nominal this arm departs from
    provenance: ResearchInputProvenance;                    // includes phase and reference temperature (6.3)
  }[];
  aliasArmIds: string[];
};
```

`band.manifest` becomes the ordered descriptor list instead of a bare id list (gate item 15 and B3 ask for per-arm provenance; the provenance values themselves are fixture data).

User endpoints are ordered by admitted input key, low before high, after the declared arms (A4 item 5). Their ids are unique and deterministic, and each carries its parameter, units, nominal anchor and endpoint value (B3).

### 5.4 Extremes and ties

`minArmId` is the first arm in manifest order whose value equals the minimum exactly (float equality); `maxArmId` likewise. New structural integers `minArmTies` and `maxArmTies` count the arms at each extreme. Failed arms never set an extreme.

### 5.5 Onset support, cross-module references, cap

1. (Rev. 1, R1) The onset statement and its `statusSupport` counts appear only in `keyholeCavity.band`; meltDepthLink shows "Scenario support: see Conditional cavity estimate". Only arms inside the inception envelope (the nominal `dwell` event and the inception conventions O1 and O3, Amendment 3 C1) vote and can set an extreme; the denominator n counts those arms after deduplication. O2 (event `geometric-R-about-1`) never enters the cavity or link envelope, an extreme or the support count. It is reported in the separate structural list `keyholeCavity.geometricThresholdDiagnostics` (`armId`, `event`, `thresholdPower_W`, `thresholdToInceptionRatio`, provenance, and `includedInInceptionEnvelope: false`), as the fixture records it, so its exclusion stays visible. The support caption names the excluded event.
2. (Rev. 1, R15, Amendment 3 C6) A deduplicated arm id is first resolved through `aliasArmIds` to its retained equivalent before any cross-module lookup. Marangoni and surfaceBalance `validRange` values of P/P* and scan Pe are then read from the cavity record of the same resolved armId, else from the cavity nominal, and the per-arm note says which. The B2 onset-mismatch comparison never falls back to the nominal: it needs a cavity record with the same thermal tuple, vapour triple and onset event as the reading arm, and it evaluates the surface side with the reading arm's own coefficients (accommodation, net factor, recoil fraction, emissivity). Without such a record (user vapour endpoint, custom triple, changed thermal tuple) the comparison is `tuple-mismatch`; with a different onset event it is `event-mismatch`; both leave the comparison values null with their code (7.2). These reads add no arms to the reading module; every referenced cavity arm key, alias resolution and comparison dependency enters the reading arm's cache key.
3. Arm cap: 80 per module manifest after deduplication. Above it that module alone is unavailable with `RESEARCH_ARM_LIMIT_EXCEEDED`. With the currently admitted range keys the cap is unreachable (gate minor 17); R-MAN tests it with an injected declared-arm table.

## 6. Provenance vocabulary (gate item 14)

### 6.1 Leaf roles

(Rev. 1, R6, R13.) The RULES.md-style `evidenceKind` literal on every leaf is replaced by two separate statements, as the maintainer decided (13.12): the module evidence ceiling `moduleEvidenceCeiling: "screening-only"` on every container (shown once per module as "Screening only"), and a per-value `sourceEvidenceKind` (`"Literature estimate"`, `"User input"`, `"Unresolved"`, or null for non-evidence leaves) that never raises the ceiling. Every `ResearchField` gains `leafRole`:

| leafRole | Meaning | sourceEvidenceKind | Provenance label shown |
|---|---|---|---|
| `requestInput` | echo of a process request value (P, v, d, T0, alloy, wavelength) | "User input" on the echo itself, as the Amendment 3 records carry it; excluded from the derived-output rule (13.12) | "request input" |
| `physicalInput` | physical or coefficient input echo; its kind (6.3) says where it comes from | from its record: "Literature estimate" for a located source (sourceDefault, sourceModelAssumption, sourcedAlternative, alloyTransfer, modelConvention), "Unresolved" for declaredAssumption and legacyEstimate, "User input" for userInput, the governing rule for followsInput, and for `derived` the record's own label, which it computes from its `dependsOn` records (for example `vapour_o8` Tv, Lv and M: `derived`, `dependsOn` the O8 composition, hybrid route, Mg Tb convention and local-slope enthalpy records, Literature estimate with status extrapolated) (Rev. 2) | the kind label of 13.5 |
| `softwareLimit` | computational policy bound (Pe 0.01 to 10, R_bound 10, scan sizes, tolerances, the arm cap) | null | "software limit (not a physical cutoff)" |
| `convention` | enum, identifier, solver setting or index convention (`decision`, `classificationChanged`, `selectedBranch`, `observable`, `onsetEvent`, `floorFieldModelId`, `floorExtractorId`, `conductionStatus`, `linkDispatch`, `slopeBaseline`, `evaporationConvention`, `pressureRoute`, `calculationStatus`, `evaluationLocation`, `quadratureOrder`, `xSamples`, `iterations`) | null | "convention" |
| `indexConvention` | `alSi10MgIndexDisclosure.indexAbsorptance`, the served regime-index convention (`python/four_alloy_materials.py:625-631`, "regime-index-convention", not a measurement) | null | "served index convention (not a physical absorptance)" |
| `derived` | computed output, including band min and max wrappers | the decided rule of 6.2 over its determining physical and coefficient inputs; a band endpoint uses the inputs of the arm that generated it | "research result: {sourceEvidenceKind}", with the named inputs (13.8) |

`moduleMaturity`, `experimentalValidation: false`, `uiSentence` and the status string `validationStatus` stay on every leaf, as in the P8 spec section 2. Amendment 3 C4 fixes the status semantics (Rev. 1, R7): non-surface leaves carry "Not experimentally validated; research diagnostic/model only." with the locator `docs/research/SPEC_p8_research_arm_2026-10-14.md Amendment 3 C4` in the structural member `validationStatusLocator`; every value that depends on the flat surface closure carries the B2 falsified-closure status wherever it is displayed, including the surface-derived `onsetMismatch` values inside cavity and link notes. The status follows the value's dependency, not the container that shows it. No status names `.orchestra/GOAL.md` (gitignored, gate 4(e)); R-CODE checks the strings and locators.

### 6.2 Source label of derived leaves (decided by the maintainer, 2026-10-15; Rev. 1, R13)

The rule is the maintainer's decision 2 (13.12): all determining inputs sourced, "Literature estimate" with their sources; any user-typed input, "User input" naming those inputs; any unsourced default, "Unresolved" naming those inputs; Unresolved takes precedence over User input; a user input left at its sourced default keeps the sourced label. The application details are in 13.12. The structural lists `weakestInputs` (inputs that made it Unresolved or User input) and `labelSources` (source locators behind a Literature estimate) are rendered (13.8).

### 6.3 Input provenance (replaces the A1 `ResearchInputProvenance`)

```ts
// Rev. 1, R6: the closed kind enum is Amendment 3 C7's vocabulary (p8_input_provenance.KINDS).
type ResearchInputProvenance = {
  kind: "sourceDefault" | "sourceModelAssumption" | "sourcedAlternative" | "alloyTransfer" | "modelConvention"
      | "declaredAssumption" | "legacyEstimate" | "userInput" | "followsInput" | "derived";
  label: string;                         // display label from the kind table in 13.5
  sourceId: string;                      // stable id; part of the module tuple (5.2)
  sourceLocator: string | null;          // located physical source only; never a ledger placeholder
  declarationLocator: string | null;     // where an unsourced declaration is made (for example A4, B3)
  source: string | null;                 // short source text
  scope: string;                         // transfer, range or event scope text
  status: "inRange" | "extrapolated" | "outOfRange";
  sourceEvidenceKind: "Literature estimate" | "User input" | "Unresolved" | "Measured";  // Measured: transcribed data only; no v1 research value
  defaultValue: number | string | null;  // what Reset restores; null when there is no default
  defaultKind: string | null;            // kind of the default value
  followsInput: string | null;           // for followsInput: the governing input
  followState: "following" | "user-fixed" | null;
  dependsOn: string[];                   // inputs a followed or derived value depends on
  phase: "solid" | "liquid" | "solid-liquid-mean" | "vapour" | "process" | null;
  referenceTemperature_K: number | null;
  sourceRange_K: [number, number] | null;  // null: source range not established (never invented)
};
```

Rules:

1. `sourceLocator` is plain structural text. One record can no longer read "user input" and "Literature estimate" at once (gate 14(a)).
2. A value that follows another input (length from d, Tref from deltaT, Al viscosity from Tref) has kind `followsInput` while it follows; `defaultKind` gives the kind of the rule itself (for example `declaredAssumption` for L = d). Typing a value switches it to `userInput` with `followState: "user-fixed"` until reset.
3. Reset button text by `defaultKind`: "Reset to sourced default", "Reset to source model assumption", "Reset to {kind label}" for a transfer or a sourced alternative, "Reset to declared assumption", or "Clear (input required)" when null. A legacy estimate is never a default; it is offered only as an explicit scenario. No control without a sourced default shows "Reset to sourced default".
4. Every output's input summary lists the kinds of its inputs; any `userInput` shows "user input" beside the output.
5. (Rev. 2) A `sourceLocator` may cite the PROPERTY_LEDGER only through the ledger entry's own source and locator for that exact value (for example the Ti Kirchhoff forms, Gan 2021 SI Table 1). A ledger entry marked OPEN, or one with no locator of its own (for example the AlSi10Mg vapour tuple, `python/four_alloy_materials.py:510-511`), never becomes a `sourceLocator`: such a value is `declaredAssumption` with a `declarationLocator`, or `derived` from located records (O8). This is the only sense of "no generic PROPERTY_LEDGER fallback" in 13.5.

Host ceiling (decided by the maintainer, 2026-10-15, decision 1; Rev. 1, R13): the `3d-distortion-lab` contract keeps its `screening-only` ceiling (`src/generated/moduleRegistry.json`; `PENDING_ORACLE_CEILING` at `python/module_contract.py:58`) and no ceiling is raised. Every research container carries `moduleEvidenceCeiling: "screening-only"`. The per-value `sourceEvidenceKind` is a source label, not a module evidence claim, so it is not compared with the ceiling. Because the legacy contract declares no `emits`, the registry check never runs for this operation; R-CODE therefore asserts directly that every research container's `moduleEvidenceCeiling` is within the host ceiling (`module_contract.within_ceiling`, `:136-141`).

## 7. Leaf names and labels (gate item 17)

Amendment 2 B9 leaves final names to this contract ("naming aliases are settled by the integration contract", B2). Because sections 5 to 9 change closed names and wrappers, the block's `schemaVersion` becomes `p8-research-v3` (the spec's section 2 still says `p8-research-v2`). UI labels come from Python (`lpbf_research_codes.LEAF_LABELS`) and travel in the response `labels` map; TypeScript never authors a research label.

### 7.1 Renames of existing leaves

| Current | New | UI label |
|---|---|---|
| `surfaceBalance.peakTemperatureProxy_K` | removed (it was an alias of `beamCenterBalanceTemperature_K`) | none |
| `surfaceBalance.beamCenterBalanceTemperature_K` | unchanged | "Beam-centre balance temperature (flat HKL diagnostic, not the surface maximum)" |
| `surfaceBalance.recoilPressure_Pa` | `beamCenterRecoilPressure_Pa` | "Beam-centre recoil pressure (flat HKL diagnostic)" |
| `unavailablePhysics.peakTemperature_K` | `physicalWallPeakTemperature_K` | "Physical cavity-wall peak temperature" |
| `unavailablePhysics.recoilPressure_Pa` | `physicalWallRecoilPressure_Pa` | "Physical cavity-wall recoil pressure" |
| `keyholeCavity.aspectRatio`, `roots[].aspectRatio` | `aspectRatio_e_over_d` | "Cavity depth over beam diameter, e/d" |
| `roots[].stability` | `scalarRelaxation` (the fixture name; values unchanged; Rev. 1, R4) | "Scalar root relaxation (not keyhole stability)" |
| `selectedBranch` value `lowest-strictly-stable` | value unchanged | "Lowest root that relaxes back (branch convention)" |
| `keyholeCavity.peclet` | unchanged | "Pe = v d / (2 alpha), served conduction-kernel diffusivity" (Rev. 1, R5) |
| `surfaceBalance.lossFreeCenterTemperature_K` | unchanged | "Loss-free beam-centre intermediate (not a physical temperature)" (Rev. 1, R5) |
| `marangoni.sulfur_ppm`, `marangoni.oxygen_ppm` (fields and `researchOptions.marangoni`) | `solubleSulfur_ppm`, `solubleOxygen_ppm` | "Soluble S for the Fe-S analogue (ppm)", "Soluble O for the Fe-O analogue (ppm)" |
| `marangoni.effectiveConductivityCorrection`, `aspectRatioCorrection`, `correctedConductionDepth_um` | removed from `marangoni.fields`; the one null record `unavailablePhysics.marangoniWidthDepthCorrection` stays | none (gate minor 10) |

Label rules:

1. No label, help text or sentence uses "peak" for the beam-centre scalar.
2. No research label equals a served label. Pinned served labels to avoid: the aspect label at `MeltPool3DCrossSectionLab.tsx:1137`, the sulfur slider label at `:925`, and the tile labels at `IndustrialLPBFDecisionLab.tsx:624-632`. R-UI-7 checks the `labels` map against this list.
3. Research labels render only inside the Research model panel.
4. Every field path the response emits has a label (R-UI-7, R-CODE).

### 7.2 New leaves and wrappers required by Amendment 2

| Container | Name | Role and unit | Content |
|---|---|---|---|
| meltDepthLink | `floorFieldModelId` (replaces `floorModelId`) | convention, 1 | `eagar-tsai-v2`, the unchanged field identity (B5) |
| meltDepthLink | `floorExtractorId` | convention, 1 | `p8-gaussian-liquidus-envelope-v2` (B5) |
| meltDepthLink | `conductionStatus` (the fixture name; Rev. 1, R4) | convention, 1 | `computed` or `no-melting`; a resolved no-melting floor is exactly 0 um; an extraction failure is null with `CONDUCTION_EXTENT_UNRESOLVED` (B5) |
| meltDepthLink | `linkDispatch` | convention, 1 | `gaussian-below-onset` or `conditional-line-above-onset` (fixture values) |
| meltDepthLink | `wallConductionPower_W` | derived, W | K (Tv-T0) g e, the wall balance that sizes e (B6) |
| meltDepthLink | `cavityLedgerRatio` (Rev. 1, R4; replaces the withdrawn reciprocal `wallToSplitCavityPowerRatio`) | derived, 1 | `cavityPower_W / wallConductionPower_W`, the fixture direction (`p8_amendment1_synthetic.py`, `cavityLedgerRatio=qc/wall`); null with `NOT_APPLICABLE_BELOW_ONSET` at e = 0 (B6) |
| keyholeCavity, meltDepthLink, surfaceBalance notes | `onsetMismatch` | structural object of derived ResearchFields | `onsetPower_W`, `thresholdTemperature_K`, `surfaceTemperatureAtOnsetPower_K`, `surfaceRecoilAtOnsetPower_Pa`, `surfaceThresholdPower_W`, `surfaceToCavityOnsetRatio` (fixture `onsetSurfaceContradictions` names, mapped in 13.3), plus structural `comparison` (closed enum, Rev. 1, R15): `matching-tuple`, `event-mismatch`, `tuple-mismatch` or `unavailable`, with `reasonCode` and `comparedArmId`. Always present. The surface-derived values carry the B2 falsified status wherever shown (6.1); `onsetPower_W` and `thresholdTemperature_K` keep their own status (Amendment 3 C4) |
| marangoni | `slopeBaseline` | convention, 1 | `alloy-direct` or `fe-clean-analogue` (B8) |
| surfaceBalance | `evaporationConvention` | convention, 1 | `accommodation-and-beta` (default) or `net-factor` (B3) |
| surfaceBalance | `netEvaporationFactor` | input echo, 1 | the user net factor in `net-factor` convention (for example 0.82); null with `NOT_APPLICABLE_FOR_CONVENTION` otherwise |
| surfaceBalance | `effectiveNetFactor`, `effectiveAccommodation` | derived, 1 | always populated: accommodation x (1-beta), or the net factor; the fixture's `effectiveNetFactor` maps here (Rev. 1, R4) |
| every consistency note | `validRange.temperatureRanges` (replaces `temperature_K`, `temperatureMin_K`, `temperatureMax_K`) | list of `{property, phase, referenceTemperature_K, sourceRange_K, status}`; `status` closed enum (Rev. 1, R15): `inRange`, `extrapolated`, `outOfRange`, `rangeNotEstablished` (the last with `SOURCE_RANGE_NOT_ESTABLISHED`) | one entry per property with a stated source range, so liquid-phase properties are never judged by one aggregate flag (B3 last paragraph, gate 7) |

`onsetMismatch` carries the B2 unconditional statement in the note's assumptions, not as the primary sentence (9.2). The field-shape carrier `fieldShapeStep` (R2) is defined in 13.15.

## 8. Difference statements (gate item 18)

Python authors the templates in `lpbf_research_codes.py`. Each container named in the first research path of a row carries that row in its structural list `servedDifferences` (Rev. 1, minor note 12):

```ts
type DifferenceCondition = "always" | "served-null" | "served-number" | "research-positive" | "alloy-alsi10mg"
  | "host-build-job" | "host-melt-pool" | "served-kernel-eagar-tsai-and-below-onset";   // Rev. 1, R5
type ServedDifference = {
  id: string;
  servedPaths: string[];    // paths into the served thermal result (PythonLPBFResult)
  researchPaths: string[];  // paths into researchModels
  variants: { when: DifferenceCondition[]; template: string }[];   // first variant whose conditions all hold
  fallback: string;         // text used when the served result for these inputs is not loaded
};
```

Path notation: a served path is a dotted path from the root of the served thermal result (`job.thermal` in the Build Job host); a research path `<container>.<field>` names `researchModels.<container>.fields.<field>`. Placeholders `{served:<path>}` and `{research:<path>}` render the value with its unit at 4 significant digits, or the word "unavailable" when the value is null (Rev. 1, minor note 12); templates carry no unit after a placeholder. `{servedKernel}` is the served heat-source name. TypeScript substitutes values only when the served identity matches (4.6) and evaluates the conditions from this closed list; otherwise it renders `fallback`. Statements appear only under "Differences from the served result" in the research section, never in served tiles. All templates are W-1 drafts (Rev. 1, R5).

| Id | Served path | Research path | Variant conditions | Template (W-1 draft) |
|---|---|---|---|---|
| D1 | `hydrodynamicsAndRecoil.peakTemperature_C`, `peakUnavailableReason` | `surfaceBalance.lossFreeCenterTemperature_K` | served-null | "The served peak temperature is withheld: {served:hydrodynamicsAndRecoil.peakUnavailableReason}. The same reason applies to the research loss-free beam-centre value ({research:surfaceBalance.lossFreeCenterTemperature_K}): it is a loss-free intermediate, not a physical temperature, and is shown only as an input to the falsified flat surface balance." |
| D2 | `hydrodynamicsAndRecoil.knudsenRecoilPressure_kPa`, `recoilPressureUnavailableReason` | `surfaceBalance.beamCenterRecoilPressure_Pa` | served-null | "The served recoil pressure is unavailable: {served:hydrodynamicsAndRecoil.recoilPressureUnavailableReason}. The research beam-centre recoil pressure is an artefact of a falsified flat surface closure, shown only as a mathematical diagnostic; it does not replace the served refusal." (shipped reference: P8 spec Amendment 2 B2 and Amendment 3 C4) |
| D3 | `marangoniModel.surfaceVelocity_m_s`, `marangoniModel.dGamma_dT_N_mK` | `marangoni.surfaceVelocityScale_m_s`, `marangoni.surfaceTensionSlope_N_mK` | always | "The served Marangoni block uses slope {served:marangoniModel.dGamma_dT_N_mK} and gives velocity {served:marangoniModel.surfaceVelocity_m_s}. The research velocity scale ({research:marangoni.surfaceVelocityScale_m_s}) uses slope {research:marangoni.surfaceTensionSlope_N_mK}. They are separate models and are not reconciled." |
| D4 | `meltPoolGeometry.regime`, `keyholeModel.fabbroDepth_um` | `keyholeCavity.cavityDepth_um`, `keyholeCavity.onsetPower_W` | host-build-job; host-melt-pool | "The served regime label ({served:meltPoolGeometry.regime}) and the served Fabbro keyhole depth ({served:keyholeModel.fabbroDepth_um}) follow the normalised-enthalpy index and its unsourced 15 to 30 screening ramp. The research cavity depth ({research:keyholeCavity.cavityDepth_um}) uses the research onset P* = {research:keyholeCavity.onsetPower_W}; it changes neither the served regime nor the verdict." In the Melt Pool host the last clause reads "it does not change the served regime." |
| D5 | `hydrodynamicsAndRecoil.vaporTemperatureUnavailableReason` | `keyholeCavity.vapourSource` | alloy-alsi10mg | "The served model uses no elemental vapour proxy for AlSi10Mg ({served:hydrodynamicsAndRecoil.vaporTemperatureUnavailableReason}). This research model uses a pure-aluminium vapour proxy by explicit choice; the served refusal stands." (served text: `python/lpbf_thermal_solver.py:582-583`; ledger `python/four_alloy_materials.py:510-511`) |
| D6 | `keyholeModel.peclet`, `processParameters.effectiveDiffusivity_m2_s` | `keyholeCavity.peclet` | always | "Both use Pe = v d / (2 alpha). The research Pe ({research:keyholeCavity.peclet}) uses the served conduction-kernel diffusivity ({served:processParameters.effectiveDiffusivity_m2_s}); the served keyhole Pe ({served:keyholeModel.peclet}) uses the room-temperature solid diffusivity of the served Fabbro leg." (served alpha echo: `python/lpbf_thermal_solver.py:1440`; served Pe: `python/fabbro_keyhole.py:55`; Rev. 1, R5 item 4) |
| D7 | `meltPoolGeometry.aspectRatio_L_over_W`, `keyholeModel.aspectRatio_e_over_d` | `keyholeCavity.aspectRatio_e_over_d` | always | "Research e/d is cavity depth over beam diameter. The served aspect ratio tile is melt-pool length over width, a different quantity. The served Fabbro e/d is {served:keyholeModel.aspectRatio_e_over_d}." |
| D8 | `meltPoolGeometry.depth_um` | `meltDepthLink.linkedMeltDepth_um` | served-kernel-eagar-tsai-and-below-onset; always | First variant: "Below the research onset both depths come from the same Eagar-Tsai temperature field. The served depth ({served:meltPoolGeometry.depth_um}) uses the served four-probe extent; the research floor ({research:meltDepthLink.linkedMeltDepth_um}) uses a separate envelope extractor, so the two can differ." Second variant: "The served melt-pool depth ({served:meltPoolGeometry.depth_um}, {servedKernel} kernel) and the research linked melt depth ({research:meltDepthLink.linkedMeltDepth_um}) are different constructions; the research value never replaces the served depth." |
| D9 | `meltPoolGeometry.keyholeVaporCavityDepth_um` | `keyholeCavity.cavityDepth_um` | always | "The served keyhole vapour cavity depth is the increment of the Fabbro leg over the conduction depth; the research cavity depth is measured from the original surface. The two numbers are not comparable." |
| D10 | `marangoniModel.sulfur_ppm` | `marangoni.solubleSulfur_ppm` | always | "The served sulfur slider ({served:marangoniModel.sulfur_ppm}, Heiple-Roper screening) does not feed this research model. The research Fe-S analogue reads only the soluble sulfur entered here." |
| D11 | `processParameters.indexAbsorptivity`, `processParameters.effectiveAbsorptivity` | `alSi10MgIndexDisclosure.physicalToIndexRatio` | alloy-alsi10mg | "The served regime index uses absorptivity {served:processParameters.indexAbsorptivity}; the served field uses {served:processParameters.effectiveAbsorptivity}. The disclosure below explains the difference; no classification changes." |

Fallback for every row: the same sentence without numbers, ending "The served result for these inputs is not loaded."

The `uiSentence` drafts, including the keyholeCavity replacement, are in 13.4 (Rev. 1, R5).

R-LINK-1 checks that every `servedPaths` entry resolves in a `calculate_meltpool_physics` result for Ti-6Al-4V and AlSi10Mg (200 W, 800 mm/s, 80 um, 20 C) in each served kernel, and that every `researchPaths` entry exists in the closed field list of 13.3.

## 9. Reason codes, refusal wording and option checks (gate item 20)

### 9.1 Classes and precedence

| Class | Scope | Meaning | Codes |
|---|---|---|---|
| C1 | request | request refused, no block (HTTP 422, or 504 for the timeout) | `RESEARCH_REQUEST_INVALID`, `PROPERTY_SNAPSHOT_MISMATCH`, `RESEARCH_CODE_STALE`; `RESEARCH_TIMEOUT` (from `handleResearchDispatch`, 3.1) |
| C2 | request, module or arm | research failure (a bug or an oversize result; HTTP 200 envelope at request scope) | `RESEARCH_EVALUATION_FAILED`, `RESEARCH_SERIALIZATION_FAILED`, `RESEARCH_RESPONSE_TOO_LARGE` (moved from C1, Rev. 1, R8) |
| C3 | module | research option refused | `RESEARCH_OPTIONS_INVALID`, `RESEARCH_PRESET_ALLOY_MISMATCH`, `SURFACTANT_BINARY_COMBINATION_UNSUPPORTED`, `RESEARCH_ARM_LIMIT_EXCEEDED` |
| C4 | module | not admitted or not applicable | `ALLOY_CONSTANT_CHAIN_NOT_ADMITTED`, `ALLOY_NOT_ALSI10MG`, `UNSOURCED_PROPERTY_OVERRIDE` |
| C5 | module or leaf | outside a software or source range (policy refusal) | `INVALID_INPUT`, `PREHEAT_OUTSIDE_PROPERTY_SCOPE`, `WAVELENGTH_UNSUPPORTED`, `POWDER_CONTEXT_UNSUPPORTED`, `PECLET_OUTSIDE_NUMERICAL_SCOPE`, `ASPECT_BOUND_OUTSIDE_NUMERICAL_SCOPE`, `NUMERICAL_INPUT_BELOW_FLOOR`, `VAPOUR_PRESSURE_OUTSIDE_SOURCE_RANGE` |
| C6 | module or leaf | input required or reference undefined | `SURFACE_VAPOUR_INPUT_REQUIRED`, `MARANGONI_VISCOSITY_INPUT_REQUIRED`, `MARANGONI_SOLUTE_INPUT_REQUIRED` (new), `ONSET_REFERENCE_UNAVAILABLE` |
| C7 | leaf | upstream, branch, convention or comparison state | `MELT_LINK_NOT_AVAILABLE`, `NOT_APPLICABLE_BELOW_ONSET`, `NOT_APPLICABLE_FOR_CONVENTION` (new), `ONSET_COMPARISON_EVENT_MISMATCH` (new, B2), `ONSET_COMPARISON_TUPLE_MISMATCH` (new, Rev. 1, R15) |
| C8 | leaf or arm | numerical acceptance rule not met | `CYLINDER_CONVERGENCE_FAILED`, `OPTICAL_TRACE_UNRESOLVED`, `CAVITY_ROOT_SCAN_UNRESOLVED`, `CAVITY_RESIDUAL_FAILED`, `NO_STRICTLY_STABLE_ROOT`, `CONDUCTION_EXTENT_UNRESOLVED`, `MELT_BRACKET_FAILURE`, `MELT_OPTIMIZER_FAILURE`, `MELT_CONVERGENCE_FAILED`, `TIP_SHELL_UNRESOLVED`, `SURFACE_BALANCE_NO_BRACKET`, `SURFACE_BALANCE_CONVERGENCE_FAILED`, `NONFINITE_RESULT` |
| C9 | leaf | closure or data not available (permanent) | `MARANGONI_SURFACE_CHEMISTRY_UNAVAILABLE`, `MARANGONI_TRANSPORT_CLOSURE_UNAVAILABLE`, `SURFACE_BALANCE_CLOSURE_FALSIFIED`, `POWDER_ALLOY_OPTICAL_CONSTANTS_UNAVAILABLE`, `POWDER_LOT_INPUTS_UNAVAILABLE`, `POWDER_THERMAL_OPERATOR_UNAVAILABLE`, `KEYHOLE_THERMAL_FLOW_CLOSURE_UNAVAILABLE`, `SOURCE_RANGE_NOT_ESTABLISHED` |
| C10 | band | band state | `BAND_PENDING` (new), `BAND_NO_SUCCESSFUL_ARM` (new), `BAND_MANIFEST_NOT_DECLARED` (new, Rev. 1, R15) |
| W | leaf (value present) | warning, never a `reasonCode` | `LOW_PE_HYDRODYNAMICS_OMITTED`, `LOW_ASPECT_CAVITY_MECHANICS_OMITTED`, `THERMAL_CYLINDER_CLOSURE_EXTRAPOLATED` (new, B6: derived per arm from its own Pe and R), `SOURCE_SCOPE_TRANSFER` (new, Amendment 3 C3: per arm, from its `inputScopeReasons`), `FIELD_SHAPE_STEP_NEAR_ONSET` (new, Rev. 1, R2), `VAPOUR_PRESSURE_EXTRAPOLATED`, `HKL_SUBBOILING_FIXED_BETA`, `VAPOUR_CONSTANT_LV_EXTREME_EXTRAPOLATION`, `USER_COEFFICIENT_PAIR_DECOUPLED`, `FE_ANALOGUE_BASELINE_SUBSTITUTED` (new, B8: on every Belton-mode output) |

Precedence: a null leaf carries the code of the lowest class number among its causes; inside one class, the first detected in the module's fixed evaluation order. Every cause, not only the winner, is listed in the new structural member `consistencyNote.reasons`:

```ts
type ResearchReason = {
  code: string; fieldPaths: string[];
  cause: "request" | "evaluator" | "option" | "alloy-not-admitted" | "software-limit" | "source-range"
       | "input-missing" | "default-cleared" | "domain" | "upstream" | "convention" | "comparison"
       | "numerical" | "closure-falsified" | "closure-missing" | "data-missing" | "band";   // Rev. 1, R8
  quantity: string | null; value: number | string | null;
  limitMin: number | null; limitMax: number | null;       // one may be null for a one-sided limit
  allowedValues: string[] | null;                          // enum limits
  missingInputs: string[];                                 // data-missing and input-missing causes
  changeInputs: string[];   // request or option names the user can change; empty when none can
};
```

Request-level failures produce no block, so the `researchModels` root needs no `reasonCode` slot (gate 20(a), third point): the error envelope carries `reasonCode` and `problems`. A band with no successful arm has `BAND_NO_SUCCESSFUL_ARM`; a Belton mode with its ppm empty has `MARANGONI_SOLUTE_INPUT_REQUIRED` (gate 20(a), first and second points).

`NUMERICAL_INPUT_BELOW_FLOOR` (Rev. 1, R8) has one trigger: the research Gaussian floor reuses `EagarTsaiField`, which silently floors K at 1e-6 W/(m K), alpha at 1e-12 m2/s, the beam radius at 1e-7 m and the speed at 1e-6 m/s (`python/eagar_tsai_solver.py:77-79`, `:89`). When an unfloored research input is below one of these floors, the floor and linked depth are null with this code (cause `software-limit`, `changeInputs` the offending request input) instead of being computed with the floored value.

### 9.2 English n/a text per class and cause (Rev. 1, R8; W-1 drafts)

The short n/a cell text is chosen by class and `cause` and filled from the `ResearchReason` fields; each code also has a fixed noun phrase in the registry (for example `PECLET_OUTSIDE_NUMERICAL_SCOPE`: "Pe of the cavity solver"; `TIP_SHELL_UNRESOLVED`: "melt envelope near the cavity tip").

| Class and cause | Template |
|---|---|
| C1 request | "Research request refused: {problem messages}. The served result is not affected." |
| C1 `RESEARCH_CODE_STALE` | "The research code changed on disk; the research worker was restarted to load it. Running research models again." (the panel retries once automatically, 13.7) |
| C1 `RESEARCH_TIMEOUT`, `run` | "The research computation took longer than {timeout} s and was stopped; the research worker was restarted and its cache cleared. The served result is not affected." |
| C1 `RESEARCH_TIMEOUT`, `queue` | "The research request waited {timeout} s behind other research work and was not started. Nothing was computed and the research cache is kept. Run research models again." |
| C1 `RESEARCH_TIMEOUT`, `reply` | "No reply arrived from the research engine within {timeout} s. The computation may still finish in the background and cache its results. Run research models again." |
| C1 `RESEARCH_TIMEOUT`, `adhoc` | "The research computation took longer than {timeout} s and was stopped. The local engine is running without its persistent worker, so nothing was cached. The served result is not affected." |
| C2 evaluator | "The research evaluator failed for this model. The served result is not affected; details are in the local server log." |
| C2 `RESEARCH_RESPONSE_TOO_LARGE` | "The research result exceeded the 4 MiB response limit and was not sent. The served result is not affected." |
| C3 option | "Research inputs for this model were refused: {problem messages}. Other research models are unaffected." |
| C4 alloy-not-admitted | "Not computed: {phrase} for {alloy}. No input in this panel can admit it, and no value is borrowed from another alloy." |
| C5 software-limit or source-range, two-sided | "Not computed: {quantity} = {value} is outside the {limit kind} {limitMin} to {limitMax}. This is a {limit kind}, not a physical cutoff. {change clause}" |
| C5, one-sided | "Not computed: {quantity} = {value} is below the {limit kind} minimum {limitMin}." or "... above the {limit kind} maximum {limitMax}." followed by "This is a {limit kind}, not a physical cutoff. {change clause}" |
| C5, enum | "Not computed: {quantity} {value} is not supported by this research model (supported: {allowedValues}). {change clause}" |
| C5 source-range, permanent (`VAPOUR_PRESSURE_OUTSIDE_SOURCE_RANGE` on `dynamicVapourTemperature_K`) | "Not available: {phrase} lies outside its source range for every admissible input (the Mg vapour pressure exceeds the 600 to 1730 K fit and the 10 atm synthesis ceiling), so it is always withheld. No input in this panel changes this." |
| change clause | "Change {changeInputs} to evaluate it." when `changeInputs` is not empty; otherwise "No input in this panel changes this limit." |
| C6 input-missing | "Not computed: {phrase} is required and no sourced default exists for {alloy}. Enter a value to evaluate it." |
| C6 default-cleared | "Not computed: {phrase} is empty. {reset label} or enter a value." (for example `SURFACE_VAPOUR_INPUT_REQUIRED` on Ti-6Al-4V after a custom preset, where `gan-ti64` is the sourced default) |
| C6 domain | "Not computed: the onset reference is undefined for these inputs ({quantity} = {value})." (`ONSET_REFERENCE_UNAVAILABLE` when P* <= 0 or Tth <= T0) |
| C6 alloy-not-admitted | the C4 template (`ONSET_REFERENCE_UNAVAILABLE` for IN625, IN718 and 316L, where no user input can open admission) |
| C7 | "Not available: {phrase}." |
| C7 comparison | "Comparison not available: {phrase}; this arm's {event or tuple} differs from every cavity scenario." |
| C8 numerical | "Not computed: the {phrase} did not meet its numerical acceptance rule. No clipped or fallback value is shown." |
| C9 closure-falsified | "Not available: the physical {phrase} needs a coupled wall, energy and flow closure. The flat surface closure that exists is falsified and appears only as a diagnostic in Surface balance." (`SURFACE_BALANCE_CLOSURE_FALSIFIED`) |
| C9 closure-missing | "Not available: no closure for {phrase} is adopted." |
| C9 data-missing | "Not available: {phrase} needs inputs that are not in the library: {missingInputs}." |
| C10 | the pending and unavailable captions of 4.7; `BAND_MANIFEST_NOT_DECLARED`: "No scenario manifest is declared for this model and alloy; only the nominal value is shown." |

A leaf that is null for every admissible input is rendered with a permanent template and never with "Change ... to evaluate it" (Rev. 1, R8 item 2): `dynamicVapourTemperature_K` uses the "C5 source-range, permanent" row above (Rev. 2); any other such leaf uses the C9 form of its cause. Each unavailablePhysics leaf carries the validation status of its own cause (Amendment 3 C4), not a generic data-unavailable status (R8 item 3).

Each C5 code declares whether its limit is a software limit (Pe 0.01 to 10, aspect bound, numerical floors) or a source range (property scope, vapour source range). This splits the single "hard failure" sentence of A5 (gate 20(c)). The Pe policy stays 0.01 to 10, a computational limit separate from any physical range (Amendment 2 B6).

Primary consistency sentence eligibility is in 13.6 (Rev. 1, R7). The B2 unconditional onset-mismatch statement, the B6 two-ledger statement and, near onset, the C2 field-shape disclosure (13.15) are always listed in the visible note of the cavity, link and surface modules; they never compete for the primary slot and are never dropped when another sentence wins.

### 9.3 Option checks

```ts
type OptionProblem = {
  pointer: string;               // JSON pointer, for example "/researchOptions/surfaceBalance/emissivity"
  rule: "unknown-key" | "wrong-type" | "not-finite" | "below-min" | "above-max" | "range-inverted"
      | "range-excludes-nominal" | "range-without-nominal" | "mode-field-ignored"
      | "binary-combination" | "preset-alloy-mismatch" | "not-positive" | "too-large"
      | "alloy-material-mismatch" | "snapshot-hash-mismatch";
  limit: number | string | null;
  value: string;                 // JSON text of the received value, at most 64 characters
  message: string;               // English, from the template below
};
```

| Rule | Scope | Code | Message template |
|---|---|---|---|
| unknown-key | request | `RESEARCH_REQUEST_INVALID` | "Unknown key {pointer}." |
| wrong-type | request | `RESEARCH_REQUEST_INVALID` | "{label} must be a {type}." |
| not-positive | request | `RESEARCH_REQUEST_INVALID` | "{label} must be greater than 0; got {value}." |
| too-large | request | `RESEARCH_REQUEST_INVALID` | "The research request exceeds 65536 bytes." |
| alloy-material-mismatch | request | `RESEARCH_REQUEST_INVALID` | "Alloy {value} does not match material {material}." |
| snapshot-hash-mismatch | request | `PROPERTY_SNAPSHOT_MISMATCH` | "The Build Job used a different material property revision. Re-run the Build Job, then run research models." |
| not-finite | module | `RESEARCH_OPTIONS_INVALID` | "{label} must be a finite number." |
| below-min, above-max | module | `RESEARCH_OPTIONS_INVALID` | "{label} must be between {min} and {max} {unit}; got {value}." |
| range-inverted | module | `RESEARCH_OPTIONS_INVALID` | "The range for {label} has min {min} above max {max}." |
| range-excludes-nominal | module | `RESEARCH_OPTIONS_INVALID` | "The range for {label} ({min} to {max} {unit}) does not contain its current value {nominal}. Widen the range or reset it." |
| range-without-nominal | module | `RESEARCH_OPTIONS_INVALID` | "{label} has no value (input required), so a range cannot be used." |
| mode-field-ignored | module | `RESEARCH_OPTIONS_INVALID` | "{label} is not used in {mode}. Clear it or change the mode." (for example soluble S or O in direct mode, the direct slope or its range in a Belton mode, accommodation in net-factor convention) |
| binary-combination | module | `SURFACTANT_BINARY_COMBINATION_UNSUPPORTED` | "Enter soluble S or soluble O, not both; the two Fe analogues cannot be combined." |
| preset-alloy-mismatch | module | `RESEARCH_PRESET_ALLOY_MISMATCH` | "Vapour preset {value} is defined for {presetAlloy} only." |

Rules:

1. Module scoping: problems under `researchOptions.marangoni` or `ranges.marangoni` make only marangoni unavailable, with the problems listed in its note; the same for surfaceBalance. keyholeCavity, meltDepthLink, the disclosures and unavailablePhysics never read research options (A4 dependency rule) and stay byte-identical (R-TR-2).
2. Containment is checked after follow-defaults are resolved (length from d, Tref from deltaT, Al viscosity from Tref), so a range that stops containing its nominal after an unrelated edit gets `range-excludes-nominal` with the new nominal in the message. The UI re-checks on every edit of a followed input and shows the message before Run.
3. A sulfur or oxygen value or range in direct mode is refused (`mode-field-ignored`) instead of adding no-op arms (gate 20(b)).
4. A custom vapour preset with missing values is not an option refusal; it is `SURFACE_VAPOUR_INPUT_REQUIRED` (C6).
5. A preset change clears that module's vapour ranges and custom overrides in the UI and shows "Vapour ranges and overrides were cleared because the preset changed." Python treats ranges as given.
6. Units on input (gate minor 21): the slope control shows an explicit unit selector, default mN/(m K), with the A2 limits converted exactly (divide by 1000); the latent heat field shows the per-mole equivalent L x M in J/mol beside the typed J/kg value, so a per-mole number typed into the J/kg field is visible.
7. Fe-mode semantics (B8): in `fe-s-belton` or `fe-o-belton` the request carries no `surfaceTensionSlope_N_mK` and no range for it; the store keeps the direct value and restores it on return to `direct`. If a Belton request carries either, it is refused with `mode-field-ignored`. An empty soluble ppm gives `MARANGONI_SOLUTE_INPUT_REQUIRED`; a numerical 0 is a deliberate clean-Fe scenario. Every Belton-mode output carries `FE_ANALOGUE_BASELINE_SUBSTITUTED`.
8. Evaporation convention (B3): `researchOptions.surfaceBalance` gains `evaporationConvention` (`accommodation-and-beta`, default, or `net-factor`) and `netEvaporationFactor` in [0, 1]. In `net-factor` convention the net factor replaces accommodation times (1-beta), so 0.82 is admissible without forcing an accommodation above 1; `evaporationAccommodation` is then refused with `mode-field-ignored`, and the other way round. `recoilFraction` stays independent in both conventions. Ranges are admitted for `netEvaporationFactor` like any numeric surface input.

## 10. Frozen-physics scope, parity and tests

### 10.1 Scope

This is not a served bump.

| Artifact | Effect |
|---|---|
| Frozen manifest files (`python/lpbf_simulation.py:44-81`) | none touched; manifest count stays 36 |
| Fingerprint pin `python/lpbf_implementation_fingerprint.expected` (`36cd9d4a96c9726ab2ff4f3030b442f862d96f9ebdc3f724cc6dd85f55110348`) | unchanged |
| Parity goldens `python/golden/lpbf_parity/`, other goldens | unchanged |
| Parity allowlist and first-appearance entries (`python/tools/lpbf_parity_check.py:1754`) | none: no served key appears, so the first-appearance rule is never exercised |
| Honesty keys | no served honesty key added, renamed or changed; research honesty leaves exist only in the research response and are asserted by research tests |
| `HTTP_GOLDEN` digests (`python/test_lpbf_calibration_frozen.py:55-59`) | unchanged by P8; the frozen-file diff guard T-FRZ-3 (`:95-120`) stays green on this branch. P8 compares against merge-base values, not 835466fa literals (Rev. 1, R12) |
| `BUILD_JOB_SOLVER_REVISION` v25, `lpbf_job_cache.build_cache_key`, job, input and material hashes, verdict | unchanged |
| Error bands, demo snapshots, leaderboard, `DEPTH_BIAS_BANDS_ID`, stored machine calibrations | bound to the unchanged fingerprint; nothing goes stale (gate minor 13 does not arise) |
| Legacy broad cache hash (`python/lpbf_simulation.py:269-281`, used for worker job keys at `python/lpbf_worker.py:949`) | changes, because it hashes every `python/*.py` and new files are added. Previously cached build-job and GPU-pilot worker jobs are recomputed once on their next request. No served value changes. Already noted in `python/tools/lpbf_bump_record.py:187-188`. |

### 10.2 Parity case list (served side; zero edits to pins, goldens and allowlists)

| Id | Check |
|---|---|
| P-1 | (Rev. 1, R12) The fingerprint and its pin equal their values at the merge base with main (`git show <merge-base>:python/lpbf_implementation_fingerprint.expected`); T-FRZ-1 (`test_lpbf_calibration_frozen.py:69-71`) and `python/test_lpbf_implementation_fingerprint_pin.py` run unchanged. No 835466fa literal is restated, so a served bump that lands first (for example SOL-A1) cannot fail P8. |
| P-2 | (Rev. 1, R12) Branch-scoped, run once in phase G by `python/tools/p8_isolation_diff_check.py --range <p8-base>..<p8-head>`, never a permanent test: the P8 commits themselves (`<p8-base>` is the constant `P8_BASE` in that tool, 13.11, so a SOL-A1 base or later main edits do not count) touch no manifest file and none of the served entry modules `lpbf_build_job_solver.py`, `lpbf_build_job_material_snapshot.py`, `lpbf_build_job_schema.py`, `lpbf_job_cache.py`, `lpbf_worker.py`, `lpbf_process_window.py`, `lpbf_bayesian_optimizer.py`, `lpbf_screening_uq.py`, `lpbf_gr_solidification.py`, `lpbf_solidification_microstructure.py`, `lpbf_calibrated_meltpool.py`, `lpbf_calibration_layer.py`, `lpbf_machine_calibrated_meltpool.py`, `lpbf_machine_calibration.py`, `src/store/useLpbfBuildJobStore.ts`, `src/utils/lpbfBuildJobIdentity.ts`, and leave the thermal-solver route block unchanged (the 150-character rule of `test_lpbf_calibration_frozen.py:113-120`). |
| P-3 | (Rev. 1, R12) T-HTTP-1 digests equal the `HTTP_GOLDEN` values of the merge-base copy of `python/test_lpbf_calibration_frozen.py`, for the 316L input in all three kernels (Windows reference machine). |
| P-4 | `python python/tools/lpbf_parity_check.py --check` and `--check --slow`: zero drift. |
| P-5 | In one Python process: canonical served thermal JSON (without `computeTimeMs`) for Ti-6Al-4V, AlSi10Mg, Inconel 718, 316L and Inconel 625, three kernels, P 100, 200 and 400 W, v 800 mm/s, d 80 um, T0 20 C, before and after a complete research band for the same inputs: equal. This proves no shared mutable state leaks even when research runs in the same process (tests, ad-hoc use). |
| P-6 | Build Job payload for the four Build Job alloys (UQ off) before and after a research run: equal, including `solverRevision`, `buildJobIdentity`, `materialPropertySha256` and `verdict`. |
| P-7 | Measured and recorded, not promised: served thermal route p50 and p95 over 50 calls without research and with a concurrent research band loop; served `queueWaitMs`; research per-arm p50, p95 and max per module; nominal stage cold and warm; full band cold and warm for the default manifests and at the per-module cap; the ad-hoc spawn path and the null-budget fallback at the per-module cap; `describe` latency including queueing behind a band chunk (Rev. 1, R14, D-12 conditions). Acceptance: no served request waits in a research queue; any CPU-contention effect is reported, not hidden. |
| P-8 | IPC: a research run timeout leaves the shared pool generation unchanged; `METALLIX_IPC_AFFINITY=0` still isolates research; the research lane is not prestarted; a research payload with an `action` key never reaches the shared pool. |

### 10.3 Test plan

All tests are self-contained: they carry their own inputs and pinned literals, import no measured data and invoke no registered runner.

Python (new files):

| File | Tests |
|---|---|
| `python/test_lpbf_research_isolation.py` | R-ISO-1 AST import guard over `python/**/*.py`: importers of `lpbf_research_*` are only research modules and `test_lpbf_research_*`; research modules never reference `calculate_meltpool_physics`; no research file is in `IMPLEMENTATION_SOURCE_FILES`; and (Rev. 1, minor note 10) every research test runs with `calculate_meltpool_physics` patched to raise, so a transitive call (for example through `lpbf_calibration_layer._default_solver`) fails. R-ISO-3 lane configuration in a subprocess with `METALLIX_IPC_AFFINITY=0` and unset. The former R-ISO-2 diff guard is the branch-scoped phase G tool of P-2, not a permanent test (Rev. 1, R12). |
| `python/test_lpbf_research_context.py` | R-CTX-1 the 3.8 tuple literals for Ti-6Al-4V and AlSi10Mg at 20 C. R-CTX-2 equality with served internals: `unittest.mock.patch.object(lpbf_thermal_solver, "resolve_conduction_kernel", wraps=...)` during `calculate_meltpool_physics` for five alloys and three kernels, float.hex of K, cp, rho_k and alpha compared with the research context. R-CTX-3 build-job snapshot equals nominal for the four Build Job alloys; a tampered hash gives `PROPERTY_SNAPSHOT_MISMATCH`; a wrong alloy gives `alloy-material-mismatch`. R-CTX-4 SI conversions by float.hex: 800 mm/s to 0.8, 80 um to 8e-05, 20 C to 293.15. |
| `python/test_lpbf_research_transport.py` (injected deterministic fake evaluator, no physics) | R-TR-1 request-check table: each rule with code, pointer, rule and limit (for example laserPower_W 0 gives `RESEARCH_REQUEST_INVALID`, `/process/laserPower_W`, `not-positive`); booleans refused as numbers. R-TR-2 emissivity 1.2 makes surfaceBalance unavailable with `{pointer "/researchOptions/surfaceBalance/emissivity", rule "above-max", limit 1}` while the other six containers are byte-identical to a run without it. R-TR-3 stage protocol: pending bands; strictly increasing `armsDone`; the complete block equals a `timeBudgetMs: null` run; `researchModels` null while incomplete. R-TR-4 cache: cold equals warm byte for byte; a surface-only option change leaves cavity, link and Marangoni arm keys unchanged; the 1025th insert evicts the oldest; a band loop at the per-module cap completes with strictly increasing `armsDone` (Rev. 1, R14); size eviction with synthetic large entries; transient failures not cached, deterministic failures cached. R-TR-5 (Rev. 1, R11) NaN and infinity injected by the fake evaluator at the first, a middle and the last manifest position of a field give the same band, the same extremes and the same field-specific failures, and never a NaN extreme; values, bands and notes become null with `NONFINITE_RESULT`; a strict parser reads the output. R-TR-6 nominal values identical across stages. R-TR-7 an exception in one arm gives a failed arm with `RESEARCH_EVALUATION_FAILED`; an exception in one module's assembly leaves the other six containers. R-TR-8 a patched on-disk hash gives `RESEARCH_CODE_STALE`. R-TR-9 key sensitivity: every process field, property context, option, follow flag and identity hash changes `requestKey`. R-TR-10 a synthetic oversize block gives `RESEARCH_RESPONSE_TOO_LARGE`. R-TR-11 (Rev. 1, R12; Rev. 2) the CLI output for a fixed request, run with the fake evaluator, a stubbed identity provider (constant research and served hashes), a stubbed property provider (a fixed synthetic property set, so `propertySetSha256` is constant), a fixed injected declared-arm table, a fixed injected label table, an injected `cacheInstanceId` and a cold cache, equals the committed transport fixture `tests/fixtures/lpbf-research-response-v1.json`; only `computeMs` is excluded. The fixture describes transport shape only and does not change when the real evaluator lands. R-TR-12 (Rev. 1, R10) `describe` returns controls, defaults (including followed defaults evaluated in Python), provenance, labels and option problems without evaluating an arm. R-TR-13 (Rev. 1, R8) `RESEARCH_CODE_STALE` sets `recycleWorker` and the next request runs in a fresh worker; a lane timeout reaches the route as exit 124. |
| `python/test_lpbf_research_status.py` (Rev. 1, R7, R13) | R-STAT: the decided label rule of 13.12 on synthetic provenance tables (Unresolved over User input over Literature estimate; a typed value equal to its sourced default keeps the sourced label; request values excluded; band endpoints labelled by their arm); the inside-range primary sentence is rejected for every extrapolated and outOfRange note; each 13.6 sentence fires on its trigger; status follows the dependency (surface-derived `onsetMismatch` values carry the B2 status inside cavity and link notes); `moduleEvidenceCeiling` is within the host ceiling (`module_contract.within_ceiling`). |
| `python/test_persistent_ipc_research_lane.py` | R-IPC with the existing thread-pool factory pattern of `_AffinityLane` tests: run timeout recycles only the research lane; a queued research request is superseded; no prestart; the metadata guard. |
| `python/test_lpbf_research_manifest.py` | R-MAN: per-module deduplication (a power arm aliases the Marangoni nominal), sourceId distinctness, user endpoint ids and order, `minArmTies`, the per-module cap with an injected table, onset support only in keyholeCavity with the cavity denominator. |
| `python/test_lpbf_research_codes.py` | R-CODE: every code a research module emits is in the registry; every entry has class, scope and English text without em or en dashes; warnings never appear as `reasonCode`; a pinned precedence table (for example C5 `PECLET_OUTSIDE_NUMERICAL_SCOPE` with C8 `NONFINITE_RESULT` resolves to the C5 code); every emitted field path has a label. |
| `python/test_lpbf_research_links.py` | R-LINK-1 (section 8). |
| `python/test_lpbf_research_identity.py` | R-ID-1 pin equality. |
| `python/test_lpbf_research_arm.py` | Astra's physics contract (phase C). R-MAP-1 (Rev. 1, R4) applies the committed constant `FIXTURE_TO_RUNTIME` (13.3) to the fixture and fails on any unmapped or renamed key; then replay of the committed fixture `docs/research/scripts/p8_amendment1_synthetic.json` (`p8-research-synthetic-v2`): per-arm input tuples, root arrays and counts, selected branch and depth, categorical support, extrema-generating ids, onset pins (Ti 31.363133215875212 W, Al 157.1067664028826 W at 200 W, v 0.8 m/s, d 80 um, T0 293.15 K), the Amendment 3 records (O2 outside the inception envelope, the field-shape step records on both sides of P*, the status-policy cases, the secondary-alloy manifests), with the fixture's own field-specific tolerances, plus the B4 executed checks and the Amendment 3 C6 acceptance list. The test reads the fixture as data; the runtime does not. |

TypeScript (new files):

| File | Tests |
|---|---|
| `tests/lpbf-research-transport.test.ts` | the exact request body; abort; stale rejection by generation, `clientRequestId` and `requestKey`; fallback to `timeBudgetMs: null` on a changed `cacheInstanceId` or stalled `armsDone`; superseded envelope ignored; 422 problems surfaced; 504 with `RESEARCH_TIMEOUT` shown with the text of its `timeoutKind` (`queue`, `run`, `reply`, `adhoc`), and the route test asserts the two thrown-message literals of 3.1 still occur in `server/processOrchestrator.ts`; 413 for an oversize body (route test with `physicsDeps`, `routes/physics.ts:9`). |
| `tests/lpbf-research-model-panel.test.tsx` | header "Research model"; collapsed by default; research values only inside the panel; no request on mount or on input edits (R-UI-9); stale hiding; nominal, pending and complete states; Cancel; the 4.7 captions (R-UI-5); the banned-string scan (R-UI-6); labels from the response map and the served-label list (R-UI-7); difference statements with matching served identity and fallback otherwise; static demo text; keyboard access to every input, help, reset, Run and Cancel; reset button text per `defaultKind`. |
| `tests/lpbf-build-job-research-isolation.test.ts` | R-UI-10 (4.5). |
| `tests/lpbf-research-describe.test.tsx` (Rev. 2) | R-UI-12: Run stays disabled until the `describe` answer for the current inputs arrives, and again after every edit until the new answer arrives; a stale `describe` answer for older inputs never enables Run. R-UI-13: options are stored per alloy; a preset or coefficient chosen while one host shows AlSi10Mg never appears in a host showing Ti-6Al-4V, and two hosts showing the same alloy share it. |
| `tests/lpbf-research-evidence-display.test.tsx` (Rev. 1, R9) | R-UI-11 (13.8): module statements visible collapsed and expanded; the surfaceBalance collapsed note and help show the B2 status; typing a coefficient marks every dependent output "User input: {name}"; reset, or typing the sourced default, restores the sourced label; an unsourced default shows "Unresolved: {names}"; band endpoints show their arm's support; no research text contains "peak" outside D1's served clause and the physical-wall label (R-UI-6 extended, Rev. 1, R5). |
| `tests/lpbf-research-schema.test.ts` | the TypeScript response guard accepts the R-TR-11 fixture and rejects unknown keys and a wrong `schemaVersion`. |

Existing suites that must pass without edits: `python/test_lpbf_calibration_frozen.py`, `python/test_lpbf_implementation_fingerprint.py`, `python/test_lpbf_implementation_fingerprint_pin.py`, `python/test_phase6a_leaf_modules.py`, `python/test_lpbf_parity_golden.py`, `python/test_module_warm_parity.py`; with the new route literal `python/test_persistent_ipc_security.py`, `tests/persistent-ipc-auth.test.ts`, `tests/route-authority.test.ts` and `tests/module-registry.test.ts`; `tests/component-reachability.test.ts`, `tests/demo-snapshots.test.ts`, `npm run lint`, `npm run lint:eslint`, `npm run check:bundle` (the panel is lazy-loaded if the budget requires it).

## 11. Implementation phases

| Phase | Owner | Work | Acceptance |
|---|---|---|---|
| A | lead | Re-gate done 2026-10-15 (APPROVE_WITH_CHANGES); the lead checks R1 to R15 against Amendment 3 and Revision 1. | Phase A GO at e6934ffd with residuals fixed in Revision 2; maintainer decisions 1 and 2 recorded (13.12); W-1 deferred to phase C. |
| B | Opus; starts once the lead has checked R11, R12 and R14 | Isolation and transport core, including `describe`, `handleResearchDispatch`, the stale recycle and the LRU bound: `lpbf_research_models.py`, `lpbf_research_context.py`, `lpbf_research_cache.py`, the registry skeleton of `lpbf_research_codes.py`, the research pin, the `persistent_ipc_service.py` lane edits, the fake-evaluator harness. | R-ISO, R-CTX, R-TR, R-IPC and R-ID pass; P-1 to P-4 pass unchanged; the R-TR-11 fixture is committed; the per-request cost of the code-stale check is recorded. |
| C | Opus, numerics reviewed by Astra | Physics evaluator `lpbf_research_arm.py` and `lpbf_research_manifest.py` per Amendment 2, ported (not imported) from `docs/research/scripts/p8_cavity_kernel.py` and the synthetic script; full codes, labels and difference templates. | `test_lpbf_research_arm.py` replays the Amendment 2 fixture within its stated tolerances, including the 200 W manifest counts of 5.1; R-MAN, R-CODE and R-LINK pass; per-arm timings, manifest sizes and response sizes recorded (P-7, research part); budget and cap confirmed or changed by measurement (D-12). |
| D | Sonnet | Route, registry operation and regenerated registry, `DISPATCHABLE_SCRIPTS`, `pythonComputationService.solveLpbfResearchModels`, `src/types/lpbfResearchModels.ts` with its guard. | Transport and schema TS tests, persistent-ipc-auth, route-authority, module-registry, `test_persistent_ipc_security.py`, `npm run lint`. |
| E | Sonnet; Opus reviews the state machine | `ResearchModelPanel.tsx`, `useLpbfResearchModelStore.ts`, the two host mounts, the served-signature ref. | Panel and isolation tests; `npm run check:bundle`; a browser check of both panels under `npm run dev` (run, pending, complete, cancel, stale on input change; served tiles, verdict and exports unchanged), screenshots in the report. |
| F | Haiku | Chores: a distinct `P8-RA` evidence entry in `PROOF.md` (Amendment 2 naming; no collision with "P8 fresh UI archive acceptance" at `PROOF.md:3083`, gate minor 12) recording the actual runtime, parity and test checks and their limits; a short research-route note in `docs/LPBF_ENGINEERING.md`; review of `scripts/ci-unit-tests.txt` (LF); confirmation that `scripts/demo/` is unchanged. | Documentation diff only; lint passes. |
| G | Opus | Integration check and report. | P-1 to P-8; `npm run test:unit`; `npm run test:lpbf`; parity `--check --slow`; research suites; skips and failures named explicitly; local commits with explicit paths; no push. |

## 12. Open items after the re-gate

Settled by Amendments 2 and 3 and reflected above: gate items 1, 5, 8, 9, 10, 15, 16 and 21; R1 (O2 outside the inception envelope, Amendment 3 C1); R2 physics (field model kept, step disclosed and pinned on both sides of P*, C2); R6 per-input data (C5, C7); R7 status semantics (C3, C4); R15 secondary-alloy arm lists (C7).

Decided by the maintainer on 2026-10-15 and recorded in 13.12: the per-value source label under the unchanged screening-only ceiling (former M-1 and M-2). They are no longer open.

Still open:

| Id | Owner | Open point |
|---|---|---|
| W-1 | maintainer, phase C | Deferred to phase C (lead decision at Phase A GO, e6934ffd): approval of every user-facing English string drafted here (13.4, 13.6, 13.15, 9.2, section 8, 4.7 and 9.3); tests pin the approved text. |
| X-2 | Astra (spec only) | P8 spec Amendment 2 B3 (line 526) still says the fixture records "O1/O2/O3 source-convention arms"; after Amendment 3 C1, O2 is a geometric diagnostic outside the arm envelope. This contract does not edit the spec. |
| D-12 | Opus, phase C | Default band budget (1500 ms), route timeout (30000 ms), per-module cap (80) and LRU byte bound (128 MiB), confirmed by measured timings that include the ad-hoc path and the null-budget fallback at the cap. |
| X-1 | SOL integration owner, lead | The solidification plan side of R3 (bump table, swap rule, MD4, SOL-C channel). This contract's side is the statement in 1.5. |
| I-1 | lead | Confirm the reading in 13.12 rule 1 that request process values (P, v, d, T0) are the evaluation point and do not make a derived output "User input". The Amendment 3 records already exclude them ("excluded from physical-coefficient evidence rule"). |


### 12.1 Spec locations that should point to this contract (for Astra; Rev. 2)

| P8 spec location | Contract section |
|---|---|
| Section 2 (`result.researchModels`, field lists, `evidenceKind` literal, schema version) | 3.5, 6.1, 13.3 (`p8-research-v3`) |
| Section 8 (implementation plan, frozen bump, parity) | 0.1, 10, 11 |
| A1 (`researchOptions` transport, `ResearchNumericBand`, `ResearchInputProvenance`) | 3.4, 5.3, 5.4, 6.3, 13.5 |
| A4 (cache overlay, responsive UI) | 3.6, 4.3, 4.4, 13.13 |
| A5 (sentences and eligibility) | 9.2, 13.6 |
| B3 (O1/O2/O3 arms, band caption) | 4.7, 5.5 item 1, 13.2 |
| C2 (field-shape disclosure carrier) | 13.15 |
| C5 and C7 (evidence labels, provenance vocabulary) | 6.1, 6.3, 13.5, 13.12 |
| C6 (comparison identity) | 5.5 item 2, 7.2, 13.14 |

## 13. Revision 1 (re-gate 2026-10-15)

Source: `../Metalliksa-1/.orchestra/reports/p8_regate_verdict_2026-10-15.md` (APPROVE_WITH_CHANGES; the lead checks R1 to R15; phase B needs only R11, R12 and R14). Astra's Amendment 3 (`78607f3e`) resolves the physics and data side (R1, R2, R6 data, R7 status semantics, R15 arm lists) and leaves names, enums, availability, serialization and rendering to this contract. This section applies the architect's share; earlier sections changed in place are marked "Rev. 1, Rn". All user-facing strings here are W-1 drafts.

### 13.1 Index

| Item | Architect's change | Where |
|---|---|---|
| R1 | Inception-only support and extrema; O2 listed separately | 5.1, 5.5 item 1 |
| R2 | Field-shape carrier `fieldShapeStep`, warning, visible note | 13.15, 9.1, 9.2 |
| R3 | No channel to served code | 1.5 |
| R4 | Closed field list, fixture map, ratio direction, supersession rows | 13.3, 7.1, 7.2, 0.1 |
| R5 | W-1 drafts for sentences, labels, help and difference statements | 13.4, 7.1, section 8 |
| R6 | Provenance schema on the Amendment 3 vocabulary, kind labels, mapping, roles | 6.1, 6.3, 13.5 |
| R7 | Status-gated sentence eligibility and drafts | 6.1, 13.6 |
| R8 | Cause-specific templates, code classes, triggers, stale recovery, timeout code | 3.1, 3.5, 9.1, 9.2, 13.7 |
| R9 | Evidence display and its tests | 4.2, 13.8, 10.3 |
| R10 | `describe` stage; options keyed by alloy | 3.4, 3.5, 4.3, 4.5, 13.9 |
| R11 | Non-finite values handled at arm time | 3.6, 3.7, 13.10 |
| R12 | Branch-scoped isolation diff; stub-based transport fixture; merge-base comparisons | 10.2, 10.3, 13.11 |
| R13 | Maintainer decisions recorded; application rules; default outcomes | 6.1, 6.2, 6.3, 13.12 |
| R14 | LRU bound follows the cap; request-local records; O8 in the band order; 504 timeout; fallback caveat | 3.1, 3.5, 3.6, 4.4, 13.13 |
| R15 | Undeclared-manifest rule, alias resolution, comparison enum, temperature-range enum | 5.1, 5.5, 7.2, 13.14 |

### 13.2 R1 and R3

R1 is carried by 5.5 item 1: only inception-envelope arms (nominal `dwell`, O1, O3) vote or set extrema; O2 appears only in `keyholeCavity.geometricThresholdDiagnostics`. The support caption (W-1 draft) reads: "Scenario support: P exceeds the inception onset in {k} of {n} declared inception scenarios. Equal-weight named conventions, not a calibrated probability. Excluded: O2 ({event}) is a geometric threshold and is listed separately." Each extreme names its arm's `onsetEvent` (minor note 11). R3 is the statement in 1.5.

### 13.3 R4: closed runtime field list and fixture map

`researchModels.schemaVersion` is `p8-research-v3`. The closed `fields` lists are:

| Container | Fields |
|---|---|
| keyholeCavity | input echoes `alloy`, `power_W`, `speed_m_s`, `beamDiameter_m`, `preheat_K`, `liquidus_K`, `conductivity_W_mK`, `specificHeat_J_kgK`, `density_kg_m3`, `diffusivity_m2_s`, `wallAbsorptanceProxy`, `vapourTemperature_K`, `vapourLatentHeat_J_kg`, `vapourMolarMass_kg_mol`, `propertyConvention`, `propertySource`, `vapourSource`, `onsetEvent`; derived `peclet`, `thermalResponse_g`, `thresholdTemperature_K`, `onsetPower_W`, `powerOverOnset`, `modeledAboveOnset`, `cavityDepth_um`, `aspectRatio_e_over_d`, `cavityAbsorptance`, `totalAbsorptance`, `energyResidual_W`, `rootCount`, `rootTopologyStatus`, `selectedBranch`, `roots[]` (`depth_um`, `aspectRatio_e_over_d`, `scalarRelaxation`, `cavityEnergyResidual_W`, `selected`), `rootScanRelativeDifference`, `cylinderHarmonicDifference`; structural `geometricThresholdDiagnostics` |
| meltDepthLink | `cavityDepth_um`, `conductionDepth_um`, `conditionalMeltDepth_um`, `linkedMeltDepth_um`, `controllingLeg`, `linkDispatch`, `conductionStatus`, `surfacePower_W`, `cavityPower_W`, `absorbedPower_W`, `depositedThermalPower_W`, `unresolvedPower_W`, `cavityPowerFraction`, `wallConductionPower_W`, `cavityLedgerRatio`, `lossMultiplier`, `photonResidual_W`, `relativeConvergenceDifference`, `meltDepthCoarse_m`, `meltDepthRefined_m`, `conductionRefinement_m`, `conductionPeakX_m`, `conductionRearBound_m`, `quadratureOrder`, `xSamples`, `observable`, `floorFieldModelId`, `floorExtractorId` |
| marangoni | `surfaceTensionSlope_N_mK`, `slopeMode`, `slopeBaseline`, `length_m`, `deltaTemperature_K`, `referenceTemperature_K`, `viscosity_Pa_s`, `liquidConductivity_W_mK`, `liquidSpecificHeat_J_kgK`, `liquidDensity_kg_m3`, `liquidDiffusivity_m2_s`, `marangoniNumber`, `marangoniMagnitude`, `surfaceVelocityScale_m_s`, `liquidPecletScale`, `liquidReynoldsScale`, `liquidPrandtl`, `flowDirection`, `solubleSulfur_ppm`, `solubleOxygen_ppm`, `source` |
| surfaceBalance | `beamCenterBalanceTemperature_K`, `lossFreeCenterTemperature_K`, `absorbedCenterFlux_W_m2`, `conductiveAdmittance_W_m2K`, `monotonicDerivative_W_m2K`, `evaporationMassFlux_kg_m2_s`, `evaporationEnergyFlux_W_m2`, `beamCenterRecoilPressure_Pa`, `saturationPressure_Pa`, `conductionFlux_W_m2`, `radiationFlux_W_m2`, `relativeFluxResidual`, `surfaceGainRefinementRelative`, `iterations`, `evaluationLocation`, `vapourPreset`, `vapourTemperature_K`, `vapourLatentHeat_J_kg`, `vapourMolarMass_kg_mol`, `evaporationConvention`, `evaporationAccommodation`, `effectiveAccommodation`, `netEvaporationFactor`, `effectiveNetFactor`, `recoilFraction`, `emissivity`, `source` |
| alSi10MgIndexDisclosure | `physicalAbsorptance`, `indexAbsorptance`, `physicalToIndexRatio`, `decision`, `classificationChanged`, `basis` |
| alSi10MgVapourMgAware | the P8 spec section 2.3 list, unchanged |
| unavailablePhysics | `marangoniWidthDepthCorrection`, `physicalWallPeakTemperature_K`, `physicalWallRecoilPressure_Pa`, `powderAbsorptance`, `physicalKeyholeGradient_K_m`, `physicalKeyholeCoolingRate_K_s` |

Notes carry `onsetMismatch` (7.2), `fieldShapeStep` (13.15), `reasons` (9.1) and `validRange.temperatureRanges` (7.2).

Fixture-to-runtime map (only names that differ; committed as the constant `FIXTURE_TO_RUNTIME` in `lpbf_research_manifest.py` and checked by R-MAP-1):

| Fixture (`p8_amendment1_synthetic.json`) | Runtime |
|---|---|
| module key `cavity` | `keyholeCavity` |
| `lineFraction` | `cavityPowerFraction` (spec 2.2) |
| `cavityLedgerRatio` | `cavityLedgerRatio`, defined as `cavityPower_W / wallConductionPower_W`, the fixture direction (`qc/wall`). The Rev. 0 leaf `wallToSplitCavityPowerRatio`, its reciprocal, is withdrawn; band min and max arm ids follow the fixture. |
| `meltDepthRefinementRelative` | `relativeConvergenceDifference` (spec 2.2) |
| `peakTemperatureProxy_K` | `beamCenterBalanceTemperature_K` |
| `recoilPressure_Pa` (surfaceBalance) | `beamCenterRecoilPressure_Pa` |
| `energyResidualRelative` | `relativeFluxResidual` (A3) |
| `roots[].R` | `roots[].aspectRatio_e_over_d` |
| `onsetSurfaceContradictions[]` | `onsetMismatch`: `surfaceAtCavityOnset.peakTemperatureProxy_K` to `surfaceTemperatureAtOnsetPower_K`, `surfaceAtCavityOnset.recoilPressure_Pa` to `surfaceRecoilAtOnsetPower_Pa`; `onsetPower_W`, `thresholdTemperature_K`, `surfaceThresholdPower_W`, `surfaceToCavityOnsetRatio` unchanged |
| `effectiveNetFactor` | `effectiveNetFactor`, always populated; the input echo `netEvaporationFactor` is null outside the net-factor convention |
| arm `inputs` keys `P`, `v`, `d`, `T0`, `Tl`, `K`, `cp`, `rho`, `alpha`, `A`, `Tv`, `Lv`, `M`, `kl`, `cpl`, `rhol`, `slope`, `mu`, `deltaT`, `L`, `Lm`, `Tref`, `onsetMethod`, `accommodation`, `effectiveNetFactor`, `recoil`, `emissivity` | `power_W`, `speed_m_s`, `beamDiameter_m`, `preheat_K`, `liquidus_K`, `conductivity_W_mK`, `specificHeat_J_kgK`, `density_kg_m3`, `diffusivity_m2_s`, `wallAbsorptanceProxy`, `vapourTemperature_K`, `vapourLatentHeat_J_kg`, `vapourMolarMass_kg_mol`, `liquidConductivity_W_mK`, `liquidSpecificHeat_J_kgK`, `liquidDensity_kg_m3`, `surfaceTensionSlope_N_mK`, `viscosity_Pa_s`, `deltaTemperature_K`, `length_m`, `latentHeatFusion_J_kg`, `referenceTemperature_K`, `onsetEvent` (values `dwell`, `O1`, `O3`; O2 only in `geometricThresholdDiagnostics`), `evaporationAccommodation`, `effectiveNetFactor`, `recoilFraction`, `emissivity` |
| `armResults[].provenance`, `inputProvenance`, `valueProvenance`, `consistencyStatus`, `validationStatus`, `experimentalValidation`, `moduleEvidenceCeiling`, `inputScopeReasons` | see 13.5 |
| `bands[].modules.<module>.fields.<field>` (`min`, `nominal`, `max`, `minArmId`, `maxArmId`, `successfulArms`) | the leaf's `ResearchNumericBand` (A1, 5.4); ties counted at runtime as `minArmTies`, `maxArmTies` (Rev. 2) |
| `armIds` | `band.manifest`: the ordered `ResearchArmDescriptor` list (5.3), built from `armIds`, each arm's `provenance` (`armProvenance`), its `inputs` compared with the nominal (`changes`) and its `inputProvenance`; aliases from module-local deduplication (Rev. 2) |
| `categoricalSupport` (`{field: {value: count}}`) | `band.categoricalSupport`: `{field, value, count}[]` with value and count as labelled leaves (A1) (Rev. 2) |
| `statusSupport` (`{status: count}`) | `band.statusSupport`: `{status, count}[]` (A1) (Rev. 2) |
| `modeledOnsetSupport` (`above`, `total`, `unresolved`, `caveat`) | `keyholeCavity.band.onsetSupport` (`supported`, `total`, `unresolved`, `caveat`), the source of the support statement (5.5); meltDepthLink references it (Rev. 2) |
| module-level `successfulArms`, `failedArms` | `band.successfulArmCount`, `band.failedArms` (field-specific failures stay in each leaf band, 13.10) (Rev. 2) |
| module-level `validationStatus`, `experimentalValidation`, `moduleEvidenceCeiling` | the container's members of the same names (6.1) |
| `armResults[].values` | the cached arm record's values, renamed by this map |
| `armResults[].fieldShapeDiagnostics` | the per-arm `FieldShapeShare` (13.15) |

Every other fixture key keeps its name. R-MAP-1 covers only keys under `points[].values`, `bands[].modules.*` (including arm `inputs`) and nothing else (Rev. 2); fixture metadata (`evidence`, `sourceBase`, source and script hashes, `bandMethod`, `labels`, `tolerances`, `noMeltLimits`, `independentTransientChecks`, `gaussianFieldCrosschecks`, `syntheticRootTopology`, `statusSemanticsChecks`, `secondaryAlloyManifests`) is not mapped. The top-level records `onsetSurfaceContradictions`, `geometricThresholdDiagnostics` and `fieldShapeStepChecks` are mapped above and in 13.15 and are checked by their own replay assertions in `test_lpbf_research_arm.py`. Inside its scope, a key absent from this map and from the closed lists fails R-MAP-1, so a later rename cannot slip through silently.

### 13.4 R5: W-1 drafts for sentences, labels and help

| Item | Superseded spec text | W-1 draft |
|---|---|---|
| keyholeCavity `uiSentence` | section 2 table | "Conditional cavity estimate on the served conduction-kernel properties; the served keyhole leg uses room-temperature solid properties, so the two can differ (see Differences); no blind validation." |
| meltDepthLink `uiSentence` | section 2 table ("Loss-free point/line") | "Conditional melt-depth construction: the finite Gaussian conduction floor at or below onset, a surface point plus line source above it; the two fields differ near onset; no blind validation." |
| marangoni `uiSentence` | section 2 table ("explicit user inputs") | "Surface-flow diagnostic from preset or user coefficients with an assumed temperature difference and length; the velocity is a scale, not a solved flow field; no blind validation." |
| surfaceBalance `uiSentence` | section 2 table ("peak proxy", "contradiction") | "Beam-centre diagnostic of a falsified flat surface-balance closure; the numbers are closure artefacts, not a surface temperature; no blind validation." |
| surfaceBalance help | A3 help text ("peak proxy ... may be unreliable") | "Change evaporation, recoil or vapour inputs to explore the falsified flat surface-balance closure at the beam centre. Its temperature, evaporation and recoil are closure artefacts, shown only as mathematical diagnostics." |
| surfaceBalance primary sentence | A5 "Flat HKL" sentence | the Amendment 2 B2 primary sentence, verbatim |
| `beamCenterBalanceTemperature_K` label | A3 "Peak surface temperature (flat HKL proxy)" | 7.1 |
| `lossFreeCenterTemperature_K` label | none | "Loss-free beam-centre intermediate (not a physical temperature)" |
| `onsetPower_W` label | none | "Research inception onset power P* ({onsetEvent} convention)" |
| residual, refinement and convergence leaves | none | "Numerical check: {quantity} (software diagnostic)" |
| `scalarRelaxation` values | display of `stable`, `unstable`, `neutral` | "relaxes back (scalar balance)", "moves away (scalar balance)", "neutral (scalar balance)"; never the bare word "stable" (minor note 13) |
| `peclet` label and D6 | "research diffusivity" | 7.1 and D6: the research Pe uses the served conduction-kernel diffusivity |
| D1, D3, D4, D8 | section 8 Rev. 0 | section 8 |

Unchanged (Astra's text): the alSi10MgIndexDisclosure, alSi10MgVapourMgAware and unavailablePhysics `uiSentence` texts, the Amendment 2 B5, B7 and B8 sentences, and the B3 band caption. R-UI-6 additionally bans "peak" in research text except in D1's served clause and in the `physicalWallPeakTemperature_K` label.

### 13.5 R6: provenance schema, kind labels, mapping and roles

The closed `kind` enum is Amendment 3 C7's vocabulary (6.3). Display and evidence by kind:

| kind | Label shown | sourceEvidenceKind | Reset text when it is a control default |
|---|---|---|---|
| `sourceDefault` | "sourced default" | Literature estimate | "Reset to sourced default" |
| `sourceModelAssumption` | "source model assumption" | Literature estimate | "Reset to source model assumption" |
| `sourcedAlternative` | "sourced alternative" | Literature estimate | not a control default (scenario arms only) |
| `alloyTransfer` | "transferred: {scope}" | Literature estimate, with status extrapolated | "Reset to transferred default" |
| `modelConvention` | "alternative convention: {event}" | Literature estimate for the input; the event is shown | not a control default |
| `declaredAssumption` | "declared assumption (no source)" | Unresolved | "Reset to declared assumption" |
| `legacyEstimate` | "legacy estimate (no located source)" | Unresolved | never a default |
| `userInput` | "user input" | User input | none |
| `followsInput` | "follows {followsInput}" | the weakest label of its governing rule and followed inputs | "Follow {followsInput} again" |
| `derived` | "derived from {dependsOn}" | by 13.12 from `dependsOn` | none |

Mapping of the Amendment 3 fixture records:

1. `armResults[].provenance` (one record per arm) becomes the new descriptor member `armProvenance: ResearchInputProvenance` of 5.3. (Rev. 2) The arm label displayed at an extreme and in the onset-support list comes from the weakest kind among the provenance records of the inputs the arm changes, ranked weakest first: `declaredAssumption` and `legacyEstimate` (and a `followsInput` or `derived` record whose label is Unresolved); then `userInput`; then `alloyTransfer` (and a `derived` record with status extrapolated, such as `vapour_o8`); then `sourcedAlternative` and `modelConvention` (and other `derived` records); then `sourceDefault` and `sourceModelAssumption`. On a tie the first changed input in descriptor order wins; when more inputs changed, the label adds "(+{k} more)". `armProvenance` stays available in the expanded row.
2. `armResults[].inputProvenance` (one record per input key) becomes `changes[].provenance` for the inputs the arm changes and the container's `inputProvenance` map for the nominal, with keys translated by 13.3.
3. `armResults[].valueProvenance` (per derived leaf: `sourceEvidenceKind`, `dependsOn`, `weakestInputs`) becomes the derived leaf's `sourceEvidenceKind`, `dependsOn` and `weakestInputs`.
4. `consistencyStatus`, `validationStatus`, `experimentalValidation` and `moduleEvidenceCeiling` become the per-arm note status, the leaf status (6.1), `experimentalValidation` and the container's `moduleEvidenceCeiling`; `inputScopeReasons` become `SOURCE_SCOPE_TRANSFER` warnings with the reasons listed in the per-arm note.
5. The Rev. 0 arm kinds `literatureModelInput` and `unsourcedDiagnostic` are retired. There is no generic PROPERTY_LEDGER fallback: a value without a located record is `declaredAssumption` and Unresolved (Amendment 3 C5).
6. Checks pinned by R-MAP-1 and R-STAT: `absorptance_0.14` is `alloyTransfer` (Trapp Al1100) and appears as a transferred extreme and in the support list; `vapour_o8` Tv, Lv and M carry the O8 record locator, status extrapolated and the B7 scope text; Ti `vapour_3360` and `vapour_3760` Tv are `declaredAssumption`, Unresolved; `srv` is `legacyEstimate`, Unresolved.

Roles are those of 6.1. Per-input phase, reference temperature and source range come from the records; a null `sourceRange_K` renders as "source range not established".

### 13.6 R7: primary sentence eligibility and drafts

Amendment 3 C3 and C4 own the status semantics; this contract owns eligibility and wording. The primary sentence is the first eligible entry in this order:

| Order | Sentence | Eligible when |
|---|---|---|
| 1 | class sentence of the winning C1 to C8 cause (9.2) | a hard input, numerical or source refusal applies |
| 2 | falsified surface closure (Amendment 2 B2 primary sentence) | surfaceBalance notes, and any note whose primary value is surface-derived |
| 3 | O8 scenario (Amendment 2 B7) | an O8 arm note, an O8 nominal, preset `o8-mg-inclusive`, alSi10MgVapourMgAware |
| 4 | below onset (Amendment 2 B5) with its qualifier | cavity and link at P <= P*; when the note is extrapolated the qualifier "Extrapolated: {reasons}." is part of the same visible sentence |
| 5 | low aspect | cavity and link above onset with selected e/d < 0.5 |
| 6 | low Pe | cavity and link with Pe < 2 |
| 7 | Marangoni transfer (A5) | marangoni |
| 8 | source transfer (required fallback) | any other extrapolated note |
| 9 | inside range (A5, both variants) | only when the note's consistency status is `inRange` |

W-1 drafts with the meanings Amendment 3 C3 requires:

1. Source transfer: "These inputs or this closure are used beyond their declared source scope ({reasons}). Numerical admission is not a sourced physical range, and no blind validation is available."
2. Low aspect: "Above onset the selected cavity has e/d = {R}, below 0.5, outside the thermal-cylinder source geometry. This is an extrapolated conditional estimate, and cavity mechanics are omitted."
3. Low Pe: "Pe = {Pe} is below 2: the high-Pe thermal-cylinder closure used here is transferred outside its source range, and drilling, recoil-driven flow and melt transport are omitted. A converged series removes neither limitation."

The B2 statement, the B6 two-ledger statement, the C2 field-shape disclosure (13.15) and every other applicable limitation stay in the visible note whichever sentence wins. Non-surface status text is Amendment 3 C4's literal "Not experimentally validated; research diagnostic/model only." with its locator (6.1).

### 13.7 R8: further rules

1. `RESEARCH_RESPONSE_TOO_LARGE` is class C2, returned in the HTTP 200 research envelope (9.1, 3.5).
2. Stale-code recovery without a server restart: for `ISOLATED_SCRIPT_NAMES` lanes, `_execute_affinity` (`python/persistent_ipc_service.py:806-842`) recycles the lane pool after returning a result whose stdout JSON carries the top-level flag `"recycleWorker": true`; the research script sets it only with `RESEARCH_CODE_STALE`. The next request runs in a fresh worker that imports the current code, and the panel retries once automatically (R-TR-13).
3. `RESEARCH_TIMEOUT` reaches the client as a code through `handleResearchDispatch` (3.1).
4. Cause-specific templates, one-sided and enum forms, the change clause and the permanent-null rule are in 9.2; the `NUMERICAL_INPUT_BELOW_FLOOR` trigger is in 9.1.

### 13.8 R9: evidence display

1. Module header, always visible whether the module is collapsed or expanded: "Research" (moduleMaturity), "Screening only" (`moduleEvidenceCeiling`), the module `validationStatus` text with a link to its locator, and "No experimental validation" (`experimentalValidation: false`).
2. Collapsed note (each module is collapsed by default): the `uiSentence`, the `validationStatus`, the primary sentence and, near onset, the field-shape disclosure. For surfaceBalance the collapsed note and the help text both show the B2 falsified status (Amendment 2 B2).
3. Field table, column "Source support": "Literature estimate" with a sources popover from `labelSources`, "User input: {weakestInputs}" or "Unresolved: {weakestInputs}". Band min and max show the support of their generating arm.
4. Input rows: kind label (13.5), source or declaration locator, phase, reference temperature, and the source range or "source range not established".
5. R-UI-11 (10.3) pins all of the above, including that a user-typed coefficient marks every dependent output and that reset, or typing the sourced default, restores the sourced label (spec A6).

### 13.9 R10: the `describe` stage

`stage: "describe"` runs in the research lane, evaluates no arm and returns this closed shape (Rev. 2):

```ts
type ResearchControl = {
  key: string;                                  // admitted option key, for example "surfaceTensionSlope_N_mK"
  module: "marangoni" | "surfaceBalance";
  label: string; help: string;                  // W-1 drafts, authored in Python
  unit: string;                                 // SI unit of the value
  displayUnits: Record<string, number>;         // display unit to SI factor, for example {"mN/(m K)": 1000}
  valueType: "number" | "enum";
  enumValues: string[] | null;
  min: number | null; max: number | null;       // software exploration limits (A2, A3)
  enabled: boolean;                             // false, for example, for the direct slope in a Belton mode
  value: number | string | null;                // current value, followed defaults evaluated in Python
  provenance: ResearchInputProvenance;          // 6.3
  rangeAdmitted: boolean;                       // whether min/max endpoints may be entered for this key
  resetLabel: string | null;                    // 6.3 rule 3
};
type ResearchDescribeResponse = {
  success: true;
  schemaVersion: "p8-research-response-v1";
  stage: "describe";
  clientRequestId: string;
  requestKey: string;                           // the key the next nominal request would carry
  controls: ResearchControl[];
  presets: { vapourPreset: { id: string; label: string; admitted: boolean; reasonCode: string | null }[];
             slopeMode: { id: string; label: string }[] };
  labels: Record<string, string>;
  problems: OptionProblem[];                    // 9.3
  moduleAvailability: Record<string, { status: "available" | "unavailable" | "not-applicable"; reasonCode: string | null }>;
  identity: { researchImplementationSha256: string; servedImplementationFingerprint: string;
              researchSchemaVersion: string; propertySetSha256: string; propertyContextKind: string };
  channel: string;                              // added by handleResearchDispatch (3.1)
};
```

1. Followed defaults (length from d, reference temperature from deltaT, the AlSi10Mg viscosity law at the followed reference temperature) are evaluated in Python and returned as values; the UI evaluates no equation.
2. Limits, units, labels, help, presets admitted for the alloy, reset targets and option problems all come from `describe`, so the panel has them before the first Run.
3. The panel sends `describe` on mount and 300 ms after the last edit, and caches responses by request key. During a band run it can wait behind one chunk; the panel shows "Checking inputs" and keeps Run disabled until the answer for the current inputs arrives. P-7 measures this wait.
4. Options are stored per alloy (4.5), so a preset chosen for AlSi10Mg never reaches a host showing Ti-6Al-4V.

### 13.10 R11: non-finite values

1. Immediately after an arm is evaluated, every non-finite numeric leaf becomes null with `NONFINITE_RESULT`; the arm counts as failed for that field only (field-specific `failedArms`, field-specific `successfulArms`).
2. The cached record is finite-only; `NONFINITE_RESULT` is deterministic for the same inputs, so the null record is cacheable.
3. Aggregation reads finite numbers only, by an explicit loop in manifest order: the minimum is the first arm whose value is strictly below the running minimum, ties counted in `minArmTies` (5.4), and likewise for the maximum. Python `min` and `max` are never applied to a list that may contain NaN or None.
4. The serialization pass of 3.7 item 4 stays as a second guard. R-TR-5 checks order independence.

### 13.11 R12: test scoping

1. The isolation diff (P-2) is a branch-scoped phase G tool over the P8 commit range, not a permanent test. `<p8-base>` is recorded as the constant `P8_BASE` in `python/tools/p8_isolation_diff_check.py`, written by the first phase B commit (the commit phase B starts from) and repeated in the phase B report; it changes only by an explicit lead decision (Rev. 2).
2. P-1 and P-3 compare with merge-base values, never with 835466fa literals.
3. The R-TR-11 transport fixture uses stubbed identity, a stubbed property set (constant `propertySetSha256`), a fixed declared-arm table, a fixed label table, an injected `cacheInstanceId` and a cold cache; only `computeMs` is volatile. It depends on neither the physics evaluator nor served material data, so an ordinary served material edit cannot move it (Rev. 2).
4. Permanent research tests depend only on research files, the closed schema and committed fixtures, so ordinary edits to served modules (for example `lpbf_worker.py`, `useLpbfBuildJobStore.ts`, `BUILD_JOB_SOLVER_REVISION` v26 in SOL-A) cannot fail them.

### 13.12 R13: maintainer decisions (2026-10-15), recorded as decided

From `../Metalliksa-1/.orchestra/GOAL.md`, section "Label and data decisions (maintainer, 2026-10-15)":

1. Decision 1: every served or research value carries its own `sourceEvidenceKind` (Literature estimate with source and locator; Measured for transcribed measurements), while the module evidence ceiling stays screening-only until a blind test passes. No ceiling is raised.
2. Decision 2: research outputs whose inputs are all sourced defaults are "Literature estimate" (with sources); any user-typed input gives "User input", naming those inputs; any unsourced default gives "Unresolved", naming those inputs; Unresolved takes precedence over User input; a user input left at its sourced default keeps the sourced label.

Application rules (this contract; Amendment 3 C5 agrees):

1. The determining inputs of a derived leaf are its physical and coefficient inputs (`dependsOn`, within the module's physical input set of Amendment 3, `p8_input_provenance.PHYSICAL_INPUTS`). Request process values, conventions, solver settings and software limits are excluded (open item I-1 asks the lead to confirm the exclusion of process values).
2. Unresolved when any determining input is `declaredAssumption` or `legacyEstimate`, or follows a rule of that kind; otherwise User input when any determining input is `userInput`; otherwise Literature estimate. `weakestInputs` names the inputs behind Unresolved or User input; `labelSources` lists the locators behind Literature estimate.
3. A typed value that equals its sourced default (float.hex after unit conversion) keeps the default's kind and label.
4. Each band endpoint is labelled from the inputs of the arm that generated it; user endpoint arms give User input.
5. A falsified closure does not change the source label; the falsification is carried by `validationStatus` (Amendment 3 C5).
6. A transfer keeps Literature estimate with its locator; its scope stays extrapolated.
7. Measured applies only to transcribed measurements; no research leaf in v1 carries it.

Default outcomes on the Amendment 3 fixture (200 W, nominal arm; consistency status in brackets):

| Module | Ti-6Al-4V | AlSi10Mg |
|---|---|---|
| keyholeCavity | Literature estimate (extrapolated) | Literature estimate (extrapolated) |
| meltDepthLink | Literature estimate (extrapolated) | Unresolved: `Tl` (the liquidus proxy convention) on the depth leaves; Literature estimate on the power ledger (extrapolated) |
| marangoni | Unresolved: `L`, `deltaT` (extrapolated) | Unresolved: `L`, `deltaT`, `cpl`, `mu` (extrapolated) |
| surfaceBalance | Literature estimate, with the B2 falsified status (outOfRange) | Unresolved: `emissivity`, with the B2 falsified status (outOfRange) |

### 13.13 R14: transport bounds

1. LRU bound follows the cap (3.6): 1024 entries and 128 MiB hold two complete requests at 80 arms per banded module.
2. Records are held request-locally until aggregation (3.5 rule 10).
3. The band order includes alSi10MgVapourMgAware, so the O8 band completes (3.5 rule 2).
4. A timeout reaches the client as `RESEARCH_TIMEOUT` with HTTP 504 (3.1).
5. A null-budget fallback can run until the route timeout; it is never sent after Cancel (4.4 item 2). The re-gate measured 10 to 12 s at the default manifests, about 23 s at 50 cavity arms, and 3 to 6 arms per 1500 ms chunk; phase C repeats these on the ad-hoc path and at the cap (D-12).

### 13.14 R15: manifests and cross-module rules

1. Every module that runs for an alloy has a declared manifest in the fixture or the spec (Amendment 3 C7 declares IN625, IN718 and 316L). A module without one returns its band with `completeness: "unavailable"` and `BAND_MANIFEST_NOT_DECLARED`; it never presents a nominal-only band as complete.
2. Alias resolution precedes every cross-module lookup (5.5 item 2).
3. The `onsetMismatch.comparison` enum is `matching-tuple`, `event-mismatch`, `tuple-mismatch`, `unavailable`, with `ONSET_COMPARISON_EVENT_MISMATCH` and `ONSET_COMPARISON_TUPLE_MISMATCH` (7.2, 9.1). A net-factor or accommodation change recomputes the surface side with the reading arm's own coefficients (Amendment 3 C6).
4. The `temperatureRanges` status enum is `inRange`, `extrapolated`, `outOfRange`, `rangeNotEstablished` (7.2).
5. User endpoints, Belton modes and user vapour triples extend or rebuild these manifests under 5.3 and 9.3; the declared lists cover the default arms only.

### 13.15 R2: field-shape carrier

Amendment 3 C2 keeps the above-onset point plus line field and requires the Gaussian-to-point step to be disclosed. The carrier is the structural object `meltDepthLink.consistencyNote.fieldShapeStep`, also referenced from the keyholeCavity note:

```ts
// Rev. 2: two carriers, mirroring the two fixture records.
type FieldShapeStep = {                                   // meltDepthLink.consistencyNote.fieldShapeStep, one per request
  onsetPower_W: ResearchField<number>;
  relativeBracket: number;                                // structural, 1e-9 in the fixture
  gaussianDepthAtOnset_um: ResearchField<number>;         // Gaussian floor at P*
  pointDepthAtOnset_um: ResearchField<number>;            // surface-point limit just above P* (diagnostic only)
  pointMinusGaussian_um: ResearchField<number>;
  pointToGaussianRatio: ResearchField<number>;
  pointDepthIndependentCheck_um: ResearchField<number>;   // numerical check
  pointDepthIndependentDifference_m: ResearchField<number>;  // numerical check
  linkedDepthJustBelowOnset_um: ResearchField<number>;    // at P*(1-1e-9)
  linkedDepthJustAboveOnset_um: ResearchField<number>;    // at P*(1+1e-9)
  onsetSideRecords: { side: "below" | "at" | "above"; powerFactor: number;
                      values: Record<string, ResearchField<number | string>> }[];   // values use runtime names (13.3)
  aboveOnsetFieldChanged: boolean;                        // structural
  cause: string;                                          // structural text
  locator: string;                                        // P8 spec Amendment 3 C2
};
type FieldShapeShare = {                                  // per-arm note of meltDepthLink, and the nominal in the module note
  applicable: boolean;
  samePowerPointDepth_um: ResearchField<number>;
  fieldShapeExcess_um: ResearchField<number>;
  conditionalExcessOverGaussian_um: ResearchField<number>;
  fieldShapeShareOfExcess: ResearchField<number>;
  nearOnset: boolean;                                     // trigger declared by Astra in the spec (share based)
  caveat: string;                                         // structural text
};
```

Fixture-to-runtime names for these carriers (part of `FIXTURE_TO_RUNTIME`, Rev. 2):

| Fixture | Runtime |
|---|---|
| top-level `fieldShapeStepChecks[]` (one per alloy) | `meltDepthLink.consistencyNote.fieldShapeStep` |
| `atOnsetGaussianDepth_um` | `gaussianDepthAtOnset_um` |
| `aboveOnsetPointLimitDepth_um` | `pointDepthAtOnset_um` |
| `fieldShapeStep_um` | `pointMinusGaussian_um` |
| `independentPointLimitDepth_um`, `pointLimitIndependentDifference_m` | `pointDepthIndependentCheck_um`, `pointDepthIndependentDifference_m` |
| `records[]` (`side`, `powerFactor`, `inputs`, `values`) | `onsetSideRecords[]`, values renamed by 13.3; `linkedDepthJustBelowOnset_um` and `linkedDepthJustAboveOnset_um` are the `linkedMeltDepth_um` of the below and above records |
| `onsetPower_W`, `relativeBracket`, `pointToGaussianRatio`, `aboveOnsetFieldChanged`, `cause` | same names |
| `bands[].modules.meltDepthLink.armResults[].fieldShapeDiagnostics` | the per-arm `FieldShapeShare` |
| `fieldShapeShare` | `fieldShapeShareOfExcess` |
| `applicable`, `samePowerPointDepth_um`, `fieldShapeExcess_um`, `conditionalExcessOverGaussian_um`, `caveat` | same names |

Rules:

1. The same-power point baseline is a diagnostic and is never the selected conditional result at or below onset.
2. The field-shape assumption and its locator appear in every cavity and link note whose conditional model uses the Gaussian-to-point dispatch, whether `nearOnset` is true or false (Rev. 2; Amendment 3 C2). W-1 draft of that assumption: "At or below onset the link uses the finite Gaussian field; above onset it uses a surface point plus line. The two fields differ, so the linked depth can change at P* because of field shape, not because of a cavity (P8 spec Amendment 3 C2)."
3. When `nearOnset` is true, or the arm crosses onset within its band, the linked and conditional depths and `controllingLeg` also carry the warning `FIELD_SHAPE_STEP_NEAR_ONSET`, and the visible note leads its limitations with (W-1 draft): "Near onset the linked depth is dominated by the change of field shape ({fieldShapeShareOfExcess} of the excess over the Gaussian floor); controlling-leg support does not show that a cavity caused the increase."
4. Neither text is dropped when another primary sentence wins (13.6). The `nearOnset` trigger (share based) and the share computation are Astra's physics, declared in the P8 spec; the fixture pins the values.
