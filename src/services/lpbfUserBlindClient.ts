/**
 * Same-origin client of the user blind test (spec 3.2.1, 3.4 item 5). Preview, list and get go through
 * POST /api/lpbf/estimate; freeze, reveal, score, bundle and open are queued through POST /api/lpbf/jobs and followed
 * with one poll step per call (the component drives the steps with useVisiblePolling). Documents that hold predictions
 * or measurements are fetched only through the artifact route and checked against their declared sha256 in the browser
 * when SubtleCrypto exists. The browser attaches the Origin header itself; the server's same-origin guard is the CSRF
 * defence, so no other header is needed and no request leaves this origin.
 */
import {
  BLIND_REQUEST_SCHEMA,
  checkedBlindGet,
  checkedBlindJobResult,
  checkedBlindList,
  checkedBlindPreview,
  type BlindGet,
  type BlindJobType,
  type BlindList,
  type BlindPreview,
} from "../data/lpbfUserBlind";

export const HASH_CHECK_SKIPPED_NOTE = "Browser hash check unavailable on this connection; the worker checked the hash.";
export const HASHING_NEEDS_SECURE_NOTE = "Hashing needs https or localhost. Compute the SHA-256 of the targets file with sha256sum or certutil -hashfile <file> SHA256 and paste it.";

export type BlindErrorKind = "worker-unavailable" | "queue-full" | "too-large" | "refusal" | "job-failed" | "hash-mismatch" | "http" | "invalid-response";
/** Refusals show only `message` and `code`. Every other kind carries a fixed sentence written here. */
export class BlindClientError extends Error {
  readonly kind: BlindErrorKind;
  readonly code: string | null;
  readonly field: string | null;
  readonly retryAfterS: number | null;
  constructor(kind: BlindErrorKind, message: string, extra: { code?: string | null; field?: string | null; retryAfterS?: number | null } = {}) {
    super(message);
    this.name = "BlindClientError";
    this.kind = kind;
    this.code = extra.code ?? null;
    this.field = extra.field ?? null;
    this.retryAfterS = extra.retryAfterS ?? null;
  }
}

export type BlindPollResult =
  | { state: "pending"; status: string; progress: number | null }
  | { state: "completed"; result: unknown }
  | { state: "failed"; status: string; code: string | null; message: string };

export interface BlindClientDeps {
  fetch: (input: string, init?: RequestInit) => Promise<Response>;
  /** Evaluated at each call so a test can remove or add SubtleCrypto. */
  subtle: () => SubtleCrypto | undefined;
}
const defaultDeps: BlindClientDeps = {
  fetch: (input, init) => globalThis.fetch(input, init),
  subtle: () => globalThis.crypto?.subtle,
};

const isObj = (v: unknown): v is Record<string, unknown> => typeof v === "object" && v !== null && !Array.isArray(v);
const toHex = (buf: ArrayBuffer) => Array.from(new Uint8Array(buf), b => b.toString(16).padStart(2, "0")).join("");

export function bytesToBase64(bytes: Uint8Array): string {
  let binary = "";
  const step = 0x8000;
  for (let i = 0; i < bytes.length; i += step) binary += String.fromCharCode(...bytes.subarray(i, i + step));
  return btoa(binary);
}

