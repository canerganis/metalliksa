import React from "react";
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { renderToStaticMarkup } from "react-dom/server";
import { THIN_SPACE, displayUnit, formatScientific, formatSignificant, formatWithUnit } from "../src/utils/numberFormat";
import { MeltPoolSummaryCard } from "../src/components/3d-distortion-lab/MeltPoolSummaryCard";
import { ProcessWindowCellDetail, ProcessWindowResultView } from "../src/components/LpbfProcessWindowMap";
import { cellGateSentences, noPrintableExplanation, noPrintableNoteText } from "../src/data/lpbfProcessWindow";
import type { SimulationResult } from "../src/services/lpbfSimulationService";
import type { LpbfProcessWindowCell, LpbfProcessWindowResponse } from "../src/services/pythonComputationService";

const read = (rel: string) => readFileSync(new URL(`../${rel}`, import.meta.url), "utf8");

// ---- Item 2: one shared formatter ---------------------------------------------------------------------------
test("formatScientific writes 1.7 × 10⁷, never 1.7e+7, and keeps the stated digits", () => {
  assert.equal(formatScientific(1.7e7, 2), "1.7 × 10⁷");
  assert.equal(formatScientific(2e7, 2), "2.0 × 10⁷");
  assert.equal(formatScientific(5.3e-5, 1), "5 × 10⁻⁵");
  assert.equal(formatScientific(-1234567, 3), "-1.23 × 10⁶");
  assert.equal(formatScientific(Number.NaN), "—");
  assert.doesNotMatch(formatScientific(1.7e7, 2), /e[+-]/);
});

test("formatSignificant: 3 significant digits by default, scientific only for very large or small values", () => {
  assert.equal(formatSignificant(123.456), "123");
  assert.equal(formatSignificant(0.012345), "0.0123");
  assert.equal(formatSignificant(1234.5), "1,230");
  assert.equal(formatSignificant(45), "45");
  assert.equal(formatSignificant(0), "0");
  assert.equal(formatSignificant(1.7e7), "1.70 × 10⁷");
  assert.equal(formatSignificant(2.5e-4), "2.50 × 10⁻⁴");
  assert.equal(formatSignificant(Number.POSITIVE_INFINITY), "—");
  assert.equal(formatSignificant(123.456, 5), "123.46");
});

test("units: thin space before the unit, um shown as µm, percent attached", () => {
  assert.equal(displayUnit("um"), "µm");
  assert.equal(displayUnit("um^2"), "µm^2");
  assert.equal(displayUnit("mm/s"), "mm/s");
  assert.equal(displayUnit("sum"), "sum");
  assert.equal(formatWithUnit(123.456, "um"), `123${THIN_SPACE}µm`);
  assert.equal(formatWithUnit(1.7e7, "K/m", 2), `1.7 × 10⁷${THIN_SPACE}K/m`);
  assert.equal(formatWithUnit(12.34, "%"), "12.3%");
  assert.equal(formatWithUnit(7, ""), "7");
});

test("solidification, kinetics and G/R helpers use the shared scientific notation", async () => {
  const { formatSci } = await import("../src/data/lpbfGrSolidification");
  assert.equal(formatSci(1.2345e7, 3), "1.235 × 10⁷");
  assert.equal(formatSci(null), "not available");
  const { sig } = await import("../src/components/3d-distortion-lab/AcceptedPrefixView");
  assert.equal(sig(2.5e7, 2), "2.5 × 10⁷");
  assert.equal(sig(1234, 4), "1234");
  for (const rel of ["src/utils/solidificationEstimateDisplay.ts", "src/utils/solidificationDisplay.ts", "src/utils/kineticsHardnessDisplay.ts", "src/data/lpbfGrSolidification.ts", "src/components/3d-distortion-lab/AcceptedPrefixView.tsx"]) {
    assert.doesNotMatch(read(rel), /\.toExponential\(/, `${rel} formats scientific notation itself`);
  }
});

test("the process window shows µm and a thin space, and keeps exact values in tooltips", () => {
  const source = read("src/components/LpbfProcessWindowMap.tsx");
  assert.doesNotMatch(source, /\(um\)|\} um\b/);
  assert.match(source, /Exact value:/);
  assert.match(read("src/components/3d-distortion-lab/LpbfResultPresentation.tsx"), /Exact value:/);
});

