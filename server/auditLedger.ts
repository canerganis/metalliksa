/**
 * Append-only, hash-chained run audit ledger (JSON lines). Tamper-evident, not tamper-proof and
 * not a signature: see docs/AUDIT_LEDGER.md. Local file I/O only, so it is safe in air-gap mode.
 */
import { createHash } from 'node:crypto';
import { appendFileSync, existsSync, mkdirSync, readFileSync } from 'node:fs';
import path from 'node:path';
import type { RunRecord } from './lpbfRunRepository';

export const AUDIT_SCHEMA_VERSION = 1;
export const GENESIS_HASH = '0'.repeat(64);

export interface AuditEntry {
  schemaVersion: number;
  seq: number;
  ts: string;
  kind: string;
  route: string;
  runId: string;
  inputSha256: string;
  resultSha256: string;
  model: string | null;
  implementationFingerprint: string | null;
  evidenceStatus: string;
  prevHash: string;
}
export type AuditEntryInput = Omit<AuditEntry, 'schemaVersion' | 'seq' | 'ts' | 'prevHash'> & { ts?: string };

export interface AuditVerification {
  entries: AuditEntry[];
  chainValid: boolean;
  /**
   * Seq of the first entry whose bytes no longer match the chain (an edited line), or of the first
   * unreadable or out-of-order line. The tamper is at or just after it. Null when valid.
   * That entry is excluded from `entries` when the chain is broken.
   */
  firstBrokenSeq: number | null;
  headHash: string;
  problem: string | null;
}

export const sha256Hex = (text: string): string => createHash('sha256').update(text, 'utf8').digest('hex');

/** Deterministic JSON: object keys sorted recursively, no whitespace. */
export function canonicalJson(value: unknown): string {
  if (value === null || typeof value !== 'object') {
    if (typeof value === 'number' && !Number.isFinite(value)) throw new Error('Non-finite number is not canonical JSON');
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) return `[${value.map(v => canonicalJson(v === undefined ? null : v)).join(',')}]`;
  const object = value as Record<string, unknown>;
  const parts = Object.keys(object).sort().filter(k => object[k] !== undefined)
    .map(k => `${JSON.stringify(k)}:${canonicalJson(object[k])}`);
  return `{${parts.join(',')}}`;
}

export const canonicalSha256 = (value: unknown): string => sha256Hex(canonicalJson(value));

/**
 * Default ledger location. An explicit METALLIKSA_AUDIT_DIR wins; otherwise the ledger lives under
 * the run archive root (<runRoot>/audit), so any test or deployment with its own run root is isolated.
 */
export function defaultLedgerPath(runRoot: string = path.resolve(process.env.METALLIKSA_LPBF_RUN_ROOT || '.lpbf-runs')): string {
  const dir = process.env.METALLIKSA_AUDIT_DIR ? path.resolve(process.env.METALLIKSA_AUDIT_DIR) : path.join(runRoot, 'audit');
  return path.join(dir, 'ledger.jsonl');
}

function readLines(file: string): string[] {
  if (!existsSync(file)) return [];
  return readFileSync(file, 'utf8').split('\n').filter(line => line.length > 0);
}

export class AuditLedger {
  private queue: Promise<unknown> = Promise.resolve();
  /** Appends that failed in this process (recordRunAudit is fail-open). Reported by the endpoint. */
  failedAppends = 0;
  constructor(private readonly file: string = defaultLedgerPath()) {}

  /** Appends are serialised in-process; the seq and prevHash are read from the file tail under that queue. */
  append(input: AuditEntryInput): Promise<AuditEntry> {
    const run = this.queue.then(() => this.appendNow(input));
    this.queue = run.catch(() => undefined);
    return run;
  }

