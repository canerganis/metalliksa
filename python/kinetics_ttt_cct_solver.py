#!/usr/bin/env python3
"""
MetalliX Python steel TTT/CCT kinetics solver (Li et al. 1998 model).

TTT: the Li, Niebuhr, Meekisho & Atteridge (1998) modification of the Kirkaldy-Venugopalan
isothermal model for ferrite, pearlite and bainite in low-alloy steels:

    tau_i(X, T) = F_i(C, Mn, Si, Ni, Cr, Mo) S(X) / (2^(n1_i G) (T_i - T)^n2_i exp(-Q / (R T)))

CCT: the additivity rule (Scheil 1935) applied to the 1 % start time of each phase along a linear
cooling path. Critical temperatures: Ae3/Ae1 by Grange (1961), Bs by Li et al., Ms by the Andrews
linear equation as modified by Kung & Rayment (1982). The model is reported only for steels whose
composition lies inside the range stated by the model's author; everything else is unavailable
with an explicit status and reason. Phase fractions and hardness are NOT computed (see
FRACTIONS_REASON).

Precipitate coarsening and strengthening (SOL-K, SPEC_solidification section 6.3): the generic LSW radius and the
280 MPa / 9 nm strengthening curve rest on constants without a source and on no alloy-specific model, so the mean
radius, the strengthening and its mechanism are unavailable (null) for every alloy and every aging input, each row
with a status and machine-readable reason codes. The aging inputs are still validated before any arithmetic.
"""

import sys
import json
import math
import time

import alloy_data_kinetics_uq_fatigue as _kinetics_data
import alloy_registry
import hardness_conversion_e140
import input_validation
import physical_constants

# Alloy kinetics data (Phase 6a structural migration, design step (a)): the numeric
# columns of the former local ALLOY_KINETICS_DB come from alloy_registry (domain
# "kinetics"), the labels from alloy_data_kinetics_uq_fatigue. Values and the
# "alloyMetadata" key order are unchanged. An unknown alloy name now raises
# input_validation.ValidationError (UNKNOWN_ALLOY) instead of silently using AISI 4140.
# Phase 6a value step (b): exact SI 2019 R = N_A*k (was the 4-significant-figure 8.314).
R_GAS = physical_constants.GAS_CONSTANT_R.value  # J/(mol*K), exact
ZERO_C_K = physical_constants.ZERO_CELSIUS_K.value

ENGINE = "MetalliX-Python-Li1998-Additivity-Kinetics-v4.1"
LI_MODEL_VERSION = "li1998-additivity-v1"

# predictedHardness_HV: ASTM E140 Table 1 HRC -> HV (hardness_conversion_e140), which applies
# to non-austenitic steels only. The Li model does not compute phase fractions or hardness, so every
# CCT row has HRC None; HV is None with STATUS_HV_NO_HRC (steels) or STATUS_UNAVAILABLE_ALLOY_CLASS.
E140_NON_AUSTENITIC_STEEL_IDS = frozenset({"aisi4140", "aisi4340", "aisid2"})

# ---------------------------------------------------------------------------------------------------------------
# Sources (the equations below were checked against these; see the lane handoff for URLs and sha256):
# [Li98]  M. V. Li, D. V. Niebuhr, L. L. Meekisho, D. G. Atteridge, Metall. Mater. Trans. B 29 (1998) 661-672.
# [Li96]  M. Li, PhD thesis, Oregon Graduate Institute (1996), doi:10.6083/M4S180SN: Eqs. 3.66-3.77 (pp. 83-86),
#         validity statement p. 86, worked AISI 4140 example Tables 5.7, 5.9, 5.11-5.14 (pp. 157-160).
# [Col23] J. Collins et al., Metals 13 (2023) 1168 (CC BY 4.0): Eqs. 1-14 (the same F_i, n1, n2, Q = 115,060
#         J/mol, Bs) and Grange's Ae3/Ae1 (Eqs. 8, 11); Li-model CCT panels Figs. 3a, 6a, 9a.
# [Gra61] R. A. Grange, Metal Progress 79 (1961) 73 (Ae3/Ae1, degF), as printed in [Col23] Eqs. 8 and 11.
# [KR82]  C. Y. Kung, J. J. Rayment, Metall. Trans. A 13 (1982) 328 (Andrews linear Ms with Co and Si terms),
#         as printed in [Li96] Eq. 3.77.
SOURCE_LABEL = (
    "Li, Niebuhr, Meekisho & Atteridge, Metall. Mater. Trans. B 29 (1998) 661-672: equations as printed in "
    "M. Li, PhD thesis, Oregon Graduate Institute (1996), Eqs. 3.67 and 3.70-3.77, and in Collins et al., "
    "Metals 13 (2023) 1168, Eqs. 1-14; Ae3/Ae1: Grange (1961) as printed in Collins et al. Eqs. 8 and 11; "
    "Ms: Andrews linear equation modified by Kung & Rayment (1982), Li (1996) Eq. 3.77; CCT: additivity rule "
    "(Scheil 1935)."
)
VALIDITY_SOURCE = (
    "M. Li (1996) thesis p. 86: the author 'has not thoroughly tested the application range' and believes the "
    "model valid 'at least within the same range of Creusot-Loire model': 0.1<C<0.5, Si<1.0, Mn<2, Ni<4, Cr<3, "
    "Mo<1, V<0.2, Cu<0.5, Mo+Ni+Cr+Mo<5 (as printed), 0.01<Al<0.05 (wt%)."
)
# Q = 27,500 cal/mol [Li96 Eqs. 3.73] = 115,060 J/mol [Col23 Eqs. 6, 9, 12].
LI_Q_J_MOL = 115060.0
# (grain-size exponent n1, undercooling exponent n2) per phase [Li96 Eqs. 3.69-3.73; Col23 Eqs. 6, 9, 12].
LI_EXPONENTS = {"Ferrite": (0.41, 3), "Pearlite": (0.32, 3), "Bainite": (0.29, 2)}
LI_PHASES = ("Ferrite", "Pearlite", "Bainite")
# Reaction fractions reported on the TTT curves (start / half / finish of the isothermal reaction).
TTT_FRACTIONS = (0.01, 0.5, 0.99)
# Composition range stated in [Li96] p. 86 (strict inequalities as printed; wt%).
LI_RANGE_UPPER = {"Si": 1.0, "Mn": 2.0, "Ni": 4.0, "Cr": 3.0, "Mo": 1.0, "V": 0.2, "Cu": 0.5}
LI_RANGE_C = (0.1, 0.5)
LI_RANGE_AL = (0.01, 0.05)
LI_RANGE_SUM_MAX = 5.0
# Elements the stated range covers (Fe is the balance). Any other element makes the composition "not covered".
LI_RANGE_ELEMENTS = frozenset({"Fe", "C", "Si", "Mn", "Ni", "Cr", "Mo", "V", "Cu", "Al"})
# Display/numerics choices of this implementation (not source constants):
TTT_POINTS_PER_PHASE = 40          # temperatures per C-curve, evenly spaced from Ms to (T_i - 1 C)
TTT_DISPLAY_MAX_S = 1.0e6          # TTT points with a start time at or above 1e6 s are not listed (as before)
CCT_STEP_K = 0.05                  # temperature step of the additivity integral (midpoint rule)
# Input bounds of this implementation for the modelled steels (sanity limits of the inputs, NOT a source validity
# range): prior-austenite grain diameter 1-1000 um (ASTM G about 18.3 to -1.6) and austenitizing temperature
# 0-1600 C. Outside them the request is rejected (OUT_OF_RANGE). The published comparisons used here span
# G 5.6-11.0 (Collins et al. 2023 Figs. 3, 6, 9) and G 8 (Li 1996 AISI 4140 example); validityDomain.grainSize
# says whether a request is inside that compared span.
GRAIN_SIZE_BOUNDS_UM = (1.0, 1000.0)
AUST_TEMP_BOUNDS_C = (0.0, 1600.0)
COMPARED_G_RANGE = (5.6, 11.0)
KM_ALPHA_PER_K = 0.011             # Koistinen-Marburger rate constant as used in [Li96] Eq. 3.76
ROOM_TEMPERATURE_C = 25.0

