import React from "react";
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { renderToStaticMarkup } from "react-dom/server";
import { checkedEstimateContainer, checkedQuantityContainer } from "../src/data/quantityEnvelope";
import { checkedGrSolidification } from "../src/data/lpbfGrSolidification";
import { SolidificationQuantities } from "../src/components/SolidificationQuantities";
import { quantityText } from "../src/utils/solidificationDisplay";
const directory = new URL("./fixtures/solidification-payloads/", import.meta.url);
function containers(raw: unknown): number {
  if (raw === null || typeof raw !== "object") return 0;
  if (Array.isArray(raw)) return raw.reduce((n, item) => n + containers(item), 0);
  const record = raw as Record<string, unknown>;
  const own = Object.hasOwn(record, "quantities")
    ? ((record.quantityEnvelopeSchema === "metalliksa-quantity-envelope-2" ? checkedEstimateContainer(record) : checkedQuantityContainer(record)), 1) : 0;
  return own + Object.values(record).reduce<number>((n, item) => n + containers(item), 0);
}
test("all committed real Python payload fixtures parse with no dual read", () => {
  const files = readdirSync(directory).filter(name => name.endsWith(".json"));
  assert.equal(files.length, 15);
  let count = 0;
  for (const file of files) {
    const raw = JSON.parse(readFileSync(new URL(file, directory), "utf8"));
    count += containers(raw);
    if (file.startsWith("gr-") && raw.success === true) checkedGrSolidification(raw);
    if (file.startsWith("thermal-")) {
      const html = renderToStaticMarkup(React.createElement(SolidificationQuantities, { container: raw }));
      assert.match(html, /data-solidification-envelope/, file);
      assert.doesNotMatch(html, /Older solver result/, file);
      assert.match(html, /Screening only/); assert.match(html, /Research/);
    }
  }
  assert.ok(count >= 20);
});
test("F16 synthetic admitted values stay non-null and keep their per-value source label", () => {
  const raw = JSON.parse(readFileSync(new URL("./fixtures/quantity-envelope/synthetic-admitted-liquidus.json", import.meta.url), "utf8"));
  const container = checkedQuantityContainer(raw);
  assert.equal(container.quantities.thermalGradient.value, 12345678.901234567);
  assert.match(quantityText(container.quantities.thermalGradient), /1\.235 × 10⁷ K\/m · Literature estimate/);
  const html = renderToStaticMarkup(React.createElement(SolidificationQuantities, { container, frontOnly: false }));
  assert.match(html, /data-solidification-envelope/);
  assert.match(html, /1\.235 × 10⁷ K\/m · Literature estimate/);
  assert.doesNotMatch(html, /Older solver result/);
});


test("PDAS displays two named SI-to-micrometre alternatives, without interval wording", () => {
  const raw = JSON.parse(readFileSync(new URL("thermal-in718.json", directory), "utf8"));
  const template = checkedQuantityContainer(raw).quantities.pdas;
  const text = quantityText({ ...template, status: "computed", value: { hunt: 2e-6, kurzFisher: 3e-6 }, reasons: [] });
  assert.equal(text, "Hunt: 2.000; Kurz-Fisher: 3.000 µm");
  assert.doesNotMatch(text, / to |–/);
});

test("quantityReason states a repeated parent-unavailable sentence once and maps the SOL-C gate", async () => {
  const { quantityReason, SOL_C_CHANNEL_TEXT } = await import("../src/utils/solidificationDisplay");
  const parent = (input: string) => ({ input, kind: "derived" });
  const twice = { reasons: [
    { code: "parent-unavailable", params: {}, parent: parent("a") },
    { code: "parent-unavailable", params: {}, parent: parent("b") },
  ] };
  assert.equal(quantityReason(twice as never), "A parent value this quantity depends on is unavailable.");
  const gated = { reasons: [{ code: "parent-unavailable", params: { gate: "sol-c-local-samples-not-installed" }, parent: parent("a") }] };
  assert.equal(quantityReason(gated as never), SOL_C_CHANNEL_TEXT);
});
