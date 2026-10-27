// Real outputs, pinned 2026-10-27 (lane alsi). python/lpbf_worker Queue job (alsi10mg-evaporative-surface,
// 100 um track, 1300 mm/s, 100 um beam, 80 C, 300 W and 180 W) via get(). Not experimental data.
/* eslint-disable */
export const alsiFixtures: any = {
 "onset": {
  "id": "8f38ba09ee1d41129972f0bb36ad5c75",
  "cache_key": "57e987e066e3aba7b26663f20174b8d1aa1878d80661091da4dcd0937a74643d",
  "status": "completed",
  "progress": 1.0,
  "log": "{\"progress\": 0.016618602955276743, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.04355187610591996, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.07603666669100727, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.10827964229907552, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.13659420083695312, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.17307627136456377, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.24675096117800763, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.35852824492718255, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.47029955406596, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.5820951872676352, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.6939164900086398, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.8057616548249399, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.9176286656127687, \"message\": \"Evaporative surface solve\"}\n",
  "error": null,
  "created": 1793129637.4646928,
  "requestSummary": {
   "jobType": "alsi10mg-evaporative-surface",
   "config": {
    "power_W": 300.0,
    "speed_mm_s": 1300.0,
    "beamDiameter_um": 100.0,
    "preheat_C": 80.0,
    "mesh_um": 20.0,
    "maxDt_s": 1e-06,
    "trackLength_um": 100.0,
    "cooling_s": 0.0005,
    "sourcePenetration_um": 20.0,
    "convection_W_m2K": 20.0,
    "material": "AlSi10Mg",
    "backend": "reference",
    "surfaceMode": "bare-plate",
    "mode": "standard",
    "layers": 1,
    "tracks": 1,
    "study": "none",
    "evaporation": {
     "transitionLow_K": 2800.0,
     "transitionHigh_K": 3200.0,
     "ambientPressure_Pa": 101325.0,
     "returnFraction": 0.18,
     "maxTemperature_K": 5000.0,
     "surfaceTension_N_m": 0.91
    }
   }
  },
  "result": {
   "schema": "lpbf-alsi10mg-evaporative-result-v1",
   "modelId": "alsi10mg-al6061-proxy-fixed-surface-evaporation-v1",
   "status": "completed",
   "researchLabel": "Research model: AlSi10Mg on an Al6061 proxy profile. Not experimentally validated.",
   "disclosure": "Thermal and vapour constants are Al6061 values (Gan 2021 SI Tables 1-2, citing Valencia and Quested 2013) used as an Al-rich proxy for AlSi10Mg; Mg and Si selective evaporation and the real AlSi10Mg composition are not modelled.",
   "experimentalValidation": false,
   "productionReady": false,
   "tier": "Uncalibrated estimate",
   "provenance": {
    "implementationHash": "62d5e275bb844c1f3a552bd25c6f3ace15ce160d443968b0b564a921084d1a03",
    "implementationFingerprintSchema": "alsi10mg-evaporative-dependency-closure-v1",
    "defaultImplementationHash": "3a978739eb184883089cf2d4e7078a0f310adccdd3abe52f267cd4c26f993143",
    "moduleSha256": {
     "lpbf_alsi10mg_evaporative_solver.py": "51501a7bb7c542644b459c4e0cca5b338957e7f78faf124d4314ccec4c8564e2",
     "lpbf_al_proxy_evaporation.py": "cd0962e56b25e7b54a0d6219ab2fed5ff0cb4727d0008d608a2072b78c08db90",
     "lpbf_proxy_evaporation.py": "beb6d65d9799926a2255890247d66868eb6b3406351fd61088612d06965b3ed0",
     "lpbf_ti64_evaporative_solver.py": "a821a5a21cc821f7864ece8131f5c4af644f3973957dca9a3674ae5427143b9f",
     "lpbf_ti64_evaporation.py": "eb7a529c47a49910cb36673f32170f6711d89af43e95a7a1dc9f85338cf98733"
    },
    "requestSha256": "bed1f1869a1c363c3a758f3ad13f78ff0851f63bd1bd8247950e006a7f85ae9f",
    "inputs": {
     "power_W": 300.0,
     "speed_mm_s": 1300.0,
     "beamDiameter_um": 100.0,
     "preheat_C": 80.0,
     "mesh_um": 20.0,
     "maxDt_s": 1e-06,
     "trackLength_um": 100.0,
     "cooling_s": 0.0005,
     "sourcePenetration_um": 20.0,
     "convection_W_m2K": 20.0,
     "material": "AlSi10Mg",
     "backend": "reference",
     "surfaceMode": "bare-plate",
     "mode": "standard",
     "layers": 1,
     "tracks": 1,
     "study": "none",
     "evaporation": {
      "transitionLow_K": 2800.0,
      "transitionHigh_K": 3200.0,
      "ambientPressure_Pa": 101325.0,
      "returnFraction": 0.18,
      "maxTemperature_K": 5000.0,
      "surfaceTension_N_m": 0.91
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
     "source": "Gan et al. 2021, Nat Commun 12, 2379, Supplementary Information (papers/gan2021_SI.pdf), Supplementary Table 1, printed p. 20, Al6061 column (citing Valencia and Quested 2013), used as an Al-rich proxy for AlSi10Mg. Absorptivity: AlSi10Mg authority, Leis, Weber, Graf 2020, Procedia CIRP 94, 173 to 176 (leis2020.pdf), Sec. 3, Figs. 4 to 6 (pp.175 to 176): area II minimum 30 percent (35 and 100 um beams) and 28 percent (200 um); 30 to 40 percent below 1800 W/mm at 35 um; sensitivities 0.14 (Trapp 2017 Fig. 7, Al 1100 ground, a relative alloy) and 0.40 live in PROPERTY_LEDGER",
     "solidus_K": 873.0,
     "liquidus_K": 915.0,
     "boiling_K": 2792.0,
     "latentHeat_J_kg": 380000.0,
     "absorptivity": 0.3,
     "emissivity": 0.1,
     "dGamma_dT": -0.00035,
     "table": [
      [
       273.15,
       2705.0,
       177.35665,
       857.7509,
       0.001
      ],
      [
       873.0,
       2705.0,
       231.94299999999998,
       1149.278,
       0.001
      ],
      [
       914.0,
       2705.0,
       235.67399999999998,
       1169.204,
       0.001
      ],
      [
       915.0,
       2415.0,
       90.0,
       1170.0,
       0.001
      ],
      [
       2792.0,
       2415.0,
       90.0,
       1170.0,
       0.001
      ]
     ],
     "uncertaintyNote": "Property uncertainties not quantified; source string does not establish validation.",
     "quality": "literature-proxy-unvalidated",
     "name": "AlSi10Mg",
     "version": "lpbf-materials-1",
     "temperatureCoverage_K": [
      273.15,
      2792.0
     ],
     "materialId": "proxy:gan2021-al6061-for-alsi10mg",
     "provenanceClass": "literature-proxy-al6061",
     "materialIdentitySchemaVersion": 1,
     "proxyOf": "AlSi10Mg",
     "proxyAlloy": "Al6061",
     "proxySourceId": "Gan2021-SI-Tables1-2-Al6061-proxy-for-AlSi10Mg",
     "proxyDisclosure": "Thermal and vapour constants are Al6061 values (Gan 2021 SI Tables 1-2, citing Valencia and Quested 2013) used as an Al-rich proxy for AlSi10Mg; Mg and Si selective evaporation and the real AlSi10Mg composition are not modelled.",
     "materialRevisionSha256": "19947740f811507ef0a8d339f781a0d18e1402b9d7c968a8d329f4a402e00ebe"
    },
    "vaporSource": {
     "absorptivityBasis": "not an Al6061 value: Gan's 'minimal absorptivity' 0.01 is a ray-tracing Fresnel floor, not an effective absorptance; the AlSi10Mg absorptivity authority (four_alloy_materials.ABSORPTIVITY_AUTHORITY['alsi10mg']) is used unchanged",
     "constants": [
      {
       "locator": "row 'Density rho_l': 2705, T < 915 K",
       "quantity": "density, solid branch",
       "table": "Supplementary Table 1, printed p. 20, Al6061 column",
       "unit": "kg/m3",
       "usedAs": "table density below 915 K; fixed reference density at preheat for volumetric enthalpy",
       "value": 2705.0
      },
      {
       "locator": "row 'Density rho_l': 2415, T >= 915 K",
       "quantity": "density, liquid branch",
       "table": "Supplementary Table 1, printed p. 20, Al6061 column",
       "unit": "kg/m3",
       "usedAs": "table density at and above 915 K (unused by the fixed reference density)",
       "value": 2415.0
      },
      {
       "locator": "row 'Heat capacity (liquid) C_pl': 0.486T+725, T < 915 K",
       "quantity": "heat capacity, solid branch",
       "table": "Supplementary Table 1, printed p. 20, Al6061 column",
       "unit": "J/(kg K)",
       "usedAs": "cp below 915 K",
       "value": "0.486T+725"
      },
      {
       "locator": "row 'Heat capacity (liquid) C_pl': 1170, T >= 915 K",
       "quantity": "heat capacity, liquid branch",
       "table": "Supplementary Table 1, printed p. 20, Al6061 column",
       "unit": "J/(kg K)",
       "usedAs": "cp at and above 915 K, also above 2792 K to maxTemperature_K",
       "value": 1170.0
      },
      {
       "locator": "row 'Thermal conductivity (liquid) k_l': 0.091T+152.5, T < 915 K",
       "quantity": "thermal conductivity, solid branch",
       "table": "Supplementary Table 1, printed p. 20, Al6061 column",
       "unit": "W/(m K)",
       "usedAs": "k below 915 K",
       "value": "0.091T+152.5"
      },
      {
       "locator": "row 'Thermal conductivity (liquid) k_l': 90, T >= 915 K",
       "quantity": "thermal conductivity, liquid branch",
       "table": "Supplementary Table 1, printed p. 20, Al6061 column",
       "unit": "W/(m K)",
       "usedAs": "k at and above 915 K",
       "value": 90.0
      },
      {
       "locator": "row 'Solidus temperature T_s'",
       "quantity": "solidus temperature",
       "table": "Supplementary Table 1, printed p. 20, Al6061 column",
       "unit": "K",
       "usedAs": "start of latent release",
       "value": 873.0
      },
      {
       "locator": "row 'Liquidus temperature T_l'",
       "quantity": "liquidus temperature",
       "table": "Supplementary Table 1, printed p. 20, Al6061 column",
       "unit": "K",
       "usedAs": "end of latent release; melt isotherm",
       "value": 915.0
      },
      {
       "locator": "row 'Latent heat of melting L_m': 3.8x10^5",
       "quantity": "latent heat of melting",
       "table": "Supplementary Table 1, printed p. 20, Al6061 column",
       "unit": "J/kg",
       "usedAs": "latent heat spread linearly over solidus to liquidus",
       "value": 380000.0
      },
      {
       "locator": "row 'Vaporization point T_v'",
       "quantity": "vaporization point",
       "table": "Supplementary Table 1, printed p. 20, Al6061 column",
       "unit": "K",
       "usedAs": "Clausius-Clapeyron reference temperature; table boiling endpoint",
       "value": 2792.0
      },
      {
       "locator": "row 'Latent heat of vaporization L_v': 1.053x10^7",
       "quantity": "latent heat of vaporization",
       "table": "Supplementary Table 1, printed p. 20, Al6061 column",
       "unit": "J/kg",
       "usedAs": "Clausius-Clapeyron slope and evaporative heat flux j*L_v",
       "value": 10530000.0
      },
      {
       "locator": "row 'Molar mass M_l': 27 g/mol",
       "quantity": "molar mass",
       "table": "Supplementary Table 1, printed p. 20, Al6061 column",
       "unit": "kg/mol",
       "usedAs": "vapor law",
       "value": 0.027
      },
      {
       "locator": "row 'Surface tension sigma'",
       "quantity": "surface tension",
       "table": "Supplementary Table 1, printed p. 20, Al6061 column",
       "unit": "N/m",
       "usedAs": "default scalar for the recoil/capillary gate 2*sigma/r",
       "value": 0.91
      },
      {
       "locator": "row 'Thermocapillary coefficient d sigma/dT'",
       "quantity": "thermocapillary coefficient",
       "table": "Supplementary Table 1, printed p. 20, Al6061 column",
       "unit": "N/(m K)",
       "usedAs": "recorded in the material (dGamma_dT); the gate uses the scalar sigma, as in the Ti64 model",
       "value": -0.00035
      },
      {
       "locator": "row 'Emissivity epsilon'",
       "quantity": "emissivity",
       "table": "Supplementary Table 1, printed p. 20, Al6061 column",
       "unit": "-",
       "usedAs": "top-face radiation",
       "value": 0.1
      },
      {
       "locator": "row 'Dynamic viscosity mu_l'",
       "quantity": "dynamic viscosity",
       "table": "Supplementary Table 1, printed p. 20, Al6061 column",
       "unit": "Pa s",
       "usedAs": "table viscosity column only; not used by this conduction solver",
       "value": 0.001
      },
      {
       "locator": "row 'Low vaporization threshold T_L'",
       "quantity": "low vaporization threshold",
       "table": "Supplementary Table 2, printed p. 21, 'Vaporization constants of Al6061' block",
       "unit": "K",
       "usedAs": "default declared transitionLow_K (start of the Hermite bridge)",
       "value": 2800.0
      },
      {
       "locator": "row 'High vaporization threshold T_L'",
       "quantity": "high vaporization threshold",
       "table": "Supplementary Table 2, printed p. 21, 'Vaporization constants of Al6061' block",
       "unit": "K",
       "usedAs": "default declared transitionHigh_K (closed-form law at and above)",
       "value": 3200.0
      },
      {
       "locator": "row 'Retro-diffusion coefficient beta_R'",
       "quantity": "retro-diffusion coefficient",
       "table": "Supplementary Table 2, printed p. 21, computational constants",
       "unit": "-",
       "usedAs": "default declared returnFraction",
       "value": 0.18
      }
     ],
     "disclosure": "Thermal and vapour constants are Al6061 values (Gan 2021 SI Tables 1-2, citing Valencia and Quested 2013) used as an Al-rich proxy for AlSi10Mg; Mg and Si selective evaporation and the real AlSi10Mg composition are not modelled.",
     "gasConstant_J_molK": 8.31446261815324,
     "latentHeat_J_kg": 10530000.0,
     "maxTemperatureLimit_K": 6000.0,
     "molarMass_kg_mol": 0.027,
     "phaseStepRegularization": "Gan's solid/liquid property step at 915 K is carried by a declared 1 K linear ramp below it; numerical table regularization",
     "primarySourceCitedByGan": "Valencia and Quested 2013, ASM Handbook Vol. 22B, 'Thermophysical properties' (Gan SI ref. 13)",
     "proxyAlloy": "Al6061",
     "recordedUnusedTable2": {
      "ablationRateConstants_a1_b1": [
       -1.78408e-06,
       0.0166819
      ],
      "ablationRateConstants_c1_d1": [
       -51.4573,
       52458.2
      ],
      "locator": "Supplementary Table 2, printed p. 21, 'Vaporization constants of Al6061' block",
      "status": "recorded only; the polynomial forms are not evaluated (declared Hermite bridge, following the Ti64 model)",
      "surfacePressureConstants_a2_b2": [
       0.000206397,
       -0.683622
      ],
      "surfacePressureConstants_c2_d2": [
       -1026.17,
       3802050.0
      ]
     },
     "referencePressureBasis": "declared convention (normal boiling point at 1 atm), as in the Ti64 model",
     "referencePressure_Pa": 101325.0,
     "source": "Gan et al. 2021, Nat Commun 12, 2379, Supplementary Information (papers/gan2021_SI.pdf)",
     "sourceId": "Gan2021-SI-Tables1-2-Al6061-proxy-for-AlSi10Mg",
     "species": "Al (single effective species; Al6061 proxy; no Mg/Si selective evaporation, no composition evolution)",
     "targetAlloy": "AlSi10Mg",
     "temperatureLimitBasis": "computational scenario limit; not a source validity range",
     "transitionBasis": "declared cubic Hermite matching following Gan Eqs 12/14; not recovered fitting coefficients",
     "vaporizationTemperature_K": 2792.0
    },
    "thermalContinuation": {
     "method": "constant-liquid-branch-of-source",
     "starts_K": 2792.0,
     "ends_K": 5000.0,
     "endpointDensity_kg_m3": 2415.0,
     "endpointConductivity_W_mK": 90.0,
     "endpointCp_J_kgK": 1170.0,
     "densityMethod": "fixed reference density at preheat for volumetric enthalpy",
     "status": "Gan Table 1 liquid laws are constant for T >= 915 K with no stated upper bound; held above 2792 K as a declared assumption, not a source validity extension"
    },
    "proxyNote": "Single Al6061 proxy profile: thermal table, boiling endpoint and vapor law share one source",
    "runtime_s": 1.2809999999881256,
    "executionRuntime": {
     "executable": "C:\\Users\\can02\\AppData\\Local\\Programs\\Python\\Python312\\python.exe",
     "python": "3.12.10",
     "platform": "Windows-11-10.0.26300-SP0",
     "numpy": "2.5.3"
    }
   },
   "acceptedStepCount": 1374,
   "acceptedTime_s": 0.0005769230769230769,
   "timesteps": {
    "minimum_s": 5.730452937580741e-08,
    "maximum_s": 6.455220953276332e-07,
    "rejectedCandidates": 0,
    "sourceRetries": 668
   },
   "energy": {
    "input_J": 0.006923076923076918,
    "base_J": 0.003967436558142079,
    "radiativeConvective_J": 2.4182578980411084e-07,
    "evaporative_J": 4.939312772211551e-05,
    "stored_J": 0.002906005411422926,
    "residual_J": -6.938893903907228e-18,
    "relativeResidual": 1.0022846750088226e-15
   },
   "diagnosticEmittedMass_kg": 4.690705386715622e-12,
   "diagnosticMassLabel": "Integrated Al-species (Al6061 proxy) emitted mass diagnostic; not ablation or material removal",
   "peakTemperature_K": 3236.9741649606603,
   "temperatureLabel": "Conditional fixed-surface temperature estimate",
   "geometry": {
    "time_s": 7.595760459519007e-05,
    "width_um": 120.00000000000001,
    "depth_um": null,
    "length_um": null,
    "volume_um3": null,
    "truncated": false,
    "basis": "instantaneous liquidus extent at peak-melt-volume snapshot; cell bounds",
    "label": "Uncalibrated fixed-surface isotherm estimate",
    "widthLabel": "Conditional fixed-surface liquidus width estimate",
    "widthWarning": "The model's recoil/capillary onset criterion was exceeded. This width is a fixed-surface isotherm scenario and may not represent the melt pool.",
    "refusalReason": "The model's recoil/capillary onset criterion was exceeded; surface deformation and keyhole geometry are not resolved, so depth, length and volume are not reported.",
    "liquidus_K": 915.0,
    "cellResolution_um": 20.0
   },
   "gate": {
    "onset": true,
    "unresolvedGeometry": false,
    "firstOnsetTime_s": 4.014491698841372e-05,
    "firstUnresolvedTime_s": null,
    "geometryAvailable": false
   },
   "warnings": [
    "Thermal and vapour constants are Al6061 values (Gan 2021 SI Tables 1-2, citing Valencia and Quested 2013) used as an Al-rich proxy for AlSi10Mg; Mg and Si selective evaporation and the real AlSi10Mg composition are not modelled.",
    "Uncalibrated estimate of temperature and liquidus isotherm geometry for AlSi10Mg from the stated transient model on an Al6061 proxy profile. Uncertainty is unknown and may be large. Calibrate to your machine for better accuracy.",
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
    "minimumFinalTemperature_K": 355.18368664339107,
    "maximumFinalTemperature_K": 392.13255149786875,
    "minimumSourceCapture": 0.9999999990172297
   },
   "jobType": "alsi10mg-evaporative-surface",
   "settings": {
    "jobType": "alsi10mg-evaporative-surface",
    "config": {
     "power_W": 300.0,
     "speed_mm_s": 1300.0,
     "beamDiameter_um": 100.0,
     "preheat_C": 80.0,
     "mesh_um": 20.0,
     "maxDt_s": 1e-06,
     "trackLength_um": 100.0,
     "cooling_s": 0.0005,
     "sourcePenetration_um": 20.0,
     "convection_W_m2K": 20.0,
     "material": "AlSi10Mg",
     "backend": "reference",
     "surfaceMode": "bare-plate",
     "mode": "standard",
     "layers": 1,
     "tracks": 1,
     "study": "none",
     "evaporation": {
      "transitionLow_K": 2800.0,
      "transitionHigh_K": 3200.0,
      "ambientPressure_Pa": 101325.0,
      "returnFraction": 0.18,
      "maxTemperature_K": 5000.0,
      "surfaceTension_N_m": 0.91
     }
    }
   }
  }
 },
 "noEvaporation": {
  "id": "5a7e9e1d5a8a412498ba18e0f57bb06b",
  "cache_key": "f1ff1015be5f4c6149ea8e4ffc05c70b8a757980bad70359f73212e25aaaee4b",
  "status": "completed",
  "progress": 1.0,
  "log": "{\"progress\": 0.03421264799506317, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.07680152738693354, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.12153667197121032, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.15922704632279458, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.2478443950313543, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.35971328899836325, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.4715837189447455, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.5834694480754264, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.6953706830431912, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.8072863274056586, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.919215100001586, \"message\": \"Evaporative surface solve\"}\n",
  "error": null,
  "created": 1793129639.6972983,
  "requestSummary": {
   "jobType": "alsi10mg-evaporative-surface",
   "config": {
    "power_W": 180.0,
    "speed_mm_s": 1300.0,
    "beamDiameter_um": 100.0,
    "preheat_C": 80.0,
    "mesh_um": 20.0,
    "maxDt_s": 1e-06,
    "trackLength_um": 100.0,
    "cooling_s": 0.0005,
    "sourcePenetration_um": 20.0,
    "convection_W_m2K": 20.0,
    "material": "AlSi10Mg",
    "backend": "reference",
    "surfaceMode": "bare-plate",
    "mode": "standard",
    "layers": 1,
    "tracks": 1,
    "study": "none",
    "evaporation": {
     "transitionLow_K": 2800.0,
     "transitionHigh_K": 3200.0,
     "ambientPressure_Pa": 101325.0,
     "returnFraction": 0.18,
     "maxTemperature_K": 5000.0,
     "surfaceTension_N_m": 0.91
    }
   }
  },
  "result": {
   "schema": "lpbf-alsi10mg-evaporative-result-v1",
   "modelId": "alsi10mg-al6061-proxy-fixed-surface-evaporation-v1",
   "status": "completed",
   "researchLabel": "Research model: AlSi10Mg on an Al6061 proxy profile. Not experimentally validated.",
   "disclosure": "Thermal and vapour constants are Al6061 values (Gan 2021 SI Tables 1-2, citing Valencia and Quested 2013) used as an Al-rich proxy for AlSi10Mg; Mg and Si selective evaporation and the real AlSi10Mg composition are not modelled.",
   "experimentalValidation": false,
   "productionReady": false,
   "tier": "Uncalibrated estimate",
   "provenance": {
    "implementationHash": "62d5e275bb844c1f3a552bd25c6f3ace15ce160d443968b0b564a921084d1a03",
    "implementationFingerprintSchema": "alsi10mg-evaporative-dependency-closure-v1",
    "defaultImplementationHash": "3a978739eb184883089cf2d4e7078a0f310adccdd3abe52f267cd4c26f993143",
    "moduleSha256": {
     "lpbf_alsi10mg_evaporative_solver.py": "51501a7bb7c542644b459c4e0cca5b338957e7f78faf124d4314ccec4c8564e2",
     "lpbf_al_proxy_evaporation.py": "cd0962e56b25e7b54a0d6219ab2fed5ff0cb4727d0008d608a2072b78c08db90",
     "lpbf_proxy_evaporation.py": "beb6d65d9799926a2255890247d66868eb6b3406351fd61088612d06965b3ed0",
     "lpbf_ti64_evaporative_solver.py": "a821a5a21cc821f7864ece8131f5c4af644f3973957dca9a3674ae5427143b9f",
     "lpbf_ti64_evaporation.py": "eb7a529c47a49910cb36673f32170f6711d89af43e95a7a1dc9f85338cf98733"
    },
    "requestSha256": "e3c4d94d818abf5780a95b813e3d6338493216e76e8d2ab22b3302d45642018e",
    "inputs": {
     "power_W": 180.0,
     "speed_mm_s": 1300.0,
     "beamDiameter_um": 100.0,
     "preheat_C": 80.0,
     "mesh_um": 20.0,
     "maxDt_s": 1e-06,
     "trackLength_um": 100.0,
     "cooling_s": 0.0005,
     "sourcePenetration_um": 20.0,
     "convection_W_m2K": 20.0,
     "material": "AlSi10Mg",
     "backend": "reference",
     "surfaceMode": "bare-plate",
     "mode": "standard",
     "layers": 1,
     "tracks": 1,
     "study": "none",
     "evaporation": {
      "transitionLow_K": 2800.0,
      "transitionHigh_K": 3200.0,
      "ambientPressure_Pa": 101325.0,
      "returnFraction": 0.18,
      "maxTemperature_K": 5000.0,
      "surfaceTension_N_m": 0.91
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
     "source": "Gan et al. 2021, Nat Commun 12, 2379, Supplementary Information (papers/gan2021_SI.pdf), Supplementary Table 1, printed p. 20, Al6061 column (citing Valencia and Quested 2013), used as an Al-rich proxy for AlSi10Mg. Absorptivity: AlSi10Mg authority, Leis, Weber, Graf 2020, Procedia CIRP 94, 173 to 176 (leis2020.pdf), Sec. 3, Figs. 4 to 6 (pp.175 to 176): area II minimum 30 percent (35 and 100 um beams) and 28 percent (200 um); 30 to 40 percent below 1800 W/mm at 35 um; sensitivities 0.14 (Trapp 2017 Fig. 7, Al 1100 ground, a relative alloy) and 0.40 live in PROPERTY_LEDGER",
     "solidus_K": 873.0,
     "liquidus_K": 915.0,
     "boiling_K": 2792.0,
     "latentHeat_J_kg": 380000.0,
     "absorptivity": 0.3,
     "emissivity": 0.1,
     "dGamma_dT": -0.00035,
     "table": [
      [
       273.15,
       2705.0,
       177.35665,
       857.7509,
       0.001
      ],
      [
       873.0,
       2705.0,
       231.94299999999998,
       1149.278,
       0.001
      ],
      [
       914.0,
       2705.0,
       235.67399999999998,
       1169.204,
       0.001
      ],
      [
       915.0,
       2415.0,
       90.0,
       1170.0,
       0.001
      ],
      [
       2792.0,
       2415.0,
       90.0,
       1170.0,
       0.001
      ]
     ],
     "uncertaintyNote": "Property uncertainties not quantified; source string does not establish validation.",
     "quality": "literature-proxy-unvalidated",
     "name": "AlSi10Mg",
     "version": "lpbf-materials-1",
     "temperatureCoverage_K": [
      273.15,
      2792.0
     ],
     "materialId": "proxy:gan2021-al6061-for-alsi10mg",
     "provenanceClass": "literature-proxy-al6061",
     "materialIdentitySchemaVersion": 1,
     "proxyOf": "AlSi10Mg",
     "proxyAlloy": "Al6061",
     "proxySourceId": "Gan2021-SI-Tables1-2-Al6061-proxy-for-AlSi10Mg",
     "proxyDisclosure": "Thermal and vapour constants are Al6061 values (Gan 2021 SI Tables 1-2, citing Valencia and Quested 2013) used as an Al-rich proxy for AlSi10Mg; Mg and Si selective evaporation and the real AlSi10Mg composition are not modelled.",
     "materialRevisionSha256": "19947740f811507ef0a8d339f781a0d18e1402b9d7c968a8d329f4a402e00ebe"
    },
    "vaporSource": {
     "absorptivityBasis": "not an Al6061 value: Gan's 'minimal absorptivity' 0.01 is a ray-tracing Fresnel floor, not an effective absorptance; the AlSi10Mg absorptivity authority (four_alloy_materials.ABSORPTIVITY_AUTHORITY['alsi10mg']) is used unchanged",
     "constants": [
      {
       "locator": "row 'Density rho_l': 2705, T < 915 K",
       "quantity": "density, solid branch",
       "table": "Supplementary Table 1, printed p. 20, Al6061 column",
       "unit": "kg/m3",
       "usedAs": "table density below 915 K; fixed reference density at preheat for volumetric enthalpy",
       "value": 2705.0
      },
      {
       "locator": "row 'Density rho_l': 2415, T >= 915 K",
       "quantity": "density, liquid branch",
       "table": "Supplementary Table 1, printed p. 20, Al6061 column",
       "unit": "kg/m3",
       "usedAs": "table density at and above 915 K (unused by the fixed reference density)",
       "value": 2415.0
      },
      {
       "locator": "row 'Heat capacity (liquid) C_pl': 0.486T+725, T < 915 K",
       "quantity": "heat capacity, solid branch",
       "table": "Supplementary Table 1, printed p. 20, Al6061 column",
       "unit": "J/(kg K)",
       "usedAs": "cp below 915 K",
       "value": "0.486T+725"
      },
      {
       "locator": "row 'Heat capacity (liquid) C_pl': 1170, T >= 915 K",
       "quantity": "heat capacity, liquid branch",
       "table": "Supplementary Table 1, printed p. 20, Al6061 column",
       "unit": "J/(kg K)",
       "usedAs": "cp at and above 915 K, also above 2792 K to maxTemperature_K",
       "value": 1170.0
      },
      {
       "locator": "row 'Thermal conductivity (liquid) k_l': 0.091T+152.5, T < 915 K",
       "quantity": "thermal conductivity, solid branch",
       "table": "Supplementary Table 1, printed p. 20, Al6061 column",
       "unit": "W/(m K)",
       "usedAs": "k below 915 K",
       "value": "0.091T+152.5"
      },
      {
       "locator": "row 'Thermal conductivity (liquid) k_l': 90, T >= 915 K",
       "quantity": "thermal conductivity, liquid branch",
       "table": "Supplementary Table 1, printed p. 20, Al6061 column",
       "unit": "W/(m K)",
       "usedAs": "k at and above 915 K",
       "value": 90.0
      },
      {
       "locator": "row 'Solidus temperature T_s'",
       "quantity": "solidus temperature",
       "table": "Supplementary Table 1, printed p. 20, Al6061 column",
       "unit": "K",
       "usedAs": "start of latent release",
       "value": 873.0
      },
      {
       "locator": "row 'Liquidus temperature T_l'",
       "quantity": "liquidus temperature",
       "table": "Supplementary Table 1, printed p. 20, Al6061 column",
       "unit": "K",
       "usedAs": "end of latent release; melt isotherm",
       "value": 915.0
      },
      {
       "locator": "row 'Latent heat of melting L_m': 3.8x10^5",
       "quantity": "latent heat of melting",
       "table": "Supplementary Table 1, printed p. 20, Al6061 column",
       "unit": "J/kg",
       "usedAs": "latent heat spread linearly over solidus to liquidus",
       "value": 380000.0
      },
      {
       "locator": "row 'Vaporization point T_v'",
       "quantity": "vaporization point",
       "table": "Supplementary Table 1, printed p. 20, Al6061 column",
       "unit": "K",
       "usedAs": "Clausius-Clapeyron reference temperature; table boiling endpoint",
       "value": 2792.0
      },
      {
       "locator": "row 'Latent heat of vaporization L_v': 1.053x10^7",
       "quantity": "latent heat of vaporization",
       "table": "Supplementary Table 1, printed p. 20, Al6061 column",
       "unit": "J/kg",
       "usedAs": "Clausius-Clapeyron slope and evaporative heat flux j*L_v",
       "value": 10530000.0
      },
      {
       "locator": "row 'Molar mass M_l': 27 g/mol",
       "quantity": "molar mass",
       "table": "Supplementary Table 1, printed p. 20, Al6061 column",
       "unit": "kg/mol",
       "usedAs": "vapor law",
       "value": 0.027
      },
      {
       "locator": "row 'Surface tension sigma'",
       "quantity": "surface tension",
       "table": "Supplementary Table 1, printed p. 20, Al6061 column",
       "unit": "N/m",
       "usedAs": "default scalar for the recoil/capillary gate 2*sigma/r",
       "value": 0.91
      },
      {
       "locator": "row 'Thermocapillary coefficient d sigma/dT'",
       "quantity": "thermocapillary coefficient",
       "table": "Supplementary Table 1, printed p. 20, Al6061 column",
       "unit": "N/(m K)",
       "usedAs": "recorded in the material (dGamma_dT); the gate uses the scalar sigma, as in the Ti64 model",
       "value": -0.00035
      },
      {
       "locator": "row 'Emissivity epsilon'",
       "quantity": "emissivity",
       "table": "Supplementary Table 1, printed p. 20, Al6061 column",
       "unit": "-",
       "usedAs": "top-face radiation",
       "value": 0.1
      },
      {
       "locator": "row 'Dynamic viscosity mu_l'",
       "quantity": "dynamic viscosity",
       "table": "Supplementary Table 1, printed p. 20, Al6061 column",
       "unit": "Pa s",
       "usedAs": "table viscosity column only; not used by this conduction solver",
       "value": 0.001
      },
      {
       "locator": "row 'Low vaporization threshold T_L'",
       "quantity": "low vaporization threshold",
       "table": "Supplementary Table 2, printed p. 21, 'Vaporization constants of Al6061' block",
       "unit": "K",
       "usedAs": "default declared transitionLow_K (start of the Hermite bridge)",
       "value": 2800.0
      },
      {
       "locator": "row 'High vaporization threshold T_L'",
       "quantity": "high vaporization threshold",
       "table": "Supplementary Table 2, printed p. 21, 'Vaporization constants of Al6061' block",
       "unit": "K",
       "usedAs": "default declared transitionHigh_K (closed-form law at and above)",
       "value": 3200.0
      },
      {
       "locator": "row 'Retro-diffusion coefficient beta_R'",
       "quantity": "retro-diffusion coefficient",
       "table": "Supplementary Table 2, printed p. 21, computational constants",
       "unit": "-",
       "usedAs": "default declared returnFraction",
       "value": 0.18
      }
     ],
     "disclosure": "Thermal and vapour constants are Al6061 values (Gan 2021 SI Tables 1-2, citing Valencia and Quested 2013) used as an Al-rich proxy for AlSi10Mg; Mg and Si selective evaporation and the real AlSi10Mg composition are not modelled.",
     "gasConstant_J_molK": 8.31446261815324,
     "latentHeat_J_kg": 10530000.0,
     "maxTemperatureLimit_K": 6000.0,
     "molarMass_kg_mol": 0.027,
     "phaseStepRegularization": "Gan's solid/liquid property step at 915 K is carried by a declared 1 K linear ramp below it; numerical table regularization",
     "primarySourceCitedByGan": "Valencia and Quested 2013, ASM Handbook Vol. 22B, 'Thermophysical properties' (Gan SI ref. 13)",
     "proxyAlloy": "Al6061",
     "recordedUnusedTable2": {
      "ablationRateConstants_a1_b1": [
       -1.78408e-06,
       0.0166819
      ],
      "ablationRateConstants_c1_d1": [
       -51.4573,
       52458.2
      ],
      "locator": "Supplementary Table 2, printed p. 21, 'Vaporization constants of Al6061' block",
      "status": "recorded only; the polynomial forms are not evaluated (declared Hermite bridge, following the Ti64 model)",
      "surfacePressureConstants_a2_b2": [
       0.000206397,
       -0.683622
      ],
      "surfacePressureConstants_c2_d2": [
       -1026.17,
       3802050.0
      ]
     },
     "referencePressureBasis": "declared convention (normal boiling point at 1 atm), as in the Ti64 model",
     "referencePressure_Pa": 101325.0,
     "source": "Gan et al. 2021, Nat Commun 12, 2379, Supplementary Information (papers/gan2021_SI.pdf)",
     "sourceId": "Gan2021-SI-Tables1-2-Al6061-proxy-for-AlSi10Mg",
     "species": "Al (single effective species; Al6061 proxy; no Mg/Si selective evaporation, no composition evolution)",
     "targetAlloy": "AlSi10Mg",
     "temperatureLimitBasis": "computational scenario limit; not a source validity range",
     "transitionBasis": "declared cubic Hermite matching following Gan Eqs 12/14; not recovered fitting coefficients",
     "vaporizationTemperature_K": 2792.0
    },
    "thermalContinuation": {
     "method": "constant-liquid-branch-of-source",
     "starts_K": 2792.0,
     "ends_K": 5000.0,
     "endpointDensity_kg_m3": 2415.0,
     "endpointConductivity_W_mK": 90.0,
     "endpointCp_J_kgK": 1170.0,
     "densityMethod": "fixed reference density at preheat for volumetric enthalpy",
     "status": "Gan Table 1 liquid laws are constant for T >= 915 K with no stated upper bound; held above 2792 K as a declared assumption, not a source validity extension"
    },
    "proxyNote": "Single Al6061 proxy profile: thermal table, boiling endpoint and vapor law share one source",
    "runtime_s": 1.0159999999887077,
    "executionRuntime": {
     "executable": "C:\\Users\\can02\\AppData\\Local\\Programs\\Python\\Python312\\python.exe",
     "python": "3.12.10",
     "platform": "Windows-11-10.0.26300-SP0",
     "numpy": "2.5.3"
    }
   },
   "acceptedStepCount": 1173,
   "acceptedTime_s": 0.0005769230769230769,
   "timesteps": {
    "minimum_s": 9.5507548959679e-08,
    "maximum_s": 6.458669343733752e-07,
    "rejectedCandidates": 0,
    "sourceRetries": 434
   },
   "energy": {
    "input_J": 0.004153846153846148,
    "base_J": 0.0024174128628542484,
    "radiativeConvective_J": 1.0772947436474412e-07,
    "evaporative_J": 0.0,
    "stored_J": 0.0017363255615175327,
    "residual_J": 1.951563910473908e-18,
    "relativeResidual": 4.698209414103859e-16
   },
   "diagnosticEmittedMass_kg": 0.0,
   "diagnosticMassLabel": "Integrated Al-species (Al6061 proxy) emitted mass diagnostic; not ablation or material removal",
   "peakTemperature_K": 1941.8054692659427,
   "temperatureLabel": "Conditional fixed-surface temperature estimate",
   "geometry": {
    "time_s": 7.130512263310504e-05,
    "width_um": 80.0,
    "depth_um": 40.0,
    "length_um": 99.99999999999996,
    "volume_um3": 175999.99999999997,
    "truncated": false,
    "basis": "instantaneous liquidus extent at peak-melt-volume snapshot; cell bounds",
    "label": "Uncalibrated fixed-surface isotherm estimate",
    "widthLabel": "Conditional fixed-surface liquidus width estimate",
    "widthWarning": null,
    "refusalReason": null,
    "liquidus_K": 915.0,
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
    "Thermal and vapour constants are Al6061 values (Gan 2021 SI Tables 1-2, citing Valencia and Quested 2013) used as an Al-rich proxy for AlSi10Mg; Mg and Si selective evaporation and the real AlSi10Mg composition are not modelled.",
    "Uncalibrated estimate of temperature and liquidus isotherm geometry for AlSi10Mg from the stated transient model on an Al6061 proxy profile. Uncertainty is unknown and may be large. Calibrate to your machine for better accuracy.",
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
    "minimumFinalTemperature_K": 354.3663247263506,
    "maximumFinalTemperature_K": 376.5325543350135,
    "minimumSourceCapture": 0.9999999990197679
   },
   "jobType": "alsi10mg-evaporative-surface",
   "settings": {
    "jobType": "alsi10mg-evaporative-surface",
    "config": {
     "power_W": 180.0,
     "speed_mm_s": 1300.0,
     "beamDiameter_um": 100.0,
     "preheat_C": 80.0,
     "mesh_um": 20.0,
     "maxDt_s": 1e-06,
     "trackLength_um": 100.0,
     "cooling_s": 0.0005,
     "sourcePenetration_um": 20.0,
     "convection_W_m2K": 20.0,
     "material": "AlSi10Mg",
     "backend": "reference",
     "surfaceMode": "bare-plate",
     "mode": "standard",
     "layers": 1,
     "tracks": 1,
     "study": "none",
     "evaporation": {
      "transitionLow_K": 2800.0,
      "transitionHigh_K": 3200.0,
      "ambientPressure_Pa": 101325.0,
      "returnFraction": 0.18,
      "maxTemperature_K": 5000.0,
      "surfaceTension_N_m": 0.91
     }
    }
   }
  }
 }
};
