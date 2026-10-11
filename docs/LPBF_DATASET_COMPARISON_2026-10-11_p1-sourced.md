# LPBF dataset comparison (2026-10-11)

**Comparison of screening kernels against published single-track measurements; not experimental validation; estimated material laws; absorptivity assumed.**

Schema `lpbf-dataset-comparison-1`; implementation fingerprint `c61ab6a81912c92ce086073b0e5543fdfc3dd2740cb04458758a147abce88a32`; quick mode: False. Honesty: comparison, not validation; screening kernels; estimated material laws; absorptivity assumed (not measured); published single-track measurements, no replicate or uncertainty model; a failing comparison is reported, not fitted away. `experimentalValidation` = false.

Slim view record `LPBF_DATASET_COMPARISON_2026-10-11_p1-sourced.view.json` (this record minus `breakdowns` and `referenceTransient.rows`; sha256 of its LF bytes `147cac201907badced30dc2a9693913cdd0e1cd488aa644787deda4d1fe0cc8e`).

## Datasets

- **hofmann-316l-2026** (316L Stainless Steel): DOI 10.5281/zenodo.16979848, CC BY 4.0, 677 rows recorded, table sha256 `d4bbc7a60b536118586f44b64beb0fa20f94133f6d1a8d0fdcf726003720c3d8`. Hofmann et al., melt-pool geometry data for 316L single tracks (Aconity Midi), Zenodo 10.5281/zenodo.16979848 (v1, 2025-08-28); associated paper Materials & Design 262 (2026) 115459, doi:10.1016/j.matdes.2026.115459.
  - caveat: Measured cross-sections from micrographs; the uncertainty budget is not stated in the files read.
  - caveat: The d_laser column is the laser spot DIAMETER in mm; the diameter definition (1/e^2 or other) is not stated on the Zenodo record or in the paper (Sec. 2.1 gives a single-mode Gaussian beam, 50 um focus diameter, defocused to 80-140 um): treated as 1/e^2 by assumption.
  - caveat: Depth datum (settled from the paper, Fig. 2 and Sec. 2.2): penetration depth is measured from the original substrate surface, not from the powder surface; for t_powder > 0 a model that computes depth from the free (powder) surface is offset by the layer height above the datum (geometric assumption h_surface = phi*t, phi = 0.60 packing from Trapp 2017; powder denudation not modelled).
  - caveat: Absorptivity is not measured; the comparison uses the repo's estimated 316L absorptivity.
  - caveat: Build-plate temperature is not given: 20 C is an assumption.
  - caveat: t_powder = 0 rows are bare plate; t_powder 30/60 um are powder layers (the packing is not stated).
  - caveat: The CSV header calls the area column 'um' although the values are um^2 (width x depth scale confirms).
  - caveat: 677 rows contain repeated parameter sets (623 distinct) -- replicates are kept as separate rows.
  - caveat: Where the width/depth are taken along the track and whether the section is at steady state is not stated in the files read.
  - caveat: 316L thermophysical properties used by the models are estimated, not measured.
- **totis-ti64-2021** (Ti-6Al-4V): DOI 10.17632/s9438vb5xd.1, CC BY 4.0, 80 rows recorded, table sha256 `3b5794f3a25a5f67fa0d8d1ab006834205ef820b046c24deb15836025825d623`. Totis, Vaglio et al., single-track Ti6Al4V SEM images and geometrical data (Concept Laser M2, 50 um laser spot), Mendeley Data, 10.17632/s9438vb5xd.1 (v1, 2021-04-26); related article Data in Brief, doi:10.1016/j.dib.2020.106443.
  - caveat: Tracks were made on a 25 um powder layer over a printed Ti-6Al-4V base (not a bare plate, not a semi-infinite wrought substrate); the 50 um spot is taken as 1/e^2 from the research note.
  - caveat: The workbook does not state the depth reference line, but the associated paper does (Vaglio et al. 2020, Fig. 1 and Fig. 2(b), Sec. 1.3): depth is measured from the top of the printed base under the 25 um powder layer, height above it. A model that computes depth from the powder surface is offset by the layer height above the datum (geometric assumption h_surface = phi*t, phi = 0.60; powder denudation not modelled).
  - caveat: One track per (power, speed) cell: no replicates, no scatter estimate.
  - caveat: Absorptivity is not measured; the comparison uses the repo's estimated Ti-6Al-4V absorptivity.
  - caveat: Build-plate temperature is not given: 20 C is an assumption.
  - caveat: No balling flag in the workbook: the regime classifier uses inputs only for this dataset.
  - caveat: Width, depth and height are SEM-derived values read from the workbook sheets 'Track width (W)', 'Track depth (D)', 'Track height (H)', 'Contact angle' (microhardness sheet not used).
  - caveat: Ti-6Al-4V thermophysical properties used by the models are estimated, not measured.
- **cmu-ti64-st-2026** (Ti-6Al-4V): DOI 10.1184/R1/25696293.v1, CC BY 4.0, 216 rows recorded, table sha256 `7f415afb20cd8e1698efcbc4948654ed4b95bb4fc1854b5c1e7f45e9874a1f90`. CMU KiltHub, Ti-6Al-4V melt-pool variability, 10.1184/R1/25696293.v1.
  - caveat: ST source table has no power column; beam diameter is also unreported. No solver prediction is made.
- **cmu-ti64-mt-2026** (Ti-6Al-4V): DOI 10.1184/R1/25696293.v1, CC BY 4.0, 410 rows recorded, table sha256 `d8d318fd673c69ad250a9d44cc7b37b71d3706cde7ad93539049454aedf09c57`. CMU KiltHub, Ti-6Al-4V melt-pool variability, 10.1184/R1/25696293.v1.
  - caveat: Beam diameter, layer, preheat and absorptivity are unreported; no solver prediction is made.
- **ku-leuven-in718-2021** (Inconel 718): DOI 10.6084/m9.figshare.15035706.v1, CC0, 48 rows recorded, table sha256 `d8731ecc5cd027e697e4fbd7f9dabb634c197f0325f4282eb3c86ce9ff9d512b`. KU Leuven IN718 melt-pool measurements, Figshare, 10.6084/m9.figshare.15035706.v1.
  - caveat: Source CSV does not state units for w exp/d exp; article describes half-width, so dimensions are retained as source values and excluded from numeric comparison until resolved.
  - caveat: 48 numbered conditions; 38 contain both dimensions and 10 have missing dimensions.
  - caveat: Condition means, not individual cross-sections; source sample counts vary.
  - caveat: Paper reports 37.5 um spot and 60 um powder layer; preheat and measured absorptivity are not reported.
- **ku-leuven-316l-2021** (316L Stainless Steel): DOI 10.6084/m9.figshare.15035733.v1 + 10.6084/m9.figshare.15035703.v1, CC0, 44 rows recorded, table sha256 `e031aead71bf64c70a35ae05d64c0c576d33c2ae757a1e5bda68b5da532ac831`. V. Coen (KU Leuven), melt-pool measurement CSVs for 316L and Ti-6Al-4V, Figshare (CC0, 2021-07-22): 316L 10.6084/m9.figshare.15035733.v1 (raw) and 15035703.v1 (processed); Ti-6Al-4V 15035709.v1 (raw) and 15035712.v2 (processed). Manuscript: V. Coen, L. Goossens, B. Van Hooreweder, 'Methodology and experimental validation of analytical melt pool models for laser powder bed fusion', J. Mater. Process. Technol. 304 (2022) 117547, doi:10.1016/j.jmatprotec.2022.117547 (article not read: publisher returned HTTP 403).
  - caveat: Only the measured 'w exp', 'd exp', 'R exp' columns and the authors' 'melting regime' label are read from the processed '(2)' files; their 'model' and 'error' columns (analytical-model outputs) are excluded by name.
  - caveat: Units: the raw '(1)' files tag every section row with 'um' (micrometre sign); the processed '(2)' files carry no units. 316L 'w exp'/'d exp' equal the arithmetic means of the raw sections; Ti-6Al-4V values differ from the raw means by a few um (see raw_mean_* columns), so the processing step is not fully reproduced here.
  - caveat: Width operator: 'Width' in the raw files; the authors' R = d/w with keyhole for R > 1 implies full width (inference, the article was not read).
  - caveat: Regime labels are the authors' published labels ('melting regime' column), kept verbatim; they are not a strict function of R exp and are not the repo's screening classifier.
  - caveat: Beam diameter unverified: 37.5 um carried from the 2026-10-05 KU Leuven IN718 record ('Paper reports 37.5 um spot'); the article (doi:10.1016/j.jmatprotec.2022.117547) could not be read (HTTP 403), so diameter vs radius and the beam-size definition are not confirmed.
  - caveat: Powder layer not stated in the files read; the 2026-10-05 KU Leuven IN718 record cites a 60 um powder layer from the Coen article, which could not be read here (HTTP 403), so it is not carried over to these rows (the kernels ignore layer thickness, so there is no numeric effect). Preheat and absorptivity are not stated in the files read; 20 C preheat is an assumption.
  - caveat: Conditions blank in the processed file (316L 600 W at 400/500/1000/1100 mm/s) carry no exp value and are not compared, although the raw file has partial sections for some of them.
  - caveat: Condition means: per-condition section count is taken from the raw file (raw_sections_n); the trailing 'nb. of samples' column of the processed file belongs to its regime-summary block and is not used.
  - caveat: not compared: ku-leuven-316l-2021-41 (w exp / d exp blank in the processed source file)
  - caveat: not compared: ku-leuven-316l-2021-42 (w exp / d exp blank in the processed source file)
  - caveat: not compared: ku-leuven-316l-2021-47 (w exp / d exp blank in the processed source file)
  - caveat: not compared: ku-leuven-316l-2021-48 (w exp / d exp blank in the processed source file)
- **ku-leuven-ti64-2021** (Ti-6Al-4V): DOI 10.6084/m9.figshare.15035709.v1 + 10.6084/m9.figshare.15035712.v2, CC0, 14 rows recorded, table sha256 `e031aead71bf64c70a35ae05d64c0c576d33c2ae757a1e5bda68b5da532ac831`. V. Coen (KU Leuven), melt-pool measurement CSVs for 316L and Ti-6Al-4V, Figshare (CC0, 2021-07-22): 316L 10.6084/m9.figshare.15035733.v1 (raw) and 15035703.v1 (processed); Ti-6Al-4V 15035709.v1 (raw) and 15035712.v2 (processed). Manuscript: V. Coen, L. Goossens, B. Van Hooreweder, 'Methodology and experimental validation of analytical melt pool models for laser powder bed fusion', J. Mater. Process. Technol. 304 (2022) 117547, doi:10.1016/j.jmatprotec.2022.117547 (article not read: publisher returned HTTP 403).
  - caveat: Only the measured 'w exp', 'd exp', 'R exp' columns and the authors' 'melting regime' label are read from the processed '(2)' files; their 'model' and 'error' columns (analytical-model outputs) are excluded by name.
  - caveat: Units: the raw '(1)' files tag every section row with 'um' (micrometre sign); the processed '(2)' files carry no units. 316L 'w exp'/'d exp' equal the arithmetic means of the raw sections; Ti-6Al-4V values differ from the raw means by a few um (see raw_mean_* columns), so the processing step is not fully reproduced here.
  - caveat: Width operator: 'Width' in the raw files; the authors' R = d/w with keyhole for R > 1 implies full width (inference, the article was not read).
  - caveat: Regime labels are the authors' published labels ('melting regime' column), kept verbatim; they are not a strict function of R exp and are not the repo's screening classifier.
  - caveat: Beam diameter unverified: 37.5 um carried from the 2026-10-05 KU Leuven IN718 record ('Paper reports 37.5 um spot'); the article (doi:10.1016/j.jmatprotec.2022.117547) could not be read (HTTP 403), so diameter vs radius and the beam-size definition are not confirmed.
  - caveat: Powder layer not stated in the files read; the 2026-10-05 KU Leuven IN718 record cites a 60 um powder layer from the Coen article, which could not be read here (HTTP 403), so it is not carried over to these rows (the kernels ignore layer thickness, so there is no numeric effect). Preheat and absorptivity are not stated in the files read; 20 C preheat is an assumption.
  - caveat: Conditions blank in the processed file (316L 600 W at 400/500/1000/1100 mm/s) carry no exp value and are not compared, although the raw file has partial sections for some of them.
  - caveat: Condition means: per-condition section count is taken from the raw file (raw_sections_n); the trailing 'nb. of samples' column of the processed file belongs to its regime-summary block and is not used.
