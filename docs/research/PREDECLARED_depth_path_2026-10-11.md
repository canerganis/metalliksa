# Pre-registration (staged): measured regime absorptance plus a gated keyhole depth law for IN625 depth

Date: 2026-10-11. Lane `depth-path`, branch `research/depth-path`, base `63104c92` (fingerprint `0d52d7f7`).
Sources and locators: `docs/research/SOURCES_depth_path_2026-10-11.md` (cited as SOURCES). N3 ledger, split and metric:
`PREDECLARED_ke_width_n3_2026-10-10.md` sections 5 and 7 and `RESULTS_ke_width_n3_2026-10-10.md`.

**PREDECLARED. Stage 1 only. Nothing has been run on held-out data. No constant has been fitted.** The stage 1 runner
(`python/tools/run_lpbf_depth_path_stage1.py`, to be written after the gate) adds no solver code: it calls the served kernels
`lpbf_thermal_solver.calculate_meltpool_physics` and `fabbro_keyhole.fabbro_keyhole_depth_m` with different inputs and does
arithmetic on their outputs. `experimentalValidation` stays false. Original N3 stays NOT PASSED, original N4 NOT EVALUATED.
Frozen physics, the fingerprint pin and `main` are not touched. A PASS licenses only stage 2 (section 8), never a bump.

## 1. Candidates weighed and the choice

The brief offered (a) regime-dependent absorptance A(index) from Deisenroth 2020 fed to the served kernels, (b) a sourced
keyhole depth law above a sourced onset with a conduction kernel below, (c) both.

Choice: **(c)**, in one specific form. Reasons, all from process inputs and sources, none from held-out depth:

1. (a) alone cannot reach the Lane case A target. The served conduction isotherm scales with about the square root of
   absorbed power, so raising A from 0.38 to the Deisenroth value at the CBM A index (0.49) lifts the conduction depth by
   24 percent (93 against 75 um, section 10) and moves the predicted CBM A over AMMT A ratio from 1.82 to 1.94. The observed
   ratio is 3.55 and the rule asks for 2.5. Only a law that is linear or steeper in A P can get there.
2. Fabbro 2020 Eq. 2 is the one keyhole law in the repo whose absorptivity is by definition the total absorbed fraction of a
   keyhole, A(R) (SOURCES 3.4). Deisenroth's calorimetric absorptance is exactly that quantity, measured on bare IN625. Feeding
   it to Fabbro is the physically consistent pairing. The served Fabbro kernel already exists and already takes the flat
   absorptivity as "a calibrated effective value" and notes that a keyhole A(R) of 0.6 to 0.75 is what it lacks
   (`python/fabbro_keyhole.py` docstring).
3. The served kernels compound absorptivity three times on the Rosenthal path (index-driven multi-reflection boost, the
   uncited 1/(1 + 0.55 St) factor, the uncited depth increment keyed on the index). Feeding a measured total absorptance into
   that path double counts the multi-reflection boost. The design therefore strips the increment (conduction isotherm only,
   as the N3 baseline does) and lets the keyhole leg come from Fabbro, where the measured absorptance belongs.

Dropped, one line each:

- Rubenchik 2018 Eq. 11: a conduction-numerics interpolation, Weaver Appendix A finds 50 to 100 percent errors on IN625, and
  it cannot exceed conduction-mode depth, so it cannot move the ratio (SOURCES 3.1).
- Rubenchik closed form `d = 0.25 delta dH/hs`: its 0.25 was derived with a constant A per material, so a regime-dependent A_D
  would double count the absorptance rise, and the A that makes it work on IN625 (0.40) is back-solved from Lane CBM
  (contaminated, SOURCES 6 item 2).
- Ye 2019 with its own A_e curve: underpredicts IN625 keyhole depth by half (Weaver Table 5, literature), foil data, 57 um beam.
- Gan 2021 Ke vapour depth: already failed on this ledger (`RESULTS_ke_width_n3_2026-10-10.md`).
- Onset from the conduction field's peak temperature reaching T_v: the served Rosenthal and Eagar-Tsai fields have no
  evaporation sink and exceed 2880 C at A_D in 183 of the 201 ledger rows (probe, section 2), so the criterion
  opens for almost every row and discriminates nothing.
- Width-informed campaign factor: failed (`RESULTS_ke_width_n3`); latent-heat check: no effect (`RESULTS_lane_ab_latent_check`).

## 2. What the author saw before declaring (disclosure)

