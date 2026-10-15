# SPEC: your own blind test (bring your own data) and the descriptive panel on spent sets

File: `docs/research/SPEC_research_hub_data_2026-10-14.md`. Design gate draft, written 2026-10-15 on worktree
`Metalliksa-1-wt-hub` (branch `feat/research-hub-data`, HEAD `835466fa`, fingerprint pin `36cd9d4a…`). Nothing in the
product implements it yet. Revision 2 (2026-10-15): the gate's must-fix items, missing items and contradictions are
applied in place (committed as `2f0d884a`). Revision 3 (2026-10-15, section 14): sharing with the maintainer (Mode A
"share my result", Mode B "sealed submission"), transport without a server, anti-fabrication trust tiers, the
maintainer's per-value label decisions, and section 7.6 reconciled with the P8 integration contract
(`research/p8-research-arm` `29ae2183`: no served bump, research only through its own opt-in route, block schema
`p8-research-v3`), integrated into the affected sections (Appendix A.5).

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
| `notG3oRecord` | `true` | `true` unless `g3oBlock` is true (14.4.6 item 6) |
| `appBlindTest` (new) | `false` | `true` for a scored sealed block at tier Evidenced or above; `false` otherwise |
| `neverEnters` | every member `true` | `g3`, `n3`, `n4`, `physicsBump`, `calibration`, `researchRegistry` `true`; `g3o` `false` only for a G3o block; `leaderboard` `false` |
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
| Research arm label | `Literature estimate / Research / not validated` (GOAL item 0 wording; see Q2); under revision 3 the first part is the leaf's own `sourceEvidenceKind` (14.6) |
| Research opt-in (revision 3) | `Include the research arm (runs the research models for every condition; values stay hidden until scoring)` |
| Share step (revision 3) | `Share my result` |
| Share notice | `Sharing sends nothing by itself. The app writes a file and you decide where it goes. Once the maintainer opens it, this data counts as seen and can never be a blind test of the app.` |
| Sealed step | `Sealed submission` |
| Sealed notice | `Your measurements stay with you until the maintainer has published predictions. Submit the commitment file, wait for the predictions, then release the targets file you committed.` |
| Sealed Declared reason | `tier Declared: table only, not checked` |
| Leaderboard table | `Independent sealed blind tests`, caption `Each row is one data owner's block, scored once under the sealed protocol. Rows are not ranked or pooled.` |
| Tier badges, flag line, export and fabrication notices | 14.7.5 |

Status words are lower-case kebab identifiers in data; the UI never shows PASS, FAIL, "validated" or "accuracy".

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
| `python/lpbf_served_arms.py` | Single definition of served and research arms, shared by the blind test and the descriptive tool. `served_arm(alloy, P, v, d_1e2_um, T0_C, layer_um)` reproduces `lpbf_build_job_solver.py:910-1028` exactly: `resolve_alloy_id`, `ALLOY_MATERIALS`, `build_material_property_snapshot`, `canonical_material_source`, `build_build_job_identity(BUILD_JOB_MODEL_ID, BUILD_JOB_SOLVER_REVISION)`, then `calculate_meltpool_physics(thermal_mat, P, v, d, T0, layer, 110.0, "IR_1064nm", incline_angle_deg=0.0, process_seed=DEFAULT_PROCESS_SEED, prop_overrides=snapshot["thermal"], include_process_map=X)`. X is `False` only if the parity test proves identical geometry with `True`; otherwise `True`. Returns `depth_um` and `width_um` only when `meltPoolGeometry.extentStatus == "computed"`, else `{status: "failed", reason: "EXTENT_NOT_COMPUTED"}`; also `keyholeModel.fabbroDepth_um` (context) and the unrounded index from `lpbf_public_datasets.normalized_enthalpy` (the runner's leverage convention; the served response rounds it to 2 dp). IN625 is not a Build Job alloy: the direct thermal path with `"Inconel 625"`, flat-plate, Rosenthal, no overrides, `buildJobIdentity: null`, reason label `IN625_DIRECT_THERMAL_PATH`, and the result's `materialEvidence` (`legacy-estimated-secondary`) copied into the arm label. `sensitivity_arms()`: served at P x 0.95, P x 1.05, d x 0.95, d x 1.05 (MELT `POWER_BAND` and `BEAM_BAND_GRADE_B`); no served call evaluates research (P8 integration contract, 7.6). `research_requests(conditions, identity)`: builds the closed research request bodies of 7.6 item 2 from inputs only; it imports no research module and computes no research value. `predictor_identity()`: section 3.6. |
| `python/lpbf_p8_adapter.py` | Closed P8 adapter (7.6): `P8_ADAPTERS["p8-research-v3"]` over the relayed response subsets, the identity checks of 7.6 item 3, the reason-code class table, band and `consistencyNote` extraction, the `researchOptions`-absent and no-`userInput` assertions, the research pin read as bytes. Pinned in the served-closure pin (3.6). Imports no `lpbf_research_*` module (contract guard R-ISO-1) and no research branch. |
| `python/lpbf_user_blind_inputs.py` | Metadata schema and validation, inputs CSV parsing (dialects, closed alias table, header whitelist checked before any data row, caps, base64 decode, UTF-8), structure checks, input-only exclusions (runner `parse_input_rows` rules), beam conversion, grades, block issues, design checks, preview. Must not import the targets parser. |
| `python/lpbf_user_blind_targets.py` | Targets CSV parsing, exact key join, `depth_status` rules, repeated-input check, commitment check. |
| `python/lpbf_user_blind_store.py` | Store root, layout, exclusive create (`open(mode="x")`), sha256 sidecars, read-only bit after write, content-addressed uploads, staging and rename (the commit point), ledger with sequence and previous-entry hash, OS-held store lock, start-of-mutation reconciliation (3.5), caps, listing of incomplete staging dirs, the reveal-or-score state gate shared by the artifact branch, the bundle job and the CLI, `source_identity(paths)` (hashes files by path without importing them), read-only tuple readers for the calibration stores (6.4 item 7). |
| `python/lpbf_user_blind_freeze.py` | Freeze: re-run preview, re-check required acknowledgements and overlap, identity checks, per-condition arm predictions, freeze record, receipt. Imports inputs, served arms, stats (design checks only) and store. Must not import `lpbf_user_blind_targets` or `lpbf_user_blind_score` (AST test); the scorer identity is computed by `source_identity`, which reads bytes and imports nothing. |
| `python/lpbf_user_blind_score.py` | Score: verify freeze, join targets, reduce, statistics per arm, coverage and common subset, qualifiers, fragile labels, blindness rule, scorer identity, report. |
| `python/lpbf_user_blind.py` | Façade for the worker: `USER_BLIND_RPC_TYPES` and `USER_BLIND_JOB_TYPES` (3.2.1), `validate_request(raw)` per type (closed keys, Phase 6a validation envelope so the route answers 422), `stage_request(p)`, `run_job(input)` (silent child, fixed error codes), `rpc(raw)` for the estimate RPC (preview, list, get), `enforce_user_blind_job_result(result, params)`, `filter_blind_log(text)`, `blind_document(result, name)` for the artifact branch, label constants. Lazy imports per job type keep the freeze path free of the targets parser. |
| `python/lpbf_spent_ledger.py` | Loader and checks for `data/benchmark/spent-ledger-v1.json`; used by the descriptive tool and by the blind test exposure check. |
| `python/tools/lpbf_user_blind.py` | Offline CLI for air-gapped labs on the same library: `templates [--from-plan plan.json]`, `preview`, `freeze [--research-responses <dir>]`, `reveal`, `score`, `list`, `show`, `bundle`, `verify`, `export-protocol [--check]`, `pin-served-closure [--check]`, and in revision 3 `share`, `share-verify`, `share-import` (Mode A), `sealed-precheck`, `commit`, `check-predictions`, `release` (Mode B, user side). No network. The CLI goes through the same store functions and the same state gate as the worker: `show` prints predicted values and `bundle` writes a tar only when a reveal record or a score exists for the freeze, or when `--reveal "<phrase>"` is given, which writes `reveal-<n>.json` and the `revealed` ledger event first; otherwise both refuse with `REVEAL_REQUIRED`. `list` and `verify` print receipts, hashes, statuses and check results only, never a predicted or measured value. Run it in the same environment as the worker (both Windows or both WSL), because an `msvcrt` lock and an `flock` on a `/mnt` path do not exclude each other. |
| `python/tools/lpbf_spent_descriptive.py` | Offline producer of the descriptive record (section 8). |
| `python/lpbf_blind_share.py` (revision 3) | Mode A (14.3): deterministic share tar, consent, licence and attribution checks, ledger excerpt with redacted links; `share_verify(tar)` and `share_import(tar)` with the checks of 14.3.4, closed member names and caps (9.16), writes only under the shared-results root, drafts the spent ledger entry. Imports the store, the scorer (re-score) and `lpbf_served_arms` (re-predict); never a research module. |
| `python/lpbf_sealed_submission.py` (revision 3) | Mode B (14.4): commitment builder and checks (user side); the maintainer's sealed store (layout of 3.5, same lock, ledger and commit-point rules); the state machine of 14.4.3; import, run amendment builder (closed key set of MELT Amendment 6 item 14.4), freeze (served arms through `lpbf_served_arms`, the MELT runner's prediction file imported by hash, research subsets from route responses), publish, receive-targets, intake, tier events, score (`lpbf_blind_stats` under the sealed rule record, compared with the MELT runner's verdict file), result and record entry, `verify`. |
| `python/lpbf_submission_plausibility.py` (revision 3) | The flag-only checks of 14.7.2; pure functions; reads spent sets through `lpbf_spent_ledger`; returns codes and keys, never values. |
| `python/tools/lpbf_sealed.py` (revision 3) | Maintainer and reader CLI: `export-protocol [--check]`, `import`, `anchor`, `run-amendment`, `freeze`, `publish`, `receive-targets`, `intake`, `tier`, `score`, `record`, `status`, `verify`. No network; anchors (URLs, server times) are typed by the maintainer. |
| `scripts/research-route-batch.ts` (revision 3) | Explicit batch client for the P8 research route on the local server: reads a list of request bodies, runs the contract's band loop per request, writes one response file per request; authenticates with the server's bearer token when one is configured (`tokenAuth`, `server/security.ts:271`). Runs only when a person starts it (OD1). |

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
   `python/*.py`). Per-type `timeout_s` (read by `execute()` at line 1017): freeze 180 s (served calls only; research
   runs in the P8 research lane before the job is queued, 7.6 item 12), score 60 s, reveal 30 s, bundle 60 s, open 30 s,
   share 60 s, sealed commit 30 s, sealed release 60 s. Revision 3: the relayed research subsets of a freeze request are
   staged like the other documents (`uploads/<sha256>.research.json`), so `input.json` holds `researchSha256` only.
3. Child `main()`: `elif job_type in USER_BLIND_JOB_TYPES: result = run_job(input_data)`; no `write_artifacts`.
   The child's stdout and stderr are `progress.log` (`_spawn_execution_child`, line 637), which `execute()` copies
   into the sqlite `log` column (lines 1049 to 1082) and, through `_execution_failure_message`, into `error`; `GET
   /api/lpbf/jobs/:id` returns both. `run_job` is therefore silent by construction:
   (a) file descriptors 1 and 2 are redirected to `os.devnull` with `os.dup2` for the whole job (so prints from the
   solver and from C extensions are covered), and `warnings` are captured and dropped;
   (b) the only writes to the log go through one function, on a saved copy of the original descriptor, of the two
   closed forms `blind-progress <stage> <k>/<n>` (stage from a closed list, counts only) and `blind-error <CODE>`;
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
   cannot reach the sqlite `log` or `error` column or the `GET` response even if (a) fails. Timeout and cancel messages
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

Queue starvation: the worker runs one queued job at a time (`work()`, lines 997 to 1008), so a freeze delays a waiting
Build Job. The condition cap (section 4.3) is set from measured timing so that a freeze at the cap takes at most 60 s
(p95, warm worker, cold child, reference machine), and the UI states "a freeze can hold the simulation queue for up to
about a minute". Reveal, score, bundle and open make no solver call; preview, list and get are not queued at all.
Revision 3: under the P8 integration contract no served call evaluates research, so P8 adds nothing to the freeze job;
the opt-in research step runs in the research lane before the freeze is queued and never holds the worker queue (7.6
item 12). Share, sealed commit and sealed release make no solver call.

