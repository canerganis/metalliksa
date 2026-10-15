import React from "react";
import { afterEach, test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { renderToStaticMarkup } from "react-dom/server";
import {
  CALPHAD_CLIENT_TIMEOUT_MS,
  CALPHAD_SERVER_TIMEOUT_MS,
  isAbortError,
  pythonComputationService,
} from "../src/services/pythonComputationService";
import {
  calphadProvenanceLabels,
  calphadUnavailableDetails,
  formatCalphadUnavailable,
  formatCriticalTemperature,
  buildEquilibriumCSV,
  formatFreezingRange,
  isMcTiResult,
  parseCalphadUnavailable,
  partitionSourceNote,
} from "../src/utils/calphadDisplay";
import {
  calphadUnavailableHeadline,
  formatCoverageRow,
  formatModelCache,
  formatPartitionK,
  formatTimings,
  calphadTemperatureWindow,
  clampProbeToRange,
  withOrderingNote,
  calphadRequestKey,
} from "../src/utils/calphadResultDisplay";
import { CALPHADMultiComponentStudio } from "../src/components/CALPHADMultiComponentStudio";
import type { PythonCalphadSolveResult } from "../src/services/pythonComputationService";
import { solveMultiComponentEquilibrium, STANDARD_MULTI_COMPONENT_ALLOYS } from "../src/physics/calphadMultiComponentSolver";
import { parseTDBFile, PRELOADED_MULTI_COMPONENT_TDB } from "../src/physics/tdbParser";

const originalFetch = globalThis.fetch;
afterEach(() => {
  globalThis.fetch = originalFetch;
});

// Real envelope of python/calphad_solver.py on the locked interpreter (no pycalphad), trimmed.
const UNAVAILABLE = {
  success: false,
  status: "unavailable",
  unavailableKind: "pycalphad-not-installed",
  reason: "pycalphad not installed",
  reasons: ["pycalphad not installed"],
  engine: "pycalphad-open-tdb",
  pycalphadAvailable: false,
  pycalphadVersion: null,
  databaseId: "cost507",
  databaseUsed: "COST 507 Comprehensive Light Alloys Database",
  databaseStatus: "assessment",
};
const ALLOY = { name: "Ti-6Al-4V", elements: { Ti: 90, Al: 6, V: 4 }, unit: "wt_pct" as const };

function stubFetch(status: number, body: unknown) {
  globalThis.fetch = (async () =>
    new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } })) as any;
}

test("parseCalphadUnavailable accepts only the unavailable envelope", () => {
  const u = parseCalphadUnavailable({ ...UNAVAILABLE, missingElements: ["Al"] });
  assert.ok(u);
  assert.equal(u!.reason, "pycalphad not installed");
  assert.deepEqual(u!.missingElements, ["Al"]);
  assert.equal(formatCalphadUnavailable(u!), "Python CALPHAD (pycalphad) unavailable: pycalphad not installed.");
  assert.equal(parseCalphadUnavailable({ success: true, equilibriumProfile: [] }), null);
  assert.equal(parseCalphadUnavailable(null), null);
});

test("a null critical temperature renders Unavailable with its reason, never a number or an empty unit", () => {
  const shown = formatCriticalTemperature(null, { status: "unavailable", reason: "the solver reached the grid bound" });
  assert.equal(shown.text, "Unavailable");
  assert.equal(shown.title, "the solver reached the grid bound");
  assert.equal(shown.available, false);
  assert.equal(formatCriticalTemperature(1689.5).text, "1689.5°C");
  assert.equal(formatFreezingRange(null), "Unavailable");
  assert.equal(formatFreezingRange(100), "100 K");
});

test("a client screening result is never labelled as pycalphad", () => {
  const client = calphadProvenanceLabels({ isPythonEngine: false, isEmpirical: true, thermodynamicModel: "x", databaseUsed: "y" });
  assert.equal(client.isPycalphad, false);
  assert.match(client.model, /not CALPHAD/);
  assert.match(client.database, /not an assessment/);
  const python = calphadProvenanceLabels({ isPythonEngine: true, isEmpirical: false, thermodynamicModel: "CEF", databaseUsed: "COST 507" });
  assert.equal(python.isPycalphad, true);
  assert.equal(python.database, "COST 507");
  assert.equal(partitionSourceNote("default-table-not-thermodynamic"), "default screening value, not CALPHAD");
  assert.equal(partitionSourceNote("tie-line"), null);
});

test("solveCalphadEquilibrium keeps the Python reason and returns no numbers (no client substitute)", async () => {
  stubFetch(200, UNAVAILABLE);
  const res = await pythonComputationService.solveCalphadEquilibrium(ALLOY, 500, 1450, 50);
  assert.equal(res.isPythonEngine, false);
  assert.equal(res.pythonUnavailable?.reason, "pycalphad not installed");
  assert.equal(res.pythonUnavailable?.unavailableKind, "pycalphad-not-installed");
  assert.equal(res.equilibriumProfile.length, 0);
  assert.deepEqual(res.criticalTemperatures, { liquidusC: null, solidusC: null, freezingRangeC: null });
  assert.equal(res.solutePartitioning.length, 0);
  assert.equal(res.multiElementScheil.length, 0);
  assert.equal(res.thermodynamicModel, undefined);
  assert.equal(res.engine, "none (pycalphad unavailable)");
});

test("a Python success passes through with null solidus and gamma-prime untouched", async () => {
  stubFetch(200, {
    success: true,
    engine: "pycalphad-open-tdb",
    isEmpirical: false,
    equilibriumProfile: [{ temperatureC: 600, phases: [], totalGibbsEnergy_kJ_mol: -1 }],
    criticalTemperatures: { liquidusC: 1689.5, solidusC: null, freezingRangeC: null, gammaPrimeSolvusC: null },
    criticalTemperatureStatus: { solidusC: { status: "unavailable", reason: "grid bound" } },
  });
  const res = await pythonComputationService.solveCalphadEquilibrium(ALLOY);
  assert.equal(res.isPythonEngine, true);
  assert.equal(res.criticalTemperatures.solidusC, null);
  assert.equal(res.criticalTemperatureStatus?.solidusC?.reason, "grid bound");
  assert.equal(res.pythonUnavailable, undefined);
});

