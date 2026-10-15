"""P8 research route: reason-code registry, option-rule texts and label tables (integration contract 2026-10-15,
sections 7 to 9).

The runtime registry holds the closed code list of contract 9.1 with class, scope and the causes each code may carry,
the precedence rule, the option-problem rules and message templates of 9.3, the request field labels the request
checks need, and (Revision 3, section 14) the closed sender list with its supersedeKey rules, the relay limits and the
blind relay projection BLIND_RELAY_V1. The leaf labels (7.1, 13.4), the per-code noun phrases and n/a templates of 9.2
and the served-difference templates of section 8 are W-1 drafts awaiting maintainer approval.

Research only: no served module may import this file (guard R-ISO-1, python/test_lpbf_research_isolation.py).
Every English string here is a W-1 draft.
"""

from __future__ import annotations

import hashlib
import json
import re
from types import MappingProxyType
from typing import Any, Mapping

REGISTRY_REVISION = "p8-research-codes-v2-phase-c"

# Class order is the precedence order: a null leaf carries the code of the lowest class number among its causes
# (contract 9.1); W is never a reasonCode.
CLASS_ORDER = ("C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10")
WARNING_CLASS = "W"

CAUSES = ("request", "evaluator", "option", "alloy-not-admitted", "software-limit", "source-range", "input-missing",
          "default-cleared", "domain", "upstream", "convention", "comparison", "numerical", "closure-falsified",
          "closure-missing", "data-missing", "band")


def _codes(cls: str, scope: tuple, causes: tuple, *names: str) -> dict:
    return {name: MappingProxyType({"class": cls, "scope": scope, "causes": causes}) for name in names}


_REASON_CODES: dict = {}
_REASON_CODES.update(_codes("C1", ("request",), ("request",),
                            "RESEARCH_REQUEST_INVALID", "PROPERTY_SNAPSHOT_MISMATCH", "RESEARCH_CODE_STALE",
                            "RESEARCH_TIMEOUT"))
_REASON_CODES.update(_codes("C2", ("request", "module", "arm"), ("evaluator",),
                            "RESEARCH_EVALUATION_FAILED", "RESEARCH_SERIALIZATION_FAILED",
                            "RESEARCH_RESPONSE_TOO_LARGE"))
_REASON_CODES.update(_codes("C3", ("module",), ("option",),
                            "RESEARCH_OPTIONS_INVALID", "RESEARCH_PRESET_ALLOY_MISMATCH",
                            "SURFACTANT_BINARY_COMBINATION_UNSUPPORTED", "RESEARCH_ARM_LIMIT_EXCEEDED"))
_REASON_CODES.update(_codes("C4", ("module",), ("alloy-not-admitted",),
                            "ALLOY_CONSTANT_CHAIN_NOT_ADMITTED", "ALLOY_NOT_ALSI10MG", "UNSOURCED_PROPERTY_OVERRIDE"))
_REASON_CODES.update(_codes("C5", ("module", "leaf"), ("software-limit", "source-range"),
                            "INVALID_INPUT", "PREHEAT_OUTSIDE_PROPERTY_SCOPE", "WAVELENGTH_UNSUPPORTED",
                            "POWDER_CONTEXT_UNSUPPORTED", "PECLET_OUTSIDE_NUMERICAL_SCOPE",
                            "ASPECT_BOUND_OUTSIDE_NUMERICAL_SCOPE", "NUMERICAL_INPUT_BELOW_FLOOR",
                            "VAPOUR_PRESSURE_OUTSIDE_SOURCE_RANGE"))
_REASON_CODES.update(_codes("C6", ("module", "leaf"), ("input-missing", "default-cleared", "domain",
                                                       "alloy-not-admitted"),
                            "SURFACE_VAPOUR_INPUT_REQUIRED", "MARANGONI_VISCOSITY_INPUT_REQUIRED",
                            "MARANGONI_SOLUTE_INPUT_REQUIRED", "ONSET_REFERENCE_UNAVAILABLE"))
_REASON_CODES.update(_codes("C7", ("leaf",), ("upstream", "convention", "comparison"),
                            "MELT_LINK_NOT_AVAILABLE", "NOT_APPLICABLE_BELOW_ONSET", "NOT_APPLICABLE_FOR_CONVENTION",
                            "ONSET_COMPARISON_EVENT_MISMATCH", "ONSET_COMPARISON_TUPLE_MISMATCH"))
_REASON_CODES.update(_codes("C8", ("leaf", "arm"), ("numerical",),
                            "CYLINDER_CONVERGENCE_FAILED", "OPTICAL_TRACE_UNRESOLVED", "CAVITY_ROOT_SCAN_UNRESOLVED",
                            "CAVITY_RESIDUAL_FAILED", "NO_STRICTLY_STABLE_ROOT", "CONDUCTION_EXTENT_UNRESOLVED",
                            "MELT_BRACKET_FAILURE", "MELT_OPTIMIZER_FAILURE", "MELT_CONVERGENCE_FAILED",
                            "TIP_SHELL_UNRESOLVED", "SURFACE_BALANCE_NO_BRACKET",
                            "SURFACE_BALANCE_CONVERGENCE_FAILED", "NONFINITE_RESULT"))
_REASON_CODES.update(_codes("C9", ("leaf",), ("closure-falsified", "closure-missing", "data-missing"),
                            "MARANGONI_SURFACE_CHEMISTRY_UNAVAILABLE", "MARANGONI_TRANSPORT_CLOSURE_UNAVAILABLE",
                            "SURFACE_BALANCE_CLOSURE_FALSIFIED", "POWDER_ALLOY_OPTICAL_CONSTANTS_UNAVAILABLE",
                            "POWDER_LOT_INPUTS_UNAVAILABLE", "POWDER_THERMAL_OPERATOR_UNAVAILABLE",
                            "KEYHOLE_THERMAL_FLOW_CLOSURE_UNAVAILABLE", "SOURCE_RANGE_NOT_ESTABLISHED"))
_REASON_CODES.update(_codes("C10", ("band",), ("band",),
                            "BAND_PENDING", "BAND_NO_SUCCESSFUL_ARM", "BAND_MANIFEST_NOT_DECLARED"))
REASON_CODES: Mapping[str, Mapping[str, Any]] = MappingProxyType(_REASON_CODES)

WARNING_CODES = frozenset({
    "LOW_PE_HYDRODYNAMICS_OMITTED", "LOW_ASPECT_CAVITY_MECHANICS_OMITTED", "THERMAL_CYLINDER_CLOSURE_EXTRAPOLATED",
    "SOURCE_SCOPE_TRANSFER", "FIELD_SHAPE_STEP_NEAR_ONSET", "VAPOUR_PRESSURE_EXTRAPOLATED",
    "HKL_SUBBOILING_FIXED_BETA", "VAPOUR_CONSTANT_LV_EXTREME_EXTRAPOLATION", "USER_COEFFICIENT_PAIR_DECOUPLED",
    "FE_ANALOGUE_BASELINE_SUBSTITUTED",
})

