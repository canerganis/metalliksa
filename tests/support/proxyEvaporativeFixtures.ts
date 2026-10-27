// Real outputs, pinned 2026-10-27 (lane evap-more). python/lpbf_worker Queue job (proxy-evaporative-surface,
// 100 um track, 1000 mm/s, 100 um beam, 80 C; 316L 200 W, IN718 150 W, IN718 150 W with user thresholds
// 4900/5000 K) via get(). Not experimental data.
/* eslint-disable */
export const proxyFixtures: any = {
 "ss316lOnset": {
  "id": "f711f775dcaf469488d718f4a9f87038",
  "cache_key": "71efb62ad64ef4003bc246d3acf8adb479447219d0d30ce08a03d7ada1d5b771",
  "status": "completed",
  "progress": 1.0,
  "log": "{\"progress\": 0.02849674697741445, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.059472747729636705, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.0925106851247086, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.12607796297854662, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.1597248735643083, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.22426677132337808, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.3836533432233312, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.5503200098900013, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.716986676556672, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.8836533432233427, \"message\": \"Evaporative surface solve\"}\n",
  "error": null,
  "created": 1793059140.2654533,
  "requestSummary": {
   "jobType": "proxy-evaporative-surface",
   "config": {
    "power_W": 200.0,
    "speed_mm_s": 1000.0,
    "beamDiameter_um": 100.0,
    "preheat_C": 80.0,
    "mesh_um": 20.0,
    "maxDt_s": 1e-06,
    "trackLength_um": 100.0,
    "cooling_s": 0.0005,
    "sourcePenetration_um": 20.0,
    "convection_W_m2K": 20.0,
    "backend": "reference",
    "surfaceMode": "bare-plate",
    "mode": "standard",
    "layers": 1,
    "tracks": 1,
    "study": "none",
    "material": "316L Stainless Steel",
    "evaporation": {
     "transitionLow_K": 3022.0,
     "transitionHigh_K": 3522.0,
     "ambientPressure_Pa": 101325.0,
     "returnFraction": 0.18,
     "maxTemperature_K": 5000.0,
     "surfaceTension_N_m": 1.87
    }
   }
  },
  "result": {
   "schema": "lpbf-ss316l-evaporative-result-v1",
   "modelId": "ss316l-gan2021-ss316-proxy-fixed-surface-evaporation-v1",
   "status": "completed",
   "alloy": "316L Stainless Steel",
   "researchLabel": "Research model: 316L on a Gan 2021 SS316 proxy profile. Not experimentally validated.",
   "disclosure": "Thermal and vapour constants are SS316 values (Gan 2021 SI Table 1, citing Valencia and Quested 2013) transferred to 316L as one effective Fe-rich vapour species; selective evaporation, activity and composition change, melt flow, surface motion, plume and keyhole geometry are not modelled; the recoil/capillary gate is a model criterion, not an observed keyhole.",
   "evidenceLabel": "Unresolved",
   "evidence": {
    "label": "Unresolved",
    "summary": "Unresolved: no source gives transitionLow_K and transitionHigh_K for this alloy; the values used are declared defaults.",
    "unresolvedInputs": [
     "transitionLow_K",
     "transitionHigh_K"
    ],
    "userInputs": [],
    "inputBasis": {
     "transitionLow_K": {
      "status": "default",
      "value": 3022.0,
      "kind": "unsourced",
      "note": "declared default, not a source value: Gan 2021 SI Table 2 gives threshold pairs for Ti64 and Al6061 only and no source gives one for SS316; chosen as 3122 K - 100 K and + 400 K around the SS316 vaporization point for 316L"
     },
     "transitionHigh_K": {
      "status": "default",
      "value": 3522.0,
      "kind": "unsourced",
      "note": "declared default, not a source value: Gan 2021 SI Table 2 gives threshold pairs for Ti64 and Al6061 only and no source gives one for SS316; chosen as 3122 K - 100 K and + 400 K around the SS316 vaporization point for 316L"
     },
     "ambientPressure_Pa": {
      "status": "default",
      "value": 101325.0,
      "kind": "convention",
      "note": "declared convention: one standard atmosphere, the reference pressure of the normal boiling point; not a measured chamber pressure"
     },
     "returnFraction": {
      "status": "default",
      "value": 0.18,
      "kind": "sourced",
      "note": "Gan et al. 2021, Nat Commun 12, 2379, Supplementary Information (papers/gan2021_SI.pdf), Supplementary Table 2, printed p. 21, computational constants, retro-diffusion coefficient 0.18"
     },
     "maxTemperature_K": {
      "status": "default",
      "value": 5000.0,
      "kind": "computational-limit",
      "note": "computational scenario limit; not a source validity range"
     },
     "surfaceTension_N_m": {
      "status": "default",
      "value": 1.87,
      "kind": "sourced",
      "note": "Gan et al. 2021, Nat Commun 12, 2379, Supplementary Information (papers/gan2021_SI.pdf), Supplementary Table 1, printed p. 20, SS316 column, surface tension 1.87 N/m"
     }
    }
   },
   "experimentalValidation": false,
   "productionReady": false,
   "tier": "Uncalibrated estimate",
   "provenance": {
    "implementationHash": "305450511901a40bf5900ac8bb2f42106ba9619feb8b0e7fb687b8a5173739dc",
    "implementationFingerprintSchema": "proxy-evaporative-dependency-closure-v1",
    "defaultImplementationHash": "13203cac19bf69db80b546c6e67ed846a0941e35ea4ad62e53a786de073c46ca",
    "moduleSha256": {
     "lpbf_proxy_evaporative_solver.py": "6600fc9b913839af23b9b4ae9710324c79b79e0ddedf063117ddc101d2b196f6",
     "lpbf_proxy_evaporation.py": "be5735b441790bb9ea983438b86eb6392a33d2d2f6228650470b14ab30b4166d",
     "lpbf_proxy_vapor_profiles.py": "b37e744713300a6f2334136ca62ccb132bb56395109b304319d99c69db513e48",
     "lpbf_ti64_evaporative_solver.py": "a821a5a21cc821f7864ece8131f5c4af644f3973957dca9a3674ae5427143b9f",
     "lpbf_ti64_evaporation.py": "eb7a529c47a49910cb36673f32170f6711d89af43e95a7a1dc9f85338cf98733"
    },
    "requestSha256": "f962288f58713ccf21b443095b51a547f3412272d0a70cc44d7595efaf9229da",
    "inputs": {
     "power_W": 200.0,
     "speed_mm_s": 1000.0,
     "beamDiameter_um": 100.0,
     "preheat_C": 80.0,
     "mesh_um": 20.0,
     "maxDt_s": 1e-06,
     "trackLength_um": 100.0,
     "cooling_s": 0.0005,
     "sourcePenetration_um": 20.0,
     "convection_W_m2K": 20.0,
     "backend": "reference",
     "surfaceMode": "bare-plate",
     "mode": "standard",
     "layers": 1,
     "tracks": 1,
     "study": "none",
     "material": "316L Stainless Steel",
     "evaporation": {
      "transitionLow_K": 3022.0,
      "transitionHigh_K": 3522.0,
      "ambientPressure_Pa": 101325.0,
      "returnFraction": 0.18,
      "maxTemperature_K": 5000.0,
      "surfaceTension_N_m": 1.87
     }
    },
    "settings": {
     "stepMethod": "explicit-Euler-conservative-enthalpy-FV",
     "conduction": "shared-harmonic-interior-faces",
     "sourceIntegration": "cell-integrated-gaussian-adaptive-gl-v2",
     "stabilitySafety": 0.9,
     "sourceIncrementLimit_K": 25.0,
     "maxCandidateRetries": 20,
     "maximumAcceptedSteps": 2000000,
     "maximumCells": 600000,
     "timeout_s": 300.0,
     "bottomBoundary": "isothermal-at-preheat-half-cell",
     "lateralBoundary": "adiabatic",
     "surface": "fixed-top-face",
     "verticalGrid": "integer-cells-anchored-at-zero-exposed-face",
     "geometry": "instantaneous-liquidus-extent-at-peak-melt-volume-snapshot",
     "minimumSourceCapture": 0.9900990099009901,
     "radiationConstant_W_m2K4": 5.670374419e-08
    },
    "material": {
     "source": "Gan et al. 2021, Nat Commun 12, 2379, Supplementary Information (papers/gan2021_SI.pdf), Supplementary Table 1, printed p. 20, SS316 column (citing Valencia and Quested 2013), SS316 transferred to 316L. Absorptivity: 316L authority, Trapp et al. 2017 (trapp2017.pdf); Ye et al. 2019 (ye2019.pdf); Matthews et al. 2018 (matthews2018.pdf, qualitative cross check), Trapp 2017 Sec. 3.1, Fig. 3a: 0.29 to 0.31 (regime I); Ye 2019 Table 1 Am 0.28; Matthews 2018 Fig. 4 (bare and powder coated discs at 1500 mm/s; the powder coated curve differs at low power, so bare plate values do not describe a powder layer)",
     "solidus_K": 1658.0,
     "liquidus_K": 1723.0,
     "boiling_K": 3122.0,
     "latentHeat_J_kg": 260000.0,
     "absorptivity": 0.3,
     "emissivity": 0.3,
     "dGamma_dT": -0.00049,
     "table": [
      [
       273.15,
       7950.0,
       14.28799,
       486.356,
       0.008
      ],
      [
       1658.0,
       7950.0,
       34.5068,
       818.72,
       0.008
      ],
      [
       1722.0,
       7950.0,
       35.4412,
       834.0799999999999,
       0.008
      ],
      [
       1723.0,
       6881.0,
       26.9,
       790.0,
       0.008
      ],
      [
       3122.0,
       6881.0,
       26.9,
       790.0,
       0.008
      ]
     ],
     "uncertaintyNote": "Property uncertainties not quantified; source string does not establish validation.",
     "quality": "literature-proxy-unvalidated",
     "name": "316L Stainless Steel",
     "version": "lpbf-materials-1",
     "temperatureCoverage_K": [
      273.15,
      3122.0
     ],
     "materialId": "proxy:gan2021-ss316-for-316l",
     "provenanceClass": "literature-proxy-ss316",
     "materialIdentitySchemaVersion": 1,
     "proxyOf": "316L Stainless Steel",
     "proxyAlloy": "SS316",
     "proxySourceId": "Gan2021-SI-Table1-SS316-proxy-for-316L",
     "proxyDisclosure": "Thermal and vapour constants are SS316 values (Gan 2021 SI Table 1, citing Valencia and Quested 2013) transferred to 316L as one effective Fe-rich vapour species; selective evaporation, activity and composition change, melt flow, surface motion, plume and keyhole geometry are not modelled; the recoil/capillary gate is a model criterion, not an observed keyhole.",
     "materialRevisionSha256": "45477951aaf36df99a9c49dc5ed77334e1381aa268e6206babb6719eaf63de03"
    },
    "vaporSource": {
     "constants": [
      {
       "locator": "Supplementary Table 1, printed p. 20, SS316 column, row 'Density rho_l': 7950, T < 1723 K",
       "quantity": "density, solid branch",
       "source": "Gan et al. 2021, Nat Commun 12, 2379, Supplementary Information (papers/gan2021_SI.pdf)",
       "unit": "kg/m3",
       "usedAs": "table density below 1723 K; fixed reference density at preheat for volumetric enthalpy",
       "value": 7950.0
      },
      {
       "locator": "Supplementary Table 1, printed p. 20, SS316 column, row 'Density rho_l': 6881, T >= 1723 K",
       "quantity": "density, liquid branch",
       "source": "Gan et al. 2021, Nat Commun 12, 2379, Supplementary Information (papers/gan2021_SI.pdf)",
       "unit": "kg/m3",
       "usedAs": "table density at and above 1723 K (unused by the fixed reference density)",
       "value": 6881.0
      },
      {
       "locator": "Supplementary Table 1, printed p. 20, SS316 column, row 'Heat capacity C_pl': 0.24T+420.8, T < 1723 K",
       "quantity": "heat capacity, solid branch",
       "source": "Gan et al. 2021, Nat Commun 12, 2379, Supplementary Information (papers/gan2021_SI.pdf)",
       "unit": "J/(kg K)",
       "usedAs": "cp below 1723 K",
       "value": "0.24T+420.8"
      },
      {
       "locator": "Supplementary Table 1, printed p. 20, SS316 column, row 'Heat capacity C_pl': 790, T >= 1723 K",
       "quantity": "heat capacity, liquid branch",
       "source": "Gan et al. 2021, Nat Commun 12, 2379, Supplementary Information (papers/gan2021_SI.pdf)",
       "unit": "J/(kg K)",
       "usedAs": "cp at and above 1723 K, held above 3122 K to maxTemperature_K",
       "value": 790.0
      },
      {
       "locator": "Supplementary Table 1, printed p. 20, SS316 column, row 'Thermal conductivity k_l': 0.0146T+10.3, T < 1723 K",
       "quantity": "thermal conductivity, solid branch",
       "source": "Gan et al. 2021, Nat Commun 12, 2379, Supplementary Information (papers/gan2021_SI.pdf)",
       "unit": "W/(m K)",
       "usedAs": "k below 1723 K",
       "value": "0.0146T+10.3"
      },
      {
       "locator": "Supplementary Table 1, printed p. 20, SS316 column, row 'Thermal conductivity k_l': 26.9, T >= 1723 K",
       "quantity": "thermal conductivity, liquid branch",
       "source": "Gan et al. 2021, Nat Commun 12, 2379, Supplementary Information (papers/gan2021_SI.pdf)",
       "unit": "W/(m K)",
       "usedAs": "k at and above 1723 K",
       "value": 26.9
      },
      {
       "locator": "Supplementary Table 1, printed p. 20, SS316 column, row 'Solidus temperature T_s'",
       "quantity": "solidus temperature",
       "source": "Gan et al. 2021, Nat Commun 12, 2379, Supplementary Information (papers/gan2021_SI.pdf)",
       "unit": "K",
       "usedAs": "start of latent release",
       "value": 1658.0
      },
      {
       "locator": "Supplementary Table 1, printed p. 20, SS316 column, row 'Liquidus temperature T_l'",
       "quantity": "liquidus temperature",
       "source": "Gan et al. 2021, Nat Commun 12, 2379, Supplementary Information (papers/gan2021_SI.pdf)",
       "unit": "K",
       "usedAs": "end of latent release; melt isotherm",
       "value": 1723.0
      },
      {
       "locator": "Supplementary Table 1, printed p. 20, SS316 column, row 'Latent heat of melting L_m': 2.6x10^5",
       "quantity": "latent heat of melting",
       "source": "Gan et al. 2021, Nat Commun 12, 2379, Supplementary Information (papers/gan2021_SI.pdf)",
       "unit": "J/kg",
       "usedAs": "latent heat spread linearly over solidus to liquidus",
       "value": 260000.0
      },
      {
       "locator": "Supplementary Table 1, printed p. 20, SS316 column, row 'Vaporization point T_v'",
       "quantity": "vaporization point",
       "source": "Gan et al. 2021, Nat Commun 12, 2379, Supplementary Information (papers/gan2021_SI.pdf)",
       "unit": "K",
       "usedAs": "Clausius-Clapeyron reference temperature; table boiling endpoint",
       "value": 3122.0
      },
      {
       "locator": "Supplementary Table 1, printed p. 20, SS316 column, row 'Latent heat of vaporization L_v': 6.336x10^6",
       "quantity": "latent heat of vaporization",
       "source": "Gan et al. 2021, Nat Commun 12, 2379, Supplementary Information (papers/gan2021_SI.pdf)",
       "unit": "J/kg",
       "usedAs": "Clausius-Clapeyron slope and evaporative heat flux j*L_v",
       "value": 6336000.0
      },
      {
       "locator": "Supplementary Table 1, printed p. 20, SS316 column, row 'Molar mass M_l': 56 g/mol",
       "quantity": "molar mass",
       "source": "Gan et al. 2021, Nat Commun 12, 2379, Supplementary Information (papers/gan2021_SI.pdf)",
       "unit": "kg/mol",
       "usedAs": "vapor law (single effective species)",
       "value": 0.056
      },
      {
       "locator": "Supplementary Table 1, printed p. 20, SS316 column, row 'Surface tension sigma': 1.87",
       "quantity": "surface tension",
       "source": "Gan et al. 2021, Nat Commun 12, 2379, Supplementary Information (papers/gan2021_SI.pdf)",
       "unit": "N/m",
       "usedAs": "default scalar for the recoil/capillary gate 2*sigma/r",
       "value": 1.87
      },
      {
       "locator": "Supplementary Table 1, printed p. 20, SS316 column, row 'Thermocapillary coefficient': -4.9x10^-4",
       "quantity": "thermocapillary coefficient",
       "source": "Gan et al. 2021, Nat Commun 12, 2379, Supplementary Information (papers/gan2021_SI.pdf)",
       "unit": "N/(m K)",
       "usedAs": "recorded in the material (dGamma_dT); not used by the conduction solver",
       "value": -0.00049
      },
      {
       "locator": "Supplementary Table 1, printed p. 20, SS316 column, row 'Emissivity epsilon': 0.3",
       "quantity": "emissivity",
       "source": "Gan et al. 2021, Nat Commun 12, 2379, Supplementary Information (papers/gan2021_SI.pdf)",
       "unit": "-",
       "usedAs": "top-face radiation",
       "value": 0.3
      },
      {
       "locator": "Supplementary Table 1, printed p. 20, SS316 column, row 'Dynamic viscosity mu_l': 8x10^-3",
       "quantity": "dynamic viscosity",
       "source": "Gan et al. 2021, Nat Commun 12, 2379, Supplementary Information (papers/gan2021_SI.pdf)",
       "unit": "Pa s",
       "usedAs": "table viscosity column only; not used by this conduction solver",
       "value": 0.008
      },
      {
       "locator": "Supplementary Table 2, printed p. 21, computational constants, row 'Retro-diffusion coefficient beta_R'",
       "quantity": "retro-diffusion coefficient",
       "source": "Gan et al. 2021, Nat Commun 12, 2379, Supplementary Information (papers/gan2021_SI.pdf)",
       "unit": "-",
       "usedAs": "default returnFraction (Gan applies it to all three materials, SS316 included)",
       "value": 0.18
      },
      {
       "locator": "Trapp 2017 Sec. 3.1, Fig. 3a: 0.29 to 0.31 (regime I); Ye 2019 Table 1 Am 0.28; Matthews 2018 Fig. 4 (bare and powder coated discs at 1500 mm/s; the powder coated curve differs at low power, so bare plate values do not describe a powder layer)",
       "quantity": "absorptivity",
       "source": "Trapp et al. 2017 (trapp2017.pdf); Ye et al. 2019 (ye2019.pdf); Matthews et al. 2018 (matthews2018.pdf, qualitative cross check)",
       "unit": "-",
       "usedAs": "absorbed power A*P (existing 316L authority, bare plate, conduction regime; Gan's 0.33 'minimal absorptivity' is a ray-tracing floor and is not used)",
       "value": 0.3
      }
     ],
     "disclosure": "Thermal and vapour constants are SS316 values (Gan 2021 SI Table 1, citing Valencia and Quested 2013) transferred to 316L as one effective Fe-rich vapour species; selective evaporation, activity and composition change, melt flow, surface motion, plume and keyhole geometry are not modelled; the recoil/capillary gate is a model criterion, not an observed keyhole.",
     "gasConstant_J_molK": 8.31446261815324,
     "latentHeat_J_kg": 6336000.0,
     "maxTemperatureLimit_K": 6000.0,
     "molarMass_kg_mol": 0.056,
     "phaseStepRegularization": "Gan's solid/liquid step at 1723 K is carried by a declared 1 K linear ramp below it; numerical table regularization",
     "primarySourceCitedByGan": "Valencia and Quested 2013, ASM Handbook Vol. 22B, 'Thermophysical properties' (Gan SI ref. 13)",
     "proxyAlloy": "SS316",
     "recordedUnused": {
      "minimalAbsorptivity": 0.33,
      "status": "Gan's ray-tracing absorptivity floor; not an effective absorptance; not used"
     },
     "referencePressureBasis": "declared convention (normal boiling point at 1 atm), as in the Ti64 model",
     "referencePressure_Pa": 101325.0,
     "source": "Gan et al. 2021, Nat Commun 12, 2379, Supplementary Information (papers/gan2021_SI.pdf)",
     "sourceId": "Gan2021-SI-Table1-SS316-proxy-for-316L",
     "species": "single effective Fe-rich species with Gan's SS316 molar mass 56 g/mol; no selective evaporation",
     "targetAlloy": "316L Stainless Steel",
     "thermalContinuation": "Gan Table 1 liquid laws are constant for T >= 1723 K with no stated upper bound; held above 3122 K as a declared assumption, not a source validity extension",
     "transitionBasis": "declared cubic Hermite matching following Gan Eqs 12/14; thresholds are unsourced defaults",
     "vaporizationTemperature_K": 3122.0
    },
    "thermalContinuation": {
     "method": "constant-last-row-of-source-table",
     "starts_K": 3122.0,
     "ends_K": 5000.0,
     "endpointDensity_kg_m3": 6881.0,
     "endpointConductivity_W_mK": 26.9,
     "endpointCp_J_kgK": 790.0,
     "densityMethod": "fixed reference density at preheat for volumetric enthalpy",
     "status": "Gan Table 1 liquid laws are constant for T >= 1723 K with no stated upper bound; held above 3122 K as a declared assumption, not a source validity extension"
    },
    "proxyNote": "Single proxy profile for 316L: a Gan 2021 SS316 proxy profile",
    "runtime_s": 0.9539999999979045,
    "executionRuntime": {
     "executable": "C:\\Users\\can02\\AppData\\Local\\Programs\\Python\\Python312\\python.exe",
     "python": "3.12.10",
     "platform": "Windows-11-10.0.26300-SP0",
     "numpy": "2.5.3"
    }
   },
   "acceptedStepCount": 1070,
   "acceptedTime_s": 0.0006000000000000001,
   "timesteps": {
    "minimum_s": 1.4325356733869304e-07,
    "maximum_s": 1e-06,
    "rejectedCandidates": 0,
    "sourceRetries": 621
   },
   "energy": {
    "input_J": 0.006000000000000003,
    "base_J": 2.0184203057592048e-07,
    "radiativeConvective_J": 1.202950119819781e-06,
    "evaporative_J": 0.00012063638752891524,
    "stored_J": 0.005877958820320695,
    "residual_J": -3.469446951953614e-18,
    "relativeResidual": 5.782411586589355e-16
   },
   "diagnosticEmittedMass_kg": 1.9039833890295964e-11,
   "diagnosticMassLabel": "Integrated effective Fe-rich species (SS316 proxy) emitted mass diagnostic; not ablation or material removal",
   "peakTemperature_K": 3710.1060122012714,
   "temperatureLabel": "Conditional fixed-surface temperature estimate",
   "geometry": {
    "time_s": 9.693236027498042e-05,
    "width_um": 80.0,
    "depth_um": null,
    "length_um": null,
    "volume_um3": null,
    "truncated": false,
    "basis": "instantaneous liquidus extent at peak-melt-volume snapshot; cell bounds",
    "label": "Uncalibrated fixed-surface isotherm estimate",
    "widthLabel": "Conditional fixed-surface liquidus width estimate",
    "widthWarning": "The model's recoil/capillary onset criterion was exceeded. This width is a fixed-surface isotherm scenario and may not represent the melt pool.",
    "refusalReason": "The model's recoil/capillary onset criterion was exceeded; surface deformation and keyhole geometry are not resolved, so depth, length and volume are not reported.",
    "liquidus_K": 1723.0,
    "cellResolution_um": 20.0
   },
   "gate": {
    "onset": true,
    "unresolvedGeometry": false,
    "firstOnsetTime_s": 5.48869075794507e-05,
    "firstUnresolvedTime_s": null,
    "geometryAvailable": false
   },
   "warnings": [
    "Thermal and vapour constants are SS316 values (Gan 2021 SI Table 1, citing Valencia and Quested 2013) transferred to 316L as one effective Fe-rich vapour species; selective evaporation, activity and composition change, melt flow, surface motion, plume and keyhole geometry are not modelled; the recoil/capillary gate is a model criterion, not an observed keyhole.",
    "Unresolved: no source gives transitionLow_K and transitionHigh_K for this alloy; the values used are declared defaults.",
    "Uncalibrated estimate of temperature and liquidus isotherm geometry for 316L from the stated transient model on a Gan 2021 SS316 proxy profile. Uncertainty is unknown and may be large. Calibrate to your machine for better accuracy.",
    "The surface is held fixed. Evaporation removes energy, but melt flow, surface recession and changes in alloy composition are not resolved.",
    "This is the liquidus isotherm envelope of the selected temperature model. The envelope uses the reported instantaneous peak-melt-volume snapshot.",
    "Active evaporation is present. Surface recession, expelled liquid, plume shielding, convective redistribution and advective redistribution are not resolved.",
    "The model's recoil/capillary onset criterion was exceeded. This width is a fixed-surface isotherm scenario and may not represent the melt pool.",
    "The model's recoil/capillary onset criterion was exceeded; surface deformation and keyhole geometry are not resolved, so depth, length and volume are not reported."
   ],
   "fieldSummary": {
    "shape": [
     20,
     20,
     15
    ],
    "dx_m": 1.9999999999999998e-05,
    "minimumFinalTemperature_K": 353.1500818601878,
    "maximumFinalTemperature_K": 765.3768744261292,
    "minimumSourceCapture": 0.9999999990207419
   },
   "jobType": "proxy-evaporative-surface",
   "settings": {
    "jobType": "proxy-evaporative-surface",
    "config": {
     "power_W": 200.0,
     "speed_mm_s": 1000.0,
     "beamDiameter_um": 100.0,
     "preheat_C": 80.0,
     "mesh_um": 20.0,
     "maxDt_s": 1e-06,
     "trackLength_um": 100.0,
     "cooling_s": 0.0005,
     "sourcePenetration_um": 20.0,
     "convection_W_m2K": 20.0,
     "backend": "reference",
     "surfaceMode": "bare-plate",
     "mode": "standard",
     "layers": 1,
     "tracks": 1,
     "study": "none",
     "material": "316L Stainless Steel",
     "evaporation": {
      "transitionLow_K": 3022.0,
      "transitionHigh_K": 3522.0,
      "ambientPressure_Pa": 101325.0,
      "returnFraction": 0.18,
      "maxTemperature_K": 5000.0,
      "surfaceTension_N_m": 1.87
     }
    }
   }
  }
 },
 "in718Onset": {
  "id": "1f3fa431a7bc419a8e6b036aedd89cfa",
  "cache_key": "3cedbdf741f63a70c0b088504f91b2f2ba6f04d9fde1146927249bd4517848e1",
  "status": "completed",
  "progress": 1.0,
  "log": "{\"progress\": 0.027210362210763072, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.05654473770569453, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.08872176654215964, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.12165540992415752, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.154722223747297, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.20157895859066188, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.34241009205602185, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.5090767587226909, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.6757434253893615, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.8424100920560321, \"message\": \"Evaporative surface solve\"}\n",
  "error": null,
  "created": 1793059142.3333676,
  "requestSummary": {
   "jobType": "proxy-evaporative-surface",
   "config": {
    "power_W": 150.0,
    "speed_mm_s": 1000.0,
    "beamDiameter_um": 100.0,
    "preheat_C": 80.0,
    "mesh_um": 20.0,
    "maxDt_s": 1e-06,
    "trackLength_um": 100.0,
    "cooling_s": 0.0005,
    "sourcePenetration_um": 20.0,
    "convection_W_m2K": 20.0,
    "backend": "reference",
    "surfaceMode": "bare-plate",
    "mode": "standard",
    "layers": 1,
    "tracks": 1,
    "study": "none",
    "material": "Inconel 718",
    "evaporation": {
     "transitionLow_K": 3083.0,
     "transitionHigh_K": 3583.0,
     "ambientPressure_Pa": 101325.0,
     "returnFraction": 0.18,
     "maxTemperature_K": 5000.0,
     "surfaceTension_N_m": 1.882
    }
   }
  },
  "result": {
   "schema": "lpbf-in718-evaporative-result-v1",
   "modelId": "in718-fang2021-ni-proxy-fixed-surface-evaporation-v1",
   "status": "completed",
   "alloy": "Inconel 718",
   "researchLabel": "Research model: IN718 on a Fang 2021 thermal profile with a pure-Ni vapour proxy. Not experimentally validated.",
   "disclosure": "Thermal properties are IN718 model inputs of Fang 2021 (SI Tables 2, 4, 7; k and cp held constant above 1573 K); the vapour law is pure Ni (Knapp 2019 Table 3 Ni row, NIST Ni atomic weight) used as a single-species proxy for IN718; selective evaporation, activity and composition change, melt flow, surface motion, plume and keyhole geometry are not modelled; the recoil/capillary gate is a model criterion, not an observed keyhole.",
   "evidenceLabel": "Unresolved",
   "evidence": {
    "label": "Unresolved",
    "summary": "Unresolved: no source gives transitionLow_K and transitionHigh_K for this alloy; the values used are declared defaults.",
    "unresolvedInputs": [
     "transitionLow_K",
     "transitionHigh_K"
    ],
    "userInputs": [],
    "inputBasis": {
     "transitionLow_K": {
      "status": "default",
      "value": 3083.0,
      "kind": "unsourced",
      "note": "declared default, not a source value: Gan 2021 SI Table 2 gives threshold pairs for Ti64 and Al6061 only and no source gives one for Ni; chosen as 3183 K - 100 K and + 400 K around the Ni vaporization point for IN718"
     },
     "transitionHigh_K": {
      "status": "default",
      "value": 3583.0,
      "kind": "unsourced",
      "note": "declared default, not a source value: Gan 2021 SI Table 2 gives threshold pairs for Ti64 and Al6061 only and no source gives one for Ni; chosen as 3183 K - 100 K and + 400 K around the Ni vaporization point for IN718"
     },
     "ambientPressure_Pa": {
      "status": "default",
      "value": 101325.0,
      "kind": "convention",
      "note": "declared convention: one standard atmosphere, the reference pressure of the normal boiling point; not a measured chamber pressure"
     },
     "returnFraction": {
      "status": "default",
      "value": 0.18,
      "kind": "transferred",
      "note": "Gan et al. 2021, Nat Commun 12, 2379, Supplementary Information (papers/gan2021_SI.pdf), Supplementary Table 2, printed p. 21, computational constants, retro-diffusion coefficient 0.18; a material-independent model constant in Gan, not an IN718 or Ni value"
     },
     "maxTemperature_K": {
      "status": "default",
      "value": 5000.0,
      "kind": "computational-limit",
      "note": "computational scenario limit; not a source validity range"
     },
     "surfaceTension_N_m": {
      "status": "default",
      "value": 1.882,
      "kind": "sourced",
      "note": "Mills 2002, Recommended Values of Thermophysical Properties for Selected Commercial Alloys, chapter IN718 (papers/mills2002_b.pdf), Table 1, printed p. 190, 1882 mN/m at 1336 C"
     }
    }
   },
   "experimentalValidation": false,
   "productionReady": false,
   "tier": "Uncalibrated estimate",
   "provenance": {
    "implementationHash": "1cb02d8cfd8432f5761bd7c209c24873b72961da6fa48137760d5d7c802f9c06",
    "implementationFingerprintSchema": "proxy-evaporative-dependency-closure-v1",
    "defaultImplementationHash": "13203cac19bf69db80b546c6e67ed846a0941e35ea4ad62e53a786de073c46ca",
    "moduleSha256": {
     "lpbf_proxy_evaporative_solver.py": "6600fc9b913839af23b9b4ae9710324c79b79e0ddedf063117ddc101d2b196f6",
     "lpbf_proxy_evaporation.py": "be5735b441790bb9ea983438b86eb6392a33d2d2f6228650470b14ab30b4166d",
     "lpbf_proxy_vapor_profiles.py": "b37e744713300a6f2334136ca62ccb132bb56395109b304319d99c69db513e48",
     "lpbf_ti64_evaporative_solver.py": "a821a5a21cc821f7864ece8131f5c4af644f3973957dca9a3674ae5427143b9f",
     "lpbf_ti64_evaporation.py": "eb7a529c47a49910cb36673f32170f6711d89af43e95a7a1dc9f85338cf98733"
    },
    "requestSha256": "ca34deb10a716325468a82023f196ee178c379ff9384aceac2bd00d3b2395bf5",
    "inputs": {
     "power_W": 150.0,
     "speed_mm_s": 1000.0,
     "beamDiameter_um": 100.0,
     "preheat_C": 80.0,
     "mesh_um": 20.0,
     "maxDt_s": 1e-06,
     "trackLength_um": 100.0,
     "cooling_s": 0.0005,
     "sourcePenetration_um": 20.0,
     "convection_W_m2K": 20.0,
     "backend": "reference",
     "surfaceMode": "bare-plate",
     "mode": "standard",
     "layers": 1,
     "tracks": 1,
     "study": "none",
     "material": "Inconel 718",
     "evaporation": {
      "transitionLow_K": 3083.0,
      "transitionHigh_K": 3583.0,
      "ambientPressure_Pa": 101325.0,
      "returnFraction": 0.18,
      "maxTemperature_K": 5000.0,
      "surfaceTension_N_m": 1.882
     }
    },
    "settings": {
     "stepMethod": "explicit-Euler-conservative-enthalpy-FV",
     "conduction": "shared-harmonic-interior-faces",
     "sourceIntegration": "cell-integrated-gaussian-adaptive-gl-v2",
     "stabilitySafety": 0.9,
     "sourceIncrementLimit_K": 25.0,
     "maxCandidateRetries": 20,
     "maximumAcceptedSteps": 2000000,
     "maximumCells": 600000,
     "timeout_s": 300.0,
     "bottomBoundary": "isothermal-at-preheat-half-cell",
     "lateralBoundary": "adiabatic",
     "surface": "fixed-top-face",
     "verticalGrid": "integer-cells-anchored-at-zero-exposed-face",
     "geometry": "instantaneous-liquidus-extent-at-peak-melt-volume-snapshot",
     "minimumSourceCapture": 0.9900990099009901,
     "radiationConstant_W_m2K4": 5.670374419e-08
    },
    "material": {
     "source": "Fang et al. 2021, arXiv 2110.07108, Supplementary Information (papers/fang2021_in718_thin_walls_arxiv.pdf), Supplementary Table 2, SI printed p. 2 (PDF p. 33), Supplementary Table 4, SI printed p. 2 (PDF p. 33), Supplementary Table 7, SI printed p. 3 (PDF p. 34); vapour endpoint Knapp et al. 2019, Addit. Manuf. 25, 511-521 (2019ADMA_Knapp.pdf, https://modeling.matse.psu.edu/research_files/papers/2019ADMA_Knapp.pdf) Table 3, journal p. 513, row 'Ni' (pure Ni proxy). Absorptivity: IN718 authority, Deisenroth et al. 2026 (deisenroth2026_in718_laser_reflections.pdf), liquid IN718 nominal energy coupling 0.32; about 0.32 along the track length at 85 W (Fig. 11); solid ground surface 0.38 (Introduction); low end 0.28 = Ye 2019 Table 1 IN625 Am by analogy",
     "solidus_K": 1533.0,
     "liquidus_K": 1609.0,
     "boiling_K": 3183.0,
     "latentHeat_J_kg": 272000.0,
     "absorptivity": 0.32,
     "emissivity": 0.45,
     "dGamma_dT": -0.00011,
     "table": [
      [
       273.15,
       8100.0,
       10.31,
       362.0,
       0.0072
      ],
      [
       293.0,
       8100.0,
       10.31,
       362.0,
       0.0072
      ],
      [
       373.0,
       8100.0,
       11.88,
       378.0,
       0.0072
      ],
      [
       473.0,
       8100.0,
       13.6,
       400.0,
       0.0072
      ],
      [
       673.0,
       8100.0,
       16.6,
       412.0,
       0.0072
      ],
      [
       873.0,
       8100.0,
       20.1,
       460.0,
       0.0072
      ],
      [
       1073.0,
       8100.0,
       26.3,
       544.0,
       0.0072
      ],
      [
       1573.0,
       8100.0,
       30.75,
       583.0,
       0.0072
      ],
      [
       3183.0,
       8100.0,
       30.75,
       583.0,
       0.0072
      ]
     ],
     "uncertaintyNote": "Property uncertainties not quantified; source string does not establish validation.",
     "quality": "literature-proxy-unvalidated",
     "name": "Inconel 718",
     "version": "lpbf-materials-1",
     "temperatureCoverage_K": [
      273.15,
      3183.0
     ],
     "materialId": "proxy:fang2021-in718-with-knapp2019-ni-vapour",
     "provenanceClass": "literature-proxy-in718-ni-vapour",
     "materialIdentitySchemaVersion": 1,
     "proxyOf": "Inconel 718",
     "proxyAlloy": "pure Ni (vapour law only)",
     "proxySourceId": "Fang2021-SI-IN718-thermal-with-Knapp2019-Ni-vapour-proxy",
     "proxyDisclosure": "Thermal properties are IN718 model inputs of Fang 2021 (SI Tables 2, 4, 7; k and cp held constant above 1573 K); the vapour law is pure Ni (Knapp 2019 Table 3 Ni row, NIST Ni atomic weight) used as a single-species proxy for IN718; selective evaporation, activity and composition change, melt flow, surface motion, plume and keyhole geometry are not modelled; the recoil/capillary gate is a model criterion, not an observed keyhole.",
     "materialRevisionSha256": "e021dfff2f54b03abc00fc0d93eb03ee5a8f4643f6847507eb0558be07d606d8"
    },
    "vaporSource": {
     "constants": [
      {
       "locator": "Supplementary Table 2, SI printed p. 2 (PDF p. 33), row 'Density'",
       "quantity": "density",
       "source": "Fang et al. 2021, arXiv 2110.07108, Supplementary Information (papers/fang2021_in718_thin_walls_arxiv.pdf)",
       "unit": "kg/m3",
       "usedAs": "constant density, all temperatures",
       "value": 8100.0
      },
      {
       "locator": "Supplementary Table 7, SI printed p. 3 (PDF p. 34), rows 293.0 to 1573.0; caption: linear interpolation, constant above 1573 K",
       "quantity": "thermal conductivity and heat capacity nodes",
       "source": "Fang et al. 2021, arXiv 2110.07108, Supplementary Information (papers/fang2021_in718_thin_walls_arxiv.pdf)",
       "unit": "K; W/(m K); J/(kg K)",
       "usedAs": "k(T), cp(T) by linear interpolation; held at the 1573 K values above it (extrapolation assumption)",
       "value": [
        [
         293.0,
         10.31,
         362.0
        ],
        [
         373.0,
         11.88,
         378.0
        ],
        [
         473.0,
         13.6,
         400.0
        ],
        [
         673.0,
         16.6,
         412.0
        ],
        [
         873.0,
         20.1,
         460.0
        ],
        [
         1073.0,
         26.3,
         544.0
        ],
        [
         1573.0,
         30.75,
         583.0
        ]
       ]
      },
      {
       "locator": "Supplementary Table 2, SI printed p. 2 (PDF p. 33), row 'Solidus temperature'",
       "quantity": "solidus temperature",
       "source": "Fang et al. 2021, arXiv 2110.07108, Supplementary Information (papers/fang2021_in718_thin_walls_arxiv.pdf)",
       "unit": "K",
       "usedAs": "start of latent release",
       "value": 1533.0
      },
      {
       "locator": "Supplementary Table 2, SI printed p. 2 (PDF p. 33), row 'Liquidus temperature'",
       "quantity": "liquidus temperature",
       "source": "Fang et al. 2021, arXiv 2110.07108, Supplementary Information (papers/fang2021_in718_thin_walls_arxiv.pdf)",
       "unit": "K",
       "usedAs": "end of latent release; melt isotherm",
       "value": 1609.0
      },
      {
       "locator": "Supplementary Table 2, SI printed p. 2 (PDF p. 33), row 'Latent heat of fusion': 272 kJ/kg",
       "quantity": "latent heat of fusion",
       "source": "Fang et al. 2021, arXiv 2110.07108, Supplementary Information (papers/fang2021_in718_thin_walls_arxiv.pdf)",
       "unit": "J/kg",
       "usedAs": "latent heat spread linearly over solidus to liquidus",
       "value": 272000.0
      },
      {
       "locator": "Supplementary Table 4, SI printed p. 2 (PDF p. 33), row 'Emissivity': 0.45 (a DED model value)",
       "quantity": "emissivity",
       "source": "Fang et al. 2021, arXiv 2110.07108, Supplementary Information (papers/fang2021_in718_thin_walls_arxiv.pdf)",
       "unit": "-",
       "usedAs": "top-face radiation",
       "value": 0.45
      },
      {
       "locator": "Table 3, journal p. 513, row 'Ni', 'Boiling point (K)': 3183",
       "quantity": "Ni boiling point",
       "source": "Knapp et al. 2019, Addit. Manuf. 25, 511-521 (2019ADMA_Knapp.pdf, https://modeling.matse.psu.edu/research_files/papers/2019ADMA_Knapp.pdf)",
       "unit": "K",
       "usedAs": "Clausius-Clapeyron reference temperature; table boiling endpoint",
       "value": 3183.0
      },
      {
       "locator": "Table 3, journal p. 513, row 'Ni', 'Heat of vaporization (kJ/mol)': 374.3",
       "quantity": "Ni heat of vaporization",
       "source": "Knapp et al. 2019, Addit. Manuf. 25, 511-521 (2019ADMA_Knapp.pdf, https://modeling.matse.psu.edu/research_files/papers/2019ADMA_Knapp.pdf)",
       "unit": "J/mol",
       "usedAs": "divided by the Ni molar mass: latent heat per kg for the vapor law and j*L_v",
       "value": 374300.0
      },
      {
       "locator": "standard atomic weight 58.6934(4)",
       "quantity": "Ni molar mass",
       "source": "NIST Atomic Weights and Isotopic Compositions, Nickel (https://physics.nist.gov/cgi-bin/Compositions/stand_alone.pl?ele=Ni)",
       "unit": "kg/mol",
       "usedAs": "vapor law",
       "value": 0.0586934
      },
      {
       "locator": "374.3 kJ/mol / 58.6934 g/mol",
       "quantity": "Ni latent heat of vaporization (derived)",
       "source": "Knapp et al. 2019, Addit. Manuf. 25, 511-521 (2019ADMA_Knapp.pdf, https://modeling.matse.psu.edu/research_files/papers/2019ADMA_Knapp.pdf); NIST Atomic Weights and Isotopic Compositions, Nickel (https://physics.nist.gov/cgi-bin/Compositions/stand_alone.pl?ele=Ni)",
       "unit": "J/kg",
       "usedAs": "Clausius-Clapeyron slope and evaporative heat flux j*L_v",
       "value": 6377207.65878276
      },
      {
       "locator": "Table 1, printed p. 190, liquid row 1336 C: 1882 mN/m (footnote a: extrapolated from 1725 C, 10 ppm S)",
       "quantity": "surface tension",
       "source": "Mills 2002, Recommended Values of Thermophysical Properties for Selected Commercial Alloys, chapter IN718 (papers/mills2002_b.pdf)",
       "unit": "N/m",
       "usedAs": "default scalar for the recoil/capillary gate 2*sigma/r",
       "value": 1.882
      },
      {
       "locator": "Eq. 8, printed p. 187: gamma (mN/m) = 1842 - 0.11 (T - 1725 C)",
       "quantity": "surface tension temperature coefficient",
       "source": "Mills 2002, Recommended Values of Thermophysical Properties for Selected Commercial Alloys, chapter IN718 (papers/mills2002_b.pdf)",
       "unit": "N/(m K)",
       "usedAs": "recorded in the material (dGamma_dT); not used by the conduction solver",
       "value": -0.00011
      },
      {
       "locator": "Table 1, printed p. 190, liquid row 1336 C: 7.20 mPa s",
       "quantity": "dynamic viscosity",
       "source": "Mills 2002, Recommended Values of Thermophysical Properties for Selected Commercial Alloys, chapter IN718 (papers/mills2002_b.pdf)",
       "unit": "Pa s",
       "usedAs": "table viscosity column only; not used by this conduction solver",
       "value": 0.0072
      },
      {
       "locator": "liquid IN718 nominal energy coupling 0.32; about 0.32 along the track length at 85 W (Fig. 11); solid ground surface 0.38 (Introduction); low end 0.28 = Ye 2019 Table 1 IN625 Am by analogy",
       "quantity": "absorptivity",
       "source": "Deisenroth et al. 2026 (deisenroth2026_in718_laser_reflections.pdf)",
       "unit": "-",
       "usedAs": "absorbed power A*P (existing IN718 authority, bare plate)",
       "value": 0.32
      }
     ],
     "disclosure": "Thermal properties are IN718 model inputs of Fang 2021 (SI Tables 2, 4, 7; k and cp held constant above 1573 K); the vapour law is pure Ni (Knapp 2019 Table 3 Ni row, NIST Ni atomic weight) used as a single-species proxy for IN718; selective evaporation, activity and composition change, melt flow, surface motion, plume and keyhole geometry are not modelled; the recoil/capillary gate is a model criterion, not an observed keyhole.",
     "gasConstant_J_molK": 8.31446261815324,
     "latentHeat_J_kg": 6377207.65878276,
     "maxTemperatureLimit_K": 6000.0,
     "molarMass_kg_mol": 0.0586934,
     "phaseStepRegularization": "none needed: Fang's properties are continuous; latent heat over 1533 to 1609 K",
     "proxyAlloy": "pure Ni (vapour law only)",
     "recordedUnused": {
      "fangBoilingPoint_K": 3120.0,
      "fangEvaporatingSpeciesMolarMass_kg_mol": 0.166534,
      "fangLatentHeatVaporization_J_kg": 2224000.0,
      "locator": "Supplementary Table 2, SI printed p. 2 (PDF p. 33), rows 'Boiling point', 'Latent heat of vaporization', 'Molar mass of the evaporating species'",
      "status": "reported by Fang for their model; not mixed with the pure-Ni triple and not used"
     },
     "referencePressureBasis": "declared convention (normal boiling point at 1 atm), as in the Ti64 model",
     "referencePressure_Pa": 101325.0,
     "source": "Fang et al. 2021, arXiv 2110.07108, Supplementary Information (papers/fang2021_in718_thin_walls_arxiv.pdf); Knapp et al. 2019, Addit. Manuf. 25, 511-521 (2019ADMA_Knapp.pdf, https://modeling.matse.psu.edu/research_files/papers/2019ADMA_Knapp.pdf); Mills 2002, Recommended Values of Thermophysical Properties for Selected Commercial Alloys, chapter IN718 (papers/mills2002_b.pdf)",
     "sourceId": "Fang2021-SI-IN718-thermal-with-Knapp2019-Ni-vapour-proxy",
     "species": "Ni (single species; no selective evaporation of Cr, Fe, Mn or others; no activity correction)",
     "targetAlloy": "Inconel 718",
     "thermalContinuation": "Fang SI Table 7 holds k and cp constant above 1573 K; held through the liquid and to maxTemperature_K as an extrapolation assumption; constant density 8100 kg/m3",
     "transitionBasis": "declared cubic Hermite matching following Gan Eqs 12/14; thresholds are unsourced defaults",
     "vaporizationTemperature_K": 3183.0
    },
    "thermalContinuation": {
     "method": "constant-last-row-of-source-table",
     "starts_K": 3183.0,
     "ends_K": 5000.0,
     "endpointDensity_kg_m3": 8100.0,
     "endpointConductivity_W_mK": 30.75,
     "endpointCp_J_kgK": 583.0,
     "densityMethod": "fixed reference density at preheat for volumetric enthalpy",
     "status": "Fang SI Table 7 holds k and cp constant above 1573 K; held through the liquid and to maxTemperature_K as an extrapolation assumption; constant density 8100 kg/m3"
    },
    "proxyNote": "Single proxy profile for IN718: a Fang 2021 IN718 thermal profile with a pure-Ni vapour law",
    "runtime_s": 0.9369999999980791,
    "executionRuntime": {
     "executable": "C:\\Users\\can02\\AppData\\Local\\Programs\\Python\\Python312\\python.exe",
     "python": "3.12.10",
     "platform": "Windows-11-10.0.26300-SP0",
     "numpy": "2.5.3"
    }
   },
   "acceptedStepCount": 1095,
   "acceptedTime_s": 0.0006000000000000001,
   "timesteps": {
    "minimum_s": 1.357962075889501e-07,
    "maximum_s": 1e-06,
    "rejectedCandidates": 0,
    "sourceRetries": 658
   },
   "energy": {
    "input_J": 0.004800000000000001,
    "base_J": 1.822302991565001e-07,
    "radiativeConvective_J": 1.4166015384204758e-06,
    "evaporative_J": 3.8135329731641025e-05,
    "stored_J": 0.004760265838430782,
    "residual_J": 1.734723475976807e-18,
    "relativeResidual": 3.6140072416183473e-16
   },
   "diagnosticEmittedMass_kg": 5.979941656615276e-12,
   "diagnosticMassLabel": "Integrated Ni-species (pure Ni proxy) emitted mass diagnostic; not ablation or material removal",
   "peakTemperature_K": 3538.884247373387,
   "temperatureLabel": "Conditional fixed-surface temperature estimate",
   "geometry": {
    "time_s": 9.487833535584835e-05,
    "width_um": 80.0,
    "depth_um": null,
    "length_um": null,
    "volume_um3": null,
    "truncated": false,
    "basis": "instantaneous liquidus extent at peak-melt-volume snapshot; cell bounds",
    "label": "Uncalibrated fixed-surface isotherm estimate",
    "widthLabel": "Conditional fixed-surface liquidus width estimate",
    "widthWarning": "The model's recoil/capillary onset criterion was exceeded. This width is a fixed-surface isotherm scenario and may not represent the melt pool.",
    "refusalReason": "The model's recoil/capillary onset criterion was exceeded; surface deformation and keyhole geometry are not resolved, so depth, length and volume are not reported.",
    "liquidus_K": 1609.0,
    "cellResolution_um": 20.0
   },
   "gate": {
    "onset": true,
    "unresolvedGeometry": false,
    "firstOnsetTime_s": 7.595254815819672e-05,
    "firstUnresolvedTime_s": null,
    "geometryAvailable": false
   },
   "warnings": [
    "Thermal properties are IN718 model inputs of Fang 2021 (SI Tables 2, 4, 7; k and cp held constant above 1573 K); the vapour law is pure Ni (Knapp 2019 Table 3 Ni row, NIST Ni atomic weight) used as a single-species proxy for IN718; selective evaporation, activity and composition change, melt flow, surface motion, plume and keyhole geometry are not modelled; the recoil/capillary gate is a model criterion, not an observed keyhole.",
    "Unresolved: no source gives transitionLow_K and transitionHigh_K for this alloy; the values used are declared defaults.",
    "Uncalibrated estimate of temperature and liquidus isotherm geometry for IN718 from the stated transient model on a Fang 2021 IN718 thermal profile with a pure-Ni vapour law. Uncertainty is unknown and may be large. Calibrate to your machine for better accuracy.",
    "The surface is held fixed. Evaporation removes energy, but melt flow, surface recession and changes in alloy composition are not resolved.",
    "This is the liquidus isotherm envelope of the selected temperature model. The envelope uses the reported instantaneous peak-melt-volume snapshot.",
    "Active evaporation is present. Surface recession, expelled liquid, plume shielding, convective redistribution and advective redistribution are not resolved.",
    "The model's recoil/capillary onset criterion was exceeded. This width is a fixed-surface isotherm scenario and may not represent the melt pool.",
    "The model's recoil/capillary onset criterion was exceeded; surface deformation and keyhole geometry are not resolved, so depth, length and volume are not reported."
   ],
   "fieldSummary": {
    "shape": [
     20,
     20,
     15
    ],
    "dx_m": 1.9999999999999998e-05,
    "minimumFinalTemperature_K": 353.15009173805834,
    "maximumFinalTemperature_K": 739.5100246142878,
    "minimumSourceCapture": 0.9999999990203614
   },
   "jobType": "proxy-evaporative-surface",
   "settings": {
    "jobType": "proxy-evaporative-surface",
    "config": {
     "power_W": 150.0,
     "speed_mm_s": 1000.0,
     "beamDiameter_um": 100.0,
     "preheat_C": 80.0,
     "mesh_um": 20.0,
     "maxDt_s": 1e-06,
     "trackLength_um": 100.0,
     "cooling_s": 0.0005,
     "sourcePenetration_um": 20.0,
     "convection_W_m2K": 20.0,
     "backend": "reference",
     "surfaceMode": "bare-plate",
     "mode": "standard",
     "layers": 1,
     "tracks": 1,
     "study": "none",
     "material": "Inconel 718",
     "evaporation": {
      "transitionLow_K": 3083.0,
      "transitionHigh_K": 3583.0,
      "ambientPressure_Pa": 101325.0,
      "returnFraction": 0.18,
      "maxTemperature_K": 5000.0,
      "surfaceTension_N_m": 1.882
     }
    }
   }
  }
 },
 "in718UserThresholds": {
  "id": "6eca4457cf1d43529dcafb5828a5c838",
  "cache_key": "03f7619b49f8ea7e06e93b3137affda34c50cfbb1966de5f7e840f9c804a7e13",
  "status": "completed",
  "progress": 1.0,
  "log": "{\"progress\": 0.027210362210763072, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.05654473770569453, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.0887217201990153, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.1216322102030839, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.15461232592512578, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.1986622036945382, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.33185320140901214, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.4985198680756808, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.6651865347423516, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.8318532014090222, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.95, \"message\": \"Evaporative surface solve\"}\n",
  "error": null,
  "created": 1793059144.2853923,
  "requestSummary": {
   "jobType": "proxy-evaporative-surface",
   "config": {
    "power_W": 150.0,
    "speed_mm_s": 1000.0,
    "beamDiameter_um": 100.0,
    "preheat_C": 80.0,
    "mesh_um": 20.0,
    "maxDt_s": 1e-06,
    "trackLength_um": 100.0,
    "cooling_s": 0.0005,
    "sourcePenetration_um": 20.0,
    "convection_W_m2K": 20.0,
    "backend": "reference",
    "surfaceMode": "bare-plate",
    "mode": "standard",
    "layers": 1,
    "tracks": 1,
    "study": "none",
    "material": "Inconel 718",
    "evaporation": {
     "transitionLow_K": 4900.0,
     "transitionHigh_K": 5000.0,
     "ambientPressure_Pa": 101325.0,
     "returnFraction": 0.18,
     "maxTemperature_K": 5000.0,
     "surfaceTension_N_m": 1.882
    }
   }
  },
  "result": {
   "schema": "lpbf-in718-evaporative-result-v1",
   "modelId": "in718-fang2021-ni-proxy-fixed-surface-evaporation-v1",
   "status": "completed",
   "alloy": "Inconel 718",
   "researchLabel": "Research model: IN718 on a Fang 2021 thermal profile with a pure-Ni vapour proxy. Not experimentally validated.",
   "disclosure": "Thermal properties are IN718 model inputs of Fang 2021 (SI Tables 2, 4, 7; k and cp held constant above 1573 K); the vapour law is pure Ni (Knapp 2019 Table 3 Ni row, NIST Ni atomic weight) used as a single-species proxy for IN718; selective evaporation, activity and composition change, melt flow, surface motion, plume and keyhole geometry are not modelled; the recoil/capillary gate is a model criterion, not an observed keyhole.",
   "evidenceLabel": "User input",
   "evidence": {
    "label": "User input",
    "summary": "User input: transitionLow_K, transitionHigh_K.",
    "unresolvedInputs": [],
    "userInputs": [
     "transitionLow_K",
     "transitionHigh_K"
    ],
    "inputBasis": {
     "transitionLow_K": {
      "status": "user input",
      "value": 4900.0,
      "kind": "user",
      "note": "value typed by the user"
     },
     "transitionHigh_K": {
      "status": "user input",
      "value": 5000.0,
      "kind": "user",
      "note": "value typed by the user"
     },
     "ambientPressure_Pa": {
      "status": "default",
      "value": 101325.0,
      "kind": "convention",
      "note": "declared convention: one standard atmosphere, the reference pressure of the normal boiling point; not a measured chamber pressure"
     },
     "returnFraction": {
      "status": "default",
      "value": 0.18,
      "kind": "transferred",
      "note": "Gan et al. 2021, Nat Commun 12, 2379, Supplementary Information (papers/gan2021_SI.pdf), Supplementary Table 2, printed p. 21, computational constants, retro-diffusion coefficient 0.18; a material-independent model constant in Gan, not an IN718 or Ni value"
     },
     "maxTemperature_K": {
      "status": "default",
      "value": 5000.0,
      "kind": "computational-limit",
      "note": "computational scenario limit; not a source validity range"
     },
     "surfaceTension_N_m": {
      "status": "default",
      "value": 1.882,
      "kind": "sourced",
      "note": "Mills 2002, Recommended Values of Thermophysical Properties for Selected Commercial Alloys, chapter IN718 (papers/mills2002_b.pdf), Table 1, printed p. 190, 1882 mN/m at 1336 C"
     }
    }
   },
   "experimentalValidation": false,
   "productionReady": false,
   "tier": "Uncalibrated estimate",
   "provenance": {
    "implementationHash": "1cb02d8cfd8432f5761bd7c209c24873b72961da6fa48137760d5d7c802f9c06",
    "implementationFingerprintSchema": "proxy-evaporative-dependency-closure-v1",
    "defaultImplementationHash": "13203cac19bf69db80b546c6e67ed846a0941e35ea4ad62e53a786de073c46ca",
    "moduleSha256": {
     "lpbf_proxy_evaporative_solver.py": "6600fc9b913839af23b9b4ae9710324c79b79e0ddedf063117ddc101d2b196f6",
     "lpbf_proxy_evaporation.py": "be5735b441790bb9ea983438b86eb6392a33d2d2f6228650470b14ab30b4166d",
     "lpbf_proxy_vapor_profiles.py": "b37e744713300a6f2334136ca62ccb132bb56395109b304319d99c69db513e48",
     "lpbf_ti64_evaporative_solver.py": "a821a5a21cc821f7864ece8131f5c4af644f3973957dca9a3674ae5427143b9f",
     "lpbf_ti64_evaporation.py": "eb7a529c47a49910cb36673f32170f6711d89af43e95a7a1dc9f85338cf98733"
    },
    "requestSha256": "e7c04d37b46d8ebfd2d2cdbf33ed121ff20e1f5d6ebb47d6953c53e1996f0e02",
    "inputs": {
     "power_W": 150.0,
     "speed_mm_s": 1000.0,
     "beamDiameter_um": 100.0,
     "preheat_C": 80.0,
     "mesh_um": 20.0,
     "maxDt_s": 1e-06,
     "trackLength_um": 100.0,
     "cooling_s": 0.0005,
     "sourcePenetration_um": 20.0,
     "convection_W_m2K": 20.0,
     "backend": "reference",
     "surfaceMode": "bare-plate",
     "mode": "standard",
     "layers": 1,
     "tracks": 1,
     "study": "none",
     "material": "Inconel 718",
     "evaporation": {
      "transitionLow_K": 4900.0,
      "transitionHigh_K": 5000.0,
      "ambientPressure_Pa": 101325.0,
      "returnFraction": 0.18,
      "maxTemperature_K": 5000.0,
      "surfaceTension_N_m": 1.882
     }
    },
    "settings": {
     "stepMethod": "explicit-Euler-conservative-enthalpy-FV",
     "conduction": "shared-harmonic-interior-faces",
     "sourceIntegration": "cell-integrated-gaussian-adaptive-gl-v2",
     "stabilitySafety": 0.9,
     "sourceIncrementLimit_K": 25.0,
     "maxCandidateRetries": 20,
     "maximumAcceptedSteps": 2000000,
     "maximumCells": 600000,
     "timeout_s": 300.0,
     "bottomBoundary": "isothermal-at-preheat-half-cell",
     "lateralBoundary": "adiabatic",
     "surface": "fixed-top-face",
     "verticalGrid": "integer-cells-anchored-at-zero-exposed-face",
     "geometry": "instantaneous-liquidus-extent-at-peak-melt-volume-snapshot",
     "minimumSourceCapture": 0.9900990099009901,
     "radiationConstant_W_m2K4": 5.670374419e-08
    },
    "material": {
     "source": "Fang et al. 2021, arXiv 2110.07108, Supplementary Information (papers/fang2021_in718_thin_walls_arxiv.pdf), Supplementary Table 2, SI printed p. 2 (PDF p. 33), Supplementary Table 4, SI printed p. 2 (PDF p. 33), Supplementary Table 7, SI printed p. 3 (PDF p. 34); vapour endpoint Knapp et al. 2019, Addit. Manuf. 25, 511-521 (2019ADMA_Knapp.pdf, https://modeling.matse.psu.edu/research_files/papers/2019ADMA_Knapp.pdf) Table 3, journal p. 513, row 'Ni' (pure Ni proxy). Absorptivity: IN718 authority, Deisenroth et al. 2026 (deisenroth2026_in718_laser_reflections.pdf), liquid IN718 nominal energy coupling 0.32; about 0.32 along the track length at 85 W (Fig. 11); solid ground surface 0.38 (Introduction); low end 0.28 = Ye 2019 Table 1 IN625 Am by analogy",
     "solidus_K": 1533.0,
     "liquidus_K": 1609.0,
     "boiling_K": 3183.0,
     "latentHeat_J_kg": 272000.0,
     "absorptivity": 0.32,
     "emissivity": 0.45,
     "dGamma_dT": -0.00011,
     "table": [
      [
       273.15,
       8100.0,
       10.31,
       362.0,
       0.0072
      ],
      [
       293.0,
       8100.0,
       10.31,
       362.0,
       0.0072
      ],
      [
       373.0,
       8100.0,
       11.88,
       378.0,
       0.0072
      ],
      [
       473.0,
       8100.0,
       13.6,
       400.0,
       0.0072
      ],
      [
       673.0,
       8100.0,
       16.6,
       412.0,
       0.0072
      ],
      [
       873.0,
       8100.0,
       20.1,
       460.0,
       0.0072
      ],
      [
       1073.0,
       8100.0,
       26.3,
       544.0,
       0.0072
      ],
      [
       1573.0,
       8100.0,
       30.75,
       583.0,
       0.0072
      ],
      [
       3183.0,
       8100.0,
       30.75,
       583.0,
       0.0072
      ]
     ],
     "uncertaintyNote": "Property uncertainties not quantified; source string does not establish validation.",
     "quality": "literature-proxy-unvalidated",
     "name": "Inconel 718",
     "version": "lpbf-materials-1",
     "temperatureCoverage_K": [
      273.15,
      3183.0
     ],
     "materialId": "proxy:fang2021-in718-with-knapp2019-ni-vapour",
     "provenanceClass": "literature-proxy-in718-ni-vapour",
     "materialIdentitySchemaVersion": 1,
     "proxyOf": "Inconel 718",
     "proxyAlloy": "pure Ni (vapour law only)",
     "proxySourceId": "Fang2021-SI-IN718-thermal-with-Knapp2019-Ni-vapour-proxy",
     "proxyDisclosure": "Thermal properties are IN718 model inputs of Fang 2021 (SI Tables 2, 4, 7; k and cp held constant above 1573 K); the vapour law is pure Ni (Knapp 2019 Table 3 Ni row, NIST Ni atomic weight) used as a single-species proxy for IN718; selective evaporation, activity and composition change, melt flow, surface motion, plume and keyhole geometry are not modelled; the recoil/capillary gate is a model criterion, not an observed keyhole.",
     "materialRevisionSha256": "e021dfff2f54b03abc00fc0d93eb03ee5a8f4643f6847507eb0558be07d606d8"
    },
    "vaporSource": {
     "constants": [
      {
       "locator": "Supplementary Table 2, SI printed p. 2 (PDF p. 33), row 'Density'",
       "quantity": "density",
       "source": "Fang et al. 2021, arXiv 2110.07108, Supplementary Information (papers/fang2021_in718_thin_walls_arxiv.pdf)",
       "unit": "kg/m3",
       "usedAs": "constant density, all temperatures",
       "value": 8100.0
      },
      {
       "locator": "Supplementary Table 7, SI printed p. 3 (PDF p. 34), rows 293.0 to 1573.0; caption: linear interpolation, constant above 1573 K",
       "quantity": "thermal conductivity and heat capacity nodes",
       "source": "Fang et al. 2021, arXiv 2110.07108, Supplementary Information (papers/fang2021_in718_thin_walls_arxiv.pdf)",
       "unit": "K; W/(m K); J/(kg K)",
       "usedAs": "k(T), cp(T) by linear interpolation; held at the 1573 K values above it (extrapolation assumption)",
       "value": [
        [
         293.0,
         10.31,
         362.0
        ],
        [
         373.0,
         11.88,
         378.0
        ],
        [
         473.0,
         13.6,
         400.0
        ],
        [
         673.0,
         16.6,
         412.0
        ],
        [
         873.0,
         20.1,
         460.0
        ],
        [
         1073.0,
         26.3,
         544.0
        ],
        [
         1573.0,
         30.75,
         583.0
        ]
       ]
      },
      {
       "locator": "Supplementary Table 2, SI printed p. 2 (PDF p. 33), row 'Solidus temperature'",
       "quantity": "solidus temperature",
       "source": "Fang et al. 2021, arXiv 2110.07108, Supplementary Information (papers/fang2021_in718_thin_walls_arxiv.pdf)",
       "unit": "K",
       "usedAs": "start of latent release",
       "value": 1533.0
      },
      {
       "locator": "Supplementary Table 2, SI printed p. 2 (PDF p. 33), row 'Liquidus temperature'",
       "quantity": "liquidus temperature",
       "source": "Fang et al. 2021, arXiv 2110.07108, Supplementary Information (papers/fang2021_in718_thin_walls_arxiv.pdf)",
       "unit": "K",
       "usedAs": "end of latent release; melt isotherm",
       "value": 1609.0
      },
      {
       "locator": "Supplementary Table 2, SI printed p. 2 (PDF p. 33), row 'Latent heat of fusion': 272 kJ/kg",
       "quantity": "latent heat of fusion",
       "source": "Fang et al. 2021, arXiv 2110.07108, Supplementary Information (papers/fang2021_in718_thin_walls_arxiv.pdf)",
       "unit": "J/kg",
       "usedAs": "latent heat spread linearly over solidus to liquidus",
       "value": 272000.0
      },
      {
       "locator": "Supplementary Table 4, SI printed p. 2 (PDF p. 33), row 'Emissivity': 0.45 (a DED model value)",
       "quantity": "emissivity",
       "source": "Fang et al. 2021, arXiv 2110.07108, Supplementary Information (papers/fang2021_in718_thin_walls_arxiv.pdf)",
       "unit": "-",
       "usedAs": "top-face radiation",
       "value": 0.45
      },
      {
       "locator": "Table 3, journal p. 513, row 'Ni', 'Boiling point (K)': 3183",
       "quantity": "Ni boiling point",
       "source": "Knapp et al. 2019, Addit. Manuf. 25, 511-521 (2019ADMA_Knapp.pdf, https://modeling.matse.psu.edu/research_files/papers/2019ADMA_Knapp.pdf)",
       "unit": "K",
       "usedAs": "Clausius-Clapeyron reference temperature; table boiling endpoint",
       "value": 3183.0
      },
      {
       "locator": "Table 3, journal p. 513, row 'Ni', 'Heat of vaporization (kJ/mol)': 374.3",
       "quantity": "Ni heat of vaporization",
       "source": "Knapp et al. 2019, Addit. Manuf. 25, 511-521 (2019ADMA_Knapp.pdf, https://modeling.matse.psu.edu/research_files/papers/2019ADMA_Knapp.pdf)",
       "unit": "J/mol",
       "usedAs": "divided by the Ni molar mass: latent heat per kg for the vapor law and j*L_v",
       "value": 374300.0
      },
      {
       "locator": "standard atomic weight 58.6934(4)",
       "quantity": "Ni molar mass",
       "source": "NIST Atomic Weights and Isotopic Compositions, Nickel (https://physics.nist.gov/cgi-bin/Compositions/stand_alone.pl?ele=Ni)",
       "unit": "kg/mol",
       "usedAs": "vapor law",
       "value": 0.0586934
      },
      {
       "locator": "374.3 kJ/mol / 58.6934 g/mol",
       "quantity": "Ni latent heat of vaporization (derived)",
       "source": "Knapp et al. 2019, Addit. Manuf. 25, 511-521 (2019ADMA_Knapp.pdf, https://modeling.matse.psu.edu/research_files/papers/2019ADMA_Knapp.pdf); NIST Atomic Weights and Isotopic Compositions, Nickel (https://physics.nist.gov/cgi-bin/Compositions/stand_alone.pl?ele=Ni)",
       "unit": "J/kg",
       "usedAs": "Clausius-Clapeyron slope and evaporative heat flux j*L_v",
       "value": 6377207.65878276
      },
      {
       "locator": "Table 1, printed p. 190, liquid row 1336 C: 1882 mN/m (footnote a: extrapolated from 1725 C, 10 ppm S)",
       "quantity": "surface tension",
       "source": "Mills 2002, Recommended Values of Thermophysical Properties for Selected Commercial Alloys, chapter IN718 (papers/mills2002_b.pdf)",
       "unit": "N/m",
       "usedAs": "default scalar for the recoil/capillary gate 2*sigma/r",
       "value": 1.882
      },
      {
       "locator": "Eq. 8, printed p. 187: gamma (mN/m) = 1842 - 0.11 (T - 1725 C)",
       "quantity": "surface tension temperature coefficient",
       "source": "Mills 2002, Recommended Values of Thermophysical Properties for Selected Commercial Alloys, chapter IN718 (papers/mills2002_b.pdf)",
       "unit": "N/(m K)",
       "usedAs": "recorded in the material (dGamma_dT); not used by the conduction solver",
       "value": -0.00011
      },
      {
       "locator": "Table 1, printed p. 190, liquid row 1336 C: 7.20 mPa s",
       "quantity": "dynamic viscosity",
       "source": "Mills 2002, Recommended Values of Thermophysical Properties for Selected Commercial Alloys, chapter IN718 (papers/mills2002_b.pdf)",
       "unit": "Pa s",
       "usedAs": "table viscosity column only; not used by this conduction solver",
       "value": 0.0072
      },
      {
       "locator": "liquid IN718 nominal energy coupling 0.32; about 0.32 along the track length at 85 W (Fig. 11); solid ground surface 0.38 (Introduction); low end 0.28 = Ye 2019 Table 1 IN625 Am by analogy",
       "quantity": "absorptivity",
       "source": "Deisenroth et al. 2026 (deisenroth2026_in718_laser_reflections.pdf)",
       "unit": "-",
       "usedAs": "absorbed power A*P (existing IN718 authority, bare plate)",
       "value": 0.32
      }
     ],
     "disclosure": "Thermal properties are IN718 model inputs of Fang 2021 (SI Tables 2, 4, 7; k and cp held constant above 1573 K); the vapour law is pure Ni (Knapp 2019 Table 3 Ni row, NIST Ni atomic weight) used as a single-species proxy for IN718; selective evaporation, activity and composition change, melt flow, surface motion, plume and keyhole geometry are not modelled; the recoil/capillary gate is a model criterion, not an observed keyhole.",
     "gasConstant_J_molK": 8.31446261815324,
     "latentHeat_J_kg": 6377207.65878276,
     "maxTemperatureLimit_K": 6000.0,
     "molarMass_kg_mol": 0.0586934,
     "phaseStepRegularization": "none needed: Fang's properties are continuous; latent heat over 1533 to 1609 K",
     "proxyAlloy": "pure Ni (vapour law only)",
     "recordedUnused": {
      "fangBoilingPoint_K": 3120.0,
      "fangEvaporatingSpeciesMolarMass_kg_mol": 0.166534,
      "fangLatentHeatVaporization_J_kg": 2224000.0,
      "locator": "Supplementary Table 2, SI printed p. 2 (PDF p. 33), rows 'Boiling point', 'Latent heat of vaporization', 'Molar mass of the evaporating species'",
      "status": "reported by Fang for their model; not mixed with the pure-Ni triple and not used"
     },
     "referencePressureBasis": "declared convention (normal boiling point at 1 atm), as in the Ti64 model",
     "referencePressure_Pa": 101325.0,
     "source": "Fang et al. 2021, arXiv 2110.07108, Supplementary Information (papers/fang2021_in718_thin_walls_arxiv.pdf); Knapp et al. 2019, Addit. Manuf. 25, 511-521 (2019ADMA_Knapp.pdf, https://modeling.matse.psu.edu/research_files/papers/2019ADMA_Knapp.pdf); Mills 2002, Recommended Values of Thermophysical Properties for Selected Commercial Alloys, chapter IN718 (papers/mills2002_b.pdf)",
     "sourceId": "Fang2021-SI-IN718-thermal-with-Knapp2019-Ni-vapour-proxy",
     "species": "Ni (single species; no selective evaporation of Cr, Fe, Mn or others; no activity correction)",
     "targetAlloy": "Inconel 718",
     "thermalContinuation": "Fang SI Table 7 holds k and cp constant above 1573 K; held through the liquid and to maxTemperature_K as an extrapolation assumption; constant density 8100 kg/m3",
     "transitionBasis": "declared cubic Hermite matching following Gan Eqs 12/14; thresholds are unsourced defaults",
     "vaporizationTemperature_K": 3183.0
    },
    "thermalContinuation": {
     "method": "constant-last-row-of-source-table",
     "starts_K": 3183.0,
     "ends_K": 5000.0,
     "endpointDensity_kg_m3": 8100.0,
     "endpointConductivity_W_mK": 30.75,
     "endpointCp_J_kgK": 583.0,
     "densityMethod": "fixed reference density at preheat for volumetric enthalpy",
     "status": "Fang SI Table 7 holds k and cp constant above 1573 K; held through the liquid and to maxTemperature_K as an extrapolation assumption; constant density 8100 kg/m3"
    },
    "proxyNote": "Single proxy profile for IN718: a Fang 2021 IN718 thermal profile with a pure-Ni vapour law",
    "runtime_s": 0.9539999999979045,
    "executionRuntime": {
     "executable": "C:\\Users\\can02\\AppData\\Local\\Programs\\Python\\Python312\\python.exe",
     "python": "3.12.10",
     "platform": "Windows-11-10.0.26300-SP0",
     "numpy": "2.5.3"
    }
   },
   "acceptedStepCount": 1101,
   "acceptedTime_s": 0.0006000000000000001,
   "timesteps": {
    "minimum_s": 5.7200681322270935e-08,
    "maximum_s": 1e-06,
    "rejectedCandidates": 0,
    "sourceRetries": 665
   },
   "energy": {
    "input_J": 0.0048,
    "base_J": 1.830901752484877e-07,
    "radiativeConvective_J": 1.4587049924837352e-06,
    "evaporative_J": 0.0,
    "stored_J": 0.004798358204832266,
    "residual_J": 1.734723475976807e-18,
    "relativeResidual": 3.6140072416183483e-16
   },
   "diagnosticEmittedMass_kg": 0.0,
   "diagnosticMassLabel": "Integrated Ni-species (pure Ni proxy) emitted mass diagnostic; not ablation or material removal",
   "peakTemperature_K": 3646.802581773472,
   "temperatureLabel": "Conditional fixed-surface temperature estimate",
   "geometry": {
    "time_s": 9.479532349001025e-05,
    "width_um": 80.0,
    "depth_um": 20.0,
    "length_um": 120.00000000000001,
    "volume_um3": 175999.99999999997,
    "truncated": false,
    "basis": "instantaneous liquidus extent at peak-melt-volume snapshot; cell bounds",
    "label": "Uncalibrated fixed-surface isotherm estimate",
    "widthLabel": "Conditional fixed-surface liquidus width estimate",
    "widthWarning": null,
    "refusalReason": null,
    "liquidus_K": 1609.0,
    "cellResolution_um": 20.0
   },
   "gate": {
    "onset": false,
    "unresolvedGeometry": false,
    "firstOnsetTime_s": null,
    "firstUnresolvedTime_s": null,
    "geometryAvailable": true
   },
   "warnings": [
    "Thermal properties are IN718 model inputs of Fang 2021 (SI Tables 2, 4, 7; k and cp held constant above 1573 K); the vapour law is pure Ni (Knapp 2019 Table 3 Ni row, NIST Ni atomic weight) used as a single-species proxy for IN718; selective evaporation, activity and composition change, melt flow, surface motion, plume and keyhole geometry are not modelled; the recoil/capillary gate is a model criterion, not an observed keyhole.",
    "User input: transitionLow_K, transitionHigh_K.",
    "Uncalibrated estimate of temperature and liquidus isotherm geometry for IN718 from the stated transient model on a Fang 2021 IN718 thermal profile with a pure-Ni vapour law. Uncertainty is unknown and may be large. Calibrate to your machine for better accuracy.",
    "The surface is held fixed. Evaporation removes energy, but melt flow, surface recession and changes in alloy composition are not resolved.",
    "This is the liquidus isotherm envelope of the selected temperature model. The envelope uses the reported instantaneous peak-melt-volume snapshot."
   ],
   "fieldSummary": {
    "shape": [
     20,
     20,
     15
    ],
    "dx_m": 1.9999999999999998e-05,
    "minimumFinalTemperature_K": 353.1500920331582,
    "maximumFinalTemperature_K": 742.9157458989421,
    "minimumSourceCapture": 0.9999999990163446
   },
   "jobType": "proxy-evaporative-surface",
   "settings": {
    "jobType": "proxy-evaporative-surface",
    "config": {
     "power_W": 150.0,
     "speed_mm_s": 1000.0,
     "beamDiameter_um": 100.0,
     "preheat_C": 80.0,
     "mesh_um": 20.0,
     "maxDt_s": 1e-06,
     "trackLength_um": 100.0,
     "cooling_s": 0.0005,
     "sourcePenetration_um": 20.0,
     "convection_W_m2K": 20.0,
     "backend": "reference",
     "surfaceMode": "bare-plate",
     "mode": "standard",
     "layers": 1,
     "tracks": 1,
     "study": "none",
     "material": "Inconel 718",
     "evaporation": {
      "transitionLow_K": 4900.0,
      "transitionHigh_K": 5000.0,
      "ambientPressure_Pa": 101325.0,
      "returnFraction": 0.18,
      "maxTemperature_K": 5000.0,
      "surfaceTension_N_m": 1.882
     }
    }
   }
  }
 }
};
