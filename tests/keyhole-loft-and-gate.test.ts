import assert from "node:assert/strict";
import { test } from "node:test";
import { isLoftKeyhole, LOFT_KEYHOLE_DH_HS_EDGE } from "../src/components/3d-distortion-lab/meltPool3DGeometry";
import { keyholeGateOk, LOF_DIAGNOSTIC_HINT, lofTileState, recoaterTileState } from "../src/components/3d-distortion-lab/IndustrialLPBFDecisionLab";
import { STRESS_UNAVAILABLE_NOTE } from "../src/utils/distortionHeuristic";

const mk = (regime: string, dh?: number) =>
  ({ meltPoolGeometry: { regime }, processParameters: dh === undefined ? {} : { normalizedEnthalpy: dh } }) as never;

test("loft keyhole shape follows the legacy ΔH/hs 30 contour edge, not the regime label", () => {
  assert.equal(LOFT_KEYHOLE_DH_HS_EDGE, 30);
  assert.equal(isLoftKeyhole(mk("Keyhole", 25)), false); // regime Keyhole from 20, contour edge still 30
  assert.equal(isLoftKeyhole(mk("Keyhole", 30)), true);
  assert.equal(isLoftKeyhole(mk("Conduction", 45)), true);
});

test("loft keyhole falls back to the regime label when ΔH/hs is missing", () => {
  assert.equal(isLoftKeyhole(mk("Keyhole")), true);
  assert.equal(isLoftKeyhole(mk("Conduction")), false);
});

test("missing keyhole gate verdict is unavailable (null), not OK", () => {
  assert.equal(keyholeGateOk(undefined), null);
  assert.equal(keyholeGateOk("pass"), true);
  assert.equal(keyholeGateOk("advisory"), true);
  assert.equal(keyholeGateOk("fail"), false);
});

test("not-evaluated and unavailable keyhole gates are null (not evaluated), never fail", () => {
  assert.equal(keyholeGateOk("not-evaluated"), null);
  assert.equal(keyholeGateOk("unavailable"), null);
});

test("null lofGeometry payload renders W/h and D/t as not evaluated with the gate reason", () => {
  const lofGeometry = { widthOverHatch: null, depthOverLayer: null, tangIndex: null, hOverW: null, tOverD: null };
  const reason = "not evaluated: lack-of-fusion input (Tang index, width or depth) is null (never counted as pass or fail)";
  const gate = { status: "not-evaluated", reason };
  const wh = lofTileState(lofGeometry.widthOverHatch, true, gate, "");
  assert.deepEqual(wh, { value: "not evaluated", ok: null, hint: reason });
  const dt = lofTileState(lofGeometry.depthOverLayer, true, gate, "");
  assert.deepEqual(dt, { value: "not evaluated", ok: null, hint: reason });
  assert.equal(lofTileState(null, true, undefined, "").ok, null);
});

test("P7a payloads (gate.required null) render the W/h and D/t ratios neutrally with the diagnostic hint", () => {
  // The former hard-coded 1.05 / 1.15 edges are gone from the tile: a 0.9 ratio must not turn amber.
  assert.deepEqual(lofTileState(0.9, true, { status: "pass", required: null }, ""),
    { value: "0.90", ok: null, hint: LOF_DIAGNOSTIC_HINT });
  assert.deepEqual(lofTileState(1.2, true, { status: "pass", required: null }, ""),
    { value: "1.20", ok: null, hint: LOF_DIAGNOSTIC_HINT });
  assert.equal(lofTileState(1.2, true, { status: "pass" }, "").ok, null);
});

test("legacy payloads with a numeric required still pass or fail against that threshold", () => {
  assert.deepEqual(lofTileState(1.2, true, { status: "pass", required: 1.05 }, ""),
    { value: "1.20", ok: true, hint: "> 1.05 (legacy payload threshold)" });
  assert.equal(lofTileState(0.9, true, { status: "fail", required: 1.05 }, "").ok, false);
  assert.equal(lofTileState(1.2, false, undefined, "extent unresolved").value, "unavailable");
});

test("recoater tile is n/a and neutral when the gate is not evaluated or the risk is unavailable", () => {
  const reason = "not evaluated: no sourced stress model";
  assert.deepEqual(recoaterTileState("unavailable: no sourced stress model (...)", { status: "not-evaluated", reason }),
    { value: "n/a", ok: null, hint: reason });
  const noGate = recoaterTileState("unavailable: no sourced stress model (...)", undefined);
  assert.equal(noGate.value, "n/a");
  assert.equal(noGate.ok, null);
  assert.equal(noGate.hint, STRESS_UNAVAILABLE_NOTE);
  // Legacy payloads keep their text and are never neutral-null.
  assert.equal(recoaterTileState("Not evaluated from scan parameters (...)", { status: "advisory" }).value, "Not evaluated");
  assert.equal(recoaterTileState("High (distortion index 7.59 > 2.0)", { status: "advisory" }).ok, true);
});
