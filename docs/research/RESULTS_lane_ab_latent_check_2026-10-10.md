# Results: fixed-resolution conservative latent check on Lane A/B contrasts

Run on 2026-10-10 on branch claude/lane-ab-latent-check, from the declaration in
PREDECLARED_lane_ab_latent_check_2026-10-10.md (SHA256 9d3f67b46cf8003dfde0ed5086f1427dd5eb6524e4f67103eae911f4f719e50f,
committed at 28a33020). Raw output: RESULTS_lane_ab_latent_check_2026-10-10.json (SHA256
4325803efae47c6e3f3530e88aa7f1cbfe36dee977bcb33760373c64ecf5338b, schema lpbf-lane-ab-latent-check-v1).
experimentalValidation=false, depthTransferSolved=false, servedPredictionsChanged=false.
originalN3 stays NOT PASSED and N4 is not evaluated.

## 1. Outcome in one paragraph

Declared verdict: INCONCLUSIVE, reason missing-primary-variants (closure, front_fine, front_domain). Interpretation label:
no-conclusion. Case B could not be evaluated at all. All eight case B units (primary, L = 0 control, robustness, H2) stopped at
the very first trial depth h = 0 of the source-depth closure, because that field touched the far cell layer
(failure far-contour-contact) and the solver rejects an invalid field instead of reporting a residual. Case A ran cleanly for all
eight units, with one root each, no timeout and no fallback. Case A alone shows a latent CBM/AMMT depth ratio of 1.213, against 3.55
observed and 1.174 for the same-pipeline L = 0 control. The declared rule needs both cases, so no pass or "does not change the diagnosis" is awarded.

Neither H1 nor H2 is supported or excluded by this run.

## 2. Execution record

| Item | Value |
| --- | --- |
| Command | python/tools/run_lpbf_lane_ab_latent_check.py --run --output docs/research/RESULTS_lane_ab_latent_check_2026-10-10.json --declaration-sha256 9d3f67b4... |
| Interpreter | C:/Users/can02/AppData/Local/Programs/Python/Python312/python.exe, Python 3.12.10, numpy 2.5.3, scipy 1.18.1, Warp 1.17.0, CUDA 12.9, RTX 4060 Laptop 8 GiB |
| Runs | One. No second run, no retry, no resolution or threshold change |
| Wall time | 853.1 s of the 5400 s budget (about 14 min). Started 23:08:48, finished 23:23:04 local |
| Status | completed. No process crash, no Python crash, no unit crash (crashedUnits empty), stderr empty, exit code 0 |
| Timeouts and fallback | None. No unit used the 17/33 fallback. Every successful closure used scan levels 17/33/65 |
| Hashes | sha256_before equals sha256_after for every input and module (all_source_hashes_unchanged true). Git HEAD 28a33020, tracked, not dirty |
| Not run | none |

The eight case B failures are recorded failures of a declared unit, not crashes. They ended each unit at once (about 1 s each), so the
run was far under budget. By section 4.6 of the declaration no unit is rerun.

### Per-unit timings and outcomes

| Unit | Closure | Closure wall (s) | Forwards | Controls |
| --- | --- | --- | --- | --- |
| primary:CBM-A:D100:b0,0.5 | single root h 76.47 um | 99.9 | 116 | front_fine 15.2 s, front_domain 2.9 s, both valid and converged |
| primary:AMMT-A:D170:b0,0.5 | single root h 64.39 um | 93.0 | 115 | front_fine 14.6 s, front_domain 2.9 s |
| primary:CBM-B:D100:b0,0.5 | failed, far-contour-contact at h = 0 | 1.0 | 1 | none (no root) |
| primary:AMMT-B:D170:b0,0.5 | failed, far-contour-contact at h = 0 | 1.0 | 1 | none |
| l0-control:CBM-A:D100:b0,0.5 | single root h 85.91 um | 98.5 | 115 | none planned |
| l0-control:AMMT-A:D170:b0,0.5 | single root h 74.48 um | 99.5 | 110 | none planned |
| l0-control:CBM-B:D100:b0,0.5 | failed, same | 0.9 | 1 | none |
| l0-control:AMMT-B:D170:b0,0.5 | failed, same | 0.9 | 1 | none |
| shape-robustness:CBM-A:D100:b1,0 | single root h 77.00 um | 99.5 | 120 | none planned |
| shape-robustness:AMMT-A:D170:b1,0 | single root h 64.98 um | 92.9 | 121 | none planned |
| shape-robustness:CBM-B:D100:b1,0 | failed, same | 1.0 | 1 | none |
| shape-robustness:AMMT-B:D170:b1,0 | failed, same | 1.0 | 1 | none |
| h2-beam:CBM-A:D85:b0,0.5 | single root h 77.24 um | 98.9 | 122 | front_fine 15.0 s, valid |
| h2-beam:CBM-B:D85:b0,0.5 | failed, same | 1.0 | 1 | none |
| h2-beam:CBM-A:D70:b0,0.5 | single root h 80.65 um | 96.3 | 115 | front_fine 14.5 s, valid |
| h2-beam:CBM-B:D70:b0,0.5 | failed, same | 1.1 | 1 | none |

