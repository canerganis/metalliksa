#!/usr/bin/env python3
"""
MetalliX Python LPBF Thermal, Melt Pool Geometry & Multi-Defect Physics Solver
Author: MetalliX Additive Manufacturing HPC Subsystem

Simulates:
1. 3D Goldak double-ellipsoid moving laser heat source & Eagar-Tsai / Rosenthal thermal fields
2. Multi-regime melt pool geometry (Conduction, Transition, Keyhole Mode)
3. 3-View geometric contours (Top-Down X-Y, Longitudinal X-Z, Transverse Y-Z with Hatch Overlap)
4. Marangoni screening from the served loss-free peak (null where unsupported); recoil pressure is not served
   (P6 containment 2026-10-11: no wall closure), an onset status string is served instead
5. Comprehensive defect analytics: Lack of Fusion (LoF), Keyhole Porosity, Plateau-Rayleigh Balling
   (powder denudation width is served null: uncited heuristic, G1 audit B05)
6. Solidification front container (SOL-A1, 2026-10-15): G, R, cooling rate, G/R, PDAS, SDAS, morphology and the
   transformation note are null with reason codes for every alloy until an admitted liquidus parent exists
7. Full 2D Power-Velocity (P-V) Process Window map generation
"""

import sys
import json
import math
import time

import numpy as np

from eagar_tsai_solver import (EagarTsaiField, MODEL_ID as EAGAR_TSAI_MODEL_ID, SURFACE_MAXIMUM_BASIS,
                               eagar_tsai_surface_maximum)
from fabbro_keyhole import MODEL_ID as FABBRO_MODEL_ID, fabbro_keyhole_depth_m
from four_alloy_materials import (ABSORPTIVITY_BASIS_UNSOURCED, ABSORPTIVITY_INDEX_BASIS,
                                  ABSORPTIVITY_INDEX_NOTE_ALSI10MG, INDEX_FULL_SET_KEYS, INDEX_KEY_IR, KERNEL_KEYS,
                                  KERNEL_LEDGER_BASIS, KERNEL_LEDGER_STATE_NOTE_ALSI10MG, MELT_KEYS,
                                  PROPERTY_CONVENTION_BLEND_BASIS, SOLID_CONDUCTIVITY_BASIS_LEDGER,
                                  absorptivity_authority, four_alloy_thermophysical_db, kernel_properties,
                                  endpoint_admission, melt_point_properties, resolve_alloy_id, thermal_props)
from in625_thermal_material import LATENT_HEAT_J_KG as IN625_LATENT_HEAT_J_KG
from goldak_solver import GoldakField, MODEL_ID as GOLDAK_MODEL_ID, seed_goldak_axes
from solidification_front import evaluate_solidification
from marangoni_screening import (BAND_BASIS as MARANGONI_BAND_BASIS, MODEL_ID as MARANGONI_MODEL_ID,
                                 SURFACE_VELOCITY_DOI as MARANGONI_SURFACE_VELOCITY_DOI,
                                 marangoni_flow_direction, marangoni_screening)
from lpbf_defect_diagnostics import balling_screen, defect_diagnostics

# Secondary alloys only. Ti-6Al-4V, 316L, AlSi10Mg, IN718 live in four_alloy_materials.py.
# pdas_A1 and sdas_B1 below: unused since P7a (2026-10-11; no sourced PDAS prefactor or SDAS B1); kept so no material
# snapshot hash moves. The solver does not read them.
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
        # P7b (2026-10-14): absorptivity_IR is the measured conduction-mode authority (Deisenroth 2020 Sec. 3.4,
        # four_alloy_materials.ABSORPTIVITY_AUTHORITY), absorptivity_index_IR the pre-P7 convention constant of the
        # dH/hs regime index (the 13.6 cut was fitted with it), the melt keys the Weaver 2022 Table 2 melting-point
        # convention (four_alloy_materials.MELT_POINT_PROPERTIES). The other secondaries have no measurement: their
        # index constant equals their absorptivity_IR and they keep the solid/liquid blend (no melt keys).
        "absorptivity_IR": 0.34,
        "absorptivity_index_IR": 0.38,
        "absorptivity_Green": 0.58,
        "thermal_conductivity_melt_W_mK": 28.78,
        "specific_heat_melt_J_kgK": 719.92,
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
        "absorptivity_index_IR": 0.40,
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
        "absorptivity_index_IR": 0.22,
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
        "absorptivity_index_IR": 0.39,
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
        "absorptivity_index_IR": 0.08,
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

for _name, _row in SECONDARY_THERMOPHYSICAL_DB.items():
    assert _row["absorptivity_IR"] == absorptivity_authority(_name)["value"], _name
    _melt = melt_point_properties(_name)
    if _melt is None:
        assert all(_key not in _row for _key in MELT_KEYS), _name
        assert _row[INDEX_KEY_IR] == _row["absorptivity_IR"], _name
    else:
        for _key in MELT_KEYS:
            assert _row[_key] == _melt[_key], (_name, _key)
del _name, _row, _melt, _key

# P7b (2026-10-14, docs/research/SPEC_p7b_sourced_constants_2026-10-11.md section 2.2): the dH/hs regime index is
# CLASSIFICATION NEUTRAL. It reads an index convention absorptivity (absorptivity_index_IR, the pre-P7 served value
# per alloy) because the cuts 15, 20 and 13.6, the King conversion 22.2 and the Zhao and Cunningham derived bands were
# all derived in that convention; the conduction field, the Fabbro leg amplitude and every other physical use take the
# measured authority absorptivity_IR. Resolution of the index value for the IR wavelength, in order: (1) the override
# set's own absorptivity_index_IR; (2) a FULL property set override (every key of INDEX_FULL_SET_KEYS present, for
# example the AM-Bench IN625_VALIDATION_PROPS snapshot) without an index key follows its own absorptivity_IR, stated;
# (3) otherwise (a partial override such as UQ or the calibration layer) the base alloy's absorptivity_index_IR. The
# Green wavelength index reads absorptivity_Green unchanged.
ABSORPTIVITY_TRANSITION_NOTE = ("In transition and keyhole mode the measured absorptance is 0.6 to 0.9 (Deisenroth "
                                "2020 Fig 7, Trapp 2017 Fig 3a, Fabbro 2020 Sec 4.1); the field and the Fabbro leg "
                                "use this conduction value, a disclosed lower bound there (see FABBRO_BASIS; "
                                "replacement is P3). Not a powder layer value.")
ABSORPTIVITY_BASIS_ALSI10MG = ("measured conduction value on an as-built rough AM surface (Sa 22.3 um) in N2 at 1075 nm, "
                               "Leis 2020 area II minimum; band 0.28 to 0.40; not a polished or ground plate; not a "
                               "powder layer value")
