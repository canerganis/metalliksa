import React from 'react';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { renderToStaticMarkup } from 'react-dom/server';
import opticalTable4 from '../data/benchmark/nist-amb2022-03-optical/table4-aggregate-v2.json';
import { FirstRunCard, TourPanel } from '../src/components/GuidedDemo';
import { MELT_POOL_LITERATURE_CASES } from '../src/data/meltPoolLiteratureCases';
import { checkedCalibrationScorecard } from '../src/data/lpbfCalibrationScorecard';
import type { SimulationJob } from '../src/services/lpbfSimulationService';
import { useMaterialSpecimenStore } from '../src/store/useMaterialSpecimenStore';
import { useLpbfEngineeringStore } from '../src/store/useLpbfEngineeringStore';
import { useLpbfResearchModelStore, type ResearchHostState } from '../src/store/useLpbfResearchModelStore';
import { GUIDED_DEMO_STORAGE_KEY, readGuidedDemoOutcome, useGuidedDemoStore, writeGuidedDemoOutcome } from '../src/store/useGuidedDemoStore';
import { compareToMeasurement, demoCase, demoProcessPatch, researchDepthForCase, runMatchesCase, scorecardStatementFor } from '../src/utils/guidedDemo';

const c = demoCase();
const caseZero = opticalTable4.cases.find(row => row.caseNumber === '0')!;

// SYNTHETIC job fixture: only the fields compareToMeasurement reads. The numbers are arithmetic inputs, not a solver result.
function fixtureJob(over: { settings?: Record<string, unknown>; metrics?: Record<string, unknown>; status?: SimulationJob['status'] } = {}): SimulationJob {
  return {
    id: 'fixture0job', status: over.status ?? 'completed', progress: 1, log: '', error: null,
    result: {
      settings: { material: 'Inconel 718', power_W: c.laserPower_W, speed_mm_s: c.scanSpeed_mm_s, beamDiameter_um: c.beamDiameter_um, preheat_C: c.preheatTemp_C, ...over.settings },
      metrics: { width_um: 140, depth_um: 130, length_um: 500, extentStatus: 'computed', ...over.metrics },
      solver: { id: 'fixture-solver', version: '0', openfoam: null },
      provenance: { createdAt: 'x', inputHash: 'x', implementationHash: 'fixture-impl-hash', solverBinaryHash: null },
    },
  } as unknown as SimulationJob;
}
const memoryStorage = (initial?: string) => {
  const map = new Map<string, string>(initial === undefined ? [] : [[GUIDED_DEMO_STORAGE_KEY, initial]]);
  return { getItem: (k: string) => map.get(k) ?? null, setItem: (k: string, v: string) => { map.set(k, v); } };
};
const throwingStorage = { getItem: () => { throw new Error('blocked'); }, setItem: () => { throw new Error('blocked'); } };

test('the case resolves from the committed NIST JSON; a missing or incomplete case throws', () => {
  assert.equal(c.id, 'nist-amb2022-03-0');
  assert.equal(c.laserPower_W, 285);
  assert.equal(c.scanSpeed_mm_s, 960);
  assert.equal(c.beamDiameter_um, 67);
  assert.equal(c.preheatTemp_C, 23.5);
  assert.equal(c.publishedWidth_um, 136.3);
  assert.equal(c.widthStdDev_um, 2.9);
  assert.equal(c.publishedDepth_um, 139.7);
  assert.equal(c.depthStdDev_um, 1.9);
  assert.equal(c.measurementCount, 6);
  assert.equal(c.doi, opticalTable4.doi);
  assert.equal(c.doi, '10.18434/mds2-2718');
  assert.equal(c.laserPower_W, caseZero.laserPower_W);
  assert.deepEqual(demoProcessPatch(c), { laserPower_W: 285, scanSpeed_mms: 960, beamDiameter_um: 67, preheatTemp_C: 23.5 });
  assert.throws(() => demoCase(MELT_POOL_LITERATURE_CASES, 'no-such-case'), /not in the literature cases/);
  assert.throws(() => demoCase(MELT_POOL_LITERATURE_CASES, 'ti64-rosenthal-proof003'), /lacks a measured value/);
  assert.throws(() => demoCase(MELT_POOL_LITERATURE_CASES.filter(x => x.id !== c.id)), /not in the literature cases/);
});

