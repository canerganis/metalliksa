# SOL-C round 3: review resolution and acceptance contract

2026-10-16, research/solc-estimates, baseline a141b369. This research handoff changes only the allowed source notes, append-only SPEC and research checkers. It installs no served calculation or channel. Numerical/source checks are not experimental validation. Amendments 5 and 6 remain historical; Amendment 7 takes precedence.

## Acceptance before implementation

1. Every local PDAS/SDAS passes a named alloy/proxy capillary-consistency gate; physically inconsistent output is refused, never floored.
2. No source-domain extrapolation or family transfer reaches Tier 1, even with an executed sweep. Inherited thermal-parent transfers also count.
3. Thermal OFAT uses a recomputed rear-branch summary in all eleven arms, a broader declared absorption scenario and explicit input-sensitivity wording/precision.
4. Verify the CET convention and attribution; do not substitute an unverified original-Hunt convention.
5. Block an Al primary tip at/below the eutectic; expose tip Peclet inadequacy in all five alloys.
6. Make the KM evaluation state deterministic, report it, and stop calling its complement retained beta.
7. Define a typed prospective emit contract with separate warning and blocking vocabularies; preserve the current v1 registry.
8. Bind parsed source coefficients into the real estimator; exercise actual mutations and pin the historical morphology receipt.
9. Use one named Al10Si0.45Mg nominal scenario across spacing and phase references; disclose absent secondary arms everywhere.
10. Remove unreachable warning code; require the visible unresolved-nucleation explanation for fraction and CET class.

## 1. Capillary consistency, including all PDAS and SDAS routes

Use the **same named binary proxy** as the alloy's morphology row, not a Ni threshold for Ti or Al. The source constants C0,k,|m|,D,Gamma are from Ghosh2018 Table6 (Ti effective-slope closure), Azizi2020 TableII (Al), Ghosh2017 Table2 (Ni5Nb) and Gerstgrasser2021 Table7 (316L Fe-C). The [source audit](sol_c_a7_source_audit.md) authenticates newly obtained originals. These proxies transfer to real alloys; their stability scales are not measured full-multicomponent limits.

Let P=|m| C0(1-k)/k, diffusion length lD=D/R, and constitutional drive S=P/lD-G. For a sinusoidal interface displacement h cos(omega*x), the local-equilibrium driving temperature perturbation is S h, while Gibbs-Thomson capillarity opposes it by Gamma omega^2 h. In this **declared one-sided, quasi-static binary screening approximation**, a growing perturbation requires S-Gamma omega^2>0. Thus:

`lambda_cut = 2*pi*sqrt(Gamma/(P*R/D-G))`, when `P*R/D>G`.

Units are sqrt[(K m)/(K/m)]=m. The low-G limit is `2*pi*sqrt(Gamma D/(P R))`. For Ni5Nb P=56.875 K, Gamma=3.65e-7 K m, D=3e-9 m2/s and R=.1 m/s, that limit is about 0.087 micrometres; finite G increases it. The separately printed 57 K in Ghosh's PDAS correlation remains 57, not a silently changed correlation coefficient. If chi<=1 or R>=P D/(k Gamma), the binary dendrite route is also refused. Every scalar, or each member of a PDAS alternative record, must be >=lambda_cut. A missing/invalid proxy needs source-bound stability inputs; it cannot silently disable the gate. Arithmetic is performed locally before aggregation, with retained rejected-sample IDs and support diagnostics.

Mitchell at cooling 1e5,1e6,1e7 K/s gives approximately 0.014,0.0032,0.00076 micrometres. At R=.1 these all fail the Ni gate and are **no-value**, with existing blocking reason `outside-source-model-domain`. No Tier 2 warning can rescue them. Keep raw values only in labelled rejected-model diagnostics, not quantity values. Visible text: "This correlation predicts a scale below the capillary screening limit of its stated binary model. A compatible rapid-solidification spacing model is needed."

The review's implication of a universal experimentally exact minimum shared by every primary and secondary spacing is too strong. Mullins-Sekerka original PDF was not obtained, and the finite-Pe dispersion, anisotropy, solute trapping and sidebranch dynamics are not solved here. The equation above is our disclosed conservative screening refusal. It neither claims a newly verified original MS equation nor borrows Brooke Eq9 with an invented -G term. It still rejects the questionable values rather than retaining them with a warning. A passed gate does not establish physical dendrites or branching.

## 2 and 3. Tier ceiling and thermal display

