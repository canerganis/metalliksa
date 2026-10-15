import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { convertSteelHardness } from "../src/utils/hardnessConversion";
import {
  KINETICS_HV_STATUS_NOTES,
  KINETICS_STATUS_NOTES,
  buildJobCctRow,
  buildJobKineticsAvailability,
  buildJobMartensiteText,
  formatCoolingRate,
  kineticsCctRowText,
  kineticsHardnessText,
  kineticsLabelText,
  kineticsLswAvailability,
  kineticsModelBanner,
  kineticsNoseText,
  kineticsPhaseSlices,
  kineticsPhaseStartsText,
  kineticsStatusNote,
  kineticsValueText,
  kineticsVerdictSentence,
} from "../src/utils/kineticsHardnessDisplay";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), ".."); // cwd-independent
const STEP_B = join(ROOT, "python", "golden", "phase6a", "kinetics_ttt_cct_solver", "step_b");

type Row = {
  coolingRate_C_s: number;
  predictedHardness_HRC: number | null;
  predictedHardness_HV: number | null;
  predictedHardness_HV_status: string;
};
const goldenRows = (file: string): { type: string; rows: Row[] } => {
  const doc = JSON.parse(readFileSync(join(STEP_B, file), "utf8"));
  return { type: doc.stdout.alloyMetadata.type, rows: doc.stdout.cctContinuousCoolingMap };
};

test("kinetics hardness text: converted steel row", () => {
  const t = kineticsHardnessText({
    predictedHardness_HRC: 58,
    predictedHardness_HV: 653,
    predictedHardness_HV_status: "converted-astm-e140-table1",
  });
  assert.deepEqual(t, {
    hrcValue: "58",
    hvValue: "653",
    hrc: "58 HRC",
    hv: "653 HV",
    note: KINETICS_HV_STATUS_NOTES["converted-astm-e140-table1"],
  });
});

test("kinetics hardness text: null HV is Unavailable, never a number", () => {
  for (const status of [
    "unavailable-outside-e140-table1-hrc-20-68",
    "unavailable-no-verified-table-for-alloy-class",
  ]) {
    const t = kineticsHardnessText({ predictedHardness_HRC: 18, predictedHardness_HV: null, predictedHardness_HV_status: status });
    assert.equal(t.hv, "HV: Unavailable");
    assert.equal(t.hvValue, "Unavailable");
    assert.equal(t.hrc, "18 HRC");
    assert.equal(t.note, KINETICS_HV_STATUS_NOTES[status]);
  }
  // older payload without a status key
  assert.equal(kineticsHardnessText({ predictedHardness_HRC: 42, predictedHardness_HV: null }).note, "HV unavailable.");
});

test("kinetics hardness text: no solver row shows Unavailable instead of the old invented 52 HRC / 550 HV", () => {
  for (const row of [null, undefined, {}]) {
    const t = kineticsHardnessText(row);
    assert.equal(t.hrc, "HRC: Unavailable");
    assert.equal(t.hv, "HV: Unavailable");
    assert.equal(t.hrcValue, "Unavailable");
    assert.equal(t.hvValue, "Unavailable");
    assert.ok(!/52|550/.test(JSON.stringify(t)));
  }
  assert.equal(kineticsHardnessText({ predictedHardness_HRC: Number.NaN, predictedHardness_HV: Number.NaN }).hv, "HV: Unavailable");
});

test("re-blessed solver goldens: no hardness is predicted (Li model), HV null with the alloy-class status", () => {
  // Lane kin-li: the Li (1998) model computes no phase fractions or hardness, so the E140 conversion has no input;
  // the TS util itself is unchanged (convertSteelHardness still converts a given HRC).
  const files = readdirSync(STEP_B).filter((f) => f.endsWith(".json")).sort();
  assert.deepEqual(files, [
    "aisi4140_ui_defaults.json",
    "aisi4340_slow_cool.json",
    "in718_lpbf_quench.json",
    "ti64_beta_quench.json",
  ]);
  for (const f of files) {
    const { type, rows } = goldenRows(f);
    assert.equal(rows.length, 10, f);
    for (const r of rows) {
      assert.equal(r.predictedHardness_HRC, null, `${f} ${r.coolingRate_C_s} C/s`);
      assert.equal(r.predictedHardness_HV, null, `${f} ${r.coolingRate_C_s} C/s`);
      assert.equal(
        r.predictedHardness_HV_status,
        type.includes("Steel") ? "unavailable-no-predicted-hrc" : "unavailable-no-verified-table-for-alloy-class"
      );
    }
  }
  assert.equal(convertSteelHardness(58, "HRC").HV, 653);
});

