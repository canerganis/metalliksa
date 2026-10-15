# SPEC: your own blind test (bring your own data) and the descriptive panel on spent sets

File: `docs/research/SPEC_research_hub_data_2026-10-14.md`. Design gate draft, written 2026-10-15 on worktree
`Metalliksa-1-wt-hub` (branch `feat/research-hub-data`, HEAD `835466fa`, fingerprint pin `36cd9d4a…`). Nothing in the
product implements it yet. Revision 2 (2026-10-15): the gate's must-fix items, missing items and contradictions are
applied in place (committed as `2f0d884a`). Revision 3 (2026-10-15, section 14): sharing with the maintainer (Mode A
"share my result", Mode B "sealed submission"), transport without a server, anti-fabrication trust tiers, the
maintainer's per-value label decisions, and section 7.6 reconciled with the P8 integration contract
(`research/p8-research-arm` `29ae2183`: no served bump, research only through its own opt-in route, block schema
`p8-research-v3`), integrated into the affected sections (Appendix A.5). Revision 4 (2026-10-15, section 15): Part S
after the gate, with Mode B as the successor objective G3s with its own pre-registration [Q12], the sealed runner mode,
the rebased research relay, and the Mode A, tier, identity, licence and public-surface changes; the Part P changes are
in place (Appendix A.6).

Gate of 2026-10-15 (REJECT of revision 3 as a whole, `.orchestra/reports/hub_spec_gate_verdict_2026-10-15.md`), split
re-entry. Part P is the protocol 1 local flow (sections 2 to 7, research arm fixed at `RESEARCH_NOT_REQUESTED`) and
section 8; it carries R12(a) and R13 to R21 in place, marked "(Part P)", for the lead check. Part S is the research
relay, Mode A and Mode B (sections 14 and 15, and every row or item marked "revision 3" or "Part S" in the other
sections); it is revision 4 (section 15) and needs a fresh Opus gate, and Mode B also needs its own pre-registration.
Nothing marked Part S is in scope of the Part P check.

Goals: roadmap items 1 and 2 of `.orchestra/GOAL.md` ("Roadmap after the batch push", maintainer approved 2026-10-14).

Base design: "reuse first" (design 1), the best combined judge score (evidence 6.5, engineering 8, usability 6, total
20.5; protocol integrity first 19; Research Hub usability first 18). Grafted ideas and the fix for every judge defect are
listed in Appendix A. Where this spec and a design disagree, this spec wins.

Labels unchanged by this work: `experimentalValidation=false`, evidence kind `screening-only`, no module or result
promoted, no served physics change, fingerprint manifest untouched (36 files), `routes/AUTHORITY_ALLOWLIST.json` and every
`*.ceiling.json` untouched, legacy contract count stays 3. Revision 3 adds a per-value `sourceEvidenceKind` under that
unchanged screening-only ceiling (14.6); no ceiling is raised.

## 1. Purpose and non-goals

### 1.1 Purpose

1. A researcher with their own LPBF single-track cross sections (Ti-6Al-4V and AlSi10Mg first; 316L, IN718 and IN625
   also) runs a blind test of the app's melt-depth predictor in their own lab. The app asks the metadata the MELT
   pre-registration needs, freezes and hashes its predictions from the inputs file before any measurement byte reaches
   the server, withholds every predicted value until the measurements are uploaded (or records that the user chose to
   see them early), then scores the frozen values with the MELT statistics and reports the served path and the P8
   research arm side by side. The result is the user's own blind test, never the app's validation.
2. A descriptive panel in the Dataset Comparison lab shows served and research-arm model curves beside spent public
   sets, where the model deviates and which catalogued, untested explanation applies, labelled "not validation, data
   already seen".
3. Both features share one definition of "served" (the Build Job thermal call, reproduced and parity tested) and one of
   "research arm" (the `researchModels` block of the P8 research route response, read through a closed adapter, 7.6).
4. Revision 3: a user may share a finished local test with the maintainer (Mode A, counted as seen) or submit a sealed
   block that the maintainer predicts before the targets are released (Mode B, an independent blind test of the app at
   tier Evidenced or above). Both modes produce files only; the app uploads nothing (section 14).

### 1.2 Non-goals

1. No validation claim for the app, no G3, G3o, N3 or N4 credit, no physics bump, no calibration from user data (the
   existing machine-calibration path stays separate and unchanged), no leaderboard entry, no automatic link into the
   research registry. This holds for every local test and every Mode A share. The one route to a G3o block and a
   leaderboard row is a Mode B sealed submission handled by the maintainer under the sealed protocol (14.4).
2. No served physics change. All new Python files sit outside `lpbf_simulation.IMPLEMENTATION_SOURCE_FILES`; the
   served modules outside that manifest are pinned separately (3.6).
3. No new HTTP route, no allowlist or ceiling growth, no new registry module, no `App.tsx` edit, no nav golden change.
   Node gets one edit and no route edit: `server/pythonRuntime.ts` forwards the blind environment variables to a WSL
   worker (3.3). The research route `POST /api/python/lpbf-research-models` belongs to the P8 integration contract;
   this spec uses it and adds nothing to it (7.6).
4. No hosted or multi-user service, no upload. The store is local to one workstation and is not scoped per user; on a
   server bound to a non-loopback address blind mutations are refused unless the operator declares a single-user
   install (9.7). Sharing writes files the user sends by hand; the app makes no outbound call (14.1, 9.14).
5. No proof of ordering to third parties from the local store alone. The app records local order and hashes; provable
   order needs the user to anchor the receipt hash outside this computer, or a Mode B submission, whose order rests on
   GitHub and Zenodo server times (14.5).
6. Protocol 1 scores melt-pool depth only. Width is descriptive. Vapour-depression depth is descriptive (scored
   against nothing until a separate registration). Multi-track, powder-layer scoring, xlsx files, property-fragile arms
   and per-user stores are out of scope.
7. The descriptive panel shows no thresholds, no pass or fail words, no ranking and no "accuracy".

## 2. Labels and evidence rules

### 2.1 Fixed fields (Python sets them, Python and TypeScript validators refuse any other value)

Every blind document (preview, receipt, reveal record, report, list entry) carries an `honesty` block:

| Field | Value |
|---|---|
| `resultScope` | `user-blind-test` |
| `protocolId` | `lpbf-user-blind-protocol-1` (explicitly not the G3o registration) |
| `notG3oRecord` | `true` |
| `experimentalValidation` | `false` (the boolean; missing, `true` or the string `"false"` is refused) |
| `appValidation` | `false` |
| `labelPromotionProposed` | `none` |
| `evidenceKind` | `screening-only` |
| `dataLabel` | `Measured (user-supplied)` (reuses `lpbf_user_measurements.ROW_LABEL`) |
| `neverEnters` | `{g3, g3o, n3, n4, physicsBump, calibration, leaderboard, researchRegistry}`, all `true` |
| `g3Satisfied`, `n3Counted` | `false` |

The descriptive record carries `{label, statement, experimentalValidation: false, labelPromotionProposed: "none",
evidenceKind: "screening-only", spentOnly: true}`.

Revision 3 scopes. Shared and sealed documents carry the same block with these differences; Python and TypeScript
refuse any other combination:

| Field | Mode A (share manifest, maintainer import record) | Mode B (commitment, predictions, result, sealed record) |
|---|---|---|
| `resultScope` | `shared-result` | `sealed-submission` |
| `protocolId` | the frozen test's `lpbf-user-blind-protocol-1` | `lpbf-sealed-protocol-1` |
| `notG3oRecord` | `true` | `true` always; a sealed block never counts for G3o (Rev. 4, 15.1) [Q12] |
| `objective` (Rev. 4) | absent | `G3s` for a block registered at import, `none` otherwise (15.1 item 2d) [Q12] |
| `appBlindTest` (new) | `false` | `true` only for a scored registered block with blindness `blind-sealed` in state `recorded`; `false` otherwise (Rev. 4, 15.1 item 4, PI-11) |
| `neverEnters` | every member `true` | `g3`, `g3o`, `n3`, `n4`, `physicsBump`, `calibration`, `researchRegistry` `true`; `g3s` `false` only for a registered block; `leaderboard` `false` (Rev. 4) |
| `seenByMaintainer` (new) | `true` after import | `false` until `released`, then `true` |
| `tier` (new) | the current tier (14.7) | the tier at score and the current tier |

`experimentalValidation`, `appValidation`, `labelPromotionProposed`, `evidenceKind` (the module ceiling) and `dataLabel`
keep their 2.1 values in every scope. Every predicted or measured value also carries `sourceEvidenceKind` and
`sourceLocator` (14.6).

### 2.2 Wording (proposals; the maintainer decides user-facing label wording, ORCHESTRA section 6)

Tests pin the strings only after approval (open question Q1). Until then they live in one wording table
(`data/blind/lpbf-user-blind-wording-v1.json`, section 4.6) so approval is a one-file change. The wording table is kept
out of `protocolSha256` and out of every identity (3.6), so an approved wording change never labels an older freeze.

| Where | Proposed text |
|---|---|
| Hub tab | `Your blind test` (unnumbered; not part of the numbered brief workflow) |
| Report title | `Your blind test on your own measurements` |
| Banner | `This is your test of the model on your data. It is not validation of this app, and the app's evidence labels do not change (experimentalValidation false).` |
| Receipt line | `Predictions frozen. Values are withheld until you upload your measurements or choose to reveal them.` |
| Status `thresholds-met` | `All four thresholds were met on your data, with leverage and resolution met.` |
| Status `threshold-not-met` | `At least one threshold was not met on your data: <list>.` |
| Status `inconclusive` | `Inconclusive: <reason>. The statistics are shown for information.` |
| Status `descriptive-not-scored` | `Shown for information, not scored: <reason>.` |
| Status `descriptive-exposed` | `Not blind: <reason>. The statistics are shown for information.` |
| Status `unavailable` | `Research arm not available: <reason>.` |
| Descriptive badge | `Not validation: data already seen` |
| Descriptive "why" prefix | `Candidate explanation, not tested:` |
| Blindness `blind-committed` (Part P, U9) | `Blind: your targets file was fixed by its hash before the predictions were frozen.` |
| Blindness `blind-prospective-declared` | `Blind as you declared: you froze the predictions before measuring.` |
| Blindness `blind-retrospective-declared` | `Blind as you declared: you measured before freezing, and no commitment of the targets was matched.` |
| Blindness `not-blind-predictions-viewed` | `Not blind: you declared that you viewed predictions for these conditions.` |
| Blindness `not-blind-predictions-revealed` | `Not blind: the frozen predictions were revealed before this score.` |
| Blindness `not-blind-earlier-test-overlap` | `Not blind: <k> conditions match a test on this computer that was revealed or scored earlier.` |
| Blindness `not-blind-rescored-changed-targets` | `Not blind: this attempt uses a targets file that differs from attempt 1.` |
| Blindness `not-blind-data-already-used-by-app` | `Not blind: these data or conditions are in this app's spent ledger (<id>).` |
| Blindness `not-blind-app-history` | `Not blind: Build Job history on this computer holds these conditions before the freeze (partial check).` |
| Blindness `not-blind-used-for-calibration` | `Not blind: these conditions were used for machine calibration on this computer (<store id>).` |
| Block issue fix texts (Part P, U9) | one sentence per issue of 6.2, in the wording table: what to change in the metadata or the file, for example `State the cross-section location; sections near track ends measure start or end transients.` |
| Served value label (Part P, HUB-LP-18) | `Unresolved: the served result does not yet list the source of each value.` |
| Research arm label | `Literature estimate / Research / not validated` (GOAL item 0 wording; see Q2); under revision 3 the first part is the leaf's own `sourceEvidenceKind` (14.6) |
| Research arm reason, protocol 1 (Part P) | `not requested: the P8 research route accepts requests only from the Research model panel today` |
| Research opt-in (Part S, after the contract amendment of OD1) | `Include the research arm (runs the research models for every condition; values stay hidden until scoring)` |
| Share step (revision 3) | `Share my result` |
| Share notice | `Sharing sends nothing by itself. The app writes a file and you decide where it goes. Once the maintainer opens it, this data counts as seen and can never be a blind test of the app.` |
| Sealed step | `Sealed submission` |
| Sealed notice | `Your measurements stay with you until the maintainer has published predictions. Submit the commitment file, wait for the predictions, then release the targets file you committed.` |
| Sealed Declared reason | `tier Declared: table only, not checked` |
| Sealed table (Rev. 4, R10) [Q1] | `Sealed submissions (data owners' blocks, scored once)`, with the caveat of 15.7 item 1; the revision 3 title `Independent sealed blind tests` is withdrawn |
| Tier badges, flag line, export and fabrication notices | 14.7.5 |

Status words are lower-case kebab identifiers in data; the UI never shows PASS, FAIL, "validated" or "accuracy".

Row numbers in every message (Part P, U9) are 1-based file line numbers counting the header as line 1, so the first
data row is row 2, the number a spreadsheet shows. Every `sourceLocator` and every status locator points to a shipped,
tracked document, never to `.orchestra/GOAL.md` or another gitignored file (Part P, HUB-LP-14).

### 2.3 Evidence rules this feature obeys

1. Python is the only authority for parsing, prediction, statistics, grades, labels and verdicts. TypeScript renders
   and formats; it computes no statistic and no verdict (AGENTS.md).
2. User rows are always `Measured (user-supplied)`, never promoted, never imputed (a blank is a stated exclusion),
   never sent anywhere (no network in the path).
3. Exposed targets are spent: a not-blind report still shows numbers, labelled descriptive, and the attempt history
   is printed in every later report (GOAL kill criterion 3).
4. Different quantities are never compared as one: vapour-depression depth is never scored against melt-pool depth.
5. Constants carry a source and locator; anything that is a lead assumption is labelled so (`u_m assumed`).
6. Blind rule for builders: agents never print measured values from user fixtures or spent sets; tests assert
   structure, counts, hashes and labels. Synthetic fixtures are named and titled synthetic.
7. Every place protocol 1 departs from the MELT pre-registration or from GOAL is a numbered entry of the declared
   divergence list (7.7), carried in the protocol record and printed in every report. An undeclared departure is a
   defect.

## 3. Architecture

Four tiers, one authority (Python in the existing LPBF worker). Root below: `WT = Metalliksa-1-wt-hub`.

### 3.1 Tier A: Python library (new files, none in the fingerprint manifest)

