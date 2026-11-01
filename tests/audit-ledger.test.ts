import assert from 'node:assert/strict';
import { test } from 'node:test';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import express from 'express';
import { createServer } from 'node:http';
import { AuditLedger, GENESIS_HASH, defaultLedgerPath, canonicalJson, canonicalSha256, recordRunAudit, sha256Hex, type AuditEntryInput } from '../server/auditLedger';
import { createAuditLedgerRouter } from '../routes/auditLedger';

const sample = (runId: string): AuditEntryInput => ({
  kind: 'lpbf-run-import', route: 'POST /api/lpbf/runs/import', runId,
  inputSha256: canonicalSha256({ a: 1 }), resultSha256: canonicalSha256({ b: 2 }),
  model: 'test-solver', implementationFingerprint: 'f'.repeat(64), evidenceStatus: 'unvalidated-model',
});

function withLedger<T>(fn: (ledger: AuditLedger, file: string) => Promise<T> | T): Promise<T> | T {
  const dir = mkdtempSync(path.join(tmpdir(), 'audit-ledger-'));
  const file = path.join(dir, 'audit', 'ledger.jsonl');
  const done = () => rmSync(dir, { recursive: true, force: true });
  let result: Promise<T> | T;
  try { result = fn(new AuditLedger(file), file); } catch (e) { done(); throw e; }
  if (result instanceof Promise) return result.finally(done);
  done(); return result;
}

test('canonical hashing ignores key order and whitespace', () => {
  assert.equal(canonicalJson({ b: [1, { z: 1, a: 2 }], a: null }), '{"a":null,"b":[1,{"a":2,"z":1}]}');
  assert.equal(canonicalSha256({ x: 1, y: 2 }), canonicalSha256(JSON.parse('{ "y": 2,\n "x": 1 }')));
  assert.notEqual(canonicalSha256({ x: 1 }), canonicalSha256({ x: 2 }));
  assert.throws(() => canonicalJson({ x: Number.NaN }));
});

test('append builds a hash chain from the genesis hash', () => withLedger(async (ledger, file) => {
  const a = await ledger.append(sample('run-a'));
  const b = await ledger.append(sample('run-b'));
  assert.equal(a.seq, 1); assert.equal(b.seq, 2);
  assert.equal(a.prevHash, GENESIS_HASH);
  const lines = readFileSync(file, 'utf8').trim().split('\n');
  assert.equal(b.prevHash, sha256Hex(lines[0]));
  const v = ledger.verify();
  assert.equal(v.chainValid, true); assert.equal(v.firstBrokenSeq, null);
  assert.equal(v.entries.length, 2); assert.equal(v.headHash, sha256Hex(lines[1]));
}));

test('an empty or missing ledger verifies as valid', () => withLedger(ledger => {
  const v = ledger.verify();
  assert.equal(v.chainValid, true); assert.equal(v.entries.length, 0);
}));

test('editing an entry makes the chain invalid at that seq', () => withLedger(async (ledger, file) => {
  for (const id of ['r1', 'r2', 'r3', 'r4']) await ledger.append(sample(id));
  const lines = readFileSync(file, 'utf8').trim().split('\n');
  lines[1] = lines[1].replace('r2', 'rX');
  writeFileSync(file, `${lines.join('\n')}\n`);
  const v = ledger.verify();
  assert.equal(v.chainValid, false);
  assert.equal(v.firstBrokenSeq, 2);
  assert.deepEqual(v.entries.map(e => e.seq), [1], 'the edited entry and everything after it are not returned');
}));

test('default ledger path follows the run root unless METALLIKSA_AUDIT_DIR is set', () => {
  const saved = process.env.METALLIKSA_AUDIT_DIR; delete process.env.METALLIKSA_AUDIT_DIR;
  try {
    assert.equal(defaultLedgerPath(path.resolve('some-root')), path.join(path.resolve('some-root'), 'audit', 'ledger.jsonl'));
    process.env.METALLIKSA_AUDIT_DIR = path.resolve('elsewhere');
    assert.equal(defaultLedgerPath(path.resolve('some-root')), path.join(path.resolve('elsewhere'), 'ledger.jsonl'));
  } finally { if (saved === undefined) delete process.env.METALLIKSA_AUDIT_DIR; else process.env.METALLIKSA_AUDIT_DIR = saved; }
});

