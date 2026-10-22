import React from "react";
import test from "node:test";
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { renderToStaticMarkup } from "react-dom/server";
import katex from "katex";
import { HowCalculated } from "../src/components/HowCalculated";
import { p8ExplainerContext } from "../src/components/Ti64EvaporativePanel";
import { p8ViewFromRun } from "../src/utils/ti64EvaporativeResearchDepth";
import { fixtures as ti64Fixtures } from "./support/ti64EvaporativeFixtures";
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

const ti64Result = () => ti64Fixtures.w1Onset.result;
const p8Context = () => p8ExplainerContext(ti64Result(), p8ViewFromRun(ti64Fixtures.p8Above));

test("every input path of every explainer exists in a real solver result", () => {
  const contexts: Record<string, any> = {
    "meltpool-geometry": fixture("rosenthal"),
    "enthalpy-gates": fixture("rosenthal"),
    "ti64-evaporation": ti64Result(),
    "p8-linked-depth": p8Context(),
    "solidification-estimates": JSON.parse(readFileSync(new URL("./fixtures/solidification-estimates/ti64-conduction.json", import.meta.url), "utf8")),
  };
  assert.deepEqual(Object.keys(contexts).sort(), Object.keys(CALCULATION_EXPLAINERS).sort());
  for (const [id, context] of Object.entries(contexts)) {
    for (const input of CALCULATION_EXPLAINERS[id].inputs) assert.notEqual(readResultPath(context, input.path), undefined, `${id}: ${input.path}`);
  }
});

test("Ti-6Al-4V evaporation panel shows this run's declared scenario and the code's constants", () => {
  const r = ti64Result();
  const html = renderToStaticMarkup(<HowCalculated explainerId="ti64-evaporation" result={r} />);
  assert.ok(html.includes("<details") && !/<details[^>]*sopen/.test(html));
  assert.ok(html.includes(`${r.provenance.inputs.evaporation.transitionHigh_K} K`));
  assert.ok(html.includes(`${r.provenance.vaporSource.latentHeat_J_kg} J/kg`));
  assert.ok(html.includes(`${r.provenance.inputs.evaporation.surfaceTension_N_m} N/m`));
  for (const id of ["vapour-pressure", "mass-flux", "recoil", "bridge", "heat-loss", "onset"]) assert.ok(html.includes(`data-equation-id="${id}"`), id);
});

test("P8 linked depth panel reads only the served view and the run inputs; material constants stay symbol only", () => {
  const context = p8Context();
  const html = renderToStaticMarkup(<HowCalculated explainerId="p8-linked-depth" result={context} />);
  assert.ok(html.includes(`${context.p8.linkedMeltDepth_um} um`));
  assert.ok(html.includes(String(context.p8.powerOverOnset)));
  for (const id of ["threshold-temperature", "onset-power", "cavity-balance", "thermal-g", "absorptance", "partition", "field", "model-depth", "conduction-depth", "linked-depth"]) assert.ok(html.includes(`data-equation-id="${id}"`), id);
});

