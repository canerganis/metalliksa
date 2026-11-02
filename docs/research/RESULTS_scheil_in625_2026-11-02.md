# Scheil solidification research arm: IN625 (mc_ni) and Ti-6Al-4V (mc_ti), 2026-11-02

Label for every number below: **Literature estimate / Research / not validated**. These are CALPHAD
calculations on open databases, not measurements. The Scheil limit (complete liquid mixing, no solid
diffusion, local interface equilibrium) is not the LPBF solidification path: no undercooling, no solute
trapping, no evaporation, no cooling rate. Nothing here is wired into served outputs.

Code: `python/research_scheil.py` (pure core `scheil_path`, pycalphad adapter `run_case`).
Tests: `python/test_research_scheil.py` (fast synthetic fixtures; one real IN625 solve behind
`METALLIX_SLOW_TESTS=1`). Raw results: `docs/research/RESULTS_scheil_in625_2026-11-02.json`.

## Design origin

A problem-only brief (problem, constraints, databases and files, deliverable; no physics route; no
approval trailer allowed) went to Codex Astra in read-only mode during the first, interrupted attempt of this
lane on 2026-11-02. The brief text was not preserved; Astra's answer (in Turkish) is in the untracked
worktree file `.tmp-astra-scheil.md`, not committed. Astra answered with a design; the parts used
here: per-step weighting of every solid vertex by the same remaining liquid, independent inventory closure
per step and per path, threshold temperatures as brackets, no forced `f_s = 1`, stop on two liquids or gas,
pairing with the existing equilibrium path under the same TDB hash, phase set, used composition and
calculation options, and the literature list below. Implementation and parameter choices are this lane's.

Astra also pointed out a defect in the installed `scheil` 0.3.0 package (not used by the repository). Checked
by reading `.runtime/lpbf-win-py312/Lib/site-packages/scheil/simulate.py` line 267 and line 300: the solid
phases of one step are booked as `(1 - current_fraction_solid) * NP` with `current_fraction_solid` updated
inside the phase loop, so 0.8 liquid + 0.1 + 0.1 solid books 0.19 instead of 0.20; and the path appends an
artificial `fraction_solid = 1.0` point when it stops early. The fast test
`test_two_solids_in_one_step_use_same_liquid_weight` pins the correct 0.20 for this module.

## Databases

| Case | TDB file | SHA-256 | Licence | Scope notes |
|---|---|---|---|---|
| IN625 | `python/databases/mc_ni_v2036_repaired.tdb` (MatCalc mc_ni 2.036, syntactic repair) | `c914f534cc99f5fc2f7aab0373cfe5bc720bd2b85b545027d35ac4e0bcc6f94d` | ODbL 1.0 / DbCL 1.0, `python/databases/MATCALC_OPEN_DATABASES_LICENSE.md` | Bulk Cr 21.5 and Mo 9.0 wt% exceed the header's tested limits (Cr < 20, Mo < 5). No Ta, no P. BCC_B2 excluded (catalogue). Seeded starting points, pdens 10. |
| Ti-6Al-4V | `python/databases/mc_ti_v203_repaired.tdb` (MatCalc mc_ti 2.03, syntactic repair) | `f8758e12d8a96109b4dee0e0d95365ebe6ec19b0d1b8e3b249465c46a12e94ff` | ODbL 1.0 / DbCL 1.0, same licence file | Optimised 773-2000 K, V < 5 wt%. No C, Fe, O, N, H. Default pycalphad sampling. |

pycalphad 0.11.2, Python 3.12.10, P = 101325 Pa. Fractions are moles of atoms.

## Compositions (nominal design scenarios, wt%, not batch analyses)

- `in625_c0`: Ni 61.0, Cr 21.5, Mo 9.0, Nb 3.6, Fe 4.9. Inside Special Metals INCONEL 625 bulletin Table 1
  limits; Nb+Ta realised as Nb 3.6, Ta 0. Same scenario as `python/test_calphad_matcalc_open.py` and the
  `ALLOY_KNOWN_DEVIATIONS` record in `python/calphad_solver.py`. Si, Mn, Al, Ti, C, P, S not represented.