The eight successful closures took 93 to 100 s each, inside the 120 s cap but close to it, as the declaration anticipated. No
residual-positive-at-search-cap outcome occurred (searchCapUnits empty); every case A residual changes sign inside [0, 120 um].

### The case B failure

The recorded first evaluation of primary:CBM-B (h = 0, so source depth d = 20 um, kappa 1) ended after 4300 steps with
valid false, failure far-contour-contact, liquidus-isotherm width 251 um and depth 123 um. The same h = 0 trial in case A is valid
(CBM-A depth 72 um, width 161 um). The closure code (python/tools/lpbf_projected_enthalpy_feedback_v2.py:283) raises a ValueError for any invalid
field, so the whole search ends before it samples a second depth. The JSON does not record which boundary was touched. Inference, not a recorded fact: the
0.8 m/s cases have the longer liquid tail, and the x extent of front_coarse stops at -1.5 mm, so the tail probably reaches the outflow end of the box. The front_domain grid
(x to -2.1 mm) was not run for case B because it is a same-source control and needs a closure root. The failure therefore says the declared front_coarse
box cannot evaluate the h = 0 trial of case B. It does not say the case B physical answer is anything in particular.

## 3. Readouts versus observed (case A only; case B unavailable)

Observed Table 3 means as in the declaration: depth CBM-A 151.53, AMMT-A 42.63, CBM-B 91.25, AMMT-B 35.98 um; width CBM-A 171.0, AMMT-A 148.95, CBM-B 133.02, AMMT-B 125.6 um.

| Quantity, case A | Observed | Zero-latent N3 | L = 0 control (same pipeline) | Latent, closure | Latent, front_fine | Latent, front_domain |
| --- | --- | --- | --- | --- | --- | --- |
| CBM depth (um) | 151.53 | 87.22 | 87.54 | 78.11 | 77.93 | 78.11 |
| AMMT depth (um) | 42.63 | 74.40 | 74.59 | 64.42 | 64.33 | 64.42 |
| Depth ratio CBM/AMMT | 3.555 | 1.172 | 1.174 | 1.213 | 1.211 | 1.213 |
| Depth difference (um) | 108.9 | 12.8 | 12.95 | 13.69 | 13.60 | 13.69 |
| CBM width (um) | 171.0 | n/a here | 161.29 | 145.74 | 147.60 | 145.74 |
| AMMT width (um) | 148.95 | n/a here | 173.46 | 162.84 | 163.20 | 162.84 |
| Width ratio CBM/AMMT | 1.148 | 0.932 | 0.930 | 0.895 | 0.904 | 0.895 |

| Quantity, case B | Observed | Zero-latent N3 | L = 0 control | Latent (all variants) |
| --- | --- | --- | --- | --- |
| Depth ratio CBM/AMMT | 2.537 | 1.207 | unavailable | unavailable |
| Depth difference (um) | 55.3 | 11.7 | unavailable | unavailable |

Secondary, case A closure roots: CBM-A h = source depth = Dref = 76.47 um, kappa 1.237, peak 9225 C; AMMT-A 64.39 um, kappa 1.0, peak 5202 C; closure residual 0 within the 0.05 um tolerance.

Reading:

