# tang bump: drift reasons (13203cac... -> 3a978739...)

Companion to `LPBF_IMPLEMENTATION_BUMP_2026-10-27_tang-advisory.json`, the tool output of

`python -B tools/lpbf_bump_record.py --from-revision fc585b4a --with-parity-check --slow --expect-drift <the 7 entries of LPBF_IMPLEMENTATION_BUMP_2026-10-27_tang-advisory.expect-drift.txt>`

run at commit `b1c59bb6` (the guarded re-pin to `3a978739eb184883089cf2d4e7078a0f310adccdd3abe52f267cd4c26f993143` with the pre-bump goldens restored byte for byte from `fc585b4a`; code `cab77a11`; `worktreeDirty: false`) in the locked interpreter `.runtime/lpbf-win-py312` (Python 3.12.10, numpy 2.2.6; the interpreter of the main checkout, called by absolute path from the lane worktree `Metalliksa-1-wt-tang`, branch `lane/tang-2026-10-27`). Result: **2 DRIFT (G11, G18), 23 PASS, 0 FAIL, 0 SKIP**; `pinMatchesToHash: true`, `versionUnchanged: true` (`enthalpy-fv-6`). Manifest files changed: 1 of 36, `lpbf_thermal_solver.py`.

The file name keeps "tang-advisory" (no rename). This record **replaces** the first version of the lane (pin `50cc550b`, record made at `9dcf838f`), which implemented the reviewer's first design (Tang above 1.0 as an advisory, printable verdict). The physics gate (APPROVE_WITH_CHANGES, finding 1) rejected a printable verdict at a large Tang exceedance; this version makes it risky.

Authority: maintainer approval of the planned Tang bump; design by the physics reviewer (Codex, read-only), and the gate's finding 1 for the ladder. **This bump is a decision-policy change, not a physics correction.** The Tang formula, the geometry and every number are unchanged; the review found no unit, factor or layer/depth error. It does not claim that the Tang criterion is wrong, that a risky cell has a defect, or that a printable cell is free of lack of fusion.

The allowlist is the full set of diff keys of a `--check --slow` run of this tree against the pre-bump goldens (not hand-picked): 7 exact keys.

## Cause

