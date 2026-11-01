# Design note: guided tour bare-plate path for NIST AMB2022-03 case 0 (2026-11-02)

Status: design note, lane `tour`, base `ac753ee5`. Outcome: **blocked**. No source, pin, golden or fingerprint was changed. The tour stays on Quick Screening with its existing "Screening only, comparison not validation" labelling.

## Finding: the cell count is not the binding blocker

`docs/research/NOTE_tour_bare_plate_blockers_2026-10-27.md` costs the layered square path (671,744 cells at 80 um). The non-layered bare-plate `rectangular-corridor` route already exists in the pinned solver and accepts a 10 mm track. Its cell count from `calculate_mesh_domain` (default corridor width 6 x beam diameter = 402 um) is 511 x 21 x 16 = **171,696 cells at 20 um** (386,127 at 15 um), under the 600,000 limit with no code change.

The binding blocker is the fixed-material **boiling validity stop** at case-0 power (285 W, 960 mm/s, 67 um, 23.5 C, registry IN718 absorptivity 0.32). Whether a run finishes depends on the unsourced `sourcePenetration_um`, which must not be chosen to finish a run.

## Measured probes (tiny, 500 um track, 20 um mesh, CPU reference, one at a time)

| Probe | Cells | Result | Wall time | Peak working set |
|---|---|---|---|---|
| Corridor, `sourcePenetration_um` 40 (value of the 2026-09-24 preregistration) | 12,096 (36 x 21 x 16) | Stopped at the boiling limit in the first steps (3108.6 K before the failing step, limit 3123.15 K) | 0.22 s | 62.7 MB |
| Corridor, `sourcePenetration_um` 150 (largest allowed) | 12,096 | Completed, peak 2871 K | 3.40 s | 64.1 MB (60.9 MB before the solve) |
| IN718 proxy evaporative solver (`lpbf_proxy_evaporative_solver.py`), square, `sourcePenetration_um` 20, declared default thresholds | 20,736 (36 x 36 x 16) | Completed, label Unresolved; recoil/capillary onset exceeded, so **depth, length and volume are not reported** (width only, conditional) | 16.82 s | 64.0 MB (no rise over imports) |

Peak memory at these sizes is dominated by the interpreter and numpy, so it gives no basis for moving the 600k limit. These probes are feasibility checks, not comparisons; no width or depth from them is compared to NIST. The threshold value of `sourcePenetration_um` between 40 and 150 was deliberately not searched.

Uncalibrated scaling, not measured: 3.40 s x (171,696 / 12,096 cells) x (10.92 / 1.02 ms simulated, scan plus 0.5 ms cooling) is about 520 s for the full 10 mm corridor at p = 150, above the 300 s default worker timeout. The 2026-09-24 preregistration estimated more (5.5 x 300 s).

## Options

| Option | What it changes | Verdict |
|---|---|---|
| A. Existing non-layered corridor, 10 mm, 20 um | Tour config only; no solver change. Homogeneous 0.32 mm IN718 substrate, not the 3.17 mm plate on support (depth-of-domain sensitivity untested) | Fits the budget, but finishes only for large p. Picking p to finish is the tuning the 2026-10-27 note and `docs/ACTIVE_WORK.md` (2026-09-25) forbid. **Blocked.** |
| A'. A plus existing boiling cap (`evaporationModel: true`, `marangoniMultiplier: 1` to drop the uncited k_eff surrogate) | Tour config only; cap is frozen code | Finishes for any p, but the cap keeps excess enthalpy in the cell and is "not an evaporation model". The recorded decision is to keep the NIST path unavailable rather than force it. **Maintainer decision.** Not run. |
| B. IN718 proxy evaporative solver, square, 3 mm track (161 x 161 x 16 = 414,736 cells at 20 um) | Tour config and a different job route; shorter track than NIST | Its own onset gate withholds depth at case-0 power (probe above). No width plus depth comparison. **Not viable.** |
| C. Layered path on a rectangular corridor | `lpbf_simulation.py` validate and layered solver; fingerprint | Planned physics bump (note item 1). Also inherits the boiling stop. |
| D. Raise the 600k cap on a measured basis | `lpbf_simulation.py` (fingerprinted) | Fingerprint change; does not address boiling; 80 um is already too coarse for a ~100 um deep pool. |
| E. Coarser tour-only mesh | `BOUNDS.mesh_um` max 80 (fingerprinted) | About one cell over the pool depth; fingerprint change. Not viable. |
| F. Symmetric half-domain (y >= 0) | Solver symmetry boundary; fingerprint | Halves cells but is a solver change and still hits boiling. |

No option gives a completed case-0 width and depth without either tuning `sourcePenetration_um`, adopting the boiling cap against a recorded decision, or a physics change. Per the lane rule, implementation stops here.

## Recommendation

1. Planned physics bump (research lane, physics owner): an energy-leaving evaporation sink for IN718 on the existing non-layered bare-plate corridor route, sourced like the Ti-6Al-4V and proxy models, with fingerprint regeneration and review. After it lands, the tour can use the corridor at 20 um (171,696 cells) with no cell-limit change. The 2026-10-27 note's claim that only Ti-6Al-4V has an evaporative model is outdated: the IN718 proxy solver exists, but its onset gate withholds depth at this power.
2. Maintainer decision, if a faster interim is wanted: whether option A' may appear in the tour as a labelled screening arm with p shown as an assumption. If yes, the engineering work is tour config, a bare-plate run preset and tests; no pinned file changes.
3. Plate thickness and support stay with the layered rectangular-corridor bump (note item 1); not needed for the tour if (1) or (2) is chosen and the domain-depth assumption is labelled.
