# SOL-C Ti64 keyhole consultation

2026-10-16. Reviewed branch `feat/solidification-solc`, HEAD `fd98bbe76bd5624bff53c47455c413375c0a008e`, worktree `Metalliksa-1-wt-solc-impl`.

## Decision

Recommend **(a): make the existing conduction-field surrogate the default Tier 2 estimate scenario when the Fabbro leg controls depth**, with the warning below and explicit surrogate identity on every dependent quantity. This is a recommendation for a separately labelled model scenario. It does not turn the conduction field into the actual keyhole-controlled temperature field or admit a resolved cavity-front result. Keep the latter unavailable.

The default Ti64 keyhole classification is physically plausible. The exact served depth switch is a screening construction, not a verified Ti64 onset law. P8's approximately 31 W is a different, loss-free recoil-temperature event and does not diagnose a units error. Neither number justifies changing the served threshold or tuning absorption to recover SOL-C availability.

This consultation supersedes **no installed contract**. Adoption would require a focused implementation change to the default-selection rule in SPEC A5/A6 and the channel's default/surrogate metadata. A7's downstream physics gates remain. No such change is made here.

## 1. What the served switch actually does

Read directly: [thermal solver](../../python/lpbf_thermal_solver.py), `calculate_meltpool_physics`, `classify_enthalpy_regime`; [Fabbro leg](../../python/fabbro_keyhole.py), `fabbro_keyhole_depth_m`; [SOL-C](../../python/lpbf_solidification_estimates.py), `served_solve`, `compute_solidification_estimates`. Direct source inspection was used instead of refreshing graph artifacts, keeping writes inside the authorized paths.

Three separate decisions must not be conflated:

1. Ti64's regime **label** is conduction below H=15, transition from 15 to 20, keyhole from H=20, where H is the repository's normalized enthalpy.
2. The Fabbro depth is zero below H=15, multiplied by `(H-15)/15` for 15<H<30, and fully enabled from H=30. This ramp is explicitly uncited in the implementation.
3. SOL-C's hard refusal is driven by **`fabbro_depth > d_iso`**, where `d_iso` is the selected conduction field's extracted depth. It is not driven directly by the regime label, P8 P*, a measured cavity, or a melt-flow calculation. A labelled keyhole case can still retain the conduction front.

For the unmodified IR Ti64 tuple, SI quantities are:

```text
r = d/2; alpha_s = k_s/(rho cp_s)
H = A_index P / [rho cp_s (TL-T0) sqrt(pi alpha_s v r^3)]
Pe_s = v d/(2 alpha_s)
e_F = A_flat P b(H) / [k_s (Tv-T0) (2.4 Pe_s + 3)]
depth = max(d_iso, e_F); refusal = (e_F > d_iso)
```

`A_index=.35`, `A_flat=.32`, `rho=4430 kg/m3`, `cp_s=526 J/(kg K)`, `k_s=6.7 W/(m K)`, `TL=1660 C`, `Tv=3287 C`. The index and Fabbro retain room-temperature property conventions; the conduction field instead uses the temperature-interval mean properties. The stored Tv used by this served leg has unresolved provenance. These are implementation inputs, not measurements of the current specimen.

At **280 W, 940 mm/s, 80 um, preheat 200 C**, the checker reproduces the question's outputs: H=39.08, Pe_s=13.08, e_F=125.99 um, and a conduction field whose globally deepest centre-plane liquidus point is 70.85 um. The served keyhole-depth flag is true. Opt-in outputs are G=1.80e7 K/m, R=.124 m/s, cooling=2.24e6 K/s, G/R=1.45e8 K s/m2, PDAS=1.08 um, SDAS=.482 um, and KM progress=.826. Thus **200 C reproduces the supplied case**; the prompt's P/v/d alone did not specify a complete thermal request. At preheat 80 C the same P/v/d gives H=36.11 and G=2.01e7 K/m; at 25 C H=34.89. All three remain depth-controlled by Fabbro. These are computed scenarios, not observed dimensions or microstructures.

