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
const LABEL_PREFIX = "Literature estimate (screening)";

test("available (IN718): label chip as text, k with citation, Nb band, risk class, ratio, copied G/R, validity, upper bound", () => {
  const block = BLOCKS.available_in718_150_1200;
  assert.equal(block.status, "available");
  const markup = html("available_in718_150_1200");
  const t = text(markup);
  assert.match(markup, /data-seg-status="available"/);
  assert.match(markup, /data-seg-label/);
  assert.ok(t.includes(block.evidenceLabel), t);
  assert.ok(block.evidenceLabel.startsWith(LABEL_PREFIX));
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
  // Process coupling: G, R and morphology copied from the build job's microstructure block.
  assert.match(markup, /data-seg-coupling="available"/);
  assert.ok(t.includes(block.processCoupling.G_K_m.toExponential(2)), t);
  assert.ok(t.includes(block.processCoupling.R_m_s.toFixed(4)), t);
  assert.ok(t.includes(block.processCoupling.morphology), t);
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

test("degenerate-floor microstructure: composition result still shown, process coupling reason only", () => {
  const block = BLOCKS.in718_degenerate_floor_synthetic;
  assert.equal(block.processCoupling.status, "unavailable");
  const markup = html("in718_degenerate_floor_synthetic");
  const t = text(markup);
  assert.match(markup, /data-seg-coupling="unavailable"/);
  assert.ok(t.includes(`Process coupling unavailable — ${block.processCoupling.reason}`), t);
  assert.ok(!t.includes("K/m"), t);
});

test("available (IN625, Cieslak 1988 k + DuPont 1996 C_e): binary band, no risk class, no carbon columns, phase identity and validity shown", () => {
  const block = BLOCKS.in625_available;
  assert.equal(block.status, "available");
  const markup = html("in625_available");
  const t = text(markup);
  assert.match(markup, /data-seg-status="available"/);
  assert.ok(block.evidenceLabel.startsWith(LABEL_PREFIX));
  assert.ok(t.includes(block.evidenceLabel), t);
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
    assert.equal(p.pseudoTernaryAtCmax.status, "not-modelled");
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

test("rapid solidification k(V) (IN718): shown beside the unchanged upper bound with V_D range, label and notes", () => {
  const block = BLOCKS.available_in718_150_1200;
  const rs = block.rapidSolidification;
  assert.equal(rs.status, "available");
  assert.equal(rs.replacesUpperBound, false);
  const markup = html("available_in718_150_1200");
  const t = text(markup);
  assert.match(markup, /data-seg-rapid="available"/);
  assert.ok(rs.evidenceLabel.startsWith(LABEL_PREFIX));
  assert.ok(t.includes(rs.evidenceLabel), t);
  assert.ok(t.includes("V D = 0.23–0.31 m/s"), t);
  assert.ok(t.includes(`R = ${rs.R_m_s.toFixed(4)} m/s`), t);
  assert.ok(t.includes(`k(R) = ${rs.kEff.min.toFixed(3)} to ${rs.kEff.max.toFixed(3)}`), t);
  for (const row of rs.byVD) {
    for (const p of row.band) {
      const cell = `${(p.binary.fGammaLavesConstituent * 100).toFixed(1)} % / ${(p.pseudoTernaryAtCmax.fGammaLavesConstituent * 100).toFixed(1)} %`;
      assert.ok(t.includes(cell), `${row.V_D_m_s} ${p.label} ${cell}`);
    }
    assert.ok(t.includes(`${row.segregation.coreRatioToNominal.toFixed(3)} (V_D ${row.V_D_m_s.toFixed(2)} m/s)`), t);
  }
  // the equilibrium-k upper bound rows are still rendered with their own numbers
  for (const p of block.band) assert.ok(t.includes(`${(p.binaryUpperBound.fGammaLavesConstituent * 100).toFixed(1)} %`), t);
  assert.match(markup, /data-seg-rapid-notes/);
  assert.ok(t.includes(rs.V_D_m_s.nature) && rs.V_D_m_s.nature.includes("no experimental V_D"), t);
  assert.ok(t.includes(rs.extrapolationNote) && rs.extrapolationNote.startsWith("Extrapolation"), t);
  assert.ok(t.includes(rs.kTransferNote), t);
  // IN718: no LPBF measurement among the sources read; said so, no comparison numbers.
  assert.match(markup, /data-seg-lpbf="unavailable"/);
  assert.ok(t.includes(`LPBF observations: none — ${block.lpbfObservations.reason}`), t);
  assert.doesNotMatch(markup, /data-seg-lpbf-comparison/);
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

test("IN625: k(V) estimate and as-built LPBF observations with the non-discriminating comparison", () => {
  const block = BLOCKS.in625_available;
  const rs = block.rapidSolidification;
  const obs = block.lpbfObservations;
  assert.equal(rs.status, "available");
  assert.equal(obs.status, "available");
  const markup = html("in625_available");
  const t = text(markup);
  for (const row of rs.byVD) {
    for (const p of row.band) {
      assert.equal(p.pseudoTernaryAtCmax, undefined);
      assert.ok(t.includes(`${(p.binary.fGammaLavesConstituent * 100).toFixed(1)} %`), t);
    }
  }
  assert.match(markup, /data-seg-lpbf="available"/);
  for (const ob of obs.observations) {
    assert.ok(t.includes(ob.locator), ob.locator);
  }
  assert.ok(t.includes("Nb 2.81 to 5.84 wt%"), t);
  const c = obs.comparison;
  assert.match(markup, /data-seg-lpbf-comparison/);
  assert.ok(t.includes(`equilibrium k ${c.equilibriumK.coreRatioToNominal.toFixed(3)}`), t);
  assert.ok(t.includes(`EDS lowest ${c.measured.lowestRatioToNominal.toFixed(3)}`), t);
  assert.ok(t.includes("measured fraction: none reported"), t);
  assert.ok(t.includes(c.note) && c.note.startsWith("Non-discriminating"), t);
  for (const word of ["Validated", "Calibrated"]) assert.ok(!t.includes(word), word);
});

test("not-applicable (316L): reason only, no numbers", () => {
  const block = BLOCKS.ss316l_not_applicable;
  assert.equal(block.status, "not-applicable");
  const markup = html("ss316l_not_applicable");
  const t = text(markup);
  assert.match(markup, /data-seg-status="not-applicable"/);
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
  assert.match(withSeg, /data-micro-status="available"[\s\S]*data-seg-status="available"/);
  assert.match(withSeg, /<section[^>]*aria-labelledby="[^"]+"/);
  const without = renderToStaticMarkup(<BuildJobMicrostructurePanel micro={micro} />);
  assert.doesNotMatch(without, /data-seg-status/);
  // Composition-only result is still shown when the microstructure block is missing (e.g. old payload).
  const noMicro = renderToStaticMarkup(
    <BuildJobMicrostructurePanel micro={undefined} segregation={BLOCKS.available_in718_150_1200} />,
  );
  assert.match(noMicro, /data-seg-status="available"/);
  assert.equal(renderToStaticMarkup(<BuildJobMicrostructurePanel micro={undefined} />), "");
});
