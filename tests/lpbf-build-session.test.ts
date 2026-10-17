import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { after, beforeEach, test } from "node:test";
import { pythonComputationService, type PythonLpbfBuildJobResult } from "../src/services/pythonComputationService";
import { BUILD_JOB_SOLVER_REVISION, peekLpbfBuildJobKey, requestLpbfBuildJob, setLpbfKineticsInput, setLpbfMurakamiInput, useLpbfBuildJobStore } from "../src/store/useLpbfBuildJobStore";
import { useMaterialSpecimenStore } from "../src/store/useMaterialSpecimenStore";
import { useLpbfBuildMeshStore } from "../src/store/useLpbfBuildMeshStore";
import { mapSpecimenToBuildJobMaterials } from "../src/utils/lpbfIndustrialDecision";
import { canonicalBuildJobIdentity, canonicalBuildJobMaterialSnapshot } from "../src/utils/lpbfBuildJobIdentity";

// Deliberately incomplete service fixtures exercise session routing, never physical truth.
const initialSpecimen = useMaterialSpecimenStore.getState().activeSpecimen;
const initialBuild = useLpbfBuildJobStore.getState();
const originalSolve = pythonComputationService.solveLpbfBuildJob;
let calls = 0;
const sha = (value: string) => createHash("sha256").update(value).digest("hex");
const fixture = (extra: Partial<PythonLpbfBuildJobResult> = {}) => {
  const result = {
    success: true,
    modelId: "synthetic-session-fixture",
    solverRevision: BUILD_JOB_SOLVER_REVISION,
    alloyId: "in718",
    materialPropertySchemaVersion: 1,
    materialPropertyRevision: "build-job-effective-properties-v1",
    uq: null,
    ambench: null,
    ...extra,
  };
  const alloyId = result.alloyId ?? "in718";
  const modelId = result.modelId ?? "synthetic-session-fixture";
  const solverRevision = result.solverRevision ?? BUILD_JOB_SOLVER_REVISION;
  const propertySchemaVersion = result.materialPropertySchemaVersion ?? 1;
  const propertyRevision = result.materialPropertyRevision ?? "build-job-effective-properties-v1";
  const snapshot = {
    schemaVersion: propertySchemaVersion,
    alloyId,
    thermal: { base: "Ni", liquidus_C: 1336.0, thermal_expansion_1_K: 13e-6 },
    slicer: { density_gcm3: 8.19 },
  };
  const propertySha256 = result.materialPropertySha256 ?? sha(canonicalBuildJobMaterialSnapshot(snapshot));
  const defaultIdentityPayload = {
    schemaVersion: 1,
    alloyId,
    modelId,
    solverRevision,
    materialPropertySchemaVersion: propertySchemaVersion,
    materialPropertyRevision: propertyRevision,
    materialPropertySha256: propertySha256,
  };
  const defaultIdentity = { ...defaultIdentityPayload, sha256: sha(canonicalBuildJobIdentity({ ...defaultIdentityPayload, sha256: "" })) };
  return {
    ...result,
    materialPropertySha256: propertySha256,
    materialPropertySnapshot: snapshot,
    buildJobIdentity: Object.prototype.hasOwnProperty.call(extra, "buildJobIdentity")
      ? extra.buildJobIdentity
      : defaultIdentity,
  } as unknown as PythonLpbfBuildJobResult;
};

test("build-job snapshot canonical JSON preserves Python float bytes", () => {
  assert.equal(canonicalBuildJobMaterialSnapshot({ schemaVersion: 1, alloyId: "in718",
    thermal: { base: "Ni", liquidus_C: 1336.0, thermal_expansion_1_K: 13e-6 },
    slicer: { density_gcm3: 8.19 } }),
  '{"alloyId":"in718","schemaVersion":1,"slicer":{"density_gcm3":8.19},"thermal":{"base":"Ni","liquidus_C":1336.0,"thermal_expansion_1_K":1.3e-05}}');
});

beforeEach(() => {
  useMaterialSpecimenStore.setState({ activeSpecimen: initialSpecimen });
  useMaterialSpecimenStore.getState().loadPreset("inconel-718");
  useLpbfBuildMeshStore.setState({ mesh: null });
  useLpbfBuildJobStore.setState(initialBuild);
  calls = 0;
  pythonComputationService.solveLpbfBuildJob = async () => { calls++; return fixture(); };
});
after(() => { pythonComputationService.solveLpbfBuildJob = originalSolve; });

