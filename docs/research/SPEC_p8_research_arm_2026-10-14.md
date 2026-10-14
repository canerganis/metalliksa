# P8: additive, unvalidated LPBF research arm

Date: 2026-10-14. Owner: Codex Astra (physics); implementer: Fable.
Base: `research/p8-research-arm`, `1400f7a984f5c164efe19cc6d1870952ea093542`.

**Decision:** publish the derived hypotheses beside the served predictor, with explicit research labels, without waiting indefinitely for blind data. This document specifies the future integration; this commit contains the specification and a reproducible O8 calculation, **not an implemented API or UI**. The maintainer authorized this scope on 2026-10-14. G2 and G3o remain **BLOCKED BY DATA**, P3 **INCONCLUSIVE**, G3 permanently blocked under its original laboratory contract, N3 NOT PASSED, N4 NOT EVALUATED. Numerical agreement below is synthetic software evidence, never experimental validation.

## 1. Boundaries and immutable records

Read alongside `CLAUDE.md`, `RULES.md`, `PROOF.md` P1/P6/P7a/P7b, and `docs/LPBF_INTEGRATION_CONSTRAINTS.md`. Lead-owned files, outside this worktree: `../Metalliksa-1/.orchestra/GOAL.md`, `PLAN_2026-10-14.md`, and `reports/{ti64,alsi10mg}_constants_sweep_2026-10-14.md`. GOAL's latest status and the present maintainer decision supersede old deadlines in PLAN; no new experiment, author contact or external publication is authorized here.

Source records read with `git show`, not checked out or modified:

| Record | Immutable revision | Locators within the revision |
|---|---|---|
| P3 cavity | `c4470b017cfe533c74b23dc5712a2df720ae00c4` (`research/p3-cavity-astra`) | `docs/research/DERIVATION_p3_keyhole_cavity_2026-10-11.md`, `PREDECLARED_p3_cavity_2026-10-11.md` Amendments 1–6 including S3k, `NOTE_p3_onset_continuity_2026-10-11.md`; `python/tools/p3_cavity_model_sketch.py`, `run_lpbf_p3_cavity.py`; Stage 0/1 record dated 2026-10-14 |
| MELT | `e91d0fbda10b9b01e974dd9838aae026e1cdd91c` (`research/ti64-primary`) | `docs/research/PREDECLARED_melt_depth_2026-10-11.md` Amendments 1–7, sections 2.3, 2.5, 11; `python/tools/run_lpbf_melt_depth.py` |
| P5 transport | `53ca5f18639629b5e221f3b643b655d33a183a3f` | branch `research/p5-transport-astra`, `docs/research/DERIVATION_p5_transport_powder_2026-10-11.md` sections 2–3 |
| P6 surface | `d553cba437c325f8da7022020945a0b3f40aaba2` | branch `research/p6-surface-astra`, `docs/research/DERIVATION_p6_surface_energy_2026-10-11.md` Amendment 1 and section 6 |

P3 sketch Git blob: `b762dc6268b82f15f9e1fe529845b5e3e9013415`; continuity-note blob: `5f5cb4edc9b8217c17607f263bb7762cd3e12fd1`; MELT runner blob: `2bff1378fc4d23d2528c6834ea096f541228906c`. These identify references; Fable must not import a mutable research branch at runtime. The registered P3 APP-solid chain (Ti64 K=6.7 W/m/K, cp=526 J/kg/K, rho=4430 kg/m3, A0=0.26) and its named S3k arm remain untouched. P8 is neither that primary chain nor a scored successor; its model identity is `p8-cavity-served-kernel-v1`.

No raw images, depth spreadsheets, forbidden target papers, measured depths or target-data runners were opened/run for this specification. Source-property composition is not a depth target. No usable fresh graph/coverage result was established; bounded source review was used without a graph-coverage claim.

## 2. Output contract and labels

Add **only** `result.researchModels` to the completed `calculate_meltpool_physics` result; Build Job exposes the same block under `job.thermal.researchModels`. Always include unavailable modules, so a null cannot disappear silently. No research output enters any old field, served tiles, contours, regime, defect flag, job verdict, process map, calibration, optimizer or qualification chain.

Every data leaf is a `ResearchField<T>` (including constants, input echoes, enums and diagnostics):

```typescript
type ResearchField<T> = {
  value: T | null;
  unit: string;                  // "1" for dimensionless, enum or string
  reasonCode: string | null;      // null iff value is available
  warnings: string[];             // explicit assumptions/extrapolations; [] otherwise
  evidenceKind: "Literature estimate";
  moduleMaturity: "Research";
  validationStatus: "not validated: no blind test passed (open data unavailable, see GOAL.md)";
  experimentalValidation: false;
  uiSentence: string;
};
type ResearchRoot = {
  depth_um: ResearchField<number>;
  aspectRatio: ResearchField<number>;
  stability: ResearchField<"stable" | "unstable" | "neutral">;
};
type ResearchComposition = {
  Al: ResearchField<number>; Si: ResearchField<number>;
  Mg: ResearchField<number>; Fe: ResearchField<number>;
};
// roots: ResearchField<ResearchRoot[]>; composition_wt_pct:
// ResearchField<ResearchComposition>. Root depth unit "um", stability "1";
// every constituent percentage unit "wt%".
```

There are no bare unlabelled numerical research leaves. Array entries inherit the same wrapper individually (root depth, aspect and stability); source locator strings are also wrapped. Containers carry the identical four evidence labels and their own `uiSentence`; structural metadata is limited to `schemaVersion`, `modelId`, `status`, `reasonCode`, `warnings` and `fields`. `warnings` is a list of reason-code strings, not a confidence score. Status is `available`, `unavailable` or `not-applicable`; `available` means numerically computed within declared software scope, never validated. Leaf-level failure can coexist with an available module and its other diagnostics. No NaN/Infinity in JSON; null is never replaced by zero. Exactly zero cavity depth below onset is a model result, not missing data.

`researchModels` has `schemaVersion="p8-research-v1"` and these five containers (no additional free-form runtime keys):

| Container / modelId | UI sentence |
|---|---|
| `keyholeCavity` / `p8-cavity-served-kernel-v1` | "Conditional cavity estimate using the served thermal properties; no blind validation." |
| `meltDepthLink` / `p8-melt-link-s2-hypothesis-v1` | "Loss-free point/line melt-depth hypothesis; no blind validation." |
| `alSi10MgIndexDisclosure` / `p8-alsi-index-disclosure-v1` | "The regime index keeps its historical absorption convention; physical absorption is different." |
| `alSi10MgVapourMgAware` / `p8-alsi-vapour-mg-sensitivity-v1` | "Ideal-mixture vapour sensitivity; extrapolated Mg pressure, no blind validation." |
| `unavailablePhysics` / `p8-unavailable-closures-v1` | "These closures need missing inputs or new physics and are not available." |

### 2.1 Input echoes and primary keyhole fields

