import React from 'react';
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { renderToStaticMarkup } from 'react-dom/server';
import { ModuleEvidenceDisclosure, evidenceBadgeView } from '../src/components/sdk/EvidenceBadge';
import { MODULES, MODULE_PURPOSE } from '../src/data/workspaces';
import { ModuleNav } from '../src/components/ModuleNav';
import { MODULE_CONTRACTS } from '../src/modules/registry';

// Maintainer-approved plain-English labels (docs/research/WORDING_PLAIN_LABELS_2026-10-22.md).
const read = (path: string) => readFileSync(new URL(`../${path}`, import.meta.url), 'utf8');
const labelOf = (id: string) => MODULES.find(m => m.id === id)?.label;

test('renamed modules show the approved names, ids unchanged', () => {
  assert.equal(labelOf('solidification-microstructure'), 'Solidification Map (cooling and grain structure)');
  assert.equal(labelOf('experimental-validation'), 'Melt Pool vs Published Measurements');
  assert.equal(labelOf('keyhole-raytracing'), 'Keyhole Laser Absorption');
  assert.equal(labelOf('lpbf-dataset-comparison'), 'Model vs Published Datasets (LPBF)');
  assert.equal(labelOf('lpbf-calibration-scorecard'), 'Model Error Scorecard (LPBF)');
  assert.equal(labelOf('experimental-data'), 'Measured Findings (user-labelled)');
  const sidebar = renderToStaticMarkup(<ModuleNav home={false} modules={[...MODULES]} activeTab="database" activeWorkspace="materials" onNavigate={() => undefined} />);
  assert.ok(sidebar.includes('Model Error Scorecard (LPBF)'));
  assert.ok(sidebar.includes(`title="${MODULE_PURPOSE['lpbf-optimizer']}"`), 'sidebar tooltip is the plain purpose sentence');
});

test('calibration scorecard description uses the plain wording', () => {
  const d = MODULES.find(m => m.id === 'lpbf-calibration-scorecard')!.description;
  assert.ok(d.includes('laser absorptivity fitted separately from the solver'));
  assert.ok(d.includes('Errors on data the model was not fitted to (each source left out in turn)'));
  assert.ok(!/nuisance|frozen code/.test(d));
});

test('module header disclosure renders the approved summary and body text', () => {
  const contract = MODULE_CONTRACTS.find(c => c.id === 'keyhole-raytracing')!;
  const view = evidenceBadgeView(contract)!;
  assert.match(view.text, /^Strongest claim allowed: Screening only\. Reference check: (available|not yet available)$/);
  const html = renderToStaticMarkup(<ModuleEvidenceDisclosure moduleId="keyhole-raytracing" />);
  assert.ok(html.includes('<summary>What this result can claim</summary>'));
  assert.ok(html.includes('The strongest kind of evidence this module is allowed to report.'));
  assert.ok(html.includes('This is a limit, not a grade for any single result, and not a validation.'));
  assert.ok(html.includes('The reference check is not run automatically here (it needs the Warp GPU stack).'));
  assert.ok(!/Max claim|Oracle|contract\./.test(html));
});

test('shell strings: header, engine status, shared-material panel, CALPHAD and LPBF workflow header', () => {
  const app = read('src/App.tsx');
  for (const text of ['Runs on this computer', 'Calculation engine ready', 'Calculation engine unavailable', 'Material and settings in use',
    'Module status: Production, Research, Preview or Unresolved.', 'Energy balance, mesh convergence and comparison with experiments are three separate checks.']) {
    assert.ok(app.includes(text), text);
  }
  assert.ok(!app.includes('Active surface') && !app.includes('Python daemon') && !app.includes('Context & trust'));
  const calphad = read('src/components/CALPHADMultiComponentStudio.tsx');
  assert.ok(calphad.includes('SHARED MATERIAL') && calphad.includes('Follow shared material: ON') && calphad.includes('Follow shared material: PAUSED'));
  assert.ok(read('src/components/LpbfEngineeringWorkspace.tsx').includes('One material, one set of laser settings, with every run and source recorded.'));
});
