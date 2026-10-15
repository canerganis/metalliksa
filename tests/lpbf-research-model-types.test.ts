import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import {
  classifyResearchAnswer,
  isResearchBlock,
  isResearchDescribeResponse,
  isResearchRunResponse,
} from "../src/types/lpbfResearchModels";
import { pythonComputationService } from "../src/services/pythonComputationService";
import { completeResponse, describeResponse, nominalResponse } from "./support/researchPanelFixtures";

// Phase D: the closed response types and their guards (contract 3.5, 9.3, 13.9), and the transport classification of
// every server answer (3.5 outcomes table). The fixtures are pruned real Python output.

const root = path.resolve(import.meta.dirname, "..");

test("guards accept the real describe, nominal and complete band responses", () => {
  assert.equal(isResearchDescribeResponse(describeResponse("melt-pool:1")), true);
  assert.equal(isResearchRunResponse(nominalResponse("melt-pool:2")), true);
  assert.equal(isResearchRunResponse(completeResponse("melt-pool:3")), true);
  assert.equal(classifyResearchAnswer(200, describeResponse("melt-pool:1")).kind, "describe");
  assert.equal(classifyResearchAnswer(200, completeResponse("melt-pool:3")).kind, "run");
});

test("guards refuse a response that would crash or mislead the panel", () => {
  const bad = (mutate: (r: any) => void, make: () => any = () => completeResponse("x:1")) => {
    const r = make();
    mutate(r);
    return classifyResearchAnswer(200, r).kind;
  };
  assert.equal(bad((r) => { r.schemaVersion = "p8-research-response-v2"; }), "malformed");
  assert.equal(bad((r) => { r.researchModels.keyholeCavity.fields.alloy.unit = 3; }), "malformed");
  assert.equal(bad((r) => { r.researchModels.keyholeCavity.status = "great"; }), "malformed");
  assert.equal(bad((r) => { r.researchModels.invented = r.researchModels.keyholeCavity; }), "malformed");
  assert.equal(bad((r) => { delete r.researchModels.marangoni.servedDifferences; }), "malformed");
  assert.equal(bad((r) => { r.researchModels.keyholeCavity.band.completeness = "mostly"; }), "malformed");
  assert.equal(bad((r) => { r.identity.servedImplementationFingerprint = "short"; }), "malformed");
  assert.equal(bad((r) => { r.researchModels = null; }), "malformed", "a complete band must carry its block");
  assert.equal(bad((r) => { r.labels.x = 5; }), "malformed");
  assert.equal(bad((r) => { r.controls[0].valueType = "date"; }, () => describeResponse("x:1")), "malformed");
  assert.equal(bad((r) => { delete r.sentences; }, () => describeResponse("x:1")), "malformed");
  assert.equal(isResearchBlock(completeResponse("x:1").researchModels), true);
});

test("an incomplete band response may carry no block, a nominal one may not", () => {
  const chunk: any = completeResponse("x:1");
  chunk.researchModels = null;
  chunk.progress = { armsDone: 10, armsTotal: 79, complete: false };
  assert.equal(classifyResearchAnswer(200, chunk).kind, "run");
  const nominal: any = nominalResponse("x:2");
  nominal.researchModels = null;
  assert.equal(classifyResearchAnswer(200, nominal).kind, "malformed");
});

test("transport outcomes: refusal, failure envelope, timeouts, superseded, server errors", () => {
  const problem = { pointer: "/process/material", rule: "wrong-type", limit: null, value: "1", message: "Material must be a string." };
  assert.deepEqual(
    classifyResearchAnswer(422, { success: false, errorKind: "research-request", reasonCode: "RESEARCH_REQUEST_INVALID", problems: [problem] }),
    { kind: "refused", reasonCode: "RESEARCH_REQUEST_INVALID", problems: [problem], httpStatus: 422, recycleWorker: false },
  );
  const stale = classifyResearchAnswer(422, { success: false, reasonCode: "RESEARCH_CODE_STALE", recycleWorker: true, problems: [] });
  assert.equal(stale.kind === "refused" && stale.recycleWorker, true);
  assert.equal(classifyResearchAnswer(413, { success: false, reasonCode: "RESEARCH_REQUEST_INVALID", problems: [] }).kind, "refused");
  assert.deepEqual(
    classifyResearchAnswer(200, { success: false, errorKind: "research", reasonCode: "RESEARCH_EVALUATION_FAILED" }),
    { kind: "failed", reasonCode: "RESEARCH_EVALUATION_FAILED", httpStatus: 200 },
  );
  for (const timeoutKind of ["queue", "run", "reply", "adhoc"] as const) {
    assert.deepEqual(
      classifyResearchAnswer(504, { success: false, reasonCode: "RESEARCH_TIMEOUT", timeoutKind, channel: "persistent" }),
      { kind: "timeout", timeoutKind, channel: "persistent" },
    );
  }
  assert.equal(classifyResearchAnswer(504, { success: false, reasonCode: "RESEARCH_TIMEOUT", timeoutKind: "weird" }).kind, "timeout");
  assert.deepEqual(classifyResearchAnswer(200, { success: false, status: "superseded" }), { kind: "superseded" });
  assert.deepEqual(classifyResearchAnswer(500, { error: "boom" }), { kind: "http-error", httpStatus: 500, message: "boom" });
  assert.deepEqual(classifyResearchAnswer(502, undefined), { kind: "http-error", httpStatus: 502, message: "HTTP 502" });
  assert.equal(classifyResearchAnswer(200, { hello: 1 }).kind, "malformed");
});

