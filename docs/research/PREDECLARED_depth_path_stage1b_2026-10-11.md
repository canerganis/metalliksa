# Pre-registration: depth path stage 1b, two candidate arms confirmed on a fresh IN625 depth ledger

Date: 2026-10-11. Lane `depth-path`, branch `research/depth-path`, base `6e02867d` (fresh ledger commit on top of `55101efc`).
Inputs: `SOURCES_depth_path_2026-10-11.md` (SOURCES), `PREDECLARED_depth_path_2026-10-11.md` (stage 1 declaration, S1),
`RESULTS_depth_path_stage1_2026-10-11.{md,json}` (stage 1 results, R1), fresh ledger
`data/benchmark/in625-fresh-depth-2026-10-11/ledger.csv` (LF, SHA-256 `523c8701...e416` pinned in
`python/lpbf_in625_fresh_depth.py`) with `LICENSE-ATTRIBUTION.md`.

**Gate revision, same day, before any run.** The Opus prereg gate required two changes, both made here: a stricter PASS rule
(section 6: per-source margin and a count floor, because the earlier rule could pass on the Sabau block alone) and fuller
disclosure of how the Sabau beam input was chosen (section 4.1). The ledger is unchanged (hash pin intact). No arm,
constant or data reading changed.

**PREDECLARED. Nothing has been run. No model depth was computed on any fresh row (one hand evaluation disclosed in
section 2). No constant is fitted.** `experimentalValidation` stays false. Original N3 stays NOT PASSED, original N4 NOT
EVALUATED. Frozen physics, the fingerprint pin and `main` are not touched. A PASS licenses only stage 2 for the passing
arm (section 9), never a bump.

## 1. Why a stage 1b, and why these two arms

Stage 1 failed (R1: H pooled 25.14 vs served 25.57, 3 of 5 groups better, Lane A ratio 2.73 passed). Two unscored
sensitivity arms of that run looked better: S_ETleg (pooled 18.3, ratio 2.85, 3 of 5 groups) and S_k19.9 (pooled 22.0,
4 of 5 groups, ratio 1.94). The failure sits at D4sigma below 90 um (32 rows, H 47.0 vs served 9.5).

**Selection disclosure.** Both arms below were chosen by looking at those N3 readouts. N3 is therefore spent for these
arms: it cannot select or confirm them. It is reported in section 8 as a secondary, already-seen readout with no pass
authority. The confirming test is the fresh ledger only.

| arm | definition | stage 1 evidence that picked it | what changes versus S1 H |
|---|---|---|---|
| **H_ET** | S1 H with the conduction leg from the Eagar-Tsai kernel. Identical to S1 arm S_ETleg. | S_ETleg pooled 18.3, ratio 2.85 | conduction leg only; Fabbro leg, A_D, gate unchanged |
| **H_k** | S1 H with the Fabbro keyhole leg using a temperature-averaged property set from Sabau 2018 (section 3.3). Rosenthal conduction leg unchanged. | S_k19.9 22.0 and S_k28.78 23.0 both beat H; S1 section 8 item 1 already named this replacement | keyhole leg k, cp, rho only |

At most two arms. No other variant is scored. The Sabau averaged values were fixed by formula from the source before
any fresh-row prediction exists (section 3.3), not tuned on N3 (S_k19.9 and S_k28.78 used other values).

## 2. What the author saw before declaring (disclosure)

1. All of R1 (per-group MAPE, bias, sensitivity arms, D4sigma split). These choose the arms (section 1).
2. **The full fresh ledger CSV, including the observed depth and width columns**, read while writing this file to fix the
   datum handling of section 4. The arms, constants, metric and thresholds below come from section 1 and section 6
   reasoning; none is chosen from a fresh observed value. The gate should treat this as a real exposure.
3. Process-input arithmetic on the 15 distinct fresh conditions (repo runtime, `lpbf_public_datasets.normalized_enthalpy`
   at 20 C, the Deisenroth map and the Fabbro Peclet number at the served solid alpha). Table in section 10.
