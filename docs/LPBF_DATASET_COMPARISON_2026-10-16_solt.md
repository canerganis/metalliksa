# LPBF dataset comparison (2026-10-16)

**Comparison of screening kernels against published single-track measurements; not experimental validation; estimated material laws; absorptivity assumed.**

Schema `lpbf-dataset-comparison-1`; implementation fingerprint `13203cac19bf69db80b546c6e67ed846a0941e35ea4ad62e53a786de073c46ca`; quick mode: False. Honesty: comparison, not validation; screening kernels; estimated material laws; absorptivity assumed (not measured); published single-track measurements, no replicate or uncertainty model; a failing comparison is reported, not fitted away. `experimentalValidation` = false.

Slim view record `LPBF_DATASET_COMPARISON_2026-10-16_solt.view.json` (this record minus `breakdowns` and `referenceTransient.rows`; sha256 of its LF bytes `fc08d6e8abae4526c9413671105fe240181978b673f3a8b673dd29d33d3d69db`).

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
  - caveat: IN625 kernel properties come from lpbf_thermal_solver.SECONDARY_THERMOPHYSICAL_DB (provenance class 'legacy-estimated-secondary'; since P7b its absorptivity_IR 0.34 is the measured conduction-mode authority (Deisenroth 2020 Sec. 3.4) and the regime index reads the convention constant 0.38; the other properties are estimated), not from a measured property set.

## Regime screening rule

Screening classifier, not the papers' regime definition. Inputs: normalised enthalpy dH/h_s = eta*P / (rho*cp_s*max(50, T_liq-T0)*sqrt(pi*alpha_s*v*r^3)) (same form as lpbf_thermal_solver.py, flat-plate absorptivity_IR of the material authority, solid k/cp, r = d/2) and the dataset's own balling flag. balling == 1 -> 'balling-flagged' (Hofmann only); otherwise dH/h_s < 15 -> 'conduction', 15 <= dH/h_s < 20 -> 'transition', >= 20 -> 'keyhole'; Inconel 625: dH/h_s < 13.6 -> 'conduction', >= 13.6 -> 'keyhole', no transition band (derivation: lpbf_thermal_solver.REGIME_THRESHOLD_BASIS). Measured D/W is recorded next to the label but not used for it. Wave 2 rows (KU Leuven 316L/Ti-6Al-4V, Lane IN625) are classified by the same screening rule; the KU Leuven authors' own labels are kept verbatim in regime.publishedLabel and are not used for the statistics' regime split. Added datasets without a reported beam diameter (CMU) or with unresolved measured dimension units/operator (KU Leuven IN718 (ku-leuven-in718-2021)) are labeled unclassified and excluded from kernel predictions; no regime label is inferred for them.

Row counts per regime: all 1431, balling-flagged 216, conduction 154, keyhole 309, transition 78, unclassified-missing-process-input 626, unclassified-source-dimensions-unresolved 48

## Assumptions

- **hatch_um**: 100 (no dataset in this record has a hatch: single tracks; the hatch only enters the lack-of-fusion screen, not the width/depth/length extents)
- **layer_um**: t_powder 0 (bare plate) rows are passed with a nominal 30 um layer because the function requires a positive layer; width/depth/length do not depend on it (checked at 10/30/60 um)
- **preheat_C**: 20 C assumed for every dataset (no dataset in this record states a build-plate or substrate temperature in the files read)
- **absorptivity**: the repo's absorptivity_IR authority (316L 0.30, Ti-6Al-4V 0.32: measured conduction-mode bare-plate values since P7b; IN625 0.34 measured, Deisenroth 2020, from the secondary table, wave 2 Lane rows only; the regime index reads the convention constants 0.42, 0.35 and 0.38), flat-plate
- **inclusionRule**: a row counts for statistics only when extentStatus == 'computed'
- **powderBedRayTracer**: calculate_meltpool_physics runs the optional GPU powder ray tracer only when absorption_model='powder-raytrace' is requested (tier-2 bump 2026-10-06); the default and this harness use the flat-plate absorptivity, so the ray tracer was not used; see `absorption`
- **wave2**: KU Leuven rows: beam diameter unverified: 37.5 um carried from the 2026-10-05 KU Leuven IN718 record ('Paper reports 37.5 um spot'); the article (doi:10.1016/j.jmatprotec.2022.117547) could not be read (HTTP 403), so diameter vs radius and the beam-size definition are not confirmed; layer left unset (not stated in the files read; the 2026-10-05 KU Leuven IN718 record cites a 60 um powder layer from the Coen article, which could not be read here (HTTP 403), so it is not carried over to these rows; kernels ignore it); 20 C preheat assumed. Lane rows: bare plate (layer 0, passed as the nominal layer), Table 3 power, D4sigma spot as the 1/e^2 diameter, 20 C preheat assumed, IN625 properties from the solver's legacy-estimated secondary table. No kernel parameter was changed for these rows; sensitivities are reported separately.
- **addedDatasetTreatment**: CMU ST has no power field; all CMU rows lack beam diameter. KU Leuven IN718 (ku-leuven-in718-2021) source dimensions retain unresolved units and width operator. These rows have no numeric regime classification or kernel predictions and are excluded from MAPE/statistics; source observations remain in rows with explicit extentStatus reasons. This applies to the IN718 file only: the wave 2 KU Leuven 316L/Ti-6Al-4V units were resolved from their raw '(1)' files (see the wave 2 catalog notes); the same raw-file check was not applied to the IN718 file in this record.

## Absorption path

Path: **flat-plate** (pinned: True). calculate_meltpool_physics(absorption_model='flat-plate'), the solver default on every machine since the 2026-10-06 tier-2 bump; sys.modules['powder_bed_raytracer'] = None is also set in the main process and in every worker so any ray-tracer import fails loudly.

Ray-tracer module present: True; importable in a separate probe process: False. Absorptivity by material: 316L 0.3, Ti-6Al-4V 0.32, Inconel 625 0.34. Flat-plate calls: 4362 of 4362 solver calls (by kernel, main run: rosenthal 838, eagar-tsai 838, goldak 838).

flat-plate absorptivity_IR; the GPU powder ray tracer was not used; with it the predictions change (reviewer stub: Eagar-Tsai hofmann-0001 171.0/119.6 -> 209.2/143.6 um at effective 0.65). flatPlateCalls counts the solver results that report processParameters.absorptionModel == 'flat-plate'; equal to solverCalls when every call took the flat-plate path (failed calls report none).

## Limits

