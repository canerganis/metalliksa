# Solidification chain: integration contract

Record date: 2026-10-15. Owner: Opus system architect (architecture and hard integration code).
Branch `research/solidification-astra`. Revision 0 was `7146e11e` on `3908a741`; this Revision 1 sits on `024e30cd` (SPEC Amendment 2 and the melt-point ledger). Served code locators refer to `835466fa`; no served file changed since, so they still hold.
Status: proposed integration contract, **not implemented**. Companions: [physics specification](SPEC_solidification_2026-10-14.md) (Amendments 1 and 2) and [audit](AUDIT_solidification_chain_2026-10-14.md).

Scope: the Opus gate's required changes 4, 5 and 10, the engineering parts of minor notes 9, 13, 14, 17, 18, 20 and 21 (`.orchestra/reports/solidification_gate_verdict_2026-10-15.md`), the items SPEC Amendment 1 asks of this contract ((a) to (f)), and the plan side of re-gate items RA1 to RA6 plus the engineering W1 minors (`.orchestra/reports/solidification_regate_verdict_2026-10-15.md`; index in section 13). Physics admission rules, coefficients and domains stay in the SPEC and the ledger; this file decides representation, order, identities, consumers, tests and owners. Nothing in this file is evidence about physical accuracy, and no software check named here is a physical test.

Literal marking (RA4): every user-facing English string this plan introduces or moves is listed in 11.2 with an ID `L1` to `L11`; all are drafts pending the maintainer's MD2 round, which happens before SOL-A1 freezes.

## 1. Decisions

| ID | Decision | Section |
|---|---|---|
| D1 | The pin chain on `36cd9d4a` is SOL-A1, then SOL-T, then SOL-C, each in its own batch. SOL-A1 is the blanket-null bump with W/D byte-equal (gate decision RA1). SOL-T installs the melt-point admissions and changes W/D. P8 holds no pin and is outside the chain. P3's keyhole-leg bump changes depth and comes later in its own batch. | 3.1, 3.2 |
| D2 | Bands, `DEPTH_BIAS_BANDS_ID`, demo snapshots and dated records leave the blind lanes. A records lane (R-lane) regenerates them once per batch on the batch head: restamp after SOL-A1 and SOL-C, the full bands run after SOL-T. | 3.6, 3.7 |
| D3 | W/D invariance for SOL-A1 and SOL-C is shown without measured rows: parity cases, a synthetic float.hex snapshot tool, the HTTP digest guard's geometry. SOL-T claims no invariance; it records every moved value. | 3.5 |
| D4 | The four legacy helpers in `solidification_front.py` are retired. G12 is rewritten with named PDAS pairs that a mutant cannot pass (RA5). The parity harness refuses error observations in all three shapes the harness produces (F10). | 6 |
| D5 | Envelope v1 lives in `python/quantity_envelope.py` outside the thermal manifest, is declared in `module_contract.py` and emitted to TypeScript. Manifest files emit codes and structured parameters, never English sentences (RA4). | 4.1 |
| D6 | Envelope v1 carries the maintainer's decisions 1 and 2 (`.orchestra/GOAL.md`, "Label and data decisions"): a per-value `sourceEvidenceKind` under a container `moduleEvidenceCeiling: "screening-only"`, the label rule with named inputs and Unresolved precedence, and request process values excluded. The per-value fields match P8's encoding (P8 contract `e6934ffd`, 6.1 to 6.3, 13.5, 13.12). MD1 is closed. | 4.2, 4.3 |
| D7 | One closed quantity status vocabulary: `computed`, `partial`, `unavailable`, `failed`, `not-requested`, with a mapping for every served status, kinetics and segregation included. | 4.5 |
| D8 | Reason codes: the 21 SPEC:34 codes plus four integration codes. | 4.6 |
| D9 | Migration is atomic per producer lane; no dual-read. | 4.8 |
| D10 | Model IDs change with values, schema IDs with shape. `BUILD_JOB_SOLVER_REVISION` v26 at SOL-A. CALPHAD gets `solidificationChainIdentity` keyed on CRLF-normalised TDB bytes. | 5 |
| D11 | CET source facts become `equationRead`, `algebraReproduced`, `printedLimitComparison`. | 4.7 |
| D12 | `gr-solidification` accepts the five canonical alloy IDs and answers per quantity; an unknown alias is refused with `unknown-alloy-alias`. | 7.1 |
| D13 | The transient and OpenFOAM liquidus G, R and cooling producers (RA3) are scoped out at SOL-A1 with a visible label and an MD5 line, and contained at SOL-T under the reference-case harness decision that SOL-T needs anyway. | 7.1, 7.4 |

## 2. Code facts this plan rests on

1. The thermal manifest has 36 files (`python/lpbf_simulation.py:44-81`), including `lpbf_thermal_solver.py` (:73) and `solidification_front.py` (:76). Changing either moves pin `36cd9d4a` (`python/lpbf_implementation_fingerprint.expected:1`).
2. Front outputs reach the thermal result only through `solidificationKinetics`: `evaluate_solidification` is called at `lpbf_thermal_solver.py:1195-1204`, read at :1211-1217 and written at :1563-1591. Geometry is computed before that call; `compose_verdict` (`lpbf_build_job_solver.py:483`) reads no solidification, microstructure, segregation or kinetics block. A front-only change therefore cannot move W, D, the enthalpy index, the regime or the verdict.
3. The liquidus itself does drive W/D (re-gate RA1): `_liquidus_extent` (`lpbf_thermal_solver.py:696-737`, called at :1078), the enthalpy denominators (:975, :1029) and the Kirchhoff kernel mean (:316, `python/four_alloy_materials.py:563-585`). Installing new endpoints (SOL-T) moves W/D, including the recorded IN718 reference numerics that the harness never lets drift (`python/tools/lpbf_parity_check.py:1567`, :1581-1587, :1646-1647).
4. Objects bound to the pin: 25 goldens in `python/golden/lpbf_parity/` (`recordedImplementationHash`), `GOLDEN_FINGERPRINT` (`python/test_lpbf_parity_golden.py:60`), `data/calibration/lpbf-meltpool-error-bands-v1{,.summary,.rows}.json`, `demo/snapshots/*`, the dated records `docs/LPBF_*_2026-10-14_p7b-sourced-constants.*` and `docs/LPBF_LEADERBOARD_2026-10-14.json`.
5. CI-run checks bound to it: `tests/lpbf-error-bands.test.tsx:59-62`, `tests/demo-snapshots.test.ts:65-78`, `tests/demo-gate.test.tsx:108-111` (snapshots against bands, not against the pin), `tests/depth-bias-warning.test.tsx:13` with `src/utils/depthBiasWarning.ts:19`, `python/test_lpbf_error_bands.py:316-321`, `python/test_lpbf_depth_bias.py:199`, `python/test_lpbf_calibration_frozen.py:55-59` (HTTP digests) and T-FRZ-3 at :97-115 (frozen-file diff against the merge base, red on any bump branch until merge).
6. The bands tool cannot restamp (`python/tools/lpbf_error_bands.py:292-297`); its full run loads measured rows (:69-101), and the committed row table carries measured `width_um` and `depth_um` (:140-143).
7. Re-recording demo snapshots reads measured rows too: `demo/snapshots/index.json` includes the process-window request with an overlay, which loads published single tracks (`python/lpbf_process_window.py:53-61`, :254, :286-287, :310); snapshot `3609eb6351a5a4cf.json` holds the KU Leuven IN718 and NIST AMB2022-03 overlays.
8. Parity: G11 (`lpbf_parity_check.py:1118-1146`) and G18 (:720-767) record whole-result digests plus `geometry_um`. G12 (:1148-1211) observes the four legacy helpers (:1184-1193) and `evaluate_solidification` with ignored keywords (:1196-1201). Error shapes differ by case: `observe_value` stores `{"error": text}` under the same key (:232-235); G11 writes `meltpool.{i}` = `{"error": text}` while the success keys disappear (:1139); G16 writes a plain string under `<prefix>.error` (:549-554). `evaluate_drift` (:1754-1806) accepts any of these under a matching entry. Guarded paths: `scripts/check_ceiling_review.py:39`, :44-47, :49, :54-55.
9. Each pin move makes stored machine calibrations stale (`python/lpbf_machine_calibration.py:525-529`) and invalidates the process-window LRU (`python/lpbf_process_window_cache.py:68`). Adding any new `python/*.py` file changes the legacy broad cache hash (`python/lpbf_simulation.py:269-281`, worker keys at `python/lpbf_worker.py:949`), so cached build-job and GPU-pilot worker jobs recompute once; no served value changes.
10. P8 holds no pin. Its research route runs outside `calculate_meltpool_physics`, touches no manifest file, pin, golden, Build Job revision or allowlist, and offers no channel to served code (P8 contract `e6934ffd`, 0 item 4, 1.5, 10.1). Its P-1 and P-3 checks compare against merge-base values (10.2), its former R-ISO-2 diff guard is the branch-scoped P-2 tool over the P8 commit range (10.3), and its R-TR-11 transport fixture uses a stubbed identity (13.11 item 3). Its research context reads served `liquidus_C` and Kirchhoff means; R-CTX-1 pins literals that SOL-T moves (re-gate RT7).
11. Second and third served producers of liquidus G, R and cooling (re-gate RA3): the transient CPU path sums liquidus-crossing events on the registry liquidus (`python/lpbf_simulation.py:392-411`, called at :751) and writes the event means into `metrics` (:803-810, with a single-mesh note at :822-830); the OpenFOAM path writes the same three keys (`python/lpbf_openfoam.py:177-179`). They render generically at `src/components/3d-distortion-lab/LpbfEngineeringSimulation.tsx:674`, a panel embedded in `MeltPool3DCrossSectionLab.tsx:633`, and feed the convergence study's metric list (`lpbf_simulation.py:1131-1132`) and `python/tools/lpbf_validity_envelope.py:112-113`. `*.key.metrics` is protected reference numerics in G1, G2 and G4 (`lpbf_parity_check.py:1567`, :1582).
12. SDK facts: `EVIDENCE_TYPES` (`python/module_contract.py:30-37`, `src/types/research.ts:2`), pending-oracle cap (:54-58), `MATURITY` (:78), `within_ceiling` (:136-141), status-key rules (:293-296, :332-335); both solidification contracts declare `emits=()` and the cap (`python/module_contracts_calphad.py:147-152`, `python/module_contracts_lpbf_secondary.py:37-45`); the gr `evidence` object rides outside the declared fields (`module_contracts_lpbf_secondary.py:243-247`). Governing prose for evidence labels: `README.md:106-110`.
13. Cross-tier fixtures already exist for Build Job blocks (`python/test_lpbf_build_job.py:116`, :124, :466); gr parser tests use synthetic payloads only (`tests/lpbf-gr-solidification.test.tsx:19-48`).