1. The published N3 results: per-group depth MAPE and signed bias of baseline and served (`RESULTS_ke_width_n3` sections 3
   and 4: served bias +5.2, +9.0, +23.4, -30.9, +24.3 percent for nist-20180905, nist-20180910, nist-20181026, lane-CBM,
   lane-AMMT). They fix the PASS target and inform the expectation in section 10. No constant below was chosen from them.
2. Lane Table 4 class mean depths (150.75, 91.28, 60.54 um) and Weaver Table 5 percent differences, both quoted in SOURCES 3.2.
   They are the lane-CBM held-out targets. They are not used in any formula, threshold or arm selection below. The headline
   law is chosen by the A(R) argument of section 1 item 2, the dropped laws by the reasons given, not by their CBM match.
3. Three process-input-only probes (scratch scripts, not committed; the runner's `--probe` mode must reproduce them from
   the (group, power, speed, D4sigma) tuples of the ledger alone): kernel depths at A 0.38 and at A_D for every distinct
   condition, the Fabbro depth with three conductivities, Eagar-Tsai peak temperatures, and the group means and Lane ratios in
   section 10. No `observed_width_um` or `observed_depth_um` value was read; the probe code reads only `group` and `condition`.

## 3. Frozen inputs and formulas

Reference index. `idx = lpbf_public_datasets.normalized_enthalpy("Inconel 625", P, v, D4sigma, 20.0)`, that is the app index at
the flat A 0.38 with the app's solid properties (rho 8440, k_s 9.8, cp_s 410, T_liq 1350 C). It is the similarity variable of
the A map and of the gate. It is computed once per condition at A 0.38 and is never recomputed at A_D (no fixed point).

Absorptance map A_D(idx). Piecewise-linear interpolation of Deisenroth 2020 Fig. 7 (SOURCES 2.1 table, sample means) on the
reference index of Deisenroth's own conditions (P at 500 mm/s, 65 um D4sigma, 20 C), flat outside the measured range:

| P (W) | 50 | 60 | 80 | 100 | 120 | 150 | 300 |
|---|---:|---:|---:|---:|---:|---:|---:|
| reference index | 10.6 | 12.7 | 16.9 | 21.1 | 25.4 | 31.7 | 63.4 |
| A_D | 0.3325 | 0.32 | 0.40 | 0.6217 | 0.695 | 0.75 | 0.9075 |

Below 10.6 the conduction plateau 0.3325 (mean of the two 50 W samples; the text says "about 0.34"), above 63.4 the value
0.9075. The runner recomputes the seven indices from (P, 500, 65) and a test pins them to this row within 0.1. The 100 W value
is the mean of the three plotted points (0.55, 0.65, 0.665). Read uncertainty about 0.02, plus up to 16 percent unmeasured
energy near 80 W (SOURCES 2.1), not propagated. Transfer across beams (65 um to 50 to 322 um) goes only through the index and
is unverified for IN625; the intensity mapping of section 5 is the declared alternative.

Conduction leg. `calculate_meltpool_physics("Inconel 625", P, v, D4sigma, preheat_temp_C=20.0, heat_source="rosenthal",
prop_overrides={"absorptivity_IR": A_D})`, `d_c = meltPoolGeometry.depth_um - meltPoolGeometry.keyholeVaporCavityDepth_um`
(the isotherm depth without the uncited increment, exactly the N3 baseline quantity at a different A). Valid statuses
`computed` and `width-floor-applied`; any other status invalidates the row. Below the gate A_D is at most 0.40 and the
kernel's own index stays below 15, so no multi-reflection boost and no increment enter. Above the gate the Rosenthal boost is
active inside d_c; the runner counts the rows where d_c exceeds the keyhole leg above the gate (`boost_leg_rows`) and the
probe gives 0 of 201 at nominal inputs.

Keyhole leg. `fabbro_keyhole_depth_m(P, v, D4sigma, k_s, alpha_s, T_boil, 20.0, A_D, 99.0)["depth_m"]` with the served IN625
constants the kernel itself passes (k_s 9.8 W/(m K), alpha_s = 9.8 / (8440 x 410), T_boil 2880 C), that is Fabbro Eq. 2
`e = A_D P / (k_s (T_v - T_0)(2.4 Pe + 3))`, `Pe = v D4sigma / (2 alpha_s)`. The argument 99.0 sets the kernel's uncited
15 to 30 onset ramp to 1 (full depth). `pecletInFitRange` is reported per row; Fabbro's fit band is Pe 2 to 10 and most
ledger rows are outside it (ledger Pe 3.5 to 46).

