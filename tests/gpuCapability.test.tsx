import assert from 'node:assert/strict';
import test from 'node:test';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { GpuCapabilityNotice } from '../src/components/GpuCapabilityNotice';
import { GpuCapabilityError } from '../src/utils/gpuCapability';
import { workerError } from '../routes/lpbfSimulation';
import { EventEmitter } from 'node:events';
import { PassThrough } from 'node:stream';
import { createInterface } from 'node:readline';
import type { ChildProcessWithoutNullStreams } from 'node:child_process';
import { LpbfWorkerBridge } from '../server/lpbfWorkerBridge';
import { gpuPilotApi } from '../src/services/lpbfSimulationService';
import { warpCapabilityFromInventory } from '../src/utils/gpuCapability';

for (const code of ['gpu-runtime-missing', 'gpu-device-missing'] as const) {
  test(`${code}: structured HTTP state and explanatory UI without Retry`, () => {
    const capability = { available: false as const, code };
    const error = new GpuCapabilityError(capability);
    let status = 0; let body: unknown;
    const res = { status(value: number) { status = value; return this; }, json(value: unknown) { body = value; return this; } };
    workerError(res as never, error, 'failure');
    assert.equal(status, 503);
    assert.deepEqual(body, { error: error.message, code, capability });
    const html = renderToStaticMarkup(<GpuCapabilityNotice capability={capability} />);
    assert.match(html, /GPU thermal solver/);
    assert.match(html, /CPU solvers still work/);
    assert.match(html, code === 'gpu-runtime-missing' ? /no GPU runtime/ : /no available CUDA device/);
    assert.doesNotMatch(html, /Retry|No module named|<button/);
    assert.match(html, /role="status"/);
  });
}

for (const code of ['gpu-runtime-missing', 'gpu-device-missing'] as const) {
  test(`${code}: worker JSON-lines bridge and client retain structured state`, async () => {
    const capability = { available: false as const, code };
    const child = Object.assign(new EventEmitter(), {
      pid: 4242, exitCode: null as number | null, signalCode: null,
      stdin: new PassThrough(), stdout: new PassThrough(), stderr: new PassThrough(),
      kill() { this.exitCode = 0; setImmediate(() => this.emit('close', 0)); return true; },
    });
    createInterface({ input: child.stdin }).on('line', line => {
      const request = JSON.parse(line);
      child.stdout.write(JSON.stringify({ id: request.id, ...(request.method === 'capabilities'
        ? { data: {} } : { error: 'internal detail', errorKind: 'capability', capability }) }) + '\n');
    });
    const bridge = new LpbfWorkerBridge({ command: () => ({ cmd: 'mock', args: [] }),
      spawn: () => child as unknown as ChildProcessWithoutNullStreams });
    try {
      await assert.rejects(bridge.request('submit', {}), (error: unknown) => {
        assert.ok(error instanceof GpuCapabilityError);
        assert.deepEqual(error.capability, capability);
        assert.doesNotMatch(error.message, /internal detail/);
        return true;
      });
    } finally { bridge.close(); }
    const original = globalThis.fetch;
    globalThis.fetch = async () => new Response(JSON.stringify({ capability, code }), { status: 503 });
    try {
      await assert.rejects(gpuPilotApi.submit({} as never), (error: unknown) => {
        assert.ok(error instanceof GpuCapabilityError);
        assert.deepEqual(error.capability, capability);
        return true;
      });
    } finally { globalThis.fetch = original; }
    assert.deepEqual(warpCapabilityFromInventory({ gpuDevices: { warp: { capability } } }), capability);
  });
}