- **lane-in625-2020** (Inconel 625): DOI 10.1007/s40192-020-00169-1, not stated as a licence: PMC author manuscript (NIHMS1686029), PMC permissions text 'available for text mining ... fair use'; NIST-authored; numeric table values transcribed with citation, 23 rows recorded, table sha256 `32fe10fb8606a49cdc59e1e3753b40e6be9ea9751dae9ec8ac95c217e6d16179`. B. Lane et al., 'Measurements of melt pool geometry and cooling rates of individual laser traces on IN625 bare plates', Integr. Mater. Manuf. Innov. 9(1) (2020), doi:10.1007/s40192-020-00169-1, PMC8194244, Tables 3 and 4 (AM-Bench AMB2018-02).
  - caveat: Width and depth are Table 3 'Cross Section (um)' track means (N = 3 microscopy measurements per track, sigma = spread, not an uncertainty); the first Cross Section column is width, the second depth (their CBM means reproduce Table 4 Class Width/Depth).
  - caveat: Bare IN625 plate, no powder; preheat not stated (20 C assumed). Spot sizes are D4sigma diameters (CBM 100 um, AMMT 170 um, Table 1); for a Gaussian beam D4sigma equals the 1/e^2 diameter the kernels take.
  - caveat: AMMT power: Fig. 2 caption: 'Laser power values indicated are the applied laser power'; Table 3 lists 137.9/179.2 W for the AMMT cases and the Section 2 case definitions give 150/195 W. Whether these are applied vs commanded powers is not stated explicitly, and the Fig. 2 image was not read. Status: UNRESOLVED. Kernel inputs use the Table 3 values; a nominal-power sensitivity is reported separately.
  - caveat: AMMT cooling rates: Table 3 footnote c says they 'should not be used' (motion blur / calibration range); they are stored flagged do-not-use. AMMT 1290-1000 C cooling rates are blank (footnote b). AMMT-100us case C emittance 0.519 is assumed (footnote a). The conclusions call all cooling rates exemplar, not reference data.
  - caveat: AMMT-100us and AMMT-20us tracks are different physical tracks made under nominally the same conditions (paper Fig. 7); CBM case A is described as near or at keyholing.
  - caveat: IN625 kernel properties come from lpbf_thermal_solver.SECONDARY_THERMOPHYSICAL_DB (provenance class 'legacy-estimated-secondary', absorptivity_IR 0.38 estimated), not from a measured property set.

## Regime screening rule

Screening classifier, not the papers' regime definition. Inputs: normalised enthalpy dH/h_s = eta*P / (rho*cp_s*max(50, T_liq-T0)*sqrt(pi*alpha_s*v*r^3)) (same form as lpbf_thermal_solver.py, flat-plate absorptivity_IR of the material authority, solid k/cp, r = d/2) and the dataset's own balling flag. balling == 1 -> 'balling-flagged' (Hofmann only); otherwise dH/h_s < 15 -> 'conduction', 15 <= dH/h_s < 20 -> 'transition', >= 20 -> 'keyhole'; Inconel 625: dH/h_s < 13.6 -> 'conduction', >= 13.6 -> 'keyhole', no transition band (derivation: lpbf_thermal_solver.REGIME_THRESHOLD_BASIS). Measured D/W is recorded next to the label but not used for it. Wave 2 rows (KU Leuven 316L/Ti-6Al-4V, Lane IN625) are classified by the same screening rule; the KU Leuven authors' own labels are kept verbatim in regime.publishedLabel and are not used for the statistics' regime split. Added datasets without a reported beam diameter (CMU) or with unresolved measured dimension units/operator (KU Leuven IN718 (ku-leuven-in718-2021)) are labeled unclassified and excluded from kernel predictions; no regime label is inferred for them.

Row counts per regime: all 1431, balling-flagged 216, conduction 141, keyhole 315, transition 85, unclassified-missing-process-input 626, unclassified-source-dimensions-unresolved 48

## Assumptions

- **hatch_um**: 100 (no dataset in this record has a hatch: single tracks; the hatch only enters the lack-of-fusion screen, not the width/depth/length extents)
- **layer_um**: t_powder 0 (bare plate) rows are passed with a nominal 30 um layer because the function requires a positive layer; width/depth/length do not depend on it (checked at 10/30/60 um)
- **preheat_C**: 20 C assumed for every dataset (no dataset in this record states a build-plate or substrate temperature in the files read)
- **absorptivity**: the repo's estimated absorptivity_IR (316L 0.42, Ti-6Al-4V 0.35; IN625 0.38 from the legacy-estimated secondary table, wave 2 Lane rows only), flat-plate
- **inclusionRule**: a row counts for statistics only when extentStatus == 'computed'
- **powderBedRayTracer**: calculate_meltpool_physics runs the optional GPU powder ray tracer only when absorption_model='powder-raytrace' is requested (tier-2 bump 2026-10-06); the default and this harness use the flat-plate absorptivity, so the ray tracer was not used; see `absorption`
- **wave2**: KU Leuven rows: beam diameter unverified: 37.5 um carried from the 2026-10-05 KU Leuven IN718 record ('Paper reports 37.5 um spot'); the article (doi:10.1016/j.jmatprotec.2022.117547) could not be read (HTTP 403), so diameter vs radius and the beam-size definition are not confirmed; layer left unset (not stated in the files read; the 2026-10-05 KU Leuven IN718 record cites a 60 um powder layer from the Coen article, which could not be read here (HTTP 403), so it is not carried over to these rows; kernels ignore it); 20 C preheat assumed. Lane rows: bare plate (layer 0, passed as the nominal layer), Table 3 power, D4sigma spot as the 1/e^2 diameter, 20 C preheat assumed, IN625 properties from the solver's legacy-estimated secondary table. No kernel parameter was changed for these rows; sensitivities are reported separately.
- **addedDatasetTreatment**: CMU ST has no power field; all CMU rows lack beam diameter. KU Leuven IN718 (ku-leuven-in718-2021) source dimensions retain unresolved units and width operator. These rows have no numeric regime classification or kernel predictions and are excluded from MAPE/statistics; source observations remain in rows with explicit extentStatus reasons. This applies to the IN718 file only: the wave 2 KU Leuven 316L/Ti-6Al-4V units were resolved from their raw '(1)' files (see the wave 2 catalog notes); the same raw-file check was not applied to the IN718 file in this record.

## Absorption path

Path: **flat-plate** (pinned: True). calculate_meltpool_physics(absorption_model='flat-plate'), the solver default on every machine since the 2026-10-06 tier-2 bump; sys.modules['powder_bed_raytracer'] = None is also set in the main process and in every worker so any ray-tracer import fails loudly.

Ray-tracer module present: True; importable in a separate probe process: False. Absorptivity by material: 316L 0.42, Ti-6Al-4V 0.35, Inconel 625 0.38. Flat-plate calls: 4206 of 4206 solver calls (by kernel, main run: rosenthal 838, eagar-tsai 838, goldak 838).

flat-plate absorptivity_IR; the GPU powder ray tracer was not used; with it the predictions change (reviewer stub: Eagar-Tsai hofmann-0001 171.0/119.6 -> 209.2/143.6 um at effective 0.65). flatPlateCalls counts the solver results that report processParameters.absorptionModel == 'flat-plate'; equal to solverCalls when every call took the flat-plate path (failed calls report none).

## Limits

- Kernels are compared on different included subsets (rows with extentStatus == 'computed'): pooled n = rosenthal 754 of 1431, eagar-tsai 757 of 1431, goldak 753 of 1431. Only summary.<kernel>.common (n = 753, the rows where all kernels are computed) is a like-for-like comparison; pooled and per-regime figures of different kernels are not.
- Rosenthal conduction statistics rest on 138 of 141 conduction rows: they are selected by the kernel's own output (only rows where Rosenthal resolves an extent without heuristic fallback, search-box limitation or the 0.55 x beam-diameter width floor are 'computed'), so they describe the rows it can resolve, not the regime.
- Eagar-Tsai and Goldak keyhole-regime depth statistics are near-identical (bias -4.0 / -3.0 %, MAPE 26.6 / 26.2 %) because both add the same Fabbro keyhole depth term; they are not independent evidence.
- The measurements carry no uncertainty model: the pooled-summary datasets (Hofmann 316L, Totis Ti-6Al-4V) provide no per-row measurement uncertainty; the wave 2 Lane IN625 rows carry Table 3 per-track sigma (measured.widthSigma_um / depthSigma_um, the spread of N = 3 microscopy measurements, not an uncertainty) and the statistics do not use it. The bootstrap intervals cover resampling of parameter sets only, not measurement error, the estimated material laws or the assumed absorptivity.
- Replicate rows are not independent: the Hofmann table has 677 rows but only 623 distinct parameter sets; the bootstrap intervals resample whole parameter sets (clusters), the point statistics weight every row.
- Balling-flagged rows (216) are inside the pooled 'all' headline statistics; a continuous-track screening kernel is not meant to describe them.
- The Totis depth datum is the top of the printed base under the 25 um powder layer (Vaglio et al. 2020, Fig. 1/2b; the workbook does not state it) and the Hofmann datum is the substrate surface (Fig. 2); the kernels compute depth from the free surface, so the 80 Totis and the Hofmann powder-layer depths carry an offset, reported as the declared sensitivity column `sensitivity.depthDatumCorrection_um` = phi*t with phi = 0.6 (geometric assumption (h_surface = φ·t); powder denudation not modelled), never applied to the served depth.
- The kernels ignore powder-layer thickness (identical predictions at 0/30/60 um; see assumptions.layer_um), so any trend with powder-layer thickness is in the measurements only.
- Absorption path: flat-plate absorptivity_IR (316L 0.42, Ti-6Al-4V 0.35, Inconel 625 0.38); the GPU powder ray tracer was not used; with the ray tracer the predictions change.
- The reference-transient block depends on wall-clock budgets (total and per case): on a slower host rows can become 'not-run (budget)'. --reuse-reference copies the block of an earlier record instead.
- KU Leuven 316L/Ti-6Al-4V (58 condition means): the beam diameter is unverified: 37.5 um carried from the 2026-10-05 KU Leuven IN718 record ('Paper reports 37.5 um spot'); the article (doi:10.1016/j.jmatprotec.2022.117547) could not be read (HTTP 403), so diameter vs radius and the beam-size definition are not confirmed; the 75 um re-run in wave2.kuBeamDiameterSensitivity shows how much the statistics move with it. Rows are condition means of 7 to 16 sections; the bootstrap resamples conditions, not sections.
- Lane IN625 (23 tracks): AMMT kernel inputs use the Table 3 power (137.9/179.2 W). Fig. 2 caption: 'Laser power values indicated are the applied laser power'; Table 3 lists 137.9/179.2 W for the AMMT cases and the Section 2 case definitions give 150/195 W. Whether these are applied vs commanded powers is not stated explicitly, and the Fig. 2 image was not read. Status: UNRESOLVED. See wave2.laneNominalPowerSensitivity. IN625 properties are legacy estimates (absorptivity_IR 0.38).
- Wave 2 reference targets (NIST AMB2022-03 thermal Tables 2-3, Simonds 2018 Table III) have no like-for-like model comparison in the app; their comparison status is 'unavailable' with the reason recorded.
- The pooled summary, its limits above and the absorptivity sensitivity exclude the 81 wave 2 rows (KU Leuven 316L/Ti-6Al-4V, Lane IN625; see summaryScope), so the pooled headline keeps the 2026-10-05 scope and is comparable to it. Per-dataset wave 2 figures are in wave2.scorecard; they are not pooled across materials.

## Depth-datum sensitivity column (declared; not applied to the served depth)

`rows[].sensitivity.depthDatumCorrection_um` = phi*t with phi = 0.6 (Trapp 2017) on 547 powder-layer rows of sources whose measured depth starts at the substrate; geometric assumption (h_surface = φ·t); powder denudation not modelled. It is reported alongside the served `predictions` and never replaces them.

- hofmann-316l-2026: 232 rows, correction 18 um
- hofmann-316l-2026: 235 rows, correction 36 um
- totis-ti64-2021: 80 rows, correction 15 um

## Summary: kernel x regime (2026-10-05 dataset scope pooled; wave 2 rows excluded, see the wave 2 scorecard)

summary, limits and absorptivitySensitivity cover the 2026-10-05 dataset scope only, so the pooled headline is comparable to the 2026-10-05 record; wave 2 rows are scored per dataset in wave2.scorecard because their inputs include unverified (KU Leuven beam diameter) or legacy-estimated (IN625 properties) values. Pooled rows: 1431; excluded wave 2 rows: 81.

