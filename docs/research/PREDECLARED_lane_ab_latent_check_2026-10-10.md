# Fixed-resolution conservative latent check on Lane A/B contrasts

Declared on 2026-10-10 on branch claude/lane-ab-latent-check (from codex/depth-identifiability
tip 62e49bd0), committed before any physics run of a Lane input. This is a diagnostic
that follows the negative nominal N3 screen (RESULTS_N3_nominal_two_shape_screen_2026-10-10.md).
It is not the original N3 or N4 gate, trains nothing, and fits nothing.
experimentalValidation=false, depthTransferSolved=false, servedPredictionsChanged=false.

Revision 2 (2026-10-10, still before any Lane run). A gate review of revision 1 found three design problems and
this revision fixes them without changing any threshold, grid, shape coefficient or input: (1) the H2 beam arm cannot
separate H1 from H2 in this model, so it is declared as a conduction-model sensitivity with its zero-latent expectation
stated in advance (section 8); (2) latent heat was confounded with a change of solver, so four same-pipeline L = 0
control units are added and latent effects are reported only against them (section 4a); (3) the hard 120 um search cap
makes some outcomes unreachable, so the reachable outcomes are declared and a closure that ends positive at the cap gets
its own label (section 7a). The plan is now sixteen units.

Question. The zero-latent constant-property surrogate predicted Lane CBM/AMMT depth ratios of
1.17 (A) and 1.21 (B) against observed 3.55 and 2.54. Does the branch's conservative latent
enthalpy model, with the same nominal input ledger and no fitted absorption, change that
diagnosis? Separately, how much of the gap can a different CBM beam diameter alone move in a conduction plus latent model?

## 1. What the branch implements (Task 1 finding)

1. Fixed-source conservative enthalpy forward exists in two independent implementations:
CUDA Warp (ConservativeEnthalpyForward in python/tools/lpbf_projected_enthalpy_forward.py:79,
extended by the graded, local-pseudo, cached-graph and fused classes down to
FusedEnthalpyForward in python/tools/lpbf_projected_fused_step.py:60) and an OpenFOAM
reference under python/tools/projected_*_reference (WSL). Equation in the moving frame,
U = (-v, 0, 0): rho div(U H) - div(k grad T) = Q, MUSCL/minmod H flux, temperature diffusion,
exact phase inverse, adiabatic top surface at z = 0, T = T0 on the other faces. The phase law
is PhaseLaw in python/tools/lpbf_projected_latent_proxy.py:46: H = cp (T - T0) + L f(T), f linear
between solidus and liquidus.
2. A latent source-depth closure IS implemented. solve_feedback in
python/tools/lpbf_projected_enthalpy_feedback_v2.py:234 samples the residual Dref(h) - h on
[0, 120 um] at 17, 33 and 65 points, brackets and refines sign changes to 0.05 um, and
reports sampled roots with no completeness proof. The source for a trial h is d = max(20 um, h),
kappa = 2^clip(b0 + b1 log2(h/r), 0, 9) (shape_parameters in
python/tools/lpbf_projected_source_cells.py:132), the same law as the N3 screen. Dref is the
deepest full-trilinear liquidus isotherm inside the rectangle |x|,|y| <= R, R = r sqrt(-ln(1e-3)/2)
(geometry in lpbf_projected_enthalpy_forward.py:18). So source depth is a closure output, not a
fixed input. Hard validators cap the search depth at 120 um, the whole closure at 120 s and one
forward at 60 s.
3. It has only ever been run on the synthetic fixture (80 W absorbed, 0.8 m/s, r = 50 um,
rho 8000, cp 500, k 20, L 250000, Ts 1000, Tl 1020), shapes (1, 0) and (1, .25). Locators:
RESULTS_projected_front_host_feedback_v2_coarse_constant_2026-10-10.json (sampled single root,
93.3 s of the 120 s cap), ..._coarse_variable_... (111.1 s), RESULTS_projected_front_feedback_v2_coarse_constant_...
(115.2 s). The fine closure, RESULTS_projected_front_host_feedback_v2_fine_constant_2026-10-10.json, ended in a TimeoutError at the cap with no root. It has never been
run on IN625 or on any Lane or NIST input.
4. Numerical status on the front-band grids (python/tools/lpbf_projected_front_band_grid.py:41):
fixed-source finite pair and domain checks PASS for one synthetic point on GPU
(RESULTS_projected_front_GPU_summary_2026-10-10.json: W/D/Dref mesh changes 0.44%, 0.0065%, 0.24%,
domain 2e-10) and for the A selected source on CPU (STATUS.md, 2026-10-10 same-source fine and
domain entries). The general N2 gate is still open: the fine closure times out, the CPU fine point
root residual 0.17 um fails the 0.05 um gate, and Stage 2 material/optical qualification is not
done. latentBackendQualified=false.
5. The original uniform fixed-source N2 latent gate grids (MESHES in lpbf_projected_enthalpy_cuda.py:21,
80x36x24 and 160x72x48, z cells of 15 and 7.5 um) pass the synthetic fixed-source gate but are too
coarse in z for closure at 40 to 90 um depths. The later front-band grids carry the closure
qualification evidence above, so this check uses them.
6. Environment. The project runtime python (.runtime/lpbf-win-py312) has no Warp. The run uses
C:/Users/can02/AppData/Local/Programs/Python/Python312/python.exe (Warp 1.17.0, CUDA 12.9,
RTX 4060 Laptop 8 GiB), the interpreter the branch's CUDA evidence used. Unit tests pass on both.