- Kernels are compared on different included subsets (rows with extentStatus == 'computed'): pooled n = rosenthal 718 of 1431, eagar-tsai 756 of 1431, goldak 711 of 1431. Only summary.<kernel>.common (n = 711, the rows where all kernels are computed) is a like-for-like comparison; pooled and per-regime figures of different kernels are not.
- Rosenthal conduction statistics rest on 117 of 154 conduction rows: they are selected by the kernel's own output (only rows where Rosenthal resolves an extent without heuristic fallback, search-box limitation or the 0.55 x beam-diameter width floor are 'computed'), so they describe the rows it can resolve, not the regime.
- Eagar-Tsai and Goldak keyhole-regime depth statistics are near-identical (bias -29.2 / -28.2 %, MAPE 34.5 / 33.5 %) because both add the same Fabbro keyhole depth term; they are not independent evidence.
- The measurements carry no uncertainty model: the pooled-summary datasets (Hofmann 316L, Totis Ti-6Al-4V) provide no per-row measurement uncertainty; the wave 2 Lane IN625 rows carry Table 3 per-track sigma (measured.widthSigma_um / depthSigma_um, the spread of N = 3 microscopy measurements, not an uncertainty) and the statistics do not use it. The bootstrap intervals cover resampling of parameter sets only, not measurement error, the estimated material laws or the assumed absorptivity.
- Replicate rows are not independent: the Hofmann table has 677 rows but only 623 distinct parameter sets; the bootstrap intervals resample whole parameter sets (clusters), the point statistics weight every row.
- Balling-flagged rows (216) are inside the pooled 'all' headline statistics; a continuous-track screening kernel is not meant to describe them.
- The Totis depth datum is the top of the printed base under the 25 um powder layer (Vaglio et al. 2020, Fig. 1/2b; the workbook does not state it) and the Hofmann datum is the substrate surface (Fig. 2); the kernels compute depth from the free surface, so the 80 Totis and the Hofmann powder-layer depths carry an offset, reported as the declared sensitivity column `sensitivity.depthDatumCorrection_um` = phi*t with phi = 0.6 (geometric assumption (h_surface = φ·t); powder denudation not modelled), never applied to the served depth.
- The kernels ignore powder-layer thickness (identical predictions at 0/30/60 um; see assumptions.layer_um), so any trend with powder-layer thickness is in the measurements only.
- Absorption path: flat-plate absorptivity_IR (316L 0.3, Ti-6Al-4V 0.32, Inconel 625 0.34); the GPU powder ray tracer was not used; with the ray tracer the predictions change.
- The reference-transient block depends on wall-clock budgets (total and per case): on a slower host rows can become 'not-run (budget)'. --reuse-reference copies the block of an earlier record instead.
- KU Leuven 316L/Ti-6Al-4V (58 condition means): the beam diameter is unverified: 37.5 um carried from the 2026-10-05 KU Leuven IN718 record ('Paper reports 37.5 um spot'); the article (doi:10.1016/j.jmatprotec.2022.117547) could not be read (HTTP 403), so diameter vs radius and the beam-size definition are not confirmed; the 75 um re-run in wave2.kuBeamDiameterSensitivity shows how much the statistics move with it. Rows are condition means of 7 to 16 sections; the bootstrap resamples conditions, not sections.
- Lane IN625 (23 tracks): AMMT kernel inputs use the Table 3 power (137.9/179.2 W). Fig. 2 caption: 'Laser power values indicated are the applied laser power'; Table 3 lists 137.9/179.2 W for the AMMT cases and the Section 2 case definitions give 150/195 W. Whether these are applied vs commanded powers is not stated explicitly, and the Fig. 2 image was not read. Status: UNRESOLVED. See wave2.laneNominalPowerSensitivity. IN625 properties are legacy estimates (absorptivity_IR 0.34).
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
| rosenthal | all | 718 | 713 | -33.2 | 34.6 | 65.3 | 27% / 93% | -13.3 | 34.5 | 71.9 | 50% / 88% |
| rosenthal | balling-flagged | 214 | 2 | -35.5 | 35.9 | 65.3 | 27% / 92% | +4.2 | 37.1 | 43.2 | 53% / 93% |
| rosenthal | conduction | 117 | 37 | -43.4 | 43.4 | 69.4 | 6% / 79% | +5.5 | 31.5 | 14.8 | 74% / 91% |
| rosenthal | keyhole | 309 | 0 | -26.1 | 29.0 | 61.4 | 41% / 99% | -28.6 | 33.9 | 101.1 | 38% / 85% |
| rosenthal | transition | 78 | 0 | -39.9 | 39.9 | 73.4 | 5% / 95% | -28.7 | 34.0 | 40.4 | 49% / 83% |
| rosenthal | unclassified-missing-process-input | 0 | 626 | - | - | - | - | - | - | - | - |
| rosenthal | unclassified-source-dimensions-unresolved | 0 | 48 | - | - | - | - | - | - | - | - |
| rosenthal | common | 711 | 720 | -33.1 | 34.5 | 65.2 | 28% / 94% | -13.6 | 34.5 | 72.3 | 49% / 88% |
| eagar-tsai | all | 756 | 675 | -23.9 | 25.6 | 49.7 | 66% / 100% | -18.6 | 35.6 | 70.7 | 42% / 87% |
| eagar-tsai | balling-flagged | 216 | 0 | -25.1 | 25.7 | 48.9 | 67% / 100% | -1.3 | 37.7 | 43.8 | 48% / 92% |
| eagar-tsai | conduction | 153 | 1 | -24.9 | 25.3 | 42.1 | 69% / 100% | -13.2 | 33.0 | 15.5 | 49% / 93% |
| eagar-tsai | keyhole | 309 | 0 | -21.5 | 25.0 | 52.8 | 67% / 100% | -29.2 | 34.5 | 101.5 | 37% / 84% |
| eagar-tsai | transition | 78 | 0 | -28.2 | 28.4 | 53.1 | 56% / 100% | -35.1 | 38.9 | 43.6 | 31% / 78% |
| eagar-tsai | unclassified-missing-process-input | 0 | 626 | - | - | - | - | - | - | - | - |
| eagar-tsai | unclassified-source-dimensions-unresolved | 0 | 48 | - | - | - | - | - | - | - | - |
| eagar-tsai | common | 711 | 720 | -23.6 | 25.4 | 50.1 | 67% / 100% | -18.5 | 35.8 | 72.9 | 42% / 87% |
| goldak | all | 711 | 720 | -33.1 | 34.5 | 65.2 | 28% / 93% | -12.2 | 34.0 | 72.0 | 50% / 89% |
| goldak | balling-flagged | 212 | 4 | -35.5 | 35.9 | 65.2 | 27% / 92% | +5.2 | 36.7 | 43.2 | 54% / 93% |
| goldak | conduction | 112 | 42 | -43.5 | 43.5 | 70.1 | 7% / 77% | +8.2 | 31.9 | 14.6 | 72% / 91% |
| goldak | keyhole | 309 | 0 | -25.9 | 28.9 | 61.2 | 42% / 99% | -28.2 | 33.5 | 100.9 | 39% / 86% |
| goldak | transition | 78 | 0 | -39.9 | 39.9 | 73.2 | 5% / 94% | -25.8 | 31.8 | 38.8 | 54% / 86% |
| goldak | unclassified-missing-process-input | 0 | 626 | - | - | - | - | - | - | - | - |
| goldak | unclassified-source-dimensions-unresolved | 0 | 48 | - | - | - | - | - | - | - | - |
| goldak | common | 711 | 720 | -33.1 | 34.5 | 65.2 | 28% / 93% | -12.2 | 34.0 | 72.0 | 50% / 89% |

### Cluster-bootstrap 95 % intervals (pooled summary cells)

Distinct parameter sets (dataset, power, speed, beam diameter, layer) resampled with replacement, 1000 replicates, `random.Random(0)`, percentile 2.5/97.5; replicates of one set stay together. The intervals cover this resampling only (no measurement uncertainty, no material-law uncertainty); they are in JSON `summary.<kernel>.<regime>.<width|depth>.{bias_pct_ci95, mape_pct_ci95, n_parameterSets}`.

