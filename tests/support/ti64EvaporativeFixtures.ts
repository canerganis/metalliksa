// Real outputs, pinned 2026-10-20 (A2/A3 lane ti64std). W1: python/lpbf_worker Queue job (ti64-evaporative-surface, 100 um track,
// 1000 mm/s, 80 um, 80 C, 150 W and 30 W) via get(). P8: python/lpbf_research_models.run (sender batch-client, Ti-6Al-4V, IR_1064nm,
// 80 um, 80 C; 150 W/1000, 30 W/1000, 150 W/10 mm/s), reduced to the meltDepthLink and keyholeCavity members this UI reads.
/* eslint-disable */
export const fixtures: any = {
 "w1Onset": {
  "id": "d59c442a771c43c6a784afb8620af96e",
  "status": "completed",
  "progress": 1.0,
  "log": "{\"progress\": 0.012707836410116564, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.027405162915285133, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.044586277367317295, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.06305461943202266, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.08269291947131527, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.10218505487784747, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.12227571456974286, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.1427900566498783, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.16232506823594545, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.18727020580296075, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.2634167832148905, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.4057423428395402, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.5724090095062109, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.7390756761728816, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.9057423428395522, \"message\": \"Evaporative surface solve\"}\n",
  "error": null,
  "requestSummary": {
   "jobType": "ti64-evaporative-surface",
   "config": {
    "power_W": 150.0,
    "speed_mm_s": 1000.0,
    "beamDiameter_um": 80.0,
    "preheat_C": 80.0,
    "mesh_um": 20.0,
    "maxDt_s": 1e-06,
    "trackLength_um": 100.0,
    "cooling_s": 0.0005,
    "sourcePenetration_um": 20.0,
    "convection_W_m2K": 20.0,
    "material": "Ti-6Al-4V",
    "backend": "reference",
    "surfaceMode": "bare-plate",
    "mode": "standard",
    "layers": 1,
    "tracks": 1,
    "study": "none",
    "evaporation": {
     "transitionLow_K": 3560.0,
     "transitionHigh_K": 4000.0,
     "ambientPressure_Pa": 101325.0,
     "returnFraction": 0.2,
     "maxTemperature_K": 5000.0,
     "surfaceTension_N_m": 1.65
    }
   }
  },
  "result": {
   "schema": "lpbf-ti64-evaporative-result-v1",
   "modelId": "ti64-fixed-surface-evaporation-v1",
   "status": "completed",
   "experimentalValidation": false,
   "productionReady": false,
   "tier": "Uncalibrated estimate",
   "provenance": {
    "implementationHash": "b9358627276417c1ab8672cfd508d826659f601b43c6a534dd1cff975e49009e",
    "implementationFingerprintSchema": "ti64-evaporative-dependency-closure-v1",
    "defaultImplementationHash": "13203cac19bf69db80b546c6e67ed846a0941e35ea4ad62e53a786de073c46ca",
    "moduleSha256": {
     "lpbf_ti64_evaporative_solver.py": "a821a5a21cc821f7864ece8131f5c4af644f3973957dca9a3674ae5427143b9f",
     "lpbf_ti64_evaporation.py": "eb7a529c47a49910cb36673f32170f6711d89af43e95a7a1dc9f85338cf98733"
    },
    "requestSha256": "e9cb702f8347ba92407be94d26ff5aa9931034cc5166b777d4ddbc27a7ff5b89",
    "inputs": {
     "power_W": 150.0,
     "speed_mm_s": 1000.0,
     "beamDiameter_um": 80.0,
     "preheat_C": 80.0,
     "mesh_um": 20.0,
     "maxDt_s": 1e-06,
     "trackLength_um": 100.0,
     "cooling_s": 0.0005,
     "sourcePenetration_um": 20.0,
     "convection_W_m2K": 20.0,
     "material": "Ti-6Al-4V",
     "backend": "reference",
     "surfaceMode": "bare-plate",
     "mode": "standard",
     "layers": 1,
     "tracks": 1,
     "study": "none",
     "evaporation": {
      "transitionLow_K": 3560.0,
      "transitionHigh_K": 4000.0,
      "ambientPressure_Pa": 101325.0,
      "returnFraction": 0.2,
      "maxTemperature_K": 5000.0,
      "surfaceTension_N_m": 1.65
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
     "solidus_K": 1877.15,
     "liquidus_K": 1933.15,
     "boiling_K": 3560.15,
     "latentHeat_J_kg": 290000.0,
     "absorptivity": 0.32,
     "emissivity": 0.35,
     "dGamma_dT": -0.00028,
     "source": "Existing four_alloy_materials.py / lpbf_thermal_solver.py; endpoint provenance not independently verified",
     "quality": "estimated",
     "table": [
      [
       273.15,
       4430.0,
       6.7,
       526.0,
       0.0042
      ],
      [
       1933.15,
       4087.0,
       29.8,
       930.0,
       0.0042
      ],
      [
       3560.15,
       4087.0,
       29.8,
       930.0,
       0.0042
      ]
     ],
     "name": "Ti-6Al-4V",
     "version": "lpbf-materials-1",
     "temperatureCoverage_K": [
      273.15,
      3560.15
     ],
     "uncertaintyNote": "Property uncertainties not quantified; source string does not establish validation.",
     "materialId": "ti6al4v",
     "provenanceClass": "estimated-legacy",
     "materialIdentitySchemaVersion": 1,
     "endpointAdmission": {
      "record": {
       "id": "ti6al4v",
       "decision": "admit-nominal-research-convention",
       "sourceId": "SOLT-GAN-TI",
       "sourceCheck": "SOLT-GAN-TI-PAIR",
       "original": {
        "values": [
         1877,
         1933
        ],
        "unit": "K"
       },
       "endpoint_K": [
        1877.15,
        1933.15
       ],
       "baseline_C": [
        1604,
        1660
       ],
       "delta_K": [
        0,
        0
       ],
       "admissionClass": "fixed-front-literature-model",
       "chemistryMatch": "not-established",
       "uncertainty": {
        "type": "not-quantified",
        "coverage": "No statistical coverage; unknown model, rate, chemistry/state-transfer biases"
       },
       "scope": "Named nominal-alloy fixed-front research approximation only; complete request chemistry/state retained. Explicit per-quantity convention/transfer disclosure required. No arbitrary composition inheritance. USER-VISIBLE LABEL: Cezairliyan reports solidus 1942.6 K with estimated total inaccuracy 8 K (coverage unspecified), 9.45 K above this convention liquidus 1933.15 K; unresolved batch/observable/rate/temperature-scale contradiction.",
       "refusedScope": "Measured or assessed exact-specimen endpoints; automatic user-composition admission; physical validation; restoration of local SOL-A1 quantities before SOL-C",
       "sourceChemistry": "Named Ti64 only; batch assay and state unknown; Fe/O not silently removed",
       "solidusDefinition": "Source-model solidus isotherm; unknown; no measured endpoint criterion published for this model input",
       "liquidusDefinition": "Source-model liquidus isotherm; unknown; no measured endpoint criterion published for this model input",
       "method": "Gan2021 compiled thermal-model prescription; upstream numeric lineage unresolved",
       "rate": "not applicable to adopted model; upstream measurement rate unknown",
       "cycle": "not applicable to adopted model; upstream experimental cycle unknown",
       "direction": "not applicable to adopted model; upstream direction unknown",
       "pairingStatus": "same source model/table; no same-cycle measurement claim",
       "transfer": "Gan nominal Ti64 convention to nominal Ti64 screening; exact chemistry match not established; Cezairliyan solidus contradiction unresolved; integer-273 conversion interpretation disclosed, not a verified upstream Celsius pair",
       "parentIdentity": {
        "recordId": "SOL-T-A4-ti6al4v",
        "endpoint_K": [
         1877.15,
         1933.15
        ],
        "sourceSha256": "22a8d2dc870bbd83f6bd3330899437911733f9335d52758d95a328bd6993d6e5",
        "requiredRuntimeBindings": [
         "complete original and solved chemistry with units",
         "material state",
         "source locator and transfer scope",
         "field/model/solver revision and full process vector",
         "threshold-dependent property convention and numerical settings",
         "admission-record canonical hash"
        ],
        "conversion": {
         "rule": "compiled-K-integer-273-interpretation",
         "offset_K": 0.15,
         "interpreted_C": [
          1604,
          1660
         ],
         "sameLineageKChecks": [],
         "interpretation": "Inferred Celsius pair from the cross-checkable IN718, SS316 and IN625 integer-273 pattern; Ti64 upstream Celsius row not read. Original Gan K text retained; no physical accuracy claim."
        }
       },
       "conversion": {
        "rule": "compiled-K-integer-273-interpretation",
        "offset_K": 0.15,
        "interpreted_C": [
         1604,
         1660
        ],
        "sameLineageKChecks": [],
        "interpretation": "Inferred Celsius pair from the cross-checkable IN718, SS316 and IN625 integer-273 pattern; Ti64 upstream Celsius row not read. Original Gan K text retained; no physical accuracy claim."
       }
      },
      "recordSha256": "25953a4a59c06e25e049aa1ee6291d51aef46bcdae16f3586940cf841e3e5840",
      "sourceLocator": "Gan2021 SI PDF20 Supplementary Table1 Ti64; integer-273 interpretation",
      "scope": "Named nominal-alloy fixed-front research approximation only; complete request chemistry/state retained. Explicit per-quantity convention/transfer disclosure required. No arbitrary composition inheritance. USER-VISIBLE LABEL: Cezairliyan reports solidus 1942.6 K with estimated total inaccuracy 8 K (coverage unspecified), 9.45 K above this convention liquidus 1933.15 K; unresolved batch/observable/rate/temperature-scale contradiction. Gan nominal Ti64 convention to nominal Ti64 screening; exact chemistry match not established; Cezairliyan solidus contradiction unresolved; integer-273 conversion interpretation disclosed, not a verified upstream Celsius pair",
      "sourceEvidenceKind": "Literature estimate",
      "kind": "modelConvention",
      "status": "admitted-convention"
     },
     "materialAuthority": "four_alloy_materials.py",
     "materialAuthorityRevisionSha256": "d26c4b0318380615fbe89d482100083a5d2ad8193e03640149b0bc2f1770ff12",
     "materialRevisionSha256": "8052bde35739e4b670c0d2eabd09caa402ce23a36a63aed848e2bc092c206a0d"
    },
    "vaporSource": {
     "sourceId": "Gan2021-SI-Table1-Ti",
     "species": "Ti (nominal Ti64 scenario; no composition evolution)",
     "vaporizationTemperature_K": 3560.0,
     "latentHeat_J_kg": 9255000.0,
     "molarMass_kg_mol": 0.048,
     "gasConstant_J_molK": 8.31446261815324,
     "referencePressure_Pa": 101325.0,
     "referencePressureBasis": "declared convention",
     "transitionBasis": "declared cubic Hermite matching following Gan Eqs 12/14; not recovered fitting coefficients",
     "maxTemperatureLimit_K": 6000.0,
     "temperatureLimitBasis": "computational scenario limit; not a source validity range",
     "surfaceTensionBasis": "optional caller-declared scalar assumption; no default"
    },
    "thermalContinuation": {
     "method": "constant-liquid-endpoint-properties",
     "starts_K": 3560.15,
     "ends_K": 5000.0,
     "endpointDensity_kg_m3": 4087.0,
     "endpointConductivity_W_mK": 29.8,
     "endpointCp_J_kgK": 930.0,
     "densityMethod": "fixed reference density at preheat for volumetric enthalpy",
     "status": "declared model assumption, not new data or source validity extension"
    },
    "mixedSourceNote": "Registry Ti64 boiling endpoint 3560.15 K retained; independent Gan Ti vapor reference 3560 K; no reconciliation or Ti64 species evolution",
    "runtime_s": 1.4690000000009604,
    "executionRuntime": {
     "executable": "C:\\Users\\can02\\Projects\\metalliksaa\\Metalliksa-1\\.runtime\\lpbf-win-py312\\Scripts\\python.exe",
     "python": "3.12.10",
     "platform": "Windows-11-10.0.26300-SP0",
     "numpy": "2.2.6"
    }
   },
   "acceptedStepCount": 1557,
   "acceptedTime_s": 0.0006000000000000001,
   "timesteps": {
    "minimum_s": 7.280073128840463e-08,
    "maximum_s": 1e-06,
    "rejectedCandidates": 0,
    "sourceRetries": 1173
   },
   "energy": {
    "input_J": 0.004800000000000001,
    "base_J": 6.635745409494616e-08,
    "radiativeConvective_J": 2.2672890852684565e-06,
    "evaporative_J": 0.00029174152651392906,
    "stored_J": 0.004505924826946702,
    "residual_J": 6.938893903907228e-18,
    "relativeResidual": 1.445602896647339e-15
   },
   "diagnosticEmittedMass_kg": 3.152258525272055e-11,
   "diagnosticMassLabel": "Integrated Ti-species emitted mass diagnostic; not ablation or material removal",
   "peakTemperature_K": 4467.799246181222,
   "temperatureLabel": "Conditional fixed-surface temperature estimate",
   "geometry": {
    "time_s": 9.287587985979773e-05,
    "width_um": 99.99999999999999,
    "depth_um": null,
    "length_um": null,
    "volume_um3": null,
    "truncated": false,
    "basis": "instantaneous liquidus extent at peak-melt-volume snapshot; cell bounds",
    "label": "Uncalibrated fixed-surface isotherm estimate",
    "widthLabel": "Conditional fixed-surface liquidus width estimate",
    "widthWarning": "The surface would deform into a vapor cavity. This width is a fixed-surface isotherm scenario and may not represent the melt pool.",
    "refusalReason": "The surface would deform into a vapor cavity at these settings. A fixed-surface model cannot give melt depth here. Use a model with surface motion and melt flow for depth, length and volume.",
    "liquidus_K": 1933.15,
    "cellResolution_um": 20.0
   },
   "gate": {
    "onset": true,
    "unresolvedGeometry": false,
    "firstOnsetTime_s": 2.828203229233529e-05,
    "firstUnresolvedTime_s": null,
    "geometryAvailable": false
   },
   "warnings": [
    "Uncalibrated estimate of temperature and liquidus isotherm geometry for Ti-6Al-4V from the stated transient model. Uncertainty is unknown and may be large. Calibrate to your machine for better accuracy.",
    "The surface is held fixed. Evaporation removes energy, but melt flow, surface recession and changes in alloy composition are not resolved.",
    "This is the liquidus isotherm envelope of the selected temperature model. The envelope uses the reported instantaneous peak-melt-volume snapshot.",
    "Active evaporation is present. Surface recession, expelled liquid, plume shielding, convective redistribution and advective redistribution are not resolved.",
    "The surface would deform into a vapor cavity. This width is a fixed-surface isotherm scenario and may not represent the melt pool.",
    "The surface would deform into a vapor cavity at these settings. A fixed-surface model cannot give melt depth here. Use a model with surface motion and melt flow for depth, length and volume."
   ],
   "fieldSummary": {
    "shape": [
     17,
     17,
     15
    ],
    "dx_m": 1.9999999999999998e-05,
    "minimumFinalTemperature_K": 353.15019080052036,
    "maximumFinalTemperature_K": 825.982552887902,
    "minimumSourceCapture": 0.9999999990180777
   },
   "jobType": "ti64-evaporative-surface",
   "settings": {
    "jobType": "ti64-evaporative-surface",
    "config": {
     "power_W": 150.0,
     "speed_mm_s": 1000.0,
     "beamDiameter_um": 80.0,
     "preheat_C": 80.0,
     "mesh_um": 20.0,
     "maxDt_s": 1e-06,
     "trackLength_um": 100.0,
     "cooling_s": 0.0005,
     "sourcePenetration_um": 20.0,
     "convection_W_m2K": 20.0,
     "material": "Ti-6Al-4V",
     "backend": "reference",
     "surfaceMode": "bare-plate",
     "mode": "standard",
     "layers": 1,
     "tracks": 1,
     "study": "none",
     "evaporation": {
      "transitionLow_K": 3560.0,
      "transitionHigh_K": 4000.0,
      "ambientPressure_Pa": 101325.0,
      "returnFraction": 0.2,
      "maxTemperature_K": 5000.0,
      "surfaceTension_N_m": 1.65
     }
    }
   }
  }
 },
 "w1BelowOnset": {
  "id": "c2a5f8d3fdec4e3993e9a3df96087f4b",
  "status": "completed",
  "progress": 1.0,
  "log": "{\"progress\": 0.07940633003375229, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.16934888401854742, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.3279127774929964, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.494579444159665, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.6612461108263357, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.8279127774930063, \"message\": \"Evaporative surface solve\"}\n{\"progress\": 0.95, \"message\": \"Evaporative surface solve\"}\n",
  "error": null,
  "requestSummary": {
   "jobType": "ti64-evaporative-surface",
   "config": {
    "power_W": 30.0,
    "speed_mm_s": 1000.0,
    "beamDiameter_um": 80.0,
    "preheat_C": 80.0,
    "mesh_um": 20.0,
    "maxDt_s": 1e-06,
    "trackLength_um": 100.0,
    "cooling_s": 0.0005,
    "sourcePenetration_um": 20.0,
    "convection_W_m2K": 20.0,
    "material": "Ti-6Al-4V",
    "backend": "reference",
    "surfaceMode": "bare-plate",
    "mode": "standard",
    "layers": 1,
    "tracks": 1,
    "study": "none",
    "evaporation": {
     "transitionLow_K": 3560.0,
     "transitionHigh_K": 4000.0,
     "ambientPressure_Pa": 101325.0,
     "returnFraction": 0.2,
     "maxTemperature_K": 5000.0,
     "surfaceTension_N_m": 1.65
    }
   }
  },
  "result": {
   "schema": "lpbf-ti64-evaporative-result-v1",
   "modelId": "ti64-fixed-surface-evaporation-v1",
   "status": "completed",
   "experimentalValidation": false,
   "productionReady": false,
   "tier": "Uncalibrated estimate",
   "provenance": {
    "implementationHash": "b9358627276417c1ab8672cfd508d826659f601b43c6a534dd1cff975e49009e",
    "implementationFingerprintSchema": "ti64-evaporative-dependency-closure-v1",
    "defaultImplementationHash": "13203cac19bf69db80b546c6e67ed846a0941e35ea4ad62e53a786de073c46ca",
    "moduleSha256": {
     "lpbf_ti64_evaporative_solver.py": "a821a5a21cc821f7864ece8131f5c4af644f3973957dca9a3674ae5427143b9f",
     "lpbf_ti64_evaporation.py": "eb7a529c47a49910cb36673f32170f6711d89af43e95a7a1dc9f85338cf98733"
    },
    "requestSha256": "0054ac21f0a81c8f366c2177dda2ea280411712a5e6011a4e9453a28e621f894",
    "inputs": {
     "power_W": 30.0,
     "speed_mm_s": 1000.0,
     "beamDiameter_um": 80.0,
     "preheat_C": 80.0,
     "mesh_um": 20.0,
     "maxDt_s": 1e-06,
     "trackLength_um": 100.0,
     "cooling_s": 0.0005,
     "sourcePenetration_um": 20.0,
     "convection_W_m2K": 20.0,
     "material": "Ti-6Al-4V",
     "backend": "reference",
     "surfaceMode": "bare-plate",
     "mode": "standard",
     "layers": 1,
     "tracks": 1,
     "study": "none",
     "evaporation": {
      "transitionLow_K": 3560.0,
      "transitionHigh_K": 4000.0,
      "ambientPressure_Pa": 101325.0,
      "returnFraction": 0.2,
      "maxTemperature_K": 5000.0,
      "surfaceTension_N_m": 1.65
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
     "solidus_K": 1877.15,
     "liquidus_K": 1933.15,
     "boiling_K": 3560.15,
     "latentHeat_J_kg": 290000.0,
     "absorptivity": 0.32,
     "emissivity": 0.35,
     "dGamma_dT": -0.00028,
     "source": "Existing four_alloy_materials.py / lpbf_thermal_solver.py; endpoint provenance not independently verified",
     "quality": "estimated",
     "table": [
      [
       273.15,
       4430.0,
       6.7,
       526.0,
       0.0042
      ],
      [
       1933.15,
       4087.0,
       29.8,
       930.0,
       0.0042
      ],
      [
       3560.15,
       4087.0,
       29.8,
       930.0,
       0.0042
      ]
     ],
     "name": "Ti-6Al-4V",
     "version": "lpbf-materials-1",
     "temperatureCoverage_K": [
      273.15,
      3560.15
     ],
     "uncertaintyNote": "Property uncertainties not quantified; source string does not establish validation.",
     "materialId": "ti6al4v",
     "provenanceClass": "estimated-legacy",
     "materialIdentitySchemaVersion": 1,
     "endpointAdmission": {
      "record": {
       "id": "ti6al4v",
       "decision": "admit-nominal-research-convention",
       "sourceId": "SOLT-GAN-TI",
       "sourceCheck": "SOLT-GAN-TI-PAIR",
       "original": {
        "values": [
         1877,
         1933
        ],
        "unit": "K"
       },
       "endpoint_K": [
        1877.15,
        1933.15
       ],
       "baseline_C": [
        1604,
        1660
       ],
       "delta_K": [
        0,
        0
       ],
       "admissionClass": "fixed-front-literature-model",
       "chemistryMatch": "not-established",
       "uncertainty": {
        "type": "not-quantified",
        "coverage": "No statistical coverage; unknown model, rate, chemistry/state-transfer biases"
       },
       "scope": "Named nominal-alloy fixed-front research approximation only; complete request chemistry/state retained. Explicit per-quantity convention/transfer disclosure required. No arbitrary composition inheritance. USER-VISIBLE LABEL: Cezairliyan reports solidus 1942.6 K with estimated total inaccuracy 8 K (coverage unspecified), 9.45 K above this convention liquidus 1933.15 K; unresolved batch/observable/rate/temperature-scale contradiction.",
       "refusedScope": "Measured or assessed exact-specimen endpoints; automatic user-composition admission; physical validation; restoration of local SOL-A1 quantities before SOL-C",
       "sourceChemistry": "Named Ti64 only; batch assay and state unknown; Fe/O not silently removed",
       "solidusDefinition": "Source-model solidus isotherm; unknown; no measured endpoint criterion published for this model input",
       "liquidusDefinition": "Source-model liquidus isotherm; unknown; no measured endpoint criterion published for this model input",
       "method": "Gan2021 compiled thermal-model prescription; upstream numeric lineage unresolved",
       "rate": "not applicable to adopted model; upstream measurement rate unknown",
       "cycle": "not applicable to adopted model; upstream experimental cycle unknown",
       "direction": "not applicable to adopted model; upstream direction unknown",
       "pairingStatus": "same source model/table; no same-cycle measurement claim",
       "transfer": "Gan nominal Ti64 convention to nominal Ti64 screening; exact chemistry match not established; Cezairliyan solidus contradiction unresolved; integer-273 conversion interpretation disclosed, not a verified upstream Celsius pair",
       "parentIdentity": {
        "recordId": "SOL-T-A4-ti6al4v",
        "endpoint_K": [
         1877.15,
         1933.15
        ],
        "sourceSha256": "22a8d2dc870bbd83f6bd3330899437911733f9335d52758d95a328bd6993d6e5",
        "requiredRuntimeBindings": [
         "complete original and solved chemistry with units",
         "material state",
         "source locator and transfer scope",
         "field/model/solver revision and full process vector",
         "threshold-dependent property convention and numerical settings",
         "admission-record canonical hash"
        ],
        "conversion": {
         "rule": "compiled-K-integer-273-interpretation",
         "offset_K": 0.15,
         "interpreted_C": [
          1604,
          1660
         ],
         "sameLineageKChecks": [],
         "interpretation": "Inferred Celsius pair from the cross-checkable IN718, SS316 and IN625 integer-273 pattern; Ti64 upstream Celsius row not read. Original Gan K text retained; no physical accuracy claim."
        }
       },
       "conversion": {
        "rule": "compiled-K-integer-273-interpretation",
        "offset_K": 0.15,
        "interpreted_C": [
         1604,
         1660
        ],
        "sameLineageKChecks": [],
        "interpretation": "Inferred Celsius pair from the cross-checkable IN718, SS316 and IN625 integer-273 pattern; Ti64 upstream Celsius row not read. Original Gan K text retained; no physical accuracy claim."
       }
      },
      "recordSha256": "25953a4a59c06e25e049aa1ee6291d51aef46bcdae16f3586940cf841e3e5840",
      "sourceLocator": "Gan2021 SI PDF20 Supplementary Table1 Ti64; integer-273 interpretation",
      "scope": "Named nominal-alloy fixed-front research approximation only; complete request chemistry/state retained. Explicit per-quantity convention/transfer disclosure required. No arbitrary composition inheritance. USER-VISIBLE LABEL: Cezairliyan reports solidus 1942.6 K with estimated total inaccuracy 8 K (coverage unspecified), 9.45 K above this convention liquidus 1933.15 K; unresolved batch/observable/rate/temperature-scale contradiction. Gan nominal Ti64 convention to nominal Ti64 screening; exact chemistry match not established; Cezairliyan solidus contradiction unresolved; integer-273 conversion interpretation disclosed, not a verified upstream Celsius pair",
      "sourceEvidenceKind": "Literature estimate",
      "kind": "modelConvention",
      "status": "admitted-convention"
     },
     "materialAuthority": "four_alloy_materials.py",
     "materialAuthorityRevisionSha256": "d26c4b0318380615fbe89d482100083a5d2ad8193e03640149b0bc2f1770ff12",
     "materialRevisionSha256": "8052bde35739e4b670c0d2eabd09caa402ce23a36a63aed848e2bc092c206a0d"
    },
    "vaporSource": {
     "sourceId": "Gan2021-SI-Table1-Ti",
     "species": "Ti (nominal Ti64 scenario; no composition evolution)",
     "vaporizationTemperature_K": 3560.0,
     "latentHeat_J_kg": 9255000.0,
     "molarMass_kg_mol": 0.048,
     "gasConstant_J_molK": 8.31446261815324,
     "referencePressure_Pa": 101325.0,
     "referencePressureBasis": "declared convention",
     "transitionBasis": "declared cubic Hermite matching following Gan Eqs 12/14; not recovered fitting coefficients",
     "maxTemperatureLimit_K": 6000.0,
     "temperatureLimitBasis": "computational scenario limit; not a source validity range",
     "surfaceTensionBasis": "optional caller-declared scalar assumption; no default"
    },
    "thermalContinuation": {
     "method": "constant-liquid-endpoint-properties",
     "starts_K": 3560.15,
     "ends_K": 5000.0,
     "endpointDensity_kg_m3": 4087.0,
     "endpointConductivity_W_mK": 29.8,
     "endpointCp_J_kgK": 930.0,
     "densityMethod": "fixed reference density at preheat for volumetric enthalpy",
     "status": "declared model assumption, not new data or source validity extension"
    },
    "mixedSourceNote": "Registry Ti64 boiling endpoint 3560.15 K retained; independent Gan Ti vapor reference 3560 K; no reconciliation or Ti64 species evolution",
    "runtime_s": 0.5310000000008586,
    "executionRuntime": {
     "executable": "C:\\Users\\can02\\Projects\\metalliksaa\\Metalliksa-1\\.runtime\\lpbf-win-py312\\Scripts\\python.exe",
     "python": "3.12.10",
     "platform": "Windows-11-10.0.26300-SP0",
     "numpy": "2.2.6"
    }
   },
   "acceptedStepCount": 704,
   "acceptedTime_s": 0.0006000000000000001,
   "timesteps": {
    "minimum_s": 2.523335041937271e-07,
    "maximum_s": 1e-06,
    "rejectedCandidates": 0,
    "sourceRetries": 217
   },
   "energy": {
    "input_J": 0.0009599999999999997,
    "base_J": 9.338547560158971e-09,
    "radiativeConvective_J": 1.4258362878273635e-07,
    "evaporative_J": 0.0,
    "stored_J": 0.0009598480778236568,
    "residual_J": 0.0,
    "relativeResidual": 0.0
   },
   "diagnosticEmittedMass_kg": 0.0,
   "diagnosticMassLabel": "Integrated Ti-species emitted mass diagnostic; not ablation or material removal",
   "peakTemperature_K": 1761.5832088891093,
   "temperatureLabel": "Conditional fixed-surface temperature estimate",
   "geometry": {
    "time_s": 0.0,
    "width_um": 0.0,
    "depth_um": 0.0,
    "length_um": 0.0,
    "volume_um3": 0.0,
    "truncated": false,
    "basis": "instantaneous liquidus extent at peak-melt-volume snapshot; cell bounds",
    "label": "Uncalibrated fixed-surface isotherm estimate",
    "widthLabel": "Conditional fixed-surface liquidus width estimate",
    "widthWarning": null,
    "refusalReason": null,
    "liquidus_K": 1933.15,
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
    "Uncalibrated estimate of temperature and liquidus isotherm geometry for Ti-6Al-4V from the stated transient model. Uncertainty is unknown and may be large. Calibrate to your machine for better accuracy.",
    "The surface is held fixed. Evaporation removes energy, but melt flow, surface recession and changes in alloy composition are not resolved.",
    "This is the liquidus isotherm envelope of the selected temperature model. The envelope uses the reported instantaneous peak-melt-volume snapshot."
   ],
   "fieldSummary": {
    "shape": [
     17,
     17,
     15
    ],
    "dx_m": 1.9999999999999998e-05,
    "minimumFinalTemperature_K": 353.150025307098,
    "maximumFinalTemperature_K": 498.578174334148,
    "minimumSourceCapture": 0.9999999990365253
   },
   "jobType": "ti64-evaporative-surface",
   "settings": {
    "jobType": "ti64-evaporative-surface",
    "config": {
     "power_W": 30.0,
     "speed_mm_s": 1000.0,
     "beamDiameter_um": 80.0,
     "preheat_C": 80.0,
     "mesh_um": 20.0,
     "maxDt_s": 1e-06,
     "trackLength_um": 100.0,
     "cooling_s": 0.0005,
     "sourcePenetration_um": 20.0,
     "convection_W_m2K": 20.0,
     "material": "Ti-6Al-4V",
     "backend": "reference",
     "surfaceMode": "bare-plate",
     "mode": "standard",
     "layers": 1,
     "tracks": 1,
     "study": "none",
     "evaporation": {
      "transitionLow_K": 3560.0,
      "transitionHigh_K": 4000.0,
      "ambientPressure_Pa": 101325.0,
      "returnFraction": 0.2,
      "maxTemperature_K": 5000.0,
      "surfaceTension_N_m": 1.65
     }
    }
   }
  }
 },
 "p8Above": {
  "success": true,
  "stage": "band",
  "requestKey": "984189c5a49cf9a9c051fb608dd6639c8f78745a9ed510248a23910553a4d67a",
  "progress": {
   "armsDone": 79,
   "armsTotal": 79,
   "complete": true
  },
  "researchModels": {
   "schemaVersion": "p8-research-v3",
   "meltDepthLink": {
    "modelId": "p8-melt-link-s2-hypothesis-v2",
    "status": "available",
    "reasonCode": null,
    "uiSentence": "Conditional melt-depth construction: the finite Gaussian conduction floor at or below onset, a surface point plus line source above it; the two fields differ near onset; no blind validation.",
    "validationStatus": "Not experimentally validated; research diagnostic/model only.",
    "fields": {
     "linkedMeltDepth_um": {
      "band": {
       "completeness": "complete",
       "failedArms": [],
       "max": {
        "dependsOn": [
         "conductivity_W_mK",
         "specificHeat_J_kgK",
         "density_kg_m3",
         "wallAbsorptanceProxy",
         "vapourTemperature_K",
         "vapourLatentHeat_J_kg",
         "vapourMolarMass_kg_mol",
         "liquidus_K"
        ],
        "experimentalValidation": false,
        "labelSources": [
         "Gan 2021 SI Table 1 PDF p.20; 835466fa:python/four_alloy_materials.py PROPERTY_LEDGER.ti6al4v.numeric",
         "NBS61-V Table 4(S1); docs/research/SPEC_p8_research_arm_2026-10-14.md section 3",
         "Simonds 2021 Sec.3.2 Fig.3a PDF p.4; NIST mds2-2525",
         "Gan 2021 SI Table 1 PDF p.20"
        ],
        "leafRole": "derived",
        "moduleMaturity": "Research",
        "reasonCode": null,
        "sourceEvidenceKind": "Unresolved",
        "uiSentence": "Research only.",
        "unit": "um",
        "validationStatus": "Not experimentally validated; research diagnostic/model only.",
        "validationStatusLocator": "docs/research/SPEC_p8_research_arm_2026-10-14.md Amendment 3 C4",
        "value": 90.51041715556929,
        "warnings": [
         "SOURCE_SCOPE_TRANSFER",
         "FIELD_SHAPE_STEP_NEAR_ONSET"
        ],
        "weakestInputs": [
         "vapourTemperature_K"
        ]
       },
       "maxArmId": "vapour_3360",
       "maxArmLabel": "vapour 3360: declared assumption (no source)",
       "maxArmTies": 1,
       "method": "declared-ofat-envelope-v1",
       "min": {
        "dependsOn": [
         "conductivity_W_mK",
         "specificHeat_J_kgK",
         "density_kg_m3",
         "wallAbsorptanceProxy",
         "vapourTemperature_K",
         "vapourLatentHeat_J_kg",
         "vapourMolarMass_kg_mol",
         "liquidus_K"
        ],
        "experimentalValidation": false,
        "labelSources": [
         "docs/research/SPEC_p8_research_arm_2026-10-14.md Amendment 2 B3",
         "Simonds 2021 Sec.3.2 Fig.3a PDF p.4; NIST mds2-2525",
         "Gan 2021 SI Table 1 PDF p.20"
        ],
        "leafRole": "derived",
        "moduleMaturity": "Research",
        "reasonCode": null,
        "sourceEvidenceKind": "Literature estimate",
        "uiSentence": "Research only.",
        "unit": "um",
        "validationStatus": "Not experimentally validated; research diagnostic/model only.",
        "validationStatusLocator": "docs/research/SPEC_p8_research_arm_2026-10-14.md Amendment 3 C4",
        "value": 40.99944678232907,
        "warnings": [
         "SOURCE_SCOPE_TRANSFER",
         "LOW_ASPECT_CAVITY_MECHANICS_OMITTED",
         "THERMAL_CYLINDER_CLOSURE_EXTRAPOLATED",
         "FIELD_SHAPE_STEP_NEAR_ONSET"
        ],
        "weakestInputs": []
       },
       "minArmId": "melt_front_cpl_1126",
       "minArmLabel": "melt front cpl 1126: derived (+4 more)",
       "minArmTies": 1,
       "nominal": {
        "dependsOn": [
         "conductivity_W_mK",
         "specificHeat_J_kgK",
         "density_kg_m3",
         "wallAbsorptanceProxy",
         "vapourTemperature_K",
         "vapourLatentHeat_J_kg",
         "vapourMolarMass_kg_mol",
         "liquidus_K"
        ],
        "experimentalValidation": false,
        "labelSources": [
         "Gan 2021 SI Table 1 PDF p.20; 835466fa:python/four_alloy_materials.py PROPERTY_LEDGER.ti6al4v.numeric",
         "NBS61-V Table 4(S1); docs/research/SPEC_p8_research_arm_2026-10-14.md section 3",
         "Simonds 2021 Sec.3.2 Fig.3a PDF p.4; NIST mds2-2525",
         "Gan 2021 SI Table 1 PDF p.20"
        ],
        "leafRole": "derived",
        "moduleMaturity": "Research",
        "reasonCode": null,
        "sourceEvidenceKind": "Literature estimate",
        "uiSentence": "Research only.",
        "unit": "um",
        "validationStatus": "Not experimentally validated; research diagnostic/model only.",
        "validationStatusLocator": "docs/research/SPEC_p8_research_arm_2026-10-14.md Amendment 3 C4",
        "value": 71.66566383588037,
        "warnings": [
         "SOURCE_SCOPE_TRANSFER",
         "FIELD_SHAPE_STEP_NEAR_ONSET"
        ],
        "weakestInputs": []
       },
       "reasonCode": null,
       "statusSupport": [
        {
         "count": {
          "dependsOn": [],
          "experimentalValidation": false,
          "labelSources": [],
          "leafRole": "convention",
          "moduleMaturity": "Research",
          "reasonCode": null,
          "sourceEvidenceKind": null,
          "uiSentence": "Research only.",
          "unit": "1",
          "validationStatus": "Not experimentally validated; research diagnostic/model only.",
          "validationStatusLocator": "docs/research/SPEC_p8_research_arm_2026-10-14.md Amendment 3 C4",
          "value": 20,
          "warnings": [],
          "weakestInputs": []
         },
         "status": "extrapolated"
        }
       ],
       "successfulArms": {
        "dependsOn": [],
        "experimentalValidation": false,
        "labelSources": [],
        "leafRole": "convention",
        "moduleMaturity": "Research",
        "reasonCode": null,
        "sourceEvidenceKind": null,
        "uiSentence": "Research only.",
        "unit": "1",
        "validationStatus": "Not experimentally validated; research diagnostic/model only.",
        "validationStatusLocator": "docs/research/SPEC_p8_research_arm_2026-10-14.md Amendment 3 C4",
        "value": 20,
        "warnings": [],
        "weakestInputs": []
       },
       "totalArms": {
        "dependsOn": [],
        "experimentalValidation": false,
        "labelSources": [],
        "leafRole": "convention",
        "moduleMaturity": "Research",
        "reasonCode": null,
        "sourceEvidenceKind": null,
        "uiSentence": "Research only.",
        "unit": "1",
        "validationStatus": "Not experimentally validated; research diagnostic/model only.",
        "validationStatusLocator": "docs/research/SPEC_p8_research_arm_2026-10-14.md Amendment 3 C4",
        "value": 20,
        "warnings": [],
        "weakestInputs": []
       },
       "unit": "um"
      },
      "consistencyNoteRef": "meltDepthLink",
      "dependsOn": [
       "conductivity_W_mK",
       "specificHeat_J_kgK",
       "density_kg_m3",
       "wallAbsorptanceProxy",
       "vapourTemperature_K",
       "vapourLatentHeat_J_kg",
       "vapourMolarMass_kg_mol",
       "liquidus_K"
      ],
      "experimentalValidation": false,
      "labelSources": [
       "Gan 2021 SI Table 1 PDF p.20; 835466fa:python/four_alloy_materials.py PROPERTY_LEDGER.ti6al4v.numeric",
       "NBS61-V Table 4(S1); docs/research/SPEC_p8_research_arm_2026-10-14.md section 3",
       "Simonds 2021 Sec.3.2 Fig.3a PDF p.4; NIST mds2-2525",
       "Gan 2021 SI Table 1 PDF p.20"
      ],
      "leafRole": "derived",
      "moduleMaturity": "Research",
      "reasonCode": null,
      "sourceEvidenceKind": "Literature estimate",
      "uiSentence": "Research only.",
      "unit": "um",
      "validationStatus": "Not experimentally validated; research diagnostic/model only.",
      "validationStatusLocator": "docs/research/SPEC_p8_research_arm_2026-10-14.md Amendment 3 C4",
      "value": 71.66566383588037,
      "warnings": [
       "SOURCE_SCOPE_TRANSFER",
       "FIELD_SHAPE_STEP_NEAR_ONSET"
      ],
      "weakestInputs": []
     }
    },
    "band": {
     "caption": "Min / nominal / max is an envelope of named one-at-a-time scenarios. Interactions are not evaluated. It is not a confidence interval, an error bar, or a physical lower or upper bound.",
     "completeness": "complete"
    },
    "consistencyNote": {
     "sentence": {
      "dependsOn": [],
      "experimentalValidation": false,
      "labelSources": [],
      "leafRole": "convention",
      "moduleMaturity": "Research",
      "reasonCode": null,
      "sourceEvidenceKind": null,
      "uiSentence": "Research only.",
      "unit": "1",
      "validationStatus": "Not experimentally validated; research diagnostic/model only.",
      "validationStatusLocator": "docs/research/SPEC_p8_research_arm_2026-10-14.md Amendment 3 C4",
      "value": "These inputs or this closure are used beyond their declared source scope (A: source/material-state transfer). Numerical admission is not a sourced physical range, and no blind validation is available.",
      "warnings": [],
      "weakestInputs": []
     },
     "reasons": []
    }
   },
   "keyholeCavity": {
    "fields": {
     "powerOverOnset": {
      "band": {
       "completeness": "complete",
       "failedArms": [],
       "max": {
        "dependsOn": [
         "conductivity_W_mK",
         "specificHeat_J_kgK",
         "density_kg_m3",
         "wallAbsorptanceProxy",
         "vapourTemperature_K",
         "vapourLatentHeat_J_kg",
         "vapourMolarMass_kg_mol"
        ],
        "experimentalValidation": false,
        "labelSources": [
         "Gan 2021 SI Table 1 PDF p.20; 835466fa:python/four_alloy_materials.py PROPERTY_LEDGER.ti6al4v.numeric",
         "NBS61-V Table 4(S1); docs/research/SPEC_p8_research_arm_2026-10-14.md section 3",
         "Simonds 2021 Sec.3.2 Fig.3a PDF p.4; NIST mds2-2525",
         "Gan 2021 SI Table 1 PDF p.20"
        ],
        "leafRole": "derived",
        "moduleMaturity": "Research",
        "reasonCode": null,
        "sourceEvidenceKind": "Literature estimate",
        "uiSentence": "Research only.",
        "unit": "1",
        "validationStatus": "Not experimentally validated; research diagnostic/model only.",
        "validationStatusLocator": "docs/research/SPEC_p8_research_arm_2026-10-14.md Amendment 3 C4",
        "value": 4.781450377250436,
        "warnings": [
         "SOURCE_SCOPE_TRANSFER"
        ],
        "weakestInputs": []
       },
       "maxArmId": "beam_0.95",
       "maxArmLabel": "beam 0.95: declared assumption (no source) (+1 more)",
       "maxArmTies": 1,
       "method": "declared-ofat-envelope-v1",
       "min": {
        "dependsOn": [
         "conductivity_W_mK",
         "specificHeat_J_kgK",
         "density_kg_m3",
         "wallAbsorptanceProxy",
         "vapourTemperature_K",
         "vapourLatentHeat_J_kg",
         "vapourMolarMass_kg_mol"
        ],
        "experimentalValidation": false,
        "labelSources": [
         "Gan 2021 SI Table 1 PDF p.20; 835466fa:python/four_alloy_materials.py PROPERTY_LEDGER.ti6al4v.numeric",
         "NBS61-V Table 4(S1); docs/research/SPEC_p8_research_arm_2026-10-14.md section 3",
         "Simonds 2021 Sec.3.2 Fig.3a PDF p.4; NIST mds2-2525",
         "Gan 2021 SI Table 1 PDF p.20"
        ],
        "leafRole": "derived",
        "moduleMaturity": "Research",
        "reasonCode": null,
        "sourceEvidenceKind": "Literature estimate",
        "uiSentence": "Research only.",
        "unit": "1",
        "validationStatus": "Not experimentally validated; research diagnostic/model only.",
        "validationStatusLocator": "docs/research/SPEC_p8_research_arm_2026-10-14.md Amendment 3 C4",
        "value": 2.324028820606664,
        "warnings": [
         "SOURCE_SCOPE_TRANSFER"
        ],
        "weakestInputs": []
       },
       "minArmId": "onset_O1",
       "minArmLabel": "onset O1: alternative convention",
       "minArmTies": 1,
       "nominal": {
        "dependsOn": [
         "conductivity_W_mK",
         "specificHeat_J_kgK",
         "density_kg_m3",
         "wallAbsorptanceProxy",
         "vapourTemperature_K",
         "vapourLatentHeat_J_kg",
         "vapourMolarMass_kg_mol"
        ],
        "experimentalValidation": false,
        "labelSources": [
         "Gan 2021 SI Table 1 PDF p.20; 835466fa:python/four_alloy_materials.py PROPERTY_LEDGER.ti6al4v.numeric",
         "NBS61-V Table 4(S1); docs/research/SPEC_p8_research_arm_2026-10-14.md section 3",
         "Simonds 2021 Sec.3.2 Fig.3a PDF p.4; NIST mds2-2525",
         "Gan 2021 SI Table 1 PDF p.20"
        ],
        "leafRole": "derived",
        "moduleMaturity": "Research",
        "reasonCode": null,
        "sourceEvidenceKind": "Literature estimate",
        "uiSentence": "Research only.",
        "unit": "1",
        "validationStatus": "Not experimentally validated; research diagnostic/model only.",
        "validationStatusLocator": "docs/research/SPEC_p8_research_arm_2026-10-14.md Amendment 3 C4",
        "value": 4.473090182079545,
        "warnings": [
         "SOURCE_SCOPE_TRANSFER"
        ],
        "weakestInputs": []
       },
       "reasonCode": null,
       "statusSupport": [
        {
         "count": {
          "dependsOn": [],
          "experimentalValidation": false,
          "labelSources": [],
          "leafRole": "convention",
          "moduleMaturity": "Research",
          "reasonCode": null,
          "sourceEvidenceKind": null,
          "uiSentence": "Research only.",
          "unit": "1",
          "validationStatus": "Not experimentally validated; research diagnostic/model only.",
          "validationStatusLocator": "docs/research/SPEC_p8_research_arm_2026-10-14.md Amendment 3 C4",
          "value": 20,
          "warnings": [],
          "weakestInputs": []
         },
         "status": "extrapolated"
        }
       ],
       "successfulArms": {
        "dependsOn": [],
        "experimentalValidation": false,
        "labelSources": [],
        "leafRole": "convention",
        "moduleMaturity": "Research",
        "reasonCode": null,
        "sourceEvidenceKind": null,
        "uiSentence": "Research only.",
        "unit": "1",
        "validationStatus": "Not experimentally validated; research diagnostic/model only.",
        "validationStatusLocator": "docs/research/SPEC_p8_research_arm_2026-10-14.md Amendment 3 C4",
        "value": 20,
        "warnings": [],
        "weakestInputs": []
       },
       "totalArms": {
        "dependsOn": [],
        "experimentalValidation": false,
        "labelSources": [],
        "leafRole": "convention",
        "moduleMaturity": "Research",
        "reasonCode": null,
        "sourceEvidenceKind": null,
        "uiSentence": "Research only.",
        "unit": "1",
        "validationStatus": "Not experimentally validated; research diagnostic/model only.",
        "validationStatusLocator": "docs/research/SPEC_p8_research_arm_2026-10-14.md Amendment 3 C4",
        "value": 20,
        "warnings": [],
        "weakestInputs": []
       },
       "unit": "1"
      },
      "consistencyNoteRef": "keyholeCavity",
      "dependsOn": [
       "conductivity_W_mK",
       "specificHeat_J_kgK",
       "density_kg_m3",
       "wallAbsorptanceProxy",
       "vapourTemperature_K",
       "vapourLatentHeat_J_kg",
       "vapourMolarMass_kg_mol"
      ],
      "experimentalValidation": false,
      "labelSources": [
       "Gan 2021 SI Table 1 PDF p.20; 835466fa:python/four_alloy_materials.py PROPERTY_LEDGER.ti6al4v.numeric",
       "NBS61-V Table 4(S1); docs/research/SPEC_p8_research_arm_2026-10-14.md section 3",
       "Simonds 2021 Sec.3.2 Fig.3a PDF p.4; NIST mds2-2525",
       "Gan 2021 SI Table 1 PDF p.20"
      ],
      "leafRole": "derived",
      "moduleMaturity": "Research",
      "reasonCode": null,
      "sourceEvidenceKind": "Literature estimate",
      "uiSentence": "Research only.",
      "unit": "1",
      "validationStatus": "Not experimentally validated; research diagnostic/model only.",
      "validationStatusLocator": "docs/research/SPEC_p8_research_arm_2026-10-14.md Amendment 3 C4",
      "value": 4.473090182079545,
      "warnings": [
       "SOURCE_SCOPE_TRANSFER"
      ],
      "weakestInputs": []
     },
     "modeledAboveOnset": {
      "dependsOn": [],
      "experimentalValidation": false,
      "labelSources": [],
      "leafRole": "convention",
      "moduleMaturity": "Research",
      "reasonCode": null,
      "sourceEvidenceKind": null,
      "uiSentence": "Research only.",
      "unit": "1",
      "validationStatus": "Not experimentally validated; research diagnostic/model only.",
      "validationStatusLocator": "docs/research/SPEC_p8_research_arm_2026-10-14.md Amendment 3 C4",
      "value": true,
      "warnings": [
       "SOURCE_SCOPE_TRANSFER"
      ],
      "weakestInputs": []
     }
    }
   }
  }
 },
 "p8Below": {
  "success": true,
  "stage": "band",
  "requestKey": "74ed29b0772d949a3c7667ad3c7156e36330825e1ba73254d377076c09df1220",
  "progress": {
   "armsDone": 79,
   "armsTotal": 79,
   "complete": true
  },
  "researchModels": {
   "schemaVersion": "p8-research-v3",
   "meltDepthLink": {
    "modelId": "p8-melt-link-s2-hypothesis-v2",
    "status": "available",
    "reasonCode": null,
    "uiSentence": "Conditional melt-depth construction: the finite Gaussian conduction floor at or below onset, a surface point plus line source above it; the two fields differ near onset; no blind validation.",
    "validationStatus": "Not experimentally validated; research diagnostic/model only.",
    "fields": {
     "linkedMeltDepth_um": {
      "band": {
       "completeness": "complete",
       "failedArms": [],
       "max": {
        "dependsOn": [
         "conductivity_W_mK",
         "specificHeat_J_kgK",
         "density_kg_m3",
         "wallAbsorptanceProxy",
         "vapourTemperature_K",
         "vapourLatentHeat_J_kg",
         "vapourMolarMass_kg_mol",
         "liquidus_K"
        ],
        "experimentalValidation": false,
        "labelSources": [
         "Gan 2021 SI Table 1 PDF p.20; 835466fa:python/four_alloy_materials.py PROPERTY_LEDGER.ti6al4v.numeric",
         "NBS61-V Table 4(S1); docs/research/SPEC_p8_research_arm_2026-10-14.md section 3",
         "Simonds 2021 Sec.3.2 Fig.3a PDF p.4; NIST mds2-2525",
         "Gan 2021 SI Table 1 PDF p.20"
        ],
        "leafRole": "derived",
        "moduleMaturity": "Research",
        "reasonCode": null,
        "sourceEvidenceKind": "Literature estimate",
        "uiSentence": "Research only.",
        "unit": "um",
        "validationStatus": "Not experimentally validated; research diagnostic/model only.",
        "validationStatusLocator": "docs/research/SPEC_p8_research_arm_2026-10-14.md Amendment 3 C4",
        "value": 10.864913806505674,
        "warnings": [
         "SOURCE_SCOPE_TRANSFER"
        ],
        "weakestInputs": []
       },
       "maxArmId": "power_1.05",
       "maxArmLabel": "power 1.05: declared assumption (no source)",
       "maxArmTies": 1,
       "method": "declared-ofat-envelope-v1",
       "min": {
        "dependsOn": [
         "conductivity_W_mK",
         "specificHeat_J_kgK",
         "density_kg_m3",
         "wallAbsorptanceProxy",
         "vapourTemperature_K",
         "vapourLatentHeat_J_kg",
         "vapourMolarMass_kg_mol",
         "liquidus_K"
        ],
        "experimentalValidation": false,
        "labelSources": [
         "docs/research/SPEC_p8_research_arm_2026-10-14.md Amendment 2 B3",
         "Simonds 2021 Sec.3.2 Fig.3a PDF p.4; NIST mds2-2525",
         "Gan 2021 SI Table 1 PDF p.20"
        ],
        "leafRole": "derived",
        "moduleMaturity": "Research",
        "reasonCode": null,
        "sourceEvidenceKind": "Literature estimate",
        "uiSentence": "Research only.",
        "unit": "um",
        "validationStatus": "Not experimentally validated; research diagnostic/model only.",
        "validationStatusLocator": "docs/research/SPEC_p8_research_arm_2026-10-14.md Amendment 3 C4",
        "value": 2.7946234440820708,
        "warnings": [
         "SOURCE_SCOPE_TRANSFER"
        ],
        "weakestInputs": []
       },
       "minArmId": "melt_front_cpl_1126",
       "minArmLabel": "melt front cpl 1126: derived (+4 more)",
       "minArmTies": 1,
       "nominal": {
        "dependsOn": [
         "conductivity_W_mK",
         "specificHeat_J_kgK",
         "density_kg_m3",
         "wallAbsorptanceProxy",
         "vapourTemperature_K",
         "vapourLatentHeat_J_kg",
         "vapourMolarMass_kg_mol",
         "liquidus_K"
        ],
        "experimentalValidation": false,
        "labelSources": [
         "Gan 2021 SI Table 1 PDF p.20; 835466fa:python/four_alloy_materials.py PROPERTY_LEDGER.ti6al4v.numeric",
         "NBS61-V Table 4(S1); docs/research/SPEC_p8_research_arm_2026-10-14.md section 3",
         "Simonds 2021 Sec.3.2 Fig.3a PDF p.4; NIST mds2-2525",
         "Gan 2021 SI Table 1 PDF p.20"
        ],
        "leafRole": "derived",
        "moduleMaturity": "Research",
        "reasonCode": null,
        "sourceEvidenceKind": "Literature estimate",
        "uiSentence": "Research only.",
        "unit": "um",
        "validationStatus": "Not experimentally validated; research diagnostic/model only.",
        "validationStatusLocator": "docs/research/SPEC_p8_research_arm_2026-10-14.md Amendment 3 C4",
        "value": 10.033879325902124,
        "warnings": [
         "SOURCE_SCOPE_TRANSFER"
        ],
        "weakestInputs": []
       },
       "reasonCode": null,
       "statusSupport": [
        {
         "count": {
          "dependsOn": [],
          "experimentalValidation": false,
          "labelSources": [],
          "leafRole": "convention",
          "moduleMaturity": "Research",
          "reasonCode": null,
          "sourceEvidenceKind": null,
          "uiSentence": "Research only.",
          "unit": "1",
          "validationStatus": "Not experimentally validated; research diagnostic/model only.",
          "validationStatusLocator": "docs/research/SPEC_p8_research_arm_2026-10-14.md Amendment 3 C4",
          "value": 20,
          "warnings": [],
          "weakestInputs": []
         },
         "status": "extrapolated"
        }
       ],
       "successfulArms": {
        "dependsOn": [],
        "experimentalValidation": false,
        "labelSources": [],
        "leafRole": "convention",
        "moduleMaturity": "Research",
        "reasonCode": null,
        "sourceEvidenceKind": null,
        "uiSentence": "Research only.",
        "unit": "1",
        "validationStatus": "Not experimentally validated; research diagnostic/model only.",
        "validationStatusLocator": "docs/research/SPEC_p8_research_arm_2026-10-14.md Amendment 3 C4",
        "value": 20,
        "warnings": [],
        "weakestInputs": []
       },
       "totalArms": {
        "dependsOn": [],
        "experimentalValidation": false,
        "labelSources": [],
        "leafRole": "convention",
        "moduleMaturity": "Research",
        "reasonCode": null,
        "sourceEvidenceKind": null,
        "uiSentence": "Research only.",
        "unit": "1",
        "validationStatus": "Not experimentally validated; research diagnostic/model only.",
        "validationStatusLocator": "docs/research/SPEC_p8_research_arm_2026-10-14.md Amendment 3 C4",
        "value": 20,
        "warnings": [],
        "weakestInputs": []
       },
       "unit": "um"
      },
      "consistencyNoteRef": "meltDepthLink",
      "dependsOn": [
       "conductivity_W_mK",
       "specificHeat_J_kgK",
       "density_kg_m3",
       "wallAbsorptanceProxy",
       "vapourTemperature_K",
       "vapourLatentHeat_J_kg",
       "vapourMolarMass_kg_mol",
       "liquidus_K"
      ],
      "experimentalValidation": false,
      "labelSources": [
       "Gan 2021 SI Table 1 PDF p.20; 835466fa:python/four_alloy_materials.py PROPERTY_LEDGER.ti6al4v.numeric",
       "NBS61-V Table 4(S1); docs/research/SPEC_p8_research_arm_2026-10-14.md section 3",
       "Simonds 2021 Sec.3.2 Fig.3a PDF p.4; NIST mds2-2525",
       "Gan 2021 SI Table 1 PDF p.20"
      ],
      "leafRole": "derived",
      "moduleMaturity": "Research",
      "reasonCode": null,
      "sourceEvidenceKind": "Literature estimate",
      "uiSentence": "Research only.",
      "unit": "um",
      "validationStatus": "Not experimentally validated; research diagnostic/model only.",
      "validationStatusLocator": "docs/research/SPEC_p8_research_arm_2026-10-14.md Amendment 3 C4",
      "value": 10.033879325902124,
      "warnings": [
       "SOURCE_SCOPE_TRANSFER"
      ],
      "weakestInputs": []
     }
    },
    "band": {
     "caption": "Min / nominal / max is an envelope of named one-at-a-time scenarios. Interactions are not evaluated. It is not a confidence interval, an error bar, or a physical lower or upper bound.",
     "completeness": "complete"
    },
    "consistencyNote": {
     "sentence": {
      "dependsOn": [],
      "experimentalValidation": false,
      "labelSources": [],
      "leafRole": "convention",
      "moduleMaturity": "Research",
      "reasonCode": null,
      "sourceEvidenceKind": null,
      "uiSentence": "Research only.",
      "unit": "1",
      "validationStatus": "Not experimentally validated; research diagnostic/model only.",
      "validationStatusLocator": "docs/research/SPEC_p8_research_arm_2026-10-14.md Amendment 3 C4",
      "value": "This cavity hypothesis gives zero depression at P/P*<=1. Melting is determined separately by the finite-Gaussian liquidus test; it is not guaranteed. Extrapolated: A: source/material-state transfer.",
      "warnings": [],
      "weakestInputs": []
     },
     "reasons": [
      {
       "allowedValues": null,
       "cause": "upstream",
       "changeInputs": [],
       "code": "NOT_APPLICABLE_BELOW_ONSET",
       "fieldPaths": [
        "meltDepthLink.cavityLedgerRatio"
       ],
       "limitMax": null,
       "limitMin": null,
       "missingInputs": [],
       "quantity": null,
       "value": null
      }
     ]
    }
   },
   "keyholeCavity": {
    "fields": {
     "powerOverOnset": {
      "band": {
       "completeness": "complete",
       "failedArms": [],
       "max": {
        "dependsOn": [
         "conductivity_W_mK",
         "specificHeat_J_kgK",
         "density_kg_m3",
         "wallAbsorptanceProxy",
         "vapourTemperature_K",
         "vapourLatentHeat_J_kg",
         "vapourMolarMass_kg_mol"
        ],
        "experimentalValidation": false,
        "labelSources": [
         "Gan 2021 SI Table 1 PDF p.20; 835466fa:python/four_alloy_materials.py PROPERTY_LEDGER.ti6al4v.numeric",
         "NBS61-V Table 4(S1); docs/research/SPEC_p8_research_arm_2026-10-14.md section 3",
         "Simonds 2021 Sec.3.2 Fig.3a PDF p.4; NIST mds2-2525",
         "Gan 2021 SI Table 1 PDF p.20"
        ],
        "leafRole": "derived",
        "moduleMaturity": "Research",
        "reasonCode": null,
        "sourceEvidenceKind": "Literature estimate",
        "uiSentence": "Research only.",
        "unit": "1",
        "validationStatus": "Not experimentally validated; research diagnostic/model only.",
        "validationStatusLocator": "docs/research/SPEC_p8_research_arm_2026-10-14.md Amendment 3 C4",
        "value": 0.9562900754500872,
        "warnings": [
         "SOURCE_SCOPE_TRANSFER"
        ],
        "weakestInputs": []
       },
       "maxArmId": "beam_0.95",
       "maxArmLabel": "beam 0.95: declared assumption (no source) (+1 more)",
       "maxArmTies": 1,
       "method": "declared-ofat-envelope-v1",
       "min": {
        "dependsOn": [
         "conductivity_W_mK",
         "specificHeat_J_kgK",
         "density_kg_m3",
         "wallAbsorptanceProxy",
         "vapourTemperature_K",
         "vapourLatentHeat_J_kg",
         "vapourMolarMass_kg_mol"
        ],
        "experimentalValidation": false,
        "labelSources": [
         "Gan 2021 SI Table 1 PDF p.20; 835466fa:python/four_alloy_materials.py PROPERTY_LEDGER.ti6al4v.numeric",
         "NBS61-V Table 4(S1); docs/research/SPEC_p8_research_arm_2026-10-14.md section 3",
         "Simonds 2021 Sec.3.2 Fig.3a PDF p.4; NIST mds2-2525",
         "Gan 2021 SI Table 1 PDF p.20"
        ],
        "leafRole": "derived",
        "moduleMaturity": "Research",
        "reasonCode": null,
        "sourceEvidenceKind": "Literature estimate",
        "uiSentence": "Research only.",
        "unit": "1",
        "validationStatus": "Not experimentally validated; research diagnostic/model only.",
        "validationStatusLocator": "docs/research/SPEC_p8_research_arm_2026-10-14.md Amendment 3 C4",
        "value": 0.4648057641213328,
        "warnings": [
         "SOURCE_SCOPE_TRANSFER"
        ],
        "weakestInputs": []
       },
       "minArmId": "onset_O1",
       "minArmLabel": "onset O1: alternative convention",
       "minArmTies": 1,
       "nominal": {
        "dependsOn": [
         "conductivity_W_mK",
         "specificHeat_J_kgK",
         "density_kg_m3",
         "wallAbsorptanceProxy",
         "vapourTemperature_K",
         "vapourLatentHeat_J_kg",
         "vapourMolarMass_kg_mol"
        ],
        "experimentalValidation": false,
        "labelSources": [
         "Gan 2021 SI Table 1 PDF p.20; 835466fa:python/four_alloy_materials.py PROPERTY_LEDGER.ti6al4v.numeric",
         "NBS61-V Table 4(S1); docs/research/SPEC_p8_research_arm_2026-10-14.md section 3",
         "Simonds 2021 Sec.3.2 Fig.3a PDF p.4; NIST mds2-2525",
         "Gan 2021 SI Table 1 PDF p.20"
        ],
        "leafRole": "derived",
        "moduleMaturity": "Research",
        "reasonCode": null,
        "sourceEvidenceKind": "Literature estimate",
        "uiSentence": "Research only.",
        "unit": "1",
        "validationStatus": "Not experimentally validated; research diagnostic/model only.",
        "validationStatusLocator": "docs/research/SPEC_p8_research_arm_2026-10-14.md Amendment 3 C4",
        "value": 0.8946180364159091,
        "warnings": [
         "SOURCE_SCOPE_TRANSFER"
        ],
        "weakestInputs": []
       },
       "reasonCode": null,
       "statusSupport": [
        {
         "count": {
          "dependsOn": [],
          "experimentalValidation": false,
          "labelSources": [],
          "leafRole": "convention",
          "moduleMaturity": "Research",
          "reasonCode": null,
          "sourceEvidenceKind": null,
          "uiSentence": "Research only.",
          "unit": "1",
          "validationStatus": "Not experimentally validated; research diagnostic/model only.",
          "validationStatusLocator": "docs/research/SPEC_p8_research_arm_2026-10-14.md Amendment 3 C4",
          "value": 20,
          "warnings": [],
          "weakestInputs": []
         },
         "status": "extrapolated"
        }
       ],
       "successfulArms": {
        "dependsOn": [],
        "experimentalValidation": false,
        "labelSources": [],
        "leafRole": "convention",
        "moduleMaturity": "Research",
        "reasonCode": null,
        "sourceEvidenceKind": null,
        "uiSentence": "Research only.",
        "unit": "1",
        "validationStatus": "Not experimentally validated; research diagnostic/model only.",
        "validationStatusLocator": "docs/research/SPEC_p8_research_arm_2026-10-14.md Amendment 3 C4",
        "value": 20,
        "warnings": [],
        "weakestInputs": []
       },
       "totalArms": {
        "dependsOn": [],
        "experimentalValidation": false,
        "labelSources": [],
        "leafRole": "convention",
        "moduleMaturity": "Research",
        "reasonCode": null,
        "sourceEvidenceKind": null,
        "uiSentence": "Research only.",
        "unit": "1",
        "validationStatus": "Not experimentally validated; research diagnostic/model only.",
        "validationStatusLocator": "docs/research/SPEC_p8_research_arm_2026-10-14.md Amendment 3 C4",
        "value": 20,
        "warnings": [],
        "weakestInputs": []
       },
       "unit": "1"
      },
      "consistencyNoteRef": "keyholeCavity",
      "dependsOn": [
       "conductivity_W_mK",
       "specificHeat_J_kgK",
       "density_kg_m3",
       "wallAbsorptanceProxy",
       "vapourTemperature_K",
       "vapourLatentHeat_J_kg",
       "vapourMolarMass_kg_mol"
      ],
      "experimentalValidation": false,
      "labelSources": [
       "Gan 2021 SI Table 1 PDF p.20; 835466fa:python/four_alloy_materials.py PROPERTY_LEDGER.ti6al4v.numeric",
       "NBS61-V Table 4(S1); docs/research/SPEC_p8_research_arm_2026-10-14.md section 3",
       "Simonds 2021 Sec.3.2 Fig.3a PDF p.4; NIST mds2-2525",
       "Gan 2021 SI Table 1 PDF p.20"
      ],
      "leafRole": "derived",
      "moduleMaturity": "Research",
      "reasonCode": null,
      "sourceEvidenceKind": "Literature estimate",
      "uiSentence": "Research only.",
      "unit": "1",
      "validationStatus": "Not experimentally validated; research diagnostic/model only.",
      "validationStatusLocator": "docs/research/SPEC_p8_research_arm_2026-10-14.md Amendment 3 C4",
      "value": 0.8946180364159091,
      "warnings": [
       "SOURCE_SCOPE_TRANSFER"
      ],
      "weakestInputs": []
     },
     "modeledAboveOnset": {
      "dependsOn": [],
      "experimentalValidation": false,
      "labelSources": [],
      "leafRole": "convention",
      "moduleMaturity": "Research",
      "reasonCode": null,
      "sourceEvidenceKind": null,
      "uiSentence": "Research only.",
      "unit": "1",
      "validationStatus": "Not experimentally validated; research diagnostic/model only.",
      "validationStatusLocator": "docs/research/SPEC_p8_research_arm_2026-10-14.md Amendment 3 C4",
      "value": false,
      "warnings": [
       "SOURCE_SCOPE_TRANSFER"
      ],
      "weakestInputs": []
     }
    }
   }
  }
 },
 "p8Unavailable": {
  "success": true,
  "stage": "nominal",
  "requestKey": "b399f25a58c06f78e6b086f3896730eef42eb309566e65a30bd5ca8d2f72b9d4",
  "progress": {
   "armsDone": 7,
   "armsTotal": 79,
   "complete": false
  },
  "researchModels": {
   "schemaVersion": "p8-research-v3",
   "meltDepthLink": {
    "modelId": "p8-melt-link-s2-hypothesis-v2",
    "status": "unavailable",
    "reasonCode": "ASPECT_BOUND_OUTSIDE_NUMERICAL_SCOPE",
    "uiSentence": "Conditional melt-depth construction: the finite Gaussian conduction floor at or below onset, a surface point plus line source above it; the two fields differ near onset; no blind validation.",
    "validationStatus": "Not experimentally validated; research diagnostic/model only.",
    "fields": {
     "linkedMeltDepth_um": {
      "band": {
       "completeness": "pending",
       "failedArms": [],
       "max": {
        "dependsOn": [
         "conductivity_W_mK",
         "specificHeat_J_kgK",
         "density_kg_m3",
         "wallAbsorptanceProxy",
         "vapourTemperature_K",
         "vapourLatentHeat_J_kg",
         "vapourMolarMass_kg_mol",
         "liquidus_K"
        ],
        "experimentalValidation": false,
        "labelSources": [
         "Gan 2021 SI Table 1 PDF p.20; 835466fa:python/four_alloy_materials.py PROPERTY_LEDGER.ti6al4v.numeric",
         "NBS61-V Table 4(S1); docs/research/SPEC_p8_research_arm_2026-10-14.md section 3",
         "Simonds 2021 Sec.3.2 Fig.3a PDF p.4; NIST mds2-2525",
         "Gan 2021 SI Table 1 PDF p.20"
        ],
        "leafRole": "derived",
        "moduleMaturity": "Research",
        "reasonCode": "BAND_PENDING",
        "sourceEvidenceKind": "Literature estimate",
        "uiSentence": "Research only.",
        "unit": "um",
        "validationStatus": "Not experimentally validated; research diagnostic/model only.",
        "validationStatusLocator": "docs/research/SPEC_p8_research_arm_2026-10-14.md Amendment 3 C4",
        "value": null,
        "warnings": [],
        "weakestInputs": []
       },
       "maxArmId": null,
       "maxArmLabel": null,
       "maxArmTies": null,
       "method": "declared-ofat-envelope-v1",
       "min": {
        "dependsOn": [
         "conductivity_W_mK",
         "specificHeat_J_kgK",
         "density_kg_m3",
         "wallAbsorptanceProxy",
         "vapourTemperature_K",
         "vapourLatentHeat_J_kg",
         "vapourMolarMass_kg_mol",
         "liquidus_K"
        ],
        "experimentalValidation": false,
        "labelSources": [
         "Gan 2021 SI Table 1 PDF p.20; 835466fa:python/four_alloy_materials.py PROPERTY_LEDGER.ti6al4v.numeric",
         "NBS61-V Table 4(S1); docs/research/SPEC_p8_research_arm_2026-10-14.md section 3",
         "Simonds 2021 Sec.3.2 Fig.3a PDF p.4; NIST mds2-2525",
         "Gan 2021 SI Table 1 PDF p.20"
        ],
        "leafRole": "derived",
        "moduleMaturity": "Research",
        "reasonCode": "BAND_PENDING",
        "sourceEvidenceKind": "Literature estimate",
        "uiSentence": "Research only.",
        "unit": "um",
        "validationStatus": "Not experimentally validated; research diagnostic/model only.",
        "validationStatusLocator": "docs/research/SPEC_p8_research_arm_2026-10-14.md Amendment 3 C4",
        "value": null,
        "warnings": [],
        "weakestInputs": []
       },
       "minArmId": null,
       "minArmLabel": null,
       "minArmTies": null,
       "nominal": {
        "dependsOn": [
         "conductivity_W_mK",
         "specificHeat_J_kgK",
         "density_kg_m3",
         "wallAbsorptanceProxy",
         "vapourTemperature_K",
         "vapourLatentHeat_J_kg",
         "vapourMolarMass_kg_mol",
         "liquidus_K"
        ],
        "experimentalValidation": false,
        "labelSources": [
         "Gan 2021 SI Table 1 PDF p.20; 835466fa:python/four_alloy_materials.py PROPERTY_LEDGER.ti6al4v.numeric",
         "NBS61-V Table 4(S1); docs/research/SPEC_p8_research_arm_2026-10-14.md section 3",
         "Simonds 2021 Sec.3.2 Fig.3a PDF p.4; NIST mds2-2525",
         "Gan 2021 SI Table 1 PDF p.20"
        ],
        "leafRole": "derived",
        "moduleMaturity": "Research",
        "reasonCode": "ASPECT_BOUND_OUTSIDE_NUMERICAL_SCOPE",
        "sourceEvidenceKind": "Literature estimate",
        "uiSentence": "Research only.",
        "unit": "um",
        "validationStatus": "Not experimentally validated; research diagnostic/model only.",
        "validationStatusLocator": "docs/research/SPEC_p8_research_arm_2026-10-14.md Amendment 3 C4",
        "value": null,
        "warnings": [],
        "weakestInputs": []
       },
       "reasonCode": "BAND_PENDING",
       "statusSupport": [
        {
         "count": {
          "dependsOn": [],
          "experimentalValidation": false,
          "labelSources": [],
          "leafRole": "convention",
          "moduleMaturity": "Research",
          "reasonCode": null,
          "sourceEvidenceKind": null,
          "uiSentence": "Research only.",
          "unit": "1",
          "validationStatus": "Not experimentally validated; research diagnostic/model only.",
          "validationStatusLocator": "docs/research/SPEC_p8_research_arm_2026-10-14.md Amendment 3 C4",
          "value": 1,
          "warnings": [],
          "weakestInputs": []
         },
         "status": "outOfRange"
        }
       ],
       "successfulArms": {
        "dependsOn": [],
        "experimentalValidation": false,
        "labelSources": [],
        "leafRole": "convention",
        "moduleMaturity": "Research",
        "reasonCode": "BAND_PENDING",
        "sourceEvidenceKind": null,
        "uiSentence": "Research only.",
        "unit": "1",
        "validationStatus": "Not experimentally validated; research diagnostic/model only.",
        "validationStatusLocator": "docs/research/SPEC_p8_research_arm_2026-10-14.md Amendment 3 C4",
        "value": null,
        "warnings": [],
        "weakestInputs": []
       },
       "totalArms": {
        "dependsOn": [],
        "experimentalValidation": false,
        "labelSources": [],
        "leafRole": "convention",
        "moduleMaturity": "Research",
        "reasonCode": "BAND_PENDING",
        "sourceEvidenceKind": null,
        "uiSentence": "Research only.",
        "unit": "1",
        "validationStatus": "Not experimentally validated; research diagnostic/model only.",
        "validationStatusLocator": "docs/research/SPEC_p8_research_arm_2026-10-14.md Amendment 3 C4",
        "value": null,
        "warnings": [],
        "weakestInputs": []
       },
       "unit": "um"
      },
      "consistencyNoteRef": "meltDepthLink",
      "dependsOn": [
       "conductivity_W_mK",
       "specificHeat_J_kgK",
       "density_kg_m3",
       "wallAbsorptanceProxy",
       "vapourTemperature_K",
       "vapourLatentHeat_J_kg",
       "vapourMolarMass_kg_mol",
       "liquidus_K"
      ],
      "experimentalValidation": false,
      "labelSources": [
       "Gan 2021 SI Table 1 PDF p.20; 835466fa:python/four_alloy_materials.py PROPERTY_LEDGER.ti6al4v.numeric",
       "NBS61-V Table 4(S1); docs/research/SPEC_p8_research_arm_2026-10-14.md section 3",
       "Simonds 2021 Sec.3.2 Fig.3a PDF p.4; NIST mds2-2525",
       "Gan 2021 SI Table 1 PDF p.20"
      ],
      "leafRole": "derived",
      "moduleMaturity": "Research",
      "reasonCode": "ASPECT_BOUND_OUTSIDE_NUMERICAL_SCOPE",
      "sourceEvidenceKind": "Literature estimate",
      "uiSentence": "Research only.",
      "unit": "um",
      "validationStatus": "Not experimentally validated; research diagnostic/model only.",
      "validationStatusLocator": "docs/research/SPEC_p8_research_arm_2026-10-14.md Amendment 3 C4",
      "value": null,
      "warnings": [],
      "weakestInputs": []
     }
    },
    "consistencyNote": {
     "sentence": {
      "dependsOn": [],
      "experimentalValidation": false,
      "labelSources": [],
      "leafRole": "convention",
      "moduleMaturity": "Research",
      "reasonCode": null,
      "sourceEvidenceKind": null,
      "uiSentence": "Research only.",
      "unit": "1",
      "validationStatus": "Not experimentally validated; research diagnostic/model only.",
      "validationStatusLocator": "docs/research/SPEC_p8_research_arm_2026-10-14.md Amendment 3 C4",
      "value": "Not computed: cavity aspect bound = 15.381626654299538 is above the software limit maximum 10.0. This is a software limit, not a physical cutoff. Change laserPower_W, scanSpeed_mm_s, beamDiameter_um to evaluate it.",
      "warnings": [],
      "weakestInputs": []
     },
     "reasons": [
      {
       "allowedValues": null,
       "cause": "software-limit",
       "changeInputs": [
        "laserPower_W",
        "scanSpeed_mm_s",
        "beamDiameter_um"
       ],
       "code": "ASPECT_BOUND_OUTSIDE_NUMERICAL_SCOPE",
       "fieldPaths": [
        "meltDepthLink.cavityDepth_um",
        "meltDepthLink.conductionDepth_um",
        "meltDepthLink.conditionalMeltDepth_um",
        "meltDepthLink.linkedMeltDepth_um",
        "meltDepthLink.controllingLeg",
        "meltDepthLink.linkDispatch",
        "meltDepthLink.conductionStatus",
        "meltDepthLink.surfacePower_W",
        "meltDepthLink.cavityPower_W",
        "meltDepthLink.absorbedPower_W",
        "meltDepthLink.depositedThermalPower_W",
        "meltDepthLink.unresolvedPower_W",
        "meltDepthLink.cavityPowerFraction",
        "meltDepthLink.wallConductionPower_W",
        "meltDepthLink.cavityLedgerRatio",
        "meltDepthLink.lossMultiplier",
        "meltDepthLink.photonResidual_W",
        "meltDepthLink.relativeConvergenceDifference",
        "meltDepthLink.meltDepthCoarse_m",
        "meltDepthLink.meltDepthRefined_m",
        "meltDepthLink.conductionRefinement_m",
        "meltDepthLink.conductionPeakX_m",
        "meltDepthLink.conductionRearBound_m",
        "meltDepthLink.quadratureOrder",
        "meltDepthLink.xSamples",
        "meltDepthLink.observable",
        "meltDepthLink.floorFieldModelId",
        "meltDepthLink.floorExtractorId"
       ],
       "limitMax": 10.0,
       "limitMin": null,
       "missingInputs": [],
       "quantity": "cavity aspect bound",
       "value": 15.381626654299538
      }
     ]
    }
   },
   "keyholeCavity": {
    "fields": {}
   }
  }
 }
};
