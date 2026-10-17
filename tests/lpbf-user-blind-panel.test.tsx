import React from 'react';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { renderToStaticMarkup } from 'react-dom/server';
import wording from '../data/blind/lpbf-user-blind-wording-v1.json';
import protocol from '../data/blind/lpbf-user-blind-protocol-v1.json';
import { AdvancedResearchHub } from '../src/components/AdvancedResearchHub';
import { ExperimentPlanView } from '../src/components/LpbfExperimentPlanPanel';
import { BlindTestCallToAction, BlindTestPointer } from '../src/components/research/BlindTestLink';
import { BlindTestMetadataForm } from '../src/components/research/BlindTestMetadataForm';
import { BlindTestInputsStep, BlindTestPreviewReview } from '../src/components/research/BlindTestInputsStep';
import { BlindTestList, BlindTestListView } from '../src/components/research/BlindTestList';
import BlindTestPanel, { BlindSharedHostWarning, BLIND_STEPS } from '../src/components/research/BlindTestPanel';
import { BlindTestReceiptView } from '../src/components/research/BlindTestReceiptView';
import { BlindTestReportView, ObservedServedSvg } from '../src/components/research/BlindTestReportView';
import { BlindRevealDialog, BlindTestTargetsStep } from '../src/components/research/BlindTestTargetsStep';
import { BLIND_FIELD_HELP, PREDICTION_SURFACES } from '../src/components/research/blindTestHelp';
import { LPBF_EXPERIMENT_PLAN_LABEL, checkedExperimentPlan } from '../src/data/lpbfExperimentPlan';
import { BLIND_DRAFT_DEFAULTS, checkedBlindGet, checkedBlindList, checkedBlindPreview, checkedBlindReceipt, checkedBlindReport } from '../src/data/lpbfUserBlind';
import { HASHING_NEEDS_SECURE_NOTE } from '../src/services/lpbfUserBlindClient';
import { useResearchStore } from '../src/store/useResearchStore';
import { PLAN_BLIND_NOTICE } from '../src/components/LpbfExperimentPlanPanel';

const fixture = (name: string): Record<string, unknown> => {
  const raw = JSON.parse(readFileSync(new URL(`./fixtures/lpbf-user-blind-${name}.SYNTHETIC.json`, import.meta.url), 'utf8')) as { _title: string; document: Record<string, unknown> };
  assert.equal(raw._title, 'Synthetic fixture, not measured data');
  return raw.document;
};
const clone = <T,>(v: T): T => JSON.parse(JSON.stringify(v)) as T;
const decode = (s: string) => s.replace(/&#x27;/g, "'").replace(/&quot;/g, '"').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');
const html = (node: React.ReactElement) => decode(renderToStaticMarkup(node));
const W = wording.wording;
const KEY = String(fixture('receipt').freezeKey);

const preview = checkedBlindPreview(fixture('preview'));
const receipt = checkedBlindReceipt(fixture('receipt'));
const report = checkedBlindReport(fixture('report'));

const ALL: string[] = [];
const keep = (markup: string) => { ALL.push(markup); return markup; };

function assertAllControlsLabelled(markup: string, what: string) {
  const controls = [...markup.matchAll(/<(input|select|textarea)\b([^>]*)>/g)];
  for (const [, tag, attrs] of controls) {
    const id = /\bid="([^"]+)"/.exec(attrs)?.[1];
    assert.ok(id, `${what}: a ${tag} has no id (${attrs})`);
    assert.ok(markup.includes(`for="${id}"`), `${what}: no label for ${tag} ${id}`);
  }
  return controls.length;
}

