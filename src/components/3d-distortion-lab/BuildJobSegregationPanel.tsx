import { checkedQuantityContainer } from "../../data/quantityEnvelope";
import type { QuantitySourceEvidenceKind } from "../../generated/quantityEnvelope";
import { SolidificationQuantities } from "../SolidificationQuantities";
import type { QuantityContainer } from "../../data/quantityEnvelope";
import { QUANTITY_ENVELOPE } from "../../generated/quantityEnvelope";
import React from "react";
import { FlaskConical } from "lucide-react";

// Build-job Nb segregation / terminal gamma-Laves screening (python/lpbf_solidification_segregation.py
// build_job_segregation). Python decides everything: status "available" (IN718: DuPont, Robino & Marder 1998 (Acta Mater 46, Table 2)
// pseudo-ternary model; IN625: binary Scheil, k_Nb Cieslak 1988, C_e DuPont 1996, no risk class; both
// Literature estimate (screening)), "unavailable" (reason only, e.g. constants not verified
// against a primary source) or "not-applicable" (no Nb-bearing gamma/Laves model for the alloy). This panel only
// displays those decisions; it never computes a fraction and shows no number unless the status is "available".
// The optional rapidSolidification sub-block (Aziz k(V), V_D range from Ghosh et al. 2017, screening) is shown beside
// the equilibrium-k upper bound, never instead of it; lpbfObservations lists as-built LPBF IN625 literature data.

interface SegBandEntry {
  C_wt?: number | null;
  fGammaLavesConstituent?: number | null;
  fGammaNbCConstituent?: number | null;
  fEutecticTotal?: number | null;
  riskClass?: string | null;
  status?: string | null;
  reason?: string | null;
}

interface SegBandPoint {
  label?: string;
  Nb_wt?: number | null;
  binaryUpperBound?: SegBandEntry | null;
  pseudoTernaryAtCmax?: SegBandEntry | null;
}

interface RapidBandPoint {
  label?: string;
  Nb_wt?: number | null;
  binary?: { fGammaLavesConstituent?: number | null } | null;
  pseudoTernaryAtCmax?: { fGammaLavesConstituent?: number | null; fGammaNbCConstituent?: number | null; status?: string | null } | null;
}

interface RapidSolidificationLike {
  status?: string | null;
  reason?: string | null;
  evidenceLabel?: string | null;
  model?: { equation?: string | null; locator?: string | null } | null;
  V_D_m_s?: { min?: number | null; max?: number | null; nature?: string | null } | null;
  R_m_s?: number | null;
  k_e?: number | null;
  kEff?: { min?: number | null; max?: number | null } | null;
  byVD?: {
    V_D_m_s?: number | null;
    kEff?: number | null;
    band?: RapidBandPoint[] | null;
    segregation?: { coreRatioToNominal?: number | null } | null;
  }[] | null;
  extrapolationNote?: string | null;
  kTransferNote?: string | null;
}

interface LpbfObservationsLike {
  status?: string | null;
  reason?: string | null;
  evidenceKind?: string | null;
  observations?: {
    source?: string;
    quantity?: string | null;
    result?: string | null;
    Nb_wt?: { min?: number; max?: number } | null;
    locator?: string | null;
  }[] | null;
  comparison?: {
    Nb_wt?: number | null;
    equilibriumK?: { coreRatioToNominal?: number | null; fGammaLavesConstituent?: number | null } | null;
    kOfV?: {
      coreRatioToNominal?: { min?: number | null; max?: number | null } | null;
      fGammaLavesConstituent?: { min?: number | null; max?: number | null } | null;
    } | null;
    measured?: { lowestRatioToNominal?: number | null; highestRatioToNominal?: number | null } | null;
    note?: string | null;
  } | null;
}