## 3. Bump plan

### 3.1 Pin-moving changes

| Order | Bump | Files that move the pin | W/D | Batch | Owner |
|---|---|---|---|---|---|
| 1 | SOL-A1, blanket-null front containment | `python/solidification_front.py`, `python/lpbf_thermal_solver.py` (:1195-1217, :1563-1591 only) | byte-equal | W1 | Opus |
| 2 | SOL-T, melt-point endpoint installation (SPEC A2.2 records as settled by A3.C, RT1 to RT8) | the alloy authority (`python/four_alloy_materials.py`, `python/lpbf_thermal_solver.py` secondary table, `python/lpbf_material_registry.py`), plus `python/lpbf_simulation.py` and `python/lpbf_openfoam.py` for the D13 containment | changes | T | Opus |
| 3 | SOL-C, local coupling and opt-in field diagnostic | `python/solidification_front.py`, `python/lpbf_thermal_solver.py` | byte-equal against the SOL-T head | W2 | Opus |
| later | P3 keyhole leg (conditional) | per its registration | changes | its own | P3 lane |

Not in the chain (no pin move): P8 (fact 10), SOL-K (kinetics), SOL-B (CALPHAD), every TypeScript change. SOL-B and SOL-K carry their own identities (section 5) and the phase6a golden ledger.

### 3.2 Ordering rules

1. Gate decision RA1, recorded: SOL-A1 stays blanket-null with W/D byte-equal; endpoint admission is the separate bump SOL-T in its own W/D-changing batch, after SOL-A1 and before SOL-C. Reasons from the re-gate: admissions produce no user-visible number at SOL-A1 (A2.4 refuses whole-front medians and per-sample tuples arrive with SOL-C); the admissions are not settled (RT1 to RT7); installing them moves IN718 reference numerics, forces the full bands run on measured rows and moves P8's R-CTX-1 literals.
2. SOL-T starts only after Astra's Amendment 3 closes RT1 to RT7 and a narrow Opus physics check passes, and after the reference-case harness decision of 6.4.
3. SOL-C starts only after RC1 (its own served opt-in channel, designed jointly with the P8 architect, because P8 offers none) and RC2 (the stronger kinematics oracle).
4. P8 merges whenever its own gate allows, before or after any SOL bump. Because P8 compares against merge-base values and holds no pin, no SOL bump record is re-made because of P8, and P8 needs no edit when a SOL pin moves. The former swap rule is withdrawn.
5. A SOL bump record is re-made only when another pin move lands first. Only one branch holds the pin at a time; a bump branch is cut from the previous bump's head.
6. P3 waits until any open SOL batch has run its R-lane and been pushed, and until P8's onset-kernel correction has a served path of its own (re-gate RC1). Its batch uses the full bands run.

### 3.3 Per-bump outputs

1. Pre-bump: synthetic snapshot at the from-head (3.5).
2. Code change and its self-contained tests.
3. Guarded commit: the new pin.
4. From `python/`: `python -B tools/lpbf_bump_record.py --from-revision <from-head> --with-parity-check --slow --expect-drift <exact keys>` against the goldens still recorded at the from-hash; record JSON, `.reasons.md` and `.expect-drift.txt` under `docs/LPBF_IMPLEMENTATION_BUMP_<date>_<id>.*`.
5. Guarded commit: 25 goldens re-recorded (`--record --force --twice --slow`), `GOLDEN_FINGERPRINT`, `HTTP_GOLDEN` with a reason line (`python/test_lpbf_calibration_frozen.py:40-59`); then `--check --slow` gives 25 PASS.
6. Pin-literal sweep (RA6): `git grep -n <old pin>` and `git grep -n servedImplementationFingerprint -- tests python/golden demo data`; every hit is regenerated in this bump, handed to the R-lane (3.6) or recorded as dated history. A committed fixture that binds the live served fingerprint is a defect of that fixture's owner; P8's R-TR-11 is stubbed and is expected to give no hit.
7. Post-bump snapshot compared with the pre-bump one (SOL-A1, SOL-C) or the moved-value record (SOL-T).
8. PROOF.md entry: scope, changed paths, drift keys, known reds of 3.6. No accuracy wording.

### 3.4 SOL-A1 expected drift

Exact entries, no globs:

1. `g11_build_job_meltpool:meltpool.0.typedSha256`, `meltpool.0.canonicalSha256`, the same two keys for `meltpool.1` (Ti64, today carrying the martensite note) and `meltpool.2`.
2. `g18_in625_latent_heat:meltpool.in625`.
3. G12: the four removed observations, the changed `solidification.evaluate`, the new first appearances of 6.3, each named exactly.
4. Every `geometry_um`, `peakTemperature_C`, every `*.key.metrics` and every other case must PASS. Any other drift stops the bump; it is enumerated and justified before recording.

SOL-T's list is not predeclared here: it moves reference numerics, so its record follows the harness decision of 6.4 and names every moved key; nothing is absorbed by a glob.

### 3.5 Unchanged-output evidence without measured rows (SOL-A1, SOL-C)

1. Parity: everything other than the 3.4 keys PASS.
2. `python/tools/lpbf_wd_invariance.py` (Phase 0, non-manifest): `--capture OUT` calls `calculate_meltpool_physics` and `compose_verdict` directly (never the process-window endpoint, whose overlay reads measured rows) for the five primary alloys x three kernels x the 49-cell synthetic grid of the P7b spec (P 80 to 540 W, v 300 to 2400 mm/s, beam 80 um, preheat 80 C, layer 40 um, hatch 100 um), recording float.hex of `meltPoolGeometry`, `processParameters`, `processWindowMap.grid`, `defectDiagnostics`, regime, `extentStatus` and verdict class. `--compare A B` requires byte equality.
3. `HTTP_GOLDEN` digests move; the geometry inside is covered by item 2.
4. No bands row, loader or overlay is read; the R-lane restamp repeats the invariance on the published input tuples.

### 3.6 CI-bound artefacts and known reds

| Artefact or check | State on a bump branch | Handled by | When |
|---|---|---|---|
| Bands files | stale; `tests/lpbf-error-bands.test.tsx:59-62` and `python/test_lpbf_error_bands.py:316-321` red | R-lane: `--restamp` (W1, W2), full run (T) | once per batch, on its head |
| `DEPTH_BIAS_BANDS_ID` | unchanged; its two checks stay green | R-lane, same commit as the bands | same |
| Demo snapshots | stale; `tests/demo-snapshots.test.ts:65-78` red; `tests/demo-gate.test.tsx:108-111` green while both are stale | R-lane, `npm run demo:snapshots` then `npm run demo:snapshots:determinism` | after the bands |
| Dated records | stale; the keyhole benchmark test skips (`python/test_lpbf_keyhole_benchmark.py:167-170`) | R-lane, regenerated as dated history | same |
| T-FRZ-3 (`python/test_lpbf_calibration_frozen.py:97-115`) | red by construction on every bump branch | owner: the bump owner names it in the bump record; the batch gate accepts it as the single named red and checks the record's changed-path list instead; the merge clears it | at the gate |
| P8 R-ISO-2 (now P-2) | not run on SOL branches; its range is the P8 commit range only, so SOL-A edits to files on its list (`lpbf_build_job_solver.py`, `lpbf_gr_solidification.py`, `lpbf_solidification_microstructure.py`) never enter it | owner: P8 architect (tool scope); SOL integration owner confirms no permanent SOL test depends on it | none |
| P8 R-TR-11 fixture | stubbed identity; unaffected | owner: P8 lane; the SOL sweep of 3.3 item 6 catches a regression | each SOL bump |
| Stored machine calibrations | stale for users | MD5 notice | at push |

