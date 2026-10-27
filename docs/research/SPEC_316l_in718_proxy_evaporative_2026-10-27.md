# 316L and IN718 proxy fixed-surface evaporative models (research), 2026-10-27

Opt-in research models, same numerics and gate as the Ti64 model and the AlSi10Mg Al6061-proxy model.
Not experimentally validated (`experimentalValidation=false`, `productionReady=false`). Physics design by the
reviewer (Codex gpt-6.1-terra, `design-other.md`); every value below was rechecked on the source page by the builder.

| Alloy | Model id | Schema |
|---|---|---|
| 316L | `ss316l-gan2021-ss316-proxy-fixed-surface-evaporation-v1` | `lpbf-ss316l-evaporative-result-v1` |
| IN718 | `in718-fang2021-ni-proxy-fixed-surface-evaporation-v1` | `lpbf-in718-evaporative-result-v1` |

Code: `python/lpbf_proxy_evaporation.py` (profile-parameterised vapour law, label rule),
`python/lpbf_proxy_vapor_profiles.py` (constants), `python/lpbf_proxy_evaporative_solver.py` (solver and CLI),
worker job type `proxy-evaporative-surface` (alloy named in `config.material`), `src/components/ProxyEvaporativePanel.tsx`.
Ti64 and AlSi10Mg files are unchanged. The AlSi10Mg modules were not rewired onto the shared module, because its
test pins its module hash closure; a test instead shows that the shared law with the Al6061 triple reproduces the
AlSi10Mg law bitwise on 4001 temperatures (300 to 5000 K), so a later rewiring is numerically neutral.

## Vapour law

Single species. Above the high threshold: Clausius-Clapeyron saturation pressure referenced to 101325 Pa at the
vaporization point, Hertz-Knudsen mass flux times (1 - beta), recoil (1 + beta) p_sat / 2, heat flux j L_v (Gan 2021
Eqs 12/14 closed form). Between the thresholds: declared cubic Hermite bridge matching value and slope. Below the low
threshold: j = 0, recoil = ambient. Gate: recoil minus ambient >= 2 sigma / r_beam latches onset and nulls depth,
length and volume. The gate is a model criterion, not an observed keyhole.

## 316L: Gan 2021 SS316 column

Source: Gan et al. 2021, Nat Commun 12, 2379, Supplementary Information (papers/gan2021_SI.pdf), Supplementary
Table 1, printed p. 20, SS316 column (rendered page image checked; the text extraction interleaves the columns).

| Quantity | Value | Unit | Locator | Used as |
|---|---|---|---|---|
| Density, T < 1723 K / T >= 1723 K | 7950 / 6881 | kg/m3 | T1 row rho_l | table; preheat density is the fixed reference |
| c_p, T < 1723 K / T >= 1723 K | 0.24T+420.8 / 790 | J/(kg K) | T1 row C_pl | table |
| k, T < 1723 K / T >= 1723 K | 0.0146T+10.3 / 26.9 | W/(m K) | T1 row k_l | table |
| Solidus / liquidus | 1658 / 1723 | K | T1 rows T_s, T_l | latent release, melt isotherm |
| Latent heat of melting | 2.6e5 | J/kg | T1 row L_m | latent release |
| Vaporization point | 3122 | K | T1 row T_v | vapour law reference |
| Latent heat of vaporization | 6.336e6 | J/kg | T1 row L_v | vapour law, j L_v |
| Molar mass | 56 | g/mol | T1 row M_l | vapour law (one effective Fe-rich species) |
| Surface tension | 1.87 | N/m | T1 row sigma | gate default |
| d sigma / dT | -4.9e-4 | N/(m K) | T1 | recorded only |
| Emissivity | 0.3 | - | T1 | top-face radiation |
| Viscosity | 8e-3 | Pa s | T1 | table column only, unused |
| Minimal absorptivity | 0.33 | - | T1 | recorded, not used (ray-tracing floor) |
| Retro-diffusion coefficient beta | 0.18 | - | T2 p. 21, computational constants (no material column) | returnFraction default, sourced |
| Absorptivity | 0.30 | - | four_alloy_materials ABSORPTIVITY_AUTHORITY["ss316l"]: Trapp 2017 Sec. 3.1, Fig. 3a | absorbed power |

