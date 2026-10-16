/**
 * Session-only Python Build Job result. Not persisted.
 * Industrial UI (rail + Decision lab) must display job.verdict and must not re-score in TypeScript.
 *
 * Faz 5: default job is fast (enableUq=false, includeAmbench=false).
 * Session retains last UQ / NIST blocks when subsequent jobs skip them.
 */
import { useEffect } from "react";
import { create } from "zustand";
import {
  pythonComputationService,
  PythonLpbfAmbenchBlock,
  PythonLpbfBuildJobResult,
  PythonLpbfMurakamiBlock,
  PythonLpbfUqBlock,
} from "../services/pythonComputationService";
import { inferSlicerPreset, mapSpecimenToBuildJobMaterials } from "../utils/lpbfIndustrialDecision";
import { canonicalBuildJobIdentity, canonicalBuildJobMaterialSnapshot, sha256Utf8 } from "../utils/lpbfBuildJobIdentity";
import { useMaterialSpecimenStore } from "./useMaterialSpecimenStore";
import { useLpbfBuildMeshStore } from "./useLpbfBuildMeshStore";

// Keep aligned with python/lpbf_job_cache.py; changing this invalidates held
// same-input results when the client and build-job solver are upgraded.
export const BUILD_JOB_SOLVER_REVISION = "lpbf-build-job-solt-v27";

export interface LpbfMurakamiSessionInput {
  defectSqrtAreasPaste: string;
  hardness_HV: number | null;
  ctDetectionThreshold_um: number | null;
}

interface LpbfBuildJobPythonState {
  job: PythonLpbfBuildJobResult | null;
  error: string | null;
  busy: boolean;
  roundTripMs: number | null;
  lastKey: string | null;
  seq: number;
  /** Retained when a later fast job omits UQ. */
  sessionUq: PythonLpbfUqBlock | null;
  sessionAmbench: PythonLpbfAmbenchBlock | null;
  sessionEvidenceKey: string | null;
  lastUqSamples: number;
  murakamiInput: LpbfMurakamiSessionInput;
  lastFlags: { enableUq: boolean; includeAmbench: boolean };
}

export const useLpbfBuildJobStore = create<LpbfBuildJobPythonState>(() => ({
  job: null,
  error: null,
  busy: false,
  roundTripMs: null,
  lastKey: null,
  seq: 0,
  sessionUq: null,
  sessionAmbench: null,
  sessionEvidenceKey: null,
  lastUqSamples: 96,
  murakamiInput: {
    defectSqrtAreasPaste: "",
    hardness_HV: null,
    ctDetectionThreshold_um: null,
  },
  lastFlags: { enableUq: false, includeAmbench: false },
}));

const meshIdentities = new WeakMap<object, number>();
let nextMeshIdentity = 0;
function meshIdentity(mesh: object | null): number {
  if (!mesh) return 0;
  if (!meshIdentities.has(mesh)) meshIdentities.set(mesh, ++nextMeshIdentity);
  return meshIdentities.get(mesh)!;
}

let inFlightKey: string | null = null;
let inFlightPromise: Promise<void> | null = null;
let inFlightSeq = 0;

export type LpbfBuildJobRequestOptions = {
  force?: boolean;
  enableUq?: boolean;
  includeAmbench?: boolean;
  uqSamples?: number;
  bypassCache?: boolean;
};

