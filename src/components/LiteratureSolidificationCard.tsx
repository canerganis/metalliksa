import { checkedQuantityContainer } from "../data/quantityEnvelope";
import { SolidificationQuantities } from "./SolidificationQuantities";
import React from "react";

// Read-only literature solidification estimate for IN718 / IN625, shown under an unavailable CALPHAD result or
// beside a successful one (then with the comparison note).
// Python (python/calphad_solver.py literature_solidification_block, fed by lpbf_solidification_segregation.py)
// decides everything; this card displays those fields and computes nothing. It is not a CALPHAD result.

interface KValue {
  id?: string;
  value?: number | null;
  unit?: string | null;
  citation?: string | null;
  locator?: string | null;
}

interface BandPoint {
  label?: string;
  Nb_wt?: number | null;
  binaryUpperBound?: { fGammaLavesConstituent?: number | null } | null;
  pseudoTernaryAtCmax?: {
    status?: string | null;
    reason?: string | null;
    fGammaLavesConstituent?: number | null;
    fGammaNbCConstituent?: number | null;
  } | null;
}

interface SourceRef {
  citation?: string | null;
  url?: string | null;
}

export interface LiteratureSolidificationLike {
  status?: string;
  reason?: string | null;
  alloyId?: string | null;
  source?: string | null;
  primarySource?: SourceRef | null;
  secondarySource?: SourceRef | null;
  kValues?: KValue[] | null;
  kSensitivity?: {
    note?: string | null;
    [key: string]: { k?: number | null; band?: { label?: string; fGammaLavesConstituent?: number | null }[] | null } | string | null | undefined;
  } | null;
  band?: BandPoint[] | null;
  bandNote?: string | null;
  quantity?: string | null;
  upperBoundNote?: string | null;
  rapidSolidificationNote?: string | null;
  validity?: {
    outsideSourceRegime?: boolean;
    outsideSourceRegimeReason?: string | null;
    sourceRegime?: string | null;
    outsideSourceComposition?: boolean;
    outsideSourceCompositionReasons?: string[] | null;
    kTransferNote?: string | null;
  } | null;
}

const fin = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);
const pct = (v: unknown) => (fin(v) ? `${(v * 100).toFixed(1)} %` : "—");
const num = (v: unknown, digits = 2) => (fin(v) ? v.toFixed(digits) : "—");

export const LITERATURE_VS_CALPHAD_NOTE =
  "Not comparable directly: the CALPHAD Scheil phase amounts are mole percent of atoms with composition sets merged " +
  "(the IN718 Laves amount is minimiser-sensitive and marked do-not-use in the known deviations), while the literature " +
  "γ/Laves figure is the constituent fraction of the liquid and includes the eutectic γ.";