ABSORPTIVITY_AUTHORITY_SEE = "authority value, see absorptivityBasis"
# Process-map grid kernel (B17, B19): every cell's width and liquidus depth come from the served Rosenthal field
# extent routine at the authority field power whatever kernel was requested (an Eagar-Tsai or Goldak cell would
# cost about 100 times more). gridKernel says so.
GRID_KERNEL = "rosenthal-screening-v1"
GRID_KERNEL_NOTE = ("every grid cell is the served Rosenthal field extent (_axial_peak_x, _liquidus_extent) at the "
                    "authority field power A P with the served k, cp, rho and alpha convention and depth = max(liquidus "
                    "depth, Fabbro leg), whatever kernel the operating point requested; the former closed-form width "
                    "sqrt(8/(pi e) A P / (rho cp dT v) + d_beam^2) had no source (G1 audit B17) and the 0.5 w depth "
                    "bound is dropped. Cells whose extent is not a computed isotherm serve width and depth null with "
                    "their extentStatus and no Lack of Fusion Zone class.")
GRID_NOT_COMPUTED_NOTE = "process map not computed (include_process_map=False: an internal re-run)"
# Conduction property conventions served as propertyConvention.
PROPERTY_CONVENTION_KERNEL_LEDGER = "kernel-ledger-kirchhoff"
PROPERTY_CONVENTION_KERNEL_OVERRIDE = "kernel-override"
PROPERTY_CONVENTION_MELTING_POINT = "melting-point"
PROPERTY_CONVENTION_BLEND = "blend"
DENSITY_BASIS_ALSI10MG = "2680, room temperature convention constant, unsourced; the conduction kernel uses 2696"


def _merged_props(base_props, prop_overrides):
    props = dict(base_props)
    if prop_overrides:
        props.update(prop_overrides)
    return props


def resolve_index_absorptivity(laser_wavelength, base_props, prop_overrides, material_name=None):
    """(index absorptivity, basis text) for the dH/hs regime index under the P7b resolution rule."""
    if laser_wavelength != "IR_1064nm":
        return float(_merged_props(base_props, prop_overrides)["absorptivity_Green"]), (
            "Green wavelength: the index reads absorptivity_Green (the same value as the field); no index "
            "convention constant exists for 515 nm")
    overrides = prop_overrides or {}
    if INDEX_KEY_IR in overrides:
        value = float(overrides[INDEX_KEY_IR])
        text = f"{ABSORPTIVITY_INDEX_BASIS}; the override set supplied its own {INDEX_KEY_IR}"
    elif all(key in overrides for key in INDEX_FULL_SET_KEYS):
        value = float(overrides["absorptivity_IR"])
        text = ("index follows the override set's own absorptivity, no index key supplied (a full property set "
                f"override; {ABSORPTIVITY_INDEX_BASIS})")
    else:
        value = float(base_props.get(INDEX_KEY_IR, base_props["absorptivity_IR"]))
        text = (f"{ABSORPTIVITY_INDEX_BASIS}; the base alloy's {INDEX_KEY_IR} is used"
                + ("; a partial override (absorptivity_IR among the keys) moves the field, not the index"
                   if "absorptivity_IR" in overrides else ""))
    if resolve_alloy_id(material_name) == "alsi10mg" and value == 0.18:
        text += f"; {ABSORPTIVITY_INDEX_NOTE_ALSI10MG}"
    return value, text


def absorptivity_basis_text(material_name, laser_wavelength, prop_overrides=None):
    """(absorptivityBasis, absorptivitySource) of the physical field value (spec section 2.3, Amendment 1 item 3.7)."""
    entry = absorptivity_authority(material_name)
    overridden = bool(prop_overrides) and "absorptivity_IR" in prop_overrides
    if laser_wavelength != "IR_1064nm" or entry is None or entry["unsourced"]:
        return ABSORPTIVITY_BASIS_UNSOURCED, None
    lo, hi = entry["band"]
    if entry["alloy"] == "alsi10mg":
        text = f"{ABSORPTIVITY_BASIS_ALSI10MG}. {ABSORPTIVITY_TRANSITION_NOTE}"
    else:
        text = (f"measured conduction-mode value, bare plate, 1070 nm: {entry['source']}, {entry['locator']}; band "
                f"{lo:g} to {hi:g}. {ABSORPTIVITY_TRANSITION_NOTE}")
    if overridden:
        text = ("overridden by prop_overrides (the served value is the override, not the authority); authority: "
                + text)
    return text, entry["source"]


