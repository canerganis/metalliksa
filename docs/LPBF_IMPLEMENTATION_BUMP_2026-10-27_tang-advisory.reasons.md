# tang-advisory bump: drift reasons (13203cac... -> 50cc550b...)

Companion to `LPBF_IMPLEMENTATION_BUMP_2026-10-27_tang-advisory.json`, the tool output of

`python -B tools/lpbf_bump_record.py --from-revision fc585b4a --with-parity-check --slow --expect-drift <the 7 entries of LPBF_IMPLEMENTATION_BUMP_2026-10-27_tang-advisory.expect-drift.txt>`

run at commit `9dcf838f` (the guarded re-pin to `50cc550b834bd29d81ef5fc52e0d7acd892641524283aac2c637f46e3087c0d0`; code `e2e0cab7`; `worktreeDirty: false`; the 25 goldens still recorded at `13203cac`) in the locked interpreter `.runtime/lpbf-win-py312` (Python 3.12.10, numpy 2.2.6; the interpreter of the main checkout, called by absolute path from the lane worktree `Metalliksa-1-wt-tang`, branch `lane/tang-2026-10-27`). Result: **2 DRIFT (G11, G18), 23 PASS, 0 FAIL, 0 SKIP**; `pinMatchesToHash: true`, `versionUnchanged: true` (`enthalpy-fv-6`). Manifest files changed: 1 of 36, `lpbf_thermal_solver.py`.

Authority: maintainer approval of "Tang to advisory" as a planned bump; design by the physics reviewer (Codex, read-only), sections 3 and 4. **This bump is a decision-policy change, not a physics correction.** The Tang formula, the geometry and every number are unchanged; the review found no unit, factor or layer/depth error. It does not claim that the Tang criterion is wrong or that a printable cell is free of lack of fusion.

The allowlist is the full set of diff keys of a `--check --slow --expect-unpinned` run of this tree before the re-pin (not hand-picked): 7 exact keys.

## Cause

| id | cause | source | files |
|---|---|---|---|
| TA-1 (verdict ladder) | `compose_verdict`: `lof_fail` keeps its numeric meaning (served status Fail or index > 1.0) but leaves the ladder. Ladder: inconclusive (geometry not resolved, or the Tang index, width, depth or dH/hs null) > risky (served regime keyhole mode, cut 20, IN625 13.6) > printable. No rule issues do-not-print. Above 1.0 the `lof_tang` gate is `advisory` (required 1.0, measured kept), listed in `advisoryGates`, never in `blockingGates`, never `dominantGate`; the verbatim design text "Advisory: Tang overlap index exceeds 1.0 using modelled melt-pool geometry. Lack of fusion is possible; this screen cannot establish whether fusion is adequate. The advisory does not change the verdict." goes to `advisories` and `reasons` with the index, W/h, D/t, the basis and (dH/hs >= 15) the keyhole depth-bias note. The 0.80 margin advisory is unchanged. `VERDICT_BASIS` `model-geometry-advisory-keyhole-screen`. Printable headline and empty-reasons text say "Screening result; fusion adequacy is not established."; "no sourced gate fails" and "Melt pool passes the Tang overlap criterion" are removed. | Harkin 2023 Eq. 5 (quoting Tang, Pistorius and Beuth 2017; primary full text not retrieved, see Limits); Harkin 2023 Table 5 and Conclusions (analytic geometry about 40 % wide and 21 % shallow for one Ti-6Al-4V case; not transferred to IN718) | `lpbf_build_job_solver.py` (outside the manifest) |
| TA-2 (suggested patch) | A patch is offered when the re-run is printable (geometry resolved, verdict inputs not null, below the keyhole cut); a Tang overlap advisory at the suggested point is listed in `suggestedPatchAdvisories`, and zero-advisory candidates are still preferred. The note no longer says "Tang unit criterion passes" or "Verified"; it says "Re-run by the solver ... (screening result; fusion adequacy is not established)". | design 3.1 | `lpbf_build_job_solver.py` |
| TA-3 (labels) | `lackOfFusionRisk`: "Severe Lack of Fusion (Tang index > 1 — inter-track/layer unmelt)" -> "Tang overlap advisory: index > 1 using modelled geometry"; "Full Fusion Bonding (...)" -> "Tang overlap screen: index <= 1 using modelled geometry; fusion not established" (plus the unchanged margin suffix). `lackOfFusionStatus`, the index fields and the formula are unchanged (kept for compatibility; a comment says they are not a verdict gate). This is the only manifest change and the only cause of the 7 drifted digests. | design 3.2 | `lpbf_thermal_solver.py` |
| TA-4 (texts) | Process-window docstring states the new ladder; `lpbfProcessWindow.ts` describes Tang as an advisory (`tangAdvisoryCells`) and a stored cell where `lof_tang` blocks as a legacy result of an earlier solver revision (`legacyTangBlockedCells`, cell sentence "Legacy result: ..."), never as current policy; `LOF_DIAGNOSTIC_HINT`, `LOF_DIAGNOSTIC_BASIS` and the `verdictBasis` doc comment follow. | design 3.3, 3.4 | `lpbf_process_window.py`, `src/data/lpbfProcessWindow.ts`, `IndustrialLPBFDecisionLab.tsx`, `pythonComputationService.ts` |
| TA-5 (revision) | `BUILD_JOB_SOLVER_REVISION` `lpbf-build-job-solt-v28` -> `lpbf-build-job-tang-advisory-v29` in `lpbf_job_cache.py` and `useLpbfBuildJobStore.ts`; retired lists gain v28. The process-window cache key includes the revision and the implementation hash (test `test_cache_hit_and_miss_on_solver_revision`), so a warm worker cannot return a pre-bump verdict. | design 3.5 | `lpbf_job_cache.py`, TS store |

