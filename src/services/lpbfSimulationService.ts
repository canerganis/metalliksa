import { parseGpuPilotArtifactDescriptor } from '../types/lpbfGpuArtifacts';
import { pythonRequestError } from '../utils/pythonValidationError';
import { gpuCapability, GpuCapabilityError } from '../utils/gpuCapability';
import type { GpuPilotArtifactDescriptor } from '../types/lpbfGpuArtifacts';

export type SimulationMode = "screening" | "standard" | "high-fidelity" | "calibration";
export interface SimulationInput {
  material: string; power_W: number; speed_mm_s: number; beamDiameter_um: number;
  preheat_C: number; layer_um: number; hatch_um: number;
  mode?: SimulationMode; backend?: "auto" | "reference" | "openfoam-thermal";
  powderGridPolicy?: "layer-conforming";
  thermalModelId?: 'layered-plate-enthalpy-v1';
  plateThickness_um?: number; supportThickness_um?: number; contactResistance_m2K_W?: number;
  supportBottomBoundary?: 'adiabatic' | 'isothermal-at-preheat';
  incidenceAngle_deg?: number; incidenceAzimuth_deg?: number;
  beamProfileModelId?: 'assumed-oblique-gaussian-normal-plane-v1';
  sourcePenetration_um?: number;
  mesh_um?: number; maxDt_s?: number; tracks?: number; layers?: number;
  strategy?: "meander" | "unidirectional" | "stripe" | "island"; stripeWidth_um?: number; islandSize_um?: number; scanAngle_deg?: number; layerRotation_deg?: number;
  dwell_s?: number; trackLength_um?: number; cooling_s?: number; timeout_s?: number;
  packingFraction?: number; powderConductivityRatio?: number; convection_W_m2K?: number;
  absorptivity?: number; emissivity?: number; study?: "none" | "mesh" | "timestep";
  properties?: unknown;
  measurements?: { width_um: number; depth_um: number; source: string; processVector?: Record<string, unknown>; uncertainty_um?: { width_um: number; depth_um: number }; independentHoldout?: boolean }[];
}
export interface ResourceEstimate {
  cells: number; spacing_m: number; shape: number[]; duration_s: number;
  minimumRequiredSteps?: number; stepBudget?: number; exceedsStepBudget?: boolean;
  minimumEstimatedSteps: number; workingMemoryEstimate_MB: number; runs: number;
  cellBudget: number; exceedsCellBudget: boolean; runtimeEstimate: string; note: string;
}
const CORE_UNITS = { power: 'W', speed: 'mm/s', length: 'um', preheat: 'degC', temperature: 'K', internalLength: 'm', time: 's', energy: 'J', beamDiameter: '1/e2-intensity' } as const;
const LAYERED_CORE_UNITS = { ...CORE_UNITS, incidenceAngle: 'deg', incidenceAzimuth: 'deg', contactResistance: 'm2-K/W' } as const;
export interface CoreContractV1 {
  schemaVersion: 1;
  modelId: 'analytical-conduction-screening-v1' | 'stationary-enthalpy-conduction-v1'
    | 'stationary-enthalpy-conduction-layer-conforming-v1';
  actualBackend: 'analytical' | 'numpy-reference' | 'openfoam-thermal';
  requestedBackend: 'auto' | 'reference' | 'openfoam-thermal';
  effectiveMode: 'screening' | 'standard' | 'calibration';
  solverId: string; inputSha256: string; materialSha256: string;
  units: typeof CORE_UNITS;
  resolvedPhysics: { conduction: true; transient: boolean; latentHeat: boolean; momentum: false; freeSurface: false; evaporation: false };
  evidenceClass: 'unvalidated-model';
}
export interface CoreContractV2 {
  schemaVersion: 2; modelId: 'layered-plate-enthalpy-v1';
  actualBackend: 'numpy-reference'; requestedBackend: 'reference';
  effectiveMode: 'standard'; solverId: 'layered-enthalpy-fv-1';
  inputSha256: string; materialSha256: string; evidenceClass: 'unvalidated-model';
  units: typeof LAYERED_CORE_UNITS;
  resolvedPhysics: { conduction: true; transient: true; latentHeat: true; momentum: false; freeSurface: false;
    evaporation: false; layeredMaterials: true; interfaceModelId: 'planar-series-resistance-v1';
    contactResistanceModelId: 'explicit-area-specific-resistance'; supportMaterialRevisionSha256: string;
    beamSourceModelId: 'assumed-oblique-gaussian-normal-plane-v1'; supportBottomBoundaryId: 'adiabatic' | 'isothermal-at-preheat' };
}
export type CoreContract = CoreContractV1 | CoreContractV2;
export interface SimulationResult {
  transientFrontDiagnostics?: import("../data/quantityEnvelope").QuantityContainer;
  coreContract?: CoreContract;
  /** Wave B LT-3: G, R and cooling rate are single-mesh values; status says how many cells span the pool. */
  solidificationResolution?: {
    methodId: string; mesh_um: number; cellsAcrossWidth: number; cellsAcrossDepth: number;
    gradientStencilCells: number; meshVerified: false;
    status: "not-available" | "stencil-spans-melt-pool" | "single-mesh-unverified"; note: string;
  };
  numericalDiagnostics?: {
    meltPoolExtraction?: string;
    overlapExtraction?: string;
    peakMeltTime_s?: number | null; peakMeltStep?: number | null;
    meltPoolObservedSteps?: number; sampledPeakMeltVolume_um3?: number; peakMeltSamplingLossFraction?: number;
    sourceIntegration: string; stabilityLimit: string; minimumCapturedSourceFraction: number;
    maximumSourceRenormalization: number; maximumSurfaceOffset_um: number;
    maximumTimestep_s: number; maximumEnthalpyIncrement_K: number; sourceTimestepRetries: number;
    acceptedTimestepDistribution?: {
      methodId: "accepted-timestep-distribution-v1"; count: number; total_s: number; sumSquared_s2: number;
      mean_s: number; minimum_s: number; p50_s: number; p90_s: number; p99_s: number; maximum_s: number;
      eulerFirstOrderWeightedDt_s: number; requestedMaxDt_s: number; requestedMaxDtHitFraction: number;
      sourceLimitedStepCount: number; sourceTimestepRetries: number;
    };
  };
  fieldOverlapDiagnostics?: {
    modelId: string; scope: string; tracks: number; layers: number;
    trackOverlapRatio: number | null; meanInterTrackOverlapRatio: number | null; minInterTrackOverlapRatio: number | null;
    pairwiseOverlapRatios?: number[]; interTrackGapVolume_um3: number; hasInterTrackGap: boolean;
    interTrackLackOfFusion: boolean; midpointPenetrationDepth_um?: number; interLayerPenetrationDepth_um?: number;
    interLayerRemeltRatio?: number; globalRemeltRatio: number; totalMeltVolume_um3: number; totalRemeltVolume_um3: number;
    status: string; note: string;
  } | null; // null only for bare-plate runs (enforced by parseSimulationJob)
  geometricDefectScreen?: {
    modelId: string; scope: string; status: string; limitations: string[];
    lackOfFusion: { status: string; ellipseIndex: number | null; signedMargin: number | null;
      overlapDepth_um: number | null; maximumHatch_um: number | null; riskScreened: boolean | null; reason: string | null };
    /** Wave B LA-3: no D/W risk verdict (null; archived pre-Wave-B runs may carry a string); King et al. 2014 sec. 5.2 mode label only. */
    keyhole?: { depthToWidth: number | null; risk: string | null; kingModeIndicator?: "keyhole-mode" | "conduction-mode" | null; reason: string };
  } | null; // null only for bare-plate runs (enforced by parseSimulationJob)
  schemaVersion: 1; requestedMode: SimulationMode; effectiveMode: SimulationMode;
  requestedBackend?: SimulationInput["backend"];
  solver: { id: string; version: string; openfoam: string | null };
  settings: SimulationInput; confidence: "low"; validationStatus: "unvalidated";
  productionReady: false; label: string; fallbackReason: string | null;
  metrics: { width_um: number; depth_um: number; length_um: number; [key: string]: unknown };
  material: { name: string; quality: string; source: string; temperatureCoverage_K?: number[]; sourceValidityRange_K?: number[]; liquidus_K?: number; solidus_K?: number; table?: number[][]; uncertaintyNote?: string };
  /** null only when settings.surfaceMode is "bare-plate" (enforced by parseSimulationJob). */
  analyticalComparison: Record<string, { width_um: number; depth_um: number; length_um: number }> | null;
  assumptions: string[]; regime: string; mainRisk: string; recommendation: string; riskScope: string;
  thermalHistory?: { time_s: number; peak_K: number }[];
  energyBalance?: { input_J: number; losses_J: number; stored_J: number; relativeError: number };
  measurementComparison?: Record<string, { count: number; errors_pct: number[]; rmse_um: number; bias_um: number; calibrationFactor: number | null; note: string }>;
  convergenceStudy?: unknown;
  resourceEstimate?: ResourceEstimate;
  confidenceReason?: string;
  scanPath?: { start_s: number; end_s: number; layer: number; track?: number; start?: number[]; end?: number[] }[];
  provenance?: { createdAt: string; inputHash: string; executionInputHash?: string; implementationHash: string; implementationFingerprintSchema?: string; solverBinaryHash: string | null; runtime_s?: number };
  massBalance?: { initial_kg: number; deposited_kg: number; final_kg: number; relativeError: number; scope: string };
  phaseAudit?: { liquidVolume_m3: number; solidVolume_m3: number; activeVolume_m3: number; minFraction: number; maxFraction: number; scope: string };
  fieldSeries?: "field-series.json" | null;
  fieldPreviews?: string[];
  artifacts?: { path: string; size_bytes: number; sha256: string }[];
  retentionPolicy?: string;
  measurementEvidence?: { source: string; sameProcessVector: string; uncertainty_um: unknown; independentHoldout: boolean | null }[];
  discretization?: { cells: number; mesh_m: number; minimumDt_s: number; meanDt_s: number; steps: number };

}
export interface AcceptedPrefixPoint {
  id: string; cellIndex: number[]; coordinate_m: number[];
  maximumOverComputedInterval_K: number; timeOfMaximum_s: number; lastAcceptedTemperature_K: number;
  history: { time_s: number; temperature_K: number }[];
}
/** Partial temperature history attached to a THERMAL_BOILING_LIMIT refusal (python/lpbf_accepted_prefix.py). */
export interface AcceptedPrefix {
  schema: "lpbf-accepted-prefix-1"; estimateTier: string; tierLabel: string;
  displaySignificantDigits: number | null; uncertaintyStatement: string | null;
  observable: string; maximumLabel: string; computedInterval_s: [number, number];
  acceptedSteps: number; firstRejectedStep: { index: number; reasonCode: string };
  points: AcceptedPrefixPoint[]; pointRule: string; domainWarnings: string[];
  explanation: string | null; noValueText: string | null; completeHistoryText: string;
}
export interface SimulationRefusal {
  code: string; field: string; message: string;
  detail: { acceptedPrefix?: AcceptedPrefix; [key: string]: unknown };
}
export interface SimulationJob {
  errorKind?: "validation"; refusal?: SimulationRefusal;
  id: string; status: "queued" | "running" | "completed" | "failed" | "cancelled" | "timed_out";
  requestSummary?: { mode: string; backend: string; material: string };
  progress: number; log: string; error: string | null; cacheHit?: boolean; deduplicated?: boolean; result?: SimulationResult;
  partialArtifacts?:
    | { status: 'retained-unverified'; fileCount: number; totalBytes: number }
    | { status: 'inventory-unavailable'; fileCount?: number; totalBytes?: number };
}
export interface SimulationCapabilities {
  openfoamVersion: string | null; openfoamThermal: boolean; freeSurfaceSolver: boolean; platform: string;
  limitation: string; materials: { name: string; quality: string; available: boolean; note: string }[];
  cudaThermalPilot?: { selection: string; availability: 'checked-on-submit'; cpuAlternative: string; evidenceScope: string };
}
function object(value: unknown): value is Record<string, unknown> { return typeof value === "object" && value !== null && !Array.isArray(value); }
function literalFields(value: unknown, expected: Record<string, unknown>): boolean {
  return object(value) && Object.keys(value).length === Object.keys(expected).length
    && Object.entries(expected).every(([key, item]) => value[key] === item);
}
const isNumArray = (v: unknown, n?: number): v is number[] =>
  Array.isArray(v) && (n === undefined || v.length === n) && v.every(x => typeof x === "number" && Number.isFinite(x));
