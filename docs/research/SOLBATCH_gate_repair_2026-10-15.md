# Solidification batch gate repair, 2026-10-15

Scope: `batch/solidification-2026-10-15`, baseline `5aca4599`. Integration authority: [SPEC](SPEC_solidification_integration_2026-10-15.md), especially sections 4.2-4.5, 4.8, 7 and 8.1. No scientific formula, coefficient, endpoint admission, W/D kernel, envelope validator, label rule, error rule or tolerance changes.

## Producer and consumer fixes

- Null morphology/transformation quantities name the existing blocking liquidus input and preserve missing-model/history reasons. Unknown aliases retain null values and explicitly name an unresolved alloy-identity input.
- Missing/invalid/quarantined worker results, unavailable segregation inventories, absent-R rapid solidification, and unavailable G/R CET/Laves containers name their refusal inputs. A provenance record describes an unadmitted request/sample; it does not admit a numerical value.
- CALPHAD's read-only literature adapter accepts the migrated `computed` segregation status, forwards the same per-quantity envelope, and removes the retired block-wide evidence label. Its card validates the envelope before rendering and displays the unresolved nominal-composition label. Coefficients, fractions, citations, observation identity and non-comparability warnings stay intact.
- The registered quantity view calls `pdasBandText` for the actual PDAS row, preserving two named model alternatives and SI conversion. No dead-code allowance was added.

## Every changed test expectation

| Test / fixture | Changed expectation | Reason |
|---|---|---|
| `test_solidification_front.AliasesAndInputs.test_unknown_alias_is_a_value_with_a_reason_not_an_error` | No provenance -> exactly `alloyIdentity`, explicitly `Unresolved`; existing null, alias-refusal and full-validator checks retained | Section 4.2 requires null quantities to name a real blocker. An unresolved identity record supplies no surrogate alloy or value. |
| `test_lpbf_p7b_sourced_constants.ProcessMapGrid.test_labels_unchanged` | Literal solver revision v25 -> `lpbf-build-job-sola1-v26` | The integrated SOL-A consumer revision already is v26. All unvalidated/non-production/sourcing-correction checks remain unchanged. |
| `test_calphad_literature_solidification.LiteratureSolidificationTests.test_block_matches_segregation_estimate_for_in718` | `available` -> `computed`; block-wide evidence-label equality -> exact upstream quantity equality, envelope validity, and absence of `evidenceLabel` | Sections 4.3 and 4.5 retire block-wide labels and map available -> computed. All numeric, citation and validity comparisons retained. |
| Same class, `test_block_matches_segregation_estimate_for_in625` | Block-wide evidence-label equality -> upstream quantity equality, envelope validity and absence of `evidenceLabel` | Same label migration; both k values and sensitivity comparisons retained. |
| Same class, `test_response_field_and_unchanged_calphad_status` | Old Literature estimate (screening) prefix -> every returned inventory has `Unresolved` | Nominal composition is a declared assumption; Unresolved takes precedence. Real-CALPHAD slow test remains skipped unless requested. |
| `tests/calphad-literature-solidification.test.tsx`, IN718 and IN625 rendering tests | Old label chip -> real quantity envelope and `Unresolved: composition`, with retired label absent | Show the actual determining-input label while preserving all band, source and non-comparability assertions. |
| Same TS file, new `legacy and corrupted evidence blocks never render numerical literature results` | New rejection checks for retired `available` and a quantity relabelled `Measured` | Regression guard for the adapter/card fix; neither payload may expose a numerical band/envelope. A valid new envelope cannot resurrect an injected retired `Measured` block-wide label. |
| `test_lpbf_calibration_frozen.DefaultResponseUnchanged.test_default_thermal_solver_response_is_byte_identical` | Three HTTP digests re-pinned: Eagar-Tsai `4ded6837` -> `9f56b27a`; Goldak `e9ae1725` -> `73eee9c2`; Rosenthal `719cec4f` -> `50ca3ad7` | Replaying the baseline front producer reproduces all three old hashes exactly. Replacing only the new `solidificationKinetics` with that old block makes the complete outputs equal; all other fields stay identical. Exact-byte guard retained. |
| Producer-bound payload equality fixtures | `build-job-microstructure-blocks.json`, `build-job-segregation-blocks.json`, `calphad-literature-solidification.json`, and affected JSON under `solidification-payloads/` regenerated from real producers | SPEC 4.8.3 requires real reproducible envelopes; no hand-edited numbers or relaxed parser assertions. The 15-file inventory and exact regeneration guard remain unchanged. |
| `test_lpbf_parity_golden` recording constants and 25 parity goldens | New manifest fingerprint/recording revision; exactly ten existing digest observations change, listed below | Necessary manifest producer fix; all numerical/reference observations and exact parity/error guards remain intact. |

## Necessary pin exception and parity scope

The only changed manifest file is `solidification_front.py`; changing its dependency metadata necessarily changes canonical fingerprint `1f8ad2b28ef951c4b062ee8f25ce4e463a519e6eb12ccd75098424cf556ff916` to `dc6f5fddfa40c38b24128284e0baf2e13990d034d17e5e0cff9095b1d03398d5`. Solver version and all solidification physics stay fixed. Initial unpinned full parity check found exactly these ten changed observations and no others:

