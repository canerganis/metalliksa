# Pre-registration P2: keyhole onset criterion with explicit beam size and Peclet dependence

Date 2026-10-11. Lane type RESEARCH, branch `research/phys-keyhole`, base local main `393cdbd1` (fingerprint `0d52d7f7`). Author: physics designer (Fable). Gate: a fresh Opus run. Runner: Sonnet, one declared run. Verifier: Opus.
Inputs: `.orchestra/reports/physics_forms_sweep_2026-10-11.md` (SWEEP, section 4), `.orchestra/reports/blind_validation_inventory_2026-10-11.md` (INV), `RESULTS_depth_path_stage1b_2026-10-11.md` (R1b), `SPEC_p1_sourced_served_physics_2026-10-11.md` (P1), `python/fabbro_keyhole.py` (FK).

**PREDECLARED. Nothing has been run. No held-out target value has been read by the author (process inputs and metadata only, section 2). No constant is fitted on any held-out row.** `experimentalValidation` stays false. Original N3 stays NOT PASSED, original N4 NOT EVALUATED. A PASS licenses only a planned bump on a BUILD lane (section 10); it never changes a label.

## 0. Open questions for the gate

1. **Al6061 vaporisation temperature.** Gan 2021 SI Supplementary Table 1 lists a "vaporization point" column, but the pdftotext extraction interleaves columns (values 3560, 873, 1658 appear on one line). This declaration uses elemental Al, `Tv = 2743 K` (2470 C). If the page image shows a different Al6061 value, that value replaces it **before** the run and is recorded in the amendment line; it is a property input, not a fit. Same for the SS316 row: the app `316L Stainless Steel` set is used (section 3.3), not Gan's SS316 table, so that the served gate baseline is the served computation.
2. **One criterion, two conductivity conventions, or two criteria?** This file scores one criterion (Fabbro generalized piston threshold, `R >= 1`) under two declared conductivity conventions (arms K_s and K_avg). A peak temperature boiling criterion (King 2014 Eq 2.3 to 2.5, Trapp 2017 Eq 3, Fabbro 2020 P*) was considered and dropped: evaluated with the served Eagar-Tsai field at the solid conductivity it predicts a vapour depression at every SS316 condition in the range (peak 19,000 to 61,000 C against Tv 2814 C, section 8), so it cannot discriminate without a constant that would have to be chosen from data. The gate may insist on it as a descriptive baseline only.
3. **Hann 2011 status.** INV open question 1: EXPOSED-LOW allowed with disclosure (BOARD 2026-10-11 lead decision). This file uses Hann only as a secondary, descriptive readout (section 5.3). Confirm.
4. **Bitharas 2022.** Download blocked (BOARD: Cloudflare); folder `.orchestra/external-data/bitharas2022/` holds `SOURCE.md` only. If `Figure_data.xlsx` arrives before the run, it is added under the header-only rule of section 2 as a second primary X-ray set (Ti64, 84 and 99 um, Pe about 3 to 26) with its own readout block; its PASS items are declared in section 6.4 now so that nothing is chosen after seeing it. If it does not arrive, section 6.4 is void.

## 1. Question and why these candidates

The served keyhole leg opens at `dH/hs >= 15` regardless of beam size and Peclet number (FK 61 to 67, ramp to 30). R1b: every Sabau condition (Pe 0.7 to 14, 80 um) opened the leg and the leg over-predicted 2 to 8 times at the 75 W rows; R1: the path over-predicted every row below D4sigma 90 um by 47 %. SWEEP 4.2 ranks the sourced onset criteria; the only one with explicit beam diameter **and** Peclet dependence and constants that do not come from any repo data is Fabbro's threshold power (SWEEP rank 3): Fabbro 2020 Eq 6, 11, 13, 14 (`fabbro2020.pdf`, doi 10.3390/app10041487, printed p.3 and p.7 to 8, verified on page image by the SWEEP and by text extraction here). Gan's keyhole number (rank 1) is a fitted correlation and in-sample on the primary held-out rows, so it is a baseline. King/Hann/Weaver enthalpy cuts (rank 2) carry only the `sigma^-1.5` beam dependence and no Peclet term; the served gate is their representative.

