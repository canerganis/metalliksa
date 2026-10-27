import React from 'react';
import assert from 'node:assert/strict';
import test from 'node:test';
import { renderToStaticMarkup } from 'react-dom/server';
import { proxyFixtures } from './support/proxyEvaporativeFixtures';
import { alsiFixtures } from './support/alsi10mgEvaporativeFixtures';
import {
  parseAlSi10MgEvaporativeJob, parseProxyEvaporativeJob, type ProxyEvaporativeResult,
} from '../src/services/lpbfSimulationService';
import {
  PROXY_ALLOY_PROFILES, PROXY_EVAPORATIVE_TRACK_UM, buildProxyEvaporativeInput, proxyAlloyFor, proxyEvaporativeAvailability,
} from '../src/utils/proxyEvaporativeModel';
import {
  ProxyEvaporativePanel, ProxyEvaporativeResultView, ProxyRunStatus, proxyResultIsStale, proxyResultSettings,
} from '../src/components/ProxyEvaporativePanel';

const clone = <T,>(v: T): T => JSON.parse(JSON.stringify(v));
const html = (node: React.ReactElement) => renderToStaticMarkup(node).replace(/&#x27;/g, "'");
const ss316: ProxyEvaporativeResult = parseProxyEvaporativeJob(proxyFixtures.ss316lOnset).result!;
const in718: ProxyEvaporativeResult = parseProxyEvaporativeJob(proxyFixtures.in718Onset).result!;
const userThresholds: ProxyEvaporativeResult = parseProxyEvaporativeJob(proxyFixtures.in718UserThresholds).result!;
const REFUSAL = "The model's recoil/capillary onset criterion was exceeded; surface deformation and keyhole geometry are not resolved, so depth, length and volume are not reported.";
const PROCESS = { power_W: 150, speed_mm_s: 1000, beamDiameter_um: 100, preheat_C: 80 };

test('real 316L and IN718 worker fixtures parse with their disclosure and the Unresolved label; tampered or foreign jobs do not', () => {
  assert.equal(ss316.modelId, 'ss316l-gan2021-ss316-proxy-fixed-surface-evaporation-v1');
  assert.equal(in718.modelId, 'in718-fang2021-ni-proxy-fixed-surface-evaporation-v1');
  assert.equal(ss316.disclosure, PROXY_ALLOY_PROFILES['316L Stainless Steel'].disclosure);
  assert.equal(in718.disclosure, PROXY_ALLOY_PROFILES['Inconel 718'].disclosure);
  for (const r of [ss316, in718]) {
    assert.equal(r.evidenceLabel, 'Unresolved');
    assert.deepEqual(r.evidence.unresolvedInputs, ['transitionLow_K', 'transitionHigh_K']);
    assert.equal(r.gate.onset, true);
    assert.equal(r.geometry.depth_um, null);
    assert.equal(r.geometry.refusalReason, REFUSAL);
    assert.equal(r.experimentalValidation, false);
  }
  assert.equal(userThresholds.evidenceLabel, 'User input');
  assert.deepEqual(userThresholds.evidence.userInputs, ['transitionLow_K', 'transitionHigh_K']);
  assert.ok((userThresholds.geometry.depth_um as number) > 0);

  const filled = clone(proxyFixtures.in718Onset); filled.result.geometry.depth_um = 50;
  assert.throws(() => parseProxyEvaporativeJob(filled), /Inconsistent proxy evaporative refusal/);
  const validated = clone(proxyFixtures.in718Onset); validated.result.experimentalValidation = true;
  assert.throws(() => parseProxyEvaporativeJob(validated), /result identity/);
  const promoted = clone(proxyFixtures.in718Onset); promoted.result.evidenceLabel = 'Literature estimate';
  assert.throws(() => parseProxyEvaporativeJob(promoted), /evidence label/);
  const emptied = clone(proxyFixtures.in718Onset); emptied.result.evidence.unresolvedInputs = [];
  assert.throws(() => parseProxyEvaporativeJob(emptied), /evidence label/);
  const swapped = clone(proxyFixtures.in718Onset); swapped.result.modelId = ss316.modelId;
  assert.throws(() => parseProxyEvaporativeJob(swapped), /result identity/);
  const open = clone(proxyFixtures.ss316lOnset); open.result.energy.relativeResidual = 1e-3;
  assert.throws(() => parseProxyEvaporativeJob(open), /energy ledger/);
  assert.throws(() => parseProxyEvaporativeJob(alsiFixtures.onset), /Invalid proxy evaporative job response/);
  assert.throws(() => parseAlSi10MgEvaporativeJob(proxyFixtures.in718Onset), /Invalid AlSi10Mg evaporative job response/);
});

test('the proxy model choice appears for 316L and IN718 only, and is disabled with a reason for a powder layer', () => {
  assert.equal(proxyAlloyFor('316L'), '316L Stainless Steel');
  assert.equal(proxyAlloyFor('IN718'), 'Inconel 718');
  assert.equal(proxyAlloyFor('AlSi10Mg'), undefined);
  assert.deepEqual(proxyEvaporativeAvailability('Inconel 718', 'bare-plate'), { available: true, alloy: 'Inconel 718' });
  const alloy = proxyEvaporativeAvailability('Ti-6Al-4V', 'bare-plate');
  assert.match((alloy as { reason: string }).reason, /only for 316L and IN718.*Ti-6Al-4V/);
  const powder = proxyEvaporativeAvailability('316L Stainless Steel', 'powder-layer');
  assert.match((powder as { reason: string }).reason, /bare plate only.*powder layer is not modelled/);

  const wrong = html(<ProxyEvaporativePanel material="AlSi10Mg" process={PROCESS} />);
  assert.match(wrong, /type="checkbox"[^>]*disabled/);
  for (const [material, name] of [['316L Stainless Steel', '316L'], ['Inconel 718', 'IN718']] as const) {
    const right = html(<ProxyEvaporativePanel material={material} process={PROCESS} />);
    const profile = PROXY_ALLOY_PROFILES[material];
    assert.ok(right.includes(profile.label), material);
    assert.ok(right.includes(profile.disclosure), material);
    assert.ok(right.includes('bare plate only'), material);
    assert.ok(right.includes(`Output label: Unresolved. No source gives the vaporization transition thresholds for this alloy; the run uses declared defaults transitionLow_K = ${profile.scenario.transitionLow_K} K and transitionHigh_K = ${profile.scenario.transitionHigh_K} K.`), material);
    assert.match(right, new RegExp(`<button[^>]*disabled[^>]*>Run ${name} evaporative surface model`)); // disabled until opt-in
    assert.doesNotMatch(right, /type="checkbox"[^>]*disabled/);
  }
});

test('the UI request uses the shared job type, the named alloy, the 600 um track and the declared scenario', () => {
  const input = buildProxyEvaporativeInput('Inconel 718', PROCESS);
  assert.equal(input.jobType, 'proxy-evaporative-surface');
  assert.equal(input.config.material, 'Inconel 718');
  assert.equal(PROXY_EVAPORATIVE_TRACK_UM, 600);
  assert.equal(input.config.trackLength_um, 600);
  assert.deepEqual(input.config.evaporation, { transitionLow_K: 3083, transitionHigh_K: 3583, ambientPressure_Pa: 101325, returnFraction: 0.18, maxTemperature_K: 5000, surfaceTension_N_m: 1.882 });
  assert.deepEqual(buildProxyEvaporativeInput('316L Stainless Steel', PROCESS).config.evaporation,
    { transitionLow_K: 3022, transitionHigh_K: 3522, ambientPressure_Pa: 101325, returnFraction: 0.18, maxTemperature_K: 5000, surfaceTension_N_m: 1.87 });
});

test('the result view shows the evidence label with the named inputs, null extents with their reason and the disclosure', () => {
  for (const r of [ss316, in718]) {
    const view = html(<ProxyEvaporativeResultView result={r} />);
    assert.ok(view.includes(r.researchLabel));
    assert.ok(view.includes(r.disclosure));
    assert.ok(view.includes('Evidence label: <strong>Unresolved</strong>'));
    assert.ok(view.includes('Unresolved inputs: transitionLow_K, transitionHigh_K.'));
    assert.ok(view.includes('experimentalValidation=false'));
    assert.equal((view.match(new RegExp(`null <span[^>]*>\\(not available: ${REFUSAL.replace(/\./g, '\\.')}\\)`, 'g')) ?? []).length, 3);
    assert.ok(view.includes(r.geometry.widthWarning!));
  }
  const userView = html(<ProxyEvaporativeResultView result={userThresholds} />);
  assert.ok(userView.includes('Evidence label: <strong>User input</strong>'));
  assert.doesNotMatch(userView, /not available/);
});

test('a finished result goes stale when the alloy or any shared process input changes, and a running job shows its submitted settings', () => {
  const base = proxyResultSettings(in718);
  assert.deepEqual(base, PROCESS);
  assert.equal(proxyResultIsStale(in718, base, 'Inconel 718'), false);
  assert.equal(proxyResultIsStale(in718, base, '316L Stainless Steel'), true);
  assert.equal(proxyResultIsStale(undefined, base), false);
  for (const [key, value] of Object.entries({ power_W: 151, speed_mm_s: 1001, beamDiameter_um: 101, preheat_C: 81 })) {
    const changed = { ...base, [key]: value };
    assert.equal(proxyResultIsStale(in718, changed, 'Inconel 718'), true, key);
    assert.ok(html(<ProxyEvaporativeResultView result={in718} stale />).includes('Inputs changed after this run'), key);
    const status = html(<ProxyRunStatus job={clone(proxyFixtures.in718Onset)} process={changed} />);
    assert.ok(status.includes('Submitted settings: 150 W, 1000 mm/s, 100 µm beam, 80 °C preheat.'), key);
    assert.ok(status.includes('now read'), key);
  }
  const running = { ...clone(proxyFixtures.in718Onset), status: 'running', progress: 0.4 };
  delete running.result;
  const runningJob = parseProxyEvaporativeJob(running);
  const live = html(<ProxyRunStatus job={runningJob} submitted={base} process={{ ...base, power_W: 250 }} />);
  assert.ok(live.includes('running · 40%'));
  assert.ok(live.includes('now read 250 W'));
});