export interface BuildJobSegregationLike {
  status?: string;
  reason?: string | null;
  alloyId?: string | null;
  schema?: string;
  quantityEnvelopeSchema?: string;
  sourceEvidenceKind?: QuantitySourceEvidenceKind | null;
  evidenceLabel?: string | null;
  k_Nb?: { value?: number | null; citation?: string | null; locator?: string | null } | null;
  band?: SegBandPoint[] | null;
  bandNote?: string | null;
  feBaseSensitivity?: { point?: SegBandPoint | null; note?: string | null; constants?: Record<string, { value?: number | null }> } | null;
  kSensitivity?: {
    note?: string | null;
    [key: string]: { k?: number | null; band?: { label?: string; fGammaLavesConstituent?: number | null }[] | null } | string | null | undefined;
  } | null;
  sourceComparison?: {
    c88?: { alloy?: string; fComputed?: number | null; fMeasured?: number | null; phasesObserved?: string | null }[] | null;
    c88Locator?: string | null;
  } | null;
  segregation?: {
    Nb_wt?: number | null;
    basis?: string | null;
    coreRatioToNominal?: number | null;
    interdendritic?: { fs?: number; liquidNb_wt?: number | null; ratioToNominal?: number | null; atEutecticComposition?: boolean }[] | null;
  } | null;
  riskClass?: string | null;
  riskClassRule?: string | null;
  processCoupling?: QuantityContainer | null;
  upperBoundNote?: string | null;
  sourceAgreementNote?: string | null;
  quantity?: string | null;
  binaryBoundNote?: string | null;
  validity?: {
    outsideSourceRegime?: boolean;
    outsideSourceRegimeReason?: string | null;
    sourceRegime?: string | null;
    outsideSourceComposition?: boolean;
    outsideSourceCompositionReasons?: string[] | null;
    kTransferNote?: string | null;
    ceTransferNote?: string | null;
    phaseIdentityNote?: string | null;
  } | null;
  rapidSolidification?: RapidSolidificationLike | null;
  lpbfObservations?: LpbfObservationsLike | null;
}

const KNOWN_STATUS: readonly string[] = QUANTITY_ENVELOPE.statuses;

const fin = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);
const pct = (v: unknown) => (fin(v) ? `${(v * 100).toFixed(1)} %` : "—");
const num = (v: unknown, digits = 2) => (fin(v) ? v.toFixed(digits) : "—");

function asBlock(value: unknown): BuildJobSegregationLike | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value as BuildJobSegregationLike;
}

export const BuildJobSegregationPanel: React.FC<{ segregation: unknown }> = ({ segregation }) => {
  const headingId = React.useId();
  const raw = asBlock(segregation);
  if (!raw) return null;
  // A block without a known status is never shown as available.
  let known = typeof raw.status === "string" && KNOWN_STATUS.includes(raw.status) && raw.schema === "lpbf-solidification-segregation-2";
  if (known) {
    try { checkedQuantityContainer(raw); } catch { known = false; }
  }
  const s: BuildJobSegregationLike = known ? raw : { status: "unavailable", reason: "segregation block without a known status" };
  return (
    <section className="space-y-2 border-t border-[#162032] pt-3 mt-2" aria-labelledby={headingId} data-seg-status={s.status}>
      <div className="flex items-center gap-2">
        <FlaskConical className="w-4 h-4 text-teal-400" aria-hidden="true" />
        <h4 id={headingId} className="text-xs font-bold text-white">Nb Segregation &amp; Laves (Scheil screening)</h4>
      </div>
      {s.status === "not-requested" ? (
        <p className="text-[11px] text-slate-400" data-seg-note="not-applicable">Not applicable — {s.reason}</p>
      ) : s.status !== "computed" ? (
        <p className="text-[11px] text-slate-400" data-seg-note="unavailable">Unavailable — {s.reason}</p>
      ) : (
        <><SolidificationQuantities container={raw} frontOnly={false} /><AvailableBody s={s} /></>
      )}
    </section>
  );
};

