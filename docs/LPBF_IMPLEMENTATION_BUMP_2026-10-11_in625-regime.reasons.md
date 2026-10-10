# in625-regime bump: drift reasons (ec7e1f7a... -> 0d52d7f7...)

Companion to `LPBF_IMPLEMENTATION_BUMP_2026-10-11_in625-regime.json`, the tool output of

`python -B tools/lpbf_bump_record.py --from-revision f8c2f3b9 --with-parity-check --slow --expect-drift <the 7 entries of LPBF_IMPLEMENTATION_BUMP_2026-10-11_in625-regime.expect-drift.txt>`

run at commit `c2e4c63d` (after the re-pin to `0d52d7f707b98fc588c0972c1c198315d3c1071ed1c7ad7ab91616e69b5248e8`, tree clean, `worktreeDirty: false`) in the locked interpreter `.runtime/lpbf-win-py312` (Python 3.12.10, numpy 2.2.6; G11 and G18 ran, not skipped). Result: **2 DRIFT, 23 PASS, 0 FAIL**; `pinMatchesToHash: true`, `versionUnchanged: true` (`enthalpy-fv-6`). Base: `f8c2f3b9` on `research/in625-regime-threshold` (pin `ec7e1f7a...`, parity `--check --slow` all PASS there before the edit). Manifest files changed (1 of 36): `lpbf_thermal_solver.py`.

The allowlist is the full set of diff keys of a `--check --slow --expect-unpinned` run of this tree (not hand-picked): 7 exact keys, 6 in G11 and 1 in G18, the two cases that call `calculate_meltpool_physics`. The transient reference path never reads the regime, so G1 to G10, G12 to G17, G19 and the NPZ case are bit-equal. `thermalSolver.classify_enthalpy_regime` (G11) did not drift: called without a material name the classifier keeps the shared 15 / 20 cuts.

## Cause

| id | cause | source | files |
|---|---|---|---|
| IR-1 | Inconel 625 gets its own keyhole-mode cut `ENTHALPY_KEYHOLE_IN625 = 13.6` on the app index (`regime_keyhole_cut`). Fitted on the fit split only (56 EOS M270 IN625 tracks of NIST mds2-2923, truth depth > half width, fixed before the run); one declared run on 13 held-out IN625 tracks (mds2-2923 AMMT spot series and Lane et al. 2020 Table 3): 0 errors, balanced accuracy 1.00, against 3 errors and 0.70 for the shared cut 20. The held-out data place the onset only in (12.67, 13.94]; 13.6 is the fit-split point estimate, not a held-out-validated value. The transition cut 15 is not moved, so IN625 has no transition band. The process-map grid uses the same per-alloy cut. `regimeKeyholeThreshold` is served in `meltPoolGeometry` and `processWindowMap`. `REGIME_THRESHOLD_BASIS` and `REGIME_MATERIAL_NOTE_IN625` rewritten. No number changes. | `docs/research/PREDECLARED_in625_regime_2026-10-11.md`, `RESULTS_in625_regime_2026-10-11.{md,json}`, `SOURCES_in625_regime_2026-10-11.md` | `lpbf_thermal_solver.py` |

A 693-case snapshot (7 alloys x 11 P-v pairs x spots 80 / 100 / 170 um x 3 kernels, 80 C preheat) against `f8c2f3b9`: every width, depth, length, vapour-cavity depth, eta_eff, temperature, contour, thermal slice, grid width and grid depth is bit-equal. Only these keys differ: `regimeBasis` (both blocks, every case), the new `regimeKeyholeThreshold` (both blocks, every case), `regimeMaterialNote` (IN625), and for IN625 only `meltPoolGeometry.regime` and `processWindowMap.currentOperatingPoint.regime` (21 cases: 18 Transition to Keyhole Mode, 3 Conduction to Keyhole Mode) plus grid `regime` and `color` cells with 13.6 <= dH/hs < 20.

## Drift by case

| case / observation | what changed in the hashed dict |
|---|---|
| g11 `meltpool.0` IN718 200/800/80 Rosenthal (dH/hs 23.67) | `regimeBasis` text (both blocks), new `regimeKeyholeThreshold` 20.0 (both blocks); regime, geometry and grid unchanged |
| g11 `meltpool.1` Ti-6Al-4V 280/1200/70 Eagar-Tsai (42.25) | same as above |
| g11 `meltpool.2` 316L 370/600/60 Goldak (62.08) | same as above |
| g11 `...canonicalSha256` / `...typedSha256` x3 | tool hashes of the dicts above; the `meltpool.N.geometry_um` and `peakTemperature_C` companions did not drift |
| g18 `meltpool.in625` IN625 200/800/80 Rosenthal (25.62) | regime stays Keyhole Mode (25.62 >= 20 and >= 13.6); `regimeBasis`, `regimeMaterialNote` (IN625 note), new `regimeKeyholeThreshold` 13.6 (both blocks); grid cells 0, 9, 10, 18, 19, 20 (dH/hs 15 to 20) Transition (#38bdf8) to Keyhole Mode (#ef4444) |

## Outside the manifest (same branch, not hashed)

`lpbf_public_datasets.classify_regime` mirrors the IN625 cut (`keyhole_cut`, `REGIME_PARAMETERS.keyholeEnthalpyByAlloy`); committed dataset-comparison records are history and were not regenerated. `lpbf_depth_bias.py` and `src/utils/depthBiasWarning.ts`: the UNDER note names the Lane CBM tracks as Keyhole Mode and its basis states that IN625 indices 13.6 to 15 have no keyhole increment and no held-out depth check (direction logic unchanged, label driven). `BUILD_JOB_SOLVER_REVISION` v18 to v19 (`lpbf-build-job-in625-regime-v19`): the four build-job alloys keep their labels, but the served text changed. Error bands keep their own pre-declared 15 / 20 enthalpy classes (configuration unchanged); they were regenerated only for the new fingerprint.

## Goldens

Not re-recorded in this commit (separate guarded commit).

## Labels

Evidence labels unchanged: `experimentalValidation=false`, `validationStatus=unvalidated`, `productionReady=false`. Keyhole mode is not keyhole porosity. The IN625 cut is tied to the app's legacy-estimated IN625 property set and to a 20 C plate in the fit; a property change requires a refit.