function buildJobKey(flags: { enableUq: boolean; includeAmbench: boolean; uqSamples: number }): {
  key: string;
  evidenceKey: string;
  materialSupported: boolean;
  payload: Parameters<typeof pythonComputationService.solveLpbfBuildJob>[0];
} {
  const specimen = useMaterialSpecimenStore.getState().activeSpecimen;
  const liveMesh = useLpbfBuildMeshStore.getState().mesh;
  const murakamiInput = useLpbfBuildJobStore.getState().murakamiInput;
  const lpbf = specimen.lpbf;
  const materials = mapSpecimenToBuildJobMaterials(specimen.name, specimen.baseMetal);
  const payload: Parameters<typeof pythonComputationService.solveLpbfBuildJob>[0] = {
    // Unsupported identities remain visible in the key but are never submitted.
    alloyId: materials?.alloyId ?? specimen.name,
    thermalMaterial: materials?.pythonThermal ?? specimen.name,
    slicerMaterial: materials?.pythonSlicer ?? specimen.name,
    laserPower_W: lpbf.laserPower_W,
    scanSpeed_mm_s: lpbf.scanSpeed_mms,
    beamDiameter_um: lpbf.beamDiameter_um,
    preheatTemp_C: lpbf.preheatTemp_C,
    layerThickness_um: lpbf.layer_um,
    hatchSpacing_um: lpbf.hatch_um,
    laserWavelength: "IR_1064nm",
    preset: liveMesh ? "custom" : inferSlicerPreset(lpbf.cadAssetName),
    customTriangles: liveMesh?.triangles ?? null,
    cadAssetName: liveMesh?.name || lpbf.cadAssetName,
    triangleCountNative: liveMesh?.nativeTriangleCount,
    processSeed: lpbf.processSeed ?? 42,
    scanStrategy: lpbf.scanStrategy,
    stripeWidth_mm: 5,
    scanRotation_deg: 67,
    hatchDwell_ms: 0,
    inclineAngle_deg: lpbf.inclineAngle_deg ?? 0,
    enableUq: flags.enableUq,
    uqSamples: flags.uqSamples,
    includeAmbench: flags.includeAmbench,
    ...(lpbf.downskinOverhang_deg > 0
      ? { downskinOverhang_deg: lpbf.downskinOverhang_deg }
      : {}),
    ...(murakamiInput.defectSqrtAreasPaste.trim()
      ? { defectSqrtAreasPaste: murakamiInput.defectSqrtAreasPaste }
      : {}),
    ...(murakamiInput.hardness_HV != null ? { hardness_HV: murakamiInput.hardness_HV } : {}),
    ...(murakamiInput.ctDetectionThreshold_um != null
      ? { ctDetectionThreshold_um: murakamiInput.ctDetectionThreshold_um }
      : {}),
  };
  // Include the complete CT/defect input and mesh identity. Names/counts do not identify geometry.
  const { customTriangles: _triangles, enableUq: _uq, includeAmbench: _ambench, uqSamples: _samples, ...basePayload } = payload;
  const evidenceKey = JSON.stringify([basePayload, {id:specimen.id,name:specimen.name,composition:specimen.composition}, meshIdentity(liveMesh)]);
  const key = JSON.stringify([BUILD_JOB_SOLVER_REVISION, evidenceKey, flags.enableUq, flags.includeAmbench, flags.enableUq ? flags.uqSamples : 0]);
  return { key, evidenceKey, payload, materialSupported: materials !== null };
}

export function peekLpbfBuildJobKey(): string {
  const st = useLpbfBuildJobStore.getState();
  return buildJobKey({
    enableUq: st.lastFlags.enableUq,
    includeAmbench: st.lastFlags.includeAmbench,
    uqSamples: st.lastUqSamples,
  }).key;
}

export function setLpbfMurakamiInput( partial: Partial<LpbfMurakamiSessionInput>): void {
  const prev = useLpbfBuildJobStore.getState().murakamiInput;
  useLpbfBuildJobStore.setState({ murakamiInput: { ...prev, ...partial } });
}