1. Latent heat lowers both case A depths (CBM 0.892 and AMMT 0.864 of the L = 0 depth) and raises the ratio by 0.04, from 1.174 to 1.213. The direction of the depth change
matches the prior expectation in section 10.1 of the declaration. The size of the ratio effect is tiny against the observed gap of about 2.4 in ratio.
2. Both latent CBM/AMMT ratios sit far under the explains-contrast threshold 2.5 and under the no-change threshold 1.6. The latent AMMT-A depth (64.4 um) is also well above the 48 um that section 7a
required for explains-contrast to be reachable, so in case A the explains-contrast class was unreachable in this model, as the declaration warned.
3. The predicted CBM depth (78 um) is half the observed 151.5 um, and the predicted AMMT depth (64 um) is 1.5 times the observed 42.6 um. The model errs in opposite directions on the two machines, which is the pattern of the earlier zero-latent screen and is what a missing deep-cavity mechanism on the CBM side would also produce. This is an observation about
this one case, not a test of H1.
4. Solver cross-check (declaration section 4a.2, informational): the L = 0 units reproduce the N3 zero-latent depths within 0.37 percent (CBM-A) and 0.25 percent (AMMT-A), well inside the 10 percent flag. The finite-volume box pipeline and the Dref closure therefore did not
change the A depths; the latent ratio change versus the L = 0 control is attributable to latent heat for case A. Case B has no cross-check.
5. Resolution: classes agree across closure, front_fine and front_domain for A (same side of every threshold). front_domain moves nothing (relative changes of order 1e-8). front_fine moves CBM-A width by 1.3 percent (above the original informational 1 percent check, flagged false for CBM-A) and AMMT-A by 0.3 percent; the ratio moves by 0.001. Informational only.

## 4. Decision per the declared rule

| Step | Rule | Result |
| --- | --- | --- |
| Per variant class (closure, front_fine, front_domain) | explains rA >= 2.5 and rB >= 2.0; does-not-change rA < 1.6 and rB < 1.6; else inconclusive | rB missing in every variant, so inconclusive for each. rA = 1.213, 1.211, 1.213 |
| Single sampled root for all four primary closures | required | Not met. Two of four (the B units) ended in an invalid-field failure |
| Robustness shape (1, 0) class | must match | Case A ratio 1.213 (CBM 79.00, AMMT 65.10 um); case B missing; class unavailable |
| Verdict | | inconclusive, reason missing-primary-variants:closure,front_fine,front_domain |
| L = 0 class | needed only for the explains label | unavailable; latent attribution relation: unavailable |
| Interpretation label | | no-conclusion |

Because rB is missing, the rule cannot yield does-not-change-diagnosis, and the H2 row of the interpretation table cannot be reached. This is stated to prevent a misreading: a case A ratio of 1.21
does not by itself award does-not-change. It does show, as a matter of arithmetic of the declared thresholds, that explains-contrast was not going to be awarded, because that class needs rA >= 2.5 and the case A ratio, in every variant and for the robustness shape, is about half of that.

## 5. H2 beam sensitivity (case A only)

Shape (0, 0.5), AMMT fixed at D170 (latent 64.42 um), D100 reused from the primary units. This arm was declared as a conduction plus latent response and not as an H2 test (declaration section 8).

| CBM D4sigma (um) | CBM depth (um), closure | fine control | Ratio, closure | Ratio, front_fine | Zero-latent expected ratio | Width CBM (um), closure |
| --- | --- | --- | --- | --- | --- | --- |
| 100 | 78.11 | 77.93 | 1.213 | 1.211 | 1.172 | 145.74 |
| 85 | 80.21 | 79.71 | 1.245 | 1.239 | 1.194 | 143.72 |
| 70 | 82.08 | 81.93 | 1.274 | 1.273 | 1.215 | 142.17 |

Case B at all three diameters: unavailable (invalid field at h = 0). Per-diameter classes: D70, D85, D100 all null (case B missing). Declared reading: conduction-model-beam-sensitivity-partial-or-inconclusive.

Beam response in case A: ratio change D100 to D70 is 0.062 latent, against 0.043 for the pre-run zero-latent expectation. The stated expectation ("a few hundredths, all diameters well below 1.6") holds for case A. Shrinking the CBM beam from 100 to 70 um
raises the predicted CBM depth by 4 um, while the observed CBM depth sits 73 um above the model. The model has no mechanism for a smaller beam to deepen the pool the way real irradiance and keyhole onset do, so this table cannot say whether H2 is the cause. It also cannot favour H1. No diameter is selected or scored against depth.

## 6. What this run does and does not show

