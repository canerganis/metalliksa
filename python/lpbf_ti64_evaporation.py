"""Declared fixed-surface Ti-species vapor law; not Ti64 physical validation.

Gan2021 SI Table 1 supplies the Ti-species constants. The explicit Hermite
matching interval, ambient pressure, return fraction and optional scalar surface
tension are caller-declared scenarios. No species depletion, surface motion,
ablation or free-surface/keyhole solution is represented here.
"""

from collections.abc import Mapping
from dataclasses import dataclass
import math
from numbers import Real
from types import MappingProxyType

import numpy as np


VAPORIZATION_TEMPERATURE_K = 3560.0
LATENT_HEAT_J_KG = 9.255e6
MOLAR_MASS_KG_MOL = 0.048
GAS_CONSTANT_J_MOL_K = 8.31446261815324
REFERENCE_PRESSURE_PA = 101325.0
SCENARIO_TEMPERATURE_LIMIT_K = 6000.0
_CLAUSIUS_K = LATENT_HEAT_J_KG * MOLAR_MASS_KG_MOL / GAS_CONSTANT_J_MOL_K

SOURCE_PROFILE = MappingProxyType({
    "sourceId": "Gan2021-SI-Table1-Ti",
    "species": "Ti (nominal Ti64 scenario; no composition evolution)",
    "vaporizationTemperature_K": VAPORIZATION_TEMPERATURE_K,
    "latentHeat_J_kg": LATENT_HEAT_J_KG,
    "molarMass_kg_mol": MOLAR_MASS_KG_MOL,
    "gasConstant_J_molK": GAS_CONSTANT_J_MOL_K,
    "referencePressure_Pa": REFERENCE_PRESSURE_PA,
    "referencePressureBasis": "declared convention",
    "transitionBasis": "declared cubic Hermite matching following Gan Eqs 12/14; not recovered fitting coefficients",
    "maxTemperatureLimit_K": SCENARIO_TEMPERATURE_LIMIT_K,
    "temperatureLimitBasis": "computational scenario limit; not a source validity range",
    "surfaceTensionBasis": "optional caller-declared scalar assumption; no default",
})


@dataclass(frozen=True, slots=True)
class EvaporationConfig:
    """Immutable scenario produced by :func:`validate_config`.

    Attribute names match the explicit JSON keys. Coefficients are in normalized
    u=(T-low)/(high-low): y=y_low+u**2*(a+b*u).
    """

    transitionLow_K: float
    transitionHigh_K: float
    ambientPressure_Pa: float
    returnFraction: float
    maxTemperature_K: float
    surfaceTension_N_m: float | None
    liquidus_K: float
    _mass_coefficients: tuple[float, float]
    _recoil_coefficients: tuple[float, float]


