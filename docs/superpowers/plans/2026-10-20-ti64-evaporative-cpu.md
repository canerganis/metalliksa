# Ti64 Evaporative CPU Implementation Plan

> For agentic workers: use subagent-driven-development, one implementer at a time,
> task review after each task, then independent whole-branch review.

**Goal:** Add and test an actual opt-in Ti64 evaporative spatial thermal solver.
**Architecture:** Additive source-profile/operator module plus distinct CPU solver
and JSON CLI, reusing existing spatial operators; default model/pin remains unchanged.
**Tech stack:** locked CPython 3.12, existing NumPy, stdlib unittest. No installation.
**Spec:** ../../research/SPEC_ti64_evaporative_cpu_2026-10-20.md.

## Global constraints

Existing local sources only; preserve user changes. No default source edits,
golden/pin/band regeneration, new data, UI or HTTP route, push, or scientific promotion.
Read G1/A1.1 and the bounded spec; user has authorized implementation and this workflow.

## Review focus

1. Transition assumptions cannot become measured material inputs.
2. Above-table enthalpy inversion cannot silently clip.
3. Rejected steps cannot change ledgers or latch geometry.
4. Full-run geometry cannot reappear after cooling.
5. No duplicated laser power or diagnostic mass confused with ablation.

### Task 1: Vapor profile and boundary law

Files: create python/lpbf_ti64_evaporation.py and python/test_lpbf_ti64_evaporation.py.
Interfaces: validate_config(raw, liquidus_K) -> immutable configuration;
surface_state(temperature_K, config) -> arrays for mass_flux_kg_m2_s,
heat_flux_W_m2, recoil_pressure_Pa, heat_flux_derivative_W_m2K;
update_onset(previous, state, config, beam_radius_m, time_s) -> new latched gate dict.
Source identity exported from the same module. Input arrays must remain unchanged.

- [x] Write failing law/unit/bridge/invalid-input/onset tests.
- [x] Implement the source constants, explicit transition and latch per spec.
- [x] Run focused tests with locked Python; record RED/GREEN evidence and commit.
- [x] Independent task review and fixes before Task 2.

### Task 2: Spatial solver and integration tests

Files: create python/lpbf_ti64_evaporative_solver.py,
python/test_lpbf_ti64_evaporative_solver.py; optional small new numerical helper
only if needed for focused independently testable stepping (report ownership first).
Consumes Task1 interfaces. Produces run(raw, report=lambda *args:None) -> distinct
JSON result plus stdin/stdout CLI. No source-mutation injection or monkeypatch.

- [x] Write failing contract/energy/cooling/refinement/geometry/CLI tests.
- [x] Implement strict bounded request validation, field solve and accepted-step
  ledgers; source dependency identity; labels/refusals per spec.
- [x] Use the same discrete step in manufactured cooling and actual moving-source
  tests. Verify independent numeric acceptance, not only helper algebra.
- [x] Run focused suite and real CLI, commit, then independent task review/fixes.

### Task 3: Parent verification and delivery

Files: docs/research/RESULTS_ti64_evaporative_cpu_2026-10-20.md, PROOF.md, STATUS.md,
workflow and this plan. Parent owns these, workers do not edit them.

- [x] Run combined new tests, relevant existing operator/default tests and frozen
  parity on locked interpreter; record actual counts and limitations.
- [ ] Run independent whole-branch review; fix important findings and re-review.
- [x] Document usage, declared assumptions, evidence and pending UI integration.
- [ ] Verify/stage only own files, local commits, no push.
