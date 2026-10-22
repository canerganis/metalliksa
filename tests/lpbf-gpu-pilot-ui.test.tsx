import React from 'react';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import { renderToStaticMarkup } from 'react-dom/server';
import { GpuPilotArchiveAction, GpuPilotControls, GpuPilotExecutedInputSummary, LpbfEngineeringSimulation, gpuPilotRuntimeLabel,
  materialSourceEvidenceReadiness, materialTableAvailabilityReadiness, recoverMissingSavedGpuPilot, gpuDevicesForEngine, sameGpuDeviceIdentity } from '../src/components/3d-distortion-lab/LpbfEngineeringSimulation';
import { ArchivedRunMaterialProvenance, ExecutedMaterialProvenance, GpuPilotParityTable, gpuPilotEngineLabel, persistRunSelectionForArchive,
  restoreRunSelectionForArchive } from '../src/components/LpbfRunArchivePanel';
import { buildGpuPilotInput, parseGpuPilotJob, type GpuPilotInput } from '../src/services/lpbfSimulationService';

test('engineering screen exposes only the primary run action before CUDA inventory is reported', () => {
  const html = renderToStaticMarkup(<LpbfEngineeringSimulation input={{
    material: 'Inconel 718', power_W: 60, speed_mm_s: 1200,
    beamDiameter_um: 80, preheat_C: 25, layer_um: 80, hatch_um: 100,
  }}/>);
  assert.equal((html.match(/>Run simulation<\/button>/g) ?? []).length, 1);
  for (const text of ['Advanced (GPU pilots)', 'GPU (CUDA)', 'CUDA thermal parity pilot', 'Run CUDA parity pilot', 'Run CPU screen', 'Run CUDA screen']) {
    assert.ok(!html.includes(text), text);
  }
});

const pilotProps = {
  input: { material: 'Inconel 718', power_W: 60, speed_mm_s: 1200,
    beamDiameter_um: 80, preheat_C: 25, layer_um: 80, hatch_um: 100 },
  settings: {}, material: 'Inconel 718', properties: '', strategy: 'stripe' as const, blocked: false,
};
const cudaDevice = { ordinal: 0, device: 'cuda:0', name: 'Test CUDA device', computeCapability: [8, 9], memoryBytes: 8000 };
const workerCaps = { openfoamVersion: null, openfoamThermal: false, freeSurfaceSolver: false,
  platform: 'test', limitation: '', materials: [] };

test('GPU section is open and visible, not a closed disclosure, and retains both parity and bare-plate controls with a reported CUDA device', () => {
  const caps = { ...workerCaps, gpuDevices: { torch: { runtimeAvailable: true, devices: [cudaDevice] } } };
  const html = renderToStaticMarkup(<GpuPilotControls {...pilotProps} caps={caps}/>);
  assert.match(html, /^<section aria-label="GPU \(CUDA\)"[^>]*><h4[^>]*>GPU \(CUDA\)<\/h4>/);
  assert.doesNotMatch(html, /^<details/);
  assert.ok(!html.includes('Advanced (GPU pilots)'));
  for (const text of ['CUDA thermal parity pilot', 'Run CUDA parity pilot', 'Run CPU screen', 'Run CUDA screen',
    'Explicit CUDA device', 'Numerical CPU/GPU parity only',
    'Experimental validation and qualification are unavailable',
    'A completed bound GPU result can be imported with Save to Archive below',
    'field bytes and numerical evidence are rechecked during import and bundle restore']) {
    assert.ok(html.includes(text), text);
  }
  assert.ok(!html.includes('Permanent archive export and restoration remain unavailable'));
  assert.match(html, /aria-label="CUDA device"/);
  assert.match(html, /aria-label="GPU engine"/);
  assert.ok(html.includes('NVIDIA Warp candidate · v2'));
  assert.match(html, /type="submit"/);
});

test('GPU pilot controls stay hidden for missing, unavailable or malformed CUDA inventory and support Warp-only devices', () => {
  for (const caps of [undefined, workerCaps,
    { ...workerCaps, gpuDevices: { torch: { runtimeAvailable: false, devices: [cudaDevice] } } },
    { ...workerCaps, gpuDevices: { torch: { runtimeAvailable: true, devices: [{ ...cudaDevice, memoryBytes: 0 }] } } },
  ]) assert.equal(renderToStaticMarkup(<GpuPilotControls {...pilotProps} caps={caps}/>), '');
  const caps = { ...workerCaps, gpuDevices: { warp: { runtimeAvailable: true, devices: [cudaDevice] } } };
  assert.match(renderToStaticMarkup(<GpuPilotControls {...pilotProps} caps={caps}/>), /GPU \(CUDA\)/);
});

