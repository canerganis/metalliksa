import React from 'react';
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { renderToStaticMarkup } from 'react-dom/server';
import { ContractEvidenceBadge, EvidenceBadge, ModuleEvidenceDisclosure, evidenceBadgeView } from '../src/components/sdk/EvidenceBadge';
import { MODULES, MODULE_PURPOSE } from '../src/data/workspaces';
import { MODULE_CONTRACTS, MODULE_REGISTRY_CORE as MODULE_REGISTRY, type EvidenceType, type RegisteredContract } from '../src/modules/registry';

const EVIDENCE_TYPES = MODULE_REGISTRY.vocabulary.evidenceTypes as readonly EvidenceType[];
// Lower index = stronger claim (python/module_contract.py EVIDENCE_RANK).
const rank = (type: string) => EVIDENCE_TYPES.indexOf(type as EvidenceType);
const LABELS = ['Measured', 'Validated simulation', 'Calibrated simulation', 'Literature estimate', 'Screening only', 'Unresolved'];
const read = (path: string) => readFileSync(new URL(`../${path}`, import.meta.url), 'utf8');

test('the badge shows exactly the contract ceiling and no stronger evidence class', () => {
  const contracted = MODULE_CONTRACTS.filter(contract => contract.migrationState === 'contracted');
  assert.deepEqual(contracted.map(contract => contract.id), ['lpbf-optimizer', 'solidification-microstructure', 'keyhole-raytracing', 'lpbf-dataset-comparison', 'lpbf-calibration-scorecard', 'database', 'phase-diagram', 'experimental-data', 'traceability']);
  for (const contract of contracted) {
    const html = renderToStaticMarkup(<EvidenceBadge moduleId={contract.id} />);
    const ceiling = contract.evidence.ceiling;
    assert.match(html, new RegExp(`data-evidence-ceiling="${ceiling}"`), contract.id);
    assert.match(html, new RegExp(`data-oracle="${contract.tests.oracle.status}"`), contract.id);
    assert.ok(html.includes(`Max claim: ${LABELS[rank(ceiling)]}`), contract.id);
    for (const stronger of LABELS.slice(0, rank(ceiling))) assert.ok(!html.includes(stronger), `${contract.id} shows ${stronger}`);
    assert.ok(!/qualified|certified|validated|airworthy/i.test(html), contract.id);
  }
});

test('callers cannot raise the ceiling: the badge has no evidence input', () => {
  // @ts-expect-error EvidenceBadge accepts only a module id; a ceiling prop is a type error.
  const html = renderToStaticMarkup(<EvidenceBadge moduleId="keyhole-raytracing" ceiling="measured" status="validated-simulation" />);
  assert.match(html, /data-evidence-ceiling="screening-only"/);
  assert.ok(!html.includes('Measured') && !html.includes('Validated simulation'));
  // Legacy and unknown modules render nothing rather than a placeholder claim.
  for (const contract of MODULE_CONTRACTS.filter(item => item.migrationState === 'legacy')) {
    assert.equal(renderToStaticMarkup(<EvidenceBadge moduleId={contract.id} />), '', contract.id);
  }
  assert.equal(renderToStaticMarkup(<EvidenceBadge moduleId="not-a-module" />), '');
});

test('the view is a pure projection of whatever ceiling the contract holds', () => {
  const base = MODULE_CONTRACTS.find(contract => contract.id === 'keyhole-raytracing') as RegisteredContract;
  for (const ceiling of EVIDENCE_TYPES) {
    const contract = { ...base, evidence: { ...base.evidence, ceiling } } as RegisteredContract;
    const view = evidenceBadgeView(contract);
    assert.equal(view?.ceiling, ceiling);
    assert.ok(view?.text.startsWith(`Max claim: ${LABELS[rank(ceiling)]} ·`), ceiling);
  }
  const pending = { ...base, tests: { oracle: { status: 'pending', ciNote: null, scope: null } } } as unknown as RegisteredContract;
  assert.match(evidenceBadgeView(pending)?.description ?? '', /Oracle pending/);
  assert.equal(evidenceBadgeView({ ...base, migrationState: 'legacy' } as unknown as RegisteredContract), null);
});

// Both pilots are screening-only, so rendering only the registry could not catch a ceiling or
// oracle hard-coded in the JSX. Render synthetic contracts through the same component instead.
test('the rendered badge follows every ceiling and oracle state of the contract it is given', () => {
  const base = MODULE_CONTRACTS.find(contract => contract.id === 'keyhole-raytracing') as RegisteredContract;
  const oracles = [
    { status: 'present', ciNote: null, scope: 'It checks a synthetic case only.' },
    { status: 'pending', ciNote: null, scope: null },
  ] as const;
  for (const ceiling of EVIDENCE_TYPES) {
    for (const oracle of oracles) {
      const contract = { ...base, evidence: { ceiling }, tests: { oracle } } as unknown as RegisteredContract;
      const html = renderToStaticMarkup(<ContractEvidenceBadge contract={contract} />);
      const visible = /<span class="mk-count-badge[^>]*>([^<]*)<\/span>/.exec(html)?.[1] ?? '';
      const label = `${ceiling}/${oracle.status}`;
      assert.match(html, new RegExp(`data-evidence-ceiling="${ceiling}"`), label);
      assert.match(html, new RegExp(`data-oracle="${oracle.status}"`), label);
      assert.equal(visible, `Max claim: ${LABELS[rank(ceiling)]} · Oracle ${oracle.status}`, label);
      for (const other of LABELS.filter(item => item !== LABELS[rank(ceiling)])) assert.ok(!visible.includes(other), `${label} shows ${other}`);
      // The screen-reader description (not only the tooltip) carries the contract's oracle text.
      const sr = /class="mk-sr-only">([^<]*)</.exec(html)?.[1] ?? '';
      assert.equal(/title="([^"]*)"/.exec(html)?.[1], sr, label);
      assert.equal(sr.includes('It checks a synthetic case only.'), oracle.status === 'present', label);
      assert.equal(sr.includes('stays capped'), oracle.status === 'pending', label);
    }
  }
  const withGap = { ...base, tests: { oracle: { status: 'present', ciNote: 'Synthetic CI gap.', scope: 'Checks x.' } } } as unknown as RegisteredContract;
  assert.match(renderToStaticMarkup(<ContractEvidenceBadge contract={withGap} />), /class="mk-sr-only">[^<]*Synthetic CI gap\./);
  assert.equal(renderToStaticMarkup(<ContractEvidenceBadge contract={{ ...base, migrationState: 'legacy' } as unknown as RegisteredContract} />), '');
});

