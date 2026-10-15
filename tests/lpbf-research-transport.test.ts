import { after, test as baseTest } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import express from "express";
import type { AddressInfo } from "node:net";
import type { Server } from "node:http";
import {
  physicsDeps, physicsRouter, RESEARCH_ADHOC_TIMEOUT_MARKER, RESEARCH_REPLY_TIMEOUT_MARKER,
  RESEARCH_REQUEST_MAX_BYTES, RESEARCH_ROUTE_TIMEOUT_MS,
} from "../routes/physics.ts";

// P8 research route, server side (docs/research/SPEC_p8_integration_contract_2026-10-15.md 3.1, 3.5, 10.3): the
// route literal, the 413 size refusal, handleResearchDispatch's 504 mapping per timeoutKind, the 422 problems, the
// channel on every body, and the two thrown-message literals of server/processOrchestrator.ts. The client side of
// this file (request body, abort, stale rejection, fallback) is phase D work.
// Importing the router starts the persistent Python supervisor (import side effect in
// server/processOrchestrator.ts); exit explicitly once done, preserving a failing exit code.
let anyFailed = false;
const test: typeof baseTest = ((name: string, fn: any) =>
  baseTest(name, async (...args: any[]) => {
    try {
      await fn(...args);
    } catch (error) {
      anyFailed = true;
      throw error;
    }
  })) as any;
after(() => {
  setTimeout(() => process.exit(anyFailed ? 1 : 0), 250);
});

const ROUTE = "/api/python/lpbf-research-models";
const SCRIPT = "python/lpbf_research_models.py";
const REQUEST = {
  schemaVersion: "p8-research-request-v1", supersedeKey: "p8-research:melt-pool", clientRequestId: "melt-pool:1",
  stage: "nominal",
  process: { material: "Ti-6Al-4V", laserPower_W: 200, scanSpeed_mm_s: 800, beamDiameter_um: 80, preheatTemp_C: 20,
    laserWavelength: "IR_1064nm", absorptionModel: "flat-plate" },
  propertyContext: { kind: "nominal" },
};

interface Harness { base: string; close: () => Promise<void> }

async function start(): Promise<Harness> {
  const app = express();
  app.use(express.json({ limit: "5mb" }));
  app.use(physicsRouter);
  const server: Server = await new Promise((resolve) => {
    const s = app.listen(0, "127.0.0.1", () => resolve(s));
  });
  const port = (server.address() as AddressInfo).port;
  return {
    base: `http://127.0.0.1:${port}`,
    close: () => new Promise<void>((resolve) => { server.close(() => resolve()); (server as any).closeAllConnections?.(); }),
  };
}