# Never cached (contract 3.6): request-scope failures, evaluator bugs and timeouts.
TRANSIENT_CODES = frozenset(code for code, entry in _REASON_CODES.items() if entry["class"] in ("C1", "C2"))
# Deterministic for the same inputs, so an arm record failed with one of them is cacheable (C3 to C9).
DETERMINISTIC_CODES = frozenset(code for code, entry in _REASON_CODES.items()
                                if entry["class"] in ("C3", "C4", "C5", "C6", "C7", "C8", "C9"))

TIMEOUT_KINDS = ("queue", "run", "reply", "adhoc")


def code_class(code: str) -> str:
    if code in WARNING_CODES:
        return WARNING_CLASS
    entry = REASON_CODES.get(code)
    if entry is None:
        raise KeyError(f"unregistered research reason code: {code!r}")
    return entry["class"]


def winning_code(codes_in_detection_order) -> str | None:
    """Precedence of contract 9.1: lowest class number; inside one class the first detected. Warnings never win."""
    best = None
    best_rank = None
    for code in codes_in_detection_order:
        cls = code_class(code)
        if cls == WARNING_CLASS:
            raise ValueError(f"warning {code} can never be a reasonCode")
        rank = CLASS_ORDER.index(cls)
        if best_rank is None or rank < best_rank:
            best, best_rank = code, rank
    return best


# --- Option problems (contract 9.3) ------------------------------------------------------------------------------

OPTION_RULES: Mapping[str, Mapping[str, str]] = MappingProxyType({
    "unknown-key": MappingProxyType({"scope": "request", "code": "RESEARCH_REQUEST_INVALID",
                                     "template": "Unknown key {pointer}."}),
    "wrong-type": MappingProxyType({"scope": "request", "code": "RESEARCH_REQUEST_INVALID",
                                    "template": "{label} must be a {type}."}),
    "not-positive": MappingProxyType({"scope": "request", "code": "RESEARCH_REQUEST_INVALID",
                                      "template": "{label} must be greater than 0; got {value}."}),
    "too-large": MappingProxyType({"scope": "request", "code": "RESEARCH_REQUEST_INVALID",
                                   "template": "The research request exceeds 65536 bytes."}),
    "alloy-material-mismatch": MappingProxyType({"scope": "request", "code": "RESEARCH_REQUEST_INVALID",
                                                 "template": "Alloy {value} does not match material {material}."}),
    "snapshot-hash-mismatch": MappingProxyType({
        "scope": "request", "code": "PROPERTY_SNAPSHOT_MISMATCH",
        "template": ("The Build Job used a different material property revision. Re-run the Build Job, then run "
                     "research models.")}),
    "not-finite": MappingProxyType({"scope": "module", "code": "RESEARCH_OPTIONS_INVALID",
                                    "template": "{label} must be a finite number."}),
    "below-min": MappingProxyType({"scope": "module", "code": "RESEARCH_OPTIONS_INVALID",
                                   "template": "{label} must be between {min} and {max} {unit}; got {value}."}),
    "above-max": MappingProxyType({"scope": "module", "code": "RESEARCH_OPTIONS_INVALID",
                                   "template": "{label} must be between {min} and {max} {unit}; got {value}."}),
    "range-inverted": MappingProxyType({"scope": "module", "code": "RESEARCH_OPTIONS_INVALID",
                                        "template": "The range for {label} has min {min} above max {max}."}),
    "range-excludes-nominal": MappingProxyType({
        "scope": "module", "code": "RESEARCH_OPTIONS_INVALID",
        "template": ("The range for {label} ({min} to {max} {unit}) does not contain its current value {nominal}. "
                     "Widen the range or reset it.")}),
    "range-without-nominal": MappingProxyType({
        "scope": "module", "code": "RESEARCH_OPTIONS_INVALID",
        "template": "{label} has no value (input required), so a range cannot be used."}),
    "mode-field-ignored": MappingProxyType({"scope": "module", "code": "RESEARCH_OPTIONS_INVALID",
                                            "template": "{label} is not used in {mode}. Clear it or change the mode."}),
    "binary-combination": MappingProxyType({
        "scope": "module", "code": "SURFACTANT_BINARY_COMBINATION_UNSUPPORTED",
        "template": "Enter soluble S or soluble O, not both; the two Fe analogues cannot be combined."}),
    "preset-alloy-mismatch": MappingProxyType({"scope": "module", "code": "RESEARCH_PRESET_ALLOY_MISMATCH",
                                               "template": "Vapour preset {value} is defined for {presetAlloy} only."}),
    # Revision 3 (14.1 item 2): sender and relay rules, request scope.
    "sender-key-mismatch": MappingProxyType({
        "scope": "request", "code": "RESEARCH_REQUEST_INVALID",
        "template": "Supersede key {value} does not match sender {sender} (expected {expected})."}),
    "relay-sender-mismatch": MappingProxyType({"scope": "request", "code": "RESEARCH_REQUEST_INVALID",
                                               "template": "Sender {sender} cannot send a relay."}),
    "relay-options-forbidden": MappingProxyType({
        "scope": "request", "code": "RESEARCH_REQUEST_INVALID",
        "template": "Research options are not accepted {context}; the relay uses the default research inputs."}),
    "relay-required": MappingProxyType({"scope": "request", "code": "RESEARCH_REQUEST_INVALID",
                                        "template": "A blind-freeze band request needs a relay."}),
})

MAX_PROBLEM_VALUE_CHARS = 64

# Request field labels used in request-check messages (W-1 drafts). Research option labels come from the control
# table of the describe stage (phase C).
REQUEST_FIELD_LABELS: Mapping[str, str] = MappingProxyType({
    "": "The research request",
    "/schemaVersion": "Request schema version",
    "/supersedeKey": "Supersede key",
    "/clientRequestId": "Client request id",
    "/stage": "Stage",
    "/timeBudgetMs": "Time budget (ms)",
    "/process": "Process",
    "/process/material": "Material",
    "/process/laserPower_W": "Laser power (W)",
    "/process/scanSpeed_mm_s": "Scan speed (mm/s)",
    "/process/beamDiameter_um": "Beam diameter (um)",
    "/process/preheatTemp_C": "Preheat temperature (C)",
    "/process/laserWavelength": "Laser wavelength",
    "/process/absorptionModel": "Absorption model",
    "/propertyContext": "Property context",
    "/propertyContext/kind": "Property context kind",
    "/propertyContext/alloyId": "Build Job alloy",
    "/propertyContext/materialPropertySha256": "Material property SHA-256",
    "/researchOptions": "Research options",
    "/sender": "Sender",
    "/relay": "Relay",
    "/relay/kind": "Relay kind",
    "/relay/previewSha256": "Relay preview SHA-256",
    "/relay/conditionOrdinal": "Relay condition ordinal",
})


