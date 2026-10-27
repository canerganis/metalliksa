"""Al6061 proxy profile and fixed-surface Al-species vapor law for AlSi10Mg; research only.

One complete, sourced, explicitly labelled Al-rich proxy profile: every thermal and
vapor constant is the Al6061 column of Gan et al. 2021 (Nat Commun 12, 2379)
Supplementary Tables 1 and 2, which cite Valencia and Quested 2013 (ASM Handbook,
"Thermophysical properties"). It is used as a proxy for AlSi10Mg. Mg and Si
selective evaporation and the real AlSi10Mg composition are not modelled. The
OPEN O8 AlSi10Mg values in four_alloy_materials.py are neither used nor relabelled.

The vapor law is the shared lpbf_proxy_evaporation one (Gan Eqs 12/14 closed form above
the high threshold, a declared cubic Hermite bridge between the thresholds). Table 2
supplies the Al6061 threshold pair 2800/3200 K that the default scenario declares as
the bridge interval; its ablation and surface-pressure polynomial constants are
recorded for traceability only and are not evaluated, as in the Ti64 model. This
module only holds the Al6061 constants and binds them to a ProxyVaporProfile.
"""

from types import MappingProxyType

from four_alloy_materials import ABSORPTIVITY_AUTHORITY
from lpbf_proxy_evaporation import (GAS_CONSTANT_J_MOL_K, REFERENCE_PRESSURE_PA,
                                    SCENARIO_TEMPERATURE_LIMIT_K, make_profile, surface_state,
                                    update_onset, validate_config as _validate_config)


SOURCE_ID = "Gan2021-SI-Tables1-2-Al6061-proxy-for-AlSi10Mg"
DISCLOSURE = ("Thermal and vapour constants are Al6061 values (Gan 2021 SI Tables 1-2, citing "
              "Valencia and Quested 2013) used as an Al-rich proxy for AlSi10Mg; Mg and Si selective "
              "evaporation and the real AlSi10Mg composition are not modelled.")
_GAN = "Gan et al. 2021, Nat Commun 12, 2379, Supplementary Information (papers/gan2021_SI.pdf)"
_T1 = "Supplementary Table 1, printed p. 20, Al6061 column"
_T2 = "Supplementary Table 2, printed p. 21, 'Vaporization constants of Al6061' block"

# Supplementary Table 1 (Al6061), every value used below.
SOLID_DENSITY_KG_M3 = 2705.0            # rho_l row: 2705, T < 915 K
LIQUID_DENSITY_KG_M3 = 2415.0           # rho_l row: 2415, T >= 915 K
SOLID_CP_SLOPE, SOLID_CP_INTERCEPT = 0.486, 725.0     # C_pl row: 0.486T+725, T < 915 K
LIQUID_CP_J_KGK = 1170.0                # C_pl row: 1170, T >= 915 K
SOLID_K_SLOPE, SOLID_K_INTERCEPT = 0.091, 152.5       # k_l row: 0.091T+152.5, T < 915 K
LIQUID_K_W_MK = 90.0                    # k_l row: 90, T >= 915 K
SOLIDUS_K = 873.0
LIQUIDUS_K = 915.0
LATENT_HEAT_MELTING_J_KG = 3.8e5
VAPORIZATION_TEMPERATURE_K = 2792.0
LATENT_HEAT_J_KG = 1.053e7
MOLAR_MASS_KG_MOL = 0.027               # 27 g/mol
SURFACE_TENSION_N_M = 0.91
SURFACE_TENSION_SLOPE_N_MK = -3.5e-4
EMISSIVITY = 0.1
DYNAMIC_VISCOSITY_PA_S = 1e-3
# Supplementary Table 2 (Al6061 vaporization constants and shared constants).
LOW_VAPORIZATION_THRESHOLD_K = 2800.0
HIGH_VAPORIZATION_THRESHOLD_K = 3200.0
RETRO_DIFFUSION_COEFFICIENT = 0.18

# Gan's property step at the liquidus is a discontinuity; the registry table is
# piecewise linear, so the step is carried by a declared 1 K ramp below 915 K.
PHASE_STEP_RAMP_K = 1.0


def _row(quantity, value, unit, table, locator, used_as):
    return MappingProxyType(dict(quantity=quantity, value=value, unit=unit, table=table,
                                 locator=locator, usedAs=used_as))


