# Standards traceability map

Traceability aid only. Not a compliance claim, not qualification, not certification.

This maps what the Metalliksa LPBF run report and qualification dossier record to what the documents below ask for. The most useful part is the gap list in section 4. Machine-readable twin: `data/standards/traceability-map-v1.json`. A test (`tests/standards-traceability.test.ts`) checks that every field path named there exists, so the map cannot rot silently.

Built from `src/utils/lpbfQualificationReport.ts`, `src/utils/lpbfRunReport.ts` and `docs/archive/SCHEMA.md`. Metalliksa is a research workstation. Its dossier states `qualificationStatus: Unresolved` and `productionReady: false`, and nothing here changes that.

## 1. Documents

| Id | Designation | Title | Access | Verification |
|---|---|---|---|---|
| NASA-6030 | NASA-STD-6030 | Additive Manufacturing Requirements for Spaceflight Systems | public | Read from the public PDF. Section numbers and requirement identifiers (AMR-n) were checked against its table of contents and body. No clause text is quoted. |
| AMS7003 | SAE AMS7003 | Laser Powder Bed Fusion Process | paywalled | Title and one-line purpose (process controls for repeatable L-PBF production of aerospace parts) from the public SAE listing. Clause numbers and record requirements: unverified: check against a licensed copy. |
| AMS7000-2 | SAE AMS7000, AMS7001, AMS7002 | AMS7000: L-PBF produced parts, nickel alloy 62Ni-21.5Cr-9.0Mo-3.65Nb, stress relieved, HIP and solution annealed. AMS7001: nickel alloy powder for additive manufacturing (same composition). AMS7002: Process requirements for production of metal powder feedstock for use in additive manufacturing of aerospace parts. | paywalled | Titles from public press coverage of the 2018 SAE release. Relevant here mainly for AMS7002 (powder feedstock records). AMS7000 and AMS7001 are nickel alloy 625 specific and outside the Ti64/AlSi10Mg primary scope. Clause numbers: unverified: check against a licensed copy. |
| F3055 | ASTM F3055 | Standard Specification for Additive Manufacturing Nickel Alloy (UNS N07718) with Powder Bed Fusion | paywalled | Title and topic list from the ASTM store page and third-party listings: ordering information, manufacturing plan, feedstock, thermal processing, chemical composition, microstructure, mechanical properties, hot isostatic pressing, supplementary requirements S1 to S16. Clause numbers: unverified: check against a licensed copy. |
| F3001 | ASTM F3001 | Standard Specification for Additive Manufacturing Titanium-6 Aluminum-4 Vanadium ELI (Extra Low Interstitial) with Powder Bed Fusion | paywalled | Designation and title only, from public listings. Scope topics and clause numbers: unverified: check against a licensed copy. |
| F3318 | ASTM F3318 | Standard for Additive Manufacturing, Finished Part Properties, Specification for AlSi10Mg with Powder Bed Fusion, Laser Beam | paywalled | Designation and title from the ASTM additive manufacturing catalogue and volume listings. One third-party database listed a different alloy for this number, so confirm the title on a licensed copy. Scope topics and clause numbers: unverified: check against a licensed copy. |
| F3302 | ASTM F3302 | Standard for Additive Manufacturing, Finished Part Properties, Standard Specification for Titanium Alloys via Powder Bed Fusion | paywalled | Title and one-line scope (full-melt PBF of titanium alloys, wrought-like properties) from the ANSI webstore listing. Clause numbers: unverified: check against a licensed copy. |
| ISOASTM52900 | ISO/ASTM 52900 | Additive manufacturing, General principles, Fundamentals and vocabulary | paywalled | Designation, title and edition from the ISO catalogue page. A vocabulary standard: it asks for no records, so it is used only to check that dossier wording uses standard terms. Clause numbers: unverified: check against a licensed copy. |

