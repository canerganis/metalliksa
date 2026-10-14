# Solidification chain: integration contract

Record date: 2026-10-15. Owner: Opus system architect (architecture and hard integration code).
Branch `research/solidification-astra` at `3908a741` (base `main` `835466fa`). Served code locators below refer to `835466fa`; commits `e94934ea` and `3908a741` changed documentation and audit scripts only, so the locators hold at `3908a741`.
Status: proposed integration contract, **not implemented**. Companions: [physics specification](SPEC_solidification_2026-10-14.md) (with its Amendment 1) and [audit](AUDIT_solidification_chain_2026-10-14.md).

Scope: the Opus gate's required changes 4, 5 and 10 and the engineering parts of minor notes 9, 13, 14, 17, 18, 20 and 21 (`.orchestra/reports/solidification_gate_verdict_2026-10-15.md`), and the six items SPEC:240 asks of this contract, (a) to (f). Physics admission rules, coefficients and domains stay in the SPEC; this file decides representation, order, identities, consumers, tests and owners. Nothing in this file is evidence about physical accuracy, and no software check named here is a physical test.

## 1. Decisions

| ID | Decision | Section |
|---|---|---|
| D1 | Pin order on `36cd9d4a`: SOL-A1 first, then P8, then SOL-C. P3's keyhole-leg bump changes melt depth and therefore runs in its own later batch, never inside a batch whose bumps leave W/D unchanged. | 3.1, 3.2 |
| D2 | The error bands, `DEPTH_BIAS_BANDS_ID`, the demo snapshots and the dated comparison records leave the blind lanes. A separate records lane (R-lane) regenerates them once per batch, on the batch head, before the merge to `main`. No solidification lane opens a bands row, a dataset loader or the process-window overlay. | 3.6, 3.7 |
| D3 | W/D invariance is shown inside each bump lane without measured rows: the parity cases, a new synthetic 5 alloy x 3 kernel x 49 cell float.hex snapshot tool, and the HTTP digest guard's geometry. | 3.5 |
| D4 | The four legacy helpers in `solidification_front.py` are retired, not kept as parity-only code. G12 is rewritten in the same guarded commit, and the parity harness gains a rule that a recorded value turning into an `{"error": ...}` observation never passes under `--expect-drift`. | 6 |
| D5 | Quantity envelope v1 lives in a new stdlib-only `python/quantity_envelope.py` outside the thermal manifest. Operations declare their quantities in `module_contract.py`; the registry emits the declarations and vocabularies to TypeScript. Manifest files emit envelope literals and never import the module. | 4.1 |
| D6 | Per-quantity `evidenceKind` is capped by the module ceiling (`screening-only` today). Transcribed measurements are separate observation records. Maturity stays a module label. `PENDING_ORACLE_CEILING` does not change for this chain. | 4.3, 4.4 |
| D7 | One closed quantity status vocabulary: `computed`, `partial`, `unavailable`, `failed`, `not-requested`, with a mapping for every served status. | 4.5 |
| D8 | Reason codes: the 21 SPEC:34 codes plus four integration codes. | 4.6 |
| D9 | Migration is atomic per producer lane: SDK, producer, every consumer, Python-generated payload fixtures and TypeScript parsers merge together. No dual-read period; an old payload renders as an older solver result to recompute. | 4.8 |
| D10 | A model ID changes when served values change; a schema ID changes when the shape changes. `BUILD_JOB_SOLVER_REVISION` goes to v26 with SOL-A. CALPHAD gets a `solidificationChainIdentity` keyed on CRLF-normalised TDB bytes, with the raw sha256 kept as provenance. | 5 |
| D11 | CET source facts become three separate fields: `equationRead`, `algebraReproduced`, `printedLimitComparison`. | 4.7 |
| D12 | `gr-solidification` accepts the canonical alloy IDs of all five primary alloys and answers per quantity. An unknown alias is refused with `unknown-alloy-alias`. | 7.1 |

## 2. Code facts this plan rests on

1. The thermal implementation manifest has 36 files (`python/lpbf_simulation.py:44-81`), including `lpbf_thermal_solver.py` (:73) and `solidification_front.py` (:76). Any change to either moves pin `36cd9d4a` (`python/lpbf_implementation_fingerprint.expected:1`).
2. Solidification outputs reach the thermal result only through the `solidificationKinetics` block: `evaluate_solidification` is called at `lpbf_thermal_solver.py:1195-1204`, its values are read at :1211-1217 and written only at :1563-1591. Geometry is computed before that call and nothing in the block flows back. `compose_verdict` (`lpbf_build_job_solver.py:483`) does not read solidification, microstructure, segregation or kinetics. A change confined to the front therefore cannot move W, D, the enthalpy index, the regime label or the verdict.
3. Objects bound to the pin: the 25 goldens in `python/golden/lpbf_parity/` (`recordedImplementationHash`), `GOLDEN_FINGERPRINT` (`python/test_lpbf_parity_golden.py:60`), the three bands files `data/calibration/lpbf-meltpool-error-bands-v1{,.summary,.rows}.json`, `demo/snapshots/*` (`recordedWith.fingerprint`, `index.json`), and the dated records `docs/LPBF_*_2026-10-14_p7b-sourced-constants.*` and `docs/LPBF_LEADERBOARD_2026-10-14.json`.
4. CI-run checks bound to it: `tests/lpbf-error-bands.test.tsx:59-62` (summary hash equals the pin), `tests/demo-snapshots.test.ts:65-78` (snapshot fingerprints equal the pin), `tests/demo-gate.test.tsx:108-111` (snapshots equal the bands summary, not the pin), `tests/depth-bias-warning.test.tsx:13` (`DEPTH_BIAS_BANDS_ID`, `src/utils/depthBiasWarning.ts:19`, equals the summary `bandsId`), `python/test_lpbf_error_bands.py:316-321` (`load_bands` refuses a stale artefact), `python/test_lpbf_depth_bias.py:199` (Python twin of the bands ID), `python/test_lpbf_calibration_frozen.py:55-59` (HTTP digests) and :97-115 (frozen-file diff, red on any bump branch until merge).
5. The bands tool cannot restamp: `python/tools/lpbf_error_bands.py:292-297` refuses `--from-rows` when the row table carries another fingerprint, and the full run loads every measured depth row through the loaders (:69-101). The committed row table itself carries measured `width_um` and `depth_um` per row (:140-143), so even `--from-rows` reads measured depths.
6. Correction to gate item 4.5: re-recording the demo snapshots is not depth-free either. `demo/snapshots/index.json` includes `POST /api/python/lpbf-process-window` with `overlayBeamTolerance_pct`; that endpoint loads published single-track W/D rows (`python/lpbf_process_window.py:53-61`, :254, :286-287, :310), and snapshot `3609eb6351a5a4cf.json` holds the `ku-leuven-in718-2021` and `nist-amb2022-03-table4` overlays with status available.
7. Parity: G11 (`python/tools/lpbf_parity_check.py:1118-1146`) and G18 (:720-767) call `calculate_meltpool_physics` and record whole-result digests plus a `geometry_um` companion. G12 (:1148-1211) observes `hunt_morphology` (:1184-1185), `hunt_lu_pdas_um` (:1186-1187), `kirkwood_sdas_um` (:1188-1189), `phase_transformation_note` with display names (:1190-1193) and `evaluate_solidification` with the ignored legacy keywords (:1196-1201). `observe_value` stores a digest or `{"error": ...}` (:232-235), and `evaluate_drift` (:1754-1806) lets any matching entry accept a value that became an error. New honesty keys never pass (:1781-1782). The harness and goldens are guarded (`scripts/check_ceiling_review.py:39`, :44-47, :49, :54-55).
8. Every pin move makes stored user machine calibrations stale (`python/lpbf_machine_calibration.py:525-529`), invalidates the process-window LRU (`python/lpbf_process_window_cache.py:68`) and misses the transient job cache. The committed calibration layers v1 and v2 are already stale since `d92d1a3a` (`python/lpbf_calibration_layer.py:83-87`).
9. P8 also moves the pin: its hook goes into `lpbf_thermal_solver.py` and a new manifest file takes the count from 36 to 37 (`SPEC_p8_research_arm_2026-10-14.md` at `b6e68dfe`, lines 240 and 242). Its parity statement names base `835466fa` (:243, :248). P3's registered model shares P8's onset kernel (P8 gate, B1), and G2 is blocked by data (`.orchestra/BOARD.md`, 2026-10-14 status).
10. The SDK: `EVIDENCE_TYPES` (`python/module_contract.py:30-37`, mirrored at `src/types/research.ts:2`), run states (:40-45), rank order and the pending-oracle cap marked TODO maintainer review (:48-58), `MATURITY = ("Research", "Preview")` (:78), `within_ceiling` (:136-141), status-like top-level keys must be declared (:293-296), transport values may say `unavailable` only when the output has no status key (:332-335), a pending oracle caps the ceiling (:636-638). Both solidification-related contracts declare `emits=()` and the pending cap (`python/module_contracts_calphad.py:147-152`, `python/module_contracts_lpbf_secondary.py:37-45`); the gr response's `evidence` object rides outside the declared fields because the SDK reserves that name (`module_contracts_lpbf_secondary.py:243-247`, pinned by `python/test_module_contract_solidification_microstructure.py:36-38`).
11. The only prose definitions of the evidence kinds are `README.md:106-110`; `RULES.md` defines none. `docs/MODULE_EVIDENCE_INVENTORY.md:7` defines maturity as a module label.
12. Python already pins three cross-tier fixtures that TypeScript reads (`python/test_lpbf_build_job.py:116`, :124, :466 against `tests/fixtures/build-job-{microstructure,kinetics,segregation}-blocks.json`). The gr parser tests use synthetic payloads only (`tests/lpbf-gr-solidification.test.tsx:19-48`).

