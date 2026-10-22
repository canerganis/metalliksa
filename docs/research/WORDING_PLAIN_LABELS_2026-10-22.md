Applied 2026-10-22 (maintainer approved all rows). Skipped rows: none. Notes: the defaults notice says "1 input uses an unsourced default" for a count of one; the "N more notes" row was already the shipped wording; the sidebar tooltip and hidden description now use MODULE_PURPOSE, and the registry description stays in the module header disclosure; tests/fixtures/modules-nav-golden.json was updated to the new names and the scorecard description.

# Plain-English label proposals (applied)

Status: approved and applied (see the first line). The evidence labels themselves (Measured, Validated simulation, Calibrated simulation, Literature estimate, Screening only, Uncalibrated estimate, Unresolved, "Not experimentally validated", maturity badges, refusal and warning sentences) are governed by RULES.md and stay as they are. The proposals below are only for the jargon around them.

How to read the table: "Where" is the place a user sees the string. "Today" is the current text. "Proposed" is the replacement. "Why" is the plain reason.

| Where | Today | Proposed | Why |
| --- | --- | --- | --- |
| Module header badge (now behind "About this evidence level") | `Max claim: Screening only · Oracle pending` | `Strongest claim allowed: Screening only. Reference check: not yet available` | "Max claim" and "oracle" mean nothing to a new user. |
| Same, oracle present | `Max claim: Screening only · Oracle present` | `Strongest claim allowed: Screening only. Reference check: available` | Same. |
| Disclosure summary | `About this evidence level` | `What this result can claim` | Says what the reader gets. |
| Disclosure body, first sentence | `Maximum claim: the strongest evidence class this module may report under its contract.` | `The strongest kind of evidence this module is allowed to report.` | Drops "contract". |
| Disclosure body | `It is not the status of a result and not a validation claim.` | `This is a limit, not a grade for any single result, and not a validation.` | Same meaning, shorter words. |
| Disclosure body | `Oracle pending, so the maximum claim stays capped.` | `No independent reference check exists yet, so the claim level stays capped.` | "Oracle" is test-suite jargon. |
| Disclosure body | `Oracle present. <scope>` | `An independent reference check exists. <scope>` | Same. |
| Disclosure body (CI gap note) | `Oracle not run in CI (requires Warp/GPU stack).` | `The reference check is not run automatically here (it needs the Warp GPU stack).` | "CI" is developer jargon. |
| Tooltip on maturity badge | `Module maturity; this is not a validation claim for any result.` | `How finished this module is. It says nothing about whether a result is validated.` | Plain contrast between maturity and validation. |
| Shared-material panel summary | `Context & trust` | `Material and settings in use` | "Trust" over-promises; the panel lists the inputs. |
| Shared-material panel | `Module scope: Production / Research / Preview / Unresolved. Result evidence: Measured / Validated simulation / ...` | `Module status: Production, Research, Preview or Unresolved. Result evidence: Measured, Validated simulation, ...` | Replaces "Module scope" with "Module status"; the evidence names are unchanged. |
| Shared-material panel | `Conservation, convergence and experimental validation are separate checks.` | `Energy balance, mesh convergence and comparison with experiments are three separate checks.` | Names what each check is. |
| Content header kicker | `<Workspace> / Active surface` | `<Workspace>` | "Active surface" is filler. |
| Defaults notice (compact line, new) | `Unsourced defaults in use (N)` | `N inputs use unsourced defaults` | Counts in plain order. |
| Defaults notice (detail line) | `Unsourced defaults or class heuristics in use: ...` | `Inputs filled in without a source (default values or rules of thumb for this alloy class): ...` | "Class heuristics" needs a gloss. |
| Result warnings fold (new) | `N more notes` | `N more notes` | Already plain; listed so the wording is approved once. |
| Out-of-domain warning prefix | `Out of domain:` | `Outside the tested range of the model:` | "Domain" is mathematical jargon. |
| Surrogate note | `Conduction-field surrogate: the temperature field does not include the keyhole cavity.` | `Simplified temperature field: it does not include the keyhole cavity.` | "Conduction-field surrogate" is jargon. |
| Sidebar tooltip and screen-reader description | module registry descriptions (for example `Gaussian-process search over power, speed, hatch and layer ...`) | the plain purpose sentences now shown in the module header (`MODULE_PURPOSE` in `src/data/workspaces.ts`) | One short sentence per module in tooltips too. |
| Module name | `Melt Pool vs Measurements` | `Melt Pool vs Published Measurements` | Separates it from the next row. |
| Module name | `Dataset Comparison (LPBF)` | `Model vs Published Datasets (LPBF)` | It compares models, not data to data. |
| Module name | `Calibration Scorecard (LPBF)` | `Model Error Scorecard (LPBF)` | "Calibration" suggests the tool calibrates the machine. |
| Module name | `Solidification Map (G/R)` | `Solidification Map (cooling and grain structure)` | G/R is thermal gradient over growth rate. |
| Module name | `Keyhole Ray Tracing` | `Keyhole Laser Absorption` | Says the output, not the method. |
| Module name | `Measured Findings` | `Measured Findings (user-labelled)` | The label is user-declared, not verified. |
| Calibration module text | `nuisance absorptivity fitted outside the frozen code` | `laser absorptivity fitted separately from the solver` | "Nuisance parameter" is statistics jargon. |
| Calibration module text | `Held-out errors ... leave-one-source-out` | `Errors on data the model was not fitted to (each source left out in turn)` | Plain description of the test. |
| Header chip | `Local control plane` | `Runs on this computer` | Says what it means to the user. |
| Engine status button | `Python daemon ready` / `Python daemon unavailable` | `Calculation engine ready` / `Calculation engine unavailable` | "Daemon" is developer jargon. |
| CALPHAD banner | `UNIVERSAL SPECIMEN` | `SHARED MATERIAL` | Matches the term used elsewhere ("shared material"). |
| CALPHAD toggle | `Live Sync: ON` / `Live Sync: PAUSED` | `Follow shared material: ON` / `Follow shared material: PAUSED` | Says what is being synced. |
| LPBF workspace header | `One specimen, one process vector, traceable jobs and evidence.` | `One material, one set of laser settings, with every run and source recorded.` | "Process vector" is internal. |
| LPBF workspace badge | `Research · experimental validation unresolved` | unchanged | Evidence label wording is protected. |
| Sidebar group names (new) | `Simulate`, `Compare with data`, `Materials and phases`, `Evidence and export` | unchanged | Already plain. |

Not proposed for change: "Process Parameter Search", "Materials Database", "Research Hub", "Export Review Package", "Phase Diagrams & CALPHAD" (the last two are standard terms for this audience).
