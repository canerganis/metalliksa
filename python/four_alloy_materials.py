#!/usr/bin/env python3
"""
Single source for the four locked LPBF alloys: Ti-6Al-4V, 316L, AlSi10Mg, IN718.

Thermal, slicer, Marangoni, and inherent-strain solvers look up this file.
Do not copy k, ρ, Cp, or P–v boxes into other Python modules.
Secondary alloys (CoCrMo, Scalmalloy, Cu, Hastelloy) stay local to those solvers.
"""

import hashlib
import json
import math

FOUR_ALLOY_IDS = ("ti6al4v", "ss316l", "alsi10mg", "in718")
MATERIAL_AUTHORITY = "four_alloy_materials.py"
MATERIAL_AUTHORITY_SCHEMA_VERSION = 1

# Canonical display names used by the Rosenthal thermal solver.
THERMAL_NAME = {
    "ti6al4v": "Ti-6Al-4V",
    "ss316l": "316L Stainless Steel",
    "alsi10mg": "AlSi10Mg",
    "in718": "Inconel 718",
}

SLICER_NAME = {
    "ti6al4v": "Ti-6Al-4V ELI",
    "ss316l": "SS 316L",
    "alsi10mg": "AlSi10Mg",
    "in718": "Inconel 718",
}

ALLOY_MATERIALS = {
    aid: {"thermal": THERMAL_NAME[aid], "slicer": SLICER_NAME[aid]} for aid in FOUR_ALLOY_IDS
}

# Literature P–v boxes (machine-class typical). Same numbers as lpbfFourAlloySchema.ts.
LITERATURE_PV_WINDOWS = {
    "ti6al4v": {"powerMin_W": 150, "powerMax_W": 280, "speedMin_mm_s": 700, "speedMax_mm_s": 1200},
    "ss316l": {"powerMin_W": 150, "powerMax_W": 230, "speedMin_mm_s": 600, "speedMax_mm_s": 1000},
    "alsi10mg": {"powerMin_W": 280, "powerMax_W": 380, "speedMin_mm_s": 900, "speedMax_mm_s": 1400},
    "in718": {"powerMin_W": 120, "powerMax_W": 300, "speedMin_mm_s": 550, "speedMax_mm_s": 1000},
}

_ALIAS = {
    "ti6al4v": "ti6al4v",
    "ti-6al-4v": "ti6al4v",
    "ti-6al-4v eli": "ti6al4v",
    "ti-6al-4v eli grade 23": "ti6al4v",
    "ti64": "ti6al4v",
    "ss316l": "ss316l",
    "316l": "ss316l",
    "ss 316l": "ss316l",
    "316l stainless steel": "ss316l",
    "alsi10mg": "alsi10mg",
    "alsi10mg aluminum": "alsi10mg",
    "in718": "in718",
    "inconel 718": "in718",
    "inconel 718 (ams 5662)": "in718",
}


def resolve_alloy_id(name):
    if name is None:
        return None
    key = str(name).strip().lower().replace("_", "-")
    key = " ".join(key.split())
    compact = key.replace(" ", "").replace("-", "")
    if key in _ALIAS:
        return _ALIAS[key]
    if compact in _ALIAS:
        return _ALIAS[compact]
    return None


# Thermophysical screening constants (solid k, Cp used in Rosenthal / King ΔH/hs).
_THERMAL = {
    "in718": {
        "base": "Ni",
        "liquidus_C": 1336.0,
        "solidus_C": 1260.0,
        "boiling_C": 2850.0,
        "M_molar_kg_mol": 0.0587,
        "density_kg_m3": 8190.0,
        "density_liquid_kg_m3": 7450.0,
        "thermal_conductivity_W_mK": 11.4,
        "thermal_conductivity_liquid_W_mK": 29.0,
        "specific_heat_J_kgK": 435.0,
        "specific_heat_liquid_J_kgK": 730.0,
        "latent_heat_fusion_J_kg": 270000.0,
        "latent_heat_vap_J_kg": 6400000.0,
        # P7b (2026-10-14): absorptivity_IR is the measured conduction-mode authority (ABSORPTIVITY_AUTHORITY);
        # absorptivity_index_IR is the pre-P7 convention constant of the dH/hs regime index (not a measurement);
        # thermal_conductivity_melt_W_mK / specific_heat_melt_J_kgK are the melting-point convention of the
        # conduction field (MELT_POINT_PROPERTIES). Ti-6Al-4V and AlSi10Mg carry no melt keys: their conduction
        # kernel is the Kirchhoff mean of the PROPERTY_LEDGER solid forms (kernel_properties), evaluated per call.
        "absorptivity_IR": 0.32,
        "absorptivity_index_IR": 0.38,
        "absorptivity_Green": 0.58,
        "thermal_conductivity_melt_W_mK": 29.6,
        "specific_heat_melt_J_kgK": 720.0,
        "surface_tension_N_m": 1.78,
        "d_gamma_dT_N_mK": -0.00040,
        "viscosity_Pa_s": 0.0055,
        "thermal_expansion_1_K": 13.0e-6,
        "youngs_modulus_GPa": 205.0,
        "poissons_ratio": 0.29,
        # pdas_A1 / sdas_B1 (all four alloys): unused since P7a (2026-10-11); no sourced PDAS prefactor or SDAS B1
        # exists, the solver no longer reads them, kept so canonical_material_source and materialPropertySha256 do not move.
        "pdas_A1": 80.0,
        "sdas_B1": 42.0,
    },
    "ti6al4v": {
        "base": "Ti",
        "liquidus_C": 1660.0,
        "solidus_C": 1604.0,
        "boiling_C": 3287.0,
        "M_molar_kg_mol": 0.0459,
        # P7b Amendment 1 (2026-10-14): density_kg_m3, thermal_conductivity_W_mK and specific_heat_J_kgK are room
        # temperature convention constants (regime index, Fabbro leg k_s / alpha_solid, registry solid table), not the
        # conduction kernel (PROPERTY_LEDGER Kirchhoff mean). The liquid row is Mohr 2020 (k_l Wiedemann-Franz on EML
        # resistivity p.7; cp_l Sec. 5 p.8 Fig. 4a; rho_l Eq. 21 p.5 at 1933 K); the kernel does not read it.
        "density_kg_m3": 4430.0,
        "density_liquid_kg_m3": 4087.0,
        "thermal_conductivity_W_mK": 6.7,
        "thermal_conductivity_liquid_W_mK": 29.8,
        "specific_heat_J_kgK": 526.0,
        "specific_heat_liquid_J_kgK": 930.0,
        "latent_heat_fusion_J_kg": 290000.0,
        "latent_heat_vap_J_kg": 8900000.0,
        "absorptivity_IR": 0.32,
        "absorptivity_index_IR": 0.35,
        "absorptivity_Green": 0.52,
        "surface_tension_N_m": 1.55,
        "d_gamma_dT_N_mK": -0.00028,
        "viscosity_Pa_s": 0.0042,
        "thermal_expansion_1_K": 8.6e-6,
        "youngs_modulus_GPa": 114.0,
        "poissons_ratio": 0.34,
        "pdas_A1": 65.0,
        "sdas_B1": 35.0,
    },
    "ss316l": {
        "base": "Fe",
        "liquidus_C": 1450.0,
        "solidus_C": 1385.0,
        "boiling_C": 2814.0,
        "M_molar_kg_mol": 0.0554,
        "density_kg_m3": 7990.0,
        "density_liquid_kg_m3": 6980.0,
        "thermal_conductivity_W_mK": 16.3,
        "thermal_conductivity_liquid_W_mK": 31.0,
        "specific_heat_J_kgK": 500.0,
        "specific_heat_liquid_J_kgK": 780.0,
        "latent_heat_fusion_J_kg": 270000.0,
        "latent_heat_vap_J_kg": 6250000.0,
        "absorptivity_IR": 0.30,
        "absorptivity_index_IR": 0.42,
        "absorptivity_Green": 0.62,
        "thermal_conductivity_melt_W_mK": 28.5,
        "specific_heat_melt_J_kgK": 830.0,
        "surface_tension_N_m": 1.70,
        "d_gamma_dT_N_mK": -0.00045,
        "viscosity_Pa_s": 0.0060,
        "thermal_expansion_1_K": 16.0e-6,
        "youngs_modulus_GPa": 193.0,
        "poissons_ratio": 0.30,
        "pdas_A1": 95.0,
        "sdas_B1": 48.0,
    },
    "alsi10mg": {
        "base": "Al",
        "liquidus_C": 599.0,
        "solidus_C": 567.0,
        "boiling_C": 2470.0,
        "M_molar_kg_mol": 0.0270,
        # P7b Amendment 1 (2026-10-14): density_kg_m3 2680, thermal_conductivity_W_mK 130 and specific_heat_J_kgK 910
        # are room temperature convention constants (regime index, Fabbro leg, registry solid table; unsourced); the
        # conduction kernel uses kernel_density_kg_m3 2696 (Akwaboa 2023 Table 3) with the PROPERTY_LEDGER Kirchhoff
        # mean (state as built). k_l 64 (Sun 2019 Fig. 7, extrapolated 155 K; bracket 63 to 73.4), rho_l 2393.8 at
        # 868.15 K (Assael 2012 Table 2 law 2603 - 0.241 T, evaluated at the pre-SOL-T liquidus and kept: SOL-T
        # changes no density); cp_l 1180 stays a pure Al proxy (disclosure).
        "density_kg_m3": 2680.0,
        "density_liquid_kg_m3": 2393.8,
        "kernel_density_kg_m3": 2696.0,
        "thermal_conductivity_W_mK": 130.0,
        "thermal_conductivity_liquid_W_mK": 64.0,
        "specific_heat_J_kgK": 910.0,
        "specific_heat_liquid_J_kgK": 1180.0,
        "latent_heat_fusion_J_kg": 397000.0,
        "latent_heat_vap_J_kg": 10500000.0,
        # Leis, Weber, Graf 2020 Sec. 3, Figs. 4 to 6: area II minimum on as-built AM blocks without powder, N2, 1075 nm.
        "absorptivity_IR": 0.30,
        "absorptivity_index_IR": 0.18,
        "absorptivity_Green": 0.38,
        "surface_tension_N_m": 0.85,
        # Seimiya, Yoneyama, Ozawa 2026 Table 1 (PDF p.16): Al-10 at. percent Si, EML, oxide-free droplets (binary, no Mg).
        "d_gamma_dT_N_mK": -0.000103,
        "viscosity_Pa_s": 0.0013,
        "thermal_expansion_1_K": 20.5e-6,
        "youngs_modulus_GPa": 70.0,
        "poissons_ratio": 0.33,
        "pdas_A1": 45.0,
        "sdas_B1": 22.0,
    },
}

# P7b (2026-10-14): the former per-table "absorptivity" duplicates (_MARANGONI 0.42 / 0.38 / 0.44 / 0.18 and _ISM
# 0.52 / 0.65 / 0.58 / 0.30) are deleted; marangoni_props() and inherent_strain_props() return the one authority
# value _THERMAL[aid]["absorptivity_IR"]. No solver read the duplicates (`rg absorptivity python src`, recorded in
# the P7b reasons file). The AlSi10Mg d_gamma_dT copy follows _THERMAL (Seimiya 2026 Table 1).
_MARANGONI = {
    "in718": {"critical_Ma": 4500.0, "sulfur_activity_factor": 0.000035, "d_gamma_dT_pure_N_mK": -0.00040},
    "ti6al4v": {"critical_Ma": 3800.0, "sulfur_activity_factor": 0.000015, "d_gamma_dT_pure_N_mK": -0.00028},
    "ss316l": {"critical_Ma": 4200.0, "sulfur_activity_factor": 0.000048, "d_gamma_dT_pure_N_mK": -0.00045},
    "alsi10mg": {"critical_Ma": 3200.0, "sulfur_activity_factor": 0.000010, "d_gamma_dT_pure_N_mK": -0.000103},
}

