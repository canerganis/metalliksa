# Depth path stage 1 results (2026-10-11)

Verdict: **FAIL** (arm H, stage 2 entry: no). One run, from a clean tree, git head 071a75ce, status completed, all source hashes unchanged. Elapsed 26.8 s (prediction phase 25.4 s, 728 cached kernel calls). Raw numbers: `RESULTS_depth_path_stage1_2026-10-11.json`. Declaration: `PREDECLARED_depth_path_2026-10-11.md`.

## Declared readouts

| readout | value | rule | ok |
|---|---|---|---|
| pooled held-out depth MAPE, H | 25.14 % | at most 20.6 % | no |
| groups strictly better than served | 3 of 5 (nist-20180910, lane-CBM, lane-AMMT) | at least 4 of 5 | no |
| Lane CBM/AMMT case A ratio, H | 2.73 (observed 3.55) | at least 2.5 | yes |
| fragility flag | not applicable (FAIL) | | |

Pooled references: served 25.57 %, Rosenthal baseline 32.71 %. H beats served pooled by only 0.43 pp, bootstrap 95 % CI [-3.96, +4.60] pp (descriptive, 99 inferred clusters). No incomplete rows.

## Per held-out group, depth MAPE

| group | rows | H depth MAPE % | served % | baseline % | S_k19.9 % | H bias % | keyhole-leg rows |
|---|---|---|---|---|---|---|---|
| nist-20180905 | 22 | 22.3 | 18.3 | 30.8 | 16.6 | 14.5 | 12 |
| nist-20180910 | 96 | 23.4 | 27.5 | 34.1 | 24.0 | 10.3 | 34 |
| nist-20181026 | 34 | 36.8 | 23.9 | 31.2 | 19.5 | 35.0 | 10 |
| lane-CBM | 10 | 23.2 | 30.9 | 39.3 | 35.3 | -23.1 | 6 |
| lane-AMMT | 13 | 13.4 | 24.3 | 24.3 | 13.4 | 13.4 | 0 |
| pooled_heldout | 175 | 25.1 | 25.6 | 32.7 | 22.0 | 14.0 | - |

nist-20181026 is the clear loss (36.8 vs 23.9 served, bias +35 %). Lane AMMT has no keyhole-leg rows, so its 13.4 % is the conduction leg at A_D alone.

## Legs and splits

Keyhole-leg rows: 12 (0905), 34 (0910), 10 (1026), 6 (CBM), 0 (AMMT). Boost-leg rows: 0 everywhere. Peclet outside the fit range on most rows (all of 0905 and 0910).

D4sigma split at 90 um: rows below 90 um (32 rows) H 47.0 % vs served 9.5 % (H over-predicts, bias +47 %); rows at or above 90 um (143 rows) H 20.3 % vs served 29.2 %.

## Sensitivity arms (pooled held-out depth MAPE, not scored)

ET_served 23.3, ET_AD 22.9, S_k19.9 22.0, S_k28.78 23.0, S_gate16.9 26.4, S_gate21.1 28.3, S_intensity 27.2, S_cbm112.5 26.2, S_cbm125 26.7, S_ETleg 18.3. Lane A ratio: S_k19.9 1.94, S_cbm112.5 1.90, S_gate16.9 2.73, S_ETleg 2.85. Only gate-index and ET-leg variants keep the ratio above 2.5, S_ETleg meets only the pooled item (18.3) and fails the 4 of 5 group item (3 of 5: it loses nist-20180905 19.3 vs 18.3 and nist-20181026 26.9 vs 23.9); it was not a declared scored arm.

## Reading

The keyhole-leg gate reproduces the CBM/AMMT contrast (ratio 2.73) but does not improve pooled depth beyond served: it over-predicts shallow, small-diameter rows and nist-20181026. The pooled gain is within bootstrap noise. Pre-registered pass rule not met; no rerun, no tuning on these results.

## Limits

H timing p50 16 ms per track (84 tracks), descriptive only, not an N4 claim. Clusters are inferred, not independent campaigns. Sensitivity arms were pre-declared in section 5 of the declaration; they are unscored readouts of the same single run and carry no pass authority.
