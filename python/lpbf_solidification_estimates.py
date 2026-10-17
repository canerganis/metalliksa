"""SOL-C: labelled solidification estimates on their own opt-in served channel (RC1).

Authority: docs/research/SPEC_solidification_2026-10-14.md Amendments 5, 6 and 7 (Amendment 7 controls conflicts:
typed emit schema, separate warning and blocking vocabularies, tier enum, precision rule), the research records
docs/research/sol_c_* and the integration contract docs/research/SPEC_solidification_integration_2026-10-15.md
(3.1 to 3.7, 4.x, 7.x, D13). Maintainer decisions of 2026-10-16: Tier 1 "Estimated" with an input sensitivity range,
Tier 2 "Uncalibrated estimate" with reduced precision and the unknown-uncertainty sentence, an out-of-domain warning
beside every affected value, and a constructive no-value text wherever a physics model or input is missing.

Channel (RC1, re-gate verdict section D item 1): ``POST /api/python/lpbf-solidification-estimates``, worker method
``solidification-estimates``, response schema CHANNEL_SCHEMA and channel identity CHANNEL_ID. It is opt-in: no default
thermal result, Build Job, process window, regime or verdict reads it, and nothing it computes flows back. It is not a
P8 research import (R-ISO-1) and adds no file to the thermal fingerprint manifest, so the pin and W/D stay byte-equal
against the SOL-T head.

Field parent. The estimate never rebuilds or re-implements the served conduction field. For each solve it calls the
served ``calculate_meltpool_physics`` and captures, in the calling thread only, the exact arguments the solver hands
to ``solidification_front.evaluate_solidification`` (the field closure, the liquidus, the scan speed, the rear search
box and the Fabbro keyhole-leg flag). The capture wrapper always delegates to the real function, so the served
result is byte-identical with or without it (python/test_lpbf_solidification_estimates.py proves it for every alloy
and kernel). Every sensitivity arm is such a full served solve with its own property overrides: alpha, the kernel
reductions, the field, its roots and the co-located tuples are recomputed; no threshold is swapped on stored tuples.

Physics routes (all evaluated per local tuple before any aggregation; never at separate G and R medians):
- Q-T kinematics (Ghosh et al. 2017 Sec. 3.1; Eagar and Tsai 1983 moving conduction framework): rear solidifying
  centre-plane liquidus branch y = 0 between the deepest liquidus point and the rear surface crossing, midpoint nodes
  of 32 equal-x cells (8 and 16 for the support-resolution check), chord-length weights; G = |grad T|,
  R = v gx / G, cooling = v gx, G/R = G^2 / (v gx); weighted medians of the local outputs, spatial percentiles kept
  separate from any uncertainty statement.
- PDAS/SDAS correlations of Amendment 6.3 behind the Amendment 7.1 capillary screening gate of the alloy's named
  binary proxy; the Ni-Nb Hunt / Kurz-Fisher alternatives with their binary dendrite-range gate.
- Planar stability index chi and the Hunt grain-envelope fraction with the Durga true-fraction class convention,
  refused for chi <= 1, a tip undercooling above P, absolute stability or an aluminium tip at the eutectic (A7.5);
  tip Peclet diagnostic in every alloy.
- Ti-6Al-4V time-scoped KM progress on the single-pass material-point path (rule finite-25K-above-preheat-v1, A7.6);
  AlSi10Mg terminal equilibrium reference and binary Scheil microconstituents at the one named Al-10Si-0.45Mg scenario
  (A7.9); no phase-fraction model for IN718, 316L and IN625 (constructive no-value text).

Tier (A7 items 2 and 3): any family transfer, source-process transfer or source-domain violation anywhere in the
dependency closure caps a value at "Physics estimate" (shown as "Uncalibrated estimate"); with the present inherited
thermal parents this is every default value of every alloy, including G, R, cooling and G/R. The executed OFAT sweep
is then only an auxiliary ``inputSensitivity`` record, never an error interval or a promotion. Tier 1 needs a wholly
in-domain closure plus the complete matched sweep; ``estimate_tier`` implements it, nothing default reaches it.

Nothing here is a measurement, a validation or a calibration: every container states the screening-only ceiling,
Research maturity and physicalValidation unvalidated.
"""
from __future__ import annotations

import contextlib
import copy
import hashlib
import json
import math
import threading
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import quantity_envelope as qe

CHANNEL_SCHEMA = "lpbf-solidification-estimates-1"
CHANNEL_ID = "sol-c-solidification-estimates"
MODEL_ID = "solidification-estimates-v1"
SAMPLER_ID = "rear-centre-plane-liquidus-branch-v1"
KELVIN = 273.15

# Numerical controls (A5.2, A5.3): engineering settings, not material constants.
NODE_COUNT = 32
SUPPORT_RESOLUTIONS = (8, 16, 32)
MIN_BRANCH_SAMPLES = 3
STEP_FRACTION_OF_DEPTH = 2.0e-3
ORDER_BAND_INTERIOR = (1.5, 2.5)
ORDER_BAND_SURFACE = (0.75, 1.25)
ROOT_ITERATIONS = 100
IDENTITY_RTOL = 1e-12

# --- Visible texts (drafts pending the maintainer's wording round, except the maintainer's tier labels) -------------

TIER2_LABEL = qe.ESTIMATE_TIER_LABELS["Physics estimate"]
UNKNOWN = qe.UNCERTAINTY_STATEMENT_TIER2
QUANTITY_NAMES = {
    "thermalGradient": "thermal gradient G", "normalSpeed": "solidification rate R",
    "coolingRate": "cooling rate", "gOverR": "G/R",
}
NO_CROSSING_TEXT = ("A solidifying liquidus crossing is needed. Check absorbed power, preheat and the selected "
                    "temperature-field model.")
FEW_POINTS_TEXT = "Only these local points were computed. A front summary needs more solidifying samples."
NO_FRONT_TEXT = ("A solidification estimate needs a compatible cooling side front with finite positive gradient and "
                 "growth rate.")
KEYHOLE_TEXT = ("The served depth comes from the keyhole leg, and this conduction temperature field does not include "
                "the keyhole cavity. The conduction-field surrogate is turned off for this request; turn it on (the "
                "default) to see an uncalibrated estimate of the conduction field's own rear front.")
# Maintainer-approved warning (2026-10-16, Astra keyhole consult docs/research/SOL_C_TI64_KEYHOLE_CONSULT_2026-10-16.md
# section 4): attached to the conduction-surrogate front parent, so every thermal and derived quantity inherits it.
KEYHOLE_SURROGATE_WARNING = ("Keyhole regime. These estimates use the rear solidifying front of a conduction-only "
                             "temperature field. The field does not include keyhole energy deposition, melt flow or "
                             "cavity motion and is not coupled to the served melt-pool depth. Spacing, morphology and "
                             "phase estimates inherit this assumption.")
SURROGATE_ID = "conduction-field-surrogate-v1"
SURROGATE_TEXT = (f"{TIER2_LABEL} from a conduction-field surrogate. The temperature field does not include the "
                  f"keyhole cavity. {UNKNOWN}")
CAPILLARY_TEXT = ("This correlation predicts a scale below the capillary screening limit of its stated binary model. "
                  "A compatible rapid-solidification spacing model is needed.")
PLANAR_TEXT = "This model predicts a planar front. A cellular or planar stability and spacing model is needed."
GRAIN_DOMAIN_TEXT = ("The planar stability index can be computed here. A grain fraction needs a growth model for this "
                     "planar or rapid solidification regime. The current dendrite model cannot represent it.")
AL_EUTECTIC_TEXT = ("The primary aluminium tip reaches the eutectic in this model. A coupled primary and eutectic "
                    "growth model is needed for a grain fraction here.")
KM_MISSING_TEXT = ("A retained phase estimate needs a cooling path and the beta fraction entering martensite "
                   "formation. Slow cooling or reheating also needs competing transformation kinetics.")
SECONDARY_ARMS = "Secondary arms may not form."
PHASE_NO_MODEL_TEXT = {
    "in718": ("No phase fraction is formed from this front model. Supply a phase-resolved gamma, carbide and Laves "
              "solidification model with residual chemistry, then delta, gamma-prime and gamma-double-prime kinetics "
              "for the requested heat path."),
    "ss316l": ("No austenite or ferrite fraction is formed from this front model. Supply the C, N, Cr, Ni and Mo "
               "composition, a competing austenite and ferrite solidification-growth model and the subsolidus "
               "history. The alloy name and G/R do not select the phase mode."),
    "in625": ("No phase fraction is formed from this front model. Supply a multicomponent segregation and terminal "
              "phase-selection model with the heat path; later delta and carbide fractions need compatible kinetics."),
}
PHASE_CONTEXT = {
    "ti6al4v": ("SLM Ti-6Al-4V studies report an as-built martensitic structure that changes with subsequent heat "
                "treatment. This front estimate does not predict the final alpha/beta or martensite content.",
                "Vrancken et al. 2012, J. Alloys Compd. 541, 177-185, doi 10.1016/j.jallcom.2012.07.022, Abstract"),
    "alsi10mg": ("The cited SLM study observed primary aluminium cells bordered by a silicon network; build-platform "
                 "heating changed that network. This is context, not a phase or precipitation prediction for this "
                 "build.", "Casati et al. 2018, Metals 8, 954, doi 10.3390/met8110954, section 3.1"),
    "in718": ("The cited as-manufactured SLM IN718 study observed a cellular-dendritic structure with interdendritic "
              "Laves phases. This does not establish the phase content of the current build.",
              "Deng et al. 2018, Mater. Sci. Eng. A 713, 294-306, doi 10.1016/j.msea.2017.12.043, Abstract"),
    "in625": ("The cited laser powder-bed IN625 study found niobium- and molybdenum-enriched interdendritic regions "
              "and heat-treatment-dependent delta precipitation. A local liquidus-front estimate does not determine "
              "the final precipitate content.",
              "Lass et al. 2017, Metall. Mater. Trans. A 48, doi 10.1007/s11661-017-4304-6, Abstract"),
    "ss316l": ("The cited laser powder-bed 316L study reports an austenitic material with solidification-enabled "
               "cellular structures. This does not determine primary solidification mode or the phase fractions of "
               "the current build.", "Wang et al. 2018, Nature Materials 17, 63-71, doi 10.1038/nmat5021, Abstract"),
}
ALLOY_NAMES = {"ti6al4v": "Ti-6Al-4V", "alsi10mg": "AlSi10Mg", "in718": "IN718", "ss316l": "316L", "in625": "IN625"}
MATERIAL_NAMES = {"ti6al4v": "Ti-6Al-4V", "alsi10mg": "AlSi10Mg", "in718": "Inconel 718",
                  "ss316l": "316L Stainless Steel", "in625": "Inconel 625"}

# --- Source references ------------------------------------------------------------------------------------------------

def _src(source_id: str, locator: str, level: str = "primary-read") -> Dict[str, str]:
    return qe.source_ref(source_id, locator, level)


SRC_GHOSH_KINEMATICS = _src("ghosh2017-kinematics", "Ghosh et al. 2017, Modelling Simul. Mater. Sci. Eng. 25 065002, "
                            "doi 10.1088/1361-651X/aa7369, Sec. 3.1 (PDF9/printed8): normal projection of scan velocity "
                            "and the full Cartesian gradient norm")
SRC_EAGAR_TSAI = _src("eagar-tsai-1983", "Eagar and Tsai 1983, Welding Journal, printed 346s-348s, Eqs. 1 to 6 "
                      "(moving conduction framework; the repository kernel keeps its own regularisation)")

# Endpoint and thermophysical parent scope per alloy (A5.4 parent table, A6.1, A7 2 and 3).
DENSITY_SOURCES = {
    "ti6al4v": (4430.0, "TIMET, TIMETAL 6-4 Properties, PDF6/printed2 Density paragraph, 4.43 g/cc"),
    "alsi10mg": (2696.0, "Akwaboa et al. 2023, Materials 16, 4920, Table 3 (PDF p.5), sample 100-0.2, 2.696 g/cm3"),
    "in718": (8190.0, "ATI Allvac, ATI 718 Alloy NI-105 v2, PDF1 Physical Properties, Density 8.19 g/cm3"),
    "ss316l": (7990.0, "AK Steel 316/316L data sheet 316/316L-S-08-01-07, PDF2 Physical Properties, Density 7.99 g/cm3"),
    "in625": (8440.0, "Special Metals, INCONEL alloy 625 (Aug 2013), PDF2 Table 2 Physical Constants, 8.44 g/cc"),
}
THERMAL_PARENT_SCOPE = {
    "ti6al4v": "Gan conversion-interpreted nominal endpoints (the Cezairliyan solidus contradiction stays visible); "
               "Kirchhoff mean of the Gan/Mills solid k(T) and cp(T); nominal constant ambient density",
    "alsi10mg": "Brandt Al-9Si-0.6Mg heating endpoints transferred in both Si and Mg; held as-built node k and cp; "
                "source-located kernel density; IR as-built surface absorption",
    "in718": "Mills/SMC compiled endpoint pair; Mills melting-point k and cp held constant; ambient density",
    "ss316l": "Mills SS316 to 316L endpoint transfer (carbon and other chemistry differ); melting-point k and cp held "
              "constant; nominal 316L ambient density",
    "in625": "Sabau linear-fraction endpoint convention; Weaver melting-point k and cp evaluated at the solidus; "
             "ambient density",
}

