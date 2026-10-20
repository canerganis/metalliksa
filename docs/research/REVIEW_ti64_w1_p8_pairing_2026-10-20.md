# Ti64 W1 / P8 pairing: physics and presentation review

Date: 2026-10-20. Lane: astra. Reviewed source baseline:
`87b7b868103a4e17c1970e24912ff4b10dd92a90`.
Scope: C2 of [the standard-mode integration contract](SPEC_ti64_standard_integration_2026-10-20.md#L47),
the fixed-surface evaporative model (W1), and the existing P8 cavity/melt-depth arm.
Evidence level: repository source inspection and explicitly identified arithmetic;
no new solver results, experimental validation, calibration, or blind evaluation.

## Decision

**Do not present C2 as currently worded.** A separate comparison of research
hypotheses can be physically honest after the mapping and disclosure requirements
below are met. It is not a coupled simulation, a continuation through W1's refusal,
or a replacement prediction of the refused observable.

The decisive issue is not merely that both models lack validation. W1 refuses
geometry after a transient, scenario-dependent recoil/capillary latch; P8 uses a
different inception rule, different thermal reduction, geometry-enhanced optics,
and a loss-free conditional heat field. P8 does not solve the surface motion and
melt flow recommended by W1's refusal text. A generic **"Keyhole-mode research
depth (P8)"** row therefore suggests a physical handoff that has not been established.
P8 can also return a conduction-only linked depth below its own onset. [S1, S2, S3, S7]

The three independent review facets (W1 physics, P8 physics, and input/presentation
mapping) reached this same conclusion. This review makes no product-code changes
and does not change either model or the integration contract.

## What is shared, and what is not

| Aspect | W1 fixed-surface evaporative run | P8 cavity and melt-depth hypothesis | Consequence |
|---|---|---|---|
| Process vector | Incident power, scan speed, nominal Ti64, Gaussian diameter, preheat | Can read those same values | Equal machine inputs do not imply equal constitutive laws or onset events. |
| Domain/time | Finite single track and cooling history, finite substrate, isothermal bottom and adiabatic lateral boundaries | Moving half-space/quasi-steady constructions; no finite track or cooling history | A shorter W1 track chosen for runtime is not a shorter P8 track. |
| Heating geometry | Gaussian XY deposition with finite subsurface penetration | Gaussian surface field for the floor; surface-point plus finite uniform vertical line above onset | Same nominal beam diameter does not mean identical 3D heat deposition. |
| Thermal properties | Estimated registry interpolation, variable conductivity, enthalpy including fusion; density fixed at its interpolated preheat value | One constant solid-kernel mean K/cp/rho/alpha for onset, cavity and link | Do not call the two property models identical or copy W1's table into P8. |
| Optical power | Constant flat-surface absorptance times incident power | Flat-surface absorptance transferred to a wall proxy, then cone multiple reflections and whole-beam allocation | P8 generally uses different absorbed power once a cavity is positive. |
| Vapour properties | Gan Ti effective-species tuple | Same nominal Gan tuple for cavity inception | A real agreement; neither models alloy depletion or evolving vapour composition. |
| Losses | Evaporative, radiation/convection and bottom losses in the energy ledger | Cavity/link assume loss-free deposited absorbed power | W1's energy ledger does not close P8's heat field. |
| Onset | Accepted-history recoil excess versus capillary load; permanent latch | Gaussian dwell-derived inception power and scalar cavity balance | W1 onset does not establish P8 onset or observed keyholing. |
| Depth observable | Instantaneous liquidus cell-bound extent at the peak-melt-volume snapshot, suppressed after a latch | Deepest liquidus envelope below the original datum, with independent floor/max construction | Common original-surface datum is possible; temporal/extraction definitions still differ. |

Implementation locators: W1 [S1] lines 42–47, 80–111, 214–286, 321–345;
registry [S4] lines 103–121, 165–171; heat source [S5] lines 50–69,
166–169, 224–230; P8 [S3] lines 1008–1091 and [S7] sections 2.1–3,
especially lines 148–181. None of these hypotheses resolves a moving free surface,
recoil-driven flow, plume shielding, ejected melt, or changing alloy composition.

## Located material and optical inputs

The numbers in this section are **source-code values or repository source
attributions**, not new measurements. Original PDFs and the NIST dataset were not
reopened in this review. Their named page/equation locators are retained so the
attribution can be audited; they do not certify applicability to a new specimen.

| Quantity | Located value and provenance | Pairing implication |
|---|---|---|
| Nominal melt endpoints | Solidus 1877.15 K, liquidus 1933.15 K: [S6] lines 115–116, 396–397; [S8] lines 438–440 attributes the liquidus to Gan 2021 SI Table 1, PDF p.20. These are nominal source-model conventions, not specimen DSC. | Shared nominal liquidus is possible; matching it does not match the full enthalpy law. |
| W1 estimated table endpoints | Room row at 273.15 K: rho 4430 kg/m³, k 6.7 W/(m K), cp 526 J/(kg K); liquid row: rho 4087, k 29.8, cp 930 in those units. Values: [S6] lines 119–128; interpolation convention: [S4] lines 103–121. Liquid sources in [S6] lines 418–423: Mohr 2020 p.7 Wiedemann–Franz conductivity, section 5 p.8 Fig.4a heat capacity, Eq.21 p.5 density. The room constants are legacy conventions, not that liquid measurement. | W1 uses this estimated temperature-dependent table, not the P8 solid fits. Its density is evaluated once at preheat ([S1] line 229); it is not updated to liquid density during melting. |
| W1 latent heat and continuation | Fusion latent heat 290000 J/kg: [S6] lines 129, 404, 424; Boivineau 2006 p.520 section 5.2 Fig.8. W1 explicitly continues the endpoint cp/k above its registry table; [S1] lines 80–91, 204–211, 229–234. | Nominal P8 link does not solve fusion enthalpy or this high-temperature continuation. An enthalpy sensitivity arm is a separate scenario, not a repair of the nominal. |
| P8 solid-kernel properties | k_s(T)=0.0136 T+1.3097; cp_s(T)=0.1734 T+452.72 (SI, T in K), means over [T0,Tl]; [S6] lines 398–400, 414–417, 427–429: Gan 2021 SI Table 1 PDF p.20, Mills fits; Kirchhoff motivation Carslaw and Jaeger 1959 section 1.7. rho=4430 kg/m³ held constant; [S8] lines 430–433 attributes the room-density convention to NBS61-V Table 4(S1). alpha=K/(rho cp). | A constant-diffusivity approximation, not W1's constitutive law. At T0=353.15 K (80 °C), rounded repository pins are K=16.857, cp=650.94, alpha=5.846e-6 m²/s ([S6] line 407). Pins are descriptive source records, not a fresh runtime result. |
| Flat-surface absorptance | A0=0.32; located alternatives 0.26/0.33: [S6] lines 249–257. Source record: Simonds 2021 section 3.2, PDF p.4 Fig.3a; NIST mds2-2525 campaign summary; Ye 2019 Table 1. | Same nominal starting value. W1 keeps it fixed; P8 explicitly transfers it to a constant molten-wall proxy ([S8] lines 443–449), then changes total absorption with geometry. It is not a measured wall optical coefficient. |
| Effective Ti vapour | Tv=3560 K, Lv=9.255e6 J/kg, M=0.048 kg/mol: [S2] lines 18–39 and [S8] lines 106–108, 453–456; Gan 2021 SI Table 1 PDF p.20. W1 registry boiling endpoint is 3560.15 K, explicitly distinguished in [S1] line 211. | Nominal vapour tuples agree. Do not replace them with legacy registry Lv=8.9e6 J/kg or M=0.0459 kg/mol ([S6] lines 118, 130, 435). The small table-temperature convention difference is not the central physical mismatch. |
| Evaporation scenario | W1 reference example: transition 3560–4000 K, return fraction 0.2, ambient 101325 Pa, assumed sigma=1.65 N/m, maximum 5000 K: [S9] lines 29–36. None is an inferred default. Reference pressure 101325 Pa and Rg=8.31446261815324 J/(mol K) are conventions in [S2] lines 21–38; maximum 6000 K is a computational ceiling, not a source validity bound. | Chamber pressure, surface tension and the Hermite transition must be visible. Missing sigma is unresolved geometry, not positive onset. |
| Secondary loss coefficients | W1 emissivity 0.35 is an estimated registry convention ([S4] lines 165–171); convection and penetration default to 20 W/(m² K) and 20 µm ([S1] lines 42–45). P8 Ti surfaceBalance emissivity 0.3 is a separate preset ([S8] line 114; [S7] line 440 attributes it to Gan SI Table 1). | P8 surfaceBalance is not the cavity/link heat solver. Changing its emissivity, return/recoil or accommodation controls does not couple it to W1 ([S7] line 454). |

W1 rejects property, absorptivity, emissivity and wavelength override keys outside
its allowlist ([S1] lines 54–76). P8's nominal-equal property gate must not be
bypassed to force apparent material equality ([S3] lines 1113–1116).

## Beam and absorptivity mapping

Both models can interpret d as the **Gaussian 1/e² intensity diameter**: a=d/2,
q(r)=2 A0 P exp(-2 r²/a²)/(pi a²). This equals D4sigma for an ideal Gaussian,
not for every measured profile. W1 source: [S5] lines 50–69, 168; P8 definition:
[S3] lines 503–510 and [S7] line 123. A machine's undefined "spot size", FWHM,
sigma width, top-hat diameter, or non-Gaussian D4sigma must not be silently passed
as this d. Require the diameter convention/profile or return an explicit mapping
limitation; power is incident workpiece power, not already absorbed power.

For the P8 cone, the Gaussian fractions inside/outside a=d/2 are
1-exp(-2) and exp(-2); A_tot=(1-exp(-2))A_cav+exp(-2)A0.
These are geometric Gaussian integrals/model conventions, sourced in [S7]
lines 123–150 and implemented in [S3] lines 66–79, 126–128, 1037–1048.
W1 has no such multiple-reflection enhancement. Do not pass P8's enhanced
absorptance to W1, apply an additional absorption multiplier to P8, or subtract
W1's losses from P8 input power. Each would create a new, unreviewed coupling.

## The onset events are different

W1's high-temperature branch uses
psat=pref exp[(Lv M/Rg)(1/Tv-1/T)],
j=(1-beta) psat sqrt[M/(2 pi Rg T)], pr=(1+beta)psat/2.
Below the declared transition low, j=0 and pr=pambient; between low/high it
uses a declared monotone cubic Hermite bridge, not recovered source fit
coefficients. [S2] lines 93–114, 122–181; Gan model attribution [S9] lines 24–46.

W1 latches if any **accepted exposed state** has j>0 and
pr-pambient >= 2 sigma/a. The gate remains latched after cooling, including if
onset occurs after the stored peak-melt-volume snapshot. Active evaporation
without supplied sigma instead latches unresolvedGeometry. Neither null means
zero depth or measured cavity formation. [S2] lines 190–239; [S1] lines 239–286,
321–325. C2's onset trigger must inspect gate.onset, not merely null depth.

P8's nominal recoil-temperature threshold uses beta_r=0.2 and the atmospheric
reference convention; Tth=Tv/[1-ln(2/(1+beta_r))/c], c=Lv M/(Rg Tv).
It is the recoil-versus-reference-pressure construction of Fabbro 2020
Appendix A Eqs.A10–A11 (PDF pp.19–20), not a capillary-loaded free-surface solve.
P* is then obtained from the loss-free finite-Gaussian dwell gain (dwell a/v),
attributed to Trapp 2017 Eq.3 p.346. Capillary/hydrostatic loads and W1's
Hermite bridge are absent. Positive cavity is P>P*, with zero depression at or
below P*. [S3] lines 473–482, 537–551, 720–727; [S7] lines 137–154.

**Source-based arithmetic example, not a solver run:** for the declared W1
sigma=1.65 N/m example and d=80 µm (W1 process default, [S1] line 42), a=40 µm
and 2 sigma/a=82500 Pa. At pambient=101325 Pa its pressure gate therefore
requires pr>=183825 Pa with j>0. P8's atmospheric construction reaches its
pressure threshold at pr=101325 Pa. Equal nominal beta does not remove this
load difference, and W1's bridge prevents assuming a common temperature law.
All physical inputs here are the declared scenario in [S9] lines 29–36;
the displayed pressures/radius are direct arithmetic, not observed onset.

Consequently neither implication "W1 latched, therefore P8 is above onset" nor
"P8 is above onset, therefore W1 has latched" is established. A numerical
disagreement would be a model-model difference until independently investigated;
agreement would not establish physical accuracy.

## Depth, energy and regime boundaries

P8 cavityDepth_um is vapour-cavity depression e. It is not melt depth.
conditionalMeltDepth_um is a liquidus envelope from the conditional field;
linkedMeltDepth_um is max(conditionalMeltDepth_um, conductionDepth_um), using an
independently extracted finite-Gaussian floor. At P<=P*, e=0 and both conditional
and linked depths dispatch to that Gaussian floor; melting itself is not
guaranteed. Above onset, the point/line field is a different spatial construction.
[S3] lines 1037–1091; [S7] sections 2.2 and Amendment 3 C2.

The finite-Gaussian field below onset and singular surface-point limit above
onset do not meet continuously as e tends to zero. The max safeguard does not
fix this. An increase in Dlinked near onset may therefore be a field-shape
change rather than cavity-caused penetration. Keep the general field-shape note
and any returned FIELD_SHAPE_STEP_NEAR_ONSET warning, including band-crossing
warnings. Do not smooth, clip or reinterpret the step. [S7] lines 596–614 and
Amendment 4 D1; [S10] lines 487–492.

P8's lossMultiplier=1 and unresolvedPower_W=0 are **loss-free closure choices**,
not predictions of zero evaporation. Photon-conservative allocation also does
not establish a shared free-boundary energy/flow balance or reconcile its cavity
thermal ledger with W1. Neither the W1 evaporation loss nor P8's separate flat
surfaceBalance scalar is consumed by nominal cavity/link. [S3] lines 1037–1048;
[S7] lines 148–181, 454, 633–637. The documented contradiction of the older flat
HKL surface-balance closure must retain its own status when shown; it is not
automatically a falsification of W1's transient FV solver or P8's independent
cavity/link. It is also not evidence that either independent model is valid.

P8's hard admission rules include nominal-equal properties, IR_1064nm, flat-plate,
293.15 K<=T0<=Tl-50 K, 0.01<=Pe<=10, and a computed aspect-bound limit of 10,
with Pe=v d/(2 alpha). These numbers are **declared software/model gates**,
not measured Ti64 validity limits ([S3] lines 1109–1128). Pe<2 or an above-onset
e/d<0.5 additionally require extrapolation disclosure; the latter is outside the
thermal-cylinder source geometry. A numerically admitted tuple remains transferred
if its inputs, such as the wall-absorptance proxy, are transferred. [S7] lines
618–629; [S3] lines 788–811. Root stability is scalar mathematical selection,
not observed hydrodynamic/keyhole stability.

For typical inputs, the following already follow from the source contracts;
**the arithmetic entries do not claim that a paired solve completed**:

| Declared process/context | Source-based consequence |
|---|---|
| Ti64 60 or 150 W, 1000 mm/s | These are cases named in the standard-integration problem/A4 ([S11] lines 8–11, 82–83). W1 onset and P8 depth for them were not computed in this review. Common P/v alone cannot select the P8 regime. |
| Nominal d=80 µm, preheat=80 °C | Defaults in [S1] lines 42–45. P8 uses the mean tuple above; W1 uses interpolated preheat density and temperature-dependent registry properties. This material mismatch exists before any numerical run. |
| v=1000 mm/s, d=80 µm, preheat=80 °C | Hand arithmetic from the rounded alpha pin in [S6] line 407 gives Pe approximately 6.84, inside P8's Pe gate; it does not establish source validity or a positive cavity. |
| v=1000 mm/s, d=120 µm, preheat=80 °C | Reviewer-declared beam sensitivity; same rounded-pin arithmetic gives Pe approximately 10.3, outside P8's software gate. W1 input admissibility is not permission to bypass it. |
| v=200 mm/s, d=40 µm, preheat=80 °C | Reviewer-declared slow/small-beam sensitivity; same arithmetic gives Pe approximately 0.684, inside the numerical gate but below the Pe=2 transfer boundary. |
| Preheat=0 °C | W1's legacy input validator allows it ([S12] lines 92–98); P8's minimum is 293.15 K ([S3] line 1117). W1 acceptance can coexist with P8 unavailability. |

The P8 band is an envelope of named one-at-a-time scenarios, with interactions
unevaluated. It is not an error bar, confidence interval, or physical bound.
Likewise onset scenario frequency is not a probability of a real keyhole.
[S7] Amendment 1 A4 and Amendment 3 C3; [S10] lines 484–486.
No spent dataset was opened, fitted, scored or used to resolve these differences.

## Required input and result binding

1. Bind the paired P8 request to the **completed W1 provenance.inputs**, not the
   current editable process store or an old Build Job. Preserve full values and
   model/source identities. The current P8 path is a standalone research request,
   not a reliable assumed job.thermal.researchModels field: [S13] lines 1–24;
   [S14] lines 71–87, 629. Keep results and bands associated with that same run;
   input edits invalidate the pair.
2. Map W1 material/power_W/speed_mm_s/beamDiameter_um/preheat_C to P8
   process.material/laserPower_W/scanSpeed_mm_s/beamDiameter_um/preheatTemp_C.
   Keep incident workpiece power and beam convention explicit. P8 converts speed
   /1000, diameter /1e6 and preheat +273.15 once ([S15] lines 127–149); do not
   pre-convert UI values and then convert them again.
3. Require/disclose the compatible bare-plate, IR optical scenario. W1 has no
   wavelength request field; record that an IR material absorptance is used rather
   than claiming a measured wavelength was echoed. P8 must explicitly request
   IR_1064nm and flat-plate and retain its admission rules. The existing UI helper
   supplies a wavelength fallback and forces flat-plate ([S16] lines 31–40);
   those defaults must not conceal an unsupported original machine context.
4. Use the existing P8 property context/resolver and nominal-equal gate; retain
   its property SHA, unrounded tuple and per-input provenance ([S15] lines
   153–195). Do not copy W1 estimated properties into P8, manufacture an override,
   or use a different Build Job property snapshot to imply identity.
5. Preserve W1 transition/pressure/beta/sigma, source penetration, mesh, track,
   cooling and boundary assumptions as W1-only inputs. Preserve P8 scenario
   options and source arms as P8-only inputs. State explicitly that no W1 losses,
   temperatures or onset latch are forwarded as a P8 thermal boundary condition.
6. Select **meltDepthLink.fields.linkedMeltDepth_um** for a linked melt-depth row.
   If cavityDepth_um is also shown, label it as vapour-cavity depression. Preserve
   the selected field's null/reason, model id, observable, controlling leg,
   P/P*, nominal/arm scope, provenance, validation status, consistency note and
   returned band. An available container is not sufficient if this leaf is null.
   Do not substitute conditional depth, cavity depth or a band endpoint for it.
7. Trigger C2 on gate.onset=true. A null caused by unresolvedGeometry, failure,
   missing sigma, or absent melt is a different cause. Keep both onset decisions
   visible; do not relabel a below-onset P8 conduction envelope as keyhole mode.
8. Preserve P8-specific notes, but do not mistake its existing comparison with
   the old "served keyhole leg" for a description of W1 ([S10] lines 520–522).
   Add the W1-specific contrast below. No scoring, validation badge, relative
   accuracy claim, or "recovered depth" is justified by the pair.

## Required visible wording (English)

Preferred row title: **"P8 conditional linked melt-depth scenario (research)"**.
If a separate cavity value is shown: **"P8 vapour-cavity depression (research)"**.

Add beside W1's verbatim refusal (without changing the solver output):

> This run crossed its declared recoil/capillary criterion. The fixed-surface
> depth remains unavailable. This criterion is not an observation of a keyhole.

Add beside the P8 linked value:

> Independent quasi-steady cavity/conduction hypothesis for the same incident
> power, scan speed, Gaussian 1/e² diameter and preheat. This is not a continuation,
> correction or replacement of the evaporative result. P8 uses different thermal
> properties, absorption and onset assumptions and does not resolve surface motion
> or melt flow. Linked depth is a liquidus envelope below the original surface,
> not vapour-cavity depth. Neither model is experimentally validated.

For P8 at/below its own onset:

> P8 is at or below its own modeled onset. Any available linked depth is its
> Gaussian conduction envelope, not a keyhole-depth result.

For unavailable linked depth:

> P8 linked depth is unavailable: [returned reason code and text]. No substitute
> depth is supplied.

Retain the full returned OFAT caption, field-shape warning and model-specific
consistency/validation disclosures. In particular, preserve P8's literal
**"Not experimentally validated; research diagnostic/model only."**
([S7] Amendment 3 C4, line 633). The generic sentence "the models differ and
neither is validated" does not convey the onset, energy and observable differences
identified here. If these disclosures or the required input binding cannot be
provided, **do not show a paired numeric P8 row under the refused W1 depth**.
An independently opened research panel may still explain the hypotheses.

## Verification and limits

Fresh source/contract inspection was completed by the root and exactly three
subagents. The required ancestry check passed on the specified lane. Repository
file/line references and the final diff are checked separately in REPORT.md.

Numerical execution is **blocked**, not passed. The initial required
`C:/Users/can02/Projects/metalliksaa/Metalliksa-1/.runtime/lpbf-win-py312/Scripts/python.exe`
could not create its underlying interpreter. On continuation, the lead-authorized
fallback was attempted directly:
`C:/Users/can02/AppData/Local/Programs/Python/Python312/python.exe`, with
`PYTHONPATH=C:/Users/can02/Projects/metalliksaa/Metalliksa-1/.runtime/lpbf-win-py312/Lib/site-packages`
and `METALLIX_PYTHON` set to that base interpreter. This attempt failed before
Python started: **"Program 'python.exe' failed to run: Erişim engellendi"**
(access denied), shell exit 1. Even the runtime/package identification command
could not execute. The lead's stated runtime/package versions were therefore not
independently confirmed here. This authorized fallback was used as instructed;
no additional interpreter, copied executable or permission workaround was used.
There are still **zero executed numerical cases**. The temporary unexecuted
comparison script from the initial attempt remains removed. Graft freshness was
also unavailable under the current approval policy; direct source review was used
without a graph coverage claim. REPORT.md contains both attempts' command records.

No model runs, unit suites, parity/goldens, full-app lint/build, server/browser
checks, new original-PDF audit, dataset analysis, or runtime/band replay completed
in this review. Hand arithmetic above is deliberately limited to source-defined
pressure and Pe relations. It supplies no W1 latch, P8 onset power, melt depth,
run time, or physical-convergence result for the typical cases.

Before implementing a revised C2, execute the paired typical cases and explicit
below-onset, unresolved-sigma, P8-unavailable, leaf-null, field-shape and stale-input
cases once the prescribed interpreter or authorized fallback can actually start.
The remaining blocker is executable access, not missing authorization to use the
base interpreter. Verify that full labels/reasons/bands survive
the transport and rendering, without changing physics or tolerances. Those are
integration/numerical checks; independent experimental evidence would still be
required for any physical accuracy claim.

## Source register

All file/line locators refer to the reviewed baseline; source-model page locators
above are repository attributions, not a claim of fresh full-text verification.

[S1]: ../../python/lpbf_ti64_evaporative_solver.py "W1 solver: input, property law, source, gate and result"
[S2]: ../../python/lpbf_ti64_evaporation.py "W1 vapour law and accepted-state latch"
[S3]: ../../python/lpbf_research_arm.py "P8 physical kernels, admission, fields and status"
[S4]: ../../python/lpbf_material_registry.py "W1 estimated legacy table authority"
[S5]: ../../python/lpbf_core_physics.py "Beam deposition, domain and SI inputs"
[S6]: ../../python/four_alloy_materials.py "Shared Ti64 endpoints, optics and sourced property ledger"
[S7]: SPEC_p8_research_arm_2026-10-14.md "P8 scientific contract; Amendments 3 and 4 govern conflicts"
[S8]: ../../python/lpbf_research_manifest.py "P8 nominal state and per-input source records"
[S9]: SPEC_ti64_evaporative_cpu_2026-10-20.md "W1 source profile and declared scenarios"
[S10]: ../../python/lpbf_research_codes.py "P8 captions, reason codes and UI sentences"
[S11]: SPEC_ti64_standard_integration_2026-10-20.md "Reviewed integration contract and typical cases"
[S12]: ../../python/lpbf_simulation.py "W1 legacy process validation"
[S13]: ../../python/lpbf_research_models.py "Current standalone P8 transport"
[S14]: ../../src/components/3d-distortion-lab/IndustrialLPBFDecisionLab.tsx "Existing P8 panel host is independent of job output"
[S15]: ../../python/lpbf_research_context.py "Unrounded SI and property resolution"
[S16]: ../../src/utils/lpbfResearchPanelModel.ts "Existing panel request defaults"
