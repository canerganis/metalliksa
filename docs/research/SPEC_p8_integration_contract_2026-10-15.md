# P8 integration contract: opt-in research route, isolation, transport, panel and labels

Date: 2026-10-15. Owner: system architect (Opus). Scope: the engineering items 2, 7, 11, 12, 13, 14, 17, 18 and 20 and the UI/caption part of item 6 of the lead-owned gate verdict `../Metalliksa-1/.orchestra/reports/p8_gate_verdict_2026-10-15.md`.
Base: branch `research/p8-research-arm`. Its code is identical to main `835466fa` (the branch adds documents only), so every `file:line` below is a line of `835466fa`.
Companion: `docs/research/SPEC_p8_research_arm_2026-10-14.md` (base, Amendment 1 and Amendment 2; physics owner Astra). Amendment 2 landed on this branch as `1c76a2fd` while this contract was written; the contract is aligned with it. Amendment 2 (header and B9) assigns to this contract the transport, gating, caching, provenance vocabulary, field names, reason-code serialization and availability enums, and lists eight physics requirements the final schema must carry (0.2). This file does not edit the physics spec. Where this contract still needs a physics decision it says so in section 12; the re-gate reconciles both files.

Status: proposal for the re-gate. Nothing is implemented. This commit changes no code, pin, golden, allowlist or test.

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
| Section 8 items "Append after served computation", the attach parts of "Typed transport and panel", "Additive-output frozen bump", "Parity before goldens", "Parity-tool policy", "Frozen calibration assertions", and the worker-restart and revision parts of "Checks/rollout" | Sections 3, 4, 10 and 11 |
| A1 first sentence: `researchOptions` on both the standalone thermal and the Build Job requests | `researchOptions` travels only in the research route request (3.4) |
| A4 "Responsive UI" paragraph, the cache location "in the Python worker", and "Build Job cache integration correction" | Sections 3.6 and 4 |
| A6 "Build Job cache-hit overlay tests" and the section 9.1 cache sentence ("change only researchOptions on a warm served job") | Section 10.3 tests |
| Implementer "Fable" | Owners in section 11 |

The physics content (sections 3 to 7, A2, A3, the physics of A4 and A5, and Amendment 2 B1 to B8) is untouched. Where the spec's field lists and this contract's names differ (section 7), this contract's names apply, as Amendment 2 B9 assigns.

### 0.2 Amendment 2 B9 requirements and where this contract carries them

| B9 item | Requirement | Carried by |
|---|---|---|
| (1) | Distinct source, assumption, user and derived provenance, with phase and reference temperature, for each arm, input and extremum | 5.3, 6.1, 6.3, 4.7 |
| (2) | Module-local arm and event manifests, field-specific failures, deterministic ties, per-arm root arrays, counts and branch support, a non-statistical caption | 5.1 to 5.5, 3.6 (whole arm records cached), 4.7 |
| (3) | Unconditional onset-mismatch diagnostics; separate photon-split and wall-conduction ledgers | 7.2 (`onsetMismatch`, `wallConductionPower_W`, `wallToSplitCavityPowerRatio`), 9.2 |
| (4) | Falsified surface-closure status on every dependent surface diagnostic, with shipped references | 6.1, 9.2, D2 in section 8 |
| (5) | O8 band and note, feedstock, route, enthalpy and extrapolation scope, Mg-aware depth sensitivities | 5.1 (own `o8` manifest; O8 vapour arm in the cavity manifest), 9.2 |
| (6) | Independent Gaussian-floor method identity, resolved no-melting zero, below-onset dispatch | 3.8, 7.2 (`floorFieldModelId`, `floorExtractorId`, `conductionMeltState`) |
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

## 2. Files touched

