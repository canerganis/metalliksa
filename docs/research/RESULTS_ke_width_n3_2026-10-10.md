# Results: Keyhole-number depth term plus width-informed campaign correction (Ke + width N3/N4)

Date: 2026-10-10. Branch `claude/ke-width-n3`. Declaration: `PREDECLARED_ke_width_n3_2026-10-10.md` (commit 33e41b75, the git HEAD stored in the JSON). Machine-readable results: `RESULTS_ke_width_n3_2026-10-10.json` (every number below is taken from it). `experimentalValidation=false`. Original N3 stays NOT PASSED and original N4 stays NOT EVALUATED. Frozen LPBF physics, the implementation fingerprint pin, `codex/depth-identifiability` and `main` were not touched.

## 1. Verdict

**Lane verdict: FAIL** (headline link: max). The additive link, an unsourced hypothesis, also FAILS. Two links were tested; the headline is the max link only, as declared. Every rule item fails except completeness; Lane CBM is the single group that improves over baseline. The N4 runtime check of this lane passes (p95 0.029 s against a 2.0 s limit).

Run: one declared run, `python python/tools/run_lpbf_ke_width_n3.py --run --output docs/research/RESULTS_ke_width_n3_2026-10-10.json`, completed in 52.8 s (prediction phase 50.7 s, 2311 distinct cached kernel calls). No crash, no retry, no tuning. Focused tests: 33 passed before the run and were re-run after it and passed. All 12 recorded source hashes (runner, audit, loader, declaration, source record, NIST workbook, Lane Table 3 and Table 4, frozen thermal solver, public datasets, materials module, fingerprint expectation) were identical before and after the run.

## 2. PASS rule evaluation

| item | threshold | AB_additive | AB_max |
| --- | --- | --- | --- |
| 1. pooled held-out depth MAPE gain over baseline | at least +10.0 pp | -66.6 pp (FAIL) | -14.3 pp (FAIL) |
| 2. groups strictly better than baseline | at least 4 of 5 | 1 of 5: lane-CBM (FAIL) | 1 of 5: lane-CBM (FAIL) |
| 3. Lane case A CBM/AMMT predicted depth ratio | at least 2.5 | 1.74 (FAIL) | 1.44 (FAIL) |
| 4. guard: pooled MAPE below served_reference (25.6 %) | strictly below | 99.3 % (FAIL) | 47.0 % (FAIL) |
| 5. completeness | 175 of 175 rows for baseline, A+B, served_reference | complete | complete |
| verdict | | FAIL | FAIL |

Negative gain means A+B is worse than baseline. Baseline pooled held-out depth MAPE is 32.7 %. A+B is 99.3 % (additive) and 47.0 % (max). The "unsourced hypothesis survives screen" outcome does not occur, because the additive link fails too.

## 3. Depth MAPE (percent) per held-out group

Equal weight per image-averaged observation row. Group `nist-20180828` is scored for completeness in the JSON, is not part of the pooled set or the rule, and is not trained on.

| group (rows) | baseline | A_additive | A_max | B | AB_additive | AB_max | served_reference |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| nist-20180905 (22) | 30.8 | 37.5 | 23.6 | 33.6 | 80.4 | 31.4 | 18.3 |
| nist-20180910 (96) | 34.1 | 37.4 | 30.9 | 46.5 | 103.1 | 46.6 | 27.5 |
| nist-20181026 (34) | 31.2 | 54.4 | 26.4 | 46.6 | 103.1 | 55.3 | 23.9 |
| lane-CBM (10) | 39.3 | 14.1 | 36.3 | 30.2 | 34.4 | 26.0 | 30.9 |
| lane-AMMT (13) | 24.3 | 25.8 | 24.3 | 71.2 | 143.1 | 71.2 | 24.3 |
| pooled_heldout (175) | 32.7 | 38.5 | 28.9 | 45.8 | 99.3 | 47.0 | 25.6 |
| nist-20180828 (26, descriptive) | 37.4 | 30.4 | 29.9 | 48.6 | 94.5 | 37.5 | 27.2 |

Variants: A_* use f = 1. B and AB_* use the per-campaign factor f from widths only. served_reference is the depth the app serves today, with its uncited Rosenthal keyhole increment.

## 4. Depth bias (percent, signed, predicted minus observed relative to observed, mean over rows)