The controlling leg is not universal over realistic parameters. The following small synthetic grid uses Rosenthal, 80 um, preheat **80 C**, layer 40 um, hatch 100 um. Each cell reports `H / controlling leg`; C means conduction, F means Fabbro. This is an availability diagnostic, not a process-window benchmark.

| Power W | 700 mm/s | 940 mm/s | 1200 mm/s |
|---|---|---|---|
| 100 | 14.94 / C | 12.90 / C | 11.41 / C |
| 150 | 22.42 / C | 19.34 / C | 17.12 / C |
| 200 | 29.89 / F | 25.79 / F | 22.83 / C |
| 280 | 41.84 / F | 36.11 / F | 31.96 / F |

For example, 200 W/1200 mm/s is labelled keyhole but SOL-C is not rejected by the depth flag. At 280 W/940 mm/s, increasing the declared diameter to 160 um gives H=12.77 and conduction control. This does not establish how frequently real machines occupy either leg.

The H=15/20/30 powers at 80 um and preheat 80 C are respectively 100.4/133.8/200.8 W at 700 mm/s, 116.3/155.1/232.6 W at 940 mm/s, and 131.4/175.2/262.8 W at 1200 mm/s. None is itself the depth-crossover power. More generally H scales as `P/(sqrt(v) d^1.5)` at fixed material/preheat; the exact refusal additionally depends on the selected field and its depth extraction.

## 2. Literature comparison and the 31 W question