The liquidus property step is carried by a declared 1 K ramp (1722 to 1723 K). Liquid constants are held above
3122 K to maxTemperature_K (declared continuation, not a source validity range).

## IN718: Fang 2021 thermal profile, pure-Ni vapour law

| Quantity | Value | Unit | Source and locator | Used as |
|---|---|---|---|---|
| Density | 8100 | kg/m3 | Fang 2021 arXiv 2110.07108 SI Table 2 (SI p. 2, PDF p. 33) | constant density |
| Solidus / liquidus | 1533 / 1609 | K | Fang SI Table 2 | latent release, melt isotherm |
| Latent heat of fusion | 272 | kJ/kg | Fang SI Table 2 | latent release |
| Emissivity | 0.45 | - | Fang SI Table 4 (a DED model value) | top-face radiation |
| k, c_p nodes (T K: k, c_p) | 293: 10.31, 362; 373: 11.88, 378; 473: 13.6, 400; 673: 16.6, 412; 873: 20.1, 460; 1073: 26.3, 544; 1573: 30.75, 583 | W/(m K), J/(kg K) | Fang SI Table 7 (SI p. 3, PDF p. 34); caption: linear interpolation, constant above 1573 K | table |
| Ni boiling point | 3183 | K | Knapp et al. 2019, Addit. Manuf. 25, 511-521, Table 3 (journal p. 513), row Ni | vapour law reference |
| Ni heat of vaporization | 374.3 | kJ/mol | Knapp 2019 Table 3, row Ni | divided by M: 6.37721e6 J/kg |
| Ni molar mass | 58.6934 | g/mol | NIST Atomic Weights and Isotopic Compositions, Ni, standard atomic weight 58.6934(4) | vapour law |
| Surface tension | 1.882 | N/m | Mills 2002 IN718 (papers/mills2002_b.pdf) Table 1, printed p. 190, liquid row 1336 C, footnote a: extrapolated from 1725 C, 10 ppm S | gate default |
| d gamma / dT | -0.11 | mN/(m K) | Mills 2002 Eq. 8, printed p. 187 | recorded only |
| Viscosity | 7.20 | mPa s | Mills 2002 Table 1, 1336 C | table column only, unused |
| Absorptivity | 0.32 | - | four_alloy_materials ABSORPTIVITY_AUTHORITY["in718"]: Deisenroth 2026 Fig. 11 | absorbed power |
| Retro-diffusion coefficient beta | 0.18 | - | Gan 2021 SI Table 2 | returnFraction default, transferred (not an IN718 or Ni value) |

The registry needs a row at 273.15 K, so the 293 K node is held down to it (preheat is above 293 K in every
supported run). Above 1573 K the last node is held through the liquid and to maxTemperature_K, as Fang's caption
states for their own model; this is an extrapolation assumption. Fang's own vapour triple (3120 K, 2224 kJ/kg,
166.534 g/mol) is recorded as unused and never mixed with the Ni triple. Knapp 2019 was downloaded from the PSU
modeling page into a scratch directory for checking (SHA-256 1c461161...0bd9d); it is not committed.

## Scenario inputs and the output label

| Input | 316L default | IN718 default | Basis |
|---|---|---|---|
| transitionLow_K | 3022 | 3083 | unsourced declared default (T_v - 100 K) |
| transitionHigh_K | 3522 | 3583 | unsourced declared default (T_v + 400 K) |
| returnFraction | 0.18 | 0.18 | Gan SI Table 2 (316L sourced, IN718 transferred) |
| ambientPressure_Pa | 101325 | 101325 | declared convention (1 atm) |
| maxTemperature_K | 5000 | 5000 | computational limit |
| surfaceTension_N_m | 1.87 | 1.882 | Gan T1 / Mills Table 1 |

