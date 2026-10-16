import React from "react";
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { renderToStaticMarkup } from "react-dom/server";
import { SolidificationEstimates } from "../src/components/SolidificationEstimates";

const load = (name: string): any => JSON.parse(readFileSync(new URL(`./fixtures/solidification-estimates/${name}.json`, import.meta.url), "utf8"));
const count = (s: string, needle: string) => s.split(needle).length - 1;

test("conduction fixtures show Uncalibrated estimate badges with the Physics estimate tier", () => {
  for (const name of ["ti64-conduction", "alsi10mg-conduction"]) {
    const html = renderToStaticMarkup(<SolidificationEstimates payload={load(name)} />);
    assert.ok(html.includes("Uncalibrated estimate"), name);
    assert.ok(html.includes('data-estimate-tier="Physics estimate"'), name);
    assert.ok(html.includes("Thermal gradient G"), name);
    assert.ok(html.includes("Out of domain:"), name);
  }
});

test("keyhole default shows No value and the constructive text without the duplicated parent sentence", () => {
  const html = renderToStaticMarkup(<SolidificationEstimates payload={load("ti64-keyhole-default")} />);
  assert.ok(html.includes("No value"));
  assert.ok(html.includes("Request the conduction-field surrogate"));
  assert.equal(count(html, "A parent value this quantity depends on is unavailable."), 0);
});

test("a rejected payload renders the rejection and no numeric value", () => {
  const bad = structuredClone(load("ti64-conduction"));
  bad.quantities.thermalGradient.validity.estimateTier = "Estimated";
  const html = renderToStaticMarkup(<SolidificationEstimates payload={bad} />);
  assert.ok(html.includes("Estimate payload rejected"));
  assert.doesNotMatch(html, /K\/m|\d\.\de[+-]?\d/);
  assert.ok(!html.includes("data-estimate-tier"));
});

test("surrogate sensitivity fixture shows the surrogate note and the auxiliary range label", () => {
  const html = renderToStaticMarkup(<SolidificationEstimates payload={load("ti64-surrogate-sensitivity")} />);
  assert.ok(html.includes("Conduction-field surrogate: the temperature field does not include the keyhole cavity."));
  assert.ok(html.includes("Auxiliary input sensitivity range (not an error bar)"));
});
