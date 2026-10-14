# Solidification and precipitation: implementation specification

Requested record date: 2026-10-14; prepared against `835466fabca27d0209b29599fde7fa05a9b9ee75` on `research/solidification-astra`, completed 2026-10-15.
Status: proposed physics/contract changes, **not implemented**. [Audit and primary-source ledger](AUDIT_solidification_chain_2026-10-14.md) define the evidence and current defects F01-F11. Source IDs S01-S10 below refer to that ledger.

## 1. Design decision and acceptance boundary

Keep Python as the scientific authority. Build an explicit chain:

`composition + material state -> assessed thermodynamics -> eligible thermal-interface samples -> local solidification screens -> conserved segregated solid state -> subsolidus T(t) -> named transformation/precipitation model`.

Each arrow is conditional. It is permissible for equilibrium, thermal G/R and literature segregation to be available while final phase fractions, CET or precipitation are unavailable. A missing arrow must not be filled by an empirical client fallback, constant cooling rate, borrowed alloy coefficient, or melt depth. No change to Build Job's decision ladder follows from this work.

Immediate deliverable is an honest, conserved, reproducible research chain for the existing methods. Quantitative final Ti64/AlSi10Mg microstructure and precipitation strength remain unavailable until the required state, coefficients and independent evidence exist. The current Python stepwise Scheil is retained and corrected, not replaced with the historical power law. Full coupled phase-field/CFD/KWN is not a mandatory prerequisite for the honesty fixes.

Acceptance distinguishes software invariants, numerical convergence, source reproduction and blind physical validation. Passing the first three never promotes a module to `Validated simulation`. Benchmarks must reserve untouched evaluation data before calibration and use compatible phase definitions, fraction bases, thermal intervals and microscopy protocols. Measured melt-pool depths remain excluded from this lane.

## 2. Common quantity contract

Add a Python-owned quantity envelope, propagated unchanged by service/UI:

| Field | Required semantics |
|---|---|
| `status` | `computed`, `partial`, `unavailable` or `failed`; reasons are machine-readable and human-readable. A whole job may succeed while individual quantities are unavailable. |
| `value`, `unit`, `quantityDefinition` | Nullable value with explicit physical observable. Celsius for display and K internally; G K/m; R m/s; positive cooling magnitude K/s; G/R K s/m². Identify signed migration rate separately from a positive solidification speed. |
| `fractionBasis` | Explicit `mole-of-atoms`, `mass`, `volume`, `reaction-progress` or `microconstituent`; no conversion without the needed phase compositions/densities. Distinguish instantaneous newly formed phase amount from cumulative solid inventory. |
| `evidenceKind` | Exactly one RULES kind: `Measured`, `Validated simulation`, `Calibrated simulation`, `Literature estimate`, `Screening only`, `Unresolved`. Model results here are `Screening only`; copied source observations/assessed coefficients can be `Literature estimate`. Unavailable quantities are `Unresolved`. No simulation number becomes `Measured`. |
| `moduleMaturity` | Independent `Research`, `Preview`, `Production` or `Unresolved`; maturity cannot imply evidence. Proposed scientific chain maturity is `Research`. |
| `numericalStatus`, `physicalValidation` | Separate convergence, residuals and solver completion from physical validation; default `unvalidated`, `experimentalValidation=false`, `productionReady=false`. |
| `sources`, `assumptions`, `validity` | Source ID plus primary page/equation/table locator for every material coefficient and relation; assessed-system/temperature/process domain and explicit exclusions. Unsourced required coefficients yield unavailable. |
| `inputIdentity`, `modelIdentity`, `parentIdentity` | Exact solved composition, state/process vector, thermal-field parent and algorithm/database/source revisions. Store complete request alongside hashes. A renamed specimen does not rename an old solved composition. |
| `uncertainty` | Typed `model-alternatives`, `parameter-sensitivity`, `numerical-refinement`, `calibrated-prediction-interval` or `not-quantified`, plus construction and coverage limits. Never call two literature curves a confidence interval. |

