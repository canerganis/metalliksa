import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdirSync, mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { test } from 'node:test';
import express from 'express';
import type { Server } from 'node:http';
import { createLpbfRunsRouter } from '../routes/lpbfRuns';
import { LpbfArtifactStore } from '../server/lpbfArtifactStore';
import { LpbfNistComparisonService } from '../server/lpbfNistComparisonService';
import { LpbfRunArchiveService } from '../server/lpbfRunArchiveService';
import { LpbfRunBundleService } from '../server/lpbfRunBundleService';
import { importRun } from '../server/lpbfRunImport';
import { LpbfRunRepository } from '../server/lpbfRunRepository';
import { LpbfSourceArchiveService } from '../server/lpbfSourceArchiveService';
import { LpbfSourceRepository } from '../server/lpbfSourceRepository';
import { nistOpticalTable4CatalogEntry } from '../server/lpbfSourceCatalog';
import { lpbfWorker } from '../server/lpbfWorkerBridge';
import { canonicalBuildJobMaterialSnapshot } from '../src/utils/lpbfBuildJobIdentity';
import { isolateWorkerJobRoot, removeWorkerTestRoot, runCleanupSteps, retryWorkerCall, stopRealWorker, waitForRealWorker } from './support/realLpbfWorker';

const sha256 = (bytes: Buffer | string) => createHash('sha256').update(bytes).digest('hex');

async function jsonRequest(base: string, suffix: string, method: 'GET' | 'POST' = 'GET', body?: unknown) {
  const response = await fetch(`${base}${suffix}`, {
    method,
    ...(method === 'POST' ? { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body ?? {}) } : {}),
  });
  const text = await response.text();
  let payload: any;
  try { payload = JSON.parse(text); }
  catch { throw new Error(`${method} ${suffix} returned non-JSON HTTP ${response.status}: ${text.slice(0, 160)}`); }
  return { status: response.status, payload };
}

/** preview/import capture the job through the worker RPC (20 s caller budget); on a loaded host that RPC can time out
 * and the route answers a generic 503 before any archive state is written. Retry only that 503, bounded, and
 * return the last response unchanged at the deadline so the caller's status assertion still reports it. */
async function jsonRequestRetry503(base: string, suffix: string, body: unknown, budgetMs = 180_000) {
  const deadline = Date.now() + budgetMs;
  for (;;) {
    const result = await jsonRequest(base, suffix, 'POST', body);
    if (result.status !== 503 || Date.now() >= deadline) return result;
    await new Promise(resolve => setTimeout(resolve, 500));
  }
}

