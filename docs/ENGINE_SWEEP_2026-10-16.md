# Served engine sweep — 2026-10-16

## Scope and reproducibility

Checkout: `Metalliksa-1-wt-sweep`, branch `chore/engine-sweep`, base `ec14298d`. Inventory: **28 operation families**, including distinct submit engine branches and archive readers; **16 executed**, **12 wholly skipped**. Across five requested alloy identities and three P8 stages: **94 records = 58 ok + 15 error + 21 skipped**. **7 operation families have at least one error**. Aliases and repeat submissions are not additional physics engines.

Read-only apart from this tool, its test, this report, explicitly requested raw JSON in the OS temp directory, and disposable solver artifacts. No served module, manifest, golden, pin, CI file or parity check changed. No GPU, OpenFOAM, network, measured-row loader or `.orchestra/external-data` access. The seven named forbidden dataset paths and network/child execution are blocked by an audit hook. CPU calls are sequential with BLAS/OpenMP/NumExpr threads fixed to 1. No queue/SQLite job is submitted or cancelled. Worker job functions run directly into disposable temporary folders.

Direct Python calls reproduce the computation branch, not the HTTP transport, warm daemon, cache reuse, scheduling or UI rendering. `ok` means the function returned without a top-level error: it can still contain unavailable physics. `ReturnedError` is the harness label for a returned `success:false`/error envelope; it is not an invented Python exception class. Exceptions retain their actual class/message. No experimental validation is claimed.

Commands (from the checkout; interpreter exactly as requested):

```powershell
$py = 'C:/Users/can02/Projects/metalliksaa/Metalliksa-1/.runtime/lpbf-win-py312/Scripts/python.exe'
& $py python/tools/test_engine_sweep.py
& $py python/tools/engine_sweep.py --output "$env:TEMP/metalliksa-engine-sweep.json" --timeout 45
# CALPHAD can exceed 45 s on this shared CPU; final calls use a bounded 120 s budget:
& $py python/tools/engine_sweep.py --output "$env:TEMP/metalliksa-calphad.json" --timeout 120 --only calphad-minimize
```

The first exploratory melt-pool pass used the Python Rosenthal default. It was replaced in the final inventory by the actual mounted UI default **Goldak**, sulfur 15 ppm. CALPHAD was repeated with the CLI literature/provenance additions included. Two 45 s CALPHAD retries timed out; the final bounded retry below determines the final outcome. Timing varies with the other ongoing work; no latency benchmark is implied.

Raw per-call evidence (all exact paths, inherited reason objects, input payloads, errors and logs): `C:/Users/can02/AppData/Local/Temp/metalliksa-engine-sweep-20261016-final.json` (not committed). SHA-256: `d929ca2fb78dc0027c855adc3c91d235c5653b19b9657b9851b17e6a1d8a9814`. The tables and grouped leaf index below preserve reviewable results in Git; rerun the standalone tool to regenerate full JSON.

## Input contract

| Alloy identity | P W | v mm/s | preheat C | composition basis |
| --- | --- | --- | --- | --- |
| Ti-6Al-4V | 240 | 1200 | 150 | UI preset |
| AlSi10Mg | 350 | 1300 | 160 | UI preset |
| IN718 | 280 | 940 | 200 | UI preset |
| 316L | 200 | 850 | 80 | UI preset |
| IN625 | 280 | 940 | 200 | No UI preset; identity-only substitution, no chemistry invented |

Shared fresh specimen defaults: beam 80 µm (1/e²), layer 40 µm, hatch 100 µm, IR_1064nm, stripe strategy, seed 42, no uploaded mesh (nozzle demo). Values are the UI’s defaults, not a recommended process recipe. Loading a preset normally preserves an already edited process vector; this sweep starts from a fresh preset-derived vector. IN625 retains the initial IN718 process vector only for the requested identity coverage. Unsupported identities are deliberately probed and are distinguished from bugs.

CALPHAD: exact UI wt% presets, Al 400–750/10 C, Ti 600–1750/25 C, others 500–1550/25 C; database auto, adaptiveGrid/boundaryRefinement/Scheil false. IN625 composition is absent and is skipped. Bayesian: UI bounds P 100–500, v 200–2000, h 60–200, t 20–80; 20 iterations/5 warmup/seed 42, beam/preheat 80/80. G/R: default IN718 7×7 axes P 60–450 W, v 275–1500 mm/s, beam/layer/hatch/preheat 80/40/110/80; the same explicit axes are held while substituting alloys. Other-alloy map forms initially have blank axes, so those are coverage probes, not an automatic UI request. No measured overlay runs.

Transient: standard, explicit reference CPU (equivalent to auto with no OpenFOAM capability), mesh 20 µm, maxDt 1e-6 s, 600 µm track, one track/layer, dwell/cooling 0.2/0.5 ms, no study or measurements; these match useLpbfEngineeringStore defaults. P8: nominal property context, empty options/ranges, describe/nominal/band stages; band budget 1500 ms. Each stage has a cold process cache: a band response may have `researchModels:null` while progress is pending; the mounted UI retains nominal output and requests later chunks. Build-job uses no UQ/NIST/CT data. Calibrated mode is explicitly opted in; local fitted artifact summaries are allowed, measured-row loaders remain blocked. Machine-calibrated calls with no selected artifact id are deliberate precondition probes; the UI normally waits for selection.

## Served Python inventory and UI reachability

| Operation family | Python authority | UI screen / caller | HTTP route or internal bridge |
| --- | --- | --- | --- |
| calphad-minimize | calphad_solver:compute_multi_component_equilibrium | CALPHADMultiComponentStudio / phase-diagram | /api/python/calphad-minimize (alias /api/calphad/minimize) |
| calphad-databases | calphad_solver:list_available_databases | CALPHADMultiComponentStudio | /api/python/calphad-databases (alias /api/calphad/databases) |
| lpbf-thermal-solver | lpbf_thermal_solver:calculate_meltpool_physics | MeltPool3DCrossSectionLab / 3d-distortion-lab | /api/python/lpbf-thermal-solver |
| stl-slicer-build-time | stl_slicer_build_time_solver:solve_slicer | BasicSTLSlicerLab | /api/python/stl-slicer-build-time |
| lpbf-bayesian-optimize | lpbf_bayesian_optimizer:_run_from_payload | LpbfOptimizerSearchPanel | /api/python/lpbf-bayesian-optimize |
| lpbf-calibrated-meltpool | lpbf_calibrated_meltpool:run | CalibratedMeltpoolPanel / MeltPool3DCrossSectionLab | /api/python/lpbf-calibrated-meltpool |
| lpbf-process-window | lpbf_process_window:run_process_window | LpbfProcessWindowMap / optimizer | /api/python/lpbf-process-window |
| lpbf-gr-solidification | lpbf_gr_solidification:run_gr_solidification | GrSolidificationMapCard / optimizer | /api/python/lpbf-gr-solidification |
| lpbf-machine-calibrated-meltpool | lpbf_machine_calibrated_meltpool:run | CalibratedMeltpoolPanel / useMachineDepth | /api/python/lpbf-machine-calibrated-meltpool |
| lpbf-machine-calibration-status | lpbf_machine_calibrated_meltpool:status | CalibratedMeltpoolPanel machine selector | /api/python/lpbf-machine-calibration/status |
| lpbf-research-models | lpbf_research_models:run | ResearchModelPanel / melt-pool and build-job hosts | /api/python/lpbf-research-models |
| xrd-deconvolve | xrd_peak_deconvolution:deconvolve_peak_roi / solve_williamson_hall | No mounted caller; service method deconvolveXRD only | /api/python/xrd-deconvolve |
| solidification-microstructure | lpbf_worker_rpc:_rpc_solidification_microstructure | SolidificationMicrostructureLab | /api/python/lpbf-solidification-microstructure |
| keyhole-raytracing | lpbf_keyhole_raytracing:compute_keyhole_raytracing | KeyholeRaytracingLab | /api/python/lpbf-keyhole-raytracing |
| estimate | lpbf_worker_rpc:_estimate | LpbfEngineeringSimulation | /api/lpbf/estimate |
| submit | lpbf_simulation:run | LpbfEngineeringSimulation (standard/reference CPU) | /api/lpbf/jobs |
| submit:build-job | lpbf_build_job_solver:solve_lpbf_build_job | IndustrialLPBFDecisionLab / Build rail | /api/lpbf/jobs jobType=build-job |
| submit:in625-bareplate-field | lpbf_worker:_run_in625_bareplate_job | In625BareplatePanel | /api/lpbf/jobs jobType=in625-bareplate-field |
| submit:gpu-thermal-pilot | lpbf_gpu_thermal:run_queued_pilot / lpbf_gpu_warp_pilot:run_queued_warp_pilot | GpuThermalPilotPanel | /api/lpbf/jobs jobType=gpu-thermal-pilot |
| capabilities | lpbf_worker:_capabilities_response | LpbfEngineeringSimulation / LpbfRunArchivePanel | GET /api/lpbf/capabilities |
| submit-repeat | Queue.submit(execution_scope=repeat) | LpbfEngineeringSimulation / LpbfRunArchivePanel | POST /api/lpbf/jobs/repeat |
| get | Queue.get | LpbfEngineeringSimulation / LpbfRunArchivePanel | GET /api/lpbf/jobs/:id |
| cancel | Queue.cancel | LpbfEngineeringSimulation / LpbfRunArchivePanel | DELETE /api/lpbf/jobs/:id |
| artifact | Queue.artifact | LpbfEngineeringSimulation / LpbfRunArchivePanel | GET /api/lpbf/jobs/:id/artifacts/:name |
| archive-capture | Queue.archive_capture | LpbfEngineeringSimulation / LpbfRunArchivePanel | LpbfRunArchiveService -> captureForArchive |
| nist-comparison | lpbf_nist_in718_comparison | LpbfEngineeringSimulation / LpbfRunArchivePanel | POST /api/lpbf/runs/:runId/nist-comparison (+ restored alias) |
| proxy-campaign-validation | lpbf_nist_proxy_campaign:validate_proxy_campaign | LpbfEngineeringSimulation / LpbfRunArchivePanel | POST /api/lpbf/runs/proxy-campaigns[/preview] |
| proxy-section-rederive | lpbf_nist_proxy_sections:rederive_rectangular_corridor_sections | LpbfEngineeringSimulation / LpbfRunArchivePanel | archive/campaign validation -> server/lpbfProxyCampaignBinding.ts |

Trace reviewed: routes/physics.ts, routes/characterization.ts, routes/lpbfSimulation.ts, routes/lpbfRuns.ts, routes/lpbfSources.ts; server/pythonRuntime.ts, processOrchestrator.ts, lpbfWorkerBridge.ts, lpbfNistComparisonService.ts, lpbfNistProxyCampaignService.ts, lpbfProxyCampaignBinding.ts; python/lpbf_worker.py and lpbf_worker_rpc.py; module_registry.py, module_contract*.py and generated moduleRegistry.json. Runtime selection code selects an interpreter; it does not add an engine. IPC allowlists include exactly the 10 route-dispatched script modules. Registry Python/worker authorities are covered by a self-contained parity test. Graft/codebase-memory tools were unavailable in this session; direct source review and rg were used.

RPC methods `fatigue-fracture`, `capture`, `purge-unverified-artifacts` exist internally but have no current UI/HTTP route in this checkout. They are not silently counted as served physics. archive-capture is reachable through the run archive service. `/api/python/status`, `/ipc-status`, `/ipc-warmup` return Node supervisor health only. Source archive/data-view/database operations are Node/browser readers; source measurements and static comparison overlays were not loaded. XRD has two Python modes (ROI deconvolution and Williamson–Hall), but only an unused service method, no mounted Python caller and no default spectrum; neither measured nor synthetic points were invented.

## Per-engine results

`N/S/C` = number of null scalar leaves / unavailable-like status leaves / unavailable containers. N+S is the requested leaf count; C is separately reported to avoid double-counting envelopes. Strings partial/failed/not-requested/not-evaluated and unavailable-* statuses, plus available:false containers, are retained. Counts include optional metadata, reasonCode:null, warnings and scenario bands; they are not a count of independent missing physical quantities. Wall time is the timed child computation including authority imports, excluding optional Warp setup and process startup. The raw JSON also records full process wall time and timeout budget.

### CALPHAD

Returns uniform-grid equilibrium phase fractions, thermodynamic profiles and critical-temperature blocks; Scheil is off by default. Ti fails its selected database/model construction. Missing phase temperatures and not-computed properties remain explicitly unavailable/null.

| Operation | Alloy | Variant | ok/error/skipped | Wall s | N/S/C |
| --- | --- | --- | --- | --- | --- |
| calphad-minimize | Ti-6Al-4V | default | error | 5.560 | 0/1/1 |
| calphad-minimize | AlSi10Mg | default | ok | 15.653 | 46/14/9 |
| calphad-minimize | IN718 | default | ok | 61.419 | 85/16/7 |
| calphad-minimize | 316L | default | ok | 71.884 | 55/15/8 |
| calphad-minimize | IN625 | default | skipped | 0.000 | 0/0/0 |
| calphad-databases | — | default | ok | 1.787 | 7/0/0 |