test('material availability does not pass source and uncertainty evidence readiness', () => {
  const available = materialTableAvailabilityReadiness(true, false, false);
  assert.equal(available.status, 'pass');
  assert.match(available.details, /availability does not establish source quality/i);
  const missing = materialTableAvailabilityReadiness(false, false, true);
  assert.equal(missing.status, 'fail');
  const userSupplied = materialTableAvailabilityReadiness(undefined, true, false);
  assert.equal(userSupplied.status, 'pending');
  assert.match(userSupplied.details, /awaiting worker validation/i);
  assert.equal(materialTableAvailabilityReadiness(true, true, false).status, 'pending', 'user override must not inherit canonical registry availability');
  const overrideEvidence = materialSourceEvidenceReadiness('user-supplied-unverified');
  assert.equal(overrideEvidence.status, 'warn');
  assert.match(overrideEvidence.details, /User-supplied material data/);
  assert.equal(materialTableAvailabilityReadiness(undefined, false, false).status, 'pending');
  for (const quality of ['estimated', 'estimated-legacy', 'user-supplied-unverified']) {
    const evidence = materialSourceEvidenceReadiness(quality);
    assert.equal(evidence.status, 'warn', quality);
    assert.match(evidence.details, /source review and quantified property uncertainty are not established/i);
    assert.match(evidence.details, /exploratory execution remains available/i);
  }
  const pending = materialSourceEvidenceReadiness();
  assert.equal(pending.status, 'pending');
  assert.match(pending.details, /treat material data as unverified/i);
  const html = renderToStaticMarkup(<LpbfEngineeringSimulation input={{
    material: 'Inconel 718', power_W: 60, speed_mm_s: 1200,
    beamDiameter_um: 80, preheat_C: 25, layer_um: 80, hatch_um: 100,
  }}/>);
  assert.ok(html.includes('Material table availability'));
  assert.ok(html.includes('Material source and uncertainty evidence'));
  assert.ok(html.includes('Source review and quantified property uncertainty are not established'));
  assert.ok(html.includes('treat material data as unverified'));
});

test('CUDA device picker uses only the selected runtime inventory and rejects malformed entries', () => {
  const caps = { gpuDevices: {
    torch: { runtimeAvailable: true, devices: [
      { ordinal: 1, device: 'cuda:1', name: 'Torch GPU 1', computeCapability: [8, 9], memoryBytes: 8000 },
      { ordinal: 0, device: 'cuda:0', name: 'Torch GPU 0', computeCapability: [8, 6], memoryBytes: 4000 },
      { ordinal: 2, device: 'cuda:2', name: 'stale', computeCapability: [8, 9], memoryBytes: 0 },
    ] },
    warp: { runtimeAvailable: true, devices: [
      { ordinal: 0, device: 'cuda:0', name: 'Warp GPU 0', computeCapability: [8, 9], memoryBytes: 12000 },
    ] },
  } };
  assert.deepEqual(gpuDevicesForEngine(caps, 'torch').map(device => device.device), ['cuda:0', 'cuda:1']);
  assert.equal(gpuDevicesForEngine(caps, 'warp')[0].name, 'Warp GPU 0');
  assert.deepEqual(gpuDevicesForEngine({ gpuDevices: { torch: {
    runtimeAvailable: false,
    devices: [{ ordinal: 0, device: 'cuda:0', name: 'stale but plausible', computeCapability: [8, 9], memoryBytes: 12000 }],
  } } }, 'torch'), [], 'a plausible list cannot override unavailable runtime status');
  assert.deepEqual(gpuDevicesForEngine({ gpuDevices: { warp: { devices: [{}] } } }, 'warp'), []);
  assert.deepEqual(gpuDevicesForEngine(undefined, 'torch'), []);
});

test('CUDA submit identity rejects a same ordinal that resolves to a changed device', () => {
  const selected = { ordinal: 0, device: 'cuda:0' as const, name: 'GPU A',
    computeCapability: [8, 9] as [number, number], memoryBytes: 8000 };
  assert.equal(sameGpuDeviceIdentity(selected, {...selected}), true);
  assert.equal(sameGpuDeviceIdentity(selected, {...selected, name: 'GPU B'}), false);
  assert.equal(sameGpuDeviceIdentity(selected, {...selected, computeCapability: [8, 6]}), false);
  assert.equal(sameGpuDeviceIdentity(selected, {...selected, memoryBytes: 4000}), false);
  assert.equal(sameGpuDeviceIdentity(selected, undefined), false);
});

