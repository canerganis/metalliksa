/**
 * Equation content of the "How this is calculated" panels. Review in one place.
 *
 * Every equation here is transcribed from the code that computes the shown value (not from memory or a textbook).
 * `codeLocator` names that code; `sourceLocator` repeats the source the code or spec cites for it. Where the code
 * differs from the cited paper, the equation is the code's form and `asImplemented` says so.
 * The matching review table is docs/research/EQUATIONS_SHOWN_2026-10-22.md.
 *
 * Input values are only read from the result object (see `readResultPath`); nothing is recomputed here. A value that
 * the result does not carry is shown as its symbol only.
 */

export type KernelId = "rosenthal" | "eagar-tsai" | "goldak";

export interface ExplainerInput {
  symbol: string;
  label: string;
  unit: string;
  /** Dot path into the result object. */
  path: string;
}

export interface ExplainerEquation {
  id: string;
  label: string;
  /** KaTeX source. */
  latex: string;
  /** Plain-text formula, used as the accessible text alternative and as the fallback before KaTeX has loaded. */
  plain: string;
  /** Symbol definitions with units. */
  symbols: ReadonlyArray<readonly [string, string]>;
  codeLocator: string;
  sourceLocator: string;
  /** Present only when the code's form differs from, or narrows, the cited source. */
  asImplemented?: string;
  /** Show only for these kernels (the result's model id names the kernel). */
  kernels?: readonly KernelId[];
}

export interface ExplainerNote {
  label: string;
  /** Dot path to a string in the result, shown verbatim. */
  path: string;
}

export interface Explainer {
  id: string;
  title: string;
  summary: string;
  inputs: readonly ExplainerInput[];
  notes: readonly ExplainerNote[];
  equations: readonly ExplainerEquation[];
}

const TS = "python/lpbf_thermal_solver.py";

/** Kernel named by a result's model id ("rosenthal-screening-v1", "eagar-tsai-v2", "goldak-half-space-v3"). */
export function kernelOfModelId(modelId: unknown): KernelId | null {
  const id = typeof modelId === "string" ? modelId.toLowerCase() : "";
  if (id.startsWith("rosenthal")) return "rosenthal";
  if (id.startsWith("eagar-tsai")) return "eagar-tsai";
  if (id.startsWith("goldak")) return "goldak";
  return null;
}

/** Reads a dot path from a result object; undefined when any step is missing. */
export function readResultPath(result: unknown, path: string): unknown {
  let cursor: unknown = result;
  for (const key of path.split(".")) {
    if (cursor === null || typeof cursor !== "object") return undefined;
    cursor = (cursor as Record<string, unknown>)[key];
  }
  return cursor;
}