# --- Binary proxies of the capillary gate and the morphology model (A6.4 table, A7.1) --------------------------------
#
# Positive slope magnitudes; C0 in wt percent. Ti: freezing-range-closed Ti-10X surrogate of Ghosh 2018 Table 6
# (|m| derived from P = 50 K, the printed 0.088 K/wt% is incompatible and recorded). Al: Azizi 2020 Table II Al-0.5Si
# coefficients at the named 10 wt% Si scenario with Ce 12.6 wt% (Metals 2022 Table 1). Ni: Ghosh 2017 Table 2 Ni-5Nb.
# 316L: Gerstgrasser 2021 Table 7 effective Fe-0.029C.
PROXIES = {
    "ti6al4v": {"c": 10.0, "k": 0.838, "m": 50.0 * 0.838 / (10.0 * (1.0 - 0.838)), "d": 9.5e-9, "gamma": 2.2e-7,
                "nuclei": 5e14, "activation": 8.0, "ce": None, "printedSlope": 0.088,
                "locator": "Ghosh et al. 2018, arXiv 1809.01056, Table 6 (Ti-10X surrogate; |m| derived from the "
                           "source freezing range 50 K, printed 0.088 K/wt% incompatible)",
                "family": "a Ti-10X binary surrogate", "chem": "solute C0 = 10 wt% of the closed surrogate"},
    "alsi10mg": {"c": 10.0, "k": 0.13, "m": 6.5, "d": 3e-9, "gamma": 9e-8, "nuclei": 2e15, "activation": 8.0,
                 "ce": 12.6, "printedSlope": None,
                 "locator": "Azizi et al. 2020, arXiv 2003.09757v1, Table II (Al-0.5Si); Ce 12.6 wt% Metals 12 (2022) "
                            "1711 Table 1",
                 "family": "dilute Al-Si (Al-0.5Si) binary coefficients", "chem": "Si = 10 wt% named scenario"},
    "in718": {"c": 5.0, "k": 0.48, "m": 10.5, "d": 3e-9, "gamma": 3.65e-7, "nuclei": 2.65e14, "activation": 0.0,
              "ce": None, "printedSlope": None,
              "locator": "Ghosh et al. 2017, arXiv 1705.06669, Table 2 (Ni-5Nb binary)",
              "family": "Ni-5Nb binary", "chem": "Nb = 5 wt% proxy"},
    "in625": {"c": 5.0, "k": 0.48, "m": 10.5, "d": 3e-9, "gamma": 3.65e-7, "nuclei": 2.65e14, "activation": 0.0,
              "ce": None, "printedSlope": None,
              "locator": "Ghosh et al. 2017, arXiv 1705.06669, Table 2 (Ni-5Nb binary, explicit IN625 transfer)",
              "family": "Ni-5Nb binary (Ni-family transfer to IN625)", "chem": "Nb = 5 wt% proxy (not an IN625 assay)"},
    "ss316l": {"c": 0.029, "k": 0.17, "m": 84.3, "d": 2e-9, "gamma": 1.9e-7, "nuclei": 1e13, "activation": 8.0,
               "ce": None, "printedSlope": None,
               "locator": "Gerstgrasser et al. 2021, Materials & Design 199, 109395, Table 7 (effective Fe-0.029C)",
               "family": "effective Fe-0.029C binary", "chem": "C = 0.029 wt% source proxy"},
}
NUCLEATION_SCENARIOS = {
    "ti6al4v": "Gao et al. 2025 Table 2 Ti64 set transferred to a single threshold",
    "alsi10mg": "Azizi 2020 Table II inoculant count read as all sites eligible; activation 8 K declared",
    "in718": "Knapp casting-map-derived N0 scenario, ideal potent-nucleant activation 0 K",
    "in625": "Ni-family N0 scenario copied from IN718, activation 0 K",
    "ss316l": "declared N0 and activation scenario",
}
SRC_HUNT_DURGA = _src("durga-lindwall-2023", "Durga and Lindwall 2023, Additive Manufacturing 78, 103802, doi "
                      "10.1016/j.addma.2023.103802, section 2.1 Eqs. 2, 3, 7, 8 and the paragraph after Eq. 9 "
                      "(true-fraction class convention 0.0049 / 0.49; indexed primary text)", "secondary-read")
SRC_BROOKE_TIP = _src("brooke-2025", "Brooke et al. 2025, Nature Communications 16, 5710, doi "
                      "10.1038/s41467-025-60162-0, Eqs. 1, 2 and 6 (P, Q and the solutal Hunt tip law)")
SRC_A7_CAPILLARY = _src("solc-a7-capillary", "SPEC Amendment 7 item 1: declared one-sided quasi-static binary screening "
                        "bound lambda_cut = 2 pi sqrt(Gamma / (P R / D - G))", "repository-attribution")

# PDAS / SDAS laws (A6.3; results in micrometres unless SI).
NI_HUNT_A = 1.1773863284676703e-3
NI_KF_A = 2.5821435943712695e-3
NI_KE, NI_GAMMA, NI_DT0, NI_DL = 0.48, 3.65e-7, 57.0, 3.0e-9
NI_VAB = NI_DT0 * NI_DL / (NI_KE * NI_GAMMA)
SPACING = {
    "ti6al4v": {
        "pdas": {"definition": "pdas-correlation", "slope": 62.0, "intercept": 699.0, "n": 0.39, "uses": "q",
                 "locator": "Mizukami et al. 2020, ISIJ Int., doi 10.2355/isijinternational.ISIJINT-2020-089, Eq. 4"},
        "sdas": {"definition": "sdas", "slope": 33.0, "intercept": 366.0, "n": 0.40, "uses": "q",
                 "locator": "Mizukami et al. 2020, ISIJ Int., Eq. 5"},
        "text": ("{label} from a titanium ingot solidification correlation. This is a process and composition "
                 "transfer."),
        "domain": "EB-remelted Ti alloy ingots, Al groups 2.9 to 5.7 wt%, plotted cooling 1 to 100 K/s",
    },
    "alsi10mg": {
        "pdas": {"definition": "pdas-correlation", "a": 165.0, "n": 0.4, "uses": "q",
                 "locator": "Gandolfi et al. 2021, Metals 11, 1019, doi 10.3390/met11071019, PDF13 Eq. 1"},
        "sdas": {"definition": "sdas", "a": 22.0, "n": 2.0 / 3.0, "uses": "R_mm_s",
                 "locator": "Gandolfi et al. 2021, Metals 11, 1019, PDF13 Eq. 2 (Al-10Si-0.45Mg)"},
        "text": ("{label} from directional solidification of an Al-Si-Mg alloy. The source chemistry is "
                 "Al-10Si-0.45Mg."),
        "domain": "directional casting, plotted q 0.05 to 10.75 K/s and R 0.300 to 1.240 mm/s",
    },
    "ss316l": {
        "pdas": {"definition": "pdas-correlation", "a": 80.0, "n": 0.33, "uses": "q",
                 "locator": "Bunaziv et al. 2023, doi 10.1007/s00170-023-11567-y, PDF16/printed926 Eq. 2"},
        "sdas": {"definition": "sdas", "a": 25.0, "n": 0.28, "uses": "q",
                 "locator": "Bunaziv et al. 2023, PDF17/printed927 Eq. 6"},
        "text": ("{label} from an austenitic stainless steel spacing correlation used for 316L cladding. The "
                 "cooling-rate definition and process are transferred."),
        "domain": "316L laser cladding; 1450 to 1350 C cooling average, illustrative 115 to 5204 K/s",
    },
    "in718": {
        "pdas": {"definition": "pdas-model-alternatives",
                 "locator": "Ghosh et al. 2017, Table 2/PDF8, Eq. 7 (Hunt) and Eq. 8 (Kurz-Fisher)"},
        "sdas": {"definition": "sdas", "a": 19.5, "n": 0.63, "uses": "q",
                 "locator": "Mitchell 2005, Superalloys 2005, 299-310, PDF4/printed302 Eq. 1"},
        "text": "{label} from two binary Ni-Nb dendrite models transferred to IN718.",
        "domain": "Ni-5Nb binary on the source fixed-G line G = 1e7 K/m",
    },
    "in625": {
        "pdas": {"definition": "pdas-model-alternatives",
                 "locator": "Ghosh et al. 2017, Table 2/PDF8, Eq. 7 (Hunt) and Eq. 8 (Kurz-Fisher), IN625 transfer"},
        "sdas": {"definition": "sdas", "a": 19.5, "n": 0.63, "uses": "q",
                 "locator": "Mitchell 2005, Superalloys 2005, PDF4/printed302 Eq. 1, IN718 to IN625 transfer"},
        "text": "{label} from two binary Ni-Nb dendrite models transferred to IN625.",
        "domain": "Ni-5Nb binary on the source fixed-G line G = 1e7 K/m",
    },
}

# KM (Salsi, Chiumenti and Cervera 2018, Metals 8, 633, section 3.2.2 Eq. 19 and section 4.1; A7.6).
KM_MS_C, KM_TRANSUS_C, KM_COEFFICIENT, KM_RATE_K_S, KM_OFFSET_K = 575.0, 998.0, 0.005, 410.0, 25.0
KM_LOCATOR = ("Salsi, Chiumenti and Cervera 2018, Metals 8, 633, doi 10.3390/met8080633, PDF9 Eq. 19 and PDF12 "
              "before Fig. 7 (km 0.005 1/K, Ms 575 C, transus 998 C, 410 K/s)")
KM_PATH_RATIO = 1.15
KM_PATH_FIRST_STEP_M = 1e-7
KM_PATH_MAX_M = 1.0
KM_TIME_TOLERANCE_REL = 1e-3
KM_TEMPERATURE_TOLERANCE_K = 1e-6
# Al (A6.4, A7.9): one named scenario, CIAAW abridged atomic weights.
AL_SI, AL_MG = 0.10, 0.0045
M_MG, M_SI = 24.305, 28.085
AL_SCHEIL_K, AL_CE = 0.13, 12.6


# ======================================================================================================================
# Served field capture
# ======================================================================================================================

_CAPTURE_LOCK = threading.Lock()
_LOCAL = threading.local()


@contextlib.contextmanager
def capture_front_parent():
    """Record, in this thread only, the arguments the served solver hands to evaluate_solidification.

    The wrapper always calls the real function and returns its container unchanged; other threads pass straight
    through. Yields the list that receives one record per solve."""
    import lpbf_thermal_solver as solver
    original = solver.evaluate_solidification

    def passthrough(T_fn, **kwargs):
        slot = getattr(_LOCAL, "slot", None)
        if slot is not None:
            slot.append({"T_fn": T_fn, **kwargs})
        return original(T_fn, **kwargs)

    with _CAPTURE_LOCK:
        _LOCAL.slot = []
        solver.evaluate_solidification = passthrough
        try:
            yield _LOCAL.slot
        finally:
            solver.evaluate_solidification = original
            _LOCAL.slot = None