# --- Senders and the blind relay (Revision 3, section 14) ---------------------------------------------------------

DEFAULT_SENDER = "research-panel"
SENDERS = ("research-panel", "blind-freeze", "batch-client")
PANEL_SUPERSEDE_KEYS = ("p8-research:melt-pool", "p8-research:build-job")
BLIND_SUPERSEDE_KEY = re.compile(r"p8-research:blind:([0-9a-f]{16})\Z")
BATCH_SUPERSEDE_KEY = re.compile(r"p8-research:batch:[a-z0-9]{8,32}\Z")
SUPERSEDE_KEY_RULES = MappingProxyType({
    "research-panel": "p8-research:melt-pool or p8-research:build-job",
    "blind-freeze": "p8-research:blind:<first 16 hex of relay.previewSha256>",
    "batch-client": "p8-research:batch:<runId of 8 to 32 characters a-z 0-9>",
})

RELAY_KIND = "blind-freeze-v1"
RELAY_CONDITION_ORDINAL_MAX = 1023      # R-REL-1: integer conditionOrdinal 0 to 1023
RELAY_SUBSET_MAX_CHARS = 12000          # 14.3 item 5 and 14.4 item 4, enforced by the route per condition
# 14.4 item 3: per freeze (blind relay) and per batch-client run. The route sees one condition per request, so these
# counts are enforced where conditions are counted (the hub freeze and scripts/research-route-batch.ts); they are
# recorded here as the one Python statement of the caps.
RELAY_MAX_CONDITIONS = 48
BATCH_DEFAULT_MAX_REQUESTS = 48
BATCH_MAX_REQUESTS = 256


def supersede_key_matches(sender: str, key: str, preview_sha256: str | None) -> bool:
    """14.1: the supersedeKey prefix of each sender. A blind-freeze key must name the first 16 hex of the relay's
    previewSha256 when the request carries a relay."""
    if sender == "research-panel":
        return key in PANEL_SUPERSEDE_KEYS
    if sender == "blind-freeze":
        match = BLIND_SUPERSEDE_KEY.match(key)
        return bool(match) and (preview_sha256 is None or match.group(1) == preview_sha256[:16])
    if sender == "batch-client":
        return bool(BATCH_SUPERSEDE_KEY.match(key))
    return False


# BLIND_RELAY_V1 (14.3 item 4): the closed key set of relay.subsetJson. A None leaf is an opaque value copied from the
# request, the response or the block; the dotted keys of scored, context, support, notes and statements are paths
# into researchModels (a path the block does not carry is null). "knownContradictions[].id" keeps only the ids.
_RELAY_MODULES = ("keyholeCavity", "meltDepthLink")
_RELAY_SECTIONS = {
    "scored": ("meltDepthLink.fields.linkedMeltDepth_um",),
    "context": tuple(f"meltDepthLink.fields.{name}" for name in (
        "conditionalMeltDepth_um", "conductionDepth_um", "controllingLeg", "linkDispatch", "conductionStatus",
        "floorFieldModelId", "floorExtractorId", "cavityLedgerRatio"))
    + tuple(f"keyholeCavity.fields.{name}" for name in (
        "cavityDepth_um", "onsetPower_W", "powerOverOnset", "peclet", "onsetEvent")),
    "support": ("keyholeCavity.band.onsetSupport", "keyholeCavity.band.statusSupport",
                "meltDepthLink.band.statusSupport"),
    "notes": tuple(f"{module}.consistencyNote.{name}" for module in _RELAY_MODULES for name in (
        "status", "worstArmStatus", "sentence", "assumptions", "knownContradictions[].id", "reasons", "onsetMismatch"))
    + ("meltDepthLink.consistencyNote.fieldShapeStep", "meltDepthLink.consistencyNote.fieldShapeShare"),
    "statements": tuple(f"{module}.{name}" for module in _RELAY_MODULES for name in (
        "moduleMaturity", "moduleEvidenceCeiling", "validationStatus", "validationStatusLocator",
        "experimentalValidation", "uiSentence")),
}
RELAY_PROCESS_KEYS = ("material", "laserPower_W", "scanSpeed_mm_s", "beamDiameter_um", "preheatTemp_C",
                      "laserWavelength", "absorptionModel")
RELAY_SI_KEYS = ("power_W", "speed_m_s", "beamDiameter_m", "preheat_K")
BLIND_RELAY_V1: Mapping[str, Any] = MappingProxyType({
    "relaySchemaVersion": None,
    "relayPathsSha256": None,
    "binding": MappingProxyType({"previewSha256": None, "conditionOrdinal": None}),
    "request": MappingProxyType({
        "process": MappingProxyType({key: None for key in RELAY_PROCESS_KEYS}),
        "si": MappingProxyType({key: None for key in RELAY_SI_KEYS}),
        "propertyContext": None,
        "sender": None,
    }),
    "requestKey": None,
    "identity": MappingProxyType({key: None for key in (
        "researchImplementationSha256", "servedImplementationFingerprint", "researchSchemaVersion",
        "propertySetSha256", "propertyContextKind")}),
    "digests": MappingProxyType({"researchModelsSha256": None, "labelsSha256": None}),
    **{section: MappingProxyType({path: None for path in paths}) for section, paths in _RELAY_SECTIONS.items()},
    "labels": None,   # {"<container>.<field>": label} for the field paths of scored and context the response labels
})


def relay_paths(spec: Mapping[str, Any] = BLIND_RELAY_V1, prefix: tuple = ()) -> list:
    """The canonical path list of BLIND_RELAY_V1: every key path, as lists of keys, sorted."""
    out = []
    for key, sub in spec.items():
        path = prefix + (key,)
        out.append(list(path))
        if isinstance(sub, Mapping):
            out.extend(relay_paths(sub, path))
    return sorted(out)


