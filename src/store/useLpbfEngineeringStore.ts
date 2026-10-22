import { useCallback } from "react";
import { create } from "zustand";
import { simulationApi, type SimulationInput, type SimulationJob, type SimulationMode } from "../services/lpbfSimulationService";
import { resultSignatureOnPoll, resultSignatureOnRestore } from "../utils/lpbfResultStaleness";

export const LPBF_ENGINEERING_DEFAULTS: Partial<SimulationInput> = { stripeWidth_um:500,islandSize_um:200,mesh_um:20,maxDt_s:1e-6,tracks:1,layers:1,trackLength_um:600,dwell_s:.0002,cooling_s:.0005,packingFraction:.55,powderConductivityRatio:.12,convection_W_m2K:20,timeout_s:300,scanAngle_deg:0,layerRotation_deg:67,study:"none",backend:"auto" };
export interface LpbfEngineeringState {
  settings: Partial<SimulationInput>;
  mode: SimulationMode;
  job: SimulationJob | undefined;
  error: string;
  busy: boolean;
  material: string;
  properties: string;
  measurements: string;
  specimen: string;
  uncertainty: string;
  holdout: string;
  width: string;
  depth: string;
  source: string;
  submittedSignature: string;
  resultSignature: string;
  submittedInput: SimulationInput | undefined;
}

/** Run state survives route changes. Large worker fields remain server artifacts. */
export const useLpbfEngineeringStore = create<LpbfEngineeringState>(() => ({
  settings: {...LPBF_ENGINEERING_DEFAULTS}, mode: "screening", job: undefined,
  error: "", busy: false, material: "", properties: "", measurements: "", specimen: "",
  uncertainty: "", holdout: "unknown", width: "", depth: "", source: "",
  submittedSignature: "", resultSignature: "", submittedInput: undefined,
}));

export const LPBF_ENGINEERING_JOB_STORAGE_KEY = "metalliksa.lpbf.engineering.job.v2";
/** Per-viewer convenience: the thermal backend select only. Results and evidence are never stored here. */
export const LPBF_BACKEND_PREFERENCE_KEY = "metalliksa.lpbf.thermal.backend.v1";
const BACKENDS: SimulationInput["backend"][] = ["auto", "reference", "openfoam-thermal"];

/** Restore evidence at app startup, including direct report/comparison routes. */
export function startEngineeringJobPersistence(storage?: Pick<Storage, "getItem" | "setItem">): () => void {
  let live = true;
  let superseded = false;
  let saved: {id: string; signature?: string; cacheHit?: boolean; input?: SimulationInput} | undefined;
  try {
    storage ??= globalThis.localStorage;
    const value = JSON.parse(storage?.getItem(LPBF_ENGINEERING_JOB_STORAGE_KEY) || "null");
    if (value && typeof value.id === "string" && /^[a-f0-9]{32}$/.test(value.id)) {
      const input = value.input;
      const validInput = input && typeof input.material === "string" && ["power_W", "speed_mm_s", "beamDiameter_um", "preheat_C", "layer_um", "hatch_um"].every(key => typeof input[key] === "number" && Number.isFinite(input[key]));
      saved = {id:value.id, signature:typeof value.signature === "string" ? value.signature : "", cacheHit:typeof value.cacheHit === "boolean" ? value.cacheHit : undefined, input:validInput ? input : undefined};
    }
  } catch { /* Invalid or disabled storage must not block a new simulation. */ }
  try {
    // Remembered backend select (unknown values ignored), restored when App starts this persistence (an App effect,
    // so after App's first render). Views and the report read the store reactively and follow the restored value.
    // A job restored below keeps its executed backend.
    const backend = storage?.getItem(LPBF_BACKEND_PREFERENCE_KEY) as SimulationInput["backend"];
    if (backend && BACKENDS.includes(backend) && backend !== useLpbfEngineeringStore.getState().settings.backend) useLpbfEngineeringStore.setState(s => ({settings: {...s.settings, backend}}));
  } catch { /* Disabled storage: nothing is remembered. */ }
  const persist = (state: LpbfEngineeringState) => {
    if (!state.job) return;
    try {
      storage?.setItem(LPBF_ENGINEERING_JOB_STORAGE_KEY, JSON.stringify({id:state.job.id, signature:state.submittedSignature, cacheHit:state.job.cacheHit, input:state.submittedInput}));
    } catch { /* The server job and in-memory evidence remain available. */ }
  };
  const unsubscribe = useLpbfEngineeringStore.subscribe((state, previous) => {
    if (state.settings.backend !== previous.settings.backend && state.settings.backend) try { storage?.setItem(LPBF_BACKEND_PREFERENCE_KEY, state.settings.backend); } catch { /* Still applies for this page view. */ }
    if (state.job !== previous.job || state.submittedInput !== previous.submittedInput || state.submittedSignature !== previous.submittedSignature || state.busy) superseded = true;
    if (state.job !== previous.job || state.submittedInput !== previous.submittedInput || state.submittedSignature !== previous.submittedSignature) persist(state);
  });
  const initial = useLpbfEngineeringStore.getState();
  if (initial.job) { persist(initial); resumeEngineeringJob(); }
  else if (saved && !initial.busy) {
    const snapshot = saved;
    simulationApi.get(snapshot.id).then(job => {
      if (!live || superseded || useLpbfEngineeringStore.getState().job || useLpbfEngineeringStore.getState().busy) return;
      // Keep current controls intact. A different executed signature remains stale.
      useLpbfEngineeringStore.setState({job:{...job,cacheHit:snapshot.cacheHit}, submittedInput:snapshot.input ?? job.result?.settings, submittedSignature:snapshot.signature || "", resultSignature:resultSignatureOnRestore(job.status, snapshot.signature), error:""});
      resumeEngineeringJob();
    }).catch(error => {
      if (live && !superseded && !useLpbfEngineeringStore.getState().job && !useLpbfEngineeringStore.getState().busy) useLpbfEngineeringStore.setState({error:`Saved job unavailable: ${error instanceof Error ? error.message : "Worker connection failed"}`});
    });
  }
  return () => { live = false; unsubscribe(); };
}

