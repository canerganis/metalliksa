import React from "react";
import assert from "node:assert/strict";
import { test } from "node:test";
import { renderToStaticMarkup } from "react-dom/server";
import {
  deriveSpecimenProperties,
  migrateMaterialSpecimenStoreState,
  MATERIAL_SPECIMEN_STORE_VERSION,
  SPECIMEN_PRESETS,
  type ActiveSpecimenState,
} from "../src/store/useMaterialSpecimenStore";
import {
  catalogueDesignationFor,
  deriveProperties,
  MATERIAL_PRESETS,
  MATERIAL_STORE_VERSION,
  migrateMaterialStoreState,
  type MaterialSpecimen,
} from "../src/store/useMaterialStore";
import {
  COMPOSITION_HEURISTIC_PROPERTY_FIELDS,
  ruleOfMixturesDensity,
} from "../src/utils/compositionPropertyAvailability";
import { stressProxyYieldCheck } from "../src/utils/residualStressYieldCheck";
import { StressProxyMetric } from "../src/components/3d-distortion-lab/IndustrialLPBFDecisionLab";

const HEURISTIC_VALUES = {
  liquidus_C: 1336, solidus_C: 1260, freezingRange_C: 76, solvus_C: 1100,
  yieldStrength_25C_MPa: 1050, uts_25C_MPa: 1350, youngsModulus_GPa: 210, elongation_pct: 16,
};

test("shared specimen store holds no heuristic temperatures or strengths for any preset", () => {
  for (const [key, preset] of Object.entries(SPECIMEN_PRESETS)) {
    const d = deriveSpecimenProperties(preset.composition, preset.name, preset.base);
    for (const field of COMPOSITION_HEURISTIC_PROPERTY_FIELDS) assert.equal(d[field], null, `${key}.${field}`);
  }
  // Pure iron used to get a composition-derived yield strength like any steel.
  assert.equal(deriveSpecimenProperties({ Fe: 100 }, "Fe fixture").yieldStrength_25C_MPa, null);
});

test("LPBF inputs from the specimen store are unchanged (values pinned from the pre-change derivation)", () => {
  // recommended P, v, hatch, layer, preheat, hot-tearing class, rho: loadPreset copies these into the live vector.
  const expected: Record<string, [number, number, number, number, number, string, number]> = {
    "custom-ni-superalloy": [280, 940, 100, 40, 200, "High", 7914],
    "inconel-718": [280, 940, 100, 40, 200, "High", 8167],
    "ti-6al-4v": [240, 1200, 100, 40, 150, "Moderate", 4377],
    "ss-316l": [200, 850, 100, 40, 80, "Low", 7771],
    alsi10mg: [350, 1300, 100, 40, 160, "Moderate", 2656],
  };
  for (const [key, preset] of Object.entries(SPECIMEN_PRESETS)) {
    const l = deriveSpecimenProperties(preset.composition, preset.name, preset.base).lpbf;
    assert.deepEqual(
      [l.recommendedLaserPower_W, l.recommendedScanSpeed_mms, l.recommendedHatch_um, l.recommendedLayer_um, l.recommendedPreheatTemp_C, l.hotTearingSusceptibility, l.density_rho_kgm3],
      expected[key],
      key
    );
  }
});

test("specimen store migration v2 -> v4 nulls heuristic properties and keeps the live LPBF vector", () => {
  assert.equal(MATERIAL_SPECIMEN_STORE_VERSION, 4);
  const base = deriveSpecimenProperties(SPECIMEN_PRESETS["inconel-718"].composition, "IN718 fixture", "Ni");
  const lpbf = { ...base.lpbf, laserPower_W: 333, scanSpeed_mms: 777, processSeed: 9 };
  const persisted = { activeSpecimen: { ...base, ...HEURISTIC_VALUES, id: "x", lpbf, sourceTab: "t", lastModified: 1, isCustomModified: true } };
  const migrated = migrateMaterialSpecimenStoreState(persisted, 2) as { activeSpecimen: ActiveSpecimenState };
  for (const field of COMPOSITION_HEURISTIC_PROPERTY_FIELDS) assert.equal(migrated.activeSpecimen[field], null, field);
  assert.deepEqual(migrated.activeSpecimen.lpbf, lpbf);
  assert.deepEqual(migrated.activeSpecimen.composition, base.composition);
  assert.equal(migrated.activeSpecimen.name, "IN718 fixture");
  // current-version blobs and non-objects pass through untouched
  assert.equal(migrateMaterialSpecimenStoreState(persisted, 4), persisted);
  assert.equal(migrateMaterialSpecimenStoreState(null, 1), null);
});

