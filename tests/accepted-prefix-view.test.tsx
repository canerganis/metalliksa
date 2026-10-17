import React from "react";
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { renderToStaticMarkup } from "react-dom/server";
import { AcceptedPrefixView } from "../src/components/3d-distortion-lab/AcceptedPrefixView";
import { parseSimulationJob } from "../src/services/lpbfSimulationService";

const fixture = (): any => JSON.parse(readFileSync(new URL("./fixtures/accepted-prefix/ti64-boiling-job.json", import.meta.url), "utf8"));

test("boiling-limit job renders the accepted prefix", () => {
  const job = parseSimulationJob(fixture());
  assert.equal(job.errorKind, "validation");
  const html = renderToStaticMarkup(<AcceptedPrefixView refusal={job.refusal!} />);
  assert.ok(html.includes("Uncalibrated estimate"));
  assert.ok(/Only the interval from 0 s to [^ ]+ s was computed\./.test(html));
  assert.ok(html.includes("Uncertainty is unknown and may be large. Calibrate to your machine for better accuracy."));
  assert.ok(html.includes("maximum over the computed interval"));
  assert.equal(html.split("data-prefix-point=").length - 1, 5);
  assert.ok(html.includes("data-estimate-warnings-toggle"));
  assert.ok(html.includes(job.refusal!.detail.acceptedPrefix!.completeHistoryText));
  assert.ok(!/error bar/i.test(html));
  assert.ok(!html.includes("—") && !html.includes("–"));
});

test("no-value prefix shows noValueText", () => {
  const raw = fixture();
  Object.assign(raw.refusal.detail.acceptedPrefix, { points: [], acceptedSteps: 0, estimateTier: "no-value", tierLabel: "No value",
    displaySignificantDigits: null, uncertaintyStatement: null, explanation: null, noValueText: "No history available." });
  const html = renderToStaticMarkup(<AcceptedPrefixView refusal={parseSimulationJob(raw).refusal!} />);
  assert.ok(html.includes("No history available."));
  assert.ok(!html.includes("data-prefix-points"));
});

test("malformed prefix is rejected, failed job without refusal still parses", () => {
  const bad = fixture();
  bad.refusal.detail.acceptedPrefix.acceptedSteps = "many";
  assert.throws(() => parseSimulationJob(bad));
  const plain = fixture();
  delete plain.refusal; delete plain.errorKind;
  assert.equal(parseSimulationJob(plain).status, "failed");
  const wrong = fixture();
  wrong.status = "running";
  assert.throws(() => parseSimulationJob(wrong));
});