test('run archive restores only a still-present saved run selection', () => {
  const runs = ['a'.repeat(32), 'b'.repeat(32)];
  const values = new Map<string, string>([['metalliksa.lpbf.runArchive.selectedRun.v1', runs[1]]]);
  const storage = { getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => values.set(key, value) };
  assert.equal(restoreRunSelectionForArchive(runs, () => storage), runs[1]);
  assert.equal(restoreRunSelectionForArchive(runs, () => storage), runs[1], 'a remount keeps the same run selected');
  assert.equal(restoreRunSelectionForArchive(runs, () => ({ ...storage,
    getItem: () => 'c'.repeat(32) })), runs[0]);
  assert.equal(values.get('metalliksa.lpbf.runArchive.selectedRun.v1'), runs[0], 'a stale ID is replaced by a current run');
  assert.equal(restoreRunSelectionForArchive([], () => storage), '');
  assert.equal(values.get('metalliksa.lpbf.runArchive.selectedRun.v1'), runs[0], 'an empty archive preserves the last valid ID');
  assert.equal(restoreRunSelectionForArchive(runs, () => { throw new Error('storage denied'); }), runs[0]);
  assert.equal(restoreRunSelectionForArchive(runs, () => ({ getItem: () => { throw new Error('read denied'); },
    setItem: () => { throw new Error('write denied'); } })), runs[0]);
  assert.doesNotThrow(() => persistRunSelectionForArchive(runs[1], () => { throw new Error('storage denied'); }));
});

test('only a confirmed missing saved CUDA job is forgotten; newer IDs and transient errors are preserved', () => {
  const savedId = 'd'.repeat(32);
  const key = 'metalliksa.lpbf.gpu-pilot.job.v1';
  const values = new Map<string, string>([[key, savedId]]);
  const storage = { getItem: (name: string) => values.get(name) ?? null,
    removeItem: (name: string) => { values.delete(name); } };
  assert.equal(recoverMissingSavedGpuPilot(new Error('Job not found'), savedId, () => storage), true);
  assert.equal(values.has(key), false);
  values.set(key, 'e'.repeat(32));
  assert.equal(recoverMissingSavedGpuPilot(new Error('LPBF HTTP 404'), savedId, () => storage), true);
  assert.equal(values.get(key), 'e'.repeat(32), 'a newer saved job must not be removed');
  for (const error of [new Error('LPBF HTTP 503'), new Error('fetch failed'), new Error('invalid job response')]) {
    assert.equal(recoverMissingSavedGpuPilot(error, 'e'.repeat(32), () => storage), false);
    assert.equal(values.get(key), 'e'.repeat(32), 'transient or malformed responses must retain the saved ID');
  }
  assert.equal(recoverMissingSavedGpuPilot(new Error('Job not found'), savedId, () => { throw new Error('storage denied'); }), true);
  assert.doesNotThrow(() => recoverMissingSavedGpuPilot(new Error('Job not found'), savedId,
    () => ({ getItem: () => savedId, removeItem: () => { throw new Error('removal denied'); } })));
});

test('completed bound GPU jobs expose an archive action for that job only', () => {
  const actual = JSON.parse(readFileSync(new URL(
    '../docs/LPBF_GPU_NATIVE_WORKER_ACCEPTANCE_RETRY_2026-09-27/2bcb01e5799041ec9458a947506d491f/result.json',
    import.meta.url), 'utf8')) as { settings: GpuPilotInput } & Record<string, unknown>;
  const jobId = '2bcb01e5799041ec9458a947506d491f';
  const job = parseGpuPilotJob({
    id: jobId, status: 'completed', progress: 1, log: '', error: null,
    requestSummary: { jobType: 'gpu-thermal-pilot', backend: actual.settings.backend,
      mode: actual.settings.mode, material: actual.settings.material },
    result: actual,
  });
  const html = renderToStaticMarkup(<GpuPilotArchiveAction job={job}/>);
  assert.match(html, /aria-label="Archive completed CUDA pilot"/);
  assert.match(html, new RegExp(`data-gpu-job-id="${jobId}"`));
  assert.match(html, /Save to Archive/);
  assert.match(html, /Loading imported source revisions/);

  const unfinished = renderToStaticMarkup(<GpuPilotArchiveAction job={{...job, status: 'running', result: undefined}}/>);
  assert.equal(unfinished, '');

  const legacyResult: Record<string, unknown> = {...actual, artifacts: []};
  delete legacyResult.gpuRunContract;
  delete legacyResult.gpuFieldArtifacts;
  const legacy = parseGpuPilotJob({
    id: jobId, status: 'completed', progress: 1, log: '', error: null,
    requestSummary: { jobType: 'gpu-thermal-pilot', backend: actual.settings.backend,
      mode: actual.settings.mode, material: actual.settings.material },
    result: legacyResult,
  });
  assert.equal(renderToStaticMarkup(<GpuPilotArchiveAction job={legacy}/>), '');
});

