# SOL-T batch records, 2026-10-16

Scope: records lane of batch T on `feat/solidification-solt`, pin `13203cac19bf69db80b546c6e67ed846a0941e35ea4ad62e53a786de073c46ca` (code `8de9373d`, re-pin `b5ee77d2`, goldens `dfde1f17`). Locked interpreter `.runtime/lpbf-win-py312`. Software and model comparison records only; nothing here is experimental validation or evidence of improved accuracy. No physics, tolerance or approval trailer changed in this lane.

**Error bands (full run, not a restamp; contract 3.7 item 4).** `python -B python/tools/lpbf_error_bands.py --date 2026-10-16 --jobs 4` on the committed row table; `--check` passes. New `bandsId` `lpbf-meltpool-error-bands-2026-10-16-b37692769673`, `DEPTH_BIAS_BANDS_ID` and the `DEPTH_BIAS_CELLS` mirror in the same commit (`601103ee`). 732 of 863 rows moved, all 316L; the 94 Ti64, 30 IN625 and 7 IN718 rows are bit equal; the table holds no AlSi10Mg row. 24 of 96 cells moved, all 316L (relative error pred / meas - 1):

| quantity / kernel / family / regime | n | median | p10 / p90 | coverage (equal weight) | state |
|---|---|---|---|---|---|
| depth / eagar-tsai / 316L / all | 730 -> 730 | -0.438 -> -0.445 | -0.613 / -0.021 -> -0.624 / -0.041 | 0.649 -> 0.655 | band-under-covers -> band-under-covers |
| depth / eagar-tsai / 316L / conduction | 166 -> 178 | -0.205 -> -0.241 | -0.365 / 0.116 -> -0.624 / 0.085 | 0.724 -> 0.523 | band -> band-under-covers |
| depth / eagar-tsai / 316L / keyhole | 442 -> 432 | -0.505 -> -0.505 | -0.570 / -0.019 -> -0.571 / -0.040 | 0.562 -> 0.580 | band-under-covers -> band-under-covers |
| depth / eagar-tsai / 316L / transition | 122 -> 120 | -0.613 -> -0.706 | -0.699 / -0.135 -> -0.706 / -0.187 | null -> null | insufficient-data -> insufficient-data |
| depth / goldak / 316L / all | 688 -> 684 | -0.445 -> -0.449 | -0.570 / 0.022 -> -0.576 / -0.001 | 0.658 -> 0.660 | band-under-covers -> band-under-covers |
| depth / goldak / 316L / conduction | 124 -> 132 | -0.061 -> -0.123 | -0.187 / 0.353 -> -0.576 / 0.304 | null -> 0.550 | insufficient-data -> band-under-covers |
| depth / goldak / 316L / keyhole | 442 -> 432 | -0.504 -> -0.505 | -0.570 / -0.007 -> -0.570 / -0.040 | 0.566 -> 0.577 | band-under-covers -> band-under-covers |
| depth / goldak / 316L / transition | 122 -> 120 | -0.565 -> -0.674 | -0.667 / -0.013 -> -0.674 / -0.065 | null -> null | insufficient-data -> insufficient-data |
| depth / rosenthal / 316L / all | 695 -> 691 | -0.445 -> -0.455 | -0.583 / 0.014 -> -0.594 / -0.010 | 0.646 -> 0.648 | band-under-covers -> band-under-covers |
| depth / rosenthal / 316L / conduction | 131 -> 139 | -0.100 -> -0.136 | -0.213 / 0.312 -> -0.594 / 0.261 | null -> 0.525 | insufficient-data -> band-under-covers |
| depth / rosenthal / 316L / keyhole | 442 -> 432 | -0.504 -> -0.505 | -0.570 / -0.017 -> -0.570 / -0.040 | 0.560 -> 0.578 | band-under-covers -> band-under-covers |
| depth / rosenthal / 316L / transition | 122 -> 120 | -0.583 -> -0.687 | -0.679 / -0.050 -> -0.687 / -0.099 | null -> null | insufficient-data -> insufficient-data |
| width / eagar-tsai / 316L / all | 731 -> 731 | -0.227 -> -0.238 | -0.355 / -0.034 -> -0.365 / -0.051 | 0.737 -> 0.745 | band -> band |
| width / eagar-tsai / 316L / conduction | 166 -> 178 | -0.146 -> -0.184 | -0.320 / -0.107 -> -0.327 / -0.120 | 0.364 -> 0.654 | band-under-covers -> band-under-covers |
| width / eagar-tsai / 316L / keyhole | 443 -> 433 | -0.229 -> -0.242 | -0.332 / -0.018 -> -0.341 / -0.035 | 0.771 -> 0.770 | band -> band |
| width / eagar-tsai / 316L / transition | 122 -> 120 | -0.271 -> -0.380 | -0.371 / -0.183 -> -0.380 / -0.197 | null -> null | insufficient-data -> insufficient-data |
| width / goldak / 316L / all | 689 -> 685 | -0.303 -> -0.319 | -0.432 / -0.042 -> -0.443 / -0.060 | 0.663 -> 0.678 | band-under-covers -> band-under-covers |
| width / goldak / 316L / conduction | 124 -> 132 | -0.409 -> -0.416 | -0.511 / -0.303 -> -0.507 / -0.321 | null -> 0.519 | insufficient-data -> band-under-covers |
| width / goldak / 316L / keyhole | 443 -> 433 | -0.273 -> -0.286 | -0.397 / -0.032 -> -0.409 / -0.050 | 0.789 -> 0.789 | band -> band |
| width / goldak / 316L / transition | 122 -> 120 | -0.392 -> -0.464 | -0.452 / -0.321 -> -0.464 / -0.338 | null -> null | insufficient-data -> insufficient-data |
| width / rosenthal / 316L / all | 696 -> 692 | -0.309 -> -0.322 | -0.433 / -0.043 -> -0.444 / -0.061 | 0.658 -> 0.665 | band-under-covers -> band-under-covers |
| width / rosenthal / 316L / conduction | 131 -> 139 | -0.404 -> -0.411 | -0.511 / -0.309 -> -0.507 / -0.328 | null -> 0.488 | insufficient-data -> band-under-covers |
| width / rosenthal / 316L / keyhole | 443 -> 433 | -0.274 -> -0.288 | -0.400 / -0.033 -> -0.413 / -0.050 | 0.789 -> 0.735 | band -> band |
| width / rosenthal / 316L / transition | 122 -> 120 | -0.396 -> -0.468 | -0.456 / -0.323 -> -0.468 / -0.338 | null -> null | insufficient-data -> insufficient-data |