Each keyhole input is echoed in `fields` under exactly these names: `alloy` (canonical string, 1), `power_W` (W), `speed_m_s` (m/s), `beamDiameter_m` (m), `preheat_K` (K), `liquidus_K` (K), `conductivity_W_mK` (W/m/K), `specificHeat_J_kgK` (J/kg/K), `density_kg_m3` (kg/m3), `diffusivity_m2_s` (m2/s), `wallAbsorptanceProxy` (1), `vapourTemperature_K` (K), `vapourLatentHeat_J_kg` (J/kg), `vapourMolarMass_kg_mol` (kg/mol), `propertyConvention` (1), `propertySource` (1), `vapourSource` (1). These are finite/non-null when prerequisites resolve; an unavailable prerequisite is null with its own reason. Never synthesize a missing property from another alloy.

Derived keyhole leaves: `peclet` (1), `thermalResponse_g` (1), `thresholdTemperature_K` (K), `onsetPower_W` (W), `powerOverOnset` (1), `cavityDepth_um` (um), `aspectRatio` (1), `cavityAbsorptance` (1), `totalAbsorptance` (1), `energyResidual_W` (W), `rootCount` (1), `selectedBranch` (1, exactly `lowest-strictly-stable`), `roots` (array of objects with individually wrapped `depth_um`, `aspectRatio`, `stability`, 1 for enum), `rootScanRelativeDifference` (1), `cylinderHarmonicDifference` (1). A failed cavity solve nulls depth/aspect/absorptances/selection/roots/residual but retains already-resolved inputs, Pe and onset. Do not confuse `cavityDepth_um` with served `keyholeVaporCavityDepth_um`, which is the hybrid increment over conduction, or with served `keyholeModel.fabbroDepth_um`, which is the Fabbro leg from the original surface.

Read original, unclipped served request inputs `material_name`, `laser_power_W`, `scan_speed_mm_s`, `beam_diameter_um`, `preheat_temp_C`, `laser_wavelength`, `prop_overrides`, `absorption_model`. SI conversions: speed /1000; diameter /1e6; preheat +273.15. Read the **unrounded local** tuple already returned by `resolve_conduction_kernel` and the resolved physical absorptivity; never reconstruct cp from its rounded display echo. Read resolved liquidus. Do not read normalized enthalpy/index absorptivity for this predictor. Hatch, layer, inclination, sulfur default, seed and served regime are not physical inputs to this bare half-space hypothesis. Keep them out of its equations.

### 2.2 Melt-link fields

`meltDepthLink.fields` contains only: `cavityDepth_um`, `conductionDepth_um`, `conditionalMeltDepth_um`, `linkedMeltDepth_um` (um); `controllingLeg` (1, `conduction`, `conditional-link`, `equal`); `surfacePower_W`, `cavityPower_W`, `absorbedPower_W`, `depositedThermalPower_W`, `unresolvedPower_W` (W); `cavityPowerFraction`, `lossMultiplier`, `relativeConvergenceDifference` (1); `quadratureOrder`, `xSamples` (1); `observable` (1, `deepest-below-original-datum-liquidus-envelope`); `floorModelId` (1, `eagar-tsai-v2`). Reads the request and resolved tuple in 2.1, plus keyhole e, P*, A_cav and A0. All depths are nullable; keep the energy ledger if the cavity solved but the melt envelope fails. `linkedMeltDepth_um` is null unless **both** floor and conditional envelope resolve. `unresolvedPower_W=0` and `lossMultiplier=1` denote this loss-free hypothesis, not zero real evaporation.

The floor is MELT S2's **conduction-only Eagar–Tsai depth** with the same K/cp/rho/A0/T0/Tl and input beam/speed/power. Reuse the existing Python `EagarTsaiField` plus extent search; do not use the served hybrid depth as the floor. For an Eagar–Tsai served call pass its already-computed unrounded `d_iso` only if its optical/beam/power/preheat locals exactly match the unmodified research inputs; otherwise calculate an independent research companion, never reuse clamped locals. For Rosenthal/Goldak compute the Eagar–Tsai companion without a recursive full solver call. Existing `EagarTsaiField` numerically floors r0 at 1e-7 m and v at 1e-6 m/s: below d=2e-7 m or v=1e-6 m/s, make conductionDepth/linkedMeltDepth null with `NUMERICAL_INPUT_BELOW_FLOOR`, retaining a separately admissible cavity/Dmodel diagnostic. Do not change the served guards or silently use clipped floor inputs. The nominal K/alpha tuple exceeds its internal floors (K>=1e-6 W/m/K, alpha>=1e-12 m2/s); assert that condition too. This fixed floor keeps the D(e) definition explicit across requested kernels; it does not replace the kernel selected for served output. It is a new unscored P8 chain, not a licence to call the registered S2 candidate PASSED.

### 2.3 Disclosure, sensitivity and unavailable fields

`alSi10MgIndexDisclosure.fields` has `physicalAbsorptance` (1), `indexAbsorptance` (1), `physicalToIndexRatio` (1), `decision` (1, `disclosure-only`), `classificationChanged` (1, false), `basis` (1). Read physical and index absorptivities from the same resolved property set, including existing override precedence; nominal values are 0.30 and 0.18. It is `not-applicable` with `ALLOY_NOT_ALSI10MG` for other alloys. Do not emit a reclassified regime or rescaled index diagnostic.

`alSi10MgVapourMgAware.fields` has `scenarioTemperature_K` (K), `scenarioMolarMass_kg_mol` (kg/mol), `scenarioLatentHeatLocalSlope_J_kg`, `scenarioLatentHeatTableWeighted_J_kg` (J/kg), `pureMgPressure_atm` (atm), `composition_wt_pct` (wrapped four constituent percentages, container unit wt%), `pressureRoute` (1, `hybrid`), `calculationStatus` (1, `reproduced-extrapolated-sensitivity`), `source` (1), and `dynamicVapourTemperature_K` (K). The scenario leaves are the pinned O8 **constant computational example**, not a process-dependent surface-composition predictor. For other alloys null with `ALLOY_NOT_ALSI10MG`. For Al the explicit warning `VAPOUR_PRESSURE_EXTRAPOLATED` is mandatory on every populated scenario field; the values are a sensitivity outside the Mg fit range, not an in-range vapour-pressure prediction. No Mg-aware depth is emitted in v1. The dynamic, validity-scoped field is always null with `VAPOUR_PRESSURE_OUTSIDE_SOURCE_RANGE`; thus an out-of-range scientific model is not rescued by clipping or calling its scenario a valid result.

`unavailablePhysics.fields` always includes `marangoniWidthDepthCorrection` (1), `peakTemperature_K` (K), `recoilPressure_Pa` (Pa), `powderAbsorptance` (1), `physicalKeyholeGradient_K_m` (K/m), `physicalKeyholeCoolingRate_K_s` (K/s). Every value is null. Primary reason codes and prerequisites are in section 7. Existing served interface G/cooling, loss-free maximum and opt-in powder-raytrace diagnostics keep their current contract.