test("resetting the shared specimen selects an admitted LPBF alloy", () => {
  const before = useMaterialSpecimenStore.getState().activeSpecimen;
  try {
    useMaterialSpecimenStore.getState().resetToDefault();
    const specimen = useMaterialSpecimenStore.getState().activeSpecimen;
    assert.equal(specimen.name, "Inconel 718 (AMS 5662 / UNS N07718)");
    assert.equal(mapSpecimenToBuildJobMaterials(specimen.name, specimen.baseMetal)?.alloyId, "in718");
  } finally {
    useMaterialSpecimenStore.setState({ activeSpecimen: before });
  }
});

test("identical fast requests reuse the result; changed CT threshold recomputes", async () => {
  setLpbfMurakamiInput({ ctDetectionThreshold_um: 10 });
  await requestLpbfBuildJob();
  await requestLpbfBuildJob();
  assert.equal(calls, 1);
  setLpbfMurakamiInput({ ctDetectionThreshold_um: 25 });
  await requestLpbfBuildJob();
  assert.equal(calls, 2);
});

test("scenario fields are sent only when the user set them and a change recomputes", async () => {
  const sent: Record<string, unknown>[] = [];
  pythonComputationService.solveLpbfBuildJob = async (payload) => { calls++; sent.push(payload as Record<string, unknown>); return fixture(); };
  const scenarioKeys = ["defectSqrtArea_um", "defectEvidence", "defectLocation", "hardnessEvidence", "specimenOrientation",
    "loadRatio", "cycleTarget", "ctDetectionMethod", "defectSampling", "hardness_HV"];
  await requestLpbfBuildJob();
  for (const key of scenarioKeys) assert.equal(key in sent[0], false, key);
  setLpbfMurakamiInput({ defectSqrtArea_um: 250, defectEvidence: "assumed-scenario", defectLocation: "internal",
    hardnessEvidence: "assumed-scenario", hardness_HV: 330, blockVolume_mm3: 10, targetVolume_mm3: 1000, targetProbability: 0.9 });
  await requestLpbfBuildJob();
  assert.equal(calls, 2);
  assert.equal(sent[1].defectSqrtArea_um, 250);
  assert.equal(sent[1].defectEvidence, "assumed-scenario");
  assert.equal(sent[1].defectLocation, "internal");
  assert.equal(sent[1].hardnessEvidence, "assumed-scenario");
  for (const key of ["specimenOrientation", "loadRatio", "cycleTarget", "ctDetectionMethod", "defectSampling"]) {
    assert.equal(key in sent[1], false, key);
  }
  setLpbfMurakamiInput({ blockMaximaComparable: true });
  await requestLpbfBuildJob();
  assert.deepEqual(sent[2].defectSampling, { design: "comparable-independent-block-maxima", blockVolume_mm3: 10,
    targetVolume_mm3: 1000, targetProbability: 0.9 });
});

test("same-input results from a prior solver revision are recomputed", async () => {
  await requestLpbfBuildJob();
  const currentKey = peekLpbfBuildJobKey();
  const keyParts = JSON.parse(currentKey) as unknown[];
  assert.equal(keyParts[0], BUILD_JOB_SOLVER_REVISION);

  // The prior client key was the remaining input/flag tuple without a revision.
  useLpbfBuildJobStore.setState({ lastKey: JSON.stringify(keyParts.slice(1)) });
  await requestLpbfBuildJob();
  assert.equal(calls, 2);
  assert.equal(useLpbfBuildJobStore.getState().lastKey, currentKey);
});

test("a backend result from a different solver revision is rejected", async () => {
  pythonComputationService.solveLpbfBuildJob = async () => fixture({ solverRevision: "old-solver-revision" });
  await requestLpbfBuildJob();
  assert.match(useLpbfBuildJobStore.getState().error ?? "", /solver revision mismatch/);
  assert.equal(useLpbfBuildJobStore.getState().job, null);
});

