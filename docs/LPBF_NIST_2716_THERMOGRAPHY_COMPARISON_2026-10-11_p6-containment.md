# LPBF NIST mds2-2716 thermography trend comparison (2026-10-11)

**Sensitivity-only trend comparison of the screening kernels against NIST mds2-2716 raw camera-signal metrics; not experimental validation; no temperature conversion; application outputs are screening and unvalidated; nothing was tuned.**

Schema `lpbf-nist-2716-thermography-comparison-1`; implementation fingerprint `807d74b35239a6854ed7e5259f47711e01971b0fa3733f7aab73075e5a65faf8`; quick mode: False; kernels: rosenthal, eagar-tsai, goldak. Honesty: comparison, not validation; raw camera signal in digital levels (DL); no temperature conversion executed; application outputs are screening and unvalidated; measured and model quantities refer to different isotherms, so only normalised trends and ranks are shown (sensitivity-only); nothing tuned. `experimentalValidation` = false, `opticalOperatorMatched` = false, `modelAcceptance` = false, `nistResidual` = null, `temperatureConversion` = null.

## Inputs

Citation: Deisenroth, D., Mekhontsev, S., Lane, B., Weaver, J., & Yeung, H. (2026). AM Bench 2022 Measurement Results Data: In-situ Thermography and Scan Strategy for Laser-scanned Single Tracks and Pads on Bare In718 (AMB2022-03) (Version 1.3.1; first released 2022-07-15) [Data set]. National Institute of Standards and Technology. https://doi.org/10.18434/mds2-2716

| File | Bytes | SHA-256 | Committed |
| --- | ---: | --- | --- |
| data/benchmark/nist-amb2022-03/derived/thermography-signal-metrics-v1.json | 182588 | `7b34b3b304a95aab0dccd9481d8d944d066bfddb087bd05bd409a949b021d76a` | yes |
| AMB2022-03-718-AMMT-StaringCamera_Signal.h5 (raw NIST input) | 549979044 | `f6fe21ec911707f72e7efda2932c77eae2b75d84765848878fe5beb6b728cd43` | no |
| AMB2022-03-AMMT-718-Pad_XYPT.h5 (raw NIST input) | 406992 | `7b7004753e150bc26632e9ce356e0440429160fa92cbff8fc8559202fdce2103` | no |
| README.txt (raw NIST input) | 12573 | `ba44076ed51b69c0e4ca80ff0e2568eed2dc6459e85c9ad83b85860bee5760f2` | no |