## 3. Bump plan

### 3.1 Pin-moving changes

| Order | Bump | Files that move the pin | W/D | Owner |
|---|---|---|---|---|
| 1 | SOL-A1, front containment | `python/solidification_front.py`, `python/lpbf_thermal_solver.py` (:1195-1217, :1563-1591 only) | unchanged | Opus |
| 2 | P8, additive research arm | `python/lpbf_thermal_solver.py` hook, new `python/lpbf_research_arm.py` (manifest 36 to 37) | unchanged | per the P8 integration contract |
| 3 | SOL-C, local coupling and opt-in field diagnostic | `python/solidification_front.py`, `python/lpbf_thermal_solver.py` | unchanged | Opus |
| later | P3 keyhole leg (conditional) | `python/fabbro_keyhole.py` and or `python/lpbf_thermal_solver.py` per its registration | changes | P3 lane |

Served frozen bumps: SOL-A1, P8 and SOL-C. Not frozen bumps (outside the manifest, no pin move): SOL-K (kinetics), SOL-B (CALPHAD conserved Scheil and admission), every TypeScript change. They carry their own identities (section 5) and the phase6a golden change ledger.

Stage A from the SPEC splits into SOL-A (front, its consumers and the UI, including bump SOL-A1) and SOL-K (kinetics). Stage B is SOL-B. Stage C is SOL-C. Stage D arms are separate research lanes.

### 3.2 Ordering rules

1. SOL-A1 goes first because it contains served misleading output (the Ti64 phase note, the 19% low Hunt coefficient) and because SPEC:192 requires the corrected coefficient, path-local admission and the unsourced-parent cascade before any new numerical baseline is frozen.
2. Swap rule: if P8 passes its re-gate and its pre-bump checks before SOL-A1 does, P8 goes first. The second bump then re-makes its bump record with `--from-revision <first bump head>`, re-records the goldens from that head, and uses that head, not `835466fa`, as its parity and snapshot base. P8's base statement (SPEC_p8 at `b6e68dfe`, :243, :248) must read "the preceding pin head".
3. SOL-C comes after P8 in every case: its opt-in field diagnostic rides P8's isolated research-options transport and cache overlay in `lpbf_thermal_solver.py` rather than a second option channel.
4. P3 starts only after P8's onset-kernel correction is merged and after its data unblock. If its served bump is ready while a W/D-invariant batch is open, it waits for that batch's R-lane run and push. Its own batch uses the full bands run (statistics change), not the restamp.
5. Only one bump branch holds the pin at a time. A bump branch is cut from the previous bump's head, never from `main` while another bump is in flight.

### 3.3 Per-bump outputs

Each pin-moving bump produces, in this order, on its own branch:

1. Pre-bump: synthetic unchanged-output snapshot at the from-head (3.5).
2. The code change plus its self-contained tests.
3. Guarded commit: the new pin in `python/lpbf_implementation_fingerprint.expected`.
4. From `python/`: `python -B tools/lpbf_bump_record.py --from-revision <from-head> --with-parity-check --slow --expect-drift <exact keys>`, run against the goldens still recorded at the from-hash (the tool refuses others), with the record JSON, `.reasons.md` and `.expect-drift.txt` under `docs/LPBF_IMPLEMENTATION_BUMP_<date>_<id>.*`.
5. Guarded commit: all 25 goldens re-recorded with `--record --force --twice --slow`, `GOLDEN_FINGERPRINT`, and `HTTP_GOLDEN` re-pinned with a reason line (`python/test_lpbf_calibration_frozen.py:40-59`); afterwards `--check --slow` gives 25 PASS.
6. Post-bump snapshot compared with the pre-bump snapshot (3.5).
7. PROOF.md entry with scope, changed paths, drift keys and the known reds of 3.6. No accuracy wording.

### 3.4 SOL-A1 expected drift

Exact entries, no globs (G11 and G18 are not reference cases, but exact keys keep the record honest):

1. `g11_build_job_meltpool:meltpool.0.typedSha256`, `meltpool.0.canonicalSha256`, and the same two keys for `meltpool.1` (Ti64, the case that today carries the martensite note) and `meltpool.2`.
2. `g18_in625_latent_heat:meltpool.in625`.
3. G12: the four removed observations `solidification.hunt`, `solidification.pdas`, `solidification.sdas`, `solidification.phaseNote`, the changed `solidification.evaluate`, and the new first appearances defined in section 6, each named exactly.
4. Every `geometry_um`, `peakTemperature_C` and every other case must PASS. A drift outside this list stops the bump; it is enumerated and justified before recording, never absorbed by widening the list.

### 3.5 Unchanged-output evidence without measured rows