### Melt pool

Goldak analytical screening returns process indices, geometry/contours, thermal slices, hydrodynamic/recoil surrogates, defect diagnostics and source-gated solidification envelopes. Stress/distortion are null. This is not CFD or validated geometry.

| Operation | Alloy | Variant | ok/error/skipped | Wall s | N/S/C |
| --- | --- | --- | --- | --- | --- |
| lpbf-thermal-solver | Ti-6Al-4V | default | ok | 1.754 | 97/8/8 |
| lpbf-thermal-solver | AlSi10Mg | default | ok | 1.207 | 93/8/8 |
| lpbf-thermal-solver | IN718 | default | ok | 1.514 | 107/8/8 |
| lpbf-thermal-solver | 316L | default | ok | 1.572 | 100/8/8 |
| lpbf-thermal-solver | IN625 | default | ok | 1.135 | 107/8/8 |

### Slicer

Returns demo geometry/mesh metrics, part-mass estimate, VED/AED/LED, layer table and build/laser/recoat time. No null leaf does not establish correct material admission: IN625 silently falls back to IN718 properties (bug below).

| Operation | Alloy | Variant | ok/error/skipped | Wall s | N/S/C |
| --- | --- | --- | --- | --- | --- |
| stl-slicer-build-time | Ti-6Al-4V | default | ok | 0.827 | 0/0/0 |
| stl-slicer-build-time | AlSi10Mg | default | ok | 0.776 | 0/0/0 |
| stl-slicer-build-time | IN718 | default | ok | 0.751 | 0/0/0 |
| stl-slicer-build-time | 316L | default | ok | 0.751 | 0/0/0 |
| stl-slicer-build-time | IN625 | default | ok | 0.741 | 0/0/0 |

### Bayesian optimizer

Returns best parameters/verdict/score, iteration history, convergence and gate summary. Four-alloy screening objective only; IN625 is rejected.

| Operation | Alloy | Variant | ok/error/skipped | Wall s | N/S/C |
| --- | --- | --- | --- | --- | --- |
| lpbf-bayesian-optimize | Ti-6Al-4V | default | ok | 25.188 | 0/0/0 |
| lpbf-bayesian-optimize | AlSi10Mg | default | ok | 24.017 | 0/0/0 |
| lpbf-bayesian-optimize | IN718 | default | ok | 24.067 | 0/0/0 |
| lpbf-bayesian-optimize | 316L | default | ok | 24.128 | 0/0/0 |
| lpbf-bayesian-optimize | IN625 | default | error | 1.015 | 0/0/0 |

### Calibrated melt pool

Returns unchanged screening and a calibrated availability block. Artifact is stale for current implementation: calibrated width/depth remain null. Fitted artifact stores aggregate source/count/fit metadata, not measured track rows; the fit tool itself was never imported.

| Operation | Alloy | Variant | ok/error/skipped | Wall s | N/S/C |
| --- | --- | --- | --- | --- | --- |
| lpbf-calibrated-meltpool | Ti-6Al-4V | default | ok | 1.018 | 100/8/9 |
| lpbf-calibrated-meltpool | AlSi10Mg | default | ok | 0.660 | 96/8/9 |
| lpbf-calibrated-meltpool | IN718 | default | ok | 0.713 | 110/8/9 |
| lpbf-calibrated-meltpool | 316L | default | ok | 0.875 | 103/8/9 |
| lpbf-calibrated-meltpool | IN625 | default | ok | 0.606 | 110/8/9 |

### Process window

Whole operation skipped: overlay always loads measured rows for the configured alloys; no overlay-off request switch. No runtime availability claim is made for this engine.

| Operation | Alloy | Variant | ok/error/skipped | Wall s | N/S/C |
| --- | --- | --- | --- | --- | --- |
| lpbf-process-window | Ti-6Al-4V | default | skipped | 0.000 | 0/0/0 |
| lpbf-process-window | AlSi10Mg | default | skipped | 0.000 | 0/0/0 |
| lpbf-process-window | IN718 | default | skipped | 0.000 | 0/0/0 |
| lpbf-process-window | 316L | default | skipped | 0.000 | 0/0/0 |
| lpbf-process-window | IN625 | default | skipped | 0.000 | 0/0/0 |

### G/R solidification

Returns 49 cells, front G/R/cooling and microstructure envelopes, CET constants/admission views and Laves bound. Missing admitted liquidus source and additional model/domain guards prevent many outputs. IN718 CET source constants exist; LPBF class admission is still unavailable.

| Operation | Alloy | Variant | ok/error/skipped | Wall s | N/S/C |
| --- | --- | --- | --- | --- | --- |
| lpbf-gr-solidification | Ti-6Al-4V | default | ok | 2.044 | 5415/687/687 |
| lpbf-gr-solidification | AlSi10Mg | default | ok | 2.067 | 5151/687/687 |
| lpbf-gr-solidification | IN718 | default | ok | 2.088 | 5347/686/686 |
| lpbf-gr-solidification | 316L | default | ok | 2.041 | 5343/687/687 |
| lpbf-gr-solidification | IN625 | default | ok | 2.190 | 5349/687/687 |

### Machine calibration

Status reports no local artifacts in this worktree. Solve calls without a selected machineCalibration id return validation errors; this is a missing UI prerequisite, not a physics bug.

| Operation | Alloy | Variant | ok/error/skipped | Wall s | N/S/C |
| --- | --- | --- | --- | --- | --- |
| lpbf-machine-calibrated-meltpool | Ti-6Al-4V | default | error | 0.175 | 0/0/0 |
| lpbf-machine-calibrated-meltpool | AlSi10Mg | default | error | 0.144 | 0/0/0 |
| lpbf-machine-calibrated-meltpool | IN718 | default | error | 0.126 | 0/0/0 |
| lpbf-machine-calibrated-meltpool | 316L | default | error | 0.140 | 0/0/0 |
| lpbf-machine-calibrated-meltpool | IN625 | default | error | 0.137 | 0/0/0 |
| lpbf-machine-calibration-status | — | default | ok | 0.138 | 0/0/0 |

### P8 research

Returns describe availability/controls, nominal research modules and bounded scenario-band progress. Keyhole/depth chains are alloy-admitted selectively. Convention/nonapplicable/metadata nulls and pending bands must not be mistaken for missing physical models.

| Operation | Alloy | Variant | ok/error/skipped | Wall s | N/S/C |
| --- | --- | --- | --- | --- | --- |
| lpbf-research-models | Ti-6Al-4V | describe | ok | 1.264 | 130/0/0 |
| lpbf-research-models | Ti-6Al-4V | nominal | ok | 2.225 | 7022/9/1 |
| lpbf-research-models | Ti-6Al-4V | band | ok | 2.407 | 1/0/0 |
| lpbf-research-models | AlSi10Mg | describe | ok | 0.960 | 129/0/0 |
| lpbf-research-models | AlSi10Mg | nominal | ok | 2.381 | 7096/9/1 |
| lpbf-research-models | AlSi10Mg | band | ok | 2.641 | 1/0/0 |
| lpbf-research-models | IN718 | describe | ok | 1.056 | 150/3/3 |
| lpbf-research-models | IN718 | nominal | ok | 1.155 | 5945/17/3 |
| lpbf-research-models | IN718 | band | ok | 1.359 | 6329/216/3 |
| lpbf-research-models | 316L | describe | ok | 1.041 | 153/3/3 |
| lpbf-research-models | 316L | nominal | ok | 1.320 | 5919/17/3 |
| lpbf-research-models | 316L | band | ok | 1.634 | 6263/215/3 |
| lpbf-research-models | IN625 | describe | ok | 1.359 | 161/4/4 |
| lpbf-research-models | IN625 | nominal | ok | 1.837 | 5977/17/3 |
| lpbf-research-models | IN625 | band | ok | 1.981 | 6403/246/3 |

### XRD

Skipped: user ROI points/peaks required; no mounted Python consumer/default spectrum found. Do not describe browser-local XRD visuals as this Python engine having run.

| Operation | Alloy | Variant | ok/error/skipped | Wall s | N/S/C |
| --- | --- | --- | --- | --- | --- |
| xrd-deconvolve | — | default | skipped | 0.000 | 0/0/0 |

### Microstructure

Returns the thermal solver’s source-gated solidification quantities, not a separate empirical alloy fallback. G/R/cooling/PDAS/SDAS/morphology/transformation can be unavailable while transport is ok.

| Operation | Alloy | Variant | ok/error/skipped | Wall s | N/S/C |
| --- | --- | --- | --- | --- | --- |
| solidification-microstructure | Ti-6Al-4V | default | ok | 0.727 | 77/9/9 |
| solidification-microstructure | AlSi10Mg | default | ok | 0.662 | 69/9/9 |
| solidification-microstructure | IN718 | default | ok | 0.742 | 76/9/9 |
| solidification-microstructure | 316L | default | ok | 0.877 | 69/9/9 |
| solidification-microstructure | IN625 | default | ok | 0.907 | 76/9/9 |

### Keyhole optics

No result: missing optional Warp dependency in the requested CPU interpreter. Tool would explicitly request device=cpu; no GPU attempt occurred.

| Operation | Alloy | Variant | ok/error/skipped | Wall s | N/S/C |
| --- | --- | --- | --- | --- | --- |
| keyhole-raytracing | — | default | error | 0.118 | 0/0/0 |

### Job estimate

Returns CPU resource/work estimate for four alloys. IN625 is refused without a full thermophysical table; its bounded bare-plate model does not admit it to this full transient path.

| Operation | Alloy | Variant | ok/error/skipped | Wall s | N/S/C |
| --- | --- | --- | --- | --- | --- |
| estimate | Ti-6Al-4V | default | ok | 0.553 | 0/0/0 |
| estimate | AlSi10Mg | default | ok | 0.574 | 0/0/0 |
| estimate | IN718 | default | ok | 0.544 | 0/0/0 |
| estimate | 316L | default | ok | 0.680 | 0/0/0 |
| estimate | IN625 | default | error | 0.698 | 0/0/0 |

### Transient thermal

All four default vectors hit the boiling validity STOP before a result is returned; IN625 lacks a full thermophysical table. This is a deliberate model-domain stop, not evidence of a numerical/implementation bug. No clipped/evaporation surrogate was enabled.

| Operation | Alloy | Variant | ok/error/skipped | Wall s | N/S/C |
| --- | --- | --- | --- | --- | --- |
| submit | Ti-6Al-4V | default | error | 2.903 | 0/0/0 |
| submit | AlSi10Mg | default | error | 2.230 | 0/0/0 |
| submit | IN718 | default | error | 4.012 | 0/0/0 |
| submit | 316L | default | error | 2.560 | 0/0/0 |
| submit | IN625 | default | error | 0.668 | 0/0/0 |

### Build job

Four alloys return screening verdict/gates, thermal+slicer results, microstructure/segregation/kinetics, porosity index and qualification blocks. CT fatigue unavailable without user data, UQ/NIST absent by request. IN625 unsupported.

| Operation | Alloy | Variant | ok/error/skipped | Wall s | N/S/C |
| --- | --- | --- | --- | --- | --- |
| submit:build-job | Ti-6Al-4V | default | ok | 2.860 | 229/24/22 |
| submit:build-job | AlSi10Mg | default | ok | 1.684 | 219/24/22 |
| submit:build-job | IN718 | default | ok | 3.250 | 338/32/32 |
| submit:build-job | 316L | default | ok | 3.261 | 226/24/22 |
| submit:build-job | IN625 | default | error | 0.733 | 0/0/0 |

### IN625 bounded field

Returns CPU bounded enthalpy/temperature evolution, energy residual, metrics, material identity and binary field artifact descriptor. No powder, melt-pool, evaporation or full-transient admission is inferred. Temporary artifacts were deleted.

| Operation | Alloy | Variant | ok/error/skipped | Wall s | N/S/C |
| --- | --- | --- | --- | --- | --- |
| submit:in625-bareplate-field | IN625 fixed | default | ok | 0.830 | 2/0/0 |

### GPU pilot

Skipped for all identities: CUDA-only Torch/Warp pilot. CPU sweep makes no statement about GPU execution availability.

| Operation | Alloy | Variant | ok/error/skipped | Wall s | N/S/C |
| --- | --- | --- | --- | --- | --- |
| submit:gpu-thermal-pilot | Ti-6Al-4V | default | skipped | 0.000 | 0/0/0 |
| submit:gpu-thermal-pilot | AlSi10Mg | default | skipped | 0.000 | 0/0/0 |
| submit:gpu-thermal-pilot | IN718 | default | skipped | 0.000 | 0/0/0 |
| submit:gpu-thermal-pilot | 316L | default | skipped | 0.000 | 0/0/0 |
| submit:gpu-thermal-pilot | IN625 | default | skipped | 0.000 | 0/0/0 |

