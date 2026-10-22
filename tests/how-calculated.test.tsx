import React from "react";
import test from "node:test";
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { renderToStaticMarkup } from "react-dom/server";
import katex from "katex";
import { HowCalculated } from "../src/components/HowCalculated";
import {
  CALCULATION_EXPLAINERS, equationsForKernel, kernelOfModelId, readResultPath,
} from "../src/data/calculationExplainers";

const fixture = (kernel: string): any =>
  JSON.parse(readFileSync(new URL(`./fixtures/how-calculated/meltpool-${kernel}-ti64.json`, import.meta.url), "utf8"));
const repoFile = (rel: string) => new URL(`../${rel}`, import.meta.url);

test("panel is collapsed by default and shows run inputs, equations, code and source locators", () => {
  const html = renderToStaticMarkup(<HowCalculated explainerId="meltpool-geometry" result={fixture("rosenthal")} />);
  assert.ok(html.includes("<details"));
  assert.ok(!/<details[^>]*\sopen/.test(html), "collapsed by default");
  assert.ok(html.includes("How this is calculated"));
  assert.ok(html.includes("data-run-inputs"));
  assert.ok(html.includes("data-equations"));
  assert.ok(html.includes("Code:") && html.includes("Source:"));
  // Values come from the result object, unchanged.
  const r = fixture("rosenthal");
  assert.ok(html.includes(`${r.processParameters.laserPower_W} W`));
  assert.ok(html.includes(`${r.meltPoolGeometry.width_um} um`));
  assert.ok(html.includes(`${r.processParameters.volumetricEnergyDensity_J_mm3} J/mm^3`));
  assert.ok(html.includes(String(r.meltPoolGeometry.extentStatus)));
});

test("only the equation of the result's kernel is listed", () => {
  const ex = CALCULATION_EXPLAINERS["meltpool-geometry"];
  const ids = (k: string) => equationsForKernel(ex, kernelOfModelId(fixture(k).modelId)).map((e) => e.id);
  assert.ok(ids("rosenthal").includes("rosenthal") && !ids("rosenthal").includes("eagar-tsai") && !ids("rosenthal").includes("goldak"));
  assert.ok(ids("eagar-tsai").includes("eagar-tsai") && !ids("eagar-tsai").includes("rosenthal"));
  assert.ok(ids("goldak").includes("goldak") && !ids("goldak").includes("rosenthal"));
  for (const k of ["rosenthal", "eagar-tsai", "goldak"]) for (const id of ["width", "length", "depth", "fabbro", "ved"]) assert.ok(ids(k).includes(id), `${k} ${id}`);
});

test("a value the result does not carry is shown as symbol only, never filled in", () => {
  const r = fixture("rosenthal");
  delete r.processParameters.fieldPower_W;
  const html = renderToStaticMarkup(<HowCalculated explainerId="meltpool-geometry" result={r} />);
  assert.ok(html.includes("symbol only, not in this result"));
});

test("result notes (caveats, extent status) are shown verbatim", () => {
  const r = fixture("rosenthal");
  const html = renderToStaticMarkup(<HowCalculated explainerId="enthalpy-gates" result={r} />).replace(/&#x27;/g, "'").replace(/&quot;/g, "\"").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&amp;/g, "&");
  assert.ok(html.includes(r.meltPoolGeometry.regimeBasis));
  assert.ok(html.includes(r.meltPoolGeometry.regimeKeyholeCutBasis));
  assert.ok(html.includes(String(r.meltPoolGeometry.regimeKeyholeThreshold)));
});

test("every explainer equation renders in KaTeX without error and has an accessible plain text, locators and symbols", () => {
  for (const ex of Object.values(CALCULATION_EXPLAINERS)) {
    assert.ok(ex.equations.length > 0);
    for (const eq of ex.equations) {
      const html = katex.renderToString(eq.latex, { displayMode: true, throwOnError: true, output: "html" });
      assert.ok(html.includes("katex"), eq.id);
      assert.ok(eq.plain.length > 8 && eq.codeLocator.length > 8 && eq.sourceLocator.length > 8 && eq.symbols.length > 0, eq.id);
      for (const text of [eq.label, eq.plain, eq.codeLocator, eq.sourceLocator, eq.asImplemented ?? "", ...eq.symbols.flat()]) {
        assert.ok(!text.includes("\u2014") && !text.includes("\u2013"), `no dash punctuation in ${eq.id}`);
      }
    }
  }
});

test("every code locator names an existing file and, where written file:name, a name present in it", () => {
  for (const ex of Object.values(CALCULATION_EXPLAINERS)) {
    for (const eq of ex.equations) {
      for (const m of eq.codeLocator.matchAll(/(python\/[\w]+\.py)(?::([A-Za-z_]\w*))?/g)) {
        assert.ok(existsSync(repoFile(m[1])), `${eq.id}: ${m[1]} exists`);
        if (m[2]) assert.ok(readFileSync(repoFile(m[1]), "utf8").includes(m[2]), `${eq.id}: ${m[1]} contains ${m[2]}`);
      }
    }
  }
});

test("every input path of every explainer exists in a real solver result", () => {
  for (const ex of [CALCULATION_EXPLAINERS["meltpool-geometry"], CALCULATION_EXPLAINERS["enthalpy-gates"]]) {
    const r = fixture("rosenthal");
    for (const input of ex.inputs) assert.notEqual(readResultPath(r, input.path), undefined, input.path);
  }
});

test("the equation constants match the python constants they transcribe", () => {
  const thermal = readFileSync(repoFile("python/lpbf_thermal_solver.py"), "utf8");
  const fabbro = readFileSync(repoFile("python/fabbro_keyhole.py"), "utf8");
  assert.match(thermal, /ENTHALPY_TRANSITION = 15\.0/);
  assert.match(thermal, /ENTHALPY_KEYHOLE = 20\.0/);
  assert.match(thermal, /ENTHALPY_KEYHOLE_IN625 = 13\.6/);
  assert.match(fabbro, /FABBRO_M = 2\.4/);
  assert.match(fabbro, /FABBRO_N = 3\.0/);
  assert.match(fabbro, /ENTHALPY_ONSET = 15\.0/);
  assert.match(fabbro, /ENTHALPY_KEYHOLE = 30\.0/);
  assert.match(thermal, /d_beam \* 0\.55/);
  assert.match(thermal, /math\.sqrt\(math\.pi \* alpha_solid \* v_scan \* \(r_beam \*\* 3\)\)/);
});