1. Parity: all cases other than the 3.4 keys PASS, including `meltpool.{0,1,2}.geometry_um` and `meltpool.in625.geometry_um`.
2. New tool `python/tools/lpbf_wd_invariance.py` (non-manifest, Phase 0): `--capture OUT` calls `calculate_meltpool_physics` and `compose_verdict` directly (not the process-window endpoint, whose overlay reads measured rows) for the five primary alloys x Rosenthal, Eagar-Tsai, Goldak x the 49-cell synthetic grid of the P7b spec (P 80 to 540 W, v 300 to 2400 mm/s, beam 80 um, preheat 80 C, layer 40 um, hatch 100 um). It records float.hex of `meltPoolGeometry`, `processParameters`, `processWindowMap.grid`, `defectDiagnostics`, the regime label, `extentStatus` and the verdict class. `--compare A B` requires byte equality and prints the first difference. P8 can use the same tool for its own statement.
3. `HTTP_GOLDEN`: the three digests move; the geometry inside the payload is asserted equal by the snapshot above.
4. No bands row, dataset loader or overlay is read. The R-lane restamp later repeats the invariance on the published input tuples as an independent check (3.7).

### 3.6 CI-bound artefacts

| Artefact | State on a bump branch | Handled by | When |
|---|---|---|---|
| `data/calibration/lpbf-meltpool-error-bands-v1*.json` | stale; `tests/lpbf-error-bands.test.tsx:59-62` and `python/test_lpbf_error_bands.py:316-321` red | R-lane, `--restamp` | once, on the batch head |
| `DEPTH_BIAS_BANDS_ID` (`src/utils/depthBiasWarning.ts:19`) | unchanged; `tests/depth-bias-warning.test.tsx:13` and `python/test_lpbf_depth_bias.py:199` stay green | R-lane, same commit as the bands | same |
| `demo/snapshots/*` | stale; `tests/demo-snapshots.test.ts:65-78` red; `tests/demo-gate.test.tsx:108-111` stays green because snapshots and bands are stale together | R-lane, `npm run demo:snapshots` then `npm run demo:snapshots:determinism` | after the bands, same batch |
| Dated records (NIST 2716 and 2525, dataset comparison, keyhole benchmark, leaderboard) | stale; the keyhole benchmark test skips (`python/test_lpbf_keyhole_benchmark.py:167-170`), record-current tests outside CI fail | R-lane, regenerated as dated history | same |
| Stored machine calibrations | stale for users (fact 8) | notice in the batch report | at push |

Expected reds are listed in each bump record and cleared before the merge to `main`. A batch with any of them red is not merged.

### 3.7 Records lane (R-lane)

1. Purpose: the only lane that opens the bands row table, runs dataset loaders or records the overlay. It is a records lane, not a physics lane. Its agent is not reused for later blind depth work; the BOARD exposure log records it.
2. New mode, written in Phase 0 by Sonnet with synthetic tests only: `python -B python/tools/lpbf_error_bands.py --restamp [--date D]`. It checks the committed artefact against its own recorded hash, re-solves every committed row with the same kernels, and requires `pred` (W, D, status) and `enthalpy` to equal the committed values at the committed precision (`eb.round_sig`, tool :144). On any difference it writes nothing, exits 1 and lists row IDs only. Otherwise it writes the new `implementationHash`, `codeRevision`, `toolSha256`, `generatedAt`, `rowsSha256`, `contentSha256` and `bandsId`, recomputes the cells from the rows and requires them byte-equal to the old cells. `--check` must pass afterwards.
3. Sequence on the batch head: restamp; update `DEPTH_BIAS_BANDS_ID`; record the demo snapshots and run the determinism check; regenerate the dated records; run the full unit suite and the CI Python list; one commit with explicit paths.
4. A restamp refusal means a bump changed W/D. The batch stops and the Opus gate reopens that bump.
5. For P3 the R-lane runs the full tool (`npm run lpbf:bands`) with the before and after statistics review that P7b recorded, and its owner states every moved cell.

### 3.8 Batches

1. W1: Phase 0, SOL-A (with SOL-A1), SOL-K, and P8 if gated in time; SOL-B joins if ready (it moves no pin). R-lane, Opus gate on the batch, one maintainer trailer run, one push.
2. W2: SOL-C and anything left from W1. R-lane, gate, trailer, push.
3. P3: its own batch.

## 4. Quantity envelope contract

### 4.1 Placement

1. `python/quantity_envelope.py` (new, stdlib-only, outside the thermal manifest): closed vocabularies (statuses, reason codes, quantity definitions with SI units, uncertainty kinds, fraction bases, source read levels), builders (`quantity(...)`, `unavailable(...)`, `observation(...)`) and `envelope_problems(obj, declaration)`.
2. `python/module_contract.py`: new frozen dataclasses `QuantityDeclaration(path, definition, unit, statuses, evidence_kinds, reason_codes, fraction_basis=None, role="model-output")` and `ObservationDeclaration(path, observable, source_evidence_kinds)`; `Operation` gains `quantities` and `observations`. `ModuleContract.__post_init__` rejects a declared evidence kind above the module ceiling (`within_ceiling`), unknown statuses or codes, paths whose first segment is not an output field, and overlap between quantity and observation paths. Nested `status`, `reasons`, `evidenceKind` keys are legal only inside declared paths; the top-level rules at :293-296 and :332-335 stay as they are.
3. `python/module_registry.py` emits `quantities` and `observations` per operation into `src/generated/moduleRegistry.{json,ts}` and a new generated `src/generated/quantityEnvelope.ts` with the vocabularies; `python scripts/emit-module-registry.py --check` covers both.
4. `src/data/quantityEnvelope.ts` (new): `checkedQuantity(raw, declaration)` and `checkedObservation(...)`, used by every strict parser in 7.2.
5. Manifest rule: `solidification_front.py` and `lpbf_thermal_solver.py` must not import `quantity_envelope.py`, because the manifest closure test (`python/test_lpbf_implementation_fingerprint.py:113`) would then require it in the manifest, and every later vocabulary edit would move the pin. They emit plain literals; `python/test_quantity_envelope_payloads.py` runs `envelope_problems` on the real thermal payloads of the fixture set (4.8) so a literal outside the vocabulary fails a test.
6. The thermal solver and Build Job sit in the legacy `3d-distortion-lab` contract; their envelopes are enforced by the Python payload test and the TypeScript parsers, not by contract declarations, until that module is contracted.

### 4.2 Wire format v1

Every response that carries envelopes has top-level `quantityEnvelopeSchema: "metalliksa-quantity-envelope-1"`. A quantity is an object:

| Key | Rule |
|---|---|
| `status` | one of 4.5. |
| `value` | SI number, or an object of SI numbers for a band of model alternatives; `null` unless `status` is `computed` or `partial`. Display conversion (um, mm/s, C) happens only in the UI. |
| `unit` | closed unit string, present even when `value` is null. |
| `quantityDefinition` | ID from the registry in `quantity_envelope.py` (initial set: `liquidus-front-thermal-gradient`, `liquidus-front-normal-speed`, `liquidus-front-cooling-rate`, `liquidus-front-g-over-r`, `pdas-model-alternatives`, `sdas`, `front-morphology`, `solid-state-transformation`, `cet-class`, `laves-trapped-scheil-fraction`, `scheil-phase-inventory`, `scheil-residual-liquid`, `critical-temperature`, `lsw-mean-radius`, `precipitation-strengthening`). |
| `role` | `model-output` or `software-diagnostic` (the SOL-C user-threshold arm). |
| `reasons` | list of `{code, text, parent}`; `parent` names the dependency path (for example `material.liquidus_C` with its provenance class) so a child's unavailability traces to its parent. Empty only for `computed`. |
| `evidenceKind` | machine vocabulary of 4.3; `unresolved` whenever `value` is null. |
| `numericalStatus` | `{state, settings, residuals}`; `state` in `not-assessed`, `unresolved`, `refinement-passed`, `failed`. Separate from physical status. |
| `physicalValidation` | fixed `{status: "unvalidated", experimentalValidation: false, productionReady: false}` in this chain. |
| `sources` | list of `{id, locator, readLevel}`; `readLevel` in `primary-read`, `secondary-read`, `repository-attribution`. Replaces block-wide `doi` fields. |
| `assumptions`, `validity` | lists and domain objects from the SPEC. |
| `uncertainty` | `{kind, construction}`; `kind` in `model-alternatives`, `parameter-sensitivity`, `numerical-refinement`, `calibrated-prediction-interval`, `not-quantified`. |
| `fractionBasis` | required for fraction quantities: `mole-of-atoms`, `mass`, `volume`, `reaction-progress`, `microconstituent`. |
| `identity` | `{input, model, parent}` digests and IDs (section 5). |

