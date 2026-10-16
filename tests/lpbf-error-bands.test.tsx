import React from "react";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { renderToStaticMarkup } from "react-dom/server";
import {
  BAND_LABEL_LINE,
  bandDisplays,
  bandFor,
  bandKernelOfModelId,
  bandRegimeClass,
  bandSentence,
  bandShort,
  bandSubjectFromProcessWindowCell,
  bandSubjectFromThermal,
  publishedTrackBandsReport,
  summarizeErrorBands,
  type BandCell,
  type ErrorBandsSummary,
} from "../src/data/lpbfErrorBands";
import { PublishedTrackBands } from "../src/components/PublishedTrackBands";
import { ProcessWindowCellDetail } from "../src/components/LpbfProcessWindowMap";
import { createLpbfQualificationReport } from "../src/utils/lpbfQualificationReport";
import { buildLpbfRunReportHtml } from "../src/utils/lpbfRunReport";
import { useMaterialSpecimenStore } from "../src/store/useMaterialSpecimenStore";
import { LPBF_ENGINEERING_DEFAULTS, type LpbfEngineeringState } from "../src/store/useLpbfEngineeringStore";
import type { PythonLpbfBuildJobResult } from "../src/services/pythonComputationService";

const raw = JSON.parse(readFileSync("data/calibration/lpbf-meltpool-error-bands-v1.summary.json", "utf8"));
const summary = summarizeErrorBands(raw) as ErrorBandsSummary;
const fixture = JSON.parse(readFileSync("tests/fixtures/lpbf-error-band-sentences.json", "utf8")) as {
  labelLine: string;
  cases: Array<{ name: string; cell: BandCell | null; value_um: number; quantity: "depth" | "width"; material: string; inputs: Record<string, number> | null; sentence: string; short: string }>;
};

test("the committed summary parses and is screening-only, not validation, with no promotion", () => {
  assert.ok(summary, "summary must parse");
  assert.equal(raw.evidenceKind, "screening-only");
  assert.equal(raw.experimentalValidation, false);
  assert.equal(raw.labelPromotionProposed, "none");
  assert.equal(summary.labelLine, BAND_LABEL_LINE);
  assert.equal(BAND_LABEL_LINE, "Screening only · typical published-data error shown; transfer to another lab not established");
  assert.equal(summary.cells.length, 96);
  assert.ok(summary.cells.every((c) => !c.loso || !("bands" in c.loso)), "row-level held-out bands stay in the full artefact");
});

test("the summary is refused when it is not screening-only, claims validation, or loses the approved label line", () => {
  assert.equal(summarizeErrorBands(null), null);
  assert.equal(summarizeErrorBands({ ...raw, evidenceKind: "validated-simulation" }), null);
  assert.equal(summarizeErrorBands({ ...raw, experimentalValidation: true }), null);
  assert.equal(summarizeErrorBands({ ...raw, labelPromotionProposed: "Validated simulation" }), null);
  assert.equal(summarizeErrorBands({ ...raw, labelLine: "Screening only" }), null);
  assert.equal(summarizeErrorBands({ ...raw, schema: "other" }), null);
  const broken = JSON.parse(JSON.stringify(raw));
  broken.cells[0].state = "calibrated";
  assert.equal(summarizeErrorBands(broken), null);
});

test("the summary was measured against the pinned implementation fingerprint (regenerate after a physics bump)", () => {
  const pin = readFileSync("python/lpbf_implementation_fingerprint.expected", "utf8").trim();
  assert.equal(summary.implementationHash, pin);
});

test("bandSentence and bandShort are byte-identical to the Python golden fixture", () => {
  assert.equal(fixture.labelLine, BAND_LABEL_LINE);
  const states = new Set<string>();
  for (const c of fixture.cases) {
    assert.equal(bandSentence(c.cell, c.value_um, c.quantity, c.inputs, { material: c.material, nominalCoverage: 0.8 }), c.sentence, c.name);
    assert.equal(bandShort(c.cell, c.quantity), c.short, c.name);
    states.add(c.cell ? c.cell.state : "missing");
    // honesty: never a bare +/- x %, always n and sources, always the approved label line last
    assert.ok(c.sentence.endsWith(BAND_LABEL_LINE));
    assert.doesNotMatch(c.sentence, /±/);
    assert.match(c.sentence, /\d+ rows/);
    assert.match(c.sentence, /source/);
  }
  assert.deepEqual([...states].sort(), ["band", "band-under-covers", "insufficient-data", "missing"]);
});

