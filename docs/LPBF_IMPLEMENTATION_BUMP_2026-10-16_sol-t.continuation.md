# SOL-T continuation: step 1 complete, stopped during step 2

Original brief: `C:/Users/can02/AppData/Local/Temp/claude/C--Users-can02-Projects-metalliksaa/63bd2bb8-c90d-4910-8a02-f55be6809988/scratchpad/codex_solt_install.md`.
Original from HEAD: `d2f8e5d194456cb4133162b2a3f96238ba636bd2`; branch `feat/solidification-solt`.

## Binding lead decision

The served `compose_verdict` refusal for `in625` is the contract, not a helper bug. Before and after capture its verdict as `{"verdictStatus": "refused", "error": "<exception class>: <message>"}`. A changed refusal is a moved value. Capture geometry, processParameters, grid, defectDiagnostics, regime and extentStatus normally. No new verdict rule, alloy substitution or skipping IN625. This replaces the previous stopped-note characterization.

## Completed step 1

`.before.json` records all 735 synthetic cases (five alloys, three kernels, 49 points), including 147 IN625 exact refusals. Required fields were checked. The capture helper and its two unit tests pass. The locked interpreter's from-head `--check --slow` gave all 25 PASS (`sol-t-baseline-parity.log`). The original `.from.json` remains the pre-bump skeleton.

## Stop during step 2; do not claim an installation

- UI/CSV verification (`npx tsx --test tests/sol-t-disclosure.test.tsx tests/quantity-envelope.test.ts tests/solidification-transient-diagnostics.test.tsx`) could not load React: `ERR_MODULE_NOT_FOUND: Cannot find package 'react'`. Nine non-React checks passed; the two React test files failed to load. Dependencies were not installed after the failure, per the user's stop rule.
- The already-running Python installation diagnostic additionally shows a real implementation error: D13 used `implementation_fingerprint()` as field identity and placed it outside `provenance.implementationHash`; `result.implementationHashOccurrencesAfterStrip` moved 0 -> 4. This is not accepted drift. G2 `fixture.strippedResultEqualExceptMaterialIdentity` also becomes false after parent/D13 metadata changes; no RT8 exception was implemented or claimed.
- The diagnostic and `.after.json` capture were started before the stop. A later metadata-only source edit (rejecting overridden endpoints from nominal admission) landed while they were running. The diagnostic therefore spans fingerprints `6d3267e11a2aee11443ddd9ab7920dbfc1947cd91d99c2db39410f04cf531d21` and `10d92a2502288e3904e2b1392a4d3c08cfdefe9fa61bd4e801b4b252439ddde4`; neither run is an immutable installation-head receipt. Rerun from one frozen source head only after a lead continuation decision. Do not use this diagnostic as the step-4 bump record or RT8 decision.
- `.after.json` and `.preliminary-moves.json` are unpinned diagnostics only, not committed installation evidence. All 147 IN625 refusals are unchanged. Preliminary maximum signed W/D changes (um): Ti64 0/0, IN718 0/0, IN625 0/0, 316L -4.6/-5.9, AlSi10Mg -2.6/-1.3.
- 93 focused Python checks passed before the final metadata-only override guard; eight SOL-T/capture checks passed after that guard. `git diff --check` passed. No full CI, lint, bundle, browser QA or final parity pass is claimed.
- Graft freshness timed out at 300 seconds; source/rg fallback was used. No graph freshness or coverage claim is made.

## Unfinished installation

Production edits are deliberately uncommitted and incomplete. The complete admission records are copied into `four_alloy_materials.py`; the two changed pairs and Al Kirchhoff endpoint coordinates were installed; source identities and blanket-null front model v3 were wired; v27 cache revision and per-value D13 envelope/UI/CSV were prepared. Remaining issues include the fingerprint leak, exact G2 replay handling under RT8, complete source/registry/secondary consistency, final UI/CSV tests and browser QA. The new `python/test_sol_t_installation.py`, TS test and synthetic D13 fixture are unfinished work, not part of the completed step-1 preparation commit.