test("Studio table text for the AISI 4140 UI-default golden (old -> new)", () => {
  const { rows } = goldenRows("aisi4140_ui_defaults.json");
  assert.deepEqual(
    rows.map((r) => {
      const t = kineticsHardnessText(r);
      const c = kineticsCctRowText(r);
      return `${r.coolingRate_C_s}: ${c.startTemp} ${c.microstructure}; ${t.hrc} (${t.hv})`;
    }),
    [
      "0.05: 721.3 °C Ferrite; HRC: Unavailable (HV: Unavailable)", // was Unavailable start; 18 HRC (HV: Unavailable)
      "0.2: 689.3 °C Ferrite; HRC: Unavailable (HV: Unavailable)", // was Unavailable; 18 HRC
      "1: 611.1 °C Pearlite; HRC: Unavailable (HV: Unavailable)", // was Unavailable; 28 HRC (286 HV)
      "5: 479.1 °C Bainite; HRC: Unavailable (HV: Unavailable)", // was Unavailable; 28 HRC (286 HV)
      "10: 448.6 °C Bainite; HRC: Unavailable (HV: Unavailable)", // was Unavailable; 42 HRC (412 HV)
      "25: 328.5 °C Martensite (Athermal); HRC: Unavailable (HV: Unavailable)", // was Unavailable; 42 HRC (412 HV)
      "50: 328.5 °C Martensite (Athermal); HRC: Unavailable (HV: Unavailable)", // was Unavailable; 54 HRC (577 HV)
      "100: 328.5 °C Martensite (Athermal); HRC: Unavailable (HV: Unavailable)", // was Unavailable; 58 HRC (653 HV)
      "500: 328.5 °C Martensite (Athermal); HRC: Unavailable (HV: Unavailable)", // was Unavailable; 58 HRC (653 HV)
      "2000: 328.5 °C Martensite (Athermal); HRC: Unavailable (HV: Unavailable)", // was Unavailable; 58 HRC (653 HV)
    ]
  );
  assert.equal(kineticsHardnessText(rows[0]).note, KINETICS_STATUS_NOTES["unavailable-fractions-not-computed"]);
});

test("consumers: the Decision Lab delegates the build-job kinetics block to the panel", () => {
  // The Decision Lab delegates the build-job kinetics block to the panel (render-tested in
  // tests/build-job-kinetics-panel.test.tsx); it reads no kinetics field itself.
  const lab = readFileSync(join(ROOT, "src", "components", "3d-distortion-lab", "IndustrialLPBFDecisionLab.tsx"), "utf8");
  assert.match(lab, /<BuildJobKineticsPanel kinetics=\{job\?\.kinetics\} \/>/);
  assert.ok(!/cctContinuousCoolingMap|calphadVsKineticsGap|predictedMartensite_pct|predictedHardness_H/.test(lab));
});

test("build-job kinetics: availability follows Python's status, not the legacy success flag", () => {
  assert.deepEqual(
    buildJobKineticsAvailability({ status: "unavailable", reason: "no kinetics model for 316L Stainless Steel" }),
    { available: false, reason: "no kinetics model for 316L Stainless Steel." }
  );
  assert.equal(buildJobKineticsAvailability(null).available, false);
  assert.equal(buildJobKineticsAvailability({}).available, false); // a pre-status payload is not trusted
  assert.equal(buildJobKineticsAvailability({ status: "available" }).available, true);
});

test("build-job kinetics: a CCT selection is trusted only when it matches its map row", () => {
  const rows = [{ coolingRate_C_s: 0.05 }, { coolingRate_C_s: 25, primaryMicrostructure: "Bainite" }];
  const base = { status: "available", cctContinuousCoolingMap: rows };
  const sel = { status: "selected", rowIndex: 1, rowCoolingRate_C_s: 25, buildCoolingRate_C_s: 30 };
  const ok = buildJobCctRow({ ...base, buildCoolingRateCctRow: sel });
  assert.equal(ok.row, rows[1]);
  assert.equal(ok.label, "CCT row 25 °C/s (nearest on a log scale to the build cooling rate 30 °C/s).");
  for (const bad of [
    { ...sel, rowIndex: 99 },
    { ...sel, rowIndex: 0 }, // index points at a row whose rate differs from rowCoolingRate_C_s
    { ...sel, rowCoolingRate_C_s: 50 },
    { ...sel, buildCoolingRate_C_s: null },
    { ...sel, status: "unavailable" },
  ]) {
    assert.equal(buildJobCctRow({ ...base, buildCoolingRateCctRow: bad }).row, null, JSON.stringify(bad));
  }
  assert.equal(
    buildJobCctRow({ ...base, buildCoolingRateCctRow: { status: "unavailable", reason: "r" } }).label,
    "No CCT row: r."
  );
});

