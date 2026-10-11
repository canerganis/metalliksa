import React from "react";
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { renderToStaticMarkup } from "react-dom/server";
import { BuildJobMicrostructurePanel } from "../src/components/3d-distortion-lab/BuildJobMicrostructurePanel";

// Real Python output: python/test_lpbf_build_job.py check_microstructure_fixture() fails when this file differs from
// project_build_job_microstructure (regenerate with `python test_lpbf_build_job.py --write-microstructure-fixture`).
const BLOCKS = JSON.parse(readFileSync(new URL("./fixtures/build-job-microstructure-blocks.json", import.meta.url), "utf8"));
const html = (name: string) => {
  assert.ok(BLOCKS[name], name);
  return renderToStaticMarkup(<BuildJobMicrostructurePanel micro={BLOCKS[name]} />);
};
const text = (markup: string) => markup.replace(/<[^>]+>/g, " ").replace(/&#x27;/g, "'").replace(/&gt;/g, ">").replace(/&lt;/g, "<").replace(/\s+/g, " ");

test("available (field map): numbers, correlation names, modelId · gradientSource, keyhole regime note, no fallback note", () => {
  const markup = html("available_in718_285_960");
  const t = text(markup);
  assert.match(markup, /data-micro-status="available"/);
  // Wave B (LA-2 field, KS-1 solidifying-front samples): PDAS/SDAS 0.66/0.51 -> 0.67/0.47 um; P1 (2026-10-11, flat
  // absorptivity and no latent factor on the Rosenthal field): 0.52/0.38 um.
  assert.ok(t.includes("0.52") && t.includes("0.38"), t);
  assert.ok(t.includes("Hunt–Lu 1996"), t);
  // modelId and gradientSource are the same string on the field-map path: the source is shown once, not repeated.
  assert.equal(t.split("solidification-front-v1").length - 1, 1, t);
  assert.match(markup, /data-micro-provenance/);
  assert.ok(t.includes("Source: solidification-front-v1"), t);
  // The 285 W / 960 mm/s morphology is dendritic after the physics bump (was Cellular), so the
  // cellular-only "no secondary arms" tooltip is absent; the SDAS correlation name is still shown.
  assert.ok(t.includes("Kirkwood 1985") && !t.includes("cells have no secondary arms"), t);
  assert.ok(t.includes("median of G·R over front samples"), t);
  assert.ok(t.includes("Columnar dendritic (Hunt G/R screening)"), t);
  assert.match(markup, /data-micro-note="regime"/);
  assert.ok(t.includes("Keyhole Mode: outside the conduction regime of the G/R field"), t);
  assert.doesNotMatch(markup, /data-micro-note="screening-fallback"/);
  assert.ok(!t.includes("Unavailable"), t);
});

test("screening-fallback: amber note with Python's reason, tail-length-fallback shown, numbers still rendered", () => {
  const markup = html("screening_fallback_in718_10_3000");
  const t = text(markup);
  assert.match(markup, /data-micro-status="screening-fallback"/);
  assert.match(markup, /data-micro-note="screening-fallback"[^>]*>/);
  assert.ok(t.includes(BLOCKS.screening_fallback_in718_10_3000.reason), t);
  assert.ok(t.includes("tail-length-fallback"), t);
  assert.ok(t.includes("2.25"), t); // PDAS of the 10 W / 3000 mm/s fallback case (P1 fixture, 2026-10-11)
  assert.ok(t.includes("Source: solidification-front-v1 · tail-length-fallback"), t);
  assert.equal(t.split("tail-length-fallback").length - 1, 1, t); // only in the single source line
  assert.doesNotMatch(markup, /data-micro-note="regime"/);
});

test("degenerate-floor: rendered like unavailable (reason, no PDAS/SDAS/morphology/cooling as results)", () => {
  const block = BLOCKS.degenerate_floor_synthetic;
  assert.equal(block.status, "degenerate-floor");
  assert.equal(block.coolingRate_K_s, 1);
  const markup = html("degenerate_floor_synthetic");
  const t = text(markup);
  assert.match(markup, /data-micro-status="degenerate-floor"/);
  assert.match(markup, /data-micro-note="degenerate-floor"/);
  assert.ok(t.includes(block.reason), t);
  assert.ok(t.includes("solidification front degenerate: floor-clamped R/cooling"), t);
  assert.doesNotMatch(markup, /data-micro-metric=/);
  assert.doesNotMatch(markup, /data-micro-provenance/);
  // The clamp-floor numbers and the labels derived from them are not shown.
  assert.ok(!t.includes("19.64") && !t.includes("1.77") && !t.includes("Planar"), t);
});

test("unavailable: reason only, no numbers, no PDAS/SDAS tiles", () => {
  const markup = html("unavailable_no_kinetics");
  const t = text(markup);
  assert.match(markup, /data-micro-status="unavailable"/);
  assert.ok(t.includes("Unavailable — thermal.solidificationKinetics missing or non-finite"), t);
  assert.doesNotMatch(markup, /data-micro-metric=/);
});

test("legacy block without status (old worker Rosenthal block) is not shown as available", () => {
  const legacy = { source: "rosenthal-analytical-screening", G_K_m: 10000, R_m_s: 0.678823, coolingRate_K_s: 6788.23, PDAS_um: 0.881, SDAS_um: 3.508, morphology: "equiaxed", disclaimer: "old" };
  const markup = renderToStaticMarkup(<BuildJobMicrostructurePanel micro={legacy} />);
  const t = text(markup);
  assert.match(markup, /data-micro-status="unavailable"/);
  assert.ok(t.includes("Unavailable — legacy block without status"), t);
  assert.doesNotMatch(markup, /data-micro-metric=/);
  assert.ok(!t.includes("0.88") && !t.includes("equiaxed"), t);
});

test("G/R hint is Python's g_over_r_ratio, not recomputed from rounded G and R", () => {
  // Recomputing G/R from the block's G and R would print 6.1e+8; the panel must print Python's value.
  const block = { ...BLOCKS.available_in718_285_960, g_over_r_ratio: 1.23e9 };
  const t = text(renderToStaticMarkup(<BuildJobMicrostructurePanel micro={block} />));
  assert.ok(t.includes("G/R = 1.2e+9"), t);
  assert.ok(!t.includes("6.1e+8"), t);
});

test("no microstructure block renders nothing", () => {
  assert.equal(renderToStaticMarkup(<BuildJobMicrostructurePanel micro={undefined} />), "");
});
