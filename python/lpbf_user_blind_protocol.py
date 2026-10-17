"""Protocol 1 of the user blind test: closed vocabularies, aliases, caps, divergences, wording and honesty literals.

Research hub spec (docs/research/SPEC_research_hub_data_2026-10-14.md) sections 2.1, 2.2, 3.2.1, 4.1 to 4.7 and 7.7.

`protocol_record()` is the rules record whose canonical sha256 is `protocolSha256`; it is exported to
`data/blind/lpbf-user-blind-protocol-v1.json` by `python/tools/lpbf_user_blind.py export-protocol` (`--check` compares).
Label and status sentences live in `wording_record()` (`data/blind/lpbf-user-blind-wording-v1.json`); its sha256 is
shown in reports for display only and enters no identity, so an approved wording change never relabels an old freeze.
A released protocol id is immutable: any rule change here needs a new `PROTOCOL_ID`.

Pure data and helpers; no solver import, no I/O at import time.
"""
from __future__ import annotations

import hashlib
import json
import re

PROTOCOL_ID = "lpbf-user-blind-protocol-1"
REQUEST_SCHEMA = "lpbf-user-blind-request-1"
METADATA_SCHEMA = "lpbf-user-blind-metadata-1"
PREVIEW_SCHEMA = "lpbf-user-blind-preview-1"
FREEZE_SCHEMA = "lpbf-user-blind-freeze-1"
RECEIPT_SCHEMA = "lpbf-user-blind-receipt-1"
REVEAL_SCHEMA = "lpbf-user-blind-reveal-1"
REPORT_SCHEMA = "lpbf-user-blind-report-1"
LIST_SCHEMA = "lpbf-user-blind-list-1"
GET_SCHEMA = "lpbf-user-blind-get-1"
BUNDLE_SCHEMA = "lpbf-user-blind-bundle-1"
STORE_SCHEMA = "lpbf-user-blind-store-1"
COMPARISON_CSV_NAME = "blind_comparison_v1.csv"

DATA_LABEL = "Measured (user-supplied)"   # lpbf_user_measurements.ROW_LABEL (maintainer decision Q15)
USER_TIER = "Declared"                     # trust tier of a local test (decision 6): nobody checked the table
SERVED_SOURCE_KIND = "Unresolved"
SERVED_SOURCE_REASON = "SERVED_VALUE_KIND_NOT_PROVIDED"
SERVED_SOURCE_LOCATOR = "docs/research/SPEC_research_hub_data_2026-10-14.md section 14.6"
CEILING_BADGE = "Screening only"

HONESTY = {
    "resultScope": "user-blind-test",
    "protocolId": PROTOCOL_ID,
    "notG3oRecord": True,
    "experimentalValidation": False,
    "appValidation": False,
    "labelPromotionProposed": "none",
    "evidenceKind": "screening-only",
    "dataLabel": DATA_LABEL,
    "neverEnters": {k: True for k in ("g3", "g3o", "n3", "n4", "physicsBump", "calibration", "leaderboard",
                                      "researchRegistry")},
    "g3Satisfied": False,
    "n3Counted": False,
}

# ---------------------------------------------------------------------------------------------- metadata (4.1)
ALLOYS = ("Ti-6Al-4V", "AlSi10Mg", "316L", "IN718", "IN625")
# Maintainer decision 2026-10-17 ("alasim kapsamini arttir"): the user's own blind test scores all five served alloys
# with the same thresholds and statistics. The thresholds and leverage cuts were registered (MELT) for Ti-6Al-4V and
# AlSi10Mg; they are reused unchanged for 316L, IN718 and IN625 with a label (divergence D6). Results are reported
# per alloy and never pooled: one freeze holds one alloy. This does not change the project's G3o or G3s objectives,
# which keep their pre-registered scope (Ti-6Al-4V and AlSi10Mg).
SCORED_ALLOYS = ("Ti-6Al-4V", "AlSi10Mg", "316L", "IN718", "IN625")
REGISTERED_ALLOYS = ("Ti-6Al-4V", "AlSi10Mg")
# Low cuts: MELT for Ti-6Al-4V and AlSi10Mg; 15 proposed for 316L and IN718 (spec 7.4 item 3, D6). IN625 has no low
# cut (the served IN625 rule is two-class at 13.6), so its leverage is not evaluable: a threshold failure is still
# reported as threshold-not-met, and an IN625 block that meets all four thresholds is inconclusive.
LEVERAGE_LOW_CUT = {"Ti-6Al-4V": 15.0, "AlSi10Mg": 15.0, "316L": 15.0, "IN718": 15.0}
STATS_ALLOY_KEY = {"Ti-6Al-4V": "Ti64", "AlSi10Mg": "AlSi10Mg"}