Apart from T-FRZ-3, a batch with any of these red is not merged.

### 3.7 Records lane (R-lane)

1. The only lane that opens the bands row table, runs dataset loaders or records the overlay. Its agent is not reused for blind depth work; the BOARD exposure log records it.
2. `python -B python/tools/lpbf_error_bands.py --restamp [--date D]` (written in Phase 0 by Sonnet, synthetic tests only): checks the committed artefact against its own hash, re-solves every committed row, requires `pred` (W, D, status) and `enthalpy` equal at the committed precision (`eb.round_sig`, tool :144), writes nothing and lists row IDs only on any difference, otherwise rewrites the identity fields and requires the recomputed cells byte-equal to the old ones.
3. W1 and W2 sequence on the batch head: restamp; `DEPTH_BIAS_BANDS_ID`; demo snapshots and determinism check; dated records; the offline note of F13 (`python/lpbf_public_datasets.py:1108`, which sits beside measured NIST rows); full unit suite and CI Python list; one explicit-path commit.
4. Batch T: the full tool (`npm run lpbf:bands`) with the before and after review of every moved cell, as P7b recorded it; restamp is not allowed (re-gate RT8).
5. A restamp refusal means a W/D-invariant bump moved W/D; the batch stops and the gate reopens that bump.

### 3.8 Batches (re-gate MD4 recommendation)

1. W1: Phase 0, SOL-A with SOL-A1, SOL-K, and SOL-B if its Amendment 3 check has passed. R-lane restamp, batch gate, trailer run, push.
2. T: SOL-T alone. R-lane full bands run, batch gate, trailer run including the Ceiling-Review trailer for the reference-case harness decision, push. P8's owner re-pins R-CTX-1 in the same batch (12.4).
3. W2: SOL-C and anything left. R-lane restamp, gate, trailer, push.
4. P3: its own batch.

P8 is pushed in whatever batch the lead assigns; it never shares a guarded commit with a SOL bump.

## 4. Quantity envelope contract

### 4.1 Placement

1. `python/quantity_envelope.py` (new, stdlib-only, outside the manifest): closed vocabularies (statuses, reason codes with sentence templates, quantity definitions with SI units, uncertainty kinds, fraction bases, `SOURCE_EVIDENCE_KINDS`, the input provenance kinds, leaf roles), builders, the label rule `source_label(inputs)` (4.3) and `envelope_problems(obj, declaration)`.
2. `python/module_contract.py`: frozen dataclasses `QuantityDeclaration(path, definition, unit, statuses, source_evidence_kinds, reason_codes, fraction_basis=None, leaf_role="derived")` and `ObservationDeclaration(path, observable, source_evidence_kinds)`; `Operation` gains `quantities` and `observations`. Checks: `"Measured"` is legal only in an `ObservationDeclaration`; unknown statuses, codes or kinds fail; paths start at an output field; quantity and observation paths do not overlap. The container ceiling is checked with `within_ceiling` against the contract ceiling.
3. `python/module_registry.py` emits the declarations into `src/generated/moduleRegistry.{json,ts}` and the vocabularies, sentence templates included, into a new `src/generated/quantityEnvelope.ts`; `python scripts/emit-module-registry.py --check` covers both.
4. `src/data/quantityEnvelope.ts` (new): `checkedQuantity`, `checkedObservation` and `checkedValueProvenance`, the last shared with P8's research parser (12.5).
5. Manifest rule: `solidification_front.py` and `lpbf_thermal_solver.py` never import `quantity_envelope.py` (the closure test at `python/test_lpbf_implementation_fingerprint.py:113` would pull it into the manifest). They emit codes, parameters and provenance kinds as literals; `python/test_quantity_envelope_payloads.py` runs `envelope_problems` on the real thermal payloads.
6. Text placement (RA4): no English sentence is emitted from a manifest file after SOL-A1. The existing sentences in `solidification_front.py` (`INTERFACE_LABEL` and the two P6 reasons at :37-45, `PDAS_BASIS` and the two unavailable reasons at :70-81, `_DISCLAIMER` at :311-315) become registry texts keyed by code. Python consumers attach text with `quantity_envelope.reason_text(code, params)`; the UI uses the generated table. A wording change after SOL-A1 then moves no pin.
7. One placement (F14): every object holding a `quantities` map is a container and carries `quantityEnvelopeSchema`, `moduleEvidenceCeiling` and `moduleMaturity` (the registry label, echoed). Nothing else carries them; a response is a container only when its top level holds the map.
8. The thermal solver and Build Job sit in the legacy `3d-distortion-lab` contract, so their envelopes are enforced by the payload test and the TypeScript parsers, as P8 does for the same host (P8 contract 6.3).

### 4.2 Wire format v1

Container keys: `quantityEnvelopeSchema: "metalliksa-quantity-envelope-1"`, `moduleEvidenceCeiling: "screening-only"`, `moduleMaturity`, `quantities`, optional `observations`, optional `inputProvenance` (map from input name to an input record).

A quantity:

| Key | Rule |
|---|---|
| `status` | one of 4.5. |
| `value` | SI number, or an object of SI numbers for model alternatives; `null` unless `status` is `computed` or `partial`. Display units only in the UI. |
| `unit` | closed unit string, present when `value` is null. |
| `quantityDefinition` | registry ID (`liquidus-front-thermal-gradient`, `liquidus-front-normal-speed`, `liquidus-front-cooling-rate`, `liquidus-front-g-over-r`, `pdas-model-alternatives`, `sdas`, `front-morphology`, `solid-state-transformation`, `cet-class`, `laves-trapped-scheil-fraction`, `scheil-phase-inventory`, `scheil-residual-liquid`, `critical-temperature`, `lsw-mean-radius`, `precipitation-strengthening`, `user-threshold-isotherm-kinematics`). |
| `leafRole` | P8's roles: `derived` for computed quantities, `requestInput`, `physicalInput`, `softwareLimit`, `convention`, `indexConvention`. |
| `sourceEvidenceKind` | per value, decision 1: `"Literature estimate"`, `"User input"`, `"Unresolved"`, or null when `value` is null or the leaf is not evidence. Never `"Measured"` on a quantity. Not compared with the ceiling. |
| `dependsOn`, `weakestInputs`, `labelSources` | as in P8 6.2: determining inputs; the inputs behind Unresolved or User input; the locators behind Literature estimate. |
| `reasons` | list of `{code, params, parent}`; `parent` names the blocking input and its provenance kind. No `text` from manifest producers (4.1 item 6). Empty only for `computed`. |
| `numericalStatus` | `{state, settings, residuals}`, state in `not-assessed`, `unresolved`, `refinement-passed`, `failed`. |
| `physicalValidation` | `{status: "unvalidated", experimentalValidation: false, productionReady: false}`. |
| `sources` | `{id, locator, readLevel}` with `readLevel` in `primary-read`, `secondary-read`, `repository-attribution`; replaces block-wide DOI fields. |
| `assumptions`, `validity`, `uncertainty`, `fractionBasis`, `identity` | as in Revision 0: uncertainty kinds `model-alternatives`, `parameter-sensitivity`, `numerical-refinement`, `calibrated-prediction-interval`, `not-quantified`; fraction bases `mole-of-atoms`, `mass`, `volume`, `reaction-progress`, `microconstituent`; identity `{input, model, parent}`. |

Input record: P8's `ResearchInputProvenance` keys (P8 contract 6.3), with the same closed `kind` enum: `sourceDefault`, `sourceModelAssumption`, `sourcedAlternative`, `alloyTransfer`, `modelConvention`, `declaredAssumption`, `legacyEstimate`, `userInput`, `followsInput`, `derived`.

### 4.3 Evidence labels (decisions 1 and 2; MD1 closed)