const strOrNull = (v: unknown) => v === null || typeof v === "string";
function checkAcceptedPrefix(p: unknown): void {
  const fail = () => { throw new Error("Invalid LPBF accepted prefix"); };
  if (!object(p) || p.schema !== "lpbf-accepted-prefix-1" || typeof p.estimateTier !== "string" || typeof p.tierLabel !== "string"
    || !(p.displaySignificantDigits === null || (Number.isSafeInteger(p.displaySignificantDigits) && Number(p.displaySignificantDigits) >= 1))
    || !strOrNull(p.uncertaintyStatement) || !strOrNull(p.explanation) || !strOrNull(p.noValueText)
    || typeof p.observable !== "string" || typeof p.maximumLabel !== "string" || typeof p.completeHistoryText !== "string"
    || typeof p.pointRule !== "string" || !isNumArray(p.computedInterval_s, 2)
    || !Number.isSafeInteger(p.acceptedSteps) || Number(p.acceptedSteps) < 0
    || !object(p.firstRejectedStep) || !Number.isSafeInteger(p.firstRejectedStep.index) || typeof p.firstRejectedStep.reasonCode !== "string"
    || !Array.isArray(p.domainWarnings) || !p.domainWarnings.every(w => typeof w === "string")
    || !Array.isArray(p.points)) return fail();
  for (const pt of p.points) {
    if (!object(pt) || typeof pt.id !== "string" || !isNumArray(pt.cellIndex) || !isNumArray(pt.coordinate_m, 3)
      || typeof pt.maximumOverComputedInterval_K !== "number" || typeof pt.timeOfMaximum_s !== "number"
      || typeof pt.lastAcceptedTemperature_K !== "number" || !Array.isArray(pt.history)
      || !pt.history.every(h => object(h) && typeof h.time_s === "number" && typeof h.temperature_K === "number")) return fail();
  }
}
function checkRefusal(value: Record<string, unknown>): void {
  const refusal = value.refusal;
  if (value.errorKind === undefined && refusal === undefined) return;
  if (value.status !== "failed" || value.errorKind !== "validation" || !object(refusal)
    || typeof refusal.code !== "string" || typeof refusal.field !== "string" || typeof refusal.message !== "string"
    || !object(refusal.detail)) throw new Error("Invalid LPBF job refusal");
  if (refusal.detail.acceptedPrefix !== undefined) checkAcceptedPrefix(refusal.detail.acceptedPrefix);
}
function checkCoreContract(result: Record<string, unknown>): void {
  if (result.coreContract === undefined) return; // Preserve legacy absence without inventing a binding.
  const c = result.coreContract;
  const fail = () => { throw new Error('Invalid LPBF core contract'); };
  if (!object(c) || !object(result.settings) || !object(result.solver)) return fail();
  const requested = result.settings.backend;
  const mode = result.effectiveMode;
  const solver = result.solver.id;
  if (c.schemaVersion === 2) {
    const settings = result.settings;
    const physics = c.resolvedPhysics;
    const settingInRange = (key: string, minimum: number, maximum: number) =>
      typeof settings[key] === 'number' && Number.isFinite(settings[key])
      && settings[key] >= minimum && settings[key] <= maximum;
    if (mode !== 'standard' || solver !== 'layered-enthalpy-fv-1'
      || requested !== 'reference'
      || result.settings.mode !== 'standard'
      || result.settings.thermalModelId !== 'layered-plate-enthalpy-v1'
      || result.settings.surfaceMode !== 'bare-plate'
      || result.settings.barePlateGeometry !== 'square'
      || result.settings.scanAngle_deg !== 0 || result.settings.layers !== 1 || result.settings.tracks !== 1
      || result.settings.study !== 'none' || result.settings.measurements
      || result.settings.beamProfileModelId !== 'assumed-oblique-gaussian-normal-plane-v1'
      || !settingInRange('plateThickness_um', 5, 10000)
      || !settingInRange('supportThickness_um', 5, 10000)
      || !settingInRange('contactResistance_m2K_W', 0, 1)
      || !settingInRange('incidenceAngle_deg', 0, 89.9)
      || !settingInRange('incidenceAzimuth_deg', 0, 359.999999999)
      || !settingInRange('sourcePenetration_um', 5, 150)
      || !['adiabatic', 'isothermal-at-preheat'].includes(String(result.settings.supportBottomBoundary))
      || typeof c.inputSha256 !== 'string' || !/^[a-f0-9]{64}$/.test(c.inputSha256)
      || typeof c.materialSha256 !== 'string' || !/^[a-f0-9]{64}$/.test(c.materialSha256)
      || !object(physics) || typeof physics.supportMaterialRevisionSha256 !== 'string'
      || !/^[a-f0-9]{64}$/.test(physics.supportMaterialRevisionSha256)
      || physics.supportBottomBoundaryId !== settings.supportBottomBoundary
      || !literalFields(c.units, LAYERED_CORE_UNITS)
      || !literalFields(physics, {
        conduction: true, transient: true, latentHeat: true, momentum: false, freeSurface: false,
        evaporation: false, layeredMaterials: true, interfaceModelId: 'planar-series-resistance-v1',
        contactResistanceModelId: 'explicit-area-specific-resistance',
        supportMaterialRevisionSha256: physics.supportMaterialRevisionSha256,
        beamSourceModelId: 'assumed-oblique-gaussian-normal-plane-v1',
        supportBottomBoundaryId: settings.supportBottomBoundary,
      })
      || !literalFields(c, {
        schemaVersion: 2, modelId: 'layered-plate-enthalpy-v1', actualBackend: 'numpy-reference',
        requestedBackend: requested, effectiveMode: 'standard', solverId: 'layered-enthalpy-fv-1',
        inputSha256: c.inputSha256, materialSha256: c.materialSha256, units: c.units,
        resolvedPhysics: c.resolvedPhysics, evidenceClass: 'unvalidated-model',
      })) return fail();
    return;
  }
  let backend: CoreContract['actualBackend'];
  let transient: boolean;
  if (mode === 'screening' && solver === 'rosenthal+goldak') {
    backend = 'analytical'; transient = false;
  } else if ((mode === 'standard' || mode === 'calibration')
    && (solver === 'enthalpy-fv-6' || solver === 'metalliksaThermal-OpenFOAM14-6')) {
    backend = solver === 'enthalpy-fv-6' ? 'numpy-reference' : 'openfoam-thermal';
    transient = true;
    if (requested !== 'auto' && requested !== (backend === 'numpy-reference' ? 'reference' : 'openfoam-thermal')) return fail();
  } else return fail();
  if (typeof requested !== 'string' || !['auto', 'reference', 'openfoam-thermal'].includes(requested)) return fail();
  const gridPolicy = result.settings.powderGridPolicy;
  if (gridPolicy !== undefined && gridPolicy !== 'layer-conforming') return fail();
  if (gridPolicy === 'layer-conforming'
    && (backend !== 'numpy-reference' || requested !== 'reference'
      || result.settings.surfaceMode !== 'powder-layer' || mode !== 'standard')) return fail();
  const modelId = transient
    ? gridPolicy === 'layer-conforming'
      ? 'stationary-enthalpy-conduction-layer-conforming-v1'
      : 'stationary-enthalpy-conduction-v1'
    : 'analytical-conduction-screening-v1';
  // Structural check only. Python verifies these hashes against full resolved snapshots.
  if (![c.inputSha256, c.materialSha256].every(v => typeof v === 'string' && /^[a-f0-9]{64}$/.test(v))) return fail();
  if (!literalFields(c.units, CORE_UNITS) || !literalFields(c.resolvedPhysics, {
    conduction: true, transient, latentHeat: transient, momentum: false, freeSurface: false, evaporation: false,
  }) || !literalFields(c, {
    schemaVersion: 1, modelId,
    actualBackend: backend, requestedBackend: requested, effectiveMode: mode, solverId: solver,
    inputSha256: c.inputSha256, materialSha256: c.materialSha256, units: c.units,
    resolvedPhysics: c.resolvedPhysics, evidenceClass: 'unvalidated-model',
  })) return fail();
}
function finiteTree(value: unknown): boolean {
  if (typeof value === "number") return Number.isFinite(value);
  if (Array.isArray(value)) return value.every(finiteTree);
  return !object(value) || Object.values(value).every(finiteTree);
}
// python/lpbf_simulation.py emits analyticalComparison, fieldOverlapDiagnostics and
// geometricDefectScreen as null exactly for bare-plate runs (no powder-layer screening or
// inter-track overlap tracker exists). null is accepted for those fields only in that case.
function barePlateNull(result: Record<string, unknown>, value: unknown): boolean {
  return value === null && object(result.settings) && result.settings.surfaceMode === "bare-plate";
}
function dimensions(value: unknown): boolean {
  return object(value) && ["width_um", "depth_um", "length_um"].every(k => typeof value[k] === "number" && Number.isFinite(value[k]) && (value[k] as number) >= 0);
}
function checkClosure(value: unknown, keys: string[], tolerance: number): void {
  if (!object(value) || !keys.every(k => typeof value[k] === "number" && Number(value[k]) >= 0)) throw new Error("Missing or invalid thermal conservation audit");
  const [total, a, b] = keys.map(k => Number(value[k]));
  if (Math.abs(total-a-b)/Math.max(total,1e-30) > tolerance || (value.relativeError !== undefined && (typeof value.relativeError !== "number" || value.relativeError < 0 || value.relativeError > tolerance))) throw new Error("Failed thermal conservation audit");
}
export function parseSimulationJob(value: unknown): SimulationJob {
  if (!object(value) || !finiteTree(value) || typeof value.id !== "string" || !/^[a-f0-9]{32}$/.test(value.id)
    || !["queued", "running", "completed", "failed", "cancelled", "timed_out"].includes(String(value.status))
    || typeof value.progress !== "number" || value.progress < 0 || value.progress > 1 || typeof value.log !== "string"
    || !(value.error === null || typeof value.error === "string")) throw new Error("Invalid LPBF job response");
  if (value.status !== "completed" && value.result !== undefined) throw new Error("Unfinished job must not contain a result");
  if (value.partialArtifacts !== undefined) {
    const partial = value.partialArtifacts;
    if (!["failed", "cancelled", "timed_out"].includes(String(value.status)) || !object(partial)
      || Object.keys(partial).some(key => !["status", "fileCount", "totalBytes"].includes(key))
      || (partial.status === "retained-unverified"
        ? Object.keys(partial).length !== 3 || !Number.isSafeInteger(partial.fileCount)
          || Number(partial.fileCount) < 1 || !Number.isSafeInteger(partial.totalBytes)
          || Number(partial.totalBytes) < 0
        : partial.status !== "inventory-unavailable"
          || (partial.fileCount !== undefined && (!Number.isSafeInteger(partial.fileCount) || Number(partial.fileCount) < 0))
          || (partial.totalBytes !== undefined && (!Number.isSafeInteger(partial.totalBytes) || Number(partial.totalBytes) < 0)))) {
      throw new Error("Invalid LPBF partial artifact inventory");
    }
  }
  checkRefusal(value);
  if (value.status === "completed") {
    const r = value.result;
    if (!object(r)
      || typeof r.requestedMode !== "string" || !["screening", "standard", "high-fidelity", "calibration"].includes(r.requestedMode)
      || typeof r.effectiveMode !== "string" || !["screening", "standard", "calibration"].includes(r.effectiveMode)
      || !(r.fallbackReason === null || typeof r.fallbackReason === "string")
      || (r.requestedMode !== r.effectiveMode && (r.effectiveMode !== "screening" || typeof r.fallbackReason !== "string" || !r.fallbackReason.trim()))
      || (object(r.settings) && r.settings.mode !== undefined && r.settings.mode !== r.requestedMode)) throw new Error("Invalid LPBF execution mode or fallback provenance");
    if (!object(r) || r.schemaVersion !== 1 || r.validationStatus !== "unvalidated" || r.productionReady !== false
      || r.confidence !== "low" || !dimensions(r.metrics) || !object(r.settings) || !object(r.solver)
      || typeof r.solver.id !== "string" || typeof r.solver.version !== "string" || !object(r.material)
      || !["name", "quality", "source"].every(k => typeof (r.material as Record<string, unknown>)[k] === "string")
      || !["label", "regime", "mainRisk", "recommendation", "riskScope"].every(k => typeof r[k] === "string")
      || !Array.isArray(r.assumptions) || !r.assumptions.every(a => typeof a === "string")
      || !(object(r.analyticalComparison)
        ? Object.values(r.analyticalComparison).every(dimensions)
        : barePlateNull(r, r.analyticalComparison))) throw new Error("Invalid LPBF result contract");
    checkCoreContract(r);
    if (r.thermalHistory !== undefined && (!Array.isArray(r.thermalHistory) || !r.thermalHistory.every((h, index, history) => object(h) && typeof h.time_s === "number" && h.time_s >= 0 && typeof h.peak_K === "number" && h.peak_K > 0
      && (index === 0 || h.time_s > history[index - 1].time_s)))) throw new Error("Invalid thermal history");
    if (!object(r.metrics) || Object.values(r.metrics).some(v => typeof v === "number" && v < 0)) throw new Error("Negative physical result");
    if (r.energyBalance !== undefined && (!object(r.energyBalance) || !["input_J", "losses_J", "stored_J", "relativeError"].every(k => typeof (r.energyBalance as Record<string, unknown>)[k] === "number"))) throw new Error("Invalid energy audit");
    if (r.massBalance !== undefined && (!object(r.massBalance) || !["initial_kg", "deposited_kg", "final_kg", "relativeError"].every(k => typeof (r.massBalance as Record<string, unknown>)[k] === "number" && Number((r.massBalance as Record<string, unknown>)[k]) >= 0) || typeof r.massBalance.scope !== "string")) throw new Error("Invalid mass audit");
    if (r.phaseAudit !== undefined && (!object(r.phaseAudit) || !["liquidVolume_m3", "solidVolume_m3", "activeVolume_m3", "minFraction", "maxFraction"].every(k => typeof (r.phaseAudit as Record<string, unknown>)[k] === "number" && Number((r.phaseAudit as Record<string, unknown>)[k]) >= 0) || Number(r.phaseAudit.maxFraction) > 1 || Number(r.phaseAudit.minFraction) > Number(r.phaseAudit.maxFraction) || typeof r.phaseAudit.scope !== "string")) throw new Error("Invalid phase audit");
    if (r.effectiveMode === "standard" || r.effectiveMode === "calibration") {
      checkClosure(r.energyBalance, ["input_J", "losses_J", "stored_J"], .01);
      checkClosure(r.massBalance, ["final_kg", "initial_kg", "deposited_kg"], 1e-10);
      checkClosure(r.phaseAudit, ["activeVolume_m3", "liquidVolume_m3", "solidVolume_m3"], 1e-10);
    }
    if (r.artifacts !== undefined && (!Array.isArray(r.artifacts) || !r.artifacts.every(a => object(a) && typeof a.path === "string" && !a.path.includes("..") && !a.path.startsWith("/") && typeof a.size_bytes === "number" && Number.isSafeInteger(a.size_bytes) && a.size_bytes >= 0 && typeof a.sha256 === "string" && /^[a-f0-9]{64}$/.test(a.sha256)))) throw new Error("Invalid artifact manifest");
    if (r.fieldSeries != null && r.fieldSeries !== "field-series.json") throw new Error("Invalid field series artifact");
    if (r.numericalDiagnostics !== undefined) {
      const d = r.numericalDiagnostics;
      if (!object(d) || (d.sourceIntegration !== "cell-integrated-gaussian-gl2-v1"
        && d.sourceIntegration !== "cell-integrated-gaussian-adaptive-gl-v2")
        || d.stabilityLimit !== "local-conductance-row-sum"
        || !["minimumCapturedSourceFraction", "maximumSourceRenormalization", "maximumSurfaceOffset_um", "maximumTimestep_s", "maximumEnthalpyIncrement_K", "sourceTimestepRetries"].every(k => typeof d[k] === "number" && Number(d[k]) >= 0)
        || Number(d.minimumCapturedSourceFraction) <= 0 || Number(d.minimumCapturedSourceFraction) > 1
        || Number(d.maximumSourceRenormalization) < 1 || !Number.isSafeInteger(d.sourceTimestepRetries)) throw new Error("Invalid numerical source diagnostics");
      if (d.acceptedTimestepDistribution !== undefined) {
        const s = d.acceptedTimestepDistribution;
        const numeric = ["total_s", "sumSquared_s2", "mean_s", "minimum_s", "p50_s", "p90_s", "p99_s", "maximum_s",
          "eulerFirstOrderWeightedDt_s", "requestedMaxDt_s"];
        if (!object(s) || s.methodId !== "accepted-timestep-distribution-v1"
          || !Number.isSafeInteger(s.count) || Number(s.count) < 1
          || !numeric.every(k => typeof s[k] === "number" && Number(s[k]) > 0)
          || !Number.isSafeInteger(s.sourceLimitedStepCount) || Number(s.sourceLimitedStepCount) < 0
          || Number(s.sourceLimitedStepCount) > Number(s.count)
          || !Number.isSafeInteger(s.sourceTimestepRetries) || Number(s.sourceTimestepRetries) < Number(s.sourceLimitedStepCount)
          || Number(s.sourceTimestepRetries) !== Number(d.sourceTimestepRetries)
          || typeof s.requestedMaxDtHitFraction !== "number" || Number(s.requestedMaxDtHitFraction) < 0
          || Number(s.requestedMaxDtHitFraction) > 1
          || !(Number(s.minimum_s) <= Number(s.p50_s) && Number(s.p50_s) <= Number(s.p90_s)
            && Number(s.p90_s) <= Number(s.p99_s) && Number(s.p99_s) <= Number(s.maximum_s))
          || Math.abs(Number(s.mean_s) - Number(s.total_s) / Number(s.count)) > Math.max(Number(s.mean_s) * 1e-10, 1e-30)
          || Math.abs(Number(s.eulerFirstOrderWeightedDt_s) - Number(s.sumSquared_s2) / Number(s.total_s))
            > Math.max(Number(s.eulerFirstOrderWeightedDt_s) * 1e-10, 1e-30)
          || Number(s.eulerFirstOrderWeightedDt_s) < Number(s.minimum_s) * (1 - 1e-10)
          || Number(s.eulerFirstOrderWeightedDt_s) > Number(s.maximum_s) * (1 + 1e-10)) {
          throw new Error("Invalid accepted-timestep distribution diagnostics");
        }
      }
      if (d.meltPoolExtraction !== undefined && (d.meltPoolExtraction !== "accepted-step-molten-volume-v1"
        || !Number.isSafeInteger(d.meltPoolObservedSteps) || Number(d.meltPoolObservedSteps) < 1
        || typeof d.sampledPeakMeltVolume_um3 !== "number" || d.sampledPeakMeltVolume_um3 < 0
        || typeof d.peakMeltSamplingLossFraction !== "number" || d.peakMeltSamplingLossFraction < 0 || d.peakMeltSamplingLossFraction > 1
        || !(d.peakMeltTime_s === null && d.peakMeltStep === null
          || typeof d.peakMeltTime_s === "number" && d.peakMeltTime_s > 0 && Number.isSafeInteger(d.peakMeltStep)
            && Number(d.peakMeltStep) > 0 && Number(d.peakMeltStep) <= Number(d.meltPoolObservedSteps)))) throw new Error("Invalid melt pool extraction diagnostics");
    }
    if (r.fieldOverlapDiagnostics !== undefined && !barePlateNull(r, r.fieldOverlapDiagnostics)) {
      const d = r.fieldOverlapDiagnostics;
      if (!object(d) || d.modelId !== "field-inter-track-overlap-v1" || typeof d.scope !== "string"
        || !Number.isSafeInteger(d.tracks) || Number(d.tracks) < 1 || !Number.isSafeInteger(d.layers) || Number(d.layers) < 1
        || !(d.trackOverlapRatio === null || (typeof d.trackOverlapRatio === "number" && d.trackOverlapRatio >= 0 && d.trackOverlapRatio <= 1))
        || typeof d.interTrackGapVolume_um3 !== "number" || d.interTrackGapVolume_um3 < 0
        || typeof d.hasInterTrackGap !== "boolean" || typeof d.interTrackLackOfFusion !== "boolean"
        || typeof d.globalRemeltRatio !== "number" || d.globalRemeltRatio < 0 || d.globalRemeltRatio > 1
        || typeof d.totalMeltVolume_um3 !== "number" || d.totalMeltVolume_um3 < 0
        || typeof d.totalRemeltVolume_um3 !== "number" || d.totalRemeltVolume_um3 < 0
        || typeof d.status !== "string" || typeof d.note !== "string") throw new Error("Invalid field overlap diagnostics");
    }
    if (r.geometricDefectScreen !== undefined && !barePlateNull(r, r.geometricDefectScreen)) {
      const d = r.geometricDefectScreen;
      const loss = object(d) ? d.lackOfFusion : undefined;
      if (!object(d) || !["elliptic-overlap-screening-v1", "elliptic-overlap-screening-v2"].includes(d.modelId as string) || typeof d.scope !== "string" || typeof d.status !== "string"
        || !Array.isArray(d.limitations) || !d.limitations.every(v => typeof v === "string") || !object(loss)
        || typeof loss.status !== "string" || !(loss.reason === null || typeof loss.reason === "string")
        || !(loss.riskScreened === null || typeof loss.riskScreened === "boolean")
        || !["ellipseIndex", "signedMargin", "overlapDepth_um", "maximumHatch_um"].every(k => loss[k] === null || typeof loss[k] === "number")) throw new Error("Invalid geometric defect screening");
    }
    if (r.fieldPreviews !== undefined && (!Array.isArray(r.fieldPreviews) || !r.fieldPreviews.every(a => a === "temperature-slice.svg" || a === "phase-slice.svg"))) throw new Error("Invalid field preview");
    if (r.measurementComparison !== undefined && (!object(r.measurementComparison) || !Object.values(r.measurementComparison).every(c => object(c)
      && typeof c.count === "number" && Number.isSafeInteger(c.count) && c.count > 0
      && typeof c.rmse_um === "number" && c.rmse_um >= 0 && typeof c.bias_um === "number"
      && (c.calibrationFactor === null || (typeof c.calibrationFactor === "number" && c.calibrationFactor > 0))
      && Array.isArray(c.errors_pct) && c.errors_pct.length === c.count && c.errors_pct.every(e => typeof e === "number") && typeof c.note === "string"))) throw new Error("Invalid measurement comparison");
  }
  return value as unknown as SimulationJob;
}
async function request(url: string, options?: RequestInit): Promise<unknown> {
  const res = await fetch(url, { ...options, signal: AbortSignal.timeout(25000), headers: { "Content-Type": "application/json" } });
  if (!res.ok) {
    // Read the body once: a GPU capability refusal is shown as such, every other error goes through pythonRequestError.
    const body: unknown = await res.json().catch(() => null);
    const capability = object(body) ? gpuCapability(body.capability) : null;
    if (capability) throw new GpuCapabilityError(capability);
    throw await pythonRequestError({ status: res.status, json: async () => body }, `LPBF request failed (HTTP ${res.status}).`);
  }
  const data: unknown = await res.json();
  return data;
}
export const simulationApi = {
  async capabilities(): Promise<SimulationCapabilities> {
    const c = await request("/api/lpbf/capabilities");
    if (!object(c) || typeof c.openfoamThermal !== "boolean" || typeof c.freeSurfaceSolver !== "boolean" || typeof c.limitation !== "string"
      || !Array.isArray(c.materials) || !c.materials.every(m => object(m) && typeof m.name === "string" && typeof m.available === "boolean" && typeof m.quality === "string" && typeof m.note === "string")) throw new Error("Invalid worker capabilities");
    return c as unknown as SimulationCapabilities;
  },
  async estimate(input: SimulationInput): Promise<ResourceEstimate> {
    const e = await request("/api/lpbf/estimate", { method: "POST", body: JSON.stringify(input) });
    if (!object(e) || !finiteTree(e) || typeof e.cells !== "number" || e.cells <= 0 || typeof e.minimumEstimatedSteps !== "number") throw new Error("Invalid resource estimate");
    return e as unknown as ResourceEstimate;
  },
  async submit(input: SimulationInput, options: { executionScope?: 'repeat' } = {}) {
    const endpoint = options.executionScope === 'repeat' ? "/api/lpbf/jobs/repeat" : "/api/lpbf/jobs";
    return parseSimulationJob(await request(endpoint, { method: "POST", body: JSON.stringify(input) }));
  },
  async get(id: string) { return parseSimulationJob(await request(`/api/lpbf/jobs/${encodeURIComponent(id)}`)); },
  async cancel(id: string) { return parseSimulationJob(await request(`/api/lpbf/jobs/${encodeURIComponent(id)}`, { method: "DELETE" })); },
};