## 2. Exact model

Conservative latent enthalpy with the projected volumetric source and the sampled closure above,
solved by FusedEnthalpyForward behind HostSeedCacheFeedback, unchanged branch code. Source:
Gaussian 1/e^2 radius r = D4sigma/2 in x and y, axial profile exp(-3 (z/d)^kappa) normalized
(axial_cell_masses, python/tools/lpbf_projected_source_cells.py), absorbed power
0.38 P applied as volumetric heat. The liquidus isotherm is the melt boundary, as in N3
(threshold 1350 C). No fluid flow, recoil, free cavity, evaporation, multiple reflection or
absorptivity change is modelled. Constant properties are used through the mushy zone.

Source depth. For each trial reference depth h the closure sets d = max(20 um, h) and
kappa from the shape law below, solves the field, and takes the residual Dref - h. The reported
prediction is the single sampled root and the geometry of the field at that root. If the search finds
zero, several or unresolved roots, or a field fails a gate, that case has no prediction and
the case is counted as failed. The one zero-root case with a distinct meaning is a residual that is still positive at
the 120 um cap (section 7a). No fallback rule fills in a missing depth.

Shape coefficients (b0, b1), fixed before the run and not tuned on Lane:
(a) primary (0, 0.5), the N3 training winner on NIST folder date 20180828 under the zero-latent
surrogate, used as such. Its provenance is weak: 42 of 79 training conditions sat on the kappa = 1
clip and the nine training losses spanned 0.77 points (RESULTS_N3 report). It was not selected for the latent
model. (b) robustness (1, 0), the N3 fixed baseline and the shape the closure was qualified with.
Both are evaluated; the verdict needs them to agree.

## 3. Input ledger, identical to the N3 screen

| Item | Value | Locator |
| --- | --- | --- |
| Material | IN625, rho 8440 kg/m3, cp 410 J/(kg K), k 9.8 W/(m K), T0 20 C | python/lpbf_public_datasets.py screening_props; python/lpbf_thermal_solver.py:34 SECONDARY_THERMOPHYSICAL_DB; k and cp at 21 C from Special Metals Tables 2 and 3 (python/in625_thermal_material.py) |
| Absorptivity | 0.38 on every case, no fitting | same authority; PREDECLARED_N3_nominal_two_shape_screen_2026-10-10.md |
| Solidus, liquidus | 1290 C, 1350 C, linear mushy fraction | SECONDARY_THERMOPHYSICAL_DB; Sabau et al. 2020, doi:10.1007/s11663-020-01808-w (in625_thermal_material.py:70) |
| Fusion enthalpy | 290000 J/kg | in625_thermal_material.py:74 LATENT_HEAT_J_KG, same source |
| Powers | Table 3 power: CBM 150 and 195 W, AMMT 137.9 and 179.2 W | data/benchmark/lane-in625-amb2018-02/table3_tracks.csv (sha pinned by LANE_TRACKS_TABLE_SHA256); NIST_AMB2018_primary_input_followup_2026-10-10.json (AMMT correction) |
| Speeds | A 400 mm/s, B 800 mm/s | same table |
| Beam D4sigma | CBM 100 um, AMMT 170 um, radius = D/2 | same table. AMMT is measured. CBM 100 um is attributed to manufacturer literature and machine settings, not measured (NIST followup JSON, section Table 2) |