### 4.3 Evidence kinds, ceiling and observations

1. Machine vocabulary: `EVIDENCE_TYPES` (`module_contract.py:30-37`). Display labels and governing prose: `README.md:106-110`, as SPEC:27 now states.
2. Computed quantities in this chain carry `screening-only` (SPEC:27); the cap equals the module ceiling, so no ceiling change is needed.
3. Retired quantity kinds and their replacements:

| Current string | Location | Replacement |
|---|---|---|
| `"evidence": "unvalidated"` | `python/calphad_solver.py:2172`, :2258 | `evidenceKind: "screening-only"` plus `physicalValidation.status: "unvalidated"` |
| `Literature estimate (screening): ...` | `python/lpbf_solidification_segregation.py:84`, :687, :904 | `evidenceKind: "screening-only"`; the source relation moves to `sources` and `assumptions` |
| `Measured (literature, as-built LPBF IN625); simulations listed separately` | `lpbf_solidification_segregation.py:1149` | an observation record (below) |
| `evidence: {kind: "screening-only", ...}` | `python/lpbf_gr_solidification.py:461` | kept as the response-level object (SDK-reserved name); quantities carry their own envelopes |

4. Observation records: a separate top-level list `observations` of `{recordKind: "source-observation", observable, value, unit, sourceEvidenceKind, source, materialScope, processScope, comparability}`. The key is `sourceEvidenceKind`, never `evidenceKind`, so no reader can take it for the module's result. Whether such a record may say `measured` inside a module whose ceiling is `screening-only` is a maintainer item (section 11, MD1).

### 4.4 Maturity

There is no per-quantity maturity field. Maturity comes from the registry (`src/generated/moduleRegistryCore.ts`), stays `Research` for this chain, and `Production` cannot be expressed (`MATURITY`, :78). A retained instructional demonstration (SPEC:166, :180) needs its own seed entry and contract in `python/module_registry_seed.json`, where `Preview` is allowed. The lead decides between retiring and isolating; this contract recommends retiring the browser numerical phase and Scheil prediction controls.

### 4.5 Status mapping

| Served status | Where | Envelope |
|---|---|---|
| `available` | worker and gr cells (`module_contracts_lpbf_secondary.py:185`, `lpbf_gr_solidification.py:41`) | `computed` |
| `screening-fallback` | `python/lpbf_solidification_microstructure.py:149`, :188 (tail-length path removed in P6, only legacy inputs reach it) | `unavailable`, `invalid-interface-sample` |
| `degenerate-floor` | same module :102-111, :179-188 | removed; a physical value is `computed`, a zero or nonfinite one is `unavailable` with `invalid-interface-sample` (SPEC:104) |
| `unavailable` | everywhere | `unavailable` with a code |
| `error` | gr cell | `failed`, `solver-error` |
| `pycalphad-scheil-gulliver` | `calphad_solver.py:2143`, :2235 | `computed` only when phase and atom inventories close; otherwise `partial` |
| `incomplete` | `calphad_solver.py:2235` (kernel `complete` or `incomplete` at :1608) | `partial`, `residual-liquid-at-termination` |
| `bisected`, `bracketed-by-grid` | `criticalTemperatureStatus` (`module_contracts_calphad.py:100-110`) | `computed`; the method goes to `numericalStatus.settings` |
| `heuristic-phase-name` | beta transus, sigma risk | `unavailable`, `missing-source-bound-model` until the SPEC:57 criterion exists |
| `screening-constant` | sigma risk temperature | `unavailable`, `missing-source-constant` |
| `generic-constants-illustrative` | `python/kinetics_ttt_cct_solver.py:103` | `unavailable`, `missing-source-bound-model` |
| `registry-screening-value` | `kinetics_ttt_cct_solver.py:101` (Ti64 Ms, Mf, transus) | `unavailable`, `missing-source-constant`; the registry value may survive only as metadata (SPEC:172) |
| `unavailable-aging-temperature-at-or-above-solvus` | `kinetics_ttt_cct_solver.py:102` | `unavailable`, `outside-source-model-domain` |
| `"not requested"` reason | `src/components/CALPHADMultiComponentStudio.tsx:1618` | `not-requested`, `not-requested` |
| `pdasOutOfRange: true` | `python/solidification_front.py:117-122` | `unavailable`, `outside-source-model-domain` |

### 4.6 Reason codes

The registry holds the 21 codes of SPEC:34 and four integration codes:

1. `parent-unavailable`: generic cascade code, always with a `parent` path.
2. `solver-error`: an exception or nonconvergence with no physical meaning.
3. `insufficient-sample-support`: the P6 "fewer than 3 solidifying samples" case (`solidification_front.py:43-45`), which is a support count, not an invalid sample.
4. `quarantined-legacy-path`: the legacy CFD request (`python/lpbf_worker_rpc.py:16-20`) and `openfoam/meltPoolFoam/solidificationModel.H`.

Every code has one English display sentence in `quantity_envelope.py`; the sentences are user-facing wording under MD2.

### 4.7 CET source facts

The boolean `equationVerified` (`python/lpbf_cet_screening.py:65`, :94, :114, :273; parsed at `src/data/lpbfGrSolidification.ts:278`, :285; typed at `src/services/lpbfGrSolidificationService.ts:60-61`, :139-140) is replaced by:

| Field | Values |
|---|---|
| `sourceChecks.equationRead` | `{state: "read" or "not-read", locator}` |
| `sourceChecks.algebraReproduced` | `{state: "reproduced", "not-reproduced" or "not-attempted", test}`; `test` names the Python test that recomputes it, and a test asserts that every named test exists |
| `sourceChecks.printedLimitComparison` | `{state: "agrees", "disagrees", "not-available" or "not-attempted", printed, computed, tolerance}` |

Knapp: read, reproduced, compared with the printed 1.52e11 and 6.98e9 within the SPEC gate 4 tolerance. Polonsky: read, reproduced, `not-available`. Top-level Gaumann 2001: `not-read`. `_set_complete` (:160-169) additionally requires `equationRead.state == "read"`. `GrSolidificationMapCard.tsx:455` and :467 render the three facts separately. The `constants_override` branch (:255-256) leaves the served path and becomes a test helper.

### 4.8 Contract, registry and TypeScript migration