- G11 `meltpool.0.canonicalSha256`, `meltpool.0.typedSha256`, `meltpool.1.canonicalSha256`, `meltpool.1.typedSha256`, `meltpool.2.canonicalSha256`, `meltpool.2.typedSha256`.
- G12 `solidification.defaultBlock`, `solidification.evaluate`, `solidification.unknownAlias`.
- G18 `meltpool.in625`.

The planned-drift record uses these exact keys, without globs. All geometry, peak-temperature, transient/reference replay, direct source-model PDAS/admission and error observations stay protected. This is software/metadata verification, not experimental validation. All 25 goldens were recorded once with `--record --force --twice --slow`, at code/pin commit `c6ec6dbf`, using the required locked Windows Python 3.12 runtime. A programmatic comparison with `5aca4599` confirms exactly the ten observation changes above, identical observation-key sets and solver version, and `recordedTwice: true` with two equal executions in every file. The full post-record `--check --slow` passes all 25 cases with no skip or drift. `test_lpbf_parity_golden.ParityHarnessTests`: 50/50 pass, including rejection/mutation tests; printed REFUSED/INCOMPLETE messages inside those negative tests are expected assertions.

## Separate records lane, untouched

- `data/calibration/lpbf-meltpool-error-bands-v1.json`, `.rows.json`, `.summary.json`.
- `src/utils/depthBiasWarning.ts` / `DEPTH_BIAS_BANDS_ID` (old bands id).
- All nine `demo/snapshots/*.json`, including `index.json`.
- `docs/LPBF_DATASET_COMPARISON_2026-10-14_p7b-sourced-constants.{json,md,view.json,common-subset.json,common-subset.md}`.
- `docs/LPBF_KEYHOLE_BENCHMARK_2026-10-14_p7b-sourced-constants.{json,md,view.json}`.
- `docs/LPBF_NIST_2525_ABSORPTANCE_COMPARISON_2026-10-14_p7b-sourced-constants.{json,md}` and `docs/LPBF_NIST_2716_THERMOGRAPHY_COMPARISON_2026-10-14_p7b-sourced-constants.{json,md}`.
- `docs/LPBF_LEADERBOARD_2026-10-14.json`.
- Historical pin references in P7b/SOL-A1 bump records and dated research records stay historical. This repair creates its own new bump record; none of those records are regenerated.

T-FRZ-3 stays red before merge. Review-trailer checks are not bypassed or satisfied by fabricated approvals; no review/approval trailer or push is authorized. Existing `.claude/` changes are excluded.

## Validation checkpoint

Full final unit: 1289 total, 1286 pass, 2 fail, 1 skip; the two failures are stale demo/bands record identity checks. Focused TS payload/segregation/CALPHAD tests including the new rejection guard: 18/18 pass. Component reachability: 12/12 pass. Lint passes. HTTP/pin checks: 7/7 pass. Final CI Python list: 127 entries, 1655 tests in 753.609 s; 2 failures, 1 error, 53 skips. Failures: `test_lpbf_calibration_frozen.FrozenGuards.test_diff_against_the_named_base_has_no_frozen_file` (T-FRZ-3; expected before merge) and `test_lpbf_benchmark.LeaderboardTests.test_committed_record_is_current_when_present` (stale records lane). Error: `test_lpbf_error_bands.CommittedArtefactTests.setUpClass` raises `BandsStale` on the old record. Unit failures: `tests/demo-snapshots.test.ts` / committed snapshot provenance and `tests/lpbf-error-bands.test.tsx` / summary pinned identity. None of these guards was changed or skipped. The base `origin/main` ceiling checker reports 28 unreviewed changes (CI/parity-harness history, pin and 25 goldens); no approval/review trailer was added. Raw logs are retained under `.runtime/solbatch/repair-*.log` (ignored local files). Real-browser interaction was not exercised; UI verification uses real Python fixtures and server-rendered components.

Producer-bound fixture files changed (exact names):

- `tests/fixtures/build-job-microstructure-blocks.json`
- `tests/fixtures/build-job-segregation-blocks.json`
- `tests/fixtures/calphad-literature-solidification.json`
- `tests/fixtures/solidification-payloads/build-job-microstructure.json`
- `tests/fixtures/solidification-payloads/build-job-segregation.json`
- `tests/fixtures/solidification-payloads/gr-map-in718.json`
- `tests/fixtures/solidification-payloads/gr-point-in718.json`
- `tests/fixtures/solidification-payloads/gr-point-ti6al4v.json`
- `tests/fixtures/solidification-payloads/thermal-alsi10mg.json`
- `tests/fixtures/solidification-payloads/thermal-in625.json`
- `tests/fixtures/solidification-payloads/thermal-in718.json`
- `tests/fixtures/solidification-payloads/thermal-keyhole.json`
- `tests/fixtures/solidification-payloads/thermal-ss316l.json`
- `tests/fixtures/solidification-payloads/thermal-ti6al4v.json`
- `tests/fixtures/solidification-payloads/worker-cfd-refused.json`
- `tests/fixtures/solidification-payloads/worker-result.json`

Additional CI identity job: 36 tests, OK with 1 host symlink-creation skip (35 pass); no skip rule changed.
