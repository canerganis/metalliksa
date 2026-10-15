/** Person-started P8 batch sender. Contract 14.4, 14.7 and Revision 5 (16.2). */
import { randomBytes } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { classifyResearchAnswer, RESEARCH_ROUTE_SCHEMA_REQUEST, type ResearchRequest, type ResearchOutcome, type ResearchRunResponse } from "../src/types/lpbfResearchModels";

export type BatchCondition = Pick<ResearchRequest, "process" | "propertyContext" | "researchOptions" | "relay">;
export const BATCH_WORDING = {
  estimate: "{n} conditions, estimated {seconds} s using the measured default-manifest cold nominal plus band time (11.5 s per condition, P8 phase C). This is an estimate, not a time limit. Press Ctrl+C to cancel.",
  cap: "Batch exceeds the {max} condition limit.",
  max: "maxRequests must be an integer from 1 to 256.",
  runId: "runId must contain 8 to 32 lowercase letters or digits.",
  input: "Input must be a nonempty array of research request bodies.",
  relayOptions: "A relay request cannot include researchOptions.",
  cancelled: "Batch cancelled. No further requests will be sent.",
  timeout: "Research timeout ({kind}).",
  failed: "Research request failed ({kind}).",
  mismatch: "Research response does not match the request.",
  progress: "Research progress stalled on the persistent lane. No null-budget request was sent.",
  incomplete: "The null-budget request did not complete.",
  relay: "The complete response has no valid relay within the 16000-character limit.",
  tooLarge: "Research payload exceeds its transport size limit.",
  flag: "Unknown argument or missing value: {flag}.",
  required: "Use --input FILE --output-dir DIR [--url URL] [--max-requests N] [--run-id ID].",
  complete: "Batch complete: {n} conditions. Full responses saved.",
  partial: "Batch incomplete. Files already saved are partial output and must not be used as a complete relay.",
} as const;
const message = (s: string, args: Record<string, string | number>) => s.replace(/\{(\w+)\}/g, (m, k) => String(args[k] ?? m));
const validateMax = (n: number) => { if (!Number.isInteger(n) || n < 1 || n > 256) throw new Error(BATCH_WORDING.max); };
const validateId = (s: string) => { if (!/^[a-z0-9]{8,32}$/.test(s)) throw new Error(BATCH_WORDING.runId); };

export interface BatchOptions {
  runId: string;
  maxRequests?: number;
  signal?: AbortSignal;
  send: (r: ResearchRequest, signal?: AbortSignal) => Promise<ResearchOutcome>;
  write: (ordinal: number, response: ResearchRunResponse) => Promise<void>;
  log: (s: string) => void;
}

