import test, { afterEach, beforeEach } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import {
  BAND_BUDGET_MS,
  DESCRIBE_DEBOUNCE_MS,
  isResearchRunnable,
  useLpbfResearchModelStore,
} from "../src/store/useLpbfResearchModelStore";
import { peekLpbfBuildJobKey, useLpbfBuildJobStore } from "../src/store/useLpbfBuildJobStore";
import { buildResearchOptions, emptyAlloyOptions, researchAlloyKey } from "../src/utils/lpbfResearchPanelModel";
import {
  FakeResearchEngine,
  TI64_INPUT,
  asOutcome,
  chunkResponse,
  completeResponse,
  deferred,
  describeResponse,
  finalResponse,
  nominalResponse,
  tick,
  until,
} from "./support/researchPanelFixtures";
import type { ResearchOutcome } from "../src/types/lpbfResearchModels";

// R-UI state machine of the Research model panel (contract 4.3 to 4.5, 13.9, 16.2): describe before Run, the
// generation counter, progressive band chunks, Cancel, stale on input change, identity checks on responses, per-alloy
// options, the bounded client result map, and that the Build Job store and its exports are never touched.

const store = () => useLpbfResearchModelStore.getState();
const host = (id: "melt-pool" | "build-job" = "melt-pool") => store().hosts[id];
let engine: FakeResearchEngine;

/** A fake engine that answers describe at once, nominal at once and the band in three chunks. */
function standardEngine(): FakeResearchEngine {
  let chunk = 0;
  return new FakeResearchEngine()
    .on("describe", (r) => asOutcome(describeResponse(r.clientRequestId)))
    .on("nominal", (r) => { chunk = 0; return asOutcome(nominalResponse(r.clientRequestId)); })
    .on("band", (r) => {
      chunk += 1;
      if (chunk === 1) return asOutcome(chunkResponse(r.clientRequestId, 20));
      if (chunk === 2) return asOutcome(chunkResponse(r.clientRequestId, 50));
      return asOutcome(finalResponse(r.clientRequestId));
    });
}

async function mount(id: "melt-pool" | "build-job" = "melt-pool", input = TI64_INPUT) {
  store().syncHost(id, input);
  await until(() => isResearchRunnable(host(id)), "describe ready");
}

beforeEach(() => {
  store().reset();
  engine = standardEngine();
});
afterEach(() => {
  engine.restore();
  store().reset();
});

test("Run stays disabled until the describe answer for the current inputs arrives", async () => {
  const gate = deferred<ResearchOutcome>();
  engine.on("describe", () => gate.promise);
  store().syncHost("melt-pool", TI64_INPUT);
  assert.equal(host().describe.status, "checking");
  assert.equal(isResearchRunnable(host()), false);
  await store().run("melt-pool");
  assert.equal(engine.byStage("nominal").length, 0, "no nominal request without a describe answer");
  gate.resolve(asOutcome(describeResponse(engine.requests[0].clientRequestId)));
  await until(() => isResearchRunnable(host()), "describe ready");
  assert.equal(engine.byStage("describe").length, 1);
});

test("a describe answer with option problems keeps Run disabled and carries the messages", async () => {
  engine.on("describe", (r) => asOutcome(describeResponse(r.clientRequestId, {
    problems: [{ pointer: "/researchOptions/marangoni/length_m", rule: "below-min", limit: 1e-6, value: "0", message: "Research length m must be between 1e-6 and 0.01 m; got 0." }],
  })));
  store().syncHost("melt-pool", TI64_INPUT);
  await until(() => host().describe.status === "ready", "describe ready");
  assert.equal(isResearchRunnable(host()), false);
  assert.match(host().describe.response!.problems[0].message, /between/);
});

