# P8 research panel residuals, 2026-10-15

Scope: approved refusal item 23, quantity labels and contract 14.7 phase D batch client. No physical equation or served path changes.

## Wording for lead review

Item 23 now comes from the Python describe sentence table; the identical TypeScript constant is a parity pin, not an override:

`Not available: no source-bound closure or data exists for the keyhole thermal flow.`

Quantity labels changed below. Units remain in the field unit column. Existing hand-authored labels are preserved. These labels name quantities and model choices; they assert no validation.

| Path | Previous | New |
|---|---|---|
| `keyholeCavity.alloy` | Research alloy | Alloy |
| `keyholeCavity.power_W` | Research power W | Laser power |
| `keyholeCavity.speed_m_s` | Research speed m s | Scan speed |
| `keyholeCavity.beamDiameter_m` | Research beam Diameter m | Beam diameter |
| `keyholeCavity.preheat_K` | Research preheat K | Preheat temperature |
| `keyholeCavity.liquidus_K` | Research liquidus K | Liquidus temperature |
| `keyholeCavity.conductivity_W_mK` | Research conductivity W m K | Conductivity |
| `keyholeCavity.specificHeat_J_kgK` | Research specific Heat J kg K | Specific heat |
| `keyholeCavity.density_kg_m3` | Research density kg m3 | Density |
| `keyholeCavity.diffusivity_m2_s` | Research diffusivity m2 s | Thermal diffusivity |
| `keyholeCavity.wallAbsorptanceProxy` | Research wall Absorptance Proxy | Wall absorptance proxy |
| `keyholeCavity.vapourTemperature_K` | Research vapour Temperature K | Vapour temperature |
| `keyholeCavity.vapourLatentHeat_J_kg` | Research vapour Latent Heat J kg | Vapour latent heat |
| `keyholeCavity.vapourMolarMass_kg_mol` | Research vapour Molar Mass kg mol | Vapour molar mass |
| `keyholeCavity.propertyConvention` | Research property Convention | Property convention |
| `keyholeCavity.propertySource` | Research property Source | Property source |
| `keyholeCavity.vapourSource` | Research vapour Source | Vapour source |
| `keyholeCavity.onsetEvent` | Research onset Event | Onset event |
| `keyholeCavity.thermalResponse_g` | Research thermal Response g | Thermal response |
| `keyholeCavity.thresholdTemperature_K` | Research threshold Temperature K | Onset threshold temperature |
| `keyholeCavity.onsetPower_W` | Research inception onset power P* ({onsetEvent} convention) | Inception onset power P* ({onsetEvent} convention) |
| `keyholeCavity.powerOverOnset` | Research power Over Onset | Power relative to onset |
| `keyholeCavity.modeledAboveOnset` | Research modeled Above Onset | Above onset in this model |
| `keyholeCavity.cavityDepth_um` | Research cavity Depth um | Cavity depth |
| `keyholeCavity.cavityAbsorptance` | Research cavity Absorptance | Cavity absorptance |
| `keyholeCavity.totalAbsorptance` | Research total Absorptance | Total absorptance |
| `keyholeCavity.energyResidual_W` | Research energy Residual W | Energy residual |
| `keyholeCavity.rootCount` | Research root Count | Root count |
| `keyholeCavity.rootTopologyStatus` | Research root Topology Status | Root topology |
| `keyholeCavity.selectedBranch` | Research selected Branch | Selected branch |
| `keyholeCavity.roots` | Research roots | Roots |
| `keyholeCavity.rootScanRelativeDifference` | Research root Scan Relative Difference | Relative difference after root-scan refinement |
| `keyholeCavity.cylinderHarmonicDifference` | Research cylinder Harmonic Difference | Difference after cylinder-series refinement |
| `meltDepthLink.cavityDepth_um` | Research cavity Depth um | Cavity depth |
| `meltDepthLink.conductionDepth_um` | Research conduction Depth um | Conduction depth |
| `meltDepthLink.conditionalMeltDepth_um` | Research conditional Melt Depth um | Conditional melt depth |
| `meltDepthLink.linkedMeltDepth_um` | Research linked Melt Depth um | Linked melt depth |
| `meltDepthLink.controllingLeg` | Research controlling Leg | Controlling depth model |
| `meltDepthLink.linkDispatch` | Research link Dispatch | Depth model selection |
| `meltDepthLink.conductionStatus` | Research conduction Status | Conduction status |
| `meltDepthLink.surfacePower_W` | Research surface Power W | Surface power |
| `meltDepthLink.cavityPower_W` | Research cavity Power W | Cavity power |
| `meltDepthLink.absorbedPower_W` | Research absorbed Power W | Absorbed power |
| `meltDepthLink.depositedThermalPower_W` | Research deposited Thermal Power W | Deposited thermal power |
| `meltDepthLink.unresolvedPower_W` | Research unresolved Power W | Unresolved power |
| `meltDepthLink.cavityPowerFraction` | Research cavity Power Fraction | Cavity power fraction |
| `meltDepthLink.wallConductionPower_W` | Research wall Conduction Power W | Wall conduction power |
| `meltDepthLink.cavityLedgerRatio` | Research cavity Ledger Ratio | Cavity ledger ratio |
| `meltDepthLink.lossMultiplier` | Research loss Multiplier | Loss multiplier |
| `meltDepthLink.photonResidual_W` | Research photon Residual W | Photon residual |
| `meltDepthLink.relativeConvergenceDifference` | Research relative Convergence Difference | Relative difference after numerical refinement |
| `meltDepthLink.meltDepthCoarse_m` | Research melt Depth Coarse m | Melt depth on the coarse search |
| `meltDepthLink.meltDepthRefined_m` | Research melt Depth Refined m | Melt depth on the refined search |
| `meltDepthLink.conductionRefinement_m` | Research conduction Refinement m | Conduction-depth refinement difference |
| `meltDepthLink.conductionPeakX_m` | Research conduction Peak X m | Position of maximum conduction depth |
| `meltDepthLink.conductionRearBound_m` | Research conduction Rear Bound m | Rear search bound for conduction depth |
| `meltDepthLink.quadratureOrder` | Research quadrature Order | Quadrature order |
| `meltDepthLink.xSamples` | Research x Samples | Axial search samples |
| `meltDepthLink.observable` | Research observable | Observable |
| `meltDepthLink.floorFieldModelId` | Research floor Field Model Id | Conduction-field model |
| `meltDepthLink.floorExtractorId` | Research floor Extractor Id | Conduction-depth extraction method |
| `marangoni.surfaceTensionSlope_N_mK` | Research surface Tension Slope N m K | Surface tension slope |
| `marangoni.slopeMode` | Research slope Mode | Surface-tension slope mode |
| `marangoni.slopeBaseline` | Research slope Baseline | Surface-tension slope baseline |
| `marangoni.length_m` | Research length m | Surface-flow length scale |
| `marangoni.deltaTemperature_K` | Research delta Temperature K | Temperature difference |
| `marangoni.referenceTemperature_K` | Research reference Temperature K | Reference temperature |
| `marangoni.viscosity_Pa_s` | Research viscosity Pa s | Viscosity |
| `marangoni.liquidConductivity_W_mK` | Research liquid Conductivity W m K | Liquid conductivity |
| `marangoni.liquidSpecificHeat_J_kgK` | Research liquid Specific Heat J kg K | Liquid specific heat |
| `marangoni.liquidDensity_kg_m3` | Research liquid Density kg m3 | Liquid density |
| `marangoni.liquidDiffusivity_m2_s` | Research liquid Diffusivity m2 s | Liquid diffusivity |
| `marangoni.marangoniNumber` | Research marangoni Number | Marangoni number |
| `marangoni.marangoniMagnitude` | Research marangoni Magnitude | Marangoni number magnitude |
| `marangoni.surfaceVelocityScale_m_s` | Research surface Velocity Scale m s | Surface velocity scale |
| `marangoni.liquidPecletScale` | Research liquid Peclet Scale | Liquid Peclet number scale |
| `marangoni.liquidReynoldsScale` | Research liquid Reynolds Scale | Liquid Reynolds number scale |
| `marangoni.liquidPrandtl` | Research liquid Prandtl | Liquid Prandtl number |
| `marangoni.flowDirection` | Research flow Direction | Flow direction |
| `marangoni.source` | Research source | Source |
| `surfaceBalance.absorbedCenterFlux_W_m2` | Research absorbed Center Flux W m2 | Absorbed center flux |
| `surfaceBalance.conductiveAdmittance_W_m2K` | Research conductive Admittance W m2K | Conductive admittance |
| `surfaceBalance.monotonicDerivative_W_m2K` | Research monotonic Derivative W m2K | Surface-balance flux derivative |
| `surfaceBalance.evaporationMassFlux_kg_m2_s` | Research evaporation Mass Flux kg m2 s | Evaporation mass flux |
| `surfaceBalance.evaporationEnergyFlux_W_m2` | Research evaporation Energy Flux W m2 | Evaporation energy flux |
| `surfaceBalance.saturationPressure_Pa` | Research saturation Pressure Pa | Saturation pressure |
| `surfaceBalance.conductionFlux_W_m2` | Research conduction Flux W m2 | Conduction flux |
| `surfaceBalance.radiationFlux_W_m2` | Research radiation Flux W m2 | Radiation flux |
| `surfaceBalance.relativeFluxResidual` | Research relative Flux Residual | Relative flux residual |
| `surfaceBalance.surfaceGainRefinementRelative` | Research surface Gain Refinement Relative | Relative change after surface-gain refinement |
| `surfaceBalance.iterations` | Research iterations | Iterations |
| `surfaceBalance.evaluationLocation` | Research evaluation Location | Evaluation location |
| `surfaceBalance.vapourPreset` | Research vapour Preset | Vapour preset |
| `surfaceBalance.vapourTemperature_K` | Research vapour Temperature K | Vapour temperature |
| `surfaceBalance.vapourLatentHeat_J_kg` | Research vapour Latent Heat J kg | Vapour latent heat |
| `surfaceBalance.vapourMolarMass_kg_mol` | Research vapour Molar Mass kg mol | Vapour molar mass |
| `surfaceBalance.evaporationConvention` | Research evaporation Convention | Evaporation convention |
| `surfaceBalance.evaporationAccommodation` | Research evaporation Accommodation | Evaporation accommodation |
| `surfaceBalance.effectiveAccommodation` | Research effective Accommodation | Effective accommodation |
| `surfaceBalance.netEvaporationFactor` | Research net Evaporation Factor | Net evaporation factor |
| `surfaceBalance.effectiveNetFactor` | Research effective Net Factor | Effective net factor |
| `surfaceBalance.recoilFraction` | Research recoil Fraction | Recoil fraction |
| `surfaceBalance.emissivity` | Research emissivity | Emissivity |
| `surfaceBalance.source` | Research source | Source |
| `alSi10MgIndexDisclosure.physicalAbsorptance` | Research physical Absorptance | Physical absorptance |
| `alSi10MgIndexDisclosure.indexAbsorptance` | Research index Absorptance | Index absorptance |
| `alSi10MgIndexDisclosure.physicalToIndexRatio` | Research physical To Index Ratio | Physical absorptance relative to index absorptance |
| `alSi10MgIndexDisclosure.decision` | Research decision | Decision |
| `alSi10MgIndexDisclosure.classificationChanged` | Research classification Changed | Change in index classification |
| `alSi10MgIndexDisclosure.basis` | Research basis | Basis |
| `unavailablePhysics.marangoniWidthDepthCorrection` | Research marangoni Width Depth Correction | Marangoni width-to-depth correction |
| `unavailablePhysics.powderAbsorptance` | Research powder Absorptance | Powder absorptance |
| `unavailablePhysics.physicalKeyholeGradient_K_m` | Research physical Keyhole Gradient K m | Physical keyhole temperature gradient |
| `unavailablePhysics.physicalKeyholeCoolingRate_K_s` | Research physical Keyhole Cooling Rate K s | Physical keyhole cooling rate |
| `alSi10MgVapourMgAware.scenarioTemperature_K` | Research scenario Temperature K | Scenario temperature |
| `alSi10MgVapourMgAware.scenarioMolarMass_kg_mol` | Research scenario Molar Mass kg mol | Scenario molar mass |
| `alSi10MgVapourMgAware.scenarioLatentHeatLocalSlope_J_kg` | Research scenario Latent Heat Local Slope J kg | Scenario latent heat from local slope |
| `alSi10MgVapourMgAware.scenarioLatentHeatTableWeighted_J_kg` | Research scenario Latent Heat Table Weighted J kg | Scenario latent heat from table weighting |
| `alSi10MgVapourMgAware.pureMgPressure_atm` | Research pure Mg Pressure atm | Pure Mg vapour pressure |
| `alSi10MgVapourMgAware.composition_wt_pct` | Research composition wt pct | Feedstock composition |
| `alSi10MgVapourMgAware.pressureRoute` | Research pressure Route | Pressure route |
| `alSi10MgVapourMgAware.calculationStatus` | Research calculation Status | Calculation status |
| `alSi10MgVapourMgAware.source` | Research source | Source |
| `alSi10MgVapourMgAware.dynamicVapourTemperature_K` | Research dynamic Vapour Temperature K | Dynamic vapour-temperature inference |
| `keyholeCavity.roots.depth_um` | Research root depth um | Root depth |
| `keyholeCavity.roots.aspectRatio_e_over_d` | Research root aspectRatio e over d | Root depth over beam diameter, e/d |
| `keyholeCavity.roots.scalarRelaxation` | Research root scalarRelaxation | Root scalar relaxation |
| `keyholeCavity.roots.cavityEnergyResidual_W` | Research root cavityEnergyResidual W | Root cavity energy residual |
| `keyholeCavity.roots.selected` | Research root selected | Selected root |

