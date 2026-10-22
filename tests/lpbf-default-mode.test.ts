import { test } from "node:test";
import assert from "node:assert/strict";
import { useLpbfEngineeringStore } from "../src/store/useLpbfEngineeringStore";

// Standard (transient) stops at the boiling limit for typical LPBF inputs (audit 2026-10-20), so a first run
// with the default must be Screening, which always returns a labelled analytical result.
test("a fresh session starts in Screening mode", () => {
  assert.equal(useLpbfEngineeringStore.getInitialState().mode, "screening");
});
