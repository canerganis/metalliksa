# Predeclaration: Keyhole-number depth term plus width-informed campaign correction

Date: 2026-10-10. Branch `claude/ke-width-n3`, from `codex/depth-identifiability`
(62e49bd0). Source record: `SOURCES_ke_scaling_2026-10-10.md` (commit 1e54705e).
This file, the runner `python/tools/run_lpbf_ke_width_n3.py` and the tests
`python/test_lpbf_ke_width_n3.py` are committed before any real run. The runner
refuses `--run` unless this file, the runner, the tests, the source record,
`python/tools/ke_regime_audit.py` and the N3 loader
`python/tools/run_lpbf_n3_nominal_shape_screen.py` are tracked and clean in git. The
loader file, its `LANE_SUMMARY` table (`table4_summary.csv`), the NIST workbook and the
Lane tables are also SHA-256 recorded before and after the run.

`experimentalValidation=false`. Original N3 stays NOT PASSED and original N4 stays NOT
EVALUATED. A PASS below is a screening verdict for this candidate only. It does not
meet the original N3 statistical gate, which needs two independent campaigns, and no
Lane or NIST physical-track independence is claimed. Frozen LPBF physics, the
implementation fingerprint pin and `codex/depth-identifiability` and `main` are not
touched. No nuisance constant is fitted anywhere in this lane.

## 1. What the author had seen before declaring

Disclosed so the reader can judge contamination.

1. The process-input-only regime audit (`ke_regime_audit.py`): Ke ranges per group.
2. Process-input-only kernel probes for this declaration: wall time per call and the
   kernel `extentStatus` at f = 0.4, 1.0 and 2.0 for every (group, power, speed, beam)
   condition. At f = 1.0 the served width carries the 0.55 beam-diameter floor for 28
   of 84 (group, condition) pairs, at f = 0.4 for 57 and at f = 2.0 for 4. No other
   non-computed status occurred. No measured width or depth was read for this probe,
   and no prediction was compared with any measurement.
3. The earlier published N3 screen results and the Lane Table 4 class means in
   `DEPTH_TRANSFER_DIAGNOSIS_2026-10-09.md` (observed CBM over AMMT depth ratios
   3.55, 2.54, 2.04). They fix the PASS target in the brief, not any model constant.
4. Weaver et al. 2022 percent differences for Rubenchik's law on Lane CBM A, B, C.
   They are not used here. Weaver's tuned "modified Ye" constants are not used.

No Ke, vapour term, campaign factor or depth was computed for any measured row before
this commit. The only model evaluations were the kernel probes in item 2.

## 2. Corrections to the brief, fixed here

1. Citation. The law is Gan et al., Nature Communications 12, 2379 (2021),
   doi:10.1038/s41467-021-22704-0, not a Science 2022 paper (SOURCES section 1).
2. Observable. Gan's e is the X-ray vapour depression depth. The N3 observable is the
   etched melt depth. The authors state the two do not scale linearly together.
3. The vapour to melt depth link is not sourced (SOURCES section 7). Two links are
   declared, labelled by their status, see section 4.
4. Reading of "below the keyhole threshold". Gan Eq. (2) gives e* = 0 for Ke at or
   below 1.4, so the vapour term switches on at Ke = 1.4, where the term is zero and
   the blend is continuous. Ke = 6.0 is only a regime label (reported, not a switch).
   The stricter reading, a switch at Ke = 6.0, would leave all Lane CBM conditions
   (Ke 2.6 to 5.9, SOURCES section 8) on the pure conduction kernel and make Part A
   inert for them, so it is not tested.

## 3. Frozen kernel and constants

Kernel call, every constant with a locator.