The live pin remains `dc6f5fddfa40c38b24128284e0baf2e13990d034d17e5e0cff9095b1d03398d5`. Steps 3-10 have not begun: no guarded installation commit/new pin, exact drift allowance, RT8 decision, golden recording, P8 re-pin, R-lane bands/demo/history regeneration, PROOF entry or final acceptance run. No measured bands were opened; no forbidden dataset, PDF or `.orchestra/external-data/bitharas2022` file was touched. No push or approval trailer.

Continuation requires the lead's disposition of these uncovered failures under the original stop rule. Resume step 2, not step 1; do not redo the completed baseline.

Tracked working-tree edits at stop:
- `python/four_alloy_materials.py`
- `python/lpbf_job_cache.py`
- `python/lpbf_material_registry.py`
- `python/lpbf_openfoam.py`
- `python/lpbf_simulation.py`
- `python/lpbf_thermal_solver.py`
- `python/quantity_envelope.py`
- `python/solidification_front.py`
- `python/test_lpbf_build_job.py`
- `python/test_lpbf_p7a_rules_and_nulls.py`
- `python/test_lpbf_p7b_sourced_constants.py`
- `python/test_quantity_envelope.py`
- `python/test_quantity_envelope_payloads.py`
- `python/test_solidification_front.py`
- `src/components/3d-distortion-lab/LpbfEngineeringSimulation.tsx`
- `src/components/SolidificationQuantities.tsx`
- `src/generated/lpbfMaterialAuthority.json`
- `src/services/lpbfSimulationService.ts`
- `src/store/useLpbfBuildJobStore.ts`
- `src/utils/solidificationDisplay.ts`
- `tests/build-job-kinetics-panel.test.tsx`

## Completed diagnostic (not step 4 / not an exact-key approval)

The unallowlisted installation diagnostic completed: 3 PASS, 22 FAIL, no final parity pass. Its two source hashes are disclosed above. Log: `sol-t-installation-diagnostic.log`. Preliminary observation-diff counts from that log (not installation-head-bound):

- `g1_v1_60w_in718`: 9 changed observations; FAIL
- `g2_bare_plate_100w_corridor`: 9 changed observations; FAIL
- `g3_powder_stripe_multilayer`: 9 changed observations; FAIL
- `g3_powder_island`: 9 changed observations; FAIL
- `g4_layered_plate`: 9 changed observations; FAIL
- `g5_evaporation`: 9 changed observations; FAIL
- `g6_screening_and_fallback`: 24 changed observations; FAIL
- `g7_mesh_study`: 9 changed observations; FAIL
- `g7_timestep_study`: 9 changed observations; FAIL
- `g3_powder_meander_unidirectional`: 18 changed observations; FAIL
- `g13_source_quadrature_refinement`: 0 changed observations; PASS
- `g14_calibration_measurements`: 18 changed observations; FAIL
- `g15_bare_plate_square_optical_observer`: 9 changed observations; FAIL
- `g16_non_in718_transient`: 42 changed observations; FAIL
- `g17_evaporation_ti6al4v`: 9 changed observations; FAIL
- `g17_evaporation_316l`: 92 changed observations; FAIL
- `g17_evaporation_alsi10mg`: 92 changed observations; FAIL
- `g18_in625_latent_heat`: 1 changed observations; FAIL
- `g19_emissivity_echo`: 10 changed observations; FAIL
- `g8_observers`: 10 changed observations; FAIL
- `g9_material_snapshots`: 68 changed observations; FAIL
- `g10_openfoam_case_generation`: 0 changed observations; PASS
- `g11_build_job_meltpool`: 8 changed observations; FAIL
- `g12_analytical_modules`: 4 changed observations; FAIL
- `npz_determinism`: 0 changed observations; PASS
