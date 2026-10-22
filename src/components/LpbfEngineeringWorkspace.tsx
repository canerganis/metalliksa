import { WorkspaceVisibility } from './WorkspaceVisibility';
import { IS_STATIC_DEMO } from "../demo/flag.ts";
import { DEMO_LOCK, DEMO_UNAVAILABLE_LOCK } from "../demo/demoGate.ts";
import { isDemoPanelShown } from "../demo/demoModules.ts";
import { DemoUnavailable } from "../demo/demoNotes.tsx";
import { LpbfSourceArchivePanel } from './LpbfSourceArchivePanel';
import { LpbfRunArchivePanel } from './LpbfRunArchivePanel';
import { LpbfRunReportExport } from './LpbfRunReportExport';
import React, { lazy, Suspense, useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, Download, FlaskConical, Layers, BookOpen } from "lucide-react";
import { useMaterialSpecimenStore, type LpbfProcessPatch } from "../store/useMaterialSpecimenStore";
import { LpbfDefaultsNote } from "./LpbfDefaultsNote";
import { useLpbfWorkflowStore, LPBF_WORKFLOW_STAGES, isLpbfWorkflowStage, type LpbfWorkflowStage } from "../store/useLpbfWorkflowStore";
import { useEngineeringField, useLpbfEngineeringStore } from "../store/useLpbfEngineeringStore";
import { peekLpbfBuildJobKey, useLpbfBuildJobStore } from "../store/useLpbfBuildJobStore";
import { useLpbfBuildMeshStore } from "../store/useLpbfBuildMeshStore";
import { createLpbfQualificationReport, sharedSimulationInput } from "../utils/lpbfQualificationReport";
import { useResearchStore } from "../store/useResearchStore";
import { mapSpecimenToBuildJobMaterials } from "../utils/lpbfIndustrialDecision";
import { getResearchIntegrationRecords } from "../utils/researchRegistry";
import { formatExactNumber } from "../utils/numberFormat";
import { MeasurementPanel, StaleResultBanner, ThermalHistory, ConvergencePanel, jobContextLabel } from "./3d-distortion-lab/LpbfResultPresentation";
import { MeltPoolSummaryCard } from "./3d-distortion-lab/MeltPoolSummaryCard";
import { ResolvedThermalViewer } from "./3d-distortion-lab/ResolvedThermalViewer";


const BuildSlicer = lazy(() => import("./3d-distortion-lab/BasicSTLSlicerLab").then(module => ({default:module.BasicSTLSlicerLab})));
const DefectScreening = lazy(() => import("./3d-distortion-lab/IndustrialLPBFDecisionLab").then(module => ({default:module.IndustrialLPBFDecisionLab})));
const MeltPool3D = lazy(() => import("./3d-distortion-lab/MeltPool3DCrossSectionLab").then(module => ({default:module.MeltPool3DCrossSectionLab})));
const LpbfEngineeringSimulation = lazy(() => import("./3d-distortion-lab/LpbfEngineeringSimulation").then(module => ({default:module.LpbfEngineeringSimulation})));
// Static demo (docs/DEMO_STATIC_DESIGN.md section 5): inputs are locked to the recorded values, stages that need a live engine show a note.
// IS_STATIC_DEMO is a compile-time constant, so a normal build keeps none of this.
type LockProps = { disabled?: boolean; title?: string };
const lock: LockProps = IS_STATIC_DEMO ? DEMO_LOCK : {};
const unavailable: LockProps = IS_STATIC_DEMO ? DEMO_UNAVAILABLE_LOCK : {};
const stageHidden = (id: string) => IS_STATIC_DEMO && !isDemoPanelShown("3d-distortion-lab", id);
const panel = "rounded-2xl border border-slate-700/70 bg-slate-900/40 p-5 md:p-6";
const inputStyle = "mt-2 w-full rounded-lg border border-slate-600 bg-slate-950 px-3 py-2.5 text-sm text-slate-100 focus-visible:outline-2 focus-visible:outline-sky-300";
const buttonStyle = "rounded-lg border border-slate-600 px-3 py-2 text-sm text-slate-200 hover:bg-slate-800 focus-visible:outline-2 focus-visible:outline-sky-300 disabled:opacity-40";
const processFields = [
  ["laserPower_W", "Laser power", "W", 10, 1500], ["scanSpeed_mms", "Scan speed", "mm/s", 10, 10000],
  ["beamDiameter_um", "Beam diameter", "µm", 20, 500], ["hatch_um", "Hatch spacing", "µm", 10, 1000],
  ["layer_um", "Layer thickness", "µm", 10, 150], ["preheatTemp_C", "Preheat", "°C", 0, 1200],
] as const;