Reading: lower 316L index values move tracks from the transition to the conduction class, so the Goldak and Rosenthal conduction cells gain eight tracks and leave insufficient-data; the Eagar-Tsai 316L conduction depth cell drops below the 0.70 coverage floor (`band` -> `band-under-covers`), so no depth cell reaches it now; the seven passing width cells are unchanged. Every failing cell stays reported. Nothing was tuned.

**Demo snapshots (`a30a4a6c`).** Engine on port 3100 with `METALLIX_PYTHON` set to the locked interpreter; `npm run demo:snapshots` recorded eight requests (nine snapshot/index files plus the manifest); the job-response file is renamed with its job identity. `npm run demo:snapshots:determinism` passes, ten files byte-identical across two runs.

**Dated records (new history; older records unchanged).** `LPBF_DATASET_COMPARISON_2026-10-16_solt.*` (`--include-wave2 --reuse-reference` the 2026-10-15 solbatch record, whose IN718 reference-transient block is unchanged because IN718 numerics are bit equal) and its common-subset comparison against 2026-10-15; `LPBF_KEYHOLE_BENCHMARK_2026-10-16_solt.*` (index evaluation and King conversion at the served 316L properties); `LPBF_LEADERBOARD_2026-10-16.json` after re-exporting `data/benchmark/leaderboard/inputs-v1.csv` and its manifest (39 Hofmann 316L rows change `regime_class_input`). `test_lpbf_keyhole_benchmark` keeps the 2026-10-07 record as the keyhole-regime history, reproduced at the pre-SOL-T 316L endpoints, and checks the new record at the served ones. The offline NIST note in `python/lpbf_public_datasets.py` now says the front cooling rate stays unavailable because SOL-C's co-located samples are not installed. NIST 2525 (Ti64, Warp sweep) and NIST 2716 (IN718) were not regenerated: both alloys keep bit-equal numerics, the locked interpreter has no Warp, and their tests bound to the 2026-10-14 records were already red at `dc6f5fdd` for the same stale-pin and missing-Warp reasons.

**Exposure (contract 3.7 item 1).** This lane read the committed band row table and summary cells, the leaderboard truth through its loaders, the dataset-comparison loaders (Hofmann, Totis, CMU, KU Leuven, Lane, NIST, Simonds) and the demo overlay; the agent that ran it is not for blind depth work. None of leis2021, hyer2020, aboulkhair2016, ruckh2025, gong2014, ullah or wimmer2020 was opened. `.orchestra/external-data/bitharas2022` was not touched.