No source gives a vaporization threshold pair for SS316 or Ni (Gan Table 2 has Ti64 and Al6061 only). Per the GOAL.md
label rule M-1 item 2, the result carries `evidenceLabel` and `evidence` (summary, unresolvedInputs, userInputs,
inputBasis): at the defaults the label is **Unresolved**, naming transitionLow_K and transitionHigh_K. A changed
input is User input; Unresolved takes precedence. The UI shows the label and the two inputs before and after a run.

Not modelled: selective evaporation, activity and composition change, melt flow, surface motion, plume, keyhole
geometry. The SS316 to 316L transfer and the pure-Ni species for IN718 are stated in each disclosure.

## Acceptance (python/test_lpbf_proxy_evaporation.py, test_lpbf_proxy_evaporative_solver.py, _worker.py)

- Mass flux vs independent Gauss-Legendre Maxwellian quadrature: relative error <= 1e-8 at T_high, 4000, 5000 K, both alloys.
- Exact zero flux and ambient recoil at and below the low threshold.
- Value and slope continuity at both thresholds; analytic heat derivative vs finite difference rtol 1e-8.
- Cooling ODE (independent RK4 reference): errors 0.578, 0.287, 0.143 K (316L), order 1.008 / 1.004; IN718 order 1.009 / 1.004; energy match < 1e-10.
- Three-level analytical conduction: L2 3.47e-4, 8.26e-5, 2.04e-5 (decreasing).
- Moving source relative energy residual 5.8e-16 (316L) and 5.4e-16 (IN718), test bound 1e-9.
- Gate latch, null extents and the neutral refusal reason; missing sigma gives unresolvedGeometry; JSON CLI round trip and error output; worker strict request, cache identity, timeout and result audit (including a promoted evidence label).

## Real CLI runs (reference CPU, bare plate, solver default domain and mesh 20 um, 600 um track, 0.5 ms cooling, preheat 80 C default, declared default scenario)

| Run | 316L 200 W, 800 mm/s, 80 um | IN718 285 W, 960 mm/s, 67 um (NIST AMB2022-03 case) |
|---|---|---|
| Grid | 42 x 42 x 15 | 41 x 41 x 16 |
| Runtime | 16.2 s | 25.2 s |
| Accepted steps | 5086 | 7899 |
| Peak temperature | 4194 K | 4878 K (below the 5000 K scenario limit) |
| Onset gate | latched at 30.7 us | latched at 8.4 us |
| Width | 80.0 um | 97.7 um |
| Depth, length, volume | null (onset refusal) | null (onset refusal) |
| Input / evaporative energy | 0.0450 J / 0.00789 J | 0.0570 J / 0.0231 J |
| Relative energy residual | 1.9e-15 | 1.8e-15 |
| Diagnostic emitted mass | 1.25e-9 kg | 3.63e-9 kg |
| Evidence label | Unresolved (transitionLow_K, transitionHigh_K) | Unresolved (transitionLow_K, transitionHigh_K) |

Both runs complete; both refuse depth by the recoil criterion, so no depth is compared with NIST AMB2022-03. The
preheat of the NIST case was not set (solver default 80 C used). The IN718 peak sits 122 K below the scenario limit;
slightly higher power or lower speed may refuse the run (range error, no clipping).

## Fix round (terra gate, 2026-10-27)

- The panel has validated K inputs for transitionLow_K and transitionHigh_K (defaults unsourced; liquidus <= low < high <= 5000 K, the
  solver rule). Entered values are sent and tied to the stale-result check; changed values are the user's choice.
- Near-ceiling warning: `warnings` gains a note when peak T is within `PEAK_NEAR_CEILING_MARGIN_K` = 500 K of maxTemperature_K,
  stating the gap. The 500 K margin is a declared presentation choice, not a physical threshold; the 5000 K ceiling is the scenario's
  computational limit, not a validity limit. The peak is sensitive to unmodelled surface motion, melt flow and plume.
  The IN718 NIST case (4878 K, 122 K gap) triggers it; the pinned 100 um fixtures (peaks 3.5 to 3.7 kK) do not.
- Worker audit recomputes the evidence label (label, summary, unresolved and user input lists) from the normalised request and checks
  gate flag consistency (geometryAvailable == not onset and not unresolvedGeometry, latch times match flags).
