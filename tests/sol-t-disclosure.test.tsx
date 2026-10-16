import React from "react";
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { renderToStaticMarkup } from "react-dom/server";
import { SolidificationQuantities } from "../src/components/SolidificationQuantities";
import { checkedQuantityContainer } from "../src/data/quantityEnvelope";
import { quantityContainerCsv } from "../src/utils/solidificationDisplay";

const fixture = JSON.parse(readFileSync(new URL("./fixtures/quantity-envelope/sol-t-d13.json", import.meta.url), "utf8"));

test("SOL-T transfer scope travels with every D13 value in UI and CSV", () => {
  const container = checkedQuantityContainer(fixture);
  const html = renderToStaticMarkup(<SolidificationQuantities container={container} frontOnly={false}/>);
  assert.ok(html.includes("Literature estimate"));
  assert.equal((html.match(/data-input-scope/g) ?? []).length, 3);
  assert.ok(html.includes("Al-9Si-0.6Mg"));
  const csv = quantityContainerCsv(container);
  assert.equal(csv.split("\r\n").length, 5);
  for (const line of csv.split("\r\n").slice(1, 4)) {
    assert.ok(line.includes("Literature estimate"));
    assert.ok(line.includes("Al-9Si-0.6Mg"));
    assert.ok(line.includes("Brandt2007"));
  }
});

test("SOL-T CSV quotes embedded commas, quotes and line breaks", () => {
  const container = checkedQuantityContainer(fixture);
  const changed = { ...container, inputProvenance: { ...container.inputProvenance,
    liquidus_K: { ...container.inputProvenance!.liquidus_K, scope: 'transfer, "quoted"\nnext line' } } };
  assert.ok(quantityContainerCsv(changed).includes('"transfer, ""quoted""\nnext line"'));
});