/** Separate CUDA pilot contract. It must never be parsed as a standard CPU job. */
export interface GpuPilotInput extends Omit<SimulationInput, 'backend' | 'mode' | 'study' | 'tracks' | 'layers' | 'measurements'> {
  jobType: 'gpu-thermal-pilot';
  executionEngine?: 'warp';
  backend: `cuda:${number}`;
  mode: 'standard';
  surfaceMode: 'powder-layer';
  powderGridPolicy: 'layer-conforming';
  study: 'none';
  tracks: 1;
  layers: 1;
}
const GPU_PILOT_OPTIONAL_FIELDS = [
  'mesh_um', 'maxDt_s', 'stripeWidth_um', 'islandSize_um', 'scanAngle_deg', 'layerRotation_deg',
  'dwell_s', 'trackLength_um', 'cooling_s', 'timeout_s', 'packingFraction',
  'powderConductivityRatio', 'convection_W_m2K', 'absorptivity', 'emissivity',
] as const;

/** Build only fields accepted by the CPU reference validator, even from older runtime inputs. */
export function buildGpuPilotInput(input: SimulationInput, settings: Partial<SimulationInput>,
  device: `cuda:${number}`, material: string, strategy: SimulationInput['strategy'], properties?: unknown,
  executionEngine: 'torch' | 'warp' = 'torch'): GpuPilotInput {
  const merged = { ...input, ...settings };
  const optional = Object.fromEntries(GPU_PILOT_OPTIONAL_FIELDS
    .filter(key => merged[key] !== undefined).map(key => [key, merged[key]])) as Partial<GpuPilotInput>;
  return {
    ...optional, material, power_W: input.power_W, speed_mm_s: input.speed_mm_s,
    beamDiameter_um: input.beamDiameter_um, preheat_C: input.preheat_C,
    layer_um: input.layer_um, hatch_um: input.hatch_um, strategy,
    ...(properties !== undefined ? { properties } : {}),
    jobType: 'gpu-thermal-pilot', backend: device, mode: 'standard',
    ...(executionEngine === 'warp' ? { executionEngine: 'warp' as const } : {}),
    surfaceMode: 'powder-layer', powderGridPolicy: 'layer-conforming',
    study: 'none', tracks: 1, layers: 1,
  };
}
export type GpuPilotStatus = 'pass' | 'failed' | 'inconclusive';
export interface GpuPilotComparison {
  status: GpuPilotStatus;
  cpu?: number; gpu?: number; relativeDifference?: number;
  absoluteDifference_um?: number; relativeRiseL2?: number; relativeRiseMax?: number;
  reason?: string;
}
interface GpuPilotDeviceEvidenceBase {
  selected: string; name: string; computeCapability: number[];
  thermalEvolution: string; sourceIntegration: 'cpu' | `cuda:${number}`;
  sourceTimestepLimiter?: 'cpu' | `cuda:${number}`; synchronizedAfterSolve: true;
}
type GpuPilotDeviceEvidence = GpuPilotDeviceEvidenceBase & (
  | { torch: string; cudaRuntime: string; warp?: never; engineId?: never;
      warpCudaToolkitVersion?: never; cudaDriverVersion?: never }
  | { warp: string; engineId: 'warp'; warpCudaToolkitVersion: string; cudaDriverVersion: string;
      torch?: never; cudaRuntime?: never }
);
interface GpuPilotResultBase {
  schemaVersion: 1; jobType: 'gpu-thermal-pilot';
  requestedMode: 'standard'; effectiveMode: 'gpu-pilot';
  validationStatus: 'unvalidated'; productionReady: false; label: string;
  settings: GpuPilotInput;
  solver: { id: 'enthalpy-fv-6-cuda-pilot-1' | 'enthalpy-fv-6-warp-candidate-1'; modelId: 'stationary-enthalpy-conduction-layer-conforming-v1';
    actualBackend: string; thermalEvolutionDevice: string; sourceIntegrationDevice: 'cpu' | `cuda:${number}`;
    sourceTimestepLimiterDevice: 'cpu' | `cuda:${number}`; dtype: 'float64' };
  material: { name: string; materialId: string; materialRevisionSha256: string; version: string };
  metrics: { width_um: number; depth_um: number; length_um: number; volume_um3: number; peakTemperature_K: number };
  energyBalance: { input_J: number; losses_J: number; stored_J: number; relativeError: number };
  discretization: { cells: number; mesh_m: number; minimumDt_s: number; maximumDt_s: number; meanDt_s: number; steps: number };
  gpuPilot: { status: GpuPilotStatus; scope: string; experimentalValidation: false;
    targets: { integralRelativeMax: number; widthDepthAbsoluteCellsMax: number;
      fieldRiseL2RelativeMax: number; fieldRiseMaxRelativeMax: number; peakMeltVolumeRelativeMax: number; source: string };
    cpu: { solver: { id: string }; coreContract: { modelId: 'stationary-enthalpy-conduction-layer-conforming-v1'; actualBackend: 'numpy-reference' };
      material: { materialRevisionSha256: string }; discretization: { cells: number; steps: number; mesh_m: number } };
    comparisons: Record<string, GpuPilotComparison> };
  provenance: { inputHash: string; implementationHash: string; implementationFingerprintSchema?: string; materialVersion: string; createdAt: string;
    deviceEvidence: GpuPilotDeviceEvidence;
    runtime_s?: number };
}
export type GpuPilotArtifactManifestEntry = { path: string; size_bytes: number; sha256: string };
export type GpuPilotResult = GpuPilotResultBase & (
  | { artifacts: []; gpuRunContract?: never; gpuFieldArtifacts?: never }
  | { artifacts: GpuPilotArtifactManifestEntry[]; gpuRunContract: Record<string, unknown>;
      gpuFieldArtifacts: GpuPilotArtifactDescriptor }
);
export interface GpuPilotJob {
  id: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled' | 'timed_out';
  requestSummary: { jobType: 'gpu-thermal-pilot'; backend: string; mode: string; material: string; executionEngine?: 'torch' | 'warp' };
  progress: number; log: string; error: string | null;
  cacheHit?: boolean; deduplicated?: boolean;
  result?: GpuPilotResult;
}

