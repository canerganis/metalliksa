import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { pythonComputationService } from "../../src/services/pythonComputationService";
import {
  isResearchDescribeResponse,
  isResearchRunResponse,
  type ResearchDescribeResponse,
  type ResearchOutcome,
  type ResearchRequest,
  type ResearchRunResponse,
} from "../../src/types/lpbfResearchModels";
import type { ResearchHostInput } from "../../src/utils/lpbfResearchPanelModel";

// Real Python output of python/lpbf_research_models.py for Ti-6Al-4V (200 W, 800 mm/s, 80 um, 20 C, nominal property
// context), pruned: `describe` is whole; `band` is the complete band response with every module kept but only a few
// fields, arms and notes per module. The runtime reads none of it; the tests only exercise rendering and the state
// machine on a response of the real shape. Regenerate by sending the stage requests to the route and pruning the same way.
const RAW = JSON.parse(readFileSync(new URL("../fixtures/lpbf-research-panel-ti64-v1.json", import.meta.url), "utf8")) as {
  describe: unknown;
  band: unknown;
};

/** One cache instance for a whole fake run; a different id on a chunk simulates a lane recycle. */
export const CACHE_ID = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";

export const TI64_INPUT: ResearchHostInput = {
  material: "Ti-6Al-4V",
  laserPower_W: 200,
  scanSpeed_mm_s: 800,
  beamDiameter_um: 80,
  preheatTemp_C: 20,
  propertyContext: { kind: "nominal" },
};

// Render the current Python text tables, while preserving the historical numeric fixtures byte for byte.
// No evaluator or served module is imported. PYTHON_EXECUTABLE can select the project's scientific runtime.
const wording = JSON.parse(execFileSync(process.env.PYTHON_EXECUTABLE ?? "python", ["-B", "-c",
  "import sys,json;sys.path.insert(0,'python');import lpbf_research_codes as c;print(json.dumps({'labels':dict(c.LEAF_LABELS),'sentences':c.SENTENCES}))"],
  { encoding: "utf8", cwd: new URL("../../", import.meta.url) }).toString()) as { labels: Record<string, string>; sentences: Record<string, string> };

const clone = <T>(value: T): T => JSON.parse(JSON.stringify(value)) as T;

export function describeResponse(clientRequestId: string, patch?: Partial<ResearchDescribeResponse>): ResearchDescribeResponse {
  const raw = clone(RAW.describe) as ResearchDescribeResponse;
  const response = { ...raw, clientRequestId, labels: { ...raw.labels, ...wording.labels }, sentences: wording.sentences, ...patch };
  if (!isResearchDescribeResponse(response)) throw new Error("describe fixture no longer passes the guard");
  return response;
}

export function completeResponse(clientRequestId: string): ResearchRunResponse {
  const raw = clone(RAW.band) as ResearchRunResponse;
  const response = { ...raw, clientRequestId, labels: { ...raw.labels, ...wording.labels } };
  if (!isResearchRunResponse(response)) throw new Error("band fixture no longer passes the guard");
  return response;
}

/** The nominal stage of the same request: every band pending, no scenario range yet. */
export function nominalResponse(clientRequestId: string, total = 79): ResearchRunResponse {
  const r = completeResponse(clientRequestId);
  r.stage = "nominal";
  r.progress = { armsDone: 7, armsTotal: total, complete: false };
  r.cache = { cacheInstanceId: CACHE_ID, armsHit: 0, armsComputed: 7 };
  for (const container of Object.values(r.researchModels ?? {})) {
    if (typeof container !== "object" || container === null || !("fields" in container)) continue;
    for (const field of Object.values(container.fields)) {
      if (!field.band) continue;
      for (const leaf of [field.band.min, field.band.max, field.band.successfulArms, field.band.totalArms]) {
        leaf.value = null; leaf.reasonCode = "BAND_PENDING";
      }
      field.band.completeness = "pending";
      field.band.minArmId = null; field.band.maxArmId = null; field.band.minArmLabel = null; field.band.maxArmLabel = null;
    }
    if (container.band) container.band.completeness = "pending";
  }
  if (!isResearchRunResponse(r)) throw new Error("nominal fixture no longer passes the guard");
  return r;
}

/** An incomplete band chunk: progress only, no block. */
export function chunkResponse(clientRequestId: string, armsDone: number, cacheInstanceId = CACHE_ID, total = 79): ResearchRunResponse {
  const r = completeResponse(clientRequestId);
  r.researchModels = null;
  r.progress = { armsDone, armsTotal: total, complete: false };
  r.cache = { cacheInstanceId, armsHit: 0, armsComputed: armsDone };
  delete r.digests;
  return r;
}

export function finalResponse(clientRequestId: string, cacheInstanceId = CACHE_ID): ResearchRunResponse {
  const r = completeResponse(clientRequestId);
  r.cache = { ...r.cache, cacheInstanceId };
  return r;
}

export const asOutcome = (response: ResearchRunResponse | ResearchDescribeResponse): ResearchOutcome =>
  response.stage === "describe" ? { kind: "describe", response: response as ResearchDescribeResponse } : { kind: "run", response: response as ResearchRunResponse };

type Handler = (request: ResearchRequest, signal: AbortSignal | undefined) => ResearchOutcome | Promise<ResearchOutcome>;

/** Replaces pythonComputationService.solveLpbfResearchModels for one test; `restore()` puts the original back. */
export class FakeResearchEngine {
  readonly requests: ResearchRequest[] = [];
  private readonly handlers: Partial<Record<string, Handler>> = {};
  private readonly original = pythonComputationService.solveLpbfResearchModels;

  constructor() {
    pythonComputationService.solveLpbfResearchModels = async (request, signal) => {
      this.requests.push(JSON.parse(JSON.stringify(request)) as ResearchRequest);
      if (signal?.aborted) throw Object.assign(new Error("aborted"), { name: "AbortError" });
      const handler = this.handlers[request.stage];
      if (!handler) throw new Error(`no handler for ${request.stage}`);
      const result = handler(request, signal);
      if (!signal) return result;
      return new Promise<ResearchOutcome>((resolve, reject) => {
        const onAbort = () => reject(Object.assign(new Error("aborted"), { name: "AbortError" }));
        signal.addEventListener("abort", onAbort, { once: true });
        Promise.resolve(result).then(resolve, reject).finally(() => signal.removeEventListener("abort", onAbort));
      });
    };
  }

  on(stage: "describe" | "nominal" | "band", handler: Handler): this {
    this.handlers[stage] = handler;
    return this;
  }

  byStage(stage: string): ResearchRequest[] {
    return this.requests.filter((r) => r.stage === stage);
  }

  restore(): void {
    pythonComputationService.solveLpbfResearchModels = this.original;
  }
}

export const tick = (ms = 0) => new Promise<void>((resolve) => setTimeout(resolve, ms));

export async function until(predicate: () => boolean, label: string, timeoutMs = 3000): Promise<void> {
  const start = Date.now();
  while (!predicate()) {
    if (Date.now() - start > timeoutMs) throw new Error(`timed out waiting for ${label}`);
    await tick(5);
  }
}

/** A controllable promise, for holding a request in flight. */
export function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((r) => { resolve = r; });
  return { promise, resolve };
}