// ---- Item 1: melt pool summary card -------------------------------------------------------------------------
const result = {
  schemaVersion: 1, requestedMode: "screening", effectiveMode: "screening", settings: {},
  solver: { id: "synthetic-summary-fixture", version: "1", openfoam: null }, confidence: "low", validationStatus: "unvalidated", productionReady: false,
  label: "Screening only", fallbackReason: null, metrics: { length_um: 321.456, width_um: 123.4, depth_um: 45 },
  material: { name: "Synthetic", quality: "estimated", source: "Synthetic UI test" }, analyticalComparison: {}, assumptions: [],
  regime: "conduction assumption", mainRisk: "lack-of-fusion", recommendation: "Verify.", riskScope: "Geometric screening only",
} as unknown as SimulationResult;

test("summary card: W, D, L with units and the result's own label, the model scope sentence and the regime verdict", () => {
  const html = renderToStaticMarkup(<MeltPoolSummaryCard result={result} />);
  for (const [label, value] of [["Length", "321"], ["Width", "123"], ["Depth", "45"]]) {
    assert.match(html, new RegExp(`<dt[^>]*>${label}</dt><dd[^>]*>${value}${THIN_SPACE}µm</dd><dd[^>]*data-evidence-label[^>]*>Screening only</dd>`), label);
  }
  assert.equal((html.match(/data-evidence-label/g) ?? []).length, 3);
  assert.match(html, /Exact value: 321\.456 µm/);
  assert.match(html, /Produced by synthetic-summary-fixture in Quick Screening mode, scope: Seconds · Rosenthal \/ Goldak · analytical conduction only · not eligible for experimental validation\./);
  assert.match(html, /Analytical geometry · literature-based approximation\. No transient field or resolved keyhole\./);
  assert.match(html, /Regime verdict: conduction assumption · Geometric screening only/);
});

test("summary card: no regime line when the result has none, and a missing value is a dash, not a number", () => {
  const html = renderToStaticMarkup(<MeltPoolSummaryCard result={{ ...result, regime: "", metrics: { length_um: 1, width_um: Number.NaN, depth_um: 3 } } as SimulationResult} stale />);
  assert.doesNotMatch(html, /Regime verdict/);
  assert.match(html, new RegExp(`—${THIN_SPACE}µm`));
  assert.match(html, /opacity-75/);
});

test("the melt pool stage renders the summary card before the field viewer and thermal history", () => {
  const source = read("src/components/LpbfEngineeringWorkspace.tsx");
  const card = source.indexOf("<MeltPoolSummaryCard");
  assert.ok(card > 0 && card < source.indexOf("<ResolvedThermalViewer") && card < source.indexOf("<ThermalHistory result={result}/>"));
});

// ---- Item 4: process window explanation ---------------------------------------------------------------------
function cell(over: Partial<LpbfProcessWindowCell>): LpbfProcessWindowCell {
  return {
    iP: 0, iV: 0, power_W: 100, speed_mm_s: 500, verdict: "do-not-print", headline: "synthetic headline", dominantGate: "lof_tang",
    blockingGates: ["lof_tang"], riskGates: [], advisoryGates: [], unavailableGates: [], reasons: ["synthetic reason"], extentStatus: "computed",
    insideLiteratureBox: true, normalizedEnthalpy: 12, ballingBand: null, width_um: 100, depth_um: 50, error: null, ...over,
  };
}
const keyholeCell = (iV: number) => cell({ iV, verdict: "risky", dominantGate: "keyhole", blockingGates: [], riskGates: ["keyhole"] });
const tangCell = (iV: number) => cell({ iV });
const printableCell = (iV: number) => cell({ iV, verdict: "printable", blockingGates: [], dominantGate: null });

