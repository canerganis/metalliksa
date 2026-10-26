import React from "react";
import test from "node:test";
import assert from "node:assert/strict";
import { renderToStaticMarkup } from "react-dom/server";
import {
  LpbfProcessWindowMap,
  ProcessWindowHeatmap,
  ProcessWindowHonestyBanner,
  ProcessWindowLegend,
  ProcessWindowPhaseNotice,
  ProcessWindowResultView,
  ProcessWindowUnsupportedAlloy,
} from "../src/components/LpbfProcessWindowMap";
import {
  axisFraction,
  checkedProcessWindow,
  inputsFromResponse,
  inputsKey,
  isStale,
  legendEntries,
  memoClear,
  memoGet,
  memoSet,
  memoSize,
  moveCell,
  parseAxis,
  verdictStyle,
} from "../src/data/lpbfProcessWindow";
import {
  LpbfProcessWindowRequestError,
  pythonComputationService,
  type LpbfProcessWindowCell,
  type LpbfProcessWindowCellVerdict,
  type LpbfProcessWindowResponse,
} from "../src/services/pythonComputationService";

// SYNTHETIC fixture: it exercises the view and validator only. No number here is a model or measurement result.
const POWERS = [100, 200, 300];
const SPEEDS = [400, 600, 800, 1000];
const VERDICT_BY_CELL: LpbfProcessWindowCellVerdict[] = [
  "printable", "risky", "do-not-print", "inconclusive",
  "risky", "printable", "error", "inconclusive",
  "do-not-print", "risky", "printable", "printable",
];

function makeCell(index: number): LpbfProcessWindowCell {
  const iP = Math.floor(index / SPEEDS.length);
  const iV = index % SPEEDS.length;
  const verdict = VERDICT_BY_CELL[index];
  const computed = verdict !== "inconclusive" && verdict !== "error";
  return {
    iP, iV, power_W: POWERS[iP], speed_mm_s: SPEEDS[iV], verdict,
    headline: `synthetic headline ${verdict}`,
    dominantGate: verdict === "do-not-print" ? "keyhole" : null,
    blockingGates: verdict === "do-not-print" ? ["keyhole"] : [],
    riskGates: verdict === "risky" ? ["literature_pv"] : [],
    advisoryGates: [], unavailableGates: verdict === "inconclusive" ? ["lof_tang"] : [],
    reasons: verdict === "error" ? [] : [`synthetic reason ${index}`],
    extentStatus: verdict === "error" ? null : computed ? "computed" : "heuristic-width-fallback",
    insideLiteratureBox: verdict === "error" ? null : true,
    normalizedEnthalpy: verdict === "error" ? null : 12.5,
    ballingBand: null,
    width_um: computed ? 100 + index : null,
    depth_um: computed ? 50 + index : null,
    error: verdict === "error" ? "RuntimeError: synthetic failure" : null,
  };
}