async function post(h: Harness, route: string, body: unknown) {
  const res = await fetch(h.base + route, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  return { status: res.status, json: (await res.json()) as any };
}

type Call = { script: string; payload: any; timeoutMs: number };
type Runner = (call: Call) => Promise<any>;

async function withRunner(runner: Runner, fn: (h: Harness, calls: Call[]) => Promise<void>) {
  const h = await start();
  const calls: Call[] = [];
  const original = physicsDeps.runPythonScript;
  physicsDeps.runPythonScript = (async (script: string, payload: any, _args: string[], timeoutMs: number) => {
    const call = { script, payload, timeoutMs };
    calls.push(call);
    return runner(call);
  }) as any;
  try {
    await fn(h, calls);
  } finally {
    physicsDeps.runPythonScript = original;
    await h.close();
  }
}

const reply = (stdout: string, exitCode: number | null, channel = "unix_socket") =>
  async () => ({ stdout, stderr: "", exitCode, durationMs: 1, warm: true, channel });

test("the route dispatches the research script with the 30 s route timeout and the request body", async () => {
  const body = { success: true, schemaVersion: "p8-research-response-v1", stage: "nominal" };
  await withRunner(reply(JSON.stringify(body) + "\n", 0), async (h, calls) => {
    const r = await post(h, ROUTE, REQUEST);
    assert.equal(r.status, 200);
    assert.deepEqual(r.json, { ...body, channel: "unix_socket" });
    assert.equal(calls.length, 1);
    assert.equal(calls[0].script, SCRIPT);
    assert.equal(calls[0].timeoutMs, RESEARCH_ROUTE_TIMEOUT_MS);
    assert.equal(RESEARCH_ROUTE_TIMEOUT_MS, 30000);
    assert.deepEqual(calls[0].payload, REQUEST);
  });
});

test("an oversize body is refused with 413 before any dispatch", async () => {
  await withRunner(reply("{}", 0), async (h, calls) => {
    const big = { ...REQUEST, clientRequestId: "x".repeat(RESEARCH_REQUEST_MAX_BYTES) };
    const r = await post(h, ROUTE, big);
    assert.equal(r.status, 413);
    assert.deepEqual(r.json, { success: false, errorKind: "research-request", reasonCode: "RESEARCH_REQUEST_INVALID",
      problems: [{ pointer: "", rule: "too-large", limit: 65536 }] });
    assert.equal(calls.length, 0);
  });
});

test("a refused request (exit 2, validation envelope) surfaces its problems with HTTP 422", async () => {
  const refusal = { success: false, errorKind: "validation", reasonCode: "RESEARCH_REQUEST_INVALID",
    problems: [{ pointer: "/process/laserPower_W", rule: "not-positive", limit: 0, value: "0",
      message: "Laser power (W) must be greater than 0; got 0." }] };
  await withRunner(reply(JSON.stringify(refusal), 2), async (h) => {
    const r = await post(h, ROUTE, REQUEST);
    assert.equal(r.status, 422);
    assert.deepEqual(r.json, { ...refusal, channel: "unix_socket" });
  });
  const stale = { success: false, errorKind: "validation", reasonCode: "RESEARCH_CODE_STALE", problems: [], recycleWorker: true };
  await withRunner(reply(JSON.stringify(stale), 2, "http_microservice"), async (h) => {
    const r = await post(h, ROUTE, REQUEST);
    assert.equal(r.status, 422);
    assert.deepEqual(r.json, { ...stale, channel: "http_microservice" });
  });
});

test("request-scope research failures and superseded envelopes keep HTTP 200, with the channel", async () => {
  for (const body of [
    { success: false, errorKind: "research", reasonCode: "RESEARCH_EVALUATION_FAILED" },
    { success: false, errorKind: "research", reasonCode: "RESEARCH_RESPONSE_TOO_LARGE" },
    { success: false, status: "superseded", reason: "superseded by a newer request with the same supersedeKey before it started; not computed" },
  ]) {
    await withRunner(reply(JSON.stringify(body), 0, "ad_hoc_fallback"), async (h) => {
      const r = await post(h, ROUTE, REQUEST);
      assert.equal(r.status, 200);
      assert.deepEqual(r.json, { ...body, channel: "ad_hoc_fallback" });
    });
  }
});

test("lane queue and run timeouts (exit 124 envelope) become 504 RESEARCH_TIMEOUT with their timeoutKind", async () => {
  for (const kind of ["queue", "run"]) {
    const envelope = { success: false, errorKind: "research", reasonCode: "RESEARCH_TIMEOUT", timeoutKind: kind };
    await withRunner(reply(JSON.stringify(envelope), 124), async (h) => {
      const r = await post(h, ROUTE, REQUEST);
      assert.equal(r.status, 504, kind);
      assert.deepEqual(r.json, { ...envelope, channel: "unix_socket" });
    });
  }
});

test("reply and ad-hoc timeouts (thrown messages) become 504 RESEARCH_TIMEOUT with their timeoutKind", async () => {
  const cases: [string, string, string | null][] = [
    ["Python IPC request may already have run, so it was not retried: UNIX socket IPC got no reply within 35000ms", "reply", "unix_socket"],
    ["Python IPC request may already have run, so it was not retried: HTTP microservice got no reply within 35000ms", "reply", "http_microservice"],
    ["Ad-hoc Python execution timed out after 30000ms", "adhoc", "ad_hoc_fallback"],
  ];
  for (const [message, kind, channel] of cases) {
    await withRunner(async () => { throw new Error(message); }, async (h) => {
      const r = await post(h, ROUTE, REQUEST);
      assert.equal(r.status, 504, message);
      assert.deepEqual(r.json, { success: false, errorKind: "research", reasonCode: "RESEARCH_TIMEOUT", timeoutKind: kind, channel });
    });
  }
});

test("other failures map as handlePythonDispatch maps them, plus the channel", async () => {
  await withRunner(async () => { throw new Error("spawn python ENOENT"); }, async (h) => {
    const r = await post(h, ROUTE, REQUEST);
    assert.equal(r.status, 500);
    assert.deepEqual(r.json, { error: "spawn python ENOENT", script: SCRIPT, channel: null });
  });
  await withRunner(async () => ({ stdout: "", stderr: "Traceback: boom", exitCode: 1, durationMs: 1, channel: "unix_socket" }), async (h) => {
    const r = await post(h, ROUTE, REQUEST);
    assert.equal(r.status, 500);
    assert.deepEqual(r.json, { error: "Traceback: boom", script: SCRIPT, stderr: "Traceback: boom", channel: "unix_socket" });
  });
  // exit 124 without the research envelope is not a research timeout
  await withRunner(async () => ({ stdout: "", stderr: "Execution timed out after 30000ms", exitCode: 124, durationMs: 1, channel: "unix_socket" }), async (h) => {
    const r = await post(h, ROUTE, REQUEST);
    assert.equal(r.status, 500);
    assert.equal(r.json.channel, "unix_socket");
  });
});

test("the thrown-message literals still occur in server/processOrchestrator.ts", () => {
  const source = readFileSync(path.join(process.cwd(), "server", "processOrchestrator.ts"), "utf8");
  assert.equal(RESEARCH_REPLY_TIMEOUT_MARKER, "got no reply within");
  assert.equal(RESEARCH_ADHOC_TIMEOUT_MARKER, "Ad-hoc Python execution timed out after");
  assert.ok(source.includes(`UNIX socket IPC ${RESEARCH_REPLY_TIMEOUT_MARKER}`), "UNIX reply timeout message renamed");
  assert.ok(source.includes(`HTTP microservice ${RESEARCH_REPLY_TIMEOUT_MARKER}`), "HTTP reply timeout message renamed");
  assert.ok(source.includes(`new Error(\`${RESEARCH_ADHOC_TIMEOUT_MARKER}`), "ad-hoc timeout message renamed");
  assert.ok(source.includes("Python IPC request may already have run, so it was not retried"), "reply rethrow renamed");
});

test("the served thermal-solver route is untouched: no channel member, handlePythonDispatch mapping", async () => {
  const served = { success: true, meltPoolGeometry: { depth_um: 50 } };
  await withRunner(reply(JSON.stringify(served), 0), async (h, calls) => {
    const r = await post(h, "/api/python/lpbf-thermal-solver", { material: "Ti-6Al-4V" });
    assert.equal(r.status, 200);
    assert.deepEqual(r.json, served);
    assert.equal(calls[0].script, "python/lpbf_thermal_solver.py");
    assert.equal(calls[0].timeoutMs, 25000);
  });
});