### 3.2.1 Blind request types and closed payloads

Every payload is closed (unknown keys refused, booleans real booleans), `schema` is `lpbf-user-blind-request-1`,
`freezeKey` is 64 lower-case hex, file names follow 4.2 item 10, base64 fields follow 4.3. Each result carries the
honesty block of 2.1.

| Type | Path | Payload (keys required unless marked optional) | Result |
|---|---|---|---|
| `user-blind-preview` | estimate RPC | `{jobType, schema, metadata, inputsCsvBase64, inputsFileName}` | preview (4.5 item 1) |
| `user-blind-list` | estimate RPC | `{jobType, schema, page?: int >= 0, pageSize?: int 1 to 50}` | `{entries [{freezeKey, blockLabel, alloy, createdAt, counts, state (frozen, revealed, scored), attempts, latestStatus}], total, page, readOnly, sharedHost}`; receipt fields only |
| `user-blind-get` | estimate RPC | `{jobType, schema, freezeKey}` | receipt summary, reveal events, attempts with status words, `documents [{name, attempt or null, sha256, size, jobId, jobRecordPresent}]` for the documents the state gate allows; no predicted or measured value |
| `user-blind-freeze` | queued | `{jobType, schema, metadata, inputsCsvBase64, inputsFileName, previewSha256, overlapSha256, acknowledgements, research?: {requested: true, subsets [closed subset per condition, 7.6 item 2]}}` (`overlapSha256` copied from the reviewed preview; `research` absent means not requested) | receipt (4.5 item 3) |
| `user-blind-reveal` | queued | `{jobType, schema, freezeKey, confirmation}` (exact phrase) | `{freezeKey, revealN, ledgerSeq, documents}` |
| `user-blind-score` | queued | `{jobType, schema, freezeKey, targetsCsvBase64, targetsFileName, declarations {viewedPredictionsBeforeFinalisingTargets}, acceptCommitmentMismatch}` | `{freezeKey, attempt, alreadyScored, statuses, documents}` |
| `user-blind-bundle` | queued | `{jobType, schema, freezeKey, revealConfirmation?: exact phrase}` | `{freezeKey, bundleN, sha256, size, documents}`. Refused at submit and again in the child with `REVEAL_REQUIRED` unless a reveal record or a score exists; with `revealConfirmation` the child writes `reveal-<n>.json` and the `revealed` event before the tar |
| `user-blind-open` | queued, deduplicated | `{jobType, schema, freezeKey, name (closed set of 3.2 item 7), attempt?: int >= 1}` | `{freezeKey, name, attempt, sha256, size}`; writes nothing; same state gate |
| `user-blind-share` (revision 3) | queued | `{jobType, schema, freezeKey, consent {includeTargets}, licence, publishAllowed, attribution?, evidenceManifest?}` | `{freezeKey, shareN, shareId, sha256, size, documents}`; refused with `SHARE_NO_SCORE` unless a score exists (14.3) |
| `user-sealed-precheck` (revision 3) | estimate RPC | `{jobType, schema, metadata, inputsCsvBase64, inputsFileName, targetsCsvBase64, targetsFileName, evidenceManifest?}` | structure checks of inputs and targets (4.2, 4.4), `targetsSha256` computed in Python, plausibility flags for the user only (14.7.2), counts and codes, never a value; writes nothing; no solver call |
| `user-sealed-commit` (revision 3) | queued | `{jobType, schema, metadata, inputsCsvBase64, inputsFileName, targetsSha256, evidenceManifest?, submitter?, licence, publishAllowed, confidential, declarations}` | `{commitmentId, documents}`; writes `commitments/<commitmentId>/`; refusals of 14.4.4 |
| `user-sealed-check-predictions` (revision 3) | estimate RPC | `{jobType, schema, commitmentId, predictionsJsonBase64}` | hashes, counts and identities; `PREDICTIONS_INPUTS_MISMATCH` when the file names other inputs; writes nothing |
| `user-sealed-release` (revision 3) | queued | `{jobType, schema, commitmentId, targetsCsvBase64, targetsFileName, predictionsJsonBase64}` | `{commitmentId, releaseN, documents}`; `TARGETS_HASH_MISMATCH` and `PREDICTIONS_NOT_PUBLISHED` refusals; writes `release.json` and `sealed-score-local.json` |

`USER_BLIND_RPC_TYPES` and `USER_BLIND_JOB_TYPES` are the only two sets. A test asserts that every type in them has a
closed schema, a Python validator, a TypeScript result validator and a refusal test, and that no other `user-blind-*`
type is accepted by `submit`, `submit-repeat` or the estimate RPC.

### 3.3 Tier C: Node