function response(cells: LpbfProcessWindowCell[], alloyId = "ss316l"): LpbfProcessWindowResponse {
  const counts = { printable: 0, risky: 0, "do-not-print": 0, inconclusive: 0, error: 0 } as Record<string, number>;
  for (const c of cells) counts[c.verdict] += 1;
  return {
    success: true, engine: "lpbf_process_window", alloyId,
    request: { alloyId, beamDiameter_um: 80, layer_um: 40, hatch_um: 110, preheatTemp_C: 80, overlayBeamTolerance_pct: 10 },
    grid: { powers_W: [100], speeds_mm_s: cells.map((_, i) => 500 + i * 100), nP: 1, nV: cells.length, nCells: cells.length,
      literatureBox: { powerMin_W: 100, powerMax_W: 100, speedMin_mm_s: 500, speedMax_mm_s: 600 },
      rangeBasis: { power: { basis: "request", min_W: 100, max_W: 100, n: 1, rule: "request" }, speed: { basis: "request", min_mm_s: 500, max_mm_s: 900, n: cells.length, rule: "request" } } },
    cells, counts, gridAdvisories: [],
    overlay: { beamTolerance_pct: 10, beamWindow_um: [72, 88], note: null, measurementKind: "synthetic", datasets: [] },
    evidence: { kind: "screening-only", experimentalValidation: false, statement: "synthetic" },
    provenance: { modelId: "m", solverRevision: "r", implementationHash: "a".repeat(64), absorptionModel: "flat-plate" },
    cache: { hit: false, key: "k" }, computeMs: 1,
  } as unknown as LpbfProcessWindowResponse;
}

// Tang bump (2026-10-27, physics gate finding 1): a current cell carries lof_tang as a risk gate (alone or with keyhole);
// tangCell is a legacy stored result (an earlier solver revision made lof_tang blocking) and is described as such.
const tangRiskCell = (iV: number) => cell({ iV, verdict: "risky", dominantGate: "lof_tang", blockingGates: [], riskGates: ["lof_tang"], tangIndex: 9.3 });
const tangKeyholeCell = (iV: number) => cell({ iV, verdict: "risky", dominantGate: "lof_tang", blockingGates: [], riskGates: ["lof_tang", "keyhole"], tangIndex: 1.05 });

test("no-printable note: legacy Tang-blocked cells are labelled a legacy result, counts come from the returned gate data", () => {
  const cells = [keyholeCell(0), keyholeCell(1), keyholeCell(2), tangCell(3), tangCell(4)];
  assert.deepEqual(noPrintableExplanation({ cells }), { total: 5, keyholeRiskCells: 3, tangRiskCells: 0, legacyTangBlockedCells: 2, unresolvedCells: 0 });
  const text = noPrintableNoteText({ cells, alloyId: "ss316l" })!;
  assert.match(text, /^No cell in this P-v range is printable\./);
  assert.match(text, /The keyhole risk gate \(dH\/hs at or above 20, a threshold transferred from 316L and Ti-6Al-4V and not derived for this alloy\) flags 3 cells of 5 as a keyhole risk/);
  assert.match(text, /legacy result: an earlier solver revision made 2 cells of 5 do-not-print on the Tang overlap index \(modelled melt-pool geometry\), which the current screen reports as a risk \(risky\), never do-not-print \(re-run the map for current verdicts\)/);
  assert.doesNotMatch(text, /Tang lack-of-fusion criterion|fails in/);
  // Counts are not hard-coded: other gate data gives other counts.
  const one = noPrintableNoteText({ cells: [keyholeCell(0)], alloyId: "ss316l" })!;
  assert.match(one, /flags 1 cell of 1 as a keyhole risk/);
  assert.doesNotMatch(one, /Tang/);
});