def _number(value, name, *, zero_allowed=False):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite real number (no booleans or numeric strings)")
    try:
        result = float(value)
    except (OverflowError, TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be finite") from exc
    if not math.isfinite(result) or result < 0 or (result == 0 and not zero_allowed):
        raise ValueError(f"{name} must be finite and {'nonnegative' if zero_allowed else 'positive'}")
    return result


def _array(value, name):
    """Validate before float conversion, so mixed lists cannot hide bools/strings."""
    try:
        if isinstance(value, np.ndarray):
            if value.dtype.kind not in "iuf":
                raise ValueError(f"{name} must contain real numeric values")
        else:
            unconverted = np.asarray(value, dtype=object)
            if any(isinstance(item, (bool, np.bool_)) or not isinstance(item, Real)
                   for item in unconverted.flat):
                raise ValueError(f"{name} must contain real numbers (no booleans or numeric strings)")
        with np.errstate(over="raise", invalid="raise"):
            result = np.asarray(value, dtype=np.float64)
    except (OverflowError, TypeError, ValueError, FloatingPointError) as exc:
        raise ValueError(f"{name} must contain finite real numbers") from exc
    if not np.isfinite(result).all():
        raise ValueError(f"{name} must contain finite real numbers")
    return result


def _high_law(temperature, return_fraction):
    with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
        inverse_temperature = 1.0 / temperature
        saturation = REFERENCE_PRESSURE_PA * np.exp(
            _CLAUSIUS_K * (1.0 / VAPORIZATION_TEMPERATURE_K - inverse_temperature))
        mass = (1.0 - return_fraction) * saturation * np.sqrt(
            MOLAR_MASS_KG_MOL / (2.0 * math.pi * GAS_CONSTANT_J_MOL_K) * inverse_temperature)
        recoil = (1.0 + return_fraction) * saturation / 2.0
        pressure_log_slope = _CLAUSIUS_K * inverse_temperature * inverse_temperature
        mass_slope = mass * (pressure_log_slope - 0.5 * inverse_temperature)
        recoil_slope = recoil * pressure_log_slope
    return mass, recoil, mass_slope, recoil_slope


def _bridge_coefficients(low_value, high_value, high_slope, width, name):
    delta = high_value - low_value
    scaled_slope = width * high_slope
    # dy/du = u*(2*a+3*b*u). The remaining factor is linear, so checking
    # both endpoints (a>=0, 2*a+3*b=scaled_slope>=0) proves monotonicity.
    if (not all(math.isfinite(x) for x in (delta, scaled_slope))
            or delta < 0 or scaled_slope < 0 or scaled_slope > 3.0 * delta):
        raise ValueError(f"{name} Hermite bridge would be negative or nonmonotone")
    a = 3.0 * delta - scaled_slope
    b = scaled_slope - 2.0 * delta
    if not math.isfinite(a) or not math.isfinite(b):
        raise ValueError(f"{name} Hermite bridge coefficients must be finite")
    return a, b


def validate_config(raw, liquidus_K):
    """Validate the explicit evaporation object; never infer missing assumptions."""
    required = {"transitionLow_K", "transitionHigh_K", "ambientPressure_Pa",
                "returnFraction", "maxTemperature_K"}
    allowed = required | {"surfaceTension_N_m"}
    if not isinstance(raw, Mapping):
        raise ValueError("evaporation must be an explicit object")
    if set(raw) - allowed or required - set(raw):
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
        mass, recoil, mass_slope, recoil_slope = _high_law(np.asarray(high), beta)
        mass_coefficients = _bridge_coefficients(0.0, float(mass), float(mass_slope), high - low, "mass flux")
        recoil_coefficients = _bridge_coefficients(ambient, float(recoil), float(recoil_slope), high - low, "recoil")
    except (FloatingPointError, OverflowError) as exc:
        raise ValueError("evaporation scenario is outside finite numerical range") from exc
    return EvaporationConfig(low, high, ambient, beta, maximum, sigma, liquidus,
                             mass_coefficients, recoil_coefficients)


def surface_state(temperature_K, config):
    """Return independent arrays (also 0-D for scalars); never mutate the input.

    The heat derivative is the analytic d(j*Lv)/dT for the surface-loss explicit
    stability bound. Invalid/out-of-scenario temperatures raise; nothing is capped.
    """
    if not isinstance(config, EvaporationConfig):
        raise ValueError("config must be produced by validate_config")
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
            u = (temperature[bridge] - config.transitionLow_K) / (config.transitionHigh_K - config.transitionLow_K)
            a, b = config._mass_coefficients
            mass[bridge] = u * u * (a + b * u)
            mass_slope[bridge] = u * (2.0 * a + 3.0 * b * u) / (config.transitionHigh_K - config.transitionLow_K)
            a, b = config._recoil_coefficients
            recoil[bridge] += u * u * (a + b * u)
            mass[high], recoil[high], mass_slope[high], _ = _high_law(temperature[high], config.returnFraction)
            heat = mass * LATENT_HEAT_J_KG
            heat_slope = mass_slope * LATENT_HEAT_J_KG
    except (FloatingPointError, OverflowError) as exc:
        raise ValueError("surface vapor state is outside finite numerical range") from exc
    result = {"mass_flux_kg_m2_s": mass, "heat_flux_W_m2": heat,
              "recoil_pressure_Pa": recoil, "heat_flux_derivative_W_m2K": heat_slope}
    if (not all(np.isfinite(value).all() for value in result.values())
            or np.any(mass < 0) or np.any(heat_slope < 0)
            or np.any(recoil < config.ambientPressure_Pa)):
        raise ValueError("surface vapor state is negative, nonfinite or below ambient pressure")
    return result


def update_onset(previous, state, config, beam_radius_m, time_s):
    """Pure persistent geometry gate; call only for admitted exposed states.

    A candidate call returns a new dict. Discard it on rejection: neither the
    previous dict nor the state arrays are modified. The initial accepted state
    must also be evaluated by the solver. Positive j implies T>low>=liquidus.
    """
    if not isinstance(config, EvaporationConfig):
        raise ValueError("config must be produced by validate_config")
    radius = _number(beam_radius_m, "beam_radius_m")
    time = _number(time_s, "time_s", zero_allowed=True)
    gate = {"onset": False, "unresolvedGeometry": False,
            "firstOnsetTime_s": None, "firstUnresolvedTime_s": None,
            "geometryAvailable": True}
    if previous is not None:
        if not isinstance(previous, Mapping) or set(previous) != set(gate):
            raise ValueError("previous must be a prior onset gate or None")
        for key in ("onset", "unresolvedGeometry", "geometryAvailable"):
            if not isinstance(previous[key], bool):
                raise ValueError(f"previous.{key} must be a boolean")
        for flag, key in (("onset", "firstOnsetTime_s"), ("unresolvedGeometry", "firstUnresolvedTime_s")):
            if previous[key] is None:
                if previous[flag]:
                    raise ValueError(f"previous.{key} is required for a latched gate")
            elif not previous[flag] or _number(previous[key], key, zero_allowed=True) > time:
                raise ValueError(f"previous.{key} is inconsistent with accepted time")
        if previous["geometryAvailable"] != (not previous["onset"] and not previous["unresolvedGeometry"]):
            raise ValueError("previous geometry availability is inconsistent with latches")
        gate = dict(previous)
    if not isinstance(state, Mapping) or not {"mass_flux_kg_m2_s", "recoil_pressure_Pa"} <= set(state):
        raise ValueError("state must contain mass_flux_kg_m2_s and recoil_pressure_Pa arrays")
    mass = _array(state["mass_flux_kg_m2_s"], "mass_flux_kg_m2_s")
    recoil = _array(state["recoil_pressure_Pa"], "recoil_pressure_Pa")
    if mass.shape != recoil.shape or np.any(mass < 0) or np.any(recoil < config.ambientPressure_Pa):
        raise ValueError("onset state must have matching shapes, nonnegative mass flux and recoil >= ambient")
    active = mass > 0
    if np.any(active):
        if config.surfaceTension_N_m is None:
            if not gate["unresolvedGeometry"]:
                gate["unresolvedGeometry"] = True
                gate["firstUnresolvedTime_s"] = time
        else:
            threshold = 2.0 * config.surfaceTension_N_m / radius
            if not math.isfinite(threshold) or threshold <= 0:
                raise ValueError("capillary pressure threshold must be positive and finite")
            if np.any((recoil[active] - config.ambientPressure_Pa) >= threshold) and not gate["onset"]:
                gate["onset"] = True
                gate["firstOnsetTime_s"] = time
    gate["geometryAvailable"] = not gate["onset"] and not gate["unresolvedGeometry"]
    return gate