| group | baseline | A_additive | A_max | B | AB_additive | AB_max | served_reference |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| nist-20180905 | -7.3 | +37.5 | -0.1 | +11.1 | +80.4 | +27.3 | +5.2 |
| nist-20180910 | +2.3 | +37.4 | +5.6 | +33.9 | +103.1 | +44.5 | +9.0 |
| nist-20181026 | +9.1 | +54.4 | +25.9 | +27.7 | +103.1 | +55.3 | +23.4 |
| lane-CBM | -39.3 | +13.5 | -36.3 | -30.2 | +34.4 | -26.0 | -30.9 |
| lane-AMMT | +24.3 | +25.8 | +24.3 | +71.2 | +143.1 | +71.2 | +24.3 |
| pooled_heldout | +1.7 | +38.5 | +7.8 | +28.9 | +99.3 | +42.4 | +10.2 |

## 5. Width (percent MAPE) and campaign factors

Width is the served kernel width at the variant's f. For B and A+B the width MAPE is in-sample for the campaign (one factor fitted to the campaign's own widths). The baseline width MAPE is the transfer figure.

| group | baseline width MAPE | B width MAPE (in-sample) | baseline width bias | B width bias | factor f | floored widths at solution | residual at f=0.4 / 2.0 | status |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| nist-20180905 | 17.6 | 20.1 | -11.3 | +2.3 | 1.305 | 4 of 22 | -0.59 / 0.12 | solved |
| nist-20180910 | 18.9 | 21.2 | -17.0 | +2.4 | 1.444 | 18 of 96 | -0.55 / 0.10 | solved |
| nist-20181026 | 25.5 | 21.8 | -5.3 | +3.3 | 1.303 | 8 of 34 | -0.40 / 0.16 | solved |
| lane-CBM | 13.0 | 3.9 | -13.0 | +0.1 | 1.136 | 0 of 10 | -0.77 / 0.26 | solved |
| lane-AMMT | 20.7 | 3.3 | -20.7 | +0.1 | 1.692 | 0 of 13 | -0.29 / 0.10 | solved |
| nist-20180828 | 23.9 | 15.6 | -17.1 | +1.5 | 1.458 | 2 of 26 | -0.73 / 0.11 | solved |

Pooled held-out width MAPE: baseline 19.8 %, B 18.9 % (in-sample). The estimator zeroes the mean log width ratio, so in-sample MAPE can rise slightly (nist-20180905 and nist-20180910) when the width floor binds or the spread is large. No factor was clamped, no inversion failed, no plateau flag. The held-out factors are 1.14 to 1.69, i.e. effective absorptivity 0.43 to 0.64 against the nominal 0.38.

## 6. Lane CBM over AMMT depth ratios

Mean predicted depth over Lane Table 3 tracks of the CBM case divided by that of the AMMT case. Observed ratios from the Lane tables.

| case | observed | baseline | A_additive | A_max | B | AB_additive | AB_max | served_reference |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A | 3.55 | 1.42 | 3.01 | 1.71 | 1.16 | 1.74 | 1.44 | 1.82 |
| B | 2.54 | 1.28 | 2.51 | 1.28 | 1.09 | 1.47 | 1.09 | 1.57 |
| C | 2.04 | 1.10 | 1.78 | 1.10 | 0.92 | 1.19 | 0.92 | 1.10 |

The rule asks for a Lane A ratio of at least 2.5 from A+B. The A+B values are 1.74 (additive) and 1.44 (max). Only A_additive (no Part B) gets near the observed ratios (3.01, 2.51, 1.78), and that variant has a pooled depth MAPE of 38.5 %, worse than baseline.

## 7. Regime counts, bootstrap, N4

Ke regime of the baseline (f = 1) row by Gan thresholds 1.4 and 6.0, counted over rows:

| group | conduction | transition | keyhole |
| --- | ---: | ---: | ---: |
| nist-20180828 | 6 | 12 | 8 |
| nist-20180905 | 8 | 8 | 6 |
| nist-20180910 | 36 | 46 | 14 |
| nist-20181026 | 12 | 12 | 10 |
| lane-CBM | 0 | 10 | 0 |
| lane-AMMT | 9 | 4 | 0 |

Descriptive track-cluster bootstrap of the pooled depth MAPE gain over baseline (2000 resamples, seed 20261010, 99 inferred clusters, not independent campaigns). Positive is better than baseline:

| variant | point gain (pp) | 95 % interval (pp) |
| --- | ---: | --- |
| A_additive | -5.8 | -10.1 to -1.6 |
| A_max | +3.8 | +2.2 to +5.5 |
| B | -13.1 | -18.2 to -7.8 |
| AB_additive | -66.6 | -73.8 to -59.4 |
| AB_max | -14.3 | -19.4 to -8.8 |

