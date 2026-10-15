# Data to the user: implementation and wording review

Branch: `feat/data-to-user`, based on `0af46127`. No push.

The existing Dataset Comparison module now opens the SPENT descriptive panel. Its six entries come verbatim from `data/benchmark/spent-ledger-v1.json`, imported with the NIST attribution file from `27187cd9`. Lane and Cunningham expose metadata and DOI links only. Their tables are not imported or bundled by this feature. NIST, both KU Leuven alloys and Totis expose their existing measured depths beside samples of the served default Rosenthal model, grouped by power and beam diameter. Each condition has a signed difference in µm. There is no pooled accuracy summary or ranking on this landing view. The explicit-document historical view API is retained for existing callers and tests.

Materials Database (`#/database`) contains five read-only alloy disclosures under **Served constants and sources**. They project the Python material authority, its `PROPERTY_PROVENANCE`, the material registry and the quantity-envelope input record's `sourceEvidenceKind`. A source for another value or path cannot admit the displayed value. Missing or assumed evidence stays Unresolved. IN625's secondary row and unresolved path differences are disclosed. The unused legacy PDAS/SDAS parameters are identified as unused, with unresolved units.

`scripts/emit-data-to-user.py` emits only served model samples and constant provenance into `src/generated/dataToUser.json`. Measurements remain in the existing benchmark files and are read directly by Vite. No solver, pin, golden, manifest, route, authority allowlist or ceiling file changes. Python source hashes normalize LF; benchmark hashes retain exact source bytes. `python -B scripts/emit-data-to-user.py --check` checks reproducibility, not physical validity. Regenerate this projection when its sources change. This is a committed served-model snapshot, not an execution triggered by the user. Browser-side subtraction and chart scales are presentation arithmetic, not another physics implementation.

Model assumptions: NIST uses its per-case D4sigma numbers and 23.5 °C preheat. The KU Leuven beam is the existing unverified 37.5 µm reading; no sensitivity curve is silently substituted. KU Leuven and Totis retain the loader's assumed 20 °C. Missing layer thickness and hatch use disclosed positive placeholders required by the served interface. Beam definitions and measurement datums are not reconciled. No P8 research path is included. Straight chart segments connect model evaluations at the existing conditions; they do not add measurements or extra solver evaluations between conditions.

Code exploration used direct sources and `rg`; no Graft or codebase-memory tools were callable. No new dependency was added; `npm ci --ignore-scripts --no-audit --no-fund` populated this worktree's dependencies without changing the lockfile.

## Checks

- `npm run lint`: passed.
- Affected TypeScript tests: 44 passed, 0 failed, 0 skipped.
- `npm run test:unit`: 1295 passed, 0 failed, 1 skipped (1296 tests). The skipped existing Phase 4 end-to-end check requires the optional CMU payload (`STMeasurements.csv`, `MTMeasurements.csv`, `README.txt`), which is not restored in this worktree.
- Projection regeneration check and source identity assertions: passed within the affected tests.
- Real Chrome: all six dataset selections checked; NIST 7, KU Leuven 316L 44, KU Leuven Ti-6Al-4V 14 and Totis 80 displayed rows. Lane and Cunningham have no chart or measurement table. Arrow-key selection works; the constant disclosures open with Enter. Table headers, captions, accessible dataset name, focus outlines and horizontally scrollable wrappers checked. Totis chart and Ti-6Al-4V constants visually inspected.
- No new numerical or experimental validation is claimed. The existing module subtitle still describes the historical kernel-comparison record; registry/manifest wording was kept outside this change.

## New authored user-visible strings

Templates below use braces for substitutions. Symbols and units are listed once. Existing ledger/registry/provenance text is displayed verbatim rather than rewritten; the exact data fields are listed after the authored strings.

### Dataset panel