## 3. Material authority and applicability

**Consistency means one thermal tuple per request:** use resolved P7b K, cp, rho, alpha=K/(rho cp), liquidus and physical A0 throughout onset, cavity and D(e). The served Fabbro leg deliberately still uses room-solid K/cp/rho and the historical index ramp; P8 does not change it. The registered P3 Ti64 K=6.7 chain and S3k remain separate research records. Do not copy their APP-solid tuple into P8 or silently mix alpha from one tuple with K from another.

P7b's material authority is reused, not reimplemented: `Kbar=integral_(T0..Tl) k_s(T)dT/(Tl-T0)` and `cpbar=integral_(T0..Tl) cp_s(T)dT/(Tl-T0)`. Ti linear forms integrate analytically; Al piecewise-linear node tables integrate segment by segment with the ledger's explicit end holds above 800.15 K for k and 773.15 K for cp. Those end holds are disclosed property extrapolations, not silent clipping of a research process input. Kirchhoff transformed conduction (Carslaw and Jaeger 1959 section 1.7) motivates the K mean; reusing a constant alpha with this mean is an approximation, exact only under the corresponding constant-diffusivity hypothesis.

Optical source locators: Ti A0=0.32 reads the P7b IR authority (Simonds 2021 Sec.3.2 Fig.3a, PDF p.4; NIST mds2-2525 pre-keyhole mean in the same campaign; Ye 2019 Table 1 Am=0.26 alternative). Al A0=0.30 reads Leis, Weber and Graf **2020**, Procedia CIRP 94 pp.173–176, Sec.3 Figs.4–6 pp.175–176, N2/1075 nm rough as-built blocks without powder. These sourced conduction absorptances become **inferred constant wall proxies**, not measured molten-wall absorption. The forbidden Leis 2021 target paper is not used. Al kernel rho=2696 kg/m3 is Akwaboa 2023 Table 3 PDF p.5, helium-pycnometer sample 100-0.2 (2.696 +/-0.005 g/cm3). The liquidus constants are the existing source-model/supplier conventions, with Al DSC uncertainty left explicit.

| Alloy | P8 v1 availability and constants |
|---|---|
| Ti-6Al-4V | Compute. P7b Kirchhoff K/cp from Gan 2021 SI Table 1, PDF p.20: k_s(T)=0.0136T+1.3097; cp_s(T)=0.1734T+452.72; means over [T0,Tl]. At 293.15 K: K=16.44854, cp=645.74021, rho=4430, alpha=5.749972908328388e-6. Vapour tuple from that table: Tv=3560 K, Lv=9.255e6 J/kg, M=0.048 kg/mol, sourced model inputs, not alloy vapour measurements. Constant room-density and constant molten-wall proxy are disclosed approximations. |
| AlSi10Mg | Compute **pure-Al-vapour proxy**. P7b sourced solid node tables, build-direction as-built convention (Yang 2018 Figs.1/4/5, Akwaboa 2023 Fig.2 and conclusion, Fetni 2024 Fig.4, recorded node locators in `PROPERTY_LEDGER`); rho=2696, Tl=868.15 K is a disclosed supplier/proxy convention, not measured alloy DSC. At 293.15 K: K=152.52434782608697, cp=1020.0826086956522, alpha=5.54605210495764e-5. Vapour: pure Al Tb=2743 K, H=284000 J/mol (Mondal 2023 Table 1 p.3), M=0.0269815384 kg/mol (CIAAW Al); Lv=H/M=10525715.613013377 J/kg. This represents a Mg-depleted Al-dominated surface hypothesis, **not measured AlSi10Mg boiling or latent heat**. Mg-inclusive scenario stays separate. |
| 316L | Null `ALLOY_CONSTANT_CHAIN_NOT_ADMITTED`. Gan SS316 vapour inputs and Ye 316L optics exist, but transferring SS316 into exact 316L and its served liquidus convention needs a separately pinned chain. Do not silently claim the existing SS316 sensitivity establishes it. |
| IN625 | Null `ALLOY_CONSTANT_CHAIN_NOT_ADMITTED`. MELT's independently recomputed Raoult tuple exists (Amendment 4); it has not been admitted as a consistent P8 tuple with the served kernel. Keep that separate record, no inheritance from Ti64. |
| IN718 / all other alloys | Null `ALLOY_CONSTANT_CHAIN_NOT_ADMITTED`; no complete P8 sourced vapour chain selected. No generic Ni/steel/Ti substitute. |

Every fixed input has a source locator or an explicitly declared approximation/proxy. This is a literature-estimate contract, not a claim that the served room-density, surface state, optical wall, liquidus proxy or every kernel node was measured for the current specimen. Ti64 4430 kg/m3 is supported for this arm by the newly checked NBS61-V Table 4(S1) room-density compilation below; using it at high temperature is still an approximation. The existing served ledger's OPEN O5/"no locator of its own" wording is not edited or relabelled by this specification. Use the exact served value, not Gan's separate 4420 density. Arbitrary thermophysical `prop_overrides`, calibrated properties and UQ perturbations are not a sourced nominal chain: null primary model outputs with `UNSOURCED_PROPERTY_OVERRIDE`. A full Build Job snapshot identical to the nominal resolved set is allowed; absorptivity-only or explicit-kernel overrides that change any physical value also fail this gate. Historical index-only override does not feed the research equations.

