import assert from 'node:assert/strict';
import type { LpbfSourceDocument } from '../src/types/lpbfSource';
import { createHash } from 'node:crypto';
import { existsSync, mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { test } from 'node:test';
import express from 'express';
import { createLpbfRunsRouter } from '../routes/lpbfRuns';
import { verifyLedgerFile } from '../server/auditLedger';
import { LpbfArtifactStore } from '../server/lpbfArtifactStore';
import { LpbfRunArchiveService } from '../server/lpbfRunArchiveService';
import { LpbfRunRepository } from '../server/lpbfRunRepository';
import { LpbfSourceRepository } from '../server/lpbfSourceRepository';
import { in625BareplateScreeningCatalogEntry } from '../server/lpbfSourceCatalog';
import { lpbfWorker } from '../server/lpbfWorkerBridge';

const sha = (value: string) => createHash('sha256').update(value).digest('hex');
const jobId = 'a'.repeat(32);

test('run HTTP archive resolves exact source and preserves analytical screening classification', async t => {
  const root = mkdtempSync(path.join(tmpdir(), 'lpbf-run-api-'));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  const sourceRoot = path.join(root, 'sources'), runRoot = path.join(root, 'runs');
  mkdirSync(sourceRoot);
  const sourceRepo = new LpbfSourceRepository(path.join(sourceRoot, 'metadata.sqlite'));
  const raw = path.join(root, 'raw'); mkdirSync(raw); writeFileSync(path.join(raw, 'raw.bin'), 'raw');
  const artifact = { relativePath: 'raw.bin', sha256: sha('raw'), byteSize: 3, sourceUrl: 'https://example.org/raw' };
  const source = { schemaVersion: 1, datasetId: 'synthetic', materialId: 'in718', processScope: 'unknown',
    source: { url: 'https://example.org/source', citation: 'Synthetic test only', version: '1', terms: null, termsMissingReason: 'Unknown' },
    artifacts: [artifact], sourceContext: null };
  const sourceStore = new LpbfArtifactStore(path.join(sourceRoot, 'artifacts'));
  await sourceStore.putFile(raw, 'raw.bin', artifact);
  const revision1 = sourceRepo.save(source, 0);
  source.source.version = '2'; sourceRepo.save(source, 1);
  sourceRepo.close();

  const job = path.join(root, 'job'); mkdirSync(job);
  writeFileSync(path.join(job, 'field.bin'), 'abc');
  const result = { schemaVersion: 1, runKind: 'analytical-screening', requestedMode: 'screening', effectiveMode: 'screening',
    fallbackReason: null, validationStatus: 'unvalidated', productionReady: false, confidence: 'low',
    settings: { backend: 'auto', mode: 'screening', power_W: 0 }, resolvedPhysics: { transient: false },
    solver: { id: 'synthetic-contract-test', version: '1' },
    material: { name: 'Synthetic', quality: 'synthetic', source: 'Unit test only' },
    label: 'Screening', regime: 'test', mainRisk: 'test', recommendation: 'test', riskScope: 'test',
    metrics: { width_um: 0, depth_um: 0, length_um: 0 }, assumptions: ['Synthetic only'],
    analyticalComparison: { goldak: { width_um: 0, depth_um: 0, length_um: 0 } },
    provenance: { executionRuntime: null },
    artifacts: [{ path: 'field.bin', size_bytes: 3, sha256: sha('abc') }] };
  const capture = { schemaVersion: 1, jobId, resultJson: JSON.stringify(result),
    inputJson: JSON.stringify(result.settings), materialJson: JSON.stringify(result.material),
    contractStatus: 'legacy-unbound', runKind: 'analytical-screening' as const };
  writeFileSync(path.join(job, 'result.json'), capture.resultJson);
  let captured = 0;
  t.mock.method(lpbfWorker, 'captureForArchive', async () => { captured++; return { capture, root: job }; });

  const service = new LpbfRunArchiveService(runRoot, sourceRoot);
  const app = express(); app.use(createLpbfRunsRouter(service));
  const server = app.listen(0, '127.0.0.1');
  t.after(() => server.close());
  await new Promise<void>(resolve => server.once('listening', resolve));
  const address = server.address(); assert.ok(address && typeof address !== 'string');
  const endpoint = `http://127.0.0.1:${address.port}/api/lpbf/runs`;
  async function post(action: string, sources: unknown) {
    const response = await fetch(`${endpoint}/${action}`, { method: 'POST',
      headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ jobId, sources }) });
    return { status: response.status, body: await response.json() };
  }

  const empty = await post('preview', []);
  assert.equal(empty.status, 400); assert.match(empty.body.error, /source revision/i);
  assert.equal(captured, 0, 'bad selections fail before worker capture');
  const missing = await post('preview', [{ datasetId: 'synthetic', revision: 3 }]);
  assert.equal(missing.status, 404);
  const changed = await post('preview', [{ datasetId: 'synthetic', revision: 1, documentSha256: sha('stale') }]);
  assert.equal(changed.status, 409);
  const selected = [{ datasetId: 'synthetic', revision: 1, documentSha256: revision1.documentSha256 }];
  const preview = await post('preview', selected);
  assert.equal(preview.status, 200);
  assert.equal(preview.body.document.capture.runKind, 'analytical-screening');
  assert.deepEqual(preview.body.document.sources, selected);
  assert.equal(preview.body.sourceBindingStatus, 'exact-revision-bound');
  const imported = await post('import', [{ datasetId: 'synthetic', revision: 1 }]);
  assert.equal(imported.status, 200);
  assert.equal(imported.body.runKind, 'analytical-screening');
  assert.deepEqual(imported.body.document.sources, selected);
  assert.equal(imported.body.sourceBindingStatus, 'exact-revision-bound');
  // The audit ledger lives under the temp run root; nothing may be written to the checkout's .runtime.
  const ledgerState = verifyLedgerFile(path.join(runRoot, 'audit', 'ledger.jsonl'));
  assert.equal(ledgerState.chainValid, true);
  assert.deepEqual(ledgerState.entries.map(entry => entry.runId), [jobId]);
  assert.equal(existsSync(path.resolve('.runtime', 'audit', 'ledger.jsonl')), false, 'tests must not touch the real ledger');
  const record = await (await fetch(`${endpoint}/${jobId}`)).json();
  assert.equal(record.sourceBindingStatus, 'exact-revision-bound');
  assert.equal(record.evidenceStatus, 'unvalidated-model');
  const listed = await (await fetch(endpoint)).json();
  assert.equal(listed[0].sourceBindingStatus, 'exact-revision-bound');
  assert.equal(listed[0].runKind, 'analytical-screening');
  assert.equal((await (await fetch(`${endpoint}/${jobId}`)).json()).runKind, 'analytical-screening');

  const legacyId = 'b'.repeat(32);
  const legacyRepo = new LpbfRunRepository(path.join(runRoot, 'runs.sqlite'));
  try { legacyRepo.save({ schemaVersion: 1, runId: legacyId,
    capture: { ...capture, jobId: legacyId }, sources: [] }); }
  finally { legacyRepo.close(); }
  const legacy = await (await fetch(`${endpoint}/${legacyId}`)).json();
  assert.equal(legacy.sourceBindingStatus, 'legacy-unlinked');
  assert.equal(legacy.evidenceStatus, 'unvalidated-model');

  const unresolvedId = 'c'.repeat(32);
  const unresolvedRepo = new LpbfRunRepository(path.join(runRoot, 'runs.sqlite'));
  try { unresolvedRepo.save({ schemaVersion: 1, runId: unresolvedId,
    capture: { ...capture, jobId: unresolvedId },
    sources: [{ datasetId: 'synthetic', revision: 99, documentSha256: sha('missing-source-revision') }] }); }
  finally { unresolvedRepo.close(); }
  const unresolved = await (await fetch(`${endpoint}/${unresolvedId}`)).json();
  assert.equal(unresolved.sourceBindingStatus, 'unverified-source-link');
  const unresolvedList = await (await fetch(endpoint)).json();
  assert.equal(unresolvedList.find((item: { runId: string }) => item.runId === unresolvedId).sourceBindingStatus,
    'unverified-source-link');

  writeFileSync((await sourceStore.verify(artifact)).path, 'bad');
  const invalidBytes = await post('preview', selected);
  assert.equal(invalidBytes.status, 409); assert.match(invalidBytes.body.error, /artifact bytes/i);
});