1. `Collected datasets (SPENT)`
2. `Descriptive: not validation; this data was already seen`
3. `Dataset`
4. `{datasetId} ({alloy})`
5. `Source`
6. `Locator`
7. `Licence`
8. `Attribution`
9. `Observable`
10. `Depth datum`
11. `Beam`
12. `{beam.definition} ({beam.status})`
13. `Power basis`
14. `Substrate`
15. `Transcription`
16. `Prior use`
17. `{spentBy.date}: {spentBy.event}`
18. `Inferred inputs`
19. `{input}: {method} ({locator})`
20. `None recorded`
21. `Metadata and source link only. No open licence is recorded for this set.`
22. `Served path: Rosenthal screening with flat-plate absorption. Blue squares and lines: served model samples. Brown circles: measured depth. Lines connect samples at fixed power and beam diameter only.`
23. `Model record source`
24. `rosenthal-screening-v1: python/lpbf_thermal_solver.py`
25. `SHA-256 (LF): {sourceHash}`
26. `NIST uses the recorded 23.5 °C substrate temperature. Other sets use an assumed 20 °C. Missing layer thickness uses a 40 µm placeholder; hatch spacing uses a 100 µm placeholder. These placeholders do not enter the single-track geometry. Beam definitions and depth datums have not been reconciled.`
27. `Measured depth points and served model samples by scan speed` (SVG accessible name)
28. `{conditionId}: {power} W, {speed} mm/s, {beam} µm` (point tooltip)
29. `Scan speed (mm/s)`
30. `Depth (µm)`
31. `Depth comparison table` (accessible scroll region)
32. `Signed deviation = served depth minus measured depth (µm). No experimental validation is claimed.`
33. `Condition`
34. `Power (W)`
35. `Beam diameter (µm)`
36. `Measured depth (µm)`
37. `Served depth (µm)`
38. `Signed deviation (µm)`
39. `Unavailable`
40. `Unavailable: {extentNote}`
41. `No measurement rows are available in this view.`
42. `Unsupported benchmark CSV quoting` (source-shape error)
43. `Non-finite benchmark condition` (source-shape error)

### Constant tables

1. `Served constants and sources`
2. `Read-only Python constant-property tables. Source labels describe input evidence, not experimental validation. Unresolved values have no admitted source for this value and scope. Kernel property reductions can depend on temperature.`
3. `Registry: {quality}. {note}`
4. `IN625 uses the secondary Rosenthal constant-property row. Other served paths hold different values; these paths are not reconciled.`
5. `{alloy.name}: served constants` (caption and accessible scroll region)
6. `Quantity and unit`
7. `Value`
8. `Evidence kind`
9. `Scope and basis`
10. `{scope} ({basis}) {note}`
11. `Retained legacy parameter; unused by the served solver.`
12. `Unresolved`
13. `Literature estimate` (from the existing quantity envelope)
14. `{quantity with underscores replaced by spaces} ({unit})`
15. `dimensionless`
16. `unit unresolved`
17. Units: `°C`, `kg/m³`, `W/(m K)`, `J/(kg K)`, `J/kg`, `kg/mol`, `N/(m K)`, `N/m`, `Pa s`, `1/K`, `GPa`.
18. Quantity labels produced by the template: `M molar`, `absorptivity Green`, `absorptivity IR`, `absorptivity index IR`, `boiling`, `d gamma dT`, `density`, `density liquid`, `emissivity`, `kernel density`, `latent heat fusion`, `latent heat vap`, `liquidus`, `pdas A1`, `poissons ratio`, `sdas B1`, `solidus`, `specific heat`, `specific heat liquid`, `specific heat melt`, `surface tension`, `thermal conductivity`, `thermal conductivity liquid`, `thermal conductivity melt`, `thermal expansion`, `viscosity`, `youngs modulus`.

### Existing source strings newly exposed verbatim

- All six ledger entries: `datasetId`, `alloy`, `title`, `doi`, `locator`, `licence`, `attribution`, `observable`, `datum`, `beam.definition`, `beam.status`, `powerBasis`, `substrate`, `transcription`, `spentBy[].date/event`, and `inputsInferred[].input/method/locator`. The committed ledger is the exhaustive text source for these values, including licence qualifications.
- Five alloy names: `Ti-6Al-4V`, `AlSi10Mg`, `Inconel 625`, `Inconel 718`, `316L Stainless Steel`.
- Material registry `quality` and `note`; per-constant `source`, `locator`, `basis`, `scope`, `note`; and any served `extentNote`. These are projected verbatim in `src/generated/dataToUser.json`. Missing textual provenance uses the authored fallback `Unresolved`.
- Condition IDs from existing tables (NIST case numbers, loader-compatible KU Leuven sample IDs and Totis power/speed IDs); numerical axis ticks, measured depths, served depths and explicitly signed differences. No rewritten experimental claims or new observation strings are introduced.
