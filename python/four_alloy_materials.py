#!/usr/bin/env python3
"""
Single source for the four locked LPBF alloys: Ti-6Al-4V, 316L, AlSi10Mg, IN718.

Thermal, slicer, Marangoni, and inherent-strain solvers look up this file.
Do not copy k, ρ, Cp, or P–v boxes into other Python modules.
Secondary alloys (CoCrMo, Scalmalloy, Cu, Hastelloy) stay local to those solvers.
"""

import hashlib
import json

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
        "absorptivity_IR": 0.38,
        "absorptivity_Green": 0.58,
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
        "density_kg_m3": 4430.0,
        "density_liquid_kg_m3": 3950.0,
        "thermal_conductivity_W_mK": 6.7,
        "thermal_conductivity_liquid_W_mK": 23.0,
        "specific_heat_J_kgK": 526.0,
        "specific_heat_liquid_J_kgK": 830.0,
        "latent_heat_fusion_J_kg": 290000.0,
        "latent_heat_vap_J_kg": 8900000.0,
        "absorptivity_IR": 0.35,
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
        "liquidus_C": 1400.0,
        "solidus_C": 1375.0,
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
        "absorptivity_IR": 0.42,
        "absorptivity_Green": 0.62,
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
        "liquidus_C": 595.0,
        "solidus_C": 557.0,
        "boiling_C": 2470.0,
        "M_molar_kg_mol": 0.0270,
        "density_kg_m3": 2680.0,
        "density_liquid_kg_m3": 2390.0,
        "thermal_conductivity_W_mK": 130.0,
        "thermal_conductivity_liquid_W_mK": 85.0,
        "specific_heat_J_kgK": 910.0,
        "specific_heat_liquid_J_kgK": 1180.0,
        "latent_heat_fusion_J_kg": 397000.0,
        "latent_heat_vap_J_kg": 10500000.0,
        "absorptivity_IR": 0.18,
        "absorptivity_Green": 0.38,
        "surface_tension_N_m": 0.85,
        "d_gamma_dT_N_mK": -0.00035,
        "viscosity_Pa_s": 0.0013,
        "thermal_expansion_1_K": 20.5e-6,
        "youngs_modulus_GPa": 70.0,
        "poissons_ratio": 0.33,
        "pdas_A1": 45.0,
        "sdas_B1": 22.0,
    },
}

_MARANGONI = {
    "in718": {"critical_Ma": 4500.0, "sulfur_activity_factor": 0.000035, "d_gamma_dT_pure_N_mK": -0.00040, "absorptivity": 0.42},
    "ti6al4v": {"critical_Ma": 3800.0, "sulfur_activity_factor": 0.000015, "d_gamma_dT_pure_N_mK": -0.00028, "absorptivity": 0.38},
    "ss316l": {"critical_Ma": 4200.0, "sulfur_activity_factor": 0.000048, "d_gamma_dT_pure_N_mK": -0.00045, "absorptivity": 0.44},
    "alsi10mg": {"critical_Ma": 3200.0, "sulfur_activity_factor": 0.000010, "d_gamma_dT_pure_N_mK": -0.00035, "absorptivity": 0.18},
}

# Per-property provenance for values in _THERMAL/_MARANGONI. Kept OUT of _THERMAL so that
# canonical_material_source() digests (and every identity derived from them) are unchanged by
# labelling. "basis" vocabulary: cited-primary | cited-secondary | assumed-screening-constant |
# unsourced-estimate.
PROPERTY_PROVENANCE = {
    "in718": {
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
    "alsi10mg": {
        "d_gamma_dT_N_mK": {
            "value": -0.00035,
            "basis": "unsourced-estimate",
            "scope": "alloy melt; no AlSi10Mg-specific measurement located",
            "source": None,
            "note": ("A former second value (-1.8e-4 in the Marangoni table) was also unsourced and was "
                     "removed so both routes use one number; magnitude uncertain by about 2x."),
        },
    },
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
        "absorptivity": 0.52,
        "cracking_susceptibility": "High",
    },
    "ti6al4v": {
        "yield_MPa": 950.0,
        "uts_MPa": 1050.0,
        "absorptivity": 0.65,
        "cracking_susceptibility": "Moderate",
    },
    "ss316l": {
        "yield_MPa": 530.0,
        "uts_MPa": 650.0,
        "absorptivity": 0.58,
        "cracking_susceptibility": "Low",
    },
    "alsi10mg": {
        "yield_MPa": 240.0,
        "uts_MPa": 390.0,
        "absorptivity": 0.30,
        "cracking_susceptibility": "Moderate",
    },
}

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
        "absorptivity": m["absorptivity"],
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
        "absorptivity": s["absorptivity"],
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