CONSTANTS = (
    _row("density, solid branch", SOLID_DENSITY_KG_M3, "kg/m3", _T1, "row 'Density rho_l': 2705, T < 915 K",
         "table density below 915 K; fixed reference density at preheat for volumetric enthalpy"),
    _row("density, liquid branch", LIQUID_DENSITY_KG_M3, "kg/m3", _T1, "row 'Density rho_l': 2415, T >= 915 K",
         "table density at and above 915 K (unused by the fixed reference density)"),
    _row("heat capacity, solid branch", "0.486T+725", "J/(kg K)", _T1, "row 'Heat capacity (liquid) C_pl': 0.486T+725, T < 915 K",
         "cp below 915 K"),
    _row("heat capacity, liquid branch", LIQUID_CP_J_KGK, "J/(kg K)", _T1, "row 'Heat capacity (liquid) C_pl': 1170, T >= 915 K",
         "cp at and above 915 K, also above 2792 K to maxTemperature_K"),
    _row("thermal conductivity, solid branch", "0.091T+152.5", "W/(m K)", _T1,
         "row 'Thermal conductivity (liquid) k_l': 0.091T+152.5, T < 915 K", "k below 915 K"),
    _row("thermal conductivity, liquid branch", LIQUID_K_W_MK, "W/(m K)", _T1,
         "row 'Thermal conductivity (liquid) k_l': 90, T >= 915 K", "k at and above 915 K"),
    _row("solidus temperature", SOLIDUS_K, "K", _T1, "row 'Solidus temperature T_s'", "start of latent release"),
    _row("liquidus temperature", LIQUIDUS_K, "K", _T1, "row 'Liquidus temperature T_l'", "end of latent release; melt isotherm"),
    _row("latent heat of melting", LATENT_HEAT_MELTING_J_KG, "J/kg", _T1, "row 'Latent heat of melting L_m': 3.8x10^5",
         "latent heat spread linearly over solidus to liquidus"),
    _row("vaporization point", VAPORIZATION_TEMPERATURE_K, "K", _T1, "row 'Vaporization point T_v'",
         "Clausius-Clapeyron reference temperature; table boiling endpoint"),
    _row("latent heat of vaporization", LATENT_HEAT_J_KG, "J/kg", _T1, "row 'Latent heat of vaporization L_v': 1.053x10^7",
         "Clausius-Clapeyron slope and evaporative heat flux j*L_v"),
    _row("molar mass", MOLAR_MASS_KG_MOL, "kg/mol", _T1, "row 'Molar mass M_l': 27 g/mol", "vapor law"),
    _row("surface tension", SURFACE_TENSION_N_M, "N/m", _T1, "row 'Surface tension sigma'",
         "default scalar for the recoil/capillary gate 2*sigma/r"),
    _row("thermocapillary coefficient", SURFACE_TENSION_SLOPE_N_MK, "N/(m K)", _T1, "row 'Thermocapillary coefficient d sigma/dT'",
         "recorded in the material (dGamma_dT); the gate uses the scalar sigma, as in the Ti64 model"),
    _row("emissivity", EMISSIVITY, "-", _T1, "row 'Emissivity epsilon'", "top-face radiation"),
    _row("dynamic viscosity", DYNAMIC_VISCOSITY_PA_S, "Pa s", _T1, "row 'Dynamic viscosity mu_l'",
         "table viscosity column only; not used by this conduction solver"),
    _row("low vaporization threshold", LOW_VAPORIZATION_THRESHOLD_K, "K", _T2, "row 'Low vaporization threshold T_L'",
         "default declared transitionLow_K (start of the Hermite bridge)"),
    _row("high vaporization threshold", HIGH_VAPORIZATION_THRESHOLD_K, "K", _T2, "row 'High vaporization threshold T_L'",
         "default declared transitionHigh_K (closed-form law at and above)"),
    _row("retro-diffusion coefficient", RETRO_DIFFUSION_COEFFICIENT, "-", "Supplementary Table 2, printed p. 21, computational constants",
         "row 'Retro-diffusion coefficient beta_R'", "default declared returnFraction"),
)

# Recorded for traceability, NOT evaluated (the Ti64 model also builds its own Hermite bridge).
RECORDED_UNUSED_TABLE2 = MappingProxyType({
    "ablationRateConstants_a1_b1": (-1.78408e-6, 1.66819e-2),
    "ablationRateConstants_c1_d1": (-5.14573e1, 5.24582e4),
    "surfacePressureConstants_a2_b2": (2.06397e-4, -6.83622e-1),
    "surfacePressureConstants_c2_d2": (-1.02617e3, 3.80205e6),
    "locator": _T2,
    "status": "recorded only; the polynomial forms are not evaluated (declared Hermite bridge, following the Ti64 model)",
})

