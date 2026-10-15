# P8 phase C implementation and D-12 record

Date: 2026-10-15. Branch: `feat/p8-research-impl`.
Baseline: phase B `00f71983`; research branch merged at `c4f37ba7`, including
Amendment 4 `6c831842` and contract revisions `9c6128f6` / `44624410`.

## Scope and evidence

`lpbf_research_manifest.py` and `lpbf_research_arm.py` implement the documented
`ResearchEngine`. Production research requests now use the real evaluator.
The six runtime files participate in the separate research identity; runtime
reads neither documentation fixtures nor branch blobs. Shared alloy properties
still come from the existing Python property authority.

The source-distinct module manifests preserve default counts, target-module
aliases, OFAT endpoint order and the 80-arm refusal. Revision 4 input records
have exactly 17 base keys, with nonrecursive derivation detail kept separately.
Derived labels exclude process request values, conventions and software policy;
Unresolved takes precedence over User input. Process echoes retain the separate
requestInput role of contract 6.1. Surface-dependent comparison values carry the
falsified-closure status independently of their containing module.

The above-onset point/line field is retained. Independent Gaussian and line
failure paths preserve a resolved leg and withhold the linked result if either
leg fails. The shared companion solve supplies both cavity and link field-shape
disclosures without repeating their numerical work. The onset-side step is
reported once in the module note, with per-arm field-shape shares separately.

The served fingerprint remains
`36cd9d4a96c9726ab2ff4f3030b442f862d96f9ebdc3f724cc6dd85f55110348`.
The research pin is
`7bd877e123791ad42112d5a188a9388b74fd12899618de2dc79af82e15344d85`.
No served manifest member, golden, material authority, documentation fixture or
phase B transport/relay fixture was edited. Nothing was pushed.

## Verification

Interpreter for every check:
`C:/Users/can02/Projects/metalliksaa/Metalliksa-1/.runtime/lpbf-win-py312/Scripts/python.exe`.

- Final research test discovery: 105 tests passed, including the aggregate
  descriptor-cache regression and the complete seven-test R-MAN file. The
  four-test R-CODE file additionally verifies `within_ceiling` directly.
- R-MAP-1 / numeric replay covers all six points, primary arm tuples/provenance,
  roots, numerical values, extrema and statuses; secondary manifests; onset-side
  records; disclosure boundaries; custom coefficient identity; failures of either
  melt leg; independent Gaussian normalization; Belton differentiation; and all
  eight O8 scenarios. Inputs/IDs are exact; numerical comparisons use the declared
  fixture tolerances, with tighter O8 replay.
- All three documentation reproduction commands passed: `p8_amendment1_synthetic.py
  --check`, `p8_input_provenance.py --check`, `alsi10mg_vapour_o8.py --check`.
- R-LINK resolves all difference paths in six served alloy/kernel cases.
- `python/tools/lpbf_parity_check.py --check`: PASS for the default non-slow suite.
  Slow parity cases were not run.
- `python/tools/p8_isolation_diff_check.py`: PASS over the P8 commit range, with
  zero manifest/served-entry changes and the thermal route block unchanged.
- Live served fingerprint equals its untouched pin; the separate research pin
  check passes. Explicit-path diff checks passed.

A read-only independent implementation review found custom endpoint-follow,
coefficient preservation, convention-cache, descriptor-cache, comparison-label,
manifest-wrapper and refusal-cause issues. Fixes and regression checks are in the
implementation. This review is not an experimental or new-physics validation.
Local graph tools were unavailable; exploration used bounded source/document
review without a graph-coverage claim.

## W-1 wording

All new English wording remains **pending maintainer approval**. The authored
tables live in `lpbf_research_codes.py`: `WORDING`, `UI_SENTENCES`, `LEAF_LABELS`,
`VALUE_LABELS`, `SERVED_DIFFERENCES`, and the refusal registry/templates.
Tests check contracts and source-prescribed status text; they do not turn draft
wording into an approval. Leaf summaries are concise; the full module sentence
and the mandatory validation-status text remain present. No UI was implemented
in phase C.

## D-12 measurements

The manual, research-only tool is `python/lpbf_research_measure.py --output <path>`.
It measures complete production serialization, cold/warm stages, per-arm times,
1500 ms chunks, the null-budget path, canonical relay sizes and cache sizes.
The 80-arm probe injects named source-distinct synthetic duplicates into each
banded module; it is a capacity probe, not a newly admitted physical manifest.
The ad-hoc cap probe uses a fresh interpreter with that injected table.

Environment: Windows, Python 3.12.10, NumPy 2.2.6, SciPy 1.15.3. The
documentation fixtures were produced with other NumPy/SciPy versions; their
declared numerical replay tolerances pass here. Cold/warm below means an empty
or populated research LRU in the same interpreter; ad-hoc means a fresh process.
The 80-arm probe preserves O8 physical input keys while adding a synthetic
source-id marker to the cache tuple.

| Alloy / manifest | Nominal cold / warm (s) | Band cold / warm (s) | Complete response bytes before cap | Relay characters |
|---|---:|---:|---:|---:|
| ti6al4v / declared defaults | 1.643 / 0.371 | 8.855 / 0.400 | 3,320,543 | 135,286 |
| alsi10mg / declared defaults | 1.551 / 0.399 | 9.855 / 0.491 | 3,989,336 | 153,045 |
| ti6al4v / 80 per banded module | 1.827 / 0.689 | 31.089 / 1.418 | 9,944,618 | 135,286 |
| alsi10mg / 80 per banded module | 1.894 / 0.737 | 30.167 / 1.441 | 10,329,350 | 153,045 |

