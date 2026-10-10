# LPBF NIST mds2-2525 absorptance comparison (2026-10-11)

**Comparison of application absorptivity and prescribed-cavity ray tracing against NIST mds2-2525 measured laser absorptance; not experimental validation; application outputs are screening and unvalidated; nothing was tuned.**

Schema `lpbf-nist-2525-absorptance-comparison-1`; implementation fingerprint `0d52d7f707b98fc588c0972c1c198315d3c1071ed1c7ad7ab91616e69b5248e8`; quick mode: False; fingerprint test passed: True; loader: `lpbf_nist_mds2_2525_absorptance`. Honesty: comparison, not validation; NIST values are measured for the NIST experiment only (polished bare Ti-6Al-4V, ~300 um coupon, argon); application outputs are screening and unvalidated; the ray-tracing sweep over prescribed cavity depth is a sensitivity bracket, not a calibration; nothing was tuned to the data; where the application cannot represent the experiment the record says unavailable and no number is forced. `experimentalValidation` = false, `opticalOperatorMatched` = false, `modelAcceptance` = false, `nistResidual` = null.

## Dataset

Asynchronous AM Bench 2022 Challenge Data: Real-time, simultaneous absorptance and high-speed Xray imaging, DOI 10.18434/mds2-2525, version 1.3.2, license https://www.nist.gov/open/license.

Citation: Simonds, B. J., Tanner, J., Artusio-Glimpse, A., Williams, P. A., Parab, N., Zhao, C., & Sun, T. (2022). Asynchronous AM Bench 2022 Challenge Data: Real-time, simultaneous absorptance and high-speed Xray imaging (v1.3.2). National Institute of Standards and Technology. https://doi.org/10.18434/mds2-2525 (constructed from the NERDm record fields)

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| Spot on Bare Metal_Calibrated Absorption Data.csv | 6497288 | `0e96b220852d762fde846e406cc44c6fc874cef22e7e41db7f4025dbcc9ca274` |
| Al_Spot_AA_ASR_Results.csv | 242 | `4429f08ff3f571ab871fdbaf072e0c67aaef346259a3f2ca8744927ad6419ffb` |
| Al_Scan_AA_MWD_ASR_Results.csv | 364 | `d3732fcddaaee046105aa90eb82547ffd0fe61edb425fc1e8f019c6f73ed0b4d` |
| Al_Spot_TDW_Results.csv | 2169 | `06b280222eab5f82eb9dcfb0689f20a5011c16e115548cd94ce120e5a97b4f5c` |
| Al_Spot_TDA_Results.csv | 2292050 | `3f0b6812f98535f5ffbb0e2fed31f084ad9a7f9cc393c04a43ed57f0bb14bf69` |
| Al_Scan_TDA_v2_Results.csv | 2493685 | `3af3478b463b867ed3c78ef6e60c75f9d613607b236933f3f9df08113884a6a8` |
| 2525_README_v200.txt | 21907 | `936f4c166b448f4b5a27d1e2b2465f9c2db1be073a7bffd54d45eb4259120a65` |

- Not acquired: `Scan on Bare Metal_Calibrated Absorption Data.csv` (official SHA-256 `1c64f24e84c274d9f9ae27fb09e79b86cda2fda5bee4b67da3567c8a59ca499d`): file not acquired (NIST download unavailable; no archived copy with the official SHA-256).
- Not acquired: `Absorption_Uncertainty_Analysis.pdf` (official SHA-256 `98ead678e3a8f6696650302dbf29660f2a886a62ba677453dd130c222755e28d`): file not acquired (NIST download unavailable; no archived copy with the official SHA-256).

Experiment: Ti-6Al-4V (NIST SRM 654b), 1070 nm, 1/e^2 spot diameter 122.5 um (+/- 3.0 um), 7 deg incidence, polished bare metal (no powder), ~300 um thin Ti-6Al-4V coupon (not a semi-infinite plate), argon, integrating sphere, 40 ns resolution.

## Measured summary (Ti-6Al-4V stationary 2 ms pulse; measured for the NIST experiment only)

| Quantity | Value | Unit |
| --- | ---: | --- |
| Median input power while on | 101.9 | W |
| Pre-keyhole mean, window [0.05, 0.8] ms (local) | 32.47 | % |
| Pre-keyhole sample std | 1.451 | % |
| Keyhole-phase mean, window [0.9, 2.0] ms (local) | 62.01 | % |
| Keyhole-phase sample std | 7.091 | % |
| Transition time (local rule) | 0.85 | ms |
| Energy coupling, absorbed J / input J (derived locally, trapezoid over laser-on samples) | 49.4 | % |
| Median per-sample absorbed-power uncertainty | 1.158 | W |
| ... as percentage points of median input | 1.137 | pp |