STEEL_ONLY_REASON = "kinetics model is steel-only"
STATUS_UNAVAILABLE_STEEL_ONLY = "unavailable-kinetics-model-steel-only"
STATUS_UNAVAILABLE_OUTSIDE_RANGE = "unavailable-composition-outside-li-model-range"
STATUS_UNAVAILABLE_PLACEHOLDER = "unavailable-registry-placeholder"
STATUS_REGISTRY_VALUE = "registry-screening-value"
STATUS_LSW_NOT_MODELLED = "unavailable-not-modelled"
STATUS_START_LI = "li1998-additivity-first-diffusional-start"
STATUS_START_ATHERMAL = "athermal-martensite-no-diffusional-start-above-ms"
STATUS_START_NOT_AUSTENITIC = "unavailable-austenitizing-at-or-below-ae3"
STATUS_FRACTIONS_NOT_COMPUTED = "unavailable-fractions-not-computed"
STATUS_HV_NO_HRC = "unavailable-no-predicted-hrc"
STATUS_STATIC_TEXT = "static-text-not-a-calphad-calculation"
STATUS_LI_SCREENING = "li1998-additivity-screening"
STATUS_GRANGE = "computed-grange-1961-screening"
STATUS_BS_LI = "computed-li-1998-screening"
STATUS_MS_KR = "computed-andrews-kung-rayment-1982-screening"
STATUS_MF_NOT_MODELLED = "unavailable-not-modelled"
STATUS_TTT_NO_FLOOR = "no-floor-li-1998-law"
# Reason codes (SPEC_solidification section 2, integration contract 4.5 and 4.6): codes only; the sentence for each
# code belongs to the maintainer's wording round and the quantity-envelope registry, not to this solver.
REASON_MISSING_SOURCE_BOUND_MODEL = "missing-source-bound-model"
REASON_MISSING_SOURCE_CONSTANT = "missing-source-constant"
REASON_OUTSIDE_SOURCE_MODEL_DOMAIN = "outside-source-model-domain"
REASON_NONPHYSICAL_INPUT = "nonphysical-input"
# Precipitate coarsening and strengthening are unavailable for every alloy: no source-bound model (the generic LSW
# law alone cannot represent nucleation, growth, dissolution or a changing population) and no sourced constants
# (the shared gamma, equilibrium concentration, molar volume and D0, and the 280 MPa / 9 nm strengthening curve).
LSW_REASON_CODES = (REASON_MISSING_SOURCE_BOUND_MODEL, REASON_MISSING_SOURCE_CONSTANT)
# Aging inputs (SPEC section 6.3): a temperature must be above absolute zero (-273.15 C itself is rejected), a time
# must be finite and not negative. The bound is the smallest float above -273.15 C, so ``T_K > 0`` holds exactly.
AGING_TEMP_LOWER_BOUND_C = math.nextafter(-ZERO_C_K, math.inf)
LSW_AGING_TIMES_H = (0.1, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 24.0, 48.0, 100.0)
VALIDATION_STATUS = "unvalidated"
EVIDENCE_LEVEL = "screening"
SCOPE = "low-alloy steels inside the composition range stated for the Li (1998) model"

