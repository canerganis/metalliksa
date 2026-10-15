import React from "react";
import test from "node:test";
import assert from "node:assert/strict";
import { renderToStaticMarkup } from "react-dom/server";
import { ConvergencePanel } from "../src/components/3d-distortion-lab/LpbfResultPresentation";
import { SOLIDIFICATION_WORDING } from "../src/utils/solidificationDisplay";
import type { SimulationResult } from "../src/services/lpbfSimulationService";
test("transient G/R convergence checks appear under the unadmitted-liquidus single-mesh heading", () => {
  const study = { kind: "mesh", status: "incomplete", checks: {
    thermalGradient_K_m: { status: "not-converged", observedOrder: 1.2, fineGCI_pct: 5 },
    width_um: { status: "converged", observedOrder: 2, fineGCI_pct: 1 },
  } } as unknown as SimulationResult["convergenceStudy"];
  const html = renderToStaticMarkup(<ConvergencePanel study={study} />);
  const transient = html.slice(html.indexOf("data-transient-convergence"));
  assert.ok(transient.includes(SOLIDIFICATION_WORDING.transientHeading));
  assert.ok(transient.includes("thermalGradient_K_m"));
  assert.ok(!html.slice(0, html.indexOf("data-transient-convergence")).includes("thermalGradient_K_m"));
  assert.ok(html.slice(0, html.indexOf("data-transient-convergence")).includes("width_um"));
});