const GPU_COMPARISON_KEYS = ['finalSampling', 'finalTemperatureField', 'peakTemperature_K',
  'input_J', 'losses_J', 'stored_J', 'width_um', 'depth_um', 'length_um', 'volume_um3'] as const;
const gpuStatus = (value: unknown): value is GpuPilotStatus =>
  value === 'pass' || value === 'failed' || value === 'inconclusive';
const gpuSourceDevicesMatch = (solver: unknown, evidence: unknown, selected: unknown): boolean => {
  if (!object(solver) || !object(evidence) || typeof selected !== 'string'
    || !/^cuda:[0-9]+$/.test(selected)) return false;
  const source = solver.sourceIntegrationDevice;
  const limiter = solver.sourceTimestepLimiterDevice;
  if (source === 'cpu' && limiter === 'cpu') {
    return evidence.sourceIntegration === 'cpu'
      && (evidence.sourceTimestepLimiter === undefined || evidence.sourceTimestepLimiter === 'cpu');
  }
  return source === selected && limiter === selected
    && evidence.sourceIntegration === selected && evidence.sourceTimestepLimiter === selected;
};

function exactKeys(value: unknown, keys: readonly string[]): value is Record<string, unknown> {
  return object(value) && Object.keys(value).length === keys.length
    && keys.every(key => Object.hasOwn(value, key));
}

