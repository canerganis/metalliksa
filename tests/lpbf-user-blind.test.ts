import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { webcrypto } from 'node:crypto';
import protocol from '../data/blind/lpbf-user-blind-protocol-v1.json';
import {
  BLIND_REVEAL_PHRASE,
  assertNoPredictionKeys,
  blindCsvTextCell,
  blindInputsFromPlanCsv,
  blindInputsTemplateCsv,
  blindMetadataTemplateJson,
  blindTargetsTemplateCsv,
  checkInputsHeader,
  checkTargetsHeader,
  checkedBlindBundleResult,
  checkedBlindFreezeResult,
  checkedBlindGet,
  checkedBlindList,
  checkedBlindOpenResult,
  checkedBlindPreview,
  checkedBlindReceipt,
  checkedBlindReport,
  checkedBlindRevealResult,
  checkedBlindScoreResult,
  formatSignedPercent,
} from '../src/data/lpbfUserBlind';
import { LPBF_EXPERIMENT_PLAN_LABEL, checkedExperimentPlan } from '../src/data/lpbfExperimentPlan';
import { BLIND_FIELD_HELP, PLAN_PANEL_SENTENCE, PREDICTION_SURFACES } from '../src/components/research/blindTestHelp';
import { BlindClientError, HASH_CHECK_SKIPPED_NOTE, createBlindClient, describeBlindError } from '../src/services/lpbfUserBlindClient';
import { USER_BLIND_STORE_KEY, mergeBlindPersisted, safeBlindStorage, useUserBlindStore } from '../src/store/useUserBlindStore';
import { BLIND_DRAFT_DEFAULTS } from '../src/data/lpbfUserBlind';

const fixture = (name: string): Record<string, unknown> => {
  const raw = JSON.parse(readFileSync(new URL(`./fixtures/lpbf-user-blind-${name}.SYNTHETIC.json`, import.meta.url), 'utf8')) as { _title: string; document: Record<string, unknown> };
  assert.equal(raw._title, 'Synthetic fixture, not measured data');
  return raw.document;
};
const clone = <T,>(v: T): T => JSON.parse(JSON.stringify(v)) as T;
const fileText = (path: string) => readFileSync(new URL(path, import.meta.url), 'utf8');
const lf = (s: string) => s.replace(/\r\n/g, '\n');

type Checker = (v: unknown) => unknown;
const DOCS: [string, string, Checker][] = [
  ['preview', 'preview', checkedBlindPreview], ['receipt', 'receipt', checkedBlindReceipt], ['report', 'report', checkedBlindReport],
  ['list', 'list', checkedBlindList], ['get', 'get', checkedBlindGet], ['score-result', 'score result', checkedBlindScoreResult],
  ['reveal-result', 'reveal result', checkedBlindRevealResult],
];

test('every validator accepts the fixture produced by the real Python code', () => {
  for (const [name, , check] of DOCS) assert.doesNotThrow(() => check(fixture(name)), name);
  assert.doesNotThrow(() => checkedBlindFreezeResult(fixture('receipt')));
  // bundle and open results have no fixture; build them from the closed key sets of RESULT_KEYS.
  const honesty = fixture('reveal-result').honesty;
  const key = String(fixture('receipt').freezeKey);
  const sha = 'a'.repeat(64);
  assert.doesNotThrow(() => checkedBlindBundleResult({ freezeKey: key, bundleN: 1, sha256: sha, size: 10, documents: [{ name: 'blind-bundle.tar', attempt: 1 }], honesty, provenance: {} }));
  assert.doesNotThrow(() => checkedBlindOpenResult({ freezeKey: key, name: 'blind-report.json', attempt: 1, sha256: sha, size: 10, honesty, provenance: {} }));
});