1. Contract versions: `CONTRACT_VERSION` 0.1.0 to 0.2.0 in `module_contracts_calphad.py:13` and `module_contracts_lpbf_secondary.py:21`; regenerate `docs/modules/phase-diagram.md` and `docs/modules/solidification-microstructure.md`.
2. Response schemas: `lpbf-gr-solidification-1` to `-2` (`lpbf_gr_solidification.py:37`, `src/data/lpbfGrSolidification.ts:20`); `lpbf-solidification-segregation-1` to `-2` (`lpbf_solidification_segregation.py:80`); new `schema: "lpbf-solidification-microstructure-2"` on the worker response; `calphad-minimize-2` on the CALPHAD response.
3. Real payload fixtures (Phase 0, then regenerated by each lane): `python/tools/solidification_payload_fixtures.py --write` produces `tests/fixtures/solidification-payloads/*.json` from the real Python functions on synthetic requests only: thermal blocks for the five alloys (Rosenthal, the G11 payload style) and one keyhole-leg case; Build Job microstructure, segregation and kinetics blocks (reusing the generators at `python/test_lpbf_build_job.py:78-99`, :439-459); gr point and 2 x 2 map for IN718, a point for Ti64, an unknown-alias refusal; worker results for the five alloys and a `cfdResult` refusal; CALPHAD results for IN718 (mc_ni), Ti64 (mc_ti), 316L (mc_fe) and AlSi10Mg (COST507) with Scheil on. `python/test_solidification_payload_fixtures.py` asserts committed equals regenerated, as :116 does today. TypeScript tests parse every fixture and assert acceptance, plus one mutation per rule. This answers SPEC gate 6: the parsers are tested on migrated Python payloads.
4. No dual-read: parsers accept only the new schema. Older payloads (warm workers, browser state, `useLpbfBuildJobStore.ts:219`) render the existing "older solver result, recompute" path. Restart `lpbf_worker.py` at rollout.
5. Hand-written vocabularies to replace with the generated ones: `GR_CELL_STATUSES` (`lpbfGrSolidification.ts:17`), `KNOWN_STATUS` (`src/components/3d-distortion-lab/BuildJobMicrostructurePanel.tsx:47`), the status branches of `src/utils/solidificationOutcome.ts:19-27`, the alloy check (`lpbfGrSolidification.ts:266`), the Hunt colour and letter maps (:116-125).

### 4.9 SDK items left for review

`TODO(maintainer-review)` items 1 (rank of `literature-estimate` against `screening-only`, `module_contract.py:48-52`) and 3 (the pending-oracle cap, :54-58) stay open; this chain does not need either changed. The observation-record rule of MD1 is added to the same review list (`.orchestra/REVIEW-prep-opus-python.md`, named in the TODO comments) as a new item.

## 5. Identities and caches

| Identifier | Location | Changes at | Notes |
|---|---|---|---|
| Implementation pin | `python/lpbf_implementation_fingerprint.expected:1`, `python/test_lpbf_parity_golden.py:60`, 25 goldens | SOL-A1, P8, SOL-C | guarded |
| `MODEL_ID` | `python/solidification_front.py:35` | v1 to v2 at SOL-A1, v3 at SOL-C | read at `lpbf_thermal_solver.py:37`, `lpbf_gr_solidification.py:414`; the UI literal fallback at `src/components/3d-distortion-lab/MeltPool3DCrossSectionLab.tsx:1232` is removed |
| `BUILD_JOB_SOLVER_REVISION` | `python/lpbf_job_cache.py:25`, `src/store/useLpbfBuildJobStore.ts:24`, `python/test_lpbf_build_job.py:666-689`, `tests/build-job-kinetics-panel.test.tsx:27-50` | v26 `lpbf-build-job-sol-a-containment-v26` at SOL-A; again at SOL-C if Build Job output changes; P8 keeps the current value | the job cache key reads it (`lpbf_job_cache.py:111`) |
| gr provenance | `lpbf_gr_solidification.py:463-464` | SOL-A | `frozenFilesModified: False` is removed; `implementationHash` (from the once-per-process helper at `python/lpbf_process_window_cache.py:34-39`), `solidificationModelId`, `buildJobSolverRevision` remain |
| CET `MODEL_ID` | `lpbf_cet_screening.py:38` | v1 to v2 at SOL-A (admission masks change values) | |
| Segregation model IDs | `lpbf_solidification_segregation.py:81`, :685, :902 | unchanged unless values change; schema ID changes (4.8) | |
| `solidificationChainIdentity` | new, `python/calphad_solver.py` provenance (:2505-2512) | SOL-B | sha256 over the canonical bytes of the chain source closure (`lpbf_source_identity.fingerprint_sources`, CANONICAL_SCHEMA v3), pycalphad version, comparator version if used, `tdbCanonicalSha256`, phase exclusions, step and stop settings, original and solved composition, envelope schema |
| TDB identity (minor 20) | new | SOL-B | `tdbCanonicalSha256` = sha256 of the raw bytes with each CRLF pair replaced by LF and nothing else (no decode), the key for identity and caches; `tdbRawSha256` kept as licence provenance to match the external data manifest. `.tdb` is not a text suffix in `lpbf_source_identity.py:13`, and adding it would move the pin, so the chain owns this rule. `calphad_model_cache.read_tdb_text` decodes with `errors="replace"` (`python/calphad_model_cache.py:66-68`); the identity records the replacement count and SOL-B refuses an admitted database with a nonzero count |
| Chain closure test | new `python/test_solidification_chain_identity.py` | SOL-B | the static local import closure of `calphad_solver.py` must be inside the identity file list, like the manifest closure test |
| CALPHAD client request | `src/components/CALPHADMultiComponentStudio.tsx:225-274`, :374-377, :483-490, :557-563 | SOL-B | the result stores the exact request object it answered; export is allowed only when the current request is equal; Python echoes `solvedRequestKey` and the chain identity |
| CSV export | `CALPHADMultiComponentStudio.tsx:490`, `src/utils/calphadDisplay.ts:150-170` | SOL-B | file name `<alloy>_<engine>_<solvedRequestKey[0:8]>.csv`; header rows carry engine, chain identity, solved composition, evidence kind and the ODbL notice under MD3; columns add status and reason codes |
| Process-window LRU, transient cache | fact 8 | every pin move | automatic |
| `scheil==0.3.0` | `python/requirements-lpbf.in` | SOL-B | comparator only, installed with maintainer approval (BOARD 2026-10-15); the CI Python job then installs it |

## 6. Parity harness decisions

1. Error-transition rule (Phase 0, Opus, guarded): in `evaluate_drift` (:1754-1806) a recorded non-error observation whose new value is `{"error": ...}` is a problem under every entry, glob or exact. A deliberate removal deletes the observation instead, which appears as `<missing>` and needs an exact entry. Its unit test goes into the harness tests in `python/test_lpbf_parity_golden.py`.
2. Retire `hunt_morphology` (`solidification_front.py:167-174` and the cuts at :49-52), `hunt_lu_pdas_um` and `HUNT_LU_A_SI` (:56, :177-181), `kirkwood_sdas_um` (:184-187) and `phase_transformation_note` with `TI64_MARTENSITE_K_S` (:83, :190-235). Reason: they are unsourced or wrong rules sitting in a served module, and `lpbf_gr_solidification.py:230` already imports one of them. P7a's parity-only precedent is not repeated.
3. G12 rewrite in the SOL-A1 guarded commit: remove the four observations; observe `solidification.pdasAdmission` (`pdas_band_um` on the fixed-G line pairs of SPEC:126 including the two rejection pairs and canonical IDs `in625`, `in718`, `ti6al4v`), `solidification.defaultBlock` (`evaluate_solidification` for the five canonical IDs on the existing Eagar-Tsai field, without legacy keywords) and `solidification.unknownAlias` (the refusal message). None of these names matches `HONESTY_PATTERNS` (:1590-1600). Honesty facts of the new block are asserted in self-contained tests, not added as parity observations.
4. `evaluate_solidification` loses the ignored keywords (`solidification_front.py:352-364`); its only caller passing them is G12.