test('deleting a middle entry and garbage lines are detected', () => withLedger(async (ledger, file) => {
  for (const id of ['r1', 'r2', 'r3']) await ledger.append(sample(id));
  const lines = readFileSync(file, 'utf8').trim().split('\n');
  writeFileSync(file, `${[lines[0], lines[2]].join('\n')}\n`);
  assert.equal(ledger.verify().chainValid, false);
  writeFileSync(file, `${lines[0]}\nnot json\n`);
  const v = ledger.verify();
  assert.equal(v.chainValid, false); assert.equal(v.firstBrokenSeq, 2);
}));

test('append refuses to extend a ledger with an unreadable tail', () => withLedger(async (ledger, file) => {
  await ledger.append(sample('r1'));
  writeFileSync(file, 'garbage\n');
  await assert.rejects(ledger.append(sample('r2')), /unreadable/);
}));

test('concurrent appends are serialised with contiguous seq and a valid chain', () => withLedger(async (ledger) => {
  const entries = await Promise.all(Array.from({ length: 50 }, (_, i) => ledger.append(sample(`run-${i}`))));
  assert.deepEqual(entries.map(e => e.seq), Array.from({ length: 50 }, (_, i) => i + 1));
  const v = ledger.verify();
  assert.equal(v.chainValid, true); assert.equal(v.entries.length, 50);
}));

test('recordRunAudit hashes canonical input/result and extracts model identity', () => withLedger(async (ledger) => {
  const result = { solver: { id: 'solver-x' }, provenance: { implementationHash: 'abc123' } };
  const record: any = {
    document: { runId: 'job-1', capture: { inputJson: '{"b":1,"a":2}', resultJson: JSON.stringify(result) }, sources: [] },
    evidenceStatus: 'unvalidated-model', runKind: 'build-screening',
  };
  const entry = await recordRunAudit(record, ledger);
  assert.ok(entry);
  assert.equal(entry!.inputSha256, canonicalSha256({ a: 2, b: 1 }));
  assert.equal(entry!.resultSha256, canonicalSha256(result));
  assert.equal(entry!.model, 'solver-x'); assert.equal(entry!.implementationFingerprint, 'abc123');
  assert.equal(entry!.evidenceStatus, 'unvalidated-model');
}));

test('recordRunAudit never throws when the ledger fails', async () => {
  const broken = { failedAppends: 0, append: async () => { throw new Error('disk full'); } } as unknown as AuditLedger;
  const origError = console.error; console.error = () => {};
  try {
    const record: any = { document: { runId: 'j', capture: { inputJson: '{}', resultJson: '{}' } }, evidenceStatus: 'unvalidated-model', runKind: 'legacy-unspecified' };
    assert.equal(await recordRunAudit(record, broken), null);
    assert.equal(broken.failedAppends, 1);
  } finally { console.error = origError; }
});

test('GET /api/audit/ledger returns entries and chain status, and flags tampering', () => withLedger(async (ledger, file) => {
  await ledger.append(sample('r1')); await ledger.append(sample('r2'));
  const app = express(); app.use(createAuditLedgerRouter(ledger));
  const server = createServer(app);
  await new Promise<void>(r => server.listen(0, '127.0.0.1', r));
  try {
    const base = `http://127.0.0.1:${(server.address() as { port: number }).port}/api/audit/ledger`;
    const ok: any = await (await fetch(base)).json();
    assert.equal(ok.chainValid, true); assert.equal(ok.firstBrokenSeq, null); assert.equal(ok.entries.length, 2);
    const lines = readFileSync(file, 'utf8').trim().split('\n');
    lines[0] = lines[0].replace('r1', 'rZ');
    writeFileSync(file, `${lines.join('\n')}\n`);
    const bad: any = await (await fetch(base)).json();
    assert.equal(bad.chainValid, false); assert.equal(bad.firstBrokenSeq, 1);
  } finally { await new Promise(r => server.close(r)); }
}));