test('every honesty literal is enforced in every document type', () => {
  const breaks: [string, (h: Record<string, unknown>) => void][] = [
    ['experimentalValidation true', h => { h.experimentalValidation = true; }],
    ['experimentalValidation the string "false"', h => { h.experimentalValidation = 'false'; }],
    ['experimentalValidation missing', h => { delete h.experimentalValidation; }],
    ['appValidation true', h => { h.appValidation = true; }],
    ['labelPromotionProposed', h => { h.labelPromotionProposed = 'proposed'; }],
    ['evidenceKind', h => { h.evidenceKind = 'validated-simulation'; }],
    ['dataLabel', h => { h.dataLabel = 'Measured'; }],
    ['resultScope', h => { h.resultScope = 'shared-result'; }],
    ['neverEnters member false', h => { (h.neverEnters as Record<string, unknown>).g3 = false; }],
    ['unknown honesty key', h => { h.extra = true; }],
  ];
  for (const [name, , check] of DOCS) {
    for (const [what, mutate] of breaks) {
      const doc = clone(fixture(name));
      const holder = name === 'get' || name === 'list' ? doc : doc;
      mutate(holder.honesty as Record<string, unknown>);
      assert.throws(() => check(doc), /lpbf user blind rejected/, `${name}: ${what}`);
    }
  }
  // The honesty block inside the receipt of a get document is checked too.
  const get = clone(fixture('get'));
  ((get.receipt as Record<string, unknown>).honesty as Record<string, unknown>).appValidation = true;
  assert.throws(() => checkedBlindGet(get), /appValidation/);
});

test('unknown status words, unknown keys and prediction-like keys are refused', () => {
  const report = clone(fixture('report'));
  ((report.arms as Record<string, Record<string, unknown>>).served).status = 'PASS';
  assert.throws(() => checkedBlindReport(report), /unknown word/);
  const blind = clone(fixture('report'));
  (blind.blindness as Record<string, unknown>).status = 'blind-ish';
  assert.throws(() => checkedBlindReport(blind), /unknown word/);
  const list = clone(fixture('list'));
  (((list.entries as Record<string, unknown>[])[0].latestStatus) as Record<string, unknown>).served = 'passed';
  assert.throws(() => checkedBlindList(list), /unknown word/);
  const score = clone(fixture('score-result'));
  (score.statuses as Record<string, string>).served = 'validated';
  assert.throws(() => checkedBlindScoreResult(score), /unknown word/);

  for (const [name, , check] of DOCS) {
    const doc = clone(fixture(name));
    doc.surprise = 1;
    assert.throws(() => check(doc), /unknown key 'surprise'/, `${name} top-level key`);
  }
  const preview = clone(fixture('preview'));
  (preview.budget as Record<string, unknown>).value_um = 61.7;
  assert.throws(() => checkedBlindPreview(preview), /prediction-like key 'value_um'/);
  const receipt = clone(fixture('receipt'));
  (receipt.designChecks as Record<string, unknown>).pred = {};
  assert.throws(() => checkedBlindReceipt(receipt), /prediction-like key 'pred'/);
  const reveal = clone(fixture('reveal-result'));
  (reveal.documents as Record<string, unknown>[])[0].rel = 0.1;
  assert.throws(() => checkedBlindRevealResult(reveal), /prediction-like key 'rel'/);
  const get = clone(fixture('get'));
  ((get.attempts as Record<string, unknown>[])[0]).trackDepths_um = [1];
  assert.throws(() => checkedBlindGet(get), /prediction-like key 'trackDepths_um'/);
  const list2 = clone(fixture('list'));
  (list2.entries as Record<string, unknown>[])[0].ledger = [];
  assert.throws(() => checkedBlindList(list2), /prediction-like key 'ledger'/);
  for (const key of ['depth_um', 'width_um', 'D_obs_um']) {
    assert.throws(() => assertNoPredictionKeys({ nested: [{ [key]: 1 }] }), /prediction-like key/, key);
  }
  // The predictor and scorer identity subtrees are exempt.
  const exempt = clone(fixture('receipt'));
  (exempt.predictorIdentity as Record<string, unknown>).ledger = { value_um: 1 };
  (exempt.scorerIdentity as Record<string, unknown>).rel = 1;
  assert.doesNotThrow(() => checkedBlindReceipt(exempt));
});