4. One hand evaluation of Fabbro Eq. 2 at Sabau p2s05 (75 W, 50 mm/s, 80 um), done while checking the Peclet range:
   about 443 um with the served k (the H_ET keyhole leg) and about 204 um with the section 3.3 set (H_k). No other model
   depth was evaluated on a fresh row; no kernel was called on a fresh row.
5. Sabau averaged properties computed from the Appendix D polynomials (section 3.3).

## 3. Frozen model (inputs, legs, gate)

### 3.1 Shared with S1 (unchanged)

Reference index `idx = normalized_enthalpy("Inconel 625", P, v, D4sigma, 20.0)` at A 0.38 and the app solid set, always
at 20 C (the convention of the Deisenroth map), computed once, never at A_D. A_D(idx): S1 section 3 table, piecewise
linear, flat outside. Gate `idx >= 15.0` (served ENTHALPY_TRANSITION; never 13.6, `regime_keyhole_cut` or
`meltPoolGeometry.regime`). Link `max(d_c, e_Fabbro)` above the gate, `d_c` below. Fabbro call
`fabbro_keyhole_depth_m(P, v, D4sigma, k, alpha, 2880.0, T0, A_D, 99.0)` (ramp disabled), T_boil 2880 C served. Valid
statuses `computed`, `width-floor-applied`.

### 3.2 H_ET

`d_c = depth_um - keyholeVaporCavityDepth_um` from `calculate_meltpool_physics("Inconel 625", P, v, D4sigma,
preheat_temp_C=T0, heat_source="eagar-tsai", prop_overrides={"absorptivity_IR": A_D})`. Keyhole leg with the served
k_s 9.8, alpha_s 9.8/(8440 x 410).

### 3.3 H_k

Conduction leg: S1 H (Rosenthal, same call with `heat_source="rosenthal"`). Keyhole leg: Fabbro with

    k_avg  = (1/(T_v - T0)) * integral_T0^T_v k(T) dT
    cp_avg = (1/(T_v - T0)) * integral_T0^T_v cp(T) dT
    alpha  = k_avg / (7700 * cp_avg)

T in K, T_v = 2880 C = 3153.15 K (served), T0 = the row's preheat. Sabau 2018 Appendix D (PDF p63, report p57, SOURCES
4.1 item 2): solid `k = 4.929465 + 1.574994e-2 T`, solid `cp = 361.8513 + 0.1251116 T + 1.740843e-4 T^2 - 7.527126e-8
T^3`, liquid k 30, liquid cp 700, density 7700 constant, both linearly blended over 1563 to 1623 K; latent heat
excluded from cp. The three keyhole-leg properties come from one source set; the conduction leg keeps the app set.
Declared values (trapezoid, 200001 points; the runner recomputes them and a test pins them within 0.01):

| T0 | k_avg W/(m K) | cp_avg J/(kg K) | alpha m2/s |
|---|---:|---:|---:|
| 20 C (293.15 K) | 25.354 | 639.11 | 5.152e-6 |
| 79.85 C (353.0 K) | 25.682 | 643.84 | 5.180e-6 |

Cross-check, not used: Mills 2006 k 27.3 at 1500 K versus Sabau 28.55 at 1500 K (SOURCES 4.1 item 1). Sabau 2018 is
also the source of six fresh rows; its property polynomials are JMatPro output, not fitted on those tracks (SOURCES 4.4).

### 3.4 Arms run (scored and descriptive)

| arm | role |
|---|---|
| H_ET, H_k | scored, each judged alone |
| served_reference | Rosenthal at A 0.38, `depth_um` with the served increment, same T0 and inputs as the arms (the S1 number to beat) |
| baseline | Rosenthal at A 0.38, d_c (completeness only) |
| H (S1 headline), ET_served | descriptive |
| S_beam56.6, S_beam100 | descriptive, Sabau block only: H_ET, H_k and served_reference at the other two beams (section 4.1) |

## 4. Inputs per source (fixed in advance)

