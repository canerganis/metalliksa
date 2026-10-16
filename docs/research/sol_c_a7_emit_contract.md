# SOL-C A7 prospective physics payload contract

Research-only Amendment 7 specification, 2026-10-16. This defines physics metadata for a future coordinated migration. It neither changes `python/quantity_envelope.py` nor admits new wire definitions, designs an opt-in channel, or changes a process verdict. Existing v1 status, evidence, source/provenance, physical-validation, identity, numerical, uncertainty and blocking-reason contracts remain authoritative. The research checker tests the prospective subset below, not full v1 conformance.

## Single schema table

Paths are relative to one quantity unless prefixed `container`. A value means non-null `value`; unknown uncertainty never implies no value. Full precision is retained internally. `Estimated` means an actual retained input-sensitivity calculation inside the source domains; it does not mean an error bound, confidence interval or physical validation. Source labels and tiers are independent.

| Field | Type | Unit | Enum / exact constraint | Required when |
|---|---|---|---|---|
| `quantityDefinition` | string | n/a | Existing applicable definition, or prospective definition below | Always |
| `status` | string | n/a | Existing v1: computed, partial, unavailable, failed, not-requested | Always; computed/partial iff value |
| `value` | finite number, category, map, or null | `unit` | Definition below; no NaN/Infinity | Always |
| `unit` | string | SI | Exact definition unit below; `1` is dimensionless | Always, including null |
| `fractionBasis` | string or null | n/a | Exact basis below; null for nonfractions and no-value | Always |
| `dependsOn` | string array | n/a | Nonempty, resolvable input/quantity IDs; acyclic closure | Always |
| `sourceEvidenceKind` | string or null | n/a | Existing per-value rule; null for no-value | Always; inherited v1 rule applies |
| `reasons[]` | existing v1 reason records | n/a | Existing blocking codes only; `outside-source-model-domain` is blocking only | Nonempty iff no-value; empty for value |
| `validity.estimateTier` | string | n/a | `Estimated`, `Physics estimate`, `no-value` | Always |
| `validity.displaySignificantDigits` | integer | n/a | 2 for thermal kinematics/PDAS/SDAS; 1 for chi, envelope fraction, KM and phase/constituent fractions; 1 for associated CET text | Values; null for no-value |
| `validity.domainWarnings[]` | warning objects | n/a | `{code, detail}`; closed codes below; nonempty detail names violated input/model | Always, possibly empty |
| `validity.estimateBand` | object or null | quantity unit | Exact range object below | Object iff `Estimated`; null otherwise |
| `validity.inputSensitivity` | object or null | quantity unit | Same range structure, explicitly auxiliary | Optional for `Physics estimate`; null/absent for other tiers; never promotes tier |
| `validity.uncertaintyStatement` | string or null | n/a | Tier 2: `Uncertainty is unknown and may be large. Calibrate to your machine for better accuracy.` | Exact Tier 2 sentence; null otherwise |
| `validity.nucleationScenarioNote` | string | n/a | Exact mandatory CET text below, including N0, activation, Unresolved and substantial class sensitivity | Every envelope fraction and CET class value |
| `estimateBand/inputSensitivity.lower`, `.upper` | finite number or same-member finite map | quantity unit | Ordered, includes nominal value; no categorical interval | Every range object |
| `estimateBand/inputSensitivity.unit` | string | SI | Exactly quantity `unit` | Every range object |
| `estimateBand/inputSensitivity.construction` | string | n/a | `ofat`, `joint` | Every range object |
| `estimateBand/inputSensitivity.inputRanges[]` | objects | per input | Exact `{name,unit,nominal,lower,upper}`; nonempty name/unit, finite ordered bounds containing nominal | Every range object; nonempty |
| `estimateBand/inputSensitivity.armIds[]` | unique strings | n/a | Retained executed arm identities, not a proposed sweep | Every range object; nonempty |
| `estimateBand/inputSensitivity.unknownComponents[]` | strings | n/a | `model-error`, `input-interactions`, `alloy-transfer-error`, `source-parameter-uncertainty`; must include model-error and, for OFAT, input-interactions | Every range object |
| `uncertainty` | existing object or null | n/a | Existing exact `{kind,construction}` shape; `parameter-sensitivity` for Estimated, `not-quantified` for Physics estimate; exception: existing PDAS alternatives retain `model-alternatives`; human-readable construction | Values; null for no-value |
| `container.inputProvenance` | ID-to-record map | input-specific | Existing v1 input records, including kind/status/dependsOn; retain physical thermal-input transfers | Every referenced input |
| `evaluation` | object | mixed, named below | Exact KM record below | KM value |
| `evaluation.ruleId` | string | n/a | `finite-25K-above-preheat-v1` | KM value |
| `evaluation.preheat_K`, `.offset_K`, `.temperature_K` | finite positive numbers | K | offset exactly 25; temperature = preheat + 25 | KM value |
| `evaluation.time_s` | finite nonnegative number | s | First monotonic post-melt crossing, not arbitrary last history point | KM value |
| `evaluation.historyBracketIds` | two distinct strings | n/a | IDs of consecutive retained path nodes bracketing the crossing | KM value |
| `evaluation.timeInterpolation` | string | n/a | `linear-in-temperature`; crossing verified/refined on the actual material path | KM value |
| `evaluation.refinement` | object | s, K | `{status: refinement-passed, timeTolerance_s: finite >0, temperatureTolerance_K: finite >0}` | KM value |
| `residual` | object | reaction-progress | Exact `{untransformedAsymptote,beta0,preExistingConstituent}`; nonnegative, value + untransformedAsymptote = beta0, preExistingConstituent = 1-beta0 | KM value; never name remainder retained beta |