test("describe and run requests carry the panel sender, its own supersede key and the per-host options", async () => {
  await mount();
  await store().run("melt-pool");
  for (const r of engine.requests) {
    assert.equal(r.sender, "research-panel");
    assert.equal(r.supersedeKey, "p8-research:melt-pool");
    assert.match(r.clientRequestId, /^melt-pool:\d+$/);
    assert.equal(r.process.laserWavelength, "IR_1064nm");
    assert.deepEqual(r.propertyContext, { kind: "nominal" });
    assert.equal(r.relay, undefined);
  }
  await mount("build-job", { ...TI64_INPUT, propertyContext: { kind: "build-job-snapshot", alloyId: "ti6al4v", materialPropertySha256: "a".repeat(64) } });
  assert.equal(engine.byStage("describe").at(-1)!.supersedeKey, "p8-research:build-job");
});

test("nominal, then band chunks with the 1500 ms budget until complete, one request key throughout", async () => {
  await mount();
  const seen: string[] = [];
  const unsubscribe = useLpbfResearchModelStore.subscribe((s) => { seen.push(s.hosts["melt-pool"].run.status); });
  await store().run("melt-pool");
  unsubscribe();
  const run = host().run;
  assert.equal(run.status, "complete");
  assert.deepEqual(engine.byStage("band").map((r) => r.timeBudgetMs), [BAND_BUDGET_MS, BAND_BUDGET_MS, BAND_BUDGET_MS]);
  assert.equal(run.requestKey, run.nominal!.requestKey);
  assert.equal(run.result!.requestKey, run.nominal!.requestKey);
  assert.ok(seen.includes("running-nominal") && seen.includes("band-pending"));
  assert.deepEqual(run.progress, { armsDone: 79, armsTotal: 79 });
  assert.ok(run.result!.researchModels, "complete block");
  assert.equal(engine.byStage("nominal").length, 1);
  assert.ok(engine.byStage("band").every((r) => r.researchOptions !== undefined));
});

test("Cancel stops the loop at once, keeps the nominal values and sends nothing to the server", async () => {
  await mount();
  const hold = deferred<ResearchOutcome>();
  let bandCalls = 0;
  engine.on("band", (r) => { bandCalls += 1; return bandCalls === 1 ? asOutcome(chunkResponse(r.clientRequestId, 20)) : hold.promise; });
  const running = store().run("melt-pool");
  await until(() => bandCalls === 2, "second chunk in flight");
  const requestsBefore = engine.requests.length;
  store().cancel("melt-pool");
  assert.equal(host().run.status, "cancelled");
  assert.ok(host().run.nominal, "nominal values stay");
  hold.resolve(asOutcome(finalResponse(engine.requests.at(-1)!.clientRequestId)));
  await running;
  await tick(20);
  assert.equal(host().run.status, "cancelled", "a late answer never revives a cancelled run");
  assert.equal(host().run.result, null);
  assert.equal(engine.requests.length, requestsBefore, "no request after Cancel");
  // the next Run starts a new generation and completes
  engine.on("band", (r) => asOutcome(finalResponse(r.clientRequestId)));
  await store().run("melt-pool");
  assert.equal(host().run.status, "complete");
});

test("a change of a run-identity input hides every research value at once and a late answer is dropped", async () => {
  await mount();
  const hold = deferred<ResearchOutcome>();
  engine.on("band", () => hold.promise);
  const running = store().run("melt-pool");
  await until(() => host().run.status === "band-pending", "band pending");
  store().syncHost("melt-pool", { ...TI64_INPUT, laserPower_W: 250 });
  assert.equal(host().run.status, "stale");
  assert.notEqual(host().run.identity, host().identity, "the run identity is not the current one");
  hold.resolve(asOutcome(finalResponse(engine.requests.at(-1)!.clientRequestId)));
  await running;
  assert.equal(host().run.status, "stale");
  assert.equal(host().run.result, null, "the old result is never applied beside the new inputs");
  assert.equal(isResearchRunnable(host()), false, "Run waits for the describe of the new inputs");
  engine.on("band", (r) => asOutcome(finalResponse(r.clientRequestId)));
  await until(() => isResearchRunnable(host()), "describe of new inputs", 1500);
  assert.equal(engine.byStage("describe").at(-1)!.process.laserPower_W, 250);
});