| | Sabau 2018 (6 rows) | Gan 2021 (11 rows, 9 conditions) |
|---|---|---|
| surface | bare plate | 40 um powder layer on an AM substrate |
| model surface | bare plate | bare plate (no powder model exists in the kernels; `layer_thickness_um` stays at the default 40 and does not enter depth). The bare-plate A_D map is applied unchanged; powder absorptance transfer is a stated gap, shared by every arm |
| P, v | ledger | ledger |
| D4sigma | 80 um (paper's model 1/e2 diameter taken as D4sigma; experimental beam unmeasured; chosen by the source, see 4.1) | 100 um (stated D4sigma) |
| T0 | 20 C (preheat not stated; S1 convention) | 79.85 C (353 K stated); the reference index stays at 20 C |
| observed depth | `depth_um`, below the original surface (mp1, mp2 inferred; Table 2 rows unverified) | `depth_um` (corrected column) as released |
| replicates | none | B10, B11, B18 (`G300_1230`) averaged to one condition (mean of the three corrected depths) |

Gan datum. The released depth is very likely cross-section depth plus track height, so it may exceed penetration by an
unknown height. Two readings are scored and the rule must hold on both: **R0**, the Gan depth as released; **R40**, the
Gan depth minus 40 um, the stated layer thickness (PDF p2), the only vertical scale the source gives. R40 is a stress
reading, not a correction. Sabau rows are identical in R0 and R40. The original Gan depth column and the widths are not
scored.

### 4.1 Sabau beam provenance (disclosure)

The 80 um is not a number this repo set or measured, and it is not a neutral input.

1. Sabau 2018 Eq. 1 (PDF p15) is `exp(-2 r^2 / R^2)`, so 80 um is a 1/e2 diameter, which equals D4sigma for a Gaussian.
2. The source chose 80 um by comparing its own model against these same tracks. It reran the model at 70, 80 and 100 um
   against the measured widths and depths (Sabau PDF p31 to p32, report p25 to p26): 100 um pushed the calculated width
   up to about 50% above measured; 70 um pushed the calculated depth below measured; "the initial laser beam size of 80
   um was found to be appropriate". The beam was therefore selected by the source against the very widths and depths
   that are scored here. This repo did not fit it, but it is source-selected against these targets, so the Sabau block is
   not an out-of-sample test of the beam. A Sabau result says how the path behaves at the beam a source model needed,
   not how it would behave with an independently measured beam.
3. Rubenchik 2018 (PDF p8 and footnote 3) states that the Inconel data in its scaling plots came from GE Global Research,
   taken on an SLM machine, with beam radius `a` about 20 um in `exp(-r^2/a^2)` (its shape factor, PDF p5). That is D4sigma
   = 2 sqrt(2) a = about 57 um. Sabau's experiments are also a GE Global Research campaign. Whether they are the same
   campaign is not established, but if they are, the experimental beam was near 57 um and the 80 um model beam is larger
   than the real one. The failure of stage 1 sits at D4sigma below 90 um, so this input can decide the outcome.
4. Consequence for reading results: a Sabau-driven PASS or FAIL carries the beam uncertainty. The Gan block (stated 0.1 mm
   D4sigma) has no such issue and is the cleaner half of the test. The rule in section 6 therefore requires Gan to carry
   its own weight.

Descriptive beam sensitivity, declared now with no pass authority: the six Sabau conditions are also run for
`served_reference`, H_ET and H_k at D4sigma 56.6 um (2 sqrt(2) x 20 um) and 100 um, everything else unchanged
(reference index recomputed at the new beam, A_D from that index, Pe at that beam). It is reported as extra rows
(`S_beam56.6`, `S_beam100`), never enters section 5 pooled numbers, section 6 or the verdict, and no beam is chosen from it.
Cost is about 36 extra kernel calls.

## 5. Metric

Unit: a distinct condition (15: 6 Sabau, 9 Gan). Per condition `APE = |pred - obs| / obs`. Per source MAPE and signed
bias (mean of `(pred - obs)/obs`); pooled MAPE = mean APE over the 15 conditions. Computed for every arm under R0 and R40.

## 6. PASS rule (per scored arm, Bonferroni over two arms)

An arm X PASSES when ALL hold, under **both** R0 and R40. "served" is `served_reference`; margins are in percentage points
of per-source or pooled MAPE.

1. pooled MAPE(X) <= pooled MAPE(served) - 5.0 pp;
2. per-source strict margin: MAPE(X) <= MAPE(served) - 2.0 pp on Sabau **and** MAPE(X) <= MAPE(served) - 2.0 pp on Gan
   (a tie or a marginal gain on either source fails);
3. count floor: `APE_X < APE_served` strictly on at least 11 of the 15 conditions, with at least 5 of the 9 Gan conditions
   and at least 4 of the 6 Sabau conditions;
4. one-sided exact paired sign-flip test on the 15 per-condition differences `APE_served - APE_X`: statistic their mean,
   p = share of all 2^15 sign assignments with a statistic at least the observed one; p <= 0.025 (0.05 / 2 arms);
5. completeness: all 15 conditions predicted with a valid status by X, served and baseline; otherwise X is
   INCONCLUSIVE, never PASS.

Why items 2 and 3 exist. Item 4 alone does not stop a few large wins: the test statistic is the sum, so at n = 15 large
wins on one source can reach p <= 0.025 even when the other source is flat. Examples, exact enumeration of all 2^15 sign
flips (differences in pp): six Sabau wins of 30 plus nine Gan differences of +-4, +-3, +-2, +-1, 0 that sum to zero give
p = 0.0086; five Sabau wins of 30 plus one Sabau loss of 2 plus nine Gan differences of +-3, +-2, +-1, +-0.5, 0 give
p = 0.021. Both pass item 4, and with a Gan tie they would also pass the old item 1 and the old non-strict item 2, so a
PASS could have rested on six single-section tracks from one lab, four of them with an unverified depth datum and all with
a beam chosen by the source (section 4.1). Item 2 now demands a real gain on each source and item 3 demands that most
conditions improve, with Gan counted on its own. Item 4 stays as the check that gains are not carried by a handful of
rows inside a source.

Lane verdict: PASS if at least one arm passes, naming it; an arm that fails is not rescued by the other. If both pass,
both are confirmed and stage 2 takes H_k first (sourced keyhole constants, S1 section 8 item 1). No descriptive arm
(including the section 4.1 beam sensitivity) can produce a PASS. Thresholds are fixed at this commit.

## 7. Failure modes (what each outcome would mean)

1. Low-speed overshoot. Every fresh condition opens the gate (section 10), including Sabau 75 W at 50 to 200 mm/s with
   Pe 0.7 to 2.8, below Fabbro's 2 to 10 fit band. Fabbro Eq. 2 grows as Pe falls; the p2s05 hand value (section 2 item
   4) is several times any conduction depth at that condition. This alone can sink the Sabau item for both arms and is
   the main expected cause of failure: the index gate is the wrong onset at low speed and small beam, as the S1 D4sigma
   split already suggested.
