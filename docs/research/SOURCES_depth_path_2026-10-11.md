# Sources for a transferable melt-pool depth path (IN625, bare plate)

Date: 2026-10-11. Lane `depth-path`, branch `research/depth-path`, base `63104c92` (tip of the IN625 regime bump,
fingerprint `0d52d7f7`). RESEARCH step 1 of `.orchestra/ORCHESTRA.md` section 2 (sources only). No model was run, nothing was
fitted and nothing was scored on held-out data. `experimentalValidation` stays false.

The only computations in this file are arithmetic on process inputs and published constants (the app index for
Deisenroth's conditions, the app index for the N3 process conditions, and unit conversions). No measured width or depth
of an N3 track was read to produce any number here.

N3 context (ledger in `RESULTS_ke_width_n3_2026-10-10.md`, split in `PREDECLARED_ke_width_n3_2026-10-10.md`): held-out
campaigns are `nist-20180905`, `nist-20180910`, `nist-20181026` (AMMT spot series), `lane-CBM`, `lane-AMMT`;
`nist-20180828` is descriptive. Baseline pooled depth MAPE 32.7 %, served 25.6 %.

PDF page numbers below are the page index of the file in `papers/` (printed page numbers are given where they differ).
Text was extracted with pdftotext. Figures that carry the data (Deisenroth Fig. 7, Hong Figs. 3 and 4) were rendered and read
by eye or from printed bar labels, which is stated each time.

## 1. Summary of the numbers that matter

1. Measured IN625 bare-plate absorptance (Deisenroth 2020, calorimetry, 65 um D4sigma, 500 mm/s) is about 0.33 to 0.34 in
   conduction mode (50 to 60 W), 0.40 at 80 W, 0.55 to 0.67 at 100 W, 0.70 at 120 W, 0.75 at 150 W and 0.89 to 0.93 at 300 W.
   The app serves a flat 0.38 plus a multi-reflection boost above its regime cuts. The conduction plateau is 10 to 13 percent
   below 0.38. This source does not use any N3 track.
2. On the app index (A 0.38, app properties, 20 C), Deisenroth's absorptance step sits between 80 W (index 16.9) and 100 W
   (index 21.1). The N3 conditions are: AMMT A, B, C index 7.7, 7.1, 5.8 (below the 50 W conduction point at 10.6) and CBM A, B, C
   index 18.6, 17.1, 13.9 (inside Deisenroth's step region, 12.7 to 21). So the source implies A about 0.33 to 0.34 for the
   AMMT tracks and a regime-dependent 0.34 to 0.55 for the CBM tracks. Transfer across beam size (65 um versus 100 um) is
   unverified for IN625.
3. Ye 2019 minimal absorptivity for IN625 is 0.28 (foil, 57 um beam). Ye's depth law is d/a = 0.6 A_e L_th with A_e = 0.70 (1 - exp(-0.66 A_m L_th)).
4. Rubenchik 2018 depth function s(B,p) (Eq. 11) is an interpolation of a conduction-model numerical solution with no data fit.
   Its IN625 data came from GE (not NIST). It is independent of N3. Weaver 2022 found it poor on 80 NIST IN625 tracks
   (errors about 50 percent, up to 100 percent, Appendix A, Fig. A1).
5. The constant 0.25 of Rubenchik's closed form `d = 0.25 delta dH/hs` (Weaver Eq. 13) comes from Fabbro's analysis of
   Rubenchik's data, independent of N3. The absorptivity that makes it work on IN625, A = 0.40, is a back-solve from Lane CBM
   depths (contaminated).
6. Published conduction models do not match CBM. Hong 2021 conduction model (A 0.37) gives CBM depth ratios predicted over
   measured of about 0.42, 0.55, 0.67 for A, B, C (bar labels, Fig. 4a). Only a keyhole-physics model with ray-traced Fresnel
   absorption (A0 0.43, no tuning to IN625 depth) matched CBM, within 10 percent, with nominal D4sigma 100 um.
7. Property sensitivity (Grohol 2024 thesis ch. 4, 304L and IN718, not IN625): surface-normal absorption is dominant (27 to 39 percent raises
   304L depth 76 percent). Liquid conductivity within physical range changes depth by 7 percent or less. Vaporization
   temperature moves depth 6 to 18 percent. Beam diameter plus or minus 10 um moves depth by minus 24 / plus 5 percent.
8. The app's mixed solid/liquid k and cp (k_th 19.9, cp 580) reproduce the temperature-averaged ORNL JMatPro set
   (k 19.5, cp 569) within 3 percent. The solid constants 9.8 and 410 are room temperature values. The remaining
   unsourced item in the served conduction kernel is the factor 1/(1 + 0.55 St), about 0.83 for IN625.

## 2. Absorptance of IN625 and related metals, by regime

### 2.1 Deisenroth, Mekhontsev, Lane 2020 (`deisenroth2020_in625_energy_balance.pdf`)

Title: "Measurement of mass loss, absorbed energy, and time-resolved reflected power for laser powder bed fusion"
(NIST, conference manuscript, 13 pages). Setup (PDF p2, Sec. 2): NIST AMMT, 1070 nm, D4sigma 65 um, scan speed 500 mm/s,
P 50 to 300 W, rolled and annealed bare IN625 plate, ground 400 grit, 3 mm to 7 mm tracks. Absorbed energy by calorimetry
(Sec. 2.3, Eq. 2 and 3, thermistor, specific heat from Pawel and Williams, 1.5 percent standard uncertainty), reflected energy by
integrating hemisphere (Sec. 2.5, Eq. 4, 3.5 percent standard uncertainty), mass loss by balance. Tracks were not
cross-sectioned (PDF p9, Sec. 3.1: "Cross-sections of the tracks formed for this study were not made"), regime labels come
from literature at comparable conditions: 60 W conduction, 100 W transition, 300 W keyhole (PDF p9).

The paper has no table. Values exist as text (PDF p10, Sec. 3.4) and in Fig. 7 (PDF p10). The per-condition numbers below are
my reading of Fig. 7 rendered at 200 dpi (axis calibrated on the 0 and 1 ticks and the 50 and 350 W ticks), so read
uncertainty is about 0.02 on the ratio, in addition to the plotted error bars (combined standard uncertainty, 68 percent, about
0.02 to 0.05 on the ratios). Sample 1 is a circle, Sample 2 a triangle. "Index" is the app normalized enthalpy index
`A P / (rho cp_s (T_liq - T0) sqrt(pi alpha_s v r^3))` with A 0.38, rho 8440, cp_s 410, k_s 9.8, T_liq 1350 C, T0 20 C,
r = D4sigma/2 = 32.5 um (my arithmetic, formula from `python/lpbf_thermal_solver.py:606-607`). Ye coordinate X = A_m P / (pi hs u (2 sigma)^2)
with A_m 0.28, hs = rho c (T_m - T0) with Weaver Table 2 IN625 properties (my arithmetic).

| P (W) | sample | absorbed / applied (Fig. 7) | reflected / applied | stated in text | app index | Ye X |
|---|---|---:|---:|---|---:|---:|
| 50 | 1 | 0.33 | 0.60 | "about 0.34" | 10.6 | 1.10 |
| 50 | 2 | 0.335 | 0.60 | | 10.6 | 1.10 |
| 50 | non-melting, defocused 300 um | 0.37 | 0.61 | energy sum 0.97 plus or minus 0.045 | n/a | n/a |
| 60 | 2 | 0.32 | 0.62 | | 12.7 | 1.32 |
| 80 | 1 | 0.40 | 0.49 | "only 0.40 at 80 W" | 16.9 | 1.76 |
| 80 | 2 | n/a | 0.45 | largest unmeasured energy, 7 to 16 percent | 16.9 | 1.76 |
| 100 | 1 | 0.55 and 0.65 (two points) | 0.34, 0.26 | "jumps to about 0.60 at 100 W" | 21.1 | 2.20 |
| 100 | 2 | 0.665 | 0.26 | largest scatter, transition mode | 21.1 | 2.20 |
| 120 | 2 | 0.68 and 0.71 | 0.24 | | 25.4 | 2.64 |
| 150 | 1 | 0.745 | 0.18 | | 31.7 | 3.30 |
| 150 | 2 | 0.755 | 0.17 | | 31.7 | 3.30 |
| 300 | 1 | 0.885 | 0.08 | "to about 0.90 at 300 W" | 63.4 | 6.60 |
| 300 | 2 | 0.93 | 0.07 | "falls to 0.07 at 300 W" | 63.4 | 6.60 |

Quotes (under 15 words): "jump in absorption at 100 W is associated with transition mode" (PDF p10); "less than 1.5 % of the input energy was
converted to vaporization" (PDF p11, Conclusions). Reflected power in time (Fig. 6, PDF p9): about 0.50 at 50 W, 0.27 plateau at
100 W with nearly 60 percent swing at track start, 0.125 average at 200 W (keyhole). Mass loss rises to 0.67 mg/m at 300 W (PDF p9, Fig. 5).
Energy balance (Fig. 7): sum of absorbed and reflected 0.89 to 0.97, so up to 16 percent of the energy is unmeasured near 80 W,
possibly port losses or heating of ambient gas (PDF p10 end). A systematic bias in the absorbed values is therefore not excluded.

Independence from N3 held-out tracks: yes. AMMT bare IN625 plates, a separate experiment, no melt-pool depth used. Weaver 2022
cites these values (Sec. 5, PDF p12) when explaining the "modified Ye" constants, but Deisenroth's data were not derived from them.
Caveats: single beam size 65 um and single speed 500 mm/s, so the transfer of the power axis to other spots goes only through a
similarity variable (app index or Ye X), and for IN625 that transfer is not tested. Absorptance is track-averaged over 3 to 7 mm.

### 2.2 Knapp et al. 2022 (`knapp2022_calibrating_meltpool_am.pdf`)

Knapp, Rolchigo, et al., "Calibrating uncertain parameters in melt pool simulations of additive manufacturing", Comput. Mater.
Sci. 2022 (doi:10.1016/j.commatsci.2022.111904). Finite-volume heat transfer (HT) and heat transfer plus fluid flow (HTFF) models
calibrated on width and depth (WD) and on width, depth and length (WDL). Calibration targets: NIST AM-Bench 2018-02 AMMT
cases A, B, C from Lane 2020 (PDF p11 to p12, Sec. 2.4 and Table 4): 137.9 W / 400 mm/s width 148 depth 42 um, 179.2 W / 800 mm/s
123 and 36, 179.2 W / 1200 mm/s 106 and 30. Laser D4sigma 170 um (FWHM 100 um) (PDF p12). Absorptivity search range 0.20 to 0.35 (Table 2, PDF p10),
radius range 50 to 110 um.

Calibrated effective absorption and radius (Table 5, PDF p15, mode of the posterior, per AMMT case):

| case | model | r_xy (um) | A |
|---|---|---:|---:|
| A | HT | 84.7 | 0.307 |
| A | HTFF | 61.2 | 0.288 |
| B | HT | 71.1 | 0.289 |
| B | HTFF | 57.0 | 0.277 |
| C | HT | 62.7 | 0.302 |
| C | HTFF | 53.5 | 0.291 |

Text (PDF p13 to p14): mean absorption "between 29-32 %" for HT and 27 to 29 percent for HTFF, close to a Fresnel value for 1064 nm of
30 percent (rule of mixtures). Combined A, B, C calibration (Fig. 9 text, PDF p21): "well-defined peak around 0.3". The calibrated radius is
below the nominal half-D4sigma (85 um) for every case except HT case A, so the nominal beam is not reproduced.

Contamination: the constants are tuned on Lane AMMT depth and width, which are the lane-AMMT held-out group of N3. Not independent of lane-AMMT.
It also shows that a model needs a smaller effective spot than nominal to reproduce these tracks, which bears on the AMMT beam definition.
No Knapp constant is independent for the CBM or NIST-workbook groups, since the calibration targets are AMMT only, but a transfer would be
a cross-campaign claim tested on data close to the calibration set.

### 2.3 Ye et al. 2019 (`ye2019.pdf`, transcription `data/benchmark/ye-2019-absorptivity/table1_min_absorptivity.csv`)

Ye, Khairallah, Rubenchik, Crumb, Guss, Belak, Matthews, "Energy Coupling Mechanisms and Scaling Behavior Associated with Laser Powder
Bed Fusion Additive Manufacturing", Adv. Eng. Mater. 21 (2019) 1900185. Calorimetric A_e on bare 0.5 mm foils, 1/e2 beam
57 um, 500 mm/s (Figs. 2 and 6), materials Ti-6Al-4V, IN625, 316L.

Table 1 (PDF p4, printed 4 of 9): minimal absorptivity A_m "in this work": Ti-6Al-4V 0.26, IN625 0.28, 316L 0.28 (repo transcription;
the pdftotext layout of the table is scrambled, the repo CSV is the checked reading). IN625 melting enthalpy 7985 J/cm3, melting
point 1563 to 1623 K, thermal diffusivity 0.048 cm2/s at T_m (as printed). A_m is the minimum of the A_e versus power curve,
read as the flat-melt absorptivity (PDF p7).

Depth law (PDF p7, Eq. 5 and Fig. 5): d/a = K A_L_th with normalized depth d/a, L_th = sqrt(D a / u) / a, enthalpy
beta = A P / (H_m a^2 sqrt(D a u))-type group (symbols are lost in the text layer). With measured A_e, K = 0.60 "throughout thermal
conduction and keyhole regimes". With A_m (constant), slope 0.6 for A_m L_th < 2 and 1.72 for A_m L_th > 2 (adjusted R squared 0.98 in keyhole).
Absorptivity fit (PDF p8, Eq. 6): A_e = 0.701 (1 - exp(-0.66 A_m L_th)), R squared 0.80 over three materials, saturation 0.7 attributed partly to
plume scattering and evaporation losses.

Quote: "slope (K in Equation (5)) equals 0.60 throughout" (PDF p8). Independence from N3: yes (LLNL foils, 2019, before AM-Bench published
Lane 2020 depths). Caveat: foils 0.5 mm thick (not semi-infinite), 57 um beam only. The IN625 per-condition A_e values are in Fig. 6 only
and were not digitized. IN625 depth pictures in Fig. 2F to I, no table.

### 2.4 Trapp 2017, Matthews 2018, Simonds 2018 and 2021 (none are IN625)

Trapp et al. 2017 (`trapp2017.pdf`): 316L bare disc, 60 plus or minus 5 um 1/e2, 1070 nm. Regime I 0.29 to 0.31, step above about 70 W (500 mm/s),
saturation about 0.78 (PDF p4, Fig. 3a). Repo values `data/benchmark/trapp-316l-2017/absorptivity_digitized.csv`, series `316L-disc-v500`:
0.287 (32 W), 0.295, 0.298, 0.307 (65 W), 0.371 (74 W), 0.420, 0.534, 0.558 (91 W), 0.656, 0.699, 0.726, 0.764 (178 W), 0.792, 0.785, 0.784 (356 W);
`316L-disc-v1500`: 0.315 (48 W) rising to 0.690 (534 W). Digitized, read uncertainty 0.005 per the repo attribution file.
Matthews et al. 2018 (`matthews2018.pdf`): W, Al 1100 and 316L discs, 30 to 600 W, 100, 500, 1500 mm/s. No IN625.
Simonds et al. 2018 (repo `simonds-316l-2018/table3_absorptance.csv`, PRApplied 10, 044061 Table III): 316L polished discs, stationary 10 ms spot welds, 303 um top hat.
Coupling 0.31 at 0.17 to 0.29 MW/cm2, 0.35 at 0.41, then 0.50 to 0.86 as keyholing starts (time to keyhole 2.1 to 0.14 ms).
Simonds et al. 2021 (`simonds2021.pdf`, Appl. Mater. Today 23, 101049, PDF p7, Eq. 1 and Fig. 6): Ti-6Al-4V keyhole depth over L_th versus normalized
enthalpy from measured time-resolved absorptance: bare plate linear fit slope 0.42, compared with the 0.60 of Ye. Quote: "linear fit of the bare plate data re-" (cut at line break, PDF p7), slope 0.42.
These show the same step structure as Deisenroth for other alloys. They give no IN625 value. Independent of N3 (different material).

### 2.5 Other IN625 absorptivity values used by modelers (secondhand, for context)

1. Sabau et al. 2018 (`sabau2018_in625_jmatpro_properties.pdf`, ORNL/TM-2018/1044, PDF p24, Eq. 12): estimated 0.33 at 1.064 um from resistivity (1.3e-4 ohm cm);
   Drude model value about 0.24; simulations used 0.5 and 0.3. Estimate, not a measurement.
2. Hong 2021 (PDF p6): absorptivity used by published benchmark models "ranged from 0.2 to 0.51"; high-fidelity model uses a Fresnel curve with 0.43 at normal incidence (average IN718 data, PDF p7, Fig. 2).
3. Grohol thesis ch. 4 (PDF p33, thesis p. 97): Deisenroth about 34 percent, Lane about 40 percent (ref. [143] not in the extract), Ye 28 to about 38 percent for IN625, Boley 27 percent for Ni, Trapp 25 to 34 percent for 316L.
4. Weaver 2022 (PDF p12): Deisenroth "start at a range 0.34 to 0.40, increase quickly to 0.60 ... maximum value of 0.90".

### 2.6 Which absorptance values are independent of the N3 held-out tracks

| value | source | used on | independent of N3 held-out? |
|---|---|---|---|
| 0.33 to 0.34 conduction, 0.40 at 80 W, 0.55 to 0.67 at 100 W, to 0.90 at 300 W | Deisenroth 2020 | AMMT, own bare plates | yes |
| A_m 0.28, A_e curve 0.70 (1 - exp(-0.66 X)) | Ye 2019 | LLNL foils | yes |
| 0.33 (Hagen-Rubens style estimate) | Sabau 2018 | property estimate | yes |
| 0.27 to 0.31 (calibrated A) | Knapp 2022 | Lane AMMT A, B, C | no, lane-AMMT |
| 0.37 (calibrated) | Hong 2021 conduction and fluid models | Lane AMMT-B depth | no, lane-AMMT (and it then underpredicts CBM) |
| 0.43 Fresnel, ray traced | Hong 2021 high-fidelity | IN718 literature average | yes for the value, but the keyhole model is not a closed form |
| 0.5, 0.8, 1.32 ("modified Ye") | Weaver 2022 | tuned on 80 NIST and Lane tracks | no, all groups |
| 0.40 (Rubenchik A) | back-solved from Weaver Table 5 | Lane CBM A, B, C depths | no, lane-CBM |
| 0.8 and Tv 3500 K (Fabbro) | Weaver 2022 | adjusted to match slope on Weaver's tracks | no |
| 0.38 | repo `SECONDARY_THERMOPHYSICAL_DB` | legacy-estimated-secondary, no locator | not traceable, treat as unsourced |
| 0.26, 0.31 to 0.32 316L, W, Al values | Trapp, Matthews, Simonds | other materials | yes, wrong material |

## 3. Keyhole and transition depth laws (computable form, validity)

Notation: P laser power (W), v scan speed (m/s), D4sigma beam diameter (m), A absorptivity, rho, c, k, D = k / (rho c) properties,
T_m melting or liquidus (K), T_0 start temperature, T_v boiling (K), hs = rho c (T_m - T_0), sigma = D4sigma / 4, r0 = D4sigma / 2.

### 3.1 Rubenchik, King, Wu 2018 (`1-s2.0-S0924013618300906-am.pdf`, J. Mater. Process. Technol. 257, 234)

Model: steady moving Gaussian source, conduction only, constant properties at melting, latent heat ignored, flat surface (PDF p5 to p7).
The depth is a universal function of normalized enthalpy and Peclet-like ratio. Variables (PDF p6, page image checked):

    a = sqrt(2) sigma = D4sigma / (2 sqrt 2)         (intensity exp(-r^2/a^2), footnote 2, PDF p6; D4sigma 54 um gives a about 20 um)
    B = T_s / T_m = A P / (pi rho c T_m sqrt(D v a^3))   ; dH/hs = 2^(3/4) pi B = 5.3 B  (PDF p6 and p19)
    p = D / (a v)
    depth d = a |s(B,p)|

Interpolation (Eq. 11, PDF p20). The text layer drops minus signs; I reconstructed them from the pdftotext -raw sign sequence and
cross-checked with the same formula printed in Weaver 2022 Eq. 18 (PDF p14). Weaver prints `p ln B` in the numerator where Rubenchik
prints `p ln p`; I follow Rubenchik's page image:

    s(B,p) = (a / sqrt p) [ 0.008 - 0.0048 B - 0.047 p - 0.099 B p + (0.32 + 0.015 B) p ln p
                            + ln B (0.0056 - 0.89 p + 0.29 p ln p) ]

The bracket is negative with these signs (z axis points down), so depth is its magnitude. Sanity point from the text (PDF p19:
316L, A 0.4, P 200 W, 1.5 m/s, B about 6, p 0.17): |s| = 1.63, depth about 33 um for a = 20 um (my arithmetic, no data compared).
Table 1 (PDF p19) as printed lists for IN625 `B sqrt(u)/(A P) = 8` and `p u = 0.65` (u in m/s, P in 100 W, a = 20 um), which does not agree with
Ye's IN625 properties (I compute about 20 and 0.24). Treat the IN625 row of that table as unreliable.

Validity stated by the authors: B between 1 and 20, p between 0.1 and 5 (PDF p19). "More applicable to ... below deep key hole regimes" (PDF p25). No
vaporization, no recoil, no absorptivity increase.
Training data: none fitted. Fig. 1 (PDF p9) only shows the collapse of King's 316L data (Concept Laser M2, D4sigma 54 um), IN625 data from
GE Global Research (SLM machine, a about 20 um) and Ti-6Al-4V from Dilip et al. 2017 (EOS) in normalized variables (PDF p8 and p26, acknowledgment).
Neither NIST AMB2018 nor Lane IN625 tracks are in it (the paper is dated 2018, Lane 2020 is later; the NIST mds2-2923 plates were made
in 2018 and published in 2023). Verdict: the law is independent of N3.

Closed form used by Weaver (Eq. 13, `d = 0.25 delta dH/hs` with `delta = sqrt(sqrt 2 D sigma / v)`, Eq. 5, Weaver PDF p8, SOURCES_ke_scaling section 7.3):
the 0.25 "comes from Fabbro's analysis of Rubenchik's data" (Weaver PDF p8), independent of N3. Weaver's fit of its variables on its own tracks gave slope 0.256
(0.247, 0.266), R squared 0.948 (Table 3, PDF p34), i.e. the constant is consistent with the NIST tracks but was not fitted to them.

### 3.2 Weaver, Heigel, Lane 2022 (`nihms-1855299.pdf`, J. Manuf. Process. 73, 551)

Tracks: 80 IN625 bare-plate single tracks, EOS M270 plus AMMT, 122 to 195 W, 200 to 1200 mm/s, D4sigma 50 to 322 um, plus ten Lane 2020 EOS tracks
(PDF p6 Sec. 2.2, SOURCES_in625_regime section 3.2). Properties (Table 2, PDF p33): T0 300.15 K, T_m 1563.15 K, T_v 3500 K, rho 8440,
k 28.78, cp 719.92. Scaling-law predictions (Eq. 13 to 15) and constants:

| law | form (PDF page) | constants | tuned on |
|---|---|---|---|
| Rubenchik closed form (Eq. 13) | `d = 0.25 delta dH/hs`, A "constant" (Fig. 7a inset, not in text) | 0.25 (Fabbro on Rubenchik), A back-solved 0.40 by the previous lane (SOURCES_ke_scaling) | A: Lane CBM depths (Table 5); 0.25: not tuned |
| Ye (Eq. 14) | `d = 2 sigma K A L_th`, A_e = 0.70 (1 - exp(-0.66 beta A_m L_th)), A_m 0.28 | K 0.6, 0.66, 0.70 as published | not tuned |
| Modified Ye | A_m 0.5, ceiling 0.8, exponent 1.32 (PDF p11 to p12) | adjusted "until the percent difference was clustered around zero" (PDF p12) | Weaver's own 80 tracks |
| Fabbro (Eq. 15) | `d = A P / ((T_v - T_0)(m Pe + n) k)`-type with m 2.4, n 3 (PDF p8 to p9) | A 0.8, T_v 3500 K "adjusted within reason" to match slope (PDF p10) | Weaver's tracks |

Table 5 (PDF p36): percent difference of predicted depth for Lane CBM A, B, C (150 W 400, 195 W 800, 195 W 1200 mm/s, D4sigma 100 um), defined
as difference divided by the average (not by the measurement): Rubenchik -13.9, -6.8, -6.3; Fabbro -41.2, -22.5, -17.7; Ye -51.2, -68.5, -92.6;
adjusted Ye -2.6, -1.0, -11.8. Measured depths 150.75, 91.28, 60.54 um (Table 4, PDF p35). The seven benchmark thermal models M1 to M7 (same table)
are -49.6 to -95.2 percent on case A. Text conclusion (PDF p12): "percent difference is as high as 35 %" for the best law. Appendix A (PDF p14 to p15, Fig. A1):
Rubenchik's universal functions versus Weaver's measurements, "rather poor agreement". Weaver Sec. 6.1 (PDF p12): "single most influential parameter in the scaling laws ... is the
absorption coefficient".

Independence: the 80 tracks include the NIST workbook plates (mds2-2923, the N3 NIST groups) and the Lane CBM B tracks, so every constant adjusted on them is contaminated
(section 6).

### 3.3 King et al. 2014 (`king2014.pdf`, J. Mater. Process. Technol. 214, 2915)

King gives no fitted depth law. Eq. 2.6 (PDF p2): dH/hs = A P / (hs sqrt(pi D v sigma^3)) with `I = I0 exp(-r^2 / 2 sigma^2)` (footnote 1). Eq. 2.7: keyhole
threshold from surface temperature reaching boiling. Experiments: Concept Laser M2, 316L, two D4sigma 52 and 130 um, two sets of 28 tracks plus 14 tracks at 54 um
(PDF p9 to p10). Depth over sigma collapses below the keyhole threshold with scatter, and "the two lines ... are separated by d/sigma = 0.2" for the two beam sizes
(PDF p9), so the normalized enthalpy "lacks some physics" in the dependence on beam size in conduction mode. Threshold about 30 plus or minus 4 (SOURCES_in625_regime section 3.1).
Alternative scalings quoted (PDF p2): Gladush and Smurov `d` versus `A P ln(...)`, and Fabbro `d proportional to A P / v`; King says neither collapses the data as well. Computable use:
a regime gate on dH/hs only. Validity: 316L, 52 and 130 um beams, powder bed (28 tracks) and powder-covered plates. Independent of N3.

### 3.4 Fabbro 2020 (`fabbro2020.pdf`, Appl. Sci. 10, 1487)

Deep-penetration thermal model (Sec. 2, PDF p2 to p3, Eq. 1 to 5): vertical cylindrical keyhole of diameter d = spot diameter, wall at T_v, conduction loss per
depth `K (T_v - T_0) g(Pe)`, `g(Pe) = m Pe + n` with `Pe = V_w d / (2 kappa)`, m = 2.4 and n = 3 for 2 <= Pe <= 10 (PDF p3, from ref. [16]). Depth:

    e = A(R) P / ( K (T_v - T_0) (m Pe + n) ),    R = e / d                         (Eq. 2 and 3)

with K the solid conductivity and kappa the solid diffusivity. Equivalent line `A P / (d R) = a + b V_w d`, `a = n K (T_v - T_0)`, `b = m K (T_v - T_0) / (2 kappa)` (Eq. 4 and 5).
Micro-welding model, inclined keyhole front (Sec. 3, PDF p7, Eq. 11 to 13): `R = A_F(R) P / ( d (a1 + b1 V_w d) )` with `a1 about 2.1e5 W/m`, `b1 about 1.2e10 J/m3`, `a1 = n1 K (T_v - T_0)`,
`b1 = m1 K (T_v - T_0) / (2 kappa)`, m1 about 2.1, n1 about 2.2, Fresnel absorptivity A_F(1) about 0.32, A_F(R) 0.31 to 0.36 over the aspect ratios used (PDF p8). With a threshold power P* (Eq. 14, PDF p8):
`R = A_F(R) (P - P*) / (A_F(1) P_t)`. These constants were obtained on the Ti-6Al-4V X-ray data of Cunningham 2019 (spot 95 to 140 um); for IN625 only the property-based forms of a1 and b1 can be recomputed.
My arithmetic with Weaver Table 2 IN625 values (k 28.78, kappa 4.74e-6, T_v 3500 K, T_0 300 K): a1 about 2.0e5 W/m, b1 about 2.0e10 J/m3 (not a source value).
Validity: keyhole mode with R from 0.5 to 2.5, 120 um spot (Fig. 4, PDF p7), thermal form for Pe 2 to 10. Weaver's tracks have Pe 2.1 to 27.2 (Weaver PDF p10) and an aspect ratio below 1 for conduction rows,
where Weaver found Fabbro overpredicts by up to 50 percent. Independent of N3 (Ti-6Al-4V and steel data), but Weaver's use of it is tuned (A 0.8, T_v 3500 K).
Note: the app already carries a Fabbro keyhole kernel (`fabbro_keyhole_depth_m`, `python/lpbf_thermal_solver.py`) with flat absorptivity.

### 3.5 Gan et al. 2021, Nature Communications 12, 2379 (`s41467-021-22704-0.pdf`; same text as `gan2021.pdf`)

From `SOURCES_ke_scaling_2026-10-10.md` section 3 (equations read from Europe PMC JATS; PDF page 2 holds Eq. 1 and 2, page 3 Eq. 3 to 5 and Eq. 6):

    Ke = eta P / ( (T_l - T_0) pi rho c_p sqrt( alpha v r0^3 ) )   (Eq. 1),   e* = e / r0 = 0.4 (Ke - 1.4)   (Eq. 2)
    eta = 0.7 (1 - exp(-0.6 Ke_m L_d*)),  Ke_m L_d* = eta_m P / ( (T_l - T_0) pi rho c_p v r0^2 )   (Eq. 6 and 7)

with r0 the 1/e2 radius (D4sigma / 2 for Gaussian). Regimes Ke < 1.4 conduction, 1.4 to 6.0 transition, above 6.0 keyhole. e is the X-ray vapour depression depth. Quote: "depth
of the fusion region is certainly larger than" the keyhole depth (PDF p2). Data: 87 rows, Ti-6Al-4V (Cunningham experiments), Al6061, SS316, spots 84 to 144 um, 103 to 522 W, 0.3 to 1.2 m/s.
Liquid properties needed (convention at the liquidus). Not an etched-depth law and no IN625 data; the N3 screen with it failed (RESULTS_ke_width_n3, verdict FAIL). Independent of N3.

### 3.6 Cunningham et al. 2019, Science 363, 849 (`cunningham2019.pdf`, plus `aav4687_cunningham_sm.pdf`)

Ti-6Al-4V bare plate, 95 and 140 um spot, X-ray imaging. PDF p2 to p3: the vapour depression depth is "highly linear" in power at fixed speed (Fig. 3B and 3C). Stationary drill rate rises linearly with power
density above about 0.4 MW/cm2 (Fig. 2C, PDF p1 and p2). Model after Fabbro: `tan(theta) = V_d(rho) / V_w`, depth `d_kh = D tan(theta)`; "using the full beam sizes ... overestimated the depths by a factor of
about 2" (PDF p3), so a reduced effective beam is required. Constants are Ti-6Al-4V specific (digitized transition lines `P = 0.04691 v + 96.25` vapour and `P = 0.08448 v + 102.13` melt pool in W and mm/s, repo
`data/benchmark/cunningham-ti64-2019`). Not computable for IN625 without a measured drill-rate line. Independent of N3.

### 3.7 Comparison of computable forms

| law | output | needs | regime it describes | IN625 etched depth evidence |
|---|---|---|---|---|
| Rubenchik Eq. 11 | isotherm depth (conduction numerics) | A, rho, c, D, T_m, a | conduction to shallow transition | Weaver App. A: poor, errors about 50 to 100 percent |
| Rubenchik closed form, 0.25 | depth, linear in dH/hs | A, hs, delta | transition and keyhole (collapse data) | Weaver: -13.9, -6.8, -6.3 on CBM with A 0.40 (contaminated A) |
| Ye 2019 | depth, linear in A_e L_th | A_m, A_e curve, hs | conduction to keyhole with absorptivity ramp | IN625 foils (Ye Fig. 5C); Weaver: -51 to -93 on CBM unless modified |
| Fabbro 2020 | keyhole depth | k, kappa, T_v, A, m, n | keyhole (Pe 2 to 10) | Weaver: overpredicts conduction, underpredicts deep keyhole |
| Gan 2021 | vapour depression depth | eta(P), liquid properties | transition and keyhole (Ke above 1.4) | not an etched depth; N3 screen failed |
| King 2014 | threshold only | dH/hs | keyhole onset | 316L; Weaver sees about 30 in IN625 |

## 4. Temperature-dependent IN625 properties

### 4.1 Sources

1. Mills et al. 2006 (`mills2006_ni_superalloy_property_models.pdf`, ISIJ Int. 46, 623). Composition-based models for Ni superalloys, no IN625 table of its own. Locator PDF p7 (printed 628), Sec. 9.2 and 9.3:
   `a_298 = 3.0 + 0.10 (mass% Al)` in 1e-6 m2/s, `k_298 = 11.7 + 0.45 (mass% Al)` W/(m K), at 1500 K `a = 4.2e-6 m2/s` and `k = 27.3 W/(m K)` for all alloys (fully gamma), liquid
   `a = 5.1 plus or minus 0.5e-6 m2/s`, `k_liq` from `k = a cp rho` or the Wiedemann-Franz law (CMSX4 25 to 33.6 W/(m K)). Uncertainty "10 %" on calculated liquid k (PDF p7). IN625 curves in Figs. 12 and 13.
   Mills states an "urgent need for reliable property measurements on liquid" Ni alloys (abstract, PDF p1). For IN625 (Al about 0.2 mass%) the room temperature values are about 3.0e-6 m2/s and 11.8 W/(m K).
2. Sabau et al. 2018 (`sabau2018_in625_jmatpro_properties.pdf`, ORNL/TM-2018/1044). JMatPro data fitted for Truchas, Appendix D input file (PDF p63, report p57):
   solid `cp(T) = 361.8513 + 0.1251116 T + 1.740843e-4 T^2 - 7.527126e-8 T^3` J/(kg K) (T in K), solid `k(T) = 4.929465 + 1.574994e-2 T` W/(m K) (linear in T), liquid cp 700, liquid k 30, density constant
   7700 kg/m3 plus a liquid deviation polynomial, transition 1563 to 1623 K. These are the same numbers as the repo snapshot `data/benchmark/in625-bareplate-screening/in625-thermal-snapshot-v1.json` (which cites doi:10.1007/s11663-020-01808-w Appendix B).
   My arithmetic: cp 413 J/(kg K) and k 9.65 at 300 K, cp 695 and k 29.5 at 1563 K. Enthalpy from 293 K to 1563 K is 715 kJ/kg, to 1623 K is 757 kJ/kg (mushy cp blended), latent heat 290 kJ/kg on top. Mean cp over 293 to 1623 K 569, mean solid k 19.5.
   Sabau also reports IN625 single tracks from GE Global Research, see section 5.3.
3. Grohol 2025 thesis chapter 4 (`grohol2025_dissertation_ch4.pdf`, Purdue, CC BY 4.0; in Turkish cover page, English body). The chapter is 304L and IN718 (NIST IN718 benchmark), not IN625 (cover page says so). Sensitivity locators: Fig. 4.7 and Table 4.6 (PDF p29 to p36, thesis p. 93 to 100).
4. Gan, Jones, Lu, Liu 2021 (`gan2021_benchmark_in625_tracks.pdf`, Table 1, PDF p4): IN625 solid rho 8440, liquid rho 7640, solid cp `0.2441 T + 338.39`, liquid cp 709.25, solid k `0.0163 T + 4.5847`, liquid k 30.078, latent 290 kJ/kg, solidus 1563 K, liquidus 1623 K, preheat 353 K.
5. Knapp 2022 (PDF p10, Table 2, JMatPro): rho 7569.92, liquidus 1620 K, liquid cp 579.28, liquid k `8.275 + 0.01472 T` (32.2 W/(m K) at 1623 K); the solid rows are garbled in the text layer.
6. Weaver 2022 Table 2 (PDF p33): rho 8440, k 28.78, cp 719.92, T_m 1563.15 K, T_v 3500 K (single values near the melting point, not temperature dependent).

### 4.2 Served constants versus sources

App (`python/lpbf_thermal_solver.py` lines 34 to 52, Rosenthal path lines 573 to 613): rho 8440, k_s 9.8, k_l 30, cp_s 410, cp_l 750, T_liq 1350 C, T_sol 1290 C, T_boil 2880 C, latent 290 kJ/kg, A_IR 0.38
(provenance class `legacy-estimated-secondary`, unvalidated). The kernel uses `k_th = (k_s + k_l)/2 = 19.9`, `cp = (cp_s + cp_l)/2 = 580`, `alpha_th = 4.07e-6 m2/s`, and for the normalized-enthalpy index the solid pair (9.8, 410, alpha 2.83e-6).
It also multiplies the Rosenthal power by `1 / (1 + 0.55 St)`, `St = L_f / (cp (T_liq - T0))`; for IN625 at 20 C St = 0.376 and the factor is 0.83. The code comment states that this factor and its 0.55 have no published source.

| quantity | app served | sources | comment |
|---|---:|---|---|
| k at room T | 9.8 | Sabau 9.65 (300 K); Gan 9.47; Mills 11.8 | solid value of the index and nothing else |
| k near T_m | k_th 19.9 | Sabau 29.5 at 1563 K; Mills 27.3 at 1500 K; Weaver 28.78; Gan 30.1 | mean over 293 to 1563 K (Sabau) is 19.5, so the blend reproduces a mean, not the hot value |
| cp | 580 mixed, 410 solid | Sabau mean 569 over 293 to 1623 K; peak 695 at 1563 K; liquid 700 to 750 (Gan 709, Sabau 700, Knapp 579) | mixed cp times (T_liq - T0) gives 771 kJ/kg versus Sabau 757 kJ/kg, a 2 percent difference |
| density | 8440 | Sabau 7700 constant (liquid 7640 Gan, 7570 Knapp) | up to 9 percent in rho cp |
| diffusivity at liquidus | 4.07e-6 mixed | Sabau liquid 5.6e-6; Mills liquid 5.1e-6; Mills 4.2e-6 at 1500 K | Rosenthal width scale depends on rho cp (T_liq - T0), not on alpha |
| T_liq | 1350 C (1623 K) | Gan, Sabau 1623 K; Knapp 1620 K | consistent |
| T_boil | 2880 C | Weaver T_v 3500 K (steel value of Fabbro), Hong 3188 K (IN718), Grohol IN718 estimate 3181 K | boiling only enters the Fabbro kernel and recoil |
| latent heat | 290 kJ/kg | Gan 290, Sabau 290, Mills-based 227 (other module) | used inside the uncited St factor |
| A_IR | 0.38 | Section 2 | the one input that moves depth most |

### 4.3 Property sensitivity (Grohol and Shin 2024, thesis Table 4.6, PDF p36 and Fig. 4.7)

304L-SS (T_v 3080 K, baseline A 35 percent, k_l 36.3 W/(m K)), 150 W, 500 mm/s: surface-normal absorption 27, 33, 39, 50 percent gives depth 54, 77, 96, 119 um versus baseline 85
(-36, -10, +13, +39 percent) and width -7 to -1 percent: "increasing the absorption from 27% to 39% increased the molten pool depth by 76%" (PDF p33). Liquid k 20, 26.9, 50, 167.5, 209.2 W/(m K)
gives depth +6, +5, -7, -40, -40 percent (the last two are artificial conduction collapses). T_v 3122, 3200, 3375 K gives -3, -8, -18 percent. For 200 W, 250 mm/s (keyhole) absorption 27 to 50 percent moves depth -20 to +13 percent
(saturates, "keyhole already captures the majority of the laser energy", PDF p30), liquid k 26.9 and 50 move it by 2 and -2 percent.
IN718 (150 W-960 mm/s case in the extract: baseline A 31.5 percent, k_l 36.2, T_v 3000 K): A 20 and 51 percent give depth -37 and +35 percent; k_l 30 gives +1 percent; T_v 3188 and 3335 K give -6 and -12 percent.
Beam diameter plus 10 / minus 10 um gives depth -24 / +5 percent and width +26 / -14 percent (IN718, PDF p34, Fig. 4.9).
Reading: absorptivity moves depth with an elasticity of about 0.8 (IN718) to 1.6 (304L conduction side); k_l and T_v within their physical ranges are second order; beam size is first order. Caveat: these are
304L and IN718 results from a high-fidelity keyhole model, not IN625 and not a conduction kernel. IN625 sensitivities were not published in the file.

### 4.4 Independence

Property sources are independent of N3 tracks. Gan, Knapp and Hong used the properties for models calibrated elsewhere, the property numbers themselves are not tuned on N3 tracks.

## 5. What published models needed to match AMMT and CBM

### 5.1 Hong, Grohol, Shin 2021 (`hong2021_nist_benchmark.pdf`, Integr. Mater. Manuf. Innov. 10, 58)

Beam inputs (PDF p3, Table 1): D4sigma AMMT 170 um, CBM 100 um, both nominal for CBM. Process (Table 2): AMMT A 137.9 W / 400 mm/s, B 179.2 / 800, C 179.2 / 1200; CBM A 150, B 195, C 195 W at the same speeds.

Absorptivity inputs: fluid and conduction (Ansys Fluent) models, "laser absorptivity was calibrated to 0.37 to match the depth of the AMMT-B case" and it "was the only tuning parameter" (PDF p4). High-fidelity welding model
(sharp interface, ray tracing, Fresnel absorption, plume attenuation): normal-incidence absorptivity 0.43 from IN718 data, drops past the Brewster angle (PDF p7, Fig. 2), no tuning to IN625 depth. Domain 2 x 1 x 1 mm, beam as in Table 1.

Depth results from printed bar labels (um; Fig. 3a PDF p7 for AMMT, Fig. 4a PDF p8 for CBM; group order is measured, high fidelity, fluid, conduction, then reference models; order read from the figure legend):

| case | measured | high-fidelity (A0 0.43) | conduction (A 0.37) | conduction / measured | fluid |
|---|---:|---:|---:|---:|---:|
| AMMT A | 42 | 40 | 51 | 1.21 | 46 |
| AMMT B | 36 | 34 | 39 | 1.08 | 36 |
| AMMT C | 30 | 26 | 29 | 0.97 | 27 |
| CBM A | 151 | 139 | 63 | 0.42 | 53 |
| CBM B | 91 | 84 | 50 | 0.55 | 44 |
| CBM C | 60 | 54 | 40 | 0.67 | 35 |

The association of the two middle bars to "fluid" and "conduction" follows the legend order and the text statement that conduction "is slightly more accurate than the fluid model" (PDF p8); the labels were read from a rendered page.
Quotes: "high fidelity welding model was the only model that reasonably predicted" CBM depth, "maximum error of 10%" (PDF p8); fluid and conduction models "vastly under-predicted the depth" (PDF p8); AMMT keyholes do not form
(PDF p7).
Answer: no conduction model matched CBM at any case; the closest, CBM C, still underpredicts by 33 percent. For AMMT the Fluent conduction model with A 0.37 tuned on AMMT-B gives +21, +8, -3 percent, so the AMMT conduction
overprediction pattern (largest at the lowest speed) persists even with a tuned A. The benchmark entries Fan and Li, Gan, Robichaud and Kollmannsberger ([8] to [11] in Hong) used absorptivities from 0.2 to 0.51 (PDF p6);
Gan et al. calibrated 0.43 (PDF p7); Kollmannsberger used a calibrated anisotropic conductivity "highly dependent on the material-specific scaling factor" (PDF p8). Their constants were calibrated on the AM-Bench 2018 data itself and were not retrieved.

### 5.2 Weaver 2022 as the same question (see section 3.2)

Beam: EOS spot sizes estimated from manufacturer data and a caustic model (D0 78 um), AMMT measured by CCD (PDF p4 to p5). Scaling laws needed A 0.50 baseline and 0.80 ceiling to bring CBM depth to within a few percent (modified Ye), with A 0.40 for the Rubenchik form.

### 5.3 Gan, Jones, Lu, Liu 2021 benchmark (`gan2021_benchmark_in625_tracks.pdf`, Integr. Mater. Manuf. Innov. 10, 177) is not NIST AM-Bench

This paper models the AFRL AM Modeling Challenge Series (EOS M280, gas-atomized IN625 powder 40 um layer on an AM substrate, D4sigma 0.1 mm, argon, preheat 353 K), not AMB2018-02 (PDF p2). Eleven single tracks are the calibration set (Table 2, PDF p7):
P 225 to 370 W, v 953 to 1230 mm/s in the cases whose P and v pairing is legible in the text layer, widths 76 to 148 um, corrected depths 76 to 148 um (cases 1 to 11 with original and corrected depth; the pairing of P and v for cases 1 and 2 is not legible in the extraction, read the page image before use).
Heat source (Eq. 5 and 6, PDF p3): Gaussian cylinder with absorptivity `max(beta P / V, 0.28)` (alpha, beta, gamma calibrated by proper generalized decomposition), ranges alpha 1 to 2.5e-3, beta 1.3 to 2.0e-7, gamma 3.8 to 4.5e-7 (PDF p7); the calibrated values are not printed in the text layer. Minimum absorptivity constrained to 0.28 (Ye).
This is an independent campaign for N3 purposes (different machine, powder bed on printed substrate, D4sigma 100 um nominal), with the caveat that the regime and substrate differ from bare plates.

### 5.4 Other independent IN625 depth data found in sources

Sabau 2018 GE Global Research single tracks (PDF p21, Tables 1 and 2, bulk IN625, nominal beam 80 um): 100 W / 300 mm/s width 132 depth 46 (conduction); 150 W / 300 mm/s width 196 depth 168 (keyhole); 75 W at 50, 100, 200 mm/s width 158, 131, 110 depth 58, 49, 39; 150 W / 1000 mm/s width 89 depth 31 um.
The authors' fluid model with A 0.5 underpredicted these depths by 22 to 31 percent (conduction) and 79 percent (keyhole, Tables 4 and 5, PDF p29). Uncertainties and the number of sections per track are not given. These six tracks are independent of N3 and could serve as a source-clean check set, with the beam size as the large uncertainty.

## 6. Contamination list (constants tuned on any N3 held-out track)

N3 held-out groups: nist-20180905, nist-20180910, nist-20181026, lane-CBM, lane-AMMT.

| # | constant | source and locator | tuned on | N3 group(s) contaminated |
|---|---|---|---|---|
| 1 | "Modified Ye": A_m 0.5, ceiling 0.8, exponent 1.32 | Weaver 2022 PDF p11 to p12, Fig. 7d | adjusted until percent difference clustered near zero on Weaver's 80 tracks | all NIST groups from mds2-2923 and lane-CBM (Weaver Table 4, 5 CBM A, B, C) |
| 2 | Rubenchik closed form with A 0.40 (back-solve) | SOURCES_ke_scaling section "Contamination note", from Weaver Table 5 | Lane CBM A, B, C depths | lane-CBM. The 0.25 is clean |
| 3 | Fabbro A 0.8, T_v 3500 K | Weaver PDF p10 | chosen to bring slope toward the expected value on Weaver's tracks | all groups represented in Weaver's tracks |
| 4 | Weaver K 0.6 / slope claims | Weaver Table 3 PDF p34 | regression on the same tracks (a diagnostic, not fitted constants) | descriptive only |
| 5 | A 0.277 to 0.307 and r_xy 53.5 to 84.7 um | Knapp 2022 Table 5 PDF p15 | Lane AMMT A, B, C width and depth | lane-AMMT |
| 6 | A 0.37 (Fluent conduction and fluid) | Hong 2021 PDF p4 | AMMT-B depth (Lane) | lane-AMMT, and it fails on lane-CBM |
| 7 | A 0.43, anisotropic conductivity factor, others in Hong's reference models [8] to [11] | Hong PDF p6 to p8 | AM-Bench 2018 AMMT and CBM data (values not retrieved) | lane-AMMT, lane-CBM |
| 8 | In625 keyhole-mode cut 13.6 on the app index | `docs/research/RESULTS_in625_regime_2026-10-11.md` (repo, already in the served path) | morphology (depth over width) of the 56 mds2-2923 EOS rows, a fit split | nist groups: the fit uses their depth and width (a regime label, not a depth, but any depth path gated on 13.6 inherits it) |
| 9 | A_IR 0.38 | repo `SECONDARY_THERMOPHYSICAL_DB` | no locator found | unknown, treat as legacy and unsourced |

Clean (not tuned on N3 tracks): Deisenroth absorptance values; Ye 0.28, 0.6, 0.66, 0.70, 1.72 (foils); Rubenchik Eq. 11 (conduction numerics) and the 0.25 (Fabbro on Rubenchik); King 30 plus or minus 4;
Fabbro m, n, a1, b1 (steel and Ti-6Al-4V); Gan 0.4, 1.4 (Ti, Al, SS316); Sabau/Mills/Gan property sets; Sabau GE tracks; Gan AFRL tracks.
Partially clean: Hong high-fidelity A0 0.43 (IN718 literature average, but the same value Gan et al. calibrated on AM-Bench, as Hong notes, PDF p7).

## 7. Open items and what was not read

1. Deisenroth per-condition values are read off a figure, not a table. Contact data (NIST) or a digitization pass would tighten them. The 80 W discrepancy of up to 16 percent unmeasured energy leaves the absorbed values uncertain by that amount in transition.
2. Ye Fig. 6 IN625 A_e points, Ye Fig. 2F to I cross-sections: figure only.
3. Knapp 2022 Fig. 9 posterior on the combined A, B, C calibration: text only ("peak around 0.3").
4. Weaver Fig. 7a inset (A for Rubenchik), Fig. 7 and Fig. 9 data: figure only. The 0.40 is the earlier lane's back-solve.
5. Hong references [8] to [11] and the Gan AM-Bench entry constants not retrieved. Lane ref. [143] (about 40 percent absorptance) not in the Grohol extract.
6. Rubenchik Eq. 11 sign reconstruction: verified by two independent sign sources (pdftotext raw order and Weaver Eq. 18) and a sanity point, but a numerical check against the published Figure 9 contour was not done.
7. Rubenchik Table 1 IN625 row and the sqrt(pi) discrepancy between the T_s/T_m form and `dH/(2^(3/4) pi hs)` in Rubenchik PDF p6: the paper is internally inconsistent by that factor; the later lane must fix one definition before coding it.
8. CBM beam D4sigma 100 um remains nominal only (`.orchestra/reports/cbm_beam_metadata_2026-10-11.md`). Hong, Weaver and Knapp all inherit it. Knapp's calibrated radii below the nominal half-diameter show the nominal beam is not self-consistent for AMMT either.
9. No Python and no model was run; the app index values in sections 1 and 2.1 are arithmetic on the process inputs listed.
