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
  /** Show only for these alloy ids (the result's alloyId). */
  alloys?: readonly string[];
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
        ["a_f, a_r, b, c", "semi-axes seeded from the beam radius r = max(d/2, 8 um): a_f = r, a_r = 2r, b = c = r (the field also floors each axis at 4 um)"],
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

const EVAP = "python/lpbf_ti64_evaporation.py";
const EVAP_SPEC = "docs/research/SPEC_ti64_evaporative_cpu_2026-10-20.md";

const TI64_EVAPORATION: Explainer = {
  id: "ti64-evaporation",
  title: "How the Ti-6Al-4V evaporative surface model is calculated",
  summary:
    "A fixed-surface Ti-species vapour law removes energy at the top face and defines a recoil pressure there. The first time that recoil exceeds the capillary pressure latches onset, after which depth, length and volume are withheld. Uncalibrated estimate, not experimentally validated.",
  inputs: [
    { symbol: "T_v", label: "vaporization temperature (Gan 2021 SI Table 1, Ti)", unit: "K", path: "provenance.vaporSource.vaporizationTemperature_K" },
    { symbol: "L_v", label: "latent heat of vaporization", unit: "J/kg", path: "provenance.vaporSource.latentHeat_J_kg" },
    { symbol: "M", label: "molar mass", unit: "kg/mol", path: "provenance.vaporSource.molarMass_kg_mol" },
    { symbol: "R", label: "gas constant", unit: "J/mol/K", path: "provenance.vaporSource.gasConstant_J_molK" },
    { symbol: "p_ref", label: "reference pressure (declared convention)", unit: "Pa", path: "provenance.vaporSource.referencePressure_Pa" },
    { symbol: "T_low", label: "bridge start (declared scenario)", unit: "K", path: "provenance.inputs.evaporation.transitionLow_K" },
    { symbol: "T_high", label: "bridge end, high law above (declared scenario)", unit: "K", path: "provenance.inputs.evaporation.transitionHigh_K" },
    { symbol: "p_amb", label: "ambient pressure (declared scenario)", unit: "Pa", path: "provenance.inputs.evaporation.ambientPressure_Pa" },
    { symbol: "beta", label: "return fraction (declared scenario)", unit: "", path: "provenance.inputs.evaporation.returnFraction" },
    { symbol: "T_max", label: "scenario temperature limit (declared)", unit: "K", path: "provenance.inputs.evaporation.maxTemperature_K" },
    { symbol: "sigma", label: "surface tension (declared scalar, optional)", unit: "N/m", path: "provenance.inputs.evaporation.surfaceTension_N_m" },
    { symbol: "d", label: "beam diameter (1/e^2)", unit: "um", path: "provenance.inputs.beamDiameter_um" },
    { symbol: "T_peak", label: "peak temperature of this run", unit: "K", path: "peakTemperature_K" },
    { symbol: "onset", label: "onset latched", unit: "", path: "gate.onset" },
    { symbol: "t_onset", label: "first onset time", unit: "s", path: "gate.firstOnsetTime_s" },
    { symbol: "unresolved", label: "geometry unresolved (no surface tension declared)", unit: "", path: "gate.unresolvedGeometry" },
  ],
  notes: [
    { label: "Transition basis", path: "provenance.vaporSource.transitionBasis" },
    { label: "Reference pressure basis", path: "provenance.vaporSource.referencePressureBasis" },
    { label: "Temperature limit basis", path: "provenance.vaporSource.temperatureLimitBasis" },
    { label: "Surface tension basis", path: "provenance.vaporSource.surfaceTensionBasis" },
    { label: "Temperature label", path: "temperatureLabel" },
    { label: "Diagnostic mass label", path: "diagnosticMassLabel" },
    { label: "Geometry refusal", path: "geometry.refusalReason" },
  ],
  equations: [
    {
      id: "vapour-pressure",
      label: "Saturation pressure above the bridge (T at or above T_high)",
      latex: String.raw`p_{\mathrm{sat}}(T)=p_{\mathrm{ref}}\exp\!\left[\frac{L_v M}{R}\left(\frac{1}{T_v}-\frac{1}{T}\right)\right]`,
      plain: "p_sat(T) = p_ref * exp( (L_v M / R) * (1/T_v - 1/T) )",
      symbols: [
        ["p_sat", "saturation pressure, Pa"],
        ["T", "surface temperature, K"],
        ["L_v M / R", "the Clausius constant (_CLAUSIUS_K), K"],
      ],
      codeLocator: EVAP + ":_high_law (saturation), _CLAUSIUS_K",
      sourceLocator:
        "Constants: Gan 2021 SI Table 1, Ti species (module docstring, SOURCE_PROFILE sourceId Gan2021-SI-Table1-Ti). The law is stated in " + EVAP_SPEC + " (For T>=high); the code cites no equation number for the Clausius-Clapeyron form.",
      asImplemented: "p_ref = 101325 Pa is a declared convention, not a source value. No species depletion and no composition evolution: Ti species only.",
    },
    {
      id: "mass-flux",
      label: "Evaporative mass flux (T at or above T_high)",
      latex: String.raw`j(T)=(1-\beta)\,p_{\mathrm{sat}}(T)\,\sqrt{\frac{M}{2\pi R\,T}}`,
      plain: "j(T) = (1 - beta) * p_sat(T) * sqrt( M / (2 pi R T) )",
      symbols: [
        ["j", "mass flux, kg/m^2/s"],
        ["beta", "return fraction, 0 <= beta < 1, declared"],
      ],
      codeLocator: EVAP + ":_high_law (mass)",
      sourceLocator: EVAP_SPEC + " (For T>=high: j=(1-beta)*psat*sqrt(M/(2*pi*R*T))). No equation number is cited in the code.",
    },
    {
      id: "recoil",
      label: "Recoil pressure (T at or above T_high)",
      latex: String.raw`p_r(T)=\frac{1+\beta}{2}\,p_{\mathrm{sat}}(T)`,
      plain: "p_r(T) = (1 + beta) / 2 * p_sat(T)",
      symbols: [["p_r", "recoil pressure at the surface, Pa (absolute, so it equals p_amb at and below T_low)"]],
      codeLocator: EVAP + ":_high_law (recoil)",
      sourceLocator: EVAP_SPEC + " (For T>=high: pr=(1+beta)*psat/2). No equation number is cited in the code.",
    },
    {
      id: "bridge",
      label: "Declared cubic Hermite bridge between T_low and T_high",
      latex: String.raw`y(T)=y_{\mathrm{low}}+u^{2}\,(a+b\,u),\quad u=\frac{T-T_{\mathrm{low}}}{T_{\mathrm{high}}-T_{\mathrm{low}}},\quad a=3\Delta-s,\ b=s-2\Delta,\quad \Delta=y(T_{\mathrm{high}})-y_{\mathrm{low}},\ s=(T_{\mathrm{high}}-T_{\mathrm{low}})\,\frac{dy}{dT}\Big|_{T_{\mathrm{high}}}`,
      plain:
        "y(T) = y_low + u^2 (a + b u); u = (T - T_low)/(T_high - T_low); a = 3 Delta - s; b = s - 2 Delta; Delta = y(T_high) - y_low; s = (T_high - T_low) dy/dT at T_high. For the mass flux y = j and y_low = 0. For the recoil pressure y = p_r and y_low = p_amb. At or below T_low: j = 0 and p_r = p_amb.",
      symbols: [
        ["y", "j for the mass flux, p_r for the recoil pressure"],
        ["y_low", "0 for j, p_amb for p_r"],
        ["dj/dT", "j (L_v M / (R T^2) - 1/(2 T)) at T_high"],
        ["dp_r/dT", "p_r L_v M / (R T^2) at T_high"],
      ],
      codeLocator: EVAP + ":_bridge_coefficients, validate_config (bridge coefficients), surface_state (bridge branch); slopes in _high_law",
      sourceLocator: "Declared matching construction following Gan 2021 Eqs 12 and 14 (SOURCE_PROFILE transitionBasis, " + EVAP_SPEC + ").",
      asImplemented: "Not the recovered fitting coefficients of the source. A bridge that would be negative or non-monotone is refused, never clipped. T_low and T_high are declared scenario inputs.",
    },
    {
      id: "heat-loss",
      label: "Evaporative heat loss at the top face",
      latex: String.raw`q_{\mathrm{ev}}=j(T)\,L_v,\qquad \text{top-cell volumetric rate reduced by } \frac{q_{\mathrm{ev}}}{\Delta x}`,
      plain: "q_ev = j(T) * L_v at the top face; the volumetric rate of the top cell is reduced by q_ev / dx",
      symbols: [
        ["q_ev", "evaporative heat flux, W/m^2"],
        ["dx", "cell size, m"],
      ],
      codeLocator:
        EVAP + ":surface_state (heat = mass * LATENT_HEAT_J_KG); python/lpbf_ti64_evaporative_solver.py:_accepted_step (passive[:, :, -1] -= (radiative_convective + vapor heat_flux) / dx)",
      sourceLocator: EVAP_SPEC + " (Top exposed face only: subtract q_evap=j*Lv divided by dx from volumetric rate).",
      asImplemented: "Top exposed face only. Fixed material mass and geometry are not reduced; the diagnostic emitted mass is not ablation.",
    },
    {
      id: "onset",
      label: "Onset criterion (capillary pressure against recoil)",
      latex: String.raw`\text{onset latches when } j>0 \text{ and } p_r-p_{\mathrm{amb}}\ \ge\ \frac{2\sigma}{r},\qquad r=\frac{d}{2}`,
      plain:
        "onset latches the first time j > 0 and p_r - p_amb >= 2 sigma / r, with r = d/2. If no sigma is declared, an active j > 0 latches unresolved geometry instead. A latch is never cleared.",
      symbols: [
        ["sigma", "declared surface tension, N/m (no default)"],
        ["r", "1/e^2 beam radius, m"],
      ],
      codeLocator: EVAP + ":update_onset (threshold = 2 sigma / radius, active = mass > 0)",
      sourceLocator: EVAP_SPEC + " (A1.1: active j and pr-pambient >= 2*sigma/r latch onset, including equality; r = diameter_1e2/2).",
      asImplemented:
        "A scenario criterion with a declared sigma, not a measured keyhole threshold. After onset or unresolved geometry, depth, length and volume are withheld; width and temperature keep their fixed-surface labels.",
    },
  ],
};

