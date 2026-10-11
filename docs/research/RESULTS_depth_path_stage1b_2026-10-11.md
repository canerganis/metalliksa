# Depth path stage 1b results (2026-10-11)

Verdict: **FAIL** (stage 2 arm: none). One run, from a clean tree, git head cd324b6a, status completed, all source hashes unchanged: True. Elapsed 19.6 s, 177 cached kernel calls. Arm status: H_ET FAIL, H_k FAIL.

Fresh ledger only decides the verdict. N3 below is a secondary, already-seen readout with no pass authority.
`experimentalValidation` stays false. Original N3 stays NOT PASSED, original N4 NOT EVALUATED.

## Rule items, arm H_ET

| item | R0 | R40 |
|---|---|---|
| pooled MAPE % (served) | 130.8 (78.5) | 151.4 (91.0) |
| 1 pooled margin pp (need 5.0) | -52.4 no | -60.3 no |
| 2 Sabau / Gan margin pp (need 2.0 each) | -124.0 / -4.7 no | -124.0 / -17.9 no |
| 3 wins total / Gan / Sabau (need 11 / 5 / 4) | 2 / 2 / 0 no | 3 / 3 / 0 no |
| 4 sign-flip p (need at most 0.025) | 0.9979 no | 0.9996 no |
| arm status | FAIL | FAIL |

## Rule items, arm H_k

| item | R0 | R40 |
|---|---|---|
| pooled MAPE % (served) | 65.1 (78.5) | 58.0 (91.0) |
| 1 pooled margin pp (need 5.0) | 13.3 ok | 33.0 ok |
| 2 Sabau / Gan margin pp (need 2.0 each) | 52.2 / -12.6 no | 52.2 / 20.2 ok |
| 3 wins total / Gan / Sabau (need 11 / 5 / 4) | 6 / 0 / 6 no | 15 / 9 / 6 ok |
| 4 sign-flip p (need at most 0.025) | 0.2749 no | 0.0000 ok |
| arm status | FAIL | PASS |

## Per-source depth MAPE and signed bias (percent)

| arm | reading | pooled MAPE | pooled bias | Sabau MAPE | Sabau bias | Gan MAPE | Gan bias |
|---|---|---|---|---|---|---|---|
| H_ET | R0 | 130.8 | 117.8 | 297.6 | 297.6 | 19.7 | -2.1 |
| H_ET | R40 | 151.4 | 151.4 | 297.6 | 297.6 | 53.9 | 53.9 |
| H_k | R0 | 65.1 | 32.0 | 121.4 | 121.4 | 27.6 | -27.6 |
| H_k | R40 | 58.0 | 58.0 | 121.4 | 121.4 | 15.8 | 15.8 |
| served_reference | R0 | 78.5 | 60.5 | 173.7 | 173.7 | 15.0 | -15.0 |
| served_reference | R40 | 91.0 | 91.0 | 173.7 | 173.7 | 36.0 | 36.0 |
| baseline | R0 | 59.1 | 7.0 | 88.6 | 76.7 | 39.4 | -39.4 |
| baseline | R40 | 43.0 | 29.7 | 88.6 | 76.7 | 12.6 | -1.6 |
| H | R0 | 130.8 | 117.8 | 297.6 | 297.6 | 19.7 | -2.1 |
| H | R40 | 151.4 | 151.4 | 297.6 | 297.6 | 53.9 | 53.9 |
| ET_served | R0 | 64.9 | 3.4 | 86.8 | 84.1 | 50.3 | -50.3 |
| ET_served | R40 | 47.6 | 22.2 | 86.8 | 84.1 | 21.4 | -19.1 |

## Per-condition table (predicted depth um, observed R0 / R40, APE percent R0)

