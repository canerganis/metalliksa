import React from 'react';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { renderToStaticMarkup } from 'react-dom/server';
import { LpbfDatasetComparisonLab, REGIME_COLORS, fmt1 } from '../src/components/3d-distortion-lab/LpbfDatasetComparisonLab';
import { checkedDatasetComparison, type LpbfDatasetComparisonDocument } from '../src/data/lpbfDatasetComparison';
import { setPath } from './support/jsonPath';

const fixtureJson = (): unknown => JSON.parse(readFileSync('tests/fixtures/lpbf-dataset-comparison.sample.json', 'utf8'));
const REAL = 'docs/LPBF_DATASET_COMPARISON_2026-10-05.json';
const doc = checkedDatasetComparison(fixtureJson());
const render = (d: LpbfDatasetComparisonDocument) => renderToStaticMarkup(<LpbfDatasetComparisonLab document={d} />);
const html = render(doc);
const NO_LITERAL_FILLS = /fill="#(?:ffffff|334155|f8fafc)"/i;

test('header carries the honesty statement verbatim and the provenance block', () => {
  assert.ok(html.includes(doc.honesty.statement));
  for (const d of doc.datasets) {
    assert.ok(html.includes(d.sha256));
    assert.ok(html.includes(d.license));
    assert.ok(html.includes(d.citation));
    assert.ok(html.includes(`href="https://doi.org/${d.doi}"`));
    assert.ok(html.includes(`Rows in dataset: ${d.rows}`));
  }
});

test('excluded rows are counted for the first kernel and drawn hollow', () => {
  const kernel = doc.kernels[0];
  const excluded = doc.rows.filter((r) => !r.predictions[kernel].included);
  assert.ok(excluded.length > 0);
  const statuses = Array.from(new Set(excluded.map((r) => r.predictions[kernel].extentStatus)));
  assert.ok(html.includes(`${excluded.length} excluded: extentStatus ${statuses.join(', ')}`));
  const hollow = (html.match(/data-point="excluded"/g) ?? []).length;
  assert.ok(hollow >= 1 && hollow <= 2 * excluded.length);
  assert.ok(html.includes('Excluded, extentStatus '));
});

test('summary tiles equal the fixture values (one decimal) and the sensitivity table is labelled', () => {
  const kernel = doc.kernels[0];
  for (const [regime, cell] of Object.entries(doc.summary[kernel])) {
    const tile = html.split(`data-summary="${kernel}/${regime}"`)[1]?.split('data-summary=')[0] ?? '';
    assert.ok(tile.length > 0, `tile ${regime}`);
    for (const stat of [cell.width, cell.depth]) {
      assert.ok(stat);
      assert.ok(tile.includes(`${fmt1(stat.bias_pct)} %`));
      assert.ok(tile.includes(`${fmt1(stat.mape_pct)} %`));
      assert.ok(tile.includes(`${fmt1(stat.rmse_um)} µm`));
      assert.ok(tile.includes(`${Math.round(stat.within30pct * 1000) / 10} %`), `within30pct rendered as percent of the fraction ${stat.within30pct}`);
      assert.ok(stat.within30pct <= 1, 'fixture stores fractions like the real record');
    }
  }
  assert.ok(html.includes('sensitivity, not calibration'));
  assert.ok(html.includes('Sensitivity, not calibration'));
  assert.ok(html.includes('13.3'));
});

test('kernel selector and regime chips are present', () => {
  assert.match(html, /aria-label="Kernel"/);
  for (const k of ['Rosenthal', 'Eagar–Tsai v2', 'Goldak v3']) assert.ok(html.includes(k));
  assert.match(html, /aria-pressed="true"[^>]*>conduction</);
  assert.match(html, /aria-pressed="true"[^>]*>transition</);
});

test('the page never claims validation', () => {
  assert.doesNotMatch(html, /\bvalidated\b/i);
  assert.doesNotMatch(html, /\bvalidation (?:confirmed|passed)\b/i);
});

test('absent record renders the honest message and no scatter', () => {
  const empty = renderToStaticMarkup(<LpbfDatasetComparisonLab document={null} />);
  assert.match(empty, /No comparison record committed yet/);
  assert.doesNotMatch(empty, /<svg[^>]*role="img"/);
  assert.doesNotMatch(empty, /\bvalidated\b/i);
});

test('dataset notes render as a list with one item per caveat; the Totis depth-reference caption follows the notes', () => {
  for (const d of doc.datasets) {
    const block = html.split(`data-testid="notes-${d.id}"`)[1]?.split('</ul>')[0] ?? '';
    assert.equal((block.match(/<li>/g) ?? []).length, d.notes.length);
  }
  assert.ok(html.includes('Totis depth reference line not stated (substrate vs powder surface); 25 µm powder layer over a printed base.'));
  const without = fixtureJson();
  setPath(without, ['datasets', 1, 'notes'], ['no relevant note']);
  assert.ok(!render(checkedDatasetComparison(without)).includes('Totis depth reference line not stated'));
});

