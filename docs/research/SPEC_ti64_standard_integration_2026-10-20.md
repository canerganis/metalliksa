# Ti64 standard-mode integration and usable first run

Status: contract, 2026-10-20, lead (Opus). Base `a09fedee` on `release/0.2.0-prep`.

## Problem

A usability audit on 2026-10-20 found that the Standard (transient) mode stops at
`THERMAL_BOILING_LIMIT` for every typical LPBF input tried: IN718 200 W / 800 mm/s,
Ti-6Al-4V 60 and 150 W / 1000 mm/s, AlSi10Mg 300 W / 1300 mm/s, 316L 200 W / 800 mm/s
and the NIST IN718 tour case 285 W / 960 mm/s. Screening does not report a melt-pool
extent status, so the guided tour's comparison step is never available. A user
therefore gets no melt-pool depth from the main workflow.

Existing, already reviewed pieces:

1. `python/lpbf_ti64_evaporative_solver.py` (`ti64-fixed-surface-evaporation-v1`):
   fixed-surface conduction with Ti vapour energy loss, bare plate only, CPU/CLI only.
   It completes past the boiling temperature, but after the recoil onset latch it
   returns depth, length and volume as null with a refusal reason; width carries a
   conditional warning.
2. `python/lpbf_research_arm.py` (P8 research arm, served inside Build Job
   `researchModels`): keyhole cavity depth and the melt-depth link `Dlinked`, labelled
   research / not experimentally validated.

## Contract

### C1. Opt-in Ti64 evaporative run (no change to existing defaults)

1. The Thermal Simulation stage offers an explicit opt-in model choice
   "Ti-6Al-4V evaporative surface (research)" only when the shared material is
   Ti-6Al-4V and the surface mode is bare plate. Otherwise the choice is shown
   disabled with the reason (wrong alloy, or powder layer not supported).
2. Selecting it submits a job that runs `lpbf_ti64_evaporative_solver.run` through the
   existing worker/job path (same queue, cancel, timeout and refusal handling). It is a
   separate job type; the existing Standard, Screening and GPU paths, their cache keys,
   pins and goldens are unchanged.
3. The result view shows the solver's own labels verbatim: tier, temperature label,
   width label and width warning, refusal reason, energy ledger
   (input, evaporative, radiative/convective, stored, relative residual), accepted time
   and steps, `experimentalValidation=false`. Null depth/length/volume stay null and the
   refusal reason is shown next to them. No value is clipped, filled or renamed.
4. Default request values for the UI must keep a typical run under 120 s on the
   reference CPU. Measure first (see acceptance A2); if the solver's current settings
   cannot meet this at a 600 um track, use a shorter declared track and state it in
   the result, do not change solver physics or numerical tolerances.

### C2. Research depth beside a refused depth

When the evaporative run refuses depth because the recoil onset latched, the result
view adds a separate row "Keyhole-mode research depth (P8)" computed by the existing
P8 research arm for the same alloy, power, speed, beam diameter and preheat. Rules:

1. It is a separate field with its own model id, labels, band and consistency note as
   the P8 arm returns them. It never fills or replaces the evaporative solver's depth.
2. If P8 returns unavailable, show its reason code text; do not fall back to anything.
3. The row states in plain words that the two models differ (fixed surface vs. cavity
   balance) and that neither is validated.

### C3. Guided tour reaches a result

1. The tour's run step must preselect a mode that actually returns comparable output
   for its case, and must navigate the user to the stage that holds the mode control.
   Its popover must not cover the control it asks the user to press.
2. If the case still cannot produce a comparable melt pool, the compare step shows the
   Screening width/depth beside the measurement, labelled "Screening only, comparison
   not validation", plus the P8 research depth if available, instead of a dead end.
   It never claims a closed liquidus isotherm for Screening.

### C4. Run buttons

One primary "Run simulation" button per stage. GPU/CUDA pilot buttons move into an
"Advanced" disclosure and are hidden when no CUDA device is reported.

## Acceptance

A1. Existing suites unchanged: `npm run lint`, `npm run test:unit`, the W1 combined
    Python command in `RESULTS_ti64_evaporative_cpu_2026-10-20.md`, and
    `python tools/lpbf_parity_check.py --check --slow` 25 PASS with no re-recording.
A2. Measured wall time of the UI default Ti64 evaporative request, reported.
A3. New tests: job dispatch for the new type; refusal and P8 row rendering with real
    Python fixtures; disabled-reason rendering; tour preselection and compare fallback.
A4. Browser check: Ti64 bare plate 150 W / 1000 mm/s completes in the app and shows the
    labels and, if onset latched, the P8 row.

## Forbidden

No push. No Ceiling-Review or approval trailers. No edits to pins, goldens,
`.claude/`, frozen solver physics or numerical tolerances. No relabelling a research or
screening value as validated or measured. Spent datasets stay descriptive.