| id | cause | source | files |
|---|---|---|---|
| T-1 (verdict ladder) | `compose_verdict`: inconclusive (geometry not resolved, or the Tang index, width, depth or dH/hs null) > **risky** (Tang overlap index above 1.0, or the served regime is keyhole mode, cut 20, IN625 13.6) > printable. No rule issues do-not-print. `lof_tang` above 1.0 has status `warn` (a risk gate, `riskGates`; required 1.0, measured kept), never `blockingGates`. Tang risk reason (gate text, verbatim): "Modelled geometry indicates possible lack of fusion (Tang overlap index above 1.0); not an experimentally established defect.", followed by the index, W/h, D/t, the basis and (dH/hs >= 15) the keyhole depth-bias note. When both causes apply both reasons are listed and the risky headline names both ("Risky — possible lack of fusion (...) and keyhole mode by the regime classifier; screening result; fusion adequacy is not established; ..."); with Tang alone keyhole is not named. `dominantGate` is the first risk gate in gate order (`lof_tang` before `keyhole`). The 0.80 margin advisory is unchanged. `VERDICT_BASIS` `model-geometry-tang-keyhole-risk-screen`. Printable headline and empty-reasons text say "Screening result; fusion adequacy is not established."; "no sourced gate fails" and "Melt pool passes the Tang overlap criterion" are removed. | Harkin 2023 Eq. 5 (the geometric unit bound, quoting Tang, Pistorius and Beuth 2017; primary full text not retrieved, see Limits); Harkin 2023 Table 5 and Conclusions (analytic geometry error for one Ti-6Al-4V case, not transferred). No tolerance, porosity threshold or held-out tuning is claimed. | `lpbf_build_job_solver.py` (outside the manifest) |
| T-2 (suggested patch) | A patch is offered only when the re-run is printable (Tang at or below 1.0, below the keyhole cut, resolved geometry, inputs not null). The note states the Tang index of the point and "screening result; fusion adequacy is not established"; it never says "Verified" or "Tang unit criterion passes". | gate finding 2 | `lpbf_build_job_solver.py` |
| T-3 (labels) | `lackOfFusionRisk`: "Severe Lack of Fusion (Tang index > 1 — inter-track/layer unmelt)" -> "Tang overlap risk: index > 1 using modelled geometry; possible lack of fusion, not an established defect"; "Full Fusion Bonding (...)" -> "Tang overlap screen: index <= 1 using modelled geometry; fusion not established" (plus the unchanged margin suffix). `lackOfFusionStatus`, the index fields and the formula are unchanged. This is the only manifest change and the only cause of the 7 drifted digests. | design 3.2 | `lpbf_thermal_solver.py` |
| T-4 (texts, UI) | Process-window docstring; each process-window cell carries `tangIndex` (null when the extent is not computed); the selected-cell detail shows "Tang overlap index x on modelled melt-pool geometry (risk above 1.0). Screening result; fusion adequacy is not established."; `lpbfProcessWindow.ts` has a Tang risk sentence and count (never keyhole-only wording) and describes a stored Tang-blocked cell as a legacy result; the verdict explainer in `calculationExplainers.ts` no longer says do-not-print on Tang. Visible labels Printable / Risky are unchanged (the gate's label proposal is the maintainer's decision). The Build Job UI does not render `suggestedPatch`; the note is served in the API. | gate findings 1, 2 | `lpbf_process_window.py`, `src/data/lpbfProcessWindow.ts`, `LpbfProcessWindowMap.tsx`, `calculationExplainers.ts`, `pythonComputationService.ts`, `IndustrialLPBFDecisionLab.tsx` |
| T-5 (revision) | `BUILD_JOB_SOLVER_REVISION` `lpbf-build-job-solt-v28` -> `lpbf-build-job-tang-risk-v30` (v29 `lpbf-build-job-tang-advisory-v29` was the lane's advisory variant, retired) in `lpbf_job_cache.py` and `useLpbfBuildJobStore.ts`; the process-window cache key includes the revision and the implementation hash. | design 3.5 | `lpbf_job_cache.py`, TS store |

Not changed: the Tang formula and threshold 1.0, the 0.80 margin, `ENTHALPY_KEYHOLE` 20 and `ENTHALPY_KEYHOLE_IN625` 13.6 (13.6 is not transferred to IN718), the regime classifier, width/depth/length, balling, downskin, the literature box, recoater/distortion, `experimentalValidation=false`.

## Drift by case (exact keys, all in the `.expect-drift.txt`)

| case / observation | what moved |
|---|---|
| g11 `meltpool.0` (IN718, Tang 1.824, Fail) canonical + typed digests | `lackOfFusionRisk` "Severe Lack of Fusion ..." -> "Tang overlap risk: index > 1 using modelled geometry; possible lack of fusion, not an established defect" |
| g11 `meltpool.1` (Ti-6Al-4V, Tang 0.906, Pass, margin) canonical + typed | "Full Fusion Bonding (...); margin advisory ..." -> "Tang overlap screen: index <= 1 using modelled geometry; fusion not established; margin advisory ..." |
| g11 `meltpool.2` (316L, Tang 0.54, Pass) canonical + typed | "Full Fusion Bonding (...)" -> "Tang overlap screen: index <= 1 using modelled geometry; fusion not established" |
| g18 `meltpool.in625` (IN625, Tang 1.523, Fail) | same as `meltpool.0` |

`lackOfFusionRisk` is the only differing field of the four full `calculate_meltpool_physics` results; `geometry_um`, `peakTemperature_C` and every G1 to G10, G12 to G17, G19 and NPZ observation are bit equal. `test_lpbf_calibration_frozen` HTTP_GOLDEN (316L 200/900, three kernels): the three digests move; restoring the former label in the new output reproduces the three SOL-T digests exactly.

## Process-window verdict counts

Default 11 x 11 grid of `lpbf_process_window` (0.5 x literature-box minimum to 1.5 x maximum) at the UI default settings of the four presets (`deriveSpecimenProperties`: beam 80 um, layer 40 um, hatch 100 um; preheat IN718 200 C, Ti-6Al-4V 150 C, 316L 80 C, AlSi10Mg 160 C). Before: tree `fc585b4a` (revision v28); after: `cab77a11` (v30). printable / risky / do-not-print / inconclusive / error, and the risk causes of the risky cells after (Tang only / keyhole only / both):

| Alloy | before | after | risky by cause after | moves |
|---|---|---|---|---|
| IN718 | 0 / 58 / 58 / 5 / 0 | 0 / 116 / 0 / 5 / 0 | 27 / 58 / 31 | 58 do-not-print -> risky |
| Ti-6Al-4V | 0 / 68 / 53 / 0 / 0 | 0 / 121 / 0 / 0 / 0 | 31 / 68 / 22 | 53 do-not-print -> risky |
| 316L | 0 / 22 / 91 / 8 / 0 | 0 / 113 / 0 / 8 / 0 | 56 / 22 / 35 | 91 do-not-print -> risky |
| AlSi10Mg | 62 / 43 / 16 / 0 / 0 | 62 / 59 / 0 / 0 / 0 | 16 / 43 / 0 | 16 do-not-print -> risky |

Every moved cell was do-not-print before and is risky now; no printable, risky or inconclusive cell changed. **IN718 has no printable cell at these settings** (every resolved cell has a Tang index above 1.0 at hatch 100 um and layer 40 um, or is keyhole mode). This is reported, not forced: no threshold, grid or input was changed. The first lane version's IN718 acceptance ("at least one printable cell") no longer holds and was not pursued. Moved cells (P W / v mm/s), by risk cause after the bump:

- IN718, Tang only (27): 60/275, 60/397.5, 60/520, 60/642.5, 60/765, 60/887.5, 99/397.5, 99/520, 99/642.5, 99/765, 99/887.5, 99/1010, 99/1132.5, 99/1255, 99/1377.5, 99/1500, 138/765, 138/887.5, 138/1010, 138/1132.5, 138/1255, 138/1377.5, 138/1500, 177/1132.5, 177/1255, 177/1377.5, 177/1500. Tang and keyhole (31): 99/275, 138/397.5, 138/520, 138/642.5, 177/642.5, 177/765, 177/887.5, 177/1010, 216/765, 216/887.5, 216/1010, 216/1132.5, 216/1255, 216/1377.5, 216/1500, 255/887.5, 255/1010, 255/1132.5, 255/1255, 255/1377.5, 255/1500, 294/1132.5, 294/1255, 294/1377.5, 294/1500, 333/1255, 333/1377.5, 333/1500, 372/1377.5, 372/1500, 411/1500.
- Ti-6Al-4V, Tang only (31): 75/350 to 75/1800 (11 cells), 109.5/640 to 109.5/1800 (9), 144/930 to 144/1800 (7), 178.5/1365, 178.5/1510, 178.5/1655, 178.5/1800. Tang and keyhole (22): 109.5/495, 144/640, 144/785, 178.5/785, 178.5/930, 178.5/1075, 178.5/1220, 213/1075 to 213/1800 (6), 247.5/1365, 247.5/1510, 247.5/1655, 247.5/1800, 282/1510, 282/1655, 282/1800, 316.5/1655, 316.5/1800.
- 316L, Tang only (56): 75/300 to 75/780 (5), 102/300 to 102/1260 (9), 129/300 to 129/1500 (11), 156/540 to 156/1500 (9), 183/660 to 183/1500 (8), 210/900 to 210/1500 (6), 237/1020 to 237/1500 (5), 264/1260, 264/1380, 264/1500. Tang and keyhole (35): 156/300, 156/420, 183/420, 183/540, 210/540, 210/660, 210/780, 237/540, 237/660, 237/780, 237/900, 264/660 to 264/1140 (5), 291/780 to 291/1500 (7), 318/900 to 318/1500 (6), 345/900 to 345/1500 (6).
- AlSi10Mg, Tang only (16): 140/615 to 140/2100 (10 cells), 183/1440, 183/1605, 183/1770, 183/1935, 183/2100, 226/2100.

Pinned in `test_lpbf_process_window.TangRiskDefaultGrid` (counts, cause mix, only former do-not-print cells moved, `tangIndex` > 1.0 on every Tang-risky cell).

## Outside the manifest and regenerated records

Tests: `test_lpbf_build_job_verdict_tier1.py` (`TangRisk`: 1.0 printable, 1.001 risky, 9.3 risky never do-not-print, Tang plus keyhole lists both causes, 0.80 margin, null Tang/width/depth and unresolved geometry inconclusive, keyhole cuts 20 / 13.6 unchanged, pre-bump geometry of IN718 280/940/100 bit equal), `test_lpbf_p7a_rules_and_nulls.py`, `test_lpbf_suggested_patch.py`, `test_lpbf_build_job.py`, `test_lpbf_p7b_sourced_constants.py` (revision), `test_lpbf_process_window.py`, `test_lpbf_calibration_frozen.py` (HTTP digests); TS `display-lane`, `lpbf-process-window`, `lpbf-verdict-tier1`, `build-job-kinetics-panel`. `tests/fixtures/how-calculated/meltpool-*-ti64.json` regenerated from real `lpbf_thermal_solver.py` runs with the same inputs and kept keys (only the label and `computeTimeMs` move). Regenerated in their own commits after this record: parity goldens with GOLDEN_FINGERPRINT and HTTP_GOLDEN, error bands and `DEPTH_BIAS_BANDS_ID`, demo snapshots. Known red on this branch: T-FRZ-3 (`test_diff_against_the_named_base_has_no_frozen_file`, by construction for any manifest change). Left as historical: the solidification payload fixtures naming v28; the leaderboard and NIST records (geometry only, bit equal; not re-run). Demo `solverBinaryHash` stays null (the lane backend reports none; no hash is invented).

## Limits

The Tang, Pistorius and Beuth 2017 full text was not retrieved (not in the library index; the publisher link was not readable), so the original shape and depth datum are not independently checked; the unit bound is used as quoted by Harkin 2023 Eq. 5. Risky on Tang means a modelled-geometry indication, not a measured or predicted defect; printable means Tang at or below 1.0 and below the keyhole cut on modelled geometry, not a printability proof. Evidence labels unchanged: `experimentalValidation=false`, screening only.