const MELTPOOL_GEOMETRY: Explainer = {
  id: "meltpool-geometry",
  title: "How the melt pool length, width, depth and VED are calculated",
  summary:
    "The screening kernel gives a temperature field. Length, width and depth are read from it as the liquidus isotherm by a numerical search, and depth is raised to the Fabbro keyhole depth when that is larger. Screening only, not experimentally validated.",
  inputs: [
    { symbol: "P", label: "laser power", unit: "W", path: "processParameters.laserPower_W" },
    { symbol: "v", label: "scan speed", unit: "mm/s", path: "processParameters.scanSpeed_mm_s" },
    { symbol: "d", label: "beam diameter (1/e^2)", unit: "um", path: "processParameters.beamDiameter_um" },
    { symbol: "T_0", label: "preheat", unit: "degC", path: "processParameters.preheatTemp_C" },
    { symbol: "h", label: "hatch spacing", unit: "um", path: "processParameters.hatchSpacing_um" },
    { symbol: "t", label: "layer thickness", unit: "um", path: "processParameters.layerThickness_um" },
    { symbol: "A", label: "conduction absorptivity", unit: "", path: "processParameters.conductionAbsorptivity" },
    { symbol: "P_f", label: "field power", unit: "W", path: "processParameters.fieldPower_W" },
    { symbol: "k", label: "conduction-kernel conductivity", unit: "W/m/K", path: "processParameters.effectiveConductivity_W_mK" },
    { symbol: "c_p", label: "conduction-kernel specific heat", unit: "J/kg/K", path: "processParameters.effectiveSpecificHeat_J_kgK" },
    { symbol: "rho_k", label: "conduction-kernel density", unit: "kg/m^3", path: "processParameters.kernelDensity_kg_m3" },
    { symbol: "alpha", label: "conduction-kernel diffusivity", unit: "m^2/s", path: "processParameters.effectiveDiffusivity_m2_s" },
    { symbol: "T_liq", label: "liquidus", unit: "degC", path: "thermalSlices.liquidus_C" },
    { symbol: "k_s", label: "solid conductivity", unit: "W/m/K", path: "processParameters.solidConductivity_W_mK" },
    { symbol: "Pe (Fabbro)", label: "Peclet number of the Fabbro leg", unit: "", path: "keyholeModel.peclet" },
    { symbol: "e", label: "Fabbro keyhole depth served", unit: "um", path: "keyholeModel.fabbroDepth_um" },
    { symbol: "L", label: "melt pool length served", unit: "um", path: "meltPoolGeometry.length_um" },
    { symbol: "W", label: "melt pool width served", unit: "um", path: "meltPoolGeometry.width_um" },
    { symbol: "D", label: "melt pool depth served", unit: "um", path: "meltPoolGeometry.depth_um" },
    { symbol: "VED", label: "volumetric energy density served", unit: "J/mm^3", path: "processParameters.volumetricEnergyDensity_J_mm3" },
  ],
  notes: [
    { label: "Extent status", path: "meltPoolGeometry.extentStatus" },
    { label: "Extent note", path: "meltPoolGeometry.extentNote" },
    { label: "Keyhole depth leg basis", path: "keyholeModel.basis" },
    { label: "Keyhole depth benchmark note", path: "keyholeModel.depthBenchmarkNote" },
  ],
  equations: [
    {
      id: "field-power",
      label: "Power put into the conduction field",
      latex: String.raw`P_f = A\,P`,
      plain: "P_f = A * P",
      symbols: [
        ["P_f", "field power, W"],
        ["A", "conduction absorptivity (flat value; the ray-traced value only if that model was requested), dimensionless"],
        ["P", "laser power, W"],
      ],
      codeLocator: `${TS}:calculate_meltpool_physics (P_absorbed = eta_base * P_laser; P_geom = P_absorbed * latent_heat_power_factor, factor 1.0)`,
      sourceLocator:
        "Code comments: Eagar and Tsai 1983 and Goldak 1984 take Q as absorbed power; Rubenchik 2018 Sec. 3.1 and Gan 2021 SI Method 3 use one absorptivity in the conduction scaling. Latent heat of fusion is excluded.",
    },
    {
      id: "diffusivity",
      label: "Thermal diffusivity of the conduction kernel",
      latex: String.raw`\alpha = \frac{k}{\rho_k\,c_p}`,
      plain: "alpha = k / (rho_k * c_p)",
      symbols: [
        ["alpha", "thermal diffusivity, m^2/s"],
        ["k", "conductivity of the conduction kernel, W/m/K"],
        ["rho_k", "kernel density, kg/m^3"],
        ["c_p", "kernel specific heat, J/kg/K"],
      ],
      codeLocator: `${TS}:calculate_meltpool_physics (alpha_th = k_th / (rho_k * cp)); k, cp, rho_k from ${TS}:resolve_conduction_kernel`,
      sourceLocator:
        "Code comment (P7b): one constant k, cp, rho per call; Rubenchik 2018 Sec. 3.1 (values at the melting point) where a source gives them, else a labelled solid/liquid blend.",
    },
    {
      id: "rosenthal",
      label: "Rosenthal field (kernel rosenthal-screening-v1)",
      latex: String.raw`T(x,y,z) = T_0 + \frac{P_f}{2\pi\,k\,R_{\mathrm{reg}}}\,\exp\!\left(-\frac{v\,(R+x)}{2\,\alpha}\right),\quad R=\sqrt{x^2+y^2+z^2},\; R_{\mathrm{reg}}=\sqrt{R^2+r_{\mathrm{reg}}^2},\; r_{\mathrm{reg}}=\max\!\left(\frac{d}{2\sqrt2},\,8\,\mu\mathrm{m}\right)`,
      plain:
        "T(x,y,z) = T0 + Pf / (2 pi k R_reg) * exp(-v (R + x) / (2 alpha)); R = sqrt(x^2+y^2+z^2); R_reg = sqrt(R^2 + r_reg^2); r_reg = max(d/(2 sqrt 2), 8 um)",
      symbols: [
        ["T", "temperature in the laser-attached frame (+x travel, z down), degC"],
        ["x, y, z", "position, m"],
        ["v", "scan speed, m/s"],
        ["r_reg", "regularisation radius, m"],
      ],
      codeLocator: `${TS}:rosenthal_temperature_C; r_reg = max(r_beam / sqrt(2), 8e-6) in calculate_meltpool_physics`,
      sourceLocator: "Docstring: 3D Rosenthal (1946) moving point source.",
      asImplemented:
        "Only the 1/R prefactor is regularised; the exponent keeps the true R. The exponent argument is clamped to [-45, 20]. The near-field maximum is a regularisation artefact, not a wall temperature.",
      kernels: ["rosenthal"],
    },
    {
      id: "eagar-tsai",
      label: "Eagar-Tsai field (kernel eagar-tsai-v2)",
      latex: String.raw`T = T_0 + \frac{P_f}{2\pi\sqrt{2\pi}\,k\,\sigma}\int_0^\infty \frac{2}{1+u^2}\,\exp\!\left(-\frac{(X+U u^2)^2+Y^2}{2\,(1+u^2)}-\frac{Z^2}{2\,u^2}\right)du`,
      plain:
        "T = T0 + Pf / (2 pi sqrt(2 pi) k sigma) * integral from 0 to infinity of 2/(1+u^2) * exp(-((X+U u^2)^2 + Y^2) / (2 (1+u^2)) - Z^2 / (2 u^2)) du",
      symbols: [
        ["sigma", "d/4, half of the 1/e^2 beam radius d/2, m"],
        ["X, Y, Z", "x/sigma, y/sigma, |z|/sigma"],
        ["U", "v sigma / (2 alpha)"],
        ["u", "integration variable, tau = u^2"],
      ],
      codeLocator: "python/eagar_tsai_solver.py:EagarTsaiField (__init__ prefactor, bind_speed, temperature_C)",
      sourceLocator: "Eagar and Tsai 1983, Welding Journal, 346-s to 354-s (module docstring).",
      asImplemented:
        "Evaluated by composite Gauss-Legendre quadrature in u = sqrt(tau), where the module docstring writes the same integral in tau with a factor tau^(-1/2) (1+tau)^(-1). Conduction only, loss-free.",
      kernels: ["eagar-tsai"],
    },
    {
      id: "goldak",
      label: "Goldak double-ellipsoid field (kernel goldak-half-space-v3)",
      latex: String.raw`T = T_0 + \frac{3\sqrt3\,P_f}{\pi\sqrt\pi\,\rho_k c_p}\int_0^\infty \frac{e^{-3y^2/s_b-3z^2/s_c}}{\sqrt{s_b\,s_c}}\Big[f_r\,\frac{e^{-3\hat x^2/s_r}}{\sqrt{s_r}}\Big(1-\mathrm{erf}\,\frac{a_r\hat x}{2\sqrt{\alpha\tau\,s_r}}\Big)+f_f\,\frac{e^{-3\hat x^2/s_f}}{\sqrt{s_f}}\Big(1+\mathrm{erf}\,\frac{a_f\hat x}{2\sqrt{\alpha\tau\,s_f}}\Big)\Big]d\tau`,
      plain:
        "T = T0 + 3 sqrt(3) Pf / (pi sqrt(pi) rho_k c_p) * integral over tau of exp(-3 y^2/s_b - 3 z^2/s_c) / sqrt(s_b s_c) * [ f_r exp(-3 xh^2/s_r)/sqrt(s_r) (1 - erf(a_r xh / (2 sqrt(alpha tau s_r)))) + f_f exp(-3 xh^2/s_f)/sqrt(s_f) (1 + erf(a_f xh / (2 sqrt(alpha tau s_f)))) ] dtau",
      symbols: [
        ["xh", "x + v tau"],
        ["s_i", "12 alpha tau + a_i^2, with a_i = b, c, a_f, a_r for i = b, c, f, r"],
        ["f_f, f_r", "2 a_f / (a_f + a_r) and 2 - f_f"],
        ["a_f, a_r, b, c", "semi-axes seeded from the beam radius r = d/2: a_f = r, a_r = 2r, b = c = r, each at least 4 um"],
      ],
      codeLocator: "python/goldak_solver.py:GoldakField (__init__ pref, temperature_C), goldak_fractions, seed_goldak_axes",
      sourceLocator: "Goldak et al. 1984 Metall. Trans. B, with the Fachinotti and Cardona 2008 erf correction (module docstring); Fachinotti eq. 15 and 18 named in the code comments.",
      asImplemented: "The time integral is done by quadrature in u = sqrt(tau). Q is the absorbed power P_f, not halved. The axes are a beam-based seed, not a fit to the pool.",
      kernels: ["goldak"],
    },
    {
      id: "width",
      label: "Melt pool width",
      latex: String.raw`W = \max\!\left(2\,y_h,\;0.55\,d\right),\qquad y_h=\max_{x_p}\ \max\{\,y : T(x_p,y,0)\ge T_{\mathrm{liq}}\}`,
      plain: "W = max(2 y_h, 0.55 d); y_h = largest y with T(x_p, y, 0) >= T_liq, maximised over the probe stations x_p",
      symbols: [
        ["y_h", "liquidus half-width found by bisection on the surface, m"],
        ["x_p", "probe stations along the track around the axial temperature peak"],
        ["T_liq", "liquidus, degC"],
      ],
      codeLocator: `${TS}:_liquidus_extent (half_w search; w_melt_m = max(2.0 * half_w, d_beam * 0.55))`,
      sourceLocator: "Defined in the code (numerical liquidus isotherm search). No external source is cited.",
      asImplemented:
        "The 0.55 d floor is a screening width floor. When extentStatus is not computed the width is not a computed isotherm (see the extent status and note above).",
    },
    {
      id: "length",
      label: "Melt pool length",
      latex: String.raw`L = x_f + x_r,\qquad T(x_{\mathrm{peak}}+x_f,0,0)=T_{\mathrm{liq}},\quad T(x_{\mathrm{peak}}-x_r,0,0)=T_{\mathrm{liq}}`,
      plain: "L = x_f + x_r, where the liquidus is crossed on the axis y = z = 0 at distances x_f ahead and x_r behind the axial temperature peak",
      symbols: [
        ["x_peak", "location of the axial temperature maximum, m"],
        ["x_f, x_r", "front and rear liquidus distances on the axis, m"],
      ],
      codeLocator: `${TS}:_liquidus_extent (front_rel, rear_rel; l_melt_m = max(x_front + x_rear, d_beam), then front and rear floors)`,
      sourceLocator: "Defined in the code (numerical liquidus isotherm search). No external source is cited.",
      asImplemented: "The length has a floor of one beam diameter, and the front and rear parts have floors of 0.35 r and 0.8 r.",
    },
    {
      id: "depth",
      label: "Melt pool depth",
      latex: String.raw`D = \max\!\left(d_{\mathrm{iso}},\;e\right),\qquad d_{\mathrm{iso}}=\max_{x_p}\ \max\{\,z : T(x_p,0,z)\ge T_{\mathrm{liq}}\},\quad d_{\mathrm{iso}}\ge 4\,\mu\mathrm{m}`,
      plain: "D = max(d_iso, e); d_iso = largest z with T(x_p, 0, z) >= T_liq, maximised over the probe stations; d_iso is at least 4 um",
      symbols: [
        ["d_iso", "conduction liquidus depth, m"],
        ["e", "Fabbro keyhole depth, m (zero below dH/hs 15)"],
      ],
      codeLocator: `${TS}:calculate_meltpool_physics (d_melt_m = max(d_iso, fabbro["depth_m"])) and ${TS}:_liquidus_extent (d_iso)`,
      sourceLocator: "Code comment (P1): one depth path for every kernel, Fabbro 2020 eq. 6 to 7 and Sec. 3 reading.",
    },
    {
      id: "fabbro",
      label: "Fabbro keyhole depth leg",
      latex: String.raw`e = s\,\frac{A\,P}{k_s\,(T_v-T_0)\,(m\,\mathrm{Pe}+n)},\quad \mathrm{Pe}=\frac{v\,d}{2\,\alpha_s},\quad m=2.4,\ n=3,\qquad s=\begin{cases}0 & \Delta H/h_s<15\\ (\Delta H/h_s-15)/15 & 15\le \Delta H/h_s<30\\ 1 & \Delta H/h_s\ge 30\end{cases}`,
      plain:
        "e = s * A P / (k_s (T_v - T_0) (m Pe + n)); Pe = v d / (2 alpha_s); m = 2.4; n = 3; s = 0 for dH/hs < 15, (dH/hs - 15)/15 for 15 to 30, 1 above 30",
      symbols: [
        ["e", "keyhole depth, m"],
        ["A", "flat-surface absorptivity (keyhole absorptivity A(R) is not modelled)"],
        ["P", "laser power, W"],
        ["k_s, alpha_s", "solid conductivity (W/m/K) and solid diffusivity k_s/(rho c_p,s) (m^2/s)"],
        ["T_v", "boiling point of the material authority, degC (an unsourced authority value in the code)"],
        ["Pe", "Peclet number, dimensionless"],
        ["dH/hs", "normalised enthalpy, dimensionless"],
      ],
      codeLocator:
        "python/fabbro_keyhole.py:fabbro_keyhole_depth_m, called from python/lpbf_thermal_solver.py:calculate_meltpool_physics with P_laser, A_fabbro, k_s, alpha_solid. Clamps in the function: A in [0.02, 0.99], T_v - T_0 at least 50 K.",
      sourceLocator: "Fabbro 2020, Appl. Sci. 10, 1487, doi 10.3390/app10041487, eq. 2; m = 2.4, n = 3 for 2 <= Pe <= 10 (Sec. 2.1).",
      asImplemented:
        "The ramp s from 15 to 30 is an uncited screening heuristic, not part of Fabbro. m and n are used outside 2 <= Pe <= 10 too (keyholeModel.pecletInFitRange says whether the fit range holds).",
    },
    {
      id: "fallback",
      label: "Fallback width scale when no liquidus extent is resolved",
      latex: String.raw`w_a=\sqrt{\frac{8}{\pi\,\mathrm{e}}\,\frac{P_f}{\rho_k\,c_p\,\max(50,\,T_{\mathrm{liq}}-T_0)\,v}},\qquad W_{fb}=\sqrt{w_a^2+(0.65\,d)^2},\qquad y_h\ge \frac{W_{fb}}{2},\ d_{\mathrm{iso}}\ge y_h`,
      plain:
        "w_a = sqrt((8/(pi exp(1))) Pf / (rho_k c_p max(50, T_liq - T0) v)); W_fb = sqrt(w_a^2 + (0.65 d)^2); used only when extentStatus is heuristic-width-fallback: half-width at least W_fb/2 and depth at least the half-width",
      symbols: [
        ["w_a", "high-speed Rosenthal width scale, m (also seeds the search box)"],
        ["e (upright)", "Euler's number 2.718..., not the keyhole depth e"],
      ],
      codeLocator: `${TS}:calculate_meltpool_physics (w_analytical) and ${TS}:_liquidus_extent (heuristic-width-fallback branch)`,
      sourceLocator: "Code comment: Rosenthal symmetry, King 2014 Sec. 5.2 (d <= w/2 in conduction mode). The 8/(pi e) scale and the 0.65 factor carry no citation in the code.",
      asImplemented: "Applies only when extentStatus is heuristic-width-fallback; the geometry is then not a computed isotherm.",
    },
    {
      id: "ved",
      label: "Volumetric energy density",
      latex: String.raw`\mathrm{VED} = \frac{P}{v\,h\,t}`,
      plain: "VED = P / (v * h * t)",
      symbols: [
        ["VED", "J/mm^3"],
        ["P", "W"],
        ["v", "mm/s"],
        ["h, t", "hatch spacing and layer thickness, mm"],
      ],
      codeLocator: `${TS}:calculate_meltpool_physics (ved_J_mm3 = P_laser / (scan_speed_mm_s * hatch_mm * layer_mm))`,
      sourceLocator: "Standard definition; the code cites no source. VED is not used as the sole criterion in the verdict.",
    },
  ],
};