**Candidate (one criterion, two arms).** The keyhole leg opens when the Fabbro aspect ratio at the flat absorptivity reaches 1:

    R(P, v, d) = A_flat P / ( K (Tv - T0) d (m Pe + n) ),   Pe = v (d/2) / alpha_s,   open  <=>  R >= 1
    equivalently  P >= Pt = d (a + b v d) / A_flat,  a = n K (Tv - T0),  b = m K (Tv - T0) / (2 alpha_s)

This is Fabbro 2020 Eq 2 with R = 1 (Eq 6, the "incident power threshold Pt necessary for obtaining an aspect ratio R = 1") and the generalized piston form Eq 11 (`A_F(1) Pt / d = a1 + b1 Vw d`). Constants:
- `m = 2.4`, `n = 3.0` (cylindrical keyhole, Fabbro 2020 p.3, fitted by Fabbro to a finite element conduction solution for `2 <= Pe <= 10`, origin Fabbro 2018 J. Laser Appl. 30, 032410, not in library) for arm K_s, identical to the served leg; **or** `m1 = 2.1`, `n1 = 2.2` (half cone front, Fabbro 2020 Sec 3.3 p.7 to 8: "a1 = n1 K(Tv - T0) and b1 = m1 K(Tv - T0)/(2 kappa) ... one then finds that m1 = 2.1 and n1 = 2.2") for arm K_avg. Both pairs are Fabbro's model constants, none is fitted to experiment.
- `Pe = v (d/2) / alpha_s`, `alpha_s` the app solid diffusivity (lead's convention, FK 55, INV 0.3). Fabbro's own Pe uses `kappa` "solid" (SWEEP note 6). Liquid alpha appears only as a descriptive sensitivity (section 5.4).
- `A_flat`: the flat absorptivity of the declared property set (section 3.3). Fabbro's `A_F(1) = 0.32` is a Ti64 Fresnel value at `pi/4` and is not transferred.
- `K`: arm K_s uses the app room temperature solid `k_s` (the served leg); arm K_avg uses the temperature averaged conductivity `k_avg = (1/(Tv - T0)) integral_{T0}^{Tv} k(T) dT` from the declared k(T) table (section 3.3), the convention Fabbro's own `a1` implies (SPEC P1 open question 3).
- `Tv`, `T0`: boiling point of the declared set, 20 C plate (no preheat stated by any held-out source).

Why `R >= 1` is the right observable link: Fabbro defines the keyhole threshold at R = e/d = 1, Gan defines keyhole mode at `e* = e/r0 >= 2` (`gan2021.pdf` p.2, verified: "keyhole mode (e* > 2 or Ke > 6.0)"), and `e/d = 1 <=> e/r0 = 2`. King 2014 Sec 5.2 defines keyhole mode in etched sections as `d > w/2`. Those are three statements of the same event in two observables, which stay separate below.

## 2. What the author saw (disclosure) and the blindness rules of the run

Seen: INV in full (input ranges, counts, Pe and dH/hs statistics of every set; no row targets except the incidental items INV 0.1 lists, none of which is a primary row here); the three held-out CSV headers (`hann-ss304-2011/tables3_4_welds.csv`, `gan-keyhole-2021/printed_cases.csv`, `ku-leuven-in718-2021/measurements.csv`, first line only); the first two lines of `.orchestra/external-data/ku-in718-figshare15035697/Data_Inconel718.csv` (`;Power;100;W;;...` and an empty line: the file is laid out in power blocks, no column header row, no unit row); `SOURCE.md` of the KU and Bitharas folders; `2923_README.txt` lines 1 to 12 and the lines matching machine, spot, power, speed; sheet names and nothing else of `Master_TrackList_Measurements.xlsx` (the header read failed on a console encoding error before printing); Gan 2021 SI Table 1 text extraction (property inputs). **Not seen:** any `e`, depth, width, `delta_star`, `side_reported`, `regime_reported` value of any held-out row; the Gan Data 1 or Data 2 spreadsheets; any KU or mds2-2923 measurement.
Expectation arithmetic (section 8) uses only the INV input range endpoints.

Run rules: (1) the runner's prediction phase loads only whitelisted input columns (`material, P, V, r0|d, T0`), asserts that no column name containing `e_`, `depth`, `width`, `delta`, `side`, `regime`, `stability` is in memory, and writes predictions to a file **before** any target column is read; (2) target columns are read in a separate scoring process that imports the prediction file; (3) a header-only rule for every file not yet in the repo (Bitharas): the runner prints column names, the lead approves the whitelist, nothing else is printed; (4) one run, crashes recorded, no rerun to look better; (5) source hashes recorded before and after.

## 3. Data (held-out, unspent per INV), observables, property sets

### 3.1 Primary: Gan 2021 Supplementary Data 1, Al6061 and SS316 rows (X-ray)

`C:/Users/can02/Projects/metalliksaa/papers/gan2021_data1.xlsx` (Gan et al. 2021 Nat. Commun. 12, 2379, doi 10.1038/s41467-021-22704-0, CC BY 4.0). Rows: Al6061 9 (88 um spot label, 416 to 520 W, 350 to 900 mm/s), SS316 7 (110 um, 208 to 520 W, 300 to 600 mm/s) per INV 2.2. Status EXPOSED-LOW (Gan's own law reproduced on all 87 rows in `SOURCES_ke_scaling` section 5, aggregates only; no repo model ever scored on them). Observable: **VAPOR** keyhole depth `e` (X-ray, per frame contour, Data 1 column as released) with `r0` as released in Data 1. Class: `keyhole mode` if `e / r0 >= 2`, else `below` (transition or conduction). Beam definition is unstated in the source (INV metadata); `d = 2 r0` as released, declared now. The Ti64 rows of Data 1 are SPENT (Cunningham, 20 cut) and are excluded from scoring; they are reported descriptively only (section 5.4).
Why unmixed: this set never meets an etched depth here.

### 3.2 Secondary, descriptive only (no pass authority)

- **mds2-2923 IN718 2021 AMMT spot series** (`data/benchmark/nist-mds2-2923-in718/official/Master_TrackList_Measurements.xlsx`, NIST, doi 10.18434/mds2-2923): etched **MELT** depth and width, 285 W, 960 mm/s, D4sigma 48.3 to 80 um measured (AMMT), 54 section rows in 5 AMMT conditions (INV 2.1 and 4). Observable: `d > w/2` per section (King 2014 Sec 5.2), condition class by majority of sections. **Exposure disclosure and exclusion:** INV 0.1 reports that a header preview printed the first three Data rows of the set `IN718_20210323_M290` (EOS M290, 285 W, 960 mm/s, D4sigma 80 um) with their width and depth, and the first Summary row (the M290 condition's averages). The whole M290 condition (its 18 Data rows and its Summary row) is therefore excluded from every count; the 5 AMMT conditions were not previewed. One P and v only, all `dH/hs` 29 to 63: it can show whether the criterion keeps the leg open across 48 to 80 um at a keyhole-side condition; it cannot show an onset.
- **Hann 2011 AISI 304 welds** (`data/benchmark/hann-ss304-2011/tables3_4_welds.csv`, 14 welds (a) to (n), 300 to 1800 W, 16.7 to 50 mm/s, focus 320 to 960 um, EXPOSED-LOW: only Hann's own relation and the `Hv/hs` transition were checked). Observable: **MELT** `side_reported` as printed (conduction or keyhole side), a depth-derived label; `delta_star_printed` is not read. Not LPBF, not an app alloy, Pe 1.3 to 3.9 on the 316L proxy: the only unspent rows below Pe 2 on a steel. Property set: app `316L Stainless Steel` as the 304 proxy, declared.
- **KU Leuven IN718** (`.orchestra/external-data/ku-in718-figshare15035697/Data_Inconel718.csv`, Figshare 15035697.v1, CC0): **excluded**. The file has no header row and no unit row (first two lines seen, section 2), the attribution note of the repo loader states that width and depth units and the half width operator are unresolved, the beam (37.5 um) is unverified, and all 48 conditions sit at `dH/hs > 30` (no conduction side). Resolving the units would require reading dimension values; not done.
- **Gan Data 2** (28 rows, CLEAN): excluded. Power is released as `eta (P - P0)`, an absorbed power from the simulation, not an incident power; a criterion on incident power cannot be evaluated without the simulation's eta.
- **Bitharas 2022**: conditional, section 0 item 4 and 6.4.

### 3.3 Property sets (fixed now)

| set | k_s W/mK | k(T) for k_avg | cp_s J/kgK | rho kg/m3 | T_liq C | Tv C | A_flat | alpha_s m2/s | source |
|---|---|---|---|---|---|---|---|---|---|
| SS316 rows and Hann (304 proxy) | 16.3 | app set has no k(T): k_avg from Gan SI Table 1 SS316, `k = 0.0146 T + 10.3` (T < 1723 K), 26.9 above, averaged 293 to 3087 K: **25.9** | 500 | 7990 | 1400 | 2814 | 0.42 | 4.08e-6 | app `316L Stainless Steel` (TS `THERMOPHYSICAL_DB`); k(T) `gan2021_SI.pdf` Supplementary Table 1 (text extraction, column order checked against the Ti64 column) |
| Al6061 rows | 179.2 (`0.091 x 293 + 152.5`) | `k = 0.091 T + 152.5` (T < 915 K), 90 above, averaged 293 to 2743 K: **119.8** | 867 (`0.486 x 293 + 725`) | 2705 | 642 (915 K) | 2470 (2743 K, open question 1) | 0.10 (Gan SI eta_m for Al, SWEEP 1B) | 7.64e-5 | Gan SI Table 1 (not an app material; no AlSi10Mg substitution) |
| IN718 AMMT series | 11.4 | none available: arm K_avg not run on this set | 435 | 8190 | 1336 | 2850 | 0.38 | 3.20e-6 | app `Inconel 718` |

Averages are trapezoid integrals of the printed piecewise expressions; the runner recomputes them and a test pins them within 0.1 W/mK. The INV used Gan's liquid Al alpha (3.2e-5) for its Pe counts; this declaration uses the 293 K solid value (7.64e-5) per the lead's solid convention, so Al6061 Pe here is 0.2 to 0.5.

## 4. Models and arms

| arm | role | definition |
|---|---|---|
| **K_s** | scored | `R >= 1` with `m 2.4, n 3.0`, `K = k_s` (the served leg's own threshold) |
| **K_avg** | scored | `R >= 1` with `m1 2.1, n1 2.2`, `K = k_avg` (Fabbro's generalized piston constants and conductivity convention) |
| served | baseline | keyhole mode if app index `dH/hs >= regime_keyhole_cut` (20; 13.6 is IN625 only, not used here), leg open if `>= 15`; index per `lpbf_public_datasets.normalized_enthalpy` convention with the section 3.3 set |
| Gan Ke | baseline, in-sample on the primary set | `Ke = eta P / ((Tl - T0) rho cp sqrt(pi alpha V r0^3)) >= 6` with Gan's released per row `eta` column (read in the scoring phase only, it is a simulation output) and Gan's SI property values; never refitted |
| Cunningham | descriptive | `2 P / (pi D^2) >= 0.4 MW/cm2` (`cunningham2019.pdf` p.2, text verified: "threshold of ~0.4 MW/cm2"), stationary Ti64 drill onset, no speed term |

Inputs per row: `P`, `v`, `d = 2 r0`, `T0 = 20 C`, the section 3.3 set. Nothing else.

## 5. Metrics

### 5.1 Primary (Gan Al6061 + SS316, n = 16, VAPOR)

Per row: observed class `keyhole` if `e/r0 >= 2`; predicted class per arm. Counts: correct `c`, errors by type (false open, false closed), per material and pooled. Balanced accuracy `BA = 0.5 (TPR + TNR)` when both classes occur. Exact one-sided binomial `p` for `c` of 16 at chance 0.5: `c >= 13` gives `p = 0.0106`, `c >= 14` gives `0.0021`.

### 5.2 Secondary (descriptive, MELT)

mds2-2923 IN718 AMMT (5 conditions): per condition observed `d > w/2` majority class vs predicted; reported as a 5 row table with the beam diameter. Hann (14 welds): `side_reported` vs predicted, with Pe per weld; reported as a 14 row table.

### 5.3 Pe leverage readout (descriptive)

For each primary and secondary row: Pe (solid convention), beam, served gate state, each arm's R. Count of rows where the arms and the served gate disagree, split at Pe 2 and at d 80 um.

### 5.4 Sensitivities (descriptive, no authority)

(a) liquid alpha in Pe (Gan SI liquid values); (b) `A_flat` replaced by Fabbro's `A_F(1) = 0.32` for all rows; (c) Ti64 Data 1 rows (SPENT) under both arms, labelled "already seen, selection data"; (d) Cunningham power density.

## 6. PASS rule

### 6.1 Per scored arm, on the primary set only, all of

1. `c >= 13` of 16 correct (exact binomial `p <= 0.0106 <= 0.025`, Bonferroni 0.05 over 2 arms);
2. both classes present in the observed labels and `BA >= 0.80`; if only one observed class is present the arm is **INCONCLUSIVE** (cannot PASS, cannot FAIL on this item);
3. per material: at most 1 error on the 7 SS316 rows **and** at most 2 errors on the 9 Al6061 rows (a one material pass is not a pass);
4. not worse than served: `errors(arm) <= errors(served baseline)` on the 16 rows;
5. completeness: every row evaluated with finite R for the arm, served and Gan Ke; otherwise INCONCLUSIVE.

### 6.2 Multiplicity and lane verdict

Two scored arms, one primary observable, Bonferroni at 0.025 each (item 1 is already stricter). Lane PASS if at least one arm passes, naming it; if both pass, the bump takes K_avg (the Fabbro consistent convention). Secondary sets, sensitivities and the Gan Ke baseline never produce a PASS; a secondary table that contradicts a primary PASS (for example K_avg closes the leg on every IN718 AMMT condition that is observed keyhole) is reported in the verdict line as a **contradiction flag** and blocks the bump until P3 or a new primary set resolves it (section 10).

### 6.3 Failure modes (what each outcome means)

1. Al6061 closed everywhere (section 8 expects `R <= 0.58` for both arms across the Al range): if the Al rows are observed keyhole mode, both arms miss all of them, item 3 fails, lane FAIL. Reading: the threshold at flat `A = 0.10` cannot open on Al; the coupled absorptance (Gan eta 0.3 to 0.5 at keyhole) is the lever, which points P3 at the absorptance, not the gate.
2. SS316 split: K_avg opens at 520 W and closes at 208 W (section 8); K_s opens both. Which is right decides between the conventions; a K_s pass with K_avg failing says the served `k_s` is the better effective value at these Pe, and the P1 open question 3 is closed in favour of keeping `k_s`.
3. Beam definition: Gan's spot label (88, 110) vs the Methods list (84, 93, 114, 144 um; INV metadata). `R` scales as `d^-1` at low Pe and `d^-2` at high Pe, so a 10 % beam error moves R by 10 to 20 %; rows with `0.8 < R < 1.25` are listed as beam sensitive in the results.
4. Datum and operator: X-ray `e` per frame vs mean of frames; Data 1 is used as released; no correction.
5. Small n: 16 rows, 7 and 9; items 1 and 3 are exact counts; no bootstrap.

### 6.4 Conditional Bitharas block (void if the file is absent at run time)

If `Figure_data.xlsx` is in the repo external data folder with a lead approved input whitelist before the run: Ti64 app set (k_s 6.7, cp 526, rho 4430, T_liq 1660, Tv 3287, A 0.35; k_avg not available, so arm K_s only, plus K_avg with the Gan SI Ti64 k(T) `0.0136 T + 1.3097` below 1933 K and 33.4 above, averaged 293 to 3560 K), bare plate rows only (powder rows descriptive), observable X-ray keyhole depth class `e / (d/2) >= 2` with d the released 1/e2 diameter (84 or 99 um). Items 1 to 5 of 6.1 apply with the counts scaled: `c >= ceil(0.8 n)` and the exact binomial `p <= 0.025`, at most `floor(0.15 n)` errors per beam diameter. A Bitharas PASS or FAIL is scored separately; lane PASS then requires the Gan block to pass and the Bitharas block not to fail.

## 7. One run protocol

1. Gate approves this file (amendments, if any, listed at the top with date, before any run).
2. Sonnet writes `python/tools/run_lpbf_keyhole_onset_p2.py` and `python/test_lpbf_keyhole_onset_p2.py`. Tests are self contained and synthetic: `declaration()` equals section 11; the section 3.3 averages within 0.1; `R` against hand values (`A 0.4, P 200 W, v 0.8 m/s, d 80 um, K 10, Tv - T0 2800, alpha 3e-6` gives `Pe 10.67`, `R = 80/(10 x 2800 x 80e-6 x 28.6) = 1.248` for m 2.4 n 3); the exact binomial table (`c = 13 -> 0.0106`, `c = 14 -> 0.0021`); item 3 on a synthetic 16 row label set where a one material pass must fail; the prediction phase assertion that no target column name is loaded; the M290 exclusion by set id; the Ti64 exclusion from scoring.
3. `--run` refuses unless this file, the runner, the tests, `fabbro_keyhole.py`, `lpbf_thermal_solver.py`, `lpbf_public_datasets.py` and the pinned held-out files (SHA-256 of `gan2021_data1.xlsx`, the mds2-2923 workbook, `tables3_4_welds.csv`) are tracked or pinned and clean; hashes recorded before and after.
4. One declared run, runtime `.runtime/lpbf-win-py312`, exclusive create JSON, LF. Prediction file written first, scoring process second (section 2 rules).
5. `RESULTS_keyhole_onset_2026-10-XX.{md,json}`: every rule item per arm, per row table (material, P, v, d, Pe, dH/hs, R_Ks, R_Kavg, served state, Gan Ke, observed class, correctness), secondary tables, sensitivities, contradiction flags, hashes, verdict. Opus verifies by recomputing R for every row from the inputs and the section 3.3 set.

## 8. Expectation from process inputs only (INV range endpoints, no row read)

Script: scratchpad `p2_expect.py` (Eagar-Tsai peak only for the dropped criterion; R by hand form).

| rows | P W | v mm/s | d um | dH/hs (app form) | Pe | R K_s | R K_avg |
|---|---|---|---|---|---|---|---|
| SS316 | 208 | 300 | 110 | 19.8 | 4.0 | 1.37 open | 0.86 closed |
| SS316 | 520 | 300 | 110 | 49.5 | 4.0 | 3.43 open | 2.16 open |
| SS316 | 208 | 600 | 110 | 14.0 | 8.1 | 0.78 closed | 0.49 closed |
| SS316 | 520 | 600 | 110 | 35.0 | 8.1 | 1.95 open | 1.22 open |
| Al6061 | 416 | 350 | 88 | 10.7 | 0.20 | 0.31 closed | 0.46 closed |
| Al6061 | 520 | 350 | 88 | 13.3 | 0.20 | 0.39 closed | 0.58 closed |
| Al6061 | 416 | 900 | 88 | 6.6 | 0.52 | 0.25 closed | 0.38 closed |
| Al6061 | 520 | 900 | 88 | 8.3 | 0.52 | 0.32 closed | 0.47 closed |

(Arm K_avg at m1 2.1, n1 2.2; Al6061 `dH/hs` uses `A 0.10` and the 293 K set, it is far below any served cut, so the served gate is closed on every Al row as well.)

Expectation: **FAIL for both arms**, driven by Al6061 (failure mode 1): Gan ran these Al6061 rows as keyhole experiments and his Fig 1 to 2 Al cases are keyholes, so most of the 9 rows are probably observed keyhole mode while every arm and the served gate predict closed. If instead several Al rows are transition (`e* < 2`), item 3 can hold and the SS316 split (failure mode 2) decides between K_s and K_avg: K_s opens at 208 W / 300 mm/s (dH/hs 19.8, below the served cut 20 but above 15), K_avg does not. Spurious pass risk: none visible; the risk is the other way, a FAIL that is really an absorptance failure on Al. That is still worth the run (about 60 closed form evaluations): it is the first held-out test of the served leg's own threshold and of the conductivity convention, and the per row R table steers P3.

## 9. What stays unchanged whatever the outcome

`experimentalValidation=false`; original N3 NOT PASSED; original N4 NOT EVALUATED; served depth numbers, labels, fingerprint and `main` untouched by this lane; the IN625 cut 13.6 and the shared 15/20 cuts untouched; the Fabbro leg constants untouched.

## 10. What a PASS licenses

Only a planned bump on a BUILD lane (goldens, parity `--expect-drift`, PROOF entry, fresh Opus gate, same procedure as SPEC P1 section 6) that replaces `dH/hs >= 15` and the 15 to 30 ramp in the one depth path by the passing arm's `R >= 1` test (leg open iff `R >= 1`; the leg value itself stays Fabbro Eq 2 at the served constants unless K_avg passed, in which case the bump also needs a sourced k(T) table per app alloy and a separate SOURCES file before it can change `K`). The served regime labels (`classify_enthalpy_regime`, 15/20/13.6) are not touched by that bump: they are a different observable (etched `d > w/2` on IN625 and 316L data) and keep their own evidence trail. No accuracy claim on melt depth follows from a PASS on X-ray vapour depth; N3 stays NOT PASSED; the depth bias note keeps its text until a MELT observable run says otherwise. A contradiction flag (section 6.2) blocks the bump.

## 11. Machine-readable declaration

```json declaration
{
  "schema": "lpbf-keyhole-onset-p2-v1",
  "lane": "P2 keyhole onset",
  "base": "393cdbd1",
  "criterion": "Fabbro 2020 threshold: R = A_flat P / (K (Tv - T0) d (m Pe + n)) >= 1, Pe = v (d/2) / alpha_solid_app",
  "arms": {
    "K_s": {"m": 2.4, "n": 3.0, "K": "app solid k_s", "source": "Fabbro 2020 Eq 2, 6; p.3"},
    "K_avg": {"m": 2.1, "n": 2.2, "K": "temperature averaged k(T), T0 to Tv, section 3.3", "source": "Fabbro 2020 Eq 11, Sec 3.3 p.7-8"}
  },
  "peclet_convention": "v * (d/2) / alpha_solid (app set; Gan SI 293 K values for Al6061); liquid alpha descriptive only",
  "property_sets": {
    "SS316": {"app": "316L Stainless Steel", "k_s": 16.3, "k_avg": 25.9, "cp_s": 500, "rho": 7990, "T_liq_C": 1400, "Tv_C": 2814, "A": 0.42},
    "Al6061": {"k_s": 179.2, "k_avg": 119.8, "cp_s": 867, "rho": 2705, "T_liq_C": 642, "Tv_C": 2470, "A": 0.10, "source": "Gan 2021 SI Table 1 at 293 K; Tv open question 1"},
    "IN718": {"app": "Inconel 718", "k_s": 11.4, "k_avg": null}
  },
  "k_avg_tolerance_W_mK": 0.1,
  "primary": {"set": "gan2021_data1 Al6061 (9) + SS316 (7)", "observable": "VAPOR keyhole depth e, class keyhole if e/r0 >= 2", "d": "2 r0 as released", "T0_C": 20, "ti64_rows": "excluded (SPENT), descriptive only"},
  "secondary_descriptive": [
    {"set": "mds2-2923 IN718 AMMT spot series, 5 conditions", "observable": "MELT d > w/2 per section, condition majority", "excluded": "set IN718_20210323_M290 (all Data rows and its Summary row, previewed per INV 0.1)"},
    {"set": "hann-ss304-2011, 14 welds", "observable": "MELT side_reported", "proxy": "app 316L"}
  ],
  "excluded": {"ku-leuven-in718": "no header or unit row, units and half-width operator unresolved, beam unverified, no conduction side", "gan_data2": "power released as eta (P - P0), not incident"},
  "conditional": {"bitharas2022": "section 6.4, void if Figure_data.xlsx absent at run time"},
  "baselines": ["served gate dH/hs >= 15 (leg) and >= 20 (keyhole mode)", "Gan Ke >= 6 with released eta (in-sample, never refit)"],
  "descriptive": ["Cunningham 2P/(pi D^2) >= 0.4 MW/cm2", "liquid alpha Pe", "A_F(1) = 0.32", "Ti64 Data 1 rows"],
  "pass_rule": {
    "per_arm_all_of": [
      "correct >= 13 of 16 (exact binomial p <= 0.0106)",
      "both observed classes present and balanced accuracy >= 0.80, else INCONCLUSIVE",
      "errors <= 1 of 7 SS316 and errors <= 2 of 9 Al6061",
      "errors(arm) <= errors(served baseline)",
      "completeness: finite R on all 16 rows for arm, served and Gan Ke, else INCONCLUSIVE"
    ],
    "multiplicity": "Bonferroni 0.05 over 2 arms (0.025 each)",
    "lane_verdict": "PASS if at least one arm passes; both pass -> K_avg first; secondary and descriptive never pass; contradiction flag blocks the bump"
  },
  "expectation": "both arms FAIL, Al6061 rows observed keyhole while every arm predicts closed (R <= 0.58); SS316 split decides K_s vs K_avg",
  "licenses_on_pass": "planned BUILD bump replacing dH/hs >= 15 gate and 15->30 ramp by R >= 1; labels, regime cuts, N3 status unchanged",
  "experimentalValidation": false,
  "original_N3": "NOT_PASSED",
  "original_N4": "NOT_EVALUATED"
}
```
