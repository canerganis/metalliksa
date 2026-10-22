import React, { useEffect, useMemo, useState } from 'react';
import { FlaskConical } from 'lucide-react';
import { sourceMeasurements, SourceNotImportedError } from '../services/lpbfSourceService';
import { useLpbfEngineeringStore } from '../store/useLpbfEngineeringStore';
import { aggregateByVelocity, overlayGate, residualAt, CMU_OVERLAY_SCOPE, MEASURED_DEPTH_LABEL, DEPTH_NOT_COMPARABLE_REASON, describePowers, type MeasuredRow, type ResidualQuantity, type Residual } from '../utils/experimentalValidation';
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceDot } from 'recharts';

const fmt = (v: number | null | undefined, d = 1) => v == null ? 'n/a' : v.toFixed(d);
export const ResidualRow: React.FC<{ label: string; q: ResidualQuantity | undefined }> = ({ label, q }) => (
  <tr>
    <td className="py-1 pr-4 text-slate-300">{label}</td>
    {q ? <>
      <td className="pr-4">{fmt(q.simulated)} µm</td>
      <td className="pr-4">{fmt(q.measuredMean)} µm (n={q.n}{q.sd == null ? ', spread n/a' : `, sd ${fmt(q.sd)}`})</td>
      <td className="pr-4">{q.residual >= 0 ? '+' : ''}{fmt(q.residual)} µm</td>
      <td>{q.withinRange ? 'inside measured range' : 'outside measured range'}</td>
    </> : <td colSpan={4} className="text-slate-400">Unavailable: no value for this quantity.</td>}
  </tr>
);
export const DepthRow: React.FC<{ q: NonNullable<Residual['depth']> | undefined }> = ({ q }) => (
  <tr>
    <td className="py-1 pr-4 text-slate-300">{MEASURED_DEPTH_LABEL}</td>
    {q ? <>
      <td className="pr-4">{fmt(q.simulated)} µm (simulated melt-pool depth)</td>
      <td className="pr-4">{fmt(q.measuredMean)} µm (n={q.n}{q.sd == null ? ', spread n/a' : `, sd ${fmt(q.sd)}`})</td>
      <td colSpan={2} className="text-amber-300">{DEPTH_NOT_COMPARABLE_REASON}</td>
    </> : <td colSpan={4} className="text-slate-400">Unavailable: no value for this quantity.</td>}
  </tr>
);

export const toLoadError = (err: unknown): { message: string; notImported: boolean } => ({
  message: err instanceof Error ? err.message : String(err), notImported: err instanceof SourceNotImportedError });

export const SourceLoadStatus: React.FC<{ error: { message: string; notImported: boolean } }> = ({ error }) => error.notImported ? (
  <div role="status" className="text-amber-200 space-y-1">
    <p className="font-semibold">The CMU Ti-6Al-4V measurement source is not imported in this installation.</p>
    <p className="text-sm">Prerequisite: download the raw files listed in data/benchmark/cmu-ti64-meltpool-v1/manifest.json into that folder's raw/ directory (see its README); the importer does not download anything.</p>
    <p className="text-sm">Then open LPBF Engineering, go to the Experimental Comparison stage, and use the Source Archive panel: under Local source select "CMU Single/Multi-track Meltpool Dimensions", choose Preview local source, then Import previewed source. Then reopen this view.</p>
  </div>
) : <p className="text-rose-400">Failed to load experimental data: {error.message}</p>;

