"""Sourced proxy profiles for the 316L and IN718 fixed-surface evaporative research models.

316L: every thermal and vapor constant is the SS316 column of Gan et al. 2021 (Nat Commun
12, 2379) Supplementary Table 1, used for 316L (SS316 to 316L transfer).
IN718: thermal profile of Fang et al. 2021 (arXiv 2110.07108) Supplementary Tables 2, 4
and 7; a pure-Ni single-species vapor law (Knapp et al. 2019 Table 3 Ni row; NIST Ni
standard atomic weight); surface tension from Mills 2002 IN718 Table 1. Fang's own vapor
triple (3120 K, 2224 kJ/kg, 166.534 g/mol) is recorded but not used.

Absorptivity is the existing alloy authority in four_alloy_materials.ABSORPTIVITY_AUTHORITY,
unchanged. No source gives a vaporization threshold pair for SS316 or Ni: the transition
thresholds are declared defaults and make the output label Unresolved.
"""

from types import MappingProxyType

from four_alloy_materials import ABSORPTIVITY_AUTHORITY
from lpbf_proxy_evaporation import (GAS_CONSTANT_J_MOL_K, REFERENCE_PRESSURE_PA,
                                    SCENARIO_TEMPERATURE_LIMIT_K, make_profile)


def _row(quantity, value, unit, source, locator, used_as):
    return MappingProxyType(dict(quantity=quantity, value=value, unit=unit, source=source,
                                 locator=locator, usedAs=used_as))


_COMMON_NOT_MODELLED = ("selective evaporation, activity and composition change, melt flow, surface "
                        "motion, plume and keyhole geometry are not modelled")
_RECOIL_GATE_NOTE = ("the recoil/capillary gate is a model criterion, not an observed keyhole")
_GAN = "Gan et al. 2021, Nat Commun 12, 2379, Supplementary Information (papers/gan2021_SI.pdf)"
_GAN_T1 = "Supplementary Table 1, printed p. 20, SS316 column"
_GAN_T2 = "Supplementary Table 2, printed p. 21, computational constants"
_PHASE_STEP_RAMP_K = 1.0


def _threshold_basis(alloy, species, vaporization_K):
    note = (f"declared default, not a source value: Gan 2021 SI Table 2 gives threshold pairs for Ti64 and "
            f"Al6061 only and no source gives one for {species}; chosen as {vaporization_K:g} K - 100 K and "
            f"+ 400 K around the {species} vaporization point for {alloy}")
    return dict(kind="unsourced", note=note)


_CONVENTION = dict(kind="convention", note=("declared convention: one standard atmosphere, the reference "
                                            "pressure of the normal boiling point; not a measured chamber pressure"))
_LIMIT = dict(kind="computational-limit", note="computational scenario limit; not a source validity range")


# ---------------------------------------------------------------------------------------------------------------
# 316L on the Gan 2021 SS316 column
# ---------------------------------------------------------------------------------------------------------------
SS316_SOLID_DENSITY = 7950.0           # T < 1723 K
SS316_LIQUID_DENSITY = 6881.0          # T >= 1723 K
SS316_SOLID_CP = (0.24, 420.8)         # 0.24T+420.8, T < 1723 K
SS316_LIQUID_CP = 790.0
SS316_SOLID_K = (0.0146, 10.3)         # 0.0146T+10.3, T < 1723 K
SS316_LIQUID_K = 26.9
SS316_SOLIDUS_K = 1658.0
SS316_LIQUIDUS_K = 1723.0
SS316_LATENT_MELTING = 2.6e5
SS316_VAPORIZATION_K = 3122.0
SS316_LATENT_VAPORIZATION = 6.336e6
SS316_MOLAR_MASS = 0.056               # 56 g/mol
SS316_SURFACE_TENSION = 1.87
SS316_DSIGMA_DT = -4.9e-4
SS316_EMISSIVITY = 0.3
SS316_VISCOSITY = 8e-3
SS316_MINIMAL_ABSORPTIVITY = 0.33      # recorded, not used (ray-tracing floor, not effective absorptance)
RETRO_DIFFUSION_COEFFICIENT = 0.18

SS316_DISCLOSURE = ("Thermal and vapour constants are SS316 values (Gan 2021 SI Table 1, citing Valencia and "
                    "Quested 2013) transferred to 316L as one effective Fe-rich vapour species; "
                    + _COMMON_NOT_MODELLED + "; " + _RECOIL_GATE_NOTE + ".")

