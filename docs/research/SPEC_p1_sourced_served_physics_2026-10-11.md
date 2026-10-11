# SPEC P1: sourced forms for the uncited parts of the served melt pool depth path

Date 2026-10-11. Lane type BUILD (planned physics bump), branch `research/phys-keyhole` for the spec, bump branch to be opened by the builder from current main. Author: physics designer (Fable). Gate: a fresh Opus run. Implementer: Sonnet.
Base: local main `393cdbd1` (fingerprint `0d52d7f7...`, `VERSION enthalpy-fv-6`, `BUILD_JOB_SOLVER_REVISION lpbf-build-job-in625-regime-v20`).
Inputs: `.orchestra/reports/physics_forms_sweep_2026-10-11.md` (SWEEP), `.orchestra/reports/blind_validation_inventory_2026-10-11.md` (INV), `docs/research/RESULTS_depth_path_stage1_2026-10-11.md` and `_stage1b_` (R1, R1b), `python/lpbf_thermal_solver.py` at `393cdbd1` (TS), `python/fabbro_keyhole.py` (FK). Paper library `C:/Users/can02/Projects/metalliksaa/papers` (INDEX.md).
Blast radius report `.orchestra/reports/p1_bump_blast_radius_2026-10-11.md`: TODO, not present when this spec was written (another agent is writing it); section 9 lists what this spec found by grep and must be reconciled with that report before the bump starts.

**What P1 is.** An honesty fix. Four served expressions have no source (TS 638 to 645, 661 to 663, 721 to 737, 436, 994; FK docstring). P1 replaces each with a sourced form or removes it with a sourced justification. Acceptance is software correctness: unit tests against the source equations and limits, parity `--expect-drift` with a full allowlist, goldens re-recorded once, PROOF entry, fingerprint re-pin, gate. **P1 makes no accuracy claim.** N3 stays NOT PASSED, N4 NOT EVALUATED, `experimentalValidation=false`, `validationStatus=unvalidated`, `productionReady=false`; no served evidence label or wording that users read as validation changes. The keyhole onset gate (item D, `dH/hs >= 15` and the 15 to 30 ramp) is **not** touched: that is P2 (`PREDECLARED_keyhole_onset_2026-10-11.md`).

## 0. Open questions for the gate (decide before the builder starts)

1. **Item A, keyhole leg absorptance.** This spec keeps the Fabbro leg at the flat absorptivity and cites Fabbro 2020 for it (section 2), and rejects the Gouffe/Kelly cavity form for the served leg because Fabbro 2020 Sec 4.1 reports that it overestimates measured A(R) for R < 3 and because coupling it to the served leg roughly doubles keyhole regime depth (section 2.4 table). Alternative: adopt the Gouffe/Kelly cone with a bounded bisection (fully specified in section 2.3) so that the leg carries a sourced A(R). The alternative is an unvalidated accuracy change hidden inside an honesty bump; recommendation: reject for P1, reserve for P3.
2. **Item B, latent heat.** This spec removes the field power factor (factor 1.0 for every kernel, section 3). Alternative, also sourced: apparent heat capacity `cp_app = cp + Lf/(T_liq - T0)` inside the Rosenthal field (section 3.3). Recommendation: remove; the apparent heat capacity variant changes the field shape, not only its amplitude, and needs its own tests.
3. **Keyhole leg conductivity.** The served leg uses the app room temperature solid `k_s` (IN625 9.8, Ti64 6.7). Fabbro's own constants imply a high temperature K (his `a1 = n1 K (Tv - T0) = 2.1e5 W/m` for Ti64 gives K about 29 W/mK). P1 does not change `k_s` (no per alloy sourced k(T) table exists for all app alloys; Sabau 2018 covers IN625 only). P2 tests both conventions on held-out data. Confirm that this stays out of P1.
4. **Process map depth proxy** (TS 999 to 1004, multipliers 0.45 / 0.70 / 1.15, uncited). Section 4.4 folds it into the one depth path. The gate may defer it to a later chore if it prefers a smaller diff; the spec treats it as in scope because the backlog item 0b names it ("process-window grid proxy, third uncited model").

## 1. The one depth path (design summary)