export const ExperimentalValidationLab: React.FC = () => {
  const job = useLpbfEngineeringStore(state => state.job);
  const [data, setData] = useState<MeasuredRow[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [unresolved, setUnresolved] = useState<readonly string[]>([]);
  const [error, setError] = useState<{ message: string; notImported: boolean } | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    sourceMeasurements('cmu-ti64-meltpool-v1', controller.signal)
      .then(res => { if (!controller.signal.aborted) { setData(res.data); setUnresolved(res.scope?.unresolved ?? []); setLoaded(true); } })
      .catch(err => { if (!controller.signal.aborted) setError(toLoadError(err)); });
    return () => controller.abort();
  }, []);

  const simResult = job?.result?.metrics;
  const simInput = job?.result?.settings;
  const aggregates = useMemo(() => aggregateByVelocity(data), [data]);
  const gate = overlayGate(simInput);
  const residual = useMemo(() => gate.eligible ? residualAt(aggregates, simInput?.speed_mm_s, simResult) : undefined, [gate.eligible, aggregates, simInput, simResult]);
  const powerLabel = useMemo(() => describePowers(data), [data]);
  const chartData = (key: 'width_um' | 'depth_um') => data.filter(d => d[key] != null && d.velocity_mms != null).map(d => ({ velocity_mms: d.velocity_mms, value: d[key] }));

  return (
    <section aria-labelledby="lpbf-experiment-heading" className="max-w-5xl mx-auto p-4 space-y-4">
      <div className="flex items-center gap-3 bg-cyan-950/40 p-4 rounded-xl border border-cyan-800/50">
        <FlaskConical aria-hidden="true" className="w-8 h-8 text-cyan-400 shrink-0" />
        <div>
          <h2 id="lpbf-experiment-heading" className="text-lg font-bold text-white">Melt Pool vs Published Measurements</h2>
          <p className="text-sm text-cyan-100">Compare traceable measurements with an identified simulation.</p>
        </div>
      </div>

      <div className="bg-slate-900/80 p-5 rounded-xl border border-slate-700 space-y-4">
        <h3 className="text-base font-semibold text-white">CMU Ti-6Al-4V multi-track, powder-entrained measurements ({powerLabel})</h3>
        {error ? (
          <SourceLoadStatus error={error} />
        ) : !loaded ? (
          <p className="text-slate-400">Loading experimental data...</p>
        ) : data.length === 0 ? (
          <p className="text-slate-400">No measurement rows were returned for this dataset; nothing to compare.</p>
        ) : (
          <>
            <div className="h-96 w-full mt-4">
              <ResponsiveContainer width="100%" height="100%">
                <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis type="number" dataKey="velocity_mms" name="Velocity" unit=" mm/s" stroke="#94a3b8" domain={['auto', 'auto']} />
                  <YAxis type="number" dataKey="value" name="Dimension" unit=" µm" stroke="#94a3b8" />
                  <Tooltip cursor={{ strokeDasharray: '3 3' }} contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155' }} />
                  <Legend />
                  <Scatter name="Exp Width" data={chartData('width_um')} fill="#38bdf8" />
                  <Scatter name={`Exp ${MEASURED_DEPTH_LABEL}`} data={chartData('depth_um')} fill="#fbbf24" />
                  {gate.eligible && simResult && simInput && (
                    <>
                      <ReferenceDot x={simInput.speed_mm_s} y={simResult.width_um} r={6} fill="#0ea5e9" stroke="white" label={{ value: 'Sim. width', position: 'top', fill: '#0ea5e9', fontSize: 10 }} />
                      <ReferenceDot x={simInput.speed_mm_s} y={simResult.depth_um} r={6} fill="#d97706" stroke="white" label={{ value: 'Sim. depth (not remelt depth)', position: 'top', fill: '#d97706', fontSize: 10 }} />
                    </>
                  )}
                </ScatterChart>
              </ResponsiveContainer>
            </div>

            <div className="overflow-x-auto">
              <table className="text-sm text-slate-200" aria-label="Measured melt pool per scan velocity">
                <caption className="text-left text-slate-400 pb-1">Per-velocity mean and sample standard deviation across all slices and orientations (not independent builds)</caption>
                <thead><tr className="text-left text-slate-400"><th className="pr-4">Velocity (mm/s)</th><th className="pr-4">Width mean ± sd (µm)</th><th className="pr-4">{MEASURED_DEPTH_LABEL} mean ± sd (µm)</th><th>n</th></tr></thead>
                <tbody>
                  {aggregates.map(a => (
                    <tr key={a.velocity_mms}>
                      <td className="pr-4">{a.velocity_mms}</td>
                      <td className="pr-4">{a.width ? `${fmt(a.width.mean)} ± ${a.width.sd == null ? 'n/a' : fmt(a.width.sd)}` : 'n/a'}</td>
                      <td className="pr-4">{a.depth ? `${fmt(a.depth.mean)} ± ${a.depth.sd == null ? 'n/a' : fmt(a.depth.sd)}` : 'n/a'}</td>
                      <td>{Math.max(a.width?.n ?? 0, a.depth?.n ?? 0)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}

        <div className="bg-slate-800 p-4 rounded-lg text-sm text-slate-300 space-y-2" aria-live="polite">
          <h4 className="font-semibold text-white">Current simulation vs these measurements</h4>
          {!simResult || !simInput ? (
            <p>Not compared: no simulation result is loaded. Run one in the Engineering workspace.</p>
          ) : !gate.eligible ? (
            <div>
              <p>Not compared: the current run is outside the measurement scope, so it is not drawn on the chart.</p>
              <ul className="list-disc pl-5">{gate.reasons.map(r => <li key={r}>{r}</li>)}</ul>
            </div>
          ) : residual?.available ? (
            <div className="overflow-x-auto">
              <p>Run at {residual.velocity_mms} mm/s. Residual = simulated minus measured mean.</p>
              <table><tbody>
                <ResidualRow label="Width" q={residual.width} />
                <DepthRow q={residual.depth} />
              </tbody></table>
            </div>
          ) : (
            <p>Drawn on the chart, residual unavailable: {residual?.reason}</p>
          )}
        </div>

        <div className="bg-slate-800 p-4 rounded-lg text-sm text-slate-300 space-y-1">
          <p><strong>Scope:</strong> the plotted rows come from MTMeasurements.csv (multi-track, powder-entrained cross sections, CMU Ti-6Al-4V, DOI 10.1184/R1/25696293.v1, CC BY 4.0). STMeasurements.csv is not plotted because it has no power column.</p>
          <p>Beam diameter, layer thickness, powder lot and thermal boundaries are not recorded in the CSV. The overlay requires Ti-6Al-4V, {CMU_OVERLAY_SCOPE.power_W} W (±{CMU_OVERLAY_SCOPE.powerTolerance_W} W) and a beam diameter of {CMU_OVERLAY_SCOPE.beamDiameter_um} µm (±{CMU_OVERLAY_SCOPE.beamTolerance_um} µm), the manufacturer-reported spot of the cited fatigue-coupon build (Miner et al., Addit. Manuf. 2024, sec. 2.2), which is not confirmed for these rows.</p>
          {unresolved.length > 0 && <p>Not recorded in the CSV (unresolved): {unresolved.join('; ')}.</p>}
          <p>Measured depth is the remelt depth of multi-track cross sections with the cap excluded; it is not the same quantity as the simulated melt-pool depth, so only width carries a residual.</p>
          <p>A single-track simulation compared with multi-track data is a comparison only, not validation; no accuracy is claimed.</p>
        </div>
      </div>
    </section>
  );
};