test('the report validator keeps the user and served value labels', () => {
  const a = clone(fixture('report'));
  ((a.ledger as Record<string, unknown>[])[0].observed as Record<string, unknown>).sourceEvidenceKind = 'Measured';
  assert.throws(() => checkedBlindReport(a), /Measured \(user-supplied\)/);
  const b = clone(fixture('report'));
  ((((b.ledger as Record<string, unknown>[])[0].pred as Record<string, Record<string, unknown>>).served)).sourceEvidenceKind = 'Validated simulation';
  assert.throws(() => checkedBlindReport(b), /Unresolved/);
  const c = clone(fixture('report'));
  (c.userValueLabel as Record<string, unknown>).tier = 'Reviewed';
  assert.throws(() => checkedBlindReport(c), /userValueLabel/);
});

test('header helpers: aliases, dialects, units, target-like names, example rows', () => {
  const ok = checkInputsHeader('condition_id,track_id,P_W,Speed (mm/s),beam_um\nA,A1,100,800,80\n', 'comma-dot');
  assert.equal(ok.ok, true);
  assert.deepEqual(ok.echoes.map(e => e.canonical).sort(), ['power_W', 'speed_mm_s', 'spot_um']);
  const unit = checkInputsHeader('track_id,Power [kW],Speed (m/s),Spot (mm)\nA,0.1,0.8,0.08\n', 'comma-dot');
  assert.equal(unit.ok, true);
  assert.equal(unit.mapped.power_W.factor, 1000);
  assert.equal(unit.mapped.speed_mm_s.factor, 1000);
  assert.equal(unit.mapped.spot_um.factor, 1000);
  const unitless = checkInputsHeader('track_id,P,v,spot\nA,100,800,80\n', 'comma-dot');
  assert.equal(unitless.ok, true);
  assert.ok(unitless.labels.includes('unit not stated, read as W'));
  assert.ok(unitless.labels.includes('unit not stated, read as mm/s'));

  assert.equal(checkInputsHeader('Power (MW),v,spot\n1,2,3\n', 'comma-dot').issues[0].code, 'HEADER_UNIT_UNKNOWN');
  assert.equal(checkInputsHeader('track_id;P_W;v_mm_s\nA;1;2\n', 'comma-dot').issues[0].code, 'DIALECT_MISMATCH');
  assert.equal(checkInputsHeader('track_id,P_W,v_mm_s\nA,1,2\n', 'semicolon-comma').issues[0].code, 'DIALECT_MISMATCH');
  assert.equal(checkInputsHeader('track_id;P_W;v_mm_s;spot_um\nA;100;800;80\n', 'semicolon-comma').ok, true);

  const target = checkInputsHeader('track_id,P_W,v_mm_s,depth_um\nA,1,2,3\n', 'comma-dot');
  assert.equal(target.issues[0].code, 'INPUTS_TARGET_COLUMN');
  assert.match(target.issues[0].message, /Column 'depth_um' may be a measurement/);
  const layer = checkInputsHeader('track_id,P_W,v_mm_s,layer height\nA,1,2,3\n', 'comma-dot');
  assert.match(layer.issues[0].message, /contains 'height'/);
  for (const name of ['D', 'W', 'd', 'w']) {
    assert.equal(checkInputsHeader(`track_id,P_W,v_mm_s,${name}\nA,1,2,3\n`, 'comma-dot').issues[0].code, 'INPUTS_TARGET_COLUMN', name);
  }
  assert.equal(checkInputsHeader('track_id,P_W,v_mm_s,notes\nA,1,2,x\n', 'comma-dot').issues[0].code, 'INPUTS_UNKNOWN_COLUMN');
  assert.equal(checkInputsHeader('track_id,P,power_W,v_mm_s\nA,1,2,3\n', 'comma-dot').issues[0].code, 'AMBIGUOUS_ALIAS');
  assert.equal(checkInputsHeader('track_id,P_W\nA,1\n', 'comma-dot').issues[0].code, 'INPUTS_COLUMN_MISSING');
  assert.equal(checkInputsHeader('P_W,v_mm_s\n1,2\n', 'comma-dot').issues.some(i => i.code === 'INPUTS_COLUMN_MISSING'), true);
  assert.equal(checkInputsHeader('track_id,P_W,v_mm_s\n', 'comma-dot').issues[0].code, 'FILE_EMPTY');
  assert.equal(checkInputsHeader('PK\u0003\u0004binary', 'comma-dot').issues[0].code, 'FILE_NOT_CSV_UTF8');
  assert.equal(checkInputsHeader('﻿track_id,P_W,v_mm_s\nA,1,2\n', 'comma-dot').ok, true);

  const example = checkInputsHeader(blindInputsTemplateCsv(), 'comma-dot');
  assert.equal(example.exampleRow, true);
  assert.equal(example.ok, false);
  assert.ok(example.issues.some(i => i.code === 'SYNTHETIC_EXAMPLE_ROW'));
  assert.equal(checkTargetsHeader(blindTargetsTemplateCsv(), 'comma-dot').exampleRow, true);

  const targets = checkTargetsHeader('condition_id,Depth (um),notes,P_W\nA,40,x,100\n', 'comma-dot');
  assert.equal(targets.ok, true);
  assert.deepEqual(targets.ignored, ['notes']);
  assert.equal(targets.dataLines, 1);
  assert.equal(checkTargetsHeader('condition_id,width_um\nA,40\n', 'comma-dot').issues[0].code, 'TARGETS_COLUMN_MISSING');
  assert.equal(checkTargetsHeader('depth_um,width_um\n40,50\n', 'comma-dot').issues[0].code, 'TARGETS_COLUMN_MISSING');
  assert.equal(checkTargetsHeader('condition;depth\nA;40\n', 'comma-dot').issues[0].code, 'DIALECT_MISMATCH');
});