test("Studio first paint says the numbers are not CALPHAD and no longer claims a pycalphad guarantee", () => {
  const markup = renderToStaticMarkup(<CALPHADMultiComponentStudio />);
  const text = markup.replace(/<[^>]+>/g, " ").replace(/&#x27;/g, "'").replace(/&amp;/g, "&").replace(/\s+/g, " ");
  assert.doesNotMatch(text, /True CALPHAD/);
  assert.doesNotMatch(text, /Rigorous Thermodynamic Trust Guarantee/);
  assert.doesNotMatch(text, /Simplified Solvus Minimizer/);
  // review S3 / Sol S4: Python ON, no answer yet -> no screening numbers, no client engine name
  assert.match(text, /No pycalphad result for this input yet\./);
  assert.match(text, /Active Engine: pycalphad \(no result for this input yet\)/);
  assert.doesNotMatch(text, /Liquidus \(T_liq\):/);
  assert.doesNotMatch(text, /MetalliX-Client/);
  // Python explicitly OFF: the client screening model, labelled
  const off = textOf(renderToStaticMarkup(<CALPHADMultiComponentStudio initialUsePython={false} />));
  assert.match(off, /not an assessment/);
  assert.match(off, /Liquidus \(T_liq\):/);
});

// ---- Studio rendering with a solved result (test seams initialResult / initialSubTab) ----
const textOf = (markup: string) =>
  markup.replace(/<[^>]+>/g, " ").replace(/&#x27;/g, "'").replace(/&amp;/g, "&").replace(/&quot;/g, '"').replace(/\s+/g, " ");

function clientBase(): PythonCalphadSolveResult {
  const tdb = parseTDBFile(PRELOADED_MULTI_COMPONENT_TDB[0].rawTdbText, PRELOADED_MULTI_COMPONENT_TDB[0].name);
  const client = solveMultiComponentEquilibrium(ALLOY, tdb, 500, 1450, 50);
  return { ...client, engine: "MetalliX-Client-TS-Solver", computeTimeMs: null, isPythonEngine: false, isEmpirical: true };
}

function pycalphadResult(over: Partial<PythonCalphadSolveResult> = {}): PythonCalphadSolveResult {
  const base = clientBase();
  return {
    ...base,
    engine: "pycalphad-open-tdb",
    isPythonEngine: true,
    isEmpirical: false,
    computeTimeMs: 1234,
    thermodynamicModel: "Compound Energy Formalism (CEF) Gibbs minimisation (pycalphad equilibrium)",
    databaseUsed: "COST 507 Comprehensive Light Alloys Database",
    databaseSuitability: "Light-metal alloys with an Al, Mg or Ti base. Ni-, Fe- and Co-base alloys are outside its assessed scope and are refused.",
    criticalTemperatures: { liquidusC: 1689.5, solidusC: null, freezingRangeC: null, gammaPrimeSolvusC: null, betaTransusC: 932.9 },
    criticalTemperatureStatus: {
      solidusC: { status: "unavailable", reason: "no liquid appears inside the temperature grid, so the solidus is above the grid" },
      gammaPrimeSolvusC: { status: "unavailable", reason: "gamma-prime was identified by phase name only" },
    },
    multiElementScheil: base.multiElementScheil.map((pt) => ({ ...pt, temperatureC: null })),
    multiElementScheilNote: "Compositions follow the Scheil equation; the temperature axis is null when either is unavailable.",
    tcpEmbrittlementRisk: null,
    thermodynamicStabilityIndex: null,
    phacompAnalysis: {
      status: "unavailable",
      reason: "New-PHACOMP (Nv/Md TCP screening) applies to Ni-base superalloys only; this alloy is Ti-base",
      n_v_bar: null, m_d_bar: null, tcpEmbrittlementRisk: null, tcpSigmaRiskTemperatureC: null, thermodynamicStabilityIndex: null,
    },
    ...over,
  };
}

test("Studio shows the unavailable banner with the Python reason, scope and missing elements", () => {
  const result = {
    ...clientBase(),
    pythonUnavailable: {
      unavailableKind: "database-not-assessed-for-base",
      reason: "database 'cost507' is not assessed for Ni-base alloys (assessed base elements: AL, MG, TI)",
      reasons: ["database 'cost507' is not assessed for Ni-base alloys (assessed base elements: AL, MG, TI)"],
      missingElements: ["Cr"],
      databaseUsed: "COST 507 Comprehensive Light Alloys Database",
      databaseSuitability: "Light-metal alloys with an Al, Mg or Ti base.",
    },
  } as PythonCalphadSolveResult;
  const text = textOf(renderToStaticMarkup(<CALPHADMultiComponentStudio initialResult={result} />));
  assert.match(text, /Python CALPHAD \(pycalphad\) unavailable: database 'cost507' is not assessed for Ni-base alloys/);
  assert.match(text, /Elements missing from the database: Cr\./);
  assert.match(text, /Database scope \(COST 507 Comprehensive Light Alloys Database\): Light-metal alloys with an Al, Mg or Ti base\./);
  // calphad-use lane: an unavailable answer is never filled with client screening numbers
  assert.match(text, /Unavailable: no thermodynamic database for this system/);
  assert.match(text, /No equilibrium numbers are shown for this request/);
  assert.match(text, /No equilibrium result/);
  assert.doesNotMatch(text, /Liquidus \(T_liq\):/);
  assert.doesNotMatch(text, /Equilibrium Phase Mole Fractions/);
  assert.match(text, /Compute Time: n\/a/);
  // and no banner without a Python refusal
  const none = textOf(renderToStaticMarkup(<CALPHADMultiComponentStudio initialResult={clientBase()} />));
  assert.doesNotMatch(none, /Python CALPHAD \(pycalphad\) unavailable/);
});

test("Studio shows the database scope and Unavailable cards for a pycalphad result", () => {
  const markup = renderToStaticMarkup(<CALPHADMultiComponentStudio initialResult={pycalphadResult()} />);
  const text = textOf(markup);
  assert.match(text, /Database scope: Light-metal alloys with an Al, Mg or Ti base\./);
  assert.match(text, /Solidus \(T_sol\): Unavailable/);
  assert.match(text, /γ' Solvus: Unavailable/);
  assert.match(text, /Liquidus \(T_liq\): 1689\.5°C/);
  assert.match(text, /TCP Risk: Unavailable/);
  assert.match(text, /Compute Time: 1234 ms/);
  assert.ok(markup.includes("no liquid appears inside the temperature grid"), "reason is the tooltip");
  assert.doesNotMatch(text, /null/);
});

test("Studio no longer claims adaptive refinement", () => {
  const text = textOf(renderToStaticMarkup(<CALPHADMultiComponentStudio initialResult={pycalphadResult()} />));
  assert.doesNotMatch(text, /ADAPTIVE REFINEMENT/);
  assert.doesNotMatch(text, /Adaptive Grid/);
  assert.doesNotMatch(text, /Ultra-Sharp/);
  assert.doesNotMatch(text, /two-pass bisection/);
  assert.match(text, /Liquidus \/ solidus boundary refinement/);
  assert.match(text, /there is no adaptive grid/);
});

test("Studio non-converged grid points are announced, never shown as numbers", () => {
  const text = textOf(renderToStaticMarkup(<CALPHADMultiComponentStudio initialResult={pycalphadResult({ nonConvergedPoints: [800, 825] })} />));
  assert.match(text, /2 grid point\(s\) did not converge and are shown as n\/a: 800, 825 °C\./);
});

test("Scheil tab: a client screening curve with no temperature axis says why instead of an empty chart", () => {
  const client = { ...clientBase(), multiElementScheil: clientBase().multiElementScheil.map((pt) => ({ ...pt, temperatureC: null })) };
  client.criticalTemperatures = { liquidusC: 1689.5, solidusC: null, freezingRangeC: null };
  client.criticalTemperatureStatus = { solidusC: { status: "unavailable", reason: "no liquid appears inside the temperature grid" } };
  const markup = renderToStaticMarkup(
    <CALPHADMultiComponentStudio initialResult={client} initialSubTab="multi_scheil" initialUsePython={false} />);
  const text = textOf(markup);
  assert.ok(markup.includes('data-testid="scheil-unavailable"'));
  assert.match(text, /No temperature axis: the screening curve needs both the liquidus and the solidus\./);
  assert.match(text, /Solidus unavailable: no liquid appears inside the temperature grid/);
  assert.match(text, /not a CALPHAD Scheil calculation/);
});

test("Scheil tab: an unavailable pycalphad Scheil path shows its reason and no chart", () => {
  const result = pycalphadResult({
    multiElementScheil: [],
    scheilSolidification: { status: "unavailable", reason: "the liquidus is not available on this grid, so there is no start temperature", evidence: "unvalidated" },
  });
  const markup = renderToStaticMarkup(<CALPHADMultiComponentStudio initialResult={result} initialSubTab="multi_scheil" />);
  const text = textOf(markup);
  assert.match(text, /Scheil-Gulliver path unavailable: the liquidus is not available on this grid/);
  assert.match(text, /Evidence: unvalidated/);
  assert.ok(!markup.includes("recharts-wrapper"));
  assert.doesNotMatch(text, /screening curve/);
});

test("Scheil tab: a computed pycalphad path shows the engine's own numbers with validity and evidence", () => {
  const result = pycalphadResult({
    criticalTemperatures: { liquidusC: 616.2, solidusC: 576.8, freezingRangeC: 39.4 },
    multiElementScheil: [
      { fractionSolid: 0, temperatureC: 616.5, liquidCompositions: { Al: 93, Si: 7 }, solidCompositions: null, solidPhases: [] },
      { fractionSolid: 0.48, temperatureC: 577.0, liquidCompositions: { Al: 87.5, Si: 12.5 }, solidCompositions: { Al: 98.6, Si: 1.4 }, solidPhases: ["FCC_A1"] },
      { fractionSolid: 1, temperatureC: 576.5, liquidCompositions: null, solidCompositions: { Al: 87.5, Si: 12.5 }, solidPhases: ["DIAMOND_A4", "FCC_A1"] },
    ],
    scheilSolidification: {
      status: "pycalphad-scheil-gulliver",
      terminationReason: "liquid-exhausted-within-step",
      startTemperatureC: 616.5,
      terminalTemperatureC: 576.5,
      terminalBracketC: [576.5, 577.0],
      remainingLiquidFraction: 0,
      stepC: 0.5,
      steps: 80,
      phaseAmounts: { DIAMOND_A4: 0.0556, FCC_A1: 0.9444 },
      massBalanceMaxAbsError: 2e-16,
      fractionBasis: "mole fraction of atoms",
      validity: "Scheil-Gulliver limit: no diffusion in the solid, complete mixing in the liquid.",
      evidence: "unvalidated",
    },
  });
  const text = textOf(renderToStaticMarkup(<CALPHADMultiComponentStudio initialResult={result} initialSubTab="multi_scheil" />));
  assert.match(text, /Scheil-Gulliver solidification path \(pycalphad equilibria of the remaining liquid\)/);
  assert.match(text, /End of solidification between 576\.5 and 577 °C \(liquid-exhausted-within-step\)\./);
  assert.match(text, /Solid formed \(mole fraction of atoms\): DIAMOND_A4 5\.6 %, FCC_A1 94\.4 %/);
  assert.match(text, /mass balance error 2\.0e-16/);
  assert.match(text, /Validity: Scheil-Gulliver limit/);
  assert.match(text, /Evidence: unvalidated/);
  assert.doesNotMatch(text, /not a CALPHAD Scheil calculation/);
});

test("no compute time is invented when the engine reports none", async () => {
  stubFetch(200, { success: true, engine: "pycalphad-open-tdb", equilibriumProfile: [{ temperatureC: 600, phases: [], totalGibbsEnergy_kJ_mol: -1 }] });
  const res = await pythonComputationService.solveCalphadEquilibrium(ALLOY);
  assert.equal(res.computeTimeMs, null);
});

test("unavailable details carry the scope, the missing elements and the convergence counts", () => {
  const u = parseCalphadUnavailable({
    status: "unavailable", unavailableKind: "pycalphad-equilibrium-failed",
    reason: "pycalphad equilibrium failed (non-finite results)", nonConvergedPoints: 39, gridPoints: 39,
    databaseSuitability: "Light-metal alloys.", databaseUsed: "COST 507", missingElements: ["Al"],
  });
  assert.ok(u);
  assert.deepEqual(calphadUnavailableDetails(u!), [
    "Elements missing from the database: Al.",
    "Database scope (COST 507): Light-metal alloys.",
    "39 of 39 grid points did not converge.",
  ]);
});

// ---- calphad-use lane: provenance, cold/warm models, loading state, coverage, partition table ----

test("model cache and timings are shown as reported, never invented", () => {
  assert.equal(formatModelCache(undefined), "Model cache: not reported");
  assert.match(formatModelCache({ status: "warm" }), /^Models: warm/);
  assert.match(formatModelCache({ status: "cold", workspaceBuildMs: 604.3 }), /model construction 604 ms/);
  assert.match(formatModelCache({ status: "not-cached" }), /not cached/);
  assert.equal(formatTimings(undefined), null);
  assert.equal(formatTimings({ gridEquilibrium: 414.57, scheil: 525.9, total: 1439.9, databaseLoad: 0.48 }),
    "database 0.5 ms, grid 415 ms, Scheil path 526 ms, total 1440 ms");
});

test("unavailable headline: no database, no pycalphad, unreachable service", () => {
  const h = (kind: string) => calphadUnavailableHeadline({ unavailableKind: kind, reason: "r", reasons: ["r"] });
  assert.equal(h("no-database-covers-elements"), "Unavailable: no thermodynamic database for this system");
  assert.equal(h("database-not-assessed-for-base"), "Unavailable: no thermodynamic database for this system");
  assert.equal(h("elements-missing-from-database"), "Unavailable: no thermodynamic database for this system");
  assert.match(h("pycalphad-not-installed"), /pycalphad is not installed/);
  assert.match(h("engine-unreachable"), /did not answer/);
});

test("a 5xx or network failure is an unavailable state, not a silent client equilibrium", async () => {
  stubFetch(500, { error: "boom" });
  const res = await pythonComputationService.solveCalphadEquilibrium(ALLOY, 500, 1450, 50);
  assert.equal(res.pythonUnavailable?.unavailableKind, "engine-unreachable");
  assert.match(res.pythonUnavailable?.reason ?? "", /HTTP 500/);
  const text = textOf(renderToStaticMarkup(<CALPHADMultiComponentStudio initialResult={res} />));
  assert.match(text, /Unavailable: the Python CALPHAD service did not answer/);
  assert.doesNotMatch(text, /Liquidus \(T_liq\):/);
});

test("Studio shows provenance with the database hash, warm/cold models and measured timings", () => {
  const result = pycalphadResult({
    pycalphadVersion: "0.11.2",
    modelCache: { status: "warm", databaseSha256: "0123456789abcdef0123", workspaceBuildMs: 0 },
    timingsMs: { databaseLoad: 0.5, workspaceBuild: 0.1, gridEquilibrium: 414.6, boundaryRefinement: 489.7, scheil: 525.9, total: 1439.9 },
  });
  const markup = renderToStaticMarkup(<CALPHADMultiComponentStudio initialResult={result} />);
  const text = textOf(markup);
  assert.ok(markup.includes('data-testid="calphad-provenance"'));
  assert.match(text, /Provenance: pycalphad 0\.11\.2 equilibrium on COST 507 Comprehensive Light Alloys Database \(TDB SHA-256 0123456789ab…\)/);
  assert.match(text, /not validated against experiment/);
  assert.match(text, /Models: warm \(compiled models reused by this worker\)/);
  assert.match(text, /Measured: database 0\.5 ms, models 0\.1 ms, grid 415 ms, liquidus\/solidus refinement 490 ms, Scheil path 526 ms, total 1440 ms\./);
  // a client screening result has no provenance strip
  assert.ok(!renderToStaticMarkup(<CALPHADMultiComponentStudio initialResult={clientBase()} />).includes("calphad-provenance"));
});

test("Studio calculating state shows measured elapsed time, no invented progress, and marks old results", () => {
  const markup = renderToStaticMarkup(<CALPHADMultiComponentStudio initialResult={pycalphadResult()} initialSolving />);
  const text = textOf(markup);
  assert.ok(markup.includes('data-testid="calphad-solving"'));
  assert.match(text, /Calculating with pycalphad… 0\.0 s elapsed/);
  assert.match(text, /No completion estimate exists/);
  assert.match(text, /belong to the previous input/);
  assert.doesNotMatch(text, /\d+ ?%\s*complete/i);
  assert.ok(markup.includes('aria-busy="true"'));
});

test("Studio lists database coverage with unavailable systems and known deviations", () => {
  const coverage = [
    { id: "in718", label: "Inconel 718 (UNS N07718)", baseElement: "Ni", elements: ["Ni", "Cr"], status: "unavailable" as const,
      reason: "no thermodynamic database for this system: ...", missingElements: ["Cr", "Fe"] },
    { id: "ti6al4v", label: "Ti-6Al-4V (UNS R56400)", baseElement: "Ti", elements: ["Ti", "Al", "V"], status: "covered" as const,
      databaseId: "cost507", databaseUsed: "COST 507 Comprehensive Light Alloys Database", knownDeviation: "beta transus about 925 vs 995 degC" },
  ];
  const text = textOf(renderToStaticMarkup(<CALPHADMultiComponentStudio initialResult={pycalphadResult()} initialCoverage={coverage} />));
  assert.match(text, /Database coverage: 1 of 2 reference alloy systems/);
  assert.match(text, /Inconel 718 \(UNS N07718\): unavailable, no thermodynamic database for this system \(missing: Cr, Fe\)/);
  assert.match(text, /Ti-6Al-4V \(UNS R56400\): covered by COST 507 Comprehensive Light Alloys Database \(not validated for this alloy here\)/);
  assert.match(text, /Known deviation: beta transus about 925 vs 995 degC/);
  assert.equal(formatCoverageRow({ ...coverage[0], missingElements: [] }), "Inconel 718 (UNS N07718): unavailable, no thermodynamic database for this system");
});

test("partition table: pycalphad k with phase and temperature, null k as Unavailable with the reason", () => {
  const result = pycalphadResult({
    solutePartitioning: [
      { element: "SI", partitionCoefficient_k: 0.1123, partitionCoefficientSource: "scheil-primary-phase-tie-line", temperatureC: 615.5,
        primarySolidPhase: "FCC_A1", role: "Rejected into the liquid (k < 1): enriches the last liquid / interdendritic regions" },
      { element: "MG", partitionCoefficient_k: null, partitionCoefficientSource: "unavailable", reason: "needs the Scheil-Gulliver path",
        temperatureC: null, primarySolidPhase: null, role: null },
    ],
  });
  const markup = renderToStaticMarkup(<CALPHADMultiComponentStudio initialResult={result} initialSubTab="solute_partitioning" />);
  const text = textOf(markup);
  assert.match(text, /k = 0\.112/);
  assert.match(text, /FCC_A1 at 615\.5 °C/);
  assert.match(text, /Unavailable/);
  assert.match(text, /needs the Scheil-Gulliver path/);
  assert.doesNotMatch(text, /Matrix \(γ\) wt%/);
  assert.doesNotMatch(text, /screening value, not CALPHAD/);
  assert.equal(formatPartitionK(null), "Unavailable");
});

test("the request temperature window follows the base element so the melting range is on the grid", () => {
  assert.deepEqual(calphadTemperatureWindow({ Al: 89.5, Si: 10, Mg: 0.5 }), { tMin: 400, tMax: 750, tStep: 10 });
  assert.deepEqual(calphadTemperatureWindow({ Ti: 90, Al: 6, V: 4 }), { tMin: 600, tMax: 1750, tStep: 25 });
  assert.deepEqual(calphadTemperatureWindow({ Mg: 92, Al: 8 }), { tMin: 350, tMax: 700, tStep: 10 });
  assert.deepEqual(calphadTemperatureWindow({ Ni: 53, Cr: 19, Fe: 18 }), { tMin: 500, tMax: 1550, tStep: 25 });
  // at most 80 grid points in each window (the engine's cap)
  for (const w of [calphadTemperatureWindow({ Al: 1 }), calphadTemperatureWindow({ Ti: 1 }), calphadTemperatureWindow({ Ni: 1 })]) {
    assert.ok((w.tMax - w.tMin) / w.tStep + 1 <= 80);
  }
});

// ---- fix round 1 (reviews REVIEW-calphad-opus / -sol) ----

test("Python ON never shows a client result left from a Python-OFF period (review S3)", () => {
  const text = textOf(renderToStaticMarkup(<CALPHADMultiComponentStudio initialResult={clientBase()} />));
  assert.doesNotMatch(text, /Liquidus \(T_liq\):/);
  assert.match(text, /No pycalphad result for this input yet/);
  const off = textOf(renderToStaticMarkup(<CALPHADMultiComponentStudio initialResult={clientBase()} initialUsePython={false} />));
  assert.match(off, /Liquidus \(T_liq\):/);
  assert.match(off, /MetalliX-Client-TS-Solver/);
});

test("the service sends the supersede key, and a superseded answer is an abort once the caller moved on", async () => {
  let sent: any = null;
  const controller = new AbortController();
  globalThis.fetch = (async (_url: string, init: any) => {
    sent = init;
    controller.abort(); // the caller moved on while the server was answering
    return new Response(JSON.stringify({ success: false, status: "superseded", reason: "x" }),
      { status: 200, headers: { "Content-Type": "application/json" } });
  }) as any;
  await assert.rejects(
    pythonComputationService.solveCalphadEquilibrium(ALLOY, 500, 1450, 50, true, undefined, undefined, false, true, 0.5,
      { signal: controller.signal, supersedeKey: "studio-abc" }),
    (err: unknown) => isAbortError(err));
  assert.equal(JSON.parse(sent.body).supersedeKey, "studio-abc");
  assert.equal(sent.signal.aborted, true); // the caller's abort reaches the fetch
});

test("a superseded answer for a caller that still waits is an unavailable result, never a silent abort (stuck studio)", async () => {
  globalThis.fetch = (async () =>
    new Response(JSON.stringify({ success: false, status: "superseded", reason: "x" }),
      { status: 200, headers: { "Content-Type": "application/json" } })) as any;
  const res = await pythonComputationService.solveCalphadEquilibrium(ALLOY, 500, 1450, 50, true, undefined, undefined,
    false, false, 0.5, { signal: new AbortController().signal, supersedeKey: "studio-abc" });
  assert.equal(res.pythonUnavailable?.unavailableKind, "engine-unreachable");
  assert.match(res.pythonUnavailable?.reason ?? "", /superseded/);
  assert.equal(res.equilibriumProfile.length, 0);
});

test("a request with no answer ends at the client deadline as unavailable (stuck studio)", async () => {
  let seen: AbortSignal | null = null;
  // A server that never answers: the fetch settles only when its signal aborts.
  globalThis.fetch = ((_url: string, init: any) => new Promise((_resolve, reject) => {
    seen = init.signal;
    init.signal.addEventListener("abort", () => {
      const err = new Error("aborted");
      err.name = "AbortError";
      reject(err);
    });
  })) as any;
  const t0 = Date.now();
  const res = await pythonComputationService.solveCalphadEquilibrium(ALLOY, 500, 1450, 50, true, undefined, undefined,
    false, false, 0.5, { signal: new AbortController().signal, timeoutMs: 50 });
  assert.ok(Date.now() - t0 < 5000);
  assert.equal(seen!.aborted, true);
  assert.equal(res.pythonUnavailable?.unavailableKind, "engine-unreachable");
  assert.match(res.pythonUnavailable?.reason ?? "", /no answer within/);
  assert.equal(res.equilibriumProfile.length, 0);
  assert.equal(res.isPythonEngine, false);
});

test("the caller's abort before the deadline is still an abort, and the client deadline outlasts the server budget", async () => {
  globalThis.fetch = ((_url: string, init: any) => new Promise((_resolve, reject) => {
    init.signal.addEventListener("abort", () => {
      const err = new Error("aborted");
      err.name = "AbortError";
      reject(err);
    });
  })) as any;
  const controller = new AbortController();
  const pending = pythonComputationService.solveCalphadEquilibrium(ALLOY, 500, 1450, 50, true, undefined, undefined,
    false, false, 0.5, { signal: controller.signal, timeoutMs: 60000 });
  controller.abort();
  await assert.rejects(pending, (err: unknown) => isAbortError(err));
  assert.ok(CALPHAD_CLIENT_TIMEOUT_MS > CALPHAD_SERVER_TIMEOUT_MS);
  // The server budget constant is the one the route really uses.
  const route = readFileSync(new URL("../routes/physics.ts", import.meta.url), "utf8");
  const budget = route.match(/calphad-minimize"[\s\S]*?handlePythonDispatch\("python\/calphad_solver\.py", req\.body, res, (\d+)\)/);
  assert.equal(Number(budget?.[1]), CALPHAD_SERVER_TIMEOUT_MS);
});

test("order/disorder model phase names carry 'ordering not checked' (review S4)", () => {
  const result = pycalphadResult({
    phaseNameNotes: { BCC_B2: "order/disorder model phase: ordering not checked" },
    solutePartitioning: [
      { element: "AL", partitionCoefficient_k: 1.0575, partitionCoefficientSource: "scheil-primary-phase-tie-line",
        temperatureC: 1684.5, primarySolidPhase: "BCC_B2", role: "Enriched in the primary solid (k > 1): depleted in the last liquid" },
    ],
    scheilSolidification: {
      status: "pycalphad-scheil-gulliver", terminationReason: "liquid-below-0.1-percent", startTemperatureC: 1686.5,
      terminalTemperatureC: 1654.5, terminalBracketC: null, remainingLiquidFraction: 0.0009, stepC: 2, steps: 16,
      phaseAmounts: { BCC_B2: 0.9991 }, primarySolidPhase: "BCC_B2",
      phaseNameNotes: { BCC_B2: "order/disorder model phase: ordering not checked" }, evidence: "unvalidated",
    },
  });
  const scheil = textOf(renderToStaticMarkup(<CALPHADMultiComponentStudio initialResult={result} initialSubTab="multi_scheil" />));
  assert.match(scheil, /Solid formed \(mole fraction\): BCC_B2 \(ordering not checked\) 99\.9 %/);
  assert.match(scheil, /Primary solid \(first to form\): BCC_B2 \(ordering not checked\)/);
  const part = textOf(renderToStaticMarkup(<CALPHADMultiComponentStudio initialResult={result} initialSubTab="solute_partitioning" />));
  assert.match(part, /BCC_B2 \(ordering not checked\) at 1684\.5 °C/);
  const grid = textOf(renderToStaticMarkup(<CALPHADMultiComponentStudio initialResult={result} />));
  assert.match(grid, /BCC_B2: order\/disorder model phase: ordering not checked\./);
  assert.equal(withOrderingNote("FCC_A1", { BCC_B2: "x" }), "FCC_A1");
});

test("the beta transus is shown with its heuristic status and the database deviation next to it (review S5)", () => {
  const result = pycalphadResult({
    criticalTemperatures: { liquidusC: 1686.4, solidusC: 1681.1, freezingRangeC: 5.3, betaTransusC: 925 },
    criticalTemperatureStatus: {
      betaTransusC: { status: "heuristic-phase-name", note: "highest grid temperature with HCP_A3 > 1 %",
        knownDeviation: "COST 507 places alpha (HCP_A3) up to about 925 degC, about 70 K below the 995 +/- 10 degC beta transus" },
      liquidusC: { status: "bisected", knownDeviation: "COST 507 liquidus/solidus lie above the values usually quoted" },
    },
  });
  const markup = renderToStaticMarkup(<CALPHADMultiComponentStudio initialResult={result} />);
  const text = textOf(markup);
  assert.match(text, /β-Transus \(phase-name heuristic, grid resolution\): 925°C COST 507 places alpha \(HCP_A3\) up to about 925 degC, about 70 K below/);
  assert.match(text, /COST 507 liquidus\/solidus lie above the values usually quoted/);
});

test("the probe stays on the solved grid and names the grid temperature it shows (Sol S5)", () => {
  assert.equal(clampProbeToRange(950, 400, 750, 10), 750);
  assert.equal(clampProbeToRange(613, 400, 750, 10), 610);
  assert.equal(clampProbeToRange(100, 600, 1750, 25), 600);
  assert.equal(clampProbeToRange(Number.NaN, 400, 750, 10), 400);
  const profile = [400, 500, 600, 700, 750].map((t) => ({
    temperatureC: t, status: "converged", phases: [], totalGibbsEnergy_kJ_mol: -40, thermodynamicActivities: {}, chemicalPotentials_J_mol: {},
  })) as any;
  const result = pycalphadResult({ temperatureRangeC: [400, 750], equilibriumProfile: profile });
  const text = textOf(renderToStaticMarkup(<CALPHADMultiComponentStudio initialResult={result} />));
  assert.match(text, /At 750°C \(nearest grid point\):/);
  assert.doesNotMatch(text, /At 950°C/);
});

test("an unavailable answer names no client engine and no compute time (review N1)", () => {
  const res = {
    alloyName: "IN718", nominalComposition: { Ni: 53 }, temperatureRangeC: [500, 1550] as [number, number], temperatureStepC: 25,
    equilibriumProfile: [], criticalTemperatures: { liquidusC: null, solidusC: null, freezingRangeC: null },
    solutePartitioning: [], multiElementScheil: [], thermodynamicStabilityIndex: null, tcpEmbrittlementRisk: null,
    engine: "none (pycalphad unavailable)", computeTimeMs: null, isPythonEngine: false,
    pythonUnavailable: { unavailableKind: "no-database-covers-elements", reason: "no usable thermodynamic database", reasons: ["x"] },
  } as PythonCalphadSolveResult;
  const text = textOf(renderToStaticMarkup(<CALPHADMultiComponentStudio initialResult={res} />));
  assert.match(text, /Active Engine: pycalphad \(unavailable for this input\)/);
  assert.match(text, /Compute Time: n\/a/);
  assert.doesNotMatch(text, /MetalliX-Client/);
  assert.match(text, /Unavailable: no thermodynamic database for this system/);
});

test("Scheil tab: an incomplete path says where it stopped and never claims an end of solidification", () => {
  const result = pycalphadResult({
    criticalTemperatures: { liquidusC: 1450, solidusC: 1250, freezingRangeC: 200 },
    multiElementScheil: [
      { fractionSolid: 0, temperatureC: 1450, liquidCompositions: { Fe: 65, Cr: 17 }, solidCompositions: null, solidPhases: [] },
      { fractionSolid: 0.9, temperatureC: 1246, liquidCompositions: { Fe: 60, Cr: 20 }, solidCompositions: { Fe: 66, Cr: 16 }, solidPhases: ["FCC_A1"] },
    ],
    scheilSolidification: {
      status: "incomplete",
      reason: "the path stopped early: an equilibrium on the path did not converge",
      terminationReason: "equilibrium-not-converged",
      startTemperatureC: 1450,
      terminalTemperatureC: 1246,
      terminalBracketC: null,
      remainingLiquidFraction: 0.12,
      phaseAmounts: { FCC_A1: 0.88 },
      fractionBasis: "mole fraction of atoms",
      evidence: "unvalidated",
    },
  });
  const text = textOf(renderToStaticMarkup(<CALPHADMultiComponentStudio initialResult={result} initialSubTab="multi_scheil" />));
  assert.match(text, /Scheil path incomplete: stopped at 1246 °C with 12\.0 % liquid \(equilibrium-not-converged\)/);
  assert.doesNotMatch(text, /End of solidification/);
  assert.match(text, /Solid formed so far \(mole fraction of atoms\): FCC_A1 88\.0 %/);
});

test("Scheil tab: the IN718 Laves do-not-use deviation is visible next to the Scheil phase amounts", () => {
  const result = pycalphadResult({
    scheilSolidification: {
      status: "pycalphad-scheil-gulliver", terminationReason: "liquid-exhausted-within-step", startTemperatureC: 1350,
      terminalTemperatureC: 1200, terminalBracketC: [1200, 1201], remainingLiquidFraction: 0,
      phaseAmounts: { FCC_A1: 0.95, LAVES: 0.0086 }, fractionBasis: "mole fraction of atoms", evidence: "unvalidated",
    },
    knownDeviations: [{ systemId: "in718", notes: ["Scheil terminal phases are not robust. Do not use the Scheil LAVES amount; nothing was tuned."] }],
  });
  const markup = renderToStaticMarkup(<CALPHADMultiComponentStudio initialResult={result} initialSubTab="multi_scheil" />);
  const text = textOf(markup);
  assert.match(markup, /data-testid="scheil-known-deviations"/);
  assert.ok(text.indexOf("LAVES 0.9 %") >= 0 && text.indexOf("Do not use the Scheil LAVES amount") > text.indexOf("LAVES 0.9 %"), text);
});

test("Studio: IN718 CALPHAD result shows the labelled literature card with the not-comparable note; 316L and Python-off show none", () => {
  const lit = { status: "available", alloyId: "in718", evidenceLabel: "Literature estimate (screening)", source: "weld studies", band: [], kValues: [] };
  const withLit = renderToStaticMarkup(<CALPHADMultiComponentStudio initialResult={pycalphadResult({ literatureSolidification: lit })} />);
  const t = textOf(withLit);
  assert.match(withLit, /data-testid="calphad-literature-solidification"/);
  assert.match(withLit, /data-lit-alongside-calphad="true"/);
  assert.ok(t.includes("Literature solidification estimate (not CALPHAD)") && t.includes("Not comparable directly"), t);
  assert.doesNotMatch(renderToStaticMarkup(<CALPHADMultiComponentStudio initialResult={pycalphadResult()} />), /calphad-literature-solidification/);
  assert.doesNotMatch(
    renderToStaticMarkup(<CALPHADMultiComponentStudio initialResult={pycalphadResult({ literatureSolidification: lit })} initialUsePython={false} />),
    /calphad-literature-solidification/);
});

// ---- calphad-studio-python-result: request identity, on-demand Scheil, pycalphad-only Gibbs tab ----

const WINDOW = { tMin: 500, tMax: 1550, tStep: 25 };

test("calphadRequestKey ignores key order and object identity, and changes with any request field", () => {
  const base = calphadRequestKey({ Ni: 53, Cr: 19, Fe: 18 }, "wt_pct", WINDOW, true, "auto", false, 0.5, false);
  assert.equal(base, calphadRequestKey({ Fe: 18, Ni: 53, Cr: 19 }, "wt_pct", { ...WINDOW }, true, "auto", false, 0.5, false));
  assert.notEqual(base, calphadRequestKey({ Ni: 53.1, Cr: 19, Fe: 18 }, "wt_pct", WINDOW, true, "auto", false, 0.5, false));
  assert.notEqual(base, calphadRequestKey({ Ni: 53, Cr: 19, Fe: 18 }, "wt_pct", WINDOW, true, "cost507", false, 0.5, false));
  assert.notEqual(base, calphadRequestKey({ Ni: 53, Cr: 19, Fe: 18 }, "wt_pct", WINDOW, true, "auto", true, 0.5, false));
  assert.notEqual(base, calphadRequestKey({ Ni: 53, Cr: 19, Fe: 18 }, "wt_pct", WINDOW, true, "auto", false, 0.5, true));
});

test("the service body carries scheil false by default, true when asked, and still the supersede key", async () => {
  const bodies: any[] = [];
  globalThis.fetch = (async (_url: string, init: any) => {
    bodies.push(JSON.parse(init.body));
    return new Response(JSON.stringify(UNAVAILABLE), { status: 200, headers: { "Content-Type": "application/json" } });
  }) as any;
  await pythonComputationService.solveCalphadEquilibrium(ALLOY, 600, 1750, 25, true, undefined, undefined, false, false, 0.5,
    { supersedeKey: "studio-1" });
  await pythonComputationService.solveCalphadEquilibrium(ALLOY, 600, 1750, 25, true, undefined, undefined, false, true, 0.5,
    { supersedeKey: "studio-1", scheil: true });
  assert.equal(bodies[0].scheil, false);
  assert.equal(bodies[0].boundaryRefinement, false);
  assert.equal(bodies[1].scheil, true);
  assert.equal(bodies[1].boundaryRefinement, true);
  assert.equal(bodies[0].supersedeKey, "studio-1");
  assert.equal(bodies[1].supersedeKey, "studio-1");
});

function resultWithPotentials(): PythonCalphadSolveResult {
  const base = pycalphadResult();
  return {
    ...base,
    activeComponents: ["TI", "AL", "V"],
    activityReferenceStates: {
      TI: { phase: "HCP_A3", temperature: "same T", pressurePa: 101325, status: "available", reason: null, definition: "Pure-element SER phase at the same temperature and pressure." },
      AL: { phase: "FCC_A1", temperature: "same T", pressurePa: 101325, status: "available", reason: null, definition: "Pure-element SER phase at the same temperature and pressure." },
      V: { phase: null, temperature: "same T", pressurePa: 101325, status: "unavailable", reason: "no reference phase", definition: "Pure-element SER phase at the same temperature and pressure." },
    },
    equilibriumProfile: base.equilibriumProfile.map((pt) => ({
      ...pt,
      totalGibbsEnergy_kJ_mol: -50,
      thermodynamicActivities: { TI: 0.5, AL: 0.1, V: null },
      chemicalPotentials_J_mol: { TI: -60000, AL: -70000 },
    })) as any,
  };
}

test("Gibbs tab with Python ON and no result shows no numbers", () => {
  const text = textOf(renderToStaticMarkup(<CALPHADMultiComponentStudio initialSubTab="gibbs_energy" />));
  assert.doesNotMatch(text, /G_min/);
  assert.doesNotMatch(text, /kJ\/mol/);
  assert.match(text, /No equilibrium result/);
});

test("Gibbs tab with a client result and Python OFF shows no mu or a cards and no 0.00 kJ/mol", () => {
  const text = textOf(renderToStaticMarkup(
    <CALPHADMultiComponentStudio initialResult={clientBase()} initialSubTab="gibbs_energy" initialUsePython={false} />));
  assert.doesNotMatch(text, /0\.00 kJ\/mol/);
  assert.doesNotMatch(text, /μ_[A-Z]+ =/);
  assert.doesNotMatch(text, /a_[A-Z]+ =/);
  assert.match(text, /come only from pycalphad/);
  assert.doesNotMatch(text, /The Python CALPHAD engine did not return a result/);
});

test("Gibbs tab with a pycalphad result shows Unavailable for a missing mu, the reference phase and the definition", () => {
  const text = textOf(renderToStaticMarkup(
    <CALPHADMultiComponentStudio initialResult={resultWithPotentials()} initialSubTab="gibbs_energy" />));
  assert.match(text, /μ_V = Unavailable/);
  assert.match(text, /μ_TI = -60\.00 kJ\/mol/);
  assert.match(text, /Ref: pure TI, HCP_A3, same T/);
  assert.match(text, /Pure-element SER phase at the same temperature and pressure\./);
  assert.match(text, /database SER scale/);
});

test("activity card shows the SER basis and the literature source when the engine reports them", () => {
  const base = resultWithPotentials();
  const withBasis = {
    ...base,
    activityReferenceStates: {
      ...base.activityReferenceStates,
      TI: { ...base.activityReferenceStates!.TI, basis: "SER unary function GHSERTI", referenceFunction: "GHSERTI",
        referenceSource: "SYNTHETIC source string, carried by this database FUNCTION" },
    },
  } as PythonCalphadSolveResult;
  const text = textOf(renderToStaticMarkup(
    <CALPHADMultiComponentStudio initialResult={withBasis} initialSubTab="gibbs_energy" />));
  assert.match(text, /Basis: SER unary function GHSERTI/);
  assert.match(text, /Reference: SYNTHETIC source string, carried by this database FUNCTION/);
});

test("activity card shows no basis or source line when the engine reports none", () => {
  const text = textOf(renderToStaticMarkup(
    <CALPHADMultiComponentStudio initialResult={resultWithPotentials()} initialSubTab="gibbs_energy" />));
  assert.match(text, /Ref: pure TI, HCP_A3, same T/);
  assert.doesNotMatch(text, /Basis:/);
  assert.doesNotMatch(text, /Reference: Dinsdale/);
});

test("Gibbs tab metric buttons and sub-tab buttons expose their selection with aria-pressed", () => {
  const markup = renderToStaticMarkup(
    <CALPHADMultiComponentStudio initialResult={resultWithPotentials()} initialSubTab="gibbs_energy" />);
  const pressed = (label: RegExp) => {
    const m = [...markup.matchAll(/<button\b([^>]*)>([\s\S]*?)<\/button>/g)].find((b) => label.test(textOf(b[2]).trim()));
    assert.ok(m, `button ${label} is rendered`);
    return /aria-pressed="(true|false)"/.exec(m[1])?.[1];
  };
  // default metric is G_m: exactly one metric button is pressed
  assert.equal(pressed(/^G_m \(kJ\/mol\)$/), "true");
  assert.equal(pressed(/^Activities a_i$/), "false");
  assert.equal(pressed(/^Chemical Potentials μ_i$/), "false");
  // the same pattern for the view switcher
  assert.equal(pressed(/Gibbs Energy & Activities/), "true");
  assert.equal(pressed(/Phase Fraction vs T/), "false");
});

test("Scheil tab offers the compute button when the path was not requested, and draws no chart", () => {
  const result = pycalphadResult({
    scheilSolidification: { status: "unavailable", reason: "not requested" },
  } as Partial<PythonCalphadSolveResult>);
  const markup = renderToStaticMarkup(<CALPHADMultiComponentStudio initialResult={result} initialSubTab="multi_scheil" />);
  const text = textOf(markup);
  assert.match(text, /Compute Scheil path \(about 1\.5 to 2 min\)/);
  assert.match(text, /Scheil-Gulliver path unavailable: not requested/);
  assert.doesNotMatch(markup, /recharts-wrapper/);
});

test("a studio composition that differs from the shared specimen shows the mismatch banner with both names", () => {
  const markup = renderToStaticMarkup(<CALPHADMultiComponentStudio initialAlloy={ALLOY} />);
  assert.match(markup, /role="status"[^>]*data-testid="calphad-composition-mismatch"|data-testid="calphad-composition-mismatch"[^>]*role="status"/);
  const text = textOf(markup);
  assert.ok(text.includes("This studio is calculating Ti-6Al-4V, not the shared material Inconel 718 (AMS 5662 / UNS N07718). Re-Sync to calculate the shared material."));
  // the default (shared) composition shows no banner
  assert.doesNotMatch(renderToStaticMarkup(<CALPHADMultiComponentStudio />), /calphad-composition-mismatch/);
});

// ---- mc_ti scope flag and the Ti-6Al-4V preset ----

const MC_TI_FLAG = "Valid for beta transus, liquidus/solidus and single-phase beta. Not for alpha/beta fractions below about 900 C. No Fe or O in this database.";

test("a scoped database result shows its scope flag; other results do not", () => {
  const flagged = textOf(renderToStaticMarkup(
    <CALPHADMultiComponentStudio initialResult={pycalphadResult({ databaseId: "mc_ti", databaseScopeFlag: MC_TI_FLAG })} />));
  assert.ok(flagged.includes(MC_TI_FLAG));
  assert.equal(calphadProvenanceLabels({ isPythonEngine: true, isEmpirical: false, databaseUsed: "mc_ti", databaseScopeFlag: MC_TI_FLAG }).scopeFlag, MC_TI_FLAG);
  const plain = renderToStaticMarkup(<CALPHADMultiComponentStudio initialResult={pycalphadResult()} />);
  assert.ok(!plain.includes("calphad-database-scope-flag"));
});

test("mc_ti phase-fraction view flags alpha/beta fractions below 900 C as not valid; other databases show no note", () => {
  const NOTE = "Not valid below about 900 C with mc_ti (see scope)";
  const scoped = textOf(renderToStaticMarkup(
    <CALPHADMultiComponentStudio initialResult={pycalphadResult({ databaseId: "mc_ti", databaseScopeFlag: MC_TI_FLAG })} initialSubTab="phase_fractions" />));
  assert.ok(scoped.includes(NOTE));
  assert.equal(isMcTiResult({ databaseId: "mc_ti" }), true);
  assert.equal(isMcTiResult({ databaseId: "cost507", databaseUsed: "COST 507" }), false);
  // probe (950 C) is above the limit: its fractions are still listed
  assert.ok(!scoped.includes("fraction-probe-clipped"));
  const base = pycalphadResult({ databaseId: "mc_ti", databaseScopeFlag: MC_TI_FLAG });
  const low = { ...base, equilibriumProfile: base.equilibriumProfile.filter((p) => p.temperatureC < 900) } as PythonCalphadSolveResult;
  const lowMarkup = renderToStaticMarkup(<CALPHADMultiComponentStudio initialResult={low} initialSubTab="phase_fractions" />);
  assert.match(lowMarkup, /data-testid="phase-fraction-probe-clipped"/);
  const other = renderToStaticMarkup(<CALPHADMultiComponentStudio initialResult={pycalphadResult()} initialSubTab="phase_fractions" />);
  assert.ok(!other.includes("phase-fraction-scope-note"));
  assert.ok(!textOf(other).includes(NOTE));
});

test("equilibrium CSV blanks mc_ti phase fractions below 900 C and leads with a scope comment; other databases unchanged", () => {
  const profile = [
    { temperatureC: 800, phases: [{ phaseId: "HCP_A3", phaseName: "HCP_A3 (alpha)", fraction: 0.6, majorElements: ["TI", "AL"] }] },
    { temperatureC: 950, phases: [{ phaseId: "BCC_A2", phaseName: "BCC_A2 (beta)", fraction: 0.5, majorElements: ["TI"] }] },
  ];
  const mc = buildEquilibriumCSV({ databaseId: "mc_ti", equilibriumProfile: profile });
  const lines = mc.trimEnd().split("\n");
  assert.equal(lines[0], "# mc_ti scope: phase fractions below about 900 C are not valid and are left blank");
  assert.equal(lines[1], "Temperature (C),Phase ID,Phase Name,Phase Fraction (%),Major Elements");
  assert.equal(lines[2], '800,"HCP_A3","HCP_A3 (alpha)",,"TI-AL"');
  assert.equal(lines[3], '950,"BCC_A2","BCC_A2 (beta)",50.0,"TI"');
  const other = buildEquilibriumCSV({ databaseId: "cost507", databaseUsed: "COST 507", equilibriumProfile: profile });
  assert.equal(other.split("\n")[0], "Temperature (C),Phase ID,Phase Name,Phase Fraction (%),Major Elements");
  assert.equal(other.split("\n")[1], '800,"HCP_A3","HCP_A3 (alpha)",60.0,"TI-AL"');
  assert.ok(!other.includes("# mc_ti"));
});

test("the Ti-6Al-4V preset is Ti-Al-V only and names mc_ti, not COST 507", () => {
  const ti64 = STANDARD_MULTI_COMPONENT_ALLOYS.find((a) => a.name.startsWith("Ti-6Al-4V"));
  assert.ok(ti64);
  assert.equal(ti64!.preferredDatabaseId, "mc_ti");
  assert.deepEqual(Object.keys(ti64!.elements).sort(), ["Al", "Ti", "V"]);
  assert.equal(STANDARD_MULTI_COMPONENT_ALLOYS.filter((a) => a.preferredDatabaseId).length, 1);
});