129 label entries changed. The existing physical cavity-wall temperature label and approved text remain verbatim. R-UI-6 now excludes only the two contract-authorized phrases, not the conduction position label. No physical quantity or numeric value changed.

## New CLI strings (lead review)

These are all new runtime CLI text templates. `{kind}` is an existing outcome or timeout code; an absent timeout kind displays `unknown`. Flags, paths, run ids and counts are substituted as data. Test descriptions and assertion diagnostics are test-only.

| Key | Text |
|---|---|
| `estimate` | {n} conditions, estimated {seconds} s using the measured default-manifest cold nominal plus band time (11.5 s per condition, P8 phase C). This is an estimate, not a time limit. Press Ctrl+C to cancel. |
| `cap` | Batch exceeds the {max} condition limit. |
| `max` | maxRequests must be an integer from 1 to 256. |
| `runId` | runId must contain 8 to 32 lowercase letters or digits. |
| `input` | Input must be a nonempty array of research request bodies. |
| `relayOptions` | A relay request cannot include researchOptions. |
| `cancelled` | Batch cancelled. No further requests will be sent. |
| `timeout` | Research timeout ({kind}). |
| `failed` | Research request failed ({kind}). |
| `mismatch` | Research response does not match the request. |
| `progress` | Research progress stalled on the persistent lane. No null-budget request was sent. |
| `incomplete` | The null-budget request did not complete. |
| `relay` | The complete response has no valid relay within the 16000-character limit. |
| `tooLarge` | Research payload exceeds its transport size limit. |
| `flag` | Unknown argument or missing value: {flag}. |
| `required` | Use --input FILE --output-dir DIR [--url URL] [--max-requests N] [--run-id ID]. |
| `complete` | Batch complete: {n} conditions. Full responses saved. |
| `partial` | Batch incomplete. Files already saved are partial output and must not be used as a complete relay. |