ENUMS = {
    "mode": ("pre-measurement", "post-measurement"),
    "alloy": ALLOYS,
    "quantity": ("melt-pool-depth",),
    "depthBoundary": ("etched-fusion-boundary", "unetched-contrast", "other"),
    "measurementMethod": ("optical-cross-section", "sem-cross-section", "other"),
    "depthDatum": ("original-surface", "powder-top", "cap-top", "depth-plus-height", "unresolved"),
    "reduction": ("per-section-raw", "per-track-mean-of-sections", "track-value-released", "condition-mean-released",
                  "maximum-only", "single-selected-section"),
    "crossSectionLocation": ("steady-state-mid-track", "several-locations", "near-track-start-or-end", "unstated"),
    "beam.quantity": ("diameter", "radius"),
    "beam.definition": ("1/e2", "D4sigma", "FWHM", "unstated"),
    "beam.basis": ("measured-work-plane", "measured-other-plane", "nominal"),
    "beam.profile": ("gaussian", "top-hat", "ring", "unknown"),
    "power.basis": ("measured-at-workpiece", "measured-elsewhere", "commanded", "unstated"),
    "substrate.kind": ("bare-plate", "powder-layer"),
    "substrate.surfacePreparation": ("machined", "ground", "polished", "blasted", "as-built", "other", "unstated"),
    "substrate.alsi10mgState": ("as-built", "heat-treated", "unstated"),
    "preheatBasis": ("measured", "set-point", "nominal-ambient"),
    "atmosphere": ("argon", "nitrogen", "helium", "vacuum", "air", "other", "unstated"),
    "depthUncertainty.basis": ("per-row", "block", "not-released"),
    "depthUncertainty.coverageFactor": (1, 2),
    "chemistry.basis": ("certified-heat-analysis", "supplier-nominal", "unstated"),
    "independence.predictionsViewedBeforeFreeze": ("no", "yes", "unsure"),
    "independence.dataPreviouslyPublished": ("no", "yes", "unknown"),
    "csvDialect": ("comma-dot", "semicolon-dot", "semicolon-comma"),
}
# Vapour-depression depth is protocol 1 descriptive only and needs the phase 6 research arm; not offered in v1.

BLOCK_LABEL_RE = r"^[A-Za-z0-9 ._()/-]{1,80}$"
ID_RE = r"^[A-Za-z0-9._-]{1,64}$"
FILE_NAME_RE = r"^[A-Za-z0-9 ._()-]{1,120}$"
FORMULA_START = ("=", "+", "-", "@")
SYNTHETIC_MARKER = "SYNTHETIC-EXAMPLE"

