# Sources for the Keyhole-number depth candidate (Ke scaling)

Date: 2026-10-10. Branch `claude/ke-width-n3`, created from the tip of
`codex/depth-identifiability` (62e49bd0). Sources only. No model was run, no
parameter was fitted and no N3 or N4 score exists. `experimentalValidation=false`.
The only computations are (a) a reproduction of the Gan et al. Supplementary Data 1
table against the Gan equations and (b) a process-input-only regime audit
(`python/tools/ke_regime_audit.py`) that reads power, speed and beam diameter and
never opens a measured width or depth.

## 1. Findings that matter for the pre-declaration

1. Citation. The law is Gan, Kafka, Parab, Zhao, Fang, Heinonen, Sun, Liu,
   "Universal scaling laws of keyhole stability and porosity in 3D printing of
   metals", Nature Communications 12, 2379 (2021), doi:10.1038/s41467-021-22704-0
   (CC BY 4.0). No Science 2022 paper by these authors was found. The brief's
   "Science 2022" is a misattribution (Science appears only as the venue of the
   X-ray source paper, Cunningham et al., Science 363, 849, 2019). An arXiv preprint
   (arXiv:2005.00117) defines a different Keyhole number and must not be used (section 2).
2. Observable. Gan's e is the keyhole (vapour depression) depth read from in situ
   X-ray images, divided by the laser spot radius r0. The paper states that the
   fusion region (melt pool) depth "is certainly larger than the keyhole depth and
   does not linearly scale with keyhole depth" (Results, paragraph after Eq. 2).
   The N3 observable is the etched, solidified melt pool depth. These are different
   quantities.
3. Absorptivity is not a constant. With constant eta = 0.38 or 0.28, Gan's own
   Supplementary Data 1 is not reproduced (R squared 0.22 and 0.10). The law holds
   (R squared 0.98) only with the process-dependent eta of Supplementary Data 1,
   which follows the saturating form of Eq. (6) with effective constants that the
   paper does not print (section 5).
4. Property convention. Data 1 uses liquid-phase density, heat capacity and
   conductivity at or above the liquidus. Because Ke is proportional to
   1/sqrt(rho cp k), the app's frozen solid constants (8440, 410, 9.8) would raise Ke
   by a factor 2.19 relative to the liquid IN625 set of section 6.
5. No primary source gives a vapour depth to etched melt depth relation. Gan's
   Supplementary Method 3 states that e is "approximately equal to" the melt pool
   depth in keyhole and transition mode, as a derivation assumption, and this
   contradicts the main text. A "conduction shell" link is therefore a new,
   unsourced hypothesis, not a transcription (section 7).
6. Threshold consistency. For a Gaussian beam with r0 = 2 sigma, Ke = (dH/hs) /
   sqrt(8 pi) (derivation in section 7), so Gan's keyhole threshold Ke = 6.0 equals
   King's dH/hs of about 30.1. Weaver et al. 2022 observe the dH/hs of about 30
   threshold in etched IN625 melt data. The regime boundary is therefore supported
   for IN625 etched geometry; the depth law above it is not.
7. A sourced closed-form etched-depth law for IN625 already exists and was tested
   on the same Lane and NIST tracks that N3 holds out (Rubenchik et al. 2018 as
   evaluated by Weaver et al. 2022, section 7.3). It is worth declaring as an
   additional arm or as the link, because it is written in nearly the same
   variables as Ke. Constants tuned by Weaver on those tracks must not be used.
8. Regime audit (process inputs only, section 8). Under Gan thresholds, all three
   Lane CBM conditions (cases A, B, C) fall in the transition band (Ke about 2.6 to
   5.9), all Lane AMMT conditions have Ke at most 1.46, and most N3 conditions have
   Ke below 6. Part A can therefore only act as a transition-band vapour depression
   term for most rows, where Gan's own e* is at most about 2.

Verdict on applicability to etched melt depth of IN625: doubtful. See section 9.

## 2. Access log and hashes

Nothing was taken from Sci-Hub. Nature and Springer PDFs sit behind a browser
check and a PMC PDF behind a reCAPTCHA page; these were not bypassed. Open
machine-readable routes were used instead.