function makeResponse(overrides: Record<string, unknown> = {}): LpbfProcessWindowResponse {
  const cells = VERDICT_BY_CELL.map((_, i) => makeCell(i));
  const counts = { printable: 0, risky: 0, "do-not-print": 0, inconclusive: 0, error: 0 } as Record<string, number>;
  for (const c of cells) counts[c.verdict] += 1;
  const base = {
    success: true, engine: "lpbf_process_window", alloyId: "in718",
    request: { alloyId: "in718", beamDiameter_um: 80, layer_um: 40, hatch_um: 110, preheatTemp_C: 80, overlayBeamTolerance_pct: 10 },
    grid: {
      powers_W: POWERS, speeds_mm_s: SPEEDS, nP: POWERS.length, nV: SPEEDS.length, nCells: cells.length,
      literatureBox: { powerMin_W: 150, powerMax_W: 250, speedMin_mm_s: 500, speedMax_mm_s: 900 },
      rangeBasis: {
        power: { basis: "default", min_W: 100, max_W: 300, n: 3, rule: "synthetic rule" },
        speed: { basis: "request", min_mm_s: 400, max_mm_s: 1000, n: 4, rule: "request" },
      },
    },
    cells, counts,
    gridAdvisories: [{ gate: "distortion", note: "synthetic parameter-independent note", cells: 11 }],
    overlay: {
      beamTolerance_pct: 10, beamWindow_um: [72, 88], note: null, measurementKind: "published single-track geometry, not print outcomes",
      datasets: [
        {
          id: "synthetic-ds", label: "Synthetic dataset", status: "available", reason: null, nRows: 10, nShown: 2, hiddenByBeam: 5, hiddenNoBeam: 0, hiddenOutsideRange: 3,
          points: [
            { datasetId: "synthetic-ds", rowId: "s-1", power_W: 200, speed_mm_s: 600, beamDiameter_um: 80, layer_um: 0, preheat_C: 20, measuredWidth_um: 111.1, measuredDepth_um: 55.5,
              modelVerdict: { verdict: "risky", dominantGate: null, extentStatus: "computed", modelWidth_um: 99, modelDepth_um: 44, error: null } },
            { datasetId: "synthetic-ds", rowId: "s-2", power_W: 300, speed_mm_s: 1000, beamDiameter_um: 80, layer_um: 0, preheat_C: 20, measuredWidth_um: null, measuredDepth_um: null,
              modelVerdict: { verdict: "inconclusive", dominantGate: null, extentStatus: "heuristic-width-fallback", modelWidth_um: null, modelDepth_um: null, error: null } },
          ],
        },
        { id: "broken-ds", label: "Broken dataset", status: "unavailable", reason: "OSError: disk gone", nRows: 0, nShown: 0, hiddenByBeam: 0, hiddenNoBeam: 0, hiddenOutsideRange: 0, points: [] },
      ],
    },
    evidence: { kind: "screening-only", experimentalValidation: false, statement: "synthetic statement" },
    provenance: { modelId: "synthetic-model", solverRevision: "synthetic-rev-1", implementationHash: "a".repeat(64), absorptionModel: "flat-plate" },
    cache: { hit: false, key: "k".repeat(64) },
    computeMs: 12.5,
  };
  return { ...base, ...overrides } as unknown as LpbfProcessWindowResponse;
}

const clone = <T,>(value: T): T => JSON.parse(JSON.stringify(value));
const good = (): any => clone(makeResponse());
const rejects = (mutate: (raw: any) => void, pattern: RegExp, label: string) => {
  const raw = good();
  mutate(raw);
  assert.throws(() => checkedProcessWindow(raw), pattern, label);
};

const response = checkedProcessWindow(good());
const gridHtml = renderToStaticMarkup(<ProcessWindowHeatmap result={response} selected={{ iP: 1, iV: 2 }} current={{ power_W: 200, speed_mm_s: 600 }} onSelect={() => undefined} />);
const cellMarkup = (html: string, iP: number, iV: number): string => {
  const start = html.indexOf(`data-testid="pw-cell-${iP}-${iV}"`);
  assert.ok(start >= 0, `cell ${iP}-${iV} not rendered`);
  return html.slice(html.lastIndexOf("<g ", start), html.indexOf("</g>", start));
};

test("validator accepts a well-formed response", () => {
  assert.equal(checkedProcessWindow(good()).cells.length, 12);
});

test("validator rejects a response that is not flagged screening-only and unvalidated", () => {
  rejects(raw => { raw.evidence.experimentalValidation = true; }, /experimentalValidation must be exactly false/, "true");
  rejects(raw => { delete raw.evidence.experimentalValidation; }, /experimentalValidation must be exactly false/, "missing");
  rejects(raw => { raw.evidence.experimentalValidation = "false"; }, /experimentalValidation must be exactly false/, "string");
  rejects(raw => { raw.evidence.kind = "validated-simulation"; }, /screening-only/, "kind");
  rejects(raw => { raw.success = false; }, /success/, "success");
  rejects(raw => { raw.provenance.implementationHash = ""; }, /implementationHash/, "hash");
});