export const LiteratureSolidificationCard: React.FC<{ literature: unknown; alongsideCalphad?: boolean }> = ({ literature, alongsideCalphad = false }) => {
  const headingId = React.useId();
  if (!literature || typeof literature !== "object" || Array.isArray(literature)) return null;
  const s = literature as LiteratureSolidificationLike;
  let available = s.status === "computed";
  if (available) {
    try { checkedQuantityContainer(s); } catch { available = false; }
  }
  const band = Array.isArray(s.band) ? s.band : [];
  const v = s.validity ?? null;
  return (
    <section
      className="lg:col-span-8 p-4 rounded-2xl bg-[#090e18] border border-[#1e2d46] text-xs text-slate-300 space-y-2"
      aria-labelledby={headingId}
      data-testid="calphad-literature-solidification"
      data-lit-status={s.status ?? "unavailable"}
      data-lit-alloy={s.alloyId ?? ""}
      data-lit-alongside-calphad={alongsideCalphad ? "true" : "false"}
    >
      <h3 id={headingId} className="text-sm font-bold text-white">
        Literature solidification estimate (not CALPHAD)
      </h3>
      {alongsideCalphad && (
        <p className="text-[10px] text-sky-200 rounded border border-sky-400/40 p-2" role="note" data-lit-comparison-note>
          {LITERATURE_VS_CALPHAD_NOTE}
        </p>
      )}
      {!available ? (
        <p className="text-[11px] text-slate-400" data-lit-note="unavailable">Unavailable — {s.reason ?? "no literature block"}</p>
      ) : (
        <>
          <SolidificationQuantities container={s} frontOnly={false} />
          {s.source && <p className="text-[10px] text-slate-400" data-lit-source>Source: {s.source}</p>}
          <ul className="space-y-0.5 text-[11px]" data-lit-k>
            {(s.kValues ?? []).map((k, i) => (
              <li key={k.id ?? i} data-lit-k-row={k.id}>
                k<sub>{(k.id ?? "").replace(/^k_gamma_/, "γ ").replace(/_slopes$/, " (liquidus/solidus slopes)")}</sub> = {num(k.value, 2)} — {k.citation}
                {k.locator ? <span className="text-slate-500">, {k.locator}</span> : null}
              </li>
            ))}
          </ul>
          {s.kSensitivity && (
            <p className="text-[10px] text-slate-400" data-lit-k-sensitivity>
              {Object.entries(s.kSensitivity)
                .filter(([key, e]) => key !== "note" && e && typeof e === "object")
                .map(([key, e]) => {
                  const entry = e as { k?: number | null; band?: { label?: string; fGammaLavesConstituent?: number | null }[] | null };
                  return (
                    <span key={key}>
                      k<sub>Nb</sub> = {num(entry.k, 2)}: {(entry.band ?? []).map((p) => `${p.label} ${pct(p.fGammaLavesConstituent)}`).join(", ")}.{" "}
                    </span>
                  );
                })}
              {s.kSensitivity.note ? <span className="text-slate-500">({s.kSensitivity.note})</span> : null}
            </p>
          )}
          <table className="w-full text-[10px] text-slate-300 border-collapse" data-lit-band>
            <caption className="text-left text-[10px] text-slate-500 pb-1">
              Upper bound (equilibrium k): terminal eutectic-type fraction of the liquid over the specification Nb band
            </caption>
            <thead>
              <tr className="text-slate-500">
                <th scope="col" className="text-left font-normal">Nb (wt%)</th>
                <th scope="col" className="text-left font-normal">γ/Laves, C = 0</th>
                <th scope="col" className="text-left font-normal">γ/Laves at C max</th>
                <th scope="col" className="text-left font-normal">γ/NbC at C max</th>
              </tr>
            </thead>
            <tbody>
              {band.map((p, i) => {
                const t = p.pseudoTernaryAtCmax ?? null;
                const ok = t && !t.status;
                return (
                  <tr key={p.label ?? i} data-lit-band-row={p.label}>
                    <th scope="row" className="text-left font-normal">
                      {num(p.Nb_wt, 3)} <span className="text-slate-500">({p.label})</span>
                    </th>
                    <td>{pct(p.binaryUpperBound?.fGammaLavesConstituent)}</td>
                    <td>{ok ? pct(t.fGammaLavesConstituent) : `— ${t?.reason ?? ""}`}</td>
                    <td>{ok ? pct(t.fGammaNbCConstituent) : "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {s.bandNote && <p className="text-[9px] text-slate-500">{s.bandNote}</p>}
          {s.quantity && <p className="text-[9px] text-slate-500">{s.quantity}</p>}
          {s.upperBoundNote && <p className="text-[10px] text-slate-400" data-lit-upper-bound>{s.upperBoundNote}</p>}
          {s.rapidSolidificationNote && (
            <p className="text-[10px] text-slate-400" data-lit-rapid-note>{s.rapidSolidificationNote}</p>
          )}
          {v && (
            <div className="rounded border border-amber-500/40 p-2 text-[10px] text-amber-200 space-y-1" role="note" data-lit-validity>
              {v.outsideSourceRegime && <p>Outside the source regime — {v.outsideSourceRegimeReason}</p>}
              {v.outsideSourceComposition && (v.outsideSourceCompositionReasons ?? []).length > 0 && (
                <ul className="list-disc pl-4">
                  {(v.outsideSourceCompositionReasons ?? []).map((r) => (
                    <li key={r}>{r}</li>
                  ))}
                </ul>
              )}
              {v.kTransferNote && <p>{v.kTransferNote}</p>}
            </div>
          )}
        </>
      )}
    </section>
  );
};