export async function requestLpbfBuildJob(options?: LpbfBuildJobRequestOptions): Promise<void> {
  const force = options?.force === true;
  const enableUq = options?.enableUq === true;
  const includeAmbench = options?.includeAmbench === true;
  const uqSamples = options?.uqSamples ?? 96;
  const { key, evidenceKey, payload, materialSupported } = buildJobKey({ enableUq, includeAmbench, uqSamples });
  if (options?.bypassCache || force) {
    payload.bypassCache = true;
  }
  const st = useLpbfBuildJobStore.getState();
  const materialName = useMaterialSpecimenStore.getState().activeSpecimen.name || "unspecified material";
  const invalidProcess = [payload.laserPower_W,payload.scanSpeed_mm_s,payload.beamDiameter_um,payload.layerThickness_um,payload.hatchSpacing_um].some(value=>!Number.isFinite(value)||value<=0) || !Number.isFinite(payload.preheatTemp_C) || payload.preheatTemp_C<0;
  if (!materialSupported || invalidProcess) {
    useLpbfBuildJobStore.setState({
      job: null,
      busy: false,
      seq: st.seq + 1,
      lastKey: key,
      lastFlags: { enableUq, includeAmbench },
      lastUqSamples: uqSamples,
      sessionUq: null,
      sessionAmbench: null,
      sessionEvidenceKey: null,
      roundTripMs: null,
      error: !materialSupported
        ? `Build screening has no supported material mapping for ${materialName}. Select one of the four supported LPBF alloys; no surrogate alloy was submitted.`
        : "Build screening requires finite positive power, speed, beam, hatch and layer inputs, and nonnegative preheat.",
    });
    return;
  }

  // Client-side short-circuit only for identical fast jobs (no force).
  if (
    !force &&
    !enableUq &&
    !includeAmbench &&
    st.lastKey === key &&
    st.job &&
    !st.error &&
    st.lastFlags.enableUq === false &&
    st.lastFlags.includeAmbench === false
  ) {
    return;
  }
  if (!force && inFlightKey === key && inFlightPromise && inFlightSeq === st.seq) {
    return inFlightPromise;
  }

  const seq = st.seq + 1;
  useLpbfBuildJobStore.setState({
    busy: true,
    seq,
    error: force ? null : st.error,
    lastFlags: { enableUq, includeAmbench },
    lastUqSamples: uqSamples,
  });

  const run = (async () => {
    try {
      const t0 = performance.now();
      const job = await pythonComputationService.solveLpbfBuildJob(payload);
      if (!job.success) {
        throw new Error(job.error || "Python LPBF build-job failed.");
      }
      if (job.solverRevision !== BUILD_JOB_SOLVER_REVISION) {
        throw new Error("LPBF build-job solver revision mismatch; update the Python solver before using this result.");
      }
      const identity = job.buildJobIdentity;
      const snapshot = job.materialPropertySnapshot;
      if (
        !identity ||
        !snapshot ||
        !snapshot.thermal || typeof snapshot.thermal !== "object" || Array.isArray(snapshot.thermal) ||
        !snapshot.slicer || typeof snapshot.slicer !== "object" || Array.isArray(snapshot.slicer) ||
        !Number.isSafeInteger(job.materialPropertySchemaVersion) ||
        !Number.isSafeInteger(snapshot.schemaVersion) ||
        identity.schemaVersion !== 1 ||
        identity.alloyId !== job.alloyId ||
        snapshot.alloyId !== job.alloyId ||
        identity.modelId !== job.modelId ||
        identity.solverRevision !== job.solverRevision ||
        identity.materialPropertySchemaVersion !== job.materialPropertySchemaVersion ||
        snapshot.schemaVersion !== job.materialPropertySchemaVersion ||
        identity.materialPropertyRevision !== job.materialPropertyRevision ||
        typeof job.materialPropertyRevision !== "string" ||
        !/^[a-f0-9]{64}$/.test(job.materialPropertySha256 ?? "") ||
        identity.materialPropertySha256 !== job.materialPropertySha256 ||
        !/^[a-f0-9]{64}$/.test(identity.sha256)
      ) {
        throw new Error("LPBF build-job material/model identity is missing or inconsistent; update the Python solver before using this result.");
      }
      const snapshotHash = await sha256Utf8(canonicalBuildJobMaterialSnapshot(snapshot));
      const identityHash = await sha256Utf8(canonicalBuildJobIdentity(identity));
      if (snapshotHash !== job.materialPropertySha256 || identityHash !== identity.sha256) {
        throw new Error("LPBF build-job material/model identity hash mismatch; update the Python solver before using this result.");
      }
      if (useLpbfBuildJobStore.getState().seq !== seq) return;
      const prev = useLpbfBuildJobStore.getState();
      const sameEvidence = prev.sessionEvidenceKey === evidenceKey;
      const sessionUq = job.uq ?? (sameEvidence ? prev.sessionUq : null);
      const sessionAmbench = job.ambench ?? (sameEvidence ? prev.sessionAmbench : null);
      // Attach retained blocks for UI when this call skipped them.
      const displayJob: PythonLpbfBuildJobResult = {
        ...job,
        uq: sessionUq,
        ambench: sessionAmbench,
      };
      useLpbfBuildJobStore.setState({
        job: displayJob,
        error: null,
        busy: false,
        lastKey: key,
        roundTripMs: Math.round(performance.now() - t0),
        sessionUq,
        sessionAmbench,
        sessionEvidenceKey: evidenceKey,
        lastFlags: { enableUq, includeAmbench },
      });
    } catch (err: unknown) {
      if (useLpbfBuildJobStore.getState().seq !== seq) return;
      const prev = useLpbfBuildJobStore.getState();
      useLpbfBuildJobStore.setState({
        error: err instanceof Error ? err.message : "Python LPBF engines unavailable.",
        busy: false,
        lastKey: key,
        job: prev.lastKey === key ? prev.job : null,
      });
    } finally {
      if (inFlightKey === key && inFlightSeq === seq) {
        inFlightKey = null;
        inFlightPromise = null;
      }
    }
  })();

  inFlightKey = key;
  inFlightSeq = seq;
  inFlightPromise = run;
  return run;
}