test("no-printable note: a current result names both risk gates (Tang and keyhole), never keyhole only, never do-not-print", () => {
  const cells = [tangRiskCell(0), tangKeyholeCell(1), keyholeCell(2)];
  assert.deepEqual(noPrintableExplanation({ cells }), { total: 3, keyholeRiskCells: 2, tangRiskCells: 2, legacyTangBlockedCells: 0, unresolvedCells: 0 });
  const text = noPrintableNoteText({ cells, alloyId: "in718" })!;
  assert.match(text, /flags 2 cells of 3 as a keyhole risk/);
  assert.match(text, /the Tang overlap index \(above 1\.0 on modelled geometry\) flags 2 cells of 3 as a possible lack-of-fusion risk, not an experimentally established defect/);
  assert.doesNotMatch(text, /do-not-print|legacy/);
  // Tang alone: the note does not mention keyhole.
  const tangOnly = noPrintableNoteText({ cells: [tangRiskCell(0)], alloyId: "in718" })!;
  assert.doesNotMatch(tangOnly, /keyhole/);
  // A map with a printable cell shows no empty-map note at all.
  assert.equal(noPrintableNoteText({ cells: [tangRiskCell(0), printableCell(1)], alloyId: "in718" }), null);
  const html = renderToStaticMarkup(<ProcessWindowResultView result={response([tangRiskCell(0), printableCell(1)], "in718")} selected={null} />);
  assert.doesNotMatch(html, /pw-no-printable-note/);
});

test("no-printable note: absent when any cell is printable or the grid is empty, and no claim of 20 for IN625", () => {
  assert.equal(noPrintableNoteText({ cells: [keyholeCell(0), printableCell(1)], alloyId: "ss316l" }), null);
  assert.equal(noPrintableNoteText({ cells: [], alloyId: "ss316l" }), null);
  const in625 = noPrintableNoteText({ cells: [keyholeCell(0)], alloyId: "in625" })!;
  assert.doesNotMatch(in625, /at or above 20|transferred from/);
  assert.match(in625, /keyhole cut of this alloy/);
  assert.match(noPrintableNoteText({ cells: [cell({ verdict: "inconclusive", blockingGates: [], dominantGate: null })], alloyId: "ss316l" })!, /1 cell of 1 could not be resolved/);
});

test("the result view shows the note above the map only when nothing is printable", () => {
  const none = renderToStaticMarkup(<ProcessWindowResultView result={response([keyholeCell(0), tangCell(1)])} selected={null} />);
  const note = none.indexOf('data-testid="pw-no-printable-note"');
  assert.ok(note >= 0 && note < none.indexOf('data-testid="pw-heatmap"'));
  assert.match(none, /flags 1 cell of 2 as a keyhole risk/);
  const some = renderToStaticMarkup(<ProcessWindowResultView result={response([keyholeCell(0), printableCell(1)])} selected={null} />);
  assert.doesNotMatch(some, /pw-no-printable-note/);
});

test("a selected cell lists one plain sentence per gate and keeps the detailed gate table", () => {
  const advisory = cell({ verdict: "risky", blockingGates: [], riskGates: ["keyhole"], advisoryGates: ["balling"], unavailableGates: ["recoater"] });
  assert.deepEqual(cellGateSentences(advisory, "ss316l"), [
    "The keyhole risk gate (dH/hs at or above 20, a threshold transferred from 316L and Ti-6Al-4V and not derived for this alloy) flags this cell, which makes it risky.",
    "The balling aspect-ratio screen gives an advisory only and does not change the verdict.",
    "The recoater check could not be evaluated for this cell.",
  ]);
  // Tang bump (2026-10-27): a blocking lof_tang only exists in legacy stored results and is described so.
  assert.equal(cellGateSentences(cell({}))[0], "Legacy result: an earlier solver revision made this cell do-not-print on the Tang overlap index (modelled melt-pool geometry); the current screen reports an index above 1.0 as a risk (risky), never do-not-print. Re-run the map for the current verdict.");
  // Both risk causes get their own sentence; the Tang one is not worded as a keyhole risk.
  assert.deepEqual(cellGateSentences(tangKeyholeCell(0), "in718"), [
    "The Tang overlap index exceeds 1.0 on modelled melt-pool geometry, which makes this cell risky: modelled geometry indicates possible lack of fusion; not an experimentally established defect.",
    "The keyhole risk gate (dH/hs at or above 20, a threshold transferred from 316L and Ti-6Al-4V and not derived for this alloy) flags this cell, which makes it risky.",
  ]);
  // The selected cell shows the Tang index and the fusion note.
  const tangHtml = renderToStaticMarkup(<ProcessWindowCellDetail cell={tangRiskCell(0)} advisories={[]} />);
  assert.match(tangHtml, /data-testid="pw-detail-tang">Tang overlap index 9\.3 on modelled melt-pool geometry \(risk above 1\.0\)\. Screening result; fusion adequacy is not established\.</);
  const noIndex = renderToStaticMarkup(<ProcessWindowCellDetail cell={cell({ verdict: "inconclusive", blockingGates: [], tangIndex: null })} advisories={[]} />);
  assert.doesNotMatch(noIndex, /pw-detail-tang/);
  assert.deepEqual(cellGateSentences(cell({ verdict: "error", error: "x" })), []);
  const html = renderToStaticMarkup(<ProcessWindowCellDetail cell={advisory} advisories={[]} bandContext={{ alloyId: "ss316l", modelId: "m", beamDiameter_um: 80 }} />);
  assert.match(html, /data-testid="pw-detail-gate-sentences"/);
  assert.match(html, /Failing gates \(do-not-print\)/);
  assert.match(html, /Reasons \(verbatim from the engine\)/);
});