| item | route | bytes or hash |
| --- | --- | --- |
| Gan 2021 main text, JATS XML with TeX equations | Europe PMC REST `fullTextXML` for PMC8062476, retrieved 2026-10-10 | SHA-256 032006fb65dee06709e8d70f54ceeccc43388e18cca09ac1c6757d5bff2a77af |
| Gan 2021 Supplementary Information (23 pages) | static-content.springer.com `41467_2021_22704_MOESM1_ESM.pdf` | SHA-256 22a8d2dc870bbd83f6bd3330899437911733f9335d52758d95a328bd6993d6e5 |
| Gan 2021 Supplementary Data 1 (xlsx) | `..._MOESM4_ESM.xlsx` | SHA-256 b52d9173eb3a63983dd87c56b2720abd419a200e9594b863218de13da6a7597a, identical to the copy recorded in `data/benchmark/gan-keyhole-2021/LICENSE-ATTRIBUTION.md` |
| Gan 2021 description of supplementary files | `..._MOESM3_ESM.pdf` | SHA-256 1be86f67ed5d0b333f0c72b05861f7073656db3a17a69f11b982bd109476c1e3 |
| arXiv:2005.00117 PDF (variant, not used) | arxiv.org/pdf/2005.00117v1 | SHA-256 9b6cbfe68c543479f48aead651590b6a9ebbf22a0b268784566351f02cad3d51 |
| Weaver, Heigel, Lane 2022, JATS XML with MathML | NCBI efetch db=pmc id=9890508 | SHA-256 6c9d5f7c1d3003483a1942f98d98a50053146ad560f4e35854fe530c6cf9ada7 |
| Li, Lu, Amin, Liu 2022, arXiv:2208.02907v1 | arxiv.org/pdf/2208.02907 | SHA-256 9ea629550bf135f09e21e4bbabeee32db0d9636fe72960de9be8ba122c92cb08 |

The downloaded files are not committed. Page numbers below follow the journal PDF
as already recorded in `data/benchmark/keyhole-reference-relations-2026/published_relations.csv`;
the JATS text carries no pagination, so equation numbers and section headings are
the primary locators.

The arXiv PDF I read is titled "Universal low-dimensional scaling laws in 3D
printing of metals" and defines a different law: e* = 5.12 minus 5.07 exp(minus
1.0 P*/(Pe T*)) with Ke = ((P minus P0)/(V d^2)) (1/(Cp (Tv minus T0))) ((Tm minus
T0)/(Tv minus T0)), using the vaporisation temperature, the spot diameter d and an
offset power P0. That is not the published Ke. Use only the Nature Communications
form below.

## 3. Equations, as published

All from Gan et al. 2021 (Nat. Commun. 12, 2379), Results, subsection "Universal
scaling of keyhole aspect ratio and its stability" unless stated.

Eq. (1), Keyhole number:

    Ke = eta * P / ( (T_l - T_0) * pi * rho * C_p * sqrt( alpha * V_s * r0^3 ) )

eta absorptivity, P laser power, T_l liquidus temperature, T_0 substrate temperature,
rho density, C_p heat capacity, alpha thermal diffusivity (k / (rho C_p)), V_s scan
speed, r0 laser radius. SI units: W, K, kg/m3, J/(kg K), m2/s, m/s, m. Ke is dimensionless.

Eq. (2), keyhole aspect ratio, "nearly linear" (dashed line in Fig. 1a):

    e* = e / r0 = 0.4 * (Ke - 1.4)

No R squared and no uncertainty on the constants 0.4 and 1.4 are reported. e is the
X-ray keyhole depth, r0 the laser spot radius (Supplementary Fig. 1).

Modes, same section: conduction e* = 0 or Ke < 1.4; transition e* <= 2 or
1.4 <= Ke <= 6.0; keyhole e* > 2 or Ke > 6.0. Eq. (2) gives e* = 1.84 at Ke = 6.0
and e* = 2 at Ke = 6.4, so the two thresholds are consistent only approximately.

Eqs. (3) and (4), proportionalities: e* ~ eta P V_s^(-1/2) r0^(-3/2) and
e* ~ (T_l - T_0)^(-1) (pi rho C_p)^(-1) alpha^(-1/2).

Eq. (5), fluctuation of the aspect ratio: delta e* = 0.36 * Ke^0.86. Stability:
Ke < 16 small fluctuation, almost no porosity; Ke > 30 chaotic keyhole. Not needed for depth.

