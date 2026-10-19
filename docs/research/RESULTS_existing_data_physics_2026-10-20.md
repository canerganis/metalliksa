# Existing-data physics readiness: first package

Date: 2026-10-20. Baseline: `6b73f745`. Branch: `codex/existing-data-physics-workflow`.
Scope: W0 of [the workflow](WORKFLOW_existing_data_physics_2026-10-20.md).
No external acquisition, package installation, new measurements or solver run.
This is a targeted first inventory, not a claim that every local source was audited.

## Local source recovery

The application `papers/` initially contained only its tracked index. The four
thermal checker prerequisites already existed in `../Metalliksa-1-wt-estimates/papers/`.
Their hashes were verified before copying them into this checkout's ignored
`papers/`. Existing destination files would not be overwritten on a hash mismatch.
These PDFs are not committed; another checkout needs the same local prerequisites.

| Local PDF | SHA256 |
|---|---|
| engine_est_gan2021_SI.pdf | 22a8d2dc870bbd83f6bd3330899437911733f9335d52758d95a328bd6993d6e5 |
| engine_est_fabbro2020.pdf | 9e7c396b9e4a32f56aad26571a062e50434a889c86a65815551d69e5306ddf1e |
| engine_est_mondal2023.pdf | ba9382cea6aec334dafc3f6a9c8350a9b5cca693d980fbe237b2bb704e98d1ce |
| engine_est_gan2019_in625.pdf | 91dfb844d59ea50f44ade37dc8c44caecfb343b6ccc07fb8d665712b27c5604d |

Source locators and adoption limits remain in [the existing source receipt](engine_est_thermal_flow.md).
Only the named property/method pages were extracted. No measured-row comparison
or new source authentication claim beyond these hash/page checks is made.

## Reproducibility repair

Installed Poppler 24.04.0 rejects the checker's Xpdf-specific `-table` option with
exit 99. Replace it with `-layout`, strip table-row indentation and read the
vaporization row in `-raw` mode, where superscripts stay associated with their
mantissas. Require three columns inside named row boundaries. Source hashes,
constants, numerical tolerances and scientific comparisons are unchanged.

The initial seven-test regression suite failed in the portability/parser cases;
after the fix all seven tests passed. Missing/changed bytes, absent executable,
extraction failure and malformed column counts remain failures, not skips.

## Fresh verification

Interpreter: `.runtime/lpbf-win-py312/Scripts/python.exe`, CPython 3.12.10.
Run from the application root. For CALPHAD set OMP_NUM_THREADS,
OPENBLAS_NUM_THREADS and MKL_NUM_THREADS to 1 in the process environment.

| Command after interpreter | Actual outcome |
|---|---|
| `-I -B docs/research/scripts/test_engine_est_thermal_check.py` | 7 tests PASS |
| `-I -B docs/research/scripts/engine_est_thermal_check.py --check` | 4 PDF/hash replays PASS; CC ODE, Maxwellian quadrature, 90 conical mass states, optical identity and invalid-input checks PASS |
| `-I -B docs/research/scripts/engine_est_calphad_check.py --check --with-pycalphad` | PASS as diagnosis; pycalphad 0.11.2; expected original full-chemistry refusal, 6 disordered-limit and 18 off-order states; scientificRepair=false |
| `-I -B docs/research/scripts/engine_est_mechanical_check.py --check` | 7 tests PASS; synthetic model and recorded equation-transcription checks only |

The thermal checker explicitly labels energy identities as **smoke only**: no
independent energy PDE or installed evaporation implementation is verified here.
The CALPHAD check retains pre-existing C/R type-definition warnings and never
writes its in-memory extension into COST507. Mechanical tests authenticate no
new PDF bytes, measured result or general-part solver.

## Readiness decisions from current local evidence

| Gap | Existing material | Decision and next action |
|---|---|---|
| Evaporative transient | Gan2021 Ti64 thermophysical/vapor inputs, Fabbro equations, existing G1.2/G1.3 + A1.1 contract and independent scalar checks | **Conditional first implementation candidate: Ti64.** Specify a new energy-loss PDE with explicit vapor/recoil conventions, pressure, surface tension and onset assumptions. Source transfers remain Tier 2. Existing cap and original boiling stop are not the new model. |
| IN625 | Verified Gan2019 property functions; Sabau adjudication; existing `in625_transient_material_specification()` and bounded snapshot | **Conditional separate model path.** It is inaccurate to say no table code exists. Default admission is disabled because complete source support is not established. Do not switch on the existing Mills/Kim-labelled table or overwrite Sabau endpoints merely because Gan functions exist. |
| Ti full-chemistry CALPHAD | COST507 bytes hash `5b321bc8cf0eec17c1f204f72e82d048d864756c62ede84fb768b277def823ba`; existing mc_ti element declarations | **Blocked scientific model.** COST507 A2/B2 carbon sublattices conflict. mc_ti lacks C/Fe/O declarations required by this full chemistry. In-memory construction success is not a thermodynamic assessment. Other untracked candidate files are neither altered nor admitted by this audit. |
| Microstructure | Current SOL-C and `solidification_front.py`, existing source/admission contract | **Existing conditional estimates, not a missing blank implementation.** Next assess dependency-specific inputs; no default-front release or SDAS coefficient adoption was performed here. |
| Mechanics | Existing bar/released-beam source checks and implemented scenario contract | **Model scenarios verified at research-check level.** General-part thermomechanics/recoater evaluation remains unsupported by these checks. No UI integration claim. |
| Calibration | Existing scorecard and previously inspected datasets | **Comparison only until explicit existing-data protocol.** Reused sources cannot become a new blind holdout; no fitting or bands regeneration occurred. |

## Next concrete work: W1

Write the discrete energy-loss operator contract for a separately named Ti64
fixed-surface model, using the existing G1/A1.1 specification as authority:

1. Declare volumetric enthalpy, exposed-face area, source/loss terms and accepted
   timestep accounting. Keep diagnostic mass flux separate from actual recession.
2. Specify independent zero-flux recovery, manufactured heat-loss solution,
   energy closure, nonlinear step-rejection and mesh/time-refinement tests before
   changing the served solver. Tolerances must not be selected after seeing outputs.
3. Implement the A1.1 onset latch: at equality or above the declared recoil/capillary
   boundary, refuse whole-run depth/length/volume; never inherit these as valid front
   parents. Missing gate inputs also refuse geometry. Retain scoped diagnostics.
4. Identify pinned dependencies and required golden/fingerprint review before any
   served integration. W0 did not modify or regenerate any of them.

W1-W5 remain pending. No background job is running. Full application/Python CI,
browser checks, thermal PDE acceptance, equilibrium validation and experimental
validation were not run for this research-tool repair.