export function useEngineeringField<K extends keyof LpbfEngineeringState>(key: K): [LpbfEngineeringState[K], (value: LpbfEngineeringState[K] | ((previous: LpbfEngineeringState[K]) => LpbfEngineeringState[K])) => void] {
  const value = useLpbfEngineeringStore(state => state[key]);
  const update = useCallback((next: LpbfEngineeringState[K] | ((previous: LpbfEngineeringState[K]) => LpbfEngineeringState[K])) => {
    const resolved = typeof next === "function" ? (next as (previous: LpbfEngineeringState[K]) => LpbfEngineeringState[K])(useLpbfEngineeringStore.getState()[key]) : next;
    useLpbfEngineeringStore.setState({ [key]: resolved } as Pick<LpbfEngineeringState, K>);
    if (key === "job") resumeEngineeringJob();
  }, [key]);
  return [value, update];
}

let pollingId: string | undefined;
/** Poll independently of mounted views, so switching to evidence never loses a running job. */
export function resumeEngineeringJob(): void {
  const job = useLpbfEngineeringStore.getState().job;
  if (!job || !["queued", "running"].includes(job.status) || pollingId === job.id) return;
  pollingId = job.id;
  const id = job.id;
  const poll = async () => {
    const before = useLpbfEngineeringStore.getState();
    if (before.job?.id !== id || !["queued", "running"].includes(before.job.status)) {
      if (pollingId === id) pollingId = undefined;
      return;
    }
    try {
      const next = await simulationApi.get(id);
      const current = useLpbfEngineeringStore.getState();
      if (current.job?.id !== id || !["queued", "running"].includes(current.job.status)) {if (pollingId === id) pollingId = undefined;return;}
      const ownedSignature = resultSignatureOnPoll(next.status, current.submittedSignature);
      useLpbfEngineeringStore.setState({ job: {...next, cacheHit: current.job.cacheHit, deduplicated: current.job.deduplicated}, error: "", ...(ownedSignature !== undefined ? {resultSignature: ownedSignature} : {}) });
    } catch (error) {
      if (useLpbfEngineeringStore.getState().job?.id === id) useLpbfEngineeringStore.setState({error: error instanceof Error ? error.message : "Worker connection failed"});
    }
    const current = useLpbfEngineeringStore.getState();
    if (current.job?.id === id && ["queued", "running"].includes(current.job.status)) setTimeout(poll, typeof document !== "undefined" && document.hidden ? 5000 : 1500);
    else if (pollingId === id) pollingId = undefined;
  };
  setTimeout(poll, 500);
}

/** Signature of the draft inputs; the engineering view and the qualification report both build it here. */
export type EngineeringSignatureFields = Pick<LpbfEngineeringState, "settings" | "mode" | "material" | "properties" | "measurements" | "width" | "depth" | "source" | "specimen" | "uncertainty" | "holdout">;
export function engineeringSignature(input: SimulationInput, state: EngineeringSignatureFields, strategy: string): string {
  return JSON.stringify([input,state.settings,state.mode,state.material,state.properties,state.measurements,state.width,state.depth,state.source,state.specimen,state.uncertainty,state.holdout,strategy]);
}