Bias = mean((pred-meas)/meas); rows with extentStatus other than `computed` are excluded and counted. Fractions: share of rows within +-30 % of the measurement / within the x0.5-2 band.

### Pooled (the `common` regime = rows where all kernels are computed)

| kernel | regime | n | excluded | W bias % | W MAPE % | W RMSE um | W within +-30% / x0.5-2 | D bias % | D MAPE % | D RMSE um | D within +-30% / x0.5-2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rosenthal | all | 754 | 677 | -11.0 | 16.1 | 32.6 | 86% / 100% | +22.8 | 40.7 | 54.2 | 58% / 90% |
| rosenthal | balling-flagged | 216 | 0 | -10.4 | 16.4 | 34.4 | 89% / 100% | +49.4 | 57.5 | 47.2 | 51% / 82% |
| rosenthal | conduction | 138 | 3 | -24.5 | 25.1 | 42.7 | 58% / 99% | +51.2 | 54.9 | 19.2 | 42% / 86% |
| rosenthal | keyhole | 315 | 0 | -4.4 | 12.0 | 25.9 | 95% / 100% | -3.4 | 26.3 | 71.6 | 66% / 97% |
| rosenthal | transition | 85 | 0 | -14.7 | 16.0 | 31.4 | 91% / 99% | +6.0 | 28.5 | 27.5 | 67% / 93% |
| rosenthal | unclassified-missing-process-input | 0 | 626 | - | - | - | - | - | - | - | - |
| rosenthal | unclassified-source-dimensions-unresolved | 0 | 48 | - | - | - | - | - | - | - | - |
| rosenthal | common | 753 | 678 | -11.0 | 16.1 | 32.6 | 86% / 100% | +22.8 | 40.8 | 54.2 | 57% / 90% |
| eagar-tsai | all | 757 | 674 | -4.0 | 11.6 | 24.3 | 95% / 100% | +17.5 | 36.8 | 53.9 | 61% / 91% |
| eagar-tsai | balling-flagged | 216 | 0 | -4.1 | 12.8 | 27.3 | 94% / 100% | +44.1 | 53.8 | 46.8 | 54% / 83% |
| eagar-tsai | conduction | 141 | 0 | -7.5 | 11.9 | 22.4 | 95% / 100% | +34.9 | 39.5 | 15.7 | 61% / 88% |
| eagar-tsai | keyhole | 315 | 0 | -1.3 | 10.6 | 23.3 | 95% / 100% | -4.0 | 26.6 | 71.8 | 65% / 97% |
| eagar-tsai | transition | 85 | 0 | -8.2 | 11.8 | 23.2 | 94% / 100% | +0.6 | 27.4 | 28.2 | 66% / 93% |
| eagar-tsai | unclassified-missing-process-input | 0 | 626 | - | - | - | - | - | - | - | - |
| eagar-tsai | unclassified-source-dimensions-unresolved | 0 | 48 | - | - | - | - | - | - | - | - |
| eagar-tsai | common | 753 | 678 | -4.0 | 11.6 | 24.4 | 95% / 100% | +17.5 | 36.9 | 54.1 | 61% / 91% |
| goldak | all | 753 | 678 | -10.9 | 16.1 | 32.7 | 86% / 100% | +24.9 | 42.1 | 54.3 | 56% / 90% |
| goldak | balling-flagged | 216 | 0 | -10.5 | 16.4 | 34.6 | 89% / 100% | +51.6 | 59.0 | 47.4 | 50% / 81% |
| goldak | conduction | 137 | 4 | -24.6 | 25.2 | 43.1 | 58% / 99% | +56.5 | 59.9 | 20.7 | 35% / 84% |
| goldak | keyhole | 315 | 0 | -4.3 | 11.9 | 25.8 | 95% / 100% | -3.0 | 26.2 | 71.5 | 67% / 97% |
| goldak | transition | 85 | 0 | -14.5 | 15.9 | 31.3 | 91% / 99% | +9.2 | 29.6 | 27.2 | 66% / 93% |
| goldak | unclassified-missing-process-input | 0 | 626 | - | - | - | - | - | - | - | - |
| goldak | unclassified-source-dimensions-unresolved | 0 | 48 | - | - | - | - | - | - | - | - |
| goldak | common | 753 | 678 | -10.9 | 16.1 | 32.7 | 86% / 100% | +24.9 | 42.1 | 54.3 | 56% / 90% |

### Cluster-bootstrap 95 % intervals (pooled summary cells)

Distinct parameter sets (dataset, power, speed, beam diameter, layer) resampled with replacement, 1000 replicates, `random.Random(0)`, percentile 2.5/97.5; replicates of one set stay together. The intervals cover this resampling only (no measurement uncertainty, no material-law uncertainty); they are in JSON `summary.<kernel>.<regime>.<width|depth>.{bias_pct_ci95, mape_pct_ci95, n_parameterSets}`.

| kernel | regime | n | parameter sets | W bias % CI95 | W MAPE % CI95 | D bias % CI95 | D MAPE % CI95 |
|---|---|---|---|---|---|---|---|
| rosenthal | all | 754 | 700 | [-12.2, -9.9] | [15.3, 16.9] | [18.4, 27.3] | [37.1, 44.6] |
| rosenthal | balling-flagged | 216 | 215 | [-12.8, -8.3] | [14.9, 17.8] | [39.0, 61.5] | [47.7, 68.6] |
| rosenthal | conduction | 138 | 125 | [-26.7, -22.4] | [23.2, 27.0] | [40.9, 61.5] | [45.0, 64.6] |
| rosenthal | keyhole | 315 | 295 | [-6.1, -3.0] | [11.1, 12.9] | [-6.9, 0.2] | [24.0, 28.8] |
| rosenthal | transition | 85 | 75 | [-17.4, -12.1] | [13.8, 18.4] | [-2.6, 14.7] | [22.4, 35.1] |
| rosenthal | common | 753 | 699 | [-12.2, -9.8] | [15.3, 16.9] | [18.3, 27.3] | [37.1, 44.7] |
| eagar-tsai | all | 757 | 703 | [-5.0, -3.0] | [10.9, 12.3] | [13.2, 21.9] | [33.2, 40.8] |
| eagar-tsai | balling-flagged | 216 | 215 | [-6.2, -2.1] | [11.5, 14.2] | [33.8, 55.5] | [44.3, 64.5] |
| eagar-tsai | conduction | 141 | 128 | [-9.5, -5.5] | [10.5, 13.2] | [26.2, 44.1] | [31.4, 47.8] |
| eagar-tsai | keyhole | 315 | 295 | [-2.9, 0.2] | [9.7, 11.5] | [-7.6, -0.3] | [24.2, 29.0] |
| eagar-tsai | transition | 85 | 75 | [-11.0, -5.5] | [9.9, 13.8] | [-7.6, 9.0] | [21.6, 33.6] |
| eagar-tsai | common | 753 | 699 | [-5.0, -3.0] | [11.0, 12.3] | [13.3, 21.8] | [33.5, 40.5] |
| goldak | all | 753 | 699 | [-12.2, -9.8] | [15.3, 16.9] | [20.4, 29.5] | [38.4, 46.2] |
| goldak | balling-flagged | 216 | 215 | [-12.8, -8.3] | [15.0, 17.9] | [41.2, 63.5] | [49.1, 70.3] |
| goldak | conduction | 137 | 124 | [-26.9, -22.5] | [23.2, 27.3] | [45.9, 67.4] | [49.8, 70.4] |
| goldak | keyhole | 315 | 295 | [-5.9, -2.8] | [11.0, 12.9] | [-6.5, 0.6] | [23.9, 28.6] |
| goldak | transition | 85 | 75 | [-17.3, -11.8] | [13.8, 18.4] | [0.4, 18.2] | [23.4, 36.3] |
| goldak | common | 753 | 699 | [-12.2, -9.8] | [15.3, 16.9] | [20.4, 29.5] | [38.4, 46.2] |

### Dataset cmu-ti64-mt-2026

| kernel | regime | n | excluded | W bias % | W MAPE % | W RMSE um | W within +-30% / x0.5-2 | D bias % | D MAPE % | D RMSE um | D within +-30% / x0.5-2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rosenthal | all | 0 | 410 | - | - | - | - | - | - | - | - |
| rosenthal | unclassified-missing-process-input | 0 | 410 | - | - | - | - | - | - | - | - |
| eagar-tsai | all | 0 | 410 | - | - | - | - | - | - | - | - |
| eagar-tsai | unclassified-missing-process-input | 0 | 410 | - | - | - | - | - | - | - | - |
| goldak | all | 0 | 410 | - | - | - | - | - | - | - | - |
| goldak | unclassified-missing-process-input | 0 | 410 | - | - | - | - | - | - | - | - |

### Dataset cmu-ti64-st-2026

| kernel | regime | n | excluded | W bias % | W MAPE % | W RMSE um | W within +-30% / x0.5-2 | D bias % | D MAPE % | D RMSE um | D within +-30% / x0.5-2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rosenthal | all | 0 | 216 | - | - | - | - | - | - | - | - |
| rosenthal | unclassified-missing-process-input | 0 | 216 | - | - | - | - | - | - | - | - |
| eagar-tsai | all | 0 | 216 | - | - | - | - | - | - | - | - |
| eagar-tsai | unclassified-missing-process-input | 0 | 216 | - | - | - | - | - | - | - | - |
| goldak | all | 0 | 216 | - | - | - | - | - | - | - | - |
| goldak | unclassified-missing-process-input | 0 | 216 | - | - | - | - | - | - | - | - |

### Dataset hofmann-316l-2026

| kernel | regime | n | excluded | W bias % | W MAPE % | W RMSE um | W within +-30% / x0.5-2 | D bias % | D MAPE % | D RMSE um | D within +-30% / x0.5-2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rosenthal | all | 674 | 3 | -11.5 | 15.6 | 33.0 | 87% / 100% | +25.9 | 41.0 | 46.8 | 58% / 90% |
| rosenthal | balling-flagged | 216 | 0 | -10.4 | 16.4 | 34.4 | 89% / 100% | +49.4 | 57.5 | 47.2 | 51% / 82% |
| rosenthal | conduction | 130 | 3 | -23.9 | 24.5 | 43.5 | 61% / 99% | +47.6 | 49.6 | 18.7 | 44% / 89% |
| rosenthal | keyhole | 249 | 0 | -5.4 | 10.5 | 25.2 | 98% / 100% | -0.4 | 26.2 | 59.7 | 69% / 97% |
| rosenthal | transition | 79 | 0 | -13.0 | 14.4 | 30.7 | 95% / 100% | +8.9 | 28.1 | 28.1 | 68% / 94% |
| eagar-tsai | all | 677 | 0 | -4.2 | 10.7 | 24.0 | 97% / 100% | +20.4 | 36.9 | 46.5 | 62% / 91% |
| eagar-tsai | balling-flagged | 216 | 0 | -4.1 | 12.8 | 27.3 | 94% / 100% | +44.1 | 53.8 | 46.8 | 54% / 83% |
| eagar-tsai | conduction | 133 | 0 | -7.1 | 11.2 | 22.6 | 96% / 100% | +32.2 | 35.0 | 14.8 | 64% / 92% |
| eagar-tsai | keyhole | 249 | 0 | -2.1 | 8.9 | 21.9 | 98% / 100% | -1.1 | 26.4 | 60.0 | 67% / 96% |
| eagar-tsai | transition | 79 | 0 | -6.5 | 10.4 | 22.4 | 97% / 100% | +3.5 | 26.7 | 28.7 | 67% / 94% |
| goldak | all | 673 | 4 | -11.4 | 15.5 | 33.1 | 88% / 100% | +28.1 | 42.5 | 46.9 | 57% / 89% |
| goldak | balling-flagged | 216 | 0 | -10.5 | 16.4 | 34.6 | 89% / 100% | +51.6 | 59.0 | 47.4 | 50% / 81% |
| goldak | conduction | 129 | 4 | -24.0 | 24.6 | 43.9 | 61% / 98% | +52.9 | 54.5 | 20.4 | 37% / 88% |
| goldak | keyhole | 249 | 0 | -5.2 | 10.4 | 25.1 | 98% / 100% | +0.1 | 26.1 | 59.5 | 69% / 97% |
| goldak | transition | 79 | 0 | -12.8 | 14.3 | 30.6 | 95% / 100% | +12.2 | 29.6 | 27.8 | 67% / 94% |