2. Datum flip. An arm that passes R0 and fails R40 on Gan wins only through the crown height in the released depth.
3. High-Pe Gan rows (Pe 17 to 28 at the served alpha, outside the fit band). At high Pe Fabbro depth scales with
   1/(rho cp), so H_k's keyhole leg is about 0.70 of H_ET's there, independent of k.
4. Powder absorptance and the Sabau beam (source-selected 80 um versus a possible real beam near 57 um, section 4.1):
   shared by all arms, they shift served and candidates alike but not equally; a source-level flip on one source only
   points here. The section 4.1 beam sensitivity shows how large this is, without authority.
5. Small n: each Sabau row carries one sixth of that source's MAPE. Items 2 and 3 of section 6 require a margin and a
   count of wins on each source; item 4 guards against a few rows dominating.

## 8. Secondary N3 readout (no pass authority)

Both arms are run on the S1 N3 ledger with the S1 inputs (20 C, nominal CBM 100 um) and reported as pooled and
per-group MAPE, bias and Lane ratios, labelled "already seen, selection data". H_ET reproduces S1 S_ETleg (a mismatch
is a runner bug). H_k is new on N3 but N3 still has no authority. N3 never changes the verdict.

## 9. Stage 2 entry

Only on a stage 1b PASS, for the passing arm: re-declare with the CBM beam bound (`.orchestra/reports/cbm_beam_metadata_2026-10-11.md`)
and a Pe validity treatment from Fabbro's own band, then a planned bump on a BUILD lane. On FAIL there is no stage 2 for
these arms; the per-condition table (pred, obs, idx, A_D, Pe, leg) steers the next pre-registration, most likely to the
onset criterion.

