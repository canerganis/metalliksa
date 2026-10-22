import assert from "node:assert/strict";
import { mock, test } from "node:test";
import { readFileSync } from "node:fs";
import { createDeferredCommit } from "../src/utils/deferredCommit";
import { SLIDER_COMMIT_DELAY_MS } from "../src/components/CALPHADMultiComponentStudio";

test("without a slider edit a value is committed at once (presets, shared-material sync)", () => {
  const seen: number[] = [];
  const commit = createDeferredCommit<number>(v => seen.push(v), 800);
  commit.value(1);
  commit.value(2);
  assert.deepEqual(seen, [1, 2]);
});

test("a drag commits once, on release, not once per input event", () => {
  mock.timers.enable({ apis: ["setTimeout"] });
  try {
    const seen: number[] = [];
    const commit = createDeferredCommit<number>(v => seen.push(v), 800);
    for (const v of [1, 2, 3, 4, 5]) { commit.touch(); commit.value(v); mock.timers.tick(100); }
    assert.deepEqual(seen, [], "nothing is committed while the slider moves");
    commit.release();
    assert.deepEqual(seen, [5], "the last value is committed on release");
    mock.timers.tick(5000);
    assert.deepEqual(seen, [5], "the quiet timer does not commit it again");
  } finally { mock.timers.reset(); }
});

test("without a release the last value is committed 800 ms after the last change", () => {
  mock.timers.enable({ apis: ["setTimeout"] });
  try {
    const seen: number[] = [];
    const commit = createDeferredCommit<number>(v => seen.push(v), SLIDER_COMMIT_DELAY_MS);
    assert.equal(SLIDER_COMMIT_DELAY_MS, 800);
    commit.touch(); commit.value(1);
    mock.timers.tick(799);
    assert.deepEqual(seen, []);
    commit.touch(); commit.value(2); // a new change restarts the quiet period
    mock.timers.tick(799);
    assert.deepEqual(seen, []);
    mock.timers.tick(1);
    assert.deepEqual(seen, [2]);
    commit.value(3); // pending is over: the next non-slider value commits at once
    assert.deepEqual(seen, [2, 3]);
  } finally { mock.timers.reset(); }
});

test("a preset (reset) drops a pending slider commit and applies at once", () => {
  mock.timers.enable({ apis: ["setTimeout"] });
  try {
    const seen: number[] = [];
    const commit = createDeferredCommit<number>(v => seen.push(v), 800);
    commit.touch(); commit.value(1);
    commit.reset(); commit.value(9);
    mock.timers.tick(2000);
    assert.deepEqual(seen, [9]);
  } finally { mock.timers.reset(); }
});

test("the studio feeds only the committed composition to the request and shows the 20 to 45 s notice (source guard)", () => {
  const src = readFileSync("src/components/CALPHADMultiComponentStudio.tsx", "utf8");
  assert.match(src, /calphadRequestKey\(\s*committedAlloy\.elements/);
  assert.match(src, /\.solveCalphadEquilibrium\(\s*committedAlloy,/);
  assert.match(src, /onPointerUp=\{releaseSlider\}/);
  assert.match(src, /onBlur=\{releaseSlider\}/);
  assert.ok(src.includes("supersedeKey: supersedeKey.current"), "supersede behaviour kept");
  assert.ok(src.includes("Calculating, typically 20 to 45 s (the first run per element set compiles models)"));
});
