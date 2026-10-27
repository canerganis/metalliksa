import React from "react";
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { renderToStaticMarkup } from "react-dom/server";
import { BlockingGateSummary, formatIterationAspectRatio, formatIterationBalling, formatIterationGates } from "../src/components/LpbfBayesianOptimizerLab";
import { toActionableReason } from "../src/utils/lpbfActionableReasons";
import type { PythonBayesianOptimizationResult } from "../src/services/pythonComputationService";

const read = (path: string) => readFileSync(new URL(`../${path}`, import.meta.url), "utf8");
const text = (markup: string) => markup.replace(/<[^>]+>/g, " ").replace(/&#x27;/g, "'").replace(/\s+/g, " ");

// Shape and strings from python/lpbf_bayesian_optimizer.py (_iteration_diagnostics, _gate_summary, KEYHOLE_GATE_NOTE).
const PY_OPT = read("python/lpbf_bayesian_optimizer.py");
const KEYHOLE_NOTE = (() => {
  const m = /KEYHOLE_GATE_NOTE = \(\s*((?:'[^']*'\s*)+)\)/.exec(PY_OPT);
  assert.ok(m, "KEYHOLE_GATE_NOTE not found");
  return [...m[1].matchAll(/'([^']*)'/g)].map((x) => x[1]).join("");
})();

test("per-iteration gate cell separates failing, risk and advisory-only gates", () => {
  const d = {
    blockingGates: ["keyhole"], riskGates: ["balling", "literature_pv"], advisoryGates: ["recoater", "distortion"],
    reasons: [], extentStatus: "computed", normalizedEnthalpy: 47.29, aspectRatio_L_over_W: 7.59,
    keyholeRisk: "High", keyholeHigh: true,
  };
  assert.equal(formatIterationGates(d), "fail: keyhole; warn: balling, literature_pv; advisory (no verdict effect): recoater, distortion");
  assert.equal(formatIterationGates({ ...d, blockingGates: [], riskGates: [], advisoryGates: [] }), "none");
});

test("L/W cell marks the heuristic fallback value as unavailable for non-computed extents", () => {
  const d = {
    blockingGates: [], riskGates: [], advisoryGates: [], reasons: [], extentStatus: "computed",
    normalizedEnthalpy: 47.29, aspectRatio_L_over_W: 7.59, keyholeRisk: "High", keyholeHigh: true,
  };
  assert.equal(formatIterationAspectRatio(d), "7.59");
  assert.equal(formatIterationAspectRatio({ ...d, extentStatus: "heuristic-width-fallback", aspectRatio_L_over_W: 2.1 }),
    "2.1 (unavailable: heuristic-width-fallback)");
  assert.equal(formatIterationAspectRatio({ ...d, aspectRatio_L_over_W: null }), "not returned");
  assert.equal(formatIterationAspectRatio(undefined), "not returned");
});

test("per-iteration verdict reasons are rendered inline (details), not only in a title tooltip", () => {
  const src = read("src/components/LpbfBayesianOptimizerLab.tsx");
  assert.ok(!/title=\{d \? d\.reasons/.test(src));
  assert.match(src, /<details[^>]*>\s*<summary[^>]*>Reasons \(\{d\.reasons\.length\}\)<\/summary>/);
});

test("all-zero run shows the dominant blocking gates and the frozen keyhole note", () => {
  const result = {
    success: true, alloyId: "in718", bestScore: 0, iterations: [], converged: false, elapsedMs: 1, nIterations: 20,
    noPositiveScore: true,
    gateSummary: { blockingGateCounts: { keyhole: 15 }, riskGateCounts: { literature_pv: 19, balling: 11 },
      inconclusiveExtentStatusCounts: { "heuristic-width-fallback": 9 } },
    keyholeGateNote: KEYHOLE_NOTE,
  } as PythonBayesianOptimizationResult;
  const t = text(renderToStaticMarkup(<BlockingGateSummary result={result} />));
  assert.match(t, /Do-not-print \(failing gate\): keyhole ×15/);
  assert.match(t, /Inconclusive \(melt-pool extent not resolved\): heuristic-width-fallback ×9/);
  assert.match(t, /balling ×11/);
  assert.match(t, /frozen thermal solver/);
  assert.match(t, /the regime threshold moved to 20 in the keyhole-regime bump/);
  assert.match(t, /never do-not-print since P7a/);
  // A backend without the summary is reported, not hidden.
  const bare = text(renderToStaticMarkup(<BlockingGateSummary result={{ ...result, gateSummary: undefined, keyholeGateNote: undefined }} />));
  assert.match(bare, /Gate summary not returned/);
  assert.match(bare, /Keyhole gate note not returned/);
});

test("balling cell shows the Eagar–Tsai L/W band and its verdict effect", () => {
  const d = {
    blockingGates: [], riskGates: [], advisoryGates: ["balling"], reasons: [], extentStatus: "computed",
    normalizedEnthalpy: 20, aspectRatio_L_over_W: 7.11, keyholeRisk: null, keyholeHigh: false,
    ballingBand: "moderate" as const, ballingLengthToWidthEagarTsai: 5.016,
  };
  assert.equal(formatIterationBalling(d), "moderate (5.02; advisory)");
  assert.equal(formatIterationBalling({ ...d, ballingBand: "high", ballingLengthToWidthEagarTsai: 6 }), "high (6.00; risky)");
  assert.equal(formatIterationBalling({ ...d, ballingBand: null }), "unavailable (Eagar–Tsai extent not computed)");
  assert.equal(formatIterationBalling({ ...d, ballingBand: undefined }), "not returned");
});

test("optimizer table has the failing-gate diagnostic columns", () => {
  const src = read("src/components/LpbfBayesianOptimizerLab.tsx");
  for (const col of ["Gates \\(fail / warn / advisory\\)", "Extent", "ΔH/hₛ", "L/W", "Balling \\(Eagar–Tsai L/W\\)", "Keyhole flag"]) assert.match(src, new RegExp(`<th scope="col"[^>]*>${col}</th>`), col);
  assert.ok(src.includes("<BlockingGateSummary result={result} />"));
});

test("advisory reasons get no P/v action; balling screen still gets its action", () => {
  const adv = "Advisory: inherent-strain distortion index 7.59 (≥0.65) — alloy/layer advisory independent of P, v and hatch: the frozen distortion index depends only on alloy properties, preheat and layer thickness (not on P, v or hatch); it does not change the verdict.";
  assert.equal(toActionableReason(adv), adv);
  const rec = "Advisory: recoater crash / part curl flag High (distortion index 7.59 > 2.0) — alloy/layer advisory independent of P, v and hatch.";
  assert.equal(toActionableReason(rec), rec);
  const ball = toActionableReason("Balling screen High: Eagar–Tsai L/W = 6.00 (> 5.5; 69/71 Hofmann 316L tracks above it balled) — Eagar-Tsai aspect-ratio screen.");
  assert.match(ball, /Action:/);
  // L/W grows with P·v and shrinks with spot size: the action must not say "raise power".
  assert.match(ball, /lower the power–speed product/);
  assert.doesNotMatch(ball, /raise power/);
  const mod = "Advisory: balling screen Moderate — Eagar–Tsai L/W = 5.02 > 3.85; it does not change the verdict.";
  assert.equal(toActionableReason(mod), mod);
});

test("Python advisory / balling-screen wording and the 'advisory' gate status reach the TS contract", () => {
  const py = read("python/lpbf_build_job_solver.py");
  assert.match(py, /ADVISORY_GATES = \("recoater", "distortion"\)/);
  assert.match(py, /not a demonstrated balling/);
  // P7b (2026-10-14): no High band; the Hofmann tracks are recorded evidence per L/W bin, not a threshold.
  assert.match(py, /Eagar-Tsai aspect-ratio screen \(model L\/W uncertainty about \+-10 %\); the Hofmann 2026 316L single tracks/);
  assert.match(py, /no High band since P7b/);
  assert.doesNotMatch(py, /> 3\.8\)/);
  // P7a (2026-10-11): recoater and distortion are not-evaluated (no sourced stress model), never advisory numbers.
  assert.match(py, /"recoater",\s*"not-evaluated"/);
  assert.match(py, /"distortion",\s*"not-evaluated"/);
  // Tang bump (2026-10-27): the verdict basis names the Tang and keyhole risk screen.
  assert.match(py, /VERDICT_BASIS = "model-geometry-tang-keyhole-risk-screen"/);
  const ts = read("src/services/pythonComputationService.ts");
  // P6 containment (2026-10-11): "not-evaluated" for a null gate input, never counted as pass or fail.
  assert.match(ts, /export type PythonLpbfGateStatus = "pass" \| "warn" \| "fail" \| "unavailable" \| "advisory" \| "not-evaluated";/);
  const banner = read("src/components/3d-distortion-lab/IndustrialLPBFDecisionLab.tsx");
  assert.match(banner, /g\.status === "advisory"/);
});