const ENTHALPY_GATES: Explainer = {
  id: "enthalpy-gates",
  title: "How the normalized enthalpy, keyhole gate and lack-of-fusion gate are calculated",
  summary:
    "The same normalized enthalpy and the same Tang check are applied at the operating point and in every cell of the process window. The keyhole gate is a regime label on dH/hs, not a porosity claim. Screening only, not experimentally validated.",
  inputs: [
    { symbol: "dH/hs", label: "normalized enthalpy served", unit: "", path: "processParameters.normalizedEnthalpy" },
    { symbol: "A_idx", label: "index-convention absorptivity", unit: "", path: "processParameters.indexAbsorptivity" },
    { symbol: "P", label: "laser power", unit: "W", path: "processParameters.laserPower_W" },
    { symbol: "v", label: "scan speed", unit: "mm/s", path: "processParameters.scanSpeed_mm_s" },
    { symbol: "d", label: "beam diameter (1/e^2)", unit: "um", path: "processParameters.beamDiameter_um" },
    { symbol: "T_0", label: "preheat", unit: "degC", path: "processParameters.preheatTemp_C" },
    { symbol: "T_liq", label: "liquidus", unit: "degC", path: "thermalSlices.liquidus_C" },
    { symbol: "k_s", label: "solid conductivity", unit: "W/m/K", path: "processParameters.solidConductivity_W_mK" },
    { symbol: "c_K", label: "keyhole cut used for this alloy", unit: "", path: "meltPoolGeometry.regimeKeyholeThreshold" },
    { symbol: "regime", label: "regime served", unit: "", path: "meltPoolGeometry.regime" },
    { symbol: "h", label: "hatch spacing", unit: "um", path: "processParameters.hatchSpacing_um" },
    { symbol: "t", label: "layer thickness", unit: "um", path: "processParameters.layerThickness_um" },
    { symbol: "W", label: "melt pool width served", unit: "um", path: "meltPoolGeometry.width_um" },
    { symbol: "D", label: "melt pool depth served", unit: "um", path: "meltPoolGeometry.depth_um" },
    { symbol: "h/W", label: "hatch over width", unit: "", path: "defectDiagnostics.hOverW" },
    { symbol: "t/D", label: "layer over depth", unit: "", path: "defectDiagnostics.tOverD" },
    { symbol: "Tang", label: "Tang index served", unit: "", path: "defectDiagnostics.tangIndex_hW_tD" },
    { symbol: "LoF", label: "lack-of-fusion status served", unit: "", path: "defectDiagnostics.lackOfFusionStatus" },
  ],
  notes: [
    { label: "Regime thresholds and their stated transfer caveats", path: "meltPoolGeometry.regimeBasis" },
    { label: "Keyhole cut basis for this alloy", path: "meltPoolGeometry.regimeKeyholeCutBasis" },
    { label: "Alloy note", path: "meltPoolGeometry.regimeMaterialNote" },
    { label: "Lack-of-fusion margin note", path: "defectDiagnostics.lackOfFusionMarginBasis" },
  ],
  equations: [
    {
      id: "enthalpy",
      label: "Normalized enthalpy",
      latex: String.raw`\frac{\Delta H}{h_s}=\frac{A_{\mathrm{idx}}\,P}{h_s\,\sqrt{\pi\,\alpha_s\,v\,r^{3}}},\qquad h_s=\rho\,c_{p,s}\,\max\!\left(50,\,T_{\mathrm{liq}}-T_0\right),\quad \alpha_s=\frac{k_s}{\rho\,c_{p,s}},\quad r=\frac{d}{2}`,
      plain:
        "dH/hs = A_idx P / (hs sqrt(pi alpha_s v r^3)); hs = rho c_p,s max(50, T_liq - T0); alpha_s = k_s / (rho c_p,s); r = d/2",
      symbols: [
        ["A_idx", "index-convention absorptivity, dimensionless (always the flat value, also when the ray tracer is requested)"],
        ["P", "laser power, W"],
        ["rho, c_p,s", "room-temperature density (kg/m^3) and solid specific heat (J/kg/K)"],
        ["alpha_s", "solid thermal diffusivity, m^2/s"],
        ["v", "scan speed, m/s"],
        ["r", "1/e^2 beam radius, m"],
        ["T_liq, T_0", "liquidus and preheat, degC (the difference is floored at 50 K)"],
      ],
      codeLocator: `${TS}:calculate_meltpool_physics (enthalpy_denom, normalized_enthalpy)`,
      sourceLocator: "King et al. 2014, doi 10.1016/j.jmatprotec.2014.06.005, Eq. (2.6), Hann calibration, pi inside the root (code comment).",
      asImplemented:
        "The repo convention differs from King's calibration: r is the 1/e^2 radius (King sigma = r/2), h_s uses T_liq - T_0, and the diffusivity is the solid one. The 15 and 20 thresholds are derived in this convention.",
    },
    {
      id: "regime",
      label: "Regime and keyhole gate",
      latex: String.raw`\text{regime}=\begin{cases}\text{keyhole mode} & \Delta H/h_s\ge c_K\\ \text{transition} & 15\le \Delta H/h_s< c_K\\ \text{conduction} & \Delta H/h_s<15\end{cases}\qquad c_K=20\ (13.6\text{ for Inconel 625})`,
      plain: "keyhole mode if dH/hs >= c_K; transition if 15 <= dH/hs < c_K; conduction if dH/hs < 15; c_K = 20 (13.6 for Inconel 625)",
      symbols: [
        ["c_K", "keyhole cut of the alloy, dimensionless"],
        ["15", "transition cut (ENTHALPY_TRANSITION)"],
      ],
      codeLocator: `${TS}:classify_enthalpy_regime, regime_keyhole_cut, ENTHALPY_TRANSITION, ENTHALPY_KEYHOLE, ENTHALPY_KEYHOLE_IN625; the process-window verdict reads the same label in python/lpbf_build_job_solver.py:compose_verdict (_keyhole_mode)`,
      sourceLocator:
        "Cunningham et al. 2019 Fig. 3A (cut 15: blue line, 13.0 to 16.9 in app units along speed; cut 20: red line, 17.3 to 20.0); King et al. 2014 30 +/- 4 converted to this convention (code comments above ENTHALPY_TRANSITION). Inconel 625: fitted on 56 NIST mds2-2923 tracks (code comment above ENTHALPY_KEYHOLE_IN625).",
      asImplemented:
        "The cut 20 is a provisional screening choice. It is transferred, not derived, for IN718 and AlSi10Mg. Keyhole mode is a regime label, not a porosity claim. See the thresholds and caveats text above, taken from the result.",
    },
    {
      id: "tang",
      label: "Lack-of-fusion gate (Tang criterion)",
      latex: String.raw`\left(\frac{h}{W}\right)^{2}+\left(\frac{t}{D}\right)^{2}\le 1\ \Rightarrow\ \text{pass},\qquad >1\ \Rightarrow\ \text{fail (lack of fusion)}`,
      plain: "(h/W)^2 + (t/D)^2 <= 1 passes; above 1 fails (lack of fusion)",
      symbols: [
        ["h", "hatch spacing, um (at least 1)"],
        ["t", "layer thickness, um (at least 1)"],
        ["W, D", "served melt pool width and depth, um (each at least 1 in the ratio)"],
      ],
      codeLocator: `${TS}:calculate_meltpool_physics (section 9A: h_over_w, t_over_d, lof_criterion_val, lof_status); the same expression per grid cell in the process-window map section`,
      sourceLocator: "Tang, Pistorius and Beuth 2017 as quoted in Harkin 2023 Eq. 5 (code comment and TANG_CRITERION_BASIS in python/lpbf_build_job_solver.py); the primary is not in the library.",
      asImplemented:
        "Applied to modelled geometry, not measured geometry. Harkin 2023 Eq. 9 to 11 find the unit value problematic for analytic geometry (Ti-6Al-4V, one machine). An index above 0.80 is only a margin advisory (unsourced threshold). With a keyhole-index depth that is biased low, a fail can be a model artefact.",
    },
    {
      id: "verdict",
      label: "How the gates set the process-window verdict",
      latex: String.raw`\text{verdict}=\begin{cases}\text{do-not-print} & \text{Tang index}>1\\ \text{risky} & \text{keyhole mode}\\ \text{printable} & \text{otherwise}\end{cases}\qquad(\text{inconclusive if the geometry is not resolved or a gate input is null})`,
      plain: "do-not-print if the Tang index is above 1; otherwise risky if the regime is keyhole mode; otherwise printable; inconclusive if the geometry is not resolved or a gate input is null",
      symbols: [["verdict", "screening verdict of the process-window map cell or the build job, not a print recommendation"]],
      codeLocator: "python/lpbf_build_job_solver.py:compose_verdict (P7a ladder); python/lpbf_process_window.py evaluates calculate_meltpool_physics then compose_verdict per cell",
      sourceLocator: "Defined in the code (P7a, 2026-10-11): sourced criteria only. The 0.80 Tang margin, the level 30 and the balling band are advisories that do not change the verdict.",
    },
  ],
};

export const CALCULATION_EXPLAINERS: Readonly<Record<string, Explainer>> = {
  [MELTPOOL_GEOMETRY.id]: MELTPOOL_GEOMETRY,
  [ENTHALPY_GATES.id]: ENTHALPY_GATES,
};

/** Equations of an explainer that apply to the result's kernel (kernel-specific ones only when the kernel is known). */
export function equationsForKernel(explainer: Explainer, kernel: KernelId | null): ExplainerEquation[] {
  return explainer.equations.filter((eq) => !eq.kernels || (kernel !== null && eq.kernels.includes(kernel)));
}