- `ti64_mc_ti`: Ti 90, Al 6, V 4 (ideal ternary). Fe, O, C, N, H not represented.

No composition clamp was applied (equilibrium `compositionAdjustments` empty; Scheil `conditionClampUses` 0).

## Results

Equilibrium: `calphad_solver.solve_pycalphad_equilibrium(..., scheil=False)`, 10 K grid, boundaries
refined to 0.1 K. Scheil: start 1 K above the upper end of the equilibrium liquidus bracket (verified fully
liquid), start step 2 K (and 1 K for IN625), refinement down to 0.0625 K, every threshold crossing refined to a
bracket of at most 0.5 K, stop when the residual liquid falls below 1e-4.

### IN625 C-free (mc_ni)

| Quantity | 2 K run | 1 K run |
|---|---|---|
| Equilibrium liquidus / solidus (C) | 1366.2 [1366.1, 1366.2] / 1309.2 [1309.2, 1309.3] | same call |
| Equilibrium range (K) | 57.0 | |
| Scheil T(fs=0.001) (C) | 1365.95 [1365.7, 1366.2] | 1365.95 [1365.7, 1366.2] |
| Scheil T(fs=0.5) | 1344.95 | 1344.45 |
| Scheil T(fs=0.9) | 1238.95 | 1237.95 |
| Scheil T(fs=0.99) | 1152.45 | 1151.95 |
| Scheil T(fs=0.999) | 1150.45 [1150.2, 1150.7] | 1150.45 [1150.2, 1150.7] |
| Scheil range 0.1-99.9 % (K) | 215.5 (bounds 215.0-216.0) | 215.5 |
| Last valid T, residual liquid | 1149.2 C, 2.1e-5 | 1149.2 C, 1.6e-5 |
| Phases (mol fraction of atoms) | FCC_A1 0.9696, DELTA 0.0217, LAVES 0.0046, BCC_A2 0.0040 | FCC_A1 0.9694, DELTA 0.0217, LAVES 0.0049, BCC_A2 0.0041 |
| Phase appearance brackets (C) | FCC [1365.7, 1366.2], DELTA [1191.7, 1193.7], LAVES [1183.7, 1185.7], BCC_A2 [1152.7, 1153.7] | DELTA [1192.7, 1193.7], LAVES [1184.7, 1185.7], BCC_A2 [1152.7, 1153.7] |
| Path inventory max abs error | 3.1e-10 | 1.3e-9 |
| Solver calls / refined or rejected steps | 148 / 24 | 231 / 8 |

- Paired comparison: Scheil first solid minus equilibrium liquidus = **-0.25 K** (inside the brackets, as
  expected from the same thermodynamics). Scheil T(fs=0.999) minus equilibrium solidus = **-158.75 K**.
  The Scheil range is 3.8 times the equilibrium range.
- Step convergence 2 K to 1 K: threshold shifts 0.0 / -0.5 / -1.0 / -0.5 / 0.0 K for fs 0.001 / 0.5 / 0.9 /
  0.99 / 0.999. Within the 1 K target; a 0.5 K run was not made.
- Residual liquid at 1149.2 C: Ni 52.4, Cr 27.1, Nb 18.6, Fe 1.0, Mo 0.8 wt%. Nb (18.6) and Cr (27.1) in the
  late liquid exceed the tested limits (Nb < 6, Cr < 20): the terminal part of the path is a database
  extrapolation on top of the bulk Cr/Mo excursion. (Computed after the run from `residualLiquidX`; this run
  predates the `liquidOutsideTestedLimits` field.)