test('compareToMeasurement computes differences from the shown inputs', () => {
  const result = compareToMeasurement(c, fixtureJob());
  assert.ok(result.available);
  if (!result.available) return;
  const [width, depth] = result.rows;
  assert.equal(width.quantity, 'width');
  assert.equal(width.predicted_um, 140);
  assert.equal(width.measured_um, 136.3);
  assert.equal(width.sd_um, 2.9);
  assert.ok(Math.abs(width.diff_um - 3.7) < 1e-9);
  assert.ok(Math.abs(width.diff_pct - (100 * 3.7) / 136.3) < 1e-9);
  assert.equal(width.withinOneSd, false); // 3.7 > 2.9
  assert.ok(Math.abs(depth.diff_um - (130 - 139.7)) < 1e-9);
  assert.equal(depth.withinOneSd, false); // |-9.7| > 1.9
  assert.equal(result.n, 6);
  assert.equal(result.solverId, 'fixture-solver');
  assert.equal(result.implementationHash, 'fixture-impl-hash');
  const close = compareToMeasurement(c, fixtureJob({ metrics: { width_um: 137, depth_um: 141 } }));
  assert.ok(close.available);
  if (close.available) assert.deepEqual(close.rows.map(r => r.withinOneSd), [true, true]); // 0.7 <= 2.9, 1.3 <= 1.9
});

