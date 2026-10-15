import React from "react";
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { renderToStaticMarkup } from "react-dom/server";
import { BuildJobMicrostructurePanel } from "../src/components/3d-distortion-lab/BuildJobMicrostructurePanel";
import { checkedFront, quantityReason } from "../src/utils/solidificationDisplay";
const BLOCKS = JSON.parse(readFileSync(new URL("./fixtures/build-job-microstructure-blocks.json", import.meta.url), "utf8"));
test("every real Build Job front renders quantity reasons without restoring removed flat fields", () => {
  for (const [name, block] of Object.entries(BLOCKS)) {
    const front = checkedFront(block);
    const markup = renderToStaticMarkup(<BuildJobMicrostructurePanel micro={block} />);
    assert.match(markup, /data-solidification-envelope/, name);
    assert.ok(!markup.includes("Hunt G/R screening"), name);
    for (const q of Object.values(front.quantities)) {
      assert.equal(q.value, null, name);
      assert.ok(markup.includes(quantityReason(q).replaceAll("'", "&#x27;")), name);
    }
  }
});
test("legacy scalar blocks request recomputation and display no legacy numbers", () => {
  const markup = renderToStaticMarkup(<BuildJobMicrostructurePanel micro={{ G_K_m: 1234567, status: "available" }} />);
  assert.match(markup, /Older solver result, recompute/);
  assert.doesNotMatch(markup, /1234567/);
});
test("missing microstructure renders nothing", () => assert.equal(renderToStaticMarkup(<BuildJobMicrostructurePanel micro={undefined} />), ""));
