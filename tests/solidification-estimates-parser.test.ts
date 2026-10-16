import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { checkedSolidificationEstimates } from "../src/utils/solidificationEstimateDisplay";

const DIR = new URL("./fixtures/solidification-estimates/", import.meta.url);
const load = (name: string): any => JSON.parse(readFileSync(new URL(`${name}.json`, DIR), "utf8"));
const names = readdirSync(DIR).filter(f => f.endsWith(".json")).map(f => f.replace(/\.json$/, ""));

test("every real estimate fixture parses", () => {
  assert.ok(names.length >= 7);
  for (const name of names) assert.doesNotThrow(() => checkedSolidificationEstimates(load(name)), name);
});

test("Ti64 and AlSi10Mg conduction fixtures carry uncalibrated thermal estimates", () => {
  for (const name of ["ti64-conduction", "alsi10mg-conduction"]) {
    const p = checkedSolidificationEstimates(load(name));
    for (const q of ["thermalGradient", "normalSpeed", "coolingRate", "gOverR"]) {
      const v = p.quantities[q].validity;
      assert.equal(v.estimateTier, "Physics estimate", `${name} ${q}`);
      assert.equal(v.tierLabel, "Uncalibrated estimate", `${name} ${q}`);
      assert.equal(typeof p.quantities[q].value, "number", `${name} ${q}`);
    }
  }
});

test("Ti64 keyhole default has no values and names the keyhole reason", () => {
  const p = checkedSolidificationEstimates(load("ti64-keyhole-default"));
  for (const [name, q] of Object.entries(p.quantities)) assert.equal(q.value, null, name);
  assert.ok(p.quantities.thermalGradient.reasons.some(r => r.code === "keyhole-field-inconsistent"));
});

test("Ti64 surrogate sensitivity fixture has auxiliary ranges and no estimate band", () => {
  const p = checkedSolidificationEstimates(load("ti64-surrogate-sensitivity"));
  for (const q of ["thermalGradient", "normalSpeed", "coolingRate", "gOverR"]) {
    assert.ok(p.quantities[q].validity.inputSensitivity, q);
    assert.equal(p.quantities[q].validity.estimateBand, null, q);
  }
});

const mutations: [string, (j: any) => void][] = [
  ["(a) tier laundering past the transfer cap", j => { j.quantities.thermalGradient.validity.estimateTier = "Estimated"; }],
  ["(b) removed inherited domain warning", j => {
    // Inheritance is checked per warning code, so drop every entry of one inherited code.
    const v = j.quantities.thermalGradient.validity;
    v.domainWarnings = v.domainWarnings.filter((w: any) => w.code !== "domain-extrapolation");
  }],
  ["(c) warning code in reasons", j => { j.quantities.thermalGradient.reasons.push({ code: "domain-extrapolation", params: {} }); }],
  ["(d) displaySignificantDigits 3", j => { j.quantities.thermalGradient.validity.displaySignificantDigits = 3; }],
  ["(e) changed uncertainty statement", j => { j.quantities.thermalGradient.validity.uncertaintyStatement = "Uncertainty is small."; }],
  ["(f) unknownComponents without model-error", j => {
    const s = load("ti64-surrogate-sensitivity");
    j.quantities.thermalGradient.validity.inputSensitivity = s.quantities.thermalGradient.validity.inputSensitivity;
    j.quantities.thermalGradient.validity.inputSensitivity.unknownComponents = ["input-interactions"];
  }],
  ["(g) KM offset_K 20", j => { j.quantities.kmAlphaMFraction.evaluation.offset_K = 20; }],
  ["(h) KM residual key renamed", j => {
    const r = j.quantities.kmAlphaMFraction.residual; r.retainedBeta = r.untransformedAsymptote; delete r.untransformedAsymptote;
  }],
  ["(i) nucleationScenarioNote removed", j => { delete j.quantities.equiaxedEnvelopeFraction.validity.nucleationScenarioNote; }],
  ["(j) frontSamples sourceId changed", j => { j.inputProvenance.frontSamples.sourceId = `${j.inputProvenance.frontSamples.sourceId}-x`; }],
  ["(k) v1 envelope schema", j => { j.quantityEnvelopeSchema = "metalliksa-quantity-envelope-1"; }],
];
for (const [label, mutate] of mutations) {
  test(`parser rejects ${label}`, () => {
    const j = structuredClone(load("ti64-conduction"));
    mutate(j);
    assert.throws(() => checkedSolidificationEstimates(j));
  });
}