New constants relative to N3 are only the solidus and fusion enthalpy, which the zero-latent screen set to zero. They come
from the same authority. The tests check that the PhaseLaw with L = 0 reduces to the N3 threshold algebra, but that is algebra only:
it says nothing about the solver. The latent effect is therefore measured against the same-pipeline L = 0 units of section 4a, not
against the N3 numbers.

Cases, with absorbed power and radius: CBM-A 57.0 W, r 50 um, 0.4 m/s. AMMT-A 52.402 W,
r 85 um, 0.4 m/s. CBM-B 74.1 W, r 50 um, 0.8 m/s. AMMT-B 68.096 W, r 85 um, 0.8 m/s.
Observed Table 3 track means (same averaging as N3: CBM 3 rows, AMMT 4 rows including the
20 us acquisition): depth CBM-A 151.53, AMMT-A 42.63, CBM-B 91.25, AMMT-B 35.98 um; width
CBM-A 171.0, AMMT-A 148.95, CBM-B 133.02, AMMT-B 125.6 um. Observed depth ratio and difference:
A 3.55 and 108.9 um, B 2.54 and 55.3 um. Zero-latent N3 predictions for the same contrasts
(selected shape): ratio 1.172 and 1.207, difference 12.8 and 11.7 um. Zero-latent N3 depths per unit (selected shape, from the same JSON,
lane_by_case predicted_mean_depth_um): CBM-A 87.22, AMMT-A 74.40, CBM-B 68.30, AMMT-B 56.58 um. The reference JSON is hash pinned in the runner:
6e3c918a0b2a2e1645b029d6b818856a6de23dd2e999e83a0836648cd6963a3a.

No measured depth or width enters any forward calculation, closure, shape or threshold. Lane Table 3 is
the N3 held-out transfer set; nothing here selects a parameter from it.

## 4. Resolution and budget, fixed in advance

1. Closure grid front_coarse, 112x37x48 = 198912 cells, x from -1.5 to 0.3 mm, y +-0.27 mm, z 0 to 0.6 mm.
2. Same-source controls at the closure root, one forward each, no re-closure: front_fine 159x53x71 =
598317 cells for every primary and H2 unit, and front_domain 136x47x55 = 351560 cells (x to -2.1 mm,
y +-0.36 mm, z to 0.9 mm) for the four primary units. Fine closure is not used because the branch's
fine closure exceeds the 120 s cap. The L = 0 control units and the robustness units run the closure only.
3. Closure settings: scan levels 17/33/65 on [0, 120 um], root tolerance 0.05 um, whole closure 120 s,
each forward 60 s, host seed cache 512 MiB, single GPU process, no other GPU job.
4. Declared fallback, the only retry: if and only if the 17/33/65 search ends with a TimeoutError, that unit
is redone once with scan levels 17/33 and a fresh 120 s. Both attempts are recorded. Any other failure,
including no root or several roots, is final. The branch's own synthetic closure takes 93 to 115 s of the 120 s
cap, so timeouts are plausible. The fallback weakens the stability evidence from three scan levels to two and is
reported per unit.
5. Whole run cooperative budget 5400 s, external hard timeout 6000 s. No further units start after 5400 s; unrun
units are listed and the verdict stays inconclusive. Worst case is about 4560 s plus engine setup: the four primary units at
2 x 120 s closure plus two 60 s controls (1440 s), four L = 0 units at 2 x 120 s (960 s), four robustness units at 2 x 120 s (960 s) and
four H2 units at 2 x 120 s plus one 60 s control (1200 s). Typical is roughly 40 minutes. The budget rose from 4800 s and 5400 s
because the plan grew from twelve to sixteen units; no other limit changed.
6. A crash is recorded with its traceback and the run continues with the next unit. A crashed unit is not
rerun inside the same run. If the whole process crashes, the operator may start one full replacement run
with a new output path and must record the crash in the results note. No other retry follows any result.
7. Resolution is never changed after seeing results. No grid, level, tolerance, wall limit or shape
coefficient edits are allowed after this declaration.