Software support (distinct from an empirically established physical range): finite P>=0, v>0, d>0, 293.15<=T0<=Tl-50 K, Tv>T0, K/cp/rho positive, 0<A0<1, `absorption_model=flat-plate`, existing request enum `laser_wavelength=IR_1064nm` (the authority's approximate 1064–1075 nm source convention). Do not add new accepted wavelength enums. P=0 is an evaluator-only synthetic limit: the existing served API rejects nonpositive power and must keep that behavior. Input violations produce `INVALID_INPUT`, `PREHEAT_OUTSIDE_PROPERTY_SCOPE`, `WAVELENGTH_UNSUPPORTED` or `POWDER_CONTEXT_UNSUPPORTED`; **never clamp** the raw request to the served solver's guards. Flat-plate describes the optical hypothesis; it is not metrology proving a bare polished surface. Al's measured rough as-built surface A0 is transferred into a molten wall explicitly as a proxy.

Numerical cavity range: **0.01<=Pe<=10**, including boundaries; outside: `PECLET_OUTSIDE_NUMERICAL_SCOPE`. The underlying cylinder fit 2<=Pe<=10 is distinct from the converged exact series. P/P*>=0; no paper supplies a validated universal upper ratio. For positive excess set S=(P-P*)/[d K(Tv-T0)g], R_bound=(w+pA0)S. Require R_bound<=10, giving the request-specific software ratio bound `P/P* <= 1 + 10 d K(Tv-T0)g/[(w+pA0)P*]`; outside: `ASPECT_BOUND_OUTSIDE_NUMERICAL_SCOPE`. This is a computational resource/domain policy, **not a sourced physical cutoff**. Below onset S=0 and e=0. If P*<=0 or Tth<=T0, null `ONSET_REFERENCE_UNAVAILABLE`. Pe<2 adds `LOW_PE_HYDRODYNAMICS_OMITTED`, selected R<0.5 above onset adds `LOW_ASPECT_CAVITY_MECHANICS_OMITTED`; both warn of conditional hypotheses, never validate them. There is **no experimentally established P8 physical validity range** for any alloy. D(e) inherits this scope; powder, multi-track, porosity, transient collapse, plume and qualification claims are excluded.

## 4. Exact cavity and onset equations

Notation: a=d/2 is the Gaussian 1/e2 radius (not Gaussian standard deviation); R=e/d; Pe=vd/(2alpha); p=exp(-2), w=1-p. All temperatures in K; power W; lengths m.

1. **Optics:** ideal finite conical walls x=+/-z/(2R), 0<=z<=e. Launch vertical meridional rays, reflect `u'=u-2(u dot n)n`, continue opposing-wall impacts even after an upward turn until the aperture is crossed. With integer escape count n(r,R):

   `A_cav(R)=integral_0^a r exp(-2r^2/a^2)[1-(1-A0)^n(r,R)]dr / integral_0^a r exp(-2r^2/a^2)dr`.

   `A_tot(R)=w A_cav(R)+p A0`; A_cav(0)=A0; ceiling A_tot<=w+pA0. Use the sketch's homogeneous ray trace and analytic Gaussian survival integrals, not a fitted table or averaged noninteger reflection count. This finite-cone weighted law is **our derivation** (P3 DER section 3.5), motivated by Kaplan 1994 p.1808 Eqs.22/24 and p.1809 Eqs.25–27; Kaplan's mean-count surrogate is not this exact escape law. Fabbro 2020 sections 4.1–4.2 pp.11–13 motivate the geometry dependence, not a Ti64/AlSi measurement of this law. Coherent, roughness, angle-dependent Fresnel, plasma and evolving aperture effects are absent.

2. **Thermal cylinder:** lambda=Pe/2,

   `g(Pe)=-2 pi lambda [I0(lambda)^2 K0'(lambda)/K0(lambda) + 2 sum_(n=1..N) (-1)^n In(lambda)^2 Kn'(lambda)/Kn(lambda)]`.

   Derivation: P3 DER section 4.3, separation of the moving isothermal-cylinder PDE in Fabbro 2018 Eq.4, pp.032410-2–3; heat flux and dimensional response Fabbro 2020 Eqs.1–2 pp.2–3. The Bessel series is our evaluated solution, **not an equation printed in Fabbro**. Use N=24; compare N=32, relative difference<=1e-8; `cylinderHarmonicDifference=abs(g32-g24)/abs(g32)`; integrated boundary-flux check<=1e-6 relative in tests. Failure `CYLINDER_CONVERGENCE_FAILED`. No m=5,n=3 surrogate; no Pe=0 drilling limit.

3. **Recoil threshold and onset:** c=Lv M/(R_g Tv), R_g=8.31446261815324 J/mol/K, beta_r=0.2 source scenario condensation fraction.

   `Tth=Tv / [1-ln(2/(1+beta_r))/c]`.

   Fabbro 2020 Appendix A Eqs.A10–A11 p.19 with discussion p.20: recoil `(1+beta_r)p_sat/2` exceeds ambient pressure. Use the same ambient/reference pressure (101325 Pa, source elemental Tb at one atmosphere), rather than mixing a 1-atm boiling point with a different pressure reference. The source's approximately 1e5 Pa convention is disclosed. This threshold omits capillary curvature/hydrostatic load; no invented surface-tension coefficient enters it.

   `G_T=2A0/[a K pi^(3/2)] atan(sqrt(8alpha/(v a)))` in K/W;
   `P*=(Tth-T0)/G_T`.

   Trapp 2017 Eq.3 p.346 with Gaussian convention Eq.2 p.345, evaluated at dwell t=a/v. This transfers a conduction estimate into initial recoil onset; it is not the exact moving peak or the empirical optical transition. P8 uses resolved K/alpha/A0, not the registered P3 values. Positive finite denominator and Tth are mandatory, else `ONSET_REFERENCE_UNAVAILABLE`.

4. **Cavity balance:** `K(Tv-T0)g(Pe)e = A_tot(e/d) max(P-P*,0)`.

   Fabbro 2020 Eqs.13–14 pp.7–8 motivate the shifted law; substituting whole-beam A_tot for front A_F and pairing it with the exact cylinder is an explicitly inferred P8 hypothesis. Lv/M affect onset; they are not a separate evaporation sink in this scalar balance. It is not a finite free-boundary energy/flow solution.

For P>P*: solve h(R)=R/A_tot(R)=S within [A0 S,(w+pA0)S]. Retain all resolved roots including tangent roots; determine scalar relaxation stability from h' (positive stable, negative unstable, abs(h')<1e-4 neutral), with finite-difference step 1e-6 max(1,R), one-sided at the R=0 boundary. Choose the **lowest strictly stable root** independently for each request; this is a quasi-static branch convention, not measured hysteresis/history. Use 1025 samples then 2049, plus a finer subgrid below R=4 when the full interval crosses it; detect/refine extrema (`minimize_scalar`, xatol=1e-12) to detect tangent roots lacking sign changes. Bisection atol=1e-12 in R, rtol=1e-11, maxiter=80; root deduplication 1e-7 max(1,R). Root count must agree across scans, every matched R within 1e-7 max(1,R), and selected power residual <=1e-6 max(1,P) W. Define `rootScanRelativeDifference=max_i abs(R2049_i-R1025_i)/max(1,abs(R2049_i))`. Failures: `CAVITY_ROOT_SCAN_UNRESOLVED`, `CAVITY_RESIDUAL_FAILED`, `NO_STRICTLY_STABLE_ROOT`, `NONFINITE_RESULT`. Refinement agreement is not an all-root proof. Ray cap=10000 impacts; exhaustion `OPTICAL_TRACE_UNRESOLVED`. No smoothing of real optical folds and no fallback root.

For P<=P*, do not run a positive-depth root scan: cavityDepth=0, aspectRatio=0, A_cav=A_tot=A0, energyResidual=0, rootCount=0 and wrapped roots=[]. `selectedBranch` and `rootScanRelativeDifference` are null with `NOT_APPLICABLE_BELOW_ONSET`; onset/Pe/g remain available when their prerequisites resolve. The sketch's artificial zero-root entry is not exposed as a resolved positive-cavity root in the new contract.

## 5. Onset continuity and D(e): research only

The **postprocessor allocation**, not P3 e or its onset equation, is corrected. Let B=A0 P*:

