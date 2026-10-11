#!/usr/bin/env python3
"""
MetalliX Python LPBF Thermal, Melt Pool Geometry & Multi-Defect Physics Solver
Author: MetalliX Additive Manufacturing HPC Subsystem

Simulates:
1. 3D Goldak double-ellipsoid moving laser heat source & Eagar-Tsai / Rosenthal thermal fields
2. Multi-regime melt pool geometry (Conduction, Transition, Keyhole Mode)
3. 3-View geometric contours (Top-Down X-Y, Longitudinal X-Z, Transverse Y-Z with Hatch Overlap)
4. Hydrodynamic Marangoni convection, Knudsen recoil vapor pressure (flat absorptivity; no multiple-reflection term)
5. Comprehensive defect analytics: Lack of Fusion (LoF), Keyhole Porosity, Plateau-Rayleigh Balling, Spatter Denudation
6. Solidification kinetics: G(x,y,z), R(x,y,z), Cooling Rate G*R, Hunt CET morphology, PDAS & SDAS
7. Full 2D Power-Velocity (P-V) Process Window map generation
"""

import sys
import json
import math
import time

import numpy as np

from eagar_tsai_solver import EagarTsaiField, MODEL_ID as EAGAR_TSAI_MODEL_ID
from fabbro_keyhole import MODEL_ID as FABBRO_MODEL_ID, fabbro_keyhole_depth_m
from four_alloy_materials import four_alloy_thermophysical_db, thermal_props
from in625_thermal_material import LATENT_HEAT_J_KG as IN625_LATENT_HEAT_J_KG
from goldak_solver import GoldakField, MODEL_ID as GOLDAK_MODEL_ID, seed_goldak_axes
from solidification_front import MODEL_ID as SOLIDIFICATION_MODEL_ID, evaluate_solidification
from marangoni_screening import MODEL_ID as MARANGONI_MODEL_ID, marangoni_screening
from lpbf_defect_diagnostics import balling_screen, defect_diagnostics

# Secondary alloys only. Ti-6Al-4V, 316L, AlSi10Mg, IN718 live in four_alloy_materials.py.
SECONDARY_THERMOPHYSICAL_DB = {
    "Inconel 625": {
        "base": "Ni",
        "liquidus_C": 1350.0,
        "solidus_C": 1290.0,
        "boiling_C": 2880.0,
        "M_molar_kg_mol": 0.0585,
        "density_kg_m3": 8440.0,
        "density_liquid_kg_m3": 7600.0,
        "thermal_conductivity_W_mK": 9.8,
        "thermal_conductivity_liquid_W_mK": 30.0,
        "specific_heat_J_kgK": 410.0,
        "specific_heat_liquid_J_kgK": 750.0,
        # D5: the Rosenthal / build-job path and the Sabau screening snapshot share 290 kJ/kg
        # (Sabau et al. 2020, cited in in625_thermal_material); the former 260 kJ/kg literal disagreed.
        # The Mills-based transient specification (in625_thermal_material.transientSpecification)
        # keeps its own 227 kJ/kg and is NOT changed here.
        "latent_heat_fusion_J_kg": IN625_LATENT_HEAT_J_KG,
        "latent_heat_vap_J_kg": 6300000.0,
        "absorptivity_IR": 0.38,
        "absorptivity_Green": 0.58,
        "surface_tension_N_m": 1.76,
        "d_gamma_dT_N_mK": -0.00045,
        "viscosity_Pa_s": 0.0055,
        "thermal_expansion_1_K": 12.8e-6,
        "youngs_modulus_GPa": 205.0,
        "poissons_ratio": 0.31,
        "pdas_A1": 80.0,
        "sdas_B1": 42.0
    },
    "CoCrMo": {
        "base": "Co",
        "liquidus_C": 1395.0,
        "solidus_C": 1330.0,
        "boiling_C": 2870.0,
        "M_molar_kg_mol": 0.0585,
        "density_kg_m3": 8300.0,
        "density_liquid_kg_m3": 7500.0,
        "thermal_conductivity_W_mK": 14.8,
        "thermal_conductivity_liquid_W_mK": 28.0,
        "specific_heat_J_kgK": 450.0,
        "specific_heat_liquid_J_kgK": 740.0,
        "latent_heat_fusion_J_kg": 275000.0,
        "latent_heat_vap_J_kg": 6300000.0,
        "absorptivity_IR": 0.40,
        "absorptivity_Green": 0.60,
        "surface_tension_N_m": 1.75,
        "d_gamma_dT_N_mK": -0.00038,
        "viscosity_Pa_s": 0.0052,
        "thermal_expansion_1_K": 14.2e-6,
        "youngs_modulus_GPa": 230.0,
        "poissons_ratio": 0.30,
        "pdas_A1": 85.0,
        "sdas_B1": 44.0
    },
    "Scalmalloy (Al-Mg-Sc-Zr)": {
        "base": "Al",
        "liquidus_C": 645.0,
        "solidus_C": 580.0,
        "boiling_C": 2470.0,
        "M_molar_kg_mol": 0.0272,
        "density_kg_m3": 2670.0,
        "density_liquid_kg_m3": 2380.0,
        "thermal_conductivity_W_mK": 115.0,
        "thermal_conductivity_liquid_W_mK": 78.0,
        "specific_heat_J_kgK": 920.0,
        "specific_heat_liquid_J_kgK": 1200.0,
        "latent_heat_fusion_J_kg": 405000.0,
        "latent_heat_vap_J_kg": 10500000.0,
        "absorptivity_IR": 0.22,
        "absorptivity_Green": 0.42,
        "surface_tension_N_m": 0.88,
        "d_gamma_dT_N_mK": -0.00032,
        "viscosity_Pa_s": 0.0014,
        "thermal_expansion_1_K": 22.0e-6,
        "youngs_modulus_GPa": 72.0,
        "poissons_ratio": 0.33,
        "pdas_A1": 38.0,
        "sdas_B1": 18.0
    },
    "Hastelloy X": {
        "base": "Ni",
        "liquidus_C": 1355.0,
        "solidus_C": 1260.0,
        "boiling_C": 2880.0,
        "M_molar_kg_mol": 0.0580,
        "density_kg_m3": 8220.0,
        "density_liquid_kg_m3": 7480.0,
        "thermal_conductivity_W_mK": 12.0,
        "thermal_conductivity_liquid_W_mK": 30.0,
        "specific_heat_J_kgK": 485.0,
        "specific_heat_liquid_J_kgK": 760.0,
        "latent_heat_fusion_J_kg": 265000.0,
        "latent_heat_vap_J_kg": 6450000.0,
        "absorptivity_IR": 0.39,
        "absorptivity_Green": 0.59,
        "surface_tension_N_m": 1.76,
        "d_gamma_dT_N_mK": -0.00042,
        "viscosity_Pa_s": 0.0058,
        "thermal_expansion_1_K": 14.5e-6,
        "youngs_modulus_GPa": 205.0,
        "poissons_ratio": 0.30,
        "pdas_A1": 82.0,
        "sdas_B1": 43.0
    },
    "Pure Copper (Cu-OF)": {
        "base": "Cu",
        "liquidus_C": 1083.0,
        "solidus_C": 1083.0,
        "boiling_C": 2562.0,
        "M_molar_kg_mol": 0.0635,
        "density_kg_m3": 8960.0,
        "density_liquid_kg_m3": 8020.0,
        "thermal_conductivity_W_mK": 390.0,
        "thermal_conductivity_liquid_W_mK": 160.0,
        "specific_heat_J_kgK": 385.0,
        "specific_heat_liquid_J_kgK": 540.0,
        "latent_heat_fusion_J_kg": 205000.0,
        "latent_heat_vap_J_kg": 4730000.0,
        "absorptivity_IR": 0.08,   # Very low IR absorption
        "absorptivity_Green": 0.45, # High Green 515nm absorption
        "surface_tension_N_m": 1.30,
        "d_gamma_dT_N_mK": -0.00028,
        "viscosity_Pa_s": 0.0040,
        "thermal_expansion_1_K": 16.5e-6,
        "youngs_modulus_GPa": 120.0,
        "poissons_ratio": 0.34,
        "pdas_A1": 50.0,
        "sdas_B1": 25.0
    }
}

THERMOPHYSICAL_DB = {**four_alloy_thermophysical_db(), **SECONDARY_THERMOPHYSICAL_DB}