test("validator rejects unknown verdicts, W/D with a non-computed extent, and wrong cell counts", () => {
  rejects(raw => { raw.cells[0].verdict = "validated"; }, /unknown verdict/, "unknown verdict");
  rejects(raw => { raw.overlay.datasets[0].points[0].modelVerdict.verdict = "great"; }, /unknown model verdict/, "unknown point verdict");
  rejects(raw => { raw.cells[3].width_um = 120; }, /extentStatus is "heuristic-width-fallback"/, "W with non-computed extent");
  rejects(raw => { raw.cells[3].depth_um = 120; }, /extentStatus/, "D with non-computed extent");
  rejects(raw => { raw.cells[6].width_um = 120; }, /error cell but carries width\/depth/, "W on an error cell");
  rejects(raw => { raw.cells.pop(); }, /cell count 11 does not equal 3 x 4/, "missing cell");
  rejects(raw => { raw.cells.push(clone(raw.cells[0])); }, /cell count 13/, "extra cell");
  rejects(raw => { raw.cells[6].error = null; }, /error cell without an error message/, "error without message");
  rejects(raw => { raw.cells[0].error = "oops"; }, /error message but verdict/, "message on a verdict");
  rejects(raw => { raw.cells[1].iV = 0; }, /index does not match/, "index mismatch");
  rejects(raw => { raw.cells[1].power_W = 999; }, /does not match the grid axes/, "axis mismatch");
  rejects(raw => { raw.counts.printable += 1; }, /counts.printable/, "counts mismatch");
  rejects(raw => { raw.grid.nCells = 11; }, /nP\/nV\/nCells/, "nCells");
  rejects(raw => { raw.cells[3].verdict = "risky"; }, /without a computed extent/, "risky without extent");
  rejects(raw => { raw.overlay.datasets[1].reason = null; }, /unavailable without a reason/, "unavailable dataset without reason");
});

test("legend counts equal the response counts and the number of cells", () => {
  const entries = legendEntries(response);
  assert.deepEqual(Object.fromEntries(entries.map(e => [e.verdict, e.count])), { ...response.counts });
  assert.equal(entries.reduce((n, e) => n + e.count, 0), response.cells.length);
  const html = renderToStaticMarkup(<ProcessWindowLegend result={response} />);
  for (const [verdict, count] of Object.entries(response.counts)) {
    assert.match(html, new RegExp(`data-testid="pw-legend-${verdict}" data-count="${count}"`), verdict);
  }
  assert.equal(response.counts.error, 1);
  assert.equal(response.counts.inconclusive, 2);
});

test("inconclusive and error cells never use the printable style", () => {
  const printable = verdictStyle("printable");
  assert.equal(printable.printableLooking, true);
  for (const verdict of ["risky", "do-not-print", "inconclusive", "error"] as const) {
    const style = verdictStyle(verdict);
    assert.equal(style.printableLooking, false, verdict);
    assert.notEqual(style.fill, printable.fill, verdict);
    assert.notEqual(style.letter, printable.letter, verdict);
  }
  assert.equal(verdictStyle("inconclusive").hatched, true);
  assert.equal(verdictStyle("error").outlined, true);
  assert.equal(verdictStyle("error").fill, "none");
  assert.throws(() => verdictStyle("validated"), /unknown process-window verdict/);

  // index 3 and 7 are inconclusive, index 6 is the error cell (iP 1, iV 2); 0 is printable.
  for (const [iP, iV] of [[0, 3], [1, 3]]) {
    const markup = cellMarkup(gridHtml, iP, iV);
    assert.match(markup, /data-verdict="inconclusive"/);
    assert.match(markup, /fill="url\(#pw-hatch\)"/);
    assert.ok(!markup.includes(printable.fill), "inconclusive cell must not use the printable fill");
    assert.match(markup, />\?<\/text>/);
  }
  const error = cellMarkup(gridHtml, 1, 2);
  assert.match(error, /data-verdict="error"/);
  assert.match(error, /fill="none"/);
  assert.match(error, /stroke-dasharray="4 3"/);
  assert.ok(!error.includes(printable.fill));
  assert.match(error, />!<\/text>/);
  const ok = cellMarkup(gridHtml, 0, 0);
  assert.match(ok, /data-verdict="printable"/);
  assert.ok(ok.includes(printable.fill));
  // every cell carries a letter as well as a colour
  for (const letter of ["P", "R", "X", "?", "!"]) assert.ok(gridHtml.includes(`>${letter}</text>`), letter);
});

test("every cell also carries a text label for assistive technology", () => {
  assert.match(cellMarkup(gridHtml, 1, 2), /aria-label="Power 200 W, speed 800 mm\/s: Solver error: RuntimeError: synthetic failure"/);
  assert.match(cellMarkup(gridHtml, 0, 3), /Inconclusive \(geometry not resolved\)/);
});