## Batch behavior and use

`npx tsx scripts/research-route-batch.ts --input conditions.json --output-dir responses [--url http://localhost:3000] [--max-requests 256] [--run-id abc12345]`

Input is a nonempty JSON array of request bodies carrying `process`, `propertyContext`, optionally `relay` or `researchOptions` (never both). The client assigns its sender, request ids, stages and run-scoped supersede key. The default cap is 48 conditions; the explicit ceiling is 256. A single instance awaits every HTTP response and file write. The optional local bearer token comes from `METALLIKSA_TOKEN` and is never printed.

Each condition runs nominal then 1500 ms band chunks. Queue/reply timeouts can retry once with a fresh request id; run/adhoc timeouts are final. Revision 5 takes precedence over the old stall-to-null rule: a persistent-lane stall fails; only an ad-hoc response or changed cache instance enables a null budget. A null-budget request is sent at most once per condition, including after a reply timeout. Its timeout therefore ends the condition rather than risking a second null-budget computation.

The estimate uses 11.5 s per condition, rounding up the slower measured default cold nominal plus band total (AlSi10Mg: 1.551 + 9.855 s, phase C report). It is printed before the first request with Ctrl+C cancellation. It is a default-manifest estimate, not a promise for user-extended manifests or contention.

Each successful condition writes its full final response as `<runId>-<index>.json`. Exclusive creation prevents overwriting an existing run. The relay string is never parsed or reserialized. Cancellation/failure stops the run with a nonzero exit and an incomplete-output warning; earlier files remain for inspection, and the hub must still reject a partial relay. The hub owns binding, hash and cross-condition validation.