function sameJsonValue(left: unknown, right: unknown): boolean {
  if (left === right) return true;
  if (Array.isArray(left) || Array.isArray(right)) {
    return Array.isArray(left) && Array.isArray(right) && left.length === right.length
      && left.every((item, index) => sameJsonValue(item, right[index]));
  }
  if (!object(left) || !object(right)) return false;
  const leftKeys = Object.keys(left);
  const rightKeys = Object.keys(right);
  return leftKeys.length === rightKeys.length && leftKeys.every(key =>
    Object.hasOwn(right, key) && sameJsonValue(left[key], right[key]));
}

function validateGpuBoundArchive(result: Record<string, unknown>): 'torch' | 'warp' {
  const fail = () => { throw new Error('Invalid bound CUDA pilot archive contract'); };
  if (!Object.hasOwn(result, 'gpuRunContract') || !Object.hasOwn(result, 'gpuFieldArtifacts')
    || 'coreContract' in result || !Array.isArray(result.artifacts)
    || result.artifacts.length > 10_000) return fail();
  const contract = result.gpuRunContract;
  const engineId = object(contract) && contract.schemaVersion === 2 ? 'warp' : 'torch';
  if (!exactKeys(contract, ['schemaVersion', 'runKind', 'capture', 'serializedInputs', 'hashes'])
    || (contract.schemaVersion !== 1 && contract.schemaVersion !== 2)
    || contract.runKind !== 'gpu-thermal-pilot') return fail();
  const capture = contract.capture;
  const serialized = contract.serializedInputs;
  const hashes = contract.hashes;
  if (!exactKeys(capture, engineId === 'warp'
    ? ['contractStatus', 'modelId', 'backend', 'device', 'dtype', 'engineId']
    : ['contractStatus', 'modelId', 'backend', 'device', 'dtype'])
    || capture.contractStatus !== (engineId === 'warp' ? 'gpu-pilot-v2-warp-bound' : 'gpu-pilot-v1-bound')
    || (engineId === 'warp' && capture.engineId !== 'warp')
    || capture.modelId !== 'stationary-enthalpy-conduction-layer-conforming-v1'
    || !object(result.settings) || capture.backend !== result.settings.backend
    || capture.device !== result.settings.backend
    || capture.dtype !== 'float64'
    || !exactKeys(serialized, ['requestJson', 'materialJson', 'cpuInputJson', 'cpuResolvedSettingsJson'])
    || !exactKeys(hashes, ['requestHash', 'materialHash', 'cpuInputHash', 'cpuResolvedSettingsHash', 'implementationHash'])
    || Object.values(serialized).some(value => typeof value !== 'string')
    || Object.values(hashes).some(value => typeof value !== 'string' || !/^[a-f0-9]{64}$/.test(value))) return fail();
  if (!object(result.settings) || !object(result.material) || !object(result.solver)
    || !object(result.provenance) || result.solver.modelId !== capture.modelId
    || result.solver.dtype !== capture.dtype || result.provenance.implementationHash !== hashes.implementationHash
    || result.provenance.inputHash !== hashes.requestHash) return fail();

  let request: unknown; let material: unknown; let cpuInput: unknown; let resolved: unknown;
  try {
    request = JSON.parse(serialized.requestJson as string);
    material = JSON.parse(serialized.materialJson as string);
    cpuInput = JSON.parse(serialized.cpuInputJson as string);
    resolved = JSON.parse(serialized.cpuResolvedSettingsJson as string);
  } catch { return fail(); }
  const expectedCpuInput = { ...result.settings };
  delete expectedCpuInput.jobType;
  if (engineId === 'warp') delete expectedCpuInput.executionEngine;
  expectedCpuInput.backend = 'reference';
  if (!sameJsonValue(request, result.settings) || !sameJsonValue(material, result.material)
    || !sameJsonValue(cpuInput, expectedCpuInput) || !sameJsonValue(resolved, cpuInput)) return fail();

  let descriptor: GpuPilotArtifactDescriptor;
  try { descriptor = parseGpuPilotArtifactDescriptor(result.gpuFieldArtifacts); }
  catch { return fail(); }
  const expected = new Map<string, { size_bytes: number; sha256: string }>();
  for (const backend of ['cpu', 'gpu'] as const) {
    for (const ref of Object.values(descriptor.states[backend].fields)) {
      if (expected.has(ref.path)) return fail();
      expected.set(ref.path, { size_bytes: ref.size_bytes, sha256: ref.sha256 });
    }
  }
  const found = new Set<string>();
  const foundExact = new Set<string>();
  let totalBytes = 0;
  for (const raw of result.artifacts) {
    if (!exactKeys(raw, ['path', 'size_bytes', 'sha256']) || typeof raw.path !== 'string'
      || !raw.path || raw.path.length > 512 || /[\\:\u0000-\u001f]/.test(raw.path)
      || raw.path.split('/').some(part => !part || part === '.' || part === '..' || /[. ]$/.test(part)
        || /^(con|prn|aux|nul|com[0-9]|lpt[0-9])(?:\.|$)/i.test(part))
      || typeof raw.size_bytes !== 'number' || !Number.isSafeInteger(raw.size_bytes) || raw.size_bytes < 0
      || typeof raw.sha256 !== 'string' || !/^[a-f0-9]{64}$/.test(raw.sha256)) return fail();
    const key = raw.path.toLocaleLowerCase('en-US');
    if (found.has(key)) return fail();
    found.add(key);
    foundExact.add(raw.path);
    totalBytes += raw.size_bytes;
    if (!Number.isSafeInteger(totalBytes) || totalBytes > 256 * 1024 * 1024) return fail();
    const field = expected.get(raw.path);
    if (field && (field.size_bytes !== raw.size_bytes || field.sha256 !== raw.sha256)) return fail();
  }
  if ([...expected.keys()].some(path => !foundExact.has(path))) return fail();
  return engineId;
}

