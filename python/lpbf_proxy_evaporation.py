"""Profile-parameterised fixed-surface single-species vapor law for proxy research models.

A ``ProxyVaporProfile`` carries one sourced single-species vapor triple (boiling point,
latent heat, molar mass), the thermal property table builder and the scenario-input
basis. The vapor law is the one of lpbf_ti64_evaporation and lpbf_al_proxy_evaporation:
Gan 2021 Eqs 12/14 closed form at and above the high threshold, a declared cubic Hermite
bridge between the thresholds, zero flux and ambient recoil below the low threshold.
The Ti64 helpers are reused by import; no Ti64 or AlSi10Mg file is changed.

Research only. Selective evaporation, activity and composition change, flow, surface
motion, plume and keyhole geometry are not represented.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import math
from types import MappingProxyType

import numpy as np

from lpbf_ti64_evaporation import (EvaporationConfig, _array, _bridge_coefficients,
                                   _number, update_onset)


GAS_CONSTANT_J_MOL_K = 8.31446261815324
REFERENCE_PRESSURE_PA = 101325.0
SCENARIO_TEMPERATURE_LIMIT_K = 6000.0
SCENARIO_KEYS = ("transitionLow_K", "transitionHigh_K", "ambientPressure_Pa",
                 "returnFraction", "maxTemperature_K", "surfaceTension_N_m")
# Basis kinds of a scenario default. Only "sourced" keeps the Literature estimate label;
# "unsourced" makes the output Unresolved (GOAL.md label rule M-1, item 2).
BASIS_KINDS = ("sourced", "transferred", "unsourced", "convention", "computational-limit")


@dataclass(frozen=True, slots=True)
class ProxyVaporProfile:
    """One complete, explicitly labelled proxy profile; immutable."""

    key: str
    targetAlloy: str
    vaporizationTemperature_K: float
    latentHeat_J_kg: float
    molarMass_kg_mol: float
    disclosure: str
    sourceProfile: Mapping
    scenarioDefaults: Mapping
    scenarioBasis: Mapping
    materialProperties: Callable[[], dict]

    @property
    def clausius_K(self):
        return self.latentHeat_J_kg*self.molarMass_kg_mol/GAS_CONSTANT_J_MOL_K


def make_profile(*, key, target_alloy, vaporization_K, latent_heat_J_kg, molar_mass_kg_mol,
                 disclosure, source_profile, scenario_defaults, scenario_basis, material_properties):
    """Build a profile and check that every scenario default carries a declared basis."""
    if set(scenario_defaults) != set(SCENARIO_KEYS) or set(scenario_basis) != set(SCENARIO_KEYS):
        raise ValueError("profile must declare a default and a basis for every scenario input")
    for name, basis in scenario_basis.items():
        if basis.get("kind") not in BASIS_KINDS or not basis.get("note"):
            raise ValueError(f"scenario basis for {name} needs a known kind and a note")
    for value in (vaporization_K, latent_heat_J_kg, molar_mass_kg_mol):
        if isinstance(value, bool) or not math.isfinite(value) or value <= 0:
            raise ValueError("vapor triple must be positive and finite")
    return ProxyVaporProfile(key, target_alloy, float(vaporization_K), float(latent_heat_J_kg),
                             float(molar_mass_kg_mol), disclosure, MappingProxyType(dict(source_profile)),
                             MappingProxyType(dict(scenario_defaults)),
                             MappingProxyType({k: MappingProxyType(dict(v)) for k, v in scenario_basis.items()}),
                             material_properties)


@dataclass(frozen=True, slots=True)
class ProxyEvaporationConfig(EvaporationConfig):
    """Ti64 config fields (so update_onset applies unchanged) plus the bound vapor profile."""

    profile: ProxyVaporProfile


def _high_law(temperature, return_fraction, profile):
    with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
        inverse_temperature = 1.0 / temperature
        saturation = REFERENCE_PRESSURE_PA * np.exp(
            profile.clausius_K * (1.0 / profile.vaporizationTemperature_K - inverse_temperature))
        mass = (1.0 - return_fraction) * saturation * np.sqrt(
            profile.molarMass_kg_mol / (2.0 * math.pi * GAS_CONSTANT_J_MOL_K) * inverse_temperature)
        recoil = (1.0 + return_fraction) * saturation / 2.0
        pressure_log_slope = profile.clausius_K * inverse_temperature * inverse_temperature
        mass_slope = mass * (pressure_log_slope - 0.5 * inverse_temperature)
        recoil_slope = recoil * pressure_log_slope
    return mass, recoil, mass_slope, recoil_slope


def validate_config(raw, liquidus_K, profile):
    """Validate the explicit evaporation object; never infer missing assumptions."""
    if not isinstance(profile, ProxyVaporProfile):
        raise ValueError("profile must be a ProxyVaporProfile")
    required = set(SCENARIO_KEYS) - {"surfaceTension_N_m"}
    if not isinstance(raw, Mapping):
        raise ValueError("evaporation must be an explicit object")
    if set(raw) - set(SCENARIO_KEYS) or required - set(raw):
        raise ValueError("evaporation contains unknown keys or is missing required keys")
    liquidus = _number(liquidus_K, "liquidus_K")
    low = _number(raw["transitionLow_K"], "transitionLow_K")
    high = _number(raw["transitionHigh_K"], "transitionHigh_K")
    ambient = _number(raw["ambientPressure_Pa"], "ambientPressure_Pa")
    beta = _number(raw["returnFraction"], "returnFraction", zero_allowed=True)
    maximum = _number(raw["maxTemperature_K"], "maxTemperature_K")
    sigma = _number(raw["surfaceTension_N_m"], "surfaceTension_N_m") if "surfaceTension_N_m" in raw else None
    if beta >= 1:
        raise ValueError("returnFraction must satisfy 0 <= returnFraction < 1")
    if not liquidus <= low < high <= maximum <= SCENARIO_TEMPERATURE_LIMIT_K:
        raise ValueError("require liquidus <= low < high <= maxTemperature_K <= 6000 K (scenario limit)")
    try:
        mass, recoil, mass_slope, recoil_slope = _high_law(np.asarray(high), beta, profile)
        mass_coefficients = _bridge_coefficients(0.0, float(mass), float(mass_slope), high - low, "mass flux")
        recoil_coefficients = _bridge_coefficients(ambient, float(recoil), float(recoil_slope), high - low, "recoil")
    except (FloatingPointError, OverflowError) as exc:
        raise ValueError("evaporation scenario is outside finite numerical range") from exc
    return ProxyEvaporationConfig(low, high, ambient, beta, maximum, sigma, liquidus,
                                  mass_coefficients, recoil_coefficients, profile)


def surface_state(temperature_K, config):
    """Return independent arrays (also 0-D for scalars); never mutate the input.

    The heat derivative is the analytic d(j*Lv)/dT for the surface-loss explicit
    stability bound. Invalid/out-of-scenario temperatures raise; nothing is capped.
    """
    if not isinstance(config, ProxyEvaporationConfig):
        raise ValueError("config must be produced by lpbf_proxy_evaporation.validate_config")
    profile = config.profile
    temperature = _array(temperature_K, "temperature_K")
    if np.any(temperature <= 0) or np.any(temperature > config.maxTemperature_K):
        raise ValueError("temperature_K must be positive and <= maxTemperature_K")
    mass = np.zeros_like(temperature)
    recoil = np.full_like(temperature, config.ambientPressure_Pa)
    mass_slope = np.zeros_like(temperature)
    bridge = (temperature > config.transitionLow_K) & (temperature < config.transitionHigh_K)
    high = temperature >= config.transitionHigh_K
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
            width = config.transitionHigh_K - config.transitionLow_K
            u = (temperature[bridge] - config.transitionLow_K) / width
            a, b = config._mass_coefficients
            mass[bridge] = u * u * (a + b * u)
            mass_slope[bridge] = u * (2.0 * a + 3.0 * b * u) / width
            a, b = config._recoil_coefficients
            recoil[bridge] += u * u * (a + b * u)
            mass[high], recoil[high], mass_slope[high], _ = _high_law(
                temperature[high], config.returnFraction, profile)
            heat = mass * profile.latentHeat_J_kg
            heat_slope = mass_slope * profile.latentHeat_J_kg
    except (FloatingPointError, OverflowError) as exc:
        raise ValueError("surface vapor state is outside finite numerical range") from exc
    result = {"mass_flux_kg_m2_s": mass, "heat_flux_W_m2": heat,
              "recoil_pressure_Pa": recoil, "heat_flux_derivative_W_m2K": heat_slope}
    if (not all(np.isfinite(value).all() for value in result.values())
            or np.any(mass < 0) or np.any(heat_slope < 0)
            or np.any(recoil < config.ambientPressure_Pa)):
        raise ValueError("surface vapor state is negative, nonfinite or below ambient pressure")
    return result


def scenario_evidence(normalized_evaporation, profile):
    """Apply the research output label rule to the scenario inputs actually used.

    Default left at a sourced value keeps the sourced label; a changed value is User input;
    a default with an unsourced basis is Unresolved, which takes precedence over User input.
    Declared conventions, transferred values and the computational temperature limit are
    named in ``inputBasis`` but do not by themselves change the label.
    """
    unresolved, user, basis = [], [], {}
    for key in SCENARIO_KEYS:
        declared = profile.scenarioBasis[key]
        if key not in normalized_evaporation:
            basis[key] = dict(status="omitted", kind=declared["kind"], note=declared["note"])
            continue
        value = normalized_evaporation[key]
        if value != profile.scenarioDefaults[key]:
            user.append(key)
            basis[key] = dict(status="user input", value=value, kind="user", note="value typed by the user")
            continue
        basis[key] = dict(status="default", value=value, kind=declared["kind"], note=declared["note"])
        if declared["kind"] == "unsourced":
            unresolved.append(key)
    label = "Unresolved" if unresolved else "User input" if user else "Literature estimate"
    if unresolved:
        summary = ("Unresolved: no source gives " + " and ".join(unresolved)
                   + " for this alloy; the values used are declared defaults.")
    elif user:
        summary = "User input: " + ", ".join(user) + "."
    else:
        summary = "Literature estimate: every scenario input is at its sourced default."
    return dict(label=label, summary=summary, unresolvedInputs=unresolved, userInputs=user, inputBasis=basis)


__all__ = ["GAS_CONSTANT_J_MOL_K", "REFERENCE_PRESSURE_PA", "SCENARIO_KEYS", "ProxyVaporProfile",
           "ProxyEvaporationConfig", "make_profile", "validate_config", "surface_state",
           "scenario_evidence", "update_onset"]
