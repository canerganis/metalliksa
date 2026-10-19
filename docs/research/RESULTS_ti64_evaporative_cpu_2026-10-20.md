# Ti64 evaporative CPU solver — numerical evidence

Scope: existing local sources only, under
[the bounded contract](SPEC_ti64_evaporative_cpu_2026-10-20.md).
Implementation commits: `6046f041` (law), `676fa2c2` (spatial solver),
`e6cb55ae` (review fixes). Task review found rare floating-point mesh top-face
misalignment and missing returned scope warnings; both were fixed with focused
regressions and independently re-reviewed without new findings. Independent
whole-branch review is pending. Numerical checks are not experimental
validation. No new material measurements or fitted parameters are introduced.

## Source and assumptions

The vapor law uses the existing Gan2021 SI Ti species constants: Tv=3560 K,
Lv=9.255e6 J/kg and M=0.048 kg/mol. The existing Ti64 thermal material registry
remains the thermal authority, including its distinct 3560.15 K table endpoint.
The transition interval, return fraction, ambient pressure, maximum temperature
and optional surface tension are explicit scenario inputs. The Hermite bridge
and constant-liquid-property continuation are declared model assumptions.

The fixed-surface model does not remove material or compute keyhole geometry.
Emitted mass is diagnostic only. Once the recoil onset criterion or missing
tension makes geometry unavailable, cooling cannot restore full-run depth,
length or volume eligibility. UI/HTTP integration is outside this package.

## Completed operator evidence

- Commit `6046f041`: vapor profile/operator and tests, two new files only.
- Locked CPython 3.12 runtime, operator unittest suite: 17 PASS, no skips.
- Independent Maxwellian quadrature, analytic bridge monotonicity and derivative,
  strict invalid-input rejection, input immutability and onset/latch tests.
- Task review: spec compliant and quality approved; no findings. Accepted-step
  integration and geometry suppression are checked with the coupled solver.
- RED evidence was a missing-module collection error, followed by a test-only
  continuity normalization correction. A near-zero endpoint derivative had an
  inappropriate absolute tolerance; its independent high-end derivative scale
  replaced that normalization. No production formula or contract tolerance moved.

## Existing-path baseline

Locked runtime: `.runtime/lpbf-win-py312/Scripts/python.exe`.
From `python/`, with BLAS/OpenMP threads set to one:

```powershell
..\.runtime\lpbf-win-py312\Scripts\python.exe -B -m unittest test_lpbf_shared_thermal_conduction_faces test_lpbf_graded_mesh_and_evaporation test_lpbf_implementation_fingerprint_pin
..\.runtime\lpbf-win-py312\Scripts\python.exe -B tools\lpbf_parity_check.py --check --slow
```

Results: 10 relevant existing tests PASS; frozen parity 25 PASS, no failures,
skips or drift. No re-recording, material-registry edits or default pin changes.
Local logs: `.runtime/ti64-evap-baseline-unit.log` and
`.runtime/ti64-evap-baseline-parity.log` (ignored runtime evidence).

## Coupled numerical acceptance

Parent combined command, from `python/` with the same locked interpreter:

```powershell
..\.runtime\lpbf-win-py312\Scripts\python.exe -B -m unittest test_lpbf_ti64_evaporation test_lpbf_ti64_evaporative_solver test_lpbf_shared_thermal_conduction_faces test_lpbf_graded_mesh_and_evaporation test_lpbf_implementation_fingerprint_pin -v
```

40 tests PASS, zero failures/errors/skips, 5.710 s at `e6cb55ae`. This comprises
30 new tests and 10 existing tests. Log: `.runtime/ti64-evap-combined.log`.

