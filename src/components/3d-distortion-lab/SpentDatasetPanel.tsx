import React, { useState } from "react";
import { DATA_TO_USER, SPENT_BADGE, SPENT_ENTRIES, spentPoints, isOpenDataset, signedDeviation, type SpentPoint } from "../../data/spentDatasets";

function DepthCurve({ points }: { points: SpentPoint[] }) {
  const maxX = Math.max(1, ...points.map(p => p.speed));
  const maxY = Math.max(1, ...points.flatMap(p => [p.measured, p.sample?.depth_um ?? 0]));
  const x = (v: number) => 60 + v / maxX * 540;
  const y = (v: number) => 270 - v / maxY * 240;
  // Connect only samples with the same fixed power and beam. Never join missing extents.
  const groups = new Map<string, SpentPoint[]>();
  for (const point of points) {
    const key = `${point.power}/${point.beam}`;
    groups.set(key, [...(groups.get(key) ?? []), point]);
  }
  return <svg viewBox="0 0 640 320" role="img" aria-label="Measured depth points and served model samples by scan speed" className="w-full max-w-3xl">
    <path d="M60 20V270H610" fill="none" stroke="currentColor" />
    {[0, 0.5, 1].map(f => <g key={f} fill="currentColor" fontSize="12">
      <text x={x(f * maxX)} y="290" textAnchor="middle">{(f * maxX).toFixed(0)}</text>
      <text x="52" y={y(f * maxY)} textAnchor="end">{(f * maxY).toFixed(0)}</text>
    </g>)}
    {[...groups].map(([key, group]) => {
      const sorted = [...group].sort((a, b) => a.speed - b.speed);
      return <g key={key}>
        {sorted.slice(1).map((p, i) => {
          const previous = sorted[i];
          return p.sample?.depth_um != null && previous.sample?.depth_um != null
            ? <line key={p.id} x1={x(previous.speed)} y1={y(previous.sample.depth_um)} x2={x(p.speed)} y2={y(p.sample.depth_um)} stroke="#1d4ed8" /> : null;
        })}
        {sorted.map(p => <g key={p.id}><title>{`${p.id}: ${p.power} W, ${p.speed} mm/s, ${p.beam} µm`}</title>
          <circle cx={x(p.speed)} cy={y(p.measured)} r="4" fill="#b45309" />
          {p.sample?.depth_um != null && <rect x={x(p.speed) - 3} y={y(p.sample.depth_um) - 3} width="6" height="6" fill="#1d4ed8" />}
        </g>)}
      </g>;
    })}
    <text x="330" y="315" textAnchor="middle" fill="currentColor" fontSize="13">Scan speed (mm/s)</text>
    <text x="15" y="150" transform="rotate(-90 15 150)" textAnchor="middle" fill="currentColor" fontSize="13">Depth (µm)</text>
  </svg>;
}

export function SpentDatasetPanel() {
  const [datasetId, setDatasetId] = useState(SPENT_ENTRIES[0].datasetId);
  const entry = SPENT_ENTRIES.find(e => e.datasetId === datasetId)!;
  const points = spentPoints(entry);
  return <section className="space-y-4 p-4 text-slate-800 bg-white rounded-xl border border-slate-200" aria-labelledby="spent-heading">
    <h2 id="spent-heading" className="text-lg font-semibold">Collected datasets (SPENT)</h2>
    <p className="inline-block rounded border border-amber-700 bg-amber-50 p-2 text-sm text-amber-900">{SPENT_BADGE}</p>
    <label className="block text-sm">Dataset
      <select aria-label="Dataset" value={datasetId} onChange={e => setDatasetId(e.target.value)} className="block w-full rounded border border-slate-400 bg-white p-2">
        {SPENT_ENTRIES.map(e => <option key={e.datasetId} value={e.datasetId}>{e.datasetId} ({e.alloy})</option>)}
      </select>
    </label>
    <h3 className="font-semibold">{entry.title}</h3>
    <dl className="grid gap-2 text-sm sm:grid-cols-[9rem_1fr]">
      <dt>Source</dt><dd><a className="text-blue-800 underline" href={`https://doi.org/${entry.doi}`} target="_blank" rel="noreferrer">{entry.doi}</a></dd>
      <dt>Locator</dt><dd>{entry.locator}</dd>
      <dt>Licence</dt><dd>{entry.licence}</dd>
      <dt>Attribution</dt><dd>{entry.attribution}</dd>
      <dt>Observable</dt><dd>{entry.observable}</dd>
      <dt>Depth datum</dt><dd>{entry.datum}</dd>
      <dt>Beam</dt><dd>{entry.beam.definition} ({entry.beam.status})</dd>
      <dt>Power basis</dt><dd>{entry.powerBasis}</dd>
      <dt>Substrate</dt><dd>{entry.substrate}</dd>
      <dt>Transcription</dt><dd>{entry.transcription}</dd>
      <dt>Prior use</dt><dd>{entry.spentBy.map((s, i) => <p key={i}>{s.date}: {s.event}</p>)}</dd>
      <dt>Inferred inputs</dt><dd>{entry.inputsInferred.length ? entry.inputsInferred.map((v, i) => <p key={i}>{v.input}: {v.method} ({v.locator})</p>) : "None recorded"}</dd>
    </dl>
    {!isOpenDataset(entry) ? <p>Metadata and source link only. No open licence is recorded for this set.</p> : <>
      <p className="text-sm">Served path: Rosenthal screening with flat-plate absorption. Blue squares and lines: served model samples. Brown circles: measured depth. Lines connect samples at fixed power and beam diameter only.</p>
      <details className="text-sm break-all"><summary className="cursor-pointer">Model record source</summary><p>rosenthal-screening-v1: python/lpbf_thermal_solver.py</p><p>SHA-256 (LF): {DATA_TO_USER.sourceHashes["python/lpbf_thermal_solver.py"]}</p></details>
      <p className="text-sm">NIST uses the recorded 23.5 °C substrate temperature. Other sets use an assumed 20 °C. Missing layer thickness uses a 40 µm placeholder; hatch spacing uses a 100 µm placeholder. These placeholders do not enter the single-track geometry. Beam definitions and depth datums have not been reconciled.</p>
      {points.length ? <><DepthCurve points={points} />
        <div className="overflow-x-auto" tabIndex={0} aria-label="Depth comparison table">
          <table className="w-full text-sm text-left"><caption className="text-left py-2">Signed deviation = served depth minus measured depth (µm). No experimental validation is claimed.</caption>
            <thead><tr>{["Condition", "Power (W)", "Scan speed (mm/s)", "Beam diameter (µm)", "Measured depth (µm)", "Served depth (µm)", "Signed deviation (µm)"].map(t => <th scope="col" className="p-2" key={t}>{t}</th>)}</tr></thead>
            <tbody>{points.map(p => <tr key={p.id} className="border-t border-slate-200"><th scope="row" className="p-2 font-normal">{p.id}</th><td>{p.power}</td><td>{p.speed}</td><td>{p.beam}</td><td>{p.measured.toFixed(1)}</td><td>{p.sample?.depth_um?.toFixed(1) ?? "Unavailable"}{p.sample?.depth_um == null && p.sample?.extentNote ? `: ${p.sample.extentNote}` : ""}</td><td>{signedDeviation(p)}</td></tr>)}</tbody>
          </table>
        </div></> : <p>No measurement rows are available in this view.</p>}
    </>}
  </section>;
}
