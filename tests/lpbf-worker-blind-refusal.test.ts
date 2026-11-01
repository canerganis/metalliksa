import assert from "node:assert/strict";
import type { ChildProcessWithoutNullStreams } from "node:child_process";
import { EventEmitter } from "node:events";
import { createInterface } from "node:readline";
import { PassThrough } from "node:stream";
import { test } from "node:test";
import { LpbfWorkerBridge, LpbfWorkerValidationError } from "../server/lpbfWorkerBridge";
import { workerError } from "../routes/lpbfSimulation";

// The blind-refusal envelope from the Python worker must reach the client unchanged as HTTP 422.
const MESSAGE = "The target column depth_um is blind and cannot be supplied as an input column.";
const ENVELOPE = {
  success: false as const,
  error: { code: "INPUTS_TARGET_COLUMN", field: "inputsCsv", message: MESSAGE, detail: { column: "depth_um" } },
  errorKind: "validation" as const,
};

function fakeChild() {
  const emitter = new EventEmitter() as EventEmitter & Record<string, unknown>;
  emitter.pid = 4242;
  emitter.exitCode = null;
  emitter.signalCode = null;
  emitter.stdout = new PassThrough();
  emitter.stderr = new PassThrough();
  emitter.stdin = new PassThrough();
  emitter.kill = () => {
    emitter.exitCode = 0;
    setImmediate(() => emitter.emit("close", 0));
    return true;
  };
  return emitter as unknown as ChildProcessWithoutNullStreams;
}

/** Bridge on a fake worker that answers each request line with `reply(request)`. */
function bridgeWith(reply: (request: { id: number; method: string }) => Record<string, unknown>) {
  const child = fakeChild();
  createInterface({ input: child.stdin as unknown as PassThrough }).on("line", (line) => {
    const request = JSON.parse(line);
    (child.stdout as unknown as PassThrough).write(`${JSON.stringify({ id: request.id, ...reply(request) })}\n`);
  });
  const bridge = new LpbfWorkerBridge({ command: () => ({ cmd: "native-python", args: [] }), spawn: () => child });
  return bridge;
}

function fakeRes() {
  const out: { status?: number; body?: unknown; headers: Record<string, string> } = { headers: {} };
  const res = {
    status(code: number) { out.status = code; return res; },
    set(name: string, value: string) { out.headers[name] = value; return res; },
    json(body: unknown) { out.body = body; return res; },
  };
  return { res: res as never, out };
}

test("a blind-refusal worker reply becomes LpbfWorkerValidationError with code and message unchanged", async () => {
  const bridge = bridgeWith((request) => request.method === "blind-score"
    ? { error: MESSAGE, errorKind: "validation", validation: ENVELOPE } : { data: {} });
  await assert.rejects(bridge.request("blind-score", { inputsCsv: "depth_um\n1" }), (error: unknown) => {
    assert.ok(error instanceof LpbfWorkerValidationError);
    assert.deepEqual(error.envelope, ENVELOPE);
    assert.equal(error.envelope.error.code, "INPUTS_TARGET_COLUMN");
    assert.equal(error.envelope.error.message, MESSAGE);
    assert.equal(error.message, MESSAGE);
    return true;
  });
  bridge.close();
});

test("workerError answers the blind refusal with HTTP 422 and the envelope as body", () => {
  const r = fakeRes();
  workerError(r.res, new LpbfWorkerValidationError(ENVELOPE), "x");
  assert.equal(r.out.status, 422);
  assert.deepEqual(r.out.body, ENVELOPE);
});
