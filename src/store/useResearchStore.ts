import { create } from 'zustand';
import { createJSONStorage, persist, type StateStorage } from 'zustand/middleware';
import type { ResearchBrief, ResearchFeedback, ResearchFinding, ResearchSnapshot, ResearchSource, ResearchTargetModule } from '../types/research';
import { normalizeDoi, parseResearchSnapshot, researchIntegrationIssues, researchReviewIssues, researchRecordKey, researchSnapshotKey, validateResearchFinding, validateResearchSource } from '../utils/researchRegistry';

type ActionResult = { id?: string; errors: string[] };
type ResearchTab = 'brief' | 'sources' | 'extract' | 'registry' | 'catalog' | 'blind-test';
export interface ResearchState extends ResearchSnapshot {
  activeBriefId: string;
  activeSourceId: string;
  activeTab: ResearchTab;
  /** Form drafts survive workspace switches and reloads. */
  drafts: Record<string, Record<string, string>>;
  storageError: string;
  serverBase: { registryId: string; revision: number } | null;
  acceptServerSnapshot: (snapshot: ResearchSnapshot, expectedLocalKey: string, serverBase: { registryId: string; revision: number }) => ActionResult;
  acknowledgeServer: (serverBase: { registryId: string; revision: number }) => void;
  setActiveTab: (tab: ResearchTab) => void;
  setActiveBrief: (id: string) => void;
  setActiveSource: (id: string) => void;
  setDraft: (key: string, value: Record<string, string>) => void;
  addBrief: (brief: Omit<ResearchBrief, 'id' | 'createdAt'>) => ActionResult;
  addSource: (source: Omit<ResearchSource, 'id' | 'createdAt'>) => ActionResult;
  updateSource: (id: string, source: Omit<ResearchSource, 'id' | 'createdAt'>) => ActionResult;
  addFinding: (finding: Omit<ResearchFinding, 'id' | 'createdAt' | 'reviewStatus' | 'reviewedAt' | 'conflictsWith'>) => ActionResult;
  reviewFinding: (id: string, note: string) => ActionResult;
  reviseFinding: (id: string, finding: Omit<ResearchFinding, 'id' | 'createdAt' | 'reviewStatus' | 'reviewedAt' | 'conflictsWith'>) => ActionResult;
  integrateFinding: (id: string, target: ResearchTargetModule) => ActionResult;
  setConflict: (id: string, otherId: string, flagged: boolean) => ActionResult;
  addFeedback: (feedback: Omit<ResearchFeedback, 'id' | 'createdAt'>) => ActionResult;
  exportSnapshot: () => ResearchSnapshot;
  importSnapshot: (value: unknown) => ActionResult;
}
const emptySnapshot: ResearchSnapshot = { schemaVersion: 1, briefs: [], sources: [], findings: [], integrations: [], feedback: [] };
const newId = (prefix: string) => `${prefix}-${globalThis.crypto.randomUUID()}`;
const now = () => new Date().toISOString();
let storageWritesBlocked = false;
const observedStorage = new Map<string, string | null>();
let reportingStorageError = false;
let pendingStorageError = '';
function reportStorageError(message: string) {
  pendingStorageError = message;
  if (reportingStorageError) return;
  reportingStorageError = true;
  queueMicrotask(() => {
    // Persist also runs for this status update. Keep the guard raised until it returns.
    useResearchStore.setState({ storageError: pendingStorageError });
    reportingStorageError = false;
  });
}
function canWriteStorage(name: string) {
  if (storageWritesBlocked) return false;
  if (localStorage.getItem(name) !== (observedStorage.get(name) ?? null)) {
    storageWritesBlocked = true;
    reportStorageError('Another tab changed the browser research registry. Persistence is paused; both versions are preserved. Export browser recovery copy before reloading to preserve this tab’s records and drafts.');
    return false;
  }
  return true;
}
// Quota / unavailable-storage errors are visible without throwing out the in-memory session.
const storage: StateStorage = {
  getItem: name => {
    const raw = typeof localStorage === 'undefined' ? null : localStorage.getItem(name);
    observedStorage.set(name, raw);
    return raw;
  },
  setItem: (name, value) => {
    if (typeof localStorage === 'undefined' || storageWritesBlocked) return;
    try {
      if (!canWriteStorage(name)) return;
      localStorage.setItem(name, value);
      observedStorage.set(name, value);
    } catch { reportStorageError('Browser storage is unavailable or full. Export browser recovery copy to preserve this session’s records and drafts.'); }
  },
  removeItem: name => {
    if (typeof localStorage === 'undefined' || storageWritesBlocked) return;
    try {
      if (!canWriteStorage(name)) return;
      localStorage.removeItem(name);
      observedStorage.set(name, null);
    } catch { reportStorageError('Browser storage is unavailable. Export browser recovery copy to preserve this session’s records and drafts.'); }
  },
};