RelativeAbsorption (%) is NIST column 6 ('Percent absorption'; README: input minus backscattered power, divided by input power, x 100) per 40 ns sample, used as published and not recomputed here; window means are plain means of that column inside local windows. Windows are measured from the first sample with input power above the laser-on threshold. They are local analysis windows chosen in this module, not NIST-published phase boundaries; NIST publishes before/during-keyhole averages only for the aluminium challenge tables.

## Headline comparison (measured vs model)

| Quantity | Measured | Model | Difference | Status |
| --- | ---: | ---: | ---: | --- |
| pre-keyhole absorptance, Ti-6Al-4V stationary pulse | 32.47 +/- 1.451 % | 35 % | 2.529 (percentage points (model - measured)) | compared |
| keyhole-phase absorptance, prescribed-depth sweep | 62.01 +/- 7.091 % | 35 to 93.56 % (sweep) | - | sensitivity-only |

Flat-plate absorptivity of record: 35 % (origin: lpbf_thermal_solver.thermal_props('Ti-6Al-4V')['absorptivity_IR'] (four_alloy_materials)). Model minus measured = 2.529 percentage points (7.788 % relative). Note: the secondary inline table has no Ti-6Al-4V entry, so no legacy value competes with the resolved one. Solver role: flat-plate eta_base_flat of calculate_meltpool_physics: the solver's default absorptivity on every machine since the 2026-10-06 tier-2 bump (powder_bed_raytracer's effective absorptivity is used only with an explicit absorption_model='powder-raytrace').

## Ray-tracing sensitivity sweep (prescribed Gaussian cavity; SENSITIVITY, not calibration)

Model `prescribed-cavity-ray-optics-v2`, Warp 1.17.0, device cpu, power 101.9 W (measured median), beam radius 61.25 um, base absorption 0.35, 20000 rays, 16 max bounces, seed 0, mesh 96x96 at 4 um (extent 380 um = 6.204 beam radii).

| Depth (um) | Absorbed (%) | Std err (pp) | Escaped (%) | Truncated (%) | Mean segments | At bounce limit (%) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 35 | 3.925e-17 | 65 | 0 | 2 | 0 |
| 25 | 35.76 | 0.002248 | 64.24 | 0 | 2 | 0 |
| 50 | 37.49 | 0.006799 | 62.51 | 0 | 2 | 0 |
| 100 | 61.46 | 0.05279 | 38.54 | 0 | 2.917 | 0 |
| 150 | 71.48 | 0.06741 | 28.52 | 0 | 3.475 | 0 |
| 200 | 77.67 | 0.06924 | 22.33 | 0 | 3.941 | 0 |
| 300 | 85.76 | 0.05703 | 14.24 | 0 | 4.761 | 0 |
| 400 | 89.67 | 0.055 | 10.33 | 0 | 5.476 | 0 |
| 600 | 93.56 | 0.04779 | 6.44 | 1.173e-06 | 6.743 | 0 |

Flat self-consistency: depth 0 gives 35 % against base 35 % (1.824e-06 pp); normal incidence; empirical law A = a(1 + 0.5(1 - cos)) reduces to a at cos = 1; the 7 deg incidence is not represented.

Bracket: sweep brackets the measured keyhole-phase mean between prescribed depths [[100.0, 150.0]] (sweep range 35 to 93.56 %); information only: the real cavity is neither Gaussian nor static, so a bracketing depth is not a prediction and not a calibration.

## Unavailable