def canonical_json(value: Any) -> str:
    """The route's canonical JSON (14.3 item 1): sorted keys, separators (",", ":"), ensure_ascii, allow_nan=False."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


RELAY_PATHS_SHA256 = hashlib.sha256(canonical_json(relay_paths()).encode("ascii")).hexdigest()

# Phase C (W-1): field path -> English label (7.1, 13.4). Empty in phase B; TypeScript never authors a label.
LEAF_LABELS: Mapping[str, str] = MappingProxyType({'keyholeCavity.alloy': 'Research alloy', 'keyholeCavity.power_W': 'Research power W', 'keyholeCavity.speed_m_s': 'Research speed m s', 'keyholeCavity.beamDiameter_m': 'Research beam Diameter m', 'keyholeCavity.preheat_K': 'Research preheat K', 'keyholeCavity.liquidus_K': 'Research liquidus K', 'keyholeCavity.conductivity_W_mK': 'Research conductivity W m K', 'keyholeCavity.specificHeat_J_kgK': 'Research specific Heat J kg K', 'keyholeCavity.density_kg_m3': 'Research density kg m3', 'keyholeCavity.diffusivity_m2_s': 'Research diffusivity m2 s', 'keyholeCavity.wallAbsorptanceProxy': 'Research wall Absorptance Proxy', 'keyholeCavity.vapourTemperature_K': 'Research vapour Temperature K', 'keyholeCavity.vapourLatentHeat_J_kg': 'Research vapour Latent Heat J kg', 'keyholeCavity.vapourMolarMass_kg_mol': 'Research vapour Molar Mass kg mol', 'keyholeCavity.propertyConvention': 'Research property Convention', 'keyholeCavity.propertySource': 'Research property Source', 'keyholeCavity.vapourSource': 'Research vapour Source', 'keyholeCavity.onsetEvent': 'Research onset Event', 'keyholeCavity.peclet': 'Pe = v d / (2 alpha), served conduction-kernel diffusivity', 'keyholeCavity.thermalResponse_g': 'Research thermal Response g', 'keyholeCavity.thresholdTemperature_K': 'Research threshold Temperature K', 'keyholeCavity.onsetPower_W': 'Research inception onset power P* ({onsetEvent} convention)', 'keyholeCavity.powerOverOnset': 'Research power Over Onset', 'keyholeCavity.modeledAboveOnset': 'Research modeled Above Onset', 'keyholeCavity.cavityDepth_um': 'Research cavity Depth um', 'keyholeCavity.aspectRatio_e_over_d': 'Cavity depth over beam diameter, e/d', 'keyholeCavity.cavityAbsorptance': 'Research cavity Absorptance', 'keyholeCavity.totalAbsorptance': 'Research total Absorptance', 'keyholeCavity.energyResidual_W': 'Research energy Residual W', 'keyholeCavity.rootCount': 'Research root Count', 'keyholeCavity.rootTopologyStatus': 'Research root Topology Status', 'keyholeCavity.selectedBranch': 'Research selected Branch', 'keyholeCavity.roots': 'Research roots', 'keyholeCavity.rootScanRelativeDifference': 'Research root Scan Relative Difference', 'keyholeCavity.cylinderHarmonicDifference': 'Research cylinder Harmonic Difference', 'meltDepthLink.cavityDepth_um': 'Research cavity Depth um', 'meltDepthLink.conductionDepth_um': 'Research conduction Depth um', 'meltDepthLink.conditionalMeltDepth_um': 'Research conditional Melt Depth um', 'meltDepthLink.linkedMeltDepth_um': 'Research linked Melt Depth um', 'meltDepthLink.controllingLeg': 'Research controlling Leg', 'meltDepthLink.linkDispatch': 'Research link Dispatch', 'meltDepthLink.conductionStatus': 'Research conduction Status', 'meltDepthLink.surfacePower_W': 'Research surface Power W', 'meltDepthLink.cavityPower_W': 'Research cavity Power W', 'meltDepthLink.absorbedPower_W': 'Research absorbed Power W', 'meltDepthLink.depositedThermalPower_W': 'Research deposited Thermal Power W', 'meltDepthLink.unresolvedPower_W': 'Research unresolved Power W', 'meltDepthLink.cavityPowerFraction': 'Research cavity Power Fraction', 'meltDepthLink.wallConductionPower_W': 'Research wall Conduction Power W', 'meltDepthLink.cavityLedgerRatio': 'Research cavity Ledger Ratio', 'meltDepthLink.lossMultiplier': 'Research loss Multiplier', 'meltDepthLink.photonResidual_W': 'Research photon Residual W', 'meltDepthLink.relativeConvergenceDifference': 'Research relative Convergence Difference', 'meltDepthLink.meltDepthCoarse_m': 'Research melt Depth Coarse m', 'meltDepthLink.meltDepthRefined_m': 'Research melt Depth Refined m', 'meltDepthLink.conductionRefinement_m': 'Research conduction Refinement m', 'meltDepthLink.conductionPeakX_m': 'Research conduction Peak X m', 'meltDepthLink.conductionRearBound_m': 'Research conduction Rear Bound m', 'meltDepthLink.quadratureOrder': 'Research quadrature Order', 'meltDepthLink.xSamples': 'Research x Samples', 'meltDepthLink.observable': 'Research observable', 'meltDepthLink.floorFieldModelId': 'Research floor Field Model Id', 'meltDepthLink.floorExtractorId': 'Research floor Extractor Id', 'marangoni.surfaceTensionSlope_N_mK': 'Research surface Tension Slope N m K', 'marangoni.slopeMode': 'Research slope Mode', 'marangoni.slopeBaseline': 'Research slope Baseline', 'marangoni.length_m': 'Research length m', 'marangoni.deltaTemperature_K': 'Research delta Temperature K', 'marangoni.referenceTemperature_K': 'Research reference Temperature K', 'marangoni.viscosity_Pa_s': 'Research viscosity Pa s', 'marangoni.liquidConductivity_W_mK': 'Research liquid Conductivity W m K', 'marangoni.liquidSpecificHeat_J_kgK': 'Research liquid Specific Heat J kg K', 'marangoni.liquidDensity_kg_m3': 'Research liquid Density kg m3', 'marangoni.liquidDiffusivity_m2_s': 'Research liquid Diffusivity m2 s', 'marangoni.marangoniNumber': 'Research marangoni Number', 'marangoni.marangoniMagnitude': 'Research marangoni Magnitude', 'marangoni.surfaceVelocityScale_m_s': 'Research surface Velocity Scale m s', 'marangoni.liquidPecletScale': 'Research liquid Peclet Scale', 'marangoni.liquidReynoldsScale': 'Research liquid Reynolds Scale', 'marangoni.liquidPrandtl': 'Research liquid Prandtl', 'marangoni.flowDirection': 'Research flow Direction', 'marangoni.solubleSulfur_ppm': 'Soluble S for the Fe-S analogue (ppm)', 'marangoni.solubleOxygen_ppm': 'Soluble O for the Fe-O analogue (ppm)', 'marangoni.source': 'Research source', 'surfaceBalance.beamCenterBalanceTemperature_K': 'Beam-centre balance temperature (flat HKL diagnostic, not the surface maximum)', 'surfaceBalance.lossFreeCenterTemperature_K': 'Loss-free beam-centre intermediate (not a physical temperature)', 'surfaceBalance.absorbedCenterFlux_W_m2': 'Research absorbed Center Flux W m2', 'surfaceBalance.conductiveAdmittance_W_m2K': 'Research conductive Admittance W m2K', 'surfaceBalance.monotonicDerivative_W_m2K': 'Research monotonic Derivative W m2K', 'surfaceBalance.evaporationMassFlux_kg_m2_s': 'Research evaporation Mass Flux kg m2 s', 'surfaceBalance.evaporationEnergyFlux_W_m2': 'Research evaporation Energy Flux W m2', 'surfaceBalance.beamCenterRecoilPressure_Pa': 'Beam-centre recoil pressure (flat HKL diagnostic)', 'surfaceBalance.saturationPressure_Pa': 'Research saturation Pressure Pa', 'surfaceBalance.conductionFlux_W_m2': 'Research conduction Flux W m2', 'surfaceBalance.radiationFlux_W_m2': 'Research radiation Flux W m2', 'surfaceBalance.relativeFluxResidual': 'Research relative Flux Residual', 'surfaceBalance.surfaceGainRefinementRelative': 'Research surface Gain Refinement Relative', 'surfaceBalance.iterations': 'Research iterations', 'surfaceBalance.evaluationLocation': 'Research evaluation Location', 'surfaceBalance.vapourPreset': 'Research vapour Preset', 'surfaceBalance.vapourTemperature_K': 'Research vapour Temperature K', 'surfaceBalance.vapourLatentHeat_J_kg': 'Research vapour Latent Heat J kg', 'surfaceBalance.vapourMolarMass_kg_mol': 'Research vapour Molar Mass kg mol', 'surfaceBalance.evaporationConvention': 'Research evaporation Convention', 'surfaceBalance.evaporationAccommodation': 'Research evaporation Accommodation', 'surfaceBalance.effectiveAccommodation': 'Research effective Accommodation', 'surfaceBalance.netEvaporationFactor': 'Research net Evaporation Factor', 'surfaceBalance.effectiveNetFactor': 'Research effective Net Factor', 'surfaceBalance.recoilFraction': 'Research recoil Fraction', 'surfaceBalance.emissivity': 'Research emissivity', 'surfaceBalance.source': 'Research source', 'alSi10MgIndexDisclosure.physicalAbsorptance': 'Research physical Absorptance', 'alSi10MgIndexDisclosure.indexAbsorptance': 'Research index Absorptance', 'alSi10MgIndexDisclosure.physicalToIndexRatio': 'Research physical To Index Ratio', 'alSi10MgIndexDisclosure.decision': 'Research decision', 'alSi10MgIndexDisclosure.classificationChanged': 'Research classification Changed', 'alSi10MgIndexDisclosure.basis': 'Research basis', 'unavailablePhysics.marangoniWidthDepthCorrection': 'Research marangoni Width Depth Correction', 'unavailablePhysics.physicalWallPeakTemperature_K': 'Physical cavity-wall peak temperature', 'unavailablePhysics.physicalWallRecoilPressure_Pa': 'Physical cavity-wall recoil pressure', 'unavailablePhysics.powderAbsorptance': 'Research powder Absorptance', 'unavailablePhysics.physicalKeyholeGradient_K_m': 'Research physical Keyhole Gradient K m', 'unavailablePhysics.physicalKeyholeCoolingRate_K_s': 'Research physical Keyhole Cooling Rate K s', 'alSi10MgVapourMgAware.scenarioTemperature_K': 'Research scenario Temperature K', 'alSi10MgVapourMgAware.scenarioMolarMass_kg_mol': 'Research scenario Molar Mass kg mol', 'alSi10MgVapourMgAware.scenarioLatentHeatLocalSlope_J_kg': 'Research scenario Latent Heat Local Slope J kg', 'alSi10MgVapourMgAware.scenarioLatentHeatTableWeighted_J_kg': 'Research scenario Latent Heat Table Weighted J kg', 'alSi10MgVapourMgAware.pureMgPressure_atm': 'Research pure Mg Pressure atm', 'alSi10MgVapourMgAware.composition_wt_pct': 'Research composition wt pct', 'alSi10MgVapourMgAware.pressureRoute': 'Research pressure Route', 'alSi10MgVapourMgAware.calculationStatus': 'Research calculation Status', 'alSi10MgVapourMgAware.source': 'Research source', 'alSi10MgVapourMgAware.dynamicVapourTemperature_K': 'Research dynamic Vapour Temperature K', 'keyholeCavity.roots.depth_um': 'Research root depth um', 'keyholeCavity.roots.aspectRatio_e_over_d': 'Research root aspectRatio e over d', 'keyholeCavity.roots.scalarRelaxation': 'Research root scalarRelaxation', 'keyholeCavity.roots.cavityEnergyResidual_W': 'Research root cavityEnergyResidual W', 'keyholeCavity.roots.selected': 'Research root selected', 'alSi10MgVapourMgAware.composition_wt_pct.Al': 'Feedstock Al (wt%)', 'alSi10MgVapourMgAware.composition_wt_pct.Si': 'Feedstock Si (wt%)', 'alSi10MgVapourMgAware.composition_wt_pct.Mg': 'Feedstock Mg (wt%)', 'alSi10MgVapourMgAware.composition_wt_pct.Fe': 'Feedstock Fe (wt%)'})


def json_value_text(value: Any) -> str:
    """JSON text of a received value, at most 64 characters (OptionProblem.value)."""
    try:
        text = json.dumps(value, ensure_ascii=False, allow_nan=True, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError):
        text = json.dumps(repr(value), ensure_ascii=False)
    return text if len(text) <= MAX_PROBLEM_VALUE_CHARS else text[:MAX_PROBLEM_VALUE_CHARS - 3] + "..."


def request_label(pointer: str) -> str:
    if pointer in REQUEST_FIELD_LABELS:
        return REQUEST_FIELD_LABELS[pointer]
    return pointer.rsplit("/", 1)[-1] or "The research request"


def option_problem(pointer: str, rule: str, *, value: Any = None, limit: float | int | str | None = None,
                   label: str | None = None, **fields: Any) -> dict:
    """One OptionProblem (contract 9.3) with its message filled from the rule template."""
    spec = OPTION_RULES[rule]
    value_text = json_value_text(value)
    params = {"pointer": pointer, "label": label or request_label(pointer), "value": value_text,
              "limit": "" if limit is None else limit, "type": "valid value", "min": "", "max": "", "unit": "",
              "nominal": "", "material": "", "mode": "", "presetAlloy": "", "sender": "", "expected": "",
              "context": ""}
    params.update({key: val for key, val in fields.items() if val is not None})
    message = " ".join(spec["template"].format(**params).split())
    return {"pointer": pointer, "rule": rule, "limit": limit, "value": value_text, "message": message}


def option_problem_code(problems) -> str | None:
    """The module or request code for a list of option problems: the code of the first problem's rule."""
    for problem in problems:
        return OPTION_RULES[problem["rule"]]["code"]
    return None