test('template headers equal the protocol record and the committed template files', () => {
  assert.equal(blindInputsTemplateCsv().split('\n')[0], protocol.templates.inputs.join(','));
  assert.equal(blindTargetsTemplateCsv().split('\n')[0], protocol.templates.targets.join(','));
  assert.equal(lf(blindInputsTemplateCsv()), lf(fileText('../data/blind/templates/blind_inputs_v1.csv')));
  assert.equal(lf(blindTargetsTemplateCsv()), lf(fileText('../data/blind/templates/blind_targets_v1.csv')));
  assert.deepEqual(JSON.parse(blindMetadataTemplateJson()), JSON.parse(fileText('../data/blind/templates/blind_metadata_v1.json')));
  for (const csv of [blindInputsTemplateCsv(), blindTargetsTemplateCsv()]) assert.match(csv.split('\n')[1], /SYNTHETIC-EXAMPLE/);
  assert.equal(BLIND_REVEAL_PHRASE, 'reveal predictions and end blind status');
});

test('blindCsvTextCell neutralises formula starts and leaves numbers alone', () => {
  assert.equal(blindCsvTextCell('=1+1'), "'=1+1");
  assert.equal(blindCsvTextCell('+x'), "'+x");
  assert.equal(blindCsvTextCell('-2'), "'-2");
  assert.equal(blindCsvTextCell('@a'), "'@a");
  assert.equal(blindCsvTextCell('\tt'), "'\tt");
  assert.equal(blindCsvTextCell('\rr'), "'\rr");
  assert.equal(blindCsvTextCell(-3.5), -3.5);
  assert.equal(blindCsvTextCell(0), 0);
  assert.equal(blindCsvTextCell(''), '');
  assert.equal(blindCsvTextCell(null), '');
  assert.equal(blindCsvTextCell(true), 'true');
  // Cross-language twin: python/lpbf_user_blind_protocol.text_cell_safe is run on the same list by the lead.
  const cells: (string | number)[] = ['=1+1', '+x', '-2', '@a', '\tt', '\rr', 'plain', -3.5, 12, 'a=b'];
  assert.deepEqual(cells.map(blindCsvTextCell), ["'=1+1", "'+x", "'-2", "'@a", "'\tt", "'\rr", 'plain', -3.5, 12, 'a=b']);
});

