# SPEC: your own blind test (bring your own data) and the descriptive panel on spent sets

File: `docs/research/SPEC_research_hub_data_2026-10-14.md`. Design gate draft, written 2026-10-15 on worktree
`Metalliksa-1-wt-hub` (branch `feat/research-hub-data`, HEAD `835466fa`, fingerprint pin `36cd9d4a…`). Nothing in the
product implements it yet. Not committed. Revision 2 (2026-10-15): the gate's must-fix items, missing items and
contradictions are applied in place; the P8 contract is P8 v2 (`research/p8-research-arm` `b6e68dfe`, schema
`p8-research-v2`).

Goals: roadmap items 1 and 2 of `.orchestra/GOAL.md` ("Roadmap after the batch push", maintainer approved 2026-10-14).

Base design: "reuse first" (design 1), the best combined judge score (evidence 6.5, engineering 8, usability 6, total
20.5; protocol integrity first 19; Research Hub usability first 18). Grafted ideas and the fix for every judge defect are
listed in Appendix A. Where this spec and a design disagree, this spec wins.

Labels unchanged by this work: `experimentalValidation=false`, evidence kind `screening-only`, no module or result
promoted, no served physics change, fingerprint manifest untouched (36 files), `routes/AUTHORITY_ALLOWLIST.json` and every
`*.ceiling.json` untouched, legacy contract count stays 3.

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
   "research arm" (the P8 `researchModels` block, read through a closed adapter).

### 1.2 Non-goals

1. No validation claim for the app, no G3, G3o, N3 or N4 credit, no physics bump, no calibration from user data (the
   existing machine-calibration path stays separate and unchanged), no leaderboard entry, no automatic link into the
   research registry.
2. No served physics change. All new Python files sit outside `lpbf_simulation.IMPLEMENTATION_SOURCE_FILES`; the
   served modules outside that manifest are pinned separately (3.6).
3. No new HTTP route, no allowlist or ceiling growth, no new registry module, no `App.tsx` edit, no nav golden change.
   Node gets one edit and no route edit: `server/pythonRuntime.ts` forwards the blind environment variables to a WSL
   worker (3.3).
4. No hosted or multi-user service. The store is local to one workstation and is not scoped per user; on a server bound
   to a non-loopback address blind mutations are refused unless the operator declares a single-user install (9.7).