One change, no route change. `server/pythonRuntime.ts` forwards the blind environment to a WSL worker. Today only
`METALLIKSA_JOB_ROOT` is listed in `WSLENV` (`wslJobRootEnvironment`, lines 82 to 96), so under WSL
`METALLIKSA_READ_ONLY` and `METALLIKSA_USER_BLIND_ROOT` never reach the worker and `STORE_READ_ONLY` would fail open
(`METALLIKSA_READ_ONLY` is checked only in Node routes today: `routes/lpbfRuns.ts:16`, `routes/lpbfSources.ts:11`). The
function is generalised to forward `METALLIKSA_USER_BLIND_ROOT` with `/p` under the same drive-letter rule as the job
root (UNC and `\\wsl$` refused loudly), and `METALLIKSA_READ_ONLY`, `METALLIKSA_HOST` and
`METALLIKSA_USER_BLIND_SINGLE_USER` as plain values; it still returns a new object and never mutates `env`.
`tests/python-runtime.test.ts` gains cases for the forwarded list, and the worker reports `readOnly` and `sharedHost`
in the `user-blind-list` result so the UI and the phase 2 WSL check can see what arrived.

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
8. Revision 3.
   a. Research relay (7.6 item 2): `src/services/lpbfUserBlindClient.ts` runs the band loop per condition through
      `pythonComputationService.solveLpbfResearchModels` (the contract's client method), sequential and awaited, with
      Cancel; `src/data/lpbfUserBlind.ts` gains the closed extractor `extractBlindResearchSubset(response)` (the members
      of 7.6 item 4, `requestKey`, `identity` and `clientRequestId`; it throws on an unknown key in those members). The
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

Ledger events: `frozen`, `revealed`, `score-refused` (code only), `commitment-mismatch`, `scored`, `bundle-exported`,
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
   holder's job id when known).
2. Commit points: a freeze is committed by the rename of `.staging/<random>/` to `freezes/<freezeKey>/` (written and
   fsynced before the rename); a reveal, score or bundle is committed by the exclusive create of `reveal-<n>.json`,
   `score-<n>.json` or `bundle-<n>.tar` with its sidecar written first to a temporary name in the same directory and
   then linked into place. Servability and every state gate read the committed files, never the ledger, so a killed
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
5. Tests kill a freeze, a reveal and a score child at each step (after the staging write, after the lock, after the
   rename or exclusive create, during the ledger append, after the ledger append, during the index append) through a
   test-only fault hook (a module-level no-op function the test replaces in the spawned child, never an environment
   switch in production code), then run the next mutation and assert: no manual action needed, the record is either
   fully committed or absent, every committed record has exactly one ledger event, no dangling event, and the index
   equals the committed freezes.

### 3.6 Predictor identity and scorer identity

Predictor identity (recorded at preview, freeze and score):
`{implementationFingerprint (live lpbf_simulation.implementation_fingerprint()), pinnedFingerprint (lpbf_fingerprint_pin),
servedClosure {pinSha256, files [{path, liveSha256, pinnedSha256}]}, buildJobSolverRevision, buildJobModelId,
per-alloy materialPropertySha256, materialAuthorityRevisionSha256, buildJobIdentitySha256, research {requested,
researchPinSha256 (the content of `python/lpbf_research_identity.expected`, read as bytes, or null when the file is
absent), researchImplementationSha256 or null (from the responses, equal to the pin), researchSchemaVersion
"p8-research-v3" or null, responseSchemaVersion "p8-research-response-v1" or null, propertyContextKind,
requestKeysSha256 (sha256 of the ordered `requestKey` list) or null, researchOptions: "absent (sourced defaults)"},
heatSource "rosenthal", absorptionModel "flat-plate", includeProcessMap, python, numpy and scipy versions}`. The research
member is outside the served-closure pin. The preview carries `researchPinSha256` only, and the other research members
are filled at freeze, so ticking the opt-in never causes `PREVIEW_DRIFT`; `research.requested` enters `freezeKey`, so a
freeze with and one without the research arm differ.

Served-closure pin. `IMPLEMENTATION_SOURCE_FILES` (`python/lpbf_simulation.py:44-81`) does not cover every module the
served arm runs through, so the fingerprint alone cannot make "served" mean "the reviewed served model". A committed pin
`data/blind/served-closure-pin-v1.json` (generated and checked by `python/tools/lpbf_user_blind.py pin-served-closure
[--check]`) lists the sha256 of `python/lpbf_build_job_solver.py`, `python/lpbf_build_job_material_snapshot.py`
(`prop_overrides` snapshot), `python/lpbf_job_cache.py` (`BUILD_JOB_SOLVER_REVISION`), `python/lpbf_public_datasets.py`
(leverage index), `python/lpbf_served_arms.py` and `python/lpbf_p8_adapter.py`. An import-closure test imports
`lpbf_served_arms` in a fresh interpreter, collects every loaded module whose file lies under `python/`, and fails when
one is neither in `IMPLEMENTATION_SOURCE_FILES` nor in the pin, so a new dependency cannot slip in unpinned. The freeze
refuses with `PREDICTOR_NOT_PINNED` when the live fingerprint differs from the fingerprint pin or any closure file
differs from the closure pin (the message names the files). A closure pin change is a reviewed commit, like the
fingerprint pin. Each job runs in a fresh child process, so a stale import cannot freeze.

Scorer identity (recorded at freeze and at score, separate from the predictor identity):
`{scoreSourcesSha256 (bytes of lpbf_blind_stats.py, lpbf_user_blind_score.py, lpbf_user_blind_targets.py and
lpbf_spent_ledger.py, read by store.source_identity without importing them), statsConstants (the threshold strings,
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
| `reduction` | `per-section-raw` \| `per-track-mean-of-sections` \| `track-value-released` \| `condition-mean-released` \| `maximum-only` \| `single-selected-section` (required) | last two: block issue `reduction mismatch` (MELT `REDUCTION_UNUSABLE`) |
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
4. Closed alias table (case-insensitive, a trailing bracketed unit ignored, every mapping echoed back):
   `power_W`: `P_W`, `P`, `power`, `laser_power_W`, `Power (W)`; `speed_mm_s`: `v_mm_s`, `v`, `speed`,
   `scan_speed_mm_s`, `Velocity (mm/s)`, `Speed (mm/s)`; `spot_um`: `beam_um`, `beam_diameter_um`, `spot`,
   `Spot (um)`; `condition_id`: `condition`; `track_id`: `track`; `section_id`: `section`; `power_u_k1_W`: `P_u_k1_W`.
   `d_um` and `D_um` are deliberately not aliases (they collide with depth). Two headers mapping to one canonical name
   refuse (`AMBIGUOUS_ALIAS`).
5. Any header matching `/depth|width|height|cap|area|penetration|remelt|d_exp|w_exp|d_obs|aspect/i`, or equal
   (case-insensitive) to `d`, `w`, `D`, `W`, refuses with `INPUTS_TARGET_COLUMN`. Any other unknown header, including
   `notes`, refuses with `INPUTS_UNKNOWN_COLUMN` (an unfamiliar name may hide a measurement). The header line is
   checked before any data row is parsed (runner `FileInputSource` and `TargetColumnRequested` design).
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
calls), derived in phase 0 from timing and set in phase 1 so that a freeze at the cap takes at most 60 s p95. Revision 3:
P8 adds no cost to the freeze job (7.6 item 12), so there is one served cap, not one per research state. The opt-in
research step runs in the research lane before the freeze is queued; its time per condition comes from the contract's
phase C measurements, the preview shows the estimate for the block, and phase 6 records it. Research request bodies
are at most 65,536 bytes each (contract 3.1) and the relayed subsets of one freeze stay under the RPC line cap at the
condition cap (checked in phase 6 against real responses). A larger campaign is split into blocks; each block needs at
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
   when `depthUncertainty.basis` is `per-row`; constant within a condition, else refused, MELT rule). Range checks
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
   `acknowledgementsRequired[]`, budget `{conditions, solverCalls, cap, estimate_s, researchEstimate_s or null}`,
   divergences that apply, `researchRequests` (revision 3: the closed request bodies of 7.6 item 2, inputs only, or
   empty when the research pin is absent), honesty. Leverage is reported as bin counts only, never per-condition index
   values. No predicted depth.
2. Freeze record (`lpbf-user-blind-freeze-1`, on disk only): `freezeKey = sha256(canonical {protocolId, metadata,
   canonical input rows, predictorIdentity})` (createdAt excluded, so re-freezing identical inputs returns the same
   record); `createdAt` (local clock, stated as unverified); metadata; `metadataSha256`, `inputsSha256` (raw bytes),
   `previewSha256`; `columnsLoaded`; `targetColumnsRead: false`; rows `[{ordinal, condition, track, section, P_W,
   v_mm_s, d_declared_um, beamQuantity, beamDefinition, d_1e2_um, conversion, P_u_k1_W, indexUnrounded, indexBin}]`;
   per condition `pred {served, "served:P-5%", "served:P+5%", "served:d-5%", "served:d+5%", "research:melt-link",
   "research:cavity", "context:fabbro"}`, each `{value_um, status ok|failed|unavailable, reasonCode, reasonClass,
   extentStatus, warnings[]}`, research arms also `requestKey`, `sourceEvidenceKind` with `weakestInputs`, `band` (the
   `p8-research-v3` fields of 7.6 item 7, with `manifestSha256` in place of the descriptor list; the cavity band's
   `statusSupport` on `research:cavity`) and `consistencyNote` (the fields of 7.6 item 4); served and research values
   carry `sourceEvidenceKind` and `sourceLocator` (14.6); acknowledgements; excluded inputs; design checks; grades; block issues; labels; predictor identity; scorer
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

### 4.6 Protocol record

`data/blind/lpbf-user-blind-protocol-v1.json`, generated by `python/tools/lpbf_user_blind.py export-protocol` and
checked with `--check`: protocol id, vocabularies, alias tables, regexes, caps, thresholds as exact decimal strings, arm
catalogue, the P8 reason-code class table (7.6 item 5), the declared divergence list with ids and rules (7.7), the
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
   wordingSha256}`. No target value, no flag, no micrograph.
2. `commitment-public.json` (`lpbf-sealed-commitment-public-1`, confidential variant, 14.4.5): `commitmentId`, the
   hashes, alloy, condition count, licence `none`, `confidential: true`, public identity fields.
3. `run-amendment.json`: exactly the closed key set of MELT Amendment 6 item 14.4 (`whitelist`, `served_commit`,
   `p1_commit`, `p3_verdict_commit`, `constants_amendment`, `candidate_arm`, `beam`, `powder_absorptance_or_p5_bias`,
   `datum_statement`, `track_section_protocol`, `grades`, `cavity_physics_statement`, `exposure_exclusions`,
   `data_hashes`), filled from the commitment metadata plus the maintainer's sourced sensitivity beams where the beam is
   nominal; `data_hashes` holds `commitmentId`, `inputsSha256`, `targetsSha256` and `evidenceManifestSha256`.
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
    `sealedDepartures` (SD1 to SD3).
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
   post-measurement mode the user may pick the targets file too: the browser computes its sha256 with SubtleCrypto over
   the raw bytes (same value as `sha256sum` or `certutil`) and puts only the hash in `targetCommitment`; the file never
   leaves the browser at this step. Without a secure context the user pastes the hash instead (3.4 item 5). A
   third-party custodian can supply the hash instead.
3. Preview: `POST /api/lpbf/estimate {jobType: "user-blind-preview", schema, metadata, inputsCsvBase64,
   inputsFileName}`. Python validates closed keys, metadata, header whitelist (before rows), structure and caps;
   computes grades, block issues, labels, design checks, index-bin counts, overlap with tests on this computer that were
   revealed or scored and with the calibration stores (6.4 item 7, from phase 4), the best reachable status and the
   required acknowledgements; returns `previewSha256` (4.5 item 1). Writes nothing, calls no thermal solver.
4. Review (browser). Shown before anything is frozen: `Best reachable outcome: inconclusive (atmosphere not stated;
   single-track conditions need at least 3 replicated conditions)`, each block issue with how to fix it, the labels,
   the declared divergences that apply, the overlap list (the user may drop overlapping conditions now; deciding from
   inputs before freeze is legitimate), and the acknowledgement boxes. Revision 3: the research opt-in box (2.2),
   unticked, with the estimated research time; when ticked, pressing Freeze first runs the research step of 7.6 item 2
   in the research lane (progress `research <k> of <n> conditions`, Cancel leaves the arm `RESEARCH_NOT_REQUESTED`),
   then submits the freeze with the subsets. Nothing is shown from the responses.
5. Freeze submit: `POST /api/lpbf/jobs {jobType: "user-blind-freeze", schema, metadata, inputsCsvBase64,
   inputsFileName, previewSha256, overlapSha256, acknowledgements}`. `acknowledgements` is a top-level request field, outside
   `metadata`, `metadataSha256` and `previewSha256` (4.1). Python (submit) re-runs the preview; first compares the live
   overlap with the reviewed `overlapSha256` (`OVERLAP_CHANGED`) and the live required acknowledgements with the ticked
   ones (`ACK_REQUIRED`), so the message says what changed; then refuses any other drift with `PREVIEW_DRIFT`; stages the
   canonical metadata and raw inputs bytes by hash; enqueues a job whose `input.json` holds hashes only.
6. Freeze (child). Silent child (3.2 item 3). Verify uploads by hash; re-run the preview; check the live fingerprint
   and the served-closure pin (3.6); for every condition compute the served arm and four sensitivity arms; parse the
   relayed research subsets through the adapter with the identity checks of 7.6 item 3 (`RESEARCH_CONTRACT_BROKEN` or
   `RESEARCH_RELAY_INCOMPLETE` refuse; no research is computed here); `assert_no_target_loaded`; record `columnsLoaded` and
   `targetColumnsRead: false`; compute `freezeKey`. If `freezes/<freezeKey>` exists, verify its sidecar and return the
   receipt with `alreadyFrozen: true`. Else write `freeze.json` (mode `x`) and its sidecar into `.staging/<random>/`
   and fsync; take the store lock and reconcile (3.5); re-derive the required acknowledgements and the overlap against
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
    row numbers and column names (never values); ledger `score-refused` with the code; no attempt is created, so fixing
    a malformed file burns nothing. A commitment mismatch refuses (`COMMITMENT_MISMATCH`) unless
    `acceptCommitmentMismatch` is true, in which case the score proceeds and the report says `commitment declared
    before freeze was not matched` (status falls back from `blind-committed` to `blind-retrospective-declared`, never
    better). Then stage the raw targets bytes and enqueue.
11. Score (child). Silent child. Load `freeze.json`, verify the sidecar and recompute `freezeKey` from content; refuse
    on mismatch (`FREEZE_ALTERED`). Read the live predictor and scorer identities (never recompute predictions; refuse
    on `PROTOCOL_CHANGED`). Join targets; apply 4.4 item 2 (not-formed tracks counted as misses, measurement losses
    excluded and counted at three levels); reduce sections to tracks to conditions (`reduce_conditions`, sections never
    replicates). Attempt ledger: an earlier score with the same `targetsSha256` is returned as is (idempotent, no new
    attempt); otherwise attempt `n = max + 1`. Statistics, coverage, common subset, qualifiers, labels and status per
    arm (section 7); blindness (6.4); under the store lock write `score-<n>.json` and sidecar exclusive (the commit
    point), then ledger `scored`. The job result declares `blind-report.json`.
12. Report (browser). Fetch through the artifact route, check sha256 (or show the secure-context note), validate with
    `checkedBlindReport`, render.
13. Later visits (browser). `user-blind-list` and `user-blind-get` on the estimate RPC load the tests and their
    documents without queueing; a document whose writing job folder is gone is fetched through `user-blind-open`.

Server-enforced: closed schemas and header whitelists in both phases; targets absent from the server until a freeze
exists; the freeze process cannot import the targets parser (AST test) and never opens a targets path (open audit test);
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
every test (9.7). Revision 3: the research values pass through the user's browser on their way to the freeze; they are
not rendered, but a user with developer tools can read them, as they can run the Research model panel at any time, so
this is declared (D13), not prevented.

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
| `INPUTS_TARGET_COLUMN` | `Column '<name>' looks like a measurement. The inputs file carries inputs only; put measurements in the targets file.` |
| `INPUTS_UNKNOWN_COLUMN` | `Column '<name>' is not an input column. Allowed: condition_id, track_id, section_id, power_W, speed_mm_s, spot_um, power_u_k1_W, or a listed alias.` |
| `AMBIGUOUS_ALIAS` | `Columns '<a>' and '<b>' both mean <canonical>. Keep one.` |
| `FILE_NOT_CSV_UTF8` | `This file is not UTF-8 CSV text (it may be an Excel workbook). In Excel use Save As, CSV UTF-8.` |
| `DIALECT_MISMATCH` | `Row <n>, column <col>: decimal comma found, but the declared format is comma separated with decimal points. Choose "semicolon separated, decimal comma" or re-export.` |
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
| `PREDICTOR_NOT_PINNED` | `The running solver does not match the reviewed served model (<fingerprint or file list>), so predictions cannot be frozen from an unreviewed build.` |
| `PROTOCOL_CHANGED` | `The protocol rules changed since this test was frozen under the same protocol id. This test cannot be scored by this build.` |
| `RESEARCH_CONTRACT_BROKEN` | `The research results do not match the pinned P8 research contract (<check>). Nothing was frozen.` (child; check ids of 7.6 item 3; for `RESEARCH_CODE_STALE` the message adds `Restart the server and run the research step again.`) |
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
| `RESEARCH_RELAY_INCOMPLETE` (rev. 3) | `The research step did not finish for every condition. Run it again, or freeze without the research arm.` |
| `SHARE_NO_SCORE` | `Share a test after it has been scored.` |
| `SHARE_ATTRIBUTION_REQUIRED` | `CC BY 4.0 needs a name or pseudonym for attribution.` |
| `SHARE_VERIFY_FAILED` (maintainer CLI) | `Check <id> failed: <check sentence>. Nothing was imported.` |
| `SEALED_PREDICTIONS_VIEWED` | `A sealed submission needs data whose predictions you have not viewed. Run a local test or share your result instead.` |
| `SEALED_DATA_PUBLISHED` | `Published data cannot be a sealed submission.` |
| `SEALED_CALIBRATION_OVERLAP` | `These conditions were used for machine calibration on this computer (<store id>), so they cannot be a sealed submission.` |
| `SUBMISSION_SCHEMA`, `SUBMISSION_ID_MISMATCH`, `SUBMISSION_PROTOCOL_UNKNOWN`, `SUBMISSION_INPUTS_CHANGED`, `SUBMISSION_DATA_EXPOSED`, `SUBMISSION_STATE` (maintainer CLI) | one sentence each naming the field, hash or state, never a value (14.4.4) |
| `TARGETS_HASH_MISMATCH` | `This targets file does not match the hash in your commitment. Only the committed file can be scored.` |
| `TARGETS_RELEASED_EARLY` (maintainer CLI) | `The targets were released before the predictions were published, so this is not a sealed test.` |
| `PREDICTIONS_NOT_PUBLISHED`, `PREDICTIONS_INPUTS_MISMATCH`, `PREDICTIONS_ALTERED`, `PREDICTIONS_DUPLICATE` | `Check the published predictions file first.` / `This predictions file is for other inputs. Do not release your targets; contact the maintainer.` / `The published predictions differ from the frozen file.` / `This commitment already has a predictions file.` |
| `EVIDENCE_HASH_MISMATCH` | `<k> evidence files do not match the committed hashes; they cannot support a tier above Declared.` (listed, not a refusal of the score) |
| `TIER_REVIEWER_NOT_APPROVED`, `TIER_REQUIREMENT_MISSING` (maintainer CLI) | `<id> is not an approved reviewer.` / `Tier <t> needs: <list>.` |
| `SEALED_SCORER_DISAGREEMENT` (maintainer CLI) | `The app's recomputation differs from the MELT runner for <arm>. The result is not recorded.` |

A child job ends with one code from the closed `BLIND_CHILD_ERROR_CODES` table: the codes above that can arise after
submit (`PREVIEW_DRIFT`, `ACK_REQUIRED`, `OVERLAP_CHANGED`, `PREDICTOR_NOT_PINNED`, `PROTOCOL_CHANGED`,
`RESEARCH_CONTRACT_BROKEN`, `RESEARCH_RELAY_INCOMPLETE`, `FREEZE_ALTERED`, `REVEAL_REQUIRED`, `SHARE_NO_SCORE`,
`TARGETS_HASH_MISMATCH`, `PREDICTIONS_NOT_PUBLISHED`, `STORE_*`) plus `SOLVER_EXCEPTION` and `INTERNAL_ERROR`. The job's `error` text is the code's fixed message, never an exception message (3.2 item 3).

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

### 6.5 Plausibility flags (revision 3; never refusals)

The checks of 14.7.2 produce flags, not codes of 6.1: they never refuse a file, block a step or change a statistic.
They are shown to the user at precheck and before a share, recorded at maintainer intake, printed in sealed and shared
records with their codes and keys, and decide only whether a tier above Declared can be granted (14.7.3).

## 7. Scoring

### 7.1 Arms

| Arm | Source | Scored |
|---|---|---|
| `served` | Build Job thermal call (`lpbf_served_arms.served_arm`); IN625 direct thermal path, labelled | yes |
| `served:P-5%`, `served:P+5%`, `served:d-5%`, `served:d+5%` | same call with perturbed power or 1/e2 beam (no served call evaluates research, 7.6 item 12) | only for the input-fragile label |
| `research:melt-link` | `p8-research-v3` `meltDepthLink.fields.linkedMeltDepth_um` from the opt-in research route (7.6 item 2), with its `band` and the module `consistencyNote` (conditional and conduction depths, `controllingLeg` and `conductionMeltState` carried as context); alloys outside the admitted chains give `ALLOY_CONSTANT_CHAIN_NOT_ADMITTED`, read from the response | yes, side by side, never changes served labels |
| `research:cavity` | `p8-research-v3` `keyholeCavity.fields.cavityDepth_um` with its band and onset support | only against `vapour-depression-depth`, descriptive in protocol 1; otherwise shown with `OBSERVABLE_MISMATCH` (goal deviation G1, 7.7) |
| `context:fabbro` | served `keyholeModel.fabbroDepth_um` | never |

A failed prediction (served `extentStatus` not `computed`, a served exception, a research code of class `failed`)
counts as APE +inf and is never dropped. A condition with a not-formed track counts as APE +inf for every arm (4.4
item 2a). An unavailable research value is listed with its code and left out of that arm's n; the coverage label and
the common-subset statistics (7.6 item 5) keep that from flattering the research arm.

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

`unavailable` applies to a research arm with no in-scope condition (`P8_NOT_IN_THIS_BUILD`, `RESEARCH_NOT_REQUESTED`,
schema unknown or malformed, alloy chain not admitted, every condition outside the numerical scope). Each status maps to one plain sentence (2.2) plus the label
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
printed as a predictor note in the collapsed predictor section. Revision 3 adds: `research arm not requested`; `model
predicted no melt track in <k> conditions` (7.6 item 5); `envelope arms extrapolated or out of range in <k>
conditions`; per value the `sourceEvidenceKind` badge (`Measured`, `Literature estimate`, `User input`, `Unresolved`
with the inputs named, 14.6); in sealed and shared records the tier badge, `descriptive only (tier Declared)`, the flag
counts, `same rules, not the registered candidate`, `confidential sealed test: third parties cannot re-score it`, and
`order: local-ledger-only` or `order: anchored <time>`.

### 7.6 Served versus the P8 research arm (contract: P8 integration contract, `research/p8-research-arm` `29ae2183`)

Revision 3 replaces the revision 2 text of this section. That text assumed a P8 served bump that would put
`researchModels` into every `calculate_meltpool_physics` result, a `research_models=False` solver switch for the
sensitivity calls, and the `p8-research-v2` block read from `thermal.researchModels`. The integration contract
(`docs/research/SPEC_p8_integration_contract_2026-10-15.md` at `29ae2183`, aligned with P8 Amendment 2 `1c76a2fd`, a
proposal for the P8 re-gate) supersedes those parts of the P8 spec, and this section follows it. (a) P8 is not a served
bump: `calculate_meltpool_physics`, the Build Job path, the 36 manifest files, the fingerprint pin, the goldens,
`BUILD_JOB_SOLVER_REVISION` and the job cache key stay byte-identical whether research runs or not (contract 0 and
10.1). (b) Research is computed only when `POST /api/python/lpbf-research-models` receives an explicit request, by
`python/lpbf_research_models.py` in its own single-process IPC lane (contract 1 and 3); no served route, worker job or
internal caller computes it, and no module outside `lpbf_research_*` imports a research module (guard R-ISO-1). (c)
Request `p8-research-request-v1`, response `p8-research-response-v1`, block schema `p8-research-v3` with the names of
contract 7, the provenance of contract 6 and the reason classes of contract 9.

The contract is being revised on the same branch (P8 Amendment 3, `78607f3e`, scenario provenance and secondary-alloy
manifests). This section depends only on the committed contract plus the two facts above; arm counts, arm names and
leaf provenance are read from each response, never pinned here.

1. Nothing waits for a P8 bump. The served arms (7.1) never change because of P8; the served-closure pin and the served
   part of the predictor identity do not move when the research route lands. The research arm becomes available when the
   contract's phases B to E land (route, lane, evaluator, types), with no served parity event.
2. Research values reach the blind test through the route only, on explicit request. The review step offers `Include
   the research arm (runs the research models for every condition; values stay hidden until scoring)`, unticked by
   default. The preview returns the closed list `researchRequests` (4.5 item 1): one request body per condition, inputs
   only: `process {material, laserPower_W, scanSpeed_mm_s, beamDiameter_um (the 1/e2 value), preheatTemp_C,
   laserWavelength "IR_1064nm", absorptionModel "flat-plate"}`, `propertyContext {kind "build-job-snapshot", alloyId,
   materialPropertySha256}` equal to the served arm's snapshot (`{kind "nominal"}` for IN625), no `researchOptions`,
   `supersedeKey "p8-research:blind-test"`, `clientRequestId "blind:<ordinal>:<first 16 hex of previewSha256>"`. After
   the user ticks the option and presses Freeze, the client runs the contract's band loop per condition (`stage "band"`,
   budget 1500 ms, each request awaited, until `progress.complete`; the contract 3.5 rule 6 fallback to one request with
   `timeBudgetMs: null`; one retry after a timeout), then passes each complete response through the closed extractor
   `extractBlindResearchSubset` (3.4 item 4) into the freeze request. The client never renders, stores or logs a research
   value. The freeze child parses the subsets through the adapter and binds them into `predictionsSha256` before any
   target reaches the server. The worker never imports a research module and never calls the route, so research cost
   never holds the worker queue. This relay is declared divergence D13 (7.7). Without the option the arm is `unavailable`
   with `RESEARCH_NOT_REQUESTED`. The CLI takes the same subsets from response files written by the explicit batch client
   `scripts/research-route-batch.ts` (`freeze --research-responses <dir>`), which the maintainer also uses for Mode A
   reruns, Mode B and the descriptive record. Admitting the blind tab and the batch client as senders is open dependency
   OD1 (section 13).