| Numerical check | Measured software result | Predeclared acceptance |
|---|---|---|
| Independent Maxwellian velocity integral | Operator tests PASS | Relative mass-flux error <=1e-8 |
| Constant-capacity cooling, 10/20/40 Euler steps | Errors .16907884 / .08423263 / .04204012 K; order 1.00261 | Order >.8; evaporative energy/removal relative difference <1e-10 |
| Spatial insulated cosine decay, nx=8/16/32 | L2 error 3.46539e-4 / 8.26111e-5 / 2.03990e-5 K | Error decreases under refinement |
| Actual moving-source energy closure | Relative residual 5.42101e-16 | <=1e-9 |
| Paired zero-flux scenario | Evaporation and diagnostic mass exactly zero; greater retained energy | Active case loses energy versus zero-flux case |
| Onset then cooling | Final maximum 3332.02 K; geometry refusal persists | Cooling never clears latch |
| Rejected moving-source candidates | Source reintegrated at reduced dt; accepted ledger/fields isolated | No rejected contribution or latch |

The actual run uses 160 W, 800 mm/s, 80 um 1/e2 beam diameter, nominal 40 um
mesh (effective dx=37.7778 um), 100 um track, 20 us cooling and 20 um source
penetration. It admits 692 steps on a 9x9x8 grid. The minimum source capture is
.999999999021; the original capture threshold remains unchanged.

| Quantity | Active scenario | Zero-flux comparison |
|---|---:|---:|
| Transition low/high, K | 3560 / 4000 | 4900 / 5000 |
| Absorbed laser input, J | .006400000000000002 | .0064000000000000055 |
| Evaporative loss, J | .00021742743375250079 | 0 |
| Stored energy above initial state, J | .006181178369281868 | .006398390615999192 |
| Peak temperature, K | 4225.537677026038 | 4462.582699779224 |

Active radiative/convective loss is 1.394192841066e-6 J and base loss is
4.124563310096e-12 J. Diagnostic emitted mass is 2.349296961129e-11 kg.
Onset latches at 70.21456 us; depth, length and volume are null afterwards.
The paired runs have different adaptive steps; the input difference is roundoff.

Test-fixture corrections were recorded explicitly: an initial rejection fixture
did not overpower evaporation, so a bounded manufactured enthalpy interval was
used to force rejection. An initial 260 W reference still evaporated; the common
power was reduced to 160 W and exact-zero reference loss assertions were added.
No physical law, acceptance tolerance or measured data was changed for a pass.

## Usage and independent CLI check

From the application repository in PowerShell:

```powershell
@'
{"material":"Ti-6Al-4V","backend":"reference","surfaceMode":"bare-plate","power_W":160,"speed_mm_s":800,"beamDiameter_um":80,"preheat_C":80,"mesh_um":40,"maxDt_s":0.000001,"trackLength_um":100,"cooling_s":0.00002,"sourcePenetration_um":20,"evaporation":{"transitionLow_K":3560,"transitionHigh_K":4000,"ambientPressure_Pa":101325,"returnFraction":0.2,"maxTemperature_K":5000,"surfaceTension_N_m":1.65}}
'@ | .runtime/lpbf-win-py312/Scripts/python.exe -B python/lpbf_ti64_evaporative_solver.py
```

Parent executed this real stdin/stdout CLI, parsed its finite JSON and checked
positive evaporation, <=1e-9 relative closure, refused depth and false
experimentalValidation; repeated after review fixes and verified returned scope
and width warnings. Exit 0; values match the table. Local output:
`.runtime/ti64-evap-parent-cli.json`. Invalid requests are covered by the CLI test.
Python callers may use `lpbf_ti64_evaporative_solver.run(request)`.

The result has its own schema/model and fingerprint, binding the existing
dependency closure plus both added modules and numerical settings. It includes
source assumptions, normalized inputs, accepted time/steps, separate energy
terms, diagnostic mass and permanently gated isotherm geometry.

## Limits and next step

No experimental validation, full nonlinear process mesh/time convergence,
keyhole/free-surface CFD, alloy depletion, ablation or production readiness is
claimed. Manufactured convergence verifies the discrete kernel only. Full UI,
TypeScript and unrelated Python suites were not rerun; no UI or existing route
changed. The next integration step is an explicit opt-in service/UI consumer
that preserves these assumptions and geometry refusals. W2-W5 remain pending.