function parseBrowserDrafts(value: unknown): ResearchState['drafts'] {
  if (!value || typeof value !== 'object' || Array.isArray(value) || Object.keys(value).length > 10000) throw new Error('Invalid browser recovery drafts.');
  const drafts = Object.entries(value).map(([key, draft]) => {
    if (!key || key.length > 1000 || !draft || typeof draft !== 'object' || Array.isArray(draft) || Object.keys(draft).length > 100) throw new Error('Invalid or oversized browser recovery draft.');
    for (const [field, text] of Object.entries(draft)) {
      if (!field || field.length > 1000 || typeof text !== 'string' || text.length > 100000) throw new Error('Invalid or oversized browser recovery draft field.');
    }
    return [key, Object.fromEntries(Object.entries(draft))] as const;
  });
  return Object.fromEntries(drafts) as ResearchState['drafts'];
}

export const useResearchStore = create<ResearchState>()(persist((set, get) => ({
  ...emptySnapshot, activeBriefId: '', activeSourceId: '', activeTab: 'brief', drafts: {}, storageError: '', serverBase: null,
  acknowledgeServer: serverBase => set({ serverBase }),
  acceptServerSnapshot: (snapshot, expectedLocalKey, serverBase) => {
    if (researchSnapshotKey(get().exportSnapshot()) !== expectedLocalKey) return { errors: ['Browser records changed during review. Check the server again before applying.'] };
    try {
      const clean = parseResearchSnapshot(snapshot);
      set({ ...clean, serverBase, activeBriefId: clean.briefs.some(b => b.id === get().activeBriefId) ? get().activeBriefId : clean.briefs[0]?.id ?? '', activeSourceId: clean.sources.some(s => s.id === get().activeSourceId) ? get().activeSourceId : '' });
      return { errors: [] };
    } catch (error) { return { errors: [(error as Error).message] }; }
  },
  setActiveTab: activeTab => set({ activeTab }),
  setActiveBrief: activeBriefId => set({ activeBriefId, activeSourceId: get().sources.find(s => s.briefId === activeBriefId)?.id ?? '' }),
  setActiveSource: activeSourceId => set({ activeSourceId }),
  setDraft: (key, value) => set(state => ({ drafts: { ...state.drafts, [key]: value } })),
  addBrief: brief => {
    if (!brief.question.trim()) return { errors: ['A research question is required.'] };
    const id = newId('brief'); set(state => ({ briefs: [...state.briefs, { ...brief, question: brief.question.trim(), id, createdAt: now() }], activeBriefId: id, activeSourceId: '', activeTab: 'sources' })); return { id, errors: [] };
  },
  addSource: input => {
    const source: ResearchSource = { ...input, doi: normalizeDoi(input.doi), id: newId('source'), createdAt: now() };
    const errors = validateResearchSource(source);
    if (!get().briefs.some(b => b.id === source.briefId)) errors.push('Create or select a research brief first.');
    if (get().sources.some(s => s.briefId === source.briefId && (source.doi ? s.doi === source.doi : s.url === source.url))) errors.push('This source is already saved in the selected brief.');
    if (errors.length) return { errors };
    set(state => ({ sources: [...state.sources, source], activeSourceId: source.id })); return { id: source.id, errors: [] };
  },
  addFinding: input => {
    const finding: ResearchFinding = { ...input, id: newId('finding'), createdAt: now(), reviewStatus: 'draft', conflictsWith: [] };
    const source = get().sources.find(s => s.id === finding.sourceId), errors = validateResearchFinding(finding, source);
    if (source?.briefId !== finding.briefId) errors.push('Finding and source must belong to the same brief.');
    if (errors.length) return { errors };
    set(state => ({ findings: [...state.findings, finding], activeTab: 'registry' })); return { id: finding.id, errors: [] };
  },
  updateSource: (id, input) => {
    const existing = get().sources.find(s => s.id === id); if (!existing) return { errors: ['Source not found.'] };
    const source = { ...input, doi: normalizeDoi(input.doi), id, createdAt: existing.createdAt };
    const errors = validateResearchSource(source);
    if (source.briefId !== existing.briefId) errors.push('A source cannot be moved to another brief.');
    if (get().sources.some(s => s.id !== id && s.briefId === source.briefId && (source.doi ? s.doi === source.doi : s.url === source.url))) errors.push('This source already exists in the brief.');
    if (errors.length) return { errors };
    const affected = new Set(get().findings.filter(f => f.sourceId === id).map(f => f.id));
    set(state => ({ sources: state.sources.map(s => s.id === id ? source : s), findings: state.findings.map(f => affected.has(f.id) ? { ...f, reviewStatus: 'draft', reviewNote: '', reviewedAt: undefined } : f), integrations: state.integrations.filter(i => !affected.has(i.findingId)) })); return { id, errors: [] };
  },
  reviseFinding: (id, input) => {
    const existing = get().findings.find(f => f.id === id); if (!existing) return { errors: ['Finding not found.'] };
    const finding: ResearchFinding = { ...existing, ...input, id, createdAt: existing.createdAt, reviewStatus: 'draft', reviewNote: '', reviewedAt: undefined };
    const source = get().sources.find(s => s.id === finding.sourceId), errors = validateResearchFinding(finding, source);
    if (source?.briefId !== finding.briefId) errors.push('Finding and source must belong to the same brief.');
    if (errors.length) return { errors };
    set(state => ({ findings: state.findings.map(f => f.id === id ? finding : f), integrations: state.integrations.filter(i => i.findingId !== id) })); return { id, errors: [] };
  },
  reviewFinding: (id, note) => {
    const original = get().findings.find(f => f.id === id); if (!original) return { errors: ['Finding not found.'] };
    const finding = { ...original, reviewNote: note.trim() }, errors = researchReviewIssues(finding, get().sources.find(s => s.id === finding.sourceId));
    if (errors.length) return { errors };
    set(state => ({ findings: state.findings.map(f => f.id === id ? { ...finding, reviewStatus: 'reviewed', reviewedAt: now() } : f) })); return { id, errors: [] };
  },
  integrateFinding: (id, target) => {
    const finding = get().findings.find(f => f.id === id); if (!finding) return { errors: ['Finding not found.'] };
    const errors = researchIntegrationIssues(finding, get().sources.find(s => s.id === finding.sourceId), target);
    if (errors.length) return { errors };
    const existing = get().integrations.find(i => i.findingId === id && i.targetModule === target); if (existing) return { id: existing.id, errors: [] };
    const integration = { id: newId('integration'), findingId: id, materialId: finding.materialId, targetModule: target, status: 'linked' as const, createdAt: now() };
    set(state => ({ integrations: [...state.integrations, integration] })); return { id: integration.id, errors: [] };
  },
  setConflict: (id, otherId, flagged) => {
    if (id === otherId || ![id, otherId].every(key => get().findings.some(f => f.id === key))) return { errors: ['Select two different saved findings.'] };
    set(state => ({
      findings: state.findings.map(f => [id, otherId].includes(f.id) ? { ...f, conflictsWith: flagged ? [...new Set([...f.conflictsWith, f.id === id ? otherId : id])] : f.conflictsWith.filter(key => key !== (f.id === id ? otherId : id)) } : f),
      integrations: flagged ? state.integrations.filter(i => ![id, otherId].includes(i.findingId)) : state.integrations,
    })); return { id, errors: [] };
  },
  addFeedback: input => {
    if (!get().findings.some(f => f.id === input.findingId)) return { errors: ['Finding not found.'] };
    if (!input.note.trim() || !input.experimentOrJobReference.trim()) return { errors: ['Feedback requires an outcome note and experiment or simulation job reference.'] };
    if (!['supports', 'contradicts', 'inconclusive'].includes(input.outcome)) return { errors: ['Select a supported feedback outcome.'] };
    const id = newId('feedback');
    set(state => ({ feedback: [...state.feedback, { ...input, id, createdAt: now() }],
      // Contradictory evidence withdraws previous integrations until a new review.
      findings: input.outcome === 'contradicts' ? state.findings.map(f => f.id === input.findingId ? { ...f, reviewStatus: 'draft', reviewNote: '', reviewedAt: undefined } : f) : state.findings,
      integrations: input.outcome === 'contradicts' ? state.integrations.filter(i => i.findingId !== input.findingId) : state.integrations,
    })); return { id, errors: [] };
  },
  exportSnapshot: () => { const { schemaVersion, briefs, sources, findings, integrations, feedback } = get(); return { schemaVersion, briefs, sources, findings, integrations, feedback }; },
  importSnapshot: value => {
    try {
      const incoming = parseResearchSnapshot(value), current = get().exportSnapshot();
      const browserDrafts = Object.prototype.hasOwnProperty.call(value, 'browserDrafts') ? parseBrowserDrafts((value as { browserDrafts: unknown }).browserDrafts) : {};
      const drafts = { ...get().drafts };
      for (const [key, draft] of Object.entries(browserDrafts)) {
        if (Object.prototype.hasOwnProperty.call(drafts, key) && researchRecordKey(drafts[key]) !== researchRecordKey(draft)) throw new Error(`Import contains a conflicting browser draft: ${key}. Existing records and drafts were preserved.`);
        Object.defineProperty(drafts, key, { value: draft, enumerable: true, configurable: true, writable: true });
      }
      const merged = { ...current };
      for (const key of ['briefs', 'sources', 'findings', 'integrations', 'feedback'] as const) {
        const existing = new Map<string, unknown>(current[key].map(item => [item.id, item] as const));
        for (const item of incoming[key]) {
          if (existing.has(item.id) && researchRecordKey(existing.get(item.id)) !== researchRecordKey(item)) throw new Error(`Import contains a conflicting existing record: ${item.id}. Existing work was preserved.`);
          existing.set(item.id, item);
        }
        (merged[key] as unknown[]) = [...existing.values()];
      }
      parseResearchSnapshot(merged); set({ ...merged, drafts, activeBriefId: get().activeBriefId || incoming.briefs[0]?.id || '' }); return { errors: [] };
    } catch (error) { return { errors: [error instanceof Error ? error.message : 'Unable to import research registry.'] }; }
  },
}), {
  name: 'metalliksa-research-registry-v1', version: 1, storage: createJSONStorage(() => storage),
  partialize: state => ({ ...state.exportSnapshot(), serverBase: state.serverBase, activeBriefId: state.activeBriefId, activeSourceId: state.activeSourceId, activeTab: state.activeTab, drafts: state.drafts }),
  merge: (persisted, current) => {
    if (persisted === undefined || persisted === null) return current;
    try {
      const data = persisted as ResearchState; const snapshot = { ...parseResearchSnapshot(data), serverBase: data.serverBase && typeof data.serverBase.registryId === 'string' && data.serverBase.registryId.length > 0 && Number.isSafeInteger(data.serverBase.revision) && data.serverBase.revision >= 0 ? { registryId: data.serverBase.registryId, revision: data.serverBase.revision } : null };
      const drafts = data.drafts && typeof data.drafts === 'object' ? Object.fromEntries(Object.entries(data.drafts).filter(([, draft]) => draft && typeof draft === 'object' && !Array.isArray(draft) && Object.values(draft).every(value => typeof value === 'string'))) : {};
      return { ...current, ...snapshot, activeBriefId: snapshot.briefs.some(b => b.id === data.activeBriefId) ? data.activeBriefId : snapshot.briefs[0]?.id ?? '', activeSourceId: snapshot.sources.some(s => s.id === data.activeSourceId) ? data.activeSourceId : '', activeTab: ['brief', 'sources', 'extract', 'registry', 'catalog', 'blind-test'].includes(data.activeTab) ? data.activeTab : 'brief', drafts };
    } catch { storageWritesBlocked = true; return { ...current, storageError: 'Saved research data could not be read safely. Original browser data are preserved and persistence is paused. Export this session to preserve new work.' }; }
  },
  onRehydrateStorage: () => (_state, error) => { if (error) { storageWritesBlocked = true; reportStorageError('Research storage could not be loaded. Original data are preserved; export browser recovery copy to keep new records and drafts.'); } },
}));