const RA = "python/lpbf_research_arm.py";
const P8_SPEC = "docs/research/SPEC_p8_research_arm_2026-10-14.md";

const P8_LINKED_DEPTH: Explainer = {
  id: "p8-linked-depth",
  title: "How the P8 linked melt depth is calculated",
  summary:
    "A cavity-balance hypothesis gives a keyhole depth e above an onset power P*. The depth of the liquidus below the cavity is then read from a point plus finite line source field and joined to the finite-Gaussian conduction depth by a maximum. A research hypothesis, not experimentally validated. Material constants (K, alpha, A0, T_v, L_v, M, T_l) are not part of the returned depth fields, so they are shown as symbols only.",
  inputs: [
    { symbol: "P", label: "laser power", unit: "W", path: "inputs.power_W" },
    { symbol: "v", label: "scan speed", unit: "mm/s", path: "inputs.speed_mm_s" },
    { symbol: "d", label: "beam diameter (1/e^2)", unit: "um", path: "inputs.beamDiameter_um" },
    { symbol: "T_0", label: "preheat", unit: "degC", path: "inputs.preheat_C" },
    { symbol: "P/P*", label: "power over onset power", unit: "", path: "p8.powerOverOnset" },
    { symbol: "D_linked", label: "linked melt depth served", unit: "um", path: "p8.linkedMeltDepth_um" },
    { symbol: "model", label: "model id", unit: "", path: "p8.modelId" },
  ],
  notes: [
    { label: "Hypothesis sentence", path: "p8.uiSentence" },
    { label: "Consistency note", path: "p8.consistencySentence" },
    { label: "Validation status", path: "p8.validationStatus" },
  ],
  equations: [
    {
      id: "threshold-temperature",
      label: "Recoil threshold temperature",
      latex: String.raw`T_{th}=\frac{T_v}{1-\ln\!\big(2/(1+\beta_r)\big)/c},\qquad c=\frac{L_v M}{R_g\,T_v},\quad \beta_r=0.2`,
      plain: "T_th = T_v / (1 - ln(2 / (1 + beta_r)) / c); c = L_v M / (R_g T_v); beta_r = 0.2",
      symbols: [
        ["T_th", "threshold temperature, K"],
        ["T_v, L_v, M", "vaporization temperature (K), latent heat (J/kg) and molar mass (kg/mol) of the material"],
        ["R_g", "8.31446261815324 J/mol/K"],
        ["beta_r", "condensation fraction, 0.2 (source scenario value)"],
      ],
      codeLocator: `${RA}:threshold_temperature`,
      sourceLocator: "Fabbro 2020 Appendix A Eqs A10 to A11, p. 20 (docstring of threshold_temperature); " + P8_SPEC + " section 4 item 3.",
      asImplemented: "Omits capillary curvature and hydrostatic load. The code refuses a non-positive denominator.",
    },
    {
      id: "onset-power",
      label: "Onset power",
      latex: String.raw`P^{*}=\frac{T_{th}-T_0}{G_T},\qquad G_T=\frac{\sqrt2\,A_0}{a\,K\,\pi^{3/2}}\,\arctan\!\sqrt{\frac{8\,\alpha}{v\,a}},\quad a=\frac{d}{2}`,
      plain: "P* = (T_th - T_0) / G_T; G_T = sqrt(2) A_0 / (a K pi^(3/2)) * arctan( sqrt(8 alpha / (v a)) ); a = d/2",
      symbols: [
        ["P*", "onset power, W"],
        ["G_T", "centre temperature rise per watt of laser power at dwell t = a/v, K/W"],
        ["A_0", "flat absorptivity"],
        ["K, alpha", "conductivity (W/m/K) and diffusivity (m^2/s) of the resolved material"],
        ["a", "Gaussian 1/e^2 radius, m"],
      ],
      codeLocator: `${RA}:_kernel_onset_power (method trapp2017, the default onset event 'dwell'), onset_power`,
      sourceLocator: "Trapp 2017 Eq. 3 p. 346 and Eq. 2 p. 345 (docstring of _kernel_onset_power); corrected normalization in " + P8_SPEC + " Amendment 2 B1.",
      asImplemented:
        "Not the verbatim Trapp equation: the prefactor was corrected for the 1/e^2 radius convention (Amendment 2 B1). It is a transient conduction estimate at dwell a/v, not the exact moving peak. The research sensitivity onset events O1 and O3 are not shown.",
    },
    {
      id: "cavity-balance",
      label: "Cavity balance and the keyhole depth e",
      latex: String.raw`K\,(T_v-T_0)\,g(\mathrm{Pe})\,e=A_{\mathrm{tot}}\!\left(\frac{e}{d}\right)\max(P-P^{*},0),\qquad \mathrm{Pe}=\frac{v\,d}{2\,\alpha}`,
      plain: "K (T_v - T_0) g(Pe) e = A_tot(e/d) * max(P - P*, 0); Pe = v d / (2 alpha); e = 0 when P <= P*",
      symbols: [
        ["e", "cavity depth, m; the lowest strictly stable root R = e/d of R / A_tot(R) = S is selected"],
        ["S", "max(P - P*, 0) / (d K (T_v - T_0) g(Pe))"],
        ["Pe", "Peclet number, dimensionless"],
        ["A_tot", "total absorptance of the beam, dimensionless"],
      ],
      codeLocator: `${RA}:energy_balance_residual (K * delta_Tv * g * e - A_tot * max(0, P - P_star)), solve_e (S, root scan), cavity_values (closure cylinder_exact)`,
      sourceLocator: "Fabbro 2020 Eqs 13 and 14, pp. 7 to 8 motivate the shifted law (docstring of energy_balance_residual); " + P8_SPEC + " section 4 item 4.",
      asImplemented:
        "Replacing Fabbro's front absorptance A_F by the whole-beam A_tot and pairing it with the exact cylinder response is an inferred hypothesis. The root choice is a quasi-static convention, not measured hysteresis. Not a free-boundary energy or flow solution.",
    },
    {
      id: "thermal-g",
      label: "Thermal response of the moving isothermal cylinder",
      latex: String.raw`g(\mathrm{Pe})=-2\pi\lambda\left[I_0(\lambda)^2\,\frac{K_0'(\lambda)}{K_0(\lambda)}+2\sum_{n=1}^{24}(-1)^n\,I_n(\lambda)^2\,\frac{K_n'(\lambda)}{K_n(\lambda)}\right],\qquad \lambda=\frac{\mathrm{Pe}}{2}`,
      plain: "g(Pe) = -2 pi lambda * [ I_0(lambda)^2 K_0'(lambda)/K_0(lambda) + 2 * sum for n = 1 to 24 of (-1)^n I_n(lambda)^2 K_n'(lambda)/K_n(lambda) ]; lambda = Pe / 2",
      symbols: [
        ["I_n, K_n", "modified Bessel functions of the first and second kind"],
        ["K_n'", "derivative of K_n"],
      ],
      codeLocator: `${RA}:thermal_g (closure cylinder_exact, 24 harmonics, valid for 0.01 <= Pe <= 10)`,
      sourceLocator: "Derived Bessel solution of Fabbro 2018 Eq. 4 (docstring of thermal_g); " + P8_SPEC + " section 4 item 2.",
      asImplemented: "Our evaluated series, not an equation printed in Fabbro. The 24-term sum is checked against 32 terms to a relative difference of 1e-8.",
    },
    {
      id: "absorptance",
      label: "Total absorptance of the beam with a conical cavity",
      latex: String.raw`A_{\mathrm{tot}}(R)=w\,A_{\mathrm{cav}}(R)+p\,A_0,\quad A_{\mathrm{cav}}(R)=\frac{1}{w}\sum_{n\ge0}A_0\,(1-A_0)^n\left[1-e^{-8\,b_n(R)^2}\right],\quad p=e^{-2},\ w=1-p,\ R=\frac{e}{d}`,
      plain: "A_tot(R) = w A_cav(R) + p A_0; A_cav(R) = (1/w) * sum for n >= 0 of A_0 (1 - A_0)^n [1 - exp(-8 b_n(R)^2)]; p = exp(-2); w = 1 - p; R = e/d",
      symbols: [
        ["b_n(R)", "largest launch radius, in units of d, of rays that still make at least n + 1 wall hits in an ideal cone with wall slope z/(2R), from the ray trace"],
        ["A_0", "flat absorptivity, applied at every reflection"],
        ["w, p", "Gaussian power fraction inside and outside the 1/e^2 radius"],
      ],
      codeLocator: `${RA}:total_absorptance, specular_cone, cone_reflection_radii`,
      sourceLocator: "Our derivation (P3 DER section 3.5), motivated by Kaplan 1994 Eqs 22, 24 to 27 and Fabbro 2020 Sec. 4.1 to 4.2 (" + P8_SPEC + " section 4 item 1).",
      asImplemented:
        "A_cav(0) = A_0. The sum is the exact survival integral of the ray-trace escape count, not a fitted table. Coherent, roughness, angle-dependent Fresnel, plasma and an evolving aperture are absent.",
    },
    {
      id: "partition",
      label: "Power split between surface and cavity",
      latex: String.raw`P\le P^{*}:\ Q_s=A_0P,\ Q_c=0;\qquad P>P^{*}:\ Q_s=A_0\,(pP+wP^{*}),\ Q_c=w\,(A_{\mathrm{cav}}P-A_0P^{*});\qquad Q=Q_s+Q_c,\ \chi=\frac{Q_c}{Q}`,
      plain: "If P <= P*: Q_s = A_0 P and Q_c = 0. If P > P*: Q_s = A_0 (p P + w P*) and Q_c = w (A_cav P - A_0 P*). Q = Q_s + Q_c; chi = Q_c / Q",
      symbols: [
        ["Q_s", "power deposited at the surface, W"],
        ["Q_c", "power deposited along the cavity, W"],
        ["Q", "absorbed power, W"],
        ["chi", "cavity power fraction"],
      ],
      codeLocator: `${RA}:link_values (qs, qc, qabs, chi)`,
      sourceLocator: P8_SPEC + " section 5 (conservative spatial hypothesis, MELT Amendment 1).",
      asImplemented: "Not a published universal allocation law. It makes the photon ledger close but does not reconcile the cavity-wall thermal ledger.",
    },
    {
      id: "field",
      label: "Temperature field below the cavity (above onset)",
      latex: String.raw`\Theta(x,0,z)=(1-\chi)\,\frac{Q\,e^{-\beta(x+r_0)}}{2\pi K\,r_0}+\chi\,\frac{Q}{4\pi K\,e}\int_{z-e}^{z+e}\frac{e^{-\beta\,(x+\sqrt{x^2+w^2})}}{\sqrt{x^2+w^2}}\,dw,\quad r_0=\sqrt{x^2+z^2},\ \beta=\frac{v}{2\alpha}`,
      plain: "Theta(x, 0, z) = (1 - chi) Q exp(-beta (x + r_0)) / (2 pi K r_0) + chi Q / (4 pi K e) * integral from z - e to z + e of exp(-beta (x + sqrt(x^2 + w^2))) / sqrt(x^2 + w^2) dw; r_0 = sqrt(x^2 + z^2); beta = v / (2 alpha)",
      symbols: [
        ["Theta", "temperature rise above T_0, K"],
        ["x", "trailing coordinate, m (searched on -L <= x <= 0)"],
        ["w", "integration variable along the line source, m"],
      ],
      codeLocator: `${RA}:melt_depth_from_e (field, observable envelope; log-coordinate Gauss-Legendre of order 32, then 64)`,
      sourceLocator: "Our finite-domain derivation (P3 DER section 6.2); Kaplan 1994 p. 1805 superposition motivates it (docstring of melt_depth_from_e; " + P8_SPEC + " section 5).",
      asImplemented:
        "A uniform finite vertical line plus its Neumann image plus a surface point. Not an etched-depth law validated by the cited papers. It omits flow and transported enthalpy (Rai 2007).",
    },
    {
      id: "model-depth",
      label: "Depth of the liquidus below the cavity",
      latex: String.raw`D_{\mathrm{model}}=\sup\left\{z\in(e,\,e+L]:\ \max_{-L\le x\le0}\Theta(x,0,z)\ge T_l-T_0\right\},\qquad L=\frac{Q}{2\pi K\,(T_l-T_0)}`,
      plain: "D_model = largest z in (e, e + L] with max over -L <= x <= 0 of Theta(x, 0, z) >= T_l - T_0; L = Q / (2 pi K (T_l - T_0))",
      symbols: [
        ["T_l", "liquidus, K"],
        ["L", "bracket length, m"],
      ],
      codeLocator: `${RA}:melt_depth_from_e (bisection on z with the trailing-x maximum), _peak_temperature; used in link_values`,
      sourceLocator: P8_SPEC + " section 5 (Dmodel numerical method).",
      asImplemented: "The depth is published only if the order 64 result agrees with the order 32 result to 1 percent. Thin tip shells are refused, never set to e.",
    },
    {
      id: "conduction-depth",
      label: "Finite-Gaussian conduction depth",
      latex: String.raw`D_{\mathrm{cond}}=\sup\left\{z:\ \max_{x\le0}\Theta_G(x,z)\ge T_l-T_0\right\},\quad \Theta_G=\frac{\sqrt2\,A_0P}{\pi^{3/2}K\,a}\int_0^{\pi/2}\exp\!\left[-\frac{2\left(x/a+\frac{v a}{8\alpha}\tan^2\vartheta\right)^2}{1+\tan^2\vartheta}-\frac{2z^2}{a^2\tan^2\vartheta}\right]d\vartheta`,
      plain: "D_cond = largest z with max over x <= 0 of Theta_G(x, z) >= T_l - T_0; Theta_G = sqrt(2) A_0 P / (pi^(3/2) K a) * integral from 0 to pi/2 of exp( -2 (x/a + (v a / (8 alpha)) tan^2(theta))^2 / (1 + tan^2(theta)) - 2 z^2 / (a^2 tan^2(theta)) ) d theta; zero if the Gaussian does not reach the liquidus",
      symbols: [
        ["Theta_G", "temperature rise of the moving Gaussian source on y = 0, K"],
        ["theta", "integration angle"],
        ["a", "Gaussian 1/e^2 radius, m"],
      ],
      codeLocator: `${RA}:gaussian_floor`,
      sourceLocator: "Eagar and Tsai 1983 field physics with the independent extractor p8-gaussian-liquidus-envelope-v2 (" + P8_SPEC + " Amendment 2 B5); module METHOD_SETTINGS floorExtractorId.",
      asImplemented: "The code writes the Eagar-Tsai integral in tan substitution form with a = d/2. If the finite Gaussian never reaches the liquidus the depth is exactly 0 (resolved no melting). No 4 um floor is imposed.",
    },
    {
      id: "linked-depth",
      label: "Linked melt depth",
      latex: String.raw`D_{\mathrm{linked}}=\begin{cases}D_{\mathrm{cond}} & P\le P^{*}\\ \max\!\left(D_{\mathrm{model}},\,D_{\mathrm{cond}}\right) & P>P^{*}\end{cases}`,
      plain: "D_linked = D_cond if P <= P*; D_linked = max(D_model, D_cond) if P > P*",
      symbols: [["D_linked", "linked melt depth, served as linkedMeltDepth_um"]],
      codeLocator: `${RA}:link_values (linkDispatch, linkedMeltDepth_um = max(depth, floor))`,
      sourceLocator: P8_SPEC + " section 5 and Amendment 2 B5.",
      asImplemented:
        "The max is an explicit hypothesis safeguard. The above-onset field keeps a surface point where the below-onset leg uses a finite Gaussian, so the depth map need not be continuous at P*. This is disclosed, not smoothed.",
    },
  ],
};