def resolve_conduction_kernel(material_name, props, prop_overrides, T_preheat_C):
    """One constant K, cp and rho_k per call for the conduction kernels (Amendment 1 item 3.3 precedence).

    (i) explicit kernel_* keys in prop_overrides win (UQ scaling uses this); (ii) otherwise a ledger alloy (Ti-6Al-4V,
    AlSi10Mg) takes the Kirchhoff mean of its sourced solid forms at the call's preheat, whatever k / cp keys the set
    carries (the Build Job passes the full frozen snapshot); (iii) otherwise the melting point keys of the property
    set, else the equal-weight solid/liquid blend. rho_k is kernel_density_kg_m3 when present, else density_kg_m3.
    Returns (k_th, cp, rho_k, convention, basis, solid_basis, kernel_ledger_or_None).
    """
    overrides = prop_overrides or {}
    rho = float(props["density_kg_m3"])
    k_s = float(props["thermal_conductivity_W_mK"])
    k_l = float(props.get("thermal_conductivity_liquid_W_mK", k_s))
    cp_s = float(props["specific_heat_J_kgK"])
    cp_l = float(props.get("specific_heat_liquid_J_kgK", cp_s))
    rho_k = float(props.get("kernel_density_kg_m3", rho))
    T_liq = float(props["liquidus_C"])
    solid_basis_tail = ("; the dH/hs index and the Fabbro leg keep the solid k_s, cp_s and the room temperature density")
    if KERNEL_KEYS[0] in overrides and KERNEL_KEYS[1] in overrides:
        k_th = float(overrides[KERNEL_KEYS[0]])
        cp = float(overrides[KERNEL_KEYS[1]])
        alpha = k_th / (rho_k * cp)
        basis = (f"explicit kernel keys of prop_overrides: K {k_th:.6g} W/mK, cp {cp:.6g} J/kgK, rho_k {rho_k:g} kg/m3, "
                 f"alpha {alpha:.4g} m2/s (a caller's own kernel, for example a UQ scale of the materialised ledger "
                 f"mean){solid_basis_tail}")
        return k_th, cp, rho_k, PROPERTY_CONVENTION_KERNEL_OVERRIDE, basis, (
            "room temperature value used by the regime index, the keyhole leg and the transient table; the "
            "conduction field uses the explicit kernel keys"), None
    ledger = kernel_properties(material_name, T_preheat_C + 273.15, T_liq + 273.15)
    if ledger is not None:
        k_th = ledger["kernel_conductivity_W_mK"]
        cp = ledger["kernel_specific_heat_J_kgK"]
        rho_k = float(overrides.get("kernel_density_kg_m3", ledger["kernel_density_kg_m3"]))
        alpha = k_th / (rho_k * cp)
        basis = f"{KERNEL_LEDGER_BASIS}; K {k_th:.3f} W/mK, cp {cp:.2f} J/kgK, alpha {alpha:.4g} m2/s"
        if ledger["alloy"] == "alsi10mg":
            basis += f"; {KERNEL_LEDGER_STATE_NOTE_ALSI10MG}; kernel density {rho_k:g} kg/m3"
        basis += (f"; evaluated at the request preheat {ledger['T0_requested_K'] - 273.15:g} C (isotherm range "
                  f"{ledger['T0_K']:.2f} to {ledger['T_liq_K']:.2f} K){solid_basis_tail}")
        return k_th, cp, rho_k, PROPERTY_CONVENTION_KERNEL_LEDGER, basis, SOLID_CONDUCTIVITY_BASIS_LEDGER, ledger
    k_blend = 0.5 * (k_s + k_l)
    cp_blend = 0.5 * (cp_s + cp_l)
    melt_entry = melt_point_properties(material_name)
    # An override set that replaces the solid or liquid k / cp without supplying the melt keys describes another
    # material (a synthetic set, a calibration property set): the base alloy's melt keys must not leak into it, so
    # the blend of the overridden values is used. A set that carries the melt keys (the Build Job snapshot, UQ
    # scales) or touches no k / cp key (an absorptivity-only override) keeps them.
    blend_source_keys = ("thermal_conductivity_W_mK", "thermal_conductivity_liquid_W_mK", "specific_heat_J_kgK",
                         "specific_heat_liquid_J_kgK")
    melt_props = dict(props)
    if overrides and not any(key in overrides for key in MELT_KEYS) and any(key in overrides for key in blend_source_keys):
        for key in MELT_KEYS:
            melt_props.pop(key, None)
    if all(key in melt_props for key in MELT_KEYS):
        k_th = float(melt_props["thermal_conductivity_melt_W_mK"])
        cp = float(melt_props["specific_heat_melt_J_kgK"])
        alpha = k_th / (rho_k * cp)
        src_alpha = None if melt_entry is None else melt_entry.get("sourceDiffusivity_m2_s")
        basis = (
            f"melting point k {k_th:g} W/mK and cp {cp:g} J/kgK with room temperature density {rho_k:g} kg/m3; "
            + (f"{melt_entry['source']}; {melt_entry['locator']}; evaluation temperature "
               f"{melt_entry['evaluationTemperature_C']:g} C; " if melt_entry is not None else
               "melt keys supplied by prop_overrides; ")
            + (f"the source diffusivity at the melting point is {src_alpha:.3g} m2/s, the served alpha is "
               f"{alpha:.3g} m2/s" if src_alpha is not None else f"the served alpha is {alpha:.3g} m2/s")
            + (f"; {melt_entry['bandNote']}" if melt_entry is not None and melt_entry.get("bandNote") else "")
            + solid_basis_tail)
        return k_th, cp, rho_k, PROPERTY_CONVENTION_MELTING_POINT, basis, (
            "room temperature value used by the regime index, the keyhole leg and the transient table; the "
            "conduction field uses the melting point k and cp"), None
    alpha = k_blend / (rho_k * cp_blend)
    basis = (f"{PROPERTY_CONVENTION_BLEND_BASIS}: k 0.5 (k_s + k_l) = {k_blend:g} W/mK, cp 0.5 (cp_s + cp_l) = "
             f"{cp_blend:g} J/kgK (no melting point source in the library for this alloy); the served alpha is "
             f"{alpha:.3g} m2/s{solid_basis_tail}")
    return k_blend, cp_blend, rho_k, PROPERTY_CONVENTION_BLEND, basis, (
        "room temperature value used by the regime index, the keyhole leg and the transient table; the "
        "conduction field uses the equal-weight solid and liquid blend"), None

# Regime (normalised-enthalpy screening index, repo convention r = 1/e^2 radius, flat A, solid k/cp,
# hs = rho cp_s (T_liq - T0)). 15 = vapor-depression onset (Cunningham 2019 Fig. 3A blue line, app units
# 13.0-16.9 along speed). 20 = PROVISIONAL screening choice for the keyhole-mode onset (melt-pool D/W ~ 0.5): it
# lies in the overlap of the King et al. 2014 30 +/- 4 (316L, Table 3 constants with the density unit corrected
# to 7980 kg/m3, sigma = D4sigma/4) converted to this convention = 21.4 (18.6-24.3 at the SOL-T 316L liquidus 1450 C;
# 22.2, 19.3-25.2 at the former 1400 C, where the cut was chosen; conditional on the app
# absorptivity, 20 C preheat and property set) and the Cunningham 2019 Fig. 3A red-line values along speed
# (Ti-6Al-4V, 95 um 1/e^2) = 17.3-20.0 (a range along speed, not a confidence interval). Not an exact threshold.
ENTHALPY_TRANSITION = 15.0
ENTHALPY_KEYHOLE = 20.0
KEYHOLE_INDEX_LOF_NOTE = (
    "Keyhole-index cell: the Tang lack-of-fusion flag comes from a keyhole depth that is biased low "
    "(keyhole absorptance A(R) not modelled); treat as unresolved, not as lack of fusion."
)
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
                          "(18.6-24.3 at the SOL-T 316L liquidus 1450 C, 19.3-25.2 at the former 1400 C where the cut was chosen; "
                          "conditional on the app absorptivity, 20 C preheat and property set; King's "
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
# P7a (2026-10-11): the level 30 no longer drives any verdict; it is an advisory ("unsourced screening threshold")
# and the former do-not-print edge 35 is removed. The Fabbro onset ramp's full-weight point is the separate constant
# FABBRO_ONSET_RAMP_FULL_AT so that demoting the porosity level does not read as demoting the ramp.
POROSITY_SCREEN_NEGLIGIBLE_BELOW = 15.0
POROSITY_SCREEN_HIGH_AT = 30.0
FABBRO_ONSET_RAMP_FULL_AT = 30.0
KEYHOLE_POROSITY_BASIS = ("Porosity unresolved; legacy screening level on the normalised enthalpy, independent of the "
                          "regime threshold. < 15: Zhao 2020 (doi 10.1126/science.abd1587) found no pore condition "
                          "below 15 (0/35) and its boundary minimum is 15.0; 0/35 observations is not evidence of "
                          "safety. >= 30 is an unsourced screening threshold, a legacy porosity level kept as an "
                          "advisory for continuity, not a porosity boundary (Zhao 2020 stable keyholes up to dH/hs 62 "
                          "at high speed); since P7a it drives no verdict. Keyhole mode (>= 20) does not imply porosity.")
# P7a: keyhole-mode basis served per alloy (the keyhole gate and regimeKeyholeCutBasis). A mode onset, not a porosity
# boundary. King 2014 Conclusion (4) and Sec. 5.6: threshold 30 +/- 4 for 316L (50 um powder layer); Conclusions (1)
# and (5): voids appear in keyhole mode and increase far above the threshold (a qualitative association). Cunningham
# 2019 p.2: keyhole threshold and morphology by x-ray imaging. Zhao 2020 (Science 370, 1080): energy-density threshold
# about 3.7 MJ/m2 below which no keyhole pores form, no pore condition below index 15, stable keyholes up to 62. Huang
# 2022 (doi 10.1038/s41467-022-28694-x): the transition to unstable keyhole melting is alloy dependent (H/hm x Lth about
# 8 +/- 3 for Ti-6Al-4V and 20 +/- 3 for Al7A77 in that paper's units).
KEYHOLE_MODE_ONSET_STATEMENT = (
    "keyhole mode onset, not a porosity boundary: King 2014 Conclusion (4) and Sec. 5.6 (30 +/- 4 for 316L, 50 um "
    "powder layer) with Conclusions (1) and (5) (voids appear in keyhole mode and increase far above the threshold, a "
    "qualitative association); Cunningham 2019 p.2 (keyhole threshold and morphology by x-ray imaging); Zhao 2020 "
    "(Science 370, 1080: energy density threshold about 3.7 MJ/m2 below which no keyhole pores form, no pore condition "
    "below index 15, stable keyholes up to 62); Huang 2022 (doi 10.1038/s41467-022-28694-x: the transition to unstable "
    "keyhole melting is alloy dependent, H/hm x Lth about 8 +/- 3 for Ti-6Al-4V and 20 +/- 3 for Al7A77 in that "
    "paper's units)")