3. Identity checks in the freeze child; any failure refuses with `RESEARCH_CONTRACT_BROKEN` and the check id, and nothing
   is written: every subset comes from a response with `success true`, `schemaVersion "p8-research-response-v1"`,
   `identity.researchSchemaVersion "p8-research-v3"`, `progress.complete true`, a non-null block and the expected
   `clientRequestId`; one `identity.researchImplementationSha256` across the block, equal to the committed research pin
   `python/lpbf_research_identity.expected` (read as bytes, no import; absent file: research option disabled with
   `P8_NOT_IN_THIS_BUILD`); `identity.servedImplementationFingerprint` equal to the live fingerprint and the fingerprint
   pin (3.6); `identity.propertyContextKind` as requested; no arm descriptor of family `user-endpoint`, no input
   provenance of kind `userInput`, and `band.totalArms` equal to the length of `band.manifest`. A request-level refusal
   (class C1: `RESEARCH_REQUEST_INVALID`, `PROPERTY_SNAPSHOT_MISMATCH`, `RESEARCH_CODE_STALE`,
   `RESEARCH_RESPONSE_TOO_LARGE`) or a request-scope failure envelope refuses the same way; `RESEARCH_CODE_STALE` adds
   the instruction to restart the server. The research identity is recorded in the predictor identity (3.6).
4. Adapter `python/lpbf_p8_adapter.py`, `P8_ADAPTERS["p8-research-v3"]` (closed; no v1 or v2 entry). From the block it
   reads the scored leaf `meltDepthLink.fields.linkedMeltDepth_um` (`value`, `reasonCode`, `warnings`, `evidenceKind`,
   `leafRole`, `weakestInputs`, `band`), the context leaves `conditionalMeltDepth_um`, `conductionDepth_um`,
   `controllingLeg`, `conductionMeltState`, `floorFieldModelId`, `floorExtractorId`, the descriptive leaf
   `keyholeCavity.fields.cavityDepth_um` with its band, the onset support `statusSupport` of `keyholeCavity.band` (onset
   support lives only there, contract 5.5), `meltDepthLink.consistencyNote` (`status`, `worstArmStatus`, the primary
   sentence verbatim, `knownContradictions[].id`, `reasons[].code` with `fieldPaths`, `onsetMismatch.comparison`) and
   the `labels` entries of those paths. Route absent from the build: `P8_NOT_IN_THIS_BUILD`. Option not ticked:
   `RESEARCH_NOT_REQUESTED`. Another block `schemaVersion`: `RESEARCH_SCHEMA_UNKNOWN`. A block that fails the closed check
   (seven containers, contract 7 names, no extra keys, band and note present on the four modules, no `pending` band in a
   complete response): `RESEARCH_BLOCK_MALFORMED`. These four are `unavailable` for every condition. The adapter never
   guesses or fills a value.
5. Reason-code classes (closed table in the protocol record, from contract 9.1; Astra signs off the split in phase 0):

   | Class here | Codes on the scored leaf | Scoring |
   |---|---|---|
   | failed: inside the declared scope, no value | C8 (`CYLINDER_CONVERGENCE_FAILED`, `OPTICAL_TRACE_UNRESOLVED`, `CAVITY_ROOT_SCAN_UNRESOLVED`, `CAVITY_RESIDUAL_FAILED`, `NO_STRICTLY_STABLE_ROOT`, `CONDUCTION_EXTENT_UNRESOLVED`, `MELT_BRACKET_FAILURE`, `MELT_OPTIMIZER_FAILURE`, `MELT_CONVERGENCE_FAILED`, `TIP_SHELL_UNRESOLVED`, `NONFINITE_RESULT`), C2 `RESEARCH_EVALUATION_FAILED`, and any code not in the contract registry (`RESEARCH_REASON_UNKNOWN`) | APE +inf, in n, never dropped |
   | unavailable: outside the declared scope | C4 `ALLOY_CONSTANT_CHAIN_NOT_ADMITTED`, `UNSOURCED_PROPERTY_OVERRIDE`; C5 (`INVALID_INPUT`, `PREHEAT_OUTSIDE_PROPERTY_SCOPE`, `WAVELENGTH_UNSUPPORTED`, `POWDER_CONTEXT_UNSUPPORTED`, `PECLET_OUTSIDE_NUMERICAL_SCOPE`, `ASPECT_BOUND_OUTSIDE_NUMERICAL_SCOPE`, `NUMERICAL_INPUT_BELOW_FLOOR`, `VAPOUR_PRESSURE_OUTSIDE_SOURCE_RANGE`); C6 `ONSET_REFERENCE_UNAVAILABLE`; client `RESEARCH_TIMEOUT` after one retry (an infrastructure event, not a model answer) | out of n, listed, counted in coverage |
   | inherited | C7 `MELT_LINK_NOT_AVAILABLE` | the class of `keyholeCavity.fields.cavityDepth_um.reasonCode` |
   | never on the scored leaf | other C7 codes (`NOT_APPLICABLE_BELOW_ONSET`, `NOT_APPLICABLE_FOR_CONVENTION`, `ONSET_COMPARISON_EVENT_MISMATCH`), C9, C10, other C6 codes, `ALLOY_NOT_ALSI10MG`, a W code used as `reasonCode` | `RESEARCH_BLOCK_MALFORMED` |
   | refuses the freeze | C1; C3 (`RESEARCH_OPTIONS_INVALID`, `RESEARCH_PRESET_ALLOY_MISMATCH`, `SURFACTANT_BINARY_COMBINATION_UNSUPPORTED`, `RESEARCH_ARM_LIMIT_EXCEEDED`; impossible with `researchOptions` absent) | `RESEARCH_CONTRACT_BROKEN`, nothing written |

   W codes stay warnings; the counts of `THERMAL_CYLINDER_CLOSURE_EXTRAPOLATED` and `VAPOUR_PRESSURE_EXTRAPOLATED` become
   labels. A linked depth of exactly 0 um with `conductionMeltState "resolved-no-melting"` is a result, not a failure
   (contract 7.2): on a formed track it scores APE 1; on a condition whose tracks did not form it is listed as `model
   predicted no melt track` and kept out of that arm's APE statistics with the count printed, the one exception to the
   D11 miss rule (Astra confirms in phase 0). `UNSOURCED_PROPERTY_OVERRIDE` should not occur: the Build Job snapshot
   resolves to the nominal tuple for the four Build Job alloys (contract 3.8); an occurrence is an integration finding.