test('the stepper lists the five steps in order with one current step', () => {
  for (let step = 1; step <= 5; step += 1) {
    const markup = keep(html(<BlindTestPanel demo={false} hostname="localhost" initialStep={step} />));
    assert.equal((markup.match(/aria-current="step"/g) ?? []).length, 1, `step ${step}`);
    assert.match(markup, /<ol[^>]*>/);
    BLIND_STEPS.forEach((label, i) => assert.ok(markup.includes(`${i + 1}. ${label}`)));
    assert.ok(markup.includes(`aria-current="step">${step}. ${BLIND_STEPS[step - 1]}`));
    assert.ok(markup.includes('Your tests'));
  }
  assert.deepEqual([...BLIND_STEPS], ['Describe', 'Inputs and check', 'Freeze', 'Measure and score', 'Report']);
});

test('the panel carries the banner, the Screening only badge and no research opt-in', () => {
  const markups = [1, 2, 3, 4, 5].map(step => html(<BlindTestPanel demo={false} hostname="localhost" initialStep={step} />));
  for (const m of markups) {
    keep(m);
    assert.ok(m.includes(W.banner));
    assert.ok(m.includes('Screening only'));
    assert.doesNotMatch(m, /research (arm )?opt|include research|request research|enable research/i);
  }
  const forms = html(<BlindTestMetadataForm draft={{ ...BLIND_DRAFT_DEFAULTS, mode: 'post-measurement' }} onChange={() => undefined} subtleAvailable />) + html(<BlindTestPreviewReview preview={preview} acks={{}} onAck={() => undefined} onFreeze={() => undefined} />);
  assert.doesNotMatch(forms, /<label[^>]*>[^<]*research[^<]*<\/label>/i);
  assert.doesNotMatch(forms, /<option[^>]*>[^<]*research[^<]*<\/option>/i);
});

test('the static demo renders DemoUnavailable (tested through the demo prop; IS_STATIC_DEMO is a compile-time flag)', () => {
  const markup = keep(html(<BlindTestPanel demo />));
  assert.match(markup, /data-testid="demo-unavailable"/);
  assert.ok(!markup.includes('Describe'));
});

test('the shared host warning appears for a shared host or a non-local hostname', () => {
  const sentence = 'Every signed-in user of this server can list and open every blind test on it, including your measurements and the frozen predictions.';
  assert.ok(html(<BlindSharedHostWarning sharedHost hostname="localhost" />).includes(sentence));
  assert.ok(html(<BlindSharedHostWarning sharedHost={false} hostname="lab.example.org" />).includes(sentence));
  assert.ok(html(<BlindSharedHostWarning sharedHost={false} hostname="192.168.1.20" />).includes(sentence));
  for (const host of ['localhost', '127.0.0.1', '[::1]']) assert.equal(html(<BlindSharedHostWarning sharedHost={false} hostname={host} />), '', host);
  assert.ok(html(<BlindTestPanel demo={false} hostname="lab.example.org" />).includes(sentence));
  assert.ok(!html(<BlindTestPanel demo={false} hostname="localhost" />).includes(sentence));
});

test('the description form: defaults are conservative, every field is labelled and has a help disclosure', () => {
  assert.equal(BLIND_DRAFT_DEFAULTS.depthDatum, 'unresolved');
  assert.equal(BLIND_DRAFT_DEFAULTS.atmosphere, 'unstated');
  assert.equal(BLIND_DRAFT_DEFAULTS.crossSectionLocation, 'unstated');
  assert.equal(BLIND_DRAFT_DEFAULTS.beamDefinition, 'unstated');
  assert.equal(BLIND_DRAFT_DEFAULTS.beamProfile, 'unknown');
  assert.equal(BLIND_DRAFT_DEFAULTS.dataPreviouslyPublished, 'unknown');
  assert.equal(BLIND_DRAFT_DEFAULTS.csvDialect, 'comma-dot');
  assert.equal(BLIND_DRAFT_DEFAULTS.depthUncertaintyBasis, 'not-released');
  for (const required of ['mode', 'alloy', 'reduction', 'beamQuantity', 'substrateKind', 'predictionsViewedBeforeFreeze', 'usedForMachineCalibration', 'wavelength_nm', 'preheat_C'] as const) {
    assert.equal(BLIND_DRAFT_DEFAULTS[required], '', `${required} has no default`);
  }
  const full = { ...BLIND_DRAFT_DEFAULTS, mode: 'post-measurement', alloy: 'AlSi10Mg', substrateKind: 'powder-layer' };
  const markup = keep(html(<BlindTestMetadataForm draft={full} onChange={() => undefined} subtleAvailable />));
  const controls = assertAllControlsLabelled(markup, 'metadata form');
  assert.ok(controls >= 40, `${controls} controls`);
  for (const [field, h] of Object.entries(BLIND_FIELD_HELP)) {
    if (field === 'targetCommitmentSha256') assert.ok(markup.includes(h.help)); else assert.ok(markup.includes(`Help: ${h.label}`), field);
  }
  assert.ok(markup.includes(BLIND_FIELD_HELP.predictionsViewedBeforeFreeze.help));
  for (const surface of PREDICTION_SURFACES) assert.ok(markup.includes(surface), surface);
  assert.ok(markup.includes(W.doNotResave));
  assert.match(markup, /type="file"/);
  assert.match(markup, /Still to fill in:/);
});