SS316_CONSTANTS = (
    _row("density, solid branch", SS316_SOLID_DENSITY, "kg/m3", _GAN, f"{_GAN_T1}, row 'Density rho_l': 7950, T < 1723 K",
         "table density below 1723 K; fixed reference density at preheat for volumetric enthalpy"),
    _row("density, liquid branch", SS316_LIQUID_DENSITY, "kg/m3", _GAN, f"{_GAN_T1}, row 'Density rho_l': 6881, T >= 1723 K",
         "table density at and above 1723 K (unused by the fixed reference density)"),
    _row("heat capacity, solid branch", "0.24T+420.8", "J/(kg K)", _GAN, f"{_GAN_T1}, row 'Heat capacity C_pl': 0.24T+420.8, T < 1723 K",
         "cp below 1723 K"),
    _row("heat capacity, liquid branch", SS316_LIQUID_CP, "J/(kg K)", _GAN, f"{_GAN_T1}, row 'Heat capacity C_pl': 790, T >= 1723 K",
         "cp at and above 1723 K, held above 3122 K to maxTemperature_K"),
    _row("thermal conductivity, solid branch", "0.0146T+10.3", "W/(m K)", _GAN,
         f"{_GAN_T1}, row 'Thermal conductivity k_l': 0.0146T+10.3, T < 1723 K", "k below 1723 K"),
    _row("thermal conductivity, liquid branch", SS316_LIQUID_K, "W/(m K)", _GAN,
         f"{_GAN_T1}, row 'Thermal conductivity k_l': 26.9, T >= 1723 K", "k at and above 1723 K"),
    _row("solidus temperature", SS316_SOLIDUS_K, "K", _GAN, f"{_GAN_T1}, row 'Solidus temperature T_s'", "start of latent release"),
    _row("liquidus temperature", SS316_LIQUIDUS_K, "K", _GAN, f"{_GAN_T1}, row 'Liquidus temperature T_l'",
         "end of latent release; melt isotherm"),
    _row("latent heat of melting", SS316_LATENT_MELTING, "J/kg", _GAN, f"{_GAN_T1}, row 'Latent heat of melting L_m': 2.6x10^5",
         "latent heat spread linearly over solidus to liquidus"),
    _row("vaporization point", SS316_VAPORIZATION_K, "K", _GAN, f"{_GAN_T1}, row 'Vaporization point T_v'",
         "Clausius-Clapeyron reference temperature; table boiling endpoint"),
    _row("latent heat of vaporization", SS316_LATENT_VAPORIZATION, "J/kg", _GAN,
         f"{_GAN_T1}, row 'Latent heat of vaporization L_v': 6.336x10^6", "Clausius-Clapeyron slope and evaporative heat flux j*L_v"),
    _row("molar mass", SS316_MOLAR_MASS, "kg/mol", _GAN, f"{_GAN_T1}, row 'Molar mass M_l': 56 g/mol",
         "vapor law (single effective species)"),
    _row("surface tension", SS316_SURFACE_TENSION, "N/m", _GAN, f"{_GAN_T1}, row 'Surface tension sigma': 1.87",
         "default scalar for the recoil/capillary gate 2*sigma/r"),
    _row("thermocapillary coefficient", SS316_DSIGMA_DT, "N/(m K)", _GAN, f"{_GAN_T1}, row 'Thermocapillary coefficient': -4.9x10^-4",
         "recorded in the material (dGamma_dT); not used by the conduction solver"),
    _row("emissivity", SS316_EMISSIVITY, "-", _GAN, f"{_GAN_T1}, row 'Emissivity epsilon': 0.3", "top-face radiation"),
    _row("dynamic viscosity", SS316_VISCOSITY, "Pa s", _GAN, f"{_GAN_T1}, row 'Dynamic viscosity mu_l': 8x10^-3",
         "table viscosity column only; not used by this conduction solver"),
    _row("retro-diffusion coefficient", RETRO_DIFFUSION_COEFFICIENT, "-", _GAN, f"{_GAN_T2}, row 'Retro-diffusion coefficient beta_R'",
         "default returnFraction (Gan applies it to all three materials, SS316 included)"),
    _row("absorptivity", ABSORPTIVITY_AUTHORITY["ss316l"]["value"], "-", ABSORPTIVITY_AUTHORITY["ss316l"]["source"],
         ABSORPTIVITY_AUTHORITY["ss316l"]["locator"],
         "absorbed power A*P (existing 316L authority, bare plate, conduction regime; Gan's 0.33 'minimal "
         "absorptivity' is a ray-tracing floor and is not used)"),
)


