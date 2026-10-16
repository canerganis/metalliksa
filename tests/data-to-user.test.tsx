import React from 'react';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import test from 'node:test';
import { renderToStaticMarkup } from 'react-dom/server';
import { getHostPython } from '../server/pythonRuntime';
import { DATA_TO_USER, SPENT_ENTRIES, isOpenDataset, spentPoints, signedDeviation } from '../src/data/spentDatasets';
import { LpbfDatasetComparisonLab } from '../src/components/3d-distortion-lab/LpbfDatasetComparisonLab';
import { ServedConstantsView } from '../src/components/ServedConstantsView';

const tables = Object.fromEntries(['ku-leuven-316l-ti64-2021/conditions.csv', 'totis-ti64-2021/tracks.csv'].map(path =>
  [`../../data/benchmark/${path}`, readFileSync(`data/benchmark/${path}`, 'utf8')]));

test('licences fail closed and all six SPENT sets remain visible', () => {
  assert.equal(SPENT_ENTRIES.length, 6);
  for (const entry of SPENT_ENTRIES) {
    const points = spentPoints(entry, tables);
    if (entry.datasetId.startsWith('lane-') || entry.datasetId.startsWith('cunningham-')) {
      assert.equal(isOpenDataset(entry), false);
      assert.deepEqual(points, []);
      assert.ok(!Object.keys(DATA_TO_USER.samples).some(k => k.startsWith(entry.datasetId)));
    } else {
      assert.ok(points.length > 0, entry.datasetId);
      assert.ok(points.every(p => p.sample), entry.datasetId);
    }
  }
  assert.equal(isOpenDataset({ ...SPENT_ENTRIES[0], licence: 'unresolved' }), false);
});

test('condition identity matches served inputs and deviations retain their signs', () => {
  for (const entry of SPENT_ENTRIES) for (const p of spentPoints(entry, tables)) {
    assert.equal(p.sample?.inputs.laser_power_W, p.power);
    assert.equal(p.sample?.inputs.scan_speed_mm_s, p.speed);
    assert.equal(p.sample?.inputs.beam_diameter_um, p.beam);
    assert.equal(p.sample?.modelId, 'rosenthal-screening-v1');
  }
  const point = spentPoints(SPENT_ENTRIES[0], tables)[0];
  assert.equal(signedDeviation({ ...point, measured: 1, sample: { ...point.sample!, depth_um: 3 } }), '+2.0');
  assert.equal(signedDeviation({ ...point, measured: 5, sample: { ...point.sample!, depth_um: 3 } }), '-2.0');
  assert.equal(signedDeviation({ ...point, sample: null }), 'Unavailable');
});

test('default lab shows descriptive observations without the dated pooled accuracy summary', () => {
  const html = renderToStaticMarkup(<LpbfDatasetComparisonLab />);
  assert.ok(html.includes('Descriptive: not validation; this data was already seen'));
  assert.ok(html.includes('Signed deviation'));
  assert.ok(html.includes('Measured depth (µm)'));
  assert.ok(!html.includes('MAPE'));
  assert.ok(!html.includes('within ±30'));
  assert.equal((html.match(/<option /g) ?? []).length, 6);
});

test('constant evidence remains unresolved without a value-specific admitted source', () => {
  const html = renderToStaticMarkup(<ServedConstantsView />);
  assert.equal(DATA_TO_USER.alloys.length, 5);
  for (const alloy of DATA_TO_USER.alloys) {
    assert.ok(html.includes(alloy.name));
    for (const c of alloy.constants) {
      assert.ok(['Unresolved', 'Literature estimate'].includes(c.sourceEvidenceKind));
      if (c.source === 'Unresolved') assert.equal(c.sourceEvidenceKind, 'Unresolved');
    }
  }
  const al = DATA_TO_USER.alloys.find(a => a.id === 'alsi10mg')!;
  assert.equal(al.constants.find(c => c.quantity === 'specific_heat_liquid_J_kgK')?.sourceEvidenceKind, 'Unresolved');
  assert.equal(al.constants.find(c => c.quantity === 'density_liquid_kg_m3')?.sourceEvidenceKind, 'Literature estimate');
  // SOL-T: admitted endpoint conventions are Literature estimates that carry their transfer scope, never Measured.
  const alLiquidus = al.constants.find(c => c.quantity === 'liquidus_C')!;
  assert.equal(alLiquidus.value, 599);
  assert.equal(alLiquidus.sourceEvidenceKind, 'Literature estimate');
  assert.equal(alLiquidus.basis, 'admitted-nominal-convention');
  assert.ok(alLiquidus.note.includes('Al-9Si-0.6Mg'));
  const ti = DATA_TO_USER.alloys.find(a => a.id === 'ti6al4v')!;
  assert.ok(ti.constants.find(c => c.quantity === 'liquidus_C')!.note.includes('Cezairliyan'));
});

test('projection contains no measurement copies and matches current source identities', () => {
  for (const sample of Object.values(DATA_TO_USER.samples)) {
    assert.deepEqual(Object.keys(sample).sort(), ['depth_um', 'extentNote', 'extentStatus', 'inputs', 'modelId']);
  }
  for (const [path, digest] of Object.entries(DATA_TO_USER.sourceHashes)) {
    const bytes = path.endsWith('.py') ? Buffer.from(readFileSync(path, 'utf8').replaceAll('\r\n', '\n')) : readFileSync(path);
    assert.equal(createHash('sha256').update(bytes).digest('hex'), digest, path);
  }
  const python = getHostPython();
  const result = spawnSync(python.cmd, [...python.prefix, '-B', 'scripts/emit-data-to-user.py', '--check'], { encoding: 'utf8', timeout: 60000 });
  assert.equal(result.status, 0, result.stderr || result.error?.message);
});