# Regime (normalised-enthalpy screening index, repo convention r = 1/e^2 radius, flat A, solid k/cp,
# hs = rho cp_s (T_liq - T0)). 15 = vapor-depression onset (Cunningham 2019 Fig. 3A blue line, app units
# 13.0-16.9 along speed). 20 = PROVISIONAL screening choice for the keyhole-mode onset (melt-pool D/W ~ 0.5): it
# lies in the overlap of the King et al. 2014 30 +/- 4 (316L, Table 3 constants with the density unit corrected
# to 7980 kg/m3, sigma = D4sigma/4) converted to this convention = 22.2 (19.3-25.2, conditional on the app
# absorptivity, 20 C preheat and property set) and the Cunningham 2019 Fig. 3A red-line values along speed
# (Ti-6Al-4V, 95 um 1/e^2) = 17.3-20.0 (a range along speed, not a confidence interval). Not an exact threshold.
ENTHALPY_TRANSITION = 15.0
ENTHALPY_KEYHOLE = 20.0
# Inconel 625 only (planned bump in625-regime, 2026-10-11): per-alloy keyhole-mode cut on the same app index. Fitted
# (max balanced accuracy, midpoint, rounded to 0.1) on 56 EOS M270 IN625 tracks of NIST mds2-2923 (Weaver et al.,
# doi 10.18434/mds2-2923) with the pre-declared truth depth > half width (King et al. 2014 Sec. 5.2); scored once on
# 13 held-out IN625 tracks (mds2-2923 AMMT spot series, Lane et al. 2020 doi 10.1007/s40192-020-00169-1 Table 3):
# 0 errors, balanced accuracy 1.00 (the shared cut 20: 3 errors, 0.70). The held-out data only place the onset in
# (12.67, 13.94]; 13.6 is the fit-split point estimate. Weaver, Heigel and Lane 2022 "about 30" is 21.73 in app units
# (factor 0.7243) and makes the same 3 errors. docs/research/PREDECLARED_ / RESULTS_in625_regime_2026-10-11.*.
# The transition cut 15 is not moved (it also starts the Fabbro leg onset ramp, fabbro_keyhole.ENTHALPY_ONSET), so
# IN625 has no transition band: < 13.6 conduction, >= 13.6 keyhole mode. No width or depth number changes.
ENTHALPY_KEYHOLE_IN625 = 13.6
REGIME_THRESHOLD_BASIS = ("dH/hs < 15 conduction, 15-20 transition, >= 20 keyhole mode (melt-pool D/W > 0.5 "
                          "screening onset); Inconel 625 uses its own cut: < 13.6 conduction, >= 13.6 keyhole mode, "
                          "no transition band (see the IN625 alloy note). "
                          "20 is a provisional screening choice, not a derived exact threshold: it "
                          "lies in the overlap of King et al. 2014 30+/-4 (316L) converted to the repo convention "
                          "(19.3-25.2; conditional on the app absorptivity, 20 C preheat and property set; King's "
                          "printed density unit kg/m3 corrected to 7980 kg/m3) and the Cunningham et al. 2019 Fig. 3A "
                          "melt-pool transition line (Ti-6Al-4V; app index 17.3-20.0 along speed, a range, not a "
                          "confidence interval). Both sources and the held-out checks are for Ti-6Al-4V and 316L; "
                          "transferred, not derived, for IN718/AlSi10Mg and the other alloys. "
                          "Cunningham and Gan data are not independent validation. Keyhole mode is not keyhole "
                          "porosity; a low index is not an assurance.")
REGIME_MATERIAL_NOTE_DERIVED = ("threshold derived for this alloy from Ti-6Al-4V / 316L data (provisional screening "
                                "choice)")
REGIME_MATERIAL_NOTE_IN625 = ("per-alloy keyhole-mode cut 13.6 (no transition band), fitted on 56 EOS M270 IN625 "
                              "tracks of NIST mds2-2923 (Weaver et al.) with the truth depth > half width; on 13 "
                              "held-out IN625 tracks (NIST AMMT, Lane et al. 2020) it makes 0 errors, balanced "
                              "accuracy 1.00 (the shared cut 20 makes 3); the held-out data place the onset only in "
                              "(12.67, 13.94], so 13.6 is a fit-split point estimate, not a held-out-validated value; "
                              "tied to the app's estimated IN625 properties; screening only, not validation")
REGIME_MATERIAL_NOTE_UNVALIDATED = "threshold not validated for this alloy"


def _is_in625(material_name) -> bool:
    return "625" in str(material_name or "").lower()


def regime_keyhole_cut(material_name=None) -> float:
    """Keyhole-mode cut on dH/hs for this alloy: ENTHALPY_KEYHOLE_IN625 for Inconel 625, else ENTHALPY_KEYHOLE."""
    return ENTHALPY_KEYHOLE_IN625 if _is_in625(material_name) else ENTHALPY_KEYHOLE


def regime_material_note(material_name: str) -> str:
    """Per-alloy statement shown next to the regime so that a low index never reads as an assurance."""
    name = str(material_name).lower()
    if _is_in625(name):
        return REGIME_MATERIAL_NOTE_IN625
    if "ti-6al-4v" in name or "ti6al4v" in name or "316l" in name:
        return REGIME_MATERIAL_NOTE_DERIVED
    return REGIME_MATERIAL_NOTE_UNVALIDATED


# Keyhole-porosity screen (proxy, not a porosity boundary; Zhao 2020 shows no single index cut exists).
POROSITY_SCREEN_NEGLIGIBLE_BELOW = 15.0
POROSITY_SCREEN_HIGH_AT = 30.0
KEYHOLE_POROSITY_BASIS = ("Porosity unresolved; legacy screening level on the normalised enthalpy, independent of the "
                          "regime threshold. < 15: Zhao 2020 (doi 10.1126/science.abd1587) found no pore condition "
                          "below 15 (0/35) and its boundary minimum is 15.0; 0/35 observations is not evidence of "
                          "safety. >= 30 is the legacy screen kept for verdict continuity, not a porosity boundary "
                          "(Zhao 2020 stable keyholes up to dH/hs 62 at high speed). Keyhole mode (>= 20) does not "
                          "imply porosity.")
KEYHOLE_DEPTH_BENCHMARK_NOTE = ("vs x-ray vapor-depression depths (keyhole benchmark 2026-10-07): under-predicts "
                                "Ti-6Al-4V (median ratio 0.62 at 95 um, 0.12 at 140 um) and exceeds the measured "
                                "316L melt depth in 176/677 Hofmann tracks; no single A(R) or ramp change fixes "
                                "both. Cause not resolved; candidate mechanisms: beam-diameter convention into "
                                "Fabbro's uniform model (Fabbro 2020 Sec. 3.4 discusses ~56 um effective diameter for a "
                                "95 um Gaussian; the app passes the 1/e^2 diameter), model validity range 2<=Pe<=10 / "
                                "deep cylindrical keyhole, flat keyhole absorptivity (no A(R) multiple-reflection "
                                "term), no vaporisation heat sink; tracked as a later bump")
# P1 planned bump (2026-10-11, docs/research/SPEC_p1_sourced_served_physics_2026-10-11.md): one depth path for every
# kernel, depth = max(conduction isotherm depth, Fabbro leg). The former Rosenthal-only increment
# (heuristic-keyhole-increment-v1, uncited) and its 30 band edge were removed.
FABBRO_BASIS = ("Fabbro 2020 eq. 2 (A(R) P distributed by multiple reflection) with the keyhole absorptivity A(R) "
                "UNMODELLED: the flat-surface value is passed, a disclosed lower bound. Measured absorptance rises at "
                "the keyhole threshold R = 1 and with R (Trapp 2017 Fig. 3a 316L 0.3 to 0.78; Deisenroth 2020 Fig. 7 "
                "IN625 0.34 to 0.90; Fabbro 2020 Sec. 4.1 and A(1) about 0.6), so transition and keyhole depth from "
                "this leg is biased low. m=2.4, n=3 fitted for 2<=Pe<=10 and served outside that band for every kernel "
                "(see pecletInFitRange); uncited linear dH/hs onset ramp 15->30 (P2); k_s is the room-temperature solid "
                "value (Fabbro's constants imply a high-temperature K; P2). Depth served as max(conduction isotherm "
                "depth, this leg) for every kernel; " + KEYHOLE_DEPTH_BENCHMARK_NOTE)
EFFECTIVE_ABSORPTIVITY_BASIS = ("flat absorptivity of the material authority for the conduction field (Eagar-Tsai 1983 "
                                "and Goldak 1984 take Q as absorbed power; Knapp 2022 finds the IN625 conduction-mode "
                                "effective absorption near Fresnel 0.30, HT 0.29 to 0.32, HTFF 0.27 to 0.29). No kernel "
                                "represents the measured absorptance rise in transition and keyhole mode (0.6 to 0.9: "
                                "Deisenroth 2020 Fig. 7, Trapp 2017 Fig. 3a). The former multi-reflection ramp 1-(1-A)^n "
                                "(uncited) was removed 2026-10-11.")
LATENT_HEAT_POWER_FACTOR_BASIS = ("1.0 for every kernel; latent heat of fusion is excluded from the conduction field "
                                  "(Rubenchik 2018 Sec. 3.1, Gan 2021 SI Method 3), from the index hs and from the "
                                  "Fabbro leg; the former 1/(1+0.55 St) factor (uncited) was removed.")

# Absorption model of the screening kernels. "flat-plate" (default, every machine): the material
# authority's flat absorptivity feeds ΔH/hs, the conduction power of every kernel and the process map
# (no multiple-reflection term anywhere since P1). "powder-raytrace": the GPU powder-bed ray tracer
# (Warp + CUDA) supplies the conduction absorptivity; it runs ONLY when requested explicitly and its
# errors propagate (no silent import-success branch, so results do not depend on whether CUDA is installed).
ABSORPTION_MODEL_FLAT = "flat-plate"
ABSORPTION_MODEL_POWDER_RAYTRACE = "powder-raytrace"
ABSORPTION_MODELS = (ABSORPTION_MODEL_FLAT, ABSORPTION_MODEL_POWDER_RAYTRACE)
# thermalSlices sampler: "cpu" (default, every machine) or "warp" (float32 GPU sampler, opt-in only).
THERMAL_SLICE_BACKENDS = ("cpu", "warp")
DISTORTION_INDEX_BASIS = ("alloy/layer/preheat-only: E, alpha, nu, T_solidus - T_preheat and layer thickness; "
                          "not evaluated from scan parameters (P, v, hatch)")


