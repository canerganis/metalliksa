# Existing-data physics workflow

Status: active; initiated 2026-10-20 at `6b73f745`.

## User contract

Use existing local data, archived sources and models only. No new source acquisition,
measurements, dependency installation, paid calls or push. Begin with physics and
solver gaps. Keep existing user changes intact. Numerical verification does not
establish experimental validity. This is a bounded work package under ROADMAP.md,
not a replacement release objective.

## Execution order and gates

1. **W0: source readiness and reproducibility (first package complete).** Locate the existing source
   bytes; verify hashes; run thermal and CALPHAD research checks on the current
   checkout. Fix extraction portability without changing physical constants,
   tolerances, source hashes or admission rules. Record usable and blocked inputs.
2. **W1: reduced evaporative thermal model (Ti64 CPU/CLI implemented).** Use the existing G1.2/G1.3 contract and
   Amendment 1 in SPEC_engine_estimates_2026-10-17.md. Start with the alloy whose
   existing input chain passes W0. Separate model identity, opt-in dispatch,
   evaporative energy ledger, timestep rejection and onset admission are required.
   Preserve the original boiling stop. A fixed surface cannot provide keyhole
   geometry, ablation or porosity. Before implementation specify the discrete
   operator, independent reference cases and refinement acceptance thresholds.
3. **W2: material admission.** Build an explicitly source-model IN625 property path
   only from existing verified functions, keeping Gan and Sabau endpoint identities
   distinct. Ti full-chemistry CALPHAD remains blocked if the existing TDBs cannot
   support its scientific model; deleting carbon or silently dropping B2 is not a fix.
4. **W3: thermal-to-microstructure coupling.** Use collocated, same-time front
   derivatives and complete input provenance. Preserve no-value outcomes for
   unsupported SDAS/phase quantities. Do not duplicate existing SOL-C estimates.
5. **W4: mechanics and consumers.** Reuse the implemented constrained-bar and
   cantilever scenarios with explicit input coverage. Do not promote these to
   arbitrary-part distortion or recoater predictions.
6. **W5: existing-data comparison.** Compare frozen before/after cases. Mark all
   previously inspected/tuned data as such; no fresh holdout or experimental pass
   can be created by reusing it. Re-recording goldens is not validation.

## Current work boundary

W0 source readiness is complete. W1's bounded Ti64 fixed-surface CPU/CLI solver
is implemented and numerically checked; whole-branch review is pending. It has
no UI/HTTP dispatch yet and no experimental validity claim. W2-W5 remain pending.
No recurring job or background autonomous task is created.

## First implementation plan

See ../superpowers/plans/2026-10-20-physics-source-readiness.md.

First receipt: [RESULTS_existing_data_physics_2026-10-20.md](RESULTS_existing_data_physics_2026-10-20.md).
W1: [contract](SPEC_ti64_evaporative_cpu_2026-10-20.md),
[plan](../superpowers/plans/2026-10-20-ti64-evaporative-cpu.md),
[numerical receipt and CLI usage](RESULTS_ti64_evaporative_cpu_2026-10-20.md).
Next: explicit opt-in consumer integration preserving the model's refusals;
then W2 material admission. No automatic promotion of estimates is permitted.