Eq. (6), absorptivity (Results, "Energy absorption revealed by multiphysics modeling"):

    eta = eta_absor = 0.7 * [ 1 - exp( -0.6 * Ke_m * L_d* ) ]

Eq. (7):

    Ke_m * L_d* = eta_m * P / ( (T_l - T_0) * pi * rho * C_p * V_s * r0^2 )
    L_d* = delta_z / r0 ,  delta_z = sqrt( alpha * r0 / V_s )

eta_m is the flat-surface (minimum) absorptivity of each material, taken from Ye et
al. 2019. Eq. (6) was fitted to 30 multiphysics simulations (Al6061 and Ti-6Al-4V)
and checked against measured absorptivity of Ti-6Al-4V, SS316 and IN718 from Ye et al.
(Fig. 3g). Eq. (6) as printed has no floor at eta_m; Supplementary Data 1 shows a
floor (section 5).

Eqs. (8) and (9), porosity and normalised energy density: not needed here.

Supplementary Methods 3, Eqs. (36) to (54): the scaling is derived from the steady
Gaussian-source conduction problem in a semi-infinite body with constant properties
at the melting point, latent heat neglected and no vaporisation. Eq. (37) is the
boundary flux 2 eta P / (pi r0^2) exp(-2 (x^2 + y^2) / r0^2). Hence r0 is the 1/e2
intensity radius, equal to D4sigma / 2 for a Gaussian. Eq. (41) defines the
temperature scale T_S = eta P / (pi rho C_p sqrt(alpha V_s r0^3)), so Ke is the
inverse of the dimensionless liquidus temperature T_l* (Eq. 45). Below the keyhole
threshold Ke is therefore the conduction similarity group of the moving Gaussian
source. Eq. (48) then makes the melt depth a function of T_l* and p = alpha/(V_s r0)
only. Locator: Supplementary Information pages 6 to 8.

## 4. Definitions and conventions

1. Observable: keyhole depth e, measured from the surface to the deepest point of
   the X-ray attenuation contour of the vapour depression, per frame at 20 microsecond
   spacing; vertical error bars are the maximum and minimum of e* over the middle
   2 mm of the scan (Fig. 1 caption, Methods "Data processing and quantification").
   Laws apply to the quasi-steady melt pool and "are inapplicable" at track starts,
   ends and turns (Discussion).
2. r0: laser spot radius, 1/e2 (Supplementary Eq. 37, Eq. 23 of the model). Spot
   diameters were set by defocus: 84, 93, 114, 144 micrometres (about 50 micrometres
   at focus, plus or minus 5 micrometres; Methods, "Selective laser melting apparatus").
   The Fig. 1 caption quotes a spot size of 44 to 70 micrometres without saying radius
   or diameter; it matches radii of the 84 to 144 micrometre diameters, but the paper
   does not state this. Supplementary Data 1 uses
   r0 = d/2. The repo notes that Supplementary Data 2 lists r0 = 75 micrometres for
   the 140 micrometre cases, a Gan-internal inconsistency that is not used.
3. T_0: substrate temperature, fixed, 303 K for Ti-6Al-4V and 293 K for Al6061 and
   SS316 (back-computed from Data 1 columns T_l minus T_0 = 1630, 622, 1430 K).
4. eta: process-dependent, see section 5. The main text calls it "coupled with the
   keyhole morphology".
5. Properties: liquid values (Supplementary Table 1, page 20), listed in
   Supplementary Data 1 as K, rho, cp, alpha. Ti-6Al-4V: K 33.4, rho 3920, cp 830;
   Al6061: K 90, rho 2415, cp 1170; SS316: K 26.9, rho 6881, cp 790. The temperature at
   which Table 1 polynomials are evaluated is not stated; the Data 1 values equal the
   above-liquidus branch.
6. Measured data: Supplementary Data 1 has 87 rows (71 Ti-6Al-4V at 95 and 140
   micrometre spots, 9 Al6061 at 88 micrometres, 7 SS316 at 110 micrometres), power
   103 to 522 W, speed 0.3 to 1.2 m/s. The Ti-6Al-4V rows are the Cunningham 2019
   experiments and are not independent of that paper. IN625 and IN718 are not in the
   keyhole dataset. IN718 enters Gan only through Ye's absorptivity data and the
   porosity compilation.