test("build-job kinetics: martensite text never renders null% and never shows a withheld verdict", () => {
  assert.deepEqual(
    buildJobMartensiteText({ buildRateMartensite: { status: "available", predictedMartensite_pct: 7, verdict: "V", coolingRate_C_s: 30 } }),
    { value: "7%", verdict: "V", reason: "", hint: "At build rate 30 °C/s" }
  );
  for (const m of [
    { status: "available", predictedMartensite_pct: null, verdict: "V" },
    { status: "available", predictedMartensite_pct: Number.NaN, verdict: "V" },
    { status: "unavailable", predictedMartensite_pct: 7, verdict: "V", reason: "withheld" },
    null,
  ]) {
    const t = buildJobMartensiteText({ buildRateMartensite: m });
    assert.equal(t.value, "Unavailable");
    assert.equal(t.verdict, null);
    assert.ok(!/null|NaN|undefined/.test(`${t.value} ${t.reason} ${t.hint}`), JSON.stringify(t));
  }
});

test("formatCoolingRate: short, never a long float", () => {
  assert.equal(formatCoolingRate(2000), "2000");
  assert.equal(formatCoolingRate(0.05), "0.05");
  assert.equal(formatCoolingRate(1523.456789123), "1523");
  assert.equal(formatCoolingRate(30.123456), "30.12");
  assert.equal(formatCoolingRate(1089047), "1.09e+6");
});

// ---------------------------------------------------------------------------------------------------------------
// Engine-fix lane fx-kinetics: steel-only model, registry placeholders, TTT floor (python/kinetics_ttt_cct_solver.py).

const goldenDoc = (file: string) => JSON.parse(readFileSync(join(STEP_B, file), "utf8")).stdout;
const GOLDEN_FILES = ["aisi4140_ui_defaults.json", "aisi4340_slow_cool.json", "in718_lpbf_quench.json", "ti64_beta_quench.json"];
const BAD_TEXT = /null|NaN|undefined|Infinity/;

test("fx-kinetics: every visible CCT/hardness/phase text of the four goldens is clean (no null, NaN, undefined)", () => {
  for (const f of GOLDEN_FILES) {
    const doc = goldenDoc(f);
    for (const row of doc.cctContinuousCoolingMap) {
      const rt = kineticsCctRowText(row);
      const ht = kineticsHardnessText(row);
      const slices = kineticsPhaseSlices(row);
      const all = [...Object.values(rt), ...Object.values(ht), slices.reason, ...slices.slices.map((s) => `${s.name}${s.value}`)];
      for (const s of all) assert.ok(!BAD_TEXT.test(String(s)), `${f} ${row.coolingRate_C_s}: ${s}`);
    }
    const banner = kineticsModelBanner(doc.kineticsModel, doc.tttIncubationFloor);
    assert.ok(!BAD_TEXT.test(`${banner.reason}${banner.caution}${banner.floorLine ?? ""}`), f);
  }
});

test("fx-kinetics: non-steel goldens (IN718, Ti-6Al-4V) show Unavailable with the steel-only reason, never steel values", () => {
  for (const f of ["in718_lpbf_quench.json", "ti64_beta_quench.json"]) {
    const doc = goldenDoc(f);
    assert.equal(doc.tttIsothermalCurves, null);
    const banner = kineticsModelBanner(doc.kineticsModel, doc.tttIncubationFloor);
    assert.equal(banner.available, false);
    assert.equal(banner.reason, "kinetics model is steel-only.");
    assert.equal(banner.floorLine, null);
    for (const row of doc.cctContinuousCoolingMap) {
      const rt = kineticsCctRowText(row);
      assert.equal(rt.startTemp, "Unavailable", f);
      assert.equal(rt.startTime, "Unavailable");
      assert.equal(rt.microstructure, "Unavailable");
      assert.equal(rt.martensite, "Unavailable");
      assert.equal(rt.startNote, "Unavailable: kinetics model is steel-only.");
      const ht = kineticsHardnessText(row);
      assert.equal(ht.hrc, "HRC: Unavailable");
      assert.equal(ht.hv, "HV: Unavailable");
      assert.equal(ht.note, "Unavailable: kinetics model is steel-only.");
      const slices = kineticsPhaseSlices(row);
      assert.deepEqual(slices.slices, []);
      assert.equal(slices.reason, "Unavailable: kinetics model is steel-only.");
    }
    const gap = doc.calphadVsKineticsGap;
    assert.equal(kineticsLabelText(gap.equilibriumPrediction.stablePhasesAtRT), "Unavailable");
    assert.equal(kineticsValueText(gap.kineticRealityAtSelectedCooling.predictedMartensite_pct, "%"), "Unavailable");
    assert.equal(kineticsLabelText(gap.kineticRealityAtSelectedCooling.verdict), "Unavailable");
  }
});