Required reason codes include `missing-assessed-system`, `outside-database-domain`, `missing-source-constant`, `missing-thermal-history`, `unsupported-precipitate`, `unverified-equation`, `invalid-interface-sample`, `phase-selection-sensitive`, `residual-liquid-at-termination`, `numerical-conservation-failed`, `stale-parent-input`, `keyhole-field-inconsistent`, `unsupported-fraction-conversion`, and `licence-scope-unconfirmed`. API output must carry the same restrictions as chart, CSV and probe.

Numerical tolerances, mesh spacings, sample-count gates and output cutoffs are **engineering settings**, not fitted material constants. Declare them before runs, source their numerical rationale or convergence protocol, include them in identity and never change them to obtain a pass. This spec sets no new arbitrary material coefficient or acceptance-percent threshold.

## 3. Thermodynamics and conserved Scheil

### 3.1 Input and database admission

Normalise composition once with recorded units/atomic-weight authority. Preserve original input, canonical mole fractions and any trace cutoff. Do not clip a trace fraction and report the original chemistry as solved; either solve it, explicitly request/accept a documented approximation, or refuse with a reason. Preserve all supplied elements, including Fe/O in Ti64.

Resolve an assessed database explicitly and check element **and assessed interaction/phase** coverage, not just an ELEMENT declaration. Record original/repaired database hash, excluded phases and reasons, temperature range, solver/minimizer sampling/settings, phase-model repairs and selection. An excluded phase or missing ordering contribution must remain visible. A parseable TDB is not automatically a suitable multicomponent assessment.

Database policy:

- COST507: existing explicit free-use notice and assessed Al-Mg-Si/Al-Ti-V inventory support local ideal-path research. The standard redistribution licence is unresolved; require clarification before new redistribution. Do not invent a standard open licence.
- MatCalc mc_ti: ODbL 1.0 / DbCL 1.0, Ti-Al-V research scope as documented. Preserve the current approximately 900 C low-temperature fraction restriction at the **API** as well as chart/export/probe; this repository suitability boundary is not a universal physical constant. Fe/O-bearing inputs need a suitable assessment or explicit unavailable state.
- MatCalc mc_ni: same licences; IN718 research with terminal-phase sensitivity guard. IN625 typical Cr/Mo exceeds header tested scope; allow an explicit extrapolation research arm only, with domain note next to each computed quantity. Do not invent an error bar from database disagreement.
- MatCalc mc_fe: same licences; 316L equilibrium/ideal Scheil research with documented excluded phases. Do not silently re-enable C15_LAVES or incomplete BCC_B2.

Exclude mc_ti's incomplete BCC_B2 as well, until a loss-free reconstruction and source-engine equivalence check exists; record that exclusion in model identity. Enforce each database header's declared temperature applicability, including mc_ti 773-2000 K and mc_fe 673-2000 K (their primary TDB header locators in the audit). Out-of-domain requests can only be explicit exploratory extrapolations with withheld unsuitable quantities. Replace the HCP >1% grid heuristic for beta transus with a stated, refined equilibrium phase-disappearance criterion; if numerical resolution/assessment cannot support it, return unavailable with the threshold diagnostic separately. Neither a percentage reporting cutoff nor a fitted transformation temperature is a thermodynamic transus definition.

### 3.2 Algorithm and inventory

Use equilibria of the **residual liquid** with local equilibrium, complete liquid mixing and no solid back-diffusion (S01; thermodynamic model assumptions). Start from a checked liquid state. Keep every phase fraction/composition from numerical equilibrium independent of plotting cutoffs. Distinguish repeated phase composition sets; do not collapse a miscibility gap by overwriting one composition with another.

For residual liquid amount L before a step, equilibrium relative liquid fraction q and relative solid fractions p_j, accumulate newly formed phase inventories `dS_j=L*p_j` and residual liquid `L_next=L*q`. The per-component inventory is `x0_i = L*xL_i + sum_over_all_solid_increments(dS_j*xS_ji)` on a consistent mole-of-atoms basis. These are conservation identities, not material fit relations; S01 supplies the cumulative/instantaneous Scheil framework. Calculate both normalisation and atom residuals from independent stored inventories.

