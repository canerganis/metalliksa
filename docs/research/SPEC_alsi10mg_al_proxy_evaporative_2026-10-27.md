# AlSi10Mg fixed-surface evaporative model on an Al6061 proxy profile

Status: implemented 2026-10-27, lane `lane/alsi-2026-10-27` (base `fc585b4a`). Research model,
`experimentalValidation=false`. Mirrors `SPEC_ti64_evaporative_cpu_2026-10-20.md` and
`SPEC_ti64_standard_integration_2026-10-20.md`.

## Why a proxy

The registry AlSi10Mg transient table (`four_alloy_materials.py`, OPEN O8) uses unsourced solid
endpoints, liquid cp, latent heat and an assumed emissivity (Terra design review, 2026-10-27).
Lead decision: build the model on ONE complete, sourced, labelled Al-rich proxy profile, the
Al6061 column of Gan et al. 2021 Nat Commun Supplementary Tables 1 and 2 (citing Valencia and
Quested 2013, ASM Handbook "Thermophysical properties"). The OPEN O8 values are not used and not
relabelled. Every output carries the disclosure:

> Thermal and vapour constants are Al6061 values (Gan 2021 SI Tables 1-2, citing Valencia and
> Quested 2013) used as an Al-rich proxy for AlSi10Mg; Mg and Si selective evaporation and the
> real AlSi10Mg composition are not modelled.

## Identity

- Model `alsi10mg-al6061-proxy-fixed-surface-evaporation-v1`, schema `lpbf-alsi10mg-evaporative-result-v1`.
- `python/lpbf_al_proxy_evaporation.py`: constants table, `SOURCE_PROFILE`, supplied material table,
  Al vapor law. Reuses `EvaporationConfig`, `_number`, `_array`, `_bridge_coefficients` and
  `update_onset` from `lpbf_ti64_evaporation` by import.
- `python/lpbf_alsi10mg_evaporative_solver.py`: request, kernel and run loop mirroring the Ti64
  solver; grid, snapshot, thermal continuation and canonical JSON helpers imported from it.
  Identity hashes all four module files (own two plus the two Ti64 files it imports).
- Worker job type `alsi10mg-evaporative-surface` (`python/lpbf_worker.py`), HTTP through the
  existing `/api/lpbf/jobs`, UI `src/components/AlSi10MgEvaporativePanel.tsx` shown when the
  shared material is AlSi10Mg (bare plate only, own opt-in and Run button).
- No Ti64 file, Standard solver file, registry or golden changed.

## Constants (Gan et al. 2021, `papers/gan2021_SI.pdf`, Al6061 column)

Values read from `pdftotext -layout` and confirmed on the rendered pages (the text extraction
interleaves the Ti64, Al6061 and SS316 columns).

| Quantity | Value | Unit | Table, page, row | Used as |
|---|---|---|---|---|
| Density, T < 915 K | 2705 | kg/m3 | T1, p. 20, Density rho_l | solid rows; fixed reference density |
| Density, T >= 915 K | 2415 | kg/m3 | T1, p. 20, Density rho_l | liquid rows |
| Heat capacity, T < 915 K | 0.486T+725 | J/(kg K) | T1, p. 20, Heat capacity (liquid) C_pl | solid cp |
| Heat capacity, T >= 915 K | 1170 | J/(kg K) | T1, p. 20, Heat capacity (liquid) C_pl | liquid cp, also above 2792 K |
| Conductivity, T < 915 K | 0.091T+152.5 | W/(m K) | T1, p. 20, Thermal conductivity (liquid) k_l | solid k |
| Conductivity, T >= 915 K | 90 | W/(m K) | T1, p. 20, Thermal conductivity (liquid) k_l | liquid k |
| Solidus | 873 | K | T1, p. 20, Solidus temperature | latent release start |
| Liquidus | 915 | K | T1, p. 20, Liquidus temperature | latent release end, melt isotherm |
| Latent heat of melting | 3.8e5 | J/kg | T1, p. 20 | enthalpy table |
| Vaporization point | 2792 | K | T1, p. 20 | Clausius-Clapeyron reference, table endpoint |
| Latent heat of vaporization | 1.053e7 | J/kg | T1, p. 20 | vapor law, q = j L_v |
| Molar mass | 27 | g/mol | T1, p. 20 | vapor law |
| Surface tension | 0.91 | N/m | T1, p. 20 | UI scalar for the gate 2 sigma/r |
| d sigma/dT | -3.5e-4 | N/(m K) | T1, p. 20 | material dGamma_dT only; gate uses scalar sigma (Ti64 rule) |
| Emissivity | 0.1 | - | T1, p. 20 | top-face radiation |
| Dynamic viscosity | 1e-3 | Pa s | T1, p. 20 | table column only, unused by conduction |
| Low vaporization threshold | 2800 | K | T2, p. 21, Al6061 block | UI transitionLow_K |
| High vaporization threshold | 3200 | K | T2, p. 21, Al6061 block | UI transitionHigh_K |
| Retro-diffusion coefficient | 0.18 | - | T2, p. 21, computational constants | UI returnFraction |
| Ablation a1/b1, c1/d1; surface pressure a2/b2, c2/d2 | see module | - | T2, p. 21, Al6061 block | recorded only, not evaluated |