def classify_enthalpy_regime(normalized_enthalpy: float, material_name=None) -> str:
    """Regime label; without a material name (or for any alloy but Inconel 625) the shared 15 / 20 cuts."""
    if normalized_enthalpy >= regime_keyhole_cut(material_name):
        return "Keyhole Mode (melt-pool D/W > 0.5 screening onset)"
    if normalized_enthalpy >= ENTHALPY_TRANSITION:
        return "Transition Mode"
    return "Conduction Mode (Stable)"


def rosenthal_temperature_C(x_m, y_m, z_m, T0_C, P_eff, k_th, v_scan, alpha_th, r_reg):
    """3D Rosenthal (1946) moving point source T0 + P/(2 pi k R) exp(-v (R + x) / 2 alpha).

    Only the 1/R prefactor is regularised (R_reg = sqrt(R^2 + r_reg^2), r_reg ~ beam radius); the
    advective exponent keeps the true R, so R + x = 0 on the trailing axis exactly as in Rosenthal.
    The near-field maximum T0 + P/(2 pi k r_reg) is a regularisation artefact, not a wall temperature.
    """
    R = math.sqrt(x_m * x_m + y_m * y_m + z_m * z_m)
    R_reg = math.sqrt(R * R + r_reg * r_reg)
    arg = -v_scan * (R + x_m) / max(1e-16, 2.0 * alpha_th)
    arg = max(-45.0, min(20.0, arg))
    return T0_C + (P_eff / (2.0 * math.pi * k_th * R_reg)) * math.exp(arg)


def knight_recoil_pressure_kPa(T_surface_C, T_vap_C, delta_H_vap_J_mol, R_gas=8.314):
    """Anisimov (1968) / Knight (1979) recoil p = 0.54 p_sat(T), p_sat from Clausius-Clapeyron referenced to
    1 atm at T_vap. Continuous in T: no 0.8*T_vap gate (taken in degC before) and no fixed 0.1 kPa floor."""
    T_surf_K = float(T_surface_C) + 273.15
    T_vap_K = float(T_vap_C) + 273.15
    recoil_exp = (delta_H_vap_J_mol / R_gas) * (1.0 / T_vap_K - 1.0 / max(500.0, T_surf_K))
    if recoil_exp > 700.0:
        p_recoil_atm = 1.0e200
    elif recoil_exp < -700.0:
        p_recoil_atm = 0.0
    else:
        p_recoil_atm = 0.54 * math.exp(recoil_exp)
    return min(1.0e12, p_recoil_atm * 101.325)


def _binary_extent(pred, lo, hi, iters=18):
    """Largest value in [lo, hi] where pred is True (pred monotonic True→False)."""
    if not pred(lo):
        return 0.0
    if pred(hi):
        return hi
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        if pred(mid):
            lo = mid
        else:
            hi = mid
    return lo


def sample_thermal_slice(eval_T, axis_a, axis_b, na, nb):
    temps = []
    for ia in range(na):
        a = axis_a[0] + (axis_a[1] - axis_a[0]) * ia / max(1, na - 1)
        for ib in range(nb):
            b = axis_b[0] + (axis_b[1] - axis_b[0]) * ib / max(1, nb - 1)
            temps.append(round(float(eval_T(a, b)), 1))
    return temps


def _normalize_absorption_model(absorption_model: str | None) -> str:
    if absorption_model is None or (isinstance(absorption_model, str) and not absorption_model.strip()):
        return ABSORPTION_MODEL_FLAT
    if not isinstance(absorption_model, str):
        raise ValueError(f"Unsupported LPBF absorption model: {absorption_model!r}")
    key = absorption_model.strip().lower().replace("_", "-")
    if key in ("flat", "flat-plate"):
        return ABSORPTION_MODEL_FLAT
    if key == ABSORPTION_MODEL_POWDER_RAYTRACE:
        return ABSORPTION_MODEL_POWDER_RAYTRACE
    raise ValueError(f"Unsupported LPBF absorption model: {absorption_model!r} (expected one of {ABSORPTION_MODELS})")


def _normalize_thermal_slice_backend(backend: str | None) -> str:
    if backend is None or (isinstance(backend, str) and not backend.strip()):
        return "cpu"
    key = backend.strip().lower() if isinstance(backend, str) else None
    if key not in THERMAL_SLICE_BACKENDS:
        raise ValueError(f"Unsupported LPBF thermal slice backend: {backend!r} (expected one of {THERMAL_SLICE_BACKENDS})")
    return key


def _axial_peak_x(T_field, lo_x, hi_x, n_scan=97, refine_iters=40):
    """x of the axial (y = z = 0) temperature maximum on [lo_x, hi_x]: a uniform scan, then a ternary
    refinement inside the bracketing cells. The regularised moving-source fields peak BEHIND the
    beam centre at high speed, so x = 0 is not a safe anchor for the liquidus extent search."""
    xs = [lo_x + (hi_x - lo_x) * i / (n_scan - 1) for i in range(n_scan)]
    temps = [float(T_field(x, 0.0, 0.0)) for x in xs]
    i_best = max(range(n_scan), key=lambda i: temps[i])
    a = xs[max(0, i_best - 1)]
    b = xs[min(n_scan - 1, i_best + 1)]
    for _ in range(refine_iters):
        m1 = a + (b - a) / 3.0
        m2 = b - (b - a) / 3.0
        if T_field(m1, 0.0, 0.0) < T_field(m2, 0.0, 0.0):
            a = m1
        else:
            b = m2
    x_peak = 0.5 * (a + b)
    if float(T_field(x_peak, 0.0, 0.0)) < float(T_field(0.0, 0.0, 0.0)):
        x_peak = 0.0
    return x_peak


def _liquidus_extent(T_field, T_liq, x_peak, search_len, search_half_w, search_depth, d_beam, r_beam,
                     w_analytical, normalized_enthalpy):
    """Liquidus extents of a conduction field anchored at its axial peak x_peak (moved verbatim out of
    calculate_meltpool_physics so the Eagar–Tsai balling companion runs the identical search)."""
    # 4. Liquidus extents from the conduction field (Rosenthal or Eagar–Tsai). The search box is a
    # seed, not a cap: when the isotherm is still liquid at the box edge the box is doubled (up to
    # 8x); if it is still at the edge after that the status says so instead of calling it computed.
    extent_flags = []

    def _extent_with_growth(pred, hi, label):
        bound = hi
        for _ in range(3):
            value = _binary_extent(pred, 0.0, bound)
            if value < bound:
                return value
            bound *= 2.0
        value = _binary_extent(pred, 0.0, bound)
        if value >= bound:
            extent_flags.append(label)
        return value

    # Probes are anchored at the axial peak x_peak and search outward (front/rear distances are
    # measured from x_peak); a field that is below liquidus even at its peak is genuinely unmelted.
    front_rel = _extent_with_growth(lambda s: T_field(x_peak + s, 0.0, 0.0) >= T_liq, search_len,
                                    "front-search-limit")
    rear_rel = _extent_with_growth(lambda s: T_field(x_peak - s, 0.0, 0.0) >= T_liq, search_len * 1.4,
                                   "rear-search-limit")
    if float(T_field(x_peak, 0.0, 0.0)) >= T_liq:
        x_front = x_peak + front_rel
        x_rear = rear_rel - x_peak
    else:
        x_front = 0.0
        x_rear = 0.0
    half_w = 0.0
    for frac in (-0.35, -0.15, -0.05, 0.0, 0.35):
        x_probe = x_peak + (frac * rear_rel if frac <= 0.0 else frac * front_rel)
        half_w = max(half_w, _extent_with_growth(lambda y, x_probe=x_probe: T_field(x_probe, y, 0.0) >= T_liq,
                                                 search_half_w, "width-search-limit"))
    d_iso = 0.0
    for frac in (-0.25, -0.1, -0.04, 0.0):
        x_probe = x_peak + frac * rear_rel
        d_iso = max(d_iso, _extent_with_growth(lambda z, x_probe=x_probe: T_field(x_probe, 0.0, z) >= T_liq,
                                               search_depth, "depth-search-limit"))

    # The conduction field did not produce a resolvable liquidus extent (no melt or a pool below the
    # search resolution): the width/depth below are a HEURISTIC substitute, reported as such in
    # meltPoolGeometry.extentStatus, never presented as a computed isotherm.
    extent_status = "computed"
    extent_note = None
    d_iso_isotherm = d_iso
    if half_w < 8e-6 or d_iso < 3e-6:
        extent_status = "heuristic-width-fallback"
        extent_note = ("The conduction field has no resolvable liquidus extent at these inputs (half-width "
                       f"{half_w*1e6:.1f} um, depth {d_iso*1e6:.1f} um before substitution); width/depth/length are "
                       "the screening heuristic sqrt(w_analytical^2 + (0.65 d_beam)^2) with the depth set equal to the "
                       "half width (Rosenthal symmetry: the point-source field is symmetric in y and z, so its liquidus "
                       "depth equals its half width; an upper bound for distributed sources, King 2014 Sec. 5.2 "
                       "d <= w/2 in conduction mode), not a computed isotherm. Treat this geometry as not resolved.")
        w_fb = math.sqrt(max(1e-12, w_analytical ** 2 + (0.65 * d_beam) ** 2))
        half_w = max(half_w, w_fb / 2.0)
        # P1 (2026-10-11): floor ratio 1.0 replaces the uncited 0.38 + 0.10 min(1, dH/hs / 15).
        d_iso = max(d_iso, half_w)
        if x_front < 1e-6:
            x_front = r_beam * 0.45
        if x_rear < 1e-6:
            x_rear = max(w_fb, half_w * 2.2)

    if extent_status == "computed" and 2.0 * half_w < d_beam * 0.55:
        extent_status = "width-floor-applied"
        extent_note = (f"The computed liquidus half-width ({half_w*1e6:.1f} um) is below the screening width floor "
                       f"0.55 x beam diameter ({0.55*d_beam*1e6:.1f} um); the reported width is the floor, not the "
                       "computed isotherm. Treat the width as not resolved.")
    if extent_status == "computed" and extent_flags:
        extent_status = "search-box-limited"
        extent_note = ("The liquidus isotherm was still liquid at the edge of the (8x-grown) search box for: "
                       + ", ".join(sorted(set(extent_flags)))
                       + "; the reported extent is a lower bound, not a converged isotherm length.")
    w_melt_m = max(2.0 * half_w, d_beam * 0.55)
    d_iso = max(d_iso, 4e-6)
    # Uncapped Rosenthal length (no Peclet fake ceiling). Floor only for numerical sanity.
    l_melt_m = max(x_front + x_rear, d_beam)
    x_front = max(x_front, r_beam * 0.35)
    x_rear = max(r_beam * 0.8, l_melt_m - x_front)
    l_melt_m = x_front + x_rear
    # d_iso_isotherm_m (depth before any floor) and half_w_m (after the fallback width substitution) are internal
    # diagnostics for the frozen pre-P1 research kernel; nothing served reads them.
    return {"extent_status": extent_status, "extent_note": extent_note, "w_melt_m": w_melt_m, "d_iso": d_iso,
            "x_front": x_front, "x_rear": x_rear, "l_melt_m": l_melt_m,
            "d_iso_isotherm_m": d_iso_isotherm, "half_w_m": half_w}


