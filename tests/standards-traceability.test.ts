import assert from "node:assert/strict";
import { test } from "node:test";
import { readFileSync } from "node:fs";
import { useMaterialSpecimenStore } from "../src/store/useMaterialSpecimenStore";
import { LPBF_ENGINEERING_DEFAULTS, engineeringSignature, type LpbfEngineeringState } from "../src/store/useLpbfEngineeringStore";
import type { LpbfBuildContext } from "../src/store/useLpbfWorkflowStore";
import { createLpbfQualificationReport, sharedSimulationInput } from "../src/utils/lpbfQualificationReport";
import { summarizeErrorBands } from "../src/data/lpbfErrorBands";
import type { SimulationJob, SimulationResult } from "../src/services/lpbfSimulationService";
import type { PythonLpbfBuildJobResult } from "../src/services/pythonComputationService";

// Traceability aid only. Not a compliance claim, not qualification, not certification.
// Synthetic fixture: it only has to populate every optional key so the map can be checked. It is never physical evidence.
const HEADER = "Traceability aid only. Not a compliance claim, not qualification, not certification.";
const read = (rel: string) => readFileSync(new URL(`../${rel}`, import.meta.url), "utf8");
const map = JSON.parse(read("data/standards/traceability-map-v1.json")) as {
  header: string;
  documents: { id: string; access: string; sha256: string | null; sourceUrl: string }[];
  fields: { id: string; path: string; scope: string; coverage: string; mappings: { doc: string; coverage: string; ref: string; refVerified: boolean }[] }[];
  gaps: { id: string; doc: string; status: string; ref: string; refVerified: boolean }[];
};

const CREATED = "2026-01-02T03:04:05.000Z";
const spec = () => useMaterialSpecimenStore.getState().activeSpecimen;
const context: LpbfBuildContext = { buildId: "B-1", machine: "M1", powderLot: "L1", powderCondition: "c", heatTreatment: "h", measurementMethod: "m", notes: "n" };
function fixtureReport() {
  const specimen = spec();
  const input = sharedSimulationInput(specimen);
  const result = {
    schemaVersion: 1, requestedMode: "standard", effectiveMode: "screening", solver: { id: "fixture", version: "v", openfoam: null },
    settings: input, confidence: "low", validationStatus: "unvalidated", productionReady: false, label: "Unvalidated thermal simulation",
    fallbackReason: "fixture", metrics: { width_um: 1, depth_um: 2, length_um: 3 }, material: { name: input.material, quality: "estimated", source: "fixture" },
    analyticalComparison: {}, assumptions: ["a"], regime: "r", mainRisk: "m", recommendation: "x", riskScope: "s",
    provenance: { createdAt: CREATED, inputHash: "i", executionInputHash: "e", implementationHash: "h", implementationFingerprintSchema: "s", solverBinaryHash: null },
    energyBalance: { input_J: 1, losses_J: 0.5, stored_J: 0.5, relativeError: 0.01 },
    convergenceStudy: {},
    measurementEvidence: [{ source: "s", sameProcessVector: "yes", uncertainty_um: 1, independentHoldout: false }],
  } as unknown as SimulationResult;
  const job: SimulationJob = { id: "a".repeat(32), status: "completed", progress: 1, log: "", error: null, result };
  const engineering: LpbfEngineeringState = { settings: { ...LPBF_ENGINEERING_DEFAULTS }, mode: "standard", job, error: "", busy: false, material: "", properties: "", measurements: "r", specimen: "s", uncertainty: "1", holdout: "unknown", width: "1", depth: "2", source: "src", submittedSignature: "", resultSignature: "", submittedInput: result.settings };
  engineering.resultSignature = engineeringSignature(input, engineering, specimen.lpbf.scanStrategy);
  const buildJob = { success: true, modelId: "mdl", verdict: { verdict: "risky" }, assumptions: [], thermal: { material: "Ti-6Al-4V", processParameters: { heatSource: "goldak", normalizedEnthalpy: 10, laserPower_W: 200, scanSpeed_mm_s: 900, beamDiameter_um: 80 }, meltPoolGeometry: { width_um: 100, depth_um: 50, extentStatus: "computed" } } } as unknown as PythonLpbfBuildJobResult;
  return createLpbfQualificationReport(specimen, context, engineering, buildJob, [{ id: "ev" }], summarizeErrorBands(JSON.parse(read("data/calibration/lpbf-meltpool-error-bands-v1.summary.json"))));
}

// Resolve "a.b[].c" on a value. Arrays are entered through their first element. Key presence is what counts (null is fine).
function exists(root: unknown, path: string): boolean {
  let cur: unknown = root;
  for (const part of path.split(".")) {
    const isArr = part.endsWith("[]");
    const key = isArr ? part.slice(0, -2) : part;
    if (cur === null || typeof cur !== "object" || !(key in (cur as object))) return false;
    cur = (cur as Record<string, unknown>)[key];
    if (isArr) { if (!Array.isArray(cur) || cur.length === 0) return false; cur = cur[0]; }
  }
  return true;
}

test("map carries the disclaimer header", () => {
  assert.equal(map.header, HEADER);
  assert.ok(read("docs/STANDARDS_TRACEABILITY.md").includes(HEADER));
});

test("every dossier field path in the map exists in the dossier", () => {
  const report = fixtureReport();
  const dossierFields = map.fields.filter(f => f.scope === "dossier");
  assert.ok(dossierFields.length > 40);
  const missing = dossierFields.filter(f => !exists(report, f.path)).map(f => f.path);
  assert.deepEqual(missing, [], `paths not found in the dossier: ${missing.join(", ")}`);
});

test("extras and options paths still appear in the run report or calibration source", () => {
  const src = read("src/utils/lpbfRunReport.ts") + read("src/data/lpbfMachineCalibration.ts");
  const others = map.fields.filter(f => f.scope !== "dossier");
  assert.ok(others.length > 0);
  for (const f of others) {
    assert.ok(["run-report-extras", "run-report-options"].includes(f.scope), `unknown scope ${f.scope}`);
    const last = f.path.split(".").pop()!;
    assert.ok(new RegExp(`\\b${last}\\b`).test(src), `${f.path}: ${last} not found in run report or machine calibration source`);
  }
});

test("map is internally consistent and makes no compliance claim", () => {
  const ids = new Set(map.documents.map(d => d.id));
  const allowed = new Set(["recorded", "partially recorded", "not recorded"]);
  for (const f of map.fields) {
    assert.ok(allowed.has(f.coverage), f.id);
    for (const m of f.mappings) { assert.ok(ids.has(m.doc), `${f.id}: unknown document ${m.doc}`); assert.ok(allowed.has(m.coverage), f.id); }
  }
  for (const g of map.gaps) { assert.ok(ids.has(g.doc), g.id); assert.equal(g.status, "not recorded"); }
  // Paywalled documents never carry a verified clause reference or a hash of text that was not obtained.
  const paywalled = new Set(map.documents.filter(d => d.access === "paywalled").map(d => d.id));
  for (const d of map.documents.filter(d => d.access === "paywalled")) assert.equal(d.sha256, null, d.id);
  for (const f of map.fields) for (const m of f.mappings) if (paywalled.has(m.doc)) { assert.equal(m.refVerified, false); assert.match(m.ref, /unverified: check against a licensed copy/); }
  for (const g of map.gaps) if (paywalled.has(g.doc)) assert.equal(g.refVerified, false);
  const text = JSON.stringify(map) + read("docs/STANDARDS_TRACEABILITY.md");
  assert.ok(!/\b(complies|compliant with|certified to|meets the requirements)\b/i.test(text));
});
