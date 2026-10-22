import { ResponsiveContainer } from './VisibleResponsiveContainer';
import React, { useState, useMemo, useEffect, useRef } from "react";
import { useWorkspaceVisible } from "./WorkspaceVisibility";
import { LiteratureSolidificationCard } from "./LiteratureSolidificationCard";
import {
  Atom,
  Flame,
  Activity,
  Layers,
  Sparkles,
  Sliders,
  CheckCircle2,
  AlertTriangle,
  Download,
  Share2,
  TrendingUp,
  FileCode,
  Info,
  RefreshCw,
  RotateCcw,
  Zap,
  Cpu,
  ShieldCheck,
  Percent,
  Thermometer,
  Gauge,
  Maximize2,
  Table,
  Terminal,
  Database,
  Check,
} from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
  ReferenceArea,
  AreaChart,
  Area,
} from "recharts";
import {
  solveMultiComponentEquilibrium,
  STANDARD_MULTI_COMPONENT_ALLOYS,
  MultiComponentAlloyComposition,
  MultiComponentSolveResult,
} from "../physics/calphadMultiComponentSolver";
import {
  PRELOADED_MULTI_COMPONENT_TDB,
  parseTDBFile,
  ParsedTDBDatabase,
} from "../physics/tdbParser";
import {
  pythonComputationService,
  PythonCalphadSolveResult,
  PythonEngineStatus,
  PythonCalphadDatabaseEntry,
  isAbortError,
  calphadUnreachableResult,
} from "../services/pythonComputationService";
import { useMaterialSpecimenStore } from "../store/useMaterialSpecimenStore";
import { createDeferredCommit, type DeferredCommit } from "../utils/deferredCommit";
import { isPythonValidationError } from "../utils/pythonValidationError";
import {
  CLIENT_DATABASE_LABEL,
  CLIENT_MODEL_LABEL,
  calphadProvenanceLabels,
  calphadUnavailableDetails,
  formatCalphadUnavailable,
  formatComputeTime,
  formatCriticalTemperature,
  formatFreezingRange,
  buildEquilibriumCSV,
  formatNullable,
  isMcTiResult,
  MC_TI_PHASE_FRACTION_MIN_C,
  MC_TI_PHASE_FRACTION_NOTE,
  partitionSourceNote,
} from "../utils/calphadDisplay";
import {
  calphadUnavailableHeadline,
  formatModelCache,
  formatTimings,
  formatCoverageRow,
  formatPartitionK,
  scheilSummaryLines,
  SCHEIL_COMPUTED,
  calphadTemperatureWindow,
  clampProbeToRange,
  withOrderingNote,
  calphadRequestKey,
  compositionKey,
  specimenKey,
  formatChemicalPotentialKJ,
  type CalphadSystemCoverage,
} from "../utils/calphadResultDisplay";

/** A slider change starts a calculation after the slider is released or this long after the last change. */
export const SLIDER_COMMIT_DELAY_MS = 800;

type PhaseProfilePoint = { temperatureC: number; phases: ReadonlyArray<{ phaseId: string; fraction: number }> };

/** Distinct phase ids over the whole profile, in first-seen order. */
export function phaseIdsOf(profile: ReadonlyArray<PhaseProfilePoint>): string[] {
  const set = new Set<string>();
  profile.forEach((p) => p.phases.forEach((ph) => set.add(ph.phaseId)));
  return Array.from(set);
}

/**
 * Stacked-area rows for the phase-fraction chart (percent). Every row carries every phase: a phase absent at a
 * point is 0 %, not a gap, because a missing key breaks the stack (the layers above lose their base and draw false
 * gaps and spikes). Repeated composition sets of one phase are summed. A clipped point is null for every phase.
 */
export function buildPhaseChartData(profile: ReadonlyArray<PhaseProfilePoint>, phaseIds: ReadonlyArray<string>,
  clipped: (temperatureC: number) => boolean = () => false): Array<Record<string, number | null>> {
  return profile.map((point) => {
    const entry: Record<string, number | null> = { temperatureC: point.temperatureC };
    const sums = new Map<string, number>(phaseIds.map((id) => [id, 0]));
    point.phases.forEach((ph) => sums.set(ph.phaseId, (sums.get(ph.phaseId) ?? 0) + ph.fraction));
    const hide = clipped(point.temperatureC);
    sums.forEach((fraction, id) => { entry[id] = hide ? null : +(fraction * 100).toFixed(1); });
    return entry;
  });
}

/**
 * Probe chips for one equilibrium point. A phase that appears in more than one composition set keeps one chip per
 * set (they are distinct equilibrium phases), numbered "set 1", "set 2" so two chips never read identically.
 */
export function phaseChipLabels(phases: ReadonlyArray<{ phaseId: string; phaseName: string; fraction: number }>) {
  const total = new Map<string, number>();
  phases.forEach((p) => total.set(p.phaseId, (total.get(p.phaseId) ?? 0) + 1));
  const seen = new Map<string, number>();
  return phases.map((p) => {
    const n = (seen.get(p.phaseId) ?? 0) + 1;
    seen.set(p.phaseId, n);
    const base = p.phaseName.split("(")[0].trim();
    return { key: `${p.phaseId}#${n}`, label: (total.get(p.phaseId) ?? 1) > 1 ? `${base} set ${n}` : base, fraction: p.fraction };
  });
}

export interface CALPHADMultiComponentStudioProps {
  /** Test seam: a solved result to show on first paint (the live solve still replaces it). */
  initialResult?: PythonCalphadSolveResult;
  /** Test seam: the sub-tab shown on first paint. */
  initialSubTab?: "phase_fractions" | "gibbs_energy" | "solute_partitioning" | "multi_scheil" | "tdb_editor";
  /** Test seam: the database coverage list shown on first paint. */
  initialCoverage?: CalphadSystemCoverage[];
  /** Test seam: render the "calculating" state on first paint. */
  initialSolving?: boolean;
  /** Test seam: start with the Python engine off (client screening model, explicitly chosen). */
  initialUsePython?: boolean;
  /** Test seam: the studio's own composition on first paint (Live Sync is then paused, as after a preset click). */
  initialAlloy?: MultiComponentAlloyComposition;
}

