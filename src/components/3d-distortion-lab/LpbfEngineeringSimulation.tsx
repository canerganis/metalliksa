import { SOLIDIFICATION_WORDING, TRANSIENT_FRONT_METRICS } from "../../utils/solidificationDisplay";
import { SolidificationQuantities } from "../SolidificationQuantities";
import { canonicalLpbfMaterialName } from "../../utils/lpbfMaterialIdentity";
import { warpCapabilityFromInventory } from '../../utils/gpuCapability';
import { GpuCapabilityNotice } from '../GpuCapabilityNotice';
import { isResultStale, resultSignatureOnSubmit } from "../../utils/lpbfResultStaleness";
import { Badge, ResultHeader, StaleResultBanner, ThermalHistory, ConvergencePanel, MeasurementPanel, surface, number } from "./LpbfResultPresentation";
import { LpbfPhysicsDiagnostics } from "./LpbfPhysicsDiagnostics";
import { ResolvedThermalViewer } from "./ResolvedThermalViewer";
import React, { useEffect, useRef, useState } from "react";
import { ExecutedMaterialProvenance, LpbfJobArchiver, gpuPilotEngineLabel as validatedGpuPilotEngineLabel } from "../LpbfRunArchivePanel";
import { In625BareplatePanel } from "../In625BareplatePanel";
import { Ti64EvaporativePanel } from "../Ti64EvaporativePanel";
import { simulationApi, gpuPilotApi, buildGpuPilotInput, type GpuPilotInput, type GpuPilotJob, type GpuPilotResult, SimulationInput, SimulationJob, SimulationMode, SimulationCapabilities, ResourceEstimate, SimulationResult } from "../../services/lpbfSimulationService";
import { useVisiblePolling } from "../../hooks/useVisiblePolling";
import { useVisibleInterval } from "../../hooks/useVisibleInterval";
import { useMaterialSpecimenStore } from "../../store/useMaterialSpecimenStore";
import { DISPLAY_LOCALE, formatExactNumber } from "../../utils/numberFormat";
import { SIMULATION_MODES, simulationModeLimitations } from "../../data/simulationModes";
import { readChoice, writeChoice } from "../../utils/viewerPreference";
import { IS_STATIC_DEMO } from "../../demo/flag.ts";
import { DemoLock, DemoUnavailable } from "../../demo/demoNotes.tsx";
import { DEMO_UNAVAILABLE_LOCK } from "../../demo/demoGate.ts";
// Static demo: sections whose inputs have no snapshot are locked to the recorded values (compile-time constant, a normal build renders a plain fragment).
const Lock: React.ElementType = IS_STATIC_DEMO ? DemoLock : React.Fragment;

import { LPBF_ENGINEERING_DEFAULTS as defaults, engineeringSignature, resumeEngineeringJob, useEngineeringField, useLpbfEngineeringStore } from "../../store/useLpbfEngineeringStore";
export const GPU_PILOT_ENGINE_PREFERENCE_KEY = "metalliksa.lpbf.gpuPilot.engine.v1";
const GPU_PILOT_ENGINES = ["torch", "warp"] as const;
const controls = [
  ["stripeWidth_um","Stripe width (µm)",20,3000], ["islandSize_um","Island size (µm)",50,3000],
  ["mesh_um","Mesh spacing (µm)",5,80], ["maxDt_s","Maximum timestep (s)",1e-9,1e-4],
  ["tracks","Track count",1,8], ["layers","Layer count",1,5], ["trackLength_um","Track length (µm)",100,3000],
  ["dwell_s","Inter-track dwell (s)",0,.1], ["cooling_s","Final cooling (s)",0,.1],
  ["scanAngle_deg","Scan angle (°)",-360,360], ["layerRotation_deg","Layer rotation (°)",-360,360],
  ["packingFraction","Powder packing fraction",.2,1], ["powderConductivityRatio","Powder / solid conductivity",.01,1],
  ["convection_W_m2K","Convection (W/m²K)",0,1000], ["timeout_s","Timeout (s)",10,3600],
] as const;
const modes = SIMULATION_MODES;
const fmt = number;
export function CancelledRunNotice({ status }: { status?: SimulationJob["status"] }) {
  if (status !== "cancelled") return null;
  return <p role="status" className="rounded-xl border border-amber-400/30 bg-amber-400/5 p-4 text-sm text-amber-200">Run cancelled. No completed result is available, so this run cannot be archived or exported.</p>;
}
const inputClass = "w-full min-w-0 rounded-lg bg-slate-950/60 border border-slate-600/70 px-3 py-2.5 text-slate-100 transition-colors hover:border-slate-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300";
type ReadinessStatus = "pass" | "warn" | "fail" | "pending";
type ReadinessItem = { status: ReadinessStatus; label: string; details: string };
export function materialTableAvailabilityReadiness(available: boolean | undefined, userSupplied: boolean, missing: boolean): Pick<ReadinessItem, "status" | "details"> {
  if (missing) return { status: "fail", details: "Material thermophysical table is missing; exploratory execution requires a table." };
  if (userSupplied) return { status: "pending", details: "User-supplied material table is awaiting worker validation; exploratory execution remains available." };
  if (available === true) return { status: "pass", details: "Registry reports a material table for exploratory execution; availability does not establish source quality." };
  return { status: "pending", details: "Material table availability is waiting for worker capability metadata." };
}
export function materialSourceEvidenceReadiness(quality?: string): Pick<ReadinessItem, "status" | "details"> {
  if (!quality) return { status: "pending", details: "Source review and quantified property uncertainty are not established; treat material data as unverified." };
  const label = quality === "estimated" || quality === "estimated-legacy"
    ? "Estimated legacy material data"
    : quality === "user-supplied-unverified"
      ? "User-supplied material data"
      : `Material data quality: ${quality}`;
  return { status: "warn", details: `${label}; source review and quantified property uncertainty are not established. Exploratory execution remains available; this is not a material quality PASS.` };
}
const readinessGlyph: Record<ReadinessStatus, string> = {
  pass: "✓",
  warn: "!",
  fail: "×",
  pending: "•",
};
const readinessClasses: Record<ReadinessStatus, string> = {
  pass: "border-emerald-300/30 bg-emerald-500/10 text-emerald-100",
  warn: "border-amber-300/30 bg-amber-500/10 text-amber-100",
  fail: "border-red-300/30 bg-red-500/10 text-red-100",
  pending: "border-slate-500/40 bg-slate-600/10 text-slate-200",
};
type ParsedMeasurementState = {
  status: "valid" | "invalid" | "empty";
  measurements?: NonNullable<SimulationInput["measurements"]>;
  errors: string[];
  mismatchedCount: number;
  missingProcessVectorCount: number;
  count: number;
};
// Keep this supplied-evidence schema aligned with python/lpbf_evidence.py PROCESS_KEYS.
// Never derive missing measurement conditions from the simulation controls.
const processVectorKeys = ["material", "power_W", "speed_mm_s", "beamDiameter_um", "preheat_C",
  "layer_um", "hatch_um", "tracks", "layers", "trackLength_um", "strategy", "scanAngle_deg",
  "layerRotation_deg", "dwell_s", "packingFraction", "stripeWidth_um", "islandSize_um",
  "absorptivity", "emissivity", "powderConductivityRatio", "convection_W_m2K", "cooling_s"] as const;