## 4a. Same-pipeline L = 0 control

Any change from the N3 ratios 1.172 and 1.207 mixes latent heat with four other changes between the N3 screen and this
pipeline: (i) a Dirichlet T0 box instead of an infinite domain, (ii) finite-volume discretization on front_coarse, (iii) the Dref window
closure instead of the N3 temperature residual, and (iv) the 0 to 120 um search interval instead of 0 to 500 um. To separate them, four extra units run
the same runner path, the same closure grid and the same inputs at the primary shape (0, 0.5) with latent_heat_J_kg = 0 and the solidus left at 1290 C:
l0-control:CBM-A:D100:b0,0.5, l0-control:AMMT-A:D170:b0,0.5, l0-control:CBM-B:D100:b0,0.5, l0-control:AMMT-B:D170:b0,0.5.
They use PhaseLaw with L = 0 through the identical engines (a new engine per unit, phase supplied per unit). The branch's CUDA engine already ran an L = 0 case to convergence on a synthetic fixture (RESULTS_projected_enthalpy_CUDA_L0coarse_2026-10-09.json, latentHeat_J_kg 0, converged, 900 steps), and the opt-in tests construct the L = 0 engine on the declared closure grid. Reading rule, fixed now:

1. The latent effect is reported as the primary-unit readout against the matching L = 0 readout: per unit depth ratio latent over L = 0, per case CBM/AMMT ratio
latent minus L = 0. Latent heat is never credited with a difference from the N3 numbers.
2. The L = 0 result against the N3 depths 87.22, 74.40, 68.30 and 56.58 um is a solver cross-check. A relative difference within 10 percent is flagged as
agreement, otherwise flagged as disagreement. The 10 percent is informational and changes no verdict. It states how much of any ratio change is a
solver effect and not latent physics; it is not a qualification.
3. The label explains-contrast is attributed to latent heat only if the L = 0 control does not itself reach the explains-contrast class. If the L = 0 control also
explains, the label is contrast-reproduced-without-latent-heat. If any L = 0 unit is missing or inconclusive, the explains label is
explains-contrast-latent-attribution-unavailable when the control class cannot be formed, and latent-enthalpy-sufficient-unexpected only when the
control class is formed and differs.
4. L = 0 units never enter the verdict. They affect only the attribution label and the reported effect tables.

## 5. Run plan

Sixteen units, run in this order by python/tools/run_lpbf_lane_ab_latent_check.py:

1. Primary, shape (0, 0.5), closure plus front_fine plus front_domain controls:
primary:CBM-A:D100:b0,0.5, primary:AMMT-A:D170:b0,0.5, primary:CBM-B:D100:b0,0.5, primary:AMMT-B:D170:b0,0.5.
2. L = 0 control, shape (0, 0.5), L = 0, closure only (section 4a):
l0-control:CBM-A:D100:b0,0.5, l0-control:AMMT-A:D170:b0,0.5, l0-control:CBM-B:D100:b0,0.5, l0-control:AMMT-B:D170:b0,0.5.
3. Robustness, shape (1, 0), closure only: shape-robustness:CBM-A:D100:b1,0, shape-robustness:AMMT-A:D170:b1,0,
shape-robustness:CBM-B:D100:b1,0, shape-robustness:AMMT-B:D170:b1,0.
4. H2 beam sensitivity, shape (0, 0.5), closure plus front_fine control: h2-beam:CBM-A:D85:b0,0.5, h2-beam:CBM-B:D85:b0,0.5,
h2-beam:CBM-A:D70:b0,0.5, h2-beam:CBM-B:D70:b0,0.5.

Command, after this document and the runner are committed (the SHA256 of this committed file goes after the flag, it cannot be written inside the file):
C:/Users/can02/AppData/Local/Programs/Python/Python312/python.exe python/tools/run_lpbf_lane_ab_latent_check.py
--run --output docs/research/RESULTS_lane_ab_latent_check_2026-10-10.json --declaration-sha256 [sha256 of this file].
The runner refuses to run unless this document, the runner and the tests are committed and unmodified, the
stated SHA256 matches, and the output path is new. It records before and after SHA256 of every input and module.