# W-1 wording table. Drafts are intentionally not presented as maintainer-approved.
WORDING = {'approvalStatus': 'pending maintainer approval',
 'bandCaption': 'Min / nominal / max is an envelope of named one-at-a-time scenarios. Interactions are not '
                'evaluated. It is not a confidence interval, an error bar, or a physical lower or upper '
                'bound.',
 'fieldShape': 'At or below onset the link uses the finite Gaussian field; above onset it uses a surface '
               'point plus line. The two fields differ, so the linked depth can change at P* because of '
               'field shape, not because of a cavity (P8 spec Amendment 3 C2).',
 'nearOnset': 'Near onset the linked depth is dominated by the change of field shape '
              '({fieldShapeShareOfExcess} of the excess over the Gaussian floor); controlling-leg support '
              'does not show that a cavity caused the increase.',
 'belowOnset': 'This cavity hypothesis gives zero depression at P/P*<=1. Melting is determined separately by '
               'the finite-Gaussian liquidus test; it is not guaranteed.',
 'lowAspect': 'Above onset the selected cavity has e/d = {R}, below 0.5, outside the thermal-cylinder source '
              'geometry. This is an extrapolated conditional estimate, and cavity mechanics are omitted.',
 'lowPe': 'Pe = {Pe} is below 2: the high-Pe thermal-cylinder closure used here is transferred outside its '
          'source range, and drilling, recoil-driven flow and melt transport are omitted. A converged series '
          'removes neither limitation.',
 'sourceTransfer': 'These inputs or this closure are used beyond their declared source scope ({reasons}). '
                   'Numerical admission is not a sourced physical range, and no blind validation is '
                   'available.',
 'surface': 'Temperature, evaporation and recoil here are artefacts of a falsified flat surface closure; '
            'explore them only as mathematical diagnostics.',
 'o8': 'This Mg-inclusive feedstock-composition scenario changes conditional onset, cavity and melt depth as '
       'well as surface temperature, evaporation and recoil; Mg pressure is extrapolated and none is a '
       'validated alloy prediction.',
 'onsetMismatch': 'The loss-free dwell onset and the flat surface balance can disagree. They are separate '
                  "uncoupled hypotheses; neither reconciles the other's losses.",
 'ledgers': 'The chosen spatial split is photon-conservative without reconciling the cavity-wall thermal '
            'ledger.',
 'marangoniHelp': 'Try a surface-tension slope or a single-solute chemistry analogue. Ma and velocity are '
                  'diagnostic scales; they do not correct the melt depth.',
 'beltonHelp': "This mode replaces the alloy's direct slope with a clean-Fe single-solute analogue. At zero "
               'solute it already changes the baseline; compare solute effects with zero solute in the same '
               'Fe mode, not with the alloy direct preset.',
 'surfaceHelp': 'Change evaporation, recoil or vapour inputs to explore the falsified flat surface-balance '
                'closure at the beam centre. Its temperature, evaporation and recoil are closure artefacts, '
                'shown only as mathematical diagnostics.'}