Do not set fractionSolid=1 because `q` fell under 0.001 or any display threshold. Stop with residual liquid and `partial` when the requested temperature floor, time budget, non-convergence or documented numerical stop is reached. A terminal equilibrium with genuinely zero liquid may be complete **only** if phase and atom inventories close. Never assign all remaining atoms to a made-up average solid composition to manufacture zero residual.

Record temperature step/refinement and stability under changed step and sampling. A changed phase set or different minimizer seed revealing different terminal phases must report `phase-selection-sensitive`, not a preferred result chosen after seeing the answer. In particular, current IN718 LAVES remains null as a usable prediction until this issue is resolved independently.

Calculate partition coefficients from phase/liquid tie-line compositions with named solid phase, temperature and concentration basis. Constant-k analytical models remain separate literature screens; they cannot substitute for missing CALPHAD output. Do not report equilibrium phase fractions as final as-built fractions, HCP equilibrium alpha as alpha-prime, or LAVES molar amount as a gamma/Laves eutectic constituent.

Remove the statement that actual solidification universally lies between equilibrium and Scheil. Show both as assumption-bound ideal reference calculations, with rapid-solidification/trapping/undercooling/mixing limits and no universal ordering claim.

### 3.3 Thermodynamic checks

- Reproduce F05's tail and trace-composition fixtures with independently reconstructed inventories; corrected output retains the residual or closes the full inventory without hidden renormalisation.
- Equilibrium/step outputs: finite nonnegative fractions/compositions, sums close under a predeclared numerical tolerance, explicit repeated phase sets, source-unit round trip, single-liquid start admission and unsupported-element refusal.
- Refine temperature step/minimizer sampling and compare liquidus, path and terminal phases; numerical instability stays visible. Disabled Scheil, partial Scheil and failed Scheil are distinct.
- Compare selected simple-system equilibria/paths against primary assessed reference states. If approved later, the separate `scheil` package can be a software cross-check, subject to its phase-multiplicity caveat; agreement is not experimental validation.

## 4. Thermal-interface coupling

### 4.1 Eligible samples and relations

Carry a co-located sample tuple `{position, time, G_vector, G, R_signed, cooling, interfaceDefinition, gradientMethod, fieldIdentity, materialIdentity, valid, reason}`. A quasi-steady translating field admits local `R=v·n`, with normal orientation/solidifying side recorded, and positive cooling magnitude `G*R` (S04 §3.1). Reject melting-side samples rather than taking an absolute rate and calling them solidification. Store actual coordinate frames and scan direction; scan speed alone is not R.

For a transient interface, define level set `F(x,t)=T(x,t)-T_interface(x,t)`. Differentiating `F(x_I(t),t)=0` gives `partial_t F + V_I·grad F=0`; its signed normal speed is `-partial_t F/|grad F|`. For a constant liquidus this reduces to `-partial_t T/|grad T|`. This is an explicitly derived kinematic identity extending the S04 travelling-field convention, not an empirical law. If liquidus depends on local composition, include that field's space/time derivatives or state the fixed-liquidus approximation. Fluid velocity U is neither V_I nor its replacement.

Temperature-history cooling must specify frame and interval. A material-point derivative `dT/dt=partial_t T+u_material·grad T` differs from the partial derivative for advected fluid. Do not mix either with liquid-flow velocity projected onto a gradient. During subsolidus transformation use the tracked solid material-point history.

Local nonlinear calculations precede aggregation. For each valid sample evaluate G/R, G*R, PDAS/CET/trapping as applicable, then summarise those sample outputs. Never evaluate at separate G and R medians. Preserve full numerical precision in transport and model inputs; rounding m/s or mm/s belongs only to display formatting, never intermediate physics. Export sample counts, spatial support, weighting and unavailable counts. Distinguish an area-weighted front distribution from an unweighted fixed-y slice; do not call a centre slice the whole melt pool. Gradient discretisation, boundary interpolation and time sampling need a refinement study before quantitative labels.

Replace old `degenerate-floor` comparisons with actual validity and parent provenance. A physically computed R=5e-5 m/s must not be refused solely for equalling an old heuristic floor; zero/nonfinite/poorly resolved gradients are rejected for stated numerical reasons.

### 4.2 P8/keyhole admission

