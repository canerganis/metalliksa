import assert from 'node:assert/strict';
import { test } from 'node:test';
import { existsSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { LpbfSourceArchiveService } from '../server/lpbfSourceArchiveService';
import { LpbfRunArchiveService } from '../server/lpbfRunArchiveService';
import { lpbfWorker } from '../server/lpbfWorkerBridge';

// The bridge answers LPBF_WORKER_STARTING while the Python worker is still importing modules ("Retry shortly").
// Under full-suite load that can take longer than one request deadline, so the test retries that one code a
// bounded number of times, as an HTTP caller would. Any other error fails the test immediately.
async function requestWhenStarted(op: string, payload: unknown, attempts = 6): Promise<any> {
  for (let attempt = 1; ; attempt += 1) {
    try {
      return await (lpbfWorker as any).request(op, payload);
    } catch (error: any) {
      if (error?.code !== 'LPBF_WORKER_STARTING' || attempt >= attempts) throw error;
      await new Promise(resolve => setTimeout(resolve, 2000));
    }
  }
}

test('Phase 4: Uçtan Uca Test - Calisma Secimi -> Is Calistirma -> Karsilastirma -> Export/Import', async t => {
  const optionalRawRoot = path.resolve('data/benchmark/cmu-ti64-meltpool-v1/raw');
  const requiredPayloads = ['STMeasurements.csv', 'MTMeasurements.csv', 'README.txt'];
  const missingPayloads = requiredPayloads.filter(name => !existsSync(path.join(optionalRawRoot, name)));
  if (missingPayloads.length > 0) {
    t.skip(`Optional CMU source payload is not restored: ${missingPayloads.join(', ')}`);
    return;
  }
  try {
    const directory = mkdtempSync(path.join(tmpdir(), 'metalliksa-e2e-'));
    const sourceRoot = path.join(directory, 'sources');
    const runRoot = path.join(directory, 'runs');
    const jobRoot = path.join(directory, 'jobs');
    t.after(() => { 
      lpbfWorker.close();
      try { rmSync(directory, { recursive: true, force: true }); } catch (e) {}
    });

    process.env.METALLIKSA_LPBF_SOURCE_ROOT = sourceRoot;
    process.env.METALLIKSA_LPBF_RUN_ROOT = runRoot;
    process.env.METALLIKSA_JOB_ROOT = jobRoot;

    const sourceService = new LpbfSourceArchiveService();
    const runService = new LpbfRunArchiveService();

    const catalog = sourceService.catalog();
    assert.ok(catalog.sources.length > 0, 'Catalog should have sources');
    const datasetId = 'cmu-ti64-meltpool-v1';

    const preview = await sourceService.preview(datasetId);
    assert.ok(preview.documentSha256, 'Preview must have a hash');

    const importedSource = await sourceService.import(datasetId, preview.expectedRevision, preview.documentSha256);
    assert.equal(importedSource.revision.revision, 1);

    const measurements = sourceService.measurements(datasetId);
    assert.ok(measurements.data.length > 0, 'Measurements must have data');
    const sample = measurements.data.find((d: any) => d.power_W === 370);
    assert.ok(sample, 'Expected 370W sample');

    const request = {
      jobType: "build-job",
      alloyId: "ti6al4v",
      laserPower_W: sample.power_W,
      scanSpeed_mms: sample.velocity_mms,
      beamDiameter_um: 80,
      layerThickness_um: 30,
      hatchSpacing_um: 100,
      preheatTemp_C: 25,
      enableUq: false,
      includeAmbench: false,
      bypassCache: true,
      timeout_s: 300
    };
    
    let submitResponse: any;
    try {
      submitResponse = await requestWhenStarted('submit', request);
    } catch (err: any) {
      console.error("SUBMIT ERROR:", err);
      throw err;
    }
    assert.ok(submitResponse.id, 'Job should be submitted and return an ID');

    let job: any;
    for (let i = 0; i < 20; i++) {
      job = await lpbfWorker.request('get', submitResponse.id);
      console.log("JOB STATUS:", job.status);
      if (job.status === 'completed' || job.status === 'cancelled' || job.status === 'failed') break;
      await new Promise(r => setTimeout(r, 500));
    }
    
    if (job.status !== 'completed') {
      console.log("JOB FAILED OR CANCELLED:", job);
    }

    assert.equal(job.status, 'completed', 'Job should complete successfully');
    
    const simResult = job.result;
    assert.equal(simResult.success, true, 'simResult.success should be true');
    assert.ok(simResult.thermal.meltPoolGeometry.width_um > 0, 'Melt pool width must be > 0');

    const sourcesToImport = [{ datasetId, revision: importedSource.revision.revision, documentSha256: preview.documentSha256 }];
    console.log("SOURCES TO IMPORT:", JSON.stringify(sourcesToImport));
    const archivePreview = await runService.preview(job.id, sourcesToImport);
    assert.ok(archivePreview.byteSize > 0, 'Archive preview byte size should be > 0');
    
    const archiveResult = await runService.import(job.id, [{ datasetId, revision: importedSource.revision.revision, documentSha256: preview.documentSha256 }]);
    assert.ok(archiveResult.document.runId, 'Archived run should have an ID');
  } catch (e) {
    console.error("TEST FAILED WITH ERROR:", e);
    throw e;
  }
});