test("regime class thresholds and lookup match the artefact (family, regime class, quantity)", () => {
  assert.equal(bandRegimeClass(14.99), "conduction");
  assert.equal(bandRegimeClass(15), "transition");
  assert.equal(bandRegimeClass(19.99), "transition");
  assert.equal(bandRegimeClass(20), "keyhole");
  assert.equal(bandRegimeClass(30), "keyhole");
  // P7b bands (2026-10-14): n 730 (was 731), coverage 65 % (was 68 %).
  const c = bandFor(summary, "eagar-tsai", "316L Stainless Steel", "all", "depth") as BandCell;
  assert.equal(c.n, 730);
  assert.equal(c.nSources, 3);
  assert.equal(c.state, "band-under-covers");
  // SOL-T bands (2026-10-16): coverage 66 % (P7b 65 %).
  assert.equal(Math.round((c.loso?.coverageEqualWeight ?? 0) * 100), 66);
  assert.equal(bandFor(summary, "eagar-tsai", "AlSi10Mg", "all", "depth"), null);
  assert.equal(bandKernelOfModelId("rosenthal-screening-v1"), "rosenthal");
  assert.equal(bandKernelOfModelId("goldak-half-space-v3"), "goldak");
  assert.equal(bandKernelOfModelId("eagar-tsai-v2"), "eagar-tsai");
  assert.equal(bandKernelOfModelId("something"), null);
});

// SYNTHETIC thermal-solver-shaped results: exercise the surfaces, not any physics.
const thermal = (over: Record<string, unknown> = {}, geo: Record<string, unknown> = {}) => ({
  material: "316L Stainless Steel",
  processParameters: { heatSource: "eagar-tsai", normalizedEnthalpy: 27.5, laserPower_W: 200, scanSpeed_mm_s: 900, beamDiameter_um: 80, ...over },
  meltPoolGeometry: { width_um: 183.3, depth_um: 119.6, extentStatus: "computed", ...geo },
});