## 6. Primary readout

For each case A and B, from the closure root on front_coarse and again from the same-source front_fine and front_domain
controls: predicted CBM and AMMT global isotherm depth (depth_m of the trilinear envelope, the analogue of the N3 x-scanned
centreline depth) and width, the CBM/AMMT depth ratio and difference in um, the width ratio and difference, each next to
the observed values above and the zero-latent values. Reported next to them: the L = 0 control readouts, the latent over L = 0 comparison and the L = 0 versus N3 cross-check of section 4a.
Reported as secondary: Dref, source depth d, kappa, root h, peak
temperature, closure residual, steps, wall time, and the relative W, D and Dref changes between closure and control grids
against the original 1% mesh check (informational; the classification stability test below is the operative control).

## 7. Declared decision rule (fixed before the run)

Per resolution variant (coarse closure, same-source fine, same-source domain) with ratios rA and rB:

1. explains-contrast: rA >= 2.5 and rB >= 2.0.
2. does-not-change-diagnosis: rA < 1.6 and rB < 1.6.
3. inconclusive: anything else, including any missing, non-finite or failed case.

The thresholds come from the orchestrator brief. The branch gives no better pre-existing reason: the original N3 gates are
MAPE and bootstrap criteria and say nothing about machine contrasts. For reference 2.5 is 70% of the observed A ratio and 2.0 is 79%
of the observed B ratio.

Final verdict is the primary-shape class only if coarse, fine and domain variants give the same class, all four primary closures
returned a single sampled root, and the (1, 0) shape gives the same class from its closure ratios. Otherwise the verdict is
inconclusive, with the reason recorded (missing variant, numerical instability across variants, ratios between thresholds,
shape dependence, residual positive at the search cap). A pass is never awarded from partial data.

## 7a. Reachability under the hard 120 um search cap

The closure searches h on [0, 120 um], a validator cap that is not widened. The reported depth is the envelope depth at the root, which can exceed h by a few
percent (synthetic roots 1.6 to 3.7 percent), so the following is an indicative bound and not a certificate.

1. A CBM root cannot lie above the cap. Explains-contrast needs a CBM depth of at least 2.5 times the AMMT depth in case A and 2.0 times in case B. Declared
consequence, case A: with the zero-latent AMMT-A depth 74.40 um the CBM-A depth would need about 186 um, outside [0, 120 um]. Explains-contrast in case A is reachable only if the
AMMT-A depth comes out below 48 um (120 / 2.5). Observed AMMT-A is 42.63 um, so the model would have to land at or below the observed AMMT depth. Case B: with the zero-latent AMMT-B depth 56.58 um
the CBM-B depth would need 113 um, inside the cap but close to it, and reachable only if AMMT-B is below 60 um (120 / 2.0). Because the verdict needs both cases, the explains-contrast verdict is
unreachable by construction unless AMMT-A comes out below 48 um. The runner reports this reachability for the latent, L = 0 and zero-latent AMMT depths.
2. A CBM closure whose residual Dref(h) - h is positive at every sampled depth at every scan level, so the search ends in sampled-no-root with no sign change, has its
self-consistent depth above the cap. It is recorded under the distinct label residual-positive-at-search-cap, with a lower bound of 120 um on the closure depth, the reference depth at the cap and
the indicative ratio of that lower bound to the partner AMMT depth. It is a lower bound on depth only. It is never scored as a root, gets no class, no control solves and no prediction. If it happens to a primary or robustness unit the verdict is inconclusive with the reason
residual-positive-at-search-cap and the unit ids, and the interpretation label is residual-positive-at-search-cap; lower bound on depth only; no-conclusion. If it happens to an H2 or L = 0 unit it is recorded and that unit contributes nothing.
3. What the cap can therefore produce for each case: a scored root (depth at most about 120 um, so a ratio of at most about 120 over the AMMT depth, 1.6 at the zero-latent AMMT-A depth), a residual-positive-at-search-cap lower bound, or a generic failure
(timeout, several roots, invalid field). Only the first can classify a case. A CBM-A result of depth 120 um or more therefore cannot be classified by this run; it can only be bounded below.