# ---------------------------------------------------------------------------------------------------------------
# P7b (2026-10-14, docs/research/SPEC_p7b_sourced_constants_2026-10-11.md section 2 and Amendment 1 item 2): ONE
# absorptivity authority for the physical field (conduction power A P of every kernel, the Fabbro leg amplitude,
# the transient, OpenFOAM and Warp paths). Wavelength 1070 nm (code key IR_1064nm), bare plate, conduction mode,
# flat pool; the powder layer is not represented. Values verified by the spec author in the PDF text of the paper
# library. The dH/hs regime index does NOT read these values: it reads absorptivity_index_IR (ABSORPTIVITY_INDEX_BASIS).
# This is a sourcing correction (goal G1), never a validation: no measured depth was read for any value here.
# ---------------------------------------------------------------------------------------------------------------
ABSORPTIVITY_BASIS_UNSOURCED = "no measurement, unsourced estimate"
ABSORPTIVITY_WAVELENGTH_NM = 1070.0
ABSORPTIVITY_AUTHORITY = {
    "in718": {
        "value": 0.32, "band": (0.28, 0.38), "wavelength_nm": ABSORPTIVITY_WAVELENGTH_NM,
        "basis": "measured-conduction-bare-plate",
        "conditions": "120 grit SiC ground bare plate, 72 um beam, 960 mm/s, argon; a laser coupling (one minus "
                      "reflected), not a calorimetric absorptance; excludes plume and evaporation losses",
        "source": "Deisenroth et al. 2026 (deisenroth2026_in718_laser_reflections.pdf)",
        "locator": "liquid IN718 nominal energy coupling 0.32; about 0.32 along the track length at 85 W (Fig. 11); "
                   "solid ground surface 0.38 (Introduction); low end 0.28 = Ye 2019 Table 1 IN625 Am by analogy",
    },
    "ss316l": {
        "value": 0.30, "band": (0.28, 0.31), "wavelength_nm": ABSORPTIVITY_WAVELENGTH_NM,
        "basis": "measured-conduction-bare-plate",
        "conditions": "polished bare discs (Trapp 2017), as machined Ra 0.17 um (Ye 2019); calorimetric, scanning",
        "source": "Trapp et al. 2017 (trapp2017.pdf); Ye et al. 2019 (ye2019.pdf); Matthews et al. 2018 "
                  "(matthews2018.pdf, qualitative cross check)",
        "locator": "Trapp 2017 Sec. 3.1, Fig. 3a: 0.29 to 0.31 (regime I); Ye 2019 Table 1 Am 0.28; Matthews 2018 "
                   "Fig. 4 (bare and powder coated discs at 1500 mm/s; the powder coated curve differs at low power, "
                   "so bare plate values do not describe a powder layer)",
    },
    "ti6al4v": {
        "value": 0.32, "band": (0.26, 0.33), "wavelength_nm": ABSORPTIVITY_WAVELENGTH_NM,
        "basis": "measured-conduction-bare-plate",
        "conditions": "polished bare plate, stationary 90 W, 5 ms, argon (Simonds 2021 and NIST mds2-2525, one "
                      "campaign); scanning as machined Ra 0.52 um (Ye 2019); two independent measurements",
        "source": "Simonds et al. 2021 (simonds2021.pdf); NIST mds2-2525 (repo summary); Ye et al. 2019 (ye2019.pdf)",
        "locator": "Simonds 2021 Sec. 3.2, PDF p.4, Fig. 3a: an average of 33 percent absorption in the first 2.4 ms, "
                   "then 66 percent once the vapour cavity forms; NIST mds2-2525 pre keyhole mean 32.5 percent; Ye "
                   "2019 Table 1 Am 0.26",
    },
    "alsi10mg": {
        "value": 0.30, "band": (0.28, 0.40), "wavelength_nm": 1075.0,
        "basis": "measured-conduction-as-built-surface",
        "conditions": "additively manufactured AlSi10Mg blocks without powder (Sa 22.3 um), N2, beams 35, 100 and 200 "
                      "um at 1/e2, 0.7 to 1.3 m/s, calorimetry (EN ISO 11551); as-built rough AM surface, not a "
                      "polished or ground plate (disclosure D9)",
        "source": "Leis, Weber, Graf 2020, Procedia CIRP 94, 173 to 176 (leis2020.pdf)",
        "locator": "Sec. 3, Figs. 4 to 6 (pp.175 to 176): area II minimum 30 percent (35 and 100 um beams) and 28 "
                   "percent (200 um); 30 to 40 percent below 1800 W/mm at 35 um; sensitivities 0.14 (Trapp 2017 Fig. 7, "
                   "Al 1100 ground, a relative alloy) and 0.40 live in PROPERTY_LEDGER",
    },
    # Secondary alloys (lpbf_thermal_solver.SECONDARY_THERMOPHYSICAL_DB), keyed by their thermal name.
    "Inconel 625": {
        "value": 0.34, "band": (0.28, 0.40), "wavelength_nm": ABSORPTIVITY_WAVELENGTH_NM,
        "basis": "measured-conduction-bare-plate",
        "conditions": "ground (400 grit SiC) bare plate, 65 um beam, 500 mm/s, calorimetry plus integrating "
                      "hemisphere; the lower end of the Deisenroth conduction range (0.40 at 80 W is near the "
                      "transition jump)",
        "source": "Deisenroth et al. 2020 (deisenroth2020_in625_energy_balance.pdf); Ye et al. 2019 (ye2019.pdf)",
        "locator": "Deisenroth 2020 Sec. 3.4, Fig. 7, PDF p.10: about 0.34 at 50 W, only 0.40 at 80 W, jump to about "
                   "0.60 at 100 W; low end Ye 2019 Table 1 Am 0.28 (Ni entry A0 0.27); Knapp 2022 Table 5 (0.277 to "
                   "0.307, calibrated) is a consistency check only",
    },
    "CoCrMo": {"value": 0.40, "band": None, "wavelength_nm": ABSORPTIVITY_WAVELENGTH_NM,
               "basis": "no-measurement-unsourced-estimate", "conditions": None, "source": None,
               "locator": "no measurement in the library"},
    "Hastelloy X": {"value": 0.39, "band": None, "wavelength_nm": ABSORPTIVITY_WAVELENGTH_NM,
                    "basis": "no-measurement-unsourced-estimate", "conditions": None, "source": None,
                    "locator": "no measurement in the library; may be read against IN625 or IN718 only as a labelled "
                               "proxy"},
    "Scalmalloy (Al-Mg-Sc-Zr)": {"value": 0.22, "band": None, "wavelength_nm": ABSORPTIVITY_WAVELENGTH_NM,
                                 "basis": "no-measurement-unsourced-estimate", "conditions": None, "source": None,
                                 "locator": "no measurement in the library"},
    "Pure Copper (Cu-OF)": {"value": 0.08, "band": None, "wavelength_nm": ABSORPTIVITY_WAVELENGTH_NM,
                            "basis": "no-measurement-unsourced-estimate", "conditions": None, "source": None,
                            "locator": "no measurement in the library"},
}
ABSORPTIVITY_INDEX_BASIS = ("convention constant of the dH/hs regime index (the cuts 15, 20, 13.6 and the King "
                            "conversion 22.2 at the pre-SOL-T 316L liquidus were derived with it); not a measurement")
# The pre-P7 served value per alloy (the index convention). Secondary alloys without a measurement: equal to their
# absorptivity_IR (the SECONDARY_THERMOPHYSICAL_DB rows carry the key).
ABSORPTIVITY_INDEX_CONVENTION = {"in718": 0.38, "ti6al4v": 0.35, "ss316l": 0.42, "alsi10mg": 0.18, "Inconel 625": 0.38}
# OI-7 (gate ruling): the AlSi10Mg index keeps 0.18 while the field absorbs 0.30; disclosed, not fixed in P7b.
ABSORPTIVITY_INDEX_NOTE_ALSI10MG = ("the index uses the convention constant 0.18 while the conduction field absorbs the "
                                    "measured 0.30 (67 percent more absorbed power), so the regime label may understate "
                                    "the onset; the cuts were derived at the convention and their re-derivation at the "
                                    "measured absorptivity is a separate lane")
# Keys of a FULL property set override (every required solver read other than the index key, for example the AM-Bench
# IN625_VALIDATION_PROPS snapshot); the Build Job snapshot freezes these plus absorptivity_index_IR. Lives in this
# manifest file so the full-set resolution rule cannot move without a fingerprint move.
INDEX_FULL_SET_KEYS = (
    "liquidus_C", "solidus_C", "boiling_C", "density_kg_m3",
    "thermal_conductivity_W_mK", "specific_heat_J_kgK",
    "absorptivity_IR", "absorptivity_Green", "latent_heat_fusion_J_kg",
    "latent_heat_vap_J_kg", "d_gamma_dT_N_mK", "viscosity_Pa_s",
    "youngs_modulus_GPa", "thermal_expansion_1_K", "poissons_ratio",
)
INDEX_KEY_IR = "absorptivity_index_IR"
MELT_KEYS = ("thermal_conductivity_melt_W_mK", "specific_heat_melt_J_kgK")
KERNEL_KEYS = ("kernel_conductivity_W_mK", "kernel_specific_heat_J_kgK", "kernel_density_kg_m3")


def absorptivity_authority(name):
    """The physical IR absorptivity entry for an alloy (four-alloy id, alias or secondary thermal name), or None."""
    aid = resolve_alloy_id(name)
    key = aid if aid is not None else str(name)
    entry = ABSORPTIVITY_AUTHORITY.get(key)
    if entry is None:
        return None
    return {"alloy": key, **entry, "band": None if entry["band"] is None else list(entry["band"]),
            "unsourced": entry["basis"] == "no-measurement-unsourced-estimate"}


# Melting-point property convention of the conduction field (spec section 3): k and cp on the liquid branch of the
# cited table at the liquidus (solid fraction 0), room-temperature density kept; alpha = k / (rho cp). Alloys without
# a source have no entry and the solver keeps the equal-weight solid/liquid blend. Rubenchik 2018 Sec. 3.1 ("the values
# will be taken at melting point where most of the energy will be deposited"); Weaver 2022 Eq. 4 and Table 2; Ye 2019
# Table 1; Mills 2002 a and b Sec. 5. Amendment 1: NO entry for Ti-6Al-4V or AlSi10Mg (their kernel is the ledger
# Kirchhoff mean); the Boivineau 28.7 / 1126 values stay only as a disputed alternative in PROPERTY_LEDGER.
MELT_POINT_PROPERTIES = {
    "in718": {
        "thermal_conductivity_melt_W_mK": 29.6, "specific_heat_melt_J_kgK": 720.0,
        "source": "Mills 2002 b (Recommended values of thermophysical properties for selected commercial alloys), "
                  "IN718 Table 1 liquid row",
        "locator": "liquid row at 1336 C (the repo liquidus): k 29.6 W/mK, cp 0.720 J/g/K, a 5.6e-6 m2/s "
                   "(the tabulated a uses the melt density 7400 kg/m3)",
        "evaluationTemperature_C": 1336.0,
        "sourceDiffusivity_m2_s": 5.6e-6,
        "bandNote": "solid side at the 1170 C row (k 29.3, cp 650) as a sensitivity; Mills k 10 percent, cp 5 percent",
    },
    "ss316l": {
        "thermal_conductivity_melt_W_mK": 28.5, "specific_heat_melt_J_kgK": 830.0,
        "source": "Mills 2002 a, 316 Table 1 liquid row; Ye 2019 Table 1",
        "locator": "Mills liquid row at 1450 C (Mills' liquidus peak; the repo liquidus is 1400 C): liquid k is "
                   "Wiedemann-Franz based, liquid cp is noisy (METALS 0.74, MTDATA 0.79 quoted in Sec. 4); Ye 2019 "
                   "Table 1 cp 0.83 J/g/K, diffusivity 0.050 cm2/s",
        "evaluationTemperature_C": 1450.0,
        "sourceDiffusivity_m2_s": 5.0e-6,
        "bandNote": "solid side 31.1 / 720 (1300 C row) as a sensitivity; Mills 316 k 10 percent, cp 5 percent",
    },
    "Inconel 625": {
        "thermal_conductivity_melt_W_mK": 28.78, "specific_heat_melt_J_kgK": 719.92,
        "source": "Weaver et al. 2022 (nihms-1855299.pdf) Table 2; Ye 2019 Table 1",
        "locator": "Weaver 2022 Table 2 (PDF p.33), listed beside T_m 1563.15 K, which equals the repo SOLIDUS "
                   "(1290 C), not the liquidus 1350 C; corroboration Ye 2019 Table 1 cp 0.72 at T_m (extrapolated), "
                   "diffusivity 0.048 cm2/s",
        "evaluationTemperature_C": 1290.0,
        "sourceDiffusivity_m2_s": 4.8e-6,
        "bandNote": "the evaluation temperature is the repo solidus; no solid-side sensitivity computed",
    },
}
PROPERTY_CONVENTION_BLEND_BASIS = "equal-weight solid and liquid blend, unsourced"