## 7. Consumer inventory

### 7.1 Python producers and consumers

| File:line | Today | Change | Lane |
|---|---|---|---|
| `solidification_front.py:35-89` | model ID, Hunt DOI, cuts, anchor, PDAS constants (`9.56e-4` at :66), Ti64 switch, substring alloy match (:86-89) | v2, `A = 1.1773863284676703e-3` (SPEC:124), canonical IDs, sources per quantity | SOL-A1 |
| `solidification_front.py:92-125` | PDAS band on a box | fixed-G line, x, cooling, Vcs, Vab admission before arithmetic (SPEC:126) | SOL-A1 |
| `solidification_front.py:343-423` | medians, notes, DOI on every child, rounding at :411-422 | default arm checks liquidus admission first and returns every front quantity `unavailable` with `missing-source-constant` and the liquidus provenance as parent (SPEC:94); keyhole leg keeps `keyhole-field-inconsistent`; no rounding | SOL-A1 |
| `solidification_front.py:238-308` | separate medians, upper median `_med` (:292-294) | per-sample tuples, defined aggregation, full precision | SOL-C |
| `lpbf_thermal_solver.py:1195-1217`, :1563-1591 | flat keys rounded at :1569-1576 | `solidificationKinetics = {modelId, quantityEnvelopeSchema, interface, quantities{...}}`; flat numeric keys removed | SOL-A1 |
| `lpbf_solidification_microstructure.py:44-79`, :91-111, :138-244, :355-375, :384-470 | own Hunt cuts and linear fractions, DOI map, floor statuses, projection, bands imported from the front, legacy CFD | envelope passthrough; cuts, fractions, floors and band import removed; CFD path refused with `quarantined-legacy-path` | SOL-A |
| `lpbf_worker_rpc.py:12-20` | runs the CFD branch when `cfdResult` is sent | refusal | SOL-A |
| `lpbf_gr_solidification.py:12-21`, :37, :41, :75, :229-319, :342, :461-464 | Hunt credits, schema 1, statuses, Hunt label, `GtimesR` alias of cooling, IN718 and IN625 only | envelopes, schema 2, five canonical IDs (D12), provenance of section 5 | SOL-A |
| `lpbf_cet_screening.py:38`, :65, :79, :84-120, :160-197, :220-280 | boolean flag, one transfer label, no finite-positive check in `cet_band` | 4.7 fields, per-set transfer labels (MD2), finite-positive and domain masks before arithmetic; default LPBF CET `unavailable` with `outside-source-model-domain` (SPEC:140) | SOL-A |
| `lpbf_solidification_segregation.py:80-84`, :600-610, :687, :904, :1009-1037, :1149 | evidence strings, microstructure status reads | envelopes, observation record, schema 2 | SOL-A |
| `lpbf_build_job_solver.py:84-96`, :113-115, :204-245, :1243-1274 | liquidus G x R fed to CCT, 1 K/s floor | kinetics `unavailable` with `missing-thermal-history` for every alloy, floor constant and comment removed (minor 17), blocks follow envelopes | SOL-A |
| `kinetics_ttt_cct_solver.py:101-103`, :567-620 | generic LSW radius and 280 MPa curve | radius and strength `unavailable` for every alloy, steels included (SPEC:166); input checks (minor 18) | SOL-K |
| `alloy_registry.py:232-234`, :343-379 | comments citing retired helpers, Ti64 registry temperatures | comments updated; values kept as metadata only | SOL-A, SOL-K |
| `python/tools/kinetics_documented_changes.py:158-207`, :602-620 | independent LSW oracle flags null rows | expects `unavailable` rows | SOL-K |
| `calphad_solver.py:1475-1633`, :1758, :2003-2008, :2158-2262, :2337-2339, :2383, :2505-2512 | identity residual, pre-kernel clamp, 0.001 filter, nominal-only domain, wording, provenance | raw inventories, residual and `firstStepUnresolved`, refusal or authorised approximation, path-local admission, envelopes, chain identity | SOL-B |
| `module_contracts_calphad.py:79-111`, `module_contracts_lpbf_secondary.py:178-206` | transport vocabularies | quantity declarations, 0.2.0 | SOL-A, SOL-B |

Unreached today and recorded as such (gate 10.9): `kinetics_ttt_cct_solver` is in neither `DISPATCHABLE_SCRIPTS` (`server/processOrchestrator.ts:186-196`) nor `ALLOWED_SCRIPT_NAMES` (`python/persistent_ipc_service.py:107-117`).

### 7.2 Strict TypeScript parsers and types

| File:line | Change |
|---|---|
| `src/data/lpbfGrSolidification.ts:17`, :20, :75-78, :116-125, :206-215, :217-254, :256-327 | generated statuses and alloy list; `checkedQuantity` for front locations; no `huntBand`, no `morphology.label` or `bands` requirement; `sourceChecks` instead of `equationVerified`; schema 2; counts per envelope status |
| `src/services/lpbfGrSolidificationService.ts:30`, :60-61, :139-140 | types |
| `src/utils/solidificationOutcome.ts:18-38` | envelope statuses; no floor branch |
| `src/services/pythonComputationService.ts:270-300`, :1395-1434 | worker and thermal block types |
| `src/utils/pdasBandText.ts:14-23` | renders `pdas-model-alternatives` as two named alternatives, not "lo to hi" (minor 13) |
| `src/utils/goldakCaeCard.ts:50`, :105 | reads envelopes; null with reason |
| `src/utils/calphadResultDisplay.ts:150-170` | inventory residual lines from the raw values replace the "mass balance error" line |
| `src/utils/calphadDisplay.ts:150-170` | CSV columns of section 5 |
| `src/utils/kineticsHardnessDisplay.ts:157-170` | `unavailable` rows; imported only by a test today |
| `src/physics/calphadMultiComponentSolver.ts:312`, :370, :532-538 | retired from numeric display or isolated (4.4) |

### 7.3 UI surfaces

| File:line | Change | Lane |
|---|---|---|
| `src/components/SolidificationMicrostructureLab.tsx:112-119` | bind to `activeSpecimen.lpbf` with a visible scenario deviation (SPEC:176) | SOL-A |
| same file :183-187, :384, :405, :420, :424, :437, :461, :475 | remove G/R band lines, Hunt-Lu and Kirkwood credits, unsourced "typical LPBF" ranges; render envelopes | SOL-A |
| `src/components/GrSolidificationMapCard.tsx:44`, :86, :243, :455, :466-467 | remove Hunt attribution and the "band" metric; render source checks; Ti64, AlSi10Mg and 316L get the Python unavailable state | SOL-A |
| `src/components/3d-distortion-lab/MeltPool3DCrossSectionLab.tsx:1232`, :1241-1290 | no model-ID literal; "Predicted Microstructure" and "Phase note" rows render envelopes or the unavailable reason | SOL-A |
| `src/components/3d-distortion-lab/BuildJobMicrostructurePanel.tsx:47`, :62-63, :86-96 | generated statuses, envelope metrics | SOL-A |
| `src/components/3d-distortion-lab/IndustrialLPBFDecisionLab.tsx:633` | cooling tile from the envelope | SOL-A |
| `src/components/CALPHADMultiComponentStudio.tsx:225-274`, :374-377, :483-490, :557-563, :1523, :1618 | stale gating and export identity, "primary solid phase" wording, `not-requested` | SOL-B |

### 7.4 Effect users will see

