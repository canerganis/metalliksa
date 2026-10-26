import React from 'react';
import assert from 'node:assert/strict';
import test from 'node:test';
import { renderToStaticMarkup } from 'react-dom/server';
import { alsiFixtures } from './support/alsi10mgEvaporativeFixtures';
import { fixtures as ti64Fixtures } from './support/ti64EvaporativeFixtures';
import {
  parseAlSi10MgEvaporativeJob, parseTi64EvaporativeJob, type AlSi10MgEvaporativeResult,
} from '../src/services/lpbfSimulationService';
import {
  ALSI10MG_EVAPORATION_SCENARIO, ALSI10MG_EVAPORATIVE_TRACK_UM, ALSI10MG_PROXY_DISCLOSURE,
  alsi10mgEvaporativeAvailability, buildAlSi10MgEvaporativeInput,
} from '../src/utils/alsi10mgEvaporativeModel';
import {
  AlSi10MgEvaporativePanel, AlSi10MgEvaporativeResultView, AlSi10MgRunStatus, alsi10mgResultIsStale, alsi10mgResultSettings,
} from '../src/components/AlSi10MgEvaporativePanel';

const clone = <T,>(v: T): T => JSON.parse(JSON.stringify(v));
const html = (node: React.ReactElement) => renderToStaticMarkup(node).replace(/&#x27;/g, "'");
const onset: AlSi10MgEvaporativeResult = parseAlSi10MgEvaporativeJob(alsiFixtures.onset).result!;
const melt: AlSi10MgEvaporativeResult = parseAlSi10MgEvaporativeJob(alsiFixtures.noEvaporation).result!;
const REFUSAL = "The model's recoil/capillary onset criterion was exceeded; surface deformation and keyhole geometry are not resolved, so depth, length and volume are not reported.";

test('real AlSi10Mg worker fixtures parse with the proxy disclosure; tampered or foreign jobs do not', () => {
  assert.equal(onset.modelId, 'alsi10mg-al6061-proxy-fixed-surface-evaporation-v1');
  assert.equal(onset.disclosure, ALSI10MG_PROXY_DISCLOSURE);
  assert.equal(onset.gate.onset, true);
  assert.equal(onset.geometry.depth_um, null);
  assert.equal(onset.geometry.refusalReason, REFUSAL);
  assert.equal(melt.gate.geometryAvailable, true);
  assert.ok((melt.geometry.depth_um as number) > 0);
  const filled = clone(alsiFixtures.onset); filled.result.geometry.depth_um = 50;
  assert.throws(() => parseAlSi10MgEvaporativeJob(filled), /Inconsistent AlSi10Mg evaporative refusal/);
  const validated = clone(alsiFixtures.onset); validated.result.experimentalValidation = true;
  assert.throws(() => parseAlSi10MgEvaporativeJob(validated), /result identity/);
  const undisclosed = clone(alsiFixtures.onset); delete undisclosed.result.disclosure;
  assert.throws(() => parseAlSi10MgEvaporativeJob(undisclosed), /result identity/);
  const open = clone(alsiFixtures.onset); open.result.energy.relativeResidual = 1e-3;
  assert.throws(() => parseAlSi10MgEvaporativeJob(open), /energy ledger/);
  assert.throws(() => parseAlSi10MgEvaporativeJob(ti64Fixtures.w1Onset), /Invalid AlSi10Mg evaporative job response/);
  assert.throws(() => parseTi64EvaporativeJob(alsiFixtures.onset), /Invalid Ti64 evaporative job response/);
});

test('AlSi10Mg model choice is disabled with a reason for another alloy or a powder layer', () => {
  assert.deepEqual(alsi10mgEvaporativeAvailability('AlSi10Mg', 'bare-plate'), { available: true });
  const alloy = alsi10mgEvaporativeAvailability('Ti-6Al-4V', 'bare-plate');
  assert.equal(alloy.available, false);
  assert.match((alloy as { reason: string }).reason, /only for AlSi10Mg.*Ti-6Al-4V/);
  const powder = alsi10mgEvaporativeAvailability('AlSi10Mg', 'powder-layer');
  assert.match((powder as { reason: string }).reason, /bare plate only.*powder layer is not modelled/);

  const wrong = html(<AlSi10MgEvaporativePanel material="Inconel 718" process={{ power_W: 300, speed_mm_s: 1300, beamDiameter_um: 100, preheat_C: 80 }} />);
  assert.match(wrong, /type="checkbox"[^>]*disabled/);
  assert.ok(wrong.includes('this model exists only for AlSi10Mg'));
  const right = html(<AlSi10MgEvaporativePanel material="AlSi10Mg" process={{ power_W: 300, speed_mm_s: 1300, beamDiameter_um: 100, preheat_C: 80 }} />);
  assert.ok(right.includes('AlSi10Mg evaporative surface, Al6061 proxy (research)'));
  assert.ok(right.includes('bare plate only'));
  assert.ok(right.includes(ALSI10MG_PROXY_DISCLOSURE));
  assert.ok(right.includes('Run AlSi10Mg evaporative surface model'));
  assert.match(right, /<button[^>]*disabled[^>]*>Run AlSi10Mg evaporative surface model/); // disabled until opt-in
  assert.doesNotMatch(right, /type="checkbox"[^>]*disabled/);
});

test('the UI request uses the separate job type, the 600 um track and the Gan-sourced scenario', () => {
  const input = buildAlSi10MgEvaporativeInput({ power_W: 300, speed_mm_s: 1300, beamDiameter_um: 100, preheat_C: 80 });
  assert.equal(input.jobType, 'alsi10mg-evaporative-surface');
  assert.equal(ALSI10MG_EVAPORATIVE_TRACK_UM, 600);
  assert.equal(input.config.trackLength_um, 600);
  assert.deepEqual(input.config.evaporation, { ...ALSI10MG_EVAPORATION_SCENARIO });
  assert.deepEqual([input.config.evaporation.transitionLow_K, input.config.evaporation.transitionHigh_K,
    input.config.evaporation.returnFraction, input.config.evaporation.surfaceTension_N_m], [2800, 3200, 0.18, 0.91]);
});

test('the result view keeps null extents with their reason, the disclosure and the solver labels verbatim', () => {
  const view = html(<AlSi10MgEvaporativeResultView result={onset} />);
  assert.ok(view.includes(onset.researchLabel));
  assert.ok(view.includes(ALSI10MG_PROXY_DISCLOSURE));
  assert.ok(view.includes('experimentalValidation=false'));
  assert.equal((view.match(new RegExp(`null <span[^>]*>\\(not available: ${REFUSAL.replace(/\./g, '\\.')}\\)`, 'g')) ?? []).length, 3);
  assert.ok(view.includes(onset.geometry.widthWarning!));
  assert.ok(view.includes('Evaporative loss'));
  const meltView = html(<AlSi10MgEvaporativeResultView result={melt} />);
  assert.doesNotMatch(meltView, /not available/);
});

test('a finished result goes stale when power, speed, beam diameter or preheat change, and a running job shows its submitted settings', () => {
  // No DOM runtime in this repo: the panel's staleness predicate and status component are driven through
  // each input edit, the same way the panel feeds them after the user changes the shared process inputs.
  const base = alsi10mgResultSettings(onset);
  assert.deepEqual(base, { power_W: 300, speed_mm_s: 1300, beamDiameter_um: 100, preheat_C: 80 });
  assert.equal(alsi10mgResultIsStale(onset, base), false);
  assert.equal(alsi10mgResultIsStale(undefined, base), false);
  const edits = { power_W: 301, speed_mm_s: 1301, beamDiameter_um: 101, preheat_C: 81 };
  for (const [key, value] of Object.entries(edits)) {
    const changed = { ...base, [key]: value };
    assert.equal(alsi10mgResultIsStale(onset, changed), true, key);
    const view = html(<AlSi10MgEvaporativeResultView result={onset} stale={alsi10mgResultIsStale(onset, changed)} />);
    assert.ok(view.includes('Inputs changed after this run'), key);
    assert.ok(view.includes(ALSI10MG_PROXY_DISCLOSURE), key);
    const status = html(<AlSi10MgRunStatus job={clone(alsiFixtures.onset)} process={changed} />);
    assert.ok(status.includes('Submitted settings: 300 W, 1300 mm/s, 100 µm beam, 80 °C preheat.'), key);
    assert.ok(status.includes('now read'), key);
  }
  assert.ok(!html(<AlSi10MgEvaporativeResultView result={onset} stale={false} />).includes('Inputs changed after this run'));
  const quiet = html(<AlSi10MgRunStatus job={clone(alsiFixtures.onset)} process={base} />);
  assert.ok(!quiet.includes('Submitted settings') && !quiet.includes('now read'));
  const running = { ...clone(alsiFixtures.onset), status: 'running', progress: 0.4 };
  delete running.result;
  const runningJob = parseAlSi10MgEvaporativeJob(running);
  const live = html(<AlSi10MgRunStatus job={runningJob} submitted={base} process={{ ...base, power_W: 250 }} />);
  assert.ok(live.includes('running · 40%'));
  assert.ok(live.includes('Submitted settings: 300 W, 1300 mm/s, 100 µm beam, 80 °C preheat.'));
  assert.ok(live.includes('now read 250 W'));
  assert.ok(html(<AlSi10MgRunStatus job={runningJob} submitted={base} process={base} />).includes('Submitted settings'));
});
