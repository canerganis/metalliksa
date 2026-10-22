import React from "react";
import assert from "node:assert/strict";
import { test } from "node:test";
import { readFileSync } from "node:fs";
import { renderToStaticMarkup } from "react-dom/server";
import { ResultHeader } from "../src/components/3d-distortion-lab/LpbfResultPresentation";
import { useLpbfEngineeringStore, engineeringSignature, resumeEngineeringJob, startEngineeringJobPersistence, LPBF_ENGINEERING_JOB_STORAGE_KEY } from "../src/store/useLpbfEngineeringStore";
import { useMaterialSpecimenStore } from "../src/store/useMaterialSpecimenStore";
import { useLpbfWorkflowStore } from "../src/store/useLpbfWorkflowStore";
import { createLpbfQualificationReport, sharedSimulationInput } from "../src/utils/lpbfQualificationReport";
import { isResultStale, resultSignatureOnPoll, resultSignatureOnRestore, resultSignatureOnSubmit } from "../src/utils/lpbfResultStaleness";
import { simulationApi, type SimulationJob, type SimulationResult } from "../src/services/lpbfSimulationService";

// Synthetic presentation fixture, never a physical validation dataset.
function completedJob(id = "a".repeat(32)): SimulationJob {
  const input = sharedSimulationInput(useMaterialSpecimenStore.getState().activeSpecimen);
  const result: SimulationResult = {
    schemaVersion: 1, requestedMode: "standard", effectiveMode: "standard", solver: { id: "synthetic-staleness-fixture", version: "1", openfoam: null },
    settings: input, confidence: "low", validationStatus: "unvalidated", productionReady: false, label: "Unvalidated thermal simulation",
    fallbackReason: null, metrics: { width_um: 120, depth_um: 45, length_um: 200 }, material: { name: input.material, quality: "estimated", source: "Synthetic UI fixture; not measured evidence" },
    analyticalComparison: {}, assumptions: ["Fixture only"], regime: "screening", mainRisk: "unresolved", recommendation: "Measure", riskScope: "screening only",
  };
  return { id, status: "completed", progress: 1, log: "fixture", error: null, result };
}
const specimen = () => useMaterialSpecimenStore.getState().activeSpecimen;
/** Signature of the current draft: engineeringSignature() is what LpbfEngineeringSimulation (its `signature`) and the qualification report both call. */
const draft = () => engineeringSignature(sharedSimulationInput(specimen()), useLpbfEngineeringStore.getState(), specimen().lpbf.scanStrategy);
const stale = () => {
  const state = useLpbfEngineeringStore.getState();
  return isResultStale(state.resultSignature, draft(), state.job?.status === "completed" && !!state.job.result);
};
const reportMatches = () => createLpbfQualificationReport(specimen(), useLpbfWorkflowStore.getState().context, useLpbfEngineeringStore.getState(), null).resultMatchesCurrentInputs;
const wait = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));
/** Polls until the condition holds (the store polls the worker on a 500 ms timer); fails with `what` after the deadline. */
async function until(condition: () => boolean, what: string, timeoutMs = 10000) {
  const deadline = Date.now() + timeoutMs;
  while (!condition()) {
    if (Date.now() > deadline) assert.fail(`timed out waiting for: ${what}`);
    await wait(25);
  }
}
const snapshot = () => ({ ...useLpbfEngineeringStore.getState() });
/** Every test restores the shared stores it touched (specimen incl. preset/process edits, engineering store, worker api). */
const isolate = async (body: () => Promise<void>) => {
  const engineering = snapshot();
  const specimenState = useMaterialSpecimenStore.getState().activeSpecimen;
  const previousGet = simulationApi.get;
  try { await body(); }
  finally {
    simulationApi.get = previousGet;
    useMaterialSpecimenStore.setState({ activeSpecimen: specimenState });
    useLpbfEngineeringStore.setState(engineering);
  }
};
const editPower = (power: number) => useMaterialSpecimenStore.getState().updateLpbfProcess({ laserPower_W: power });
/** What LpbfEngineeringSimulation.submit() records for a submitted job. */
const submit = (job: SimulationJob) => {
  const signature = draft();
  useLpbfEngineeringStore.setState({ job, submittedSignature: signature, submittedInput: sharedSimulationInput(specimen()), resultSignature: resultSignatureOnSubmit(job.status, signature) });
  return signature;
};