test("fx-kinetics: registry placeholder Ms/Mf (IN718) are null in the golden and shown as Unavailable", () => {
  const doc = goldenDoc("in718_lpbf_quench.json");
  const crit = doc.criticalTransformationTemperatures;
  assert.equal(crit.Ms_C, null);
  assert.equal(crit.Mf_C, null);
  assert.equal(crit.Ms_C_status, "unavailable-registry-placeholder");
  assert.equal(kineticsValueText(crit.Ms_C, " °C"), "Unavailable");
  assert.equal(kineticsStatusNote(crit.Ms_C_status), "Unavailable: the registry value is a non-physical placeholder.");
  assert.equal(kineticsValueText(crit.CriticalCoolingRate_CCR_C_s, " °C/s"), "Unavailable");
  // Ti-6Al-4V Ms/Mf are not flagged in the registry: they stay numbers.
  assert.equal(kineticsValueText(goldenDoc("ti64_beta_quench.json").criticalTransformationTemperatures.Ms_C, " °C"), "800 °C");
});

test("kin-li: steel goldens show Li-model starts, no floor line, fractions Unavailable with the reason", () => {
  const doc = goldenDoc("aisi4140_ui_defaults.json");
  const banner = kineticsModelBanner(doc.kineticsModel, doc.tttIncubationFloor);
  assert.equal(banner.available, true);
  assert.equal(banner.reason, "");
  assert.equal(banner.headline, "Li et al. (1998) TTT/CCT model (screening, unvalidated).");
  assert.equal(banner.floorLine, null); // was "32 of 40 TTT points are on the 0.001 s incubation floor ..."
  assert.deepEqual(banner.validityLines, [
    "Validity range only partially checked: Al not specified in the registry composition: the 0.01 < Al < 0.05 wt% bound is not checked.",
  ]);
  const coarse = kineticsModelBanner(
    { status: "available", validityDomain: { status: "inside", unchecked: [], grainSize: { astmG: 0.73, comparedRange_G: [5.6, 11], insideComparedRange: false } } },
    null
  );
  assert.deepEqual(coarse.validityLines, ["Grain size ASTM G 0.73 is outside the span of the published comparisons (G 5.6-11)."]);
  assert.deepEqual(kineticsModelBanner({ status: "unavailable", validityDomain: { status: "outside", unchecked: ["x"] } }, null).validityLines, []);
  assert.equal(doc.tttIsothermalCurves.filter((p: { floorHit: boolean }) => p.floorHit).length, 0);
  for (const row of doc.cctContinuousCoolingMap) {
    const rt = kineticsCctRowText(row);
    assert.match(rt.startTemp, /^\d+\.\d °C$/);
    assert.equal(rt.startNote, "");
    assert.equal(rt.martensite, "Unavailable");
    assert.equal(rt.fractionsNote, KINETICS_STATUS_NOTES["unavailable-fractions-not-computed"]);
    assert.deepEqual(kineticsPhaseSlices(row).slices, []);
  }
  assert.equal(kineticsPhaseStartsText(doc.cctContinuousCoolingMap[0]), "F 721.3 / P 691.9 / B 531.6 °C");
  assert.equal(kineticsPhaseStartsText(doc.cctContinuousCoolingMap[9]), "F - / P - / B - °C");
  assert.equal(kineticsPhaseStartsText(null), "Unavailable");
  assert.equal(kineticsPhaseStartsText(goldenDoc("in718_lpbf_quench.json").cctContinuousCoolingMap[0]), "Unavailable");
  assert.match(kineticsNoseText(doc.tttIsothermalCurves), /^Ferrite \d+ °C \([\d.e+]+ s\) \/ Pearlite \d+ °C \([\d.e+]+ s\) \/ Bainite \d+ °C \([\d.e+]+ s\)$/);
  assert.equal(kineticsNoseText(null), "");
  assert.equal(kineticsNoseText([{ phase: "Bainite", temperature_C: 464.2, tStart_s: 4.591 }, { phase: "Bainite", temperature_C: 500, tStart_s: 9 }]),
    "Bainite 464 °C (4.6 s)");
  // an unknown status never produces a note from thin air; removed template statuses have no note any more
  assert.equal(kineticsStatusNote("something-else"), "");
  assert.equal(kineticsStatusNote("steel-lookup-by-ccr-band-not-computed"), "");
  assert.equal(kineticsStatusNote(null), "");
  assert.equal(kineticsModelBanner(null, null).floorLine, null);
  assert.equal(kineticsModelBanner(null, null).available, false);
  assert.equal(kineticsCctRowText(null).startTemp, "Unavailable");
  assert.equal(kineticsCctRowText({ transformedStartTemp_C: Number.NaN }).startTemp, "Unavailable");
});