### Dataset ku-leuven-316l-2021

| kernel | regime | n | excluded | W bias % | W MAPE % | W RMSE um | W within +-30% / x0.5-2 | D bias % | D MAPE % | D RMSE um | D within +-30% / x0.5-2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rosenthal | all | 44 | 0 | +10.9 | 16.1 | 29.9 | 82% / 100% | -12.9 | 29.0 | 158.4 | 43% / 100% |
| rosenthal | keyhole | 44 | 0 | +10.9 | 16.1 | 29.9 | 82% / 100% | -12.9 | 29.0 | 158.4 | 43% / 100% |
| eagar-tsai | all | 44 | 0 | +12.2 | 16.7 | 30.4 | 80% / 100% | -12.9 | 29.0 | 158.4 | 43% / 100% |
| eagar-tsai | keyhole | 44 | 0 | +12.2 | 16.7 | 30.4 | 80% / 100% | -12.9 | 29.0 | 158.4 | 43% / 100% |
| goldak | all | 44 | 0 | +11.0 | 16.1 | 29.9 | 82% / 100% | -12.9 | 29.0 | 158.4 | 43% / 100% |
| goldak | keyhole | 44 | 0 | +11.0 | 16.1 | 29.9 | 82% / 100% | -12.9 | 29.0 | 158.4 | 43% / 100% |

### Dataset ku-leuven-in718-2021

| kernel | regime | n | excluded | W bias % | W MAPE % | W RMSE um | W within +-30% / x0.5-2 | D bias % | D MAPE % | D RMSE um | D within +-30% / x0.5-2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rosenthal | all | 0 | 48 | - | - | - | - | - | - | - | - |
| rosenthal | unclassified-source-dimensions-unresolved | 0 | 48 | - | - | - | - | - | - | - | - |
| eagar-tsai | all | 0 | 48 | - | - | - | - | - | - | - | - |
| eagar-tsai | unclassified-source-dimensions-unresolved | 0 | 48 | - | - | - | - | - | - | - | - |
| goldak | all | 0 | 48 | - | - | - | - | - | - | - | - |
| goldak | unclassified-source-dimensions-unresolved | 0 | 48 | - | - | - | - | - | - | - | - |

### Dataset ku-leuven-ti64-2021

| kernel | regime | n | excluded | W bias % | W MAPE % | W RMSE um | W within +-30% / x0.5-2 | D bias % | D MAPE % | D RMSE um | D within +-30% / x0.5-2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rosenthal | all | 14 | 0 | -10.7 | 11.1 | 11.2 | 100% / 100% | +21.2 | 28.6 | 22.2 | 57% / 100% |
| rosenthal | keyhole | 14 | 0 | -10.7 | 11.1 | 11.2 | 100% / 100% | +21.2 | 28.6 | 22.2 | 57% / 100% |
| eagar-tsai | all | 14 | 0 | -7.8 | 8.4 | 9.1 | 100% / 100% | +21.2 | 28.6 | 22.2 | 57% / 100% |
| eagar-tsai | keyhole | 14 | 0 | -7.8 | 8.4 | 9.1 | 100% / 100% | +21.2 | 28.6 | 22.2 | 57% / 100% |
| goldak | all | 14 | 0 | -10.6 | 11.0 | 11.1 | 100% / 100% | +21.2 | 28.6 | 22.2 | 57% / 100% |
| goldak | keyhole | 14 | 0 | -10.6 | 11.0 | 11.1 | 100% / 100% | +21.2 | 28.6 | 22.2 | 57% / 100% |

### Dataset lane-in625-2020

| kernel | regime | n | excluded | W bias % | W MAPE % | W RMSE um | W within +-30% / x0.5-2 | D bias % | D MAPE % | D RMSE um | D within +-30% / x0.5-2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rosenthal | all | 18 | 5 | -15.0 | 15.0 | 23.0 | 100% / 100% | -3.8 | 39.8 | 40.8 | 22% / 89% |
| rosenthal | conduction | 8 | 5 | -16.3 | 16.3 | 23.0 | 100% / 100% | +40.4 | 40.4 | 16.0 | 0% / 100% |
| rosenthal | keyhole | 10 | 0 | -14.0 | 14.0 | 23.0 | 100% / 100% | -39.3 | 39.3 | 52.8 | 40% / 80% |
| eagar-tsai | all | 23 | 0 | +15.3 | 20.1 | 27.0 | 78% / 100% | -14.2 | 25.2 | 37.2 | 57% / 87% |
| eagar-tsai | conduction | 13 | 0 | +26.6 | 26.6 | 32.8 | 62% / 100% | +9.3 | 10.1 | 5.3 | 100% / 100% |
| eagar-tsai | keyhole | 10 | 0 | +0.6 | 11.5 | 16.7 | 100% / 100% | -44.8 | 44.8 | 56.1 | 0% / 70% |
| goldak | all | 18 | 5 | -16.1 | 16.1 | 24.3 | 100% / 100% | -2.0 | 39.1 | 39.7 | 22% / 89% |
| goldak | conduction | 8 | 5 | -18.7 | 18.7 | 26.0 | 100% / 100% | +41.8 | 41.8 | 16.7 | 0% / 100% |
| goldak | keyhole | 10 | 0 | -14.0 | 14.0 | 22.9 | 100% / 100% | -37.0 | 37.0 | 51.1 | 40% / 80% |

### Dataset totis-ti64-2021

| kernel | regime | n | excluded | W bias % | W MAPE % | W RMSE um | W within +-30% / x0.5-2 | D bias % | D MAPE % | D RMSE um | D within +-30% / x0.5-2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rosenthal | all | 80 | 0 | -7.0 | 20.6 | 29.3 | 74% / 99% | -3.7 | 38.8 | 95.9 | 51% / 90% |
| rosenthal | conduction | 8 | 0 | -34.0 | 34.0 | 27.1 | 12% / 100% | +108.8 | 140.3 | 26.2 | 12% / 25% |
| rosenthal | keyhole | 66 | 0 | -0.9 | 17.5 | 28.4 | 85% / 100% | -14.7 | 27.0 | 105.0 | 56% / 98% |
| rosenthal | transition | 6 | 0 | -37.0 | 37.0 | 39.5 | 33% / 83% | -32.9 | 32.9 | 18.3 | 50% / 83% |
| eagar-tsai | all | 80 | 0 | -2.2 | 18.7 | 27.3 | 80% / 100% | -7.1 | 36.5 | 95.9 | 51% / 89% |
| eagar-tsai | conduction | 8 | 0 | -14.9 | 22.9 | 17.7 | 75% / 100% | +80.0 | 112.9 | 26.4 | 12% / 25% |
| eagar-tsai | keyhole | 66 | 0 | +1.8 | 17.2 | 27.8 | 83% / 100% | -14.9 | 27.2 | 105.0 | 56% / 97% |
| eagar-tsai | transition | 6 | 0 | -29.4 | 29.4 | 32.3 | 50% / 100% | -37.6 | 37.6 | 20.2 | 50% / 83% |
| goldak | all | 80 | 0 | -6.9 | 20.6 | 29.3 | 74% / 99% | -2.9 | 39.1 | 95.9 | 50% / 90% |
| goldak | conduction | 8 | 0 | -34.2 | 34.2 | 27.2 | 12% / 100% | +114.8 | 145.6 | 25.9 | 0% / 25% |
| goldak | keyhole | 66 | 0 | -0.8 | 17.5 | 28.4 | 85% / 100% | -14.6 | 26.9 | 105.0 | 56% / 98% |
| goldak | transition | 6 | 0 | -37.1 | 37.1 | 39.6 | 33% / 83% | -30.6 | 30.6 | 17.5 | 50% / 83% |

### Hofmann, spot 50 um

| kernel | regime | n | excluded | W bias % | W MAPE % | W RMSE um | W within +-30% / x0.5-2 | D bias % | D MAPE % | D RMSE um | D within +-30% / x0.5-2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rosenthal | all | 175 | 0 | -3.0 | 13.2 | 21.2 | 94% / 100% | +25.4 | 42.8 | 51.3 | 65% / 89% |
| rosenthal | balling-flagged | 74 | 0 | +0.3 | 15.0 | 25.5 | 91% / 100% | +53.8 | 67.1 | 64.3 | 58% / 77% |
| rosenthal | conduction | 9 | 0 | -10.0 | 13.9 | 11.7 | 100% / 100% | +23.1 | 31.1 | 9.3 | 78% / 89% |
| rosenthal | keyhole | 78 | 0 | -4.1 | 11.7 | 18.2 | 96% / 100% | +1.9 | 23.2 | 43.7 | 73% / 99% |
| rosenthal | transition | 14 | 0 | -9.5 | 11.6 | 14.3 | 100% / 100% | +7.7 | 30.7 | 16.3 | 43% / 93% |
| eagar-tsai | all | 175 | 0 | +0.5 | 12.5 | 20.5 | 94% / 100% | +24.4 | 42.4 | 51.3 | 65% / 89% |
| eagar-tsai | balling-flagged | 74 | 0 | +2.9 | 15.1 | 25.3 | 89% / 100% | +53.7 | 67.1 | 64.3 | 58% / 77% |
| eagar-tsai | conduction | 9 | 0 | +1.7 | 11.4 | 9.1 | 89% / 100% | +15.6 | 24.3 | 9.0 | 78% / 89% |
| eagar-tsai | keyhole | 78 | 0 | -1.2 | 10.7 | 17.3 | 97% / 100% | +1.3 | 23.3 | 43.7 | 73% / 99% |
| eagar-tsai | transition | 14 | 0 | -3.2 | 10.1 | 11.6 | 100% / 100% | +3.5 | 29.6 | 16.6 | 43% / 93% |
| goldak | all | 175 | 0 | -2.8 | 13.2 | 21.1 | 94% / 100% | +26.1 | 43.1 | 51.3 | 66% / 89% |
| goldak | balling-flagged | 74 | 0 | +0.4 | 15.0 | 25.5 | 91% / 100% | +53.9 | 67.2 | 64.3 | 58% / 77% |
| goldak | conduction | 9 | 0 | -9.6 | 13.8 | 11.6 | 100% / 100% | +27.6 | 35.2 | 9.7 | 78% / 89% |
| goldak | keyhole | 78 | 0 | -3.9 | 11.6 | 18.2 | 96% / 100% | +2.2 | 23.2 | 43.7 | 73% / 99% |
| goldak | transition | 14 | 0 | -9.1 | 11.5 | 14.0 | 100% / 100% | +10.8 | 32.0 | 16.1 | 57% / 93% |

### Hofmann, spot 80 um

| kernel | regime | n | excluded | W bias % | W MAPE % | W RMSE um | W within +-30% / x0.5-2 | D bias % | D MAPE % | D RMSE um | D within +-30% / x0.5-2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rosenthal | all | 186 | 1 | -9.5 | 13.6 | 27.9 | 90% / 100% | +25.3 | 39.6 | 49.4 | 60% / 90% |
| rosenthal | balling-flagged | 59 | 0 | -12.3 | 14.3 | 32.6 | 88% / 100% | +50.1 | 56.4 | 44.5 | 44% / 83% |
| rosenthal | conduction | 25 | 1 | -23.2 | 23.5 | 29.3 | 68% / 100% | +45.2 | 46.8 | 12.7 | 52% / 92% |
| rosenthal | keyhole | 80 | 0 | -2.7 | 10.0 | 24.8 | 96% / 100% | +4.4 | 28.4 | 63.8 | 71% / 92% |
| rosenthal | transition | 22 | 0 | -11.6 | 13.1 | 23.0 | 95% / 100% | +12.3 | 26.7 | 17.8 | 68% / 95% |
| eagar-tsai | all | 187 | 0 | -3.8 | 10.3 | 24.1 | 96% / 100% | +21.6 | 37.2 | 49.2 | 62% / 91% |
| eagar-tsai | balling-flagged | 59 | 0 | -7.1 | 11.8 | 28.7 | 93% / 100% | +46.9 | 54.9 | 44.4 | 47% / 83% |
| eagar-tsai | conduction | 26 | 0 | -8.1 | 11.0 | 16.7 | 96% / 100% | +31.2 | 33.8 | 10.2 | 65% / 96% |
| eagar-tsai | keyhole | 80 | 0 | +0.4 | 9.1 | 23.8 | 98% / 100% | +3.9 | 28.5 | 64.0 | 69% / 92% |
| eagar-tsai | transition | 22 | 0 | -4.8 | 9.8 | 17.7 | 95% / 100% | +6.9 | 25.4 | 17.9 | 68% / 100% |
| goldak | all | 186 | 1 | -9.4 | 13.5 | 27.9 | 90% / 100% | +27.1 | 40.6 | 49.4 | 58% / 90% |
| goldak | balling-flagged | 59 | 0 | -12.3 | 14.3 | 32.6 | 88% / 100% | +51.7 | 57.2 | 44.5 | 42% / 83% |
| goldak | conduction | 25 | 1 | -23.3 | 23.7 | 29.5 | 68% / 100% | +50.7 | 51.7 | 13.9 | 48% / 92% |
| goldak | keyhole | 80 | 0 | -2.5 | 9.9 | 24.8 | 96% / 100% | +4.7 | 28.4 | 63.7 | 71% / 92% |
| goldak | transition | 22 | 0 | -11.4 | 13.0 | 22.9 | 95% / 100% | +15.7 | 28.2 | 18.0 | 64% / 95% |

