# SOL-C A6: morphology, CET and phase models

Research specification, 2026-10-16. No served implementation is changed. The new maintainer rule admits an explicitly transferred physics model at Tier 2. This replaces A5's blanket missing-model conclusion for the routes below, while retaining its physics gates. These models have no independent specimen validation.

## Morphology and CET: all five alloys

Two different observables are computed at every co-located, cooling-side G,R tuple. The constitutional-supercooling index `chi = P R/(D G)`, with `Q = abs(m) C0 (1-k)` and `P = Q/k`, tests the linear, diffusion-controlled planar stability limit. `chi <= 1` is the planar-stability side; `chi > 1` allows instability. It cannot distinguish cells from dendrites, nor determine columnar versus equiaxed grains. Its dimensional inputs are m in K/(wt percent), C0 in wt percent, D in m2/s, G in K/m and R in m/s. No generic G/R cut is used.

For grain morphology use a separate Hunt mechanical-blocking model:

```
deltaTc = sqrt(8 Q Gamma R / D)
r = deltaTc/(3 G) * (1 - (deltaTn/deltaTc)^3), if deltaTc > deltaTn
r = 0, otherwise
phiExtended = (4*pi/3) N0 r^3
fEquiaxedEnvelope = 1 - exp(-phiExtended)
```

Gamma is in K m, deltaTn in K, N0 in m-3, r in m. `fEquiaxedEnvelope` is the model's fraction of space occupied by equiaxed dendritic grain envelopes, including their interdendritic liquid. It is neither a solid fraction nor a measured grain fraction. The `r=0` branch is absence of activation, not a clamp of an invalid negative radius. Model classes use true envelope fraction `f <= 0.0049: columnar`, `f >= 0.49: equiaxed`, otherwise `mixed`. These source conventions are not universal morphology thresholds. Do not apply the extended-fraction 0.0066/0.66 thresholds to f.

