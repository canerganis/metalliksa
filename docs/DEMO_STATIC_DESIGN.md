# Static GitHub Pages demo: design

Status: design only, no product code. Target: https://canerganis.github.io/metalliksa/ (project Pages, so the app lives under the `/metalliksa/` base path).

Goal: a visitor can look at the main screens without Python, Node or a server. Everything shown is a precomputed snapshot. The demo is a viewer of recorded output, not a solver.

## 1. What exists today (read from the repo)

- `vite.config.ts`: plain SPA build (`react`, `tailwindcss`), manual chunks, no `base`, no mode switch. `index.html` is the single entry.
- `server.ts`: Express mounts `physicsRouter`, `lpbfSimulationRouter`, `characterizationRouter`, `researchRouter`, plus registry, sources and runs routers. It also serves `/api/health`, `/api/runtime-config` and a JSON 404 for unmatched `/api/*`. Production serves `dist/` with an `index.html` fallback.
- `src/App.tsx`: hash routing (`#/<moduleId>`; home is no hash, `#/` or `#/home`). Hash routing works on a static host as is.
- Engine calls go through `src/services/pythonComputationService.ts` (`fetch("/api/python/...")`, `/api/lpbf/jobs`) and a few direct services (`lpbfGrSolidificationService`, `lpbfSimulationService`).
- Already static: the calibration scorecard record (`src/data/lpbfCalibrationScorecardRecord`) and the error bands (`src/data/lpbfErrorBands.ts`), built from `data/calibration/lpbf-meltpool-error-bands-v1*.json` and `docs/LPBF_CALIBRATION_SCORECARD_v2_2026-10-07*.json`.
- Core flow (`src/data/workspaces.ts`): `3d-distortion-lab` (set up and run), `lpbf-optimizer` (process window), `lpbf-dataset-comparison`, `lpbf-calibration-scorecard`.
- Fingerprint: the error bands carry an `implementationHash` equal to the current pin (`c61ab6a8` since the P1 bump of 2026-10-11; `ec7e1f7a` when this design was written; full value in `data/calibration/lpbf-meltpool-error-bands-v1.summary.json`).

## 2. Build mode and flag

- New env flag `VITE_STATIC_DEMO=1`, read as `import.meta.env.VITE_STATIC_DEMO`. New script `build:demo`: `vite build --mode demo` with the flag set, output to `dist-demo/` (never `dist/`, so the server build is untouched), followed by a copy of `demo/snapshots/` to `dist-demo/demo-snapshots/`.
- `vite.config.ts`: change to `defineConfig(({mode}) => ...)`. When `mode === 'demo'`, set `base` from `VITE_BASE_PATH` (default `/metalliksa/`) and `build.outDir = 'dist-demo'`. Other modes unchanged.
- One module, `src/demo/staticDemo.ts`, owns the demo: `IS_STATIC_DEMO`, `installDemoFetch`, `DEMO_MODULES`. Production code imports only `IS_STATIC_DEMO` and the installer. The flag is a compile-time constant, so Vite drops the demo branch in normal builds so no demo code reaches normal builds. Snapshots live in `demo/snapshots/`, outside `public/` (Vite copies all of `public/` into every build), and are copied into `dist-demo/demo-snapshots/` only by the `build:demo` script. A build check asserts `dist/` contains no `demo-snapshots` path.
- `npm run check:bundle` and `scripts/bundle-budgets.json` must pass for the normal build unchanged. The demo build has its own size check (section 4).

## 3. Serving API calls from snapshots

One seam, not edits in every component.

- `src/demo/demoFetch.ts` wraps `window.fetch`. In demo mode `src/main.tsx` installs it once (`if (IS_STATIC_DEMO) installDemoFetch()`). Components and services stay as they are.
- For a request to `/api/...` it builds the key `METHOD path + canonical JSON(body)` (sorted keys, same number normalization as the generator), looks it up in `snapshots/index.json`, fetches `snapshots/<hash>.json` relative to `import.meta.env.BASE_URL`, and answers with a `Response` carrying the recorded JSON.
- No snapshot for a request: a JSON 404 in the server's error shape (`{error, errorKind: "demo-snapshot-missing"}`) and the UI note "Not available in the static demo." Never an invented value and never a silent nearest neighbor. Controls that feed grid endpoints are locked to the recorded values.
- Writes (registry, sources, runs, imports) are not served. The one exception is `POST /api/lpbf/jobs`, which is answered only for the exact recorded guided-case body, with the recorded finished job (`GET /api/lpbf/jobs/:id` returns the stored final state). Any other job body is a miss.
- The canonical key strips fields the client generates per call (request ids, client timestamps, job or run ids, nonces), otherwise every guided request would miss. WP2 lists the excluded fields explicitly in `scripts/demo/demo-requests.json` and a shared fixture proves that two requests differing only in those fields give the same key.

