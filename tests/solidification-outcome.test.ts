import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { solidificationOutcome } from "../src/utils/solidificationOutcome";
import type { SolidificationMicrostructureResult } from "../src/services/pythonComputationService";

// Real Python output (the same blocks python/test_lpbf_build_job.py check_microstructure_fixture() pins).
const BLOCKS = JSON.parse(readFileSync(new URL("./fixtures/build-job-microstructure-blocks.json", import.meta.url), "utf8"));
const as = (block: unknown) => block as SolidificationMicrostructureResult;

test("available and screening-fallback pass through with their status", () => {
  const ok = solidificationOutcome(as(BLOCKS.available_in718_150_1200));
  assert.ok("result" in ok && ok.result.status === "available");
  // P6 (2026-10-11): the solver no longer serves "screening-fallback" (the tail-length heuristic was removed); the
  // status is kept for legacy payloads, exercised on a synthetic block.
  const fb = solidificationOutcome(as({ ...BLOCKS.available_in718_150_1200, status: "screening-fallback", reason: "legacy tail-length heuristic" }));
  assert.ok("result" in fb && fb.result.status === "screening-fallback");
  assert.equal(fb.result.reason, "legacy tail-length heuristic");
});

test("P6 unavailable blocks (keyhole-leg depth, unsampled interface) yield the thermal reason, never a result", () => {
  for (const name of ["unavailable_keyhole_leg_in718_285_960", "unavailable_few_samples_in718_10_3000"]) {
    const out = solidificationOutcome(as(BLOCKS[name]));
    assert.deepEqual(out, { error: BLOCKS[name].reason });
    assert.ok(!("result" in out));
  }
});

test("degenerate-floor yields Python's reason flagged degenerate and never a result", () => {
  const block = BLOCKS.degenerate_floor_synthetic;
  assert.equal(block.status, "degenerate-floor");
  const out = solidificationOutcome(as(block));
  assert.deepEqual(out, { error: block.reason, degenerate: true });
  assert.ok(!("result" in out));
  // A numeric block with finite G/R/PDAS/SDAS is still not a result when its status says degenerate-floor.
  assert.ok("error" in solidificationOutcome(as({ ...BLOCKS.available_in718_150_1200, status: "degenerate-floor", reason: "r" })));
});

test("unavailable yields Python's reason and never a result", () => {
  const out = solidificationOutcome(as(BLOCKS.unavailable_no_kinetics));
  assert.deepEqual(out, { error: "thermal.solidificationKinetics missing or non-finite" });
  assert.deepEqual(solidificationOutcome(as({ status: "unavailable" })), { error: "no solidification data" });
});

test("a block without status, null, or non-finite numbers is an error, not a result", () => {
  assert.deepEqual(solidificationOutcome(as({ source: "rosenthal-analytical-screening", G_K_m: 1e4, R_m_s: 0.6, coolingRate_K_s: 6788, PDAS_um: 0.9, SDAS_um: 3.5 })), { error: "legacy result without status" });
  assert.deepEqual(solidificationOutcome(null), { error: "legacy result without status" });
  assert.ok("error" in solidificationOutcome(as({ ...BLOCKS.available_in718_150_1200, G_K_m: null })));
  assert.ok("error" in solidificationOutcome(as({ ...BLOCKS.available_in718_150_1200, PDAS_um: Number.NaN })));
});

test("the Lab routes every result through the guard", () => {
  const source = readFileSync("src/components/SolidificationMicrostructureLab.tsx", "utf8");
  assert.match(source, /const outcome = solidificationOutcome\(res\);/);
  assert.match(source, /setResult\(outcome\.result\);/);
  assert.ok(!/setResult\(res\)/.test(source));
  assert.ok(!/source\.includes\('rosenthal'\)/.test(source));
  assert.ok(!/Preset supplies k, liquidus and absorptivity/.test(source));
});

test("Lab wording: heat-source note is accurate, no overclaim, no marketing line", () => {
  const source = readFileSync("src/components/SolidificationMicrostructureLab.tsx", "utf8");
  assert.ok(!source.includes("the Python solver does not assume one"));
  assert.match(source, /Always sent explicitly: \{SOLIDIFICATION_HEAT_SOURCES\[heatSource\]\} is selected/);
  assert.ok(!source.includes("A process window, made visible."));
  assert.ok(!source.includes("the same numbers the"));
  assert.match(source, /median of G·R over front samples/);
  assert.match(source, /outcome\.degenerate === true/);
});
