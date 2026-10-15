import { quantityText } from "../../utils/solidificationDisplay";
import React, { useMemo } from "react";
import {
  Activity,
  AlertTriangle,
  Box,
  CheckCircle2,
  Clock,
  Cpu,
  Database,
  Gauge,
  Grid,
  Layers,
  RefreshCw,
  ShieldAlert,
  Thermometer,
  Zap,
} from "lucide-react";
import { useMaterialSpecimenStore } from "../../store/useMaterialSpecimenStore";
import { useLpbfBuildMeshStore } from "../../store/useLpbfBuildMeshStore";
import { useLpbfBuildJobPython } from "../../store/useLpbfBuildJobStore";
import {
  findNearestLiteratureRecord,
  inferSlicerPreset,
  literatureOverlayPoints,
  mapSpecimenToBuildJobMaterials,
  mapSpecimenToSolverMaterials,
  PrintVerdict,
  PRINT_VERDICT_SCREENING_LABEL,
} from "../../utils/lpbfIndustrialDecision";
import { mapActionableReasons, modelHonestyLine, toActionableHeadline } from "../../utils/lpbfActionableReasons";
import { heatTreatmentCohorts, orientationCohorts } from "../../utils/lpbfFourAlloySchema";
import type { PythonLpbfScreeningGate } from "../../services/pythonComputationService";
import { LPBF_DEMO_VECTORS } from "../../utils/lpbfDemoVectors";
import { MeltPoolExtentNotice } from "../MeltPoolExtentNotice";
import { DepthBiasNotice } from "../DepthBiasNotice";
import { isComputedMeltPoolExtent, meltPoolExtentInfo } from "../../utils/meltPoolExtentStatus";
import { BuildJobKineticsPanel } from "./BuildJobKineticsPanel";
import { MachineTileLine } from "./MachineTileLine";
import { BuildJobMicrostructurePanel } from "./BuildJobMicrostructurePanel";
import { STRESS_PROXY_LABEL, stressProxyPresentation } from "../../utils/residualStressYieldCheck";
import { STRESS_UNAVAILABLE_NOTE } from "../../utils/distortionHeuristic";
import { peakTemperatureBasisLabel } from "../../utils/peakTemperatureDisplay";
import { PublishedTrackBands } from "../PublishedTrackBands";
import { ResearchModelPanel } from "./ResearchModelPanel";
import type { ResearchHostInput } from "../../utils/lpbfResearchPanelModel";

interface Props {
  onOpenSlicer?: () => void;
  onOpenGroundTruth?: () => void;
  onOpenMeltPool?: () => void;
}

