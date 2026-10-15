/**
 * Session store of the Research model panel (P8 contract 4.3 to 4.5, 13.9).
 *
 * Research only. This store never imports or writes useLpbfBuildJobStore, the specimen store or any export path; its
 * only outward call is pythonComputationService.solveLpbfResearchModels. It holds:
 *  - the research options keyed by alloy id (a preset chosen for one alloy never reaches a host showing another),
 *  - one run state per host ("melt-pool" and "build-job"), driven by a generation counter,
 *  - a bounded client map of finished results (8 entries), so switching labs with the same inputs shows the finished
 *    result without a rerun.
 * It keeps no process vector of its own: a host mirrors its current request values here only so a describe, a Run or
 * a Retry can be sent, and a Run snapshots them as the run identity.
 */
import { create } from "zustand";
import { pythonComputationService } from "../services/pythonComputationService";
import {
  RESEARCH_ROUTE_SCHEMA_REQUEST,
  type ResearchDescribeResponse,
  type ResearchHostId,
  type ResearchOutcome,
  type ResearchProblem,
  type ResearchRequest,
  type ResearchRunResponse,
  type ResearchStage,
} from "../types/lpbfResearchModels";
import {
  VAPOUR_OVERRIDE_KEYS,
  buildResearchOptions,
  emptyAlloyOptions,
  identityKey,
  researchAlloyKey,
  supersedeKeyFor,
  toResearchProcess,
  type AlloyOptions,
  type OptionModule,
  type OptionValue,
  type ResearchHostInput,
} from "../utils/lpbfResearchPanelModel";

export const DESCRIBE_DEBOUNCE_MS = 300;
export const BAND_BUDGET_MS = 1500;
export const CLIENT_RESULT_LIMIT = 8;
const ADHOC_CHANNEL = "ad_hoc_fallback";

export type ResearchRunStatus = "idle" | "running-nominal" | "band-pending" | "complete" | "cancelled" | "stale" | "error";
export type ResearchDescribeStatus = "idle" | "checking" | "ready" | "error";

export interface ResearchRunError {
  reasonCode: string | null;
  message: string | null;
  problems: ResearchProblem[];
  timeoutKind?: string | null;
}

export interface ResearchDescribeState {
  status: ResearchDescribeStatus;
  /** Alloy the held response was computed for; a response is never shown for another alloy. */
  alloyKey: string | null;
  /** Identity key the answer belongs to; a response for another key is never applied. */
  key: string | null;
  response: ResearchDescribeResponse | null;
  error: ResearchRunError | null;
}

export interface ResearchRunState {
  status: ResearchRunStatus;
  generation: number;
  /** Identity fixed at Run: process subset, property context, options. */
  identity: string | null;
  input: ResearchHostInput | null;
  requestKey: string | null;
  nominal: ResearchRunResponse | null;
  result: ResearchRunResponse | null;
  progress: { armsDone: number; armsTotal: number } | null;
  cache: ResearchRunResponse["cache"] | null;
  channel: string | null;
  error: ResearchRunError | null;
}

export interface ResearchHostState {
  input: ResearchHostInput | null;
  alloyKey: string | null;
  identity: string | null;
  describe: ResearchDescribeState;
  run: ResearchRunState;
}

interface FinishedResult {
  identity: string;
  input: ResearchHostInput;
  nominal: ResearchRunResponse;
  result: ResearchRunResponse;
}

interface ResearchStoreState {
  optionsByAlloy: Record<string, AlloyOptions>;
  hosts: Record<ResearchHostId, ResearchHostState>;
  finished: FinishedResult[];
  /** Set when the last preset change cleared vapour overrides, per alloy (3.3 rule 5). */
  presetCleared: Record<string, boolean>;

