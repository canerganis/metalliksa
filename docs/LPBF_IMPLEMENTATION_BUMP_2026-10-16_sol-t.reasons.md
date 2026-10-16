# sol-t bump: drift reasons (dc6f5fdd... -> 13203cac...)

Companion to `LPBF_IMPLEMENTATION_BUMP_2026-10-16_sol-t.json`, the tool output of

`python -B tools/lpbf_bump_record.py --from-revision d2f8e5d1 --with-parity-check --slow --expect-drift <the 456 entries of LPBF_IMPLEMENTATION_BUMP_2026-10-16_sol-t.expect-drift.txt>`

run at commit `b5ee77d2` (guarded re-pin to `13203cac19bf69db80b546c6e67ed846a0941e35ea4ad62e53a786de073c46ca`; code `8de9373d`; `worktreeDirty: false`; the 25 goldens still recorded at `dc6f5fdd`) in the locked interpreter `.runtime/lpbf-win-py312`. Every capture, diagnostic and this record ran from that one frozen source head; the earlier Codex diagnostic, which spanned two fingerprints, is superseded and was deleted with its unpinned `.after`, `.preliminary-moves` and `.diagnostic-counts` files. `pinMatchesToHash: true`, `versionUnchanged: true` (`enthalpy-fv-6`). Manifest files changed: `four_alloy_materials.py`, `lpbf_material_registry.py`, `lpbf_thermal_solver.py`, `lpbf_simulation.py`, `lpbf_openfoam.py`, `solidification_front.py` (the pin commit message also lists `quantity_envelope.py` and `lpbf_job_cache.py`; those two changed in `8de9373d` but are outside the manifest).

**Result: 21 DRIFT, 3 PASS (G10, G13, NPZ), 1 FAIL (G9).** The G9 FAIL is the single non-waivable error-rule problem named below; nothing else failed and no entry other than that one was stale.

**This bump installs nominal research conventions, never a validation.** Authority: SPEC Amendment 4 (A4.1 to A4.5) and integration contract 3.1 row 2, 3.3, 4.3, 6.4, 7.1, 7.4, D13. No measured depth was read, fitted or compared in this record; the parity suite and the moved-value capture are synthetic. Labels unchanged: `experimentalValidation=false`, `validationStatus=unvalidated`, `productionReady=false`, ceiling `screening-only`.

## Cause

| id | cause | files |
|---|---|---|
| SOL-T-1 endpoints | 316L 1375/1400 -> 1385/1450 C (Mills/NPL SS316 nominal transfer), AlSi10Mg 557/595 -> 567/599 C (Brandt 2007 Al-9Si-0.6Mg heating pair, family transfer). Ti64 1604/1660, IN718 1260/1336, IN625 1290/1350 C keep their numbers. Densities, k, cp, latent heats and absorptivities are not changed; the Al kernel ledger endpoints are its defined Kirchhoff coordinates, so its pins and arms are recomputed (K 152.524 -> 152.631 W/mK, cp 1020.08 -> 1020.85 J/kgK at 20 C). The served Al liquid density 2393.8 (Assael law at the former 868.15 K) is kept and disclosed. | `four_alloy_materials.py` |
| SOL-T-2 parent | `ENDPOINT_ADMISSIONS` holds frozen copies of `sol_t_admission_records.json` with their canonical hashes; `endpoint_admission` feeds the registry snapshot (`endpointAdmission`, so every material identity moves for all five), `canonical_material_source`, `kernel_properties`, the thermal result (`materialEvidence.liquidusParent`, null when a typed endpoint differs) and the front input record (kind `modelConvention` or `alloyTransfer`, Literature estimate, scope next to the value). A user table or typed endpoint never inherits it. | `four_alloy_materials.py`, `lpbf_material_registry.py`, `lpbf_thermal_solver.py`, `solidification_front.py` |
| SOL-T-3 D13 | Transient and OpenFOAM G, R and cooling: kept in `metrics` and labelled per value in `transientFrontDiagnostics` (Literature estimate, labelSources, scope, parent bindings) when the parent is admitted and the endpoints equal it; null with `missing-source-constant` and the liquidus parent otherwise. Field identity is the producer and extraction rule (`lpbf-transient:<model>:linear-liquidus-crossing-v1`, `metalliksaThermal-OpenFOAM14-6:...`), never the served fingerprint: `implementationHashOccurrencesAfterStrip` stays 0 in every case (the Codex draft leaked it four times). | `lpbf_material_registry.py`, `lpbf_simulation.py`, `lpbf_openfoam.py` |
| SOL-T-4 front | Model id v3; default front still null (A4.1 item 5): an admitted parent gives `insufficient-sample-support` with `gate: sol-c-local-samples-not-installed`, a typed or unadmitted liquidus keeps `missing-source-constant`. | `solidification_front.py` |
| SOL-T-5 text | `regimeBasis` and the 316L keyhole cut basis now state the King conversion at the served 316L property set, 21.4 (18.6 to 24.3) at 1450 C, next to the 22.2 (19.3 to 25.2) at 1400 C where the cut was chosen. The cut 20 is not re-derived and still lies in both intervals. This text moves `regimeBasis` for every alloy. | `lpbf_thermal_solver.py` |
| SOL-T-6 harness | G2 replay: `transientFrontDiagnostics` (top level) and `material.endpointAdmission` are dropped by exact name only when the real capture lacks them; `fixture.strippedResultEqualExceptMaterialIdentity` stays true. No `REFERENCE_NUMERICS_PATTERNS` change. | `tools/lpbf_parity_check.py` |

## Drift by case (exact keys, all in the `.expect-drift.txt`)