const SE = "python/lpbf_solidification_estimates.py";
const SE_SPEC = "docs/research/SPEC_solidification_2026-10-14.md";

const SOLIDIFICATION_ESTIMATES: Explainer = {
  id: "solidification-estimates",
  title: "How G, R, cooling rate, G/R and the dendrite spacings are calculated",
  summary:
    "G, R, cooling rate and G/R are computed at 32 points on the rear solidifying liquidus branch of the conduction field (plane y = 0) and the weighted median is shown. The spacing laws are then evaluated at every point, before taking the median, and only where a capillary screening gate passes. Each value is an uncalibrated estimate from a conduction-field surrogate, not a measurement.",
  inputs: [
    { symbol: "alloy", label: "alloy", unit: "", path: "alloyId" },
    { symbol: "kernel", label: "heat source model", unit: "", path: "heatSourceModel" },
    { symbol: "P", label: "laser power", unit: "W", path: "request.process.power_W" },
    { symbol: "v", label: "scan speed", unit: "mm/s", path: "request.process.speed_mm_s" },
    { symbol: "d", label: "beam diameter", unit: "um", path: "request.process.beamDiameter_um" },
    { symbol: "T_0", label: "preheat", unit: "degC", path: "request.process.preheat_C" },
    { symbol: "G", label: "thermal gradient (weighted median served)", unit: "K/m", path: "quantities.thermalGradient.value" },
    { symbol: "R", label: "solidification rate (weighted median served)", unit: "m/s", path: "quantities.normalSpeed.value" },
    { symbol: "G R", label: "cooling rate (weighted median served)", unit: "K/s", path: "quantities.coolingRate.value" },
    { symbol: "G/R", label: "gradient over rate (weighted median served)", unit: "K s/m^2", path: "quantities.gOverR.value" },
    { symbol: "lambda_1", label: "primary dendrite arm spacing served", unit: "m", path: "quantities.pdas.value" },
    { symbol: "lambda_2", label: "secondary dendrite arm scale served", unit: "m", path: "quantities.sdas.value" },
  ],
  notes: [],
  equations: [
    {
      id: "gradient",
      label: "Thermal gradient at a front point",
      latex: String.raw`G=\lvert\nabla T\rvert=\sqrt{g_x^2+g_y^2+g_z^2},\qquad g_x\approx\frac{T(x{+}h)-T(x{-}h)}{2h}\ \ (\text{same for } g_y),\quad g_z\approx\begin{cases}\dfrac{T(z{+}h)-T(z{-}h)}{2h}&\text{interior}\\[1ex]\dfrac{T(z{+}h)-T(z)}{h}&\text{at the surface}\end{cases}`,
      plain: "G = |grad T| = sqrt(gx^2 + gy^2 + gz^2), with central differences of step h for gx and gy; gz is central in the interior and one-sided (T(z+h) - T(z)) / h at the surface",
      symbols: [
        ["T", "temperature of the conduction field of the requested kernel, K"],
        ["h", "difference step, m: one quarter of h_0, where h_0 = 2e-3 times the depth of the deepest liquidus point on the branch (at least 1e-9 m)"],
        ["g_x, g_y, g_z", "components of the gradient at the liquidus point, K/m"],
      ],
      codeLocator: `${SE}:gradient, sample_front, kinematics`,
      sourceLocator: "Ghosh et al. 2017, Modelling Simul. Mater. Sci. Eng. 25 065002, Sec. 3.1: the full Cartesian gradient norm (SRC_GHOSH_KINEMATICS in the code). The conduction field itself is the served kernel (Eagar and Tsai 1983 moving conduction framework).",
      asImplemented:
        "The points lie on the liquidus isotherm at y = 0 between the deepest liquidus point and the rear surface crossing, at midpoints of 32 equal-x cells. The field is a conduction-only surrogate: it does not include the keyhole cavity.",
    },
    {
      id: "rate",
      label: "Solidification rate, cooling rate and G/R",
      latex: String.raw`R=\frac{v\,g_x}{G},\qquad \dot T = G\,R = v\,g_x,\qquad \frac{G}{R}=\frac{G^{2}}{v\,g_x}\qquad(\text{only where } g_x>0)`,
      plain: "R = v gx / G; cooling rate = G R = v gx; G/R = G^2 / (v gx); only where gx > 0, otherwise the point is refused",
      symbols: [
        ["R", "normal speed of the liquidus front, m/s (the scan speed projected on the gradient direction)"],
        ["v", "scan speed, m/s"],
        ["cooling rate", "K/s"],
        ["G/R", "K s/m^2"],
      ],
      codeLocator: `${SE}:kinematics (R = v * gx / G, cooling = v * gx, g_over_r = G * G / (v * gx))`,
      sourceLocator: "Ghosh et al. 2017 Sec. 3.1: normal projection of the scan velocity (SRC_GHOSH_KINEMATICS in the code).",
      asImplemented: "A point with a non-finite or zero gradient, or with g_x <= 0, is refused. G R equals v g_x is checked to a relative 1e-12 on every point.",
    },
    {
      id: "summary",
      label: "Value shown for G, R, cooling rate and G/R",
      latex: String.raw`\text{value}=\operatorname{median}_{w_i}\big(q_i\big),\qquad w_i=\text{chord length of cell } i \text{ along the liquidus edges},\quad q_i\in\{G_i,R_i,\dot T_i,(G/R)_i\}`,
      plain: "value = weighted median over the valid points i of the local value q_i (G_i, R_i, cooling_i, (G/R)_i), with weights w_i equal to the chord length of cell i along the liquidus edges; at least 3 valid points are needed",
      symbols: [
        ["q_i", "local value at point i"],
        ["w_i", "chord-length weight, m"],
      ],
      codeLocator: `${SE}:thermal_summary, summarize, weighted_median, sample_front (weight_m)`,
      sourceLocator: SE_SPEC + " Amendment 5 A5.2 (named in the code); module docstring of " + SE + ".",
      asImplemented: "The spatial spread (p10, p90, min, max) is kept separate and is not an uncertainty. Every quantity is computed per point first, never from the separate medians of G and R.",
    },
    {
      id: "capillary-gate",
      label: "Capillary screening gate on the spacing laws",
      latex: String.raw`\lambda_{\mathrm{cut}}=2\pi\sqrt{\frac{\Gamma}{P_f R/D-G}},\quad P_f=\frac{m\,c\,(1-k)}{k};\qquad \text{value kept only if } \lambda\ge\lambda_{\mathrm{cut}}`,
      plain: "lambda_cut = 2 pi sqrt( Gamma / (P_f R / D - G) ); P_f = m c (1 - k) / k; the spacing is kept only if it is at least lambda_cut. No value if P_f R / D - G <= 0 or R >= P_f D / (k Gamma)",
      symbols: [
        ["m, c, k", "liquidus slope (K/wt%), solute content (wt%) and partition coefficient of the alloy's named binary proxy"],
        ["D, Gamma", "liquid diffusivity (m^2/s) and Gibbs-Thomson coefficient (K m) of that proxy"],
        ["P_f", "freezing range of the proxy, K"],
        ["lambda_cut", "capillary screening limit, m"],
      ],
      codeLocator: `${SE}:capillary_cutoff, freezing_range, gated_spacing, PROXIES`,
      sourceLocator: "SPEC Amendment 7 item 1 (SRC_A7_CAPILLARY in the code): a declared one-sided quasi-static binary screening bound. Proxy constants and their locators are in PROXIES (for example Ghosh et al. 2017 Table 2 for Ni-5Nb).",
      asImplemented: "A screening bound of a named binary proxy, not a stability analysis of the real alloy. A refused point is dropped; with fewer than 3 retained points no value is shown and the reason is stated.",
    },
    {
      id: "spacing-ti64",
      label: "Dendrite arm spacings, Ti-6Al-4V",
      latex: String.raw`\lambda_1=(699-62\,w_{\mathrm{Al}})\,q^{-0.39}\ \mu\mathrm{m},\qquad \lambda_2=(366-33\,w_{\mathrm{Al}})\,q^{-0.40}\ \mu\mathrm{m},\qquad q=G\,R`,
      plain: "lambda_1 = (699 - 62 w_Al) q^-0.39 um; lambda_2 = (366 - 33 w_Al) q^-0.40 um; q = G R in K/s; w_Al = 6 wt% declared",
      symbols: [
        ["w_Al", "aluminium content, wt%; nominal 6 declared, no assay"],
        ["q", "local cooling rate G R, K/s"],
      ],
      codeLocator: `${SE}:raw_spacing, SPACING["ti6al4v"]`,
      sourceLocator: "Mizukami et al. 2020, ISIJ Int., doi 10.2355/isijinternational.ISIJINT-2020-089, Eq. 4 (primary) and Eq. 5 (secondary).",
      asImplemented: "Source domain: EB-remelted Ti alloy ingots, Al 2.9 to 5.7 wt%, cooling 1 to 100 K/s. LPBF cooling rates are far outside it. The law is refused if its bracket (699 - 62 w_Al, 366 - 33 w_Al) is not positive.",
      alloys: ["ti6al4v"],
    },
    {
      id: "spacing-alsi",
      label: "Dendrite arm spacings, AlSi10Mg",
      latex: String.raw`\lambda_1=165\,q^{-0.4}\ \mu\mathrm{m},\qquad \lambda_2=22\,(1000\,R)^{-2/3}\ \mu\mathrm{m},\qquad q=G\,R`,
      plain: "lambda_1 = 165 q^-0.4 um with q = G R in K/s; lambda_2 = 22 (1000 R)^(-2/3) um with R in m/s (1000 R is in mm/s)",
      symbols: [
        ["q", "local cooling rate G R, K/s"],
        ["1000 R", "solidification rate in mm/s"],
      ],
      codeLocator: `${SE}:raw_spacing, SPACING["alsi10mg"]`,
      sourceLocator: "Gandolfi et al. 2021, Metals 11, 1019, doi 10.3390/met11071019, PDF13 Eq. 1 (primary) and Eq. 2 (secondary, Al-10Si-0.45Mg).",
      asImplemented: "Source domain: directional casting, q 0.05 to 10.75 K/s and R 0.300 to 1.240 mm/s. Transferred to LPBF AlSi10Mg.",
      alloys: ["alsi10mg"],
    },
    {
      id: "spacing-316l",
      label: "Dendrite arm spacings, 316L",
      latex: String.raw`\lambda_1=80\,q^{-0.33}\ \mu\mathrm{m},\qquad \lambda_2=25\,q^{-0.28}\ \mu\mathrm{m},\qquad q=G\,R`,
      plain: "lambda_1 = 80 q^-0.33 um; lambda_2 = 25 q^-0.28 um; q = G R in K/s",
      symbols: [["q", "local cooling rate G R, K/s"]],
      codeLocator: `${SE}:raw_spacing, SPACING["ss316l"]`,
      sourceLocator: "Bunaziv et al. 2023, doi 10.1007/s00170-023-11567-y, PDF16/printed 926 Eq. 2 (primary) and PDF17/printed 927 Eq. 6 (secondary).",
      asImplemented: "Source domain: 316L laser cladding, cooling averaged from 1450 to 1350 C. The cooling-rate definition and the process are transferred.",
      alloys: ["ss316l"],
    },
    {
      id: "spacing-ni",
      label: "Dendrite arm spacings, IN718 and IN625",
      latex: String.raw`\lambda_1^{\mathrm{Hunt}}=1.1774\times10^{-3}\,G^{-1/2}R^{-1/4},\quad \lambda_1^{\mathrm{KF}}=2.5821\times10^{-3}\,G^{-1/2}R^{-1/4}\ \mathrm{m},\qquad \frac{G\,D}{\Delta T_0}<R<\frac{\Delta T_0\,D}{k\,\Gamma};\qquad \lambda_2=19.5\,q^{-0.63}\ \mu\mathrm{m}`,
      plain: "lambda_1(Hunt) = 1.1773863e-3 G^-0.5 R^-0.25 m; lambda_1(Kurz-Fisher) = 2.5821436e-3 G^-0.5 R^-0.25 m; both only for G D / dT0 < R < dT0 D / (k Gamma) with dT0 = 57 K, D = 3e-9 m^2/s, k = 0.48, Gamma = 3.65e-7 K m; lambda_2 = 19.5 q^-0.63 um, q = G R",
      symbols: [
        ["G, R", "local gradient (K/m) and rate (m/s)"],
        ["dT0, D, k, Gamma", "57 K, 3.0e-9 m^2/s, 0.48, 3.65e-7 K m (Ni-5Nb binary)"],
        ["q", "local cooling rate G R, K/s"],
      ],
      codeLocator: `${SE}:raw_spacing (Ni branch), NI_HUNT_A, NI_KF_A, NI_VAB, SPACING["in718"], SPACING["in625"]`,
      sourceLocator: "Ghosh et al. 2017, Table 2/PDF8, Eq. 7 (Hunt) and Eq. 8 (Kurz-Fisher); secondary: Mitchell 2005, Superalloys 2005, 299 to 310, PDF4/printed 302 Eq. 1.",
      asImplemented:
        "Two named binary Ni-Nb models transferred to IN718 (explicitly to IN625 for the Ni-family transfer). Their difference is model disagreement, not an interval. The coefficients are the code's numeric constants; the source form is not reconstructed here. Source domain: Ni-5Nb binary on the fixed-G line G = 1e7 K/m.",
      alloys: ["in718", "in625"],
    },
  ],
};