| item | value | locator |
| --- | --- | --- |
| kernel | `lpbf_thermal_solver.calculate_meltpool_physics("Inconel 625", P, v, D4sigma, preheat_temp_C=20.0, heat_source="rosenthal", prop_overrides={"absorptivity_IR": 0.38 * f})` | public API of the frozen module. Rosenthal is the served Build Job default. Flat-plate absorption (default `absorption_model`) |
| nominal flat absorptivity | 0.38 | `lpbf_public_datasets.screening_props("Inconel 625")["absorptivity_IR"]`, asserted equal before a run by `check_frozen_inputs` |
| conduction depth d_c | `meltPoolGeometry.depth_um` minus `meltPoolGeometry.keyholeVaporCavityDepth_um` | removes the uncited Rosenthal keyhole increment, leaves the isotherm depth d_iso (rounding at most 0.1 um) |
| served depth (reference only) | `meltPoolGeometry.depth_um` | the depth the app serves, including the uncited increment |
| kernel width | `meltPoolGeometry.width_um`, floor included | the app's served width |
| valid kernel statuses | `computed`, `width-floor-applied` | `_liquidus_extent`: the floor changes the reported width only, not the isotherm depth. Any other status invalidates the row (depth) or the campaign (inversion) |
| T0 | 20 C = 293.15 K | N3 ledger |
| Ke properties | liquid rho 7640, cp 709.25, k 30.078, liquidus 1623.15 K | SOURCES section 6, Li et al. 2022 arXiv:2208.02907 Table 3, secondary, unvalidated |
| Ke eta_m | 0.28 | Ye et al. 2019 Table 1, SOURCES section 6 |
| r0 | D4sigma / 2 | Gan Supplementary Eq. (37), SOURCES sections 3 and 4 |
| e* law | `e* = 0.4 (Ke - 1.4)`, zero below 1.4 | Gan 2021 Eq. (2) |
| Ke | `Ke = eta P / ((T_l - T_0) pi rho cp sqrt(alpha v r0^3))` | Gan 2021 Eq. (1) |
| eta for Ke | `eta_G = max(0.28, 0.7 (1 - exp(-0.6 X)))`, `X = 0.28 P / ((T_l - T_0) pi rho cp v r0^2)` | Gan 2021 Eq. (6), (7) as printed, floor as in Supplementary Data 1 (SOURCES section 5) |
| powers and speeds | NIST workbook settings; Lane Table 3 powers (AMMT 137.9 and 179.2 W) | N3 loaders from commit 3fc6a724, pinned hashes |

The liquid properties for Ke and the solid screening properties of the kernel differ by
design (Gan's convention versus the frozen kernel). This is declared, not tuned.
Eq. (6) as printed reproduces Gan's data only to 14 percent MAPE of e* (SOURCES
section 5), so eta carries an unexplained 5 to 20 percent scale. That uncertainty is
not propagated in this lane.

## 4. Part A: Ke vapour term and blend

For a track with absorbed-power factor f (f = 1 for variants without Part B):

    eta_Ke = min(1, f * eta_G)
    Ke = Ke(P, v, r0, eta_Ke)
    e = r0 * 0.4 * max(0, Ke - 1.4)                  (vapour depression depth)
    additive link:  D_A = d_c(f) + e                 (new hypothesis, UNSOURCED)
    max link:       D_A = max(d_c(f), e)             (Gan Supplementary Method 3: keyhole depth
                                                       approximately equals melt depth in
                                                       transition and keyhole mode; an assumption
                                                       of the derivation that the main text
                                                       contradicts)

Both links equal d_c(f) at Ke at or below 1.4 and are continuous in Ke. There is no
second switch at Ke = 6.0. The additive link is the form the brief proposed. The max
link is the only form with a primary-source statement behind it. Neither is fitted.
Any PASS on the additive link is therefore a pass of an unsourced hypothesis and must
be reported that way. The regime label (conduction below 1.4, transition to 6.0,
keyhole above 6.0) is reported per group.

## 5. Part B: width-informed campaign correction

Corrected quantity: effective absorbed power, as one multiplicative factor f per
campaign, entering both the kernel (`absorptivity_IR = 0.38 f`) and the Ke eta
(`eta_Ke = min(1, f eta_G)`). Why this quantity: the predicted width of a conduction
kernel is monotone in absorbed power and width transfers across campaigns at about
11 percent, so the width carries the campaign scale; power, absorptivity and beam
size are confounded and f absorbs their net effect. The alternative (effective beam
radius) is not tested.

Estimator, per campaign (group), widths only:

    solve  (1/n) sum_i ln( W_kernel(c_i, f) / W_i ) = 0   for f in [0.4, 2.0]