# ---------------------------------------------------------------------------------------------- CSV (4.2 to 4.4)
INPUT_COLUMNS = ("condition_id", "track_id", "section_id", "power_W", "speed_mm_s", "spot_um", "power_u_k1_W")
INPUT_ALIASES = {
    "power_W": ("P_W", "P", "power", "laser_power_W", "Power (W)"),
    "speed_mm_s": ("v_mm_s", "v", "speed", "scan_speed_mm_s", "Velocity (mm/s)", "Speed (mm/s)"),
    "spot_um": ("beam_um", "beam_diameter_um", "spot", "Spot (um)"),
    "condition_id": ("condition",),
    "track_id": ("track",),
    "section_id": ("section",),
    "power_u_k1_W": ("P_u_k1_W",),
}
TARGET_COLUMNS = ("condition_id", "track_id", "section_id", "depth_um", "width_um", "depth_u_um", "depth_status")
TARGET_ALIASES = {
    "depth_um": ("depth", "D_um", "penetration_depth_um", "Depth (um)"),
    "width_um": ("width", "W_um", "Width (um)"),
    "condition_id": ("condition",),
    "track_id": ("track",),
    "section_id": ("section",),
    "depth_status": (),
    "depth_u_um": (),
}
# Unit tables: canonical column -> {unit token (case folded): factor to the canonical unit}.
UNITS = {
    "power_W": {"w": 1.0, "kw": 1000.0},
    "power_u_k1_W": {"w": 1.0, "kw": 1000.0},
    "speed_mm_s": {"mm/s": 1.0, "m/s": 1000.0, "mm/min": 1.0 / 60.0},
    "spot_um": {"um": 1.0, "µm": 1.0, "micron": 1.0, "mm": 1000.0},
}
CANONICAL_UNIT = {"power_W": "W", "power_u_k1_W": "W", "speed_mm_s": "mm/s", "spot_um": "um"}
UNITLESS_HEADERS = {"p": "power_W", "power": "power_W", "v": "speed_mm_s", "speed": "speed_mm_s",
                    "spot": "spot_um"}
TARGET_LIKE_RE = r"depth|width|height|cap|area|penetration|remelt|d_exp|w_exp|d_obs|aspect"
TARGET_LIKE_EXACT = ("d", "w")
DEPTH_STATUS = ("measured", "track-not-formed", "specimen-lost", "section-unreadable", "not-measured")
LOSS_STATUS = ("specimen-lost", "section-unreadable", "not-measured")

RANGES = {"power_W": (10.0, 2000.0, "W"), "speed_mm_s": (1.0, 10000.0, "mm/s"), "spot_um": (10.0, 1000.0, "um"),
          "power_u_k1_W": (0.0, 2000.0, "W")}
TARGET_RANGES = {"depth_um": (1.0, 3000.0), "width_um": (5.0, 3000.0)}
WAVELENGTH_RANGE = (1030.0, 1100.0)
LAYER_RANGE = (5.0, 200.0)
PREHEAT_RANGE = (-50.0, 1000.0)

CAPS = {"fileBytes": 256 * 1024, "base64Chars": 350_000, "rows": 2000, "conditions": 48,
        "storeFreezes": 500, "storeBytes": 200 * 1024 * 1024, "minScoredConditions": 12,
        "lossShareMax": "0.20"}
# Condition cap 48 (5 served calls each): the served timing spike (docs/research/SPIKE_served_timing_2026-10-15.md)
# measured a p95 of 77.5 ms per call without the process map, so 240 calls take about 19 s, under the 60 s target.
FREEZE_ESTIMATE_S_PER_CALL = 0.0775
FREEZE_QUEUE_NOTE = "A freeze can hold the simulation queue for up to about a minute."

THRESHOLDS = {"median": "0.20", "p90": "0.35", "meanSigned": "0.10", "maxApe": "0.50", "nMin": 12, "uMax": "0.10",
              "source": ("MELT pre-registration Amendment 6 values, reused as fixed protocol 1 constants; this result "
                         "is not a G3o record")}

ARMS = ("served", "served:P-5%", "served:P+5%", "served:d-5%", "served:d+5%", "research:melt-link",
        "research:cavity", "context:fabbro")
SCORED_ARMS = ("served", "research:melt-link")
RESEARCH_ARMS = ("research:melt-link", "research:cavity")
STATUS_WORDS = ("thresholds-met", "threshold-not-met", "inconclusive", "descriptive-not-scored",
                "descriptive-exposed", "unavailable")
BLINDNESS = ("blind-committed", "blind-prospective-declared", "blind-retrospective-declared",
             "not-blind-predictions-viewed", "not-blind-predictions-revealed", "not-blind-earlier-test-overlap",
             "not-blind-rescored-changed-targets", "not-blind-data-already-used-by-app", "not-blind-app-history",
             "not-blind-used-for-calibration")
REVEAL_PHRASE = "reveal predictions and end blind status"

RPC_TYPES = ("user-blind-preview", "user-blind-list", "user-blind-get")
JOB_TYPES = ("user-blind-freeze", "user-blind-reveal", "user-blind-score", "user-blind-bundle", "user-blind-open")
JOB_TIMEOUT_S = {"user-blind-freeze": 180.0, "user-blind-score": 60.0, "user-blind-reveal": 30.0,
                 "user-blind-bundle": 60.0, "user-blind-open": 30.0}