6. Coverage and common subset: unchanged. The research arm's n counts conditions with a value or a failure; unavailable
   conditions are listed with codes; `scored on k of n conditions`; statistics also on the common subset; the research
   status needs n >= 12 inside its scope; k = 0 gives `unavailable`.
7. Bands. Per condition the freeze records the scored leaf's band: `completeness` (`complete`, `partial` or
   `unavailable`; `pending` is refused by item 4), `min`, `nominal`, `max`, `successfulArms`, `totalArms`, `method`,
   `minArmId`, `maxArmId`, `minArmTies`, `maxArmTies`, `failedArms`, and the sha256 of the canonical `band.manifest`
   descriptor list (the descriptors stay in the response). The report gives `bandCoverage {complete {inside, total,
   wilson95}, partial {inside, total, failedArms}, unavailable}` as in revision 2 (complete and partial never merged;
   Wilson 95 % interval from `lpbf_calibration_stats.wilson` on the complete count). Band text follows contract 4.7: the
   caption "Min / nominal / max is an envelope of named one-at-a-time scenarios. Interactions are not evaluated. It is not
   a confidence interval, an error bar, or a physical lower or upper bound." under every band; three numbers, never
   "nominal plus or minus x"; extremes named by their arm labels with provenance. The cavity band's `statusSupport` is
   summed into the label `envelope arms extrapolated or out of range in <k> conditions`. `band-fragile` as in revision
   2. Research input fragility is read from the process arms of the cavity manifest (contract 5.1), never from extra
   calls.
8. Consistency notes: per condition the freeze records the fields of item 4. The report counts `status` (`inRange`,
   `extrapolated`, `outOfRange`) and `worstArmStatus`, prints each distinct primary sentence once with its condition
   count, and lists `onsetMismatch.comparison` counts. An `outOfRange` note does not remove a present value from scoring.
9. Labels (decision items 1 and 2 of 2026-10-15, 14.6): each research value carries `sourceEvidenceKind` copied from the
   leaf's `evidenceKind` under the maintainer rule (`Literature estimate`, `User input` naming inputs, or `Unresolved`
   naming inputs, `Unresolved` first), with `weakestInputs`, plus `moduleMaturity "Research"`, the `validationStatus`
   text (Q2) and `experimentalValidation false`, copied, never retyped; the document ceiling stays `screening-only`.
   Leaf labels come from the response `labels` map (contract 7). These decisions settle the contract's M-1 and M-2.
10. Paired comparison (phase 6): unchanged; exact one-sided sign-flip test of research versus served APE on the common
    subset, descriptive, never a verdict.
11. Goal deviation G1 (7.7): unchanged; `keyholeCavity` is never scored against melt-pool depth.
12. Cost. The worker freeze runs served calls only: 5 per condition. The revision 2 plan (18 or 24 research arm
    evaluations inside every served call, a solver switch for the sensitivity calls, caps per research state) is void,
    because no served call evaluates research. Research cost lands in the research lane before the freeze is queued, so
    it never delays a Build Job; it can delay a Research model panel request, whose status line already shows queueing.
    Per-condition research time comes from the contract's phase C measurements (P-7); the preview shows the estimate and
    the condition count, and the UI allows cancelling the research step, which leaves the arm `RESEARCH_NOT_REQUESTED`
    (all conditions or none; a partial relay is refused, `RESEARCH_RELAY_INCOMPLETE`). Manifest sizes come from each
    response (contract 5.1 gives, at 200 W, 21 Ti-6Al-4V and 26 AlSi10Mg cavity and link arms; Amendment 3 may change
    them).
13. Integration check (phase 6, Astra and a fresh Opus gate): the adapter against real route responses and against the
    contract fixture `tests/fixtures/lpbf-research-response-v1.json` (R-TR-11), copied into `python/fixtures/` with its
    blob hash; the class table against `lpbf_research_codes.py`; the absence of `UNSOURCED_PROPERTY_OVERRIDE` on the
    Ti-6Al-4V and AlSi10Mg parity conditions; served bytes unchanged while a research relay runs (contract P-5 and P-6).
14. Removed by revision 3: `research_arms(thermal)`, `P8_ADAPTERS["p8-research-v2"]`, the fixture
    `p8_research_v2_synthetic.json`, the `research_models=False` switch, and the per-research-state condition caps (3.1,
    4.3, 10.1, 11.1, 12).

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
| D12 | no MELT counterpart | band coverage and consistency counts (7.6 items 7 and 8) are reported descriptively | P8 `p8-research-v3` output, no threshold attached |
| D13 | MELT section 6 item 6: every arm's prediction is written by the prediction process before scoring | the research arm is computed by the P8 research route on the user's explicit request and relayed by the browser into the freeze, where it is bound by hash before any target reaches the server; the worker cannot recompute it; a Mode A rerun or a maintainer batch reproduces it from the recorded requests (7.6 item 2, 14.3.4 item 7) | the P8 integration contract allows research only through its own opt-in route, never inside a worker job |
| G1 | GOAL roadmap item 1: served and P8 (`keyholeCavity`, `meltDepthLink` with bands) side by side | `keyholeCavity` not scored against melt-pool depth (7.6 item 9) | evidence rule 4 |

## 8. Descriptive panel on spent sets

### 8.1 Admission

1. `data/benchmark/spent-ledger-v1.json` (schema `lpbf-spent-ledger-1`), transcribed from
   `MAIN/.orchestra/reports/blind_validation_inventory_2026-10-11.md` section 1 plus BOARD and LOG corrections (CMU
   EXPOSED and UNUSABLE; Totis equals the Udine Mendeley set; Gan Data 1 Ti64 is the same experiments as Cunningham;
   Gan Data 1 Al6061 and SS316 SPENT by p2-onset). Entry: `{datasetId, title, doi, alloy, observable
   (fusion-boundary-depth | vapour-depression-depth | keyhole-boundary-depth), datum, beam {value_um, definition,
   status stated|assumed|unverified, sensitivity_um, locator}, powerBasis, substrate, digitized, status
   SPENT|EXPOSED|EXPOSED-LOW|CLEAN|UNUSABLE, spentBy [{event, record, date}], sameExperimentsAs, loader, tableSha256,
   curveAxis speed|power, locator}`. Haiku transcribes, Opus reviews against BOARD and LOG.
2. The producer admits only `SPENT` entries. A forbidden-id test keeps out `bitharas`, `leis`, `hyer`, `aboulkhair`,
   `ruckh`, `gong`, `ullah`, `wimmer`, `huang`, `ku-leuven-in718`, `hann`, `nist-mds2-2923-in718` and `cmu`.
3. Zhao (EXPOSED) enters only through a separate maintainer-approved ledger commit that records this panel as its
   spending event (Q3). The NIST mds2-2923 IN625 regime ledger (70 units) enters only after a
   `LICENSE-ATTRIBUTION.md` with the NIST statement and locator is committed and reviewed by Opus.

### 8.2 Sets in v1

| Set | Loader | Observable | Compared arms | Context and notes |
|---|---|---|---|---|
| NIST AMB2022-03 IN718 Table 4 (7) | `table4-aggregate-v2.json` loader used by `lpbf_process_window` | fusion-boundary depth, width | served (IN718 Build Job), research melt-link | D4sigma beams |
| NIST AMB2018-02 IN625, Lane Table 3 (23) | `lpbf_public_datasets.load_lane_in625` | fusion-boundary depth, width | served (IN625 direct path), research melt-link | `POWER_NOMINAL`, `LEGACY_PROPERTIES_IN625`, two-class cut 13.6 |
| KU Leuven 316L (44) and Ti64 (14) | `load_ku_leuven_316l_ti64` | fusion-boundary depth, width | served, research melt-link | beam 37.5 um `unverified` plus a 75 um sensitivity curve |
| Totis Ti64 (80) | `load_totis_ti64` | depth, width | served, research melt-link | beam 50 um 1/e2 per loader note; `DATUM_UNSTATED` (reference line not stated, existing caption) |
| Cunningham Ti64 (69, digitized) | `lpbf_keyhole_literature.load_cunningham_depths` | vapour-depression depth | research cavity; served Fabbro depth (the quantity `lpbf_keyhole_benchmark.py` uses, Astra confirms) | served melt-pool depth as dotted context with `different quantity: melt-pool depth versus vapour-depression depth`; read uncertainty bars; `THRESHOLD_DERIVED_FROM_THIS_SET` (cut 20) |
| Gan Data 1 Ti64 (71) | `load_gan_data1_ti64` | keyhole depth | as Cunningham | `SAME_EXPERIMENTS_AS cunningham-ti64-2019`, not independent, never added to Cunningham's n in the model map (8.3 item 4); spot labels 88 and 110 versus Methods `BEAM_ASSUMED_OR_UNVERIFIED`; the 5 printed Al6061 cases are left out (no served Al6061 model) |
| Zhao Ti64 (20 boundary depths) | `load_zhao_boundary` | keyhole boundary depth | as Cunningham | only after Q3; pore markers never plotted as depths |

Hofmann stays in the existing comparison view.

### 8.3 Computation (Python only, `python/tools/lpbf_spent_descriptive.py`)

1. Load rows through the pinned loaders with hash verification; predictions through `lpbf_served_arms` (the same served
   definition as the blind test), flat-plate pinned as in `pin_flat_plate(allow_raytracer=False)` of
   `python/tools/lpbf_dataset_comparison.py:79` (a tools module with that signature; `lpbf_calibration_stats.py:33` and
   `lpbf_powder_layer_analysis.py:69` have their own zero-argument versions, which are not used). Revision 3: research
   curves come only from route responses written by the explicit batch client `scripts/research-route-batch.ts`
   (`--research-responses <dir>`), parsed by the same adapter with the identity checks of 7.6 item 3; the producer
   imports no research module. Every measured value carries `sourceEvidenceKind: "Measured"` with `transcription` and
   its locator, every model value its own kind (14.6).
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
   `INDEX_OUTSIDE_SERVED_BAND`, `P8_NOT_IN_THIS_BUILD`, `OUT_OF_RESEARCH_SCOPE`. A note appears only when its rule
   holds and, for a signed reason, the observed sign matches; otherwise the card says `No catalogued explanation`.
   Every sentence starts `Candidate explanation, not tested:`.