test("moveCell moves by one cell, never wraps and handles Home/End/Page keys", () => {
  const at = { iP: 1, iV: 1 };
  assert.deepEqual(moveCell(at, "ArrowRight", 3, 4), { iP: 1, iV: 2 });
  assert.deepEqual(moveCell(at, "ArrowLeft", 3, 4), { iP: 1, iV: 0 });
  assert.deepEqual(moveCell(at, "ArrowUp", 3, 4), { iP: 2, iV: 1 });
  assert.deepEqual(moveCell(at, "ArrowDown", 3, 4), { iP: 0, iV: 1 });
  assert.deepEqual(moveCell({ iP: 0, iV: 0 }, "ArrowLeft", 3, 4), { iP: 0, iV: 0 });
  assert.deepEqual(moveCell({ iP: 0, iV: 0 }, "ArrowDown", 3, 4), { iP: 0, iV: 0 });
  assert.deepEqual(moveCell({ iP: 2, iV: 3 }, "ArrowRight", 3, 4), { iP: 2, iV: 3 });
  assert.deepEqual(moveCell({ iP: 2, iV: 3 }, "ArrowUp", 3, 4), { iP: 2, iV: 3 });
  assert.deepEqual(moveCell(at, "Home", 3, 4), { iP: 1, iV: 0 });
  assert.deepEqual(moveCell(at, "End", 3, 4), { iP: 1, iV: 3 });
  assert.deepEqual(moveCell(at, "PageUp", 3, 4), { iP: 2, iV: 1 });
  assert.deepEqual(moveCell(at, "PageDown", 3, 4), { iP: 0, iV: 1 });
  assert.deepEqual(moveCell(at, "a", 3, 4), at);
  assert.deepEqual(moveCell({ iP: 9, iV: 9 }, "x", 3, 4), { iP: 2, iV: 3 }, "an out-of-range position is clamped back");
});

test("the heat map is one role=grid with a single tab stop and an active descendant", () => {
  assert.equal((gridHtml.match(/role="grid"/g) ?? []).length, 1);
  assert.equal((gridHtml.match(/tabindex="0"/g) ?? []).length, 1, "exactly one tab stop");
  assert.equal((gridHtml.match(/role="gridcell"/g) ?? []).length, 12);
  assert.equal((gridHtml.match(/role="row"/g) ?? []).length, 3);
  assert.match(gridHtml, /aria-activedescendant="pw-cell-1-2"/);
  assert.match(gridHtml, /aria-selected="true"/);
  assert.equal((gridHtml.match(/aria-selected="true"/g) ?? []).length, 1);
});

test("overlays: dashed literature box, cross-hair at the current P/v, hollow dataset markers without verdict fill", () => {
  assert.match(gridHtml, /data-testid="pw-literature-box"[^>]*stroke-dasharray="7 5"/);
  assert.match(gridHtml, /data-testid="pw-crosshair"/);
  const markers = gridHtml.match(/<(circle|rect|polygon)[^>]*data-testid="pw-marker"[^>]*>/g) ?? [];
  assert.equal(markers.length, 2, "both available points are inside the mapped range");
  const verdictFills = (["printable", "risky", "do-not-print", "inconclusive"] as const).map(v => verdictStyle(v).fill);
  for (const marker of markers) {
    assert.match(marker, /fill="none"/);
    for (const fill of verdictFills) assert.ok(!marker.includes(fill), `marker must not carry ${fill}`);
  }
  // a cross-hair outside the mapped range is not drawn; the view says so instead
  const outside = renderToStaticMarkup(<ProcessWindowHeatmap result={response} selected={null} current={{ power_W: 900, speed_mm_s: 600 }} />);
  assert.ok(!outside.includes('data-testid="pw-crosshair"'));
  const view = renderToStaticMarkup(<ProcessWindowResultView result={response} selected={null} current={{ power_W: 900, speed_mm_s: 600 }} />);
  assert.match(view, /data-testid="pw-crosshair-outside"/);
});

test("axisFraction maps values onto cell centres and rejects values off the map", () => {
  assert.equal(axisFraction([100, 200, 300], 100), 0);
  assert.equal(axisFraction([100, 200, 300], 250), 1.5);
  assert.equal(axisFraction([100, 200, 300], 50), -0.5);
  assert.equal(axisFraction([100, 200, 300], 350), 2.5);
  assert.equal(axisFraction([100, 200, 300], 49), null);
  assert.equal(axisFraction([100, 200, 300], 351), null);
  assert.equal(axisFraction([100, 200, 300], Number.NaN), null);
});