After SOL-A1 the default G, R, cooling rate, G/R, PDAS, morphology and phase note are unavailable for all five alloys in the thermal card, both labs, the Build Job microstructure panel and the G/R map, because no liquidus entry has an admitted source (SPEC:94). W, D, regime and verdict do not change. This is the intended containment and goes into the batch report (MD5).

## 8. Test inventory

### 8.1 Tests that change

| Lane | Python | TypeScript |
|---|---|---|
| SOL-A | `test_solidification_front.py:8`, :23-49, :60-73, :104-108; `test_lpbf_solidification.py:12-44`; `test_lpbf_waveb_front_raytracer.py:14`, :44, :74; `test_lpbf_waveb_rosenthal_keyhole.py:66`; `test_lpbf_build_job.py:42-124`, :141-161, :204-232, :250-279, :288-360, :391-423, :426-466, :666-689, :1030-1033; `test_lpbf_p6_containment.py:203-260`, :318-328; `test_lpbf_p7a_rules_and_nulls.py:372-381`, :410; `test_lpbf_p1_sourced_depth_path.py:227` (equality still holds, recheck); `test_lpbf_gr_solidification.py` (whole file, notably :316-349); `test_lpbf_solidification_microstructure_rpc.py:16`, :47-74, :114-157; `test_lpbf_solidification_segregation.py:25`; `test_phase7_microstructure_validation.py:3`, :18-31; `test_phase8.py:25`, :35-63; `test_phase8_microstructure_contract.py:30-42`; `test_module_contract_lpbf_secondary.py:89-118`; `test_module_contract_solidification_microstructure.py:23-62`; `test_module_contract.py` (new dataclasses); `test_lpbf_calibration_frozen.py:55-59`; `test_lpbf_parity_golden.py:56-60` | `tests/lpbf-gr-solidification.test.tsx:19-48`, :78, :111-115, :203, :216; `tests/build-job-microstructure-panel.test.tsx:10`, :37, :90; `tests/build-job-segregation.test.tsx:11-12`; `tests/build-job-kinetics-panel.test.tsx:12`, :27-50; `tests/solidification-outcome.test.ts:8`, :41; `tests/goldak-cae-card.test.ts:36`, :274; `tests/lpbf-material-authority.test.ts:182-232`; `tests/lpbf-claims-wording.test.tsx:10-11`; generated registry parity tests |
| SOL-K | `test_kinetics_fx.py:100-107`, :304-312; `test_kinetics_li1998.py:30`; `test_phase6a_golden.py:304-305`; `test_phase6a_t2b_golden.py`; `test_phase6a_t2b_migration.py:95-100`; `test_alloy_registry.py`; `test_alloy_data_kinetics_uq_fatigue.py`; goldens `python/golden/phase6a/kinetics_ttt_cct_solver/` including `step_b/aisi4140_ui_defaults.json` and `step_b/aisi4340_slow_cool.json`, with a change-ledger entry | `tests/kinetics-hardness-display.test.ts:17`, :314-321 |
| SOL-B | `test_calphad_honesty.py:876`; `test_calphad_model_cache.py:177`, :207, :357; `test_calphad_literature_solidification.py`; `test_calphad_matcalc_open.py`; `test_calphad_mc_ti.py`; `test_calphad_carbon_reference.py`; `test_alloy_data_calphad_battery_icme.py`; `test_module_contract_calphad.py`; `test_phase6a_golden.py` and `test_phase6a_t2a_migration.py` for the shape of the unavailable envelope in `python/golden/phase6a/calphad_solver/`; tools `xcheck_scheil_laves.py`, `xcheck_superalloy_table.py`, `calphad_ui_specimen_drift.py` | `tests/calphad-display.test.tsx:287`; `tests/alloy-property-consumers.test.tsx:20-21`; `tests/a11y-form-labels.test.ts:27`; `tests/visibility-loops.test.tsx`; `scripts/test-calphad-alsi10mg.ts` |
| SOL-C | `test_solidification_front.py`, `test_lpbf_solidification.py`, `test_lpbf_waveb_front_raytracer.py` (samples and aggregation), G12 again | lab and map distribution rendering |
| R-lane | `test_lpbf_error_bands.py:316-321`, `test_lpbf_depth_bias.py:199` | `tests/lpbf-error-bands.test.tsx:59-62`, `tests/demo-snapshots.test.ts:65-78`, `tests/demo-gate.test.tsx:108-111`, `tests/depth-bias-warning.test.tsx:13` |

New tests: `python/test_quantity_envelope.py`, `python/test_module_contract_quantities.py`, `python/test_quantity_envelope_payloads.py`, `python/test_solidification_payload_fixtures.py`, `python/test_solidification_chain_identity.py`, `python/test_scheil_inventory_oracle.py`, `python/test_scheil_package_comparator.py` (skips with its reason when `scheil` is missing), `python/test_cet_source_checks.py`, `tests/quantity-envelope.test.ts`, `tests/solidification-payloads.test.ts`.

The three audit scripts (`docs/research/scripts/check_solidification_*.py`) assert today's defects (their `baselinePolicy` says so). They stay dated audit records and are not rerun after the matching fix; their counterexample fixtures are copied into the self-contained tests above, with the inverted expectation.

### 8.2 Independent oracles

1. Scheil inventory (SOL-B): `test_scheil_inventory_oracle.py` reads every unfiltered phase increment (amounts and `phasesX`) from a raw kernel trace and rebuilds the inventories itself, never from `solid_x` back-solved at `calphad_solver.py:1583-1585`; it drives the served `point_equilibria` below 0.001 liquid and covers the 0.40 and 18.5 phase-sum callbacks. The frozen no-pycalphad phase6a fixtures are not used for this.
2. Kinematics (SOL-C): a laboratory travelling field with analytic `v·grad(T)`, independent of the sample dictionary (SPEC gate 3).
3. LSW (SOL-K): `kinetics_documented_changes.py` stays the independent row checker, now expecting `unavailable`.
4. Comparator (SOL-B): `scheil` 0.3.0 as a separately identified software comparison only (SPEC:214).

### 8.3 Tests that read measured melt-pool data

Blind lanes run the targeted lists of 8.1 and never the full unit suite or the full CI Python list. Python modules matching the loader pattern `load_lane_in625|load_hofmann_316l|load_totis_ti64|load_ku_leuven|load_ghosh_in625|load_trapp_316l|nist-amb2022-03-optical|lpbf_public_datasets|lpbf_literature_datasets`: `test_lpbf_additional_datasets`, `test_lpbf_benchmark`, `test_lpbf_calibration_v2_config`, `test_lpbf_keyhole_literature`, `test_lpbf_keyhole_regime_bump`, `test_lpbf_literature_datasets`, `test_lpbf_nist_in718_comparison`, `test_lpbf_p7b_sourced_constants`, `test_lpbf_process_map`, `test_lpbf_process_window`, `test_lpbf_public_datasets`, `test_lpbf_wave2_datasets`, `test_lpbf_zero_drift_depth`, `test_nist_optical_transcription`, plus `test_lpbf_depth_bias` (Lane ratios) and `test_lpbf_keyhole_benchmark`. TypeScript files matching the same pattern: `tests/guided-demo.test.tsx`, `tests/lpbf-experimental-validation-logic.test.ts`, `tests/lpbf-nist-comparison-api.test.ts`, `tests/lpbf-run-bundle-api.test.ts`, `tests/lpbf-run-bundle.test.ts`, `tests/lpbf-run-client.test.ts`, `tests/lpbf-run-nist-ui.test.tsx`, `tests/lpbf-run-proxy-campaign-client.test.ts`, `tests/lpbf-run-repository.test.ts`, `tests/lpbf-source-archive-selection.test.ts`, `tests/lpbf-source-optical-catalog.test.ts`, `tests/melt-pool-literature-case.test.ts`, and `tests/demo-snapshots.test.ts` (it reads the overlay snapshot). These run at the batch gate and in the R-lane only. The parity suite is depth-free (G14 uses a synthetic row, `lpbf_parity_check.py:515-531`) and runs in the lanes.