7. Materials of validity: Ti-6Al-4V, Al6061, SS316, bare plate, single track, argon,
   vacuum chamber backfill, 1070 nm single-mode Gaussian laser, 100 to 520 W.

## 5. Reproduction on Supplementary Data 1 (my computation, no model run)

Ke was recomputed from the Data 1 columns with Eq. (1), r0 = d/2, eta from the eta
column, and compared with e/r0 and with Eq. (2). Printed Ke labels in Gan Figs. 2
and 1 (for example Al6061, 416 W, 0.75 m/s, Ke 7.68) are reproduced.

| variant of eta | R squared against e* | rms residual of e* | MAPE of e* for e* > 1 (n = 68) |
| --- | ---: | ---: | ---: |
| eta column of Data 1 | 0.977 | 0.39 | 11.5 percent |
| Eq. (6) and (7) as printed, eta_m = 0.26, 0.01, 0.33, floored at eta_m | 0.925 | 0.71 | 14.2 percent |
| constant eta = 0.38 | 0.218 | 2.28 | 50.3 percent |
| constant eta = 0.28 | 0.099 | 2.44 | 60.0 percent |

Ordinary least squares of e* on Ke with the Data 1 eta: slope 0.397, intercept
minus 0.403 (zero at Ke = 1.02), R squared 0.979, Ke range 1.55 to 31.4. So the
published 0.4 and 1.4 are matched in slope, and the zero crossing is at 1.0 to 1.4.

The Data 1 eta column is reproduced exactly by eta = max(eta_m, 0.7 (1 - exp(-0.6 X)))
with X = c * eta_m * P / ((T_l - T_0) pi rho C_p V_s r0^2) and a material constant c of
0.932 for Ti-6Al-4V, 0.748 for Al6061 and 0.775 for SS316 (constant within each
material). Equivalent effective eta_m: 0.242, 0.0075, 0.256 against the printed
0.26, 0.01, 0.33. The floor value 0.26 appears in four Ti-6Al-4V rows. The paper does
not explain c, so Eq. (6) as printed reproduces the law to 14 percent, not 11.5
percent, and eta carries a 5 to 20 percent unexplained scale in Ke.

Consequence: any Ke implementation must use Eq. (6) with an eta_m for IN625 and
must carry the eta ambiguity as an uncertainty. A constant-eta Ke has no support in
Gan's own data.

## 6. Constants for IN625

Gan convention requires liquid-phase properties at the liquidus and an eta_m.

| quantity | value | source and locator | status |
| --- | --- | --- | --- |
| liquid density rho | 7640 kg/m3 | Li, Lu, Amin, Liu 2022, arXiv:2208.02907v1, Table 3 (page 10), "Liquid density" | secondary use in a model table of the Gan and Liu group; cites Capriccioli and Frosi 2009, Pawel and Williams 1985, Valencia and Quested 2013; the underlying measurement was not read |
| liquid heat capacity C_p | 709.25 J/(kg K) | same table, "Liquid specific heat capacity" | same; the repo snapshot `in625-thermal-snapshot-v1.json` has 700 from doi:10.1007/s11663-020-01808-w Appendix B, a JMatPro-based set; Weaver 2022 Table 2 uses 719.92 |
| liquid conductivity k | 30.078 W/(m K) | same table, "Liquid thermal conductivity" | same; snapshot 30; Weaver 28.78 |
| liquid diffusivity alpha | 5.551e-6 m2/s (k / (rho C_p)) | derived | derived |
| solidus, liquidus | 1563 K, 1623 K (1290 and 1350 C) | same table; consistent with the frozen kernel threshold 1350 C | consistent with `screening_props` |
| flat absorptivity eta_m | 0.28 | Ye et al. 2019, Adv. Eng. Mater. 21, 1900185, Table 1, row "Minimal absorptivity (Am) in this work", via `data/benchmark/ye-2019-absorptivity/table1_min_absorptivity.csv` | measured on 0.5 mm bare foils, a minimum read as a flat-melt estimate; Weaver 2022 uses 0.28 as the Ye baseline |
| T_0 | 293.15 K | N3 ledger (20 C, Lane states no preheat) | assumption |
| r0 | D4sigma / 2 | Lane Table 1 and NIST workbook column "Est. Spot Diameter (D4sigma = Dg)"; equals the 1/e2 radius for a Gaussian (Gan Supp. Eq. 37) | consistent with the frozen beam convention |
| AMMT powers | 137.9 and 179.2 W for commanded 150 and 195 W | NIST AM-Bench overview Note 2, as recorded in `DEPTH_TRANSFER_DIAGNOSIS_2026-10-09.md` | resolved |

