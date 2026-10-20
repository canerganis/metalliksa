import React from 'react';
import assert from 'node:assert/strict';
import test from 'node:test';
import { renderToStaticMarkup } from 'react-dom/server';
import { fixtures } from './support/ti64EvaporativeFixtures';
import { parseTi64EvaporativeJob, type Ti64EvaporativeResult } from '../src/services/lpbfSimulationService';
import { pythonComputationService } from '../src/services/pythonComputationService';
import {
  TI64_EVAPORATIVE_TRACK_UM, buildTi64EvaporativeInput, ti64EvaporativeAvailability,
} from '../src/utils/ti64EvaporativeModel';
import {
  P8_BELOW_ONSET_NOTE, P8_HYPOTHESIS_NOTE, P8_ROW_TITLE, P8_UNAVAILABLE_SUFFIX, W1_CRITERION_NOTE,
  buildP8Request, fetchP8Depth, p8PairingApplies, p8PairingKey, p8ViewFromRun,
} from '../src/utils/ti64EvaporativeResearchDepth';
import { Ti64EvaporativePanel, Ti64EvaporativeResultView } from '../src/components/Ti64EvaporativePanel';

const clone = <T,>(v: T): T => JSON.parse(JSON.stringify(v));
const onset: Ti64EvaporativeResult = parseTi64EvaporativeJob(fixtures.w1Onset).result!;
const REFUSAL = 'The surface would deform into a vapor cavity at these settings. A fixed-surface model cannot give melt depth here. Use a model with surface motion and melt flow for depth, length and volume.';
const LITERAL_VALIDATION = 'Not experimentally validated; research diagnostic/model only.';
const html = (node: React.ReactElement) => renderToStaticMarkup(node).replace(/&#x27;/g, "'");

test('real worker job fixtures parse; a filled extent beside a closed gate, a validated flag or a foreign job type do not', () => {
  assert.equal(onset.gate.onset, true);
  assert.equal(onset.geometry.depth_um, null);
  assert.equal(onset.geometry.refusalReason, REFUSAL);
  parseTi64EvaporativeJob(fixtures.w1BelowOnset);
  const filled = clone(fixtures.w1Onset); filled.result.geometry.depth_um = 50;
  assert.throws(() => parseTi64EvaporativeJob(filled), /Inconsistent Ti64 evaporative refusal/);
  const validated = clone(fixtures.w1Onset); validated.result.experimentalValidation = true;
  assert.throws(() => parseTi64EvaporativeJob(validated), /result identity/);
  const foreign = clone(fixtures.w1Onset); foreign.requestSummary.jobType = 'transient-thermal';
  assert.throws(() => parseTi64EvaporativeJob(foreign), /Invalid Ti64 evaporative job response/);
  const open = clone(fixtures.w1Onset); open.result.energy.relativeResidual = 1e-3;
  assert.throws(() => parseTi64EvaporativeJob(open), /energy ledger/);
});

test('model choice is disabled with a reason for another alloy or a powder layer', () => {
  assert.deepEqual(ti64EvaporativeAvailability('Ti-6Al-4V', 'bare-plate'), { available: true });
  assert.deepEqual(ti64EvaporativeAvailability('ti64', 'bare-plate'), { available: true });
  const alloy = ti64EvaporativeAvailability('Inconel 718', 'bare-plate');
  assert.equal(alloy.available, false);
  assert.match((alloy as { reason: string }).reason, /only for Ti-6Al-4V.*Inconel 718/);
  const powder = ti64EvaporativeAvailability('Ti-6Al-4V', 'powder-layer');
  assert.equal(powder.available, false);
  assert.match((powder as { reason: string }).reason, /bare plate only.*powder layer is not modelled/);

  const wrong = html(<Ti64EvaporativePanel material="Inconel 718" process={{ power_W: 285, speed_mm_s: 960, beamDiameter_um: 80, preheat_C: 80 }} />);
  assert.match(wrong, /type="checkbox"[^>]*disabled/);
  assert.ok(wrong.includes('this model exists only for Ti-6Al-4V'));
  const right = html(<Ti64EvaporativePanel material="Ti-6Al-4V" process={{ power_W: 150, speed_mm_s: 1000, beamDiameter_um: 80, preheat_C: 80 }} />);
  assert.ok(right.includes('Ti-6Al-4V evaporative surface (research)'));
  assert.ok(right.includes('600 µm declared track'));
  assert.doesNotMatch(right, /type="checkbox"[^>]*disabled/);
});

test('the UI request keeps the measured 600 um track and the declared scenario', () => {
  const input = buildTi64EvaporativeInput({ power_W: 150, speed_mm_s: 1000, beamDiameter_um: 80, preheat_C: 80 });
  assert.equal(TI64_EVAPORATIVE_TRACK_UM, 600);
  assert.equal(input.jobType, 'ti64-evaporative-surface');
  assert.equal(input.config.trackLength_um, 600);
  assert.equal(input.config.evaporation.maxTemperature_K, 5000);
});

test('C2 trigger: only a crossed onset with resolved geometry bookkeeping starts the pairing', () => {
  assert.equal(p8PairingApplies(onset), true);
  assert.equal(p8PairingApplies(parseTi64EvaporativeJob(fixtures.w1BelowOnset).result), false);
  const unresolved = clone(onset); unresolved.gate.unresolvedGeometry = true; // derived from the real fixture: other cause of a null extent
  assert.equal(p8PairingApplies(unresolved), false);
  assert.equal(p8PairingApplies(undefined), false);
});

test('the P8 request is bound to the executed provenance inputs, unconverted, with explicit IR and flat plate', () => {
  const request = buildP8Request(onset, 'nominal', 'id:1', 'p8-research:batch:abcdefgh');
  assert.deepEqual(request.process, { material: 'Ti-6Al-4V', laserPower_W: 150, scanSpeed_mm_s: 1000, beamDiameter_um: 80, preheatTemp_C: 80,
    laserWavelength: 'IR_1064nm', absorptionModel: 'flat-plate' });
  assert.deepEqual(request.propertyContext, { kind: 'nominal' });
  assert.equal(request.researchOptions, undefined);
  assert.equal(buildP8Request(onset, 'band', 'id:2', 'k', 1500).timeBudgetMs, 1500);
});

test('onset true with P8 available shows the linked depth only, with the required disclosures', () => {
  const view = p8ViewFromRun(fixtures.p8Above);
  assert.equal(view.status, 'available');
  assert.equal(view.atOrBelowOnset, false);
  assert.ok(Math.abs((view.linked!.value as number) - 71.66566383588037) < 1e-9);
  const out = html(<Ti64EvaporativeResultView result={onset} p8={view} />);
  for (const text of [P8_ROW_TITLE, W1_CRITERION_NOTE, P8_HYPOTHESIS_NOTE, REFUSAL, LITERAL_VALIDATION, 'FIELD_SHAPE_STEP_NEAR_ONSET',
    'p8-melt-link-s2-hypothesis-v2', 'meltDepthLink.linkedMeltDepth_um', 'P/P* 4.47309', 'Scenario envelope (complete)', 'null']) {
    assert.ok(out.includes(text), text);
  }
  assert.ok(!out.includes(P8_BELOW_ONSET_NOTE));
  // W1 depth stays null; no cavity depth is substituted.
  assert.ok(!out.includes('cavityDepth_um'));
  assert.ok(out.includes('Conditional fixed-surface liquidus width estimate'));
});

test('P8 at or below its own onset adds the onset caveat', () => {
  const view = p8ViewFromRun(fixtures.p8Below);
  assert.equal(view.status, 'available');
  assert.equal(view.atOrBelowOnset, true);
  assert.ok(html(<Ti64EvaporativeResultView result={onset} p8={view} />).includes(P8_BELOW_ONSET_NOTE));
});

test('P8 unavailable shows the returned reason code and text and supplies no substitute depth', () => {
  const view = p8ViewFromRun(fixtures.p8Unavailable);
  assert.equal(view.status, 'unavailable');
  assert.equal(view.reason!.code, 'ASPECT_BOUND_OUTSIDE_NUMERICAL_SCOPE');
  assert.ok(view.reason!.text.length > 0);
  const out = html(<Ti64EvaporativeResultView result={onset} p8={view} />);
  assert.ok(out.includes(`P8 linked depth is unavailable: ASPECT_BOUND_OUTSIDE_NUMERICAL_SCOPE ${view.reason!.text}. ${P8_UNAVAILABLE_SUFFIX}`));
  assert.ok(!out.includes('Scenario envelope'));
  // An available container with a null leaf is also unavailable.
  const nullLeaf = clone(fixtures.p8Above); nullLeaf.researchModels.meltDepthLink.fields.linkedMeltDepth_um.value = null;
  assert.equal(p8ViewFromRun(nullLeaf).status, 'unavailable');
});

test('no P8 row without a crossed onset or when the inputs changed', () => {
  const below = parseTi64EvaporativeJob(fixtures.w1BelowOnset).result!;
  const noOnset = html(<Ti64EvaporativeResultView result={below} />);
  assert.ok(!noOnset.includes(P8_ROW_TITLE));
  assert.ok(!noOnset.includes(W1_CRITERION_NOTE));
  const stale = html(<Ti64EvaporativeResultView result={onset} p8={p8ViewFromRun(fixtures.p8Above)} stale />);
  assert.ok(!stale.includes(P8_ROW_TITLE));
  assert.ok(stale.includes('Inputs changed after this run'));
  assert.notEqual(p8PairingKey(onset), JSON.stringify(['Ti-6Al-4V', 151, 1000, 80, 80]));
  assert.equal(p8PairingKey(onset), JSON.stringify(['Ti-6Al-4V', 150, 1000, 80, 80]));
});

test('fetchP8Depth sends nominal then band on the executed inputs and reports each view', async t => {
  const sent: Array<{ stage: string; process: unknown }> = [];
  t.mock.method(pythonComputationService, 'solveLpbfResearchModels', async (request: { stage: string; process: unknown }) => {
    sent.push({ stage: request.stage, process: request.process });
    const nominal = request.stage === 'nominal';
    return { kind: 'run', response: { ...clone(fixtures.p8Above), stage: request.stage, requestKey: 'k',
      progress: { armsTotal: 79, armsDone: nominal ? 7 : 79, complete: !nominal } } };
  });
  const views: string[] = [];
  await fetchP8Depth(onset, view => views.push(view.status));
  assert.deepEqual(sent.map(s => s.stage), ['nominal', 'band']);
  assert.deepEqual(views, ['available', 'available']);
  assert.deepEqual((sent[0].process as { laserPower_W: number }).laserPower_W, 150);
});