test("typing sends a debounced describe only, never a nominal or band request", async () => {
  await mount();
  const before = engine.requests.length;
  for (const p of [210, 220, 230, 240]) store().syncHost("melt-pool", { ...TI64_INPUT, laserPower_W: p });
  assert.equal(engine.requests.length, before, "nothing is sent before the debounce");
  await until(() => engine.byStage("describe").length === 2, "debounced describe", DESCRIBE_DEBOUNCE_MS * 4);
  assert.equal(engine.byStage("describe").at(-1)!.process.laserPower_W, 240);
  assert.equal(engine.byStage("nominal").length + engine.byStage("band").length, 0);
});

test("an option edit makes a finished result stale and a revert shows it again without a rerun", async () => {
  await mount();
  await store().run("melt-pool");
  assert.equal(host().run.status, "complete");
  store().setOption("ti6al4v", "marangoni", "deltaTemperature_K", 700);
  assert.equal(host().run.status, "stale");
  store().resetControl("ti6al4v", "marangoni", "deltaTemperature_K");
  assert.equal(host().run.status, "complete", "same identity as the finished result");
  assert.equal(engine.byStage("nominal").length, 1, "no new nominal request for a revert");
});

test("a response whose request id is not the one sent is not applied", async () => {
  await mount();
  engine.on("nominal", () => asOutcome(nominalResponse("melt-pool:999")));
  await store().run("melt-pool");
  assert.equal(host().run.status, "error");
  assert.equal(host().run.nominal, null);
  assert.equal(engine.byStage("band").length, 0);
});

test("a band response for another request key is not applied", async () => {
  await mount();
  engine.on("band", (r) => {
    const other = chunkResponse(r.clientRequestId, 20);
    other.requestKey = "f".repeat(64);
    return asOutcome(other);
  });
  await store().run("melt-pool");
  assert.equal(host().run.status, "error");
  assert.equal(host().run.result, null);
});

test("a changed cache instance triggers one null-budget band request, never an endless loop", async () => {
  await mount();
  let n = 0;
  engine.on("band", (r) => {
    n += 1;
    return asOutcome(n === 1 ? chunkResponse(r.clientRequestId, 20, "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb") : finalResponse(r.clientRequestId, "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"));
  });
  await store().run("melt-pool");
  assert.equal(host().run.status, "complete");
  assert.deepEqual(engine.byStage("band").map((r) => r.timeBudgetMs), [BAND_BUDGET_MS, null]);

  engine.requests.length = 0;
  store().setOption("ti6al4v", "marangoni", "deltaTemperature_K", 800);
  await until(() => isResearchRunnable(host()), "describe ready", 1500);
  engine.on("band", (r) => asOutcome(chunkResponse(r.clientRequestId, 20, "cccccccccccccccccccccccccccccccc")));
  await store().run("melt-pool");
  assert.equal(host().run.status, "error", "a null-budget request that is still incomplete ends the run");
  assert.equal(engine.byStage("band").filter((r) => r.timeBudgetMs === null).length, 1);
});

test("no progress in a chunk also triggers the single null-budget request", async () => {
  await mount();
  let n = 0;
  engine.on("band", (r) => { n += 1; return asOutcome(n === 1 ? chunkResponse(r.clientRequestId, 7) : finalResponse(r.clientRequestId)); });
  await store().run("melt-pool");
  assert.equal(host().run.status, "complete");
  assert.deepEqual(engine.byStage("band").map((r) => r.timeBudgetMs), [BAND_BUDGET_MS, null]);
});

test("the ad-hoc channel sends the band as one null-budget request and Cancel discards its result", async () => {
  await mount();
  engine.on("nominal", (r) => { const n = nominalResponse(r.clientRequestId); n.channel = "ad_hoc_fallback"; return asOutcome(n); });
  const hold = deferred<ResearchOutcome>();
  engine.on("band", () => hold.promise);
  const running = store().run("melt-pool");
  await until(() => engine.byStage("band").length === 1, "band request");
  assert.equal(engine.byStage("band")[0].timeBudgetMs, null);
  store().cancel("melt-pool");
  hold.resolve(asOutcome(finalResponse(engine.requests.at(-1)!.clientRequestId)));
  await running;
  assert.equal(host().run.status, "cancelled");
  assert.equal(host().run.result, null);
});