export function parseGpuPilotJob(value: unknown): GpuPilotJob {
  if (!object(value) || !finiteTree(value) || typeof value.id !== 'string' || !/^[a-f0-9]{32}$/.test(value.id)
    || !['queued', 'running', 'completed', 'failed', 'cancelled', 'timed_out'].includes(String(value.status))
    || typeof value.progress !== 'number' || value.progress < 0 || value.progress > 1
    || typeof value.log !== 'string' || !(value.error === null || typeof value.error === 'string')
    || !object(value.requestSummary) || value.requestSummary.jobType !== 'gpu-thermal-pilot'
    || typeof value.requestSummary.backend !== 'string' || !/^cuda:[0-9]+$/.test(value.requestSummary.backend)
    || typeof value.requestSummary.mode !== 'string' || typeof value.requestSummary.material !== 'string'
    || (value.requestSummary.executionEngine !== undefined
      && value.requestSummary.executionEngine !== 'torch' && value.requestSummary.executionEngine !== 'warp')) {
    throw new Error('Invalid CUDA pilot job response');
  }
  if (value.status !== 'completed') {
    if (value.result !== undefined) throw new Error('Unfinished CUDA pilot job must not contain a result');
    return value as unknown as GpuPilotJob;
  }
  const r = value.result;
  if (!object(r) || 'coreContract' in r) throw new Error('Invalid CUDA pilot result identity');
  const hasBoundContract = Object.hasOwn(r, 'gpuRunContract');
  const hasBoundFields = Object.hasOwn(r, 'gpuFieldArtifacts');
  if (hasBoundContract !== hasBoundFields
    || (hasBoundContract && (r.gpuRunContract === null || r.gpuFieldArtifacts === null))) {
    throw new Error('Invalid bound CUDA pilot archive contract');
  }
  const engineId = hasBoundContract ? validateGpuBoundArchive(r) : 'torch';
  const evidence = object(r.provenance) && object(r.provenance.deviceEvidence)
    ? r.provenance.deviceEvidence : undefined;
  const runtimeMatchesEngine = engineId === 'warp'
    ? !!evidence && evidence.engineId === 'warp' && typeof evidence.warp === 'string' && !!evidence.warp.trim()
      && !Object.hasOwn(evidence, 'torch') && !Object.hasOwn(evidence, 'cudaRuntime')
      && typeof evidence.warpCudaToolkitVersion === 'string' && /^[1-9][0-9]*\.[0-9]+$/.test(evidence.warpCudaToolkitVersion)
      && typeof evidence.cudaDriverVersion === 'string' && /^[1-9][0-9]*\.[0-9]+$/.test(evidence.cudaDriverVersion)
    : !!evidence && typeof evidence.torch === 'string' && !!evidence.torch.trim()
      && !Object.hasOwn(evidence, 'warp') && !Object.hasOwn(evidence, 'engineId')
      && !Object.hasOwn(evidence, 'warpCudaToolkitVersion') && !Object.hasOwn(evidence, 'cudaDriverVersion')
      && typeof evidence.cudaRuntime === 'string' && !!evidence.cudaRuntime.trim();
  if (!object(r) || r.schemaVersion !== 1 || r.jobType !== 'gpu-thermal-pilot'
    || r.requestedMode !== 'standard' || r.effectiveMode !== 'gpu-pilot'
    || r.validationStatus !== 'unvalidated' || r.productionReady !== false
    || typeof r.label !== 'string' || !object(r.settings) || r.settings.jobType !== 'gpu-thermal-pilot'
    || r.settings.backend !== value.requestSummary.backend || r.settings.mode !== 'standard'
    || r.settings.study !== 'none' || r.settings.surfaceMode !== 'powder-layer'
    || r.settings.powderGridPolicy !== 'layer-conforming'
    || r.settings.tracks !== 1 || r.settings.layers !== 1
    || !object(r.solver) || r.solver.id !== (engineId === 'warp' ? 'enthalpy-fv-6-warp-candidate-1' : 'enthalpy-fv-6-cuda-pilot-1')
    || r.solver.modelId !== 'stationary-enthalpy-conduction-layer-conforming-v1'
    || r.solver.actualBackend !== r.settings.backend
    || r.solver.thermalEvolutionDevice !== r.settings.backend
    || r.solver.dtype !== 'float64' || !object(r.material)
    || typeof r.material.name !== 'string' || typeof r.material.materialId !== 'string'
    || typeof r.material.version !== 'string' || !r.material.version.trim()
    || typeof r.material.materialRevisionSha256 !== 'string' || !/^[a-f0-9]{64}$/.test(r.material.materialRevisionSha256)
    || !object(r.metrics) || !dimensions(r.metrics) || typeof r.metrics.volume_um3 !== 'number'
    || r.metrics.volume_um3 < 0 || typeof r.metrics.peakTemperature_K !== 'number' || r.metrics.peakTemperature_K <= 0
    || !object(r.discretization) || !Number.isSafeInteger(r.discretization.cells) || Number(r.discretization.cells) <= 0
    || !Number.isSafeInteger(r.discretization.steps) || Number(r.discretization.steps) <= 0
    || typeof r.discretization.mesh_m !== 'number' || r.discretization.mesh_m <= 0
    || !object(r.provenance) || !object(r.provenance.deviceEvidence)
    || typeof r.provenance.inputHash !== 'string' || !/^[a-f0-9]{64}$/.test(r.provenance.inputHash)
    || typeof r.provenance.implementationHash !== 'string' || !/^[a-f0-9]{64}$/.test(r.provenance.implementationHash)
    || r.provenance.materialVersion !== r.material.version
    || typeof r.provenance.createdAt !== 'string' || !Number.isFinite(Date.parse(r.provenance.createdAt))
    || !runtimeMatchesEngine
    || !Array.isArray(r.provenance.deviceEvidence.computeCapability)
    || r.provenance.deviceEvidence.computeCapability.length !== 2
    || r.provenance.deviceEvidence.computeCapability.some(part => !Number.isSafeInteger(part) || part < 0)
    || !gpuSourceDevicesMatch(r.solver, r.provenance.deviceEvidence, r.settings.backend)
    || r.provenance.deviceEvidence.selected !== r.settings.backend
    || r.provenance.deviceEvidence.thermalEvolution !== r.settings.backend
    || r.provenance.deviceEvidence.synchronizedAfterSolve !== true
    || typeof r.provenance.deviceEvidence.name !== 'string' || !r.provenance.deviceEvidence.name.trim()
    || !object(r.gpuPilot) || r.gpuPilot.experimentalValidation !== false
    || !gpuStatus(r.gpuPilot.status) || !object(r.gpuPilot.cpu)
    || !object(r.gpuPilot.cpu.coreContract)
    || r.gpuPilot.cpu.coreContract.modelId !== r.solver.modelId
    || r.gpuPilot.cpu.coreContract.actualBackend !== 'numpy-reference'
    || !object(r.gpuPilot.cpu.material)
    || r.gpuPilot.cpu.material.materialRevisionSha256 !== r.material.materialRevisionSha256
    || !object(r.gpuPilot.targets) || !object(r.gpuPilot.comparisons)
    || !Array.isArray(r.artifacts) || (!hasBoundContract && r.artifacts.length !== 0)) {
    throw new Error('Invalid CUDA pilot result identity');
  }
  if ((engineId === 'warp' && (r.settings.executionEngine !== 'warp'
      || r.solver.sourceIntegrationDevice !== 'cpu' || r.solver.sourceTimestepLimiterDevice !== 'cpu'))
    || (engineId === 'torch' && Object.hasOwn(r.settings, 'executionEngine'))
    || (value.requestSummary.executionEngine !== undefined && value.requestSummary.executionEngine !== engineId)
    || (engineId === 'warp' && value.requestSummary.executionEngine !== 'warp')) {
    throw new Error('CUDA pilot solver engine identity mismatch');
  }
  checkClosure(r.energyBalance, ['input_J', 'losses_J', 'stored_J'], .01);
  const comparisons = r.gpuPilot.comparisons as Record<string, unknown>;
  if (!GPU_COMPARISON_KEYS.every(key => {
    const item = comparisons[key];
    return object(item) && gpuStatus(item.status);
  })) {
    throw new Error('Incomplete CUDA pilot parity report');
  }
  // The report must describe the same GPU result the UI displays, including
  // failed/inconclusive reports. Equal summaries alone do not prove field parity.
  for (const key of ['peakTemperature_K', 'width_um', 'depth_um', 'length_um', 'volume_um3',
    'input_J', 'losses_J', 'stored_J']) {
    const item = comparisons[key] as Record<string, unknown>;
    const actual = key.endsWith('_J') ? r.energyBalance[key] : r.metrics[key];
    if (typeof item.cpu !== 'number' || item.cpu < 0 || item.gpu !== actual) {
      throw new Error('CUDA pilot parity result binding mismatch');
    }
  }
  const statuses = GPU_COMPARISON_KEYS.map(key => (comparisons[key] as Record<string, unknown>).status);
  const status = statuses.includes('failed') ? 'failed' : statuses.includes('inconclusive') ? 'inconclusive' : 'pass';
  if (status !== r.gpuPilot.status) throw new Error('CUDA pilot parity status mismatch');
  const targets = r.gpuPilot.targets;
  if (targets.integralRelativeMax !== .01 || targets.widthDepthAbsoluteCellsMax !== 1
    || targets.fieldRiseL2RelativeMax !== .01 || targets.fieldRiseMaxRelativeMax !== .01
    || targets.peakMeltVolumeRelativeMax !== .01
    || targets.source !== 'docs/DIGITAL_TWIN_MASTER_PLAN_2026-09-21.md#11') {
    throw new Error('CUDA pilot frozen parity targets changed');
  }
  if (status === 'pass') {
    const field = comparisons.finalTemperatureField as Record<string, unknown>;
    if (typeof field.relativeRiseL2 !== 'number' || field.relativeRiseL2 < 0
      || typeof field.relativeRiseMax !== 'number' || field.relativeRiseMax < 0
      || field.relativeRiseL2 > targets.fieldRiseL2RelativeMax
      || field.relativeRiseMax > targets.fieldRiseMaxRelativeMax) {
      throw new Error('CUDA pilot field parity exceeds target');
    }
    for (const key of ['peakTemperature_K', 'input_J', 'losses_J', 'stored_J']) {
      const item = comparisons[key] as Record<string, unknown>;
      if (typeof item.cpu !== 'number' || typeof item.gpu !== 'number'
        || Math.abs(item.cpu-item.gpu)/Math.max(Math.abs(item.cpu), 1e-30) > targets.integralRelativeMax) {
        throw new Error('CUDA pilot integral parity exceeds target');
      }
    }
    for (const key of ['width_um', 'depth_um', 'length_um']) {
      const item = comparisons[key] as Record<string, unknown>;
      if (typeof item.cpu !== 'number' || typeof item.gpu !== 'number'
        || Math.abs(item.cpu-item.gpu) > targets.widthDepthAbsoluteCellsMax * Number(r.discretization.mesh_m) * 1e6) {
        throw new Error('CUDA pilot geometry parity exceeds target');
      }
    }
    const volume = comparisons.volume_um3 as Record<string, unknown>;
    if (typeof volume.cpu !== 'number' || typeof volume.gpu !== 'number'
      || Math.abs(volume.cpu-volume.gpu)/Math.max(volume.cpu, 1e-30) > targets.peakMeltVolumeRelativeMax) {
      throw new Error('CUDA pilot melt-volume parity exceeds target');
    }
  }
  return value as unknown as GpuPilotJob;
}

export const gpuPilotApi = {
  async submit(input: GpuPilotInput) {
    return parseGpuPilotJob(await request('/api/lpbf/jobs', { method: 'POST', body: JSON.stringify(input) }));
  },
  async get(id: string) {
    return parseGpuPilotJob(await request(`/api/lpbf/jobs/${encodeURIComponent(id)}`));
  },
  async cancel(id: string) {
    return parseGpuPilotJob(await request(`/api/lpbf/jobs/${encodeURIComponent(id)}`, { method: 'DELETE' }));
  },
};