Default manifests are Ti cavity/link 20/20, Marangoni 17, surface 19 (O8 not
applicable), and Al 25/25, 13, 24, with eight O8 scenarios. Both default full
responses are below 4 MiB and succeed. Both 80-arm full responses exceed 4 MiB;
the route returns the 83-byte C2 error envelope, not the oversized block. Both
null-budget cap runs exceed the configured 30 s route timeout in this local
measurement. Therefore the cap/timeout combination is **not confirmed usable**.
No cap or timeout was changed.

| Configuration | Cache entries / canonical bytes | Chunks at 1500 ms | Chunk p50 / p95 / max (ms) | Describe service (ms) |
|---|---:|---:|---:|---:|
| ti6al4v default | 86 / 4,763,955 | 5 | 1805.6 / 1866.0 / 1866.0 | 85.7 |
| alsi10mg default | 104 / 5,819,102 | 7 | 1678.7 / 1811.9 / 1811.9 | 116.6 |
| ti6al4v cap | 409 / 17,064,716 | 29 | 1539.6 / 1820.7 / 3058.1 | 325.5 |
| alsi10mg cap | 409 / 17,067,049 | 24 | 1774.5 / 1915.1 / 3242.5 | 267.2 |

Default chunk sequences complete. The cap sequences compute the complete
block but terminate with the same size refusal; their error envelope has no
progress member. No stalled-progress fallback was needed; the explicit
timeBudgetMs=null cold band above measures the null-budget path. The two tested
cap caches contain 409 entries each, using about 17.1 MB of canonical text, below
1024 entries / 128 MiB. Twice the largest sampled footprint is about 34.1 MB;
that is an arithmetic capacity comparison, not a second concurrent-request run.

| Module | Ti default arm p50 / p95 / max (ms) | Al default arm p50 / p95 / max (ms) | Ti cap arm p50 / p95 / max (ms) | Al cap arm p50 / p95 / max (ms) |
|---|---:|---:|---:|---:|
| keyholeCavity | 333.632 / 375.082 / 380.000 | 315.647 / 333.903 / 347.827 | 332.676 / 361.085 / 378.032 | 314.142 / 344.598 / 360.910 |
| meltDepthLink | 7.654 / 771.904 / 890.885 | 7.916 / 787.719 / 823.432 | 7.649 / 10.908 / 861.500 | 8.282 / 13.335 / 805.955 |
| marangoni | 0.021 / 0.037 / 0.057 | 0.029 / 0.061 / 0.098 | 0.023 / 0.046 / 0.086 | 0.027 / 0.053 / 0.098 |
| surfaceBalance | 0.720 / 1.173 / 2.076 | 1.151 / 1.439 / 2.001 | 0.698 / 1.180 / 102.102 | 1.155 / 1.685 / 2.596 |
| alSi10MgVapourMgAware | 0.007 / 0.012 / 0.012 | 0.089 / 0.156 / 0.158 | 0.004 / 0.009 / 0.013 | 0.086 / 0.121 / 0.576 |

These samples include nominal, cold band and chunked work in manifest order.
The cavity arm includes its shared companion thermal solve; the link reuses it.
The nominal link additionally computes the onset-side disclosure records, so its
cost differs from other link arms. Numerical scopes and scenario limits are not
inferred from these timing distributions.

| Fresh ad-hoc process | Time (s) | Outcome |
|---|---:|---|
| ti6al4v default | 9.939 | success |
| alsi10mg default | 11.339 | success |
| ti6al4v cap | 31.325 | RESEARCH_RESPONSE_TOO_LARGE |
| alsi10mg cap | 30.796 | RESEARCH_RESPONSE_TOO_LARGE |

Every measured relay is larger than 12,000 characters, and the real transport
refuses it with RESEARCH_RESPONSE_TOO_LARGE / cause=relay. The cap stays exactly
12,000. Changing that cap also affects the 48-condition / one-million-character
worker RPC budget in contract 14.4 and requires an explicit design decision.

These are local wall times, not latency promises. Served-route p50/p95 under
concurrent research and actual IPC queue-wait/describe latency remain phase G
integration checks. Describe service above excludes queueing; this tool does
not claim to have measured a live server queue.

## Open decisions and continuation

- W-1 wording approval remains with the maintainer.
- The 12,000-character relay cap is unchanged. Oversized real projections are
  refused with `RESEARCH_RESPONSE_TOO_LARGE`, `cause: "relay"`; no field is
  silently omitted to make the projection fit. The measured projection needs a
  maintainer/architect decision before blind relay use.
- The 80-arm/30 s/4 MiB settings require the capacity measurements below to be
  considered together; no resource ceiling was raised in this implementation.
- Phase D/E UI work, phase G served concurrency/IPC measurements and any separate
  Astra numerical signoff are not claimed by this phase C implementation.

All numerical checks above are synthetic software evidence. They grant no blind
validation, experimental accuracy claim, qualification or served promotion.
