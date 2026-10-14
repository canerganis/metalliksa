#!/usr/bin/env python3
"""
Alloy registry for the free (non-LPBF-core) solvers: one record per alloy, one
ValueRecord per property, explicit errors instead of silent defaults.

Phase 6a status: NEW module, no solver uses it yet.

- The four locked LPBF alloys are PROJECTED read-only from four_alloy_materials.py
  (frozen in lpbf_simulation.IMPLEMENTATION_SOURCE_FILES; never edited here).
  Their canonical_material_source digest is recorded so drift is detectable.
- Secondary domain tables (kinetics, fatigue, corrosion) are numerically identical
  copies of the solver-local tables named in each ``source_ref``. The tests compare
  them key by key with the solver modules, so the copies cannot drift silently.
  The solvers keep their own tables until the per-solver migration commits.

Provenance honesty (RULES.md section 2, AGENTS.md "Bilimsel dogruluk"): none of
the source tables carries a per-value citation, so every value is tagged
``estimated``. ``literature`` or ``measured`` must only be used together with a
per-value citation in ``source_ref``. ``validity=None`` means the source states
no validity range; it does not mean "valid everywhere".

Non-physical placeholders: the kinetics Ms_C/Mf_C entries for in718 (-50/-100 degC)
and al7075 (-200/-273 degC) are solver placeholders, not martensite-start/finish
temperatures (neither alloy forms martensite on quenching; -273 degC is effectively
absolute zero). They are copied unchanged so the drift test holds, and each record
carries KINETICS_PLACEHOLDER_NOTE. No replacement value is invented here.

Bare grade numbers ("304", "316", "4140", "4340", "6061", "7075", "1018", "D2") are
refused consistently: a bare grade does not say which variant is meant (304 is not
304L; 7075 says nothing about temper). Callers must send a prefixed name such as
"AISI 4140", "steel-304" or "al-7075". No string the UI sends is a bare grade.

Corrosion equivalent weights (Phase 6a design step (b)): the corrosion ``ew`` is
not a stored number any more. It is computed from the record's own composition and
valencies and the CIAAW 2021 atomic weights with astm_g102_equivalent_weight(), the
same function tafel_corrosion_rate_solver uses for a caller's customComposition, so
both input paths give the same EW. The convention is the ASTM G102 practice of
counting only elements present at >= 1 % by mass and renormalising their fractions;
with it the pre-migration stored values of steel-1018 (27.92), al-6061 (9.02) and
cu-c110 (31.77) are reproduced to their printed digits and steel-304 (25.12) to
0.04 %. The other five stored values differ (see CORROSION_STORED_EW_BEFORE_STEP_B and
the fix-round commit); their source is not recorded, so they are kept only as a record.

Leaf module: standard library + four_alloy_materials (hashlib/json) +
physical_constants only; no numpy/scipy at import. It must NOT be imported by any manifest file until the
planned implementation-fingerprint bump.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

import four_alloy_materials as _fam
import physical_constants as _pc

# -2: Phase 6a design step (b): corrosion "ew" is computed (ASTM G102 from composition,
# valencies and CIAAW 2021 weights) instead of the stored solver values.
REGISTRY_VERSION = "alloy-registry-2"
SOURCE_TYPES = frozenset({"measured", "literature", "estimated", "computed", "synthetic"})
BASE_REVISION = "01eb3f0"
FOUR_ALLOY_MODEL_VERSION = (
    f"{_fam.MATERIAL_AUTHORITY} schema {_fam.MATERIAL_AUTHORITY_SCHEMA_VERSION}"
)

# Domain names used by resolve_alloy(name, domain=...).
DOMAIN_LPBF_THERMAL = "lpbf_thermal"
DOMAIN_MARANGONI = "marangoni"
DOMAIN_INHERENT_STRAIN = "inherent_strain"
DOMAIN_PV_WINDOW = "pv_window"
DOMAIN_KINETICS = "kinetics"
DOMAIN_FATIGUE_FRACTURE = "fatigue_fracture"
DOMAIN_FATIGUE_SCREENING = "fatigue_screening"
DOMAIN_CORROSION = "corrosion"


# --------------------------------------------------------------------------- errors

class AlloyRegistryError(LookupError):
    """Base class; ``code`` matches input_validation error codes."""

    code = "UNKNOWN_ALLOY"


class UnknownAlloyError(AlloyRegistryError):
    code = "UNKNOWN_ALLOY"

    def __init__(self, name: object, domain: Optional[str] = None,
                 suggestions: Iterable[str] = (), reason: str = "unknown"):
        self.name = name
        self.domain = domain
        self.suggestions = tuple(suggestions)
        self.reason = reason
        scope = f" for domain {domain!r}" if domain else ""
        if reason == "no-domain-data":
            msg = f"Alloy {name!r} is registered but has no data{scope}."
        else:
            msg = f"Unknown alloy {name!r}{scope}."
        if self.suggestions and reason == "no-domain-data":
            msg += " Alloys with data: " + ", ".join(self.suggestions) + "."
        elif self.suggestions:
            msg += " Did you mean: " + ", ".join(self.suggestions) + "?"
        super().__init__(msg)


class AmbiguousAlloyError(AlloyRegistryError):
    # input_validation reports this under UNKNOWN_ALLOY with reason "ambiguous".
    code = "UNKNOWN_ALLOY"

    def __init__(self, name: object, candidates: Iterable[str]):
        self.name = name
        self.candidates = tuple(sorted(candidates))
        super().__init__(
            f"Alloy name {name!r} is ambiguous; it matches: {', '.join(self.candidates)}."
        )


class MissingPropertyError(AlloyRegistryError):
    code = "MISSING_PROPERTY"

    def __init__(self, alloy: str, key: str, domain: Optional[str]):
        self.alloy = alloy
        self.key = key
        self.domain = domain
        super().__init__(
            f"Alloy {alloy!r} has no property {key!r} in domain {domain!r} (no fallback value is used)."
        )


class RegistryIntegrityError(ValueError):
    """Raised at build time when records are inconsistent (duplicate alias, bad metadata)."""


# --------------------------------------------------------------------------- records

@dataclass(frozen=True)
class Validity:
    lo: Optional[float]
    hi: Optional[float]
    unit: str


@dataclass(frozen=True)
class ValueRecord:
    value: Any
    unit: str
    source_type: str
    source_ref: str
    validity: Optional[Validity]
    model_version: str
    note: str = ""

    def __post_init__(self) -> None:
        if self.source_type not in SOURCE_TYPES:
            raise RegistryIntegrityError(f"Invalid source_type {self.source_type!r}")
        if not isinstance(self.unit, str) or not self.unit:
            raise RegistryIntegrityError("ValueRecord.unit must be a non-empty string")
        if not self.source_ref or not self.model_version:
            raise RegistryIntegrityError("ValueRecord needs source_ref and model_version")
        if isinstance(self.value, dict):
            object.__setattr__(self, "value", MappingProxyType(dict(self.value)))

    def to_json(self) -> Dict[str, Any]:
        value = dict(self.value) if isinstance(self.value, Mapping) else self.value
        validity = None
        if self.validity is not None:
            validity = {"lo": self.validity.lo, "hi": self.validity.hi, "unit": self.validity.unit}
        return {
            "value": value, "unit": self.unit, "sourceType": self.source_type,
            "sourceRef": self.source_ref, "validity": validity,
            "modelVersion": self.model_version, "note": self.note,
        }


@dataclass(frozen=True)
class AlloyRecord:
    id: str
    display_names: Tuple[str, ...]
    base_element: str
    aliases: Tuple[str, ...]
    domains: Mapping[str, Mapping[str, ValueRecord]]
    material_source_sha256: Optional[str] = None
    notes: Tuple[str, ...] = field(default_factory=tuple)

    def has_domain(self, domain: str) -> bool:
        return domain in self.domains

    def get(self, key: str, domain: str) -> ValueRecord:
        table = self.domains.get(domain)
        if table is None or key not in table:
            raise MissingPropertyError(self.id, key, domain)
        return table[key]

    def value(self, key: str, domain: str) -> Any:
        return self.get(key, domain).value


# --------------------------------------------------------------------------- units

# Explicit unit per source key. A key missing here fails the registry build, so a
# new column in a source table cannot enter the registry without a unit.
_THERMAL_UNITS = {
    "liquidus_C": "degC",
    "solidus_C": "degC",
    "boiling_C": "degC",
    "M_molar_kg_mol": "kg/mol",
    "density_kg_m3": "kg/m^3",
    "density_liquid_kg_m3": "kg/m^3",
    "thermal_conductivity_W_mK": "W/(m*K)",
    "thermal_conductivity_liquid_W_mK": "W/(m*K)",
    "specific_heat_J_kgK": "J/(kg*K)",
    "specific_heat_liquid_J_kgK": "J/(kg*K)",
    "latent_heat_fusion_J_kg": "J/kg",
    "latent_heat_vap_J_kg": "J/kg",
    "absorptivity_IR": "1",
    # P7b (2026-10-14): the dH/hs index convention constant, the melting-point k / cp of the conduction field and the
    # AlSi10Mg kernel density (the conduction kernel's rho, Akwaboa 2023 Table 3).
    "absorptivity_index_IR": "1",
    "thermal_conductivity_melt_W_mK": "W/(m*K)",
    "specific_heat_melt_J_kgK": "J/(kg*K)",
    "kernel_density_kg_m3": "kg/m^3",
    "absorptivity_Green": "1",
    "surface_tension_N_m": "N/m",
    "d_gamma_dT_N_mK": "N/(m*K)",
    "viscosity_Pa_s": "Pa*s",
    "thermal_expansion_1_K": "1/K",
    "youngs_modulus_GPa": "GPa",
    "poissons_ratio": "1",
    # Welding-type PDAS prefactor; the source states no unit and the LPBF Hunt-Lu
    # path does not use it (solidification_front.py:213).
    "pdas_A1": "unspecified",
    # Kirkwood SDAS = B * Tdot^(-1/3) in um (solidification_front.py:86).
    "sdas_B1": "um*(K/s)^(1/3)",
}
_THERMAL_NON_VALUES = {"base"}

_MARANGONI_UNITS = {
    "critical_Ma": "1",
    "sulfur_activity_factor": "unspecified",
    "d_gamma_dT_pure_N_mK": "N/(m*K)",
}

# P7b: the former per-table "absorptivity" duplicates are deleted from _MARANGONI and _ISM; the one authority value is
# the lpbf-thermal domain's absorptivity_IR.
_ISM_UNITS = {
    "yield_MPa": "MPa",
    "uts_MPa": "MPa",
    "cracking_susceptibility": "category",
}

_PV_UNITS = {
    "powerMin_W": "W",
    "powerMax_W": "W",
    "speedMin_mm_s": "mm/s",
    "speedMax_mm_s": "mm/s",
}

_KINETICS_UNITS = {
    "composition_wt": "wt%",
    "Ae3_C": "degC",
    "Ae1_C": "degC",
    "Ms_C": "degC",
    "Mf_C": "degC",
    "Q_diff_kJ_mol": "kJ/mol",
    "grain_size_d_um_default": "um",
    "aust_temp_C_default": "degC",
    "critical_cooling_rate_C_s": "K/s",
}

_FATIGUE_FRACTURE_UNITS = {
    "hardness_HV": "HV",
    "smooth_fatigue_limit_MPa": "MPa",
    "threshold_stress_intensity_MPa_m": "MPa*m^0.5",
    "fracture_toughness_K_IC": "MPa*m^0.5",
    "paris_C": "(m/cycle)/(MPa*m^0.5)^m",
    "paris_m": "1",
}

_FATIGUE_SCREENING_UNITS = {"hardness_HV": "HV"}

_CORROSION_UNITS = {
    "density_g_cm3": "g/cm^3",
    "ew": "g/equivalent",
    "composition": "mass fraction",
    "valencies": "1",
    "activation_energy_j_mol": "J/mol",
    "standard_e0_v": "V",
}


KINETICS_PLACEHOLDER_NOTE = (
    "NON-PHYSICAL PLACEHOLDER copied from the solver table: this alloy does not form "
    "martensite on quenching, so this Ms/Mf value is not a measured or literature "
    "transformation temperature and must not be reported as one."
)
# (alloy id, key) pairs in _KINETICS that are placeholders, not physical values.
KINETICS_PLACEHOLDERS = frozenset({
    ("in718", "Ms_C"), ("in718", "Mf_C"), ("al7075", "Ms_C"), ("al7075", "Mf_C"),
})
# Per-value citations that are known (every other kinetics value carries the generic "no per-value citation" note).
KINETICS_VALUE_NOTES = {
    ("ti6al4v", "critical_cooling_rate_C_s"): (
        "Solver-local screening value. It agrees with the cooling rate above which Ti-6Al-4V transforms fully "
        "martensitically (alpha prime), 410 C/s: T. Ahmed and H. J. Rack, Mater. Sci. Eng. A 243 (1998) 206-211 "
        "(cited from the published abstract; the paper itself was not read). The kinetics model is steel-only, so "
        "the value is not used for this alloy."),
}
BARE_GRADES = frozenset({"304", "316", "4140", "4340", "6061", "7075", "1018", "d2"})


def _record(value: Any, unit: str, ref: str, model_version: str, note: str = "") -> ValueRecord:
    return ValueRecord(value=value, unit=unit, source_type="estimated", source_ref=ref,
                       validity=None, model_version=model_version, note=note)


def _domain_table(raw: Mapping[str, Any], units: Mapping[str, str], ref: str,
                  model_version: str, note: str, skip: Iterable[str] = (),
                  key_notes: Optional[Mapping[str, str]] = None) -> Mapping[str, ValueRecord]:
    skip = set(skip)
    out: Dict[str, ValueRecord] = {}
    for key, value in raw.items():
        if key in skip:
            continue
        if key not in units:
            raise RegistryIntegrityError(f"{ref}: key {key!r} has no registered unit")
        out[key] = _record(value, units[key], ref, model_version,
                           (key_notes or {}).get(key, note))
    return MappingProxyType(out)


# --------------------------------------------------------------------------- copied secondary tables
# Numerically identical copies of solver-local tables at BASE_REVISION. The tests in
# test_alloy_registry.py compare each copy with the live solver table.

# kinetics_ttt_cct_solver.py:14-98 ALLOY_KINETICS_DB (numeric columns only).
_KINETICS_REF = f"kinetics_ttt_cct_solver.py:14-98 ALLOY_KINETICS_DB @{BASE_REVISION}"
_KINETICS_SOURCE_NAME = {
    "aisi4140": "AISI 4140", "aisi4340": "AISI 4340", "aisid2": "AISI D2",
    "in718": "Inconel 718", "ti6al4v": "Ti-6Al-4V", "al7075": "Al 7075",
}
_KINETICS = {
    "aisi4140": {
        "composition_wt": {"Fe": 96.8, "C": 0.40, "Mn": 0.85, "Cr": 1.00, "Mo": 0.20, "Si": 0.25},
        "Ae3_C": 780.0, "Ae1_C": 725.0, "Ms_C": 330.0, "Mf_C": 180.0, "Q_diff_kJ_mol": 240.0,
        "grain_size_d_um_default": 25.0, "aust_temp_C_default": 860.0,
        "critical_cooling_rate_C_s": 45.0,
    },
    "aisi4340": {
        "composition_wt": {"Fe": 95.7, "C": 0.40, "Ni": 1.85, "Cr": 0.80, "Mo": 0.25, "Mn": 0.70, "Si": 0.30},
        "Ae3_C": 765.0, "Ae1_C": 710.0, "Ms_C": 290.0, "Mf_C": 140.0, "Q_diff_kJ_mol": 265.0,
        "grain_size_d_um_default": 20.0, "aust_temp_C_default": 845.0,
        "critical_cooling_rate_C_s": 8.5,
    },
    "aisid2": {
        "composition_wt": {"Fe": 82.5, "C": 1.55, "Cr": 12.0, "Mo": 0.90, "V": 0.80, "Si": 0.40, "Mn": 0.35},
        "Ae3_C": 860.0, "Ae1_C": 800.0, "Ms_C": 210.0, "Mf_C": 40.0, "Q_diff_kJ_mol": 310.0,
        "grain_size_d_um_default": 15.0, "aust_temp_C_default": 1020.0,
        "critical_cooling_rate_C_s": 2.2,
    },
    "in718": {
        "composition_wt": {"Ni": 52.5, "Cr": 19.0, "Fe": 18.5, "Nb": 5.1, "Mo": 3.05, "Ti": 0.90, "Al": 0.55, "C": 0.04},
        # Ms_C/Mf_C: NON-PHYSICAL placeholders (see KINETICS_PLACEHOLDERS).
        "Ae3_C": 1020.0, "Ae1_C": 620.0, "Ms_C": -50.0, "Mf_C": -100.0, "Q_diff_kJ_mol": 285.0,
        "grain_size_d_um_default": 35.0, "aust_temp_C_default": 980.0,
        "critical_cooling_rate_C_s": 150.0,
    },
    "ti6al4v": {
        "composition_wt": {"Ti": 90.0, "Al": 6.0, "V": 4.0, "Fe": 0.25, "O": 0.18},
        "Ae3_C": 995.0, "Ae1_C": 700.0, "Ms_C": 800.0, "Mf_C": 650.0, "Q_diff_kJ_mol": 220.0,
        "grain_size_d_um_default": 50.0, "aust_temp_C_default": 1050.0,
        "critical_cooling_rate_C_s": 410.0,
    },
    "al7075": {
        "composition_wt": {"Al": 90.0, "Zn": 5.6, "Mg": 2.5, "Cu": 1.6, "Cr": 0.23},
        # Ms_C/Mf_C: NON-PHYSICAL placeholders (see KINETICS_PLACEHOLDERS).
        "Ae3_C": 480.0, "Ae1_C": 100.0, "Ms_C": -200.0, "Mf_C": -273.0, "Q_diff_kJ_mol": 130.0,
        "grain_size_d_um_default": 20.0, "aust_temp_C_default": 475.0,
        "critical_cooling_rate_C_s": 250.0,
    },
}

# lpbf_fatigue_fracture.py:40-64 ALLOY_FATIGUE_DATABASE.
_FATIGUE_FRACTURE_REF = f"lpbf_fatigue_fracture.py:40-64 ALLOY_FATIGUE_DATABASE @{BASE_REVISION}"
_FATIGUE_FRACTURE_SOURCE_NAME = {
    "ti6al4v": "Ti-6Al-4V", "ss316l": "316L SS", "in718": "Inconel 718", "alsi10mg": "AlSi10Mg",
}
_FATIGUE_FRACTURE = {
    "ti6al4v": {"hardness_HV": 340.0, "smooth_fatigue_limit_MPa": 510.0,
                "threshold_stress_intensity_MPa_m": 3.2, "fracture_toughness_K_IC": 55.0,
                "paris_C": 1.8e-11, "paris_m": 3.3},
    "ss316l": {"hardness_HV": 215.0, "smooth_fatigue_limit_MPa": 240.0,
               "threshold_stress_intensity_MPa_m": 4.8, "fracture_toughness_K_IC": 85.0,
               "paris_C": 3.5e-12, "paris_m": 3.1},
    "in718": {"hardness_HV": 440.0, "smooth_fatigue_limit_MPa": 620.0,
              "threshold_stress_intensity_MPa_m": 4.2, "fracture_toughness_K_IC": 70.0,
              "paris_C": 1.2e-11, "paris_m": 3.4},
    "alsi10mg": {"hardness_HV": 115.0, "smooth_fatigue_limit_MPa": 150.0,
                 "threshold_stress_intensity_MPa_m": 1.8, "fracture_toughness_K_IC": 32.0,
                 "paris_C": 2.1e-10, "paris_m": 3.8},
}

# murakami_fatigue_screening.py:15-20 ALLOY_HV_DEFAULTS. These intentionally differ
# from the fatigue_fracture HV values; the two domains are kept apart, not merged.
_FATIGUE_SCREENING_REF = f"murakami_fatigue_screening.py:15-20 ALLOY_HV_DEFAULTS @{BASE_REVISION}"
_FATIGUE_SCREENING = {
    "ti6al4v": {"hardness_HV": 340.0},
    "ss316l": {"hardness_HV": 210.0},
    "alsi10mg": {"hardness_HV": 120.0},
    "in718": {"hardness_HV": 380.0},
}

# tafel_corrosion_rate_solver.py:26-117 ALLOY_LIBRARY. Its per-alloy atomic weight
# copies are not duplicated here; physical_constants.STANDARD_ATOMIC_WEIGHTS holds them.
_CORROSION_REF = f"tafel_corrosion_rate_solver.py:26-117 ALLOY_LIBRARY @{BASE_REVISION}"
_CORROSION_SOURCE_NAME = {
    "ss316l": "steel-316l", "ss304": "steel-304", "steel1018": "steel-1018",
    "ti6al4v": "ti-6al-4v", "al7075": "al-7075", "al6061": "al-6061",
    "cu_c110": "cu-c110", "in718": "inconel-718", "az31b": "az31b",
}
_CORROSION = {
    "ss316l": {"density_g_cm3": 7.98,
               "composition": {"Fe": 0.655, "Cr": 0.170, "Ni": 0.120, "Mo": 0.025, "Mn": 0.020, "Si": 0.010},
               "valencies": {"Fe": 2, "Cr": 3, "Ni": 2, "Mo": 3, "Mn": 2, "Si": 4},
               "activation_energy_j_mol": 32000.0, "standard_e0_v": -0.08},
    "ss304": {"density_g_cm3": 7.93,
              "composition": {"Fe": 0.700, "Cr": 0.190, "Ni": 0.090, "Mn": 0.020},
              "valencies": {"Fe": 2, "Cr": 3, "Ni": 2, "Mn": 2},
              "activation_energy_j_mol": 34000.0, "standard_e0_v": -0.15},
    "steel1018": {"density_g_cm3": 7.87,
                  "composition": {"Fe": 0.985, "Mn": 0.008, "C": 0.002, "Si": 0.005},
                  "valencies": {"Fe": 2, "Mn": 2, "C": 4, "Si": 4},
                  "activation_energy_j_mol": 42000.0, "standard_e0_v": -0.44},
    "ti6al4v": {"density_g_cm3": 4.43,
                "composition": {"Ti": 0.900, "Al": 0.060, "V": 0.040},
                "valencies": {"Ti": 4, "Al": 3, "V": 3},
                "activation_energy_j_mol": 28000.0, "standard_e0_v": 0.12},
    "al7075": {"density_g_cm3": 2.81,
               "composition": {"Al": 0.895, "Zn": 0.056, "Mg": 0.025, "Cu": 0.016, "Cr": 0.004, "Fe": 0.004},
               "valencies": {"Al": 3, "Zn": 2, "Mg": 2, "Cu": 2, "Cr": 3, "Fe": 2},
               "activation_energy_j_mol": 36000.0, "standard_e0_v": -0.73},
    "al6061": {"density_g_cm3": 2.70,
               "composition": {"Al": 0.970, "Mg": 0.010, "Si": 0.006, "Cu": 0.003, "Cr": 0.002, "Fe": 0.007},
               "valencies": {"Al": 3, "Mg": 2, "Si": 4, "Cu": 2, "Cr": 3, "Fe": 2},
               "activation_energy_j_mol": 35000.0, "standard_e0_v": -0.70},
    "cu_c110": {"density_g_cm3": 8.94,
                "composition": {"Cu": 0.999},
                "valencies": {"Cu": 2},
                "activation_energy_j_mol": 30000.0, "standard_e0_v": 0.05},
    "in718": {"density_g_cm3": 8.19,
              "composition": {"Ni": 0.525, "Cr": 0.190, "Fe": 0.185, "Nb": 0.050, "Mo": 0.030, "Ti": 0.009, "Al": 0.005},
              "valencies": {"Ni": 2, "Cr": 3, "Fe": 2, "Nb": 5, "Mo": 3, "Ti": 4, "Al": 3},
              "activation_energy_j_mol": 38000.0, "standard_e0_v": 0.15},
    "az31b": {"density_g_cm3": 1.77,
              "composition": {"Mg": 0.960, "Al": 0.030, "Zn": 0.010},
              "valencies": {"Mg": 2, "Al": 3, "Zn": 2},
              "activation_energy_j_mol": 29000.0, "standard_e0_v": -1.65},
}

# The equivalent weights tafel_corrosion_rate_solver.py:26-117 ALLOY_LIBRARY stored at
# BASE_REVISION (g/equivalent), source not recorded. NOT USED: design step (b) replaced
# them with the computed corrosion "ew" (astm_g102_equivalent_weight). With the >= 1 %
# convention, steel-1018, al-6061 and cu-c110 reproduce these to the printed digits
# and steel-304 to 0.04 %; ss316l, ti6al4v, al7075, in718 and az31b do not.
CORROSION_STORED_EW_BEFORE_STEP_B: Mapping[str, float] = MappingProxyType({
    "ss316l": 25.68,
    "ss304": 25.12,
    "steel1018": 27.92,
    "ti6al4v": 11.97,
    "al7075": 9.15,
    "al6061": 9.02,
    "cu_c110": 31.77,
    "in718": 26.45,
    "az31b": 12.28,
})
# ASTM G102 practice for alloy equivalent weights: only elements present at >= 1 % by
# mass are counted, and their mass fractions are renormalised to sum to 1. The
# threshold is applied to the fraction of the listed total, so mass fractions and wt%
# inputs behave the same and compositions that do not sum to 1 are handled: in this
# table al-6061 sums to 0.998, cu-c110 to 0.999 and in718 to 0.994 (the remainder is
# unlisted), and the renormalisation removes that offset. Example: steel-1018 counts Fe
# only (Mn 0.8 %, Si 0.5 %, C 0.2 % are below 1 %): EW = 55.845 / 2 = 27.9225.
# The valences are an in-house convention copied from the pre-migration solver table
# (lowest common oxidation state per element); they carry no per-value citation.
# Threshold boundary: 316L lists Si at exactly 1.0 %, counted by ">=" (EW 24.8205);
# a strict "> 1 %" reading would drop it (EW 25.4728).
ASTM_G102_MIN_MASS_FRACTION = 0.01
CORROSION_EW_NOTE = (
    "Computed: ASTM G102 practice, EW = 1 / sum(f_i * n_i / W_i) over the elements present "
    "at >= 1 % by mass with renormalised mass fractions, in-house valences (no per-value "
    "citation) and CIAAW 2021 abridged atomic weights, rounded to 4 decimals; the same "
    "function the tafel customComposition path uses."
)


def astm_g102_counted_elements(composition: Mapping[str, float]) -> List[str]:
    """Elements the ASTM G102 practice counts: present at >= 1 % of the listed total mass."""
    positive = {el: float(f) for el, f in composition.items() if float(f) > 0.0}
    total = sum(positive.values())
    if total <= 0.0:
        return []
    return [el for el, f in positive.items() if f / total >= ASTM_G102_MIN_MASS_FRACTION]


def astm_g102_equivalent_weight(composition: Mapping[str, float], valencies: Mapping[str, float],
                                atomic_weights: Mapping[str, float]) -> Optional[float]:
    """ASTM G102 equivalent weight, EW = (sum_i f_i * n_i / W_i)^-1, rounded to 4 decimals.

    Only elements with f_i / sum(f) >= ASTM_G102_MIN_MASS_FRACTION (1 % by mass) count;
    their fractions are renormalised over the counted elements. n_i: valence, W_i:
    atomic weight (g/mol). A counted element without a valence or an atomic weight
    does not contribute. Returns None when nothing contributes (the caller decides
    what that means; no fallback value here).
    """
    positive = {el: float(f) for el, f in composition.items() if float(f) > 0.0}
    total = sum(positive.values())
    if total <= 0.0:
        return None
    major = {el: f for el, f in positive.items() if f / total >= ASTM_G102_MIN_MASS_FRACTION}
    known = {el: f for el, f in major.items() if el in valencies and el in atomic_weights}
    known_total = sum(known.values())
    if known_total <= 0.0:
        return None
    denom = sum((f / known_total) * valencies[el] / atomic_weights[el] for el, f in known.items())
    if denom <= 1e-12:
        return None
    return round(1.0 / denom, 4)


def _corrosion_ew_record(raw: Mapping[str, Any], model_version: str) -> "ValueRecord":
    composition = raw["composition"]
    weights = {el: _pc.atomic_weight(el) for el in composition}
    ew = astm_g102_equivalent_weight(composition, raw["valencies"], weights)
    if ew is None:
        raise RegistryIntegrityError("corrosion record without a computable equivalent weight")
    return ValueRecord(value=ew, unit=_CORROSION_UNITS["ew"], source_type="computed",
                       source_ref=f"{_CORROSION_REF} composition/valencies + {_pc.CIAAW_SOURCE}",
                       validity=None, model_version=model_version, note=CORROSION_EW_NOTE)


# --------------------------------------------------------------------------- identities and aliases
# Aliases beyond four_alloy_materials._ALIAS, harvested from the strings the UI sends
# (src/components/*, src/utils/tafelParser.ts) and the solver table keys at BASE_REVISION.

_IDENTITIES: Dict[str, Dict[str, Any]] = {
    "ti6al4v": {
        "display": ("Ti-6Al-4V", "Ti-6Al-4V ELI"), "base": "Ti",
        "aliases": (
            "Ti-6Al-4V Grade 5", "Ti-6Al-4V Grade 5 Titanium", "Titanium Ti-6Al-4V (Grade 5)",
            "Ti-6Al-4V Grade 5 (AMS 4928)", "Ti-6Al-4V Grade 5 (Aero AM)",
            "Ti-6Al-4V (Grade 5 Alpha-Beta)", "ti64_ams4928",
        ),
    },
    "ss316l": {
        "display": ("316L Stainless Steel", "SS 316L"), "base": "Fe",
        "aliases": ("316L SS", "steel-316l", "AISI 316L Stainless Steel", "AISI 316L"),
    },
    "alsi10mg": {
        "display": ("AlSi10Mg",), "base": "Al",
        # "(AMS 4215)" / "ams4215": UI-label compatibility only (StochasticUQMMPDSStudio);
        # SAE AMS 4215 is a casting spec, not AlSi10Mg LPBF. No AMS equivalence is
        # claimed; see alloy_data_kinetics_uq_fatigue.EXTRA_ALIASES["alsi10mg"].
        "aliases": ("AlSi10Mg Additive (AMS 4215)", "alsi10mg_ams4215", "AlSi10Mg Additive Alloy"),
    },
    "in718": {
        "display": ("Inconel 718",), "base": "Ni",
        "aliases": (
            "inconel-718", "Inconel 718 Superalloy", "Nickel Superalloy Inconel 718",
            "Inconel 718 (Ni-Fe Superalloy)", "Inconel 718 (Aero LPBF + Aged)",
            "Inconel 718 (AMS 5664 / AMS 5662)", "inconel718_ams5664",
        ),
    },
    "aisi4140": {"display": ("AISI 4140",), "base": "Fe", "aliases": ()},
    "aisi4340": {
        "display": ("AISI 4340",), "base": "Fe",
        "aliases": ("steel4340_ams6414", "AISI 4340 Ultra-High Strength (AMS 6414)",
                    "AISI 4340 Ultra-High Strength Steel"),
    },
    "aisid2": {"display": ("AISI D2",), "base": "Fe", "aliases": ()},
    "al7075": {
        "display": ("Al 7075",), "base": "Al",
        "aliases": ("al-7075", "Aerospace Aluminum 7075-T6", "Aerospace Al 7075-T6",
                    "Al 7075-T6 Aerospace Aluminum"),
    },
    "al6061": {
        "display": ("Al 6061",), "base": "Al",
        "aliases": ("al-6061", "Structural Aluminum 6061-T6", "Structural Al 6061-T6",
                    "Al 6061-T6 Structural Aluminum"),
    },
    "ss304": {
        "display": ("AISI 304 Stainless Steel",), "base": "Fe",
        "aliases": ("steel-304", "AISI 304"),
    },
    "steel1018": {
        "display": ("Carbon Steel (AISI 1018)",), "base": "Fe",
        "aliases": ("steel-1018", "AISI 1018", "AISI 1018 Carbon Steel"),
    },
    "cu_c110": {
        "display": ("Pure Copper (ETP C11000)",), "base": "Cu",
        "aliases": ("cu-c110", "C11000", "C11000 Electrolytic Tough Pitch Copper"),
    },
    "az31b": {
        "display": ("Magnesium Alloy AZ31B",), "base": "Mg",
        "aliases": ("AZ31B Magnesium Alloy",),
    },
}

# ---- BEGIN phase6a-t2b block: kinetics / stochastic UQ / fatigue domain data ----
# UI names harvested for tranche 2b (alloy_data_kinetics_uq_fatigue.EXTRA_ALIASES).
import alloy_data_kinetics_uq_fatigue as _t2b_data  # noqa: E402  (leaf, stdlib only)

for _t2b_id, _t2b_names in _t2b_data.EXTRA_ALIASES.items():
    _IDENTITIES[_t2b_id]["aliases"] = tuple(_IDENTITIES[_t2b_id]["aliases"]) + tuple(_t2b_names)
# ---- END phase6a-t2b block ----


def normalise_name(name: object) -> Optional[str]:
    """Same normalisation as four_alloy_materials.resolve_alloy_id (exact key form)."""
    if not isinstance(name, str):
        return None
    key = name.strip().lower().replace("_", "-")
    key = " ".join(key.split())
    return key or None


def _compact(key: str) -> str:
    return key.replace(" ", "").replace("-", "")


# --------------------------------------------------------------------------- build

def _four_alloy_domains(aid: str) -> Dict[str, Mapping[str, ValueRecord]]:
    note = "Screening constant from the locked four-alloy authority; no per-value citation in source."
    ref = _fam.MATERIAL_AUTHORITY
    domains = {
        DOMAIN_LPBF_THERMAL: _domain_table(_fam._THERMAL[aid], _THERMAL_UNITS, f"{ref} _THERMAL",
                                           FOUR_ALLOY_MODEL_VERSION, note, skip=_THERMAL_NON_VALUES),
        DOMAIN_MARANGONI: _domain_table(_fam._MARANGONI[aid], _MARANGONI_UNITS, f"{ref} _MARANGONI",
                                        FOUR_ALLOY_MODEL_VERSION, note),
        DOMAIN_INHERENT_STRAIN: _domain_table(_fam._ISM[aid], _ISM_UNITS, f"{ref} _ISM",
                                              FOUR_ALLOY_MODEL_VERSION, note),
        DOMAIN_PV_WINDOW: _domain_table(
            _fam.LITERATURE_PV_WINDOWS[aid], _PV_UNITS, f"{ref} LITERATURE_PV_WINDOWS",
            FOUR_ALLOY_MODEL_VERSION,
            "Machine-class typical P-v box; the source names no per-box citation."),
    }
    return domains


def _copied_domains(aid: str) -> Dict[str, Mapping[str, ValueRecord]]:
    out: Dict[str, Mapping[str, ValueRecord]] = {}
    tables = (
        (DOMAIN_KINETICS, _KINETICS, _KINETICS_UNITS, _KINETICS_REF),
        (DOMAIN_FATIGUE_FRACTURE, _FATIGUE_FRACTURE, _FATIGUE_FRACTURE_UNITS, _FATIGUE_FRACTURE_REF),
        (DOMAIN_FATIGUE_SCREENING, _FATIGUE_SCREENING, _FATIGUE_SCREENING_UNITS, _FATIGUE_SCREENING_REF),
        (DOMAIN_CORROSION, _CORROSION, _CORROSION_UNITS, _CORROSION_REF),
    )
    for domain, table, units, ref in tables:
        if aid in table:
            key_notes = None
            if domain == DOMAIN_KINETICS:
                key_notes = {k: KINETICS_PLACEHOLDER_NOTE
                             for a, k in KINETICS_PLACEHOLDERS if a == aid}
                key_notes.update({k: note for (a, k), note in KINETICS_VALUE_NOTES.items() if a == aid})
            out[domain] = _domain_table(
                table[aid], units, ref, f"{REGISTRY_VERSION}:{domain}",
                "Solver-local screening value copied unchanged; no per-value citation in source.",
                key_notes=key_notes)
            if domain == DOMAIN_CORROSION:
                # Design step (b): the equivalent weight is computed, not copied.
                merged = dict(out[domain])
                merged["ew"] = _corrosion_ew_record(table[aid], f"{REGISTRY_VERSION}:{domain}")
                out[domain] = MappingProxyType(merged)
    return out


def build_records() -> Dict[str, AlloyRecord]:
    records: Dict[str, AlloyRecord] = {}
    for aid, ident in _IDENTITIES.items():
        domains: Dict[str, Mapping[str, ValueRecord]] = {}
        digest = None
        if aid in _fam.FOUR_ALLOY_IDS:
            domains.update(_four_alloy_domains(aid))
            digest = _fam.canonical_material_source(aid)[1]
            aliases = tuple(k for k, v in _fam._ALIAS.items() if v == aid) + tuple(ident["aliases"])
            display = (_fam.THERMAL_NAME[aid], _fam.SLICER_NAME[aid])
        else:
            aliases = tuple(ident["aliases"])
            display = tuple(ident["display"])
        domains.update(_copied_domains(aid))
        all_names = (aid,) + display + tuple(ident["display"]) + aliases
        ordered: List[str] = []
        for n in all_names:
            if n not in ordered:
                ordered.append(n)
        records[aid] = AlloyRecord(
            id=aid, display_names=tuple(dict.fromkeys(display + tuple(ident["display"]))),
            base_element=ident["base"], aliases=tuple(ordered),
            domains=MappingProxyType(domains), material_source_sha256=digest,
        )
    return records


def build_alias_index(records: Mapping[str, AlloyRecord]) -> Tuple[Dict[str, str], Dict[str, frozenset]]:
    """Return (exact-key index, compact-key index). Duplicate exact aliases across
    records raise RegistryIntegrityError; compact collisions become ambiguous."""
    exact: Dict[str, str] = {}
    compact: Dict[str, set] = {}
    for aid, rec in records.items():
        for alias in rec.aliases:
            key = normalise_name(alias)
            if key is None:
                raise RegistryIntegrityError(f"Empty alias on {aid!r}")
            if key in BARE_GRADES or _compact(key) in BARE_GRADES:
                raise RegistryIntegrityError(f"Bare grade alias {alias!r} on {aid!r} is refused")
            owner = exact.get(key)
            if owner is not None and owner != aid:
                raise RegistryIntegrityError(f"Alias {alias!r} is shared by {owner!r} and {aid!r}")
            exact[key] = aid
            compact.setdefault(_compact(key), set()).add(aid)
    return exact, {k: frozenset(v) for k, v in compact.items()}


# ---- BEGIN Phase 6a tranche 2a domain data (calphad / battery EIS / icme) ----
# Leaf module (stdlib + physical_constants). Adds its alloy-keyed tables (domain
# "icme") on top of the copied domains above; values are tagged "estimated".
import alloy_data_calphad_battery_icme as _t2a_data  # noqa: E402

DOMAIN_ICME = _t2a_data.DOMAIN_ICME
_t2a_base_copied_domains = _copied_domains


def _copied_domains(aid: str) -> Dict[str, Mapping[str, ValueRecord]]:  # noqa: F811
    out = _t2a_base_copied_domains(aid)
    for domain, (table, units, ref) in _t2a_data.REGISTRY_DOMAIN_TABLES.items():
        if aid in table:
            out[domain] = _domain_table(table[aid], units, ref, f"{REGISTRY_VERSION}:{domain}",
                                        _t2a_data.REGISTRY_NOTE)
    return out
# ---- END Phase 6a tranche 2a ----


REGISTRY: Mapping[str, AlloyRecord] = MappingProxyType(build_records())
_EXACT_INDEX, _COMPACT_INDEX = build_alias_index(REGISTRY)


def _suggest(key: Optional[str], domain: Optional[str]) -> List[str]:
    pool = sorted(_EXACT_INDEX)
    if domain:
        pool = [k for k in pool if REGISTRY[_EXACT_INDEX[k]].has_domain(domain)]
    if not key:
        return []
    return difflib.get_close_matches(key, pool, n=3, cutoff=0.6)


def resolve_alloy_id(name: object) -> str:
    """Resolve a name to a registry id. Raises UnknownAlloyError / AmbiguousAlloyError."""
    key = normalise_name(name)
    if key is None:
        raise UnknownAlloyError(name)
    if key in BARE_GRADES:
        # Bare grade numbers are refused consistently (304 is not 304L).
        raise UnknownAlloyError(name, None, _suggest(key, None), reason="bare-grade")
    if key in _EXACT_INDEX:
        return _EXACT_INDEX[key]
    candidates = _COMPACT_INDEX.get(_compact(key), frozenset())
    if len(candidates) > 1:
        raise AmbiguousAlloyError(name, candidates)
    if len(candidates) == 1:
        return next(iter(candidates))
    raise UnknownAlloyError(name, None, _suggest(key, None))


def resolve_alloy(name: object, domain: Optional[str] = None) -> AlloyRecord:
    """Resolve ``name`` to an AlloyRecord; with ``domain``, the record must carry it."""
    try:
        aid = resolve_alloy_id(name)
    except UnknownAlloyError as exc:
        if domain is None or exc.reason == "bare-grade":
            raise
        raise UnknownAlloyError(name, domain, _suggest(normalise_name(name), domain)) from exc
    record = REGISTRY[aid]
    if domain is not None and not record.has_domain(domain):
        options = sorted(a for a, r in REGISTRY.items() if r.has_domain(domain))
        raise UnknownAlloyError(name, domain, options, reason="no-domain-data")
    return record


def get_value(name: object, key: str, domain: str) -> ValueRecord:
    return resolve_alloy(name, domain).get(key, domain)


def alloys_with_domain(domain: str) -> Tuple[str, ...]:
    return tuple(sorted(a for a, r in REGISTRY.items() if r.has_domain(domain)))


def provenance(alloy_id: Optional[str] = None) -> Dict[str, Any]:
    """Compact provenance block for solver outputs."""
    out: Dict[str, Any] = {"registryVersion": REGISTRY_VERSION, "baseRevision": BASE_REVISION}
    if alloy_id is not None:
        rec = REGISTRY[alloy_id]
        out["alloyId"] = rec.id
        if rec.material_source_sha256:
            out["materialSourceSha256"] = rec.material_source_sha256
    return out