Any family transfer, source-process/observable transfer or actual source-domain violation in a quantity or its physical dependency closure forces `Physics estimate`. It has no `estimateBand`. An executed OFAT/joint sweep may remain solely an auxiliary `inputSensitivity` note, never an error interval or promotion. This includes IN718/IN625 PDAS on Ghosh's fixed-G line because the Ni5Nb-to-real-alloy transfer persists there, and every default morphology/CET route. Geometry support never authenticates chemistry or nucleation.

For the present inherited physical parents, use the **conservative default Tier 2 for G,R,cooling,G/R in all five alloys**. AlSi10Mg and 316L have explicit endpoint family transfers; the other default paths retain ambient-density/high-temperature and reduction/optical transfer limitations. Do not erase a limitation by relabelling it modelConvention. Tier 1 remains a possible future in-domain input-sensitivity construction once the selected parents actually establish that domain and all numerical/support gates pass. The manufactured checker demonstrates that construction, not an actual-alloy Tier 1 result.

The [thermal note](sol_c_a7_thermal.md) defines exact user text and ranges. Absorptivity is now `[0.5*A0,min(1,1.5*A0)]`, a broader declared scenario, not a measured source interval. Other A6 ranges remain k/cp +/-20%, rho +/-5%, TL +/-quarter(TL-TS). Recompute eleven whole-field arms, bottom/tail/roots and length-weighted local-output medians. The range name is **input sensitivity range**. It excludes model error, which for conduction without melt-pool flow can exceed the range, and excludes input interactions and alloy transfer error. Thermal and spacing display **two significant figures** at either numerical tier; chi and fractions display **one**, retaining raw precision and small nonzero values in scientific notation. No confidence or accuracy claim is made.

## 4. Verified CET convention and the disputed threshold

DOI10.1016/j.addma.2023.103802 is **Durga and Lindwall, Additive Manufacturing78**, not Mishra, volume70. Its primary publisher-indexed section2.1 after Eq9 explicitly uses true fraction f<=.0049 for columnar and f>=.49 for equiaxed. Retain this named **Durga convention**, and cease attributing it to newly read Hunt1984. The original PDF remains absent, so this is indexed-primary-text verification, not authenticated PDF bytes.

The distinction is arithmetically material: f=1-exp(-phiExtended); extended .0066 gives true .0065782676, not .0049, while extended .66 gives .4831486655, not exactly .49. True .0049 corresponds to extended .0049120444. Replacing .0049 by .0066 on true fraction would prematurely classify f=.0055 as columnar; the retained convention calls it mixed. This is the more conservative columnar decision. The verified source convention, imperfect approximate extended correspondence and original-Hunt uncertainty must all remain visible. Threshold tests include f=.0048,.0055,.48,.50 and independent exponential conversion.

## 5. Eutectic and tip-law domain

Al at C0=10 with the transferred Azizi coefficients has P=435 K, which is **not** an available primary alpha-Al undercooling. Stop the primary Hunt envelope/class when `deltaTc >= |m|*(Ce-C0)`. Ce=12.6 wt% is now PDF-verified in Metals2022 Table1; with the chosen |m|=6.5 the compatible linearized interval is **16.9 K**. At R=.1 m/s Hunt gives 36.84 K, below the binary eutectic: no fraction/class; keep the finite chi index separately. Visible text: "The primary aluminium tip reaches the eutectic in this model. A coupled primary and eutectic growth model is needed for a grain fraction here." Do not substitute Metals2022's separate 23 K TL-TE interval into Azizi's coefficients. At/beyond eutectic composition a primary-Si/coupled model is needed.

For every alloy compute the low-Pe model's own diagnostic tip radius rhoH from the closure `deltaT=Q R rhoH/D+2 Gamma/rhoH`: stationarity gives `rhoH=sqrt(2 Gamma D/(Q R))=4 Gamma/deltaTc`; `Pe=R rhoH/(2D)`. This is a **diagnostic of the chosen Hunt reduction**, not a finite-Pe KGT solution or a radius read from Brooke Eq9. Pe>=0.1 triggers `low-peclet-tip-law`; .1 is a declared conservative adequacy trigger for the asymptotic requirement Pe<<1, not a universal instability constant. Show "The tip Peclet number is {Pe}. The low-Peclet tip approximation is outside its declared screening range; finite-Peclet growth may change this estimate." Warn every applicable fraction/class and keep it Tier 2, except hard physical gates still refuse. Source bounds for chi, tip>P and admitted absolute stability remain in force. Tests cover the Al .1 refusal and a valid .001 case, and Pe diagnostics in all alloys.

## 6. Ti64 KM evaluation and terminology