| kernel | regime | n | parameter sets | W bias % CI95 | W MAPE % CI95 | D bias % CI95 | D MAPE % CI95 |
|---|---|---|---|---|---|---|---|
| rosenthal | all | 718 | 669 | [-34.2, -32.2] | [33.7, 35.4] | [-16.6, -9.7] | [32.1, 37.1] |
| rosenthal | balling-flagged | 214 | 213 | [-37.2, -33.9] | [34.4, 37.5] | [-4.0, 12.3] | [31.2, 43.2] |
| rosenthal | conduction | 117 | 106 | [-45.0, -41.8] | [41.8, 45.0] | [-3.5, 16.7] | [24.2, 40.2] |
| rosenthal | keyhole | 309 | 290 | [-28.0, -24.2] | [27.8, 30.2] | [-31.2, -25.7] | [32.0, 35.9] |
| rosenthal | transition | 78 | 70 | [-41.3, -38.4] | [38.4, 41.3] | [-34.3, -22.7] | [30.2, 38.2] |
| rosenthal | common | 711 | 662 | [-34.1, -32.0] | [33.6, 35.3] | [-17.1, -10.2] | [32.1, 37.1] |
| eagar-tsai | all | 756 | 702 | [-24.8, -22.9] | [24.9, 26.2] | [-21.5, -15.6] | [33.6, 37.8] |
| eagar-tsai | balling-flagged | 216 | 215 | [-26.7, -23.6] | [24.4, 27.1] | [-8.6, 6.9] | [32.3, 44.4] |
| eagar-tsai | conduction | 153 | 137 | [-26.3, -23.3] | [24.1, 26.7] | [-19.4, -6.3] | [29.1, 37.8] |
| eagar-tsai | keyhole | 309 | 290 | [-23.3, -19.6] | [23.9, 26.1] | [-31.9, -26.4] | [32.5, 36.5] |
| eagar-tsai | transition | 78 | 70 | [-29.9, -26.5] | [26.7, 30.0] | [-40.0, -29.6] | [35.4, 42.5] |
| eagar-tsai | common | 711 | 662 | [-24.6, -22.8] | [24.7, 26.1] | [-21.7, -15.3] | [33.6, 38.0] |
| goldak | all | 711 | 662 | [-34.2, -32.0] | [33.6, 35.3] | [-15.7, -8.9] | [31.6, 36.7] |
| goldak | balling-flagged | 212 | 211 | [-37.1, -34.0] | [34.5, 37.3] | [-1.9, 13.7] | [31.1, 43.4] |
| goldak | conduction | 112 | 101 | [-45.1, -41.9] | [41.9, 45.1] | [-1.1, 19.1] | [23.7, 41.4] |
| goldak | keyhole | 309 | 290 | [-27.8, -24.0] | [27.7, 30.1] | [-30.7, -25.3] | [31.6, 35.4] |
| goldak | transition | 78 | 70 | [-41.3, -38.3] | [38.3, 41.3] | [-31.6, -19.5] | [27.8, 36.3] |
| goldak | common | 711 | 662 | [-34.2, -32.0] | [33.6, 35.3] | [-15.7, -8.9] | [31.6, 36.7] |

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
| rosenthal | all | 638 | 39 | -36.2 | 36.3 | 68.5 | 22% / 93% | -13.6 | 33.7 | 65.0 | 50% / 88% |
| rosenthal | balling-flagged | 214 | 2 | -35.5 | 35.9 | 65.3 | 27% / 92% | +4.2 | 37.1 | 43.2 | 53% / 93% |
| rosenthal | conduction | 109 | 37 | -43.9 | 43.9 | 71.5 | 6% / 77% | -1.3 | 24.2 | 13.6 | 79% / 96% |
| rosenthal | keyhole | 243 | 0 | -32.2 | 32.2 | 67.7 | 30% / 99% | -30.4 | 34.8 | 94.1 | 36% / 81% |
| rosenthal | transition | 72 | 0 | -40.0 | 40.0 | 75.4 | 3% / 96% | -28.2 | 33.9 | 41.7 | 49% / 83% |
| eagar-tsai | all | 676 | 1 | -26.2 | 26.4 | 51.8 | 64% / 100% | -19.1 | 35.2 | 63.9 | 42% / 87% |
| eagar-tsai | balling-flagged | 216 | 0 | -25.1 | 25.7 | 48.9 | 67% / 100% | -1.3 | 37.7 | 43.8 | 48% / 92% |
| eagar-tsai | conduction | 145 | 1 | -25.3 | 25.4 | 43.0 | 68% / 100% | -17.8 | 29.1 | 14.6 | 51% / 96% |
| eagar-tsai | keyhole | 243 | 0 | -27.2 | 27.2 | 57.9 | 61% / 100% | -31.1 | 35.6 | 94.5 | 35% / 79% |
| eagar-tsai | transition | 72 | 0 | -28.0 | 28.2 | 54.4 | 58% / 100% | -34.7 | 38.8 | 45.0 | 29% / 78% |
| goldak | all | 631 | 46 | -36.1 | 36.2 | 68.4 | 22% / 92% | -12.5 | 33.1 | 65.0 | 51% / 89% |
| goldak | balling-flagged | 212 | 4 | -35.5 | 35.9 | 65.2 | 27% / 92% | +5.2 | 36.7 | 43.2 | 54% / 93% |
| goldak | conduction | 104 | 42 | -44.0 | 44.0 | 72.3 | 7% / 76% | +0.9 | 23.9 | 13.3 | 77% / 96% |
| goldak | keyhole | 243 | 0 | -32.1 | 32.1 | 67.4 | 31% / 99% | -29.9 | 34.4 | 93.8 | 37% / 83% |
| goldak | transition | 72 | 0 | -39.9 | 39.9 | 75.3 | 3% / 94% | -25.2 | 31.8 | 40.1 | 54% / 86% |

### Dataset ku-leuven-316l-2021

| kernel | regime | n | excluded | W bias % | W MAPE % | W RMSE um | W within +-30% / x0.5-2 | D bias % | D MAPE % | D RMSE um | D within +-30% / x0.5-2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rosenthal | all | 44 | 0 | -20.2 | 20.3 | 30.7 | 82% / 100% | -38.5 | 39.9 | 245.5 | 25% / 57% |
| rosenthal | keyhole | 44 | 0 | -20.2 | 20.3 | 30.7 | 82% / 100% | -38.5 | 39.9 | 245.5 | 25% / 57% |
| eagar-tsai | all | 44 | 0 | -18.2 | 18.5 | 28.6 | 82% / 100% | -38.5 | 39.9 | 245.5 | 25% / 57% |
| eagar-tsai | keyhole | 44 | 0 | -18.2 | 18.5 | 28.6 | 82% / 100% | -38.5 | 39.9 | 245.5 | 25% / 57% |
| goldak | all | 44 | 0 | -20.0 | 20.2 | 30.5 | 82% / 100% | -38.5 | 39.9 | 245.5 | 25% / 57% |
| goldak | keyhole | 44 | 0 | -20.0 | 20.2 | 30.5 | 82% / 100% | -38.5 | 39.9 | 245.5 | 25% / 57% |

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
| rosenthal | all | 14 | 0 | -13.2 | 13.2 | 13.3 | 100% / 100% | +10.8 | 25.8 | 26.0 | 57% / 100% |
| rosenthal | keyhole | 14 | 0 | -13.2 | 13.2 | 13.3 | 100% / 100% | +10.8 | 25.8 | 26.0 | 57% / 100% |
| eagar-tsai | all | 14 | 0 | -10.1 | 10.3 | 10.9 | 100% / 100% | +10.8 | 25.8 | 26.0 | 57% / 100% |
| eagar-tsai | keyhole | 14 | 0 | -10.1 | 10.3 | 10.9 | 100% / 100% | +10.8 | 25.8 | 26.0 | 57% / 100% |
| goldak | all | 14 | 0 | -13.0 | 13.0 | 13.1 | 100% / 100% | +10.8 | 25.8 | 26.0 | 57% / 100% |
| goldak | keyhole | 14 | 0 | -13.0 | 13.0 | 13.1 | 100% / 100% | +10.8 | 25.8 | 26.0 | 57% / 100% |

### Dataset lane-in625-2020

| kernel | regime | n | excluded | W bias % | W MAPE % | W RMSE um | W within +-30% / x0.5-2 | D bias % | D MAPE % | D RMSE um | D within +-30% / x0.5-2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rosenthal | all | 14 | 9 | -31.2 | 31.2 | 46.2 | 43% / 100% | -33.8 | 37.8 | 52.5 | 29% / 64% |
| rosenthal | conduction | 4 | 9 | -35.9 | 35.9 | 53.5 | 0% / 100% | +7.1 | 7.1 | 3.2 | 100% / 100% |
| rosenthal | keyhole | 10 | 0 | -29.3 | 29.3 | 42.9 | 60% / 100% | -50.1 | 50.1 | 62.1 | 0% / 50% |
| eagar-tsai | all | 23 | 0 | -0.4 | 10.6 | 18.9 | 100% / 100% | -36.9 | 36.9 | 43.7 | 43% / 74% |
| eagar-tsai | conduction | 13 | 0 | +7.0 | 8.5 | 11.4 | 100% / 100% | -22.2 | 22.2 | 7.7 | 77% / 100% |
| eagar-tsai | keyhole | 10 | 0 | -10.0 | 13.3 | 25.6 | 100% / 100% | -56.1 | 56.1 | 65.7 | 0% / 40% |
| goldak | all | 10 | 13 | -29.2 | 29.2 | 42.7 | 60% / 100% | -48.3 | 48.3 | 60.4 | 0% / 70% |
| goldak | conduction | 0 | 13 | - | - | - | - | - | - | - | - |
| goldak | keyhole | 10 | 0 | -29.2 | 29.2 | 42.7 | 60% / 100% | -48.3 | 48.3 | 60.4 | 0% / 70% |

### Dataset totis-ti64-2021

| kernel | regime | n | excluded | W bias % | W MAPE % | W RMSE um | W within +-30% / x0.5-2 | D bias % | D MAPE % | D RMSE um | D within +-30% / x0.5-2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rosenthal | all | 80 | 0 | -9.6 | 20.9 | 29.3 | 71% / 99% | -10.8 | 40.9 | 112.8 | 42% / 91% |
| rosenthal | conduction | 8 | 0 | -37.2 | 37.2 | 29.2 | 12% / 100% | +98.9 | 131.3 | 26.4 | 12% / 25% |
| rosenthal | keyhole | 66 | 0 | -3.6 | 17.2 | 28.0 | 82% / 100% | -21.8 | 30.4 | 123.7 | 45% / 100% |
| rosenthal | transition | 6 | 0 | -39.3 | 39.3 | 41.2 | 33% / 83% | -35.3 | 35.3 | 19.1 | 50% / 83% |
| eagar-tsai | all | 80 | 0 | -4.6 | 18.5 | 26.8 | 84% / 100% | -14.1 | 38.7 | 112.8 | 42% / 91% |
| eagar-tsai | conduction | 8 | 0 | -17.3 | 24.4 | 19.0 | 88% / 100% | +70.6 | 104.3 | 26.8 | 12% / 38% |
| eagar-tsai | keyhole | 66 | 0 | -0.7 | 16.7 | 26.9 | 88% / 100% | -22.0 | 30.6 | 123.7 | 45% / 98% |
| eagar-tsai | transition | 6 | 0 | -30.9 | 30.9 | 33.4 | 33% / 100% | -39.9 | 39.9 | 21.0 | 50% / 83% |
| goldak | all | 80 | 0 | -9.6 | 20.9 | 29.3 | 71% / 98% | -10.0 | 41.1 | 112.8 | 42% / 91% |
| goldak | conduction | 8 | 0 | -37.6 | 37.6 | 29.3 | 12% / 88% | +104.1 | 135.8 | 26.1 | 12% / 25% |
| goldak | keyhole | 66 | 0 | -3.5 | 17.2 | 27.9 | 82% / 100% | -21.8 | 30.3 | 123.7 | 45% / 100% |
| goldak | transition | 6 | 0 | -39.2 | 39.2 | 41.3 | 33% / 83% | -32.9 | 32.9 | 18.3 | 50% / 83% |

