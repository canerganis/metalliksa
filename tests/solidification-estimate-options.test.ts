import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { solidificationEstimateOptions } from "../src/components/SolidificationMicrostructureLab";

test("untouched surrogate checkbox sends no conductionSurrogate key (server selection stays default)", () => {
  assert.deepEqual(solidificationEstimateOptions(false, true, false), { inputSensitivity: false });
  assert.ok(!("conductionSurrogate" in solidificationEstimateOptions(true, true, false)));
});

test("touched surrogate checkbox sends the explicit value, including a return to the default", () => {
  assert.deepEqual(solidificationEstimateOptions(false, false, true), { inputSensitivity: false, conductionSurrogate: false });
  assert.deepEqual(solidificationEstimateOptions(true, true, true), { inputSensitivity: true, conductionSurrogate: true });
});

test("Lab wires the touched flag from the checkbox into the estimate request", () => {
  const source = readFileSync("src/components/SolidificationMicrostructureLab.tsx", "utf8");
  assert.match(source, /options: solidificationEstimateOptions\(inputSensitivity, conductionSurrogate, surrogateTouched\)/);
  assert.match(source, /setConductionSurrogate\(e\.target\.checked\); setSurrogateTouched\(true\)/);
});