test('formatting helper shows a signed percent with one decimal and keeps inf as text', () => {
  assert.equal(formatSignedPercent(0.5425000000000002), '+54.3 %');
  assert.equal(formatSignedPercent(-0.1234), '-12.3 %');
  assert.equal(formatSignedPercent(0), '+0.0 %');
  assert.equal(formatSignedPercent(null), 'n/a');
  assert.match(formatSignedPercent('inf'), /^inf/);
});

test('the plan template writes track ids, power, speed and spot only, never a score or a spread', () => {
  const sha = 'a'.repeat(64);
  const point = (n: number) => ({
    trackId: `T0${n}`, rank: n, power_W: 100 * n, speed_mm_s: 400 * n, beamDiameter_um: 90, layer_um: 40, preheat_C: 80, regimeClass: 'conduction',
    score: { total: 7.31 / n, base: 7.31 / n, weights: { disagreement: 1, interval: 0.5, coverage: 1 },
      disagreement: { raw: 0.4417, sdLnW: 0.1, sdLnD: 0.3, normalised: 1, nResolvedKernels: 3, resolvedKernels: ['a', 'b', 'c'] },
      intervalWidth: { lnHiOverLo: 0.6123, term: 0.3, note: 'width' },
      coverage: { regimeClass: 'conduction', classTrainingSets: 3, minSetsPerClass: 8, classUnderCovered: true, nearestDistanceStd: 1.2, value: 0.7 } },
    layout: { printOrder: 3 - n, x_start_mm: 3, x_end_mm: 13, y_mm: 3 },
  });
  const plan = checkedExperimentPlan({
    schema: 'lpbf-next-experiment-plan-1', label: LPBF_EXPERIMENT_PLAN_LABEL, evidenceKind: 'screening-only',
    material: '316L Stainless Steel', configSha256: sha, calibration: { available: false, reason: 'none' },
    intervalWidth: { lnHiOverLo: null, note: 'none' }, plate: { x_mm: 100, y_mm: 60, pitch_mm: 3, trackLength_mm: 10, edgeMargin_mm: 3 },
    points: [point(1), point(2)], commands: ['python x'], limits: 'a proposal',
  });
  const csv = blindInputsFromPlanCsv(plan);
  assert.equal(csv, 'track_id,power_W,speed_mm_s,spot_um\nT02,200,800,90\nT01,100,400,90\n');
  for (const forbidden of ['7.31', '0.4417', '0.6123', 'score', 'disagreement', 'interval', 'regime']) assert.ok(!csv.includes(forbidden), forbidden);
  assert.ok(!blindMetadataTemplateJson().includes('7.31'));
  assert.equal(checkInputsHeader(csv, 'comma-dot').ok, true);
});

function mockResponse(status: number, body: unknown, headers: Record<string, string> = {}): Response {
  return new Response(typeof body === 'string' ? body : JSON.stringify(body), { status, headers });
}

test('client: document fetch reports the hash check as skipped without SubtleCrypto', async () => {
  const bytes = new TextEncoder().encode('hello');
  const calls: string[] = [];
  const fetchStub = async (url: string) => { calls.push(url); return new Response(bytes, { status: 200 }); };
  const without = createBlindClient({ fetch: fetchStub, subtle: () => undefined });
  assert.equal(without.hasSubtleCrypto(), false);
  const skipped = await without.fetchDocument('job1', 'blind-report.json', 'b'.repeat(64));
  assert.equal(skipped.hashCheck, 'skipped');
  assert.equal(skipped.sha256, null);
  assert.equal(HASH_CHECK_SKIPPED_NOTE, 'Browser hash check unavailable on this connection; the worker checked the hash.');

  const withSubtle = createBlindClient({ fetch: fetchStub, subtle: () => webcrypto.subtle as SubtleCrypto });
  const digest = Array.from(new Uint8Array(await webcrypto.subtle.digest('SHA-256', bytes)), b => b.toString(16).padStart(2, '0')).join('');
  assert.equal((await withSubtle.fetchDocument('job1', 'blind-report.json', digest)).hashCheck, 'matched');
  assert.equal((await withSubtle.fetchDocument('job1', 'blind-report.json', null)).hashCheck, 'not-declared');
  await assert.rejects(withSubtle.fetchDocument('job1', 'blind-report.json', 'c'.repeat(64)), (e: unknown) => e instanceof BlindClientError && e.kind === 'hash-mismatch');
  assert.deepEqual(calls.slice(-1), ['/api/lpbf/jobs/job1/artifacts/blind-report.json']);
});