### Hofmann, spot 50 um

| kernel | regime | n | excluded | W bias % | W MAPE % | W RMSE um | W within +-30% / x0.5-2 | D bias % | D MAPE % | D RMSE um | D within +-30% / x0.5-2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rosenthal | all | 175 | 0 | -30.9 | 31.4 | 40.9 | 39% / 97% | -11.8 | 39.1 | 63.9 | 43% / 87% |
| rosenthal | balling-flagged | 74 | 0 | -27.7 | 28.9 | 43.7 | 51% / 97% | +9.3 | 50.6 | 66.0 | 32% / 88% |
| rosenthal | conduction | 14 | 0 | -37.2 | 37.2 | 28.8 | 14% / 93% | -13.9 | 25.0 | 9.7 | 86% / 93% |
| rosenthal | keyhole | 77 | 0 | -31.5 | 31.5 | 40.2 | 38% / 97% | -28.3 | 30.8 | 70.6 | 47% / 88% |
| rosenthal | transition | 10 | 0 | -40.3 | 40.3 | 39.4 | 0% / 100% | -37.7 | 37.7 | 26.3 | 30% / 60% |
| eagar-tsai | all | 175 | 0 | -25.4 | 26.0 | 36.2 | 63% / 99% | -13.0 | 40.1 | 64.0 | 38% / 86% |
| eagar-tsai | balling-flagged | 74 | 0 | -24.0 | 25.5 | 40.3 | 66% / 100% | +9.2 | 50.7 | 66.0 | 31% / 88% |
| eagar-tsai | conduction | 14 | 0 | -19.4 | 19.7 | 17.7 | 86% / 100% | -21.7 | 29.8 | 10.9 | 50% / 93% |
| eagar-tsai | keyhole | 77 | 0 | -27.2 | 27.2 | 35.3 | 58% / 99% | -28.9 | 31.5 | 70.6 | 44% / 87% |
| eagar-tsai | transition | 10 | 0 | -30.1 | 30.1 | 30.6 | 40% / 100% | -42.2 | 42.2 | 27.7 | 20% / 60% |
| goldak | all | 175 | 0 | -30.7 | 31.2 | 40.7 | 39% / 97% | -11.2 | 38.7 | 63.8 | 43% / 88% |
| goldak | balling-flagged | 74 | 0 | -27.6 | 28.8 | 43.6 | 51% / 97% | +9.3 | 50.6 | 66.0 | 32% / 88% |
| goldak | conduction | 14 | 0 | -37.0 | 37.0 | 28.5 | 14% / 93% | -10.6 | 23.4 | 9.2 | 79% / 93% |
| goldak | keyhole | 77 | 0 | -31.3 | 31.3 | 40.0 | 38% / 97% | -27.9 | 30.4 | 70.5 | 48% / 88% |
| goldak | transition | 10 | 0 | -40.1 | 40.1 | 39.2 | 0% / 100% | -35.2 | 35.2 | 25.4 | 30% / 80% |

### Hofmann, spot 80 um

| kernel | regime | n | excluded | W bias % | W MAPE % | W RMSE um | W within +-30% / x0.5-2 | D bias % | D MAPE % | D RMSE um | D within +-30% / x0.5-2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rosenthal | all | 182 | 5 | -35.2 | 35.2 | 58.9 | 26% / 92% | -12.7 | 33.2 | 69.4 | 48% / 90% |
| rosenthal | balling-flagged | 59 | 0 | -36.9 | 36.9 | 63.2 | 20% / 88% | +5.3 | 33.4 | 26.0 | 58% / 93% |
| rosenthal | conduction | 28 | 5 | -42.7 | 42.7 | 50.7 | 11% / 79% | -0.6 | 26.7 | 9.4 | 75% / 96% |
| rosenthal | keyhole | 79 | 0 | -30.2 | 30.2 | 58.5 | 41% / 100% | -26.7 | 35.3 | 102.0 | 33% / 86% |
| rosenthal | transition | 16 | 0 | -40.9 | 40.9 | 57.9 | 0% / 94% | -31.4 | 33.4 | 27.2 | 44% / 88% |
| eagar-tsai | all | 187 | 0 | -26.4 | 26.5 | 48.1 | 63% / 99% | -17.2 | 34.4 | 68.8 | 42% / 88% |
| eagar-tsai | balling-flagged | 59 | 0 | -27.7 | 27.8 | 53.4 | 61% / 98% | +1.4 | 34.3 | 26.8 | 59% / 92% |
| eagar-tsai | conduction | 33 | 0 | -25.3 | 25.3 | 31.0 | 67% / 100% | -16.4 | 29.2 | 10.7 | 45% / 94% |
| eagar-tsai | keyhole | 79 | 0 | -25.6 | 25.7 | 50.8 | 63% / 100% | -27.2 | 35.8 | 102.2 | 33% / 84% |
| eagar-tsai | transition | 16 | 0 | -28.3 | 28.3 | 41.9 | 56% / 100% | -37.9 | 38.6 | 29.9 | 12% / 88% |
| goldak | all | 181 | 6 | -35.1 | 35.2 | 58.9 | 27% / 93% | -11.4 | 32.8 | 69.4 | 50% / 91% |
| goldak | balling-flagged | 59 | 0 | -37.1 | 37.1 | 63.5 | 20% / 90% | +6.7 | 33.0 | 25.7 | 59% / 93% |
| goldak | conduction | 27 | 6 | -42.7 | 42.7 | 50.9 | 15% / 81% | +3.1 | 27.4 | 9.3 | 74% / 96% |
| goldak | keyhole | 79 | 0 | -30.0 | 30.1 | 58.1 | 42% / 100% | -26.3 | 35.0 | 101.8 | 34% / 89% |
| goldak | transition | 16 | 0 | -40.8 | 40.8 | 57.8 | 0% / 88% | -28.5 | 31.2 | 25.9 | 56% / 88% |

### Hofmann, spot 110 um

| kernel | regime | n | excluded | W bias % | W MAPE % | W RMSE um | W within +-30% / x0.5-2 | D bias % | D MAPE % | D RMSE um | D within +-30% / x0.5-2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rosenthal | all | 150 | 11 | -39.1 | 39.1 | 77.6 | 11% / 92% | -15.3 | 30.8 | 59.1 | 59% / 90% |
| rosenthal | balling-flagged | 43 | 2 | -40.8 | 40.8 | 74.1 | 14% / 93% | -0.0 | 30.9 | 19.5 | 67% / 98% |
| rosenthal | conduction | 28 | 9 | -44.9 | 44.9 | 69.1 | 4% / 75% | -4.5 | 21.5 | 14.9 | 86% / 96% |
| rosenthal | keyhole | 56 | 0 | -34.3 | 34.3 | 82.7 | 16% / 100% | -31.3 | 33.9 | 91.1 | 38% / 82% |
| rosenthal | transition | 23 | 0 | -40.7 | 40.7 | 80.9 | 4% / 91% | -18.1 | 34.6 | 39.7 | 61% / 87% |
| eagar-tsai | all | 161 | 0 | -26.9 | 27.0 | 57.8 | 64% / 100% | -22.2 | 32.9 | 58.1 | 43% / 88% |
| eagar-tsai | balling-flagged | 45 | 0 | -25.1 | 25.1 | 50.9 | 73% / 100% | -8.6 | 32.0 | 21.6 | 49% / 96% |
| eagar-tsai | conduction | 37 | 0 | -25.2 | 25.5 | 40.2 | 68% / 100% | -21.6 | 28.0 | 16.0 | 49% / 97% |
| eagar-tsai | keyhole | 56 | 0 | -28.6 | 28.6 | 70.6 | 59% / 100% | -32.2 | 34.8 | 91.7 | 36% / 80% |
| eagar-tsai | transition | 23 | 0 | -28.9 | 29.3 | 59.9 | 52% / 100% | -25.7 | 38.3 | 42.6 | 39% / 78% |
| goldak | all | 148 | 13 | -39.1 | 39.1 | 77.9 | 11% / 91% | -14.1 | 29.8 | 59.0 | 59% / 89% |
| goldak | balling-flagged | 43 | 2 | -41.1 | 41.1 | 74.4 | 14% / 91% | +2.5 | 30.3 | 18.8 | 70% / 98% |
| goldak | conduction | 26 | 11 | -45.2 | 45.2 | 70.3 | 4% / 69% | -5.2 | 18.5 | 14.6 | 85% / 96% |
| goldak | keyhole | 56 | 0 | -34.2 | 34.2 | 82.4 | 16% / 100% | -30.7 | 33.3 | 90.7 | 38% / 82% |
| goldak | transition | 23 | 0 | -40.6 | 40.6 | 80.8 | 4% / 91% | -14.7 | 33.0 | 38.3 | 61% / 83% |