KEYHOLE_CUT_BASIS_316L = (
    "cut 20: King 2014 30 +/- 4 converted to this convention by the pinned tools/lpbf_keyhole_benchmark.king_conversion: "
    "21.4 (18.6 to 24.3) at the SOL-T 316L liquidus 1450 C (22.2, 19.3 to 25.2 at the former 1400 C, where the cut "
    "was chosen; the cut is not re-derived), conditional on the app absorptivity 0.42 (index convention), T0 20 C and the app 316L "
    "property set; King's printed density unit corrected to 7980 kg/m3")
KEYHOLE_CUT_BASIS_TI64 = (
    "cut 20: Cunningham 2019 Fig. 3A red line along speed, 17.3 to 20.0 in app units (a range along speed, not a "
    "confidence interval)")
KEYHOLE_CUT_BASIS_IN625 = (
    "cut 13.6: fitted on 56 NIST mds2-2923 tracks; the PASSED held-out bracket places the onset in (12.67, 13.94]; "
    "13.6 is the fit split point estimate")
KEYHOLE_CUT_BASIS_TRANSFERRED = "cut 20: transferred from the 316L and Ti-6Al-4V bases, not derived for this alloy"


def keyhole_cut_basis(material_name=None) -> str:
    """Per-alloy keyhole-mode cut basis (P7a): the onset statement plus the alloy's own cut provenance."""
    name = str(material_name or "").lower()
    if _is_in625(name):
        own = KEYHOLE_CUT_BASIS_IN625
    elif "316" in name:
        own = KEYHOLE_CUT_BASIS_316L
    elif "ti-6al-4v" in name or "ti6al4v" in name or name.startswith("ti64"):
        own = KEYHOLE_CUT_BASIS_TI64
    else:
        own = KEYHOLE_CUT_BASIS_TRANSFERRED
    return f"{KEYHOLE_MODE_ONSET_STATEMENT}; {own}"
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
                "(see pecletInFitRange); unsourced linear dH/hs onset ramp 15 to 30 (the 15 reads Cunningham 2019 Fig. 3A, "
                "the 30 is a legacy level; a sourced shape in other units exists: Gan 2021 Eq. 2 regime edges 1.4 and 6.0 "
                "in Gan units, Naderi 2022 Eq. 16 and Table 3 for IN625 and IN718; replacement is P3); k_s is the "
                "room-temperature solid "
                "value (Fabbro's constants imply a high-temperature K; P2). Depth served as max(conduction isotherm "
                "depth, this leg) for every kernel; " + KEYHOLE_DEPTH_BENCHMARK_NOTE)
EFFECTIVE_ABSORPTIVITY_BASIS = ("flat absorptivity of the material authority for the conduction field (Eagar-Tsai 1983 "
                                "and Goldak 1984 take Q as absorbed power; Knapp 2022 finds the IN625 conduction-mode "
                                "effective absorption near Fresnel 0.30, HT 0.29 to 0.32, HTFF 0.27 to 0.29). No kernel "
                                "represents the measured absorptance rise in transition and keyhole mode (0.6 to 0.9: "
                                "Deisenroth 2020 Fig. 7, Trapp 2017 Fig. 3a). The former multi-reflection ramp 1-(1-A)^n "
                                "(uncited) was removed 2026-10-11. " + ABSORPTIVITY_AUTHORITY_SEE + " (P7b: the "
                                "measured conduction-mode authority where one exists; the dH/hs index reads the "
                                "separate index convention constant, see absorptivityIndexBasis).")
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
# P7a (2026-10-11): stress and distortion are unavailable (G1 audit B08, B09; lead decision 4). The former
# sigma_eff = 0.72 E alpha dT / (1 - nu) and index = sigma_eff (layer / 40 um) / 420 MPa were unsourced constants;
# Mercelis and Kruth 2006 (Rapid Prototyping J. 12, 254) Sec. 2 assumes the stress of the newly added layer equals the
# yield strength and supports a cap at yield only, and the authority yield values are unsourced wrought values.
STRESS_UNAVAILABLE_REASON = ("unavailable: no sourced stress model (Mercelis and Kruth 2006 supports a yield cap only, "
                             "and the yield values are unsourced)")
LOF_MARGIN_BASIS = ("unsourced screening threshold 0.80; the only published analog is Harkin 2023 Eq. 11 and "
                    "Conclusions, R_c^2 = 0.7 (R_c 0.83) for analytic Rosenthal geometry, Ti-6Al-4V on one machine; it "
                    "differs and is not applied. One lack-of-fusion rule for both screens: the Tang unit criterion")
DISTORTION_INDEX_BASIS = ("unavailable since P7a (2026-10-11): the former alloy/layer/preheat-only index "
                          "0.72 E alpha dT / (1 - nu) x (layer / 40 um) / 420 MPa used unsourced constants and is "
                          "not served; " + STRESS_UNAVAILABLE_REASON)


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


# P6 containment (2026-10-11, docs/research/SPEC_p6_containment_2026-10-11.md). The served peak is the loss-free
# Eagar-Tsai surface maximum, served only below a SOURCED vapour temperature; the former regularised Rosenthal centre
# value T0 + P/(2 pi k r_reg) and the clip surfaceTemperature = min(peak, T_vap) are removed (G1 audit B01). Recoil
# pressure (former Anisimov/Knight 0.54 p_sat at the clipped T_vap, a constant 54.72 kPa in every saturated case; B03)
# and the denudation width heuristic (B05) are served null with a reason. The material authority's boiling_C,
# latent_heat_vap_J_kg and M_molar_kg_mol stay in use by the Fabbro leg (T_vap) and are UNSOURCED (G1 audit B04,
# out of P6 scope); they never feed the served peak policy.
SOURCED_VAPOR_TEMPERATURE_K = {
    # Gan et al. 2021, Nat. Commun. 12:2379, doi 10.1038/s41467-021-22704-0, Supplementary Table 1 (SI p.20),
    # "Vaporization point T_v (K)", Ti64 column: source-model effective value, not a species-resolved boiling point.
    "ti6al4v": {"T_K": 3560.0, "source": "Gan et al. 2021 Nat. Commun. 12:2379, Supplementary Table 1, SI p.20",
                "doi": "10.1038/s41467-021-22704-0"},
    # Khairallah et al. 2016, Acta Mater. 108, 36-45, doi 10.1016/j.actamat.2016.02.014, Sec. 2.2, printed p.38:
    # "T_b = 3086 K is the boiling temperature of 316L stainless steel".
    "ss316l": {"T_K": 3086.0, "source": "Khairallah et al. 2016 Acta Mater. 108, Sec. 2.2, p.38",
               "doi": "10.1016/j.actamat.2016.02.014"},
}
VAPOR_TEMPERATURE_UNSOURCED_NOTE = ("no sourced vapour temperature in the library for this alloy (no elemental "
                                    "proxy is used; lead decision, P6 containment)")