Not changed: the Tang formula and threshold 1.0, the 0.80 margin, `ENTHALPY_KEYHOLE` 20 and `ENTHALPY_KEYHOLE_IN625` 13.6 (13.6 is not transferred to IN718), the regime classifier, width/depth/length, balling, downskin, the literature box, recoater/distortion, `experimentalValidation=false`.

## Drift by case (exact keys, all in the `.expect-drift.txt`)

| case / observation | what moved |
|---|---|
| g11 `meltpool.0` (IN718, Tang 1.824, Fail) canonical + typed digests | `lackOfFusionRisk` "Severe Lack of Fusion ..." -> "Tang overlap advisory: index > 1 using modelled geometry" |
| g11 `meltpool.1` (Ti-6Al-4V, Tang 0.906, Pass, margin) canonical + typed | "Full Fusion Bonding (...); margin advisory ..." -> "Tang overlap screen: index <= 1 using modelled geometry; fusion not established; margin advisory ..." |
| g11 `meltpool.2` (316L, Tang 0.54, Pass) canonical + typed | "Full Fusion Bonding (...)" -> "Tang overlap screen: index <= 1 using modelled geometry; fusion not established" |
| g18 `meltpool.in625` (IN625, Tang 1.523, Fail) | same as `meltpool.0` |

A key-by-key diff of the four full `calculate_meltpool_physics` results (pre-bump tree `fc585b4a` vs this tree) shows `defectDiagnostics.lackOfFusionRisk` as the only differing field; `geometry_um`, `peakTemperature_C`, every G1 to G10, G12 to G17, G19 and NPZ observation are bit equal. `test_lpbf_calibration_frozen` HTTP_GOLDEN (316L 200/900, three kernels): the three digests move; restoring the former label in the new output reproduces the three SOL-T digests exactly.

## Process-window verdict counts (design section 4)

Default 11 x 11 grid of `lpbf_process_window` (0.5 x literature-box minimum to 1.5 x maximum) at the UI default settings of the four presets (`deriveSpecimenProperties`: beam 80 um, layer 40 um, hatch 100 um; preheat IN718 200 C, Ti-6Al-4V 150 C, 316L 80 C, AlSi10Mg 160 C). Before: tree `fc585b4a` (revision v28); after: `e2e0cab7` (v29). printable / risky / do-not-print / inconclusive / error:

| Alloy | before | after | moves |
|---|---|---|---|
| IN718 | 0 / 58 / 58 / 5 / 0 | 27 / 89 / 0 / 5 / 0 | 27 do-not-print -> printable, 31 do-not-print -> risky |
| Ti-6Al-4V | 0 / 68 / 53 / 0 / 0 | 31 / 90 / 0 / 0 / 0 | 31 -> printable, 22 -> risky |
| 316L | 0 / 22 / 91 / 8 / 0 | 56 / 57 / 0 / 8 / 0 | 56 -> printable, 35 -> risky |
| AlSi10Mg | 62 / 43 / 16 / 0 / 0 | 78 / 43 / 0 / 0 / 0 | 16 -> printable |

Every moved cell was do-not-print before; no printable, risky or inconclusive cell changed. Moved cells (P W / v mm/s):

