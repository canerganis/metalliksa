import React, { useMemo, useState } from "react";
import { Database, ShieldAlert } from "lucide-react";
import {
  MEASURED_TRACK_INTAKE_FIELDS,
  MELT_POOL_LITERATURE_CASES,
} from "../data/meltPoolLiteratureCases";
import { BlindTestCallToAction } from "./research/BlindTestLink";

type IntakeRow = {
  material: string;
  laserPower_W: string;
  scanSpeed_mm_s: string;
  beamDiameter_um: string;
  preheatTemp_C: string;
  width_um: string;
  depth_um: string;
  doi: string;
  source: string;
};

const EMPTY: IntakeRow = {
  material: "AlSi10Mg",
  laserPower_W: "",
  scanSpeed_mm_s: "",
  beamDiameter_um: "",
  preheatTemp_C: "",
  width_um: "",
  depth_um: "",
  doi: "",
  source: "",
};

function coverageFor(material: string): string {
  const measured = MELT_POOL_LITERATURE_CASES.some(
    (c) => c.material === material && c.kind === "measured",
  );
  if (measured) return "measured DOI W/D";
  const gap = MELT_POOL_LITERATURE_CASES.find(
    (c) => c.material === material && c.kind === "no-measured-track",
  );
  if (gap) return "no measured track";
  const asym = MELT_POOL_LITERATURE_CASES.find(
    (c) => c.material === material && c.kind === "asymptotic",
  );
  if (asym) return "asymptotic only (not a micrograph)";
  return "unlisted";
}

export function validateMeasuredTrackIntake(row: IntakeRow): { ok: boolean; reason: string } {
  const blob = `${row.source} ${row.doi} ${row.material}`.toLowerCase();
  if (blob.includes("solver-echo") || blob.includes("jsonl") || blob.includes("randomized")) {
    return { ok: false, reason: "Solver-echo / randomized sweeps are not ground truth." };
  }
  for (const key of MEASURED_TRACK_INTAKE_FIELDS) {
    const val = row[key];
    if (!String(val ?? "").trim()) {
      return { ok: false, reason: `Missing ${key}. Do not invent the number.` };
    }
  }
  if (!row.doi.includes("10.")) {
    return { ok: false, reason: "Resolvable DOI required." };
  }
  const numericKeys: (keyof IntakeRow)[] = [
    "laserPower_W",
    "scanSpeed_mm_s",
    "beamDiameter_um",
    "preheatTemp_C",
    "width_um",
    "depth_um",
  ];
  for (const key of numericKeys) {
    const n = Number(row[key]);
    if (!Number.isFinite(n) || n <= 0) {
      return { ok: false, reason: `${key} must be a positive number from the paper table.` };
    }
  }
  return { ok: true, reason: "Candidate is complete. Catalog ingest is a code change after table transcription — not a solver fit." };
}

export const MeltPoolMeasuredTrackPanel: React.FC = () => {
  const [row, setRow] = useState<IntakeRow>(EMPTY);
  const check = useMemo(() => validateMeasuredTrackIntake(row), [row]);
  const alloys = ["Ti-6Al-4V", "316L Stainless Steel", "AlSi10Mg", "Inconel 718"];

  return (
    <div className="bg-[#090e18] border border-[#1e2d46] rounded-2xl p-5 space-y-4">
      <div className="flex items-start gap-3">
        <div className="w-9 h-9 rounded-xl bg-sky-500/15 border border-sky-500/30 flex items-center justify-center text-sky-300">
          <Database className="w-4 h-4" />
        </div>
        <div>
          <h3 className="text-sm font-bold text-white">Melt-pool measured-track collector</h3>
          <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
            Intake for isolated single-track W/D with P, v, spot d, T0, and a DOI. Solver-echo JSONL
            batches are rejected. This panel does not generate sweeps and does not re-score Build Job.
          </p>
        </div>
      </div>

      <BlindTestCallToAction />

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">
        {alloys.map((alloy) => (
          <div key={alloy} className="p-2.5 rounded-xl border border-slate-800 bg-[#050810]">
            <div className="text-[10px] uppercase tracking-wide text-slate-500">{alloy}</div>
            <div className="text-xs font-bold text-slate-100 mt-1">{coverageFor(alloy)}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        {(
          [
            ["material", "Material"],
            ["laserPower_W", "P (W)"],
            ["scanSpeed_mm_s", "v (mm/s)"],
            ["beamDiameter_um", "Spot d (µm)"],
            ["preheatTemp_C", "T0 (°C)"],
            ["width_um", "Measured W (µm)"],
            ["depth_um", "Measured D (µm)"],
            ["doi", "DOI"],
          ] as const
        ).map(([key, label]) => (
          <label key={key} className="text-[10px] text-slate-400 space-y-1">
            <span>{label}</span>
            <input
              value={row[key]}
              onChange={(e) => setRow((prev) => ({ ...prev, [key]: e.target.value }))}
              className="w-full bg-[#050810] border border-slate-800 rounded-lg px-2 py-1.5 text-xs text-slate-100"
              placeholder={key === "material" ? "AlSi10Mg" : ""}
            />
          </label>
        ))}
      </div>
      <label className="block text-[10px] text-slate-400 space-y-1">
        <span>Source line (table / figure id — no invented numbers)</span>
        <input
          value={row.source}
          onChange={(e) => setRow((prev) => ({ ...prev, source: e.target.value }))}
          className="w-full bg-[#050810] border border-slate-800 rounded-lg px-2 py-1.5 text-xs text-slate-100"
          placeholder="Author year Table N row …"
        />
      </label>

      <div
        className={`flex items-start gap-2 text-[11px] rounded-lg border px-3 py-2 ${
          check.ok ? "border-emerald-800 bg-emerald-950/30 text-emerald-200" : "border-amber-800 bg-amber-950/20 text-amber-200"
        }`}
      >
        <ShieldAlert className="w-3.5 h-3.5 mt-0.5 shrink-0" />
        <span>{check.reason}</span>
      </div>
    </div>
  );
};