### Hofmann, spot 110 um

| kernel | regime | n | excluded | W bias % | W MAPE % | W RMSE um | W within +-30% / x0.5-2 | D bias % | D MAPE % | D RMSE um | D within +-30% / x0.5-2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rosenthal | all | 161 | 0 | -15.5 | 16.7 | 34.7 | 86% / 100% | +25.8 | 38.8 | 40.4 | 61% / 93% |
| rosenthal | balling-flagged | 45 | 0 | -17.9 | 18.5 | 38.0 | 89% / 100% | +51.4 | 55.6 | 27.9 | 56% / 82% |
| rosenthal | conduction | 37 | 0 | -23.4 | 24.2 | 38.6 | 62% / 100% | +40.4 | 42.2 | 16.9 | 46% / 95% |
| rosenthal | keyhole | 59 | 0 | -8.5 | 10.0 | 27.5 | 100% / 100% | -0.0 | 24.5 | 57.8 | 71% / 100% |
| rosenthal | transition | 20 | 0 | -16.0 | 18.2 | 38.1 | 85% / 100% | +17.1 | 36.7 | 31.9 | 70% / 90% |
| eagar-tsai | all | 161 | 0 | -6.8 | 10.5 | 24.2 | 99% / 100% | +18.4 | 33.2 | 40.1 | 65% / 92% |
| eagar-tsai | balling-flagged | 45 | 0 | -8.2 | 12.6 | 27.4 | 100% / 100% | +40.7 | 48.0 | 26.6 | 56% / 82% |
| eagar-tsai | conduction | 37 | 0 | -6.7 | 11.7 | 20.4 | 100% / 100% | +26.1 | 28.4 | 13.8 | 70% / 95% |
| eagar-tsai | keyhole | 59 | 0 | -4.8 | 7.3 | 21.9 | 100% / 100% | -0.9 | 24.8 | 58.0 | 69% / 100% |
| eagar-tsai | transition | 20 | 0 | -9.9 | 13.0 | 29.0 | 95% / 100% | +10.9 | 33.9 | 32.2 | 65% / 85% |
| goldak | all | 161 | 0 | -15.5 | 16.7 | 34.8 | 86% / 100% | +28.7 | 41.0 | 40.6 | 58% / 91% |
| goldak | balling-flagged | 45 | 0 | -18.1 | 18.7 | 38.3 | 89% / 100% | +55.4 | 58.6 | 28.5 | 53% / 78% |
| goldak | conduction | 37 | 0 | -23.5 | 24.4 | 38.9 | 62% / 100% | +45.4 | 47.1 | 18.3 | 41% / 92% |
| goldak | keyhole | 59 | 0 | -8.4 | 9.8 | 27.2 | 100% / 100% | +0.5 | 24.4 | 57.6 | 71% / 100% |
| goldak | transition | 20 | 0 | -15.9 | 18.1 | 38.0 | 85% / 100% | +20.8 | 39.0 | 31.8 | 65% / 90% |

### Hofmann, spot 140 um

| kernel | regime | n | excluded | W bias % | W MAPE % | W RMSE um | W within +-30% / x0.5-2 | D bias % | D MAPE % | D RMSE um | D within +-30% / x0.5-2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rosenthal | all | 152 | 2 | -19.4 | 19.5 | 45.7 | 78% / 99% | +27.5 | 42.8 | 44.5 | 47% / 91% |
| rosenthal | balling-flagged | 38 | 0 | -19.7 | 19.7 | 45.8 | 87% / 100% | +37.6 | 42.6 | 24.8 | 45% / 92% |
| rosenthal | conduction | 59 | 2 | -26.7 | 26.7 | 53.4 | 51% / 98% | +56.9 | 58.3 | 22.6 | 34% / 85% |
| rosenthal | keyhole | 32 | 0 | -9.4 | 10.0 | 34.7 | 100% / 100% | -18.5 | 30.8 | 82.2 | 47% / 97% |
| rosenthal | transition | 23 | 0 | -13.8 | 14.1 | 36.7 | 100% / 100% | -0.8 | 20.4 | 36.8 | 83% / 96% |
| eagar-tsai | all | 154 | 0 | -7.4 | 9.6 | 27.1 | 98% / 100% | +16.6 | 33.9 | 43.6 | 58% / 93% |
| eagar-tsai | balling-flagged | 38 | 0 | -8.0 | 10.1 | 28.7 | 100% / 100% | +25.2 | 33.0 | 21.7 | 55% / 97% |
| eagar-tsai | conduction | 61 | 0 | -8.1 | 10.9 | 27.1 | 95% / 100% | +38.8 | 41.1 | 17.5 | 57% / 89% |
| eagar-tsai | keyhole | 32 | 0 | -5.4 | 6.8 | 26.7 | 100% / 100% | -19.6 | 31.5 | 83.3 | 44% / 94% |
| eagar-tsai | transition | 23 | 0 | -7.3 | 9.0 | 24.6 | 100% / 100% | -6.1 | 19.8 | 38.2 | 83% / 96% |
| goldak | all | 151 | 3 | -19.4 | 19.6 | 46.0 | 78% / 99% | +31.3 | 45.7 | 44.9 | 44% / 89% |
| goldak | balling-flagged | 38 | 0 | -19.9 | 19.9 | 46.2 | 87% / 100% | +42.4 | 46.4 | 26.3 | 45% / 87% |
| goldak | conduction | 58 | 3 | -26.9 | 26.9 | 54.1 | 52% / 97% | +62.5 | 63.5 | 24.7 | 24% / 83% |
| goldak | keyhole | 32 | 0 | -9.2 | 9.9 | 34.3 | 100% / 100% | -17.8 | 30.3 | 81.4 | 53% / 97% |
| goldak | transition | 23 | 0 | -13.7 | 14.0 | 36.5 | 100% / 100% | +2.4 | 21.2 | 36.2 | 78% / 96% |

**Powder-layer breakdowns below:** the kernels ignore powder-layer thickness (identical predictions at 0/30/60 um, see `assumptions.layer_um`), so any trend with powder-layer thickness in these tables is in the measurements only, not a kernel result.

### Hofmann, powder layer 0 um

| kernel | regime | n | excluded | W bias % | W MAPE % | W RMSE um | W within +-30% / x0.5-2 | D bias % | D MAPE % | D RMSE um | D within +-30% / x0.5-2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rosenthal | all | 207 | 3 | -16.9 | 18.5 | 37.7 | 76% / 100% | +23.1 | 28.8 | 33.0 | 71% / 95% |
| rosenthal | balling-flagged | 38 | 0 | -15.3 | 16.8 | 35.7 | 89% / 100% | +32.5 | 36.8 | 46.0 | 61% / 87% |
| rosenthal | conduction | 70 | 3 | -28.0 | 28.0 | 48.1 | 44% / 99% | +30.1 | 30.1 | 12.3 | 63% / 99% |
| rosenthal | keyhole | 71 | 0 | -8.0 | 11.0 | 26.9 | 96% / 100% | +14.9 | 27.7 | 42.8 | 75% / 96% |
| rosenthal | transition | 28 | 0 | -14.0 | 15.5 | 34.0 | 89% / 100% | +13.8 | 17.2 | 12.0 | 96% / 96% |
| eagar-tsai | all | 210 | 0 | -7.7 | 11.2 | 24.8 | 97% / 100% | +16.4 | 23.6 | 32.3 | 80% / 95% |
| eagar-tsai | balling-flagged | 38 | 0 | -10.6 | 13.3 | 28.6 | 95% / 100% | +29.8 | 37.5 | 46.1 | 63% / 87% |
| eagar-tsai | conduction | 73 | 0 | -9.2 | 11.8 | 24.3 | 97% / 100% | +15.3 | 15.6 | 7.5 | 89% / 99% |
| eagar-tsai | keyhole | 71 | 0 | -4.8 | 9.3 | 22.7 | 99% / 100% | +13.9 | 27.7 | 42.9 | 73% / 96% |
| eagar-tsai | transition | 28 | 0 | -6.8 | 11.4 | 25.6 | 93% / 100% | +7.3 | 14.9 | 10.4 | 96% / 96% |
| goldak | all | 206 | 4 | -16.9 | 18.5 | 37.9 | 77% / 99% | +25.4 | 30.6 | 33.3 | 66% / 95% |
| goldak | balling-flagged | 38 | 0 | -15.4 | 16.9 | 35.9 | 89% / 100% | +33.6 | 36.9 | 46.0 | 61% / 87% |
| goldak | conduction | 69 | 4 | -28.2 | 28.2 | 48.7 | 45% / 97% | +34.4 | 34.4 | 13.8 | 51% / 99% |
| goldak | keyhole | 71 | 0 | -7.8 | 10.9 | 26.7 | 96% / 100% | +15.5 | 27.8 | 42.8 | 73% / 96% |
| goldak | transition | 28 | 0 | -13.9 | 15.5 | 34.2 | 89% / 100% | +17.5 | 19.5 | 13.1 | 89% / 96% |

### Hofmann, powder layer 30 um

| kernel | regime | n | excluded | W bias % | W MAPE % | W RMSE um | W within +-30% / x0.5-2 | D bias % | D MAPE % | D RMSE um | D within +-30% / x0.5-2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rosenthal | all | 232 | 0 | -11.8 | 16.9 | 34.4 | 88% / 100% | +31.2 | 50.0 | 48.3 | 46% / 86% |
| rosenthal | balling-flagged | 91 | 0 | -11.7 | 20.3 | 40.2 | 81% / 100% | +48.8 | 57.7 | 42.1 | 48% / 81% |
| rosenthal | conduction | 44 | 0 | -21.7 | 22.4 | 40.4 | 73% / 100% | +80.8 | 84.0 | 24.6 | 14% / 77% |
| rosenthal | keyhole | 73 | 0 | -6.2 | 10.6 | 22.2 | 100% / 100% | -12.2 | 25.0 | 65.4 | 63% / 96% |
| rosenthal | transition | 24 | 0 | -11.6 | 13.4 | 29.1 | 100% / 100% | +5.6 | 35.0 | 41.2 | 46% / 88% |
| eagar-tsai | all | 232 | 0 | -3.9 | 11.7 | 25.1 | 96% / 100% | +24.1 | 44.4 | 48.0 | 48% / 87% |
| eagar-tsai | balling-flagged | 91 | 0 | -3.6 | 15.0 | 31.4 | 92% / 100% | +41.1 | 51.4 | 41.4 | 52% / 81% |
| eagar-tsai | conduction | 44 | 0 | -5.7 | 11.2 | 22.0 | 93% / 100% | +63.1 | 67.2 | 20.1 | 23% / 82% |
| eagar-tsai | keyhole | 73 | 0 | -2.7 | 8.6 | 18.4 | 100% / 100% | -12.9 | 25.5 | 65.9 | 60% / 96% |
| eagar-tsai | transition | 24 | 0 | -5.3 | 9.8 | 20.7 | 100% / 100% | +0.7 | 33.4 | 42.6 | 42% / 88% |
| goldak | all | 232 | 0 | -11.8 | 16.9 | 34.5 | 88% / 100% | +34.0 | 52.1 | 48.3 | 47% / 84% |
| goldak | balling-flagged | 91 | 0 | -11.8 | 20.4 | 40.4 | 81% / 100% | +51.4 | 59.8 | 42.3 | 47% / 79% |
| goldak | conduction | 44 | 0 | -21.8 | 22.6 | 40.7 | 73% / 100% | +87.4 | 89.9 | 26.5 | 14% / 73% |
| goldak | keyhole | 73 | 0 | -6.0 | 10.5 | 22.0 | 100% / 100% | -11.7 | 24.8 | 65.1 | 66% / 96% |
| goldak | transition | 24 | 0 | -11.4 | 13.2 | 28.7 | 100% / 100% | +8.8 | 36.5 | 40.3 | 46% / 88% |