export async function runBatch(conditions: readonly BatchCondition[], options: BatchOptions): Promise<void> {
  const max = options.maxRequests ?? 48;
  validateMax(max); validateId(options.runId);
  if (!Array.isArray(conditions) || !conditions.length || conditions.some((c) => !c || !c.process || !c.propertyContext)) throw new Error(BATCH_WORDING.input);
  if (conditions.length > max) throw new Error(message(BATCH_WORDING.cap, { max }));
  for (const c of conditions) if (c.relay && c.researchOptions !== undefined) throw new Error(BATCH_WORDING.relayOptions);
  options.log(message(BATCH_WORDING.estimate, { n: conditions.length, seconds: (conditions.length * 11.5).toFixed(1) }));
  const checkCancel = () => { if (options.signal?.aborted) throw new Error(BATCH_WORDING.cancelled); };
  let counter = 0;
  const request = (c: BatchCondition, stage: "nominal" | "band", budget = false): ResearchRequest => ({
    schemaVersion: RESEARCH_ROUTE_SCHEMA_REQUEST, sender: "batch-client",
    supersedeKey: `p8-research:batch:${options.runId}`, clientRequestId: `${options.runId}:${++counter}`,
    stage, process: c.process, propertyContext: c.propertyContext,
    ...(c.researchOptions !== undefined ? { researchOptions: c.researchOptions } : {}),
    ...(c.relay !== undefined ? { relay: c.relay } : {}),
    ...(stage === "band" ? { timeBudgetMs: budget ? null : 1500 } : {}),
  });
  const send = async (r: ResearchRequest): Promise<ResearchRunResponse> => {
    for (let retry = 0; ; retry++) {
      checkCancel();
      const outcome = await options.send(r, options.signal);
      checkCancel();
      if (outcome.kind === "timeout") {
        if (retry === 0 && r.timeBudgetMs !== null && (outcome.timeoutKind === "queue" || outcome.timeoutKind === "reply")) {
          r = { ...r, clientRequestId: `${options.runId}:${++counter}` }; continue;
        }
        throw new Error(message(BATCH_WORDING.timeout, { kind: outcome.timeoutKind ?? "unknown" }));
      }
      if (outcome.kind !== "run") throw new Error(message(BATCH_WORDING.failed, { kind: outcome.kind }));
      if (outcome.response.clientRequestId !== r.clientRequestId || outcome.response.stage !== r.stage) throw new Error(BATCH_WORDING.mismatch);
      return outcome.response;
    }
  };
  // Each await covers both the HTTP response and the output write before advancing.
  for (let i = 0; i < conditions.length; i++) {
    const c = conditions[i];
    const nominal = await send(request(c, "nominal"));
    if (!nominal.researchModels) throw new Error(BATCH_WORDING.mismatch);
    let cache = nominal.cache.cacheInstanceId;
    let done = nominal.progress.armsDone;
    let nullBudget = nominal.channel === "ad_hoc_fallback";
    for (;;) {
      const r = await send(request(c, "band", nullBudget));
      if (r.requestKey !== nominal.requestKey) throw new Error(BATCH_WORDING.mismatch);
      if (r.progress.complete && r.researchModels) {
        if (c.relay && (!r.relay || r.relay.kind !== "blind-freeze-v2" || r.relay.subsetJson.length > 16000)) throw new Error(BATCH_WORDING.relay);
        checkCancel();
        await options.write(i, r); // subsetJson remains an opaque string, including float formatting.
        break;
      }
      if (nullBudget) throw new Error(BATCH_WORDING.incomplete);
      const changed = r.cache.cacheInstanceId !== cache;
      nullBudget = changed || r.channel === "ad_hoc_fallback";
      if (!nullBudget && r.progress.armsDone <= done) throw new Error(BATCH_WORDING.progress);
      cache = r.cache.cacheInstanceId; done = r.progress.armsDone;
    }
  }
}

export function parseArgs(args: string[]) {
  const values: Record<string, string> = {};
  const flags = ["--input", "--output-dir", "--url", "--max-requests", "--run-id"];
  for (let i = 0; i < args.length; i += 2) {
    if (!flags.includes(args[i]) || !args[i + 1] || args[i + 1].startsWith("--")) throw new Error(message(BATCH_WORDING.flag, { flag: args[i] }));
    values[args[i]] = args[i + 1];
  }
  const maxRequests = Number(values["--max-requests"] ?? 48); validateMax(maxRequests);
  const runId = values["--run-id"] ?? randomBytes(8).toString("hex"); validateId(runId);
  if (!values["--input"] || !values["--output-dir"]) throw new Error(BATCH_WORDING.required);
  return { input: values["--input"], outputDir: values["--output-dir"], url: values["--url"] ?? "http://localhost:3000", maxRequests, runId };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const conditions: BatchCondition[] = JSON.parse(await readFile(args.input, "utf8"));
  const controller = new AbortController();
  const cancel = () => controller.abort();
  process.on("SIGINT", cancel);
  try {
    await runBatch(conditions, {
      ...args, signal: controller.signal, log: console.log,
      send: async (request, signal) => {
        const body = JSON.stringify(request);
        if (Buffer.byteLength(body, "utf8") > 65536) throw new Error(BATCH_WORDING.tooLarge);
        const response = await fetch(new URL("/api/python/lpbf-research-models", args.url), {
          method: "POST", body, signal,
          headers: { "Content-Type": "application/json", ...(process.env.METALLIKSA_TOKEN ? { Authorization: `Bearer ${process.env.METALLIKSA_TOKEN}` } : {}) },
        });
        const raw = await response.text();
        if (Buffer.byteLength(raw, "utf8") > 16 * 1024 * 1024) throw new Error(BATCH_WORDING.tooLarge);
        return classifyResearchAnswer(response.status, JSON.parse(raw));
      },
      write: async (i, r) => {
        await mkdir(args.outputDir, { recursive: true });
        // Exclusive creation preserves earlier runs and makes an incomplete run visible on failure.
        await writeFile(path.join(args.outputDir, `${args.runId}-${String(i).padStart(3, "0")}.json`), JSON.stringify(r) + "\n", { flag: "wx" });
      },
    });
    console.log(message(BATCH_WORDING.complete, { n: conditions.length }));
  } finally { process.off("SIGINT", cancel); }
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  main().catch((err: unknown) => { console.error(err instanceof Error ? err.message : String(err)); console.error(BATCH_WORDING.partial); process.exitCode = 1; });
}