export function createBlindClient(overrides: Partial<BlindClientDeps> = {}) {
  const deps: BlindClientDeps = { ...defaultDeps, ...overrides };
  const hasSubtle = () => deps.subtle() !== undefined;

  async function sha256Hex(bytes: Uint8Array): Promise<string | null> {
    const subtle = deps.subtle();
    if (!subtle) return null;
    return toHex(await subtle.digest("SHA-256", bytes as unknown as BufferSource));
  }

  async function errorFromResponse(res: Response): Promise<BlindClientError> {
    let body: unknown = null;
    try { body = await res.json(); } catch { body = null; }
    if (res.status === 422 && isObj(body) && body.errorKind === "validation" && isObj(body.error)) {
      const e = body.error;
      return new BlindClientError("refusal", typeof e.message === "string" ? e.message : "The request was refused.", {
        code: typeof e.code === "string" ? e.code : "VALIDATION", field: typeof e.field === "string" ? e.field : null,
      });
    }
    if (res.status === 503) {
      const retry = Number(res.headers.get("Retry-After"));
      return new BlindClientError("worker-unavailable", "The simulation worker is not available. Try again in a moment.", { retryAfterS: Number.isFinite(retry) && retry > 0 ? retry : null });
    }
    if (res.status === 413) return new BlindClientError("too-large", "The request is too large. Use a smaller file or split the campaign into blocks.");
    if (res.status === 400 && isObj(body) && typeof body.error === "string" && /queue full/i.test(body.error)) {
      return new BlindClientError("queue-full", "The simulation queue is full. Try again when a job has finished.");
    }
    return new BlindClientError("http", `The request failed (HTTP ${res.status}).`);
  }

  async function postJson(path: string, body: unknown, timeoutMs: number): Promise<unknown> {
    const res = await deps.fetch(path, {
      method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" }, cache: "no-store",
      body: JSON.stringify(body), signal: AbortSignal.timeout(timeoutMs),
    });
    if (!res.ok) throw await errorFromResponse(res);
    try { return await res.json(); } catch { throw new BlindClientError("invalid-response", "The reply could not be read."); }
  }

  function checked<T>(check: (v: unknown) => T, value: unknown): T {
    try { return check(value); } catch { throw new BlindClientError("invalid-response", "The reply did not match the expected document and was not used."); }
  }

  return {
    hasSubtleCrypto: hasSubtle,
    sha256Hex,

    async preview(metadata: unknown, inputsCsvBase64: string, inputsFileName: string): Promise<BlindPreview> {
      const doc = await postJson("/api/lpbf/estimate", { jobType: "user-blind-preview", schema: BLIND_REQUEST_SCHEMA, metadata, inputsCsvBase64, inputsFileName }, 25000);
      return checked(checkedBlindPreview, doc);
    },
    async list(page = 0, pageSize = 20): Promise<BlindList> {
      const doc = await postJson("/api/lpbf/estimate", { jobType: "user-blind-list", schema: BLIND_REQUEST_SCHEMA, page, pageSize }, 25000);
      return checked(checkedBlindList, doc);
    },
    async get(freezeKey: string): Promise<BlindGet> {
      const doc = await postJson("/api/lpbf/estimate", { jobType: "user-blind-get", schema: BLIND_REQUEST_SCHEMA, freezeKey }, 25000);
      return checked(checkedBlindGet, doc);
    },

    /** Queue one job. `payload` holds exactly the keys of PAYLOADS in python/lpbf_user_blind.py for the type. */
    async submit(jobType: BlindJobType, payload: Record<string, unknown>): Promise<string> {
      const doc = await postJson("/api/lpbf/jobs", { jobType, schema: BLIND_REQUEST_SCHEMA, ...payload }, 60000);
      if (!isObj(doc) || typeof doc.id !== "string" || !doc.id) throw new BlindClientError("invalid-response", "The queue reply did not name a job.");
      return doc.id;
    },

    /** One poll step. The caller schedules the next step (useVisiblePolling) and stops on `completed` or `failed`. */
    async pollJob(id: string, jobType: BlindJobType): Promise<BlindPollResult> {
      const res = await deps.fetch(`/api/lpbf/jobs/${encodeURIComponent(id)}`, { cache: "no-store", headers: { Accept: "application/json" }, signal: AbortSignal.timeout(25000) });
      if (!res.ok) throw await errorFromResponse(res);
      let job: unknown;
      try { job = await res.json(); } catch { throw new BlindClientError("invalid-response", "The job reply could not be read."); }
      if (!isObj(job) || typeof job.status !== "string") throw new BlindClientError("invalid-response", "The job reply could not be read.");
      if (job.status === "completed") return { state: "completed", result: checked(v => checkedBlindJobResult(jobType, v), job.result) };
      if (job.status === "failed" || job.status === "cancelled" || job.status === "timed_out") {
        // `error` is the fixed message of the closed code in `blindError`; nothing else from the job is shown.
        const code = typeof job.blindError === "string" ? job.blindError : null;
        const message = typeof job.error === "string" && job.error ? job.error : "The job did not finish.";
        return { state: "failed", status: job.status, code, message };
      }
      return { state: "pending", status: job.status, progress: typeof job.progress === "number" ? job.progress : null };
    },

    /**
     * Fetch a document through the artifact route of the job that wrote it and check its bytes against `expectedSha256`.
     * Without SubtleCrypto the check is skipped and `hashCheck` says so. A mismatch throws.
     */
    async fetchDocument(jobId: string, name: string, expectedSha256: string | null): Promise<{ bytes: Uint8Array; sha256: string | null; hashCheck: "matched" | "skipped" | "not-declared" }> {
      const res = await deps.fetch(`/api/lpbf/jobs/${encodeURIComponent(jobId)}/artifacts/${encodeURIComponent(name)}`, { cache: "no-store", signal: AbortSignal.timeout(60000) });
      if (!res.ok) throw await errorFromResponse(res);
      const bytes = new Uint8Array(await res.arrayBuffer());
      const actual = await sha256Hex(bytes);
      if (actual === null) return { bytes, sha256: null, hashCheck: "skipped" };
      if (expectedSha256 === null) return { bytes, sha256: actual, hashCheck: "not-declared" };
      if (actual !== expectedSha256) throw new BlindClientError("hash-mismatch", "The downloaded document does not match its declared SHA-256 and was not used.");
      return { bytes, sha256: actual, hashCheck: "matched" };
    },
  };
}

export const blindClient = createBlindClient();
export type BlindClient = ReturnType<typeof createBlindClient>;

/** Poll delay in ms after a pending step; null stops the poller. */
export function nextBlindPollDelay(result: BlindPollResult): number | null {
  return result.state === "pending" ? 1500 : null;
}

export function describeBlindError(error: unknown): string {
  if (error instanceof BlindClientError) {
    if (error.kind === "refusal") return `${error.message} (${error.code ?? "VALIDATION"})`;
    if (error.kind === "job-failed" && error.code) return `${error.message} (${error.code})`;
    if (error.kind === "worker-unavailable" && error.retryAfterS) return `${error.message} Retry after ${error.retryAfterS} s.`;
    return error.message;
  }
  return "The request could not be completed.";
}
