# Results: IN625 per-alloy keyhole-mode threshold (2026-10-11)

Date: 2026-10-11. Lane `in625-regime-threshold`, branch `research/in625-regime-threshold`. Declaration:
`PREDECLARED_in625_regime_2026-10-11.md` (with amendments 1 and 2; git HEAD at the run `2320843d`, stored in the JSON).
Machine-readable results: `RESULTS_in625_regime_2026-10-11.json`. Every number below is taken from that file.
Screening evaluation, not validation: `experimentalValidation=false`, `screeningOnly=true`. The solver, the
fingerprint pin, every depth number and every other alloy were not touched in this step.

## 1. Verdict

**PASS.** P4, P1, P2, P3, P5 and P6 all hold.

Licensed claim (runner output `licensedClaimIfPass`, quoted verbatim, section 12 case 1 because arm F makes no
held-out error):

> The IN625 depth > half-width onset on the app index lies in (12.67, 13.94] (held-out-admissible interval; arm F
> makes no held-out error); T_F = 13.6 is the fit-split point estimate, not a held-out-validated value.

Read this together with section 10 of the declaration: the baseline's three held-out errors were known when the P2 and
P3 margins were set, so P1 to P3 passing was expected. The informative outputs are the interval (12.67, 13.94], which
is the error-free one of the three possible intervals listed in declaration section 10 item 3, and the P6 refits.

Run: one declared run,
`PYTHONDONTWRITEBYTECODE=1 python -B python/tools/lpbf_in625_regime_threshold.py run --declared-run`, from a clean
tree at `2320843d`, exit code 0. No crash, no retry, no tuning. The six hashes in the JSON (declaration, runner,
ledger, mds2 workbook, `lpbf_public_datasets.py`, `lpbf_thermal_solver.py`) were recomputed after the run and match.
Ledger sha256 `6957b6f3...a424a` equals the pin. Synthetic tests `python/test_lpbf_in625_regime_threshold.py`: 36
passed after the run.

## 2. Fit (fit split only, 56 EOS M270 units)

| quantity | value |
|---|---|
| units | 56 (22 keyhole, 34 not keyhole) |
| chosen midpoint | 13.643, between fit indices 13.432 (`mds2-eos-row40`) and 13.853 (`mds2-eos-row38`) |
| candidates tied at max BA | 1 |
| T_F (rounded to 0.1) | **13.6** |
| fit confusion at the midpoint | tp 21, fn 1, tn 33, fp 1 (2 errors) |
| fit balanced accuracy | 0.963 |

The two fit errors, from the per-unit table: `mds2-eos-row42` (index 12.63, depth over half width 1.18, keyhole,
called not keyhole) and `mds2-eos-row36` (index 14.61, ratio 0.92, not keyhole, called keyhole; flagged ambiguous,
and keyhole under the secondary truth). Four fit units are flagged ambiguous (`row41`, `row38`, `row36`, `row31`), all
between index 13.3 and 15.9.

The excluded unit `mds2-eos-row29` (195 W, 800 mm/s, 100 um) has app index 17.07 and depth over half width 1.35,
against 17.07 and 1.37 for held-out `lane2020-CBM-B`, consistent with the identity argument in declaration section 5.
It did not enter the fit.

## 3. Held-out arms (13 units, primary truth depth > width / 2)

| arm | cut | tp | fn | tn | fp | errors | keyhole recall | specificity | BA |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| F fitted (adoption candidate) | 13.6 | 5 | 0 | 8 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| B current 20 (baseline) | 20.0 | 2 | 3 | 8 | 0 | 3 | 0.40 | 1.00 | 0.70 |
| S Weaver 30 converted (not adoptable) | 21.73 | 2 | 3 | 8 | 0 | 3 | 0.40 | 1.00 | 0.70 |
| D current 15 (descriptive) | 15.0 | 4 | 1 | 8 | 0 | 1 | 0.80 | 1.00 | 0.90 |

## 4. PASS rule

| item | rule | value | result |
|---|---|---|---|
| P4 classes present | held-out at least 3 and 3, fit at least 5 and 5 | held-out 5 / 8, fit 22 / 34 | holds |
| P1 absolute | BA(F) >= 0.80 | 1.00 | holds |
| P2 gain | BA(F) minus BA(B) >= 0.15 | 1.00 minus 0.70 = 0.30 | holds |
| P3 errors | errors(F) <= errors(B) minus 2 | 0 <= 1 | holds |
| P5 secondary truth | BA(F) >= BA(B) under depth > D4sigma / 2 | 1.00 against 0.70 | holds |
| P6 robustness | all 56 leave-one-out refits give held-out BA >= 0.75 | minimum 0.9375 | holds |

P5 is not independent on this set (declaration section 10 item 4): the secondary confusions equal the primary ones.

