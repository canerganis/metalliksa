import React from 'react';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { renderToStaticMarkup } from 'react-dom/server';
import { CalibrationStatusDisplay } from '../src/components/CalibrationStatusDisplay';
import { CalibratedMeltpoolPanel, CalibrationStatusCheck, CalibratedResultView, MachineResultView } from '../src/components/3d-distortion-lab/CalibratedMeltpoolPanel';

const load = (name: string) => JSON.parse(readFileSync(new URL(`./fixtures/calibration-status/${name}.json`, import.meta.url), 'utf8'));
const render = (f: any) => renderToStaticMarkup(<CalibrationStatusDisplay status={f.calibrationStatus} parent={f.uncalibratedParent} />);

test('Ti64 stale: status text, both cell texts, parent 110 and 77, keyhole warning first, More toggle', () => {
  const f = load('ti64-stale');
  const out = render(f);
  assert.ok(out.includes(f.calibrationStatus.artifact.text));
  assert.ok(out.includes(f.calibrationStatus.cells.width.text));
  assert.ok(out.includes(f.calibrationStatus.cells.depth.text));
  assert.match(out, /Uncalibrated estimate/);
  assert.match(out, /data-testid="uncal-width"[^>]*>110 µm/);
  assert.match(out, /data-testid="uncal-depth"[^>]*>77 µm/);
  assert.ok(out.indexOf('Keyhole regime') < out.indexOf('Transferred inputs'));
  assert.match(out, /data-estimate-warnings-toggle/);
  assert.match(out, /More \(1 more warning\)/);
  assert.ok(out.includes('Calibrate to your machine for better accuracy.'));
  assert.doesNotMatch(out, /error bar/i);
});

test('AlSi10Mg stale: parent 210 and 100, both cell texts', () => {
  const f = load('alsi10mg-stale');
  const out = render(f);
  assert.match(out, /data-testid="uncal-width"[^>]*>210 µm/);
  assert.match(out, /data-testid="uncal-depth"[^>]*>100 µm/);
  assert.ok(out.includes(f.calibrationStatus.cells.width.text));
  assert.ok(out.includes(f.calibrationStatus.cells.depth.text));
  assert.doesNotMatch(out, /error bar/i);
});

test('AlSi10Mg not requested: its text is visible, no cell lines, no count', () => {
  const f = load('alsi10mg-not-requested');
  const out = render(f);
  assert.ok(out.includes(f.calibrationStatus.artifact.text));
  assert.doesNotMatch(out, /cal-cell-width/);
  assert.doesNotMatch(out, /Enabled calibration cells/);
  assert.doesNotMatch(out, /error bar/i);
});

test('no-value parent shows noValueText and no numbers', () => {
  const f = load('ti64-stale');
  const parent = { ...f.uncalibratedParent, width_um: null, depth_um: null, explanation: null, noValueText: 'No estimate for this input.' };
  const out = renderToStaticMarkup(<CalibrationStatusDisplay status={f.calibrationStatus} parent={parent} />);
  assert.match(out, /No estimate for this input\./);
  assert.doesNotMatch(out, /uncal-width/);
});

test('result view: refusal and status side by side, no calibrated number shown', () => {
  const f = load('ti64-stale');
  const out = renderToStaticMarkup(<CalibratedResultView result={{ ...f, screening: {}, calibration: null, outsideTrainingEnvelope: false, envelopeNotes: [] }} />);
  assert.match(out, /calibrated-unavailable/);
  assert.match(out, /uncalibrated-parent/);
  assert.doesNotMatch(out, /data-testid="cal-width"/);
});

test('machine result shows widthText next to the machine depth', () => {
  const block: any = { available: true, depth_um: 80, depthBand_um: null, evidenceKind: 'screening-only', evidenceScope: null, missingMethodFields: [], reasonText: [], widthText: 'Width is not calibrated to your machine.' };
  const out = renderToStaticMarkup(<MachineResultView artefact={{ machineCalibrationId: 'm1', nTracks: 3, userSourceId: 's' } as any} kernel="rosenthal" block={block} screeningDepth={null} />);
  assert.ok(out.includes('Width is not calibrated to your machine.'));
});

test('no enabled cell: Check calibration status button exists, no toggle, status renders from a response fixture', () => {
  const f = load('ti64-stale');
  const req = { laserPower_W: 200, scanSpeed_mm_s: 900, beamDiameter_um: 80 };
  const bare = renderToStaticMarkup(<CalibratedMeltpoolPanel heatSource="goldak" material="Ti-6Al-4V" request={req} summary={null} />);
  assert.match(bare, /data-testid="calibration-status-check"/);
  assert.match(bare, /Check calibration status/);
  assert.match(bare, /No calibrated mode is offered/);
  assert.doesNotMatch(bare, /data-testid="calibrated-toggle"/);
  assert.doesNotMatch(bare, /type="checkbox"/);
  assert.doesNotMatch(bare, /calibration-status-display/);
  const shown = renderToStaticMarkup(<CalibrationStatusCheck heatSource="goldak" material="Ti-6Al-4V" request={req} initialResult={{ ...f, screening: {}, calibration: null, outsideTrainingEnvelope: false, envelopeNotes: [] }} />);
  assert.ok(shown.includes(f.calibrationStatus.artifact.text));
  assert.ok(shown.includes(f.calibrationStatus.cells.width.text));
  assert.match(shown, /data-testid="uncal-width"[^>]*>110 µm/);
  assert.doesNotMatch(shown, /data-testid="cal-width"/);
});
