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
  assert.notEqual(BUILD_JOB_SOLVER_REVISION, "lpbf-build-job-p1-sourced-v21");
  assert.notEqual(BUILD_JOB_SOLVER_REVISION, "lpbf-build-job-p1-sourced-v22");
  assert.notEqual(BUILD_JOB_SOLVER_REVISION, "lpbf-build-job-p6-containment-v23");
  assert.notEqual(BUILD_JOB_SOLVER_REVISION, "lpbf-build-job-p7a-rules-and-nulls-v24");
  assert.equal(BUILD_JOB_SOLVER_REVISION, "lpbf-build-job-solt-v27");
});

test("all SOL-A Build Job kinetics with no eligible history show only the Python reason", () => {
  for (const [name, block] of Object.entries(BLOCKS) as [string, any][]) {
    const markup = html(name);
    assert.equal(block.status, "unavailable", name);
    assert.equal(metric(markup, "Kinetics"), "Unavailable", name);
    assert.ok(text(markup).includes(block.reason), name);
    for (const tile of NUMBER_TILES) assert.equal(metric(markup, tile), null, name);
    assert.equal(block.buildCoolingRate_C_s, null, name);
  }
});