test("stale detection compares the engine's echo with the current inputs", () => {
  const current = inputsFromResponse(response);
  assert.equal(isStale(response, current), false);
  assert.equal(isStale(response, { ...current, layer_um: 41 }), true);
  assert.equal(isStale(response, { ...current, powers: [100, 200, 301] }), true);
  assert.equal(isStale(response, { ...current, alloyId: "ss316l" }), true);
  assert.equal(isStale(response, null), true, "invalid current inputs also mean the map no longer matches the form");
  assert.equal(isStale(null, current), false);
  const stale = renderToStaticMarkup(<ProcessWindowResultView result={response} selected={null} stale />);
  assert.match(stale, /data-testid="pw-stale"/);
  assert.match(stale, /Press Compute to update it/);
  assert.match(stale, /data-stale="true"/);
  const fresh = renderToStaticMarkup(<ProcessWindowResultView result={response} selected={null} />);
  assert.ok(!fresh.includes('data-testid="pw-stale"'));
});

test("served-from-cache states are disclosed and distinguished", () => {
  const engine = renderToStaticMarkup(<ProcessWindowResultView result={{ ...response, originalComputeMs: 2400 } as LpbfProcessWindowResponse} selected={null} source="engine-cache" />);
  assert.match(engine, /data-testid="pw-cache-engine"/);
  assert.match(engine, /nothing was recomputed/);
  assert.match(engine, /2400 ms originally/);
  const memo = renderToStaticMarkup(<ProcessWindowResultView result={response} selected={null} source="browser-memo" />);
  assert.match(memo, /data-testid="pw-cache-memo"/);
  assert.match(memo, /no request was sent/);
  const computed = renderToStaticMarkup(<ProcessWindowResultView result={response} selected={null} source="computed" />);
  assert.match(computed, /data-testid="pw-computed"/);
  assert.ok(!computed.includes("pw-cache-"));
});

test("the honesty banner is always rendered and states the limits", () => {
  const before = renderToStaticMarkup(<ProcessWindowHonestyBanner />);
  assert.match(before, /Screening only/);
  assert.match(before, /not a validation/);
  assert.match(before, /flat-plate absorptivity/);
  assert.match(before, /never a printable result/);
  assert.match(before, /geometry, not print outcomes/);
  assert.match(before, /shown after Compute/, "model, revision and hash are not invented before a response exists");
  const after = renderToStaticMarkup(<ProcessWindowHonestyBanner provenance={response.provenance} />);
  assert.match(after, /synthetic-model/);
  assert.match(after, /synthetic-rev-1/);
  assert.ok(after.includes("a".repeat(64)));
  assert.match(after, /engine reports/);
  // the banner is part of the result view and of the container
  assert.match(renderToStaticMarkup(<LpbfProcessWindowMap />), /data-testid="pw-honesty-banner"/);
});

test("the table fallback renders every cell, with a text verdict and an explicit 'not computed'", () => {
  const html = renderToStaticMarkup(<ProcessWindowResultView result={response} selected={null} />);
  const rows = html.match(/data-testid="pw-table-row"/g) ?? [];
  assert.equal(rows.length, response.cells.length);
  assert.match(html, /Table view of all 12 cells/);
  assert.match(html, /<th scope="col">Verdict<\/th>/);
  assert.match(html, /Solver error: RuntimeError: synthetic failure/);
  assert.match(html, /not computed/);
});

test("the cell detail panel shows verbatim reasons, gates, advisories and the error text", () => {
  const ok = renderToStaticMarkup(<ProcessWindowResultView result={response} selected={{ iP: 0, iV: 2 }} />);
  assert.match(ok, /data-testid="pw-detail"/);
  assert.match(ok, /synthetic reason 2/);
  assert.match(ok, /Failing gates \(do-not-print\)/);
  assert.match(ok, /keyhole/);
  assert.match(ok, /data-testid="pw-grid-advisories"/);
  assert.match(ok, /synthetic parameter-independent note/);
  const inconclusive = renderToStaticMarkup(<ProcessWindowResultView result={response} selected={{ iP: 0, iV: 3 }} />);
  assert.match(inconclusive, /data-testid="pw-detail-wd">not computed \/ not computed</);
  const error = renderToStaticMarkup(<ProcessWindowResultView result={response} selected={{ iP: 1, iV: 2 }} />);
  assert.match(error, /data-testid="pw-detail-error"/);
  assert.match(error, /No verdict exists for it/);
  const none = renderToStaticMarkup(<ProcessWindowResultView result={response} selected={null} />);
  assert.match(none, /data-testid="pw-detail-empty"/);
});

