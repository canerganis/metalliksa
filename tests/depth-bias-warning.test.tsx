import { test } from "node:test";
import assert from "node:assert/strict";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { computeDepthBiasWarning, resolveDepthBiasWarning } from "../src/utils/depthBiasWarning";
import { DepthBiasNotice } from "../src/components/DepthBiasNotice";

test("Transition and Keyhole labels warn that depth is likely underestimated", () => {
  for (const regime of ["Transition Mode", "Keyhole Mode (melt-pool D/W > 0.5 screening onset)"]) {
    const w = computeDepthBiasWarning(regime, "Inconel 625");
    assert.equal(w.direction, "likely-underestimated");
    assert.match(w.text ?? "", /not a validated correction/);
  }
});

test("Conduction on IN625 gets the softer overprediction note, other alloys get none", () => {
  const w = computeDepthBiasWarning("Conduction Mode (Stable)", "Inconel 625");
  assert.equal(w.direction, "may-overestimate");
  assert.match(w.text ?? "", /1\.25 to 1\.3 times for the served depth/);
  assert.equal(computeDepthBiasWarning("Conduction Mode (Stable)", "Inconel 718").direction, null);
});

test("a served depthBiasWarning wins over the derived one", () => {
  const served = { direction: null, text: null, basis: null } as const;
  assert.equal(resolveDepthBiasWarning({ regime: "Transition Mode", depthBiasWarning: served }, "Inconel 625"), served);
});

test("notice renders alloy note and warning text, and nothing when neither applies", () => {
  const html = renderToStaticMarkup(
    React.createElement(DepthBiasNotice, { geometry: { regime: "Transition Mode", regimeMaterialNote: "threshold not validated for this alloy" }, material: "Inconel 625" }),
  );
  assert.match(html, /data-depth-bias="likely-underestimated"/);
  assert.match(html, /Alloy note: threshold not validated for this alloy\./);
  assert.match(html, /Depth is likely underestimated/);
  assert.doesNotMatch(html, /[–—]/);
  const empty = renderToStaticMarkup(React.createElement(DepthBiasNotice, { geometry: { regime: "Conduction Mode (Stable)" }, material: "Inconel 718" }));
  assert.equal(empty, "");
});