test('saved CUDA results show their executed inputs and label changed current controls', () => {
  const actual = JSON.parse(readFileSync(new URL(
    '../docs/LPBF_GPU_NATIVE_WORKER_ACCEPTANCE_RETRY_2026-09-27/2bcb01e5799041ec9458a947506d491f/result.json',
    import.meta.url), 'utf8')) as { settings: GpuPilotInput };
  const saved = actual.settings;
  const input = { material: 'Inconel 718', power_W: 60, speed_mm_s: 1200,
    beamDiameter_um: 80, preheat_C: 80, layer_um: 80, hatch_um: 100 };
  const current = buildGpuPilotInput(input, {
    mesh_um: 40, maxDt_s: 2e-7, tracks: 1, layers: 1, trackLength_um: 200,
    stripeWidth_um: 500, islandSize_um: 200, cooling_s: 2e-5, dwell_s: 0,
    scanAngle_deg: 0, layerRotation_deg: 67, timeout_s: 300, packingFraction: .55,
    powderConductivityRatio: .12, convection_W_m2K: 20,
  }, 'cuda:0', 'Inconel 718', 'stripe');
  const matching = renderToStaticMarkup(<GpuPilotExecutedInputSummary
    saved={saved} current={current} bound/>);
  assert.match(matching, /Inputs used by this saved CUDA job/);
  assert.match(matching, /Mesh spacing · µm/);
  assert.match(matching, />40</);
  assert.match(matching, /Stripe width · µm/);
  assert.match(matching, /Island size · µm/);
  assert.match(matching, /Bare-plate geometry/);
  assert.match(matching, /Absorptivity/);
  assert.match(matching, /Omitted\/defaulted fields are not compared/);

  const changed = buildGpuPilotInput(input, {
    mesh_um: 20, maxDt_s: 2e-7, tracks: 1, layers: 1, trackLength_um: 200,
    stripeWidth_um: 500, islandSize_um: 200, cooling_s: 2e-5, dwell_s: 0,
    scanAngle_deg: 0, layerRotation_deg: 67, timeout_s: 300, packingFraction: .55,
    powderConductivityRatio: .12, convection_W_m2K: 20,
  }, 'cuda:0', 'Inconel 718', 'stripe');
  const stale = renderToStaticMarkup(<GpuPilotExecutedInputSummary
    saved={saved} current={changed} bound/>);
  assert.match(stale, /Current submitted fields differ from this saved result: mesh_um/);
  assert.match(stale, /displayed result still belongs to the saved run/);
  assert.match(stale, />40</);

  const legacy = renderToStaticMarkup(<GpuPilotExecutedInputSummary
    saved={saved} current={changed} bound={false}/>);
  assert.match(legacy, /no exact request binding/);
});

test('custom GPU material provenance is shown from both executed and archived result snapshots', () => {
  const actual = JSON.parse(readFileSync(new URL(
    '../docs/LPBF_GPU_NATIVE_WORKER_ACCEPTANCE_RETRY_2026-09-27/2bcb01e5799041ec9458a947506d491f/result.json',
    import.meta.url), 'utf8')) as Record<string, any>;
  const material = {
    ...actual.material,
    quality: 'user-supplied-unverified',
    provenanceClass: 'user-supplied-unverified',
    source: 'Custom LPBF material table · supplier datasheet supplied by operator',
    uncertaintyNote: 'Supplier uncertainty was not independently checked.',
  };
  const executed = renderToStaticMarkup(<ExecutedMaterialProvenance material={material}/>);
  const archived = renderToStaticMarkup(<ArchivedRunMaterialProvenance
    resultJson={JSON.stringify({...actual, material})}/>);
  for (const html of [executed, archived]) {
    assert.match(html, /Executed material provenance/);
    assert.match(html, /user-supplied-unverified/);
    assert.match(html, /Custom LPBF material table · supplier datasheet supplied by operator/);
    assert.match(html, /Supplier uncertainty was not independently checked/);
    assert.match(html, new RegExp(material.materialRevisionSha256));
    assert.match(html, /model remains unvalidated/i);
  }
});