| condition | src | P W | v mm/s | D um | T0 C | obs R0 | obs R40 | idx | A_D | Pe | served | baseline | H | H_ET | leg | H_k | leg |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sabau2018-mp1 | sabau2018 | 100 | 300 | 80 | 20.00 | 46.0 | 46.0 | 20.0 | 0.562 | 4.2 | 97.0 | 72.8 | 152.4 | 152.4 (231.2) | keyhole | 91.9 (99.8) | conduction |
| sabau2018-mp2 | sabau2018 | 150 | 300 | 80 | 20.00 | 168.0 | 168.0 | 30.0 | 0.735 | 4.2 | 183.4 | 108.0 | 298.6 | 298.6 (77.8) | keyhole | 177.0 (5.3) | keyhole |
| sabau2018-p2s05 | sabau2018 | 75 | 50 | 80 | 20.00 | 58.0 | 58.0 | 36.7 | 0.775 | 0.7 | 327.4 | 166.0 | 441.6 | 441.6 (661.4) | keyhole | 203.8 (251.4) | keyhole |
| sabau2018-p2s1 | sabau2018 | 75 | 100 | 80 | 20.00 | 49.0 | 49.0 | 26.0 | 0.700 | 1.4 | 178.7 | 115.2 | 293.1 | 293.1 (498.1) | keyhole | 148.8 (203.7) | keyhole |
| sabau2018-p2s2 | sabau2018 | 75 | 200 | 80 | 20.00 | 39.0 | 39.0 | 18.4 | 0.477 | 2.8 | 88.0 | 69.1 | 130.4 | 130.4 (234.3) | keyhole | 87.0 (123.1) | conduction |
| sabau2018-p4s6 | sabau2018 | 150 | 1000 | 80 | 20.00 | 31.0 | 31.0 | 16.4 | 0.391 | 14.1 | 51.8 | 43.1 | 56.7 | 56.7 (82.8) | keyhole | 45.0 (45.2) | conduction |
| G300_1230 | gan2021 | 300 | 1230 | 100 | 79.85 | 115.7 | 75.7 | 21.2 | 0.623 | 21.7 | 100.0 | 70.8 | 123.6 | 123.6 (6.8) | keyhole | 83.9 (27.5) | conduction |
| gan2021-B12 | gan2021 | 290 | 953 | 100 | 79.85 | 140.1 | 100.1 | 23.3 | 0.658 | 16.8 | 122.8 | 82.2 | 160.4 | 160.4 (14.5) | keyhole | 105.9 (24.4) | keyhole |
| gan2021-B13 | gan2021 | 370 | 1230 | 100 | 79.85 | 141.9 | 101.9 | 26.1 | 0.701 | 21.7 | 136.7 | 85.3 | 171.6 | 171.6 (20.9) | keyhole | 114.6 (19.3) | keyhole |
| gan2021-B14 | gan2021 | 225 | 1230 | 100 | 79.85 | 85.3 | 45.3 | 15.9 | 0.381 | 21.7 | 60.1 | 49.7 | 56.6 | 56.6 (33.6) | keyhole | 49.9 (41.5) | conduction |
| gan2021-B15 | gan2021 | 290 | 1588 | 100 | 79.85 | 89.1 | 49.1 | 18.0 | 0.459 | 28.0 | 71.9 | 55.7 | 69.0 | 69.0 (22.5) | keyhole | 65.6 (26.4) | conduction |
| gan2021-B16 | gan2021 | 241 | 990 | 100 | 79.85 | 103.7 | 63.7 | 19.0 | 0.509 | 17.5 | 88.0 | 66.3 | 99.4 | 99.4 (4.1) | keyhole | 80.5 (22.4) | conduction |
| gan2021-B17 | gan2021 | 349 | 1430 | 100 | 79.85 | 118.6 | 78.6 | 22.8 | 0.652 | 25.2 | 108.4 | 73.4 | 130.3 | 130.3 (9.9) | keyhole | 87.5 (26.2) | keyhole |
| gan2021-B19 | gan2021 | 349 | 1058 | 100 | 79.85 | 147.5 | 107.5 | 26.6 | 0.705 | 18.7 | 145.3 | 89.7 | 187.5 | 187.5 (27.1) | keyhole | 124.4 (15.7) | keyhole |
| gan2021-B20 | gan2021 | 241 | 1529 | 100 | 79.85 | 76.4 | 36.4 | 15.3 | 0.369 | 27.0 | 52.6 | 44.4 | 47.8 | 47.8 (37.5) | keyhole | 42.1 (44.9) | conduction |

## Descriptive Sabau beam sensitivity (no authority, Sabau MAPE and bias percent, six conditions)

| beam | arm | MAPE | bias |
|---|---|---|---|
| S_beam56.6 | served_reference | 307.6 | 307.6 |
| S_beam56.6 | H_ET | 526.2 | 526.2 |
| S_beam56.6 | H_k | 225.6 | 225.6 |
| S_beam100 | served_reference | 89.8 | 82.5 |
| S_beam100 | H_ET | 146.8 | 146.8 |
| S_beam100 | H_k | 67.8 | 60.3 |

## Secondary N3 readout (already seen, selection data, no pass authority)

