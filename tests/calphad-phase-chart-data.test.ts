import { test } from "node:test";
import assert from "node:assert/strict";
import { buildPhaseChartData, phaseIdsOf } from "../src/components/CALPHADMultiComponentStudio";

// Shape of an mc_ni IN718 profile around the delta solvus and the solidus (values rounded from a real
// /api/python/calphad-minimize answer, 2026-10-22): DELTA vanishes above 1000 C and LIQUID appears above 1250 C.
const profile = [
  { temperatureC: 1000, phases: [{ phaseId: "FCC_A1", fraction: 0.952 }, { phaseId: "DELTA", fraction: 0.048 }] },
  { temperatureC: 1100, phases: [{ phaseId: "FCC_A1", fraction: 1 }] },
  { temperatureC: 1300, phases: [{ phaseId: "FCC_A1", fraction: 0.669 }, { phaseId: "LIQUID", fraction: 0.331 }] },
];

test("every chart row carries every phase, absent phases as 0 rather than a gap", () => {
  const ids = phaseIdsOf(profile);
  assert.deepEqual(ids, ["FCC_A1", "DELTA", "LIQUID"]);
  const rows = buildPhaseChartData(profile, ids);
  assert.deepEqual(rows[1], { temperatureC: 1100, FCC_A1: 100, DELTA: 0, LIQUID: 0 });
  for (const row of rows) {
    const total = ids.reduce((sum, id) => sum + (row[id] as number), 0);
    assert.ok(Math.abs(total - 100) < 0.11, `row at ${row.temperatureC} C sums to ${total}`);
  }
});

test("repeated composition sets of one phase are summed, not overwritten", () => {
  const point = { temperatureC: 950, phases: [{ phaseId: "FCC_A1", fraction: 0.912 }, { phaseId: "DELTA", fraction: 0.084 }, { phaseId: "FCC_A1", fraction: 0.004 }] };
  const [row] = buildPhaseChartData([point], phaseIdsOf([point]));
  assert.equal(row.FCC_A1, 91.6);
  assert.equal(row.DELTA, 8.4);
});

test("clipped points stay null for every phase", () => {
  const ids = phaseIdsOf(profile);
  const rows = buildPhaseChartData(profile, ids, (t) => t < 1050);
  assert.deepEqual(rows[0], { temperatureC: 1000, FCC_A1: null, DELTA: null, LIQUID: null });
  assert.equal(rows[1].FCC_A1, 100);
});

test("probe chips number repeated composition sets so two chips never read the same", async () => {
  const { phaseChipLabels } = await import("../src/components/CALPHADMultiComponentStudio");
  const chips = phaseChipLabels([
    { phaseId: "FCC_A1", phaseName: "γ-Matrix (FCC_A1 solid solution)", fraction: 0.004 },
    { phaseId: "FCC_A1", phaseName: "γ-Matrix (FCC_A1 solid solution)", fraction: 0.914 },
    { phaseId: "DELTA", phaseName: "DELTA", fraction: 0.082 },
  ]);
  assert.deepEqual(chips.map((c) => c.label), ["γ-Matrix set 1", "γ-Matrix set 2", "DELTA"]);
  assert.equal(new Set(chips.map((c) => c.key)).size, 3);
});