  private appendNow(input: AuditEntryInput): AuditEntry {
    mkdirSync(path.dirname(this.file), { recursive: true });
    const lines = readLines(this.file);
    const last = lines.length ? lines[lines.length - 1] : null;
    let seq = 1;
    if (last !== null) {
      let previous: AuditEntry;
      try { previous = JSON.parse(last); } catch { throw new Error('Audit ledger tail is unreadable; refusing to append'); }
      if (!Number.isSafeInteger(previous.seq)) throw new Error('Audit ledger tail has no valid seq; refusing to append');
      seq = previous.seq + 1;
    }
    const { ts, ...rest } = input;
    const entry: AuditEntry = {
      schemaVersion: AUDIT_SCHEMA_VERSION, seq, ts: ts ?? new Date().toISOString(), ...rest,
      prevHash: last === null ? GENESIS_HASH : sha256Hex(last),
    };
    appendFileSync(this.file, `${JSON.stringify(entry)}\n`, 'utf8');
    return entry;
  }

  verify(): AuditVerification { return verifyLedgerFile(this.file); }
}

export function verifyLedgerFile(file: string): AuditVerification {
  const lines = readLines(file);
  const entries: AuditEntry[] = [];
  let expectedPrev = GENESIS_HASH;
  for (let i = 0; i < lines.length; i++) {
    let entry: AuditEntry;
    try { entry = JSON.parse(lines[i]); } catch {
      return { entries, chainValid: false, firstBrokenSeq: i + 1, headHash: expectedPrev, problem: `Line ${i + 1} is not valid JSON.` };
    }
    if (!entry || typeof entry !== 'object' || entry.seq !== i + 1) {
      return { entries, chainValid: false, firstBrokenSeq: i + 1, headHash: expectedPrev, problem: `Line ${i + 1} has a missing or out-of-order seq.` };
    }
    if (entry.prevHash !== expectedPrev) {
      // The bytes of the previous line no longer match what this entry recorded (edit or deletion).
      const broken = Math.max(1, i);
      return { entries: entries.filter(e => e.seq < broken), chainValid: false, firstBrokenSeq: broken, headHash: expectedPrev,
        problem: `Entry ${i + 1} does not chain to the previous line; tamper at or just after seq ${broken}.` };
    }
    entries.push(entry);
    expectedPrev = sha256Hex(lines[i]);
  }
  return { entries, chainValid: true, firstBrokenSeq: null, headHash: expectedPrev, problem: null };
}

const ledgers = new Map<string, AuditLedger>();
/** One ledger instance per file path, so appends to the same file stay serialised. Path is resolved at call time. */
export function sharedAuditLedger(file: string = defaultLedgerPath()): AuditLedger {
  let ledger = ledgers.get(file);
  if (!ledger) { ledger = new AuditLedger(file); ledgers.set(file, ledger); }
  return ledger;
}

const asString = (value: unknown): string | null => (typeof value === 'string' && value ? value : null);

/** Single hook for a persisted run. Never throws: an audit failure must not lose the saved run, but it is logged. */
export async function recordRunAudit(record: RunRecord, ledger: AuditLedger,
  route = 'POST /api/lpbf/runs/import'): Promise<AuditEntry | null> {
  try {
    const capture = record.document.capture;
    let result: any = null;
    try { result = JSON.parse(capture.resultJson); } catch { /* hashed below as raw text */ }
    let input: unknown;
    try { input = JSON.parse(capture.inputJson); } catch { input = capture.inputJson; }
    return await ledger.append({
      kind: 'lpbf-run-import', route, runId: record.document.runId,
      inputSha256: canonicalSha256(input),
      resultSha256: result === null ? sha256Hex(capture.resultJson) : canonicalSha256(result),
      model: asString(result?.solver?.id) ?? record.runKind,
      implementationFingerprint: asString(result?.provenance?.implementationHash),
      evidenceStatus: record.evidenceStatus,
    });
  } catch (error) {
    ledger.failedAppends += 1;
    console.error('[Audit ledger] append failed:', error instanceof Error ? error.message : error);
    return null;
  }
}