def melt_point_properties(name):
    """The melting-point k / cp entry (four-alloy id, alias or secondary thermal name), or None (blend or ledger)."""
    aid = resolve_alloy_id(name)
    key = aid if aid is not None else str(name)
    entry = MELT_POINT_PROPERTIES.get(key)
    return None if entry is None else {"alloy": key, **entry}


# ---------------------------------------------------------------------------------------------------------------
# P7b Amendment 1 item 3: PROPERTY_LEDGER, the sourced temperature dependent solid forms of Ti-6Al-4V and AlSi10Mg
# (not served numbers). The conduction kernels take ONE constant K and cp per call: the Kirchhoff integral mean of
# k_s(T) and cp_s(T) over the isotherm range from the call's preheat to the liquidus (Carslaw and Jaeger 1959 sec 1.7;
# Amendment 5 item 2 of docs/research/PREDECLARED_melt_depth_2026-10-11.md, O3 closed; Amendment 7 items 2 and 3 for
# AlSi10Mg; the Amendment 7 reference script's kirchhoff_state is ported here as a pure function, no import of a
# research script). "numeric" is the projection hashed by kernelLedgerSha256 (nodes,
# coefficients, values, slopes, ranges, state codes); "text" carries sources, locators, notes and disclosures and never
# enters a digest. The ledger is outside _THERMAL, so labelling edits move no numeric digest. Evidence kind of every
# value: Literature estimate. Nothing here was fitted to, selected with or checked against a depth.
# ---------------------------------------------------------------------------------------------------------------
PROPERTY_LEDGER = {
    "ti6al4v": {
        "numeric": {
            "schema": "kernel-ledger-linear-v1",
            "T_liq_K": 1933.15,
            "T_sol_K": 1877.15,
            # Gan 2021 SI Table 1 (PDF p.20), a fit of Mills data, 293 K to 1933 K: 26.8 and 778.2 at 1877 K.
            "k_s_linear_W_mK": {"slope": 0.0136, "intercept": 1.3097, "range_K": [293.15, 1933.15]},
            "cp_s_linear_J_kgK": {"slope": 0.1734, "intercept": 452.72, "range_K": [293.15, 1933.15]},
            "kernel_density_kg_m3": 4430.0,
            "liquid": {"k_W_mK": 29.8, "cp_J_kgK": 930.0,
                       "rho_kg_m3": {"value_at_T_liq": 4087.0, "slope_kg_m3_per_K": -0.204, "T_liq_K": 1933.15}},
            "latent_heat_fusion_J_kg": 290000.0,
            "surface": {"sigma_N_m": 1.493, "d_sigma_dT_N_mK": -1.9e-4, "d_sigma_dT_u_N_mK": 0.5e-4},
            "pins_T0_293_15K": {"K_W_mK": 16.449, "cp_J_kgK": 645.74, "alpha_m2_s": 5.750e-6},
            "pins_T0_353_15K": {"K_W_mK": 16.857, "cp_J_kgK": 650.94, "alpha_m2_s": 5.846e-6},
            "arms": {"melt_front_means": {"K_W_mK": 28.3, "cp_J_kgK": 854.0},
                     "enthalpy_consistent_cp_J_kgK": 822.6},
            "disputed": {"cp_l_J_kgK": [831.0, 1126.0], "k_l_W_mK": [28.7, 33.4], "rho_l_kg_m3": [3920.0, 4123.0],
                         "k_s_solidus_cross_check_W_mK": 26.7},
        },
        "text": {
            "k_s": "Gan 2021 SI Table 1 (PDF p.20), a fit of Mills data, 293 K to 1933 K; cross-check Boivineau 2006 "
                   "Eq. 19 (p.526), 26.7 at 1850 K, Wiedemann-Franz, 15 percent",
            "cp_s": "Gan 2021 SI Table 1 (PDF p.20), a fit of Mills data; cross-check Cezairliyan 1977 846 J/(kg K) at "
                    "1900 K (the fit about 7 percent low there); Mohr 2020 Fig. 4a 750 to 820 at 1600 to 1800 K",
            "k_l": "Mohr 2020, Adv. Eng. Mater. 22, 2000169, p.7 (Wiedemann-Franz on EML resistivity) at 1933 K; "
                   "Boivineau Eq. 20 28.7 at 1933 K (cross-check); Mills 33.4 via Gan SI (disputed sensitivity)",
            "cp_l": "Mohr 2020 Sec. 5 p.8, Fig. 4a, 0.93 +/- 0.02 J/(g K), 1760 to 1890 K; Kaschnitz 2002, 931, quoted by "
                    "Boivineau p.524; disputed: Mills 831, Boivineau Eq. 17 1126 (ledger sensitivities)",
            "rho_l": "Mohr 2020 Eq. 21 p.5 (EML on the ISS, 0.2 percent), 4087 at 1933 K, slope minus 0.204 kg/(m3 K); "
                     "cross-check Li, Johnson, Rhim 2006, 4123 at 1943 K, slope minus 0.254; disputed Mills 3920",
            "latent_heat_fusion": "Boivineau 2006 p.520 (Sec. 5.2, Fig. 8), 290 +/- 5 kJ/kg; Gan SI 286",
            "surface": "Mohr 2020 Eq. 23 (p.6) and Fig. 3b: sigma 1.493 N/m at 1933 K, dsigma/dT minus 1.9e-4 +/- 0.5e-4 "
                       "N/(m K); the served 1.55, minus 2.8e-4 and viscosity 4.2e-3 stay (no scored arm reads them)",
            "reduction": "Kirchhoff integral mean over [T_preheat, T_liquidus] (Carslaw and Jaeger 1959 sec 1.7; "
                         "Amendment 5 item 2, O3 closed); for the linear forms the evaluation at (T0 + T_liq)/2; exact "
                         "only for constant diffusivity, the Ti-6Al-4V alpha varies about 3.3 times over the range",
            "disclosures": [
                "solid density 4430 is a room temperature convention constant (OPEN O5: Mohr Eq. 20 gives 4163 at 1933 "
                "K, Gan SI lists 4420)",
                "the Ti64 cp spread 831 / 931 / 1126 is 35 percent; Ye 2019 Table 1 diffusivity 8.6e-6 conflicts by "
                "+50 percent with the served alpha",
                "the Raoult vapour arm (O4) is not served; T_v 3560.15 K, L_v 8.9e6 and M 0.0459 stay (P3 and P6 business)",
            ],
        },
    },
    "alsi10mg": {
        "numeric": {
            "schema": "kernel-ledger-nodes-v1",
            "T_liq_K": 872.15,
            "T_sol_K": 840.15,
            "default_state": "AB",
            # k_s as built, build (Z) direction: Yang 2018 Fig. 5 (25 C), Akwaboa 2023 Conclusion (3) and Fig. 2f
            # (100 to 400 C), Fetni 2024 Fig. 4a (800 K, last measured point). Node tables (T K, value).
            "k_s_nodes_W_mK": {
                "AB": [[298.15, 114.0], [373.15, 118.2], [473.15, 144.0], [573.15, 165.0], [673.15, 172.0],
                       [800.15, 168.0]],
                "HT": [[298.15, 205.5], [373.15, 206.3], [473.15, 201.6], [573.15, 193.6], [673.15, 198.0],
                       [773.15, 192.4]],
            },
            # cp_s: Yang 2018 Fig. 1, as-built second heating (AB) and the reference sample first heating (HT).
            "cp_s_nodes_J_kgK": {
                "AB": [[298.15, 893.0], [373.15, 934.0], [423.15, 952.0], [473.15, 965.0], [523.15, 974.0],
                       [573.15, 978.0], [673.15, 1074.0], [723.15, 1121.0], [773.15, 1131.0]],
                "HT": [[298.15, 927.0], [373.15, 970.0], [423.15, 988.0], [473.15, 1002.0], [523.15, 1012.0],
                       [573.15, 1010.0], [623.15, 1046.0], [673.15, 1115.0], [723.15, 1158.0], [773.15, 1172.0]],
            },
            "HT_low_factor": 173.0 / 205.5,
            "hold_above_K": {"k_AB": 800.15, "k_HT": 773.15, "cp_AB": 773.15, "cp_HT": 773.15},
            "kernel_density_kg_m3": 2696.0,
            "rho_s_range_kg_m3": [2620.0, 2715.0],
            "liquid": {"k_W_mK": 64.0, "k_bracket_W_mK": [63.0, 73.4], "cp_J_kgK_proxy": 1170.0,
                       "rho_law_kg_m3": {"c1": 2603.0, "c2_per_K": 0.241, "value_at_T_liq": 2392.8},
                       "rho_arm_ADC12_kg_m3": {"value_at_865K": 2492.0, "slope_per_K": -0.2652, "value_at_T_liq": 2490.1}},
            "latent_heat_fusion_J_kg_served": 397000.0,
            "latent_heat_fusion_J_kg_proxy": 500000.0,
            "pins_T0_293_15K": {"K_W_mK": 152.631, "cp_J_kgK": 1020.85, "alpha_m2_s": 5.546e-5},
            "pins_T0_353_15K": {"K_W_mK": 156.934, "cp_J_kgK": 1034.04, "alpha_m2_s": 5.629e-5},
            "arms": {"AB_unrelaxed_K_W_mK": 117.892, "HT_low_K_W_mK": 166.876, "HT_K_W_mK": 198.226,
                     "melt_front_means": {"K_W_mK": 116.0, "cp_J_kgK": 1150.5, "rho_kg_m3": 2544.4},
                     "enthalpy_consistent_cp_J_kgK": {"397000": 1706.5, "500000": 1884.4}},
            "disputed": {"absorptivity": [0.14, 0.40], "rho_s_kg_m3": [2620.0, 2715.0]},
        },
        "text": {
            "k_s": "Yang 2018 J. Mater. Res. 33, 4041, Fig. 5 (114 at 25 C, Z, as built); Akwaboa 2023 Materials 16, 4920, "
                   "Conclusion (3) and Fig. 2f (118.2 at 100 C, 144 at 200 C, 165 at 300 C, 172.0 at 400 C); Fetni 2024 "
                   "Fig. 4a (168 at 527 C); HT series Yang 2018 reference sample, HT-low = Yang x 173/205.5 (EOS "
                   "datasheet via Selo 2020 p.2)",
            "cp_s": "Yang 2018 Fig. 1, as-built second heating (893 at 25 C to 1131 at 500 C); cross-check Fetni 2024 "
                    "Fig. 4c; Akwaboa cp 12 to 14 percent below Yang (disclosure)",
            "rho_s": "Akwaboa 2023 Table 3, sample 100-0.2, helium pycnometer, 2.696 +/- 0.005 g/cm3 (nine samples "
                     "2.620 to 2.715); kernel only; the served density_kg_m3 2680 is a room temperature convention "
                     "constant, unsourced",
            "k_l": "Sun, Muta, Kurosaki, Ohishi 2019, Int. J. Thermophys. 40, 31, Fig. 7 (Al-Si 10 mass percent, 750 to "
                   "850 C), extrapolated 155 K down to 868 K; cross-check Brandt and Neuer 2007 Table II "
                   "(Wiedemann-Franz 63.0 to 73.4)",
            "rho_l": "Assael et al. 2012, J. Phys. Chem. Ref. Data 41, 033103, Table 2 (Al-12 mass percent Si, 858 to "
                     "1700 K), 2603 - 0.241 T; named arm Fukuyama 2023 ADC12 2492 - 0.2652 (T - 865)",
            "absorptivity": "Leis, Weber, Graf 2020 Sec. 3, Figs. 4 to 6: 0.30 area II minimum, band 0.28 to 0.40; "
                            "sensitivities 0.14 (Trapp 2017 Fig. 7, Al 1100 ground) and 0.40",
            "d_gamma_dT": "Seimiya, Yoneyama, Ozawa 2026, Table 1 (PDF p.16), Al-10 at. percent Si, EML, oxide-free "
                          "droplets only (binary, no Mg, no oxide film); Fukuyama ADC12 minus 0.0786e-3, Gheribi pure Al "
                          "minus 0.244e-3 and oxygen saturated minus 0.180e-3",
            "reduction": "Kirchhoff integral mean over [T_preheat, T_liquidus] of the piecewise linear nodes (first node "
                         "held below it, each quantity held above its last measured temperature: 800.15 K for k AB, "
                         "773.15 K for cp); Amendment 7 items 2 and 3; exact only for constant diffusivity (as built "
                         "alpha varies about 1.3 times); state AB (as built, build direction) is served, HT-low and HT "
                         "are ledger arms (no substrate state input in this bump)",
            "disclosures": [
                "SOL-T (2026-10-16, Amendment 4): T_s 840.15 K and T_l 872.15 K are the Brandt and Neuer 2007 Table II "
                "AlSi-10 heating-cycle pair (567 / 599 C), an explicit Al-9Si-0.6Mg to nominal AlSi10Mg family transfer, "
                "not a measured AlSi10Mg endpoint (no DSC on AlSi10Mg); the former 830.15 / 868.15 K were unsourced "
                "datasheet class values; datasheet 830 to 836 and 867 to 870 K",
                "SOL-T keeps every density: the served rho_l 2393.8 is the Assael law at the former 868.15 K liquidus "
                "coordinate and stays served (Amendment 4 A4.4 changes no density); the ledger law values at the new "
                "872.15 K coordinate are 2392.8 (Assael) and 2490.1 (ADC12 arm); the arms and pins above are recomputed "
                "at T_l 872.15 K",
                "latent heat of fusion 397000 is the pure Al proxy; proxy 500 kJ/kg, range 420 to 560 (Ghomashchi 2023 "
                "Al12Si DSC 554 J/g, rule of mixtures 560); the served Stefan number is descriptive only",
                "cp_l 1180 served is a pure Al and Al6061 proxy (1170, 0.8 percent apart); no kernel read",
                "k_l 64 is a 155 K extrapolation of Sun 2019 (OI-8, disclosure only)",
                "mixed provenance of the solid set: k from Akwaboa, Yang and Fetni (three machines), cp from Yang, rho "
                "from Akwaboa; the kernel alpha is a derived number, not a measured diffusivity",
                "T_v (boiling 2470 C), L_v 1.05e7 and M 0.027 have no primary locator (OPEN O8): S2 and every vapour "
                "dependent output stay unavailable",
                "the measured absorptance is on an as-built rough AM surface in N2; a ground or polished plate may differ",
            ],
        },
    },
}
KERNEL_LEDGER_BASIS = ("conduction k and cp are the Kirchhoff integral mean of the sourced solid k(T) and cp(T) over the "
                       "isotherm range from the preheat to the liquidus (Carslaw and Jaeger 1959 sec 1.7); exact only "
                       "for constant diffusivity (Ti-6Al-4V alpha varies about 3.3 times over the range, AlSi10Mg as "
                       "built about 1.3 times); the liquid k, cp and density do not enter")
