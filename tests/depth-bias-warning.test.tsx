import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { computeDepthBiasWarning, resolveDepthBiasWarning, enthalpyClassOf, DEPTH_BIAS_CELLS, DEPTH_BIAS_BANDS_ID, DEPTH_BIAS_ENTHALPY_EDGES } from "../src/utils/depthBiasWarning";
import { DepthBiasNotice } from "../src/components/DepthBiasNotice";

const SUMMARY = JSON.parse(fs.readFileSync(path.join(process.cwd(), "data", "calibration", "lpbf-meltpool-error-bands-v1.summary.json"), "utf8"));

test("the pinned table equals the committed error-band summary", () => {
  assert.equal(DEPTH_BIAS_BANDS_ID, SUMMARY.bandsId);
  const expected: Record<string, [number, number, number]> = {};
  for (const c of SUMMARY.cells) {
    if (c.quantity !== "depth" || c.alloys.length !== 1 || !["conduction", "transition", "keyhole"].includes(c.regime)) continue;
    expected[`${c.alloys[0]}|${c.kernel}|${c.regime}`] = [Math.round(c.median * 1000) / 1000, c.n, c.nSources];
  }
  assert.deepEqual(DEPTH_BIAS_CELLS, expected);
  assert.deepEqual([...DEPTH_BIAS_ENTHALPY_EDGES], SUMMARY.config.thresholds);
});

test("the band class follows the enthalpy index edges, not the served label", () => {
  assert.equal(enthalpyClassOf(13.94), "conduction");
  assert.equal(enthalpyClassOf(15), "transition");
  assert.equal(enthalpyClassOf(19.99), "transition");
  assert.equal(enthalpyClassOf(20), "keyhole");
  assert.equal(enthalpyClassOf(null), null);
  assert.equal(enthalpyClassOf(Number.NaN), null);
  // IN625 served label is Keyhole at 13.6 and up, but index 18.6 is the transition band: measured underprediction.
  const w = computeDepthBiasWarning("Keyhole Mode", "Inconel 625", "rosenthal", 18.6);
  assert.equal(w.direction, "may-underestimate");
  assert.match(w.text ?? "", /transition band/);
  assert.match(w.basis ?? "", /Inconel 625 \/ rosenthal \/ transition/);
  assert.match(w.basis ?? "", /conduction below 15, transition 15 to 20, keyhole at 20 or above/);
  // Index below 15 is conduction while the label says keyhole: contradiction, no direction (Lane CBM-C).
  const c = computeDepthBiasWarning("Keyhole Mode", "Inconel 625", "rosenthal", 13.94);
  assert.equal(c.direction, null);
  assert.match(c.text ?? "", /served regime label \(keyhole\) and the error-band class from the enthalpy index \(conduction, dH\/hs 13\.94\) disagree here/);
  assert.match(c.text ?? "", /median depth error of 25% \(overpredicted, n=16, 2 sources\)\. No direction is given/);
  for (const k of ["rosenthal", "eagar-tsai", "goldak"]) assert.equal(computeDepthBiasWarning("Keyhole Mode", "Inconel 625", k, 13.94).direction, null);
  assert.equal(computeDepthBiasWarning("Keyhole Mode", "Inconel 625", "rosenthal", 17.1).direction, "may-underestimate");
  // Without an index the label decides (n=1 keyhole cell: no direction).
  const f = computeDepthBiasWarning("Keyhole Mode", "Inconel 625", "rosenthal");
  assert.equal(f.direction, null);
  assert.doesNotMatch(f.basis ?? "", /enthalpy index/);
});

test("direction follows the served kernel, alloy and regime class from the summary", () => {
  const regime = "Conduction Mode (Stable)";
  const ro = computeDepthBiasWarning(regime, "Inconel 625", "rosenthal");
  assert.equal(ro.direction, "may-overestimate");
  assert.match(ro.text ?? "", /Rosenthal kernel on Inconel 625 overpredicted the depth by a median of 25% \(n=16, 2 sources\)/);
  const gk = computeDepthBiasWarning(regime, "Inconel 625", "goldak");
  assert.match(gk.text ?? "", /Goldak kernel on Inconel 625 overpredicted the depth by a median of 44% \(n=17/);
  const tr = computeDepthBiasWarning("Transition Mode", "Inconel 625", "goldak");
  assert.equal(tr.direction, "may-underestimate");
  assert.match(tr.text ?? "", /underpredicted the depth by a median of 48% \(n=6, 1 source\)/);
});

test("Ti-6Al-4V Rosenthal keyhole is never called underestimated", () => {
  const w = computeDepthBiasWarning("Keyhole Mode (melt-pool D/W > 0.5 screening onset)", "Ti-6Al-4V", "rosenthal", 25);
  assert.equal(w.direction, "may-overestimate");
  assert.doesNotMatch(w.text ?? "", /underestimated/);
});

test("cells with too few tracks or no cell give no direction", () => {
  const few = computeDepthBiasWarning("Keyhole Mode", "Inconel 625", "rosenthal");
  assert.equal(few.direction, null);
  assert.match(few.text ?? "", /Too few held-out tracks/);
  const none = computeDepthBiasWarning("Conduction Mode (Stable)", "Inconel 718", "goldak");
  assert.equal(none.direction, null);
  assert.match(none.text ?? "", /No held-out check for this alloy and kernel/);
  assert.equal(computeDepthBiasWarning("Transition Mode", "Inconel 625", null).text, null);
});

test("a served depthBiasWarning wins over the derived one", () => {
  const served = { direction: null, text: null, basis: null } as const;
  assert.equal(resolveDepthBiasWarning({ regime: "Transition Mode", depthBiasWarning: served }, "Inconel 625", "goldak", 17), served);
});

test("notice renders alloy note and warning text for the served kernel", () => {
  const html = renderToStaticMarkup(
    React.createElement(DepthBiasNotice, { geometry: { regime: "Transition Mode", regimeMaterialNote: "threshold not validated for this alloy" }, material: "Inconel 625", heatSource: "goldak", enthalpy: 17.5 }),
  );
  assert.match(html, /data-depth-bias="may-underestimate"/);
  assert.match(html, /Alloy note: threshold not validated for this alloy\./);
  assert.match(html, /Depth may be underestimated/);
  assert.doesNotMatch(html, /[–—]/);
  const empty = renderToStaticMarkup(React.createElement(DepthBiasNotice, { geometry: { regime: "Conduction Mode (Stable)" }, material: "Inconel 718" }));
  assert.equal(empty, "");
});