test("successful results require a consistent material and model identity", async () => {
  pythonComputationService.solveLpbfBuildJob = async () => fixture({
    buildJobIdentity: undefined,
  });
  await requestLpbfBuildJob();
  assert.match(useLpbfBuildJobStore.getState().error ?? "", /material\/model identity/);
  assert.equal(useLpbfBuildJobStore.getState().job, null);

  pythonComputationService.solveLpbfBuildJob = async () => fixture({
    buildJobIdentity: {
      schemaVersion: 1,
      alloyId: "in718",
      modelId: "wrong-model",
      solverRevision: BUILD_JOB_SOLVER_REVISION,
      materialPropertySchemaVersion: 1,
      materialPropertyRevision: "build-job-effective-properties-v1",
      materialPropertySha256: "a".repeat(64),
      sha256: "b".repeat(64),
    },
  });
  await requestLpbfBuildJob();
  assert.match(useLpbfBuildJobStore.getState().error ?? "", /material\/model identity/);
  assert.equal(useLpbfBuildJobStore.getState().job, null);
});

test("successful backend results require the top-level material revision", async () => {
  pythonComputationService.solveLpbfBuildJob = async () => fixture({ materialPropertyRevision: undefined });
  await requestLpbfBuildJob();
  assert.match(useLpbfBuildJobStore.getState().error ?? "", /material\/model identity/);
  assert.equal(useLpbfBuildJobStore.getState().job, null);
});

test("successful backend results reject changed material snapshots and identity hashes", async () => {
  const changedSnapshot = fixture();
  changedSnapshot.materialPropertySnapshot!.thermal.liquidus_C = 1400.0;
  pythonComputationService.solveLpbfBuildJob = async () => changedSnapshot;
  await requestLpbfBuildJob();
  assert.match(useLpbfBuildJobStore.getState().error ?? "", /identity hash mismatch/);
  assert.equal(useLpbfBuildJobStore.getState().job, null);

  const changedIdentity = fixture();
  changedIdentity.buildJobIdentity!.sha256 = "f".repeat(64);
  pythonComputationService.solveLpbfBuildJob = async () => changedIdentity;
  await requestLpbfBuildJob();
  assert.match(useLpbfBuildJobStore.getState().error ?? "", /identity hash mismatch/);
  assert.equal(useLpbfBuildJobStore.getState().job, null);
});

test("backend failures without a solver revision preserve their error", async () => {
  const backendError = "Unsupported LPBF alloy identity: synthetic unknown alloy";
  pythonComputationService.solveLpbfBuildJob = async () => ({
    success: false,
    error: backendError,
  } as unknown as PythonLpbfBuildJobResult);
  await requestLpbfBuildJob();
  assert.equal(useLpbfBuildJobStore.getState().error, backendError);
  assert.equal(useLpbfBuildJobStore.getState().job, null);
});

test("defect records differing beyond their first 80 characters cannot collide", async () => {
  const prefix = "40 ".repeat(40);
  setLpbfMurakamiInput({ defectSqrtAreasPaste: `${prefix}50` });
  await requestLpbfBuildJob();
  const firstKey = peekLpbfBuildJobKey();
  setLpbfMurakamiInput({ defectSqrtAreasPaste: `${prefix}500` });
  assert.notEqual(peekLpbfBuildJobKey(), firstKey);
  await requestLpbfBuildJob();
  assert.equal(calls, 2);
});

test("different geometry with identical filename and triangle counts recomputes", async () => {
  const mesh = (size: number) => ({ name: "specimen.stl", nativeTriangleCount: 1, usedTriangleCount: 1, triangles: [[[0, 0, 0], [size, 0, 0], [0, size, 0]]] });
  useLpbfBuildMeshStore.setState({ mesh: mesh(1) });
  await requestLpbfBuildJob();
  useLpbfBuildMeshStore.setState({ mesh: mesh(10) });
  await requestLpbfBuildJob();
  assert.equal(calls, 2);
});