5. No proof of ordering to third parties. The app records local order and hashes; provable order needs the user to
   anchor the receipt hash outside this computer.
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
| Research arm label | `Literature estimate / Research / not validated` (GOAL item 0 wording; see Q2) |

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
| `python/lpbf_served_arms.py` | Single definition of served and research arms, shared by the blind test and the descriptive tool. `served_arm(alloy, P, v, d_1e2_um, T0_C, layer_um)` reproduces `lpbf_build_job_solver.py:910-1028` exactly: `resolve_alloy_id`, `ALLOY_MATERIALS`, `build_material_property_snapshot`, `canonical_material_source`, `build_build_job_identity(BUILD_JOB_MODEL_ID, BUILD_JOB_SOLVER_REVISION)`, then `calculate_meltpool_physics(thermal_mat, P, v, d, T0, layer, 110.0, "IR_1064nm", incline_angle_deg=0.0, process_seed=DEFAULT_PROCESS_SEED, prop_overrides=snapshot["thermal"], include_process_map=X)`. X is `False` only if the parity test proves identical geometry with `True`; otherwise `True`. Returns `depth_um` and `width_um` only when `meltPoolGeometry.extentStatus == "computed"`, else `{status: "failed", reason: "EXTENT_NOT_COMPUTED"}`; also `keyholeModel.fabbroDepth_um` (context) and the unrounded index from `lpbf_public_datasets.normalized_enthalpy` (the runner's leverage convention; the served response rounds it to 2 dp). IN625 is not a Build Job alloy: the direct thermal path with `"Inconel 625"`, flat-plate, Rosenthal, no overrides, `buildJobIdentity: null`, reason label `IN625_DIRECT_THERMAL_PATH`, and the result's `materialEvidence` (`legacy-estimated-secondary`) copied into the arm label. `sensitivity_arms()`: served at P x 0.95, P x 1.05, d x 0.95, d x 1.05 (MELT `POWER_BAND` and `BEAM_BAND_GRADE_B`), with the P8 research block switched off on these calls once the P8 bump provides the switch (7.6 item 10). `research_arms(thermal)`: delegates to `lpbf_p8_adapter` (section 7.6); never passes `researchOptions`. `predictor_identity()`: section 3.6. |
| `python/lpbf_p8_adapter.py` | Closed P8 v2 adapter (7.6): `P8_ADAPTERS["p8-research-v2"]`, the reason-code class table, band and `consistencyNote` extraction, the `researchOptions`-absent assertion. Pinned in the served-closure pin (3.6). No import of a research branch. |
| `python/lpbf_user_blind_inputs.py` | Metadata schema and validation, inputs CSV parsing (dialects, closed alias table, header whitelist checked before any data row, caps, base64 decode, UTF-8), structure checks, input-only exclusions (runner `parse_input_rows` rules), beam conversion, grades, block issues, design checks, preview. Must not import the targets parser. |
| `python/lpbf_user_blind_targets.py` | Targets CSV parsing, exact key join, `depth_status` rules, repeated-input check, commitment check. |
| `python/lpbf_user_blind_store.py` | Store root, layout, exclusive create (`open(mode="x")`), sha256 sidecars, read-only bit after write, content-addressed uploads, staging and rename (the commit point), ledger with sequence and previous-entry hash, OS-held store lock, start-of-mutation reconciliation (3.5), caps, listing of incomplete staging dirs, the reveal-or-score state gate shared by the artifact branch, the bundle job and the CLI, `source_identity(paths)` (hashes files by path without importing them), read-only tuple readers for the calibration stores (6.4 item 7). |
| `python/lpbf_user_blind_freeze.py` | Freeze: re-run preview, re-check required acknowledgements and overlap, identity checks, per-condition arm predictions, freeze record, receipt. Imports inputs, served arms, stats (design checks only) and store. Must not import `lpbf_user_blind_targets` or `lpbf_user_blind_score` (AST test); the scorer identity is computed by `source_identity`, which reads bytes and imports nothing. |
| `python/lpbf_user_blind_score.py` | Score: verify freeze, join targets, reduce, statistics per arm, coverage and common subset, qualifiers, fragile labels, blindness rule, scorer identity, report. |
| `python/lpbf_user_blind.py` | Façade for the worker: `USER_BLIND_RPC_TYPES` and `USER_BLIND_JOB_TYPES` (3.2.1), `validate_request(raw)` per type (closed keys, Phase 6a validation envelope so the route answers 422), `stage_request(p)`, `run_job(input)` (silent child, fixed error codes), `rpc(raw)` for the estimate RPC (preview, list, get), `enforce_user_blind_job_result(result, params)`, `filter_blind_log(text)`, `blind_document(result, name)` for the artifact branch, label constants. Lazy imports per job type keep the freeze path free of the targets parser. |
| `python/lpbf_spent_ledger.py` | Loader and checks for `data/benchmark/spent-ledger-v1.json`; used by the descriptive tool and by the blind test exposure check. |
| `python/tools/lpbf_user_blind.py` | Offline CLI for air-gapped labs on the same library: `templates [--from-plan plan.json]`, `preview`, `freeze`, `reveal`, `score`, `list`, `show`, `bundle`, `verify`, `export-protocol [--check]`, `pin-served-closure [--check]`. No network. The CLI goes through the same store functions and the same state gate as the worker: `show` prints predicted values and `bundle` writes a tar only when a reveal record or a score exists for the freeze, or when `--reveal "<phrase>"` is given, which writes `reveal-<n>.json` and the `revealed` ledger event first; otherwise both refuse with `REVEAL_REQUIRED`. `list` and `verify` print receipts, hashes, statuses and check results only, never a predicted or measured value. Run it in the same environment as the worker (both Windows or both WSL), because an `msvcrt` lock and an `flock` on a `/mnt` path do not exclude each other. |
| `python/tools/lpbf_spent_descriptive.py` | Offline producer of the descriptive record (section 8). |

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
   `python/*.py`). Per-type `timeout_s` (read by `execute()` at line 1017): freeze 180 s (re-derived with the P8 band
   cost, 7.6 item 10), score 60 s, reveal 30 s, bundle 60 s, open 30 s.
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
   `blind-report.json`, `blind-bundle.tar`). The file is resolved in the blind store from the job result's validated
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
about a minute". Reveal, score, bundle and open make no solver call; preview, list and get are not queued at all. P8 is
not free: once merged, every `calculate_meltpool_physics` call also evaluates the declared research arms (18 for
Ti-6Al-4V, 24 for AlSi10Mg, P8 A4). The freeze cost is planned with those arms in phase 0, the sensitivity calls skip
them once the P8 bump provides a switch, and the cost is re-measured in phase 6 with the cap lowered if needed (7.6
item 10).

### 3.2.1 Blind request types and closed payloads

Every payload is closed (unknown keys refused, booleans real booleans), `schema` is `lpbf-user-blind-request-1`,
`freezeKey` is 64 lower-case hex, file names follow 4.2 item 10, base64 fields follow 4.3. Each result carries the
honesty block of 2.1.