### Infrastructure / archive

All entries skipped: lifecycle operations need existing jobs, archive readers need captured run/NPZ/source bindings, and NIST comparison/proxy validation depend on measured source records. No existing jobs or archives were modified.

| Operation | Alloy | Variant | ok/error/skipped | Wall s | N/S/C |
| --- | --- | --- | --- | --- | --- |
| capabilities | — | default | skipped | 0.000 | 0/0/0 |
| submit-repeat | — | default | skipped | 0.000 | 0/0/0 |
| get | — | default | skipped | 0.000 | 0/0/0 |
| cancel | — | default | skipped | 0.000 | 0/0/0 |
| artifact | — | default | skipped | 0.000 | 0/0/0 |
| archive-capture | — | default | skipped | 0.000 | 0/0/0 |
| nist-comparison | — | default | skipped | 0.000 | 0/0/0 |
| proxy-campaign-validation | — | default | skipped | 0.000 | 0/0/0 |
| proxy-section-rederive | — | default | skipped | 0.000 | 0/0/0 |

## Errors and outright bugs

| Operation | Alloy | Exception / envelope class | Exact message |
| --- | --- | --- | --- |
| calphad-minimize | Ti-6Al-4V | ReturnedError | pycalphad equilibrium failed: Order (BCC_B2) and disorder (BCC_A2) model must have no interstitial sublattice or a single matching one |
| lpbf-bayesian-optimize | IN625 | ReturnedError | Unknown alloy 'in625': not resolvable by four_alloy_materials; no fallback alloy is used. |
| lpbf-machine-calibrated-meltpool | Ti-6Al-4V | ReturnedError | machineCalibration must be a machine calibration id like 'mc-0123456789ab' (see GET /api/python/lpbf-machine-calibration/status). |
| lpbf-machine-calibrated-meltpool | AlSi10Mg | ReturnedError | machineCalibration must be a machine calibration id like 'mc-0123456789ab' (see GET /api/python/lpbf-machine-calibration/status). |
| lpbf-machine-calibrated-meltpool | IN718 | ReturnedError | machineCalibration must be a machine calibration id like 'mc-0123456789ab' (see GET /api/python/lpbf-machine-calibration/status). |
| lpbf-machine-calibrated-meltpool | 316L | ReturnedError | machineCalibration must be a machine calibration id like 'mc-0123456789ab' (see GET /api/python/lpbf-machine-calibration/status). |
| lpbf-machine-calibrated-meltpool | IN625 | ReturnedError | machineCalibration must be a machine calibration id like 'mc-0123456789ab' (see GET /api/python/lpbf-machine-calibration/status). |
| keyhole-raytracing | — | ModuleNotFoundError | No module named 'warp' |
| estimate | IN625 | ValueError | Inconel 625: thermophysical data missing; supply sourced properties |
| submit | Ti-6Al-4V | ValueError | Thermal model validity exceeded at or above the material boiling limit (specific enthalpy 3023784.85 J/kg; limit 3011590 J/kg at 3560.15 K; cell=(np.int64(6), np.int64(20), np.int64(16)), previous T=3549.46 K, previous specific enthalpy=3001649.2 J/kg, dt=8.13109829e-08 s, source rate=8.55776666e+14 W/m³, net rate=6.58658627e+14 W/m³); evaporation/free-surface CFD required |
| submit | AlSi10Mg | ValueError | Thermal model validity exceeded at or above the material boiling limit (specific enthalpy 3238855.02 J/kg; limit 3231275 J/kg at 2743.15 K; cell=(np.int64(6), np.int64(20), np.int64(16)), previous T=2728.53 K, previous specific enthalpy=3214025.11 J/kg, dt=6.13620236e-08 s, source rate=1.15765158e+15 W/m³, net rate=5.79320457e+14 W/m³); evaporation/free-surface CFD required |
| submit | IN718 | ValueError | Thermal model validity exceeded at or above the material boiling limit (specific enthalpy 2166720.66 J/kg; limit 2153440 J/kg at 3123.15 K; cell=(np.int64(6), np.int64(20), np.int64(16)), previous T=3117.6 K, previous specific enthalpy=2149389.21 J/kg, dt=9.37122938e-08 s, source rate=9.99017182e+14 W/m³, net rate=8.21808406e+14 W/m³); evaporation/free-surface CFD required |
| submit | 316L | ValueError | Thermal model validity exceeded at or above the material boiling limit (specific enthalpy 2274502.1 J/kg; limit 2268920 J/kg at 3087.15 K; cell=(np.int64(6), np.int64(20), np.int64(16)), previous T=3073.73 K, previous specific enthalpy=2258450.64 J/kg, dt=1.46306633e-07 s, source rate=6.58561438e+14 W/m³, net rate=4.78643091e+14 W/m³); evaporation/free-surface CFD required |
| submit | IN625 | ValueError | Inconel 625: thermophysical data missing; supply sourced properties |
| submit:build-job | IN625 | ReturnedError | Unsupported LPBF alloy identity: 'in625'. No surrogate alloy was submitted. |

Confirmed software/data-integration defects: (1) Ti-6Al-4V CALPHAD selects a database whose BCC_B2/BCC_A2 interstitial sublattices are incompatible in pycalphad; phase-profile output is lost rather than producing a labelled estimate (calphad_solver.py resolve_database / solve_pycalphad_equilibrium). (2) stl_slicer_build_time_solver.py:348 uses `slicer_props(material) or SECONDARY_ALLOY_DB.get(material) or slicer_props("Inconel 718")`; IN625 is absent from both property lookups, so a successful IN625 direct request gets IN718 density for mass with no disclosure. The mounted slicer currently guards unsupported material identities, so this second defect is an endpoint/authority admission bug, not proof of an IN625 default UI submission. No fixes were made.

Missing Warp is a CPU environment dependency, not an algorithm bug. IN625 full-model refusals and missing machineCalibration selection are expected admission/precondition errors. Boiling-limit STOPs and stale calibration refusal are intentional honesty gates. 45 s CALPHAD timeouts are harness limits, not evidence that the authority always fails.

## Ranked unavailable outputs by user impact and blocker

| Rank | User output | Affected surface | Reason (served code or explicit prose) | Blocker classification | Prioritisation note |
| --- | --- | --- | --- | --- | --- |
| 1 | Transient temperature/history and melt geometry | All four UI presets; IN625 additionally lacks table | ValueError boiling-limit STOP; IN625 thermophysical data missing | MODEL / MATERIAL DOMAIN | An estimate requires an explicit bounded evaporation/free-surface surrogate or changed admitted use case; do not remove STOP or use another alloy. |
| 2 | Residual stress and distortionIndex | Thermal specialist + Build decision | stressUnavailableReason: no sourced stress model; no structured code | MODEL | Need thermomechanical constitutive/history/boundary model; a yield constant alone is insufficient. |
| 3 | Ti-6Al-4V CALPHAD equilibriumProfile / phase temperatures | Phase diagram | pycalphad-equilibrium-failed; BCC_B2/BCC_A2 sublattice mismatch | BUG / DATABASE INTEGRATION | Fix compatible phase/database admission and retain model provenance; do not substitute a heuristic profile silently. |
| 4 | G, R, coolingRate and G/R | Melt pool, microstructure, G/R map, Build job | missing-source-constant (liquidus_K) + parent-unavailable; some vectors also keyhole-field-inconsistent | SOURCE CONSTANT ONLY for isolated liquidus gate; otherwise MODEL DOMAIN too | Fastest bounded estimate candidate: label/admit sourced or explicitly estimated liquidus for the matching model. Inspect each independent keyhole guard; a constant does not repair that field. |
| 5 | PDAS, SDAS and morphology | Microstructure / G/R / Build job | missing-source-bound-model + unavailable parents | MODEL plus source/admission | Need alloy/domain-specific spacing/morphology closure. Do not treat all of these as a missing scalar; inspect existing Hunt–Lu source range separately. |
| 6 | CET class / equiaxed transition boundary | G/R map | outside-source-model-domain; no CET registry entry / IN625 no sourced constants (prose) | MODEL DOMAIN; some alloys SOURCE SET | IN718 has sourced sets for other process domains, not an admitted LPBF prediction. IN625 needs a,n,N0 plus process applicability; copying CMSX-4 is not a fix. |
| 7 | Fatigue limit / extreme-defect distribution | Build decision Murakami block | data_not_supplied; null fatigueLimit_MPa, gumbel, CT threshold; no structured reason code | MISSING USER INPUT | Require CT/defect sqrt-area and justified hardness; an explicitly assumed defect scenario can be labelled as such, never measured fatigue qualification. |
| 8 | Solid-state transformation / kinetics | Build decision + microstructure | missing-thermal-history and missing-source-bound-model | MODEL / HISTORY | Supply eligible thermal history and same-alloy kinetics; current 316L/AlSi10Mg cannot reuse steel/7075 models. |
| 9 | Calibrated width/depth and machine depth | Calibration panels | calibration stale for this physics version; machineCalibration id missing | STALE FIT / INPUT | Refresh/verify the fit independently; this sweep does not fit measured rows. Default machine selector has no local artifact. Not a missing source constant. |
| 10 | P8 physical wall T/recoil/keyhole-flow and research depth chains; ray paths | ResearchModelPanel / KeyholeRaytracingLab | KEYHOLE_THERMAL_FLOW_CLOSURE_UNAVAILABLE, SURFACE_BALANCE_CLOSURE_FALSIFIED, ALLOY_CONSTANT_CHAIN_NOT_ADMITTED; ray paths: ModuleNotFoundError warp | MODEL; SOURCE CHAIN; DEPENDENCY | Falsified closure needs replacement; unadmitted chains need full source/range checks. Warp CPU installation is a separate environment fix, not a new physics model. |

Additional narrow source/input opportunities: P8 `SURFACE_VAPOUR_INPUT_REQUIRED` (vapour triple), `MARANGONI_VISCOSITY_INPUT_REQUIRED` (IN625 viscosity), and `POWDER_ALLOY_OPTICAL_CONSTANTS_UNAVAILABLE` (alloy/lot optics). The viscosity leaf can be a sourced scalar unblock; an admitted transport field or actual powder thermal operator still needs a model. `NOT_APPLICABLE_FOR_CONVENTION`, `ALLOY_NOT_ALSI10MG`, `BAND_PENDING`, `BAND_MANIFEST_NOT_DECLARED`, `not-requested` and absent phases are not automatically estimate backlog items.

## Observed reason-code groups

