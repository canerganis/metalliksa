import test from "node:test";
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createServer } from "node:http";
import { mkdtemp, readFile, writeFile, readdir, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { runBatch, parseArgs, type BatchCondition } from "../scripts/research-route-batch";
import { chunkResponse, nominalResponse, finalResponse, TI64_INPUT } from "./support/researchPanelFixtures";
import type { ResearchRequest, ResearchOutcome } from "../src/types/lpbfResearchModels";

const condition: BatchCondition = {
  process: { ...TI64_INPUT, laserWavelength: "IR_1064nm", absorptionModel: "flat-plate" },
  propertyContext: { kind: "nominal" },
};
const good = (r: ResearchRequest): ResearchOutcome => ({ kind: "run", response: r.stage === "nominal" ? nominalResponse(r.clientRequestId) : finalResponse(r.clientRequestId) });
const opts = () => ({ runId: "test1234", log: (_s: string) => {}, write: async (_i: number, _r: unknown) => {} });

test("batch awaits every request and write; uses its own sender, keys and 1500 ms chunks", async () => {
  const seen: ResearchRequest[] = []; let active = 0; let writes = 0;
  await runBatch([condition, condition], { ...opts(), send: async (r) => {
    assert.equal(active++, 0); assert.equal(writes, Math.floor(seen.length / 2));
    await new Promise((resolve) => setTimeout(resolve, 2)); seen.push(r); active--;
    return good(r);
  }, write: async () => { assert.equal(active, 0); writes++; } });
  assert.equal(writes, 2);
  assert.deepEqual(seen.map((r) => r.stage), ["nominal", "band", "nominal", "band"]);
  assert.ok(seen.every((r) => r.sender === "batch-client" && r.supersedeKey === "p8-research:batch:test1234"));
  assert.equal(new Set(seen.map((r) => r.clientRequestId)).size, 4);
  assert.ok(seen.filter((r) => r.stage === "band").every((r) => r.timeBudgetMs === 1500));
});

test("48 default cap and 256 hard ceiling fail before any send; explicit 256 accepted", async () => {
  let sends = 0; const send = async (r: ResearchRequest) => { sends++; return good(r); };
  await assert.rejects(runBatch(Array(49).fill(condition), { ...opts(), send }), /48/);
  await assert.rejects(runBatch([condition], { ...opts(), send, maxRequests: 257 }), /256/);
  assert.equal(sends, 0);
  await runBatch(Array(256).fill(condition), { ...opts(), send, maxRequests: 256 });
  assert.equal(sends, 512);
  for (const n of [0, -1, 1.5, NaN]) await assert.rejects(runBatch([condition], { ...opts(), send, maxRequests: n }));
});

test("estimate and cancellation instruction precede the first request", async () => {
  const logs: string[] = [];
  await runBatch([condition, condition], { ...opts(), log: (s) => logs.push(s), send: async (r) => {
    assert.match(logs[0], /2 conditions.*23\.0 s.*Ctrl\+C/); return good(r);
  } });
});

test("queue and reply timeout retry once; run and adhoc are final", async () => {
  for (const timeoutKind of ["queue", "reply", "run", "adhoc"] as const) {
    let count = 0;
    const task = runBatch([condition], { ...opts(), send: async (r) => {
      count++; return count === 1 ? { kind: "timeout", timeoutKind, channel: null } : good(r);
    } });
    if (timeoutKind === "queue" || timeoutKind === "reply") { await task; assert.equal(count, 3); }
    else { await assert.rejects(task, /timeout/); assert.equal(count, 1); }
  }
  let count = 0;
  await assert.rejects(runBatch([condition], { ...opts(), send: async () => { count++; return { kind: "timeout", timeoutKind: "queue", channel: null }; } }));
  assert.equal(count, 2);
});

test("cache change enables one null-budget fallback; persistent stalls never enable it", async () => {
  const budgets: Array<number | null | undefined> = [];
  await runBatch([condition], { ...opts(), send: async (r) => {
    if (r.stage === "nominal") return good(r);
    budgets.push(r.timeBudgetMs);
    return { kind: "run", response: budgets.length === 1 ? chunkResponse(r.clientRequestId, 8, "new-cache") : finalResponse(r.clientRequestId, "new-cache") };
  } });
  assert.deepEqual(budgets, [1500, null]);
  let calls = 0;
  await assert.rejects(runBatch([condition], { ...opts(), send: async (r) => {
    calls++; if (r.stage === "nominal") return good(r);
    assert.equal(r.timeBudgetMs, 1500);
    return { kind: "run", response: chunkResponse(r.clientRequestId, 7) };
  } }), /progress/);
  assert.equal(calls, 2);
});

test("ad-hoc nominal uses one null-budget band and never retries or loops that fallback", async () => {
  for (const final of ["complete", "pending", "timeout"] as const) {
    let nulls = 0;
    const task = runBatch([condition], { ...opts(), send: async (r) => {
      if (r.stage === "nominal") {
        const response = nominalResponse(r.clientRequestId); response.channel = "ad_hoc_fallback";
        return { kind: "run", response };
      }
      assert.equal(r.timeBudgetMs, null); nulls++;
      if (final === "timeout") return { kind: "timeout", timeoutKind: "reply", channel: "ad_hoc_fallback" };
      return { kind: "run", response: final === "complete" ? finalResponse(r.clientRequestId) : chunkResponse(r.clientRequestId, 8) };
    } });
    if (final === "complete") await task;
    else await assert.rejects(task);
    assert.equal(nulls, 1);
  }
});

test("cancel stops sends and writes; failure stops the batch instead of returning a partial relay", async () => {
  const controller = new AbortController(); let count = 0;
  await assert.rejects(runBatch([condition, condition], { ...opts(), signal: controller.signal, send: async (r) => {
    count++; controller.abort(); return good(r);
  }, write: async () => assert.fail("cancelled result written") }), /cancel/i);
  assert.equal(count, 1);
  count = 0;
  await assert.rejects(runBatch([condition, condition], { ...opts(), send: async () => { count++; return { kind: "superseded" }; } }), /superseded/);
  assert.equal(count, 1);
});

test("relay bytes and full response pass through unchanged; oversize or missing relay is refused", async () => {
  const relayCondition = { ...condition, relay: { kind: "blind-freeze-v2", previewSha256: "a".repeat(64), conditionOrdinal: 0 } };
  const relay = { kind: "blind-freeze-v2", subsetJson: '{"value":1.000}', subsetSha256: "b".repeat(64) };
  let written: unknown;
  await runBatch([relayCondition], { ...opts(), send: async (r) => {
    const out = good(r); if (out.kind === "run" && r.stage === "band") out.response.relay = relay;
    return out;
  }, write: async (_i, r) => { written = r; } });
  assert.deepEqual((written as { relay: unknown }).relay, relay);
  await assert.rejects(runBatch([relayCondition], { ...opts(), send: async (r) => good(r) }), /relay/);
  for (const length of [16000, 16001]) {
    const task = runBatch([relayCondition], { ...opts(), send: async (r) => {
      const out = good(r);
      if (out.kind === "run" && r.stage === "band") out.response.relay = { ...relay, subsetJson: "x".repeat(length) };
      return out;
    } });
    if (length === 16000) await task;
    else await assert.rejects(task, /16000/);
  }
  await assert.rejects(runBatch([{ ...relayCondition, researchOptions: { marangoni: {}, surfaceBalance: {}, ranges: { marangoni: {}, surfaceBalance: {} } } }], { ...opts(), send: async () => assert.fail("invalid input sent") }));
});

test("rejects mismatched request ids, stages and keys before writing", async () => {
  for (const mutate of [
    (r: ReturnType<typeof finalResponse>) => { r.clientRequestId = "wrong"; },
    (r: ReturnType<typeof finalResponse>) => { r.stage = "nominal"; },
    (r: ReturnType<typeof finalResponse>) => { r.requestKey = "wrong"; },
  ]) await assert.rejects(runBatch([condition], { ...opts(), send: async (req) => {
    if (req.stage === "nominal") return good(req);
    const r = finalResponse(req.clientRequestId); mutate(r); return { kind: "run", response: r };
  }, write: async () => assert.fail("mismatched result written") }));
});

test("CLI parses max-requests and rejects invalid run ids and unknown flags", () => {
  assert.equal(parseArgs(["--input", "inputs.json", "--output-dir", "out", "--max-requests", "256"]).maxRequests, 256);
  assert.throws(() => parseArgs(["--max-requests", "257"]), /256/);
  assert.throws(() => parseArgs(["--run-id", "p8-research:melt-pool"]), /runId/);
  assert.throws(() => parseArgs(["--oops", "x"]));
});

test("CLI sends to the local route and saves the full response and opaque relay bytes", async () => {
  const dir = await mkdtemp(path.join(tmpdir(), "p8-batch-test-"));
  const seen: ResearchRequest[] = [];
  const subsetJson = '{"value":1.000}';
  const server = createServer(async (req, res) => {
    assert.equal(req.url, "/api/python/lpbf-research-models");
    assert.equal(req.method, "POST");
    assert.equal(req.headers.authorization, "Bearer synthetic-test-token");
    let raw = ""; for await (const part of req) raw += part;
    const r = JSON.parse(raw) as ResearchRequest; seen.push(r);
    const outcome = good(r);
    assert.equal(outcome.kind, "run");
    if (outcome.kind !== "run") throw new Error("test response shape");
    if (r.stage === "band") outcome.response.relay = { kind: "blind-freeze-v2", subsetJson, subsetSha256: "b".repeat(64) };
    res.setHeader("Content-Type", "application/json"); res.end(JSON.stringify(outcome.response));
  });
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  try {
    const address = server.address(); assert.ok(address && typeof address !== "string");
    const input = path.join(dir, "input.json"), output = path.join(dir, "output");
    await writeFile(input, JSON.stringify([{ ...condition, relay: { kind: "blind-freeze-v2", previewSha256: "a".repeat(64), conditionOrdinal: 0 } }]));
    const child = spawn(process.execPath, ["--import", "tsx", "scripts/research-route-batch.ts", "--input", input, "--output-dir", output, "--run-id", "cli12345", "--url", `http://127.0.0.1:${address.port}`], {
      cwd: process.cwd(), env: { ...process.env, METALLIKSA_TOKEN: "synthetic-test-token" }, stdio: ["ignore", "pipe", "pipe"],
    });
    let stdout = "", stderr = "";
    child.stdout.on("data", (s) => stdout += s); child.stderr.on("data", (s) => stderr += s);
    const code = await new Promise<number | null>((resolve, reject) => { child.on("error", reject); child.on("exit", resolve); });
    assert.equal(code, 0, stderr); assert.match(stdout, /estimated 11\.5 s/); assert.match(stdout, /Batch complete: 1/);
    assert.deepEqual(seen.map((r) => r.stage), ["nominal", "band"]);
    assert.ok(seen.every((r) => r.sender === "batch-client" && r.supersedeKey === "p8-research:batch:cli12345"));
    const files = await readdir(output); assert.deepEqual(files, ["cli12345-000.json"]);
    const stored = JSON.parse(await readFile(path.join(output, files[0]), "utf8"));
    assert.equal(stored.relay.subsetJson, subsetJson);
    assert.deepEqual(stored.researchModels, finalResponse("x").researchModels);
  } finally {
    await new Promise<void>((resolve, reject) => server.close((e) => e ? reject(e) : resolve()));
    await rm(dir, { recursive: true, force: true });
  }
});