KERNEL_LEDGER_STATE_NOTE_ALSI10MG = "state as built, build direction, held above 800.15 K for k and 773.15 K for cp"
SOLID_CONDUCTIVITY_BASIS_LEDGER = ("room temperature value used by the regime index, the keyhole leg and the transient "
                                   "table; the conduction field uses the kernel mean")
KERNEL_T0_FLOOR_K = 293.15
KERNEL_ISOTHERM_FLOOR_K = 50.0


def _piecewise_hold(nodes, t):
    """Piecewise linear value through (T, value) nodes; the first node held below it, the last held above it."""
    if t <= nodes[0][0]:
        return float(nodes[0][1])
    for (t1, v1), (t2, v2) in zip(nodes, nodes[1:]):
        if t <= t2:
            return float(v1 + (v2 - v1) * (t - t1) / (t2 - t1))
    return float(nodes[-1][1])


def _kirchhoff_mean_nodes(nodes, t0, t1):
    """Exact mean of the piecewise linear form over [t0, t1] (trapezoids between the knots inside the range)."""
    pts = sorted({t0, t1, *[float(k) for k, _ in nodes if t0 < k < t1]})
    area = 0.0
    for a, b in zip(pts, pts[1:]):
        area += 0.5 * (_piecewise_hold(nodes, a) + _piecewise_hold(nodes, b)) * (b - a)
    return area / (t1 - t0)


def _kirchhoff_mean_linear(form, t0, t1):
    """Mean of slope T + intercept over [t0, t1]: the evaluation at the midpoint."""
    return float(form["slope"]) * 0.5 * (t0 + t1) + float(form["intercept"])


