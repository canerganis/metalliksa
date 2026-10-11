// Goldak double-ellipsoid CAE parameter card for a user DFLUX subroutine (not an Abaqus/Ansys input deck), shared by the
// LPBF melt pool views.
//
// Power normalisation: with f_f + f_r = 2 the Goldak double ellipsoid integrates to Q over the half-space body
// (z >= 0). In an FEA half-space model Q is therefore the ABSORBED power deposited in the part, Q = eta_eff * P_laser.
// It must not be halved.
//
// The exported semi-axes are NOT seed axes and NOT a calibrated Goldak fit: they are the liquidus-isotherm extents of
// the screening field the solver ran (x_front, x_rear, W/2, D including keyhole depth;
// python/lpbf_thermal_solver.py meltPoolGeometry.goldakParameters), whichever heat source the request used
// (heatSourceModel / modelId of the result). The seed axes are the separate seed_af_um / seed_ar_um fields. Axes and Q
// are not a calibrated pair (see the card text).

export type GoldakCardVariant = "thermal-map" | "cross-section";

export interface GoldakCaeCardInput {
  /** Heat source the solver actually used (Python result); the view may not have requested Goldak. */
  heatSourceModel?: string;
  modelId?: string;
  material: string;
  baseMetal: string;
  laserWavelength: string;
  processParameters: {
    laserPower_W: number;
    scanSpeed_mm_s: number;
    beamDiameter_um: number;
    volumetricEnergyDensity_J_mm3: number;
    normalizedEnthalpy?: number;
    effectiveAbsorptivity: number;
    conductionAbsorptivity?: number;
    /** Power that drove the screening field (Wave B LA-5): P_absorbed * latentHeatPowerFactor. */
    fieldPower_W?: number;
    stefanNumber?: number;
    /** 1.0 for every source since the P1 bump (2026-10-11); older rosenthal results carried 1/(1+0.55*Stefan). */
    latentHeatPowerFactor?: number;
  };
  meltPoolGeometry: {
    regime?: string;
    /** Liquidus extents of the screening field (a_f, a_r, b = W/2, c = D); seed_* are the separate Goldak seed axes. */
    goldakParameters: {
      semiAxis_af_front_um: number;
      semiAxis_ar_rear_um: number;
      semiAxis_b_halfwidth_um: number;
      semiAxis_c_depth_um: number;
      seed_af_um?: number;
      seed_ar_um?: number;
    };
  };
  /** P6 containment (2026-10-11): null with unavailableReason where the conduction-field interface is not served. */
  solidificationKinetics: {
    thermalGradient_G_K_m: number | null;
    solidificationRate_R_m_s: number | null;
    coolingRate_K_s: number | null;
    primaryDendriteArmSpacing_PDAS_um: number | null;
    unavailableReason?: string | null;
  };
}

/** "<value> <unit>" for a served number, else "unavailable" with the solver's reason when it carries one. */
export const kineticsLine = (label: string, value: number | null | undefined, unit: string, reason?: string | null): string =>
  typeof value === "number" && Number.isFinite(value)
    ? `** ${label}: ${value} ${unit}`
    : `** ${label}: unavailable${reason ? ` (${reason})` : ""}`;

export interface GoldakCaeCard {
  filename: string;
  text: string;
}

const RULE = "** -------------------------------------------------------------";

/**
 * Goldak continuity weights for a double ellipsoid with front/rear semi-axes a_f, a_r: f_f/a_f = f_r/a_r matched at the
 * source centre gives f_f = 2*a_f/(a_f + a_r), f_r = 2 - f_f (so f_f + f_r = 2).
 */
export const goldakFrontRearFractions = (a_front: number, a_rear: number): { f_f: number; f_r: number } => {
  const f_f = (2 * a_front) / (a_front + a_rear);
  return { f_f, f_r: 2 - f_f };
};

/** Absorbed power Q = eta_eff * P_laser in W (cleaned of binary floating-point noise, 15 significant digits). */
export const goldakAbsorbedPower_W = (laserPower_W: number, effectiveAbsorptivity: number): number =>
  Number((laserPower_W * effectiveAbsorptivity).toPrecision(15));

