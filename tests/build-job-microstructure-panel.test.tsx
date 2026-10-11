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

test("available (conduction-field interface): numbers, correlation names, provenance, no regime note, no fallback note", () => {
  const markup = html("available_in718_150_1200");
  const t = text(markup);
  assert.match(markup, /data-micro-status="available"/);
  // P6 (2026-10-11): the available fixture is the conduction point 150 W / 1200 mm/s (the former 285 W / 960 mm/s
  // point serves null G/R because its depth comes from the Fabbro keyhole leg). P7a: the PDAS scalar and SDAS are
  // null; this IN718 point lies outside the Ghosh 2017 validity range, so the PDAS tile shows the reason, not a number.
  assert.equal(BLOCKS.available_in718_150_1200.PDAS_um, null);
  assert.equal(BLOCKS.available_in718_150_1200.SDAS_um, null);
  assert.ok(!t.includes("Hunt–Lu 1996"), t);
  assert.ok(t.includes("PDAS BAND") || t.includes("PDAS band"), t);
  assert.ok(t.includes(BLOCKS.available_in718_150_1200.pdasBand_um ? "Ni-Nb model alloy, Ghosh 2017" : "Ghosh 2017 validity range"), t);
  assert.ok(t.includes("no sourced SDAS prefactor"), t);
  // modelId (solidification-front-v1) and gradientSource (conduction-field-interface) are both shown once.
  assert.equal(t.split("solidification-front-v1").length - 1, 1, t);
  assert.equal(t.split("conduction-field-interface").length - 1, 1, t);
  assert.match(markup, /data-micro-provenance/);
  assert.ok(t.includes("Source: solidification-front-v1 · conduction-field-interface"), t);
  assert.ok(!t.includes("cells have no secondary arms"), t);
  assert.ok(t.includes("median of G·R over front samples"), t);
  assert.ok(t.includes("Columnar dendritic (Hunt G/R screening)"), t);
  assert.doesNotMatch(markup, /data-micro-note="regime"/);
  assert.doesNotMatch(markup, /data-micro-note="screening-fallback"/);
  assert.ok(!t.includes("Unavailable"), t);
});

test("unavailable with the thermal reason: keyhole-leg depth and unsampled interface (P6), no numbers", () => {
  for (const [name, needle] of [
    ["unavailable_keyhole_leg_in718_285_960", "Fabbro keyhole leg"],
    ["unavailable_few_samples_in718_10_3000", "fewer than 3 solidifying rear-liquidus samples"],
  ] as const) {
    const block = BLOCKS[name];
    assert.equal(block.status, "unavailable");
    assert.equal(block.PDAS_um, null);
    const markup = html(name);
    const t = text(markup);
    assert.match(markup, /data-micro-status="unavailable"/);
    assert.ok(t.includes(`Unavailable — ${block.reason}`), t);
    assert.ok(t.includes(needle), t);
    assert.doesNotMatch(markup, /data-micro-metric=/);
  }
});

test("screening-fallback (legacy payload shape, no fixture since P6): amber note with the reason, numbers rendered", () => {
  const legacy = { ...BLOCKS.available_in718_150_1200, status: "screening-fallback", gradientSource: "tail-length-fallback", usedFieldMap: false, reason: "legacy tail-length heuristic" };
  const markup = renderToStaticMarkup(<BuildJobMicrostructurePanel micro={legacy} />);
  const t = text(markup);
  assert.match(markup, /data-micro-status="screening-fallback"/);
  assert.match(markup, /data-micro-note="screening-fallback"[^>]*>/);
  assert.ok(t.includes("legacy tail-length heuristic"), t);
  assert.ok(t.includes("Source: solidification-front-v1 · tail-length-fallback"), t);
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
  // Recomputing G/R from the block's G and R would print the fixture's own ratio; the panel must print Python's value.
  const block = { ...BLOCKS.available_in718_150_1200, g_over_r_ratio: 1.23e9 };
  const t = text(renderToStaticMarkup(<BuildJobMicrostructurePanel micro={block} />));
  assert.ok(t.includes("G/R = 1.2e+9"), t);
  assert.ok(!t.includes("6.1e+8"), t);
});

test("no microstructure block renders nothing", () => {
  assert.equal(renderToStaticMarkup(<BuildJobMicrostructurePanel micro={undefined} />), "");
});
