import React from "react";
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { renderToStaticMarkup } from "react-dom/server";
import { BuildJobKineticsPanel } from "../src/components/3d-distortion-lab/BuildJobKineticsPanel";
import { BUILD_JOB_SOLVER_REVISION } from "../src/store/useLpbfBuildJobStore";

// Real Python output: python/test_lpbf_build_job.py check_kinetics_fixture() fails when this file differs from
// build_job_kinetics (regenerate with `python test_lpbf_build_job.py --write-kinetics-fixture`).
const read = (path: string) => readFileSync(new URL(`../${path}`, import.meta.url), "utf8");
const BLOCKS = JSON.parse(read("tests/fixtures/build-job-kinetics-blocks.json"));
const html = (name: string) => {
  assert.ok(BLOCKS[name], name);
  return renderToStaticMarkup(<BuildJobKineticsPanel kinetics={BLOCKS[name]} />);
};
const text = (markup: string) => markup.replace(/<[^>]+>/g, " ").replace(/&#x27;/g, "'").replace(/\s+/g, " ");
const metric = (markup: string, label: string): string | null => {
  const m = new RegExp(`data-kinetics-metric="${label.replace(/[()]/g, "\\$&")}"[^>]*>(.*?)</div></div>`).exec(markup);
  if (!m) return null;
  const values = [...m[1].matchAll(/<div[^>]*>([^<]*)<\/div>/g)].map((x) => x[1]);
  return values[1] ?? null; // [label, value, hint]
};
const NUMBER_TILES = ["Primary Phase", "Martensite", "Hardness (HRC)", "Hardness (HV)"];

test("TS and Python build-job solver revisions are the same string", () => {
  const py = /^BUILD_JOB_SOLVER_REVISION = "([^"]+)"/m.exec(read("python/lpbf_job_cache.py"));
  assert.ok(py);
  assert.equal(BUILD_JOB_SOLVER_REVISION, py[1]);
  assert.notEqual(BUILD_JOB_SOLVER_REVISION, "lpbf-build-job-core-peak-field-v2");
  assert.notEqual(BUILD_JOB_SOLVER_REVISION, "lpbf-build-job-kinetics-same-alloy-v3");
  assert.notEqual(BUILD_JOB_SOLVER_REVISION, "lpbf-build-job-kinetics-steel-only-v4");
  assert.notEqual(BUILD_JOB_SOLVER_REVISION, "lpbf-build-job-microstructure-projection-v5");
  assert.notEqual(BUILD_JOB_SOLVER_REVISION, "lpbf-build-job-kinetics-li1998-v6");
  assert.notEqual(BUILD_JOB_SOLVER_REVISION, "lpbf-build-job-extent-status-v6");
  assert.notEqual(BUILD_JOB_SOLVER_REVISION, "lpbf-build-job-kinetics-li1998-extent-v7");
  assert.notEqual(BUILD_JOB_SOLVER_REVISION, "lpbf-build-job-kinetics-li1998-extent-v8");
  assert.notEqual(BUILD_JOB_SOLVER_REVISION, "lpbf-build-job-flat-absorptivity-peak-extent-v10");
  assert.notEqual(BUILD_JOB_SOLVER_REVISION, "lpbf-build-job-waveb-front-field-marangoni-v11");
  assert.notEqual(BUILD_JOB_SOLVER_REVISION, "lpbf-build-job-eagar-tsai-balling-screen-v12");
  assert.notEqual(BUILD_JOB_SOLVER_REVISION, "lpbf-build-job-eagar-tsai-balling-screen-v13");
  assert.notEqual(BUILD_JOB_SOLVER_REVISION, "lpbf-build-job-eagar-tsai-balling-screen-v14");
  assert.notEqual(BUILD_JOB_SOLVER_REVISION, "lpbf-build-job-eagar-tsai-balling-screen-v15");
  assert.notEqual(BUILD_JOB_SOLVER_REVISION, "lpbf-build-job-la6-gusarov-v19");
  assert.notEqual(BUILD_JOB_SOLVER_REVISION, "lpbf-build-job-in625-regime-v20");
  assert.equal(BUILD_JOB_SOLVER_REVISION, "lpbf-build-job-p1-sourced-v22");
});