def _ss316_k(t):
    return SS316_SOLID_K[0]*t+SS316_SOLID_K[1]


def _ss316_cp(t):
    return SS316_SOLID_CP[0]*t+SS316_SOLID_CP[1]


def ss316l_material_properties():
    """Supplied-properties object for lpbf_material_registry.material (fresh dict every call).

    Rows are [T_K, rho, k, cp, viscosity]; linear interpolation is exact for Gan's linear
    solid laws and constant liquid laws. The liquidus step is a declared 1 K ramp below 1723 K.
    """
    authority = ABSORPTIVITY_AUTHORITY["ss316l"]
    ramp = SS316_LIQUIDUS_K-_PHASE_STEP_RAMP_K
    rows = [[t, SS316_SOLID_DENSITY, _ss316_k(t), _ss316_cp(t), SS316_VISCOSITY]
            for t in (273.15, SS316_SOLIDUS_K, ramp)]
    rows += [[t, SS316_LIQUID_DENSITY, SS316_LIQUID_K, SS316_LIQUID_CP, SS316_VISCOSITY]
             for t in (SS316_LIQUIDUS_K, SS316_VAPORIZATION_K)]
    return dict(
        source=(f"{_GAN}, {_GAN_T1} (citing Valencia and Quested 2013), SS316 transferred to 316L. "
                f"Absorptivity: 316L authority, {authority['source']}, {authority['locator']}"),
        solidus_K=SS316_SOLIDUS_K, liquidus_K=SS316_LIQUIDUS_K, boiling_K=SS316_VAPORIZATION_K,
        latentHeat_J_kg=SS316_LATENT_MELTING, absorptivity=float(authority["value"]),
        emissivity=SS316_EMISSIVITY, dGamma_dT=SS316_DSIGMA_DT, table=rows, uncertaintyNote=SS316_DISCLOSURE)


SS316L_PROFILE = make_profile(
    key="ss316l", target_alloy="316L Stainless Steel", vaporization_K=SS316_VAPORIZATION_K,
    latent_heat_J_kg=SS316_LATENT_VAPORIZATION, molar_mass_kg_mol=SS316_MOLAR_MASS, disclosure=SS316_DISCLOSURE,
    source_profile=dict(
        sourceId="Gan2021-SI-Table1-SS316-proxy-for-316L", source=_GAN,
        primarySourceCitedByGan="Valencia and Quested 2013, ASM Handbook Vol. 22B, 'Thermophysical properties' (Gan SI ref. 13)",
        proxyAlloy="SS316", targetAlloy="316L Stainless Steel",
        species="single effective Fe-rich species with Gan's SS316 molar mass 56 g/mol; no selective evaporation",
        disclosure=SS316_DISCLOSURE, constants=tuple(dict(row) for row in SS316_CONSTANTS),
        recordedUnused=dict(minimalAbsorptivity=SS316_MINIMAL_ABSORPTIVITY,
                            status="Gan's ray-tracing absorptivity floor; not an effective absorptance; not used"),
        vaporizationTemperature_K=SS316_VAPORIZATION_K, latentHeat_J_kg=SS316_LATENT_VAPORIZATION,
        molarMass_kg_mol=SS316_MOLAR_MASS, gasConstant_J_molK=GAS_CONSTANT_J_MOL_K,
        referencePressure_Pa=REFERENCE_PRESSURE_PA,
        referencePressureBasis="declared convention (normal boiling point at 1 atm), as in the Ti64 model",
        transitionBasis="declared cubic Hermite matching following Gan Eqs 12/14; thresholds are unsourced defaults",
        maxTemperatureLimit_K=SCENARIO_TEMPERATURE_LIMIT_K,
        thermalContinuation=("Gan Table 1 liquid laws are constant for T >= 1723 K with no stated upper bound; "
                             "held above 3122 K as a declared assumption, not a source validity extension"),
        phaseStepRegularization=(f"Gan's solid/liquid step at {SS316_LIQUIDUS_K:g} K is carried by a declared "
                                 f"{_PHASE_STEP_RAMP_K:g} K linear ramp below it; numerical table regularization")),
    scenario_defaults=dict(transitionLow_K=3022.0, transitionHigh_K=3522.0, ambientPressure_Pa=REFERENCE_PRESSURE_PA,
                           returnFraction=RETRO_DIFFUSION_COEFFICIENT, maxTemperature_K=5000.0,
                           surfaceTension_N_m=SS316_SURFACE_TENSION),
    scenario_basis=dict(
        transitionLow_K=_threshold_basis("316L", "SS316", SS316_VAPORIZATION_K),
        transitionHigh_K=_threshold_basis("316L", "SS316", SS316_VAPORIZATION_K),
        ambientPressure_Pa=_CONVENTION, maxTemperature_K=_LIMIT,
        returnFraction=dict(kind="sourced", note=f"{_GAN}, {_GAN_T2}, retro-diffusion coefficient 0.18"),
        surfaceTension_N_m=dict(kind="sourced", note=f"{_GAN}, {_GAN_T1}, surface tension 1.87 N/m")),
    material_properties=ss316l_material_properties)