Source equations: [Mishra et al., Additive Manufacturing 70 (2023), 103802](https://doi.org/10.1016/j.addma.2023.103802), section 2.1, equations 2,3,4,7,8 and the paragraph after equation 9. This primary study gives the radius integration, exponential impingement correction and true-fraction class conventions. [Brooke et al., Nature Communications 16 (2025), 5710](https://doi.org/10.1038/s41467-025-60162-0), equations 1,2 and 6, supplies P,Q and the solutal Hunt tip-undercooling law. Source retrieval was publisher full-text search extraction; the direct Mishra DOI fetch failed. Original Hunt 1984 is not newly claimed read.

### Fixed source parameters and explicit transfers

| Requested alloy | C0, k, abs(m), D, Gamma | Primary locator and transfer |
|---|---|---|
| Ti64 | 10; 0.838; **derived 50*0.838/(10*(1-0.838)) = 25.86419753**; 9.5e-9; 2.2e-7 | [Ghosh et al. 2018](https://arxiv.org/html/1809.01056), Table 6. Explicit **freezing-range-closed Ti-10 wt percent X surrogate**: source P=50 K, k,C0,D,Gamma; derive effective m by binary closure. The same source prints abs(m)=0.088, which instead implies P about 0.17 K and is incompatible. This route does not claim to correct the source slope; it selects a disclosed coherent surrogate. The 50 K is the source binary model's freezing range, not the thermal registry solidus/liquidus interval. Thermal undercooling and full Al/V partitioning remain omitted. |
| AlSi10Mg | actual Si wt percent, default 10; 0.13; 6.5; 3e-9; 9e-8 | [Azizi et al. 2020](https://arxiv.org/html/2003.09757v1), Table 2 and section I assumptions: source phase-field chemistry is Al-0.5Si, not Al-10Si. Reusing its constant coefficients at actual Si is an explicit Al-Si family transfer beyond the dilute source composition. Magnesium, minor elements and eutectic competition are omitted. Table 2 prints positive liquidus-slope magnitude, used with the physical negative liquidus slope. |
| IN718 | actual Nb wt percent, default 5; 0.48; 10.5; 3e-9; 3.65e-7 | [Ghosh et al. 2017](https://arxiv.org/html/1705.06669), Table 2. Ni-5Nb binary to multicomponent IN718 family transfer. |
| IN625 | actual Nb wt percent, default 5 only when explicitly selecting the Ni-5Nb proxy | Same Table 2, explicit Ni-Nb to IN625 transfer. Preserve actual Nb when supplied; default proxy chemistry is not an assertion that IN625 contains 5 wt percent Nb. |
| 316L | actual C wt percent, default 0.029; 0.17; 84.3; 2e-9; 1.9e-7 | [Gerstgrasser et al., Materials & Design 199 (2021), 109395](https://doi.org/10.1016/j.matdes.2020.109395), Table 7. The source's effective Fe-0.029C approximation omits explicit Cr/Ni/Mo partitioning and phase selection. Publisher table extraction was read; direct DOI fetch failed. It cannot establish primary austenite/ferrite mode. |

The first row's table inconsistency is an additional named domain warning, not proof of a physical Ti64 prediction. Record both printed m=0.088 and derived m_eff in provenance and model identity; never hide the closure or label m_eff as a transcribed measurement. Ni source `DeltaT0=57 K` is not needed by this law: using the source's m,C0,k gives P=56.875 K. Do not overwrite that arithmetic with rounded 57 K.

### Tier, default nucleation state and intervals

**Best default tier: Tier 2, Physics estimate, for chi and the Hunt envelope fraction/class in all five alloys.** Source-model and family-transfer errors are unknown; numerical point estimates still exist. Display chi to one significant digit and f to one significant digit or approximately whole tens of percent, carrying the unrounded value internally. Use scientific notation for small nonzero fractions, never round a nonzero fraction to an asserted exact zero.

| Alloy | N0 nominal (m-3), deltaTn nominal (K) | Declaration and plausible sensitivity range |
|---|---|---|
| Ti64 | 5e14, 8 | N0 and activation value transferred from the Ti64 phase-field nucleation set in [Gao et al. 2025](https://doi.org/10.1016/j.jmrt.2025.02.019), Table 2. Source uses a Gaussian activation distribution; this Hunt reduction replaces it by one threshold. Declared sensitivity: N0 [5e12,5e15], deltaTn [2,20]. |
| AlSi10Mg | 2e15, 8 | N0 uses Azizi Table 2's inoculant count as an explicit all-sites-eligible approximation, not a measured active count. deltaTn=8 K is a declared scenario assumption, not from Azizi. Declared sensitivity: N0 [1e9,2e15], deltaTn [1,20]. |
| IN718 | 2.65e14, 0 | N0 follows the existing Knapp casting-map-derived set, SPEC section 5.3; deltaTn=0 is the explicitly ideal potent-nucleant limit. This does not claim independently identified active density or reactivate the old source-map class as an LPBF validation. Declared sensitivity: N0 [1e10,1e15], deltaTn [0,20]. |
| IN625 | 2.65e14, 0 | Same N0 as an explicitly declared Ni-family scenario, not an IN625 measurement. Declared sensitivity: N0 [1e10,1e15], deltaTn [0,20]. |
| 316L | 1e13, 8 | Both declared scenario inputs. Declared sensitivity: N0 [1e9,1e15], deltaTn [1,20]. |

These densities correspond to approximately millimetre to micrometre site spacings and span sparse contamination through abundant particulate nucleation; the undercooling ranges cover potent through less potent heterogeneous substrates. They are plausible screening scenarios, not confidence limits or empirical powder characterization. N0=0 is also a physically allowed explicitly requested no-nucleant scenario and gives f=0.

The Ni choice 2.65e14 is a **declared scenario copied from a coupled fitted pair**, not a source-identified standalone active nucleation density: Knapp's map identifies only a*N0^(2/3), as section5.3 of the SPEC records. Combining its reported N0 number with this different growth law is an explicit new scenario assumption and must retain `Unresolved` provenance for that assumption. It cannot inherit an independently calibrated N0 label.

For Tier 2 **no error interval is claimed**, so the input-range-for-interval field is `none`. The declared ranges above are available for a **separate Tier 1 input-sensitivity estimate** when requested: jointly vary paired thermal parents through their declared input box, and N0/deltaTn through the listed endpoints, retain actual alloy C0 uncertainty or use the explicit proxy chemistry, and vary |m|, Gamma and D by factors [0.5,2], k over [0.8k, min(0.99,1.2k)]. These are declared plausible physical coefficient ranges. Compute all joint corners or use proven monotone bounds, never add OFAT deviations as if independent random errors. The resulting min/max is an input-sensitivity interval with unknown model/transfer error outside it. Classes reached are a set, not a probability or an averaged mixed class. A range containing an invalid physical coefficient is rejected; a range crossing a source-domain limit retains flagged members and the whole result is a warned extrapolation rather than silently clamped. Do not promote the default point to Tier 1 without actually evaluating and retaining the declared sweep.

### Domains, refusal and visible text

The models assume a locally quasi-steady, positive-gradient, advancing solidification front, diffusion-controlled solute rejection, constant effective binary coefficients, isotropic equiaxed envelopes and a uniform eligible nucleant population. The source process/composition domains are the table above; family transfer beyond them carries an out-of-domain warning next to the number, including every AlSi10Mg default. **Refuse the Hunt fraction/class when chi <= 1, when predicted solutal tip undercooling exceeds P, or when R reaches an admitted absolute-stability limit.** Keep chi numeric: a planar front or a solute-trapping/absolute-stability growth regime needs its own grain-growth model. Do not present a known impossible solutal dendrite tip as a formal extrapolation. Ni source absolute-stability limit about 0.98 m/s remains a hard grain-model boundary, in addition to the more restrictive tip/P condition when reached first. The carbon-only 316L source has tip<=P only below approximately 0.092 m/s; exact limit derives from its source P,D,Gamma. Other process/composition transfers and moderately transient/curved fields can remain warned Tier 2 extrapolations when the underlying dendritic physics is still applicable. A future trapping or full multicomponent model can improve this route; do not silently insert one.

Retain A5 hard refusals for nonfinite/nonpositive G or R, melting-side or noncooling samples, stale parents and a keyhole result paired with an incompatible conduction field. A melting front cannot represent solidification even if taking abs(R) creates a number. Explain the missing compatible solidifying field or tuple. No heterogeneous-nucleation assumption, source transfer or sweep cures that condition.

At each sample evaluate chi/f/class before spatial aggregation. Preserve the same support and weights as the thermal parent, actual local pairing, fraction basis, inputs, source IDs, out-of-domain flags and tier. Whole-front f is a weighted average of local model fractions, not f evaluated at separate G/R medians; whole-front class is a weighted class distribution or stated dominant model class, never a new class from averaged parameters.

User text, with substituted values and alloy family:

* "Physics estimate: the planar stability index is about {chi}. Values above 1 allow a cellular or dendritic instability in this binary diffusion model. This does not identify grain shape. Uncertainty is unknown and may be large. Calibrate to your machine for better accuracy."
* "Physics estimate: about {fraction} of the model grain envelopes are equiaxed, giving a {class} model class. This uses {family} growth parameters and an assumed nucleation state. Uncertainty is unknown and may be large. Calibrate to your machine for better accuracy."
* "Out of domain: {named composition, process, speed, stability or field limit}. This number is an extrapolation of the stated model."
* "Estimated: {value}, with an input sensitivity interval of {low} to {high}. The interval comes from a joint sweep of the declared input ranges. Model and family transfer error are unknown and may be large. Calibrate to your machine for better accuracy."
* "A solidification estimate needs a compatible cooling side front with finite positive gradient and growth rate."
* "The planar stability index can be computed here. A grain fraction needs a growth model for this planar or rapid solidification regime. The current dendrite model cannot represent it."

## Ti64 per-sample first-pass martensite: Tier 2

Use [Salsi, Chiumenti and Cervera, Metals 8 (2018), 633](https://doi.org/10.3390/met8080633), section 3.2.2 equation 19 and section 4.1 paragraph before Figure 7: `f_alpha_m = beta0 * (1-exp(-km*(Ms-T)))`, km=0.005 K-1, Ms=575 C. At T >= Ms, f_alpha_m=0. The source's alpha_m groups martensite and massive alpha; do not claim an exact independently identified alpha-prime phase fraction. The quench-limit scenario sets beta0=1 and beta=1-f_alpha_m. This is an explicit first-pass, fully-beta, diffusion-suppressed model, not a cumulative multilayer inventory.

A quasi-steady field can supply the material-point path `T(x0-v*t,y0,z0)` after the associated sample fully melts. Emit the actual computed path, final evaluation temperature and first-pass identity; measured or multilayer history is not required for this conditional single-pass estimate. Require a monotonic cooling path after full melting, a full-beta start above the source's 998 C beta transus, and a cooling-rate check through 998 C to Ms of at least 410 K/s, using the subsolidus material-point history rather than liquidus G*R. Check every resolved segment intersecting that interval, with refinement bounds. Source section 3.2.2 distinguishes rates below 410 C/s, at which a minimum retained equilibrium beta and preceding diffusional alpha formation need treatment.

For this simple no-dissolution scenario the research checker additionally requires at least 410 K/s on every resolved segment starting below the beta transus, down to the finite evaluation point. This extension is a conservative scenario admission rule, not a source-derived universal threshold below Ms. It excludes slow cooling and holds that can dissolve martensite even without reheating, as discussed in source section 4.2. A rapid-quench-limit reference may still be shown separately; it must not be presented as the retained inventory for such a path. Do not assert arrival at an asymptotic preheat temperature in finite time. KM progress is normalized to the entering beta; unless a physical mass/volume convention is established, use `reaction-progress` with beta0 recorded and keep any pre-existing `1-beta0` constituent separately.

The nominal quench-limit estimate is **Tier 2** with no interval: uncertainty is unknown. At 25 C, beta0=1 gives 0.9360721388 alpha_m and 0.0639278612 beta; display approximately 90 percent and 10 percent. These are source-law arithmetic checks, not an observation of the user's build. A declared range sweep of Ms/km/beta0 is possible only as a separately identified sensitivity scenario; this note does not invent a source uncertainty for them.

Reheating or unresolved/slow cooling requires the source's competing JMAK/dissolution equations with admitted kinetic parameters, or a user-supplied beta0 established by such a model. A standalone front tuple cannot determine beta0. Do not silently assume beta0=1 in the slow branch. Outside the fast-cooling domain, a separately named rapid-quench-limit scenario may still show the number with its warning; an actual retained phase inventory has no value until that missing model/input is supplied. Missing/inconsistent full-melt initialization or a heating path cannot be repaired by clipping phase fractions.

Visible text: "Physics estimate for a single rapid cooling pass: about {fraction} alpha martensite or massive alpha, with the remainder beta. The model assumes fully beta material before cooling and omits diffusional transformation and later reheating. Uncertainty is unknown and may be large. Calibrate to your machine for better accuracy."

Missing-input text: "A retained phase estimate needs a cooling path and the beta fraction entering martensite formation. Slow cooling or reheating also needs competing transformation kinetics."

## AlSi10Mg terminal primary and eutectic constituents: Tier 2

For a fully melted, monotonically solidifying single pass, use the ideal constant-k binary Al-Si Scheil mass balance: `CL=C0*(1-fPrimary)^(k-1)`. At the binary eutectic composition Ce, `fPrimaryAlphaAl = 1-(Ce/C0)^(1/(k-1))` and `fEutecticConstituent = 1-fPrimaryAlphaAl`. This is an alpha-Al primary solid plus terminal Al+Si microconstituent inventory on a **mass basis**, not separate Al/Si phase fractions and not an Mg2Si precipitation prediction.

The Scheil equation follows independently from `(CL-k CL) df=(1-f) dCL`, with complete liquid mixing, no solid back diffusion, constant k and a single primary branch. [Zhang et al., Metallurgical and Materials Transactions B (2023)](https://doi.org/10.1007/s11663-023-02742-3), the paragraph/equation `c_l=c0(1-f_s)^(k-1)` and Figure 10, independently states/tests this relation in a solidification model. Use k=0.13 from Azizi Table 2 above; Ce=12.6 wt percent from [Modeling and Simulation Investigations on Microstructure Evolution during Additive Manufacturing of AlSi10Mg Alloy, Metals 12 (2022), 1711](https://doi.org/10.3390/met12101711), Table 1, eutectic composition row. The latter source also states that Mg and Si transport should be treated separately in a full ternary model. This reduction explicitly ignores Mg and minor elements. Source data were read in publisher indexed table extraction; direct MDPI fetch was rate limited.

Use the sample's solved Si chemistry, not an invented composition from the alloy name; when only the named nominal proxy is selected, disclose C0=10 wt percent as an explicit nominal scenario. At C0=10, fPrimary=0.2333 and fEutectic=0.7667 approximately (the check script retains exact double arithmetic). Tier 2 has no error interval, two coarse displayed fractions summing to one, and unknown transfer error. This is a numeric phase-constituent estimate for the sample chemistry and a declared single solidification cycle, not the current final retained phase inventory.

Domain: hypoeutectic `0<C0<Ce`, `0<k<1`, primary alpha-Al, complete melting, complete single-pass freezing with terminal eutectic accounted, no subsequent dissolution/coarsening. C0=Ce gives zero primary alpha-Al as the binary eutectic limit; C0>Ce requires a primary-Si/hypereutectic model and must not use the alpha-Al equation with a negative result. No arbitrary clamping. Warn for Al-0.5Si coefficients transferred to AlSi10Mg, trapping/back-diffusion, Mg/minor chemistry and remelting. A path that has not reached the terminal reaction needs its actual temperature and a partial Scheil path, not a falsely complete eutectic inventory. A liquidus-only tuple is insufficient to assert terminal freezing, but its solved field can supply the single-pass path.

Visible text: "Physics estimate for one complete solidification pass: about {primary} primary aluminium and {eutectic} aluminium plus silicon eutectic constituent by mass. This uses a binary Al-Si Scheil model transferred to AlSi10Mg. It does not predict separate silicon or Mg2Si phase fractions. Uncertainty is unknown and may be large. Calibrate to your machine for better accuracy."

## AlSi10Mg phase-resolved terminal equilibrium reference: Tier 2

An additional **phase-resolved equilibrium-limit estimate** can be formed for each solved Al-Si-Mg chemistry. It is distinct from the Scheil constituents and from an as-built prediction. Use a closed Al-Si-Mg system, zero terminal Si/Mg solubility in alpha-Al, all Mg bound as stoichiometric Mg2Si, remaining Si as pure Si, and remaining Al as alpha-Al. These are declared asymptotic low-solubility equilibrium-limit assumptions, not measured solubilities or a source-calibrated phase law for LPBF.

The phase set and composition-based lever-rule approach are supported by [Yaokawa et al., Materials Transactions 64 (2023), MT-M2022165](https://doi.org/10.2320/matertrans.MT-M2022165), section 4.3. The zero-solubility limit is this note's explicit simplifying model assumption. With input mass fractions `cSi,cMg` and molar masses MMg=24.305, MSi=28.085 g/mol, mass conservation gives:

```
fMg2Si = cMg * (2*MMg + MSi)/(2*MMg)
fSi = cSi - cMg * MSi/(2*MMg)
fAlphaAl = 1 - fSi - fMg2Si
```

Molar masses use the [CIAAW 2024 abridged table](https://ciaaw.org/abridged-atomic-weights.htm), magnesium/silicon rows. Their atomic-weight uncertainties do not establish model uncertainty. Actual solved Si/Mg chemistry is required; if only a named nominal scenario is requested, explicitly declare cSi=0.10 and cMg=0.003. For that scenario the fractions are approximately 0.897 alpha-Al, 0.0983 Si and 0.00473 Mg2Si by mass. Display about 90 percent, 10 percent and 0.5 percent, with the rounded-total caveat; raw values conserve mass. There is **no error interval** at default Tier 2. Unknown kinetics, supersaturation and transfer error may be large.

Domain: nonnegative Si/Mg mass fractions summing below one, enough Si to bind Mg (`cSi >= cMg*MSi/(2*MMg)`), no other phase-forming chemistry, no oxidation/evaporation losses, an explicitly requested terminal equilibrium-limit reference. Outside the chemistry condition, use another phase set rather than clipping fSi to zero. For actual LPBF material, supersaturation, metastable precipitates, finite solubility, Mg loss or thermal exposure are out-of-domain warnings: retain the equilibrium reference number with the explicit reference label, while final as-built phase fractions remain uncomputed. An omitted Mg input must not silently become zero. To improve the reference, supply temperature-dependent phase solubilities; to predict retained sample phases supply the appropriate multicomponent thermodynamics/kinetics and path.

Visible text: "Physics estimate for the terminal equilibrium limit: about {Al} aluminium, {Si} silicon and {Mg2Si} Mg2Si by mass. The model assumes no solute remains in aluminium and all magnesium forms Mg2Si. It does not predict the retained phases after rapid cooling. Uncertainty is unknown and may be large. Calibrate to your machine for better accuracy."

## Remaining phase quantities and exact computability conditions

| Alloy | Numeric route now formed | Actual final phase inventory without further inputs/models |
|---|---|---|
| Ti64 | Tier 2 alpha_m/beta rapid first-pass model above | Reheating/slow cooling: needs competing diffusional/dissolution kinetics and incoming beta0, plus the corresponding history. Source calls alpha_m a combined martensite/massive-alpha constituent, not unique alpha-prime identification. |
| AlSi10Mg | Tier 2 terminal-equilibrium-limit alpha-Al/Si/Mg2Si phases; separate Tier 2 primary alpha-Al/eutectic microconstituents | Retained supersaturation and actual as-built Si/Mg2Si fractions need a phase-resolved multicomponent solidification/precipitation model and time-temperature history. |
| IN718 | Source-qualified primary gamma context; no new final phase fraction | Needs an admitted phase-resolved gamma/carbide/Laves solidification model with path-local residual chemistry and phase definitions; later delta/gamma-prime/gamma-double-prime fractions need their kinetics and the single/multipass heat path. A Ni-Nb single-solid fraction alone cannot identify those products. Preserve A3 database-domain restrictions. |
| IN625 | Source-qualified primary gamma context; no new final phase fraction | Needs an admitted multicomponent segregation/terminal phase-selection model plus thermal history; later delta/carbides require compatible kinetics. IN718 parameters do not silently become an IN625 phase law. |
| 316L | Front-stability number exists, but Fe-C proxy does not select primary austenite/ferrite | Needs full C,N,Cr,Ni,Mo etc. chemistry and a source-bound competing austenite/ferrite solidification-growth model, followed by the relevant subsolidus transformation history. Nominal name and G/R do not select phase mode. |

The last three no-value states are model/input absence for the **requested phase inventory**, not a refusal because uncertainty is unknown. Use explanatory text stating those named requirements; do not say only "Unavailable". No unsupported numeric phase probability or zero phase inventory is emitted.

## Reproducible research checks

Run `python -I -B docs/research/scripts/sol_c_a6_morph_phase_check.py --check`. It parses source rows from [bounded primary extracts](sol_c_a6_morph_source_extracts.json), reports their SHA256 identity, checks the explicit Ti64 source-range closure, SI scaling and independently integrated Hunt grain radius, true versus extended fraction thresholds, local pairing, joint sweep containment, Ti64 KM exponential against a separately integrated depletion ODE, phase conservation, distinct subsolidus-rate versus liquidus-rate behavior and slow/held cooling below Ms, Al Scheil against an independent incremental solute balance, and the terminal three-phase mass balance against independent formula-unit atom inventories. It rejects nonfinite, nonphysical, heating-side, stale and incompatible-field cases. **Authentication limit:** the bounded numeric/equation records preserve normalized transcriptions of browser/search extraction of primary publisher/author text, not authenticated original-PDF bytes or raw HTML; direct publisher downloads failed where stated. The hash identifies the transcription receipt, not the original article. These checks establish model arithmetic and refusal behavior, not physical accuracy or a served migration.