1. Ceiling: every container says `screening-only`; no ceiling is raised (decision 1). `PENDING_ORACLE_CEILING` (`module_contract.py:54-58`) stays.
2. Label rule (decision 2), implemented once in `quantity_envelope.source_label`: over the determining inputs, any `declaredAssumption` or `legacyEstimate` input (directly or through a followed rule) gives `"Unresolved"` naming them; otherwise any `userInput` gives `"User input"` naming them; otherwise `"Literature estimate"` with `labelSources`. Unresolved takes precedence. A typed value equal to its sourced default (float.hex after unit conversion) keeps the sourced kind.
3. Determining inputs are physical and coefficient inputs. Request process values P, v, d and T0, conventions, solver settings and software limits never make an output User input (the lead's decision on P8 item I-1, now in force for both lanes). Their echoes carry `leafRole: "requestInput"`.
4. `"Measured"` appears only on observation records: transcribed measurements with their own observable and process. No quantity, and no input used to compute one, reads `"Measured"`.
5. Melt-point ledger admission classes (`docs/research/scripts/solidification_melt_point_ledger.py`, records at `024e30cd`; class stems are mapped, so a renamed prefix keeps the mapping):

| Ledger class stem | Records | Input `kind` | `sourceEvidenceKind` of the endpoint input | Dependent outputs |
|---|---|---|---|---|
| `fixed-front-literature-model` | MP01 Ti64 (Gan 2021), MP04 IN625 (Sabau 2020) | `sourceModelAssumption` | Literature estimate, scope "nominal alloy model convention" | rule 2 |
| `fixed-front-explicit-family-transfer` | MP02 AlSi10Mg (Brandt and Neuer 2007, Al-9Si-0.6Mg), MP03 IN718 (Pottlacher 2002 DTA batch) | `alloyTransfer`, status `extrapolated` | Literature estimate with the transfer scope text; **never Measured**, although the source measured its own batch | rule 2; the transfer scope travels to API, UI, CSV and probes (A2.1) |
| `refusal-default-liquidus; operational-proxy-only` | MP05 316L (Pichler) | not an input of the default front | the served 316L liquidus stays `declaredAssumption`, so dependents are Unresolved or null | MP05 may appear as an observation record (`"Measured"`, observable "DSC operational temperatures of evaporating SRM316L", comparability context-only) or as the input of a separately named operational-isotherm demonstration |
| `datasheet-disclosure-only` | MP07 | observation only | Literature estimate on the observation record | never an input |
| alternatives (MP02 cooling, MP03 fast pulse, MP06 Cieslak family) | | `sourcedAlternative` | Literature estimate | sensitivity arms only, never the default |
| nothing installed (until SOL-T) | all five | current served kinds: AlSi10Mg `legacyEstimate` (`unsourced-estimate`), IN625 `legacyEstimate` (secondary-unreconciled), Ti64, IN718 and 316L `declaredAssumption` (no provenance entry) | Unresolved | null at SOL-A1 (blanket rule) |

6. Retired strings: `"evidence": "unvalidated"` (`python/calphad_solver.py:2172`, :2258) becomes a container ceiling plus per-value labels plus `physicalValidation.status`; `Literature estimate (screening): ...` (`python/lpbf_solidification_segregation.py:84`, :687, :904) becomes `sourceEvidenceKind: "Literature estimate"` with `labelSources` under the screening-only ceiling; `Measured (literature, as-built LPBF IN625); simulations listed separately` (:1149) becomes an observation record; the gr response-level `evidence` object (`python/lpbf_gr_solidification.py:461`) stays as the SDK-reserved object.
7. CALPHAD inputs (SOL-B): `databaseStatus` `assessment` gives `sourceDefault` for the database, `test-fixture` gives `declaredAssumption`, `user-supplied` gives `userInput`; a composition preset with a recorded source is `sourceDefault`, without one `declaredAssumption`, an edited composition `userInput` naming the edited elements.
8. Values at SOL-A1: every default front quantity is null with reason `missing-source-constant`, `parent` the liquidus input and its kind; `sourceEvidenceKind` null. A synthetic admitted-liquidus test fixture (F16) exercises the non-null path with Literature estimate and its sources, without serving it.

### 4.4 Maturity

No per-quantity maturity. Containers echo the registry label (4.1 item 7), which stays `Research`; `Production` cannot be expressed (`MATURITY`, :78). A retained instructional demonstration needs its own seed entry in `python/module_registry_seed.json`. Recommendation: retire the browser numerical phase and Scheil prediction controls.

### 4.5 Status mapping

| Served status | Where | Envelope |
|---|---|---|
| `available` | worker and gr cells (`module_contracts_lpbf_secondary.py:185`, `lpbf_gr_solidification.py:41`); segregation (`lpbf_solidification_segregation.py:639`, :843, :1147) | `computed` |
| `screening-fallback` | `lpbf_solidification_microstructure.py:149`, :188 | `unavailable`, `invalid-interface-sample` |
| `degenerate-floor` | same module :102-111, :179-188 | removed: physical values `computed`, zero or nonfinite `unavailable` with `invalid-interface-sample` |
| `unavailable` | everywhere | `unavailable` with a code |
| `error` | gr cell | `failed`, `solver-error` |
| `computed` | segregation :429, :457, :479 | `computed` |
| `outside-model` | segregation :433 | `unavailable`, `outside-source-model-domain` |
| `not-modelled` | segregation :826 | `unavailable`, `missing-source-bound-model` |
| `pycalphad-scheil-gulliver` | `calphad_solver.py:2143`, :2235 | `computed` only when phase and atom inventories close; otherwise `partial` |
| `incomplete` | `calphad_solver.py:2235` (kernel status at :1608) | `partial`, `residual-liquid-at-termination` |
| `bisected`, `bracketed-by-grid` | `criticalTemperatureStatus` (`module_contracts_calphad.py:100-110`) | `computed`; method in `numericalStatus.settings` |
| `heuristic-phase-name` | beta transus, sigma risk | `unavailable`, `missing-source-bound-model` |
| `screening-constant` | sigma risk temperature | `unavailable`, `missing-source-constant` |
| `li1998-additivity-first-diffusional-start`, `li1998-additivity-screening`, `computed-grange-1961-screening`, `computed-li-1998-screening`, `computed-andrews-kung-rayment-1982-screening`, `no-floor-li-1998-law` | `kinetics_ttt_cct_solver.py:104`, :110-113, :115 | `computed`; the method stays in `numericalStatus.settings` |
| `athermal-martensite-no-diffusional-start-above-ms` | :105 | `computed` with a categorical value |
| `unavailable-kinetics-model-steel-only` | :98 | `unavailable`, `missing-source-bound-model` |
| `unavailable-composition-outside-li-model-range`, `unavailable-austenitizing-at-or-below-ae3` | :99, :106 | `unavailable`, `outside-source-model-domain` |
| `unavailable-registry-placeholder`, `registry-screening-value` | :100, :101 | `unavailable`, `missing-source-constant`; a registry value may survive as metadata only (SPEC:172) |
| `unavailable-fractions-not-computed`, `unavailable-not-modelled`, `generic-constants-illustrative` | :107, :114, :103 | `unavailable`, `missing-source-bound-model` |
| `unavailable-no-predicted-hrc` | :108 | `unavailable`, `parent-unavailable` |
| `unavailable-aging-temperature-at-or-above-solvus` | :102 | `unavailable`, `outside-source-model-domain` |
| `static-text-not-a-calphad-calculation` | :109 | not a quantity: a `convention` leaf with null label |
| `"not requested"` | `CALPHADMultiComponentStudio.tsx:1618` | `not-requested`, code `not-requested` |
| `pdasOutOfRange: true` | `solidification_front.py:117-122` | `unavailable`, `outside-source-model-domain` |

Build Job gate statuses (`pass`, `fail`, `advisory`, `lpbf_build_job_solver.py:663-668`) belong to the verdict ladder and are out of scope.

### 4.6 Reason codes

The 21 SPEC:34 codes plus `parent-unavailable`, `solver-error`, `insufficient-sample-support` (the P6 fewer-than-3 case, `solidification_front.py:43-45`) and `quarantined-legacy-path` (`python/lpbf_worker_rpc.py:16-20`, `openfoam/meltPoolFoam/solidificationModel.H`). Each code has one sentence template in the registry (literal group L1).

### 4.7 CET source facts

`equationVerified` (`python/lpbf_cet_screening.py:65`, :94, :114, :273; `src/data/lpbfGrSolidification.ts:278`, :285; `src/services/lpbfGrSolidificationService.ts:60-61`, :139-140) is replaced by `sourceChecks.equationRead` (`read` or `not-read`, locator), `sourceChecks.algebraReproduced` (`reproduced`, `not-reproduced`, `not-attempted`, with the recomputing test's name, checked to exist) and `sourceChecks.printedLimitComparison` (`agrees`, `disagrees`, `not-available`, `not-attempted`, printed and computed values, tolerance). Knapp: read, reproduced, agrees within SPEC gate 4. Polonsky: read, reproduced, `not-available`. Gaumann 2001: `not-read`. `_set_complete` (:160-169) also requires `read`. Display labels are literal group L4. The `constants_override` branch (:255-256) becomes a test helper.

### 4.8 Contract, registry and TypeScript migration

1. `CONTRACT_VERSION` 0.1.0 to 0.2.0 (`module_contracts_calphad.py:13`, `module_contracts_lpbf_secondary.py:21`); regenerate `docs/modules/phase-diagram.md` and `docs/modules/solidification-microstructure.md`.
2. Schemas: `lpbf-gr-solidification-1` to `-2` (`lpbf_gr_solidification.py:37`, `src/data/lpbfGrSolidification.ts:20`); `lpbf-solidification-segregation-1` to `-2` (`lpbf_solidification_segregation.py:80`); `lpbf-solidification-microstructure-2` on the worker response; `calphad-minimize-2` on CALPHAD.
3. Real payload fixtures (Phase 0, regenerated per lane): `python/tools/solidification_payload_fixtures.py --write` builds `tests/fixtures/solidification-payloads/*.json` from the real Python functions on synthetic requests (thermal blocks for five alloys and a keyhole-leg case, Build Job blocks via the generators at `python/test_lpbf_build_job.py:78-99`, :439-459, gr point and 2 x 2 map for IN718, a Ti64 point, an unknown alias, worker results and a `cfdResult` refusal, CALPHAD results for four routes). `python/test_solidification_payload_fixtures.py` asserts committed equals regenerated; TypeScript parses every fixture plus one mutation per rule.
4. No dual-read; older payloads render the existing "older solver result, recompute" path (`useLpbfBuildJobStore.ts:219`); restart `lpbf_worker.py` at rollout.
5. Hand-written vocabularies replaced by generated ones: `GR_CELL_STATUSES` (`lpbfGrSolidification.ts:17`), `KNOWN_STATUS` (`BuildJobMicrostructurePanel.tsx:47`), `solidificationOutcome.ts:19-27`, the alloy check (`lpbfGrSolidification.ts:266`), the Hunt maps (:116-125).
6. P8 alignment: one vocabulary in `quantity_envelope.py`; P8's `p8_input_provenance.KINDS` and its label strings must equal it. The equality test is `python/test_lpbf_research_label_vocabulary.py` (a `test_lpbf_research_*` name, so R-ISO-1 lets it import both sides); the lead assigns it (12.5).

### 4.9 SDK review list

`TODO(maintainer-review)` items 1 (rank order, `module_contract.py:48-52`) and 3 (cap, :54-58) stay open; decision 1 removed the need to change either for this chain. MD1 is closed.

## 5. Identities and caches

| Identifier | Location | Changes at | Notes |
|---|---|---|---|
| Implementation pin | `python/lpbf_implementation_fingerprint.expected:1`, `python/test_lpbf_parity_golden.py:60`, 25 goldens | SOL-A1, SOL-T, SOL-C (P3 later); never P8 | guarded |
| `MODEL_ID` | `python/solidification_front.py:35` | v2 at SOL-A1, v3 at SOL-T (new liquidus parents), v4 at SOL-C | read at `lpbf_thermal_solver.py:37`, `lpbf_gr_solidification.py:414`; the UI fallback literal at `MeltPool3DCrossSectionLab.tsx:1232` is removed |
| Liquidus parent identity | new field in each front container, SOL-T | SOL-T | ledger record ID, source hash, admission class stem, transfer scope; a changed endpoint or class invalidates caches and children even when temperatures agree (A2.4) |
| `BUILD_JOB_SOLVER_REVISION` | `python/lpbf_job_cache.py:25`, `src/store/useLpbfBuildJobStore.ts:24`, `python/test_lpbf_build_job.py:666-689`, `tests/build-job-kinetics-panel.test.tsx:27-50` | v26 at SOL-A, v27 at SOL-T, again at SOL-C if Build Job output changes; P8 does not touch it | job cache key `lpbf_job_cache.py:111` |
| gr provenance | `lpbf_gr_solidification.py:463-464` | SOL-A | `frozenFilesModified` removed; `implementationHash` from the cached helper (`lpbf_process_window_cache.py:34-39`), `solidificationModelId`, `buildJobSolverRevision` |
| CET `MODEL_ID` | `lpbf_cet_screening.py:38` | v2 at SOL-A | |
| Segregation IDs | `lpbf_solidification_segregation.py:80-81`, :685, :902 | schema at SOL-A; model IDs only if values change | |
| `solidificationChainIdentity` | `calphad_solver.py` provenance (:2505-2512) | SOL-B | canonical-byte closure hash (`lpbf_source_identity.fingerprint_sources`), pycalphad and comparator versions, `tdbCanonicalSha256`, phase exclusions, settings, original and solved composition, envelope schema |
| TDB identity (minor 20, T2) | new | SOL-B | `tdbCanonicalSha256`: raw bytes with each CRLF pair replaced by LF, no decode; the identity and cache key. `tdbRawSha256`: provenance constant taken from the committed blob (`git show HEAD:<path>`), never from a working-tree file whose newlines depend on checkout. Decode replacements counted (`python/calphad_model_cache.py:66-68`); an admitted database with a nonzero count is refused |
| Chain closure test | `python/test_solidification_chain_identity.py` | SOL-B | import closure of `calphad_solver.py` inside the identity list |
| CALPHAD request and export | `CALPHADMultiComponentStudio.tsx:225-274`, :374-377, :483-490, :557-563; `src/utils/calphadDisplay.ts:150-170` | SOL-B | export only when the current request equals the answered one; file name and header are literal group L5; the ODbL line follows MD3a |
| Legacy broad cache hash | `python/lpbf_simulation.py:269-281` | any lane adding a `python/*.py` file | cached worker jobs recompute once |
| Process-window LRU | `lpbf_process_window_cache.py:68` | each pin move | automatic |
| `scheil==0.3.0` | `python/requirements-lpbf.in` | SOL-B | comparator only (T2) |

## 6. Parity harness decisions

1. Error rule (Phase 0.2, Opus, guarded), covering the three shapes of fact 8 (F10): under every entry, glob or exact, `evaluate_drift` reports a problem when a value becomes `{"error": ...}` at the same key; when a new key's value is `{"error": ...}` (the G11 `meltpool.{i}` shape, whose success keys vanish at the same time); and when a key ending in `.error` appears or changes (the G16 shape). A deliberate removal deletes the observation, which appears as `<missing>` and needs an exact entry. Unit tests for all three shapes go into `python/test_lpbf_parity_golden.py`.
2. Retire `hunt_morphology` (`solidification_front.py:167-174`, cuts :49-52), `hunt_lu_pdas_um` and `HUNT_LU_A_SI` (:56, :177-181), `kirkwood_sdas_um` (:184-187), `phase_transformation_note` and `TI64_MARTENSITE_K_S` (:83, :190-235).
3. G12 rewrite in the SOL-A1 guarded commit. Remove the four observations. Add `solidification.pdasAdmission` over these named pairs (G in K/m, R in m/s, canonical IDs `in625`, `in718`, `ti6al4v`), so the line rule is the only rule that decides pairs 2 and 3 (RA5):

| Pair | G | R | x = G^-0.5 R^-0.25 | G R (K/s) | Vcs (m/s) | Expected |
|---|---|---|---|---|---|---|
| 1 | 1e7 | 0.05 | 6.69e-4 | 5e5 | 5.26e-4 | band (on the line; positive control) |
| 2 | 2e7 | 0.01 | 7.07e-4 | 2e5 | 1.05e-3 | refused, `outside-source-model-domain`: off the line only |
| 3 | 5e6 | 0.05 | 9.46e-4 | 2.5e5 | 2.63e-4 | refused: off the line only |
| 4 | 5e7 | 0.0012 | 7.6e-4 | 6e4 | 2.63e-3 | refused: off the line and below Vcs |
| 5 | 1e6 | 1.5 | 9.04e-4 | 1.5e6 | 5.26e-5 | refused: off the line and above Vab |

A mutant that keeps the old box and adds only Vcs and Vab gives a band for pairs 2 and 3 and fails. Also add `solidification.defaultBlock` (five canonical IDs on the existing Eagar-Tsai field, no legacy keywords) and `solidification.unknownAlias`. None matches `HONESTY_PATTERNS` (:1590-1600). `python/test_cet_and_pdas_admission.py` asserts the same pairs.
4. Reference-case harness decision for SOL-T (re-gate RT8, RA3): SOL-T moves reference numerics in G1, G2 and G4 (geometry through the liquidus, and the three transient metrics of D13), which `_protected_reason` refuses (:1646-1647). The decision is a named, one-time exception recorded in the SOL-T bump record and carried by a Ceiling-Review trailer: an exact-key list for those three cases, computed from a `--check --slow --expect-unpinned` run and reviewed key by key, with no change to `REFERENCE_NUMERICS_PATTERNS`. Opus drafts it before SOL-T code starts; the maintainer's trailer approves it.
5. `evaluate_solidification` loses its ignored keywords (`solidification_front.py:352-364`); callers passing them are G12 and the tests of 8.1 (F9).

## 7. Consumer inventory

### 7.1 Python producers and consumers

| File:line | Today | Change | Lane |
|---|---|---|---|
| `solidification_front.py:35-89` | model ID, DOIs, cuts, anchor, `9.56e-4` (:66), Ti64 switch, substring alloy match (:86-89) | v2, `A = 1.1773863284676703e-3`, canonical IDs, sources per quantity, sentences moved out (4.1 item 6) | SOL-A1 |
| `solidification_front.py:92-125` | box admission | fixed-G line, x, cooling, Vcs, Vab before arithmetic; pairs of 6.3 | SOL-A1 |
| `solidification_front.py:343-423` | medians, notes, DOI on every child, rounding (:411-422) | every default quantity null with `missing-source-constant` and the liquidus parent; keyhole leg keeps `keyhole-field-inconsistent`; no rounding | SOL-A1 |
| liquidus authority (`four_alloy_materials.py`, `lpbf_thermal_solver.py` secondary table, `lpbf_material_registry.py:165-170`) | unsourced or unrecorded pairs | admitted records per RT1 to RT8, parent identity of section 5 | SOL-T |
| `lpbf_simulation.py:392-411`, :751, :803-810, :1131-1132; `lpbf_openfoam.py:177-179` | transient and OpenFOAM liquidus G, R, cooling on the registry liquidus | SOL-A1: unchanged in Python, scoped out in the UI (7.3); SOL-T: contained under 6.4 (null with `parent` when the liquidus is not admitted, labelled per 4.3 when it is) | SOL-A UI, SOL-T |
| `solidification_front.py:238-308` | separate medians, upper median (:292-294) | per-sample tuples, defined aggregation, full precision | SOL-C |
| `lpbf_thermal_solver.py:1195-1217`, :1563-1591 | flat keys rounded at :1569-1576 | one container (4.2); flat numeric keys removed | SOL-A1 |
| `lpbf_solidification_microstructure.py:44-79`, :91-111, :138-244, :355-375, :384-470 | own cuts and fractions, DOI map, floors, front band import, legacy CFD | envelope passthrough; CFD refused with `quarantined-legacy-path` | SOL-A |
| `lpbf_worker_rpc.py:12-20` | runs the CFD branch | refusal | SOL-A |
| `lpbf_gr_solidification.py:12-21`, :37, :41, :75, :229-319, :342, :461-464 | Hunt credits, schema 1, `GtimesR` alias, two alloys | containers, schema 2, five IDs, provenance | SOL-A |
| `lpbf_cet_screening.py:38`, :65, :79, :84-120, :160-197, :220-280 | one flag, one transfer label, no finite-positive check | 4.7; default LPBF CET `unavailable` with `outside-source-model-domain` | SOL-A |
| `lpbf_solidification_segregation.py:80-84`, :429-479, :598-610, :639, :687, :826, :843, :904, :1009-1037, :1142-1149 | strings, statuses | containers, observation record, schema 2 | SOL-A |
| `lpbf_build_job_solver.py:84-96`, :113-115, :204-245, :1243-1274 | liquidus G x R to CCT, 1 K/s floor | kinetics `unavailable` with `missing-thermal-history`; floor removed | SOL-A |
| `kinetics_ttt_cct_solver.py:97-115`, :567-620 | statuses, generic LSW and 280 MPa curve | 4.5 mapping; LSW and strength unavailable for every alloy; input checks | SOL-K |
| `python/tools/kinetics_documented_changes.py:158-207`, :602-620 | oracle flags null rows | expects `unavailable` | SOL-K |
| `calphad_solver.py:1475-1633`, :1758, :2003-2008, :2158-2262, :2337-2339, :2383, :2505-2512 | identity residual, clamp, filter, nominal-only domain, wording, provenance | per SOL-B and its Amendment 3 (RB1 to RB4) | SOL-B |
| `module_contracts_calphad.py:79-111`, `module_contracts_lpbf_secondary.py:178-206` | transport vocabularies | declarations, 0.2.0 | SOL-A, SOL-B |

Offline consumers and owners (F13): `python/benchmark_phase7_microstructure.py:47` (SOL-A, Sonnet); `python/tools/lpbf_validity_envelope.py:112-113` (SOL-T, Opus); `python/lpbf_public_datasets.py:1108` note (R-lane, because the line sits among measured NIST rows); `docs/research/scripts/check_solidification_*.py` stay dated audit records (Astra). Unreached today: `kinetics_ttt_cct_solver` is in neither `DISPATCHABLE_SCRIPTS` (`server/processOrchestrator.ts:186-196`) nor `ALLOWED_SCRIPT_NAMES` (`python/persistent_ipc_service.py:107-117`).

### 7.2 Strict TypeScript parsers and types

| File:line | Change |
|---|---|
| `src/data/lpbfGrSolidification.ts:17`, :20, :75-78, :116-125, :206-215, :217-254, :256-327 | generated statuses and alloys, `checkedQuantity`, no Hunt keys, `sourceChecks`, schema 2 |
| `src/services/lpbfGrSolidificationService.ts:30`, :60-61, :139-140 | types |
| `src/utils/solidificationOutcome.ts:18-38` | envelope statuses, no floor branch |
| `src/services/pythonComputationService.ts:270-300`, :1395-1434 | worker and thermal container types |
| `src/utils/pdasBandText.ts:14-23` | two named alternatives, not "lo to hi" |
| `src/utils/goldakCaeCard.ts:50`, :105 | containers |
| `src/utils/calphadResultDisplay.ts:150-170`, `src/utils/calphadDisplay.ts:150-170` | inventory residual lines; CSV columns |
| `src/utils/kineticsHardnessDisplay.ts:157-170` | `unavailable` rows |
| `src/physics/calphadMultiComponentSolver.ts:312`, :370, :532-538 | retired or isolated (4.4) |

### 7.3 UI surfaces

| File:line | Change | Lane |
|---|---|---|
| `SolidificationMicrostructureLab.tsx:112-119`, :183-187, :384, :405, :420, :424, :437, :461, :475 | bind to `activeSpecimen.lpbf`; remove band lines, wrong credits and unsourced ranges; render containers | SOL-A |
| `GrSolidificationMapCard.tsx:44`, :86, :243, :455, :466-467 | no Hunt attribution or band metric; source checks; Python unavailable state for Ti64, AlSi10Mg, 316L | SOL-A |
| `MeltPool3DCrossSectionLab.tsx:1232`, :1241-1290 | no model-ID literal; rows render containers or reasons | SOL-A |
| `LpbfEngineeringSimulation.tsx:674` and the convergence panel | `thermalGradient_K_m`, `solidificationRate_m_s`, `coolingRate_K_s` leave the generic metrics grid and appear under a labelled transient-diagnostic heading (literal L6) | SOL-A |
| `BuildJobMicrostructurePanel.tsx:47`, :62-63, :86-96; `IndustrialLPBFDecisionLab.tsx:633` | generated statuses, containers | SOL-A |
| `CALPHADMultiComponentStudio.tsx:225-274`, :374-377, :483-490, :557-563, :1523, :1618 | stale gating, export identity, primary-phase wording, `not-requested` | SOL-B |

### 7.4 Effect users will see

At SOL-A1 (blanket null, W/D unchanged; gate decision RA1), every default front quantity is unavailable for all five alloys: G, R, cooling rate, G/R, PDAS, SDAS, morphology, phase note and default LPBF CET, in the thermal card, both labs, the Build Job panel and the G/R map. W, D, regime, verdict, `extentStatus`, the process window and the defect diagnostics stay byte-equal. Reason, re-anchored: SOL-A1 installs no endpoint admission. The SPEC A2.2 records are historical proposals held by A3.C for SOL-T, so the unsourced-parent rule of SPEC §4.1 (SPEC:94) and A2.1 keeps every default front quantity null, as the RA1 paragraph of A2.4 and A3.A1 state (`f422fa26`).

The transient Standard Simulation panel inside the Melt Pool lab keeps its transient G, R and cooling numbers after SOL-A1, under the L6 heading that says they rest on the same unadmitted liquidus and a single mesh (D13); they are contained at SOL-T. This goes into the MD5 notice.

The earliest return of default front values is SOL-C after SOL-T, per alloy as the re-gate table lists (Ti64, AlSi10Mg, IN718, IN625 if RT1 to RT6 close; 316L none under Amendment 2).

## 8. Test inventory

### 8.1 Tests that change

| Lane | Python | TypeScript |
|---|---|---|
| SOL-A | `test_solidification_front.py:8`, :23-49, :60-73, :104-108; `test_lpbf_solidification.py:12-44`; `test_lpbf_waveb_front_raytracer.py:14`, :44, :74; `test_lpbf_waveb_rosenthal_keyhole.py:66`; `test_lpbf_build_job.py:42-124`, :141-161, :204-232, :250-279, :288-360, :391-423, :426-466, :666-689, :1030-1033; `test_lpbf_p6_containment.py:203-260` (legacy keywords at :226-228, F9), :318-328; `test_lpbf_p7a_rules_and_nulls.py:372-381`, :383-403 (F9), :410; `test_lpbf_p1_sourced_depth_path.py:227`; `test_lpbf_gr_solidification.py` (whole file, notably :316-349); `test_lpbf_solidification_microstructure_rpc.py:16`, :47-74, :114-157; `test_lpbf_solidification_segregation.py:25`; `test_phase7_microstructure_validation.py:3`, :18-31; `test_phase8.py:25`, :35-63; `test_phase8_microstructure_contract.py:30-42`; `test_module_contract_lpbf_secondary.py:89-118`; `test_module_contract_solidification_microstructure.py:23-62`; `test_module_contract.py`; `test_lpbf_calibration_frozen.py:55-59`; `test_lpbf_parity_golden.py:56-60` | `tests/lpbf-gr-solidification.test.tsx:19-48`, :78, :111-115, :203, :216; `tests/build-job-microstructure-panel.test.tsx:10`, :37, :90; `tests/build-job-segregation.test.tsx:11-12`; `tests/build-job-kinetics-panel.test.tsx:12`, :27-50; `tests/solidification-outcome.test.ts:8`, :41; `tests/goldak-cae-card.test.ts:36`, :274; `tests/lpbf-material-authority.test.ts:182-232`; `tests/lpbf-claims-wording.test.tsx:10-11`; the transient panel test for L6; registry parity tests |
| SOL-K | `test_kinetics_fx.py:100-107`, :304-312; `test_kinetics_li1998.py:30`; `test_phase6a_golden.py:304-305`; `test_phase6a_t2b_golden.py`; `test_phase6a_t2b_migration.py:95-100`; `test_alloy_registry.py`; `test_alloy_data_kinetics_uq_fatigue.py`; goldens `python/golden/phase6a/kinetics_ttt_cct_solver/` with a ledger entry | `tests/kinetics-hardness-display.test.ts:17`, :314-321 |
| SOL-B | `test_calphad_honesty.py:876`; `test_calphad_model_cache.py:177`, :207, :357; `test_calphad_literature_solidification.py`; `test_calphad_matcalc_open.py`; `test_calphad_mc_ti.py`; `test_calphad_carbon_reference.py`; `test_alloy_data_calphad_battery_icme.py`; `test_module_contract_calphad.py`; `test_phase6a_golden.py`, `test_phase6a_t2a_migration.py`; tools `xcheck_scheil_laves.py`, `xcheck_superalloy_table.py`, `calphad_ui_specimen_drift.py` | `tests/calphad-display.test.tsx:287`; `tests/alloy-property-consumers.test.tsx:20-21`; `tests/a11y-form-labels.test.ts:27`; `tests/visibility-loops.test.tsx`; `scripts/test-calphad-alsi10mg.ts` |
| SOL-T | liquidus authority tests (`test_four_alloy_literature`, `test_lpbf_material_authority_json`, `test_lpbf_materials_waveb`, `test_lpbf_p7b_sourced_constants` in the R-lane only, 8.3); transient metrics `test_lpbf_engineering.py:619`, `test_lpbf_verification_celik.py:120`, :142, `test_lpbf_validity_envelope.py:27`; fixture `tests/fixtures/lpbf-real-bare-plate-100W-capture.json`; every test pinning a liquidus or a W/D literal, found by the pin-literal sweep of 3.3 | demo and transient tests |
| SOL-C | `test_solidification_front.py`, `test_lpbf_solidification.py`, `test_lpbf_waveb_front_raytracer.py`, G12 | lab and map distributions |
| R-lane | `test_lpbf_error_bands.py:316-321`, `test_lpbf_depth_bias.py:199` | `tests/lpbf-error-bands.test.tsx:59-62`, `tests/demo-snapshots.test.ts:65-78`, `tests/demo-gate.test.tsx:108-111`, `tests/depth-bias-warning.test.tsx:13` |

New tests: `python/test_quantity_envelope.py` (label rule, process-value exclusion, Unresolved precedence, ledger class mapping, no Measured on a quantity), `python/test_module_contract_quantities.py`, `python/test_quantity_envelope_payloads.py`, `python/test_solidification_payload_fixtures.py`, `python/test_cet_and_pdas_admission.py` (6.3 pairs, CET masks, source checks), `python/test_solidification_chain_identity.py`, `python/test_scheil_inventory_oracle.py`, `python/test_scheil_package_comparator.py`, `python/test_lpbf_research_label_vocabulary.py` (4.8 item 6), `tests/quantity-envelope.test.ts`, `tests/solidification-payloads.test.ts`.

### 8.2 Independent oracles

1. Scheil inventory (SOL-B): unfiltered phase increments read from a raw kernel trace, never from `solid_x` back-solved at `calphad_solver.py:1583-1585`; real-fixture tolerance per Astra's Amendment 3 (RB4), declared before results.
2. Kinematics (SOL-C): the RC2 oracle that checks `dT/dz`, `dT/dy` and `|grad T|` as well, not only G R.
3. LSW (SOL-K): `kinetics_documented_changes.py`, expecting `unavailable`.
4. Comparator (SOL-B): `scheil` 0.3.0, software comparison only.

### 8.3 Tests that read measured melt-pool data

Blind lanes run the targeted lists of 8.1, never the full unit suite or the full CI Python list. Records-lane and batch-gate only: `test_lpbf_additional_datasets`, `test_lpbf_benchmark`, `test_lpbf_calibration_v2_config`, `test_lpbf_keyhole_literature`, `test_lpbf_keyhole_regime_bump`, `test_lpbf_literature_datasets`, `test_lpbf_nist_in718_comparison`, `test_lpbf_p7b_sourced_constants`, `test_lpbf_process_map`, `test_lpbf_process_window`, `test_lpbf_public_datasets`, `test_lpbf_wave2_datasets`, `test_lpbf_zero_drift_depth`, `test_nist_optical_transcription`, `test_lpbf_depth_bias`, `test_lpbf_keyhole_benchmark`; `tests/guided-demo.test.tsx`, `tests/lpbf-experimental-validation-logic.test.ts`, `tests/lpbf-nist-comparison-api.test.ts`, `tests/lpbf-run-bundle-api.test.ts`, `tests/lpbf-run-bundle.test.ts`, `tests/lpbf-run-client.test.ts`, `tests/lpbf-run-nist-ui.test.tsx`, `tests/lpbf-run-proxy-campaign-client.test.ts`, `tests/lpbf-run-repository.test.ts`, `tests/lpbf-source-archive-selection.test.ts`, `tests/lpbf-source-optical-catalog.test.ts`, `tests/melt-pool-literature-case.test.ts`, `tests/demo-snapshots.test.ts`. The list comes from the loader pattern `load_lane_in625|load_hofmann_316l|load_totis_ti64|load_ku_leuven|load_ghosh_in625|load_trapp_316l|nist-amb2022-03-optical|lpbf_public_datasets|lpbf_literature_datasets` plus two by reading. The parity suite is depth-free (G14 uses a synthetic row, `lpbf_parity_check.py:515-531`).

### 8.4 Run instructions (one form each)

| Tool | Directory | Command |
|---|---|---|
| bump record | `python/` | `python -B tools/lpbf_bump_record.py --from-revision <sha> --with-parity-check --slow --expect-drift ...` |
| parity | repository root | `python -B python/tools/lpbf_parity_check.py --check --slow` |
| bands | repository root | `python -B python/tools/lpbf_error_bands.py --restamp` or `npm run lpbf:bands`, then `npm run lpbf:bands:check` |
| registry | repository root | `python scripts/emit-module-registry.py --check` |
| audit and ledger scripts | repository root | `python -B docs/research/scripts/<name>.py --check` with the locked interpreter (`.runtime/lpbf-win-py312`); `-I` only after the T1 sibling-import fix (Phase 0.6) |
| one Python test | `python/` | `python -B -m unittest <module>` |
| one TS test | repository root | `npx tsx --test tests/<file>` |

Where the AUDIT §7 or a script docstring says otherwise, this table is the integration rule; Astra aligns her text in her own commit.

## 9. Phases, owners and acceptance checks

Owners: Opus for hard integration and guarded work, Sonnet for ordinary code, Haiku for chores, Astra for physics. One Opus gate per lane.

| Phase | Work | Owner | Acceptance checks |
|---|---|---|---|
| Doc fixes | RA1 to RA6 plan side (this revision); Astra: A2.4 and ledger wording for RA1, RA7 items; lead check | Opus, Astra, lead | lead checks RA1 to RA7 before Phase 0 code |
| MD2 round | literal groups L1 to L11 (11.2) | lead, maintainer | approved text before SOL-A1 freezes |
| 0.1 | `quantity_envelope.py` with decisions 1 and 2, label rule, ledger mapping, SDK dataclasses, registry emission, generated TS, shared value-provenance parser | Opus | new tests pass; registry check; `npm run lint`; existing contract tests unchanged |
| 0.2 | parity error rule for the three shapes (guarded) | Opus | unit tests per shape under glob and exact entries; `--check --slow` 25 PASS at `36cd9d4a` |
| 0.3 to 0.5 | restamp mode; payload fixtures; W/D invariance tool | Sonnet | synthetic tests; deterministic generation; two captures byte-equal |
| 0.6 | TDB identity inventory; T1 sibling-import fix; archive the three %TEMP% PDFs into `papers/` with INDEX entries (M12, T7) | Haiku | second run reproduces |
| SOL-A | A1 front and container plus bump; A2 Python consumers; A3 TS and UI; A4 fixtures, `docs/LPBF_ENGINEERING.md:43`, module docs, PROOF draft | A1 Opus; A2, A3 Sonnet; A4 Haiku | envelope and payload tests; F16 synthetic admitted fixture non-null; 6.3 pairs; bump record limited to 3.4; invariance byte-equal; T-FRZ-3 the only named red |
| SOL-K | LSW and strength unavailable, input checks, oracle, goldens | Sonnet; Haiku capture | Li TTT and CCT byte-equal outside LSW rows |
| SOL-B | after Astra's RB1 to RB4 and a narrow Opus check: B1, B2 Opus; B3 to B5 Sonnet | as listed | SPEC gate 2 with the RB4 real-fixture tolerance; RB1 path-local test; chain closure test; stale export refused |
| SOL-T | after RT1 to RT7 and a narrow Opus check: harness decision of 6.4, endpoint installation, D13 containment, bump | Opus; R-lane Sonnet | every moved key named; full bands run reviewed cell by cell; P8 R-CTX-1 re-pinned by its owner in the same batch |
| SOL-C | after RC1 and RC2: per-sample tuples, aggregation, opt-in channel, bump | Opus; UI Sonnet | RC2 oracle; gate 5 quantities stay `unresolved`; drift limited to declared keys |
| R-lane | 3.7 per batch | Sonnet (exposed records agent) | restamp or reviewed full run; full suites green except T-FRZ-3 before merge |
| Batch close | gate, trailer, push | lead, maintainer | `scripts/check_ceiling_review.py` covers every guarded path |

## 10. Minor notes, engineering parts

| Note | Resolution |
|---|---|
| 9 ODbL | export header slot in SOL-B; text and licence entries follow MD3a and MD3b |
| 13 ordering claims | `calphad_solver.py:2383` scope in SOL-B; `pdasBandText.ts:19` in SOL-A |
| 14, 21 | audit scripts relabelled and git-independent at `3908a741`; run form in 8.4 |
| 17 Build Job CCT input | SOL-A (`lpbf_build_job_solver.py:89-96`, :204-245) |
| 18 aging input | SOL-K: `nonphysical-input` before arithmetic, no bare `NaN` token |
| 20, T2 | section 5 TDB rule and scheil pin |
| F9 | legacy keywords in tests listed in 8.1 |
| F10 | three error shapes in 6.1 |
| F11 | kinetics and segregation statuses in 4.5 |
| F13 | offline consumer owners in 7.1 |
| F14 | one placement rule, 4.1 item 7 |
| F15 | exposure record, section 12.6 |
| conflicting run instructions | 8.4 |

## 11. Maintainer decisions

### 11.1 Decisions

1. MD1: closed by decision 1 (2026-10-15) and carried in 4.2 and 4.3.
2. MD2, wording (ORCHESTRA.md:84): one round before SOL-A1 freezes (RA4), over the literal groups of 11.2.
3. MD3a: ODbL Produced Work line on CSV and JSON exports from a MatCalc-derived database (re-gate recommendation: yes). MD3b: licence entry for `mc_fecocrnbti.tdb` (recommendation: add it, origin mc_fe 2.060, sha256, ODbL/DbCL, alteration method unknown if unrecorded). MD3c: COST507, already public since `d45f875d`: keep it, reproduce its notice verbatim, never a standard licence label; any new channel needs clarification, and asking the custodians is an external message.
4. MD4: three trailer runs and pushes (W1, T, W2); T carries the Ceiling-Review trailer for the 6.4 harness decision. P8 adds no guarded path to the SOL batches.
5. MD5 notice, after RA3 is settled (now 7.4): default front values unavailable for all five alloys at SOL-A1; the transient panel keeps labelled numbers until SOL-T; stored machine calibrations go stale at each pin move.

### 11.2 Literal inventory for MD2 (all drafts, none approved)

| ID | Literal group | Where it will live |
|---|---|---|
| L1 | one sentence per reason code (25) | `quantity_envelope.py` registry, generated TS |
| L2 | status labels (5) | same |
| L3 | source-label display: "Literature estimate", "User input: {names}", "Unresolved: {names}", observation "Measured (transcribed)" | same; shared with P8 W-1 |
| L4 | CET source-check labels replacing `GrSolidificationMapCard.tsx:455`, :467, and per-set transfer labels replacing `lpbf_cet_screening.py:79` | registry |
| L5 | CALPHAD export file name pattern and header lines, ODbL line | `src/utils/calphadDisplay.ts` |
| L6 | transient-diagnostic heading for the three metrics in `LpbfEngineeringSimulation.tsx:674` | that component |
| L7 | SPEC candidates at SPEC:110, :120, :152 (line numbers at `024e30cd`) | registry |
| L8 | quantity definition names shown in the UI (4.2) | registry |
| L9 | container header text ("Screening only", maturity echo) | generated TS |
| L10 | Evidence remains screening-only and Research. The response-level G/R evidence object is SDK-reserved; per-quantity source labels never imply experimental validation. | Introduced in `b138fad5`; `docs/modules/solidification-microstructure.md`, `src/generated/moduleRegistry.json` (mirrored in generated TS); pending maintainer wording approval |
| L11 | The worker returns lpbf-solidification-microstructure-2. Quantities are copied from the Python thermal front container with SI values, coded reasons and input provenance; no second estimate or flat-key fallback. | Introduced in `b138fad5`; `docs/modules/solidification-microstructure.md`, `src/generated/moduleRegistry.json` (mirrored in generated TS); pending maintainer wording approval |

## 12. Coordination with P8, P3 and exposure

1. P8 holds no pin (fact 10). It merges independently; SOL bump records never depend on it; SOL-C does not use P8's transport (RC1 designs SOL-C's own served channel jointly with the P8 architect).
2. R-ISO-2 is P8's branch-scoped P-2 over the P8 commit range; SOL lanes never run it and nothing in SOL depends on it (3.6).
3. R-TR-11 uses a stubbed identity; the SOL pin-literal sweep (3.3 item 6) guards against a live binding.
4. SOL-T moves P8's pinned context (R-CTX-1 Ti64 Tl 1660.0 C; AlSi10Mg K, cp and Tl; P8 spec Ti64 1877.15/1933.15 K; the Al Tl arms). The P8 owner re-pins them inside batch T; the lead coordinates (re-gate RT7).
5. Shared label vocabulary and value-provenance parser: owner of the equality test assigned by the lead (4.8 item 6).
6. Exposure record (F15). While writing Revision 0 the integration owner read derived depth statistics: the P7b reasons file (Lane IN625 served-over-observed depth ratios and band cell medians, `docs/LPBF_IMPLEMENTATION_BUMP_2026-10-14_p7b-sourced-constants.reasons.md`), the depth-bias test literals (`tests/depth-bias-warning.test.tsx:40-47`), one bands row's input tuple and predicted W and D (the measured columns were masked by the shell before display), and the key and status structure of the overlay snapshot (no values). All belong to spent sets. The integration owner does no blind depth work. Investigator exposure is recorded by Astra in SPEC A2.5.
7. P3: no served bump while a SOL batch is open; full bands run in its own R-lane.

## 13. Revision 1 index (re-gate 2026-10-15)

| Item | Where |
|---|---|
| RA1 (plan side) | D1, 3.1, 3.2 item 1, 3.8, 7.4 |
| RA2 | D6, 4.1, 4.2, 4.3, 4.8 item 6, 11.1 item 1 |
| RA3 | D13, fact 11, 6.4, 7.1, 7.3, 7.4 |
| RA4 | 4.1 item 6, 11.1 item 2, 11.2 |
| RA5 (plan side) | 6.3 |
| RA6 | fact 10, 3.1, 3.2 items 4 and 5, 3.3 item 6, 3.6, section 5 pin row, 11.1 item 4, 12 |
| W1 minors | section 10 |
| RB, RT, RC items | gating rows in 3.2 and 9; physics content is Astra's |