test('post-measurement mode without SubtleCrypto offers a paste field and the instruction, not a file picker', () => {
  const markup = keep(html(<BlindTestMetadataForm draft={{ ...BLIND_DRAFT_DEFAULTS, mode: 'post-measurement' }} onChange={() => undefined} subtleAvailable={false} />));
  assert.ok(markup.includes(HASHING_NEEDS_SECURE_NOTE));
  assert.equal(HASHING_NEEDS_SECURE_NOTE, 'Hashing needs https or localhost. Compute the SHA-256 of the targets file with sha256sum or certutil -hashfile <file> SHA256 and paste it.');
  assert.doesNotMatch(markup, /type="file"/);
  assert.ok(markup.includes('Targets file SHA-256'));
  assert.ok(markup.includes(W.doNotResave));
  const pre = keep(html(<BlindTestMetadataForm draft={{ ...BLIND_DRAFT_DEFAULTS, mode: 'pre-measurement' }} onChange={() => undefined} subtleAvailable />));
  assert.ok(!pre.includes('Commitment to the targets file'));
});

test('the inputs step renders and every control is labelled', () => {
  const markup = keep(html(<BlindTestInputsStep draft={BLIND_DRAFT_DEFAULTS} onFreeze={() => undefined} />));
  assert.ok(assertAllControlsLabelled(markup, 'inputs step') >= 1);
  assert.match(markup, /Inputs file \(CSV, at most 256 KiB\)/);
  assert.match(markup, /Fill in the description first/);
});

test('the parsed inputs screen and the review show what the preview returned', () => {
  const markup = keep(html(<BlindTestPreviewReview preview={preview} acks={{}} onAck={() => undefined} onFreeze={() => undefined} />));
  assert.ok(markup.includes('Parsed inputs'));
  const table = markup.split('data-testid="blind-parsed-table"')[1].split('</table>')[0];
  assert.equal((table.match(/<tr/g) ?? []).length, 1 + preview.parsedInputs.length);
  for (const head of ['Condition', 'Power (W)', 'Speed (mm/s)', 'Beam as given (um)', 'Beam quantity', 'Beam definition', 'Beam 1/e2 (um)', 'Tracks']) assert.ok(table.includes(head), head);
  assert.ok(markup.includes('Unit read') && markup.includes('Conversion factor'));
  assert.ok(markup.includes('Best reachable outcome: inconclusive (leverage counts below 4 on either side of the served index cuts)'));
  assert.ok(markup.includes(preview.research.text));
  assert.equal(preview.research.text, W.researchReview);
  assert.ok(markup.includes('A freeze can hold the simulation queue for up to about a minute.'));
  assert.match(markup, /12 of at most 48 conditions, 60 solver calls/);
  assert.ok(markup.includes('S and O flagged missing'));
  assert.match(markup, /I understand this design can at best end inconclusive/);
  assert.match(markup, /type="checkbox"/);
  assert.match(markup, /<button[^>]*disabled=""[^>]*>Freeze predictions<\/button>/);
  const ticked = html(<BlindTestPreviewReview preview={preview} acks={{ predeterminedInconclusive: true }} onAck={() => undefined} onFreeze={() => undefined} />);
  assert.doesNotMatch(ticked, /<button[^>]*disabled=""[^>]*>Freeze predictions<\/button>/);
  assert.equal(assertAllControlsLabelled(markup, 'review'), 1);
  for (const d of protocol.divergences.filter(x => preview.divergences.includes(x.id))) assert.ok(markup.includes(d.rule), d.id);
});