Today the three kernels disagree in structure: Eagar-Tsai and Goldak serve `depth = max(d_iso, e_Fabbro_ramped)` with the conduction field at the flat absorptivity and no latent factor; Rosenthal serves `depth = d_iso + increment(dH/hs)` with the field driven by a multi-reflection absorptivity ramp and a latent factor. P1 gives every kernel the first structure:

    P_field  = A_flat * P                                   (all kernels; was eta_eff * P * latent_factor for Rosenthal)
    d_iso    = liquidus depth of the conduction field       (unchanged search, floor changed, section 4.3)
    e_kh     = Fabbro Eq. 2 at A_flat, k_s, alpha_s, T_vap   (unchanged, FK; ramp unchanged, item D)
    depth    = max(d_iso, e_kh)
    keyholeVaporCavityDepth_um = max(0, e_kh - d_iso)       (already the Eagar-Tsai / Goldak meaning)

No kernel specific multiplier remains. The served `fabbro-keyhole-v1` function is not edited; its docstring sentence about "a calibrated effective value (NIST AMB2022-03 ...)" is replaced by the citation in section 2.2 (that one point comparison is spent data and is not a calibration).

## 2. Item A: multiple reflection absorptance

### 2.1 What is removed

TS 638 to 645: `cavity_aspect = min(4, (dH/hs - 15)/8)`, `n = 1 + 1.8 cavity_aspect`, `eta_eff = 1 - (1 - A)^n`. TS 994: process map `eff_p = (1 - (1 - A)^2.2) P` above the transition cut. Neither the aspect map, the 1.8, the 4 nor the 2.2 has a source (SWEEP section 1 found no paper with these forms). The research mirror `lpbf_regime_absorptivity_kernel.py` 115 to 120 carries the same lines (section 9).

### 2.2 Chosen form: flat absorptivity in both the conduction field and the keyhole leg

Equation: `P_field = A_flat P` for every kernel; `A_fabbro = A_flat` (as now). `effectiveAbsorptivity` is served equal to `A_flat` with the basis text of section 7.