/**
 * Quick Screening job of the LPBF Workflow (python/lpbf_simulation.py:screening). A different code path from
 * MELTPOOL_GEOMETRY (python/lpbf_thermal_solver.py): no regularised Rosenthal, no 0.55 d width floor, no Fabbro depth
 * leg. The served metrics are the Goldak field's (lpbf_simulation.py run(): result["metrics"] = analytical["goldak"]).
 */
const SCREENING_GOLDAK = MELTPOOL_GEOMETRY.equations.find((eq) => eq.id === "goldak")!;
const SCREENING_JOB: Explainer = {
  id: "screening-job-geometry",
  title: "How the Quick Screening length, width and depth are calculated",
  summary:
    "Quick Screening evaluates a Goldak double-ellipsoid conduction field with axes seeded from the beam, using material properties at the preheat temperature, and reads the liquidus extent on a fixed grid. No keyhole correction. Screening only, not experimentally validated.",
  inputs: [
    { symbol: "P", label: "laser power", unit: "W", path: "settings.power_W" },
    { symbol: "v", label: "scan speed", unit: "mm/s", path: "settings.speed_mm_s" },
    { symbol: "d", label: "beam diameter (1/e^2)", unit: "um", path: "settings.beamDiameter_um" },
    { symbol: "T_0", label: "preheat", unit: "degC", path: "settings.preheat_C" },
    { symbol: "A", label: "absorptivity of the material record", unit: "", path: "material.absorptivity" },
    { symbol: "T_liq", label: "liquidus", unit: "K", path: "material.liquidus_K" },
    { symbol: "W", label: "width", unit: "um", path: "metrics.width_um" },
    { symbol: "D", label: "depth", unit: "um", path: "metrics.depth_um" },
    { symbol: "L", label: "length", unit: "um", path: "metrics.length_um" },
  ],
  notes: [{ label: "Assumptions stated by the solver", path: "metrics.assumptions" }],
  equations: [
    {
      id: "screening-power",
      label: "Absorbed power and properties",
      latex: String.raw`P_f = A\,P,\qquad \rho_k,\ k,\ c_p \text{ at } T_0,\qquad \alpha = \frac{k}{\rho_k\,c_p}`,
      plain: "P_f = A P; rho_k, k, c_p evaluated once at the preheat temperature T_0; alpha = k / (rho_k c_p)",
      symbols: [
        ["P_f", "absorbed power used by the field, W"],
        ["rho_k, k, c_p", "density, conductivity and specific heat from the material table at T_0, constant over the field"],
      ],
      codeLocator: "python/lpbf_simulation.py:screening (power = power_W * absorptivity; rho, k, cp = property_at(m, t0 + 273.15); alpha = k / (rho * cp))",
      sourceLocator: "Defined in the code; the constant-property assumption is stated in the result's assumptions text.",
    },
    {
      ...SCREENING_GOLDAK,
      id: "screening-goldak",
      label: "Goldak double-ellipsoid field",
      kernels: undefined,
      codeLocator: "python/lpbf_simulation.py:screening (GoldakField(t0, power, rho, cp, alpha, **seed_goldak_axes(d/2)).bind_speed(v)); python/goldak_solver.py:GoldakField",
      asImplemented: "Same GoldakField class as the specialist melt-pool lab, called with absorbed power and properties at the preheat temperature. The axes are a beam-based seed, not a fit to the pool.",
    },
    {
      id: "screening-extent",
      label: "Length, width and depth from the liquidus on a fixed grid",
      latex: String.raw`W = 2\max\{y : T(x,y,0)\ge T_{\mathrm{liq}}\},\quad D = \max\{z : T(x,0,z)\ge T_{\mathrm{liq}}\},\quad L = \max x-\min x\ \text{where}\ T(x,y,0)\ge T_{\mathrm{liq}}`,
      plain: "W = 2 * largest y with T(x, y, 0) >= T_liq; D = largest z with T(x, 0, z) >= T_liq; L = range of x where T(x, y, 0) >= T_liq; grid x from -3 to 0.5 mm (301 points), y and z from 0 to 1 mm (121 points)",
      symbols: [
        ["grid", "x in [-3, 0.5] mm with 301 points; y and z in [0, 1] mm with 121 points; the result reports this spacing as gridResolution_um"],
      ],
      codeLocator: "python/lpbf_simulation.py:screening (ax = linspace(-0.003, 0.0005, 301), transverse = linspace(0, 0.001, 121); width_um, depth_um, length_um)",
      sourceLocator: "Defined in the code (discrete liquidus extent).",
      asImplemented: "No keyhole correction and no width floor; values are quantised to the grid spacing.",
    },
  ],
};

export const CALCULATION_EXPLAINERS: Readonly<Record<string, Explainer>> = {
  [MELTPOOL_GEOMETRY.id]: MELTPOOL_GEOMETRY,
  [SCREENING_JOB.id]: SCREENING_JOB,
  [ENTHALPY_GATES.id]: ENTHALPY_GATES,
  [TI64_EVAPORATION.id]: TI64_EVAPORATION,
  [P8_LINKED_DEPTH.id]: P8_LINKED_DEPTH,
  [SOLIDIFICATION_ESTIMATES.id]: SOLIDIFICATION_ESTIMATES,
};

/** Equations of an explainer that apply to the result's kernel and alloy (kernel- or alloy-specific ones only when it is known). */
export function equationsForKernel(explainer: Explainer, kernel: KernelId | null, alloyId: string | null = null): ExplainerEquation[] {
  return explainer.equations.filter((eq) =>
    (!eq.kernels || (kernel !== null && eq.kernels.includes(kernel)))
    && (!eq.alloys || (alloyId !== null && eq.alloys.includes(alloyId))));
}