def _eagar_tsai_companion(T_preheat, P_laser, eta_base, k_th, alpha_th, rho, cp, r_beam, d_beam, v_scan, T_liq,
                          fabbro_depth_m, normalized_enthalpy):
    """Eagar–Tsai liquidus L/W/D for the balling screen when the requested kernel is not Eagar–Tsai.

    Same inputs as an eagar-tsai run of calculate_meltpool_physics (absorbed power eta_base*P, mushy-blend
    k/alpha, depth = max(isotherm depth, Fabbro leg)) and the same evaluation sequence on a fresh field, so
    the numbers equal that run's meltPoolGeometry. Returns (length_um, width_um, depth_um, extentStatus).
    """
    P_geom = eta_base * P_laser
    field = EagarTsaiField(T_preheat, P_geom, k_th, alpha_th, r_beam).bind_speed(v_scan)
    T_field = field.temperature_C
    denom_thermal = rho * cp * max(50.0, T_liq - T_preheat) * v_scan
    w_analytical = math.sqrt(max(1e-12, (8.0 / (math.pi * math.e)) * (P_geom / denom_thermal)))
    search_half_w = max(d_beam * 1.8, w_analytical * 1.8, 50e-6)
    search_len = max(d_beam * 3.0, w_analytical * 4.5, 80e-6)
    search_depth = max(d_beam * 2.2, w_analytical * 2.0, 40e-6, fabbro_depth_m * 1.35)
    T_field(0.0, 0.0, 0.0)
    x_peak = _axial_peak_x(T_field, -search_len * 1.4 * 8.0, search_len)
    T_field(x_peak, 0.0, 0.0)
    ext = _liquidus_extent(T_field, T_liq, x_peak, search_len, search_half_w, search_depth, d_beam, r_beam,
                           w_analytical, normalized_enthalpy)
    d_iso = max(ext["d_iso"], 4e-6)
    d_melt_m = max(d_iso, fabbro_depth_m)
    return ext["l_melt_m"] * 1e6, ext["w_melt_m"] * 1e6, d_melt_m * 1e6, ext["extent_status"]


def _normalize_heat_source(heat_source: str | None) -> str:
    if heat_source is None or (isinstance(heat_source, str) and not heat_source.strip()):
        return "rosenthal"
    if not isinstance(heat_source, str):
        raise ValueError(f"Unsupported LPBF heat source: {heat_source!r}")
    key = heat_source.strip().lower().replace("_", "-")
    if key in ("rosenthal", "rosenthal-screening", "rosenthal-screening-v1"):
        return "rosenthal"
    if key in ("eagar-tsai", "eagar-tsai-v2", "et", "eager-tsai"):
        return "eagar-tsai"
    if key in ("goldak", "goldak-double-ellipsoid", "goldak-half-space-v3"):
        return "goldak"
    if key in ("eagar-tsai-v1", "goldak-v1", "goldak-total-power-v2"):
        # Retired kernel ids are never run silently as the corrected kernel.
        current = "eagar-tsai-v2" if key.startswith("eagar") else "goldak-half-space-v3"
        raise ValueError(f"Retired LPBF heat-source id {heat_source!r}: its kernel was replaced by the "
                         f"corrected {current!r} (planned corrected-physics bump); request {current!r} or the "
                         f"unversioned name explicitly")
    raise ValueError(f"Unsupported LPBF heat source: {heat_source!r}")


