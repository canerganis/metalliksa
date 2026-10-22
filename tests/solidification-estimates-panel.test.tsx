import React from "react";
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { renderToStaticMarkup } from "react-dom/server";
import { EstimateWarnings, SolidificationEstimates } from "../src/components/SolidificationEstimates";

const load = (name: string): any => JSON.parse(readFileSync(new URL(`./fixtures/solidification-estimates/${name}.json`, import.meta.url), "utf8"));
const count = (s: string, needle: string) => s.split(needle).length - 1;

test("conduction fixtures show Uncalibrated estimate badges with the Physics estimate tier", () => {
  for (const name of ["ti64-conduction", "alsi10mg-conduction"]) {
    const html = renderToStaticMarkup(<SolidificationEstimates payload={load(name)} />);
    assert.ok(html.includes("Uncalibrated estimate"), name);
    assert.ok(html.includes('data-estimate-tier="Physics estimate"'), name);
    assert.ok(html.includes("Thermal gradient G"), name);
    assert.ok(html.includes("Outside the tested range of the model:"), name);
  }
});

test("surrogate turned off shows No value and the constructive text without the duplicated parent sentence", () => {
  const html = renderToStaticMarkup(<SolidificationEstimates payload={load("ti64-keyhole-surrogate-off")} />);
  assert.ok(html.includes("No value"));
  assert.ok(html.includes("turn it on (the default)"));
  assert.equal(count(html, "A parent value this quantity depends on is unavailable."), 0);
});

test("keyhole default shows values with the keyhole warning as the one visible line per row", () => {
  const html = renderToStaticMarkup(<SolidificationEstimates payload={load("ti64-keyhole-default")} />);
  assert.ok(html.includes('data-estimate-tier="Physics estimate"'));
  const rows = html.split('data-estimate-warnings="true"').slice(1);
  assert.ok(rows.length >= 6);
  for (const row of rows) {
    const visible = row.split("data-estimate-warnings-more")[0];
    assert.equal(count(visible, "data-estimate-warning="), 1);
    assert.ok(visible.includes("Keyhole regime. These estimates use the rear solidifying front"));
  }
});

test("further warnings sit behind an accessible More button", () => {
  const closed = renderToStaticMarkup(<EstimateWarnings warnings={["first", "second", "third"]} />);
  assert.match(closed, /<button type="button"[^>]*aria-expanded="false"[^>]*aria-controls="[^"]+"/);
  assert.ok(closed.includes("2 more notes"));
  assert.match(closed, /<span id="[^"]+" hidden="" class="block" data-estimate-warnings-more="true">/);
  const open = renderToStaticMarkup(<EstimateWarnings warnings={["first", "second"]} initiallyOpen />);
  assert.match(open, /aria-expanded="true"/);
  assert.doesNotMatch(open, /hidden=""/);
  assert.equal(renderToStaticMarkup(<EstimateWarnings warnings={["only"]} />).includes("<button"), false);
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
  assert.ok(html.includes("Simplified temperature field: it does not include the keyhole cavity."));
  assert.ok(html.includes("Auxiliary input sensitivity range (not an error bar)"));
});
