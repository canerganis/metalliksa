import React from "react";
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { renderToStaticMarkup } from "react-dom/server";
import { MechanicsScenariosPanel, MechanicsScenariosResult } from "../src/components/3d-distortion-lab/MechanicsScenariosPanel";
import { EMPTY_MECHANICS_INPUT } from "../src/store/useLpbfBuildJobStore";

const load = (name: string): any => JSON.parse(readFileSync(new URL(`./fixtures/mechanics/${name}.json`, import.meta.url), "utf8"));
const render = (name: string) => renderToStaticMarkup(<MechanicsScenariosResult block={load(name)} />);
const plain = (html: string) => html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").replace(/&amp;/g, "&").replace(/&#x27;/g, "'");
const UNKNOWN = "Uncertainty is unknown and may be large. Calibrate to your machine for better accuracy.";
const M1_SCOPE = "It is an upper-bound scenario, not a prediction of the part's stress.";
const M2_SCOPE = "This is a released-cantilever scenario. It does not predict distortion of your part geometry.";
const M2_UNIFORM = "Uniform eigenstrain giving zero curvature is not a prediction that LPBF parts do not bend.";

test("saturated fixture shows tier label, unknown-uncertainty sentence, M1 scope, badge and mm tip deflection", () => {
  const html = render("saturated-bar-and-cantilever");
  const text = plain(html);
  assert.ok(html.includes("Uncalibrated estimate"));
  assert.ok(text.includes(UNKNOWN));
  assert.ok(text.includes(M1_SCOPE), text);
  assert.ok(html.includes("data-saturation-badge"));
  assert.ok(text.includes("Saturated at the supplied yield strength"));
  assert.ok(text.includes("Constrained-bar axial stress (scenario)"));
  assert.ok(text.includes("500 MPa"), text);
  assert.ok(text.includes("Released-cantilever tip deflection (scenario)"));
  assert.ok(text.includes("-0.45 mm"), text);
  assert.ok(!/µm/.test(text), "tip deflection must not be shown in micrometres");
  assert.ok(text.includes("Tip deflection divided by thickness"));
  assert.ok(text.includes(M2_SCOPE));
  assert.ok(!/error bar/i.test(html));
});

test("uniform fixture shows the zero-curvature sentence and no saturation badge", () => {
  const html = render("uniform-cantilever");
  const text = plain(html);
  assert.ok(text.includes(M2_UNIFORM), text);
  assert.ok(text.includes(M2_SCOPE));
  assert.ok(!html.includes("data-saturation-badge"));
  assert.ok(text.includes("0 mm"), text);
});

test("m1-derived fixture shows the refusal text and no number", () => {
  const html = render("m1-derived-refused");
  const text = plain(html);
  assert.ok(text.includes("Supply a matched-build effective inherent-strain profile or enter an explicit effective-profile scenario."), text);
  assert.ok(text.includes("A constrained-bar thermal cycle alone cannot determine cantilever bending."));
  assert.ok(!html.includes("data-estimate-value"));
});

test("not-requested fixture shows no number", () => {
  const html = render("not-requested");
  assert.ok(!html.includes("data-estimate-value"));
  assert.ok(!/\d+(\.\d+)? (MPa|mm)/.test(plain(html)));
  assert.ok(!html.includes("data-saturation-badge"));
});

test("a payload that feeds the verdict is rejected", () => {
  const block = { ...load("not-requested"), usedForBuildJobVerdict: true };
  const html = renderToStaticMarkup(<MechanicsScenariosResult block={block} />);
  assert.ok(html.includes("Mechanics payload rejected"));
});

test("panel states the scope, starts empty, preselects nothing and has add/remove profile controls", () => {
  const noop = () => {};
  const html = renderToStaticMarkup(<MechanicsScenariosPanel input={EMPTY_MECHANICS_INPUT} onBarChange={noop} onCantileverChange={noop} />);
  const text = plain(html);
  assert.ok(text.includes("not used by the Build Job verdict, the recoater gate, or the legacy residual-stress and distortion fields"));
  assert.ok(!/ checked=""/.test(html));
  assert.ok(!/ value="[^"]/.test(html.replace(/type="radio"[^>]*/g, "")), "no input may carry a prefilled value");
  assert.ok(text.includes("Add profile row"));
  assert.ok(!html.includes("data-profile-row"));
  const withRow = renderToStaticMarkup(<MechanicsScenariosPanel
    input={{ ...EMPTY_MECHANICS_INPUT, cantilever: { ...EMPTY_MECHANICS_INPUT.cantilever, profile: [{ from: null, to: null, strain: null }] } }}
    onBarChange={noop} onCantileverChange={noop} />);
  assert.ok(withRow.includes("data-profile-row"));
  assert.ok(withRow.includes("Remove profile row 1"));
});

test("source has no placeholder= attribute in the inputs", () => {
  const src = readFileSync(new URL("../src/components/3d-distortion-lab/MechanicsScenariosPanel.tsx", import.meta.url), "utf8");
  assert.ok(!/placeholder\s*=/.test(src));
  assert.ok(!/defaultValue\s*=/.test(src));
});