test("the component's draft signature is the shared engineeringSignature (same bytes as the former inline JSON.stringify)", () => {
  const input = sharedSimulationInput(specimen());
  const fields = { settings: { mesh_um: 25 }, mode: "standard" as const, material: "Inconel 718", properties: "p", measurements: "m", width: "1", depth: "2", source: "s", specimen: "sp", uncertainty: "u", holdout: "unknown" };
  assert.equal(engineeringSignature(input, fields, "meander"),
    JSON.stringify([input, fields.settings, fields.mode, fields.material, fields.properties, fields.measurements, fields.width, fields.depth, fields.source, fields.specimen, fields.uncertainty, fields.holdout, "meander"]));
  const source = readFileSync(new URL("../src/components/3d-distortion-lab/LpbfEngineeringSimulation.tsx", import.meta.url), "utf8");
  assert.match(source, /const signature = engineeringSignature\(input,\{settings,mode,material,properties,measurements,width,depth,source,specimen,uncertainty,holdout\},sharedStrategy\);/);
});

test("pure staleness decision", () => {
  assert.equal(isResultStale("s1", "s1"), false);
  assert.equal(isResultStale("s1", "s2"), true);
  assert.equal(isResultStale("", "s1"), true, "no recorded result signature is never fresh");
  assert.equal(isResultStale("s1", "s2", false), false, "nothing to mark when there is no result");
  assert.equal(resultSignatureOnSubmit("completed", "s1"), "s1");
  for (const status of ["queued", "running", "failed", "cancelled", "timed_out", undefined]) {
    assert.equal(resultSignatureOnSubmit(status, "s1"), "");
    assert.equal(resultSignatureOnPoll(status, "s1"), undefined);
    assert.equal(resultSignatureOnRestore(status, "s1"), "");
  }
  assert.equal(resultSignatureOnPoll("completed", "submitted"), "submitted");
  assert.equal(resultSignatureOnRestore("completed", "saved"), "saved");
  assert.equal(resultSignatureOnRestore("completed", undefined), "");
});