[Gan et al. 2021](https://pmc.ncbi.nlm.nih.gov/articles/PMC8062476/), Results, Eqs. (1),(2), defines `Ke = eta P / [(TL-T0) pi rho cp sqrt(alpha v r0^3)]`, with vapor-depression aspect ratio `e/r0`. It distinguishes Ke<1.4 conduction, 1.4 to 6 transition, and >6 keyhole. Its depression is not the fusion boundary; flow and deposition geometry matter. The study also makes absorption cavity-dependent. These distinctions prevent treating a flat-absorption Ke calculation as a measured onset or an independently validated depth law. Cunningham's Ti64 measurements contribute to Gan's analysis, so these are not two independent experimental validations.

**Our algebraic comparison:** only with identical radius, properties, absorption and temperature difference is `Ke=H/sqrt(pi)`. At the reproduced 200 C case the repository index tuple gives Ke=22.05. Substituting the actual conduction-kernel property tuple and A=.32 gives Ke=11.07. Both are above 6, supporting the qualitative keyhole assignment, but they are different input conventions. At preheat 80 C they are 20.37 and 10.56. Comparing H directly with 6, or with King's commonly quoted 30 without translating beam/property conventions, would be a definition error. The `r0`, Gaussian standard deviation, 1/e2 diameter and FWHM diameter must be recorded separately.

[Cunningham et al. 2019](https://doi.org/10.1126/science.aav4687), abstract and final main-text discussion following Fig. 4, observes keyholes over typical LPBF power/velocity conditions in titanium and explicitly challenges Rosenthal's moving point as the effective source. This supports the presence of a keyhole at ordinary Ti64 settings and limits an actual-front interpretation of the uncoupled point field. It does not establish that every realistic setting is keyhole-controlled by this implementation. No numerical irradiance threshold is imported here from a secondary summary.

[Fabbro 2020](https://www.mdpi.com/2076-3417/10/4/1487), §2.1, gives a cylindrical conduction-loss closure and a geometric threshold involving absorption at finite aspect ratio; §3 treats the inclined-front regime. Its Ti64 example in §3.4 distinguishes the 95 um Gaussian 1/e2 diameter from about 56 um half-maximum effective diameter. These are additional source restrictions on applying the served leg. At the default, the implementation's Pe_s=13.08 is outside its linear-fit range 2 to 10, and its flat A does not model cavity absorption. Low flat A alone cannot establish an overall lower bound on depth when property, beam and geometry transfers are also present. The 15-to-30 ramp is not supplied by this paper.

**Judgment:** keyhole presence is plausible; the precise screening crossover and the numeric Fabbro depth have not been physically established here. No held-out geometry was needed to reach either conclusion.

### P8 is a separate event and hypothesis

The inspected [P8 kernel](scripts/p8_cavity_kernel.py), `threshold_temperature`, `onset_power`, uses a flat Gaussian, a dwell time `a/v` with `a=d/2`, and a temperature response without explicit phase-change or surface-loss sinks. Here and below, the repository's shorthand **loss-free** retains heat conduction into the half-space; it excludes those additional sinks. For its nominal beta=.2 recoil convention:

```text
c = Lv M/(Rg Tv)
Tstar = Tv / [1 - ln(2/(1+beta))/c]       # .6 psat(Tstar) = pamb
gain = sqrt(2) A0/(pi^1.5 K a) atan(sqrt(8 alpha/(v a)))
Pstar = (Tstar-T0)/gain
```

Gain has units K/W, so Pstar has units W. The independent checker integrates the Gaussian Neumann half-space response in the **time domain**, rather than calling the arctangent formula as its oracle. Its stationary limit is `A0/[sqrt(2 pi) K a]`. It also checks a moving-source surface maximum with the same independent kernel. Thus the normalization and units are checked without declaring the onset physically validated.

At v=.8 m/s, d=80 um, T0=293.15 K, the **live** Ti64 tuple is K=16.44854 W/(m K), cp=645.74021 J/(kg K), rho=4430 kg/m3, A0=.32, Tv=3560 K, Lv=9.255e6 J/kg and M=.048 kg/mol. It gives Tstar=3685.44 K and **Pstar=31.363 W**; the independent steady moving-Gaussian peak alternative gives **31.081 W**. The near agreement in this tuple is not a general equivalence of the two models. The live AlSi10Mg tuple gives 157.218 W, versus about 157.1 W in the historical pinned P8 note; this consultation does not change a pin or reconcile different historical material snapshots.

This event is reaching a recoil-pressure temperature on an assumed loss-free flat surface. It is not the occurrence of a sustained deep cavity, `e/d=1`, fusion-region D/W=.5, porosity onset, or the served `e_F>d_iso` event. At Ti64's Pstar the same-tuple flat-absorption Ke is only 1.255, close to the beginning of the transition scale rather than the >6 deep-keyhole classification. The analogous Al number is 5.591. Those evaluations illustrate definition/material dependence, not an experimental match. In particular, extrapolating either scaling to low power does not validate a 31 W measured onset.

The model omits latent melting/evaporation sinks, radiative loss and the evolving optical/free-surface balance. Finite recoil does not by itself close surface tension, hydrostatic/dynamic pressure, melt displacement and cavity stability. Therefore 31 W is **plausible as this conditional thermal inception scale**, but is not established as actual Ti64 keyhole onset. The corrected sqrt(2) prefactor alone does not fix those omissions. P8's own SPEC Amendment 2 B2 records the uncoupled loss-free onset versus surface-balance disagreement; its later falsified flat surface-loss arm is not an independent validation of this onset. Do not use it to rescale the served switch or the rear G/R.

The repository attributes the dwell shape to Trapp 2017 Eq. (3), p.346, [DOI](https://doi.org/10.1016/j.apmt.2017.08.006). That page was not independently retrieved in this consultation. The equation above is admitted here as an independently checked declared heat-kernel model, **not** a newly authenticated transcription of Trapp. The paper does not supply measured Ti64 onset for this tuple in the evidence reviewed here.

## 3. What a default surrogate can and cannot mean

The rear interface is a liquid-solid boundary, not the irradiated vapor-liquid cavity wall. For a stationary solid and a declared quasi-steady field `T(x-vt,y,z)`, the cooling branch has `gx>0`, `G=|grad T|`, `R=v gx/G`, and positive cooling magnitude `v gx`. These kinematic relations are valid for that chosen field. Melt flow affects the **field**; its omission does not make the mathematical front of a conduction model undefined. An uncalibrated model estimate need not first demonstrate experimental accuracy.

Conversely, being behind the cavity does not prove that cavity deposition and convection no longer affect the liquidus. At the reproduced case the conduction branch runs roughly from x=-.205 to -.552 mm, with maximum depth .071 mm, while the controlling depth leg is .126 mm. No source-bound decoupling distance or error bound is established for that branch. Heat ultimately leaving through solid conduction does not imply that an uncoupled flat-source temperature distribution is correct. Cunningham's source-shape observation is relevant counterevidence to such an interpretation.

**Consequently:** default availability is defensible as an explicitly named **conduction-only scenario** in the existing SOL-C estimate channel, at Tier 2 with unknown model discrepancy. It is not defensible as a coupled actual-keyhole rear-front solution. This distinction must be part of the value definition and provenance, not a tooltip that leaves the main numbers attached to the cavity geometry.

Adoption requirements:

- Keep `surrogate=conduction-field` and a field-specific sample/parent identity even when selected by default. Default selection does not change the model's status. The existing `default` flag currently means the opposite for this arm and must not be flipped without updating its contract and consumers.
- Display **Uncalibrated estimate** and the keyhole warning with the values. Propagate the conduction-field origin to PDAS, SDAS, stability/morphology and KM outputs. If a consumer/export cannot preserve this distinction, retain refusal there.
- Sample only this field's own rear liquidus. Do not stretch it to the served depth, infer G by TL/depth, identify the deepest cavity with a liquidus, or mix G from one field with R or a thermal history from another. Preserve local tuple evaluation and spatial-summary definitions. A model scenario can differ geometrically from the separate served depth when that difference is explicit.
- Keep Research/unvalidated status and Tier 2. A coefficient sweep is input sensitivity, not an error interval. Keep W/D, regime, process-window and printability dependencies unchanged; this estimate channel must not feed them.
- Treat the reproduced .826 as **KM first-pass reaction progress** at the A7 evaluation state, not measured phase, a solidification phase fraction or final retained inventory. Its complement is not retained beta. A different machine/build history may not meet that route's assumptions.

### Conditions that still require refusal

| Condition | Required disposition |
|---|---|
| Invalid/nonfinite process, material constants or threshold; absent numerical coefficient | Refuse the dependent quantity. Do not invent an input. |
| No liquidus crossing or only heating/melting-side crossings | No solidification G/R summary, spacing or morphology from that branch. |
| G<=0, R<=0, nonfinite derivatives, R>v under the declared steady-field kinematics, bad root/bracket or inadequate support | Reject affected tuples; refuse a summary without sufficient eligible support. Do not replace failed numerics with a keyhole warning. |
| Stale/mismatched parent, liquidus, units, coordinate/time convention or sample identity | Refuse until a compatible parent is available. |
| A requested actual transient front lacks the necessary local time derivative; the field crosses a scan turn/start/stop but is presented as its resolved history | Refuse that actual-history interpretation. A separately declared constant-speed single-pass scenario remains a different request. |
| A7 spacing capillary inconsistency, applicable planar/absolute-stability gate, primary/eutectic domain failure, absent material/growth route | Refuse that descendant; an available thermal estimate does not override its gate. |
| KM lacks the compatible full-melting path, beta-entry state, monotonic cooling/crossing at preheat+25 K, or violates A7's transus/Ms and conservative cooling-history requirements | Refuse the time-scoped phase progress. Liquidus G*R cannot substitute for this path. Reheating/holds need competing kinetics. |
| User asks for actual cavity-front geometry, keyhole stability/collapse, retained phase inventory or actual pore formation | This surrogate cannot supply those observables. |

A large Ke, an extrapolated property convention, or absence of calibration alone is a warning/tier limit for this declared scenario, not a new universal cutoff. Gan's relatively stable and chaotic examples do not establish a hard surrogate-admission boundary. Strong flow or cavity motion does defeat an **actual-field** claim, but should not be disguised as a numerically precise cutoff without evidence.

### Better source-bound route for an actual keyhole rear front

Use a **single** thermal field with a consistent absorbed-power/deposition distribution and its own liquidus boundary. A source-informed moving volumetric/depth-distributed heat source can be a reduced estimate route; a transient free-surface thermal-fluid solution can additionally resolve cavity motion and advection. Gan's Eqs. (6),(7) and Fabbro's regime/beam conventions are candidate source inputs, not a ready-made Ti64 temperature-field validation. Deriving G/R then requires local gradients, interface normals and compatible time derivatives on that new field.

It is not sufficient to paste a Gan/Fabbro depth onto the old surface field, choose Goldak axes from the desired answer, or promote P8's current uncoupled line/point hypothesis. Unknown deposition parameters must remain declared assumptions or be identified with separately admitted evidence. A future coupled route needs its own energy/source consistency checks and independent comparison; no held-out targets should be opened to make this consultation's recommendation. This route is scientifically better for the actual-front observable, but is not required before offering the clearly scoped Tier 2 reference above.

## 4. Exact additional warning

> Keyhole regime. These estimates use the rear solidifying front of a conduction-only temperature field. The field does not include keyhole energy deposition, melt flow or cavity motion and is not coupled to the served melt-pool depth. Spacing, morphology and phase estimates inherit this assumption.

Keep the existing uncalibrated tier label separately. This warning has no accuracy claim, percentage error or em dash.

## 5. Reproduction, evidence limits and continuation

Run the [read-only checker](scripts/check_sol_c_ti64_keyhole_consult.py):

```powershell
python -I -B docs/research/scripts/check_sol_c_ti64_keyhole_consult.py --check
```

On the reviewed head: **PASS**, approximately 1.5 s per complete execution. It evaluates 15 explicit synthetic process tuples with process maps disabled, reproduces current default refusal and opt-in values, checks the switch against an independently maximized conduction depth away from crossover, and compares 32 numerical gradients with an analytic derivative of the actual regularized Rosenthal field. Maximum relative gradient discrepancy is approximately 9.95e-8. Independent time-domain Gaussian integration verifies P8 normalization/pressure and the moving-peak alternative. Radius exponent and speed-unit perturbations exercise the dimensional comparisons. These checks verify code and algebra only; spacing, morphology, KM constants and experimental accuracy are not revalidated by them. No JSON receipt or other generated file is written.

Primary-source search on 2026-10-16 targeted Ti64 keyhole onset, Gan's Keyhole number, Cunningham's transition imaging, Fabbro's source/beam definitions and Trapp's dwell response. Source verification and counterargument review used AI-assisted research. Gan's open full text was read; Cunningham's relevant text and Fabbro's sections were also checked through publisher search-index text when direct retrieval was blocked. Trapp's exact equation-page authentication remains explicitly unavailable. This is a focused consultation, not a systematic literature review or experimental validation. No numerical Cunningham transition-line digitization or universal measured onset power is claimed.

No measured melt-pool depth/width content of `leis2021`, `hyer2020`, `aboulkhair2016`, `ruckh2025`, `gong2014`, `ullah` or `wimmer2020` was opened. No measured rows, bands runner or `.orchestra/external-data` were accessed. No served source, golden, pin, parity checker or CI file was changed. Existing unrelated changes were preserved.

**Continuation:** maintainer may adopt recommendation (a) in a separate scoped implementation task, carrying the warning, default-selection semantics and descendant provenance together. Until then the current refusal remains installed. Keep the coupled actual-front route as separate research work; this consultation authorizes no push or held-out-data access.