Gate. The keyhole leg is used only where `idx >= 15.0`, the served transition cut `ENTHALPY_TRANSITION` (vapour depression
onset from Cunningham 2019 Ti-6Al-4V x-ray data, not fitted on IN625). It lies inside Deisenroth's own step band (absorptance
leaves the conduction plateau between index 12.7 and 16.9) and below King's converted 19.3 to 25.2. The runner never calls
`regime_keyhole_cut`, never reads `meltPoolGeometry.regime` and never uses 13.6 (NIST-contaminated, SOURCES 6 item 8).

Headline depth (arm H):

    D_H = d_c(A_D)                      if idx < 15
    D_H = max(d_c(A_D), e_Fabbro(A_D))  if idx >= 15        (max link, as the served Eagar-Tsai path uses)

The max link is the served form (`extra = max(0, fabbro - d_iso)` in the solver) and keeps D_H continuous in A at the
conduction side; the additive link is not tested.

Inputs per group (from the pinned N3 loader `python/tools/run_lpbf_n3_nominal_shape_screen.py`, branch
`codex/depth-identifiability` at `62e49bd0`, sha256 `25aecfd49dcdf187aecbce8d22c9f0e242cc21383c706c53c0bdc80503f81ae3`):

| group | rows | P, v | D4sigma | notes |
|---|---:|---|---|---|
| nist-20180905, nist-20180910, nist-20181026 | 22, 96, 34 | workbook columns L, M | column K "Est. Spot Diameter (D4sigma = Dg)", 50 to 322 um | mds2-2923 EOS M270 and AMMT spot series |
| lane-CBM | 10 | Table 3: 150/400, 195/800, 195/1200 | 100 um nominal (headline), 112.5 and 125 um as sensitivity | beam never fitted |
| lane-AMMT | 13 | Table 3 measured 137.9/400, 179.2/800, 179.2/1200 | 170 um measured | |
| nist-20180828 | 26 | as NIST | as NIST | descriptive only, not in the rule |

## 4. Contamination guard

None of these enter any formula, gate or arm: IN625 cut 13.6; Rubenchik A 0.40; Weaver modified-Ye 0.5 / 0.8 / 1.32;
Fabbro A 0.8 and T_v 3500 K; Knapp A 0.277 to 0.307 and radii; Hong A 0.37 and 0.43; any Weaver slope. The served A 0.38
enters only as the reference-index convention and the served-reference arm. The IN625 property set is the app's served set
(unchanged); the conductivity sensitivity of section 5 uses the app's own k_th 19.9 and Weaver Table 2 k 28.78 (property
values, not tuned on N3 tracks, SOURCES 4.4).

## 5. Arms

| arm | definition | role |
|---|---|---|
| H | section 3 headline, nominal inputs | the only arm scored by the rule |
| served_reference | Rosenthal at A 0.38, `depth_um` with increment | the number to beat (pooled 25.6) |
| baseline | Rosenthal at A 0.38, d_c | N3 baseline (32.7) |
| ET_served | Eagar-Tsai kernel at A 0.38, served depth | descriptive: the served Melt Pool lab kernel |
| ET_AD | Eagar-Tsai kernel at A_D, served depth (its own 15 to 30 ramp, index at A_D) | descriptive |
| S_k19.9, S_k28.78 | H with the Fabbro k and alpha replaced by (19.9, 19.9/(8440 x 580)) and (28.78, 28.78/(8440 x 719.92)) | sensitivity: conductivity choice |
| S_gate16.9, S_gate21.1 | H with the gate at Deisenroth's 80 W and 100 W indices | sensitivity: onset |
| S_intensity | H with A_D mapped on peak intensity `2P/(pi w^2)` instead of the index (Deisenroth 3.0 to 18.1 MW/cm2) | sensitivity: beam transfer |
| S_cbm112.5, S_cbm125 | H with lane-CBM D4sigma 112.5 and 125 um (other groups unchanged) | sensitivity: nominal CBM beam |
| S_ETleg | H with the conduction leg from the Eagar-Tsai kernel (`depth_um - keyholeVaporCavityDepth_um` at A_D) | sensitivity: conduction kernel |

Sensitivities are reported in full (pooled, per group, Lane ratios) and are not scored by the rule. They cannot rescue a FAIL
and cannot be promoted to headline after the run. Two of them set the fragility flag of section 7.

## 6. Split and metric

