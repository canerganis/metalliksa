import React from 'react';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import test from 'node:test';
import { renderToStaticMarkup } from 'react-dom/server';
import { LpbfDatasetComparisonLab } from '../src/components/3d-distortion-lab/LpbfDatasetComparisonLab';
import { SetCard, SpentChart, SpentSetDescriptivePanel } from '../src/components/3d-distortion-lab/SpentSetDescriptivePanel';
import { checkedSpentDescriptive, isForbiddenSpentId, type LpbfSpentDescriptiveDocument } from '../src/data/lpbfSpentDescriptive';
import { setPath } from './support/jsonPath';

// The fixture is titled "Synthetic fixture, not measured data". Its numbers are invented.
const fixtureJson = (): unknown => JSON.parse(readFileSync('tests/fixtures/lpbf-spent-descriptive.SYNTHETIC.json', 'utf8'));
const doc = checkedSpentDescriptive(fixtureJson());
const render = (d: LpbfSpentDescriptiveDocument | null) => renderToStaticMarkup(<SpentSetDescriptivePanel document={d} />);
const html = render(doc);
const BANNED = /\b(validated|accuracy|rank|score|pass|fail)\b/i;

test('the fixture is labelled synthetic and passes the validator', () => {
  assert.equal((fixtureJson() as { title: string }).title, 'Synthetic fixture, not measured data');
  assert.equal(doc.sets.length, 2);
});

test('validator negatives', () => {
  const bad = (mutate: (raw: unknown) => void) => {
    const raw = fixtureJson();
    mutate(raw);
    assert.throws(() => checkedSpentDescriptive(raw));
  };
  bad((r) => setPath(r, ['schema'], 'lpbf-comparison-1'));
  bad((r) => setPath(r, ['honesty', 'experimentalValidation'], true));
  bad((r) => setPath(r, ['honesty', 'labelPromotionProposed'], 'tier-1'));
  bad((r) => setPath(r, ['honesty', 'evidenceKind'], 'measured'));
  bad((r) => setPath(r, ['honesty', 'spentOnly'], false));
  bad((r) => setPath(r, ['research', 'requested'], true));
  bad((r) => setPath(r, ['sets', 0, 'spent', 'status'], 'EXPOSED'));
  bad((r) => setPath(r, ['sets', 0, 'id'], 'leis2021'));
  bad((r) => setPath(r, ['sets', 1, 'id'], 'bitharas'));
  bad((r) => setPath(r, ['sets', 0, 'measuredSource', 'label'], 'Validated'));
  bad((r) => setPath(r, ['sets', 0, 'servedSource', 'label'], 'Measured'));
  bad((r) => setPath(r, ['sets', 0, 'notes', 0, 'sentence'], 'This is the cause.'));
  for (const key of ['rank', 'score', 'pass', 'fail']) bad((r) => setPath(r, ['sets', 0, 'deviation', 0, key], 1));
  assert.throws(() => checkedSpentDescriptive(null));
  assert.ok(isForbiddenSpentId('wimmer2020') && isForbiddenSpentId('ku-leuven-in718') && !isForbiddenSpentId('ku-leuven-316l-2021'));
});

test('empty state renders without a chart', () => {
  const empty = render(null);
  assert.match(empty, /No spent-set descriptive record is committed yet/);
  assert.match(empty, /Spent sets, descriptive/);
  assert.doesNotMatch(empty, /<svg[^>]*role="img"/);
  assert.doesNotMatch(empty, BANNED);
});

test('heading, badge, statement and the reading disclosure', () => {
  assert.match(html, /<h2[^>]*>Spent sets, descriptive<\/h2>/);
  assert.match(html, /data-testid="spent-badge"[^>]*>Not validation: data already seen</);
  assert.ok(html.includes(doc.honesty.statement));
  assert.match(html, /<summary[^>]*>How to read this<\/summary>/);
});