```text
P<=P*: Qs=A0 P; Qc=0; Qabs=A0 P.
P>P*:  Qs=A0(p P+w P*);
       Qc=w[A_cav(R) P-A0 P*];
       Qabs=A_tot(R)P=Qs+Qc.
Qnet=Qabs; chi=Qc/Qnet (0 when Qnet=0); eta=1 on both sides.
```

This is the NOTE section 6 / MELT Amendment 1 conservative spatial hypothesis, **not a published universal allocation law**. It fixes both complementary powers; merely removing the old Qs surplus leaves `w(A0-A_cav)P*` missing. At inception e->0, A_cav->A0, Qs->B, Qc->0, Qnet->B. Photon identity holds at any depth; no old 13.5335% surplus or 63.1016% downward whole-source step remains. Physical evaporation/transported melt enthalpy are omitted, not estimated as zero. Fabbro Appendix A Eqs.A3–A8 pp.18–19 and section 3.3 computed conduction shares 0.30–0.35 are local energy channels, not a universal 0.325 multiplier on the entire thermal field.

At y=0 and z>e, define beta=v/(2alpha), r0=sqrt(x^2+y^2+z^2), r±=sqrt(x^2+y^2+(z±s)^2):

```text
Theta(x,y,z) = Qs exp[-beta(x+r0)]/(2 pi K r0)
 + Qc/(4 pi K e) integral_0^e {
       exp[-beta(x+r-)]/r- + exp[-beta(x+r+)]/r+
   } ds.
Dmodel = sup{z: max_x Theta(x,0,z) >= Tl-T0}.
Dlinked = max(d_iso_ET, Dmodel).
```

For e=0 omit the line and use the surface Rosenthal point with Qs=Qabs. There is no division by zero. Uniform finite vertical line + Neumann image + a surface point is **our finite-domain derivation** (P3 DER section 6.2); Kaplan 1994 p.1805 superposition and Eq.1 p.1806 concern an infinite moving line, not this exact equation. Fabbro 2020 section 2.1 p.2 supplies uniform cylinder-wall conductive-power motivation. Rai 2007 Eqs.4–6,11 pp.5757–5758 identify omitted flow/enthalpy physics. Do not call this an etched-depth law validated by those papers.

Eagar–Tsai floor: use existing `eagar-tsai-v2` unchanged, with sigma=d/4 and P_eff=A0 P. For completeness its derived SI-converted integral is

`DeltaT=P_eff/[2pi sqrt(2pi)K sigma] integral_0^infty tau^(-1/2)/(1+tau) exp(-[(X+U tau)^2+Y^2]/[2(1+tau)]-Z^2/[2tau]) d tau`,

where X=x/sigma,Y=y/sigma,Z=z/sigma,U=v sigma/(2alpha),tau=2alpha t/sigma^2. Eagar and Tsai 1983, Welding Journal 62, Gaussian Eq.6 and moving dimensional solution Eq.10 on p.347-s (PDF p.2), travelling Gaussian superposition; exact implementation and quadrature are `python/eagar_tsai_solver.py` (the normalization above is the repository conversion of Eq.10, not a verbatim numbered paper equation). Reuse its composite 16/8-point Gauss–Legendre panels and existing extent helper; do not add a second UI field solver. The pure point/line envelope at e=0 need not equal the finite-Gaussian floor; the max operation is an explicit S2 safeguard, not evidence that Dmodel>=d_iso follows from Dmodel>=e.

Dmodel numerical method: L=Qnet/[2piK(Tl-T0)]; z bracket [nextafter(e,+inf),e+L] when e>0, [L*1e-12,L] for e=0; P=0 returns exactly zero depths/energy without a root search. Combine real/image line into t in [z-e,z+e], use log(t) Gauss–Legendre order 32. Search trailing x in [-L,0] with 65 quadratic-grid points `x_j=-L[1-j/(n-1)]^2`; include endpoints as candidates and refine **every detected interior local maximum**, bounded xatol=max(1e-14 m,L*1e-9), maxiter=80. Outer depth bisection atol=1e-10 m, rtol=1e-9, maxiter=80. Repeat with order 64 /129 x samples; publish this refined depth only if `relativeConvergenceDifference=abs(D64_129-D32_65)/max(abs(D64_129),1e-12 m)` <=0.01. This is a computational acceptance policy, not an uncertainty band or scientific tolerance. The uniform-line tip is logarithmically singular; unresolved thin shells produce null `TIP_SHELL_UNRESOLVED`, not D=e.

Other failure codes: `MELT_LINK_NOT_AVAILABLE` (upstream cavity null), `CONDUCTION_EXTENT_UNRESOLVED`, `MELT_BRACKET_FAILURE`, `MELT_OPTIMIZER_FAILURE`, `MELT_CONVERGENCE_FAILED`, `NONFINITE_RESULT`. Keep Dmodel if only floor fails, but Dlinked stays null. Physical range and omitted terms are exactly section 3. No empirical error bar, measured-depth fit or calibration is supplied.

## 6. AlSi10Mg OI-7 decision and O8 closure

**OI-7 / PLAN step 25: disclosure only.** Physical absorption 0.30 versus historical index 0.18 gives a ratio 5/3; P7b intentionally separated them. Its frozen 15/20 cuts and 15→30 Fabbro ramp use the historical room-property convention; these are transferred screening rules, not a newly derived AlSi10Mg boundary. Changing the index to physical A without rescaling/re-deriving the cuts changes classifications. Multiplying every cutoff and the ramp by 5/3 could algebraically preserve this single-alloy classification only if every reader/property convention/override follows the same transformation; it would be a separate served bump, not a P8 fix. This spec changes neither index, cuts, ramp nor labels. UI states the convention difference and the conditional research P* without calling either a validated onset. No low-Pe change to the served S1/Fabbro leg is authorized.

**O8: computational sourcing/reproducibility closed; alloy material validity unresolved.** Run the committed standard-library script `docs/research/scripts/alsi10mg_vapour_o8.py`; output `alsi10mg_vapour_o8.json` is intentionally committed per the maintainer request. No solver or target dataset is imported.

Element pressures: Mondal 2023 Eq.1 p.2, Eq.2 p.4, Tables 1 p.3 and 2 p.7. Feedstock composition Al 89.67, Si 9.75, Mg 0.44, Fe 0.14 wt%: Liu & Gibbons SFF 2023 Table 1, printed p.341 / PDF p.3. This is source composition, not measured depth and not known instantaneous surface chemistry. Other trace constituents are unreported/omitted, not declared measured zeros. CIAAW atomic masses are pinned in the script.

```text
xi=(wi/Mi)/sum_j(wj/Mj).
CC: pi/atm=exp[(Hi/Rg)(1/Tbi-1/T)].
Fit: log10(pi/atm)=-Ai/T+Bi+Ci log10(T)+1e-3 Di T.
Solve sum_i xi pi(T)=1 atm; yi=xi pi/sum_j xj pj.
Mv=sum_i yi Mi; Htable=sum_i yi Hi.
Hlocal=sum_i yi Rg T^2 d ln(pi)/dT; Llocal=Hlocal/Mv.
```

