# IN625 per-alloy keyhole-mode threshold: pre-registration (2026-10-11)

File: `docs/research/PREDECLARED_in625_regime_2026-10-11.md`

**PREDECLARED. Screening evaluation, not validation. No threshold has been fitted; held-out units have been scored
only at fixed trial cuts with no fit, as disclosed in section 10.** Lane `in625-regime-threshold`, branch `research/in625-regime-threshold`, base `b22657f5` (local main).
Sources and locators: `docs/research/SOURCES_in625_regime_2026-10-11.md` (cited below as SOURCES). Runner:
`python/tools/lpbf_in625_regime_threshold.py`. Synthetic tests: `python/test_lpbf_in625_regime_threshold.py`.
Ledger: `data/benchmark/in625-regime-ledger-2026-10-11/units.csv`. Nothing frozen changes in this lane; labels stay
`experimentalValidation=false`, `validationStatus=unvalidated`, `productionReady=false`. Nothing runs before the gate
approves this file.

Amendment 1 (2026-10-11, before any run, after the pre-registration gate at `14d0de3a`): section 5 now gives the
identity reason for the one exclusion (B2); section 7 adds the held-out-admissible interval as a reported quantity;
section 10 discloses the baseline's known held-out errors and what that implies for the PASS rule; section 12 limits
what a PASS licenses (B1). The fit rule, the split, the arms and the PASS thresholds are unchanged.

Amendment 2 (2026-10-11, before any run, after gate round 2 at `85e1df60`): the PASS rule allows arm F one held-out
error, and two of the three possible held-out-admissible intervals carry one held-out error each, so the amendment 1
sentence "the onset lies in (L, U]" would be contradicted by held-out data in those cases. Section 12 now makes the
licensed sentence depend on F's held-out errors, the runner writes F's per-unit held-out calls, and section 10 item 3
states which interval is error-free. Section 5 and SOURCES section 3.3 now name the source of each value used for the
row 29 exclusion. The fit rule, the split, the arms, the PASS thresholds and the verdict logic are unchanged.

## 1. Question and scope

The app labels the regime from the normalised enthalpy dH/hs with cuts 15 (transition) and 20 (keyhole mode), both
transferred to IN625 from Ti-6Al-4V and 316L (`python/lpbf_thermal_solver.py:174-185`). The current IN625 note says the
20 cut misses keyhole in the available IN625 data.

Question: is there an IN625 keyhole-mode cut on the app index, fitted on a declared fit split against a declared,
sourced morphology criterion, that classifies held-out IN625 units with measured geometry clearly better than the
current cut 20?

In scope: the keyhole-mode cut for Inconel 625 only. Out of scope: the transition cut 15 (it is a vapour-depression
onset from Cunningham 2019 Ti-6Al-4V x-ray data; no IN625 vapour-depression data exists in the repo, SOURCES section 5),
the porosity screen, every depth, width and length number, every other alloy. The keyhole cut feeds only the regime
label and the process-map regime label; the depth increment and the depth proxy use the separate legacy 15/30 band
edges (`python/lpbf_thermal_solver.py:203-205`, `:971-977`), so no depth number changes under any outcome. This lane
does not edit the solver; a PASS only allows a planned bump on a BUILD lane (section 12).

## 2. Hypothesis

H1: on IN625, the morphology keyhole onset (depth greater than half width) sits at a lower app index than 20, and a cut
fitted on EOS M270 units transfers to AMMT units and to the separately published Lane 2020 units.

H0: no fitted cut beats 20 by the declared margin on the held-out split.

## 3. Index and convention (fixed)

1. Index: the app's own formula, `lpbf_public_datasets.normalized_enthalpy` (identical to
   `lpbf_thermal_solver.py:606-607`): dH/hs = A P / (rho cp_s max(50, T_liq - T0) sqrt(pi alpha_s v r^3)), with
   r = D4sigma / 2, A = flat absorptivity_IR, solid k and cp.
2. Material properties: `SECONDARY_THERMOPHYSICAL_DB["Inconel 625"]` at `b22657f5` (rho 8440, k_s 9.8, cp_s 410,
   T_liq 1350 C, A 0.38; legacy-estimated-secondary). Not changed by this lane.