test('LPBF source select, CPU compute, unvalidated compare, export and restore preserve identities and bytes', { timeout: 600_000 }, async t => {
  const root = mkdtempSync(path.join(process.cwd(), '.tmp-lpbf-workflow-roundtrip-'));
  const sourceRoot = path.join(root, 'sources');
  const runRoot = path.join(root, 'runs');
  const bundleRoot = path.join(root, 'bundles');
  let server: Server | undefined;
  const restoreJobRoot = isolateWorkerJobRoot(path.join(root, 'jobs'));
  // Every step runs even if an earlier one fails, so a stuck worker is a loud failure, not a leaked env or root.
  t.after(() => runCleanupSteps([
    stopRealWorker,
    restoreJobRoot,
    () => server && new Promise<void>(resolve => server!.close(() => resolve())),
    () => removeWorkerTestRoot(root),
  ]));

  const opticalSource = nistOpticalTable4CatalogEntry();
  const sources = new LpbfSourceArchiveService(sourceRoot, [opticalSource]);
  const selectedDataset = sources.catalog().sources.find(item => item.datasetId === opticalSource.datasetId);
  assert.ok(selectedDataset, 'the NIST optical source is selectable from the local catalog');
  const sourcePreview = await sources.preview(selectedDataset.datasetId);
  assert.equal(sourcePreview.artifactIntegrity, 'verified-at-dry-run');
  const importedSource = await sources.import(selectedDataset.datasetId,
    sourcePreview.expectedRevision, sourcePreview.documentSha256);
  const sourceLink = { datasetId: selectedDataset.datasetId,
    revision: importedSource.revision.revision, documentSha256: importedSource.revision.documentSha256 };
  assert.equal(sourceLink.revision, 1);

  const runs = new LpbfRunArchiveService(runRoot, sourceRoot);
  const bundles = new LpbfRunBundleService(runRoot, sourceRoot, bundleRoot);
  const comparison = new LpbfNistComparisonService(runRoot, sourceRoot);
  const app = express();
  app.use(createLpbfRunsRouter(runs, bundles, comparison));
  server = app.listen(0, '127.0.0.1');
  await new Promise<void>(resolve => server.once('listening', resolve));
  const address = server.address();
  assert.ok(address && typeof address !== 'string');
  const base = `http://127.0.0.1:${address.port}/api/lpbf/runs`;

  // Freeze the V1 CPU user-path reference. It is a workflow replay, not a
  // numerical-convergence oracle and does not reproduce NIST Table 4.
  const workerBudget = 240_000; // bounded per phase; every retry below still fails at its deadline
  await waitForRealWorker(Date.now() + workerBudget);
  const submission = await retryWorkerCall(() => lpbfWorker.request('submit', {
    mode: 'standard', backend: 'reference', material: 'Inconel 718', power_W: 60,
    speed_mm_s: 1200, beamDiameter_um: 80, preheat_C: 200, layer_um: 40,
    mesh_um: 20, maxDt_s: 0.000001, trackLength_um: 600, tracks: 1, layers: 1,
    surfaceMode: 'powder-layer', cooling_s: 0.0005, dwell_s: 0.0002,
  }), Date.now() + workerBudget, { idempotent: false }) as { id: string };
  assert.match(submission.id, /^[a-f0-9]{32}$/);
  let job: any;
  const deadline = Date.now() + workerBudget;
  do {
    job = await retryWorkerCall(() => lpbfWorker.request('get', submission.id), deadline, { idempotent: true });
    if (job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled') break;
    await new Promise(resolve => setTimeout(resolve, 100));
  } while (Date.now() < deadline);
  assert.equal(job.status, 'completed', job.error ?? `CPU thermal job remained ${job.status}`);
  assert.equal(job.result.runKind, 'transient-thermal');
  assert.equal(job.result.validationStatus, 'unvalidated');
  assert.equal(job.result.productionReady, false);
  assert.ok(job.result.thermalHistory?.length > 0, 'the CPU solver produced a thermal history');
  for (const [key, value] of Object.entries({ mode: 'standard', backend: 'reference', power_W: 60,
    speed_mm_s: 1200, beamDiameter_um: 80, preheat_C: 200, layer_um: 40, mesh_um: 20,
    maxDt_s: 0.000001, trackLength_um: 600, tracks: 1, layers: 1, surfaceMode: 'powder-layer',
    cooling_s: 0.0005, dwell_s: 0.0002 })) {
    assert.equal(job.result.settings[key], value, `resolved workflow setting ${key}`);
  }
  assert.equal(job.result.material.materialId, 'in718');
  // P7b (2026-10-14): the IN718 registry material absorbs the authority 0.32 (was 0.38, digest 5c9179e947ca...).
  assert.equal(job.result.material.materialRevisionSha256,
    '8bbceb4e810fd1554ff14ab72fbb8801fd7b5aa7bdc388f5af505e8da3d0ebd8');
  assert.match(job.result.provenance.inputHash, /^[a-f0-9]{64}$/);
  assert.match(job.result.provenance.implementationHash, /^[a-f0-9]{64}$/);
  assert.equal(job.result.solver.id, 'enthalpy-fv-6');
  assert.equal(job.result.coreContract.modelId, 'stationary-enthalpy-conduction-layer-conforming-v1');
  assert.equal(job.result.coreContract.actualBackend, 'numpy-reference');
  // The core contract uses compact canonical JSON; worker provenance hashes
  // Python's default JSON separators, so preserve and validate both bindings.
  assert.match(job.result.coreContract.inputSha256, /^[a-f0-9]{64}$/);
  assert.match(job.result.provenance.executionInputHash, /^[a-f0-9]{64}$/);
  assert.ok(job.result.energyBalance.relativeError <= 0.01, 'numerical ledger closes within the workflow gate');

  const selection = [{ ...sourceLink }];
  const previewResponse = await jsonRequestRetry503(base, '/preview', { jobId: submission.id, sources: selection });
  assert.equal(previewResponse.status, 200, JSON.stringify(previewResponse.payload));
  assert.equal(previewResponse.payload.sourceBindingStatus, 'exact-revision-bound');
  assert.equal(previewResponse.payload.document.capture.contractStatus, 'core-v1-bound');
  assert.deepEqual(previewResponse.payload.document.sources, selection);
  const importResponse = await jsonRequestRetry503(base, '/import', { jobId: submission.id, sources: selection });
  assert.equal(importResponse.status, 200, JSON.stringify(importResponse.payload));
  assert.deepEqual(importResponse.payload.document, previewResponse.payload.document);
  assert.match(importResponse.payload.documentSha256, /^[a-f0-9]{64}$/);

  const runId = importResponse.payload.document.runId as string;
  const selectedRun = await jsonRequest(base, `/${runId}`);
  assert.equal(selectedRun.status, 200);
  assert.equal(selectedRun.payload.sourceBindingStatus, 'exact-revision-bound');
  assert.equal(selectedRun.payload.evidenceStatus, 'unvalidated-model');
  assert.equal(selectedRun.payload.runKind, 'transient-thermal');

  const compared = await jsonRequest(base, `/${runId}/nist-comparison`, 'POST', { caseNumber: '0' });
  assert.equal(compared.status, 200, JSON.stringify(compared.payload));
  assert.equal(compared.payload.status, 'unavailable', 'the optical operator/process match is not implemented');
  assert.equal(compared.payload.validationStatus, 'unvalidated');
  assert.equal(compared.payload.errors, null);
  assert.ok(compared.payload.reasons.length > 0);

  const buildSubmission = await retryWorkerCall(() => lpbfWorker.request('submit', { jobType: 'build-job', alloyId: 'in718' }),
    Date.now() + workerBudget, { idempotent: false }) as { id: string };
  assert.match(buildSubmission.id, /^[a-f0-9]{32}$/);
  let buildJob: any;
  const buildDeadline = Date.now() + workerBudget;
  do {
    buildJob = await retryWorkerCall(() => lpbfWorker.request('get', buildSubmission.id), buildDeadline, { idempotent: true });
    if (['completed', 'failed', 'cancelled'].includes(buildJob.status)) break;
    await new Promise(resolve => setTimeout(resolve, 100));
  } while (Date.now() < buildDeadline);
  assert.equal(buildJob.status, 'completed', buildJob.error ?? `Build job remained ${buildJob.status}`);
  assert.equal(buildJob.result.runKind, 'build-screening');
  assert.equal(buildJob.result.success, true, buildJob.result.error);
  const materialSnapshot = buildJob.result.materialPropertySnapshot;
  const materialHash = buildJob.result.materialPropertySha256;
  assert.equal(materialSnapshot.alloyId, 'in718');
  assert.match(materialHash, /^[a-f0-9]{64}$/);
  assert.equal(sha256(canonicalBuildJobMaterialSnapshot(materialSnapshot)), materialHash);
  assert.equal(buildJob.result.material.propertySha256, materialHash);
  // The selected optical source does not establish derivation of build-job material properties.
  // Import this run without source links at the repository boundary; the HTTP import requires a selection.
  const buildCapture = await retryWorkerCall(() => lpbfWorker.captureForArchive(buildSubmission.id),
    Date.now() + workerBudget, { idempotent: true });
  const buildRuns = new LpbfRunRepository(path.join(runRoot, 'runs.sqlite'));
  const buildSources = new LpbfSourceRepository(path.join(sourceRoot, 'metadata.sqlite'), { readOnly: true });
  let buildImport;
  try {
    buildImport = await importRun(buildRuns, new LpbfArtifactStore(path.join(runRoot, 'artifacts')),
      buildCapture.capture, [], buildSources, buildCapture.root);
  } finally { buildRuns.close(); buildSources.close(); }
  assert.equal(buildImport.runKind, 'build-screening');
  assert.deepEqual(buildImport.document.sources, []);
  const buildRunId = buildImport.document.runId;
  const archivedBuild = JSON.parse(buildImport.document.capture.resultJson);
  assert.deepEqual(archivedBuild.materialPropertySnapshot, materialSnapshot);
  assert.equal(archivedBuild.materialPropertySha256, materialHash);
  assert.equal(archivedBuild.material.propertySha256, materialHash);

  const exported = await jsonRequest(base, '/bundles/export', 'POST');
  assert.equal(exported.status, 200, JSON.stringify(exported.payload));
  const bundleId = exported.payload.bundleId as string;
  assert.equal(exported.payload.manifest.runCount, 2);
  assert.equal(exported.payload.manifest.sourceLinkCount, 1);
  const bundleDownload = await fetch(`${base}/bundles/${bundleId}/download`);
  assert.equal(bundleDownload.status, 200);
  const bundleBytes = Buffer.from(await bundleDownload.arrayBuffer());
  assert.ok(bundleBytes.byteLength > 0);
  assert.equal((await jsonRequest(base, `/bundles/${bundleId}/verify`, 'POST')).payload.verified, true);
  const restored = await jsonRequest(base, `/bundles/${bundleId}/restore`, 'POST');
  assert.equal(restored.status, 200, JSON.stringify(restored.payload));
  assert.equal(restored.payload.verified, true);
  const restoredBuildResponse = await jsonRequest(base,
    `/bundles/restores/${restored.payload.restoreId}/runs/${buildRunId}`);
  assert.equal(restoredBuildResponse.status, 200);
  assert.equal(restoredBuildResponse.payload.runKind, 'build-screening');
  const restoredBuildResult = JSON.parse(restoredBuildResponse.payload.document.capture.resultJson);
  assert.deepEqual(restoredBuildResult.materialPropertySnapshot, materialSnapshot);
  assert.equal(restoredBuildResult.materialPropertySha256, materialHash);
  assert.equal(sha256(canonicalBuildJobMaterialSnapshot(restoredBuildResult.materialPropertySnapshot)), materialHash);

  const restoredRoot = path.join(bundleRoot, 'restores', restored.payload.restoreId);
  const restoredRuns = new LpbfRunRepository(path.join(restoredRoot, 'runs.sqlite'), { readOnly: true });
  const restoredSources = new LpbfSourceRepository(path.join(restoredRoot, 'sources/metadata.sqlite'), { readOnly: true });
  try {
    const record = restoredRuns.get(runId);
    assert.ok(record);
    assert.equal(record.documentSha256, importResponse.payload.documentSha256);
    assert.deepEqual(record.document.sources, selection);
    const buildRecord = restoredRuns.get(buildRunId);
    assert.ok(buildRecord);
    assert.equal(buildRecord.documentSha256, buildImport.documentSha256);
    assert.deepEqual(buildRecord.document.sources, []);
    const restoredSource = restoredSources.revision(sourceLink.datasetId, sourceLink.revision);
    assert.ok(restoredSource);
    assert.equal(restoredSource.documentSha256, sourceLink.documentSha256);
  } finally { restoredRuns.close(); restoredSources.close(); }

  const runArtifactRefs = JSON.parse(importResponse.payload.document.capture.resultJson).artifacts;
  const restoredRunStore = new LpbfArtifactStore(path.join(restoredRoot, 'artifacts'), { readOnly: true });
  for (const ref of runArtifactRefs) {
    const bytes = readFileSync((await restoredRunStore.verify({ sha256: ref.sha256, byteSize: ref.size_bytes })).path);
    assert.equal(sha256(bytes), ref.sha256);
    assert.equal(bytes.byteLength, ref.size_bytes);
  }
  const restoredSourceStore = new LpbfArtifactStore(path.join(restoredRoot, 'sources/artifacts'), { readOnly: true });
  const sourceArtifact = sourcePreview.document.artifacts[0];
  const sourceBytes = readFileSync((await restoredSourceStore.verify(sourceArtifact)).path);
  assert.equal(sha256(sourceBytes), sourceArtifact.sha256);
  assert.equal(sourceBytes.byteLength, sourceArtifact.byteSize);

  const evidencePath = process.env.METALLIKSA_WORKFLOW_EVIDENCE_OUT;
  if (evidencePath) {
    const output = path.resolve(evidencePath);
    mkdirSync(path.dirname(output), { recursive: true });
    writeFileSync(output, `${JSON.stringify({
      schemaVersion: 1,
      evidenceClass: 'isolated-live-cpu-workflow-archive-roundtrip',
      executionHead: process.env.METALLIKSA_WORKFLOW_EVIDENCE_HEAD ?? 'not-recorded',
      validationStatus: job.result.validationStatus,
      productionReady: job.result.productionReady,
      experimentalValidation: false,
      numericalConvergenceStatus: 'not-established',
      settings: job.result.settings,
      solver: job.result.solver,
      coreContract: job.result.coreContract,
      material: {
        materialId: job.result.material.materialId,
        quality: job.result.material.quality,
        provenanceClass: job.result.material.provenanceClass,
        materialRevisionSha256: job.result.material.materialRevisionSha256,
        propertyUncertainty: job.result.material.propertyUncertainty,
      },
      provenance: {
        inputHash: job.result.provenance.inputHash,
        executionInputHash: job.result.provenance.executionInputHash,
        implementationHash: job.result.provenance.implementationHash,
        executionRuntime: job.result.provenance.executionRuntime,
        solverSeconds: job.result.provenance.runtime_s,
      },
      energyBalance: job.result.energyBalance,
      thermalHistorySamples: job.result.thermalHistory.length,
      artifactCount: runArtifactRefs.length,
      run: {
        id: runId,
        documentSha256: importResponse.payload.documentSha256,
        sourceBindingStatus: selectedRun.payload.sourceBindingStatus,
        evidenceStatus: selectedRun.payload.evidenceStatus,
      },
      bundle: {
        id: bundleId,
        downloadSha256: sha256(bundleBytes),
        downloadByteSize: bundleBytes.byteLength,
        verified: true,
      },
      restore: {
        id: restored.payload.restoreId,
        verified: restored.payload.verified,
        runDocumentSha256: importResponse.payload.documentSha256,
        sourceDocumentSha256: sourceLink.documentSha256,
        artifactBytesRechecked: true,
      },
      comparison: {
        status: compared.payload.status,
        validationStatus: compared.payload.validationStatus,
        errors: compared.payload.errors,
      },
      limitations: [
        'Workflow replay and archive-integrity evidence only; no mesh/time convergence or experimental validation.',
        'NIST comparison residual remains unavailable and unvalidated.',
        'IN718 material properties are estimated legacy values with unquantified uncertainty.',
      ],
    }, null, 2)}\n`, 'utf8');
  }
});