def kernel_ledger_sha256(name):
    """sha256 of the canonical JSON of the ledger's numeric projection, or None (no ledger entry)."""
    aid = resolve_alloy_id(name)
    entry = PROPERTY_LEDGER.get(aid) if aid else None
    if entry is None:
        return None
    payload = json.dumps(entry["numeric"], sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True, allow_nan=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def kernel_properties(name, T0_K, T_liq_K=None, state=None):
    """Kirchhoff kernel (K, cp, rho_k, alpha) of a ledger alloy at the call's preheat, or None (no ledger entry).

    The mean runs over [max(293.15 K, min(T0, T_liq - 50 K)), T_liq]: a preheat below 293.15 K evaluates the forms
    from 293.15 K (the first value held), a preheat within 50 K of the liquidus uses the floored range of the solver
    (max(50, T_liq - T0)), and a preheat at or above the liquidus is refused as invalid input (the served solver does
    not refuse it earlier). T_liq_K defaults to the ledger's liquidus; a caller that overrides liquidus_C passes its own.
    """
    aid = resolve_alloy_id(name)
    entry = PROPERTY_LEDGER.get(aid) if aid else None
    if entry is None:
        return None
    num = entry["numeric"]
    t_liq = float(num["T_liq_K"] if T_liq_K is None else T_liq_K)
    t0_req = float(T0_K)
    if not math.isfinite(t0_req) or not math.isfinite(t_liq):
        raise ValueError("kernel_properties needs finite temperatures")
    if t0_req >= t_liq:
        raise ValueError(f"preheat {t0_req:.2f} K is at or above the liquidus {t_liq:.2f} K: no conduction kernel")
    t0 = max(KERNEL_T0_FLOOR_K, min(t0_req, t_liq - KERNEL_ISOTHERM_FLOOR_K))
    if num["schema"] == "kernel-ledger-linear-v1":
        state_code = None
        K = _kirchhoff_mean_linear(num["k_s_linear_W_mK"], t0, t_liq)
        cp = _kirchhoff_mean_linear(num["cp_s_linear_J_kgK"], t0, t_liq)
    else:
        state_code = str(state or num["default_state"])
        base_state = "HT" if state_code.startswith("HT") else "AB"
        k_nodes = num["k_s_nodes_W_mK"][base_state]
        if state_code == "AB_unrelaxed":
            k_nodes = k_nodes[:2]
        scale = float(num["HT_low_factor"]) if state_code == "HT_low" else 1.0
        K = scale * _kirchhoff_mean_nodes(k_nodes, t0, t_liq)
        cp = _kirchhoff_mean_nodes(num["cp_s_nodes_J_kgK"][base_state], t0, t_liq)
    rho_k = float(num["kernel_density_kg_m3"])
    return {
        "alloy": aid,
        "kernel_conductivity_W_mK": float(K),
        "kernel_specific_heat_J_kgK": float(cp),
        "kernel_density_kg_m3": rho_k,
        "alpha_m2_s": float(K) / (rho_k * float(cp)),
        "T0_K": t0,
        "T0_requested_K": t0_req,
        "T_liq_K": t_liq,
        "state": state_code,
        "kernelLedgerSha256": kernel_ledger_sha256(aid),
        "endpointAdmission": endpoint_admission(aid),
    }


def _absorptivity_provenance(aid):
    entry = ABSORPTIVITY_AUTHORITY[aid]
    return {
        "absorptivity_IR": {
            "value": entry["value"],
            "basis": entry["basis"],
            "scope": (f"{entry['wavelength_nm']:g} nm, conduction mode, flat pool; "
                      + ("as-built rough AM surface in N2, not a polished or ground plate; "
                         if aid == "alsi10mg" else "bare plate; ")
                      + "not a powder layer value"),
            "source": entry["source"],
            "locator": entry["locator"],
            "note": entry["conditions"],
        },
        "absorptivity_index_IR": {
            "value": ABSORPTIVITY_INDEX_CONVENTION[aid],
            "basis": "regime-index-convention",
            "scope": "dH/hs regime index only (pre-P7 served value)",
            "source": "pre-P7 served value of this alloy (the convention the cuts 15, 20 and 13.6 were derived with)",
            "locator": "lpbf_thermal_solver.REGIME_THRESHOLD_BASIS; tools/lpbf_keyhole_benchmark.king_conversion (22.2)",
            "note": ABSORPTIVITY_INDEX_BASIS,
        },
    }


def _melt_point_provenance(aid):
    entry = MELT_POINT_PROPERTIES[aid]
    shared = {"basis": "cited-secondary", "scope": "conduction field k and cp at the melting point (room temperature "
              "density kept); the index and the Fabbro leg keep the solid values",
              "source": entry["source"], "locator": entry["locator"], "note": entry["bandNote"]}
    return {
        "thermal_conductivity_melt_W_mK": {"value": entry["thermal_conductivity_melt_W_mK"], **shared},
        "specific_heat_melt_J_kgK": {"value": entry["specific_heat_melt_J_kgK"], **shared},
    }


_ROOM_TEMPERATURE_CONVENTION_NOTE = ("room temperature convention constant, not the conduction kernel: it feeds the regime "
                                     "index, the Fabbro leg (k_s, alpha_solid) and the registry solid table; the "
                                     "conduction field uses the PROPERTY_LEDGER Kirchhoff mean (kernel_properties)")


def _ledger_provenance_ti64():
    text = PROPERTY_LEDGER["ti6al4v"]["text"]
    conv = {"basis": "assumed-screening-constant", "scope": "regime index, Fabbro leg, registry solid table",
            "source": "pre-existing served value (no locator of its own)", "locator": "four_alloy_materials._THERMAL",
            "note": _ROOM_TEMPERATURE_CONVENTION_NOTE}
    return {
        "thermal_conductivity_W_mK": {"value": 6.7, **conv},
        "specific_heat_J_kgK": {"value": 526.0, **conv},
        "density_kg_m3": {"value": 4430.0, **conv, "note": _ROOM_TEMPERATURE_CONVENTION_NOTE + "; OPEN O5"},
        "thermal_conductivity_liquid_W_mK": {
            "value": 29.8, "basis": "cited-primary", "scope": "registry and transient liquid table and display; the "
            "conduction kernel does not read it", "source": "Mohr et al. 2020, Adv. Eng. Mater. 22, 2000169",
            "locator": "p.7, Wiedemann-Franz on EML resistivity, 1933 K", "note": text["k_l"]},
        "specific_heat_liquid_J_kgK": {
            "value": 930.0, "basis": "cited-primary", "scope": "registry and transient liquid table and display; the "
            "conduction kernel does not read it", "source": "Mohr et al. 2020, Adv. Eng. Mater. 22, 2000169",
            "locator": "Sec. 5 p.8, Fig. 4a, 0.93 +/- 0.02 J/(g K)", "note": text["cp_l"]},
        "density_liquid_kg_m3": {
            "value": 4087.0, "basis": "cited-primary", "scope": "registry liquid table, Marangoni screening",
            "source": "Mohr et al. 2020, Adv. Eng. Mater. 22, 2000169", "locator": "Eq. 21 p.5 (EML on the ISS), 1933 K",
            "note": text["rho_l"]},
        "latent_heat_fusion_J_kg": {
            "value": 290000.0, "basis": "cited-primary", "scope": "Stefan number (descriptive) and the registry",
            "source": "Boivineau et al. 2006", "locator": "p.520 (Sec. 5.2, Fig. 8), 290 +/- 5 kJ/kg",
            "note": text["latent_heat_fusion"]},
        "kernel_ledger": {
            "value": None, "basis": "cited-primary", "scope": "conduction kernel (Kirchhoff mean per call)",
            "source": "Gan 2021 SI Table 1 (k_s, cp_s fits of Mills data)", "locator": "PDF p.20",
            "note": text["reduction"]},
    }


def _ledger_provenance_alsi10mg():
    text = PROPERTY_LEDGER["alsi10mg"]["text"]
    conv = {"basis": "unsourced-estimate", "scope": "regime index, Fabbro leg, registry solid table",
            "source": None, "locator": "four_alloy_materials._THERMAL",
            "note": _ROOM_TEMPERATURE_CONVENTION_NOTE + "; unsourced"}
    return {
        "thermal_conductivity_W_mK": {"value": 130.0, **conv},
        "specific_heat_J_kgK": {"value": 910.0, **conv},
        "density_kg_m3": {"value": 2680.0, **conv,
                          "note": "2680, room temperature convention constant, unsourced; the conduction kernel uses 2696"},
        "kernel_density_kg_m3": {
            "value": 2696.0, "basis": "cited-primary", "scope": "every kernel read of rho (alpha, denom_thermal, the "
            "companion, Goldak, the grid, the slices); not the index or the Fabbro leg",
            "source": "Akwaboa et al. 2023, Materials 16, 4920", "locator": "Table 3 (PDF p.5), sample 100-0.2, helium "
            "pycnometer, 2.696 +/- 0.005 g/cm3", "note": text["rho_s"]},
        "thermal_conductivity_liquid_W_mK": {
            "value": 64.0, "basis": "cited-primary", "scope": "registry and transient liquid table and display; the "
            "conduction kernel does not read it", "source": "Sun, Muta, Kurosaki, Ohishi 2019, Int. J. Thermophys. 40, 31",
            "locator": "Fig. 7 (Al-Si 10 mass percent, 750 to 850 C), extrapolated 155 K down to 868 K",
            "note": text["k_l"]},
        "density_liquid_kg_m3": {
            "value": 2393.8, "basis": "cited-primary", "scope": "registry liquid table, Marangoni screening",
            "source": "Assael et al. 2012, J. Phys. Chem. Ref. Data 41, 033103",
            "locator": "Table 2 (Al-12 mass percent Si, 858 to 1700 K), 2603 - 0.241 T at 868.15 K", "note": text["rho_l"]},
        "specific_heat_liquid_J_kgK": {
            "value": 1180.0, "basis": "unsourced-estimate", "scope": "registry liquid table; no kernel read",
            "source": None, "locator": "pure Al and Al6061 proxy (1170, Amendment 7 item 6.3; 0.8 percent apart)",
            "note": "proxy, disclosure only"},
        # liquidus_C / solidus_C: SOL-T admission records (_endpoint_provenance, below ENDPOINT_ADMISSIONS).
        "latent_heat_fusion_J_kg": {"value": 397000.0, "basis": "unsourced-estimate", "scope": "Stefan number "
                                    "(descriptive) and the registry", "source": None,
                                    "locator": "pure Al proxy; Ghomashchi 2023 Al12Si DSC 554 J/g, rule of mixtures 560",
                                    "note": "proxy 500 kJ/kg, range 420 to 560 (disclosure)"},
        "kernel_ledger": {
            "value": None, "basis": "cited-primary", "scope": "conduction kernel (Kirchhoff mean per call, state AB)",
            "source": "Yang 2018 Fig. 5 and Fig. 1; Akwaboa 2023 Conclusion (3), Fig. 2f, Table 3; Fetni 2024 Fig. 4a",
            "locator": "PROPERTY_LEDGER['alsi10mg']", "note": text["reduction"]},
    }


# Per-property provenance for values in _THERMAL/_MARANGONI. Kept OUT of _THERMAL so that
# canonical_material_source() digests (and every identity derived from them) are unchanged by
# labelling. "basis" vocabulary: cited-primary | cited-secondary | assumed-screening-constant |
# unsourced-estimate | measured-conduction-bare-plate | measured-conduction-as-built-surface |
# no-measurement-unsourced-estimate | regime-index-convention | admitted-nominal-convention (SOL-T endpoints).
PROPERTY_PROVENANCE = {
    "in718": {
        **_absorptivity_provenance("in718"),
        **_melt_point_provenance("in718"),
        "d_gamma_dT_N_mK": {
            "value": -0.00040,
            "basis": "cited-primary",
            "scope": "zero-O, zero-S alloy (upper bound for commercial melts)",
            "source": ("Mills, Youssef, Li & Su, ISIJ Int. 46(5) (2006) 623-632, "
                       "doi:10.2355/isijinternational.46.623, section 11.3, Eq. (24): "
                       "-0.4 mN/(m K), identical to pure Ni, for every Ni superalloy"),
            "commercialMeasured_N_mK": -0.00011,
            "commercialMeasuredSource": ("Brooks et al. oscillating drop, as cited by Mills et al. 2006 "
                                         "(section 11.1) and by Sabau et al., Metall. Mater. Trans. B 51 (2020), "
                                         "doi:10.1007/s11663-020-01808-w ('For IN718, dσ/dT was measured to be "
                                         "-1.1e-4', ref. 55)"),
            "note": ("Marangoni numbers built from this value are zero-O/S upper bounds, about 3.6x the "
                     "value implied by the measured commercial coefficient."),
        },
    },
    "ti6al4v": {**_absorptivity_provenance("ti6al4v"), **_ledger_provenance_ti64()},
    "ss316l": {**_absorptivity_provenance("ss316l"), **_melt_point_provenance("ss316l")},
    "alsi10mg": {
        **_absorptivity_provenance("alsi10mg"),
        **_ledger_provenance_alsi10mg(),
        "d_gamma_dT_N_mK": {
            "value": -0.000103,
            "basis": "cited-primary",
            "scope": ("binary Al-10 at. percent Si, EML, oxide-free droplets only (no Mg, no oxide film): a proxy for "
                      "the AlSi10Mg melt; read by the transient and OpenFOAM marangoniNumber and the capability display"),
            "source": ("Seimiya, Yoneyama, Ozawa 2026, Table 1 (PDF p.16; Research Square rs-10699497, published "
                       "Int. J. Thermophys., doi 10.1007/s10765-026-03847-y)"),
            "locator": "Table 1 (PDF p.16): minus 0.103 +/- 0.004 mN/(m K), 1476 to 1981 K",
            "note": ("P7b (2026-10-14) replaced the former unsourced -3.5e-4 (the Mukherjee 2018 model input); the "
                     "transient marangoniNumber falls by x0.294. Fukuyama ADC12 -0.0786e-3, Gheribi pure Al -0.244e-3 and "
                     "oxygen saturated -0.180e-3 are ledger sensitivities. Marangoni modelling stays out of scope."),
        },
    },
    "Inconel 625": {**_absorptivity_provenance("Inconel 625"), **_melt_point_provenance("Inconel 625")},
    "*": {
        "emissivity": {
            "value": 0.35,
            "basis": "assumed-screening-constant",
            "source": None,
            "note": ("Applied to every legacy alloy and to IN625. Ni superalloys: 0.1-0.2 polished, 0.8-0.9 "
                     "oxidised (Mills et al. 2006, section 12.1); powder-bed effective values are higher than "
                     "polished bulk Cu/Al. Radiative loss is negligible against laser input in these solvers."),
        },
    },
}

_ISM = {
    "in718": {
        "yield_MPa": 1180.0,
        "uts_MPa": 1420.0,
        "cracking_susceptibility": "High",
    },
    "ti6al4v": {
        "yield_MPa": 950.0,
        "uts_MPa": 1050.0,
        "cracking_susceptibility": "Moderate",
    },
    "ss316l": {
        "yield_MPa": 530.0,
        "uts_MPa": 650.0,
        "cracking_susceptibility": "Low",
    },
    "alsi10mg": {
        "yield_MPa": 240.0,
        "uts_MPa": 390.0,
        "cracking_susceptibility": "Moderate",
    },
}

for _aid in FOUR_ALLOY_IDS:
    assert _THERMAL[_aid]["absorptivity_IR"] == ABSORPTIVITY_AUTHORITY[_aid]["value"], _aid
    assert _THERMAL[_aid]["absorptivity_index_IR"] == ABSORPTIVITY_INDEX_CONVENTION[_aid], _aid
    if _aid in MELT_POINT_PROPERTIES:
        assert _aid not in PROPERTY_LEDGER, _aid
        for _key in MELT_KEYS:
            assert _THERMAL[_aid][_key] == MELT_POINT_PROPERTIES[_aid][_key], (_aid, _key)
    else:
        assert all(_key not in _THERMAL[_aid] for _key in MELT_KEYS), _aid
        assert _aid in PROPERTY_LEDGER, _aid
    assert "absorptivity" not in _MARANGONI[_aid] and "absorptivity" not in _ISM[_aid], _aid
assert _THERMAL["alsi10mg"]["d_gamma_dT_N_mK"] == _MARANGONI["alsi10mg"]["d_gamma_dT_pure_N_mK"]
assert _THERMAL["alsi10mg"]["kernel_density_kg_m3"] == PROPERTY_LEDGER["alsi10mg"]["numeric"]["kernel_density_kg_m3"]
del _aid, _key

# Screening Rosenthal vs reference single-track W/D, or King class when W/D is not claimed.
# The keys keep their historical names ("publishedWidth_um", ...); "widthDepthBasis" says what the
# numbers are. Only "published-measurement" would be a measured, cited track; none of these is.
# King et al. 2014 (doi 10.1016/j.jmatprotec.2014.06.005, keyhole-mode LPBF of 316L) is cited only for
# the normalized-enthalpy regime threshold: King did not measure these tracks (and did not study IN718).
LITERATURE_MELT_POOL_CASES = [
    {
        "id": "ti64-rosenthal-proof003",
        "alloy_id": "ti6al4v",
        "label": "Ti-6Al-4V Rosenthal asymptotic",
        "laserPower_W": 200,
        "scanSpeed_mm_s": 900,
        "beamDiameter_um": 80,
        "preheatTemp_C": 150,
        "layerThickness_um": 30,
        "hatchSpacing_um": 100,
        "publishedWidth_um": 125.0,
        "publishedDepth_um": 62.5,
        "publishedRegime": "Transition",
        "source": ("Rosenthal 3D moving source high-speed asymptotic (PROOF 003); Rosenthal, Trans. ASME 68 "
                   "(1946) 849-865"),
        "doi": "10.1115/1.4018624",
        "widthDepthBasis": "analytical-asymptotic-not-measured",
        "check": "class",
    },
    {
        "id": "ss316l-king-window",
        "alloy_id": "ss316l",
        "label": "316L typical LPBF track (typical values, not published)",
        "laserPower_W": 200,
        "scanSpeed_mm_s": 800,
        "beamDiameter_um": 70,
        "preheatTemp_C": 80,
        "layerThickness_um": 30,
        "hatchSpacing_um": 100,
        "publishedWidth_um": 140.0,
        "publishedDepth_um": 70.0,
        "publishedRegime": "Transition",
        "source": ("Typical 316L single-track W/D (not a published measurement; not from King et al. 2014, "
                   "which measured 316L at other parameters); regime class per the King et al. 2014 "
                   "normalized-enthalpy threshold"),
        "doi": "10.1016/j.jmatprotec.2014.06.005",
        "widthDepthBasis": "typical-not-published",
        "check": "class",
    },
    {
        "id": "in718-nist-amb2022-03-0",
        "alloy_id": "in718",
        "label": "IN718 NIST AMB2022-03 case 0 (measured bare-plate track)",
        "laserPower_W": 285,
        "scanSpeed_mm_s": 960,
        "beamDiameter_um": 67,
        "preheatTemp_C": 23.5,
        "layerThickness_um": 40,
        "hatchSpacing_um": 100,
        "publishedWidth_um": 136.3,
        "publishedDepth_um": 139.7,
        "publishedRegime": None,
        "source": ("Lane et al., Integr. Mater. Manuf. Innov. (2024) Table 4 case 0 (AMB2022-03 baseline), "
                   "mean of six optical cross-sections; bare plate, D4sigma 67 um; same row as "
                   "meltpool_literature_catalog.TRACKS['nist-amb2022-03-0']. No regime label is published; "
                   "layer/hatch are placeholders the single-track kernel does not use."),
        "doi": "10.1007/s40192-024-00355-5",
        "widthDepthBasis": "published-measurement",
        "check": "wd",
    },
    {
        "id": "alsi10mg-read-window",
        "alloy_id": "alsi10mg",
        "label": "AlSi10Mg Read-style P-v window",
        "laserPower_W": 370,
        "scanSpeed_mm_s": 1300,
        "beamDiameter_um": 100,
        "preheatTemp_C": 150,
        "layerThickness_um": 30,
        "hatchSpacing_um": 130,
        "publishedWidth_um": None,
        "publishedDepth_um": None,
        "publishedRegime": "Conduction",
        "source": "Read et al., Mater. Des. (2015) process window — class only (no published W/D)",
        "doi": "10.1016/j.matdes.2014.09.044",
        "widthDepthBasis": None,
        "check": "class",
    },
]


def thermal_props(name):
    aid = resolve_alloy_id(name)
    if aid is None:
        return None
    return _THERMAL[aid]



# SOL-T Amendment 4: nominal fixed-isotherm conventions, never specimen measurements.
# Frozen copies of the complete reviewed, dated admission records.
ENDPOINT_ADMISSIONS = {'ti6al4v': {'record': {'id': 'ti6al4v',
                        'decision': 'admit-nominal-research-convention',
                        'sourceId': 'SOLT-GAN-TI',
                        'sourceCheck': 'SOLT-GAN-TI-PAIR',
                        'original': {'values': [1877, 1933], 'unit': 'K'},
                        'endpoint_K': [1877.15, 1933.15],
                        'baseline_C': [1604, 1660],
                        'delta_K': [0, 0],
                        'admissionClass': 'fixed-front-literature-model',
                        'chemistryMatch': 'not-established',
                        'uncertainty': {'type': 'not-quantified',
                                        'coverage': 'No statistical coverage; unknown model, rate, '
                                                    'chemistry/state-transfer biases'},
                        'scope': 'Named nominal-alloy fixed-front research approximation only; complete request '
                                 'chemistry/state retained. Explicit per-quantity convention/transfer disclosure '
                                 'required. No arbitrary composition inheritance. USER-VISIBLE LABEL: Cezairliyan '
                                 'reports solidus 1942.6 K with estimated total inaccuracy 8 K (coverage '
                                 'unspecified), 9.45 K above this convention liquidus 1933.15 K; unresolved '
                                 'batch/observable/rate/temperature-scale contradiction.',
                        'refusedScope': 'Measured or assessed exact-specimen endpoints; automatic '
                                        'user-composition admission; physical validation; restoration of local '
                                        'SOL-A1 quantities before SOL-C',
                        'sourceChemistry': 'Named Ti64 only; batch assay and state unknown; Fe/O not silently '
                                           'removed',
                        'solidusDefinition': 'Source-model solidus isotherm; unknown; no measured endpoint '
                                             'criterion published for this model input',
                        'liquidusDefinition': 'Source-model liquidus isotherm; unknown; no measured endpoint '
                                              'criterion published for this model input',
                        'method': 'Gan2021 compiled thermal-model prescription; upstream numeric lineage '
                                  'unresolved',
                        'rate': 'not applicable to adopted model; upstream measurement rate unknown',
                        'cycle': 'not applicable to adopted model; upstream experimental cycle unknown',
                        'direction': 'not applicable to adopted model; upstream direction unknown',
                        'pairingStatus': 'same source model/table; no same-cycle measurement claim',
                        'transfer': 'Gan nominal Ti64 convention to nominal Ti64 screening; exact chemistry match '
                                    'not established; Cezairliyan solidus contradiction unresolved; integer-273 '
                                    'conversion interpretation disclosed, not a verified upstream Celsius pair',
                        'parentIdentity': {'recordId': 'SOL-T-A4-ti6al4v',
                                           'endpoint_K': [1877.15, 1933.15],
                                           'sourceSha256': '22a8d2dc870bbd83f6bd3330899437911733f9335d52758d95a328bd6993d6e5',
                                           'requiredRuntimeBindings': ['complete original and solved chemistry '
                                                                       'with units',
                                                                       'material state',
                                                                       'source locator and transfer scope',
                                                                       'field/model/solver revision and full '
                                                                       'process vector',
                                                                       'threshold-dependent property convention '
                                                                       'and numerical settings',
                                                                       'admission-record canonical hash'],
                                           'conversion': {'rule': 'compiled-K-integer-273-interpretation',
                                                          'offset_K': 0.15,
                                                          'interpreted_C': [1604, 1660],
                                                          'sameLineageKChecks': [],
                                                          'interpretation': 'Inferred Celsius pair from the '
                                                                            'cross-checkable IN718, SS316 and '
                                                                            'IN625 integer-273 pattern; Ti64 '
                                                                            'upstream Celsius row not read. '
                                                                            'Original Gan K text retained; no '
                                                                            'physical accuracy claim.'}},
                        'conversion': {'rule': 'compiled-K-integer-273-interpretation',
                                       'offset_K': 0.15,
                                       'interpreted_C': [1604, 1660],
                                       'sameLineageKChecks': [],
                                       'interpretation': 'Inferred Celsius pair from the cross-checkable IN718, '
                                                         'SS316 and IN625 integer-273 pattern; Ti64 upstream '
                                                         'Celsius row not read. Original Gan K text retained; no '
                                                         'physical accuracy claim.'}},
             'recordSha256': '25953a4a59c06e25e049aa1ee6291d51aef46bcdae16f3586940cf841e3e5840',
             'sourceLocator': 'Gan2021 SI PDF20 Supplementary Table1 Ti64; integer-273 interpretation',
             'scope': 'Named nominal-alloy fixed-front research approximation only; complete request '
                      'chemistry/state retained. Explicit per-quantity convention/transfer disclosure required. '
                      'No arbitrary composition inheritance. USER-VISIBLE LABEL: Cezairliyan reports solidus '
                      '1942.6 K with estimated total inaccuracy 8 K (coverage unspecified), 9.45 K above this '
                      'convention liquidus 1933.15 K; unresolved batch/observable/rate/temperature-scale '
                      'contradiction. Gan nominal Ti64 convention to nominal Ti64 screening; exact chemistry '
                      'match not established; Cezairliyan solidus contradiction unresolved; integer-273 '
                      'conversion interpretation disclosed, not a verified upstream Celsius pair',
             'sourceEvidenceKind': 'Literature estimate',
             'kind': 'modelConvention',
             'status': 'admitted-convention'},
 'alsi10mg': {'record': {'id': 'alsi10mg',
                         'decision': 'admit-nominal-research-convention',
                         'sourceId': 'SOLT-BRANDT-AL',
                         'sourceCheck': 'SOLT-BRANDT-AL-HEATING',
                         'original': {'values': [567, 599], 'unit': 'degC'},
                         'endpoint_K': [840.15, 872.15],
                         'baseline_C': [557, 595],
                         'delta_K': [10, 4],
                         'admissionClass': 'fixed-front-explicit-family-transfer',
                         'chemistryMatch': 'not-established',
                         'uncertainty': {'type': 'not-quantified',
                                         'coverage': 'No statistical coverage; unknown model, rate, '
                                                     'chemistry/state-transfer biases'},
                         'scope': 'Named nominal-alloy fixed-front research approximation only; complete request '
                                  'chemistry/state retained. Explicit per-quantity convention/transfer disclosure '
                                  'required. No arbitrary composition inheritance.',
                         'refusedScope': 'Measured or assessed exact-specimen endpoints; automatic '
                                         'user-composition admission; physical validation; restoration of local '
                                         'SOL-A1 quantities before SOL-C',
                         'sourceChemistry': {'Si_wt_pct': 9,
                                             'Mg_wt_pct': 0.6,
                                             'balance': 'Al',
                                             'otherElements': 'unreported, not zero',
                                             'state': 'Hydro MEBSP alloy; complete prior treatment unknown'},
                         'solidusDefinition': 'Source-labelled resistivity transition solidus boundary; '
                                              'onset/peak/end construction unknown',
                         'liquidusDefinition': 'Source-labelled resistivity transition liquidus boundary; '
                                               'onset/peak/end construction unknown',
                         'method': 'Brandt2007 four-probe resistivity, furnace/tubular ceramic crucible; heating '
                                   'row',
                         'rate': 'about 100 K/h in phase-change region; prescribed apparatus rate, not LPBF rate',
                         'cycle': 'source Table II Heating cycle; individual run/cycle number unknown',
                         'direction': 'heating',
                         'pairingStatus': 'same named sample and source-labelled Heating cycle pair; same '
                                          'individual trace not established',
                         'transfer': 'Al-9Si-0.6Mg to nominal AlSi10Mg: both Si9->nominal10 and Mg0.6->explicit '
                                     'requested Mg; impurities/state/rate transfer unquantified; no fitted '
                                     'correction',
                         'parentIdentity': {'recordId': 'SOL-T-A4-alsi10mg',
                                            'endpoint_K': [840.15, 872.15],
                                            'sourceSha256': '505f04de097d31d97ca92a35821233f198ac59aca8ff3ffc27c4ce9cb011d0f7',
                                            'requiredRuntimeBindings': ['complete original and solved chemistry '
                                                                        'with units',
                                                                        'material state',
                                                                        'source locator and transfer scope',
                                                                        'field/model/solver revision and full '
                                                                        'process vector',
                                                                        'threshold-dependent property convention '
                                                                        'and numerical settings',
                                                                        'admission-record canonical hash'],
                                            'conversion': {'rule': 'degC-plus-273.15',
                                                           'offset_K': 273.15,
                                                           'sameLineageKChecks': []}},
                         'conversion': {'rule': 'degC-plus-273.15', 'offset_K': 273.15, 'sameLineageKChecks': []}},
              'recordSha256': 'ca4a499bc021698c9214cb5aa51d4ea4282d05ec2f0741cb6ccd3ca46928bf96',
              'sourceLocator': 'Brandt2007 PDF14 / p1442 TableII AlSi-10 Heating cycle',
              'scope': 'Named nominal-alloy fixed-front research approximation only; complete request '
                       'chemistry/state retained. Explicit per-quantity convention/transfer disclosure required. '
                       'No arbitrary composition inheritance. Al-9Si-0.6Mg to nominal AlSi10Mg: both '
                       'Si9->nominal10 and Mg0.6->explicit requested Mg; impurities/state/rate transfer '
                       'unquantified; no fitted correction',
              'sourceEvidenceKind': 'Literature estimate',
              'kind': 'alloyTransfer',
              'status': 'extrapolated'},
 'in718': {'record': {'id': 'in718',
                      'decision': 'admit-nominal-research-convention',
                      'sourceId': 'SMC718',
                      'sourceCheck': 'smc718-celsius-pair',
                      'original': {'values': [1260, 1336], 'unit': 'degC'},
                      'endpoint_K': [1533.15, 1609.15],
                      'baseline_C': [1260, 1336],
                      'delta_K': [0, 0],
                      'admissionClass': 'fixed-front-literature-model',
                      'chemistryMatch': 'not-established',
                      'uncertainty': {'type': 'not-quantified',
                                      'coverage': 'No statistical coverage; unknown model, rate, '
                                                  'chemistry/state-transfer biases'},
                      'scope': 'Named nominal-alloy fixed-front research approximation only; complete request '
                               'chemistry/state retained. Explicit per-quantity convention/transfer disclosure '
                               'required. No arbitrary composition inheritance.',
                      'refusedScope': 'Measured or assessed exact-specimen endpoints; automatic user-composition '
                                      'admission; physical validation; restoration of local SOL-A1 quantities '
                                      'before SOL-C',
                      'sourceChemistry': 'Named nominal IN718; endpoint-batch assay and state unknown; not '
                                         'Pottlacher Mo4.34 batch',
                      'solidusDefinition': 'Lower compiled melting-range boundary; experimental signal criterion '
                                           'unknown; Mills tentative 1170 C eutectic solidus remains an '
                                           'unselected alternative',
                      'liquidusDefinition': 'Upper compiled melting-range boundary; experimental signal criterion '
                                            'unknown',
                      'method': 'SMC-045 September2007 PDF1 Table2 compiled melting-range prescription; Mills2002 '
                                'PDF1 agrees at 1260/1336 C but tentatively adopts 1170 C solidus separately',
                      'rate': 'not applicable to adopted model; underlying measurement rate unknown',
                      'cycle': 'not applicable to adopted model; underlying measurement cycle unknown',
                      'direction': 'not applicable to adopted model; upstream direction unknown',
                      'pairingStatus': 'same manufacturer compiled range; no same-cycle measurement claim',
                      'transfer': 'SMC-045 nominal IN718 compiled convention to nominal IN718 screening; '
                                  'Knapp1533/1609 K recorded as same-lineage integer-273 rendering '
                                  '(interpretation, not independently verified ancestry). Pottlacher DTA transfer '
                                  'refused.',
                      'parentIdentity': {'recordId': 'SOL-T-A4-in718',
                                         'endpoint_K': [1533.15, 1609.15],
                                         'sourceSha256': '6c9c60dc272cb4f7275091e02779879760afcb1801fc9bd04fbfca239907da90',
                                         'requiredRuntimeBindings': ['complete original and solved chemistry with '
                                                                     'units',
                                                                     'material state',
                                                                     'source locator and transfer scope',
                                                                     'field/model/solver revision and full '
                                                                     'process vector',
                                                                     'threshold-dependent property convention and '
                                                                     'numerical settings',
                                                                     'admission-record canonical hash'],
                                         'conversion': {'rule': 'degC-plus-273.15',
                                                        'offset_K': 273.15,
                                                        'sameLineageKChecks': ['knapp718-pair']}},
                      'conversion': {'rule': 'degC-plus-273.15',
                                     'offset_K': 273.15,
                                     'sameLineageKChecks': ['knapp718-pair']}},
           'recordSha256': 'e4170adc48b284e986ad8e1a46052c4611b05f97415e20fc7ecd99e08ed2b4b4',
           'sourceLocator': 'SMC-045 PDF1 Table2; Mills PDF1 compiled IN718',
           'scope': 'Named nominal-alloy fixed-front research approximation only; complete request '
                    'chemistry/state retained. Explicit per-quantity convention/transfer disclosure required. No '
                    'arbitrary composition inheritance. SMC-045 nominal IN718 compiled convention to nominal '
                    'IN718 screening; Knapp1533/1609 K recorded as same-lineage integer-273 rendering '
                    '(interpretation, not independently verified ancestry). Pottlacher DTA transfer refused.',
           'sourceEvidenceKind': 'Literature estimate',
           'kind': 'modelConvention',
           'status': 'admitted-convention'},
 'ss316l': {'record': {'id': 'ss316l',
                       'decision': 'admit-nominal-research-convention',
                       'sourceId': 'MILLS316',
                       'sourceCheck': 'mills316-adopted-pair',
                       'original': {'values': [1385, 1450], 'unit': 'degC'},
                       'endpoint_K': [1658.15, 1723.15],
                       'baseline_C': [1375, 1400],
                       'delta_K': [10, 50],
                       'admissionClass': 'fixed-front-transferred-literature-model',
                       'chemistryMatch': 'not-established',
                       'uncertainty': {'type': 'not-quantified',
                                       'coverage': 'No statistical coverage; unknown model, rate, '
                                                   'chemistry/state-transfer biases'},
                       'scope': 'Named nominal-alloy fixed-front research approximation only; complete request '
                                'chemistry/state retained. Explicit per-quantity convention/transfer disclosure '
                                'required. No arbitrary composition inheritance.',
                       'refusedScope': 'Measured or assessed exact-specimen endpoints; automatic user-composition '
                                       'admission; physical validation; restoration of local SOL-A1 quantities '
                                       'before SOL-C',
                       'sourceChemistry': 'Mills nominal SS316 wt% C0.08, Cr17, Cu0.3, Fe65, Mn2, Mo2.5, Ni12, '
                                          'Si1; not a measured316L batch; adopted NPL endpoint-batch assay/state '
                                          'unknown',
                       'solidusDefinition': 'Mills/NPL DPSC adopted solidus; exact onset construction unknown',
                       'liquidusDefinition': 'Mills/NPL DPSC adopted liquidus peak, not return-to-baseline',
                       'method': 'Mills2002 PDF1/printed135 adopted NPL DPSC compilation; same source as '
                                 'served316L k/cp',
                       'rate': 'not applicable to adopted model; underlying measurement rate unknown',
                       'cycle': 'not applicable to adopted model; underlying measurement cycle unknown',
                       'direction': 'not applicable to adopted model; upstream direction unknown',
                       'pairingStatus': 'same adopted DPSC compiled pair; no authenticated individual same-cycle '
                                        'measurement claim',
                       'transfer': 'EXPLICIT SS316 -> nominal316L transfer including C0.08 nominal compilation '
                                   'and other chemistry/state differences; not exact316L liquidus. Gan1658/1723 K '
                                   'is same-lineage integer-273 rendering (interpretation, not independently '
                                   'verified ancestry).',
                       'parentIdentity': {'recordId': 'SOL-T-A4-ss316l',
                                          'endpoint_K': [1658.15, 1723.15],
                                          'sourceSha256': '1acda1c90a17df10b33fff9437a1b60bd728460b39b9bb558b57f99f9a265ad6',
                                          'requiredRuntimeBindings': ['complete original and solved chemistry '
                                                                      'with units',
                                                                      'material state',
                                                                      'source locator and transfer scope',
                                                                      'field/model/solver revision and full '
                                                                      'process vector',
                                                                      'threshold-dependent property convention '
                                                                      'and numerical settings',
                                                                      'admission-record canonical hash'],
                                          'conversion': {'rule': 'degC-plus-273.15',
                                                         'offset_K': 273.15,
                                                         'sameLineageKChecks': ['gan316-pair']}},
                       'conversion': {'rule': 'degC-plus-273.15',
                                      'offset_K': 273.15,
                                      'sameLineageKChecks': ['gan316-pair']}},
            'recordSha256': 'a9d79d87f716c255dda3d1bbc76faf614289033cf5c940916ed8f6e3da66d42c',
            'sourceLocator': 'Mills/NPL DPSC PDF1 / p135 SS316 liquidus peak',
            'scope': 'Named nominal-alloy fixed-front research approximation only; complete request '
                     'chemistry/state retained. Explicit per-quantity convention/transfer disclosure required. No '
                     'arbitrary composition inheritance. EXPLICIT SS316 -> nominal316L transfer including C0.08 '
                     'nominal compilation and other chemistry/state differences; not exact316L liquidus. '
                     'Gan1658/1723 K is same-lineage integer-273 rendering (interpretation, not independently '
                     'verified ancestry).',
            'sourceEvidenceKind': 'Literature estimate',
            'kind': 'alloyTransfer',
            'status': 'extrapolated'},
 'in625': {'record': {'id': 'in625',
                      'decision': 'admit-nominal-research-convention',
                      'sourceId': 'MP04',
                      'sourceCheck': 'sabau2020-paired-prescription',
                      'original': {'values': [1290, 1350], 'unit': 'degC'},
                      'endpoint_K': [1563.15, 1623.15],
                      'baseline_C': [1290, 1350],
                      'delta_K': [0, 0],
                      'admissionClass': 'fixed-front-literature-model',
                      'chemistryMatch': 'not-established',
                      'uncertainty': {'type': 'not-quantified',
                                      'coverage': 'No statistical coverage; unknown model, rate, '
                                                  'chemistry/state-transfer biases'},
                      'scope': 'Named nominal-alloy fixed-front research approximation only; complete request '
                               'chemistry/state retained. Explicit per-quantity convention/transfer disclosure '
                               'required. No arbitrary composition inheritance.',
                      'refusedScope': 'Measured or assessed exact-specimen endpoints; automatic user-composition '
                                      'admission; physical validation; restoration of local SOL-A1 quantities '
                                      'before SOL-C',
                      'sourceChemistry': 'Named IN625; endpoint-model batch assay and state unknown',
                      'solidusDefinition': 'Lower boundary of source linear-fraction-solid constitutive interval; '
                                           'experimental criterion unknown',
                      'liquidusDefinition': 'Upper boundary of source linear-fraction-solid constitutive '
                                            'interval; experimental criterion unknown',
                      'method': 'Sabau2020 source constitutive-model prescription; literature OR JMatPro grouped '
                                'origin unresolved for these endpoints',
                      'rate': 'not applicable to adopted model; upstream measurement rate unknown',
                      'cycle': 'not applicable to adopted model; upstream experimental cycle unknown',
                      'direction': 'not applicable to adopted model; upstream direction unknown',
                      'pairingStatus': 'same source constitutive interval; no same-cycle measurement claim',
                      'transfer': 'Source IN625 constitutive interval to nominal IN625 screening; no '
                                  'primary-measurement claim; independence from CALPHAD not established',
                      'parentIdentity': {'recordId': 'SOL-T-A4-in625',
                                         'endpoint_K': [1563.15, 1623.15],
                                         'sourceSha256': '726e52b0b58ee77bed424101d4111a0813b7bcce9de0225b346c0c2a065e7377',
                                         'requiredRuntimeBindings': ['complete original and solved chemistry with '
                                                                     'units',
                                                                     'material state',
                                                                     'source locator and transfer scope',
                                                                     'field/model/solver revision and full '
                                                                     'process vector',
                                                                     'threshold-dependent property convention and '
                                                                     'numerical settings',
                                                                     'admission-record canonical hash'],
                                         'conversion': {'rule': 'degC-plus-273.15',
                                                        'offset_K': 273.15,
                                                        'sameLineageKChecks': ['gan625-paired-inputs']}},
                      'conversion': {'rule': 'degC-plus-273.15',
                                     'offset_K': 273.15,
                                     'sameLineageKChecks': ['gan625-paired-inputs']}},
           'recordSha256': 'afc0543703b0669d81b8b317674e668e4d85f612eebc45f1f07f081f9fa4b40e',
           'sourceLocator': 'Sabau2020 PDF7 / p1269 linear-fraction constitutive interval',
           'scope': 'Named nominal-alloy fixed-front research approximation only; complete request '
                    'chemistry/state retained. Explicit per-quantity convention/transfer disclosure required. No '
                    'arbitrary composition inheritance. Source IN625 constitutive interval to nominal IN625 '
                    'screening; no primary-measurement claim; independence from CALPHAD not established',
           'sourceEvidenceKind': 'Literature estimate',
           'kind': 'modelConvention',
           'status': 'admitted-convention'}}


def _endpoint_provenance(aid):
    """SOL-T: label-only endpoint provenance taken from the admission record (never a measured specimen pair)."""
    parent = ENDPOINT_ADMISSIONS[aid]
    record = parent["record"]
    shared = {"basis": "admitted-nominal-convention", "scope": "solidus / liquidus of every path (nominal convention)",
              "source": record["parentIdentity"]["recordId"], "locator": parent["sourceLocator"],
              "admissionKind": parent["kind"], "admissionStatus": parent["status"],
              "sourceEvidenceKind": parent["sourceEvidenceKind"], "note": parent["scope"]}
    return {"solidus_C": {"value": round(record["endpoint_K"][0] - 273.15, 6), **shared},
            "liquidus_C": {"value": round(record["endpoint_K"][1] - 273.15, 6), **shared}}


for _aid, _key in (("ti6al4v", "ti6al4v"), ("alsi10mg", "alsi10mg"), ("in718", "in718"), ("ss316l", "ss316l"),
                   ("in625", "Inconel 625")):
    PROPERTY_PROVENANCE[_key].update(_endpoint_provenance(_aid))


def endpoint_admission(name):
    """Copy the selected nominal convention; unknown identities fail closed."""
    compact = ''.join(str(name).lower().split()).replace('-', '')
    aid = "in625" if compact in ("in625", "inconel625") else resolve_alloy_id(name)
    return json.loads(json.dumps(ENDPOINT_ADMISSIONS[aid])) if aid in ENDPOINT_ADMISSIONS else None


def endpoint_input(name, default_value):
    """P8-shaped located input; transfer scope stays adjacent to each dependent value."""
    parent = endpoint_admission(name)
    if parent is None:
        return None
    record = parent["record"]
    return {"kind": parent["kind"], "label": parent["kind"],
            "sourceId": record["parentIdentity"]["recordId"] + ":" + parent["recordSha256"],
            "sourceLocator": parent["sourceLocator"],
            "declarationLocator": "python/four_alloy_materials.py#ENDPOINT_ADMISSIONS/" + record["id"],
            "source": record["sourceId"], "scope": parent["scope"],
            "status": "extrapolated" if parent["kind"] == "alloyTransfer" else "inRange",
            "sourceEvidenceKind": "Literature estimate", "defaultValue": default_value, "defaultKind": None,
            "followsInput": None, "followState": None, "dependsOn": [], "phase": None,
            "referenceTemperature_K": None, "sourceRange_K": None}


def canonical_material_source(alloy_id):
    """Return the locked source snapshot and digest shared by LPBF model routes."""
    aid = resolve_alloy_id(alloy_id)
    if aid is None:
        raise ValueError(f"Unsupported LPBF alloy identity: {alloy_id!r}")
    snapshot = {
        "schemaVersion": MATERIAL_AUTHORITY_SCHEMA_VERSION,
        "authority": MATERIAL_AUTHORITY,
        "alloyId": aid,
        "thermal": dict(_THERMAL[aid]),
        # P7b: the numeric projection of the kernel ledger is part of the material identity (None without a ledger),
        # so a ledger number moves the digest and a ledger text edit does not.
        "kernelLedgerSha256": kernel_ledger_sha256(aid),
        "endpointAdmission": endpoint_admission(aid),
    }
    payload = json.dumps(snapshot, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode("utf-8")
    return snapshot, hashlib.sha256(payload).hexdigest()


def four_alloy_thermophysical_db():
    db = {}
    for aid in FOUR_ALLOY_IDS:
        props = _THERMAL[aid]
        db[THERMAL_NAME[aid]] = props
        db[SLICER_NAME[aid]] = props
    return db


def slicer_props(name):
    aid = resolve_alloy_id(name)
    if aid is None:
        return None
    t = _THERMAL[aid]
    return {
        "density_gcm3": round(t["density_kg_m3"] / 1000.0, 3),
        "k_WmK": t["thermal_conductivity_W_mK"],
        "name": SLICER_NAME[aid],
    }


def marangoni_props(name):
    aid = resolve_alloy_id(name)
    if aid is None:
        return None
    t = _THERMAL[aid]
    m = _MARANGONI[aid]
    return {
        "liquidus_C": t["liquidus_C"],
        "solidus_C": t["solidus_C"],
        "boiling_C": t["boiling_C"],
        "density_kg_m3": t["density_kg_m3"],
        "liquid_density_kg_m3": t["density_liquid_kg_m3"],
        "thermal_conductivity_W_mK": t["thermal_conductivity_liquid_W_mK"],
        "specific_heat_J_kgK": t["specific_heat_liquid_J_kgK"],
        "viscosity_Pa_s": t["viscosity_Pa_s"],
        "surface_tension_pure_N_m": t["surface_tension_N_m"],
        "d_gamma_dT_pure_N_mK": m["d_gamma_dT_pure_N_mK"],
        "critical_Ma": m["critical_Ma"],
        # P7b: the one authority value (the former per-table duplicate is deleted).
        "absorptivity": t["absorptivity_IR"],
        "sulfur_activity_factor": m["sulfur_activity_factor"],
    }


def inherent_strain_props(name):
    aid = resolve_alloy_id(name)
    if aid is None:
        return None
    t = _THERMAL[aid]
    s = _ISM[aid]
    return {
        "E_GPa": t["youngs_modulus_GPa"],
        "nu": t["poissons_ratio"],
        "CTE_10e6": t["thermal_expansion_1_K"] * 1e6,
        "yield_MPa": s["yield_MPa"],
        "uts_MPa": s["uts_MPa"],
        "k_WmK": t["thermal_conductivity_W_mK"],
        "Tm_C": t["liquidus_C"],
        "Tsol_C": t["solidus_C"],
        "rho_kgm3": t["density_kg_m3"],
        # P7b: the one authority value (the former per-table duplicate is deleted).
        "absorptivity": t["absorptivity_IR"],
        "cracking_susceptibility": s["cracking_susceptibility"],
    }


def evaluate_literature_pv(alloy_id, power_W, speed_mm_s):
    aid = resolve_alloy_id(alloy_id)
    if aid is None:
        # D8: no silent IN718 fallback for an unknown alloy identity.
        raise ValueError(f"Unsupported LPBF alloy identity: {alloy_id!r}")
    box = LITERATURE_PV_WINDOWS[aid]
    inside = (
        box["powerMin_W"] <= power_W <= box["powerMax_W"]
        and box["speedMin_mm_s"] <= speed_mm_s <= box["speedMax_mm_s"]
    )
    return {"inside": inside, "box": box, "alloyId": aid}


def regime_family(regime):
    r = str(regime).lower()
    if "keyhole" in r:
        return "Keyhole"
    if "transition" in r:
        return "Transition"
    return "Conduction"


# Temperature-dependent relative uncertainties labelled U95 (k=2). ASSUMED engineering budget:
# round values chosen by the authors, NOT derived from a cited uncertainty table (no per-value
# source exists). For orientation only: Mills et al., ISIJ Int. 46 (2006) 623, section 14(2),
# gives "probable uncertainties" of its calculated Ni-superalloy properties (density 2 %, Cp 2-5 %,
# conductivity 10 %, viscosity 10 %), not k=2 budgets.
FOUR_ALLOY_U95_BUDGET_BASIS = "assumed-engineering-budget-not-derived"
FOUR_ALLOY_U95_BUDGET = {
    "in718": {
        "solid": {"k_u95_rel": 0.05, "cp_u95_rel": 0.04, "rho_u95_rel": 0.015},
        "mushy": {"k_u95_rel": 0.12, "cp_u95_rel": 0.10, "rho_u95_rel": 0.03, "latent_u95_rel": 0.10},
        "liquid": {"k_u95_rel": 0.10, "cp_u95_rel": 0.08, "rho_u95_rel": 0.035, "viscosity_u95_rel": 0.15},
    },
    "ti6al4v": {
        "solid": {"k_u95_rel": 0.06, "cp_u95_rel": 0.04, "rho_u95_rel": 0.012},
        "mushy": {"k_u95_rel": 0.15, "cp_u95_rel": 0.12, "rho_u95_rel": 0.03, "latent_u95_rel": 0.10},
        "liquid": {"k_u95_rel": 0.12, "cp_u95_rel": 0.10, "rho_u95_rel": 0.04, "viscosity_u95_rel": 0.20},
    },
    "ss316l": {
        "solid": {"k_u95_rel": 0.05, "cp_u95_rel": 0.04, "rho_u95_rel": 0.015},
        "mushy": {"k_u95_rel": 0.10, "cp_u95_rel": 0.08, "rho_u95_rel": 0.025, "latent_u95_rel": 0.08},
        "liquid": {"k_u95_rel": 0.08, "cp_u95_rel": 0.06, "rho_u95_rel": 0.03, "viscosity_u95_rel": 0.15},
    },
    "alsi10mg": {
        "solid": {"k_u95_rel": 0.05, "cp_u95_rel": 0.05, "rho_u95_rel": 0.010},
        "mushy": {"k_u95_rel": 0.12, "cp_u95_rel": 0.10, "rho_u95_rel": 0.025, "latent_u95_rel": 0.08},
        "liquid": {"k_u95_rel": 0.10, "cp_u95_rel": 0.08, "rho_u95_rel": 0.035, "viscosity_u95_rel": 0.18},
    },
}


def four_alloy_u95_at_temperature(alloy_id, property_name, temperature_k):
    """Return temperature-dependent U95 relative uncertainty for locked 4 alloys."""
    aid = resolve_alloy_id(alloy_id)
    if aid is None or aid not in FOUR_ALLOY_U95_BUDGET:
        raise ValueError(f"Unknown alloy identity for U95 budget: {alloy_id}")
    t_props = _THERMAL[aid]
    t_sol_k = t_props["solidus_C"] + 273.15
    t_liq_k = t_props["liquidus_C"] + 273.15
    budget = FOUR_ALLOY_U95_BUDGET[aid]
    if temperature_k <= t_sol_k:
        regime = "solid"
    elif temperature_k <= t_liq_k:
        regime = "mushy"
    else:
        regime = "liquid"
    key = f"{property_name}_u95_rel"
    regime_dict = budget[regime]
    if key not in regime_dict:
        if key in budget["solid"]:
            return budget["solid"][key]
        raise ValueError(f"Property {property_name} has no U95 specification in {regime} regime")
    return regime_dict[key]