test("RESEARCH_CODE_STALE is retried once on the recycled lane", async () => {
  await mount();
  let n = 0;
  engine.on("nominal", (r) => {
    n += 1;
    return n === 1
      ? { kind: "refused", reasonCode: "RESEARCH_CODE_STALE", problems: [], httpStatus: 422, recycleWorker: true } as ResearchOutcome
      : asOutcome(nominalResponse(r.clientRequestId));
  });
  await store().run("melt-pool");
  assert.equal(engine.byStage("nominal").length, 2);
  assert.notEqual(engine.byStage("nominal")[0].clientRequestId, engine.byStage("nominal")[1].clientRequestId);
  assert.equal(host().run.status, "complete");

  store().reset();
  engine.restore();
  engine = standardEngine().on("nominal", () => ({ kind: "refused", reasonCode: "RESEARCH_CODE_STALE", problems: [], httpStatus: 422, recycleWorker: true }));
  await mount();
  await store().run("melt-pool");
  assert.equal(engine.byStage("nominal").length, 2, "one retry only");
  assert.equal(host().run.status, "error");
});

test("errors are panel-local and carry the registry code; Retry runs again", async () => {
  await mount();
  engine.on("nominal", () => ({ kind: "timeout", timeoutKind: "run", channel: "persistent" }));
  await store().run("melt-pool");
  assert.equal(host().run.status, "error");
  assert.equal(host().run.error!.reasonCode, "RESEARCH_TIMEOUT");
  assert.equal(host().run.error!.timeoutKind, "run");
  engine.on("nominal", (r) => asOutcome(nominalResponse(r.clientRequestId)));
  store().retry("melt-pool");
  await until(() => host().run.status === "complete", "retry complete");
});

test("a superseded describe is ignored and leaves the host checking", async () => {
  engine.on("describe", () => ({ kind: "superseded" }));
  store().syncHost("melt-pool", TI64_INPUT);
  await tick(30);
  assert.equal(host().describe.status, "checking");
  assert.equal(isResearchRunnable(host()), false);
});

test("options are kept per alloy and never reach a host showing another alloy", async () => {
  await mount("melt-pool", TI64_INPUT);
  await mount("build-job", { ...TI64_INPUT, material: "AlSi10Mg", propertyContext: { kind: "build-job-snapshot", alloyId: "alsi10mg", materialPropertySha256: "b".repeat(64) } });
  assert.equal(researchAlloyKey("Ti-6Al-4V"), "ti6al4v");
  assert.equal(researchAlloyKey("AlSi10Mg"), "alsi10mg");
  const tiBefore = host("melt-pool").identity;
  store().setVapourPreset("alsi10mg", "pure-al-proxy");
  assert.equal(host("melt-pool").identity, tiBefore, "the Ti-6Al-4V host identity is unchanged");
  assert.equal(store().optionsByAlloy.ti6al4v, undefined);
  assert.equal(store().optionsByAlloy.alsi10mg.surfaceBalance.vapourPreset, "pure-al-proxy");
  await until(() => engine.byStage("describe").some((r) => r.process.material === "AlSi10Mg" && r.researchOptions?.surfaceBalance.vapourPreset === "pure-al-proxy"), "Al describe with preset");
  assert.ok(engine.byStage("describe").filter((r) => r.process.material === "Ti-6Al-4V").every((r) => r.researchOptions?.surfaceBalance.vapourPreset === undefined));
  // the same alloy shown by two hosts shares its options
  await mount("build-job", { ...TI64_INPUT, propertyContext: { kind: "build-job-snapshot", alloyId: "ti6al4v", materialPropertySha256: "a".repeat(64) } });
  store().setOption("ti6al4v", "marangoni", "deltaTemperature_K", 650);
  await until(() => engine.byStage("describe").some((r) => r.process.material === "Ti-6Al-4V" && r.supersedeKey === "p8-research:build-job" && r.researchOptions?.marangoni.deltaTemperature_K === 650), "build-job describe with option");
});