test('the disclaimer is screen-reader text tied to the badge, not only a tooltip', () => {
  for (const contract of MODULE_CONTRACTS.filter(item => item.migrationState === 'contracted')) {
    const html = renderToStaticMarkup(<EvidenceBadge moduleId={contract.id} />);
    const describedBy = /aria-describedby="([^"]+)"/.exec(html)?.[1];
    assert.ok(describedBy, contract.id);
    const sr = new RegExp(`<span id="${describedBy}" class="mk-sr-only">([^<]+)</span>`).exec(html)?.[1] ?? '';
    assert.match(sr, /not the status of a result and not a validation claim/, contract.id);
    assert.match(html, /class="mk-count-badge/, contract.id);
    assert.ok(!/slate-/.test(html), 'mk-* tokens, not raw slate classes');
    assert.ok(!html.includes('python/') && !html.includes('.py'), 'no repository paths in user-facing text');
  }
  const keyhole = renderToStaticMarkup(<EvidenceBadge moduleId="keyhole-raytracing" />);
  assert.ok(keyhole.includes('It checks sampling and energy bookkeeping on a flat surface only.'));
});

test('a recorded oracle CI gap is shown with the badge', () => {
  for (const contract of MODULE_CONTRACTS.filter(item => item.migrationState === 'contracted')) {
    const view = evidenceBadgeView(contract);
    const ciNote = contract.tests.oracle.ciNote;
    if (ciNote) assert.ok(view?.description.includes(ciNote), contract.id);
  }
  const keyhole = MODULE_CONTRACTS.find(contract => contract.id === 'keyhole-raytracing');
  assert.equal(keyhole?.tests.oracle.ciNote, 'Oracle not run in CI (requires Warp/GPU stack).');
});

test('the badge reads only the committed contract (no store, service or fetch)', () => {
  const source = read('src/components/sdk/EvidenceBadge.tsx');
  const imports = [...source.matchAll(/from '([^']+)'/g)].map(match => match[1]);
  assert.deepEqual(imports, ['react', '../../modules/registry']);
  assert.ok(!/fetch\(|useStore|Service/.test(source));
});

test('App.tsx header keeps title and maturity badge, then the plain purpose sentence and the evidence disclosure', () => {
  const app = read('src/App.tsx');
  assert.match(app, /\{activeModule\.scope\}<\/span><\/div><p [^>]*>\{MODULE_PURPOSE\[activeModule\.id\]\}<\/p><ModuleEvidenceDisclosure moduleId=\{activeModule\.id\} detail=\{activeModule\.description\} \/>/);
  assert.ok(!/<EvidenceBadge /.test(app), 'the max-claim badge is no longer printed in the header');
});

test('module header: max-claim and oracle text sit behind "About this evidence level", wording unchanged', () => {
  for (const contract of MODULE_CONTRACTS.filter(item => item.migrationState === 'contracted')) {
    const view = evidenceBadgeView(contract);
    const html = renderToStaticMarkup(<ModuleEvidenceDisclosure moduleId={contract.id} />);
    assert.match(html, /^<details class="mk-about"/, contract.id);
    assert.ok(!/^<details[^>]*\bopen/.test(html), `${contract.id} starts closed`);
    assert.ok(html.includes('<summary>About this evidence level</summary>'), contract.id);
    assert.match(html, new RegExp(`data-evidence-ceiling="${contract.evidence.ceiling}"`), contract.id);
    const escape = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#x27;');
    assert.ok(html.includes(escape(view!.text)), `${contract.id} max-claim text unchanged`);
    assert.ok(html.includes(escape(view!.description)), `${contract.id} description unchanged`);
  }
  // A legacy module has no evidence level: no disclosure unless a detail is given, then a plain "About this module".
  const legacy = MODULE_CONTRACTS.find(item => item.migrationState === 'legacy');
  if (legacy) {
    assert.equal(renderToStaticMarkup(<ModuleEvidenceDisclosure moduleId={legacy.id} />), '');
    assert.match(renderToStaticMarkup(<ModuleEvidenceDisclosure moduleId={legacy.id} detail="Technical text." />), /<summary>About this module<\/summary>.*Technical text\./);
  }
});

test('every listed module has one plain purpose sentence', () => {
  assert.deepEqual(Object.keys(MODULE_PURPOSE).sort(), MODULES.map(module => module.id).sort());
  for (const [id, sentence] of Object.entries(MODULE_PURPOSE)) {
    assert.ok(sentence.length > 20 && sentence.length < 170, id);
    assert.ok(sentence.endsWith('.') && (sentence.match(/\. /g) ?? []).length <= 1, `${id}: one sentence (a second one is allowed only as a short caveat)`);
    assert.ok(!/max claim|oracle|ceiling/i.test(sentence), `${id}: no internal jargon`);
  }
});