| Reason code | Affected operations | Alloys | N + container occurrences (not independent outputs) | Representative exact output-path pattern |
| --- | --- | --- | --- | --- |
| BAND_PENDING | lpbf-research-models | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | 21602 | $.researchModels.marangoni.band.manifest[*].onsetEvent; $.researchModels.marangoni.band.fields.length_m.maxArmId; $.researchModels.marangoni.band.fields.length_m.minArmId |
| missing-source-constant | lpbf-calibrated-meltpool, lpbf-gr-solidification, lpbf-thermal-solver, solidification-microstructure, submit:build-job | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | 19510 | $.quantities.pdas; $.quantities.sdas; $.quantities.gOverR |
| ALLOY_CONSTANT_CHAIN_NOT_ADMITTED | lpbf-research-models | 316L, IN625, IN718 | 15870 | $.researchModels.keyholeCavity; $.researchModels.meltDepthLink; $.moduleAvailability.keyholeCavity |
| parent-unavailable | lpbf-calibrated-meltpool, lpbf-gr-solidification, lpbf-thermal-solver, solidification-microstructure, submit:build-job | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | 12027 | $.quantities.pdas; $.quantities.sdas; $.quantities.gOverR |
| keyhole-field-inconsistent | lpbf-calibrated-meltpool, lpbf-gr-solidification, lpbf-thermal-solver, solidification-microstructure, submit:build-job | 316L, IN625, IN718, Ti-6Al-4V | 10094 | $.quantities.pdas; $.quantities.sdas; $.quantities.gOverR |
| missing-source-bound-model | lpbf-calibrated-meltpool, lpbf-gr-solidification, lpbf-thermal-solver, solidification-microstructure, submit:build-job | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | 9448 | $.quantities.pdas; $.quantities.sdas; $.quantities.morphology |
| BAND_MANIFEST_NOT_DECLARED | lpbf-research-models | 316L, IN625, IN718 | 6894 | $.researchModels.keyholeCavity.band.fields.alloy.maxArmId; $.researchModels.keyholeCavity.band.fields.alloy.minArmId; $.researchModels.keyholeCavity.band.fields.roots.maxArmId |
| ALLOY_NOT_ALSI10MG | lpbf-research-models | 316L, IN625, IN718, Ti-6Al-4V | 5971 | $.researchModels.alSi10MgVapourMgAware.fields.source.value; $.researchModels.alSi10MgIndexDisclosure.fields.basis.value; $.researchModels.alSi10MgIndexDisclosure.fields.decision.value |
| NOT_APPLICABLE_FOR_CONVENTION | lpbf-research-models | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | 3419 | $.researchModels.marangoni.fields.solubleOxygen_ppm.value; $.researchModels.marangoni.fields.solubleSulfur_ppm.value; $.researchModels.marangoni.consistencyNote.reasons[*].value |
| SURFACE_VAPOUR_INPUT_REQUIRED | lpbf-research-models | 316L, IN625, IN718 | 3046 | $.moduleAvailability.surfaceBalance; $.researchModels.surfaceBalance.fields.iterations.value; $.researchModels.surfaceBalance.fields.iterations.band.maxArmId |
| missing-thermal-history | lpbf-calibrated-meltpool, lpbf-gr-solidification, lpbf-thermal-solver, solidification-microstructure, submit:build-job | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | 2862 | $.kinetics; $.kinetics.alloy; $.kinetics.coolingRateSource |
| outside-source-model-domain | lpbf-gr-solidification | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | 2450 | $.cells[*].cet.quantities.class; $.cells[*].cet.quantities.class.value; $.cells[*].cet.quantities.class.validity |
| BAND_NO_SUCCESSFUL_ARM | lpbf-research-models | 316L, IN625, IN718 | 1908 | $.researchModels.marangoni.band.fields.liquidPrandtl.maxArmId; $.researchModels.marangoni.band.fields.liquidPrandtl.minArmId; $.researchModels.marangoni.fields.liquidPrandtl.band.maxArmId |
| ONSET_REFERENCE_UNAVAILABLE | lpbf-research-models | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | 1261 | $.researchModels.marangoni.consistencyNote.validRange.peclet.value; $.researchModels.keyholeCavity.consistencyNote.validRange.peclet.value; $.researchModels.marangoni.consistencyNote.onsetMismatch.comparedArmId |
| MARANGONI_VISCOSITY_INPUT_REQUIRED | lpbf-research-models | IN625 | 743 | $.moduleAvailability.marangoni; $.researchModels.marangoni.fields.liquidPrandtl.value; $.researchModels.marangoni.fields.viscosity_Pa_s.value |
| KEYHOLE_THERMAL_FLOW_CLOSURE_UNAVAILABLE | lpbf-research-models | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | 656 | $.researchModels.unavailablePhysics.consistencyNote.reasons[*].value; $.researchModels.unavailablePhysics.consistencyNote.reasons[*].limitMax; $.researchModels.unavailablePhysics.consistencyNote.reasons[*].limitMin |
| SURFACE_BALANCE_CLOSURE_FALSIFIED | lpbf-research-models | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | 656 | $.researchModels.unavailablePhysics.consistencyNote.reasons[*].value; $.researchModels.unavailablePhysics.consistencyNote.reasons[*].limitMax; $.researchModels.unavailablePhysics.consistencyNote.reasons[*].limitMin |
| MARANGONI_SURFACE_CHEMISTRY_UNAVAILABLE | lpbf-research-models | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | 648 | $.researchModels.unavailablePhysics.consistencyNote.reasons[*].value; $.researchModels.unavailablePhysics.consistencyNote.reasons[*].limitMax; $.researchModels.unavailablePhysics.consistencyNote.reasons[*].limitMin |
| POWDER_ALLOY_OPTICAL_CONSTANTS_UNAVAILABLE | lpbf-research-models | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | 648 | $.researchModels.unavailablePhysics.fields.powderAbsorptance.value; $.researchModels.unavailablePhysics.consistencyNote.reasons[*].value; $.researchModels.unavailablePhysics.consistencyNote.reasons[*].limitMax |
| SOURCE_RANGE_NOT_ESTABLISHED | lpbf-research-models | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | 454 | $.researchModels.marangoni.consistencyNote.validRange.temperatureRanges[*].sourceRange_K.value; $.researchModels.keyholeCavity.consistencyNote.validRange.temperatureRanges[*].sourceRange_K.value; $.researchModels.meltDepthLink.consistencyNote.validRange.temperatureRanges[*].sourceRange_K.value |
| not-requested | submit:build-job | 316L, AlSi10Mg, Ti-6Al-4V | 90 | $.segregation; $.segregation.reasons[*].parent; $.segregation.quantities.phaseInventory |
| VAPOUR_PRESSURE_OUTSIDE_SOURCE_RANGE | lpbf-research-models | AlSi10Mg | 61 | $.researchModels.alSi10MgVapourMgAware.consistencyNote.reasons[*].value; $.researchModels.alSi10MgVapourMgAware.consistencyNote.sentence.reasonCode; $.researchModels.alSi10MgVapourMgAware.consistencyNote.validRange.peclet.value |

Counts include inherited reasons, repeated map cells and scenario envelopes; one field can have several blockers. No new reason codes were inserted into served output. Prose-only reasons (stress, calibration stale, absent phase, CET registry) and unreasoned optional nulls remain prose/unknown rather than fabricated codes.

## Physical output leaf index

This compact index keeps user-facing quantity values and status leaves; P8 scenario-band internals and metadata are summarised in the reason groups above. Numeric indices are collapsed to [*]. Raw JSON retains every exact leaf, including all omitted metadata/band leaves, with complete per-call reason contexts. N is occurrences across calls, not independent physical outputs.

### calphad-minimize

| Leaf path pattern | Occurrences | Alloys | Reason codes (empty = prose-only or undisclosed) |
| --- | --- | --- | --- |
| $.criticalTemperatureStatus.betaTransusC.status | 3 | 316L, AlSi10Mg, IN718 | — |
| $.criticalTemperatureStatus.carbidePrecipitationC.status | 3 | 316L, AlSi10Mg, IN718 | — |
| $.criticalTemperatureStatus.deltaSolvusC.status | 3 | 316L, AlSi10Mg, IN718 | — |
| $.criticalTemperatureStatus.gammaDoublePrimeSolvusC.status | 3 | 316L, AlSi10Mg, IN718 | — |
| $.criticalTemperatureStatus.gammaPrimeSolvusC.status | 3 | 316L, AlSi10Mg, IN718 | — |
| $.criticalTemperatureStatus.tcpSigmaRiskTemperatureC.status | 1 | AlSi10Mg | — |
| $.criticalTemperatures.betaTransusC | 3 | 316L, AlSi10Mg, IN718 | — |
| $.criticalTemperatures.carbidePrecipitationC | 3 | 316L, AlSi10Mg, IN718 | — |
| $.criticalTemperatures.deltaSolvusC | 3 | 316L, AlSi10Mg, IN718 | — |
| $.criticalTemperatures.gammaDoublePrimeSolvusC | 3 | 316L, AlSi10Mg, IN718 | — |
| $.criticalTemperatures.gammaPrimeSolvusC | 3 | 316L, AlSi10Mg, IN718 | — |
| $.criticalTemperatures.tcpSigmaRiskTemperatureC | 1 | AlSi10Mg | — |
| $.literatureSolidification.kSensitivity | 1 | IN718 | — |
| $.literatureSolidification.quantities.maxBinary.identity.input | 1 | IN718 | — |
| $.literatureSolidification.quantities.maxBinary.validity | 1 | IN718 | — |
| $.literatureSolidification.quantities.maxTernary.identity.input | 1 | IN718 | — |
| $.literatureSolidification.quantities.maxTernary.validity | 1 | IN718 | — |
| $.literatureSolidification.quantities.minBinary.identity.input | 1 | IN718 | — |
| $.literatureSolidification.quantities.minBinary.validity | 1 | IN718 | — |
| $.literatureSolidification.quantities.minTernary.identity.input | 1 | IN718 | — |
| $.literatureSolidification.quantities.minTernary.validity | 1 | IN718 | — |
| $.literatureSolidification.quantities.nominalBinary.identity.input | 1 | IN718 | — |
| $.literatureSolidification.quantities.nominalBinary.validity | 1 | IN718 | — |
| $.literatureSolidification.quantities.nominalTernary.identity.input | 1 | IN718 | — |
| $.literatureSolidification.quantities.nominalTernary.validity | 1 | IN718 | — |
| $.literatureSolidification.secondarySource | 1 | IN718 | — |
| $.multiElementScheilStatus | 3 | 316L, AlSi10Mg, IN718 | — |
| $.phacompAnalysis.compositionBasis | 2 | 316L, AlSi10Mg | — |
| $.phacompAnalysis.criticalMd | 2 | 316L, AlSi10Mg | — |
| $.phacompAnalysis.excludedElements | 2 | 316L, AlSi10Mg | — |
| $.phacompAnalysis.m_d_bar | 2 | 316L, AlSi10Mg | — |
| $.phacompAnalysis.n_v_bar | 2 | 316L, AlSi10Mg | — |
| $.phacompAnalysis.nvNote | 2 | 316L, AlSi10Mg | — |
| $.phacompAnalysis.riskBasis | 2 | 316L, AlSi10Mg | — |
| $.phacompAnalysis.sources | 2 | 316L, AlSi10Mg | — |
| $.phacompAnalysis.status | 2 | 316L, AlSi10Mg | — |
| $.phacompAnalysis.tcpEmbrittlementRisk | 2 | 316L, AlSi10Mg | — |
| $.phacompAnalysis.tcpSigmaRiskTemperatureC | 3 | 316L, AlSi10Mg, IN718 | — |
| $.phacompAnalysis.tcpSigmaRiskTemperatureReason | 2 | 316L, AlSi10Mg | — |
| $.phacompAnalysis.thermodynamicStabilityIndex | 3 | 316L, AlSi10Mg, IN718 | — |
| $.phacompAnalysis.thermodynamicStabilityIndexReason | 2 | 316L, AlSi10Mg | — |
| $.scheilSolidification.status | 3 | 316L, AlSi10Mg, IN718 | — |
| $.solutePartitioning[*].partitionCoefficientSource | 21 | 316L, AlSi10Mg, IN718 | — |
| $.solutePartitioning[*].partitionCoefficient_k | 21 | 316L, AlSi10Mg, IN718 | — |
| $.solutePartitioning[*].primarySolidPhase | 21 | 316L, AlSi10Mg, IN718 | — |
| $.solutePartitioning[*].role | 21 | 316L, AlSi10Mg, IN718 | — |
| $.solutePartitioning[*].temperatureC | 21 | 316L, AlSi10Mg, IN718 | — |
| $.status | 1 | Ti-6Al-4V | — |
| $.tcpEmbrittlementRisk | 2 | 316L, AlSi10Mg | — |
| $.thermodynamicStabilityIndex | 3 | 316L, AlSi10Mg, IN718 | — |

### calphad-databases

| Leaf path pattern | Occurrences | Alloys | Reason codes (empty = prose-only or undisclosed) |
| --- | --- | --- | --- |
| $.databases[*].statusReason | 6 | — | — |
| $.unavailableReason | 1 | — | — |

### lpbf-thermal-solver