const measurementFields = new Set(["width_um", "depth_um", "source", "processVector", "uncertainty_um", "independentHoldout"]);
const isFiniteNumber = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);
export const parseMeasurementPayload = (raw: string, nextInput: SimulationInput, strategy: string): ParsedMeasurementState => {
  const knownInput = { ...nextInput, strategy: nextInput.strategy || strategy };
  const text = raw.trim();
  if (!text) return {status:"empty", errors:[], mismatchedCount:0, missingProcessVectorCount:0, count:0, measurements: undefined};
  try {
    const parsed = JSON.parse(text);
    if (!Array.isArray(parsed)) {
      return {status:"invalid", errors:["Replicate JSON must be an array of replicate objects."], mismatchedCount:0, missingProcessVectorCount:0, count:0, measurements: undefined};
    }
    if (!parsed.length) {
      return {status:"invalid", errors:["Replicate JSON is empty."], mismatchedCount:0, missingProcessVectorCount:0, count:0, measurements: undefined};
    }
    const next: NonNullable<SimulationInput["measurements"]> = [];
    const errors: string[] = [];
    let mismatchedCount = 0;
    let missingProcessVectorCount = 0;
    for (const [index, rawEntry] of parsed.entries()) {
      if (!rawEntry || typeof rawEntry !== "object" || Array.isArray(rawEntry)) {
        errors.push(`Replicate #${index + 1}: expected object.`);
        continue;
      }
      const unknownFields = Object.keys(rawEntry).filter(key => !measurementFields.has(key));
      if (unknownFields.length) errors.push(`Replicate #${index + 1}: unknown fields: ${unknownFields.join(", ")}. Supported fields: ${[...measurementFields].join(", ")}.`);
      const width = rawEntry.width_um;
      const depth = rawEntry.depth_um;
      const source = typeof rawEntry.source === "string" ? rawEntry.source.trim() : "";
      if (!isFiniteNumber(width) || !isFiniteNumber(depth) || width <= 0 || depth <= 0) {
        errors.push(`Replicate #${index + 1}: width and depth must be positive finite numbers (µm).`);
      }
      if (!source) errors.push(`Replicate #${index + 1}: source is required.`);
      const entry: NonNullable<SimulationInput["measurements"]>[number] = { width_um: width, depth_um: depth, source };
      if (!Object.hasOwn(rawEntry, "processVector")) {
        missingProcessVectorCount += 1;
      } else {
        const vector = rawEntry.processVector;
        const isObject = vector !== null && typeof vector === "object" && !Array.isArray(vector);
        const hasExactKeys = isObject && Object.keys(vector).length === processVectorKeys.length
          && processVectorKeys.every(key => Object.hasOwn(vector, key));
        const validTypes = hasExactKeys && processVectorKeys.every(key => key === "material"
          ? typeof vector[key] === "string" && Boolean(vector[key].trim())
          : key === "strategy" ? ["meander", "unidirectional", "stripe", "island"].includes(vector[key])
          : isFiniteNumber(vector[key]));
        if (!validTypes) {
          errors.push(`Replicate #${index + 1}: processVector requires exactly ${processVectorKeys.join(", ")}. Use a nonempty material name, a supported strategy, and finite numbers for all other fields; omit processVector if measurement conditions are unknown.`);
        } else {
          entry.processVector = { ...vector };
          // Only detect differences in known controls. Material/optical defaults are
          // resolved by the worker; completeness alone never establishes a match.
          if (processVectorKeys.some(key => knownInput[key] !== undefined && vector[key] !== knownInput[key])) mismatchedCount += 1;
        }
      }
      if (rawEntry.uncertainty_um !== undefined) {
        if (!rawEntry.uncertainty_um || typeof rawEntry.uncertainty_um !== "object" || Array.isArray(rawEntry.uncertainty_um)) {
          errors.push(`Replicate #${index + 1}: uncertainty_um must be an object when provided.`);
        } else {
          const unknownUncertaintyFields = Object.keys(rawEntry.uncertainty_um).filter(key => key !== "width_um" && key !== "depth_um");
          if (unknownUncertaintyFields.length) errors.push(`Replicate #${index + 1}: uncertainty_um requires exactly width_um and depth_um; unknown fields: ${unknownUncertaintyFields.join(", ")}.`);
          const widthUnc = rawEntry.uncertainty_um.width_um;
          const depthUnc = rawEntry.uncertainty_um.depth_um;
          if (!isFiniteNumber(widthUnc) || !isFiniteNumber(depthUnc) || widthUnc < 0 || depthUnc < 0) {
            errors.push(`Replicate #${index + 1}: uncertainty_um.width_um and uncertainty_um.depth_um must be nonnegative finite numbers.`);
          } else {
            entry.uncertainty_um = { width_um: widthUnc, depth_um: depthUnc };
          }
        }
      }
      if (rawEntry.independentHoldout !== undefined && typeof rawEntry.independentHoldout !== "boolean") {
        errors.push(`Replicate #${index + 1}: independentHoldout must be boolean when provided.`);
      } else if (rawEntry.independentHoldout !== undefined) {
        entry.independentHoldout = Boolean(rawEntry.independentHoldout);
      }
      next.push(entry);
    }
    if (errors.length) return {status:"invalid", errors, mismatchedCount, missingProcessVectorCount, count: next.length, measurements: next};
    return {status:"valid", errors: [], mismatchedCount, missingProcessVectorCount, count: next.length, measurements: next};
  } catch {
    return {status:"invalid", errors:["Replicate JSON is not valid JSON."], mismatchedCount:0, missingProcessVectorCount:0, count:0, measurements: undefined};
  }
};

type ManualMeasurementDraft = { width: string; depth: string; source: string; specimen: string; uncertainty: string; holdout: string };
export function measurementSubmission(input: SimulationInput, raw: string, draft: ManualMeasurementDraft, strategy: string): SimulationInput["measurements"] {
  const state = parseMeasurementPayload(raw, input, input.strategy || strategy);
  const { width, depth, source, specimen, uncertainty, holdout } = draft;
  const validDimensions = Boolean(width && depth && source.trim()) && isFiniteNumber(Number(width))
    && isFiniteNumber(Number(depth)) && Number(width) > 0 && Number(depth) > 0;
  if (input.mode === "calibration" || state.status !== "empty") {
    if (state.status === "invalid") throw new Error(state.errors.join(" "));
    if (state.status === "valid") return state.measurements;
    if (!validDimensions) throw new Error("Calibration requires finite positive measured width and depth and a measurement source.");
  }
  if (state.status === "empty" && (width || depth || source)) {
    if (!validDimensions) throw new Error("Calibration requires finite positive measured width and depth and a measurement source.");
    if (uncertainty !== "" && (!Number.isFinite(Number(uncertainty)) || Number(uncertainty) < 0)) throw new Error("Measurement uncertainty must be nonnegative in µm.");
    return [{ width_um: Number(width), depth_um: Number(depth), source: source + (specimen ? ` · ${specimen}` : ""), ...(uncertainty !== "" ? { uncertainty_um: { width_um: Number(uncertainty), depth_um: Number(uncertainty) } } : {}), ...(holdout !== "unknown" ? { independentHoldout: holdout === "yes" } : {}) }];
  }
  return undefined;
}

const GPU_PILOT_STORAGE_KEY = "metalliksa.lpbf.gpu-pilot.job.v1";

type SavedGpuPilotStorage = Pick<Storage, 'getItem' | 'removeItem'>;

export function recoverMissingSavedGpuPilot(error: unknown, savedId: string,
  getStorage: () => SavedGpuPilotStorage = () => window.localStorage): boolean {
  const message = error instanceof Error ? error.message.trim() : '';
  if (!/^[a-f0-9]{32}$/.test(savedId) || (message !== 'Job not found' && message !== 'LPBF HTTP 404')) return false;
  try {
    const storage = getStorage();
    if (storage.getItem(GPU_PILOT_STORAGE_KEY) === savedId) storage.removeItem(GPU_PILOT_STORAGE_KEY);
  } catch { /* Keep the page usable when browser storage is unavailable. */ }
  return true;
}

const samePilotValue = (left: unknown, right: unknown): boolean => {
  if (Object.is(left, right)) return true;
  if (!left || !right || typeof left !== "object" || typeof right !== "object") return false;
  if (Array.isArray(left) || Array.isArray(right)) {
    return Array.isArray(left) && Array.isArray(right) && left.length === right.length
      && left.every((value, index) => samePilotValue(value, right[index]));
  }
  const a = left as Record<string, unknown>;
  const b = right as Record<string, unknown>;
  const keys = Object.keys(a).sort();
  const otherKeys = Object.keys(b).sort();
  return keys.length === otherKeys.length
    && keys.every((key, index) => key === otherKeys[index] && samePilotValue(a[key], b[key]));
};

const executedPilotFields: Array<[string, string]> = [
  ["material", "Material"], ["backend", "CUDA device"], ["power_W", "Laser power · W"],
  ["speed_mm_s", "Scan speed · mm/s"], ["beamDiameter_um", "Beam diameter · µm"],
  ["preheat_C", "Preheat · °C"], ["hatch_um", "Hatch spacing · µm"],
  ["layer_um", "Layer thickness · µm"], ["strategy", "Scan strategy"],
  ["mesh_um", "Mesh spacing · µm"], ["maxDt_s", "Maximum timestep · s"],
  ["tracks", "Tracks"], ["layers", "Layers"], ["stripeWidth_um", "Stripe width · µm"],
  ["islandSize_um", "Island size · µm"], ["trackLength_um", "Track length · µm"],
  ["dwell_s", "Track dwell · s"], ["cooling_s", "Final cooling · s"],
  ["scanAngle_deg", "Scan angle · °"], ["layerRotation_deg", "Layer rotation · °"],
  ["packingFraction", "Powder packing fraction"],
  ["powderConductivityRatio", "Powder conductivity ratio"],
  ["convection_W_m2K", "Convection · W/m²K"], ["timeout_s", "Worker timeout · s"],
  ["absorptivity", "Absorptivity"], ["emissivity", "Emissivity"], ["properties", "Custom material table"],
  ["barePlateGeometry", "Bare-plate geometry"], ["sourcePenetration_um", "Source penetration · µm"],
];

export function GpuPilotExecutedInputSummary({saved, current, bound}: {
  saved: GpuPilotInput; current?: GpuPilotInput; bound: boolean;
}) {
  const savedValues = saved as unknown as Record<string, unknown>;
  const currentValues = current as unknown as Record<string, unknown> | undefined;
  const differences = currentValues ? Object.keys(currentValues).filter(key =>
    !Object.hasOwn(savedValues, key) || !samePilotValue(savedValues[key], currentValues[key])) : [];
  if (currentValues && Object.hasOwn(savedValues, "properties") && !Object.hasOwn(currentValues, "properties")) {
    differences.push("properties");
  }
  const omittedFields = currentValues
    ? Object.keys(savedValues).filter(key => !Object.hasOwn(currentValues, key)) : [];
  const warning = !bound || currentValues === undefined || differences.length > 0 || omittedFields.length > 0;
  const formatValue = (key: string, value: unknown) => {
    if (!Object.hasOwn(savedValues, key)) return "Not supplied in saved request";
    if (key === "properties") return "User-supplied table included";
    if (value === null) return "Not set (null)";
    return typeof value === "object" ? "Supplied" : String(value);
  };
  return <section aria-label="Saved CUDA pilot inputs" className="rounded-lg border border-slate-700/60 bg-slate-950/40 p-3">
    <h5 className="font-medium">Inputs used by this saved CUDA job</h5>
    <p className="mt-1 text-xs text-slate-400">Read from the completed job result; these values stay attached to its metrics.</p>
    <dl className="mt-3 grid gap-x-4 gap-y-2 sm:grid-cols-2 lg:grid-cols-3">
      {executedPilotFields.map(([key, label]) => <div key={key}>
        <dt className="text-xs text-slate-400">{label}</dt>
        <dd className="mt-0.5 break-all text-sm tabular-nums">{formatValue(key, savedValues[key])}</dd>
      </div>)}
    </dl>
    <p role="status" aria-label="Saved CUDA input comparison" className={`mt-3 text-xs ${warning ? "text-amber-200" : "text-emerald-200"}`}>
      {!bound ? "This saved run has no exact request binding, so current controls cannot be verified against it."
        : current === undefined ? "Current controls cannot form a valid request; the displayed result remains from the saved run."
          : differences.length ? `Current submitted fields differ from this saved result: ${differences.join(", ")}. The displayed result still belongs to the saved run.`
            : omittedFields.length ? "Current submitted fields match the saved values where both are explicit. Omitted/defaulted fields are not compared, so full request identity is unverified."
              : "Current explicit fields match the saved values. Full request identity is not asserted."}
    </p>
  </section>;
}