test('block issues show their text and fix, and overlap counts are listed', () => {
  const doc = clone(fixture('preview'));
  doc.blockIssues = [{ code: 'ATMOSPHERE_UNSTATED', text: 'atmosphere not stated', fix: W.blockIssueFix.ATMOSPHERE_UNSTATED }];
  (doc.overlap as Record<string, unknown[]>).earlierTests = [{ freezeKey: KEY, kind: 'revealed', nConditions: 3 }];
  (doc.overlap as Record<string, unknown[]>).calibrationStores = [{ storeId: 'store-1', kind: 'machine-calibration', nConditions: 2 }];
  doc.acknowledgementsRequired = ['predeterminedInconclusive', 'calibrationOverlap'];
  const markup = keep(html(<BlindTestPreviewReview preview={checkedBlindPreview(doc)} acks={{}} onAck={() => undefined} onFreeze={() => undefined} freezeError="Refused text (PREVIEW_DRIFT)" />));
  assert.ok(markup.includes('atmosphere not stated'));
  assert.ok(markup.includes(W.blockIssueFix.ATMOSPHERE_UNSTATED));
  assert.ok(markup.includes('3 conditions match an earlier test that was revealed.'));
  assert.ok(markup.includes('2 conditions match calibration store store-1.'));
  assert.ok(markup.includes('I understand some conditions match calibration data on this computer.'));
  assert.ok(markup.includes('Refused text (PREVIEW_DRIFT)'));
});

test('the receipt shows no depth number, the receipt line and the anchor advice', () => {
  const markup = keep(html(<BlindTestReceiptView receipt={receipt} onContinue={() => undefined} />));
  assert.ok(markup.includes(receipt.receiptLine));
  assert.ok(markup.includes(receipt.anchorAdvice));
  assert.equal(receipt.receiptLine, W.receiptLine);
  assert.ok(markup.includes('Download receipt JSON'));
  assert.ok(markup.includes(receipt.freezeSha256));
  // The only lengths on a receipt are inputs named in a label (the layer argument), never a depth.
  const lengths = (markup.match(/[^<>]*\d(\.\d+)?\s*(um|µm)\b[^<>]*/g) ?? []).filter(t => !/layer argument/.test(t));
  assert.deepEqual(lengths, []);
  assert.doesNotMatch(markup, /value_um|depth_um|D_pred/);
});