| Leaf path pattern | Occurrences | Alloys | Reason codes (empty = prose-only or undisclosed) |
| --- | --- | --- | --- |
| $.defectDiagnostics.ballingScreen.highThreshold | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | — |
| $.defectDiagnostics.distortionIndex | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | — |
| $.defectDiagnostics.effectiveResidualStress_MPa | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | — |
| $.geometricDefectScreen.balling.screen.highThreshold | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | — |
| $.geometricDefectScreen.gasPore.risk | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | — |
| $.geometricDefectScreen.keyhole.risk | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | — |
| $.geometricDefectScreen.porosity.value | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | — |
| $.hydrodynamicsAndRecoil.knudsenRecoilPressure_kPa | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | — |
| $.hydrodynamicsAndRecoil.marangoniNumber | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | — |
| $.hydrodynamicsAndRecoil.peakExceedsVaporization | 3 | AlSi10Mg, IN625, IN718 | — |
| $.hydrodynamicsAndRecoil.peakLocation_x_um | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | — |
| $.hydrodynamicsAndRecoil.peakTemperature_C | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | — |
| $.hydrodynamicsAndRecoil.powderDenudationWidth_um | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | — |
| $.hydrodynamicsAndRecoil.recoilOnsetStatus | 3 | AlSi10Mg, IN625, IN718 | — |
| $.hydrodynamicsAndRecoil.recoilOnsetUnavailableReason | 2 | 316L, Ti-6Al-4V | — |
| $.hydrodynamicsAndRecoil.surfaceTemperature_C | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | — |
| $.hydrodynamicsAndRecoil.vaporTemperatureDoi | 3 | AlSi10Mg, IN625, IN718 | — |
| $.hydrodynamicsAndRecoil.vaporTemperatureSource | 3 | AlSi10Mg, IN625, IN718 | — |
| $.hydrodynamicsAndRecoil.vaporTemperatureSourced_C | 3 | AlSi10Mg, IN625, IN718 | — |
| $.hydrodynamicsAndRecoil.vaporTemperatureSourced_K | 3 | AlSi10Mg, IN625, IN718 | — |
| $.hydrodynamicsAndRecoil.vaporTemperatureUnavailableReason | 2 | 316L, Ti-6Al-4V | — |
| $.marangoniModel.doi | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | — |
| $.marangoniModel.pecletMarangoni | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | — |
| $.marangoniModel.surfaceVelocity_m_s | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | — |
| $.meltPoolGeometry.axialFieldMaximum_C | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | — |
| $.meltPoolGeometry.extentNote | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | — |
| $.processParameters.kernelLedgerSha256 | 3 | 316L, IN625, IN718 | — |
| $.processWindowMap.grid[*].depth_um | 11 | 316L, IN625, IN718 | — |
| $.processWindowMap.grid[*].width_um | 11 | 316L, IN625, IN718 | — |
| $.solidificationKinetics.quantities.coolingRate.fractionBasis | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.solidificationKinetics.quantities.coolingRate.identity.input | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.solidificationKinetics.quantities.coolingRate.status | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.solidificationKinetics.quantities.coolingRate.validity | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.solidificationKinetics.quantities.coolingRate.value | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.solidificationKinetics.quantities.gOverR.fractionBasis | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.solidificationKinetics.quantities.gOverR.identity.input | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.solidificationKinetics.quantities.gOverR.status | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.solidificationKinetics.quantities.gOverR.validity | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.solidificationKinetics.quantities.gOverR.value | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.solidificationKinetics.quantities.morphology.fractionBasis | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant |
| $.solidificationKinetics.quantities.morphology.identity.input | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant |
| $.solidificationKinetics.quantities.morphology.status | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant |
| $.solidificationKinetics.quantities.morphology.validity | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant |
| $.solidificationKinetics.quantities.morphology.value | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant |
| $.solidificationKinetics.quantities.normalSpeed.fractionBasis | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.solidificationKinetics.quantities.normalSpeed.identity.input | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.solidificationKinetics.quantities.normalSpeed.status | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.solidificationKinetics.quantities.normalSpeed.validity | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.solidificationKinetics.quantities.normalSpeed.value | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.solidificationKinetics.quantities.pdas.fractionBasis | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.solidificationKinetics.quantities.pdas.identity.input | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.solidificationKinetics.quantities.pdas.status | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.solidificationKinetics.quantities.pdas.validity | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.solidificationKinetics.quantities.pdas.value | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.solidificationKinetics.quantities.sdas.fractionBasis | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.solidificationKinetics.quantities.sdas.identity.input | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.solidificationKinetics.quantities.sdas.status | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.solidificationKinetics.quantities.sdas.validity | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.solidificationKinetics.quantities.sdas.value | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.solidificationKinetics.quantities.solidStateTransformation.fractionBasis | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, missing-thermal-history |
| $.solidificationKinetics.quantities.solidStateTransformation.identity.input | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, missing-thermal-history |
| $.solidificationKinetics.quantities.solidStateTransformation.status | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, missing-thermal-history |
| $.solidificationKinetics.quantities.solidStateTransformation.validity | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, missing-thermal-history |
| $.solidificationKinetics.quantities.solidStateTransformation.value | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, missing-thermal-history |
| $.solidificationKinetics.quantities.thermalGradient.fractionBasis | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.solidificationKinetics.quantities.thermalGradient.identity.input | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.solidificationKinetics.quantities.thermalGradient.status | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.solidificationKinetics.quantities.thermalGradient.validity | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.solidificationKinetics.quantities.thermalGradient.value | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |

### stl-slicer-build-time

No physical null/status leaf retained in this compact index (see counts/errors and raw JSON).

### lpbf-bayesian-optimize

No physical null/status leaf retained in this compact index (see counts/errors and raw JSON).

### lpbf-calibrated-meltpool

| Leaf path pattern | Occurrences | Alloys | Reason codes (empty = prose-only or undisclosed) |
| --- | --- | --- | --- |
| $.calibrated.depth_um | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | — |
| $.calibrated.width_um | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | — |
| $.calibration | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | — |
| $.screening.defectDiagnostics.ballingScreen.highThreshold | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | — |
| $.screening.defectDiagnostics.distortionIndex | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | — |
| $.screening.defectDiagnostics.effectiveResidualStress_MPa | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | — |
| $.screening.geometricDefectScreen.balling.screen.highThreshold | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | — |
| $.screening.geometricDefectScreen.gasPore.risk | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | — |
| $.screening.geometricDefectScreen.keyhole.risk | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | — |
| $.screening.geometricDefectScreen.porosity.value | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | — |
| $.screening.hydrodynamicsAndRecoil.knudsenRecoilPressure_kPa | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | — |
| $.screening.hydrodynamicsAndRecoil.marangoniNumber | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | — |
| $.screening.hydrodynamicsAndRecoil.peakExceedsVaporization | 3 | AlSi10Mg, IN625, IN718 | — |
| $.screening.hydrodynamicsAndRecoil.peakLocation_x_um | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | — |
| $.screening.hydrodynamicsAndRecoil.peakTemperature_C | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | — |
| $.screening.hydrodynamicsAndRecoil.powderDenudationWidth_um | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | — |
| $.screening.hydrodynamicsAndRecoil.recoilOnsetStatus | 3 | AlSi10Mg, IN625, IN718 | — |
| $.screening.hydrodynamicsAndRecoil.recoilOnsetUnavailableReason | 2 | 316L, Ti-6Al-4V | — |
| $.screening.hydrodynamicsAndRecoil.surfaceTemperature_C | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | — |
| $.screening.hydrodynamicsAndRecoil.vaporTemperatureDoi | 3 | AlSi10Mg, IN625, IN718 | — |
| $.screening.hydrodynamicsAndRecoil.vaporTemperatureSource | 3 | AlSi10Mg, IN625, IN718 | — |
| $.screening.hydrodynamicsAndRecoil.vaporTemperatureSourced_C | 3 | AlSi10Mg, IN625, IN718 | — |
| $.screening.hydrodynamicsAndRecoil.vaporTemperatureSourced_K | 3 | AlSi10Mg, IN625, IN718 | — |
| $.screening.hydrodynamicsAndRecoil.vaporTemperatureUnavailableReason | 2 | 316L, Ti-6Al-4V | — |
| $.screening.marangoniModel.doi | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | — |
| $.screening.marangoniModel.pecletMarangoni | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | — |
| $.screening.marangoniModel.surfaceVelocity_m_s | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | — |
| $.screening.meltPoolGeometry.axialFieldMaximum_C | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | — |
| $.screening.meltPoolGeometry.extentNote | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | — |
| $.screening.processParameters.kernelLedgerSha256 | 3 | 316L, IN625, IN718 | — |
| $.screening.processWindowMap.grid[*].depth_um | 11 | 316L, IN625, IN718 | — |
| $.screening.processWindowMap.grid[*].width_um | 11 | 316L, IN625, IN718 | — |
| $.screening.solidificationKinetics.quantities.coolingRate.fractionBasis | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.screening.solidificationKinetics.quantities.coolingRate.identity.input | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.screening.solidificationKinetics.quantities.coolingRate.status | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.screening.solidificationKinetics.quantities.coolingRate.validity | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.screening.solidificationKinetics.quantities.coolingRate.value | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.screening.solidificationKinetics.quantities.gOverR.fractionBasis | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.screening.solidificationKinetics.quantities.gOverR.identity.input | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.screening.solidificationKinetics.quantities.gOverR.status | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.screening.solidificationKinetics.quantities.gOverR.validity | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.screening.solidificationKinetics.quantities.gOverR.value | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.screening.solidificationKinetics.quantities.morphology.fractionBasis | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant |
| $.screening.solidificationKinetics.quantities.morphology.identity.input | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant |
| $.screening.solidificationKinetics.quantities.morphology.status | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant |
| $.screening.solidificationKinetics.quantities.morphology.validity | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant |
| $.screening.solidificationKinetics.quantities.morphology.value | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant |
| $.screening.solidificationKinetics.quantities.normalSpeed.fractionBasis | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.screening.solidificationKinetics.quantities.normalSpeed.identity.input | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.screening.solidificationKinetics.quantities.normalSpeed.status | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.screening.solidificationKinetics.quantities.normalSpeed.validity | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.screening.solidificationKinetics.quantities.normalSpeed.value | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.screening.solidificationKinetics.quantities.pdas.fractionBasis | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.screening.solidificationKinetics.quantities.pdas.identity.input | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.screening.solidificationKinetics.quantities.pdas.status | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.screening.solidificationKinetics.quantities.pdas.validity | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.screening.solidificationKinetics.quantities.pdas.value | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.screening.solidificationKinetics.quantities.sdas.fractionBasis | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.screening.solidificationKinetics.quantities.sdas.identity.input | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.screening.solidificationKinetics.quantities.sdas.status | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.screening.solidificationKinetics.quantities.sdas.validity | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.screening.solidificationKinetics.quantities.sdas.value | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.screening.solidificationKinetics.quantities.solidStateTransformation.fractionBasis | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, missing-thermal-history |
| $.screening.solidificationKinetics.quantities.solidStateTransformation.identity.input | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, missing-thermal-history |
| $.screening.solidificationKinetics.quantities.solidStateTransformation.status | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, missing-thermal-history |
| $.screening.solidificationKinetics.quantities.solidStateTransformation.validity | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, missing-thermal-history |
| $.screening.solidificationKinetics.quantities.solidStateTransformation.value | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, missing-thermal-history |
| $.screening.solidificationKinetics.quantities.thermalGradient.fractionBasis | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.screening.solidificationKinetics.quantities.thermalGradient.identity.input | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.screening.solidificationKinetics.quantities.thermalGradient.status | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.screening.solidificationKinetics.quantities.thermalGradient.validity | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.screening.solidificationKinetics.quantities.thermalGradient.value | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |

### lpbf-gr-solidification

| Leaf path pattern | Occurrences | Alloys | Reason codes (empty = prose-only or undisclosed) |
| --- | --- | --- | --- |
| $.cells[*].cet.quantities.class.fractionBasis | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | outside-source-model-domain |
| $.cells[*].cet.quantities.class.identity.input | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | outside-source-model-domain |
| $.cells[*].cet.quantities.class.identity.model | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | outside-source-model-domain |
| $.cells[*].cet.quantities.class.status | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | outside-source-model-domain |
| $.cells[*].cet.quantities.class.validity | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | outside-source-model-domain |
| $.cells[*].cet.quantities.class.value | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | outside-source-model-domain |
| $.cells[*].cet.status | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | — |
| $.cells[*].front.quantities.coolingRate.fractionBasis | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.cells[*].front.quantities.coolingRate.identity.input | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.cells[*].front.quantities.coolingRate.status | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.cells[*].front.quantities.coolingRate.validity | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.cells[*].front.quantities.coolingRate.value | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.cells[*].front.quantities.gOverR.fractionBasis | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.cells[*].front.quantities.gOverR.identity.input | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.cells[*].front.quantities.gOverR.status | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.cells[*].front.quantities.gOverR.validity | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.cells[*].front.quantities.gOverR.value | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.cells[*].front.quantities.morphology.fractionBasis | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant |
| $.cells[*].front.quantities.morphology.identity.input | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant |
| $.cells[*].front.quantities.morphology.status | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant |
| $.cells[*].front.quantities.morphology.validity | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant |
| $.cells[*].front.quantities.morphology.value | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant |
| $.cells[*].front.quantities.normalSpeed.fractionBasis | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.cells[*].front.quantities.normalSpeed.identity.input | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.cells[*].front.quantities.normalSpeed.status | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.cells[*].front.quantities.normalSpeed.validity | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.cells[*].front.quantities.normalSpeed.value | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.cells[*].front.quantities.pdas.fractionBasis | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.cells[*].front.quantities.pdas.identity.input | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.cells[*].front.quantities.pdas.status | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.cells[*].front.quantities.pdas.validity | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.cells[*].front.quantities.pdas.value | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.cells[*].front.quantities.sdas.fractionBasis | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.cells[*].front.quantities.sdas.identity.input | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.cells[*].front.quantities.sdas.status | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.cells[*].front.quantities.sdas.validity | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.cells[*].front.quantities.sdas.value | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.cells[*].front.quantities.solidStateTransformation.fractionBasis | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, missing-thermal-history |
| $.cells[*].front.quantities.solidStateTransformation.identity.input | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, missing-thermal-history |
| $.cells[*].front.quantities.solidStateTransformation.status | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, missing-thermal-history |
| $.cells[*].front.quantities.solidStateTransformation.validity | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, missing-thermal-history |
| $.cells[*].front.quantities.solidStateTransformation.value | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, missing-thermal-history |
| $.cells[*].front.quantities.thermalGradient.fractionBasis | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.cells[*].front.quantities.thermalGradient.identity.input | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.cells[*].front.quantities.thermalGradient.status | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.cells[*].front.quantities.thermalGradient.validity | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.cells[*].front.quantities.thermalGradient.value | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.cells[*].front.status | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | — |
| $.cells[*].laves.quantities.fraction.fractionBasis | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | parent-unavailable |
| $.cells[*].laves.quantities.fraction.identity.input | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | parent-unavailable |
| $.cells[*].laves.quantities.fraction.identity.model | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | parent-unavailable |
| $.cells[*].laves.quantities.fraction.status | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | parent-unavailable |
| $.cells[*].laves.quantities.fraction.validity | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | parent-unavailable |
| $.cells[*].laves.quantities.fraction.value | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | parent-unavailable |
| $.cells[*].laves.status | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | — |
| $.cells[*].status | 245 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | — |
| $.cet.sourceChecks.algebraReproduced.test | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | — |
| $.cet.sourceChecks.equationRead.locator | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | — |
| $.cet.sourceChecks.printedLimitComparison.computed | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | — |
| $.cet.sourceChecks.printedLimitComparison.printed | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | — |
| $.cet.sourceChecks.printedLimitComparison.tolerance | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | — |
| $.materialEvidence | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | — |

### lpbf-machine-calibrated-meltpool

No physical null/status leaf retained in this compact index (see counts/errors and raw JSON).

### lpbf-machine-calibration-status

No physical null/status leaf retained in this compact index (see counts/errors and raw JSON).

### lpbf-research-models

| Leaf path pattern | Occurrences | Alloys | Reason codes (empty = prose-only or undisclosed) |
| --- | --- | --- | --- |
| $.researchModels.alSi10MgIndexDisclosure.fields.basis.value | 7 | 316L, IN625, IN718, Ti-6Al-4V | ALLOY_NOT_ALSI10MG |
| $.researchModels.alSi10MgIndexDisclosure.fields.classificationChanged.value | 7 | 316L, IN625, IN718, Ti-6Al-4V | ALLOY_NOT_ALSI10MG |
| $.researchModels.alSi10MgIndexDisclosure.fields.decision.value | 7 | 316L, IN625, IN718, Ti-6Al-4V | ALLOY_NOT_ALSI10MG |
| $.researchModels.alSi10MgIndexDisclosure.fields.indexAbsorptance.value | 7 | 316L, IN625, IN718, Ti-6Al-4V | ALLOY_NOT_ALSI10MG |
| $.researchModels.alSi10MgIndexDisclosure.fields.physicalAbsorptance.value | 7 | 316L, IN625, IN718, Ti-6Al-4V | ALLOY_NOT_ALSI10MG |
| $.researchModels.alSi10MgIndexDisclosure.fields.physicalToIndexRatio.value | 7 | 316L, IN625, IN718, Ti-6Al-4V | ALLOY_NOT_ALSI10MG |
| $.researchModels.alSi10MgVapourMgAware.fields.calculationStatus.value | 7 | 316L, IN625, IN718, Ti-6Al-4V | ALLOY_NOT_ALSI10MG |
| $.researchModels.alSi10MgVapourMgAware.fields.composition_wt_pct.value | 7 | 316L, IN625, IN718, Ti-6Al-4V | ALLOY_NOT_ALSI10MG |
| $.researchModels.alSi10MgVapourMgAware.fields.dynamicVapourTemperature_K.value | 8 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | ALLOY_NOT_ALSI10MG, VAPOUR_PRESSURE_OUTSIDE_SOURCE_RANGE |
| $.researchModels.alSi10MgVapourMgAware.fields.pressureRoute.value | 7 | 316L, IN625, IN718, Ti-6Al-4V | ALLOY_NOT_ALSI10MG |
| $.researchModels.alSi10MgVapourMgAware.fields.pureMgPressure_atm.value | 7 | 316L, IN625, IN718, Ti-6Al-4V | ALLOY_NOT_ALSI10MG |
| $.researchModels.alSi10MgVapourMgAware.fields.scenarioLatentHeatLocalSlope_J_kg.value | 7 | 316L, IN625, IN718, Ti-6Al-4V | ALLOY_NOT_ALSI10MG |
| $.researchModels.alSi10MgVapourMgAware.fields.scenarioLatentHeatTableWeighted_J_kg.value | 7 | 316L, IN625, IN718, Ti-6Al-4V | ALLOY_NOT_ALSI10MG |
| $.researchModels.alSi10MgVapourMgAware.fields.scenarioMolarMass_kg_mol.value | 7 | 316L, IN625, IN718, Ti-6Al-4V | ALLOY_NOT_ALSI10MG |
| $.researchModels.alSi10MgVapourMgAware.fields.scenarioTemperature_K.value | 7 | 316L, IN625, IN718, Ti-6Al-4V | ALLOY_NOT_ALSI10MG |
| $.researchModels.alSi10MgVapourMgAware.fields.source.value | 7 | 316L, IN625, IN718, Ti-6Al-4V | ALLOY_NOT_ALSI10MG |
| $.researchModels.keyholeCavity.fields.alloy.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.keyholeCavity.fields.aspectRatio_e_over_d.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.keyholeCavity.fields.beamDiameter_m.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.keyholeCavity.fields.cavityAbsorptance.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.keyholeCavity.fields.cavityDepth_um.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.keyholeCavity.fields.conductivity_W_mK.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.keyholeCavity.fields.cylinderHarmonicDifference.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.keyholeCavity.fields.density_kg_m3.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.keyholeCavity.fields.diffusivity_m2_s.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.keyholeCavity.fields.energyResidual_W.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.keyholeCavity.fields.liquidus_K.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.keyholeCavity.fields.modeledAboveOnset.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.keyholeCavity.fields.onsetEvent.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.keyholeCavity.fields.onsetPower_W.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.keyholeCavity.fields.peclet.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.keyholeCavity.fields.powerOverOnset.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.keyholeCavity.fields.power_W.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.keyholeCavity.fields.preheat_K.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.keyholeCavity.fields.propertyConvention.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.keyholeCavity.fields.propertySource.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.keyholeCavity.fields.rootCount.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.keyholeCavity.fields.rootScanRelativeDifference.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.keyholeCavity.fields.rootTopologyStatus.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.keyholeCavity.fields.roots.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.keyholeCavity.fields.selectedBranch.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.keyholeCavity.fields.specificHeat_J_kgK.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.keyholeCavity.fields.speed_m_s.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.keyholeCavity.fields.thermalResponse_g.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.keyholeCavity.fields.thresholdTemperature_K.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.keyholeCavity.fields.totalAbsorptance.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.keyholeCavity.fields.vapourLatentHeat_J_kg.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.keyholeCavity.fields.vapourMolarMass_kg_mol.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.keyholeCavity.fields.vapourSource.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.keyholeCavity.fields.vapourTemperature_K.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.keyholeCavity.fields.wallAbsorptanceProxy.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.marangoni.fields.liquidConductivity_W_mK.value | 2 | IN625 | MARANGONI_VISCOSITY_INPUT_REQUIRED |
| $.researchModels.marangoni.fields.liquidDensity_kg_m3.value | 2 | IN625 | MARANGONI_VISCOSITY_INPUT_REQUIRED |
| $.researchModels.marangoni.fields.liquidDiffusivity_m2_s.value | 2 | IN625 | MARANGONI_VISCOSITY_INPUT_REQUIRED |
| $.researchModels.marangoni.fields.liquidPecletScale.value | 2 | IN625 | MARANGONI_VISCOSITY_INPUT_REQUIRED |
| $.researchModels.marangoni.fields.liquidPrandtl.value | 2 | IN625 | MARANGONI_VISCOSITY_INPUT_REQUIRED |
| $.researchModels.marangoni.fields.liquidReynoldsScale.value | 2 | IN625 | MARANGONI_VISCOSITY_INPUT_REQUIRED |
| $.researchModels.marangoni.fields.liquidSpecificHeat_J_kgK.value | 2 | IN625 | MARANGONI_VISCOSITY_INPUT_REQUIRED |
| $.researchModels.marangoni.fields.marangoniMagnitude.value | 2 | IN625 | MARANGONI_VISCOSITY_INPUT_REQUIRED |
| $.researchModels.marangoni.fields.marangoniNumber.value | 2 | IN625 | MARANGONI_VISCOSITY_INPUT_REQUIRED |
| $.researchModels.marangoni.fields.referenceTemperature_K.value | 2 | IN625 | MARANGONI_VISCOSITY_INPUT_REQUIRED |
| $.researchModels.marangoni.fields.solubleOxygen_ppm.value | 8 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | NOT_APPLICABLE_FOR_CONVENTION |
| $.researchModels.marangoni.fields.solubleSulfur_ppm.value | 8 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | NOT_APPLICABLE_FOR_CONVENTION |
| $.researchModels.marangoni.fields.surfaceVelocityScale_m_s.value | 2 | IN625 | MARANGONI_VISCOSITY_INPUT_REQUIRED |
| $.researchModels.marangoni.fields.viscosity_Pa_s.value | 2 | IN625 | MARANGONI_VISCOSITY_INPUT_REQUIRED |
| $.researchModels.meltDepthLink.fields.absorbedPower_W.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.meltDepthLink.fields.cavityDepth_um.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.meltDepthLink.fields.cavityLedgerRatio.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.meltDepthLink.fields.cavityPowerFraction.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.meltDepthLink.fields.cavityPower_W.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.meltDepthLink.fields.conditionalMeltDepth_um.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.meltDepthLink.fields.conductionDepth_um.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.meltDepthLink.fields.conductionPeakX_m.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.meltDepthLink.fields.conductionRearBound_m.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.meltDepthLink.fields.conductionRefinement_m.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.meltDepthLink.fields.conductionStatus.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.meltDepthLink.fields.controllingLeg.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.meltDepthLink.fields.depositedThermalPower_W.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.meltDepthLink.fields.floorExtractorId.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.meltDepthLink.fields.floorFieldModelId.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.meltDepthLink.fields.linkDispatch.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.meltDepthLink.fields.linkedMeltDepth_um.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.meltDepthLink.fields.lossMultiplier.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.meltDepthLink.fields.meltDepthCoarse_m.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.meltDepthLink.fields.meltDepthRefined_m.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.meltDepthLink.fields.observable.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.meltDepthLink.fields.photonResidual_W.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.meltDepthLink.fields.quadratureOrder.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.meltDepthLink.fields.relativeConvergenceDifference.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.meltDepthLink.fields.surfacePower_W.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.meltDepthLink.fields.unresolvedPower_W.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.meltDepthLink.fields.wallConductionPower_W.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.meltDepthLink.fields.xSamples.value | 6 | 316L, IN625, IN718 | ALLOY_CONSTANT_CHAIN_NOT_ADMITTED |
| $.researchModels.surfaceBalance.fields.absorbedCenterFlux_W_m2.value | 2 | IN625 | SURFACE_VAPOUR_INPUT_REQUIRED |
| $.researchModels.surfaceBalance.fields.beamCenterBalanceTemperature_K.value | 6 | 316L, IN625, IN718 | SURFACE_VAPOUR_INPUT_REQUIRED |
| $.researchModels.surfaceBalance.fields.beamCenterRecoilPressure_Pa.value | 6 | 316L, IN625, IN718 | SURFACE_VAPOUR_INPUT_REQUIRED |
| $.researchModels.surfaceBalance.fields.conductionFlux_W_m2.value | 6 | 316L, IN625, IN718 | SURFACE_VAPOUR_INPUT_REQUIRED |
| $.researchModels.surfaceBalance.fields.conductiveAdmittance_W_m2K.value | 2 | IN625 | SURFACE_VAPOUR_INPUT_REQUIRED |
| $.researchModels.surfaceBalance.fields.effectiveAccommodation.value | 6 | 316L, IN625, IN718 | SURFACE_VAPOUR_INPUT_REQUIRED |
| $.researchModels.surfaceBalance.fields.evaporationEnergyFlux_W_m2.value | 6 | 316L, IN625, IN718 | SURFACE_VAPOUR_INPUT_REQUIRED |
| $.researchModels.surfaceBalance.fields.evaporationMassFlux_kg_m2_s.value | 6 | 316L, IN625, IN718 | SURFACE_VAPOUR_INPUT_REQUIRED |
| $.researchModels.surfaceBalance.fields.iterations.value | 6 | 316L, IN625, IN718 | SURFACE_VAPOUR_INPUT_REQUIRED |
| $.researchModels.surfaceBalance.fields.lossFreeCenterTemperature_K.value | 2 | IN625 | SURFACE_VAPOUR_INPUT_REQUIRED |
| $.researchModels.surfaceBalance.fields.monotonicDerivative_W_m2K.value | 6 | 316L, IN625, IN718 | SURFACE_VAPOUR_INPUT_REQUIRED |
| $.researchModels.surfaceBalance.fields.netEvaporationFactor.value | 8 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | NOT_APPLICABLE_FOR_CONVENTION |
| $.researchModels.surfaceBalance.fields.radiationFlux_W_m2.value | 6 | 316L, IN625, IN718 | SURFACE_VAPOUR_INPUT_REQUIRED |
| $.researchModels.surfaceBalance.fields.relativeFluxResidual.value | 6 | 316L, IN625, IN718 | SURFACE_VAPOUR_INPUT_REQUIRED |
| $.researchModels.surfaceBalance.fields.saturationPressure_Pa.value | 6 | 316L, IN625, IN718 | SURFACE_VAPOUR_INPUT_REQUIRED |
| $.researchModels.surfaceBalance.fields.surfaceGainRefinementRelative.value | 6 | 316L, IN625, IN718 | SURFACE_VAPOUR_INPUT_REQUIRED |
| $.researchModels.surfaceBalance.fields.vapourLatentHeat_J_kg.value | 6 | 316L, IN625, IN718 | SURFACE_VAPOUR_INPUT_REQUIRED |
| $.researchModels.surfaceBalance.fields.vapourMolarMass_kg_mol.value | 6 | 316L, IN625, IN718 | SURFACE_VAPOUR_INPUT_REQUIRED |
| $.researchModels.surfaceBalance.fields.vapourTemperature_K.value | 6 | 316L, IN625, IN718 | SURFACE_VAPOUR_INPUT_REQUIRED |
| $.researchModels.unavailablePhysics.fields.marangoniWidthDepthCorrection.value | 8 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | MARANGONI_SURFACE_CHEMISTRY_UNAVAILABLE |
| $.researchModels.unavailablePhysics.fields.physicalKeyholeCoolingRate_K_s.value | 8 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | KEYHOLE_THERMAL_FLOW_CLOSURE_UNAVAILABLE |
| $.researchModels.unavailablePhysics.fields.physicalKeyholeGradient_K_m.value | 8 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | KEYHOLE_THERMAL_FLOW_CLOSURE_UNAVAILABLE |
| $.researchModels.unavailablePhysics.fields.physicalWallPeakTemperature_K.value | 8 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | SURFACE_BALANCE_CLOSURE_FALSIFIED |
| $.researchModels.unavailablePhysics.fields.physicalWallRecoilPressure_Pa.value | 8 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | SURFACE_BALANCE_CLOSURE_FALSIFIED |
| $.researchModels.unavailablePhysics.fields.powderAbsorptance.value | 8 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | POWDER_ALLOY_OPTICAL_CONSTANTS_UNAVAILABLE |

