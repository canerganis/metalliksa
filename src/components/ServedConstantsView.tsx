import React from "react";
import DATA_TO_USER from "../generated/dataToUser.json";

const UNITS: Record<string, string> = { C: "°C", kg_m3: "kg/m³", W_mK: "W/(m K)", J_kgK: "J/(kg K)", J_kg: "J/kg", kg_mol: "kg/mol", N_mK: "N/(m K)", N_m: "N/m", Pa_s: "Pa s", "1_K": "1/K", GPa: "GPa" };
export function constantLabel(key: string): string {
  const suffix = Object.keys(UNITS).sort((a, b) => b.length - a.length).find(unit => key.endsWith(`_${unit}`));
  if (suffix) return `${key.slice(0, -suffix.length - 1).replaceAll("_", " ")} (${UNITS[suffix]})`;
  const dimensionless = ["absorptivity_IR", "absorptivity_Green", "absorptivity_index_IR", "emissivity", "poissons_ratio"].includes(key);
  return `${key.replaceAll("_", " ")} (${dimensionless ? "dimensionless" : "unit unresolved"})`;
}

export function ServedConstantsView() {
  return <section className="rounded-xl border border-slate-400 bg-white p-4 text-slate-800 space-y-3" aria-labelledby="served-constants-heading">
    <h2 id="served-constants-heading" className="font-semibold">Served constants and sources</h2>
    <p className="text-sm">Read-only Python constant-property tables. Source labels describe input evidence, not experimental validation. Unresolved values have no admitted source for this value and scope. Kernel property reductions can depend on temperature.</p>
    {DATA_TO_USER.alloys.map(alloy => <details key={alloy.id} className="border-t border-slate-300 pt-2">
      <summary className="cursor-pointer font-medium">{alloy.name}</summary>
      <p className="text-sm my-2">Registry: {alloy.registry.quality}. {alloy.registry.note}</p>
      {alloy.id === "in625" && <p className="text-sm">IN625 uses the secondary Rosenthal constant-property row. Other served paths hold different values; these paths are not reconciled.</p>}
      <div className="overflow-x-auto" tabIndex={0} aria-label={`${alloy.name}: served constants`}>
        <table className="w-full text-sm text-left"><caption className="text-left">{alloy.name}: served constants</caption>
          <thead><tr>{["Quantity and unit", "Value", "Source", "Locator", "Evidence kind", "Scope and basis"].map(s => <th key={s} scope="col" className="p-2">{s}</th>)}</tr></thead>
          <tbody>{alloy.constants.map(c => <tr key={c.quantity} className="border-t border-slate-200 align-top"><th scope="row" className="p-2 font-normal">{constantLabel(c.quantity)}</th><td className="p-2">{c.value}</td><td className="p-2">{c.source}</td><td className="p-2">{c.locator}</td><td className="p-2">{c.sourceEvidenceKind}</td><td className="p-2">{c.scope} ({c.basis}) {c.note}</td></tr>)}</tbody>
        </table>
      </div>
    </details>)}
  </section>;
}
