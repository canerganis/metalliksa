import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { checkedSolidificationEstimates, estimateLine, formatSignificant } from "../src/utils/solidificationEstimateDisplay";

const load = (name: string) => checkedSolidificationEstimates(JSON.parse(readFileSync(new URL(`./fixtures/solidification-estimates/${name}.json`, import.meta.url), "utf8")));

test("formatSignificant keeps the stated digits and never rounds a small value to zero", () => {
  assert.equal(formatSignificant(24535931, 2), "2.5e+7");
  assert.equal(formatSignificant(0.1505, 2), "0.15");
  assert.equal(formatSignificant(0.9046, 1), "0.9");
  assert.equal(formatSignificant(5.3e-5, 1), "5e-5");
  assert.notEqual(formatSignificant(5.3e-5, 1), "0");
});

test("Ti64 KM text names the untransformed asymptote and does not claim retained beta", () => {
  const km = estimateLine("kmAlphaMFraction", load("ti64-conduction").quantities.kmAlphaMFraction);
  assert.match(km.text, /untransformed KM asymptote/);
  assert.doesNotMatch(km.text.replaceAll("not an estimate of retained beta", ""), /retained beta/);
});

test("every Physics estimate line with a value tells the user to calibrate", () => {
  for (const name of ["ti64-conduction", "alsi10mg-conduction", "in718-conduction", "ss316l-conduction"]) {
    for (const [q, quantity] of Object.entries(load(name).quantities)) {
      const line = estimateLine(q, quantity);
      if (line.tier !== "Physics estimate") continue;
      assert.ok(line.text.includes("Calibrate to your machine for better accuracy."), `${name} ${q}`);
    }
  }
});

test("SDAS explanation warns that secondary arms may not form", () => {
  assert.ok(estimateLine("sdas", load("ti64-conduction").quantities.sdas).text.includes("Secondary arms may not form."));
});

test("range text is an input sensitivity range, never an error bar or confidence interval", () => {
  let seen = 0;
  for (const name of ["ti64-surrogate-sensitivity", "ti64-conduction", "alsi10mg-conduction"]) {
    for (const [q, quantity] of Object.entries(load(name).quantities)) {
      const line = estimateLine(q, quantity);
      if (!line.range) continue;
      seen += 1;
      assert.match(line.range, /input sensitivity range/);
      const all = [line.range, line.text, line.rangeInputs ?? ""].join(" ").replaceAll("not an error bar", "");
      assert.doesNotMatch(all, /error bar|confidence interval/i, `${name} ${q}`);
    }
  }
  assert.ok(seen > 0);
});