def calculate_meltpool_physics(
    material_name: str,
    laser_power_W: float,
    scan_speed_mm_s: float,
    beam_diameter_um: float,
    preheat_temp_C: float = 80.0,
    layer_thickness_um: float = 40.0,
    hatch_spacing_um: float = 100.0,
    laser_wavelength: str = "IR_1064nm",
    incline_angle_deg: float = 0.0,
    process_seed: int = 42,
    prop_overrides: dict | None = None,
    heat_source: str | None = None,
    sulfur_ppm: float = 15.0,
    absorption_model: str | None = None,
    thermal_slice_backend: str | None = None,
):
    """
    Evaluates 3D multi-regime melt pool physics, geometry, defects, and microstructure.
    Optional prop_overrides merge onto the resolved thermophysical dict (UQ / AM-Bench).
    heat_source: "rosenthal" (Build Job default), "eagar-tsai", or "goldak" (Melt Pool lab).
    sulfur_ppm: Heiple–Roper screening only (does not refit W/D or re-score Build Job).
    absorption_model: "flat-plate" (default) or "powder-raytrace" (explicit GPU opt-in; ΔH/hs stays flat).
    thermal_slice_backend: "cpu" (default) or "warp" (explicit GPU opt-in, Rosenthal only).
    """
    if not isinstance(material_name, str) or not material_name.strip():
        raise ValueError(f"Unsupported LPBF material identity: {material_name!r}")
    source = _normalize_heat_source(heat_source)
    absorption_model = _normalize_absorption_model(absorption_model)
    thermal_slice_backend = _normalize_thermal_slice_backend(thermal_slice_backend)
    if thermal_slice_backend == "warp" and source != "rosenthal":
        raise ValueError("thermal_slice_backend='warp' is available for the Rosenthal field only")
    base = thermal_props(material_name) or SECONDARY_THERMOPHYSICAL_DB.get(material_name)
    if base is None:
        raise ValueError(f"Unsupported LPBF material identity: {material_name!r}")
    props = dict(base)
    if prop_overrides:
        props.update(prop_overrides)
    
    process_values = {}
    for name, value in (
        ("laser_power_W", laser_power_W),
        ("scan_speed_mm_s", scan_speed_mm_s),
        ("beam_diameter_um", beam_diameter_um),
        ("layer_thickness_um", layer_thickness_um),
        ("hatch_spacing_um", hatch_spacing_um),
    ):
        try:
            numeric_value = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name} must be finite and positive") from exc
        if not math.isfinite(numeric_value) or numeric_value <= 0:
            raise ValueError(f"{name} must be finite and positive")
        process_values[name] = numeric_value

    P_laser = process_values["laser_power_W"]
    scan_speed_mm_s = process_values["scan_speed_mm_s"]
    beam_diameter_um = process_values["beam_diameter_um"]
    layer_thickness_um = process_values["layer_thickness_um"]
    hatch_spacing_um = process_values["hatch_spacing_um"]
    v_scan = scan_speed_mm_s * 1e-3  # m/s
    d_beam = beam_diameter_um * 1e-6  # m
    r_beam = d_beam / 2.0
    T_preheat = float(preheat_temp_C)
    t_layer_m = float(layer_thickness_um) * 1e-6
    hatch_m = float(hatch_spacing_um) * 1e-6
    theta_rad = math.radians(float(incline_angle_deg))
    cos_theta = max(0.05, math.cos(theta_rad))  # avoid zero R on vertical walls

    T_liq = props["liquidus_C"]
    T_sol = props["solidus_C"]
    T_vap = props["boiling_C"]
    rho = props["density_kg_m3"]
    k_s = props["thermal_conductivity_W_mK"]
    k_l = float(props.get("thermal_conductivity_liquid_W_mK", k_s))
    cp_s = props["specific_heat_J_kgK"]
    cp_l = float(props.get("specific_heat_liquid_J_kgK", cp_s))
    # Effective mushy-zone k/Cp for Rosenthal geometry (equal-weight solid↔liquid blend).
    k_th = 0.5 * (k_s + k_l)
    cp = 0.5 * (cp_s + cp_l)
    alpha_th = k_th / (rho * cp)  # Thermal diffusivity (m^2/s)
    # King ΔH/hs stays on solid props (literature onset ~30 is solid-based).
    alpha_solid = k_s / (rho * cp_s)

    # Use only wavelength/property pairs that exist in the material snapshot.
    wavelength_property = {
        "IR_1064nm": "absorptivity_IR",
        "Green_515nm": "absorptivity_Green",
    }.get(laser_wavelength)
    if wavelength_property is None:
        raise ValueError(f"Unsupported LPBF laser wavelength: {laser_wavelength!r}")
    if wavelength_property not in props:
        raise ValueError(
            f"Material {material_name!r} has no absorptivity for {laser_wavelength}"
        )
    eta_base_flat = float(props[wavelength_property])

    if absorption_model == ABSORPTION_MODEL_POWDER_RAYTRACE:
        # Explicit opt-in only; import or CUDA errors propagate instead of silently changing physics.
        from powder_bed_raytracer import calculate_powder_bed_absorptivity
        powder_metrics = calculate_powder_bed_absorptivity(
            beam_radius_um=r_beam * 1e6,
            base_absorptivity=eta_base_flat
        )
        eta_base = float(powder_metrics["effective_absorptivity"])
    else:
        eta_base = eta_base_flat

    # 1. Volumetric and Linear Energy Densities
    ved_J_mm3 = P_laser / (
        scan_speed_mm_s
        * (hatch_spacing_um * 1e-3)
        * (layer_thickness_um * 1e-3)
    )
    led_J_m = P_laser / v_scan

    # 2. Normalized Enthalpy (King / Rubenchik) + peak intensity I0 — solid k, Cp
    # King et al. 2014 (doi 10.1016/j.jmatprotec.2014.06.005) Eq. (2.6), Hann calibration, pi INSIDE
    # the root: dH/hs = A P / (hs sqrt(pi D u sigma^3)), A = flat absorptivity. Repo convention differs
    # from King's calibration: r = 1/e^2 radius (King sigma = r/2), hs = rho cp_s (T_liq - T0), D = solid
    # diffusivity; the 15/20 thresholds (IN625: 13.6) are derived in this convention (see REGIME_THRESHOLD_BASIS).
    # dH always uses the flat absorptivity, also when the powder ray tracer is requested.
    enthalpy_denom = rho * cp_s * max(50.0, T_liq - T_preheat) * math.sqrt(math.pi * alpha_solid * v_scan * (r_beam ** 3))
    normalized_enthalpy = (eta_base_flat * P_laser) / max(1e-9, enthalpy_denom)
    # Gaussian 1/e² diameter d=2w: I0 = 2P/(πw²) = 8P/(πd²).
    peak_intensity_W_m2 = (8.0 * P_laser) / (math.pi * d_beam ** 2)
    peak_intensity_MW_cm2 = peak_intensity_W_m2 * 1e-10

    # 3. Field power, every kernel (P1, 2026-10-11): P_field = A P with the flat (or, on explicit opt-in,
    # ray-traced) conduction absorptivity. Eagar & Tsai (1983) and Goldak (1984) take the absorbed power as Q;
    # Rubenchik 2018 Sec. 3.1 and Gan 2021 SI Method 3 use one absorptivity in the conduction scaling. The former
    # Rosenthal-only multi-reflection ramp eta_eff = 1 - (1 - A)^n (uncited) is removed: no kernel represents the
    # measured absorptance rise in transition and keyhole mode (EFFECTIVE_ABSORPTIVITY_BASIS).
    eta_eff = eta_base
    # Latent heat of fusion is excluded from the conduction field of every kernel (Rubenchik 2018 Sec. 3.1,
    # Gan 2021 SI Method 3), from the index hs and from the Fabbro leg; the former Rosenthal-only factor
    # 1/(1 + 0.55 St) (uncited) is removed. stefanNumber stays served as a descriptive number only.
    Lf = props["latent_heat_fusion_J_kg"]
    stefan = Lf / max(1.0, cp * max(50.0, T_liq - T_preheat))
    latent_heat_power_factor = 1.0
    P_absorbed = eta_base * P_laser
    # Fabbro (Appl. Sci. 2020, eq. 2) defines A(R), the aspect-ratio-dependent keyhole absorptivity, which is NOT
    # modelled here: the flat value is passed, a disclosed lower bound (FABBRO_BASIS).
    A_fabbro = eta_base_flat
    P_geom = P_absorbed * latent_heat_power_factor
    r_reg = max(r_beam / math.sqrt(2.0), 8e-6)

    goldak_seed = seed_goldak_axes(r_beam)
    if source == "eagar-tsai":
        et_field = EagarTsaiField(T_preheat, P_geom, k_th, alpha_th, r_beam).bind_speed(v_scan)

        def T_field(x_m, y_m, z_m):
            return et_field.temperature_C(x_m, y_m, z_m)

        heat_source_id = EAGAR_TSAI_MODEL_ID
    elif source == "goldak":
        gk_field = GoldakField(
            T_preheat, P_geom, rho, cp, alpha_th,
            goldak_seed["af_m"], goldak_seed["ar_m"], goldak_seed["b_m"], goldak_seed["c_m"],
        ).bind_speed(v_scan)

        def T_field(x_m, y_m, z_m):
            return gk_field.temperature_C(x_m, y_m, z_m)

        heat_source_id = GOLDAK_MODEL_ID
    else:
        def T_field(x_m, y_m, z_m):
            return rosenthal_temperature_C(x_m, y_m, z_m, T_preheat, P_geom, k_th, v_scan, alpha_th, r_reg)

        heat_source_id = "rosenthal-screening-v1"

    fabbro = fabbro_keyhole_depth_m(
        P_laser, v_scan, d_beam, k_s, alpha_solid, T_vap, T_preheat, A_fabbro, normalized_enthalpy
    )

    # Seed search box from the high-speed Rosenthal width scale
    denom_thermal = rho * cp * max(50.0, T_liq - T_preheat) * v_scan
    w_analytical = math.sqrt(max(1e-12, (8.0 / (math.pi * math.e)) * (P_geom / denom_thermal)))
    search_half_w = max(d_beam * 1.8, w_analytical * 1.8, 50e-6)
    search_len = max(d_beam * 3.0, w_analytical * 4.5, 80e-6)
    search_depth = max(d_beam * 2.2, w_analytical * 2.0, 40e-6, fabbro["depth_m"] * 1.35)

    # Reported peak / surface proxy: beam-centre value T(0,0,0) as before the tier-2 bump (recoil,
    # Marangoni and denudation read it). No artificial 3900 °C display ceiling (may exceed boiling).
    t_peak_C = float(T_field(0.0, 0.0, 0.0))
    # Axial field maximum: only the extent search and the cross-section plane are anchored there (it
    # lies behind x = 0 at high speed); its value is reported separately as axialFieldMaximum_C.
    x_peak = _axial_peak_x(T_field, -search_len * 1.4 * 8.0, search_len)
    t_axial_max_C = max(t_peak_C, float(T_field(x_peak, 0.0, 0.0)))

    # 4. Liquidus extents from the conduction field (Rosenthal, Eagar–Tsai or Goldak): _liquidus_extent.
    ext = _liquidus_extent(T_field, T_liq, x_peak, search_len, search_half_w, search_depth, d_beam, r_beam,
                           w_analytical, normalized_enthalpy)
    extent_status = ext["extent_status"]
    extent_note = ext["extent_note"]
    w_melt_m = ext["w_melt_m"]
    d_iso = ext["d_iso"]
    x_front = ext["x_front"]
    x_rear = ext["x_rear"]
    l_melt_m = ext["l_melt_m"]

    # One depth path for every kernel (P1): depth = max(d_iso, e_kh), Fabbro 2020 eq. 6 to 7 / Sec. 3 reading
    # (below the threshold the pool is the conduction pool, above it the keyhole depth). The former Rosenthal-only
    # increment d_iso*(0.15+0.55 t) / d_iso*(0.85+0.55 log10(...)) (uncited) is removed.
    extra = max(0.0, fabbro["depth_m"] - d_iso)
    keyhole_depth_um = extra * 1e6

    if normalized_enthalpy < POROSITY_SCREEN_NEGLIGIBLE_BELOW:
        keyhole_porosity_risk = ("Negligible (legacy screening level, dH/hs < 15; porosity unresolved: Zhao 2020 "
                                 "0/35 pore conditions below 15 is not evidence of safety)")
    elif normalized_enthalpy < POROSITY_SCREEN_HIGH_AT:
        keyhole_porosity_risk = ("Possible (legacy screening level, 15 <= dH/hs < 30; porosity unresolved by this "
                                 "index: Zhao 2020 Ti-6Al-4V pores observed at dH/hs 16-28 for v <= 445 mm/s)")
    else:
        keyhole_porosity_risk = ("High (legacy screening level, dH/hs >= 30; porosity unresolved, not a porosity "
                                 "boundary: Zhao 2020 Ti-6Al-4V stable keyholes up to dH/hs 62 at high speed)")

    d_melt_m = max(d_iso, fabbro["depth_m"])
    regime = classify_enthalpy_regime(normalized_enthalpy, material_name)

    w_melt_um = w_melt_m * 1e6
    d_melt_um = d_melt_m * 1e6
    l_melt_um = l_melt_m * 1e6
    peclet_number = (v_scan * w_melt_m) / (2.0 * alpha_th)

    goldak_af_um = max(4.0, x_front * 1e6)
    goldak_ar_um = max(4.0, x_rear * 1e6)
    goldak_b_um = w_melt_um / 2.0
    goldak_c_um = d_melt_um

    # 8. Recoil from evaporative surface T (Anisimov/Knight 0.54 Psat). Field peak stays
    # uncapped (PROOF 015). Conduction singularities of 10^4 °C are not a wall temperature.
    M_molar = float(props.get("M_molar_kg_mol", 0.055))
    delta_H_vap = props["latent_heat_vap_J_kg"] * M_molar
    t_surface_C = min(float(t_peak_C), float(T_vap))
    # Wave B D1: label what the reported peak is. It is the beam-centre value T(0,0,0) of a conduction
    # field with no evaporation sink, so above T_vap it is not a physical wall temperature.
    if source in ("eagar-tsai", "goldak"):
        peak_temperature_basis = "distributed-source-conduction-centre-value"
        peak_temperature_note = ("beam-centre value T(0,0,0) of the uncapped Eagar-Tsai/Goldak conduction field "
                                 "(no evaporation sink); above T_vap it is not a wall temperature. Recoil and "
                                 "Marangoni use surfaceTemperature_C = min(peak, T_vap).")
    else:
        peak_temperature_basis = "regularised-singular-source-value"
        peak_temperature_note = ("beam-centre value T(0,0,0) of the Rosenthal (1946) point source with only the 1/R "
                                 "prefactor regularised at r_reg (= axial maximum for Rosenthal after Wave B LA-2), "
                                 "i.e. T0 + P/(2 pi k r_reg): a regularised singular-source value, not a wall "
                                 "temperature. Recoil and Marangoni use surfaceTemperature_C = min(peak, T_vap).")
    surface_temperature_basis = ("saturated at T_vap: " + peak_temperature_basis.replace("-", " ")
                                 if float(t_peak_C) >= float(T_vap) else "beam-centre field value below T_vap")
    p_recoil_kPa = knight_recoil_pressure_kPa(t_surface_C, T_vap, delta_H_vap)

    ma = marangoni_screening(
        props["d_gamma_dT_N_mK"],
        props["viscosity_Pa_s"],
        alpha_th,
        float(props.get("density_liquid_kg_m3", rho)),
        w_melt_m / 2.0,
        t_surface_C,
        T_liq,
        sulfur_ppm=float(sulfur_ppm),
    )
    marangoni_number = ma["marangoniNumber"]

    # 9. Defect Diagnostics
    # A) Lack of Fusion — Tang et al.: (h/W)^2 + (t/D)^2 ≤ 1 for full consolidation
    h_um = max(1.0, float(hatch_spacing_um))
    t_um = max(1.0, float(layer_thickness_um))
    h_over_w = h_um / max(1.0, w_melt_um)
    t_over_d = t_um / max(1.0, d_melt_um)
    lof_criterion_val = (h_over_w ** 2) + (t_over_d ** 2)
    w_over_h = w_melt_um / h_um
    d_over_t = d_melt_um / t_um

    if lof_criterion_val > 1.0:
        lof_risk = "Severe Lack of Fusion (Tang index > 1 — inter-track/layer unmelt)"
        lof_status = "Fail"
    elif lof_criterion_val > 0.80:
        lof_risk = "Marginal Overlap (Tang index approaching 1)"
        lof_status = "Warning"
    else:
        lof_risk = "Full Fusion Bonding (Tang (h/W)^2+(t/D)^2 ≤ 0.80)"
        lof_status = "Pass"

    # B) Balling / track-instability screen (lpbf_defect_diagnostics.balling_screen): Eagar–Tsai liquidus
    # L/W whatever kernel was requested (the point-source Rosenthal L/W has no beam radius). Replaces the
    # frozen steady-Rosenthal L/W > 3.8 flag (planned bump on top of Wave B f3ba9896).
    aspect_L_over_W = l_melt_um / max(1.0, w_melt_um)
    if source == "eagar-tsai":
        et_extent = (l_melt_um, w_melt_um, d_melt_um, extent_status)
    else:
        et_extent = _eagar_tsai_companion(T_preheat, P_laser, eta_base, k_th, alpha_th, rho, cp, r_beam, d_beam,
                                          v_scan, T_liq, fabbro["depth_m"], normalized_enthalpy)
    balling = balling_screen(*et_extent)
    if balling["band"] == "high":
        balling_risk = (f"High Balling Risk (Eagar-Tsai L/W {balling['lengthToWidth']:.2f} > "
                        f"{balling['highThreshold']}; empirical 316L-calibrated screen)")
    elif balling["band"] == "moderate":
        balling_risk = (f"Moderate (Eagar-Tsai L/W {balling['lengthToWidth']:.2f} > {balling['moderateThreshold']:.2f}, "
                        "Gusarov/Yadroitsev bound; advisory)")
    elif balling["band"] == "stable":
        balling_risk = (f"Stable Continuous Track (Eagar-Tsai L/W {balling['lengthToWidth']:.2f} <= "
                        f"{balling['moderateThreshold']:.2f})")
    else:
        balling_risk = f"Unavailable (Eagar-Tsai extent {balling['extentStatus']}; no balling band)"

    # C) Powder Denudation & Spatter Entrainment Width
    # Denudation width w_denude ~ W * (1 + 0.45 * (P_recoil / 50))
    denudation_width_um = w_melt_um * (1.0 + 0.35 * min(3.0, min(1e6, p_recoil_kPa) / 30.0))

    # 10. Solidification kinetics from the liquidus isotherm (G = |∇T|, R = v n_x).
    sol = evaluate_solidification(
        T_field,
        T_liq=T_liq,
        T_sol=T_sol,
        t_surface=t_surface_C,
        v_scan=v_scan,
        x_rear=x_rear,
        x_front=x_front,
        search_depth=search_depth,
        r_beam=r_beam,
        cos_theta=cos_theta,
        pdas_A1=float(props.get("pdas_A1", 75.0)),
        sdas_B1=float(props.get("sdas_B1", 40.0)),
        material_name=material_name,
    )
    thermal_gradient_G_K_m = float(sol["thermalGradient_G_K_m"])
    solidification_rate_R_m_s = float(sol["solidificationRate_R_m_s"])
    cooling_rate_K_s = float(sol["coolingRate_K_s"])
    g_over_r = float(sol["g_over_r_ratio"])
    morphology = str(sol["microstructureMorphology"])
    pdas_um = float(sol["primaryDendriteArmSpacing_PDAS_um"])
    sdas_um = float(sol["secondaryDendriteArmSpacing_SDAS_um"])

    # 11. Residual Stress & Recoater Crash Upper Bound (no artificial 1200 MPa ceiling)
    e_gpa = props["youngs_modulus_GPa"]
    alpha_exp = props["thermal_expansion_1_K"]
    nu = props["poissons_ratio"]
    delta_t_stress = max(10.0, T_sol - T_preheat)
    elastic_stress_max_mpa = (e_gpa * 1e3 * alpha_exp * delta_t_stress) / max(0.01, 1.0 - nu)
    effective_residual_stress_mpa = elastic_stress_max_mpa * 0.72
    distortion_index = (effective_residual_stress_mpa * (float(layer_thickness_um) / 40.0)) / 420.0
    # The index has no scan-dependent term (alloy, preheat and layer thickness only), so no recoater
    # High/Moderate/Low band is assigned from it here; the value itself is unchanged.
    recoater_risk = (f"Not evaluated from scan parameters (alloy/layer/preheat-only distortion index "
                     f"{distortion_index:.2f})")

    # 12. Geometric 2D contours from liquidus isolines, scaled by depth / d_iso (1 below the Fabbro leg, e_kh / d_iso
    # where the leg exceeds the isotherm depth)
    depth_scale = d_melt_m / max(1e-9, d_iso)
    num_pts = 48
    top_down_contour = []
    for i in range(num_pts + 1):
        s = i / num_pts
        x_m = goldak_af_um * 1e-6 - (goldak_af_um + goldak_ar_um) * 1e-6 * s
        y_half = _binary_extent(lambda y: T_field(x_m, y, 0.0) >= T_liq, 0.0, search_half_w)
        x_um = x_m * 1e6
        y_um = y_half * 1e6
        top_down_contour.append({"x_um": round(float(x_um), 1), "y_um": round(float(y_um), 1)})
    # Close teardrop with the opposite (+y then walk back already one-sided; mirror)
    mirrored = [{"x_um": pt["x_um"], "y_um": -pt["y_um"]} for pt in reversed(top_down_contour[1:-1])]
    top_down_contour = top_down_contour + mirrored

    longitudinal_contour = []
    for i in range(num_pts + 1):
        s = i / num_pts
        x_m = goldak_af_um * 1e-6 - (goldak_af_um + goldak_ar_um) * 1e-6 * s
        z_iso = _binary_extent(lambda z: T_field(x_m, 0.0, z) >= T_liq, 0.0, search_depth)
        z_depth = z_iso * depth_scale * 1e6
        longitudinal_contour.append({
            "x_um": round(float(x_m * 1e6), 1),
            "z_depth_um": round(float(z_depth), 1),
            "isKeyhole": keyhole_depth_um > 0 and abs(x_m) < (r_beam * 0.9)
        })

    transverse_contour = []
    for i in range(33):
        phi = (math.pi * i) / 32.0
        y_m = (goldak_b_um * 1e-6) * math.cos(phi)
        # Cross-section plane at the axial peak x_peak (x = 0 when the field peaks at the beam centre),
        # consistent with the anchored extent search; a pool behind the beam is otherwise missed.
        z_iso = _binary_extent(lambda z: T_field(x_peak, y_m, z) >= T_liq, 0.0, search_depth)
        # P1: the contour follows depth_scale alone (the former sin(phi)^0.75 taper above dH/hs 30 went with the
        # removed increment constant).
        z_pt = z_iso * depth_scale
        transverse_contour.append({
            "y_um": round(float(y_m * 1e6), 1),
            "z_depth_um": round(float(z_pt * 1e6), 1)
        })

    T_haz = T_sol * 0.70
    nx_s, nz_s, ny_s = 36, 24, 28
    x_span = (-goldak_ar_um * 1.15, goldak_af_um * 1.15)
    y_span = (-goldak_b_um * 1.25, goldak_b_um * 1.25)
    z_span = (0.0, d_melt_um * 1.25)

    def T_xz(x_um, z_um):
        return T_field(x_um * 1e-6, 0.0, z_um * 1e-6)

    def T_yz(y_um, z_um):
        return T_field(x_peak, y_um * 1e-6, z_um * 1e-6)

    if thermal_slice_backend == "warp":
        # Explicit opt-in only (float32 GPU sampler, not bit-equal to the CPU sampler); errors propagate.
        from warp_thermal_solver import compute_rosenthal_slice_warp
        x_span_m = (x_span[0] * 1e-6, x_span[1] * 1e-6)
        z_span_m = (z_span[0] * 1e-6, z_span[1] * 1e-6)
        y_span_m = (y_span[0] * 1e-6, y_span[1] * 1e-6)

        slice_xz = compute_rosenthal_slice_warp(x_span_m, z_span_m, nx_s, nz_s, 1, 0.0, T_preheat, P_geom, k_th, v_scan, alpha_th, r_reg)
        slice_yz = compute_rosenthal_slice_warp(y_span_m, z_span_m, ny_s, nz_s, 2, x_peak, T_preheat, P_geom, k_th, v_scan, alpha_th, r_reg)
    else:
        slice_xz = sample_thermal_slice(T_xz, x_span, z_span, nx_s, nz_s)
        slice_yz = sample_thermal_slice(T_yz, y_span, z_span, ny_s, nz_s)

    thermal_slices = {
        "liquidus_C": T_liq,
        "solidus_C": T_sol,
        "haz_C": round(T_haz, 1),
        "xz": {
            "nx": nx_s,
            "nz": nz_s,
            "xMin_um": round(x_span[0], 1),
            "xMax_um": round(x_span[1], 1),
            "zMin_um": 0.0,
            "zMax_um": round(z_span[1], 1),
            "T_C": slice_xz
        },
        "yz": {
            "ny": ny_s,
            "nz": nz_s,
            "yMin_um": round(y_span[0], 1),
            "yMax_um": round(y_span[1], 1),
            "zMin_um": 0.0,
            "zMax_um": round(z_span[1], 1),
            "T_C": slice_yz
        }
    }

    # Transverse Multi-Track Overlap with left & right hatch lines
    hatch_val_um = float(hatch_spacing_um)
    overlap_tracks = [
        {"trackId": "Left Track (-1)", "y_center_um": -hatch_val_um, "contour": [{"y_um": round(pt["y_um"] - hatch_val_um, 1), "z_depth_um": pt["z_depth_um"]} for pt in transverse_contour]},
        {"trackId": "Current Track (0)", "y_center_um": 0.0, "contour": transverse_contour},
        {"trackId": "Right Track (+1)", "y_center_um": hatch_val_um, "contour": [{"y_um": round(pt["y_um"] + hatch_val_um, 1), "z_depth_um": pt["z_depth_um"]} for pt in transverse_contour]}
    ]

    # 13. Dynamic P-V Process Window Map (2D Grid: Power 50-600W, Speed 200-2500 mm/s)
    process_map_grid = []
    keyhole_cut = regime_keyhole_cut(material_name)
    p_steps = np.array([80, 150, 220, 300, 380, 460, 540], dtype=np.float64)
    v_steps = np.array([300, 600, 900, 1200, 1600, 2000, 2400], dtype=np.float64)

    for p_val in p_steps:
        for v_val in v_steps:
            # Quick evaluation of regime
            v_m = float(v_val) * 1e-3
            denom_th = rho * cp_s * (T_liq - T_preheat) * math.sqrt(math.pi * alpha_solid * v_m * (r_beam ** 3))
            enth = (eta_base_flat * float(p_val)) / max(1e-9, denom_th)
            
            # Width proxy (P1): the flat conduction absorptivity for every cell (the former 1-(1-A)^2.2 ramp above
            # the transition cut was uncited).
            eff_p = eta_base * float(p_val)
            w_m = math.sqrt(max(1e-12, (8.0 / (math.pi * math.e)) * (eff_p / (rho * cp * max(50.0, T_liq - T_preheat) * v_m))) + d_beam ** 2)
            w_um = w_m * 1e6

            # Depth proxy (P1): max(conduction bound w/2, Fabbro leg) with the same leg and onset ramp as the operating
            # point. King et al. 2014 Sec. 5.2 define keyhole mode by d > w/2, so a conduction pool has d <= w/2 and
            # the leg takes over where it exceeds that bound. The former 0.45 / 0.70 / 1.15 width multiples were uncited.
            cell_fabbro = fabbro_keyhole_depth_m(float(p_val), v_m, d_beam, k_s, alpha_solid, T_vap, T_preheat,
                                                 A_fabbro, enth)
            d_um = max(0.5 * w_um, cell_fabbro["depth_m"] * 1e6)
            # Same per-alloy cuts as classify_enthalpy_regime (Inconel 625: keyhole from 13.6, no transition band).
            if enth >= keyhole_cut:
                pt_regime = "Keyhole Mode"
                color_code = "#ef4444"  # Red
            elif enth >= ENTHALPY_TRANSITION:
                pt_regime = "Transition"
                color_code = "#38bdf8"  # Sky
            else:
                pt_regime = "Optimal Conduction"
                color_code = "#10b981"  # Emerald

            # Check Lack of Fusion — Tang (h/W)^2+(t/D)^2
            tang_pt = (float(hatch_spacing_um) / max(1.0, w_um)) ** 2 + (
                float(layer_thickness_um) / max(1.0, d_um)
            ) ** 2
            if tang_pt > 1.0:
                pt_regime = "Lack of Fusion Zone"
                color_code = "#f59e0b"  # Amber
            # No balling cell: the balling screen needs the Eagar–Tsai liquidus L/W, which this quick grid
            # does not compute (the former (1.6 + 0.55 min(6, Pe)) > 3.8 rule was Pe > 4, uncited).

            process_map_grid.append({
                "power_W": int(p_val),
                "speed_mm_s": int(v_val),
                "normalizedEnthalpy": round(enth, 2),
                "regime": pt_regime,
                "color": color_code,
                "width_um": round(w_um, 1),
                "depth_um": round(d_um, 1)
            })

    result = {
        "success": True,
        "engine": "MetalliX-Python-HPC-LPBF-MeltPool-v6.0",
        "modelId": heat_source_id,
        "heatSourceModel": heat_source_id,
        "material": material_name,
        "baseMetal": props["base"],
        "laserWavelength": laser_wavelength,
        "processParameters": {
            "laserPower_W": P_laser,
            "scanSpeed_mm_s": float(scan_speed_mm_s),
            "beamDiameter_um": float(beam_diameter_um),
            "preheatTemp_C": T_preheat,
            "layerThickness_um": float(layer_thickness_um),
            "hatchSpacing_um": float(hatch_spacing_um),
            "inclineAngle_deg": round(float(incline_angle_deg), 2),
            "processSeed": int(process_seed),
            "effectiveAbsorptivity": round(eta_eff, 3),
            "effectiveAbsorptivityBasis": EFFECTIVE_ABSORPTIVITY_BASIS,
            "conductionAbsorptivity": round(eta_base, 3),
            "fabbroAbsorptivity": round(A_fabbro, 3),
            "effectiveConductivity_W_mK": round(k_th, 3),
            "effectiveSpecificHeat_J_kgK": round(cp, 1),
            "solidConductivity_W_mK": round(k_s, 3),
            "liquidConductivity_W_mK": round(k_l, 3),
            "kingUsesSolidThermophysics": True,
            "volumetricEnergyDensity_J_mm3": round(ved_J_mm3, 2),
            "linearEnergyDensity_J_m": round(led_J_m, 1),
            "peakIntensity_MW_cm2": round(peak_intensity_MW_cm2, 3),
            "normalizedEnthalpy": round(normalized_enthalpy, 2),
            "heatSource": source,
            "absorptionModel": absorption_model,
            "thermalSliceBackend": thermal_slice_backend,
            "stefanNumber": round(stefan, 4),
            "latentHeatPowerFactor": round(latent_heat_power_factor, 4),
            "latentHeatPowerFactorBasis": LATENT_HEAT_POWER_FACTOR_BASIS,
            "fieldPower_W": round(P_geom, 2),
        },
        "meltPoolGeometry": {
            "length_um": round(l_melt_um, 1),
            "width_um": round(w_melt_um, 1),
            "depth_um": round(d_melt_um, 1),
            "aspectRatio_L_over_W": round(aspect_L_over_W, 2),
            "depthToWidthRatio_D_over_W": round(d_melt_um / max(1.0, w_melt_um), 2),
            "keyholeVaporCavityDepth_um": round(keyhole_depth_um, 1),
            "regime": regime,
            "regimeBasis": REGIME_THRESHOLD_BASIS,
            "regimeKeyholeThreshold": regime_keyhole_cut(material_name),
            "regimeMaterialNote": regime_material_note(material_name),
            "extentStatus": extent_status,
            "extentNote": extent_note,
            "peakOffset_um": round(x_peak * 1e6, 1),
            "axialFieldMaximum_C": round(t_axial_max_C, 1),
            "goldakParameters": {
                "semiAxis_af_front_um": round(goldak_af_um, 1),
                "semiAxis_ar_rear_um": round(goldak_ar_um, 1),
                "semiAxis_b_halfwidth_um": round(goldak_b_um, 1),
                "semiAxis_c_depth_um": round(goldak_c_um, 1),
                "seed_af_um": round(goldak_seed["af_m"] * 1e6, 1),
                "seed_ar_um": round(goldak_seed["ar_m"] * 1e6, 1),
            }
        },
        "keyholeModel": {
            "modelId": FABBRO_MODEL_ID,
            "basis": FABBRO_BASIS,
            "fabbroDepth_um": round(fabbro["depth_m"] * 1e6, 1),
            "aspectRatio_e_over_d": round(fabbro["aspectRatio_e_over_d"], 2),
            "peclet": round(fabbro["peclet"], 2),
            "pecletInFitRange": fabbro["pecletInFitRange"],
            "absorptivity": round(A_fabbro, 3),
            "absorptivityBasis": "flat-surface value, a disclosed lower bound (not Fabbro keyhole A(R), unmodelled)",
            "doi": fabbro["doi"],
            "depthBenchmarkNote": KEYHOLE_DEPTH_BENCHMARK_NOTE,
        },
        "marangoniModel": {
            "modelId": MARANGONI_MODEL_ID,
            "flowDirection": ma["flowDirection"],
            "dGamma_dT_N_mK": round(ma["dGamma_dT_N_mK"], 6),
            "sulfur_ppm": round(ma["sulfur_ppm"], 1),
            "surfaceVelocity_m_s": round(ma["surfaceVelocity_m_s"], 3),
            "surfaceVelocityDoi": ma.get("surfaceVelocityDoi"),
            "pecletMarangoni": round(ma["pecletMarangoni"], 2),
            "aspectNote": ma["aspectNote"],
            "doi": ma["doi"],
        },
        "hydrodynamicsAndRecoil": {
            "peakTemperature_C": round(t_peak_C, 1),
            "peakTemperatureBasis": peak_temperature_basis,
            "peakTemperatureNote": peak_temperature_note,
            "peakExceedsVaporization": bool(t_peak_C > float(T_vap)),
            "surfaceTemperatureBasis": surface_temperature_basis,
            "surfaceTemperature_C": round(t_surface_C, 1),
            "knudsenRecoilPressure_kPa": round(p_recoil_kPa, 2),
            "marangoniNumber": round(marangoni_number, 0),
            "marangoniGeometrySource": "thermal",
            "molarMass_kg_mol": round(M_molar, 5),
            "pecletThermalNumber": round(peclet_number, 2),
            "powderDenudationWidth_um": round(denudation_width_um, 1)
        },
        "geometricDefectScreen": defect_diagnostics(
            w_melt_um, d_melt_um, l_melt_um, float(hatch_spacing_um), float(layer_thickness_um), balling=balling),
        "defectDiagnostics": {
            "lackOfFusionStatus": lof_status,
            "lackOfFusionRisk": lof_risk,
            "lackOfFusionOverlapIndex": round(lof_criterion_val, 3),
            "tangIndex_hW_tD": round(lof_criterion_val, 3),
            "hOverW": round(h_over_w, 3),
            "tOverD": round(t_over_d, 3),
            "keyholePorosityRisk": keyhole_porosity_risk,
            "keyholePorosityBasis": KEYHOLE_POROSITY_BASIS,
            "keyholePorosityResolved": False,
            "ballingInstabilityRisk": balling_risk,
            "ballingScreen": balling,
            "recoaterCrashRisk": recoater_risk,
            "effectiveResidualStress_MPa": round(effective_residual_stress_mpa, 1),
            "distortionIndex": round(distortion_index, 2),
            "distortionIndexBasis": DISTORTION_INDEX_BASIS,
        },
        "solidificationKinetics": {
            "modelId": SOLIDIFICATION_MODEL_ID,
            "gradientSource": sol.get("gradientSource"),
            "usedFieldMap": bool(sol.get("usedFieldMap")),
            "thermalGradient_G_K_m": round(thermal_gradient_G_K_m, 0),
            "thermalGradient_G_K_um": round(thermal_gradient_G_K_m * 1e-6, 3),
            "thermalGradientTail_G_K_m": round(float(sol.get("G_tail_K_m") or thermal_gradient_G_K_m), 0),
            "solidificationRate_R_m_s": round(solidification_rate_R_m_s, 3),
            "solidificationRate_R_mm_s": round(solidification_rate_R_m_s * 1e3, 1),
            "solidificationCosTheta": round(cos_theta, 4),
            "coolingRate_K_s": round(cooling_rate_K_s, 0),
            "coolingRate_log10": round(math.log10(max(10.0, cooling_rate_K_s)), 2),
            "g_over_r_ratio": round(g_over_r, 0),
            "microstructureMorphology": morphology,
            "primaryDendriteArmSpacing_PDAS_um": round(pdas_um, 2),
            "secondaryDendriteArmSpacing_SDAS_um": round(sdas_um, 2),
            "phaseTransformation": sol.get("phaseTransformation"),
            "frontPointCount": sol.get("frontPointCount"),
            "tail": sol.get("tail"),
            "bottom": sol.get("bottom"),
            "doi": sol.get("doi"),
            "disclaimer": sol.get("disclaimer"),
        },
        "geometricContours": {
            "topDownXY": top_down_contour,
            "longitudinalXZ": longitudinal_contour,
            "transverseYZ": transverse_contour,
            "multiTrackHatchOverlap": overlap_tracks
        },
        "thermalSlices": thermal_slices,
        "processWindowMap": {
            "currentOperatingPoint": {
                "power_W": P_laser,
                "speed_mm_s": float(scan_speed_mm_s),
                "regime": regime,
                "lofStatus": lof_status
            },
            "regimeBasis": REGIME_THRESHOLD_BASIS,
            "regimeKeyholeThreshold": keyhole_cut,
            "grid": process_map_grid,
            "ballingNote": ("Balling is screened at the operating point only (defectDiagnostics.ballingScreen, "
                            "Eagar-Tsai L/W); the quick grid has no melt-pool length and marks no balling zone."),
        }
    }
    if material_name == "Inconel 625":
        result["materialEvidence"] = {
            "propertySource": "lpbf_thermal_solver.SECONDARY_THERMOPHYSICAL_DB.Inconel 625",
            "provenanceClass": "legacy-estimated-secondary",
            "validationStatus": "unvalidated",
            "scope": "direct-meltpool-screening",
            "usesBoundedIN625Snapshot": False,
        }
    return result

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--status":
        print(json.dumps({
            "status": "ready",
            "engine": "MetalliX Python LPBF Thermal & Solidification Solver v4.0",
            "materials": list(THERMOPHYSICAL_DB.keys())
        }))
        sys.exit(0)
        
    try:
        if len(sys.argv) > 1 and sys.argv[1].strip().startswith("{"):
            data = json.loads(sys.argv[1])
        elif not sys.stdin.isatty():
            raw_input = sys.stdin.read()
            if raw_input.strip():
                data = json.loads(raw_input)
            else:
                data = {}
        else:
            data = {}
            
        mat = data.get("material", "Inconel 718")
        power = float(data.get("laserPower_W", 285.0))
        speed = float(data.get("scanSpeed_mm_s", 960.0))
        beam = float(data.get("beamDiameter_um", 80.0))
        preheat = float(data.get("preheatTemp_C", 80.0))
        layer = float(data.get("layerThickness_um", 40.0))
        hatch = float(data.get("hatchSpacing_um", 110.0))
        wavelength = data.get("laserWavelength", "IR_1064nm")
        heat_source = data.get("heatSource") or data.get("heat_source") or "rosenthal"
        absorption_model = data.get("absorptionModel")
        thermal_slice_backend = data.get("thermalSliceBackend")
        sulfur_ppm = float(data.get("sulfur_ppm", data.get("sulfurPpm", 15.0)))
        
        t0 = time.time()
        result = calculate_meltpool_physics(
            mat, power, speed, beam, preheat, layer, hatch, wavelength,
            heat_source=heat_source,
            sulfur_ppm=sulfur_ppm,
            absorption_model=absorption_model,
            thermal_slice_backend=thermal_slice_backend,
        )
        result["computeTimeMs"] = round((time.time() - t0) * 1000.0, 1)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)