test("fx-kinetics: floor line only when at least one point is on the floor; LSW availability follows the solver", () => {
  const model = { status: "available", note: "n" };
  assert.equal(kineticsModelBanner(model, { pointCount: 40, floorHitCount: 0, floorValue_s: 0.001 }).floorLine, null);
  assert.equal(
    kineticsModelBanner(model, { pointCount: 40, floorHitCount: 1, floorValue_s: 0.001 }).floorLine,
    "1 of 40 TTT points are on the 0.001 s incubation floor (floorHit): their start time is the floor, not a model value."
  );
  assert.equal(kineticsModelBanner(model, { pointCount: null, floorHitCount: null }).floorLine, null);
  const unavailable = kineticsLswAvailability(
    [{ meanRadius_nm: null }, { meanRadius_nm: Number.NaN }],
    { status: "unavailable-aging-temperature-at-or-above-solvus", reason: "aging temperature 720 C is at or above the registry Ae3" }
  );
  assert.deepEqual(unavailable, { available: false, reason: "aging temperature 720 C is at or above the registry Ae3." });
  // SOL-K: the solver returns null rows with a status and reason codes for every alloy (Ti-6Al-4V at 720 C used to
  // return 5.03 nm / 209.3 MPa); the helper shows the existing note of the status, no sentence is added for a code
  const nullRow = {
    meanRadius_nm: null,
    precipitationHardening_MPa: null,
    strengtheningMechanism: null,
    status: "unavailable-not-modelled",
    reasonCodes: ["missing-source-bound-model", "missing-source-constant"],
  };
  assert.deepEqual(
    kineticsLswAvailability([nullRow, nullRow], {
      status: "unavailable-not-modelled",
      reason: null,
      reasonCodes: ["missing-source-bound-model", "missing-source-constant"],
    }),
    { available: false, reason: "Unavailable: not modelled." }
  );
  assert.equal(kineticsLswAvailability([nullRow], { status: "unavailable-not-modelled" }).available, false);
  assert.equal(kineticsLswAvailability([{ meanRadius_nm: 2.5 }], null).available, true);
  assert.equal(
    kineticsLswAvailability(null, { status: "unavailable-aging-temperature-at-or-above-solvus" }).reason,
    "Unavailable: the aging temperature is at or above the registry solvus (steels: Ae1); no precipitate population."
  );
  // the verdict sentence follows the Li verdict and never claims martensite for a diffusional start
  assert.match(kineticsVerdictSentence("No diffusional start above Ms (Li 1998 additivity): martensite from Ms", 100, true),
    /transforms athermally \(martensite\)/);
  assert.equal(kineticsVerdictSentence("Bainite start at 448.6 C (Li 1998 additivity); phase fractions not computed", 10, true),
    "At 10 °C/s, the Li (1998) additivity model reaches a bainite start above Ms; the phase fractions are not computed.");
  assert.doesNotMatch(kineticsVerdictSentence("Ferrite start at 721.3 C (Li 1998 additivity); phase fractions not computed", 0.05, true), /martensite|shear/);
  assert.equal(kineticsVerdictSentence("Full Martensitic / Metastable Quench", 100, true), ""); // old template verdict: no sentence
  assert.equal(kineticsVerdictSentence(null, 10, false), "Unavailable: kinetics model is steel-only.");
  assert.equal(kineticsVerdictSentence(null, 10, false, "composition outside the Li (1998) model range: C 1.55 wt%"),
    "Unavailable: composition outside the Li (1998) model range: C 1.55 wt%.");
  assert.equal(kineticsVerdictSentence(null, 10, true), "");
  // registry-screening-value has a note (the Ti-6Al-4V Ms/Mf tooltips were empty)
  assert.notEqual(kineticsStatusNote("registry-screening-value"), "");
});