PEAK_TEMPERATURE_BASIS = SURFACE_MAXIMUM_BASIS
PEAK_TEMPERATURE_NOTE = ("numerical maximum along the axis y = z = 0 of the loss-free Eagar & Tsai 1983 Gaussian "
                         "surface field (printed p.347-s Eq. 6, 8 to 10, p.348-s Eq. 11, Appendix B) driven by the "
                         "same field power, served k and alpha convention (kernel ledger mean, melting point or blend, "
                         "see propertyConventionBasis; P7b) and 1/e^2 radius as the requested kernel; conduction only, "
                         "no evaporation, flow or recoil loss. Served only below the sourced vapour temperature: a "
                         "centreline above boiling is an impossible situation for the loss-free solution (Eagar & "
                         "Tsai 1983 p.348-s). The former regularised Rosenthal centre value was removed (P6).")
PEAK_ABOVE_TV_REASON = ("the loss-free Eagar-Tsai surface maximum is at or above the sourced vapour temperature: a "
                        "centreline above boiling is an impossible situation for the loss-free solution (Eagar & Tsai "
                        "1983 p.348-s) and no wall closure is served (P6 containment)")
RECOIL_UNAVAILABLE_REASON = ("recoil pressure needs a wall temperature from a surface or cavity closure; none is "
                             "served (the former Anisimov/Knight 0.54 p_sat at the clipped T_vap, a constant 54.72 kPa, "
                             "was removed; P6 containment)")
RECOIL_ONSET_BELOW = "below Fabbro 2020 App A onset"
RECOIL_ONSET_ABOVE = "above onset, no wall closure"
RECOIL_ONSET_BASIS = ("Fabbro 2020 (doi 10.3390/app10041487) Appendix A Eq. A10 to A12: recoil p_r = (1 + beta)/2 "
                      "p_sat(T), beta = 0.2, onset at p_r = p_amb, i.e. T_th = T_v / (1 - ln(2 p_amb / ((1 + beta) "
                      "p0)) / c) with c = L_v M / (R T_v), 3.5 to 4.4 % above T_v for the Gan 2021 SI Table 1 "
                      "alloys. The status compares the loss-free Eagar-Tsai maximum with the sourced T_v, a lower "
                      "bound of T_th: below T_v the surface is below the onset; at or above T_v the loss-free "
                      "solution is invalid and neither the wall temperature nor the onset margin is resolvable "
                      "without a wall closure. Not evaluated where T_v is unsourced.")
MARANGONI_UNAVAILABLE_REASON = ("the Marangoni temperature difference reads the served peak, which is unavailable: ")
DENUDATION_UNAVAILABLE_REASON = ("the denudation width heuristic W (1 + 0.35 min(3, p_recoil / 30)) was uncited "
                                 "(G1 audit B05) and recoil is not served; no sourced relation replaces it (P6 "
                                 "containment)")
AXIAL_MAXIMUM_ROSENTHAL_REASON = ("the Rosenthal axial maximum is the regularised singular-source value T0 + P/(2 pi "
                                  "k r_reg), not a field maximum; removed (P6 containment)")
AXIAL_MAXIMUM_ABOVE_TV_REASON = ("the kernel's axial field maximum is at or above the sourced vapour temperature; "
                                 "the loss-free field is not a wall temperature there (Eagar & Tsai 1983 p.348-s; P6 "
                                 "containment)")


