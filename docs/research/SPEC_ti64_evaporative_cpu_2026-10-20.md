# Ti64 fixed-surface evaporative CPU solver

User-authorized implementation, 2026-10-20; existing local data only. This refines
G1.2/G1.3 and A1.1 of SPEC_engine_estimates_2026-10-17.md, not their scientific ceiling.

## Scope and identity

Add an opt-in Python/JSON CLI solver `python/lpbf_ti64_evaporative_solver.py`, model
`ti64-fixed-surface-evaporation-v1`. It solves a spatial 3D transient enthalpy field,
using existing conduction, moving volumetric source, mesh and material operators.
This is not a scalar surface balance, a boiling cap or a keyhole solver. Preserve
all existing solver bytes/pins/goldens/default routes. UI/HTTP integration is outside
this bounded solver request; the new schema must not be mistaken for an old result.

CPU, nominal Ti-6Al-4V, single bare-plate track/layer only. Reject unsupported alloy,
backend, powder, layered support, measurements, old cap or Marangoni switches.
Use the existing material registry as thermal authority. Above its table endpoint,
use an explicitly disclosed constant-liquid-property continuation up to the requested
`maxTemperature_K`; no silent `np.interp` clipping. Fixed reference density and
volumetric enthalpy are retained. This continuation is a model assumption, not new data.

## Evaporative boundary

Source constants: verified Gan2021 SI Table1 Ti species Tv=3560 K, Lv=9.255e6 J/kg,
M=0.048 kg/mol; R=8.31446261815324 J/(mol K), p_ref=101325 Pa convention.
All new vapor constants live in one named source-profile module, not copied into
the time loop. The existing four-alloy authority is not modified.

Require an explicit `evaporation` object with transitionLow_K, transitionHigh_K,
ambientPressure_Pa, returnFraction and maxTemperature_K. Optional
surfaceTension_N_m is an explicitly assumed scalar (never silently defaulted).
Positive finite inputs, no booleans/numeric strings/unknown keys; 0<=returnFraction<1;
liquidus<=low<high<=maxTemperature_K. Bound maxTemperature_K to 6000 K as a declared
computational scenario limit, not a source validity range. Reference tests may use
low=3560 K, high=4000 K, beta=.2, ambient=101325 Pa, sigma=1.65 N/m, Tmax=5000 K;
these transition/tension choices are declared scenarios, not measured Ti64 inputs.

For T<=low: j=0, pr=pambient. For T>=high:
psat=p_ref exp[(Lv*M/R)(1/Tv-1/T)];
j=(1-beta)*psat*sqrt(M/(2*pi*R*T)); pr=(1+beta)*psat/2.
Between: cubic Hermite interpolation matching the low value and zero slope to
the high formula's value and derivative at high, separately for j and pr.
This is a declared matching construction following Gan Eqs12/14, not recovered
source fitting coefficients. Reject settings giving negative/nonmonotone bridge
flux or recoil below ambient; do not clip such a bridge. The high law is used only
above the explicit high threshold. No invented vapor partial pressure.

Top exposed face only: subtract q_evap=j*Lv [W/m2] divided by dx from volumetric
rate. Existing volumetric source is the sole laser input. No conductivity multiplier.
Track evaporative energy and diagnostic emitted mass separately; fixed material
mass/composition/geometry are not reduced. Never report diagnostic mass as ablation.

## Accepted-step and output rules

Explicit FV stepping: use conduction/source stability bounds plus surface-loss
derivative bound; recompute moving source after dt reductions. Compute candidates
without mutating accepted state. Nonfinite/out-of-enthalpy-range candidates reduce
dt with a bounded retry count; persistent failure raises, never clamps. Commit
temperature, enthalpy, clock, energy/mass ledgers and onset state only after admission.

A1.1: evaluate every accepted exposed liquid state, with r=diameter_1e2/2.
Active j and pr-pambient >= 2*sigma/r latch onset, including equality. Missing sigma
with active evaporation latches unresolved geometry. Initial accepted state must
also be accounted for if evaporation is active. Later cooling never clears a latch.
Depth/length/volume and all aliases are unavailable after onset/unresolved; width
and temperature retain explicit fixed-surface conditional labels. No physical-front,
porosity, stress or keyhole geometry is emitted. Rejected candidates cannot latch.

Output distinct schema, model/source/input provenance, dependency fingerprint,
accepted-step count/time, separate input/base/radiative-convective/evaporative energy,
stored energy and residual, diagnostic mass, peak temperature and bounded isotherm
geometry with reasons and gate status. JSON finite. `experimentalValidation=false`,
`productionReady=false`, tier `Uncalibrated estimate`. No data-fitting or validation claim.

## Acceptance, declared before implementation

- Independent Maxwellian quadrature / closed-law constants and scalar units;
  relative mass-flux error <=1e-8. Exact zero evaporation below transition.
- Bridge endpoint value/derivative continuity and analytic monotonicity; malformed
  settings fail; negative/NaN states are not clipped.
- Gate below/equal/above pressure boundary, radius-vs-diameter, missing sigma,
  onset then cooling, and rejected-state isolation.
- Independent single-cell constant-capacity cooling ODE reference: decreasing
  timestep errors with observed first-order explicit convergence (order >0.8);
  integrated evaporative energy equals enthalpy removal within 1e-10 relative.
- Spatial conduction manufactured/analytic reference under refinement; existing
  operators' tests plus a new actual-field case, error decreases with refinement.
- Actual moving-source Ti64 solve has positive evaporation, finite temperatures,
  reduced retained energy against the same zero-flux scenario; energy residual
  <=1e-9 relative to max(input, loss, stored magnitude, 1e-12 J).
- Default solver regression and frozen parity remain unchanged; no re-recording.
- CLI round trip, unsupported inputs, zero-evaporation and onset geometry refusal.

No tolerance changes after observing outputs without an explicit recorded rationale.