test("measurements table: geometry only, no verdict fill on markers, unavailable datasets keep the map", () => {
  const html = renderToStaticMarkup(<ProcessWindowResultView result={response} selected={null} />);
  assert.match(html, /Measurements \(geometry, not print outcomes\)/);
  assert.equal((html.match(/data-testid="pw-measurement-row"/g) ?? []).length, 2);
  assert.match(html, /111\.1/);
  assert.match(html, /not available/, "a point without measured width/depth says so");
  assert.match(html, /5 hidden by the beam-diameter filter/);
  assert.match(html, /3 outside the mapped P\/v range/);
  assert.match(html, /data-testid="pw-dataset-unavailable"[^>]*>Unavailable: OSError: disk gone/);
  const empty = clone(good());
  empty.overlay.datasets = [];
  empty.overlay.note = "No measurement dataset for this alloy is wired into the repository; no overlay is shown.";
  const emptyHtml = renderToStaticMarkup(<ProcessWindowResultView result={checkedProcessWindow(empty)} selected={null} />);
  assert.match(emptyHtml, /data-testid="pw-overlay-note"/);
  assert.match(emptyHtml, /data-testid="pw-no-measurements"/);
});

test("loading, engine-unavailable, refusal, invalid-response and unsupported-alloy states", () => {
  const render = (phase: React.ComponentProps<typeof ProcessWindowPhaseNotice>["phase"], supported = true) =>
    renderToStaticMarkup(<ProcessWindowPhaseNotice phase={phase} alloySupported={supported} />);
  assert.match(render({ kind: "idle" }), /No map yet/);
  assert.ok(!render({ kind: "idle" }, false).includes("No map yet"));
  const loading = render({ kind: "loading", cells: 121 });
  assert.match(loading, /role="status"/);
  assert.match(loading, /Computing 121 cells/);
  const unavailable = render({ kind: "unavailable", message: "connect ECONNREFUSED" });
  assert.match(unavailable, /Engine unavailable: connect ECONNREFUSED/);
  assert.match(unavailable, /nothing was estimated in the browser/);
  const refused = render({ kind: "refused", message: "powers needs 2 to 15 values" });
  assert.match(refused, /The engine refused this request: powers needs 2 to 15 values/);
  assert.match(refused, /Nothing was clamped or substituted/);
  assert.match(render({ kind: "invalid", message: "lpbf process window response rejected: x" }), /failed validation and is not shown/);
  const unsupported = renderToStaticMarkup(<ProcessWindowUnsupportedAlloy reason={'Alloy "in625" has no solver material in the optimizer backend.'} />);
  assert.match(unsupported, /Unsupported alloy: Alloy &quot;in625&quot; has no solver material/);
  assert.match(unsupported, /No map can be computed/);
});

test("axis parsing mirrors the engine limits", () => {
  const ok = parseAxis("60", "450", "11", "Power", "W", 1500);
  assert.equal(ok.ok, true);
  assert.equal(ok.values.length, 11);
  assert.equal(ok.values[0], 60);
  assert.equal(ok.values[10], 450);
  for (const [min, max, n, pattern] of [
    ["0", "450", "11", /greater than 0/], ["-5", "450", "11", /greater than 0/], ["450", "60", "11", /greater than the minimum/],
    ["60", "450", "16", /2 to 15/], ["60", "450", "1", /2 to 15/], ["60", "450", "2.5", /2 to 15/], ["60", "1501", "11", /at most 1500/],
    ["", "450", "11", /must be numbers/], ["60", "60.001", "15", /too narrow/],
  ] as const) {
    const parsed = parseAxis(min, max, n, "Power", "W", 1500);
    assert.equal(parsed.ok, false, `${min}-${max} n=${n}`);
    assert.match(parsed.reason ?? "", pattern);
  }
});