6. Output: full JSON plus slim `docs/LPBF_SPENT_DESCRIPTIVE_<date>.view.json` (schema
   `lpbf-spent-descriptive-view-1`, canonical JSON, 6 significant digits, under 150 KB raw): `generatedAt`,
   `implementationHash`, `servedIdentity`, `researchSchemaVersion` (`p8-research-v3`) with `researchImplementationSha256`
   and the research pin, `spentLedgerSha256`, `reasonsCatalogSha256`,
   `honesty`, `arms`, `sets [{provenance, spent, observable, beam, groups [{fixed, curve, points}], deviation, notes}]`,
   `modelMap`. `servedIdentity` includes the served-closure pin sha256 (3.6). `--check` re-derives and compares; a
   Python test fails when `implementationHash` differs from the live fingerprint (leaderboard pattern), so the record
   is regenerated in every bump batch. The tool prints counts and hashes only.
   CI scope (decided): the full `--check` re-derivation stays out of CI, like the P7b bit-exact parity goldens (the
   `ci.yml` comment above the fingerprint step), because 6-significant-digit floats from a solver run can differ
   across machines and library builds. CI runs the structure-and-hash test only (schema, honesty literals, SPENT-only
   ids, ledger and catalogue sha256, `implementationHash` equal to the pin, size cap). The re-derivation runs locally in
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
4. Research columns read `unavailable: P8_NOT_IN_THIS_BUILD` until the research route lands and the maintainer has run
   the explicit batch (no served bump is involved, 7.6). With `p8-research-v3` responses the research curve carries its
   band as a shaded envelope with the contract 4.7 caption and the per-point `consistencyNote.status`, through the same
   adapter as the blind test (7.6). The committed record is static: viewing the panel sends no research request.
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
11. Build Job cache: new `python/*.py` files change the broad Build Job cache key once (`_legacy_broad_cache_fingerprint`
    hashes every Python file); announced in PROOF, harmless.
12. Secure context: without `crypto.subtle` (plain http to a non-loopback address) the commitment is pasted, not
    computed, and the browser hash check is skipped with a visible note; the worker check always runs (3.4 item 5).
13. CSV exports: `blockLabel` and file names are restricted at input, and every text cell of a blind export is
    neutralised against formula injection; numbers are never prefixed (3.4 item 4).
14. No upload (revision 3): share and sealed features make no outbound request from Node, Python or the browser; the
    only network use is the same-origin research route on the user's explicit request (7.6 item 2). Python tests run
    under the NoNetwork socket patch; a TypeScript test fails on any non-same-origin URL in the new client modules;
    links are text with a copy button. Air-gap mode needs no change (`server/airgap.ts` untouched).
15. Research relay: the relayed subsets are closed, size-capped and bound by hash at freeze; the client never renders,
    persists or logs them; the worker never trusts a relayed value beyond the identity checks of 7.6 item 3, and the
    record says the values were relayed (D13).
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
    times and Zenodo publication dates, never on git author or committer dates a client can set; an email release is
    timed by the maintainer's record and labelled so.
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
| `python/lpbf_p8_adapter.py` | Opus (fresh Opus gate), Astra sign-off of the reason-code class table |
| `data/blind/served-closure-pin-v1.json` (generated by `pin-served-closure`) | Sonnet runs, fresh Opus gate reviews each change |
| `python/lpbf_user_blind_inputs.py`, `python/lpbf_user_blind_targets.py` | Sonnet |
| `python/lpbf_user_blind_store.py` | Opus, fresh Opus gate |
| `python/lpbf_user_blind_freeze.py`, `python/lpbf_user_blind_score.py` | Opus, fresh Opus gate |
| `python/lpbf_user_blind.py` | Opus (façade, enforcer, silent child, log filter; fresh Opus gate), Sonnet (validators) |
| `python/lpbf_spent_ledger.py` | Sonnet |
| `python/tools/lpbf_user_blind.py` | Sonnet |
| `python/tools/lpbf_spent_descriptive.py` | Sonnet; Astra owns quantity mapping |
| `python/test_lpbf_blind_stats.py`, `test_lpbf_served_arms.py`, `test_lpbf_p8_adapter.py`, `test_lpbf_user_blind_inputs.py`, `test_lpbf_user_blind_store.py`, `test_lpbf_user_blind_crash.py`, `test_lpbf_user_blind.py`, `test_lpbf_worker_blind_jobs.py`, `test_lpbf_spent_ledger.py`, `test_lpbf_spent_descriptive.py`, fixture `python/fixtures/p8_research_response_v1.json` (copied from the contract fixture `tests/fixtures/lpbf-research-response-v1.json` once it is committed, with its blob hash; revision 3) | Sonnet (Opus writes the isolation, blindness, leak and crash cases) |
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
| `python/lpbf_worker.py` | blind branches in `submit`, `execute` completion (log filter before every log and error write), `get`, child `main` (silent blind branch ahead of the generic exception print), `_archive_run_kind`, `capture`, `artifact` (reveal-or-score gate for freeze and bundle); forced no-dedupe except `user-blind-open`; per-type timeout | Opus, fresh Opus gate |
| `python/lpbf_worker_rpc.py` | `_estimate` branch for `USER_BLIND_RPC_TYPES` (preview, list, get) | Opus, fresh Opus gate |
| `server/pythonRuntime.ts`, `tests/python-runtime.test.ts` | `wslJobRootEnvironment` generalised to forward `METALLIKSA_USER_BLIND_ROOT` (`/p`, drive-letter rule), `METALLIKSA_READ_ONLY`, `METALLIKSA_HOST` and `METALLIKSA_USER_BLIND_SINGLE_USER` through `WSLENV` (3.3); tests for each variable and for a refused UNC blind root | Sonnet, Opus review |
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
| `src/components/LpbfExperimentPlanPanel.tsx` | phase 4: `Download blind-test templates from this plan` | Sonnet |
| `python/tools/lpbf_benchmark_score.py`, `src/data/lpbfLeaderboard.ts`, `src/components/LpbfLeaderboardPanel.tsx`, `tests/lpbf-leaderboard.test.tsx`, `docs/LPBF_BENCHMARK.md` | revision 3: leaderboard schema `lpbf-leaderboard-2` with the `sealedTests` member copied from `sealed-submissions-v1.json`; the separate never-ranked table of 14.4.9; `--check` on structure and hashes only | Sonnet, Opus review |
| `src/services/lpbfUserBlindClient.ts`, `src/data/lpbfUserBlind.ts` | revision 3: research relay and `extractBlindResearchSubset` (3.4 item 8) | Sonnet, Opus review |
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
   the live fingerprint equal to the pin and the served-closure pin equal to the live file hashes; the import-closure
   test (3.6) finds no project module outside the manifest and the closure pin; a one-byte edit of any closure file in
   a temp copy gives `PREDICTOR_NOT_PINNED` naming that file; importing the modules leaves
   `IMPLEMENTATION_SOURCE_FILES` and both pins unchanged.
3. `test_lpbf_p8_adapter.py` and `test_lpbf_research_relay.py` (revision 3; self-contained fixture
   `python/fixtures/p8_research_response_v1.json`, a copy of the contract's R-TR-11 fixture with its blob hash, plus
   synthetic edits of it): `P8_NOT_IN_THIS_BUILD` when the research pin file is absent; `RESEARCH_NOT_REQUESTED` without
   the opt-in; a `p8-research-v3` subset parses (value, band with ties and manifest hash, consistency note, cavity onset
   support); every code of the 7.6 item 5 table lands in its class, `MELT_LINK_NOT_AVAILABLE` inherits the cavity
   class, an unknown code is failed with `RESEARCH_REASON_UNKNOWN`, `NOT_APPLICABLE_BELOW_ONSET` on the scored leaf is
   `RESEARCH_BLOCK_MALFORMED`, a `pending` band in a complete response is malformed; each identity check of 7.6 item 3
   fails alone with its check id (wrong schema, incomplete progress, research hash not equal to the pin, served
   fingerprint not equal to the live one, `userInput` provenance, `user-endpoint` family, `totalArms` not equal to the
   manifest length, a C1 envelope); a subset missing for one condition gives `RESEARCH_RELAY_INCOMPLETE`; a 0 um linked
   depth with `resolved-no-melting` is a value, scored APE 1 on a formed track and listed on a not-formed condition;
   `sourceEvidenceKind` and `weakestInputs` are copied unchanged; an AST check proves no blind module imports
   `lpbf_research_*` and no blind module references the research route; no value is filled or guessed.
4. `test_lpbf_user_blind_inputs.py`: every refusal code in 6.1 for inputs and metadata, including
   `SYNTHETIC_EXAMPLE_ROW`, `FILE_NAME_INVALID`, a formula-like or tabbed `blockLabel`, and published data in
   pre-measurement mode; target-like header refused with a deliberately malformed second line that must not be
   reached; aliases echoed, `d_um` not an alias, ambiguity refused; three dialects; BOM and CRLF; zip magic and
   non-UTF-8 refused; caps; key modes (condition id, unique track ids); replication mismatch; grades, block issues and
   labels from metadata (`beam.profile` `unknown` is a label, `ring` an issue); preview determinism and `previewSha256`
   (acknowledgements do not change it; a new overlap does); preview holds no depth-like value and makes no solver call
   (patched solver raises).
5. `test_lpbf_user_blind_store.py` and `test_lpbf_user_blind_crash.py`: exclusive create refuses overwrite; sidecar
   verification; ledger chain verify and one-byte tamper detection; the OS lock is released when its holder is killed
   (a child holding it is killed, the parent then takes it at once); staging leftovers listed as incomplete and never
   used; read-only, full and shared-host refusals; content-addressed upload reuse; reconciliation adds a missing event,
   cuts a partial trailing line and rebuilds the index; the kill-at-each-step matrix of 3.5 item 5 for freeze, reveal
   and score.
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
   gives inconclusive; powder layer gives `descriptive-not-scored`; n < 12 inconclusive, and a research arm with 12
   served conditions but 11 in scope inconclusive with its coverage label and common-subset statistics; published DOI
   in the ledger gives `not-blind-data-already-used-by-app`; `changedSinceFreeze` scored on frozen values; a changed
   score source gives `scoring code changed since freeze` and not the predictor label; a wording-table change gives no
   label; a protocol rules change under the same id gives `PROTOCOL_CHANGED`; one-byte edited freeze refused; every
   output carries the honesty literals and the full divergence list; sentinel target numbers never appear in errors,
   logs, ledger or job results. Bundle and CLI gate: a bundle request and CLI `show` and `bundle` before a reveal or
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
   present); `SAME_EXPERIMENTS_AS` on Gan, `DATUM_UNSTATED` on Totis, `THRESHOLD_DERIVED_FROM_THIS_SET` on Cunningham;
   the model map counts Gan and Cunningham once; notes only from the catalogue and only with matching sign; KU beam 37.5
   unverified with a 75 sensitivity curve; IN625 two bins at 13.6; no `validated`, `accuracy`, `rank`, `score`, pass or
   fail tokens; size under 150 KB; determinism; committed record current against the live fingerprint (structure and
   hashes only, the CI part); the full `--check` re-derivation as a local-only test, excluded from CI (8.3 item 6).
9. Contract and guards: `python -B -m unittest test_module_contract test_module_contract_research
   test_module_contract_dataset_view test_allowlist_ceilings test_module_warm_parity`, `python
   scripts/emit-module-registry.py --check`, fingerprint pin test unchanged, `pin-served-closure --check`,
   `export-protocol --check`, and in revision 3 `lpbf_sealed.py export-protocol --check`.
10. `test_lpbf_blind_share.py` (revision 3): the share tar is deterministic; `SHARE_NO_SCORE`; targets absent without
    consent and present for every attempt with it (no attempt can be left out); licence and `publishAllowed` rules and
    `SHARE_ATTRIBUTION_REQUIRED`; the ledger excerpt verifies with redacted links and a one-byte edit of any line fails;
    `share-verify` passes on an untouched tar and fails, with the right check id, on each tamper (a member hash, the
    freeze record, a `scored` event moved before `frozen`, a commitment that does not match, a member outside the
    manifest); re-score byte for byte with targets, the skip label without them; `share-verify` writes nothing;
    `share-import` writes only under the shared-results root and creates the `EXPOSED` entry draft and the seen-tuples
    index; a later local test with an overlapping tuple on the maintainer's machine is
    `not-blind-data-already-used-by-app`; a later sealed import with the same hashes gives `SUBMISSION_DATA_EXPOSED`;
    the tar safety cases of 9.16 (absolute path, `..`, link, duplicate name, oversize member) refuse.