test('IN625 worker capture shape round-trips through source-bound run preview', async t => {
  const root = mkdtempSync(path.join(tmpdir(), 'lpbf-in625-run-preview-'));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  const sourceRoot = path.join(root, 'sources'), runRoot = path.join(root, 'runs'), jobRoot = path.join(root, 'job');
  mkdirSync(sourceRoot); mkdirSync(jobRoot);
  const sourceRepo = new LpbfSourceRepository(path.join(sourceRoot, 'metadata.sqlite'));
  const sourceEntry = in625BareplateScreeningCatalogEntry();
  const sourceDocument = sourceEntry.loadDocument() as LpbfSourceDocument; // LpbfSourceCatalogEntry.loadDocument is typed unknown; catalogs return validated source documents
  const sourceObjects = new LpbfArtifactStore(path.join(sourceRoot, 'artifacts'));
  for (const artifact of sourceDocument.artifacts) await sourceObjects.putFile(sourceEntry.sourceRoot, artifact.relativePath, artifact);
  const sourceRevision = sourceRepo.save(sourceDocument, 0);
  sourceRepo.close();

  const jobId = 'c'.repeat(32);
  const settings = { jobType: 'in625-bareplate-field', backend: 'cpu', config: {
    shapeXYZ: [2, 2, 2], cellSizeM: [1e-4, 1e-4, 1e-4], initialTemperatureK: 300,
    dtS: 0.001, steps: 1, absorbedPowerW: 0, spotSigmaM: 1e-4,
    scanStartXM: 0, scanYM: 0, scanVelocityXMS: 1,
  } };
  const material = JSON.parse(readFileSync(path.join(sourceEntry.sourceRoot, 'in625-thermal-snapshot-v1.json'), 'utf8'));
  const fieldBytes = Buffer.alloc(8 * settings.config.shapeXYZ.reduce((a, b) => a * b, 1));
  const fieldHash = createHash('sha256').update(fieldBytes).digest('hex');
  writeFileSync(path.join(jobRoot, 'in625-temperature-field-f64le.bin'), fieldBytes);
  const result = {
    schemaVersion: 1, jobType: 'in625-bareplate-field', runKind: 'bounded-material-screening',
    requestedMode: 'screening', effectiveMode: 'screening', fallbackReason: null,
    settings, material,
    solver: { id: 'in625-bareplate-field-v1', modelId: 'in625-bareplate-enthalpy-conduction-v1',
      revision: '1', actualBackend: 'cpu', device: 'cpu', dtype: 'float64' },
    validationStatus: 'unvalidated-literature-model-screening', productionReady: false, confidence: 'low',
    label: 'IN625 bare-substrate conduction screening',
    modelScope: '3D bounded enthalpy conduction on bare substrate; all faces adiabatic; no powder, melt pool, absorptivity, vapor, flow, or free-surface physics',
    metrics: { cells: 8, peakTemperature_K: 300, finalTime_s: 0.001, finalEnthalpy_J: 0,
      energyResidual_J: 0, minimumSourceCaptureFraction: 1 },
    energyHistory: [{ time_s: 0.001, totalEnthalpy_J: 0, peakTemperature_K: 300, energyResidual_J: 0 }],
    energyBalance: { input_J: 0, losses_J: 0, stored_J: 0, relativeError: 0,
      scope: 'adiabatic bareplate enthalpy accounting; not melt-pool or interface closure' },
    field: { artifact: 'in625-temperature-field-f64le.bin', shapeXYZ: [2, 2, 2], dtype: 'float64',
      encoding: 'little-endian', byteOrder: 'little-endian', arrayOrder: 'z,y,x', sha256: fieldHash,
      scope: 'final cell-centered temperature field only; no interface interpolation' },
    numericalDiagnostics: { sourceCaptureFractionMinimum: 1, temperatureBounds_K: [273.15, 1623.15],
      density_kg_m3: 8440, densityBasis: 'fixed supplier-bulletin density assumption; not lot-matched' },
    provenance: { inputSha256: sha(JSON.stringify(settings)),
      implementationIdentity: { modelId: 'in625-bareplate-enthalpy-conduction-v1', solverRevision: '1',
        materialRevisionSha256: material.materialRevisionSha256, backend: 'cpu', device: 'cpu' },
      deviceEvidence: { selected: 'cpu', thermalEvolution: 'cpu', noCpuFallback: true, name: 'NumPy CPU',
        synchronizedAfterSolve: true } },
    artifacts: [{ path: 'in625-temperature-field-f64le.bin', size_bytes: fieldBytes.length, sha256: fieldHash }],
    assumptions: ['Constant 8440 kg/m^3 supplier-bulletin density assumption; not lot-matched.',
      'Source input is absorbed power in W; no optical absorptivity is inferred.',
      'Constitutive law is bounded to 273.15..1623.15 K and remains unvalidated literature-model screening.'],
  };
  const resultJson = JSON.stringify(result);
  writeFileSync(path.join(jobRoot, 'result.json'), resultJson);
  const capture = { schemaVersion: 1, jobId, resultJson, inputJson: JSON.stringify(settings),
    materialJson: JSON.stringify(material), contractStatus: 'legacy-unbound',
    runKind: 'bounded-material-screening' as const };
  t.mock.method(lpbfWorker, 'captureForArchive', async () => ({ capture, root: jobRoot }));

  const service = new LpbfRunArchiveService(runRoot, sourceRoot);
  const app = express(); app.use(createLpbfRunsRouter(service));
  const server = app.listen(0, '127.0.0.1');
  t.after(() => server.close());
  await new Promise<void>(resolve => server.once('listening', resolve));
  const address = server.address(); assert.ok(address && typeof address !== 'string');
  const endpoint = `http://127.0.0.1:${address.port}/api/lpbf/runs/preview`;
  const selected = [{ datasetId: sourceRevision.document.datasetId, revision: sourceRevision.revision,
    documentSha256: sourceRevision.documentSha256 }];
  const response = await fetch(endpoint, { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ jobId, sources: selected }) });
  assert.equal(response.status, 200);
  const preview = await response.json();
  assert.equal(preview.document.capture.runKind, 'bounded-material-screening');
  assert.equal(preview.document.capture.resultJson, resultJson);
  assert.deepEqual(preview.document.sources, selected);
  assert.equal(preview.document.capture.materialJson, JSON.stringify(material));
  assert.equal(preview.sourceBindingStatus, 'exact-revision-bound');
  assert.equal(preview.artifactIntegrity, 'verified-at-dry-run');
});