P6 detail: of the 56 leave-one-fit-unit-out refits, 53 give 13.6, 2 give 12.5 and 1 gives 13.9. Held-out BA is 1.0
in 54 refits and 0.9375 in 2. A cut of 12.5 lies below `mds2-ammt-row10` (12.67), which would call that unit keyhole
(one false positive, BA 0.9375), so the two 0.9375 refits are consistent with the two 12.5 refits.

## 5. Held-out-admissible interval and arm F calls

Interval (L, U] = (12.667, 13.937]: lower bound `mds2-ammt-row10` (not keyhole, depth over half width 0.81), upper
bound `lane2020-CBM-C` (keyhole, ratio 1.20). Every cut in this interval gives the same held-out confusion as T_F.
The held-out split cannot tell T_F from any other cut in it.

| unit | app index | depth / half width | truth | F call |
|---|---:|---:|---|---|
| mds2-ammt-row14 | 4.17 | 0.34 | not keyhole | not keyhole |
| mds2-ammt-row13 | 5.57 | 0.41 | not keyhole | not keyhole |
| lane2020-AMMT-C | 5.78 | 0.57 | not keyhole | not keyhole |
| lane2020-AMMT-B | 7.08 | 0.59 | not keyhole | not keyhole |
| lane2020-AMMT-A | 7.70 | 0.57 | not keyhole | not keyhole |
| mds2-ammt-row12 | 7.91 | 0.55 | not keyhole | not keyhole |
| mds2-ammt-row11 | 9.88 | 0.68 | not keyhole | not keyhole |
| mds2-ammt-row10 | 12.67 | 0.81 | not keyhole | not keyhole |
| lane2020-CBM-C | 13.94 | 1.20 | keyhole | keyhole |
| lane2020-CBM-B | 17.07 | 1.37 | keyhole | keyhole |
| lane2020-CBM-A | 18.57 | 1.77 | keyhole | keyhole |
| mds2-ammt-row09 | 23.86 | 1.31 | keyhole | keyhole |
| mds2-ammt-row08 | 48.28 | 2.92 | keyhole | keyhole |

All 13 held-out units are unambiguous under declaration section 4 item 4.

## 6. Convention reconciliation (dH/hs)

| quantity | value |
|---|---|
| app index per Weaver index, same P, u, D4sigma (`weaverToRepoFactor`) | 0.72429 |
| Weaver 30 in app units (arm S) | 21.73 |
| King band 26 to 34 in app units | 18.83 to 24.63 |

Converted to the app convention, Weaver's 30 sits above the current cut 20 and makes the same three held-out errors.
The fitted onset in Weaver units is about 13.6 / 0.72429, near 18.8; the held-out interval in Weaver units runs from
17.49 (`mds2-ammt-row10`) to 19.24 (`lane2020-CBM-C`), per the per-unit `weaverIndex` column. So on these data the
depth > half-width onset sits below Weaver's quoted 30 in either convention; the convention difference alone (factor
0.724) does not explain the gap. The brief quoted app indices 19.45 and 17.88 for the two Lane CBM conditions; this
lane uses the pre-registered convention (declaration section 3: published D4sigma, Lane table power, flat A, T0 20 C)
and gets 18.57 and 17.07. That difference was not investigated in this step.

## 7. Sensitivities (not part of the verdict)

| sensitivity | T_F | F errors / BA | B errors / BA |
|---|---:|---|---|
| unambiguous held-out only (n 13) | 13.6 | 0 / 1.00 | 3 / 0.70 |
| preheat 27 C, F refitted | 13.7 | 0 / 1.00 | 3 / 0.70 |
| Lane AMMT nominal power 150 / 195 W | 13.6 | 0 / 1.00 | 3 / 0.70 |

Transition cut (declaration section 8 item 5), runner output `transitionCutConsequence`: "adopted keyhole cut is
below the transition cut 15: the IN625 transition band would be empty". How the product labels that is a BUILD-lane
decision.

## 8. Limits

1. The truth is etched cross-section morphology (depth > half width), not a vapour depression and not porosity.
2. The fit split uses estimated EOS spot sizes; the index scales as D^-1.5. The held-out AMMT spots are measured.
3. The held-out split has 13 units; the 7 mds2 AMMT units are one power and speed with a spot series, and Lane CBM is
   the same machine model as the fit split (cross-campaign, not cross-machine).
4. The cut is tied to the app's legacy-estimated IN625 property set; a property change requires a refit.
5. The held-out split was not blind to the author (declaration section 10).

## 9. What follows

Per declaration section 12, this PASS allows a planned physics bump on a separate BUILD lane: a per-alloy IN625 keyhole
cut of 13.6 in the app convention, a rewritten `REGIME_MATERIAL_NOTE_IN625` quoting the source, the truth criterion,
the held-out score, the interval (12.67, 13.94] and zero held-out errors, a fingerprint bump with goldens, parity, a
PROOF entry and an Opus gate. The transition cut 15 does not move (it also drives the multi-reflection absorptivity
step), other alloys keep 15 / 20, and no depth number changes. This lane does not edit the solver.