test('missing or malformed archived material provenance is rendered as not reported', () => {
  const missing = renderToStaticMarkup(<ArchivedRunMaterialProvenance
    resultJson={JSON.stringify({material: {name: 'Legacy material'}})}/>);
  const malformed = renderToStaticMarkup(<ArchivedRunMaterialProvenance resultJson="{"/>);
  for (const html of [missing, malformed]) {
    assert.match(html, /Executed material provenance/);
    assert.equal((html.match(/Not reported/g) ?? []).length, 5);
    assert.match(html, /model remains unvalidated/i);
  }
});

test('archived build-job provenance renders its captured effective material property snapshot', () => {
  const propertySha256 = 'a'.repeat(64);
  const conflictingNestedPropertySha256 = 'b'.repeat(64);
  const materialPropertySnapshot = {
    schemaVersion: 1,
    alloyId: 'in718',
    thermal: { base: 'Ni', liquidus_C: 1336, thermal_conductivity_W_mK: 11.4 },
    slicer: { density_gcm3: 8.19 },
  };
  const html = renderToStaticMarkup(<ArchivedRunMaterialProvenance resultJson={JSON.stringify({
    runKind: 'build-screening',
    material: { id: 'in718', propertySha256: conflictingNestedPropertySha256 },
    materialPropertySha256: propertySha256,
    materialPropertySnapshot,
  })}/>);
  assert.match(html, /Build-job material property snapshot/);
  assert.match(html, /Captured effective identity and properties/);
  assert.match(html, /in718/);
  assert.match(html, /Recorded property SHA-256/);
  assert.match(html, new RegExp(propertySha256));
  assert.ok(!html.includes(conflictingNestedPropertySha256), 'display the top-level digest bound to the snapshot, not the unbound nested alias');
  assert.match(html, /Captured thermal and slicer properties/);
  assert.match(html, /liquidus_C/);
  assert.match(html, /density_gcm3/);
  assert.match(html, /8\.19/);
  assert.match(html, /does not establish source validation/);
  assert.match(html, /model remains unvalidated/i);
});

