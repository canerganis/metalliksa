import type { SimulationMode } from "../services/lpbfSimulationService";

/** Mode names and scope sentences shown in the LPBF thermal stage. Single source for the mode picker and the melt-pool summary card. */
export const SIMULATION_MODES: readonly { id: SimulationMode; name: string; scope: string }[] = [
  { id: "screening", name: "Quick Screening", scope: "Seconds · Rosenthal / Goldak · analytical conduction only · not eligible for experimental validation" },
  { id: "standard", name: "Standard Simulation", scope: "Seconds to minutes · OpenFOAM or reference enthalpy FV · phase change and thermal history · numerical only; flow unresolved" },
  { id: "high-fidelity", name: "High-Fidelity CFD", scope: "Free-surface CFD unavailable · falls back to Screening only · no solved velocity or keyhole" },
  { id: "calibration", name: "Calibration / Validation", scope: "Transient thermal + measured comparison · matching process vector required for calibration · independent validation pending" },
];

/** The expected-fidelity and limitations sentence of a mode (same text as the mode picker). */
export function simulationModeLimitations(mode: SimulationMode): string {
  return mode === "screening" || mode === "high-fidelity"
    ? "Analytical geometry · literature-based approximation. No transient field or resolved keyhole."
    : "Unvalidated transient thermal · enthalpy phase change. Free-surface, velocity and stress not solved.";
}