SOURCE_PROFILE = MappingProxyType({
    "sourceId": SOURCE_ID,
    "source": _GAN,
    "primarySourceCitedByGan": "Valencia and Quested 2013, ASM Handbook Vol. 22B, 'Thermophysical properties' (Gan SI ref. 13)",
    "proxyAlloy": "Al6061",
    "targetAlloy": "AlSi10Mg",
    "species": "Al (single effective species; Al6061 proxy; no Mg/Si selective evaporation, no composition evolution)",
    "disclosure": DISCLOSURE,
    "constants": tuple(dict(row) for row in CONSTANTS),
    "recordedUnusedTable2": dict(RECORDED_UNUSED_TABLE2),
    "vaporizationTemperature_K": VAPORIZATION_TEMPERATURE_K,
    "latentHeat_J_kg": LATENT_HEAT_J_KG,
    "molarMass_kg_mol": MOLAR_MASS_KG_MOL,
    "gasConstant_J_molK": GAS_CONSTANT_J_MOL_K,
    "referencePressure_Pa": REFERENCE_PRESSURE_PA,
    "referencePressureBasis": "declared convention (normal boiling point at 1 atm), as in the Ti64 model",
    "transitionBasis": "declared cubic Hermite matching following Gan Eqs 12/14; not recovered fitting coefficients",
    "maxTemperatureLimit_K": SCENARIO_TEMPERATURE_LIMIT_K,
    "temperatureLimitBasis": "computational scenario limit; not a source validity range",
    "phaseStepRegularization": (f"Gan's solid/liquid property step at {LIQUIDUS_K:g} K is carried by a declared "
                                f"{PHASE_STEP_RAMP_K:g} K linear ramp below it; numerical table regularization"),
    "absorptivityBasis": ("not an Al6061 value: Gan's 'minimal absorptivity' 0.01 is a ray-tracing Fresnel floor, not "
                          "an effective absorptance; the AlSi10Mg absorptivity authority (four_alloy_materials."
                          "ABSORPTIVITY_AUTHORITY['alsi10mg']) is used unchanged"),
})


def _solid_k(temperature):
    return SOLID_K_SLOPE*temperature+SOLID_K_INTERCEPT


def _solid_cp(temperature):
    return SOLID_CP_SLOPE*temperature+SOLID_CP_INTERCEPT


def proxy_material_properties():
    """Supplied-properties object for lpbf_material_registry.material (fresh dict every call).

    Rows are [T_K, rho, k, cp, viscosity]; the registry interpolates linearly, which is
    exact for Gan's linear solid laws and constant liquid laws.
    """
    authority = ABSORPTIVITY_AUTHORITY["alsi10mg"]
    ramp = LIQUIDUS_K-PHASE_STEP_RAMP_K
    rows = [[273.15, SOLID_DENSITY_KG_M3, _solid_k(273.15), _solid_cp(273.15), DYNAMIC_VISCOSITY_PA_S],
            [SOLIDUS_K, SOLID_DENSITY_KG_M3, _solid_k(SOLIDUS_K), _solid_cp(SOLIDUS_K), DYNAMIC_VISCOSITY_PA_S],
            [ramp, SOLID_DENSITY_KG_M3, _solid_k(ramp), _solid_cp(ramp), DYNAMIC_VISCOSITY_PA_S],
            [LIQUIDUS_K, LIQUID_DENSITY_KG_M3, LIQUID_K_W_MK, LIQUID_CP_J_KGK, DYNAMIC_VISCOSITY_PA_S],
            [VAPORIZATION_TEMPERATURE_K, LIQUID_DENSITY_KG_M3, LIQUID_K_W_MK, LIQUID_CP_J_KGK, DYNAMIC_VISCOSITY_PA_S]]
    return dict(
        source=(f"{_GAN}, {_T1} (citing Valencia and Quested 2013), used as an Al-rich proxy for AlSi10Mg. "
                f"Absorptivity: AlSi10Mg authority, {authority['source']}, {authority['locator']}"),
        solidus_K=SOLIDUS_K, liquidus_K=LIQUIDUS_K, boiling_K=VAPORIZATION_TEMPERATURE_K,
        latentHeat_J_kg=LATENT_HEAT_MELTING_J_KG, absorptivity=float(authority["value"]),
        emissivity=EMISSIVITY, dGamma_dT=SURFACE_TENSION_SLOPE_N_MK, table=rows,
        uncertaintyNote=DISCLOSURE)


AL6061_PROFILE = make_profile(
    key="alsi10mg", target_alloy="AlSi10Mg", vaporization_K=VAPORIZATION_TEMPERATURE_K,
    latent_heat_J_kg=LATENT_HEAT_J_KG, molar_mass_kg_mol=MOLAR_MASS_KG_MOL, disclosure=DISCLOSURE,
    source_profile=SOURCE_PROFILE, material_properties=proxy_material_properties)


def validate_config(raw, liquidus_K):
    """Validate the explicit evaporation object against the Al6061 proxy profile."""
    return _validate_config(raw, liquidus_K, AL6061_PROFILE)


__all__ = ["CONSTANTS", "DISCLOSURE", "SOURCE_PROFILE", "AL6061_PROFILE",
           "proxy_material_properties", "validate_config", "surface_state", "update_onset"]