Sources and locators:
- Conduction field at the flat value: Knapp et al. 2022 (`knapp2022_calibrating_meltpool_am.pdf`, Bayesian calibration on AMMT IN625): effective absorptivity 0.27 to 0.32, "about Fresnel 0.30" (BOARD decision log 2026-10-11, library index); Eagar and Tsai 1983 and Goldak 1984 take the absorbed power as Q (TS 656, already served). Rubenchik 2018 Sec 3.1 and Gan 2021 SI Method 3 use a single absorptivity in the conduction scaling (SWEEP 2A).
- Keyhole leg at the flat value: Fabbro 2020 (`fabbro2020.pdf`, doi 10.3390/app10041487) Sec 3.3 p.8: for the aspect ratios of the generalized piston model the front wall Fresnel absorptivity stays in `0.31 < A_F(R) < 0.36` (text verified, this spec's extraction); Sec 4.1 p.10 to 12, Fig 8 to 9: the Gouffe cone formula overestimates the measured A(R) of Trapp 2017 for R < 3, and `A_F(1) = 1 - (1 - A0)^2 = 0.52` only at R = 1 for steel (SWEEP 1F, TEXT). In LPBF the served leg's R = e/d is below 3 for nearly every app condition (section 2.4 table, column `R`), so the sourced level is the flat value, not a multiplied one.
- Fabbro 2010 (`fabbro2010.pdf`) Sec 3.1: with A0 0.7, "one to two more reflections" add about 30 percent to depth; a statement, not an equation (SWEEP 1G). It bounds the error of ignoring reflections at the leg level and is cited in the basis text as the known omission.

Constants: none new. `A_flat` is the material authority's `absorptivity_IR` (unchanged per alloy). Evaluation: trivial. Per heat source: identical. Per alloy: identical.

### 2.3 Rejected sourced alternative (specified so the gate can choose it)

Gouffe 1945 / Kelly 1966 cavity absorptance as reproduced by Coleman et al. 2024 Eq 7 (`coleman2024_dynamic_volumetric_source_am.pdf`, printed p.11 to 12, PDF p.11, verified by the SWEEP on the page image and by this spec's text extraction; **the primaries Gouffe 1945, Kelly 1966 and Buckley 1927 are not in the library**, see section 10):

    eta(a) = eta0 [1 + (1 - eta0)(G - F)] / [1 - (1 - eta0)(1 - G)],  a = e / r0 = 2 R,  theta = atan(1/a)
    cone:      G = 1 / (1 + sqrt(1 + a^2)),  F = sin^3(theta)
    cylinder:  G = 0.5 / (1 + a),            F = sin^2(theta)

Limits: `eta(0) = eta0` (flat), `eta -> 1` as `a -> inf`. Hand values with eta0 0.28: cone 0.51, 0.65, 0.75 at a = 1, 2, 4; cylinder 0.50, 0.68, 0.82 (SWEEP 1.3, reproduced by this spec's script). Coupled to Fabbro Eq 2 (`e = eta P / (k (Tv - T0)(m Pe + n))`, `R = e/d`) the self consistent `eta` is the root of `f(A) = A - eta(2 e(A)/d)` on `[eta0, 1]`; `f(eta0) <= 0`, `f(1) >= 0`, so bisection with absolute tolerance 1e-4 ends in at most 14 iterations (bounded, deterministic, about 30 microseconds in Python; `eta0` would be `A_flat`). Kaplan 1994 (`kaplan1994.pdf`, printed p.1808 to 1809, Eq 22 to 27, Fig 3, verified) gives the triangle cavity bound `n_mr = pi/(4 theta_w)`, `alpha_mr = 1 - rho_Fr^(n_mr - 1)`, used only as a cross check (lower than the cone).
Why rejected for P1: section 2.2 Fabbro evidence; and the table in 2.4 shows the coupled leg at the served `k_s` more than doubles keyhole regime depth (Ti64 118 to 301 um, 316L 251 to 576 um), an accuracy change that no held-out run supports (R1, R1b failed with milder absorptance maps). It belongs to P3 (cavity model falsified on X-ray vapour depth first).

### 2.4 Expected drift of item A (with items B and C), process inputs only

Script: scratchpad `p1_drift.py` (calls `calculate_meltpool_physics` on process inputs, no measured depth; Rosenthal `d_iso` and width after the bump are approximated by `sqrt(P_field_new / P_field_served)`, the high Peclet Rosenthal width scaling, so the Rosenthal rows are rough). 20 C preheat, IR.

| material P/v/d (kernel) | dH/hs | Pe | R = e/d (flat, ramped) | eta_eff served | A_flat | latent served | depth served um | depth P1 um (rough) | width served um | width P1 um |
|---|---|---|---|---|---|---|---|---|---|---|
| IN718 200/800/80 (rosenthal, g11.0) | 22.6 | 10.0 | 0.55 | 0.726 | 0.38 | 0.838 | 103.1 | 57 (-45 %) | 148.7 | 118 (-21 %) |
| Ti64 280/1200/70 (eagar-tsai, g11.1) | 37.6 | 14.6 | 1.68 | 0.927 (not used by ET field) | 0.35 | 1.0 | 117.6 | 117.6 (0) | 128.5 | 128.5 (0) |
| 316L 370/600/60 (goldak, g11.2) | 61.9 | 4.4 | 4.19 | 0.989 (not used) | 0.42 | 1.0 | 251.1 | 251.1 (0) | 182.8 | 182.8 (0) |
| IN625 200/800/80 (rosenthal, g18) | 24.5 | 11.3 | 0.71 | 0.776 | 0.38 | 0.829 | 109.3 | 57 (-48 %) | 150.3 | 116 (-23 %) |
| IN625 195/800/100 (rosenthal, Lane CBM A inputs) | 17.1 | 14.1 | 0.10 | 0.504 | 0.38 | 0.829 | 70.2 | 55 (-22 %) | 118.2 | 113 (-5 %) |
| IN625 195/800/170 (rosenthal, Lane AMMT inputs) | 7.7 | 24.0 | 0 | 0.380 | 0.38 | 0.829 | 47.2 | 52 (+10 %) | 98.6 | 108 (+10 %) |
| 316L 150/700/80 (rosenthal) | 15.1 | 6.9 | 0.01 | 0.426 | 0.42 | 0.856 | 54.1 | 50 (-7 %) | 96.9 | 104 (+7 %) |
| IN625 100/300/80 (rosenthal) | 20.0 | 4.2 | 0.43 | 0.637 | 0.38 | 0.829 | 97.0 | 62 (-36 %) | 149.5 | 127 (-15 %) |
| IN625 75/50/80 (rosenthal, Pe below band) | 36.7 | 0.7 | 2.71 | 0.940 | 0.38 | 0.829 | 327.4 | 217 (-34 %, leg) | 333.7 | 233 (-30 %) |
| AlSi10Mg 350/1200/80 (rosenthal) | 12.5 | 0.9 | 0 | 0.180 | 0.18 | 0.734 | 56.4 | 66 (+17 %) | 113.6 | 133 (+17 %) |

Direction: Eagar-Tsai and Goldak numbers do not move (items A and B already hold there; item C's floor moves only the heuristic fallback rows). Rosenthal below the transition cut rises by the removed latent factor (+5 to +17 %, larger for AlSi10Mg with its large Stefan number). Rosenthal above the cut falls by 20 to 50 %: the removed absorptivity ramp dominates, and the Fabbro leg at the flat value (ramped) rarely exceeds the conduction depth there. The served IN625 depth note (Lane CBM underprediction) therefore gets worse in the transition band; that is recorded, not hidden (section 7). Cross kernel spread shrinks: the three kernels now share the keyhole leg and differ only in the conduction field.

## 3. Item B: latent heat factor on the field power

### 3.1 What is removed

TS 661 to 663: `latent_heat_power_factor = 1/(1 + 0.55 St)`, `St = Lf / (cp_blend (T_liq - T0))`, Rosenthal only. No paper supplies a `1/(1 + k St)` power cut (SWEEP section 2, five sourced handlings, none of this form).

### 3.2 Chosen form: factor 1.0 for every kernel (remove)

Equation: `latent_heat_power_factor = 1.0`; `P_field = A_flat P`. `latentHeatPowerFactor` stays served (value 1.0) so consumers (`src/services/pythonComputationService.ts` 1238, `src/utils/goldakCaeCard.ts` 31 to 149) keep their field; the card text that names the 0.55 factor is rewritten (section 9).
Sources: Rubenchik 2018 Sec 3.1 (`1-s2.0-S0924013618300906-am.pdf`, PDF p.5): the heat of fusion is ignored because it is small and does not affect the temperature distribution (SWEEP 2A, TEXT); Gan 2021 SI Supplementary Method 3 p.6 (`gan2021_SI.pdf`): "We neglect the latent heat of melting because it is much smaller than the energy required to heat material to the melting point" (this spec's extraction); Ye 2019 Tab 1 and Sec 3.3 (`ye2019.pdf`, p.4): `Hm` about `rho Cp Tm`, latent heat excluded. Eagar and Tsai 1983 and Goldak 1984 (served citations at TS 656) take Q as the absorbed power. The normalized enthalpy index already excludes latent heat (`hs = rho cp_s (T_liq - T0)`, TS 629) and the Fabbro leg uses `Tv` only, so the whole path becomes latent free and consistent.
Stefan number: still computed and served (`stefanNumber`), descriptive only.
Evaluation: trivial. Per kernel: identical. Per alloy: identical. Drift: section 2.4 (+5 to +17 % Rosenthal field power to the 0.5 power, below the cut; above the cut it is swamped by item A).

### 3.3 Sourced alternative (if the gate wants latent heat kept)

Apparent heat capacity in the Rosenthal field: `cp_app = cp_blend + Lf / (T_liq - T0)`, `alpha_app = k_blend / (rho cp_app)`, field unchanged otherwise. Source: Hann 2011 Tab 2 (`hann2011.pdf`, PDF p.5, verified image): `hf/hs = 1.4` generic (304 SS 1.33, V 1.37, Ti64 1.36) from Richards' rule, which is `1 + St` with `St = Lf/(cp (Tm - T0))`; using `hf` in place of `hs` is the sourced way to keep fusion enthalpy in a conduction scaling. Gusarov 2007 Sec 2 and Coleman 2024 energy equation use the same apparent capacity in numerical models (SWEEP 2E). It changes the exponential decay length of the Rosenthal field (`alpha_app` about `alpha/(1 + St)`), so rear length and depth shrink by roughly `(1 + St)^-0.5` at high Pe; it is not a power factor. Needs its own limit test (`Lf = 0` reproduces the plain field). Not recommended for P1.

## 4. Item C: Rosenthal keyhole depth increment, d_iso floor, process map depth proxy

### 4.1 What is removed

TS 721 to 737: `extra = d_iso (0.15 + 0.55 t)` for `15 <= dH/hs < 30`, `d_iso (0.85 + 0.55 log10(1 + (dH/hs - 30)/10))` above, Rosenthal only; `KEYHOLE_INCREMENT_MODEL_ID`, `KEYHOLE_INCREMENT_BASIS`, `KEYHOLE_INCREMENT_FULL_AT`. TS 436: fallback floor `d_iso = half_w (0.38 + 0.10 min(1, dH/hs / 15))`. TS 999 to 1004: grid depth proxy `0.45 w`, `0.70 w`, `1.15 w`. None has a source (SWEEP 3, 3.2; TS comment 721 to 723 says so).

### 4.2 Chosen form for the depth: `depth = max(d_iso, e_kh)` for every kernel

This is the served Eagar-Tsai and Goldak rule (TS 724 to 726) applied to Rosenthal. The keyhole leg `e_kh` is Fabbro 2020 Eq 2 exactly as served in FK (`e = A P / (K (Tv - T0)(m Pe + n))`, `Pe = V d / (2 kappa)`, `m = 2.4`, `n = 3` for `2 <= Pe <= 10`, Fabbro 2020 p.3, text verified by this spec; `pecletInFitRange` flag unchanged; the 15 to 30 ramp unchanged and still labelled uncited, item D). The max is Fabbro's own reading: the conduction isotherm and the keyhole depth are two estimates of the same bottom, the deeper one wins (Fabbro 2020 Eq 7 and Sec 3: below Pt the pool is the conduction pool). Constants: none new. Evaluation: closed form. Per alloy: `k_s`, `alpha_s`, `T_vap`, `A_flat` from the authority as now.
`keyholeDepthModel.modelId` becomes `FABBRO_MODEL_ID` for every kernel; `basis` becomes `FABBRO_BASIS` (its text is updated, section 7). Drift: section 2.4.

### 4.3 Chosen form for the fallback floor: `d_iso = half_w` (ratio 1.0)

The fallback (TS 423 to 440) runs only when the field has no resolvable liquidus extent and is already served as `heuristic-width-fallback`, "not resolved". The served Rosenthal field `rosenthal_temperature_C` (TS 281 to 292) depends on `R = sqrt(x^2 + y^2 + z^2)` and `x` only, so it is symmetric under `y <-> z`: at any station x its liquidus half width and depth are equal. The sourced floor for a Rosenthal substitute is therefore `d_iso = half_w` exactly (Rosenthal 1946 point source, primary not in library, section 10; King 2014 Sec 5.1 p.2921 states the conduction pool as a semicircle, depth about half width, `king2014.pdf`). For Eagar-Tsai and Goldak the distributed source makes depth below half width (Hofmann 2026 Sec 2.2: conduction up to d/w 0.5; Cunningham 2019 SM p.3: d/w about 0.5 at the melt pool transition), so ratio 1.0 is an upper bound there; acceptable because the branch is labelled not resolved, and the extent note gains the sentence "depth set equal to the half width (Rosenthal symmetry), an upper bound for distributed sources". Drift: only rows that hit the fallback (low power, tiny pools, g6 case): their depth rises 2.1 to 2.6 times (from 0.38 to 0.48 to 1.0 of `half_w`).

### 4.4 Chosen form for the process map proxy (optional per open question 4)

Width cell: `eff_p = A_flat P` for every cell (item A). Depth cell: `d = max(0.5 w, e_kh(P, v))` with the same Fabbro leg (ramped, same gate) and the semicircle conduction floor `0.5 w` (King 2014 Sec 5.1 to 5.2; the keyhole criterion `d > w/2` of Sec 5.2 is exactly the point where the leg takes over). The lack of fusion test (Tang) reads the new `d`. Cost: 49 closed form evaluations. Drift: every grid cell's `width_um` and `depth_um` moves; regime labels and colors do not (they read `enth` and the per alloy cuts, untouched).

## 5. Tests (self contained, synthetic fixtures, no measured depth)

New file `python/test_lpbf_p1_sourced_depth_path.py` (plus edits listed in section 9):

1. `test_field_power_is_flat_absorptivity_every_kernel`: for a synthetic material dict (rho 8000, k 10/30, cp 400/700, T_liq 1300, T_boil 2800, Lf 2.9e5, A 0.4) injected through `prop_overrides` and three kernels, `processParameters.effectiveAbsorptivity == conductionAbsorptivity == 0.4`, `latentHeatPowerFactor == 1.0`, `fieldPower_W == 0.4 P` at dH/hs 8, 18 and 40.
2. `test_depth_is_max_of_isotherm_and_fabbro_every_kernel`: `depth_um == max(depth_um - keyholeVaporCavityDepth_um, fabbro depth)` to 0.05 um, and `keyholeVaporCavityDepth_um == max(0, e - d_iso)`, on 6 synthetic (P, v, d) points spanning dH/hs 5 to 45 and Pe 0.5 to 25, three kernels; the Fabbro reference value recomputed in the test from `fabbro_keyhole_depth_m` with the same inputs.
3. `test_no_increment_constants_remain`: `solver` has no attribute `KEYHOLE_INCREMENT_FULL_AT`, `KEYHOLE_INCREMENT_MODEL_ID`, `KEYHOLE_INCREMENT_BASIS`; `keyholeDepthModel.modelId == "fabbro-keyhole-v1"` for every kernel; `basis` contains "flat" and "Fabbro 2020" and not "uncited screening heuristic: extra depth".
4. `test_fabbro_eq2_against_source_numbers`: Fabbro 2020 Eq 2 and Eq 3 identity (keep `test_lpbf_waveb_rosenthal_keyhole.FabbroLA4`), plus `R0 = A P/(n d K dT)`, `V0 = 2 n kappa/(m d)` on a synthetic input.
5. `test_fallback_floor_is_half_width`: force the fallback (P 20 W, v 2500 mm/s, d 200 um, synthetic material) and check `extentStatus == "heuristic-width-fallback"`, `depth_um - keyholeVaporCavityDepth_um == width_um / 2` to 0.05 um, note contains "Rosenthal symmetry".
6. `test_rosenthal_field_yz_symmetry`: `rosenthal_temperature_C(x, y, 0) == rosenthal_temperature_C(x, 0, y)` on a 5 x 5 grid (the derivation behind item 4.3).
7. `test_latent_free_limit`: with `Lf = 0` and with `Lf = 5e5` in `prop_overrides` all served geometry numbers are identical (latent heat no longer enters any served number except `stefanNumber`).
8. `test_process_map_proxy` (if 4.4 is in scope): each grid cell `depth_um == max(0.5 width_um, e_kh)` to 0.1 um and `width_um` uses `A_flat P`; regime labels equal the pre bump labels for a pinned synthetic grid (labelled synthetic in the fixture docstring).
9. `test_kernel_parity_of_keyhole_leg`: for one synthetic input, `keyholeDepthModel.depth_um` (the leg value) is identical across the three kernels (the leg does not depend on the kernel).
10. Gouffe/Kelly form is **not** implemented, so no test; if open question 1 is decided the other way, add `test_gouffe_limits` (flat limit `eta(0) = eta0`, `eta(1e6) > 0.99`, cone below cylinder for a > 0, bisection ends within 14 iterations, hand values 0.51 / 0.65 / 0.75 at eta0 0.28, a 1 / 2 / 4).

Existing tests that pin the removed heuristics and must be changed in the same commit (each with a one line reason in the diff): `test_lpbf_keyhole_regime_bump.py` (78 `KEYHOLE_INCREMENT_FULL_AT`; `UnchangedNumerics.test_rosenthal_increment_unchanged` and `PRE_BUMP_ROSENTHAL` table, `test_process_map_depth_proxy_unchanged` and `PRE_GRID_*`: these were the in625-regime "no number changed" proofs; retire them into the new bump's record, do not re-fit the tables), `test_lpbf_tier2_physics_bump.py` 83 (`effectiveAbsorptivity 0.884`), `test_lpbf_waveb_rosenthal_keyhole.py` 136 to 156 (`LatentHeatFactorLA5.test_rosenthal_factor_exported` formula, `IncrementAndRecoilLA8.test_model_id_is_heuristic`), `test_eagar_tsai.py` 99 to 100 (reads `d_iso` as depth minus cavity: still valid, keep), `test_lpbf_build_job.py` 652 (`BUILD_JOB_SOLVER_REVISION`).

## 6. Bump procedure (mirrors the in625-regime bump, `git log --stat efafe933..0e7f7ab7`)

1. Builder opens `fix/p1-sourced-depth-path` in `../Metalliksa-1-wt-p1` from current main after the gate approves this spec and `p1_bump_blast_radius` exists. Record the pre bump sha (`REV0`) and confirm `python tools/lpbf_parity_check.py --check --slow` is all PASS at `REV0`.
2. Code commit: `python/lpbf_thermal_solver.py` (items A, B, C, basis texts, `effectiveAbsorptivity` meaning), `python/fabbro_keyhole.py` docstring only (remove the one point "calibrated effective value" sentence; FK numbers untouched), `python/lpbf_regime_absorptivity_kernel.py` mirror lines, `python/lpbf_job_cache.py` `BUILD_JOB_SOLVER_REVISION` -> `lpbf-build-job-p1-sourced-v21`, TS text in `src/utils/goldakCaeCard.ts`, new and edited tests (section 5), `docs/LPBF_ENGINEERING.md` model scope lines. `npm run lint`, `npm run test:unit`, targeted python tests.
3. Re-pin: `python tools/lpbf_fingerprint_pin.py` regenerate `lpbf_implementation_fingerprint.expected` (deliberate; commit message says why).
4. Record: from `python/`, locked interpreter, `python -B tools/lpbf_bump_record.py --from-revision REV0 --with-parity-check --slow --expect-drift <full diff key set of a prior --check --slow --expect-unpinned run> --out ../docs/LPBF_IMPLEMENTATION_BUMP_2026-10-XX_p1-sourced.json`, plus `.expect-drift.txt` and `.reasons.md` with a per case cause table (expected drift: g6 fallback rows, g11 all three thermal dicts, g18, every Rosenthal geometry; Eagar-Tsai and Goldak geometry only where the fallback or the grid changes; transient cases g1 to g10, g12 to g17, g19, NPZ bit equal). A 693 case snapshot (7 alloys x 11 P-v x 3 spots x 3 kernels) against `REV0` is run and summarised in the reasons file: which keys moved, sign and size per regime, and the explicit statement that Eagar-Tsai and Goldak `depth_um`, `width_um`, `length_um` are bit equal outside the fallback.
5. Goldens: re-record `python/golden/lpbf_parity/*` once, guarded commit; pin `GOLDEN_FINGERPRINT`, `REVISION` and `HTTP_GOLDEN` digests in `test_lpbf_parity_golden.py` and `test_lpbf_calibration_frozen.py`.
6. Records at the new fingerprint: NIST 2716/2525 comparison records (fingerprint only), error bands and leaderboard regenerated (`data/calibration/lpbf-meltpool-error-bands-v1*`, `docs/LPBF_LEADERBOARD_<date>.json`; cells **will** change this time, which the reasons file says), demo snapshots re-recorded, `test_lpbf_regime_absorptivity_config.py` check.
7. PROOF entry (English, same shape as the 2026-10-11 in625-regime entry): scope, what was removed and what source replaced it, drift table from step 4, labels unchanged, limits (no accuracy claim, N3 NOT PASSED, the Lane CBM underprediction grows, the leg's `k_s` and the 15 to 30 ramp still uncited and queued for P2).
8. Gate: fresh Opus reviews the diff, lint, full unit suite, python tests listed in section 5, `module_registry.py --check`, fingerprint pin, `check_ceiling_review.py`. At most 2 fix rounds. Lead merges, updates BOARD.md; maintainer trailer and push with the batch.

## 7. Served text that changes (English, no label promotion)

- `FABBRO_BASIS`: "Fabbro 2020 eq. 2 with the flat-surface absorptivity: Fabbro 2020 Sec. 3.3 and 4.1 report the front-wall Fresnel absorptivity in 0.31 to 0.36 for aspect ratios below 3 and that cavity (Gouffe) forms overestimate measured A(R) there; no multiple-reflection gain is applied (Fabbro 2010 Sec. 3.1: one to two extra reflections add about 30 percent depth, a known omission). m=2.4, n=3 fitted for 2<=Pe<=10; uncited linear dH/hs onset ramp 15->30 (P2); k_s is the room-temperature solid value (Fabbro's constants imply a high-temperature K; P2). Depth served as max(conduction isotherm depth, this leg) for every kernel; " + `KEYHOLE_DEPTH_BENCHMARK_NOTE` (kept).
- `effectiveAbsorptivity` basis: "flat absorptivity of the material authority for the conduction field (Knapp 2022 calibrated 0.27 to 0.32 for IN625 conduction mode; Eagar-Tsai 1983 and Goldak 1984 take Q as absorbed power); the former multi-reflection ramp 1-(1-A)^n (uncited) was removed 2026-10-XX".
- `latentHeatPowerFactor` basis: "1.0 for every kernel; latent heat of fusion is excluded from the conduction field (Rubenchik 2018 Sec. 3.1, Gan 2021 SI Method 3), from the index hs and from the Fabbro leg; the former 1/(1+0.55 St) factor (uncited) was removed".
- Depth bias note (`lpbf_depth_bias.py`, `src/utils/depthBiasWarning.ts`): no class edge changes; the UNDER text gains "the sourced path serves the conduction isotherm until the Fabbro leg exceeds it, so transition-band depth is lower than before 2026-10-XX". Direction logic unchanged.
- `REGIME_THRESHOLD_BASIS`, `REGIME_MATERIAL_NOTE_*`, `KEYHOLE_POROSITY_BASIS`: unchanged.
- No `experimentalValidation`, `validationStatus`, `productionReady` or evidence kind changes. UI strings that users read as validation are not touched; the maintainer owns label wording.

## 8. Acceptance (what PASS means for this lane)

All of: section 5 tests green; parity record with 0 FAIL and every DRIFT allowlisted and explained; goldens re-recorded once; `pinMatchesToHash` and `versionUnchanged` true; PROOF entry; gate approval. **Not** part of acceptance: any MAPE, any held-out number, any comparison with measured depth. The regenerated error bands and leaderboard are descriptive records at the new fingerprint, not evidence for the bump.

## 9. Blast radius found by grep at `393cdbd1` (reconcile with the TODO report)

Python served: `lpbf_thermal_solver.py` 228 to 256, 436, 638 to 664, 721 to 737, 994 to 1004, 1053, 1069, 1078, 1097 to 1098. Research mirror (outside or inside the manifest to be confirmed by the record tool): `lpbf_regime_absorptivity_kernel.py` 115 to 136, 176 to 181. Unchanged: `fabbro_keyhole.py` numbers, `lpbf_public_datasets.normalized_enthalpy`, `classify_enthalpy_regime`, IN625 cut 13.6. Revision string: `lpbf_job_cache.py` 25. TypeScript: `src/utils/goldakCaeCard.ts` 31 to 35, 144, 149 (text names the 0.55 factor), `src/services/pythonComputationService.ts` 1238 to 1248 (types only, keep), `src/components/3d-distortion-lab/MeltPool3DCrossSectionLab.tsx` 1142 (reads `keyholeVaporCavityDepth_um`, keep). Tests: section 5 list. Goldens: `python/golden/lpbf_parity/g6_screening_and_fallback.json`, `g11_build_job_meltpool.json`, `g18_in625_latent_heat.json` at least; HTTP_GOLDEN digests; demo snapshots; error bands; leaderboard. Docs: `docs/LPBF_ENGINEERING.md`, `PROOF.md`, `STATUS.md` milestone line.

## 10. Primary sources needed that are not in the library

| source | needed for | DOI |
|---|---|---|
| Kelly F. J. 1966, Appl. Opt. 5, 925 to 927 | Gouffe/Kelly cone form (2.3), only if open question 1 is decided for the cavity form | 10.1364/AO.5.000925 |
| Gouffe A. 1945, Rev. Opt. 24, 1 to 10 | same (cylinder, cone origin) | none (pre DOI) |
| Buckley H. 1927, Phil. Mag. 4, 753 to 762 | cylinder form | 10.1080/14786441008564378 |
| Rosenthal D. 1946, Trans. ASME 68, 849 to 866 | fallback floor derivation (4.3); the symmetry is also visible in the served field | none (pre DOI) |
| Eagar T. W., Tsai N. S. 1983, Weld. J. 62, 346s to 355s | conduction floor d/w (4.3, 4.4) | none |
| Fabbro R. et al. 2018, J. Laser Appl. 30, 032410 | origin of m 2.4, n 3 in the served leg (cited through Fabbro 2020 ref 16) | 10.2351/1.5040624 |
| Rai R. et al. 2007, J. Phys. D 40, 5753 | hs convention check (King Tab 3), not needed for P1 numbers | 10.1088/0022-3727/40/18/037 |