# ---------------------------------------------------------------------------------------------------------------
# IN718: Fang 2021 thermal profile, pure-Ni vapor law
# ---------------------------------------------------------------------------------------------------------------
_FANG = "Fang et al. 2021, arXiv 2110.07108, Supplementary Information (papers/fang2021_in718_thin_walls_arxiv.pdf)"
_FANG_T2 = "Supplementary Table 2, SI printed p. 2 (PDF p. 33)"
_FANG_T4 = "Supplementary Table 4, SI printed p. 2 (PDF p. 33)"
_FANG_T7 = "Supplementary Table 7, SI printed p. 3 (PDF p. 34)"
_KNAPP = ("Knapp et al. 2019, Addit. Manuf. 25, 511-521 (2019ADMA_Knapp.pdf, "
          "https://modeling.matse.psu.edu/research_files/papers/2019ADMA_Knapp.pdf)")
_KNAPP_T3 = "Table 3, journal p. 513, row 'Ni'"
_NIST_NI = ("NIST Atomic Weights and Isotopic Compositions, Nickel "
            "(https://physics.nist.gov/cgi-bin/Compositions/stand_alone.pl?ele=Ni)")
_MILLS = ("Mills 2002, Recommended Values of Thermophysical Properties for Selected Commercial Alloys, "
          "chapter IN718 (papers/mills2002_b.pdf)")

IN718_DENSITY = 8100.0
IN718_SOLIDUS_K = 1533.0
IN718_LIQUIDUS_K = 1609.0
IN718_LATENT_MELTING = 2.72e5          # 272 kJ/kg
IN718_EMISSIVITY = 0.45
# Fang SI Table 7: (T K, k W/(m K), cp J/(kg K)); constant above 1573 K per the table caption.
IN718_K_CP_NODES = ((293.0, 10.31, 362.0), (373.0, 11.88, 378.0), (473.0, 13.6, 400.0), (673.0, 16.6, 412.0),
                    (873.0, 20.1, 460.0), (1073.0, 26.3, 544.0), (1573.0, 30.75, 583.0))
NI_VAPORIZATION_K = 3183.0
NI_HEAT_OF_VAPORIZATION_J_MOL = 374.3e3
NI_MOLAR_MASS = 0.0586934              # 58.6934 g/mol
NI_LATENT_VAPORIZATION = NI_HEAT_OF_VAPORIZATION_J_MOL/NI_MOLAR_MASS
IN718_SURFACE_TENSION = 1.882          # 1882 mN/m at 1336 C
IN718_DSIGMA_DT = -1.1e-4              # -0.11 mN/(m K), Mills Eq. 8
IN718_VISCOSITY = 7.20e-3              # 7.20 mPa s at 1336 C

IN718_DISCLOSURE = ("Thermal properties are IN718 model inputs of Fang 2021 (SI Tables 2, 4, 7; k and cp held "
                    "constant above 1573 K); the vapour law is pure Ni (Knapp 2019 Table 3 Ni row, NIST Ni "
                    "atomic weight) used as a single-species proxy for IN718; "
                    + _COMMON_NOT_MODELLED + "; " + _RECOIL_GATE_NOTE + ".")