The transport and numeric fixtures remain byte-identical. Render tests load the current Python label and sentence tables over the old pruned fixture shape, so the banned-label scan covers current backend wording. Python also checks the literal TypeScript item 23 against the describe table. The TypeScript constant remains a parity pin only; runtime refusal rendering uses the response table directly.

Only the research identity pin is regenerated with the changed research source. No evidence ceiling or physical validation claim is raised. No push is performed.

## Verification

All checks below ran in this worktree on the final code. No changes were made to equations, served code, parity baselines or ceilings.

| Check | Result |
|---|---|
| `npm run lint` | PASS, TypeScript compile check, 0 errors |
| `npx tsx --test tests/lpbf-research-*.test.ts tests/lpbf-research-*.test.tsx` | 70 passed, 0 failed, 0 skipped; includes 11 batch tests |
| `npm run test:unit` | 1365 passed, 0 failed, 1 skipped (1366 total). The pre-existing Phase 4 end-to-end test skips because optional CMU STMeasurements.csv, MTMeasurements.csv and README.txt are not restored. |
| Python `-B -m unittest discover -s python -p test_lpbf_research*.py` | 114 passed, 0 failures, 341.029 s; includes real default and 80-arm capacity checks for both alloys |
| Python `-B -m unittest discover -s python -p test_persistent_ipc_research_lane.py` | 11 passed, 0 failures |
| Python `-B -m unittest discover -s python -p test_module_contract_research.py` | 5 passed, 0 failures; Python research checks total 130 |
| Python `-B python/tools/lpbf_parity_check.py --check` | PASS, 24 cases; slow mode was not requested or run |
| Python `-B python/lpbf_research_identity_pin.py --check` | PASS; research identity `91e3aa2328eba33377bf2818d256cf77e64b491a59a7eef14fca77742c829fab` |
| Python `-B python/tools/p8_isolation_diff_check.py` | PASS at precommit HEAD 64bbbd44; rechecked after committing the residuals |
| Working-tree comparison with `64bbbd44` | 36 manifest entries unchanged; all 121 compared manifest-source, served-pin, golden, fixture, AUTHORITY_ALLOWLIST and ceiling paths unchanged |
| `git diff --check` | PASS on task paths |
| Independent read-only review | No actionable findings; no code edits by reviewer |

All Python checks used `C:/Users/can02/Projects/metalliksaa/Metalliksa-1/.runtime/lpbf-win-py312/Scripts/python.exe`. TypeScript runs set `PYTHON_EXECUTABLE` to the same interpreter for the live text-table overlay. No dependencies were installed.

UI wording was checked through rendered-component tests, including fully expanded modules and the strengthened banned-word scan. A live Chrome check loaded the actual current nominal Ti-6Al-4V research response in a temporary local component harness. All seven module sections were opened with Enter. The new conduction-position and slope-mode labels and approved refusal were visible; a DOM text scan found no standalone peak outside the two authorized phrases. This checks component wording and keyboard expansion, not the complete host or blind-freeze workflow. The temporary page and server were removed after the check. The CLI integration test used a local synthetic HTTP server; it is transport evidence, not an end-to-end physics or blind-freeze validation. The existing hub relay checks remain the hub's responsibility.

The served fingerprint remains `36cd9d4a96c9726ab2ff4f3030b442f862d96f9ebdc3f724cc6dd85f55110348`. Initial unrelated `.claude/` modifications were preserved and excluded from staging. No approval trailer, push or ceiling change is part of this work.