test('limits, pooled n, powder-layer note and sensitivity sentence are shown; optional record keys are honoured', () => {
  assert.ok(html.includes('The screening kernels ignore the powder-layer thickness (identical predictions for 0/30/60 µm layers); any powder-layer trend is in the measurements only.'));
  assert.ok(html.includes('Sensitivity, not a calibration: included row counts differ per column (only rows where the kernel resolves an extent are counted), and width and depth errors pull in opposite directions.'));
  assert.ok(html.includes('Balling-flagged rows are included in the pooled headline.'));
  const pooled = doc.kernels.flatMap((k) => (doc.summary[k].all ? [doc.summary[k].all.n] : []));
  for (const n of pooled) assert.ok(html.includes(`n ${n}`));

  const custom = fixtureJson();
  setPath(custom, ['limits'], ['custom limit one']);
  setPath(custom, ['absorption'], { path: 'flat-plate absorptivity_IR', pinned: true });
  setPath(custom, ['summary', 'rosenthal', 'common'], doc.summary.rosenthal.conduction);
  setPath(custom, ['summary', 'rosenthal', 'conduction', 'width', 'mape_pct_ci95'], [10.04, 20.06]);
  const out = render(checkedDatasetComparison(custom));
  assert.ok(out.includes('custom limit one'));
  assert.ok(!out.includes('Balling-flagged rows are included in the pooled headline.'));
  assert.ok(out.includes('Absorption path: flat-plate absorptivity_IR'));
  assert.ok(out.includes('data-summary="rosenthal/common"'));
  assert.ok(out.includes('(95 % CI 10.0–20.1)'));
});

test('a null width or depth slot renders "no included rows" instead of crashing', () => {
  const raw = fixtureJson();
  setPath(raw, ['summary', 'rosenthal', 'conduction', 'width'], null);
  setPath(raw, ['summary', 'rosenthal', 'conduction', 'depth'], null);
  const out = render(checkedDatasetComparison(raw));
  const tile = out.split('data-summary="rosenthal/conduction"')[1]?.split('data-summary=')[0] ?? '';
  assert.equal((tile.match(/no included rows/g) ?? []).length, 2);
});

test('scatter SVG has no literal light fills; excluded markers are hollow and drawn after included ones', () => {
  assert.doesNotMatch(html, NO_LITERAL_FILLS);
  const groups = html.match(/<g data-point="excluded">.*?<\/g>/g) ?? [];
  assert.ok(groups.length >= 1);
  for (const g of groups) assert.match(g, /fill="none"/);
  const included = html.match(/<g data-point="included">.*?<\/g>/g) ?? [];
  for (const g of included) assert.doesNotMatch(g, /fill="none"/);
  const firstSvg = html.split('<svg')[1];
  assert.ok(firstSvg.lastIndexOf('data-point="included"') < firstSvg.indexOf('data-point="excluded"'));
  assert.ok(firstSvg.includes('fill="var(--mk-text-strong)"'));
});

test('regime colours keep >= 4.5:1 contrast against white chip text', () => {
  const lin = (c: number) => (c / 255 <= 0.03928 ? c / 255 / 12.92 : ((c / 255 + 0.055) / 1.055) ** 2.4);
  const lum = (hex: string) => {
    const n = parseInt(hex.slice(1), 16);
    return 0.2126 * lin((n >> 16) & 255) + 0.7152 * lin((n >> 8) & 255) + 0.0722 * lin(n & 255);
  };
  for (const color of REGIME_COLORS) assert.ok(1.05 / (lum(color) + 0.05) >= 4.5, color);
});

test('the real committed record renders real sensitivity numbers (no n/a) and keeps the honesty line', () => {
  const real = checkedDatasetComparison(JSON.parse(readFileSync(REAL, 'utf8')));
  const out = render(real);
  const table = out.split('data-testid="sensitivity-table"')[1]?.split('</table>')[0] ?? '';
  assert.ok(table.length > 0);
  assert.ok(!table.includes('n/a'));
  const cell = table.split('data-sensitivity="rosenthal/0.3"')[1]?.split('</td>')[0] ?? '';
  assert.ok(cell.includes('width 49.9 %'), cell);
  assert.ok(cell.includes('depth 34.6 %'), cell);
  assert.ok(cell.includes('n 15'), cell);
  const goldak = table.split('data-sensitivity="goldak/0.6"')[1]?.split('</td>')[0] ?? '';
  assert.ok(goldak.includes('width 17.4 %') && goldak.includes('n 139'), goldak);
  assert.ok(out.includes(real.honesty.statement));
  assert.ok(out.includes('SENSITIVITY, not a calibrated value'));
  assert.doesNotMatch(out, /\bvalidated\b/i);
  assert.equal(real.honesty.experimentalValidation, false);
  assert.doesNotMatch(out, NO_LITERAL_FILLS);
  assert.ok(out.includes('Totis depth reference line not stated'));
  assert.ok(out.includes('n 757'));
  assert.ok(out.includes('independent of the chip filter'));
  assert.ok(out.includes('Rosenthal n 519, Eagar–Tsai v2 n 757, Goldak v3 n 743'));
});

test('App skips the shared-material block and the context panel for this module (source guard)', () => {
  const app = readFileSync('src/App.tsx', 'utf8');
  assert.match(app, /MODULES_WITHOUT_SHARED_SPECIMEN[^=]*=\s*new Set\(\['lpbf-dataset-comparison', 'lpbf-calibration-scorecard'\]\)/);
  assert.match(app, /!MODULES_WITHOUT_SHARED_SPECIMEN\.has\(activeTab\) && <details/);
  assert.match(app, /!MODULES_WITHOUT_SHARED_SPECIMEN\.has\(activeTab\) && !CONTEXT_AFTER_MODULE\.has\(activeTab\) && <SilentBoundary><Suspense fallback=\{null\}><ScientificContextPanel/);
});