NON_STEEL_MODEL_NOTE = (
    "The Li (1998) TTT/CCT model covers low-alloy steels only; no sourced transformation-kinetics model of this "
    "alloy class is implemented, so no TTT/CCT curves, start temperatures, phase fractions or hardness are reported."
)
OUTSIDE_RANGE_NOTE = (
    "The composition is outside the range stated for the Li (1998) model (M. Li 1996 thesis p. 86), so no TTT/CCT "
    "curves, start temperatures, phase fractions or hardness are reported."
)
LI_NOTE = (
    "Li et al. (1998) isothermal start/finish law with Grange Ae3/Ae1, Li Bs and Kung-Rayment Ms; CCT starts from "
    "the additivity rule applied to each phase's 1 % start curve independently (no phase interaction, no carbon "
    "partitioning). Unvalidated screening model: phase fractions and hardness are not computed."
)
# X in tau(X, T) per phase ([Li96] p. 84): ferrite and bainite use the volume fraction of the austenite directly;
# ferrite completes at its equilibrium amount (thermodynamic model, not implemented), so only its 1 % start is a
# reportable time. Pearlite uses a phantom (normalized) fraction that goes to completion.
REACTION_FRACTION_BASIS = {
    "Ferrite": ("volume fraction of the original austenite; the reaction ends at the equilibrium ferrite amount "
                "(thermodynamic model, not implemented), so t50_s and tFinish_s are not reported (null)"),
    "Pearlite": "phantom (normalized) reaction fraction that goes to completion (Li 1996 p. 84)",
    "Bainite": ("volume fraction of the austenite (Li 1996 p. 84); the model lets bainite consume all remaining "
                "austenite (Li 1996 p. 86), incomplete-reaction effects are not modelled"),
}
FRACTIONS_REASON = (
    "phase fractions and hardness are not computed: the Li (1998) model needs the equilibrium ferrite and pearlite "
    "amounts from a thermodynamic Fe-C-M model that is not implemented"
)
NOT_AUSTENITIC_REASON_FMT = (
    "austenitizing temperature {aust:g} C is at or below the Grange Ae3 of {ae3:.1f} C: the Li model assumes a fully "
    "austenitic start"
)
TTT_NO_FLOOR_NOTE = (
    "The Li (1998) start-time law diverges at its start temperature (Ae3, Ae1, Bs); no time floor is applied. "
    "Points with a start time of 1e6 s or more are not listed."
)
TTT_UNAVAILABLE_NOTE = "No TTT points: the kinetics model is unavailable for this alloy."
# Fixed steel text (not a CALPHAD result).
STEEL_EQUILIBRIUM_PHASES = "Ferrite + Cementite / Equilibrium intermetallics"


def checked_aging_inputs(aging_temp_c, aging_time_h):
    """Validate the aging inputs before any arithmetic on them; returns (temperature C, time h) as floats.

    A non-number, NaN, an infinity, a temperature at or below absolute zero (-273.15 C included) or a negative
    time raises ValidationError, whose ``detail["reasonCode"]`` is ``nonphysical-input``. Nothing is clamped.
    """
    try:
        try:
            temp = input_validation.require_finite("agingTemp_C", aging_temp_c)
        except OverflowError as exc:
            raise input_validation.ValidationError(input_validation.NON_FINITE, "agingTemp_C", "must be finite") from exc
        if temp <= -ZERO_C_K:
            raise input_validation.ValidationError(input_validation.OUT_OF_RANGE, "agingTemp_C",
                                                  "must be > -273.15 degC", {"value": temp})
        try:
            time_h = input_validation.require_positive("agingTime_h", aging_time_h, allow_zero=True)
        except OverflowError as exc:
            raise input_validation.ValidationError(input_validation.NON_FINITE, "agingTime_h", "must be finite") from exc
    except input_validation.ValidationError as err:
        err.detail["reasonCode"] = REASON_NONPHYSICAL_INPUT
        raise
    return temp, time_h


def is_steel_alloy(alloy):
    """Whether the kinetics descriptor 'type' of this alloy is a steel (the only modelled class)."""
    return "Steel" in alloy["type"]


def placeholder_keys(registry_id):
    """Registry keys of this alloy that alloy_registry.KINETICS_PLACEHOLDERS flags as non-physical."""
    return sorted(key for alloy_id, key in alloy_registry.KINETICS_PLACEHOLDERS if alloy_id == registry_id)


def resolve_kinetics_alloy(alloy_name):
    """Return (registry id, legacy table name, alloy metadata dict) for ``alloy_name``.

    The metadata dict has the legacy ALLOY_KINETICS_DB layout and key order.
    Raises ValidationError(UNKNOWN_ALLOY) for names without kinetics data.
    """
    record = input_validation.require_known_alloy(alloy_name, alloy_registry.DOMAIN_KINETICS, field="alloy")
    labels = _kinetics_data.KINETICS_DESCRIPTORS[record.id]
    metadata = {}
    for key in _kinetics_data.KINETICS_METADATA_KEYS:
        if key == "phases":
            metadata[key] = list(labels[key])
        elif key in _kinetics_data.KINETICS_DESCRIPTOR_KEYS:
            metadata[key] = labels[key]
        elif key == "composition_wt":
            metadata[key] = dict(record.value(key, alloy_registry.DOMAIN_KINETICS))
        else:
            metadata[key] = record.value(key, alloy_registry.DOMAIN_KINETICS)
    return record.id, _kinetics_data.KINETICS_LEGACY_NAMES[record.id], metadata


def provenance(registry_id):
    out = {
        "registryVersion": alloy_registry.REGISTRY_VERSION,
        "constantsVersion": physical_constants.CONSTANTS_VERSION,
        "registryAlloyId": registry_id,
        "gasConstantR_J_molK": R_GAS,
        "constantsNote": "Exact SI 2019 R = N_A*k (Phase 6a value step); it replaced the "
                         "4-significant-figure R = 8.314.",
    }
    out.update(_kinetics_data.provenance())
    out["hardnessConversion"] = dict(
        hardness_conversion_e140.provenance(),
        appliesToRegistryIds=sorted(E140_NON_AUSTENITIC_STEEL_IDS),
        appliedToThisAlloy=registry_id in E140_NON_AUSTENITIC_STEEL_IDS,
    )
    out["kineticsModelVersion"] = LI_MODEL_VERSION
    return out


# ---------------------------------------------------------------------------------------------------------------
# Li (1998) model
def _w(comp, element):
    return float(comp.get(element, 0.0) or 0.0)