def sourced_vapor_temperature(material_name):
    """Sourced vapour temperature (K and C, with source and DOI) for the alloy, or None (no proxy)."""
    alloy_id = resolve_alloy_id(material_name)
    entry = SOURCED_VAPOR_TEMPERATURE_K.get(alloy_id) if alloy_id else None
    if entry is None:
        return None
    return {"T_K": entry["T_K"], "T_C": entry["T_K"] - 273.15, "source": entry["source"], "doi": entry["doi"]}


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
    include_process_map: bool = True,
):
    """
    Evaluates 3D multi-regime melt pool physics, geometry, defects, and microstructure.
    Optional prop_overrides merge onto the resolved thermophysical dict (UQ / AM-Bench).
    heat_source: "rosenthal" (Build Job default), "eagar-tsai", or "goldak" (Melt Pool lab).
    sulfur_ppm: Heiple–Roper screening only (does not refit W/D or re-score Build Job).
    absorption_model: "flat-plate" (default) or "powder-raytrace" (explicit GPU opt-in; ΔH/hs stays flat).
    thermal_slice_backend: "cpu" (default) or "warp" (explicit GPU opt-in, Rosenthal only).
    include_process_map: False skips the 49-cell field-extent grid (internal re-runs: suggested patch, UQ, optimizer,
    process window); processWindowMap.grid is then None and every other served field is identical (P7b).
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
    liquidus_parent = endpoint_admission(material_name)
    if liquidus_parent is not None and [props["solidus_C"] + 273.15, props["liquidus_C"] + 273.15] != liquidus_parent["record"]["endpoint_K"]:
        liquidus_parent = None
    
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
    # The build-surface incline is echoed (inclineAngle_deg) but no longer multiplies R (P6 containment).

    T_liq = props["liquidus_C"]
    T_sol = props["solidus_C"]
    # UNSOURCED authority value (G1 audit B04, out of P6 scope): drives the Fabbro leg only. The served peak policy
    # reads sourced_vapor_temperature() instead.
    T_vap = props["boiling_C"]
    rho = props["density_kg_m3"]
    k_s = props["thermal_conductivity_W_mK"]
    k_l = float(props.get("thermal_conductivity_liquid_W_mK", k_s))
    cp_s = props["specific_heat_J_kgK"]
    cp_l = float(props.get("specific_heat_liquid_J_kgK", cp_s))
    # P7b (V07 and Amendment 1 item 3): the conduction field (Rosenthal, Eagar-Tsai, Goldak, the balling companion,
    # the grid, the loss-free peak, the thermal slices and the field mapped G and R) takes ONE constant k, cp and rho_k
    # per call: the Kirchhoff mean of the sourced solid forms at the request preheat for a ledger alloy (Ti-6Al-4V,
    # AlSi10Mg), the melting point values where a source gives them (Rubenchik 2018 Sec. 3.1: "the values will be
    # taken at melting point where most of the energy will be deposited"; Weaver 2022; Mills 2002), else the former
    # equal-weight solid/liquid blend, labelled. The index and the Fabbro leg keep the solid k_s, cp_s and the room
    # temperature density (V17, V08 unchanged); rho_k is used in every kernel read of rho.
    k_th, cp, rho_k, property_convention, property_convention_basis, solid_conductivity_basis, kernel_ledger = (
        resolve_conduction_kernel(material_name, props, prop_overrides, T_preheat))
    alpha_th = k_th / (rho_k * cp)  # Thermal diffusivity (m^2/s) of the conduction kernel
    density_basis = (DENSITY_BASIS_ALSI10MG if resolve_alloy_id(material_name) == "alsi10mg" and rho_k != rho
                     else "room temperature value; the conduction kernel reads the same density")
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
    # Physical value (P7b: the measured conduction-mode authority where one exists): the field power of every
    # kernel and the Fabbro leg amplitude.
    eta_base_flat = float(props[wavelength_property])
    # Index convention value (P7b, classification neutral): the dH/hs regime index only.
    eta_index, absorptivity_index_basis = resolve_index_absorptivity(laser_wavelength, base, prop_overrides,
                                                                     material_name)
    absorptivity_basis, absorptivity_source = absorptivity_basis_text(material_name, laser_wavelength, prop_overrides)

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
    # dH always uses the flat INDEX CONVENTION absorptivity (P7b, eta_index), also when the powder ray tracer is
    # requested; the measured authority moves the field, never the regime label.
    enthalpy_denom = rho * cp_s * max(50.0, T_liq - T_preheat) * math.sqrt(math.pi * alpha_solid * v_scan * (r_beam ** 3))
    normalized_enthalpy = (eta_index * P_laser) / max(1e-9, enthalpy_denom)
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
            T_preheat, P_geom, rho_k, cp, alpha_th,
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

    # Seed search box from the high-speed Rosenthal width scale (kernel density rho_k, P7b)
    denom_thermal = rho_k * cp * max(50.0, T_liq - T_preheat) * v_scan
    w_analytical = math.sqrt(max(1e-12, (8.0 / (math.pi * math.e)) * (P_geom / denom_thermal)))
    search_half_w = max(d_beam * 1.8, w_analytical * 1.8, 50e-6)
    search_len = max(d_beam * 3.0, w_analytical * 4.5, 80e-6)
    search_depth = max(d_beam * 2.2, w_analytical * 2.0, 40e-6, fabbro["depth_m"] * 1.35)

    # Axial field maximum of the requested kernel: the extent search and the cross-section plane are anchored there
    # (it lies behind x = 0 at high speed). Its value is served as axialFieldMaximum_C under the P6 policy below.
    T_field(0.0, 0.0, 0.0)
    x_peak = _axial_peak_x(T_field, -search_len * 1.4 * 8.0, search_len)
    t_axial_max_C = max(float(T_field(0.0, 0.0, 0.0)), float(T_field(x_peak, 0.0, 0.0)))

    # P6 served peak: the loss-free Eagar-Tsai surface maximum at the kernel's inputs, served only below the sourced
    # vapour temperature (SPEC_p6_containment item 1 to 3). The same value for every kernel.
    loss_free = eagar_tsai_surface_maximum(T_preheat, P_geom, k_th, alpha_th, r_beam, v_scan)
    t_lossfree_max_C = float(loss_free["T_C"])
    tv_sourced = sourced_vapor_temperature(material_name)
    if tv_sourced is None:
        t_peak_C = None
        peak_unavailable_reason = f"{VAPOR_TEMPERATURE_UNSOURCED_NOTE}: the loss-free maximum cannot be checked against boiling"
        peak_exceeds_vaporization = None
        recoil_onset_status = None
        recoil_onset_reason = f"not evaluated: {VAPOR_TEMPERATURE_UNSOURCED_NOTE}"
    elif t_lossfree_max_C < tv_sourced["T_C"]:
        t_peak_C = t_lossfree_max_C
        peak_unavailable_reason = None
        peak_exceeds_vaporization = False
        recoil_onset_status = RECOIL_ONSET_BELOW
        recoil_onset_reason = None
    else:
        t_peak_C = None
        peak_unavailable_reason = PEAK_ABOVE_TV_REASON
        peak_exceeds_vaporization = True
        recoil_onset_status = RECOIL_ONSET_ABOVE
        recoil_onset_reason = None
    if source == "rosenthal":
        t_axial_served_C = None
        axial_unavailable_reason = AXIAL_MAXIMUM_ROSENTHAL_REASON
    elif tv_sourced is None:
        t_axial_served_C = None
        axial_unavailable_reason = f"{VAPOR_TEMPERATURE_UNSOURCED_NOTE}: the axial maximum cannot be checked against boiling"
    elif t_axial_max_C < tv_sourced["T_C"]:
        t_axial_served_C = t_axial_max_C
        axial_unavailable_reason = None
    else:
        t_axial_served_C = None
        axial_unavailable_reason = AXIAL_MAXIMUM_ABOVE_TV_REASON

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

    # 8. Surface temperature equals the served peak (no clip); recoil pressure is not served (no wall closure); the
    # Marangoni temperature difference reads the served peak or is unavailable (P6 containment).
    M_molar = float(props.get("M_molar_kg_mol", 0.055))  # UNSOURCED authority value (B04), echoed only
    t_surface_C = t_peak_C
    surface_temperature_basis = ("equals the served loss-free Eagar-Tsai surface maximum (no clipping)"
                                 if t_peak_C is not None else f"unavailable: {peak_unavailable_reason}")
    if t_peak_C is not None:
        ma = marangoni_screening(
            props["d_gamma_dT_N_mK"],
            props["viscosity_Pa_s"],
            alpha_th,
            float(props.get("density_liquid_kg_m3", rho)),
            w_melt_m / 2.0,
            t_peak_C,
            T_liq,
            sulfur_ppm=float(sulfur_ppm),
        )
        marangoni_number = ma["marangoniNumber"]
        marangoni_unavailable_reason = None
    else:
        flow = marangoni_flow_direction(props["d_gamma_dT_N_mK"], float(sulfur_ppm))
        ma = {**flow, "marangoniNumber": None, "surfaceVelocity_m_s": None, "pecletMarangoni": None,
              "surfaceVelocityDoi": MARANGONI_SURFACE_VELOCITY_DOI, "doi": None, "basis": MARANGONI_BAND_BASIS}
        marangoni_number = None
        marangoni_unavailable_reason = MARANGONI_UNAVAILABLE_REASON + str(peak_unavailable_reason)

    # 9. Defect Diagnostics
    # A) Lack of Fusion — Tang et al.: (h/W)^2 + (t/D)^2 ≤ 1 for full consolidation
    h_um = max(1.0, float(hatch_spacing_um))
    t_um = max(1.0, float(layer_thickness_um))
    h_over_w = h_um / max(1.0, w_melt_um)
    t_over_d = t_um / max(1.0, d_melt_um)
    lof_criterion_val = (h_over_w ** 2) + (t_over_d ** 2)
    w_over_h = w_melt_um / h_um
    d_over_t = d_melt_um / t_um

    # P7a (2026-10-11): one lack-of-fusion rule for both screens, the Tang unit criterion (Harkin 2023 Eq. 5 quoting
    # Tang, Pistorius and Beuth 2017): Pass or Fail only. The former 0.80 "Warning" band is an unsourced screening
    # threshold reported as the margin advisory flag lackOfFusionMarginAdvisory (never a status, never a verdict).
    lof_margin_advisory = bool(0.80 < lof_criterion_val <= 1.0)
    if lof_criterion_val > 1.0:
        lof_risk = "Severe Lack of Fusion (Tang index > 1 — inter-track/layer unmelt)"
        lof_status = "Fail"
    elif lof_margin_advisory:
        lof_risk = ("Full Fusion Bonding (Tang (h/W)^2+(t/D)^2 ≤ 1.0); margin advisory: index above 0.80, an unsourced "
                    "screening threshold")
        lof_status = "Pass"
    else:
        lof_risk = "Full Fusion Bonding (Tang (h/W)^2+(t/D)^2 ≤ 1.0)"
        lof_status = "Pass"

    # B) Balling / track-instability screen (lpbf_defect_diagnostics.balling_screen): Eagar–Tsai liquidus
    # L/W whatever kernel was requested (the point-source Rosenthal L/W has no beam radius). Replaces the
    # frozen steady-Rosenthal L/W > 3.8 flag (planned bump on top of Wave B f3ba9896).
    aspect_L_over_W = l_melt_um / max(1.0, w_melt_um)
    if source == "eagar-tsai":
        et_extent = (l_melt_um, w_melt_um, d_melt_um, extent_status)
    else:
        et_extent = _eagar_tsai_companion(T_preheat, P_laser, eta_base, k_th, alpha_th, rho_k, cp, r_beam, d_beam,
                                          v_scan, T_liq, fabbro["depth_m"], normalized_enthalpy)
    balling = balling_screen(*et_extent, material_name=material_name)
    if balling["band"] == "high":
        balling_risk = (f"High Balling Risk (Eagar-Tsai L/W {balling['lengthToWidth']:.2f} > "
                        f"{balling['highThreshold']}; empirical 316L-calibrated screen, unsourced screening threshold, "
                        "advisory)")
    elif balling["band"] == "moderate":
        balling_risk = (f"Moderate (Eagar-Tsai L/W {balling['lengthToWidth']:.2f} > {balling['moderateThreshold']:.2f}, "
                        "Gusarov/Yadroitsev bound; advisory)")
    elif balling["band"] == "stable":
        balling_risk = (f"Stable Continuous Track (Eagar-Tsai L/W {balling['lengthToWidth']:.2f} <= "
                        f"{balling['moderateThreshold']:.2f})")
    else:
        balling_risk = f"Unavailable (Eagar-Tsai extent {balling['extentStatus']}; no balling band)"

    # C) Powder denudation width: served null (uncited heuristic, G1 audit B05; P6 containment).

    # 10. Solidification front (SOL-A1, 2026-10-15; solidification integration contract 4.2, 4.3 item 8, 7.1): one
    # quantity container. No served liquidus is an admitted parent, so every front quantity is null with reason codes
    # (missing-source-constant naming the liquidus input; keyhole-field-inconsistent on the Fabbro keyhole leg). The
    # container is written to the result only; nothing here feeds W, D, the regime, the verdict or the process window.
    solidification_kinetics = evaluate_solidification(
        T_field,
        T_liq=T_liq,
        v_scan=v_scan,
        x_rear=x_rear,
        search_depth=search_depth,
        r_beam=r_beam,
        material_name=material_name,
        depth_from_keyhole_leg=bool(fabbro["depth_m"] > d_iso),
        authority_liquidus_C=base["liquidus_C"],
    )

    def _opt(value, digits):
        return None if value is None else round(float(value), digits)

    # 11. Residual stress and distortion: unavailable since P7a (2026-10-11, G1 audit B08/B09). The former
    # 0.72 E alpha dT / (1 - nu) and the index (layer / 40 um) / 420 MPa were unsourced; Mercelis and Kruth 2006 Sec. 2
    # supports a cap at the yield strength only, and the authority yield values are unsourced. Nothing is computed.
    recoater_risk = STRESS_UNAVAILABLE_REASON

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

    # 13. P-V Process Window Map (2D grid: power 80 to 540 W, speed 300 to 2400 mm/s). P7b (B17, B19): every cell's
    # width and liquidus depth are the served Rosenthal field extent at the authority field power (GRID_KERNEL_NOTE);
    # the former closed-form width with the unsourced d_beam^2 quadrature term and the 0.5 w depth bound are gone.
    process_map_grid = None
    keyhole_cut = regime_keyhole_cut(material_name)
    if include_process_map:
        process_map_grid = []
        p_steps = np.array([80, 150, 220, 300, 380, 460, 540], dtype=np.float64)
        v_steps = np.array([300, 600, 900, 1200, 1600, 2000, 2400], dtype=np.float64)
        dT_liq = max(50.0, T_liq - T_preheat)

        for p_val in p_steps:
            for v_val in v_steps:
                v_m = float(v_val) * 1e-3
                # Index of the cell: the index convention absorptivity, solid k and cp (as the operating point).
                denom_th = rho * cp_s * dT_liq * math.sqrt(math.pi * alpha_solid * v_m * (r_beam ** 3))
                enth = (eta_index * float(p_val)) / max(1e-9, denom_th)

                # Field extent of the cell: the served Rosenthal routine at the authority field power A P with the
                # served k, cp, rho_k and alpha convention (identical to the operating point's sequence, so a Rosenthal
                # operating point that lies on the grid reproduces its own served W and D exactly). The leg is the
                # same Fabbro leg (amplitude A authority, ramp weight from the index convention dH/hs).
                cell_p_geom = eta_base * float(p_val)
                cell_w_analytical = math.sqrt(max(1e-12, (8.0 / (math.pi * math.e))
                                                  * (cell_p_geom / (rho_k * cp * dT_liq * v_m))))
                cell_fabbro = fabbro_keyhole_depth_m(float(p_val), v_m, d_beam, k_s, alpha_solid, T_vap, T_preheat,
                                                     A_fabbro, enth)
                cell_half_w = max(d_beam * 1.8, cell_w_analytical * 1.8, 50e-6)
                cell_len = max(d_beam * 3.0, cell_w_analytical * 4.5, 80e-6)
                cell_depth = max(d_beam * 2.2, cell_w_analytical * 2.0, 40e-6, cell_fabbro["depth_m"] * 1.35)

                def cell_T(x_m, y_m, z_m, _p=cell_p_geom, _v=v_m):
                    return rosenthal_temperature_C(x_m, y_m, z_m, T_preheat, _p, k_th, _v, alpha_th, r_reg)

                cell_x_peak = _axial_peak_x(cell_T, -cell_len * 1.4 * 8.0, cell_len)
                cell_ext = _liquidus_extent(cell_T, T_liq, cell_x_peak, cell_len, cell_half_w, cell_depth, d_beam,
                                            r_beam, cell_w_analytical, enth)
                cell_status = cell_ext["extent_status"]
                if cell_status == "computed":
                    w_um = cell_ext["w_melt_m"] * 1e6
                    d_um = max(cell_ext["d_iso"], cell_fabbro["depth_m"]) * 1e6
                else:
                    w_um = None
                    d_um = None

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

                # Tang (h/W)^2 + (t/D)^2 on computed cells only; an unresolved cell keeps its enthalpy regime and no
                # Lack of Fusion Zone class (its width and depth are not an isotherm).
                keyhole_index_lof = False
                if w_um is not None:
                    tang_pt = (float(hatch_spacing_um) / max(1.0, w_um)) ** 2 + (
                        float(layer_thickness_um) / max(1.0, d_um)
                    ) ** 2
                    if tang_pt > 1.0:
                        pt_regime = "Lack of Fusion Zone"
                        color_code = "#f59e0b"  # Amber
                    # Additive flag (P1 follow-on; B19 since P7b: the per-alloy keyhole cut, 13.6 for Inconel 625): the
                    # Tang flag of a keyhole-index cell comes from the Fabbro depth, which is biased low because the
                    # keyhole absorptance A(R) is not modelled. Regime string and colour are unchanged.
                    keyhole_index_lof = bool(tang_pt > 1.0 and enth >= keyhole_cut)
                # No balling cell: the balling screen needs the Eagar–Tsai liquidus L/W, which this grid does not
                # compute (the former (1.6 + 0.55 min(6, Pe)) > 3.8 rule was Pe > 4, uncited).
                cell = {
                    "power_W": int(p_val),
                    "speed_mm_s": int(v_val),
                    "normalizedEnthalpy": round(enth, 2),
                    "regime": pt_regime,
                    "color": color_code,
                    "width_um": None if w_um is None else round(w_um, 1),
                    "depth_um": None if d_um is None else round(d_um, 1),
                    "extentStatus": cell_status,
                    "keyholeIndexLackOfFusion": keyhole_index_lof,
                }
                if keyhole_index_lof:
                    cell["lackOfFusionNote"] = KEYHOLE_INDEX_LOF_NOTE
                process_map_grid.append(cell)

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
            # P7b: the physical authority value and its basis; the index convention value and its basis.
            "absorptivityBasis": absorptivity_basis,
            "absorptivitySource": absorptivity_source,
            "indexAbsorptivity": round(eta_index, 3),
            "absorptivityIndexBasis": absorptivity_index_basis,
            "effectiveConductivity_W_mK": round(k_th, 3),
            "effectiveSpecificHeat_J_kgK": round(cp, 1),
            "kernelDensity_kg_m3": round(rho_k, 1),
            "effectiveDiffusivity_m2_s": alpha_th,
            "propertyConvention": property_convention,
            "propertyConventionBasis": property_convention_basis,
            "kernelLedgerSha256": None if kernel_ledger is None else kernel_ledger["kernelLedgerSha256"],
            "solidConductivity_W_mK": round(k_s, 3),
            "solidConductivityBasis": solid_conductivity_basis,
            "liquidConductivity_W_mK": round(k_l, 3),
            "densityBasis": density_basis,
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
            "regimeKeyholeCutBasis": keyhole_cut_basis(material_name),
            "extentStatus": extent_status,
            "extentNote": extent_note,
            "peakOffset_um": round(x_peak * 1e6, 1),
            "axialFieldMaximum_C": _opt(t_axial_served_C, 1),
            "axialFieldMaximumUnavailableReason": axial_unavailable_reason,
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
            "absorptivityBasis": ("flat-surface value, a disclosed lower bound (not Fabbro keyhole A(R), unmodelled); "
                                  + ABSORPTIVITY_AUTHORITY_SEE),
            "doi": fabbro["doi"],
            "depthBenchmarkNote": KEYHOLE_DEPTH_BENCHMARK_NOTE,
        },
        "marangoniModel": {
            "modelId": MARANGONI_MODEL_ID,
            "flowDirection": ma["flowDirection"],
            "dGamma_dT_N_mK": round(ma["dGamma_dT_N_mK"], 6),
            "sulfur_ppm": round(ma["sulfur_ppm"], 1),
            "surfaceVelocity_m_s": _opt(ma["surfaceVelocity_m_s"], 3),
            "surfaceVelocityDoi": ma.get("surfaceVelocityDoi"),
            "pecletMarangoni": _opt(ma["pecletMarangoni"], 2),
            "marangoniUnavailableReason": marangoni_unavailable_reason,
            "aspectNote": ma["aspectNote"],
            "doi": ma["doi"],
            "basis": ma.get("basis", MARANGONI_BAND_BASIS),
        },
        "hydrodynamicsAndRecoil": {
            "peakTemperature_C": _opt(t_peak_C, 1),
            "peakTemperatureBasis": PEAK_TEMPERATURE_BASIS,
            "peakTemperatureModelId": loss_free["modelId"],
            "peakTemperatureNote": PEAK_TEMPERATURE_NOTE,
            "peakUnavailableReason": peak_unavailable_reason,
            "peakLocation_x_um": None if t_peak_C is None else round(float(loss_free["x_m"]) * 1e6, 1),
            "vaporTemperatureSourced_K": None if tv_sourced is None else tv_sourced["T_K"],
            "vaporTemperatureSourced_C": None if tv_sourced is None else round(tv_sourced["T_C"], 2),
            "vaporTemperatureSource": None if tv_sourced is None else tv_sourced["source"],
            "vaporTemperatureDoi": None if tv_sourced is None else tv_sourced["doi"],
            "vaporTemperatureUnavailableReason": VAPOR_TEMPERATURE_UNSOURCED_NOTE if tv_sourced is None else None,
            "peakExceedsVaporization": peak_exceeds_vaporization,
            "surfaceTemperatureBasis": surface_temperature_basis,
            "surfaceTemperature_C": _opt(t_surface_C, 1),
            "knudsenRecoilPressure_kPa": None,
            "recoilPressureUnavailableReason": RECOIL_UNAVAILABLE_REASON,
            "recoilOnsetStatus": recoil_onset_status,
            "recoilOnsetUnavailableReason": recoil_onset_reason,
            "recoilOnsetBasis": RECOIL_ONSET_BASIS,
            "marangoniNumber": _opt(marangoni_number, 0),
            "marangoniUnavailableReason": marangoni_unavailable_reason,
            "marangoniGeometrySource": "thermal",
            "molarMass_kg_mol": round(M_molar, 5),
            "pecletThermalNumber": round(peclet_number, 2),
            "powderDenudationWidth_um": None,
            "powderDenudationUnavailableReason": DENUDATION_UNAVAILABLE_REASON,
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
            "lackOfFusionMarginAdvisory": lof_margin_advisory,
            "lackOfFusionMarginBasis": LOF_MARGIN_BASIS,
            "recoaterCrashRisk": recoater_risk,
            "effectiveResidualStress_MPa": None,
            "distortionIndex": None,
            "distortionIndexBasis": DISTORTION_INDEX_BASIS,
            "stressUnavailableReason": STRESS_UNAVAILABLE_REASON,
        },
        # SOL-A1: the front container of solidification_front.evaluate_solidification (its modelId is
        # solidification_front.MODEL_ID), full precision, no flat numeric keys, codes only (contract 4.1 item 6).
        "solidificationKinetics": solidification_kinetics,
        "materialEvidence": {"liquidusParent": liquidus_parent},
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
            "gridKernel": GRID_KERNEL,
            "gridKernelNote": GRID_KERNEL_NOTE if include_process_map else GRID_NOT_COMPUTED_NOTE,
            "keyholeIndexLackOfFusionCut": keyhole_cut,
            "grid": process_map_grid,
            "ballingNote": ("Balling is screened at the operating point only (defectDiagnostics.ballingScreen, "
                            "Eagar-Tsai L/W); the grid has no melt-pool length and marks no balling zone."),
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