by 24 bisections in ln f. Each campaign track (image-averaged observation) counts
once, with the served kernel width including its floor, which is non-decreasing in f.
If the residual is non-negative at f = 0.4 the factor is clamped to 0.4; if non-positive
at 2.0 it is clamped to 2.0. Clamping and all-floored plateaus are recorded as flags,
not failures. Bracket: f = 2.0 means 0.76 absorptivity, still below 1. A non-isotherm
kernel status during inversion marks the campaign inversion failed, and its rows stay
in the denominator as failed. Measured depths are never an input of any function
that builds f or a prediction. Campaigns are the N3 groups: `nist-20180905`,
`nist-20180910`, `nist-20181026` (AMMT spot series), `lane-CBM`, `lane-AMMT`. Lane
cases A, B, C share one factor per machine. The group `nist-20180828` is scored for
completeness and is not part of the pooled held-out set or the PASS rule. Nothing is
trained on it.

## 6. Variants

| name | f | depth |
| --- | --- | --- |
| baseline | 1 | d_c(1) |
| A_additive, A_max | 1 | Part A, additive or max link |
| B | f_group | d_c(f_group) |
| AB_additive, AB_max | f_group | Part A with f_group |
| served_reference | 1 | served depth, uncorrected (guard and context only) |

Width is reported for every variant as the served kernel width at that variant's f.
For B and A+B the width MAPE is in-sample for the campaign (one factor fitted to
the campaign's own widths) and is labelled as such.

## 7. N3 test and PASS rule

Metric: held-out depth MAPE, equal weight per image-averaged observation row, pooled
over the 175 rows of the five held-out groups, plus per group. Lane CBM/AMMT depth
ratio per case A, B, C: mean predicted depth over Table 3 tracks of the CBM case
divided by that of the AMMT case, against observed 3.55, 2.54, 2.04.

A+B PASSES on a link when ALL hold:

1. pooled held-out depth MAPE of A+B is at least 10 percentage points below baseline;
2. A+B depth MAPE is strictly below baseline in at least 4 of the 5 held-out groups;
3. A+B predicted Lane case A CBM/AMMT ratio is at least 2.5;
4. guard: A+B pooled depth MAPE is below that of served_reference;
5. completeness: every held-out row of baseline, A+B and served_reference is predicted
   (otherwise the verdict is INCONCLUSIVE, never PASS).

Written reason for item 4, the one addition to the brief's example rule: the app serves
the depth with its uncited increment, so beating a conduction-only baseline would not
show an improvement over the shipped output if the shipped output is already better.
Item 5 follows the earlier N3 screen (failed rows stay in the denominator). The rule is
evaluated separately for the additive link and the max link and both verdicts are
reported. No other threshold is adjusted after this commit.

Lane-level verdict (declared before the run). Two links are tested, so the rule above
gives two chances to pass. To prevent that, the headline is the max link only: the lane
PASSES if and only if the AB_max link PASSES, and the lane verdict equals the AB_max
verdict (PASS, FAIL or INCONCLUSIVE). The additive link is a secondary, unsourced
hypothesis. If AB_additive PASSES while AB_max does not, the lane verdict is the AB_max
verdict and the result is reported as "unsourced hypothesis survives screen", which is
not a model pass. Every report and results document states that two links were tested.

Descriptive only, not part of the rule: per-group width and depth MAPE and bias, B-only
and A-only rows, regime counts, and a track-cluster bootstrap of the pooled depth MAPE
gain over baseline (2000 resamples, seed 20261010, clusters as in the N3 loader,
inferred and not independent campaigns).

## 8. N4 test

Per-track runtime of the full A+B pipeline (public-API kernel call, Ke, both links)
for every (group, condition) pair of the ledger, one untimed warm-up call, then one
timed call each, no memoization, single thread, this machine, wall clock
`time.perf_counter`. Gate: p95 at most 2.0 s (numpy linear percentile). The campaign
inversion is reported separately as prediction-phase seconds and per-group factors,
and is not part of the per-track latency. The arithmetic of Ke and the blend takes
microseconds, but the public-API kernel call measured about 15 to 30 ms in the probe,
so the "microseconds per track" aim is not met by this design and is not claimed. This
is the lane's N4 and does not evaluate the original CPU complete-track N4.

## 9. Run protocol

1. One declared run: `python python/tools/run_lpbf_ke_width_n3.py --run --output <new json>`
   with the Windows runtime Python of `Metalliksa-1/.runtime/lpbf-win-py312`.
   The output is exclusive-create and LF.
2. No retries and no tuning. A rerun is allowed only after a crash that produced no
   result file, and the crash is recorded in the results document.
3. Source hashes before and after the run are recorded. The runner stores the git
   HEAD, which must contain this file and the runner.
4. The focused tests must pass before the run and are re-run after it.
5. After the run, write `RESULTS_ke_width_n3_2026-10-10.md` with every number from the JSON,
   including failures, flags and the per-link verdicts.

## 10. Expectation (not a claim)

Before running, the author expects the lane to fail. Reasons: wrong observable, no
IN625 in the law, an unsourced link, Lane CBM Ke at most about 5.9, and a Rosenthal
conduction kernel whose D/W cannot exceed about 0.5. The max link cannot lift the CBM
depth much beyond the kernel depth. A PASS on the additive link would be surprising and
would still be unsourced. A FAIL rejects this combination for this ledger. It does not
reject Ke scaling for keyhole vapour depth in the materials Gan measured.

## 11. Machine-readable declaration

The runner's `declaration()` must equal this block. A test enforces it.

```json declaration
{
  "schema": "lpbf-ke-width-n3-v1",
  "kernel": {
    "call": "lpbf_thermal_solver.calculate_meltpool_physics",
    "material": "Inconel 625",
    "heat_source": "rosenthal",
    "preheat_C": 20.0,
    "absorptivity_IR_nominal": 0.38,
    "absorption_model": "flat-plate (default)",
    "conduction_depth": "meltPoolGeometry.depth_um minus keyholeVaporCavityDepth_um",
    "valid_statuses": [
      "computed",
      "width-floor-applied"
    ]
  },
  "partA": {
    "law": "Gan et al. 2021 Nat. Commun. 12, 2379, Eq. (1), (2), (6), (7)",
    "e_star": "0.4 * max(0, Ke - 1.4)",
    "e_star_slope": 0.4,
    "e_star_zero_at": 1.4,
    "ke_conduction_below": 1.4,
    "ke_keyhole_above": 6.0,
    "r0": "D4sigma / 2",
    "eta": "min(1, f * Gan Eq. (6) with eta_m 0.28, floored at 0.28)",
    "properties_liquid": {
      "rho": 7640.0,
      "cp": 709.25,
      "k": 30.078,
      "T_liquidus_K": 1623.15,
      "T0_K": 293.15
    },
    "links": {
      "additive": "conduction + e* r0 (unsourced hypothesis)",
      "max": "max(conduction, e* r0) (Gan Supplementary Method 3)"
    }
  },
  "partB": {
    "corrected_quantity": "effective absorbed power, factor f on absorptivity_IR and on Ke eta",
    "estimator": "mean_i ln(W_kernel_i(f) / W_i) = 0, widths of the held-out campaign only",
    "bracket": [
      0.4,
      2.0
    ],
    "bisections_in_ln_f": 24,
    "eta_ke_cap": 1.0,
    "width_used": "served kernel width including the 0.55 beam-diameter floor"
  },
  "groups": {
    "calibration_free_descriptive": "nist-20180828",
    "heldout": [
      "nist-20180905",
      "nist-20180910",
      "nist-20181026",
      "lane-CBM",
      "lane-AMMT"
    ]
  },
  "variants": [
    "baseline",
    "A_additive",
    "A_max",
    "B",
    "AB_additive",
    "AB_max",
    "served_reference"
  ],
  "pass_rule": {
    "pooled_gain_pp_min": 10.0,
    "groups_better_min_of_5": 4,
    "lane_A_ratio_min": 2.5,
    "guard": "A+B pooled depth MAPE below served_reference pooled depth MAPE",
    "completeness": "all held-out rows of baseline, A+B and served_reference predicted",
    "evaluated_for_links": [
      "additive",
      "max"
    ],
    "links_tested": 2,
    "lane_verdict": {
      "headline_link": "max",
      "rule": "lane PASSES only if the AB_max link PASSES; the lane verdict equals the AB_max verdict (PASS, FAIL or INCONCLUSIVE)",
      "additive_only_pass": "reported as 'unsourced hypothesis survives screen', not a model pass"
    }
  },
  "n4": {
    "p95_limit_s": 2.0,
    "percentile_method": "numpy linear"
  },
  "bootstrap": {
    "resamples": 2000,
    "seed": 20261010,
    "descriptive_only": true
  },
  "experimentalValidation": false,
  "original_N3": "NOT_PASSED",
  "original_N4": "NOT_EVALUATED"
}
```
