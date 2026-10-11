"""Machine-readable copy of every pre-registered value of the regime-dependent absorptivity evaluation.

Source of truth for the numbers: docs/research/PREDECLARED_regime_absorptivity_2026-10-09.md as amended by Amendment 1
(commit fe30687d; the original text is commit 91174d2c).
This file is frozen with the pre-registration (stage 0). Its sha256 (canonical JSON of CONFIG) is pinned in
python/test_lpbf_regime_absorptivity_config.py, so any edit shows up as a test failure and needs a recorded deviation.

Neither this file nor the harness (python/tools/lpbf_regime_absorptivity_eval.py, python/lpbf_regime_absorptivity_kernel.py)
is in lpbf_simulation.IMPLEMENTATION_SOURCE_FILES, and no frozen file imports them. SCREENING ONLY, NOT VALIDATION:
experimentalValidation=false, validationStatus=unvalidated, productionReady=false stay as they are.

Note (P1 planned bump, 2026-10-11): the placement block below names the Rosenthal multi-reflection ramp, the latent-heat
factor and the "Rosenthal keyhole increment heuristic" as unchanged. That is the pre-P1 baseline the evaluation ran
against; P1 removed all three from the served path (docs/research/SPEC_p1_sourced_served_physics_2026-10-11.md). CONFIG
is not edited (its sha256 is pinned), the kernel stays frozen as the pre-P1 copy.
"""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Dict

PREREGISTRATION_DOC = "docs/research/PREDECLARED_regime_absorptivity_2026-10-09.md"
PREREGISTRATION_COMMIT = "fe30687d5be201377e7249bff710c02f33924af3"  # Amendment 1 (original: 91174d2c)
PREREGISTRATION_SHA256 = "ccc365f120cbe29c98997aa6b1d9d3e3eeb795359ab9631ac534100e112d76f4"  # LF content
BASE_COMMIT_PREFIX = "02503eed"
FROZEN_FINGERPRINT = "ec7e1f7a6606e937e448fefe97549b49a7ddfe7b95376b93867ae007b0c12555"
EVIDENCE_LABEL = "Screening (literature estimate): regime-dependent absorptivity law, not validation"