Ke is proportional to 1 / sqrt(rho C_p k). Property-set sensitivity, same other inputs:

| property set | sqrt(rho C_p k) | Ke relative to the liquid set |
| --- | ---: | ---: |
| liquid set above (7640, 709.25, 30.078) | 12766 | 1.00 |
| frozen app solid nominal (8440, 410, 9.8) | 5823 | 2.19 |

Heugenhauser and Kaschnitz, High Temp. High Press. 48 (2019) 4, doi:10.32908/hthp.v48.726,
measured IN625 density from 150 to 1400 C including the liquid; only the abstract was
readable, so no liquid-density value could be confirmed from it. IN718 and 316L are
not needed: the N3 ledger declares IN625 only (the NIST workbook also holds 72 IN718
rows, which are outside the declared ledger). For reference, Gan's own SS316 set
is in Supplementary Table 1.

All IN625 liquid properties above are model-input values, not measurements read
from a primary measurement paper. The application's evidence class for them is
literature estimate, not validated.

## 7. Vapour depth to melt depth

### 7.1 What the sources say

1. Gan main text: fusion depth exceeds keyhole depth and does not scale linearly with
   it, owing to differing melt pool geometry and flow (Results, paragraph after Eq. 2).
2. Gan Supplementary Method 3 (page 7): "In the keyhole mode or transition mode, the
   keyhole depth e is approximately equal to the melt pool depth z_m." This is a
   derivation assumption used to write Eq. (49); no data in Data 1 or Data 2 test it
   (Data 1 has keyhole depth, length and front angle only; the fusion boundary depth
   is not tabulated). Supplementary Fig. 6b compares simulated and X-ray melt pool
   depth for Al6061 only, as a figure (not read).
3. Cunningham et al. 2019 (Science 363, 849), Fig. 3A, 95 micrometre spot,
   Ti-6Al-4V, as digitized in `data/benchmark/cunningham-ti64-2019/fig3a_transition_lines_digitized.csv`
   (read uncertainty 4 W): the vapour depression transition is P = 0.04691 v + 96.25
   and the melt pool transition (depth to width 0.5) is P = 0.08448 v + 102.13
   (W, mm/s). The vapour depression appears 20 to 50 W below the melt pool
   keyhole transition. With the Data 1 eta recipe I compute Ke of 2.2 to 4.9 on the
   vapour line and 3.6 to 6.3 on the melt line (speeds 0.4 to 1.2 m/s). So the two
   transitions are different events and neither sits at Ke = 1.4 or a single value.
4. No primary source was found that gives melt depth as vapour depth plus a
   conduction shell, or any closed form linking e to etched melt depth.

### 7.2 Threshold mapping between Ke and normalised enthalpy