| File | Change | Frozen? | Guarded path (`scripts/check_ceiling_review.py` `PROTECTED_PATHS`)? |
|---|---|---|---|
| `python/lpbf_research_models.py` | new dispatch script | no | no |
| `python/lpbf_research_context.py`, `lpbf_research_cache.py`, `lpbf_research_codes.py`, `lpbf_research_manifest.py`, `lpbf_research_arm.py` | new modules | no | no |
| `python/lpbf_research_identity.expected` | new research pin | no | no |
| `python/persistent_ipc_service.py` | allowlist entry, isolated lane, prestart filter, metadata guard | no | no |
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
  return handlePythonDispatch("python/lpbf_research_models.py", req.body, res, 30000);
});
```

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

The served thermal solver keeps the shared pool (`execute_script`, `:844-915`). Research never takes the in-process fallback, because the affinity branch returns first (`:878-880`).

Ad-hoc spawn fallback (`server/processOrchestrator.ts:647-650`): every research request is then a fresh process with a cold cache. Results are unchanged; the client detects it (3.5 rule 6).

### 3.4 Request schema (`p8-research-request-v1`, closed at every level)

```jsonc
{
  "schemaVersion": "p8-research-request-v1",
  "supersedeKey": "p8-research:melt-pool",    // or "p8-research:build-job"; 1 to 128 characters
  "clientRequestId": "melt-pool:17",           // opaque, 1 to 128 characters, echoed back
  "stage": "nominal",                          // "nominal" | "band"
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
  "stage": "nominal",                          // or "band"
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
2. `stage: "band"` with budget b builds the manifests (section 5) and looks up every arm key. It computes uncached arms in a fixed order (modules keyholeCavity, meltDepthLink, marangoni, surfaceBalance; manifest order inside each) and stops starting new arms once the elapsed time reaches b. It always computes at least one uncached arm, so every request makes progress.
3. When every arm is available, it aggregates (cached under the aggregate key) and returns the full block with `complete`, `partial` or `unavailable` bands, and `progress.complete = true`.
4. Otherwise it returns `researchModels: null` with the progress counts. A partial envelope is never sent or shown.
5. `timeBudgetMs: null` computes every remaining arm in one request, bounded by the route timeout.
6. Client fallback: when two consecutive band responses carry different `cacheInstanceId`, or `armsDone` does not increase, the client sends one band request with `timeBudgetMs: null`.
7. The nominal arm records are the same cache entries the band stage uses. A nominal leaf value is byte-identical in the nominal and the complete response (R-TR-6).
8. Determinism: for one `requestKey`, `researchModels` and `labels` are byte-identical between cold and warm runs.
9. A meltDepthLink arm reads the keyholeCavity record of the same scenario; the cavity arm is always evaluated first and the link arm key includes the cavity arm key.

Outcomes and HTTP status:

| Outcome | stdout | Exit | HTTP |
|---|---|---|---|
| Request refused | `{"success": false, "errorKind": <the literal mapped to 422 at server/pythonDispatchStatus.ts:15>, "reasonCode": "RESEARCH_REQUEST_INVALID" or "PROPERTY_SNAPSHOT_MISMATCH" or "RESEARCH_CODE_STALE", "problems": [OptionProblem]}` | 2 | 422 |
| Request-scope research failure (a bug outside any module) | `{"success": false, "errorKind": "research", "reasonCode": "RESEARCH_EVALUATION_FAILED" or "RESEARCH_SERIALIZATION_FAILED" or "RESEARCH_RESPONSE_TOO_LARGE"}`; traceback on stderr only | 0 | 200 (`pythonDispatchStatus`, `server/pythonDispatchStatus.ts:11-16`) |
| Crash before any stdout | empty; stderr | nonzero | 500 (`routes/physics.ts:18-24`) |
| Lane timeout | empty; stderr "Execution timed out ..." (`persistent_ipc_service.py:833-840`) | 124 | 500; the client shows `RESEARCH_TIMEOUT` |
| Superseded while queued | `{"success": false, "status": "superseded", ...}` (`persistent_ipc_service.py:826-832`) | 0 | 200; the client ignores it |

### 3.6 Cache

Location: a module-level `OrderedDict` in `python/lpbf_research_cache.py`, inside the single research lane process. It survives between requests because imported modules stay in `sys.modules`; it is empty after a daemon restart, after a lane recycle (timeout or worker death) and in every ad-hoc spawn. It is never persisted and never shared with served code. It is never held in the dispatch script, whose namespace is fresh per request.

Bounds: LRU with at most 256 entries and 64 MiB, measured as the UTF-8 length of each entry's canonical JSON at insert; the oldest entries are evicted until both bounds hold.

Entries: one arm record per (module, arm), and one aggregate per module. Successful arms and arms failed with a deterministic code (classes C3 to C9 of 9.1) are cached. `RESEARCH_EVALUATION_FAILED`, `RESEARCH_SERIALIZATION_FAILED` and timeouts are never cached.

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
4. Non-finite values. Before serialization a recursive pass replaces every non-finite float in a value, band or note slot by null with `NONFINITE_RESULT`; then `json.dumps(..., allow_nan=False)`. If that still raises, the script prints the `RESEARCH_SERIALIZATION_FAILED` envelope. The served serializers (`python/lpbf_worker.py:1220`, `python/lpbf_thermal_solver.py:1669`) never see research data, which removes gate finding 11(c).
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
5. One section per container in the order of the P8 spec section 2 table: its `uiSentence`, the primary consistency sentence, a field table (label, nominal, scenario range, provenance), the English n/a reasons (9.2), and "Differences from the served result" (section 8).
6. Footer: short `requestKey`, short research implementation hash, and cache hits of the last response.

Statuses use neutral colours for every value; no green approval colour, as the P8 spec requires.

### 4.3 States and transitions

States: `idle`, `running-nominal`, `band-pending`, `complete`, `cancelled`, `stale`, `error`.

1. **Run** is enabled only when every research input passes the client checks. Pressing it fixes the run identity (process subset, property context, options), increments the generation and sends the nominal stage.
2. On an accepted nominal response the panel shows the nominal values, shows "Computing scenario range: {armsDone} of {armsTotal}." with **Cancel**, and sends band requests one after another (each awaited) with budget 1500 ms until `complete`.
3. **Cancel** increments the generation, aborts the in-flight fetch and stops the loop; the state becomes `cancelled`. The nominal values stay, because they belong to the same identity. The band area reads "Scenario range not computed (cancelled). Run research models to compute it." No message is sent to the server.
4. Any change of a run-identity input (host process subset, property context, options, preset, ranges) increments the generation, aborts, stops the loop and hides every research value at once (state `stale`): "Inputs changed. Run research models to update." An old nominal or band is never shown beside new inputs.
5. A response is applied only when the generation matches, `clientRequestId` equals the one sent and, for band responses, `requestKey` equals the nominal response's `requestKey`.
6. Debounce: text inputs are checked client-side 300 ms after the last keystroke, for inline messages only (the 9.3 rules mirrored). Typing never sends a request; Python repeats every check.
7. Errors are panel-local, worded from the registry (9.2), with **Retry**.
8. Unmount cancels.

### 4.4 Cancellation and timing guarantees

1. The screen reacts to Cancel immediately.
2. After a cancel at most one research request is still in flight, because the loop is sequential. It ends within its budget plus one arm; its arm records stay cached for the next run.
3. The next run's nominal request waits in the lane behind that one request at most.
4. In ad-hoc mode there is no persistent cache, so the band stage runs as one request (3.5 rule 6) and a cancel discards its result.
5. Per-arm times are not promised here; phase C measures them (P-7) and confirms or adjusts the default budget and the arm cap (dependency D-12).

### 4.5 State ownership (gate item 13)

New session store `src/store/useLpbfResearchModelStore.ts`. It holds the research options (shared by both hosts, so a coefficient set once applies in both labs), the per-host run state, and a bounded client result map (8 entries, keyed by the canonical request) so that switching labs with the same inputs shows a finished result without a rerun. It holds no process values: the Melt Pool host passes its local process state (the values sent at `MeltPool3DCrossSectionLab.tsx:164-175`); the Build Job host passes `specimen.lpbf`, `job.alloyId` and `job.materialPropertySha256`, with `laserWavelength` fixed to IR as in `useLpbfBuildJobStore.ts:109`.

Nothing research-related is written to `useLpbfBuildJobStore`. Unchanged: the `buildJobKey` payload, `evidenceKey` and `key` (`useLpbfBuildJobStore.ts:98-137`), `sameEvidence` (`:252-255`), the failure fallback (`:280`), `aligned` (`:307`), and the exports that read `build.job` (`src/components/LpbfEngineeringWorkspace.tsx:60` and `:117`, `src/components/EvidenceWorkspace.tsx:28`). R-UI-10 pins that research option edits, runs, failures and cancels leave `peekLpbfBuildJobKey()`, `lastKey`, `sessionEvidenceKey`, `job` and `aligned` unchanged and the exported JSON byte-identical. Research results are not added to the qualification, run-report or evidence exports in v1.

### 4.6 Served-result identity for the difference statements

The Melt Pool lab records, next to `setPyResult(res)` (`MeltPool3DCrossSectionLab.tsx:180`), the signature of the inputs that produced `pyResult` (material, P, v, d, T0, wavelength, heat source) in a ref. The panel substitutes served numbers into a difference statement only when that signature's research subset equals the panel's run identity; otherwise it renders the statement's fallback text. The Build Job host reads `job.thermal`, aligned by construction. This ref write is the only edit inside the live re-solve callback; it sends nothing.

### 4.7 Band caption and display rules (UI part of item 6)

Exact strings, pinned by R-UI-5:

| Situation | Text |
|---|---|
| Under every numeric band | Amendment 2 B3 sentence, verbatim: "Min / nominal / max is an envelope of named one-at-a-time scenarios. Interactions are not evaluated. It is not a confidence interval, an error bar, or a physical lower or upper bound." followed by "{n} named scenarios." |
| Degenerate echo band (min = nominal = max for an input echo) | "Unchanged in every declared scenario; this is not a known zero uncertainty." (B3) |
| Extremes | "Lowest: {minArmLabel}. Highest: {maxArmLabel}." Each arm label is followed by its provenance label, phase and reference temperature (6.3), so a transferred or unsourced extreme (B3: `absorptance_0.14`, `srv`) is visible as such. |
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
| cavity | keyholeCavity and meltDepthLink | nominal, absorptance, property tuples, vapour-source scenarios (including the O8 Mg-inclusive arm for AlSi10Mg, B7), onset-criterion arms (O1 to O3, each carrying its event, B3), process ±5% arms. Never a user Marangoni or surface endpoint and never a flow-only assumption arm. |
| marangoni | marangoni | every declared arm, deduplicated on the Marangoni input tuple, plus the flow-only assumption arms of B3 and user Marangoni endpoints. In a Belton mode no direct-slope endpoint enters (B8). |
| surfaceBalance | surfaceBalance | every declared arm, deduplicated on the surface input tuple, plus user surface endpoints |
| o8 | alSi10MgVapourMgAware | its own composition, route, enthalpy and boiling-constant arms (B7); never counted in cavity onset support |
| none | alSi10MgIndexDisclosure, unavailablePhysics | no band |

The declared arm lists per alloy, with sources and labels, are physics and come from Amendment 2 and its fixture. At 200 W the fixture has, after this deduplication, Ti-6Al-4V 21 cavity/link arms (onset support 20 of 21), 17 Marangoni and 19 surface arms; AlSi10Mg 26 (22 of 26), 13 and 24 (Amendment 2 section 9.1). This contract fixes how manifests are built, keyed and counted.

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
  onsetEvent: string | null;   // "recoil-inception" for the default; the O1, O2, O3 event names otherwise (B3)
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

1. The onset statement and its `statusSupport` counts appear only in `keyholeCavity.band`. meltDepthLink shows "Scenario support: see Conditional cavity estimate". The denominator n is the cavity manifest size after deduplication.
2. Marangoni and surfaceBalance `validRange` values of P/P* and scan Pe, and the B2 onset-mismatch comparison (7.2), are read from the cavity record of the same armId when that id is in the cavity manifest (the same coherent thermal and vapour tuple, as B2 requires), else from the cavity nominal, and the per-arm note says which. These reads add no arms to the reading module and enter its cache key only as the referenced cavity arm key.
3. Arm cap: 80 per module manifest after deduplication. Above it that module alone is unavailable with `RESEARCH_ARM_LIMIT_EXCEEDED`. With the currently admitted range keys the cap is unreachable (gate minor 17); R-MAN tests it with an injected declared-arm table.

## 6. Provenance vocabulary (gate item 14)

### 6.1 Leaf roles

Every `ResearchField` gains `leafRole`. `evidenceKind` takes values from the RULES.md vocabulary only, chosen by role:

| leafRole | Meaning | evidenceKind | Provenance label shown |
|---|---|---|---|
| `requestInput` | echo of a process request value | "Unresolved" | "request input" |
| `sourcedConstant` | constant with a located source | "Literature estimate" | "sourced default" |
| `sourceModelAssumption` | assumption stated in a located source's model (accommodation 1, beta 0.2, recoil fraction 0.6) | "Literature estimate" | "source model assumption" |
| `declaredAssumption` | assumption without a located source (deltaT 500 K, L = d, Tref rule, emissivity 0.35) | "Unresolved" | "declared assumption (no source)" |
| `legacyEstimate` | served legacy number without a located source (viscosity 0.0013, the served Ti slope -2.8e-4, former served blends) | "Unresolved" | "legacy estimate (no located source)" |
| `userInput` | value typed by the user | "Unresolved" | "user input" |
| `softwareLimit` | computational policy bound (Pe 0.01 to 10, R_bound 10, scan sizes, tolerances) | "Unresolved" | "software limit (not a physical cutoff)" |
| `convention` | enum or identifier naming a convention (`decision`, `classificationChanged`, `selectedBranch`, `observable`, `floorFieldModelId`, `floorExtractorId`, `conductionMeltState`, `slopeBaseline`, `evaporationConvention`, `pressureRoute`, `calculationStatus`, `evaluationLocation`) | null | none |
| `derived` | computed output | rule 6.2 | "research result" |

`moduleMaturity`, `experimentalValidation: false`, `uiSentence` and the status string `validationStatus` stay on every leaf, as in the P8 spec section 2. Amendment 2 made the status module-specific: every populated surfaceBalance diagnostic and its band carry the B2 falsified-closure status; the other modules keep the data-unavailable status. The engineering constraint is that each status names a shipped document (this branch's spec or the pinned P6 derivation), never `.orchestra/GOAL.md` (gitignored, gate 4(e)); R-CODE checks the strings.

### 6.2 Evidence kind of derived leaves (maintainer label decision M-1)

Proposed rule: a derived leaf is "Literature estimate" when every non-request input in its module tuple (5.2) is `sourcedConstant` or `sourceModelAssumption`; otherwise it is "Unresolved" and the structural list `weakestInputs` names the inputs that caused it. The alternative, "Literature estimate" on every derived leaf as A1 states, is the maintainer's choice. The schema carries both; the tests pin the chosen one.

### 6.3 Input provenance (replaces the A1 `ResearchInputProvenance`)

```ts
type ResearchInputProvenance = {
  kind: "sourceDefault" | "sourceModelAssumption" | "declaredAssumption" | "legacyEstimate" | "userInput" | "followsInput";
  label: string;                       // the label column of 6.1, or "follows {input label}"
  sourceLocator: string | null;        // structural text, not a ResearchField; null for userInput and declaredAssumption
  defaultValue: number | string | null;  // what Reset restores; null when there is no default
  defaultKind: "sourceDefault" | "sourceModelAssumption" | "declaredAssumption" | null;
  followsInput: "beamDiameter_m" | "deltaTemperature_K" | "referenceTemperature_K" | null;
  followState: "following" | "user-fixed" | null;
  phase: "solid" | "liquid" | "solid-liquid-mean" | "vapour" | "process" | null;   // B3, B9 (1)
  referenceTemperature_K: number | null;   // evaluation or reference temperature of a property value
  sourceRange_K: [number, number] | null;  // the source's own temperature range, when one is stated
};
```

Rules:

1. `sourceLocator` is plain structural text. One record can no longer read "user input" and "Literature estimate" at once (gate 14(a)).
2. A value that follows another input (length from d, Tref from deltaT, Al viscosity from Tref) has kind `followsInput` while it follows; `defaultKind` gives the kind of the rule itself (for example `declaredAssumption` for L = d). Typing a value switches it to `userInput` with `followState: "user-fixed"` until reset.
3. Reset button text by `defaultKind`: "Reset to sourced default", "Reset to source model assumption", "Reset to declared assumption", or "Clear (input required)" when null. A legacy estimate is never a default; it is offered only as an explicit scenario. No control without a sourced default shows "Reset to sourced default".
4. Every output's input summary lists the kinds of its inputs; any `userInput` shows "user input" beside the output.

Host ceiling (maintainer decision M-2): the `3d-distortion-lab` registry contract is legacy, with `emits: []` and ceiling `screening-only` (`src/generated/moduleRegistry.json`; `PENDING_ORACLE_CEILING` at `python/module_contract.py:58`). `module_contract.py:48-52` already records the order of literature-estimate and screening-only as an open maintainer item. The research operation registers under that contract without an `emits` declaration, which matches its legacy state. Whether research leaves may say "Literature estimate" under a screening-only host ceiling is left to the maintainer; this contract does not edit the registry evidence statement.

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
| `roots[].stability` | `rootRelaxation` (values unchanged) | "Scalar root relaxation (not keyhole stability)" |
| `selectedBranch` value `lowest-strictly-stable` | value unchanged | "Lowest root that relaxes back (branch convention)" |
| `keyholeCavity.peclet` | unchanged | "Pe = v d / (2 alpha), research diffusivity" |
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
| meltDepthLink | `conductionMeltState` | convention, 1 | `resolved-melting` or `resolved-no-melting`; a resolved no-melting floor is exactly 0 um; an extraction failure is null with `CONDUCTION_EXTENT_UNRESOLVED` (B5) |
| meltDepthLink | `wallConductionPower_W` | derived, W | K (Tv-T0) g e, the wall balance that sizes e (B6) |
| meltDepthLink | `wallToSplitCavityPowerRatio` | derived, 1 | `wallConductionPower_W / cavityPower_W`; null with `NOT_APPLICABLE_BELOW_ONSET` at e = 0 (B6) |
| keyholeCavity, meltDepthLink, surfaceBalance notes | `onsetMismatch` | structural object of derived ResearchFields | `thresholdTemperature_K`, `surfaceTemperatureAtOnsetPower_K`, `surfaceRecoilAtOnsetPower_Pa`, `surfacePowerToReachThreshold_W`, `surfacePowerToReachThresholdOverOnset`, plus structural `comparison`: `matching-tuple`, `event-mismatch` or `unavailable`, with `reasonCode`. Always present; values null with their cause when the comparison is missing or event-mismatched (B2) |
| marangoni | `slopeBaseline` | convention, 1 | `alloy-direct` or `fe-clean-analogue` (B8) |
| surfaceBalance | `evaporationConvention` | convention, 1 | `accommodation-and-beta` (default) or `net-factor` (B3) |
| surfaceBalance | `netEvaporationFactor` | input echo, 1 | the net factor in `net-factor` convention (for example 0.82); null with `NOT_APPLICABLE_FOR_CONVENTION` otherwise |
| every consistency note | `validRange.temperatureRanges` (replaces `temperature_K`, `temperatureMin_K`, `temperatureMax_K`) | list of `{property, phase, referenceTemperature_K, sourceRange_K, status}` | one entry per property with a stated source range, so liquid-phase properties are never judged by one aggregate flag (B3 last paragraph, gate 7) |

`onsetMismatch` carries the B2 unconditional statement in the note's assumptions, not as the primary sentence (9.2).

## 8. Difference statements (gate item 18)

Python authors the templates in `lpbf_research_codes.py`. Each relevant container carries a structural list `servedDifferences`:

```ts
type ServedDifference = {
  id: string;
  servedPaths: string[];    // paths into the served thermal result (PythonLPBFResult)
  researchPaths: string[];  // paths into researchModels
  showWhen: "always" | "served-null" | "served-number" | "research-positive" | "alloy-alsi10mg";
  template: string;         // placeholders {served:<path>}, {research:<path>}, {servedKernel}
  fallback: string;         // text used when the served result for these inputs is not loaded
};
```

Path notation: a served path is a dotted path from the root of the served thermal result (`job.thermal` in the Build Job host); a research path `<container>.<field>` names `researchModels.<container>.fields.<field>`. TypeScript substitutes values (4 significant digits) only when the served identity matches (4.6) and evaluates `showWhen` from this closed list; otherwise it renders `fallback`. Statements appear only under "Differences from the served result" in the research section, never in served tiles. Rows D1 and D2 follow the Amendment 2 B2 status; the physics phrasing of D1, D4 and D8 is open to the lead's wording check (D-10); the ids, paths and conditions are this contract.

| Id | Served path | Research path | Show when | Template |
|---|---|---|---|---|
| D1 | `hydrodynamicsAndRecoil.peakTemperature_C`, `peakUnavailableReason` | `surfaceBalance.lossFreeCenterTemperature_K` | served-null | "The served peak temperature is withheld: {served:hydrodynamicsAndRecoil.peakUnavailableReason}. The research loss-free centre temperature ({research:surfaceBalance.lossFreeCenterTemperature_K} K) is a loss-free intermediate of the same kind, shown only as an input to the flat surface balance; it is not a surface temperature estimate." |
| D2 | `hydrodynamicsAndRecoil.knudsenRecoilPressure_kPa`, `recoilPressureUnavailableReason` | `surfaceBalance.beamCenterRecoilPressure_Pa` | served-null | "The served recoil pressure is unavailable: {served:hydrodynamicsAndRecoil.recoilPressureUnavailableReason}. The research beam-centre recoil pressure is an artefact of a falsified flat surface closure (Amendment 2 B2), shown only as a mathematical diagnostic; it does not replace the served refusal." |
| D3 | `marangoniModel.surfaceVelocity_m_s`, `marangoniModel.dGamma_dT_N_mK` | `marangoni.surfaceVelocityScale_m_s`, `marangoni.surfaceTensionSlope_N_mK` | always | "The served Marangoni block uses slope {served:marangoniModel.dGamma_dT_N_mK} N/(m K); its velocity is {served:marangoniModel.surfaceVelocity_m_s} m/s or unavailable. The research velocity scale uses slope {research:marangoni.surfaceTensionSlope_N_mK} N/(m K). They are separate models and are not reconciled." |
| D4 | `meltPoolGeometry.regime`, `keyholeModel.fabbroDepth_um` | `keyholeCavity.cavityDepth_um`, `keyholeCavity.onsetPower_W` | always | "The served regime label ({served:meltPoolGeometry.regime}) comes from the normalised-enthalpy index, and the served Fabbro keyhole depth is {served:keyholeModel.fabbroDepth_um} um. The research cavity depth ({research:keyholeCavity.cavityDepth_um} um) uses a different onset (P* = {research:keyholeCavity.onsetPower_W} W) and property tuple; it changes neither the served regime nor the verdict." |
| D5 | `hydrodynamicsAndRecoil.vaporTemperatureUnavailableReason` | `keyholeCavity.vapourSource` | alloy-alsi10mg | "The served model uses no elemental vapour proxy for AlSi10Mg ({served:hydrodynamicsAndRecoil.vaporTemperatureUnavailableReason}). This research model uses a pure-aluminium vapour proxy by explicit choice; the served refusal stands." (served text: `python/lpbf_thermal_solver.py:582-583`; ledger `python/four_alloy_materials.py:510-511`) |
| D6 | `keyholeModel.peclet` | `keyholeCavity.peclet`, `keyholeCavity.diffusivity_m2_s` | always | "Both use Pe = v d / (2 alpha). The served keyhole Pe ({served:keyholeModel.peclet}) uses the room-temperature solid diffusivity; the research Pe ({research:keyholeCavity.peclet}) uses the research Kirchhoff-mean diffusivity {research:keyholeCavity.diffusivity_m2_s} m2/s." (served definition: `python/fabbro_keyhole.py:55`) |
| D7 | `meltPoolGeometry.aspectRatio_L_over_W`, `keyholeModel.aspectRatio_e_over_d` | `keyholeCavity.aspectRatio_e_over_d` | always | "Research e/d is cavity depth over beam diameter. The served aspect ratio tile is melt-pool length over width, a different quantity. The served Fabbro e/d is {served:keyholeModel.aspectRatio_e_over_d}." |
| D8 | `meltPoolGeometry.depth_um` | `meltDepthLink.linkedMeltDepth_um` | always | "The served melt-pool depth ({served:meltPoolGeometry.depth_um} um, {servedKernel} kernel) and the research linked melt depth ({research:meltDepthLink.linkedMeltDepth_um} um) are different models; the research value never replaces the served depth." |
| D9 | `meltPoolGeometry.keyholeVaporCavityDepth_um` | `keyholeCavity.cavityDepth_um` | always | "The served keyhole vapour cavity depth is the increment of the Fabbro leg over the conduction depth; the research cavity depth is measured from the original surface. The two numbers are not comparable." |
| D10 | `marangoniModel.sulfur_ppm` | `marangoni.solubleSulfur_ppm` | always | "The served sulfur slider ({served:marangoniModel.sulfur_ppm} ppm, Heiple-Roper screening) does not feed this research model. The research Fe-S analogue reads only the soluble sulfur entered here." |
| D11 | `processParameters.indexAbsorptivity`, `processParameters.effectiveAbsorptivity` | `alSi10MgIndexDisclosure.physicalToIndexRatio` | alloy-alsi10mg | "The served regime index uses absorptivity {served:processParameters.indexAbsorptivity}; the served field uses {served:processParameters.effectiveAbsorptivity}. The disclosure below explains the difference; no classification changes." |

Fallback for every row: the same sentence without numbers, ending "The served result for these inputs is not loaded."

The keyholeCavity `uiSentence` of the P8 spec section 2 table says the estimate uses "the served thermal properties", which reads as agreement (gate 18). Proposed replacement for the lead's wording check (D-10): "Conditional cavity estimate from the research property tuple; it can differ from the served keyhole leg (see the differences below)."

R-LINK-1 checks that every `servedPaths` entry resolves in a `calculate_meltpool_physics` result for Ti-6Al-4V and AlSi10Mg (200 W, 800 mm/s, 80 um, 20 C) in each served kernel, and that every `researchPaths` entry exists in the research schema.

## 9. Reason codes, refusal wording and option checks (gate item 20)

### 9.1 Classes and precedence

| Class | Scope | Meaning | Codes |
|---|---|---|---|
| C1 | request | request refused, no block | `RESEARCH_REQUEST_INVALID`, `PROPERTY_SNAPSHOT_MISMATCH`, `RESEARCH_CODE_STALE`, `RESEARCH_RESPONSE_TOO_LARGE`; client-side `RESEARCH_TIMEOUT` |
| C2 | request, module or arm | evaluator failure (a bug) | `RESEARCH_EVALUATION_FAILED`, `RESEARCH_SERIALIZATION_FAILED` |
| C3 | module | research option refused | `RESEARCH_OPTIONS_INVALID`, `RESEARCH_PRESET_ALLOY_MISMATCH`, `SURFACTANT_BINARY_COMBINATION_UNSUPPORTED`, `RESEARCH_ARM_LIMIT_EXCEEDED` |
| C4 | module | not admitted or not applicable | `ALLOY_CONSTANT_CHAIN_NOT_ADMITTED`, `ALLOY_NOT_ALSI10MG`, `UNSOURCED_PROPERTY_OVERRIDE` |
| C5 | module or leaf | outside a software or source range (policy refusal) | `INVALID_INPUT`, `PREHEAT_OUTSIDE_PROPERTY_SCOPE`, `WAVELENGTH_UNSUPPORTED`, `POWDER_CONTEXT_UNSUPPORTED`, `PECLET_OUTSIDE_NUMERICAL_SCOPE`, `ASPECT_BOUND_OUTSIDE_NUMERICAL_SCOPE`, `NUMERICAL_INPUT_BELOW_FLOOR`, `VAPOUR_PRESSURE_OUTSIDE_SOURCE_RANGE` |
| C6 | module or leaf | input required | `SURFACE_VAPOUR_INPUT_REQUIRED`, `MARANGONI_VISCOSITY_INPUT_REQUIRED`, `MARANGONI_SOLUTE_INPUT_REQUIRED` (new), `ONSET_REFERENCE_UNAVAILABLE` |
| C7 | leaf | upstream, branch or convention state | `MELT_LINK_NOT_AVAILABLE`, `NOT_APPLICABLE_BELOW_ONSET`, `NOT_APPLICABLE_FOR_CONVENTION` (new), `ONSET_COMPARISON_EVENT_MISMATCH` (new, B2) |
| C8 | leaf or arm | numerical acceptance rule not met | `CYLINDER_CONVERGENCE_FAILED`, `OPTICAL_TRACE_UNRESOLVED`, `CAVITY_ROOT_SCAN_UNRESOLVED`, `CAVITY_RESIDUAL_FAILED`, `NO_STRICTLY_STABLE_ROOT`, `CONDUCTION_EXTENT_UNRESOLVED`, `MELT_BRACKET_FAILURE`, `MELT_OPTIMIZER_FAILURE`, `MELT_CONVERGENCE_FAILED`, `TIP_SHELL_UNRESOLVED`, `SURFACE_BALANCE_NO_BRACKET`, `SURFACE_BALANCE_CONVERGENCE_FAILED`, `NONFINITE_RESULT` |
| C9 | leaf | closure not available (permanent) | `MARANGONI_SURFACE_CHEMISTRY_UNAVAILABLE`, `MARANGONI_TRANSPORT_CLOSURE_UNAVAILABLE`, `SURFACE_BALANCE_CLOSURE_FALSIFIED`, `POWDER_ALLOY_OPTICAL_CONSTANTS_UNAVAILABLE`, `POWDER_LOT_INPUTS_UNAVAILABLE`, `POWDER_THERMAL_OPERATOR_UNAVAILABLE`, `KEYHOLE_THERMAL_FLOW_CLOSURE_UNAVAILABLE`, `SOURCE_RANGE_NOT_ESTABLISHED` |
| C10 | band | band state | `BAND_PENDING` (new), `BAND_NO_SUCCESSFUL_ARM` (new) |
| W | leaf (value present) | warning, never a `reasonCode` | `LOW_PE_HYDRODYNAMICS_OMITTED`, `LOW_ASPECT_CAVITY_MECHANICS_OMITTED`, `THERMAL_CYLINDER_CLOSURE_EXTRAPOLATED` (new, B6: derived per arm from its own Pe and R), `VAPOUR_PRESSURE_EXTRAPOLATED`, `HKL_SUBBOILING_FIXED_BETA`, `VAPOUR_CONSTANT_LV_EXTREME_EXTRAPOLATION`, `USER_COEFFICIENT_PAIR_DECOUPLED`, `FE_ANALOGUE_BASELINE_SUBSTITUTED` (new, B8: on every Belton-mode output) |

Precedence: a null leaf carries the code of the lowest class number among its causes; inside one class, the first detected in the module's fixed evaluation order. Every cause, not only the winner, is listed in the new structural member `consistencyNote.reasons`:

```ts
type ResearchReason = {
  code: string; fieldPaths: string[];
  quantity: string | null; value: number | null;
  limitMin: number | null; limitMax: number | null;
  changeInputs: string[];   // request or option names the user can change
};
```

Request-level failures produce no block, so the `researchModels` root needs no `reasonCode` slot (gate 20(a), third point): the error envelope carries `reasonCode` and `problems`. A band with no successful arm has `BAND_NO_SUCCESSFUL_ARM`; a Belton mode with its ppm empty has `MARANGONI_SOLUTE_INPUT_REQUIRED` (gate 20(a), first and second points).

### 9.2 English n/a text per class

The short n/a cell text is built from the class template and the `ResearchReason` fields; each code also has a fixed noun phrase in the registry (for example `PECLET_OUTSIDE_NUMERICAL_SCOPE`: "Pe of the cavity solver"; `TIP_SHELL_UNRESOLVED`: "melt envelope near the cavity tip").

| Class | Template |
|---|---|
| C1 | "Research request refused: {problem messages}. The served result is not affected." |
| C2 | "The research evaluator failed for this model. The served result is not affected; details are in the local server log." |
| C3 | "Research inputs for this model were refused: {problem messages}. Other research models are unaffected." |
| C4 | "Not computed: {phrase} for {alloy}. No value is borrowed from another alloy." |
| C5 | "Not computed: {quantity} = {value} is outside the {software range or source range} {limitMin} to {limitMax}. This is a {software limit or source limit}, not a physical cutoff. Change {changeInputs} to evaluate it." |
| C6 | "Not computed: {phrase} is required and has no sourced default for {alloy}." |
| C7 | "Not available: {phrase}." |
| C8 | "Not computed: the {phrase} did not meet its numerical acceptance rule. No clipped or fallback value is shown." |
| C9 | "Not available: {phrase}." |
| C10 | the pending and unavailable captions of 4.7 |

Each C5 code declares whether its limit is a software limit (Pe 0.01 to 10, aspect bound, numerical floors) or a source limit (property scope, vapour source range). This splits the single "hard failure" sentence of A5 (gate 20(c)). The Pe policy stays 0.01 to 10, a computational limit separate from any physical range (Amendment 2 B6).

Primary consistency sentence eligibility per module (gate 20(d)). Sentence texts are Astra's: A5 as replaced by Amendment 2 (falsified surface closure, B2; below onset, B5; O8 scenario, B7; Fe-mode help, B8). The eligibility is this contract:

| Module or note | Eligible primary sentences, in precedence order |
|---|---|
| keyholeCavity, meltDepthLink (module note) | class sentence of the winning C1 to C8 cause; below onset (B5); low Pe; inside range |
| keyholeCavity, meltDepthLink, surfaceBalance (per-arm note of an O8 arm) | class sentence; O8 scenario (B7); then the module's own list |
| marangoni | class sentence; Marangoni transfer; inside range. Never low Pe or O8. |
| surfaceBalance (module note) | class sentence; falsified surface closure (B2); O8 scenario (only for preset `o8-mg-inclusive`); inside range |
| alSi10MgVapourMgAware | class sentence; O8 scenario (B7) |

The B2 unconditional onset-mismatch statement and the B6 two-ledger statement are always listed in the assumptions of the cavity, link and surface notes; they never compete for the primary slot.

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
| `HTTP_GOLDEN` digests (`python/test_lpbf_calibration_frozen.py:55-59`) | unchanged; the frozen-file diff guard T-FRZ-3 (`:95-120`) stays green on this branch |
| `BUILD_JOB_SOLVER_REVISION` v25, `lpbf_job_cache.build_cache_key`, job, input and material hashes, verdict | unchanged |
| Error bands, demo snapshots, leaderboard, `DEPTH_BIAS_BANDS_ID`, stored machine calibrations | bound to the unchanged fingerprint; nothing goes stale (gate minor 13 does not arise) |
| Legacy broad cache hash (`python/lpbf_simulation.py:269-281`, used for worker job keys at `python/lpbf_worker.py:949`) | changes, because it hashes every `python/*.py` and new files are added. Previously cached build-job and GPU-pilot worker jobs are recomputed once on their next request. No served value changes. Already noted in `python/tools/lpbf_bump_record.py:187-188`. |

### 10.2 Parity case list (served side; zero edits to pins, goldens and allowlists)

| Id | Check |
|---|---|
| P-1 | Fingerprint equals the pin: T-FRZ-1 (`test_lpbf_calibration_frozen.py:69-71`) and `python/test_lpbf_implementation_fingerprint_pin.py`. |
| P-2 | Diff against the merge-base with main contains no manifest file (T-FRZ-3) and none of the served entry modules: `lpbf_build_job_solver.py`, `lpbf_build_job_material_snapshot.py`, `lpbf_build_job_schema.py`, `lpbf_job_cache.py`, `lpbf_worker.py`, `lpbf_process_window.py`, `lpbf_bayesian_optimizer.py`, `lpbf_screening_uq.py`, `lpbf_gr_solidification.py`, `lpbf_solidification_microstructure.py`, `lpbf_calibrated_meltpool.py`, `lpbf_calibration_layer.py`, `lpbf_machine_calibrated_meltpool.py`, `lpbf_machine_calibration.py`, `src/store/useLpbfBuildJobStore.ts`, `src/utils/lpbfBuildJobIdentity.ts` (R-ISO-2). |
| P-3 | T-HTTP-1 digests unchanged for the 316L input in all three kernels (Windows reference machine): eagar-tsai `84e7cdd8c0018053046a4488d8ca3a949f3aed89c9c97577e9149bb947d9ecf6`, goldak `4e898835200d22ec154a0b2a00c530d137a3bf7857a3ef840b8b51c530d6ee4b`, rosenthal `e74869355304712d9d5ff9804e7bd6149dd5035f54ba4762b62350972523ae09`. |
| P-4 | `python python/tools/lpbf_parity_check.py --check` and `--check --slow`: zero drift. |
| P-5 | In one Python process: canonical served thermal JSON (without `computeTimeMs`) for Ti-6Al-4V, AlSi10Mg, Inconel 718, 316L and Inconel 625, three kernels, P 100, 200 and 400 W, v 800 mm/s, d 80 um, T0 20 C, before and after a complete research band for the same inputs: equal. This proves no shared mutable state leaks even when research runs in the same process (tests, ad-hoc use). |
| P-6 | Build Job payload for the four Build Job alloys (UQ off) before and after a research run: equal, including `solverRevision`, `buildJobIdentity`, `materialPropertySha256` and `verdict`. |
| P-7 | Measured and recorded, not promised: served thermal route p50 and p95 over 50 calls without research and with a concurrent research band loop; served `queueWaitMs`; research per-arm p50, p95 and max per module; nominal stage cold and warm; full band cold and warm for the default manifests and at the per-module cap. Acceptance: no served request waits in a research queue; any CPU-contention effect is reported, not hidden. |
| P-8 | IPC: a research run timeout leaves the shared pool generation unchanged; `METALLIX_IPC_AFFINITY=0` still isolates research; the research lane is not prestarted; a research payload with an `action` key never reaches the shared pool. |

### 10.3 Test plan

All tests are self-contained: they carry their own inputs and pinned literals, import no measured data and invoke no registered runner.

Python (new files):

| File | Tests |
|---|---|
| `python/test_lpbf_research_isolation.py` | R-ISO-1 AST import guard over `python/**/*.py`: importers of `lpbf_research_*` are only research modules and `test_lpbf_research_*`; research modules never reference `calculate_meltpool_physics`; no research file is in `IMPLEMENTATION_SOURCE_FILES`. R-ISO-2 the P-2 diff guard, including the 150-character route-block rule of `test_lpbf_calibration_frozen.py:113-120`. R-ISO-3 lane configuration in a subprocess with `METALLIX_IPC_AFFINITY=0` and unset. |
| `python/test_lpbf_research_context.py` | R-CTX-1 the 3.8 tuple literals for Ti-6Al-4V and AlSi10Mg at 20 C. R-CTX-2 equality with served internals: `unittest.mock.patch.object(lpbf_thermal_solver, "resolve_conduction_kernel", wraps=...)` during `calculate_meltpool_physics` for five alloys and three kernels, float.hex of K, cp, rho_k and alpha compared with the research context. R-CTX-3 build-job snapshot equals nominal for the four Build Job alloys; a tampered hash gives `PROPERTY_SNAPSHOT_MISMATCH`; a wrong alloy gives `alloy-material-mismatch`. R-CTX-4 SI conversions by float.hex: 800 mm/s to 0.8, 80 um to 8e-05, 20 C to 293.15. |
| `python/test_lpbf_research_transport.py` (injected deterministic fake evaluator, no physics) | R-TR-1 request-check table: each rule with code, pointer, rule and limit (for example laserPower_W 0 gives `RESEARCH_REQUEST_INVALID`, `/process/laserPower_W`, `not-positive`); booleans refused as numbers. R-TR-2 emissivity 1.2 makes surfaceBalance unavailable with `{pointer "/researchOptions/surfaceBalance/emissivity", rule "above-max", limit 1}` while the other six containers are byte-identical to a run without it. R-TR-3 stage protocol: pending bands; strictly increasing `armsDone`; the complete block equals a `timeBudgetMs: null` run; `researchModels` null while incomplete. R-TR-4 cache: cold equals warm byte for byte; a surface-only option change leaves cavity, link and Marangoni arm keys unchanged; the 257th insert evicts the oldest; size eviction with synthetic large entries; transient failures not cached, deterministic failures cached. R-TR-5 NaN and infinity from the fake evaluator in a value, a band and a note become null with `NONFINITE_RESULT`, and a strict parser reads the output. R-TR-6 nominal values identical across stages. R-TR-7 an exception in one arm gives a failed arm with `RESEARCH_EVALUATION_FAILED`; an exception in one module's assembly leaves the other six containers. R-TR-8 a patched on-disk hash gives `RESEARCH_CODE_STALE`. R-TR-9 key sensitivity: every process field, property context, option, follow flag and identity hash changes `requestKey`. R-TR-10 a synthetic oversize block gives `RESEARCH_RESPONSE_TOO_LARGE`. R-TR-11 the CLI output for a fixed request equals the committed fixture `tests/fixtures/lpbf-research-response-v1.json` (regenerated only by a deliberate commit). |
| `python/test_persistent_ipc_research_lane.py` | R-IPC with the existing thread-pool factory pattern of `_AffinityLane` tests: run timeout recycles only the research lane; a queued research request is superseded; no prestart; the metadata guard. |
| `python/test_lpbf_research_manifest.py` | R-MAN: per-module deduplication (a power arm aliases the Marangoni nominal), sourceId distinctness, user endpoint ids and order, `minArmTies`, the per-module cap with an injected table, onset support only in keyholeCavity with the cavity denominator. |
| `python/test_lpbf_research_codes.py` | R-CODE: every code a research module emits is in the registry; every entry has class, scope and English text without em or en dashes; warnings never appear as `reasonCode`; a pinned precedence table (for example C5 `PECLET_OUTSIDE_NUMERICAL_SCOPE` with C8 `NONFINITE_RESULT` resolves to the C5 code); every emitted field path has a label. |
| `python/test_lpbf_research_links.py` | R-LINK-1 (section 8). |
| `python/test_lpbf_research_identity.py` | R-ID-1 pin equality. |
| `python/test_lpbf_research_arm.py` | Astra's physics contract (phase C): replay of the committed fixture `docs/research/scripts/p8_amendment1_synthetic.json` (`p8-research-synthetic-v2`): per-arm input tuples, root arrays and counts, selected branch and depth, categorical support, extrema-generating ids, onset pins (Ti 31.363133215875212 W, Al 157.1067664028826 W at 200 W, v 0.8 m/s, d 80 um, T0 293.15 K), with the fixture's own field-specific tolerances, plus the B4 executed checks. The test reads the fixture as data; the runtime does not. |

TypeScript (new files):

| File | Tests |
|---|---|
| `tests/lpbf-research-transport.test.ts` | the exact request body; abort; stale rejection by generation, `clientRequestId` and `requestKey`; fallback to `timeBudgetMs: null` on a changed `cacheInstanceId` or stalled `armsDone`; superseded envelope ignored; 422 problems surfaced; 500 with exit 124 shown as `RESEARCH_TIMEOUT`; 413 for an oversize body (route test with `physicsDeps`, `routes/physics.ts:9`). |
| `tests/lpbf-research-model-panel.test.tsx` | header "Research model"; collapsed by default; research values only inside the panel; no request on mount or on input edits (R-UI-9); stale hiding; nominal, pending and complete states; Cancel; the 4.7 captions (R-UI-5); the banned-string scan (R-UI-6); labels from the response map and the served-label list (R-UI-7); difference statements with matching served identity and fallback otherwise; static demo text; keyboard access to every input, help, reset, Run and Cancel; reset button text per `defaultKind`. |
| `tests/lpbf-build-job-research-isolation.test.ts` | R-UI-10 (4.5). |
| `tests/lpbf-research-schema.test.ts` | the TypeScript response guard accepts the R-TR-11 fixture and rejects unknown keys and a wrong `schemaVersion`. |

Existing suites that must pass without edits: `python/test_lpbf_calibration_frozen.py`, `python/test_lpbf_implementation_fingerprint.py`, `python/test_lpbf_implementation_fingerprint_pin.py`, `python/test_phase6a_leaf_modules.py`, `python/test_lpbf_parity_golden.py`, `python/test_module_warm_parity.py`; with the new route literal `python/test_persistent_ipc_security.py`, `tests/persistent-ipc-auth.test.ts`, `tests/route-authority.test.ts` and `tests/module-registry.test.ts`; `tests/component-reachability.test.ts`, `tests/demo-snapshots.test.ts`, `npm run lint`, `npm run lint:eslint`, `npm run check:bundle` (the panel is lazy-loaded if the budget requires it).

## 11. Implementation phases

| Phase | Owner | Work | Acceptance |
|---|---|---|---|
| A | lead | Re-gate this contract with Amendment 2. | Verdict; D-2, D-4, D-10 and D-12 closed or explicitly deferred; M-1 and M-2 recorded. |
| B | Opus | Isolation and transport core: `lpbf_research_models.py`, `lpbf_research_context.py`, `lpbf_research_cache.py`, the registry skeleton of `lpbf_research_codes.py`, the research pin, the `persistent_ipc_service.py` lane edits, the fake-evaluator harness. | R-ISO, R-CTX, R-TR, R-IPC and R-ID pass; P-1 to P-4 pass unchanged; the R-TR-11 fixture is committed; the per-request cost of the code-stale check is recorded. |
| C | Opus, numerics reviewed by Astra | Physics evaluator `lpbf_research_arm.py` and `lpbf_research_manifest.py` per Amendment 2, ported (not imported) from `docs/research/scripts/p8_cavity_kernel.py` and the synthetic script; full codes, labels and difference templates. | `test_lpbf_research_arm.py` replays the Amendment 2 fixture within its stated tolerances, including the 200 W manifest counts of 5.1; R-MAN, R-CODE and R-LINK pass; per-arm timings, manifest sizes and response sizes recorded (P-7, research part); budget and cap confirmed or changed by measurement (D-12). |
| D | Sonnet | Route, registry operation and regenerated registry, `DISPATCHABLE_SCRIPTS`, `pythonComputationService.solveLpbfResearchModels`, `src/types/lpbfResearchModels.ts` with its guard. | Transport and schema TS tests, persistent-ipc-auth, route-authority, module-registry, `test_persistent_ipc_security.py`, `npm run lint`. |
| E | Sonnet; Opus reviews the state machine | `ResearchModelPanel.tsx`, `useLpbfResearchModelStore.ts`, the two host mounts, the served-signature ref. | Panel and isolation tests; `npm run check:bundle`; a browser check of both panels under `npm run dev` (run, pending, complete, cancel, stale on input change; served tiles, verdict and exports unchanged), screenshots in the report. |
| F | Haiku | Chores: a distinct `P8-RA` evidence entry in `PROOF.md` (Amendment 2 naming; no collision with "P8 fresh UI archive acceptance" at `PROOF.md:3083`, gate minor 12) recording the actual runtime, parity and test checks and their limits; a short research-route note in `docs/LPBF_ENGINEERING.md`; review of `scripts/ci-unit-tests.txt` (LF); confirmation that `scripts/demo/` is unchanged. | Documentation diff only; lint passes. |
| G | Opus | Integration check and report. | P-1 to P-8; `npm run test:unit`; `npm run test:lpbf`; parity `--check --slow`; research suites; skips and failures named explicitly; local commits with explicit paths; no push. |

## 12. Open dependencies and maintainer decisions

Gate items already settled by Amendment 2 (`1c76a2fd`) and reflected above: item 1 (onset normalization, B1), item 8 and 10 (root scan rule and per-arm fixture records, B4), item 9 (independent Gaussian floor, B5; 3.8 and 7.2), item 16 (O8 band, note and Mg-aware sensitivity arms, B7; 5.1), item 21 (Fe-mode semantics, B8; 9.3 rule 7), items 5 and 15 (module-local declared arms with provenance, B3; section 5), and the Pe computational policy of 0.01 to 10 kept separate from any physical range (B6; 9.2 C5).

Items still open for the re-gate:

| Id | Gate item | Open point |
|---|---|---|
| D-2 | 14, 17 | One closed field list. The spec's sections 2, A2 and A3 still use the pre-contract names (`peakTemperatureProxy_K`, `recoilPressure_Pa` in two containers, `aspectRatio`, `stability`, `sulfur_ppm`, `oxygen_ppm`, `floorModelId`, the three null Marangoni corrections). Amendment 2 B9 assigns names to this contract, so sections 6 and 7 here govern; the re-gate confirms one list. |
| D-4 | 3, 7 | Confirm the same-armId rule of 5.5 for cross-module P/P*, Pe and the B2 onset-mismatch comparison, and the per-property `temperatureRanges` of 7.2. |
| D-10 | 4, 18, 19 | Lead wording check: the keyholeCavity `uiSentence` (still "using the served thermal properties" after Amendment 2; replacement proposed in section 8) and the physics phrasing of difference statements D1, D4 and D8. |
| D-12 | 2 | Default band budget (1500 ms), route timeout (30000 ms) and per-module cap (80), confirmed by phase C timings. |

Maintainer decisions (label wording):

| Id | Question |
|---|---|
| M-1 | Evidence kind of derived leaves: the 6.2 rule ("Unresolved" when any non-request input is unsourced or user-typed) or "Literature estimate" on every derived leaf as A1 states. |
| M-2 | Whether research leaves may carry "Literature estimate" under the screening-only evidence ceiling of the legacy `3d-distortion-lab` contract (`python/module_contract.py:48-58`). Amendment 2 B9 adds that an inspectable numeric artefact must not promote any evidence ceiling. |