## 10. Expectation from process inputs only

Reference index at 20 C, A_D and Fabbro Pe at the served solid alpha (arithmetic on the ledger inputs, no depth):

| condition | idx | A_D | Pe | | condition | idx | A_D | Pe |
|---|---:|---:|---:|---|---|---:|---:|---:|
| Sabau 100 W / 300 | 20.0 | 0.562 | 4.2 | | Gan 300 / 1230 (x3) | 21.2 | 0.623 | 21.7 |
| Sabau 150 / 300 | 30.0 | 0.735 | 4.2 | | Gan 290 / 953 | 23.3 | 0.658 | 16.8 |
| Sabau 75 / 50 | 36.7 | 0.775 | 0.7 | | Gan 370 / 1230 | 26.1 | 0.701 | 21.7 |
| Sabau 75 / 100 | 26.0 | 0.700 | 1.4 | | Gan 225 / 1230 | 15.9 | 0.381 | 21.7 |
| Sabau 75 / 200 | 18.4 | 0.477 | 2.8 | | Gan 290 / 1588 | 18.0 | 0.459 | 28.0 |
| Sabau 150 / 1000 | 16.4 | 0.391 | 14.1 | | Gan 241 / 990 | 19.0 | 0.509 | 17.5 |
| | | | | | Gan 349 / 1430 | 22.8 | 0.652 | 25.2 |
| | | | | | Gan 349 / 1058 | 26.6 | 0.705 | 18.7 |
| | | | | | Gan 241 / 1529 | 15.3 | 0.369 | 27.0 |

All 15 conditions open the gate, so both arms are on `max(d_c, e_Fabbro)` everywhere and both are mostly the Fabbro leg.
H_ET differs from S1 H only where the Eagar-Tsai d_c exceeds Fabbro; on this ledger that will be rare, so H_ET should
behave close to S1 H, which overshot small beams in S1.

Expectation: **both arms FAIL**. H_ET fails item 2 on Sabau (80 um beams, low speed, served Fabbro constants, failure mode
1). H_k is the better candidate (its keyhole leg is lower by about 0.4 to 0.7 across the Pe range) but its Sabau
slow-speed rows are still far above conduction depth, so it most likely fails item 2 or 3 of section 6 as well. The main reason
either could fail is the gate, not the law constants: an index cut at 15 opens Fabbro at Pe below its fit band. The run
is still worth its cost (about 100 kernel calls): it is the first source-clean test of the path, and a FAIL with the
per-condition table settles whether the next lane should replace the onset. Spurious-pass risk: the Gan datum favours
deeper predictions, which R40 is there to catch.

## 11. Run protocol

1. Gate approves this file. Then `python/tools/run_lpbf_depth_path_stage1b.py` and
   `python/test_lpbf_depth_path_stage1b.py` are written, importing the S1 runner functions unchanged; tests use
   synthetic conditions only and enforce: `declaration()` equals section 12; the section 3.3 averages within 0.01; the
   sign-flip p on a synthetic case; the item 2 margin and item 3 count floor on synthetic cases, including the two section 6
examples (each must fail item 2 or 3 although item 4 passes); T0 per source; replicate averaging; prediction phase reads no observed field.
2. `--run` refuses unless this file, the runner, tests, the fresh loader and ledger (hash pin), the S1 runner and the
   solver modules are tracked and clean; source hashes recorded before and after.
3. One declared run, runtime Python `.runtime/lpbf-win-py312`, exclusive-create JSON, LF. No retry except after a crash
   with no result file, recorded. No tuning, no post hoc arm, no row dropped.
4. `RESULTS_depth_path_stage1b_2026-10-11.{md,json}`: every rule item per arm and reading, per-source tables, the
   per-condition table, N3 secondary block, hashes, verdict.

