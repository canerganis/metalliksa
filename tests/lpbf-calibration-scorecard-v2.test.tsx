import React from 'react';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import test from 'node:test';
import { renderToStaticMarkup } from 'react-dom/server';
import { LpbfCalibrationScorecardLab } from '../src/components/LpbfCalibrationScorecardLab';
import { checkedCalibrationScorecard, statusCounts } from '../src/data/lpbfCalibrationScorecard';

// Calibration v2 records (a new pre-registered version; v1 stays committed). The fixture is the SYNTHETIC v1 view
// fixture with the v2 fields added here, so the test carries its own data.
const base = (): Record<string, unknown> => JSON.parse(readFileSync('tests/fixtures/lpbf-calibration-scorecard.sample.json', 'utf8'));

function v2Fixture(): Record<string, unknown> {
  const raw = base();
  const headline = raw.headline as Record<string, unknown>[];
  const first = headline[0];
  const p2 = (first.p2 as Record<string, unknown>[]);
  const extra = { ...(p2[0] ?? { trainedOn: [], rung: 'default', nRows: 7, nSets: 7, mapeDefault: 10, mapeServed: 10, skill: 0, skillCi95: [0, 0], unresolvedDefault: 0, unresolvedServed: 0, coverage90: null }), heldOut: 'ghosh-in625-2018', role: 'test-only', reading: '140' };
  first.p2 = [...p2.map((p) => ({ ...p, role: 'trainable fold' })), extra];
  raw.calibrationVersion = 'v2';
  raw.preRegistration = { doc: 'docs/LPBF_CALIBRATION_V2_PREREGISTRATION_2026-10-07.md', config: 'python/lpbf_calibration_config_v2.py', configCommit: 'synthetic', statement: 'synthetic' };
  raw.supersedes = { record: 'docs/LPBF_CALIBRATION_SCORECARD_2026-10-07.json', configSha256: 'a'.repeat(64), calibrationId: 'synthetic', note: 'v1 is kept unchanged' };
  raw.v1Comparison = headline.map((h) => ({ kernel: h.kernel, material: h.material, quantity: h.quantity, v1: h.status, v2TrainableOnly: h.status, v2: h.status, changed: false }));
  raw.reproducesV1TrainableOnly = true;
  return raw;
}

test('v2 record validates and renders the version card and test-only rows', () => {
  const doc = checkedCalibrationScorecard(v2Fixture());
  const html = renderToStaticMarkup(<LpbfCalibrationScorecardLab document={doc} />);
  assert.ok(html.includes('data-testid="version-table"'));
  assert.ok(html.includes('Calibration v2'));
  assert.ok(html.includes('LPBF_CALIBRATION_V2_PREREGISTRATION_2026-10-07.md'));
  assert.ok(html.includes('reproduces every v1 status'));
  assert.ok(html.includes('data-role="test-only"'));
  assert.ok(html.includes('spot 140 µm'));
  assert.ok(html.includes('Screening only'));
});

test('a v1 record renders no version card', () => {
  const html = renderToStaticMarkup(<LpbfCalibrationScorecardLab document={checkedCalibrationScorecard(base())} />);
  assert.doesNotMatch(html, /data-testid="version-table"/);
  assert.doesNotMatch(html, /data-role="test-only"/);
});

test('validator refuses a versioned record without pre-registration or with a bad comparison status', () => {
  const noPrereg = v2Fixture();
  delete noPrereg.preRegistration;
  assert.throws(() => checkedCalibrationScorecard(noPrereg), /preRegistration/);
  const noSup = v2Fixture();
  delete noSup.supersedes;
  assert.throws(() => checkedCalibrationScorecard(noSup), /supersedes/);
  const bad = v2Fixture();
  (bad.v1Comparison as Record<string, unknown>[])[0].v2 = 'validated';
  assert.throws(() => checkedCalibrationScorecard(bad), /v1Comparison\[0\]\.v2/);
});

test('the committed v2 record (if present) validates, agrees with its artefact, and calibrated mode still reads v1', () => {
  const view = 'docs/LPBF_CALIBRATION_SCORECARD_v2_2026-10-07.view.json';
  const artefact = 'data/calibration/lpbf-meltpool-calibration-v2.json';
  const artefactSource = readFileSync('src/data/lpbfCalibrationArtefact.ts', 'utf8');
  assert.ok(artefactSource.includes('lpbf-meltpool-calibration-v1.summary.json'), 'calibrated mode is wired to the v1 artefact only');
  assert.doesNotMatch(artefactSource, /calibration-v2/);
  if (!existsSync(view) || !existsSync(artefact)) return;
  const real = checkedCalibrationScorecard(JSON.parse(readFileSync(view, 'utf8')));
  assert.equal(real.calibrationVersion, 'v2');
  assert.equal(real.evidence.experimentalValidation, false);
  assert.equal(real.evidence.labelPromotionProposed, 'none');
  const art = JSON.parse(readFileSync(artefact, 'utf8')) as { cells: { kernel: string; material: string; quantity: string; status: string }[]; servedByRuntime: boolean; proposedEvidenceKind: unknown };
  assert.equal(art.servedByRuntime, false);
  assert.equal(art.proposedEvidenceKind, null);
  for (const row of real.headline) {
    const cell = art.cells.find((c) => c.kernel === row.kernel && c.material === row.material && c.quantity === row.quantity);
    assert.ok(cell);
    assert.equal(cell.status, row.status);
  }
  const html = renderToStaticMarkup(<LpbfCalibrationScorecardLab document={real} />);
  assert.ok(html.includes('data-testid="version-table"'));
  if (statusCounts(real).enabled === 0) assert.ok(html.includes('data-testid="none-enabled"'));
});