def served_solve(material: str, process: Mapping[str, float], heat_source: str,
                 overrides: Optional[Mapping[str, Any]] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """(served thermal result, captured front parent) of one full served solve."""
    from lpbf_thermal_solver import calculate_meltpool_physics
    with capture_front_parent() as slot:
        thermal = calculate_meltpool_physics(
            material, process["power_W"], process["speed_mm_s"], process["beamDiameter_um"], process["preheat_C"],
            process["layerThickness_um"], process["hatch_um"], prop_overrides=dict(overrides) if overrides else None,
            heat_source=heat_source, include_process_map=False)
    if len(slot) != 1:
        raise RuntimeError(f"expected one captured front parent, got {len(slot)}")
    return thermal, slot[0]


# ======================================================================================================================
# Rear-branch sampler (A5.2, A5.3)
# ======================================================================================================================

def _t(T_fn: Callable, x: float, y: float, z: float) -> float:
    value = T_fn(x, y, z)
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(value.reshape(-1)[0])


def _bisect(fn: Callable[[float], float], lo: float, hi: float, iterations: int = ROOT_ITERATIONS) -> float:
    """Root of fn on [lo, hi] with fn(lo) and fn(hi) of opposite sign (bracketed bisection)."""
    f_lo = fn(lo)
    for _ in range(iterations):
        mid = 0.5 * (lo + hi)
        if mid in (lo, hi):
            break
        f_mid = fn(mid)
        if (f_mid > 0) == (f_lo > 0):
            lo, f_lo = mid, f_mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def depth_root(T_fn: Callable, x: float, T_liq: float, z_hint: float) -> Optional[float]:
    """Liquidus depth z(x) on y = 0, or None when the surface at x is below the liquidus."""
    if _t(T_fn, x, 0.0, 0.0) < T_liq:
        return None
    hi = max(float(z_hint), 1e-6)
    for _ in range(40):
        if _t(T_fn, x, 0.0, hi) < T_liq:
            break
        hi *= 2.0
    else:
        return None
    return _bisect(lambda z: _t(T_fn, x, 0.0, z) - T_liq, 0.0, hi)


def gradient(T_fn: Callable, x: float, y: float, z: float, h: float, surface: bool) -> Tuple[float, float, float]:
    """Central differences in x and y; z central in the interior, one-sided over its own step at the surface."""
    gx = (_t(T_fn, x + h, y, z) - _t(T_fn, x - h, y, z)) / (2.0 * h)
    gy = (_t(T_fn, x, y + h, z) - _t(T_fn, x, y - h, z)) / (2.0 * h)
    if surface:
        gz = (_t(T_fn, x, y, z + h) - _t(T_fn, x, y, z)) / h
    else:
        gz = (_t(T_fn, x, y, z + h) - _t(T_fn, x, y, z - h)) / (2.0 * h)
    return gx, gy, gz


def kinematics(g: Sequence[float], v: float) -> Dict[str, float]:
    """Local Q-T outputs of one gradient: G, R, cooling, G/R and the normal toward hotter liquid.

    Raises ValueError('invalid-interface-sample') for a nonfinite or zero gradient or a melting-side sample."""
    gx, gy, gz = (float(c) for c in g)
    if not all(math.isfinite(c) for c in (gx, gy, gz)) or not (math.isfinite(v) and v > 0):
        raise ValueError("invalid-interface-sample")
    G = math.sqrt(gx * gx + gy * gy + gz * gz)
    if not G > 0:
        raise ValueError("invalid-interface-sample")
    if not gx > 0:
        raise ValueError("invalid-interface-sample")
    R = v * gx / G
    cooling = v * gx
    g_over_r = G * G / (v * gx)
    return {"G": G, "R": R, "cooling": cooling, "gOverR": g_over_r, "normal": (gx / G, gy / G, gz / G)}


def _observed_order(d: Sequence[float], noise: float) -> Optional[float]:
    e1, e2 = d[0] - d[1], d[1] - d[2]
    if not (abs(e2) > noise and abs(e1) > noise) or (e1 > 0) != (e2 > 0):
        return None
    return math.log2(abs(e1) / abs(e2))


def _component_state(d: Sequence[float], noise: float, band: Tuple[float, float]) -> Tuple[str, Optional[float]]:
    if d[0] == d[1] == d[2] == 0.0:
        return "symmetry-zero", None
    order = _observed_order(d, noise)
    if order is None:
        return "unresolved", None
    return ("resolved" if band[0] <= order <= band[1] else "unresolved"), order


def weighted_median(values: Sequence[float], weights: Sequence[float]) -> float:
    """Midpoint of the weighted-median set (A5.2); deterministic ties."""
    pairs = sorted(zip(values, weights, range(len(values))))
    total = sum(weights)
    half = 0.5 * total
    cumulative = 0.0
    for index, (value, weight, _) in enumerate(pairs):
        cumulative += weight
        if abs(cumulative - half) <= 1e-14 * total and index + 1 < len(pairs):
            return 0.5 * (value + pairs[index + 1][0])
        if cumulative > half:
            return value
    return pairs[-1][0]


def weighted_percentile(values: Sequence[float], weights: Sequence[float], q: float) -> float:
    pairs = sorted(zip(values, weights, range(len(values))))
    total = sum(weights)
    cumulative = 0.0
    for value, weight, _ in pairs:
        cumulative += weight
        if cumulative >= q * total:
            return value
    return pairs[-1][0]


def summarize(values: Sequence[float], weights: Sequence[float]) -> Dict[str, float]:
    """Weighted median plus spatial variability (never an uncertainty or coverage claim)."""
    return {"median": weighted_median(values, weights), "p10": weighted_percentile(values, weights, 0.10),
            "p90": weighted_percentile(values, weights, 0.90), "min": min(values), "max": max(values)}


def sample_front(T_fn: Callable, T_liq: float, v: float, x_rear_hint: float, depth_hint: float, *,
                 count: int = NODE_COUNT, arm_id: str = "nominal", refine: bool = True) -> Dict[str, Any]:
    """Local tuples on the rear solidifying centre-plane liquidus branch of one field (A5.2).

    Returns {"status": "sampled" | "no-crossing", "samples": [...], "support": {...}, "branch": {...}}."""
    x_rear_hint = max(4e-6, abs(float(x_rear_hint)))
    # Hottest surface point on the axis (coarse scan, then the branch is bracketed on both sides of it).
    xs = [x_rear_hint * (0.25 - 1.25 * i / 64.0) for i in range(65)]
    temps = [_t(T_fn, x, 0.0, 0.0) for x in xs]
    x_hot = xs[max(range(len(xs)), key=temps.__getitem__)]
    if _t(T_fn, x_hot, 0.0, 0.0) < T_liq:
        return {"status": "no-crossing", "samples": [], "support": {"attempted": 0}, "branch": None}

    def crossing(direction: float) -> Optional[float]:
        step = x_rear_hint
        for _ in range(40):
            far = x_hot + direction * step
            if _t(T_fn, far, 0.0, 0.0) < T_liq:
                return _bisect(lambda x: _t(T_fn, x, 0.0, 0.0) - T_liq, x_hot, far)
            step *= 2.0
        return None

    x_tail, x_front = crossing(-1.0), crossing(1.0)
    if x_tail is None or x_front is None:
        return {"status": "no-crossing", "samples": [], "support": {"attempted": 0}, "branch": None}
    depth_cache: Dict[float, Optional[float]] = {}

    def z_of(x: float) -> Optional[float]:
        if x not in depth_cache:
            depth_cache[x] = depth_root(T_fn, x, T_liq, depth_hint)
        return depth_cache[x]

    def gx_on_branch(x: float) -> float:
        z = z_of(x)
        if z is None:
            return 1.0  # outside the pool: counts as the solidifying side of the bracket
        h = max(1e-9, STEP_FRACTION_OF_DEPTH * max(z, 1e-6))
        return gradient(T_fn, x, 0.0, z, h, z < h)[0]

    lo_x, hi_x = x_tail + 1e-12 * abs(x_tail), x_front - 1e-12 * abs(x_front)
    if not (gx_on_branch(lo_x) > 0 > gx_on_branch(hi_x)):
        return {"status": "no-crossing", "samples": [], "support": {"attempted": 0}, "branch": None}
    x_bottom = _bisect(gx_on_branch, hi_x, lo_x, 80)
    z_bottom = z_of(x_bottom) or 0.0
    h0 = max(1e-9, STEP_FRACTION_OF_DEPTH * max(z_bottom, 1e-6))
    steps = (h0, h0 / 2.0, h0 / 4.0) if refine else (h0 / 4.0,)
    edges = []
    for i in range(count + 1):
        x = x_bottom + (x_tail - x_bottom) * i / count
        z = 0.0 if i == count else z_of(x)
        edges.append((x, z))
    samples: List[Dict[str, Any]] = []
    counts = {"attempted": count, "rootFound": 0, "solidifying": 0, "numericallyEligible": 0,
              "refusedByReason": {}}
    T_scale = max(abs(T_liq), 1.0)
    for i in range(count):
        a, b = edges[i], edges[i + 1]
        sample_id = f"{arm_id}:n{count}:{i}"
        x = x_bottom + (x_tail - x_bottom) * (i + 0.5) / count
        z = z_of(x)
        if z is None or a[1] is None or b[1] is None:
            counts["refusedByReason"]["invalid-interface-sample"] = counts["refusedByReason"].get(
                "invalid-interface-sample", 0) + 1
            continue
        counts["rootFound"] += 1
        weight = math.hypot(b[0] - a[0], b[1] - a[1])
        surface = z < h0
        grads = [gradient(T_fn, x, 0.0, z, h, surface) for h in steps]
        gx, gy, gz = grads[-1]
        record: Dict[str, Any] = {
            "sampleId": sample_id, "armId": arm_id, "position_m": {"x": x, "y": 0.0, "z": z},
            "timeConvention": "steady-beam-frame", "weight_m": weight,
            "gradient_K_m": {"gx": gx, "gy": gy, "gz": gz},
            "root": {"residual_K": _t(T_fn, x, 0.0, z) - T_liq, "method": "bracketed-bisection",
                     "iterations": ROOT_ITERATIONS},
            "stencil": {"steps_m": list(steps), "boundaryMode": "one-sided-surface" if surface else "central"},
        }
        try:
            kin = kinematics((gx, gy, gz), v)
        except ValueError as exc:
            record.update(valid=False, refusal=str(exc))
            counts["refusedByReason"][str(exc)] = counts["refusedByReason"].get(str(exc), 0) + 1
            samples.append(record)
            continue
        counts["solidifying"] += 1
        # Local identities on the same tuple (A5.5): a failed arithmetic identity is a solver error.
        if (abs(kin["G"] * kin["R"] - kin["cooling"]) > IDENTITY_RTOL * kin["cooling"]
                or abs(kin["G"] / kin["R"] - kin["gOverR"]) > IDENTITY_RTOL * kin["gOverR"]):
            record.update(valid=False, refusal="solver-error")
            counts["refusedByReason"]["solver-error"] = counts["refusedByReason"].get("solver-error", 0) + 1
            samples.append(record)
            continue
        numerics: Dict[str, Any] = {}
        if refine:
            noise = 64.0 * 2.220446049250313e-16 * T_scale / steps[-1]
            band_x, band_z = ORDER_BAND_INTERIOR, ORDER_BAND_SURFACE if surface else ORDER_BAND_INTERIOR
            for name, index, band in (("gx", 0, band_x), ("gy", 1, ORDER_BAND_INTERIOR), ("gz", 2, band_z)):
                state, order = _component_state([g[index] for g in grads], noise, band)
                numerics[name] = {"state": state, "observedOrder": order,
                                  "estimates": [g[index] for g in grads]}
        resolved = (not refine) or all(item["state"] in ("resolved", "symmetry-zero") for item in numerics.values())
        counts["numericallyEligible"] += 1
        record.update(valid=True, refusal=None, G_K_m=kin["G"], R_m_s=kin["R"], coolingRate_K_s=kin["cooling"],
                      gOverR_K_s_m2=kin["gOverR"], normal=list(kin["normal"]), numerics=numerics,
                      numericallyResolved=resolved)
        samples.append(record)
    return {"status": "sampled", "samples": samples, "support": counts,
            "branch": {"xBottom_m": x_bottom, "zBottom_m": z_bottom, "xTail_m": x_tail, "xFront_m": x_front,
                       "nodes": count, "weights": "chord-length-of-liquidus-cell-edges",
                       "interval": "open u in (0, 1), midpoint nodes", "plane": "y = 0"}}


def valid_samples(front: Mapping[str, Any]) -> List[Dict[str, Any]]:
    return [s for s in front.get("samples", []) if s.get("valid")]


def thermal_summary(front: Mapping[str, Any]) -> Optional[Dict[str, Dict[str, float]]]:
    """Weighted medians of the local Q-T outputs, or None below the three-sample branch support."""
    rows = valid_samples(front)
    if len(rows) < MIN_BRANCH_SAMPLES:
        return None
    weights = [s["weight_m"] for s in rows]
    return {name: summarize([s[key] for s in rows], weights) for name, key in (
        ("thermalGradient", "G_K_m"), ("normalSpeed", "R_m_s"), ("coolingRate", "coolingRate_K_s"),
        ("gOverR", "gOverR_K_s_m2"))}


# ======================================================================================================================
# Local spacing, morphology and phase models
# ======================================================================================================================

def freezing_range(p: Mapping[str, float]) -> float:
    return p["m"] * p["c"] * (1.0 - p["k"]) / p["k"]


def capillary_cutoff(p: Mapping[str, float], G: float, R: float) -> Optional[float]:
    """A7.1 screening bound of the named binary proxy, or None where the binary dendrite route is refused."""
    P = freezing_range(p)
    drive = P * R / p["d"] - G
    if drive <= 0 or R >= P * p["d"] / (p["k"] * p["gamma"]):
        return None
    return 2.0 * math.pi * math.sqrt(p["gamma"] / drive)


def raw_spacing(alloy: str, kind: str, G: float, R: float, al_wt: float = 6.0) -> Any:
    """Source-law algebra in metres (Ni PDAS: {hunt, kurzFisher}); None for a refused law. Never a value by itself."""
    law = SPACING[alloy][kind]
    q = G * R
    if alloy in ("in718", "in625") and kind == "pdas":
        if not (G * NI_DL / NI_DT0 < R < NI_VAB):
            return None
        x = G ** -0.5 * R ** -0.25
        return {"hunt": NI_HUNT_A * x, "kurzFisher": NI_KF_A * x}
    if alloy == "ti6al4v":
        a = law["intercept"] - law["slope"] * al_wt
        if not a > 0:
            return None
        return a * q ** -law["n"] * 1e-6
    base = 1000.0 * R if law["uses"] == "R_mm_s" else q
    return law["a"] * base ** -law["n"] * 1e-6


def gated_spacing(alloy: str, kind: str, G: float, R: float) -> Tuple[Any, Optional[str], Any]:
    """(value or None, refusal tag, raw diagnostic) after the alloy's own capillary screening gate (A7.1)."""
    raw = raw_spacing(alloy, kind, G, R)
    if raw is None:
        return None, "outside-dendrite-range", None
    cut = capillary_cutoff(PROXIES[alloy], G, R)
    if cut is None:
        return None, "planar-or-absolute-stability", raw
    values = raw.values() if isinstance(raw, dict) else [raw]
    if not all(v >= cut for v in values):
        return None, "below-capillary-limit", raw
    return raw, None, raw


def morphology(alloy: str, G: float, R: float, nuclei: Optional[float] = None,
               activation: Optional[float] = None) -> Dict[str, Any]:
    """chi, Hunt envelope fraction and Durga class at one tuple (A6.4, A7.4, A7.5)."""
    p = PROXIES[alloy]
    n0 = p["nuclei"] if nuclei is None else nuclei
    dtn = p["activation"] if activation is None else activation
    Q = p["m"] * p["c"] * (1.0 - p["k"])
    P = Q / p["k"]
    chi = P * R / (p["d"] * G)
    tip = math.sqrt(8.0 * Q * p["gamma"] * R / p["d"])
    radius_tip = 4.0 * p["gamma"] / tip
    peclet = R * radius_tip / (2.0 * p["d"])
    out: Dict[str, Any] = {"chi": chi, "tip_K": tip, "tipRadius_m": radius_tip, "peclet": peclet, "fraction": None,
                           "class": None, "refusal": None}
    eutectic = None if p["ce"] is None else p["m"] * (p["ce"] - p["c"])
    if eutectic is not None and (eutectic <= 0 or tip >= eutectic):
        out["refusal"] = "tip-reaches-eutectic"
    elif chi <= 1 or tip > P or R >= P * p["d"] / (p["k"] * p["gamma"]):
        out["refusal"] = "outside-dendritic-growth-domain"
    if out["refusal"] is None:
        radius = 0.0 if tip <= dtn else tip / (3.0 * G) * (1.0 - (dtn / tip) ** 3)
        extended = 4.0 * math.pi / 3.0 * n0 * radius ** 3
        fraction = -math.expm1(-extended)
        out.update(fraction=fraction, extended=extended, envelopeRadius_m=radius,
                   **{"class": cet_class(fraction)})
    return out


def cet_class(fraction: float) -> str:
    """Durga convention on the true envelope fraction (never the extended-fraction 0.0066 / 0.66)."""
    return "columnar" if fraction <= 0.0049 else "equiaxed" if fraction >= 0.49 else "mixed"


def km_path(T_fn: Callable, sample: Mapping[str, Any], v: float, preheat_C: float,
            ratio: float = KM_PATH_RATIO) -> Dict[str, Any]:
    """Single-pass material-point path T(x0 - v t, 0, z0) from the sample's solidification to the first downward
    crossing of preheat + 25 K, with the A7.6 gates. Raises ValueError with a descriptive tag on refusal."""
    x0, z0 = sample["position_m"]["x"], sample["position_m"]["z"]
    T_eval = preheat_C + KM_OFFSET_K
    nodes = [(0.0, _t(T_fn, x0, 0.0, z0))]
    if nodes[0][1] < KM_TRANSUS_C:
        raise ValueError("missing-beta-initialization")
    s = KM_PATH_FIRST_STEP_M
    crossing = None
    while s <= KM_PATH_MAX_M:
        temperature = _t(T_fn, x0 - s, 0.0, z0)
        nodes.append((s / v, temperature))
        (t0, a), (t1, b) = nodes[-2], nodes[-1]
        if b > a:
            raise ValueError("reheating-needs-competing-kinetics")
        if b < KM_TRANSUS_C and (a - b) / (t1 - t0) < KM_RATE_K_S:
            raise ValueError("slow-cooling-needs-competing-kinetics")
        if a >= T_eval > b:
            crossing = len(nodes) - 2
            break
        s *= ratio
    if crossing is None:
        raise ValueError("missing-evaluation-crossing")
    (t0, a), (t1, b) = nodes[crossing], nodes[crossing + 1]
    t_linear = t0 + (t1 - t0) * (a - T_eval) / (a - b)
    t_refined = _bisect(lambda t: _t(T_fn, x0 - v * t, 0.0, z0) - T_eval, t0, t1, 200)
    return {"nodes": nodes, "bracket": (crossing, crossing + 1), "timeLinear_s": t_linear, "time_s": t_refined,
            "evaluation_C": T_eval}


def km_fraction(T_eval_C: float, beta0: float = 1.0) -> float:
    return beta0 * -math.expm1(-KM_COEFFICIENT * max(0.0, KM_MS_C - T_eval_C))


def al_equilibrium(c_si: float = AL_SI, c_mg: float = AL_MG) -> Dict[str, float]:
    bound = c_mg * M_SI / (2.0 * M_MG)
    if bound > c_si:
        raise ValueError("silicon-deficit-needs-different-phase-set")
    f_mg2si = c_mg + bound
    f_si = c_si - bound
    return {"alphaAl": 1.0 - f_si - f_mg2si, "Si": f_si, "Mg2Si": f_mg2si}


def al_scheil(c_wt: float = 100.0 * AL_SI, k: float = AL_SCHEIL_K, ce: float = AL_CE) -> Dict[str, float]:
    if c_wt >= ce:
        raise ValueError("hypereutectic-needs-primary-silicon-model")
    residual = (ce / c_wt) ** (1.0 / (k - 1.0))
    return {"primaryAlphaAl": 1.0 - residual, "eutecticConstituent": residual}


# ======================================================================================================================
# Tier, validity and envelope assembly
# ======================================================================================================================

def estimate_tier(has_value: bool, warning_codes: Iterable[str], band_complete: bool,
                  numerically_resolved: bool) -> str:
    """A7 tier rule: no value -> no-value; any capping warning in the closure -> Physics estimate; Estimated only
    with a complete matched executed sweep on a numerically resolved, wholly in-domain closure."""
    if not has_value:
        return "no-value"
    if set(warning_codes) & set(qe.TIER_CAPPING_WARNING_CODES):
        return "Physics estimate"
    return "Estimated" if band_complete and numerically_resolved else "Physics estimate"


def _validity(definition: str, tier: str, warnings: Sequence[Mapping[str, str]], *, explanation: str = "",
              band: Optional[Mapping[str, Any]] = None, sensitivity: Optional[Mapping[str, Any]] = None,
              extra: Optional[Mapping[str, Any]] = None, no_value_text: Optional[str] = None) -> Dict[str, Any]:
    has = tier != "no-value"
    out = {
        "estimateTier": tier,
        "tierLabel": qe.ESTIMATE_TIER_LABELS[tier],
        "displaySignificantDigits": qe.DISPLAY_SIGNIFICANT_DIGITS[definition] if has else None,
        "domainWarnings": [dict(item) for item in warnings],
        "estimateBand": dict(band) if (has and tier == "Estimated" and band is not None) else None,
        "inputSensitivity": dict(sensitivity) if (has and tier == "Physics estimate" and sensitivity) else None,
        "uncertaintyStatement": UNKNOWN if tier == "Physics estimate" else None,
        "explanation": explanation if has else None,
        "noValueText": None if has else (no_value_text or NO_FRONT_TEXT),
    }
    if definition in ("equiaxed-envelope-fraction", "cet-class") and has:
        out["nucleationScenarioNote"] = qe.NUCLEATION_SCENARIO_NOTE
    out.update(extra or {})
    return out


def _warn(code: str, detail: str) -> Dict[str, str]:
    if code not in qe.VALUE_WARNING_CODES:
        raise qe.EnvelopeError(f"unknown value warning {code!r}")
    return {"code": code, "detail": detail}


def _dedupe(warnings: Iterable[Mapping[str, str]]) -> List[Dict[str, str]]:
    seen, out = set(), []
    for item in warnings:
        key = (item["code"], item["detail"])
        if key not in seen:
            seen.add(key)
            out.append(dict(item))
    return out


def _digest(value: Any) -> str:
    def encode(item):
        if isinstance(item, bool) or item is None or isinstance(item, str):
            return item
        if isinstance(item, (int, float)):
            return float(item).hex()
        if isinstance(item, (list, tuple)):
            return [encode(v) for v in item]
        if isinstance(item, dict):
            return {str(k): encode(v) for k, v in sorted(item.items())}
        return repr(item)
    return hashlib.sha256(json.dumps(encode(value), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _record(kind: str, source_id: str, *, status: str, locator: Optional[str] = None, scope: str = "",
            declaration: Optional[str] = None, depends_on: Sequence[str] = (), evidence: Optional[str] = None,
            default_value: Any = None, phase: Optional[str] = None) -> Dict[str, Any]:
    return qe.input_record(kind, source_id, status=status, source_locator=locator, declaration_locator=declaration,
                           scope=scope, depends_on=depends_on, source_evidence_kind=evidence,
                           default_value=default_value, phase=phase, label=kind)


class Builder:
    """Accumulates input records and quantities of one v2 container, with the inherited-warning bookkeeping."""

    def __init__(self) -> None:
        self.inputs: Dict[str, Any] = {}
        self.quantities: Dict[str, Any] = {}
        self.warnings: Dict[str, List[Dict[str, str]]] = {}  # input name -> warnings its record implies

    def add_input(self, name: str, record: Dict[str, Any], warnings: Sequence[Mapping[str, str]] = ()) -> None:
        self.inputs[name] = record
        self.warnings[name] = [dict(item) for item in warnings]

    def closure_warnings(self, depends_on: Sequence[str], seen: frozenset = frozenset()) -> List[Dict[str, str]]:
        out: List[Dict[str, str]] = []
        for name in depends_on:
            if name in seen:
                continue
            if name in self.inputs:
                record = self.inputs[name]
                out += self.warnings.get(name, [])
                if record["kind"] == "alloyTransfer" and not any(w["code"] == "alloy-family-transfer"
                                                                 for w in self.warnings.get(name, [])):
                    out.append(_warn("alloy-family-transfer", f"{name}: {record['scope'] or record['sourceId']}"))
                if record["status"] in ("extrapolated", "outOfRange") and not any(
                        w["code"] == "domain-extrapolation" for w in self.warnings.get(name, [])):
                    out.append(_warn("domain-extrapolation", f"{name}: {record['scope'] or record['sourceId']}"))
                out += self.closure_warnings(record["dependsOn"], seen | {name})
            elif name in self.quantities:
                q = self.quantities[name]
                out += (q.get("validity") or {}).get("domainWarnings", [])
                out += self.closure_warnings(q["dependsOn"], seen | {name})
        return _dedupe(out)

    def value(self, name: str, definition: str, value: Any, *, depends_on: Sequence[str], sources: Sequence[Mapping],
              own_warnings: Sequence[Mapping[str, str]] = (), explanation: str, construction: str,
              numerical: Optional[Mapping[str, Any]] = None, band: Optional[Mapping[str, Any]] = None,
              sensitivity: Optional[Mapping[str, Any]] = None, numerically_resolved: bool = True,
              extra_validity: Optional[Mapping[str, Any]] = None, fraction_basis: Optional[str] = None,
              assumptions: Sequence[str] = (), extra: Optional[Mapping[str, Any]] = None,
              input_identity: Optional[str] = None) -> Dict[str, Any]:
        warnings = _dedupe(list(self.closure_warnings(depends_on)) + list(own_warnings))
        tier = estimate_tier(True, [w["code"] for w in warnings], band is not None, numerically_resolved)
        kind = qe.V2_QUANTITY_DEFINITIONS[definition]["valueKind"]
        uncertainty_kind = ("model-alternatives" if kind == "alternatives"
                            else "parameter-sensitivity" if tier == "Estimated" else "not-quantified")
        if tier == "Estimated":
            text = explanation
        else:
            text = explanation
        q = qe.quantity(
            definition, value, inputs=self.inputs, depends_on=depends_on, sources=sources, model_identity=MODEL_ID,
            uncertainty={"kind": uncertainty_kind, "construction": construction}, numerical=numerical,
            fraction_basis=fraction_basis, assumptions=assumptions,
            validity=_validity(definition, tier, warnings, explanation=text, band=band, sensitivity=sensitivity,
                               extra=extra_validity),
            quantities=self.quantities, extra=extra, input_identity=input_identity)
        self.quantities[name] = q
        return q

    def no_value(self, name: str, definition: str, code: str, *, parent: str, depends_on: Sequence[str],
                 text: str, extra_reasons: Sequence[Mapping[str, Any]] = (), params: Optional[Mapping] = None,
                 extra_validity: Optional[Mapping[str, Any]] = None,
                 numerical: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        reasons = [qe.reason(code, params or {}, qe.reason_parent(parent, self.inputs, self.quantities))]
        reasons += [dict(item) for item in extra_reasons]
        for dep in depends_on:
            sibling = self.quantities.get(dep)
            if isinstance(sibling, dict) and sibling["value"] is None and dep != parent:
                reasons.append(qe.reason("parent-unavailable", {}, {"input": dep, "kind": "derived"}))
        q = qe.unavailable(definition, reasons, depends_on=depends_on, numerical=numerical,
                           validity=_validity(definition, "no-value", [], no_value_text=text, extra=extra_validity),
                           model_identity=MODEL_ID)
        self.quantities[name] = q
        return q


def _fmt(value: float, digits: int = 2) -> str:
    if value == 0:
        return "0"
    return f"{value:.{digits}g}"


def _range_object(nominal: float, arms: Mapping[str, float], unit: str, input_ranges: List[Dict[str, Any]],
                  unknown: Sequence[str]) -> Dict[str, Any]:
    values = [nominal, *arms.values()]
    return {"lower": min(values), "upper": max(values), "unit": unit, "construction": "ofat",
            "inputRanges": input_ranges, "armIds": ["nominal", *arms.keys()], "unknownComponents": list(unknown)}


# ======================================================================================================================
# Request handling
# ======================================================================================================================

_PROCESS_KEYS = ("power_W", "speed_mm_s", "beamDiameter_um", "preheat_C", "layerThickness_um", "hatch_um")
HEAT_SOURCES = ("rosenthal", "eagar-tsai", "goldak")


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _refusal(code: str, detail: str, request: Any = None) -> Dict[str, Any]:
    """Channel-level refusal: a v2 container whose quantities are all null with the coded reason."""
    b = Builder()
    b.add_input("estimateRequest", _record("declaredAssumption", "request:solidification-estimates",
                                           status="outOfRange", declaration="python/lpbf_solidification_estimates.py",
                                           scope=detail))
    for name, definition in (("thermalGradient", "liquidus-front-thermal-gradient"),
                             ("normalSpeed", "liquidus-front-normal-speed"),
                             ("coolingRate", "liquidus-front-cooling-rate"), ("gOverR", "liquidus-front-g-over-r")):
        b.no_value(name, definition, code, parent="estimateRequest", depends_on=("estimateRequest",),
                   text=detail)
    out = qe.container(b.quantities, input_provenance=b.inputs, schema=qe.ENVELOPE_SCHEMA_V2)
    out.update(schema=CHANNEL_SCHEMA, channelId=CHANNEL_ID, modelId=MODEL_ID, status="unavailable",
               alloyId=None, refusal={"code": code, "detail": detail})
    return out


def parse_request(payload: Any) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """(parsed request, None) or (None, refusal container). No default alloy, process value or surrogate."""
    from solidification_front import canonical_alloy_id
    if not isinstance(payload, dict) or not isinstance(payload.get("params"), dict):
        return None, _refusal("nonphysical-input", "The request needs a params object with the alloy and process.")
    params = payload["params"]
    options = payload.get("options") if isinstance(payload.get("options"), dict) else {}
    alloy = canonical_alloy_id(params.get("materialName"))
    if alloy is None:
        return None, _refusal("unknown-alloy-alias", "Choose one of Ti-6Al-4V, AlSi10Mg, Inconel 718, 316L or "
                                                     "Inconel 625; no surrogate alloy is substituted.")
    process: Dict[str, float] = {}
    for key in _PROCESS_KEYS:
        value = params.get(key)
        if not _finite(value):
            return None, _refusal("nonphysical-input", f"Provide a finite {key}; no default is used.")
        process[key] = float(value)
    for key in ("power_W", "speed_mm_s", "beamDiameter_um", "layerThickness_um", "hatch_um"):
        if process[key] <= 0:
            return None, _refusal("nonphysical-input", f"{key} must be positive.")
    heat_source = params.get("heatSource", "rosenthal")
    if heat_source not in HEAT_SOURCES:
        return None, _refusal("nonphysical-input", f"heatSource must be one of {', '.join(HEAT_SOURCES)}.")
    for key in ("inputSensitivity", "conductionSurrogate"):
        if key in options and not isinstance(options[key], bool):
            return None, _refusal("nonphysical-input", f"options.{key} must be true or false.")
    from four_alloy_materials import thermal_props
    from lpbf_thermal_solver import SECONDARY_THERMOPHYSICAL_DB
    material = MATERIAL_NAMES[alloy]
    props = thermal_props(material) or SECONDARY_THERMOPHYSICAL_DB.get(material)
    if not (process["preheat_C"] > -KELVIN and process["preheat_C"] < props["liquidus_C"]):
        return None, _refusal("nonphysical-input", "The preheat must be above absolute zero and below the liquidus.")
    return {"alloy": alloy, "material": material, "process": process, "heatSource": heat_source,
            "inputSensitivity": bool(options.get("inputSensitivity", False)),
            # Default ON (maintainer decision 2026-10-16 on the Astra consult): when the Fabbro keyhole leg controls the
            # served geometry, the conduction-only rear front is shown as a labelled Tier 2 surrogate scenario unless the
            # request turns it off. It never becomes a computed keyhole front.
            "conductionSurrogate": bool(options.get("conductionSurrogate", True)),
            "surrogateSelection": "requested" if "conductionSurrogate" in options else "default",
            "props": props}, None


def _thermal_inputs(b: Builder, request: Mapping[str, Any], thermal: Mapping[str, Any],
                    kernel: Tuple[float, float, float, str]) -> List[str]:
    """Input records of the four thermal parents plus the process echoes; returns the front's determining list."""
    from four_alloy_materials import absorptivity_authority, melt_point_properties, PROPERTY_LEDGER
    alloy, material = request["alloy"], request["material"]
    process = thermal.get("processParameters") or {}
    served = (thermal.get("solidificationKinetics") or {}).get("inputProvenance", {}).get("liquidus_K")
    if not isinstance(served, dict):
        raise RuntimeError("the served front container carries no liquidus input record")
    b.add_input("liquidus_K", copy.deepcopy(served))
    k_th, cp, rho_k, convention = kernel
    if convention == "kernel-ledger-kirchhoff":
        ledger = PROPERTY_LEDGER[alloy]["text"] if alloy in PROPERTY_LEDGER else {}
        locator = ("Gan 2021 SI Table 1, PDF p.20 (fits of Mills data), Kirchhoff mean" if alloy == "ti6al4v" else
                   "Yang 2018 Fig. 5 and Fig. 1; Akwaboa 2023 Fig. 2f, Table 3; Fetni 2024 Fig. 4a; Kirchhoff mean")
        scope_k = ("Kirchhoff mean of the sourced solid k(T) from preheat to liquidus held constant over the field; "
                   "liquid and high-temperature state transfer")
        scope_cp = scope_k.replace("k(T)", "cp(T)")
        del ledger
    else:
        entry = melt_point_properties(material)
        locator = f"{entry['source']}: {entry['locator']}"
        scope_k = "melting-point k held constant over the whole field (solid and liquid state transfer)"
        scope_cp = "melting-point cp held constant over the whole field (solid and liquid state transfer)"
    b.add_input("thermalConductivity", _record("modelConvention", f"kernel-k:{alloy}:{float(k_th).hex()}",
                                               status="extrapolated", locator=locator, scope=scope_k,
                                               default_value=k_th, phase="solid-liquid-mean"))
    b.add_input("specificHeat", _record("modelConvention", f"kernel-cp:{alloy}:{float(cp).hex()}",
                                        status="extrapolated", locator=locator, scope=scope_cp, default_value=cp,
                                        phase="solid-liquid-mean"))
    rho_source, rho_locator = DENSITY_SOURCES[alloy]
    if float(rho_k).hex() == float(rho_source).hex():
        b.add_input("density", _record("modelConvention", f"density:{alloy}:{float(rho_k).hex()}",
                                       status="extrapolated", locator=rho_locator,
                                       scope="nominal ambient density held constant over the high-temperature field",
                                       default_value=rho_k))
    else:
        b.add_input("density", _record("declaredAssumption", f"density:{alloy}:{float(rho_k).hex()}",
                                       status="extrapolated", declaration="python/four_alloy_materials.py",
                                       scope="kernel density without a located source", default_value=rho_k))
    entry = absorptivity_authority(material)
    eta = float(process.get("conductionAbsorptivity", float("nan")))
    if entry is not None and not entry["unsourced"] and abs(eta - float(entry["value"])) <= 1e-12:
        b.add_input("absorptivity", _record(
            "sourceDefault", f"absorptivity:{alloy}:{eta.hex()}", status="extrapolated",
            locator=f"{entry['source']}: {entry['locator']}",
            scope=(f"{entry['basis']} at {entry['wavelength_nm']:g} nm applied to a powder-bed track; "
                   "optical surface transfer"), default_value=eta))
    else:
        b.add_input("absorptivity", _record("declaredAssumption", f"absorptivity:{alloy}:{eta.hex()}",
                                            status="extrapolated", declaration="python/four_alloy_materials.py",
                                            scope="absorptivity without a located source for this request",
                                            default_value=eta))
    for name in ("power_W", "speed_mm_s", "beamDiameter_um", "preheat_C", "heatSource"):
        b.add_input(name, qe.process_input_record(name))
    return ["liquidus_K", "thermalConductivity", "specificHeat", "density", "absorptivity", "power_W",
            "speed_mm_s", "beamDiameter_um", "preheat_C", "heatSource"]


def _sensitivity_arms(request: Mapping[str, Any], kernel: Tuple[float, float, float, str],
                      eta: float, keyhole_ok: bool) -> Dict[str, Any]:
    """A7 OFAT: eleven full served solves (nominal outside), one parent at a time, with recomputed branches."""
    props = request["props"]
    k_th, cp, rho_k, _ = kernel
    TL, TS = float(props["liquidus_C"]), float(props["solidus_C"])
    quarter = 0.25 * (TL - TS)
    plan = {
        "thermalConductivity": ("W/(m K)", k_th, (0.8 * k_th, 1.2 * k_th)),
        "specificHeat": ("J/(kg K)", cp, (0.8 * cp, 1.2 * cp)),
        "density": ("kg/m3", rho_k, (0.95 * rho_k, 1.05 * rho_k)),
        "absorptivity": ("1", eta, (0.5 * eta, min(1.0, 1.5 * eta))),
        "liquidus_K": ("K", TL + KELVIN, (TL - quarter + KELVIN, TL + quarter + KELVIN)),
    }
    arms: Dict[str, Any] = {}
    for name, (_, _, endpoints) in plan.items():
        for index, value in zip(("low", "high"), endpoints):
            arm_id = f"{name}:{index}"
            if name == "thermalConductivity":
                overrides = {"kernel_conductivity_W_mK": value, "kernel_specific_heat_J_kgK": cp,
                             "kernel_density_kg_m3": rho_k}
            elif name == "specificHeat":
                overrides = {"kernel_conductivity_W_mK": k_th, "kernel_specific_heat_J_kgK": value,
                             "kernel_density_kg_m3": rho_k}
            elif name == "density":
                overrides = {"kernel_conductivity_W_mK": k_th, "kernel_specific_heat_J_kgK": cp,
                             "kernel_density_kg_m3": value}
            elif name == "absorptivity":
                overrides = {"absorptivity_IR": value}
            else:
                overrides = {"liquidus_C": value - KELVIN}
            try:
                _, parent = served_solve(request["material"], request["process"], request["heatSource"], overrides)
            except (ValueError, RuntimeError) as exc:
                arms[arm_id] = {"status": "failed", "detail": str(exc), "overrides": overrides}
                continue
            if parent["depth_from_keyhole_leg"] and not keyhole_ok:
                arms[arm_id] = {"status": "keyhole-field-inconsistent", "overrides": overrides}
                continue
            front = sample_front(parent["T_fn"], parent["T_liq"], parent["v_scan"], parent["x_rear"],
                                 parent["search_depth"], arm_id=arm_id, refine=False)
            summary = thermal_summary(front)
            arms[arm_id] = {"status": "computed" if summary else "insufficient-sample-support",
                            "overrides": overrides, "validSamples": len(valid_samples(front)),
                            "summary": {key: value["median"] for key, value in summary.items()} if summary else None}
    ranges = [{"name": name, "unit": unit, "nominal": nominal, "lower": lo, "upper": hi}
              for name, (unit, nominal, (lo, hi)) in plan.items()]
    complete = all(arm["status"] == "computed" for arm in arms.values()) and len(arms) == 10
    return {"arms": arms, "inputRanges": ranges, "complete": complete,
            "design": "one-factor-at-a-time, eleven full-field arms (nominal plus low and high per parent)",
            "declaredScenario": ("k and cp +/-20 percent, density +/-5 percent, absorptivity 0.5 to min(1, 1.5) "
                                 "times nominal, liquidus +/- a quarter of the freezing interval (A7 2 and 3); "
                                 "declared screening scenarios, not measured uncertainties")}


class StaleParent(RuntimeError):
    """The captured thermal parent does not match the kernel the estimate would read."""


def front_state(request: Mapping[str, Any], thermal: Mapping[str, Any], parent: Mapping[str, Any], *,
                prop_overrides: Optional[Mapping[str, Any]] = None, support_resolutions: bool = True
                ) -> Dict[str, Any]:
    """The shared front parent of this channel and of its projections onto other served surfaces (SPEC engine
    estimates groups 6 and 8): identity-checked kernel, thermal input records, the rear-branch local tuples and the
    blocking state, all from one captured served solve. Raises StaleParent on an identity mismatch."""
    from lpbf_thermal_solver import resolve_conduction_kernel
    material = request["material"]
    props = dict(request["props"])
    if prop_overrides:
        props.update(prop_overrides)
    kernel = resolve_conduction_kernel(material, props, dict(prop_overrides) if prop_overrides else None,
                                       request["process"]["preheat_C"])[:4]
    process_echo = thermal["processParameters"]
    # Identity checks: the full-precision kernel the estimate reads is the one the served solve used.
    identity_checks = {
        "diffusivityMatchesServed": (kernel[0] / (kernel[2] * kernel[1])) == process_echo["effectiveDiffusivity_m2_s"],
        "liquidusMatchesCapture": float(parent["T_liq"]) == float(props["liquidus_C"]),
        "speedMatchesCapture": abs(parent["v_scan"] - request["process"]["speed_mm_s"] * 1e-3) == 0.0,
    }
    if not all(identity_checks.values()):
        raise StaleParent("The estimate's thermal parent does not match the served solve.")
    keyhole = bool(parent["depth_from_keyhole_leg"])
    surrogate = keyhole and request["conductionSurrogate"]
    b = Builder()
    front_inputs = _thermal_inputs(b, request, thermal, kernel)
    front = sample_front(parent["T_fn"], parent["T_liq"], parent["v_scan"], parent["x_rear"], parent["search_depth"])
    resolutions = {}
    for count in (SUPPORT_RESOLUTIONS[:-1] if support_resolutions else ()):
        coarse = sample_front(parent["T_fn"], parent["T_liq"], parent["v_scan"], parent["x_rear"],
                              parent["search_depth"], count=count, arm_id=f"nominal-n{count}", refine=False)
        summary = thermal_summary(coarse)
        resolutions[str(count)] = ({key: value["median"] for key, value in summary.items()} if summary else None)
    rows = valid_samples(front)
    sample_digest = _digest([{k: s[k] for k in ("sampleId", "position_m", "gradient_K_m", "weight_m")} for s in rows])
    b.add_input("frontSamples", _record(
        "derived", (f"front-samples-{SURROGATE_ID}:" if surrogate else "front-samples:") + f"{SAMPLER_ID}:{sample_digest}",
        status="inRange",
        locator=SRC_GHOSH_KINEMATICS["locator"], depends_on=front_inputs,
        evidence=qe.source_label(b.inputs, front_inputs)["sourceEvidenceKind"],
        scope=("local tuples of the rear solidifying centre-plane liquidus branch of the served conduction field "
               f"({thermal.get('heatSourceModel')})"
               + ("; conduction-field surrogate: the field does not include the keyhole cavity" if surrogate else ""))),
        warnings=[_warn("domain-extrapolation", KEYHOLE_SURROGATE_WARNING)] if surrogate else [])
    summary = thermal_summary(front)
    resolved = bool(rows) and all(s["numericallyResolved"] for s in rows)
    numerical = qe.numerical_status(
        "refinement-passed" if resolved else "unresolved",
        settings={"sampler": SAMPLER_ID, "nodes": NODE_COUNT, "supportResolutions": list(SUPPORT_RESOLUTIONS),
                  "stepFractionOfDepth": STEP_FRACTION_OF_DEPTH, "orderBandInterior": list(ORDER_BAND_INTERIOR),
                  "orderBandSurface": list(ORDER_BAND_SURFACE), "rootIterations": ROOT_ITERATIONS},
        residuals={"maxRootResidual_K": max((abs(s["root"]["residual_K"]) for s in rows), default=None)})
    support = dict(front["support"])
    support["retained"] = len(rows)
    support["resolutionMedians"] = resolutions
    blocked, local = None, []
    if front["status"] == "no-crossing":
        blocked = ("invalid-interface-sample", NO_CROSSING_TEXT)
    elif keyhole and not surrogate:
        blocked = ("keyhole-field-inconsistent", KEYHOLE_TEXT)
    elif summary is None:
        local = [{"sampleId": s["sampleId"], "position_m": s["position_m"], "G_K_m": s["G_K_m"], "R_m_s": s["R_m_s"],
                  "coolingRate_K_s": s["coolingRate_K_s"], "gOverR_K_s_m2": s["gOverR_K_s_m2"]} for s in rows]
        blocked = ("insufficient-sample-support", FEW_POINTS_TEXT if local else NO_FRONT_TEXT)
    return {"builder": b, "kernel": kernel, "identityChecks": identity_checks, "keyhole": keyhole,
            "surrogate": surrogate, "front": front, "rows": rows, "sampleDigest": sample_digest, "summary": summary,
            "resolved": resolved, "numerical": numerical, "support": support, "blocked": blocked, "local": local}


def surrogate_identity(request: Mapping[str, Any], thermal: Mapping[str, Any]) -> Dict[str, Any]:
    return {"id": SURROGATE_ID, "selection": request["surrogateSelection"], "field": thermal.get("heatSourceModel"),
            "observable": "conduction-only rear liquidus front",
            "notCoupledTo": "served melt-pool depth (Fabbro keyhole leg)", "warning": KEYHOLE_SURROGATE_WARNING}


def compute_solidification_estimates(payload: Any) -> Dict[str, Any]:
    """The SOL-C channel response for one request (see the module docstring)."""
    request, refusal = parse_request(payload)
    if refusal is not None:
        return refusal
    alloy, material = request["alloy"], request["material"]
    try:
        thermal, parent = served_solve(material, request["process"], request["heatSource"])
    except ValueError as exc:
        return _refusal("nonphysical-input", str(exc))
    try:
        state = front_state(request, thermal, parent)
    except StaleParent as exc:
        return _refusal("stale-parent-input", str(exc))
    process_echo = thermal["processParameters"]
    kernel, identity_checks, keyhole, surrogate = (state[k] for k in ("kernel", "identityChecks", "keyhole",
                                                                       "surrogate"))
    b, front, rows, sample_digest = state["builder"], state["front"], state["rows"], state["sampleDigest"]
    summary, resolved, numerical, support = state["summary"], state["resolved"], state["numerical"], state["support"]
    blocked, local = state["blocked"], state["local"]
    sensitivity = None
    if request["inputSensitivity"] and summary is not None and (not keyhole or surrogate):
        sensitivity = _sensitivity_arms(request, kernel, float(process_echo["conductionAbsorptivity"]),
                                        keyhole_ok=surrogate)
    alloy_name = ALLOY_NAMES[alloy]
    thermal_defs = (("thermalGradient", "liquidus-front-thermal-gradient", "G_K_m"),
                    ("normalSpeed", "liquidus-front-normal-speed", "R_m_s"),
                    ("coolingRate", "liquidus-front-cooling-rate", "coolingRate_K_s"),
                    ("gOverR", "liquidus-front-g-over-r", "gOverR_K_s_m2"))
    for name, definition, key in thermal_defs:
        if blocked is not None:
            extra = {"localPoints": local} if blocked[0] == "insufficient-sample-support" and local else None
            b.no_value(name, definition, blocked[0], parent="frontSamples", depends_on=("frontSamples",),
                       text=blocked[1], numerical=numerical, extra_validity=extra)
            continue
        nominal = summary[name]["median"]
        band = aux = None
        if sensitivity is not None and sensitivity["complete"]:
            arm_values = {arm_id: arm["summary"][name] for arm_id, arm in sensitivity["arms"].items()}
            unknown = ["model-error", "input-interactions", "alloy-transfer-error"]
            aux = _range_object(nominal, arm_values, qe.V2_QUANTITY_DEFINITIONS[definition]["unit"],
                                sensitivity["inputRanges"], unknown)
        provisional = _dedupe(list(b.closure_warnings(("frontSamples",))))
        tier = estimate_tier(True, [w["code"] for w in provisional], aux is not None, resolved)
        if tier == "Estimated":
            band, aux = aux, None
        label = QUANTITY_NAMES[name]
        if surrogate:
            text = SURROGATE_TEXT
        elif tier == "Estimated":
            ranges = "; ".join(f"{row['name']} {_fmt(row['lower'], 3)} to {_fmt(row['upper'], 3)} {row['unit']}"
                               for row in band["inputRanges"])
            text = (f"Estimated {label} for {alloy_name} from the selected conduction temperature-field model at the "
                    "rear solidifying liquidus slice. " + qe.TIER1_RANGE_SENTENCE.format(ranges=ranges))
        else:
            text = (f"{TIER2_LABEL} of {label} for {alloy_name} from the selected conduction temperature-field model "
                    f"at the identified solidifying locations. {UNKNOWN}")
        b.value(name, definition, nominal, depends_on=("frontSamples",),
                sources=[SRC_GHOSH_KINEMATICS, SRC_EAGAR_TSAI], explanation=text,
                construction=("Weighted median of local outputs on the rear centre-plane liquidus slice; spatial "
                              "variability, numerical refinement and any input sweep are reported separately. "
                              "Model, transfer and endpoint error are not quantified."),
                numerical=numerical, band=band, sensitivity=aux, numerically_resolved=resolved,
                extra_validity={"spatialVariability": {k: v for k, v in summary[name].items() if k != "median"},
                                "support": support, "parentScope": THERMAL_PARENT_SCOPE[alloy],
                                "inputSensitivityArms": ({arm_id: arm.get("summary", {}) and arm["summary"][name]
                                                          if arm.get("summary") else None
                                                          for arm_id, arm in sensitivity["arms"].items()}
                                                         if sensitivity else None)})
    front_ok = blocked is None
    _spacing_quantities(b, alloy, rows, front_ok, blocked)
    _morphology_quantities(b, alloy, rows, front_ok, blocked)
    _phase_quantities(b, alloy, rows, front_ok, blocked, parent, request)
    statuses = [q["status"] for q in b.quantities.values()]
    out = qe.container(b.quantities, input_provenance=b.inputs, schema=qe.ENVELOPE_SCHEMA_V2,
                       default=not surrogate)
    context_text, context_locator = PHASE_CONTEXT[alloy]
    out.update({
        "schema": CHANNEL_SCHEMA, "channelId": CHANNEL_ID, "modelId": MODEL_ID,
        "status": "computed" if all(s == "computed" for s in statuses) else
                  "partial" if any(s == "computed" for s in statuses) else "unavailable",
        "alloyId": alloy, "materialName": material, "heatSourceModel": thermal.get("heatSourceModel"),
        "request": {"process": dict(request["process"]), "heatSource": request["heatSource"]},
        "options": {"inputSensitivity": request["inputSensitivity"],
                    "conductionSurrogate": request["conductionSurrogate"]},
        "surrogate": "conduction-field" if surrogate else None,
        # Distinct surrogate identity: default selection does not change the model's status. "default" above keeps its
        # contract meaning (false: not the default physical arm of the served field).
        "surrogateIdentity": surrogate_identity(request, thermal) if surrogate else None,
        "thermalParent": {
            "thermalModelId": thermal.get("modelId"),
            "servedFrontModelId": (thermal.get("solidificationKinetics") or {}).get("modelId"),
            "keyholeLegSetsDepth": keyhole, "liquidus_C": parent["T_liq"], "scanSpeed_m_s": parent["v_scan"],
            "kernel": {"conductivity_W_mK": kernel[0], "specificHeat_J_kgK": kernel[1],
                       "density_kg_m3": kernel[2], "convention": kernel[3]},
            "identityChecks": identity_checks, "frontSampleDigest": sample_digest,
        },
        "front": {"samplerId": SAMPLER_ID, "status": front["status"], "branch": front["branch"],
                  "support": support, "samples": front["samples"]},
        "inputSensitivityRun": sensitivity,
        "phaseContext": {"text": "Literature context; phase prediction unavailable. " + context_text,
                         "locator": context_locator, "comparability": "context-only",
                         "sourceEvidenceKind": "Literature estimate"},
    })
    return out


# --- Spacing ------------------------------------------------------------------------------------------------------

def _chemistry_inputs(b: Builder, alloy: str) -> List[str]:
    """Declared nominal chemistry scenarios (no assay is supplied; Unresolved provenance)."""
    names = []
    rows = {"ti6al4v": [("aluminiumContent", 6.0, "nominal Ti-6Al-4V Al = 6 wt% declared, no assay supplied")],
            "alsi10mg": [("siliconContent", 10.0, "named Al-10Si-0.45Mg scenario: Si = 10 wt%, no assay supplied"),
                         ("magnesiumContent", 0.45, "named Al-10Si-0.45Mg scenario: Mg = 0.45 wt%, no assay supplied")],
            "in718": [("niobiumContent", 5.0, "Ni-5Nb proxy chemistry Nb = 5 wt%, no assay supplied")],
            "in625": [("niobiumContent", 5.0, "Ni-5Nb proxy chemistry Nb = 5 wt%; not an IN625 assay")],
            "ss316l": []}[alloy]
    for name, value, scope in rows:
        if name not in b.inputs:
            b.add_input(name, _record("declaredAssumption", f"nominal:{alloy}:{name}", status="inRange",
                                      declaration="python/lpbf_solidification_estimates.py#_chemistry_inputs",
                                      scope=scope, default_value=value))
        names.append(name)
    return names


def _proxy_input(b: Builder, alloy: str) -> str:
    p = PROXIES[alloy]
    if "binaryProxy" not in b.inputs:
        warnings = []
        if alloy == "ti6al4v":
            warnings.append(_warn("Ti-slope-closure", "binary slope |m| derived by freezing-range closure "
                                  f"({p['m']:.6g} K/wt%); the source prints {p['printedSlope']} K/wt%"))
        if alloy == "alsi10mg":
            warnings.append(_warn("binary-eutectic-omission", "Mg, minor elements and eutectic competition omitted "
                                  "from the dilute Al-Si binary coefficients"))
        kind = "sourceModelAssumption" if alloy == "ti6al4v" else "alloyTransfer"
        b.add_input("binaryProxy", _record(kind, f"binary-proxy:{alloy}", status="extrapolated",
                                           locator=p["locator"], scope=f"{p['family']}; {p['chem']}"),
                    warnings)
    return "binaryProxy"


def _local_summary(rows: Sequence[Mapping[str, Any]], values: Sequence[Any]) -> Any:
    weights = [s["weight_m"] for s in rows]
    if isinstance(values[0], dict):
        return {member: weighted_median([v[member] for v in values], weights) for member in values[0]}
    return weighted_median(values, weights)


def _spacing_quantities(b: Builder, alloy: str, rows: Sequence[Mapping[str, Any]], front_ok: bool,
                        blocked: Optional[Tuple[str, str]]) -> None:
    proxy = _proxy_input(b, alloy)
    chem = _chemistry_inputs(b, alloy)
    law = SPACING[alloy]
    for kind, name in (("pdas", "pdas"), ("sdas", "sdas")):
        entry = law[kind]
        definition = entry["definition"]
        law_input = f"{kind}Law"
        b.add_input(law_input, _record("sourceModelAssumption", f"{kind}-law:{alloy}", status="extrapolated",
                                       locator=entry["locator"], scope=f"source domain: {law['domain']}"))
        depends = ["frontSamples", law_input, proxy] + (["aluminiumContent"] if alloy == "ti6al4v" else [])
        if not front_ok:
            b.no_value(name, definition, "parent-unavailable", parent="frontSamples", depends_on=depends,
                       text=blocked[1] if blocked else NO_FRONT_TEXT)
            continue
        kept, values, refused = [], [], {}
        for s in rows:
            value, tag, raw = gated_spacing(alloy, kind, s["G_K_m"], s["R_m_s"])
            if value is None:
                refused[tag] = refused.get(tag, 0) + 1
                continue
            kept.append(s)
            values.append(value)
        diagnostics = {"retained": len(kept), "refusedByReason": refused}
        if len(kept) < MIN_BRANCH_SAMPLES:
            tag = max(refused, key=refused.get) if refused else "below-capillary-limit"
            text = {"below-capillary-limit": CAPILLARY_TEXT, "planar-or-absolute-stability": PLANAR_TEXT,
                    "outside-dendrite-range": PLANAR_TEXT}[tag]
            b.no_value(name, definition, "outside-source-model-domain", parent=law_input, depends_on=depends,
                       text=text, params={"gate": tag}, extra_validity={"localSupport": diagnostics})
            continue
        value = _local_summary(kept, values)
        q_lo = min(s["coolingRate_K_s"] for s in kept)
        q_hi = max(s["coolingRate_K_s"] for s in kept)
        own = [_warn("domain-extrapolation", f"LPBF local cooling {q_lo:.2g} to {q_hi:.2g} K/s outside the source "
                     f"conditions: {law['domain']}")]
        if alloy in ("alsi10mg", "ss316l"):
            own.append(_warn("alloy-family-transfer", f"{law['domain']} transferred to {ALLOY_NAMES[alloy]}"))
        label = "Primary dendrite arm spacing" if kind == "pdas" else "Secondary dendrite arm scale"
        text = law["text"].format(label=f"{TIER2_LABEL} of {label.lower()}")
        if kind == "sdas":
            text += f" {SECONDARY_ARMS}"
        text += " Inputs are outside the source conditions. " + UNKNOWN
        alternatives = definition == "pdas-model-alternatives"
        b.value(name, definition, value, depends_on=depends,
                sources=[_src(f"{kind}-law-{alloy}", entry["locator"]), SRC_A7_CAPILLARY],
                own_warnings=own, explanation=text,
                construction=("Two named Ni-Nb models evaluated per local tuple, each with unknown uncertainty and "
                              "no interval; their difference is model disagreement." if alternatives else
                              "Correlation evaluated per local tuple behind the capillary screening gate, weighted "
                              "median over the retained tuples; model and transfer error are not quantified."),
                extra_validity={"localSupport": diagnostics})


# --- Morphology -----------------------------------------------------------------------------------------------------

def _morphology_quantities(b: Builder, alloy: str, rows: Sequence[Mapping[str, Any]], front_ok: bool,
                           blocked: Optional[Tuple[str, str]]) -> None:
    proxy = _proxy_input(b, alloy)
    chem = [name for name in _chemistry_inputs(b, alloy) if name != "magnesiumContent" and name != "aluminiumContent"]
    p = PROXIES[alloy]
    for name, value in (("nucleationDensity", p["nuclei"]), ("activationUndercooling", p["activation"])):
        b.add_input(name, _record("declaredAssumption", f"nucleation:{alloy}:{name}", status="inRange",
                                  declaration="python/lpbf_solidification_estimates.py#PROXIES",
                                  scope=NUCLEATION_SCENARIOS[alloy], default_value=value))
    chi_deps = ["frontSamples", proxy] + chem
    frac_deps = chi_deps + ["nucleationDensity", "activationUndercooling"]
    if not front_ok:
        text = blocked[1] if blocked else NO_FRONT_TEXT
        b.no_value("planarStabilityIndex", "planar-stability-index", "parent-unavailable", parent="frontSamples",
                   depends_on=chi_deps, text=text)
        b.no_value("equiaxedEnvelopeFraction", "equiaxed-envelope-fraction", "parent-unavailable",
                   parent="frontSamples", depends_on=frac_deps, text=text)
        b.no_value("cetClass", "cet-class", "parent-unavailable", parent="equiaxedEnvelopeFraction",
                   depends_on=("equiaxedEnvelopeFraction",), text=text)
        return
    local = [morphology(alloy, s["G_K_m"], s["R_m_s"]) for s in rows]
    chi = _local_summary(rows, [m["chi"] for m in local])
    peclets = [m["peclet"] for m in local]
    b.value("planarStabilityIndex", "planar-stability-index", chi, depends_on=chi_deps,
            sources=[_src(f"binary-proxy-{alloy}", p["locator"]), SRC_BROOKE_TIP],
            explanation=(f"{TIER2_LABEL}: the planar stability index is about {_fmt(chi, 1)}. Values above 1 allow "
                         "a cellular or dendritic instability in this binary diffusion model. This does not identify "
                         f"grain shape. {UNKNOWN}"),
            construction="chi = P R / (D G) per local tuple, weighted median; binary proxy coefficients transferred.",
            extra_validity={"tipPeclet": {"min": min(peclets), "max": max(peclets)}})
    kept = [(s, m) for s, m in zip(rows, local) if m["fraction"] is not None]
    refused: Dict[str, int] = {}
    for m in local:
        if m["refusal"]:
            refused[m["refusal"]] = refused.get(m["refusal"], 0) + 1
    diagnostics = {"retained": len(kept), "refusedByReason": refused,
                   "classCounts": {c: sum(1 for _, m in kept if m["class"] == c)
                                   for c in ("columnar", "mixed", "equiaxed")}}
    if len(kept) < MIN_BRANCH_SAMPLES:
        tag = max(refused, key=refused.get) if refused else "outside-dendritic-growth-domain"
        text = AL_EUTECTIC_TEXT if tag == "tip-reaches-eutectic" else GRAIN_DOMAIN_TEXT
        b.no_value("equiaxedEnvelopeFraction", "equiaxed-envelope-fraction", "outside-source-model-domain",
                   parent=proxy, depends_on=frac_deps, text=text, params={"gate": tag},
                   extra_validity={"localSupport": diagnostics})
        b.no_value("cetClass", "cet-class", "parent-unavailable", parent="equiaxedEnvelopeFraction",
                   depends_on=("equiaxedEnvelopeFraction",), text=text)
        return
    fraction = _local_summary([s for s, _ in kept], [m["fraction"] for _, m in kept])
    pe_hi = max(m["peclet"] for _, m in kept)
    own = [_warn("nucleation-scenario-unresolved", f"N0 {p['nuclei']:g} m^-3 and activation {p['activation']:g} K: "
                 f"{NUCLEATION_SCENARIOS[alloy]}")]
    if pe_hi >= 0.1:
        own.append(_warn("low-peclet-tip-law", f"The tip Peclet number is up to {pe_hi:.2g}. The low-Peclet tip "
                         "approximation is outside its declared screening range; finite-Peclet growth may change "
                         "this estimate."))
    klass = cet_class(fraction)
    fraction_text = f"{fraction:.1e}" if 0 < fraction < 0.05 else _fmt(fraction, 1)
    b.value("equiaxedEnvelopeFraction", "equiaxed-envelope-fraction", fraction, depends_on=frac_deps,
            sources=[SRC_HUNT_DURGA, SRC_BROOKE_TIP, _src(f"binary-proxy-{alloy}", p["locator"])],
            own_warnings=own, fraction_basis="volume",
            explanation=(f"{TIER2_LABEL}: about {fraction_text} of the model grain envelopes are equiaxed, giving a "
                         f"{klass} model class. This uses {p['family']} growth parameters and an assumed nucleation "
                         f"state. {UNKNOWN}"),
            construction="Hunt envelope fraction per local tuple, weighted median; Durga true-fraction convention.",
            extra_validity={"localSupport": diagnostics})
    b.value("cetClass", "cet-class", klass, depends_on=("equiaxedEnvelopeFraction",),
            sources=[SRC_HUNT_DURGA], explanation=(f"{TIER2_LABEL}: {klass} model class from the envelope fraction "
                                                   f"(f <= 0.0049 columnar, f >= 0.49 equiaxed). {UNKNOWN}"),
            construction="Class of the summarized envelope fraction; per-sample class counts are in localSupport.",
            extra_validity={"localSupport": diagnostics})


# --- Phase models ---------------------------------------------------------------------------------------------------

def _phase_quantities(b: Builder, alloy: str, rows: Sequence[Mapping[str, Any]], front_ok: bool,
                      blocked: Optional[Tuple[str, str]], parent: Mapping[str, Any],
                      request: Mapping[str, Any]) -> None:
    if alloy == "ti6al4v":
        _km_quantity(b, rows, front_ok, blocked, parent, request)
        return
    if alloy == "alsi10mg":
        _al_phase_quantities(b, front_ok, blocked)
        return
    b.add_input("phaseSelectionModel", _record("declaredAssumption", f"phase-model:{alloy}", status="outOfRange",
                                               declaration="python/lpbf_solidification_estimates.py#PHASE_NO_MODEL_TEXT",
                                               scope="no admitted phase-resolved model for this alloy"))
    reasons = [qe.reason("missing-thermal-history", {}, {"input": "phaseSelectionModel",
                                                         "kind": "declaredAssumption"})]
    b.no_value("phaseInventory", "solid-state-transformation", "missing-source-bound-model",
               parent="phaseSelectionModel", depends_on=("phaseSelectionModel",), text=PHASE_NO_MODEL_TEXT[alloy],
               extra_reasons=reasons)


def _km_quantity(b: Builder, rows, front_ok, blocked, parent, request) -> None:
    b.add_input("kmModel", _record("sourceModelAssumption", "km-salsi2018", status="inRange", locator=KM_LOCATOR,
                                   scope="first-pass, fully beta, diffusion-suppressed KM progress; Ms fitted"))
    b.add_input("beta0", _record("declaredAssumption", "km-beta0-nominal", status="inRange",
                                 declaration="python/lpbf_solidification_estimates.py#_km_quantity",
                                 scope="entering beta fraction declared 1 (fully beta before cooling)",
                                 default_value=1.0))
    depends = ("frontSamples", "kmModel", "beta0", "preheat_C")
    if not front_ok:
        b.no_value("kmAlphaMFraction", "km-alpha-m-fraction", "parent-unavailable", parent="frontSamples",
                   depends_on=depends, text=blocked[1] if blocked else NO_FRONT_TEXT)
        return
    preheat = request["process"]["preheat_C"]
    v = parent["v_scan"]
    kept, refused, evaluations = [], {}, []
    for s in rows:
        try:
            path = km_path(parent["T_fn"], s, v, preheat)
            fine = km_path(parent["T_fn"], s, v, preheat, ratio=math.sqrt(KM_PATH_RATIO))
        except ValueError as exc:
            refused[str(exc)] = refused.get(str(exc), 0) + 1
            continue
        tolerance = KM_TIME_TOLERANCE_REL * path["time_s"]
        if abs(path["time_s"] - fine["time_s"]) > tolerance or abs(path["timeLinear_s"] - path["time_s"]) > max(
                tolerance, abs(path["time_s"])):
            refused["refinement-failed"] = refused.get("refinement-failed", 0) + 1
            continue
        kept.append(s)
        evaluations.append((s, path, tolerance))
    if len(kept) < MIN_BRANCH_SAMPLES:
        reason = max(refused, key=refused.get) if refused else "missing-evaluation-crossing"
        b.no_value("kmAlphaMFraction", "km-alpha-m-fraction", "missing-thermal-history", parent="kmModel",
                   depends_on=depends, text=KM_MISSING_TEXT, params={"gate": reason},
                   extra_validity={"localSupport": {"retained": len(kept), "refusedByReason": refused}})
        return
    T_eval = preheat + KM_OFFSET_K
    fraction = km_fraction(T_eval)
    s0, path, tolerance = evaluations[len(evaluations) // 2]
    i0, i1 = path["bracket"]
    evaluation = {"ruleId": qe.KM_EVALUATION_RULE, "preheat_K": preheat + KELVIN, "offset_K": KM_OFFSET_K,
                  "temperature_K": T_eval + KELVIN, "time_s": path["time_s"],
                  "historyBracketIds": [f"{s0['sampleId']}:path:{i0}", f"{s0['sampleId']}:path:{i1}"],
                  "timeInterpolation": "linear-in-temperature",
                  "refinement": {"status": "refinement-passed", "timeTolerance_s": tolerance,
                                 "temperatureTolerance_K": KM_TEMPERATURE_TOLERANCE_K}}
    residual = {"untransformedAsymptote": 1.0 - fraction, "beta0": 1.0, "preExistingConstituent": 0.0}
    shown = _fmt(fraction, 1)
    if T_eval >= KM_MS_C:
        text = (f"{TIER2_LABEL}: zero transformation by this evaluation state (the evaluation temperature "
                f"{T_eval:g} C is at or above Ms). {UNKNOWN}")
    elif float(shown) >= 0.9:
        text = (f"{TIER2_LABEL} for a single rapid cooling pass: mostly alpha martensite or massive alpha (model about "
                f"{shown}). The remainder is the untransformed KM asymptote, not an estimate of retained beta. Ms is a "
                f"fitted source parameter with unquantified uncertainty. {UNKNOWN}")
    else:
        text = (f"{TIER2_LABEL} for a single rapid cooling pass: about {shown} alpha martensite or massive alpha. The "
                "remainder is the untransformed KM asymptote, not an estimate of retained beta. Ms is a fitted source "
                f"parameter with unquantified uncertainty. {UNKNOWN}")
    b.value("kmAlphaMFraction", "km-alpha-m-fraction", fraction, depends_on=depends,
            sources=[_src("salsi2018", KM_LOCATOR)], fraction_basis="reaction-progress",
            own_warnings=[_warn("km-source-fit-uncertainty", "Ms = 575 C and km = 0.005 1/K are fitted source "
                                "parameters with unquantified uncertainty")],
            explanation=text, construction="KM progress at the first post-melt crossing of preheat + 25 K on each "
                                           "retained single-pass material path; no interval.",
            extra={"evaluation": evaluation, "residual": residual},
            extra_validity={"localSupport": {"retained": len(kept), "refusedByReason": refused}})


def _al_phase_quantities(b: Builder, front_ok: bool, blocked) -> None:
    _chemistry_inputs(b, "alsi10mg")
    b.add_input("equilibriumModel", _record(
        "sourceModelAssumption", "al-equilibrium-limit", status="extrapolated",
        locator=("Yaokawa et al. 2023, Mater. Trans. 64, doi 10.2320/matertrans.MT-M2022165, section 4.3; CIAAW "
                 "abridged atomic weights Mg 24.305, Si 28.085"),
        scope="zero terminal solubility, all Mg as Mg2Si: terminal equilibrium-limit reference"))
    value = al_equilibrium()
    b.value("equilibriumPhaseInventory", "terminal-equilibrium-phase-inventory", value,
            depends_on=("siliconContent", "magnesiumContent", "equilibriumModel"),
            sources=[_src("yaokawa2023", b.inputs["equilibriumModel"]["sourceLocator"])],
            own_warnings=[_warn("equilibrium-limit-only", "zero-solubility equilibrium reference; supersaturation, "
                                "metastable precipitates and Mg loss after rapid cooling are not modelled")],
            fraction_basis="mass",
            explanation=(f"{TIER2_LABEL} for the terminal equilibrium limit: about {_fmt(value['alphaAl'], 1)} "
                         f"aluminium, {_fmt(value['Si'], 1)} silicon and {_fmt(value['Mg2Si'], 1)} Mg2Si by mass "
                         "(rounded, so the shown values need not add to 1). The model assumes no solute remains in "
                         "aluminium and all magnesium forms Mg2Si. It does not predict the retained phases after "
                         f"rapid cooling. {UNKNOWN}"),
            construction="Mass balance of the named Al-10Si-0.45Mg scenario; no interval.")
    b.add_input("scheilModel", _record(
        "alloyTransfer", "al-si-binary-scheil", status="extrapolated",
        locator="Azizi 2020 Table II k = 0.13 (Al-0.5Si); Ce 12.6 wt% Metals 12 (2022) 1711 Table 1",
        scope="binary Al-Si Scheil with dilute Al-0.5Si partitioning transferred to AlSi10Mg; Mg omitted"))
    depends = ("frontSamples", "siliconContent", "scheilModel")
    if not front_ok:
        b.no_value("scheilMicroconstituents", "scheil-microconstituent-inventory", "parent-unavailable",
                   parent="frontSamples", depends_on=depends, text=blocked[1] if blocked else NO_FRONT_TEXT)
        return
    split = al_scheil()
    b.value("scheilMicroconstituents", "scheil-microconstituent-inventory", split, depends_on=depends,
            sources=[_src("al-scheil", b.inputs["scheilModel"]["sourceLocator"])], fraction_basis="mass",
            own_warnings=[_warn("microconstituent-not-phase", "primary alpha-Al and the Al plus Si eutectic "
                                "constituent are microconstituents, not separate Al and Si phase fractions")],
            explanation=(f"{TIER2_LABEL} for one complete solidification pass: about "
                         f"{_fmt(split['primaryAlphaAl'], 1)} primary aluminium and "
                         f"{_fmt(split['eutecticConstituent'], 1)} aluminium plus silicon eutectic constituent by "
                         "mass. This uses a binary Al-Si Scheil model transferred to AlSi10Mg. It does not predict "
                         f"separate silicon or Mg2Si phase fractions. {UNKNOWN}"),
            construction="Constant-k binary Scheil at the named 10 wt% Si scenario; no interval.")


# ======================================================================================================================
# Projections onto other served surfaces (SPEC engine estimates 2026-10-17, groups 6 and 8)
# ======================================================================================================================

PROJECTION_REQUEST_KEYS = ("power_W", "speed_mm_s", "beamDiameter_um", "preheat_C", "layerThickness_um", "hatch_um")
CET_PROJECTION_ID = "sol-c-cet-projection-v1"
CET_STALE_TEXT = ("A grain estimate needs a compatible cooling-side front and a growth model for this solidification "
                  "regime. The thermal parent of this cell did not match the estimate kernel, so no front was formed.")


def projection_request(alloy: str, process: Mapping[str, float], heat_source: str) -> Dict[str, Any]:
    """The channel's parsed request for a projection; raises ValueError with the channel's refusal detail."""
    params = {"materialName": MATERIAL_NAMES.get(alloy, alloy), "heatSource": heat_source,
              **{key: process[key] for key in PROJECTION_REQUEST_KEYS}}
    request, refusal = parse_request({"params": params})
    if refusal is not None:
        raise ValueError(refusal["refusal"]["detail"])
    return request


CET_NO_FRONT_TEXT = ("A grain estimate needs a compatible cooling-side front and a growth model for this "
                     "solidification regime. No front parent was formed for this cell.")
CET_SOLVER_TEXT = ("A grain estimate needs a completed thermal solve. The solver failed for this cell, so no front or "
                   "grain class exists.")


def unavailable_container(name: str, definition: str, code: str, text: str, scope: str) -> Dict[str, Any]:
    """A v2 container whose one quantity is no-value with ``code`` and the constructive ``text``."""
    b = Builder()
    b.add_input("frontSamples", _record("declaredAssumption", f"front-samples:{code}", status="outOfRange",
                                        declaration="python/lpbf_solidification_estimates.py#front_state",
                                        scope=scope))
    b.no_value(name, definition, code, parent="frontSamples", depends_on=("frontSamples",), text=text)
    return qe.container(b.quantities, input_provenance=b.inputs, schema=qe.ENVELOPE_SCHEMA_V2)


def cet_unavailable(code: str) -> Dict[str, Any]:
    """The CET block of a cell without a usable front parent (parent-unavailable, solver-error, stale-parent-input)."""
    text, scope = {"stale-parent-input": (CET_STALE_TEXT, "captured thermal parent did not match the estimate kernel"),
                   "solver-error": (CET_SOLVER_TEXT, "the thermal solve of this cell failed"),
                   "parent-unavailable": (CET_NO_FRONT_TEXT, "no captured front parent")}[code]
    out = unavailable_container("class", "cet-class", code, text, scope)
    out.update(status="failed" if code == "solver-error" else "unavailable", projectionId=CET_PROJECTION_ID,
               surrogate=None)
    if code == "solver-error":
        out["quantities"]["class"]["status"] = "failed"
    return out


def cet_projection(alloy: str, thermal: Mapping[str, Any], parent: Mapping[str, Any], process: Mapping[str, float],
                   heat_source: str) -> Dict[str, Any]:
    """The channel's Hunt/Durga grain-envelope model at this served solve's own rear-branch tuples (group 6).

    Returns a v2 container with ``class`` (cet-class), ``equiaxedEnvelopeFraction`` and ``planarStabilityIndex``,
    plus ``status``, ``projectionId`` and ``surrogate``. Same tuples, proxies, nucleation scenarios and gates as the
    SOL-C channel; the legacy Knapp route of lpbf_cet_screening keeps its own identity and stays unavailable."""
    request = projection_request(alloy, process, heat_source)
    try:
        state = front_state(request, thermal, parent, support_resolutions=False)
    except StaleParent:
        return cet_unavailable("stale-parent-input")
    b = state["builder"]
    _morphology_quantities(b, alloy, state["rows"], state["blocked"] is None, state["blocked"])
    quantities = {("class" if name == "cetClass" else name): q for name, q in b.quantities.items()
                  if name in ("cetClass", "equiaxedEnvelopeFraction", "planarStabilityIndex")}
    out = qe.container(quantities, input_provenance=b.inputs, schema=qe.ENVELOPE_SCHEMA_V2,
                       default=not state["surrogate"])
    statuses = [q["status"] for q in quantities.values()]
    out.update(status=("computed" if all(s == "computed" for s in statuses) else
                       "partial" if any(s == "computed" for s in statuses) else "unavailable"),
               projectionId=CET_PROJECTION_ID, surrogate="conduction-field" if state["surrogate"] else None)
    return out
