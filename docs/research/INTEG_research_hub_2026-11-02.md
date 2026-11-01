# Research Hub integration onto main (2026-11-02)

Lane `lane/hub-2026-11-02`, base main `ac753ee5`. Merged `feat/research-hub` at `694e0b7c` (17 commits, history not rewritten) in merge commit `81de655f`.

## Conflicts and resolution

`git merge-tree ac753ee5 694e0b7c` reports three content conflicts. Everything else auto-merged.

| File | Resolution |
| --- | --- |
| `PROOF.md` | Both sides kept. Main entries first, hub entry after, in date order. No main line removed. |
| `STATUS.md` | Same as PROOF.md. No main line removed. |
| `python/lpbf_worker.py` | Both sides kept. Main's evaporative job types (Ti64, AlSi10Mg, proxy) and the hub's `USER_BLIND_JOB_TYPES` coexist in the constants, `requestSummary`, the saved-result integrity check and the run-time result check. Main's branches are evaluated first; blind jobs take their own branch. |

Auto-merged but needed follow-up after main's physics moved (solver revision `lpbf-build-job-solt-v27` to `lpbf-build-job-tang-risk-v30`, fingerprint `13203cac` to `3a978739`):

| File | Change |
| --- | --- |
| `data/blind/served-closure-pin-v1.json` | `python/lpbf_job_cache.py` changed on main (cache keys every semantic request field, Murakami scenario). Its LF sha256 entry updated to the current file. The other three pinned files are unchanged. The pin note says a change is a reviewed commit, so this needs the maintainer's eye. |
| `docs/LPBF_SPENT_DESCRIPTIVE_2026-10-17.json`, `.view.json` | Identity fields only: `implementationHash`, `servedIdentity.implementationFingerprint`, `buildJobSolverRevision`, `servedClosurePinSha256`, per-alloy `buildJobIdentitySha256` for 316L, IN718, Ti-6Al-4V, and `generatedAt`. Every arm, set, group, point and deviation value is byte for byte the same as the hub's record. Live `predictor_identity` matches the record for all four spent alloys. |
| `.gitattributes` | `/docs/LPBF_SPENT_DESCRIPTIVE_*.json -text`. The descriptive test compares raw bytes with the LF canonical form, and a CRLF checkout broke it. |

Not changed: frozen LPBF physics, `python/lpbf_implementation_fingerprint.expected`, goldens, allowlists, labels. `.github/workflows/ci.yml` arrives from hub commit `b1770332` (ten blind and descriptive modules added to the explicit unittest list) and carries no review trailer here; that is the maintainer's.

Blind-stats goldens: numpy and scipy pins in `python/requirements-lpbf.in` are the same on main and on the hub branch (numpy 2.2.6, scipy 1.15.3), and the goldens pass unchanged in the pinned runtime. Nothing re-recorded.

## Checks run

Pinned runtime: `.runtime/lpbf-win-py312` (Python 3.12.10, numpy 2.2.6, scipy 1.15.3).

| Command | Result |
| --- | --- |
| `python -B scripts/emit-module-registry.py --check` | pass |
| `python -B lpbf_research_identity_pin.py --check` (python/) | pass, pinned equals current |
| `npx tsc --noEmit` | pass |
| `npx eslint` on the 30 merged TS/TSX files under src, routes, server, tests | pass |
| `npx tsx --test --test-concurrency=1` on `lpbf-spent-descriptive`, `lpbf-user-blind-panel`, `lpbf-user-blind`, `lpbf-worker-blind-refusal`, `python-runtime` | 79/79 pass |
| `test_lpbf_blind_stats` | 25 OK |
| `test_lpbf_served_arms` | 14 OK |
| `test_lpbf_spent_ledger` | 8 OK |
| `test_lpbf_spent_descriptive` | 21 OK, 1 skipped (full re-derivation, opt-in) |
| `test_lpbf_user_blind` | 50 OK |
| `test_lpbf_user_blind_inputs` | 57 OK |
| `test_lpbf_user_blind_targets` | 28 OK |
| `test_lpbf_user_blind_store` | 8 OK |
| `test_lpbf_user_blind_crash` | 2 OK |
| `test_lpbf_worker_blind_jobs` | 3 OK |
| `test_module_contract_dataset_view`, `test_module_contract_research`, `test_lpbf_user_measurements` | 4, 6, 23 OK |
| `test_lpbf_proxy_evaporative_worker` (worker conflict, main side) | 6 OK |

## Not run

Light mode on a shared CPU.

- Full descriptive re-derivation: `LPBF_SPENT_DESCRIPTIVE_FULL=1 python -B -m unittest test_lpbf_spent_descriptive` (equivalently `python -B tools/lpbf_spent_descriptive.py --check --date 2026-10-17`). Runs the served arm over every spent row.
- Ti64 and AlSi10Mg evaporative worker tests, the full unit suite, the full Python CI list, parity `--slow`, the browser check of the Research Hub tab and the descriptive panel.