Covered features (the snapshot set is exactly these):

| Feature | Endpoint(s) | Snapshot |
| --- | --- | --- |
| Process window map | `POST /api/python/lpbf-process-window` | one entry per preset (IN718 guided case first, other presets if the budget allows) at the recorded P x v grid |
| Error bands | none (bundled TS data) | no snapshot; the build must embed the data of the current pin (`c61ab6a8` since 2026-10-11) |
| Calibration scorecard v2 | none (bundled TS record) | no snapshot; shown as is (0 of 30 cells pass) |
| Guided NIST IN718 case | `/api/python/lpbf-calibrated-meltpool`, `/api/python/lpbf-thermal-solver`, `/api/lpbf/jobs` and `/api/lpbf/jobs/:id`, `/api/python/lpbf-process-window` | the chain recorded at 285 W, 960 mm/s |
| Engine status | `/api/python/status`, `/api/health`, `/api/runtime-config` | fixed fixtures: engine "static snapshot" and a dedicated `staticDemo: true` flag in the runtime-config fixture (the demo UI reads it to suppress network features; `airgapped` is a security flag and is not reused) |

For the guided case the generator calls the same code path the app uses, with the exact request from `src/utils/guidedDemo.ts`. The recorded responses are the app's own output, not a reimplementation.

## 4. Snapshot generator spec

Script: `scripts/demo/generate-demo-snapshots.mjs` (Node orchestration over the local engine). If direct Python calls prove simpler, `python/tools/demo_snapshots.py` is acceptable; the output format below is fixed either way. New files only, no solver changes.

- Inputs: `scripts/demo/demo-requests.json` (method, path, body, label, group), the running local engine, a clean git commit.
- Outputs under `demo/snapshots/` (outside `public/`; the `build:demo` copy step places them in `dist-demo/demo-snapshots/`), committed:
  - `index.json`: `{ format: 1, appVersion, gitCommit, fingerprint, generatedAt, entries: { key: file } }`
  - `<sha256-prefix>.json`: `{ request, response, recordedWith: { appVersion, fingerprint } }`
  - `manifest.json`: file list, byte sizes, sha256 per file.
- Provenance in `index.json`:
  - `appVersion` from `package.json` (`0.1.0` today) plus short git commit.
  - `fingerprint`: the LPBF implementation hash from the engine (the value the pin test checks, `c61ab6a8...` since the P1 bump of 2026-10-11; `ec7e1f7a...` when this design was written). The generator refuses to run if it differs from `python/lpbf_implementation_fingerprint.expected`. At load the app compares `index.json.fingerprint` with the bundled error-bands `implementationHash`; a mismatch hides the process window and calibration cards and puts the banner in a warning state.
  - The generator reads the pin and never writes it.
- Determinism: fixed seeds, sorted keys, no rounding beyond the engine's own output, no timestamps inside responses (`generatedAt` only in `index.json`). Two runs give byte-identical `<hash>.json` files.
- Size budget: `demo/snapshots/` at most 6 MB raw and 1.5 MB gzip, one file at most 1 MB, `dist-demo/` at most 12 MB gzip excluding the already budgeted `vendor-*` chunks. The generator fails over budget. Grids keep the recorded resolution; no extra resolution to fill space.
- Evidence labels pass through unchanged. The generator asserts that every response containing `experimentalValidation` has it `false` and fails otherwise.

## 5. Modules hidden in demo mode

`DEMO_MODULES` is an allowlist; everything else is hidden.

Shown: Overview/home, `3d-distortion-lab` (read-only, recorded run), `lpbf-optimizer` (process window map panel only), `lpbf-dataset-comparison` (bundled views), `lpbf-calibration-scorecard`, the guided NIST IN718 tour, the keyhole benchmark view (bundled view JSON).