Hybrid: Al/Si/Fe Table 2 fits within their printed ranges; Mg uses **explicit constant-H CC extrapolation**, never its polynomial above 1730 K. Fit coefficients and individual ranges are in JSON. Bisection [1800,3000] K, atol=1e-9 K, maxiter=80; one-atmosphere pressure residual<1e-10. An independent all-CC route, mass/mole/energy identities, source-range flags and synthetic composition sensitivities are included.

| Scenario | Tv K | M kg/mol | L J/kg | Interpretation |
|---|---:|---:|---:|---|
| Nominal hybrid Mg-inclusive | 2477.605213 | 0.024889589 | 6823019.625 (local slope) | Reproduced extrapolated scenario, research only |
| Independent all-CC | 2471.728504 | 0.024921288 | 6700437.224 (tabulated enthalpy) | Assumption sensitivity, not independent experiment |
| Earlier rounded proposal | 2480 | 0.025 | 6800000 | Matches hybrid to about 0.1% /0.44% /0.34%, not a distinct measured triple |
| Primary P8 pure-Al proxy | 2743 | 0.0269815384 | 10525715.613013377 | Sourced elemental model for a Mg-depleted surface, explicitly transferred |

At the mixture crossing, pure Mg pressure exceeds 150 atm, outside Mondal's 600–1730 K Mg fit and its synthesized-pressure ceiling of 10 atm. Ideal activities, equilibrium monatomic vapour and no preferential depletion are strong hypotheses. Hybrid local-slope H is not the same as weighted tabulated latent enthalpy; never interchange them silently. These differences explain why the earlier uncommitted calculation is a scenario, not a served material identity.

**The Mg-aware triple becomes an arm only, never served.** The existing served Al tuple (2743.15 K, 1.05e7 J/kg, 0.027 kg/mol) remains byte-for-byte unchanged; P8's sourced pure-Al tuple also stays only inside its block. The O8 result does not grant registered MELT S2 eligibility, replace the required independent Opus recomputation before any freeze, amend any registration, or remove G2/G3o's data blocker. Dynamic Mg vapour inference remains unavailable outside source range, as specified in 2.3.

## 7. Explicitly unavailable physics

| Field / primary reason | Why / what would be needed | Source locator |
|---|---|---|
| `marangoniWidthDepthCorrection`: `MARANGONI_SURFACE_CHEMISTRY_UNAVAILABLE` | Need actual soluble S and O, not the default sulfur value, nominal grade or oxygen bound in oxide. Even with chemistry, no coefficient-free W/D closure was obtained (`MARANGONI_TRANSPORT_CLOSURE_UNAVAILABLE`); velocity scaling does not provide u(x), return flow or the low-Pr thermal boundary layer. No guessed transport multiplier. | P5 DER sections 2.3–2.4; Mills 2006 pp.630–631 sections 11.2–11.4 Eqs.25–29; Mills 316 chapter p.139 Eq.5 has its own sulfur convention; its 35.7 ppm crossover is correlation-specific. |
| `peakTemperature_K`, `recoilPressure_Pa`: `SURFACE_BALANCE_CLOSURE_FALSIFIED` | P6's flat non-receding HKL scalar balance was falsified, not merely data blocked. Source vapour constants do not repair missing wall inclination, ejection/convection, flux-to-area allocation and global energy balance. Reject those scalar numbers as an arm. Requires a coupled local wall/energy/flow closure; same Ts/beta for recoil and losses. | P6 Amendment 1(1), section 6; Semak–Matsunawa 1997 pp.2547–2548; Fabbro 2020 Eq.8 and Appendix A. |
| `powderAbsorptance`: `POWDER_ALLOY_OPTICAL_CONSTANTS_UNAVAILABLE` | Need grade/wavelength/T/state-specific n+i kappa, lot D32, porosity phi, layer H and substrate boundary (`POWDER_LOT_INPUTS_UNAVAILABLE`); also a declared deposited-power operator (`POWDER_THERMAL_OPERATOR_UNAVAILABLE`). Boley elemental Ti/Al or generic steel values must not silently become alloy optics. | P5 DER sections 3.1–3.5; Boley 2015 p.2478 Eqs.1–2/Table 1, Tables 1–2 continuum/ray comparisons; Gusarov 2005 p.3426 Eqs.14,20–22, Fig.7 p.3432; Gusarov 2007 p.977. |
| `physicalKeyholeGradient_K_m`, `physicalKeyholeCoolingRate_K_s`: `KEYHOLE_THERMAL_FLOW_CLOSURE_UNAVAILABLE` | The loss-free liquidus/interface diagnostic is not a solved physical cavity G or cooling rate; requires the coupled finite thermal/flow boundary. | P6 section 6; MELT scope limitations. |

Powder extinction derivation `beta=3(1-phi)/(2phi D32)` remains a sourced continuum hypothesis; the measured approximately 3.4x discrepancy is a disclosure, not a universal multiplier. Mathematical conservation does not validate absorptance. Existing opt-in GPU powder-raytrace path is a separate served feature; P8 neither removes nor promotes it. Existing loss-free Gaussian maximum below its sourced Tv remains a separate served diagnostic, not the unavailable physical surface-balance peak.

## 8. Fable implementation plan and acceptance gates

Goal: append the research report, preserving every pre-existing thermal output and every decision. Python remains the sole scientific authority; TypeScript renders backend values and labels only. No new dependency; NumPy/SciPy already support the sketch methods. Root integration owns the shared schema, solver hook and manifest. Physics approval is this contract, not an instruction to tune after results.

