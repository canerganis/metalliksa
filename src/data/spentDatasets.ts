import ledger from "../../data/benchmark/spent-ledger-v1.json";
import nist from "../../data/benchmark/nist-amb2022-03-optical/table4-aggregate-v2.json";
import projection from "../generated/dataToUser.json";

export const SPENT_BADGE = "Descriptive: not validation; this data was already seen";
export const SPENT_ENTRIES = ledger.entries;
export type SpentEntry = typeof SPENT_ENTRIES[number];
export const DATA_TO_USER = projection;
export type ServedSample = typeof projection.samples[keyof typeof projection.samples];
export interface SpentPoint { id: string; power: number; speed: number; beam: number; measured: number; sample: ServedSample | null }

// An explicit licence allowlist fails closed. Restricted source tables are never bundled.
export function isOpenDataset(entry: SpentEntry): boolean {
  return ["CC0", "CC BY 4.0", "NIST open data, https://www.nist.gov/open/license"].includes(entry.licence);
}

let tables: Record<string, string> = {};
try {
  tables = import.meta.glob([
    "../../data/benchmark/ku-leuven-316l-ti64-2021/conditions.csv",
    "../../data/benchmark/totis-ti64-2021/tracks.csv",
  ], { eager: true, query: "?raw", import: "default" });
} catch { /* Tests inject existing source text; Vite supplies it in the app. */ }

export function spentPoints(entry: SpentEntry, sourceTables = tables): SpentPoint[] {
  if (!isOpenDataset(entry)) return [];
  const samples: Record<string, ServedSample> = projection.samples;
  const point = (id: string, power: number, speed: number, beam: number, measured: number): SpentPoint =>
    ({ id, power, speed, beam, measured, sample: samples[`${entry.datasetId}/${id}`] ?? null });
  if (entry.datasetId === "nist-amb2022-03-optical") {
    return nist.cases.map(c => point(c.caseNumber, c.laserPower_W, c.scanSpeed_mm_s, c.beamDiameterD4sigma_um, c.depthMean_um));
  }
  const ku = entry.datasetId.startsWith("ku-leuven-");
  const path = ku ? "../../data/benchmark/ku-leuven-316l-ti64-2021/conditions.csv" : "../../data/benchmark/totis-ti64-2021/tracks.csv";
  const text = sourceTables[path];
  if (!text) return [];
  // These committed numeric tables have no quoted fields. Reject schema drift.
  if (text.includes('"')) throw new Error("Unsupported benchmark CSV quoting");
  const [header, ...lines] = text.trim().split(/\r?\n/).map(line => line.split(","));
  const records = lines.map(cells => Object.fromEntries(header.map((key, i) => [key, cells[i]])));
  return records.flatMap(r => {
    if (ku && r.alloy !== entry.alloy) return [];
    const depth = ku ? r.d_exp_um : r.depth_um;
    if (!depth?.trim()) return [];
    const power = Number(r.power_W), speed = Number(r.speed_mm_s), measured = Number(depth);
    if (![power, speed, measured].every(Number.isFinite)) throw new Error("Non-finite benchmark condition");
    const id = ku ? `${entry.datasetId}-${r.sample.padStart(2, "0")}` : `totis-${String(power).padStart(3, "0")}W-${String(speed).padStart(4, "0")}mms`;
    return [point(id, power, speed, entry.beam.value_um, measured)];
  });
}

export function signedDeviation(point: SpentPoint): string {
  const predicted = point.sample?.depth_um;
  if (predicted == null) return "Unavailable";
  const delta = predicted - point.measured;
  return `${delta >= 0 ? "+" : ""}${delta.toFixed(1)}`;
}