export function buildGoldakCaeCard(
  pyResult: GoldakCaeCardInput,
  variant: GoldakCardVariant = "thermal-map",
): GoldakCaeCard {
  const params = pyResult.processParameters;
  const geom = pyResult.meltPoolGeometry;
  const goldak = geom.goldakParameters;
  const kin = pyResult.solidificationKinetics;
  const crossSection = variant === "cross-section";
  const axis_m = (um: number) => (um * 1e-6).toExponential(4);
  const Q_W = goldakAbsorbedPower_W(params.laserPower_W, params.effectiveAbsorptivity);
  const heatSource = pyResult.heatSourceModel ?? pyResult.modelId ?? "heat source not reported";
  const { f_f, f_r } = goldakFrontRearFractions(goldak.semiAxis_af_front_um, goldak.semiAxis_ar_rear_um);
  const etaCond = params.conductionAbsorptivity;
  const hasEtaCond = etaCond !== undefined && etaCond !== null;
  // Since the P1 bump (2026-10-11) the solver (python/lpbf_thermal_solver.py) drives every source with P_absorbed =
  // conductionAbsorptivity*P and factor 1.0, and serves effectiveAbsorptivity equal to conductionAbsorptivity, so Q equals
  // the field power (ratio 1.00). Older results (multi-reflection eta_eff above eta_cond, rosenthal latent factor below 1)
  // are still printed honestly from the fields they carry; the thermal-map default is rosenthal.
  const source = heatSource.toLowerCase();
  const isRosenthal = source.includes("rosenthal");
  const isConductionSource = !isRosenthal && (source.includes("goldak") || source.includes("eagar-tsai"));
  const etaRatio = hasEtaCond ? (params.effectiveAbsorptivity / (etaCond as number)).toFixed(2) : undefined;

  const lines: string[] = [
    RULE,
    "** METALLIX LPBF GOLDAK HEAT SOURCE CAE EXPORT CARD",
    "** Parameter card for a user DFLUX subroutine, not an input deck.",
    `** Material: ${pyResult.material} (Base: ${pyResult.baseMetal})`,
    `** Laser Power: ${params.laserPower_W} W | Scan Speed: ${params.scanSpeed_mm_s} mm/s`,
    `** Beam Diameter: ${params.beamDiameter_um} um | Wavelength: ${pyResult.laserWavelength}`,
    `** Volumetric Energy Density (VED): ${params.volumetricEnergyDensity_J_mm3} J/mm3`,
  ];
  if (crossSection) lines.push(`** Normalized Enthalpy (ΔH/hs): ${params.normalizedEnthalpy} (${geom.regime})`);
  lines.push(
    RULE,
    "*DFLUX, USER",
    "*GOLDAK_DOUBLE_ELLIPSOID",
    crossSection ? "** Semi-Axes in meters (SI Units):" : "** Parameters in meters (SI Units):",
    "** Screening-model output; not Goldak FEA, not validated (see docs/LPBF_ENGINEERING.md).",
    `** Heat source used by the screening solver: ${heatSource}. *GOLDAK_DOUBLE_ELLIPSOID above is only the TARGET source type of the DFLUX.`,
    `** axes = liquidus extents of the ${heatSource} screening field (x_front, x_rear, W/2, D incl. keyhole depth), used as UNCALIBRATED Goldak axes`,
  );
  if (goldak.seed_af_um !== undefined && goldak.seed_ar_um !== undefined) {
    lines.push(`** reference only, not exported below: Goldak seed axes a_front = ${goldak.seed_af_um} um, a_rear = ${goldak.seed_ar_um} um`);
  }
  if (isRosenthal) {
    lines.push(
      `** field absorbed power (rosenthal source; before the latent-heat factor in results older than 2026-10-11), P_absorbed = eta_eff*P_laser: ${Q_W} W`,
    );
    if (hasEtaCond) {
      lines.push(
        `** conductionAbsorptivity (tabulated flat-plate absorptivity, or ray-traced powder value when warp is present; informational, NOT used by the rosenthal source): ${etaCond}`,
      );
    }
  } else if (isConductionSource && hasEtaCond) {
    lines.push(
      `** conductionAbsorptivity (tabulated flat-plate absorptivity, or ray-traced powder value when warp is present; used by the screening conduction field): ${etaCond}`,
      `** conduction-field absorbed power, eta_cond*P_laser: ${goldakAbsorbedPower_W(params.laserPower_W, etaCond as number)} W (the field power: Eagar & Tsai 1983 and Goldak et al. 1984 take the absorbed power as Q, no latent-heat factor)`,
    );
  } else if (hasEtaCond) {
    lines.push(
      `** conductionAbsorptivity (tabulated flat-plate absorptivity, or ray-traced powder value when warp is present): ${etaCond}`,
      `** field absorbed power depends on the heat source, which is not identified here: eta_cond*P_laser = ${goldakAbsorbedPower_W(params.laserPower_W, etaCond as number)} W (goldak/eagar-tsai) or eta_eff*P_laser = ${Q_W} W (rosenthal; before its latent-heat factor in results older than 2026-10-11)`,
    );
  }
  const hasFieldPower = typeof params.fieldPower_W === "number" && Number.isFinite(params.fieldPower_W);
  const exportedFieldPower = hasFieldPower
    ? `** exported by the solver: fieldPower_W = ${params.fieldPower_W} W` +
      (typeof params.latentHeatPowerFactor === "number" ? `, latentHeatPowerFactor = ${params.latentHeatPowerFactor}` : "") +
      (typeof params.stefanNumber === "number" ? `, stefanNumber = ${params.stefanNumber}` : "") +
      (hasFieldPower && (params.fieldPower_W as number) > 0 ? `; Q/P_field = ${(Q_W / (params.fieldPower_W as number)).toFixed(2)}` : "")
    : "** fieldPower_W not present in this result (older worker); P_field is not recomputed here.";
  lines.push(
    "** axes and Q are NOT a calibrated pair: the screening field was driven by P_field = P_absorbed*latentHeatPowerFactor, with P_absorbed = conductionAbsorptivity*P_laser and factor 1.0 for every source since 2026-10-11 (P1 planned bump; before it the rosenthal source used P_absorbed = effectiveAbsorptivity*P_laser with a multi-reflection eta_eff and the uncited factor 1/(1+0.55*Stefan), both removed) (python/lpbf_thermal_solver.py).",
    exportedFieldPower,
    isConductionSource && etaRatio !== undefined
      ? `** Q = eta_eff*P_laser = ${Q_W} W; for this ${heatSource} source the field power is eta_cond*P_laser, so Q exceeds it by eta_eff/eta_cond = ${etaRatio} here (1.00 means Q equals the field power, the case for every result since 2026-10-11); an FEA with these axes and Q will not reproduce the screening pool.`
      : isRosenthal
        ? `** Q = eta_eff*P_laser = ${Q_W} W is the rosenthal P_absorbed${etaRatio !== undefined ? `, eta_eff/eta_cond = ${etaRatio}` : ""}; since 2026-10-11 the field power equals it (factor 1.0, ratio 1.00), in older results the excess over the field power is the latent-heat factor only; an FEA with these axes and Q will not reproduce the screening pool.`
        : "** Q = eta_eff*P_laser equals the field power for every result since 2026-10-11 and can exceed it in older results (by the rosenthal latent-heat factor, or by eta_eff/eta_cond for goldak/eagar-tsai in transition/keyhole cases); an FEA with these axes and Q will not reproduce the screening pool.",
    "** a_front (m), a_rear (m), b_halfwidth (m), c_depth (m), Q_Goldak=eta_eff*P_laser (W, absorbed power deposited in the half-space body; f_f+f_r=2, do not halve), eta_eff (informational, ALREADY included in Q; do not apply again in DFLUX)",
    ` ${axis_m(goldak.semiAxis_af_front_um)}, ${axis_m(goldak.semiAxis_ar_rear_um)}, ${axis_m(goldak.semiAxis_b_halfwidth_um)}, ${axis_m(goldak.semiAxis_c_depth_um)}, ${Q_W}, ${params.effectiveAbsorptivity}`,
    `** f_f, f_r (continuity rule f_f = 2*a_f/(a_f+a_r), f_r = 2 - f_f): ${f_f.toFixed(4)}, ${f_r.toFixed(4)}`,
    "** Solidification Kinetics (rear liquidus of the loss-free conduction field; null with a reason where that interface is not served, P6 2026-10-11):",
    kineticsLine("G_avg", kin.thermalGradient_G_K_m, "K/m", kin.unavailableReason),
    kineticsLine("R_solid", kin.solidificationRate_R_m_s, "m/s", kin.unavailableReason),
    kineticsLine("Cooling Rate", kin.coolingRate_K_s, "K/s", kin.unavailableReason),
    kineticsLine("Primary Spacing (PDAS)", kin.primaryDendriteArmSpacing_PDAS_um, "um", kin.unavailableReason),
    RULE,
  );

  const material = pyResult.material.replace(/\s+/g, "_");
  const filename = `Goldak_LPBF_${crossSection ? "CrossSection_" : ""}${material}_${params.laserPower_W}W.goldak.txt`;
  return { filename, text: lines.join("\n") };
}