test("service: sends the request body as given, classifies the answer, rethrows only an abort", async () => {
  const realFetch = globalThis.fetch;
  const seen: Array<{ url: string; init: RequestInit }> = [];
  try {
    globalThis.fetch = (async (url: string, init: RequestInit) => {
      seen.push({ url, init });
      return new Response(JSON.stringify(describeResponse("melt-pool:9")), { status: 200, headers: { "Content-Type": "application/json" } });
    }) as typeof fetch;
    const request: any = {
      schemaVersion: "p8-research-request-v1", supersedeKey: "p8-research:melt-pool", clientRequestId: "melt-pool:9", stage: "describe",
      process: { material: "Ti-6Al-4V" }, propertyContext: { kind: "nominal" }, sender: "research-panel",
    };
    const outcome = await pythonComputationService.solveLpbfResearchModels(request);
    assert.equal(outcome.kind, "describe");
    assert.equal(seen[0].url, "/api/python/lpbf-research-models");
    assert.equal(seen[0].init.method, "POST");
    assert.equal(seen[0].init.body, JSON.stringify(request));

    globalThis.fetch = (async () => { throw new TypeError("fetch failed"); }) as typeof fetch;
    const net = await pythonComputationService.solveLpbfResearchModels(request);
    assert.deepEqual(net, { kind: "http-error", httpStatus: 0, message: "fetch failed" });

    globalThis.fetch = (async () => { throw Object.assign(new Error("aborted"), { name: "AbortError" }); }) as typeof fetch;
    await assert.rejects(() => pythonComputationService.solveLpbfResearchModels(request), (e: Error) => e.name === "AbortError");

    globalThis.fetch = (async () => new Response("<html>", { status: 200 })) as typeof fetch;
    assert.equal((await pythonComputationService.solveLpbfResearchModels(request)).kind, "malformed");
  } finally {
    globalThis.fetch = realFetch;
  }
});

test("service passes relay.subsetJson through as a string, never parsed and re-serialized", () => {
  const subsetJson = '{"b":1,"a":[1.0,2.50,3e0]}';
  const response: any = completeResponse("batch:1");
  response.relay = { kind: "blind-freeze-v2", subsetJson, subsetSha256: "0".repeat(64) };
  const outcome = classifyResearchAnswer(200, response);
  assert.equal(outcome.kind, "run");
  assert.equal(outcome.kind === "run" ? outcome.response.relay?.subsetJson : null, subsetJson);
  // the type and the guard keep it a string: nothing in the client reads its content
  const source = readFileSync(path.join(root, "src/types/lpbfResearchModels.ts"), "utf8");
  assert.equal(/JSON\.parse\([^)]*subsetJson/.test(source), false);
});

test("the research route literal appears only in the service, the route, the generated registry and tests", () => {
  const literal = "api/python/lpbf-research-models";
  const allowed = new Set([
    "src/services/pythonComputationService.ts",
    "scripts/research-route-batch.ts",
    "routes/physics.ts",
    "src/generated/moduleRegistry.ts",
    "src/generated/moduleRegistry.json",
  ]);
  const hits: string[] = [];
  const walk = (dir: string) => {
    for (const name of readdirSync(dir)) {
      if (["node_modules", ".git", "dist", ".runtime", "graft", ".claude", ".orchestra"].includes(name)) continue;
      const full = path.join(dir, name);
      const info = statSync(full);
      if (info.isDirectory()) { walk(full); continue; }
      if (!/\.(ts|tsx|js|cjs|mjs|json)$/.test(name)) continue;
      if (info.size > 2_000_000) continue;
      const rel = path.relative(root, full).split(path.sep).join("/");
      if (readFileSync(full, "utf8").includes(literal)) hits.push(rel);
    }
  };
  for (const dir of ["src", "server", "routes", "scripts"]) walk(path.join(root, dir));
  for (const hit of hits) assert.ok(allowed.has(hit), `unexpected sender of the research route: ${hit}`);
  assert.ok(hits.includes("src/services/pythonComputationService.ts"));
});