/** Separate IN625 bare-substrate contract; it is not a generic transient material. */
export interface In625BareplateConfig {
  shapeXYZ: [number, number, number];
  cellSizeM: [number, number, number];
  initialTemperatureK: number;
  dtS: number;
  steps: number;
  absorbedPowerW: number;
  spotSigmaM: number;
  scanStartXM: number;
  scanYM: number;
  scanVelocityXMS: number;
}
export interface In625BareplateInput {
  jobType: 'in625-bareplate-field';
  backend: 'cpu' | `cuda:${number}`;
  config: In625BareplateConfig;
}
export interface In625BareplateResult {
  schemaVersion: 1;
  jobType: 'in625-bareplate-field';
  requestedMode: 'screening';
  effectiveMode: 'screening';
  fallbackReason: null;
  settings: In625BareplateInput;
  material: { schemaVersion: number; materialId: 'in625'; materialRevisionSha256: string;
    temperatureCoverage_K: [number, number]; validationStatus: 'unvalidated-literature-model-screening';
    [key: string]: unknown };
  solver: { id: 'in625-bareplate-field-v1'; modelId: 'in625-bareplate-enthalpy-conduction-v1';
    revision: '1'; actualBackend: 'cpu' | `cuda:${number}`; device: string; dtype: 'float64' };
  validationStatus: 'unvalidated-literature-model-screening'; productionReady: false;
  confidence: 'low'; label: string;
  modelScope: string;
  metrics: { cells: number; peakTemperature_K: number; finalTime_s: number; finalEnthalpy_J: number;
    energyResidual_J: number; minimumSourceCaptureFraction: number };
  energyHistory: Array<{ time_s: number; totalEnthalpy_J: number; peakTemperature_K: number; energyResidual_J: number }>;
  energyBalance: { input_J: number; losses_J: number; stored_J: number; relativeError: number; scope: string };
  field: { artifact: 'in625-temperature-field-f64le.bin'; shapeXYZ: [number, number, number]; dtype: 'float64';
    encoding: 'little-endian'; byteOrder: 'little-endian'; arrayOrder: 'z,y,x'; sha256: string;
    scope: 'final cell-centered temperature field only; no interface interpolation' };
  numericalDiagnostics: { sourceCaptureFractionMinimum: number; temperatureBounds_K: [number, number];
    density_kg_m3: 8440; densityBasis: string };
  provenance: { inputSha256: string; implementationIdentity: { modelId: string; solverRevision: string;
    materialRevisionSha256: string; backend: string; device: string };
    deviceEvidence: { name: string; index: number | null; computeCapability?: number[];
      torch?: string; cudaRuntime?: string; synchronizedAfterSolve: true } };
  artifacts: Array<{ path: string; size_bytes: number; sha256: string }>;
  assumptions: string[];
  runKind?: 'bounded-material-screening';
}
export interface In625BareplateJob {
  id: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled' | 'timed_out';
  requestSummary: { jobType: 'in625-bareplate-field'; backend: 'cpu' | `cuda:${number}` };
  progress: number; log: string; error: string | null;
  cacheHit?: boolean; deduplicated?: boolean;
  result?: In625BareplateResult;
}

const in625Backend = (value: unknown): value is 'cpu' | `cuda:${number}` =>
  value === 'cpu' || typeof value === 'string' && /^cuda:[0-9]+$/.test(value);
const in625Config = (value: unknown): value is In625BareplateConfig => object(value)
  && Array.isArray(value.shapeXYZ) && value.shapeXYZ.length === 3
  && value.shapeXYZ.every(n => typeof n === 'number' && Number.isSafeInteger(n) && n >= 2)
  && Array.isArray(value.cellSizeM) && value.cellSizeM.length === 3
  && value.cellSizeM.every(n => typeof n === 'number' && Number.isFinite(n) && n > 0)
  && ['initialTemperatureK', 'dtS', 'absorbedPowerW', 'spotSigmaM', 'scanStartXM', 'scanYM', 'scanVelocityXMS']
    .every(key => typeof value[key] === 'number' && Number.isFinite(value[key]))
  && typeof value.steps === 'number' && Number.isSafeInteger(value.steps) && value.steps > 0 && value.steps <= 25_000
  && Number.isSafeInteger(value.shapeXYZ[0] * value.shapeXYZ[1] * value.shapeXYZ[2])
  && value.shapeXYZ[0] * value.shapeXYZ[1] * value.shapeXYZ[2] <= 1_000_000
  && Number.isSafeInteger(value.shapeXYZ[0] * value.shapeXYZ[1] * value.shapeXYZ[2] * value.steps)
  && value.shapeXYZ[0] * value.shapeXYZ[1] * value.shapeXYZ[2] * value.steps <= 2_000_000;

export function parseIn625BareplateJob(value: unknown): In625BareplateJob {
  if (!object(value) || !finiteTree(value) || typeof value.id !== 'string' || !/^[a-f0-9]{32}$/.test(value.id)
    || !['queued', 'running', 'completed', 'failed', 'cancelled', 'timed_out'].includes(String(value.status))
    || typeof value.progress !== 'number' || value.progress < 0 || value.progress > 1
    || typeof value.log !== 'string' || !(value.error === null || typeof value.error === 'string')
    || !object(value.requestSummary) || value.requestSummary.jobType !== 'in625-bareplate-field'
    || !in625Backend(value.requestSummary.backend)) {
    throw new Error('Invalid IN625 bare-plate job response');
  }
  if (value.status !== 'completed') {
    if (value.result !== undefined) throw new Error('Unfinished IN625 bare-plate job must not contain a result');
    return value as unknown as In625BareplateJob;
  }
  const r = value.result;
  if (!object(r) || r.schemaVersion !== 1 || r.jobType !== 'in625-bareplate-field'
    || r.requestedMode !== 'screening' || r.effectiveMode !== 'screening' || r.fallbackReason !== null
    || r.validationStatus !== 'unvalidated-literature-model-screening' || r.productionReady !== false
    || r.confidence !== 'low' || typeof r.label !== 'string' || typeof r.modelScope !== 'string'
    || !object(r.settings) || r.settings.jobType !== 'in625-bareplate-field'
    || r.settings.backend !== value.requestSummary.backend || !in625Config(r.settings.config)
    || !object(r.material) || r.material.materialId !== 'in625'
    || r.material.validationStatus !== 'unvalidated-literature-model-screening'
    || !Array.isArray(r.material.temperatureCoverage_K)
    || r.material.temperatureCoverage_K[0] !== 273.15 || r.material.temperatureCoverage_K[1] !== 1623.15
    || typeof r.material.materialRevisionSha256 !== 'string' || !/^[a-f0-9]{64}$/.test(r.material.materialRevisionSha256)
    || !object(r.solver) || r.solver.modelId !== 'in625-bareplate-enthalpy-conduction-v1'
    || r.solver.id !== 'in625-bareplate-field-v1' || r.solver.revision !== '1'
    || r.solver.actualBackend !== value.requestSummary.backend || r.solver.device !== value.requestSummary.backend
    || r.solver.dtype !== 'float64'
    || !object(r.metrics) || !['cells', 'peakTemperature_K', 'finalTime_s', 'finalEnthalpy_J', 'energyResidual_J', 'minimumSourceCaptureFraction']
      .every(key => typeof r.metrics[key] === 'number')
    || !Array.isArray(r.energyHistory) || !r.energyHistory.length || !r.energyHistory.every(row => object(row)
      && ['time_s', 'totalEnthalpy_J', 'peakTemperature_K', 'energyResidual_J'].every(key => typeof row[key] === 'number'))
    || !object(r.energyBalance) || !['input_J', 'losses_J', 'stored_J', 'relativeError']
      .every(key => typeof r.energyBalance[key] === 'number')
    || typeof r.energyBalance.losses_J !== 'number' || typeof r.energyBalance.relativeError !== 'number'
    || r.energyBalance.losses_J !== 0 || r.energyBalance.relativeError > .01
    || !object(r.field) || r.field.artifact !== 'in625-temperature-field-f64le.bin'
    || r.field.encoding !== 'little-endian' || r.field.dtype !== 'float64'
    || r.field.byteOrder !== 'little-endian' || r.field.arrayOrder !== 'z,y,x'
    || r.field.scope !== 'final cell-centered temperature field only; no interface interpolation'
    || typeof r.field.sha256 !== 'string' || !/^[a-f0-9]{64}$/.test(r.field.sha256)
    || !Array.isArray(r.field.shapeXYZ) || r.field.shapeXYZ.length !== 3
    || !object(r.numericalDiagnostics) || r.numericalDiagnostics.density_kg_m3 !== 8440
    || !Array.isArray(r.numericalDiagnostics.temperatureBounds_K)
    || r.numericalDiagnostics.temperatureBounds_K[0] !== 273.15 || r.numericalDiagnostics.temperatureBounds_K[1] !== 1623.15
    || typeof r.numericalDiagnostics.densityBasis !== 'string'
    || !object(r.provenance) || typeof r.provenance.inputSha256 !== 'string'
    || !object(r.provenance.implementationIdentity)
    || r.provenance.implementationIdentity.modelId !== r.solver.modelId
    || r.provenance.implementationIdentity.solverRevision !== r.solver.revision
    || r.provenance.implementationIdentity.materialRevisionSha256 !== r.material.materialRevisionSha256
    || r.provenance.implementationIdentity.backend !== value.requestSummary.backend
    || !object(r.provenance.deviceEvidence) || r.provenance.deviceEvidence.selected !== value.requestSummary.backend
    || r.provenance.deviceEvidence.thermalEvolution !== value.requestSummary.backend
    || r.provenance.deviceEvidence.noCpuFallback !== true
    || typeof r.provenance.deviceEvidence.name !== 'string'
    || r.provenance.deviceEvidence.synchronizedAfterSolve !== true
    || !Array.isArray(r.artifacts) || !r.artifacts.some(a => object(a)
      && a.path === 'in625-temperature-field-f64le.bin'
      && a.sha256 === (r.field as Record<string, unknown>).sha256 && typeof a.size_bytes === 'number')
    || !Array.isArray(r.assumptions) || !r.assumptions.every(item => typeof item === 'string')
    || r.runKind !== 'bounded-material-screening') {
    throw new Error('Invalid IN625 bare-plate result identity');
  }
  const energyBalance = r.energyBalance as In625BareplateResult['energyBalance'];
  const metrics = r.metrics as In625BareplateResult['metrics'];
  const settings = r.settings as unknown as In625BareplateInput;
  const field = r.field as In625BareplateResult['field'];
  const expectedCells = settings.config.shapeXYZ[0] * settings.config.shapeXYZ[1] * settings.config.shapeXYZ[2];
  if (energyBalance.input_J < 0 || energyBalance.stored_J < 0 || energyBalance.relativeError < 0
    || metrics.cells !== expectedCells || JSON.stringify(field.shapeXYZ) !== JSON.stringify(settings.config.shapeXYZ)) {
    throw new Error('Inconsistent IN625 bare-plate result');
  }
  const fieldEntry = (r.artifacts as Array<Record<string, unknown>>).find(a => a.path === field.artifact);
  if (!fieldEntry || fieldEntry.size_bytes !== expectedCells * Float64Array.BYTES_PER_ELEMENT
    || fieldEntry.sha256 !== field.sha256) throw new Error('Invalid IN625 bare-plate field manifest');
  return value as unknown as In625BareplateJob;
}