export const CALPHADMultiComponentStudio: React.FC<CALPHADMultiComponentStudioProps> = ({
  initialResult,
  initialSubTab,
  initialCoverage,
  initialSolving,
  initialUsePython,
  initialAlloy,
}) => {
  const activeSpecimen = useMaterialSpecimenStore((s) => s.activeSpecimen);
  const visible = useWorkspaceVisible();
  const [isLiveSyncedWithUniversalSpecimen, setIsLiveSyncedWithUniversalSpecimen] = useState<boolean>(!initialAlloy);
  const [selectedAlloyIndex, setSelectedAlloyIndex] = useState<number>(-1); // -1 = Live Universal Specimen
  const [customAlloy, setCustomAlloy] = useState<MultiComponentAlloyComposition>(() => {
    if (initialAlloy) return JSON.parse(JSON.stringify(initialAlloy));
    const spec = useMaterialSpecimenStore.getState().activeSpecimen;
    return {
      name: spec.name,
      elements: { ...spec.composition },
      unit: "wt_pct",
    };
  });
  // The composition a calculation is started for. It follows customAlloy at once, except while a slider is being
  // dragged or has just been changed: then it catches up when the slider is released or 800 ms after the last
  // change, so a drag starts one calculation, not one per input event.
  const [committedAlloy, setCommittedAlloy] = useState<MultiComponentAlloyComposition>(customAlloy);
  const committer = useRef<DeferredCommit<MultiComponentAlloyComposition> | null>(null);
  if (!committer.current) committer.current = createDeferredCommit(setCommittedAlloy, SLIDER_COMMIT_DELAY_MS);
  useEffect(() => { committer.current!.value(customAlloy); }, [customAlloy]);
  useEffect(() => () => committer.current!.dispose(), []);
  const releaseSlider = () => committer.current!.release();
  const [selectedTdbIndex, setSelectedTdbIndex] = useState<number>(0);
  const [activeTdbContent, setActiveTdbContent] = useState<string>(
    PRELOADED_MULTI_COMPONENT_TDB[0].rawTdbText
  );
  const [viewSubTab, setViewSubTab] = useState<
    "phase_fractions" | "gibbs_energy" | "solute_partitioning" | "multi_scheil" | "tdb_editor"
  >(initialSubTab ?? "phase_fractions");

  // Open TDB Database & True Gibbs Minimizer States
  const [availableDatabases, setAvailableDatabases] = useState<PythonCalphadDatabaseEntry[]>([]);
  const [selectedDatabaseId, setSelectedDatabaseId] = useState<string>("auto");
  const [activeGibbsMetric, setActiveGibbsMetric] = useState<"gibbs_free_energy" | "activities" | "potentials">("gibbs_free_energy");

  // Reactively synchronize whenever Active Specimen is modified in Tab 1 (Alloy Formulator)
  // Keyed on the specimen's name and composition, not lastModified: LPBF process edits bump lastModified
  // but do not change the alloy, and must not trigger a new CALPHAD request.
  const sharedSpecimenKey = specimenKey(activeSpecimen.name, activeSpecimen.composition);
  useEffect(() => {
    if (isLiveSyncedWithUniversalSpecimen && activeSpecimen) {
      setSelectedAlloyIndex(-1);
      setCustomAlloy((prev) =>
        specimenKey(prev.name, prev.elements) === sharedSpecimenKey
          ? prev
          : { name: activeSpecimen.name, elements: { ...activeSpecimen.composition }, unit: "wt_pct" });
    }
  }, [sharedSpecimenKey, isLiveSyncedWithUniversalSpecimen]);

  // Python Engine Integration State
  const [usePythonEngine, setUsePythonEngine] = useState<boolean>(initialUsePython ?? true);
  // Identifies this Studio's requests: the server drops a queued, not yet started request of this key
  // when a newer one arrives (slider drags compute only the latest input).
  const supersedeKey = useRef<string>(`studio-${Math.random().toString(36).slice(2)}-${Date.now().toString(36)}`);
  const [pythonStatus, setPythonStatus] = useState<PythonEngineStatus | null>(null);
  const [isSolving, setIsSolving] = useState<boolean>(initialSolving ?? false);
  // Wall time of the running request, measured here (no estimated progress percentage exists).
  const [solveStartedAt, setSolveStartedAt] = useState<number | null>(null);
  const [solveElapsedMs, setSolveElapsedMs] = useState<number>(0);
  const [coverage, setCoverage] = useState<CalphadSystemCoverage[]>(initialCoverage ?? []);
  const [asyncSolveResult, setAsyncSolveResult] = useState<PythonCalphadSolveResult | null>(initialResult ?? null);
  // Message of a Python 422 validation refusal (shown; the client solver result is used instead).
  const [pythonValidationMessage, setPythonValidationMessage] = useState<string | null>(null);

  // Liquidus / solidus boundary refinement (multi-section equilibrium calculations; the grid is uniform)
  const [boundaryRefinement, setBoundaryRefinement] = useState<boolean>(false);
  // Scheil path on demand: remembers for which composition and database it was requested, so a new input
  // returns to the cheap default request.
  const [scheilRequestedFor, setScheilRequestedFor] = useState<string | null>(null);
  const [minRefineStep, setMinRefineStep] = useState<number>(0.5);

  // Temperature Probe
  const [probeTemperatureC, setProbeTemperatureC] = useState<number>(950);

  // Check Python Subsystem Status & fetch Open TDB Databases on mount
  useEffect(() => {
    pythonComputationService.checkEngineStatus().then((status) => {
      setPythonStatus(status);
    });
    pythonComputationService.getCalphadDatabases().then((dbRes) => {
      if (dbRes.success && dbRes.databases?.length) {
        setAvailableDatabases(dbRes.databases);
      }
      if (dbRes.success && Array.isArray(dbRes.systemCoverage)) {
        setCoverage(dbRes.systemCoverage);
      }
    });
  }, []);

  // Elapsed-time display while a calculation runs.
  useEffect(() => {
    if (!isSolving || solveStartedAt == null) return;
    const id = setInterval(() => setSolveElapsedMs(performance.now() - solveStartedAt), 250);
    return () => clearInterval(id);
  }, [isSolving, solveStartedAt]);

  // Identity of the request this input state asks for. Equal keys are identical request bodies, so the
  // same request is never sent twice (a new customAlloy object with the same content sends nothing).
  const scheilScopeKey = `${compositionKey(committedAlloy.elements)}|${selectedDatabaseId}`;
  const scheilOn = usePythonEngine && scheilRequestedFor === scheilScopeKey;
  const requestWindow = calphadTemperatureWindow(committedAlloy.elements);
  const requestKey = calphadRequestKey(
    committedAlloy.elements, committedAlloy.unit || "wt_pct", requestWindow, usePythonEngine,
    selectedDatabaseId, boundaryRefinement, minRefineStep, scheilOn,
  );
  const inflightRef = useRef<{ key: string; controller: AbortController } | null>(null);
  const answeredKeyRef = useRef<string | null>(null);

  // Solve via the Python pycalphad service (Python ON) or the client screening model (Python OFF, explicit).
  // Depends on the request key and visibility only. Nothing starts while the studio is hidden, and a key
  // that is already in flight or answered is not sent again.
  useEffect(() => {
    const running = inflightRef.current;
    if (running && running.key !== requestKey) {
      running.controller.abort(); // the input moved on: this answer would be stale
      inflightRef.current = null;
    }
    if (!visible) return;
    if (answeredKeyRef.current === requestKey) {
      setIsSolving(false);
      return;
    }
    if (inflightRef.current?.key === requestKey) {
      setIsSolving(true);
      return;
    }

    setIsSolving(true);
    setSolveStartedAt(performance.now());
    setSolveElapsedMs(0);

    const win = requestWindow;
    const controller = new AbortController();
    inflightRef.current = { key: requestKey, controller };
    const finish = (answered: boolean) => {
      if (inflightRef.current?.controller !== controller) return false; // superseded
      inflightRef.current = null;
      if (answered) answeredKeyRef.current = requestKey;
      return true;
    };
    let fired = false;
    const timer = setTimeout(() => {
      fired = true;
      pythonComputationService
        .solveCalphadEquilibrium(
          committedAlloy,
          win.tMin,
          win.tMax,
          win.tStep,
          usePythonEngine,
          selectedDatabaseId === "auto" ? undefined : selectedDatabaseId,
          undefined,
          false, // no adaptive grid exists in the engine
          boundaryRefinement,
          minRefineStep,
          { signal: controller.signal, supersedeKey: supersedeKey.current, scheil: scheilOn }
        )
        .then((res) => {
          if (!finish(true)) return;
          setPythonValidationMessage(null);
          setAsyncSolveResult(res);
          setIsSolving(false);
        })
        .catch((err) => {
          if (isAbortError(err) && controller.signal.aborted) {
            finish(false);
            return; // superseded by newer input
          }
          if (isPythonValidationError(err)) {
            // Python refused the input (HTTP 422): say so; no result is shown (no client substitute).
            if (!finish(true)) return;
            setPythonValidationMessage(err.message);
            setAsyncSolveResult(null);
            setIsSolving(false);
            return;
          }
          // Any other end without an answer is shown as such: the studio never keeps waiting on a request
          // that is over (no numbers; the reason names the failure).
          console.warn("Async solve error:", err);
          if (!finish(true)) return;
          setPythonValidationMessage(null);
          setAsyncSolveResult(calphadUnreachableResult(committedAlloy, win.tMin, win.tMax, win.tStep,
            `the CALPHAD request failed in the browser (${err instanceof Error ? err.message : String(err)})`));
          setIsSolving(false);
        });
    }, 80); // Debounce slider changes

    return () => {
      if (!fired) {
        // Not sent yet (re-render with another key, or the studio was hidden during the debounce).
        clearTimeout(timer);
        if (inflightRef.current?.controller === controller) inflightRef.current = null;
      }
    };
  }, [requestKey, visible]);

  // Unmount: stop the request still waiting on this studio's behalf.
  // The ref is cleared too: if the effects run again on the same instance (Fast Refresh), the same key is sent
  // again instead of waiting on the aborted request.
  useEffect(() => () => {
    inflightRef.current?.controller.abort();
    inflightRef.current = null;
  }, []);

  // Switch preloaded alloy
  const handleSelectPreload = (idx: number) => {
    committer.current!.reset();
    setSelectedAlloyIndex(idx);
    const standard = STANDARD_MULTI_COMPONENT_ALLOYS[idx];
    if (standard) {
      setCustomAlloy(JSON.parse(JSON.stringify(standard)));
      // A preset that names a database selects it; every other preset returns to auto-detect.
      setSelectedDatabaseId(standard.preferredDatabaseId ?? "auto");
    }
    if (PRELOADED_MULTI_COMPONENT_TDB[idx]) {
      setSelectedTdbIndex(idx);
      setActiveTdbContent(PRELOADED_MULTI_COMPONENT_TDB[idx].rawTdbText);
    }
  };

  // Adjust element composition
  const handleElementChange = (element: string, val: number) => {
    committer.current!.touch(); // the calculation waits for release or 800 ms of quiet
    const updated = {
      ...customAlloy.elements,
      [element]: +val.toFixed(2),
    };
    setCustomAlloy((prev) => ({
      ...prev,
      elements: updated,
    }));
    if (isLiveSyncedWithUniversalSpecimen) {
      useMaterialSpecimenStore.getState().updateComposition(
        updated,
        customAlloy.name,
        undefined,
        "CALPHAD Thermodynamic Studio (Tab 2)"
      );
    }
  };

  // Parsed TDB Database representation
  const parsedTdb: ParsedTDBDatabase = useMemo(() => {
    return parseTDBFile(
      activeTdbContent,
      PRELOADED_MULTI_COMPONENT_TDB[selectedTdbIndex]?.name || "Active Database"
    );
  }, [activeTdbContent, selectedTdbIndex]);

  // Fallback solved Multi-Component Thermodynamic Equilibrium
  const clientSolveResult: MultiComponentSolveResult = useMemo(() => {
    return solveMultiComponentEquilibrium(customAlloy, parsedTdb, 500, 1450, 20);
  }, [customAlloy, parsedTdb]);

  // Effective solve result (Python result preferred, client result as fallback)
  const solveResult: PythonCalphadSolveResult = asyncSolveResult || {
    ...clientSolveResult,
    engine: "MetalliX-Client-WASM/TS",
    computeTimeMs: null,
    isPythonEngine: false,
    isEmpirical: true,
    databaseUsed: CLIENT_DATABASE_LABEL,
    thermodynamicModel: CLIENT_MODEL_LABEL,
  };
  const provenanceLabels = calphadProvenanceLabels(solveResult);
  const tempWindowStep = (range: [number, number]) => (range[1] - range[0] > 600 ? 25 : 10);
  const tempWindow = calphadTemperatureWindow(customAlloy.elements);
  const criticalStatus = solveResult.criticalTemperatureStatus ?? {};
  // A Python "unavailable" answer is shown as such: no equilibrium numbers (the client screening model
  // is not substituted; it is shown only when the user switches the Python engine off).
  const pythonUnavailable = usePythonEngine ? solveResult.pythonUnavailable : undefined;
  // With Python ON, nothing but a pycalphad answer is shown: before the first answer, after a refusal
  // (422) or while only a client result from an earlier Python-OFF period exists, no numbers appear.
  const pythonRefused = usePythonEngine && pythonValidationMessage != null;
  const pythonPending = usePythonEngine && !pythonRefused && !pythonUnavailable &&
    !(asyncSolveResult && asyncSolveResult.isPythonEngine);
  const showNumbers = !pythonUnavailable && !pythonPending && !pythonRefused;
  const phaseNotes = solveResult.phaseNameNotes ?? {};
  const timingText = formatTimings(solveResult.timingsMs);
  const scheilBlock = solveResult.scheilSolidification;
  const gibbsNumbers = showNumbers && provenanceLabels.isPycalphad;
  const scheilComputed = provenanceLabels.isPycalphad && scheilBlock?.status !== undefined && scheilBlock.status !== "unavailable";

  // Active components list for activities and chemical potentials
  const activeComponentsList = useMemo(() => {
    if (solveResult.activeComponents && solveResult.activeComponents.length > 0) {
      return solveResult.activeComponents;
    }
    return Object.keys(customAlloy.elements).map((e) => e.toUpperCase());
  }, [solveResult, customAlloy]);

  // Chart Data for Phase Fractions vs Temperature
  // mc_ti is not valid for alpha/beta fractions below about 900 C: those grid points are not plotted (null, no area).
  const phaseFractionsClipped = isMcTiResult(solveResult);
  // All distinct phase IDs
  const allPhaseIds = useMemo(() => phaseIdsOf(solveResult.equilibriumProfile), [solveResult]);
  const phaseChartData = useMemo(
    () => buildPhaseChartData(solveResult.equilibriumProfile, allPhaseIds,
      (t) => phaseFractionsClipped && t < MC_TI_PHASE_FRACTION_MIN_C),
    [solveResult, phaseFractionsClipped, allPhaseIds]);
  const clippedGridTemps = phaseFractionsClipped
    ? solveResult.equilibriumProfile.map((p) => p.temperatureC).filter((t) => t < MC_TI_PHASE_FRACTION_MIN_C).sort((a, b) => a - b)
    : [];

  // Chart Data for Gibbs Free Energy, Activities, and Chemical Potentials
  const gibbsChartData = useMemo(() => {
    return solveResult.equilibriumProfile.map((point) => {
      const entry: any = {
        temperatureC: point.temperatureC,
        totalGibbsEnergy_kJ_mol: point.totalGibbsEnergy_kJ_mol,
      };
      if (point.thermodynamicActivities) {
        Object.entries(point.thermodynamicActivities).forEach(([el, val]) => {
          // null = no reference state for this element: no point is drawn (never a 0)
          entry[`act_${el}`] = typeof val === "number" && val > 0 ? +val.toExponential(3) : null;
        });
      }
      if (point.chemicalPotentials_J_mol) {
        Object.entries(point.chemicalPotentials_J_mol).forEach(([el, val]) => {
          // a missing or non-finite potential is null (no point drawn), never 0
          entry[`mu_${el}`] = typeof val === "number" && Number.isFinite(val) ? +(val / 1000.0).toFixed(2) : null;
        });
      }
      return entry;
    });
  }, [solveResult]);

  // Equilibrium fraction solid vs T (grid points inside the freezing range plus its two ends), for the Scheil tab.
  const equilibriumSolidCurve = useMemo(() => {
    const pts = solveResult.equilibriumProfile
      .filter((p) => p.status !== "not-converged")
      .map((p) => {
        const liquid = p.phases.filter((ph) => ph.phaseId.includes("LIQUID")).reduce((acc, ph) => acc + ph.fraction, 0);
        return { temperatureC: p.temperatureC, fractionSolid: +(1 - liquid).toFixed(4), liquid };
      })
      .sort((x, y) => x.temperatureC - y.temperatureC);
    const inside = pts.filter((p) => p.liquid > 0 && p.liquid < 1);
    const out: { temperatureC: number; fractionSolid: number }[] = [];
    const { liquidusC, solidusC } = solveResult.criticalTemperatures;
    if (typeof liquidusC === "number") out.push({ temperatureC: liquidusC, fractionSolid: 0 });
    inside.reverse().forEach((p) => out.push({ temperatureC: p.temperatureC, fractionSolid: p.fractionSolid }));
    if (typeof solidusC === "number") out.push({ temperatureC: solidusC, fractionSolid: 1 });
    return out;
  }, [solveResult]);

  // Probe at current temperature
  const solvedRange = solveResult.temperatureRangeC;
  useEffect(() => {
    // The probe stays on the solved grid when the window changes (e.g. 950 C for an Al alloy solved 400-750 C).
    setProbeTemperatureC((t) => clampProbeToRange(t, solvedRange[0], solvedRange[1], tempWindowStep(solvedRange)));
  }, [solvedRange[0], solvedRange[1]]);

  const currentEquilibriumPoint = useMemo(() => {
    if (solveResult.equilibriumProfile.length === 0) {
      return { temperatureC: probeTemperatureC, phases: [], totalGibbsEnergy_kJ_mol: null,
        thermodynamicActivities: undefined, chemicalPotentials_J_mol: undefined } as unknown as
        PythonCalphadSolveResult["equilibriumProfile"][number];
    }
    const closest = solveResult.equilibriumProfile.reduce((prev, curr) => {
      return Math.abs(curr.temperatureC - probeTemperatureC) < Math.abs(prev.temperatureC - probeTemperatureC)
        ? curr
        : prev;
    });
    return closest;
  }, [solveResult, probeTemperatureC]);

  // Export solved thermodynamic equilibrium report
  const handleExportEquilibriumCSV = () => {
    const csv = buildEquilibriumCSV(solveResult);

    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${customAlloy.name.replace(/\s+/g, "_")}_Equilibrium_CALPHAD.csv`;
    a.click();
  };

  // Export current TDB file
  const handleExportTDBFile = () => {
    const blob = new Blob([activeTdbContent], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${customAlloy.name.replace(/\s+/g, "_")}_CALPHAD.tdb`;
    a.click();
  };

  return (
    <div className="space-y-5 font-mono">
      {/* Studio Header */}
      <div className="p-4 rounded-2xl bg-[#090e18] border border-[#1e2d46] flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-violet-500/10 border border-violet-500/30 flex items-center justify-center text-violet-400">
            <Atom className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className="text-base sm:text-lg font-bold text-white tracking-tight">
                Generalized Multi-Component CALPHAD Gibbs Minimizer
              </h2>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-violet-500/20 text-violet-300 border border-violet-500/40 font-bold">
                5+ Elements Superalloys
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-bold hidden sm:inline-block">
                OpenCALPHAD TDB
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Solves multi-phase thermodynamic equilibrium for nickel superalloys, titanium alloys, and high-entropy systems (HEAs).
            </p>
          </div>
        </div>

        {/* Top Action Buttons & Python HPC Engine Controller */}
        <div className="flex items-center gap-2 flex-wrap">
          {/* Python HPC Acceleration Switch */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-[#050810] border border-[#1e2d46]">
            <Cpu className={`w-3.5 h-3.5 ${usePythonEngine ? "text-sky-400 animate-pulse" : "text-slate-500"}`} />
            <span className="text-xs text-slate-300 font-semibold">Python HPC:</span>
            <button
              type="button"
              onClick={() => setUsePythonEngine(!usePythonEngine)}
              className={`px-2 py-0.5 rounded text-[10px] font-bold transition ${
                usePythonEngine
                  ? "bg-sky-500/20 text-sky-300 border border-sky-500/40 shadow-[0_0_8px_rgba(56,189,248,0.25)]"
                  : "bg-slate-800 text-slate-400 border border-slate-700"
              }`}
            >
              {usePythonEngine ? "ON (Backend Proxy)" : "OFF (Client TS)"}
            </button>
          </div>

          <button
            type="button"
            onClick={handleExportTDBFile}
            className="px-3 py-1.5 rounded-xl bg-[#050810] border border-[#1e2d46] hover:border-violet-400 text-violet-300 text-xs font-semibold transition flex items-center gap-1.5"
          >
            <FileCode className="w-3.5 h-3.5 text-violet-400" />
            <span>Export .TDB</span>
          </button>
          <button
            type="button"
            onClick={handleExportEquilibriumCSV}
            className="px-3 py-1.5 rounded-xl bg-[#050810] border border-[#1e2d46] hover:border-emerald-400 text-emerald-300 text-xs font-semibold transition flex items-center gap-1.5"
          >
            <Download className="w-3.5 h-3.5 text-emerald-400" />
            <span>Export CSV</span>
          </button>
        </div>
      </div>

      {pythonValidationMessage && (
        <div role="alert" className="px-4 py-2 rounded-xl bg-amber-500/10 border border-amber-500/40 text-amber-200 text-xs">
          Python solver refused the input: {pythonValidationMessage}. No result is shown; correct the input, or switch
          Python HPC off to look at the client screening model.
        </div>
      )}

      {isSolving && (
        <div role="status" aria-live="polite" data-testid="calphad-solving"
          className="px-4 py-2 rounded-xl bg-sky-500/10 border border-sky-500/40 text-sky-200 text-xs space-y-0.5">
          <div className="flex items-center gap-2">
            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            <strong>Calculating, typically 20 to 45 s (the first run per element set compiles models)</strong>
            <span>{(solveElapsedMs / 1000).toFixed(1)} s elapsed</span>
          </div>
          {usePythonEngine && (
            <div>The first calculation for a database and element set builds and compiles the thermodynamic models;
              later ones for the same system reuse them. No completion estimate exists for a single calculation.</div>
          )}
          {asyncSolveResult && <div>The results below belong to the previous input until this calculation finishes.</div>}
        </div>
      )}

      {pythonUnavailable && (
        <div role="alert" data-testid="calphad-unavailable" className="px-4 py-3 rounded-xl bg-amber-500/10 border border-amber-500/40 text-amber-200 text-xs space-y-0.5">
          <div className="text-sm font-bold">{calphadUnavailableHeadline(pythonUnavailable)}</div>
          <div>{formatCalphadUnavailable(pythonUnavailable)}</div>
          {calphadUnavailableDetails(pythonUnavailable).map((line) => (
            <div key={line}>{line}</div>
          ))}
          <div>No equilibrium numbers are shown for this request. The client-side screening model is not a substitute;
            switch Python HPC off to look at it, labelled as a screening model.</div>
        </div>
      )}

      {showNumbers && provenanceLabels.isPycalphad && (
        <div data-testid="calphad-provenance" className={`px-4 py-1.5 rounded-xl bg-[#060a14] border border-[#1a273e] text-[11px] text-slate-300 space-y-0.5 ${isSolving ? "opacity-60" : ""}`}>
          <div>
            Provenance: pycalphad {solveResult.pycalphadVersion ?? "(version not reported)"} equilibrium on {provenanceLabels.database}
            {solveResult.modelCache?.databaseSha256 ? ` (TDB SHA-256 ${solveResult.modelCache.databaseSha256.slice(0, 12)}…)` : ""}.
            Calculated, not validated against experiment in this application.
          </div>
          <div data-testid="calphad-model-cache">
            {formatModelCache(solveResult.modelCache)}{timingText ? `. Measured: ${timingText}.` : "."}
          </div>
        </div>
      )}

      {coverage.length > 0 && (
        <details data-testid="calphad-coverage" className="px-4 py-1.5 rounded-xl bg-[#060a14] border border-[#1a273e] text-[11px] text-slate-300">
          <summary className="cursor-pointer text-slate-200 font-semibold">
            Database coverage: {coverage.filter((c) => c.status === "covered").length} of {coverage.length} reference alloy systems
          </summary>
          <ul className="mt-1 space-y-0.5">
            {coverage.map((row) => (
              <li key={row.id} className={row.status === "covered" ? "text-slate-300" : "text-amber-200"}>
                {formatCoverageRow(row)}
                {row.knownDeviation && <span className="block text-amber-300/90">Known deviation: {row.knownDeviation}</span>}
              </li>
            ))}
          </ul>
        </details>
      )}

      {/* Python HPC Telemetry & Execution Banner */}
      <div className="px-4 py-2.5 rounded-xl bg-[#060a14] border border-[#1a273e] flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2.5 flex-wrap">
          <span className="flex items-center gap-1.5 text-slate-300">
            <span className={`w-2 h-2 rounded-full ${showNumbers && solveResult.isPythonEngine ? "bg-emerald-400 animate-ping" : "bg-amber-400"}`} />
            <strong className="text-white">Active Engine:</strong>
            <span className="text-sky-300 font-bold">
              {showNumbers ? solveResult.engine || "pycalphad-open-tdb"
                : pythonUnavailable ? "pycalphad (unavailable for this input)"
                : "pycalphad (no result for this input yet)"}
            </span>
            {solveResult.pycalphadVersion && (
              <span className="text-[10px] px-1.5 py-0.2 rounded bg-sky-500/20 text-sky-300 border border-sky-500/30">
                v{solveResult.pycalphadVersion}
              </span>
            )}
          </span>
          <span className="text-slate-600">|</span>
          <span className="text-slate-400">
            Database: <strong className="text-violet-300">{showNumbers ? provenanceLabels.database : pythonUnavailable?.databaseUsed ?? "n/a"}</strong>
          </span>
          <span className="text-slate-600">|</span>
          <span className="text-slate-400">
            Compute Time: <strong className="text-emerald-400">{formatComputeTime(showNumbers ? solveResult.computeTimeMs : null)}</strong>
            {solveResult.proxyRoundtripMs ? ` (HTTP Proxy: ${solveResult.proxyRoundtripMs}ms)` : ""}
          </span>
        </div>

        {/* Database Selector Dropdown */}
        <div className="flex items-center gap-2">
          <Database className="w-3.5 h-3.5 text-violet-400" />
          <span className="text-slate-400 font-medium">TDB Source:</span>
          <select aria-label="TDB Source"
            value={selectedDatabaseId}
            onChange={(e) => setSelectedDatabaseId(e.target.value)}
            className="bg-[#050810] border border-[#1e2d46] text-xs text-sky-300 rounded-lg px-2.5 py-1 focus:outline-none focus:border-violet-500 font-mono"
          >
            <option value="auto">⚡ Auto-Detect Database (Composition Match)</option>
            {availableDatabases.map((db) => (
              <option key={db.id} value={db.id} disabled={db.usable === false}>
                {db.name} ({db.elements.slice(0, 5).join("-")}...){db.usable === false ? " - test fixture, refused" : ""}
              </option>
            ))}
            {availableDatabases.length === 0 && (
              <>
                <option value="cost507">COST 507 Light Alloys (29 Elements Al-Mg-Ti...)</option>
                <option value="mc_ti">MatCalc mc_ti 2.03 Ti alloys (Ti-Al-V, scoped)</option>
                <option value="alni_dupin_2001">Al-Ni Dupin 2001 NIST Benchmark</option>
                <option value="crtiv_ghosh">Cr-Ti-V Assessment (Ghosh), no Al</option>
              </>
            )}
          </select>
        </div>
      </div>

      {provenanceLabels.scope && (
        <div className="px-4 py-1.5 rounded-xl bg-[#060a14] border border-[#1a273e] text-[11px] text-amber-200/90" data-testid="calphad-database-scope">
          Database scope: {provenanceLabels.scope}
        </div>
      )}
      {showNumbers && provenanceLabels.scopeFlag && (
        <div role="note" className="px-4 py-1.5 rounded-xl bg-amber-500/10 border border-amber-500/40 text-[11px] text-amber-200" data-testid="calphad-database-scope-flag">
          Scope flag: {provenanceLabels.scopeFlag}
        </div>
      )}
      {showNumbers && solveResult.nonConvergedPoints && solveResult.nonConvergedPoints.length > 0 && (
        <div role="alert" className="px-4 py-1.5 rounded-xl bg-amber-500/10 border border-amber-500/40 text-amber-200 text-[11px]">
          {solveResult.nonConvergedPoints.length} grid point(s) did not converge and are shown as n/a: {solveResult.nonConvergedPoints.join(", ")} °C.
        </div>
      )}

      {/* Liquidus / solidus boundary refinement control strip */}
      <div className="p-3.5 rounded-xl bg-[#070b16] border border-sky-500/30 space-y-2.5 text-xs font-mono">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="flex items-center gap-2.5 flex-wrap">
            <div className="w-7 h-7 rounded-lg bg-sky-500/10 border border-sky-500/30 flex items-center justify-center text-sky-400">
              <Zap className="w-3.5 h-3.5" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-bold text-white">Liquidus / solidus boundary refinement</span>
                <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold border ${
                  boundaryRefinement
                    ? "bg-sky-500/20 text-sky-300 border-sky-500/40"
                    : "bg-slate-800 text-slate-400 border-slate-700"
                }`}>
                  {boundaryRefinement ? "REFINEMENT ON" : "GRID BRACKET ONLY"}
                </span>
              </div>
              <p className="text-[11px] text-slate-400">
                Python / pycalphad engine only. The temperature grid is uniform (at most 80 points); there is no adaptive grid.
                The liquidus and solidus are located between the bracketing grid points by repeated multi-section equilibrium
                calculations down to the tolerance chosen here.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <button
              type="button"
              onClick={() => {
                // Scheil needs a bisected liquidus: switching refinement off also withdraws the Scheil request.
                if (boundaryRefinement) setScheilRequestedFor(null);
                setBoundaryRefinement(!boundaryRefinement);
              }}
              className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition border flex items-center gap-1.5 ${
                boundaryRefinement
                  ? "bg-violet-500/20 text-violet-300 border-violet-500/40 shadow-sm"
                  : "bg-slate-800 text-slate-500 border-slate-700 opacity-80"
              }`}
            >
              <Sparkles className="w-3 h-3" />
              <span>{boundaryRefinement ? "Boundary Refine: ON" : "Boundary Refine: OFF"}</span>
            </button>

            <div className="flex items-center gap-1 bg-[#050810] border border-[#1e2d46] rounded-lg px-2 py-0.5">
              <span className="text-[11px] text-slate-400">Tolerance:</span>
              <select aria-label="Boundary tolerance"
                disabled={!boundaryRefinement}
                value={minRefineStep}
                onChange={(e) => setMinRefineStep(parseFloat(e.target.value))}
                className="bg-transparent text-xs text-sky-300 focus:outline-none font-mono"
              >
                <option value="0.2">0.2°C</option>
                <option value="0.5">0.5°C</option>
                <option value="1.0">1.0°C</option>
                <option value="2.0">2.0°C</option>
              </select>
            </div>
          </div>
        </div>

        {showNumbers && solveResult.boundaryRefinement && (
          <div className="pt-2 border-t border-[#162032] text-[11px] text-slate-300">
            Refinement {solveResult.boundaryRefinement.enabled ? "on" : "off"}, tolerance ±{solveResult.boundaryRefinement.toleranceC}°C,{" "}
            {solveResult.boundaryRefinement.equilibriumCalls} refinement round(s). {solveResult.boundaryRefinement.note}
          </div>
        )}
      </div>

      {specimenKey(customAlloy.name, customAlloy.elements) !== sharedSpecimenKey && (
        <div role="status" data-testid="calphad-composition-mismatch"
          className="px-4 py-2 rounded-xl bg-amber-500/10 border border-amber-500/40 text-amber-200 text-xs">
          This studio is calculating {customAlloy.name}, not the shared material {activeSpecimen.name}. Re-Sync to calculate the shared material.
        </div>
      )}

      {/* Universal Specimen Reactive Thread Status Banner */}
      <div className="p-3.5 rounded-xl bg-gradient-to-r from-sky-950/30 via-indigo-950/20 to-purple-950/30 border border-sky-500/30 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs font-mono">
        <div className="flex items-center gap-2.5">
          <span className={`w-2.5 h-2.5 rounded-full ${isLiveSyncedWithUniversalSpecimen ? "bg-emerald-400 animate-pulse" : "bg-slate-500"}`} />
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <strong className="text-white">Active Material Specimen:</strong>
              <span className="text-sky-300 font-bold">{activeSpecimen.name}</span>
              <span className="text-[10px] px-2 py-0.5 rounded bg-sky-500/20 text-sky-300 border border-sky-500/30 font-semibold">
                {activeSpecimen.chemicalFormula}
              </span>
            </div>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Source: <span className="text-slate-300 font-semibold">{activeSpecimen.sourceTab}</span> • <span data-testid="calphad-specimen-properties-unavailable">Specimen liquidus, solidus and yield strength: unavailable (not computed from composition); liquidus/solidus come only from the calculation in this studio.</span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setIsLiveSyncedWithUniversalSpecimen(!isLiveSyncedWithUniversalSpecimen)}
            className={`px-2.5 py-1.5 rounded-lg text-xs font-semibold transition border flex items-center gap-1.5 ${
              isLiveSyncedWithUniversalSpecimen
                ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40 shadow-[0_0_10px_rgba(16,185,129,0.2)]"
                : "bg-slate-800 text-slate-400 border-slate-700"
            }`}
          >
            <span>{isLiveSyncedWithUniversalSpecimen ? "⚡ Live Sync: ON" : "Live Sync: PAUSED"}</span>
          </button>
          <button
            type="button"
            onClick={() => {
              setSelectedAlloyIndex(-1);
              setIsLiveSyncedWithUniversalSpecimen(true);
              setCustomAlloy({
                name: activeSpecimen.name,
                elements: { ...activeSpecimen.composition },
                unit: "wt_pct",
              });
            }}
            className="px-2.5 py-1.5 rounded-lg bg-sky-500/15 hover:bg-sky-500/25 border border-sky-500/30 text-sky-300 text-xs font-semibold transition flex items-center gap-1"
          >
            <RotateCcw className="w-3 h-3 text-sky-400" />
            <span>Re-Sync</span>
          </button>
        </div>
      </div>

      {/* Preloaded Multi-Component Alloy Selector */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
        {/* Active Universal Specimen Card */}
        <button
          type="button"
          onClick={() => {
            setSelectedAlloyIndex(-1);
            setIsLiveSyncedWithUniversalSpecimen(true);
            setCustomAlloy({
              name: activeSpecimen.name,
              elements: { ...activeSpecimen.composition },
              unit: "wt_pct",
            });
          }}
          className={`p-3 rounded-xl border text-left transition relative overflow-hidden ${
            selectedAlloyIndex === -1
              ? "bg-sky-950/50 border-sky-400 text-sky-100 shadow-[0_0_15px_rgba(56,189,248,0.3)] ring-1 ring-sky-400"
              : "bg-[#090e18] border-[#1e2d46] text-slate-400 hover:text-white"
          }`}
        >
          <div className="flex items-center justify-between">
            <div className="text-[10px] font-bold text-sky-400 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              <span>UNIVERSAL SPECIMEN</span>
            </div>
          </div>
          <div className="text-xs font-bold text-white truncate mt-1">{activeSpecimen.name}</div>
          <div className="text-[10px] text-sky-300 font-medium mt-0.5 truncate">
            {activeSpecimen.chemicalFormula}
          </div>
          <div className="text-[9px] text-slate-400 mt-1">
            Base: {activeSpecimen.baseMetal} ({activeSpecimen.composition[activeSpecimen.baseMetal] || 0}%)
          </div>
        </button>

        {STANDARD_MULTI_COMPONENT_ALLOYS.map((alloy, idx) => (
          <button
            key={alloy.name}
            type="button"
            onClick={() => {
              setIsLiveSyncedWithUniversalSpecimen(false);
              handleSelectPreload(idx);
            }}
            className={`p-3 rounded-xl border text-left transition ${
              selectedAlloyIndex === idx
                ? "bg-violet-950/40 border-violet-500/60 text-violet-200 shadow-[0_0_12px_rgba(139,92,246,0.25)]"
                : "bg-[#090e18] border-[#1e2d46] text-slate-400 hover:text-white"
            }`}
          >
            <div className="text-xs font-bold text-white truncate">{alloy.name.split("(")[0]}</div>
            <div className="text-[10px] text-violet-400 font-medium mt-0.5">
              {Object.keys(alloy.elements).length} Components ({Object.keys(alloy.elements).join("-")})
            </div>
            <div className="text-[9px] text-slate-500 mt-1">
              Base: {Object.keys(alloy.elements)[0]} ({alloy.elements[Object.keys(alloy.elements)[0]]}%)
            </div>
          </button>
        ))}
      </div>

      {/* Main Grid: Composition & State Sliders (Left 4 cols) + Interactive CALPHAD Graphs (Right 8 cols) */}
      <div className={`grid grid-cols-1 lg:grid-cols-12 gap-5 ${isSolving ? "opacity-60" : ""}`} aria-busy={isSolving}>
        {/* Left Column: Multi-Element Composition Sliders & Critical Temperatures */}
        <div className="lg:col-span-4 space-y-4">
          {/* Element Sliders */}
          <div className="p-4 rounded-2xl bg-[#090e18] border border-[#1e2d46] space-y-3">
            <div className="flex items-center justify-between border-b border-[#162032] pb-2 text-xs">
              <span className="font-bold text-white flex items-center gap-1.5">
                <Sliders className="w-3.5 h-3.5 text-violet-400" />
                <span>Element Composition (wt%)</span>
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded bg-violet-500/10 text-violet-300 font-bold border border-violet-500/30">
                {Object.keys(customAlloy.elements).length} Elements
              </span>
            </div>

            <div className="space-y-2.5 max-h-[320px] overflow-y-auto pr-1">
              {Object.entries(customAlloy.elements).map(([el, val]) => (
                <div key={el} className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold text-slate-200">{el}</span>
                    <span className="text-violet-300 font-bold">{val}%</span>
                  </div>
                  <input aria-label={`${el} content (%)`}
                    type="range"
                    min="0"
                    max={el === "Ni" || el === "Ti" || el === "Fe" ? "90" : "25"}
                    step="0.1"
                    value={val}
                    onChange={(e) => handleElementChange(el, parseFloat(e.target.value))}
                    onPointerUp={releaseSlider}
                    onBlur={releaseSlider}
                    className="w-full accent-violet-500"
                  />
                </div>
              ))}
            </div>
          </div>

          {/* Critical Transition Temperatures */}
          {showNumbers && (
          <div className="p-4 rounded-2xl bg-[#090e18] border border-[#1e2d46] space-y-3">
            <div className="flex items-center justify-between border-b border-[#162032] pb-2 text-xs">
              <span className="font-bold text-white flex items-center gap-1.5">
                <Thermometer className="w-3.5 h-3.5 text-rose-400" />
                <span>Critical Transition Solvus</span>
              </span>
              <span
                className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                  solveResult.tcpEmbrittlementRisk == null
                    ? "bg-slate-800 text-slate-400 border border-slate-700"
                    : solveResult.tcpEmbrittlementRisk === "Low"
                    ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                    : solveResult.tcpEmbrittlementRisk === "Moderate"
                    ? "bg-amber-500/10 text-amber-400 border border-amber-500/30"
                    : "bg-rose-500/10 text-rose-400 border border-rose-500/30"
                }`}
              >
                <span title={solveResult.phacompAnalysis?.reason ?? solveResult.phacompAnalysis?.riskBasis ?? ""}>TCP Risk: {solveResult.tcpEmbrittlementRisk ?? "Unavailable"}</span>
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs font-mono">
              <div className="p-2 rounded-xl bg-[#050810] border border-[#162032]" title={formatCriticalTemperature(solveResult.criticalTemperatures.liquidusC, criticalStatus.liquidusC).title}>
                <div className="text-[10px] text-slate-400">Liquidus (T_liq):</div>
                <div className="text-sm font-bold text-sky-300">{formatCriticalTemperature(solveResult.criticalTemperatures.liquidusC, criticalStatus.liquidusC).text}</div>
              </div>
              <div className="p-2 rounded-xl bg-[#050810] border border-[#162032]" title={formatCriticalTemperature(solveResult.criticalTemperatures.solidusC, criticalStatus.solidusC).title}>
                <div className="text-[10px] text-slate-400">Solidus (T_sol):</div>
                <div className="text-sm font-bold text-emerald-300">{formatCriticalTemperature(solveResult.criticalTemperatures.solidusC, criticalStatus.solidusC).text}</div>
              </div>
              {(solveResult.criticalTemperatures.gammaPrimeSolvusC || criticalStatus.gammaPrimeSolvusC) && (
                <div className="p-2 rounded-xl bg-[#050810] border border-[#162032]" title={formatCriticalTemperature(solveResult.criticalTemperatures.gammaPrimeSolvusC, criticalStatus.gammaPrimeSolvusC).title}>
                  <div className="text-[10px] text-slate-400">γ' Solvus:</div>
                  <div className="text-sm font-bold text-purple-300">{formatCriticalTemperature(solveResult.criticalTemperatures.gammaPrimeSolvusC, criticalStatus.gammaPrimeSolvusC).text}</div>
                </div>
              )}
              {solveResult.criticalTemperatures.gammaDoublePrimeSolvusC && (
                <div className="p-2 rounded-xl bg-[#050810] border border-[#162032]">
                  <div className="text-[10px] text-slate-400">γ'' Solvus:</div>
                  <div className="text-sm font-bold text-violet-300">{solveResult.criticalTemperatures.gammaDoublePrimeSolvusC}°C</div>
                </div>
              )}
              {solveResult.criticalTemperatures.deltaSolvusC && (
                <div className="p-2 rounded-xl bg-[#050810] border border-[#162032]">
                  <div className="text-[10px] text-slate-400">δ-Phase Solvus:</div>
                  <div className="text-sm font-bold text-amber-300">{solveResult.criticalTemperatures.deltaSolvusC}°C</div>
                </div>
              )}
              {solveResult.criticalTemperatures.betaTransusC && (
                <div className="p-2 rounded-xl bg-[#050810] border border-[#162032]" title={criticalStatus.betaTransusC?.note ?? ""}
                  data-testid="beta-transus-card">
                  <div className="text-[10px] text-slate-400">β-Transus (phase-name heuristic, grid resolution):</div>
                  <div className="text-sm font-bold text-amber-300">{solveResult.criticalTemperatures.betaTransusC}°C</div>
                  {criticalStatus.betaTransusC?.knownDeviation && (
                    <div className="text-[10px] text-amber-200/90 mt-0.5">{criticalStatus.betaTransusC.knownDeviation}</div>
                  )}
                </div>
              )}
              {(criticalStatus.liquidusC?.knownDeviation || criticalStatus.solidusC?.knownDeviation) && (
                <div className="col-span-2 text-[10px] text-amber-200/90" data-testid="melting-deviation">
                  {criticalStatus.liquidusC?.knownDeviation ?? criticalStatus.solidusC?.knownDeviation}
                </div>
              )}
            </div>
          </div>
          )}
        </div>

        {/* Right Column: Interactive Graphs & Solute Partitioning Matrix */}
        {!showNumbers ? (
          <>
          <div className="lg:col-span-8 p-6 rounded-2xl bg-[#090e18] border border-amber-500/30 text-xs text-amber-200 space-y-2" data-testid="calphad-no-result">
            <div className="font-bold text-sm">No equilibrium result</div>
            <div>
              {pythonUnavailable
                ? `${calphadUnavailableHeadline(pythonUnavailable)}. Phase fractions, Gibbs energies, partition coefficients and the Scheil path are not shown because no CALPHAD calculation was made.`
                : pythonRefused
                ? "The Python solver refused this input (see the message above); nothing was calculated."
                : isSolving
                ? "Waiting for the first pycalphad result for this input. No numbers are shown until it arrives."
                : "No pycalphad result for this input yet."}
            </div>
          </div>
          {pythonUnavailable && solveResult.literatureSolidification != null && (
            <LiteratureSolidificationCard literature={solveResult.literatureSolidification} />
          )}
          </>
        ) : (
        <div className="lg:col-span-8 space-y-4">
          {/* Sub-tab Switcher */}
          <div className="p-3 rounded-2xl bg-[#090e18] border border-[#1e2d46] flex flex-wrap items-center justify-between gap-2">
            <div className="flex p-1 bg-[#050810] rounded-xl border border-[#162032] flex-wrap gap-1 text-xs">
              <button
                type="button"
                onClick={() => setViewSubTab("phase_fractions")}
                aria-pressed={viewSubTab === "phase_fractions"}
                className={`px-3 py-1.5 rounded-lg font-bold transition flex items-center gap-1.5 ${
                  viewSubTab === "phase_fractions"
                    ? "bg-violet-500/20 text-violet-300 border border-violet-500/40 shadow-sm"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <TrendingUp className="w-3.5 h-3.5" />
                <span>Phase Fraction vs T</span>
              </button>
              <button
                type="button"
                onClick={() => setViewSubTab("gibbs_energy")}
                aria-pressed={viewSubTab === "gibbs_energy"}
                className={`px-3 py-1.5 rounded-lg font-bold transition flex items-center gap-1.5 ${
                  viewSubTab === "gibbs_energy"
                    ? "bg-violet-500/20 text-violet-300 border border-violet-500/40 shadow-sm"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <Zap className="w-3.5 h-3.5 text-amber-400" />
                <span>Gibbs Energy & Activities</span>
              </button>
              <button
                type="button"
                onClick={() => setViewSubTab("solute_partitioning")}
                aria-pressed={viewSubTab === "solute_partitioning"}
                className={`px-3 py-1.5 rounded-lg font-bold transition flex items-center gap-1.5 ${
                  viewSubTab === "solute_partitioning"
                    ? "bg-violet-500/20 text-violet-300 border border-violet-500/40 shadow-sm"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <Table className="w-3.5 h-3.5" />
                <span>Solute Partitioning (k_i)</span>
              </button>
              <button
                type="button"
                onClick={() => setViewSubTab("multi_scheil")}
                aria-pressed={viewSubTab === "multi_scheil"}
                className={`px-3 py-1.5 rounded-lg font-bold transition flex items-center gap-1.5 ${
                  viewSubTab === "multi_scheil"
                    ? "bg-violet-500/20 text-violet-300 border border-violet-500/40 shadow-sm"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <Flame className="w-3.5 h-3.5" />
                <span>Multi-Element Scheil</span>
              </button>
              <button
                type="button"
                onClick={() => setViewSubTab("tdb_editor")}
                aria-pressed={viewSubTab === "tdb_editor"}
                className={`px-3 py-1.5 rounded-lg font-bold transition flex items-center gap-1.5 ${
                  viewSubTab === "tdb_editor"
                    ? "bg-violet-500/20 text-violet-300 border border-violet-500/40 shadow-sm"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <FileCode className="w-3.5 h-3.5" />
                <span>TDB Code & Sublattices</span>
              </button>
            </div>

            {/* Probe Slider */}
            <div className="flex items-center gap-2 text-xs">
              <span className="text-slate-400">T Probe: <strong className="text-violet-300">{probeTemperatureC}°C</strong></span>
              <input aria-label="T Probe (°C)"
                type="range"
                min={tempWindow.tMin}
                max={tempWindow.tMax}
                step={tempWindow.tStep}
                value={probeTemperatureC}
                onChange={(e) => setProbeTemperatureC(parseInt(e.target.value, 10))}
                className="w-28 accent-violet-500"
              />
            </div>
          </div>

          {/* Subtab 1: Phase Fraction vs Temperature Chart */}
          {viewSubTab === "phase_fractions" && (
            <div className="p-4 rounded-2xl bg-[#090e18] border border-[#1e2d46] space-y-3">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-white flex items-center gap-2">
                  <Activity className="w-4 h-4 text-violet-400" />
                  <span>Equilibrium Phase Mole Fractions vs Temperature ({solveResult.temperatureRangeC[0]}°C – {solveResult.temperatureRangeC[1]}°C)</span>
                </span>
                <span className="text-[11px] text-slate-400 font-mono">
                  Minimization: min G(T, x_i)
                </span>
              </div>

              <div className="h-[340px] w-full pt-2">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={phaseChartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e2d46" />
                    <XAxis
                      dataKey="temperatureC"
                      stroke="#64748b"
                      tick={{ fill: "#94a3b8", fontSize: 11 }}
                      minTickGap={28}
                      tickFormatter={(value: number) => `${Math.round(value)}°C`}
                    />
                    <YAxis
                      stroke="#64748b"
                      tick={{ fill: "#94a3b8", fontSize: 11 }}
                      domain={[0, 100]}
                      ticks={[0, 25, 50, 75, 100]}
                      allowDataOverflow
                      tickFormatter={(value: number) => `${Math.round(value)}%`}
                      width={44}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#ffffff",
                        borderColor: "#d0d5dc",
                        borderRadius: "12px",
                        fontSize: "12px",
                        fontFamily: "monospace",
                      }}
                    />
                    <Legend />
                    {clippedGridTemps.length > 0 && (
                      <ReferenceArea x1={clippedGridTemps[0]} x2={clippedGridTemps[clippedGridTemps.length - 1]} fill="#64748b" fillOpacity={0.25} stroke="none" />
                    )}
                    <ReferenceLine x={probeTemperatureC} stroke="#ec4899" strokeDasharray="4 4" label={{ value: `${probeTemperatureC}°C`, fill: "#ec4899", fontSize: 11 }} />
                    {solveResult.criticalTemperatures?.liquidusC && (
                      <ReferenceLine
                        x={solveResult.criticalTemperatures.liquidusC}
                        stroke="#0284c7"
                        strokeDasharray="3 3"
                        label={{ value: `T_liq ${solveResult.criticalTemperatures.liquidusC}°C`, fill: "#38bdf8", fontSize: 10, position: "insideTopRight" }}
                      />
                    )}
                    {solveResult.criticalTemperatures?.solidusC && (
                      <ReferenceLine
                        x={solveResult.criticalTemperatures.solidusC}
                        stroke="#0284c7"
                        strokeDasharray="3 3"
                        label={{ value: `T_sol ${solveResult.criticalTemperatures.solidusC}°C`, fill: "#38bdf8", fontSize: 10, position: "insideTopLeft" }}
                      />
                    )}
                    {solveResult.criticalTemperatures?.gammaPrimeSolvusC && (
                      <ReferenceLine
                        x={solveResult.criticalTemperatures.gammaPrimeSolvusC}
                        stroke="#a855f7"
                        strokeDasharray="3 3"
                        label={{ value: `T_γ' ${solveResult.criticalTemperatures.gammaPrimeSolvusC}°C`, fill: "#c084fc", fontSize: 10, position: "insideTopRight" }}
                      />
                    )}

                    {allPhaseIds.map((phId, idx) => {
                      const colors = ["#10b981", "#8b5cf6", "#ec4899", "#f59e0b", "#38bdf8", "#ef4444", "#eab308"];
                      const color = colors[idx % colors.length];
                      return (
                        <Area
                          key={phId}
                          type="monotone"
                          dataKey={phId}
                          name={phId.replace("_", " ")}
                          stroke={color}
                          fill={color}
                          fillOpacity={0.4}
                          stackId="1"
                        />
                      );
                    })}
                  </AreaChart>
                </ResponsiveContainer>
              </div>

              {phaseFractionsClipped && (
                <p role="note" className="text-[11px] text-amber-200" data-testid="phase-fraction-scope-note">
                  {MC_TI_PHASE_FRACTION_NOTE}
                </p>
              )}

              {Object.keys(phaseNotes).length > 0 && (
                <p className="text-[10px] text-amber-200/90" data-testid="phase-name-notes">
                  {Object.keys(phaseNotes).join(", ")}: {Object.values(phaseNotes)[0]}.
                </p>
              )}

              {/* Probe Breakdown Bar */}
              <div className="pt-2 border-t border-[#162032] flex flex-wrap items-center justify-between gap-3 text-xs">
                <div className="flex items-center gap-2">
                  <span className="text-slate-400">At {currentEquilibriumPoint.temperatureC}°C (nearest grid point):</span>
                  {phaseFractionsClipped && currentEquilibriumPoint.temperatureC < MC_TI_PHASE_FRACTION_MIN_C ? (
                    <span className="text-[10px] text-amber-200" data-testid="phase-fraction-probe-clipped">{MC_TI_PHASE_FRACTION_NOTE}</span>
                  ) : phaseChipLabels(currentEquilibriumPoint.phases).map(({ key, label, fraction }) => (
                    <span key={key} className="px-2 py-0.5 rounded bg-violet-500/10 text-violet-300 font-bold border border-violet-500/20 text-[10px]">
                      {label}: {(fraction * 100).toFixed(1)}%
                    </span>
                  ))}
                </div>
                <span className="text-[11px] text-slate-400 font-mono">
                  G_total = {formatNullable(currentEquilibriumPoint.totalGibbsEnergy_kJ_mol, "kJ/mol")}
                </span>
              </div>
            </div>
          )}

          {/* Subtab: True Gibbs Minimizer & Activities */}
          {viewSubTab === "gibbs_energy" && (
            <div className="p-4 rounded-2xl bg-[#090e18] border border-[#1e2d46] space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
                <div>
                  <span className="font-bold text-white flex items-center gap-2">
                    <Zap className="w-4 h-4 text-amber-400" />
                    <span>{gibbsNumbers ? "CALPHAD Gibbs Free Energy & Solute Activities" : "Gibbs energy, chemical potentials & activities (pycalphad only)"}</span>
                  </span>
                  {gibbsNumbers && (
                    <p className="text-[11px] text-slate-400 mt-0.5 font-mono">
                      Model: <strong className="text-violet-300">{provenanceLabels.model}</strong>
                    </p>
                  )}
                </div>

                {/* Metric Selector Buttons */}
                {gibbsNumbers && (
                <div className="flex p-0.5 bg-[#050810] rounded-lg border border-[#162032] text-xs">
                  <button
                    type="button"
                    onClick={() => setActiveGibbsMetric("gibbs_free_energy")}
                    aria-pressed={activeGibbsMetric === "gibbs_free_energy"}
                    className={`px-2.5 py-1 rounded text-[11px] font-bold transition ${
                      activeGibbsMetric === "gibbs_free_energy"
                        ? "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    G_m (kJ/mol)
                  </button>
                  <button
                    type="button"
                    onClick={() => setActiveGibbsMetric("activities")}
                    aria-pressed={activeGibbsMetric === "activities"}
                    className={`px-2.5 py-1 rounded text-[11px] font-bold transition ${
                      activeGibbsMetric === "activities"
                        ? "bg-sky-500/20 text-sky-300 border border-sky-500/40"
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    Activities a_i
                  </button>
                  <button
                    type="button"
                    onClick={() => setActiveGibbsMetric("potentials")}
                    aria-pressed={activeGibbsMetric === "potentials"}
                    className={`px-2.5 py-1 rounded text-[11px] font-bold transition ${
                      activeGibbsMetric === "potentials"
                        ? "bg-purple-500/20 text-purple-300 border border-purple-500/40"
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    Chemical Potentials μ_i
                  </button>
                </div>
                )}
              </div>

              {!gibbsNumbers && (
                <div role="status" data-testid="gibbs-pycalphad-only" className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/40 text-amber-200 text-xs space-y-1">
                  {usePythonEngine && (
                    <div>{pythonUnavailable ? "No equilibrium result: the pycalphad calculation is unavailable for this input."
                      : pythonRefused ? "No equilibrium result: the Python solver refused the input."
                      : "No equilibrium result yet for this input."}</div>
                  )}
                  {!usePythonEngine && <div>Python HPC is switched off, so no pycalphad calculation was requested.</div>}
                  <div>Gibbs energy, chemical potentials and activities come only from pycalphad; the client screening model computes none.</div>
                </div>
              )}

              {gibbsNumbers && (<>
              {/* Chart Display Area */}
              <div className="h-[340px] w-full pt-1">
                <ResponsiveContainer width="100%" height="100%">
                  {activeGibbsMetric === "gibbs_free_energy" ? (
                    <LineChart data={gibbsChartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e2d46" />
                      <XAxis
                        dataKey="temperatureC"
                        stroke="#64748b"
                        tick={{ fill: "#94a3b8", fontSize: 11 }}
                        unit="°C"
                      />
                      <YAxis
                        stroke="#64748b"
                        tick={{ fill: "#94a3b8", fontSize: 11 }}
                        unit=" kJ/mol"
                        domain={["auto", "auto"]}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#050810",
                          borderColor: "#1e2d46",
                          borderRadius: "12px",
                          fontSize: "12px",
                          fontFamily: "monospace",
                        }}
                      />
                      <Legend />
                      <ReferenceLine
                        x={probeTemperatureC}
                        stroke="#ec4899"
                        strokeDasharray="4 4"
                        label={{ value: `${probeTemperatureC}°C`, fill: "#ec4899", fontSize: 11 }}
                      />
                      <Line
                        type="monotone"
                        dataKey="totalGibbsEnergy_kJ_mol"
                        name="Molar Gibbs Energy G_m(T)"
                        stroke="#f59e0b"
                        strokeWidth={2.5}
                        dot={false}
                      />
                    </LineChart>
                  ) : activeGibbsMetric === "activities" ? (
                    <LineChart data={gibbsChartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e2d46" />
                      <XAxis
                        dataKey="temperatureC"
                        stroke="#64748b"
                        tick={{ fill: "#94a3b8", fontSize: 11 }}
                        unit="°C"
                      />
                      <YAxis
                        stroke="#64748b"
                        tick={{ fill: "#94a3b8", fontSize: 11 }}
                        domain={[0, "auto"]}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#050810",
                          borderColor: "#1e2d46",
                          borderRadius: "12px",
                          fontSize: "12px",
                          fontFamily: "monospace",
                        }}
                      />
                      <Legend />
                      <ReferenceLine
                        x={probeTemperatureC}
                        stroke="#ec4899"
                        strokeDasharray="4 4"
                        label={{ value: `${probeTemperatureC}°C`, fill: "#ec4899", fontSize: 11 }}
                      />
                      {activeComponentsList.map((elem, idx) => {
                        const colors = ["#38bdf8", "#10b981", "#ec4899", "#8b5cf6", "#f59e0b", "#eab308", "#14b8a6"];
                        const color = colors[idx % colors.length];
                        return (
                          <Line
                            key={elem}
                            type="monotone"
                            dataKey={`act_${elem}`}
                            name={`Activity a_${elem}`}
                            stroke={color}
                            strokeWidth={2}
                            dot={false}
                          />
                        );
                      })}
                    </LineChart>
                  ) : (
                    <LineChart data={gibbsChartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e2d46" />
                      <XAxis
                        dataKey="temperatureC"
                        stroke="#64748b"
                        tick={{ fill: "#94a3b8", fontSize: 11 }}
                        unit="°C"
                      />
                      <YAxis
                        stroke="#64748b"
                        tick={{ fill: "#94a3b8", fontSize: 11 }}
                        unit=" kJ/mol"
                        domain={["auto", "auto"]}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#050810",
                          borderColor: "#1e2d46",
                          borderRadius: "12px",
                          fontSize: "12px",
                          fontFamily: "monospace",
                        }}
                      />
                      <Legend />
                      <ReferenceLine
                        x={probeTemperatureC}
                        stroke="#ec4899"
                        strokeDasharray="4 4"
                        label={{ value: `${probeTemperatureC}°C`, fill: "#ec4899", fontSize: 11 }}
                      />
                      {activeComponentsList.map((elem, idx) => {
                        const colors = ["#8b5cf6", "#38bdf8", "#10b981", "#ec4899", "#f59e0b", "#eab308", "#14b8a6"];
                        const color = colors[idx % colors.length];
                        return (
                          <Line
                            key={elem}
                            type="monotone"
                            dataKey={`mu_${elem}`}
                            name={`μ_${elem} (kJ/mol)`}
                            stroke={color}
                            strokeWidth={2}
                            dot={false}
                          />
                        );
                      })}
                    </LineChart>
                  )}
                </ResponsiveContainer>
              </div>

              {/* Probe Thermodynamic Activity & Chemical Potential Table */}
              <div className="pt-3 border-t border-[#162032] space-y-3">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-300">
                    Component Thermodynamic Activities & Potentials at <strong className="text-amber-300">{currentEquilibriumPoint.temperatureC}°C</strong> (nearest grid point):
                  </span>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-bold">
                    G_min = {formatNullable(currentEquilibriumPoint.totalGibbsEnergy_kJ_mol, "kJ/mol")}
                  </span>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 gap-2">
                  {activeComponentsList.map((elem) => {
                    const act = currentEquilibriumPoint.thermodynamicActivities?.[elem] ?? null;
                    const refState = solveResult.activityReferenceStates?.[elem];
                    const muText = formatChemicalPotentialKJ(currentEquilibriumPoint.chemicalPotentials_J_mol?.[elem]);
                    return (
                      <div
                        key={elem}
                        className="p-2.5 rounded-xl bg-[#050810] border border-[#162032] flex flex-col gap-1 text-[11px]"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-white text-xs">{elem}</span>
                          <span className="text-[10px] text-slate-500" title={refState?.definition ?? ""}>
                            Ref: pure {elem}{refState?.phase ? `, ${refState.phase}, same T` : ", no reference phase"}
                          </span>
                        </div>
                        {refState?.basis && (
                          <div className="text-[10px] text-slate-500" data-testid={`activity-basis-${elem}`}>
                            Basis: {refState.basis}
                          </div>
                        )}
                        {refState?.referenceSource && (
                          <div className="text-[10px] text-slate-500" data-testid={`activity-source-${elem}`}>
                            Reference: {refState.referenceSource}
                          </div>
                        )}
                        <div className="text-slate-400">
                          a_{elem} = <strong className="text-sky-300" title={act === null ? (refState?.reason ?? "") : ""}>{act === null ? "Unavailable" : act > 0 ? (act < 0.001 ? act.toExponential(2) : act.toFixed(4)) : "0.0000"}</strong>
                        </div>
                        <div className="text-slate-400">
                          μ_{elem} = <strong className="text-purple-300">{muText}</strong>
                        </div>
                      </div>
                    );
                  })}
                </div>

                {Object.values(solveResult.activityReferenceStates ?? {}).find((r) => r?.definition) && (
                  <p className="text-[11px] text-slate-400" data-testid="gibbs-reference-definition">
                    Activity reference: {Object.values(solveResult.activityReferenceStates ?? {}).find((r) => r?.definition)?.definition}{" "}
                    Chemical potentials μ_i are on the database SER scale.
                  </p>
                )}

                {/* Computational Rigor Callout */}
                <div className="p-3 rounded-xl bg-violet-950/20 border border-violet-500/30 flex items-start gap-2.5 text-xs">
                  <ShieldCheck className="w-4 h-4 text-emerald-400 mt-0.5 flex-shrink-0" />
                  <div className="space-y-1 text-slate-300">
                    <p className="font-bold text-white">
                      Provenance of these numbers:
                    </p>
                    <p className="text-[11px] text-slate-400 leading-relaxed">
                      Phase constitution, Gibbs energy, chemical potentials and activities come from a pycalphad Gibbs energy minimisation with the database named above (assessments only; test-fixture databases are refused). Liquidus and solidus are read off the temperature grid and are null when the grid cannot support them; the gamma-prime solvus is not stated because the L1_2 phase name does not prove ordering. The partition matrix and the Scheil-style curve are screening aids, flagged where they use default values.
                    </p>
                  </div>
                </div>
              </div>
              </>)}
            </div>
          )}

          {/* Subtab 2: Solute Partitioning */}
          {viewSubTab === "solute_partitioning" && (
            <div className="p-4 rounded-2xl bg-[#090e18] border border-[#1e2d46] space-y-3">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-white flex items-center gap-2">
                  <Table className="w-4 h-4 text-purple-400" />
                  <span>
                    {provenanceLabels.isPycalphad
                      ? "Solid/liquid partition coefficients k_i = x_i(primary solid) / x_i(liquid)"
                      : "Partition table of the client screening model (not CALPHAD)"}
                  </span>
                </span>
              </div>
              {provenanceLabels.isPycalphad && (
                <p className="text-[11px] text-slate-400" data-testid="partition-definition">
                  From the equilibrium tie-line between the majority solid phase of the Scheil-Gulliver path and the liquid,
                  at the temperature where that phase first forms (mole fractions). Calculated, not validated against experiment.
                </p>
              )}

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse font-mono">
                  <thead>
                    <tr className="border-b border-[#162032] text-slate-400 text-[10px] uppercase">
                      <th className="pb-2">Element</th>
                      <th className="pb-2 text-right">Partition k_i</th>
                      <th className="pb-2 text-right">Primary solid / T</th>
                      <th className="pb-2 text-right">Meaning</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#162032]/60">
                    {solveResult.solutePartitioning.map((sp) => (
                      <tr key={sp.element} className="hover:bg-white/[0.02]">
                        <td className="py-2.5 font-bold text-white">{sp.element}</td>
                        <td className="py-2.5 text-right" title={sp.partitionCoefficient_k == null ? sp.reason ?? "" : ""}>
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              sp.partitionCoefficient_k == null
                                ? "bg-slate-800 text-slate-400 border border-slate-700"
                                : sp.partitionCoefficient_k > 1.0
                                ? "bg-purple-500/20 text-purple-300 border border-purple-500/40"
                                : "bg-blue-500/20 text-blue-300 border border-blue-500/40"
                            }`}
                          >
                            {formatPartitionK(sp.partitionCoefficient_k)}
                          </span>
                        </td>
                        <td className="py-2.5 text-right text-slate-300">
                          {sp.primarySolidPhase
                            ? `${withOrderingNote(sp.primarySolidPhase, phaseNotes, scheilBlock?.phaseNameNotes)}${typeof sp.temperatureC === "number" ? ` at ${sp.temperatureC} °C` : ""}`
                            : "n/a"}
                        </td>
                        <td className="py-2.5 text-right text-[11px] text-slate-400">
                          {sp.role ?? sp.reason ?? ""}
                          {!provenanceLabels.isPycalphad && (
                            <span className="block text-amber-300">screening value, not CALPHAD</span>
                          )}
                          {partitionSourceNote(sp.partitionCoefficientSource) && (
                            <span className="block text-amber-300">{partitionSourceNote(sp.partitionCoefficientSource)}</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Subtab 3: Scheil-Gulliver solidification path */}
          {viewSubTab === "multi_scheil" && (
            <div className="p-4 rounded-2xl bg-[#090e18] border border-[#1e2d46] space-y-3">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-white flex items-center gap-2">
                  <Flame className="w-4 h-4 text-amber-400" />
                  <span>
                    {provenanceLabels.isPycalphad
                      ? "Scheil-Gulliver solidification path (pycalphad equilibria of the remaining liquid)"
                      : "Solidification screening curve of the client model (not a CALPHAD Scheil calculation)"}
                  </span>
                </span>
                <span className="text-[11px] text-slate-400 font-mono">
                  Equilibrium freezing range ΔT = {formatFreezingRange(solveResult.criticalTemperatures.freezingRangeC)}
                </span>
              </div>

              {solveResult.multiElementScheilNote && (
                <p className="text-[11px] text-slate-400" data-testid="scheil-note">{solveResult.multiElementScheilNote}</p>
              )}
              {provenanceLabels.isPycalphad && scheilBlock && (
                <div data-testid="scheil-summary" className={`p-3 rounded-xl text-xs space-y-0.5 border ${
                  scheilBlock.status === SCHEIL_COMPUTED ? "bg-[#050810] border-[#162032] text-slate-300" : "bg-amber-500/10 border-amber-500/40 text-amber-200"
                }`}>
                  {scheilSummaryLines(scheilBlock).map((line) => (
                    <div key={line}>{line}</div>
                  ))}
                  {scheilBlock.validity && <div className="text-slate-400">Validity: {scheilBlock.validity}</div>}
                  {(solveResult.knownDeviations ?? []).flatMap((d) => d.notes ?? []).length > 0 && (
                    <div className="mt-1 pt-1 border-t border-amber-500/30 text-amber-200" data-testid="scheil-known-deviations">
                      <div className="font-semibold">Known deviations for this alloy and database (not corrected):</div>
                      <ul className="list-disc pl-4">
                        {(solveResult.knownDeviations ?? []).flatMap((d) => d.notes ?? []).map((note) => (
                          <li key={note}>{note}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  <div className="text-amber-300">Evidence: {scheilBlock.evidence ?? "unvalidated"} (calculated path, no experimental comparison here)</div>
                </div>
              )}
              {provenanceLabels.isPycalphad && showNumbers && scheilBlock?.status === "unavailable" && scheilBlock.reason === "not requested" && (
                <div className="p-3 rounded-xl bg-[#050810] border border-[#162032] text-xs space-y-2" data-testid="scheil-compute">
                  <div className="text-slate-300">The Scheil-Gulliver path was not requested for this input; it is the slowest part of the calculation and is computed on demand. It also switches liquidus/solidus refinement on, because the path needs a bisected liquidus.</div>
                  <button
                    type="button"
                    disabled={isSolving}
                    onClick={() => {
                      setBoundaryRefinement(true);
                      setScheilRequestedFor(scheilScopeKey);
                    }}
                    className="px-3 py-1.5 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/40 text-amber-200 font-semibold transition disabled:opacity-50"
                  >
                    Compute Scheil path (about 1.5 to 2 min)
                  </button>
                </div>
              )}
              {!provenanceLabels.isPycalphad && solveResult.multiElementScheil.every((pt) => pt.temperatureC == null) && (
                <div role="status" className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/40 text-amber-200 text-xs space-y-1" data-testid="scheil-unavailable">
                  <div>No temperature axis: the screening curve needs both the liquidus and the solidus.</div>
                  {(["liquidusC", "solidusC"] as const).map((key) =>
                    solveResult.criticalTemperatures[key] == null ? (
                      <div key={key}>{key === "liquidusC" ? "Liquidus" : "Solidus"} unavailable: {criticalStatus[key]?.reason ?? "no reason reported"}</div>
                    ) : null,
                  )}
                </div>
              )}

              {(scheilComputed || !provenanceLabels.isPycalphad) && solveResult.multiElementScheil.some((pt) => pt.temperatureC != null) && (
                <div className="h-[320px] w-full pt-2">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e2d46" />
                      <XAxis
                        dataKey="fractionSolid"
                        type="number"
                        domain={[0, 1]}
                        stroke="#64748b"
                        tick={{ fill: "#94a3b8", fontSize: 11 }}
                        unit=" (f_S)"
                      />
                      <YAxis
                        dataKey="temperatureC"
                        type="number"
                        domain={["auto", "auto"]}
                        stroke="#64748b"
                        tick={{ fill: "#94a3b8", fontSize: 11 }}
                        unit="°C"
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#050810",
                          borderColor: "#1e2d46",
                          borderRadius: "12px",
                          fontSize: "12px",
                          fontFamily: "monospace",
                        }}
                      />
                      <Legend />
                      <Line
                        data={solveResult.multiElementScheil.filter((pt) => pt.temperatureC != null)}
                        type="linear"
                        dataKey="temperatureC"
                        name={provenanceLabels.isPycalphad ? "Scheil-Gulliver (no solid diffusion)" : "Screening curve (client model)"}
                        stroke="#f59e0b"
                        strokeWidth={2.5}
                        dot={false}
                      />
                      {provenanceLabels.isPycalphad && equilibriumSolidCurve.length > 1 && (
                        <Line
                          data={equilibriumSolidCurve}
                          type="linear"
                          dataKey="temperatureC"
                          name="Equilibrium fraction solid (grid points and refined liquidus/solidus; markers only, not interpolated)"
                          stroke="none"
                          isAnimationActive={false}
                          dot={{ r: 3, fill: "#38bdf8", stroke: "#38bdf8" }}
                        />
                      )}
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>
          )}

          {/* Subtab 4: Real TDB Code & Constituent Sublattice Editor */}
          {viewSubTab === "tdb_editor" && (
            <div className="p-4 rounded-2xl bg-[#090e18] border border-[#1e2d46] space-y-3">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-white flex items-center gap-2">
                  <FileCode className="w-4 h-4 text-violet-400" />
                  <span>OpenCALPHAD Thermodynamic Database (.TDB) Script</span>
                </span>
                <span className="text-[11px] text-slate-400 font-mono">
                  {parsedTdb.phases.size} Phases | {parsedTdb.elements.size} Elements | {parsedTdb.parameters.length} Parameters
                </span>
              </div>

              <textarea aria-label="OpenCALPHAD Thermodynamic Database (.TDB) Script"
                value={activeTdbContent}
                onChange={(e) => setActiveTdbContent(e.target.value)}
                className="w-full h-[320px] bg-[#050810] border border-[#162032] rounded-xl p-3 text-xs text-violet-300 font-mono focus:outline-none focus:border-violet-500 resize-none leading-relaxed"
                spellCheck={false}
              />
            </div>
          )}

          {usePythonEngine && provenanceLabels.isPycalphad && solveResult.literatureSolidification != null && (
            <LiteratureSolidificationCard literature={solveResult.literatureSolidification} alongsideCalphad />
          )}
        </div>
        )}
      </div>
    </div>
  );
};