- [ ] **Synthetic contract tests first:** create `python/test_lpbf_research_arm.py` for sections 2–7 and numerical literals below; add `tests/lpbf-research-model-panel.test.tsx` for English separate panel, n/a/reason, exact labels and stale-result handling. Test P=0, P*±small epsilon, negative/nonfinite inputs, unsupported alloy/IR override, property snapshot equivalence, preheat just outside scope, Pe=0.01/10 and just outside, root cap/no stable root, failed envelope/floor and all unavailability codes. No measured-data import or registered runner invocation.
- [ ] **One Python evaluator:** create `python/lpbf_research_arm.py`, function `evaluate_research_models(request, resolved_context) -> dict`, with immutable sourced constants and source locators defined by this document. Consume a copied/read-only resolved context containing unrounded K/cp/rho/alpha/A0/Tl and, if available, ET d_iso. Port the pinned sketch methods with tests, corrected section 5 allocation, and exact reason codes. Do not import papers, branch artifacts or JSON measured-depth catalogs. O8 constants come from this committed sourcing record; they cannot alter `four_alloy_materials.py`.
- [ ] **Append after served computation:** modify `python/lpbf_thermal_solver.py` just before its final return, after `materialEvidence` assembly. Preserve all old calculations and result dictionaries; set only `result['researchModels']`. Catch declared helper-local numerical/domain exceptions and emit their explicit reason; an unexpected research-evaluator failure emits `RESEARCH_EVALUATION_FAILED` plus a server-side diagnostic, never silently a plausible number and never changing/aborting a valid served result. Do not wrap the served solver in that catch. Invalid original request scope is checked before using any clamped served locals. No full recursive `calculate_meltpool_physics` call. Existing `lpbf_build_job_solver.py` forwards thermal wholesale and `compose_verdict` reads old blocks, so no scoring edit is required. `routes/physics.ts` already forwards the Python payload; do not create a second API predictor.
- [ ] **Typed transport and panel:** add optional `researchModels` to `PythonLPBFResult` in `src/services/pythonComputationService.ts` for backward-compatible old payload reads; define the closed field/module schemas above. Add `src/components/3d-distortion-lab/ResearchModelPanel.tsx`, placed after served notices in `IndustrialLPBFDecisionLab.tsx` (reads `job.thermal.researchModels`) and separately before Solidification in `MeltPool3DCrossSectionLab.tsx` (reads result block). Header exactly **Research model**; show the four evidence labels, short sentence, source and explicit n/a reason. Do not mix values into served metric tiles. Reuse current request/result identity and pending state; hide stale results when inputs change. Use no duplicate process store, UI equation evaluation, re-scoring or conditional green approval colour.
- [ ] **Additive-output frozen bump:** solver hook touches a frozen manifest file, therefore the global implementation fingerprint necessarily changes even though old physical numbers do not. Add the research evaluator intentionally to `IMPLEMENTATION_SOURCE_FILES` in `python/lpbf_simulation.py`, manifest count 36→37; update `python/test_phase6a_leaf_modules.py` and related exact manifest guards, and pin the reviewed planned bump. Current fingerprint is `36cd9d4a96c9726ab2ff4f3030b442f862d96f9ebdc3f724cc6dd85f55110348`. Follow the existing Opus gate, bump record/reasons, fingerprint-pin/golden workflow and maintainer Ceiling-Review trailer procedure for guarded paths. This spec commit itself changes **no** frozen file/pin/golden. Do not forge the maintainer trailer or push.
- [ ] **Parity before goldens:** synthetic snapshots against immutable base `1400f7a9`, five alloys x three served kernels, default/full-snapshot and supported/unsupported research inputs, 49-cell classification grids. Remove only `researchModels` from old thermal payloads, and only known volatile compute-time metadata for comparison; compare all remaining values, labels, classification/nulls and floats exactly (canonical representation and float.hex), with no numerical tolerance. Confirm `job.verdict`, material/input hashes and all old honesty observations are equal. Baseline capture must not open target data. Fingerprint provenance is the separately declared identity consequence of the additive bump, not a changed physical result.
- [ ] **Parity-tool policy:** `python/tools/lpbf_parity_check.py:evaluate_drift` handles a first-appearance ordinary observation by a matching allowlist entry; protected reference/identity first appearances require the **exact key**, never a glob or whole-case relaxation. New honesty observations (including `*.validationStatus`/`*.experimentalValidation`) are rejected even if named exactly. Therefore do not add research honesty leaves as drift-allowlisted observations; assert their new response contract in self-contained tests. **No existing honesty key is touched, renamed, removed or allowed to drift.** New ordinary research observations, if added, get exact per-key first-appearance entries. Existing whole-result digests change merely because the block is appended: exact candidate entries `g11_build_job_meltpool:meltpool.{0,1,2}.{typedSha256,canonicalSha256}` and `g18_in625_latent_heat:meltpool.in625`, expanded to actual keys, never wildcard allowances. Inspect actual observation diff, permit only block-induced digests and declared implementation-identity metadata; do not copy P7b's broad 516-entry list. First-appearance permission is not scientific validation. If another affected case appears, enumerate/justify it before recording, rather than assuming this list is exhaustive.
- [ ] **Frozen calibration assertions:** in `python/test_lpbf_calibration_frozen.py`, project out only the additive `researchModels` before comparing the prior `HTTP_GOLDEN` payload hashes; keep the old physical/label pins and add the independent exact comparison above. Do not re-fit a calibration or loosen frozen numeric/honesty observations. Its frozen-file-diff branch guard is expected to fail on a bump branch until merge; report that limitation, not all-green status.
- [ ] **Checks/rollout:** run `python -I docs/research/scripts/alsi10mg_vapour_o8.py --check`, `python -B -m unittest discover -s python -p test_lpbf_research_arm.py`, relevant fingerprint/contract/served tests, `npm run lint`, focused panel tests, and synthetic old-output parity before any golden recording. After the reviewed bump, run the existing parity suite `python python/tools/lpbf_parity_check.py --check --slow` and relevant full project checks under its original protected rules; report unavailable environments/skips. Future parity suite execution is Fable's integration gate, not an executed data experiment in this specification session. Restart all `lpbf_worker.py` workers at rollout to clear in-process job cache: keep `BUILD_JOB_SOLVER_REVISION` v25 and old job/input/material identities unchanged for this additive block. Do not invent identity drift to compensate for a gratuitous revision bump. Verify both panels in browser, including changed-input stale state; review explicit-path commit, local only, then hand the concrete review/trailer scope to the maintainer.

**Parity statement:** pre-existing thermal result fields and served classification must be bit-identical to `1400f7a9`, except the newly appended `researchModels` block (and naturally volatile elapsed time). The necessary global implementation fingerprint and whole-result digests change as declared metadata; claiming the entire global API/provenance payload, including that fingerprint, is bit-identical would be false. No material ledger, absorption authority, served vapour tuple, honesty value or Build Job scoring is changed. A failure of old-field equality rejects the implementation; a numerical tolerance or golden regeneration cannot repair it.

## 9. Synthetic comparison and pinned tests

**Synthetic inputs only; no measured depths, fitted values or accuracy scores.** P=100/200/400 W, v=800 mm/s, d=80 um D4sigma, T0=20 C, IR flat-plate; default hatch/layer affect served diagnostics only. Served column is the frozen Eagar–Tsai request at `1400f7a9`; keyhole is **`keyholeModel.fabbroDepth_um`**, not its increment over conduction. Research uses sections 3–5, with Gan Ti vapour or exact Mondal pure-Al proxy, exact cylinder and conservative eta=1. Floor is the conduction-only ET extent. Values displayed here are rounded to 0.001 um; tests pin unrounded literals. These separations show the size of the hypothesis change, not which predictor is correct.

| Alloy | P W | Served keyhole um | Research cavity um | Served melt um | Research linked melt um |
|---|---:|---:|---:|---:|---:|
| Ti-6Al-4V | 100 | 0.0 | 43.770 | 36.7 | 61.267 |
| Ti-6Al-4V | 200 | 78.3 | 161.878 | 78.3 | 177.532 |
| Ti-6Al-4V | 400 | 196.8 | 378.516 | 196.8 | 393.599 |
| AlSi10Mg | 100 | 0.0 | 0.000 | 33.7 | 41.752 |
| AlSi10Mg | 200 | 0.0 | 17.905 | 66.6 | 71.888 |
| AlSi10Mg | 400 | 14.3 | 155.840 | 113.1 | 242.232 |

