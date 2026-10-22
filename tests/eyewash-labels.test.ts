import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const src = (path: string) => readFileSync(path, "utf8");

test("shell: status chip does not claim engine connection; boot row says the registry is bundled, not probed", () => {
  const app = src("src/App.tsx");
  assert.doesNotMatch(app, /Engine connected/);
  assert.match(app, /Calculation engine ready/);
  const boot = src("src/services/bootSteps.ts");
  assert.match(boot, /Module registry \(bundled\)/);
  assert.match(boot, /not probed/);
});

test("database: no 'Calibrated' composition claim and no pooled-family correlation mode", () => {
  assert.doesNotMatch(src("src/components/MaterialsDatabaseView.tsx"), /Calibrated chemical compositions/);
  const heatmap = src("src/components/MaterialsPropertyHeatmapD3.tsx");
  assert.doesNotMatch(heatmap, /property-correlation|Pearson|Correlation \(r\) Matrix|correlationData/);
});

test("database contract text no longer describes the removed correlation mode", () => {
  assert.doesNotMatch(src("src/generated/moduleRegistry.json"), /Pearson/);
});