test("UQ sample count remains aligned and evidence is retained only for the same process", async () => {
  const uq = { enabled: true, nSamples: 24, source: "Synthetic session fixture" } as unknown as NonNullable<PythonLpbfBuildJobResult["uq"]>;
  const ambench = { source: { doi: "Synthetic session fixture; not experimental" } } as unknown as NonNullable<PythonLpbfBuildJobResult["ambench"]>;
  pythonComputationService.solveLpbfBuildJob = async payload => fixture({ uq: payload.enableUq ? uq : null, ambench: payload.includeAmbench ? ambench : null });
  await requestLpbfBuildJob({ enableUq: true, includeAmbench: true, uqSamples: 24 });
  assert.equal(useLpbfBuildJobStore.getState().lastKey, peekLpbfBuildJobKey());
  await requestLpbfBuildJob();
  assert.equal(useLpbfBuildJobStore.getState().job?.uq, uq);
  assert.equal(useLpbfBuildJobStore.getState().job?.ambench, ambench);
  const currentSpecimen = useMaterialSpecimenStore.getState().activeSpecimen;
  useMaterialSpecimenStore.setState({ activeSpecimen: { ...currentSpecimen, lpbf: { ...currentSpecimen.lpbf, laserPower_W: currentSpecimen.lpbf.laserPower_W + 25 } } });
  await requestLpbfBuildJob();
  assert.equal(useLpbfBuildJobStore.getState().job?.uq, null);
  assert.equal(useLpbfBuildJobStore.getState().job?.ambench, null);
  assert.equal(useLpbfBuildJobStore.getState().sessionUq, null);
  assert.equal(useLpbfBuildJobStore.getState().sessionAmbench, null);
});

test("a slower superseded job cannot overwrite a newer process result", async () => {
  let release: (result: PythonLpbfBuildJobResult) => void = () => {};
  const older = new Promise<PythonLpbfBuildJobResult>(resolve => { release = resolve; });
  const latest = fixture();
  pythonComputationService.solveLpbfBuildJob = async () => ++calls === 1 ? older : latest;
  const pending = requestLpbfBuildJob();
  setLpbfMurakamiInput({ ctDetectionThreshold_um: 99 });
  await requestLpbfBuildJob();
  const currentKey = useLpbfBuildJobStore.getState().lastKey;
  release(fixture({ engine: "older-synthetic-fixture" } as Partial<PythonLpbfBuildJobResult>));
  await pending;
  assert.equal(useLpbfBuildJobStore.getState().lastKey, currentKey);
  assert.notEqual(useLpbfBuildJobStore.getState().job?.engine, "older-synthetic-fixture");
});

test("unsupported alloy identity refuses computation and clears a previous supported result", async () => {
  await requestLpbfBuildJob();
  assert.equal(calls, 1);
  assert.ok(useLpbfBuildJobStore.getState().job);
  const supported = useMaterialSpecimenStore.getState().activeSpecimen;
  useLpbfBuildJobStore.setState({
    sessionUq: { enabled: true, nSamples: 8, source: "synthetic stale fixture" } as unknown as NonNullable<typeof initialBuild.sessionUq>, // intentionally partial stale fixture
    sessionAmbench: {} as NonNullable<typeof initialBuild.sessionAmbench>,
    sessionEvidenceKey: "stale-evidence",
  });
  for (const [name, baseMetal] of [
    ["Unknown nickel alloy", "Ni"],
    ["CoCrMo", "Co"],
    ["Unknown iron alloy", "Fe"],
    ["316L", "Co"],
    ["IN718", "Fe"],
  ] as const) {
    useMaterialSpecimenStore.setState({ activeSpecimen: { ...supported, id: `synthetic-${baseMetal}`, name, baseMetal } });
    await requestLpbfBuildJob();
    assert.equal(calls, 1, `${name} must not submit a surrogate alloy`);
    assert.equal(useLpbfBuildJobStore.getState().job, null);
    assert.equal(useLpbfBuildJobStore.getState().busy, false);
    assert.equal(useLpbfBuildJobStore.getState().sessionUq, null);
    assert.equal(useLpbfBuildJobStore.getState().sessionAmbench, null);
    assert.equal(useLpbfBuildJobStore.getState().sessionEvidenceKey, null);
    assert.match(useLpbfBuildJobStore.getState().error!, /no supported material mapping.*no surrogate alloy was submitted/);
  }
});