Hidden from navigation, the command palette and `#/` deep links (a hidden id redirects home with a note): everything that needs a live engine or free input. That is the Bayesian optimizer, the solidification microstructure lab (and with it the G/R map card, which is mounted only there and is therefore not part of this demo), CALPHAD and phase diagram viewer, characterization (XRD, EIS, SEM), research and AI consultation (needs keys), materials import, experiment and validation lab, research registry, sources and runs bundles, the job queue, exports that write to disk, and the engine status dialog (replaced by a static note).

Inside `lpbf-optimizer`, only the process window map panel is live-recorded. The Bayesian optimizer panel is not rendered and is replaced by the note "Not available in the static demo." WP3 identifies the panel boundary in the module and records it in the allowlist file.

Any remaining control that would send an input outside the recorded set is disabled with the title "Recorded values only in the static demo."

The allowlist lives in one place. `ModuleNav`, the palette and the hash resolver read the filtered list. `src/generated/moduleRegistry.ts` is generated and must not be edited for this.

## 6. Banner

A non-dismissible bar at the top of every screen in demo mode, English only, exact text:

> Static snapshot of version X, computed offline. Not live solver output.

`X` is `appVersion` plus short commit from `index.json`, for example `0.1.0 (a1b2c3d)`. It links to the repo and shows the fingerprint prefix on hover. It renders outside module boundaries so no module can hide it, and a test fails if it is absent. The HTML work report gets the same sentence in its header. Existing evidence badges, "screening only" banners and `experimentalValidation=false` stay as they are. The demo adds no claim and promotes no evidence label.

## 7. Pages workflow

New file `.github/workflows/pages-demo.yml`:

- Trigger: `push` to `main` with paths `src/**`, `demo/snapshots/**`, `package*.json`, `vite.config.ts`, the workflow file, plus `workflow_dispatch`.
- Permissions: `contents: read`, `pages: write`, `id-token: write`. Concurrency group `pages`, no cancel of a running deploy.
- Steps: checkout, setup-node (`.nvmrc`), `npm ci`, `npm run build:demo` with `VITE_BASE_PATH=/metalliksa/`, `node scripts/demo/check-demo-build.mjs` (size budget, banner string present, no `/api` literal outside the demo module, manifest hashes match, and `dist/` (normal build, if present) contains no `demo-snapshots` path), copy `dist-demo/index.html` to `dist-demo/404.html`, `actions/upload-pages-artifact`, then a `deploy` job with `actions/deploy-pages` and environment `github-pages`.
- No Python in the workflow and no snapshot regeneration. Snapshots are generated locally, reviewed and committed, so a deploy cannot change numbers silently.
- Review note: it is a new file under `.github/workflows/`. `scripts/check_ceiling_review.py` protects `.github/workflows/ci.yml` and `.github/CODEOWNERS` by exact path, and CODEOWNERS lists only `ci.yml` there, so a new workflow file is not covered today. The maintainer should still review it because it grants Pages and OIDC write. If the maintainer decides to add it to `PROTECTED_PATHS` or CODEOWNERS, that edit to the guard files needs a `Ceiling-Review: <reason of four or more words>` trailer added by the maintainer. Worker agents never add that trailer.
- One-time maintainer setting: repository Settings, Pages, source "GitHub Actions". It cannot be set from repo content.
- `ci.yml` is not touched. Suggested additions for the maintainer: a step `npm run build:demo && node scripts/demo/check-demo-build.mjs`, and the new unit tests in `scripts/ci-unit-tests.txt` if that list gates them.

## 8. Base path handling

- `base` is `/metalliksa/` in demo mode only. Asset URLs go through Vite's base. Runtime paths (snapshots, images, STLs in `public/`) use `import.meta.env.BASE_URL`, never a leading `/`. The build check greps the output for root-absolute `"/demo-snapshots`, `"/images`, `"/stls`, `"/icon.svg` and `"/manifest.json` and fails on a hit.
- Routing is hash based, so `https://canerganis.github.io/metalliksa/#/lpbf-optimizer` needs no rewrite. `404.html` is a copy of `index.html` as a safety net.
- `App.tsx` rewrites legacy hashes with `history.replaceState(null, '', pathname + search + hash)`, which keeps the base. A test confirms it.
- Check `public/manifest.json` and any service worker for base-relative `start_url` and `scope`.
- Fonts are bundled `@fontsource` packages. Demo mode makes no network call except same-origin static files.