King et al. 2014 (J. Mater. Process. Technol. 214, 2915; Table 3 and the 30 plus or
minus 4 transition, as transcribed in `published_relations.csv` row
`king2014-keyhole-threshold-316l`) define dH/hs = A P / (rho hs' sqrt(pi D u sigma^3))
with the 1/e2 radius 2 sigma and hs = rho c (T_m or T_l minus T_0). With r0 = 2 sigma:

    Ke = (dH/hs) / sqrt(8 pi) = (dH/hs) / 5.013

so Ke = 6.0 corresponds to dH/hs = 30.1 and Ke = 1.4 to 7.0, for equal eta and
equal property sets. King's 30 plus or minus 4 was defined on etched melt pool
depth over half width exceeding 0.5 for 316L. Weaver et al. 2022, Section 4.2, report:
"The same threshold is observed in this data on IN625" (etched depth, dH/hs about
30), with scatter beyond it. Gan's Ke = 6.0 is hence consistent with an etched-depth
keyhole boundary, with the caveat that the three authors' eta and property
conventions differ.

### 7.3 Etched-melt-depth scaling laws already tested on IN625

Weaver, Heigel, Lane, "Laser spot size and scaling laws for laser beam additive
manufacturing", J. Manuf. Process. 73 (2022) 551 to 560, doi:10.1016/j.jmapro.2021.10.053
(PMC9890508). 80 IN625 bare-plate single tracks, NIST AMMT and EOS M270 (the EOS M270
is Lane's CBM), D4sigma 50 to 322 micrometres, depth from the substrate surface to the
etched (aqua regia) melt pool bottom, plus the 10 Lane 2020 tracks. This is the same
population as the N3 held-out sets, so it is a contamination warning as well as a source.

Equations as printed (MathML, section 3 "Theory"; sigma is the beam variance
parameter with D4sigma = 4 sigma and spot radius 2 sigma):

    Eq. (3)  dH/hs = A P / ( hs sqrt( pi D u sigma^3 ) )
    Eq. (4)  hs = rho c (T_m - T_0)
    Eq. (5)  delta = ( D sqrt(2) sigma / u )^(1/2)           Rubenchik convention
    Eq. (6)  L_th* = sqrt( D 2 sigma / u ) / (2 sigma) = 1 / sqrt(Pe)
    Eq. (7)  beta = A P / ( pi hs sqrt( D u (2 sigma)^3 ) )
    Eq. (8)  d / (2 sigma) = K beta L_th*,  K = 0.6          Ye et al. 2019
    Eq. (9)  A_e = A_m for d/(2 sigma) <= 1;  A_e = 0.70 (1 - exp(-0.66 beta_Am L_th*)) above
    Eq. (13) d = 0.25 delta dH/hs                            Rubenchik et al. 2018
    Eq. (14) d = 2 sigma K beta_A L_th*                      Ye et al. 2019
    Eq. (18) universal d(B, p) regression, Appendix A (Rubenchik et al. 2018)

Note beta L_th* = A P / (pi hs u (2 sigma)^2), the same group as Gan's Ke_m L_d*.
Gan Eq. (6) and Ye Eq. (9) share the form; the exponent constants differ (0.6 and 0.66).
Weaver Table 2 IN625 inputs: T_0 300.15 K, T_m 1563.15 K, rho 8440, k 28.78, c 719.92.
Weaver Table 3 (fits of the plotted variables, not depth errors): Rubenchik slope 0.256
(0.247, 0.266), R squared 0.948; Ye slope 0.631, R squared 0.912; modified Ye 0.518,
R squared 0.971. Weaver Table 5, percent difference of predicted depth against Lane
CBM A, B, C (EOS M270, 150 W 400 mm/s, 195 W 800 and 1200 mm/s, D4sigma 100):
Rubenchik minus 13.9, minus 6.8, minus 6.3; Ye minus 51.2, minus 68.5, minus 92.6;
Fabbro minus 41.2, minus 22.5, minus 17.7; modified Ye minus 2.6, minus 1.0, minus 11.8.
Text: depth errors up to 35 percent at best, above 50 percent below depth over radius 1.

Inference, not a source statement: the three Rubenchik errors above are
reproduced with Eq. (13) using Table 2 properties, Eq. (5) as printed and a constant
A = 0.40 (all three cases give 0.40 within rounding); with delta from 2 sigma the same
constant would be 0.336. The text read does not state A (it is in the Fig. 7 inset,
not read), so this is a back-solve, not a citation.

Warnings. (i) Weaver's "modified Ye" constants (A_m 0.5, ceiling 0.8, exponent 1.32)
were adjusted until the percent difference on these very tracks clustered near zero;
they are fitted to N3 held-out data and must not be used. (ii) The constant 0.25
comes from Fabbro's analysis of Rubenchik's data; whether Rubenchik's IN625 points
include Lane or AM-Bench tracks was not verified (that paper is not open). (iii) The
Rubenchik depth is linear through the origin in Ke, d / delta_z close to
1.25 Ke when hs uses T_m minus T_0 and the conventions are aligned, a different
form from Gan's 0.4 (Ke minus 1.4) r0.

## 8. Regime audit on the N3 ledger (process inputs only)

`python/tools/ke_regime_audit.py` reads power, speed and D4sigma from the N3
loaders (`load_nist`, `load_lane`, pinned hashes) and computes Ke with the section 6
liquid constants. No width or depth is accessed. Counts are of unique
(power, speed, D4sigma) conditions. "eta_eq6" is Gan Eq. (6) and (7) with eta_m = 0.28,
floored at 0.28; "eta flat" is 0.28.

| group | conditions | Ke range, flat 0.28 | Ke range, eta_eq6 | below 1.4 / 1.4 to 6 / above 6 (eta_eq6) |
| --- | ---: | --- | --- | --- |
| NIST 20180828 (train) | 13 | 0.72 to 6.47 | 0.72 to 15.3 | 3 / 6 / 4 |
| NIST 20180905 | 6 | 0.70 to 4.52 | 0.70 to 7.66 | 3 / 2 / 1 |
| NIST 20180910 | 45 | 0.56 to 4.52 | 0.56 to 7.66 | 17 / 21 / 7 |
| NIST 20181026 AMMT spot series | 14 | 0.73 to 9.16 | 0.73 to 21.6 | 5 / 5 / 4 |
| Lane CBM (A, B, C) | 3 | 2.64 to 3.52 | 2.64 to 5.91 | 0 / 3 / 0 |
| Lane AMMT (A, B, C) | 3 | 1.10 to 1.46 | 1.10 to 1.46 | 2 / 1 / 0 |

Reading: Gan's keyhole mode is reached only by a minority of N3 conditions, and
the eta_eq6 result for Lane depends on the saturating eta. For Lane CBM the thresholds
alone place all three cases in the transition band, where Gan's law gives e* below
about 1.8 (at most about 90 micrometres at r0 = 50 micrometres) and the law is least
tested. The Lane A observed CBM over AMMT depth ratio of 3.55 would therefore have
to come largely from the melt shell around the vapour depression, which is the part
with no source.

## 9. Applicability verdict

Doubtful, for these reasons.

1. Wrong observable (vapour depression, not fusion depth); the authors say the two
   do not scale linearly together.
2. No IN625 data in the law; materials Ti-6Al-4V, Al6061, SS316 only. IN625 enters
   only through eta_m = 0.28 and liquid properties from a secondary table.
3. Needs process-dependent eta with unexplained effective constants; constant eta fails
   on Gan's own data.
4. Factor 2.19 sensitivity to the solid versus liquid property convention.
5. Vapour to melt link unsourced; Gan's own SI and main text disagree.
6. Quasi-steady, bare-plate, vapour-recoil-driven regime; most N3 rows sit below
   Ke = 6 where the law is a conduction-group extrapolation with a zero crossing at
   Ke = 1.0 to 1.4 and no data below Ke of about 1.5 in Data 1.
7. The only IN625 etched-depth tests of closed-form scaling laws (Weaver 2022) found
   errors of 35 percent at best after tuning on these same tracks, and the untuned
   Rubenchik law at 6 to 14 percent on CBM A, B and C only.

What does hold: the keyhole regime boundary Ke about 6 is equivalent to the
dH/hs about 30 threshold seen in etched IN625 data (section 7.2).

## 10. Inputs for the next step (not declarations)

1. The Ke part can be declared as a regime gate and a vapour-depression term, but
   the etched-depth link must be declared as a new hypothesis, labelled unsourced,
   or replaced by a sourced law (Rubenchik Eq. 13, with A stated in advance and not
   taken from Weaver's tuned values).
2. Declare the eta rule (Eq. 6 with eta_m = 0.28, floor, and the effective-constant
   ambiguity as a sensitivity) and the property set (liquid, section 6) in advance.
3. Treat the N3 held-out groups as the contamination set for Weaver's tuning.

## 11. Not read or not available

1. Gan Supplementary Data 2 (transient powers) and Supplementary Fig. 6 values.
2. Rubenchik, King, Wu 2018 (paywalled; no open copy located), Fabbro 2019, Ye 2019
   body (only Table 1 via the repo transcription).
3. Weaver Fig. 7 insets (A for the Rubenchik fit).
4. Valencia and Quested 2013, Pawel and Williams 1985, Capriccioli and Frosi 2009
   (underlying IN625 liquid values); Heugenhauser and Kaschnitz full text.
5. The Nature PDF page numbers (JATS used).

## Contamination note: Rubenchik A = 0.40 back-solve

The Rubenchik absorptivity A = 0.40 back-solve is itself derived from Lane CBM held-out
depths (via Weaver Table 5). It is contaminated by the held-out depths of this ledger.
It must not seed or tune any future arm that is scored on Lane CBM, and it is not used
in this lane.