test("a preset change clears that module's vapour overrides and ranges", () => {
  store().setVapourPreset("ti6al4v", "custom");
  store().setOption("ti6al4v", "surfaceBalance", "vapourTemperature_K", 3000);
  store().setRange("ti6al4v", "surfaceBalance", "vapourLatentHeat_J_kg", { min: 8e6, max: 1e7 });
  store().setOption("ti6al4v", "surfaceBalance", "emissivity", 0.4);
  store().setVapourPreset("ti6al4v", "gan-ti64");
  const o = store().optionsByAlloy.ti6al4v;
  assert.equal(o.surfaceBalance.vapourTemperature_K, undefined);
  assert.equal(o.ranges.surfaceBalance.vapourLatentHeat_J_kg, undefined);
  assert.equal(o.surfaceBalance.emissivity, 0.4, "unrelated options stay");
  assert.equal(store().presetCleared.ti6al4v, true);
});

test("Belton modes drop the direct slope and its range from the request and keep the saved value", () => {
  const o = emptyAlloyOptions();
  o.marangoni.surfaceTensionSlope_N_mK = -0.0004;
  o.ranges.marangoni.surfaceTensionSlope_N_mK = { min: -0.0006, max: -0.0002 };
  o.marangoni.slopeMode = "fe-s-belton";
  o.marangoni.solubleSulfur_ppm = 20;
  const belton = buildResearchOptions(o);
  assert.equal("surfaceTensionSlope_N_mK" in belton.marangoni, false);
  assert.equal("surfaceTensionSlope_N_mK" in belton.ranges.marangoni, false);
  assert.equal(belton.marangoni.solubleSulfur_ppm, 20);
  assert.equal(o.marangoni.surfaceTensionSlope_N_mK, -0.0004, "the stored direct value is untouched");
  o.marangoni.slopeMode = "direct";
  assert.equal(buildResearchOptions(o).marangoni.surfaceTensionSlope_N_mK, -0.0004, "back in direct mode it is restored");
});

test("finished results are kept (8 at most) so another host with the same inputs shows one without a rerun", async () => {
  await mount("melt-pool");
  await store().run("melt-pool");
  assert.equal(host().run.status, "complete");
  store().unmountHost("melt-pool");
  engine.requests.length = 0;
  store().syncHost("melt-pool", TI64_INPUT);
  assert.equal(host().run.status, "complete", "shown from the client map at once");
  assert.equal(engine.byStage("nominal").length + engine.byStage("band").length, 0);
  for (let i = 0; i < 10; i += 1) {
    store().setOption("ti6al4v", "marangoni", "deltaTemperature_K", 300 + i);
    await until(() => isResearchRunnable(host()), "describe ready", 1500);
    await store().run("melt-pool");
  }
  assert.ok(store().finished.length <= 8);
});

test("unmount cancels a running request", async () => {
  await mount();
  const hold = deferred<ResearchOutcome>();
  engine.on("band", () => hold.promise);
  const running = store().run("melt-pool");
  await until(() => host().run.status === "band-pending", "band pending");
  store().unmountHost("melt-pool");
  assert.equal(host().run.status, "cancelled");
  hold.resolve(asOutcome(finalResponse(engine.requests.at(-1)!.clientRequestId)));
  await running;
  assert.equal(host().run.result, null);
});