test('compareToMeasurement is unavailable, with a reason and no numbers, when it cannot compare', () => {
  const cases: [string, ReturnType<typeof compareToMeasurement>, RegExp][] = [
    ['no job', compareToMeasurement(c, undefined), /No job has been run/],
    ['running job', compareToMeasurement(c, fixtureJob({ status: 'running' })), /running/],
    ['inputs mismatch', compareToMeasurement(c, fixtureJob({ settings: { power_W: 286 } })), /different material or process inputs/],
    ['extent not computed', compareToMeasurement(c, fixtureJob({ metrics: { extentStatus: 'width-floor-applied' } })), /extent is not computed \(status: width-floor-applied/],
    ['extent not reported', compareToMeasurement(c, fixtureJob({ metrics: { extentStatus: undefined } })), /does not report a melt-pool extent status/],
  ];
  for (const [name, result, reason] of cases) {
    assert.equal(result.available, false, name);
    if (result.available) continue;
    assert.match(result.reason, reason, name);
    assert.equal('rows' in result, false, name);
  }
});

test('runMatchesCase uses a 1e-6 tolerance and the case material', () => {
  const base = { material: 'Inconel 718', power_W: 285, speed_mm_s: 960, beamDiameter_um: 67, preheat_C: 23.5 };
  assert.equal(runMatchesCase(base, c), true);
  assert.equal(runMatchesCase({ ...base, power_W: 285 + 5e-7 }, c), true);
  assert.equal(runMatchesCase({ ...base, power_W: 285 + 2e-6 }, c), false);
  assert.equal(runMatchesCase({ ...base, preheat_C: 25 }, c), false);
  assert.equal(runMatchesCase({ ...base, material: '316L Stainless Steel' }, c), false);
  assert.equal(runMatchesCase({ ...base, speed_mm_s: Number.NaN }, c), false);
  assert.equal(runMatchesCase(undefined, c), false);
});

test('Screening without extent status exposes labelled arithmetic only for matching finite completed results', () => {
  const screening = fixtureJob({ settings: { mode: 'screening' }, metrics: { extentStatus: undefined } });
  screening.result!.effectiveMode = 'screening';
  const result = compareToMeasurement(c, screening);
  assert.ok(result.available);
  if (result.available) {
    assert.equal(result.screeningOnly, true);
    assert.ok(Math.abs(result.rows[0].diff_um - 3.7) < 1e-9);
    assert.ok(Math.abs(result.rows[1].diff_pct - (100 * (130 - 139.7)) / 139.7) < 1e-9);
  }
  const rejected = [
    fixtureJob({ settings: { mode: 'screening', power_W: 286 }, metrics: { extentStatus: undefined } }),
    fixtureJob({ settings: { mode: 'screening' }, metrics: { extentStatus: 'search-box-limited' } }),
    fixtureJob({ settings: { mode: 'screening' }, metrics: { extentStatus: 'unknown-status' } }),
    fixtureJob({ settings: { mode: 'screening' }, metrics: { extentStatus: undefined, width_um: Infinity } }),
    fixtureJob({ settings: { mode: 'screening' }, metrics: { extentStatus: undefined, depth_um: null } }),
    fixtureJob({ settings: { mode: 'screening' }, status: 'failed', metrics: { extentStatus: undefined } }),
    fixtureJob({ settings: { mode: 'standard' }, metrics: { extentStatus: undefined } }),
  ];
  for (const job of rejected) { job.result!.effectiveMode = 'screening'; assert.equal(compareToMeasurement(c, job).available, false); }
  screening.result!.effectiveMode = 'standard';
  const standard = compareToMeasurement(c, screening);
  assert.equal(standard.available, false);
  if (!standard.available) assert.equal(standard.reason, 'The solver does not report a melt-pool extent status for this run, so the tour cannot confirm that width and depth are a closed liquidus isotherm and does not compare them.');
});

test('Screening comparison renders its evidence label, differences and analytical caveat', () => {
  const tour = useGuidedDemoStore.getInitialState();
  const engineering = useLpbfEngineeringStore.getInitialState();
  const before = { step: tour.step, job: engineering.job };
  try {
    tour.step = 3;
    engineering.job = fixtureJob({ settings: { mode: 'screening' }, metrics: { extentStatus: undefined } });
    engineering.job.result!.effectiveMode = 'screening';
    const html = renderToStaticMarkup(<TourPanel engine={null} engineChecking={false} scorecard={null} />);
    assert.match(html, /Screening only, comparison not validation/);
    assert.match(html, /analytical estimate, not a closed liquidus isotherm/);
    assert.match(html, /Diff \(%\)/);
    assert.doesNotMatch(html, /Comparison unavailable/);
    assert.doesNotMatch(html, /Within 1 SD/);
  } finally { tour.step = before.step; engineering.job = before.job; }
});

test('Run step panel stays in document flow so it cannot overlay mode or run controls', () => {
  const tour = useGuidedDemoStore.getInitialState();
  const before = tour.step;
  try {
    tour.step = 2;
    const html = renderToStaticMarkup(<TourPanel engine={null} engineChecking={false} scorecard={null} />);
    const section = html.match(/<section[^>]*>/)![0];
    assert.match(section, /relative/);
    assert.doesNotMatch(section, /fixed|sticky|absolute/);
  } finally { tour.step = before; }
});

test('first-run intro promises labelled screening estimates beside the measurement', () => {
  const html = renderToStaticMarkup(<FirstRunCard home storage={memoryStorage()} />);
  assert.match(html, /analytical width and depth estimates beside the measurement/);
  assert.doesNotMatch(html, /currently unavailable/);
});

test('P8 depth is read only from an existing completed matching research run, never a stale or refused value', () => {
  // SYNTHETIC transport fixture: verifies identity gating, not research physics.
  const host = {
    identity: 'same-input',
    run: {
      status: 'complete', identity: 'same-input', requestKey: 'same-request',
      input: { material: c.material, laserPower_W: c.laserPower_W, scanSpeed_mm_s: c.scanSpeed_mm_s, beamDiameter_um: c.beamDiameter_um, preheatTemp_C: c.preheatTemp_C },
      result: { requestKey: 'same-request', progress: { complete: true }, researchModels: {
        meltDepthLink: { modelId: 'fixture-p8', status: 'available', experimentalValidation: false, fields: { linkedMeltDepth_um: { value: 155, unit: 'um', reasonCode: null } } },
      } },
    },
  } as unknown as ResearchHostState;
  assert.equal(researchDepthForCase(c, host)?.depth.value, 155);
  assert.equal(researchDepthForCase(c, { ...host, identity: 'stale' }), null);
  assert.equal(researchDepthForCase(c, { ...host, run: { ...host.run, status: 'running-nominal' } }), null);
  assert.equal(researchDepthForCase(c, { ...host, run: { ...host.run, requestKey: 'other-request' } }), null);
  assert.equal(researchDepthForCase(c, { ...host, run: { ...host.run, input: { ...host.run.input!, laserPower_W: 999 } } }), null);
  host.run.result!.researchModels!.meltDepthLink!.fields.linkedMeltDepth_um.value = null;
  assert.equal(researchDepthForCase(c, host), null);
});

test('Screening comparison renders a separate held P8 research depth and suppresses a stale host', () => {
  const tour = useGuidedDemoStore.getInitialState();
  const engineering = useLpbfEngineeringStore.getInitialState();
  const research = useLpbfResearchModelStore.getInitialState();
  const before = { step: tour.step, job: engineering.job, hosts: research.hosts };
  // SYNTHETIC values test presentation and identity gating only, not model accuracy.
  const host = {
    identity: 'fixture-current', run: {
      status: 'complete', identity: 'fixture-current', requestKey: 'fixture-request',
      input: { material: c.material, laserPower_W: c.laserPower_W, scanSpeed_mm_s: c.scanSpeed_mm_s, beamDiameter_um: c.beamDiameter_um, preheatTemp_C: c.preheatTemp_C },
      result: { requestKey: 'fixture-request', progress: { complete: true }, researchModels: { meltDepthLink: {
        modelId: 'fixture-p8-render', status: 'available', experimentalValidation: false, uiSentence: 'Synthetic research fixture.',
        fields: { linkedMeltDepth_um: { value: 155, unit: 'um', reasonCode: null, uiSentence: 'Synthetic linked depth.' } },
      } } },
    },
  } as unknown as ResearchHostState;
  try {
    tour.step = 3;
    engineering.job = fixtureJob({ settings: { mode: 'screening' }, metrics: { extentStatus: undefined } });
    engineering.job.result!.effectiveMode = 'screening';
    research.hosts = { ...before.hosts, 'melt-pool': host };
    const render = () => renderToStaticMarkup(<TourPanel engine={null} engineChecking={false} scorecard={null} />);
    const html = render();
    assert.match(html, /Keyhole-mode research depth \(P8\): 155\.0 um/);
    assert.match(html, /Research only, not experimentally validated; separate from the Screening estimate/);
    assert.match(html, /fixture-p8-render/);
    assert.match(html, /<th scope="row">depth<\/th><td>130\.0<\/td>/);
    research.hosts = { ...research.hosts, 'melt-pool': { ...host, identity: 'stale' } };
    assert.doesNotMatch(render(), /Keyhole-mode research depth/);
  } finally { tour.step = before.step; engineering.job = before.job; research.hosts = before.hosts; }
});

test('the committed scorecard reports every IN718 row as no-data; a null record is explicit', () => {
  const record = checkedCalibrationScorecard(JSON.parse(readFileSync('docs/LPBF_CALIBRATION_SCORECARD_2026-10-07.view.json', 'utf8')));
  const rows = record.headline.filter(r => r.material === 'Inconel 718');
  assert.ok(rows.length > 0);
  assert.ok(rows.every(r => r.status === 'no-data'), 'premise: every IN718 row is no-data in the committed record');
  const statement = scorecardStatementFor('Inconel 718', record);
  assert.match(statement, new RegExp(`Every Inconel 718 row \\(${rows.length} of ${rows.length}`));
  assert.match(statement, /is no-data/);
  assert.ok(statement.includes(record.implementationHash));
  assert.match(scorecardStatementFor('Inconel 718', null), /No calibration scorecard record is committed/);
  assert.match(scorecardStatementFor('Unobtainium', record), /has no rows for Unobtainium/);
  // A mixed record is summarised from its rows, never called a pass.
  const mixed = { ...record, headline: record.headline.map((r, i) => (r.material === 'Inconel 718' && i % 2 === 0 ? { ...r, status: 'rejected' as const } : r)) };
  assert.match(scorecardStatementFor('Inconel 718', mixed), /rejected.*no-data|no-data.*rejected/);
});

test('first-run card shows only on the Overview with the key unset, and storage failures do not break it', () => {
  const shown = renderToStaticMarkup(<FirstRunCard home storage={memoryStorage()} />);
  assert.match(shown, /role="region"/);
  assert.match(shown, />Start tour</);
  assert.match(shown, />Skip</);
  assert.equal(renderToStaticMarkup(<FirstRunCard home={false} storage={memoryStorage()} />), '');
  assert.equal(renderToStaticMarkup(<FirstRunCard home storage={memoryStorage('dismissed')} />), '');
  assert.equal(renderToStaticMarkup(<FirstRunCard home storage={memoryStorage('completed')} />), '');
  assert.match(renderToStaticMarkup(<FirstRunCard home storage={memoryStorage('garbage')} />), />Skip</);
  assert.match(renderToStaticMarkup(<FirstRunCard home storage={throwingStorage} />), />Start tour</);
});

test('skip persists under metalliksa.guidedDemo.v1 and a storage throw is survivable', () => {
  const storage = memoryStorage();
  assert.equal(readGuidedDemoOutcome(storage), null);
  assert.equal(writeGuidedDemoOutcome('dismissed', storage), true);
  assert.equal(storage.getItem('metalliksa.guidedDemo.v1'), 'dismissed');
  assert.equal(readGuidedDemoOutcome(storage), 'dismissed');
  assert.equal(renderToStaticMarkup(<FirstRunCard home storage={storage} />), '');
  assert.equal(readGuidedDemoOutcome(throwingStorage), null);
  assert.equal(writeGuidedDemoOutcome('completed', throwingStorage), false);
});

test('the tour panel has its heading, step counter and named buttons, and never claims validation', () => {
  const html = renderToStaticMarkup(<TourPanel engine={null} engineChecking={false} scorecard={null} />);
  assert.match(html, /<h2[^>]*id="guided-demo-title"[^>]*tabindex="-1"[^>]*>Material<\/h2>/);
  assert.match(html, /Step 1 of 4/);
  assert.match(html, /role="region"/);
  for (const name of ['Back', 'Next', 'Exit \\(Esc\\)']) assert.match(html, new RegExp(`<button[^>]*>${name}</button>`), name);
  assert.match(html, /print:hidden/);
  assert.match(html, /bare plate/);
  assert.match(html, /D4σ/);
  assert.match(html, /10\.18434\/mds2-2718/);
  const text = html.replace(/<[^>]+>/g, ' ');
  for (const match of text.matchAll(/validat\w*/gi)) {
    const before = text.slice(Math.max(0, match.index! - 40), match.index!).toLowerCase();
    assert.match(before, /\b(not|no|never|isn't|without)\b/, `"${match[0]}" must appear only in negation: ...${before}`);
  }
});

test('comparison carries the surface configuration and caveats a powder-layer run against the bare-track measurement', () => {
  const powder = compareToMeasurement(c, fixtureJob({ settings: { surfaceMode: 'powder-layer', layer_um: 40, hatch_um: 110 } }));
  assert.ok(powder.available);
  if (powder.available) assert.deepEqual(powder.surface, { mode: 'powder-layer', layer_um: 40, hatch_um: 110, bareTrack: false });
  const bare = compareToMeasurement(c, fixtureJob({ settings: { surfaceMode: 'bare-plate' } }));
  assert.ok(bare.available);
  if (bare.available) assert.equal(bare.surface.bareTrack, true);
});

test('store: start snapshots and loads the case, restore writes the snapshot back, finish and exit persist', async () => {
  // COMMITTED_CALIBRATION_SCORECARD is import.meta.glob-backed and null under tsx, so the production scorecard wiring is covered only by the docs JSON test above.
  const map = new Map<string, string>();
  Object.defineProperty(globalThis, 'localStorage', { configurable: true, value: { getItem: (k: string) => map.get(k) ?? null, setItem: (k: string, v: string) => { map.set(k, v); } } });
  try {
    const before = useMaterialSpecimenStore.getState().activeSpecimen;
    await useGuidedDemoStore.getState().start();
    const state = useGuidedDemoStore.getState();
    assert.equal(state.active, true);
    assert.equal(state.step, 1);
    assert.equal(state.startError, '');
    assert.equal(state.previousSpecimen, before);
    const lpbf = useMaterialSpecimenStore.getState().activeSpecimen.lpbf;
    assert.equal(lpbf.laserPower_W, 285);
    assert.equal(lpbf.scanSpeed_mms, 960);
    assert.equal(lpbf.beamDiameter_um, 67);
    assert.equal(lpbf.preheatTemp_C, 23.5);
    useGuidedDemoStore.getState().restorePrevious();
    assert.equal(useMaterialSpecimenStore.getState().activeSpecimen, before);
    assert.equal(useGuidedDemoStore.getState().previousSpecimen, null);
    useGuidedDemoStore.getState().exit();
    assert.equal(useGuidedDemoStore.getState().active, false);
    assert.equal(map.get(GUIDED_DEMO_STORAGE_KEY), 'dismissed');
    await useGuidedDemoStore.getState().start();
    useGuidedDemoStore.getState().finish();
    assert.equal(map.get(GUIDED_DEMO_STORAGE_KEY), 'completed');
    assert.equal(useGuidedDemoStore.getState().active, false);
  } finally {
    useGuidedDemoStore.setState({ active: false, previousSpecimen: null, step: 1 });
    Reflect.deleteProperty(globalThis, 'localStorage');
  }
});