Shown (case A, this model, nominal ledger, no fitted absorption):

1. The conservative latent enthalpy model with the sampled source-depth closure, run for the first time on IN625 inputs, produces a CBM/AMMT depth ratio of 1.21 and not the observed 3.55. Fusion enthalpy changes the ratio by 0.04 relative to the same-pipeline L = 0 control.
2. The same-pipeline L = 0 control matches the N3 zero-latent depths to 0.4 percent, so the box, mesh and closure changes are not hiding a solver difference in case A.
3. A 30 percent smaller CBM beam changes the case A ratio by 0.06.

Not shown:

1. Anything about case B. The declared decision, the robustness agreement, the H2 reading and the latent attribution are all unavailable.
2. That H1 (missing cavity or keyhole physics) is the cause. Nothing here models or excludes a cavity, and the beam arm cannot separate H1 from H2.
3. That H2 (wrong beam diameter or power) is the cause. The CBM 100 um diameter is still presumed and unmeasured. Nominal versus actual power was not varied (no second value in the ledger).
4. Any validation of the model against experiment, or that the latent backend is qualified (latentBackendQualified=false).

## 7. Limits

1. The case B failure is a coverage hole in the declared design, not a finding about case B. The closure starts at h = 0 (d = 20 um) and cannot recover from one invalid trial field. The declared front_coarse box (x to -1.5 mm) is the probable cause for the 0.8 m/s cases (inference, see section 2). The declaration said resolution is never changed after seeing results, so this run stopped there.
2. Case A results are conditional on constant 21 C properties applied to 1350 C, a literature fusion enthalpy (290 kJ/kg), a linear mushy fraction between 1290 and 1350 C, and no fluid flow, recoil, free cavity, evaporation, multiple reflection or absorptivity change.
3. The depth is a sampled closure root with a 0.05 um tolerance, not a completeness or uniqueness certificate, though all three scan levels agreed for every case A unit.
4. The shape coefficients (0, 0.5) have weak provenance (declaration section 2). The robustness shape (1, 0) agrees for case A within 0.001 in the ratio, so case A is not shape sensitive at this resolution.
5. The A grid adequacy was measured only by the same-source controls (fine and domain). The domain control passes. The fine control moved CBM-A width by 1.3 percent. Grids are not pre-qualified for these inputs.
6. The CBM and AMMT predictions disagree with observation in opposite directions, so a single scale factor on power cannot explain both. This is a qualitative observation and is not used as a fit.
7. No later run, retry, grid change or threshold change was made after seeing results. If a follow-up is wanted, it needs a new declaration that fixes the case B coverage hole before it runs (for example by treating an invalid h = 0 trial as above-threshold, or by a longer x extent for the 0.8 m/s cases), with its own gate.

## 8. Correction, 2026-10-10 (Opus verification)

The cause given for the case B failure in section 2 and the follow-up suggested in section 7 item 7 are wrong. The JSON, the verdict and every number above are unchanged.

1. The physical liquidus tail ends inside the box: x = -0.96 mm for CBM-B and -0.76 mm for AMMT-B (Rosenthal estimate for CBM-B 0.905 mm).
2. The far-contour contact comes only from the single outflow cell layer next to the Dirichlet T0 face, where heat piles up: 3141 C at x = -1.4875 mm against 1180 C in the next layer for CBM-B, 2603 C against 966 C for AMMT-B. The advective flux through that layer is about 3.5 P, while interior layers carry 0.99 to 1.00 P and match Rosenthal within 5 percent.
3. The longer front_domain box (to -2.1 mm) fails the same way (outflow layer 2116 C for CBM-B, 1839 C for AMMT-B), so a longer x extent is not a fix.
4. The recorded case B h = 0 width 251 um and depth 123 um are artifacts of that layer. The interior pool is about 125 um wide and 52 um deep at cell centres.
5. The same pile-up exists in case A (outflow layer rise 1061 K against Rosenthal 622 K) but stays below liquidus; front_domain moved the case A depths by about 1e-8, so case A is unaffected.
6. "converged false" in case B is the contact check overriding a residual-converged field (L1 about 9e-7 at 4300 steps), not a non-converged solve.

Any follow-up declaration must change the outflow treatment or exclude the outflow Dirichlet layer from the contact test. That is a solver or validator change and needs its own gate.
