import assert from "node:assert/strict";
import { test } from "node:test";
import { isLoftKeyhole, LOFT_KEYHOLE_DH_HS_EDGE } from "../src/components/3d-distortion-lab/meltPool3DGeometry";
import { keyholeGateOk, lofTileState } from "../src/components/3d-distortion-lab/IndustrialLPBFDecisionLab";

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
  const wh = lofTileState(lofGeometry.widthOverHatch, 1.05, true, gate, "");
  assert.deepEqual(wh, { value: "not evaluated", ok: null, hint: reason });
  const dt = lofTileState(lofGeometry.depthOverLayer, 1.15, true, gate, "");
  assert.deepEqual(dt, { value: "not evaluated", ok: null, hint: reason });
  assert.equal(lofTileState(null, 1.05, true, undefined, "").ok, null);
});

test("resolved lofGeometry ratios still pass or fail against the threshold", () => {
  assert.deepEqual(lofTileState(1.2, 1.05, true, { status: "pass" }, ""), { value: "1.20", ok: true, hint: "> 1.05" });
  assert.equal(lofTileState(0.9, 1.05, true, { status: "fail" }, "").ok, false);
  assert.equal(lofTileState(1.2, 1.05, false, undefined, "extent unresolved").value, "unavailable");
});
