import assert from "node:assert/strict";
import { test } from "node:test";
import React from "react";
import { readFileSync } from "node:fs";
import { renderToStaticMarkup } from "react-dom/server";
import { LpbfDefaultsNote } from "../src/components/LpbfDefaultsNote";
import { ScientificContextPanel } from "../src/components/ScientificContextPanel";
import { WarningNotes, EstimateWarnings, moreNotesLabel } from "../src/components/SolidificationEstimates";
import { CONTEXT_AFTER_MODULE } from "../src/data/workspaces";
import { useMaterialSpecimenStore, withLpbfProcessDefaults } from "../src/store/useMaterialSpecimenStore";

const specimen = useMaterialSpecimenStore.getState().activeSpecimen;
const read = (path: string) => readFileSync(new URL(`../${path}`, import.meta.url), "utf8");

test("unsourced-defaults notice is compact with a 'show which' disclosure holding the unchanged line", () => {
  const lpbf = withLpbfProcessDefaults(specimen.lpbf);
  assert.ok((lpbf.defaultsApplied ?? []).length > 0, "fixture flags at least one default");
  const html = renderToStaticMarkup(<LpbfDefaultsNote lpbf={lpbf} />);
  assert.match(html, /^<span role="note" data-testid="lpbf-defaults-applied"/);
  assert.ok(html.includes(`Unsourced defaults in use (${lpbf.defaultsApplied!.length})`));
  assert.match(html, /<details class="inline"><summary[^>]*>show which<\/summary>/);
  assert.ok(!/<details[^>]*\bopen/.test(html), "closed by default");
  assert.match(html, /Unsourced defaults or class heuristics in use: /);
  assert.equal(renderToStaticMarkup(<LpbfDefaultsNote lpbf={{ ...lpbf, defaultsApplied: [] }} />), "");
});

test("scientific context: collapsed form hides the block behind its title, plain form is unchanged", () => {
  const plain = renderToStaticMarkup(<ScientificContextPanel moduleId="3d-distortion-lab" specimen={specimen} />);
  const folded = renderToStaticMarkup(<ScientificContextPanel moduleId="3d-distortion-lab" specimen={specimen} collapsed />);
  assert.ok(!plain.includes("<details"));
  assert.match(folded, /<details><summary[^>]*><p class="mk-kicker">Scientific context · interpretation<\/p><h2 id="scientific-context-title"[^>]*>LPBF process physics<\/h2><\/summary>/);
  assert.ok(!/<details[^>]*\bopen/.test(folded));
  for (const text of ["Mechanism", "What drives the result", "How to read it", "Limitation: "]) {
    assert.ok(plain.includes(text) && folded.includes(text), text);
  }
  assert.equal(renderToStaticMarkup(<ScientificContextPanel moduleId="database" specimen={specimen} collapsed />), "");
});

test("App places the LPBF scientific context after the module views, collapsed; other modules keep it above", () => {
  const app = read("src/App.tsx");
  assert.ok(CONTEXT_AFTER_MODULE.has("3d-distortion-lab"));
  const views = app.indexOf("{visited.map(id =>");
  const after = app.indexOf("CONTEXT_AFTER_MODULE.has(activeTab) && <div");
  const above = app.indexOf("!CONTEXT_AFTER_MODULE.has(activeTab) && <SilentBoundary>");
  assert.ok(above > 0 && above < views && after > views, "above for others, below the module for LPBF");
  assert.match(app, /<ScientificContextPanel moduleId=\{activeTab\} specimen=\{specimen\} collapsed \/>/);
});

test("warnings: first stays visible, the rest are 'N more notes' (singular for one)", () => {
  assert.equal(moreNotesLabel(1), "1 more note");
  assert.equal(moreNotesLabel(3), "3 more notes");
  const list = renderToStaticMarkup(<WarningNotes warnings={["Severe first", "second", "third"]} />);
  assert.ok(list.indexOf("Severe first") < list.indexOf("<details"), "first outside the disclosure");
  assert.ok(list.indexOf("<details") < list.indexOf("second"));
  assert.match(list, /<summary[^>]*>2 more notes<\/summary>/);
  assert.ok(!/<details[^>]*\bopen/.test(list));
  assert.ok(!renderToStaticMarkup(<WarningNotes warnings={["only"]} />).includes("<details"));
  assert.equal(renderToStaticMarkup(<WarningNotes warnings={[]} />), "");
  const est = renderToStaticMarkup(<EstimateWarnings warnings={["a", "b"]} />);
  assert.match(est, /1 more note/);
  assert.match(est, /hidden=""/);
});

test("Ti64 evaporative result list uses the fold (source guard)", () => {
  assert.match(read("src/components/Ti64EvaporativePanel.tsx"), /<WarningNotes [^>]*warnings=\{result\.warnings\}/);
});