Define `finite-25K-above-preheat-v1`: follow the material point from full melting, then choose its **first monotonic downward crossing of T_eval=T_preheat+25 K**. The 25 K offset is an explicit deterministic evaluation convention, not a source transformation parameter. Report preheat, offset, evaluation temperature/time, bracketing path-node IDs, interpolation and refinement as specified in the emit schema. No arbitrary final stored node, asymptotic arrival at preheat, liquidus G*R substitution or room-temperature default is allowed. Missing crossing means provide/extend a compatible path; there is no retained-inventory number for the incomplete scenario.

Before the crossing reject reheating or holds/slow segments below the source beta transus, including segments straddling it. Keep the source's 410 K/s condition through transus to Ms, and the disclosed conservative extension down to evaluation. Later cooling/reheating does not retroactively alter this **time-scoped first-pass reference**, and is not a claim about the later retained inventory. Predicting later retained phases needs the competing kinetics/history. A separate rapid-quench-limit reference, if requested when that path fails, must state its counterfactual cooling assumption and use the same evaluation-temperature rule; it is never a retained phase inventory.

Salsi PDF9 Eq19 and PDF12 before Fig7 now verify km=.005 K^-1, Ms=575 C, with the source's 998 C transus and 410 K/s rule. Ms=575 C is a fitted source choice with **unquantified uncertainty**. At preheat25 C evaluation is50 C; beta0=1 gives alpha_m=.92756024, displayed model about .9. At a warmer preheat this changes; the value is primarily controlled by evaluation state, not G/R. Preserve reaction-progress basis. The complement .07243976 is the **untransformed KM asymptote**, not retained beta. Any pre-existing 1-beta0 constituent is separate.

For values rounding to .9 or higher show: "Physics estimate for a single rapid cooling pass: mostly alpha martensite or massive alpha (model about {fraction}). The remainder is the untransformed KM asymptote, not an estimate of retained beta. Ms is a fitted source parameter with unquantified uncertainty. Uncertainty is unknown and may be large. Calibrate to your machine for better accuracy." For smaller positive values omit "mostly" and show the coarse fraction; at T_eval>=Ms explicitly state zero transformation **by this evaluation state**. No universal .9 claim.

## 7, 9 and CET wording. Emit contract, composition and precision

The [prospective schema](sol_c_a7_emit_contract.md) gives the complete field/type/unit/enum/required-when table, separate value warnings from blocking reasons, six typed new definitions and existing Ni alternatives. The five A6 prospective numerical definitions now have exact units/fraction bases; a sixth is added for Scheil microconstituents so that Al+Si eutectic is never disguised as a phase. No new definition is installed in the closed v1 registry. `outside-source-model-domain` is blocking only; `domain-extrapolation` and `alloy-family-transfer` are value warnings. Two-digit thermal/spacing and one-digit chi/fraction metadata resolve the previous conflict. Source label and tier remain independent.

Choose **Al-10Si-0.45Mg by mass** as the single explicitly selected nominal scenario across all routes, with cSi=.10 and cMg=.0045 in mass-fraction arithmetic. Actual supplied chemistry always wins. Gandolfi's separate 1Mg law is a named alternative only; no interpolated Mg correlation. In the zero-solubility equilibrium reference this changes fractions to .8955 alphaAl, .097400072 Si and .007099928 Mg2Si. Display about .9, .1 and .007, with the rounded-total caveat, not false exact closure after rounding. Scheil's binary primary/eutectic split remains .23328924/.76671076; Mg is omitted by that disclosed binary model, not assigned a different nominal value.

Every Ti, Al, 316L, IN718 and IN625 SDAS explanation appends: **"Secondary arms may not form."** If arms are known absent, the hard no-value rule and actionable branching-model requirement still apply. This is not cured by a gate-passing correlation.

Every valued envelope fraction and CET class must include: **"N0 and activation undercooling are declared scenarios with Unresolved provenance. The model class may change substantially with these scenarios. Uncertainty is unknown and may be large. Calibrate to your machine for better accuracy."** Gao's unverified corrigendum makes the Ti nucleation provenance especially material. A sensitivity class-set is auxiliary input sensitivity, not a probability or promotion.

## 8 and 10. Changed checks and evidence boundary

`sol_c_a6_spacing_check.py` now parses Ti HTML, Al/316L/Mitchell PDFs and Ni Table2/Eqs7/8 into coefficients actually consumed by `raw_estimate` and the gated `estimate`. Source-law algebra is tested even when its raw scale is rejected, never counted as an accepted value. Independent Decimal/inverse/fourth-power oracles remain. Actual estimator dependency/code mutations change mm/s conversion, exponent, Ni prefactor and the capillary gate; the real checks must reject each. Every alloy/spacing combination has a tiny-output refusal test and independent drive-minus-capillarity sign checks.