export function GpuPilotArchiveAction({job}: {job: GpuPilotJob}) {
  const result = job.result;
  if (job.status !== "completed" || !result?.gpuRunContract || !result.gpuFieldArtifacts) return null;
  return <div className="mt-6" aria-label="Archive completed CUDA pilot" data-gpu-job-id={job.id}>
    <LpbfJobArchiver jobId={job.id} />
  </div>;
}

export function gpuPilotEngineLabel(result: GpuPilotResult): string {
  const contract = result.gpuRunContract;
  const capture = contract && isRecord(contract.capture) ? contract.capture : undefined;
  const serialized = contract && isRecord(contract.serializedInputs) ? contract.serializedInputs : undefined;
  return validatedGpuPilotEngineLabel(capture && serialized ? {
    schemaVersion: 1,
    runKind: 'gpu-thermal-pilot',
    contractStatus: capture.contractStatus,
    inputJson: serialized.requestJson,
    materialJson: serialized.materialJson,
  } : undefined, result);
}

export function gpuPilotRuntimeLabel(result: GpuPilotResult): string {
  const engine = gpuPilotEngineLabel(result);
  const evidence = result.provenance.deviceEvidence;
  if (engine === 'NVIDIA Warp candidate · v2' && 'engineId' in evidence
      && evidence.engineId === 'warp' && typeof evidence.warp === 'string'
      && typeof evidence.warpCudaToolkitVersion === 'string' && typeof evidence.cudaDriverVersion === 'string') {
    return `Warp ${evidence.warp} · CUDA toolkit ${evidence.warpCudaToolkitVersion} · CUDA driver ${evidence.cudaDriverVersion}`;
  }
  if (engine === 'PyTorch CUDA · v1' && 'cudaRuntime' in evidence
      && typeof evidence.torch === 'string' && typeof evidence.cudaRuntime === 'string') {
    return `PyTorch ${evidence.torch} · CUDA runtime ${evidence.cudaRuntime}`;
  }
  return 'GPU runtime evidence unverified';
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export interface GpuRuntimeDevice {
  ordinal: number; device: `cuda:${number}`; name: string;
  computeCapability: [number, number]; memoryBytes: number;
}

export function gpuDevicesForEngine(caps: unknown, engine: 'torch' | 'warp'): GpuRuntimeDevice[] {
  if (typeof caps !== 'object' || caps === null || Array.isArray(caps)) return [];
  const inventories = (caps as {gpuDevices?: unknown}).gpuDevices;
  if (typeof inventories !== 'object' || inventories === null || Array.isArray(inventories)) return [];
  const runtime = (inventories as Record<string, unknown>)[engine];
  if (typeof runtime !== 'object' || runtime === null || Array.isArray(runtime)) return [];
  const runtimeRecord = runtime as {runtimeAvailable?: unknown; devices?: unknown};
  if (runtimeRecord.runtimeAvailable !== true) return [];
  const devices = runtimeRecord.devices;
  if (!Array.isArray(devices)) return [];
  return devices.filter((value): value is GpuRuntimeDevice => {
    if (typeof value !== 'object' || value === null || Array.isArray(value)) return false;
    const item = value as Record<string, unknown>;
    return Number.isSafeInteger(item.ordinal) && (item.ordinal as number) >= 0
      && item.device === `cuda:${item.ordinal}` && typeof item.name === 'string' && !!item.name.trim()
      && Array.isArray(item.computeCapability) && item.computeCapability.length === 2
      && item.computeCapability.every(part => Number.isSafeInteger(part) && (part as number) >= 0)
      && Number.isSafeInteger(item.memoryBytes) && (item.memoryBytes as number) > 0;
  }).sort((a, b) => a.ordinal - b.ordinal);
}

export function sameGpuDeviceIdentity(selected: GpuRuntimeDevice | undefined,
  current: GpuRuntimeDevice | undefined): boolean {
  return !!selected && !!current && selected.ordinal === current.ordinal
    && selected.device === current.device && selected.name === current.name
    && selected.memoryBytes === current.memoryBytes
    && selected.computeCapability[0] === current.computeCapability[0]
    && selected.computeCapability[1] === current.computeCapability[1];
}

function GpuThermalPilotPanel({input, settings, material, properties, strategy, caps, blocked}: {
  input: SimulationInput; settings: Partial<SimulationInput>; material: string;
  properties: string; strategy: SimulationInput["strategy"];
  caps?: SimulationCapabilities; blocked: boolean;
}) {
  const [device, setDevice] = useState("");
  const [deviceCaps, setDeviceCaps] = useState<SimulationCapabilities | undefined>(caps);
  // Remembered per viewer (a select convenience); a restored saved pilot job still shows its executed engine.
  const [engine, setEngine] = useState<'torch' | 'warp'>(() => readChoice(GPU_PILOT_ENGINE_PREFERENCE_KEY, GPU_PILOT_ENGINES, 'torch'));
  const [job, setJob] = useState<GpuPilotJob>();
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [refreshingDevices, setRefreshingDevices] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const active = job?.status === "queued" || job?.status === "running";
  const result = job?.status === "completed" ? job.result : undefined;
  useEffect(() => setDeviceCaps(caps), [caps]);
  const devices = gpuDevicesForEngine(deviceCaps, engine);
  const unavailableCapability = engine === 'warp' ? warpCapabilityFromInventory(deviceCaps) : null;
  const selectedDevice = devices.find(candidate => candidate.device === device);
  useEffect(() => {
    if (devices.length && !devices.some(candidate => candidate.device === device)) setDevice(devices[0].device);
    else if (!devices.length && device) setDevice("");
  }, [engine, deviceCaps]);
  const refreshDevices = async () => {
    if (refreshingDevices || submitting) return;
    setRefreshingDevices(true);
    try { setDeviceCaps(await simulationApi.capabilities()); setError(""); }
    catch (e) { setError(e instanceof Error ? e.message : "CUDA runtime inventory refresh failed"); }
    finally { setRefreshingDevices(false); }
  };
  useEffect(() => {
    let live = true;
    let saved = "";
    try { saved = localStorage.getItem(GPU_PILOT_STORAGE_KEY) || ""; } catch { /* Storage may be disabled. */ }
    if (/^[a-f0-9]{32}$/.test(saved)) {
      gpuPilotApi.get(saved).then(next => { if (live) { setJob(next); setDevice(next.requestSummary.backend);
        setEngine(next.requestSummary.executionEngine === 'warp' ? 'warp' : 'torch'); } })
        .catch(e => {
          if (!live) return;
          if (recoverMissingSavedGpuPilot(e, saved)) { setError(""); return; }
          setError(`Saved CUDA pilot unavailable: ${e instanceof Error ? e.message : "Worker connection failed"}`);
        });
    }
    return () => { live = false; };
  }, []);
  // Paused while the module is hidden; becoming visible again polls at once to catch up.
  useVisiblePolling(async (isLive) => {
    if (!job) return null;
    try {
      const next = await gpuPilotApi.get(job.id);
      if (!isLive()) return null;
      setJob(next); setError("");
      return next.status === "queued" || next.status === "running" ? 1500 : null;
    } catch (e) {
      if (!isLive()) return null;
      setError(e instanceof Error ? e.message : "CUDA pilot polling failed");
      return 3000;
    }
  }, !!job && active, `${job?.id}:${job?.status}`);
  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (submitting || active) return;
    const submittedEngine = engine;
    const submittedDevice = device;
    const selectedAtSubmit = devices.find(candidate => candidate.device === submittedDevice);
    setSubmitting(true); setError("");
    try {
      if (!selectedAtSubmit) throw new Error("Select a CUDA device from the current runtime list.");
      const freshCaps = await simulationApi.capabilities();
      setDeviceCaps(freshCaps);
      const freshDevices = gpuDevicesForEngine(freshCaps, submittedEngine);
      const freshSelection = freshDevices.find(candidate => candidate.device === submittedDevice);
      if (!sameGpuDeviceIdentity(selectedAtSubmit, freshSelection)) {
        throw new Error(`${submittedDevice} changed or is no longer available in the ${submittedEngine === 'warp' ? 'Warp' : 'PyTorch CUDA'} runtime. Refresh the list, select a device, and retry. No CPU fallback is used.`);
      }
      const pilot = buildGpuPilotInput(input, settings, submittedDevice as `cuda:${number}`,
        material, strategy, properties.trim() ? JSON.parse(properties) : undefined, submittedEngine);
      const next = await gpuPilotApi.submit(pilot);
      setJob(next);
      try { localStorage.setItem(GPU_PILOT_STORAGE_KEY, next.id); } catch { /* Live job remains visible. */ }
    } catch (e) { setError(e instanceof Error ? e.message : "CUDA pilot submission failed"); }
    finally { setSubmitting(false); }
  };
  const cancel = async () => {
    if (!job || !active || cancelling) return;
    setCancelling(true);
    try { setJob(await gpuPilotApi.cancel(job.id)); }
    catch (e) { setError(e instanceof Error ? e.message : "CUDA pilot cancellation failed"); }
    finally { setCancelling(false); }
  };
  const parity = result?.gpuPilot;
  const evidence = result?.provenance.deviceEvidence;
  const comparisons = parity?.comparisons;
  let currentRequest: GpuPilotInput | undefined;
  try {
    currentRequest = buildGpuPilotInput(input, settings, device as `cuda:${number}`,
      material, strategy, properties.trim() ? JSON.parse(properties) : undefined, engine);
  } catch { /* Invalid current controls cannot match an archived run. */ }
  return <section className={surface} aria-label="CUDA thermal parity pilot">
    <h4 className="font-medium">CUDA thermal parity pilot</h4>
    <p className="mt-2 text-sm text-slate-300">Explicit CUDA device · one powder-layer track and one layer · standard enthalpy conduction · no convergence study or measurements. Current mesh, time and process values are used. Device availability is checked when submitted.</p>
    <p className="mt-2 text-xs text-amber-200">Numerical CPU/GPU parity only. A completed bound GPU result can be imported with Save to Archive below after selecting a source revision; field bytes and numerical evidence are rechecked during import and bundle restore. This remains unvalidated parity evidence. Experimental validation and qualification are unavailable. CPU alternative: Reference enthalpy FV above.</p>
    <form onSubmit={submit} className="mt-4 flex flex-wrap items-end gap-3">
      <label className="text-sm">GPU engine<select aria-label="GPU engine" className={inputClass} value={engine}
        disabled={blocked||submitting||active} onChange={e=>{const next = e.target.value === 'warp' ? 'warp' : 'torch'; setEngine(next); writeChoice(GPU_PILOT_ENGINE_PREFERENCE_KEY, next);}}>
        <option value="torch">PyTorch CUDA · v1</option><option value="warp">NVIDIA Warp candidate · v2</option>
      </select></label>
      <label className="text-sm">CUDA device<select aria-label="CUDA device" className={inputClass} value={device}
        disabled={blocked||submitting||active||refreshingDevices} onChange={e=>setDevice(e.target.value)} aria-describedby="cuda-pilot-help" required>
        {!devices.length && <option value="">No {engine === 'warp' ? 'Warp' : 'PyTorch CUDA'} devices available</option>}
        {devices.map(candidate=><option key={candidate.device} value={candidate.device}>
          {candidate.device} · {candidate.name} · compute {candidate.computeCapability.join('.')} · {(candidate.memoryBytes / 1024 ** 3).toFixed(1)} GiB
        </option>)}
      </select></label>
      <button type="button" onClick={refreshDevices} disabled={blocked||submitting||refreshingDevices}
        className="rounded-lg border border-slate-500 px-3 py-2.5 text-sm disabled:opacity-40">
        {refreshingDevices ? "Refreshing…" : "Refresh devices"}
      </button>
      <button type="submit" disabled={blocked||submitting||active||!selectedDevice} className="rounded-lg border border-sky-400/50 bg-sky-950/50 px-4 py-2.5 text-sm disabled:opacity-40">{submitting?"Checking device…":engine === 'warp' ? "Run Warp parity pilot" : "Run CUDA parity pilot"}</button>
      {active&&<button type="button" disabled={cancelling} onClick={cancel} className="rounded-lg border border-slate-500 px-4 py-2.5 text-sm disabled:opacity-40">{cancelling?"Cancelling…":"Cancel CUDA pilot"}</button>}
    </form>
    {unavailableCapability && <GpuCapabilityNotice capability={unavailableCapability} />}
    <p id="cuda-pilot-help" className="mt-2 text-xs text-slate-400">{selectedDevice
      ? `Listed by the ${engine === 'warp' ? 'Warp' : 'PyTorch CUDA'} runtime · ordinal ${selectedDevice.ordinal} · ${selectedDevice.memoryBytes.toLocaleString(DISPLAY_LOCALE)} bytes. Device and engine availability are refreshed before submission.`
      : `No ${engine === 'warp' ? 'Warp' : 'PyTorch CUDA'} runtime device is currently available. Refresh the device list or select another engine.`} The worker rechecks the exact CUDA ordinal during submission. No CPU fallback is used.</p>
    {error&&<p role="alert" className="mt-3 rounded-lg border border-red-400/40 p-3 text-sm text-red-200">{error}</p>}
    {job&&<p role="status" className="mt-3 text-sm">CUDA job {job.id} · {job.status}{job.cacheHit?" · cached":""}</p>}
    {job?.error&&<p role="alert" className="mt-2 text-sm text-red-200">{job.error}</p>}
    {result&&<div className="mt-4 space-y-3 text-sm">
      <GpuPilotExecutedInputSummary saved={result.settings} current={currentRequest}
        bound={Boolean(result.gpuRunContract)}/>
      <p>CPU/GPU parity: <strong>{parity?.status}</strong> · {parity?.scope} · experimental validation: unavailable.</p>
      <p>Executed engine: {gpuPilotEngineLabel(result)} · device: {evidence?.name} ({evidence?.selected}) · thermal evolution {result.solver.thermalEvolutionDevice} · source integration {result.solver.sourceIntegrationDevice} · {result.solver.dtype}.</p>
      <p>Model: {result.solver.modelId} · material {result.material.name} ({result.material.materialId}) · revision <span className="font-mono break-all">{result.material.materialRevisionSha256}</span>.</p>
      <ExecutedMaterialProvenance material={result.material} />
      <p>GPU W/D/L: {fmt(result.metrics.width_um)} / {fmt(result.metrics.depth_um)} / {fmt(result.metrics.length_um)} µm · peak {fmt(result.metrics.peakTemperature_K)} K · energy closure {fmt(result.energyBalance.relativeError*100)}%.</p>
      <p>CPU reference: {parity?.cpu.solver.id} / {parity?.cpu.coreContract.actualBackend}. Final 3D field L2 {fmt(comparisons?.finalTemperatureField.relativeRiseL2)}; max {fmt(comparisons?.finalTemperatureField.relativeRiseMax)}. Frozen field targets ≤ {fmt(parity?.targets.fieldRiseL2RelativeMax)} / {fmt(parity?.targets.fieldRiseMaxRelativeMax)}.</p>
      <details className="border-t border-slate-700/50 pt-2"><summary className="cursor-pointer">CPU/GPU comparison and device evidence</summary>
        <div className="mt-3 overflow-x-auto"><table className="w-full min-w-[520px] text-left text-xs"><caption className="sr-only">CUDA pilot numerical parity checks</caption><thead><tr><th scope="col">Quantity</th><th scope="col">CPU</th><th scope="col">GPU</th><th scope="col">Difference</th><th scope="col">Status</th></tr></thead><tbody>{Object.entries(comparisons||{}).map(([key,c])=><tr key={key} className="border-t border-slate-700/40"><th scope="row" className="py-2 pr-2 font-normal">{key}</th><td>{fmt(c.cpu)}</td><td>{fmt(c.gpu)}</td><td>{fmt(c.relativeDifference ?? c.absoluteDifference_um ?? c.relativeRiseL2)}</td><td>{c.status}</td></tr>)}</tbody></table></div>
        <p className="mt-3 text-xs text-slate-400">{gpuPilotRuntimeLabel(result)} · compute capability {evidence?.computeCapability.join(".")} · synchronized after solve: {evidence?.synchronizedAfterSolve?"yes":"no"}.</p>
        <p className="mt-2 text-xs text-slate-400">Input {result.provenance.inputHash} · implementation {result.provenance.implementationHash}.</p>
      </details>
    </div>}
    {job && <GpuPilotArchiveAction job={job} />}
  </section>;
}