ARTIFACT_NAMES = ("blind-receipt.json", "blind-freeze.json", "blind-report.json", "blind-bundle.tar",
                  "blind-comparison.csv")
ACKNOWLEDGEMENTS = ("predeterminedInconclusive", "powderLayerDescriptive", "exposedDescriptive",
                    "publishedConditionOverlap", "calibrationOverlap")

DIVERGENCES = (
    {"id": "D1", "rule": ("declared measurement losses (specimen-lost, section-unreadable, not-measured) are excluded, "
                          "listed and counted at section, track and condition level; above 20 % of tracks or of "
                          "conditions is a block issue; a status change after an attempt is a changed targets file"),
     "melt": "MELT reduce_conditions refuses a missing or non-positive target; GOAL kill criterion 3"},
    {"id": "D2", "rule": "a boundary that is not an etched fusion boundary is a block issue",
     "melt": "MELT block_level_issues has no boundary item"},
    {"id": "D3", "rule": "a cross-section location near track ends or unstated is a block issue",
     "melt": "no MELT item"},
    {"id": "D4", "rule": "beam profile top-hat or ring is a block issue; unknown is a label only",
     "melt": "no MELT item"},
    {"id": "D5", "rule": "a missing plate temperature refuses (PREHEAT_MISSING); nominal-ambient is labelled",
     "melt": "MELT: initial temperature not released is a block issue"},
    {"id": "D6", "rule": ("thresholds and statistics registered for Ti-6Al-4V and AlSi10Mg are reused unchanged for "
                          "316L, IN718 and IN625 with a label; low cut 15 proposed for 316L and IN718; IN625 leverage "
                          "is not evaluable (a step 5 qualifier); results are reported per alloy and never pooled "
                          "(maintainer decision 2026-10-17); the G3o and G3s objectives keep their registered scope"),
     "melt": "MELT registers thresholds and leverage cuts for Ti-6Al-4V and AlSi10Mg only"},
    {"id": "D7", "rule": "protocol 1 scores the served Build Job melt-pool depth",
     "melt": "MELT scores its registered arm catalogue"},
    {"id": "D8", "rule": "the research arm would be P8 linkedMeltDepth_um, not the registered S2 candidate",
     "melt": "MELT S2 is the registered melt-link candidate"},
    {"id": "D9", "rule": "blindness statuses of 6.4, several of them declared by the user",
     "melt": "MELT exposure: a target read before the prediction hash"},
    {"id": "D10", "rule": "status words thresholds-met, threshold-not-met, inconclusive and the descriptive words",
     "melt": "MELT status words PASS, FAIL, INCONCLUSIVE"},
    {"id": "D11", "rule": "track-not-formed counts as APE +inf for every arm",
     "melt": "MELT refuses a non-positive target"},
    {"id": "D12", "rule": "research band coverage and consistency counts (protocol 2 only; inactive here)",
     "melt": "no MELT counterpart"},
    {"id": "G1", "rule": ("protocol 1 records the research arm as RESEARCH_NOT_REQUESTED; keyholeCavity is never "
                          "scored against melt-pool depth"),
     "melt": "GOAL roadmap item 1: served and P8 side by side"},
)

TEMPLATE_INPUT_HEADER = ("condition_id", "track_id", "section_id", "power_W", "speed_mm_s", "spot_um")
TEMPLATE_TARGET_HEADER = ("condition_id", "track_id", "section_id", "depth_um", "width_um", "depth_u_um",
                          "depth_status")