P8 b6e68dfe is a documented research design, not a present served G/R source. Accept a future P8 coupling only when it provides an identified compatible temperature field/interface or tracked thermal history with geometry, coordinate/beam definitions, assumptions and model uncertainty. A melt-depth/cavity-depth correction cannot rescale conduction G or manufacture local R. Keep physical keyhole G/R null while the field is inconsistent with the served cavity/melt geometry.

An opt-in P8 **conduction-surrogate** arm may show independently named surrogate G/R and model sensitivity only if the proxy origin is explicit: “Conduction-field surrogate; keyhole geometry and this temperature field are not physically coupled.” No blending into the default physical quantities, no claim of physical consistency and no score change. If no source-bound range exists, report `uncertainty=not-quantified`, rather than drawing an invented percentage interval.

Legacy OpenFOAM `meltPoolFoam/solidificationModel.H` must be quarantined from this contract or obtain interface speed from a consistent interface/time derivative; remove its unsourced spacing prefactors and zero-floor manufacture. Verify actual executable/build inclusion before claiming a legacy correction affects the active solver.

## 5. Solidification structure, segregation and CET

### 5.1 Phase/growth identity

Ti64: primary beta-grain solidification is separate from subsolidus beta decomposition (S07-S08). AlSi10Mg: primary Al cellular solidification/eutectic Si and subsequent Si/Mg-Si precipitation are separate (S09). IN625/IN718: gamma solidification/terminal constituents and later gamma-prime, gamma-double-prime or delta precipitation are separate (S02-S03,S10). 316L: no low-alloy steel transformation shortcut.

Delete alloy-neutral quantitative G/R morphology cuts and linear fractions. A constitutional-supercooling/front-stability criterion requires source-bound liquidus/partition/diffusion/undercooling information and declared assumptions; a grain CET criterion additionally requires nucleation. Without them, serve thermal metrics and “No source-bound morphology model for this alloy/process”, with quantitative fractions null. Retain qualitative source observations as observations with their material/process scope.

### 5.2 Spacing and rapid segregation screens

Retain the bounded Ni-Nb PDAS literature arm `lambda1=A*G^(-1/2)*R^(-1/4)` from S04 Eqs.7-8/Fig.6. Its existing Hunt/Kurz-Fisher coefficients 9.56e-4 / 2.6e-3 have units m^(3/4) s^(-1/4) K^(1/2); x support 4e-4 to 1.2e-3 and cooling support 5e4 to 3e6 K/s are source-model ranges, not universal alloy limits. Keep two **model alternatives**; do not use the 2.1e-3 fitted slope without the source fit's offset. Apply only as explicitly transferred dilute Ni-Nb screens, never Ti64/AlSi10Mg/316L. All SDAS stays unavailable without its full coefficient/source set.

Retain Ni literature segregation with its actual mass-fraction/microconstituent basis (S02). Preserve both neglected Nb back-diffusion and fast C-diffusion assumptions; all LPBF transfers stay screening. For IN625 retain unresolved terminal species and document the transferred terminal Nb context (S03); carbon k alone does not supply the missing saturation trajectory.

An independently named rapid-solidification sensitivity arm can use `k(R)=(k_e+R/V_D)/(1+R/V_D)` from S04 Eq.12. The existing V_D alternatives 0.23/0.31 m/s are fitted 1D/2D Ni-Nb phase-field values (S04 PDF17-18), partly numerical trapping; not measured transport constants or a confidence interval. Never silently change CALPHAD/thermal equilibrium chemistry or recalculate a “validated” full-alloy path with these binary values. Missing local R makes this arm unavailable.

### 5.3 CET method and gates

Retain only explicitly sourced sets using

`Gcrit(R,phi)=(a*R)^(1/n)/(n+1)*[-4*pi*N0/(3*ln(1-phi))]^(1/3)`.

S05 Eq.12 and S06 Eqs.4-5 are the verified primary model formulations; the simplified form neglects nucleation undercooling. a has units K^n s/m, n is dimensionless, N0 m^-3. Source alternatives: Knapp a=4.5,n=2,N0=2.65e14 (S05 printed515); Polonsky a=1.23e5,n=3.13,N0=5.4e12 (S06 §3.3/Table2). The latter N0 is a lower bound, not an LPBF material constant; its printed a units conflict with Eq.5 and must be annotated. The critical fractions 0.0066/0.49 are those used in S05 printed514; they are **criterion conventions**, not measured final LPBF phase fractions.