| Module | Role |
|---|---|
| `python/lpbf_blind_stats.py` | Verbatim extraction of the MELT runner's pure functions from `research/ti64-primary` `e91d0fbd` (`python/tools/run_lpbf_melt_depth.py`, blob `2bff1378`): thresholds as strings compared as Fractions (`MEDIAN_MAX 0.20`, `P90_MAX 0.35`, `BIAS_MAX 0.10`, `MAXAPE_MAX 0.50`), `N_MIN 12`, `SIDE_MIN 4`, `U_MAX 0.10`, `LEVERAGE_LOW_CUT`, `LEVERAGE_HIGH_CUT 20`, `POWER_BAND 0.05`, `BEAM_BAND_GRADE_B 0.05`, `U_M_REL_FLOOR 0.03`, `U_M_F_UM`, `CV_POOL_MIN_CONDITIONS 3`, `CV_POOL_MIN_DF 3`, `BOOT_B 2000`, `BOOT_SEED 20261011`, `rank_quantile_exact` (+inf rule), `mean_signed_exact`, `block_statistics`, `bootstrap_intervals`, `index_bins`, `power_grade`, `beam_grade`, `block_grade`, `u_m_default_um`, `cv_pool`, `resolution_qualifier`, `reduce_conditions`, `arm_rels`, `leverage_qualifier`, `block_verdict`, `served_bins`, the fragile flip block of `score_phase`, `beam_d_um` (runner 666), `assert_no_target_loaded` (1390, applied to the blind input source's `columnsLoaded` and the protocol's target logicals), `served_index` (1499), plus `signflip_p_enumerate`, `signflip_p_dp`, `signflip_p` (830 to 900), `paired_differences` (901) and `FWHM_FACTOR = sqrt(ln 2 / 2)` (117) copied from `research/p3-cavity-astra` `c4470b01` `run_lpbf_p3_cavity.py`. Provenance header names blobs and line ranges. No git guards, amendment pins or research-branch imports (the P8 spec forbids runtime imports of mutable research branches). Only additions, each declared in 7.7: per-alloy leverage cuts (section 7.4), the `SERVED_NAME` map of `served_index` widened from two alloys to five, the not-formed-track and measurement-loss handling around `reduce_conditions` (4.4), and status words mapped at the report layer, never inside extracted code. |
| `python/lpbf_served_arms.py` | Single definition of served and research arms, shared by the blind test and the descriptive tool. `served_arm(alloy, P, v, d_1e2_um, T0_C, layer_um)` reproduces `lpbf_build_job_solver.py:910-1028` exactly while importing only `lpbf_thermal_solver.calculate_meltpool_physics`, `four_alloy_materials` (`resolve_alloy_id`, `ALLOY_MATERIALS`, `canonical_material_source`), `lpbf_build_job_material_snapshot` (`build_material_property_snapshot`, `build_build_job_identity`), the constants `BUILD_JOB_MODEL_ID` and `BUILD_JOB_SOLVER_REVISION` of `lpbf_job_cache`, and `lpbf_public_datasets.normalized_enthalpy` (Part P, R14). It never imports `lpbf_build_job_solver`, whose import loads about 21 further project modules and whose `_machine_calibrated_block` imports `lpbf_machine_calibrated_meltpool` lazily (`lpbf_build_job_solver.py:876`); the parity test calls `solve_lpbf_build_job` in the test process only. Steps: `resolve_alloy_id`, `ALLOY_MATERIALS`, `build_material_property_snapshot`, `canonical_material_source`, `build_build_job_identity(BUILD_JOB_MODEL_ID, BUILD_JOB_SOLVER_REVISION)`, then `calculate_meltpool_physics(thermal_mat, P, v, d, T0, layer, 110.0, "IR_1064nm", incline_angle_deg=0.0, process_seed=DEFAULT_PROCESS_SEED, prop_overrides=snapshot["thermal"], include_process_map=X)` with flat-plate absorption and the default CPU slice backend always, so the lazy imports of `powder_bed_raytracer` (`lpbf_thermal_solver.py:951`) and `warp_thermal_solver` (`:1281`) are never reached; the closure test asserts it. X is `False` only if the parity test proves identical geometry with `True`; otherwise `True`. Returns `depth_um` and `width_um` only when `meltPoolGeometry.extentStatus == "computed"`, else `{status: "failed", reason: "EXTENT_NOT_COMPUTED"}`; also `keyholeModel.fabbroDepth_um` (context) and the unrounded index from `lpbf_public_datasets.normalized_enthalpy` (the runner's leverage convention; the served response rounds it to 2 dp). IN625 is not a Build Job alloy: the direct thermal path with `"Inconel 625"`, flat-plate, Rosenthal, no overrides, `buildJobIdentity: null`, reason label `IN625_DIRECT_THERMAL_PATH`, and the result's `materialEvidence` (`legacy-estimated-secondary`) copied into the arm label. `sensitivity_arms()`: served at P x 0.95, P x 1.05, d x 0.95, d x 1.05 (MELT `POWER_BAND` and `BEAM_BAND_GRADE_B`); no served call evaluates research (P8 integration contract, 7.6). This module holds no research code: the research request builder and the adapter live in the separate research module of Part S (R13), outside the served-closure pin. `predictor_identity()`: section 3.6. |
| `python/lpbf_blind_research.py` (Part S, not shipped in Part P) | The research request builder and the closed P8 adapter of 15.3, in one research module hashed into the research member of the predictor identity (3.6), never into the served-closure pin, so a phase 6 edit cannot move that pin (R13). Imports no `lpbf_research_*` module (contract guard R-ISO-1). Protocol 1 v1 has no research module at all; the arm is `RESEARCH_NOT_REQUESTED` (7.6). |
| `python/lpbf_user_blind_inputs.py` | Metadata schema and validation, inputs CSV parsing (dialects, closed alias table, header whitelist checked before any data row, caps, base64 decode, UTF-8), structure checks, input-only exclusions (runner `parse_input_rows` rules), beam conversion, grades, block issues, design checks, preview. Must not import the targets parser. |
| `python/lpbf_user_blind_targets.py` | Targets CSV parsing, exact key join, `depth_status` rules, repeated-input check, commitment check. |
| `python/lpbf_user_blind_store.py` | Store root, layout, exclusive create (`open(mode="x")`), sha256 sidecars, read-only bit after write, content-addressed uploads, staging and rename (the commit point), ledger with sequence and previous-entry hash, OS-held store lock with its recorded lock domain (Part P, R17), start-of-mutation reconciliation (3.5), caps, listing of incomplete staging dirs, the reveal-or-score state gate shared by the artifact branch, the bundle job and the CLI, `scorer_source_hashes(paths)` (renamed from `source_identity` so it is not confused with `lpbf_source_identity`; hashes files by path through `lpbf_source_identity.canonical_source_bytes`, so LF and CRLF checkouts give the same hash, without importing them; Part P, R14), read-only tuple readers for the calibration stores (6.4 item 7). |
| `python/lpbf_user_blind_freeze.py` | Freeze: re-run preview, re-check required acknowledgements and overlap, identity checks, per-condition arm predictions, freeze record, receipt. Imports inputs, served arms, stats (design checks only) and store. Must not import `lpbf_user_blind_targets` or `lpbf_user_blind_score` (AST test), and asserts before its commit point that neither module is in `sys.modules` (Part P, ENG-17); the scorer identity is computed by `scorer_source_hashes`, which reads bytes and imports nothing. |
| `python/lpbf_user_blind_score.py` | Score: verify freeze, join targets, reduce, statistics per arm, coverage and common subset, qualifiers, fragile labels, blindness rule, scorer identity, report. |
| `python/lpbf_user_blind.py` | Façade for the worker: `USER_BLIND_RPC_TYPES` and `USER_BLIND_JOB_TYPES` (3.2.1), `validate_request(raw)` per type (closed keys, Phase 6a validation envelope so the route answers 422), `stage_request(p)`, `run_job(input)` (silent child, fixed error codes), `rpc(raw)` for the estimate RPC (preview, list, get), `enforce_user_blind_job_result(result, params)`, `filter_blind_log(text)`, `blind_document(result, name)` for the artifact branch, label constants. Lazy imports per job type keep the freeze path free of the targets parser. |
| `python/lpbf_spent_ledger.py` | Loader and checks for `data/benchmark/spent-ledger-v1.json`; used by the descriptive tool and by the blind test exposure check. |
| `python/tools/lpbf_user_blind.py` | Offline CLI for air-gapped labs on the same library: `templates [--from-plan plan.json]`, `preview`, `freeze`, `reveal`, `score`, `list`, `show`, `bundle`, `verify`, `export-protocol [--check]`, `pin-served-closure [--check]`, and in revision 3 `share`, `share-verify`, `share-import` (Mode A), `sealed-precheck`, `commit`, `check-predictions`, `release` (Mode B, user side). No network. The CLI goes through the same store functions and the same state gate as the worker: `show` prints predicted values and `bundle` writes a tar only when a reveal record or a score exists for the freeze, or when `--reveal "<phrase>"` is given, which writes `reveal-<n>.json` and the `revealed` ledger event first; otherwise both refuse with `REVEAL_REQUIRED`. `list` and `verify` print receipts, hashes, statuses and check results only, never a predicted or measured value. Run it in the same environment as the worker (both Windows or both WSL), because an `msvcrt` lock and an `flock` on a `/mnt` path do not exclude each other. |
| `python/tools/lpbf_spent_descriptive.py` | Offline producer of the descriptive record (section 8). |
| `python/lpbf_blind_share.py` (revision 3) | Mode A (14.3): deterministic share tar, consent, licence and attribution checks, ledger excerpt with redacted links; `share_verify(tar)` and `share_import(tar)` with the checks of 14.3.4, closed member names and caps (9.16), writes only under the shared-results root, drafts the spent ledger entry. Imports the store, the scorer (re-score) and `lpbf_served_arms` (re-predict); never a research module. |
| `python/lpbf_sealed_submission.py` (revision 3) | Mode B (14.4): commitment builder and checks (user side); the maintainer's sealed store (layout of 3.5, same lock, ledger and commit-point rules); the state machine of 14.4.3; import, run amendment builder (closed key set of MELT Amendment 6 item 14.4), freeze (served arms through `lpbf_served_arms`, the MELT runner's prediction file imported by hash, research subsets from route responses), publish, receive-targets, intake, tier events, score (`lpbf_blind_stats` under the sealed rule record, compared with the MELT runner's verdict file), result and record entry, `verify`. |
| `python/lpbf_submission_plausibility.py` (revision 3) | The flag-only checks of 14.7.2; pure functions; reads spent sets through `lpbf_spent_ledger`; returns codes and keys, never values. |
| `python/tools/lpbf_sealed.py` (revision 3) | Maintainer and reader CLI: `export-protocol [--check]`, `import`, `anchor`, `run-amendment`, `freeze`, `publish`, `receive-targets`, `intake`, `tier`, `score`, `record`, `status`, `verify`. No network; anchors (URLs, server times) are typed by the maintainer. |
| `scripts/research-route-batch.ts` (Part S, after OD1) | Explicit batch client for the P8 research route on the local server: reads a list of request bodies, runs the contract's band loop per request, writes one response file per request; authenticates with the server's bearer token when one is configured (`tokenAuth`, `server/security.ts:271`). Runs only when a person starts it (OD1). |

### 3.2 Tier B: worker transport (`python/lpbf_worker.py`, `python/lpbf_worker_rpc.py`; not fingerprint files)

All blind work runs inside the existing persistent worker. Every mutation is a queued job in its own child process
(freeze and score never share a process, like the P3 `spawn_scoring` split). Write-free reads ride the existing estimate
RPC.

1. Estimate RPC (`lpbf_worker_rpc._estimate`): when `payload.jobType` is in `USER_BLIND_RPC_TYPES`
   (`user-blind-preview`, `user-blind-list`, `user-blind-get`, 3.2.1) call `lpbf_user_blind.rpc(payload)` and return
   the document. These calls write nothing (no store file, no `.lpbf-jobs` folder, no sqlite row, no queue slot), call
   no thermal solver and read only committed store state (renamed freeze directories, exclusive-created records,
   complete ledger lines), so a freeze child writing at the same moment is never seen half done. Target cost: preview
   under 300 ms at the condition cap, list and get under 100 ms at the store cap (measured in phase 1; the RPC loop is
   single threaded, so a slow call would stall status polls). They are answered while a queued job runs, so loading
   the test list never waits behind a Build Job or a GPU pilot, and polling never grows `.lpbf-jobs` (phase 2 measures
   both). Bound route: `POST /api/lpbf/estimate` (`lpbf-estimate`).
2. `submit()`: new branch `elif job_type in USER_BLIND_JOB_TYPES`: `p = validate_request(raw)` (raises the validation
   envelope, no job row), then `stage_request(p)` writes every user document (canonical metadata JSON bytes, raw
   inputs bytes, raw targets bytes) into the blind store under `uploads/<sha256>.<kind>` (exclusive create; identical
   bytes reuse the file), and `p` is rewritten to hashes only. `input.json` in `.lpbf-jobs/<job>/` therefore holds the
   closed per-type form of 3.2.1 with hashes in place of content (`metadataSha256`, `inputsSha256`, `targetsSha256`)
   and no CSV or metadata content. Blind mutations bypass the generic result reuse in both `submit` and
   `submit-repeat` (forced `execution_scope="repeat"`); idempotency of mutations lives in the blind store. The one
   exception is `user-blind-open`, which writes nothing and is deduplicated on `(freezeKey, name, attempt, document
   sha256)`. Cache key for blind jobs is `sha256(canonical_json(p))`, not `fingerprint(p, m)` (which hashes every
   `python/*.py`). Per-type `timeout_s` (read by `execute()` at line 1017): freeze 180 s (served calls only; protocol 1
   sends no research request, 7.6), score 60 s, reveal 30 s, bundle 60 s, open 30 s; Part S adds share 60 s, sealed
   commit 30 s and sealed release 60 s.
   Submit errors (Part P, R15). `submit` for a blind type runs `validate_request` and `stage_request` inside its own
   `try`/`except BaseException`: a `BlindRefusal` (3.2 item 10) passes through with its code; any other exception
   becomes `BLIND_SUBMIT_INTERNAL` from the closed `BLIND_SUBMIT_ERROR_CODES` table with its fixed message. No
   exception text reaches the reply, because `rpc_error_response` would otherwise put `str(error)` into the HTTP 400
   body, and a `float()` message carries the cell text, so a target value could leak.
3. Child `main()`: `elif job_type in USER_BLIND_JOB_TYPES: result = run_job(input_data)`; no `write_artifacts`.
   The child's stdout and stderr are `progress.log` (`_spawn_execution_child`, line 637), which `execute()` copies
   into the sqlite `log` column (lines 1049 to 1082) and, through `_execution_failure_message`, into `error`; `GET
   /api/lpbf/jobs/:id` returns both. `run_job` is therefore silent by construction:
   (a) file descriptors 1 and 2 are redirected to `os.devnull` with `os.dup2` for the whole job (so prints from the
   solver and from C extensions are covered), and `warnings` are captured and dropped;
   (b) the only writes to the log go through one function, on a saved copy of the original descriptor, of two closed
   JSON frames, one per line: `{"blindProgress": {"stage": <closed list>, "k": int, "n": int}}` and
   `{"blindError": <CODE>}` (Part P, ENG-22); the log filter of item 4 accepts exactly these two shapes;
   (c) the blind branch has its own `try`/`except BaseException` ahead of the generic exception path (around line
   1230, which prints `str(e)`), maps every exception to a fixed code from the closed `BLIND_CHILD_ERROR_CODES` table
   (the refusal codes of 6.1 that can arise in a child, plus `SOLVER_EXCEPTION` and `INTERNAL_ERROR`), prints only
   `blind-error <CODE>` and exits 1. Exception messages and tracebacks are dropped; developers reproduce on synthetic
   data.
   A solver exception for one condition is not a job failure: that arm is `failed` with reason `SERVED_EXCEPTION`
   (APE +inf, 7.1). `run_job` always returns a `provenance` dict, because the child stamps `provenance.runtime_s` and
   `executionRuntime` unconditionally (lines 1211 to 1219).
4. Parent completion (`execute()` lines 1069 to 1079) and `get()` (lines 765 to 789): explicit
   `elif job_type in USER_BLIND_JOB_TYPES: enforce_user_blind_job_result(result, params)` instead of falling into
   `enforce_thermal_balances`. The enforcer checks the closed result schema, the honesty block literals and that no
   predicted value appears in any blind job result (recursive key and value scan). For blind jobs `execute()` also
   passes the log text through `filter_blind_log` before every `update(..., log=...)` and before
   `_execution_failure_message`: a line not of the two closed forms becomes `[blind: line dropped]`, so a stray print
   cannot reach the sqlite `log` or `error` column or the `GET` response even if (a) fails (a line is kept only when it
   parses as one of the two closed frames of item 3(b)). Timeout and cancel messages
   stay the existing fixed strings.
5. `get()` `requestSummary` for blind jobs: `{jobType, schema, freezeKey}` only.
6. `_archive_run_kind` returns `None` for blind types (today an unknown type falls through to `transient-thermal`), and
   `capture()` refuses blind job types explicitly ("blind tests are not archivable"), so the run archive and portable
   bundles never copy them.
7. `artifact()` branch for blind jobs: names are a closed set (`blind-receipt.json`, `blind-freeze.json`,
   `blind-report.json`, `blind-bundle.tar`; revision 3 adds `blind-share.tar`, served only when a score exists,
   `sealed-commitment.json`, `sealed-commitment-public.json`, `sealed-release.json` and `sealed-score-local.json`). The file is resolved in the blind store from the job result's validated
   `freezeKey` and attempt number (never from the client), checked against the size and sha256 the store sidecar and
   the job result declare, and state gated through the store's reveal-or-score gate: `blind-freeze.json` and
   `blind-bundle.tar` (both hold predictions; the tar contains `freeze.json`) are served only when a reveal record or a
   score exists for that freeze; `blind-report.json` only when it exists. The bundle job applies the same gate before
   it writes a tar, and the CLI `show` and `bundle` apply it too (3.1). Types: `application/json`,
   `application/x-tar`. Bound route: `GET /api/lpbf/jobs/:id/artifacts/:name` (`lpbf-job-artifact`), which already sets
   `Content-Security-Policy: default-src 'none'; sandbox` and `nosniff`.
8. Job results are small: the freeze result is the receipt (no predicted value); reveal, score, bundle and open results
   carry hashes, status words, counts and the declared documents only. Predictions and measured values are served from
   the blind store through the artifact branch, so `.lpbf-jobs` never holds a second copy of either. Every ledger event
   records the `jobId` of the job that wrote it, so `user-blind-get` can name, per document, a job whose artifact
   branch serves it; when that job folder no longer exists, the client submits `user-blind-open`.
9. Unchanged: queue cap 16 (shared with Build Jobs), RPC line cap 1,000,000 characters, `lpbf_worker_rpc.py` method
   table (no new RPC method), dedupe behaviour of every non-blind job type.
10. Refusals reach HTTP 422 (Part P, R15). `input_validation.ValidationError` accepts only its closed seven codes
    (`ERROR_CODES`, `python/input_validation.py:38-39`), so none of the 6.1 codes can use it. The blind code raises
    `lpbf_user_blind.BlindRefusal(code, message, detail)` with `code` from the closed `BLIND_REFUSAL_CODES` table (every
    code of 6.1 that can arise at preview or submit). `rpc_error_response` (`python/lpbf_worker.py:1277`) gains a second
    lookup beside the one for `input_validation`: when `lpbf_user_blind` is in `sys.modules` and the error is a
    `BlindRefusal`, the reply carries `errorKind: "validation"` and the Phase 6a envelope shape `{success: false,
    errorKind: "validation", error: {code, field, message, detail}}` with the blind code, and its `error` member is the
    fixed refusal message, never `str(error)` of another exception. `server/lpbfWorkerBridge.ts` (`validationEnvelope`,
    lines 35 to 40) already accepts any code string and the LPBF routes already map `LpbfWorkerValidationError` to HTTP
    422 (`routes/lpbfSimulation.ts:7`), so no bridge logic and no route changes; the bridge gains a test that a blind
    code reaches the 422 body unchanged. `detail` holds row numbers, column names and counts only, never a cell value.

Queue starvation: the worker runs one queued job at a time (`work()`, lines 997 to 1008), so a freeze delays a waiting
Build Job. The condition cap (section 4.3) is set from measured timing so that a freeze at the cap takes at most 60 s
(p95, warm worker, cold child, reference machine), and the UI states "a freeze can hold the simulation queue for up to
about a minute". Reveal, score, bundle and open make no solver call; preview, list and get are not queued at all.
Under the P8 integration contract no served call evaluates research, and protocol 1 sends no research request (7.6), so
P8 adds nothing to the freeze job. In Part S, the opt-in research step runs in the research lane before the freeze is
queued and never holds the worker queue (15.3); share, sealed commit and sealed release make no solver call.

### 3.2.1 Blind request types and closed payloads

Every payload is closed (unknown keys refused, booleans real booleans), `schema` is `lpbf-user-blind-request-1`,
`freezeKey` is 64 lower-case hex, file names follow 4.2 item 10, base64 fields follow 4.3. Each result carries the
honesty block of 2.1.

| Type | Path | Payload (keys required unless marked optional) | Result |
|---|---|---|---|
| `user-blind-preview` | estimate RPC | `{jobType, schema, metadata, inputsCsvBase64, inputsFileName}` | preview (4.5 item 1) |
| `user-blind-list` | estimate RPC | `{jobType, schema, page?: int >= 0, pageSize?: int 1 to 50}` | `{entries [{freezeKey, blockLabel, alloy, createdAt, counts, state (frozen, revealed, scored), attempts, latestStatus}], total, page, readOnly, sharedHost}`; receipt fields only |
| `user-blind-get` | estimate RPC | `{jobType, schema, freezeKey}` | receipt summary, reveal events, attempts with status words, `documents [{name, attempt or null, sha256, size, jobId, jobRecordPresent}]` for the documents the state gate allows; no predicted or measured value |
| `user-blind-freeze` | queued | `{jobType, schema, metadata, inputsCsvBase64, inputsFileName, previewSha256, overlapSha256, acknowledgements}` (`overlapSha256` copied from the reviewed preview; no `research` member in protocol 1, 7.6; Part S adds one in protocol 2, 15.3) | receipt (4.5 item 3) |
| `user-blind-reveal` | queued | `{jobType, schema, freezeKey, confirmation}` (exact phrase) | `{freezeKey, revealN, ledgerSeq, documents}` |
| `user-blind-score` | queued | `{jobType, schema, freezeKey, targetsCsvBase64, targetsFileName, declarations {viewedPredictionsBeforeFinalisingTargets}, acceptCommitmentMismatch}` | `{freezeKey, attempt, alreadyScored, statuses, documents}` |
| `user-blind-bundle` | queued | `{jobType, schema, freezeKey, revealConfirmation?: exact phrase}` | `{freezeKey, bundleN, sha256, size, documents}`. Refused at submit and again in the child with `REVEAL_REQUIRED` unless a reveal record or a score exists; with `revealConfirmation` the child writes `reveal-<n>.json` and the `revealed` event before the tar |
| `user-blind-open` | queued, deduplicated | `{jobType, schema, freezeKey, name (closed set of 3.2 item 7), attempt?: int >= 1}` | `{freezeKey, name, attempt, sha256, size}`; writes nothing; same state gate |
| `user-blind-share` (revision 3) | queued | `{jobType, schema, freezeKey, consent {includeTargets}, licence, publishAllowed, attribution?, evidenceManifest?}` | `{freezeKey, shareN, shareId, sha256, size, documents}`; refused with `SHARE_NO_SCORE` unless a score exists (14.3) |
| `user-sealed-precheck` (revision 3) | estimate RPC | `{jobType, schema, metadata, inputsCsvBase64, inputsFileName, targetsCsvBase64, targetsFileName, evidenceManifest?}` | structure checks of inputs and targets (4.2, 4.4), `targetsSha256` computed in Python, plausibility flags for the user only (14.7.2), counts and codes, never a value; writes nothing; no solver call |
| `user-sealed-commit` (revision 3) | queued | `{jobType, schema, metadata, inputsCsvBase64, inputsFileName, targetsSha256, evidenceManifest?, submitter?, licence, publishAllowed, confidential, declarations}` | `{commitmentId, documents}`; writes `commitments/<commitmentId>/`; refusals of 14.4.4 and, Rev. 4, `SEALED_LOCAL_TEST_OVERLAP` (15.4 item 7); identity and attribution are staged as hashed documents (15.6 item 9) |
| `user-sealed-check-predictions` (revision 3) | estimate RPC | `{jobType, schema, commitmentId, predictionsJsonBase64}` | hashes, counts and identities; `PREDICTIONS_INPUTS_MISMATCH` when the file names other inputs; writes nothing |
| `user-sealed-release` (revision 3) | queued | `{jobType, schema, commitmentId, targetsCsvBase64, targetsFileName, predictionsJsonBase64}` | `{commitmentId, releaseN, documents}`; `TARGETS_HASH_MISMATCH` and `PREDICTIONS_FILE_NOT_CHECKED` refusals; writes `release.json` and `sealed-score-local.json`. Rev. 4: the predictions file is referenced by `predictionsSha256` after chunked staging, not sent inline (15.4 item 8) |
| `user-blind-stage-chunk` (Rev. 4, Part S) | queued | `{jobType, schema, uploadSha256, index, count, chunkBase64}` (chunk at most 300,000 characters) | `{uploadSha256, received, complete}`; assembles and hash-checks the upload when the last chunk arrives (15.3 item 7) |

This table is the one authoritative list of request types (Part P, ENG-16). Budgets for the estimate RPC types, all
measured in phase 1 and again in phase 4 with every type present: preview 300 ms at the condition cap, list 100 ms and
get 100 ms at the store cap (Part S adds sealed precheck 300 ms and predictions check 100 ms). RPC reads take no
blocking lock: they try the store lock once without waiting (at most 50 ms) and otherwise read committed records only.
In Part P the freeze payload has no `research` member; a request carrying one is refused with `METADATA_FIELD`
(unknown key) until protocol 2 (7.6).

`USER_BLIND_RPC_TYPES` and `USER_BLIND_JOB_TYPES` are the only two sets. A test asserts that every type in them has a
closed schema, a Python validator, a TypeScript result validator and a refusal test, and that no other `user-blind-*`
type is accepted by `submit`, `submit-repeat` or the estimate RPC.

### 3.3 Tier C: Node

One change, no route change. `server/pythonRuntime.ts` forwards the blind environment to a WSL worker. Today only
`METALLIKSA_JOB_ROOT` is listed in `WSLENV` (`wslJobRootEnvironment`, lines 82 to 96), so under WSL
`METALLIKSA_READ_ONLY` and `METALLIKSA_USER_BLIND_ROOT` never reach the worker and `STORE_READ_ONLY` would fail open
(`METALLIKSA_READ_ONLY` is checked only in Node routes today: `routes/lpbfRuns.ts:16`, `routes/lpbfSources.ts:11`). The
function is generalised to forward `METALLIKSA_USER_BLIND_ROOT` with `/p` under the same drive-letter rule as the job
root (UNC and `\\wsl$` refused loudly), `LPBF_MACHINE_CALIBRATION_DIR` with `/p` under the same rule (Part P, R16:
without it the calibration-store overlap check of 6.4 item 7 looks in the wrong place under the default WSL worker and
finds nothing), and `METALLIKSA_READ_ONLY`, `METALLIKSA_HOST` and `METALLIKSA_USER_BLIND_SINGLE_USER` as plain values;
it still returns a new object and never mutates `env`. Today the function returns early when `METALLIKSA_JOB_ROOT` is
unset (`server/pythonRuntime.ts:88`), which would drop every other variable, including `METALLIKSA_READ_ONLY`; the
generalised function forwards each variable on its own (Part P, R16). `tests/python-runtime.test.ts` gains cases for
the forwarded list, including the case with `METALLIKSA_JOB_ROOT` unset, and the worker reports `readOnly`,
`sharedHost`, `storeId` (the id from `store.json`, never a path; Part P, ENG-15) and `lockDomain` in the
`user-blind-list` result so the UI and the phase 2 WSL check can see what arrived.

Otherwise unchanged. `routes/lpbfSimulation.ts` already gives the same-origin guard, login and CSRF through
`applySecurity`, the rate limit and the 422, 503 and 400 mapping; the routes used (`POST /api/lpbf/jobs`,
`POST /api/lpbf/jobs/repeat`, `POST /api/lpbf/estimate`, `GET /api/lpbf/jobs/:id`,
`GET /api/lpbf/jobs/:id/artifacts/:name`) are bound registry operations of the legacy `3d-distortion-lab` contract
(`_worker` authorities in `LEGACY_OPERATIONS`, `python/module_registry.py:160-168`). No duplicate `LEGACY_OPERATIONS`
rows are added (decided: the call is documented in the unwired research-hub contract builder instead, 10.2). The
pre-existing 50 MB global parser is not changed: the worker RPC line cap (1,000,000 characters) bounds what reaches
Python and Python enforces the per-file caps.

### 3.4 Tier D: TypeScript (renders, never computes)

1. Placement: a sixth Research Hub tab, id `blind-test`, label `Your blind test` (unnumbered), added in place to the
   `tabs` array (`AdvancedResearchHub.tsx:12`), rendered after the `catalog` line; the "Active research brief"
   selector (line 34) is hidden on this tab so it does not read as step 5 of a brief. `ResearchTab` union
   (`useResearchStore.ts:7`) and the persisted `activeTab` whitelist (line 211) gain `blind-test` in place.
2. Discoverability: a call to action `Test the model on your own tracks` in the Measured track catalog tab
   (`MeltPoolMeasuredTrackPanel`), a one-line pointer at the top of the Melt Pool vs Measurements lab
   (`ExperimentalValidationLab`; asserted strings untouched, no `sha256` or `citation` text), a link from the descriptive
   panel, and palette keywords for `research-hub` (`blind test`, `your data`, `upload measurements`). Each link calls
   `useResearchStore.getState().setActiveTab("blind-test")` and dispatches `metallix-navigate-tab` (pattern of
   `src/components/ResearchIntegrationPanel.tsx:20`, which sits in `src/components/`, not under `research/`).
3. Components under `src/components/research/` (reachable through the hub): `BlindTestPanel` (stepper, ordered list
   with `aria-current="step"`), `BlindTestMetadataForm`, `BlindTestInputsStep`, `BlindTestReceiptView`,
   `BlindTestTargetsStep`, `BlindTestReportView` (`React.lazy`, lightweight SVG, no Recharts), `BlindTestList`, and
   `blindTestHelp.ts` (help text as data). All inputs use `ResearchControls` `Field` and `Select` (useId plus htmlFor).
4. `src/data/lpbfUserBlind.ts`: types, closed-key validators `checkedBlindPreview`, `checkedBlindReceipt`,
   `checkedBlindReport`, `checkedBlindList`, `checkedBlindGet` and one result validator per queued type of 3.2.1
   (throw on any honesty literal mismatch, unknown status word, unknown key, or a prediction-like key in a preview,
   receipt, list, get or job result), template header lists and alias table read from the protocol record JSON,
   header-only check helpers, CSV formatting for exports. `csvCell` and `toCsv` in `src/data/lpbfExperimentPlan.ts`
   (lines 187 and 192) are module-private today; 10.2 exports them unchanged. The blind exports wrap them with
   `blindCsvTextCell`, which neutralises any text cell starting with `=`, `+`, `-`, `@`, tab or carriage return by a
   leading apostrophe; numbers are passed as numbers and never prefixed (a negative signed percent stays a number).
5. `src/services/lpbfUserBlindClient.ts`: submit through `POST /api/lpbf/jobs`; preview, list and get through
   `POST /api/lpbf/estimate`; document fetch through the artifact route of the job named by `user-blind-get` (or a
   `user-blind-open` job when `jobRecordPresent` is false) with a SubtleCrypto sha256 check of the bytes against the
   declared hash; typed errors (worker unavailable 503 with Retry-After, queue full, 413, 422 with code). Polling uses
   `useVisiblePolling` so a hidden hub pauses; only queued jobs are polled, and the pending job id is kept in the store
   so a reload resumes.
   Secure-context limit: `crypto.subtle` is undefined on plain http to a non-loopback address. The client checks
   `globalThis.crypto?.subtle` once. Without it, the commitment step replaces the file picker by a paste field with the
   instruction `Hashing needs https or localhost. Compute the SHA-256 of the targets file with sha256sum or certutil
   -hashfile <file> SHA256 and paste it.`, and the browser hash check of fetched documents is skipped and shown as
   `Browser hash check unavailable on this connection; the worker checked the hash.` No bundled hash code is added.
6. `src/store/useUserBlindStore.ts`: persisted key `metalliksa.lpbf.userBlind.v1`, defensive whitelist merge
   (`useLpbfWorkflowStore` pattern), every storage access in try and catch; holds the metadata draft, pending job ids
   and known freeze keys with receipt summaries only, never predictions, measurements or CSV text.
7. Static demo: the tab renders `DemoUnavailable`. Read-only installation: the worker refuses mutations and the UI
   shows the message. Shared host: when `user-blind-list` reports `sharedHost: true`, or the page's own
   `location.hostname` is not `localhost`, `127.0.0.1` or `[::1]`, the tab shows a permanent warning `Every signed-in
   user of this server can list and open every blind test on it, including your measurements and the frozen
   predictions.` (enforcement is in the worker, 9.7).
8. Parsed inputs screen (Part P, R20). Before the acknowledgement boxes, `BlindTestInputsStep` shows the table the
   preview returns: per condition the parsed power, speed and beam in canonical units, the header unit read and the
   conversion applied (4.2 item 4), the beam quantity, definition and 1/e2 value, tracks and sections, so a unit or
   column mistake is visible before anything is frozen. These are inputs only, never a prediction.
9. Revision 3 (Part S; not in the Part P check).
   a. Research relay (15.3; only after the contract amendment of OD1): `src/services/lpbfUserBlindClient.ts` runs the band loop per condition through
      `pythonComputationService.solveLpbfResearchModels` (the contract's client method), sequential and awaited, with
      Cancel; `src/data/lpbfUserBlind.ts` gains the closed extractor `extractBlindResearchSubset(response)` (the members
      of 15.3, `requestKey`, `identity` and `clientRequestId`; it throws on an unknown key in those members). The
      subsets live only in the pending freeze request; nothing renders, persists or logs them (sentinel test, 11.2
      item 7).
   b. Components: `BlindTestShareStep` (consent per part, licence, attribution, evidence list, file list before export),
      `SealedSubmissionPanel` (precheck with the user's own flags, identity form with a `public` choice per field and the
      public-and-permanent notice, commitment export, predictions file check, release preparation, local score view),
      `SubmissionTierBadge` and the tier and flag strings of 14.7.5, all under `src/components/research/`, reachable from
      the blind-test tab. Evidence files are hashed in the browser and listed; their bytes are never sent to the server.
   c. Closed checkers in `src/data/lpbfSealed.ts`: commitment, public commitment, predictions, release, result, evidence
      manifest, share manifest, each closed, with the scope literals of 2.1.
   d. No non-same-origin request anywhere in these modules; links to the submissions repository and Zenodo are text
      with a copy button (14.1 item 3).
   e. `useUserBlindStore` may persist commitment ids, share numbers and their states, never targets, research subsets,
      evidence bytes or identity fields other than the user's own draft.

### 3.5 Storage

`METALLIKSA_USER_BLIND_ROOT`, default `<repo>/.runtime/user-blind` (already ignored by `.gitignore:21` and
`.dockerignore:20`), resolved worker side. When the worker runs in WSL, Node forwards the variable through `WSLENV`
(3.3) and never reads the store itself. Docker: `/data/user-blind`.

```
<root>/store.json                      schema, storeId, createdAt
<root>/store.lock                      OS-held lock (msvcrt or flock), released by the OS when the holder dies
<root>/ledger.jsonl                    {seq, at, event, freezeKey, jobId, hashes, prevEntryHash, entryHash}
<root>/uploads/<sha256>.metadata.json  canonical metadata bytes
<root>/uploads/<sha256>.inputs.csv     raw inputs bytes
<root>/uploads/<sha256>.targets.csv    raw targets bytes (exist only after a score submit)
<root>/index/conditions.jsonl          {freezeKey, alloy, tuples [P_W, v_mm_s, d_1e2_um]} for overlap checks (derived data)
<root>/freezes/<freezeKey>/freeze.json (+ .sha256)
<root>/freezes/<freezeKey>/reveal-<n>.json (+ .sha256)
<root>/freezes/<freezeKey>/score-<n>.json (+ .sha256)
<root>/freezes/<freezeKey>/bundles/bundle-<n>.tar (+ .sha256)
<root>/.staging/<random>/              freeze staging; renamed into place; leftovers listed as incomplete, never used
```

Revision 3 adds to the user's store `freezes/<freezeKey>/shares/share-<n>.tar (+ .sha256)` (Mode A) and
`commitments/<commitmentId>/` with `commitment.json`, `commitment-public.json` (confidential variant),
`predictions-check-<n>.json`, `release-<n>.json` and `sealed-score-local.json`, each with a sidecar (Mode B, user side).
The maintainer's tools use two further roots, never the maintainer's own blind store: `METALLIKSA_SHARED_ROOT` (default
`<repo>/.runtime/shared-results/`: one directory per imported share, plus `index/seen-tuples.jsonl`) and
`METALLIKSA_SEALED_ROOT` (default `<repo>/.runtime/sealed-submissions/`: `store.json`, `store.lock`, `ledger.jsonl` and
`submissions/<commitmentId>/` with the files of 14.4.2). Both sit under the ignored `.runtime`, follow the lock,
exclusive-create, sidecar, ledger and reconciliation rules above, and are written only by the CLI (no worker job, so no
WSL forwarding is needed).

Ledger events: `frozen`, `revealed`, `score-refused` (the code and the sha256 of the refused targets file, never a
value; Part P, PI-15), `commitment-mismatch`, `scored`, `bundle-exported`,
`reconciled` (names the event it restored); revision 3 adds `share-exported`, `commitment-exported`,
`predictions-checked`, `release-prepared`, `release-refused` (user store) and the sealed events of 14.4.3 (sealed
store). The ledger never holds measured values, predictions or free text; `jobId`
is the worker's fixed-format job id. No delete API: history is evidence; the user guide explains manual removal. Caps:
500 freezes, 200 MB total; beyond them new uploads are refused (`STORE_FULL`). Mutations are refused when
`METALLIKSA_READ_ONLY=true` reaches the worker (`STORE_READ_ONLY`; forwarded under WSL, 3.3) and on a shared host
(`STORE_SHARED_HOST`, 9.7).

Crash consistency. A timeout or cancel kills a child at any point (`execute()` `terminate_child`, `cancel()`), so every
mutation is written to survive a kill at each step:

1. Lock: `store.lock` is opened `a+b` and locked with `msvcrt.locking(LK_NBLCK)` on Windows or
   `fcntl.flock(LOCK_EX | LOCK_NB)` elsewhere, the pattern of the worker's own `worker.lock`
   (`lpbf_worker.py:1240-1248`). The OS releases it when the holder dies, so a killed job never leaves a stale lock and
   nobody deletes a file by hand. A busy lock is retried for up to 10 s, then `STORE_LOCKED` (the message names the
   holder's job id when known). Lock domain (Part P, R17): an `msvcrt` lock taken by a Windows process and an `flock`
   taken by a WSL process on the same drvfs folder do not exclude each other, so concurrent appends could fork the
   ledger chain. `store.json` records `lockDomain` (`windows` or `posix`) when the store is created; a process of the
   other domain may read but refuses every mutation with `STORE_LOCK_DOMAIN` (`This store is used by the <domain>
   worker. Run the CLI in the same environment as the worker.`).
2. Commit points: a freeze is committed by the rename of `.staging/<random>/` to `freezes/<freezeKey>/` (written and
   fsynced before the rename); a reveal, score or bundle is committed the same way, as a directory: the record and its
   sidecar are written and fsynced into `.staging/<random>/` and the directory is renamed to
   `freezes/<freezeKey>/reveal-<n>/`, `score-<n>/` or `bundles/bundle-<n>/` (Part P, R17), so a record never exists
   without its sidecar or the reverse. The attempt number n, the `alreadyFrozen` check and every other existence check
   are computed after the lock is taken and repeated there, never before it (Part P, R17). Servability and every state gate read the committed files, never the ledger, so a killed
   reveal whose record exists counts as revealed (the conservative reading).
3. Ledger and index after the commit point: the `frozen`, `revealed`, `scored` or `bundle-exported` event and the index
   tuples are appended (and fsynced) only after the commit point, still under the lock. A kill before the commit
   leaves no ledger event; a kill after it leaves a committed record without its event.
4. Reconciliation at the start of every mutation, under the lock: a committed record without its ledger event gets the
   event appended with `reconciled` marking it; a trailing ledger line without a newline (a killed append) is cut after
   the chain up to it verifies, and the cut is itself a `reconciled` event; `index/conditions.jsonl` is rebuilt from the
   committed freezes when it disagrees with them; a ledger event whose record is missing can only come from outside
   tampering and is reported by `list`, `get` and `verify` as `ledger-dangling`, never used for overlap or state.
   Readers on the estimate RPC see committed records only and tolerate a missing trailing event.
5. Tests kill every mutation type (freeze, reveal, score, bundle, and in Part S share, commit and release) at each step (after the staging write, after the lock, after the
   rename or exclusive create, during the ledger append, after the ledger append, during the index append) through a
   test-only fault hook (a module-level no-op function the test replaces in the spawned child, never an environment
   switch in production code), then run the next mutation and assert: no manual action needed, the record is either
   fully committed or absent, every committed record has exactly one ledger event, no dangling event, and the index
   equals the committed freezes. The matrix runs on a native folder and on a drvfs folder (`/mnt/<drive>/...`) under
   WSL (Part P, R17).

### 3.6 Predictor identity and scorer identity

Predictor identity (recorded at preview, freeze and score):
`{implementationFingerprint (live lpbf_simulation.implementation_fingerprint()), pinnedFingerprint (lpbf_fingerprint_pin),
servedClosure {pinSha256, files [{path, liveSha256, pinnedSha256}]}, buildJobSolverRevision, buildJobModelId,
per-alloy materialPropertySha256, materialAuthorityRevisionSha256, buildJobIdentitySha256, research {requested: false,
reasonCode: "RESEARCH_NOT_REQUESTED", contract: "research/p8-research-arm 14e13ea8"}, heatSource "rosenthal",
absorptionModel "flat-plate", includeProcessMap, python, numpy and scipy versions}`. The research member is outside the
served-closure pin. In Part P it is a constant (7.6). The full research member of a later protocol (research module
hash, research pin, schemas, request keys) is Part S (15.3).

Served-closure pin. `IMPLEMENTATION_SOURCE_FILES` (`python/lpbf_simulation.py:44-81`) does not cover every module the
served arm runs through, so the fingerprint alone cannot make "served" mean "the reviewed served model". A committed pin
`data/blind/served-closure-pin-v1.json` (generated and checked by `python/tools/lpbf_user_blind.py pin-served-closure
[--check]`) lists, for every project module the served arm loads that is not in `IMPLEMENTATION_SOURCE_FILES`, its
hash through `lpbf_source_identity.canonical_source_bytes` (LF and CRLF checkouts hash alike; Part P, R14). Known
members today: `python/lpbf_build_job_material_snapshot.py` (`prop_overrides` snapshot and Build Job identity),
`python/lpbf_job_cache.py` (`BUILD_JOB_SOLVER_REVISION`, `BUILD_JOB_MODEL_ID`), `python/lpbf_public_datasets.py`
(leverage index) and `python/lpbf_served_arms.py`; the generator writes whatever the closure test finds, and no
research module is ever a member (R13). The import-closure test runs in a fresh interpreter, imports
`lpbf_served_arms`, then executes `served_arm` and `sensitivity_arms` once for each of the five alloys (so lazy imports
are caught, not only module-level ones), collects every loaded module whose file lies under `python/`, and fails when
one is neither in `IMPLEMENTATION_SOURCE_FILES` nor in the pin, or when `lpbf_build_job_solver`,
`lpbf_machine_calibrated_meltpool`, `powder_bed_raytracer`, `warp_thermal_solver` or any `lpbf_research_*` module is
loaded (Part P, R14). The freeze
refuses with `PREDICTOR_NOT_PINNED` when the live fingerprint differs from the fingerprint pin or any closure file
differs from the closure pin (the message names the files). A closure pin change is a reviewed commit, like the
fingerprint pin. Each job runs in a fresh child process, so a stale import cannot freeze.

Scorer identity (recorded at freeze and at score, separate from the predictor identity):
`{scoreSourcesSha256 (canonical source bytes of lpbf_blind_stats.py, lpbf_user_blind_score.py,
lpbf_user_blind_targets.py and lpbf_spent_ledger.py, read by store.scorer_source_hashes without importing them), statsConstants (the threshold strings,
N_MIN, SIDE_MIN, U_MAX, the leverage cuts, U_M floors, BOOT_B, BOOT_SEED), protocolSha256, numpy version}`.
`protocolSha256` hashes the rules part of the protocol record only (4.6); label sentences sit in the wording table and
never enter an identity.

At score both blocks are read again; predictions are never recomputed.

1. Predictor identity differs: `predictor.changedSinceFreeze` and the label `predictor changed since freeze; this result
   scores the frozen predictions`.
2. Scorer identity differs (a scoring bug fix, a numpy change that moves the bootstrap): `scorer.changedSinceFreeze`
   and the label `scoring code changed since freeze; this result uses the scorer present at score time`, with both
   hashes printed, so a change of scoring after the freeze is visible on its own and never disguised as a predictor
   change.
3. `protocolSha256` differs under the same `protocolId`: refused (`PROTOCOL_CHANGED`), because a released protocol is
   immutable (4.6); a new protocol id needs a new freeze.
4. Wording changes (Q1 approvals) change neither identity and produce no label.

## 4. Data model and CSV templates

All schemas are closed: unknown keys refused, booleans real booleans, numbers finite. Vocabularies, aliases, caps and
template columns live in one generated record (4.6) read by Python and TypeScript.

### 4.1 Metadata, schema `lpbf-user-blind-metadata-1`

Defaults are conservative: a default never raises a grade, and a missing value is an issue or a refusal, never a
silent value. Every field has a help disclosure that says what it is and how it changes the grade or status.

| Field | Values | Effect |
|---|---|---|
| `blockLabel` | text 1 to 80 matching `^[A-Za-z0-9 ._()/-]{1,80}$`, not starting with `= + - @`, no tab or line break; display only | none; anything else refuses (`METADATA_FIELD`), and exports neutralise text cells anyway (3.4 item 4) |
| `mode` | `pre-measurement` \| `post-measurement` (required, no default) | blindness status (6.4) |
| `alloy` | `Ti-6Al-4V` \| `AlSi10Mg` \| `316L` \| `IN718` \| `IN625` (required) | served path; leverage cut |
| `quantity` | `melt-pool-depth` (protocol 1 scored) \| `vapour-depression-depth` (descriptive, phase 6) | arms scored |
| `depthBoundary` | `etched-fusion-boundary` \| `unetched-contrast` \| `other` | non-etched: block issue (observable identity; divergence D2) |
| `measurementMethod` | `optical-cross-section` \| `sem-cross-section` \| `other` | recorded |
| `depthDatum` | `original-surface` \| `powder-top` \| `cap-top` \| `depth-plus-height` \| `unresolved` (default `unresolved`) | not `original-surface`: block issue |
| `reduction` | `per-section-raw` \| `per-track-mean-of-sections` \| `track-value-released` \| `condition-mean-released` \| `maximum-only` \| `single-selected-section` (required) | last two: block issue `reduction mismatch` (MELT `REDUCTION_UNUSABLE`). `condition-mean-released` with one row per condition can never meet the resolution qualifier (no track scatter, so `cv_pool` cannot form), and the preview says so as the best reachable status; the help tells users to upload one row per track, or per section with `track_id` and `section_id`, and that a mean-plus-SD sheet is not accepted (an SD column is an unknown header) (Part P, R20) |
| `crossSectionLocation` | `steady-state-mid-track` \| `several-locations` \| `near-track-start-or-end` \| `unstated` (default `unstated`) | last two: block issue (divergence D3) |
| `beam.diameter_um` | number or null (block value when inputs carry no `spot_um`) | refusal if neither given |
| `beam.quantity` | `diameter` \| `radius` (required, no default) | what `beam.diameter_um` and the `spot_um` column carry; `radius` values are doubled before the definition conversion, and the factor is frozen in `conversion`. Help text names the case it guards against: a 37.5 um value that may be a radius of a 75 um beam (the KU Leuven reading in 8.2). Label `beam size declared as radius (doubled)` |
| `beam.definition` | `1/e2` \| `D4sigma` \| `FWHM` \| `unstated` (default `unstated`) | unstated read as 1/e2, beam grade C, label; FWHM converted with `FWHM_FACTOR`; D4sigma taken as 1/e2 for a Gaussian; input, factor and converted value frozen |
| `beam.basis` | `measured-work-plane` \| `measured-other-plane` \| `nominal` (default `nominal`) | beam grade |
| `beam.profile` | `gaussian` \| `top-hat` \| `ring` \| `unknown` (default `unknown`) | `top-hat` or `ring`: block issue (the served model is Gaussian; divergence D4); `unknown`: label `beam profile not stated (Gaussian assumed by the served model)`, not an issue |
| `beam.uncertaintyReleased` | bool, default false; `beam.u_k1_um` number or null | beam grade |
| `power.basis` | `measured-at-workpiece` \| `measured-elsewhere` \| `commanded` \| `unstated` (default `commanded`) | power grade (unstated is C, as commanded) |
| `power.meterNamed`, `power.uncertaintyReleased` | bool, default false; `power.u_k1_rel` number or null | power grade; declared uncertainty above the 5 % fragility band is labelled |
| `wavelength_nm` | number (required) | outside 1030 to 1100: refusal |
| `substrate.kind` | `bare-plate` \| `powder-layer` (required) | powder layer: `descriptive-not-scored` (served model is flat-plate, MELT Amendment 6 item 6) |
| `substrate.layerThickness_um` | 5 to 200, required for powder layer, null for bare plate | layer argument (bare plate passes the Build Job default 40, see 7.5) |
| `substrate.amSubstrate` | bool, default false | u_m default f |
| `substrate.thickness_mm` | number or null | null: block issue |
| `substrate.surfacePreparation` | `machined` \| `ground` \| `polished` \| `blasted` \| `as-built` \| `other` \| `unstated` | unstated: block issue |
| `substrate.alsi10mgState` | `as-built` \| `heat-treated` \| `unstated` (default `unstated`); required for AlSi10Mg, null otherwise | recorded (MELT `constants_amendment.substrate_state`, Amendment 7). The P8 research arm fixes the as-built state (P8 A4 item 3) and the served P7b ledger uses the build-direction as-built convention (P8 section 3); `heat-treated` or `unstated` gives the label `plate state differs from the as-built property convention` on each AlSi10Mg arm whose property source Astra confirms as as-built in phase 0, the research arm always |
| `preheat_C` | number, required; `preheatBasis` `measured` \| `set-point` \| `nominal-ambient` | refusal if missing (MELT makes it a block issue; divergence D5); `nominal-ambient` labelled |
| `atmosphere` | `argon` \| `nitrogen` \| `helium` \| `vacuum` \| `air` \| `other` \| `unstated` | unstated: block issue |
| `replication` | `tracksPerCondition` int 1 to 20, `sectionsPerTrack` int 1 to 20, `rowsAreSeparateTracks` bool | checked against the file at preview |
| `depthUncertainty` | `basis` `per-row` \| `block` \| `not-released` (default), `u_um` number or null, `coverageFactor` 1 \| 2 | u_m = u / k; not released: MELT default and label `u_m assumed` |
| `chemistry` | `basis` `certified-heat-analysis` \| `supplier-nominal` \| `unstated`; `sulfur_ppm`, `oxygen_ppm` number or null | recorded; label `S and O certified` or `S and O flagged missing`; not a served model input |
| `independence` | `predictionsViewedBeforeFreeze` `no` \| `yes` \| `unsure` (required); `dataPreviouslyPublished` `no` \| `yes` \| `unknown`; `publishedDoi` text or null; `usedForMachineCalibration` bool (required) | blindness (6.4 items 1, 5, 7 and 8); `unknown` publication: block issue `independence not established` (MELT item); `yes` with `mode: pre-measurement` refuses (`METADATA_FIELD`) |
| `targetCommitment` | `{sha256: 64 hex}` or null; only in post-measurement mode | blindness `blind-committed` when matched |
| `csvDialect` | `comma-dot` (default) \| `semicolon-dot` \| `semicolon-comma` | parsing |

Help text of `predictionsViewedBeforeFreeze` names every place a served depth is visible, so "no" is an informed
answer: the Build Job result, the process window, the thermal route (melt-pool cross-section lab), the Dataset
Comparison lab including the new spent-set descriptive panel (section 8), the Melt Pool vs Measurements lab, the
machine-calibration block, the experiment plan panel, the Research model panel of the P8 contract (Melt Pool lab and
Build Job Decision lab; revision 3), and any CLI that prints a served or research depth. A test pins that the help
data lists each of these surfaces.

Acknowledgements are not metadata. They are a top-level field of the freeze request (5 step 5, 3.2.1):
`acknowledgements {predeterminedInconclusive?, powderLayerDescriptive?, exposedDescriptive?, publishedConditionOverlap?,
calibrationOverlap?}`, each `true` when present, required when the preview predicts that status. They are outside
`metadataSha256` and outside `previewSha256`, so ticking a box never causes `PREVIEW_DRIFT`; they are recorded in the
freeze record and the receipt.

No free-text notes field (keeps payloads closed). Field names map onto the existing `METHOD_COLUMNS` vocabulary
(`depthDatum`, `beamDiameterDefinition`, `measuredPowerW`, `crossSectionLocation`, `replicates`).

### 4.2 inputs.csv (prediction phase whitelist)

Canonical columns, in any order: `condition_id`, `track_id`, `section_id`, `power_W`, `speed_mm_s`, `spot_um`,
`power_u_k1_W`.

1. Required: `power_W`, `speed_mm_s`; `spot_um` unless `beam.diameter_um` is set.
2. Keys: either `condition_id` is present, or `track_id` is present and unique per row group, in which case conditions
   are derived from identical `(power_W, speed_mm_s, spot)` (MELT rule). This makes the experiment-plan
   `measurement_template.csv` usable once its measurement and notes columns are removed, and the CLI
   `templates --from-plan` and a plan-panel button (phase 4) write a ready inputs file from a plan.
3. `section_id` only with `track_id`. Repeated rows of one condition without `track_id` need
   `replication.rowsAreSeparateTracks`; otherwise refused (sections and duplicates are never replicates).
4. Closed alias table (case-insensitive, every mapping echoed back). A trailing bracketed or suffixed unit is read,
   never ignored (Part P, R20): closed unit table `power_W` and `power_u_k1_W`: `W` (factor 1), `kW` (1000);
   `speed_mm_s`: `mm/s` (1), `m/s` (1000), `mm/min` (1/60); `spot_um`: `um`, `µm`, `micron` (1), `mm` (1000). A known
   unit is converted and the factor is echoed in the preview and the parsed inputs screen (3.4 item 8) and frozen in
   `conversion`; an unknown unit refuses with `HEADER_UNIT_UNKNOWN`; a header without a unit (`P`, `power`, `v`,
   `speed`, `spot`) is read in the canonical unit with the label `unit not stated, read as <unit>`. Aliases:
   `power_W`: `P_W`, `P`, `power`, `laser_power_W`, `Power (W)`; `speed_mm_s`: `v_mm_s`, `v`, `speed`,
   `scan_speed_mm_s`, `Velocity (mm/s)`, `Speed (mm/s)`; `spot_um`: `beam_um`, `beam_diameter_um`, `spot`,
   `Spot (um)`; `condition_id`: `condition`; `track_id`: `track`; `section_id`: `section`; `power_u_k1_W`: `P_u_k1_W`.
   `d_um` and `D_um` are deliberately not aliases (they collide with depth). Two headers mapping to one canonical name
   refuse (`AMBIGUOUS_ALIAS`).
5. Any header matching `/depth|width|height|cap|area|penetration|remelt|d_exp|w_exp|d_obs|aspect/i`, or equal
   (case-insensitive) to `d`, `w`, `D`, `W`, refuses with `INPUTS_TARGET_COLUMN`. Any other unknown header, including
   `notes`, refuses with `INPUTS_UNKNOWN_COLUMN` (an unfamiliar name may hide a measurement). The header line is
   checked before any data row is parsed (runner `FileInputSource` and `TargetColumnRequested` design). The
   `INPUTS_TARGET_COLUMN` message names the matched token, because legitimate input words such as `layer height` or
   `hatch area` also match (Part P, U11). Before any header rule, the header line is sniffed for its separator: a header
   with `;` and no `,` under `comma-dot`, or the reverse under a semicolon dialect, refuses with `DIALECT_MISMATCH` and
   the header-level message of 6.1, so a semicolon export never shows up as one unknown column (Part P, R20).
   Required columns missing refuse with `INPUTS_COLUMN_MISSING`; a file with a header and no data row refuses with
   `FILE_EMPTY`; a `csv.Error` (unterminated quote, field count differing from the header) refuses with
   `CSV_MALFORMED` and the row number (Part P, R15).
6. Values: plain decimals (decimal point, or decimal comma only in the declared `semicolon-comma` dialect), finite,
   no units or thousands separators. Ranges: power 10 to 2000 W, speed 1 to 10000 mm/s, spot 10 to 1000 um, and within
   the Build Job request bounds where tighter. Range errors carry a unit hint (for example `speed looks like m/s`).
7. Ids: `^[A-Za-z0-9._-]{1,64}$`, not starting with `= + - @`. An id containing `SYNTHETIC-EXAMPLE`
   (case-insensitive), the marker of the template's example row (4.7), refuses with `SYNTHETIC_EXAMPLE_ROW` in inputs
   and in targets, so the example can never be frozen or scored as a real condition.
8. All rows of one `condition_id` must carry identical inputs; two condition ids with identical inputs refuse
   (merge them as tracks of one condition).
9. Text: UTF-8 (BOM stripped), `csv.reader(strict=True)`, at most 256 KiB, 2000 rows, and the condition cap (4.3).
   Bytes starting with the zip magic (`PK\x03\x04`, xlsx) or not valid UTF-8 refuse with save-as instructions.
10. Display file names (`inputsFileName`, `targetsFileName`): base name only, `^[A-Za-z0-9 ._()-]{1,120}$`, not
    starting with `= + - @` or a dot; anything else refuses with `FILE_NAME_INVALID`. They are never used as paths and
    are neutralised again in exports.

### 4.3 Caps

Inputs and targets files: 256 KiB each after base64 decode (base64 request field at most 350,000 characters; one RPC
line at most 1,000,000 characters). Rows: 2000. Conditions per freeze: provisional 48 (5 served calls each, 240
calls), derived in phase 0 from timing and set in phase 1 so that a freeze at the cap takes at most 60 s p95. P8 adds
no cost to the freeze job and protocol 1 sends no research request (7.6), so there is one served cap. A larger
campaign is split into blocks; each block needs at
least 12 conditions to be scored, which the preview says.

### 4.4 targets.csv (scoring phase whitelist)

1. Keys: exactly the frozen key set (`condition_id`, `track_id`, `section_id`, as used at freeze). Missing, extra or
   duplicate keys refuse the score submission.
2. `depth_status`: blank or `measured`, `track-not-formed`, `specimen-lost`, `section-unreadable`, `not-measured`.
   A measured row needs `depth_um > 0`; any other status needs a blank `depth_um`. `track-not-formed` must cover every
   section of its track (else `TARGET_STATUS_CONFLICT`).
   a. `track-not-formed` is an outcome, not a measurement loss, and is never excluded: the track counts, and its
      condition enters every scored arm with APE +inf (label `track not formed in <k> conditions: counted as model
      misses`). The model predicted a melt track where none formed; scoring it as a miss can only hurt the model
      (divergence D11, because MELT refuses a non-positive target instead).
   b. `specimen-lost`, `section-unreadable` and `not-measured` are measurement losses. They are excluded with their
      status, listed by key in every report (never with a value), and counted at three levels: sections, tracks (a
      track with no measured section) and conditions (a condition with no measured track), each as `k of n frozen`.
      More than 20 % of frozen tracks or more than 20 % of frozen conditions is a block issue (inconclusive). Changing a
      status after an attempt is a changed targets file and therefore `not-blind-rescored-changed-targets` (6.4).
   c. This exclusion policy is declared divergence D1 (7.7): MELT `reduce_conditions` (runner 1567 to 1572) refuses a
      missing or non-positive target and drops no row, and GOAL kill criterion 3 forbids excluding adverse rows.
      Protocol 1 accepts declared measurement losses because a user lab loses sections, with the safeguards above:
      per-row status, two-level 20 % caps, no exclusion of not-formed tracks, and the attempt rule.
3. `depth_um` (um), `width_um` (optional, descriptive, blank allowed), `depth_u_um` (required in every measured row
   when `depthUncertainty.basis` is `per-row`; constant within a condition, else refused with `U_PER_ROW_VARIES`, MELT
   rule). A `depth_status` word outside the vocabulary refuses with `TARGET_STATUS_UNKNOWN`; a missing key or `depth_um`
   column refuses with `TARGETS_COLUMN_MISSING`; `FILE_EMPTY` and `CSV_MALFORMED` apply as in inputs (Part P, R15). Range checks
   with unit hints (`TARGET_OUT_OF_RANGE`, a 422 at submit, no attempt created, ledger `score-refused` with the code
   only): `depth_um` 1 to 3000 um, `width_um` 5 to 3000 um, `depth_u_um` above 0 and below the row's `depth_um`. The
   hint is computed from the value but never prints it: below the range `values look like millimetres; enter
   micrometres`, above the range `values look like nanometres or a wrong column`. These checks run after the freeze,
   so they cannot shape a prediction.
4. Input columns (`power_W`, `speed_mm_s`, `spot_um` and aliases) may be repeated only unchanged; a difference refuses
   (`INPUT_REPEAT_MISMATCH`). This lets the user keep one measurement sheet as the targets file.
5. Unknown headers (for example `notes`, `cap_um`) are listed as ignored and never parsed.
6. Same dialect, encoding, size, id (including `SYNTHETIC_EXAMPLE_ROW`) and file-name rules as inputs. Targets
   aliases: `depth_um`: `depth`, `D_um`, `penetration_depth_um`, `Depth (um)`; `width_um`: `width`, `W_um`,
   `Width (um)`.

### 4.5 Documents

1. Preview (`lpbf-user-blind-preview-1`, estimate result, writes nothing): `previewSha256 = sha256(canonical
   {schema, metadataSha256, inputsSha256, columns, protocolSha256, predictorIdentity, bestReachable,
   acknowledgementsRequired, overlapSha256})` (acknowledgements themselves are not hashed, 4.1), alias mappings,
   dialect, counts (rows, conditions, tracks, sections), input-only exclusions with reasons, grades `{power, beam,
   block}`, block issues, labels, design checks `{nConditions, nMinMet, leverage {cut, nBelow, nAtOrAbove20, ok or
   "not evaluable"}, resolution {evaluable, reason}, uMNote}`, overlap `{earlierTests[], publishedSets[],
   calibrationStores[]}` (condition counts and store ids only), `bestReachable {status, reasons[]}`,
   `acknowledgementsRequired[]`, budget `{conditions, solverCalls, cap, estimate_s}`, divergences that apply,
   `parsedInputs` (the per-condition table of 3.4 item 8: parsed and converted inputs, units read, conversions; inputs
   only), honesty. Leverage is reported as bin counts only, never per-condition index values. No predicted depth.
2. Freeze record (`lpbf-user-blind-freeze-1`, on disk only): `freezeKey = sha256(canonical {protocolId, metadata,
   canonical input rows, predictorIdentity})` (createdAt excluded, so re-freezing identical inputs returns the same
   record); `createdAt` (local clock, stated as unverified); metadata; `metadataSha256`, `inputsSha256` (raw bytes),
   `previewSha256`; `columnsLoaded`; `targetColumnsRead: false`; rows `[{ordinal, condition, track, section, P_W,
   v_mm_s, d_declared_um, beamQuantity, beamDefinition, d_1e2_um, conversion, P_u_k1_W, indexUnrounded, indexBin}]`;
   per condition `pred {served, "served:P-5%", "served:P+5%", "served:d-5%", "served:d+5%", "research:melt-link",
   "research:cavity", "context:fabbro"}`, each `{value_um, status ok|failed|unavailable, reasonCode, reasonClass,
   extentStatus, warnings[]}`; in Part P both research arms are `{value_um: null, status "unavailable", reasonCode
   "RESEARCH_NOT_REQUESTED"}` for every condition (7.6; the research fields of a later protocol are Part S, 15.3);
   served values carry `sourceEvidenceKind: "Unresolved"` with the reason of 14.6 shown as text; acknowledgements; excluded inputs; design checks; grades; block issues; labels; predictor identity; scorer
   identity at freeze; `predictionsSha256`; honesty. Sidecar `freeze.json.sha256`.
3. Receipt (`lpbf-user-blind-receipt-1`, freeze job result): `freezeKey`, `freezeSha256`, `predictionsSha256`,
   `inputsSha256`, `metadataSha256`, `previewSha256`, `targetCommitmentSha256 or null`, `createdAt`, `alreadyFrozen`,
   counts, acknowledgements, excluded inputs, design checks, grades, block issues, labels, `armsFrozen [{id,
   available, reasonCode}]` (availability counts only, no value), predictor identity, scorer identity,
   `ledgerSeq`, `ledgerEntryHash`, `predictionsWithheld: true`, `anchorAdvice` ("share freezeSha256 with
   someone outside this computer, or commit it to a repository, before you measure or upload measurements; this app
   cannot prove the order of events by itself"), honesty. No predicted value anywhere.
4. Reveal record (`lpbf-user-blind-reveal-1`): `{revealedAt, scoreAttemptsBefore, via (reveal, bundle, cli),
   jobId or null}`, written exclusive before the freeze document becomes servable; its creation is the commit point and
   the `revealed` ledger event follows it (3.5).
5. Report (`lpbf-user-blind-report-1`, `score-<n>.json` plus sidecar, served through the artifact branch):
   `freezeKey`, `freezeSha256`, `targetsSha256`, `commitment {declared, matched}`, `attempt {n, earlierTargetsSha256[]}`,
   `blindness {status, reasons[], revealEvents[], overlap[], exposuresAfterCommitment[]}`, `predictor {atFreeze,
   atScore, changedSinceFreeze}`, `scorer {atFreeze, atScore, changedSinceFreeze}`, `divergences [{id, sentence}]`
   (the full declared list of 7.7, every report), `wordingSha256` (display only),
   `thresholds {median "0.20", p90 "0.35", meanSigned "0.10", maxApe "0.50", nMin 12, uMax "0.10", source "MELT
   pre-registration Amendment 6 values, reused as fixed protocol 1 constants; this result is not a G3o record",
   alloyNote}`, `grades`, `blockIssues`, `resolution` (runner `resolution_qualifier` output incl. `u_m_assumed` and the
   lead-assumption text), `leverage`, `arms {armId: {status, sentence, reason, coverage {k, n, unavailableByCode},
   stats {n, median, p75, p90, meanSigned, maxApe, nFailed, nNotFormed, thresholdsMet}, bootstrap95, marginal[],
   unavailableConditions[], bandCoverage?, consistencyCounts?}}`, `commonSubset {k, conditions[], stats per arm}`,
   `labels[]`, `fragile {input, inputFlips[], band?, property: "not evaluated"}`, `paired {p, nNonzero, improves}`
   (phase 6, common subset), `ledger [{condition, P_W, v_mm_s, d_1e2_um, indexBin, nTracks, trackDepths_um, D_obs_um,
   predUm per arm, rel per arm, widthObs_um, widthModel_um, band per research arm, consistencyNotes[]}]`, `excluded
   {inputs[], targets [{key, status}]}`, `exclusions {sections, tracks, conditions}` (each `k of n frozen`),
   `notFormed {tracks, conditions}`, honesty.
6. Comparison CSV (`blind_comparison_v1.csv`, Part P, R21), exported from a report only (it holds predictions, so it
   follows the reveal-or-score gate), written by Python from the report, never recomputed in TypeScript. Preamble lines,
   each starting `# `: the banner of 2.2, the honesty literals, the report title, `freezeKey`, `reportSha256`, the
   blindness status and its sentence, the status and sentence of every arm, the labels, the ids and sentences of the
   divergences that applied, and `rel is a fraction (pred - obs) / obs; positive means the model is deeper`. Then one
   header and one row per (condition, arm): `condition_id`, `P_W`, `v_mm_s`, `d_1e2_um`, `index_bin`, `n_tracks`,
   `D_obs_um`, `arm`, `arm_status`, `D_pred_um`, `rel_signed_fraction`, `ape_fraction`, `band_min_um`,
   `band_nominal_um`, `band_max_um` (blank for served arms, and blank for research arms while they are not requested),
   `consistency_status`, `source_evidence_kind`, `excluded_status`, `labels` (joined by ` | `). Units are in the column
   names; fractions, not percent; `+inf` is written as `inf` with `ape_fraction` and a `failed` status; text cells pass
   through `blindCsvTextCell` (3.4 item 4). A cross-language test pins the header.

### 4.6 Protocol record

`data/blind/lpbf-user-blind-protocol-v1.json`, generated by `python/tools/lpbf_user_blind.py export-protocol` and
checked with `--check`: protocol id, vocabularies, alias tables, regexes, caps, thresholds as exact decimal strings, arm
catalogue (protocol 1: research arms fixed at `RESEARCH_NOT_REQUESTED`; the P8 reason-code class table enters only
protocol 2, 15.3), the declared divergence list with ids and rules (7.7), the
blind request types (3.2.1), template columns and the path and sha256 of the served-closure pin (3.6). Its sha256 is
`protocolSha256`. A released protocol version is immutable; any rule, threshold or vocabulary change is a new id.
Label and status sentences live in `data/blind/lpbf-user-blind-wording-v1.json` (same generator, `--check` too),
whose sha256 `wordingSha256` is printed in reports for display and is in no identity. TypeScript imports both for
templates, header checks and display only.

### 4.7 Templates

`data/blind/templates/blind_inputs_v1.csv`, `blind_targets_v1.csv` (headers plus one row marked
`SYNTHETIC-EXAMPLE` in its ids) and `blind_metadata_v1.json`; the browser generates the same files with `toCsv`. A
cross-language test pins the TypeScript header lists to the protocol record. The example row is refused if it is
uploaded (`SYNTHETIC_EXAMPLE_ROW`, 4.2 item 7), and the browser header check warns about it before upload.

### 4.8 Mode A share documents (revision 3)

All closed, canonical JSON (14.4.2 rules).

1. `share-manifest.json` (`lpbf-user-blind-share-1`): `shareId` (sha256 of the canonical manifest without `shareId`),
   `freezeKey`, `freezeSha256`, `predictionsSha256`, `receiptLedgerEntryHash`, `files [{name, sha256, size, kind}]`
   (closed name set of 14.3.1), `consent {includeInputs: true, includeMetadata: true, includeTargets}`, `licence`
   (`CC-BY-4.0` | `CC0-1.0` | `none`), `publishAllowed`, `attribution` or null, `submitter` or null (14.7.1),
   `evidenceManifestSha256` or null, `anchors [{kind github | zenodo | other, url, note}]` as typed by the user,
   `createdAt` (local, unverified), `appIdentity {protocolSha256, wordingSha256, scorer identity}`, honesty (2.1, scope
   `shared-result`).
2. `ledger-excerpt.jsonl`: full lines for this freeze, redacted links `{seq, prevEntryHash, entryHash}` for the others
   (14.3.2).
3. Maintainer import record `shared-results/<shareId>/import.json` (`lpbf-shared-import-1`): `shareId`, the check
   results of 14.3.4 by id, `order` (`local-ledger-only` or `anchored <time>`), `importedAt`, the spent ledger entry
   draft, `tier` with its events (14.7.4).

### 4.9 Mode B sealed documents (revision 3)

All closed, canonical JSON (14.4.2 rules); the honesty block of 2.1 with scope `sealed-submission` in each.

1. `commitment.json` (`lpbf-sealed-commitment-1`): `commitmentId`, `sealedProtocolSha256`, `createdAt` (local,
   unverified), `metadata` (4.1, with `mode: "post-measurement"` and `targetCommitment: null`; the commitment carries the
   hash), `metadataSha256`, `inputs {fileName, csvBase64, sha256}`, `targets {sha256, sizeBytes, fileName, dialect}`,
   `evidenceManifest` (14.7.1) or null with `evidenceManifestSha256`, `submitter` (public fields only; private fields as
   sha256), `licence`, `publishAllowed`, `confidential: false`, `declarations {predictionsViewedBeforeCommitment: "no",
   targetsPublic: "no", dataPreviouslyPublished: "no", usedForMachineCalibration: false}`, `appIdentity {protocolSha256,
   wordingSha256}`, and in Rev. 4 `lossCount` (15.1 item 2c). No target value, no flag, no micrograph. Rev. 4: the
   `submitter` holds no email in any form (15.6 item 2).
2. `commitment-public.json` (`lpbf-sealed-commitment-public-1`, confidential variant, 14.4.5): `commitmentId`, the
   hashes, alloy, condition count, licence `none`, `confidential: true`, public identity fields.
3. `run-amendment.json`: exactly the closed key set of MELT Amendment 6 item 14.4 (`whitelist`, `served_commit`,
   `p1_commit`, `p3_verdict_commit`, `constants_amendment`, `candidate_arm`, `beam`, `powder_absorptance_or_p5_bias`,
   `datum_statement`, `track_section_protocol`, `grades`, `cavity_physics_statement`, `exposure_exclusions`,
   `data_hashes`), filled from the commitment metadata plus the maintainer's sourced sensitivity beams where the beam is
   nominal. [Rev. 4: see 15.2 item 2] `data_hashes` keeps the runner's shape: paths in the maintainer submissions working
   repository mapped to the sha256 values of the commitment (inputs, targets, evidence files); the id-keyed shape is
   withdrawn.
4. `predictions.json` (`lpbf-sealed-predictions-1`): `commitmentId`, `inputsSha256`, `targetsSha256`,
   `runAmendmentSha256`, `servedIdentity` (3.6 served part with the served-closure pin), `researchIdentity` (3.6 research
   member) or `{requested: false}`, `meltRunner {commit, amendment6TextSha256, amendment6JsonSha256,
   predictionFileSha256}`, `candidateArm`, per condition every MELT arm from the runner's prediction file and every app
   arm of 7.1 in the freeze record form of 4.5 item 2, `frozenAt` (maintainer clock), `predictionsContentSha256`.
   `predictions-public.json` holds the identities and `predictionsSha256` only.
5. `publication.json`: `predictionsSha256`, `url`, `serverTime`, `recordedBy`, `recordedAt`.
6. `release.json` (`lpbf-sealed-release-1`, user side): `commitmentId`, `predictionsSha256` as checked, `files [{name,
   sha256, size, role targets | inputs | metadata | commitment | predictions | evidence}]`, `licence`,
   `depositInstructions` (text), `localScoreSha256`.
7. `release-<n>.json` (maintainer): `source {kind zenodo | email, doi or null, publicationDate or receivedAt}`, file
   hashes, `accepted` or `refused {code}`.
8. `intake.json`: flags `[{code, keys, sentence}]`, evidence re-hash results, identity completeness, plausibility
   constants sha256.
9. `tier.json`: append-only events (14.7.4).
10. `result.json` (`lpbf-sealed-result-1`): the protocol 1 report fields of 4.5 item 5 that apply, plus `meltVerdict
    {verdictFileSha256, status, statistics, qualifiers, licenceSentence or null}`, `scorerAgreement` (14.4.6 item 2),
    `tierAtScore`, `g3oBlock {value, reasons}`, `blindness {status: "blind-sealed"}`, the anchors of 14.4.9 and
    `sealedDepartures` (SD1 to SD3). [Rev. 4: `g3oBlock` becomes `registration {objective, reasons, at}` (15.1 item 2d);
    SD2 and SD3 are withdrawn and SD1 lives in the G3s pre-registration; the caveat of 15.7 item 1 and
    `milestoneStatement` (null for a single block) are added.]
11. `data/benchmark/sealed-submissions-v1.json` (`lpbf-sealed-submissions-1`, main repository): the entries of 14.4.9,
    never per-condition values.
12. `data/benchmark/approved-reviewers-v1.json` (`lpbf-approved-reviewers-1`): `{reviewerId, approvedBy, approvedAt}`.

## 5. Blind protocol with server-enforced order

"Python" below is the worker (RPC process for validation, staging and write-free reads, a fresh child process per
queued job). Browser checks are convenience only. Request shapes are the closed payloads of 3.2.1.

1. Describe (browser). The user fills the metadata form, downloads templates and reads: "Inputs and measurements travel
   in separate files. The app does not receive your measurements until it has frozen its predictions."
2. Pick inputs (browser). `file.slice(0, 65536)` header line only; target-like or unknown headers and the template's
   example row are flagged before the rest is read; then `arrayBuffer()` with the 256 KiB cap and base64. In
   post-measurement mode the user may pick the targets file too. Before hashing, the browser runs the header-only checks
   of the targets file with the TypeScript helpers and the protocol record's header lists (separator sniff, key and
   `depth_um` columns present, aliases, the example-row marker in the first data rows) and counts its data lines, so a
   file that will fail at score is caught before it is committed (Part P, R20); Python still runs every check at score.
   The browser then computes the sha256 with SubtleCrypto over the raw bytes (same value as `sha256sum` or `certutil`)
   and puts only the hash in `targetCommitment`; the file never leaves the browser at this step. The step shows
   `Do not open and save this file again before you upload it for scoring: saving it, even unchanged, in a spreadsheet
   program usually changes its bytes, and the hash will no longer match.` Without a secure context the user pastes the hash instead (3.4 item 5). A
   third-party custodian can supply the hash instead.
3. Preview: `POST /api/lpbf/estimate {jobType: "user-blind-preview", schema, metadata, inputsCsvBase64,
   inputsFileName}`. Python validates closed keys, metadata, header whitelist (before rows), structure and caps;
   computes grades, block issues, labels, design checks, index-bin counts, overlap with tests on this computer that were
   revealed or scored and with the calibration stores (6.4 item 7, from phase 4), the best reachable status and the
   required acknowledgements and the parsed inputs table; returns `previewSha256` (4.5 item 1). Writes nothing, calls
   no thermal solver.
4. Review (browser). Shown before anything is frozen: `Best reachable outcome: inconclusive (atmosphere not stated;
   single-track conditions need at least 3 replicated conditions)`, each block issue with how to fix it, the labels,
   the declared divergences that apply, the overlap list (the user may drop overlapping conditions now; deciding from
   inputs before freeze is legitimate), the parsed inputs screen (3.4 item 8), and the acknowledgement boxes. The
   research arm is not offered (7.6); the review states `Research arm: not requested in this version`.
5. Freeze submit: `POST /api/lpbf/jobs {jobType: "user-blind-freeze", schema, metadata, inputsCsvBase64,
   inputsFileName, previewSha256, overlapSha256, acknowledgements}`. `acknowledgements` is a top-level request field, outside
   `metadata`, `metadataSha256` and `previewSha256` (4.1). Python (submit) re-runs the preview; first compares the live
   overlap with the reviewed `overlapSha256` (`OVERLAP_CHANGED`) and the live required acknowledgements with the ticked
   ones (`ACK_REQUIRED`), so the message says what changed; then refuses any other drift with `PREVIEW_DRIFT`; stages the
   canonical metadata and raw inputs bytes by hash; enqueues a job whose `input.json` holds hashes only.
6. Freeze (child). Silent child (3.2 item 3). Verify uploads by hash; re-run the preview; check the live fingerprint
   and the served-closure pin (3.6); for every condition compute the served arm and four sensitivity arms, and record
   both research arms as `RESEARCH_NOT_REQUESTED` (7.6); `assert_no_target_loaded`; assert that
   `lpbf_user_blind_targets` and `lpbf_user_blind_score` are absent from `sys.modules` (Part P, ENG-17); record
   `columnsLoaded` and `targetColumnsRead: false`; compute `freezeKey`. Write `freeze.json` and its sidecar into
   `.staging/<random>/` and fsync; take the store lock and reconcile (3.5); if `freezes/<freezeKey>` now exists, verify
   its sidecar, leave the staging directory as incomplete and return the receipt with `alreadyFrozen: true` (the
   existence check runs under the lock, Part P, R17); re-derive the required acknowledgements and the overlap against
   the store as it is now and fail with `OVERLAP_CHANGED` (against the `overlapSha256` kept in `input.json`) or
   `ACK_REQUIRED` (against the kept acknowledgements) if they differ (nothing committed, staging left as incomplete); rename into place (the commit point); append ledger `frozen` (with `jobId`) and the condition
   tuples to `index/conditions.jsonl`; release. The job result is the receipt.
7. Receipt (browser). Shown, stored (summary only) and downloadable as JSON. The UI asks the user to anchor
   `freezeSha256` outside this computer if they need provable order.
8. Optional reveal: `{jobType: "user-blind-reveal", schema, freezeKey, confirmation: "reveal predictions and end blind
   status"}` (exact phrase, typed in a `role="dialog"` confirmation). Python writes `reveal-<n>.json` exclusive (the
   commit point) and then appends ledger `revealed`, before the artifact branch will serve `blind-freeze.json`. A
   bundle request with `revealConfirmation` and the CLI `show` or `bundle` with `--reveal` take the same path first.
   Every later report on this freeze, and on any later test with overlapping conditions, is not blind unless the
   commitment exception of 6.4 applies.
9. Measure (user's lab). Prospective when the mode is pre-measurement.
10. Score submit: `POST /api/lpbf/jobs {jobType: "user-blind-score", schema, freezeKey, targetsCsvBase64,
    targetsFileName, declarations {viewedPredictionsBeforeFinalisingTargets: no|yes|unsure},
    acceptCommitmentMismatch: false}`. Python (submit) checks the freeze key format and that the freeze exists with a
    valid sidecar, parses the targets header and rows, checks the exact key set, statuses, positivity, ranges with
    unit hints (`TARGET_OUT_OF_RANGE`), the example row, repeated inputs and the commitment. Any refusal is a 422 with
    row numbers and column names (never values), raised as `BlindRefusal` (3.2 item 10); any other exception becomes
    `BLIND_SUBMIT_INTERNAL` with its fixed message, never the exception text (Part P, R15); ledger `score-refused` with
    the code and the targets sha256; no attempt is created, so fixing a malformed file burns nothing. A commitment mismatch refuses (`COMMITMENT_MISMATCH`) unless
    `acceptCommitmentMismatch` is true, in which case the score proceeds and the report says `commitment declared
    before freeze was not matched` (status falls back from `blind-committed` to `blind-retrospective-declared`, never
    better). Then stage the raw targets bytes and enqueue.
11. Score (child). Silent child. Load `freeze.json`, verify the sidecar and recompute `freezeKey` from content; refuse
    on mismatch (`FREEZE_ALTERED`). Read the live predictor and scorer identities (never recompute predictions; refuse
    on `PROTOCOL_CHANGED`). Join targets; apply 4.4 item 2 (not-formed tracks counted as misses, measurement losses
    excluded and counted at three levels); reduce sections to tracks to conditions (`reduce_conditions`, sections never
    replicates). Statistics, coverage, common subset, qualifiers, labels and status per arm (section 7); blindness
    (6.4). Then, under the store lock (Part P, R17): an earlier score with the same `targetsSha256` is returned as is
    (idempotent, no new attempt); otherwise attempt `n = max + 1` is computed there, the record and its sidecar are
    committed as the directory `score-<n>/` (3.5 item 2), then ledger `scored`. The job result declares `blind-report.json`.
12. Report (browser). Fetch through the artifact route, check sha256 (or show the secure-context note), validate with
    `checkedBlindReport`, render.
13. Later visits (browser). `user-blind-list` and `user-blind-get` on the estimate RPC load the tests and their
    documents without queueing; a document whose writing job folder is gone is fetched through `user-blind-open`.

Server-enforced (protocol 1; the Part S flows of section 14 have their own rules): closed schemas and header whitelists
in both phases; targets absent from the server until a freeze exists; the freeze process cannot import the targets parser (AST test) and never opens a targets path (open audit test);
no predicted value in any preview, receipt, list, get or job result, nor in `progress.log`, the sqlite `log` and `error`
columns or `GET /api/lpbf/jobs/:id` (silent child, log filter, sentinel test); the frozen document and every bundle are
not servable or writable before a reveal or a score, through the worker or the CLI; frozen values never recomputed;
exclusive-create records with sidecars and crash-safe commit points; attempt, reveal and overlap history in every
report; label fields both Python and TypeScript refuse to change.

Not enforceable, and said in the UI and the guide: order is recorded on a local clock; the served predictor is public
and deterministic, so viewing predictions elsewhere in the app (every surface listed in the
`predictionsViewedBeforeFreeze` help, 4.1) is declared, not prevented (phase 4 adds a partial Build Job history check
and the calibration-store overlap check); a person with disk access can rewrite or delete the store and sidecars
together, which is detectable only against an externally anchored hash; on a shared host every signed-in user can read
every test (9.7). The withholding is a gate on what the app serves, not on what the disk holds: `freeze.json` and the
uploads are plain files under the store root, readable by anyone with disk access before any reveal (Part P,
PI-12b).

### 5.1 Mode A flow (revision 3, design in 14.3)

1. The user opens a scored test, chooses `Share my result`, reads the file list, ticks the consent per part, chooses a
   licence and, for CC BY 4.0, an attribution; optionally lists evidence files and identity (14.7.1).
2. `user-blind-share` writes the tar; the browser downloads it through the artifact route with the sha256 check.
3. The user deposits it on Zenodo or emails it, following the instruction sheet; the app sends nothing.
4. The maintainer runs `share-verify`, then `share-import`; the set becomes `EXPOSED` (14.3.5); a tier review is
   optional and descriptive only.

### 5.2 Mode B flow (revision 3, design and state machine in 14.4)

1. The user, post-measurement, picks the inputs and targets files and optional evidence files; `user-sealed-precheck`
   checks both files and shows the user's own plausibility flags; the user fixes any structural problem now, because
   the committed targets bytes can never change.
2. The user fills identity and licence, confirms the four declarations, and `user-sealed-commit` writes
   `commitment.json` (no target value, flag or micrograph inside).
3. The user opens a pull request or issue in the submissions repository with the commitment, following the sheet.
4. The maintainer runs `import`, `anchor`, `run-amendment`, `freeze` (served arms, the MELT runner's prediction file,
   research subsets from an explicit batch), then publishes `predictions.json` by a merge and records it with `publish`.
5. The user downloads the published predictions file; `user-sealed-check-predictions` confirms it names the committed
   inputs; `user-sealed-release` checks the targets hash, writes `release.json` and the local score.
6. The user publishes the release folder on Zenodo (or emails it); the maintainer runs `receive-targets`, `intake`,
   `tier`, `score` once, and `record`; the result enters `sealed-submissions-v1.json` and the leaderboard (14.4.9).

## 6. Metadata gates and refusal messages

### 6.1 Refusals (no job, 422 validation envelope with `code` and `message`; messages cite rows and columns, never values)

| Code | Message |
|---|---|
| `INPUTS_TARGET_COLUMN` | `Column '<name>' may be a measurement (it contains '<token>'). The inputs file carries inputs only; put measurements in the targets file, or remove the column if it is not a measurement.` |
| `INPUTS_COLUMN_MISSING`, `TARGETS_COLUMN_MISSING` (Part P, R15) | `Column <canonical name> is required (or one of its aliases: <list>).` |
| `FILE_EMPTY` | `The file has a header but no data rows.` |
| `CSV_MALFORMED` | `Row <n>: the line could not be read as CSV (<unterminated quote or field count differs from the header>).` |
| `HEADER_UNIT_UNKNOWN` (Part P, R20) | `Column '<name>' states the unit '<unit>', which this form does not convert. Use <accepted units>.` |
| `TARGET_STATUS_UNKNOWN` | `Row <n>: depth_status must be blank or one of measured, track-not-formed, specimen-lost, section-unreadable, not-measured.` |
| `U_PER_ROW_VARIES` | `Condition <id>: depth_u_um differs between rows; give one uncertainty per condition.` |
| `BLIND_SUBMIT_INTERNAL` | `The request could not be processed. Nothing was stored. Check the file against the template and try again.` |
| `STORE_LOCK_DOMAIN` (Part P, R17) | `This store is used by the <domain> worker. Run the CLI in the same environment as the worker.` |
| `INPUTS_UNKNOWN_COLUMN` | `Column '<name>' is not an input column. Allowed: condition_id, track_id, section_id, power_W, speed_mm_s, spot_um, power_u_k1_W, or a listed alias.` |
| `AMBIGUOUS_ALIAS` | `Columns '<a>' and '<b>' both mean <canonical>. Keep one.` |
| `FILE_NOT_CSV_UTF8` | `This file is not UTF-8 CSV text (it may be an Excel workbook). In Excel use Save As, CSV UTF-8.` |
| `DIALECT_MISMATCH` | `Row <n>, column <col>: decimal comma found, but the declared format is comma separated with decimal points. Choose "semicolon separated, decimal comma" or re-export.`; at header level (Part P, R20): `The header is separated by semicolons, but the declared format is comma separated. Choose a semicolon format.` (and the reverse) |
| `NUMBER_INVALID` | `Row <n>, column <col>: not a plain positive number (no units, no thousands separators).` |
| `OUT_OF_RANGE` | `Row <n>, column <col>: outside <lo> to <hi> <unit>. <hint>` |
| `ID_INVALID` | `Row <n>: <col> must be 1 to 64 letters, digits, dots, underscores or hyphens, not starting with = + - @.` |
| `SYNTHETIC_EXAMPLE_ROW` | `Row <n> is the template's synthetic example. Delete it before uploading your own data.` |
| `FILE_NAME_INVALID` | `The file name may use letters, digits, spaces, dots, underscores, hyphens and brackets (1 to 120 characters), not starting with = + - @ or a dot. Rename the file and pick it again.` |
| `DUPLICATE_KEY` | `Rows <a> and <b> have the same condition, track and section.` |
| `CONDITION_INCONSISTENT` | `Condition <id>: rows differ in power, speed or spot. One condition is one setting.` |
| `CONDITION_DUPLICATE_SETTING` | `Conditions <a> and <b> have identical power, speed and spot. Merge them as tracks of one condition.` |
| `SECTION_WITHOUT_TRACK` | `Row <n>: section_id needs track_id.` |
| `REPEATED_ROWS_NO_TRACK` | `Condition <id> has several rows and no track_id. Add track_id, or declare that each row is a separate track.` |
| `REPLICATION_MISMATCH` | `You declared <k> tracks per condition and <m> sections per track; the file differs for conditions <list>.` |
| `SIZE_CAP` | `The file exceeds <cap>. Split the campaign into blocks; each block needs at least 12 conditions to be scored.` |
| `ALLOY_NOT_SERVED` | `<alloy> has no served melt-pool model in this app.` |
| `WAVELENGTH_OUT_OF_SCOPE` | `The served model is an infrared flat-plate model (1030 to 1100 nm); <x> nm is outside it.` |
| `BEAM_MISSING` | `No beam diameter: give spot_um per row or one block beam diameter.` |
| `PREHEAT_MISSING` | `The plate temperature before the first track is required to compute predictions.` |
| `METADATA_FIELD` | `Unknown metadata field '<k>'.`, `Missing required field '<k>'.`, `Field '<k>' has a value this form does not accept (<rule>).` (for example the block label rule) or `Published data cannot be a pre-measurement test; choose post-measurement.` |
| `ACK_REQUIRED` | `This design can at best end <status> (<reason>). Tick the acknowledgement to freeze anyway.` (checked at submit and again in the freeze child) |
| `OVERLAP_CHANGED` | `Since your check, <k> conditions newly overlap a test or calibration data on this computer. Run the check again.` (submit and child) |
| `PREVIEW_DRIFT` | `The request differs from the check you reviewed, or the predictor changed. Run the check again.` |
| `PREDICTOR_NOT_PINNED` | `The running solver does not match the reviewed served model (<fingerprint or file list>), so predictions cannot be frozen from an unreviewed build. Restore the listed files or install a reviewed release; a developer changes the pin only in a reviewed commit.` (remedy, Part P, U11) |
| `PROTOCOL_CHANGED` | `The protocol rules changed since this test was frozen under the same protocol id. This test cannot be scored by this build.` |
| `RESEARCH_CONTRACT_BROKEN` (Part S only; cannot occur in protocol 1, 7.6) | `The research results do not match the pinned P8 research contract (<check>). Nothing was frozen. Freeze without the research arm, or update to a release whose research pin matches.` (check ids of 15.3) |
| `STORE_READ_ONLY`, `STORE_FULL`, `STORE_LOCKED`, `STORE_SHARED_HOST` | `This installation is read-only.` / `The blind test store is full; see the guide for manual archiving.` / `Another blind job holds the store (job <id>). Try again when it finishes.` / `This server is reachable by other users, so blind tests are switched off. An operator can declare a single-user install (see the guide).` |
| `FREEZE_UNKNOWN` | `No frozen test with this key on this computer.` |
| `TARGETS_KEYS_MISMATCH` | `The targets file must list exactly the frozen rows: <m> missing, <e> extra, <d> duplicate (first: <key>).` |
| `TARGET_DEPTH_INVALID` | `Row <n>: a measured row needs a positive depth_um; for a lost or unreadable section set depth_status and leave depth_um blank.` |
| `TARGET_STATUS_CONFLICT` | `Row <n>: depth_status <s> needs an empty depth_um.` |
| `INPUT_REPEAT_MISMATCH` | `Row <n>: <col> differs from the frozen input. The targets file may repeat inputs only unchanged.` |
| `U_PER_ROW_MISSING` | `Row <n>: depth_u_um is required because the uncertainty basis is per row.` |
| `COMMITMENT_MISMATCH` | `This targets file does not match the hash you committed before the freeze. Upload the committed file, or continue; the result is then marked "commitment not matched".` |
| `FREEZE_ALTERED` | `The freeze record or its hash file changed after it was written. Not scored.` |
| `CONFIRMATION_PHRASE` | `Type the phrase exactly to reveal the predictions.` |
| `REVEAL_REQUIRED` | `This shows or exports the frozen predictions, which ends blind status. Reveal them first, or confirm the reveal phrase with this request.` (bundle job, CLI `show` and `bundle`) |
| `TARGET_OUT_OF_RANGE` | `Row <n>, column <col>: outside <lo> to <hi> um. <hint>` (hint `values look like millimetres; enter micrometres` or `values look like nanometres or a wrong column`) |
| `RESEARCH_RELAY_INCOMPLETE` (Part S only) | `The research step did not finish for every condition. Run it again, or freeze without the research arm.` |
| `SHARE_NO_SCORE` | `Share a test after it has been scored.` |
| `SHARE_ATTRIBUTION_REQUIRED` | `CC BY 4.0 needs a name or pseudonym for attribution.` |
| `SHARE_VERIFY_FAILED` (maintainer CLI) | `Check <id> failed: <check sentence>. Nothing was imported.` |
| `SEALED_PREDICTIONS_VIEWED` | `A sealed submission needs data whose predictions you have not viewed.` (Rev. 4, R9: no suggestion to run a local test) |
| `SEALED_LOCAL_TEST_OVERLAP` (Rev. 4, R9) | `<k> conditions match a test or a Build Job on this computer that showed predictions. A sealed submission needs conditions whose predictions you have not seen.` |
| `SHARED_INDEX_MISSING` (Rev. 4, R7; maintainer CLI) | `The maintainer index of seen data is missing or does not verify. Nothing was imported.` |
| `SEALED_DATA_PUBLISHED` | `Published data cannot be a sealed submission.` |
| `SEALED_CALIBRATION_OVERLAP` | `These conditions were used for machine calibration on this computer (<store id>), so they cannot be a sealed submission.` |
| `SUBMISSION_SCHEMA`, `SUBMISSION_ID_MISMATCH`, `SUBMISSION_PROTOCOL_UNKNOWN`, `SUBMISSION_INPUTS_CHANGED`, `SUBMISSION_DATA_EXPOSED`, `SUBMISSION_STATE` (maintainer CLI) | one sentence each naming the field, hash or state, never a value (14.4.4) |
| `TARGETS_HASH_MISMATCH` | `This targets file does not match the hash in your commitment. Only the committed file can be scored.` |
| `TARGETS_RELEASED_EARLY` (maintainer CLI) | `The targets were released before the predictions were published, so this is not a sealed test.` |
| `PREDICTIONS_FILE_NOT_CHECKED` (renamed from `PREDICTIONS_NOT_PUBLISHED`, Rev. 4, R6), `PREDICTIONS_INPUTS_MISMATCH`, `PREDICTIONS_ALTERED`, `PREDICTIONS_DUPLICATE` | `No predictions file has been checked for this commitment on this computer. Check the published predictions file first.` / `This predictions file is for other inputs. Do not release your targets; contact the maintainer.` / `The published predictions differ from the frozen file.` / `This commitment already has a predictions file.` |
| `EVIDENCE_HASH_MISMATCH` | `<k> evidence files do not match the committed hashes; they cannot support a tier above Declared.` (listed, not a refusal of the score) |
| `TIER_REVIEWER_NOT_APPROVED`, `TIER_REQUIREMENT_MISSING` (maintainer CLI) | `<id> is not an approved reviewer.` / `Tier <t> needs: <list>.` |
| `SEALED_SCORER_DISAGREEMENT` (maintainer CLI) | `The app's recomputation differs from the MELT runner for <arm>. The result is not recorded.` |

A child job ends with one code from the closed `BLIND_CHILD_ERROR_CODES` table: the codes above that can arise after
submit (`PREVIEW_DRIFT`, `ACK_REQUIRED`, `OVERLAP_CHANGED`, `PREDICTOR_NOT_PINNED`, `PROTOCOL_CHANGED`,
`FREEZE_ALTERED`, `REVEAL_REQUIRED`, `STORE_*` including `STORE_LOCK_DOMAIN`) plus `SOLVER_EXCEPTION` and
`INTERNAL_ERROR`; Part S adds `RESEARCH_CONTRACT_BROKEN`, `RESEARCH_RELAY_INCOMPLETE`, `SHARE_NO_SCORE` and the sealed
codes. The submit side has its own closed table `BLIND_SUBMIT_ERROR_CODES` (3.2 item 2) and the refusal table
`BLIND_REFUSAL_CODES` (3.2 item 10). The job's `error` text is the code's fixed message, never an exception message (3.2 item 3).

### 6.2 Block issues (scored arms become `inconclusive`; statistics still shown)

From MELT `block_level_issues` (runner 1242 to 1275): datum not `original-surface`; reduction `maximum-only` or
`single-selected-section`; sections released without a track key; plate thickness not released; atmosphere or surface
preparation unstated; independence not established (publication status `unknown`, the MELT item "independence from
spent data not established"). These and GOAL kill criterion 1 (no scored verdict when datum, observable or
independence is unresolved) are the base.

Additions, each a declared divergence (7.7): boundary not an etched fusion boundary (D2); cross-section location near
track ends or unstated (D3); beam profile `top-hat` or `ring` (D4); post-freeze measurement losses above 20 % of frozen
tracks or of frozen conditions (D1). A beam profile of `unknown` is not an issue: it is the label `beam profile not
stated (Gaussian assumed by the served model)`, because the default would otherwise make almost every user test
inconclusive.

Not block issues: MELT's "initial temperature not released" is a refusal here (`PREHEAT_MISSING`, predictions need
T0), with `nominal-ambient` labelled (D5). Leverage not evaluable (IN625, 7.4) is the step 5 leverage qualifier of 7.3,
as in MELT `block_verdict` (runner 1653 to 1679), so a block that fails a threshold is still reported as
`threshold-not-met` (GOAL kill criterion 3: a failed registered block is reported).

Decision recorded (not a question): power basis unstated and beam definition unstated follow MELT `power_grade` and
`beam_grade` (grade C, beam read as 1/e2, labelled), as Amendment 6 resolved for G3o, rather than refusing. The grade
is printed on every result.

### 6.3 Predetermined statuses (preview, from inputs and metadata only, acknowledgement required)

`inconclusive at best` (fewer than 12 conditions; any block issue; single-track conditions with fewer than 3 replicated
conditions or pooled df below 3; leverage counts below 4 on either side; IN625 leverage not evaluable, where
`threshold-not-met` stays reachable and the preview says so), `descriptive only` (powder layer; vapour-depression
quantity), `not blind` (exposure, 6.4, including calibration overlap from phase 4). The preview also states the
arithmetic of the resolution rule without data: with u_m not released, a condition needs a measured depth of at least
100 um on bare plate (200 um on powder or an AM block) for U_c at most 0.10 even with no track scatter. For a research
arm the preview states only the number of research requests and the estimated research time; scope (alloy chain
admitted, numerical Peclet range 0.01 to 10) is read from the responses and reported after the freeze, because the
worker imports no research code (7.6).

### 6.4 Blindness rule (Python, at score)

Exposure statuses:

1. `not-blind-predictions-viewed`: `predictionsViewedBeforeFreeze` or `viewedPredictionsBeforeFinalisingTargets` is
   `yes` or `unsure`.
2. `not-blind-predictions-revealed`: a reveal record for this freeze precedes the score.
3. `not-blind-earlier-test-overlap`: a condition tuple matches (same alloy; power, speed and 1/e2 beam each within
   1 %) a condition of another test on this computer that was revealed or scored before this score.
4. `not-blind-rescored-changed-targets`: attempt n > 1 with a targets hash that differs from attempt 1.
5. `not-blind-data-already-used-by-app`: `publishedDoi` matches a SPENT or EXPOSED ledger entry, or (phase 4) a
   condition tuple matches a condition of a published set in the spent ledger loaders.
6. `not-blind-app-history` (phase 4): Build Job history on this workstation holds a completed job with the same alloy
   and power, speed and beam within 1 % before the freeze; reported as "partial check, Build Job history only".
7. `not-blind-used-for-calibration`: `usedForMachineCalibration` is true, or (phase 4 at the latest, before any push) a
   condition tuple matches, at the 1 % rule, a row of `.runtime/user-calibration/<id>/rows.json` (written by
   `lpbf_user_measurements`, `python/lpbf_user_measurements.py:1-16`) or a fit row of
   `.runtime/machine-calibration/<id>/machine-calibration.json` (read by `lpbf_machine_calibrated_meltpool`,
   `python/lpbf_machine_calibrated_meltpool.py:6`). Those stores hold the user's measurements already compared with or
   fitted against the served model on this workstation. The check resolves both roots the way those modules do, reads
   alloy, power, speed and spot only, drops every measured field at parse (a sentinel test proves no width or depth
   value reaches any output), never writes, and records the import time from the store's own provenance as the
   exposure time. A user who declares `false` while a tuple matches gets the status anyway, with the reason `tuple
   overlap with calibration store <id>`.

Commitment exception, applied the same way to items 2, 3 and 7: a matched commitment fixes the targets by hash no later
than this test's `frozen` ledger event. An exposure recorded after that event (this test's own reveal, another test's
reveal or score, a calibration import) cannot have shaped the targets, so it does not make the test not blind; the
status stays `blind-committed` and the report lists it under `exposuresAfterCommitment`. Exposures before the `frozen`
event, every exposure of a test without a matched commitment, and items 1, 4, 5 and 6 always apply in full. (Earlier
drafts exempted only item 3; the reasoning holds equally for item 2, because the own reveal also follows the freeze and
so the commitment.)

Published data that the app has not seen:

8. `dataPreviouslyPublished` `yes` with a DOI that is not in the spent ledger, or with `publishedDoi` null, sets no
   `not-blind-*` status, because nothing shows that this app used the data. The best status is
   `blind-retrospective-declared` (a published set was measured, and public, before the freeze, so neither
   `blind-committed` nor `blind-prospective-declared` can apply), with the label `published data, not in this app's
   spent ledger (DOI <doi>)` or `(DOI not given)`. `yes` with `mode: pre-measurement` refuses at preview
   (`METADATA_FIELD`).

Otherwise blind: `blind-committed` (post-measurement, commitment matched), `blind-prospective-declared`
(pre-measurement mode), `blind-retrospective-declared` (post-measurement without a matched commitment, or item 8).

Any `not-blind-*` status makes every scored arm `descriptive-exposed`.

Revision 3. (a) `blind-sealed` is the status of a Mode B block (14.4.6 item 3): the targets were committed in public
before predictions were published by a party who never held them, the commit-time declarations hold (items 1, 5 and 7
apply through them) and the release came after the publication. It ranks above `blind-committed` and exists only in
the sealed scope. (b) Item 5 covers Mode A sets: on the maintainer's machine a test or submission whose hashes or
condition tuples match a `shared-result` entry or the local seen-tuples index is `not-blind-data-already-used-by-app`
(or refused at sealed import, `SUBMISSION_DATA_EXPOSED`). (c) A sealed block released early is
`not-blind-targets-released-early` if it is scored at all, always descriptive.

### 6.5 Plausibility flags (revision 3, Part S; never refusals)

The checks of 14.7.2 produce flags, not codes of 6.1: they never refuse a file, block a step or change a statistic.
They are shown to the user at precheck and before a share, recorded at maintainer intake, printed in sealed and shared
records with their codes and keys, and decide only whether a tier above Declared can be granted (14.7.3).

## 7. Scoring

### 7.1 Arms

| Arm | Source | Scored |
|---|---|---|
| `served` | Build Job thermal call (`lpbf_served_arms.served_arm`); IN625 direct thermal path, labelled | yes |
| `served:P-5%`, `served:P+5%`, `served:d-5%`, `served:d+5%` | same call with perturbed power or 1/e2 beam (no served call evaluates research, 7.6) | only for the input-fragile label |
| `research:melt-link` | Part P: `unavailable`, `RESEARCH_NOT_REQUESTED` for every condition (7.6). Later protocol (Part S, 15.3): `p8-research-v3` `meltDepthLink.fields.linkedMeltDepth_um` from the opt-in research route, with its `band` and the module `consistencyNote` (conditional and conduction depths, `controllingLeg` and `conductionMeltState` carried as context); alloys outside the admitted chains give `ALLOY_CONSTANT_CHAIN_NOT_ADMITTED`, read from the response | yes, side by side, never changes served labels |
| `research:cavity` | Part P: `unavailable`, `RESEARCH_NOT_REQUESTED`. Later protocol: `p8-research-v3` `keyholeCavity.fields.cavityDepth_um` with its band and onset support | only against `vapour-depression-depth`, descriptive in protocol 1; otherwise shown with `OBSERVABLE_MISMATCH` (goal deviation G1, 7.7) |
| `context:fabbro` | served `keyholeModel.fabbroDepth_um` | never |

A failed prediction (served `extentStatus` not `computed`, a served exception, a research code of class `failed`)
counts as APE +inf and is never dropped. A condition with a not-formed track counts as APE +inf for every arm (4.4
item 2a). In protocol 1 both research arms are `unavailable` with `RESEARCH_NOT_REQUESTED` (7.6). The coverage and
common-subset rules that keep an unavailable research value from flattering the research arm belong to protocol 2
(15.3).

### 7.2 Statistics (extracted functions, unchanged)

Per arm on condition means: `rel_c = (D_pred - D_obs) / D_obs`; median APE, P90 APE with the +inf rule
(`rank_quantile_exact`), mean signed over finite rows, max APE (+inf on any failure), n >= 12 counted inside the arm's
scope (conditions with a value or a failure); thresholds compared as exact Fractions of the strings `0.20`, `0.35`,
`0.10`, `0.50`. Cluster bootstrap over conditions (B 2000, seed 20261011) gives `bootstrap95` and `marginal: <stat>`
labels when an interval crosses a threshold. Served index bins (`served_bins`) are reported for every arm.

### 7.3 Status precedence (runner `block_verdict`, extended)

1. `descriptive-exposed` (any `not-blind-*`)
2. `descriptive-not-scored` (powder layer; vapour quantity; research cavity against melt depth; a sealed block at tier
   Declared, 14.4.6 item 4)
3. `inconclusive` (n < 12 counted inside the arm's scope, any block issue)
4. `threshold-not-met` (any of the four)
5. `inconclusive` (leverage not met or not evaluable, the latter for IN625; resolution `not_met` or `not_evaluable`)
6. `thresholds-met`

`unavailable` applies to a research arm with no in-scope condition; in protocol 1 always, with `RESEARCH_NOT_REQUESTED`
(7.6); in protocol 2 also for `P8_NOT_IN_THIS_BUILD`, schema unknown or malformed, alloy chain not admitted, or every
condition outside the numerical scope (15.3). Each status maps to one plain sentence (2.2) plus the label
list.

### 7.4 Grade, resolution and leverage

1. Grades from metadata facts through `power_grade`, `beam_grade`, `block_grade`; shown as `Input metrology grade:
   <block> (power <p>, beam <b>)` with the facts that set them.
2. Resolution: `resolution_qualifier` (median U_c <= 0.10, k = 2), u_m released or the default `max(f, 0.03 D)` with
   f 5 um bare plate and 10 um powder layer or AM block, label `u_m assumed (lead assumption, not sourced)`; cv_pool for
   single-track conditions; 2 x u_m reported descriptively.
3. Leverage: `leverage_qualifier` on the unrounded served index of the inputs: at least 4 conditions below the low cut
   and at least 4 at or above 20. Low cuts: Ti-6Al-4V 15 and AlSi10Mg 15 (MELT); 316L 15 and IN718 15 proposed from the
   served regime parameters (divergence D6); IN625 undefined until Astra decides (the served IN625 rule is two-class at
   13.6), so an IN625 block carries `leverage not evaluable` as the step 5 qualifier of 7.3: a threshold failure is
   still reported as `threshold-not-met`, and only an all-thresholds-met IN625 block becomes `inconclusive`. Astra
   signs off in phase 0.
4. Alloy note: thresholds were registered for Ti-6Al-4V and AlSi10Mg; for 316L, IN718 and IN625 the report says
   `thresholds reused unchanged; registered for Ti-6Al-4V and AlSi10Mg` (divergence D6, see Q4).

### 7.5 Labels

`u_m assumed`; `input-fragile` (served nominal meets all four thresholds and any of the four perturbed arms does not,
runner flip logic); `property sensitivity not evaluated`; `marginal: <stat>`; `beam definition unstated (read as 1/e2)`;
`beam size declared as radius (doubled)`; `beam profile not stated (Gaussian assumed by the served model)`; `declared
power uncertainty exceeds the 5 % fragility band`; `S and O flagged missing`; `predictor changed since freeze`;
`scoring code changed since freeze`; `thresholds reused for <alloy>`; `served direct thermal path (IN625,
legacy-estimated properties)`; `leverage not evaluable (IN625)`; `conditions match published set <id>` (phase 4);
`published data, not in this app's spent ledger`; `commitment not matched`; `track not formed in <k> conditions:
counted as model misses`; `measurement losses: <s> sections, <t> tracks, <c> conditions excluded`; `plate state
differs from the as-built property convention`; `research arm scored on <k> of <n> conditions (<codes>)`; `research
consistency: inRange <a>, extrapolated <b>, outOfRange <c>`; `band-fragile`; `bare plate: layer argument 40 um passed
(no effect on served depth)` shown only if the phase 0 Astra check confirms invariance, otherwise the layer used is
printed as a predictor note in the collapsed predictor section. Part P adds: `research arm not requested`; `unit not
stated, read as <unit>`; per value the source label (14.6, R19): `Measured (user-supplied)` on user values, never a
bare `Measured`, and on served values `Unresolved` with its reason as text (HUB-LP-18); this source vocabulary is never
used in the evidence ceiling badge, which stays `Screening only`. Part S adds the research, tier, flag and sharing labels
(15.3, 15.6).

### 7.6 Served versus the P8 research arm (Part P: contract `research/p8-research-arm` `14e13ea8`; research arm not requested)

The gate of 2026-10-15 (R12) found the revision 3 text of this section written against the superseded contract
`29ae2183`. This Part P text is rebased on the P8 integration contract at `14e13ea8`
(`docs/research/SPEC_p8_integration_contract_2026-10-15.md`, revision 2, re-gated APPROVE_WITH_CHANGES). The relay
design of revision 3, corrected per R12(b), is Part S (15.3) and waits for the contract amendment of OD1.

Facts of the contract this section relies on:

1. P8 is not a served bump (contract 0 and 10.1): `calculate_meltpool_physics`, the Build Job path, the 36 manifest
   files, the fingerprint pin, the goldens, `BUILD_JOB_SOLVER_REVISION` and the job cache key stay byte-identical
   whether research runs or not. Nothing in this spec waits for a P8 bump.
2. Research is computed only when `POST /api/python/lpbf-research-models` receives a request, and only the Research
   model panel sends one, after the user presses Run research models (contract 1.1). No served route, solver call,
   worker job or internal caller can send options to the route or receive values from it (contract 1.5).
3. No module outside `lpbf_research_*` imports a research module (guard R-ISO-1).
4. Block schema `p8-research-v3`, response `p8-research-response-v1`, request `p8-research-request-v1`; every research
   container carries `moduleEvidenceCeiling: "screening-only"` and every value its own `sourceEvidenceKind`
   (contract 6.1 and 6.2).

Consequences for protocol 1 (Part P, R12(a)):

1. Protocol 1 ships with the research arm at `RESEARCH_NOT_REQUESTED`. Both research arms of 7.1 are `unavailable` for
   every condition of every freeze; the report shows `Research arm not available: not requested: the P8 research route
   accepts requests only from the Research model panel today` (2.2). No research step, opt-in box, request builder,
   adapter, research upload or research member beyond the constant of 3.6 exists in phases 1 to 4.
2. The blind tab, the worker, the CLI and the descriptive producer send no request to the research route and import no
   research module. An AST test over every blind and descriptive module enforces both (11.1 item 3).
3. Served arms (7.1) never change because of P8; the served-closure pin does not move when the research route lands.
4. The research rules of revision 2 (coverage, common subset, bands, consistency notes, paired comparison, the class
   table) are not part of protocol 1 v1. They return, rebased on the contract and the amendment, in a later protocol id
   (`lpbf-user-blind-protocol-2`), because a released protocol record is immutable (4.6) and adding a scored arm changes
   its arm catalogue. A freeze made under protocol 1 never gains a research value afterwards.
5. Goal deviation G1 stays declared: GOAL roadmap item 1 asks for the served path and the P8 research arm side by side;
   protocol 1 v1 delivers the served path and records the research arm as not requested, with the reason, until the
   contract admits the blind tab (OD1). `keyholeCavity` would in any case never be scored against melt-pool depth
   (evidence rule 4).
6. Cost: the freeze job runs served calls only, 5 per condition (4.3).
7. The descriptive panel (section 8) carries no research curve in Part P: its research columns read `unavailable:
   RESEARCH_NOT_REQUESTED` (8.4 item 4).
8. Phase 6 starts only when the P8 owner has approved the contract amendment of OD1 (section 12).

### 7.7 Declared divergences from MELT and from GOAL

The protocol record holds this list (id, MELT or GOAL locator, rule, reason); every report prints it in full and marks
the entries that applied to the block. Adding an entry is a protocol change (new protocol id).

| Id | MELT or GOAL rule | Protocol 1 rule | Reason |
|---|---|---|---|
| D1 | MELT `reduce_conditions` (runner 1567 to 1572): a missing or non-positive target refuses, no row is dropped; GOAL kill criterion 3: no excluding adverse rows | declared measurement losses (`specimen-lost`, `section-unreadable`, `not-measured`) are excluded, listed and counted at section, track and condition level; above 20 % of tracks or of conditions is a block issue; a status change after an attempt is `not-blind-rescored-changed-targets` | user labs lose sections; refusing would push users to drop rows silently before upload |
| D2 | MELT `block_level_issues` has no boundary item | boundary not an etched fusion boundary is a block issue | observable identity (melt-pool depth) |
| D3 | no MELT item | cross-section location near track ends or unstated is a block issue | start and end transients are not the steady-state depth the served model predicts |
| D4 | no MELT item | beam profile `top-hat` or `ring` is a block issue; `unknown` is a label only | the served model is Gaussian; an issue on `unknown` would make nearly every user test inconclusive |
| D5 | MELT: initial temperature not released is a block issue | a refusal (`PREHEAT_MISSING`); `nominal-ambient` labelled | predictions cannot be frozen without T0 |
| D6 | MELT registers thresholds and leverage cuts for Ti-6Al-4V and AlSi10Mg only | thresholds reused for 316L, IN718 and IN625 with a label; low cuts 15 proposed for 316L and IN718; IN625 leverage not evaluable as a step 5 qualifier | Q4; Astra sign-off |
| D7 | MELT scores its registered arm catalogue (`arm_catalogue`, `predict_arm`) | protocol 1 scores the served Build Job melt-pool depth (`served_arm`, 3.1) | the user tests the model the app serves |
| D8 | MELT S2 is the registered melt-link candidate | the research arm is P8 `linkedMeltDepth_um`, which P8 says is not the registered S2 candidate | P8 section 2.2 |
| D9 | MELT exposure: a target read before the prediction hash | blindness statuses of 6.4, several of them declared by the user (`*-declared`) | no custodian in a user lab; the receipt anchor advice covers provable order |
| D10 | MELT status words PASS, FAIL, INCONCLUSIVE | `thresholds-met`, `threshold-not-met`, `inconclusive` and the descriptive words of 7.3 | naming only, same precedence |
| D11 | MELT refuses a non-positive target | `track-not-formed` counts as APE +inf for every arm | an adverse outcome is counted against the model, never excluded |
| D12 | no MELT counterpart | band coverage and consistency counts of the research arm are reported descriptively (protocol 2 only; inactive in protocol 1, where the research arm is not requested, 7.6) | P8 `p8-research-v3` output, no threshold attached |
| G1 | GOAL roadmap item 1: served and P8 (`keyholeCavity`, `meltDepthLink` with bands) side by side | protocol 1 v1 records the research arm as `RESEARCH_NOT_REQUESTED`; `keyholeCavity` is never scored against melt-pool depth (7.6) | the P8 contract admits only the Research model panel as a sender (OD1); evidence rule 4 |

## 8. Descriptive panel on spent sets

### 8.1 Admission

1. `data/benchmark/spent-ledger-v1.json` (schema `lpbf-spent-ledger-1`), transcribed from
   `MAIN/.orchestra/reports/blind_validation_inventory_2026-10-11.md` section 1 plus BOARD and LOG corrections (CMU
   EXPOSED and UNUSABLE; Totis equals the Udine Mendeley set; Gan Data 1 Ti64 is the same experiments as Cunningham;
   Gan Data 1 Al6061 and SS316 SPENT by p2-onset). Entry: `{datasetId, title, doi, alloy, observable
   (fusion-boundary-depth | vapour-depression-depth | keyhole-boundary-depth), datum, beam {value_um, definition,
   status stated|assumed|unverified, sensitivity_um, locator}, powerBasis, substrate, digitized, status
   SPENT|EXPOSED|EXPOSED-LOW|CLEAN|UNUSABLE, spentBy [{event, record, date}], sameExperimentsAs, loader, tableSha256,
   curveAxis speed|power, locator, licence, attribution, licenceFile, transcription table|digitized-figure|
   derived-from-raw-images, inputsInferred [{input, method, locator}] or [], usedInServedDevelopment bool}` (Part P:
   licence fields HUB-LP-16, transcription kind and inferred inputs R18, served-development flag HUB-LP-15). The ledger
   loader refuses an entry without `licence`, `attribution` and `licenceFile` (a path to a committed licence or
   attribution file, or `none` with a reason the producer then refuses to admit). Haiku transcribes, Opus reviews
   against BOARD and LOG.
2. The producer admits only `SPENT` entries. A forbidden-id test keeps out `bitharas`, `leis`, `hyer`, `aboulkhair`,
   `ruckh`, `gong`, `ullah`, `wimmer`, `huang`, `ku-leuven-in718`, `hann`, `nist-mds2-2923-in718` and `cmu`.
3. Zhao (EXPOSED) enters only through a separate maintainer-approved ledger commit that records this panel as its
   spending event (Q3). Bitharas (Part P, R18) is admitted only through its own gated SPENT record from
   `docs/research/SPEC_bitharas_descriptive_2026-10-15.md` (`research/bitharas-descriptive` `45598c42`), with
   `inputsInferred` filled and transcription `derived-from-raw-images`; until that record is committed, `bitharas` stays
   on the forbidden list. That spec and this one define "served" and the panel path differently and disagree on percent
   differences (that spec allows no percent, log or accuracy figure for its set; 8.3 item 3 shows signed percent for
   depth sets). Until the lead names one owner for the served definition and the panel path (R18, an open lead item),
   the rule here is: a Bitharas entry never gets a curve, a percent difference or a model map cell from this producer;
   it shows its own record's content under that spec's rules only. The NIST mds2-2923 IN625 regime ledger (70 units) enters only after a
   `LICENSE-ATTRIBUTION.md` with the NIST statement and locator is committed and reviewed by Opus.

### 8.2 Sets in v1

| Set | Loader | Observable | Compared arms | Context and notes |
|---|---|---|---|---|
| NIST AMB2022-03 IN718 Table 4 (7) | `table4-aggregate-v2.json` loader used by `lpbf_process_window` | fusion-boundary depth, width | served (IN718 Build Job), research melt-link | D4sigma beams |
| NIST AMB2018-02 IN625, Lane Table 3 (23) | `lpbf_public_datasets.load_lane_in625` | fusion-boundary depth, width | served (IN625 direct path), research melt-link | `POWER_NOMINAL`, `LEGACY_PROPERTIES_IN625`, two-class cut 13.6 |
| KU Leuven 316L (44) and Ti64 (14) | `load_ku_leuven_316l_ti64` | fusion-boundary depth, width | served, research melt-link | beam 37.5 um `unverified` plus a 75 um sensitivity curve |
| Totis Ti64 (80) | `load_totis_ti64` | depth, width | served, research melt-link | beam 50 um 1/e2 per loader note; datum stated by the associated paper, recorded at `python/lpbf_public_datasets.py:131-133`: depth from the top of the printed base under the 25 um powder layer (Vaglio et al. 2020, Fig. 1, Fig. 2(b), Sec. 1.3); the reason note for this datum and the powder-layer offset is Astra's to write (Rev. 4, R23; the earlier `DATUM_UNSTATED` was wrong) |
| Cunningham Ti64 (69, digitized) | `lpbf_keyhole_literature.load_cunningham_depths` | vapour-depression depth | research cavity; served Fabbro depth (the quantity `lpbf_keyhole_benchmark.py` uses, Astra confirms) | served melt-pool depth as dotted context with `different quantity: melt-pool depth versus vapour-depression depth`; read uncertainty bars; `THRESHOLD_DERIVED_FROM_THIS_SET` (cut 20) |
| Gan Data 1 Ti64 (71) | `load_gan_data1_ti64` | keyhole depth | as Cunningham | `SAME_EXPERIMENTS_AS cunningham-ti64-2019`, not independent, never added to Cunningham's n in the model map (8.3 item 4); spot labels 88 and 110 versus Methods `BEAM_ASSUMED_OR_UNVERIFIED`; the 5 printed Al6061 cases are left out (no served Al6061 model) |
| Zhao Ti64 (20 boundary depths) | `load_zhao_boundary` | keyhole boundary depth | as Cunningham | only after Q3; pore markers never plotted as depths |

Hofmann stays in the existing comparison view.

### 8.3 Computation (Python only, `python/tools/lpbf_spent_descriptive.py`)

1. Load rows through the pinned loaders with hash verification; predictions through `lpbf_served_arms` (the same served
   definition as the blind test), flat-plate pinned as in `pin_flat_plate(allow_raytracer=False)` of
   `python/tools/lpbf_dataset_comparison.py:79` (a tools module with that signature; `lpbf_calibration_stats.py:33` and
   `lpbf_powder_layer_analysis.py:69` have their own zero-argument versions, which are not used). Part P: no research
   curve; the producer sends no research request and imports no research module (7.6). Every measured value carries the
   source label `Measured` with `transcription` and its locator (these are published, transcribed measurements, not
   user values), and every served value `Unresolved` with its reason as text (14.6).
2. Curves per group (alloy, power or speed, beam, substrate) with at least 3 points: 25 log-spaced points from 0.8 x min
   to 1.25 x max of the group axis; each point also carries the unrounded index so the UI can switch the x axis.
3. Deviation per set and arm: n, failed, unavailable, median signed relative difference in percent, p10 and p90, and the
   same per served index bin (below the low cut, between, at or above 20; IN625 two bins at 13.6). No thresholds, no
   pass or fail, no rank.
4. Model map: sets x bins, direction (`model deeper`, `model shallower`, `mixed`) with n. Sets that share
   `sameExperimentsAs` form one map row keyed by the experiment: Gan Data 1 Ti64 and Cunningham are never added
   together as independent n; the row counts the Cunningham conditions once and names Gan as the same experiments,
   and the set view shows Gan on its own with its own deviation and the `SAME_EXPERIMENTS_AS` note.
5. Why notes from a closed catalogue `data/benchmark/spent-descriptive-reasons-v1.json` written by Astra and gated by
   Opus: `{code, sentence, source, locator, appliesWhen, expectedSign}` with codes `BEAM_ASSUMED_OR_UNVERIFIED`,
   `DATUM_UNSTATED`, `DATUM_NOT_ORIGINAL_SURFACE`, `OBSERVABLE_VAPOUR_NOT_MELT`, `POWER_NOMINAL`,
   `POWDER_LAYER_FLAT_PLATE_MODEL`, `DIGITIZED_FROM_FIGURE`, `LEGACY_PROPERTIES_IN625`, `SAME_EXPERIMENTS_AS`,
   `THRESHOLD_DERIVED_FROM_THIS_SET`, `KEYHOLE_LEG_SCALING`, `CONDUCTION_LEG_BIAS`, `EXTENT_NOT_COMPUTED`,
   `INDEX_OUTSIDE_SERVED_BAND`, `RESEARCH_NOT_REQUESTED`, `OUT_OF_RESEARCH_SCOPE`, and `USED_IN_SERVED_DEVELOPMENT`
   (Part P, HUB-LP-15: the set was used while the served physics was developed, for example NIST AMB2022-03, so its
   agreement says little about the model; set from the ledger flag `usedInServedDevelopment`). A note appears only when its rule
   holds and, for a signed reason, the observed sign matches; otherwise the card says `No catalogued explanation`.
   Every sentence starts `Candidate explanation, not tested:`.
6. Output: full JSON plus slim `docs/LPBF_SPENT_DESCRIPTIVE_<date>.view.json` (schema
   `lpbf-spent-descriptive-view-1`, canonical JSON, 6 significant digits, under 150 KB raw): `generatedAt`,
   `implementationHash`, `servedIdentity`, `research {requested: false, reasonCode: "RESEARCH_NOT_REQUESTED"}`,
   `spentLedgerSha256`, `reasonsCatalogSha256`,
   `honesty`, `arms`, `sets [{provenance, spent, observable, beam, groups [{fixed, curve, points}], deviation, notes}]`,
   `modelMap`. `servedIdentity` includes the served-closure pin sha256 (3.6). `--check` re-derives and compares; a
   Python test fails when `implementationHash` differs from the live fingerprint (leaderboard pattern), so the record
   is regenerated in every bump batch. The tool prints counts and hashes only.
   CI scope (decided): the full `--check` re-derivation stays out of CI, like the P7b bit-exact parity goldens (the
   `ci.yml` comment above the fingerprint step), because 6-significant-digit floats from a solver run can differ
   across machines and library builds. CI runs the structure-and-hash test only (schema, honesty literals, SPENT-only
   ids, ledger and catalogue sha256, `implementationHash` equal to the pin, `servedClosurePinSha256` equal to the
   committed served-closure pin (Part P, ENG-19), size cap). The re-derivation runs locally in
   every bump batch and its result, with the machine and library versions, is recorded in PROOF.

### 8.4 Viewer

1. `src/data/lpbfSpentDescriptive.ts` (validator: schema prefix, honesty literals, every set `SPENT`, set ids not in the
   forbidden list, no `rank`, `score`, `pass`, `fail` keys), `src/data/lpbfSpentDescriptiveRecord.ts` (non-eager
   `import.meta.glob`, newest by name, null when absent, own lazy chunk so the comparison chunk and
   `scripts/bundle-budgets.json` stay untouched).
2. `src/components/3d-distortion-lab/SpentSetDescriptivePanel.tsx`, mounted by `React.lazy` inside a `Suspense`
   boundary with a static one-line fallback at the end of the `LpbfDatasetComparisonLab` export, outside
   `DatasetComparisonView`, so it renders without the 2026-10-05 record. Without the boundary the existing
   `renderToStaticMarkup` tests in `tests/lpbf-dataset-comparison-lab.test.tsx` (lines 13 and 71) can throw on the lazy
   component; with it they render the fallback, and a test asserts that.
3. Content: heading `Spent sets, descriptive`, badge per 2.2 and the record statement; `How to read this` disclosure;
   model map table; set selector as a labelled radiogroup with roving arrow keys; provenance card (citation, DOI via the
   existing `doiHref`, licence, sha256, rows, spent status with `spentBy`, observable, beam reading); a purpose-built
   SVG (x speed or power on a log axis, toggle to the unrounded index with cut lines; measured points with SD or read
   uncertainty bars; served solid, research dashed, context dotted; text legend); deviation chips (`model deeper by
   about x % (n)`) per bin; notes with source; a data table fallback inside `details`; empty state; a link `Test the
   model on your own tracks`. Not the parity `ScatterPlot` (its 1:1 and plus or minus 30 % guides look like
   thresholds). Every number carries `data-source` with its record field path.
4. Research columns read `unavailable: RESEARCH_NOT_REQUESTED` in Part P (7.6). Research curves return only with the
   contract amendment of OD1 and a later record (Part S, 15.3). The committed record is static: viewing the panel sends
   no research request.
5. Contract: `python/module_contracts_dataset_view.py` gains browser-local operation `display-spent-descriptive-record`
   (output fields `datasets`, `curves`, `deviation`, `notes`, `honesty`, chosen so `looks_like_status_key` stays clear)
   and its source refs. Its legacy note (`python/module_contracts_dataset_view.py:32`, "Vite eagerly bundles the
   committed .view.json record") gains one sentence: the spent descriptive record is loaded lazily through a non-eager
   `import.meta.glob` in its own chunk, and its absence renders the panel's empty state.
   `docs/modules/lpbf-dataset-comparison.md` and `src/generated/*` are regenerated by `scripts/emit-module-registry.py`,
   never hand edited.

## 9. Security and limits

1. Transport: same-origin guard on `/api/lpbf`, login, CSRF and the rate limit from `applySecurity`; no route change.
   The one Node edit forwards the blind environment to a WSL worker (3.3), so read-only mode, the store root and the
   shared-host settings reach the worker on every platform.
2. No client path: `freezeKey` is 64 hex computed by Python; artifact names are a closed set; every store path is
   derived server side; display file names follow 4.2 item 10 and are never used as paths.
3. Parsing: strict UTF-8 CSV, header whitelist before rows, caps enforced in Python regardless of browser checks,
   formula-like ids refused, the template example row refused, target ranges checked with unit hints, zip and xlsx
   bytes refused, no zip reader anywhere.
4. Leak control: no predicted value in any preview, receipt, list, get or job result (recursive scan in the enforcer
   and in tests); the frozen document and bundles are state gated in the artifact branch, the bundle job and the CLI;
   the blind child is silent (descriptors 1 and 2 to devnull, warnings dropped, fixed error codes, counts-only progress)
   and `execute()` filters the log, so `progress.log`, the sqlite `log` and `error` columns and `GET /api/lpbf/jobs/:id`
   carry no cell value and no prediction. Tests seed unique sentinel numbers, both as target values and as predicted
   depths returned, printed, warned and raised by a stubbed solver, and search every output for them (11.1 items 6
   and 7). The ledger never carries values.
5. Integrity: exclusive create, sidecars, ledger chain, recomputed `freezeKey`, crash-safe commit points with
   reconciliation (3.5), sha256 check of every served document in the worker and again in the browser where a secure
   context allows it (3.4 item 5). Local tamper evidence only.
6. Privacy: data stays under the blind root (gitignored, dockerignored, a volume in Docker); no outbound call (so air-gap
   needs no change); NoNetwork socket patch in tests; the CLI works offline. The calibration-store overlap check reads
   tuples only and drops measured fields at parse (6.4 item 7).
7. Shared host: the store is not scoped per user, so in a Docker or LAN deployment with login every signed-in user could
   list and fetch every blind test, including proprietary measurements and predictions. The worker therefore refuses
   blind mutations with `STORE_SHARED_HOST` when `METALLIKSA_HOST` is set to an address other than `127.0.0.1`, `::1`
   or `localhost`, unless `METALLIKSA_USER_BLIND_SINGLE_USER=true` declares a single-user install. Reads stay available
   so existing tests can be exported. `docker-compose.yml` publishes the port on `127.0.0.1` only and binds `0.0.0.0`
   inside the container, so it sets `METALLIKSA_USER_BLIND_SINGLE_USER=true` with a comment that whoever publishes the
   port on another interface must remove it. The UI shows the shared-host warning of 3.4 item 7 whenever the flag is
   set or the page is not on a loopback name. Read-only installs refuse blind mutations (`STORE_READ_ONLY`).
8. Disk: caps in 3.5; no delete API; manual removal documented.
9. Queue: a freeze can delay a Build Job by up to about a minute at the cap (3.2); preview, list and get are synchronous,
   write-free and solver-free, and are answered while a queued job runs.
10. Static demo: no worker, the tab shows `DemoUnavailable`; the descriptive panel works from the committed record only.
11. Build Job cache: `_legacy_broad_cache_fingerprint` hashes every `python/*.py` file, so the broad Build Job cache
    key changes with every new or edited Python file of this work, in every phase that touches one, not once (Part P,
    ENG-21); each change makes cached Build Job and GPU-pilot worker jobs recompute once; PROOF states this as recurring;
    no served value changes.
12. Secure context: without `crypto.subtle` (plain http to a non-loopback address) the commitment is pasted, not
    computed, and the browser hash check is skipped with a visible note; the worker check always runs (3.4 item 5).
13. CSV exports: `blockLabel` and file names are restricted at input, and every text cell of a blind export is
    neutralised against formula injection; numbers are never prefixed (3.4 item 4).
14. No upload (revision 3): share and sealed features make no outbound request from Node, Python or the browser; the
    only network use, in Part S after OD1, is the same-origin research route on the user's explicit request (15.3). Python tests run
    under the NoNetwork socket patch; a TypeScript test fails on any non-same-origin URL in the new client modules;
    links are text with a copy button. Air-gap mode needs no change (`server/airgap.ts` untouched).
15. Research relay (Part S only): the relayed subsets are closed, size-capped and bound by hash at freeze; the client never renders,
    persists or logs them; the worker never trusts a relayed value beyond the identity checks of 15.3, and the record
    says the values were relayed and are client-asserted (D13 of 15.3).
16. Imported files are untrusted (maintainer side): a share tar is read member by member against the closed name set;
    absolute paths, `..`, links, devices, duplicate names, non-regular members and members outside the manifest refuse
    the import; caps 32 MiB per tar and 2 MiB per JSON member; no zip reader; nothing is extracted to a path from the
    archive; commitments, predictions and release manifests are closed JSON of at most 512 KiB; nothing imported is
    executed or imported as code, and the served model never reads an imported file. Evidence images are hashed and
    listed only, never decoded by the app.
17. Personal data: identity fields are optional below Evidenced, each with a `public` choice; an institutional email
    appears in public files only as its sha256; the UI states that a Mode B commitment is public and permanent; exports
    never contain the OS user name, host name, store paths or machine identifiers (a test scans export bytes for them);
    the UI asks the user to strip camera and location metadata from images before hashing.
18. Order and integrity limits: local ledgers prove local order only (14.3.4); Mode B order rests on GitHub server
    times and the Zenodo server-side record creation timestamp (`created`), never on the depositor-set
    `publication_date` and never on git author or committer dates a client can set; an email release is timed by the
    maintainer's record, labelled so, and never counts (Rev. 4, R6, 15.4).
19. Fabrication: a sealed submission proves when targets were fixed, not that they are real; tiers, review, plausibility
    flags and the two-independent-campaign rule are the mitigation (14.1 item 7, 14.7).

## 10. Files to add and change, with owners

Owners: Opus (architecture, hard and integrity-critical code), Sonnet (ordinary code and tests), Haiku (chores), Astra
(physics sign-off). Paths under `WT`.

Gates. Opus never gates its own code (maintainer rule, 2026-10-10). Every file Opus authors here (`lpbf_blind_stats`,
the store, freeze, score, the façade and enforcer, the worker branches, the P8 adapter) is gated by a fresh Opus run:
a new session with no authoring context, given this spec, the diff and the test output, writing its own gate record.
Sonnet and Haiku work is gated by the authoring-independent Opus reviewer as usual. "Opus review" in the phase
acceptance lines below means this: a fresh Opus gate for Opus-authored code, the Opus reviewer otherwise.

### 10.1 Add

| File | Owner |
|---|---|
| `python/lpbf_blind_stats.py` | Opus, fresh Opus gate (Haiku generates golden vectors from the runner at `e91d0fbd` on synthetic data) |
| `python/lpbf_served_arms.py` | Sonnet, Opus review, Astra sign-off of arm set and conversions |
| `python/lpbf_blind_research.py` (Part S, phase 6, after OD1; replaces `lpbf_p8_adapter.py`, R13) | Opus (fresh Opus gate), Astra sign-off of the reason-code class table |
| `data/blind/served-closure-pin-v1.json` (generated by `pin-served-closure`) | Sonnet runs, fresh Opus gate reviews each change |
| `python/lpbf_user_blind_inputs.py`, `python/lpbf_user_blind_targets.py` | Sonnet |
| `python/lpbf_user_blind_store.py` | Opus, fresh Opus gate |
| `python/lpbf_user_blind_freeze.py`, `python/lpbf_user_blind_score.py` | Opus, fresh Opus gate |
| `python/lpbf_user_blind.py` | Opus (façade, enforcer, silent child, log filter; fresh Opus gate), Sonnet (validators) |
| `python/lpbf_spent_ledger.py` | Sonnet |
| `python/tools/lpbf_user_blind.py` | Sonnet |
| `python/tools/lpbf_spent_descriptive.py` | Sonnet; Astra owns quantity mapping |
| `python/test_lpbf_blind_stats.py`, `test_lpbf_served_arms.py`, `test_lpbf_user_blind_inputs.py`, `test_lpbf_user_blind_store.py`, `test_lpbf_user_blind_crash.py`, `test_lpbf_user_blind.py`, `test_lpbf_worker_blind_jobs.py`, `test_lpbf_spent_ledger.py`, `test_lpbf_spent_descriptive.py`; Part S adds the research adapter tests with the fixture `python/fixtures/p8_research_response_v1.json` (copied from the contract fixture `tests/fixtures/lpbf-research-response-v1.json` once it is committed, with its blob hash; the tests skip with that reason until then, R13) | Sonnet (Opus writes the isolation, blindness, leak and crash cases) |
| `data/blind/lpbf-user-blind-protocol-v1.json` and `data/blind/lpbf-user-blind-wording-v1.json` (generated), `data/blind/templates/blind_inputs_v1.csv`, `blind_targets_v1.csv`, `blind_metadata_v1.json` | Haiku |
| `data/benchmark/spent-ledger-v1.json` | Haiku transcribes, Opus reviews |
| `data/benchmark/spent-descriptive-reasons-v1.json` | Astra writes, Opus gates |
| `docs/LPBF_SPENT_DESCRIPTIVE_<date>.json` and `.view.json` (generated) | Sonnet runs, Opus checks |
| `docs/LPBF_USER_BLIND_TEST.md` (guide: templates, metadata meaning, protocol, what is and is not enforced, labels, manual archiving) | Haiku drafts, Opus reviews |
| `src/data/lpbfUserBlind.ts`, `src/services/lpbfUserBlindClient.ts`, `src/store/useUserBlindStore.ts` | Sonnet |
| `src/components/research/BlindTestPanel.tsx`, `BlindTestMetadataForm.tsx`, `BlindTestInputsStep.tsx`, `BlindTestReceiptView.tsx`, `BlindTestTargetsStep.tsx`, `BlindTestReportView.tsx`, `BlindTestList.tsx` | Sonnet |
| `src/components/research/blindTestHelp.ts` | Haiku drafts, Opus reviews wording |
| `src/data/lpbfSpentDescriptive.ts`, `src/data/lpbfSpentDescriptiveRecord.ts`, `src/components/3d-distortion-lab/SpentSetDescriptivePanel.tsx` | Sonnet |
| Revision 3: `python/lpbf_blind_share.py`, `python/lpbf_sealed_submission.py` | Opus, fresh Opus gate (integrity-critical: hashes, chain, state machine, import safety) |
| Revision 3: `python/lpbf_submission_plausibility.py` | Sonnet; Astra signs off the constants; Opus review |
| Revision 3: `python/tools/lpbf_sealed.py`, `scripts/research-route-batch.ts` | Sonnet, Opus review |
| Revision 3: `data/blind/lpbf-sealed-protocol-v1.json` (generated), `data/benchmark/sealed-submissions-v1.json` (empty `entries` at start), `data/benchmark/approved-reviewers-v1.json` (empty until the maintainer approves a reviewer) | Haiku runs the generator; the maintainer owns the reviewer list |
| Revision 3: `python/test_lpbf_blind_share.py`, `python/test_lpbf_sealed_submission.py`, `python/test_lpbf_submission_plausibility.py`, `python/test_lpbf_research_relay.py` | Sonnet (Opus writes the order, tamper, state-machine and leak cases) |
| Revision 3: `src/data/lpbfSealed.ts`, `src/components/research/BlindTestShareStep.tsx`, `SealedSubmissionPanel.tsx`, `SubmissionTierBadge.tsx`, `tests/lpbf-sealed.test.ts`, `tests/lpbf-sealed-panel.test.tsx` | Sonnet |
| `tests/lpbf-user-blind.test.ts`, `tests/lpbf-user-blind-panel.test.tsx`, `tests/lpbf-spent-descriptive.test.tsx`, `tests/fixtures/lpbf-user-blind-report.SYNTHETIC.json`, `tests/fixtures/lpbf-spent-descriptive.SYNTHETIC.json` | Sonnet (fixtures Haiku) |

### 10.2 Change

| File | Change | Owner |
|---|---|---|
| `python/lpbf_worker.py` | blind branches in `submit` (closed `BLIND_SUBMIT_ERROR_CODES` mapping, R15), `execute` completion (log filter before every log and error write), `get`, child `main` (silent blind branch ahead of the generic exception print), `_archive_run_kind`, `capture`, `artifact` (reveal-or-score gate for freeze and bundle), `rpc_error_response` (`BlindRefusal` envelope, 3.2 item 10, R15); forced no-dedupe except `user-blind-open`; per-type timeout | Opus, fresh Opus gate |
| `tests/` for `server/lpbfWorkerBridge.ts` (Part P, R15) | a test that a `BlindRefusal` envelope from `rpc_error_response` reaches HTTP 422 with its blind code and message; no bridge or route logic changes (3.2 item 10) | Sonnet, Opus review |
| `python/lpbf_worker_rpc.py` | `_estimate` branch for `USER_BLIND_RPC_TYPES` (preview, list, get) | Opus, fresh Opus gate |
| `server/pythonRuntime.ts`, `tests/python-runtime.test.ts` | `wslJobRootEnvironment` generalised to forward `METALLIKSA_USER_BLIND_ROOT` and `LPBF_MACHINE_CALIBRATION_DIR` (`/p`, drive-letter rule), `METALLIKSA_READ_ONLY`, `METALLIKSA_HOST` and `METALLIKSA_USER_BLIND_SINGLE_USER` through `WSLENV`, each on its own with no early return when `METALLIKSA_JOB_ROOT` is unset (3.3, R16); tests for each variable, for `METALLIKSA_JOB_ROOT` unset, and for a refused UNC blind root | Sonnet, Opus review |
| `src/data/lpbfExperimentPlan.ts` | `export` added to `csvCell` (line 187) and `toCsv` (line 192), no behaviour change | Haiku |
| `python/test_lpbf_worker_dispatch.py` | blind job types at submit and repeat, not archivable, child path with stub | Sonnet |
| `src/components/AdvancedResearchHub.tsx` | tab entry in place, render line, brief selector hidden on the tab | Sonnet |
| `src/store/useResearchStore.ts` | `ResearchTab` union and whitelist in place | Sonnet |
| `python/module_contracts_research.py`, `python/test_module_contract_research.py` | browser-local ops (`download-blind-test-templates`, `edit-blind-test-metadata`, `check-blind-test-headers`, `render-blind-test-report`, `export-blind-test-report`); remote ops on the bound worker routes built with a worker authority (`Authority(kind="lpbf-worker", worker_method=...)`, the `_worker` form of `LEGACY_OPERATIONS` at `python/module_registry.py:160-168`), not the builder's `_remote` helper, which makes `node-provider` authorities; lifecycle changed from `background_work="none", resources=("fetch",)` to `background_work="server-job", resources=("fetch", "interval")`, with the asserts at `test_module_contract_research.py:45-46` updated in the same commit; the legacy note sentence "No polling, interval, server job or background analysis is launched by the hub" replaced by one that names the blind-test polling (visible-only, queued blind jobs only); line anchors on `AdvancedResearchHub.tsx` replaced by symbol anchors | Sonnet, Opus review |
| `src/components/MeltPoolMeasuredTrackPanel.tsx` | call to action | Haiku |
| `src/components/ExperimentalValidationLab.tsx` | one pointer line; asserted strings untouched | Haiku |
| `src/data/paletteKeywords.ts` | `research-hub` keywords | Haiku |
| `src/components/3d-distortion-lab/LpbfDatasetComparisonLab.tsx` | lazy mount of the descriptive panel | Sonnet |
| `python/module_contracts_dataset_view.py`, `python/test_module_contract_dataset_view.py` | second browser-local operation and refs | Sonnet |
| `src/generated/moduleRegistry.json`, `moduleRegistry.ts`, `moduleRegistryCore.ts`, `docs/modules/lpbf-dataset-comparison.md` | regenerated only | Haiku runs the emitter |
| `src/components/LpbfExperimentPlanPanel.tsx` | phase 4: `Download blind-test templates from this plan`, behind a notice (Part P, R21): `This plan shows the app's predicted depths for these conditions. If you have looked at them, answer yes to "predictions viewed" and the test will not be blind. If you import measurements of these conditions for machine calibration, the test will not be blind either. To keep it blind, download the templates without opening the plan's predictions.` The button writes inputs templates only, never predicted values. | Sonnet, Opus review |
| `python/tools/lpbf_benchmark_score.py`, `src/data/lpbfLeaderboard.ts`, `src/components/LpbfLeaderboardPanel.tsx`, `tests/lpbf-leaderboard.test.tsx`, `docs/LPBF_BENCHMARK.md` | Rev. 4 (ENG-20): no change to `lpbf_benchmark_score.py` or the leaderboard schema; the sealed table reads `sealed-submissions-v1.json` through its own loader in `src/data/lpbfSealed.ts`, shown in `LpbfLeaderboardPanel.tsx` after the screening tables with the caveat, title and verdict mapping of 15.7; the four committed v1 records keep loading; tests for no PASS or FAIL token and no rank control | Sonnet, Opus review |
| `src/services/lpbfUserBlindClient.ts`, `src/data/lpbfUserBlind.ts` | Part S (after OD1): research relay and `extractBlindResearchSubset` (3.4 item 9, 15.3) | Sonnet, Opus review |
| `data/benchmark/spent-ledger-v1.json` | revision 3: entry kind `shared-result` (14.3.5), added only by maintainer commits | Haiku drafts the schema change, Opus reviews |
| `docs/MODULE_EVIDENCE_INVENTORY.md` | research-hub and lpbf-dataset-comparison rows name the new files and next gap; the research-hub row also says that the wired registry keeps the legacy research-hub row, which does not list the LPBF worker calls the blind-test tab makes (they are bound under `3d-distortion-lab`), and that the contracted research-hub builder documents them | Haiku |
| `docker-compose.yml`, `Dockerfile` | `METALLIKSA_USER_BLIND_ROOT=/data/user-blind` and mkdir; `METALLIKSA_USER_BLIND_SINGLE_USER=true` in `docker-compose.yml` with the comment of 9.7 | Haiku |
| `.github/workflows/ci.yml` (protected) | append the new Python test modules to the explicit list (lines 80 to 130) | Haiku prepares; maintainer adds the Ceiling-Review trailer at the batch push |
| `PROOF.md`, `STATUS.md` | milestone entries only, labels unchanged statement | Opus |

Not changed: `server.ts`, `routes/*` (read-only mode is enforced in the worker after forwarding, not in a route),
`routes/AUTHORITY_ALLOWLIST*.json`, `python/module_registry.py`,
`python/module_registry_seed.json`, `src/App.tsx`, `src/modules/views.ts`, nav golden, every `*.ceiling.json`, every
fingerprint manifest file, `python/lpbf_implementation_fingerprint.expected`, `src/services/pythonComputationService.ts`
(its research method comes from the P8 contract, not from this spec), `server/airgap.ts`, every file of the P8
contract (`lpbf_research_*`, `routes/physics.ts`, `python/persistent_ipc_service.py`, the research pin).

## 11. Tests

### 11.1 Python

1. `test_lpbf_blind_stats.py`: golden vectors (embedded, synthetic) produced by the runner at `e91d0fbd` and P3 for
   every extracted function, including `beam_d_um`, `assert_no_target_loaded` and `served_index`; +inf neighbours in
   rank quantiles; exact boundaries (0.20 passes, the next representable value above fails) for all four thresholds;
   mean signed over finite rows; max APE +inf; bootstrap determinism; cv_pool minimums and `not_evaluable`; u_m floor
   and `u_m_assumed`; grade tables incl. unstated beam is C; reduction refusing repeated rows without a track key; full
   status precedence matrix, including an IN625 block that fails a threshold reported as `threshold-not-met` and an
   IN625 block that meets all four reported as `inconclusive` (leverage not evaluable); sign-flip p values on small
   enumerations; `FWHM_FACTOR` value.
2. `test_lpbf_served_arms.py` (real solver, synthetic conditions): served depth, width and extentStatus equal
   `solve_lpbf_build_job(..., bypassCache=True)["thermal"]["meltPoolGeometry"]` for three conditions per Build Job alloy;
   `include_process_map` False and True identical (or the adapter uses True); non-computed extent gives failed; IN625
   equals the direct call and carries `legacy-estimated-secondary`; index equals unrounded `normalized_enthalpy`; bare
   plate layer invariance check recorded for Astra; `beam.quantity` radius doubles before conversion; identity carries
   the live fingerprint equal to the pin and the served-closure pin equal to the live file hashes; the closure test
   (3.6) runs after executing `served_arm` and `sensitivity_arms` for all five alloys and finds no project module
   outside the manifest and the closure pin, and none of `lpbf_build_job_solver`, `lpbf_machine_calibrated_meltpool`,
   `powder_bed_raytracer`, `warp_thermal_solver` or `lpbf_research_*` (Part P, R14); the closure pin hashes are equal
   for an LF and a CRLF copy of each file (`canonical_source_bytes`); a one-byte edit of any closure file in a temp copy
   gives `PREDICTOR_NOT_PINNED` naming that file; importing the modules leaves `IMPLEMENTATION_SOURCE_FILES` and both
   pins unchanged.
3. Research arm fixed (Part P, R12(a)): every freeze, receipt and report records both research arms as `unavailable`
   with `RESEARCH_NOT_REQUESTED`; the predictor identity's research member is the constant of 3.6; a freeze request
   carrying a `research` member is refused; an AST test over every blind and descriptive module (`lpbf_user_blind*`,
   `lpbf_served_arms`, `lpbf_blind_stats`, `lpbf_spent_*`, both CLIs) finds no import of an `lpbf_research_*` module
   and no reference to `lpbf-research-models` or `/api/python/lpbf-research-models`; the same check runs over the
   TypeScript blind modules. The research adapter tests of Part S (15.3) live in a file named `test_lpbf_research_*` so
   the contract's own guard scope covers them, and skip with the reason `contract fixture not committed` until it is.
4. `test_lpbf_user_blind_inputs.py`: every refusal code in 6.1 for inputs and metadata, including
   `SYNTHETIC_EXAMPLE_ROW`, `FILE_NAME_INVALID`, a formula-like or tabbed `blockLabel`, and published data in
   pre-measurement mode; target-like header refused with a deliberately malformed second line that must not be
   reached; aliases echoed, `d_um` not an alias, ambiguity refused; three dialects; BOM and CRLF; zip magic and
   non-UTF-8 refused; caps; key modes (condition id, unique track ids); replication mismatch; grades, block issues and
   labels from metadata (`beam.profile` `unknown` is a label, `ring` an issue); preview determinism and `previewSha256`
   (acknowledgements do not change it; a new overlap does); preview holds no depth-like value and makes no solver call
   (patched solver raises). Part P additions: `INPUTS_COLUMN_MISSING`, `FILE_EMPTY`, `CSV_MALFORMED` with its row
   number, `HEADER_UNIT_UNKNOWN`; `Speed (m/s)` converts by 1000 and `Power (kW)` by 1000 with the factor echoed in
   `parsedInputs` and frozen in `conversion`, and a unitless `speed` header carries the `unit not stated` label (R20); a
   semicolon header under `comma-dot` gives the header-level `DIALECT_MISMATCH` before any unknown-column refusal
   (R20); the `INPUTS_TARGET_COLUMN` message names the matched token (U11); every refusal at preview and submit arrives
   as a `BlindRefusal` envelope mapped to 422, never as a 400 with exception text (R15); row numbers count the header as
   row 1 (U9).
5. `test_lpbf_user_blind_store.py` and `test_lpbf_user_blind_crash.py`: exclusive create refuses overwrite; sidecar
   verification; ledger chain verify and one-byte tamper detection; the OS lock is released when its holder is killed
   (a child holding it is killed, the parent then takes it at once); staging leftovers listed as incomplete and never
   used; read-only, full and shared-host refusals; content-addressed upload reuse; reconciliation adds a missing event,
   cuts a partial trailing line and rebuilds the index; the kill-at-each-step matrix of 3.5 item 5 for every mutation
   type, on a native folder and on a drvfs folder under WSL; a record and its sidecar appear together or not at all;
   two concurrent mutations computing the same attempt number end with distinct numbers and one chain; a process of the
   other lock domain is refused with `STORE_LOCK_DOMAIN` and can still read (Part P, R17).
6. `test_lpbf_user_blind.py` (stub solver, temp root, NoNetwork socket patch): end to end preview, freeze, receipt,
   score; freeze idempotent and `freezeKey` independent of `createdAt`; `PREDICTOR_NOT_PINNED` with a monkeypatched
   fingerprint; `ACK_REQUIRED` and `OVERLAP_CHANGED` at submit and in the child (an overlapping test revealed between
   submit and child run); receipt, list, get and every job result hold no predicted number (recursive scan); AST check
   that `lpbf_user_blind_freeze` and its project imports exclude `lpbf_user_blind_targets` and
   `lpbf_user_blind_score`; an `open()` and `Path.open` audit during freeze proves no targets path is opened; reveal
   record precedes servability and later reports say `not-blind-predictions-revealed`; overlap with an earlier revealed
   or scored test gives `not-blind-earlier-test-overlap`; the commitment exception holds the same way for the own
   reveal, another test's exposure and a calibration import after the `frozen` event, and does not hold before it;
   `usedForMachineCalibration` true, and a tuple in a synthetic `.runtime/user-calibration` or
   `.runtime/machine-calibration` store, give `not-blind-used-for-calibration`, with sentinel width and depth values in
   those stores absent from every output; published data with an unknown DOI gives `blind-retrospective-declared` and
   its label; refused scores create no attempt; `TARGET_OUT_OF_RANGE` with the millimetre hint and no value in the
   message; identical targets return attempt 1; changed targets give attempt 2 `not-blind-rescored-changed-targets`;
   commitment match, mismatch refusal and accepted mismatch; measurement losses above 20 % of tracks (with conditions
   under 20 %) and above 20 % of conditions each give inconclusive; a not-formed track makes its condition APE +inf for
   every arm and is never listed as excluded; reduction `maximum-only` gives inconclusive; datum not original surface
   gives inconclusive; powder layer gives `descriptive-not-scored`; n < 12 inconclusive (the research-arm coverage case
   moves to protocol 2, Part S); published DOI
   in the ledger gives `not-blind-data-already-used-by-app`; `changedSinceFreeze` scored on frozen values; a changed
   score source gives `scoring code changed since freeze` and not the predictor label; a wording-table change gives no
   label; a protocol rules change under the same id gives `PROTOCOL_CHANGED`; one-byte edited freeze refused; every
   output carries the honesty literals and the full divergence list; sentinel target numbers never appear in errors,
   logs, ledger or job results, including when a targets cell holds a malformed number built around a sentinel (for
   example `12.5x7` or `1,234.5`) at submit, which must give `NUMBER_INVALID` or `BLIND_SUBMIT_INTERNAL` with no cell
   text in the 422 or 400 body (Part P, R15); the child asserts `lpbf_user_blind_targets` and `lpbf_user_blind_score`
   are absent from `sys.modules` before the freeze commit point (ENG-17); the comparison CSV of 4.5 item 6 has the
   pinned header and preamble and is refused before a reveal or score (R21). Bundle and CLI gate: a bundle request and CLI `show` and `bundle` before a reveal or
   score refuse with `REVEAL_REQUIRED` and write nothing; with the reveal phrase they write `reveal-<n>.json` and the
   `revealed` event before the tar or the printout (ledger order checked), and the next report is not blind.
7. `test_lpbf_worker_blind_jobs.py` and `test_lpbf_worker_dispatch.py` additions: closed payload validation of every
   type in 3.2.1 at submit and on the estimate RPC (validation envelope, no job row), for `POST /api/lpbf/jobs` and the
   repeat path; blind mutations never deduplicated, `user-blind-open` deduplicated; list and get on the estimate RPC
   create no `.lpbf-jobs` folder, no sqlite row and no queue slot over 100 polls, and answer within the 100 ms target
   while a stubbed long Build Job holds the queue; `input.json` holds hashes only; per-type timeouts; completion and
   `get()` use the blind enforcer, not `enforce_thermal_balances`; `_archive_run_kind` None and `capture()` refuses;
   `artifact()` serves blind documents from the store with sha256 check, refuses the freeze document and the bundle
   before reveal or score, refuses names outside the set; job result carries `provenance`; existing
   `test_lpbf_worker_*` unchanged. Prediction leak sentinel: a stubbed solver returns unique sentinel PREDICTED depths
   and also prints them to stdout and stderr (Python and an `os.write` to descriptors 1 and 2), emits them in a
   warning, and in a second run raises an exception whose message contains them; the test then scans `progress.log`,
   the sqlite `log` and `error` columns and the worker `get()` response (and, in the phase 2 smoke, the body of
   `GET /api/lpbf/jobs/:id`) and finds none of them, only `blind-progress` counts and `blind-error <CODE>` lines.
8. `test_lpbf_spent_ledger.py` and `test_lpbf_spent_descriptive.py`: ledger schema and closed vocabulary; producer
   refuses non-SPENT and forbidden ids; quantity mapping (vapour sets only against vapour arms, context caption
   present); `SAME_EXPERIMENTS_AS` on Gan, no `DATUM_UNSTATED` on Totis (its datum is stated, 8.2, Rev. 4), `THRESHOLD_DERIVED_FROM_THIS_SET` on Cunningham;
   the model map counts Gan and Cunningham once; notes only from the catalogue and only with matching sign; KU beam 37.5
   unverified with a 75 sensitivity curve; IN625 two bins at 13.6; no `validated`, `accuracy`, `rank`, `score`, pass or
   fail tokens; size under 150 KB; determinism; committed record current against the live fingerprint (structure and
   hashes only, the CI part); the full `--check` re-derivation as a local-only test, excluded from CI (8.3 item 6).
9. Contract and guards: `python -B -m unittest test_module_contract test_module_contract_research
   test_module_contract_dataset_view test_allowlist_ceilings test_module_warm_parity`, `python
   scripts/emit-module-registry.py --check`, fingerprint pin test unchanged, `pin-served-closure --check`,
   `export-protocol --check`, and in revision 3 `lpbf_sealed.py export-protocol --check`.
10. `test_lpbf_blind_share.py` (revision 3, Part S): the share tar is deterministic; `SHARE_NO_SCORE`; targets absent without
    consent and present for every attempt with it (no attempt can be left out); licence and `publishAllowed` rules and
    `SHARE_ATTRIBUTION_REQUIRED`; the ledger excerpt verifies with redacted links and a one-byte edit of any line fails;
    `share-verify` passes on an untouched tar and fails, with the right check id, on each tamper (a member hash, the
    freeze record, a `scored` event moved before `frozen`, a commitment that does not match, a member outside the
    manifest); re-score byte for byte with targets, the skip label without them; `share-verify` writes nothing;
    `share-import` writes only under the shared-results root and creates the `EXPOSED` entry draft and the seen-tuples
    index; a later local test with an overlapping tuple on the maintainer's machine is
    `not-blind-data-already-used-by-app`; a later sealed import with the same hashes gives `SUBMISSION_DATA_EXPOSED`;
    the tar safety cases of 9.16 (absolute path, `..`, link, duplicate name, oversize member) refuse. Rev. 4 additions:
    a no-consent tar holds the redacted reports only and no sentinel target (15.5 item 1); the public entry draft holds
    hashes, DOI, licence and counts only; a re-saved copy of a shared file matches by content hash; import fails with
    `SHARED_INDEX_MISSING` without the durable index (15.5 items 4 and 5); `share-verify` says `research unverified`
    for relayed research values (15.3 item 8).
11. `test_lpbf_sealed_submission.py` and `test_lpbf_submission_plausibility.py` (revision 3, Part S): commitment schema closed
    and `commitmentId` recomputed; no target value, flag or micrograph in a commitment (sentinel scan); every refusal of
    14.4.4 at its stage; the state machine table-driven: every allowed transition succeeds and every other command
    gives `SUBMISSION_STATE`, with `score` before `tier-decided`, `freeze` before `amended` and `receive-targets` before
    `published` among them; `TARGETS_HASH_MISMATCH` records `release-refused` and leaves the state at `published`; a
    release dated not later than the publication time gives `void-early-release`; changed inputs in a release are
    refused and scoring uses the committed bytes; `PREDICTIONS_ALTERED`, `PREDICTIONS_INPUTS_MISMATCH` and
    `PREDICTIONS_DUPLICATE`; the user's local score equals the maintainer's result byte for byte; a synthetic runner
    verdict that differs from the app's recomputation gives `SEALED_SCORER_DISAGREEMENT`; the confidential variant
    publishes hashes only (scan of every public file for sentinel inputs and targets); `sealed-submissions-v1.json`
    holds no per-condition value (sentinel scan); a tier Declared block is `descriptive-not-scored` with its reason;
    G3o eligibility follows 14.4.6 item 6 case by case. Tiers: requirements per tier, `TIER_REVIEWER_NOT_APPROVED`,
    `TIER_REQUIREMENT_MISSING`, append-only history, a promotion after scoring leaves `g3oBlock` false, a demotion of a
    scored G3o block marks `tier-revoked`, the spot-check sample is the same for the same hashes. Plausibility: each
    flag fires on its synthetic case and stays silent on a clean synthetic set; flags never refuse (the commitment,
    import and score still succeed); flag output carries keys, never values; rounded values give the label, not a
    flag; the known-set check runs over every registry entry with a depth loader and flags a synthetic copy of a spent
    set without printing a value. Rev. 4 additions: registration is fixed at import and never changes; a registered
    block withdrawn after predictions, expired, released early or ended by `void-run-failed` is recorded as not passed;
    `lossCount` above 0 blocks registration; a Zenodo `created` time equal to the predictions merge second gives
    `void-early-release`; an email release never registers; `SEALED_LOCAL_TEST_OVERLAP` on a tuple of a revealed local
    test or a Build Job; the blinded spot check hides the claimed depths until the reviewer's values are recorded; only
    the three integrity findings remove a registered block, and the removal record still prints the score;
    `milestoneStatement` stays null for one block and for two blocks from one lab; identity and attribution never appear
    in plain form in `.lpbf-jobs` (identity sentinel); the sealed runner mode predicts with the target file absent and
    refuses when it is present (15.2).
12. Labels (Part P for protocol 1 documents and the descriptive record, Part S for shared and sealed records): every
    predicted and measured value in reports, shared and sealed records and the descriptive
    record carries `sourceEvidenceKind` and `sourceLocator`; user values carry `Measured (user-supplied)` and never a bare
    `Measured` (R19); served values carry `Unresolved` with `SERVED_VALUE_KIND_NOT_PROVIDED` and its text (HUB-LP-18);
    every locator points to a tracked file (HUB-LP-14); the research rule on synthetic leaves (all sourced gives `Literature estimate`,
    one user input gives `User input` naming it, one unsourced default gives `Unresolved` naming it, both give
    `Unresolved`, a user input equal to its sourced default keeps the sourced label) is copied, never recomputed; the
    document `evidenceKind` stays `screening-only` in every scope.
13. No network (revision 3, Part S): every share, sealed and relay test runs under the NoNetwork socket patch; the CLIs
    `lpbf_sealed.py` and `lpbf_user_blind.py` open no socket in any subcommand.

### 11.2 TypeScript

1. `tests/lpbf-user-blind.test.ts`: validators reject `experimentalValidation` true, missing and `"false"`;
   `appValidation` true; `labelPromotionProposed` other than `none`; wrong `evidenceKind` or `dataLabel`; unknown status
   words and keys; any prediction-like key in preview, receipt, list, get or any queued-type result; header check
   helpers for both files incl. aliases, dialects and the example row; template headers equal the protocol record;
   `blindCsvTextCell` prefixes text cells starting with `=`, `+`, `-`, `@`, tab or carriage return and leaves numbers
   (including negative ones) untouched; the client without `crypto.subtle` offers the paste field and marks the
   browser hash check as skipped; store merge drops unknown persisted fields and survives a throwing `localStorage`;
   the store never persists CSV text. Part P additions: the targets header check runs before the browser hash and the
   `Do not open and save this file again` notice is shown (R20); the header separator sniff and unit reading match the
   Python rules on the same fixtures (R20); a `blind-refusal` reply surfaces its code and message and never an
   exception text (R15); the comparison CSV header and preamble equal the pinned list (R21).
2. `tests/lpbf-user-blind-panel.test.tsx` (`renderToStaticMarkup`, fixture titled `Synthetic fixture, not measured
   data`): each step; the parsed inputs screen with a converted unit and the `unit not stated` label (R20); preview with
   best reachable status and acknowledgements; receipt with no depth number; report with served met, research
   `unavailable` with the not-requested reason text, input-fragile and u_m assumed; user values labelled `Measured
   (user-supplied)` and served values `Unresolved` with the reason as text (R19, HUB-LP-18); the blindness-status
   sentence for each status (U9); no research opt-in control anywhere (R12(a)); the divergence list rendered; banner and data label exact (after
   Q1); no `/\bvalidated\b/` (or the approved exception, Q2); every input labelled; the `predictionsViewedBeforeFreeze`
   help lists every surface of 4.1; the shared-host warning when `sharedHost` is true; hub tab list includes
   `blind-test`; `DemoUnavailable` in the static demo.
3. `tests/lpbf-spent-descriptive.test.tsx`: validator negatives; empty state; badge; spent chips; quantity caption;
   `unavailable: RESEARCH_NOT_REQUESTED`; `USED_IN_SERVED_DEVELOPMENT` on the NIST AMB2022-03 card; data table
   fallback; `data-source` on numbers; no `validated` or `accuracy`; a
   committed record sanity check (set ids SPENT, counts only); the lab renders the `Suspense` fallback under
   `renderToStaticMarkup` without throwing.
4. `tests/python-runtime.test.ts` additions: `WSLENV` carries `METALLIKSA_USER_BLIND_ROOT/p`, `METALLIKSA_READ_ONLY`,
   `METALLIKSA_HOST`, `METALLIKSA_USER_BLIND_SINGLE_USER` and `LPBF_MACHINE_CALIBRATION_DIR/p` when set, keeps
   `METALLIKSA_JOB_ROOT/p`, forwards every other variable when `METALLIKSA_JOB_ROOT` is unset (R16), does not mutate the
   input env, and refuses a UNC blind root loudly.
5. Guards unchanged and green: `tests/route-authority.test.ts`, `tests/component-reachability.test.ts`,
   `tests/module-views.test.ts`, `tests/module-registry.test.ts`, `tests/lpbf-dataset-comparison-lab.test.tsx`,
   `tests/a11y-form-labels.test.ts`, `tests/a11y-static.test.ts`, `tests/workspaces-registry-parity.test.ts`,
   `npm run lint`, `npm run test:unit`, `npm run check:bundle`, `scripts/check_ceiling_review.py`.
6. Real browser (RULES.md 14): keyboard-only run with synthetic files on a local dev server and worker: refusal of an
   inputs file with a depth column and of one with the example row, preview and acknowledgements, freeze and receipt
   download, list and load by freeze key after clearing storage (with a Build Job running), reveal dialog, score,
   re-score with changed targets, exports, print view, an `m/s` header converted on the parsed inputs screen, a
   semicolon file under the comma format, the plan-panel template notice (R20, R21); descriptive panel set selector, axis toggle, details fallback;
   light and dark themes; hidden-tab polling pause; the same hub opened through a LAN address (no secure context)
   showing the paste field, the skipped-hash note and the shared-host warning.
7. `tests/lpbf-sealed.test.ts` and `tests/lpbf-sealed-panel.test.tsx` (revision 3, Part S): closed checkers for every
   document of 4.8 and 4.9 with the scope literals of 2.1; `extractBlindResearchSubset` keeps only the members of 7.6
   item 4 and throws on an unknown key; the relay never renders, persists or logs a research value (sentinel research
   values absent from the rendered markup, the persisted store snapshot and console calls); share step file list,
   consent and licence rules; sealed panel states, the public-and-permanent notice, identity `public` choices with the
   email private by default, flags shown to the user, tier badges and the fabrication notice; the leaderboard sealed
   table has no rank control, groups by alloy, shows `descriptive only` on Declared rows and the pending, withdrawn,
   expired and void counts.
8. No outbound request (revision 3, Part S): a fetch mock fails the test on any non-same-origin URL from the blind, share,
   sealed and relay modules; the submissions repository and Zenodo links render as text with a copy button.
9. Real browser additions (revision 3, Part S): opt-in research step with progress and Cancel against a local server with the
   research route; share export and download; sealed precheck, commitment export, predictions check and release on
   synthetic files; the same in air-gap mode with identical behaviour.

## 12. Phased plan with acceptance checks

"Opus review" below means the gate rule of section 10: a fresh Opus gate for Opus-authored code, the Opus reviewer
otherwise.

Opus queue and critical path (Part P, ENG-24). One Opus works at a time, in this order: `lpbf_blind_stats` extraction
and golden vectors (may start now, gate verdict "Phases that may start"); the store with lock domain and directory
commits; freeze and score; the façade, enforcer, `BlindRefusal` and submit mapping; the worker branches; then, after
the contract amendment, the research module of Part S. Critical path for Part P: Part P lead check, phase 1 core
(stats, store, freeze, score), phase 2 worker with R16 and R17 in its acceptance, phase 3 UI, phase 4 strengthening.
Phase 5 runs beside phases 2 to 4 once R18 (served-definition owner named by the lead), R23 (8.2 datum), HUB-LP-15 and
HUB-LP-16 are in the text. Phases 6 and 8 are off the Part P path.

### Phase 0, design gate and spikes (Opus; Astra; Haiku)

Work: commit nothing yet; a fresh Opus run gates this spec; Astra signs off the physics list (served-path definition and
parity fixtures, `FWHM_FACTOR` and D4sigma equivalence, `beam.quantity` radius handling, sensitivity arm set, leverage
cuts for 316L, IN718 and IN625, bare plate layer invariance, u_m f defaults for non-Ti64 alloys, the AlSi10Mg as-built
property convention of the served ledger, descriptive quantity mapping, the reasons catalogue sentences with locators,
the divergence list of 7.7); the P8 reconciliation is blocked (gate): it uses the contract at `14e13ea8` and waits
for the P8 owner's reply to the amendment request of OD1, and it belongs to Part S (15.3); Haiku times 48 conditions x 5 served calls (include_process_map
True and False) on the worker child path and reports p50 and p95 (research time per condition comes from the contract's
phase C, not from this spike); Part S sign-offs (plausibility constants, sealed rules) wait for revision 4 and Q12;
Haiku transcribes the spent ledger for NIST, Cunningham, KU Leuven and Totis with the licence fields of 8.1 and without
Bitharas, Opus reviews; a spike adds the dataset-view browser-local op and runs `route-authority` and
`emit-module-registry --check`, then is discarded or kept; maintainer answers Q1 to Q5 (Q2 can wait until phase 6).
Accept: gate record with decisions; the served condition cap of 4.3 from the measured p95 (at most 60 s); Astra
sign-off note for the Part P physics list.

### Phase 1, Python core offline (Opus stats, store, freeze, score; Sonnet served arms, intake, CLI, tests; Haiku vectors and templates)

No research module, relay or adapter in phases 1 to 4 (R12(a)).
Accept: `python -B -m unittest test_lpbf_blind_stats test_lpbf_served_arms test_lpbf_user_blind_inputs
test_lpbf_user_blind_store test_lpbf_user_blind_crash test_lpbf_user_blind` green (counts recorded); golden vectors
equal; served parity exact for four alloys plus IN625 direct; served-closure pin and the executed-closure test green
(R14); research arm fixed at `RESEARCH_NOT_REQUESTED` with its AST check (11.1 item 3); every refusal reaches 422 as a
`BlindRefusal` envelope and the malformed-number sentinel holds at submit (R15); lock domain, directory commits and
attempt numbering under the lock (R17); AST isolation, open audit and NoNetwork green; kill-at-each-step matrix green; `git diff` of
the 36 manifest files and the fingerprint pin empty; CLI end to end on synthetic files deterministic, including the
`show` and `bundle` gate; preview under 300 ms and list and get under 100 ms at the caps; fresh Opus gate.

### Phase 2, worker integration (Opus; Sonnet tests)

Accept: `test_lpbf_worker_dispatch`, `test_lpbf_worker_blind_jobs` and every existing `test_lpbf_worker_*` green,
including the prediction-leak sentinel scan of 11.1 item 7 over `progress.log`, the sqlite `log` and `error` columns and
the `get()` response; `tests/python-runtime.test.ts` green; `git diff routes/ server.ts python/module_registry.py`
empty; route-authority and `emit-module-registry --check` green; manual smoke against a local worker with synthetic
CSVs (estimate preview, list and get, freeze, `GET /api/lpbf/jobs/:id` body scanned for the sentinel predictions,
artifact refusal of `blind-freeze.json` and of a bundle before reveal, score, report fetch, repeat route behaves the
same); WSL env forwarding check: a WSL worker started by Node with `METALLIKSA_READ_ONLY=true` and a custom
`METALLIKSA_USER_BLIND_ROOT` refuses a freeze with `STORE_READ_ONLY` and reports that root in `user-blind-list` (or the
check is recorded as not run on a machine without WSL); kill-mid-freeze recovery through the real worker (cancel and
timeout of a running freeze, then a new freeze succeeds with no manual step and the store reconciles); list and get
latency measured while a Build Job runs, with `.lpbf-jobs` unchanged after 100 polls; R16: under the WSL worker with
`METALLIKSA_JOB_ROOT` unset, `METALLIKSA_READ_ONLY=true` still refuses a freeze, and a synthetic machine-calibration
store under a forwarded `LPBF_MACHINE_CALIBRATION_DIR` is found by the overlap check; R17: the kill matrix on drvfs and
a Windows CLI refused by a store created by the WSL worker (`STORE_LOCK_DOMAIN`); fresh Opus gate.

### Phase 3, Hub UI (Sonnet; Haiku help text, CTA, palette, guide draft)

Accept: lint, `npm run test:unit`, a11y gates at 0 exclusions, reachability and module-view guards unchanged,
`npm run check:bundle` within budgets, research contract tests (with the lifecycle and authority changes of 10.2),
real-browser keyboard run recorded with what was not run, including the secure-context behaviour (paste field, skipped
browser hash note), the shared-host warning through a non-loopback address, the parsed inputs screen, the
do-not-resave notice and the plan-panel notice (R20, R21); Opus review; maintainer sees rendered
wording (Q1 strings pinned after approval).

### Phase 4, strengthening (Sonnet; Opus review)

Work: deterministic bundle (`tarfile`, sorted names, mtime 0, uid and gid 0, mode 0644) and `verify` (re-hash, recompute
`freezeKey`, re-score byte for byte; re-predict only when the identity matches, else `re-prediction skipped: different
predictor`; bootstrap reproducibility stated per numpy version); `user-blind-bundle` job and artifact behind the
reveal-or-score gate; Build Job history check (partial, labelled); published-set overlap labels from the spent ledger
loaders; the calibration-store tuple overlap of 6.4 item 7 (if not already in phase 1; it must land before any push);
plan-panel template button; comparison CSV and print view if not already in phase 3.
Accept: verify reproduces reports byte for byte on synthetic bundles; exposure tests for history, published overlap and
calibration-store overlap; bundle gate tests; browser run of export and verify instructions.

### Phase 5, descriptive panel (Sonnet tool, viewer, tests; Astra mapping and notes; Opus admissions) can run beside phases 2 to 4

Accept: ledger and reasons catalogue reviewed; `lpbf_spent_descriptive.py --check` green locally with machine and
library versions recorded (not in CI, 8.3 item 6), and the structure-and-hash test green in the CI list; record under
150 KB; Python and TSX tests green; existing comparison lab tests unchanged, including under the `Suspense` mount; the
dataset-view legacy note updated; bundle check; browser run in light and dark; agents printed no measured values
(review of logs).

### Phase 6, P8 research arm (Part S; Opus with Astra; Sonnet)

Starts only when all hold: the P8 owner has approved the contract amendment of OD1; the contract's phases B to E have
landed; a fresh Opus gate has passed the rebased relay design of 15.3. No served bump is involved (7.6).
Work: the research module `python/lpbf_blind_research.py` (15.3) and protocol 2 (`lpbf-user-blind-protocol-2`) with the
research arm; band coverage, consistency counts, common subset, sign-flip comparison; the descriptive record's research
curves.
Accept: contract amendment approved (recorded with its commit); served bytes unchanged with a relay running (contract
P-5 and P-6) and the served-closure pin unchanged; protocol 1 freezes keep `RESEARCH_NOT_REQUESTED` (no research value
is ever added after a freeze); the research adapter tests run against the committed contract fixture; fresh Opus gate.

### Phase 7, close-out (Opus; Haiku docs and docker)

Accept: `docs/LPBF_USER_BLIND_TEST.md` reviewed (it states the divergence list, the shared-host rule, the
secure-context limit and the CLI environment rule); inventory rows; docker env; PROOF entry in the P7b format (scope,
checks with exact counts and what was not run, limits, `labels unchanged: experimentalValidation=false, no label
promoted`, Build Job cache invalidation noted); STATUS milestone in Turkish; ci.yml additions prepared for the
maintainer's single Ceiling-Review trailer; one batch push only on the maintainer's word, explicit paths staged.

### Phase 8, sharing with the maintainer (revision 3; Opus share and sealed core, fresh Opus gate; Sonnet CLI, plausibility, UI, leaderboard; Haiku guide and templates; Astra constants)

Blocked until (Rev. 4): a fresh Opus gate passes revision 4 (section 15); for Mode A, R7 to R9 and HUB-LP-12 are in
the text (done in 15.4 to 15.6); for Mode B also Q12 is answered and the G3s pre-registration with the sealed runner
mode (15.1, 15.2, OD2) is gated. Then it runs beside phases 5 and 6; the research parts wait for phase 6.
Work: Mode A (`lpbf_blind_share.py`, `user-blind-share`, share step, `share-verify` and `share-import`, spent ledger
entry kind); Mode B user side (`user-sealed-precheck`, `user-sealed-commit`, `user-sealed-check-predictions`,
`user-sealed-release`, sealed panel); maintainer side (`lpbf_sealed_submission.py`, `lpbf_sealed.py`, sealed rule record,
`sealed-submissions-v1.json`, `approved-reviewers-v1.json`, the maintainer index of 15.5 item 5); the sealed runner mode
of 15.2 in the runner's own repository (Sonnet after the gate); plausibility checks and tiers (14.7 as changed by
15.6); the sealed table with its own loader (15.7, no leaderboard schema change); guide sections (both modes, licences, the fabrication statement, the tiers) and, for the
maintainer to place, a README and pull request template for the submissions repository.
Accept: 11.1 items 10 to 13 and 11.2 items 7 to 9 green with counts; a full synthetic Mode B run on one machine with two
stores (user and maintainer) through every state of 14.4.3, including each refusal of 14.4.4, ending in a leaderboard
row whose public files hold no sentinel value; a synthetic Mode A share verified and imported, then refusing a sealed
submission of the same data; a synthetic sealed block predicted by the sealed runner with only the targets hash known,
scored after release, leaving nothing of the submission in the product repository (15.2); a registered block withdrawn
after predictions recorded as not passed; a spot check run blinded; no PASS or FAIL token in the sealed table; no
socket opened (NoNetwork) and no non-same-origin fetch; G3s runner pins recorded or the path marked not run; OD2 recorded
by the lead; fresh Opus gate. Creating the submissions repository and the Zenodo
community stays with the maintainer; until then the placeholder name stays in the wording table.

## 13. Open questions for the maintainer

1. Q1, wording (Rev. 4, gate recommendation): (a) approve now the protocol 1 core strings of 2.2 (tab name, report
   title, banner, receipt line, the six status sentences, the descriptive badge, which matches roadmap item 2, and the
   "why" prefix) and the blindness-status sentences (U9); (b) approve the refusal messages of 6.1 in bulk, since they
   make no claim; (c) defer the share notice and consent text, the tier badges, the research label, the sealed table
   title and caveat, and the `Measured (user-supplied)` label until revision 4 can show a rendered sheet (15.5 to 15.7).
   Tests pin strings only after approval; until then they sit in the wording table, outside every identity.
2. Q2, research status string versus the guard `/\bvalidated\b/i` (Rev. 4, restated with the contract's strings): the
   contract at `14e13ea8` puts "Not experimentally validated; research diagnostic/model only." on non-surface leaves
   (locator `docs/research/SPEC_p8_research_arm_2026-10-14.md Amendment 3 C4`) and the B2 falsified-closure status on
   surface-dependent values. Proposal: an exact-string exception in the guard of
   `tests/lpbf-dataset-comparison-lab.test.tsx` and the hub tests for exactly these strings, rendered verbatim from the
   response. Needed before phase 6 only.
3. Q3, spending Zhao: GOAL item 2 names NIST, Cunningham, KU Leuven and Totis. Admitting Zhao (EXPOSED today) spends it;
   approve a separate ledger commit, or leave Zhao out. Gan Data 1 Ti64 is included as part of the Cunningham
   experiments (same experiments, flagged); confirm.
4. Q4, other alloys: show scored statuses for 316L, IN718 and IN625 with `thresholds reused unchanged` (proposal), or keep
   those alloys descriptive only because the thresholds were registered for Ti-6Al-4V and AlSi10Mg.
5. Q5, digitized AAAS figure data (Cunningham, Zhao): show per point in the app (proposal, with the digitization note and
   read uncertainty), or show group summaries only.
6. Q6, Mode B candidate arm (Rev. 4): gate recommendation accepted as the working default: the MELT candidate through the
   pinned runner in sealed mode (15.2), with the served Build Job arm and the research arm scored beside it, on three
   conditions: R1 lands first, the candidate row is labelled `not the model this app serves`, and the objective name
   follows Q12. Alternative: the served Build Job arm as the candidate, written into the G3s pre-registration.
7. Q7, which sealed blocks count (Rev. 4): Ti-6Al-4V and AlSi10Mg only, with all of: a public block, an open licence (CC
   BY 4.0 or CC0 1.0), a Zenodo release, registration fixed at import, a bound identity, and zero declared losses
   (SD2 withdrawn; a block with losses is descriptive only, decided by the pre-registration rule, not by Astra alone).
   The objective is G3s, not G3o (Q12).
8. Q8, release window and withdrawal (Rev. 4): 180 days from `published`; a registered block that ends unreleased or
   withdrawn after predictions counts as not passed (R3), not only listed; a withdrawal before predictions may be
   replaced by a hashes-only file; a `submitted` commitment not imported or refused within 30 days is listed as
   `stale-submitted`.
9. Q9, labels: accept served `Unresolved` with the reason shown as text; confirm that P, v, d and T0 never make a research
   output `User input`, answered once in GOAL as P8 item I-1 and cited from both specs.
10. Q10, licence and identity (Rev. 4, gate recommendation as the working default): keep CC BY 4.0 (default), CC0 1.0 and
    none, with none only for Mode A and confidential Mode B; Evidenced needs an ORCID bound by a checkable channel
    (Zenodo deposit under that ORCID, the ORCID record listing the DOI, or a linked GitHub account), format and checksum
    alone are not enough; lab and machine are public for counting blocks; the institutional email is never published,
    not even as a hash (15.6).
11. Q11, plausibility constants: accept the proposed values (`ASPECT_MAX` 6, scatter floor 0.5 %, digit test at
    p < 0.001 with at least 50 values, known-set match within max(1 um, 1 %), spot check of min(5, n) sections within
    2 u_m or 5 %), freeze them in the sealed protocol record before the first real submission, Astra signs the
    physical ones, and run the known-set check only on sets with a depth loader.
12. Q12 (new), objective name for sealed submissions: MELT Amendment 6 item 14.3 bars the sealed rules from riding on
    G3o. Recommendation: a successor objective, working name G3s, with a fresh pre-registration that copies the G3o
    thresholds unchanged and adds R1 and R3 to R6, the MELT 9.4 clauses and the release obligation (15.1). Alternative:
    an Astra and fresh Opus ruling that SD1 is not a loosening (recommended against). This refines GOAL decision 5's
    wording "route to G3o".
13. Q13 (new): should a Mode A set with `publishAllowed` true ever enter the committed descriptive record with its
    points? Recommendation: no; link the DOI and show counts only, or amend decision 5 explicitly.
14. Q14 (new): public identity fields (submitter ORCID, reviewer ids) go beyond decision 5's "results, hashes, DOIs".
    Recommendation: ORCID and lab or machine only for counting blocks, with consent; a reviewer is listed only with the
    reviewer's consent.
15. Q15 (new): does "Measured for transcribed measurements" cover user-supplied values? Recommendation: `Measured
    (user-supplied)` with the tier beside it, never a bare `Measured` (applied in Part P, 14.6 and 7.5).
16. Q16 (new): should the findings note be published at all? Recommendation: keep it internal; publish a cleaned version
    only on the maintainer's word. The note left this branch (R22, `ba7dc030`); nothing in this spec depends on it.

Q1 also covers the revision 3 and 4 strings listed in 15.9; 15.9 lists every point of Part S that waits for an answer.

Open dependencies (not maintainer questions):

1. OD1, contract amendment request to the P8 owner (R12(a); the lead sends it). The contract at `14e13ea8` lets only the
   Research model panel send research requests (1.1) and forbids any worker job or internal caller to receive values
   from the route (1.5). The request asks for three changes: (a) new senders: the blind tab's explicit opt-in step and
   the maintainer's explicit batch client `scripts/research-route-batch.ts`, using the same route, lane, request schema
   and cache; (b) an exception to 1.5 for a hash-bound relay: research values received by the browser or the batch
   client and passed, unrendered, into a blind freeze, where they are bound by hash and declared client-asserted
   (15.3); (c) rendering outside the panel: research values, labels and captions shown in the blind report and the
   descriptive panel, with the labels taken from the response, under the contract's label rule 3 (7.1) and display
   rules (4.7). Until the P8 owner approves, protocol 1 keeps the research arm at `RESEARCH_NOT_REQUESTED` (7.6), and
   phase 6 does not start.
2. OD2, G3s pre-registration by the lead (Rev. 4, after Q12): the successor objective of 15.1 with SD1, zero declared
   losses, registration at import, the MELT 9.4 clauses, the closed integrity list, the conflict-of-interest
   declaration, the release obligation and the sealed runner mode of 15.2 (a runner change with its own pins), written
   and gated by a fresh Opus run before any submitted target is read and before any phase 8 code.

Maintainer actions (not questions): the Ceiling-Review trailer for `.github/workflows/ci.yml` at the batch push; the push
itself; creating the submissions repository and the Zenodo community (14.5); approving reviewers (14.7.4).

## 14. Revision 3: sharing with the maintainer and label decisions (2026-10-15)

Source: the maintainer decisions in `.orchestra/GOAL.md` (main checkout, gitignored lead file), section "Label and data
decisions (maintainer, 2026-10-15)", items 1 to 5, and the maintainer's answer of the same day on anti-fabrication trust
tiers ("Olur"). This section holds the design; the affected sections carry the integrated changes and point here
(Appendix A.5 lists them). Section 7.6 is rewritten against the P8 integration contract in the same revision. Nothing
here is implemented; the revision goes to the design gate with the rest of the spec. Revision 4 (section 15) changes
parts of this section after the gate of 2026-10-15; each changed statement carries "[Rev. 4: see 15.x]" and is listed
in 15.10, and where the two differ, section 15 applies.

### 14.1 Decisions and fixed principles

1. Processing stays on the user's machine. A local blind test (protocol 1, sections 3 to 7) runs in the user's own blind
   store, separate from the calibration stores. The maintainer has no account, remote access, telemetry or job path into
   a user's app and never processes raw data inside it. The maintainer's tools (14.3, 14.4) run on the maintainer's own
   machine, on files the user chose to send, in stores separate from the maintainer's own blind store.
2. Two sharing modes, both started by the user, both producing files only: Mode A "share my result" (14.3) and Mode B
   "sealed submission" (14.4, preferred).
3. The app uploads nothing. No mode makes an outbound request: no GitHub, Zenodo or mail API, no SMTP, no prefetch of a
   link. The app writes files and shows instructions; links to the submissions repository and to Zenodo are shown as
   text with a copy button. Behaviour is identical with `AIRGAPPED=1`; `server/airgap.ts` needs no change, because
   there is no outbound call to block (`AIRGAP_BLOCKED_SERVICES` stays as it is).
4. [Rev. 4: see 15.5 item 4 and 15.6 item 2] The main repository stores results, hashes, DOIs and the identity fields a
   submitter chose to make public (14.7.1),
   never inputs, targets, metadata text, micrographs or predictions of a submission. Commitments and predictions files
   live in the separate public submissions repository; data files on Zenodo or, for confidential labs, in private email
   (14.5).
5. Roles. The user is the data owner and, in Mode B, the custodian of MELT section 6 item 7 and of MELT Amendment 6 item
   12: only the user holds the targets and the evidence files until the predictions are published. The maintainer is
   the predictor and scorer of Mode B. Anyone can recheck a published result from the published files (14.4.8).
6. Labels (decision items 1 and 2): 14.6.
7. Fabrication, stated plainly. The model and its source code are public, so anyone can compute its predictions for any
   inputs, and a sealed submission alone cannot prevent measurements fabricated to match the model: a commitment proves
   only that the targets were fixed before the maintainer published predictions, not that they are real. The
   mitigation is the trust tiers with raw evidence, identity, plausibility flags and review (14.7), and the
   two-independent-campaign rule: no milestone statement rests on one submitter's data (14.4.7) [Rev. 4: see 15.1 items
   2f to 2i and 15.7 item 1].

### 14.2 The three paths compared

| | Local test (protocol 1) | Mode A, share my result | Mode B, sealed submission |
|---|---|---|---|
| Who predicts | user's app | user's app | maintainer's app |
| Targets fixed before predictions by | local order, optional commitment and anchor | as in the local test | public commitment of the targets SHA-256 before predictions are published |
| Maintainer sees the targets | never | when the user consents to include them | only after the predictions are published |
| Counts as | the user's own test | a result the maintainer has seen; never an app blind test | [Rev. 4: see 15.1] a block of the successor objective G3s when registered at import [Q12]; never a G3o block |
| Leaves the machine as | nothing | a share bundle the user sends | a commitment file, later a release folder, both sent by the user |
| Enters | nothing | spent ledger as `EXPOSED` (14.3.5) | `data/benchmark/sealed-submissions-v1.json` and the leaderboard (14.4.9) |

### 14.3 Mode A: share my result

14.3.1 Export (user's app). Precondition: the freeze has at least one score (`SHARE_NO_SCORE` otherwise). Queued job
`user-blind-share` (3.2.1) or CLI `share`. The dialog lists every file that will be written and what it holds, asks for
consent per part and for a licence, then writes `freezes/<freezeKey>/shares/share-<n>.tar` (the deterministic tar of
phase 4: sorted names, mtime 0, uid and gid 0, mode 0644), served as `blind-share.tar`. Contents (schemas in 4.8):

1. `share-manifest.json`, `metadata.json` (canonical) and `inputs.csv` (raw bytes; sha256 equal to the freeze
   `inputsSha256`);
2. `freeze.json`, every `reveal-*.json` and every `score-*.json` with their sidecars: every attempt, so a favourable
   attempt cannot be shared alone;
3. `ledger-excerpt.jsonl` (14.3.2) and `research-requests.json` (the research request bodies of 4.5 item 1, inputs
   only);
4. `targets-<n>.csv` for every attempt, only with `consent.includeTargets: true`; [Rev. 4: see 15.5 items 1 to 3:
   without consent the reports are redacted, because the full reports carry measured values];
5. `evidence-manifest.json` when the user lists evidence files (14.7.1); the image files travel beside the tar, never
   inside the store;
6. `README.txt`: contents, licence, the verify command, and the sentence that the maintainer will count the data as
   seen.

14.3.2 Ledger excerpt: every ledger line that names this freeze key, in full, plus a redacted link `{seq, prevEntryHash,
entryHash}` for every line of other tests between them, so the chain verifies without disclosing other tests.

14.3.3 Licence and publication. `licence`: `CC-BY-4.0` (proposed default), `CC0-1.0`, or `none` (no public licence: the
maintainer may read and score the data for this record only). `publishAllowed: true` needs `CC-BY-4.0` or `CC0-1.0`
and lets the maintainer list the result and its DOI publicly; `none` forces `publishAllowed: false`. `CC-BY-4.0` needs
`attribution` (a name or pseudonym, 1 to 120 characters, the `blockLabel` character rule), else
`SHARE_ATTRIBUTION_REQUIRED`. The user deposits the tar on Zenodo or sends it by email (14.5).

14.3.4 Maintainer import. `python/tools/lpbf_user_blind.py share-verify <tar>` is offline, writes nothing and prints
check results, hashes and counts only; `share-import <tar>` runs the same checks, then writes under
`METALLIKSA_SHARED_ROOT` (default `<repo>/.runtime/shared-results/<shareId>/`), never into the maintainer's own blind
store. The tar is read member by member from a closed name set (9.16); nothing is extracted to a path taken from the
archive. Checks, each with an id in the output:

1. every member's sha256 and size equal the manifest, and no member lies outside it;
2. `freeze.json` recomputes `freezeKey`, matches its sidecar, has `targetColumnsRead: false` and a recomputed
   `predictionsSha256`;
3. chain: the excerpt verifies link by link; the `frozen` event of this freeze precedes, by sequence, every event that
   names a targets hash (`score-refused`, `commitment-mismatch`, `scored`) and every `revealed` event; the receipt's
   `ledgerEntryHash` is that `frozen` entry;
4. commitment: when the frozen metadata holds `targetCommitment`, the shared targets file of the matched attempt hashes
   to it, so the targets were fixed no later than the freeze;
5. re-score: with targets, every report is recomputed byte for byte when the scorer identity matches, else `re-score
   skipped: different scorer` with both identities; without targets, `targets withheld: statistics not reproducible by
   the recipient` [Rev. 4: true only with the redacted report of 15.5 item 1];
6. re-predict: served arms are recomputed when the predictor identity equals the maintainer's live pinned build, else
   `re-prediction skipped: different predictor`;
7. research: when the frozen research identity equals the maintainer's research pin, the maintainer reruns the recorded
   requests through the research route on an explicit command (`scripts/research-route-batch.ts`, 7.6 item 2) and
   compares the frozen subsets by parsed value: `research reproduced`, `research not reproduced (<k> conditions)` or
   `skipped: different research identity`;
8. anchors: an external anchor of `freezeSha256` (a commit or issue in the submissions repository, a Zenodo record) is
   recorded with its URL and server time as typed by the maintainer; the tool cannot fetch it.

What the import proves: the frozen predictions are unchanged since their `frozen` ledger entry, and the user's ledger
records them before any targets hash. What it cannot prove: wall-clock order against a person who rewrote the whole
store and ledger consistently. Only an external anchor of `freezeSha256` made before the targets existed proves order
to a third party; the import record says which case applies (`order: local-ledger-only` or `order: anchored <time>`).

14.3.5 Effects [Rev. 4: see 15.5 items 4 to 6: the public entry holds hashes, DOI, licence and counts only; the index is
durable and outside `.runtime`]. A Mode A set is seen by the maintainer. It never counts as an app blind test (`appBlindTest: false`,
every `neverEnters` member true), whatever its local status was. Import appends its condition tuples to the local index
`shared-results/index/seen-tuples.jsonl` and, in a maintainer commit, adds a spent ledger entry of kind
`shared-result` with status `EXPOSED`, targets shared or not, because the statistics are outcome information:
`{datasetId "shared-<first 12 hex of shareId>", kind, alloy, nConditions, inputsSha256, targetsSha256 [],
shareManifestSha256, doi or null, licence, publishAllowed, importedAt, tier}`. Condition tuples enter that public entry
only with `publishAllowed: true`; otherwise they stay in the maintainer's local index. A later test on the maintainer's
machine, or a Mode B submission, whose hashes or tuples match is not blind (6.4 item 5) or refused
(`SUBMISSION_DATA_EXPOSED`). A Mode A result appears in no leaderboard table; with `publishAllowed: true` the guide may
list it under "Shared results, seen by the maintainer", its statistics labelled as the user's own test. The descriptive
panel (section 8) admits a shared set only through a separate maintainer-approved ledger commit, like Zhao (Q3).

### 14.4 Mode B: sealed submission

14.4.1 Order [Rev. 4: see 15.1 and 15.2]. The user commits in public (inputs, metadata, evidence manifest, SHA-256 of the targets file); the
maintainer imports, writes the run amendment, freezes and publishes predictions with the served and research
identities; the user releases the targets and evidence files; the maintainer checks hash and timing, runs the intake
checks, records the pre-score tier, scores once and records the result.

14.4.2 Files and hashes (schemas in 4.9). Canonical JSON everywhere: UTF-8, LF, `json.dumps(obj, sort_keys=True,
separators=(",", ":"), ensure_ascii=True)`, floats as Python `repr`. Hashes are lower-case hex SHA-256 over the exact
bytes; TypeScript never re-serializes a hashed document.

| File | Written by | Where | Hashes |
|---|---|---|---|
| `commitment.json` | user's app (`user-sealed-commit`, CLI `commit`) | submissions repository `submissions/<commitmentId>/` (the public variant only for a confidential lab, 14.4.5) | `commitmentId` = sha256 of the canonical commitment without `commitmentId`; `inputsSha256` (raw bytes), `metadataSha256`, `targetsSha256` (raw bytes of the targets file: the value `sha256sum` and `certutil -hashfile <file> SHA256` print), `evidenceManifestSha256`, `sealedProtocolSha256` |
| `run-amendment.json` | maintainer (`lpbf_sealed.py run-amendment`) | submissions repository, before predictions | `runAmendmentSha256`; the closed key set of MELT Amendment 6 item 14.4 |
| `predictions.json` | maintainer (`freeze`) | submissions repository | `predictionsSha256` (file bytes, sidecar); names `commitmentId`, `inputsSha256`, `targetsSha256`, `runAmendmentSha256`, the served identity, the research identity and the MELT runner pins |
| `publication.json` | maintainer (`publish`) | sealed store; copied into the result | URL and GitHub server time of the merge that published `predictions.json`, sha256 of the published bytes |
| `release.json` | user's app (`user-sealed-release`, CLI `release`) | inside the Zenodo deposit or the email | sha256 of every released file: targets (equal to `targetsSha256`), inputs, metadata, commitment, predictions, evidence files |
| `release-<n>.json` | maintainer (`receive-targets`) | sealed store | one per release attempt: source (DOI and Zenodo publication date, or email and the maintainer's receipt time), hashes, accepted or refused with its code |
| `intake.json` | maintainer (`intake`) | sealed store; summary in the result | plausibility flags (14.7.2), evidence re-hashes, identity completeness |
| `tier.json` | maintainer or approved reviewer (`tier`) | sealed store, mirrored in the result record | append-only tier events (14.7.4) |
| `result.json` | maintainer (`score`) | sealed store; entry in `data/benchmark/sealed-submissions-v1.json` | `resultSha256`; statistics, statuses, identities, anchors, tier at score |

14.4.3 State machine [Rev. 4: see 15.1 item 2d (registration at import; not passed when unreleased or withdrawn after
predictions) and 15.4 items 1 to 3]. The maintainer's sealed store holds the reference state; ledger events are in brackets and follow
their commit points as in 3.5. The user's store mirrors the user-side states.

| State | Entered when | Next |
|---|---|---|
| `committed` | the user's app writes `commitment.json` [user ledger `commitment-exported`] | `submitted`, `withdrawn` |
| `submitted` | the user opens a pull request or issue with the commitment in the submissions repository, outside the app; GitHub server time of creation | `imported`, `refused-at-import`, `withdrawn` |
| `imported` | `import` passes every check of 14.4.4 [`imported`, with the submission anchor typed by the maintainer] | `amended`, `withdrawn` |
| `amended` | `run-amendment.json` is written and committed to the submissions repository [`amended`] | `frozen`, `withdrawn` |
| `frozen` | `predictions.json` is written exclusive [`frozen`] | `published` |
| `published` | the merge that adds the exact `predictions.json` bytes to the submissions repository is recorded with its server time [`published`] | `released`, `expired-unreleased`, `withdrawn-after-predictions` |
| `released` | a release attempt is accepted: the targets bytes hash to `targetsSha256` and the release time is later than the publication time [`targets-received`] | `intake-checked`, `void-targets-invalid` |
| `intake-checked` | plausibility flags and evidence re-hashes are written [`intake-checked`] | `tier-decided` |
| `tier-decided` | the pre-score tier is recorded; Declared is a valid decision [`tier-decided`] | `scored` |
| `scored` | the one declared run writes `result.json` [`scored`] | `recorded` |
| `recorded` | the maintainer commits the result entry to the main repository | terminal; tier events stay possible (14.7.4) |

Terminal states without a sealed score: `refused-at-import` (with its code), `withdrawn` (before predictions; nothing
more is published), `withdrawn-after-predictions`, `expired-unreleased` (no accepted release within the release window,
proposal 180 days after `published`, Q8), `void-early-release`, `void-targets-invalid`. Every terminal state is listed
in the results record and counted on the leaderboard (14.4.9), so a withheld or withdrawn block stays visible.

Ordering rules enforced by the tools: a command used out of order refuses with `SUBMISSION_STATE` (for example `score`
before `tier-decided`, `freeze` before `amended`, `receive-targets` before `published`); exactly one `predictions.json`
per commitment (`PREDICTIONS_DUPLICATE`); one declared run (a crash is recorded; a rerun is allowed only with identical
inputs, code and store, and must reproduce the bytes).

14.4.4 Refusal cases [Rev. 4: see 15.4 items 4 to 7 and 6.1].

| Case | Where | Code | Effect |
|---|---|---|---|
| commitment id does not recompute, unknown key, unknown schema or sealed protocol | `import` | `SUBMISSION_SCHEMA`, `SUBMISSION_ID_MISMATCH`, `SUBMISSION_PROTOCOL_UNKNOWN` | `refused-at-import`; the user may submit a corrected commitment (new id) |
| the embedded inputs bytes do not hash to `inputsSha256`, or inputs or metadata break 4.1 or 4.2 | `import` | `SUBMISSION_INPUTS_CHANGED`, the 6.1 code | `refused-at-import` |
| the data was published, used for machine calibration, or its predictions were viewed (declarations and the 6.4 item 7 tuple check), or its hashes or tuples match an `EXPOSED` or `SPENT` entry | user's app at commit, again at `import` | `SEALED_DATA_PUBLISHED`, `SEALED_CALIBRATION_OVERLAP`, `SEALED_PREDICTIONS_VIEWED`, `SUBMISSION_DATA_EXPOSED` | no commitment, or `refused-at-import` |
| changed inputs later: a release carries inputs that differ from the committed bytes | `receive-targets` | `SUBMISSION_INPUTS_CHANGED` | attempt refused; state stays `published`; scoring always uses the committed inputs |
| hash mismatch: the released targets file does not hash to `targetsSha256` | user's app at release, again at `receive-targets` | `TARGETS_HASH_MISMATCH` | attempt refused and recorded; state stays `published`; only the committed bytes can ever be scored; no continue path (unlike protocol 1 `acceptCommitmentMismatch`) |
| published predictions differ from the frozen file, or name other inputs | `publish`; user's app at `user-sealed-check-predictions` | `PREDICTIONS_ALTERED`, `PREDICTIONS_INPUTS_MISMATCH` | state stays `frozen`; the user's app tells the user not to release targets |
| targets released before predictions were published: the Zenodo publication date or email receipt is not later than the publication server time, or a public copy of the targets that predates it is shown | `receive-targets`, or a later report | `TARGETS_RELEASED_EARLY` | terminal `void-early-release`; the targets are spent; the maintainer may score them descriptively, recorded `EXPOSED` like Mode A |
| the user asks for a release package before the published predictions file was checked | user's app | `PREDICTIONS_NOT_PUBLISHED` | nothing written |
| the committed targets file breaks 4.4 (keys, statuses, ranges) | `receive-targets`; unreachable when the user's precheck ran | the 4.4 code | terminal `void-targets-invalid` |
| released evidence files do not hash to the evidence manifest | `intake` | `EVIDENCE_HASH_MISMATCH` | not a score refusal: the files are listed and cannot support a tier above Declared |

14.4.5 Confidential variant [Rev. 4: never registered and never counts, 15.4 item 5]. For a lab that cannot publish inputs: the public `commitment-public.json` holds
`commitmentId`, `inputsSha256`, `metadataSha256`, `targetsSha256`, `evidenceManifestSha256`, `sealedProtocolSha256`,
alloy, condition count, licence `none` and the public identity fields; the full commitment goes by private email. The
maintainer publishes `predictions-public.json` (`predictionsSha256` and identities only) and emails `predictions.json`;
targets and evidence go by email. The result record holds statistics and statuses only, no per-condition values,
labelled `confidential sealed test: third parties cannot re-score it`. Proposal: confidential blocks are listed but do
not count toward G3o, which is an open-data objective (Q7).

14.4.6 Scoring under the sealed protocol (`lpbf-sealed-protocol-1`) [Rev. 4: see 15.1 and 15.2: the objective is G3s,
not G3o; SD2 is withdrawn; the runner runs in sealed mode]. The rule record
`data/blind/lpbf-sealed-protocol-v1.json` (generated by `python/tools/lpbf_sealed.py export-protocol [--check]`) holds
the MELT G3o rule set of MELT Amendment 6 (thresholds, input metrology grades, power and beam arms, resolution qualifier
with `cv_pool` and the `u_m` default, leverage, input-fragile and property-fragile wording, cavity physics statement,
licence sentence) with the Amendment 6 text and JSON sha256 pins of its item 14.2, the sealed departures below, the
plausibility constants (14.7.2), the tier definitions (14.7.3), the state table, the refusal codes and the file schemas.
Its sha256 is `sealedProtocolSha256`. The commitment carries it, so the user commits to the rules as well as to the
targets, and `import` refuses another value (`SUBMISSION_PROTOCOL_UNKNOWN`). A released sealed protocol is immutable.

1. The G3o verdict comes from the pinned MELT runner (`python/tools/run_lpbf_melt_depth.py` at the pinned
   `research/ti64-primary` commit, the only G3o authority), run once on the maintainer's machine against the block's
   run amendment, with the user as custodian. Candidate arm per MELT Amendment 2 item 4 (S1, or S2 with a P3 primary
   block PASS on record) (Q6).
2. The app arms of 7.1 (`served` Build Job path and its four sensitivity arms, `research:melt-link`, `research:cavity`
   descriptive, `context:fabbro`) are frozen in the same `predictions.json` and scored with `lpbf_blind_stats` under the
   same rule table; the report shows them beside the candidate, labelled `same rules, not the registered candidate`.
   The app also recomputes the candidate's statistics from the predictions file with the extracted functions; a
   difference from the runner's numbers blocks the result (`SEALED_SCORER_DISAGREEMENT`, an integration defect).
3. Blindness: `blind-sealed` (6.4) when the targets were committed in public before predictions were published by a
   party who never held them, and the declarations hold. Items 1, 5 and 7 of 6.4 apply through the commit-time
   declarations and checks; an early release gives `void-early-release`.
4. Tier: a block whose pre-score tier is Declared is scored with every arm at `descriptive-not-scored`, reason `tier
   Declared: table only, not checked` (7.3 step 2); the statistics are shown.
5. Sealed departures from Amendment 6, declared in the rule record and printed in every sealed report:
   SD1, the data owner is the custodial reader of Amendment 6 item 12, and the inputs header whitelist of 4.2 is the
   whitelist; SD2, measurement losses declared in the committed targets file follow D1 and D11 of 7.7, because they are
   fixed by hash before any prediction exists (whether a block with any declared loss may count toward G3o is Astra's
   ruling, Q7); SD3, alloys other than Ti-6Al-4V and AlSi10Mg are scored as sealed tests outside G3o (the G3o milestones
   are G3o-Ti64 and G3o-AlSi10Mg, Amendment 6 item 1.3).
6. A block counts toward G3o only when all hold: tier Evidenced or above recorded before scoring (14.7.4); a public, not
   confidential, block; Ti-6Al-4V or AlSi10Mg; a committed run amendment; a MELT runner run that did not refuse; SD2
   cleared by Astra. Otherwise it is listed as an independent sealed test with `g3oBlock: false` and the reason.

14.4.7 Claims [Rev. 4: see 15.1 items 2f and 2g, and 15.7 item 1]. A sealed block licenses at most the MELT Amendment 6 item 13 sentence for that block (a G3o block) or a
block sentence of the same form without the G3o name (another sealed test). It never claims G3, N3, a raised evidence
ceiling, a served change or a label promotion (`labelPromotionProposed: "none"`; a ceiling proposal after a G3o PASS is
a separate maintainer decision with its own gate). Two-independent-campaign rule (GOAL kill criterion 6, applied to
submitted data): a milestone statement built on submitted data needs at least two sealed blocks at Evidenced or above
from independent labs (different lab and machine, no shared submitter identity), each judged alone and never pooled.
Writing this rule into the MELT pre-registration is a lead amendment before any submitted target is read (open
dependency OD2, section 13).

14.4.8 Rechecking by anyone. `python/tools/lpbf_sealed.py verify` (offline) takes the commitment, the predictions file
and the release folder (and optionally the result): it re-hashes every file, recomputes `commitmentId`, checks that
`predictions.json` names the commitment, the committed inputs and the run amendment, recomputes every statistic from
the predictions file and the released targets with `lpbf_blind_stats` under the sealed rule record and compares with
`result.json` byte for byte (bootstrap reproducibility stated per numpy version), and prints the anchors and times as
recorded, which the reader checks on GitHub and Zenodo. Re-prediction needs the pinned commits and is optional. The
user's app runs the same computation at release (`sealed-score-local.json`), so the user can compare it with the
maintainer's record.

14.4.9 Leaderboard [Rev. 4: see 15.7: separate record, no leaderboard schema change, new title and caveat]. `data/benchmark/sealed-submissions-v1.json` (schema `lpbf-sealed-submissions-1`, committed by the
maintainer with explicit paths) holds one entry per commitment in every state from `imported` on: `commitmentId`,
state, anchors (submission URL and server time, predictions merge URL and server time, release DOI and publication date
or `email, received <date> (maintainer record)`), every hash of 14.4.2, identities (served fingerprint, served-closure
pin, research implementation sha256 and schema, MELT runner commit and Amendment 6 pins), alloy, condition count,
grades, tier at score with the current tier and its history, flag counts by code, statuses per arm, statistics,
qualifiers, labels, `g3oBlock` with its reason, the licence sentence for a G3o block that met all thresholds and
qualifiers, the public identity fields, and the honesty block of 2.1 for the sealed scope. It holds no per-condition
input, target or prediction: for public blocks those stay on Zenodo and in the submissions repository, and the record
carries their hashes and the DOI. `python/tools/lpbf_benchmark_score.py builtin` copies the record into a new member
`sealedTests` of the leaderboard record (schema `lpbf-leaderboard-2`; `--check` compares structure and hashes only,
because the targets are not in the repository and no command uses the network). The Calibration Scorecard page shows a
separate table `Independent sealed blind tests` after the screening tables: one row per block, grouped by alloy, never
ranked, never pooled with other blocks or with the screening benchmark, with the tier badge, `descriptive only` on
Declared rows, and a line per alloy counting pending, withdrawn, expired and void submissions. A G3o result, PASS, FAIL
or INCONCLUSIVE, also gets a PROOF.md entry, and its targets are spent (GOAL kill criterion 3).

### 14.5 Transport without a server

1. Submissions repository (placeholder name `metalliksa-submissions`, created later by the maintainer; the name sits in
   the wording table, so the real name is a one-file change). Layout: `submissions/<commitmentId>/commitment.json` (or
   `commitment-public.json`), `run-amendment.json`, `predictions.json` (or `predictions-public.json`) and a
   `status.json` the maintainer updates per state. The times that count are GitHub server times (creation of the pull
   request or issue, and the merge made through the GitHub web interface), never git author or committer dates, which
   a client sets freely. The pull request template and the README are maintainer tasks (phase 8).
2. [Rev. 4: see 15.4 items 4 and 5: the server-side `created` timestamp decides, and counting blocks need Zenodo]
   Zenodo (DOI, licence, optional Metalliksa community, created later by the maintainer): the user deposits the release
   folder (inputs, metadata, targets, evidence files, commitment, a copy of the predictions, `release.json`). The release
   time is the publication date of the record; a draft or an embargoed file is not a release. A correction is a new
   Zenodo version, and only the version whose targets bytes hash to `targetsSha256` is scored.
3. Private email for confidential labs (14.4.5). The maintainer records the receipt time, and the record says `email`,
   so the weaker timing is visible. [Rev. 4: an email release never counts, 15.4 item 5]
4. Main repository: `data/benchmark/sealed-submissions-v1.json`, `data/benchmark/approved-reviewers-v1.json`, spent
   ledger entries for Mode A sets and voided blocks, the leaderboard record and PROOF entries. Never raw user data.
5. The app's part: per step it writes the files and a plain-text instruction sheet (where to submit, what to deposit,
   which licence was chosen, what happens next), shown in the UI and written beside the files. It calls no network API.

### 14.6 Labels (decision items 1 and 2)

1. Per-value label. Every predicted or measured value in a blind, shared or sealed document and in the descriptive
   record carries `sourceEvidenceKind` with `sourceLocator`. The document-level `evidenceKind: "screening-only"` (2.1)
   stays the module evidence ceiling, and no per-value label raises it. The source vocabulary below is never used in
   the ceiling badge, which always reads `Screening only` (Part P, R19). Locators point to tracked files only
   (HUB-LP-14).

   | Value | `sourceEvidenceKind` | Locator |
   |---|---|---|
   | user measured depth, width, uncertainty | `Measured (user-supplied)`, never a bare `Measured`; in shared and sealed records the tier stands beside it (Part P, R19; Q15) | `{targetsSha256, key}`; after a Zenodo release also the DOI |
   | spent-set value (section 8) | `Measured`, with `transcription` `table` or `digitized-figure` | citation, DOI, table or figure locator |
   | research leaf value | the leaf's own `evidenceKind` under the rule of item 2, copied, never retyped | the source locators of the leaf's input provenance; `weakestInputs` names when not `Literature estimate` |
   | served value | `Unresolved`, reason `SERVED_VALUE_KIND_NOT_PROVIDED`, shown as the text of 2.2, until the served result carries per-value provenance (a served-side change outside this spec, Q9) | served identity |
   | statistics | none: derived comparisons under the screening-only ceiling | report |

2. Research output rule (decision item 2; settles contract M-1): all model inputs sourced defaults gives `Literature
   estimate` with its sources; any user-typed input gives `User input`, naming the inputs; any unsourced default
   (declared assumption, legacy estimate) gives `Unresolved`, naming the inputs; `Unresolved` takes precedence over
   `User input`; a user input left at its sourced default keeps the sourced label. Process conditions (P, v, d, T0,
   wavelength) are request inputs, not model inputs, for this rule (contract 6.2; Q9 asks the maintainer to confirm).
   The blind, sealed and descriptive paths send no `researchOptions`, so `User input` cannot occur there; a response
   that shows a `userInput` provenance refuses the freeze (7.6 item 3).
3. Module ceiling (decision item 1; settles contract M-2): a per-value `Literature estimate` may appear under the
   screening-only ceiling of the legacy `3d-distortion-lab` contract. No value label, Mode A import or sealed result
   raises the ceiling.

### 14.7 Trust tiers, raw evidence and plausibility flags (maintainer decision, 2026-10-15)

14.7.1 Fields. Raw evidence and identity are optional for every submission and required for tiers above Declared.

1. Per-section values: targets with `reduction: per-section-raw` and `section_id` (4.4), so a reviewer can compare
   sections with micrographs.
2. `evidence-manifest.json` (schema `lpbf-submission-evidence-1`): `files [{fileName (4.2 item 10 rule), sha256,
   sizeBytes, mediaType image/png | image/jpeg | image/tiff, kind micrograph | raw-image, key {condition_id, track_id,
   section_id} or null, scaleBar {present bool, length_um number or null}, magnification text or null}]`. The app
   identifies the type from the first bytes, hashes each file in the browser (SubtleCrypto, or the pasted-hash path
   without a secure context, 3.4 item 5) or in the CLI, and lists it; it never uploads, stores, decodes or edits an
   image. Raw images are optional. In Mode B the manifest (names, keys, hashes) is part of the public commitment, so the
   micrographs are fixed before predictions exactly like the targets; the image files are released only with the
   targets, because a micrograph shows the depth. The UI tells the user to remove camera and location metadata before
   hashing, because the app does not alter a file whose hash it records.
3. [Rev. 4: see 15.6 item 2: the email is never published in any form, and Evidenced needs an ORCID bound by a
   checkable channel] Identity (`submitter`): `orcid` (format and checksum checked offline) or `institutionalEmail` (at least one for
   Evidenced), `lab`, `machineModel`, `measurementDate` (ISO date or month), each with a `public` choice.
   `institutionalEmail` is private by default: only its sha256 appears in a public file, and the address goes to the
   maintainer by email. The UI states before export that a Mode B commitment is public and permanent in the submissions
   repository.

14.7.2 Plausibility checks (`python/lpbf_submission_plausibility.py`; constants with sources in the sealed rule record;
Astra signs off the constants in phase 0). They flag and never reject: no check refuses a file, blocks a commitment, an
import or a score, or changes a statistic. Each flag has a code, the keys involved (never a value) and one sentence.

1. Energy bound `FLAG_ENERGY_BOUND`: with width released, `0.5 D W H_min > P / v` for a condition, where `H_min = rho
   (cp (T_solidus - T0) + L_f)` from the lowest sourced values of the served property ledger, with absorptance 1 and no
   conduction loss (the triangle spanned by the depth and the surface width is a lower bound on the area of a convex
   fusion zone). Without width: `energy bound not evaluable`.
2. Monotonicity `FLAG_DEPTH_DECREASES_WITH_POWER`: two conditions with speed and 1/e2 beam within 1 % and P2 >= 1.05
   P1, where D(P2) < D(P1) by more than `2 sqrt(u1^2 + u2^2)` (u from replicates, else the u_m default of 7.4 item 2);
   the mirror check `FLAG_DEPTH_INCREASES_WITH_SPEED` at fixed power and beam.
3. Aspect `FLAG_ASPECT_RATIO`: D / W above `ASPECT_MAX` (proposal 6; Astra sets it).
4. Too-perfect scatter `FLAG_SCATTER_TOO_SMALL`: a condition with 3 or more sections or tracks all identical at the
   reported precision, or `cv_pool` (7.4) below 0.5 % with at least 3 replicated conditions.
5. Terminal digits `FLAG_DIGIT_PATTERN`: with at least 50 depth values carrying at least 3 significant digits, a
   chi-square test of last-digit uniformity at p < 0.001. Values that are all multiples of 5 or 10 get the label
   `rounded values`, not a flag.
6. Duplicated rows `FLAG_DUPLICATED_ROWS`: identical (depth, width) pairs across different conditions in more than 5 %
   of rows, or a run of 3 or more consecutive rows repeated elsewhere.
7. Known-set match `FLAG_MATCHES_KNOWN_SET <datasetId>`: at least 3 conditions whose alloy, P, v and 1/e2 beam match a
   row of a set in the spent registry within 1 % and whose depth lies within max(1 um, 1 %) of that row. Every registry
   entry with a depth loader takes part (NIST, Cunningham, KU Leuven, Totis, Zhao, Gan and the others), read through
   `lpbf_spent_ledger`; Bitharas is not in this check, because it has no depth loader (Rev. 4, R18, 15.6 item 7). A tuple match without a depth match is the
   note `inputs match known set <datasetId>`, not a flag, because standard parameters are common.

Where they run: in the user's app at `user-sealed-precheck` and before a share, shown to the user only (in Mode B they
are not part of the commitment, so the maintainer learns nothing from the targets before predictions); on the
maintainer side at Mode A import and at Mode B `intake`, which is the record. Tests use synthetic data; agents never
print values (2.3 item 6). What the checks cannot do: data fabricated with realistic scatter around the model passes
them; they catch careless and copied data only (14.1 item 7).

14.7.3 Tiers (cumulative: each requires the one below) [Rev. 4: see 15.6 items 3 to 6: the tier is fixed at import, the
spot check is blinded, and only the closed integrity list removes a registered block].

| Tier | Requires | Effect |
|---|---|---|
| `Declared` | nothing; default for every submission | descriptive only; never counts toward G3o |
| `Evidenced` | per-section values; micrographs with scale bars, at least for the spot-check sample; identity with ORCID or institutional email, lab, machine model and date; no open plausibility flag (absent, or cleared by the reviewer with a written reason); a spot check in which the reviewer measures depth on a sample of micrographs drawn deterministically from the hashes (seed sha256 of `targetsSha256` and `predictionsSha256`, min(5, n) sections) and records agreement within the declared tolerance (proposal: 2 u_m or 5 %, whichever is larger) | may count toward G3o (14.4.6 item 6) |
| `Published` | Evidenced, plus a peer-reviewed article or a DOI dataset holding the per-section values and the micrographs (a micrograph figure in an article counts by its figure locator) | as Evidenced |
| `Replicated` | Evidenced or Published, plus an independent second lab (different lab and machine, no shared submitter) whose block at Evidenced or above measured comparable conditions (same alloy and substrate kind, at least 4 conditions with P, v and 1/e2 beam each within 5 %) | as Evidenced; supports the two-campaign rule (14.4.7) |

14.7.4 Tier state machine [Rev. 4: replaced by 15.6 item 3 and 15.1 item 2h]. Every submission, Mode A or Mode B, starts at `Declared`. Promotions and demotions are events
appended to `tier.json`: `{seq, from, to, by (ORCID or GitHub handle), role maintainer | approved-reviewer, at, reason,
evidenceLocators [], flagsCleared [{code, reason}]}`; the history is never edited. Only the maintainer or a reviewer
listed in `data/benchmark/approved-reviewers-v1.json` (maintainer-committed `{reviewerId, approvedBy, approvedAt}`) may
promote; the tool refuses another `by` (`TIER_REVIEWER_NOT_APPROVED`) and a promotion with a missing requirement
(`TIER_REQUIREMENT_MISSING`, naming it). The tool cannot authenticate who runs it; the trace is the record plus the
maintainer's commit of it. Moves: up one or more tiers when every requirement holds; down to any lower tier with a reason
(a flag found later, an evidence mismatch, a retraction). A demotion of a scored G3o block below Evidenced marks its
record `tier-revoked`; nothing is deleted. The tier that decides G3o eligibility is the one recorded at `tier-decided`,
before scoring: a promotion after the score never makes a scored block count, so a good result cannot be promoted into
G3o after the fact. A later Published or Replicated tier is shown as the current tier.

14.7.5 UI labels (proposals under Q1) [Rev. 4: see 15.6 item 10 and 15.7]: tier badges `Declared: table only, not checked`, `Evidenced: micrographs and
identity checked by a reviewer`, `Published: in a peer-reviewed article or a DOI dataset`, `Replicated: measured again
by an independent lab`; flag line `Flag: <sentence>. Flags never reject data; a reviewer looks at them.`; export notice
`Your submission starts as Declared. Per-section values, micrographs with scale bars and your ORCID or institutional
email let a reviewer raise it to Evidenced.`; fabrication notice `The model is open source, so anyone can compute its
predictions. A sealed submission proves when your measurements were fixed, not that they are real. Evidence, review
and independent replication are what make a result count.`

## 15. Revision 4: Part S (sharing, sealed submissions, research relay)

Status. The gate of 2026-10-15 (`.orchestra/reports/hub_spec_gate_verdict_2026-10-15.md`) rejected revision 3 and split
re-entry. Part P (protocol 1 and section 8) carries R12(a) and R13 to R21 in place. This section is revision 4 of Part S:
it answers R1 to R11, the Part S side of R12 (R12(b)), the spec side of R23 and the minor notes that touch Part S. It is
normative for Part S. Section 14 keeps the revision 3 design as the record of the maintainer's decisions; every
statement of 14 that this section changes is marked there "[Rev. 4: see 15.x]" and listed in 15.10. Part S needs a
fresh Opus gate, and Mode B also needs its own pre-registration (15.1), gated before any phase 8 code. A point that
depends on a maintainer answer is marked [Q1] or [Q2], or [Q6] to [Q16]; until the answer, the text states the gate's
recommendation as the working default, and nothing that depends on it is built.

### 15.1 Mode B is a successor objective with its own pre-registration (working name G3s) [Q12]

1. Why. MELT Amendment 6 item 14.3 bars any loosening of a G3o rule under the G3o name ("A loosening needs a new objective
   name and a fresh pre-registration"). The sealed rules make the data owner the custodial reader, who reads every target
   and chooses the conditions; MELT section 5 item 6 calls such data EXPOSED. A sealed block therefore never counts for
   G3o. It counts, if at all, for a successor objective under its own name, working name G3s, with its own
   pre-registration. This refines the wording "route to G3o" of GOAL decision 5. The alternative, an Astra and Opus
   ruling that SD1 is not a loosening, is not adopted (the gate recommends against it).
2. The G3s pre-registration, written by the lead and gated by a fresh Opus run before any submitted target is read (OD2),
   contains:
   a. The G3o thresholds unchanged (the four thresholds with exact rational comparison, at least 12 conditions, sections
      and frames not replicates), the input metrology grades, the power and beam arms, the resolution qualifier with
      `cv_pool` and the `u_m` default, leverage, and the input-fragile and property-fragile wording, each copied by
      reference to MELT Amendment 6 (items 2.1, 3, 4, 5, 9 and 10) with the amendment's text and JSON sha256.
   b. SD1, defined here and only here: the data owner is the custodian; the predicting party never holds a target or an
      evidence file before the predictions are published.
   c. Zero declared losses in a counting block (R2). A block counts only when every frozen row is `measured` or
      `track-not-formed`. The commitment carries `lossCount`, the number of rows with `specimen-lost`,
      `section-unreadable` or `not-measured`, computed by the user's app from the targets at commit (an integer that
      reveals no value); registration needs `lossCount` 0. Reason: with an open model the owner can compute predictions
      first and mark the worst sections lost, which removes exactly the rows that drive the maximum APE. A block with
      losses is descriptive only. SD2 of 14.4.6 is withdrawn.
   d. Registration fixed at import (R3). `import` records `registration {objective: "G3s" | "none", reasons [], at}`
      before any prediction exists, and it never changes afterwards. A registered block that ends
      `withdrawn-after-predictions`, `expired-unreleased`, `void-early-release`, `void-targets-invalid` or
      `void-run-failed` counts as not passed in the objective record and in the claim line, as a FAIL does under MELT 9.4
      (e). An unregistered block never counts later. The commit and release notices say so (15.7 item 1).
   e. Registration conditions (Q7 recommendation) [Q7]: Ti-6Al-4V or AlSi10Mg; a public block (confidential blocks are
      never registered); an open licence, CC BY 4.0 or CC0 1.0 (15.6 item 1); a Zenodo release (15.4 item 5); an
      identity bound to an ORCID (15.6 item 2); an evidence manifest committed with per-section values and micrographs
      (15.6 item 3); `lossCount` 0; at least 12 conditions left after the exposure exclusions of 15.6 item 7.
   f. The two-campaign clauses of MELT 9.4, copied for G3s milestones (R5): (a) the same frozen predictor commit and rules
      for both blocks; (b) each block must meet the thresholds and qualifiers on its own, and pooled statistics are
      descriptive; (c) no amendment to model, constants or rules between the release of campaign 1 targets and the
      hashing of campaign 2 predictions; (d) the campaign 2 condition matrix committed before campaign 1 targets are
      released; (e) a FAIL, or a not passed under item d of this list, on any registered block means G3s NOT PASSED with
      this predictor. Two blocks that fail independence (same lab, same machine or a shared submitter) count as one
      campaign.
   g. `milestoneStatement` (R5), a field of the results record: null unless the tool computes it from at least two
      registered blocks that each met the thresholds and qualifiers, with bound and distinct identities, different
      public labs and machines (15.6 item 2), and clauses a to e checked. It never comes from a single block. A single
      block's sentence ends `single campaign, not an objective result`.
   h. Closed integrity list (R4). After release, only these findings remove a registered block: (1) a blinded spot-check
      disagreement beyond the declared tolerance (15.6 item 5); (2) a duplicate of a known set (`FLAG_MATCHES_KNOWN_SET`
      confirmed by the reviewer); (3) an evidence manifest mismatch (`EVIDENCE_HASH_MISMATCH`). Each removal is public,
      as `removed-integrity <code>` with the score still printed. Nothing else removes or demotes a registered block: no
      other plausibility flag and no reviewer discretion.
   i. Conflict of interest (R4), declared in the sealed protocol record and on every public surface (15.7 item 1): the
      maintainer publishes the predictions, scores the block and approves the reviewers.
   j. Release obligation and window [Q8]: the committed targets and evidence are released on Zenodo within 180 days of
      `published`.
   k. One declared run (MELT 6.9, PI-10): a crash or a `SEALED_SCORER_DISAGREEMENT` allows a rerun only from the same
      commits, and the rerun must reproduce the bytes; after any code change the block ends `void-run-failed`, which
      counts as not passed when the block is registered.
3. Candidate arm [Q6] (gate recommendation): the MELT candidate through the pinned runner in sealed mode (15.2), with the
   app's served Build Job arm and the research arm (15.3) scored beside it under the same rules. The candidate row is
   labelled `not the model this app serves`; the served row `the model this app serves (same rules, not the registered
   candidate)`. R1 lands first.
4. Honesty fields of the sealed scope (replacing the Mode B column of 2.1 where they differ): `objective` (`G3s` or
   `none`); `notG3oRecord: true` always; `neverEnters.g3o: true` always; `neverEnters.g3s: false` only for a registered
   block; `appBlindTest: true` only for a scored registered block with blindness `blind-sealed` in state `recorded`
   (PI-11).

### 15.2 Sealed runner mode (R1)

At `e91d0fbd` the runner cannot run a sealed block in the sealed order: `run_guards` calls `check_data_hashes`, which
hashes every `data_hashes` key as a file path and raises on "missing", so `--predict` needs the target file;
`validate_run_amendment` requires the whitelist file and the target file as keys; and `require_committed` needs the run
amendment, and before `--score` the prediction file, committed in the runner's own repository.

1. Sealed mode, part of the G3s pre-registration with its own runner pins: `--predict --sealed` accepts a target file
   that is absent at predict time when its sha256 is bound by the commitment (`targetsSha256`). It records
   `targetsBinding: "commitment"` with the commitment id, refuses when the target file is present (a target must not
   exist on the predicting machine before the predictions are published), and at `--score` requires the file with
   exactly that hash.
2. `data_hashes` keeps the runner's shape: keys are paths relative to the maintainer's submissions working repository
   (`submissions/<commitmentId>/inputs.csv`, `.../targets.csv`, the evidence files), values are sha256 values copied
   from the commitment. The id-keyed shape of 4.9 item 3 is withdrawn.
3. The runner runs in a maintainer submissions working repository: a clone of the public submissions repository for
   public blocks, and a private repository that is never pushed for confidential blocks. It never runs in the product
   repository, where `require_committed` would otherwise put submission files into the product history. The product
   repository receives only the result entry (14.1 item 4).
4. The inputs header stage runs at import; the targets header stage runs at `--score`, after publication, against the
   fixed targets whitelist of 4.4.
5. Owners: Opus architect (design), the lead (pre-registration text), Sonnet (code after the gate); listed in OD2 and
   phase 8. Done when a synthetic sealed block predicts with only the hash known, scores after release, and leaves
   nothing of the submission in the product repository.

### 15.3 Research relay (R12(b); after the contract amendment of OD1 and a fresh gate)

Rebased on the P8 integration contract at `14e13ea8` and its amendment once approved. It applies to protocol 2
(`lpbf-user-blind-protocol-2`), Mode A reruns, Mode B and the descriptive record; protocol 1 never uses it (7.6).

1. Module (R13): `python/lpbf_blind_research.py` holds the request builder and the adapter. Its canonical source hash
   enters the research member of the predictor identity, with the research pin and the three schema versions, never the
   served-closure pin. Its tests live in `python/test_lpbf_research_blind_adapter.py`, inside the contract's
   `test_lpbf_research_*` guard scope, and skip with `contract fixture not committed` until the contract's transport
   fixture exists.
2. Requests: one per condition, inputs only (`process` with the 1/e2 beam, `IR_1064nm`, `flat-plate`;
   `propertyContext` `build-job-snapshot` with the served snapshot's `alloyId` and `materialPropertySha256`, or
   `nominal` for IN625; no `researchOptions`), run with the contract's band loop and its 3.5 rule 6 fallback, sent only
   by the blind tab's explicit opt-in or the maintainer's batch client once OD1 admits them.
3. Fields read, with the contract's names at `14e13ea8`: the scored leaf `meltDepthLink.fields.linkedMeltDepth_um`
   (`value`, `reasonCode`, `warnings`, `leafRole`, `sourceEvidenceKind`, `weakestInputs`, `labelSources`, `dependsOn`,
   `band`); the container's `moduleEvidenceCeiling`, `validationStatus` and `validationStatusLocator`; context leaves
   `conditionalMeltDepth_um`, `conductionDepth_um`, `controllingLeg`, `linkDispatch`, `conductionStatus` (`computed` or
   `no-melting`; replaces revision 3's `conductionMeltState`), `floorFieldModelId`, `floorExtractorId`; the descriptive
   leaf `keyholeCavity.fields.cavityDepth_um` with its band; onset support from `keyholeCavity.band.onsetSupport`
   (`supported`, `total`, `unresolved`, `caveat`; replaces `statusSupport`); `meltDepthLink.consistencyNote`. Labels
   come from the response `labels` map and are never authored by the hub.
4. Identity checks (as revision 3, with these changes): the `userInput` check covers only the determining physical inputs
   of the leaf (`dependsOn` within the module's physical input set); the request echoes P, v, d and T0, which P8 marks
   `userInput`, are excluded, and a fixture whose echoes carry `userInput` must pass. `RESEARCH_CODE_STALE`: the lane
   recycles its worker (`recycleWorker`) and the client retries that condition once, as the panel does (contract 13.7
   item 2); no server restart. A request-scope C2 envelope (`RESEARCH_EVALUATION_FAILED`,
   `RESEARCH_SERIALIZATION_FAILED`, and `RESEARCH_RESPONSE_TOO_LARGE`, now C2) carries no block, so it refuses the freeze
   with `RESEARCH_CONTRACT_BROKEN` (check `request-scope-failure`); a C2 code inside a block at arm or module scope is
   class failed.
5. Class table changes: C7 `MELT_LINK_NOT_AVAILABLE` inherits the cavity leaf's class, and every other C7 code on the
   scored value is `RESEARCH_BLOCK_MALFORMED`; C10 codes are band states, never value codes (`BAND_PENDING` in a complete
   response is malformed, `BAND_NO_SUCCESSFUL_ARM` makes the band `unavailable`); `FIELD_SHAPE_STEP_NEAR_ONSET` is a W
   code, carried as a warning and counted into the label `field-shape step near onset in <k> conditions`. The test
   checks the table against the contract's registry by an AST read of `lpbf_research_codes.py`, never an import.
6. One timeout rule: a `RESEARCH_TIMEOUT` of any `timeoutKind` (`queue`, `run`, `reply`, `adhoc`) stops the research
   step for the block; the user may run the step again (cached arms make it cheaper) or freeze without the research arm.
   A freeze takes a complete relay or none (`RESEARCH_RELAY_INCOMPLETE`). There is no automatic retry after a timeout
   and no timeout value class.
7. Size: a subset carries `band.manifestSha256` only, never descriptors, so manifests are deduplicated by hash. A relay is
   staged before the freeze submit in chunks of at most 300,000 characters through the closed queued type
   `user-blind-stage-chunk {uploadSha256, index, count, chunkBase64}`, assembled and hash-checked, so no RPC line comes
   near 1,000,000 characters. The Mode B predictions file uses the same staging (15.4 item 8).
8. Client-asserted: relayed values can be altered by the client, not only read. Every record says `research values
   relayed by the client; not recomputed by the worker`. `share-verify` reports `research unverified` unless the
   maintainer's rerun reproduces them (`research reproduced`).
9. Kept from revisions 2 and 3: coverage (`scored on k of n conditions`), the common subset, n >= 12 inside the scope,
   consistency counts, the paired sign-flip comparison, cost in the research lane only. Restored from revision 2: the
   band coverage sentence `share of conditions whose measured depth lies inside the declared one-at-a-time envelope
   (scenario support, not a probability or confidence interval)`, followed by the contract 4.7 caption; and
   `band-fragile`: the research status recomputed with every complete-band condition at its band `min` and at its band
   `max`; a different status gives the label.
10. Q2 restated [Q2]: on non-surface leaves the contract's status string is "Not experimentally validated; research
    diagnostic/model only.", with `validationStatusLocator` `docs/research/SPEC_p8_research_arm_2026-10-14.md Amendment
    3 C4`; values that depend on the flat surface closure carry the B2 falsified-closure status. The hub renders these
    strings verbatim from the response. The guard `/\bvalidated\b/i` in the hub tests needs an exact-string exception for
    them.
11. Rendering outside the panel (blind report, descriptive panel) follows the contract's display rules (4.7) and label
    rule 3 (7.1), subject to item (c) of the amendment request (OD1).
12. Declared (PI-12c): the research lane's stderr (tracebacks with module, arm id and inputs) lies outside the blind
    sentinel scope; it carries inputs and research values, never a target.
13. Divergence D13 (protocol 2, moved from 7.7 below) now reads "client-asserted" in place of "bound by hash" as its
    integrity statement.

### 15.4 Mode B: state machine, transport and refusals (R3, R6, R9, PI-10, PI-11, HUB-LP-11)

1. `imported` records the registration of 15.1 item 2d. New terminal state `void-run-failed` (15.1 item 2k).
2. `submitted` has a deadline [Q8]: the maintainer imports or refuses within 30 days of the creation of the pull request
   or issue; otherwise the submission is listed as `stale-submitted`.
3. `void-early-release` is reachable from `published`, `released`, `intake-checked`, `tier-decided` and `recorded`,
   whenever an earlier release is shown.
4. Early-release check (R6): the Zenodo server-side record creation timestamp (`created`, set by Zenodo; never the
   depositor-set `publication_date`) is compared at second granularity with the GitHub server time of the predictions
   merge; equal or earlier gives `void-early-release`. The instruction sheet says to start the Zenodo deposit only after
   the predictions are published.
5. Counting blocks need a Zenodo release. An email release (the confidential variant) never counts; confidential blocks
   are registered with `objective: "none"` from import.
6. User-side code renamed: `PREDICTIONS_NOT_PUBLISHED` becomes `PREDICTIONS_FILE_NOT_CHECKED`, because the app can check
   only that a predictions file was checked on this computer, not that it was published.
7. Cross-mode overlap (R9): `user-sealed-commit` consults the local ledger (6.4 item 3: overlapping tuples of any test on
   this computer that was revealed or scored) and the Build Job history (6.4 item 6), and refuses with
   `SEALED_LOCAL_TEST_OVERLAP`. Checking a published predictions file adds its tuples to the local overlap index as
   `sealed-predictions-seen`, and the local sealed score does the same, so a later local test or sealed submission on
   those conditions is not blind or is refused. The `SEALED_PREDICTIONS_VIEWED` message no longer suggests running a
   local test.
8. Release payload: `user-sealed-release` refers to the predictions file by sha256 after chunked staging (15.3 item 7);
   the targets travel alone (at most 350,000 base64 characters), so the RPC line stays under 1,000,000 characters.
9. `appBlindTest` as 15.1 item 4 (PI-11).
10. Withdrawal before predictions: the public commitment may be replaced by a hashes-only file [Q8] (HUB-LP-11).
11. Permanence notice at release (HUB-LP-11): `Your Zenodo release is public and permanent. It cannot be withdrawn.`
12. Section 9 item 18 corrected: the times that count are GitHub server times and the Zenodo server-side `created`
    timestamp; an email release is timed by the maintainer's record, labelled so, and never counts.

### 15.5 Mode A (R7, R8, HUB-LP-13, HUB-LP-19)

1. Redacted report without targets consent (R8). The share then holds `score-<n>.redacted.json` in place of
   `score-<n>.json`: statistics, counts, statuses, coverage, keys and exclusion statuses only. Removed: per-condition
   `trackDepths_um`, `D_obs_um`, `widthObs_um`, `rel` per arm and band membership per condition. The frozen predictions
   stay. Both the redacted and the full report hashes are listed, so a full report can be checked later if the user
   consents. The `share-verify` line becomes `targets withheld: statistics as reported by the user, not reproducible by
   the recipient`, which is then true.
2. The consent text names exactly the numbers that leave [Q1]: with targets, `every measured depth, width and
   uncertainty per section, and every per-condition difference from the predictions`; without targets, `the summary
   statistics per arm (median, 90th percentile, mean signed and maximum relative error), counts and statuses, and the
   frozen predictions; no measured value`.
3. A sentinel test runs over a no-consent tar: sentinel targets appear nowhere in it.
4. Public spent-ledger entry (R7): raw and canonical-content hashes (`inputsSha256`, `inputsContentSha256`,
   `targetsSha256 []`, `targetsContentSha256 []`; a content hash is the sha256 of the canonical parsed rows, so a
   re-saved or re-indexed file gives the same value), DOI, licence, attribution and counts only. It never holds tuples or
   points, whatever `publishAllowed` says (GOAL decision 5: results, hashes, DOIs).
5. Durable maintainer index (R7): `METALLIKSA_MAINTAINER_INDEX` (default `~/.metalliksa/maintainer-index/`, outside the
   repository and outside `.runtime`) holds the seen tuples and content hashes in a hash-chained file. `share-import` and
   sealed `import` fail closed with `SHARED_INDEX_MISSING` when it is absent or its chain does not verify. A match is a
   raw hash, a content hash or a tuple overlap (1 % rule).
6. Shared sets stay out of the committed descriptive record [Q13] (recommendation: never; link the DOI and show counts
   only).
7. The share notice names the public entry and its fields, and the export offers ordinals in place of store ids and file
   names (HUB-LP-13).
8. For sharing the user starts, decision 5 supersedes the wording of decision 3 ("users may share a verifiable result
   bundle (hashes and statistics) voluntarily"); decision 3 still governs where processing happens (HUB-LP-19).

### 15.6 Tiers, identity and licence (R4, R11, PI-13, PI-14, HUB-LP-11, HUB-LP-12, U11)

1. Licence [Q10]: a public block requires CC BY 4.0 or CC0 1.0; `none` is allowed only for Mode A and for confidential
   Mode B; counting blocks need an open licence. CC BY attribution (ASCII only, U11) is carried into the result entry.
   The submissions repository README (maintainer text) states that commitments are data under the submitter's licence,
   not code contributions, so the product's licence and CONTRIBUTING do not apply to them.
2. Identity [Q10, Q14]: an institutional email is never published in any form, not even hashed, because a hash of a
   guessable address can be reversed; it reaches the maintainer by email only. Evidenced needs an ORCID bound by a
   channel the maintainer checks by hand: a Zenodo deposit made under that ORCID login, the ORCID record listing the
   DOI, or a GitHub account linked from the ORCID record that opened the submission. Format and checksum alone are not
   enough. Lab and machine are public for counting blocks; the ORCID is public only with consent and only for counting
   blocks; a reviewer is listed only with the reviewer's consent (HUB-LP-11).
3. Tier fixed at import (R4): `import` checks the identity binding (the maintainer records the channel and the check) and
   the evidence manifest (per-section reduction, a micrograph entry with a scale bar for every section, hashes). A block
   with both is `Evidenced (registered)`; otherwise it is `Declared`. There is no promotion after import. After release,
   only the blinded spot check (item 5) and the closed integrity list (15.1 item 2h) can remove a registered block.
   `Published` and `Replicated` are display tiers added later; they never change counting.
4. Plausibility flags are shown and recorded. Only `FLAG_MATCHES_KNOWN_SET`, confirmed by the reviewer, is an integrity
   finding; no other flag removes or demotes a block, and no flag is "cleared" at discretion.
5. Blinded spot check (R4): the tool gives the reviewer the sampled micrographs (the deterministic sample of 14.7.3) with
   their scale bars and keys, never the claimed depths; the reviewer records the measured depths; only then does the
   tool compare them with the table. Tolerance [Q11]: proposal 2 u_m or 5 %, whichever is larger; Astra signs it.
6. `Replicated` requires that the second block is a Mode B block registered as Evidenced, from a different lab and
   machine (PI-13).
7. Consistency of tuple matches (PI-14): a tuple-only match with a spent set is an exposure fact, never a fabrication
   flag. Protocol 1 marks the test not blind (6.4 item 5). A sealed import excludes the matching conditions by input
   label before predictions, as MELT Amendment 6 item 12 does for exposed conditions, and registration needs 12
   conditions left. The known-set check of 14.7.2 item 7 runs only on sets with a depth loader [Q11]; Bitharas is removed
   from it (R18). Declared hole: data copied from the reserved, unopened G3o candidates (Leis, Gong, Ullah, Hyer,
   Aboulkhair) cannot be detected, because no loader exists and the program must not open them.
8. Image location marker (HUB-LP-11): the browser checks the first 64 KiB of each JPEG or TIFF for a GPS tag and shows
   `FLAG_IMAGE_LOCATION_METADATA` to the user before hashing; it never alters the file.
9. Identity and attribution never persist in plain form in `.lpbf-jobs/<job>/input.json`: they are staged as hashed
   documents like the metadata, and an identity sentinel test scans job folders, logs and results (HUB-LP-12). Required
   before phase 8.
10. Badge wording matches what is checked [Q1]. Proposal: `Evidenced: identity bound to an ORCID and micrographs listed
    before the predictions; spot check made after release`; `Declared: table only, not checked`.

### 15.7 Public result surfaces (R10, ENG-20)

1. Caveat on every public result surface (the sealed table, `result.json`, `sealed-submissions-v1.json`, the claim
   sentence, the PROOF entry, the submissions repository status file) [Q1]: `The model is open source, so the data owner
   could compute its predictions before measuring or choosing conditions. A sealed submission shows when the targets
   were fixed; selection without fabrication is not detectable. The maintainer who publishes the predictions also
   scores the block and approves the reviewers.` The commit and release notices add: `If your block is registered and
   you do not release the committed targets after the predictions are published, it counts as not passed for the
   objective.`
2. Table title [Q1], proposal: `Sealed submissions (data owners' blocks, scored once)`. The title `Independent sealed
   blind tests` is withdrawn: independence is declared, not verified.
3. Verdict words are mapped at render time: the runner's PASS, FAIL and INCONCLUSIVE are shown as the `thresholds-met`,
   `threshold-not-met` and `inconclusive` sentences of 2.2. A test fails on any PASS or FAIL token in the sealed table
   and its data.
4. The candidate row and the served row carry the labels of 15.1 item 3.
5. Separate record (ENG-20): the sealed table reads `data/benchmark/sealed-submissions-v1.json` through its own loader.
   The leaderboard record keeps schema `lpbf-leaderboard-1`, the four committed v1 records keep loading, and
   `python/tools/lpbf_benchmark_score.py` does not change. The `lpbf-leaderboard-2` plan of 14.4.9 is withdrawn.
6. A registered block that ends not passed (15.1 item 2d) is a row with that status, not only a count.

### 15.8 Spec 8.2: Totis datum (R23, spec side)

The 8.2 Totis row carried `DATUM_UNSTATED`, which is wrong. The repository records the datum
(`python/lpbf_public_datasets.py:131-133`): the workbook does not state it, but the associated paper (Vaglio et al.
2020, Fig. 1, Fig. 2(b) and Sec. 1.3) does: depth is measured from the top of the printed base under the 25 um powder
layer. The row is corrected in place. Astra writes the physics sentence later: which catalogued reason applies and how
the powder-layer offset enters. The other R23 items concern the internal note, which left the branch (R22, `ba7dc030`).

### 15.9 Maintainer answers this section depends on

| Question | Points that wait for it | Working default (gate recommendation) |
|---|---|---|
| Q1 wording | tier badges, caveat, table title, consent text, notices, research label, Measured label (15.5 to 15.7) | protocol 1 core strings and refusal messages approved now; the rest after a rendered sheet |
| Q2 status string | 15.3 item 10 | exact-string exception in the guard |
| Q6 candidate arm | 15.1 item 3, 15.2 | MELT candidate through the sealed runner; served and research arms beside it |
| Q7 counting blocks | 15.1 item 2e | Ti-6Al-4V and AlSi10Mg; public; open licence; Zenodo; registration at import; identity bound; zero losses |
| Q8 window and withdrawal | 15.1 item 2j, 15.4 items 2 and 10 | 180 days; unreleased or withdrawn after predictions is not passed; hashes-only replacement before predictions |
| Q9 labels | 14.6 | served `Unresolved` with its reason as text; P, v, d, T0 never make a research output `User input` (P8 item I-1) |
| Q10 licence and identity | 15.6 items 1 and 2 | as written there |
| Q11 constants | 14.7.2, 15.6 items 5 and 7 | accept the proposals; freeze them before the first real submission; known-set check only with a depth loader |
| Q12 objective name | 15.1 | successor objective G3s with its own pre-registration |
| Q13 Mode A in the descriptive record | 15.5 item 6 | no; DOI link and counts only |
| Q14 public identity fields | 15.6 item 2 | ORCID, lab and machine only for counting blocks, with consent; reviewers only with consent |
| Q15 Measured label | 14.6, 7.5 | `Measured (user-supplied)` with the tier beside it; never a bare `Measured` |
| Q16 findings note | none in this spec (the note left the branch, R22) | keep it internal |

### 15.10 Gate items and the revision 3 statements they replace

| Gate item | Revision 4 | Replaces in section 14 or elsewhere |
|---|---|---|
| R1 runner cannot run sealed | 15.2 | 14.4.6 item 1 (runner use), 4.9 item 3 (id-keyed `data_hashes`) |
| R2 SD1 and SD2 loosen G3o | 15.1 items 1, 2b, 2c | 14.4.6 items 5 and 6 (SD1 to SD3, G3o counting) |
| R3 optional stopping | 15.1 item 2d, 15.7 item 1 | 14.4.3 terminal states without effect on counting |
| R4 tier decided with the outcome computable | 15.1 items 2h and 2i, 15.6 items 3 to 5 | 14.7.3 (Evidenced requirements), 14.7.4 (tier events after scoring) |
| R5 two-campaign rule | 15.1 items 2f and 2g | 14.4.7 (two-campaign rule) |
| R6 Zenodo publication date, email | 15.4 items 4, 5, 6 and 12 | 14.4.4 (early-release row), 14.5 items 2 and 3, 9 item 18, `PREDICTIONS_NOT_PUBLISHED` |
| R7 Mode A ledger | 15.5 items 4 to 6 | 14.3.5 (tuples in the public entry, index under `.runtime`) |
| R8 Mode A consent | 15.5 items 1 to 3 | 14.3.1 item 4 and 14.3.4 item 5 |
| R9 cross-mode overlap | 15.4 item 7 | 14.4.4 (no local overlap check), 6.1 `SEALED_PREDICTIONS_VIEWED` message |
| R10 public surfaces | 15.7 | 14.4.9 (title, verdict words), 2.2 leaderboard row |
| R11 licence and identity | 15.6 items 1, 2 and 10 | 14.3.3, 14.7.1 item 3 (email hash, offline ORCID check), 14.7.5 badge |
| R12(b) relay | 15.3 | the revision 3 relay text, now replaced in this section |
| R23 spec side | 15.8, 8.2 | 8.2 Totis row |
| Minor notes | PI-10 (15.1 item 2k, 15.4 items 2 and 3), PI-11 (15.1 item 4), PI-12c (15.3 item 12), PI-13 (15.6 item 6), PI-14 (15.6 item 7), ENG-20 (15.7 item 5), HUB-LP-11 (15.4 items 10 and 11, 15.6 items 2 and 8), HUB-LP-12 (15.6 item 9), HUB-LP-13 (15.5 item 7), HUB-LP-19 (15.5 item 8), U11 (15.6 item 1) | as listed |

Divergence moved from 7.7 with the relay (protocol 2 only; integrity statement per 15.3 item 13):

| Id | MELT or GOAL rule | Protocol 2 rule | Reason |
|---|---|---|---|
| D13 | MELT section 6 item 6: every arm's prediction is written by the prediction process before scoring | the research arm is computed by the P8 research route on the user's explicit request and relayed by the browser into the freeze, where it is bound by hash before any target reaches the server; the values are client-asserted; the worker cannot recompute them; a Mode A rerun or a maintainer batch reproduces them from the recorded requests (15.3) | the P8 integration contract allows research only through its own opt-in route, never inside a worker job |

## Appendix A. Grafts and judge defects

### A.1 Grafted ideas

| From | Idea | Where |
|---|---|---|
| Design 2 | overlap with any revealed or scored test makes later tests not blind | 6.4 item 3 |
| Design 2 | freeze refuses when the live fingerprint differs from the pin (widened to the served-closure pin) | 3.6 |
| Design 2 | browser-computed commitment of the raw targets file, pre-measurement mode | 4.1, 5 item 2, 6.4 |
| Design 2 | honesty block with `neverEnters`, `g3Satisfied`, `n3Counted`, protocol id not G3o | 2.1 |
| Design 2 | more than 20 % post-freeze exclusions gives inconclusive (counted for tracks and conditions; declared divergence D1) | 4.4, 6.2, 7.7 |
| Design 2 | AST import isolation, offline verify, phase 0 route spike, spent registry with `spentBy`, datum and same-experiments codes | 11.1, 12, 8.1 |
| Design 3 | open() audit, minimal job results, Build Job history check, previewSha256 confirm-by-hash | 11.1, 3.2, 6.4, 5 |
| Design 3 | closed alias table, declared dialects, xlsx and encoding refusals with fix text, unit hints, feasibility before freeze | 4.2, 6.1, 6.3 |
| Design 3 | per-field help, conservative defaults, list and load, exports, discoverability links | 3.4, 4.1 |
| Design 3 | model map, index-axis toggle, signed-percent chips, sign-matched catalogued reasons, `THRESHOLD_DERIVED_FROM_THIS_SET`, forbidden-id test | 8 |
| All missing | MELT reduction gate as a metadata field | 4.1 `reduction`, 6.2 |
| All missing | maintainer decision on `not validated` versus the guard | Q2 |

### A.2 Base design (reuse first) defects

| Defect | Resolution |
|---|---|
| Reveal-then-refreeze loophole across freezes | overlap rule at preview and score, 6.4 item 3 |
| P8 label rewritten to pass a guard | no rewrite; Q2 |
| Zhao moved to SPENT with an asserted approval | not moved; Q3 and a separate commit |
| Freeze does not refuse on fingerprint drift | `PREDICTOR_NOT_PINNED` over the fingerprint and the served-closure pin; scorer identity kept separate |
| No cap on post-freeze exclusions | 20 % rule at track and condition level; not-formed tracks counted as misses; D1 declared |
| Reduction (maximum only, single section) not asked | `reduction` field |
| No datum code, Gan not flagged as Cunningham | `DATUM_UNSTATED`, `SAME_EXPERIMENTS_AS` |
| Serial queue starvation | measured cap at 60 s p95 including P8 band arms, per-type timeouts, UI note; preview, list and get off the queue, write-free and solver-free |
| Completion path falls into `enforce_thermal_balances` | explicit blind enforcer in `execute()` and `get()` |
| Repeat route not covered | blind jobs never deduplicated on either path; tested |
| Predictions and targets copied into the generic job store, stale cached receipt | uploads staged by hash in the blind store, `input.json` hashes only, documents served from the store, no dedupe |
| Node parses 50 MB first | not changed: pre-existing global parser for every job type; RPC line cap and Python caps bound the work |
| Duplicate legacy rows undecided | decided: not added |
| Weak discoverability, buried under the CMU block | Hub tab, CTA, pointer, palette, cross links |
| Exact headers only, plan template unusable | aliases, derived conditions from unique track ids, repeated inputs allowed in targets, plan template button |
| Comma only | three declared dialects with fix messages |
| Feasibility only after freeze | preview with acknowledgements |
| No server-side list | `user-blind-list`, `user-blind-get` on the estimate RPC, `user-blind-open` when a job record is gone, load by freeze key |
| Two different error numbers, layer artefact exposed | leaderboard columns dropped; layer note only per Astra check |
| JSON-only export, no chart | comparison CSV, print view, SVG chart, bundle |
| ln ratio hard to read | signed percent |
| Thin UI spec | steps, help data, queue wording, qualifier sentences |

### A.3 Defects of designs 2 and 3, where they touch grafted parts

| Defect | Resolution |
|---|---|
| Leverage non-gating (design 2) | gating kept as MELT |
| Shared warm daemon for freeze and score (design 2) | not applicable: fresh child per job |
| Bundle not state gated (design 2) | one reveal-or-score gate in the artifact branch, the bundle job and the CLI `show` and `bundle`, or a reveal written first |
| Hash chain adds little (design 2) | kept as cheap local tamper evidence, stated as such |
| Hard refusals on datum and beam (design 2) | block issues instead, MELT grades |
| Commitment mismatch punishes honest mistakes (design 2) | explicit continue path that downgrades to declared |
| Shouting enums (design 2) | plain sentences |
| Budget set before measurement (design 2) | cap measured in phase 0 and 1 |
| ScatterPlot with plus or minus 30 % guides (design 2) | purpose-built SVG |
| Affinity-lane claim, warm-pool writes, registry blast radius (design 2) | not applicable: no new route, module or warm script |
| Sealed mode reads targets before freeze (design 3) | not adopted: two files, targets absent until a freeze exists |
| `d_um` and `D_um` alias collision (design 3) | not aliases |
| `registeredScope: G3o` (design 3) | `notG3oRecord: true`, alloy note |
| PASS and FAIL (design 3) | status words of 7.3 |
| Overlap only with scored tests, 50 % rule (design 3) | revealed or scored, per condition at 1 %, commitment exception |
| Panel admits EXPOSED sets (design 3) | SPENT only |
| Notes parsed and never parsed (design 3) | notes never parsed; synthetic data marked in ids and titles |
| 900 s timeout, synchronous RPC handlers, chaining logic (design 3) | 900 s timeout and chaining not adopted; synchronous handlers only for bounded, write-free, solver-free reads (preview, list, get), never for a mutation |
| Job result without provenance (design 3) | `run_job` returns provenance |
| Blank targets without a reason (design 3) | `depth_status` vocabulary |
| Numbered tab under the brief selector (design 3) | unnumbered tab, selector hidden |
| Predictor change forces refreeze (design 3) | frozen values scored with a label |

### A.4 Revision 2: gate must-fix items and where they are resolved

| Gate item | Resolution |
|---|---|
| Prediction leak through the generic job record | silent child, fixed codes, counts-only progress, log filter (3.2 items 3 and 4); sentinel-prediction scan (11.1 item 7, phase 2) |
| Bundle job and CLI `show` and `bundle` ungated | one reveal-or-score gate or a reveal written first (3.1, 3.2 item 7, 3.2.1, 5 step 8); tests (11.1 item 6) |
| Read-only mode and store root do not reach a WSL worker | `WSLENV` forwarding in `server/pythonRuntime.ts` (1.2, 3.3, 10.2); tests (11.2 item 4, phase 2) |
| 7.6 written against a stale P8 v1 contract | 7.6 rewritten against P8 v2 `b6e68dfe`: adapter, reason-code classes, pinned `researchOptions`, coverage, common subset, bands, consistency counts, freeze cost with 18 or 24 arms (superseded by revision 3: the P8 integration contract, A.5) |
| `PREDICTOR_NOT_PINNED` narrower than the served path | served-closure pin and import-closure test; separate scorer identity; wording out of `protocolSha256` (3.6, 4.6) |
| Post-freeze exclusions | not-formed tracks counted as misses; losses counted for tracks and conditions; policy declared as D1 (4.4 item 2, 7.7) |
| No divergence list; `beam.profile` default; IN625 leverage | 7.7 in the protocol record and every report; `unknown` is a label; leverage at step 5 (6.2, 7.3, 7.4) |
| Calibration data and published data without a rule; 6.4 items 2 and 3 inconsistent | 6.4 items 7 and 8, the commitment exception applied to items 2, 3 and 7 |
| Acknowledgements inside the preview hash | top-level request field; explicit `ACK_REQUIRED` and `OVERLAP_CHANGED` checks at submit and in the child (4.1, 5 steps 5 and 6) |
| List and get on the serial queue | write-free reads on the estimate RPC; `user-blind-open` for a missing job record (3.2 item 1, 3.2.1) |
| Crash consistency | OS-held lock, commit points, ledger after commit, reconciliation, kill-at-each-step tests (3.5) |
| Missing refusals and limits | `TARGET_OUT_OF_RANGE`, `SYNTHETIC_EXAMPLE_ROW`, `FILE_NAME_INVALID`, `blockLabel` rule, export neutralisation, secure-context behaviour, shared-host refusal (4.2, 4.4, 6.1, 3.4, 9.7) |
| Request types not enumerated; anchor errors; Opus gating its own code | 3.2.1; anchors fixed in 3.1, 3.4, 8.3, 10.2; fresh Opus gate (section 10, section 12) |

### A.5 Revision 3: decisions and where they land

| Decision or change | Where |
|---|---|
| Processing on the user's machine; maintainer never inside the user's app | 14.1, 1.2, 9.14 |
| Mode A share bundle, maintainer verify and import, data counted as seen | 14.3, 3.1, 3.2.1, 3.5, 4.8, 5.1, 6.1, 6.4 item 5, 9.16, 11.1 item 10, phase 8 |
| Mode B commitment, state machine, refusals, sealed protocol, leaderboard | 14.4, 3.1, 3.2.1, 3.5, 4.9, 5.2, 6.1, 6.4, 7.3, 10, 11.1 item 11, 11.2 item 7, phase 8 |
| Transport without a server; no upload; air-gap unchanged | 14.5, 9.14, 11.1 item 13, 11.2 item 8 |
| Per-value `sourceEvidenceKind`, research label rule, ceiling unchanged | 14.6, 2.1, 7.5, 7.6 item 9, 8.3, 11.1 item 12 |
| Trust tiers, raw evidence, identity, plausibility flags, two-campaign rule | 14.7, 14.4.7, 2.2, 4.9, 6.5, 9.17, 11.1 item 11, phase 8, Q1 |
| 7.6 reconciled with the P8 integration contract (no served bump, opt-in route only, `p8-research-v3`) | 7.6, 1.2, 3.1, 3.2, 3.6, 4.3, 4.5, 5, 7.1, 7.7 D12 and D13, 8.3, 8.4, 10, 11.1 item 3, phase 6, OD1 |

### A.6 Gate 2026-10-15, Part P: where each required change lands

| Gate item | Resolution |
|---|---|
| R12(a) research arm fixed, relay out of phases 1 to 4, OD1 as a contract amendment request, phase 6 acceptance | 7.6 (rebased on `14e13ea8`), 3.1, 3.2, 3.2.1, 3.6, 4.3, 4.5, 5 steps 4 and 6, 7.1, 7.3, 7.7 (D13 moved to 15.3), 8.3, 8.4, 11.1 item 3, 12 (phases 1 and 6), 13 OD1 |
| R13 adapter and request builder out of the served-closure pin | 3.1 (`lpbf_blind_research.py`, Part S), 3.6, 10.1, 11.1 item 3 (tests skip until the contract fixture exists) |
| R14 served closure | 3.1 `served_arm` imports, 3.6 executed-closure test and `canonical_source_bytes`, `scorer_source_hashes` rename, 11.1 item 2 |
| R15 refusals reach 422, closed table, no target leak | 3.2 items 2 and 10, 4.2 item 5, 4.4 item 3, 5 step 10, 6.1 rows, 10.2, 11.1 items 4 and 6, 11.2 item 1 |
| R16 WSL forwarding | 3.3, 10.2, 11.2 item 4, phase 2 acceptance |
| R17 lock domain and crash consistency | 3.1, 3.5 items 1, 2 and 5, 5 steps 6 and 11, 6.1 `STORE_LOCK_DOMAIN`, 11.1 item 5, phases 1 and 2 |
| R18 Bitharas contradictions | 8.1 items 1 and 3 (ledger fields, gated SPENT record only, interim rule); owner of the served definition and panel path is a lead item |
| R19 `Measured (user-supplied)` | 7.5, 14.6, 11.1 item 12, 11.2 item 2; Q15 |
| R20 intake | 3.4 item 8, 4.1 `reduction`, 4.2 items 4 and 5, 4.5 item 1, 5 steps 2 to 4, 6.1, 11.1 item 4, 11.2 items 1, 2 and 6 |
| R21 plan panel notice and comparison CSV | 10.2 plan panel row, 4.5 item 6, 11.1 item 6, 11.2 items 1 and 6 |
| Minor notes folded in Part P | PI-12b (5, readable on disk), PI-15 (3.5 `score-refused`, 5 guarantee scope), ENG-15 (3.3 `storeId`), ENG-16 (3.2.1 budgets and lock attempt), ENG-17 (3.1, 5 step 6), ENG-19 (8.3 item 6), ENG-21 (9.11), ENG-22 (3.2 item 3), ENG-24 (12 queue and critical path), HUB-LP-14 (2.2, 14.6), HUB-LP-15 (8.1, 8.3 item 5), HUB-LP-16 (8.1), HUB-LP-18 (2.2, 14.6), U9 (2.2), U11 (4.2 item 5, 6.1) |