export const in625BareplateApi = {
  async submit(input: In625BareplateInput) {
    return parseIn625BareplateJob(await request('/api/lpbf/jobs', { method: 'POST', body: JSON.stringify(input) }));
  },
  async get(id: string) {
    return parseIn625BareplateJob(await request(`/api/lpbf/jobs/${encodeURIComponent(id)}`));
  },
  async cancel(id: string) {
    return parseIn625BareplateJob(await request(`/api/lpbf/jobs/${encodeURIComponent(id)}`, { method: 'DELETE' }));
  },
};

export async function fetchIn625BareplateTemperatureField(jobId: string, result: In625BareplateResult) {
  const response = await fetch(
    `/api/lpbf/jobs/${encodeURIComponent(jobId)}/artifacts/${encodeURIComponent(result.field.artifact)}`,
    { signal: AbortSignal.timeout(25000), headers: { Accept: 'application/octet-stream' }, cache: 'no-store' },
  );
  if (!response.ok) {
    let message = `LPBF HTTP ${response.status}`;
    try {
      const payload: unknown = await response.json();
      if (object(payload) && typeof payload.error === 'string') message = payload.error;
    } catch { /* Binary or empty error responses use the HTTP status. */ }
    throw new Error(message);
  }
  if (!response.headers.get('content-type')?.toLowerCase().startsWith('application/octet-stream')) {
    throw new Error('Invalid IN625 temperature-field artifact content type');
  }
  const bytes = new Uint8Array(await response.arrayBuffer());
  const expectedBytes = result.field.shapeXYZ.reduce((product, count) => product * count, 1) * Float64Array.BYTES_PER_ELEMENT;
  const artifact = result.artifacts.find(entry => entry.path === result.field.artifact);
  if (!artifact || bytes.byteLength !== expectedBytes || artifact.size_bytes !== expectedBytes
    || artifact.sha256 !== result.field.sha256) throw new Error('IN625 field artifact size/manifest mismatch');
  const digest = await globalThis.crypto.subtle.digest('SHA-256', bytes);
  const actualSha256 = Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('');
  if (actualSha256 !== result.field.sha256) throw new Error('IN625 field artifact SHA-256 mismatch');
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const temperaturesK = new Float64Array(expectedBytes / Float64Array.BYTES_PER_ELEMENT);
  for (let index = 0; index < temperaturesK.length; index += 1) {
    const temperature = view.getFloat64(index * Float64Array.BYTES_PER_ELEMENT, true);
    if (!Number.isFinite(temperature) || temperature < 273.15 || temperature > 1623.15) {
      throw new Error('IN625 field contains a nonfinite or out-of-range temperature');
    }
    temperaturesK[index] = temperature;
  }
  return { shapeXYZ: result.field.shapeXYZ, temperaturesK, sha256: actualSha256 };
}

/** Opt-in Ti-6Al-4V fixed-surface evaporative model (research). A separate job type: it is never parsed as a standard job. */
export const TI64_EVAPORATIVE_JOB_TYPE = 'ti64-evaporative-surface' as const;
export interface Ti64EvaporationScenario {
  transitionLow_K: number; transitionHigh_K: number; ambientPressure_Pa: number; returnFraction: number;
  maxTemperature_K: number; surfaceTension_N_m?: number;
}
export interface Ti64EvaporativeConfig {
  power_W: number; speed_mm_s: number; beamDiameter_um: number; preheat_C: number; trackLength_um: number;
  evaporation: Ti64EvaporationScenario;
}
export interface Ti64EvaporativeInput { jobType: typeof TI64_EVAPORATIVE_JOB_TYPE; config: Ti64EvaporativeConfig }
export interface Ti64EvaporativeResult {
  schema: 'lpbf-ti64-evaporative-result-v1'; modelId: 'ti64-fixed-surface-evaporation-v1';
  jobType: typeof TI64_EVAPORATIVE_JOB_TYPE; status: 'completed';
  settings: { jobType: typeof TI64_EVAPORATIVE_JOB_TYPE; config: Record<string, unknown> };
  experimentalValidation: false; productionReady: false; tier: string;
  acceptedStepCount: number; acceptedTime_s: number;
  energy: { input_J: number; base_J: number; radiativeConvective_J: number; evaporative_J: number; stored_J: number; residual_J: number; relativeResidual: number };
  peakTemperature_K: number; temperatureLabel: string;
  diagnosticEmittedMass_kg: number; diagnosticMassLabel: string;
  geometry: {
    width_um: number | null; depth_um: number | null; length_um: number | null; volume_um3: number | null;
    label: string; widthLabel: string; widthWarning: string | null; refusalReason: string | null; basis: string; liquidus_K: number;
    cellResolution_um: number; truncated: boolean;
  };
  gate: { onset: boolean; unresolvedGeometry: boolean; firstOnsetTime_s: number | null; firstUnresolvedTime_s: number | null; geometryAvailable: boolean };
  warnings: string[];
  fieldSummary: { shape: [number, number, number]; dx_m: number };
  provenance: { inputs: Record<string, unknown>; implementationHash: string; requestSha256: string; [key: string]: unknown };
}
export interface Ti64EvaporativeJob {
  id: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled' | 'timed_out';
  requestSummary: { jobType: typeof TI64_EVAPORATIVE_JOB_TYPE; config: Record<string, unknown> };
  progress: number; log: string; error: string | null;
  errorKind?: 'validation'; refusal?: SimulationRefusal;
  cacheHit?: boolean; deduplicated?: boolean;
  result?: Ti64EvaporativeResult;
}

const isNumber = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value);
const nullableNumber = (value: unknown) => value === null || isNumber(value);

export function parseTi64EvaporativeJob(value: unknown): Ti64EvaporativeJob {
  const invalid = () => new Error('Invalid Ti64 evaporative job response');
  if (!object(value) || !finiteTree(value) || typeof value.id !== 'string' || !/^[a-f0-9]{32}$/.test(value.id)
    || !['queued', 'running', 'completed', 'failed', 'cancelled', 'timed_out'].includes(String(value.status))
    || !isNumber(value.progress) || value.progress < 0 || value.progress > 1
    || typeof value.log !== 'string' || !(value.error === null || typeof value.error === 'string')
    || !object(value.requestSummary) || value.requestSummary.jobType !== TI64_EVAPORATIVE_JOB_TYPE
    || !object(value.requestSummary.config)) throw invalid();
  if (value.status !== 'completed') {
    if (value.result !== undefined) throw new Error('Unfinished Ti64 evaporative job must not contain a result');
    checkRefusal(value);
    return value as unknown as Ti64EvaporativeJob;
  }
  const r = value.result;
  if (!object(r) || r.schema !== 'lpbf-ti64-evaporative-result-v1' || r.modelId !== 'ti64-fixed-surface-evaporation-v1'
    || r.jobType !== TI64_EVAPORATIVE_JOB_TYPE || r.status !== 'completed'
    || r.experimentalValidation !== false || r.productionReady !== false || typeof r.tier !== 'string'
    || !object(r.settings) || r.settings.jobType !== TI64_EVAPORATIVE_JOB_TYPE
    || JSON.stringify(r.settings.config) !== JSON.stringify(value.requestSummary.config)
    || !isNumber(r.acceptedStepCount) || !isNumber(r.acceptedTime_s) || !isNumber(r.peakTemperature_K)
    || typeof r.temperatureLabel !== 'string' || !isNumber(r.diagnosticEmittedMass_kg)
    || typeof r.diagnosticMassLabel !== 'string'
    || !Array.isArray(r.warnings) || !r.warnings.every(w => typeof w === 'string')
    || !object(r.provenance) || !object(r.provenance.inputs)) throw new Error('Invalid Ti64 evaporative result identity');
  const e = r.energy;
  if (!object(e) || !['input_J', 'base_J', 'radiativeConvective_J', 'evaporative_J', 'stored_J', 'residual_J', 'relativeResidual']
    .every(key => isNumber(e[key])) || Math.abs(e.relativeResidual as number) > 1e-9) throw new Error('Invalid Ti64 evaporative energy ledger');
  const g = r.geometry;
  const gate = r.gate;
  if (!object(g) || !object(gate) || typeof gate.onset !== 'boolean' || typeof gate.geometryAvailable !== 'boolean'
    || !['width_um', 'depth_um', 'length_um', 'volume_um3'].every(key => nullableNumber(g[key]))
    || typeof g.label !== 'string' || typeof g.widthLabel !== 'string'
    || !(g.widthWarning === null || typeof g.widthWarning === 'string')
    || !(g.refusalReason === null || typeof g.refusalReason === 'string')) throw new Error('Invalid Ti64 evaporative geometry');
  // A refused extent must stay null and carry its reason: never accept a filled value beside a closed gate.
  if (!gate.geometryAvailable && (['depth_um', 'length_um', 'volume_um3'].some(key => g[key] !== null)
    || typeof g.refusalReason !== 'string' || g.refusalReason.length === 0)) throw new Error('Inconsistent Ti64 evaporative refusal');
  return value as unknown as Ti64EvaporativeJob;
}

export const ti64EvaporativeApi = {
  async submit(input: Ti64EvaporativeInput, options: { executionScope?: 'repeat' } = {}) {
    const endpoint = options.executionScope === 'repeat' ? '/api/lpbf/jobs/repeat' : '/api/lpbf/jobs';
    return parseTi64EvaporativeJob(await request(endpoint, { method: 'POST', body: JSON.stringify(input) }));
  },
  async get(id: string) {
    return parseTi64EvaporativeJob(await request(`/api/lpbf/jobs/${encodeURIComponent(id)}`));
  },
  async cancel(id: string) {
    return parseTi64EvaporativeJob(await request(`/api/lpbf/jobs/${encodeURIComponent(id)}`, { method: 'DELETE' }));
  },
};