def protocol_record():
    """The rules record (no sentences beyond rule text). Its canonical sha256 is protocolSha256."""
    return {
        "schema": "lpbf-user-blind-protocol-record-1",
        "protocolId": PROTOCOL_ID,
        "requestSchema": REQUEST_SCHEMA,
        "metadataSchema": METADATA_SCHEMA,
        "enums": {k: list(v) for k, v in ENUMS.items()},
        "scoredAlloys": list(SCORED_ALLOYS), "registeredAlloys": list(REGISTERED_ALLOYS),
        "leverageLowCut": LEVERAGE_LOW_CUT,
        "regex": {"blockLabel": BLOCK_LABEL_RE, "id": ID_RE, "fileName": FILE_NAME_RE,
                  "targetLike": TARGET_LIKE_RE, "formulaStart": list(FORMULA_START),
                  "syntheticMarker": SYNTHETIC_MARKER},
        "inputColumns": list(INPUT_COLUMNS), "inputAliases": {k: list(v) for k, v in INPUT_ALIASES.items()},
        "targetColumns": list(TARGET_COLUMNS), "targetAliases": {k: list(v) for k, v in TARGET_ALIASES.items()},
        "targetLikeExact": list(TARGET_LIKE_EXACT),
        "units": UNITS, "canonicalUnit": CANONICAL_UNIT, "unitlessHeaders": UNITLESS_HEADERS,
        "depthStatus": list(DEPTH_STATUS), "lossStatus": list(LOSS_STATUS),
        "ranges": {k: list(v) for k, v in RANGES.items()},
        "targetRanges": {k: list(v) for k, v in TARGET_RANGES.items()},
        "wavelengthRange_nm": list(WAVELENGTH_RANGE), "layerRange_um": list(LAYER_RANGE),
        "caps": CAPS, "thresholds": THRESHOLDS,
        "arms": list(ARMS), "scoredArms": list(SCORED_ARMS),
        "researchArms": {a: "RESEARCH_NOT_REQUESTED" for a in RESEARCH_ARMS},
        "statusWords": list(STATUS_WORDS), "blindness": list(BLINDNESS),
        "revealPhrase": REVEAL_PHRASE,
        "requestTypes": {"rpc": list(RPC_TYPES), "jobs": list(JOB_TYPES)},
        "artifactNames": list(ARTIFACT_NAMES),
        "acknowledgements": list(ACKNOWLEDGEMENTS),
        "divergences": [dict(d) for d in DIVERGENCES],
        "templates": {"inputs": list(TEMPLATE_INPUT_HEADER), "targets": list(TEMPLATE_TARGET_HEADER)},
        "servedClosurePin": "data/blind/served-closure-pin-v1.json",
        "honesty": HONESTY,
    }