11. `test_lpbf_sealed_submission.py` and `test_lpbf_submission_plausibility.py` (revision 3): commitment schema closed
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
    flag; the known-set check runs over every registry entry with a loader and flags a synthetic copy of a spent set
    without printing a value.
12. Labels (revision 3): every predicted and measured value in reports, shared and sealed records and the descriptive
    record carries `sourceEvidenceKind` and `sourceLocator`; served values carry `Unresolved` with
    `SERVED_VALUE_KIND_NOT_PROVIDED`; the research rule on synthetic leaves (all sourced gives `Literature estimate`,
    one user input gives `User input` naming it, one unsourced default gives `Unresolved` naming it, both give
    `Unresolved`, a user input equal to its sourced default keeps the sourced label) is copied, never recomputed; the
    document `evidenceKind` stays `screening-only` in every scope.
13. No network (revision 3): every share, sealed and relay test runs under the NoNetwork socket patch; the CLIs
    `lpbf_sealed.py` and `lpbf_user_blind.py` open no socket in any subcommand.

### 11.2 TypeScript

1. `tests/lpbf-user-blind.test.ts`: validators reject `experimentalValidation` true, missing and `"false"`;
   `appValidation` true; `labelPromotionProposed` other than `none`; wrong `evidenceKind` or `dataLabel`; unknown status
   words and keys; any prediction-like key in preview, receipt, list, get or any queued-type result; header check
   helpers for both files incl. aliases, dialects and the example row; template headers equal the protocol record;
   `blindCsvTextCell` prefixes text cells starting with `=`, `+`, `-`, `@`, tab or carriage return and leaves numbers
   (including negative ones) untouched; the client without `crypto.subtle` offers the paste field and marks the
   browser hash check as skipped; store merge drops unknown persisted fields and survives a throwing `localStorage`;
   the store never persists CSV text.
2. `tests/lpbf-user-blind-panel.test.tsx` (`renderToStaticMarkup`, fixture titled `Synthetic fixture, not measured
   data`): each step; preview with best reachable status and acknowledgements; receipt with no depth number; report with
   served met, research unavailable, research coverage and common subset, band coverage with a partial band,
   consistency counts, input-fragile and u_m assumed; the divergence list rendered; banner and data label exact (after
   Q1); no `/\bvalidated\b/` (or the approved exception, Q2); every input labelled; the `predictionsViewedBeforeFreeze`
   help lists every surface of 4.1; the shared-host warning when `sharedHost` is true; hub tab list includes
   `blind-test`; `DemoUnavailable` in the static demo.
3. `tests/lpbf-spent-descriptive.test.tsx`: validator negatives; empty state; badge; spent chips; quantity caption;
   `unavailable: P8_NOT_IN_THIS_BUILD`; data table fallback; `data-source` on numbers; no `validated` or `accuracy`; a
   committed record sanity check (set ids SPENT, counts only); the lab renders the `Suspense` fallback under
   `renderToStaticMarkup` without throwing.
4. `tests/python-runtime.test.ts` additions: `WSLENV` carries `METALLIKSA_USER_BLIND_ROOT/p`, `METALLIKSA_READ_ONLY`,
   `METALLIKSA_HOST` and `METALLIKSA_USER_BLIND_SINGLE_USER` when set, keeps `METALLIKSA_JOB_ROOT/p`, does not mutate
   the input env, and refuses a UNC blind root loudly.
5. Guards unchanged and green: `tests/route-authority.test.ts`, `tests/component-reachability.test.ts`,
   `tests/module-views.test.ts`, `tests/module-registry.test.ts`, `tests/lpbf-dataset-comparison-lab.test.tsx`,
   `tests/a11y-form-labels.test.ts`, `tests/a11y-static.test.ts`, `tests/workspaces-registry-parity.test.ts`,
   `npm run lint`, `npm run test:unit`, `npm run check:bundle`, `scripts/check_ceiling_review.py`.
6. Real browser (RULES.md 14): keyboard-only run with synthetic files on a local dev server and worker: refusal of an
   inputs file with a depth column and of one with the example row, preview and acknowledgements, freeze and receipt
   download, list and load by freeze key after clearing storage (with a Build Job running), reveal dialog, score,
   re-score with changed targets, exports, print view; descriptive panel set selector, axis toggle, details fallback;
   light and dark themes; hidden-tab polling pause; the same hub opened through a LAN address (no secure context)
   showing the paste field, the skipped-hash note and the shared-host warning.
7. `tests/lpbf-sealed.test.ts` and `tests/lpbf-sealed-panel.test.tsx` (revision 3): closed checkers for every
   document of 4.8 and 4.9 with the scope literals of 2.1; `extractBlindResearchSubset` keeps only the members of 7.6
   item 4 and throws on an unknown key; the relay never renders, persists or logs a research value (sentinel research
   values absent from the rendered markup, the persisted store snapshot and console calls); share step file list,
   consent and licence rules; sealed panel states, the public-and-permanent notice, identity `public` choices with the
   email private by default, flags shown to the user, tier badges and the fabrication notice; the leaderboard sealed
   table has no rank control, groups by alloy, shows `descriptive only` on Declared rows and the pending, withdrawn,
   expired and void counts.
8. No outbound request (revision 3): a fetch mock fails the test on any non-same-origin URL from the blind, share,
   sealed and relay modules; the submissions repository and Zenodo links render as text with a copy button.
9. Real browser additions (revision 3): opt-in research step with progress and Cancel against a local server with the
   research route; share export and download; sealed precheck, commitment export, predictions check and release on
   synthetic files; the same in air-gap mode with identical behaviour.

## 12. Phased plan with acceptance checks

"Opus review" below means the gate rule of section 10: a fresh Opus gate for Opus-authored code, the Opus reviewer
otherwise.

### Phase 0, design gate and spikes (Opus; Astra; Haiku)

Work: commit nothing yet; a fresh Opus run gates this spec; Astra signs off the physics list (served-path definition and
parity fixtures, `FWHM_FACTOR` and D4sigma equivalence, `beam.quantity` radius handling, sensitivity arm set, leverage
cuts for 316L, IN718 and IN625, bare plate layer invariance, u_m f defaults for non-Ti64 alloys, the AlSi10Mg as-built
property convention of the served ledger, descriptive quantity mapping, the reasons catalogue sentences with locators,
the divergence list of 7.7 including D13); P8 reconciliation against the integration contract (`29ae2183`, schema
`p8-research-v3`, and whatever the P8 re-gate settles after Amendment 3 `78607f3e`: the subset members the adapter
reads, the reason-code class table of 7.6 item 5, the identity checks of 7.6 item 3, the opt-in senders of OD1),
signed by Astra and checked by the fresh Opus gate; Haiku times 48 conditions x 5 served calls (include_process_map
True and False) on the worker child path and reports p50 and p95 (research time per condition comes from the contract's
phase C, not from this spike); revision 3: Astra signs off the plausibility constants of 14.7.2 and the sealed
departures SD1 to SD3, and the maintainer answers Q6 to Q11; Haiku transcribes the
spent ledger, Opus reviews; a spike adds the dataset-view browser-local op and runs `route-authority` and
`emit-module-registry --check`, then is discarded or kept; maintainer answers Q1 to Q5 (Q2 can wait until phase 6).
Accept: gate record with decisions; the served condition cap of 4.3 from the measured p95 (at most 60 s); Astra
sign-off note including the P8 class table, the plausibility constants and the sealed departures.

### Phase 1, Python core offline (Opus stats, store, freeze, score, P8 adapter; Sonnet served arms, intake, CLI, tests; Haiku vectors and templates)

Accept: `python -B -m unittest test_lpbf_blind_stats test_lpbf_served_arms test_lpbf_p8_adapter
test_lpbf_user_blind_inputs test_lpbf_user_blind_store test_lpbf_user_blind_crash test_lpbf_user_blind` green (counts
recorded); golden vectors equal; served parity exact for four alloys plus IN625 direct; served-closure pin and
import-closure test green; AST isolation, open audit and NoNetwork green; kill-at-each-step matrix green; `git diff` of
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
latency measured while a Build Job runs, with `.lpbf-jobs` unchanged after 100 polls; fresh Opus gate.

### Phase 3, Hub UI (Sonnet; Haiku help text, CTA, palette, guide draft)

Accept: lint, `npm run test:unit`, a11y gates at 0 exclusions, reachability and module-view guards unchanged,
`npm run check:bundle` within budgets, research contract tests (with the lifecycle and authority changes of 10.2),
real-browser keyboard run recorded with what was not run, including the secure-context behaviour (paste field, skipped
browser hash note) and the shared-host warning through a non-loopback address; Opus review; maintainer sees rendered
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

### Phase 6, P8 research route integration after the contract's phases B to E land (Opus with Astra; Sonnet)

No served bump is involved (7.6). Work: enable `P8_ADAPTERS["p8-research-v3"]` against real route responses and the
committed contract fixture; the research relay of 7.6 item 2 in the client and the CLI `--research-responses` path;
`scripts/research-route-batch.ts`; confirm the class table and the absence of `UNSOURCED_PROPERTY_OVERRIDE` on the
Build Job snapshot context (7.6 items 5 and 13); band coverage, partial bands and consistency counts on real output;
common-subset statistics and the sign-flip comparison; `vapour-depression-depth` quantity descriptive against
`research:cavity`; label display per Q2 and 14.6; regenerate the descriptive record with research curves from an
explicit batch; record research time per condition and relayed subset sizes at the cap.
Accept: served bytes unchanged with a relay running (contract P-5 and P-6), served-closure pin unchanged; freezes made
before the route existed keep `P8_NOT_IN_THIS_BUILD` (no research value is ever added after a freeze); research arms
populated or unavailable with codes and coverage labels; OD1 settled by the P8 re-gate; guard regex change applied only
as approved; fresh Opus gate.

### Phase 7, close-out (Opus; Haiku docs and docker)

Accept: `docs/LPBF_USER_BLIND_TEST.md` reviewed (it states the divergence list, the shared-host rule, the
secure-context limit and the CLI environment rule); inventory rows; docker env; PROOF entry in the P7b format (scope,
checks with exact counts and what was not run, limits, `labels unchanged: experimentalValidation=false, no label
promoted`, Build Job cache invalidation noted); STATUS milestone in Turkish; ci.yml additions prepared for the
maintainer's single Ceiling-Review trailer; one batch push only on the maintainer's word, explicit paths staged.

### Phase 8, sharing with the maintainer (revision 3; Opus share and sealed core, fresh Opus gate; Sonnet CLI, plausibility, UI, leaderboard; Haiku guide and templates; Astra constants)

Can start after phase 4 (bundle) and run beside phases 5 and 6; the research parts wait for phase 6.
Work: Mode A (`lpbf_blind_share.py`, `user-blind-share`, share step, `share-verify` and `share-import`, spent ledger
entry kind); Mode B user side (`user-sealed-precheck`, `user-sealed-commit`, `user-sealed-check-predictions`,
`user-sealed-release`, sealed panel); maintainer side (`lpbf_sealed_submission.py`, `lpbf_sealed.py`, sealed rule record,
`sealed-submissions-v1.json`, `approved-reviewers-v1.json`); plausibility checks and tiers (14.7); leaderboard schema 2
and the sealed table; guide sections (both modes, licences, the fabrication statement, the tiers) and, for the
maintainer to place, a README and pull request template for the submissions repository.
Accept: 11.1 items 10 to 13 and 11.2 items 7 to 9 green with counts; a full synthetic Mode B run on one machine with two
stores (user and maintainer) through every state of 14.4.3, including each refusal of 14.4.4, ending in a leaderboard
row whose public files hold no sentinel value; a synthetic Mode A share verified and imported, then refusing a sealed
submission of the same data; no socket opened (NoNetwork) and no non-same-origin fetch; MELT runner pins recorded or the
G3o path marked not run; OD2 recorded by the lead; fresh Opus gate. Creating the submissions repository and the Zenodo
community stays with the maintainer; until then the placeholder name stays in the wording table.

## 13. Open questions for the maintainer

