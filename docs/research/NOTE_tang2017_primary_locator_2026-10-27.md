# Note: Tang 2017 primary locator for the overlap criterion (2026-10-27)

Status: source check only. No code, payload or golden changed. The proposed basis string below is a proposal for the maintainer and is not applied.

## Source

Tang, M.; Pistorius, P. C.; Beuth, J. L. (2017). Prediction of lack-of-fusion porosity for powder bed fusion. Additive Manufacturing 14, 39-48. doi 10.1016/j.addma.2016.12.001 (ScienceDirect pii S2214860416300471).

Full text: **not obtained.** Checked 2026-10-27: Unpaywall (is_oa false, no oa_locations), OpenAlex (oa_status closed, no repository full text), Semantic Scholar (openAccessPdf empty, CLOSED), Crossref (Elsevier TDM licence only), ScienceDirect and MDPI pages (HTTP 403 to a scripted fetch), web search for a CMU KiltHub or other institutional copy (none found). No sci-hub or similar used. No PDF of the primary was downloaded or stored. (Repo policy: `/papers/**/*.pdf` is gitignored, only `papers/INDEX.md` is tracked.)

So the exact equation number, page and section in the primary remain **unverified**. Everything below is secondary.

## What the secondaries establish

1. Harkin et al. 2023 (Int. J. Adv. Manuf. Technol. 126, 659-673; local copy `papers/harkin2023_lof_hatch_spacing.pdf`, p. 660 to 661, Eq. 5): `(H/W)^2 + (T/D)^2 <= 1`, H hatch spacing, T layer thickness, W melt pool width, D melt pool depth. Plotted as a unit circle on axes H/W and T/D. Inside means LOF avoided. Harkin does not say where D is measured from and does not state an ellipse assumption. It says Tang's relationship "takes account of the lack of fusion between adjacent tracks and the substrate".
2. Richter, Pribe, Weber, Subraveti, Oskay (NASA Langley and Vanderbilt), accepted preprint, NTRS 20250007052, `https://ntrs.nasa.gov/api/citations/20250007052/downloads/manuscript_accepted_preprint.pdf` (6.6 MB, sha256 `699a50fa7b2ca2511677bcda008e05dad16a95e89a2516eabac9862515dbddac`, licence not stated in the text, read only, not stored). Sections 1 and 2.2, Eq. 1 to 7, derive the criterion for **identical, semi-elliptical melt pool cross-sections** (width W = 2a, depth D = b, each pool infinitely long), neighbours spaced H apart. Neighbouring pools intersect at x = H/2 at depth y = D*sqrt(1 - (H/W)^2), with y measured downward from the top of the layer (the y axis is the inverse build direction). No porosity requires that intersection depth to be at least the layer thickness L, their Eq. 5. Rearranged, Eq. 6: `(L/D)^2 + (H/W)^2 <= 1` (their `C_LoF` is the left side, Eq. 7). They credit the semi-elliptical criterion to Tang et al. ref [7], the MS&T 2015 proceedings "Geometric model to predict porosity of part produced in powder bed system" (pp. 129-136), and the porosity-fraction simulation (ellipses on a pixelated 2D slice) to the 2017 paper. They state the criterion is Boolean and that the 2017 geometric model is different and more involved.
3. Subraveti and Richter (Vanderbilt, IMMI 2024) and a secondary web summary: same criterion, same dual half-ellipse 2D model. The PDF fetch returned HTML, so this is a pointer only, not re-read.
4. Zhu et al., Mukherjee et al. and arXiv 2304.04149 write other forms (`D >= t`, an `h_max` bound, `(h/W)^2 + t/(t+D) >= 1`). These are not Tang's form and must not be confused with it.

Abstract-level fact from the landing pages: the 2017 paper is a geometry-based simulation of insufficient melt pool overlap. Nothing more was readable.

## Formula, as far as the secondaries agree

`(h/W)^2 + (L/D)^2 <= 1` is the no-LOF condition. L is the layer thickness, h hatch spacing, W full melt pool width, D depth below the top of the layer, semi-elliptical cross-section, identical neighbouring pools. The index compared to 1 is the sum of the two squared ratios. Above 1 means LOF predicted, at or below 1 means avoided. Harkin 2023 reports the unit value problematic with analytic geometry (Eq. 9 to 11, Conclusions) and, per Harkin, Tang's approximation does not apply to Al-Si-Mg alloys.

## Comparison with the code

| Item | Harkin 2023 Eq. 5 | Richter et al. derivation (secondary for Tang) | Code (`lpbf_thermal_solver.py` ~1150, `tang_pt` ~1386) |
|---|---|---|---|
| Form | `(H/W)^2 + (T/D)^2 <= 1` | `(H/W)^2 + (L/D)^2 <= 1` | `(h/W)^2 + (t/D)^2`, flagged when `> 1` |
| Threshold | 1 | 1 | 1.0 (the 0.80 margin is an unsourced advisory) |
| Layer term | T layer thickness | L layer thickness | `layerThickness_um` |
| Depth reference | not stated | from the top of the layer | modelled depth, presumed from the free surface (not re-verified here) |
| Pool shape | not stated | semi-ellipse, identical pools | not an ellipse: model width, depth merged from conduction and Fabbro legs |

## Mismatches and caveats

1. No arithmetic mismatch between the code and either secondary form. The squares, the sum and the threshold match.
2. The criterion presumes a semi-elliptical cross-section. The code applies it to a modelled W and a merged D that is not a half-ellipse, so the geometric derivation does not strictly hold. The basis string says "not a measured half-ellipse" but does not name the semi-elliptical assumption as the source's premise.
3. Depth reference: the derivation takes D from the top of the powder layer, with the layer boundary at depth L. The code's `t` is the nominal layer thickness, so the code is consistent only if its D is also measured from the powder top surface, not from the substrate or a consolidated-layer level. Not checked here. Whether the primary uses powder or consolidated layer thickness is open, because the primary was not read.
4. "Primary not in the library" remains true. The equation locator (number, page) in the primary is unknown. The earlier origin of the semi-elliptical criterion appears to be the 2015 MS&T proceedings, not only the 2017 paper.

## Proposed replacement basis string (not applied)

```
Tang overlap criterion (h/W)^2 + (t/D)^2 <= 1 (Tang, Pistorius and Beuth 2017, Addit. Manuf. 14, 39-48; primary full text not obtained, equation number unverified). Read through Harkin 2023 Eq. 5 and the semi-elliptical derivation of Richter et al. (NASA NTRS 20250007052, Eq. 5 to 7): identical semi-elliptical pools, D measured down from the top of the powder layer, t the layer thickness. Sourced for measured melt pool geometry; Harkin 2023 Eq. 9 to 11 and Conclusions find the unit value problematic with analytic geometry (Ti-6Al-4V, one machine). Here applied to modelled geometry (model width and a depth merged from the conduction and Fabbro legs, not a measured half-ellipse), so an index above 1.0 indicates a risk, never a blocking gate.
```

Changing `TANG_CRITERION_BASIS` moves served payloads and parity goldens, so it needs a planned bump.

## To close the gap

Obtain the primary through interlibrary loan or a manual download by the maintainer, then confirm the equation number and page, whether L is powder or consolidated layer thickness, and the depth reference. The 2015 MS&T proceedings paper is also worth a look.