`sol_c_a6_thermal_check.py` now recomputes all rear-branch roots/32 nodes and chord-length weights for all11 fields. An independent radial isotherm parameterization, finite differences and absolute-deviation median minimization verify the summaries and input-sensitivity extrema. Real stale-root, mean, separate-median and tier-cap mutations are rejected. The removed self-containment and disconnected median arithmetic were not evidence.

`sol_c_a6_morph_phase_check.py` pins the unchanged historical receipt SHA256 `d7c4d4d2b713145d623bf3edb44eb3cda63e6e3e2b6c04ca641ac4b93900e929`; the source audit supersedes its historical bibliography/authentication limits without altering the old receipt. Unreachable chi/tip warning branches are removed. Independent integration/unit/mass-balance checks now include deterministic KM crossing, endpoint truncation/extension, preheat dependence, first-pass scoping, slow straddling/held paths, Al eutectic and all-alloy Pe. `sol_c_a7_sources_check.py` authenticates the newly downloaded originals; `sol_c_a7_emit_check.py` checks actual mutated payloads. No checker downloads files or silently skips missing prerequisites.

## Final per-quantity and per-alloy disposition

T2 means the permitted numerical model route, conditional on compatible finite inputs, current parents and the gates above. X means no value for the specified physical failure/missing model; it never means unknown uncertainty alone. Current default routes do not claim Tier 1; a future wholly in-domain thermal route may earn T1 only after the complete executed/refined sensitivity construction. No actual-alloy sweep or served installation is asserted here.

| Quantity | Ti64 | AlSi10Mg | IN718 | 316L | IN625 |
|---|---|---|---|---|---|
| G; R; cooling; G/R | T2 conduction kinematics, auxiliary OFAT only | T2, endpoint family transfer | T2, ambient/reduction transfer | T2, endpoint family transfer | T2, ambient/reduction transfer |
| PDAS | T2 Mizukami, capillary gate | T2 Gandolfi, capillary gate | T2 Hunt/Kurz-Fisher Ni5Nb, physical gates | T2 Bunaziv, capillary gate | T2 Hunt/Kurz-Fisher Ni5Nb, physical gates |
| SDAS | T2 Mizukami, capillary gate | T2 Gandolfi0.45Mg, capillary gate | T2 Mitchell only if gate passes; X for reviewed LPBF fixtures | T2 Bunaziv, capillary gate | T2 Mitchell transfer only if gate passes; X for reviewed fixtures |
| Planar stability chi | T2 disclosed Ti closure | T2 dilute Al-Si transfer | T2 Ni5Nb | T2 Fe-C proxy | T2 Ni5Nb |
| Envelope fraction/CET | T2 Hunt/Durga scenario if physical gates pass | T2 below primary eutectic limit; X at R=.1 | T2 if tip/stability gates pass | T2 only below proxy tip bound | T2 if tip/stability gates pass |
| Phase model | T2 time-scoped KM progress | T2 binary Scheil constituents and separate ternary equilibrium reference | X: missing phase-resolved segregation/kinetic model and path | X: missing full chemistry and competing phase-growth/history model | X: missing multicomponent phase-selection/kinetic model and path |

Source gaps are Durga and Brooke original PDFs, Hunt/MS original PDFs, Gao Table2 PDF and corrigendum content. Durga primary indexed text and Brooke complete authenticated XML/HTML support the explicitly bounded uses above. RC1 typed migration, actual-alloy field/sweep/refinement and consumer transport checks remain the continuation; no push is authorized.

## Verification result

All nine root commands completed with exit0 on 2026-10-16: `python -I -B docs/research/scripts/{sol_c_a6_thermal_check,sol_c_a6_spacing_check,sol_c_a6_morph_phase_check,sol_c_a7_sources_check,sol_c_a7_emit_check,sol_c_kinematics_check,sol_c_contract_check,sol_c_spacing_check,sol_c_density_check}.py --check` (brace notation lists separate commands, not a PowerShell expression). RC2 PASS; 50 prospective payload acceptance/mutation checks PASS; six new PDF/two Brooke representation pins PASS; SPEC prefix unchanged after newline normalization, with the original worktree bytes preserved before the appended amendment. Focused diff whitespace and local document-link checks passed. The old A5 producer check remains an immutable-baseline transcription check, not installation of A7's new gates in served code. No forbidden measured-row benchmark was run. No physical or served-channel validation is claimed.