def li_composition_check(comp):
    """(inside: bool, violations: list[str], unchecked: list[str]) against the [Li96] p. 86 range (wt%)."""
    violations, unchecked = [], []
    for element in sorted(comp):
        if float(comp[element] or 0.0) < 0.0:
            violations.append(f"{element} {comp[element]:g} wt% is negative")
        if element not in LI_RANGE_ELEMENTS and float(comp[element] or 0.0) > 0.0:
            violations.append(f"{element} {comp[element]:g} wt% is not covered by the stated range")
    c = _w(comp, "C")
    if not LI_RANGE_C[0] < c < LI_RANGE_C[1]:
        violations.append(f"C {c:g} wt% (range {LI_RANGE_C[0]:g} < C < {LI_RANGE_C[1]:g})")
    for element, upper in LI_RANGE_UPPER.items():
        value = _w(comp, element)
        if not value < upper:
            violations.append(f"{element} {value:g} wt% (range {element} < {upper:g})")
    for label, total in (("Mn+Ni+Cr+Mo", _w(comp, "Mn") + _w(comp, "Ni") + _w(comp, "Cr") + _w(comp, "Mo")),
                         ("Mo+Ni+Cr+Mo (as printed)", 2.0 * _w(comp, "Mo") + _w(comp, "Ni") + _w(comp, "Cr"))):
        if not total < LI_RANGE_SUM_MAX:
            violations.append(f"{label} {total:g} wt% (range < {LI_RANGE_SUM_MAX:g})")
    if "Al" in comp:
        al = _w(comp, "Al")
        if not LI_RANGE_AL[0] < al < LI_RANGE_AL[1]:
            violations.append(f"Al {al:g} wt% (range {LI_RANGE_AL[0]:g} < Al < {LI_RANGE_AL[1]:g})")
    else:
        unchecked.append("Al not specified in the registry composition: the 0.01 < Al < 0.05 wt% bound is not checked")
    return not violations, violations, unchecked


def li_critical_temperatures(comp):
    """Ae3, Ae1 (Grange, degC), Bs (Li), Ms (Andrews/Kung-Rayment) for a composition in wt%."""
    c, mn, si, ni, cr, mo, co = (_w(comp, e) for e in ("C", "Mn", "Si", "Ni", "Cr", "Mo", "Co"))
    ae3 = (1570.0 - 323.0 * c - 25.0 * mn + 80.0 * si - 32.0 * ni - 3.0 * cr - 32.0) * 5.0 / 9.0
    ae1 = (1333.0 - 25.0 * mn + 40.0 * si - 26.0 * ni + 42.0 * cr - 32.0) * 5.0 / 9.0
    bs = 637.0 - 58.0 * c - 35.0 * mn - 15.0 * ni - 34.0 * cr - 41.0 * mo
    ms = 539.0 - 423.0 * c - 30.4 * mn - 12.1 * cr - 17.7 * ni - 7.5 * mo + 10.0 * co - 7.5 * si
    return {"Ae3": ae3, "Ae1": ae1, "Bs": bs, "Ms": ms}


def li_composition_factors(comp):
    """F_ferrite (FC), F_pearlite (PC), F_bainite (BC) [Li96 Eqs. 3.70, 3.72, 3.74; Col23 Eqs. 7, 10, 13]."""
    c, mn, si, ni, cr, mo = (_w(comp, e) for e in ("C", "Mn", "Si", "Ni", "Cr", "Mo"))
    return {
        "Ferrite": math.exp(1.00 + 6.31 * c + 1.78 * mn + 0.31 * si + 1.12 * ni + 2.70 * cr + 4.06 * mo),
        "Pearlite": math.exp(-4.25 + 4.12 * c + 4.36 * mn + 0.44 * si + 1.71 * ni + 3.33 * cr + 5.19 * math.sqrt(mo)),
        "Bainite": math.exp(-10.23 + 10.18 * c + 0.85 * mn + 0.55 * ni + 0.90 * cr + 0.36 * mo),
    }


def astm_grain_size_number(mean_diameter_um):
    """ASTM E112 grain size number G from the mean planar grain diameter d [Col23 Eqs. 3-4]:
    G = -3.2877 - 6.6439 log10(l / mm), l = sqrt(pi/4) d (mean linear intercept)."""
    intercept_mm = math.sqrt(math.pi / 4.0) * mean_diameter_um * 1e-3
    return -3.2877 - 6.6439 * math.log10(intercept_mm)


def _sigmoid_integrand(x):
    return 1.0 / (x ** (0.4 * (1.0 - x)) * (1.0 - x) ** (0.4 * x))


def _simpson(f, a, b, n):
    n += n % 2
    h = (b - a) / n
    total = f(a) + f(b)
    for i in range(1, n):
        total += (4.0 if i % 2 else 2.0) * f(a + i * h)
    return total * h / 3.0


def li_reaction_integral(fraction):
    """S(X) = int_0^X dx / (x^(0.4(1-x)) (1-x)^(0.4x)) [Li96 Eq. 3.67; Col23 Eq. 2], 0 < X <= 1.

    The x^-0.4 end point singularity is removed with x = u^(5/3) on [0, min(X, 1/2)], the (1-x)^-0.4 one with
    1 - x = v^(5/3) on [1/2, X]; composite Simpson on the smooth transformed integrands.
    """
    if not 0.0 < fraction <= 1.0:
        raise ValueError("reaction fraction must be in (0, 1]")
    k = 5.0 / 3.0

    def low(u):
        if u == 0.0:
            return k  # limit of f(u^k) * k u^(k-1) at u = 0
        x = u ** k
        return _sigmoid_integrand(x) * k * u ** (k - 1.0)

    def high(v):
        if v == 0.0:
            return k
        x = 1.0 - v ** k
        return _sigmoid_integrand(x) * k * v ** (k - 1.0)

    split = min(fraction, 0.5)
    total = _simpson(low, 0.0, split ** (1.0 / k), 4000)
    if fraction > 0.5:
        total += _simpson(high, (1.0 - fraction) ** (1.0 / k), 0.5 ** (1.0 / k), 4000)
    return total