test("client memo returns the stored response for identical inputs and is bounded", () => {
  memoClear();
  const key = inputsKey(inputsFromResponse(response));
  assert.equal(memoGet(key), null);
  memoSet(key, response);
  assert.equal(memoGet(key), response);
  for (let i = 0; i < 12; i++) memoSet(`k${i}`, response);
  assert.equal(memoSize(), 8);
  assert.equal(memoGet(key), null, "the oldest entry was evicted");
  memoClear();
  assert.equal(memoSize(), 0);
});

test("the container renders the idle state with fixed process inputs and an explicit Compute button (no auto-run)", () => {
  const html = renderToStaticMarkup(<LpbfProcessWindowMap />);
  assert.match(html, /data-testid="pw-compute"/);
  assert.match(html, /Nothing is computed until you press Compute/);
  assert.match(html, /data-testid="pw-open-material"/);
  assert.match(html, /Material &amp; Parameters/);
  assert.match(html, /From the active specimen \(read-only\)/);
  assert.ok(!html.includes('data-testid="pw-result"'), "no result before Compute");
});

test("service: refusals, unreachable engine and success are told apart", async () => {
  const realFetch = globalThis.fetch;
  const reply = (status: number, body: unknown) => (async () => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } })) as typeof fetch;
  const request = { alloyId: "in718", beamDiameter_um: 80, layer_um: 40, hatch_um: 110, preheatTemp_C: 80 };
  try {
    globalThis.fetch = reply(422, { success: false, errorKind: "validation", error: "powers needs 2 to 15 values" });
    await assert.rejects(pythonComputationService.runLpbfProcessWindow(request), (e: unknown) =>
      e instanceof LpbfProcessWindowRequestError && e.kind === "validation" && e.status === 422 && /powers needs/.test(e.message));
    globalThis.fetch = reply(500, { error: "Python returned empty stdout" });
    await assert.rejects(pythonComputationService.runLpbfProcessWindow(request), (e: unknown) =>
      e instanceof LpbfProcessWindowRequestError && e.kind === "engine-unavailable" && e.status === 500);
    globalThis.fetch = (async () => { throw new TypeError("fetch failed"); }) as typeof fetch;
    await assert.rejects(pythonComputationService.runLpbfProcessWindow(request), (e: unknown) =>
      e instanceof LpbfProcessWindowRequestError && e.kind === "engine-unavailable" && e.status === null && /fetch failed/.test(e.message));
    globalThis.fetch = reply(200, { success: false, error: "boom" });
    await assert.rejects(pythonComputationService.runLpbfProcessWindow(request), /boom/);
    const calls: { url: string; body: string }[] = [];
    globalThis.fetch = (async (url: string, init: RequestInit) => {
      calls.push({ url, body: String(init.body) });
      return new Response(JSON.stringify(good()), { status: 200 });
    }) as typeof fetch;
    const raw = await pythonComputationService.runLpbfProcessWindow({ ...request, powers: [100, 200], speeds: [500, 600] });
    assert.equal(checkedProcessWindow(raw).cells.length, 12);
    assert.equal(calls[0].url, "/api/python/lpbf-process-window");
    assert.deepEqual(JSON.parse(calls[0].body).powers, [100, 200]);
  } finally {
    globalThis.fetch = realFetch;
  }
});

test("Tang advisory bump (2026-10-27): a printable cell with the Tang advisory says so in the detail and the map has no empty-map note", () => {
  // SYNTHETIC: one cell turned into a current-revision printable cell that carries lof_tang as an advisory gate.
  const base = checkedProcessWindow(good());
  const cells = base.cells.map(c => (c.iP === 0 && c.iV === 0 ? { ...c, verdict: "printable" as const, advisoryGates: ["lof_tang"], blockingGates: [], riskGates: [] } : c));
  const result = { ...base, cells };
  const html = renderToStaticMarkup(<ProcessWindowResultView result={result} selected={{ iP: 0, iV: 0 }} />);
  assert.match(html, /The Tang overlap index exceeds 1\.0 using modelled melt-pool geometry: lack of fusion is possible and this screen cannot establish whether fusion is adequate\. It is an advisory only and does not change the verdict\./);
  assert.doesNotMatch(html, /pw-no-printable-note/);
  assert.doesNotMatch(html, /Tang lack-of-fusion criterion/);
});
