# SOL-C A7 thermal correction and changed checks

This note supersedes A6.1's thermal range wording and absorptivity scenario, and the one-point scope of the A6 thermal checker. It installs no served channel. The four quantities remain `G` (K/m), `R` (m/s), cooling rate (K/s), and `G/R` (K s/m2), calculated locally before any aggregation, on the selected rear solidifying centre-plane liquidus branch. A5's physical, parent-currentness and numerical-admission gates remain in force.

## Display and tier contract

Tier 1 displays **two significant figures**, retaining full precision in the payload and subsequent calculations. Use this exact text with the actual quantity, alloy and dimensional input endpoints substituted:

> Estimated {quantity} for {alloy} from the selected conduction temperature-field model at the rear solidifying liquidus slice. The range shows how the result moves when each listed input is changed one at a time: {ranges}. It is not an error bar or confidence interval. It excludes model error, which for a conduction model without melt-pool flow can exceed this range, and input interactions and alloy transfer error. Calibrate to your machine for better accuracy.

The interval is called **input sensitivity range** everywhere, including exports. No claim that the true input values lie inside the declared scenarios is made. The preceding sentence does not assert a quantified magnitude of conduction-model error: it explicitly warns that this error is unbounded by the computed range.

Tier 2 displays **two significant figures**, and has no `estimateBand` or claimed uncertainty interval. Use:

> Physics estimate of {quantity} for {alloy} from the selected conduction temperature-field model at the identified solidifying locations. Uncertainty is unknown and may be large. Calibrate to your machine for better accuracy.

Add each applicable source-domain and transfer explanation. A numerical or declared-input sweep cannot promote a route outside its source domain, or a family/alloy-transferred route, to Tier 1. Its independently labelled input sensitivity may be an auxiliary diagnostic only; it is not a Tier 2 estimate band. `tier(..., route_outside=True)` and `tier(..., family_transfer=True)` enforce that cap, including when all ten perturbation arms exist. This applies consistently to Ti64, AlSi10Mg, IN718, 316L and IN625, using the specific parent/transfer disposition recorded in Amendment 7 rather than inferring alloy admission from this manufactured fixture.

## Declared scenarios and support

The eleven full-field arms are nominal and one low/high arm for each of these five inputs. All values are declared screening choices, **not source-derived uncertainty**:

| Input | Declared endpoints | Unit |
|---|---|---|
| Effective conductivity | `[0.8 k0, 1.2 k0]` | W/(m K) |
| Effective heat capacity | `[0.8 cp0, 1.2 cp0]` | J/(kg K) |
| Density | `[0.95 rho0, 1.05 rho0]` | kg/m3 |
| Absorptivity | **`[0.5 eta0, min(1, 1.5 eta0)]`** | dimensionless |
| Liquidus threshold | `[TL0 - 0.25 (TL0-TS0), TL0 + 0.25 (TL0-TS0)]` | deg C or K; same increment |

The wider absorptivity scenario replaces A6's 0.8/1.2 multipliers. The upper cap is absorptivity's physical upper bound, not a clipped calculation result. The other four ranges are unchanged. Recompute diffusivity, field, tail, deepest point and every isotherm root for every arm. With a temperature-dependent kernel, repeat its actual reductions as A6 requires. Beam geometry, process power/speed, base temperature and other unlisted inputs are fixed, not treated as exact. These OFAT endpoints do not bound joint changes, unsampled interior extrema, melt-pool flow, other model discrepancy or alloy-transfer error.

The revised checker evaluates 32 open equal-x midpoint cells between the deepest liquidus point and rear surface crossing on `y=0`. Its declared unequal quadrature weights are the **chord lengths of liquidus cell edges**, an approximation to branch arc length, recomputed in each arm. The weighted median of each locally calculated quantity uses the midpoint of a weighted-median interval if exactly half the weight lies on each side. It does not form cooling or G/R from separately summarized G and R. These are slice length weights, never whole-front surface-area weights. A5 permits an explicitly recorded node/weight choice; the chord choice is a numerical convention rather than a new physics constant. The sampled support changes coherently with each arm's recomputed branch.

The research fixture alone does not supply A5's derivative/root refinement admission for an actual served alloy. Spatial variability and numerical-refinement diagnostics remain separate from the input sensitivity range. Missing/failed input arms leave an otherwise admissible nominal calculation at Tier 2. Unphysical parents, no rear liquidus crossing, zero norm, non-solidifying direction, inconsistent keyhole field or incompatible/stale parents retain their respective A5 refusals; no range can override them.

## Reproducible verification

Run `python -I -B docs/research/scripts/sol_c_a6_thermal_check.py --check`.

The independent arm oracle uses a different liquidus parameterization. For the unclipped Rosenthal field, let `a=v rho cp/(2 k)`, `C=P eta/(2 pi k)`, and beam radius `b`. On `T=TL`,

`x(r)=log[C / ((TL-Tbase) sqrt(r^2+b^2))]/a-r`, `z(r)=sqrt(r^2-x(r)^2)`.

The bottom solves `r-x dx/dr=0`; the rear radius follows directly from `sqrt(r^2+b^2)=C/(TL-Tbase)`. This bypasses the summary's gradient-root/depth-bracketing code. Five-point differences of a separately written field produce its local tuples. Exhaustive minimization of `sum_i w_i |q_i-m|` supplies the weighted-median oracle independently of the cumulative-weight implementation. All eleven recomputed branch summaries and their extrema must agree with these references. A separate lab-frame time-difference oracle checks cooling without relying on cancellation of `G R`.

Mutation tests replace dependencies used by the real `summary()` with nominal-arm roots, arithmetic means, and separate sibling medians. The same assertions must reject each. The smooth physical branch can select the same node for separate medians, so the actual aggregate function is also exercised on an explicit nonmonotone local-output fixture; no false claim is made that every physical branch exhibits a median-product discrepancy. A compiled mutation of the actual `tier()` removes the transfer/out-of-domain caps and must fail the tier assertions. Empty/incomplete/failed sweeps, Celsius/Kelvin offset invariance, cp/rho response, even/unequal weighted medians, nonphysical parents, melting-side/zero/nonfinite tuples and the clipped-branch derivative refusal remain checked. This is software and numerical-transcription evidence, not physical validation or RC1 transport verification.
