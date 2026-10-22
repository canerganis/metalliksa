import React from "react";
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { renderToStaticMarkup } from "react-dom/server";
import { GrSolidificationMapCard, GrHeatmap, GrCellDetail } from "../src/components/GrSolidificationMapCard";
import { checkedGrSolidification, noValueExplanation, METRICS, metricValue, metricRange, scaleStyle, NO_VALUE_STYLE, moveCell } from "../src/data/lpbfGrSolidification";
const fixture = (name: string) => JSON.parse(readFileSync(new URL(`./fixtures/solidification-payloads/${name}.json`, import.meta.url), "utf8"));
test("real schema2 point and map fixtures parse, including non-Ni alloys with unavailable quantities", () => {
  for (const name of ["gr-point-in718", "gr-map-in718", "gr-point-ti6al4v"]) {
    const result = checkedGrSolidification(fixture(name));
    for (const body of result.cells ?? [result.point!]) {
      for (const spec of METRICS) assert.equal(metricValue(body, spec.id), null);
    }
  }
});
test("strict GR parser refuses legacy, unknown statuses, count drift and invalid quantities", () => {
  const original = fixture("gr-map-in718");
  for (const mutate of [
    (x: any) => x.schema = "lpbf-gr-solidification-1",
    (x: any) => x.cells[0].status = "screening-fallback",
    (x: any) => x.counts.unavailable++,
    (x: any) => x.cells[0].front.quantities.thermalGradient.value = 123,
    (x: any) => x.cells[0].front.median = { G_K_m: 123 },
    (x: any) => x.cet.sourceChecks.equationRead.status = "verified",
    (x: any) => delete x.cells[0].cet.quantities.class,
    (x: any) => x.cet.sourceChecks.printedLimitComparison.computed = ["wrong-unit-value"],
  ]) {
    const raw = structuredClone(original); mutate(raw);
    assert.throws(() => checkedGrSolidification(raw));
  }
  assert.throws(() => checkedGrSolidification(fixture("gr-point-unknown")));
});
test("map keeps empty unavailable cells, keyboard grid semantics and per-quantity reasons", () => {
  const result = checkedGrSolidification(fixture("gr-map-in718"));
  const body = result.cells![0];
  assert.equal(metricRange(result.cells!, "goverr"), null);
  assert.deepEqual(scaleStyle(null, null), NO_VALUE_STYLE);
  assert.deepEqual(moveCell({ iP: 0, iV: 0 }, "ArrowRight", 2, 2), { iP: 0, iV: 1 });
  const grid = renderToStaticMarkup(<GrHeatmap result={result} metric="goverr" selected={{ iP: 0, iV: 0 }} />);
  assert.match(grid, /role="grid"/); assert.match(grid, /tabindex="0"/);
  const detail = renderToStaticMarkup(<GrCellDetail body={body} result={result} />);
  assert.match(detail, /data-solidification-envelope/); assert.match(detail, /computed on request on the solidification estimate channel/); // SOL-T head container: SOL-C values live on the opt-in estimate channel
  assert.doesNotMatch(detail, /Hunt G\/R screening/);
  const card = renderToStaticMarkup(<GrSolidificationMapCard initialResult={result} />);
  assert.doesNotMatch(card, /Hunt bands|Gäumann 2001 PDF read/);
  assert.ok(!METRICS.some(m => String(m.id) === "band"));
});
test("group 6: the cell detail shows the CET projection with its tier label, first warning and More disclosure", () => {
  const result = checkedGrSolidification(fixture("gr-point-in718"));
  const point = result.point!;
  assert.equal(point.cet.projectionId, "sol-c-cet-projection-v1");
  assert.ok(["columnar", "mixed", "equiaxed"].includes(String(point.cet.quantities.class.value)));
  const detail = renderToStaticMarkup(<GrCellDetail body={point} result={result} />);
  assert.match(detail, /data-estimate-tier="Physics estimate"/);
  assert.match(detail, />Uncalibrated estimate</);
  assert.match(detail, /Uncertainty is unknown and may be large\. Calibrate to your machine for better accuracy\./);
  assert.match(detail, /data-estimate-warnings-toggle/);
  assert.doesNotMatch(detail, /error bar/i);
  const broken = structuredClone(fixture("gr-point-in718"));
  broken.point.cet.projectionId = "knapp-legacy";
  assert.throws(() => checkedGrSolidification(broken));
});

test("bug 1: a map whose cells carry no G/R value says why in one sentence (real engine fixture: partial cells, gate sol-c-local-samples-not-installed)", () => {
  const result = checkedGrSolidification(fixture("gr-map-in718"));
  assert.equal(result.counts.computed, 0);
  assert.ok(result.counts.partial > 0);
  for (const metric of ["goverr", "cooling", "laves"] as const) {
    const sentence = noValueExplanation(result.cells!, metric);
    assert.ok(sentence && sentence.startsWith("No cell has a value for this metric."), metric);
  }
  assert.match(noValueExplanation(result.cells!, "goverr")!, /computed on request on the solidification estimate channel/);
  const card = renderToStaticMarkup(<GrSolidificationMapCard initialResult={result} />);
  assert.match(card, /data-testid="gr-no-values"/);
  // A map with a value on one cell shows no explanation.
  const withValue = structuredClone(result);
  withValue.cells![0].front.quantities.gOverR.value = 1e6;
  assert.equal(noValueExplanation(withValue.cells!, "goverr"), null);
});