/** Debounced Python fetch. Mount on the industrial rail and Decision lab so they share one verdict. */
export function useLpbfBuildJobPython() {
  const specimen = useMaterialSpecimenStore((s) => s.activeSpecimen);
  const liveMesh = useLpbfBuildMeshStore((s) => s.mesh);
  const job = useLpbfBuildJobStore((s) => s.job);
  const error = useLpbfBuildJobStore((s) => s.error);
  const busy = useLpbfBuildJobStore((s) => s.busy);
  const roundTripMs = useLpbfBuildJobStore((s) => s.roundTripMs);
  const lastKey = useLpbfBuildJobStore((s) => s.lastKey);
  const lastFlags = useLpbfBuildJobStore((s) => s.lastFlags);
  const murakamiInput = useLpbfBuildJobStore((s) => s.murakamiInput);
  const aligned = lastKey === peekLpbfBuildJobKey();

  const lpbf = specimen.lpbf;

  useEffect(() => {
    const timer = setTimeout(() => {
      // Debounced default = fast path (no UQ / NIST).
      void requestLpbfBuildJob({ enableUq: false, includeAmbench: false });
    }, 280);
    return () => clearTimeout(timer);
  }, [
    specimen.id,
    specimen.name,
    specimen.composition,
    specimen.baseMetal,
    lpbf.laserPower_W,
    lpbf.scanSpeed_mms,
    lpbf.beamDiameter_um,
    lpbf.preheatTemp_C,
    lpbf.layer_um,
    lpbf.hatch_um,
    lpbf.cadAssetName,
    lpbf.processSeed,
    lpbf.scanStrategy,
    lpbf.inclineAngle_deg,
    lpbf.downskinOverhang_deg,
    liveMesh,
    murakamiInput.defectSqrtAreasPaste,
    murakamiInput.hardness_HV,
    murakamiInput.ctDetectionThreshold_um,
  ]);

  return {
    job: aligned ? job : null,
    error: aligned ? error : null,
    busy,
    roundTripMs: aligned ? roundTripMs : null,
    lastFlags,
    murakamiInput,
    cache: aligned ? job?.cache ?? null : null,
    rerun: () => requestLpbfBuildJob({ force: true, bypassCache: true, enableUq: false, includeAmbench: false }),
    runUq: () =>
      requestLpbfBuildJob({ force: true, enableUq: true, includeAmbench: false, uqSamples: 96 }),
    validateNist: () =>
      requestLpbfBuildJob({ force: true, enableUq: false, includeAmbench: true }),
    setMurakamiInput: setLpbfMurakamiInput,
  };
}