Require verified equation locator, all verified constants, finite positive G/R, source/process domain and explicit nucleation assumption before evaluating. This audit verifies the Polonsky equation but does not change its served false flag; implementation must record the verified primary locator and then enforce the flag. Treat both sets as EBM-transferred model alternatives (`Screening only` in LPBF); neither grants `Calibrated simulation` status for LPBF. No fabricated nuclei for Ti64/AlSi10Mg/IN625/316L; quantitative CET unavailable for those alloys until source sets exist.

CET classification is a screen within a model's assumptions; the threshold's phi is not the final product's measured grain fraction. Null columnar/equiaxed/mixed **fractions** unless an actual spatial nucleation/growth model with appropriate observations is implemented. Tests must cover NaN/Inf/nonpositive inputs, missing/false equation verification, unsupported alloys and process-transfer labels.

## 6. Subsolidus transformation and precipitation

### 6.1 History/state contract

Inputs must include named matrix and product phases, local solid chemistry on a declared basis, initial solid fractions, initial precipitate population if any, grain/dislocation descriptors required by the selected model, and a time-stamped solid material-point T(t) including reheating/remelting/dwell. Remelting resets the relevant solid inventory; partial melting needs conserved phase/solute transfer. No linear cooling curve is created silently from median liquidus G*R.

A non-quantitative literature process note can be shown without a history, but must say “Solid-state transformation not computed: no eligible temperature history/model.” Remove the Ti64 410 K/s universal switch and generic Inconel-to-IN718 substring logic. Use canonical alloy IDs and fail unknown aliases visibly.

### 6.2 Per-alloy method decision

| Alloy | Decision now | Requirements before quantitative implementation |
|---|---|---|
| Ti64 | Equilibrium/primary beta solidification research separately from unavailable final alpha/alpha-prime/beta fractions. | A primary Ti64 transformation model and its complete state/parameter regime, initial beta availability and reheats. S07 is a possible phase-evolution method; S08 is another research candidate, not a coefficient set adopted here. Choose one documented method and reproduce its equations/parameters before implementation. Do not blend methods or extrapolate a CCT fit over LPBF heating without a declared research arm. |
| AlSi10Mg | Withhold time-dependent precipitate fraction/radius and strengthening. Show source-specific Si precipitation and network evolution context. | Resolve Si versus metastable Mg-Si populations and their initial state (S09); stable equilibrium Mg2Si is insufficient. Need interfacial energies, diffusivities/mobilities, nucleation/growth data and identified radius/number-density/volume-fraction observations across treatments. |
| IN625 | Withhold generic aging fractions/radii/strength; preserve source-bound segregation context. | Segregated local Nb/Mo/C chemistry and suitable delta/gamma-double-prime/other product stability and kinetics. S10 treatment observations are context and cannot fit an arbitrary history model by themselves. |
| IN718 | Withhold generic aging fractions/radii/strength. | Source-bound gamma-prime/gamma-double-prime/delta/Laves identities and competing transformation model; local segregation, initial state and a licensed/compatible thermodynamic-plus-mobility assessment if the chosen method requires one. |
| 316L | Transformation/precipitation chain unavailable. | Named target phenomenon/product and alloy-state-specific model; no reuse of the Li low-alloy-steel kinetics by name similarity. |

### 6.3 Generic LSW/strength cleanup

Remove generic coarsening/strength from material-prediction outputs for unsupported alloys, including direct API results. A separate opt-in instructional demonstration, if retained, must use explicitly user-supplied illustrative parameters, maturity `Preview`, evidence `Screening only` and no alloy-specific strength claim.

No new LSW coefficient is adopted. Even a correct asymptotic coarsening law cannot model nucleation, growth from supersaturation, precipitate dissolution, evolving volume fraction, a changing population or arbitrary heat cycles using a universal radius. Do not use a matrix transus as a universal precipitate solvus or equate one matrix molar volume with every product phase. A future coarsening model needs the complete primary derivation and named-species coefficients/definitions first.