### Hofmann, powder layer 60 um

| kernel | regime | n | excluded | W bias % | W MAPE % | W RMSE um | W within +-30% / x0.5-2 | D bias % | D MAPE % | D RMSE um | D within +-30% / x0.5-2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rosenthal | all | 235 | 0 | -6.3 | 11.7 | 26.6 | 97% / 100% | +23.2 | 42.7 | 55.0 | 59% / 91% |
| rosenthal | balling-flagged | 87 | 0 | -7.0 | 12.1 | 26.3 | 97% / 100% | +57.6 | 66.3 | 52.5 | 51% / 82% |
| rosenthal | conduction | 16 | 0 | -12.4 | 14.9 | 28.1 | 100% / 100% | +32.8 | 40.6 | 23.0 | 44% / 81% |
| rosenthal | keyhole | 105 | 0 | -3.0 | 10.2 | 26.0 | 97% / 100% | -2.6 | 26.0 | 65.1 | 69% / 98% |
| rosenthal | transition | 27 | 0 | -13.2 | 14.2 | 28.4 | 96% / 100% | +6.8 | 33.3 | 25.5 | 59% / 96% |
| eagar-tsai | all | 235 | 0 | -1.5 | 9.4 | 22.0 | 97% / 100% | +20.4 | 41.4 | 55.0 | 61% / 91% |
| eagar-tsai | balling-flagged | 87 | 0 | -1.7 | 10.3 | 21.4 | 97% / 100% | +53.6 | 63.4 | 52.0 | 53% / 84% |
| eagar-tsai | conduction | 16 | 0 | -1.2 | 8.1 | 15.3 | 100% / 100% | +24.5 | 35.1 | 21.3 | 62% / 88% |
| eagar-tsai | keyhole | 105 | 0 | +0.1 | 8.8 | 23.7 | 97% / 100% | -3.0 | 26.2 | 65.4 | 68% / 97% |
| eagar-tsai | transition | 27 | 0 | -7.4 | 10.0 | 20.0 | 100% / 100% | +2.2 | 32.8 | 26.3 | 59% / 96% |
| goldak | all | 235 | 0 | -6.2 | 11.6 | 26.5 | 97% / 100% | +24.8 | 43.5 | 55.0 | 60% / 90% |
| goldak | balling-flagged | 87 | 0 | -7.0 | 12.1 | 26.4 | 97% / 100% | +59.6 | 67.8 | 52.8 | 49% / 79% |
| goldak | conduction | 16 | 0 | -12.2 | 14.7 | 27.9 | 100% / 100% | +37.8 | 44.1 | 24.4 | 44% / 81% |
| goldak | keyhole | 105 | 0 | -2.8 | 10.1 | 25.9 | 97% / 100% | -2.2 | 25.8 | 64.9 | 70% / 98% |
| goldak | transition | 27 | 0 | -12.9 | 14.1 | 28.0 | 96% / 100% | +9.9 | 33.9 | 25.3 | 63% / 96% |

## Absorptivity sensitivity (SENSITIVITY, not a calibration)