test('GPU engine label requires matching outer capture, contract, runtime, settings and solver identities', () => {
  const actual = JSON.parse(readFileSync(new URL(
    '../docs/LPBF_GPU_NATIVE_WORKER_ACCEPTANCE_RETRY_2026-09-27/2bcb01e5799041ec9458a947506d491f/result.json',
    import.meta.url), 'utf8'));
  const torchCapture = {
    schemaVersion: 1, runKind: 'gpu-thermal-pilot',
    contractStatus: 'gpu-pilot-v1-bound',
    inputJson: actual.gpuRunContract.serializedInputs.requestJson,
    materialJson: actual.gpuRunContract.serializedInputs.materialJson,
  };
  assert.equal(gpuPilotEngineLabel(torchCapture, actual), 'PyTorch CUDA · v1');
  const torchRuntimeLabel = gpuPilotRuntimeLabel(actual);
  assert.match(torchRuntimeLabel, /^PyTorch .+ · CUDA runtime .+$/);
  assert.ok(!torchRuntimeLabel.includes('CUDA toolkit'));
  assert.equal(gpuPilotEngineLabel(torchCapture,
    {...actual, solver: {...actual.solver, id: 'enthalpy-fv-6-warp-candidate-1'}}), 'GPU engine unverified');
  const torchCudaSource = structuredClone(actual);
  torchCudaSource.solver.sourceIntegrationDevice = 'cuda:0';
  torchCudaSource.solver.sourceTimestepLimiterDevice = 'cuda:0';
  torchCudaSource.provenance.deviceEvidence.sourceIntegration = 'cuda:0';
  torchCudaSource.provenance.deviceEvidence.sourceTimestepLimiter = 'cuda:0';
  assert.equal(gpuPilotEngineLabel(torchCapture, torchCudaSource), 'PyTorch CUDA · v1');
  const detachedSource = structuredClone(torchCudaSource);
  detachedSource.provenance.deviceEvidence.sourceTimestepLimiter = 'cpu';
  assert.equal(gpuPilotEngineLabel(torchCapture, detachedSource), 'GPU engine unverified');

  const warp = structuredClone(actual);
  warp.settings.executionEngine = 'warp';
  warp.solver.id = 'enthalpy-fv-6-warp-candidate-1';
  warp.solver.modelId = 'stationary-enthalpy-conduction-layer-conforming-v1';
  warp.gpuRunContract.schemaVersion = 2;
  warp.gpuRunContract.capture.contractStatus = 'gpu-pilot-v2-warp-bound';
  warp.gpuRunContract.capture.engineId = 'warp';
  warp.gpuRunContract.capture.modelId = warp.solver.modelId;
  warp.gpuRunContract.serializedInputs.requestJson = JSON.stringify(warp.settings);
  warp.gpuRunContract.hashes.requestHash = createHash('sha256').update(warp.gpuRunContract.serializedInputs.requestJson).digest('hex');
  warp.provenance.inputHash = warp.gpuRunContract.hashes.requestHash;
  warp.provenance.deviceEvidence.engineId = 'warp';
  warp.provenance.deviceEvidence.warp = '1.17.0';
  warp.provenance.deviceEvidence.warpCudaToolkitVersion = '12.9';
  warp.provenance.deviceEvidence.cudaDriverVersion = '13.4';
  delete warp.provenance.deviceEvidence.torch;
  delete warp.provenance.deviceEvidence.cudaRuntime;
  const warpCapture = {
    ...torchCapture, contractStatus: 'gpu-pilot-v2-warp-bound',
    inputJson: warp.gpuRunContract.serializedInputs.requestJson,
  };
  assert.equal(gpuPilotEngineLabel(warpCapture, warp), 'NVIDIA Warp candidate · v2');
  assert.equal(gpuPilotRuntimeLabel(warp), 'Warp 1.17.0 · CUDA toolkit 12.9 · CUDA driver 13.4');
  assert.ok(!gpuPilotRuntimeLabel(warp).includes('CUDA runtime'));
  assert.equal(gpuPilotEngineLabel(torchCapture, warp), 'GPU engine unverified');
  const ambiguousRuntime = structuredClone(warp);
  ambiguousRuntime.provenance.deviceEvidence.cudaRuntime = '12.6';
  assert.equal(gpuPilotEngineLabel(warpCapture, ambiguousRuntime), 'GPU engine unverified');

  const warpJob = parseGpuPilotJob({ id: '2bcb01e5799041ec9458a947506d491f', status: 'completed', progress: 1,
    log: '', error: null, requestSummary: { jobType: 'gpu-thermal-pilot', backend: warp.settings.backend,
      mode: 'standard', material: warp.settings.material, executionEngine: 'warp' }, result: warp });
  const table = renderToStaticMarkup(<GpuPilotParityTable captureValue={warpCapture} resultValue={warpJob.result}/>);
  assert.match(table, /CPU and Warp numerical parity/);
  assert.match(table, /numerical\/model parity · pass/);
  assert.match(table, /experimental validation/);
  assert.match(table, /finalTemperatureField/);
  assert.equal((table.match(/scope="row"/g) ?? []).length, 10);
  assert.match(table, /CPU<!-- -->:|CPU/);
  assert.match(table, /0\.000186667 s · 934 steps/);
  assert.match(table, /Expected end/);
  assert.match(table, /L2 .*Lmax/);
  assert.match(table, /dimensionless/);
  assert.equal(renderToStaticMarkup(<GpuPilotParityTable captureValue={torchCapture} resultValue={warpJob.result}/>), '');
  assert.equal(renderToStaticMarkup(<GpuPilotParityTable captureValue={warpCapture} resultValue={actual}/>), '');
  for (const version of ['0.0', '00.9']) {
    const malformedVersion = structuredClone(warp);
    malformedVersion.provenance.deviceEvidence.cudaDriverVersion = version;
    assert.equal(gpuPilotEngineLabel(warpCapture, malformedVersion), 'GPU engine unverified');
  }
});

test('the GPU section follows the main run controls in the engineering screen source', async () => {
  const { readFileSync } = await import('node:fs');
  const src = readFileSync(new URL('../src/components/3d-distortion-lab/LpbfEngineeringSimulation.tsx', import.meta.url), 'utf8');
  const run = src.indexOf('"Submitting…":"Run simulation"');
  const repeat = src.indexOf('aria-label="Create a fresh computational run record"');
  const gpu = src.indexOf('<GpuPilotControls input={input}');
  assert.ok(run > 0 && repeat > run && gpu > repeat, 'GPU controls come right after the run controls');
});