Strengthening requires a separately sourced mechanism with precipitate morphology, spacing, shearability/coherency and elastic parameters. Remove the current unsourced 280 MPa / 9 nm curve; do not replace it with an unsourced Orowan or cutting law. Until those inputs are approved, `precipitationHardening_MPa=null`, with an explicit reason. Validate absolute temperatures and aging times before arithmetic; reject -273.15 C and nonfinite temperatures cleanly.

## 7. UI and request/export identity

Bind both solidification labs to `activeSpecimen.lpbf` and canonical material state. Independent scenario controls require an explicit scenario identity and a visible deviation from the shared specimen; never present them as the specimen chain. Python decides quantities, unavailable states and evidence labels; UI only renders them.

Store `solvedRequestKey` and full solved inputs with every result. On edits, mark old output stale immediately, prevent old output from being exported under new material/process identifiers, and gate CSV/probes/charts consistently until a matching response exists. A cancelled/failed request does not make a stale result current. Export historical results only through an explicitly identified old snapshot with its original name/chemistry/time/model/database identity.

The current CALPHAD Python-off route is already labelled client screening. Prefer retire its numerical phase/Scheil prediction controls, or isolate them as an explicit instructional demonstration, never a recovery path or scientific authority. Keep “Literature solidification estimate (not CALPHAD)” separate and carry mass/microconstituent versus molar-phase definitions through tables/CSV; prohibit an unlabeled overlay/comparison of incompatible fractions.

## 8. Frozen-physics blast radius and staged work

All following are **future served changes** and require explicit implementation records. Do not exploit the current manifest omission to avoid the freeze contract.

| Stage | Owned change / affected surfaces | Identity and verification requirements |
|---|---|---|
| A: contain misleading outputs | `solidification_front.py` transformation/morphology notes; direct kinetics LSW outputs; CET gates; microstructure validity reasons; CALPHAD raw API domain gates; UI export identity. | `solidification_front.py` is in the 36-file thermal closure: planned fingerprint bump, reasons and affected thermal/parity goldens even if W/D is numerically unchanged. Nonmanifested solvers still need their own model revisions, cache invalidation and phase6a golden change ledger. Front changes can reach thermal cards, worker results, Build Job/advisories and exported/archive results. Preserve verdict authority and labels. |
| B: conservative thermodynamic chain | Scheil inventory, residual reporting, trace handling, phase multiplicities and suitability status; service/contracts/schema. | New `solidificationChainIdentity` containing solver-source closure, pycalphad version, TDB bytes, phase exclusions, input chemistry and numerical settings. Include this in result/cache/archive/export; reject old cached results as current. Update CALPHAD phase6a fixtures deliberately with a documented independent conservation oracle. No silent re-bless of old empirical fixtures. |
| C: local coupling | Co-located front samples/aggregation, shared LPBF state, correction/quarantine of legacy CFD. | Extend identity closure to actual transitive numerical files and C++ build/binary identity when used. Thermal `solidification_front.py`/shared material changes require frozen bump. Front outputs change even if geometry does not; goldens/parity must list both changed and unchanged quantities. No uncited thermal-property retuning. |
| D: optional research methods | Explicit P8 surrogate/field adapter, alloy-specific solid-state model after source/data admission. | Separate research arm IDs and compatibility gate; bounds show construction, not invented confidence. New blind protocols before any validation upgrade; validation remains unavailable meanwhile. |

Existing relevant tests: `test_solidification_front.py`, `test_lpbf_gr_solidification.py`, `test_lpbf_solidification.py`, `test_lpbf_solidification_segregation.py`, `test_lpbf_solidification_microstructure_rpc.py`, `test_module_contract_solidification_microstructure.py`, `test_module_contract_lpbf_secondary.py`, `test_calphad_honesty.py`, `test_calphad_matcalc_open.py`, `test_calphad_mc_ti.py`, `test_module_contract_calphad.py`, applicable `test_phase6a_golden.py` cases and fingerprint/parity suites. In `python/tools/lpbf_parity_check.py:1184-1201`, G12 explicitly observes morphology/PDAS/SDAS/phase note/evaluation; inspect G11 Build Job and G18 IN625 dependencies as well. Review each test's imports before running in the restricted lane; no depth-data loader/benchmark is authorised by this spec.