test('model map, radiogroup with roving tab stop, and the provenance card', () => {
  assert.match(html, /role="radiogroup"/);
  const radios = html.match(/role="radio"/g) ?? [];
  assert.equal(radios.length, doc.sets.length);
  assert.equal((html.match(/role="radio"[^>]*tabindex="0"|tabindex="0"[^>]*role="radio"/g) ?? []).length, 1);
  assert.equal((html.match(/tabindex="-1"/g) ?? []).length, doc.sets.length - 1);
  for (const row of doc.modelMap) for (const b of row.bins) assert.ok(html.includes(`data-map-row="${row.key}/${b.id}"`));
  assert.ok(html.includes('href="https://doi.org/10.0000/synthetic"'));
  assert.ok(html.includes(doc.sets[0].provenance.tableSha256));
  assert.ok(html.includes('Status: SPENT'));
  assert.ok(html.includes('Spent by: Synthetic spending event'));
  assert.ok(html.includes('Beam reading: 80 µm, stated'));
});

test('deviation chips per bin read model deeper or shallower by about x percent with n', () => {
  assert.ok(html.includes('model deeper by about 8 % (n 1)'));
  assert.ok(html.includes('model shallower by about 3 % (n 2)'));
  assert.ok(html.includes('no rows'));
  assert.ok(html.includes('no served depth: 1'));
  assert.ok(!html.includes('NaN'));
});