export function GpuPilotControls(props: React.ComponentProps<typeof GpuThermalPilotPanel>) {
  if (!gpuDevicesForEngine(props.caps, 'torch').length && !gpuDevicesForEngine(props.caps, 'warp').length) return null;
  // Shown open, right after the main run controls, whenever the worker reports a CUDA or Warp device.
  return <section aria-label="GPU (CUDA)" className="space-y-4 rounded-xl border border-slate-700/60 p-4">
    <h4 className="font-medium">GPU (CUDA)</h4>
    {IS_STATIC_DEMO ? <DemoUnavailable what="CUDA thermal parity pilot" /> : <GpuThermalPilotPanel {...props}/>}
    {IS_STATIC_DEMO ? <DemoUnavailable what="Bare-plate IN625 comparison" /> : <In625BareplatePanel />}
  </section>;
}

export function LpbfEngineeringSimulation({input:providedInput}:{input:SimulationInput}) {
  const sharedSpecimen=useMaterialSpecimenStore(s=>s.activeSpecimen);
  const process=sharedSpecimen.lpbf;
  const input:SimulationInput={...providedInput,material:canonicalLpbfMaterialName(sharedSpecimen.name),power_W:process.laserPower_W,speed_mm_s:process.scanSpeed_mms,beamDiameter_um:process.beamDiameter_um,preheat_C:process.preheatTemp_C,layer_um:process.layer_um,hatch_um:process.hatch_um};
  const updateProcess = useMaterialSpecimenStore(s=>s.updateLpbfProcess);
  const sharedStrategy = useMaterialSpecimenStore(s=>s.activeSpecimen.lpbf.scanStrategy);
  const [settings,setSettings] = useEngineeringField("settings");
  const [mode,setMode] = useEngineeringField("mode");
  // Static demo: only the recorded Quick Screening mode has a snapshot, so the mode is forced to it (compile-time constant).
  useEffect(()=>{ if (IS_STATIC_DEMO && mode!=="screening") setMode("screening"); },[mode,setMode]);
  const [caps,setCaps] = useState<SimulationCapabilities>();
  const [job,setJob] = useEngineeringField("job");
  const [estimate,setEstimate] = useState<ResourceEstimate>();
  const [estimateError,setEstimateError] = useState("");
  const [error,setError] = useEngineeringField("error");
  const [busy,setBusy] = useEngineeringField("busy");
  const [repeatExecution,setRepeatExecution] = useState(false);
  const [cancelling,setCancelling] = useState(false);
  const [elapsed,setElapsed] = useState(0);
  const [fieldTime,setFieldTime] = useState<number>();
  const initialProcess = useRef(input);
  const [material,setMaterial] = useEngineeringField("material");
  const [properties,setProperties] = useEngineeringField("properties");
  const [measurements,setMeasurements] = useEngineeringField("measurements");
  const [specimen,setSpecimen]=useEngineeringField("specimen"); const [uncertainty,setUncertainty]=useEngineeringField("uncertainty"); const [holdout,setHoldout]=useEngineeringField("holdout");
  const [width,setWidth] = useEngineeringField("width"); const [depth,setDepth] = useEngineeringField("depth"); const [source,setSource] = useEngineeringField("source");
  const signature = engineeringSignature(input,{settings,mode,material,properties,measurements,width,depth,source,specimen,uncertainty,holdout},sharedStrategy);
  const submittedSignature = useLpbfEngineeringStore(s=>s.submittedSignature);
  const canRepeatCurrentInput = job?.status === "completed" && submittedSignature === signature;
  const cancelledJob = useRef("");
  const [resultSignature] = useEngineeringField("resultSignature");
  const active = job?.status === "queued" || job?.status === "running";
  const resultStale = isResultStale(resultSignature, signature);
  useEffect(()=>{setRepeatExecution(false);},[signature]);
  const elapsedStart=useRef(0);
  useEffect(()=>{if(!active)return;setElapsed(0);elapsedStart.current=Date.now();},[active,job?.id]);
  useVisibleInterval(()=>setElapsed((Date.now()-elapsedStart.current)/1000),active?1000:null);
  const cancel=async()=>{if(!job || cancelling)return;setCancelling(true);try{const next=await simulationApi.cancel(job.id);if(next.status!=="queued"&&next.status!=="running")cancelledJob.current=job.id;setJob(next);}catch(e){setError(e instanceof Error?e.message:"Cancellation failed");}finally{setCancelling(false);}};
  const materialEvidence=caps?.materials.find(m=>m.name===(material||input.material));
  const missingMaterial=(materialEvidence?.available===false||/Unknown alloy|thermophysical data missing/i.test(estimateError))&&!properties.trim();
  const invalidOptics=(["absorptivity","emissivity"] as const).some(k=>settings[k]!==undefined&&(!Number.isFinite(settings[k])||Number(settings[k])<(k==="absorptivity"?.000001:0)||Number(settings[k])>1));
  const invalidControls=invalidOptics||controls.some(([key,,min,max])=>typeof settings[key]!=="number"||!Number.isFinite(settings[key])||Number(settings[key])<min||Number(settings[key])>max||((key==="tracks"||key==="layers")&&!Number.isInteger(settings[key])));
  const invalidProcess=([[input.power_W,10,1500],[input.speed_mm_s,10,10000],[input.beamDiameter_um,20,500],[input.hatch_um,10,1000],[input.layer_um,10,150],[input.preheat_C,0,1200]]).some(([v,min,max])=>!Number.isFinite(v)||v<min||v>max);
  const r = job?.status === "completed" ? job.result : undefined;
  const resolvedStrategy = settings.strategy ?? (sharedStrategy==="meander-67"?"meander":sharedStrategy);
  const parsedMeasurements = parseMeasurementPayload(measurements, {...input,...settings,material:material||input.material,strategy:resolvedStrategy}, resolvedStrategy);
  const isManualCalibrationProvided = width.trim() || depth.trim() || source.trim();
  const hasManualCalibration = Boolean(width && depth && source.trim());
  const manualCalibrationValuesPositive = hasManualCalibration && isFiniteNumber(Number(width)) && isFiniteNumber(Number(depth)) && Number(width) > 0 && Number(depth) > 0;
  const calibrationReadinessLabel = (() => {
    if (mode !== "calibration") return "Calibration mode is not selected.";
    if (parsedMeasurements.status === "invalid") return `Invalid replicate JSON: ${parsedMeasurements.errors.join(" ")}`;
    if (parsedMeasurements.status === "valid") {
      const mismatchText = parsedMeasurements.mismatchedCount
        ? `${parsedMeasurements.mismatchedCount} replicates differ from known current controls; the worker rejects mismatched conditions. `
        : "";
      const missingText = parsedMeasurements.missingProcessVectorCount
        ? `${parsedMeasurements.missingProcessVectorCount} replicates have unknown conditions; calibration factor is withheld. `
        : "";
      const suffix = `${parsedMeasurements.count} replicate${parsedMeasurements.count === 1 ? "" : "s"} supplied`;
      if (parsedMeasurements.mismatchedCount > 0 || parsedMeasurements.missingProcessVectorCount > 0) {
        return `${suffix}; ${mismatchText}${missingText}Exact process matching is checked by the worker.`;
      }
      return `${suffix}; complete user-supplied conditions; exact process matching is pending worker checks.`;
    }
    if (isManualCalibrationProvided) {
      return manualCalibrationValuesPositive ? "Manual dimensions have no measurement conditions; comparison is available with unverified process matching and calibration factor withheld." : "Calibration mode needs finite positive width/depth and source.";
    }
    return "Calibration mode needs valid JSON replicates or manual width/depth/source.";
  })();
  const calibrationReadinessStatus: ReadinessStatus = (() => {
    if (mode !== "calibration") return "pass";
    if (parsedMeasurements.status === "invalid") return "fail";
    if (isManualCalibrationProvided && parsedMeasurements.status === "empty") return "warn";
    if (parsedMeasurements.status === "valid") {
      if (parsedMeasurements.mismatchedCount > 0 || parsedMeasurements.missingProcessVectorCount > 0) return "warn";
      return "warn";
    }
    return "warn";
  })();
  const readinessChecks: ReadinessItem[] = [
    {status: invalidProcess ? "fail" : "pass", label: "Shared process ranges", details: invalidProcess ? "Shared P, v, beam, hatch, layer, or preheat is outside allowed bounds." : "Shared process parameters are within expected limits."},
    {status: invalidControls ? "warn" : "pass", label: "Advanced control ranges", details: invalidControls ? "One or more advanced controls are out of valid bounds." : "Advanced control block is currently valid."},
    { ...materialTableAvailabilityReadiness(materialEvidence?.available, Boolean(properties.trim()), missingMaterial), label: "Material table availability" },
    { ...materialSourceEvidenceReadiness(properties.trim() ? "user-supplied-unverified" : materialEvidence?.quality), label: "Material source and uncertainty evidence" },
    {status: mode === "high-fidelity" && !caps?.freeSurfaceSolver ? "warn" : "pass", label: "Mode compatibility", details: mode === "high-fidelity" ? caps?.freeSurfaceSolver ? "High-fidelity free-surface solver appears available." : "Free-surface solver is unavailable; this mode will run screening fallback." : "Selected mode is compatible with current solver stack."},
    {status: estimateError ? "warn" : !estimate ? "pending" : estimate.exceedsCellBudget || estimate.exceedsStepBudget ? "warn" : "pass", label: "Resource estimate", details: estimateError ? estimateError : !estimate ? "Resource estimate is waiting for worker capabilities and input snapshot." : estimate.exceedsCellBudget ? "Estimated mesh size exceeds budget; reduce mesh resolution or shorten process history." : estimate.exceedsStepBudget ? "Estimated step count exceeds budget; increase maxDt or simplify build schedule." : "Resource estimate is within budget."},
    {status: caps ? "pass" : "pending", label: "Worker availability", details: caps ? `OpenFOAM thermal: ${caps.openfoamThermal ? "available" : "unavailable"}; free-surface: ${caps.freeSurfaceSolver ? "available" : "unavailable"}.` : "Worker capabilities are still loading."},
    {status: mode !== "calibration" && measurements.trim() ? parsedMeasurements.status === "invalid" ? "fail" : "pass" : calibrationReadinessStatus, label: "Calibration inputs", details: calibrationReadinessLabel},
    {status: r && r.material.name === (material || input.material) && Array.isArray(r.material.table) && r.material.table.length > 0 ? "pass" : r ? "warn" : "pending", label: "Executed material identity", details: r ? r.material.name === (material || input.material) ? "Result identity and table match current material selection; source quality and uncertainty are assessed separately above." : "Result material does not match current material selection." : "No completed run to compare yet."},
  ];
  const payload = (selectedMode:SimulationMode):SimulationInput => ({...input,...settings,mode:selectedMode,
    material:material || input.material, strategy:resolvedStrategy,
    ...(properties.trim() ? {properties:JSON.parse(properties)} : {})});
  useEffect(()=>{
    let live=true;
    simulationApi.capabilities().then(c=>{if(live)setCaps(c);}).catch(e=>{if(live)setError(e.message);});
    return ()=>{live=false;};
  },[]);
  useEffect(()=>{
    let live=true;setEstimate(undefined);setEstimateError("");
    const timer=setTimeout(()=>{
      try {simulationApi.estimate(payload("standard")).then(e=>{if(live)setEstimate(e);}).catch(e=>{if(live)setEstimateError(e.message);});}
      catch {if(live)setEstimateError("Material JSON is invalid");}
    },750);
    return()=>{live=false;clearTimeout(timer);};
  },[JSON.stringify(input),JSON.stringify(settings),material,properties,sharedStrategy]);
  const submit=async()=>{
    setBusy(true);setError("");
    try {
      for(const [key,,min,max] of controls){const v=settings[key];if(typeof v!=="number"||!Number.isFinite(v)||v<min||v>max)throw new Error(`${key} must be in [${min}, ${max}]`);}
      if(invalidProcess||invalidControls)throw new Error("Correct the highlighted parameter ranges before running.");
      const p=payload(mode);
      p.measurements=measurementSubmission(p,measurements,{width,depth,source,specimen,uncertainty,holdout},resolvedStrategy);
      const next=await simulationApi.submit(p,repeatExecution&&canRepeatCurrentInput?{executionScope:'repeat'}:undefined);useLpbfEngineeringStore.setState({job:next,submittedSignature:signature,submittedInput:p,resultSignature:resultSignatureOnSubmit(next.status,signature)});setFieldTime(undefined);setRepeatExecution(false);resumeEngineeringJob();
    }catch(e){setError(e instanceof Error?e.message:"Submission failed");}finally{setBusy(false);}
  };
  const download=()=>{if(!r)return;const url=URL.createObjectURL(new Blob([JSON.stringify(r,null,2)],{type:"application/json"}));const a=document.createElement("a");a.href=url;a.download=`lpbf-${job.id}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};

  return <section aria-label="LPBF engineering simulation" className="min-w-0 rounded-3xl border border-slate-700/60 bg-[#090f1b] p-4 md:p-7 space-y-6 text-slate-200 font-sans [&_button]:transition-colors [&_button]:duration-150 [&_button:focus-visible]:outline-2 [&_button:focus-visible]:outline-sky-300 [&_button:focus-visible]:outline-offset-4 [&_summary:focus-visible]:outline-2 [&_summary:focus-visible]:outline-sky-300 [&_summary]:rounded-md [&_summary]:py-2 [&_select:focus-visible]:outline-2 [&_select:focus-visible]:outline-sky-300 motion-reduce:[&_*]:transition-none">
    <header className="flex flex-wrap items-center justify-between gap-4"><div><p className="text-[10px] tracking-[.3em] uppercase text-slate-400">Metalliksa / Advanced manufacturing</p><h3 className="text-3xl font-medium tracking-tight mt-2">LPBF <span className="text-slate-400">/</span> Melt Pool</h3><p className="mt-2 text-sm text-slate-400">Thermal response, process screening and traceable evidence.</p></div><Badge tone={caps?.openfoamThermal?"active":"neutral"}>{caps?caps.openfoamThermal?"OpenFOAM thermal worker available":"Reference worker · OpenFOAM unavailable":"Connecting to worker…"}</Badge></header>
    {IS_STATIC_DEMO ? <DemoUnavailable what="Ti-6Al-4V evaporative surface model" /> : <Ti64EvaporativePanel material={material||input.material} process={{power_W:input.power_W,speed_mm_s:input.speed_mm_s,beamDiameter_um:input.beamDiameter_um,preheat_C:input.preheat_C}} />}
    <ResultHeader job={job} material={material||input.material} availability={caps?`${caps.openfoamVersion||"Unavailable"} · free-surface ${caps.freeSurfaceSolver?"reported available":"unavailable"}`:"Checking…"} stale={resultStale} elapsed={elapsed} cancel={cancel} cancelling={cancelling}/>
    {active&&submittedSignature!==signature&&<p role="status" className="text-sm text-amber-200">Inputs changed — the running job uses submitted settings. Local changes apply to the next run.</p>}
    <CancelledRunNotice status={job?.status} />
    {(error||job?.error)&&<p role="alert" className="rounded-xl border border-red-400/30 bg-red-400/5 p-4 text-sm text-red-200 whitespace-pre-wrap">{error||job?.error}</p>}
    {job&&<details className="border-t border-slate-700 pt-3"><summary className="cursor-pointer">Worker log · {job.id}</summary><pre className="max-h-48 overflow-auto whitespace-pre-wrap text-xs text-slate-400 mt-3">{job.log||job.status}</pre></details>}
    {(!caps?.freeSurfaceSolver)&&<p role="status" className="rounded-xl border border-amber-400/20 bg-amber-400/5 px-5 py-3 text-sm leading-6 text-amber-200">{mode==="high-fidelity"?"Free-surface LPBF CFD is unavailable. Result is Screening only.":"Free-surface LPBF CFD is unavailable. Thermal runs do not resolve fluid flow, recoil pressure or a keyhole cavity."}</p>}
    <section aria-label="Run readiness checklist" className="space-y-2 rounded-xl border border-slate-700/50 bg-slate-900/30 p-4">
      <h4 className="text-sm font-medium">Run readiness checklist</h4>
      <ul className="space-y-2 text-xs">
        {readinessChecks.map((item) => (
          <li key={item.label} className={`rounded-lg border px-3 py-2 ${readinessClasses[item.status]}`}>
            <span className="mr-2 font-semibold" aria-hidden>{readinessGlyph[item.status]}</span>
            <span className="font-medium">{item.label}:</span> {item.details}
          </li>
        ))}
      </ul>
    </section>
    <section aria-label="Simulation mode" className="space-y-4"><div className="flex items-center justify-between"><h4 className="text-sm font-medium">Simulation mode</h4><span className="text-xs text-slate-400">Scope before compute</span></div><div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4" role="group" aria-label="Simulation modes">{modes.map((m,i)=><button key={m.id} {...(IS_STATIC_DEMO&&m.id!=="screening"?DEMO_UNAVAILABLE_LOCK:{})} aria-pressed={mode===m.id} onClick={()=>setMode(m.id)} className={`rounded-xl border p-4 text-left ${mode===m.id?"border-slate-400 bg-slate-700/40 text-white":"border-slate-700/60 bg-slate-900/30 text-slate-400 hover:bg-slate-800/60"}`}><span className="block text-[10px] tracking-widest text-slate-500">0{i+1}</span><span className="mt-2 block text-sm font-medium">{m.name}</span><span className="mt-2 block text-xs leading-5">{i===0?"Seconds · low compute":i===2?"Unavailable · screening fallback":i===3?"Seconds–minutes · 1–3 solves":"Seconds–minutes · mesh dependent"}</span></button>)}</div><div className="grid gap-3 rounded-xl border border-slate-700/50 bg-slate-900/30 p-4 text-xs sm:grid-cols-3"><p><span className="block mb-1 text-slate-500">Solver / physical scope</span>{modes.find(m=>m.id===mode)?.scope}</p><p><span className="block mb-1 text-slate-500">Expected fidelity / limitations</span>{simulationModeLimitations(mode)}</p><p><span className="block mb-1 text-slate-500">Experimental validation</span>Pending · neither calibration nor numerical convergence establishes independent validation.</p></div></section>
    <Lock>
    <details className={surface} aria-label="Engineering controls"><summary className="cursor-pointer font-medium">Process settings <span className="ml-3 text-xs font-normal text-slate-400">Shared vector · {formatExactNumber(input.power_W)} W / {formatExactNumber(input.speed_mm_s)} mm/s / {formatExactNumber(input.beamDiameter_um)} µm beam</span></summary>
      <label className="block my-3">Material for this engineering run<select className={inputClass} value={material} onChange={e=>{setMaterial(e.target.value);setProperties("");}}><option value="">Shared: {input.material}</option>{caps?.materials.map(m=><option key={m.name} value={m.name}>{m.name} · {m.quality}</option>)}</select></label><p className="text-xs text-slate-400 mb-4">Material override applies to this engineering run. The run override is included in the executed input snapshot and qualification report.</p>{missingMaterial&&<p role="alert" className="mb-4 rounded-lg border border-amber-400/30 p-3 text-sm text-amber-200">Thermophysical data is missing for this alloy. Supply a sourced property table before running the engineering solver.</p>}
    <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-3">{([
      ["power_W","laserPower_W","Laser power","W",10,1500], ["speed_mm_s","scanSpeed_mms","Scan speed","mm/s",10,10000],
      ["beamDiameter_um","beamDiameter_um","Beam diameter","µm",20,500], ["hatch_um","hatch_um","Hatch spacing","µm",10,1000],
      ["layer_um","layer_um","Layer thickness","µm",10,150], ["preheat_C","preheatTemp_C","Preheat","°C",0,1200]
    ] as const).map(([key,shared,label,unit,min,max])=><label key={key} className="text-xs text-slate-400">{label} · {unit}<input aria-label={`${label} (${unit})`} className={`${inputClass} mt-1 text-base tabular-nums`} type="number" min={min} max={max} step="any" aria-invalid={!Number.isFinite(input[key])||input[key]<min||input[key]>max} value={input[key]} onChange={e=>{const value=e.currentTarget.valueAsNumber;if(Number.isFinite(value))updateProcess({[shared]:value});}}/><span className="block mt-1 text-[10px]">{min}–{max} {unit} · shared</span>{(input[key]<min||input[key]>max)&&<span className="block text-xs text-red-300">Enter {min}–{max} {unit}.</span>}<button type="button" className="mt-1 text-xs underline underline-offset-4" onClick={()=>updateProcess({[shared]:initialProcess.current[key]})}>Reset {label.toLowerCase()} · {initialProcess.current[key]} {unit}</button><details className="mt-1"><summary className="text-[10px] cursor-pointer">Parameter guidance</summary><span className="text-xs leading-5">{label} updates the shared process vector. Default: value on opening. Power and geometry change thermal response; speed and layer thickness can change simulated duration and compute cost. See preflight for this combination.</span></details></label>)}</div>
    </details>
    </Lock>
    <div className="mt-5 flex flex-wrap items-center gap-3"><button className="rounded-lg border border-slate-400/50 bg-slate-200 px-5 py-2.5 text-sm font-semibold text-slate-950 hover:bg-white disabled:opacity-40" disabled={busy||active||missingMaterial||invalidControls||invalidProcess} onClick={submit}>{busy?"Submitting…":"Run simulation"}</button>{r&&<button className="rounded-lg border border-slate-600 px-4 py-2.5 text-sm hover:bg-slate-800" onClick={download}>Export result JSON</button>}<span className="text-xs text-slate-400">{invalidControls||invalidProcess?"Correct invalid parameters to run.":active?"Worker active · controls remain available for the next run.":"Execution runs in the worker queue."}</span></div>
    <div className="rounded-xl border border-slate-700/50 bg-slate-900/30 p-4">
      <label className="flex items-start gap-3 text-sm text-slate-200">
        <input aria-label="Create a fresh computational run record" aria-describedby="repeat-run-help"
          className="mt-1 accent-sky-400" type="checkbox" checked={repeatExecution}
          disabled={busy||active||!canRepeatCurrentInput}
          onChange={event=>setRepeatExecution(event.currentTarget.checked)}/>
        <span>Create a fresh computational run record</span>
      </label>
      <p id="repeat-run-help" className="ml-6 mt-2 text-xs leading-5 text-slate-400">
        Available after this exact input finishes. It reruns the same LPBF inputs to create a distinct run ID; it does not represent an experimental or physical repeat. The default submission remains deduplicated.
      </p>
    </div>
    <GpuPilotControls input={input} settings={settings} material={material||input.material} properties={properties} strategy={resolvedStrategy} caps={caps} blocked={busy||active||missingMaterial||invalidControls||invalidProcess}/>
    {(mode==="standard"||mode==="calibration")&&<p className="text-xs text-slate-400" role="status">{estimateError||(estimate?`Preflight: ${fmt(estimate.cells)} cells · ${fmt(estimate.spacing_m*1e6)} µm · ~${fmt(estimate.minimumEstimatedSteps)} estimated steps · ~${fmt(estimate.workingMemoryEstimate_MB)} MB working arrays · ${estimate.runs} solve(s). ${estimate.exceedsCellBudget?"Cell budget exceeded.":estimate.exceedsStepBudget?"Requested timestep exceeds the 250,000-step budget. Increase timestep or shorten the process history.":estimate.runtimeEstimate}`:"Estimating resources…")}</p>}
    {r&&<>
      {resultStale&&<StaleResultBanner className="rounded-xl"/>}
      {r.fallbackReason&&<p className="text-sm text-amber-200">{r.fallbackReason}</p>}
      <section aria-label="Melt pool geometry" className="space-y-4"><div className="flex flex-wrap justify-between gap-2"><h4 className="font-medium">Melt pool geometry</h4><Badge tone="neutral">{r.fieldSeries?"Resolved thermal cells":"Analytical screening geometry"}</Badge></div><p className="text-xs text-slate-400">{r.confidenceReason} Free-surface unresolved · Keyhole unresolved · Stress not solved.</p>
      {r.fieldSeries && <ResolvedThermalViewer jobId={job.id} result={r} onTimeChange={setFieldTime}/>}
      {r.fieldPreviews && <details className="border-t border-slate-700 pt-3"><summary className="cursor-pointer">Resolved temperature and phase fields · X–Z slice</summary><p className="text-xs text-slate-400 my-2">Peak sampled melt volume; actual cell fields. Enthalpy liquid fraction is not a metal/gas VOF interface. The analytical studio is separate.</p>{r.fieldPreviews.map(name=><img key={name} loading="lazy" className="w-full my-3" alt={name==="temperature-slice.svg"?"Resolved OpenFOAM or reference temperature slice":"Resolved enthalpy liquid fraction slice"} src={`/api/lpbf/jobs/${job.id}/artifacts/${encodeURIComponent(name)}`}/>)}</details>}
      {r.thermalHistory && <a className="text-sm underline" href={`/api/lpbf/jobs/${job.id}/artifacts/thermal-history.csv`}>Download thermal history CSV</a>}
      {!r.fieldSeries&&<div className="rounded-xl border border-slate-700/50 bg-slate-900/40 p-6"><p className="text-sm">Analytical L / W / D are reported in the result header.</p><p className="mt-2 text-xs text-slate-400">No resolved field was produced. Open the separately labelled analytical screening studio below to inspect illustrative geometry.</p></div>}
      </section>
      <ThermalHistory result={r} currentTime={fieldTime}/>
      <LpbfPhysicsDiagnostics result={r}/>
      <section className={surface} aria-label="Numerical audit"><h4 className="font-medium">Numerical audit</h4><div className="mt-4 grid gap-4 md:grid-cols-2"><div><p className="text-sm">Energy balance · {r.energyBalance?`${fmt(r.energyBalance.relativeError*100)}% closure error`:"Not reported"}</p><p className="mt-2 text-xs text-slate-400">{r.energyBalance?`Absorbed ${fmt(r.energyBalance.input_J)} J · stored ${fmt(r.energyBalance.stored_J)} J · losses ${fmt(r.energyBalance.losses_J)} J`:"Screening geometry does not establish energy conservation."}</p></div><div><p className="text-sm">Mass balance · {r.massBalance?`${fmt(r.massBalance.relativeError*100)}% closure error`:"Not reported"}</p><p className="mt-2 text-xs text-slate-400">{r.massBalance?.scope||"No resolved mass transport."}</p></div></div><p className="mt-4 text-xs text-amber-200">Conservation does not establish physical accuracy. Inspect the worker's numerical warnings.</p></section>
      <ConvergencePanel study={r.convergenceStudy}/>
      <MeasurementPanel result={r}/>
      <section data-transient-diagnostics><h5>{SOLIDIFICATION_WORDING.transientHeading}</h5><SolidificationQuantities container={r.transientFrontDiagnostics} frontOnly={false}/></section>
      <details className="border-t border-slate-700 pt-3"><summary className="cursor-pointer">Technical details · metrics, assumptions and provenance</summary><dl className="grid grid-cols-2 md:grid-cols-3 gap-4 py-4">{Object.entries(r.metrics).filter(([k]) => !TRANSIENT_FRONT_METRICS.has(k)).map(([k,v])=><div key={k}><dt className="text-xs text-slate-400 break-all">{k}</dt><dd className="tabular-nums">{fmt(v)}</dd></div>)}</dl>
        {r.discretization&&<p>Mesh: {fmt(r.discretization.cells)} cells · uniform {fmt(r.discretization.mesh_m*1e6)} µm · {fmt(r.discretization.steps)} steps · minimum Δt {fmt(r.discretization.minimumDt_s)} s. Local refinement unresolved.</p>}
        {r.massBalance&&<p className="text-sm">Mass (kg): initial {fmt(r.massBalance.initial_kg)} + deposited {fmt(r.massBalance.deposited_kg)} = final {fmt(r.massBalance.final_kg)}. {r.massBalance.scope}</p>}
        {r.phaseAudit&&<p className="text-sm">Phase partition: liquid {fmt(r.phaseAudit.liquidVolume_m3)} m³ · solid {fmt(r.phaseAudit.solidVolume_m3)} m³. {r.phaseAudit.scope}</p>}
        {Object.entries<NonNullable<SimulationResult["analyticalComparison"]>[string]>(r.analyticalComparison ?? {}).map(([name,g])=><p key={name}>{name} screening: L {fmt(g.length_um)} / W {fmt(g.width_um)} / D {fmt(g.depth_um)} µm</p>)}
        <p className="text-slate-400 my-3">{r.material.source}</p><ul className="list-disc pl-5 text-sm text-slate-400 space-y-1">{r.assumptions.map(a=><li key={a}>{a}</li>)}</ul>
        {r.provenance&&<div className="mt-4 border-t border-slate-700/50 pt-2 text-xs text-slate-400"><p className="font-medium text-slate-300">Run Provenance</p><p>Input Hash: <span className="font-mono">{r.provenance.inputHash}</span></p><p>Implementation Fingerprint: <span className="font-mono">{r.provenance.implementationHash}</span></p>{r.provenance.solverBinaryHash&&<p>Engine Version: <span className="font-mono">{r.provenance.solverBinaryHash}</span></p>}</div>}
      </details>
      {r.artifacts&&<details className="border-t border-slate-700 pt-3"><summary className="cursor-pointer">Artifacts and reproducibility · {r.artifacts.length} files</summary><p className="text-sm text-slate-400 my-2">{r.retentionPolicy}</p><div className="max-h-64 overflow-auto text-xs font-mono space-y-3">{r.artifacts.map(a=><div key={a.path}><p>{a.path} · {fmt(a.size_bytes)} bytes</p><p className="text-slate-500 break-all">SHA-256 {a.sha256}</p></div>)}</div></details>}
      
      {job?.id && !IS_STATIC_DEMO && <div className="mt-6"><LpbfJobArchiver jobId={job.id} /></div>}
    </>}
    <Lock>
    <section aria-label="Advanced engineering controls" className={surface}><div className="flex flex-wrap justify-between gap-3"><h4 className="font-medium">Engineering controls</h4><button className="text-xs underline underline-offset-4" onClick={()=>setSettings({...defaults})}>Reset advanced settings</button></div>
      {[{name:"Scan strategy",keys:["tracks","layers","trackLength_um","stripeWidth_um","islandSize_um","scanAngle_deg","layerRotation_deg","dwell_s","cooling_s"],note:"Longer paths, additional tracks and layers increase compute cost. These are run-specific controls; power, speed, beam, hatch and layer thickness remain shared."},{name:"Powder and material",keys:["packingFraction","powderConductivityRatio","convection_W_m2K"],note:"Run-specific constitutive assumptions. Cost effect is indirect through thermal evolution; estimated data does not become measured evidence."},{name:"Numerical controls",keys:["mesh_um","maxDt_s","timeout_s"],note:"Finer mesh and smaller timestep increase runtime and memory. Timeout is a worker limit, not a convergence criterion."}].map(group=><details key={group.name} className="mt-4 border-t border-slate-700/50 pt-2"><summary className="cursor-pointer text-sm">{group.name}</summary><p className="my-3 text-xs leading-6 text-slate-400">{group.note}</p><div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{controls.filter(([key])=>group.keys.includes(key)).map(([key,label,min,max])=>{const invalid=!Number.isFinite(settings[key])||Number(settings[key])<min||Number(settings[key])>max||((key==="tracks"||key==="layers")&&!Number.isInteger(settings[key]));return <label key={key} className="text-xs text-slate-300">{label}<input aria-label={label} aria-invalid={invalid} aria-describedby={`help-${key}`} className={`${inputClass} mt-2 text-sm tabular-nums`} type="number" min={min} max={max} step={key==="tracks"||key==="layers"?1:"any"} value={Number.isFinite(settings[key])?settings[key]:""} onChange={e=>setSettings(s=>({...s,[key]:e.target.value===""?NaN:Number(e.target.value)}))}/><span id={`help-${key}`} className={`mt-2 block text-xs ${invalid?"text-red-300":"text-slate-400"}`}>{invalid?"Invalid input. ":""}Range {min}–{max}{key==="tracks"||key==="layers"?" · whole numbers":""} · default {defaults[key]}</span><button type="button" className="mt-2 underline underline-offset-4" onClick={()=>setSettings(s=>({...s,[key]:defaults[key]}))}>Reset {label.toLowerCase()}</button></label>;})}</div></details>)}
      {/* A remembered backend choice can outlive the worker's capability: say so outside the collapsed details. Reference enthalpy FV and Automatic do not depend on OpenFOAM. */}
      {settings.backend === "openfoam-thermal" && caps && !caps.openfoamThermal && <p role="status" className="mt-3 rounded-lg border border-amber-500/30 px-3 py-2 text-xs text-amber-200">Backend OpenFOAM 14 thermal is selected (remembered in this browser). OpenFOAM thermal: unavailable. Select Automatic or Reference enthalpy FV under Backend, convergence study and optical overrides.</p>}
      <details className="mt-4 border-t border-slate-700/50 pt-2"><summary className="cursor-pointer text-sm">Backend, convergence study and optical overrides</summary><p className="my-3 text-xs text-slate-400">A convergence study runs three solves. Strategy override applies only to this run; Shared uses the process-vector strategy. Blank optical values use the material defaults.</p>
      <div className="grid md:grid-cols-3 gap-3"><label>Backend<select className={inputClass} value={settings.backend} onChange={e=>setSettings(s=>({...s,backend:e.target.value as SimulationInput["backend"]}))}><option value="auto">Automatic</option><option value="reference">Reference enthalpy FV</option><option value="openfoam-thermal">OpenFOAM 14 thermal</option></select></label><label>Study<select className={inputClass} value={settings.study} onChange={e=>setSettings(s=>({...s,study:e.target.value as SimulationInput["study"]}))}><option value="none">Single solve</option><option value="mesh">Three meshes</option><option value="timestep">Three timesteps</option></select></label><label>Strategy<select className={inputClass} value={settings.strategy||"shared"} onChange={e=>setSettings(s=>({...s,strategy:e.target.value==="shared"?undefined:e.target.value as SimulationInput["strategy"]}))}><option value="shared">Shared ({sharedStrategy})</option><option value="meander">Meander</option><option value="unidirectional">Unidirectional</option><option value="stripe">Stripe</option><option value="island">Rectangular islands</option></select></label></div>
      <div className="grid md:grid-cols-2 gap-3 my-3">{(["absorptivity","emissivity"] as const).map(key=><label key={key}>{key} override (0–1; blank uses material)<input className={inputClass} type="number" min="0" max="1" step="0.01" aria-invalid={settings[key]!==undefined&&(Number(settings[key])<0||Number(settings[key])>1||(key==="absorptivity"&&settings[key]===0))} value={Number.isFinite(settings[key])?settings[key]:""} onChange={e=>setSettings(s=>({...s,[key]:e.target.value===""?undefined:Number(e.target.value)}))}/><span className="block mt-1 text-xs text-slate-400">Dimensionless · {key==="absorptivity"?"0 < value ≤ 1":"0–1"} · indirect compute effect · run override</span>{settings[key]!==undefined&&(Number(settings[key])<0||Number(settings[key])>1||(key==="absorptivity"&&settings[key]===0))&&<span className="block text-xs text-red-300">Invalid optical value.</span>}<button className="text-xs underline" onClick={()=>setSettings(s=>({...s,[key]:undefined}))}>Reset {key} to material default</button></label>)}</div>
      </details>
    </section>
    </Lock>
    <section className={surface} aria-label="Material evidence"><h4 className="font-medium">Material evidence</h4><dl className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{[["Material name",material||input.material],["Data quality",properties.trim()?"User-supplied · awaiting worker checks":materialEvidence?.quality||"Awaiting registry lookup"],["Source",r?.material.name===(material||input.material)?`Executed result source: ${r.material.source}`:materialEvidence?.note||"Registry evidence available after execution"],["Model table coverage",r?.material.name===(material||input.material)&&Array.isArray(r.material.temperatureCoverage_K)?`${r.material.temperatureCoverage_K.map(fmt).join("–")} K · executed material table`:"Not reported for current inputs; inspect sourced table"],["Source validity range",r?.material.name===(material||input.material)&&Array.isArray(r.material.sourceValidityRange_K)?`${r.material.sourceValidityRange_K.map(fmt).join("–")} K · supplied source bound`:"Unknown · no source validity range supplied"],["Estimated / missing fields",materialEvidence?.note||"Not reported"],["Property table",properties.trim()?"User-supplied JSON · unverified":materialEvidence?.available?"Estimated endpoint interpolation available":"No table supplied"]].map(([k,v])=><div key={k}><dt className="text-xs text-slate-400">{k}</dt><dd className="mt-2 text-sm leading-6">{v}</dd></div>)}</dl>{Array.isArray(r?.material.table)&&r.material.table.every(row=>Array.isArray(row)&&row.length===5)&&<details className="mt-4 border-t border-slate-700/50 pt-2"><summary className="cursor-pointer text-sm">Executed property table · {r.material.name}</summary><p className="my-3 text-xs text-amber-200">{r.material.quality} · table used by the displayed result. {r.material.uncertaintyNote}</p><div className="overflow-x-auto"><table className="w-full min-w-[560px] text-left text-xs"><caption className="sr-only">Thermophysical properties used by the displayed simulation</caption><thead><tr>{["Temperature · K","Density · kg/m³","Conductivity · W/mK","Heat capacity · J/kgK","Viscosity · Pa·s"].map(h=><th key={h} className="py-3 pr-4 font-normal text-slate-400">{h}</th>)}</tr></thead><tbody>{r.material.table.map((row,i)=><tr key={i} className="border-t border-slate-700/50">{row.map((v,j)=><td key={j} className="py-3 pr-4 tabular-nums">{fmt(v)}</td>)}</tr>)}</tbody></table></div></details>}<details className="mt-4 border-t border-slate-700/50 pt-2"><summary className="cursor-pointer text-sm">Supply sourced material data</summary><p className="my-3 text-xs text-slate-400">JSON table rows: temperature K, density kg/m³, conductivity W/mK, heat capacity J/kgK, viscosity Pa·s. Include source and required phase/optical properties. Optional <code>sourceValidityRange_K</code> must span the full property table and the declared boiling temperature; it is checked separately from model table coverage. Without it, source validity remains unknown. The transient solver stops at the declared boiling limit.</p><textarea aria-label="Sourced material property JSON" className={inputClass} placeholder="Optional sourced material JSON; see docs/LPBF_ENGINEERING.md" rows={5} value={properties} onChange={e=>setProperties(e.target.value)}/></details></section>
    <Lock>
    <details open={mode==="calibration"?true:undefined} className={surface}><summary className="cursor-pointer font-medium">Validation and calibration</summary><p className="my-4 text-sm leading-6 text-amber-200">Calibration improves comparison reporting. It does not establish independent validation and is not automatically applied to the solver.</p>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3"><label className="text-xs text-slate-400">Measured width · µm<input aria-label="Measured width in micrometres" className={`${inputClass} mt-2`} min={0} step="any" type="number" value={width} onChange={e=>setWidth(e.target.value)}/></label><label className="text-xs text-slate-400">Measured depth · µm<input aria-label="Measured depth in micrometres" className={`${inputClass} mt-2`} min={0} step="any" type="number" value={depth} onChange={e=>setDepth(e.target.value)}/></label><label className="text-xs text-slate-400">Measurement source<input aria-label="Measurement source" className={`${inputClass} mt-2`} value={source} onChange={e=>setSource(e.target.value)}/></label><label className="text-xs text-slate-400">Specimen ID or DOI<input className={`${inputClass} mt-2`} value={specimen} onChange={e=>setSpecimen(e.target.value)}/></label><label className="text-xs text-slate-400">Width / depth uncertainty · µm<input className={`${inputClass} mt-2`} type="number" min={0} step="any" value={uncertainty} onChange={e=>setUncertainty(e.target.value)}/></label><label className="text-xs text-slate-400">Independent holdout status<select className={`${inputClass} mt-2`} value={holdout} onChange={e=>setHoldout(e.target.value)}><option value="unknown">Unknown</option><option value="no">Calibration data</option><option value="yes">User-declared independent</option></select></label></div>
      <p className="text-xs text-slate-400 my-2">Comparison requires real measurements. Manual dimensions have no measurement conditions; process matching remains unverified and calibration factor is withheld. To request calibration comparison, supply all 22 processVector fields in replicate JSON from the measurement conditions, including material and optical properties; the worker checks them against resolved simulation inputs. Partial vectors are rejected. Optional uncertainty_um and independentHoldout record supplied evidence; no automatic validation. See docs/LPBF_ENGINEERING.md.</p>
      <textarea aria-label="Replicate measurement JSON" className={inputClass} placeholder="Optional replicate measurement JSON" value={measurements} onChange={e=>setMeasurements(e.target.value)}/>

    </details>
    </Lock>
    <p className="text-xs text-amber-300">The specialist 3D studio displays analytical screening geometry. Marangoni quantities remain screening estimates; no velocity arrows are rendered. It does not render an OpenFOAM free surface.</p>
  </section>;
}
