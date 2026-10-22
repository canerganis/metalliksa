import assert from 'node:assert/strict';
import { test } from 'node:test';
import React from 'react';
import { registerHooks } from 'node:module';
import { renderToStaticMarkup } from 'react-dom/server';

// Atrium imports stylesheets, which plain Node cannot load: stub .css modules.
registerHooks({
  resolve: (specifier, context, next) => specifier.endsWith('.css') ? { url: 'data:text/javascript,export default {}', shortCircuit: true } : next(specifier, context),
});

// IS_STATIC_DEMO reads this global once, at module load, so set it before the dynamic imports.
(globalThis as { __STATIC_DEMO__?: boolean }).__STATIC_DEMO__ = true;

const ONLINE = { online: true, status: 'online', pythonVersion: '3.12.1' };

test('demo mode never claims a live engine: start page, boot steps and engine note', async () => {
  const { Atrium } = await import('../src/components/Atrium.tsx');
  const { buildBootSteps, describeEngine } = await import('../src/services/bootSteps.ts');
  const { DemoEngineNote } = await import('../src/demo/demoNotes.tsx');

  const atrium = renderToStaticMarkup(<Atrium continueId="lpbf-optimizer" engine={ONLINE} engineChecking={false} shortcutLabel="Ctrl K" onNavigate={() => {}} onSearch={() => {}} />);
  assert.ok(atrium.includes('static snapshot'), 'start page says static snapshot');

  const steps = buildBootSteps({
    loadConfig: async () => ({ airgapped: false, blockedServices: [] }) as never,
    probe: () => ({ loaded: true, accessRequired: false, failure: null }),
    engineStatus: async () => ONLINE,
    moduleCount: () => 4,
  });
  const details: string[] = [];
  for (const step of steps) details.push((await step.run()).detail);
  details.push(describeEngine(ONLINE).detail);
  const note = renderToStaticMarkup(<DemoEngineNote onClose={() => {}} />);

  for (const text of [atrium, note, ...details]) {
    assert.ok(!text.includes('Calculation engine ready'), text);
    assert.ok(!/online/i.test(text.replace(/\bsnapshot\b/g, '')), text);
    assert.ok(!text.includes('Refresh status'), text);
  }
  assert.ok(details.some(d => d === 'Static snapshot (no engine)'));
});