# ---------------------------------------------------------------------------------------------- wording (2.2)
# Proposals (Q1 not yet answered for these strings); kept in one table so approval is a one-file change.
WORDING = {
    "tab": "Your blind test",
    "reportTitle": "Your blind test on your own measurements",
    "banner": ("This is your test of the model on your data. It is not validation of this app, and the app's "
               "evidence labels do not change (experimentalValidation false)."),
    "receiptLine": "Predictions frozen. Values are withheld until you upload your measurements or choose to reveal them.",
    "status": {
        "thresholds-met": "All four thresholds were met on your data, with leverage and resolution met.",
        "threshold-not-met": "At least one threshold was not met on your data: {list}.",
        "inconclusive": "Inconclusive: {reason}. The statistics are shown for information.",
        "descriptive-not-scored": "Shown for information, not scored: {reason}.",
        "descriptive-exposed": "Not blind: {reason}. The statistics are shown for information.",
        "unavailable": "Research arm not available: {reason}.",
    },
    "blindness": {
        "blind-committed": "Blind: your targets file was fixed by its hash before the predictions were frozen.",
        "blind-prospective-declared": "Blind as you declared: you froze the predictions before measuring.",
        "blind-retrospective-declared": ("Blind as you declared: you measured before freezing, and no commitment of "
                                         "the targets was matched."),
        "not-blind-predictions-viewed": "Not blind: you declared that you viewed predictions for these conditions.",
        "not-blind-predictions-revealed": "Not blind: the frozen predictions were revealed before this score.",
        "not-blind-earlier-test-overlap": ("Not blind: {k} conditions match a test on this computer that was "
                                           "revealed or scored earlier."),
        "not-blind-rescored-changed-targets": "Not blind: this attempt uses a targets file that differs from attempt 1.",
        "not-blind-data-already-used-by-app": "Not blind: these data or conditions are in this app's spent ledger ({id}).",
        "not-blind-app-history": ("Not blind: Build Job history on this computer holds these conditions before the "
                                  "freeze (partial check)."),
        "not-blind-used-for-calibration": ("Not blind: these conditions were used for machine calibration on this "
                                           "computer ({id})."),
    },
    "servedValueLabel": "Unresolved: the served result does not yet list the source of each value.",
    "researchReason": "not requested: the P8 research route accepts requests only from the Research model panel today",
    "researchReview": "Research arm: not requested in this version",
    "thresholdsReused": "thresholds reused unchanged for {alloy}; registered for Ti-6Al-4V and AlSi10Mg",
    "alloyScope": "statistics for {alloy} only; never pooled with other alloys",
    "anchorAdvice": ("Share freezeSha256 with someone outside this computer, or commit it to a repository, before you "
                     "measure or upload measurements. This app cannot prove the order of events by itself."),
    "relNote": "rel is a fraction (pred - obs) / obs; positive means the model is deeper",
    "doNotResave": ("Do not open and save this file again before you upload it for scoring: saving it, even unchanged, "
                    "in a spreadsheet program usually changes its bytes, and the hash will no longer match."),
    "blockIssueFix": {
        "DATUM_NOT_ORIGINAL_SURFACE": "Measure depth from the original plate surface, or state the datum you used.",
        "REDUCTION_UNUSABLE": "Upload one row per track or per section, not a maximum or a single selected section.",
        "SECTIONS_WITHOUT_TRACK": "Add track_id so sections are grouped by track.",
        "PLATE_THICKNESS_NOT_RELEASED": "State the plate thickness.",
        "ATMOSPHERE_UNSTATED": "State the process atmosphere.",
        "SURFACE_PREPARATION_UNSTATED": "State how the plate surface was prepared.",
        "INDEPENDENCE_NOT_ESTABLISHED": "State whether these data were published before.",
        "BOUNDARY_NOT_ETCHED": "Measure on an etched fusion boundary.",
        "LOCATION_NEAR_ENDS_OR_UNSTATED": ("State the cross-section location; sections near track ends measure start "
                                           "or end transients."),
        "BEAM_PROFILE_NOT_GAUSSIAN": "The served model assumes a Gaussian beam; top-hat and ring beams are outside it.",
        "LOSSES_ABOVE_20_PERCENT": "More than 20 % of tracks or conditions were lost; measure more sections.",
    },
}


def wording_record():
    return {"schema": "lpbf-user-blind-wording-1", "protocolId": PROTOCOL_ID, "approved": False,
            "note": "Proposed wording (maintainer question Q1); not part of any identity.", "wording": WORDING}