UI_SENTENCES = {'keyholeCavity': 'Conditional cavity estimate on the served conduction-kernel properties; the served '
                  'keyhole leg uses room-temperature solid properties, so the two can differ (see '
                  'Differences); no blind validation.',
 'meltDepthLink': 'Conditional melt-depth construction: the finite Gaussian conduction floor at or below '
                  'onset, a surface point plus line source above it; the two fields differ near onset; no '
                  'blind validation.',
 'marangoni': 'Surface-flow diagnostic from preset or user coefficients with an assumed temperature '
              'difference and length; the velocity is a scale, not a solved flow field; no blind validation.',
 'surfaceBalance': 'Beam-centre diagnostic of a falsified flat surface-balance closure; the numbers are '
                   'closure artefacts, not a surface temperature; no blind validation.',
 'alSi10MgIndexDisclosure': 'The regime index keeps its historical absorption convention; physical '
                            'absorption is different.',
 'alSi10MgVapourMgAware': 'Ideal-mixture vapour sensitivity; extrapolated Mg pressure, no blind validation.',
 'unavailablePhysics': 'These closures need missing inputs or new physics and are not available.'}
SERVED_DIFFERENCES = [{'id': 'D1',
  'servedPaths': ['hydrodynamicsAndRecoil.peakTemperature_C', 'hydrodynamicsAndRecoil.peakUnavailableReason'],
  'researchPaths': ['surfaceBalance.lossFreeCenterTemperature_K'],
  'variants': [{'when': ['served-null'],
                'template': 'The served peak temperature is withheld: '
                            '{served:hydrodynamicsAndRecoil.peakUnavailableReason}. The same reason applies '
                            'to the research loss-free beam-centre value '
                            '({research:surfaceBalance.lossFreeCenterTemperature_K}): it is a loss-free '
                            'intermediate, not a physical temperature, and is shown only as an input to the '
                            'falsified flat surface balance.'}],
  'fallback': 'The served peak temperature is withheld: the corresponding value. The same reason applies to '
              'the research loss-free beam-centre value (the corresponding value): it is a loss-free '
              'intermediate, not a physical temperature, and is shown only as an input to the falsified flat '
              'surface balance. The served result for these inputs is not loaded.'},
 {'id': 'D2',
  'servedPaths': ['hydrodynamicsAndRecoil.knudsenRecoilPressure_kPa',
                  'hydrodynamicsAndRecoil.recoilPressureUnavailableReason'],
  'researchPaths': ['surfaceBalance.beamCenterRecoilPressure_Pa'],
  'variants': [{'when': ['served-null'],
                'template': 'The served recoil pressure is unavailable: '
                            '{served:hydrodynamicsAndRecoil.recoilPressureUnavailableReason}. The research '
                            'beam-centre recoil pressure is an artefact of a falsified flat surface closure, '
                            'shown only as a mathematical diagnostic; it does not replace the served '
                            'refusal.'}],
  'fallback': 'The served recoil pressure is unavailable: the corresponding value. The research beam-centre '
              'recoil pressure is an artefact of a falsified flat surface closure, shown only as a '
              'mathematical diagnostic; it does not replace the served refusal. The served result for these '
              'inputs is not loaded.'},
 {'id': 'D3',
  'servedPaths': ['marangoniModel.surfaceVelocity_m_s', 'marangoniModel.dGamma_dT_N_mK'],
  'researchPaths': ['marangoni.surfaceVelocityScale_m_s', 'marangoni.surfaceTensionSlope_N_mK'],
  'variants': [{'when': ['always'],
                'template': 'The served Marangoni block uses slope {served:marangoniModel.dGamma_dT_N_mK} '
                            'and gives velocity {served:marangoniModel.surfaceVelocity_m_s}. The research '
                            'velocity scale ({research:marangoni.surfaceVelocityScale_m_s}) uses slope '
                            '{research:marangoni.surfaceTensionSlope_N_mK}. They are separate models and are '
                            'not reconciled.'}],
  'fallback': 'The served Marangoni block uses slope the corresponding value and gives velocity the '
              'corresponding value. The research velocity scale (the corresponding value) uses slope the '
              'corresponding value. They are separate models and are not reconciled. The served result for '
              'these inputs is not loaded.'},
 {'id': 'D4',
  'servedPaths': ['meltPoolGeometry.regime', 'keyholeModel.fabbroDepth_um'],
  'researchPaths': ['keyholeCavity.cavityDepth_um', 'keyholeCavity.onsetPower_W'],
  'variants': [{'when': ['host-build-job'],
                'template': 'The served regime label ({served:meltPoolGeometry.regime}) and the served '
                            'Fabbro keyhole depth ({served:keyholeModel.fabbroDepth_um}) follow the '
                            'normalised-enthalpy index and its unsourced 15 to 30 screening ramp. The '
                            'research cavity depth ({research:keyholeCavity.cavityDepth_um}) uses the '
                            'research onset P* = {research:keyholeCavity.onsetPower_W}; it changes neither '
                            'the served regime nor the verdict.'},
               {'when': ['host-melt-pool'],
                'template': 'The served regime label ({served:meltPoolGeometry.regime}) and the served '
                            'Fabbro keyhole depth ({served:keyholeModel.fabbroDepth_um}) follow the '
                            'normalised-enthalpy index and its unsourced 15 to 30 screening ramp. The '
                            'research cavity depth ({research:keyholeCavity.cavityDepth_um}) uses the '
                            'research onset P* = {research:keyholeCavity.onsetPower_W}; it changes not '
                            'change the served regime.'}],
  'fallback': 'The served regime label (the corresponding value) and the served Fabbro keyhole depth (the '
              'corresponding value) follow the normalised-enthalpy index and its unsourced 15 to 30 '
              'screening ramp. The research cavity depth (the corresponding value) uses the research onset '
              'P* = the corresponding value; it changes neither the served regime nor the verdict. The '
              'served result for these inputs is not loaded.'},
 {'id': 'D5',
  'servedPaths': ['hydrodynamicsAndRecoil.vaporTemperatureUnavailableReason'],
  'researchPaths': ['keyholeCavity.vapourSource'],
  'variants': [{'when': ['alloy-alsi10mg'],
                'template': 'The served model uses no elemental vapour proxy for AlSi10Mg '
                            '({served:hydrodynamicsAndRecoil.vaporTemperatureUnavailableReason}). This '
                            'research model uses a pure-aluminium vapour proxy by explicit choice; the '
                            'served refusal stands.'}],
  'fallback': 'The served model uses no elemental vapour proxy for AlSi10Mg (the corresponding value). This '
              'research model uses a pure-aluminium vapour proxy by explicit choice; the served refusal '
              'stands. The served result for these inputs is not loaded.'},
 {'id': 'D6',
  'servedPaths': ['keyholeModel.peclet', 'processParameters.effectiveDiffusivity_m2_s'],
  'researchPaths': ['keyholeCavity.peclet'],
  'variants': [{'when': ['always'],
                'template': 'Both use Pe = v d / (2 alpha). The research Pe '
                            '({research:keyholeCavity.peclet}) uses the served conduction-kernel diffusivity '
                            '({served:processParameters.effectiveDiffusivity_m2_s}); the served keyhole Pe '
                            '({served:keyholeModel.peclet}) uses the room-temperature solid diffusivity of '
                            'the served Fabbro leg.'}],
  'fallback': 'Both use Pe = v d / (2 alpha). The research Pe (the corresponding value) uses the served '
              'conduction-kernel diffusivity (the corresponding value); the served keyhole Pe (the '
              'corresponding value) uses the room-temperature solid diffusivity of the served Fabbro leg. '
              'The served result for these inputs is not loaded.'},
 {'id': 'D7',
  'servedPaths': ['meltPoolGeometry.aspectRatio_L_over_W', 'keyholeModel.aspectRatio_e_over_d'],
  'researchPaths': ['keyholeCavity.aspectRatio_e_over_d'],
  'variants': [{'when': ['always'],
                'template': 'Research e/d is cavity depth over beam diameter. The served aspect ratio tile '
                            'is melt-pool length over width, a different quantity. The served Fabbro e/d is '
                            '{served:keyholeModel.aspectRatio_e_over_d}.'}],
  'fallback': 'Research e/d is cavity depth over beam diameter. The served aspect ratio tile is melt-pool '
              'length over width, a different quantity. The served Fabbro e/d is the corresponding value. '
              'The served result for these inputs is not loaded.'},
 {'id': 'D8',
  'servedPaths': ['meltPoolGeometry.depth_um'],
  'researchPaths': ['meltDepthLink.linkedMeltDepth_um'],
  'variants': [{'when': ['served-kernel-eagar-tsai-and-below-onset'],
                'template': 'Below the research onset both depths come from the same Eagar-Tsai temperature '
                            'field. The served depth ({served:meltPoolGeometry.depth_um}) uses the served '
                            'four-probe extent; the research floor '
                            '({research:meltDepthLink.linkedMeltDepth_um}) uses a separate envelope '
                            'extractor, so the two can differ.'},
               {'when': ['always'],
                'template': 'The served melt-pool depth ({served:meltPoolGeometry.depth_um}, {servedKernel} '
                            'kernel) and the research linked melt depth '
                            '({research:meltDepthLink.linkedMeltDepth_um}) are different constructions; the '
                            'research value never replaces the served depth.'}],
  'fallback': 'Below the research onset both depths come from the same Eagar-Tsai temperature field. The '
              'served depth (the corresponding value) uses the served four-probe extent; the research floor '
              '(the corresponding value) uses a separate envelope extractor, so the two can differ. The '
              'served result for these inputs is not loaded.'},
 {'id': 'D9',
  'servedPaths': ['meltPoolGeometry.keyholeVaporCavityDepth_um'],
  'researchPaths': ['keyholeCavity.cavityDepth_um'],
  'variants': [{'when': ['always'],
                'template': 'The served keyhole vapour cavity depth is the increment of the Fabbro leg over '
                            'the conduction depth; the research cavity depth is measured from the original '
                            'surface. The two numbers are not comparable.'}],
  'fallback': 'The served keyhole vapour cavity depth is the increment of the Fabbro leg over the conduction '
              'depth; the research cavity depth is measured from the original surface. The two numbers are '
              'not comparable. The served result for these inputs is not loaded.'},
 {'id': 'D10',
  'servedPaths': ['marangoniModel.sulfur_ppm'],
  'researchPaths': ['marangoni.solubleSulfur_ppm'],
  'variants': [{'when': ['always'],
                'template': 'The served sulfur slider ({served:marangoniModel.sulfur_ppm}, Heiple-Roper '
                            'screening) does not feed this research model. The research Fe-S analogue reads '
                            'only the soluble sulfur entered here.'}],
  'fallback': 'The served sulfur slider (the corresponding value, Heiple-Roper screening) does not feed this '
              'research model. The research Fe-S analogue reads only the soluble sulfur entered here. The '
              'served result for these inputs is not loaded.'},
 {'id': 'D11',
  'servedPaths': ['processParameters.indexAbsorptivity', 'processParameters.effectiveAbsorptivity'],
  'researchPaths': ['alSi10MgIndexDisclosure.physicalToIndexRatio'],
  'variants': [{'when': ['alloy-alsi10mg'],
                'template': 'The served regime index uses absorptivity '
                            '{served:processParameters.indexAbsorptivity}; the served field uses '
                            '{served:processParameters.effectiveAbsorptivity}. The disclosure below explains '
                            'the difference; no classification changes.'}],
  'fallback': 'The served regime index uses absorptivity the corresponding value; the served field uses the '
              'corresponding value. The disclosure below explains the difference; no classification changes. '
              'The served result for these inputs is not loaded.'}]