## 8. H2 sensitivity: a conduction plus latent model response, not a test of H2

Same model, shape (0, 0.5), CBM D4sigma at 70, 85 and 100 um (100 reused from the primary units), AMMT fixed at 170 um, powers and
speeds unchanged, cases A and B. Per diameter the class is taken from the closure and fine-control ratios and must agree.
Reading rule: any diameter with class explains-contrast gives conduction-model-beam-sensitivity-sufficient; all three diameters
does-not-change gives conduction-model-beam-sensitivity-insufficient; else partial or inconclusive. No diameter is selected, scored against
depth, or carried into any later model. Absorptivity and power are not varied. Nominal AMMT powers (150, 195 W) would raise
AMMT depth and lower the ratio, so they cannot rescue the contrast; nominal-versus-actual CBM power has no second value in the ledger and is not run.

Why this arm cannot separate H1 from H2. The closure sets the source depth from the solution itself (d = max(20 um, h)), so the predicted depth is almost independent of the beam
diameter by construction. The zero-latent constant-property surrogate, run on the same nominal ledger, shape (0, 0.5), with no latent run and no observed depth used, gives
(n3.predict, pinned in the runner as ZERO_LATENT_BEAM_EXPECTATION and re-derived in the tests):

| Case | AMMT D170 depth | CBM D100 depth, ratio | CBM D85 depth, ratio | CBM D70 depth, ratio |
| --- | --- | --- | --- | --- |
| A | 74.4 um | 87.2 um, 1.172 | 88.8 um, 1.194 | 90.4 um, 1.215 |
| B | 56.6 um | 68.3 um, 1.207 | 69.9 um, 1.235 | 71.4 um, 1.261 |

Stated pre-run expectation. The latent run is expected to show the same weak beam response: all three diameters well below the 1.6 no-change threshold, a D100 to D70 ratio change of
a few hundredths, and so the reading conduction-model-beam-sensitivity-insufficient. That outcome is close to certain by construction and carries no information about H1. In reality a smaller beam mostly deepens
the pool through higher irradiance and keyhole onset. That is H1 physics (cavity and keyhole), which this model does not have, so a smaller beam cannot produce its real effect here. An insufficient reading
therefore does not favour H1 and the label does not say so. A sufficient reading would be a surprise and would need independent re-checks. The runner reports the latent D100 to D70 ratio change next to the zero-latent expectation so any departure is visible.
The arm is kept only as a check that the latent model does not behave very differently from the surrogate in its beam response.

## 9. Interpretation table

| Verdict | Other condition | Label | What it supports |
| --- | --- | --- | --- |
| explains-contrast | L = 0 control does not explain | latent-enthalpy-sufficient-unexpected | Latent heat closes most of the contrast against the same-pipeline L = 0 control. Needs independent re-checks before any wider reading. Reachable only if AMMT-A is below 48 um (section 7a) |
| explains-contrast | L = 0 control also explains | contrast-reproduced-without-latent-heat | The pipeline change (box, FV mesh, Dref closure, search interval) explains the contrast, not latent heat |
| explains-contrast | L = 0 class unavailable | explains-contrast-latent-attribution-unavailable | No claim on the cause |
| does-not-change-diagnosis | H2 insufficient | latent-and-conduction-beam-sensitivity-insufficient; H1-versus-H2-not-separated | Neither latent heat nor the conduction-model beam response closes the gap. Expected by construction for the beam arm. Does not favour H1 or H2 |
| does-not-change-diagnosis | H2 sufficient | H2-beam-candidate-requires-independent-measurement | A smaller CBM beam would be required in this model; shows the sensitivity only. Needs an independent CBM beam measurement |
| does-not-change-diagnosis | H2 partial | no-conclusion-on-H1-versus-H2 | Nothing is separated |
| inconclusive | a primary or robustness closure ended residual-positive-at-search-cap | residual-positive-at-search-cap; lower bound on depth only; no-conclusion | Depth above 120 um bounded below, no class |
| inconclusive | any other reason | no-conclusion | No claim |

## 10. Expected failure modes

