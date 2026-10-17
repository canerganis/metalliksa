import React from "react";
import { EstimateWarnings } from "./SolidificationEstimates";

// Display of the calibration status and the uncalibrated parent returned by POST /api/python/lpbf-calibrated-meltpool.
// Every sentence comes from the payload (python/lpbf_calibrated_meltpool.py). Nothing here computes or derives a number
// beyond rounding to the payload's significant digits, and a calibrated value is never shown from this component.

export interface CalibrationCellStatus {
  readonly status: string;
  readonly statusText: string;
  readonly eligible: boolean;
  readonly text: string;
}

export interface CalibrationStatusPayload {
  readonly artifact: {
    readonly state: "ready" | "stale" | "unavailable" | "not-requested";
    readonly detail?: string | null;
    readonly calibrationId?: string | null;
    readonly text?: string | null;
  };
  readonly cells: { readonly width?: CalibrationCellStatus; readonly depth?: CalibrationCellStatus };
  readonly enabledCellCount: number | null;
}

export interface UncalibratedParentPayload {
  readonly estimateTier?: string;
  readonly tierLabel: string;
  readonly width_um: number | null;
  readonly depth_um: number | null;
  readonly displaySignificantDigits: number;
  readonly domainWarnings: readonly string[];
  readonly uncertaintyStatement?: string;
  readonly explanation: string | null;
  readonly noValueText: string | null;
  readonly regime?: string | null;
}

export function roundSignificant(value: number, digits: number): string {
  return String(Number(value.toPrecision(Math.max(1, digits))));
}

export function UncalibratedParentView({ parent }: { parent: UncalibratedParentPayload }) {
  const hasValue = parent.width_um !== null && parent.depth_um !== null;
  const d = parent.displaySignificantDigits;
  return (
    <div data-testid="uncalibrated-parent" className="space-y-1 rounded-xl border border-slate-800 bg-[#050810] p-2 text-xs">
      <span data-testid="uncalibrated-tier" className="block text-[10px] font-semibold uppercase text-slate-400">{parent.tierLabel}</span>
      {hasValue ? (
        <div className="grid grid-cols-2 gap-2">
          <div>
            <span className="block text-[10px] text-slate-400">Width (W)</span>
            <strong data-testid="uncal-width" className="text-sm text-slate-100">{roundSignificant(parent.width_um!, d)} µm</strong>
          </div>
          <div>
            <span className="block text-[10px] text-slate-400">Depth (D)</span>
            <strong data-testid="uncal-depth" className="text-sm text-slate-100">{roundSignificant(parent.depth_um!, d)} µm</strong>
          </div>
        </div>
      ) : <p data-testid="uncal-no-value" className="text-[11px] text-amber-200">{parent.noValueText ?? "No uncalibrated estimate is available."}</p>}
      {parent.domainWarnings.length > 0 ? <dl><EstimateWarnings warnings={parent.domainWarnings} /></dl> : null}
      {hasValue && parent.explanation ? <p data-testid="uncal-explanation" className="text-[11px] text-slate-300">{parent.explanation}</p> : null}
    </div>
  );
}

function CellStatusLine({ label, cell }: { label: string; cell: CalibrationCellStatus | undefined }) {
  if (!cell) return null;
  return (
    <li data-testid={`cal-cell-${label}`} className="text-[11px] text-slate-300">
      <strong className="capitalize">{label}</strong>: {cell.statusText}. <span data-testid={`cal-cell-${label}-text`}>{cell.text}</span>
    </li>
  );
}

export function CalibrationStatusDisplay({ status, parent }: { status?: CalibrationStatusPayload | null; parent?: UncalibratedParentPayload | null }) {
  if (!status && !parent) return null;
  return (
    <div data-testid="calibration-status-display" className="space-y-2">
      {parent ? <UncalibratedParentView parent={parent} /> : null}
      {status ? (
        <div data-testid="calibration-artifact-status" data-state={status.artifact.state} className="space-y-1 text-[11px]">
          {status.artifact.text ? <p data-testid="calibration-artifact-text" className="text-amber-200">{status.artifact.text}</p> : null}
          {status.enabledCellCount !== null ? <p data-testid="calibration-enabled-count" className="text-slate-400">Enabled calibration cells: {status.enabledCellCount}</p> : null}
          <ul className="space-y-0.5">
            <CellStatusLine label="width" cell={status.cells.width} />
            <CellStatusLine label="depth" cell={status.cells.depth} />
          </ul>
        </div>
      ) : null}
    </div>
  );
}