| Type | Path | Payload (keys required unless marked optional) | Result |
|---|---|---|---|
| `user-blind-preview` | estimate RPC | `{jobType, schema, metadata, inputsCsvBase64, inputsFileName}` | preview (4.5 item 1) |
| `user-blind-list` | estimate RPC | `{jobType, schema, page?: int >= 0, pageSize?: int 1 to 50}` | `{entries [{freezeKey, blockLabel, alloy, createdAt, counts, state (frozen, revealed, scored), attempts, latestStatus}], total, page, readOnly, sharedHost}`; receipt fields only |
| `user-blind-get` | estimate RPC | `{jobType, schema, freezeKey}` | receipt summary, reveal events, attempts with status words, `documents [{name, attempt or null, sha256, size, jobId, jobRecordPresent}]` for the documents the state gate allows; no predicted or measured value |
| `user-blind-freeze` | queued | `{jobType, schema, metadata, inputsCsvBase64, inputsFileName, previewSha256, overlapSha256, acknowledgements}` (`overlapSha256` copied from the reviewed preview) | receipt (4.5 item 3) |
| `user-blind-reveal` | queued | `{jobType, schema, freezeKey, confirmation}` (exact phrase) | `{freezeKey, revealN, ledgerSeq, documents}` |
| `user-blind-score` | queued | `{jobType, schema, freezeKey, targetsCsvBase64, targetsFileName, declarations {viewedPredictionsBeforeFinalisingTargets}, acceptCommitmentMismatch}` | `{freezeKey, attempt, alreadyScored, statuses, documents}` |
| `user-blind-bundle` | queued | `{jobType, schema, freezeKey, revealConfirmation?: exact phrase}` | `{freezeKey, bundleN, sha256, size, documents}`. Refused at submit and again in the child with `REVEAL_REQUIRED` unless a reveal record or a score exists; with `revealConfirmation` the child writes `reveal-<n>.json` and the `revealed` event before the tar |
| `user-blind-open` | queued, deduplicated | `{jobType, schema, freezeKey, name (closed set of 3.2 item 7), attempt?: int >= 1}` | `{freezeKey, name, attempt, sha256, size}`; writes nothing; same state gate |

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