# ---------------------------------------------------------------------------------------------- canonical JSON
def canonical_bytes(obj):
    """UTF-8, LF, sorted keys, no spaces, ASCII escapes, floats as Python repr; NaN and inf refused."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def sha256_hex(data):
    return hashlib.sha256(data).hexdigest()


def canonical_sha256(obj):
    return sha256_hex(canonical_bytes(obj))


def protocol_sha256():
    return canonical_sha256(protocol_record())


def wording_sha256():
    return canonical_sha256(wording_record())


def text_cell_safe(value):
    """Python twin of TypeScript blindCsvTextCell: a text cell starting with = + - @ tab or CR gets a leading
    apostrophe; numbers are never prefixed."""
    if isinstance(value, bool) or value is None:
        return "" if value is None else str(value).lower()
    if isinstance(value, (int, float)):
        return value
    text = str(value)
    if text and text[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + text
    return text


HEX64 = re.compile(r"^[0-9a-f]{64}$")


# ---------------------------------------------------------------------------------------------- refusals (6.1)
REFUSALS = {
    "INPUTS_TARGET_COLUMN": ("Column '{name}' may be a measurement (it contains '{token}'). The inputs file carries "
                             "inputs only; put measurements in the targets file, or remove the column if it is not a "
                             "measurement."),
    "INPUTS_COLUMN_MISSING": "Column {name} is required (or one of its aliases: {aliases}).",
    "TARGETS_COLUMN_MISSING": "Column {name} is required (or one of its aliases: {aliases}).",
    "FILE_EMPTY": "The file has a header but no data rows.",
    "CSV_MALFORMED": "Row {row}: the line could not be read as CSV ({why}).",
    "HEADER_UNIT_UNKNOWN": ("Column '{name}' states the unit '{unit}', which this form does not convert. "
                            "Use {accepted}."),
    "TARGET_STATUS_UNKNOWN": ("Row {row}: depth_status must be blank or one of measured, track-not-formed, "
                              "specimen-lost, section-unreadable, not-measured."),
    "U_PER_ROW_VARIES": "Condition {id}: depth_u_um differs between rows; give one uncertainty per condition.",
    "BLIND_SUBMIT_INTERNAL": ("The request could not be processed. Nothing was stored. Check the file against the "
                              "template and try again."),
    "STORE_LOCK_DOMAIN": "This store is used by the {domain} worker. Run the CLI in the same environment as the worker.",
    "INPUTS_UNKNOWN_COLUMN": ("Column '{name}' is not an input column. Allowed: condition_id, track_id, section_id, "
                              "power_W, speed_mm_s, spot_um, power_u_k1_W, or a listed alias."),
    "AMBIGUOUS_ALIAS": "Columns '{a}' and '{b}' both mean {canonical}. Keep one.",
    "FILE_NOT_CSV_UTF8": ("This file is not UTF-8 CSV text (it may be an Excel workbook). In Excel use Save As, "
                          "CSV UTF-8."),
    "DIALECT_MISMATCH": ("Row {row}, column {col}: decimal comma found, but the declared format is comma separated "
                         "with decimal points. Choose \"semicolon separated, decimal comma\" or re-export."),
    "DIALECT_MISMATCH#header": ("The header is separated by {found}, but the declared format is {declared}. "
                                "Choose {choice}."),
    "NUMBER_INVALID": "Row {row}, column {col}: not a plain positive number (no units, no thousands separators).",
    "OUT_OF_RANGE": "Row {row}, column {col}: outside {lo} to {hi} {unit}. {hint}",
    "ID_INVALID": ("Row {row}: {col} must be 1 to 64 letters, digits, dots, underscores or hyphens, not starting "
                   "with = + - @."),
    "SYNTHETIC_EXAMPLE_ROW": "Row {row} is the template's synthetic example. Delete it before uploading your own data.",
    "FILE_NAME_INVALID": ("The file name may use letters, digits, spaces, dots, underscores, hyphens and brackets "
                          "(1 to 120 characters), not starting with = + - @ or a dot. Rename the file and pick it "
                          "again."),
    "DUPLICATE_KEY": "Rows {a} and {b} have the same condition, track and section.",
    "CONDITION_INCONSISTENT": "Condition {id}: rows differ in power, speed or spot. One condition is one setting.",
    "CONDITION_DUPLICATE_SETTING": ("Conditions {a} and {b} have identical power, speed and spot. Merge them as "
                                    "tracks of one condition."),
    "SECTION_WITHOUT_TRACK": "Row {row}: section_id needs track_id.",
    "REPEATED_ROWS_NO_TRACK": ("Condition {id} has several rows and no track_id. Add track_id, or declare that each "
                               "row is a separate track."),
    "CONDITION_INCONSISTENT#track": "Track {id} appears with different power, speed or spot. Give each track one setting.",
    "REPLICATION_MISMATCH": ("You declared {k} tracks per condition and {m} sections per track; the file differs for "
                             "conditions {list}."),
    "SIZE_CAP": ("The file exceeds {cap}. Split the campaign into blocks; each block needs at least 12 conditions "
                 "to be scored."),
    "ALLOY_NOT_SERVED": "{alloy} has no served melt-pool model in this app.",
    "WAVELENGTH_OUT_OF_SCOPE": ("The served model is an infrared flat-plate model (1030 to 1100 nm); the stated "
                                "wavelength is outside it."),
    "BEAM_MISSING": "No beam diameter: give spot_um per row or one block beam diameter.",
    "PREHEAT_MISSING": "The plate temperature before the first track is required to compute predictions.",
    "METADATA_FIELD": "{message}",
    "ACK_REQUIRED": "This design can at best end {status} ({reason}). Tick the acknowledgement to freeze anyway.",
    "OVERLAP_CHANGED": ("Since your check, {k} conditions newly overlap a test or calibration data on this computer. "
                        "Run the check again."),
    "PREVIEW_DRIFT": "The request differs from the check you reviewed, or the predictor changed. Run the check again.",
    "PREDICTOR_NOT_PINNED": ("The running solver does not match the reviewed served model ({files}), so predictions "
                             "cannot be frozen from an unreviewed build. Restore the listed files or install a "
                             "reviewed release; a developer changes the pin only in a reviewed commit."),
    "PROTOCOL_CHANGED": ("The protocol rules changed since this test was frozen under the same protocol id. This test "
                         "cannot be scored by this build."),
    "STORE_READ_ONLY": "This installation is read-only.",
    "STORE_FULL": "The blind test store is full; see the guide for manual archiving.",
    "STORE_LEDGER_BROKEN": ("The blind test ledger on this computer does not verify, so nothing new is written. The "
                            "store may have been edited outside the app; see the guide. Existing tests can still be "
                            "read and exported."),
    "STORE_LOCKED": "Another blind job holds the store. Try again when it finishes.",
    "STORE_SHARED_HOST": ("This server is reachable by other users, so blind tests are switched off. An operator can "
                          "declare a single-user install (see the guide)."),
    "FREEZE_UNKNOWN": "No frozen test with this key on this computer.",
    "TARGETS_KEYS_MISMATCH": ("The targets file must list exactly the frozen rows: {m} missing, {e} extra, {d} "
                              "duplicate (first: {first})."),
    "TARGET_DEPTH_INVALID": ("Row {row}: a measured row needs a positive depth_um; for a lost or unreadable section "
                             "set depth_status and leave depth_um blank."),
    "TARGET_STATUS_CONFLICT": "Row {row}: depth_status {status} needs an empty depth_um.",
    "TARGET_STATUS_CONFLICT#track": "Row {row}: track-not-formed must cover every section of its track.",
    "INPUT_REPEAT_MISMATCH": ("Row {row}: {col} differs from the frozen input. The targets file may repeat inputs "
                              "only unchanged."),
    "U_PER_ROW_MISSING": "Row {row}: depth_u_um is required because the uncertainty basis is per row.",
    "COMMITMENT_MISMATCH": ("This targets file does not match the hash you committed before the freeze. Upload the "
                            "committed file, or continue; the result is then marked \"commitment not matched\"."),
    "FREEZE_ALTERED": "The freeze record or its hash file changed after it was written. Not scored.",
    "CONFIRMATION_PHRASE": "Type the phrase exactly to reveal the predictions.",
    "REVEAL_REQUIRED": ("This shows or exports the frozen predictions, which ends blind status. Reveal them first, or "
                        "confirm the reveal phrase with this request."),
    "TARGET_OUT_OF_RANGE": "Row {row}, column {col}: outside {lo} to {hi} um. {hint}",
    "DOCUMENT_UNAVAILABLE": "This document does not exist yet for this test.",
    "SOLVER_EXCEPTION": "The served solver failed. Nothing was frozen.",
    "INTERNAL_ERROR": "The blind job failed. Nothing was stored. Try again; if it repeats, report the code.",
}


REFUSAL_CODES = tuple(sorted({k.split("#")[0] for k in REFUSALS}))


class BlindRefusal(ValueError):
    """A refusal with a closed code. Its text is the fixed message (never an exception message or a cell value);
    `detail` holds row numbers, column names and counts only."""

    def __init__(self, code, field=None, detail=None, variant=None, **fmt):
        key = f"{code}#{variant}" if variant else code
        if key not in REFUSALS:
            code, key, fmt = "INTERNAL_ERROR", "INTERNAL_ERROR", {}
        try:
            message = REFUSALS[key].format(**fmt)
        except (KeyError, IndexError, ValueError):
            message = REFUSALS["BLIND_SUBMIT_INTERNAL"]
        super().__init__(message)
        self.code = code
        self.field = field
        self.detail = dict(detail or {})
        self.message = message

    def envelope(self):
        return {"success": False, "errorKind": "validation",
                "error": {"code": self.code, "field": self.field, "message": self.message, "detail": self.detail}}