### solidification-microstructure

| Leaf path pattern | Occurrences | Alloys | Reason codes (empty = prose-only or undisclosed) |
| --- | --- | --- | --- |
| $.quantities.coolingRate.fractionBasis | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.quantities.coolingRate.identity.input | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.quantities.coolingRate.status | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.quantities.coolingRate.validity | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.quantities.coolingRate.value | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.quantities.gOverR.fractionBasis | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.quantities.gOverR.identity.input | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.quantities.gOverR.status | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.quantities.gOverR.validity | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.quantities.gOverR.value | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.quantities.morphology.fractionBasis | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant |
| $.quantities.morphology.identity.input | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant |
| $.quantities.morphology.status | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant |
| $.quantities.morphology.validity | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant |
| $.quantities.morphology.value | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant |
| $.quantities.normalSpeed.fractionBasis | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.quantities.normalSpeed.identity.input | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.quantities.normalSpeed.status | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.quantities.normalSpeed.validity | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.quantities.normalSpeed.value | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.quantities.pdas.fractionBasis | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.quantities.pdas.identity.input | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.quantities.pdas.status | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.quantities.pdas.validity | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.quantities.pdas.value | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.quantities.sdas.fractionBasis | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.quantities.sdas.identity.input | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.quantities.sdas.status | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.quantities.sdas.validity | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.quantities.sdas.value | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.quantities.solidStateTransformation.fractionBasis | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, missing-thermal-history |
| $.quantities.solidStateTransformation.identity.input | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, missing-thermal-history |
| $.quantities.solidStateTransformation.status | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, missing-thermal-history |
| $.quantities.solidStateTransformation.validity | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, missing-thermal-history |
| $.quantities.solidStateTransformation.value | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, missing-thermal-history |
| $.quantities.thermalGradient.fractionBasis | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.quantities.thermalGradient.identity.input | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.quantities.thermalGradient.status | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.quantities.thermalGradient.validity | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.quantities.thermalGradient.value | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.status | 5 | 316L, AlSi10Mg, IN625, IN718, Ti-6Al-4V | — |

### keyhole-raytracing

No physical null/status leaf retained in this compact index (see counts/errors and raw JSON).

### estimate

No physical null/status leaf retained in this compact index (see counts/errors and raw JSON).

### submit

No physical null/status leaf retained in this compact index (see counts/errors and raw JSON).

### submit:build-job