## 9. Test plan

Unit (`tsx --test`, self-contained fixtures, no network):
- `demoFetch`: a hit returns the recorded body; a miss returns the `demo-snapshot-missing` 404; the key is order independent; write methods are refused.
- The canonical key function matches the generator's, using a shared fixture of 10 requests with expected keys.
- `DEMO_MODULES` filter: hidden ids are absent from nav and palette; a hash to a hidden id goes home.
- Banner: exact text, version from a fixture index, present on every shown module (render test).
- Fingerprint guard: matching and mismatching `index.json` against the bundled error bands.
- `experimentalValidation` is `false` in every committed snapshot.

Build checks (`check-demo-build.mjs`):
- Demo build with base `/metalliksa/`: no root-absolute asset URLs, size budget, manifest hashes, no `/api/` string outside the demo module.
- Normal `npm run build` and `npm run check:bundle` unchanged, with no demo code in production chunks (compare chunk lists) and no `demo-snapshots` path anywhere in `dist/` (the chunk list alone would not catch a copied snapshot file).
- Generator determinism: two runs, byte-identical output.

Smoke (Playwright if available, else `vite preview --base /metalliksa/`): open `/metalliksa/#/lpbf-optimizer`, run the guided tour at 285 W and 960 mm/s, check the scorecard shows 0 of 30, banner visible, no failed requests, network limited to same-origin static files.

Gate: `npm run lint`, `npm run test:unit`, the demo build check. Python tests only if the generator is Python.

## 10. Work packages

| WP | Model | Scope | Acceptance |
| --- | --- | --- | --- |
| WP1 | Sonnet | `VITE_STATIC_DEMO` flag, demo mode and base in `vite.config.ts`, `build:demo` script, `src/demo/staticDemo.ts`, `demoFetch` and its install in `main.tsx` | Normal build chunk list identical to main; `build:demo` emits `dist-demo/` under base `/metalliksa/` and copies snapshots only there; `dist/` has no `demo-snapshots` path; demoFetch unit tests pass; `npm run lint` clean |
| WP2 | Sonnet | Snapshot generator, request list with the excluded-field list for the canonical key, `demo/snapshots/`, manifest, determinism and budget checks | Two runs identical; within size budget; key-exclusion fixture passes; fingerprint read and checked against the pin file (read only); `experimentalValidation` false everywhere; no solver or pin file modified |
| WP3 | Sonnet | Module allowlist in nav, palette and hash resolver; locked controls; fingerprint mismatch state | Hidden ids unreachable by nav, palette and hash; disabled-control title present; tests pass |
| WP4 | Haiku | Banner component and report header sentence; copy check for English text and no em/en dash punctuation | Exact banner string; render test on all shown modules; grep finds no dash punctuation in new strings |
| WP5 | Sonnet | `check-demo-build.mjs`, `.github/workflows/pages-demo.yml`, 404.html copy | Check passes on a local demo build; workflow YAML validated (actionlint or equivalent); report raises the Ceiling-Review question |
| WP6 | Haiku | README "Live demo" section, short doc on what the demo is not | Pages link added only after the maintainer enables Pages; wording says snapshot, screening, not validation |
| Review | Opus | Review WP1 to WP5 diffs; run the full suite once at the gate | No frozen physics, pin, golden, `ci.yml`, CODEOWNERS or ceiling file changed |

Order: WP1 and WP2 in parallel (disjoint files), then WP3 and WP4, then WP5, WP6 last.

## 11. Open questions (conservative defaults chosen)

- Which presets besides IN718 get process window snapshots. Default: IN718 only, more if under budget.
- Generator language (Node via IPC or a Python tool). Default: Node orchestration, to reuse the app's request builders.
- Whether the maintainer wants `pages-demo.yml` under CODEOWNERS or `PROTECTED_PATHS`. Default: no change to guard files from this work.
- Whether to show the solidification microstructure lab read-only with only the G/R card for the recorded IN718 request. Default: no, the lab stays hidden and the G/R map is out of scope.
- Whether to keep the three.js viewer (about 208 KB gzip) in the demo. Default: keep, lazy as today.