### Hofmann, spot 140 um

| kernel | regime | n | excluded | W bias % | W MAPE % | W RMSE um | W within +-30% / x0.5-2 | D bias % | D MAPE % | D RMSE um | D within +-30% / x0.5-2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rosenthal | all | 131 | 23 | -41.3 | 41.3 | 94.3 | 5% / 88% | -15.2 | 30.4 | 66.6 | 54% / 85% |
| rosenthal | balling-flagged | 38 | 0 | -42.8 | 42.8 | 88.6 | 3% / 87% | -2.5 | 23.6 | 23.5 | 68% / 97% |
| rosenthal | conduction | 39 | 23 | -46.3 | 46.3 | 93.4 | 0% / 72% | +4.9 | 24.1 | 16.0 | 74% / 97% |
| rosenthal | keyhole | 31 | 0 | -35.4 | 35.4 | 104.2 | 13% / 100% | -43.5 | 45.4 | 124.5 | 16% / 52% |
| rosenthal | transition | 23 | 0 | -38.6 | 38.6 | 90.8 | 4% / 100% | -31.9 | 32.0 | 55.2 | 48% / 87% |
| eagar-tsai | all | 153 | 1 | -26.2 | 26.2 | 63.3 | 68% / 100% | -25.2 | 33.0 | 63.5 | 46% / 84% |
| eagar-tsai | balling-flagged | 38 | 0 | -23.4 | 23.4 | 54.3 | 71% / 100% | -17.3 | 24.2 | 26.9 | 63% / 97% |
| eagar-tsai | conduction | 61 | 1 | -26.7 | 26.7 | 53.2 | 64% / 100% | -15.3 | 29.6 | 16.2 | 56% / 97% |
| eagar-tsai | keyhole | 31 | 0 | -28.8 | 28.8 | 87.2 | 68% / 100% | -44.8 | 46.7 | 126.0 | 16% / 48% |
| eagar-tsai | transition | 23 | 0 | -26.0 | 26.0 | 63.6 | 74% / 100% | -38.1 | 38.1 | 59.7 | 35% / 78% |
| goldak | all | 127 | 27 | -41.2 | 41.2 | 94.8 | 5% / 87% | -14.1 | 29.9 | 66.8 | 55% / 86% |
| goldak | balling-flagged | 36 | 2 | -42.5 | 42.5 | 88.8 | 3% / 83% | -2.3 | 22.1 | 22.9 | 69% / 97% |
| goldak | conduction | 37 | 25 | -46.7 | 46.7 | 94.9 | 0% / 70% | +7.8 | 25.3 | 15.9 | 73% / 97% |
| goldak | keyhole | 31 | 0 | -35.3 | 35.3 | 103.9 | 13% / 100% | -42.7 | 44.6 | 123.6 | 16% / 55% |
| goldak | transition | 23 | 0 | -38.5 | 38.5 | 90.7 | 4% / 100% | -29.0 | 29.5 | 53.0 | 57% / 91% |

**Powder-layer breakdowns below:** the kernels ignore powder-layer thickness (identical predictions at 0/30/60 um, see `assumptions.layer_um`), so any trend with powder-layer thickness in these tables is in the measurements only, not a kernel result.

### Hofmann, powder layer 0 um

| kernel | regime | n | excluded | W bias % | W MAPE % | W RMSE um | W within +-30% / x0.5-2 | D bias % | D MAPE % | D RMSE um | D within +-30% / x0.5-2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rosenthal | all | 183 | 27 | -39.1 | 39.1 | 70.4 | 14% / 86% | -15.1 | 25.0 | 39.9 | 68% / 99% |
| rosenthal | balling-flagged | 38 | 0 | -38.9 | 38.9 | 69.1 | 18% / 92% | -6.4 | 27.5 | 25.9 | 63% / 100% |
| rosenthal | conduction | 52 | 27 | -45.9 | 45.9 | 73.1 | 0% / 63% | -13.6 | 17.7 | 8.3 | 98% / 100% |
| rosenthal | keyhole | 69 | 0 | -33.7 | 33.7 | 68.0 | 26% / 97% | -19.3 | 28.5 | 60.9 | 48% / 99% |
| rosenthal | transition | 24 | 0 | -40.6 | 40.6 | 72.8 | 4% / 92% | -19.6 | 26.5 | 17.2 | 67% / 100% |
| eagar-tsai | all | 209 | 1 | -28.1 | 28.2 | 52.4 | 56% / 100% | -22.8 | 30.9 | 38.5 | 41% / 98% |
| eagar-tsai | balling-flagged | 38 | 0 | -30.3 | 30.3 | 54.9 | 53% / 100% | -9.8 | 30.9 | 27.6 | 45% / 100% |
| eagar-tsai | conduction | 78 | 1 | -26.8 | 26.9 | 44.0 | 62% / 100% | -29.8 | 31.5 | 12.1 | 37% / 97% |
| eagar-tsai | keyhole | 69 | 0 | -28.8 | 28.8 | 59.3 | 52% / 99% | -20.4 | 29.6 | 61.3 | 45% / 97% |
| eagar-tsai | transition | 24 | 0 | -27.2 | 27.6 | 51.9 | 58% / 100% | -27.8 | 33.2 | 21.0 | 38% / 100% |
| goldak | all | 179 | 31 | -39.0 | 39.0 | 70.4 | 15% / 85% | -13.7 | 24.1 | 40.1 | 70% / 99% |
| goldak | balling-flagged | 38 | 0 | -38.9 | 38.9 | 69.2 | 18% / 89% | -5.4 | 26.5 | 25.4 | 71% / 100% |
| goldak | conduction | 48 | 31 | -45.9 | 45.9 | 73.8 | 0% / 65% | -11.7 | 16.8 | 7.9 | 98% / 100% |
| goldak | keyhole | 69 | 0 | -33.6 | 33.6 | 67.8 | 28% / 97% | -18.8 | 28.0 | 60.7 | 48% / 99% |
| goldak | transition | 24 | 0 | -40.5 | 40.5 | 72.7 | 4% / 88% | -16.3 | 23.8 | 15.7 | 79% / 100% |

### Hofmann, powder layer 30 um

| kernel | regime | n | excluded | W bias % | W MAPE % | W RMSE um | W within +-30% / x0.5-2 | D bias % | D MAPE % | D RMSE um | D within +-30% / x0.5-2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rosenthal | all | 220 | 12 | -36.7 | 37.1 | 69.3 | 20% / 92% | -11.9 | 35.5 | 68.3 | 46% / 83% |
| rosenthal | balling-flagged | 89 | 2 | -36.3 | 37.2 | 70.3 | 21% / 87% | +2.1 | 34.0 | 44.9 | 55% / 93% |
| rosenthal | conduction | 38 | 10 | -43.2 | 43.2 | 70.3 | 8% / 84% | +18.5 | 32.4 | 13.0 | 61% / 92% |
| rosenthal | keyhole | 70 | 0 | -32.9 | 32.9 | 64.2 | 30% / 100% | -38.9 | 38.9 | 104.2 | 26% / 69% |
| rosenthal | transition | 23 | 0 | -39.4 | 39.4 | 77.9 | 0% / 100% | -34.8 | 36.2 | 59.2 | 48% / 74% |
| eagar-tsai | all | 232 | 0 | -25.5 | 26.0 | 51.0 | 66% / 100% | -17.6 | 34.7 | 67.3 | 47% / 81% |
| eagar-tsai | balling-flagged | 91 | 0 | -24.0 | 25.3 | 51.5 | 65% / 99% | -4.9 | 34.3 | 45.2 | 54% / 91% |
| eagar-tsai | conduction | 48 | 0 | -24.3 | 24.4 | 42.5 | 69% / 100% | +1.4 | 25.3 | 11.8 | 75% / 94% |
| eagar-tsai | keyhole | 70 | 0 | -27.5 | 27.5 | 53.9 | 66% / 100% | -39.7 | 39.7 | 104.8 | 24% / 64% |
| eagar-tsai | transition | 23 | 0 | -27.6 | 27.6 | 56.4 | 70% / 100% | -40.5 | 41.0 | 62.7 | 30% / 65% |
| goldak | all | 217 | 15 | -36.7 | 37.1 | 69.3 | 20% / 91% | -11.4 | 34.9 | 68.4 | 46% / 84% |
| goldak | balling-flagged | 87 | 4 | -36.1 | 37.1 | 70.1 | 22% / 86% | +2.5 | 33.3 | 45.1 | 55% / 93% |
| goldak | conduction | 37 | 11 | -43.6 | 43.6 | 71.7 | 8% / 78% | +19.9 | 32.4 | 13.0 | 57% / 92% |
| goldak | keyhole | 70 | 0 | -32.7 | 32.7 | 63.9 | 30% / 100% | -38.4 | 38.5 | 103.9 | 27% / 70% |
| goldak | transition | 23 | 0 | -39.4 | 39.4 | 77.8 | 0% / 100% | -32.1 | 33.9 | 57.4 | 48% / 78% |