test('research columns read unavailable with the reason code, and the data table is a details fallback', () => {
  assert.ok(html.includes('unavailable: RESEARCH_NOT_REQUESTED'));
  const table = html.split('data-testid="data-table-fallback"')[1] ?? '';
  assert.match(table, /<summary[^>]*>Data table<\/summary>/);
  assert.equal((table.match(/data-row="/g) ?? []).length, doc.sets[0].groups[0].points.length);
  assert.ok(table.includes('Depth, Measured'));
  assert.ok(table.includes('Depth, served, Unresolved'));
  assert.ok(table.includes('data-source-label="Unresolved"'));
  assert.ok(table.includes('data-source-label="Measured"'));
  assert.ok(html.includes('Unresolved: the served result does not yet list the source of each value.'));
});

test('the used-in-development note and its source show on the first card', () => {
  assert.ok(html.includes('data-note="USED_IN_SERVED_DEVELOPMENT"'));
  assert.ok(html.includes('Candidate explanation, not tested: synthetic sentence one.'));
  assert.ok(html.includes('Source: data/benchmark/spent-ledger-v1.json, entries[].usedInServedDevelopment'));
});

test('a set without notes says there is no catalogued explanation; the sensitivity group is selectable', () => {
  const card = renderToStaticMarkup(<SetCard doc={doc} set={doc.sets[1]} setIndex={1} />);
  assert.ok(card.includes('No catalogued explanation'));
  assert.ok(card.includes('beam sensitivity reading 75 µm'));
  assert.ok(card.includes('Sensitivity reading: 75 µm'));
  assert.ok(card.includes('Beam sensitivity reading 75 µm'));
});

test('numbers carry data-source with their record field path', () => {
  assert.ok(html.includes('data-source="sets[0].groups[0].points[0].measured_um"'));
  assert.ok(html.includes('data-source="sets[0].groups[0].points[0].served_um"'));
  assert.ok(html.includes('data-source="sets[0].deviation[0].bins[0].median_pct"'));
  assert.ok(html.includes('data-source="modelMap[0].bins[0].n"'));
  assert.ok(html.includes('data-source="sets[0].provenance.rows"'));
  const tds = html.split('data-testid="data-table-fallback"')[1] ?? '';
  for (const cell of tds.match(/<td[^>]*>[^<]*\d[^<]*<\/td>/g) ?? []) assert.match(cell, /data-source=|<td class="pr-3">synthetic|<td class="pr-3">primary/, cell);
});

test('chart: no guide lines like 1:1 or percent bands; index view draws the cut lines; legend is text', () => {
  const set = doc.sets[0];
  const proc = renderToStaticMarkup(<SpentChart set={set} setIndex={0} group={set.groups[0]} groupIndex={0} xMode="process" />);
  const idx = renderToStaticMarkup(<SpentChart set={set} setIndex={0} group={set.groups[0]} groupIndex={0} xMode="index" />);
  assert.doesNotMatch(proc, /one-to-one|band-upper|data-cut/);
  assert.ok(idx.includes('data-cut="15"') && idx.includes('data-cut="20"'));
  assert.ok(idx.includes('served index (unrounded), log scale'));
  assert.ok(proc.includes('scan speed (mm/s), log scale'));
  assert.ok(proc.includes('data-line="served"'));
  assert.equal((proc.match(/data-point="measured"/g) ?? []).length, set.groups[0].points.length);
  assert.ok(html.includes('data-testid="chart-legend"'));
  assert.ok(html.includes('Solid line: served model depth, Unresolved source.'));
  const fills = proc.match(/fill="(#[0-9a-f]{3,8})"/gi) ?? [];
  assert.deepEqual(fills, []);
});

test('no validated, accuracy, rank, score, pass or fail words and no dashes as punctuation in the page', () => {
  assert.doesNotMatch(html, BANNED);
  const text = html.replace(/<[^>]*>/g, ' ');
  assert.doesNotMatch(text, /[–—]| - /);
  assert.doesNotMatch(text, /\b(?:pass|fail)(?:ed|es)?\b/i);
});

test('the link to the blind test uses the research store and the navigate event', () => {
  assert.ok(html.includes('Test the model on your own tracks'));
  const src = readFileSync('src/components/3d-distortion-lab/SpentSetDescriptivePanel.tsx', 'utf8');
  assert.match(src, /useResearchStore\.getState\(\)/);
  assert.match(src, /setActiveTab\("blind-test"/);
  assert.match(src, /metallix-navigate-tab/);
});

test('the committed record, if any, is valid, SPENT only, and counts agree (no values asserted)', () => {
  const files = readdirSync('docs').filter((f) => /^LPBF_SPENT_DESCRIPTIVE_.*\.view\.json$/.test(f)).sort();
  if (files.length === 0) return;
  const real = checkedSpentDescriptive(JSON.parse(readFileSync(`docs/${files[files.length - 1]}`, 'utf8')));
  assert.ok(real.sets.length >= 5);
  for (const s of real.sets) {
    assert.equal(s.spent.status, 'SPENT');
    assert.ok(!isForbiddenSpentId(s.id));
    const primary = s.groups.filter((g) => g.beamRole === 'primary').reduce((n, g) => n + g.points.length, 0);
    assert.equal(primary, s.provenance.rows);
    for (const g of s.groups) if (g.curve) assert.equal(g.curve.length, 25);
  }
  const nist = real.sets.find((s) => s.id === 'nist-amb2022-03-optical');
  assert.ok(nist?.notes.some((n) => n.code === 'USED_IN_SERVED_DEVELOPMENT'));
  const out = render(real);
  assert.ok(out.includes('data-note="USED_IN_SERVED_DEVELOPMENT"'));
  assert.ok(out.includes('unavailable: RESEARCH_NOT_REQUESTED'));
  assert.doesNotMatch(out, BANNED);
  assert.ok(Buffer.byteLength(readFileSync(`docs/${files[files.length - 1]}`)) < 150 * 1024);
});

test('the comparison lab renders the static fallback for the lazy panel without throwing', () => {
  for (const document of [null, undefined]) {
    const out = renderToStaticMarkup(<LpbfDatasetComparisonLab document={document} />);
    assert.ok(out.includes('data-testid="spent-descriptive-fallback"'));
    assert.ok(out.includes('Spent sets, descriptive: loading.'));
  }
});
