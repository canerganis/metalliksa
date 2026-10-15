import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { solidificationOutcome } from "../src/utils/solidificationOutcome";
import type { SolidificationMicrostructureResult } from "../src/services/pythonComputationService";
const BLOCKS = JSON.parse(readFileSync(new URL("./fixtures/build-job-microstructure-blocks.json", import.meta.url), "utf8"));
const as = (block: unknown) => block as SolidificationMicrostructureResult;
test("SOL-A unavailable containers pass through for per-quantity reason rendering", () => {
  for (const block of Object.values(BLOCKS)) assert.deepEqual(solidificationOutcome(as(block)), { result: block });
});
test("legacy flat and mutated containers are refused without a fallback", () => {
  for (const block of [null, { status: "available", G_K_m: 1e7 }, { ...Object.values(BLOCKS)[0] as object, quantities: {} }]) {
    assert.ok("error" in solidificationOutcome(as(block)));
  }
});
test("Lab uses shared process state, invalidates on vector changes, and removes unsourced chart bands and credits", () => {
  const source = readFileSync("src/components/SolidificationMicrostructureLab.tsx", "utf8");
  assert.match(source, /const outcome = solidificationOutcome\(res\);/);
  assert.match(source, /s.activeSpecimen.lpbf/);
  assert.match(source, /updateLpbfProcess/);
  assert.match(source, /useEffect\(\(\) => \{ invalidateResult\(\); \}, \[laserPower/);
  assert.doesNotMatch(source, /Hunt–Lu|Kirkwood|ReferenceLine|PDAS 1–30/);
});