Ledger events: `frozen`, `revealed`, `score-refused` (code only), `commitment-mismatch`, `scored`, `bundle-exported`,
`reconciled` (names the event it restored). The ledger never holds measured values, predictions or free text; `jobId`
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
per-alloy materialPropertySha256, materialAuthorityRevisionSha256, buildJobIdentitySha256, research {schemaVersion or
null, researchOptions: "absent (sourced defaults)", armManifestSha256 or null, bandMethod or null}, heatSource
"rosenthal", absorptionModel "flat-plate", includeProcessMap, python, numpy and scipy versions}`.

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
machine-calibration block, the experiment plan panel, and any CLI that prints a served depth. A test pins that the help
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
line at most 1,000,000 characters). Rows: 2000. Conditions per freeze: provisional 48 before P8 (5 served calls each,
240 calls). With P8 merged, each condition also costs 18 (Ti-6Al-4V) or 24 (AlSi10Mg) research arm evaluations on the
nominal call, or five times that if the sensitivity calls cannot skip the research block (7.6 item 10); the cap is
therefore stored per alloy and per research state (`conditionCap {pre-P8, P8 with switch, P8 without switch}`),
derived in phase 0 from timing (P8 cost from the committed synthetic reproduction as a planning proxy only), set in
phase 1 for the pre-P8 tree and re-measured in phase 6, always so that a freeze at the cap takes at most 60 s p95 with
a cold research cache (every freeze child starts cold). A larger campaign is split into blocks; each block needs at
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
   `acknowledgementsRequired[]`, budget `{conditions, solverCalls, researchArms, cap, estimate_s}`, divergences that
   apply, honesty. Leverage is reported as bin counts only, never per-condition index values. No predicted depth.
2. Freeze record (`lpbf-user-blind-freeze-1`, on disk only): `freezeKey = sha256(canonical {protocolId, metadata,
   canonical input rows, predictorIdentity})` (createdAt excluded, so re-freezing identical inputs returns the same
   record); `createdAt` (local clock, stated as unverified); metadata; `metadataSha256`, `inputsSha256` (raw bytes),
   `previewSha256`; `columnsLoaded`; `targetColumnsRead: false`; rows `[{ordinal, condition, track, section, P_W,
   v_mm_s, d_declared_um, beamQuantity, beamDefinition, d_1e2_um, conversion, P_u_k1_W, indexUnrounded, indexBin}]`;
   per condition `pred {served, "served:P-5%", "served:P+5%", "served:d-5%", "served:d+5%", "research:melt-link",
   "research:cavity", "context:fabbro"}`, each `{value_um, status ok|failed|unavailable, reasonCode, reasonClass,
   extentStatus, warnings[]}`, research arms also `band` (the P8 `ResearchNumericBand` of the leaf: `min`, `nominal`,
   `max`, `successfulArms`, `totalArms`, `completeness`, `method`, `minArmId`, `maxArmId`, `statusSupport`,
   `failedArms`) and `consistencyNote` (`status`, `worstArmStatus`, `statusSupport`, `sentence`, `knownContradictions`
   ids); acknowledgements; excluded inputs; design checks; grades; block issues; labels; predictor identity; scorer
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
catalogue, the P8 reason-code class table (7.6 item 3), the declared divergence list with ids and rules (7.7), the
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
   inputs before freeze is legitimate), and the acknowledgement boxes.
5. Freeze submit: `POST /api/lpbf/jobs {jobType: "user-blind-freeze", schema, metadata, inputsCsvBase64,
   inputsFileName, previewSha256, overlapSha256, acknowledgements}`. `acknowledgements` is a top-level request field, outside
   `metadata`, `metadataSha256` and `previewSha256` (4.1). Python (submit) re-runs the preview; first compares the live
   overlap with the reviewed `overlapSha256` (`OVERLAP_CHANGED`) and the live required acknowledgements with the ticked
   ones (`ACK_REQUIRED`), so the message says what changed; then refuses any other drift with `PREVIEW_DRIFT`; stages the
   canonical metadata and raw inputs bytes by hash; enqueues a job whose `input.json` holds hashes only.
6. Freeze (child). Silent child (3.2 item 3). Verify uploads by hash; re-run the preview; check the live fingerprint
   and the served-closure pin (3.6); for every condition compute the served arm, four sensitivity arms and the research
   arms (research from the nominal call's thermal result, 7.6); `assert_no_target_loaded`; record `columnsLoaded` and
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
every test (9.7).

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
| `RESEARCH_CONTRACT_BROKEN` | `The research block does not match the pinned P8 contract (<check>). Nothing was frozen.` (child) |
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

A child job ends with one code from the closed `BLIND_CHILD_ERROR_CODES` table: the codes above that can arise after
submit (`PREVIEW_DRIFT`, `ACK_REQUIRED`, `OVERLAP_CHANGED`, `PREDICTOR_NOT_PINNED`, `PROTOCOL_CHANGED`,
`RESEARCH_CONTRACT_BROKEN`, `FREEZE_ALTERED`, `REVEAL_REQUIRED`, `STORE_*`) plus `SOLVER_EXCEPTION` and
`INTERNAL_ERROR`. The job's `error` text is the code's fixed message, never an exception message (3.2 item 3).

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
arm the preview also states the number of conditions inside the P8 scope that can be decided from inputs alone
(alloy chain admitted; numerical Peclet range 0.01 to 10 needs the solver, so it is reported only after the freeze).

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

## 7. Scoring

### 7.1 Arms

| Arm | Source | Scored |
|---|---|---|
| `served` | Build Job thermal call (`lpbf_served_arms.served_arm`); IN625 direct thermal path, labelled | yes |
| `served:P-5%`, `served:P+5%`, `served:d-5%`, `served:d+5%` | same call with perturbed power or 1/e2 beam (research block off once P8 provides the switch, 7.6 item 10) | only for the input-fragile label |
| `research:melt-link` | P8 v2 `meltDepthLink.fields.linkedMeltDepth_um` with its `band` and the module `consistencyNote` (conditional and conduction depths and `controllingLeg` carried as context); Ti-6Al-4V and AlSi10Mg only (P8 section 3: other alloys `ALLOY_CONSTANT_CHAIN_NOT_ADMITTED`) | yes, side by side, never changes served labels |
| `research:cavity` | P8 v2 `keyholeCavity.fields.cavityDepth_um` with its band | only against `vapour-depression-depth`, descriptive in protocol 1; otherwise shown with `OBSERVABLE_MISMATCH` (goal deviation G1, 7.7) |
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
2. `descriptive-not-scored` (powder layer; vapour quantity; research cavity against melt depth)
3. `inconclusive` (n < 12 counted inside the arm's scope, any block issue)
4. `threshold-not-met` (any of the four)
5. `inconclusive` (leverage not met or not evaluable, the latter for IN625; resolution `not_met` or `not_evaluable`)
6. `thresholds-met`

`unavailable` applies to a research arm with no in-scope condition (P8 absent, schema unknown or malformed, alloy chain
not admitted, every condition outside the numerical scope). Each status maps to one plain sentence (2.2) plus the label
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
printed as a predictor note in the collapsed predictor section.

### 7.6 Served versus P8 research arm (contract: P8 v2, `research/p8-research-arm` `b6e68dfe`)

The P8 specification at `b6e68dfe` (`docs/research/SPEC_p8_research_arm_2026-10-14.md`, Amendment 1) declares
`schemaVersion "p8-research-v2"` (spec line 61), seven closed containers, a `band` of type `ResearchNumericBand` with
method `declared-ofat-envelope-v1`, and a closed `consistencyNote` on `keyholeCavity`, `meltDepthLink`, `marangoni` and
`surfaceBalance` (lines 73 and 328 to 369). Earlier drafts of this section were written against a v1 contract that was
never served and are replaced here.

1. Side by side in one table: per arm status, sentence, coverage, the four statistics, bootstrap, labels, and the four
   P8 evidence labels copied from the leaf (`evidenceKind "Literature estimate"`, `moduleMaturity "Research"`, the
   `validationStatus` text per Q2, `experimentalValidation false`), never retyped.
2. Adapter `python/lpbf_p8_adapter.py`, `P8_ADAPTERS["p8-research-v2"]` (closed; there is no v1 entry). It reads
   `thermal.researchModels` only: the scored leaf `meltDepthLink.fields.linkedMeltDepth_um` (`value`, `reasonCode`,
   `warnings`, `band`, `consistencyNoteRef`), context leaves `conditionalMeltDepth_um`, `conductionDepth_um`,
   `controllingLeg`, `keyholeCavity.fields.cavityDepth_um` with its band (descriptive), the module onset support
   statement and `meltDepthLink.consistencyNote`. An absent block gives `P8_NOT_IN_THIS_BUILD`; any other
   `schemaVersion` gives `RESEARCH_SCHEMA_UNKNOWN`; a block that fails the closed check (seven containers, no extra
   keys, band and note present on the four modules) gives `RESEARCH_BLOCK_MALFORMED`. All three are `unavailable` for
   every condition. The adapter never guesses or fills a value.
3. Reason codes (closed table in the protocol record, from P8 sections 3 to 5 and A1 to A4; Astra signs off the class
   split in phase 0):

   | Class | Codes on the scored leaf | Scoring |
   |---|---|---|
   | failed: inside the declared scope, the model gave no value | `CAVITY_ROOT_SCAN_UNRESOLVED`, `CAVITY_RESIDUAL_FAILED`, `NO_STRICTLY_STABLE_ROOT`, `OPTICAL_TRACE_UNRESOLVED`, `CYLINDER_CONVERGENCE_FAILED`, `TIP_SHELL_UNRESOLVED`, `CONDUCTION_EXTENT_UNRESOLVED`, `MELT_BRACKET_FAILURE`, `MELT_OPTIMIZER_FAILURE`, `MELT_CONVERGENCE_FAILED`, `NONFINITE_RESULT`, `RESEARCH_EVALUATION_FAILED`, and any code not in this table (`RESEARCH_REASON_UNKNOWN` added, so an unknown code can only hurt the arm) | APE +inf, in n, never dropped |
   | unavailable: outside the declared scope | `ALLOY_CONSTANT_CHAIN_NOT_ADMITTED`, `PECLET_OUTSIDE_NUMERICAL_SCOPE`, `ASPECT_BOUND_OUTSIDE_NUMERICAL_SCOPE`, `NUMERICAL_INPUT_BELOW_FLOOR`, `ONSET_REFERENCE_UNAVAILABLE`, `INVALID_INPUT`, `PREHEAT_OUTSIDE_PROPERTY_SCOPE`, `WAVELENGTH_UNSUPPORTED`, `POWDER_CONTEXT_UNSUPPORTED`, `UNSOURCED_PROPERTY_OVERRIDE` | out of n, listed, counted in coverage |
   | inherited | `MELT_LINK_NOT_AVAILABLE` (upstream cavity null) | takes the class of `keyholeCavity.fields.cavityDepth_um.reasonCode` |
   | never on the scored leaf | `NOT_APPLICABLE_BELOW_ONSET` (P8 sets it on `selectedBranch` and `rootScanRelativeDifference` only; a zero cavity below onset is a result and the linked depth is still computed) | an occurrence on the scored leaf is `RESEARCH_BLOCK_MALFORMED` |
   | refuses the freeze | `RESEARCH_OPTIONS_INVALID`, `RESEARCH_ARM_LIMIT_EXCEEDED` (impossible with `researchOptions` absent and the default 18 or 24 arms) | freeze fails with `RESEARCH_CONTRACT_BROKEN`, nothing written |

   `UNSOURCED_PROPERTY_OVERRIDE` is a P8 section 3 gate (spec line 113) for overrides that change a physical value; a
   full Build Job snapshot identical to the nominal resolved set is admitted there, and P8 reads `prop_overrides` as a
   request input (line 81). The served arm passes `snapshot["thermal"]`, so the code should not occur on this path;
   phase 6 asserts its absence on the Ti-6Al-4V and AlSi10Mg parity conditions, and an occurrence is reported as an
   integration finding, not absorbed silently.
4. Pinned P8 inputs: the freeze never passes `researchOptions` (P8 A1, an optional member of thermal and Build Job
   requests), so the block uses sourced defaults, the default arm manifest (Ti-6Al-4V 18 arms, AlSi10Mg 24) and no user
   endpoints. The adapter asserts it on every condition: no `inputProvenance` entry of kind `userInput`,
   `band.totalArms` equal to the default count, and the module arm manifest sha256 equal to
   `predictorIdentity.research.armManifestSha256`; a mismatch fails the freeze with `RESEARCH_CONTRACT_BROKEN`. The
   predictor identity records `research.researchOptions: "absent (sourced defaults)"` and `bandMethod
   "declared-ofat-envelope-v1"`.
5. Coverage and common subset: the research arm's n counts conditions with a value or a failure; unavailable conditions
   are listed with codes. The arm row always shows `scored on k of n conditions` (n = conditions the served arm scores)
   with the code counts. Statistics for served and research are also computed on the common subset (conditions where
   the research value is not unavailable) and shown as `common subset (k conditions)`, so the side-by-side comparison
   and the paired test use the same conditions. The research status needs n >= 12 inside its scope (7.3 step 3) even
   when the served arm has 12; k = 0 gives `unavailable`.
6. Bands (used now, not deferred): per condition the freeze records the scored leaf's `band` (4.5 item 2). The report
   gives `bandCoverage {complete {inside, total, wilson95}, partial {inside, total, failedArms}, unavailable}`: a
   measured condition depth inside `[min, max]` is counted separately for `complete` and `partial` bands (a partial
   envelope lost arms in `failedArms`, so it is narrower than declared and is never merged into the complete count);
   `unavailable` bands are listed. Wilson 95 % interval from `lpbf_calibration_stats.wilson` on the complete count. The
   sentence uses the P8 A4 framing: `share of conditions whose measured depth lies inside the declared one-at-a-time
   envelope (scenario support, not a probability or confidence interval)`. `statusSupport` of each band is summed
   into the label `envelope arms extrapolated or out of range in <k> conditions`. `band-fragile`: the research status
   recomputed with every complete-band condition at its band `min` and at its band `max`; a different status gives
   the label.
7. Consistency notes: per condition the freeze records `meltDepthLink.consistencyNote` (`status`, `worstArmStatus`,
   `statusSupport`, `sentence.value` verbatim, `knownContradictions[].id`). The report counts `status` per condition
   (`inRange`, `extrapolated`, `outOfRange`) and `worstArmStatus`, shows the counts as a label, and prints each
   distinct sentence once with its condition count. An `outOfRange` note on a condition whose value is present does not
   remove the value from scoring; the count is shown beside the statistics.
8. Paired comparison (phase 6): exact one-sided sign-flip test of research versus served APE (`paired_differences`,
   `signflip_p`, p <= 0.05) on the common subset, descriptive, never a verdict.
9. Goal deviation, stated (G1 in 7.7): GOAL roadmap item 1 asks for the served path and the P8 research arm
   (`keyholeCavity`, `meltDepthLink` with uncertainty bands) scored side by side. `meltDepthLink` is scored with its
   band; `keyholeCavity` is not scored against melt-pool depth, because a vapour cavity depth and a melt-pool depth are
   different quantities (evidence rule 4); it is shown per condition with `OBSERVABLE_MISMATCH` and scored only
   against `vapour-depression-depth` data, descriptively, in phase 6.
10. Freeze cost with P8 bands: P8 A4 evaluates every declared arm (18 or 24) inside each `calculate_meltpool_physics`
    call, and those arms already contain `0.95 P`, `1.05 P`, `0.95 d` and `1.05 d`. Running the block on the four
    served sensitivity calls would repeat the whole envelope four more times for no new information, so "P8 adds no
    solver call" was wrong. Plan: the P8 bump adds a solver switch that skips the research block (for example a
    `research_models=False` keyword on `calculate_meltpool_physics`), and the sensitivity calls use it; it must land in
    the P8 bump because `python/lpbf_thermal_solver.py` is a fingerprint manifest file. Research input fragility is read
    from the nominal call's band (its P and d arms are part of the declared envelope), never from extra calls. Cost per
    condition with the switch: 5 served solves plus 18 or 24 research arm evaluations; without it: 5 x (1 served plus 18
    or 24 arms). Every freeze child starts with a cold research cache (P8 A4 cache is in-process), so the cold cost is
    the planning number. Phase 0 estimates it from the committed synthetic reproduction
    (`docs/research/scripts/p8_amendment1_synthetic.py` at `b6e68dfe`) as a planning proxy only (P8 forbids treating
    it as product latency), re-derives the 48-condition cap per alloy for both cases (4.3), and phase 6 re-measures it
    on the merged build.
11. P8 integration check (phase 6, Astra and a fresh Opus gate): the adapter against the real block, the
    `UNSOURCED_PROPERTY_OVERRIDE` absence of item 3, the switch of item 10, and the reason-code table of item 3 against
    the merged code. If `researchModels` is null on the Build Job call path, Astra decides whether the research arm uses
    the direct thermal path (stated as a different property source) or stays unavailable. Nothing is wired until the P8
    bump is merged.

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
| D12 | no MELT counterpart | band coverage and consistency counts (7.6 items 6 and 7) are reported descriptively | P8 v2 output, no threshold attached |
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
   `lpbf_powder_layer_analysis.py:69` have their own zero-argument versions, which are not used).
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
   `implementationHash`, `servedIdentity`, `researchSchemaVersion`, `spentLedgerSha256`, `reasonsCatalogSha256`,
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
4. Research columns read `unavailable: P8_NOT_IN_THIS_BUILD` until P8 lands. With P8 v2 the research curve carries its
   band as a shaded envelope labelled `declared one-at-a-time envelope, not a probability` and the per-point
   `consistencyNote.status`, through the same adapter as the blind test (7.6).
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
| `python/test_lpbf_blind_stats.py`, `test_lpbf_served_arms.py`, `test_lpbf_p8_adapter.py`, `test_lpbf_user_blind_inputs.py`, `test_lpbf_user_blind_store.py`, `test_lpbf_user_blind_crash.py`, `test_lpbf_user_blind.py`, `test_lpbf_worker_blind_jobs.py`, `test_lpbf_spent_ledger.py`, `test_lpbf_spent_descriptive.py`, fixture `python/fixtures/p8_research_v2_synthetic.json` (copied from `b6e68dfe` with its blob hash) | Sonnet (Opus writes the isolation, blindness, leak and crash cases) |
| `data/blind/lpbf-user-blind-protocol-v1.json` and `data/blind/lpbf-user-blind-wording-v1.json` (generated), `data/blind/templates/blind_inputs_v1.csv`, `blind_targets_v1.csv`, `blind_metadata_v1.json` | Haiku |
| `data/benchmark/spent-ledger-v1.json` | Haiku transcribes, Opus reviews |
| `data/benchmark/spent-descriptive-reasons-v1.json` | Astra writes, Opus gates |
| `docs/LPBF_SPENT_DESCRIPTIVE_<date>.json` and `.view.json` (generated) | Sonnet runs, Opus checks |
| `docs/LPBF_USER_BLIND_TEST.md` (guide: templates, metadata meaning, protocol, what is and is not enforced, labels, manual archiving) | Haiku drafts, Opus reviews |
| `src/data/lpbfUserBlind.ts`, `src/services/lpbfUserBlindClient.ts`, `src/store/useUserBlindStore.ts` | Sonnet |
| `src/components/research/BlindTestPanel.tsx`, `BlindTestMetadataForm.tsx`, `BlindTestInputsStep.tsx`, `BlindTestReceiptView.tsx`, `BlindTestTargetsStep.tsx`, `BlindTestReportView.tsx`, `BlindTestList.tsx` | Sonnet |
| `src/components/research/blindTestHelp.ts` | Haiku drafts, Opus reviews wording |
| `src/data/lpbfSpentDescriptive.ts`, `src/data/lpbfSpentDescriptiveRecord.ts`, `src/components/3d-distortion-lab/SpentSetDescriptivePanel.tsx` | Sonnet |
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
| `docs/MODULE_EVIDENCE_INVENTORY.md` | research-hub and lpbf-dataset-comparison rows name the new files and next gap; the research-hub row also says that the wired registry keeps the legacy research-hub row, which does not list the LPBF worker calls the blind-test tab makes (they are bound under `3d-distortion-lab`), and that the contracted research-hub builder documents them | Haiku |
| `docker-compose.yml`, `Dockerfile` | `METALLIKSA_USER_BLIND_ROOT=/data/user-blind` and mkdir; `METALLIKSA_USER_BLIND_SINGLE_USER=true` in `docker-compose.yml` with the comment of 9.7 | Haiku |
| `.github/workflows/ci.yml` (protected) | append the new Python test modules to the explicit list (lines 80 to 130) | Haiku prepares; maintainer adds the Ceiling-Review trailer at the batch push |
| `PROOF.md`, `STATUS.md` | milestone entries only, labels unchanged statement | Opus |

Not changed: `server.ts`, `routes/*` (read-only mode is enforced in the worker after forwarding, not in a route),
`routes/AUTHORITY_ALLOWLIST*.json`, `python/module_registry.py`,
`python/module_registry_seed.json`, `src/App.tsx`, `src/modules/views.ts`, nav golden, every `*.ceiling.json`, every
fingerprint manifest file, `python/lpbf_implementation_fingerprint.expected`, `src/services/pythonComputationService.ts`.

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
3. `test_lpbf_p8_adapter.py` (self-contained fixture `python/fixtures/p8_research_v2_synthetic.json`, shapes from
   `docs/research/scripts/p8_amendment1_synthetic.json` at `b6e68dfe`, blob hash recorded): `P8_NOT_IN_THIS_BUILD` on
   this tree; a v2 block parses (value, band, consistency note, onset statement); every code of the 7.6 item 3 table
   lands in its class, `MELT_LINK_NOT_AVAILABLE` inherits the cavity class, an unknown code is failed with
   `RESEARCH_REASON_UNKNOWN`, `NOT_APPLICABLE_BELOW_ONSET` on the scored leaf is `RESEARCH_BLOCK_MALFORMED`; unknown
   schema and a missing container are unavailable; a `userInput` provenance, a non-default `totalArms` or a different
   arm manifest hash give `RESEARCH_CONTRACT_BROKEN`; `partial` and `unavailable` bands keep their `failedArms`; no
   value is filled or guessed.
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
   `export-protocol --check`.

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

## 12. Phased plan with acceptance checks

"Opus review" below means the gate rule of section 10: a fresh Opus gate for Opus-authored code, the Opus reviewer
otherwise.

### Phase 0, design gate and spikes (Opus; Astra; Haiku)

Work: commit nothing yet; a fresh Opus run gates this spec; Astra signs off the physics list (served-path definition and
parity fixtures, `FWHM_FACTOR` and D4sigma equivalence, `beam.quantity` radius handling, sensitivity arm set, leverage
cuts for 316L, IN718 and IN625, bare plate layer invariance, u_m f defaults for non-Ti64 alloys, the AlSi10Mg as-built
property convention of the served ledger, descriptive quantity mapping, the reasons catalogue sentences with locators,
the divergence list of 7.7); P8 v2 reconciliation against `b6e68dfe` (schema `p8-research-v2`, the
`ResearchNumericBand` and `consistencyNote` fields the adapter reads, the reason-code class table of 7.6 item 3, the
`researchOptions`-absent assertion, the solver switch for sensitivity calls agreed with the P8 owner as part of the P8
bump), signed by Astra and checked by the fresh Opus gate; Haiku times 48 conditions x 5 served calls
(include_process_map True and False) on the worker child path and reports p50 and p95, and times the 18 and 24 arm
evaluations per condition with the committed synthetic reproduction as a cold-cache planning proxy; Haiku transcribes the
spent ledger, Opus reviews; a spike adds the dataset-view browser-local op and runs `route-authority` and
`emit-module-registry --check`, then is discarded or kept; maintainer answers Q1 to Q5 (Q2 can wait until phase 6).
Accept: gate record with decisions; the condition caps of 4.3 (pre-P8 from the measured p95, P8 with and without the
switch from served p95 plus the proxy arm cost, each at most 60 s); Astra sign-off note including the P8 table.

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

### Phase 6, P8 integration after the P8 bump merges (Opus with Astra; Sonnet)

Work: enable `P8_ADAPTERS["p8-research-v2"]` against the real block; confirm the reason-code table and the absence of
`UNSOURCED_PROPERTY_OVERRIDE` on the served path (7.6 items 3 and 11); wire the sensitivity-call switch if the P8 bump
carries it; band coverage, partial bands and consistency counts on real output; common-subset statistics and the
sign-flip comparison; `vapour-depression-depth` quantity descriptive against `research:cavity`; label display per Q2;
regenerate the descriptive record at the new fingerprint and update the served-closure pin in the same reviewed commit;
re-measure freeze timing with a cold research cache and lower the caps if needed.
Accept: served parity unchanged across the bump; freezes made before P8 still score with `predictor changed since
freeze`; research arms populated or unavailable with codes and coverage labels; guard regex change applied only as
approved; fresh Opus gate.

### Phase 7, close-out (Opus; Haiku docs and docker)

Accept: `docs/LPBF_USER_BLIND_TEST.md` reviewed (it states the divergence list, the shared-host rule, the
secure-context limit and the CLI environment rule); inventory rows; docker env; PROOF entry in the P7b format (scope,
checks with exact counts and what was not run, limits, `labels unchanged: experimentalValidation=false, no label
promoted`, Build Job cache invalidation noted); STATUS milestone in Turkish; ci.yml additions prepared for the
maintainer's single Ceiling-Review trailer; one batch push only on the maintainer's word, explicit paths staged.

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

Maintainer actions (not questions): the Ceiling-Review trailer for `.github/workflows/ci.yml` at the batch push; the push
itself.

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
| 7.6 written against a stale P8 v1 contract | 7.6 rewritten against P8 v2 `b6e68dfe`: adapter, reason-code classes, pinned `researchOptions`, coverage, common subset, bands, consistency counts, freeze cost with 18 or 24 arms |
| `PREDICTOR_NOT_PINNED` narrower than the served path | served-closure pin and import-closure test; separate scorer identity; wording out of `protocolSha256` (3.6, 4.6) |
| Post-freeze exclusions | not-formed tracks counted as misses; losses counted for tracks and conditions; policy declared as D1 (4.4 item 2, 7.7) |
| No divergence list; `beam.profile` default; IN625 leverage | 7.7 in the protocol record and every report; `unknown` is a label; leverage at step 5 (6.2, 7.3, 7.4) |
| Calibration data and published data without a rule; 6.4 items 2 and 3 inconsistent | 6.4 items 7 and 8, the commitment exception applied to items 2, 3 and 7 |
| Acknowledgements inside the preview hash | top-level request field; explicit `ACK_REQUIRED` and `OVERLAP_CHANGED` checks at submit and in the child (4.1, 5 steps 5 and 6) |
| List and get on the serial queue | write-free reads on the estimate RPC; `user-blind-open` for a missing job record (3.2 item 1, 3.2.1) |
| Crash consistency | OS-held lock, commit points, ledger after commit, reconciliation, kill-at-each-step tests (3.5) |
| Missing refusals and limits | `TARGET_OUT_OF_RANGE`, `SYNTHETIC_EXAMPLE_ROW`, `FILE_NAME_INVALID`, `blockLabel` rule, export neutralisation, secure-context behaviour, shared-host refusal (4.2, 4.4, 6.1, 3.4, 9.7) |
| Request types not enumerated; anchor errors; Opus gating its own code | 3.2.1; anchors fixed in 3.1, 3.4, 8.3, 10.2; fresh Opus gate (section 10, section 12) |