CONFIG: Dict[str, Any] = {
    "version": "lpbf-regime-absorptivity-config-2",
    "preregistration": {"doc": PREREGISTRATION_DOC, "commit": PREREGISTRATION_COMMIT,
                        "sha256Lf": PREREGISTRATION_SHA256,
                        "note": "Amendment 1 commit; the original pre-registration is commit 91174d2c"},
    "base": {"commitPrefix": BASE_COMMIT_PREFIX, "implementationFingerprint": FROZEN_FINGERPRINT},
    "labels": {"experimentalValidation": False, "validationStatus": "unvalidated", "productionReady": False,
               "evidence": EVIDENCE_LABEL},
    "kernels": ["eagar-tsai", "goldak", "rosenthal"],
    "law": {
        "form": "A(H) = A_flat for H <= H_on, else A_kh - (A_kh - A_flat) exp(-(H - H_on) / H_s); A_flat if A_flat >= A_kh",
        "label": "literature-inspired screening surrogate, not a published law",
        "H": "A_flat P / (rho cp_s max(50, T_liq - T0) sqrt(pi alpha_s v r^3)), r = 1/e^2 radius, flat A (unchanged)",
        "H_on": 15.0,
        "A_kh": 0.70,
        "A_kh_note": "asymptote of Gan 2021 fitted effective energy-coupling relation, not a measured universal optical plateau",
        "H_s": 5.0,
        "envelope": [0.25, 0.80],
        "nothingFitted": True,
    },
    "flatAbsorptivity": {"316L Stainless Steel": 0.42, "Ti-6Al-4V": 0.35, "Inconel 625": 0.38, "Inconel 718": 0.38},
    "placement": {
        "A0": {"eagar-tsai": "absorbed power = A(H) P", "goldak": "absorbed power = A(H) P",
               "rosenthal": "eta_eff = A(H) replaces the multi-reflection ramp; latent-heat factor unchanged",
               "unchanged": ["H", "regime label", "keyholePorosityRisk", "Fabbro absorptivity (flat)",
                             "Rosenthal keyhole increment heuristic (flat H)", "process map", "powder-raytrace path",
                             "calibration layer"]},
    },
    "arms": {
        "A0": {"role": "primary (the only arm that can produce PASS)", "A_kh": 0.70, "H_s": 5.0, "fabbroA": "flat"},
        "S1": {"role": "sensitivity", "A_kh": 0.62, "H_s": 5.0, "fabbroA": "flat",
               "source": "NIST mds2-2525 Ti-6Al-4V keyhole-phase mean (measured)"},
        "S2": {"role": "sensitivity", "A_kh": 0.79, "H_s": 5.0, "fabbroA": "flat",
               "source": "Trapp 2017 Fig. 4, 316L disc 500 mm/s, highest plotted value (digitized, context only); "
                         "its source experiment is the diagnostic-only Trapp geometry (D6)"},
        "S3": {"role": "sensitivity", "A_kh": 0.70, "H_s": 2.5, "fabbroA": "flat"},
        "S4": {"role": "sensitivity", "A_kh": 0.70, "H_s": 10.0, "fabbroA": "flat"},
        "G": {"role": "sensitivity", "label": "G (Gan 2021 Eq. 6, adapted)",
              "form": "A = max(A_flat, 0.7 (1 - exp(-0.6 X))), X = Am P / ((T_liq - T0) pi rho cp_s v r^2)",
              "adaptations": ["floor max(A_flat, .) added", "T_liq - T0 floored at 50 K as in H",
                              "app properties (solid rho and cp_s, liquidus) replace Gan's property set",
                              "r = d/2 from the app's 1/e^2 diameter input", "Am from Ye 2019 Table 1",
                              "no onset, so it can differ from baseline below H = 15"],
              "eta_max": 0.7, "rate": 0.6, "deltaT_floor_K": 50.0,
              "Am": {"316L Stainless Steel": 0.28, "Ti-6Al-4V": 0.26, "Inconel 625": 0.28},
              "AmSource": "Ye 2019 Table 1 (data/benchmark/ye-2019-absorptivity)", "unavailable": ["Inconel 718"]},
        "K": {"role": "sensitivity", "A_kh": 0.70, "H_s": 5.0,
              "fabbroA": "A(H) on Eagar-Tsai and Goldak; Rosenthal identical to A0"},
        "F": {"role": "sensitivity (fitted)", "A_kh": 0.70, "H_s_grid": {"start": 1.0, "stop": 20.0, "step": 0.5},
              "objective": "equal-source-weighted depth MAPE on the frozen scoring populations P(k, g, s, depth) of "
                           "the training sources",
              "scheme": "leave-one-source-out over the five trainable-class sources; a trainable held-out source is "
                        "scored with H_s fitted on the other four, ghosh-in625-2018 with H_s fitted on all five; "
                        "ties go to the larger H_s",
              "fitPerKernelAndReading": True,
              "note": "if F passes and A0 fails, record a hypothesis for a NEW pre-registration, not a PASS"},
    },
    "robustnessArms": ["S1", "S2", "S3", "S4"],
    "robustnessCriteria": ["C1", "C3", "C4"],
    "dataRoles": {
        "trainableClass": ["hofmann-316l-2026", "ku-leuven-316l-2021", "totis-ti64-2021", "ku-leuven-ti64-2021",
                           "lane-in625-2020"],
        "testOnly": ["ghosh-in625-2018"],
        "heldOutPartlyExposed": ["hofmann-316l-2026", "totis-ti64-2021"],
        "diagnosticOnly": ["trapp-316l-2017", "cunningham-ti64-2019"],
        "digitized": ["trapp-316l-2017", "cunningham-ti64-2019"],
        "spotAssumed": ["ghosh-in625-2018"],
        "meltPoolSources": ["hofmann-316l-2026", "ku-leuven-316l-2021", "totis-ti64-2021", "ku-leuven-ti64-2021",
                            "lane-in625-2020", "ghosh-in625-2018"],
        "significanceEligible": ["hofmann-316l-2026", "ku-leuven-316l-2021", "totis-ti64-2021",
                                 "ku-leuven-ti64-2021", "lane-in625-2020"],
        "kuSources": ["ku-leuven-316l-2021", "ku-leuven-ti64-2021"],
        "cunningham": "cunningham-ti64-2019",
        "cunninghamSpot_um": 95.0,
        "cunninghamCases95": 46,
        "catalogSentinels": ["guo-316l-2024", "nist-amb2022-03-in718"],
        "sentinelRole": "reported separately, never in the verdict, PI pool or regime accuracy",
        "notUsed": {"zhao-ti64-2020": "porosity boundary, not melt-pool geometry",
                    "cmu-ti64-*": "no power or beam diameter",
                    "ku-leuven-in718-2021": "dimension units unresolved"},
        "noEligibleHeldOut": ["AlSi10Mg", "Inconel 718"],
        "neverTargets": ["nist-mds2-2525", "simonds-316l-2018", "trapp absorptivity series", "ye-2019-absorptivity",
                         "gan-2021 relations", "trapp Fig. 3(a) track geometry (diagnostic D6)",
                         "cunningham 2019 Fig. 3A lines and Fig. 3B/3C depths (diagnostics D1, D5)"],
    },
    "sourceManifest": {
        "rules": [
            "a measured response is gated only when its operator has a document locator in this manifest",
            "an input definition with a documented alternative reading is a nuisance axis; without one it is a declared assumption",
            "Totis width: gated only if the W definition is printed in Vaglio 2020 Fig. 1 / Fig. 2(b) (stage 0 outcome below)",
            "the only conversions are the ones listed here and the datum reading (measured depth + 0.60 t)",
        ],
        "totisWidthStage0": {
            "outcome": "unconfirmed",
            "read": "Vaglio et al. 2020, Data in Brief, doi:10.1016/j.dib.2020.106443, open-access full text (PMC7642809), 2026-10-09",
            "finding": "Sec. 1.3 only says W, H, D and the contact angle are defined in Fig. 2(b); the text prints no "
                       "wording or reference line for W. The figure graphic could not be read in the text channel, so "
                       "no locator and no wording can be recorded.",
            "consequence": "Totis width is reported only (D7): not gated, not in E_W, not in label set (i), not in the PI width pool",
        },
        "sources": {
            "hofmann-316l-2026": {
                "files": "Zenodo 10.5281/zenodo.16979848 MeltpoolGeometryData.csv (raw sha256 5dd0629b...); table meltpool_geometry.csv sha256 d4bbc7a6...; paper doi:10.1016/j.matdes.2026.115459",
                "widthOperator": "weld_width_um at the original substrate surface (paper Fig. 2, Sec. 2.2)",
                "depthOperator": "penetration_depth_um, substrate surface to melt-pool bottom (paper Fig. 2, Sec. 2.2)",
                "units": "um; area column (mislabelled um) not used; d_laser mm x 1000 = um",
                "beamInput": "d_laser diameter; definition not stated, 1/e^2 assumed (equal to D4sigma for the stated single-mode Gaussian); no alternative reading carried",
                "specimen": "plate with t_powder 0 / 30 / 60 um; t = t_powder; kernel layer input 30 um when t = 0; 20 C assumed",
                "datumLayer_um": "row t_powder",
                "gate": {"depth": True, "width": True, "widthBallingFlaggedExcluded": True}},
            "totis-ti64-2021": {
                "files": "Mendeley 10.17632/s9438vb5xd.1 Allegati.zip :: Data.xlsx (sha256 3211cbaa...); table tracks.csv sha256 3b5794f3...; Data in Brief doi:10.1016/j.dib.2020.106443",
                "widthOperator": "sheet 'Track width (W)'; reference height not in the repo record; not printed in the open text (stage 0)",
                "depthOperator": "sheet 'Track depth (D)', from the top of the printed Ti-6Al-4V base under the powder layer (Vaglio 2020 Fig. 1, Fig. 2(b), Sec. 1.3)",
                "units": "um; no conversion",
                "beamInput": "50 um, 1/e^2 stated",
                "specimen": "25 um powder on a printed base (same job), t = 25 um; one track per cell; 20 C assumed",
                "datumLayer_um": 25.0,
                "gate": {"depth": True, "width": False}},
            "ku-leuven-316l-2021": {
                "files": "Figshare 10.6084/m9.figshare.15035733.v1, 15035703.v1; sha256 pinned in KU_WAVE2_FILES; table conditions.csv sha256 e031aead...; article doi:10.1016/j.jmatprotec.2022.117547 NOT read (HTTP 403)",
                "widthOperator": "'w exp' (processed file), full width INFERRED, not confirmed",
                "depthOperator": "'d exp' (processed file); datum and powder layer not stated",
                "units": "um (unit tag in the raw files; processed files untagged; 316L values equal raw section means); decimal comma read as point; model and error columns excluded by name",
                "beamInput": "37.5 um, diameter versus radius unverified: nuisance readings 37.5 / 75 um",
                "specimen": "layer not stated; t = 60 um in the datum reading (cited from the unread article by the 2026-10-05 KU IN718 record; unverified); 20 C assumed",
                "datumLayer_um": 60.0,
                "gate": {"depth": True, "width": False}},
            "ku-leuven-ti64-2021": {
                "files": "Figshare 10.6084/m9.figshare.15035709.v1, 15035712.v2; sha256 pinned in KU_WAVE2_FILES; table conditions.csv sha256 e031aead...",
                "widthOperator": "as ku-leuven-316l-2021", "depthOperator": "as ku-leuven-316l-2021",
                "units": "as ku-leuven-316l-2021", "beamInput": "as ku-leuven-316l-2021",
                "specimen": "as ku-leuven-316l-2021",
                "datumLayer_um": 60.0,
                "gate": {"depth": True, "width": False}},
            "lane-in625-2020": {
                "files": "doi:10.1007/s40192-020-00169-1, PMC8194244 JATS XML (sha256 19757c67..., not committed); table3_tracks.csv sha256 32fe10fb...",
                "widthOperator": "Table 3 first 'Cross Section (um)' column, track mean of N = 3 (column order confirmed: CBM means reproduce Table 4 Class Width)",
                "depthOperator": "Table 3 second 'Cross Section' column; bare plate, depth below the plate surface",
                "units": "um; D4sigma used as the 1/e^2 diameter (equal for a Gaussian)",
                "beamInput": "D4sigma 100 um (CBM), 170 um (AMMT), Table 1",
                "specimen": "bare IN625 plate, t = 0; 20 C assumed; power: Table 3 (primary) versus nominal case power (conditional axis)",
                "datumLayer_um": 0.0,
                "gate": {"depth": True, "width": True}},
            "ghosh-in625-2018": {
                "files": "doi:10.1007/s11837-018-2771-x; fig1_tracks.csv pinned in lpbf_literature_datasets.py; PDF sha256 b89cd530... (not committed)",
                "widthOperator": "printed 'w' label in Fig. 1, CLSM section at track centre",
                "depthOperator": "printed 'h' label in Fig. 1, below the bare plate surface",
                "units": "um; printed numbers, not digitized",
                "beamInput": "not stated: nuisance readings 140 / 100 um",
                "specimen": "bare plate, t = 0; 20 C assumed",
                "datumLayer_um": 0.0,
                "gate": {"depth": True, "width": True}},
            "trapp-316l-2017": {
                "files": "doi:10.1016/j.apmt.2017.08.006; fig3a_tracks_digitized.csv",
                "widthOperator": "digitized Fig. 3(a) open circles",
                "depthOperator": "digitized Fig. 3(a) filled circles; 0.5 mm discs",
                "units": "um, read uncertainty 3 um", "beamInput": "60 um 1/e^2 stated", "specimen": "bare discs, t = 0",
                "datumLayer_um": 0.0,
                "gate": {"depth": False, "width": False}, "role": "diagnostic-only (D6)"},
            "cunningham-ti64-2019": {
                "files": "doi:10.1126/science.aav4687; pinned CSVs in lpbf_keyhole_literature.py",
                "widthOperator": "n/a", "depthOperator": "vapor-depression depth, digitized", "units": "um",
                "beamInput": "95 um", "specimen": "bare plate", "datumLayer_um": 0.0,
                "gate": {"depth": False, "width": False}, "role": "diagnostic-only (D1, D5)"},
        },
        "depthDatumPhi": 0.60,
    },
    "rows": {
        "builder": "loaders pinned by sha256 as in python/tools/lpbf_calibration_fit.py load_rows + "
                   "python/tools/lpbf_calibration_fit_v2.py load_test_only_rows at 02503eed",
        "preheat_C": 20.0, "bareLayerNominal_um": 30.0, "defaultHatch_um": 100.0,
        "laneUsesTable3PowersPrimary": True, "trapp117WExcluded": True, "ghosh7Kept": True,
        "ballingFlaggedExcludedFromWidth": True, "ballingFlaggedKeptForDepth": True,
        "noRowRemovedOnMeasuredResponse": True,
        "clusterKey": ["source", "power_W", "speed_mm_s", "beamDiameter_um", "layer_um"],
        "affected": "flat H > H_on under the input reading being scored (input-only; the datum axis does not change H)",
        "inputEligibility": "input-valid for q, gated for q by the manifest, not balling-flagged when q = width",
        "populations": "P_all(k,g,s,q) = input-eligible rows whose baseline status is computed with finite positive width and depth; "
                       "P(k,g,s,q) = affected rows of P_all; frozen at stage 2 from the baseline only",
    },
    "nuisance": {
        "kuBeam_um": [37.5, 75.0], "ghoshSpot_um": [140.0, 100.0],
        "datum": ["published", "layer"],
        "datumRule": "layer: measured depth + 0.60 t (changes measured depth and D/W only, never kernel inputs or H)",
        "lanePower": ["table3", "nominal"],
        "lanePowerRule": "axis active only if stage 1 finds at least one Lane row affected under either power; otherwise nominal is a reported sensitivity",
        "gridSize": {"laneInactive": 8, "laneActive": 16},
        "primary": {"kuBeam_um": 37.5, "ghoshSpot_um": 140.0, "datum": "published", "lanePower": "table3"},
    },
    "metrics": {
        "bootstrap": {"B": 1000, "seed": 0, "ci": "percentile", "level": 0.95,
                      "unit": "parameter-set cluster within a source, clusters sorted by key string",
                      "pooled": "1 - mean_s MAPE_cand,s / mean_s MAPE_base,s (equal source weight), stratified cluster "
                                "bootstrap: one default_rng(0) stream per pooled call, sources in sorted id order, a (B, n_clusters_s) draw per source",
                      "undefinedReplicates": "baseline MAPE 0; more than 10 of 1000 undefined makes the CI not evaluable",
                      "maxUndefined": 10},
        "regime": {"dw_keyhole_threshold": 0.5, "pred": "kernel melt-pool D/W >= 0.5 from the 0.1 um-rounded outputs; ties are keyhole",
                   "labelSets": {"i": "measured D/W >= 0.5 on rows of P(k,g,s,depth) that also have gated width and are not balling-flagged; sources with both operators confirmed (hofmann, lane, ghosh); mean of per-source accuracy",
                                 "ii": "KU Leuven published melting regime on rows of P(k,g,s,depth) of the two KU sources, keyhole versus not (transition = not keyhole), equal source weight"},
                   "labelSetISources": ["hofmann-316l-2026", "lane-in625-2020", "ghosh-in625-2018"],
                   "indexControl": {"keyholeFromH": 20.0}},
        "pi90": {"z": 1.6449, "level": 0.90, "residual": "ln(meas/pred)", "minPoolSourcesForBetween": 3,
                 "betweenDdof": 1, "wilsonConf": 0.95,
                 "recentred": "mu = mean of pool-source mean residuals; uncentred variant (mu = 0) reported"},
        "intervalScore": {"alpha": 0.10, "margin": 1.05, "reference": "Gneiting and Raftery 2007"},
        "diagnostics": {"D1": "share of Cunningham 95 um cases with predicted melt-pool depth >= measured vapor-depression depth",
                        "D2": "MAE of A(H) vs Trapp 2017 scanning 316L disc series (non-penetrated), 60 um 1/e^2, app 316L properties, vs flat 0.42",
                        "D3": "every A(H) inside [0.25, 0.80]",
                        "D4": "candidate width and depth on non-affected rows equal baseline exactly (failure makes the run INVALID)",
                        "D5": "Cunningham Fig. 3A regime agreement on the 46 Fig. 3B 95 um cases, all and nearBoundary false",
                        "D6": "Trapp Fig. 3(a) geometry: M1 to M4",
                        "D7": "ungated widths (KU Leuven, Totis if unconfirmed): M2, M3, measured D/W accuracy"},
    },
    "eligibility": {"minRows": 5, "minClusters": 3, "minSourcesInE": 2, "needsTrainableClass": True,
                    "zeroBaselineMapeRemoved": True},
    "criteria": {
        "C1": "depth skill point estimate > 0 on EVERY source in E(k, g); a direction check, not a significance claim",
        "C2": "pooled depth skill over T(k, g) (equal source weight, stratified cluster bootstrap) has CI95 lower bound > 0",
        "C3": {"perSourceWidthSkillMin": -0.05, "pooledWidthSkillCiLowerMin": -0.05,
               "text": "width skill >= -0.05 on every source in E_W(k, g) and pooled CI95 lower bound >= -0.05"},
        "C4": "accuracy_candidate >= accuracy_baseline (point estimate) on each evaluable label set (i), (ii)",
        "C5": {"minRowsPerQuantity": 10, "coverageDrop": 0.05, "intervalScoreMargin": 1.05,
               "text": "for every s in E and q in {depth; width if s in E_W} with >= 10 rows and a defined PI in both arms: "
                       "coverage_cand >= coverage_base - 0.05 and mean M8 cand <= 1.05 x mean M8 base; Wilson and coverage-difference CIs reported, never gated"},
        "C6": "rowwise preservation: every row of P_all(k, g, s, q), every source and quantity, is resolved by the candidate",
        "notEvaluable": {"C2": "its CI is not evaluable", "C3": "E_W empty or pooled CI not evaluable",
                         "C4": "neither label set has a row", "C5": "no (s, depth) pair qualifies"},
    },
    "decision": {
        "kernelVerdictOrder": ["INCONCLUSIVE if E(k, g) has fewer than 2 sources or T(k, g) is empty",
                               "FAIL if any evaluable criterion C1 to C6 fails",
                               "INCONCLUSIVE if C2, C3, C4 or C5 is not evaluable",
                               "PASS otherwise"],
        "grid": "verdict per kernel under every reading of the grid (8, or 16 with the Lane axis); any kernel verdict differing across readings gives INCONCLUSIVE (rejected: unresolved input)",
        "overall": {"PASS": "all three kernels PASS under every reading of the grid",
                    "FAIL": "at least one kernel FAILs and every kernel verdict is identical across the grid (FAIL (mixed) if some kernels pass)",
                    "INCONCLUSIVE": "eligibility or evaluability not met, or nuisance disagreement",
                    "INVALID": "parity (stage 2) or D4 fails: no verdict, the law is never touched"},
        "multiplicity": "one pooled significance endpoint (C2) per kernel and reading; PASS needs every kernel and reading to pass "
                        "(intersection-union, Berger 1982), so no adjustment; C1, C3, C4, C5 only make PASS harder; "
                        "C1 is not evidence of improvement on each source",
        "robustnessLabels": ["PASS (robust)", "PASS (endpoint-sensitive)"],
    },
    "parity": {"rtol": 1e-9, "identicalStatus": True,
               "baseline": "calculate_meltpool_physics, absorption_model='flat-plate'",
               "fingerprint": FROZEN_FINGERPRINT},
    "stages": {"inputs": "docs/research/RESULT_regime_absorptivity_stage1_<date>.json",
               "baseline": "docs/research/RESULT_regime_absorptivity_stage2_<date>.json",
               "run": "docs/research/RESULTS_regime_absorptivity_<date>.json + .md",
               "order": "stage 1 and stage 2 are committed before the candidate law runs on any dataset row"},
}


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def config_sha256(cfg: Dict[str, Any] = CONFIG) -> str:
    return hashlib.sha256(canonical_json(cfg).encode("utf-8")).hexdigest()


def get_config() -> Dict[str, Any]:
    return copy.deepcopy(CONFIG)