# Per-code noun phrases and class/cause refusal wording (contract 9.2, W-1).
NA_TEMPLATES = {
    'C1': 'Research request refused: {phrase}. The served result is not affected.',
    'C2': 'The research evaluator failed for this model. The served result is not affected; details are in the local server log.',
    'C3': 'Research inputs for this model were refused: {phrase}. Other research models are unaffected.',
    'C4': 'Not computed: {phrase}. No input in this panel can admit it, and no value is borrowed from another alloy.',
    'C5': 'Not computed: {phrase} is outside its declared software limit or source range. No clipped value is shown.',
    'C6': 'Not computed: {phrase} is required and no sourced default exists. Enter a value to evaluate it.',
    'C7': 'Not available: {phrase}.',
    'C8': 'Not computed: the {phrase} did not meet its numerical acceptance rule. No clipped or fallback value is shown.',
    'C9': 'Not available: no closure or required source data for {phrase} is adopted.',
    'C10': 'No completed scenario envelope is available: {phrase}.',
}
CODE_PHRASES = {code: code.lower().replace('_', ' ') for code in REASON_CODES}
CODE_PHRASES.update(PECLET_OUTSIDE_NUMERICAL_SCOPE='Pe of the cavity solver',
                    TIP_SHELL_UNRESOLVED='melt envelope near the cavity tip')