**N4 (this lane's runtime check):** 84 (group, condition) pairs, one untimed warm-up, one timed call each, no memoization, single thread, wall clock. p50 25.9 ms, p95 29.5 ms, max 31.1 ms, limit 2.0 s: **pass**. The time is the public-API kernel call; the Ke arithmetic and the blend take microseconds. The aim of microseconds per track is therefore not met by this design (about 26 ms per track) and is not claimed. The campaign inversion is not part of the per-track figure; the whole prediction phase (all groups, all variants, kernel calls cached) took 50.7 s. This is not the original CPU complete-track N4 and does not evaluate it.

## 8. Reading of the result

These points follow from the tables. They are not new tests.

1. Part A with the max link helps modestly (pooled MAPE 32.7 to 28.9 %, bootstrap gain +3.8 pp, interval +2.2 to +5.5 pp). It only raises depth where the vapour depth exceeds the conduction depth. It leaves Lane AMMT unchanged and Lane cases B and C ratios unchanged at baseline. Lane CBM improves slightly but stays low (36.3 % MAPE, bias -36 %).
2. Part A with the additive link raises depth in every row with Ke above 1.4. It fixes Lane CBM (14.1 % MAPE) and moves the Lane ratios toward the observed ones, but overpredicts the three NIST held-out groups by 37 to 54 %. It is the unsourced hypothesis and it does not survive.
3. Part B alone makes depth worse (pooled 32.7 to 45.8 %). Widths are fitted (3.9 % and 3.3 % in-sample for the Lane groups), but the kernel's width-to-depth proportions do not match the data. The factor that fixes width raises predicted depth by 11 to 71 % relative to observed in four of five groups. The worst case is Lane AMMT (factor 1.69, depth MAPE 24.3 to 71.2 %). A single absorbed-power factor inferred from widths does not carry to depth for this Rosenthal kernel.
4. The served reference (the shipped depth with its uncited increment) beats every new variant on the pooled set (25.6 % against 28.9 % for the best new one, A_max). This lane did not beat what the app already serves.
5. Lane CBM is the only group where A+B improves on baseline (additive 34.4 %, max 26.0 %, against 39.3 %), and only a little. No A+B variant reproduces the observed Lane CBM over AMMT ratios.

## 9. Limits

1. This is a screening result for one candidate combination on this ledger. It does not reject Ke scaling for the keyhole vapour depth in the materials Gan measured (Ti-6Al-4V, Al6061, SS316). It rejects this combination with these links for the etched IN625 depth.
2. The vapour to melt depth link is not sourced (SOURCES section 7). The max link rests on a derivation assumption in Gan's Supplementary Method 3 that the main text contradicts. The additive link is a new hypothesis. Neither was fitted.
3. IN625 liquid properties for Ke come from a secondary model table (Li et al. 2022, arXiv:2208.02907 Table 3), eta_m = 0.28 from Ye et al. 2019. Gan's Eq. (6) as printed reproduces Gan's own data to 14 % MAPE of e*, an unexplained 5 to 20 % scale on eta that is not propagated. The property convention differs from the frozen kernel's solid constants by a factor 2.19 in Ke. These were declared, not tuned, and not varied after the run.
4. Only the effective absorbed power factor was tested for Part B. The declared alternative (effective beam radius) was not tested.
5. The held-out set holds no independent campaigns in the original N3 sense. NIST physical tracks are inferred clusters, Lane CBM and AMMT are single studies. Weaver et al. 2022 tuned other laws on the same Lane tracks (SOURCES section 7.3); no Weaver constants were used here.
6. The N4 figure covers the per-track A+B call with the factor known. It is not an N4 pass for the app.
7. A FAIL does not license post hoc variants on this ledger. Any follow-up is a new predeclared lane.

## 10. Provenance

Runner `python/tools/run_lpbf_ke_width_n3.py` sha256 45ceb6c92cac0773250a1c52583aa9870993ca0741e9458746dc5dcab3b509c1. N3 loader `python/tools/run_lpbf_n3_nominal_shape_screen.py` sha256 25aecfd49dcdf187aecbce8d22c9f0e242cc21383c706c53c0bdc80503f81ae3. Declaration sha256 d79d9ab4856972291cd611e496987fe45470a1c3682d2c0f325f7881e6098a8a. The full before and after hash tables are in the JSON.
