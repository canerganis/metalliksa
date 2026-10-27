# Note: why the guided tour cannot yet run the NIST bare-plate case (2026-10-27)

Status: planning note. Nothing was run for this note; the earlier boiling-limit stop is a past finding from `docs/ACTIVE_WORK.md`.

## What `sourcePenetration_um` is

It is the width parameter of the volumetric Gaussian heat source, not a measured optical absorption depth. At normal incidence the depth profile is `exp[-2(d/p)^2]`, so at `d = p` the density is `e^-2` of the surface value. At oblique incidence the normal-depth scale is `p cos(theta)`. Cell integrals are taken and normalised to the total absorbed power in the represented region (`python/lpbf_core_physics.py`, `cell_weights`). It is a numerical assumption, not an optical measurement, and it differs from a Beer-Lambert 1/e depth or a keyhole depth. No primary source fixing this parameter for bare IN718 in the 5 to 150 um range was found in the review; that does not prove none exists. No single value of `p` should be presented as physically sourced.

## NIST AMB2022-03 inputs

Source: [AMB2022-03 measurement and challenge descriptions, v1.0.1](https://www.nist.gov/document/amb2022-03-measurement-and-challenge-descriptions-version-101), sections 2.1 to 2.2, pp. 2 to 5, Tables 1 and 2.

- 3.17 mm IN718 plate, 1070 nm Yb fibre laser
- 285 W, 960 mm/s, 67 um D4sigma beam, 10 mm single track in +X
- 23.5 +/- 1 C ambient, 5 +/- 0.5 degree incidence angle

Treating D4sigma as the solver's 1/e^2 diameter assumes an ideal Gaussian; it is not a measured 2D profile. NIST gives no Gaussian volumetric source width. Support thickness, contact resistance, bottom boundary and azimuth are not given and must be labelled assumptions in any request.

## Cell budget

Square-domain path, coarsest allowed 80 um mesh: span = 10000 + 6 x 33.5 = 10201 um, so nx = ny = 128. Plate cells = ceil(3170 / ~79.7) = 40, plus at least 1 support cell.

128 x 128 x 41 = 671,744 cells, above the 600,000-cell reference limit (`python/lpbf_simulation.py`, `cell_count > 600000`). More support thickness only raises it. The arithmetic is covered by `python/test_lpbf_cell_budget.py` (no solver run). The UI also caps track length at 3000 um.

## Earlier stop

A previous 20 um NIST-input cost run (hypothetical 5 um source width, estimated absorptivity 0.38) stopped at the boiling validity limit and produced no completed result (`docs/ACTIVE_WORK.md`). Absorptivity and `p` must not be tuned to finish a run or to match the NIST measurement.

## Conclusion

A bare-plate tour needs two things that do not exist as verified, planned work yet:

1. A planned physics bump for a rectangular-corridor layered domain that fits the cell budget, with lateral-boundary and width sensitivity, interface conservation, source capture and parity with existing results. Removing the `square` check alone is not enough. (`calculate_mesh_domain` already has a rectangular-corridor branch for the single-track bare-plate case; whether the layered path is proven with it needs that bump record.)
2. An evaporative model for IN718. The existing evaporative model is Ti-6Al-4V only.

Until then the tour stays on Quick Screening with its existing different-surface warning, and the comparison stays labelled "Comparison, not validation". `experimentalValidation` and evidence classes are unchanged.