test("the Build Job / Melt Pool lab block prints the short form and the full sentence as plain text", () => {
  const out = renderToStaticMarkup(<PublishedTrackBands thermal={thermal()} summary={summary} />);
  assert.ok(out.includes('data-testid="band-depth"'));
  assert.ok(out.includes('data-testid="band-width"'));
  const displays = bandDisplays(summary, bandSubjectFromThermal(thermal()));
  assert.equal(displays.length, 2);
  for (const d of displays) {
    assert.ok(out.includes(d.short.replace(/&/g, "&amp;")), d.short);
    assert.ok(out.includes(`>${d.sentence}</p>`.replace(/&/g, "&amp;")) || out.includes(d.sentence), "sentence is plain text, not only a title attribute");
    assert.match(d.sentence, new RegExp(BAND_LABEL_LINE.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  }
  // the measured held-out coverage and the per-source medians are always printed
  const depth = displays.find((d) => d.quantity === "depth")!;
  assert.match(depth.sentence, /held-out source fell inside/);
  assert.match(depth.sentence, /per-source median error/);
  // keyboard: a native disclosure (summary is focusable) rather than a hover-only title
  assert.match(out, /<details[^>]*><summary/);
});

test("3-state display: the three states are reachable from the committed artefact and none hides n or the sources", () => {
  const states = new Map<string, string>();
  const cases: Array<[string, Record<string, unknown>]> = [
    ["316L ET transition", thermal({ normalizedEnthalpy: 20 })],
    ["316L ET keyhole", thermal({ normalizedEnthalpy: 40 })],
    ["Ti64 ET conduction", { ...thermal({ normalizedEnthalpy: 8 }), material: "Ti-6Al-4V" }],
    ["IN718 rosenthal transition", { ...thermal({ heatSource: "rosenthal", normalizedEnthalpy: 20 }), material: "Inconel 718" }],
  ];
  for (const [name, t] of cases) {
    for (const d of bandDisplays(summary, bandSubjectFromThermal(t))) {
      states.set(`${name} ${d.quantity}`, d.state);
      assert.match(d.sentence, /\d+ rows/);
      assert.match(d.sentence, /source/);
      assert.ok(d.sentence.endsWith(BAND_LABEL_LINE));
    }
  }
  const seen = new Set(states.values());
  assert.ok(seen.has("band-under-covers"), JSON.stringify([...states]));
  assert.ok(seen.has("insufficient-data") || seen.has("band"), JSON.stringify([...states]));
  // every depth cell is under-covers or insufficient today: no depth cell reaches the 0.70 held-out coverage floor
  // P7b bands (2026-10-14): one depth cell reaches the coverage floor (Eagar-Tsai 316L conduction); every other depth cell stays below it.
  const depthBand = summary.cells.filter((c) => c.quantity === "depth" && c.state === "band");
  // SOL-T bands (2026-10-16): the Eagar-Tsai 316L conduction cell no longer reaches it, so none does.
  assert.deepEqual(depthBand.map((c) => [c.kernel, c.family, c.regime]), []);
});

test("IN718 (Ni family) names the pooled alloys and the sentinel source", () => {
  const t = { ...thermal({ heatSource: "rosenthal", normalizedEnthalpy: 20 }), material: "Inconel 718" };
  const depth = bandDisplays(summary, bandSubjectFromThermal(t)).find((d) => d.quantity === "depth")!;
  assert.match(depth.sentence, /Pooled alloys in this cell: Inconel 625, Inconel 718/);
  assert.match(depth.sentence, /NIST AMB2022-03 \(catalog sentinel\)/);
});

test("nothing is rendered when the summary is absent, the extent is unresolved, or the subject is not a thermal result", () => {
  assert.equal(renderToStaticMarkup(<PublishedTrackBands thermal={thermal()} summary={null} />), "");
  assert.equal(renderToStaticMarkup(<PublishedTrackBands thermal={thermal({}, { extentStatus: "not-computed" })} summary={summary} />), "");
  assert.equal(renderToStaticMarkup(<PublishedTrackBands thermal={{}} summary={summary} />), "");
  assert.equal(renderToStaticMarkup(<PublishedTrackBands thermal={null} summary={summary} />), "");
  assert.equal(renderToStaticMarkup(<PublishedTrackBands thermal={thermal()} summary={null} />).includes("band"), false);
  assert.equal(bandDisplays(null, bandSubjectFromThermal(thermal())).length, 0);
});

test("an input outside the published range of the cell says so", () => {
  const far = thermal({ laserPower_W: 5000 });
  const d = bandDisplays(summary, bandSubjectFromThermal(far));
  assert.ok(d.every((x) => x.sentence.includes("input outside the published range of this cell")));
  const inside = bandDisplays(summary, bandSubjectFromThermal(thermal()));
  assert.ok(inside.every((x) => !x.sentence.includes("outside the published range")));
});

const pwCell = {
  iP: 0, iV: 0, power_W: 200, speed_mm_s: 900, verdict: "risky", headline: "h", dominantGate: null, blockingGates: [], riskGates: [],
  advisoryGates: [], unavailableGates: [], reasons: [], extentStatus: "computed", insideLiteratureBox: true, normalizedEnthalpy: 20,
  ballingBand: null, width_um: 150.2, depth_um: 100.4, error: null,
} as never;

test("the process-window detail panel prints the sentence for the selected cell", () => {
  const ctx = { alloyId: "ss316l", modelId: "rosenthal-screening-v1", beamDiameter_um: 80 };
  const out = renderToStaticMarkup(<ProcessWindowCellDetail cell={pwCell} advisories={[]} bandContext={ctx} bandSummary={summary} />);
  assert.ok(out.includes('data-testid="pw-band-depth"'));
  const subject = bandSubjectFromProcessWindowCell(pwCell, ctx)!;
  const depth = bandDisplays(summary, subject).find((d) => d.quantity === "depth")!;
  assert.ok(out.includes(depth.sentence));
  assert.match(depth.sentence, /^depth ≈ 100 µm/);
  // no band context or no summary: nothing extra in the panel
  assert.ok(!renderToStaticMarkup(<ProcessWindowCellDetail cell={pwCell} advisories={[]} />).includes("pw-band"));
  assert.ok(!renderToStaticMarkup(<ProcessWindowCellDetail cell={pwCell} advisories={[]} bandContext={ctx} bandSummary={null} />).includes("pw-band"));
  // an unresolved extent carries no number and therefore no band
  assert.equal(bandSubjectFromProcessWindowCell({ ...(pwCell as object), extentStatus: "floored" } as never, ctx), null);
  assert.equal(bandSubjectFromProcessWindowCell(pwCell, { ...ctx, alloyId: "unknown" }), null);
});

test("the run report carries a Published-track error bands block with sources, DOIs and the artefact id and sha", () => {
  const spec = useMaterialSpecimenStore.getState().activeSpecimen;
  const engineering = { settings: { ...LPBF_ENGINEERING_DEFAULTS }, mode: "standard", job: undefined, error: "", busy: false, material: "", properties: "", measurements: "", specimen: "", uncertainty: "", holdout: "unknown", width: "", depth: "", source: "", submittedSignature: "", resultSignature: "", submittedInput: undefined } as unknown as LpbfEngineeringState;
  const ctx = { buildId: "B-1", machine: "M", powderLot: "L", powderCondition: "", heatTreatment: "", measurementMethod: "", notes: "" };
  const job = { success: true, engine: "fixture", modelId: "rosenthal-screening-v1", assumptions: [], alloyId: "ss316l", computeTimeMs: 1, slicer: {}, thermal: thermal({ heatSource: "rosenthal", normalizedEnthalpy: 20 }), verdict: { verdict: "risky", headline: "h", reasons: [], gates: [], blockingGates: [], riskGates: [], advisoryGates: [], unavailableGates: [], advisories: [] } } as unknown as PythonLpbfBuildJobResult;
  const report = createLpbfQualificationReport(spec, ctx, engineering, job, [], summary);
  assert.ok(report.publishedTrackBands);
  assert.equal(report.publishedTrackBands!.bandsId, summary.bandsId);
  assert.equal(report.publishedTrackBands!.experimentalValidation, false);
  const html = buildLpbfRunReportHtml(report, { buildJob: job }, { createdAt: "2026-01-02T03:04:05.000Z", dossierSha256: null });
  assert.ok(html.includes("Published-track error bands"));
  assert.ok(html.includes(summary.bandsId));
  assert.ok(html.includes(summary.contentSha256));
  assert.ok(html.includes("not a tolerance and not validation"));
  assert.ok(html.includes("10.5281/zenodo.16979848"), "Hofmann DOI from the artefact");
  for (const e of report.publishedTrackBands!.entries) assert.ok(html.includes(e.sentence.replace(/&/g, "&amp;")), e.quantity);
  // no build job, no summary, or an unresolved extent: no block (nothing invented)
  assert.equal(createLpbfQualificationReport(spec, ctx, engineering, null, [], summary).publishedTrackBands, null);
  assert.equal(createLpbfQualificationReport(spec, ctx, engineering, job, [], null).publishedTrackBands, null);
  const noBlock = buildLpbfRunReportHtml(createLpbfQualificationReport(spec, ctx, engineering, job, [], null), { buildJob: job }, { createdAt: "2026-01-02T03:04:05.000Z", dossierSha256: null });
  assert.ok(!noBlock.includes("Published-track error bands"));
  assert.equal(publishedTrackBandsReport(summary, bandSubjectFromThermal(thermal({}, { extentStatus: "floored" }))), null);
});

test("surfaces: the Build Job card, the Melt Pool lab and the process-window detail include the block; nothing reads a band to change a label", () => {
  const lab = readFileSync("src/components/3d-distortion-lab/IndustrialLPBFDecisionLab.tsx", "utf8");
  assert.match(lab, /<PublishedTrackBands thermal=\{thermal\} \/>/);
  const melt = readFileSync("src/components/3d-distortion-lab/MeltPool3DCrossSectionLab.tsx", "utf8");
  assert.match(melt, /<PublishedTrackBands thermal=\{pyResult\} \/>/);
  const pw = readFileSync("src/components/LpbfProcessWindowMap.tsx", "utf8");
  assert.match(pw, /bandSubjectFromProcessWindowCell\(cell, bandContext\)/);
  const comp = readFileSync("src/components/PublishedTrackBands.tsx", "utf8");
  assert.doesNotMatch(comp, /localStorage|sessionStorage|fetch\(/);
  // the data module is imported by display and report code only, never by the store, the verdict or the gates
  for (const f of ["src/store/useLpbfBuildJobStore.ts", "src/utils/lpbfProcessWindowVerdict.ts"]) {
    try { assert.doesNotMatch(readFileSync(f, "utf8"), /lpbfErrorBands/); } catch (e) { if ((e as NodeJS.ErrnoException).code !== "ENOENT") throw e; }
  }
});