Model inputs: IN718, liquidus 1336 C, absorptivity 0.38 (four_alloy_materials.thermal_props('IN718')['absorptivity_IR'] (assumed constant, not measured)), preheat 20 C (assumption: ambient plate; the NIST plate temperature is not stated in the files in hand), layer 30 um (nominal value passed for a bare plate (no powder), as in tools/lpbf_dataset_comparison.py), hatch 100 um. NIST spot_size (D4s) passed as the kernel beam diameter: for a Gaussian beam D4s equals the 1/e^2 diameter (assumption about the kernel's beam-size convention). flat-plate absorptivity: the optional powder-bed ray tracer is pinned off (bare plate, no powder) via tools/lpbf_dataset_comparison.pin_flat_plate.

## Derivability

| Quantity | Status |
| --- | --- |
| time above DL thresholds, saturated-region length | measured-signal (NIST) |
| pixel pitch, temporal/spatial length | derived-inferred (NIST) |
| case/baseline trend and Spearman rank vs kernels | sensitivity-only |
| absolute temperature, cooling rate, time above melting | unavailable |

## Measured case means (3 repeats each; raw signal units)

| Case | P (W) | v (mm/s) | D4s (um) | lsatTemporal_um | lsatSpatial_um | tat4095_frames | tat2000_frames | tat1000_frames |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 285 | 960 | 67 | 576 +/- 0 | 603.8 +/- 11.96 | 18 +/- 0 | 25.67 +/- 0.5774 | 37 +/- 0 |
| 1.1 | 285 | 960 | 49 | 554.7 +/- 18.48 | 597.2 +/- 0.1608 | 17.33 +/- 0.5774 | 24.67 +/- 0.5774 | 33.67 +/- 0.5774 |
| 1.2 | 285 | 960 | 82 | 512 +/- 0 | 532.7 +/- 0.2097 | 16 +/- 0 | 25.67 +/- 0.5774 | 37.67 +/- 0.5774 |
| 2.1 | 285 | 1200 | 67 | 520 +/- 0 | 539.3 +/- 12.5 | 13 +/- 0 | 19.33 +/- 0.5774 | 28.33 +/- 0.5774 |
| 2.2 | 285 | 800 | 67 | 613.3 +/- 0 | 617.9 +/- 0.02975 | 23 +/- 0 | 32 +/- 0 | 45 +/- 0 |
| 3.1 | 325 | 960 | 67 | 640 +/- 0 | 660.8 +/- 0.1641 | 20 +/- 0 | 27.67 +/- 0.5774 | 39.33 +/- 0.5774 |
| 3.2 | 245 | 960 | 67 | 490.7 +/- 18.48 | 511.4 +/- 0.2327 | 15.33 +/- 0.5774 | 22 +/- 0 | 33 +/- 0 |

## Kernel liquidus length (screening, unvalidated)

| Case | rosenthal | eagar-tsai | goldak |
| --- | ---: | ---: | ---: |
| 0 | 661.9 um | 672.9 um | 663.8 um |
| 1.1 | 662.9 um | 672.5 um | 668 um |
| 1.2 | 661 um | 671 um | 657.1 um |
| 2.1 | 659.3 um | 667.7 um | 656.3 um |
| 2.2 | 664.4 um | 676.7 um | 669.3 um |
| 3.1 | 753.5 um | 764.8 um | 755.8 um |
| 3.2 | 570.2 um | 580.8 um | 571.7 um |

## Normalised trend vs case 0 (sensitivity-only)

| Case | Varied | Metric | Measured ratio +/- SD | Resolved | rosenthal ratio (sign agrees) | eagar-tsai ratio (sign agrees) | goldak ratio (sign agrees) |
| --- | --- | --- | ---: | --- | ---: | ---: | ---: |
| 1.1 | spot D4s 67 -> 49 | lsatTemporal_um | 0.963 +/- 0.03207 | no | 1.002 (no) | 0.9994 (yes) | 1.006 (no) |
| 1.1 | spot D4s 67 -> 49 | lsatSpatial_um | 0.9891 +/- 0.01959 | no | 1.002 (no) | 0.9994 (yes) | 1.006 (no) |
| 1.1 | spot D4s 67 -> 49 | tat4095_frames | 0.963 +/- 0.03207 | no | 1.002 (no) | 0.9994 (yes) | 1.006 (no) |
| 1.1 | spot D4s 67 -> 49 | tat2000_frames | 0.961 +/- 0.0312 | no | 1.002 (no) | 0.9994 (yes) | 1.006 (no) |
| 1.1 | spot D4s 67 -> 49 | tat1000_frames | 0.9099 +/- 0.0156 | yes | 1.002 (no) | 0.9994 (yes) | 1.006 (no) |
| 1.2 | spot D4s 67 -> 82 | lsatTemporal_um | 0.8889 +/- 0 | yes | 0.9986 (yes) | 0.9972 (yes) | 0.9899 (yes) |
| 1.2 | spot D4s 67 -> 82 | lsatSpatial_um | 0.8822 +/- 0.01747 | yes | 0.9986 (yes) | 0.9972 (yes) | 0.9899 (yes) |
| 1.2 | spot D4s 67 -> 82 | tat4095_frames | 0.8889 +/- 0 | yes | 0.9986 (yes) | 0.9972 (yes) | 0.9899 (yes) |
| 1.2 | spot D4s 67 -> 82 | tat2000_frames | 1 +/- 0.03181 | no | 0.9986 (no) | 0.9972 (no) | 0.9899 (no) |
| 1.2 | spot D4s 67 -> 82 | tat1000_frames | 1.018 +/- 0.0156 | no | 0.9986 (no) | 0.9972 (no) | 0.9899 (no) |
| 2.1 | speed 960 -> 1200 | lsatTemporal_um | 0.9028 +/- 0 | yes | 0.9961 (yes) | 0.9923 (yes) | 0.9887 (yes) |
| 2.1 | speed 960 -> 1200 | lsatSpatial_um | 0.8932 +/- 0.02723 | yes | 0.9961 (yes) | 0.9923 (yes) | 0.9887 (yes) |
| 2.1 | speed 960 -> 1200 | tat4095_frames | 0.7222 +/- 0 | yes | 0.7969 (yes) | 0.7938 (yes) | 0.791 (yes) |
| 2.1 | speed 960 -> 1200 | tat2000_frames | 0.7532 +/- 0.02816 | yes | 0.7969 (yes) | 0.7938 (yes) | 0.791 (yes) |
| 2.1 | speed 960 -> 1200 | tat1000_frames | 0.7658 +/- 0.0156 | yes | 0.7969 (yes) | 0.7938 (yes) | 0.791 (yes) |
| 2.2 | speed 960 -> 800 | lsatTemporal_um | 1.065 +/- 0 | yes | 1.004 (yes) | 1.006 (yes) | 1.008 (yes) |
| 2.2 | speed 960 -> 800 | lsatSpatial_um | 1.023 +/- 0.02027 | no | 1.004 (yes) | 1.006 (yes) | 1.008 (yes) |
| 2.2 | speed 960 -> 800 | tat4095_frames | 1.278 +/- 0 | yes | 1.205 (yes) | 1.207 (yes) | 1.21 (yes) |
| 2.2 | speed 960 -> 800 | tat2000_frames | 1.247 +/- 0.02804 | yes | 1.205 (yes) | 1.207 (yes) | 1.21 (yes) |
| 2.2 | speed 960 -> 800 | tat1000_frames | 1.216 +/- 0 | yes | 1.205 (yes) | 1.207 (yes) | 1.21 (yes) |
| 3.1 | power 285 -> 325 | lsatTemporal_um | 1.111 +/- 0 | yes | 1.138 (yes) | 1.137 (yes) | 1.139 (yes) |
| 3.1 | power 285 -> 325 | lsatSpatial_um | 1.094 +/- 0.02167 | yes | 1.138 (yes) | 1.137 (yes) | 1.139 (yes) |
| 3.1 | power 285 -> 325 | tat4095_frames | 1.111 +/- 0 | yes | 1.138 (yes) | 1.137 (yes) | 1.139 (yes) |
| 3.1 | power 285 -> 325 | tat2000_frames | 1.078 +/- 0.03307 | yes | 1.138 (yes) | 1.137 (yes) | 1.139 (yes) |
| 3.1 | power 285 -> 325 | tat1000_frames | 1.063 +/- 0.0156 | yes | 1.138 (yes) | 1.137 (yes) | 1.139 (yes) |
| 3.2 | power 285 -> 245 | lsatTemporal_um | 0.8519 +/- 0.03207 | yes | 0.8615 (yes) | 0.8631 (yes) | 0.8613 (yes) |
| 3.2 | power 285 -> 245 | lsatSpatial_um | 0.847 +/- 0.01678 | yes | 0.8615 (yes) | 0.8631 (yes) | 0.8613 (yes) |
| 3.2 | power 285 -> 245 | tat4095_frames | 0.8518 +/- 0.03207 | yes | 0.8615 (yes) | 0.8631 (yes) | 0.8613 (yes) |
| 3.2 | power 285 -> 245 | tat2000_frames | 0.8571 +/- 0.01928 | yes | 0.8615 (yes) | 0.8631 (yes) | 0.8613 (yes) |
| 3.2 | power 285 -> 245 | tat1000_frames | 0.8919 +/- 0 | yes | 0.8615 (yes) | 0.8631 (yes) | 0.8613 (yes) |

Resolved = |ratio - 1| exceeds both the repeat SD of the measured ratio and one measurement quantum (one frame, one frame of travel or one pixel) relative to the baseline. An SD of 0 means the three repeats gave identical integer-frame values, not zero uncertainty. Sign agreement is reported for every row; where the measured change is not resolved it carries no weight.

## Spearman rank over the 7 cases (sensitivity-only)

| Measured metric | Model quantity | rosenthal | eagar-tsai | goldak |
| --- | --- | ---: | ---: | ---: |
| lsatTemporal_um | liquidusLength_um | 0.929 | 0.964 | 0.929 |
| lsatSpatial_um | liquidusLength_um | 0.929 | 0.964 | 0.929 |
| tat4095_frames | liquidusDwell_s | 0.964 | 1 | 0.964 |
| tat2000_frames | liquidusDwell_s | 0.883 | 0.937 | 0.883 |
| tat1000_frames | liquidusDwell_s | 0.857 | 0.893 | 0.857 |

## Unavailable

| Item | Reason |
| --- | --- |
| absolute saturated length / time above threshold vs model liquidus length / dwell | the temperature of the 4095 DL saturation isotherm and of the DL thresholds is unknown (no temperature conversion), so absolute values refer to different isotherms |
| cooling rate (K/s); NIST TSCR, TLCR, PSCR | the camera signal is not converted to temperature, so no K/s exists on the measured side; signal-decay frames are not cooling rates |
| time above melting; NIST TTAM, PTAM | needs T(DL) at solidus/liquidus, i.e. the missing temperature conversion |
| peak temperature | saturated at 4095 DL in every laser-on frame and uncalibrated |
| lpbf_simulation reference transient (enthalpy) backend | not run in v1: the local-history observer is restricted to reference powder-layer runs, the 10 mm bare-plate tracks need the corridor geometry, and the 20 um mesh is about one camera pixel and not converged |
| pad thermography vs kernels | single-track analytic kernels do not represent multi-track heat accumulation; pad camera videos are not analysed in v1 (only the commanded XYPT track table is derived) |
| radiance-temperature bracket (spec Phase 2) | gated: needs a confirmed calibration equation and unit plus a cited emissivity; not implemented |

## Checks

| Check | Result | Detail |
| --- | --- | --- |
| A1-input-pins | pass | derived table size and SHA-256 equal the tool pin; manifest raw-input pins equal NERDm v1.3.1 |
| A2-physics-fingerprint | pass | test_lpbf_implementation_fingerprint.py run; recorded fingerprint read from lpbf_implementation_fingerprint.expected |
| A9-no-temperature | pass | measured and comparison blocks scanned for temperature/cooling-rate keys: 0 found (model inputs such as the liquidus are model assumptions, not DL-derived) |
| A10-labels | pass | labels equal LABELS (experimentalValidation false, modelAcceptance false, nistResidual null); every row status in ['sensitivity-only', 'unavailable'] and every unavailable row has a reason |
| A11-determinism | pass | document built twice in this run with the same --generated-at; serialised bytes compared |
| A12-runtime | pass | both builds finished within the 300 s limit; the exact wall time is printed to stdout only, so the record stays byte-deterministic |

## Limits

- Measured and model quantities refer to different isotherms: the camera saturation level and DL thresholds have unknown temperatures; the kernels report the IN718 liquidus of the repo material table.
- Measured lengths use a pixel pitch inferred from the commanded scan speed (README +/-2.5 % k=1); ratios cancel the pitch but the temporal length also carries the commanded speed.
- Kernel inputs are assumptions: absorptivity of record (not measured), ambient preheat, D4s taken as the beam diameter, flat-plate absorption; nothing was tuned to the data.
- Each case has 3 repeats; the measured ratio SD is a first-order repeat-scatter propagation, not an uncertainty budget; Spearman correlations are over 7 cases with no significance claimed.
- Single tracks on bare IN718 only; no powder-bed claim and no pad comparison.