| case | keys | what moved |
|---|---|---|
| G1, G2, G3 stripe, G3 island, G4, G5, G7 mesh, G7 timestep, G15, G17 Ti64 (IN718 or Ti64 transient) | 8 each | identity and D13 only: `result.canonicalSha256`, `orderedTypedSha256`, `topLevelKeys`, `key.coreContract`, `key.material`, `coreContract.materialSha256`, `material.materialRevisionSha256`, new `key.transientFrontDiagnostics`. Every `key.metrics`, field, artifact, NPZ, history and fixture observation PASS bit equal. |
| G3 meander/unidirectional, G14 matched/unmatched | 16 each | the same 8 per sub-run |
| G6 screening and fallback | 24 | 6 identity keys for each of 4 sub-runs (no D13 envelope on the screening path) |
| G8 observers | 9 | the 8 plus `plain.canonicalSha256` (same run, digest) |
| G19 emissivity echo | 9 | the 8 for `implicit` plus `run.override0.36` (same identity move) |
| G16 non-IN718 transient | 39 | Ti64 8 identity/D13 keys; 316L and AlSi10Mg also `key.metrics`, `key.thermalHistory`, `key.energyBalance`, `key.massBalance`, `key.numericalDiagnostics`, `key.peakInterpolatedMeltPool`, `key.discretization` (316L also `key.analyticalComparison`): endpoint knots move the field |
| G17 316L, G17 AlSi10Mg | 91 each | field frames, field series, peak field, slices, thermal history, NPZ, evaporation probes and the result digests: the endpoint knots and interval move the transient |
| G9 material snapshots | 68 | 316L and AlSi10Mg thermal, marangoni, inherent-strain props, enthalpy tables, property_at, 316L U95 probes; canonical sources and registry snapshots of all four authority alloys (parent identity) |
| G11 Build Job melt pool | 8 | six result digests, `meltpool.2.geometry_um` (316L Goldak 370/600/60: W 134.8 -> 132.3, L 477.6 -> 461.5, cavity 113.2 -> 114.4 um; D unchanged), `thermalSolver.THERMOPHYSICAL_DB` |
| G12 | 4 | `solidification.defaultBlock`, `.evaluate`, `.pdasAdmission`, `.unknownAlias` (front v3, admitted parents, new reason) |
| G18 | 1 | `meltpool.in625` (front parent and reason; IN625 geometry and latent-heat checks PASS) |

RT8 (A4.5, contract 6.4): no protected key moved. In G1, G2 and G4 (all IN718) only identity, source/parent and D13 keys drifted, none matching `REFERENCE_NUMERICS_PATTERNS`, so the existing exact-key rule accepts them and **no `SOL-T-A4-REFERENCE-EXCEPTION-1` harness exception was implemented**. Implementing one would widen the harness without a key that needs it.

**G9 FAIL, needs the maintainer's disposition:** `fam.u95.ss316l.viscosity` item 1700 K changed from 0.15 to `ValueError: Property viscosity has no U95 specification in mushy regime`, because 1700 K is now inside the 316L interval 1658.15 to 1723.15 K. The U95 budget has no mushy viscosity entry for any alloy (IN718 already records the same error inside its interval). The harness refuses every value-to-error transition under `--expect-drift` and no entry may override it; this record names the key and does not alter the rule, the budget or the probe temperatures. Its companions `fam.u95.ss316l.latent` (error -> 0.08, recovered), `.unknown` (error text), `.k`, `.cp`, `.rho` (mushy budget values) are exact entries and pass.

## Moved-value record (contract 3.3 item 7)

`.before.json` (`d2f8e5d1`, pin `dc6f5fdd`) and `.after.json` (`b5ee77d2`, pin `13203cac`): 735 synthetic cases (5 alloys x Rosenthal, Eagar-Tsai, Goldak x 49 P-v points, beam 80 um, preheat 80 C, layer 40 um, hatch 100 um), IN625 verdict as the exact served refusal on both sides. Summary `.moves.json` (`python/tools/sol_t_moved_values.py --compare`):

| alloy | width (um) min / max change | depth (um) min / max change | other |
|---|---|---|---|
| Ti64 | 0 / 0 | 0 / 0 | only the regimeBasis and absorptivityIndexBasis text |
| IN718 | 0 / 0 | 0 / 0 | same text only |
| IN625 | 0 / 0 | 0 / 0 | same text only; 147 refusals unchanged |
| 316L | -4.6 (Goldak 540/300) / 0 | -5.9 (Eagar-Tsai 150/300) / 0 | 6 regime changes (220 W at 900 mm/s keyhole -> transition, at 1600 mm/s transition -> conduction, each kernel), 1 extent change (Rosenthal 80/900 computed -> width-floor-applied), 3 verdict changes (460/1200 Goldak and Rosenthal risky -> do-not-print, Rosenthal 80/900 do-not-print -> inconclusive) |
| AlSi10Mg | -2.6 (Rosenthal 540/300) / 0 | -1.3 (Eagar-Tsai 540/300) / -0.2 | no regime, extent or verdict change |

These are software outputs at the new conventions; no direction is an accuracy statement.

## Outside the manifest and known reds (contract 3.6)

Tests: `test_sol_t_installation.py` (new), moved literals of 316L and AlSi10Mg outputs in the P6, P7a, P7b, Wave B, balling, consumer-pin, keyhole-regime and public-dataset tests (each with its former value in a comment), the frozen pre-P1 kernel keeps pre-SOL-T endpoints, TS fixtures and generated JSON regenerated. R-lane (bands, `DEPTH_BIAS_BANDS_ID`, demo snapshots, dated records, leaderboard inputs) and P8 R-CTX-1 follow in their own commits. T-FRZ-3 is red by construction on this branch and is the batch's single named red apart from the G9 item above. Stored machine calibrations and the process-window LRU go stale with the pin.