When a manifested served path changes, use the repository bump/reason/allowlist procedure, inspect source closure, regenerate only changed goldens with reasons, re-pin and run targeted parity. W/D outputs expected to stay unchanged must be demonstrated against the approved baseline with synthetic/frozen requests that do not read depth measurements. Registry/type/export consumers and stale-result browser checks are mandatory for contract changes. Do not run unrelated physical benchmarks merely to call a documentation or label-only change “validated”.

## 9. Predeclared acceptance gates

1. **Honesty:** every unavailable alloy/quantity has null value plus reason in API/UI/CSV; no empirical recovery, universal morphology fractions, generic priority-alloy LSW strength, or kinetic inference from liquidus cooling.
2. **Conservation:** independently reconstruct full Scheil inventories from unfiltered phase increments; residual liquid and trace approximations remain explicit. Test fixture construction must not copy the solver's renormalisation.
3. **Kinematics:** synthetic travelling and time-dependent fields satisfy the derived local identity with correct frame/sign; zero fluid flow can accompany a moving interface; compare sample-paired summaries with separate-median counterexamples.
4. **Source reproduction:** reproduce the bounded S04 PDAS/trapping and S05-S06 CET formulations/constants, dimensional units and original process scopes; masks/refusals enforced before arithmetic. Reproducing a source is not validation.
5. **Numerical convergence:** preregister temperature/space/time/phase-sampling refinement settings and tolerances appropriate to each quantity, run before interpreting physical bands, and retain failure/partial status.
6. **Identity:** any change to parent chemistry/process/state/database/phase set/settings invalidates currentness, cache and export admission; old snapshots remain explicitly old. Cross-alloy alias tests distinguish IN625 from IN718.
7. **Frozen scope:** explicit changed-path manifest, approved fingerprint/golden/parity record and unaffected-output evidence; no depth dataset use, no validation promotion from goldens or software checks.
8. **Physical validation:** a separate future blinded test with matched observable definitions, withheld data, no post-result tolerance tuning and no training/test source leakage. This gate remains **not evaluated** in this job.

## 10. Approvals and unavailable remainder

No package install is needed to implement stages A-C using the existing pycalphad 0.11.2 environment (MIT; verified installed metadata) and standard-library checks. Optional `scheil` ([author project MIT licence](https://github.com/pycalphad/scheil/blob/master/LICENSE), reconfirm at the selected pinned release) could provide an independent software implementation cross-check; installation needs maintainer approval and its miscibility-gap/phase-multiplicity limits must be respected. It is not required or installed here. No mobility, precipitation or alternate solver package is selected without an approved complete method; do not install one speculatively.

Existing MatCalc ODbL/DbCL data suffice for restricted research use; COST507's explicit use notice permits the existing local research route, while additional distribution rights need clarification. No commercial TDB is required for suppression, conservation or coupling fixes. If later selected methods need commercial Ti/Al/Ni/Fe thermodynamic and mobility databases, seek approval for the **specific** version, system/phase coverage, compatible engine, local access and licence; no redistribution. An open assessed Al-Mg-Si dataset with clear redistribution terms would remove COST507's distribution uncertainty, but must first be verified for relevant phases and chemistry.

Remaining unavailable: final Ti64 solid-state phase fractions, AlSi10Mg precipitate kinetics/strength, alloy-specific IN625/IN718 precipitation histories, 316L transformation/precipitation, quantitative Ti64/AlSi10Mg/IN625/316L CET, unsupported spacing/SDAS, robust current IN718 CALPHAD LAVES and physically coupled keyhole G/R. Reasons are missing source-bound parameters/state/history/nucleation, documented database-domain or minimizer issues, and absence of a compatible keyhole temperature field—not lack of UI controls.

Continuation: stages A-C are concrete implementation work for a new authorised lane with frozen-physics records; stage D is conditional research. This specification contains no claim that the chain is validated, calibrated for LPBF or ready for qualification.