Erratum to SOURCES 5.3 (not edited there): Gan Table 2 speeds span 953 to 1588 mm/s, and the P, v pairing of cases 1
and 2 is legible on the page image (300 W / 1230 mm/s).

## 12. Machine-readable declaration

```json declaration
{
  "schema": "lpbf-depth-path-stage1b-v1",
  "stage": "1b",
  "selection_disclosure": "arms chosen from stage 1 N3 sensitivity readouts S_ETleg and S_k19.9/S_k28.78; N3 has no pass authority",
  "fresh_ledger": {"path": "data/benchmark/in625-fresh-depth-2026-10-11/ledger.csv", "sha256": "523c87016b5eb817f95dac107d2cbe4b539a19079a4113b15fbd8d3615c5e416", "rows": 17, "conditions": 15},
  "scored_arms": ["H_ET", "H_k"],
  "descriptive_arms": ["served_reference", "baseline", "H", "ET_served"],
  "shared": {"reference_index_preheat_C": 20.0, "absorptance_map": "stage 1 section 3", "gate_index_min": 15.0, "link": "max(d_c, e_fabbro) above gate", "fabbro_enthalpy_arg": 99.0, "T_boil_C": 2880.0},
  "H_ET": {"conduction_leg": "eagar-tsai", "keyhole_k_alpha": [9.8, "9.8/(8440*410)"]},
  "H_k": {"conduction_leg": "rosenthal", "keyhole_props": "Sabau 2018 App. D averaged T0 to T_v, rho 7700, latent excluded", "values": {"20.0": {"k": 25.354, "cp": 639.11}, "79.85": {"k": 25.682, "cp": 643.84}}, "tolerance": 0.01},
  "inputs": {
    "sabau2018": {"surface_model": "bare_plate", "D4sigma_um": 80.0, "T0_C": 20.0, "beam_provenance": "80 um selected by the source against these same tracks (reran 70, 80, 100 um, Sabau PDF p31-32); Rubenchik 2018 PDF p8 fn 3 suggests GE IN625 data at D4sigma about 57 um"},
    "gan2021": {"surface_model": "bare_plate (powder not modelled)", "D4sigma_um": 100.0, "T0_C": 79.85, "depth": "corrected", "replicates": "mean per replicate_group"}
  },
  "readings": {"R0": "Gan depth as released", "R40": "Gan depth minus 40 um; Sabau unchanged"},
  "descriptive_beam_sensitivity": {"authority": "none", "block": "sabau2018 only", "arms": ["served_reference", "H_ET", "H_k"], "D4sigma_um": [56.6, 100.0], "labels": ["S_beam56.6", "S_beam100"], "excluded_from": ["pooled", "pass_rule", "verdict"]},
  "metric": {"unit": "condition", "pooled": "mean APE over 15 conditions", "per_source": ["MAPE", "signed_bias"]},
  "pass_rule": {
    "per_arm_all_of_under_R0_and_R40": [
      "pooled MAPE <= served_reference pooled - 5.0 pp",
      "source MAPE <= served_reference source MAPE - 2.0 pp, for sabau2018 and gan2021 each",
      "count floor: APE_arm < APE_served on >= 11 of 15 conditions, >= 5 of 9 gan2021, >= 4 of 6 sabau2018",
      "one-sided exact paired sign-flip test on APE_served - APE_arm over 15 conditions, p <= 0.025",
      "completeness: 15 conditions valid for arm, served_reference, baseline, else INCONCLUSIVE"
    ],
    "multiplicity": "Bonferroni, 0.05 over 2 arms",
    "lane_verdict": "PASS if at least one scored arm passes; descriptive arms and N3 never produce a PASS",
    "both_pass_stage2_order": ["H_k", "H_ET"]
  },
  "secondary_N3": {"authority": "none", "label": "already seen, selection data", "H_ET_must_equal": "stage 1 S_ETleg"},
  "expectation": "both arms FAIL; main cause: gate opens Fabbro at Pe below its fit band (Sabau low speed)",
  "experimentalValidation": false,
  "original_N3": "NOT_PASSED",
  "original_N4": "NOT_EVALUATED"
}
```