test('the targets step: header check area, declaration, commitment mismatch option and the reveal dialog', () => {
  const base = keep(html(<BlindTestTargetsStep freezeKey={KEY} defaultDialect="comma-dot" onScore={() => undefined} onReveal={() => undefined} />));
  assert.ok(assertAllControlsLabelled(base, 'targets step') >= 3);
  assert.ok(base.includes(W.doNotResave));
  assert.match(base, /Did you view the frozen predictions before you finalised the targets\?/);
  assert.doesNotMatch(base, /Continue anyway/);
  assert.match(base, /Reveal predictions/);
  assert.doesNotMatch(base, /role="dialog"/);
  const refused = keep(html(<BlindTestTargetsStep freezeKey={KEY} defaultDialect="comma-dot" scoreRefusal={{ code: 'COMMITMENT_MISMATCH', message: 'This targets file does not match the hash you committed before the freeze.' }} onScore={() => undefined} onReveal={() => undefined} />));
  assert.match(refused, /Continue anyway/);
  assert.ok(refused.includes('This targets file does not match the hash you committed before the freeze. (COMMITMENT_MISMATCH)'));
  const other = html(<BlindTestTargetsStep freezeKey={KEY} defaultDialect="comma-dot" scoreRefusal={{ code: 'TARGETS_KEYS_MISMATCH', message: 'Keys differ.' }} onScore={() => undefined} onReveal={() => undefined} />);
  assert.doesNotMatch(other, /Continue anyway/);
  const empty = html(<BlindTestTargetsStep freezeKey={null} defaultDialect="comma-dot" onScore={() => undefined} onReveal={() => undefined} />);
  assert.match(empty, /Freeze predictions first/);
  const dialog = keep(html(<BlindRevealDialog onCancel={() => undefined} onConfirm={() => undefined} />));
  assert.match(dialog, /role="dialog"/);
  assert.match(dialog, /aria-modal="true"/);
  assert.ok(dialog.includes('reveal predictions and end blind status'));
  assert.match(dialog, /<button[^>]*disabled=""[^>]*>Reveal predictions<\/button>/);
  assert.equal(assertAllControlsLabelled(dialog, 'reveal dialog'), 1);
});