test("the P8 and evaporation constants match the python source", () => {
  const evap = readFileSync(repoFile("python/lpbf_ti64_evaporation.py"), "utf8");
  const arm = readFileSync(repoFile("python/lpbf_research_arm.py"), "utf8");
  for (const line of [
    "mass = (1.0 - return_fraction) * saturation * np.sqrt(",
    "recoil = (1.0 + return_fraction) * saturation / 2.0",
    "threshold = 2.0 * config.surfaceTension_N_m / radius",
    "a = 3.0 * delta - scaled_slope",
    "b = scaled_slope - 2.0 * delta",
    "mass_slope = mass * (pressure_log_slope - 0.5 * inverse_temperature)",
  ]) assert.ok(evap.includes(line), line);
  for (const line of [
    "denominator=1-math.log(2/(1+beta_recoil))/c",
    "gain=math.sqrt(2)*mat.A0/(a*mat.K*math.pi**1.5)*math.atan(math.sqrt(8*mat.alpha/(v*a)))",
    "qs=s['A']*s['P'] if s['P']<=onset else s['A']*(OUTSIDE*s['P']+INSIDE*onset)",
    "qc=0. if s['P']<=onset else INSIDE*(ac*s['P']-s['A']*onset)",
    "linkedMeltDepth_um=max(depth,floor)",
    "for n in range(1, 25)",
    "return INSIDE * A_R(R, A0, form) + OUTSIDE * A0",
  ]) assert.ok(arm.includes(line), line);
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

const estimates = (name: string): any =>
  JSON.parse(readFileSync(new URL(`./fixtures/solidification-estimates/${name}-conduction.json`, import.meta.url), "utf8"));

test("solidification estimates panel shows only the spacing law of the result's alloy, with this run's values", () => {
  const expected: Record<string, string> = { ti64: "spacing-ti64", alsi10mg: "spacing-alsi", ss316l: "spacing-316l", in718: "spacing-ni" };
  for (const [name, id] of Object.entries(expected)) {
    const r = estimates(name);
    const html = renderToStaticMarkup(<HowCalculated explainerId="solidification-estimates" result={r} />);
    assert.ok(html.includes(`data-equation-id="${id}"`), `${name} ${id}`);
    for (const other of Object.values(expected).filter((x) => x !== id)) assert.ok(!html.includes(`data-equation-id="${other}"`), `${name} not ${other}`);
    for (const id2 of ["gradient", "rate", "summary", "capillary-gate"]) assert.ok(html.includes(`data-equation-id="${id2}"`));
    assert.ok(html.includes(`${r.quantities.thermalGradient.value} K/m`), name);
    assert.ok(html.includes(`${r.quantities.coolingRate.value} K/s`), name);
  }
});

test("every solidification input path that carries a number exists in the real estimate payloads", () => {
  for (const name of ["ti64", "alsi10mg", "ss316l", "in718"]) {
    const r = estimates(name);
    for (const input of CALCULATION_EXPLAINERS["solidification-estimates"].inputs.filter((i) => !i.path.endsWith("pdas.value") && !i.path.endsWith("sdas.value"))) {
      assert.notEqual(readResultPath(r, input.path), undefined, `${name} ${input.path}`);
    }
  }
});

test("the solidification estimate constants match the python source", () => {
  const src = readFileSync(repoFile("python/lpbf_solidification_estimates.py"), "utf8");
  for (const line of [
    "R = v * gx / G", "cooling = v * gx", "g_over_r = G * G / (v * gx)",
    "return law[\"a\"] * base ** -law[\"n\"] * 1e-6", "a = law[\"intercept\"] - law[\"slope\"] * al_wt",
    "return 2.0 * math.pi * math.sqrt(p[\"gamma\"] / drive)", "return p[\"m\"] * p[\"c\"] * (1.0 - p[\"k\"]) / p[\"k\"]",
    "NI_HUNT_A = 1.1773863284676703e-3", "NI_KF_A = 2.5821435943712695e-3",
    "NI_KE, NI_GAMMA, NI_DT0, NI_DL = 0.48, 3.65e-7, 57.0, 3.0e-9",
    "{\"definition\": \"pdas-correlation\", \"slope\": 62.0, \"intercept\": 699.0, \"n\": 0.39",
    "{\"definition\": \"sdas\", \"slope\": 33.0, \"intercept\": 366.0, \"n\": 0.40",
    "{\"definition\": \"pdas-correlation\", \"a\": 165.0, \"n\": 0.4", "{\"definition\": \"sdas\", \"a\": 22.0, \"n\": 2.0 / 3.0, \"uses\": \"R_mm_s\"",
    "{\"definition\": \"pdas-correlation\", \"a\": 80.0, \"n\": 0.33", "{\"definition\": \"sdas\", \"a\": 25.0, \"n\": 0.28",
    "\"sdas\": {\"definition\": \"sdas\", \"a\": 19.5, \"n\": 0.63",
  ]) assert.ok(src.includes(line), line);
});