`estimateBand` and `inputSensitivity` paths in the table are inside `validity`. `inputSensitivity` describes the explored inputs only and has no prediction-interval interpretation. A family transfer, an extrapolated/out-of-range source input, or an inherited domain violation anywhere in the dependency closure forces Tier 2, including transfer of a thermal physical input. Retain that warning on all affected descendants. No number of sweep arms overrides this ceiling. A no-value parent propagates no-value; a physical hard gate remains blocking. Never put a blocking code in `domainWarnings` or a warning code in `reasons`.

Closed value-carrying warning codes: `domain-extrapolation`, `alloy-family-transfer`, `low-peclet-tip-law`, `nucleation-scenario-unresolved`, `Ti-slope-closure`, `binary-eutectic-omission`, `equilibrium-limit-only`, `microconstituent-not-phase`, `km-source-fit-uncertainty`, `km-quench-reference-only`. All except the scenario/source-fit/observable-meaning notes (`nucleation-scenario-unresolved`, `microconstituent-not-phase`, `km-source-fit-uncertainty`) mark an out-of-domain/reference-domain limitation and cap the value at Tier 2. A physically impossible scale or a tip below the admitted eutectic is blocked with `outside-source-model-domain`, not rescued by one of these warnings.

## Prospective quantity definitions

| Definition | Value type | Unit | Fraction basis / exact members | Display significant digits |
|---|---|---|---|---|
| `pdas-correlation` | positive finite number | m | null | 2 |
| `planar-stability-index` | finite number >=0 | 1 | null | 1 |
| `equiaxed-envelope-fraction` | finite number in [0,1] | 1 | volume; grain envelopes including interdendritic liquid, not solid fraction | 1 |
| `km-alpha-m-fraction` | finite number in [0,1] | 1 | reaction-progress; scaled to recorded entering beta0; alpha martensite or massive alpha | 1 |
| `terminal-equilibrium-phase-inventory` | finite fraction map, sum 1 | 1 | mass; exactly `alphaAl`, `Si`, `Mg2Si` | 1 |
| `scheil-microconstituent-inventory` | finite fraction map, sum 1 | 1 | mass; exactly `primaryAlphaAl`, `eutecticConstituent` | 1 |

The sixth definition is necessary: the Al+Si eutectic constituent is not an individual phase and must not use existing `scheil-phase-inventory`. Existing thermal definitions use K/m, m/s, K/s and K*s/m^2; `sdas` uses m, all 2 digits. Existing `pdas-model-alternatives` has unit m, null fraction basis, 2-digit display and exactly two positive finite members `hunt` and `kurzFisher`. These are two models, not fractions and not lower/upper bounds. Their existing `uncertainty.kind` remains `model-alternatives` with a construction explaining unknown model uncertainty; the current transferred Ni route is Tier 2 with no estimateBand. An auxiliary input sensitivity may retain separate memberwise bounds. This research subset deliberately does not admit Tier 1 alternatives. Existing `cet-class` uses unit 1, null fraction basis and exactly columnar/mixed/equiaxed, linked to the corresponding local envelope fraction and 1-digit display text. Rounding a small nonzero fraction to exact zero is forbidden; use scientific notation or an approximate textual bound. The checker checks precision metadata, leaving actual rendering to the later consumer migration.

For KM the first monotonic crossing of `T_preheat + 25 K` is deterministic and finite if the eligible computed history reaches it. Missing crossing/refinement has no value for that scenario; an arbitrary endpoint is not a substitute. The separate path/rate checker establishes first crossing, full-melt initialization and the declared quench conditions; the payload validator establishes the evaluation record shape and arithmetic. If the evaluation temperature is at/above Ms, KM gives zero and visible text must not say mostly alpha. Otherwise the coarse description may read: "Physics estimate for a single rapid cooling pass: mostly alpha martensite or massive alpha (model about 0.9). The remainder is the untransformed KM asymptote, not an estimate of retained beta."

Mandatory CET text: "N0 and activation undercooling are declared scenarios with Unresolved provenance. The model class may change substantially with these scenarios. Uncertainty is unknown and may be large. Calibrate to your machine for better accuracy." This accompanies the class and fraction even when a scenario originated from a fitted source pair. A source scenario count is not independently measured active nucleant density.

## Check boundary

Run `python -I -B docs/research/scripts/sol_c_a7_emit_check.py --check`. The executable prospective subset validator accepts valid thermal, fraction, phase, constituent, KM and no-value examples and rejects actual mutated payloads: transitive tier laundering, missing units/bases, phase/constituent confusion, warning/reason confusion, missing band inputs/arms/unknown components, excessive precision, wrong evaluation rule and retained-beta naming. It validates metadata and model arithmetic constraints, not source truth, execution receipts, physical accuracy or experimental validity. Existing v1 base conformance remains a separate integration-owner gate.