const AvailableBody: React.FC<{ s: BuildJobSegregationLike }> = ({ s }) => {
  const band = Array.isArray(s.band) ? s.band : [];
  const pc = s.processCoupling ?? null;
  const fe = s.feBaseSensitivity?.point ?? null;
  const v = s.validity ?? null;
  return (
    <>
      {s.evidenceLabel && (
        <p className="inline-block rounded border border-amber-400/60 px-2 py-0.5 text-[10px] text-amber-200" data-seg-label>
          {s.evidenceLabel}
        </p>
      )}
      <p className="text-[11px] text-slate-300" data-seg-k>
        k<sub>Nb</sub> = {num(s.k_Nb?.value, 2)} — {s.k_Nb?.citation}
        {s.k_Nb?.locator ? `, ${s.k_Nb.locator}` : ""}
      </p>
      <table className="w-full text-[10px] text-slate-300 border-collapse" data-seg-band>
        <caption className="text-left text-[10px] text-slate-500 pb-1">
          Terminal eutectic-type fractions over the specification Nb band (fraction of the liquid, %)
        </caption>
        <thead>
          <tr className="text-slate-500">
            <th scope="col" className="text-left font-normal">Nb (wt%)</th>
            <th scope="col" className="text-left font-normal">γ/Laves, C = 0 (binary; model upper bound over C only)</th>
            <th scope="col" className="text-left font-normal">γ/Laves at C max</th>
            <th scope="col" className="text-left font-normal">γ/NbC at C max</th>
          </tr>
        </thead>
        <tbody>
          {band.map((p, i) => {
            const t = p.pseudoTernaryAtCmax ?? null;
            const ternaryOk = t && !t.status;
            return (
              <tr key={p.label ?? i} data-seg-band-row={p.label}>
                <th scope="row" className="text-left font-normal">
                  {num(p.Nb_wt, 3)} <span className="text-slate-500">({p.label})</span>
                </th>
                <td>{pct(p.binaryUpperBound?.fGammaLavesConstituent)}</td>
                <td>{ternaryOk ? pct(t.fGammaLavesConstituent) : `— ${t?.reason ?? ""}`}</td>
                <td>{ternaryOk ? pct(t.fGammaNbCConstituent) : "—"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {s.bandNote && <p className="text-[9px] text-slate-500">{s.bandNote}</p>}
      {s.quantity && <p className="text-[9px] text-slate-500" data-seg-quantity>{s.quantity}</p>}
      {s.riskClass ? (
        <p className="text-[11px] text-slate-300" data-seg-risk>
          Laves risk class: <strong className="text-white">{s.riskClass}</strong>
          {s.riskClassRule ? <span className="text-slate-500"> ({s.riskClassRule})</span> : null}
        </p>
      ) : s.riskClassRule ? (
        <p className="text-[11px] text-slate-300" data-seg-risk="none">{s.riskClassRule}</p>
      ) : null}
      {s.segregation && (
        <p className="text-[11px] text-slate-300" data-seg-ratio>
          Segregation ratio C<sub>L</sub>/C<sub>0</sub> (Nb {num(s.segregation.Nb_wt, 3)} wt%): core k·C<sub>0</sub> ={" "}
          {num(s.segregation.coreRatioToNominal, 2)}
          {(s.segregation.interdendritic ?? []).map((r) => (
            <span key={String(r.fs)}>
              {" "}· f<sub>s</sub> = {num(r.fs, 2)}: {num(r.ratioToNominal, 2)}
              {r.atEutecticComposition ? " (capped at the γ/Laves composition)" : ""}
            </span>
          ))}
          {s.segregation.basis ? <span className="text-slate-500"> — {s.segregation.basis}</span> : null}
        </p>
      )}
      {fe && (
        <p className="text-[10px] text-slate-400" data-seg-sensitivity>
          Fe-base constant set (k<sub>Nb</sub> = {num(s.feBaseSensitivity?.constants?.k_gamma_Nb?.value, 2)}), nominal Nb: γ/Laves{" "}
          {pct(fe.binaryUpperBound?.fGammaLavesConstituent)} at C = 0, {pct(fe.pseudoTernaryAtCmax?.fGammaLavesConstituent)} at C max — {s.feBaseSensitivity?.note}
        </p>
      )}
      {s.kSensitivity && (
        <p className="text-[10px] text-slate-400" data-seg-k-sensitivity>
          {Object.entries(s.kSensitivity)
            .filter(([key, v]) => key !== "note" && v && typeof v === "object")
            .map(([key, v]) => {
              const e = v as { k?: number | null; band?: { label?: string; fGammaLavesConstituent?: number | null }[] | null };
              return (
                <span key={key}>
                  k<sub>Nb</sub> = {num(e.k, 2)}: {(e.band ?? []).map((p) => `${p.label} ${pct(p.fGammaLavesConstituent)}`).join(", ")}.{" "}
                </span>
              );
            })}
          {s.kSensitivity.note ? <span className="text-slate-500">({s.kSensitivity.note})</span> : null}
        </p>
      )}
      {(s.sourceComparison?.c88 ?? []).length > 0 && (
        <p className="text-[10px] text-slate-400" data-seg-source-comparison>
          Source comparison (computed vs measured):{" "}
          {(s.sourceComparison?.c88 ?? [])
            .map((r) => `alloy ${r.alloy}: ${pct(r.fComputed)} vs ${pct(r.fMeasured)} (${r.phasesObserved ?? "—"})`)
            .join("; ")}
          {s.sourceComparison?.c88Locator ? <span className="text-slate-500"> — {s.sourceComparison.c88Locator}</span> : null}
        </p>
      )}
      {pc && <div data-seg-coupling><SolidificationQuantities container={pc} /></div>}
      {v && (
        <div className="rounded border border-amber-500/40 p-2 text-[10px] text-amber-200 space-y-1" role="note" data-seg-validity>
          {v.outsideSourceRegime && <p>Outside the source regime — {v.outsideSourceRegimeReason}</p>}
          {v.outsideSourceComposition && (v.outsideSourceCompositionReasons ?? []).length > 0 && (
            <ul className="list-disc pl-4">
              {(v.outsideSourceCompositionReasons ?? []).map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          )}
          {v.phaseIdentityNote && <p data-seg-phase-identity>{v.phaseIdentityNote}</p>}
          {v.kTransferNote && <p>{v.kTransferNote}</p>}
          {v.ceTransferNote && <p>{v.ceTransferNote}</p>}
        </div>
      )}
      {s.upperBoundNote && <p className="text-[10px] text-slate-400" data-seg-upper-bound>{s.upperBoundNote}</p>}
      {s.sourceAgreementNote && (
        <p className="text-[10px] text-amber-200" data-seg-source-agreement>
          Agreement with the source measurements: {s.sourceAgreementNote}
        </p>
      )}
      {s.binaryBoundNote && <p className="text-[9px] text-slate-500">{s.binaryBoundNote}</p>}
      {s.rapidSolidification && <RapidSolidificationBody r={s.rapidSolidification} />}
      {s.lpbfObservations && <LpbfObservationsBody o={s.lpbfObservations} />}
    </>
  );
};

const span = (lo: unknown, hi: unknown, f: (v: unknown) => string) =>
  fin(lo) && fin(hi) && lo !== hi ? `${f(lo)} to ${f(hi)}` : f(lo);

const RapidSolidificationBody: React.FC<{ r: RapidSolidificationLike }> = ({ r }) => {
  const ok = r.status === "computed" || r.status === "partial";
  const rows = Array.isArray(r.byVD) ? r.byVD : [];
  const labels = (rows[0]?.band ?? []).map((p) => p.label);
  const withCmax = Boolean(rows[0]?.band?.[0]?.pseudoTernaryAtCmax);
  return (
    <div className="space-y-1 border-t border-[#162032] pt-2" data-seg-rapid={ok ? r.status : "unavailable"}>
      <p className="text-[11px] font-semibold text-slate-200">
        Rapid solidification: solute trapping k(V), shown beside the equilibrium-k upper bound (screening)
      </p>
      {!ok ? (
        <p className="text-[10px] text-slate-400">Unavailable — {r.reason}</p>
      ) : (
        <>
          {r.evidenceLabel && (
            <p className="inline-block rounded border border-amber-400/60 px-2 py-0.5 text-[10px] text-amber-200" data-seg-rapid-label>
              {r.evidenceLabel}
            </p>
          )}
          <p className="text-[10px] text-slate-300" data-seg-rapid-k>
            {r.model?.equation} ({r.model?.locator}); V<sub>D</sub> = {num(r.V_D_m_s?.min, 2)}–{num(r.V_D_m_s?.max, 2)} m/s; R ={" "}
            {num(r.R_m_s, 4)} m/s; k<sub>e</sub> = {num(r.k_e, 2)} → k(R) = {span(r.kEff?.min, r.kEff?.max, (v) => num(v, 3))}.
            {r.status === "screening-fallback" && r.reason ? ` Screening only — ${r.reason}` : ""}
          </p>
          <table className="w-full text-[10px] text-slate-300 border-collapse" data-seg-rapid-band>
            <caption className="text-left text-[10px] text-slate-500 pb-1">
              γ/Laves fraction with k(R), % of the liquid{withCmax ? " (C = 0 / C max)" : " (C = 0)"}
            </caption>
            <thead>
              <tr className="text-slate-500">
                <th scope="col" className="text-left font-normal">Nb band point</th>
                {rows.map((row) => (
                  <th key={String(row.V_D_m_s)} scope="col" className="text-left font-normal">
                    V<sub>D</sub> {num(row.V_D_m_s, 2)} m/s (k = {num(row.kEff, 3)})
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {labels.map((label, i) => (
                <tr key={label ?? i} data-seg-rapid-row={label}>
                  <th scope="row" className="text-left font-normal">{label}</th>
                  {rows.map((row) => {
                    const p = row.band?.[i];
                    const t = p?.pseudoTernaryAtCmax;
                    return (
                      <td key={String(row.V_D_m_s)}>
                        {pct(p?.binary?.fGammaLavesConstituent)}
                        {t ? ` / ${t.status ? "—" : pct(t.fGammaLavesConstituent)}` : ""}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
          <p className="text-[10px] text-slate-400" data-seg-rapid-core>
            Core ratio C<sub>s</sub>/C<sub>0</sub> = k(R):{" "}
            {rows.map((row) => `${num(row.segregation?.coreRatioToNominal, 3)} (V_D ${num(row.V_D_m_s, 2)} m/s)`).join(", ")}
          </p>
        </>
      )}
      <div className="rounded border border-amber-500/40 p-2 text-[10px] text-amber-200 space-y-1" role="note" data-seg-rapid-notes>
        {r.V_D_m_s?.nature && <p>{r.V_D_m_s.nature}</p>}
        {r.extrapolationNote && <p>{r.extrapolationNote}</p>}
        {r.kTransferNote && <p>{r.kTransferNote}</p>}
      </div>
    </div>
  );
};

const LpbfObservationsBody: React.FC<{ o: LpbfObservationsLike }> = ({ o }) => {
  if (o.status !== "computed") {
    return (
      <p className="text-[10px] text-slate-400" data-seg-lpbf="unavailable">
        LPBF observations: none — {o.reason}
      </p>
    );
  }
  const c = o.comparison ?? null;
  return (
    <div className="space-y-1 border-t border-[#162032] pt-2 text-[10px] text-slate-300" data-seg-lpbf="computed">
      <p className="text-[11px] font-semibold text-slate-200">As-built LPBF observations ({o.evidenceKind})</p>
      <ul className="list-disc pl-4 space-y-0.5">
        {(o.observations ?? []).map((ob, i) => (
          <li key={`${ob.source}-${i}`}>
            {ob.source}: {ob.quantity}
            {ob.Nb_wt ? ` — Nb ${num(ob.Nb_wt.min, 2)} to ${num(ob.Nb_wt.max, 2)} wt%` : ""}
            {ob.result ? ` — ${ob.result}` : ""}
            {ob.locator ? <span className="text-slate-500"> ({ob.locator})</span> : null}
          </li>
        ))}
      </ul>
      {c && (
        <p data-seg-lpbf-comparison>
          Comparison at Nb {num(c.Nb_wt, 2)} wt%: core ratio — equilibrium k {num(c.equilibriumK?.coreRatioToNominal, 3)}, k(V){" "}
          {span(c.kOfV?.coreRatioToNominal?.min, c.kOfV?.coreRatioToNominal?.max, (v) => num(v, 3))}, EDS lowest{" "}
          {num(c.measured?.lowestRatioToNominal, 3)} and highest {num(c.measured?.highestRatioToNominal, 3)}; γ/Laves — equilibrium k{" "}
          {pct(c.equilibriumK?.fGammaLavesConstituent)}, k(V){" "}
          {span(c.kOfV?.fGammaLavesConstituent?.min, c.kOfV?.fGammaLavesConstituent?.max, pct)}, measured fraction: none reported.{" "}
          <span className="text-amber-200">{c.note}</span>
        </p>
      )}
    </div>
  );
};