### Hofmann, powder layer 60 um

| kernel | regime | n | excluded | W bias % | W MAPE % | W RMSE um | W within +-30% / x0.5-2 | D bias % | D MAPE % | D RMSE um | D within +-30% / x0.5-2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rosenthal | all | 235 | 0 | -33.4 | 33.4 | 66.2 | 30% / 99% | -13.9 | 38.7 | 76.5 | 41% / 84% |
| rosenthal | balling-flagged | 87 | 0 | -33.4 | 33.4 | 57.7 | 36% / 98% | +11.0 | 44.5 | 47.4 | 46% / 90% |
| rosenthal | conduction | 19 | 0 | -39.6 | 39.6 | 69.4 | 16% / 100% | -7.7 | 25.5 | 22.9 | 63% / 95% |
| rosenthal | keyhole | 104 | 0 | -30.7 | 30.8 | 69.8 | 34% / 100% | -32.0 | 36.3 | 104.4 | 36% / 79% |
| rosenthal | transition | 25 | 0 | -40.0 | 40.0 | 75.6 | 4% / 96% | -30.3 | 39.0 | 38.7 | 32% / 76% |
| eagar-tsai | all | 235 | 0 | -25.2 | 25.3 | 52.0 | 69% / 100% | -17.3 | 39.5 | 77.2 | 38% / 83% |
| eagar-tsai | balling-flagged | 87 | 0 | -24.0 | 24.0 | 43.1 | 76% / 100% | +6.1 | 44.2 | 47.8 | 44% / 90% |
| eagar-tsai | conduction | 19 | 0 | -21.7 | 21.7 | 40.2 | 89% / 100% | -16.9 | 28.9 | 25.9 | 47% / 95% |
| eagar-tsai | keyhole | 104 | 0 | -25.9 | 26.0 | 59.5 | 64% / 100% | -32.6 | 36.9 | 104.9 | 36% / 78% |
| eagar-tsai | transition | 25 | 0 | -29.2 | 29.2 | 54.9 | 48% / 100% | -35.9 | 42.3 | 42.2 | 20% / 68% |
| goldak | all | 235 | 0 | -33.3 | 33.3 | 66.1 | 30% / 99% | -12.6 | 38.4 | 76.2 | 42% / 85% |
| goldak | balling-flagged | 87 | 0 | -33.4 | 33.4 | 57.8 | 36% / 98% | +12.6 | 44.7 | 47.2 | 45% / 90% |
| goldak | conduction | 19 | 0 | -39.5 | 39.5 | 69.4 | 21% / 100% | -4.2 | 25.3 | 22.0 | 63% / 95% |
| goldak | keyhole | 104 | 0 | -30.6 | 30.6 | 69.4 | 34% / 100% | -31.6 | 35.9 | 104.1 | 37% / 81% |
| goldak | transition | 25 | 0 | -39.9 | 39.9 | 75.4 | 4% / 96% | -27.4 | 37.4 | 36.9 | 36% / 80% |

## Absorptivity sensitivity (SENSITIVITY, not a calibration)