  setOption: (alloyKey: string, module: OptionModule, key: string, value: OptionValue | undefined) => void;
  setRange: (alloyKey: string, module: OptionModule, key: string, range: { min: number; max: number } | undefined) => void;
  /** Change a vapour preset: the module's vapour overrides and ranges are cleared with it. */
  setVapourPreset: (alloyKey: string, preset: string | undefined) => void;
  resetControl: (alloyKey: string, module: OptionModule, key: string) => void;
  resetAlloyOptions: (alloyKey: string) => void;

  syncHost: (host: ResearchHostId, input: ResearchHostInput) => void;
  run: (host: ResearchHostId) => Promise<void>;
  cancel: (host: ResearchHostId) => void;
  retry: (host: ResearchHostId) => void;
  unmountHost: (host: ResearchHostId) => void;
  /** Test and demo support: forget every host, option and finished result. */
  reset: () => void;
}

const emptyDescribe = (): ResearchDescribeState => ({ status: "idle", alloyKey: null, key: null, response: null, error: null });
const emptyRun = (generation = 0): ResearchRunState => ({
  status: "idle", generation, identity: null, input: null, requestKey: null, nominal: null, result: null,
  progress: null, cache: null, channel: null, error: null,
});
const emptyHost = (): ResearchHostState => ({ input: null, alloyKey: null, identity: null, describe: emptyDescribe(), run: emptyRun() });
const initialHosts = (): Record<ResearchHostId, ResearchHostState> => ({ "melt-pool": emptyHost(), "build-job": emptyHost() });

// Transport bookkeeping that must not trigger renders.
const runControllers: Partial<Record<ResearchHostId, AbortController>> = {};
const describeControllers: Partial<Record<ResearchHostId, AbortController>> = {};
const describeTimers: Partial<Record<ResearchHostId, ReturnType<typeof setTimeout>>> = {};
const describeCache = new Map<string, ResearchDescribeResponse>();
const requestCounters: Record<ResearchHostId, number> = { "melt-pool": 0, "build-job": 0 };

function nextRequestId(host: ResearchHostId): string {
  requestCounters[host] += 1;
  return `${host}:${requestCounters[host]}`;
}

function isAbort(err: unknown): boolean {
  return err instanceof Error && err.name === "AbortError";
}

function errorOf(outcome: ResearchOutcome): ResearchRunError | null {
  switch (outcome.kind) {
    case "refused": return { reasonCode: outcome.reasonCode, message: null, problems: outcome.problems };
    case "failed": return { reasonCode: outcome.reasonCode, message: null, problems: [] };
    case "timeout": return { reasonCode: "RESEARCH_TIMEOUT", message: null, problems: [], timeoutKind: outcome.timeoutKind };
    case "http-error": return { reasonCode: null, message: outcome.httpStatus === 0 ? outcome.message : `HTTP ${outcome.httpStatus}: ${outcome.message}`, problems: [] };
    case "malformed": return { reasonCode: "RESPONSE_MALFORMED", message: outcome.message, problems: [] };
    case "superseded": return { reasonCode: "REQUEST_SUPERSEDED", message: null, problems: [] };
    default: return null;
  }
}

export function isResearchRunnable(host: ResearchHostState): boolean {
  return host.describe.status === "ready"
    && host.describe.key === host.identity
    && host.describe.response !== null
    && host.describe.response.problems.length === 0;
}

function baseRequest(host: ResearchHostId, stage: ResearchStage, input: ResearchHostInput, options: AlloyOptions): ResearchRequest {
  return {
    schemaVersion: RESEARCH_ROUTE_SCHEMA_REQUEST,
    supersedeKey: supersedeKeyFor(host),
    clientRequestId: nextRequestId(host),
    stage,
    process: toResearchProcess(input),
    propertyContext: input.propertyContext,
    researchOptions: buildResearchOptions(options),
    sender: "research-panel",
  };
}