3. Preheat T0 = 20 C for every unit (bare plates; `ASSUMED_PREHEAT_C`). Weaver's T0 = 27 C is a sensitivity only.
4. Spot: the published D4sigma (Lane Table 1 and Table 3; mds2 Summary column "Estimated D4sigma Spot Diameter").
5. Power: Lane Table 3 power (AMMT 137.9 / 179.2 W); nominal 150 / 195 W is a sensitivity only.
6. Convention bridge (SOURCES section 4): H_app = 0.72429 H_Weaver for the same P, u and D4sigma. This gives the
   reported, non-adoptable arm S: Weaver's 30 is 21.73 app units. The factor is recomputed by the runner
   (`repo_per_weaver_factor`) and pinned in the tests.

## 4. Regime truth (fixed before the run)

1. Primary: a unit is keyhole mode if and only if depth / (width / 2) > 1, strictly. Source: King et al. 2014 Sec. 5.2
   ("melt pools where the depth was greater than the half width"); Weaver et al. 2022 Sec. 4.1 calls it the common
   definition; the app's own keyhole label reads "melt-pool D/W > 0.5". It uses measured geometry only and does not
   depend on the estimated EOS spot sizes.
2. Secondary (P5 and reporting): depth / (D4sigma / 2) > 1, strictly (Weaver 2022 Sec. 4.1).
3. The ratio is formed from the unit's published mean depth and mean width (mds2 Summary row, Lane Table 4 class).
   A ratio exactly 1 is not keyhole.
4. Ambiguity (sensitivity only): a unit is ambiguous when |ratio - 1| <= ratio x sqrt((U_d/d)^2 + (U_w/w)^2), with
   the ledger's expanded uncertainties (mds2 U (k = 2); Lane 2 x U_mean combined with 2 % / 5 % variability).
   Ambiguous units stay in the primary metric.

## 5. Data, units and split (fixed)

Unit: one process condition with published mean width and depth. Ledger: 70 units, sha256
`6957b6f3c9ac809b2a7221f4e07be7c26c410d873e8f01e8b2ca04b5a088424a` (SOURCES section 6).

Split rule (`assign_split`; it reads source, machine and process condition only, never width or depth):