1. Q1, wording: approve or change the strings in section 2.2 (tab name, report title, banner, receipt line, the six
   status sentences, the descriptive badge and the "why" prefix) and the user-facing strings added in revision 2 (the
   new refusal messages of 6.1, the labels of 7.5, the shared-host warning, the secure-context notes, the divergence
   sentences of 7.7). Tests pin them after approval; until then they sit in the wording table, outside every identity.
2. Q2, the P8 label `not validated` versus the guard `/\bvalidated\b/i` in `tests/lpbf-dataset-comparison-lab.test.tsx`
   (and the same guard in the new hub tests): proposal is an exact-phrase exception (the word is allowed only inside
   `not validated`) rather than rewriting the GOAL label. Needed before phase 6 only.
3. Q3, spending Zhao: GOAL item 2 names NIST, Cunningham, KU Leuven and Totis. Admitting Zhao (EXPOSED today) spends it;
   approve a separate ledger commit, or leave Zhao out. Gan Data 1 Ti64 is included as part of the Cunningham
   experiments (same experiments, flagged); confirm.
4. Q4, other alloys: show scored statuses for 316L, IN718 and IN625 with `thresholds reused unchanged` (proposal), or keep
   those alloys descriptive only because the thresholds were registered for Ti-6Al-4V and AlSi10Mg.
5. Q5, digitized AAAS figure data (Cunningham, Zhao): show per point in the app (proposal, with the digitization note and
   read uncertainty), or show group summaries only.
6. Q6, Mode B candidate arm: the MELT candidate (S1, or S2 with a P3 primary block PASS on record, Amendment 2 item 4;
   Eagar and Tsai kernel; pinned MELT runner) with the app's served Build Job arm and the research arm scored beside it
   under the same rules (proposal, 14.4.6), or the served Build Job arm as the candidate, which needs a MELT amendment
   before any submitted target is read.
7. Q7, which sealed blocks may count toward G3o: proposal Ti-6Al-4V and AlSi10Mg only, public blocks only (confidential
   blocks listed, not counted), tier Evidenced or above before scoring; and whether a block with declared measurement
   losses (SD2) may count (Astra's ruling).
8. Q8, release window and withdrawal: proposal 180 days from `published` to `expired-unreleased`; withdrawals before
   predictions leave only the public commitment, after predictions they are listed as `withdrawn-after-predictions`.
9. Q9, labels: served values carry `Unresolved` (`SERVED_VALUE_KIND_NOT_PROVIDED`) until the served payload itemises
   per-value provenance (proposal; that change is a served bump outside this spec); process conditions (P, v, d, T0)
   are request inputs that never make a research output `User input` (contract 6.2; confirm).
10. Q10, licences and identity: the licence menu (CC BY 4.0 proposed default, CC0 1.0, none) and whether an ORCID alone
    is enough identity for Evidenced, or a lab and machine model must also be public.
11. Q11, plausibility constants and tier tolerances: `ASPECT_MAX` 6, scatter floor 0.5 %, digit test at p < 0.001 with at
    least 50 values, known-set match within max(1 um, 1 %), spot check of min(5, n) sections within 2 u_m or 5 %
    (proposals; Astra signs off the physical ones in phase 0).

Q1 also covers the revision 3 strings: the share and sealed step texts of 2.2, the refusal messages of 6.1 added in
revision 3, the tier badges and descriptions, the flag line, the export and fabrication notices (14.7.5), and the
leaderboard table heading and caption (14.4.9).

Open dependencies (not maintainer questions):

1. OD1, P8 contract re-gate: the integration contract at `29ae2183` lets only the Research model panel send research
   requests (contract 1.1 and 1.3). The blind tab's opt-in research step and the explicit batch client
   `scripts/research-route-batch.ts` (7.6 item 2) need to be admitted as senders, with the same route, lane and request
   schema. If the re-gate refuses, the research arm stays `RESEARCH_NOT_REQUESTED` in protocol 1, and only maintainer
   batches (Mode A rerun, Mode B, descriptive record) carry it, if admitted. The contract is being revised on
   `research/p8-research-arm` (P8 Amendment 3 at `78607f3e` changes scenario provenance and secondary-alloy
   manifests); the adapter reads arm counts and names from each response and pins nothing that Amendment 3 may change.
2. OD2, MELT amendment by the lead: the sealed protocol (14.4.6), the two-independent-campaign rule for submitted data
   (14.4.7) and the tier condition for G3o counting are written into the MELT pre-registration before any submitted
   target is read.

Maintainer actions (not questions): the Ceiling-Review trailer for `.github/workflows/ci.yml` at the batch push; the push
itself; creating the submissions repository and the Zenodo community (14.5); approving reviewers (14.7.4).

## 14. Revision 3: sharing with the maintainer and label decisions (2026-10-15)

Source: the maintainer decisions in `.orchestra/GOAL.md` (main checkout, gitignored lead file), section "Label and data
decisions (maintainer, 2026-10-15)", items 1 to 5, and the maintainer's answer of the same day on anti-fabrication trust
tiers ("Olur"). This section holds the design; the affected sections carry the integrated changes and point here
(Appendix A.5 lists them). Section 7.6 is rewritten against the P8 integration contract in the same revision. Nothing
here is implemented; the revision goes to the design gate with the rest of the spec.

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
4. The main repository stores results, hashes, DOIs and the identity fields a submitter chose to make public (14.7.1),
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
   two-independent-campaign rule: no milestone statement rests on one submitter's data (14.4.7).

### 14.2 The three paths compared

| | Local test (protocol 1) | Mode A, share my result | Mode B, sealed submission |
|---|---|---|---|
| Who predicts | user's app | user's app | maintainer's app |
| Targets fixed before predictions by | local order, optional commitment and anchor | as in the local test | public commitment of the targets SHA-256 before predictions are published |
| Maintainer sees the targets | never | when the user consents to include them | only after the predictions are published |
| Counts as | the user's own test | a result the maintainer has seen; never an app blind test | an independent blind test of the app under the sealed protocol (14.4.6), at tier Evidenced or above |
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
4. `targets-<n>.csv` for every attempt, only with `consent.includeTargets: true`;
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
   the recipient`;
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

14.3.5 Effects. A Mode A set is seen by the maintainer. It never counts as an app blind test (`appBlindTest: false`,
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

14.4.1 Order. The user commits in public (inputs, metadata, evidence manifest, SHA-256 of the targets file); the
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

14.4.3 State machine. The maintainer's sealed store holds the reference state; ledger events are in brackets and follow
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

14.4.4 Refusal cases.

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

14.4.5 Confidential variant. For a lab that cannot publish inputs: the public `commitment-public.json` holds
`commitmentId`, `inputsSha256`, `metadataSha256`, `targetsSha256`, `evidenceManifestSha256`, `sealedProtocolSha256`,
alloy, condition count, licence `none` and the public identity fields; the full commitment goes by private email. The
maintainer publishes `predictions-public.json` (`predictionsSha256` and identities only) and emails `predictions.json`;
targets and evidence go by email. The result record holds statistics and statuses only, no per-condition values,
labelled `confidential sealed test: third parties cannot re-score it`. Proposal: confidential blocks are listed but do
not count toward G3o, which is an open-data objective (Q7).

14.4.6 Scoring under the sealed protocol (`lpbf-sealed-protocol-1`). The rule record
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

14.4.7 Claims. A sealed block licenses at most the MELT Amendment 6 item 13 sentence for that block (a G3o block) or a
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

14.4.9 Leaderboard. `data/benchmark/sealed-submissions-v1.json` (schema `lpbf-sealed-submissions-1`, committed by the
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
2. Zenodo (DOI, licence, optional Metalliksa community, created later by the maintainer): the user deposits the release
   folder (inputs, metadata, targets, evidence files, commitment, a copy of the predictions, `release.json`). The release
   time is the publication date of the record; a draft or an embargoed file is not a release. A correction is a new
   Zenodo version, and only the version whose targets bytes hash to `targetsSha256` is scored.
3. Private email for confidential labs (14.4.5). The maintainer records the receipt time, and the record says `email`,
   so the weaker timing is visible.
4. Main repository: `data/benchmark/sealed-submissions-v1.json`, `data/benchmark/approved-reviewers-v1.json`, spent
   ledger entries for Mode A sets and voided blocks, the leaderboard record and PROOF entries. Never raw user data.
5. The app's part: per step it writes the files and a plain-text instruction sheet (where to submit, what to deposit,
   which licence was chosen, what happens next), shown in the UI and written beside the files. It calls no network API.

### 14.6 Labels (decision items 1 and 2)

1. Per-value label. Every predicted or measured value in a blind, shared or sealed document and in the descriptive
   record carries `sourceEvidenceKind` with `sourceLocator`. The document-level `evidenceKind: "screening-only"` (2.1)
   stays the module evidence ceiling, and no per-value label raises it.

   | Value | `sourceEvidenceKind` | Locator |
   |---|---|---|
   | user measured depth, width, uncertainty | `Measured` (data label `Measured (user-supplied)`) | `{targetsSha256, key}`; after a Zenodo release also the DOI |
   | spent-set value (section 8) | `Measured`, with `transcription` `table` or `digitized-figure` | citation, DOI, table or figure locator |
   | research leaf value | the leaf's own `evidenceKind` under the rule of item 2, copied, never retyped | the source locators of the leaf's input provenance; `weakestInputs` names when not `Literature estimate` |
   | served value | `Unresolved`, reason `SERVED_VALUE_KIND_NOT_PROVIDED`, until the served result carries per-value provenance (a served-side change outside this spec, Q9) | served identity |
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
3. Identity (`submitter`): `orcid` (format and checksum checked offline) or `institutionalEmail` (at least one for
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
   entry with a loader takes part (NIST, Cunningham, KU Leuven, Totis, Zhao, Gan, Bitharas with its inferred keys
   labelled inferred, and the others), read through `lpbf_spent_ledger`. A tuple match without a depth match is the
   note `inputs match known set <datasetId>`, not a flag, because standard parameters are common.

Where they run: in the user's app at `user-sealed-precheck` and before a share, shown to the user only (in Mode B they
are not part of the commitment, so the maintainer learns nothing from the targets before predictions); on the
maintainer side at Mode A import and at Mode B `intake`, which is the record. Tests use synthetic data; agents never
print values (2.3 item 6). What the checks cannot do: data fabricated with realistic scatter around the model passes
them; they catch careless and copied data only (14.1 item 7).

14.7.3 Tiers (cumulative: each requires the one below).

| Tier | Requires | Effect |
|---|---|---|
| `Declared` | nothing; default for every submission | descriptive only; never counts toward G3o |
| `Evidenced` | per-section values; micrographs with scale bars, at least for the spot-check sample; identity with ORCID or institutional email, lab, machine model and date; no open plausibility flag (absent, or cleared by the reviewer with a written reason); a spot check in which the reviewer measures depth on a sample of micrographs drawn deterministically from the hashes (seed sha256 of `targetsSha256` and `predictionsSha256`, min(5, n) sections) and records agreement within the declared tolerance (proposal: 2 u_m or 5 %, whichever is larger) | may count toward G3o (14.4.6 item 6) |
| `Published` | Evidenced, plus a peer-reviewed article or a DOI dataset holding the per-section values and the micrographs (a micrograph figure in an article counts by its figure locator) | as Evidenced |
| `Replicated` | Evidenced or Published, plus an independent second lab (different lab and machine, no shared submitter) whose block at Evidenced or above measured comparable conditions (same alloy and substrate kind, at least 4 conditions with P, v and 1/e2 beam each within 5 %) | as Evidenced; supports the two-campaign rule (14.4.7) |

14.7.4 Tier state machine. Every submission, Mode A or Mode B, starts at `Declared`. Promotions and demotions are events
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

14.7.5 UI labels (proposals under Q1): tier badges `Declared: table only, not checked`, `Evidenced: micrographs and
identity checked by a reviewer`, `Published: in a peer-reviewed article or a DOI dataset`, `Replicated: measured again
by an independent lab`; flag line `Flag: <sentence>. Flags never reject data; a reviewer looks at them.`; export notice
`Your submission starts as Declared. Per-section values, micrographs with scale bars and your ORCID or institutional
email let a reviewer raise it to Evidenced.`; fabrication notice `The model is open source, so anyone can compute its
predictions. A sealed submission proves when your measurements were fixed, not that they are real. Evidence, review
and independent replication are what make a result count.`

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