test("build-job material mapping accepts only its four canonical solver alloys", () => {
  assert.equal(mapSpecimenToBuildJobMaterials("Ti-6Al-4V Grade 23 ELI", "Ti")?.alloyId, "ti6al4v");
  assert.equal(mapSpecimenToBuildJobMaterials("Ti-6Al-4V Grade 5 Titanium", "Ti")?.alloyId, "ti6al4v");
  assert.equal(mapSpecimenToBuildJobMaterials("Ti64", "Ti")?.alloyId, "ti6al4v");
  assert.equal(mapSpecimenToBuildJobMaterials("AISI 316L Stainless Steel", "Fe")?.alloyId, "ss316l");
  assert.equal(mapSpecimenToBuildJobMaterials("AlSi10Mg Additive Lightweight", "Al")?.alloyId, "alsi10mg");
  assert.equal(mapSpecimenToBuildJobMaterials("Inconel 718 (AMS 5662)", "Ni")?.alloyId, "in718");
  assert.equal(mapSpecimenToBuildJobMaterials("IN718", "Ni")?.alloyId, "in718");
  assert.equal(mapSpecimenToBuildJobMaterials("316L", "Co"), null);
  assert.equal(mapSpecimenToBuildJobMaterials("IN718", "Fe"), null);
  assert.equal(mapSpecimenToBuildJobMaterials("Ti64", "Al"), null);
  assert.equal(mapSpecimenToBuildJobMaterials("AlSi10Mg", "Ni"), null);
  assert.equal(mapSpecimenToBuildJobMaterials("CoCrMo"), null);
  assert.equal(mapSpecimenToBuildJobMaterials("Unknown iron alloy"), null);
  assert.equal(mapSpecimenToBuildJobMaterials(""), null);
  assert.equal(mapSpecimenToBuildJobMaterials("Not Inconel 718"), null);
  assert.equal(mapSpecimenToBuildJobMaterials("Ti-6Al-4V alternative alloy"), null);
  assert.equal(mapSpecimenToBuildJobMaterials("AlSi10Mg + CoCrMo"), null);
  assert.equal(mapSpecimenToBuildJobMaterials("316L-coated CoCrMo"), null);
  assert.equal(mapSpecimenToBuildJobMaterials("constructor"), null);
});

test("returning to a supported alloy cannot reuse a request superseded by an unsupported identity", async () => {
  const supported = useMaterialSpecimenStore.getState().activeSpecimen;
  let release: (result: PythonLpbfBuildJobResult) => void = () => {};
  const oldResponse = new Promise<PythonLpbfBuildJobResult>(resolve => {release=resolve;});
  pythonComputationService.solveLpbfBuildJob = async () => ++calls === 1 ? oldResponse : fixture({engine:"latest-fixture"});
  const older = requestLpbfBuildJob();
  useMaterialSpecimenStore.setState({activeSpecimen:{...supported,name:"Unknown nickel alloy"}});
  await requestLpbfBuildJob();
  useMaterialSpecimenStore.setState({activeSpecimen:supported});
  const resumed = requestLpbfBuildJob();
  release(fixture({engine:"superseded-fixture"}));
  await Promise.all([older,resumed]);
  assert.equal(calls,2);
  assert.equal(useLpbfBuildJobStore.getState().job?.engine,"latest-fixture");
  assert.equal(useLpbfBuildJobStore.getState().busy,false);
});

test("kinetics interval and isothermal hold are absent by default and sent only when complete", async () => {
  const sent: Record<string, unknown>[] = [];
  pythonComputationService.solveLpbfBuildJob = async (payload) => { calls++; sent.push(payload as Record<string, unknown>); return fixture(); };
  await requestLpbfBuildJob();
  assert.equal("kineticsCoolingInterval_C" in sent[0], false);
  assert.equal("isothermalHold" in sent[0], false);
  setLpbfKineticsInput({ coolingHigh_C: 900 });
  setLpbfKineticsInput({ holdTemperature_C: 600, holdInterpolate: true });
  await requestLpbfBuildJob();
  assert.equal(calls, 1);
  setLpbfKineticsInput({ coolingLow_C: 300, holdTime_s: 3600 });
  await requestLpbfBuildJob();
  assert.equal(calls, 2);
  assert.deepEqual(sent[1].kineticsCoolingInterval_C, { high_C: 900, low_C: 300 });
  assert.deepEqual(sent[1].isothermalHold, { temperature_C: 600, time_s: 3600, interpolate: true });
  setLpbfKineticsInput({ holdInterpolate: false });
  await requestLpbfBuildJob();
  assert.equal(calls, 3);
  assert.equal((sent[2].isothermalHold as { interpolate: boolean }).interpolate, false);
});