Below-onset Al's point-source Dmodel can exceed the finite-Gaussian floor; that is explicitly part of the conditional S2 definition, not a cavity when e=0. Al Pe=0.5769870061515482 is outside the linear Fabbro fit and carries the low-Pe omitted-physics warning, although the exact cylinder is numerically converged. Ti Pe=5.565243612478677, g=16.813989417694728, P*=22.177084176202413 W, Tth=3685.4377563347753 K. Al g=3.986663719774884 and P*=111.09125989376915 W. New P* may be very different from the historical index ramp; neither changes classification.

Pin e (um), Dmodel (um) in order P=100/200/400:

```text
Ti e = [43.76964260476196, 161.878167801, 378.516484610]
Ti D = [61.267015829582455, 177.532102554, 393.598706500]
Al e = [0.0, 17.9051282497, 155.8400293565]
Al D = [41.7515235684, 71.8881146417, 242.2317369192]
```

Absolute test tolerance 0.002 um for sketch depth pins (solver root atol and existing floor discretization); onset 1e-6 W; Pe and g 1e-8 relative. These are self-contained numerical checks, not blind-test criteria. Use literals, not expectations generated by the function under test. Research depth primary publish precision remains full finite double; UI can round and must not imply measurement precision.

Required additional tests: A_cav(R=0)=A0, R=.5/1/2 gives two/three/six impacts; at A0=.32, A_cav(.5)=.5376 and A_cav(1)=.685568. Whole-beam Gaussian ceiling <=w+pA0. At fixed e and positive P excess energy residual bound as section 4; identity Qs+Qc=A_tot P to 1e-6 relative and nonnegative allocation. Synthetic epsilon sequence P*/2, P*, P*(1±1e-8) verifies the continuous source limit and zero below-onset cavity without asserting absence of later folds. For Ti100 W pin Qs=10.466966570084843 W, Qc=40.34813766668647 W, Qabs=50.81510423677131 W and chi=0.7940185949178741. Test multiple-root/tangent fixtures from the pinned sketch with constant synthetic A0, preserving root-count and lowest-stable selection; no hydrodynamic stability claim.

Repeat all six Dmodel fixtures at 32/65 and 64/129; the independent run for this specification returned equal serialized depths at these points and cavity residuals below 1e-6 W. This local numerical agreement says nothing about experimental melt depth. O8 tests pin the independent all-CC result and check local pressure derivatives, mole normalization, H=LM, monotonic root bracket, no-nonfinite JSON and exact committed-output replay. Comparison generation is reproducible by loading the pinned P3 sketch via `git show` into a temporary file, calling `resolve_conduction_kernel` and `calculate_meltpool_physics(...heat_source='eagar-tsai',include_process_map=False)`, then `onset_power`, `solve_e(...closure='cylinder_exact')`, the section 5 partition and `melt_depth_from_e(...observable='envelope',order=64,x_samples=129)`; do **not** call the sketch's legacy `energy_partition` or data-mode runners.

## 10. Source index and continuation

- Fabbro 2020, *Depth Dependence and Keyhole Stability at Threshold, for Different Laser Welding Regimes*, DOI [10.3390/app10041487](https://doi.org/10.3390/app10041487): Eqs.1–2 pp.2–3, Eqs.13–14 pp.7–8, section 4.2 pp.12–13, Appendix A pp.18–20 (A10–A11 p.19, discussion p.20). Page labels are PDF pages.
- Fabbro 2018, *Scaling laws for the laser welding process in keyhole mode*, DOI [10.2351/1.5040624](https://doi.org/10.2351/1.5040624): Eqs.3–6 pp.032410-2–3, phase-change addition Eq.10 p.032410-4.
- Trapp et al. 2017, DOI [10.1016/j.apmt.2017.08.006](https://doi.org/10.1016/j.apmt.2017.08.006): Gaussian Eq.2 p.345, transient flat conduction Eq.3 p.346; these are source-model locators, no measured depths used.
- Kaplan 1994, *A model of deep penetration laser welding based on calculation of the keyhole profile*, DOI [10.1088/0022-3727/27/9/002](https://doi.org/10.1088/0022-3727/27/9/002): pp.1805–1809, Eq.1 infinite line, Eqs.22/24–27 optical reflections; finite cone/line transfers are identified above as derived.
- Gan et al. 2021, *Universal scaling laws of keyhole stability and porosity in 3D printing of metals*, DOI [10.1038/s41467-021-22704-0](https://doi.org/10.1038/s41467-021-22704-0), SI Table 1 PDF p.20: Ti alloy model/property inputs only, no depth targets.
- Mondal et al. 2023, DOI [10.3390/ma16010050](https://doi.org/10.3390/ma16010050), Eq.1 p.2, Eq.2 p.4, Tables 1/2 pp.3/7; [CIAAW aluminium](https://ciaaw.org/aluminium.htm), [2024 abridged masses](https://ciaaw.org/abridged-atomic-weights.htm); [Liu & Gibbons 2023 original SFF paper](https://utw10945.utweb.utexas.edu/sites/default/files/2023/027%20ControllingChemicalCompositionChangesinLaserPowderBedFusionofAlSi10Mg.pdf), composition Table 1 printed p.341/PDF p.3, source locator retained in O8 JSON.
- Ledbetter, NBS NSRDS61 Part V, [original NBS density compilation](https://srd.nist.gov/NSRDS/NSRDS-NBS-61-V.pdf), Table 4(S1) printed p.11 / PDF p.15: Ti-6Al-4V density mean and median 4.43 g/cm3 from seven observations, standard deviation 0.01 g/cm3; reviewed visually. Supports the constant room-density choice, not a high-temperature density law or material certification.
- Eagar and Tsai 1983, *Temperature Fields Produced by Traveling Distributed Heat Sources*, Welding Journal 62 pp.346-s–354-s, Eqs.6/10 p.347-s / PDF p.2, local source `C:/Users/can02/Projects/metalliksaa/papers/eagar1983.pdf`; only the derivation pages were inspected.
- Semak–Matsunawa 1997, DOI [10.1088/0022-3727/30/18/008](https://doi.org/10.1088/0022-3727/30/18/008), pp.2544–2548; Rai et al. 2007, DOI [10.1088/0022-3727/40/18/037](https://doi.org/10.1088/0022-3727/40/18/037), pp.5757–5758. They bound omitted physics, not validation of P8.

Continuation for Fable: implement section 8 after review of this specification; keep data blocks closed and all source registrations frozen. No maintainer question is needed for the proposed label wording. A new untouched, metrologically eligible open release would permit a separate registered blind test; none was manufactured by serving this arm.