Not from Gan, disclosed:

- Absorptivity 0.30: the existing AlSi10Mg authority (Leis, Weber, Graf 2020, Procedia CIRP 94,
  Sec. 3, Figs. 4 to 6), imported from `ABSORPTIVITY_AUTHORITY["alsi10mg"]`. Gan's "minimal
  absorptivity" 0.01 is a ray-tracing Fresnel floor, not an effective absorptance.
- p_ref 101325 Pa (normal boiling point convention), ambient 101325 Pa and the 5000 K scenario
  ceiling: declared, as in the Ti64 model.
- Gan's property step at 915 K is carried by a declared 1 K linear ramp (914 to 915 K) in the
  piecewise-linear table. Gan's solid branches are evaluated down to 273.15 K, below which Gan states
  no lower bound. The liquid branch (T >= 915 K, no stated upper bound) is held above 2792 K.

## Vapor law (same construction as Ti64)

T <= low: j = 0, p_r = p_ambient. T >= high: p_sat = p_ref exp[(L_v M/R)(1/T_v - 1/T)],
j = (1-beta) p_sat sqrt(M/(2 pi R T)), p_r = (1+beta) p_sat/2. Between: cubic Hermite bridge
matching zero value and slope at low and the closed-form value and slope at high, separately for j
and p_r. For 2800/3200 K and beta 0.18 the bridge is monotone (scaled slope ratio 1.27 for j and
2.07 for p_r, both inside [0, 3]). The Table 2 polynomials are not evaluated.

Gate (A1.1, unchanged rule): any active exposed cell with p_r - p_ambient >= 2 sigma/r latches onset;
depth, length and volume are then null with a refusal reason. Missing sigma with active evaporation
latches unresolved geometry.

## Results (2026-10-27, reference CPU, Python 3.12)

Acceptance tests, all passing:

| Check | Result | Limit |
|---|---|---|
| Independent Maxwellian quadrature vs mass flux, 3200/3800/5000 K | <= 1e-8 rel | 1e-8 |
| Zero flux below 2800 K, recoil = ambient | exact | exact |
| Bridge value/derivative continuity at 2800 and 3200 K | < 1e-6 scaled | 1e-6 |
| Single-cell cooling ODE (RK4 reference, 4000 K start), errors 0.346, 0.172, 0.0860 K | order 1.007, 1.003 | > 0.8 |
| Cooling ODE energy, evaporated vs enthalpy removed | < 1e-10 rel | 1e-10 |
| Analytical conduction, L2 at n = 8, 16, 32 | 3.47e-4, 8.26e-5, 2.04e-5 | monotone decrease |
| Moving source 300 W / 1300 mm/s / 100 um, 100 um track, 20 um mesh | evaporative 4.94e-5 J, residual 5.0e-16 | > 0, <= 1e-9 |

Real CLI run, `python python/lpbf_alsi10mg_evaporative_solver.py`, inputs 300 W, 1300 mm/s,
100 um beam, 80 C preheat, bare plate, solver defaults (600 um track, 20 um mesh, 0.5 ms cooling),
scenario 2800/3200 K, beta 0.18, sigma 0.91 N/m, ambient 101325 Pa, Tmax 5000 K:

- Wall time 16.0 s (subprocess timing); 3444 accepted steps, 0 rejected, mesh 45 x 45 x 15.
- Peak 3479.7 K; onset latched at 3.41e-5 s; depth, length and volume null with the vapor-cavity
  refusal reason; conditional width 140 um.
- Energy: input 4.1538e-2 J, evaporative 1.1137e-3 J, base 2.8286e-2 J, radiative/convective
  2.03e-6 J, stored 1.2137e-2 J, relative residual 3.0e-15. Diagnostic emitted mass 1.06e-10 kg.

These are uncalibrated model outputs on proxy constants, not AlSi10Mg measurements.

## Not modelled

Mg and Si selective evaporation, composition evolution, alloy activity, surface recession,
melt flow, plume shielding, keyhole geometry, powder layer. The recoil gate is a model criterion,
not an observed keyhole.