- Reproduction check: the equilibrium boundaries reproduce the recorded mc_ni values 1366.1 / 1309.1 C
  (`python/calphad_solver.py` ALLOY_KNOWN_DEVIATIONS, 2026-10-07) within 0.1 K. The independent Scheil
  core reproduces the served `scheil_gulliver` record for the same scenario ("complete to 1150 degC with
  DELTA 2.2, LAVES 0.47 and BCC_A2 0.4 mol%", same record). Same TDB and minimiser, so this checks the
  bookkeeping, not the physics.
- The path stops on residual liquid below 1e-4, not on liquid exhaustion: `temperatureExhaustion` is null.
  T(fs=0.99) and T(fs=0.999) lie 2 K apart, so the last per cent freezes in a narrow, invariant-like interval
  that was not resolved as a single-step jump.

### Ti-6Al-4V ternary (mc_ti), extra case

| Quantity | Value |
|---|---|
| Equilibrium liquidus / solidus (C) | 1647.4 [1647.4, 1647.5] / 1578.8 [1578.7, 1578.8]; range 68.6 K |
| Scheil T(fs=0.001 / 0.5 / 0.9 / 0.99 / 0.999) (C) | 1647.25 / 1623.25 / 1507.75 / 1409.75 / 1390.25 |
| Scheil range 0.1-99.9 % (K) | 257.0 (bounds 256.5-257.5) |
| Phases | BCC_A2 only (0.99991), residual liquid 9.1e-5 at 1369.0 C |
| Paired deltas | first solid -0.15 K; last solid -188.55 K |
| Liquid outside tested limits | V above 5 wt% from 1635 C (fs 0.33); residual liquid at 1369.0 C: V 24.3, Al 18.1 wt% (V peaks at 26.19 wt% along the path, see liquidOutsideTestedLimits.maxLiquidWtPct) |
| Path inventory max abs error | 1.4e-11 (176 calls) |

Single-phase primary BCC with no terminal reaction gives a long Scheil tail. Below fs 0.33 the liquid lies
outside the database's tested V range, so the tail below about 1635 C is an extrapolation. One 2 K run only;
no step convergence check for this case.

## Literature comparison and contradictions

Signed differences are model minus source. None of these sources is a matched observation of the same
chemistry, observable and thermal history; a difference is reported, not used to tune anything.

### IN625

| Source and locator | Source values | mc_ni equilibrium | mc_ni Scheil | Match of observable |
|---|---|---|---|---|
| Cieslak, Headley, Kollie, Romig 1988, Metall. Trans. A 19A 2319, DOI 10.1007/BF02645056, PDF3 / printed p. 2321 Table II (heating DTA, 4 C/min); as transcribed in `docs/research/SPEC_solidification_2026-10-14.md` A2.3 | Alloys 5-8 Ts/Tl: 1308/1363.3, 1289.3/1362, 1287.8/1356, 1275.7/1352 C; ranges 55.3-76.3 K | Tl +2.9 to +14.2 K; Ts +1.2 to +33.5 K; range 57.0 vs 55.3-76.3 K | T(0.999) 1150.45: 125 to 158 K below the DTA Ts; Scheil range 215.5 vs 55-76 K | Heating DTA of low-Fe heats (Fe about 2.3 wt%, varied C/Si; Table I not transcribed here) vs a C-free, Si-free, Fe 4.9 calculation |
| Cieslak 1988, Section III-B (via `docs/LPBF_SCHEIL_LAVES_2026-10-07.md`) | Minor constituent 0.3-1.3 vol% in rapid-scan DTA specimens; Laves, NbC and with Si M6C (Tables IV, IX) | n/a | LAVES 0.46-0.49 plus DELTA 2.17 plus BCC_A2 0.40 mol% of atoms | mol fraction of atoms is not vol%; DELTA is not among the reported constituents |
| Sabau et al. 2020, Metall. Mater. Trans. B, DOI 10.1007/s11663-020-01808-w, PDF7 / printed p. 1269, "Setup of STLF Simulation Model and Material Properties" | 1290 / 1350 C model interval (linear fraction), origin of the pair not resolved | Tl +16.2 K, Ts +19.2 K | T(0.999) 139.55 K below 1290 | Model prescription, not a measurement |
| TCNI12 table, Zenodo record 22901717, row "Inconel 625", read as kelvin (`docs/XCHECK_SUPERALLOY_TABLE.md` line 43) | 1340 / 1262 C | Tl +26.2 K, Ts +47.2 K | T(0.999) 111.55 K below 1262 | Another CALPHAD assessment, equilibrium, unknown definitions |

Contradictions (unresolved):

1. **Equilibrium solidus vs DTA solidus.** mc_ni's equilibrium solidus 1309.2 C lies at or above all four
   Cieslak heating-DTA solidus values (1275.7-1308 C). Possible causes not separated here: missing C and Si
   (Cieslak varied both; the 0.05 C mc_ni record gives 1283.1 C, ALLOY_KNOWN_DEVIATIONS), Fe 4.9 vs about
   2.3, the bulk Cr/Mo excursion outside the tested range, and the DTA onset construction.
2. **Scheil terminal temperature vs DTA solidus.** The Scheil 99.9 % temperature (1150.45 C) is 125-158 K
   below the DTA solidus values and the Scheil range is 2.8 to 3.9 times the DTA ranges. A heating DTA of
   cast or welded material is not a Scheil cooling path, so this is not a direct refutation; but if the DTA
   solidus is read as the melting of the last-solidified interdendritic material, the Scheil tail is far too
   long for these heats.
3. **Terminal phases.** The calculation puts DELTA (2.2 mol%) ahead of LAVES (0.5 mol%) and adds BCC_A2;
   Cieslak reports Laves, NbC and M6C and no delta in the solidification constituent. Without C the
   calculation cannot form NbC. The C = 0.05 case that would test this was not run (see below).

### Ti-6Al-4V

| Source and locator | Source values | mc_ti equilibrium | mc_ti Scheil |
|---|---|---|---|
| Gan et al. 2021, Nat. Commun., DOI 10.1038/s41467-021-22704-0, SI PDF20 Supplementary Table 1 (compiled model inputs) | Ts / Tl 1877 / 1933 K = 1603.85 / 1659.85 C, 56 K (other repo records, e.g. REVIEW_ti64_w1_p8_pairing_2026-10-20.md line 58, carry 1877.15 / 1933.15 K = 1604.0 / 1660.0 C; the 0.15 K difference does not change any conclusion) | Tl -12.45 K, Ts -25.05 K, range 68.6 K | T(0.999) 213.6 K below Gan Ts; range 257 K |
| Cezairliyan et al. 1977, PDF3 / printed p. 253 (pulse heating, solidus), via `docs/research/sol_t_ti_al_sources.md` | Solidus 1942.6 K = 1669.45 C, estimated total inaccuracy 8 K; no liquidus | mc_ti liquidus is 22.05 K below this measured solidus | first solid 22.2 K below it |
| Boivineau et al. 2006, DOI 10.1007/s10765-005-0001-6, PDF16 / printed p. 522 (liquidus inferred from extrapolated emissivity) | 1928 K = 1654.85 C | Tl -7.45 K | n/a |

Contradiction (unresolved): the Cezairliyan pulse-heating solidus (1669.45 C) lies above the mc_ti
liquidus (1647.4 C) by 22 K, more than the stated 8 K inaccuracy. Either the mc_ti ternary liquidus is low
for this alloy, or the source lot (Fe 0.15, O 0.17 wt%, not in mc_ti), the IPTS-68 scale, or the rapid
heating explain it; none was separated. COST 507 (not run here) is recorded at about 1686 / 1681 C for
Ti-6Al-4V, on the other side of the same sources.

## Not done

- IN625 with 0.05 C (`--case in625_c005`), AlSi10Mg on COST 507 (`--case alsi10mg_cost507`), Ti-6Al-4V on
  COST 507, the Brandt Al-9Si-0.6Mg chemistry: not run (light-mode budget). Commands are in the lane report.
- 0.5 K start step for IN625, Ti-6Al-4V 1 K run, and the mc_ni sampling-density sensitivity (seeded pdens
  10 / 30 / 60): not run.
- No partition-coefficient extraction (k_Nb) from the Scheil tie-lines in this arm.
- No lever-rule (full back-diffusion) path from CALPHAD; only the synthetic-fixture limit test.