test('client: a refusal surfaces the code and the message only', async () => {
  const body = { success: false, errorKind: 'validation', error: { code: 'ATMOSPHERE_X', field: 'atmosphere', message: 'Fixed refusal sentence.', detail: { secret: 'DETAIL-MUST-NOT-SHOW' } }, stack: 'STACK-MUST-NOT-SHOW' };
  const client = createBlindClient({ fetch: async () => mockResponse(422, body) });
  const error = await client.preview({}, 'AAAA', 'x.csv').catch((e: unknown) => e);
  assert.ok(error instanceof BlindClientError);
  assert.equal(error.kind, 'refusal');
  assert.equal(error.code, 'ATMOSPHERE_X');
  assert.equal(error.message, 'Fixed refusal sentence.');
  const shown = describeBlindError(error);
  assert.equal(shown, 'Fixed refusal sentence. (ATMOSPHERE_X)');
  assert.ok(!shown.includes('DETAIL-MUST-NOT-SHOW') && !shown.includes('STACK-MUST-NOT-SHOW'));
});

test('client: typed errors for worker unavailable, queue full and 413', async () => {
  const run = (response: Response) => createBlindClient({ fetch: async () => response }).list().then(() => { throw new Error('expected a refusal'); }, (e: unknown) => e as BlindClientError);
  const unavailable = await run(mockResponse(503, { error: 'x' }, { 'Retry-After': '1' }));
  assert.equal(unavailable.kind, 'worker-unavailable');
  assert.equal(unavailable.retryAfterS, 1);
  assert.equal((await run(mockResponse(400, { error: 'Queue full' }))).kind, 'queue-full');
  assert.equal((await run(mockResponse(413, { error: 'Simulation input too large' }))).kind, 'too-large');
  assert.equal((await run(mockResponse(500, 'oops'))).kind, 'http');
  assert.equal((await run(mockResponse(200, { schema: 'wrong' }))).kind, 'invalid-response');
});

test('client: routes, payload keys, poll results and the comparison export path', async () => {
  const seen: { url: string; init?: RequestInit }[] = [];
  const fetchStub = async (url: string, init?: RequestInit) => {
    seen.push({ url, init });
    if (url === '/api/lpbf/jobs') return mockResponse(202, { id: 'abc123' });
    if (url === '/api/lpbf/jobs/abc123') return mockResponse(200, { id: 'abc123', status: 'failed', error: 'Fixed child message.', blindError: 'PREVIEW_DRIFT', log: 'ignored' });
    if (url === '/api/lpbf/jobs/done') return mockResponse(200, { id: 'done', status: 'completed', result: fixture('score-result') });
    if (url === '/api/lpbf/jobs/run') return mockResponse(200, { id: 'run', status: 'running', progress: 0.4 });
    if (url.endsWith('/artifacts/blind-comparison.csv')) return new Response('csv bytes as written by python', { status: 200 });
    return mockResponse(200, fixture('list'));
  };
  const client = createBlindClient({ fetch: fetchStub, subtle: () => undefined });
  await client.list(0, 50);
  assert.equal(seen[0].url, '/api/lpbf/estimate');
  assert.deepEqual(JSON.parse(String(seen[0].init?.body)), { jobType: 'user-blind-list', schema: 'lpbf-user-blind-request-1', page: 0, pageSize: 50 });
  assert.equal(await client.submit('user-blind-reveal', { freezeKey: 'k'.repeat(64), confirmation: BLIND_REVEAL_PHRASE }), 'abc123');
  assert.equal(seen[1].url, '/api/lpbf/jobs');
  assert.equal(JSON.parse(String(seen[1].init?.body)).jobType, 'user-blind-reveal');
  const failed = await client.pollJob('abc123', 'user-blind-freeze');
  assert.deepEqual(failed, { state: 'failed', status: 'failed', code: 'PREVIEW_DRIFT', message: 'Fixed child message.' });
  const done = await client.pollJob('done', 'user-blind-score');
  assert.equal(done.state, 'completed');
  assert.equal((await client.pollJob('run', 'user-blind-score')).state, 'pending');
  const csv = await client.fetchDocument('job9', 'blind-comparison.csv', null);
  assert.equal(new TextDecoder().decode(csv.bytes), 'csv bytes as written by python');
  assert.equal(seen[seen.length - 1].url, '/api/lpbf/jobs/job9/artifacts/blind-comparison.csv');
  // Every request stays on this origin.
  for (const s of seen) assert.ok(s.url.startsWith('/api/lpbf/'), s.url);
});

