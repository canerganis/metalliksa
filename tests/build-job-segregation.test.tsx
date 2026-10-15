import React from "react";
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { renderToStaticMarkup } from "react-dom/server";
import { BuildJobSegregationPanel } from "../src/components/3d-distortion-lab/BuildJobSegregationPanel";
import { BuildJobMicrostructurePanel } from "../src/components/3d-distortion-lab/BuildJobMicrostructurePanel";

// Real Python output: python/test_lpbf_build_job.py check_segregation_fixture() fails when this file differs from
// build_job_segregation (regenerate with `python test_lpbf_build_job.py --write-segregation-fixture`).
const BLOCKS = JSON.parse(readFileSync(new URL("./fixtures/build-job-segregation-blocks.json", import.meta.url), "utf8"));
const MICRO = JSON.parse(readFileSync(new URL("./fixtures/build-job-microstructure-blocks.json", import.meta.url), "utf8"));
const html = (name: string) => {
  assert.ok(BLOCKS[name], name);
  return renderToStaticMarkup(<BuildJobSegregationPanel segregation={BLOCKS[name]} />);
};
const text = (markup: string) =>
  markup
    .replace(/<[^>]+>/g, " ")
    .replace(/&#x27;/g, "'")
    .replace(/&amp;/g, "&")
    .replace(/&gt;/g, ">")
    .replace(/&lt;/g, "<")
    .replace(/\s+/g, " ");
const LABEL_PREFIX = "Literature estimate";

test("available (IN718): label chip as text, k with citation, Nb band, risk class, ratio, copied G/R, validity, upper bound", () => {
  const block = BLOCKS.available_in718_150_1200;
  assert.equal(block.status, "computed");
  const markup = html("available_in718_150_1200");
  const t = text(markup);
  assert.match(markup, /data-seg-status="computed"/);
  assert.ok(t.includes("k Nb = 0.45"), t);
  assert.ok(t.includes("DuPont, C.V. Robino, A.R. Marder") && t.includes("Table 2"), t);
  // Nb band rows min / nominal / max with Python's fractions (%, one decimal).
  for (const p of block.band) {
    assert.match(markup, new RegExp(`data-seg-band-row="${p.label}"`));
    assert.ok(t.includes(`${(p.binaryUpperBound.fGammaLavesConstituent * 100).toFixed(1)} %`), `${p.label} ${t}`);
    assert.ok(t.includes(`${(p.pseudoTernaryAtCmax.fGammaLavesConstituent * 100).toFixed(1)} %`), `${p.label} ${t}`);
  }
  assert.ok(t.includes("upper bound"), t);
  assert.ok(t.includes(`Laves risk class: ${block.riskClass}`), t);
  assert.ok(t.includes("core k·C 0 = 0.45"), t);
  assert.ok(t.includes("capped at the γ/Laves composition"), t);
  assert.match(markup, /data-solidification-envelope/);
  assert.match(t, /no admitted source/);
  // Validity warning and the upper-bound wording.
  assert.match(markup, /data-seg-validity/);
  assert.ok(t.includes("Outside the source regime"), t);
  for (const r of block.validity.outsideSourceCompositionReasons) assert.ok(t.includes(r), r);
  assert.match(markup, /data-seg-upper-bound/);
  assert.ok(t.includes(block.upperBoundNote), t);
  // The source's own measurements disagree with the model in both directions (D97 Fig. 9b, conference paper): shown next to it.
  assert.match(markup, /data-seg-source-agreement/);
  assert.ok(t.includes(block.sourceAgreementNote) && block.sourceAgreementNote.includes("Fig. 9b"), t);
  assert.ok(t.includes("binary; model upper bound over C only"), t);
  assert.ok(!t.includes("C = 0 (upper bound)"), t);
  assert.match(markup, /data-seg-quantity/);
  assert.ok(t.includes("not phase fractions"), t);
  assert.ok(t.includes("positive by construction"), t);
  for (const word of ["Validated", "Calibrated", "Measured"]) assert.ok(!t.includes(word), word);
});

test("unavailable front keeps composition results and displays per-quantity reasons", () => {
  const block = BLOCKS.in718_degenerate_floor_synthetic;
  const markup = html("in718_degenerate_floor_synthetic");
  assert.match(markup, /data-solidification-envelope/);
  assert.match(markup, /data-seg-band-row/);
  assert.equal(block.processCoupling.quantities.normalSpeed.value, null);
});

test("available (IN625, Cieslak 1988 k + DuPont 1996 C_e): binary band, no risk class, no carbon columns, phase identity and validity shown", () => {
  const block = BLOCKS.in625_available;
  assert.equal(block.status, "computed");
  const markup = html("in625_available");
  const t = text(markup);
  assert.match(markup, /data-seg-status="computed"/);
  assert.ok(t.includes("k Nb = 0.51"), t);
  assert.ok(t.includes("M.J. Cieslak") && t.includes("Table VIII"), t);
  // k sensitivity (C88 Table VII and the D96 overlay value) and the C88 computed-vs-measured comparison are shown.
  assert.match(markup, /data-seg-k-sensitivity/);
  assert.ok(t.includes("k Nb = 0.54") && t.includes("k Nb = 0.46"), t);
  assert.match(markup, /data-seg-source-comparison/);
  for (const r of block.sourceComparison.c88) {
    assert.ok(t.includes(`alloy ${r.alloy}: ${(r.fComputed * 100).toFixed(1)} % vs ${(r.fMeasured * 100).toFixed(1)} %`), t);
  }
  for (const p of block.band) {
    assert.match(markup, new RegExp(`data-seg-band-row="${p.label}"`));
    assert.ok(t.includes(`${(p.binaryUpperBound.fGammaLavesConstituent * 100).toFixed(1)} %`), `${p.label} ${t}`);
    assert.equal(p.pseudoTernaryAtCmax.status, "unavailable");
    assert.ok(t.includes(`— ${p.pseudoTernaryAtCmax.reason}`), t);
  }
  // No Laves risk class: the rule explaining why is shown instead, never an empty class.
  assert.equal(block.riskClass, null);
  assert.match(markup, /data-seg-risk="none"/);
  assert.ok(!t.includes("Laves risk class:"), t);
  assert.ok(t.includes(block.riskClassRule), t);
  assert.doesNotMatch(markup, /data-seg-sensitivity/);
  assert.match(markup, /data-seg-phase-identity/);
  assert.ok(t.includes(block.validity.phaseIdentityNote), t);
  assert.ok(t.includes(block.validity.ceTransferNote), t);
  assert.ok(t.includes(`Outside the source regime — ${block.validity.outsideSourceRegimeReason}`), t);
  for (const r of block.validity.outsideSourceCompositionReasons) assert.ok(t.includes(r), r);
  assert.ok(t.includes(block.sourceAgreementNote) && block.sourceAgreementNote.includes("0.3-1.3 vol%"), t);
  for (const word of ["Validated", "Calibrated"]) assert.ok(!t.includes(word), word);
});

test("SOL-A default front withholds rapid-solidification values while keeping equilibrium upper bounds", () => {
  const block = BLOCKS.available_in718_150_1200;
  const markup = html("available_in718_150_1200");
  assert.equal(block.rapidSolidification.status, "unavailable");
  assert.match(markup, /data-seg-rapid="unavailable"/);
  assert.doesNotMatch(markup, /data-seg-rapid-band|data-seg-rapid-core/);
  for (const p of block.band) assert.ok(text(markup).includes(`${(p.binaryUpperBound.fGammaLavesConstituent * 100).toFixed(1)} %`));
});

test("rapid solidification without a usable R: reason only, no k(V) numbers", () => {
  const block = BLOCKS.in718_degenerate_floor_synthetic;
  assert.equal(block.rapidSolidification.status, "unavailable");
  const markup = html("in718_degenerate_floor_synthetic");
  const t = text(markup);
  assert.match(markup, /data-seg-rapid="unavailable"/);
  assert.ok(t.includes(`Unavailable — ${block.rapidSolidification.reason}`), t);
  assert.doesNotMatch(markup, /data-seg-rapid-band|data-seg-rapid-core/);
});

test("IN625 observations stay visible while unavailable R withholds the k(V) comparison", () => {
  const block = BLOCKS.in625_available;
  const markup = html("in625_available");
  const t = text(markup);
  assert.equal(block.rapidSolidification.status, "unavailable");
  assert.match(markup, /data-seg-lpbf="computed"/);
  for (const ob of block.lpbfObservations.observations) assert.ok(t.includes(ob.locator), ob.locator);
  assert.match(markup, /data-seg-rapid="unavailable"/);
});

test("not-applicable (316L): reason only, no numbers", () => {
  const block = BLOCKS.ss316l_not_applicable;
  assert.equal(block.status, "not-requested");
  const markup = html("ss316l_not_applicable");
  const t = text(markup);
  assert.match(markup, /data-seg-status="not-requested"/);
  assert.ok(t.includes(`Not applicable — ${block.reason}`), t);
  assert.doesNotMatch(markup, /data-seg-band|data-seg-label|data-seg-coupling/);
  assert.ok(!/\d/.test(t.replace(/316L/g, "")), t);
});

test("unknown status or malformed block is never shown as available", () => {
  const markup = renderToStaticMarkup(
    <BuildJobSegregationPanel segregation={{ ...BLOCKS.available_in718_150_1200, status: "ok" }} />,
  );
  assert.match(markup, /data-seg-status="unavailable"/);
  assert.doesNotMatch(markup, /data-seg-band/);
  assert.equal(renderToStaticMarkup(<BuildJobSegregationPanel segregation={null} />), "");
  assert.equal(renderToStaticMarkup(<BuildJobSegregationPanel segregation={[1, 2]} />), "");
});

test("rendered inside the microstructure panel via the optional prop, absent without it", () => {
  const micro = MICRO.available_in718_150_1200;
  const withSeg = renderToStaticMarkup(
    <BuildJobMicrostructurePanel micro={micro} segregation={BLOCKS.available_in718_150_1200} />,
  );
  assert.match(withSeg, /data-solidification-envelope[\s\S]*data-seg-status="computed"/);
  assert.match(withSeg, /<section[^>]*aria-labelledby="[^"]+"/);
  const without = renderToStaticMarkup(<BuildJobMicrostructurePanel micro={micro} />);
  assert.doesNotMatch(without, /data-seg-status/);
  // Composition-only result is still shown when the microstructure block is missing (e.g. old payload).
  const noMicro = renderToStaticMarkup(
    <BuildJobMicrostructurePanel micro={undefined} segregation={BLOCKS.available_in718_150_1200} />,
  );
  assert.match(noMicro, /data-seg-status="computed"/);
  assert.equal(renderToStaticMarkup(<BuildJobMicrostructurePanel micro={undefined} />), "");
});