Unchanged from `PREDECLARED_ke_width_n3` sections 5 and 7: 175 image-averaged observation rows in five held-out groups,
equal weight per row; nist-20180828 scored and reported, not pooled, not trained on (nothing is trained on anything).
Metrics: pooled held-out depth MAPE; per-group depth MAPE and signed bias; Lane CBM over AMMT predicted depth ratio per
case A, B, C (mean predicted depth over the case's Table 3 tracks) against observed 3.55, 2.54, 2.04. Descriptive: width MAPE
of the Rosenthal call at A_D, regime-leg counts per group (conduction leg, keyhole leg, boost-leg rows, Pe out of range), a
track-cluster bootstrap of the pooled MAPE gain of H over served_reference (2000 resamples, seed 20261011, clusters as in
the loader), and per-track wall time of the H pipeline (descriptive, not an N4 claim).

## 7. PASS rule (stage 1)

H PASSES when ALL hold:

1. pooled held-out depth MAPE of H is at most 20.6 percent (served_reference 25.6 minus a 5 point margin; the ke-width
   bootstrap intervals were about plus or minus 3 points wide, so 5 is above noise);
2. H depth MAPE is strictly below served_reference in at least 4 of the 5 held-out groups;
3. predicted Lane case A CBM over AMMT ratio of H is at least 2.5 (served 1.82);
4. completeness: every held-out row is predicted by H, served_reference and baseline with a valid status; otherwise the
   verdict is INCONCLUSIVE, never PASS.

One headline arm, one verdict: the lane verdict equals the H verdict. No sensitivity arm can produce a PASS. Fragility flag
(reported, does not change the verdict): a PASS is labelled "PASS, fragile" if S_k19.9 fails item 3 or S_cbm112.5 fails
item 3. The probe says both will fail item 3 (ratios 1.94 and 1.90, section 10), so any PASS of this screen will be
fragile, and section 8 makes the fragility the first thing stage 2 must remove. The rule and thresholds are fixed at this
commit.

## 8. Stage 2 and its entry condition

Enter stage 2 only on a stage 1 PASS (fragile or not). Stage 2 is still research, not a bump:

1. Replace the served k_s 9.8 in the keyhole leg by a sourced conduction-loss conductivity for a wall at T_v (Sabau 2018
   k(T) and Mills 2006, SOURCES 4.1, averaged over T_0 to T_v, about 25 W/(m K)) and re-declare. If the ratio criterion
   survives only with 9.8, the depth was carried by a compensating constant and the path stops.
2. Check the A_D beam transfer on source-clean IN625 tracks that are not in N3: Sabau 2018 GE tracks (80 um nominal,
   SOURCES 5.4) and the Gan 2021 AFRL tracks (100 um, SOURCES 5.3), each pre-registered with its own PASS rule.
3. Obtain or bound the CBM beam (`.orchestra/reports/cbm_beam_metadata_2026-10-11.md`); the 112.5 um sensitivity shows the
   CBM result flips to conduction above about 110 um.
4. Only after 1 to 3: a planned bump on a BUILD lane (goldens, parity, PROOF entry, gate). On a stage 1 FAIL there is no
   stage 2; the per-leg diagnostic (section 9) steers the next pre-registration.

## 9. Failure modes (what each outcome would mean)

1. Keyhole leg overshoots at small beams (NIST rows with D4sigma 50 to 90 um reach A_D 0.57 to 0.83 and Fabbro depths 1.4 to
   1.7 times served): the index mapping of a 65 um measurement to smaller beams is wrong, or k_s 9.8 is too low. Diagnosed by
   the per-row table split at D4sigma 90 um and by S_k19.9.
2. Conduction leg undershoots at large beams (A_D 0.33 lowers every conduction row by 7 to 9 percent): Deisenroth's plateau
   does not transfer, or the Rosenthal point source is already wrong at large beams (S_ETleg separates these).
3. CBM improves but the three NIST groups worsen: the design helps the two Lane campaigns at the cost of the 152 NIST rows
   and fails items 1 and 2 while passing item 3 (the expected outcome, section 10).
4. Lane C and B ratios stay near served even if A passes: with the 100 um beam CBM C (index 13.9) never opens the gate, so
   the gated law cannot describe a continuous depth rise; a hard gate at 15 is then the wrong form.
5. Kernel statuses other than the two valid ones on any held-out row: INCONCLUSIVE.
6. Unmeasured energy in Deisenroth (up to 16 percent near 80 W) biases A_D in the step region exactly where CBM A and B sit.

## 10. Pre-run expectation (process inputs only)

Computed from the ledger's (power, speed, D4sigma) tuples and the served kernels, no measured depth read. Row-weighted mean
predicted depth per group (um) and the Lane ratios:

| group | served_reference | H | H / served | rows on keyhole leg | S_k19.9 / served | S_gate21.1 / served | S_intensity / served | S_ETleg / served |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| nist-20180905 (22) | 68.7 | 82.2 | 1.20 | 12 | 0.94 | 1.14 | 1.25 | 1.14 |
| nist-20180910 (96) | 58.0 | 64.1 | 1.11 | 34 | 0.93 | 1.02 | 1.14 | 1.03 |
| nist-20181026 (34) | 73.4 | 96.1 | 1.31 | 10 | 1.01 | 1.31 | 1.39 | 1.25 |
| lane-CBM (10) | 66.0 | 77.6 | 1.18 | 6 | 0.94 | 0.94 | 1.05 | 1.17 |
| lane-AMMT (13) | 44.1 | 40.2 | 0.91 | 0 | 0.91 | 0.91 | 0.91 | 0.79 |

| Lane case | served ratio | H ratio (CBM, AMMT um) | S_k19.9 | S_cbm112.5 | S_cbm125 | S_intensity | observed |
|---|---:|---|---:|---:|---:|---:|---:|
| A | 1.82 | 2.73 (130.8, 47.9) | 1.94 | 1.90 | 1.11 | 1.87 | 3.55 |
| B | 1.57 | 1.88 (77.1, 41.0) | 1.54 | 1.14 | 1.08 | 1.96 | 2.54 |
| C | 1.10 | 1.14 (38.1, 33.5) | 1.14 | 1.10 | 1.10 | 1.35 | 2.04 |

Per condition, CBM A: idx 18.6, A_D 0.487, d_c 93.1, Fabbro 130.8 um; CBM B: 17.1, 0.409, 63.0, 77.1; CBM C: 13.9, 0.344,
conduction only 38.1; AMMT A, B, C: idx 7.7, 7.1, 5.8, A_D 0.3325, conduction 47.9, 41.0, 33.5 um. Boost-leg rows: 0 of 201.

Honest reading, using the disclosed served biases of section 2 (this is the only place they are used): H raises the three
NIST groups by 11 to 31 percent where served already overpredicts by 5 to 23 percent, so those groups should get worse,
most at nist-20181026 (small beams, A_D up to 0.83). H lowers AMMT by 9 percent (served +24 percent: better) and raises CBM
by 18 percent (served -31 percent: better, still under). Expected outcome: item 3 PASS at nominal inputs (2.73), items 1
and 2 FAIL (about 2 of 5 groups improve, pooled above 25.6), lane verdict **FAIL**, and the fragility flag would have been
set anyway (S_k19.9 1.94, S_cbm112.5 1.90). The author expects the screen to fail because the keyhole leg with the served
room-temperature conductivity is about 2.5 times deeper than the same law with a T_v-averaged conductivity, and that factor
is what reaches the CBM A depth; the same factor overshoots the small-beam NIST rows. A variant with k 19.9 would trade
item 3 for items 1 and 2 (means 0.93 to 1.01 of served) and was not made headline because the ratio is the discriminating
target that no earlier candidate reached. The run is still worth its cost (about 400 kernel calls, under a minute): the
per-row split at D4sigma 90 um tells whether the failure is the beam transfer of A_D or the law, which decides the next lane.

## 11. Run protocol

1. Gate approves this file. Then the runner `python/tools/run_lpbf_depth_path_stage1.py` and tests
   `python/test_lpbf_depth_path_stage1.py` are written (synthetic conditions only, no ledger values in tests), with the N3
   loader copied or cherry-picked from `codex/depth-identifiability` at `62e49bd0` and hash-pinned. Tests enforce:
   `declaration()` equals section 12; the seven Deisenroth indices within 0.1 of section 3; A_D(idx) at the seven points;
   gate uses 15.0 and the module never imports `regime_keyhole_cut`; the Fabbro call passes 99.0; the probe mode reads no
   observed key (the loader's `width_um` and `depth_um` fields are not accessed in probe mode, asserted by a stub).
2. `--run` refuses unless this file, the runner, the tests, the loader, SOURCES and the solver modules are tracked and clean;
   source hashes (runner, loader, declaration, SOURCES, NIST workbook, Lane Table 3 and 4, `lpbf_thermal_solver.py`,
   `fabbro_keyhole.py`, `lpbf_public_datasets.py`, `four_alloy_materials.py`, fingerprint expectation) recorded before and
   after. `check_frozen_inputs` asserts A 0.38, k_s 9.8, T_boil 2880 and ENTHALPY_TRANSITION 15.0 before the run.
3. One declared run with the Windows runtime Python (`.runtime/lpbf-win-py312`), exclusive-create JSON output, LF. No retry
   except after a crash with no result file, recorded. No tuning, no post hoc arm.
4. `RESULTS_depth_path_stage1_2026-10-11.md` reports every number of the JSON: rule items, all arms, per-group tables, Lane
   ratios, leg counts, the D4sigma 90 um split, the fragility flag, bootstrap, hashes, and the stage 2 decision.

## 12. Machine-readable declaration

The runner's `declaration()` must equal this block. A test enforces it.

```json declaration
{
  "schema": "lpbf-depth-path-stage1-v1",
  "stage": 1,
  "reference_index": "lpbf_public_datasets.normalized_enthalpy at A 0.38, solid props, 20 C; computed once, never at A_D",
  "absorptance_map": {
    "source": "Deisenroth 2020 Fig. 7, bare IN625, 65 um D4sigma, 500 mm/s (SOURCES 2.1)",
    "powers_W": [50, 60, 80, 100, 120, 150, 300],
    "reference_index": [10.6, 12.7, 16.9, 21.1, 25.4, 31.7, 63.4],
    "A_D": [0.3325, 0.32, 0.40, 0.6217, 0.695, 0.75, 0.9075],
    "interpolation": "piecewise linear in reference index, flat outside",
    "mapping_headline": "index",
    "mapping_sensitivity": "peak intensity 2P/(pi w^2)"
  },
  "conduction_leg": {
    "call": "calculate_meltpool_physics('Inconel 625', P, v, D4sigma, preheat_temp_C=20.0, heat_source='rosenthal', prop_overrides={'absorptivity_IR': A_D})",
    "depth": "meltPoolGeometry.depth_um minus keyholeVaporCavityDepth_um",
    "valid_statuses": ["computed", "width-floor-applied"],
    "sensitivity_leg": "eagar-tsai"
  },
  "keyhole_leg": {
    "call": "fabbro_keyhole_depth_m(P, v, D4sigma, k_s, alpha_s, T_boil, 20.0, A_D, 99.0)",
    "constants_served": {"k_s_W_mK": 9.8, "alpha_s": "9.8/(8440*410)", "T_boil_C": 2880.0, "m": 2.4, "n": 3.0},
    "ramp": "disabled by normalized_enthalpy 99.0",
    "k_sensitivity": [[19.9, "19.9/(8440*580)"], [28.78, "28.78/(8440*719.92)"]]
  },
  "gate": {"index_min": 15.0, "basis": "served ENTHALPY_TRANSITION (Cunningham 2019 Ti-6Al-4V)", "sensitivity": [16.9, 21.1], "never": ["13.6", "regime_keyhole_cut", "meltPoolGeometry.regime"]},
  "link": "max(d_c, e_fabbro) above the gate; d_c below",
  "cbm_beam_um": {"headline": 100.0, "sensitivity": [112.5, 125.0], "fitted": false},
  "groups": {"heldout": ["nist-20180905", "nist-20180910", "nist-20181026", "lane-CBM", "lane-AMMT"], "descriptive": "nist-20180828"},
  "arms": ["H", "served_reference", "baseline", "ET_served", "ET_AD", "S_k19.9", "S_k28.78", "S_gate16.9", "S_gate21.1", "S_intensity", "S_cbm112.5", "S_cbm125", "S_ETleg"],
  "scored_arm": "H",
  "pass_rule": {
    "pooled_mape_max_pct": 20.6,
    "served_reference_pooled_pct": 25.6,
    "groups_better_than_served_min_of_5": 4,
    "lane_A_ratio_min": 2.5,
    "completeness": "all held-out rows predicted by H, served_reference, baseline with valid status, else INCONCLUSIVE",
    "fragile_if": "S_k19.9 or S_cbm112.5 fails lane_A_ratio_min",
    "lane_verdict": "equals H verdict; sensitivities never produce a PASS"
  },
  "stage2_entry": "stage 1 PASS (fragile or not); stage 2 items in section 8; no bump from stage 1",
  "bootstrap": {"resamples": 2000, "seed": 20261011, "descriptive_only": true},
  "experimentalValidation": false,
  "original_N3": "NOT_PASSED",
  "original_N4": "NOT_EVALUATED"
}
```
