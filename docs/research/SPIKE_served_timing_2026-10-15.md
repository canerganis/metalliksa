# Served timing spike, 2026-10-15

Phase 0 timing task of the research hub spec (`docs/research/SPEC_research_hub_data_2026-10-14.md`, section 12, phase 0): time 48 synthetic conditions with 5 served calls each, with `include_process_map` True and False, and report p50 and p95.

## Result

On this workstation one served call takes a p95 of 77.5 ms with `include_process_map` False and 123.0 ms with True. A full pass of 48 conditions x 5 calls takes 14.2 s and 23.7 s in total. 480 calls ran with no failures.

| include_process_map | calls | p50 | p95 | mean | first call in a fresh child (cold) |
|---|---|---|---|---|---|
| False | 240 | 56.0 ms | 77.5 ms | 59.3 ms | 58.6 ms |
| True | 240 | 95.2 ms | 123.0 ms | 98.6 ms | 88.7 ms |

By alloy (120 calls each):

| alloy | False p50 | False p95 | True p50 | True p95 |
|---|---|---|---|---|
| Ti-6Al-4V | 59.7 ms | 81.9 ms | 97.9 ms | 124.5 ms |
| AlSi10Mg | 54.3 ms | 72.1 ms | 93.1 ms | 120.7 ms |

One call per condition (48 calls) takes 2.9 s with False and 4.7 s with True. The five repeats show no drift (per-repeat medians 55 to 58 ms with False, 92 to 97 ms with True). depth_um is identical for both settings in all 240 paired calls.

## Conditions

Synthetic inputs only: 2 alloys (Ti-6Al-4V and AlSi10Mg) x 4 powers (100, 200, 300, 400 W) x 6 speeds (0.4, 0.6, 0.8, 1.0, 1.2, 1.5 m/s), 48 conditions. Beam 80 um (1/e2), layer 40 um, hatch 110 um, preheat 80 C, wavelength IR_1064nm, process seed 42. Each condition gets 5 calls back to back.

## Method

1. Code: `python/` at commit 68165d21 (branch `feat/hub-phase0-chores`, clean tree at the start of the run).
2. Interpreter: `C:/Users/can02/Projects/metalliksaa/Metalliksa-1/.runtime/lpbf-win-py312/Scripts/python.exe` (Python 3.12.10), started with `-I -B`.
3. Served call: the steps of spec section 3.1 `served_arm`, in the order the spec lists them: `resolve_alloy_id`, `ALLOY_MATERIALS`, `build_material_property_snapshot`, `canonical_material_source`, `build_build_job_identity`, then `calculate_meltpool_physics` with the flag under test and `prop_overrides` set to the snapshot's thermal block.
4. Each setting ran in its own fresh Python child process, so each includes a cold start. Imports took 1.9 s (False) and 1.4 s (True) and are not in the call times. Calls are timed with `time.perf_counter`.
5. Percentiles use the nearest-rank method over 240 values; p95 is the 228th sorted value. The median of the same data is 56.1 ms (False) and 95.2 ms (True).
6. Machine: AMD Ryzen 7 7840HS (8 cores, 16 logical processors), 31 GB RAM, Windows 11. This task started no other solver jobs. Other workstation load was not controlled.

## Deviations and limits

1. `python/lpbf_served_arms.py` does not exist yet (phase 1). The harness replicates the section 3.1 steps. Re-run the spike against the real `served_arm` once phase 1 lands.
2. "Worker child path" is approximated by a fresh child process that imports the solver modules directly. The timing does not go through `python/lpbf_worker.py` or its RPC queue, so queue wait and worker overhead are not measured.
3. `solve_lpbf_build_job` (slicer, verdict, cache) and the four sensitivity arms of spec section 7.1 are not timed. A full freeze costs more than the served calls alone.
4. Reference machine not measured. The 60 s freeze target (spec sections 3.2 and 4.3) cannot be checked from this workstation alone.

## Use for the section 4.3 cap decision

At these p95 values on this machine, 60 s holds about 770 served calls with False and about 490 with True, before the sensitivity arms. The cap itself is the maintainer's and Opus's decision.
