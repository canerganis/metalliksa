import { create } from "zustand";
import { useMaterialSpecimenStore, type ActiveSpecimenState } from "./useMaterialSpecimenStore";
import { useLpbfEngineeringStore } from "./useLpbfEngineeringStore";
import { useLpbfWorkflowStore, type LpbfWorkflowStage } from "./useLpbfWorkflowStore";

export const GUIDED_DEMO_STORAGE_KEY = "metalliksa.guidedDemo.v1";
export type GuidedDemoOutcome = "dismissed" | "completed";
export type GuidedDemoStep = 1 | 2 | 3 | 4;
export const GUIDED_DEMO_STEPS = 4;

type StorageLike = Pick<Storage, "getItem" | "setItem">;

function defaultStorage(): StorageLike | undefined {
  try { return globalThis.localStorage; } catch { return undefined; }
}

/** null when unset, unreadable or holding any other value. Storage access can throw (private mode, blocked data). */
export function readGuidedDemoOutcome(storage?: StorageLike): GuidedDemoOutcome | null {
  try {
    const value = (storage ?? defaultStorage())?.getItem(GUIDED_DEMO_STORAGE_KEY);
    return value === "dismissed" || value === "completed" ? value : null;
  } catch { return null; }
}

/** Returns false when the outcome could not be stored; the tour still behaves for this page view. */
export function writeGuidedDemoOutcome(outcome: GuidedDemoOutcome, storage?: StorageLike): boolean {
  try {
    const target = storage ?? defaultStorage();
    if (!target) return false;
    target.setItem(GUIDED_DEMO_STORAGE_KEY, outcome);
    return true;
  } catch { return false; }
}

/** Where each step is shown: the LPBF workspace stage, or another module. */
const STEP_TARGET: Record<GuidedDemoStep, { tabId: string; lpbfStage?: LpbfWorkflowStage }> = {
  1: { tabId: "3d-distortion-lab", lpbfStage: "material" },
  2: { tabId: "3d-distortion-lab", lpbfStage: "thermal" },
  3: { tabId: "3d-distortion-lab", lpbfStage: "melt-pool" },
  4: { tabId: "lpbf-calibration-scorecard" },
};

const WORKSPACE_SELECTOR = 'section[aria-label="LPBF Engineering workspace"]';

/** Existing navigation event. The LPBF workspace only listens once mounted, so a first visit re-sends the stage when it appears. */
function showStep(step: GuidedDemoStep): void {
  const detail = STEP_TARGET[step];
  if (step === 2) useLpbfEngineeringStore.setState({ mode: "screening" });
  if (detail.lpbfStage) useLpbfWorkflowStore.getState().setStage(detail.lpbfStage);
  if (typeof window === "undefined") return;
  // A newly mounted workspace reads the URL before its navigation listener is ready.
  if (detail.lpbfStage) {
    const url = new URL(window.location.href);
    url.searchParams.set("lpbfStage", detail.lpbfStage);
    url.searchParams.delete("lpbfSubTab");
    window.history.replaceState(null, "", url);
  }
  const send = () => window.dispatchEvent(new CustomEvent("metallix-navigate-tab", { detail }));
  send();
  if (!detail.lpbfStage) return;
  let tries = 0;
  const wait = () => {
    if (!useGuidedDemoStore.getState().active || useGuidedDemoStore.getState().step !== step) return;
    if (document.querySelector(WORKSPACE_SELECTOR)) { if (tries > 0) send(); return; }
    if (++tries <= 50) setTimeout(wait, 100);
  };
  wait();
}

export interface GuidedDemoState {
  active: boolean;
  step: GuidedDemoStep;
  /** The specimen as it was before the tour loaded the case; null when nothing was changed. */
  previousSpecimen: ActiveSpecimenState | null;
  /** Why the last start failed; empty otherwise. Rendered with role=alert. */
  startError: string;
  /** Async: the case module loads on demand so the app shell does not carry the literature data. */
  start: () => Promise<void>;
  goTo: (step: GuidedDemoStep) => void;
  next: () => void;
  back: () => void;
  exit: () => void;
  finish: () => void;
  restorePrevious: () => void;
}

export const useGuidedDemoStore = create<GuidedDemoState>((set, get) => ({
  active: false,
  step: 1,
  previousSpecimen: null,
  startError: "",
  start: async () => {
    try {
    const { demoCase, demoProcessPatch } = await import("../utils/guidedDemo");
    const specimens = useMaterialSpecimenStore.getState();
    const c = demoCase(); // throws before anything is changed when the case is missing
    const snapshot = get().previousSpecimen ?? specimens.activeSpecimen;
    specimens.loadPreset("inconel-718");
    useMaterialSpecimenStore.getState().updateLpbfProcess(demoProcessPatch(c));
    set({ active: true, step: 1, previousSpecimen: snapshot, startError: "" });
    showStep(1);
    } catch (reason) {
      set({ startError: reason instanceof Error ? reason.message : "The tour could not start." });
    }
  },
  goTo: step => { set({ step }); showStep(step); },
  next: () => { const { step } = get(); if (step < GUIDED_DEMO_STEPS) get().goTo((step + 1) as GuidedDemoStep); },
  back: () => { const { step } = get(); if (step > 1) get().goTo((step - 1) as GuidedDemoStep); },
  exit: () => {
    if (readGuidedDemoOutcome() === null) writeGuidedDemoOutcome("dismissed");
    set({ active: false });
  },
  finish: () => { writeGuidedDemoOutcome("completed"); set({ active: false }); },
  restorePrevious: () => {
    const snapshot = get().previousSpecimen;
    if (!snapshot) return;
    useMaterialSpecimenStore.setState({ activeSpecimen: snapshot });
    set({ previousSpecimen: null });
  },
}));