export const useLpbfResearchModelStore = create<ResearchStoreState>((set, get) => {
  const patchHost = (host: ResearchHostId, patch: (h: ResearchHostState) => ResearchHostState) =>
    set((s) => ({ hosts: { ...s.hosts, [host]: patch(s.hosts[host]) } }));

  const optionsFor = (alloyKey: string): AlloyOptions => get().optionsByAlloy[alloyKey] ?? emptyAlloyOptions();

  const isCurrentRun = (host: ResearchHostId, generation: number) => get().hosts[host].run.generation === generation;

  function abortRun(host: ResearchHostId) {
    runControllers[host]?.abort();
    delete runControllers[host];
  }

  function applyFinished(host: ResearchHostId, hit: FinishedResult) {
    patchHost(host, (h) => ({
      ...h,
      run: {
        ...emptyRun(h.run.generation + 1), status: "complete", identity: hit.identity, input: hit.input,
        requestKey: hit.result.requestKey, nominal: hit.nominal, result: hit.result,
        progress: { armsDone: hit.result.progress.armsDone, armsTotal: hit.result.progress.armsTotal },
        cache: hit.result.cache, channel: hit.result.channel ?? null,
      },
    }));
  }

  // ---- describe -------------------------------------------------------------------------------------------------

  async function sendDescribe(host: ResearchHostId, identity: string, retried = false): Promise<void> {
    const h = get().hosts[host];
    if (!h.input || !h.alloyKey || h.identity !== identity) return;
    describeControllers[host]?.abort();
    const controller = new AbortController();
    describeControllers[host] = controller;
    const request = baseRequest(host, "describe", h.input, optionsFor(h.alloyKey));
    let outcome: ResearchOutcome;
    try {
      outcome = await pythonComputationService.solveLpbfResearchModels(request, controller.signal);
    } catch (err) {
      if (isAbort(err)) return;
      outcome = { kind: "http-error", httpStatus: 0, message: err instanceof Error ? err.message : "Network request failed." };
    }
    if (get().hosts[host].identity !== identity || controller.signal.aborted) return;
    if (outcome.kind === "superseded") return; // a newer request of this panel owns the lane
    if (outcome.kind === "refused" && outcome.reasonCode === "RESEARCH_CODE_STALE" && !retried) {
      return sendDescribe(host, identity, true); // 13.7 item 2: the lane was recycled; retry once
    }
    if (outcome.kind === "describe" && outcome.response.clientRequestId === request.clientRequestId) {
      describeCache.set(identity, outcome.response);
      while (describeCache.size > CLIENT_RESULT_LIMIT) describeCache.delete(describeCache.keys().next().value as string);
      patchHost(host, (cur) => ({ ...cur, describe: { status: "ready", alloyKey: cur.alloyKey, key: identity, response: outcome.response, error: null } }));
      return;
    }
    const error = errorOf(outcome) ?? { reasonCode: "RESPONSE_MALFORMED", message: null, problems: [] };
    patchHost(host, (cur) => ({ ...cur, describe: { status: "error", alloyKey: cur.alloyKey, key: identity, response: null, error } }));
  }

  function scheduleDescribe(host: ResearchHostId, identity: string, immediate: boolean) {
    clearTimeout(describeTimers[host]);
    delete describeTimers[host];
    describeControllers[host]?.abort();
    const cached = describeCache.get(identity);
    if (cached) {
      patchHost(host, (h) => ({ ...h, describe: { status: "ready", alloyKey: h.alloyKey, key: identity, response: cached, error: null } }));
      return;
    }
    // Keep the last answer of the same alloy visible while checking, so the inputs do not unmount under the cursor.
    patchHost(host, (h) => ({
      ...h,
      describe: { status: "checking", alloyKey: h.alloyKey, key: identity, response: h.describe.alloyKey === h.alloyKey ? h.describe.response : null, error: null },
    }));
    if (immediate) { void sendDescribe(host, identity); return; }
    describeTimers[host] = setTimeout(() => { delete describeTimers[host]; void sendDescribe(host, identity); }, DESCRIBE_DEBOUNCE_MS);
  }

  // ---- reconcile: input or option change -------------------------------------------------------------------------

  function reconcile(host: ResearchHostId, first = false) {
    const h = get().hosts[host];
    if (!h.input || !h.alloyKey) return;
    const identity = identityKey(h.input, optionsFor(h.alloyKey));
    const identityChanged = identity !== h.identity;
    if (identityChanged) patchHost(host, (cur) => ({ ...cur, identity }));

    const run = get().hosts[host].run;
    const hit = get().finished.find((f) => f.identity === identity);
    if (hit && (run.status === "idle" || run.status === "stale")) {
      applyFinished(host, hit); // same inputs as a finished result: no rerun (4.5)
    } else if (run.status !== "idle" && run.status !== "stale" && run.identity !== identity) {
      // Any change of a run-identity input hides every research value at once (4.3 item 4).
      abortRun(host);
      if (hit) applyFinished(host, hit);
      else patchHost(host, (cur) => ({ ...cur, run: { ...cur.run, generation: cur.run.generation + 1, status: "stale" } }));
    }
    const d = get().hosts[host].describe;
    if (d.key !== identity || (d.status === "error" && identityChanged)) scheduleDescribe(host, identity, first || d.key === null);
  }

  function reconcileAlloy(alloyKey: string) {
    for (const host of ["melt-pool", "build-job"] as ResearchHostId[]) {
      if (get().hosts[host].alloyKey === alloyKey) reconcile(host);
    }
  }

  function editOptions(alloyKey: string, edit: (o: AlloyOptions) => AlloyOptions) {
    set((s) => ({ optionsByAlloy: { ...s.optionsByAlloy, [alloyKey]: edit(s.optionsByAlloy[alloyKey] ?? emptyAlloyOptions()) } }));
    reconcileAlloy(alloyKey);
  }

  const without = <T>(rec: Record<string, T>, key: string): Record<string, T> => {
    const copy = { ...rec };
    delete copy[key];
    return copy;
  };

  // ---- run ------------------------------------------------------------------------------------------------------

  async function send(host: ResearchHostId, request: ResearchRequest, signal: AbortSignal): Promise<{ outcome: ResearchOutcome; id: string } | null> {
    let retried = false;
    for (;;) {
      let outcome: ResearchOutcome;
      try {
        outcome = await pythonComputationService.solveLpbfResearchModels(request, signal);
      } catch (err) {
        if (isAbort(err) || signal.aborted) return null;
        return { id: request.clientRequestId, outcome: { kind: "http-error", httpStatus: 0, message: err instanceof Error ? err.message : "Network request failed." } };
      }
      if (signal.aborted) return null;
      if (outcome.kind === "refused" && outcome.reasonCode === "RESEARCH_CODE_STALE" && !retried) {
        retried = true; // 13.7 item 2 (R-TR-13): one automatic retry on the recycled lane
        request = { ...request, clientRequestId: nextRequestId(host) };
        continue;
      }
      return { outcome, id: request.clientRequestId };
    }
  }

  async function execRun(host: ResearchHostId): Promise<void> {
    const h = get().hosts[host];
    if (!h.input || !h.alloyKey || !h.identity) return;
    if (!isResearchRunnable(h)) return;
    const identity = h.identity;
    const input = h.input;
    const options = optionsFor(h.alloyKey);
    abortRun(host);
    const controller = new AbortController();
    runControllers[host] = controller;
    const generation = h.run.generation + 1;
    patchHost(host, (cur) => ({ ...cur, run: { ...emptyRun(generation), status: "running-nominal", identity, input } }));
    const fail = (outcome: ResearchOutcome | null, message?: ResearchRunError) => {
      if (!isCurrentRun(host, generation)) return;
      const error = message ?? (outcome ? errorOf(outcome) : null) ?? { reasonCode: "RESPONSE_MALFORMED", message: null, problems: [] };
      patchHost(host, (cur) => ({ ...cur, run: { ...cur.run, status: "error", error } }));
    };

    // Stage 1: nominal.
    const nominalRequest = baseRequest(host, "nominal", input, options);
    const sentNominal = await send(host, nominalRequest, controller.signal);
    if (sentNominal === null || !isCurrentRun(host, generation)) return;
    const nominalOutcome = sentNominal.outcome;
    if (nominalOutcome.kind !== "run" || nominalOutcome.response.stage !== "nominal" || nominalOutcome.response.clientRequestId !== sentNominal.id) {
      return fail(nominalOutcome.kind === "run" ? { kind: "malformed", message: "The response did not match the request that was sent and was not used." } : nominalOutcome);
    }
    const nominal = nominalOutcome.response;
    if (nominal.researchModels === null) return fail(null);
    patchHost(host, (cur) => ({
      ...cur,
      run: {
        ...cur.run, status: "band-pending", requestKey: nominal.requestKey, nominal,
        progress: { armsDone: nominal.progress.armsDone, armsTotal: nominal.progress.armsTotal },
        cache: nominal.cache, channel: nominal.channel ?? null,
      },
    }));

    // Stage 2: band chunks, one after another (each awaited). A null budget is for the ad-hoc path only (16.2 item 2).
    let previousCache = nominal.cache.cacheInstanceId;
    let previousDone = nominal.progress.armsDone;
    let useNullBudget = nominal.channel === ADHOC_CHANNEL;
    let nullBudgetSent = false;
    for (;;) {
      if (!isCurrentRun(host, generation)) return;
      const request = baseRequest(host, "band", input, options);
      request.timeBudgetMs = useNullBudget ? null : BAND_BUDGET_MS;
      if (useNullBudget) nullBudgetSent = true;
      const sent = await send(host, request, controller.signal);
      if (sent === null || !isCurrentRun(host, generation)) return;
      const outcome = sent.outcome;
      if (outcome.kind !== "run" || outcome.response.stage !== "band" || outcome.response.clientRequestId !== sent.id) {
        return fail(outcome.kind === "run" ? { kind: "malformed", message: "The response did not match the request that was sent and was not used." } : outcome);
      }
      const r = outcome.response;
      // A response is applied only when its identity is the one this run fixed (4.3 item 5).
      if (r.requestKey !== nominal.requestKey) {
        return fail(null, { reasonCode: "RESPONSE_MALFORMED", message: "The response belongs to a different request and was not used.", problems: [] });
      }
      if (r.progress.complete && r.researchModels !== null) {
        const finishedEntry: FinishedResult = { identity, input, nominal, result: r };
        set((s) => ({
          finished: [...s.finished.filter((f) => f.identity !== identity), finishedEntry].slice(-CLIENT_RESULT_LIMIT),
        }));
        patchHost(host, (cur) => ({
          ...cur,
          run: {
            ...cur.run, status: "complete", result: r, cache: r.cache, channel: r.channel ?? cur.run.channel,
            progress: { armsDone: r.progress.armsDone, armsTotal: r.progress.armsTotal },
          },
        }));
        return;
      }
      patchHost(host, (cur) => ({
        ...cur,
        run: { ...cur.run, progress: { armsDone: r.progress.armsDone, armsTotal: r.progress.armsTotal }, cache: r.cache, channel: r.channel ?? cur.run.channel },
      }));
      if (nullBudgetSent) {
        return fail(null, { reasonCode: "RESPONSE_MALFORMED", message: "The scenario range did not complete.", problems: [] });
      }
      if ((r.channel ?? null) === ADHOC_CHANNEL || r.cache.cacheInstanceId !== previousCache || r.progress.armsDone <= previousDone) {
        useNullBudget = true; // 3.5 rule 6: one null-budget request; never sent after Cancel (the generation check above)
      }
      previousCache = r.cache.cacheInstanceId;
      previousDone = r.progress.armsDone;
    }
  }

  return {
    optionsByAlloy: {},
    hosts: initialHosts(),
    finished: [],
    presetCleared: {},

    setOption: (alloyKey, module, key, value) => {
      editOptions(alloyKey, (o) => ({
        ...o,
        [module]: value === undefined ? without(o[module], key) : { ...o[module], [key]: value },
      }));
    },
    setRange: (alloyKey, module, key, range) => {
      editOptions(alloyKey, (o) => ({
        ...o,
        ranges: { ...o.ranges, [module]: range === undefined ? without(o.ranges[module], key) : { ...o.ranges[module], [key]: range } },
      }));
    },
    setVapourPreset: (alloyKey, preset) => {
      const current = optionsFor(alloyKey).surfaceBalance.vapourPreset;
      const changed = current !== preset;
      editOptions(alloyKey, (o) => {
        let surface = preset === undefined ? without(o.surfaceBalance, "vapourPreset") : { ...o.surfaceBalance, vapourPreset: preset };
        let ranges = o.ranges.surfaceBalance;
        if (changed) {
          for (const key of VAPOUR_OVERRIDE_KEYS) { surface = without(surface, key); ranges = without(ranges, key); }
        }
        return { ...o, surfaceBalance: surface, ranges: { ...o.ranges, surfaceBalance: ranges } };
      });
      set((s) => ({ presetCleared: { ...s.presetCleared, [alloyKey]: changed } }));
    },
    resetControl: (alloyKey, module, key) => {
      editOptions(alloyKey, (o) => ({
        ...o,
        [module]: without(o[module], key),
        ranges: { ...o.ranges, [module]: without(o.ranges[module], key) },
      }));
    },
    resetAlloyOptions: (alloyKey) => {
      editOptions(alloyKey, () => emptyAlloyOptions());
      set((s) => ({ presetCleared: { ...s.presetCleared, [alloyKey]: false } }));
    },

    syncHost: (host, input) => {
      const alloyKey = researchAlloyKey(input.material);
      const before = get().hosts[host];
      const first = before.input === null;
      set((s) => ({
        hosts: { ...s.hosts, [host]: { ...s.hosts[host], input, alloyKey } },
      }));
      reconcile(host, first);
    },

    run: (host) => execRun(host),

    cancel: (host) => {
      const h = get().hosts[host];
      if (h.run.status !== "running-nominal" && h.run.status !== "band-pending") return;
      abortRun(host); // the screen reacts at once; no message goes to the server
      patchHost(host, (cur) => ({ ...cur, run: { ...cur.run, generation: cur.run.generation + 1, status: "cancelled" } }));
    },

    retry: (host) => {
      const h = get().hosts[host];
      if (h.describe.status === "error" && h.identity) { scheduleDescribe(host, h.identity, true); return; }
      void execRun(host);
    },

    unmountHost: (host) => {
      clearTimeout(describeTimers[host]);
      delete describeTimers[host];
      describeControllers[host]?.abort();
      abortRun(host);
      patchHost(host, (cur) => ({
        ...cur,
        input: null, identity: null, alloyKey: null,
        describe: emptyDescribe(),
        run: cur.run.status === "running-nominal" || cur.run.status === "band-pending"
          ? { ...cur.run, generation: cur.run.generation + 1, status: "cancelled" }
          : cur.run,
      }));
    },

    reset: () => {
      for (const host of ["melt-pool", "build-job"] as ResearchHostId[]) {
        clearTimeout(describeTimers[host]);
        delete describeTimers[host];
        describeControllers[host]?.abort();
        abortRun(host);
        requestCounters[host] = 0;
      }
      describeCache.clear();
      set({ optionsByAlloy: {}, hosts: initialHosts(), finished: [], presetCleared: {} });
    },
  };
});