SENSITIVITY, not a calibrated value: conduction-regime rows (regime assigned at the repo's default absorptivity), absorptivity_IR overridden uniformly via prop_overrides; the absorptivity actually acting in a physical track is unknown.

Conduction rows: 141.

| kernel | a=0.30 W MAPE % | a=0.40 W MAPE % | a=0.50 W MAPE % | a=0.60 W MAPE % | a=0.30 D MAPE % | a=0.40 D MAPE % | a=0.50 D MAPE % | a=0.60 D MAPE % | a=0.30 n | a=0.40 n | a=0.50 n | a=0.60 n |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| rosenthal | 36.8 | 26.6 | 18.5 | 14.3 | 33.8 | 52.3 | 71.4 | 89.8 | 126 | 137 | 140 | 141 |
| eagar-tsai | 18.8 | 12.4 | 10.0 | 11.5 | 27.5 | 36.9 | 56.5 | 74.8 | 141 | 141 | 141 | 141 |
| goldak | 36.8 | 26.4 | 18.5 | 14.5 | 35.9 | 57.3 | 77.0 | 96.1 | 123 | 134 | 139 | 141 |

Included row counts vary with assumed absorptivity: each column uses only rows where the kernel resolves an extent. These are different evaluation subsets; lower width error can accompany higher depth error. Sensitivity, not calibration.

## Wave 2 datasets (2026-10-06)

Wave 2 (2026-10-06): new open measured datasets run through the unchanged screening kernels; comparison, not validation. Per-dataset kernel x regime tables (regime = the repo's screening classifier) with cluster-bootstrap intervals:

### Wave 2 scorecard: ku-leuven-316l-2021

| kernel | regime | n | excluded | W bias % | W MAPE % | W RMSE um | W within +-30% / x0.5-2 | D bias % | D MAPE % | D RMSE um | D within +-30% / x0.5-2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rosenthal | all | 44 | 0 | +10.9 | 16.1 | 29.9 | 82% / 100% | -12.9 | 29.0 | 158.4 | 43% / 100% |
| rosenthal | keyhole | 44 | 0 | +10.9 | 16.1 | 29.9 | 82% / 100% | -12.9 | 29.0 | 158.4 | 43% / 100% |
| rosenthal | common | 44 | 0 | +10.9 | 16.1 | 29.9 | 82% / 100% | -12.9 | 29.0 | 158.4 | 43% / 100% |
| eagar-tsai | all | 44 | 0 | +12.2 | 16.7 | 30.4 | 80% / 100% | -12.9 | 29.0 | 158.4 | 43% / 100% |
| eagar-tsai | keyhole | 44 | 0 | +12.2 | 16.7 | 30.4 | 80% / 100% | -12.9 | 29.0 | 158.4 | 43% / 100% |
| eagar-tsai | common | 44 | 0 | +12.2 | 16.7 | 30.4 | 80% / 100% | -12.9 | 29.0 | 158.4 | 43% / 100% |
| goldak | all | 44 | 0 | +11.0 | 16.1 | 29.9 | 82% / 100% | -12.9 | 29.0 | 158.4 | 43% / 100% |
| goldak | keyhole | 44 | 0 | +11.0 | 16.1 | 29.9 | 82% / 100% | -12.9 | 29.0 | 158.4 | 43% / 100% |
| goldak | common | 44 | 0 | +11.0 | 16.1 | 29.9 | 82% / 100% | -12.9 | 29.0 | 158.4 | 43% / 100% |

| kernel | regime | n | parameter sets | W bias % CI95 | W MAPE % CI95 | D bias % CI95 | D MAPE % CI95 |
|---|---|---|---|---|---|---|---|
| rosenthal | all | 44 | 44 | [6.2, 15.6] | [12.8, 19.5] | [-21.5, -3.5] | [24.9, 33.0] |
| rosenthal | keyhole | 44 | 44 | [6.2, 15.6] | [12.8, 19.5] | [-21.5, -3.5] | [24.9, 33.0] |
| rosenthal | common | 44 | 44 | [6.2, 15.6] | [12.8, 19.5] | [-21.5, -3.5] | [24.9, 33.0] |
| eagar-tsai | all | 44 | 44 | [7.6, 16.8] | [13.4, 20.1] | [-21.5, -3.5] | [24.9, 33.0] |
| eagar-tsai | keyhole | 44 | 44 | [7.6, 16.8] | [13.4, 20.1] | [-21.5, -3.5] | [24.9, 33.0] |
| eagar-tsai | common | 44 | 44 | [7.6, 16.8] | [13.4, 20.1] | [-21.5, -3.5] | [24.9, 33.0] |
| goldak | all | 44 | 44 | [6.3, 15.7] | [12.8, 19.5] | [-21.5, -3.5] | [24.9, 33.0] |
| goldak | keyhole | 44 | 44 | [6.3, 15.7] | [12.8, 19.5] | [-21.5, -3.5] | [24.9, 33.0] |
| goldak | common | 44 | 44 | [6.3, 15.7] | [12.8, 19.5] | [-21.5, -3.5] | [24.9, 33.0] |

### Wave 2 scorecard: ku-leuven-ti64-2021

| kernel | regime | n | excluded | W bias % | W MAPE % | W RMSE um | W within +-30% / x0.5-2 | D bias % | D MAPE % | D RMSE um | D within +-30% / x0.5-2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rosenthal | all | 14 | 0 | -10.7 | 11.1 | 11.2 | 100% / 100% | +21.2 | 28.6 | 22.2 | 57% / 100% |
| rosenthal | keyhole | 14 | 0 | -10.7 | 11.1 | 11.2 | 100% / 100% | +21.2 | 28.6 | 22.2 | 57% / 100% |
| rosenthal | common | 14 | 0 | -10.7 | 11.1 | 11.2 | 100% / 100% | +21.2 | 28.6 | 22.2 | 57% / 100% |
| eagar-tsai | all | 14 | 0 | -7.8 | 8.4 | 9.1 | 100% / 100% | +21.2 | 28.6 | 22.2 | 57% / 100% |
| eagar-tsai | keyhole | 14 | 0 | -7.8 | 8.4 | 9.1 | 100% / 100% | +21.2 | 28.6 | 22.2 | 57% / 100% |
| eagar-tsai | common | 14 | 0 | -7.8 | 8.4 | 9.1 | 100% / 100% | +21.2 | 28.6 | 22.2 | 57% / 100% |
| goldak | all | 14 | 0 | -10.6 | 11.0 | 11.1 | 100% / 100% | +21.2 | 28.6 | 22.2 | 57% / 100% |
| goldak | keyhole | 14 | 0 | -10.6 | 11.0 | 11.1 | 100% / 100% | +21.2 | 28.6 | 22.2 | 57% / 100% |
| goldak | common | 14 | 0 | -10.6 | 11.0 | 11.1 | 100% / 100% | +21.2 | 28.6 | 22.2 | 57% / 100% |

| kernel | regime | n | parameter sets | W bias % CI95 | W MAPE % CI95 | D bias % CI95 | D MAPE % CI95 |
|---|---|---|---|---|---|---|---|
| rosenthal | all | 14 | 14 | [-13.6, -7.6] | [8.6, 13.6] | [5.1, 37.0] | [16.7, 40.8] |
| rosenthal | keyhole | 14 | 14 | [-13.6, -7.6] | [8.6, 13.6] | [5.1, 37.0] | [16.7, 40.8] |
| rosenthal | common | 14 | 14 | [-13.6, -7.6] | [8.6, 13.6] | [5.1, 37.0] | [16.7, 40.8] |
| eagar-tsai | all | 14 | 14 | [-10.7, -4.9] | [6.2, 10.7] | [5.1, 37.0] | [16.7, 40.8] |
| eagar-tsai | keyhole | 14 | 14 | [-10.7, -4.9] | [6.2, 10.7] | [5.1, 37.0] | [16.7, 40.8] |
| eagar-tsai | common | 14 | 14 | [-10.7, -4.9] | [6.2, 10.7] | [5.1, 37.0] | [16.7, 40.8] |
| goldak | all | 14 | 14 | [-13.4, -7.4] | [8.5, 13.5] | [5.1, 37.0] | [16.7, 40.8] |
| goldak | keyhole | 14 | 14 | [-13.4, -7.4] | [8.5, 13.5] | [5.1, 37.0] | [16.7, 40.8] |
| goldak | common | 14 | 14 | [-13.4, -7.4] | [8.5, 13.5] | [5.1, 37.0] | [16.7, 40.8] |

### Wave 2 scorecard: lane-in625-2020

| kernel | regime | n | excluded | W bias % | W MAPE % | W RMSE um | W within +-30% / x0.5-2 | D bias % | D MAPE % | D RMSE um | D within +-30% / x0.5-2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rosenthal | all | 18 | 5 | -15.0 | 15.0 | 23.0 | 100% / 100% | -3.8 | 39.8 | 40.8 | 22% / 89% |
| rosenthal | conduction | 8 | 5 | -16.3 | 16.3 | 23.0 | 100% / 100% | +40.4 | 40.4 | 16.0 | 0% / 100% |
| rosenthal | keyhole | 10 | 0 | -14.0 | 14.0 | 23.0 | 100% / 100% | -39.3 | 39.3 | 52.8 | 40% / 80% |
| rosenthal | common | 18 | 5 | -15.0 | 15.0 | 23.0 | 100% / 100% | -3.8 | 39.8 | 40.8 | 22% / 89% |
| eagar-tsai | all | 23 | 0 | +15.3 | 20.1 | 27.0 | 78% / 100% | -14.2 | 25.2 | 37.2 | 57% / 87% |
| eagar-tsai | conduction | 13 | 0 | +26.6 | 26.6 | 32.8 | 62% / 100% | +9.3 | 10.1 | 5.3 | 100% / 100% |
| eagar-tsai | keyhole | 10 | 0 | +0.6 | 11.5 | 16.7 | 100% / 100% | -44.8 | 44.8 | 56.1 | 0% / 70% |
| eagar-tsai | common | 18 | 5 | +9.7 | 15.8 | 23.0 | 94% / 100% | -18.0 | 31.8 | 42.0 | 44% / 83% |
| goldak | all | 18 | 5 | -16.1 | 16.1 | 24.3 | 100% / 100% | -2.0 | 39.1 | 39.7 | 22% / 89% |
| goldak | conduction | 8 | 5 | -18.7 | 18.7 | 26.0 | 100% / 100% | +41.8 | 41.8 | 16.7 | 0% / 100% |
| goldak | keyhole | 10 | 0 | -14.0 | 14.0 | 22.9 | 100% / 100% | -37.0 | 37.0 | 51.1 | 40% / 80% |
| goldak | common | 18 | 5 | -16.1 | 16.1 | 24.3 | 100% / 100% | -2.0 | 39.1 | 39.7 | 22% / 89% |

| kernel | regime | n | parameter sets | W bias % CI95 | W MAPE % CI95 | D bias % CI95 | D MAPE % CI95 |
|---|---|---|---|---|---|---|---|
| rosenthal | all | 18 | 5 | [-18.6, -10.8] | [10.8, 18.6] | [-42.6, 27.7] | [31.3, 48.9] |
| rosenthal | conduction | 8 | 2 | [-16.4, -16.2] | [16.2, 16.4] | [40.0, 40.9] | [40.0, 40.9] |
| rosenthal | keyhole | 10 | 3 | [-20.6, -7.8] | [7.8, 20.6] | [-56.0, -25.9] | [25.9, 56.0] |
| rosenthal | common | 18 | 5 | [-18.6, -10.8] | [10.8, 18.6] | [-42.6, 27.7] | [31.3, 48.9] |
| eagar-tsai | all | 23 | 6 | [0.5, 26.9] | [11.5, 28.6] | [-37.8, 5.9] | [10.8, 42.0] |
| eagar-tsai | conduction | 13 | 3 | [14.9, 35.5] | [14.9, 35.5] | [-0.6, 20.5] | [1.5, 20.5] |
| eagar-tsai | keyhole | 10 | 3 | [-14.1, 15.1] | [4.2, 15.1] | [-58.2, -34.5] | [34.5, 58.2] |
| eagar-tsai | common | 18 | 5 | [-4.9, 20.0] | [9.3, 22.5] | [-47.4, 7.5] | [17.3, 47.4] |
| goldak | all | 18 | 5 | [-19.6, -11.7] | [11.7, 19.6] | [-40.5, 30.0] | [30.0, 47.9] |
| goldak | conduction | 8 | 2 | [-20.3, -17.0] | [17.0, 20.3] | [38.9, 44.6] | [38.9, 44.6] |
| goldak | keyhole | 10 | 3 | [-20.3, -7.8] | [7.8, 20.3] | [-54.5, -23.1] | [23.1, 54.5] |
| goldak | common | 18 | 5 | [-19.6, -11.7] | [11.7, 19.6] | [-40.5, 30.0] | [30.0, 47.9] |

### SENSITIVITY on an unresolved input, not a fit: KU Leuven rows re-run with beam diameter 75 um (the 37.5 um value read as a radius)

### ku-leuven-316l-2021 at beam diameter 75 um

| kernel | regime | n | excluded | W bias % | W MAPE % | W RMSE um | W within +-30% / x0.5-2 | D bias % | D MAPE % | D RMSE um | D within +-30% / x0.5-2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rosenthal | all | 44 | 0 | +10.3 | 16.2 | 29.8 | 82% / 100% | -54.0 | 54.6 | 286.3 | 11% / 20% |
| rosenthal | conduction | 8 | 0 | -2.7 | 6.8 | 7.6 | 100% / 100% | -28.3 | 31.4 | 35.2 | 62% / 75% |
| rosenthal | keyhole | 33 | 0 | +16.2 | 18.1 | 33.3 | 76% / 100% | -60.4 | 60.4 | 329.6 | 0% / 3% |
| rosenthal | transition | 3 | 0 | -20.0 | 20.0 | 26.1 | 100% / 100% | -51.8 | 51.8 | 63.1 | 0% / 67% |
| rosenthal | common | 44 | 0 | +10.3 | 16.2 | 29.8 | 82% / 100% | -54.0 | 54.6 | 286.3 | 11% / 20% |
| eagar-tsai | all | 44 | 0 | +16.2 | 19.2 | 32.5 | 77% / 100% | -55.3 | 55.3 | 286.4 | 9% / 18% |
| eagar-tsai | conduction | 8 | 0 | +13.6 | 14.7 | 13.2 | 88% / 100% | -34.3 | 34.3 | 37.1 | 50% / 75% |
| eagar-tsai | keyhole | 33 | 0 | +19.6 | 20.7 | 36.5 | 73% / 100% | -60.5 | 60.5 | 329.7 | 0% / 3% |
| eagar-tsai | transition | 3 | 0 | -14.3 | 14.3 | 18.8 | 100% / 100% | -54.5 | 54.5 | 65.6 | 0% / 33% |
| eagar-tsai | common | 44 | 0 | +16.2 | 19.2 | 32.5 | 77% / 100% | -55.3 | 55.3 | 286.4 | 9% / 18% |
| goldak | all | 44 | 0 | +10.5 | 16.3 | 30.0 | 82% / 100% | -53.3 | 54.1 | 286.3 | 11% / 20% |
| goldak | conduction | 8 | 0 | -2.5 | 6.7 | 7.3 | 100% / 100% | -25.4 | 29.7 | 34.1 | 62% / 75% |
| goldak | keyhole | 33 | 0 | +16.4 | 18.2 | 33.5 | 76% / 100% | -60.4 | 60.4 | 329.6 | 0% / 3% |
| goldak | transition | 3 | 0 | -20.0 | 20.0 | 26.1 | 100% / 100% | -50.3 | 50.3 | 61.6 | 0% / 67% |
| goldak | common | 44 | 0 | +10.5 | 16.3 | 30.0 | 82% / 100% | -53.3 | 54.1 | 286.3 | 11% / 20% |

### ku-leuven-ti64-2021 at beam diameter 75 um

| kernel | regime | n | excluded | W bias % | W MAPE % | W RMSE um | W within +-30% / x0.5-2 | D bias % | D MAPE % | D RMSE um | D within +-30% / x0.5-2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rosenthal | all | 14 | 0 | -11.7 | 12.0 | 12.0 | 100% / 100% | -41.6 | 42.9 | 71.1 | 29% / 50% |
| rosenthal | conduction | 7 | 0 | -15.8 | 15.8 | 14.0 | 100% / 100% | -24.0 | 26.7 | 26.2 | 57% / 86% |
| rosenthal | keyhole | 5 | 0 | -7.7 | 8.6 | 10.5 | 100% / 100% | -63.5 | 63.5 | 111.4 | 0% / 0% |
| rosenthal | transition | 2 | 0 | -7.4 | 7.4 | 7.1 | 100% / 100% | -48.0 | 48.0 | 44.5 | 0% / 50% |
| rosenthal | common | 14 | 0 | -11.7 | 12.0 | 12.0 | 100% / 100% | -41.6 | 42.9 | 71.1 | 29% / 50% |
| eagar-tsai | all | 14 | 0 | +3.9 | 7.6 | 7.5 | 100% / 100% | -47.4 | 47.4 | 72.5 | 21% / 50% |
| eagar-tsai | conduction | 7 | 0 | +7.0 | 10.8 | 9.0 | 100% / 100% | -33.6 | 33.6 | 28.4 | 43% / 86% |
| eagar-tsai | keyhole | 5 | 0 | -1.0 | 3.9 | 5.7 | 100% / 100% | -64.7 | 64.7 | 112.6 | 0% / 0% |
| eagar-tsai | transition | 2 | 0 | +5.5 | 5.5 | 5.3 | 100% / 100% | -52.6 | 52.6 | 47.7 | 0% / 50% |
| eagar-tsai | common | 14 | 0 | +3.9 | 7.6 | 7.5 | 100% / 100% | -47.4 | 47.4 | 72.5 | 21% / 50% |
| goldak | all | 14 | 0 | -11.8 | 12.1 | 12.1 | 100% / 100% | -39.7 | 41.5 | 70.4 | 36% / 50% |
| goldak | conduction | 7 | 0 | -15.8 | 15.8 | 14.0 | 100% / 100% | -21.3 | 25.0 | 25.2 | 71% / 86% |
| goldak | keyhole | 5 | 0 | -7.7 | 8.7 | 10.6 | 100% / 100% | -62.9 | 62.9 | 110.6 | 0% / 0% |
| goldak | transition | 2 | 0 | -8.0 | 8.0 | 7.7 | 100% / 100% | -46.2 | 46.2 | 43.2 | 0% / 50% |
| goldak | common | 14 | 0 | -11.8 | 12.1 | 12.1 | 100% / 100% | -39.7 | 41.5 | 70.4 | 36% / 50% |

### SENSITIVITY on an unresolved input, not a fit: Lane AMMT rows re-run at the nominal case power from the paper text (150 W case A, 195 W cases B/C) instead of the Table 3 power (137.9/179.2 W)

### Lane AMMT at nominal power (13 rows)

| kernel | regime | n | excluded | W bias % | W MAPE % | W RMSE um | W within +-30% / x0.5-2 | D bias % | D MAPE % | D RMSE um | D within +-30% / x0.5-2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rosenthal | all | 8 | 5 | -11.9 | 11.9 | 17.2 | 100% / 100% | +47.9 | 47.9 | 18.9 | 0% / 100% |
| rosenthal | conduction | 8 | 5 | -11.9 | 11.9 | 17.2 | 100% / 100% | +47.9 | 47.9 | 18.9 | 0% / 100% |
| rosenthal | common | 8 | 5 | -11.9 | 11.9 | 17.2 | 100% / 100% | +47.9 | 47.9 | 18.9 | 0% / 100% |
| eagar-tsai | all | 13 | 0 | +30.5 | 30.5 | 37.4 | 46% / 100% | +17.2 | 17.2 | 7.8 | 92% / 100% |
| eagar-tsai | conduction | 13 | 0 | +30.5 | 30.5 | 37.4 | 46% / 100% | +17.2 | 17.2 | 7.8 | 92% / 100% |
| eagar-tsai | common | 8 | 5 | +24.6 | 24.6 | 33.7 | 75% / 100% | +23.4 | 23.4 | 9.8 | 88% / 100% |
| goldak | all | 8 | 5 | -13.3 | 13.3 | 18.9 | 100% / 100% | +51.2 | 51.2 | 20.4 | 0% / 100% |
| goldak | conduction | 8 | 5 | -13.3 | 13.3 | 18.9 | 100% / 100% | +51.2 | 51.2 | 20.4 | 0% / 100% |
| goldak | common | 8 | 5 | -13.3 | 13.3 | 18.9 | 100% / 100% | +51.2 | 51.2 | 20.4 | 0% / 100% |

Sensitivity re-runs: 213 solver calls, 213 flat-plate calls (solver calls of the two wave 2 sensitivity re-runs, not included in absorption.solverCalls; flatPlateCalls counts those calls whose result reports absorptionModel 'flat-plate').

### KU Leuven published regime label vs screening classifier

rows: KU Leuven authors' published label; columns: the repo's screening classifier at the primary inputs. Counts only; the published label is not a measured regime boundary.

| published / screening | keyhole |
|---|---|
| conduction | 9 |
| keyhole | 41 |
| transition | 8 |

### Lane 2020 Table 4 class summary (published, transcribed)

| class | width um (N, Umean) | depth um (N, Umean) | length um (N, Umean) | cooling rate 1290-1190 C/s (N, Umean) | cooling-rate use |
|---|---|---|---|---|---|
| AMMT-A | 148 (9, 1.07) | 42 (9, 0.49) | 300 (19, 0.50) | 1.16E+06 (19, 6.15E+04) | do-not-use (same AMMT-20us values as Table 3, footnote c) |
| AMMT-B | 123 (9, 1.87) | 36 (9, 0.56) | 359 (10, 3.69) | 1.08E+06 (10, 1.86E+05) | do-not-use (same AMMT-20us values as Table 3, footnote c) |
| AMMT-C | 106 (12, 0.37) | 30 (12, 0.16) | 370 (7, 7.72) | 1.90E+06 (7, 2.09E+05) | do-not-use (same AMMT-20us values as Table 3, footnote c) |
| CBM-A | 171 (9, 0.82) | 151 (9, 5.75) | 659 (129, 0.47) | 6.20E+05 (129, 6.16E+03) | exemplar, not reference (paper conclusions) |
| CBM-B | 133 (9, 0.50) | 91 (9, 0.52) | 780 (59, 0.50) | 9.35E+05 (59, 1.82E+04) | exemplar, not reference (paper conclusions) |
| CBM-C | 100 (12, 0.48) | 60 (12, 0.16) | 754 (52, 0.68) | 1.28E+06 (52, 5.29E+04) | exemplar, not reference (paper conclusions) |

Umean is the standard uncertainty of the mean as labelled in Table 4 (Tables 5-7 give the uncertainty budgets for length, width and depth). Per the Table 4 caption, AMMT length and cooling rate come from the AMMT-20 us tracks only, so the AMMT class cooling rates are the same AMMT-20 us values that Table 3 footnote c says should not be used; they are flagged do-not-use. The paper calls all cooling rates exemplar, not reference data.

### Reference target: nist-amb2022-03-thermal-2022 (thermal targets (IN718 single tracks))

NIST AM-Bench, 'AMB2022-03 Benchmark Measurements and Challenge Results' (Measurement and Result Descriptions v1.0, 2022): Table 1 (process cases), Table 2 (TTAM, TSCR, TLCR), Table 3 (TTCR, supplementary), page 2 and 4. Evidence kind: published measurement (thermography-derived, table transcription). Source sha256 `dea3feddec2bc23281ae86c6fd9cee4d0a934a4304501fe0c038f24c7dbc9db0` (1195056 B, retrieved 2026-10-06); committed table sha256 `296b526f49fd484cb482c9f3db733ecd62283ad50eb6e529750a0b30f2f81426`.

| case | power_W | speed_mm_s | d4sigma_um | TTAM_ms | TSCR_C_s | TLCR_C_s | TTCR_C_s |
|---|---|---|---|---|---|---|---|
| 0 | 285 | 960 | 67 | 1.22 | 699000 | 414000 | 193000 |
| 1.1 | 285 | 960 | 49 | 1.3 | 732000 | 406000 | 138000 |
| 1.2 | 285 | 960 | 82 | 1.04 | 511000 | 365000 | 193000 |
| 2.1 | 285 | 1200 | 67 | 0.896 | 785000 | 506000 | 301000 |
| 2.2 | 285 | 800 | 67 | 1.59 | 611000 | 325000 | 146000 |
| 3.1 | 325 | 960 | 67 | 1.38 | 705000 | 381000 | 157000 |
| 3.2 | 245 | 960 | 67 | 1.03 | 749000 | 433000 | 232000 |

- caveat: Thermography of bare IN718 single tracks; each value is the mean of three tracks over 30 centerline pixels at a nominally steady-state location (page 2).
- caveat: Processing assumptions stated on page 2: no undercooling, and emissivity set so the apparent solidification inflection equals the IN718 solidus/liquidus midpoint. The TTAM challenge definition on page 1 gives that midpoint as 'assumed to be 1298 C'; the explicit 'Ttrans = 1298 C' with emissivity 0.5 on page 7 belongs to the pad PTAM/PSCR processing. Page 3 notes the measurement error in TAM and SCR may be greatest at the largest spot size (case 1.2).
- caveat: TTCR is listed as supplementary data 'for reference', not a challenge quantity (Table 3); its definition is in the separate challenge-description document, which was not transcribed here.
- caveat: Same seven cases as the IN718 optical width/depth record already in the app (NIST mds2-2718 / AMB2022-03 Table 4); process parameters agree with lpbf_nist_in718_comparison.CASE_PROCESS.

**Comparison: unavailable.** No like-for-like model comparison exists in the app for these quantities. The screening kernels report solidificationKinetics.coolingRate_K_s as G x R at their solidification-front points, not the surface centerline cooling rate just below the solidus (TSCR) or above the liquidus (TLCR), and no reviewed operator converts a kernel melt-pool length into a time above 1298 C at the surface centerline (TTAM). Adding such an operator is a model change that needs its own review; nothing was computed here.

### Reference target: simonds-316l-2018 (absorptance targets (316L stationary spot welds))

B. J. Simonds et al., 'Time-Resolved Absorptance and Melt Pool Dynamics during Intense Laser Irradiation of a Metal', Phys. Rev. Applied 10, 044061 (2018), doi:10.1103/PhysRevApplied.10.044061, PMC7047776, Table III (integrating-sphere optical results). Evidence kind: published measurement (table transcription). Source sha256 `aaf9a603e57e95d37c7db39cbceda30cef7a6edf78f5b8626628aa68f95e86f8` (127169 B, retrieved 2026-10-06); committed table sha256 `e5fbaeb037371935c167d3e0e1740a348427313c886f7aab2ee439ee3c789db0`.

| E_in_J | avg_irradiance_MW_cm2 | W_weld_um | L_weld_um | E_abs_J | eta_coupling | time_to_melt_ms | time_to_keyhole_ms |
|---|---|---|---|---|---|---|---|
| 1.2 | 0.17 | 304 | 156 | 0.378 | 0.31 | 0.6 | - |
| 2.05 | 0.29 | 335 | 232 | 0.64 | 0.31 | 0.25 | - |
| 2.92 | 0.412 | 346 | 310 | 1.02 | 0.35 | 0.11 | 2.1 |
| 3.1 | 0.439 | 418 | 343 | 1.55 | 0.5 | 0.068 | 1.5 |
| 3.27 | 0.462 | 468 | 374 | 1.794 | 0.55 | 0.036 | 0.91 |
| 3.45 | 0.489 | 556 | 417 | 2.209 | 0.64 | 0.064 | 0.57 |
| 3.61 | 0.511 | 633 | 472 | 2.535 | 0.7 | 0.064 | 0.52 |
| 3.78 | 0.535 | 631 | 495 | 2.62 | 0.69 | 0.024 | 0.46 |
| 4.63 | 0.655 | 786 | 679 | 3.58 | 0.77 | 0.044 | 0.32 |
| 6.26 | 0.889 | 836 | 996 | 5.37 | 0.86 | 0.024 | 0.14 |

- caveat: Stationary 10 ms laser spot welds (1070 nm, 303 um top-hat, full width at 1/e^2), polished SRM 1155a disc (RMS roughness 79 +- 20 nm), no powder, no scanning: not a scan-track coupling value.
- caveat: eta_coupling is the average coupling efficiency over the weld (E_abs / E_in) from the integrating sphere; time-to-keyhole is defined in the paper as the time absorptance reaches 0.40 after the initial rise; '-' (no keyhole reached) is stored as blank.
- caveat: The Table III caption names W_weld width and L_weld 'length' without defining the direction; keyhole rows have L > W, so L may be a penetration length. It is stored but not used.
- caveat: Power-meter uncertainty 3 % (stated); per-row uncertainties are not in Table III.

**Comparison: unavailable.** The app has no stationary-spot (non-scanning) absorptance model: the kernels take a moving source and a constant flat-plate absorptivity_IR (316L 0.42, estimated), so there is no like-for-like prediction of a 10 ms, 303 um top-hat spot's average coupling efficiency. Not computed.

## Reference transient (bare plate, low power)

This block depends on wall-clock budgets (total and per case): on a slower or busier host cases can turn into 'not-run (budget)', so it is not guaranteed to reproduce; `--reuse-reference` copies the block of an earlier record instead of re-running it. This record's block was reused from a record with sha256 `3437be3732c892fe222812421dc63416cb5b9dc3a8b562695d329d9ec0139fac` (LF-normalised).

Hofmann rows with t_powder = 0 (bare plate) and P <= 100 W (26 rows); all other rows are not run with the reference transient.
Completed 17, boiling stop 9, not run (budget) 0 of 26. sourcePenetration_um = 40 is an arbitrary, unvalidated choice for the bare-plate volumetric absorption depth; mesh 20 um is coarse relative to the 50-140 um spots and the result is not mesh-converged: every completed case has depth <= 2 cells, so its width/depth are cell-quantised (meshLimited = true) and carry almost no information about the measured track; a completed width of 0 means no resolved liquid extent. completed/boiling-stop is the reference transient's own validity stop; the widths/depths are a model comparison, not validation. Rows beyond the budget were skipped, not estimated.

| row | P W | v mm/s | d um | status | W pred | W meas | D pred | D meas |
|---|---|---|---|---|---|---|---|---|
| hofmann-0047 | 75 | 1050 | 50 | completed (mesh-limited) | 39.5 | 72.8 | 19.7 | 25.7 |
| hofmann-0083 | 100 | 600 | 110 | completed (mesh-limited) | 98.9 | 121.2 | 39.6 | 35.2 |
| hofmann-0102 | 100 | 300 | 80 | boiling-stop | - | 140.1 | - | 54.8 |
| hofmann-0156 | 75 | 750 | 80 | completed (mesh-limited) | 40.0 | 99.8 | 20.0 | 25.6 |
| hofmann-0164 | 50 | 600 | 80 | completed (mesh-limited) | 40.0 | 86.0 | 20.0 | 18.0 |
| hofmann-0241 | 50 | 900 | 50 | completed (mesh-limited) | 39.5 | 66.8 | 19.7 | 22.0 |
| hofmann-0245 | 100 | 900 | 50 | boiling-stop | - | 77.9 | - | 36.6 |
| hofmann-0269 | 100 | 300 | 80 | boiling-stop | - | 124.4 | - | 50.0 |
| hofmann-0301 | 100 | 1200 | 80 | completed (mesh-limited) | 40.0 | 104.9 | 20.0 | 21.6 |
| hofmann-0326 | 50 | 300 | 50 | boiling-stop | - | 80.8 | - | 33.4 |
| hofmann-0341 | 100 | 1200 | 50 | boiling-stop | - | 67.2 | - | 29.2 |
| hofmann-0346 | 100 | 1500 | 50 | completed (mesh-limited) | 39.5 | 69.9 | 19.7 | 26.1 |
| hofmann-0409 | 100 | 900 | 80 | completed (mesh-limited) | 80.0 | 87.6 | 40.0 | 30.3 |
| hofmann-0412 | 50 | 300 | 140 | completed (mesh-limited) | 60.0 | 112.9 | 20.0 | 14.9 |
| hofmann-0432 | 100 | 900 | 110 | completed (mesh-limited) | 59.4 | 107.1 | 19.8 | 24.1 |
| hofmann-0446 | 75 | 750 | 50 | boiling-stop | - | 69.0 | - | 29.8 |
| hofmann-0467 | 50 | 600 | 80 | completed (mesh-limited) | 40.0 | 88.2 | 20.0 | 18.0 |
| hofmann-0508 | 100 | 600 | 50 | boiling-stop | - | 92.7 | - | 53.3 |
| hofmann-0529 | 100 | 1050 | 80 | completed (mesh-limited) | 40.0 | 101.7 | 20.0 | 27.9 |
| hofmann-0541 | 50 | 300 | 110 | completed (mesh-limited) | 59.4 | 115.9 | 39.6 | 22.2 |
| hofmann-0544 | 50 | 450 | 50 | completed (mesh-limited) | 39.5 | 74.8 | 39.5 | 26.8 |
| hofmann-0563 | 100 | 600 | 140 | completed (mesh-limited) | 100.0 | 130.1 | 40.0 | 26.4 |
| hofmann-0606 | 100 | 450 | 50 | boiling-stop | - | 123.3 | - | 84.7 |
| hofmann-0608 | 50 | 1050 | 80 | completed (mesh-limited) | 0.0 | 71.1 | 0.0 | 14.6 |
| hofmann-0613 | 50 | 900 | 50 | completed (mesh-limited) | 39.5 | 52.4 | 19.7 | 20.9 |
| hofmann-0618 | 100 | 600 | 80 | boiling-stop | - | 96.1 | - | 38.1 |