NASA-STD-6030 was read from the public PDF (https://standards.nasa.gov/sites/default/files/standards/NASA/Baseline/0/2021-04-21_nasa-std-6030-approveddocx.pdf), fetched 2026-11-02, 3317520 bytes, 190 pages, SHA-256 `5246d3b992ac0cc7a7deadb4c3c10284444add7d7e055968ae011d671d5a96cd`. The PDF is not stored in the repo. Paywalled documents were not obtained. For them only designation, title and public scope are cited, no clause text is quoted, and every clause reference is marked "unverified: check against a licensed copy".

## 2. Coverage terms

- **recorded**: The dossier or run report carries the field with an explicit value or an explicit unavailable marker. It says nothing about whether the value meets any requirement.
- **partially recorded**: A related field exists but it is free text, user-typed, assumed, simulated or lacks parts the document topic implies.
- **not recorded**: No dossier field carries this.

A mapping for a paywalled document names only a topic seen in its public listing or title. Treat those rows as questions to put to a licensed copy, not as requirements.

## 3. Field map

88 fields: 32 partially recorded, 56 recorded. Paths are relative to the dossier. `extras.*` fields are in the run report but outside the hashed dossier.

### build

| Field path | Status | What is recorded | Documents and references |
|---|---|---|---|
| `buildContext.buildId` | partially recorded | Build or experiment ID typed by the user in the workflow. Free text. No uniqueness check, no link to a revision-controlled production record, no file hash of the build file. | NASA-6030: 4.13 digital thread; 4.14 production engineering record (AMR-30) (partially recorded); AMS7003: unverified: check against a licensed copy (partially recorded) |
| `buildContext.machine` | partially recorded | Machine model typed by the user. Model name only. No serial number, firmware or software version, no equipment control plan reference. | NASA-6030: 4.5 equipment and facility control plan (AMR-14); 5.4.2 build process (AMR-40) (partially recorded); AMS7003: unverified: check against a licensed copy (partially recorded) |
| `buildContext.powderLot` | partially recorded | Powder lot typed by the user. Lot string only. No supplier certificate, size distribution, chemistry or reuse count attached. | NASA-6030: 5.4.1 feedstock (AMR-38); 6.6 used feedstock lot controls (AMR-66) (partially recorded); AMS7000-2: unverified: check against a licensed copy (partially recorded); F3055: unverified: check against a licensed copy (partially recorded); F3001: unverified: check against a licensed copy (partially recorded); F3318: unverified: check against a licensed copy (partially recorded) |
| `buildContext.powderCondition` | partially recorded | Free-text powder condition. Unstructured text. No virgin/reused flag, reuse count or blend ratio field. | NASA-6030: 5.4.1 feedstock (AMR-39 reuse protocol); 6.6 (AMR-66) (partially recorded); AMS7000-2: unverified: check against a licensed copy (partially recorded) |
| `buildContext.heatTreatment` | partially recorded | Free-text heat treatment. Unstructured text. No structured time, temperature, atmosphere or HIP fields, and no thermal-process specification reference. | NASA-6030: 5.4.3 post-processing (AMR-42 to AMR-45); 4.14 thermal processing record (partially recorded); F3055: unverified: check against a licensed copy (partially recorded); AMS7000-2: unverified: check against a licensed copy (partially recorded) |
| `buildContext.measurementMethod` | partially recorded | Free-text measurement method. Unstructured text. No test standard designation field, no specimen geometry or lab identity. | NASA-6030: 5.5 qualification of a candidate material process; 6.11 development of allowables (partially recorded); F3055: unverified: check against a licensed copy (partially recorded) |
| `buildContext.notes` | partially recorded | Research objective and notes. Free text, not a controlled process record. | NASA-6030: 4.14 production engineering record (AMR-30) (partially recorded) |

### sample

| Field path | Status | What is recorded | Documents and references |
|---|---|---|---|
| `specimen.id` | partially recorded | Active specimen identifier in the app. App-internal id for the simulated material, not a physical witness specimen or part serial number. | NASA-6030: 4.11 witness testing for statistical process control (partially recorded); NASA-6030: 4.12 serialization (AMR-26) (partially recorded) |
| `specimen.name` | partially recorded | Alloy or specimen name, canonicalised for the solver. Alloy name only. No specification designation or grade (for example ELI versus standard grade) field. | NASA-6030: 5.4.1 feedstock (AMR-38) (partially recorded); F3055: unverified: check against a licensed copy (partially recorded); F3001: unverified: check against a licensed copy (partially recorded); F3318: unverified: check against a licensed copy (partially recorded); F3302: unverified: check against a licensed copy (partially recorded) |
| `specimen.composition` | partially recorded | Composition map used by the app. Nominal composition used for the model, not a measured heat or powder-lot chemistry. | NASA-6030: 5.4.1 feedstock (AMR-38) (partially recorded); F3055: unverified: check against a licensed copy (partially recorded); F3001: unverified: check against a licensed copy (partially recorded); F3318: unverified: check against a licensed copy (partially recorded); F3302: unverified: check against a licensed copy (partially recorded) |
| `specimen.compositionUnit` | recorded | Unit of the composition values (wt% or at%). Unit is explicit. | NASA-6030: 5.4.1 feedstock (AMR-38) (recorded); F3055: unverified: check against a licensed copy (recorded); F3001: unverified: check against a licensed copy (recorded); F3318: unverified: check against a licensed copy (recorded); F3302: unverified: check against a licensed copy (recorded) |
| `specimen.materialTransfer` | partially recorded | Record of a composition handed over from another module, labelled Screening only. Provenance of a transfer inside the app only. | NASA-6030: 6.8 criteria for the use of external data in the MPS (partially recorded) |
| `currentProcess.inclineAngle_deg` | partially recorded | Surface incline from horizontal used by the model. Model input for solidification, not a recorded build orientation of a physical specimen. No plate location field. | NASA-6030: 6.7.3 explicit evaluation of anisotropy (partially recorded) |

### process

| Field path | Status | What is recorded | Documents and references |
|---|---|---|---|
| `currentProcess.laserPower_W` | recorded | Laser power (W) in the live process vector. Recorded as a model input. User-entered number, not machine-logged. | NASA-6030: 5.4.2 build process (AMR-40) (recorded); AMS7003: unverified: check against a licensed copy (recorded) |
| `currentProcess.scanSpeed_mms` | recorded | Scan speed (mm/s) in the live process vector. Recorded as a model input. User-entered number, not machine-logged. | NASA-6030: 5.4.2 build process (AMR-40) (recorded); AMS7003: unverified: check against a licensed copy (recorded) |
| `currentProcess.hatch_um` | recorded | Hatch spacing (um) in the live process vector. Recorded as a model input. User-entered number, not machine-logged. | NASA-6030: 5.4.2 build process (AMR-40) (recorded); AMS7003: unverified: check against a licensed copy (recorded) |
| `currentProcess.layer_um` | recorded | Layer thickness (um) in the live process vector. Recorded as a model input. User-entered number, not machine-logged. | NASA-6030: 5.4.2 build process (AMR-40) (recorded); AMS7003: unverified: check against a licensed copy (recorded) |
| `currentProcess.beamDiameter_um` | recorded | Beam diameter (um) in the live process vector. Recorded as a model input. User-entered number, not machine-logged. | NASA-6030: 5.4.2 build process (AMR-40) (recorded); AMS7003: unverified: check against a licensed copy (recorded) |
| `currentProcess.preheatTemp_C` | recorded | Preheat temperature (degC). Model input, not machine-logged. No chamber gas, oxygen level or gas flow fields. | NASA-6030: 5.4.2 build process (AMR-40) (recorded); AMS7003: unverified: check against a licensed copy (recorded) |
| `currentProcess.scanStrategy` | partially recorded | Scan strategy label. Label only. No rotation angle, island size, start/stop sequence or tool path file. | NASA-6030: 5.4.2 build process (AMR-40) (partially recorded) |
| `currentProcess.beamProfile` | partially recorded | Beam profile label. Label only. No measured beam characterisation. | NASA-6030: 5.4.2 build process (AMR-40) (partially recorded); AMS7003: unverified: check against a licensed copy (partially recorded) |
| `currentProcess.laserAbsorptivity` | partially recorded | Absorptivity assumed by the model. Assumed model constant, not a measured value. | NASA-6030: 5.4.2 build process (AMR-40) (partially recorded); AMS7003: unverified: check against a licensed copy (partially recorded) |
| `executedInput.material` | recorded | Material name actually sent to the solver. Snapshot of the executed run. | NASA-6030: 5.4.2 build process (AMR-40) (recorded); AMS7003: unverified: check against a licensed copy (recorded) |
| `executedInput.power_W` | recorded | Laser power actually sent to the solver (executed snapshot). Kept beside the current value so staleness is visible. | NASA-6030: 5.4.2 build process (AMR-40) (recorded); AMS7003: unverified: check against a licensed copy (recorded) |
| `executedInput.speed_mm_s` | recorded | Scan speed actually sent to the solver (executed snapshot). Kept beside the current value so staleness is visible. | NASA-6030: 5.4.2 build process (AMR-40) (recorded); AMS7003: unverified: check against a licensed copy (recorded) |
| `executedInput.beamDiameter_um` | recorded | Beam diameter actually sent to the solver (executed snapshot). Kept beside the current value so staleness is visible. | NASA-6030: 5.4.2 build process (AMR-40) (recorded); AMS7003: unverified: check against a licensed copy (recorded) |
| `executedInput.preheat_C` | recorded | Preheat actually sent to the solver (executed snapshot). Kept beside the current value so staleness is visible. | NASA-6030: 5.4.2 build process (AMR-40) (recorded); AMS7003: unverified: check against a licensed copy (recorded) |
| `executedInput.layer_um` | recorded | Layer thickness actually sent to the solver (executed snapshot). Kept beside the current value so staleness is visible. | NASA-6030: 5.4.2 build process (AMR-40) (recorded); AMS7003: unverified: check against a licensed copy (recorded) |
| `executedInput.hatch_um` | recorded | Hatch spacing actually sent to the solver (executed snapshot). Kept beside the current value so staleness is visible. | NASA-6030: 5.4.2 build process (AMR-40) (recorded); AMS7003: unverified: check against a licensed copy (recorded) |

### machine

| Field path | Status | What is recorded | Documents and references |
|---|---|---|---|
| `extras.machineCalibration.artefact.machineCalibrationId` | partially recorded | Id of the user machine-calibration artefact (display only, not in the hashed dossier). User-fitted offset from the user's own tracks. Not an equipment calibration or qualification record, and outside the hashed dossier. | NASA-6030: 4.5 equipment and facility control plan (AMR-14) (partially recorded) |
| `extras.machineCalibration.artefact.contentSha256` | partially recorded | SHA-256 of the machine-calibration artefact. Identifies the artefact bytes. Outside the hashed dossier. | NASA-6030: 4.5 equipment and facility control plan (AMR-14) (partially recorded) |
| `extras.machineCalibration.artefact.userSourceId` | partially recorded | Id of the user-supplied source for the fit. User supplied, unverified. | NASA-6030: 6.8 criteria for the use of external data in the MPS (partially recorded) |
| `extras.machineCalibration.artefact.nTracks` | recorded | Number of tracks used in the fit. Count only. | NASA-6030: 4.5 equipment and facility control plan (AMR-14) (recorded) |
| `extras.machineCalibration.block.factor` | partially recorded | Empirical machine offset factor. Empirical model offset, not a power or focus calibration of the machine. | NASA-6030: 4.5 equipment and facility control plan (AMR-14) (partially recorded) |

### properties

| Field path | Status | What is recorded | Documents and references |
|---|---|---|---|
| `job.result.metrics.width_um` | partially recorded | Melt pool width from the thermal simulation (a model output, not a measurement). Simulated and labelled with its evidence kind. The documents ask for measured finished-part properties (density, microstructure, tensile and so on). None of those are recorded, so the mapping to them is not recorded. | NASA-6030: 6.11 development of allowables and design values; 5.6 registration to an MPS (not recorded); F3055: unverified: check against a licensed copy (not recorded); F3001: unverified: check against a licensed copy (not recorded); F3318: unverified: check against a licensed copy (not recorded); F3302: unverified: check against a licensed copy (not recorded) |
| `job.result.metrics.depth_um` | partially recorded | Melt pool depth from the thermal simulation (a model output, not a measurement). Simulated and labelled with its evidence kind. The documents ask for measured finished-part properties (density, microstructure, tensile and so on). None of those are recorded, so the mapping to them is not recorded. | NASA-6030: 6.11 development of allowables and design values; 5.6 registration to an MPS (not recorded); F3055: unverified: check against a licensed copy (not recorded); F3001: unverified: check against a licensed copy (not recorded); F3318: unverified: check against a licensed copy (not recorded); F3302: unverified: check against a licensed copy (not recorded) |
| `job.result.metrics.length_um` | partially recorded | Melt pool length from the thermal simulation (a model output, not a measurement). Simulated and labelled with its evidence kind. The documents ask for measured finished-part properties (density, microstructure, tensile and so on). None of those are recorded, so the mapping to them is not recorded. | NASA-6030: 6.11 development of allowables and design values; 5.6 registration to an MPS (not recorded); F3055: unverified: check against a licensed copy (not recorded); F3001: unverified: check against a licensed copy (not recorded); F3318: unverified: check against a licensed copy (not recorded); F3302: unverified: check against a licensed copy (not recorded) |
| `job.result.energyBalance` | recorded | Energy conservation audit of the simulation. Numerical check only; not a property. | NASA-6030: 5.5 qualification; 7.2 part classification rationale (recorded) |
| `job.result.convergenceStudy` | recorded | Numerical convergence study, when present. Numerical check only. | NASA-6030: 5.5 qualification; 7.2 part classification rationale (recorded) |

### measurements

| Field path | Status | What is recorded | Documents and references |
|---|---|---|---|
| `measurementDraft.width_um` | partially recorded | Measured width (user draft). User-typed and unverified. Not a lab record: no instrument, calibration, operator, standard or date field. | NASA-6030: 5.5 qualification; 6.8 criteria for use of external data in the MPS (partially recorded) |
| `measurementDraft.depth_um` | partially recorded | Measured depth (user draft). User-typed and unverified. Not a lab record: no instrument, calibration, operator, standard or date field. | NASA-6030: 5.5 qualification; 6.8 criteria for use of external data in the MPS (partially recorded) |
| `measurementDraft.uncertainty_um` | partially recorded | Uncertainty (user draft). User-typed and unverified. Not a lab record: no instrument, calibration, operator, standard or date field. | NASA-6030: 5.5 qualification; 6.8 criteria for use of external data in the MPS (partially recorded) |
| `measurementDraft.source` | partially recorded | Source of the measurement (user draft). User-typed and unverified. Not a lab record: no instrument, calibration, operator, standard or date field. | NASA-6030: 5.5 qualification; 6.8 criteria for use of external data in the MPS (partially recorded) |
| `measurementDraft.specimenOrDoi` | partially recorded | Specimen or DOI (user draft). User-typed and unverified. Not a lab record: no instrument, calibration, operator, standard or date field. | NASA-6030: 5.5 qualification; 6.8 criteria for use of external data in the MPS (partially recorded) |
| `measurementDraft.holdout` | partially recorded | Independent holdout declaration (user draft). User-typed and unverified. Not a lab record: no instrument, calibration, operator, standard or date field. | NASA-6030: 5.5 qualification; 6.8 criteria for use of external data in the MPS (partially recorded) |
| `measurementDraft.replicates` | partially recorded | Replicate values (user draft). User-typed and unverified. Not a lab record: no instrument, calibration, operator, standard or date field. | NASA-6030: 5.5 qualification; 6.8 criteria for use of external data in the MPS (partially recorded) |
| `measurementDraft.status` | partially recorded | Draft status sentence. User-typed and unverified. Not a lab record: no instrument, calibration, operator, standard or date field. | NASA-6030: 5.5 qualification; 6.8 criteria for use of external data in the MPS (partially recorded) |
| `job.result.measurementEvidence[].source` | partially recorded | Worker-reported evidence source. Worker-reported; independent verification not established. | NASA-6030: 5.5 qualification; 6.8 criteria for use of external data in the MPS (partially recorded) |
| `job.result.measurementEvidence[].sameProcessVector` | recorded | Whether the evidence shares the process vector. Match flag as reported. | NASA-6030: 5.5 qualification; 6.8 criteria for use of external data in the MPS (recorded) |
| `job.result.measurementEvidence[].uncertainty_um` | recorded | Uncertainty of an evidence row. As reported by the worker. | NASA-6030: 5.5 qualification; 6.8 criteria for use of external data in the MPS (recorded) |
| `job.result.measurementEvidence[].independentHoldout` | recorded | Independent holdout flag of an evidence row. As reported. | NASA-6030: 5.5 qualification; 6.8 criteria for use of external data in the MPS (recorded) |

### source

| Field path | Status | What is recorded | Documents and references |
|---|---|---|---|
| `researchEvidence` | partially recorded | Linked research evidence records (array). Linked records as opaque JSON. No DOI, authors or testing-standard fields enforced here. | NASA-6030: 6.8 criteria for the use of external data in the MPS (partially recorded) |
| `job.result.material.name` | recorded | Thermal material name. | NASA-6030: 6.8 criteria for the use of external data in the MPS (recorded) |
| `job.result.material.source` | recorded | Source text of the material properties used. Text only; not a specification reference. | NASA-6030: 6.8 criteria for the use of external data in the MPS (recorded) |
| `job.result.material.quality` | recorded | Quality label of the material data (for example estimated). Evidence quality label. | NASA-6030: 6.8 criteria for the use of external data in the MPS (recorded) |
| `extras.buildJob.materialPropertyRevision` | recorded | Revision of the material property table used by the build job. | NASA-6030: 4.13 digital thread (recorded) |
| `extras.buildJob.materialPropertySha256` | recorded | SHA-256 of the material property table. | NASA-6030: 4.13 digital thread (AMR-27) (recorded) |
| `publishedTrackBands.statement` | recorded | Published-track error band statement. Reporting text; sources listed with DOI where available. Present only when a build job is attached. | NASA-6030: 6.8 criteria for the use of external data in the MPS (recorded) |
| `publishedTrackBands.contentSha256` | recorded | SHA-256 of the band artefact. Present only when a build job is attached. | NASA-6030: 4.13 digital thread (AMR-27) (recorded) |

### model

| Field path | Status | What is recorded | Documents and references |
|---|---|---|---|
| `job.result.solver.id` | recorded | Solver id. | NASA-6030: 4.13 digital thread (recorded) |
| `job.result.solver.version` | recorded | Solver version. | NASA-6030: 4.13 digital thread (recorded) |
| `job.result.requestedMode` | recorded | Requested simulation mode. | NASA-6030: 4.13 digital thread (recorded) |
| `job.result.effectiveMode` | recorded | Effective mode actually run. | NASA-6030: 4.13 digital thread (recorded) |
| `job.result.fallbackReason` | recorded | Reason for a mode fallback, or null. | NASA-6030: 4.13 digital thread (recorded) |
| `buildScreening.modelId` | recorded | Build-job screening model id. | NASA-6030: 4.13 digital thread (recorded) |
| `extras.buildJob.solverRevision` | recorded | Build-job solver revision. | NASA-6030: 4.13 digital thread (recorded) |
| `extras.buildJob.buildJobIdentity.sha256` | recorded | SHA-256 of the build-job identity. | NASA-6030: 4.13 digital thread (AMR-27) (recorded) |

### fingerprint

| Field path | Status | What is recorded | Documents and references |
|---|---|---|---|
| `job.result.provenance.implementationHash` | recorded | Implementation hash of the solver code. | NASA-6030: 4.13 digital thread (AMR-27) (recorded) |
| `job.result.provenance.inputHash` | recorded | Hash of the input. | NASA-6030: 4.13 digital thread (AMR-27) (recorded) |
| `job.result.provenance.executionInputHash` | recorded | Hash of the execution input (optional in older runs). Not reported by every worker run. | NASA-6030: 4.13 digital thread (AMR-27) (recorded) |
| `job.result.provenance.implementationFingerprintSchema` | recorded | Fingerprint schema id. | NASA-6030: 4.13 digital thread (AMR-27) (recorded) |
| `job.result.provenance.solverBinaryHash` | recorded | Solver binary hash, null when no binary applies. | NASA-6030: 4.13 digital thread (AMR-27) (recorded) |
| `job.result.provenance.createdAt` | recorded | Run creation time. | NASA-6030: 4.13 digital thread (AMR-27) (recorded) |
| `createdAt` | recorded | Dossier creation time. The exported run report overrides it with the caller-supplied time. | NASA-6030: 4.13 digital thread (AMR-27) (recorded) |
| `dossierSha256` | recorded | SHA-256 of the exact dossier bytes embedded in the exported HTML. Hashes the dossier itself. Not a hash of the build file, scan files or parameter file the documents refer to. | NASA-6030: 4.13 digital thread (AMR-27) (recorded) |

### evidence-labels

| Field path | Status | What is recorded | Documents and references |
|---|---|---|---|
| `resultType` | recorded | Evidence kind (Screening only or Unresolved). | NASA-6030: 4.2 AMCP; 4.17 qualification testing; 5.5 qualification (recorded) |
| `resultDescription` | recorded | Result label text. | NASA-6030: 4.2 AMCP; 4.17 qualification testing; 5.5 qualification (recorded) |
| `qualificationStatus` | recorded | Always Unresolved in the current dossier. The dossier cannot grant a release or certificate. | NASA-6030: 4.2 AMCP; 4.17 qualification testing; 5.5 qualification (recorded) |
| `productionReady` | recorded | Always false. | NASA-6030: 4.2 AMCP; 4.17 qualification testing; 5.5 qualification (recorded) |
| `scope` | recorded | Module maturity scope (Research). | NASA-6030: 4.2 AMCP; 4.17 qualification testing; 5.5 qualification (recorded) |
| `schemaVersion` | recorded | Dossier schema version. | NASA-6030: 4.13 digital thread (recorded) |
| `reportType` | recorded | Report type string. | NASA-6030: 4.2 AMCP; 4.17 qualification testing; 5.5 qualification (recorded) |
| `resultMatchesCurrentInputs` | recorded | Whether the attached result matches current inputs. | NASA-6030: 5.5 qualification; 7.2 part classification rationale (recorded) |
| `buildScreening.verdict.verdict` | recorded | Screening verdict. A screening verdict, not an acceptance decision. | NASA-6030: 5.5 qualification; 7.2 part classification rationale (recorded) |
| `job.result.validationStatus` | recorded | Validation status of the simulation (unvalidated). | NASA-6030: 5.5 qualification; 7.2 part classification rationale (recorded) |
| `job.result.confidence` | recorded | Confidence label of the simulation. | NASA-6030: 5.5 qualification; 7.2 part classification rationale (recorded) |
| `verification.experimentalValidation` | recorded | Experimental validation status (Unresolved). | NASA-6030: 5.5 qualification; 7.2 part classification rationale (recorded) |
| `limitations` | recorded | Generated gap and limitation sentences. | NASA-6030: 5.5 qualification; 7.2 part classification rationale (recorded) |

## 4. Gap list (not recorded)

Records the documents ask for (or, for paywalled documents, appear to ask for) that no dossier field carries.

| Item | Document | Reference | Note |
|---|---|---|---|
| Powder characterisation: size distribution, shape, chemistry, cleanliness, handling and storage, supplier certificate, reuse count and blend | NASA-6030 | 5.4.1 (AMR-38, AMR-39); 6.6 (AMR-66); 5.4.2 (AMR-40) names these as key variables | Only a lot string and a free-text condition exist. |
| Machine serial number, firmware and software versions, equipment and facility control plan reference | NASA-6030 | 4.5 (AMR-14); 5.4.2 (AMR-40) | Only a machine model string exists. |
| Chamber atmosphere, oxygen level, gas flow, humidity, dwell and pause times between layers | NASA-6030 | 5.4.2 (AMR-40) | Only preheat temperature is recorded. |
| Build control parameter file name and cryptographic hash; hashes of build file, tool path and other digital-thread files | NASA-6030 | 5.4.2 (AMR-40); 4.13 (AMR-27) | The dossier hash covers the dossier only. |
| Tool path settings beyond a scan strategy label: area fill scheme, rotation, start/stop sequence, distribution across the build area | NASA-6030 | 5.4.2 (AMR-40) |  |
| Process restart criteria and unplanned interruption records | NASA-6030 | 5.4.2 (AMR-41); 4.7 |  |
| Structured post-processing record: thermal process times, temperatures and atmosphere, HIP, machining, support and platform removal | NASA-6030 | 5.4.3 (AMR-42 to AMR-45); 4.14 (AMR-30) | Heat treatment is one free-text string. |
| Part or specimen serialization and traceability to the build; location on plate | NASA-6030 | 4.12 (AMR-26) |  |
| Witness specimens and statistical process control data | NASA-6030 | 4.11 |  |
| In-situ process monitoring data | NASA-6030 | 4.9 |  |
| Nondestructive evaluation records | NASA-6030 | 4.8 |  |
| Part classification and rationale; AM control plan, qualified material process, material property suite and part process references | NASA-6030 | 4.2, 4.3, 5.5 to 5.7, 6.3, 7.2, 8.3 | By design the dossier does not carry program authority decisions. |
| Measured finished-part properties: density or porosity, microstructure, tensile and hardness, with test standard, specimen geometry, orientation and heat treatment | NASA-6030 | 6.11; 5.6 | Only simulated melt-pool dimensions and a user-typed melt-pool draft exist. The properties tier of docs/archive/SCHEMA.md is not part of the dossier. |
| Build orientation and anisotropy evaluation | NASA-6030 | 6.7.3 | Only a model incline angle exists. |
| Test lab identity, instrument and calibration, operator, dates, approvals and signatures | NASA-6030 | 4.4; 4.14 (AMR-30) names operators, dates and revisions as process metadata |  |
| Specification-level chemistry, microstructure and mechanical property records for Ti-6Al-4V ELI | F3001 | unverified: check against a licensed copy | The dossier is a screening record of a simulation, so no conformance data exist. Which fields the specification requires: unverified: check against a licensed copy. |
| Specification-level records for AlSi10Mg | F3318 | unverified: check against a licensed copy | Same situation as F3001. Required fields: unverified: check against a licensed copy. |
| Specification-level records for IN718 | F3055 | topics from the public listing: manufacturing plan, feedstock, thermal processing, chemical composition, microstructure, mechanical properties, HIP; clause numbers unverified: check against a licensed copy | No IN718 conformance data in the dossier. |
| Specification-level records for titanium alloys by PBF | F3302 | unverified: check against a licensed copy | Required fields: unverified: check against a licensed copy. |
| Powder producer records (AMS7002) | AMS7000-2 | unverified: check against a licensed copy | The dossier holds no producer records. |
| Process control records of an L-PBF process specification | AMS7003 | unverified: check against a licensed copy | Required record set: unverified: check against a licensed copy. |
| Alloy grade or specification designation (for example ELI versus standard grade) | F3001 | unverified: check against a licensed copy | Only a name and nominal composition exist. |

## 5. SCHEMA.md tiers

docs/archive/SCHEMA.md describes a 5-tier Build, ProcessParams, Sample, Properties, Source chain. The run dossier does not instantiate that chain. It carries build context (tier 1, partly), the process vector (tier 2, partly), a specimen (tier 3, partly), simulated W/D/L instead of measured properties (tier 4) and research evidence as opaque JSON (tier 5). SCHEMA.md fields with no dossier counterpart: powder size distribution and atomization, chamber atmosphere, plate location, measured density and tensile properties, testing standards, lab.

## 6. Limits

- Traceability aid only. It makes no statement that a standard is met. A standards-compliance claim would have to name the standard and its scope (RULES.md).
- Edition currency of the paywalled documents is not checked.
- Rows for paywalled documents stay unverified until compared with a licensed copy.