test("material store migration v1 -> v2 nulls heuristic properties and clears threshold-assigned designations", () => {
  assert.equal(MATERIAL_STORE_VERSION, 2);
  const make = (composition: Record<string, number>, standardDesignation: string) =>
    ({
      id: "s", ...deriveProperties(composition, "fixture", undefined, { standardDesignation }),
      ...HEURISTIC_VALUES, sourceTab: "t", lastModified: 0, isCustomModified: true,
    }) as unknown as MaterialSpecimen;
  // Any Ni + Nb > 2.5 alloy was labelled IN718 by the threshold rule.
  const niNb = make({ Ni: 90, Nb: 5, Cr: 5 }, "UNS N07718 / AMS 5662");
  // A catalogue composition keeps (or regains) its catalogue designation.
  const in718 = make(MATERIAL_PRESETS.in718.composition, "UNS N07718 / AMS 5662");
  const ss316 = make(MATERIAL_PRESETS.ss316l.composition, "AISI 316L / ASTM A276");
  const userTyped = make({ Ni: 80, Cr: 20 }, "Customer spec 12");
  type M = { activeMaterialSpecimen: MaterialSpecimen; activeSpecimen: MaterialSpecimen; savedSpecimens: MaterialSpecimen[] };
  const m = migrateMaterialStoreState({ activeMaterialSpecimen: niNb, activeSpecimen: niNb, savedSpecimens: [in718, ss316, userTyped] }, 1) as M;
  for (const field of COMPOSITION_HEURISTIC_PROPERTY_FIELDS) {
    assert.equal(m.activeMaterialSpecimen[field], null, field);
    for (const s of m.savedSpecimens) assert.equal(s[field], null, field);
  }
  assert.equal(m.activeMaterialSpecimen.metadata.standardDesignation, "");
  assert.equal(m.activeSpecimen.metadata.standardDesignation, "");
  assert.equal(m.savedSpecimens[0].metadata.standardDesignation, MATERIAL_PRESETS.in718.standard);
  assert.equal(m.savedSpecimens[0].metadata.standardDesignationSource, "catalogue");
  assert.equal(m.savedSpecimens[1].metadata.standardDesignation, MATERIAL_PRESETS.ss316l.standard);
  assert.equal(m.savedSpecimens[2].metadata.standardDesignation, "Customer spec 12");
  assert.equal(catalogueDesignationFor({ Ni: 90, Nb: 5, Cr: 5 }), null);
});

test("decision lab: the residual-stress check gives no pass/fail on a missing (formerly heuristic) yield strength", () => {
  const unavailable = stressProxyYieldCheck(900, null);
  assert.equal(unavailable.status, "unavailable");
  assert.equal(unavailable.ok, null);
  assert.equal(unavailable.limit_MPa, null);
  assert.match(unavailable.hint, /No pass\/fail: Rp0\.2 unavailable/);
  for (const bad of [undefined, 0, -5, Number.NaN]) assert.equal(stressProxyYieldCheck(900, bad as number).ok, null);
  // With a real yield strength the comparison is the stated 0.7 Rp0.2 screening ratio.
  assert.deepEqual(stressProxyYieldCheck(500, 1000), { status: "below", ok: true, limit_MPa: 700, hint: "< 0.7 Rp0.2 (700)" });
  assert.equal(stressProxyYieldCheck(700, 1000).ok, false);

  // The shared specimen's yield is null, so the rendered metric is neutral: neither pass nor flagged.
  const specimen = deriveSpecimenProperties(SPECIMEN_PRESETS["inconel-718"].composition, "IN718", "Ni");
  const html = renderToStaticMarkup(<StressProxyMetric stress_MPa={812} yieldStrength_MPa={specimen.yieldStrength_25C_MPa} />);
  assert.match(html, /data-check="unavailable"/);
  assert.match(html, /No pass\/fail: Rp0\.2 unavailable/);
  assert.doesNotMatch(html, /0\.7 Rp0\.2 \(/);
  assert.match(renderToStaticMarkup(<StressProxyMetric stress_MPa={812} yieldStrength_MPa={1000} />), /data-check="flag"/);
});

test("rule-of-mixtures density: computed from tabulated values only, never a fallback", () => {
  const fe = ruleOfMixturesDensity({ Fe: 100 });
  assert.equal(fe.status, "computed");
  assert.equal(fe.density_gcm3, 7.874);
  // 50/50 wt% Ni-Al: 100 / (50/8.908 + 50/2.7) = 4.144
  assert.equal(ruleOfMixturesDensity({ Ni: 50, Al: 50 }).density_gcm3, parseFloat((100 / (50 / 8.908 + 50 / 2.7)).toFixed(3)));
  const withO = ruleOfMixturesDensity({ Ti: 90, O: 0.2 });
  assert.equal(withO.density_gcm3, null);
  assert.match(withO.note, /no tabulated elemental density for O/);
  assert.equal(ruleOfMixturesDensity({ Ni: 50, Al: 50 }, "at_pct").density_gcm3, null);
  assert.equal(ruleOfMixturesDensity({}).density_gcm3, null);
});

test("decision lab: the stress proxy is labelled a heuristic thermal-strain proxy and says when it exceeds yield", () => {
  const noYield = renderToStaticMarkup(<StressProxyMetric stress_MPa={3477} yieldStrength_MPa={null} />);
  assert.match(noYield, /Thermal-strain proxy \(heuristic, elastic; not a stress\)/);
  assert.match(noYield, /3477 MPa-eq\./);
  assert.doesNotMatch(noYield, /Exceeds yield/);
  const above = renderToStaticMarkup(<StressProxyMetric stress_MPa={3477} yieldStrength_MPa={600} />);
  assert.match(above, /Exceeds yield; elastic estimate not physical as a stress/);
  assert.match(above, /data-check="flag"/);
  assert.doesNotMatch(renderToStaticMarkup(<StressProxyMetric stress_MPa={300} yieldStrength_MPa={600} />), /Exceeds yield/);
});