- IN718 -> printable: 60/275, 60/397.5, 60/520, 60/642.5, 60/765, 60/887.5, 99/397.5, 99/520, 99/642.5, 99/765, 99/887.5, 99/1010, 99/1132.5, 99/1255, 99/1377.5, 99/1500, 138/765, 138/887.5, 138/1010, 138/1132.5, 138/1255, 138/1377.5, 138/1500, 177/1132.5, 177/1255, 177/1377.5, 177/1500. -> risky: 99/275, 138/397.5, 138/520, 138/642.5, 177/642.5, 177/765, 177/887.5, 177/1010, 216/765, 216/887.5, 216/1010, 216/1132.5, 216/1255, 216/1377.5, 216/1500, 255/887.5, 255/1010, 255/1132.5, 255/1255, 255/1377.5, 255/1500, 294/1132.5, 294/1255, 294/1377.5, 294/1500, 333/1255, 333/1377.5, 333/1500, 372/1377.5, 372/1500, 411/1500.
- Ti-6Al-4V -> printable: 75/350, 75/495, 75/640, 75/785, 75/930, 75/1075, 75/1220, 75/1365, 75/1510, 75/1655, 75/1800, 109.5/640, 109.5/785, 109.5/930, 109.5/1075, 109.5/1220, 109.5/1365, 109.5/1510, 109.5/1655, 109.5/1800, 144/930, 144/1075, 144/1220, 144/1365, 144/1510, 144/1655, 144/1800, 178.5/1365, 178.5/1510, 178.5/1655, 178.5/1800. -> risky: 109.5/495, 144/640, 144/785, 178.5/785, 178.5/930, 178.5/1075, 178.5/1220, 213/1075, 213/1220, 213/1365, 213/1510, 213/1655, 213/1800, 247.5/1365, 247.5/1510, 247.5/1655, 247.5/1800, 282/1510, 282/1655, 282/1800, 316.5/1655, 316.5/1800.
- 316L -> printable: 75/300, 75/420, 75/540, 75/660, 75/780, 102/300 to 102/1260 (9 cells), 129/300 to 129/1500 (11), 156/540 to 156/1500 (9), 183/660 to 183/1500 (8), 210/900 to 210/1500 (6), 237/1020 to 237/1500 (5), 264/1260, 264/1380, 264/1500. -> risky: 156/300, 156/420, 183/420, 183/540, 210/540, 210/660, 210/780, 237/540, 237/660, 237/780, 237/900, 264/660, 264/780, 264/900, 264/1020, 264/1140, 291/780 to 291/1500 (7), 318/900 to 318/1500 (6), 345/900 to 345/1500 (6).
- AlSi10Mg -> printable: 140/615 to 140/2100 (10 cells), 183/1440, 183/1605, 183/1770, 183/1935, 183/2100, 226/2100.

**IN718 acceptance (design section 4): met.** 27 printable cells; 2 of them inside the literature box (120 to 300 W, 550 to 1000 mm/s): 138 W at 765 and 887.5 mm/s. All 27 IN718 printable cells carry the Tang overlap advisory (no cell of this grid has a Tang index at or below 1.0 at hatch 100 um and layer 40 um); the two in-box cells also carry the keyhole transition-band advisory. Printable here means "below the keyhole cut with resolved geometry", not a printability proof (the box is a display range, and fusion adequacy is not established). Pinned in `test_lpbf_process_window.TangAdvisoryDefaultGrid`.

## Outside the manifest and known reds

Tests: `test_lpbf_build_job_verdict_tier1.py` (new `TangAdvisory` class: 1.05 printable / risky with the advisory, 1.0 vs 1.001, 0.80 margin, null Tang/width/depth and unresolved geometry inconclusive, keyhole cuts 20 / 13.6 unchanged, pre-bump geometry of IN718 280/940/100 bit equal), `test_lpbf_p7a_rules_and_nulls.py`, `test_lpbf_suggested_patch.py`, `test_lpbf_build_job.py`, `test_lpbf_p7b_sourced_constants.py` (revision), `test_lpbf_process_window.py` (counts), `test_lpbf_calibration_frozen.py` (HTTP digests); TS `display-lane`, `lpbf-process-window`, `lpbf-verdict-tier1`, `build-job-kinetics-panel`. Regenerated in their own commits: parity goldens with GOLDEN_FINGERPRINT and HTTP_GOLDEN (`b43550b8`), error bands and `DEPTH_BIAS_BANDS_ID` (`8d10b7d3`, every row and cell bit equal), demo snapshots (`cf144c2e`). Known red on this branch: T-FRZ-3 (`test_diff_against_the_named_base_has_no_frozen_file`, by construction for any manifest change). Not regenerated: `tests/fixtures/how-calculated/meltpool-*-ti64.json` (historical captures that still carry the former label; their tests pass), the solidification payload fixtures naming v28, the leaderboard and NIST records (geometry only, bit equal; not re-run).

## Limits

The Tang, Pistorius and Beuth 2017 full text was not retrieved (not in the library index; the publisher link was not readable), so the original shape and depth datum are not independently checked; the formula is used as quoted by Harkin 2023 Eq. 5. Printable no longer excludes a Tang exceedance (for example IN718 90 W / 1400 mm/s at hatch 110 um is printable with Tang 9.3 and the advisory); the advisory and "fusion adequacy is not established" are the only guard. Evidence labels unchanged: `experimentalValidation=false`, screening only.