// ---- Item 3: chart axis labels and tooltips -----------------------------------------------------------------
test("every in-scope chart axis has a label with its unit", () => {
  const bayes = read("src/components/LpbfBayesianOptimizerLab.tsx");
  assert.match(bayes, /value: "Iteration \(number\)"/);
  assert.match(bayes, /value: "Verdict score \(0 to 1, unitless\)"/);
  assert.match(bayes, /\(unitless\)`, "Verdict score"/);
  const thermal = read("src/components/3d-distortion-lab/LpbfResultPresentation.tsx");
  assert.match(thermal, /value: "Elapsed time \(ms\)"/);
  assert.match(thermal, /value: "Domain peak temperature \(K\)"/);
  const calphad = read("src/components/CALPHADMultiComponentStudio.tsx");
  assert.equal((calphad.match(/value: "Temperature \(°C\)"/g) ?? []).length, 5);
  for (const label of ["Molar Gibbs energy G_m (kJ/mol)", "Chemical potential μ_i (kJ/mol)", "Activity a_i (dimensionless)", "Phase fraction (%)", "Fraction solid f_S (dimensionless)"]) {
    assert.ok(calphad.includes(`value: "${label}"`), label);
  }
  const pw = read("src/components/LpbfProcessWindowMap.tsx");
  assert.match(pw, /Scan speed v \(mm\/s\)/);
  assert.match(pw, /Laser power P \(W\)/);
  assert.match(read("src/components/GrSolidificationMapCard.tsx"), /Scan speed v \(mm\/s\)/);
});

test("process window and G/R map cells carry a tooltip with values and units", () => {
  const html = renderToStaticMarkup(<ProcessWindowResultView result={response([tangCell(0)])} selected={null} />);
  assert.match(html, new RegExp(`<title>100${THIN_SPACE}W, 500${THIN_SPACE}mm/s: [^<]*\\. Width 100${THIN_SPACE}µm, depth 50${THIN_SPACE}µm\\.</title>`));
  assert.match(read("src/components/GrSolidificationMapCard.tsx"), /<title>\{`\$\{cellAriaLabel\(cell, metric\)\}/);
});

test("the Quick Screening summary card offers its own calculation panel, not the specialist-lab one", async () => {
  const { readFileSync } = await import("node:fs");
  const { renderToStaticMarkup } = await import("react-dom/server");
  const React = await import("react");
  const { MeltPoolSummaryCard } = await import("../src/components/3d-distortion-lab/MeltPoolSummaryCard");
  const result = JSON.parse(readFileSync(new URL("./fixtures/how-calculated/screening-job-in718.json", import.meta.url), "utf8"));
  const html = renderToStaticMarkup(React.createElement(MeltPoolSummaryCard, { result }));
  assert.match(html, /How the Quick Screening length, width and depth are calculated/);
  assert.doesNotMatch(html, /How the melt pool length, width, depth and VED are calculated/);
  const standard = renderToStaticMarkup(React.createElement(MeltPoolSummaryCard, { result: { ...result, effectiveMode: "standard" } }));
  assert.doesNotMatch(standard, /How the Quick Screening/);
});
