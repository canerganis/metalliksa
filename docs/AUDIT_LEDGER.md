# Run audit ledger

An append-only JSON-lines file recording who/what/when for every LPBF run the server persists. It answers "which run, with which model, on which input, producing which result, at what time".

## Where and what

- File: `<run root>/audit/ledger.jsonl`, by default `.lpbf-runs/audit/ledger.jsonl` (the run root is `METALLIKSA_LPBF_RUN_ROOT`). Override the directory with `METALLIKSA_AUDIT_DIR`. Runtime data, gitignored, never committed. Because it follows the run root, tests and deployments with their own run root get their own ledger. `LpbfRunArchiveService` takes the ledger as an optional constructor argument.
- Hook: `recordRunAudit()` in `server/auditLedger.ts`, called once from `LpbfRunArchiveService.import` after the run is saved. Only runs imported into the run archive are logged. Previews, failed imports, bundle restores and unarchived worker jobs are not.
- Read-only endpoint: `GET /api/audit/ledger?limit=N` returns `{ entries, chainValid, firstBrokenSeq, headHash, problem, totalEntries, failedAppends }`. `failedAppends` counts append failures since the server started. The whole chain is verified on every call; `entries` is the last N (default 500, max 5000).
- No network use, so it works with `AIRGAPPED=1`. No UI view yet.

## Entry fields

`schemaVersion, seq, ts` (ISO time), `kind, route, runId`, `inputSha256` and `resultSha256` (SHA-256 of canonical JSON: keys sorted, no whitespace), `model` (solver id from the result, else the run kind), `implementationFingerprint` (`provenance.implementationHash` of the result, or null), `evidenceStatus` (the run's evidence label, currently `unvalidated-model`), `prevHash` (SHA-256 of the previous line's exact bytes; 64 zeros for the first entry).

## What it proves

- Editing, deleting or reordering a line that is followed by another line breaks the chain. `firstBrokenSeq` is the seq of the first entry whose bytes no longer match the chain (for an edited line, that line), so the tamper is at or just after it. On a break, that entry and everything after it are left out of `entries`.
- Unparsable lines and gaps in `seq` are reported.
- Two runs with the same canonical input/result have the same hashes, so a run can be matched to its archived record.

## What it does not prove

- It is tamper-evident, not tamper-proof. Anyone with write access to the file can delete it or rewrite the whole chain consistently.
- Editing or truncating the newest line(s) is not detected by the chain alone. Record `headHash` and the entry count somewhere outside this machine (print, ticket, another system) to catch that.
- It is not a signature. There is no key, so it does not prove who wrote an entry. `ts` is the server clock, unattested.
- It records that a run was archived with a given input and result, not that the result is correct. `evidenceStatus` is carried through as is.
- Appends are serialised inside one server process only. Two server processes on the same file could race.
- An append failure is logged and does not block the run import (fail-open). Whether this should fail closed is a maintainer decision.
- Stuck mode: if the process dies mid-write and leaves a partial last line, every later append is refused (the tail is unreadable), so later imports go unaudited. This shows up as `chainValid: false` with a `problem` naming the line, and `failedAppends` rising. Repair the file by hand (keep the broken original aside as evidence) before relying on the ledger again.