test("relay traffic of another sender never changes the panel state (a blind-freeze request has its own supersede key)", async () => {
  await mount();
  const before = JSON.stringify(host());
  // a blind-tab request goes through the same service with its own sender and key; the panel store is not involved
  const { pythonComputationService } = await import("../src/services/pythonComputationService");
  const outcome = await pythonComputationService.solveLpbfResearchModels({
    schemaVersion: "p8-research-request-v1", supersedeKey: "p8-research:blind:0123456789abcdef", clientRequestId: "blind:1", stage: "describe",
    process: { ...TI64_INPUT, laserWavelength: "IR_1064nm", absorptionModel: "flat-plate" }, propertyContext: { kind: "nominal" }, sender: "blind-freeze",
  });
  assert.equal(outcome.kind, "describe");
  assert.equal(JSON.stringify(host()), before);
  const panelKeys = new Set(engine.requests.filter((r) => r.sender === "research-panel").map((r) => r.supersedeKey));
  assert.deepEqual([...panelKeys], ["p8-research:melt-pool"]);
  assert.equal(engine.requests.at(-1)!.supersedeKey.startsWith("p8-research:blind:"), true);
  // the panel does not apply a response that carries another request id
  assert.equal(host().describe.status, "ready");
});

test("R-UI-10: option edits, runs, failures and cancels leave the Build Job store and its exports unchanged", async () => {
  const snapshot = () => JSON.stringify({
    job: useLpbfBuildJobStore.getState().job,
    lastKey: useLpbfBuildJobStore.getState().lastKey,
    sessionEvidenceKey: useLpbfBuildJobStore.getState().sessionEvidenceKey,
    seq: useLpbfBuildJobStore.getState().seq,
    error: useLpbfBuildJobStore.getState().error,
    busy: useLpbfBuildJobStore.getState().busy,
    key: peekLpbfBuildJobKey(),
  });
  const before = snapshot();
  await mount("build-job", { ...TI64_INPUT, propertyContext: { kind: "build-job-snapshot", alloyId: "ti6al4v", materialPropertySha256: "a".repeat(64) } });
  store().setOption("ti6al4v", "marangoni", "deltaTemperature_K", 900);
  await until(() => isResearchRunnable(host("build-job")), "describe", 1500);
  await store().run("build-job");
  assert.equal(host("build-job").run.status, "complete");
  engine.on("nominal", () => ({ kind: "failed", reasonCode: "RESEARCH_EVALUATION_FAILED", httpStatus: 200 }));
  store().setOption("ti6al4v", "marangoni", "deltaTemperature_K", 910);
  await until(() => isResearchRunnable(host("build-job")), "describe", 1500);
  await store().run("build-job");
  assert.equal(host("build-job").run.status, "error");
  engine.on("nominal", (r) => asOutcome(nominalResponse(r.clientRequestId))).on("band", () => new Promise<ResearchOutcome>(() => {}));
  const running = store().run("build-job");
  await until(() => host("build-job").run.status === "band-pending", "band pending");
  store().cancel("build-job");
  await running;
  assert.equal(snapshot(), before);
});

test("the research store and panel import no Build Job store, export or qualification module", () => {
  const root = path.resolve(import.meta.dirname, "..");
  for (const file of [
    "src/store/useLpbfResearchModelStore.ts",
    "src/components/3d-distortion-lab/ResearchModelPanel.tsx",
    "src/components/3d-distortion-lab/ResearchModuleSection.tsx",
    "src/utils/lpbfResearchPanelModel.ts",
    "src/utils/lpbfResearchWording.ts",
  ]) {
    const source = readFileSync(path.join(root, file), "utf8");
    assert.equal(/useLpbfBuildJobStore|useMaterialSpecimenStore|lpbfBuildJobIdentity|qualification|exportRun|evidenceExport/i.test(source.replace(/\/\*[\s\S]*?\*\/|\/\/.*$/gm, "")), false, file);
  }
});

test("a complete response renders from the store without any evaluation in TypeScript", () => {
  // the nominal leaf in the complete block is the nominal leaf of the nominal response (R-TR-6 on the client)
  const a = nominalResponse("x:1").researchModels!.keyholeCavity!.fields.cavityDepth_um.value;
  const b = completeResponse("x:1").researchModels!.keyholeCavity!.fields.cavityDepth_um.value;
  assert.equal(a, b);
});
