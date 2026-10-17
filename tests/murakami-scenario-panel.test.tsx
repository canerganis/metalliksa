import React from "react";
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { renderToStaticMarkup } from "react-dom/server";
import { MurakamiScenarioResult } from "../src/components/3d-distortion-lab/MurakamiScenarioResult";

const load = (name: string): any => JSON.parse(readFileSync(new URL(`./fixtures/murakami/${name}.json`, import.meta.url), "utf8"));
const render = (name: string) => renderToStaticMarkup(<MurakamiScenarioResult block={load(name)} />);
const UNKNOWN = "Uncertainty is unknown and may be large. Calibrate to your machine for better accuracy.";
const plain = (html: string) => html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").replace(/&amp;/g, "&");

test("scenario fixtures show the tier label, the unknown-uncertainty sentence and the value in MPa at 2 digits", () => {
  for (const name of ["ti64-assumed-scenario", "alsi10mg-assumed-scenario"]) {
    const block = load(name);
    const html = render(name);
    assert.ok(html.includes("Uncalibrated estimate"), name);
    assert.ok(plain(html).includes(UNKNOWN), name);
    const expected = `${Number(block.fatigueLimit_MPa.toPrecision(2))} MPa`;
    assert.ok(html.includes(expected), `${name} ${expected}`);
    assert.ok(html.includes("Murakami threshold stress amplitude (R = -1)"), name);
    assert.ok(!/error bar|confidence interval/i.test(html), name);
  }
  assert.ok(render("ti64-assumed-scenario").includes("280 MPa"));
});

test("first warning is visible and the rest sit behind the More toggle", () => {
  const html = render("ti64-assumed-scenario");
  assert.ok(html.includes("data-estimate-warnings-toggle"));
  assert.ok(html.includes("More (3 more warnings)"));
  assert.equal(html.split("data-estimate-warnings-more").length - 1, 1);
  assert.ok(/data-estimate-warnings-more/.test(html) && /hidden=""/.test(html));
});

test("scenario echo states size with basis, location, hardness, evidence kinds and R = -1", () => {
  const text = plain(render("ti64-assumed-scenario"));
  assert.ok(text.includes("defect √area 250 µm (assumed scenario, selected defect)"));
  assert.ok(text.includes("internal defect"));
  assert.ok(text.includes("330 HV"));
  assert.ok(text.includes("R = -1"));
  assert.ok(text.includes("No fatigue strength is given at 1e+07 cycles"));
});

test("empty fixture shows constructive missing-input text and no number", () => {
  const html = render("empty");
  const text = plain(html);
  assert.ok(text.includes("Supply projected defect square-root area in micrometres"));
  assert.ok(text.includes("Missing: defect square-root area"));
  assert.ok(!html.includes("data-estimate-value"));
  assert.ok(!/\d+(\.\d+)? (MPa|µm)/.test(text), text);
  assert.ok(!html.includes("data-scenario-echo"));
});

test("block-maxima fixture shows the observed maximum without a tier and the Gumbel line in micrometres", () => {
  const html = render("block-maxima");
  const text = plain(html);
  assert.ok(text.includes("observed in supplied data"));
  assert.ok(html.includes("data-observed-maximum"));
  assert.ok(text.includes("Largest defect in target volume (Gumbel)"));
  assert.ok(text.includes("95 µm"), text);
  assert.ok(text.includes("measured CT detection threshold (echo, no estimate tier): 12 µm (POD 90/95 on drilled holes)"));
  assert.ok(!/error bar|confidence interval/i.test(html));
});

test("a malformed payload is rejected with a visible message", () => {
  const html = renderToStaticMarkup(<MurakamiScenarioResult block={{ schema: "murakami-screening-2" }} />);
  assert.ok(html.includes("Fatigue payload rejected"));
});

test("the decision lab has no alloy hardness default and no example size placeholder", () => {
  const src = readFileSync(new URL("../src/components/3d-distortion-lab/IndustrialLPBFDecisionLab.tsx", import.meta.url), "utf8");
  assert.ok(!src.includes("alloyHvDefaults"));
  assert.ok(!src.includes("40, 55, 62, 48, 70"));
  assert.ok(!/placeholder=/.test(src.slice(src.indexOf("function MurakamiInputs"))));
});