IN718_CONSTANTS = (
    _row("density", IN718_DENSITY, "kg/m3", _FANG, f"{_FANG_T2}, row 'Density'", "constant density, all temperatures"),
    _row("thermal conductivity and heat capacity nodes",
         [list(node) for node in IN718_K_CP_NODES], "K; W/(m K); J/(kg K)", _FANG,
         f"{_FANG_T7}, rows 293.0 to 1573.0; caption: linear interpolation, constant above 1573 K",
         "k(T), cp(T) by linear interpolation; held at the 1573 K values above it (extrapolation assumption)"),
    _row("solidus temperature", IN718_SOLIDUS_K, "K", _FANG, f"{_FANG_T2}, row 'Solidus temperature'", "start of latent release"),
    _row("liquidus temperature", IN718_LIQUIDUS_K, "K", _FANG, f"{_FANG_T2}, row 'Liquidus temperature'",
         "end of latent release; melt isotherm"),
    _row("latent heat of fusion", IN718_LATENT_MELTING, "J/kg", _FANG, f"{_FANG_T2}, row 'Latent heat of fusion': 272 kJ/kg",
         "latent heat spread linearly over solidus to liquidus"),
    _row("emissivity", IN718_EMISSIVITY, "-", _FANG, f"{_FANG_T4}, row 'Emissivity': 0.45 (a DED model value)",
         "top-face radiation"),
    _row("Ni boiling point", NI_VAPORIZATION_K, "K", _KNAPP, f"{_KNAPP_T3}, 'Boiling point (K)': 3183",
         "Clausius-Clapeyron reference temperature; table boiling endpoint"),
    _row("Ni heat of vaporization", NI_HEAT_OF_VAPORIZATION_J_MOL, "J/mol", _KNAPP,
         f"{_KNAPP_T3}, 'Heat of vaporization (kJ/mol)': 374.3",
         "divided by the Ni molar mass: latent heat per kg for the vapor law and j*L_v"),
    _row("Ni molar mass", NI_MOLAR_MASS, "kg/mol", _NIST_NI, "standard atomic weight 58.6934(4)", "vapor law"),
    _row("Ni latent heat of vaporization (derived)", NI_LATENT_VAPORIZATION, "J/kg", f"{_KNAPP}; {_NIST_NI}",
         "374.3 kJ/mol / 58.6934 g/mol", "Clausius-Clapeyron slope and evaporative heat flux j*L_v"),
    _row("surface tension", IN718_SURFACE_TENSION, "N/m", _MILLS,
         "Table 1, printed p. 190, liquid row 1336 C: 1882 mN/m (footnote a: extrapolated from 1725 C, 10 ppm S)",
         "default scalar for the recoil/capillary gate 2*sigma/r"),
    _row("surface tension temperature coefficient", IN718_DSIGMA_DT, "N/(m K)", _MILLS,
         "Eq. 8, printed p. 187: gamma (mN/m) = 1842 - 0.11 (T - 1725 C)",
         "recorded in the material (dGamma_dT); not used by the conduction solver"),
    _row("dynamic viscosity", IN718_VISCOSITY, "Pa s", _MILLS, "Table 1, printed p. 190, liquid row 1336 C: 7.20 mPa s",
         "table viscosity column only; not used by this conduction solver"),
    _row("absorptivity", ABSORPTIVITY_AUTHORITY["in718"]["value"], "-", ABSORPTIVITY_AUTHORITY["in718"]["source"],
         ABSORPTIVITY_AUTHORITY["in718"]["locator"], "absorbed power A*P (existing IN718 authority, bare plate)"),
)


def in718_material_properties():
    """Supplied-properties object for lpbf_material_registry.material (fresh dict every call).

    The registry needs a row at or below 273.15 K: the 293 K node is held down to it
    (declared; preheat is above 293 K in every supported run). Above 1573 K the last node
    is held to the Ni boiling point, as Fang's caption states for the source model.
    """
    authority = ABSORPTIVITY_AUTHORITY["in718"]
    first = IN718_K_CP_NODES[0]
    last = IN718_K_CP_NODES[-1]
    rows = [[273.15, IN718_DENSITY, first[1], first[2], IN718_VISCOSITY]]
    rows += [[t, IN718_DENSITY, k, cp, IN718_VISCOSITY] for t, k, cp in IN718_K_CP_NODES]
    rows.append([NI_VAPORIZATION_K, IN718_DENSITY, last[1], last[2], IN718_VISCOSITY])
    return dict(
        source=(f"{_FANG}, {_FANG_T2}, {_FANG_T4}, {_FANG_T7}; vapour endpoint {_KNAPP} {_KNAPP_T3} (pure Ni proxy). "
                f"Absorptivity: IN718 authority, {authority['source']}, {authority['locator']}"),
        solidus_K=IN718_SOLIDUS_K, liquidus_K=IN718_LIQUIDUS_K, boiling_K=NI_VAPORIZATION_K,
        latentHeat_J_kg=IN718_LATENT_MELTING, absorptivity=float(authority["value"]),
        emissivity=IN718_EMISSIVITY, dGamma_dT=IN718_DSIGMA_DT, table=rows, uncertaintyNote=IN718_DISCLOSURE)