SENSITIVITY, not a calibrated value: conduction-regime rows (regime assigned at the repo's default absorptivity), absorptivity_IR overridden uniformly via prop_overrides; the absorptivity actually acting in a physical track is unknown.

Conduction rows: 154.

| kernel | a=0.30 W MAPE % | a=0.40 W MAPE % | a=0.50 W MAPE % | a=0.60 W MAPE % | a=0.30 D MAPE % | a=0.40 D MAPE % | a=0.50 D MAPE % | a=0.60 D MAPE % | a=0.30 n | a=0.40 n | a=0.50 n | a=0.60 n |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| rosenthal | 43.6 | 34.7 | 26.9 | 20.5 | 31.0 | 34.8 | 48.5 | 63.3 | 117 | 141 | 150 | 152 |
| eagar-tsai | 25.4 | 17.6 | 12.7 | 10.6 | 32.6 | 28.9 | 35.1 | 48.9 | 153 | 154 | 154 | 154 |
| goldak | 43.7 | 34.3 | 26.6 | 20.5 | 31.2 | 37.6 | 52.4 | 68.8 | 112 | 136 | 146 | 150 |

Included row counts vary with assumed absorptivity: each column uses only rows where the kernel resolves an extent. These are different evaluation subsets; lower width error can accompany higher depth error. Sensitivity, not calibration.

## Wave 2 datasets (2026-10-06)

Wave 2 (2026-10-06): new open measured datasets run through the unchanged screening kernels; comparison, not validation. Per-dataset kernel x regime tables (regime = the repo's screening classifier) with cluster-bootstrap intervals:

### Wave 2 scorecard: ku-leuven-316l-2021

| kernel | regime | n | excluded | W bias % | W MAPE % | W RMSE um | W within +-30% / x0.5-2 | D bias % | D MAPE % | D RMSE um | D within +-30% / x0.5-2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rosenthal | all | 44 | 0 | -20.2 | 20.3 | 30.7 | 82% / 100% | -38.5 | 39.9 | 245.5 | 25% / 57% |
| rosenthal | keyhole | 44 | 0 | -20.2 | 20.3 | 30.7 | 82% / 100% | -38.5 | 39.9 | 245.5 | 25% / 57% |
| rosenthal | common | 44 | 0 | -20.2 | 20.3 | 30.7 | 82% / 100% | -38.5 | 39.9 | 245.5 | 25% / 57% |
| eagar-tsai | all | 44 | 0 | -18.2 | 18.5 | 28.6 | 82% / 100% | -38.5 | 39.9 | 245.5 | 25% / 57% |
| eagar-tsai | keyhole | 44 | 0 | -18.2 | 18.5 | 28.6 | 82% / 100% | -38.5 | 39.9 | 245.5 | 25% / 57% |
| eagar-tsai | common | 44 | 0 | -18.2 | 18.5 | 28.6 | 82% / 100% | -38.5 | 39.9 | 245.5 | 25% / 57% |
| goldak | all | 44 | 0 | -20.0 | 20.2 | 30.5 | 82% / 100% | -38.5 | 39.9 | 245.5 | 25% / 57% |
| goldak | keyhole | 44 | 0 | -20.0 | 20.2 | 30.5 | 82% / 100% | -38.5 | 39.9 | 245.5 | 25% / 57% |
| goldak | common | 44 | 0 | -20.0 | 20.2 | 30.5 | 82% / 100% | -38.5 | 39.9 | 245.5 | 25% / 57% |

| kernel | regime | n | parameter sets | W bias % CI95 | W MAPE % CI95 | D bias % CI95 | D MAPE % CI95 |
|---|---|---|---|---|---|---|---|
| rosenthal | all | 44 | 44 | [-23.7, -16.7] | [16.9, 23.8] | [-44.2, -32.2] | [34.2, 44.6] |
| rosenthal | keyhole | 44 | 44 | [-23.7, -16.7] | [16.9, 23.8] | [-44.2, -32.2] | [34.2, 44.6] |
| rosenthal | common | 44 | 44 | [-23.7, -16.7] | [16.9, 23.8] | [-44.2, -32.2] | [34.2, 44.6] |
| eagar-tsai | all | 44 | 44 | [-21.5, -15.0] | [15.3, 21.7] | [-44.2, -32.2] | [34.2, 44.6] |
| eagar-tsai | keyhole | 44 | 44 | [-21.5, -15.0] | [15.3, 21.7] | [-44.2, -32.2] | [34.2, 44.6] |
| eagar-tsai | common | 44 | 44 | [-21.5, -15.0] | [15.3, 21.7] | [-44.2, -32.2] | [34.2, 44.6] |
| goldak | all | 44 | 44 | [-23.5, -16.5] | [16.7, 23.6] | [-44.2, -32.2] | [34.2, 44.6] |
| goldak | keyhole | 44 | 44 | [-23.5, -16.5] | [16.7, 23.6] | [-44.2, -32.2] | [34.2, 44.6] |
| goldak | common | 44 | 44 | [-23.5, -16.5] | [16.7, 23.6] | [-44.2, -32.2] | [34.2, 44.6] |

### Wave 2 scorecard: ku-leuven-ti64-2021

| kernel | regime | n | excluded | W bias % | W MAPE % | W RMSE um | W within +-30% / x0.5-2 | D bias % | D MAPE % | D RMSE um | D within +-30% / x0.5-2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rosenthal | all | 14 | 0 | -13.2 | 13.2 | 13.3 | 100% / 100% | +10.8 | 25.8 | 26.0 | 57% / 100% |
| rosenthal | keyhole | 14 | 0 | -13.2 | 13.2 | 13.3 | 100% / 100% | +10.8 | 25.8 | 26.0 | 57% / 100% |
| rosenthal | common | 14 | 0 | -13.2 | 13.2 | 13.3 | 100% / 100% | +10.8 | 25.8 | 26.0 | 57% / 100% |
| eagar-tsai | all | 14 | 0 | -10.1 | 10.3 | 10.9 | 100% / 100% | +10.8 | 25.8 | 26.0 | 57% / 100% |
| eagar-tsai | keyhole | 14 | 0 | -10.1 | 10.3 | 10.9 | 100% / 100% | +10.8 | 25.8 | 26.0 | 57% / 100% |
| eagar-tsai | common | 14 | 0 | -10.1 | 10.3 | 10.9 | 100% / 100% | +10.8 | 25.8 | 26.0 | 57% / 100% |
| goldak | all | 14 | 0 | -13.0 | 13.0 | 13.1 | 100% / 100% | +10.8 | 25.8 | 26.0 | 57% / 100% |
| goldak | keyhole | 14 | 0 | -13.0 | 13.0 | 13.1 | 100% / 100% | +10.8 | 25.8 | 26.0 | 57% / 100% |
| goldak | common | 14 | 0 | -13.0 | 13.0 | 13.1 | 100% / 100% | +10.8 | 25.8 | 26.0 | 57% / 100% |

| kernel | regime | n | parameter sets | W bias % CI95 | W MAPE % CI95 | D bias % CI95 | D MAPE % CI95 |
|---|---|---|---|---|---|---|---|
| rosenthal | all | 14 | 14 | [-16.0, -10.0] | [10.0, 16.0] | [-3.9, 25.3] | [18.1, 33.9] |
| rosenthal | keyhole | 14 | 14 | [-16.0, -10.0] | [10.0, 16.0] | [-3.9, 25.3] | [18.1, 33.9] |
| rosenthal | common | 14 | 14 | [-16.0, -10.0] | [10.0, 16.0] | [-3.9, 25.3] | [18.1, 33.9] |
| eagar-tsai | all | 14 | 14 | [-12.9, -7.2] | [7.6, 12.9] | [-3.9, 25.3] | [18.1, 33.9] |
| eagar-tsai | keyhole | 14 | 14 | [-12.9, -7.2] | [7.6, 12.9] | [-3.9, 25.3] | [18.1, 33.9] |
| eagar-tsai | common | 14 | 14 | [-12.9, -7.2] | [7.6, 12.9] | [-3.9, 25.3] | [18.1, 33.9] |
| goldak | all | 14 | 14 | [-15.9, -9.9] | [9.9, 15.9] | [-3.9, 25.3] | [18.1, 33.9] |
| goldak | keyhole | 14 | 14 | [-15.9, -9.9] | [9.9, 15.9] | [-3.9, 25.3] | [18.1, 33.9] |
| goldak | common | 14 | 14 | [-15.9, -9.9] | [9.9, 15.9] | [-3.9, 25.3] | [18.1, 33.9] |

### Wave 2 scorecard: lane-in625-2020

| kernel | regime | n | excluded | W bias % | W MAPE % | W RMSE um | W within +-30% / x0.5-2 | D bias % | D MAPE % | D RMSE um | D within +-30% / x0.5-2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rosenthal | all | 14 | 9 | -31.2 | 31.2 | 46.2 | 43% / 100% | -33.8 | 37.8 | 52.5 | 29% / 64% |
| rosenthal | conduction | 4 | 9 | -35.9 | 35.9 | 53.5 | 0% / 100% | +7.1 | 7.1 | 3.2 | 100% / 100% |
| rosenthal | keyhole | 10 | 0 | -29.3 | 29.3 | 42.9 | 60% / 100% | -50.1 | 50.1 | 62.1 | 0% / 50% |
| rosenthal | common | 10 | 13 | -29.3 | 29.3 | 42.9 | 60% / 100% | -50.1 | 50.1 | 62.1 | 0% / 50% |
| eagar-tsai | all | 23 | 0 | -0.4 | 10.6 | 18.9 | 100% / 100% | -36.9 | 36.9 | 43.7 | 43% / 74% |
| eagar-tsai | conduction | 13 | 0 | +7.0 | 8.5 | 11.4 | 100% / 100% | -22.2 | 22.2 | 7.7 | 77% / 100% |
| eagar-tsai | keyhole | 10 | 0 | -10.0 | 13.3 | 25.6 | 100% / 100% | -56.1 | 56.1 | 65.7 | 0% / 40% |
| eagar-tsai | common | 10 | 13 | -10.0 | 13.3 | 25.6 | 100% / 100% | -56.1 | 56.1 | 65.7 | 0% / 40% |
| goldak | all | 10 | 13 | -29.2 | 29.2 | 42.7 | 60% / 100% | -48.3 | 48.3 | 60.4 | 0% / 70% |
| goldak | conduction | 0 | 13 | - | - | - | - | - | - | - | - |
| goldak | keyhole | 10 | 0 | -29.2 | 29.2 | 42.7 | 60% / 100% | -48.3 | 48.3 | 60.4 | 0% / 70% |
| goldak | common | 10 | 13 | -29.2 | 29.2 | 42.7 | 60% / 100% | -48.3 | 48.3 | 60.4 | 0% / 70% |

| kernel | regime | n | parameter sets | W bias % CI95 | W MAPE % CI95 | D bias % CI95 | D MAPE % CI95 |
|---|---|---|---|---|---|---|---|
| rosenthal | all | 14 | 4 | [-35.9, -26.2] | [26.2, 35.9] | [-57.7, -4.5] | [15.8, 57.7] |
| rosenthal | conduction | 4 | 1 | [-35.9, -35.9] | [35.9, 35.9] | [7.1, 7.1] | [7.1, 7.1] |
| rosenthal | keyhole | 10 | 3 | [-35.8, -23.7] | [23.7, 35.8] | [-64.4, -38.8] | [38.8, 64.4] |
| rosenthal | common | 10 | 3 | [-35.8, -23.7] | [23.7, 35.8] | [-64.4, -38.8] | [38.8, 64.4] |
| eagar-tsai | all | 23 | 6 | [-12.4, 8.0] | [5.5, 16.5] | [-52.1, -23.4] | [23.4, 52.1] |
| eagar-tsai | conduction | 13 | 3 | [-2.2, 13.0] | [2.8, 13.0] | [-31.1, -13.1] | [13.1, 31.1] |
| eagar-tsai | keyhole | 10 | 3 | [-24.9, 4.2] | [4.2, 24.9] | [-66.8, -48.2] | [48.2, 66.8] |
| eagar-tsai | common | 10 | 3 | [-24.9, 4.2] | [4.2, 24.9] | [-66.8, -48.2] | [48.2, 66.8] |
| goldak | all | 10 | 3 | [-35.5, -23.8] | [23.8, 35.5] | [-62.9, -37.0] | [37.0, 62.9] |
| goldak | keyhole | 10 | 3 | [-35.5, -23.8] | [23.8, 35.5] | [-62.9, -37.0] | [37.0, 62.9] |
| goldak | common | 10 | 3 | [-35.5, -23.8] | [23.8, 35.5] | [-62.9, -37.0] | [37.0, 62.9] |

### SENSITIVITY on an unresolved input, not a fit: KU Leuven rows re-run with beam diameter 75 um (the 37.5 um value read as a radius)

### ku-leuven-316l-2021 at beam diameter 75 um

| kernel | regime | n | excluded | W bias % | W MAPE % | W RMSE um | W within +-30% / x0.5-2 | D bias % | D MAPE % | D RMSE um | D within +-30% / x0.5-2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rosenthal | all | 44 | 0 | -21.3 | 21.4 | 31.8 | 73% / 100% | -67.9 | 67.9 | 339.0 | 2% / 11% |
| rosenthal | conduction | 8 | 0 | -33.7 | 33.7 | 32.0 | 25% / 100% | -51.5 | 51.5 | 46.5 | 12% / 62% |
| rosenthal | keyhole | 32 | 0 | -15.5 | 15.6 | 27.1 | 94% / 100% | -72.2 | 72.2 | 395.8 | 0% / 0% |
| rosenthal | transition | 4 | 0 | -42.8 | 42.8 | 56.7 | 0% / 100% | -66.6 | 66.6 | 80.1 | 0% / 0% |
| rosenthal | common | 44 | 0 | -21.3 | 21.4 | 31.8 | 73% / 100% | -67.9 | 67.9 | 339.0 | 2% / 11% |
| eagar-tsai | all | 44 | 0 | -12.4 | 13.6 | 23.1 | 93% / 100% | -69.5 | 69.5 | 339.2 | 0% / 2% |
| eagar-tsai | conduction | 8 | 0 | -9.3 | 12.3 | 15.9 | 100% / 100% | -58.3 | 58.3 | 49.1 | 0% / 12% |
| eagar-tsai | keyhole | 32 | 0 | -10.7 | 11.6 | 21.1 | 100% / 100% | -72.3 | 72.3 | 395.9 | 0% / 0% |
| eagar-tsai | transition | 4 | 0 | -31.8 | 31.8 | 42.5 | 25% / 100% | -69.7 | 69.7 | 83.3 | 0% / 0% |
| eagar-tsai | common | 44 | 0 | -12.4 | 13.6 | 23.1 | 93% / 100% | -69.5 | 69.5 | 339.2 | 0% / 2% |
| goldak | all | 44 | 0 | -21.4 | 21.5 | 31.8 | 73% / 100% | -67.6 | 67.6 | 338.9 | 2% / 9% |
| goldak | conduction | 8 | 0 | -35.0 | 35.0 | 32.5 | 25% / 100% | -50.7 | 50.7 | 45.6 | 12% / 50% |
| goldak | keyhole | 32 | 0 | -15.3 | 15.5 | 26.9 | 94% / 100% | -72.1 | 72.1 | 395.8 | 0% / 0% |
| goldak | transition | 4 | 0 | -42.9 | 42.9 | 56.9 | 0% / 100% | -65.2 | 65.2 | 78.6 | 0% / 0% |
| goldak | common | 44 | 0 | -21.4 | 21.5 | 31.8 | 73% / 100% | -67.6 | 67.6 | 338.9 | 2% / 9% |

### ku-leuven-ti64-2021 at beam diameter 75 um

| kernel | regime | n | excluded | W bias % | W MAPE % | W RMSE um | W within +-30% / x0.5-2 | D bias % | D MAPE % | D RMSE um | D within +-30% / x0.5-2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rosenthal | all | 14 | 0 | -14.5 | 14.5 | 14.4 | 100% / 100% | -43.9 | 44.7 | 73.9 | 29% / 50% |
| rosenthal | conduction | 7 | 0 | -18.9 | 18.9 | 16.5 | 100% / 100% | -27.0 | 28.4 | 27.2 | 57% / 86% |
| rosenthal | keyhole | 5 | 0 | -10.2 | 10.2 | 12.8 | 100% / 100% | -65.4 | 65.4 | 115.9 | 0% / 0% |
| rosenthal | transition | 2 | 0 | -9.7 | 9.7 | 9.1 | 100% / 100% | -49.4 | 49.4 | 45.5 | 0% / 50% |
| rosenthal | common | 14 | 0 | -14.5 | 14.5 | 14.4 | 100% / 100% | -43.9 | 44.7 | 73.9 | 29% / 50% |
| eagar-tsai | all | 14 | 0 | +1.8 | 7.3 | 7.1 | 100% / 100% | -49.7 | 49.7 | 75.4 | 21% / 50% |
| eagar-tsai | conduction | 7 | 0 | +4.5 | 10.1 | 8.2 | 100% / 100% | -36.3 | 36.3 | 29.4 | 43% / 86% |
| eagar-tsai | keyhole | 5 | 0 | -3.0 | 4.8 | 6.2 | 100% / 100% | -66.8 | 66.8 | 117.3 | 0% / 0% |
| eagar-tsai | transition | 2 | 0 | +4.1 | 4.1 | 4.1 | 100% / 100% | -54.0 | 54.0 | 48.7 | 0% / 50% |
| eagar-tsai | common | 14 | 0 | +1.8 | 7.3 | 7.1 | 100% / 100% | -49.7 | 49.7 | 75.4 | 21% / 50% |
| goldak | all | 14 | 0 | -14.7 | 14.7 | 14.5 | 100% / 100% | -42.1 | 43.3 | 73.2 | 29% / 50% |
| goldak | conduction | 7 | 0 | -19.0 | 19.0 | 16.6 | 100% / 100% | -24.3 | 26.7 | 26.2 | 57% / 86% |
| goldak | keyhole | 5 | 0 | -10.2 | 10.2 | 12.8 | 100% / 100% | -64.8 | 64.8 | 115.1 | 0% / 0% |
| goldak | transition | 2 | 0 | -10.4 | 10.4 | 9.7 | 100% / 100% | -47.5 | 47.5 | 44.1 | 0% / 50% |
| goldak | common | 14 | 0 | -14.7 | 14.7 | 14.5 | 100% / 100% | -42.1 | 43.3 | 73.2 | 29% / 50% |

### SENSITIVITY on an unresolved input, not a fit: Lane AMMT rows re-run at the nominal case power from the paper text (150 W case A, 195 W cases B/C) instead of the Table 3 power (137.9/179.2 W)

### Lane AMMT at nominal power (13 rows)

| kernel | regime | n | excluded | W bias % | W MAPE % | W RMSE um | W within +-30% / x0.5-2 | D bias % | D MAPE % | D RMSE um | D within +-30% / x0.5-2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rosenthal | all | 4 | 9 | -31.5 | 31.5 | 47.1 | 25% / 100% | +14.6 | 14.6 | 6.3 | 100% / 100% |
| rosenthal | conduction | 4 | 9 | -31.5 | 31.5 | 47.1 | 25% / 100% | +14.6 | 14.6 | 6.3 | 100% / 100% |
| rosenthal | common | 4 | 9 | -31.5 | 31.5 | 47.1 | 25% / 100% | +14.6 | 14.6 | 6.3 | 100% / 100% |
| eagar-tsai | all | 13 | 0 | +11.6 | 11.6 | 15.6 | 100% / 100% | -14.9 | 14.9 | 5.4 | 100% / 100% |
| eagar-tsai | conduction | 13 | 0 | +11.6 | 11.6 | 15.6 | 100% / 100% | -14.9 | 14.9 | 5.4 | 100% / 100% |
| eagar-tsai | common | 4 | 9 | +1.8 | 1.9 | 4.0 | 100% / 100% | -5.6 | 5.6 | 2.7 | 100% / 100% |
| goldak | all | 4 | 9 | -36.5 | 36.5 | 54.4 | 0% / 100% | +10.8 | 10.8 | 4.7 | 100% / 100% |
| goldak | conduction | 4 | 9 | -36.5 | 36.5 | 54.4 | 0% / 100% | +10.8 | 10.8 | 4.7 | 100% / 100% |
| goldak | common | 4 | 9 | -36.5 | 36.5 | 54.4 | 0% / 100% | +10.8 | 10.8 | 4.7 | 100% / 100% |

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

**Comparison: unavailable.** No like-for-like model comparison exists in the app for these quantities. The default screening kernels leave the front cooling rate unavailable: the SOL-T liquidus is an admitted nominal convention, but SOL-C's co-located interface samples are not installed. Even an admitted G x R at a solidification-front point would not be the surface centerline cooling rate just below the solidus (TSCR) or above the liquidus (TLCR), and no reviewed operator converts a kernel melt-pool length into a time above 1298 C at the surface centerline (TTAM). Adding such an operator is a model change that needs its own review; nothing was computed here.

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

**Comparison: unavailable.** The app has no stationary-spot (non-scanning) absorptance model: the kernels take a moving source and a constant flat-plate absorptivity_IR (316L 0.30, the measured conduction-mode authority since P7b; the regime index reads the convention constant 0.42), so there is no like-for-like prediction of a 10 ms, 303 um top-hat spot's average coupling efficiency. Not computed.

## Reference transient (bare plate, low power)

This block depends on wall-clock budgets (total and per case): on a slower or busier host cases can turn into 'not-run (budget)', so it is not guaranteed to reproduce; `--reuse-reference` copies the block of an earlier record instead of re-running it. This record's block was reused from a record with sha256 `b7c5d2f44492915336a70f60efda5e07c359f5577d026473cd28b6cc693ef195` (LF-normalised).

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