test("completion, input edit, edit back, cached completion and edit during execution", () => isolate(async () => {
  {
    useMaterialSpecimenStore.getState().loadPreset("inconel-718");
    editPower(250);
    useLpbfEngineeringStore.setState({ job: undefined, submittedSignature: "", resultSignature: "", submittedInput: undefined, busy: false });
    assert.equal(stale(), false, "no result: nothing is stale");
    assert.equal(reportMatches(), null);

    // Submit, run, complete: bound to the SUBMITTED signature -> fresh.
    const queued: SimulationJob = { ...completedJob(), status: "running", result: undefined, progress: .3 };
    const submitted = submit(queued);
    assert.equal(useLpbfEngineeringStore.getState().resultSignature, "");
    const done = completedJob();
    simulationApi.get = async () => done;
    resumeEngineeringJob();
    await until(() => useLpbfEngineeringStore.getState().job?.status === "completed", "polled completion");
    assert.equal(useLpbfEngineeringStore.getState().resultSignature, submitted);
    assert.equal(stale(), false);
    assert.equal(reportMatches(), true);

    // Edit an input after completion -> stale in both the engineering view decision and the report.
    editPower(300);
    assert.notEqual(draft(), submitted);
    assert.equal(stale(), true);
    assert.equal(reportMatches(), false);
    // Edit back -> fresh again (signature equality, not edit history).
    editPower(250);
    assert.equal(draft(), submitted);
    assert.equal(stale(), false);
    assert.equal(reportMatches(), true);
    // A non-process engineering input (measurement text) also invalidates.
    useLpbfEngineeringStore.setState({ width: "125" });
    assert.equal(stale(), true);
    useLpbfEngineeringStore.setState({ width: "" });
    assert.equal(stale(), false);

    // Cached completion: the submit response is already completed; fresh immediately, stale after an edit.
    useLpbfEngineeringStore.setState({ job: undefined, submittedSignature: "", resultSignature: "" });
    const cachedSignature = submit({ ...completedJob("b".repeat(32)), cacheHit: true });
    assert.equal(useLpbfEngineeringStore.getState().resultSignature, cachedSignature);
    assert.equal(stale(), false);
    editPower(310);
    assert.equal(stale(), true);
    editPower(250);

    // Edit during execution: the running job uses the submitted settings; the finished result is stale for the edited draft.
    useLpbfEngineeringStore.setState({ job: undefined, submittedSignature: "", resultSignature: "" });
    const runningId = "c".repeat(32);
    const submittedDuring = submit({ ...completedJob(runningId), status: "running", result: undefined, progress: .5 });
    editPower(275);
    assert.equal(stale(), false, "no result is shown while running, so nothing to mark");
    simulationApi.get = async () => ({ ...completedJob(runningId), result: { ...completedJob(runningId).result!, settings: { ...completedJob(runningId).result!.settings, power_W: 250 } } });
    resumeEngineeringJob();
    await until(() => useLpbfEngineeringStore.getState().job?.status === "completed", "polled completion of the edited-during-run job");
    assert.equal(useLpbfEngineeringStore.getState().resultSignature, submittedDuring, "bound to the submitted signature, not the edited draft");
    assert.notEqual(draft(), submittedDuring);
    assert.equal(stale(), true);
    assert.equal(reportMatches(), false);
    editPower(250);
    assert.equal(stale(), false, "restoring the submitted inputs makes the result current again");
  }
}));

test("restoration after reload is stale unless the current draft equals the saved executed signature", () => isolate(async () => {
  let stop = () => {};
  try {
    editPower(260);
    const executed = draft();
    const job = completedJob("d".repeat(32));
    const values = new Map([[LPBF_ENGINEERING_JOB_STORAGE_KEY, JSON.stringify({ id: job.id, signature: executed, input: sharedSimulationInput(specimen()) })]]);
    const storage = { getItem: (key: string) => values.get(key) ?? null, setItem: (key: string, value: string) => { values.set(key, value); } };
    // Restored with the same draft: fresh.
    useLpbfEngineeringStore.setState({ job: undefined, busy: false, submittedInput: undefined, submittedSignature: "", resultSignature: "" });
    simulationApi.get = async () => job;
    stop = startEngineeringJobPersistence(storage);
    await until(() => useLpbfEngineeringStore.getState().job?.id === job.id, "restored job");
    assert.equal(useLpbfEngineeringStore.getState().resultSignature, executed);
    assert.equal(stale(), false);
    // Restored while the controls differ: stale.
    editPower(400);
    assert.equal(stale(), true);
    stop();
    // A saved job that is not completed owns no result signature.
    useLpbfEngineeringStore.setState({ job: undefined, busy: false, submittedInput: undefined, submittedSignature: "", resultSignature: "" });
    simulationApi.get = async () => ({ ...job, status: "failed", result: undefined });
    stop = startEngineeringJobPersistence(storage);
    await until(() => useLpbfEngineeringStore.getState().job?.status === "failed", "restored failed job");
    assert.equal(useLpbfEngineeringStore.getState().job?.status, "failed");
    assert.equal(useLpbfEngineeringStore.getState().resultSignature, "");
    assert.equal(reportMatches(), null);
  } finally {
    stop();
  }
}));