_S_CACHE = {}


def li_s(fraction):
    if fraction not in _S_CACHE:
        _S_CACHE[fraction] = li_reaction_integral(fraction)
    return _S_CACHE[fraction]


class LiModel:
    """Li (1998) isothermal law for one steel composition and ASTM grain size G."""

    def __init__(self, comp, grain_g):
        self.comp = dict(comp)
        self.grain_g = grain_g
        self.temps = li_critical_temperatures(comp)
        self.factors = li_composition_factors(comp)
        self.start_temp = {"Ferrite": self.temps["Ae3"], "Pearlite": self.temps["Ae1"], "Bainite": self.temps["Bs"]}

    def rate_term(self, phase, temp_c):
        """1 / tau_i(X, T) * S(X): 2^(n1 G) (T_i - T)^n2 exp(-Q/RT) / F_i; 0 at or above T_i."""
        n1, n2 = LI_EXPONENTS[phase]
        under = self.start_temp[phase] - temp_c
        if under <= 0.0:
            return 0.0
        return (2.0 ** (n1 * self.grain_g) * under ** n2 * math.exp(-LI_Q_J_MOL / (R_GAS * (temp_c + ZERO_C_K)))
                / self.factors[phase])

    def tau(self, phase, fraction, temp_c):
        """Isothermal time (s) to reach reaction fraction X at temp_c; None at or above the start temperature."""
        rate = self.rate_term(phase, temp_c)
        return None if rate <= 0.0 else li_s(fraction) / rate

    def ttt_curves(self):
        points = []
        ms = self.temps["Ms"]
        for phase in LI_PHASES:
            top = self.start_temp[phase] - 1.0
            if top <= ms:
                continue
            for i in range(TTT_POINTS_PER_PHASE):
                temp = ms + (top - ms) * i / (TTT_POINTS_PER_PHASE - 1)
                t_start, t_50, t_finish = (self.tau(phase, x, temp) for x in TTT_FRACTIONS)
                if t_start is None or t_start >= TTT_DISPLAY_MAX_S:
                    continue
                if phase == "Ferrite":  # 50 % / 99 % of the austenite need not be attainable (equilibrium cap)
                    t_50 = t_finish = None
                points.append({
                    "temperature_C": round(temp, 2),
                    "phase": phase,
                    "tStart_s": _sig(t_start),
                    "t50_s": None if t_50 is None else _sig(t_50),
                    "tFinish_s": None if t_finish is None else _sig(t_finish),
                    "avramiExponent_n": None,
                    "drivingForce_DeltaT_C": round(self.start_temp[phase] - temp, 2),
                    "floorHit": False,
                })
        return points

    def start_integrals(self, aust_temp_c):
        """Per phase: the cumulative additivity integral C_i(T) = int_T^{T0} dT' / (S(0.01)/rate_i(T')) on a
        temperature grid from min(T0, T_i) down to Ms. For a linear cooling rate r the 1 % start is the first T
        where C_i(T) / r >= 1, so the phase starts above Ms iff r <= C_i(Ms)."""
        s_start = li_s(TTT_FRACTIONS[0])
        ms = self.temps["Ms"]
        out = {}
        for phase in LI_PHASES:
            top = min(aust_temp_c, self.start_temp[phase])
            grid, cum = [], []
            if top > ms:
                steps = max(1, int(math.ceil((top - ms) / CCT_STEP_K)))
                h = (top - ms) / steps
                total = 0.0
                grid.append(top)
                cum.append(0.0)
                for k in range(steps):
                    hi = top - k * h
                    total += h * self.rate_term(phase, hi - 0.5 * h) / s_start
                    grid.append(hi - h)
                    cum.append(total)
            out[phase] = (grid, cum)
        return out

    @staticmethod
    def start_for_rate(integral, rate):
        """Start temperature (degC) of one phase at cooling rate ``rate`` (K/s), or None above Ms."""
        grid, cum = integral
        if not cum or cum[-1] < rate:
            return None
        lo, hi = 0, len(cum) - 1
        while lo < hi:  # first index with cum >= rate
            mid = (lo + hi) // 2
            if cum[mid] >= rate:
                hi = mid
            else:
                lo = mid + 1
        if lo == 0:
            return grid[0]
        frac = (rate - cum[lo - 1]) / (cum[lo] - cum[lo - 1])
        return grid[lo - 1] + frac * (grid[lo] - grid[lo - 1])


def _sig(value, digits=6):
    return float(f"{value:.{digits}g}")


# ---------------------------------------------------------------------------------------------------------------
def predicted_hardness_hv(hrc, registry_id):
    """(HV or None, status) for a predicted HRC; see hardness_conversion_e140."""
    if registry_id not in E140_NON_AUSTENITIC_STEEL_IDS:
        return None, hardness_conversion_e140.STATUS_UNAVAILABLE_ALLOY_CLASS
    if hrc is None:
        return None, STATUS_HV_NO_HRC
    return hardness_conversion_e140.hrc_to_hv_non_austenitic_steel(hrc)


def _unavailable_cct_row(cr, status, reason, registry_id):
    hv, hv_status = predicted_hardness_hv(None, registry_id)
    return {
        "coolingRate_C_s": cr,
        "transformedStartTemp_C": None,
        "transformedStartTime_s": None,
        "primaryMicrostructure": None,
        "phaseFractions": {"Martensite_pct": None, "Bainite_pct": None, "Pearlite_Ferrite_pct": None,
                           "RetainedAustenite_pct": None},
        "predictedHardness_HRC": None,
        "predictedHardness_HV": hv,
        "predictedHardness_HV_status": hv_status,
        "transformedStart_status": status,
        "phaseFractions_status": status,
        "predictedHardness_HRC_status": status,
        "unavailableReason": reason,
        "phaseStartTemps_C": None,
    }


CCT_COOLING_RATES = (0.05, 0.2, 1.0, 5.0, 10.0, 25.0, 50.0, 100.0, 500.0, 2000.0)