IN718_PROFILE = make_profile(
    key="in718", target_alloy="Inconel 718", vaporization_K=NI_VAPORIZATION_K,
    latent_heat_J_kg=NI_LATENT_VAPORIZATION, molar_mass_kg_mol=NI_MOLAR_MASS, disclosure=IN718_DISCLOSURE,
    source_profile=dict(
        sourceId="Fang2021-SI-IN718-thermal-with-Knapp2019-Ni-vapour-proxy", source=f"{_FANG}; {_KNAPP}; {_MILLS}",
        proxyAlloy="pure Ni (vapour law only)", targetAlloy="Inconel 718",
        species="Ni (single species; no selective evaporation of Cr, Fe, Mn or others; no activity correction)",
        disclosure=IN718_DISCLOSURE, constants=tuple(dict(row) for row in IN718_CONSTANTS),
        recordedUnused=dict(fangBoilingPoint_K=3120.0, fangLatentHeatVaporization_J_kg=2.224e6,
                            fangEvaporatingSpeciesMolarMass_kg_mol=166.534e-3,
                            locator=f"{_FANG_T2}, rows 'Boiling point', 'Latent heat of vaporization', "
                                    "'Molar mass of the evaporating species'",
                            status="reported by Fang for their model; not mixed with the pure-Ni triple and not used"),
        vaporizationTemperature_K=NI_VAPORIZATION_K, latentHeat_J_kg=NI_LATENT_VAPORIZATION,
        molarMass_kg_mol=NI_MOLAR_MASS, gasConstant_J_molK=GAS_CONSTANT_J_MOL_K,
        referencePressure_Pa=REFERENCE_PRESSURE_PA,
        referencePressureBasis="declared convention (normal boiling point at 1 atm), as in the Ti64 model",
        transitionBasis="declared cubic Hermite matching following Gan Eqs 12/14; thresholds are unsourced defaults",
        maxTemperatureLimit_K=SCENARIO_TEMPERATURE_LIMIT_K,
        thermalContinuation=("Fang SI Table 7 holds k and cp constant above 1573 K; held through the liquid and to "
                             "maxTemperature_K as an extrapolation assumption; constant density 8100 kg/m3"),
        phaseStepRegularization="none needed: Fang's properties are continuous; latent heat over 1533 to 1609 K"),
    scenario_defaults=dict(transitionLow_K=3083.0, transitionHigh_K=3583.0, ambientPressure_Pa=REFERENCE_PRESSURE_PA,
                           returnFraction=RETRO_DIFFUSION_COEFFICIENT, maxTemperature_K=5000.0,
                           surfaceTension_N_m=IN718_SURFACE_TENSION),
    scenario_basis=dict(
        transitionLow_K=_threshold_basis("IN718", "Ni", NI_VAPORIZATION_K),
        transitionHigh_K=_threshold_basis("IN718", "Ni", NI_VAPORIZATION_K),
        ambientPressure_Pa=_CONVENTION, maxTemperature_K=_LIMIT,
        returnFraction=dict(kind="transferred", note=(f"{_GAN}, {_GAN_T2}, retro-diffusion coefficient 0.18; a "
                                                      "material-independent model constant in Gan, not an IN718 or Ni value")),
        surfaceTension_N_m=dict(kind="sourced", note=f"{_MILLS}, Table 1, printed p. 190, 1882 mN/m at 1336 C")),
    material_properties=in718_material_properties)


PROFILES = MappingProxyType({"ss316l": SS316L_PROFILE, "in718": IN718_PROFILE})

__all__ = ["PROFILES", "SS316L_PROFILE", "IN718_PROFILE", "SS316_CONSTANTS", "IN718_CONSTANTS",
           "ss316l_material_properties", "in718_material_properties"]