| split | rule | units |
|---|---|---|
| fit | mds2-2923 EOS M270 Summary rows (Weaver's own plates, estimated spots) | 56 |
| held-out | all mds2-2923 AMMT rows (measured spots) and all six Lane 2020 Table 4 classes (CBM and AMMT) | 13 |
| excluded | an mds2 EOS M270 row whose machine family, power, speed and D4sigma (rounded to 0.1) equal a held-out Lane CBM unit | 1 (195 W, 800 mm/s, 100 um) |

Why this split: the held-out units test transfer to a different machine with a measured spot (AMMT) and to a
separately published campaign (Lane 2020 AM-Bench plates).

Why the excluded row is excluded: mds2 EOS Summary row 29 (195 W, 800 mm/s, D4sigma 100 um, n = 10, mean depth
91.258 um, mean width 135.58 um) is very likely the same physical tracks as the held-out Lane CBM B class, not only
the same condition. Evidence, by source: Weaver 2022 Sec. 2.2 says their data set includes ten Lane 2020 EOS tracks;
Weaver Table 4 lists case B with d = 91.28 um (re-read from the logged XML in amendment 2, SOURCES section 3.3),
which matches the mds2 row 29 mean depth 91.258 um and the Lane Table 4 CBM B class depth of 91 um; the mds2 Summary
gives row 29 n = 10 measurements (Weaver Table 4 gives no count); and no mds2 EOS row exists at the other two CBM
conditions (150 W / 400 mm/s, 195 W / 1200 mm/s), so the ten Lane tracks can only sit in row 29. Counter-evidence, recorded: the mds2 Data sheet folders behind that condition
are named Plate 3, 4 and 9 and dated 2018-08-28 to 2018-09-10, with no AM-Bench label, so the identity is inferred,
not stated by the data set. Either way the row is a held-out target: keeping it in the fit split would put CBM B's
measured geometry into the threshold. The exclusion is therefore required, not optional.

Lane CBM is the same machine model as the fit split (Lane 2020 Introduction), so for those three units the test is
cross-campaign, not cross-machine; this is stated, not hidden.

Not used: Ghosh 2018 (spot size not stated), IN718 rows, Lane per-track rows (SOURCES section 6).

## 6. Arms and the fit rule (fixed)

Binary call for every arm: keyhole if index >= cut, otherwise not keyhole (the 15 to 20 transition band counts as not
keyhole).

| arm | cut | role |
|---|---|---|
| F | fitted on the fit split (rule below), rounded to 0.1 | the only adoption candidate |
| B | 20 (current `ENTHALPY_KEYHOLE`) | baseline |
| S | 30 x 0.72429 = 21.73 (Weaver Sec. 4.2 converted) | reported for the convention reconciliation; not adoptable |
| D | 15 (current transition cut) | descriptive only; not adoptable |

Fit rule (`fit_threshold`), applied to fit-split units only (the function raises on any other split):

1. Compute the app index and the primary truth label of every fit unit.
2. Candidate cuts are the midpoints between consecutive distinct sorted fit indices.
3. Choose the candidate with the highest balanced accuracy (mean of keyhole recall and not-keyhole specificity) on the
   fit split. Ties: the widest gap between the two bracketing fit indices; then the lower cut.
4. Adopted value T_F = the chosen cut rounded to 0.1. Every held-out metric of arm F uses T_F.
5. The fit raises (outcome INCONCLUSIVE, section 7) if the fit split lacks a class.

No other choice is free: no grid, no regularisation, no hand tuning, no second fit after the run.

## 7. Metrics and PASS rule (fixed)

Metrics on the held-out split, per arm: confusion counts, keyhole recall, not-keyhole specificity, balanced accuracy
(BA), errors.

| item | rule |
|---|---|
| P4 classes present | held-out has at least 3 keyhole and 3 not-keyhole units, and the fit split at least 5 of each; otherwise the verdict is INCONCLUSIVE and nothing else is judged |
| P1 absolute | BA(F) >= 0.80 |
| P2 gain | BA(F) - BA(B) >= 0.15 |
| P3 errors | errors(F) <= errors(B) - 2 |
| P5 secondary truth | under the secondary truth, BA(F) >= BA(B) |
| P6 robustness | each of the 56 leave-one-fit-unit-out refits (same rule, rounded) gives held-out BA >= 0.75; a degenerate refit fails P6 |

Verdict: PASS if P4 holds and P1, P2, P3, P5, P6 all hold; INCONCLUSIVE if P4 fails; FAIL otherwise. Why it is not
trivially passable: an always-keyhole or never-keyhole call has BA 0.5 (fails P1); a cut that only moves one held-out
unit fails P3; if the current cut 20 already makes at most one held-out error, no candidate can pass P3, which is the
intended outcome "the current cut is not beaten". The tests pin these cases on synthetic confusions.

Held-out-admissible interval (amendment 1, reported with every verdict): the set of cuts c that give the same
held-out confusion as T_F. With "keyhole if index >= c" it is (L, U], where L is the largest held-out index below T_F
and U is the smallest held-out index at or above T_F; any cut outside it moves at least one held-out unit and changes
the confusion. The runner computes it from held-out indices only (`heldout_admissible_interval`, no label read) and
writes it to the results JSON with the two bounding unit ids. The interval, not the BA alone, is the measure of how
tightly the held-out split locates the onset (section 12).

## 8. Sensitivities (reported, never part of the verdict)

1. Unambiguous held-out units only (section 4 item 4), arms F and B.
2. T0 = 27 C (Weaver Table 2): indices recomputed, F refitted on the fit split, arms F and B rescored.
3. Lane AMMT nominal power (150 / 195 W) in the held-out index, arms F and B.
4. Arms S and D on the primary truth; per-unit index, Weaver index, both ratios and ambiguity flags for all 70 units.
5. Whether T_F < 15. If so, the result states that an IN625 rule with this cut would leave no transition band; how the
   product labels that is a BUILD-lane decision, not a claim of this lane.

## 9. Failure modes and threats

1. EOS spot sizes in the fit split are estimates (Weaver Sec. 2.1 caustic model). The index scales as D^-1.5, so a 10 %
   spot error is about 15 % in index; a biased estimate shifts T_F. The held-out AMMT spots are measured, which is
   what exposes such a bias.
2. The truth is a morphology label of the etched cross-section, not a vapour depression and not porosity. A PASS says
   nothing about pores.
3. Width definitions: mds2 width is the widest bounding-box dimension (README); Lane uses a bounding rectangle; the
   Weaver paper text says width at the surface. Units near ratio 1 can flip with the definition.
4. Small held-out set (13 units); the 7 mds2 AMMT units are one power and speed with a spot series, so they are not
   independent draws. P2, P3 and P6 are counted in units for this reason.
5. The cut is tied to the app's IN625 property set (legacy-estimated, solid k and cp, liquidus). A property change
   requires a refit; the threshold is not a material constant.
6. Lane AMMT power question unresolved (sensitivity 3).
7. Lane CBM is the same machine model as the fit split: transfer to CBM is cross-campaign only.
8. Class overlap on the index (non-separable data) caps BA below 1 for every cut; that is a result, not a crash.
9. If the fit split is degenerate the verdict is INCONCLUSIVE; no fallback cut is chosen.

## 10. What the author has seen (disclosure)

The held-out split is not blind to the author. The mds2 Summary sheet and the Lane tables are committed in the repo and
were read to build the ledger; the brief quotes the Lane CBM depth over half width (1.4 to 1.8) and the app indices;
the repo note gives the Lane CBM indices 13.9 to 18.6; Weaver Sec. 4.1 and Table 4 place the IN625 morphology
transition in their own units (SOURCES section 1 item 4). The safeguards are structural: a label-blind split rule, a
fit rule with no free choice, and tests that show the fitted cut is invariant to held-out geometry and that no
held-out label is read before the fit returns. The gate should judge the PASS rule with this disclosure in mind.

Amendment 1 adds what follows, stated plainly because it changes what a PASS means.

1. The baseline's held-out errors were known when the P2 and P3 margins were set. Arm B (cut 20) misses exactly the
   three Lane CBM classes (app index 18.57, 17.07, 13.94; depth over half width 1.77, 1.37, 1.20) and makes no other
   held-out error: BA(B) = 0.70 with 3 errors. The margins (gain 0.15, two fewer errors) were chosen with this known.
2. Consequence: on the held-out split every cut in (9.88, 17.07] passes P1, P2 and P3 (9.88 is the mds2 AMMT
   D4sigma 144 um unit, not keyhole; 17.07 is Lane CBM B, keyhole). The fit-split boundary on the 195 W / 800 mm/s
   EOS spot series (labels flip between estimated D4sigma of about 105 and 125 um, as read by the pre-registration
   gate) sits near app index 12 to 15, inside that window. The outcome of P1 to P3 is therefore effectively known
   before the run; a PASS on those items is not a surprising success.
3. Inside that window only two held-out units constrain where the cut sits: Lane CBM C at 13.94 (keyhole) and the
   mds2 AMMT D4sigma 122 um unit at 12.67 (not keyhole). The held-out-admissible interval (section 7) can only be
   (9.88, 12.67], (12.67, 13.94] or (13.94, 17.07]. The mds2 AMMT units are one power and speed with a spot series.
   Only (12.67, 13.94] is error-free on the held-out split (tp 5, fn 0, tn 8, fp 0). The other two intervals each
   carry one held-out error and still pass P1 to P3: a cut in (9.88, 12.67] calls `mds2-ammt-row10` (index 12.67,
   depth over half width 0.814) keyhole, a false positive (BA 0.94); a cut in (13.94, 17.07] misses `lane2020-CBM-C`
   (index 13.94, depth over half width 1.20, not ambiguous), a false negative (BA 0.90). These counts were
   recomputed by the gate and the worker from held-out indices and labels at fixed trial cuts, with no fit. In those
   two cases the held-out data contradict an onset inside the interval, which is why section 12 changes the
   licensed sentence.
4. P5 is not an independent check on this set: the secondary labels (depth over D4sigma/2 > 1) equal the primary
   labels on all 13 held-out units.
5. P6 depends on the 56 leave-one-out refits, which have not been computed; its outcome is not claimed here.

## 11. Procedure

1. Gate approves this file (ORCHESTRA section 2, RESEARCH step 3). Nothing runs before that.
2. One declared run from the repo root, after the declaration, runner and ledger are committed and clean:
   `PYTHONDONTWRITEBYTECODE=1 python -B python/tools/lpbf_in625_regime_threshold.py run --declared-run`.
   The runner refuses to start if any of the three files is uncommitted or modified, if the ledger hash differs from
   the pin, if the solver cuts differ from 15 / 20, or if the results file already exists.
3. Output: `docs/research/RESULTS_in625_regime_2026-10-11.json` (hashes of the declaration, runner, ledger, workbook,
   loader and solver; git HEAD; fit; all arms; verdict; held-out-admissible interval, arm F's per-unit held-out
   calls and the licensed claim;
   sensitivities; per-unit table). A written
   `RESULTS_in625_regime_2026-10-11.md` follows and quotes only numbers from the JSON.
4. Crashes are recorded with the traceback and the fix; the run is not repeated to improve a number. A negative result
   is committed and reported.
5. Gate verification: recompute the fit from the ledger, recompute the held-out metrics, confirm that no held-out unit
   entered the fit, and check the hashes.

## 12. What a PASS allows

What a PASS licenses (amendments 1 and 2), and nothing more, depends on arm F's held-out errors at T_F:

1. F makes no held-out error: "the IN625 depth > half-width onset on the app index lies in the held-out-admissible
   interval (L, U]; T_F is the fit-split point estimate, not a held-out-validated value".
2. F makes one or more held-out errors (P3 allows one): the sentence names every misclassified held-out unit id with
   its index, measured class and call, and says that the held-out split does not place the onset in (L, U]; it only
   says that every cut in (L, U] makes the same held-out predictions as T_F, these errors included, and that T_F is
   the fit-split point estimate, not a held-out-validated value. No onset location is licensed in this case.

Neither case licenses a held-out-validated threshold to 0.1: the held-out split cannot tell T_F from any other cut in
(L, U]. The runner writes the sentence with the numbers filled in (`licensed_claim`, output `licensedClaimIfPass`)
from F's held-out confusion and per-unit calls (output `heldoutCallsF`), and refuses if the two disagree; synthetic
tests pin both branches (`LicensedClaim` in the test file). The RESULTS file and any BUILD note, product note or PROOF
entry must quote the interval and F's held-out errors, not only the BA.

A PASS allows a planned physics bump on a BUILD lane: a per-alloy keyhole cut for Inconel 625 equal to T_F in the app
convention, a rewritten `REGIME_MATERIAL_NOTE_IN625` that states the source, the truth criterion, the held-out score
and the held-out-admissible interval, a fingerprint bump of `lpbf_thermal_solver.py` (and the mirror in `lpbf_public_datasets.py`) with goldens,
parity, a PROOF entry and an Opus gate. Other alloys keep 15 / 20. A PASS does not allow moving the transition cut 15:
the solver also uses 15 as the onset of its multi-reflection absorptivity step, so moving it would change depth
numbers. If T_F is below 15, the order of the IN625 labels is a BUILD-lane decision (section 8 item 5). A FAIL or
INCONCLUSIVE leaves the product unchanged and is committed as a negative result.

## 13. Files

| file | role |
|---|---|
| `docs/research/SOURCES_in625_regime_2026-10-11.md` | sources, locators, convention reconciliation, ledger description |
| `docs/research/PREDECLARED_in625_regime_2026-10-11.md` | this declaration |
| `data/benchmark/in625-regime-ledger-2026-10-11/units.csv` | the 70-unit ledger (transcription, pinned) |
| `python/tools/lpbf_in625_regime_threshold.py` | ledger builder, fit rule, metrics, PASS rule, declared run |
| `python/test_lpbf_in625_regime_threshold.py` | synthetic tests (fit rule, ties, held-out isolation, split, convention, PASS rule, run guard) |