| Leaf path pattern | Occurrences | Alloys | Reason codes (empty = prose-only or undisclosed) |
| --- | --- | --- | --- |
| $.amBenchMaterialPropertySha256 | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | — |
| $.amBenchMaterialPropertySnapshot | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | — |
| $.ambench | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | — |
| $.kinematics.warning | 2 | 316L, IN718 | — |
| $.kinetics.alloy | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | missing-thermal-history |
| $.kinetics.buildCoolingRateCctRow | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | missing-thermal-history |
| $.kinetics.buildCoolingRate_C_s | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | missing-thermal-history |
| $.kinetics.buildRateMartensite | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | missing-thermal-history |
| $.kinetics.calphadVsKineticsGap | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | missing-thermal-history |
| $.kinetics.cctContinuousCoolingMap | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | missing-thermal-history |
| $.kinetics.coolingRateSource | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | missing-thermal-history |
| $.kinetics.reportedCoolingRate_K_s | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | missing-thermal-history |
| $.kinetics.status | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | missing-thermal-history |
| $.microstructure.quantities.coolingRate.fractionBasis | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.microstructure.quantities.coolingRate.identity.input | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.microstructure.quantities.coolingRate.status | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.microstructure.quantities.coolingRate.validity | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.microstructure.quantities.coolingRate.value | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.microstructure.quantities.gOverR.fractionBasis | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.microstructure.quantities.gOverR.identity.input | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.microstructure.quantities.gOverR.status | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.microstructure.quantities.gOverR.validity | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.microstructure.quantities.gOverR.value | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.microstructure.quantities.morphology.fractionBasis | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant |
| $.microstructure.quantities.morphology.identity.input | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant |
| $.microstructure.quantities.morphology.status | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant |
| $.microstructure.quantities.morphology.validity | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant |
| $.microstructure.quantities.morphology.value | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant |
| $.microstructure.quantities.normalSpeed.fractionBasis | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.microstructure.quantities.normalSpeed.identity.input | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.microstructure.quantities.normalSpeed.status | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.microstructure.quantities.normalSpeed.validity | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.microstructure.quantities.normalSpeed.value | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.microstructure.quantities.pdas.fractionBasis | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.microstructure.quantities.pdas.identity.input | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.microstructure.quantities.pdas.status | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.microstructure.quantities.pdas.validity | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.microstructure.quantities.pdas.value | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.microstructure.quantities.sdas.fractionBasis | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.microstructure.quantities.sdas.identity.input | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.microstructure.quantities.sdas.status | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.microstructure.quantities.sdas.validity | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.microstructure.quantities.sdas.value | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.microstructure.quantities.solidStateTransformation.fractionBasis | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, missing-thermal-history |
| $.microstructure.quantities.solidStateTransformation.identity.input | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, missing-thermal-history |
| $.microstructure.quantities.solidStateTransformation.status | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, missing-thermal-history |
| $.microstructure.quantities.solidStateTransformation.validity | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, missing-thermal-history |
| $.microstructure.quantities.solidStateTransformation.value | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, missing-thermal-history |
| $.microstructure.quantities.thermalGradient.fractionBasis | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.microstructure.quantities.thermalGradient.identity.input | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.microstructure.quantities.thermalGradient.status | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.microstructure.quantities.thermalGradient.validity | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.microstructure.quantities.thermalGradient.value | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.microstructure.status | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | — |
| $.murakami.ctDetectionThreshold_um | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | — |
| $.murakami.fatigueLimit_MPa | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | — |
| $.murakami.gumbel | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | — |
| $.qualification.oContentLimit_wt_pct | 3 | 316L, AlSi10Mg, IN718 | — |
| $.qualification.traceability.gitSha | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | — |
| $.segregation.composition.C_wt.min | 1 | IN718 | — |
| $.segregation.lpbfObservations.status | 1 | IN718 | — |
| $.segregation.processCoupling.quantities.coolingRate.fractionBasis | 1 | IN718 | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.segregation.processCoupling.quantities.coolingRate.identity.input | 1 | IN718 | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.segregation.processCoupling.quantities.coolingRate.status | 1 | IN718 | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.segregation.processCoupling.quantities.coolingRate.validity | 1 | IN718 | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.segregation.processCoupling.quantities.coolingRate.value | 1 | IN718 | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.segregation.processCoupling.quantities.gOverR.fractionBasis | 1 | IN718 | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.segregation.processCoupling.quantities.gOverR.identity.input | 1 | IN718 | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.segregation.processCoupling.quantities.gOverR.status | 1 | IN718 | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.segregation.processCoupling.quantities.gOverR.validity | 1 | IN718 | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.segregation.processCoupling.quantities.gOverR.value | 1 | IN718 | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.segregation.processCoupling.quantities.morphology.fractionBasis | 1 | IN718 | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant |
| $.segregation.processCoupling.quantities.morphology.identity.input | 1 | IN718 | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant |
| $.segregation.processCoupling.quantities.morphology.status | 1 | IN718 | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant |
| $.segregation.processCoupling.quantities.morphology.validity | 1 | IN718 | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant |
| $.segregation.processCoupling.quantities.morphology.value | 1 | IN718 | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant |
| $.segregation.processCoupling.quantities.normalSpeed.fractionBasis | 1 | IN718 | keyhole-field-inconsistent, missing-source-constant |
| $.segregation.processCoupling.quantities.normalSpeed.identity.input | 1 | IN718 | keyhole-field-inconsistent, missing-source-constant |
| $.segregation.processCoupling.quantities.normalSpeed.status | 1 | IN718 | keyhole-field-inconsistent, missing-source-constant |
| $.segregation.processCoupling.quantities.normalSpeed.validity | 1 | IN718 | keyhole-field-inconsistent, missing-source-constant |
| $.segregation.processCoupling.quantities.normalSpeed.value | 1 | IN718 | keyhole-field-inconsistent, missing-source-constant |
| $.segregation.processCoupling.quantities.pdas.fractionBasis | 1 | IN718 | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.segregation.processCoupling.quantities.pdas.identity.input | 1 | IN718 | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.segregation.processCoupling.quantities.pdas.status | 1 | IN718 | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.segregation.processCoupling.quantities.pdas.validity | 1 | IN718 | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.segregation.processCoupling.quantities.pdas.value | 1 | IN718 | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.segregation.processCoupling.quantities.sdas.fractionBasis | 1 | IN718 | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.segregation.processCoupling.quantities.sdas.identity.input | 1 | IN718 | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.segregation.processCoupling.quantities.sdas.status | 1 | IN718 | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.segregation.processCoupling.quantities.sdas.validity | 1 | IN718 | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.segregation.processCoupling.quantities.sdas.value | 1 | IN718 | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.segregation.processCoupling.quantities.solidStateTransformation.fractionBasis | 1 | IN718 | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, missing-thermal-history |
| $.segregation.processCoupling.quantities.solidStateTransformation.identity.input | 1 | IN718 | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, missing-thermal-history |
| $.segregation.processCoupling.quantities.solidStateTransformation.status | 1 | IN718 | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, missing-thermal-history |
| $.segregation.processCoupling.quantities.solidStateTransformation.validity | 1 | IN718 | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, missing-thermal-history |
| $.segregation.processCoupling.quantities.solidStateTransformation.value | 1 | IN718 | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, missing-thermal-history |
| $.segregation.processCoupling.quantities.thermalGradient.fractionBasis | 1 | IN718 | keyhole-field-inconsistent, missing-source-constant |
| $.segregation.processCoupling.quantities.thermalGradient.identity.input | 1 | IN718 | keyhole-field-inconsistent, missing-source-constant |
| $.segregation.processCoupling.quantities.thermalGradient.status | 1 | IN718 | keyhole-field-inconsistent, missing-source-constant |
| $.segregation.processCoupling.quantities.thermalGradient.validity | 1 | IN718 | keyhole-field-inconsistent, missing-source-constant |
| $.segregation.processCoupling.quantities.thermalGradient.value | 1 | IN718 | keyhole-field-inconsistent, missing-source-constant |
| $.segregation.processCoupling.status | 1 | IN718 | — |
| $.segregation.quantities.maxBinary.identity.input | 1 | IN718 | — |
| $.segregation.quantities.maxBinary.validity | 1 | IN718 | — |
| $.segregation.quantities.maxTernary.identity.input | 1 | IN718 | — |
| $.segregation.quantities.maxTernary.validity | 1 | IN718 | — |
| $.segregation.quantities.minBinary.identity.input | 1 | IN718 | — |
| $.segregation.quantities.minBinary.validity | 1 | IN718 | — |
| $.segregation.quantities.minTernary.identity.input | 1 | IN718 | — |
| $.segregation.quantities.minTernary.validity | 1 | IN718 | — |
| $.segregation.quantities.nominalBinary.identity.input | 1 | IN718 | — |
| $.segregation.quantities.nominalBinary.validity | 1 | IN718 | — |
| $.segregation.quantities.nominalTernary.identity.input | 1 | IN718 | — |
| $.segregation.quantities.nominalTernary.validity | 1 | IN718 | — |
| $.segregation.quantities.phaseInventory.fractionBasis | 3 | 316L, AlSi10Mg, Ti-6Al-4V | not-requested |
| $.segregation.quantities.phaseInventory.identity.input | 3 | 316L, AlSi10Mg, Ti-6Al-4V | not-requested |
| $.segregation.quantities.phaseInventory.identity.model | 3 | 316L, AlSi10Mg, Ti-6Al-4V | not-requested |
| $.segregation.quantities.phaseInventory.status | 3 | 316L, AlSi10Mg, Ti-6Al-4V | not-requested |
| $.segregation.quantities.phaseInventory.validity | 3 | 316L, AlSi10Mg, Ti-6Al-4V | not-requested |
| $.segregation.quantities.phaseInventory.value | 3 | 316L, AlSi10Mg, Ti-6Al-4V | not-requested |
| $.segregation.rapidSolidification.R_m_s | 1 | IN718 | — |
| $.segregation.rapidSolidification.quantities.fraction.fractionBasis | 1 | IN718 | parent-unavailable |
| $.segregation.rapidSolidification.quantities.fraction.identity.input | 1 | IN718 | parent-unavailable |
| $.segregation.rapidSolidification.quantities.fraction.identity.model | 1 | IN718 | parent-unavailable |
| $.segregation.rapidSolidification.quantities.fraction.status | 1 | IN718 | parent-unavailable |
| $.segregation.rapidSolidification.quantities.fraction.validity | 1 | IN718 | parent-unavailable |
| $.segregation.rapidSolidification.quantities.fraction.value | 1 | IN718 | parent-unavailable |
| $.segregation.rapidSolidification.status | 1 | IN718 | — |
| $.segregation.status | 3 | 316L, AlSi10Mg, Ti-6Al-4V | not-requested |
| $.thermal.defectDiagnostics.ballingScreen.highThreshold | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | — |
| $.thermal.defectDiagnostics.distortionIndex | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | — |
| $.thermal.defectDiagnostics.effectiveResidualStress_MPa | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | — |
| $.thermal.geometricDefectScreen.balling.screen.highThreshold | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | — |
| $.thermal.geometricDefectScreen.gasPore.risk | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | — |
| $.thermal.geometricDefectScreen.keyhole.risk | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | — |
| $.thermal.geometricDefectScreen.porosity.value | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | — |
| $.thermal.hydrodynamicsAndRecoil.knudsenRecoilPressure_kPa | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | — |
| $.thermal.hydrodynamicsAndRecoil.marangoniNumber | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | — |
| $.thermal.hydrodynamicsAndRecoil.peakExceedsVaporization | 2 | AlSi10Mg, IN718 | — |
| $.thermal.hydrodynamicsAndRecoil.peakLocation_x_um | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | — |
| $.thermal.hydrodynamicsAndRecoil.peakTemperature_C | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | — |
| $.thermal.hydrodynamicsAndRecoil.powderDenudationWidth_um | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | — |
| $.thermal.hydrodynamicsAndRecoil.recoilOnsetStatus | 2 | AlSi10Mg, IN718 | — |
| $.thermal.hydrodynamicsAndRecoil.recoilOnsetUnavailableReason | 2 | 316L, Ti-6Al-4V | — |
| $.thermal.hydrodynamicsAndRecoil.surfaceTemperature_C | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | — |
| $.thermal.hydrodynamicsAndRecoil.vaporTemperatureDoi | 2 | AlSi10Mg, IN718 | — |
| $.thermal.hydrodynamicsAndRecoil.vaporTemperatureSource | 2 | AlSi10Mg, IN718 | — |
| $.thermal.hydrodynamicsAndRecoil.vaporTemperatureSourced_C | 2 | AlSi10Mg, IN718 | — |
| $.thermal.hydrodynamicsAndRecoil.vaporTemperatureSourced_K | 2 | AlSi10Mg, IN718 | — |
| $.thermal.hydrodynamicsAndRecoil.vaporTemperatureUnavailableReason | 2 | 316L, Ti-6Al-4V | — |
| $.thermal.marangoniModel.doi | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | — |
| $.thermal.marangoniModel.pecletMarangoni | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | — |
| $.thermal.marangoniModel.surfaceVelocity_m_s | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | — |
| $.thermal.meltPoolGeometry.axialFieldMaximum_C | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | — |
| $.thermal.meltPoolGeometry.extentNote | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | — |
| $.thermal.processParameters.kernelLedgerSha256 | 2 | 316L, IN718 | — |
| $.thermal.processWindowMap.grid[*].depth_um | 8 | 316L, IN718 | — |
| $.thermal.processWindowMap.grid[*].width_um | 8 | 316L, IN718 | — |
| $.thermal.solidificationKinetics.quantities.coolingRate.fractionBasis | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.thermal.solidificationKinetics.quantities.coolingRate.identity.input | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.thermal.solidificationKinetics.quantities.coolingRate.status | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.thermal.solidificationKinetics.quantities.coolingRate.validity | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.thermal.solidificationKinetics.quantities.coolingRate.value | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.thermal.solidificationKinetics.quantities.gOverR.fractionBasis | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.thermal.solidificationKinetics.quantities.gOverR.identity.input | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.thermal.solidificationKinetics.quantities.gOverR.status | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.thermal.solidificationKinetics.quantities.gOverR.validity | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.thermal.solidificationKinetics.quantities.gOverR.value | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant, parent-unavailable |
| $.thermal.solidificationKinetics.quantities.morphology.fractionBasis | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant |
| $.thermal.solidificationKinetics.quantities.morphology.identity.input | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant |
| $.thermal.solidificationKinetics.quantities.morphology.status | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant |
| $.thermal.solidificationKinetics.quantities.morphology.validity | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant |
| $.thermal.solidificationKinetics.quantities.morphology.value | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant |
| $.thermal.solidificationKinetics.quantities.normalSpeed.fractionBasis | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.thermal.solidificationKinetics.quantities.normalSpeed.identity.input | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.thermal.solidificationKinetics.quantities.normalSpeed.status | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.thermal.solidificationKinetics.quantities.normalSpeed.validity | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.thermal.solidificationKinetics.quantities.normalSpeed.value | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.thermal.solidificationKinetics.quantities.pdas.fractionBasis | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.thermal.solidificationKinetics.quantities.pdas.identity.input | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.thermal.solidificationKinetics.quantities.pdas.status | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.thermal.solidificationKinetics.quantities.pdas.validity | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.thermal.solidificationKinetics.quantities.pdas.value | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.thermal.solidificationKinetics.quantities.sdas.fractionBasis | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.thermal.solidificationKinetics.quantities.sdas.identity.input | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.thermal.solidificationKinetics.quantities.sdas.status | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.thermal.solidificationKinetics.quantities.sdas.validity | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.thermal.solidificationKinetics.quantities.sdas.value | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, parent-unavailable |
| $.thermal.solidificationKinetics.quantities.solidStateTransformation.fractionBasis | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, missing-thermal-history |
| $.thermal.solidificationKinetics.quantities.solidStateTransformation.identity.input | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, missing-thermal-history |
| $.thermal.solidificationKinetics.quantities.solidStateTransformation.status | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, missing-thermal-history |
| $.thermal.solidificationKinetics.quantities.solidStateTransformation.validity | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, missing-thermal-history |
| $.thermal.solidificationKinetics.quantities.solidStateTransformation.value | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-bound-model, missing-source-constant, missing-thermal-history |
| $.thermal.solidificationKinetics.quantities.thermalGradient.fractionBasis | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.thermal.solidificationKinetics.quantities.thermalGradient.identity.input | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.thermal.solidificationKinetics.quantities.thermalGradient.status | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.thermal.solidificationKinetics.quantities.thermalGradient.validity | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.thermal.solidificationKinetics.quantities.thermalGradient.value | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | keyhole-field-inconsistent, missing-source-constant |
| $.uq | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | — |
| $.verdict.extentNote | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | — |
| $.verdict.gates[*].measured | 12 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | — |
| $.verdict.gates[*].required | 16 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | — |
| $.verdict.gates[*].status | 8 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | — |
| $.verdict.suggestedPatch | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | — |
| $.verdict.suggestedPatchNote | 1 | AlSi10Mg | — |
| $.verdict.verdictReason | 4 | 316L, AlSi10Mg, IN718, Ti-6Al-4V | — |

### submit:in625-bareplate-field

| Leaf path pattern | Occurrences | Alloys | Reason codes (empty = prose-only or undisclosed) |
| --- | --- | --- | --- |
| $.fallbackReason | 1 | — | — |
| $.provenance.deviceEvidence.index | 1 | — | — |

## Explicit skips and limits

| Operation | Alloy | Why not executed |
| --- | --- | --- |
| calphad-minimize | IN625 | NO_UI_DEFAULT: IN625 has no UI composition preset; chemistry not invented |
| lpbf-process-window | Ti-6Al-4V | MEASURED_ROWS: _overlay calls public-dataset / NIST Table 4 loaders; no overlay-off request switch |
| lpbf-process-window | AlSi10Mg | MEASURED_ROWS: _overlay calls public-dataset / NIST Table 4 loaders; no overlay-off request switch |
| lpbf-process-window | IN718 | MEASURED_ROWS: _overlay calls public-dataset / NIST Table 4 loaders; no overlay-off request switch |
| lpbf-process-window | 316L | MEASURED_ROWS: _overlay calls public-dataset / NIST Table 4 loaders; no overlay-off request switch |
| lpbf-process-window | IN625 | MEASURED_ROWS: _overlay calls public-dataset / NIST Table 4 loaders; no overlay-off request switch |
| xrd-deconvolve | — | NO_UI_DEFAULT: requires user ROI points/peaks; no mounted caller or default spectrum; no synthetic spectrum invented |
| submit:gpu-thermal-pilot | Ti-6Al-4V | GPU_FORBIDDEN: Torch/Warp CUDA execution |
| submit:gpu-thermal-pilot | AlSi10Mg | GPU_FORBIDDEN: Torch/Warp CUDA execution |
| submit:gpu-thermal-pilot | IN718 | GPU_FORBIDDEN: Torch/Warp CUDA execution |
| submit:gpu-thermal-pilot | 316L | GPU_FORBIDDEN: Torch/Warp CUDA execution |
| submit:gpu-thermal-pilot | IN625 | GPU_FORBIDDEN: Torch/Warp CUDA execution |
| capabilities | — | GPU_PROBE: capabilities probes GPU/OpenFOAM inventory; no solver output |
| submit-repeat | — | LIFECYCLE: same physics as submit; would write queue/archive identity |
| get | — | LIFECYCLE: needs existing job id; no independent physics |
| cancel | — | LIFECYCLE: mutates an existing job |
| artifact | — | LIFECYCLE: needs existing job artifact |
| archive-capture | — | ARCHIVE: existing job/source binding; no independent physics |
| nist-comparison | — | MEASURED_ROWS: exact archived Table 4 measurement binding |
| proxy-campaign-validation | — | MEASURED_ROWS: existing run/source observations; no default archive |
| proxy-section-rederive | — | ARCHIVE: needs captured NPZ bytes/result; no default artifact |

Forbidden datasets `leis2021`, `hyer2020`, `aboulkhair2016`, `ruckh2025`, `gong2014`, `ullah`, `wimmer2020` were not loaded. Reading Python source/manifests for provenance hashes is not a measurement-row load. No measured overlays, independent experimental error metrics, UQ opt-ins, convergence studies, custom meshes, GPU/OpenFOAM backends, nondefault optical wavelengths or alternate thermal kernels were executed. No claims are made for their runtime outputs beyond the explicit source inventory. Archive and queue lifecycle responses require existing state and are not probed with invented ids.

Validation: 9 standalone stdlib tests pass, including route/registry authority coverage, non-manifest isolation, nested leaf/reason collection, skipped-data no-spawn behavior, default inputs, owned Windows process-tree timeout cleanup, guarded paths/network and preserved exception messages. `git diff --check` passes. Scientific/parity/golden suites were not run because served code and physics were unchanged. Only the three requested files are committed; raw JSON and temporary report-generation helper stay outside the checkout.