| Item | Material | Reason |
| --- | --- | --- |
| keyhole-phase absorptance, direct prediction (no prescribed depth) (measured 62.01 %) | Ti-6Al-4V (NIST SRM 654b) | the application does not solve the cavity depth (no free surface) and the Ti-6Al-4V X-ray cavity depth is not among the pinned files, so there is no depth to feed the ray tracer |
| multi-reflection eta_eff, Ti-6Al-4V stationary pulse (measured 62.01 %) | Ti-6Al-4V (NIST SRM 654b) | stationary 2 ms pulse is not representable by the moving-source kernels of calculate_meltpool_physics (scan speed must be > 0; a near-zero speed is not a valid substitute and was not run) |
| Ti-6Al-4V scan (700 mm/s) before/during-keyhole absorptance | Ti-6Al-4V (NIST SRM 654b) | Ti-6Al-4V scan CSV Scan on Bare Metal_Calibrated Absorption Data.csv: file not acquired (NIST download unavailable; no archived copy with the official SHA-256) |
| NIST published absorptance uncertainty analysis | Ti-6Al-4V (NIST SRM 654b) | Absorption_Uncertainty_Analysis.pdf: file not acquired (NIST download unavailable; no archived copy with the official SHA-256); only the per-sample uncertainty column is used |
| absorbed J / input J over the 2 ms pulse (measured context) (measured 49.4 %) | Ti-6Al-4V (NIST SRM 654b) | no model counterpart: the application has no time-resolved stationary-pulse absorption model |
| Al spot absorptance before keyhole (measured 23.9 %) | aluminium (NIST SRM 1241c) | the application's locked alloy set (Ti-6Al-4V, 316L, AlSi10Mg, IN718; IN625 screening) has no aluminium SRM 1241c; AlSi10Mg is a different alloy and is not substituted |
| Al spot absorptance during keyhole (measured 64.1 %) | aluminium (NIST SRM 1241c) | the application's locked alloy set (Ti-6Al-4V, 316L, AlSi10Mg, IN718; IN625 screening) has no aluminium SRM 1241c; AlSi10Mg is a different alloy and is not substituted |
| Al scan absorptance before keyhole (measured 23.8 %) | aluminium (NIST SRM 1241c) | the application's locked alloy set (Ti-6Al-4V, 316L, AlSi10Mg, IN718; IN625 screening) has no aluminium SRM 1241c; AlSi10Mg is a different alloy and is not substituted |
| Al scan absorptance during keyhole (measured 43.3 %) | aluminium (NIST SRM 1241c) | the application's locked alloy set (Ti-6Al-4V, 316L, AlSi10Mg, IN718; IN625 screening) has no aluminium SRM 1241c; AlSi10Mg is a different alloy and is not substituted |
| Al scan maximum melt-pool depth (measured 88.8 micrometer) | aluminium (NIST SRM 1241c) | the application's locked alloy set (Ti-6Al-4V, 316L, AlSi10Mg, IN718; IN625 screening) has no aluminium SRM 1241c; AlSi10Mg is a different alloy and is not substituted |
| Al scan maximum melt-pool width (measured 326 micrometer) | aluminium (NIST SRM 1241c) | the application's locked alloy set (Ti-6Al-4V, 316L, AlSi10Mg, IN718; IN625 screening) has no aluminium SRM 1241c; AlSi10Mg is a different alloy and is not substituted |
| Al spot melt-pool width vs time (TDW; value shown is the series maximum) (measured 515.3 micrometer) | aluminium (NIST SRM 1241c) | the application's locked alloy set (Ti-6Al-4V, 316L, AlSi10Mg, IN718; IN625 screening) has no aluminium SRM 1241c; AlSi10Mg is a different alloy and is not substituted; additionally a stationary source is not representable by the moving-source kernels |

## Limits

- The NIST coupon is ~300 um thin; the application's conduction kernels and the flat-plate absorptivity assume a semi-infinite plate, so late-pulse heat accumulation and absorptance differ in kind.
- The NIST source is stationary for 2 ms; the thermal-solver absorptivity logic is moving-source only, so the stationary pulse has no thermal-solver counterpart (not run at a fake speed).
- The ray tracer uses a prescribed Gaussian cavity with a fixed depth per run, not a solved keyhole; the real cavity is dynamic and not Gaussian, so a bracketing depth is not a prediction.
- The ray tracer's angular absorption law is empirical (A = a(1 + 0.5(1 - cos theta))), not complex-index Fresnel optics, and ray power still in flight at the 16-bounce limit is reported as truncated, never as absorbed or escaped.
- The experimental 7 deg incidence is not modelled (rays at normal incidence); the flat-plate absorptivity is a constant with no angle or temperature dependence.
- NIST absorptance was measured on polished bare metal in argon, not on powder; no powder-bed claim is made.
- Aluminium (SRM 1241c) before/during-keyhole averages carry three-run standard deviations only and are not comparable with any application alloy.
- Pre-keyhole (0.05-0.80 ms) and keyhole (0.90-2.00 ms) windows are local analysis windows chosen in this work from the first laser-on sample, not NIST-published phase boundaries; the sub-microsecond leading-edge spike is excluded by starting the first window at 0.05 ms.
- The Ti-6Al-4V scan CSV and the NIST uncertainty-analysis PDF were not acquired; the scan comparison and the NIST uncertainty budget are unavailable.
- The measured uncertainty is the per-sample column median (W) only; no replicate Ti-6Al-4V runs are in the pinned files, so the window std is a within-trace sample spread, not a run-to-run uncertainty.
- Sampling standard errors of the ray tracer exclude geometry, bounce truncation and model error.
- No model input was tuned to the data; any disagreement above is the application's, reported as found.