function EvidenceInput({field,label,type="text"}:{field:"width"|"depth"|"source"|"specimen"|"uncertainty";label:string;type?:string}) {
  const [value,setValue] = useEngineeringField(field);
  return <label className="text-xs text-slate-400">{label}<input className={inputStyle} aria-label={label} type={type} min={type==="number"?0:undefined} step="any" value={value} onChange={event=>setValue(event.target.value)}/></label>;
}

export function LpbfEngineeringWorkspace() {
  const specimen = useMaterialSpecimenStore(state=>state.activeSpecimen);
  const updateProcess = useMaterialSpecimenStore(state=>state.updateLpbfProcess);
  const loadPreset = useMaterialSpecimenStore(state=>state.loadPreset);
  const {stage,context,setStage,updateContext} = useLpbfWorkflowStore();
  const engineering = useLpbfEngineeringStore();
  const build = useLpbfBuildJobStore();
  const mesh = useLpbfBuildMeshStore(state=>state.mesh);
  const research = useResearchStore();
  const evidence = getResearchIntegrationRecords(research, undefined, specimen.id);
  const report = createLpbfQualificationReport(specimen,context,engineering,build.lastKey===peekLpbfBuildJobKey()?build.job:null,evidence);
  const result = engineering.job?.status==="completed" ? engineering.job.result : undefined;
  const [specialists,setSpecialists] = useState(false);
  const [specialistSubTab,setSpecialistSubTab] = useState<string>();
  const [visited,setVisited] = useState<Set<string>>(()=>new Set([stage]));
  const currentIndex = LPBF_WORKFLOW_STAGES.findIndex(item=>item.id===stage);
  const currentStage = LPBF_WORKFLOW_STAGES[currentIndex] ?? LPBF_WORKFLOW_STAGES[0];
  const go = (next:LpbfWorkflowStage) => {const url=new URL(window.location.href);url.searchParams.set("lpbfStage",next);url.searchParams.delete("lpbfSubTab");window.history.replaceState(null,"",url);setStage(next);setSpecialists(false);setVisited(previous=>new Set([...previous,next]));};

  useEffect(()=>{
    const applyLocation = () => {
      const parameters = new URLSearchParams(window.location.search);
      const incoming = parameters.get("lpbfStage");
      if (isLpbfWorkflowStage(incoming)) {setStage(incoming);setVisited(previous=>new Set([...previous,incoming]));setSpecialists(false);}
      else if (parameters.has("lpbfSubTab") || window.location.hash.startsWith("#lpbf=")) {setSpecialists(true);setVisited(previous=>new Set([...previous,"specialists"]));}
    };
    const onNavigate = (event:Event) => {
      const detail = (event as CustomEvent<{lpbfStage?:string;subTab?:string;lpbfSubTab?:string;activeSubTab?:string}>).detail;
      if (isLpbfWorkflowStage(detail?.lpbfStage)) {setStage(detail.lpbfStage);setVisited(previous=>new Set([...previous,detail.lpbfStage!]));setSpecialists(false);}
      else if (detail?.subTab || detail?.lpbfSubTab || detail?.activeSubTab) {setSpecialistSubTab(detail.subTab||detail.lpbfSubTab||detail.activeSubTab);setSpecialists(true);setVisited(previous=>new Set([...previous,"specialists"]));}
    };
    applyLocation();
    window.addEventListener("popstate",applyLocation);
    window.addEventListener("metallix-lpbf-subtab",onNavigate);
    window.addEventListener("metallix-navigate-tab",onNavigate);
    return ()=>{window.removeEventListener("popstate",applyLocation);window.removeEventListener("metallix-lpbf-subtab",onNavigate);window.removeEventListener("metallix-navigate-tab",onNavigate);};
  },[setStage]);

  const exportReport = () => {
    const url=URL.createObjectURL(new Blob([JSON.stringify(report,null,2)],{type:"application/json"}));
    const link=document.createElement("a");link.href=url;link.download=`metalliksa-lpbf-dossier-${new Date().toISOString().slice(0,10)}.json`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  };
  const next = () => go(LPBF_WORKFLOW_STAGES[Math.min(currentIndex+1,7)].id);
  const invalidSharedProcess = processFields.some(([key,,,min,max])=>!Number.isFinite(specimen.lpbf[key])||specimen.lpbf[key]<min||specimen.lpbf[key]>max);
  const materialWarning = engineering.material && engineering.material!==sharedSimulationInput(specimen).material;
  const specialistMaterial = mapSpecimenToBuildJobMaterials(specimen.name, specimen.baseMetal)?.pythonThermal;

  return <section aria-label="LPBF Engineering workspace" className="mx-auto max-w-[1500px] space-y-5 text-slate-200">
    <header className="flex flex-wrap items-start justify-between gap-4">
      <div><p className="text-xs uppercase tracking-[.2em] text-sky-300">Research engineering workstation</p><h1 className="mt-2 text-3xl font-medium tracking-tight">LPBF Engineering</h1><p className="mt-2 text-sm text-slate-400">One specimen, one process vector, traceable jobs and evidence.</p></div>
      <div className="flex flex-wrap gap-2"><span className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">Research · experimental validation unresolved</span><button className={buttonStyle} {...unavailable} onClick={()=>{setSpecialists(!specialists);setVisited(previous=>new Set([...previous,"specialists"]));}}><FlaskConical className="mr-2 inline h-4 w-4"/>{specialists?"Return to workflow":"Specialist labs"}</button></div>
    </header>
    <div className="flex flex-wrap gap-x-6 gap-y-2 border-y border-slate-700/70 py-3 text-xs text-slate-400" aria-label="Shared LPBF context"><span>Material <strong className="ml-1 text-slate-200">{specimen.name}</strong></span><span>{formatExactNumber(specimen.lpbf.laserPower_W)} W / {formatExactNumber(specimen.lpbf.scanSpeed_mms)} mm/s / h {formatExactNumber(specimen.lpbf.hatch_um)} µm / t {formatExactNumber(specimen.lpbf.layer_um)} µm</span><span>Build {context.buildId||"unassigned"}</span><span>Job {jobContextLabel(engineering.job,report.resultMatchesCurrentInputs)}</span><span>{evidence.length} linked evidence record{evidence.length===1?"":"s"}</span><LpbfDefaultsNote lpbf={specimen.lpbf}/></div>
    <nav aria-label="LPBF workflow stages" className="grid grid-cols-2 gap-1.5 md:grid-cols-4 xl:grid-cols-8">{LPBF_WORKFLOW_STAGES.map((item,index)=><button key={item.id} aria-current={!specialists&&stage===item.id?"step":undefined} className={`min-h-20 rounded-xl border px-3 py-3 text-left ${!specialists&&stage===item.id?"border-sky-400/60 bg-sky-500/10 text-sky-100":"border-slate-700/60 text-slate-400 hover:bg-slate-800"}`} onClick={()=>go(item.id)}><span className="block text-[10px] text-slate-500">{String(index+1).padStart(2,"0")}</span><span className="mt-1 block text-xs leading-5">{item.label}</span></button>)}</nav>
    {specialists&&stageHidden("specialists")&&<DemoUnavailable what="Specialist labs"/>}
    {specialists&&!stageHidden("specialists")&&<section className="space-y-4" aria-label="Melt pool 3D specialist lab"><p className="text-sm text-amber-200">Analytical melt pool sandbox. Its inputs stay in this lab; measured bare-plate cases require a matching model before comparison.</p>{specialistMaterial?<Suspense fallback={<LoadingLab/>}><MeltPool3D initialPower_W={specimen.lpbf.laserPower_W} initialSpeed_mms={specimen.lpbf.scanSpeed_mms} initialBeamDiameter_um={specimen.lpbf.beamDiameter_um} initialPreheat_C={specimen.lpbf.preheatTemp_C} initialLayer_um={specimen.lpbf.layer_um} initialHatch_um={specimen.lpbf.hatch_um} initialMaterial={specialistMaterial}/></Suspense>:<p role="status" className={panel}>This material has no supported analytical melt pool input.</p>}</section>}
    {!specialists&&<div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-xl font-medium">{currentStage.label}</h2><p className="mt-1 text-sm text-slate-400">{currentStage.purpose}</p></div><div className="flex gap-2"><button aria-label="Previous LPBF stage" className={buttonStyle} disabled={currentIndex===0} onClick={()=>go(LPBF_WORKFLOW_STAGES[currentIndex-1].id)}><ArrowLeft className="h-4 w-4"/></button><button className={buttonStyle} disabled={currentIndex===7} onClick={next}>Next <ArrowRight className="ml-2 inline h-4 w-4"/></button></div></div>}
    {!specialists&&stageHidden(stage)&&<DemoUnavailable what={currentStage.label}/>}
    {materialWarning&&<p role="status" className="rounded-lg border border-amber-500/30 p-3 text-sm text-amber-200">Engineering run material override: {engineering.material}. Shared specimen: {specimen.name}. This difference remains explicit in the job and report. <button className="underline" onClick={()=>useLpbfEngineeringStore.setState({material:"",properties:""})}>Use shared material</button></p>}
    {!specialists&&stage==="setup"&&<section className={panel} aria-label="Build traceability"><h3 className="font-medium">Build and specimen context</h3><p className="mt-2 text-sm text-slate-400">Record known conditions. Empty fields remain unresolved in the qualification dossier.</p><div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">{([ ["buildId","Build / experiment ID"],["machine","Machine model"],["powderLot","Powder lot"],["powderCondition","Powder condition / size distribution"],["heatTreatment","Heat treatment"],["measurementMethod","Measurement method / standard"] ] as const).map(([field,label])=><label key={field} className="text-xs text-slate-400">{label}<input className={inputStyle} value={context[field]} onChange={event=>updateContext({[field]:event.target.value})}/></label>)}</div><label className="mt-5 block text-xs text-slate-400">Research objective and known limitations<textarea className={inputStyle} rows={3} value={context.notes} onChange={event=>updateContext({notes:event.target.value})}/></label><p className="mt-4 text-xs text-slate-400">Context and process persist in this browser. Job fields and STL triangles are session data; export the dossier and geometry for a durable record.</p></section>}
    {!specialists&&stage==="material"&&<section className={panel} aria-label="Shared material and process parameters"><div className="flex flex-wrap justify-between gap-3"><div><h3 className="font-medium">{specimen.name}</h3><p className="mt-1 text-xs text-slate-400">Composition: {Object.entries(specimen.composition).map(([element,value])=>`${element} ${value}`).join(" · ")} {specimen.unit==="wt_pct"?"wt%":"at%"}</p></div><select {...lock} aria-label="Load LPBF alloy preset" className="rounded-lg border border-slate-600 bg-slate-950 px-3 py-2 text-sm" value="" onChange={event=>{if(event.target.value)loadPreset(event.target.value);}}><option value="">Load material preset…</option><option value="ti-6al-4v">Ti-6Al-4V</option><option value="ss-316l">316L</option><option value="alsi10mg">AlSi10Mg</option><option value="inconel-718">Inconel 718</option></select></div><p className="my-4 text-sm text-amber-200">Preset thermophysical values are model inputs. Inspect the worker's property source and temperature coverage before using results.</p><div className="grid gap-4 md:grid-cols-3">{processFields.map(([key,label,unit,min,max])=>{const value=specimen.lpbf[key];const invalid=!Number.isFinite(value)||value<min||value>max;return <label key={key} className="text-xs text-slate-400">{label} · {unit}<input {...lock} aria-label={`${label} (${unit})`} aria-invalid={invalid} className={inputStyle} type="number" min={min} max={max} step="any" value={value} onChange={event=>{const nextValue=event.currentTarget.valueAsNumber;if(Number.isFinite(nextValue))updateProcess({[key]:nextValue} as LpbfProcessPatch);}}/><span className={`mt-1 block ${invalid?"text-rose-300":"text-slate-500"}`}>{invalid?"Out of supported range · ":""}{min}–{max} {unit}</span></label>;})}<label className="text-xs text-slate-400">Scan strategy<select {...lock} className={inputStyle} value={specimen.lpbf.scanStrategy} onChange={event=>updateProcess({scanStrategy:event.target.value as "island"|"stripe"|"meander-67"})}><option value="stripe">Stripe</option><option value="island">Island</option><option value="meander-67">Meander / 67°</option></select></label><label className="text-xs text-slate-400">Specimen / parameter source DOI<input {...lock} className={inputStyle} value={specimen.lpbf.specimenDoi} onChange={event=>updateProcess({specimenDoi:event.target.value})}/></label></div></section>}
    {visited.has("thermal")&&<WorkspaceVisibility visible={!specialists&&stage==="thermal"}><div hidden={specialists||stage!=="thermal"}><Suspense fallback={<LoadingLab/>}><LpbfEngineeringSimulation input={sharedSimulationInput(specimen)}/></Suspense></div></WorkspaceVisibility>}
    {!specialists&&stage==="melt-pool"&&<section className={`${panel} space-y-5`} aria-label="Completed melt pool analysis">{!result?<EmptyResult status={engineering.job?.status} onRun={()=>go("thermal")}/>:<><p className="text-sm text-amber-200">{result.label} · {result.solver.id} · {report.resultMatchesCurrentInputs?"Current input signature":"Inputs changed; displaying executed job"}</p>{report.resultMatchesCurrentInputs===false&&<StaleResultBanner className="rounded-xl"/>}<MeltPoolSummaryCard result={result} stale={report.resultMatchesCurrentInputs===false}/>{result.fieldSeries?<ResolvedThermalViewer jobId={engineering.job!.id} result={result}/>:<p className="text-sm text-slate-400">No resolved field in this run. Geometry is analytical screening only.</p>}<ThermalHistory result={result}/><ConvergencePanel study={result.convergenceStudy}/><p className="text-xs text-slate-400">Material source: {result.material.source}. Conservation and convergence are numerical checks; independent experimental validation remains unresolved.</p></>}</section>}
    {!specialists&&invalidSharedProcess&&(stage==="build"||stage==="defects")&&<p role="alert" className={`${panel} text-sm text-amber-200`}>Shared process inputs are outside supported ranges. <button className="underline" onClick={()=>go("material")}>Correct Material &amp; Parameters</button> before using this stage.</p>}
    {!specialists&&!invalidSharedProcess&&stage==="defects"&&!stageHidden("defects")&&<Suspense fallback={<LoadingLab/>}><div className="mb-4 rounded-lg border border-amber-500/30 p-3 text-sm text-amber-200">Screening only. The Python build-job verdict is separate from the transient thermal job; no defect, pore or residual-stress field is inferred from this decision.</div><DefectScreening onOpenSlicer={()=>go("build")} onOpenGroundTruth={()=>go("comparison")} onOpenMeltPool={()=>go("melt-pool")}/></Suspense>}
    {visited.has("build")&&!invalidSharedProcess&&!stageHidden("build")&&<WorkspaceVisibility visible={!specialists&&stage==="build"}><div hidden={specialists||stage!=="build"}><p className="mb-3 text-sm text-slate-400"><Layers className="mr-2 inline h-4 w-4"/>{mesh?`Session geometry: ${mesh.name} · ${mesh.usedTriangleCount} solver triangles` : "No uploaded STL in the session. Preset geometry is an explicit demonstration asset."}</p><Suspense fallback={<LoadingLab/>}><BuildSlicer initialPower_W={specimen.lpbf.laserPower_W} initialSpeed_mms={specimen.lpbf.scanSpeed_mms} initialHatch_um={specimen.lpbf.hatch_um} initialLayer_um={specimen.lpbf.layer_um} initialMaterial={specimen.name} onApplyParametersToLPBF={process=>updateProcess({laserPower_W:process.laserPower_W,scanSpeed_mms:process.scanSpeed_mms,hatch_um:process.hatchSpacing_um,layer_um:process.layerThickness_um})}/></Suspense></div></WorkspaceVisibility>}
    {!specialists&&stage==="comparison"&&!stageHidden("comparison")&&<section className={`${panel} space-y-5`} aria-label="Experimental comparison"><p className="text-sm text-amber-200">Enter measured data with its source and uncertainty. These inputs do not automatically establish validation or change the solver.</p><div className="grid gap-4 md:grid-cols-3"><EvidenceInput field="width" label="Measured width (µm)" type="number"/><EvidenceInput field="depth" label="Measured depth (µm)" type="number"/><EvidenceInput field="uncertainty" label="Measurement uncertainty (µm)" type="number"/><EvidenceInput field="source" label="Measurement source"/><EvidenceInput field="specimen" label="Specimen ID or DOI"/><label className="text-xs text-slate-400">Independent holdout status<select className={inputStyle} value={engineering.holdout} onChange={event=>useLpbfEngineeringStore.setState({holdout:event.target.value})}><option value="unknown">Unknown</option><option value="no">Calibration data</option><option value="yes">User-declared independent</option></select></label></div><label className="block text-xs text-slate-400">Replicate measurement JSON<textarea className={inputStyle} rows={4} value={engineering.measurements} onChange={event=>useLpbfEngineeringStore.setState({measurements:event.target.value})}/></label><p className="text-xs text-slate-400">Replicate JSON must include the actual measurement processVector to establish matching conditions. Calibration factors are withheld when conditions are unknown.</p><button className={buttonStyle} onClick={()=>{useLpbfEngineeringStore.setState({mode:"calibration"});go("thermal");}}>Review and run comparison <ArrowRight className="ml-2 inline h-4 w-4"/></button>{result?<MeasurementPanel result={result}/>:<p className="text-sm text-slate-400">No completed comparison. Submit a sourced measurement run from Thermal Simulation.</p>}<button className={buttonStyle} onClick={()=>window.dispatchEvent(new CustomEvent("metallix-navigate-tab",{detail:{tabId:"research-hub"}}))}><BookOpen className="mr-2 inline h-4 w-4"/>Open Research Hub</button></section>}
    {!specialists&&stage==="qualification"&&<section className={`${panel} space-y-5`} aria-label="LPBF qualification report"><div className="flex flex-wrap items-center justify-between gap-4"><div><h3 className="text-lg font-medium">Research qualification dossier</h3><p className="mt-1 text-sm text-amber-200">Unresolved · not a production release or standards certificate</p></div><button className={buttonStyle} {...unavailable} onClick={exportReport}><Download className="mr-2 inline h-4 w-4"/>Export qualification JSON</button>{!IS_STATIC_DEMO&&<LpbfRunReportExport report={report} buildJob={build.lastKey===peekLpbfBuildJobKey()?build.job:null}/>}</div><dl className="grid gap-4 md:grid-cols-3">{[["Build",context.buildId||"Unassigned"],["Simulation job",engineering.job?.id||"Not submitted"],["Executed solver",result?.solver.id||"Unresolved"],["Result type",report.resultType],["Input alignment",report.resultMatchesCurrentInputs===null?"No result":report.resultMatchesCurrentInputs?"Matches current inputs":"Stale · executed snapshot retained"],["Linked registry evidence",String(evidence.length)]].map(([label,value])=><div key={label}><dt className="text-xs text-slate-400">{label}</dt><dd className="mt-1 break-all text-sm">{value}</dd></div>)}</dl><div className="border-t border-slate-700 pt-4"><h4 className="text-sm font-medium">Qualification gaps and model limitations</h4><ul className="mt-3 list-disc space-y-2 pl-5 text-sm leading-6 text-slate-400">{report.limitations.map(gap=><li key={gap}>{gap}</li>)}</ul></div><p className="text-xs text-slate-400">Export includes current and executed inputs, job result, source provenance, numerical audits, linked reviewed registry records and raw measurement drafts. Conservation, convergence and experimental validation remain separate.</p></section>}
    {!specialists&&stage==="comparison"&&!stageHidden("comparison")&&<><LpbfSourceArchivePanel/><LpbfRunArchivePanel/></>}
  </section>;
}

function EmptyResult({status,onRun}:{status?:string;onRun:()=>void}) {return <div><h3 className="font-medium">No completed result</h3><p className="my-3 text-sm text-slate-400">{status?`Current job: ${status}. Only a completed job can supply melt pool results.`:"Start a thermal or screening run with the shared process vector."}</p><button className={buttonStyle} onClick={onRun}>Open Thermal Simulation</button></div>;}
function LoadingLab(){return <p role="status" className="p-6 text-sm text-slate-400">Loading engineering module…</p>;}


