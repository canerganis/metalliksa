import { create } from "zustand";
import { createJSONStorage, persist, type StateStorage } from "zustand/middleware";
import {
  BLIND_DRAFT_DEFAULTS,
  BLIND_DRAFT_KEYS,
  BLIND_PROTOCOL,
  type BlindMetadataDraft,
  type BlindJobType,
} from "../data/lpbfUserBlind";

/**
 * Persisted state of the user blind test (spec 3.4 item 6): the metadata draft, the ids of queued jobs so a reload can
 * resume polling, and receipt summaries of known freezes. Never CSV text, base64, predictions or measurements.
 */
export const USER_BLIND_STORE_KEY = "metalliksa.lpbf.userBlind.v1";

/** `name` and `attempt` are set for an open job (which document it was queued for); otherwise null. */
export interface BlindPendingJob { id: string; jobType: BlindJobType; freezeKey: string | null; name: string | null; attempt: number | null }
export interface BlindKnownFreeze { freezeKey: string; freezeSha256: string; createdAt: string; blockLabel: string; alloy: string; conditions: number }

export interface UserBlindState {
  draft: BlindMetadataDraft;
  pending: BlindPendingJob[];
  known: BlindKnownFreeze[];
  patchDraft: (patch: Partial<BlindMetadataDraft>) => void;
  resetDraft: () => void;
  addPending: (job: BlindPendingJob) => void;
  removePending: (id: string) => void;
  rememberFreeze: (summary: BlindKnownFreeze) => void;
  forgetFreeze: (freezeKey: string) => void;
}

const HEX64 = /^[0-9a-f]{64}$/;
const JOB_ID = /^[0-9a-zA-Z-]{1,64}$/;
const isObj = (v: unknown): v is Record<string, unknown> => typeof v === "object" && v !== null && !Array.isArray(v);
const MAX_KNOWN = 200;
const MAX_PENDING = 8;

/** Every storage access sits in try and catch: blocked, full or throwing storage never breaks the panel. */
export const safeBlindStorage: StateStorage = {
  getItem: name => { try { return globalThis.localStorage?.getItem(name) ?? null; } catch { return null; } },
  setItem: (name, value) => { try { globalThis.localStorage?.setItem(name, value); } catch { /* the in-memory state keeps working */ } },
  removeItem: name => { try { globalThis.localStorage?.removeItem(name); } catch { /* ignore */ } },
};

function mergeDraft(saved: unknown, base: BlindMetadataDraft): BlindMetadataDraft {
  const out: Record<string, string | boolean> = { ...base };
  if (!isObj(saved)) return out as unknown as BlindMetadataDraft;
  for (const key of BLIND_DRAFT_KEYS) {
    const want = typeof BLIND_DRAFT_DEFAULTS[key];
    const value = saved[key];
    if (typeof value === want && (want !== "string" || (value as string).length <= 400)) out[key] = value as string | boolean;
  }
  return out as unknown as BlindMetadataDraft;
}

/** Whitelist merge (useLpbfWorkflowStore pattern): unknown keys and wrongly typed values are dropped. */
export function mergeBlindPersisted(saved: unknown, current: UserBlindState): UserBlindState {
  const persisted = isObj(saved) ? saved : {};
  const jobs = BLIND_PROTOCOL.requestTypes.jobs as readonly string[];
  const pending: BlindPendingJob[] = [];
  if (Array.isArray(persisted.pending)) {
    for (const p of persisted.pending.slice(0, MAX_PENDING)) {
      if (isObj(p) && typeof p.id === "string" && JOB_ID.test(p.id) && typeof p.jobType === "string" && jobs.includes(p.jobType)
        && (p.freezeKey === null || (typeof p.freezeKey === "string" && HEX64.test(p.freezeKey)))) {
        const name = typeof p.name === "string" && (BLIND_PROTOCOL.artifactNames as readonly string[]).includes(p.name) ? p.name : null;
        const attempt = typeof p.attempt === "number" && Number.isInteger(p.attempt) && p.attempt >= 1 && p.attempt < 1000 ? p.attempt : null;
        pending.push({ id: p.id, jobType: p.jobType as BlindJobType, freezeKey: p.freezeKey as string | null, name, attempt });
      }
    }
  }
  const known: BlindKnownFreeze[] = [];
  if (Array.isArray(persisted.known)) {
    for (const k of persisted.known.slice(0, MAX_KNOWN)) {
      if (isObj(k) && typeof k.freezeKey === "string" && HEX64.test(k.freezeKey) && typeof k.freezeSha256 === "string" && HEX64.test(k.freezeSha256)
        && typeof k.createdAt === "string" && typeof k.blockLabel === "string" && typeof k.alloy === "string"
        && typeof k.conditions === "number" && Number.isInteger(k.conditions)) {
        known.push({ freezeKey: k.freezeKey, freezeSha256: k.freezeSha256, createdAt: k.createdAt.slice(0, 40), blockLabel: k.blockLabel.slice(0, 80), alloy: k.alloy.slice(0, 40), conditions: k.conditions });
      }
    }
  }
  return { ...current, draft: mergeDraft(persisted.draft, current.draft), pending, known };
}

export const useUserBlindStore = create<UserBlindState>()(persist((set) => ({
  draft: { ...BLIND_DRAFT_DEFAULTS },
  pending: [],
  known: [],
  patchDraft: patch => set(state => ({ draft: { ...state.draft, ...patch } })),
  resetDraft: () => set({ draft: { ...BLIND_DRAFT_DEFAULTS } }),
  addPending: job => set(state => ({ pending: [...state.pending.filter(p => p.id !== job.id), job].slice(-MAX_PENDING) })),
  removePending: id => set(state => ({ pending: state.pending.filter(p => p.id !== id) })),
  rememberFreeze: summary => set(state => ({ known: [summary, ...state.known.filter(k => k.freezeKey !== summary.freezeKey)].slice(0, MAX_KNOWN) })),
  forgetFreeze: freezeKey => set(state => ({ known: state.known.filter(k => k.freezeKey !== freezeKey) })),
}), {
  name: USER_BLIND_STORE_KEY,
  storage: createJSONStorage(() => safeBlindStorage),
  partialize: state => ({ draft: state.draft, pending: state.pending, known: state.known }),
  merge: (saved, current) => mergeBlindPersisted(saved, current),
}));