| group | rows | H_ET MAPE / bias | H_k MAPE / bias | served_reference MAPE / bias | baseline MAPE / bias |
|---|---|---|---|---|---|
| nist-20180828 | 26 | 14.0 / -0.8 | 25.3 / -10.9 | 27.2 / -1.6 | 37.4 / -11.8 |
| nist-20180905 | 22 | 19.3 / 3.1 | 17.7 / -3.3 | 18.3 / 5.2 | 30.8 / -7.3 |
| nist-20180910 | 96 | 15.8 / -4.3 | 24.5 / -0.6 | 27.5 / 9.0 | 34.1 / 2.3 |
| nist-20181026 | 34 | 26.9 / 21.4 | 17.7 / 15.8 | 23.9 / 23.4 | 31.2 / 9.1 |
| lane-CBM | 10 | 24.0 / -23.9 | 35.3 / -35.3 | 30.9 / -30.9 | 39.3 / -39.3 |
| lane-AMMT | 13 | 8.0 / -2.6 | 13.4 / 13.4 | 24.3 / 24.3 | 24.3 / 24.3 |
| pooled_heldout | 175 | 18.3 / 0.7 | 22.1 / 1.3 | 25.6 / 10.2 | 32.7 / 1.7 |

Lane CBM over AMMT predicted ratio (observed in the last column):

| case | H_ET | H_k | served | baseline | observed |
|---|---|---|---|---|---|
| A | 2.85 | 1.94 | 1.82 | 1.42 | 3.55 |
| B | 2.17 | 1.54 | 1.57 | 1.28 | 2.54 |
| C | 1.42 | 1.14 | 1.10 | 1.10 | 2.04 |

H_ET reproduces stage 1 S_ETleg: True (max relative difference 0.00e+00 over 201 rows).

## Run record

Git head cd324b6adc7a8132ccd438de0513039914e14ad5. Prediction phase 6.2 s. Source hashes before and after are in the JSON (`sha256_before`, `sha256_after`).


## Reading

Lane verdict FAIL: H_ET fails every item under both readings; H_k passes every item under R40 but fails R0, so by the declared rule (both readings) it fails. No stage 2 for either arm. No descriptive arm, beam sensitivity or N3 number enters the verdict.

H_ET is no better than the stage 1 headline H on the fresh ledger (identical numbers): the Eagar-Tsai conduction depth never exceeds the Fabbro leg here, so the keyhole leg decides all 15 conditions. It over-predicts Sabau by 298 % and, under R40, Gan by 54 %. Its N3 gain (pooled 18.3 %) did not transfer; it was a selection effect on N3 or specific to the N3 beams.

H_k beats the served reference on both sources under R40 (pooled 58.0 vs 91.0, Sabau 121 vs 174, Gan 15.8 vs 36.0, 15 of 15 wins, p below 1e-4). Under R0 it under-predicts Gan (bias -27.6 %), loses to served on Gan (27.6 vs 15.0), wins 0 of 9 Gan conditions and has p = 0.27. This is failure mode 2 (datum flip): H_k wins only if the released Gan depth overstates penetration by about the layer thickness. The datum is not established, so the pre-registered both-readings rule correctly withholds a PASS. The Rosenthal baseline (conduction only, A 0.38) is the best Gan arm under R40 (12.6 %) and the best pooled arm under both readings (59.1 R0, 43.0 R40), ahead of H_k.

Sabau is the dominant failure for every gated arm (failure mode 1): all six conditions open the gate at Pe 0.7 to 14, mostly below Fabbro's fit band, and the Fabbro leg is 2 to 8 times the observed depth at the 75 W rows (p2s05: 442 and 204 um predicted for H_ET and H_k, observed 58 um). The descriptive beam runs show no beam rescues this (H_k Sabau MAPE 226 % at 56.6 um, 68 % at 100 um versus served 308 % and 90 %). The conduction-only baseline (89 %) and ET_served (87 %) are the best Sabau arms. The next pre-registration should therefore target the onset criterion (when the Fabbro leg may open at low Pe), not the leg constants; with the Sabau beam source-selected and the Gan datum open, neither source is a clean arbiter alone.

N3 secondary (no authority): H_ET reproduces stage 1 S_ETleg exactly (max relative difference 0, 201 rows). H_k pooled 22.1 % on N3.

## Run notes

The Sabau averaged properties hold the Appendix D solid polynomials at their solidus value (1563 K) inside the 1563 to 1623 K blend zone. That reading reproduces the declared section 3.3 table to within 0.01 (k 25.354, cp 639.11); applying the plain polynomial through the zone gives cp 639.13, 0.02 away, a difference of order 0.003 % in depth. The pre-registration text says only "linearly blended"; the declared numeric table fixed the choice.

The fresh ledger depth columns were read for the first time in this run. One run, no rerun, no row dropped. `experimentalValidation` stays false.
