import React from "react";
import assert from "node:assert/strict";
import { renderToStaticMarkup } from "react-dom/server";
import { ResultHeader, ConvergencePanel, MeasurementPanel, ThermalHistory, StaleResultBanner, jobContextLabel } from "../src/components/3d-distortion-lab/LpbfResultPresentation";
import { SimulationJob, SimulationResult } from "../src/services/lpbfSimulationService";

const result: SimulationResult = {
  schemaVersion: 1, requestedMode: "screening", effectiveMode: "screening", settings: { material: "Inconel 718", power_W: 40, speed_mm_s: 800, beamDiameter_um: 80, preheat_C: 200, hatch_um: 100, layer_um: 40 },
  solver: { id: "synthetic-presentation-fixture", version: "1", openfoam: null }, confidence: "low", validationStatus: "unvalidated", productionReady: false,
  label: "Screening only", fallbackReason: null, metrics: { length_um: 321, width_um: 123, depth_um: 45 }, material: { name: "Inconel 718", quality: "estimated", source: "Synthetic UI test; not experimental evidence" },
  analyticalComparison: {}, assumptions: [], regime: "conduction assumption", mainRisk: "lack-of-fusion", recommendation: "Reduce hatch spacing; verify experimentally.", riskScope: "Geometric screening only",
};
const job: SimulationJob = { id: "a".repeat(32), status: "completed", progress: 1, log: "fixture", error: null, result };
const render = (j?: SimulationJob, stale = false) => renderToStaticMarkup(<ResultHeader job={j} material="Inconel 718" availability="Unavailable" stale={stale} elapsed={12} cancel={() => {}} cancelling={false}/>);
assert.match(render(job), /321/);
assert.match(render(job), /Experimental validation pending/);
assert.match(render({...job, cacheHit:true}), /Cached · completed/);
// Phase 2 D4: a result computed for earlier inputs must not look current.
{
  const fresh = render(job);
  assert.doesNotMatch(fresh, /Stale/);
  assert.doesNotMatch(fresh, /opacity-75/);
  assert.match(fresh, />completed</);
  for (const staleJob of [job, { ...job, cacheHit: true }]) {
    const html = render(staleJob, true);
    // Prominent banner at the top of the result panel, before any result value.
    const banner = html.indexOf("Stale: inputs changed since this result");
    assert.ok(banner >= 0, "stale banner rendered");
    assert.ok(banner < html.indexOf("321"), "banner precedes the old values");
    assert.ok(banner < html.indexOf("Stale simulation result"), "banner is at the top of the panel");
    assert.match(html, /data-stale-result="true"/);
    // The status chip is downgraded: no plain or cached "completed" chip remains.
    assert.match(html, />Stale · inputs changed</);
    assert.doesNotMatch(html, />completed<|Cached · completed/);
    assert.match(html, /Completed for earlier inputs · 100% reported/);
    assert.match(html, /Stale simulation result/);
    // Old numbers are de-emphasised.
    for (const value of ["321", "123", "45"]) assert.match(html, new RegExp(`<dd class="[^"]*opacity-75[^"]*"[^>]*>${value} `), value);
    assert.match(html, /<p class="mt-2 text-sm leading-6 opacity-75">Reduce hatch spacing/);
    // Evidence and limitation labels stay at full emphasis.
    for (const label of [">Experimental validation pending<", ">Calibration incomplete<", "Goldak · analytical liquidus extent", "Regime · conduction assumption", "Confidence</dt><dd class=\"mt-1.5 break-words text-sm\">low · model evidence limited"]) assert.ok(html.includes(label), label);
    assert.doesNotMatch(html, /opacity-75[^"]*">(Experimental validation pending|Calibration incomplete|Goldak)/);
  }
  // A non-completed job never shows the stale banner (there is no result to mark).
  assert.doesNotMatch(render({ ...job, status: "failed", progress: .5 }, true), /Stale: inputs changed/);
  assert.match(renderToStaticMarkup(<StaleResultBanner/>), /role="status"/);
  assert.equal(jobContextLabel(undefined, null), "not submitted");
  assert.equal(jobContextLabel(job, true), "aaaaaaaa · completed");
  assert.equal(jobContextLabel(job, false), "aaaaaaaa · stale · inputs changed");
  assert.equal(jobContextLabel({ ...job, status: "cancelled" }, null), "aaaaaaaa · cancelled");
}
for (const status of ["queued", "running", "failed", "cancelled", "timed_out"] as const) {
  // Even if an upstream caller supplies stale result data, terminal failures cannot render it.
  const html=render({...job,status,progress:.42});
  assert.doesNotMatch(html,/321/);
  assert.match(html,/42% reported/);
  if(status==="queued"||status==="running") assert.match(html,/>Cancel</);
  else {assert.doesNotMatch(html,/>Cancel</);assert.match(html,/No completed result/);}
}
const cancelledWithPartials = render({ ...job, status: 'cancelled', result: undefined,
  partialArtifacts: { status: 'retained-unverified', fileCount: 2, totalBytes: 4096 } });
assert.match(cancelledWithPartials, /2 partial files retained locally \(4096 bytes\)/);
assert.match(cancelledWithPartials, /Integrity not verified; unavailable as a result\/download and excluded from completed-run archives/);
assert.match(cancelledWithPartials, /No completed result/);
assert.doesNotMatch(cancelledWithPartials, /321/);
assert.doesNotMatch(cancelledWithPartials, />Cancel</);
assert.match(render({ ...job, status: 'failed', result: undefined,
  partialArtifacts: { status: 'inventory-unavailable' } }), /Partial output inventory unavailable; no integrity claim/);
assert.doesNotMatch(render(job), /partial files retained|Partial output inventory unavailable/);
assert.match(renderToStaticMarkup(<ConvergencePanel study={undefined}/>),/Not run/);
assert.match(renderToStaticMarkup(<ConvergencePanel study={undefined}/>),/The boiling validity stop and the peak cell temperature depend on the mesh spacing \(µm\); a verdict at one mesh is not converged evidence\./);
const audit=renderToStaticMarkup(<ConvergencePanel study={{kind:"mesh",spacings:[4e-5,2e-5,1e-5],results:[{width_um:100,depth_um:40},{width_um:110,depth_um:42},{width_um:112,depth_um:43}],checks:{width_um:{status:"inconclusive",reason:"Fixture",observedOrder:2,fineGCI_pct:3}}}}/>);
for(const label of ["Coarse","Medium","Fine","inconclusive","observed order 2","fine GCI 3"]) assert.ok(audit.includes(label));
const alignedStudy=renderToStaticMarkup(<ConvergencePanel study={{kind:"mesh",status:"complete",protocol:"layer-aligned-three-grid-cpu-reference-v1",requestedBackend:"auto",executionBackend:"reference",cellsPerLayer:[1,2,3],spacings:[4e-5,2e-5,1.333e-5],results:[{width_um:100,depth_um:40},{width_um:110,depth_um:42},{width_um:112,depth_um:43}]}}/>);
for(const label of ["Layer-aligned CPU reference study","requested backend: automatic","execution backend: reference","cells per layer: 1 / 2 / 3"]) assert.ok(alignedStudy.includes(label));
const alignedStudyV2=renderToStaticMarkup(<ConvergencePanel study={{kind:"mesh",status:"complete",protocol:"layer-aligned-three-grid-cpu-reference-v2-celik-ratio",requestedBackend:"reference",executionBackend:"reference",cellsPerLayer:[1,2,3],spacings:[4e-5,2e-5,1.333e-5],results:[{width_um:100,depth_um:40},{width_um:110,depth_um:42},{width_um:112,depth_um:43}],checks:{width_um:{status:"inconclusive",reason:"Refinement ratio below 1.3 (Celik et al. 2008 Step 2)"}}}}/>);
for(const label of ["Layer-aligned CPU reference study","cells per layer: 1 / 2 / 3","Refinement ratio below 1.3"]) assert.ok(alignedStudyV2.includes(label));
const incompleteStudy=renderToStaticMarkup(<ConvergencePanel study={{kind:"mesh",status:"failed",spacings:[null,4e-5,2e-5],results:[null,{width_um:100,depth_um:40},{width_um:110,depth_um:42}],checks:{width_um:{status:"failed",reason:"Coarse level source capture below minimum"}}}}/>);
for(const label of ["mesh · failed","Coarse level source capture below minimum","Unavailable"]) assert.ok(incompleteStudy.includes(label));
assert.match(renderToStaticMarkup(<MeasurementPanel result={result}/>),/does not establish independent validation/);
assert.match(renderToStaticMarkup(<ThermalHistory result={result}/>),/Not resolved in this screening run/);
console.log("PASS: result visibility, progress, cancellation/failure/timeout, cache, stale inputs, calibration and numerical evidence rendering");
