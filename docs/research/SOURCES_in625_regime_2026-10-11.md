# Sources: IN625 keyhole-mode threshold on the app's normalised enthalpy (2026-10-11)

Lane `in625-regime-threshold`, branch `research/in625-regime-threshold`, base `b22657f5`. Research step 1 of
`.orchestra/ORCHESTRA.md` section 2. Every constant below carries a locator into a primary source that was opened and
read for this lane. Nothing was taken from Sci-Hub. Nothing here is a result: no threshold was fitted and no held-out
unit was scored. `experimentalValidation` stays false.

## 1. Summary

1. King et al. 2014 define the keyhole-mode criterion as melt-pool depth greater than half the width (Sec. 5.2) and the
   index as dH/hs = A P / (hs sqrt(pi D u sigma^3)) with sigma the Gaussian standard deviation, D4sigma = 4 sigma
   (Eq. 2.6, footnote 1). Their 30 +/- 4 is for 316L (Sec. 5.6).
2. Weaver, Heigel and Lane 2022 use the same Eq. 3 form with hs = rho c (T_m - T_0), A = 0.4 (Fig. 6 caption) and
   IN625 properties in Table 2. They define keyhole mode as depth over spot radius D4sigma/2 greater than one
   (Sec. 4.1) and state that the more common definition, depth over half width greater than one, is nearly identical
   at the transition (Sec. 4.1, Appendix B). Sec. 4.2 says the King threshold of about 30 "is observed" in their IN625
   data.
3. Convention reconciliation (section 4): for the same power, speed and D4sigma, the app index equals 0.7243 times the
   Weaver index (IN625, app properties, 20 C). Weaver's 30 is 21.73 in app units; King's band 26 to 34 is 18.83 to
   24.63.
4. Weaver's own text does not support 30 as the morphology onset for IN625. Sec. 4.1 places the 195 W / 800 mm/s
   morphology transition between D4sigma 100 and 150 um, which is Weaver index 23.6 to 12.8, and their Table 4 lists
   the Lane CBM case C (Weaver index 19.2) at d/(2 sigma) = 1.2, keyhole by their own definition. The "about 30" of
   Sec. 4.2 reads as the knee of the d/sigma curve in Fig. 6, not as the point where a morphology ratio crosses one.
   The lane therefore fits the threshold to a declared morphology criterion instead of transferring 30.