test('the report view shows the served sentence, the unavailable research arms and the labels', () => {
  const markup = keep(html(<BlindTestReportView report={report} reportSha256={'f'.repeat(64)} hashCheck="matched" onExportCsv={() => undefined} onExportBundle={() => undefined} />));
  assert.ok(markup.includes(report.banner));
  assert.ok(markup.includes('Screening only'));
  assert.ok(markup.includes(report.title));
  assert.ok(markup.includes(report.blindness.sentence));
  assert.ok(markup.includes(report.arms.served.sentence));
  const researchSentence = 'Research arm not available: not requested: the P8 research route accepts requests only from the Research model panel today.';
  assert.equal(report.arms['research:melt-link'].sentence, researchSentence);
  assert.equal((markup.match(new RegExp(researchSentence.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g')) ?? []).length, 2);
  assert.ok(markup.includes('Measured (user-supplied)'));
  assert.ok(markup.includes('Trust tier: Declared'));
  assert.ok(markup.includes('Unresolved'));
  assert.ok(markup.includes('Unresolved: the served result does not yet list the source of each value.'));
  assert.ok(markup.includes('input sensitivity range'));
  assert.ok(markup.includes(W.relNote));
  for (const label of report.labels) assert.ok(markup.includes(label), label);
  assert.ok(markup.includes('Browser hash check: the downloaded report matches its declared SHA-256.'));
  assert.ok(markup.includes('Download comparison CSV') && markup.includes('Download bundle') && markup.includes('Print this report'));
  const sk = html(<BlindTestReportView report={report} hashCheck="skipped" />);
  assert.ok(sk.includes('Browser hash check unavailable on this connection; the worker checked the hash.'));
});

test('the report view lists every declared divergence and marks the applied ones', () => {
  const markup = html(<BlindTestReportView report={report} />);
  const list = markup.split('data-testid="blind-divergences"')[1].split('</ul>')[0];
  assert.equal((list.match(/<li/g) ?? []).length, report.divergences.length);
  assert.equal(report.divergences.length, protocol.divergences.length);
  const applied = report.divergences.filter(d => d.applied).length;
  assert.equal((list.match(/applies to this test/g) ?? []).length, applied);
  assert.equal((list.match(/declared, does not apply here/g) ?? []).length, report.divergences.length - applied);
  for (const d of report.divergences) assert.ok(list.includes(d.rule), d.id);
});

test('the per condition table labels user values and served values and shows a signed percent', () => {
  const markup = html(<BlindTestReportView report={report} />);
  const table = markup.split('data-testid="blind-ledger"')[1].split('</table>')[0];
  assert.equal((table.match(/<tr/g) ?? []).length, 1 + report.ledger.length);
  assert.equal((table.match(/Measured \(user-supplied\)/g) ?? []).length, 1 + report.ledger.length);
  assert.equal((table.match(/Trust tier: Declared/g) ?? []).length, 1 + report.ledger.length);
  assert.ok((table.match(/Unresolved/g) ?? []).length >= 1 + report.ledger.length);
  assert.ok(table.includes('Unresolved: the served result does not yet list the source of each value.'));
  assert.ok(table.includes('+54.3 %'));
  assert.ok(table.includes('59.8 to 72.9'));
  for (const h of ['Condition', 'Power (W)', 'Speed (mm/s)', 'Beam (um)', 'Observed depth (um)', 'Served depth (um)', 'Signed relative difference', 'Input sensitivity range (um)']) assert.ok(table.includes(h), h);
});

test('the scatter has axes and points but no 1:1 line, band or percentage guide, and a text table fallback', () => {
  const svg = html(<ObservedServedSvg rows={report.ledger} />);
  assert.match(svg, /data-testid="blind-scatter"/);
  assert.equal((svg.match(/<circle/g) ?? []).length, report.ledger.length);
  assert.doesNotMatch(svg, /stroke-dasharray|<path|<polygon|<rect|1:1|%|identity|parity/i);
  // Only axis lines, tick marks and the sensitivity ranges are drawn.
  const markup = html(<BlindTestReportView report={report} />);
  assert.match(markup, /<details[^>]*>\s*<summary[^>]*>Table of the plotted values/);
  assert.match(html(<ObservedServedSvg rows={[]} />), /No condition has both/);
});

test('the report view excluded rows, qualifiers and statistics come from the document', () => {
  const doc = clone(fixture('report'));
  (doc.excluded as Record<string, unknown>).targets = [{ row: 7, condition: 'c3', track: 'c3-t1', section: null, status: 'specimen-lost' }];
  doc.exclusions = { sections: '1 of 36 frozen', tracks: '0 of 36 frozen', conditions: '0 of 12 frozen' };
  doc.blockIssues = ['ATMOSPHERE_UNSTATED'];
  const r = checkedBlindReport(doc);
  const markup = html(<BlindTestReportView report={r} />);
  assert.ok(markup.includes('c3, c3-t1: specimen-lost'));
  assert.ok(markup.includes('1 of 36 frozen sections'));
  assert.ok(markup.includes(W.blockIssueFix.ATMOSPHERE_UNSTATED));
  assert.match(markup, /Resolution qualifier: not_met \(median U_c 0\.1629 above 0\.1\)/);
  assert.match(markup, /Leverage: 1 conditions below and 10 at or above/);
  const stats = markup.split('data-testid="blind-served-stats"')[1].split('</table>')[0];
  assert.ok(stats.includes('0.614') && stats.includes('1.486'));
  assert.ok(stats.includes('limit not met'));
  assert.ok(stats.includes('0.20'));
  for (const id of ['Power 5 % lower', 'Power 5 % higher', 'Beam 5 % smaller', 'Beam 5 % larger']) assert.ok(markup.includes(id), id);
});

test('the list view shows tests and works from the worker list alone', () => {
  const list = checkedBlindList(fixture('list'));
  const markup = keep(html(<BlindTestListView list={list} error={null} onLoad={() => undefined} onRefresh={() => undefined} />));
  assert.ok(markup.includes('Your tests'));
  assert.ok(markup.includes('Synthetic fixture block'));
  assert.ok(markup.includes('threshold-not-met') && markup.includes('blind-prospective-declared'));
  assert.match(markup, />Open Synthetic fixture block</);
  assert.match(html(<BlindTestListView list={{ ...list, entries: [], total: 0 }} error={null} onLoad={() => undefined} onRefresh={() => undefined} />), /No blind test is stored/);
  assert.match(html(<BlindTestListView list={null} error="The simulation worker is not available." onLoad={() => undefined} onRefresh={() => undefined} />), /not available/);
  // The stateful list renders its loading state before the effect runs; it needs no persisted data.
  assert.match(html(<BlindTestList onLoad={() => undefined} />), /Loading the list/);
  assert.equal(checkedBlindGet(fixture('get')).freezeKey, KEY);
});

test('the hub lists the blind test tab, hides the brief selector there and the call to action opens it', () => {
  // zustand renders the initial state object on the server, so the test sets the tab on that object and restores it.
  const initial = useResearchStore.getInitialState() as { activeTab: string };
  const original = initial.activeTab;
  try {
    initial.activeTab = 'brief';
    const hub = html(<AdvancedResearchHub />);
    assert.match(hub, />Your blind test<\/button>/);
    assert.ok(hub.includes('Active research brief'));
    initial.activeTab = 'blind-test';
    const blind = html(<AdvancedResearchHub />);
    assert.ok(!blind.includes('Active research brief'));
    assert.match(blind, /aria-current="step">Your blind test<\/button>/);
  } finally { initial.activeTab = original; }
  assert.ok(html(<BlindTestCallToAction />).includes('Test the model on your own tracks'));
  const pointer = html(<BlindTestPointer />);
  assert.doesNotMatch(pointer, /sha256|citation/i);
  const labShell = readFileSync(new URL('../src/components/MeltPoolMeasuredTrackPanel.tsx', import.meta.url), 'utf8');
  assert.match(labShell, /BlindTestCallToAction/);
});

test('the plan panel offers the blind-test templates with the notice verbatim', () => {
  const sha = 'a'.repeat(64);
  const plan = checkedExperimentPlan({
    schema: 'lpbf-next-experiment-plan-1', label: LPBF_EXPERIMENT_PLAN_LABEL, evidenceKind: 'screening-only', material: '316L Stainless Steel', configSha256: sha,
    calibration: { available: false, reason: 'none' }, intervalWidth: { lnHiOverLo: null, note: 'none' },
    plate: { x_mm: 100, y_mm: 60, pitch_mm: 3, trackLength_mm: 10, edgeMargin_mm: 3 },
    points: [{ trackId: 'T01', rank: 1, power_W: 100, speed_mm_s: 400, beamDiameter_um: 90, layer_um: 40, preheat_C: 80, regimeClass: 'conduction',
      score: { total: 1, base: 1, weights: { disagreement: 1, interval: 0.5, coverage: 1 }, disagreement: { raw: 0.2, sdLnW: 0.1, sdLnD: 0.3, normalised: 1, nResolvedKernels: 3, resolvedKernels: ['a', 'b', 'c'] },
        intervalWidth: { lnHiOverLo: null, term: null, note: 'n' }, coverage: { regimeClass: 'conduction', classTrainingSets: 3, minSetsPerClass: 8, classUnderCovered: true, nearestDistanceStd: 1.2, value: 0.7 } },
      layout: { printOrder: 1, x_start_mm: 3, x_end_mm: 13, y_mm: 3 } }],
    commands: ['python x'], limits: 'a proposal',
  });
  const markup = html(<ExperimentPlanView plan={plan} />);
  assert.ok(markup.includes('Download blind-test templates from this plan'));
  const verbatim = "This plan shows a score, the disagreement between the app's kernels and an interval width for each track, not a predicted depth, so viewing it does not count as viewing predictions. For a blind test, use these templates, not measurement_template.csv: importing these tracks' measurements for machine calibration with the commands below makes any blind test on them not blind.";
  assert.equal(PLAN_BLIND_NOTICE, verbatim);
  assert.ok(markup.includes(verbatim));
});

test('no rendered text claims validation or accuracy, uses PASS or FAIL, or contains a dash used as punctuation', () => {
  assert.ok(ALL.length > 15);
  for (const m of ALL) {
    assert.doesNotMatch(m, /\bvalidated\b/i);
    assert.doesNotMatch(m, /validation of the model/i);
    assert.doesNotMatch(m, /accuracy/i);
    assert.doesNotMatch(m, /\b(PASS|FAIL)\b/);
    assert.doesNotMatch(m, /[–—]/);
  }
});