1. Prior expectation, stated before the run: fusion enthalpy absorbs energy and makes depth slightly smaller, so the latent ratios are expected near the
zero-latent 1.2, well under 1.6. A does-not-change result is the likely outcome. That is not a reason to adjust any threshold.
2. Closure timeouts at the 120 s cap leading to the declared two-level fallback, or to INCONCLUSIVE units after two timeouts. The branch's synthetic closure already uses 93 to 115 s of the 120 s cap with k = 20, and IN625 enters with k = 9.8, so most units may time out and the
single declared run may be spent on inconclusive results. This is accepted: no retry, no cap change and no resolution change follows any result.
3. The 120 um search cap. A CBM closure above 120 um ends as residual-positive-at-search-cap, a lower bound only (section 7a). This can happen for the nominal 100 um CBM beam in case A, not only for the smaller beams, and the explains-contrast verdict for case A is reachable only when AMMT-A is below 48 um. The search interval is a validator cap and is not widened.
4. Several or tangent sampled roots. The solver reports them; none is selected.
5. Grid adequacy is not pre-qualified for these inputs. The z refinement band (60 to 75 um) was built around a synthetic B point, AMMT depths of about 30 to 60 um and
kappa near 1 lie outside it, and the beam radii 35 to 85 um differ from the 50 um the profile cells were aligned to. The same-source fine and domain controls measure the
effect on the ratios; if the class flips between variants the verdict is inconclusive.
6. Outflow boundary at x = -1.5 mm holds T0 while a point-source estimate P_abs/(2 pi k |x|) puts the physical rise there at roughly 570 to 800 K. The problem is advection dominated, and the synthetic
domain pair moved by 2e-10, but this has not been shown for these inputs. The front_domain control tests it. The L = 0 control uses the same box, so it shares this effect with the latent run and cancels it in the latent effect comparison.
7. Warp or CUDA faults, or GPU contention from another process. Recorded as crashes.
8. Constant 21 C properties applied to 1350 C, a literature fusion enthalpy and a linear mushy fraction are screening assumptions. A negative or positive result is conditional on them.
9. Exact agreement in class between variants can still hide a common bias. Nothing here validates the model against experiment.
10. The L = 0 control can disagree with the N3 depths by more than 10 percent. Then the solver change is itself a large effect and the latent effect must be read only against the L = 0 units.

## 11. Software verification before the run

python/test_lpbf_lane_ab_latent_check.py (run on both interpreters) covers: ledger and observed contrasts against the N3 report, source arithmetic
parity with the N3 forward, shape-law parity with N3, axial source profile parity against the N3 axial density, source capture and profile containment for all
sixteen units on all three grids, plan order including the L = 0 units and their identity with the primary inputs, the per-unit phase law (only the L = 0 units drop the fusion enthalpy and the solidus stays 1290 C), the N3 per-unit depths read from the pinned JSON,
the pre-run zero-latent beam expectation re-derived from a fresh n3.predict call, the decision rule, the latent attribution labels, the reachability arithmetic (186 um and 48 um in case A, 113 um and 60 um in case B), the search cap outcome rule and its distinct label, the H2 labels,
fallback only on timeouts, crash and control-failure recording, wall budget, determinism and run guards, plus
a check that this document names every unit and the fixed settings. Opt-in CUDA tests (LPBF_RUN_CUDA_TESTS=1) construct the production engines for the declared grids, including the L = 0 phase engine,
and reproduce the recorded synthetic closure root through the runner (delta 5e-9 m). Result: 63 tests, 61 pass and 2 CUDA opt-in tests skipped on the project runtime and on the Warp interpreter without opt-in; 63 of 63 pass with the opt-in on the Warp interpreter (about 116 s, dominated by the synthetic closure). No Lane case has been solved and no L = 0 Lane unit has been solved. The runner source SHA256 is
30a938d5a311c8faae0ca9ef5a213cc6ad3f893f9cbacdc145185ba374d1dfe3 and the test source SHA256 is 43cdef84ce40c9b9f3bd3f5f08feab229c989512bbec150685381f4136059b26 (LF bytes, -text attributes).

## 12. After the run

Results go to docs/research/RESULTS_lane_ab_latent_check_2026-10-10.json (exclusive create, partial file beside it) and a short results note. All sixteen
units are reported whether they succeed or not. originalN3 stays NOT PASSED and N4 not evaluated whatever the outcome. experimentalValidation=false and
depthTransferSolved=false are not changed by this check.