// ---- Rendering: evidence labels are never inside a dimmed ancestor -------------------------
const VOID = new Set(["input", "br", "hr", "img", "meta", "link"]);
/** Walks the static markup and returns the text nodes together with whether any ancestor is dimmed (opacity-NN class). */
function textNodes(html: string): { text: string; dimmed: boolean }[] {
  const out: { text: string; dimmed: boolean }[] = [];
  const stack: boolean[] = [];
  const re = /<(\/?)([a-zA-Z][a-zA-Z0-9]*)((?:[^>"']|"[^"]*"|'[^']*')*?)(\/?)>|([^<]+)/g;
  for (let m = re.exec(html); m; m = re.exec(html)) {
    if (m[5] !== undefined) { const text = m[5].trim(); if (text) out.push({ text, dimmed: stack.some(Boolean) }); continue; }
    const [, closing, tag, attrs, selfClosing] = m;
    if (closing) { stack.pop(); continue; }
    if (VOID.has(tag.toLowerCase()) || selfClosing) continue;
    stack.push(/class="[^"]*\bopacity-\d+/.test(attrs));
  }
  return out;
}
const renderHeader = (job: SimulationJob, staleResult: boolean, availability = "Unavailable") => renderToStaticMarkup(<ResultHeader job={job} material="Inconel 718" availability={availability} stale={staleResult} elapsed={0} cancel={() => {}} cancelling={false}/>);

test("stale rendering dims numbers only; evidence labels (unavailable/inconclusive/unvalidated) are never in a dimmed ancestor", () => {
  const job = completedJob();
  job.result = { ...job.result!, validationStatus: "unvalidated", mainRisk: "inconclusive", confidence: "low" };
  const html = renderHeader(job, true);
  const nodes = textNodes(html);
  const dimmed = nodes.filter(node => node.dimmed).map(node => node.text);
  assert.ok(dimmed.length >= 4, `stale values are dimmed (got ${dimmed.length})`);
  assert.ok(dimmed.some(text => text.startsWith("120")) && dimmed.some(text => text === "Measure"), "numbers and the recommendation are dimmed");
  const evidence = /unavailable|inconclusive|unvalidated|not resolved|incomplete|pending|limited|calibration|validation|confidence|screening|regime|risk/i;
  const labelled = nodes.filter(node => evidence.test(node.text));
  assert.ok(labelled.length >= 6, "evidence labels are present in the render");
  for (const node of labelled) assert.equal(node.dimmed, false, `evidence label must not be dimmed: ${node.text}`);
  for (const text of ["Experimental validation pending", "Calibration incomplete", "Unavailable"]) assert.ok(nodes.some(node => node.text === text && !node.dimmed), text);
  // Without stale there is no dimming at all.
  assert.equal(textNodes(renderHeader(job, false)).some(node => node.dimmed), false);
  // The scanner itself detects a dimmed ancestor (guards against a vacuous pass).
  assert.deepEqual(textNodes('<div class="a opacity-75"><p>x</p></div><p>y</p>'), [{ text: "x", dimmed: true }, { text: "y", dimmed: false }]);
});

test("the stale dimming helper is only applied to leaf value elements, never to a container", () => {
  const files = ["src/components/3d-distortion-lab/LpbfResultPresentation.tsx", "src/components/3d-distortion-lab/MeltPoolSummaryCard.tsx", "src/components/LpbfEngineeringWorkspace.tsx", "src/components/3d-distortion-lab/LpbfEngineeringSimulation.tsx"];
  let uses = 0;
  for (const file of files) {
    const source = readFileSync(new URL(`../${file}`, import.meta.url), "utf8");
    for (const match of source.matchAll(/<([a-zA-Z]+)\b[^<>]*staleValueClass\([^<>]*>/g)) { uses++; assert.ok(["dd", "p"].includes(match[1]), `${file}: staleValueClass on <${match[1]}>`); }
    assert.equal((source.match(/staleValueClass\(/g) ?? []).length, [...source.matchAll(/<([a-zA-Z]+)\b[^<>]*staleValueClass\([^<>]*>/g)].length, `${file}: every staleValueClass use is on an inspected element`);
  }
  assert.ok(uses >= 3);
});