test("316L and AlSi10Mg: one Unavailable tile with the reason, no numbers, no substituted alloy", () => {
  for (const [name, alloy] of [["ss316l_no_model", "316L Stainless Steel"], ["alsi10mg_no_model", "AlSi10Mg"]]) {
    const markup = html(name);
    assert.equal(metric(markup, "Kinetics"), "Unavailable", name);
    for (const tile of NUMBER_TILES) assert.equal(metric(markup, tile), null, `${name} renders ${tile}`);
    assert.ok(text(markup).includes(`no kinetics model for ${alloy}.`), name);
    assert.ok(!/4140|7075|Martensitic|Pearlite|%/.test(text(markup)), name);
  }
});

test("degenerate solidification front (1 K/s floor): Unavailable, never the 1 °C/s anneal row", () => {
  const markup = html("in718_degenerate_floor");
  assert.equal(metric(markup, "Kinetics"), "Unavailable");
  for (const tile of NUMBER_TILES) assert.equal(metric(markup, tile), null, tile);
  assert.ok(text(markup).includes("cooling rate is the 1 K/s floor of a degenerate solidification front, not a computed build rate."));
  assert.ok(!/Diffusional|Pearlite|CCT row 1 /.test(text(markup)));
});

test("IN718 / Ti-6Al-4V (above the CCT map or in it): Unavailable, kinetics model is steel-only, no steel values", () => {
  for (const [name, alloy] of [
    ["in718_above_map", "Inconel 718"],
    ["ti6al4v_above_map", "Ti-6Al-4V"],
    ["in718_in_map_30", "Inconel 718"],
    ["ti6al4v_in_map_30", "Ti-6Al-4V"],
  ]) {
    assert.equal(BLOCKS[name].status, "unavailable", name);
    const markup = html(name);
    assert.equal(metric(markup, "Kinetics"), "Unavailable", name);
    for (const tile of NUMBER_TILES) assert.equal(metric(markup, tile), null, `${name} renders ${tile}`);
    const t = text(markup);
    assert.ok(t.includes(`kinetics model is steel-only: ${alloy} is not a steel.`), `${name}: ${t}`);
    assert.ok(!/Full Martensitic|Pearlite|Bainite|CCT row|\d%|null|NaN|undefined/.test(t), `${name}: ${t}`);
  }
});

test("hypothetical steel in-map rate (no build-job alloy is a steel): the Python-selected row, martensite where Ms is physical", () => {
  // The fixture maps AISI 4140 into the build job for this case only (python/test_lpbf_build_job.py), to keep the
  // "selected row" display path under test.
  const steel = BLOCKS.aisi4140_in_map_30_hypothetical;
  assert.equal(steel.status, "available");
  const row = steel.cctContinuousCoolingMap[steel.buildCoolingRateCctRow.rowIndex];
  assert.equal(row.coolingRate_C_s, 25);
  assert.notEqual(steel.buildCoolingRateCctRow.rowIndex, 0);
  const markup = html("aisi4140_in_map_30_hypothetical");
  // Lane kin-li: at 25 °C/s the Li (1998) model reaches no diffusional start above Ms (AISI 4140 critical cooling
  // rate 19.81 °C/s): the row is the athermal Ms row. Hardness is not computed by the Li model -> Unavailable.
  assert.equal(row.primaryMicrostructure, "Martensite (Athermal)");
  assert.equal(metric(markup, "Primary Phase"), "Martensite (Athermal)");
  assert.equal(row.predictedHardness_HRC, null);
  assert.equal(metric(markup, "Hardness (HRC)"), "Unavailable");
  assert.equal(metric(markup, "Hardness (HV)"), "Unavailable");
  assert.equal(metric(markup, "Martensite"), `${steel.buildRateMartensite.predictedMartensite_pct}%`);
  const t = text(markup);
  assert.ok(t.includes("CCT row 25 °C/s (nearest on a log scale to the build cooling rate 30 °C/s)."), t);
  assert.ok(t.includes("At build rate 30 °C/s"));
  assert.ok(t.includes(steel.buildRateMartensite.verdict));
  assert.ok(!/null|NaN|undefined/.test(t), t);
});

test("no kinetics block renders nothing", () => {
  assert.equal(renderToStaticMarkup(<BuildJobKineticsPanel kinetics={null} />), "");
});