def solve_phase_transformation_kinetics(alloy_name="AISI 4140", cooling_rate_c_s=10.0,
                                        grain_size_um=25.0, aust_temp_c=860.0,
                                        aging_time_h=8.0, aging_temp_c=720.0):
    """
    TTT curves (Li 1998), CCT starts by the additivity rule and critical temperatures; the precipitate coarsening
    and strengthening rows are unavailable for every alloy (SOL-K, see the module docstring).

    The Li model is reported only for a steel (registry descriptor type) whose registry composition lies inside
    the range of [Li96] p. 86; otherwise every TTT/CCT output is None with an explicit status and reason (see
    ``kineticsModel``). Registry parameters flagged in alloy_registry.KINETICS_PLACEHOLDERS are never reported.
    """
    start_time = time.perf_counter()

    registry_id, _legacy_name, alloy = resolve_kinetics_alloy(alloy_name)
    steel = is_steel_alloy(alloy)
    placeholders = placeholder_keys(registry_id)
    comp = alloy["composition_wt"]
    inside, violations, unchecked = li_composition_check(comp)
    modelled = steel and inside

    ae3 = alloy["Ae3_C"]
    ae1 = alloy["Ae1_C"]
    ms_registry = alloy["Ms_C"]
    mf_registry = alloy["Mf_C"]
    ccr_registry = alloy["critical_cooling_rate_C_s"]

    if not steel:
        unavailable_status, unavailable_reason, model_note = (
            STATUS_UNAVAILABLE_STEEL_ONLY, STEEL_ONLY_REASON, NON_STEEL_MODEL_NOTE)
    elif not inside:
        unavailable_status = STATUS_UNAVAILABLE_OUTSIDE_RANGE
        unavailable_reason = "composition outside the Li (1998) model range: " + "; ".join(violations)
        model_note = OUTSIDE_RANGE_NOTE
    else:
        unavailable_status = unavailable_reason = None
        model_note = LI_NOTE

    li = None
    li_block = None
    if modelled:
        user_cr = input_validation.require_positive("coolingRate_C_s", cooling_rate_c_s)
        grain = input_validation.require_positive("grainSize_um", grain_size_um)
        grain = input_validation.require_range("grainSize_um", grain, *GRAIN_SIZE_BOUNDS_UM, "um")
        aust = input_validation.require_range("austTemp_C", aust_temp_c, *AUST_TEMP_BOUNDS_C, "degC")
        li = LiModel(comp, astm_grain_size_number(grain))
    else:
        # Unmodelled-alloy echoes must still be physical, without imposing Li model bounds.
        user_cr = input_validation.require_positive("coolingRate_C_s", cooling_rate_c_s)
        input_validation.require_positive("grainSize_um", grain_size_um)
        aust_echo = input_validation.require_finite("austTemp_C", aust_temp_c)
        if aust_echo < -ZERO_C_K:
            raise input_validation.ValidationError(input_validation.OUT_OF_RANGE, "austTemp_C",
                                                  "must be >= -273.15 degC", {"value": aust_echo})
    # SOL-K: aging inputs are validated for every alloy, before any arithmetic on them (SPEC section 6.3).
    checked_aging_inputs(aging_temp_c, aging_time_h)  # echoed unchanged below; nothing is converted or clamped

    # 1. TTT curves
    if modelled:
        ttt_curves = li.ttt_curves()
        ttt_floor = {"status": STATUS_TTT_NO_FLOOR, "floorValue_s": None, "pointCount": len(ttt_curves),
                     "floorHitCount": 0, "note": TTT_NO_FLOOR_NOTE}
    else:
        ttt_curves = None
        ttt_floor = {"status": unavailable_status, "floorValue_s": None, "pointCount": None,
                     "floorHitCount": None, "note": TTT_UNAVAILABLE_NOTE}

    # 2. CCT starts (additivity rule) and the model critical cooling rate
    cct_map = []
    ccr_model = None
    user_start = None
    if modelled:
        temps = li.temps
        ms = temps["Ms"]
        fully_austenitic = aust > temps["Ae3"]
        not_austenitic_reason = None if fully_austenitic else NOT_AUSTENITIC_REASON_FMT.format(aust=aust, ae3=temps["Ae3"])
        integrals = li.start_integrals(aust) if fully_austenitic else None
        if fully_austenitic:
            ccr_model = max(integrals[p][1][-1] if integrals[p][1] else 0.0 for p in LI_PHASES)

        def first_start(rate):
            starts = {p: li.start_for_rate(integrals[p], rate) for p in LI_PHASES}
            found = [(t, p) for p, t in starts.items() if t is not None]
            return (max(found) if found else None), starts

        for cr in CCT_COOLING_RATES:
            if not fully_austenitic:
                cct_map.append(_unavailable_cct_row(cr, STATUS_START_NOT_AUSTENITIC, not_austenitic_reason,
                                                    registry_id))
                continue
            first, starts = first_start(cr)
            if first is None:
                start_temp, start_status, primary = ms, STATUS_START_ATHERMAL, "Martensite (Athermal)"
            else:
                start_temp, start_status, primary = first[0], STATUS_START_LI, first[1]
            hv, hv_status = predicted_hardness_hv(None, registry_id)
            cct_map.append({
                "coolingRate_C_s": cr,
                "transformedStartTemp_C": round(start_temp, 1),
                "transformedStartTime_s": _sig((aust - start_temp) / cr, 4),
                "primaryMicrostructure": primary,
                "phaseFractions": {"Martensite_pct": None, "Bainite_pct": None, "Pearlite_Ferrite_pct": None,
                                   "RetainedAustenite_pct": None},
                "predictedHardness_HRC": None,
                "predictedHardness_HV": hv,
                "predictedHardness_HV_status": hv_status,
                "transformedStart_status": start_status,
                "phaseFractions_status": STATUS_FRACTIONS_NOT_COMPUTED,
                "predictedHardness_HRC_status": STATUS_FRACTIONS_NOT_COMPUTED,
                "unavailableReason": None,
                # Independent 1 % start of each phase along this cooling path (None: not reached above Ms).
                "phaseStartTemps_C": {p: (None if t is None else round(t, 1)) for p, t in starts.items()},
            })
        if fully_austenitic:
            user_start = first_start(user_cr)[0]
    else:
        for cr in CCT_COOLING_RATES:
            cct_map.append(_unavailable_cct_row(cr, unavailable_status, unavailable_reason, registry_id))

    # 3. PRECIPITATE COARSENING AND STRENGTHENING: unavailable for every alloy (SOL-K, SPEC section 6.3).
    # The generic Lifshitz-Slyozov-Wagner law with constants shared by every alloy, and the 280 MPa / 9 nm
    # strengthening curve, are not evaluated: neither has a source-bound model or sourced constants, and one
    # asymptotic coarsening law cannot represent nucleation, growth from supersaturation, dissolution or a changing
    # population. The rows keep the aging-time grid; every value is null with a status and reason codes.
    lsw_reason = None
    lsw_status = STATUS_LSW_NOT_MODELLED
    lsw_reason_codes = LSW_REASON_CODES

    lsw_coarsening_profile = [{
        "agingTime_h": t_h,
        "meanRadius_nm": None,
        "precipitationHardening_MPa": None,
        "strengtheningMechanism": None,
        "status": lsw_status,
        "reasonCodes": list(lsw_reason_codes),
    } for t_h in LSW_AGING_TIMES_H]

    # 4. CALPHAD (equilibrium text) vs KINETICS at the selected cooling rate
    if modelled:
        reason_reality = (
            "Li (1998) start-time model with the additivity rule; phase fractions are not computed. The martensite "
            "% is given only when no diffusional start is reached above Ms (Koistinen-Marburger, alpha = 0.011/K "
            "as in Li 1996 Eq. 3.76, at 25 C)")
        if ccr_model is None:
            reality = {"coolingRate_C_s": user_cr, "criticalCoolingRate_C_s": None, "isSuppressedEquilibrium": None,
                       "predictedMartensite_pct": None, "diffusionSuppressionIndex": None, "verdict": None,
                       "status": STATUS_START_NOT_AUSTENITIC,
                       "reason": NOT_AUSTENITIC_REASON_FMT.format(aust=aust, ae3=li.temps["Ae3"])}
        else:
            suppressed = user_start is None
            km = 1.0 - math.exp(-KM_ALPHA_PER_K * max(0.0, li.temps["Ms"] - ROOM_TEMPERATURE_C))
            reality = {
                "coolingRate_C_s": user_cr,
                "criticalCoolingRate_C_s": _sig(ccr_model, 4),
                "isSuppressedEquilibrium": suppressed,
                "predictedMartensite_pct": round(km * 100.0, 1) if suppressed else None,
                "diffusionSuppressionIndex": None,
                "verdict": ("No diffusional start above Ms (Li 1998 additivity): martensite from Ms" if suppressed else
                            f"{user_start[1]} start at {user_start[0]:.1f} C (Li 1998 additivity); "
                            "phase fractions not computed"),
                "status": STATUS_LI_SCREENING,
                "reason": reason_reality,
            }
        calphad_vs_kinetics_gap = {
            "equilibriumPrediction": {
                "stablePhasesAtRT": STEEL_EQUILIBRIUM_PHASES,
                "martensiteFraction": "0.0% (Thermodynamically Forbidden in Equilibrium)",
                "soluteSupersaturation": "Near Zero (<0.01 wt% C in ferrite)",
                "status": STATUS_STATIC_TEXT,
                "reason": "fixed steel text; no equilibrium (CALPHAD) calculation is performed here",
            },
            "kineticRealityAtSelectedCooling": reality,
        }
    else:
        calphad_vs_kinetics_gap = {
            "equilibriumPrediction": {
                "stablePhasesAtRT": None, "martensiteFraction": None, "soluteSupersaturation": None,
                "status": unavailable_status, "reason": unavailable_reason,
            },
            "kineticRealityAtSelectedCooling": {
                "coolingRate_C_s": user_cr, "criticalCoolingRate_C_s": None, "isSuppressedEquilibrium": None,
                "predictedMartensite_pct": None, "diffusionSuppressionIndex": None, "verdict": None,
                "status": unavailable_status, "reason": unavailable_reason,
            }
        }

    # Registry placeholders (alloy_registry.KINETICS_PLACEHOLDERS) are never reported as results.
    alloy_out = dict(alloy)
    for key in placeholders:
        alloy_out[key] = None
    if not steel:
        # Steel parameters of a non-steel alloy (eutectoid Ae1, martensite critical cooling rate) are not published.
        alloy_out["Ae1_C"] = None
        alloy_out["critical_cooling_rate_C_s"] = None

    def registry_status(key):
        return STATUS_UNAVAILABLE_PLACEHOLDER if key in placeholders else STATUS_REGISTRY_VALUE

    if modelled:
        temps = li.temps
        critical = {
            "Ae3_BetaTransus_GammaSolvus_C": round(temps["Ae3"], 1),
            "Ae1_C": round(temps["Ae1"], 1),
            "Ms_C": round(temps["Ms"], 1),
            "Mf_C": None,
            "CriticalCoolingRate_CCR_C_s": None if ccr_model is None else _sig(ccr_model, 4),
            "Ae1_C_status": STATUS_GRANGE,
            "Ms_C_status": STATUS_MS_KR,
            "Mf_C_status": STATUS_MF_NOT_MODELLED,
            "CriticalCoolingRate_CCR_status": STATUS_LI_SCREENING if ccr_model is not None else STATUS_START_NOT_AUSTENITIC,
            "Ae3_C_status": STATUS_GRANGE,
            "Bs_C": round(temps["Bs"], 1),
            "Bs_C_status": STATUS_BS_LI,
        }
        li_block = {
            "astmGrainSize_G": round(li.grain_g, 3),
            "grainSizeDefinition": ("priorGrainSize_um is taken as the mean planar grain diameter d; "
                                    "G = -3.2877 - 6.6439 log10(sqrt(pi/4) d / mm) (ASTM E112, Collins et al. Eqs. 3-4)"),
            "activationEnergy_J_mol": LI_Q_J_MOL,
            "compositionFactors": {p: _sig(v) for p, v in li.factors.items()},
            "reactionIntegral_S": {name: _sig(li_s(x)) for name, x in zip(("X_0p01", "X_0p5", "X_0p99"), TTT_FRACTIONS)},
            "startCriterion": ("1 % reaction (X = 0.01) per phase; each phase's start curve is integrated "
                               "independently from the austenitizing temperature (no phase interaction)"),
            "criticalCoolingRateDefinition": ("slowest linear cooling rate from the austenitizing temperature at which "
                                              "no ferrite, pearlite or bainite 1 % start is reached above Ms"),
            "fractionsComputed": False,
            "fractionsReason": FRACTIONS_REASON,
            "reactionFractionBasis": dict(REACTION_FRACTION_BASIS),
        }
    else:
        critical = {
            "Ae3_BetaTransus_GammaSolvus_C": ae3,
            "Ae1_C": ae1 if steel else None,
            "Ms_C": None if "Ms_C" in placeholders else ms_registry,
            "Mf_C": None if "Mf_C" in placeholders else mf_registry,
            "CriticalCoolingRate_CCR_C_s": None,
            "Ae1_C_status": STATUS_REGISTRY_VALUE if steel else STATUS_UNAVAILABLE_STEEL_ONLY,
            "Ms_C_status": registry_status("Ms_C"),
            "Mf_C_status": registry_status("Mf_C"),
            "CriticalCoolingRate_CCR_status": unavailable_status,
            "Ae3_C_status": STATUS_REGISTRY_VALUE,
            "Bs_C": None,
            "Bs_C_status": unavailable_status,
        }

    kinetics_model = {
        "status": "available" if modelled else "unavailable",
        "reason": unavailable_reason,
        "scope": SCOPE,
        "registryAlloyId": registry_id,
        "illustrativeOnly": True,
        "note": model_note,
        "placeholderParameters": placeholders,
        "lswPrecipitateCoarsening": {
            "status": lsw_status,
            "note": None,
            "reason": lsw_reason,
            "reasonCodes": list(lsw_reason_codes),
        },
        "modelVersion": LI_MODEL_VERSION,
        "sourceLabel": SOURCE_LABEL,
        "validationStatus": VALIDATION_STATUS,
        "evidenceLevel": EVIDENCE_LEVEL,
        "validityDomain": {
            # "inside-partially-checked": inside every bound that could be checked, but a bound (Al) is unchecked
            "status": ("not-applicable-alloy-class" if not steel else
                       ("outside" if not inside else ("inside-partially-checked" if unchecked else "inside"))),
            "source": VALIDITY_SOURCE,
            "violations": violations if steel else [],
            "unchecked": unchecked if steel else [],
            "grainSize": None if li is None else {
                "astmG": round(li.grain_g, 3),
                "inputBounds_um": list(GRAIN_SIZE_BOUNDS_UM),
                "comparedRange_G": list(COMPARED_G_RANGE),
                "insideComparedRange": COMPARED_G_RANGE[0] <= li.grain_g <= COMPARED_G_RANGE[1],
                "note": ("input bounds are a sanity limit of this implementation; the compared range is the span of "
                         "published examples reproduced in test_kinetics_li1998 (Collins 2023, Li 1996), not a "
                         "validity statement of the source"),
            },
        },
        "li1998": li_block,
    }

    compute_time_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

    return {
        "success": True,
        "engine": ENGINE,
        "computeTimeMs": compute_time_ms,
        "alloy": alloy_name,
        "alloyMetadata": alloy_out,
        "inputParameters": {
            "selectedCoolingRate_C_s": user_cr,
            "austSolutionTemp_C": aust_temp_c,
            "priorGrainSize_um": grain_size_um,
            "agingTemp_C": aging_temp_c,
            "agingTime_h": aging_time_h
        },
        "criticalTransformationTemperatures": critical,
        "tttIsothermalCurves": ttt_curves,
        "cctContinuousCoolingMap": cct_map,
        "lswPrecipitateCoarsening": lsw_coarsening_profile,
        "calphadVsKineticsGap": calphad_vs_kinetics_gap,
        "kineticsModel": kinetics_model,
        "tttIncubationFloor": ttt_floor,
    }


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--status":
        print(json.dumps({
            "status": "ready",
            "engine": "MetalliX Python steel TTT/CCT kinetics solver (Li 1998 model, additivity rule)",
            "capabilities": ["Li 1998 TTT C-curves (1%, 50%, 99%) for low-alloy steels", "Additivity-rule CCT starts",
                             "Grange Ae3/Ae1, Li Bs, Kung-Rayment Ms"]
        }))
        sys.exit(0)

    try:
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            print(json.dumps({"error": "Empty stdin payload", "errorKind": "internal"}))
            sys.exit(1)

        data = json.loads(raw_input)
        mat = data.get("alloy", "AISI 4140")
        cr = data.get("coolingRate_C_s", 10.0)
        d_grain = data.get("grainSize_um", 25.0)
        t_aust = data.get("austTemp_C", 860.0)
        t_aging = data.get("agingTemp_C", 720.0)
        time_aging = data.get("agingTime_h", 8.0)

        result = solve_phase_transformation_kinetics(mat, cr, d_grain, t_aust, time_aging, t_aging)
        result["provenance"] = provenance(resolve_kinetics_alloy(mat)[0])
        print(json.dumps(result, allow_nan=False))  # SOL-K: a bare NaN/Infinity token is never emitted
    except input_validation.ValidationError as err:
        print(json.dumps(input_validation.validation_envelope(err)))
        sys.exit(2)
    except Exception as e:
        print(json.dumps({"error": str(e), "errorKind": "internal"}))
        sys.exit(1)