export const IndustrialLPBFDecisionLab: React.FC<Props> = ({ onOpenSlicer, onOpenGroundTruth, onOpenMeltPool }) => {
  const specimen = useMaterialSpecimenStore((s) => s.activeSpecimen);
  const updateLpbfProcess = useMaterialSpecimenStore((s) => s.updateLpbfProcess);
  const liveMesh = useLpbfBuildMeshStore((s) => s.mesh);
  const lpbf = specimen.lpbf;
  const { job, error, busy, roundTripMs, rerun, runUq, validateNist, murakamiInput, setMurakamiInput, cache, lastFlags } =
    useLpbfBuildJobPython();

  const materials = useMemo(
    () => mapSpecimenToSolverMaterials(specimen.name, specimen.baseMetal),
    [specimen.name, specimen.baseMetal]
  );

  const demoVectors = LPBF_DEMO_VECTORS[materials.alloyId] ?? LPBF_DEMO_VECTORS.in718;

  // Request values of the Research model panel, built from the aligned job only; the Build Job store is not touched.
  const researchInput = useMemo<ResearchHostInput | null>(() => {
    if (!job) return null;
    const strict = mapSpecimenToBuildJobMaterials(specimen.name, specimen.baseMetal);
    if (!strict || strict.alloyId !== job.alloyId) return null;
    return {
      material: strict.pythonThermal,
      laserPower_W: lpbf.laserPower_W,
      scanSpeed_mm_s: lpbf.scanSpeed_mms,
      beamDiameter_um: lpbf.beamDiameter_um,
      preheatTemp_C: lpbf.preheatTemp_C,
      laserWavelength: "IR_1064nm",
      propertyContext: job.materialPropertySha256
        ? { kind: "build-job-snapshot", alloyId: job.alloyId, materialPropertySha256: job.materialPropertySha256 }
        : { kind: "nominal" },
    };
  }, [job, specimen.name, specimen.baseMetal, lpbf.laserPower_W, lpbf.scanSpeed_mms, lpbf.beamDiameter_um, lpbf.preheatTemp_C]);

  const thermal = job?.thermal ?? null;
  const slicer = job?.slicer ?? null;
  const decision = job?.verdict ?? null;
  const litWindow = job?.verdict?.literatureWindow;
  const keyholeGate = decision?.gates?.find((g) => g.id === "keyhole");
  const keyholeGateStatus = keyholeGate?.status;
  const keyholeNotEvaluated = keyholeGateStatus === "not-evaluated" || keyholeGateStatus === "unavailable";
  const geometryResolved = thermal ? isComputedMeltPoolExtent(thermal.meltPoolGeometry) : true;
  const extentLabel = thermal ? meltPoolExtentInfo(thermal.meltPoolGeometry).status : "";
  const htCohorts = useMemo(() => heatTreatmentCohorts(materials.alloyId), [materials.alloyId]);
  const oriCohorts = useMemo(() => orientationCohorts(materials.alloyId), [materials.alloyId]);

  const literature = useMemo(
    () =>
      findNearestLiteratureRecord(
        materials.alloyId,
        lpbf.laserPower_W,
        lpbf.scanSpeed_mms,
        lpbf.hatch_um,
        lpbf.layer_um,
        {
          peakIntensity_MW_cm2: thermal?.processParameters.peakIntensity_MW_cm2,
          beamDiameter_um: lpbf.beamDiameter_um,
        }
      ),
    [
      materials.alloyId,
      lpbf.laserPower_W,
      lpbf.scanSpeed_mms,
      lpbf.hatch_um,
      lpbf.layer_um,
      lpbf.beamDiameter_um,
      thermal?.processParameters.peakIntensity_MW_cm2,
    ]
  );

  const litPoints = useMemo(() => literatureOverlayPoints(materials.alloyId), [materials.alloyId]);


  return (
    <div className="space-y-4 font-mono">
      <div className="rounded-2xl border border-[#1e2d46] bg-[#090e18] p-4 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-72 h-72 bg-emerald-500/10 blur-3xl pointer-events-none" />
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 relative z-10">
          <div>
            <div className="flex items-center gap-2 text-emerald-300 text-[10px] font-bold uppercase tracking-widest">
              <Gauge className="w-3.5 h-3.5" />
              Industrial decision engine
            </div>
            <h2 className="text-lg font-bold text-white mt-1">Python Build Job verdict</h2>
            <p className="text-[11px] text-slate-400 mt-1 max-w-2xl">
              One Python call owns printability (LoF, keyhole, balling, recoater, literature P–v). The UI does not re-score. Build Job melt pool is Rosenthal screening. Open Melt Pool 3D for Goldak / Eagar–Tsai / Fabbro geometry.
            </p>
            {onOpenMeltPool && (
              <button
                type="button"
                onClick={onOpenMeltPool}
                className="mt-3 inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-gradient-to-r from-amber-500/20 via-rose-500/20 to-sky-500/25 border border-sky-400/40 text-sky-100 text-[11px] font-bold hover:border-sky-300/70"
              >
                <Zap className="w-3.5 h-3.5 text-amber-300" />
                Open Melt Pool 3D
              </button>
            )}
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            {roundTripMs != null && (
              <span className="text-[10px] text-slate-500">
                Round-trip {roundTripMs} ms
                {thermal?.computeTimeMs != null ? ` · solver ${thermal.computeTimeMs} ms` : ""}
              </span>
            )}
            <button
              type="button"
              onClick={() => updateLpbfProcess(demoVectors.lof)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-500/15 border border-rose-400/40 text-rose-200 text-[11px] font-bold"
            >
              LoF demo
            </button>
            <button
              type="button"
              onClick={() => updateLpbfProcess(demoVectors.printable)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-sky-500/15 border border-sky-400/40 text-sky-200 text-[11px] font-bold"
            >
              Printable demo
            </button>
            <button
              type="button"
              onClick={() => void runUq()}
              disabled={busy}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-violet-500/15 border border-violet-400/40 text-violet-200 text-[11px] font-bold"
              title="Literature-default Monte Carlo UQ (n≈96). Skipped on default job for speed."
            >
              Run UQ
            </button>
            <button
              type="button"
              onClick={() => void validateNist()}
              disabled={busy}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-sky-500/15 border border-sky-400/40 text-sky-200 text-[11px] font-bold"
              title="NIST AMB2018-02 IN625 CBM Table 4 MAPE vs Rosenthal screening"
            >
              Validate vs NIST
            </button>
            <button
              type="button"
              onClick={() => void rerun()}
              disabled={busy}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/15 border border-emerald-400/40 text-emerald-200 text-[11px] font-bold"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${busy ? "animate-spin" : ""}`} />
              Re-run Python
            </button>
          </div>
        </div>
        {(cache || lastFlags) && (
          <div className="mt-2 flex flex-wrap gap-2 text-[10px] font-mono text-slate-500 relative z-10">
            {busy && <span className="text-sky-300">Busy…</span>}
            {cache && (
              <span className={cache.hit ? "text-emerald-300" : "text-slate-500"}>
                Cache {cache.hit ? `HIT age ${cache.ageMs} ms` : "MISS"} · key {cache.key}
                {cache.stats ? ` · hitRate ${(cache.stats.hitRate * 100).toFixed(0)}%` : ""}
              </span>
            )}
            <span>
              Flags: UQ {lastFlags.enableUq ? "on" : "off"} · NIST {lastFlags.includeAmbench ? "on" : "off"}
            </span>
          </div>
        )}
      </div>

      {error && (
        <div className="rounded-xl border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-[11px] text-amber-200 flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          <span>
            {error} Industrial verdict needs <code className="text-amber-100">POST /api/lpbf/jobs</code>{" "}
            (LPBF worker, <code className="text-amber-100">routes/lpbfSimulation.ts</code> → <code className="text-amber-100">python/lpbf_worker.py</code>). Restart{" "}
            <code className="text-amber-100">npm run dev</code> if this route 404s.
          </span>
        </div>
      )}

      {decision && thermal && (
        <VerdictBanner
          verdict={decision.verdict}
          headline={toActionableHeadline(decision.headline)}
          reasons={mapActionableReasons(decision.reasons)}
          modelId={job?.modelId}
          gates={decision.gates}
          dominantGate={decision.dominantGate}
          pPrintable={job?.uq?.P_printable}
          dhMean={job?.uq?.normalizedEnthalpy.mean}
          dhStd={job?.uq?.normalizedEnthalpy.std}
          ambenchMape={job?.ambench?.overallMeanMape_pct ?? null}
          murakamiStatus={job?.murakami?.status}
          qualStatus={job?.qualification?.status}
        />
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="rounded-2xl border border-[#1e2d46] bg-[#090e18] p-3.5 space-y-2">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-violet-400" />
            <h3 className="text-xs font-bold text-white">Murakami √area paste (optional)</h3>
          </div>
          <p className="text-[10px] text-slate-500">
            {job?.murakami?.pasteHint ||
              "Paste √area values in µm: CSV / whitespace / one per line. Example: 40, 55, 62, 48, 70. No sizes invented when empty."}
          </p>
          <textarea aria-label="Murakami √area paste (optional)"
            value={murakamiInput.defectSqrtAreasPaste}
            onChange={(e) => setMurakamiInput({ defectSqrtAreasPaste: e.target.value })}
            rows={3}
            placeholder="40, 55, 62, 48, 70"
            className="w-full bg-[#060a12] border border-[#162032] rounded-lg px-2 py-1.5 text-[11px] text-slate-200 font-mono"
          />
          <div className="flex flex-wrap gap-2 items-end">
            <label className="text-[10px] text-slate-400 font-mono">
              HV override
              <input
                type="number"
                value={murakamiInput.hardness_HV ?? ""}
                placeholder={
                  job?.murakami?.alloyHvDefaults?.[materials.alloyId]
                    ? String(job.murakami.alloyHvDefaults[materials.alloyId])
                    : "alloy default"
                }
                onChange={(e) =>
                  setMurakamiInput({
                    hardness_HV: e.target.value === "" ? null : Number(e.target.value),
                  })
                }
                className="ml-1 w-20 bg-[#060a12] border border-[#162032] rounded px-1 py-0.5 text-[11px] text-slate-200"
              />
            </label>
            <label className="text-[10px] text-slate-400 font-mono">
              CT thresh µm
              <input
                type="number"
                value={murakamiInput.ctDetectionThreshold_um ?? ""}
                onChange={(e) =>
                  setMurakamiInput({
                    ctDetectionThreshold_um: e.target.value === "" ? null : Number(e.target.value),
                  })
                }
                className="ml-1 w-16 bg-[#060a12] border border-[#162032] rounded px-1 py-0.5 text-[11px] text-slate-200"
              />
            </label>
            {job?.murakami?.status === "screening_estimate" && (
              <span className="text-[10px] text-violet-200 font-mono">
                σ_w {job.murakami.fatigueLimit_internal_MPa ?? "—"} MPa (internal) · HV{" "}
                {job.murakami.hardness_HV} ({job.murakami.hardnessSource || "—"})
              </span>
            )}
            {job?.murakami?.status === "data_not_supplied" && (
              <span className="text-[10px] text-slate-500 font-mono">data_not_supplied</span>
            )}
          </div>
        </div>

        <div className="rounded-2xl border border-[#1e2d46] bg-[#090e18] p-3.5 space-y-2">
          <div className="flex items-center gap-2">
            <Database className="w-4 h-4 text-sky-400" />
            <h3 className="text-xs font-bold text-white">NIST AMB2018-02 case table</h3>
          </div>
          {job?.ambench?.cases?.length ? (
            <>
              <p className="text-[10px] text-slate-500">
                {job.ambench.source.citation} · DOI{" "}
                <a
                  className="text-sky-300 underline"
                  href={`https://doi.org/${job.ambench.source.doi}`}
                  target="_blank"
                  rel="noreferrer"
                >
                  {job.ambench.source.doi}
                </a>
                {" · "}
                coverage {job.ambench.alloyCoverage?.status ?? "—"}
              </p>
              <div className="overflow-x-auto">
                <table className="w-full text-[10px] font-mono text-slate-300">
                  <thead>
                    <tr className="text-slate-500 text-left border-b border-[#162032]">
                      <th className="py-1 pr-2">Case</th>
                      <th className="py-1 pr-2">NIST L/W/D</th>
                      <th className="py-1 pr-2">Pred L/W/D</th>
                      <th className="py-1">MAPE %</th>
                    </tr>
                  </thead>
                  <tbody>
                    {job.ambench.cases.map((c) => (
                      <tr key={c.caseId} className="border-b border-[#0f172a]">
                        <td className="py-1 pr-2 text-sky-200">{c.caseId}</td>
                        <td className="py-1 pr-2">
                          {c.nist.length_um}/{c.nist.width_um}/{c.nist.depth_um}
                        </td>
                        <td className="py-1 pr-2">
                          {c.predicted.length_um}/{c.predicted.width_um}/{c.predicted.depth_um}
                          {c.predictedIsHeuristic ? " (heuristic)" : ""}
                        </td>
                        <td className="py-1">
                          {c.mape_pct ? (
                            <>
                              L {c.mape_pct.length ?? "—"} · W {c.mape_pct.width ?? "—"} · D {c.mape_pct.depth ?? "—"} · μ{" "}
                              {c.mape_pct.mean ?? "—"}
                            </>
                          ) : (
                            <span className="text-amber-300" title={c.extentNote ?? undefined}>
                              not computed — {c.extentStatus ?? "extent status not reported"}
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="text-[10px] text-slate-500">
                Overall mean MAPE{" "}
                {job.ambench.overallMeanMape_pct != null ? `${job.ambench.overallMeanMape_pct}%` : "not computed"}
                {job.ambench.computedCases != null
                  ? ` (computed cases ${job.ambench.computedCases}, not computed ${job.ambench.notComputedCases ?? 0})`
                  : ""}{" "}
                — screening only, not a qualification gate.
              </p>
            </>
          ) : (
            <p className="text-[10px] text-slate-500">
              Not loaded on the default job. Click <span className="text-sky-300">Validate vs NIST</span> to attach Lane et
              al. Table 4 (IN625 CBM). No AMMT rows added without open NIST numbers.
            </p>
          )}
          {job?.uq && (
            <p className="text-[10px] text-violet-200/90 font-mono pt-1 border-t border-[#162032]">
              UQ n={job.uq.nSamples} · P(printable) {(job.uq.P_printable * 100).toFixed(0)}% · sensitivity (
              {job.uq.sensitivityMethod || "proxy"}) dom {job.uq.dominantUncertainty}
            </p>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="rounded-2xl border border-[#1e2d46] bg-[#090e18] p-3.5 space-y-3">
          <div className="flex items-center gap-2">
            <Grid className="w-4 h-4 text-emerald-400" />
            <h3 className="text-xs font-bold text-white">Is this P–v window safe?</h3>
            <span className="ml-auto text-[10px] text-slate-500">{materials.pythonThermal}</span>
          </div>
          {thermal?.processWindowMap?.grid ? (
            <>
              <div className="relative">
                <div className="grid grid-cols-7 gap-1">
                {thermal.processWindowMap.grid.map((pt, idx) => {
                  const isCurrent =
                    Math.abs(pt.power_W - lpbf.laserPower_W) < 45 &&
                    Math.abs(pt.speed_mm_s - lpbf.scanSpeed_mms) < 220;
                  return (
                    <button
                      key={idx}
                      type="button"
                      title={processMapCellTitle(pt)}
                      onClick={() =>
                        updateLpbfProcess({ laserPower_W: pt.power_W, scanSpeed_mms: pt.speed_mm_s })
                      }
                      className={`p-1 rounded text-left border text-[8px] font-mono ${
                        isCurrent ? "ring-2 ring-sky-400 border-white z-10" : "border-slate-800/70"
                      }`}
                      style={{ backgroundColor: `${pt.color}22` }}
                    >
                      <div className="flex justify-between text-white">
                        <span>{pt.power_W}W</span>
                        <span className="text-slate-400">{pt.speed_mm_s}</span>
                      </div>
                      <div style={{ color: pt.color }}>{pt.regime.split(" ")[0]}{pt.width_um === null ? " (n/r)" : ""}</div>
                    </button>
                  );
                })}
                </div>
                {litPoints.length > 0 && thermal.processWindowMap.grid && (() => {
                  const grid = thermal.processWindowMap.grid;
                  const powers = grid.map((g) => g.power_W);
                  const speeds = grid.map((g) => g.speed_mm_s);
                  const pMin = Math.min(...powers);
                  const pMax = Math.max(...powers);
                  const vMin = Math.min(...speeds);
                  const vMax = Math.max(...speeds);
                  return litPoints.map((pt, i) => {
                    const x = pMax === pMin ? 50 : ((pt.power_W - pMin) / (pMax - pMin)) * 100;
                    const y = vMax === vMin ? 50 : ((pt.speed_mm_s - vMin) / (vMax - vMin)) * 100;
                    if (x < -8 || x > 108 || y < -8 || y > 108) return null;
                    return (
                      <span
                        key={`${pt.doi}-${i}`}
                        title={`${pt.sampleCode} · DOI ${pt.doi || "—"} · ${pt.citation}`}
                        className="absolute w-2 h-2 rounded-full bg-sky-300 border border-white pointer-events-auto z-20"
                        style={{ left: `calc(${x}% - 4px)`, top: `calc(${y}% - 4px)` }}
                      />
                    );
                  });
                })()}
              </div>
              <p className="text-[10px] text-slate-500">
                Click a cell to load P and v into the Build Job store. Geometric LoF uses W vs h and D vs t. Sky dots are literature coupons (DOI tooltip). Nearest match uses P, v, h, t plus I₀ / ΔH/hₛ when recorded. Literature box:{" "}
                {litWindow
                  ? `${litWindow.box.powerMin_W}–${litWindow.box.powerMax_W} W · ${litWindow.box.speedMin_mm_s}–${litWindow.box.speedMax_mm_s} mm/s ${litWindow.inside ? "(inside)" : "(outside)"}.`
                  : "waiting for Python."}
              </p>
              <div className="flex flex-wrap gap-3 text-[10px] text-slate-400">
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded bg-emerald-500" /> Conduction</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded bg-rose-500" /> Keyhole</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded bg-amber-500" /> LoF</span>
                <span className="flex items-center gap-1">(n/r): cell extent not resolved, W/D null, no LoF class</span>
                <span className="flex items-center gap-1">Balling: operating point only (Eagar–Tsai L/W screen)</span>
                {thermal.processWindowMap.gridKernel && <span className="flex items-center gap-1">Grid cells: {thermal.processWindowMap.gridKernel} field extent (every requested kernel)</span>}
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-sky-300" /> Literature DOI</span>
              </div>
              {thermal.processParameters?.absorptivityBasis && (
                <p className="text-[10px] text-slate-500" data-testid="absorptivity-basis">
                  Absorptivity (field) {thermal.processParameters.effectiveAbsorptivity}: {thermal.processParameters.absorptivityBasis}
                  {thermal.processParameters.absorptivityIndexBasis ? ` Index ${thermal.processParameters.indexAbsorptivity}: ${thermal.processParameters.absorptivityIndexBasis}.` : ""}
                  {thermal.processParameters.propertyConventionBasis ? ` Conduction k/cp: ${thermal.processParameters.propertyConventionBasis}.` : ""}
                  {" "}Sourcing correction (P7b), not validation.
                </p>
              )}
            </>
          ) : (
            <SkeletonLines />
          )}
        </div>

        <div className="rounded-2xl border border-[#1e2d46] bg-[#090e18] p-3.5 space-y-3">
          <div className="flex items-center gap-2">
            <Box className="w-4 h-4 text-cyan-400" />
            <h3 className="text-xs font-bold text-white">Will the part print?</h3>
            <button type="button" onClick={onOpenSlicer} className="ml-auto text-[10px] text-cyan-300 underline">
              STL slicer
            </button>
          </div>
          {thermal && decision ? (
            <div className="grid grid-cols-2 gap-2">
              <LofTile label="W / h" value={decision.lofGeometry.widthOverHatch} geometryResolved={geometryResolved} gate={decision.gates?.find((g) => g.id === "lof_wh")} extentLabel={extentLabel} />
              <LofTile label="D / t" value={decision.lofGeometry.depthOverLayer} geometryResolved={geometryResolved} gate={decision.gates?.find((g) => g.id === "lof_dt")} extentLabel={extentLabel} />
              <Metric
                label="ΔH/hₛ"
                value={keyholeNotEvaluated ? "not evaluated" : String(thermal.processParameters.normalizedEnthalpy)}
                ok={keyholeGateOk(keyholeGateStatus)}
                hint={keyholeNotEvaluated ? keyholeGate?.reason ?? "keyhole gate input is null" : "regime keyhole-mode cut 20 (13.6 IN625) drives risky · level 30 is an advisory (unsourced) · porosity unresolved"}
              />
              <Metric
                label="P–v literature"
                value={decision.literatureWindow.inside ? "Inside box" : "Outside box"}
                ok={decision.literatureWindow.inside}
                hint={`${decision.literatureWindow.box.powerMin_W}–${decision.literatureWindow.box.powerMax_W} W`}
              />
              <RecoaterTile risk={thermal.defectDiagnostics.recoaterCrashRisk} gate={decision.gates?.find((g) => g.id === "recoater")} />
              <Metric
                label="Balling"
                value={geometryResolved ? shortRisk(thermal.defectDiagnostics.ballingInstabilityRisk) : "unavailable"}
                ok={!geometryResolved || !thermal.defectDiagnostics.ballingInstabilityRisk.startsWith("High")}
                hint={geometryResolved ? ballingHint(thermal.defectDiagnostics.ballingScreen) : extentLabel}
              />
            </div>
          ) : (
            <SkeletonLines />
          )}
          {slicer?.buildTimeSummary && (
            <div className="rounded-lg border border-[#162032] bg-[#060a12] p-2.5 space-y-1">
              <div className="flex items-center gap-1.5 text-[10px] text-slate-300">
                <Clock className="w-3.5 h-3.5 text-sky-400" />
                {slicer.geometrySource === "uploaded-stl"
                  ? `Live STL ${liveMesh?.name || slicer.cadAssetName || "mesh"}`
                  : `Demo preset ${slicer.preset || inferSlicerPreset(lpbf.cadAssetName)}`}{" "}
                · {slicer.buildTimeSummary.totalLayers} layers · {slicer.buildTimeSummary.totalBuildTime_hr} h
              </div>
              <div className="text-[10px] text-slate-500">
                Laser {slicer.buildTimeSummary.totalLaserTime_hr} h · Recoat {slicer.buildTimeSummary.totalRecoatTime_hr} h · Peak area{" "}
                {slicer.buildTimeSummary.peakLayerArea_mm2} mm²
                {slicer.meshMetrics ? ` · ~${slicer.meshMetrics.estimatedPartMass_g} g` : ""}
                {slicer.meshMetrics
                  ? ` · ${slicer.meshMetrics.triangleCount} tris`
                  : ""}
              </div>
              {liveMesh && liveMesh.nativeTriangleCount > liveMesh.usedTriangleCount && (
                <p className="text-[10px] text-slate-500">
                  Uniform subsample {liveMesh.usedTriangleCount} of {liveMesh.nativeTriangleCount} triangles for the Python slicer.
                </p>
              )}
              {!liveMesh && lpbf.cadAssetName && (
                <p className="text-[10px] text-amber-300/80">
                  Filename {lpbf.cadAssetName} is recorded in the shared process vector but the triangle buffer is session-only — re-upload the STL in the slicer to slice the uploaded mesh.
                </p>
              )}
              {!liveMesh && !lpbf.cadAssetName && (
                <p className="text-[10px] text-amber-300/80">No uploaded STL in the shared process vector — using a demo CAD preset. Open the slicer to bind a CAD file.</p>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="rounded-2xl border border-[#1e2d46] bg-[#090e18] p-3.5 space-y-3">
          <div className="flex items-center gap-2">
            <Thermometer className="w-4 h-4 text-orange-400" />
            <h3 className="text-xs font-bold text-white">Stress and distortion screening proxies</h3>
          </div>
          {thermal ? (
            <>
              <div className="grid grid-cols-2 gap-2">
                <Metric
                  label="Distortion screening index"
                  value={typeof thermal.defectDiagnostics.distortionIndex === "number" ? thermal.defectDiagnostics.distortionIndex.toFixed(2) : "n/a"}
                  ok={typeof thermal.defectDiagnostics.distortionIndex === "number" ? thermal.defectDiagnostics.distortionIndex < 0.65 : null}
                  hint={typeof thermal.defectDiagnostics.distortionIndex === "number" ? "legacy payload: screening threshold < 0.65" : (thermal.defectDiagnostics.stressUnavailableReason ?? STRESS_UNAVAILABLE_NOTE)}
                />
                <StressProxyMetric
                  stress_MPa={thermal.defectDiagnostics.effectiveResidualStress_MPa}
                  yieldStrength_MPa={specimen.yieldStrength_25C_MPa}
                  reason={thermal.defectDiagnostics.stressUnavailableReason}
                />
                <Metric
                  label="Peak T (°C)"
                  value={typeof thermal.hydrodynamicsAndRecoil.peakTemperature_C === "number" ? String(thermal.hydrodynamicsAndRecoil.peakTemperature_C) : "n/a"}
                  ok={typeof thermal.hydrodynamicsAndRecoil.peakTemperature_C === "number" ? true : null}
                  hint={thermal.hydrodynamicsAndRecoil.peakUnavailableReason ?? peakTemperatureBasisLabel(thermal) ?? undefined}
                />
                <Metric label="Preheat (°C)" value={String(lpbf.preheatTemp_C)} ok={lpbf.preheatTemp_C >= 80} />
              </div>
              <p className="text-[10px] text-slate-500">
                Research screening only. Since P7a (2026-10-11) no stress or distortion number is served: {STRESS_UNAVAILABLE_NOTE} This is not a part acceptance criterion.
              </p>
            </>
          ) : (
            <SkeletonLines />
          )}
        </div>

        <div className="rounded-2xl border border-[#1e2d46] bg-[#090e18] p-3.5 space-y-3">
          <div className="flex items-center gap-2">
            <Database className="w-4 h-4 text-sky-400" />
            <h3 className="text-xs font-bold text-white">Literature context (specimen properties unavailable)</h3>
            <button type="button" onClick={onOpenGroundTruth} className="ml-auto text-[10px] text-sky-300 underline">
              Experimental comparison
            </button>
          </div>
          {literature ? (
            <div className="space-y-2 text-[11px]">
              <div className="text-slate-200 font-bold">{literature.record.build.alloyName}</div>
              <div className="text-slate-400">
                {literature.record.source.citation} ({literature.record.source.year}) · DOI {literature.record.source.doi || "—"}
              </div>
              <div className="text-slate-500">
                Lit. P {literature.record.params.laserPower_W} W · v {literature.record.params.scanSpeed_mm_s} mm/s · h{" "}
                {literature.record.params.hatchSpacing_um} µm · t {literature.record.params.layerThickness_um} µm · match Δ{" "}
                {literature.distance.toFixed(2)}
              </div>
              <div className="grid grid-cols-3 gap-2">
                <Metric
                  label="Literature density %"
                  value={literature.record.properties.relativeDensity_pct.toFixed(2)}
                  ok={literature.record.properties.relativeDensity_pct >= 99.5}
                />
                <Metric
                  label="Literature Rp0.2 (MPa)"
                  value={String(literature.record.properties.yieldStrength_MPa ?? "—")}
                  hint="Specimen Rp0.2 unavailable; no comparison"
                />
                <Metric
                  label="Literature UTS (MPa)"
                  value={String(literature.record.properties.ultimateTensileStrength_MPa ?? "—")}
                  hint="Specimen UTS unavailable; no comparison"
                />
              </div>
              {htCohorts.length > 0 && (
                <div className="text-[10px] text-slate-400 space-y-0.5">
                  {htCohorts.map((c) => (
                    <div key={c.label}>
                      {c.label}: n={c.n}
                      {c.meanYS != null ? ` · Rp0.2 ${c.meanYS}` : ""}
                      {c.meanUTS != null ? ` · UTS ${c.meanUTS}` : ""}
                      {c.meanElong != null ? ` · A ${c.meanElong}%` : ""}
                    </div>
                  ))}
                </div>
              )}
              {oriCohorts.length > 0 && (
                <div className="text-[10px] text-slate-500">
                  Orientation coupons: {oriCohorts.map((c) => `${c.label} n=${c.n}`).join(" · ")}
                </div>
              )}
            </div>
          ) : (
            <p className="text-[11px] text-slate-400">No traceable coupon in the library for this alloy yet.</p>
          )}
        </div>
      </div>

      {thermal && (
        <div className="rounded-2xl border border-[#1e2d46] bg-[#090e18] p-3.5 grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-2">
          <Tiny label="Engine" value={job?.modelId || "Python"} icon={<Cpu className="w-3 h-3" />} />
          <Tiny label="Regime" value={thermal.meltPoolGeometry.regime} icon={<Zap className="w-3 h-3" />} />
          <Tiny label="W×D (µm)" value={`${thermal.meltPoolGeometry.width_um}×${thermal.meltPoolGeometry.depth_um}`} icon={<Layers className="w-3 h-3" />}
            sub={<MachineTileLine material={materials.pythonThermal} screeningDepth={thermal.meltPoolGeometry.depth_um}
              request={{ laserPower_W: lpbf.laserPower_W, scanSpeed_mm_s: lpbf.scanSpeed_mms, beamDiameter_um: lpbf.beamDiameter_um, preheatTemp_C: lpbf.preheatTemp_C, layerThickness_um: lpbf.layer_um, hatchSpacing_um: lpbf.hatch_um, laserWavelength: "IR_1064nm" }} />} />
          <Tiny label="ΔH/hs" value={String(thermal.processParameters.normalizedEnthalpy)} icon={<Activity className="w-3 h-3" />} />
          <Tiny label="I0 MW/cm²" value={String(thermal.processParameters.peakIntensity_MW_cm2 ?? "-")} />
          <Tiny label="LED J/mm" value={(thermal.processParameters.linearEnergyDensity_J_m / 1000).toFixed(3)} />
          <Tiny label="VED J/mm³" value={String(thermal.processParameters.volumetricEnergyDensity_J_mm3)} />
          <Tiny label="ε K/s" value={quantityText(thermal.solidificationKinetics.quantities.coolingRate)} />
        </div>
      )}
      {thermal && <MeltPoolExtentNotice geometry={thermal.meltPoolGeometry} />}
      {thermal && <DepthBiasNotice geometry={thermal.meltPoolGeometry} material={thermal.material} heatSource={thermal.processParameters?.heatSource} enthalpy={thermal.processParameters?.normalizedEnthalpy} />}
      {thermal && <PublishedTrackBands thermal={thermal} />}
      {job && researchInput && <ResearchModelPanel host="build-job" input={researchInput} served={thermal} />}

      {job?.porosity && (
        <div className="rounded-2xl border border-violet-500/30 bg-[#090e18] p-3.5 grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="space-y-1">
            <h3 className="text-[10px] font-bold text-violet-300 uppercase tracking-widest">Unsourced Screening Index</h3>
            <div className="text-xl text-white font-bold" title={job.porosity.screeningIndex.basis}>{job.porosity.screeningIndex.mean_percent.toFixed(2)}%</div>
            <div className="text-[9px] text-amber-500/80">{job.porosity.screeningIndex.evidenceLabel}: unsourced penalties, not a measured or predicted relative density</div>
            <div className="text-[9px] text-slate-500" title={job.porosity.screeningIndex.spreadBasis}>Spread of penalties (not a CI): {job.porosity.screeningIndex.spread_lower_percent.toFixed(2)} to {job.porosity.screeningIndex.spread_upper_percent.toFixed(2)}</div>
          </div>
          <div className="space-y-1">
            <h3 className="text-[10px] font-bold text-violet-300 uppercase tracking-widest">Dominant Mechanism</h3>
            <div className="text-sm text-slate-200 capitalize">{job.porosity.dominantMechanism}</div>
            <div className="text-[9px] text-slate-500">Based on MC aggregation</div>
          </div>
          {job.kinematics && (
            <div className="col-span-2 space-y-1">
              <h3 className="text-[10px] font-bold text-violet-300 uppercase tracking-widest">Scanner Kinematics</h3>
              <div className="text-sm text-slate-200">
                Mid-track: {job.kinematics.effectiveMidTrackSpeed_mms.toFixed(0)} mm/s 
                (Accel dist: {job.kinematics.skywritingRequired_mm.toFixed(2)} mm)
              </div>
              <div className="text-[9px] text-amber-500/80">{job.kinematics.warning || "Skywriting sufficient for acceleration."}</div>
            </div>
          )}
        </div>
      )}

      {(job?.microstructure || job?.kinetics) && (
        <div className="rounded-2xl border border-teal-500/30 bg-[#090e18] p-3.5 grid grid-cols-1 md:grid-cols-2 gap-4">
          <BuildJobMicrostructurePanel micro={job?.microstructure} segregation={job && "segregation" in job ? job.segregation : undefined} />
          <BuildJobKineticsPanel kinetics={job?.kinetics} />
        </div>
      )}

      {job?.assumptions && job.assumptions.length > 0 && (
        <div className="rounded-2xl border border-[#1e2d46] bg-[#090e18] p-3.5 space-y-2">
          <div className="text-[10px] font-bold text-slate-300 uppercase tracking-widest">
            {job.modelId} assumptions
          </div>
          <p className="text-[10px] text-slate-500">{modelHonestyLine(job.modelId)}</p>
          <ul className="list-disc pl-5 space-y-1 text-[11px] text-slate-400">
            {job.assumptions.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

function ballingHint(screen: { lengthToWidth: number | null; band: string | null } | undefined): string {
  if (!screen) return "Eagar–Tsai L/W screen not returned";
  if (screen.band === null || screen.lengthToWidth === null) return "Eagar–Tsai extent not computed";
  return `Eagar–Tsai L/W ${screen.lengthToWidth.toFixed(2)} · High > 5.5 advisory (316L only, unsourced threshold) · Moderate advisory > 3.85`;
}

function shortRisk(s: string): string {
  return s.split(" ")[0] || s;
}

function verdictTone(v: PrintVerdict): string {
  if (v === "printable") return "border-emerald-500/40 bg-emerald-500/10 text-emerald-100";
  if (v === "risky") return "border-amber-500/40 bg-amber-500/10 text-amber-100";
  if (v === "inconclusive") return "border-slate-500/40 bg-slate-500/10 text-slate-100";
  return "border-rose-500/40 bg-rose-500/10 text-rose-100";
}

export const VerdictBanner: React.FC<{
  verdict: PrintVerdict;
  headline: string;
  reasons: string[];
  modelId?: string;
  gates?: PythonLpbfScreeningGate[];
  dominantGate?: string;
  pPrintable?: number;
  dhMean?: number;
  dhStd?: number;
  ambenchMape?: number | null;
  murakamiStatus?: string;
  qualStatus?: string;
}> = ({
  verdict,
  headline,
  reasons,
  modelId,
  gates,
  dominantGate,
  pPrintable,
  dhMean,
  dhStd,
  ambenchMape,
  murakamiStatus,
  qualStatus,
}) => (
  <div className={`rounded-2xl border p-4 ${verdictTone(verdict)}`}>
    <p data-testid="print-verdict-screening-label" className="mb-1 text-[10px] font-semibold uppercase tracking-wide opacity-90">{PRINT_VERDICT_SCREENING_LABEL}</p>
    <div className="flex items-center gap-2 font-bold text-sm">
      {verdict === "printable" ? (
        <CheckCircle2 className="w-5 h-5" />
      ) : verdict === "inconclusive" ? (
        <AlertTriangle className="w-5 h-5" />
      ) : (
        <ShieldAlert className="w-5 h-5" />
      )}
      {headline}
    </div>
    <p className="mt-1 text-[10px] opacity-80">{modelHonestyLine(modelId)}</p>
    {(pPrintable != null || dhMean != null) && (
      <p className="mt-1 text-[11px] font-mono opacity-95">
        {pPrintable != null ? `P(printable) ${(pPrintable * 100).toFixed(0)}%` : null}
        {pPrintable != null && dhMean != null ? " · " : null}
        {dhMean != null ? `ΔH/hₛ ${dhMean.toFixed(1)}±${(dhStd ?? 0).toFixed(1)} (UQ lit-default)` : null}
      </p>
    )}
    {(ambenchMape != null || murakamiStatus || qualStatus) && (
      <p className="mt-1 text-[10px] font-mono opacity-80">
        {ambenchMape != null ? `NIST AMB2018-02 mean MAPE ${ambenchMape}% (IN625 CBM)` : null}
        {ambenchMape != null && (murakamiStatus || qualStatus) ? " · " : null}
        {murakamiStatus ? `Murakami ${murakamiStatus}` : null}
        {murakamiStatus && qualStatus ? " · " : null}
        {qualStatus ? `Qualification ${qualStatus}` : null}
      </p>
    )}
    {gates && gates.length > 0 && (
      <div className="mt-2 flex flex-wrap gap-1">
        {gates.map((g) => (
          <span
            key={g.id}
            title={g.reason ?? g.note}
            className={`text-[9px] font-mono px-1.5 py-0.5 rounded border ${
              g.status === "fail"
                ? "border-rose-400/50 text-rose-100"
                : g.status === "warn"
                  ? "border-amber-400/50 text-amber-100"
                  : g.status === "unavailable" || g.status === "not-evaluated"
                    ? "border-dashed border-slate-400/50 text-slate-300"
                    : g.status === "advisory"
                      ? "border-dotted border-sky-300/60 text-sky-100"
                      : "border-white/20 text-white/70"
            } ${dominantGate === g.id ? "ring-1 ring-white/60" : ""}`}
          >
            {g.id} {g.status}
            {typeof g.measured === "number" ? ` ${g.measured}` : ""}
          </span>
        ))}
      </div>
    )}
    <ul className="mt-2 space-y-1 text-[11px] opacity-90 list-disc pl-5">
      {reasons.map((r) => (
        <li key={r}>{r}</li>
      ))}
    </ul>
  </div>
);

/**
 * Missing, "not-evaluated" or "unavailable" verdict -> null (rendered as not evaluated), never the Metric default
 * ok=true and never a fail: a null gate input is neither a pass nor a fail.
 */
export function keyholeGateOk(status: string | undefined): boolean | null {
  if (status === undefined || status === "not-evaluated" || status === "unavailable") return null;
  return status === "pass" || status === "advisory";
}

export interface LofTileState {
  value: string;
  ok: boolean | null;
  hint: string;
}

/**
 * P7b (2026-10-14): process-map cells whose field extent is not a computed isotherm carry width_um and depth_um null
 * and their extentStatus; the tooltip says so instead of printing a number.
 */
export function processMapCellTitle(pt: {
  power_W: number; speed_mm_s: number; regime: string; width_um: number | null; depth_um: number | null;
  extentStatus?: string; lackOfFusionNote?: string;
}): string {
  const wd = pt.width_um === null || pt.depth_um === null
    ? `W/D not resolved (${pt.extentStatus ?? "extent not computed"})`
    : `W ${pt.width_um} µm, D ${pt.depth_um} µm`;
  return `${pt.power_W} W, ${pt.speed_mm_s} mm/s — ${pt.regime} — ${wd}${pt.lackOfFusionNote ? ` — ${pt.lackOfFusionNote}` : ""}`;
}

/** P7a (2026-10-11): lof_wh and lof_dt are diagnostics with no sourced threshold (gate.required null). */
export const LOF_DIAGNOSTIC_HINT = "diagnostic, no sourced threshold (Tang index is the gate)";

/**
 * W/h and D/t tile state. A null ratio (lofGeometry payload with a null melt-pool extent or Tang index) is "not
 * evaluated" with the gate reason, never a toFixed on null and never a pass or fail. The threshold comes from the
 * gate's required value: null (P7a payloads) renders the ratio neutrally (ok null) with the diagnostic hint; a numeric
 * required (legacy payloads, 1.05 / 1.15) keeps the former pass or fail styling.
 */
export function lofTileState(
  value: number | null | undefined,
  geometryResolved: boolean,
  gate: { status?: string; reason?: string; required?: number | null } | undefined,
  extentLabel: string,
): LofTileState {
  if (!geometryResolved) return { value: "unavailable", ok: true, hint: extentLabel };
  if (value === null || value === undefined || !Number.isFinite(value) || gate?.status === "not-evaluated") {
    return { value: "not evaluated", ok: null, hint: gate?.reason ?? "lack-of-fusion input is null" };
  }
  const min = gate?.required;
  if (typeof min !== "number" || !Number.isFinite(min)) {
    return { value: value.toFixed(2), ok: null, hint: LOF_DIAGNOSTIC_HINT };
  }
  return { value: value.toFixed(2), ok: value >= min, hint: `> ${min} (legacy payload threshold)` };
}

const LofTile: React.FC<{
  label: string;
  value: number | null | undefined;
  geometryResolved: boolean;
  gate?: { status?: string; reason?: string; required?: number | null };
  extentLabel: string;
}> = ({ label, value, geometryResolved, gate, extentLabel }) => {
  const s = lofTileState(value, geometryResolved, gate, extentLabel);
  return <Metric label={label} value={s.value} ok={s.ok} hint={s.hint} />;
};

/**
 * Recoater tile state. Since P7a the recoater gate is not-evaluated (no sourced stress model) and recoaterCrashRisk
 * starts with "unavailable": the tile shows "n/a", neutral, with the gate reason or STRESS_UNAVAILABLE_NOTE. Legacy
 * payloads keep the former short-risk text.
 */
export function recoaterTileState(
  risk: string | null | undefined,
  gate: { status?: string; reason?: string } | undefined,
): LofTileState {
  const text = risk ?? "";
  if (gate?.status === "not-evaluated" || text.toLowerCase().startsWith("unavailable")) {
    return { value: "n/a", ok: null, hint: gate?.reason ?? STRESS_UNAVAILABLE_NOTE };
  }
  if (text.startsWith("Not evaluated")) {
    return { value: "Not evaluated", ok: true, hint: "alloy/layer/preheat-only index · not from scan parameters · no verdict effect" };
  }
  return { value: shortRisk(text), ok: true, hint: "legacy payload: alloy/layer/preheat-only index · no verdict effect" };
}

const RecoaterTile: React.FC<{ risk: string; gate?: { status?: string; reason?: string } }> = ({ risk, gate }) => {
  const s = recoaterTileState(risk, gate);
  return <Metric label="Recoater" value={s.value} ok={s.ok} hint={s.hint} />;
};

/** ok = null: no pass/fail is possible (dashed, neutral), distinct from a passed check. */
const Metric: React.FC<{ label: string; value: string; ok?: boolean | null; hint?: string }> = ({ label, value, ok = true, hint }) => (
  <div
    data-check={ok === null ? "unavailable" : ok ? "ok" : "flag"}
    className={`rounded-lg border px-2 py-1.5 ${ok === null ? "border-dashed border-slate-700 bg-[#060a12]" : ok ? "border-[#162032] bg-[#060a12]" : "border-amber-500/40 bg-amber-500/10"}`}
  >
    <div className="text-[9px] text-slate-500 uppercase">{label}</div>
    <div className="text-[12px] text-white font-bold truncate">{value}</div>
    {hint && <div className="text-[9px] text-slate-500">{hint}</div>}
  </div>
);

/** Stress proxy vs 0.7 Rp0.2: pass/fail only with a real yield strength, otherwise explicitly unavailable. */
export const StressProxyMetric: React.FC<{ stress_MPa: number | null | undefined; yieldStrength_MPa: number | null | undefined; reason?: string | null }> = ({ stress_MPa, yieldStrength_MPa, reason }) => {
  if (typeof stress_MPa !== "number" || !Number.isFinite(stress_MPa)) {
    // P7a: the stress proxy is not served (null); show the reason, no number, no pass/fail.
    return <Metric label={STRESS_PROXY_LABEL} value="n/a" ok={null} hint={reason ?? STRESS_UNAVAILABLE_NOTE} />;
  }
  const p = stressProxyPresentation(stress_MPa, yieldStrength_MPa);
  return <Metric label={p.label} value={`${stress_MPa} MPa-eq.`} ok={p.check.ok} hint={p.hint} />;
};

const Tiny: React.FC<{ label: string; value: string; icon?: React.ReactNode; sub?: React.ReactNode }> = ({ label, value, icon, sub }) => (
  <div className="rounded-lg border border-[#162032] bg-[#060a12] px-2 py-1.5">
    <div className="flex items-center gap-1 text-[9px] text-slate-500 uppercase">
      {icon}
      {label}
    </div>
    <div className="text-[11px] text-slate-200 truncate">{value}</div>
    {sub}
  </div>
);

const SkeletonLines: React.FC = () => (
  <div className="h-24 rounded-lg bg-[#060a12] border border-[#162032] animate-pulse" />
);
