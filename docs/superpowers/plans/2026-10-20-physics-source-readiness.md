# Physics Source Readiness Implementation Plan

> For agentic workers: execute this bounded prerequisite inline; no parallel writers.

**Goal:** Make existing thermal-source verification reproducible on the installed
Poppler and classify existing physics inputs without acquiring new data.

**Architecture:** Preserve the existing independent research checker. Replace its
Xpdf-only extraction option with Poppler layout extraction and a strictly bounded
raw-text parser for superscript vaporization exponents. Keep all hashes, values,
tolerances and numerical checks unchanged.

**Tech Stack:** existing CPython 3.12, stdlib unittest, installed Poppler.

**Spec:** ../../research/WORKFLOW_existing_data_physics_2026-10-20.md;
../../research/SPEC_engine_estimates_2026-10-17.md, G1 and Amendment 1.

## Global constraints

- Existing local sources only; no downloads or dependency installation.
- No served physics, golden, fingerprint or evidence ceiling changes.
- Preserve source hashes and all scientific acceptance comparisons.
- Only this work's changes are staged; local commit, no push.

## Review focus

- Missing source bytes fail before extraction.
- Changed source bytes fail before extraction.
- Superscript exponents must not disappear or drift into another row.
- A missing/extra vaporization column must fail, not truncate.
- Missing executable or extraction failure must not become a skipped pass.

## Task 1: Portable source extraction

Files: docs/research/scripts/engine_est_thermal_check.py;
docs/research/scripts/test_engine_est_thermal_check.py.

- [x] Add regressions for Poppler command selection, source guards and bounded
  three-column vaporization parsing; observe the relevant failures.
- [x] Use `-layout` by default, strip row indentation, and parse scientific
  notation only inside the raw vaporization-to-absorptivity section.
- [x] Run stdlib tests and the actual four-PDF `--check` with locked Python.
- [x] Re-run the existing CALPHAD construction check with pycalphad.

## Task 2: Source receipt and continuation

Files: docs/research/RESULTS_existing_data_physics_2026-10-20.md; STATUS.md.

- [x] Record paths/hashes, commands, outcomes and limits; distinguish source
  readiness, numerical research checks, served implementation and validation.
- [x] Classify thermal, IN625, Ti CALPHAD, microstructure and mechanical readiness.
- [x] Verify diff and links; commit only the listed task files and workflow (`ce0c4a6e`).
- [x] Name W1's next concrete design task; do not claim PDE implementation.