5. The IN625 ledger has 70 condition-level units with measured width and depth and full process inputs: 64 from the
   NIST mds2-2923 workbook (Weaver's own plates; 57 EOS M270, 7 AMMT) and 6 Lane 2020 class means (3 CBM, 3 AMMT).
   Ghosh 2018 is not in it (spot size not stated, section 6). Split and exclusions are in the pre-registration. One
   mds2 EOS row (row 29) is very likely the Lane CBM B tracks themselves (section 3.3) and is excluded.
6. The brief's app indices 19.45 and 17.88 for Lane CBM A and B are the app at 80 C preheat. At the dataset convention
   of 20 C they are 18.57 and 17.07 (the repo note "13.9 to 18.6" uses 20 C).

## 2. Access log

| source | how read | identity | committed |
|---|---|---|---|
| Weaver, Heigel, Lane, "Laser spot size and scaling laws for laser beam additive manufacturing", J. Manuf. Process. 73 (2022), doi:10.1016/j.jmapro.2021.10.053, PMC9890508 (NIST author manuscript NIHMS1855299) | NCBI efetch JATS XML, 2026-10-11, MathML of Eq. 1 to 20 read directly | 125163 bytes, sha256 `6c9d5f7c1d3003483a1942f98d98a50053146ad560f4e35854fe530c6cf9ada7` | no (text-mining / fair-use permission only) |
| King, Barth, Castillo, Gallegos, Gibbs, Hahn, Kamath, Rubenchik, "Observation of keyhole-mode laser melting in laser powder-bed fusion additive manufacturing", J. Mater. Process. Technol. 214 (2014) 2915, doi:10.1016/j.jmatprotec.2014.06.005 | OSTI 1502044 accepted manuscript LLNL-JRNL-642426, PDF; pages 7 (Eq. 2.6) and 36 (Table 3) rendered and read as images, text extracted for Sec. 5 | 26003149 bytes, sha256 `aad2c6b757fc9f8483ad1653d569ce70af7518d86497f025fb797efa7d94ddf0` | no |
| Lane et al., "Measurements of melt pool geometry and cooling rates of individual laser traces on IN625 bare plates", IMMI 9 (2020), doi:10.1007/s40192-020-00169-1, PMC8194244 | NCBI efetch JATS XML, 2026-10-11 | sha256 `19757c67b91aeee5b4575722482103649dc98d03167bced14d64244f5313b460`, identical to the pin `LANE_SOURCE` in `python/lpbf_public_datasets.py` | Tables 3 and 4 as `data/benchmark/lane-in625-amb2018-02/*.csv` (pinned) |
| Weaver, Deisenroth, Mekhontsev, Heigel, Lane (2023), NIST mds2-2923 v1.0.0, doi:10.18434/mds2-2923 | committed workbook and README, read with the stdlib xlsx reader of `lpbf_public_datasets.py` | `Master_TrackList_Measurements.xlsx` sha256 `6cd32669...7a52`, `2923_README.txt` sha256 `8b8fc00c...1c39` (match `official/manifest.json`) | yes, `data/benchmark/nist-mds2-2923-in718/official/` |

PMC metadata quirk, recorded only: the Weaver XML journal-meta names "J Mater Process Technol", while the DOI
(`j.jmapro`) and the brief name J. Manuf. Process. 73. The article identity (title, authors, DOI) is unambiguous.

## 3. Constants with locators

### 3.1 King et al. 2014 (accepted manuscript, OSTI 1502044)

| item | value | locator |
|---|---|---|
| beam parameter | I(r) = I0 exp(-r^2 / (2 sigma^2)), so D4sigma = 4 sigma | footnote 1, PDF p. 6; Sec. 5.3 quotes D4sigma 52 and 130 um |
| index | dH/hs = A P / (hs sqrt(pi D u sigma^3)), "calibration following Hann" | Eq. 2.6, PDF p. 7 (rendered image) |
| hs | rho c T_m in the derivation; Table 3 gives hs = 1.2e6 J/kg (Rai 2007) with rho printed 7.98 kg/m3 (physically 7.98 g/cm3) | PDF p. 7; Table 3, PDF p. 36 (rendered image) |
| A, D (316L) | A = 0.4, D = 5.38e-6 m2/s | Table 3, PDF p. 36 |
| keyhole criterion | "melt pools where the depth was greater than the half width" | Sec. 5.2 |
| threshold | transition starts at about 26, "clearly keyhole" above about 34; threshold 30 +/- 4, two beam sizes, 316L | Sec. 5.3, Sec. 5.6 |

### 3.2 Weaver, Heigel, Lane 2022 (PMC9890508)

| item | value | locator |
|---|---|---|
| index | dH/hs = A P / (hs sqrt(pi D u sigma^3)) | Eq. 3 (MathML) |
| hs | hs = rho c (T_m - T_0) | Eq. 4 |
| beam | spot diameter = D4sigma = 4 sigma, spot radius = 2 sigma; Gaussian assumed | Sec. 3 after Eq. 4; footnote 1 |
| A for the King plot | 0.4 constant | Fig. 6 caption |
| IN625 properties | T0 300.15 K, rho 8440 kg/m3, T_m 1563.15 K, kappa 28.78 W/(m K), T_v 3500 K, c_p 719.92 J/(kg K), D = kappa/(rho c_p) | Table 2 |
| keyhole definition | depth over spot radius greater than one; common literature definition depth over half width greater than one (Eagar and Tsai), nearly identical at the transition | Sec. 4.1; Appendix B, Fig. B1 |
| transition location | 195 W, 800 mm/s: transition between D4sigma 100 and 150 um | Sec. 4.1, last paragraph |
| threshold statement | 316L threshold about 30 (King); "The same threshold is observed in this data on IN625"; scattered beyond it | Sec. 4.2, first paragraph |
| AM-Bench 2018 CBM cases | A 150 W 400 mm/s, B 195 W 800 mm/s, C 195 W 1200 mm/s, D4sigma 100 um; d/(2 sigma) = 3.0, 1.8, 1.2; "all three cases are in transition or keyhole mode" | Table 4; Sec. 6.2 |
| depth and width definitions (paper) | depth from substrate surface to melt-pool bottom, humping neglected; width edge to edge at the substrate surface | Sec. 2.2 |
| data set | 80 tracks, EOS M270 and AMMT, 122 to 195 W, 200 to 1200 mm/s, D4sigma 50 to 322 um, includes ten Lane 2020 EOS tracks | Sec. 2.2, Table 1 |
| EOS spot sizes | estimated from manufacturer data and a beam caustic (D0 = 78 um, lambda = 1070 nm), not measured; AMMT spot measured on a CCD | Sec. 2.1, Eq. 1 and 2 |

### 3.3 NIST mds2-2923 (committed)

| item | value | locator |
|---|---|---|
| width, depth definition | bounding box; top aligned with the plate surface; depth = deepest, width = widest (not necessarily at the surface); humping neglected | `2923_README.txt`, "Measurement definitions" |
| uncertainty | expanded U (k = 2) of the mean following Lane 2020; along-track variability 2 % (width) and 5 % (depth) | same paragraph; Summary columns "Width/Depth: Combined, Expanded uncertainty" |
| spot | estimated for EOS M270, measured for AMMT | README "Machine settings"; Summary column "Estimated D4sigma Spot Diameter (um)" |
| IN625 rows | Summary sheet: 57 EOS M270 rows (140 measurements), 7 AMMT rows (18 measurements); Data sheet holds 178 IN625 image rows (plates 3, 4, 8, 9, 10 on EOS M270, "SpotSize" on AMMT) | sheet Summary, column Material; sheet Data |
| relation to Weaver 2022 | README cites doi:10.1016/j.jmapro.2021.10.053 as an associated publication; the Data sheet folders are named by plate (Plates 3, 4, 8, 9, 10, "SpotSize") and dated 2018-08-28 to 2018-10-26, with no AM-Bench label, but the data set does contain the ten Lane 2020 EOS tracks Weaver Sec. 2.2 includes (next row) | README "Description"; Data sheet column Folder Name |
| Lane 2020 EOS tracks inside mds2 | Summary row 29 (EOS M270, 195 W, 800 mm/s, D4sigma 100 um, n = 10, depth 91.258 um) is very likely the AM-Bench 2018 CBM B tracks: Weaver Sec. 2.2 says the set includes ten Lane 2020 EOS tracks, Weaver Table 4 case B gives d = 91.28 um, n = 10, and no mds2 EOS row exists at 150 W / 400 mm/s or 195 W / 1200 mm/s; its ten Data sheet images sit in folders Plate3 Set1/Set2 (1 each), Plate4 Set1/Set2 (3 each) and Plate9 Set1/Set2 (1 each), so the identity is inferred, not labelled | Summary row 29; Data sheet; Weaver Sec. 2.2, Table 4 |

The Summary sheet's measurement counts (158) and the Data sheet's IN625 image rows (178) differ; the unit of this lane
is the published Summary row, so the difference is recorded, not resolved.

### 3.4 Lane et al. 2020 (PMC8194244, pinned tables)

| item | value | locator |
|---|---|---|
| machines | AMMT and an EOS M270 commercial build machine (CBM) | Introduction, last paragraph |
| spots | CBM D4sigma 100 um (FWHM 59 um), AMMT D4sigma 170 um (FWHM 100 um); both Gaussian-consistent (FWHM / D4sigma = 0.59) | section 2.1 text; Table 1 |
| width, depth | bounding rectangle at the melt-pool depth and width boundaries, aqua regia etch, CLSM | section "Melt Pool Transverse Cross-Sections Measurements" |
| class means | Table 4 "Class Width" and "Class Depth" mean, N, U_mean; AMMT values combine the 100 us and 20 us samples | Table 4 and caption |
| morphology remarks | AMMT cases all conduction mode; CBM B and C "slight keyhole or keyhole transition shape"; CBM A "near or at keyholing regime" | section "Melt Pool Transverse Cross-Sections Measurements" (Figure 6 text); section "Measurement Uncertainty - Cross-section width and depth" |
| power | AMMT Table 3 lists 137.9 / 179.2 W, case definitions 150 / 195 W; status unresolved in the repo (`LANE_POWER_QUESTION`) | Table 3; Sec. 2 |

### 3.5 Repo convention (base `b22657f5`)

| item | value | locator |
|---|---|---|
| index | A P / (rho cp_s max(50, T_liq - T0) sqrt(pi alpha_s v r^3)), r = D4sigma/2, flat A | `python/lpbf_thermal_solver.py:606-607`; same formula `python/lpbf_public_datasets.py:1129-1140` |
| IN625 properties | rho 8440, k_s 9.8, cp_s 410, T_liq 1350 C, solidus 1290 C, A_IR 0.38 (provenance class legacy-estimated-secondary) | `python/lpbf_thermal_solver.py:34-52`, `:1166-1173` |
| cuts | 15 transition, 20 keyhole mode; label "Keyhole Mode (melt-pool D/W > 0.5 screening onset)" | `python/lpbf_thermal_solver.py:174-185`, `:247-252` |
| IN625 note | "threshold misses keyhole in the available dataset (measured keyhole indices 13.9-18.6)" | `python/lpbf_thermal_solver.py:188-189` |
| dataset preheat | 20 C assumed for bare plates | `python/lpbf_public_datasets.py:63` (`ASSUMED_PREHEAT_C`) |
| depth independence | the depth increment and the process-map depth proxy use the legacy 15/30 band edges, not `ENTHALPY_KEYHOLE`; the cut changes labels only | `python/lpbf_thermal_solver.py:203-205`, `:971-977`, `:724` |

## 4. Convention reconciliation

For the same P, u and D4sigma:

    H_app / H_Weaver = (A_app / A_W) * (rho_W c_W (T_m - T_0)_W) / (rho_app cp_s (T_liq - T0)_app)
                       * sqrt(D_W / alpha_app) * (sigma / r)^1.5,   sigma / r = (D4sigma/4) / (D4sigma/2) = 1/2

| term | Weaver 2022 | app | ratio app/W contribution |
|---|---|---|---|
| A | 0.4 | 0.38 | 0.95 |
| volumetric hs | 8440 x 719.92 x 1263 = 7.674e9 J/m3 (T_m 1290 C, T_0 27 C) | 8440 x 410 x 1330 = 4.602e9 J/m3 (T_liq 1350 C, T0 20 C) | 1.6675 |
| diffusivity | 4.737e-6 m2/s | 2.832e-6 m2/s (solid) | sqrt(1.6725) = 1.2933 |
| beam length | sigma = D4sigma/4 | r = D4sigma/2 | 2^-1.5 = 0.35355 |
| product | | | **0.72429** |

| quantity | Weaver / King units | app units (IN625, 20 C) |
|---|---|---|
| Weaver Sec. 4.2 threshold | 30 | 21.73 |
| King band (316L numbers, 26 to 34) | 26 to 34 | 18.83 to 24.63 |
| Lane CBM A / B / C | 25.6 / 23.6 / 19.2 | 18.57 / 17.07 / 13.94 |
| 195 W, 800 mm/s, D4sigma 100 / 150 um (Weaver Sec. 4.1 transition bracket) | 23.6 / 12.8 | 17.07 / 9.29 |

Two differences remain that no factor removes: (1) Weaver uses T_m = 1290 C (the IN625 solidus) and liquid-range
kappa, the app uses the liquidus and room-temperature solid k and cp, so the factor is valid for IN625 with these two
property sets only; (2) King's 316L calibration (A, hs per mass, density unit) is a different property set again, and
the earlier repo conversion of King's 30 to 22.2 (`docs/LPBF_KEYHOLE_THRESHOLD_EVIDENCE_2026-10-07.md`) is a 316L
number, not an IN625 one. A threshold fitted here is a number in the app convention with the app's IN625 property set;
if those properties change, it has to be refitted.

## 5. Regime-truth criteria available

| criterion | source | measurable from the ledger |
|---|---|---|
| depth > width / 2 | King 2014 Sec. 5.2; Weaver 2022 Sec. 4.1 ("more common definition"); app label text "D/W > 0.5" | yes, all 70 units |
| depth > D4sigma / 2 | Weaver 2022 Sec. 4.1 | yes, but it depends on the spot estimate (EOS spots are estimated) |
| vapour depression present | Cunningham 2019 (Ti-6Al-4V, x-ray) | no IN625 data; the transition cut 15 is therefore not testable here |
| porosity | Zhao 2020 (Ti-6Al-4V) | no |

The pre-registration takes depth > width/2 as the primary truth (geometry only, no dependence on the spot estimate)
and depth > D4sigma/2 as the secondary.

## 6. IN625 track ledger

Committed as `data/benchmark/in625-regime-ledger-2026-10-11/units.csv` (sha256
`6957b6f3c9ac809b2a7221f4e07be7c26c410d873e8f01e8b2ca04b5a088424a`), generated by
`python python/tools/lpbf_in625_regime_threshold.py build-ledger` from the two committed sources above. One row per
condition-level unit: unit id, source, campaign, machine, power, speed, D4sigma, spot provenance, number of
measurements, mean width, mean depth, expanded uncertainties, split and a locator. The ledger is a transcription: it
holds no index, no ratio and no label.

| source | units | machines | P (W) | v (mm/s) | D4sigma (um) |
|---|---|---|---|---|---|
| mds2-2923 Summary, IN625 | 57 | EOS M270 (estimated spot) | 122, 179.2, 195 | 200, 800 | 80 to 322 |
| mds2-2923 Summary, IN625 | 7 | AMMT (measured spot) | 195 | 800 | 50 to 256 |
| Lane 2020 Table 4 classes (inputs from Table 3) | 3 | EOS M270 CBM | 150, 195, 195 | 400, 800, 1200 | 100 |
| Lane 2020 Table 4 classes (inputs from Table 3) | 3 | AMMT | 137.9, 179.2, 179.2 | 400, 800, 1200 | 170 |

Not in the ledger, with reasons:

1. Ghosh et al. 2018 (JOM 70, 1011), seven IN625 tracks in the repo (`lpbf_literature_datasets.py`): the experimental
   spot size is not stated (the repo uses the FE model's 140 um as an assumption), so the index of every row is
   unknown by a factor (d_true/140)^-1.5; case 7 (195 W, 800 mm/s) has depth 38 um against Lane CBM B 91 um at the
   same nominal inputs, unexplained in the paper. Excluded from scoring.
2. mds2-2923 IN718 rows: different alloy.
3. Lane per-track Table 3 rows: the unit is the Table 4 class mean (the authors' combined reference values), so
   tracks are not counted separately.
4. Weaver's ten Lane 2020 EOS tracks: very likely mds2 Summary row 29 (section 3.3), the same physical tracks as the
   held-out Lane CBM B class. That row is in the ledger with split "excluded" and is never fitted or scored; the
   tracks enter the evaluation only once, through Lane Table 4 class CBM-B. Without the exclusion a held-out target
   would enter the fit (pre-registration section 5). Correction of 2026-10-11 (amendment 1): an earlier version of this
   item said the tracks were not in mds2 because the mds2 plates are not AM-Bench plates; that was wrong.

Uncertainty columns: mds2 rows carry the published U (k = 2). Lane rows carry 2 x Table 4 U_mean combined with the
mds2 README variability (2 % width, 5 % depth); this is an approximation used only for the ambiguity sensitivity.

## 7. Open points (do not block the pre-registration)

1. EOS M270 spot sizes in the fit split are estimates (caustic model). A 10 % spot error moves the index by about 15 %.
2. mds2 width is the widest bounding-box dimension (README); the Weaver paper text says width at the substrate
   surface. The data file definition is used.
3. Lane AMMT applied versus commanded power (`LANE_POWER_QUESTION`) stays unresolved; a nominal-power sensitivity is
   declared.
4. N3 (`docs/research/RESULTS_ke_width_n3_2026-10-10.md`) used the same mds2 and Lane tracks as held-out depth data.
   This lane fits a regime cut, not a depth law, and changes no depth number, so there is no reuse of a fitted
   constant; the overlap is recorded.