## 9. Phases, owners and acceptance checks

Owners: Opus for hard integration code and guarded bump work, Sonnet for ordinary code, Haiku for chores, Astra for physics questions. Each lane has one Opus gate (ORCHESTRA.md section 5). Nothing starts before the re-gate of the amended SPEC and this contract passes (SPEC:188).

| Phase | Work | Owner | Acceptance checks |
|---|---|---|---|
| 0.1 | `quantity_envelope.py`, SDK dataclasses, registry emission, generated TS vocabularies, `src/data/quantityEnvelope.ts` | Opus | new Python and TS tests pass; `python scripts/emit-module-registry.py --check`; `npm run lint`; existing contract tests unchanged |
| 0.2 | parity error-transition rule (guarded) | Opus | harness unit test: a value turning into an error fails under glob and exact entries; `--check --slow` still 25 PASS at `36cd9d4a` |
| 0.3 | bands `--restamp` mode | Sonnet | synthetic tests in `test_lpbf_error_bands.py`: equal rows restamp and `--check` passes; one changed row refuses and writes nothing |
| 0.4 | payload fixture generator and staleness test, baseline at current code | Sonnet | generator deterministic twice; fixtures contain no measured input |
| 0.5 | `lpbf_wd_invariance.py` capture and compare | Sonnet | two captures of one tree are byte-equal |
| 0.6 | TDB identity inventory (raw, CRLF-canonical, decode replacement count) for COST507, mc_ti, mc_ni, mc_fe, mc_al; report under `.orchestra/reports/` | Haiku | numbers reproducible by a second run |
| SOL-A | A1 front and thermal block plus bump (3.3, 3.4, 6); A2 Python consumers; A3 TS parsers and UI; A4 fixtures, `docs/LPBF_ENGINEERING.md:43` coefficient text, module docs, PROOF draft | A1 Opus; A2, A3 Sonnet; A4 Haiku | envelope tests and payload test pass; SPEC gates 1, 4 and the identity part of 6 on real payloads; bump record shows only 3.4 keys; invariance compare byte-equal; targeted lists of 8.1 pass; known reds exactly those of 3.6 |
| SOL-K | LSW and strength `unavailable` for every alloy, input checks, oracle and goldens | Sonnet; golden capture Haiku | Li TTT and CCT outputs byte-equal outside the LSW rows; phase6a ledger entry names every changed key |
| SOL-B | B1 raw inventories, residual, refusal of invalid callbacks, path-local admission; B2 chain identity and TDB rule; B3 contract, service, studio, export; B4 comparator and requirements pin; B5 browser model retirement | B1, B2 Opus; B3, B4, B5 Sonnet | SPEC gate 2 with the independent oracle (raw 1e-12; 5e-7 per rounded scalar at API precision); chain closure test; export refused for a stale request; CSV carries engine and identity |
| P8 | per its integration contract, with the base rule of 3.2 | its owners | its own gate; invariance tool byte-equal |
| SOL-C | per-sample tuples, aggregation, unrounded transport, opt-in field diagnostic on P8's options transport, bump | Opus; UI Sonnet | SPEC gate 3 (lab-frame oracle within 3e-6 relative, mutant `R = v` fails, eight-pair and even-count fixtures); quantities that need gate 5 stay `numericalStatus.state: "unresolved"`; bump drift limited to its declared keys |
| R-lane | 3.7 | Sonnet (exposed records agent), checked by the batch gate | restamp succeeds without a refused row; `npm run lpbf:bands:check`; full unit suite and CI Python list green |
| Batch close | one gate, one trailer run, one push | lead and maintainer | `scripts/check_ceiling_review.py` reports every guarded path covered |

## 10. Minor notes, engineering parts

| Note | Engineering resolution |
|---|---|
| 9 ODbL | export header slot and `observations`-style licence record wired in SOL-B; the notice text and the `mc_fecocrnbti.tdb` entry (the licence file `python/databases/MATCALC_OPEN_DATABASES_LICENSE.md` has none; the file is a test fixture per `python/test_calphad_honesty.py:38`) go to MD3 |
| 13 ordering claims | `calphad_solver.py:2383` "upper bounds" gets its mechanism scope in SOL-B; `pdasBandText.ts:19` renders two named alternatives in SOL-A |
| 14 audit JSON labels | already relabelled at `3908a741` (`checkKind`, `baselinePolicy`); the scripts stay dated records (8.1) |
| 17 Build Job CCT input | SOL-A removes the liquidus G x R path and the stale floor (`lpbf_build_job_solver.py:89-96`, :204-245) |
| 18 aging input | SOL-K rejects nonfinite or nonpositive absolute temperatures and negative or nonfinite times before arithmetic and returns `nonphysical-input`; the CLI never prints a bare `NaN` token |
| 20 line endings | section 5 TDB rule |
| 21 reproducibility | already git-independent at `3908a741` (`docs/research/scripts/_solidification_check_common.py:1`, :13-14); nothing further |

Minor 15 (wording inside the SPEC) is Astra's text; this contract avoids the same words.

## 11. Maintainer decisions

1. MD1, SDK semantics: confirm that per-quantity `evidenceKind` is capped by the module ceiling, and decide whether a separately declared observation record may carry `sourceEvidenceKind: "measured"` inside a module whose ceiling is `screening-only` (recommended: yes, with that key name). Raising `PENDING_ORACLE_CEILING` (`module_contract.py:54-58`) is not requested.
2. MD2, wording (ORCHESTRA.md:84): the three quoted SPEC candidates (SPEC:110, :120, :152), the reason-code sentences, status labels, the per-set CET transfer labels replacing `lpbf_cet_screening.py:79`, the source-check labels replacing `GrSolidificationMapCard.tsx:455` and :467, and the export file name and header text.
3. MD3, licence: the ODbL Produced Work notice on exports, the `mc_fecocrnbti.tdb` licence entry, and COST507 redistribution (no new distribution meanwhile).
4. MD4, trailers and pushes: guarded paths per batch are the pin, the 25 goldens, `python/tools/lpbf_parity_check.py` (Phase 0 rule and G12) and, with P8, `python/test_phase6a_leaf_modules.py`; one trailer run and one push per batch.
5. MD5, notice: after SOL-A1 the default solidification numbers are unavailable for all five alloys (7.4), and every pin move makes stored machine calibrations stale (fact 8). The lead also reports the browser CALPHAD retirement choice (4.4).

## 12. Coordination with P8 and P3

1. For the P8 integration contract owner: the parity and snapshot base is the preceding pin head (3.2); the research-options transport and cache overlay are shared with SOL-C; the bands, demo snapshots and dated records go to the batch R-lane, not the P8 lane (P8 gate item 13); `BUILD_JOB_SOLVER_REVISION` stays at whatever value is current when P8 lands; each bump names only its own exact G11 and G18 keys; P8 can use `lpbf_wd_invariance.py`.
2. For P3: no served bump while a W/D-invariant batch is open; its batch runs the full bands tool in the R-lane; its onset kernel follows P8's B1 correction.