test('no non-same-origin URL in the data, client, store or component sources', () => {
  const files = [
    '../src/data/lpbfUserBlind.ts', '../src/services/lpbfUserBlindClient.ts', '../src/store/useUserBlindStore.ts',
    '../src/components/research/blindTestHelp.ts', '../src/components/research/BlindTestPanel.tsx', '../src/components/research/BlindTestInputsStep.tsx',
    '../src/components/research/BlindTestTargetsStep.tsx', '../src/components/research/BlindTestReportView.tsx', '../src/components/research/BlindTestReceiptView.tsx',
    '../src/components/research/BlindTestMetadataForm.tsx', '../src/components/research/BlindTestList.tsx', '../src/components/research/BlindTestLink.tsx',
  ];
  for (const f of files) assert.doesNotMatch(fileText(f), /https?:\/\//, f);
  const report = fileText('../src/components/research/BlindTestReportView.tsx');
  assert.match(report, /print\(\)/);
});

test('the comparison CSV export downloads the worker file and builds no CSV text', () => {
  const panel = fileText('../src/components/research/BlindTestPanel.tsx');
  const view = fileText('../src/components/research/BlindTestReportView.tsx');
  assert.match(panel, /'blind-comparison\.csv'/);
  assert.match(panel, /fetchDocument/);
  for (const source of [panel, view, fileText('../src/services/lpbfUserBlindClient.ts')]) {
    assert.doesNotMatch(source, /toCsv|csvCell|blindCsvTextCell|\.join\(','\)\s*\+\s*['"`]\\n/);
  }
});

test('store: the whitelist merge drops unknown and wrongly typed persisted fields', () => {
  const current = useUserBlindStore.getState();
  const hex = 'a'.repeat(64);
  const merged = mergeBlindPersisted({
    draft: { blockLabel: 'kept', alloy: 7, inputsCsvBase64: 'AAAA', csvText: 'a,b' },
    pending: [{ id: 'job1', jobType: 'user-blind-score', freezeKey: hex, name: null, attempt: null }, { id: 'bad id!', jobType: 'user-blind-score', freezeKey: null }, { id: 'j2', jobType: 'user-blind-share', freezeKey: null }],
    known: [{ freezeKey: hex, freezeSha256: hex, createdAt: '2026-10-17T00:00:00Z', blockLabel: 'b', alloy: 'Ti-6Al-4V', conditions: 12, predictions: [1, 2] }, { freezeKey: 'short' }],
    extra: 'dropped', csv: 'x',
  }, current);
  assert.equal(merged.draft.blockLabel, 'kept');
  assert.equal(merged.draft.alloy, BLIND_DRAFT_DEFAULTS.alloy);
  assert.ok(!('inputsCsvBase64' in merged.draft) && !('csvText' in merged.draft));
  assert.deepEqual(merged.pending.map(p => p.id), ['job1']);
  assert.equal(merged.known.length, 1);
  assert.ok(!('predictions' in merged.known[0]));
  assert.ok(!('extra' in merged) && !('csv' in merged));
  const empty = mergeBlindPersisted('garbage', current);
  assert.deepEqual(empty.draft, BLIND_DRAFT_DEFAULTS);
  assert.deepEqual(empty.pending, []);
});

test('store: a throwing localStorage never breaks reads, writes or actions', () => {
  const original = (globalThis as { localStorage?: unknown }).localStorage;
  const thrower = { getItem() { throw new Error('blocked'); }, setItem() { throw new Error('blocked'); }, removeItem() { throw new Error('blocked'); } };
  Object.defineProperty(globalThis, 'localStorage', { value: thrower, configurable: true, writable: true });
  try {
    assert.equal(safeBlindStorage.getItem('x'), null);
    assert.doesNotThrow(() => safeBlindStorage.setItem('x', 'y'));
    assert.doesNotThrow(() => safeBlindStorage.removeItem('x'));
    assert.doesNotThrow(() => useUserBlindStore.getState().patchDraft({ blockLabel: 'survives' }));
    assert.equal(useUserBlindStore.getState().draft.blockLabel, 'survives');
  } finally {
    Object.defineProperty(globalThis, 'localStorage', { value: original, configurable: true, writable: true });
    useUserBlindStore.getState().resetDraft();
  }
});

test('store: nothing but the draft, job ids and receipt summaries is ever persisted', () => {
  const written: Record<string, string> = {};
  const memory = { getItem: (k: string) => written[k] ?? null, setItem: (k: string, v: string) => { written[k] = v; }, removeItem: (k: string) => { delete written[k]; } };
  const original = (globalThis as { localStorage?: unknown }).localStorage;
  Object.defineProperty(globalThis, 'localStorage', { value: memory, configurable: true, writable: true });
  try {
    const hex = 'b'.repeat(64);
    const store = useUserBlindStore.getState();
    store.patchDraft({ blockLabel: 'Persisted block', alloy: 'Ti-6Al-4V' });
    store.addPending({ id: 'job77', jobType: 'user-blind-freeze', freezeKey: null, name: null, attempt: null });
    store.rememberFreeze({ freezeKey: hex, freezeSha256: hex, createdAt: '2026-10-17', blockLabel: 'Persisted block', alloy: 'Ti-6Al-4V', conditions: 12 });
    const raw = written[USER_BLIND_STORE_KEY];
    assert.ok(raw, 'the store wrote its key');
    const parsed = JSON.parse(raw) as { state: Record<string, unknown> };
    assert.deepEqual(Object.keys(parsed.state).sort(), ['draft', 'known', 'pending']);
    assert.doesNotMatch(raw, /inputsCsvBase64|targetsCsvBase64|condition_id|value_um|D_obs_um|"predictions"/);
    store.removePending('job77');
    store.forgetFreeze(hex);
    store.resetDraft();
  } finally {
    Object.defineProperty(globalThis, 'localStorage', { value: original, configurable: true, writable: true });
  }
});

test('help data: the predictions-viewed help names every surface and the plan panel exception', () => {
  const help = BLIND_FIELD_HELP.predictionsViewedBeforeFreeze.help;
  for (const surface of PREDICTION_SURFACES) assert.ok(help.includes(surface), surface);
  for (const word of ['Build Job result', 'process window', 'melt-pool cross-section lab', 'Dataset Comparison lab', 'spent-set descriptive panel', 'Melt Pool vs Measurements lab', 'machine-calibration block', 'Research model panel', 'Melt Pool lab', 'Build Job Decision lab', 'CLI']) {
    assert.ok(help.includes(word), word);
  }
  assert.ok(help.includes(PLAN_PANEL_SENTENCE));
  assert.match(PLAN_PANEL_SENTENCE, /experiment plan panel shows no depth/);
  for (const [field, h] of Object.entries(BLIND_FIELD_HELP)) {
    assert.ok(h.label && h.help, field);
    assert.doesNotMatch(`${h.label} ${h.help}`, /\bvalidated\b|accuracy|[–—]/i, field);
  }
});