# Enrich the existing closed registry without changing class, scope or precedence.
_REASON_CODES = {code: MappingProxyType({**entry, 'phrase': CODE_PHRASES[code],
                  'text': NA_TEMPLATES[entry['class']].format(phrase=CODE_PHRASES[code])})
                 for code, entry in REASON_CODES.items()}
REASON_CODES = MappingProxyType(_REASON_CODES)


def unit_for(name):
    for suffix, unit in (('_W_m2K','W/m2/K'),('_W_m2','W/m2'),('_kg_m2_s','kg/m2/s'),
                         ('_W_mK','W/m/K'),('_J_kgK','J/kg/K'),('_J_kg','J/kg'),('_kg_mol','kg/mol'),
                         ('_kg_m3','kg/m3'),('_m2_s','m2/s'),('_N_mK','N/m/K'),('_Pa_s','Pa s'),
                         ('_K_m','K/m'),('_K_s','K/s'),('_m_s','m/s'),('_um','um'),('_ppm','ppm'),
                         ('_Pa','Pa'),('_atm','atm'),('_K','K'),('_W','W'),('_m','m')):
        if name.endswith(suffix): return unit
    return 'wt%' if name == 'composition_wt_pct' else '1'

WORDING["leafSentence"] = "Research only."

# W-1 cause-specific refusal wording; all remains pending maintainer approval.
def refusal_text(code, reason, alloy='this alloy'):
    phrase=CODE_PHRASES[code];cls=code_class(code);cause=reason['cause']
    if code=='VAPOUR_PRESSURE_OUTSIDE_SOURCE_RANGE':
        return ('Not available: the dynamic wall-vapour inference lies outside its source range for every admissible input '
                '(the Mg vapour pressure exceeds the 600 to 1730 K fit and the 10 atm synthesis ceiling), so it is always withheld. No input in this panel changes this.')
    if cls=='C4' or cause=='alloy-not-admitted':
        return f'Not computed: {phrase} for {alloy}. No input in this panel can admit it, and no value is borrowed from another alloy.'
    if cls=='C5':
        kind='source range' if code in ('PREHEAT_OUTSIDE_PROPERTY_SCOPE','VAPOUR_PRESSURE_OUTSIDE_SOURCE_RANGE') else 'software limit'
        if reason['allowedValues']:
            statement=f"{reason['quantity']} {reason['value']} is not supported by this research model (supported: {', '.join(reason['allowedValues'])})."
        elif reason['limitMin'] is not None and reason['limitMax'] is not None:
            statement=f"{reason['quantity']} = {reason['value']} is outside the {kind} {reason['limitMin']} to {reason['limitMax']}."
        elif reason['limitMin'] is not None:
            statement=f"{reason['quantity']} = {reason['value']} is below the {kind} minimum {reason['limitMin']}."
        else:
            statement=f"{reason['quantity']} = {reason['value']} is above the {kind} maximum {reason['limitMax']}."
        change='Change '+', '.join(reason['changeInputs'])+' to evaluate it.' if reason['changeInputs'] else 'No input in this panel changes this limit.'
        return f'Not computed: {statement} This is a {kind}, not a physical cutoff. {change}'
    if cls=='C6':
        if cause=='domain':return f"Not computed: the onset reference is undefined for these inputs ({reason['quantity']} = {reason['value']})."
        if cause=='default-cleared':return f'Not computed: {phrase} is empty. Reset the declared preset or enter a value.'
        return f'Not computed: {phrase} is required and no sourced default exists for {alloy}. Enter a value to evaluate it.'
    if cause=='comparison':return f"Comparison not available: {phrase}; this arm's event or tuple differs from every cavity scenario."
    if cause=='closure-falsified':
        return f'Not available: the physical {phrase} needs a coupled wall, energy and flow closure. The flat surface closure that exists is falsified and appears only as a diagnostic in Surface balance.'
    if cause=='data-missing':return f"Not available: {phrase} needs inputs that are not in the library: {', '.join(reason['missingInputs'])}."
    if code=='BAND_MANIFEST_NOT_DECLARED':return 'No scenario manifest is declared for this model and alloy; only the nominal value is shown.'
    return REASON_CODES[code]['text']


# Enum display wording never presents scalar relaxation as physical stability.
VALUE_LABELS = {'scalarRelaxation': {'stable': 'relaxes back (scalar balance)',
                                   'unstable': 'moves away (scalar balance)',
                                   'neutral': 'neutral (scalar balance)'},
                'selectedBranch': {'lowest-strictly-stable': 'Lowest root that relaxes back (branch convention)'}}
LEAF_LABELS = MappingProxyType({**LEAF_LABELS,
    **{'keyholeCavity.roots.scalarRelaxation.'+key: text for key,text in VALUE_LABELS['scalarRelaxation'].items()},
    'keyholeCavity.selectedBranch.lowest-strictly-stable': VALUE_LABELS['selectedBranch']['lowest-strictly-stable']})
