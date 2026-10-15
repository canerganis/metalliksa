import { useWorkspaceVisible } from '../WorkspaceVisibility';
import { useDebouncedLatestTask } from "../../hooks/useDebouncedLatestTask";
import { buildSlicerPayload, slicerRequestSignature } from "../../utils/slicerRequest";
import { inferSlicerPreset } from "../../utils/lpbfIndustrialDecision";
import { canonicalLpbfMaterialName, isSupportedSlicerMaterial } from "../../utils/lpbfMaterialIdentity";
import React, { useState, useEffect, useRef, useMemo, useCallback } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { PhysicalSlicerViewport } from "./PhysicalSlicerViewport";
import {
  Layers,
  Box,
  Clock,
  Zap,
  Activity,
  Sliders,
  Play,
  Pause,
  RotateCcw,
  Upload,
  Download,
  Trash2,
  ChevronRight,
  TrendingUp,
  Flame,
  FileSpreadsheet,
  FileText,
  Sparkles,
  Maximize2,
  Eye,
  EyeOff,
  Compass,
  BarChart3,
  ListOrdered,
  Cpu,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  RefreshCw,
  Gauge,
  Scissors,
  Terminal,
  Code2,
  Copy,
  Check,
} from "lucide-react";
import {
  parseSTL,
  parseSTLAsync,
  createRocketNozzleGeometry,
  createTurbineBladeGeometry,
  createAerospaceBracketGeometry,
  createLatticeGyroidGeometry,
  createHipImplantGeometry,
  sliceGeometryAtHeight,
  calculateMeshMetrics,
  calculateExactCrossSectionalArea,
  sliceGeometryStack,
  exportGeometryAsSTL,
  LayerSliceData,
  FullStackSliceInfo,
} from "../../utils/stlParser";
import { useMaterialSpecimenStore } from "../../store/useMaterialSpecimenStore";
import { ruleOfMixturesDensity } from "../../utils/compositionPropertyAvailability";
import { useLpbfBuildMeshStore } from "../../store/useLpbfBuildMeshStore";
import { bufferGeometryToSlicerTriangles } from "../../physics/lpbfBuildMesh";

export interface BasicSTLSlicerLabProps {
  initialPower_W?: number;
  initialSpeed_mms?: number;
  initialLayer_um?: number;
  initialHatch_um?: number;
  initialMaterial?: string;
  onApplyParametersToLPBF?: (params: {
    laserPower_W: number;
    scanSpeed_mms: number;
    layerThickness_um: number;
    hatchSpacing_um: number;
  }) => void;
}

const MATERIAL_DENSITY_MAP: Record<string, { name: string; density_gcm3: number; thermal_k: number }> = {
  "Inconel 718": { name: "Inconel 718 (AMS 5662)", density_gcm3: 8.19, thermal_k: 11.4 },
  "Ti-6Al-4V ELI": { name: "Ti-6Al-4V ELI Grade 23", density_gcm3: 4.43, thermal_k: 6.7 },
  "SS 316L": { name: "316L Stainless Steel", density_gcm3: 7.99, thermal_k: 16.3 },
  AlSi10Mg: { name: "AlSi10Mg Aluminum", density_gcm3: 2.68, thermal_k: 113.0 },
  CoCrMo: { name: "CoCrMo Biomedical", density_gcm3: 8.30, thermal_k: 14.8 },
  "Scalmalloy": { name: "Scalmalloy (Al-Mg-Sc)", density_gcm3: 2.67, thermal_k: 95.0 },
};

export const BasicSTLSlicerLab: React.FC<BasicSTLSlicerLabProps> = ({
  initialPower_W = 285,
  initialSpeed_mms = 960,
  initialLayer_um = 40,
  initialHatch_um = 110,
  initialMaterial = "Inconel 718",
  onApplyParametersToLPBF,
}) => {
  const workspaceVisible = useWorkspaceVisible();
  // CAD and process use the same session/specimen context as the build job.
  const sharedSpecimen = useMaterialSpecimenStore(s => s.activeSpecimen);
  const liveMesh = useLpbfBuildMeshStore(s => s.mesh);
  const selectedPreset = liveMesh ? "custom" : inferSlicerPreset(sharedSpecimen.lpbf.cadAssetName);
  const uploadedFileName = liveMesh?.name ?? null;
  const customGeometry = useMemo(() => {
    if (!liveMesh) return null;
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.Float32BufferAttribute(liveMesh.triangles.flat(2), 3));
    geometry.computeVertexNormals();
    return geometry;
  }, [liveMesh]);
  useEffect(() => () => customGeometry?.dispose(), [customGeometry]);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Material & LPBF Machine Parameters
  const loadSharedPreset = useMaterialSpecimenStore(s => s.loadPreset);
  const selectedMaterial = canonicalLpbfMaterialName(sharedSpecimen.name);
  // Non-catalogue specimens: density from the shown composition (inverse rule of mixtures) or unavailable. The store's
  // density_gcm3 carries an internal 8.0 g/cm³ per-element fallback for LPBF inputs and is not used for display.
  const specimenDensity = ruleOfMixturesDensity(sharedSpecimen.composition, sharedSpecimen.unit);
  const matInfo: { name: string; density_gcm3: number | null; thermal_k: number } = MATERIAL_DENSITY_MAP[selectedMaterial] || MATERIAL_DENSITY_MAP[selectedMaterial === "Ti-6Al-4V" ? "Ti-6Al-4V ELI" : selectedMaterial === "316L Stainless Steel" ? "SS 316L" : ""] || {name: selectedMaterial, density_gcm3: specimenDensity.density_gcm3, thermal_k: sharedSpecimen.lpbf.thermalConductivity_k_WmK};
  const densityUnavailableNote = matInfo.density_gcm3 === null ? specimenDensity.note : null;
  const laserPower_W = sharedSpecimen.lpbf.laserPower_W;
  const scanSpeed_mms = sharedSpecimen.lpbf.scanSpeed_mms;
  const layerThickness_um = sharedSpecimen.lpbf.layer_um;
  const hatchSpacing_um = sharedSpecimen.lpbf.hatch_um;
  const [recoatTimePerLayer_s, setRecoatTimePerLayer_s] = useState<number>(9.5);
  const [hatchStrategy, setHatchStrategy] = useState<"meander_67" | "meander_90" | "unidirectional" | "cross_0_90">("meander_67");
  const [contourSkinPasses, setContourSkinPasses] = useState<number>(2);
  const updateLpbfProcess = useMaterialSpecimenStore((s) => s.updateLpbfProcess);
  const setFromGeometry = useLpbfBuildMeshStore((s) => s.setFromGeometry);
  const clearLiveMesh = useLpbfBuildMeshStore((s) => s.clearMesh);

  // Slicer Interactive Scrubbing State
  const [activeLayerIndex, setActiveLayerIndex] = useState<number>(1);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1); // 0.5x, 1x, 2x, 5x
  const [viewMode, setViewMode] = useState<"2d_slicer" | "area_distribution" | "slice_table" | "3d_wire_preview" | "python_solver">("2d_slicer");

  // Python HPC Solver State
  const [isPythonLoading, setIsPythonLoading] = useState<boolean>(false);
  const [pythonExecutionData, setPythonExecutionData] = useState<any | null>(null);
  const [pythonExecutionDurationMs, setPythonExecutionDurationMs] = useState<number | null>(null);
  const [pythonError, setPythonError] = useState<string | null>(null);
  const pythonRequestSeq = useRef(0);
  const [pythonSubTab, setPythonSubTab] = useState<"script_code" | "live_output" | "cli_guide">("script_code");
  const [copiedCode, setCopiedCode] = useState<boolean>(false);

  // 2D Visualizer Display Options
  const [showHatchVectors, setShowHatchVectors] = useState<boolean>(true);
  const [showContourPoints, setShowContourPoints] = useState<boolean>(false);
  const [showBoundingBox, setShowBoundingBox] = useState<boolean>(true);
  const [showRecoaterAxis, setShowRecoaterAxis] = useState<boolean>(true);
  const [fillPolygons, setFillPolygons] = useState<boolean>(true);
  const [zoomLevel, setZoomLevel] = useState<number>(1.0);

  // Canvas Refs
  const canvas2DRef = useRef<HTMLCanvasElement>(null);
  const threePreviewMountRef = useRef<HTMLDivElement>(null);

  // 1. Generate / Retrieve 3D Geometry
  const geometry = useMemo(() => {
    let geom: THREE.BufferGeometry;
    if (selectedPreset === "custom" && customGeometry) {
      geom = customGeometry.clone();
    } else if (selectedPreset === "turbine") {
      geom = createTurbineBladeGeometry();
    } else if (selectedPreset === "nozzle") {
      geom = createRocketNozzleGeometry();
    } else if (selectedPreset === "gyroid") {
      geom = createLatticeGyroidGeometry();
    } else if (selectedPreset === "hip_implant") {
      geom = createHipImplantGeometry();
    } else {
      geom = createAerospaceBracketGeometry();
    }
    geom.computeVertexNormals();
    geom.computeBoundingBox();
    return geom;
  }, [selectedPreset, customGeometry]);

  // Mesh Physical Metrics
  const meshMetrics = useMemo(() => {
    return calculateMeshMetrics(geometry);
  }, [geometry]);

  // Compute Full Multi-Layer Stack
  const stackSummary = useMemo(() => {
    return sliceGeometryStack(
      geometry,
      layerThickness_um,
      laserPower_W,
      scanSpeed_mms,
      hatchSpacing_um,
      recoatTimePerLayer_s,
      120 // Max sample layers for real-time responsiveness
    );
  }, [geometry, layerThickness_um, laserPower_W, scanSpeed_mms, hatchSpacing_um, recoatTimePerLayer_s]);

  // Ensure active layer is within bounds
  useEffect(() => {
    if (activeLayerIndex > stackSummary.totalLayers) {
      setActiveLayerIndex(Math.max(1, stackSummary.totalLayers));
    }
  }, [stackSummary.totalLayers, activeLayerIndex]);

  // Current Layer Height Z (mm) in geometry coordinate space
  const currentLayerZ = useMemo(() => {
    const box = geometry.boundingBox || new THREE.Box3();
    const minY = box.min.y;
    const maxY = box.max.y;
    const height = Math.max(0.1, maxY - minY);
    const fraction = Math.min(1.0, Math.max(0.0, (activeLayerIndex - 1) / Math.max(1, stackSummary.totalLayers - 1)));
    return minY + fraction * height;
  }, [geometry, activeLayerIndex, stackSummary.totalLayers]);

  // Sliced Geometry at Active Height Z
  const activeSlice: LayerSliceData = useMemo(() => {
    return sliceGeometryAtHeight(geometry, currentLayerZ);
  }, [geometry, currentLayerZ]);

  // Exact Area & Loops for Active Layer
  const activeExactArea = useMemo(() => {
    const exact = calculateExactCrossSectionalArea(activeSlice.segments);
    return exact.area_mm2 > 0 ? exact.area_mm2 : activeSlice.estimatedArea_mm2;
  }, [activeSlice]);

  // Active Layer Telemetry Metrics
  const activeLayerTelemetry = useMemo(() => {
    const area = activeExactArea;
    const perimeter = activeSlice.estimatedPerimeter_mm;
    const hatch_mm = hatchSpacing_um * 1e-3;
    const tLayer_mm = layerThickness_um * 1e-3;

    const hatchLength_mm = area / Math.max(0.01, hatch_mm);
    const hatchCount = Math.round(Math.sqrt(area) / Math.max(0.01, hatch_mm));
    const hatchTime_s = hatchLength_mm / Math.max(10, scanSpeed_mms);
    const contourTime_s = (perimeter * contourSkinPasses) / Math.max(10, scanSpeed_mms * 0.7);
    const laserTime_s = hatchTime_s + contourTime_s + hatchCount * 0.0008;

    const ved = laserPower_W / (scanSpeed_mms * hatch_mm * tLayer_mm);
    const aed = laserPower_W / (scanSpeed_mms * hatch_mm);
    const led = laserPower_W / scanSpeed_mms;
    const scanDensity = 1.0 / hatch_mm;

    const estMass_g = matInfo.density_gcm3 === null ? null : stackSummary.totalEstimatedSolidVolume_cm3 * matInfo.density_gcm3;

    return {
      area_mm2: Math.round(area * 10) / 10,
      perimeter_mm: Math.round(perimeter * 10) / 10,
      hatchLength_m: Math.round((hatchLength_mm / 1000) * 100) / 100,
      hatchCount,
      scanDensity_mm_per_mm2: Math.round(scanDensity * 10) / 10,
      laserTime_s: Math.round(laserTime_s * 100) / 100,
      recoatTime_s: recoatTimePerLayer_s,
      totalLayerTime_s: Math.round((laserTime_s + recoatTimePerLayer_s) * 100) / 100,
      ved_J_mm3: Math.round(ved * 10) / 10,
      aed_J_mm2: Math.round(aed * 10) / 10,
      led_J_mm: Math.round(led * 100) / 100,
      estPartMass_g: estMass_g === null ? null : Math.round(estMass_g * 10) / 10,
    };
  }, [
    activeExactArea,
    activeSlice,
    hatchSpacing_um,
    layerThickness_um,
    scanSpeed_mms,
    laserPower_W,
    contourSkinPasses,
    recoatTimePerLayer_s,
    stackSummary.totalEstimatedSolidVolume_cm3,
    matInfo,
  ]);

  // Handle STL File Drag & Drop / Upload
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadError(null);


    const reader = new FileReader();
    reader.onload = async (event) => {
      try {
        const buffer = event.target?.result as ArrayBuffer;
        const geom = await parseSTLAsync(buffer);
        if (!geom || geom.attributes.position.count === 0) {
          throw new Error("Empty or invalid STL mesh data.");
        }
        setFromGeometry(file.name, geom);
        geom.dispose();
        updateLpbfProcess({ cadAssetName: file.name });
        setActiveLayerIndex(1);
      } catch (err: any) {
        setUploadError(`Failed to load STL: ${err.message}`);
      }
    };
    reader.onerror = () => setUploadError("Failed to read uploaded file.");
    reader.readAsArrayBuffer(file);
  };

  const handleClearUploadedSTL = () => {

    setActiveLayerIndex(1);
    clearLiveMesh();
    updateLpbfProcess({ cadAssetName: "bracket-demo" });
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  // Run CPython 3.10+ Slicer & LPBF Build Time Solver
  const runPythonSlicer = useCallback(async (signal?: AbortSignal): Promise<boolean> => {
    const requestSeq = ++pythonRequestSeq.current;
    setPythonExecutionData(null);
    setIsPythonLoading(true);
    setPythonError(null);
    const startTime = performance.now();

    try {
      if ([laserPower_W,scanSpeed_mms,layerThickness_um,hatchSpacing_um].some(value=>!Number.isFinite(value)||value<=0)) throw new Error("Slicer requires finite positive process inputs.");
      if (!isSupportedSlicerMaterial(selectedMaterial)) throw new Error(`No verified slicer material mapping for ${selectedMaterial}. Select a supported shared preset; no surrogate alloy was submitted.`);
      // If custom mesh, extract triangle vertices
      let customTriangles: number[][][] | null = null;
      if (selectedPreset === "custom" && customGeometry) {
        const extracted = bufferGeometryToSlicerTriangles(customGeometry);
        customTriangles = extracted.triangles.length > 0 ? extracted.triangles : null;
      }

      const payload = buildSlicerPayload({
        preset: selectedPreset,
        material: selectedMaterial,
        laserPower_W,
        scanSpeed_mms,
        layerThickness_um,
        hatchSpacing_um,
        recoatTimePerLayer_s,
        hatchStrategy,
        customTriangles,
        cadAssetName: uploadedFileName || "",
        triangleCountNative: liveMesh?.nativeTriangleCount,
      });

      const res = await fetch("/api/python/stl-slicer-build-time", {
        signal: signal ? AbortSignal.any([signal, AbortSignal.timeout(25000)]) : AbortSignal.timeout(25000),
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errText = await res.text();
        throw new Error(`Python solver error (${res.status}): ${errText}`);
      }

      const result = await res.json();
      if (signal?.aborted || pythonRequestSeq.current !== requestSeq) return false;
      const elapsed = Math.round(performance.now() - startTime);
      setPythonExecutionData(result);
      setPythonExecutionDurationMs(result.pythonDurationMs || elapsed);
      return true;
    } catch (err: any) {
      if (signal?.aborted || pythonRequestSeq.current !== requestSeq) return false;
      console.warn("Python execution warning:", err);
      setPythonError(err.message || "Failed to execute Python slicer solver");
      return false;
    } finally {
      if (pythonRequestSeq.current === requestSeq) setIsPythonLoading(false);
    }
  }, [
    selectedPreset,
    selectedMaterial,
    laserPower_W,
    scanSpeed_mms,
    layerThickness_um,
    hatchSpacing_um,
    recoatTimePerLayer_s,
    hatchStrategy,
    customGeometry,
    uploadedFileName,
    liveMesh?.nativeTriangleCount,
  ]);

  // Debounce process edits; a superseded response cannot overwrite the current geometry/process.
  // The solve is skipped while hidden, aborted when superseded/hidden, and not repeated for an unchanged input.
  const slicerInputSignature = slicerRequestSignature({ preset: selectedPreset, material: selectedMaterial, laserPower_W, scanSpeed_mms, layerThickness_um, hatchSpacing_um, recoatTimePerLayer_s, hatchStrategy, cadAssetName: uploadedFileName || "", triangleCountNative: liveMesh?.nativeTriangleCount, geometryId: customGeometry?.uuid ?? null });
  useEffect(() => {
    setPythonExecutionData(null);
    pythonRequestSeq.current += 1;
  }, [slicerInputSignature]);
  const { runNow: runPythonSlicerNow } = useDebouncedLatestTask(slicerInputSignature, (_signature, signal) => runPythonSlicer(signal), 280);

  // Auto-play Layer Scrubber Animation
  useEffect(() => {
    if (!workspaceVisible || !isPlaying) return;
    const intervalMs = Math.max(25, 120 / playbackSpeed);
    const timer = setInterval(() => {
      setActiveLayerIndex((prev) => {
        if (prev >= stackSummary.totalLayers) {
          return 1;
        }
        return prev + 1;
      });
    }, intervalMs);
    return () => clearInterval(timer);
  }, [workspaceVisible, isPlaying, playbackSpeed, stackSummary.totalLayers]);

  // -------------------------------------------------------------------------
  // 2D High-Precision Slice Canvas Renderer
  // -------------------------------------------------------------------------
  useEffect(() => {
    if (!workspaceVisible || viewMode !== "2d_slicer" || !canvas2DRef.current) return;
    const canvas = canvas2DRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;
    ctx.clearRect(0, 0, width, height);

    // Dark Engineering Blueprint Grid
    ctx.fillStyle = "#050811";
    ctx.fillRect(0, 0, width, height);

    ctx.strokeStyle = "#10192a";
    ctx.lineWidth = 1;
    for (let x = 0; x < width; x += 25) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }
    for (let y = 0; y < height; y += 25) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }

    // Origin Crosshair
    ctx.strokeStyle = "#1e2d46";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(width / 2, 0);
    ctx.lineTo(width / 2, height);
    ctx.moveTo(0, height / 2);
    ctx.lineTo(width, height / 2);
    ctx.stroke();

    const segments = activeSlice.segments;
    if (segments.length === 0) {
      ctx.fillStyle = "#64748b";
      ctx.font = "13px Fira Code, monospace";
      ctx.textAlign = "center";
      ctx.fillText(
        `No cross-sectional geometry intersection at Z = ${currentLayerZ.toFixed(2)} mm (Layer ${activeLayerIndex}/${stackSummary.totalLayers})`,
        width / 2,
        height / 2
      );
      return;
    }

    // Scale and Center 2D Geometry
    const maxBound = Math.max(30, Math.max(meshMetrics.sizeX_mm, meshMetrics.sizeZ_mm) * 1.35);
    const baseScale = Math.min(width, height) / maxBound;
    const scale = baseScale * zoomLevel;
    const cx = width / 2;
    const cy = height / 2;

    // 1. Draw Laser Hatching Vectors (Raster lines)
    if (showHatchVectors) {
      ctx.strokeStyle = "#0284c766";
      ctx.lineWidth = 1.2;

      // Compute rotation angle based on hatch strategy
      let hatchAngleRad = 0;
      if (hatchStrategy === "meander_67") {
        hatchAngleRad = (activeLayerIndex * 67 * Math.PI) / 180;
      } else if (hatchStrategy === "meander_90") {
        hatchAngleRad = ((activeLayerIndex % 2) * 90 * Math.PI) / 180;
      } else if (hatchStrategy === "cross_0_90") {
        hatchAngleRad = (activeLayerIndex * 45 * Math.PI) / 180;
      }

      const cosA = Math.cos(hatchAngleRad);
      const sinA = Math.sin(hatchAngleRad);
      const span = Math.max(meshMetrics.sizeX_mm, meshMetrics.sizeZ_mm) * 1.3;
      const step_mm = Math.max(0.05, hatchSpacing_um * 1e-3);

      for (let d = -span; d <= span; d += step_mm * 1.5) {
        const p1x = cx + (-span * sinA + d * cosA) * scale;
        const p1y = cy + (span * cosA + d * sinA) * scale;
        const p2x = cx + (span * sinA + d * cosA) * scale;
        const p2y = cy + (-span * cosA + d * sinA) * scale;

        ctx.beginPath();
        ctx.moveTo(p1x, p1y);
        ctx.lineTo(p2x, p2y);
        ctx.stroke();
      }
    }

    // 2. Draw Solid Filled Polygon Loops (if available)
    if (fillPolygons) {
      const { loops } = calculateExactCrossSectionalArea(segments);
      if (loops.length > 0) {
        ctx.fillStyle = "rgba(6, 182, 212, 0.12)";
        for (const loop of loops) {
          if (loop.length < 3) continue;
          ctx.beginPath();
          ctx.moveTo(cx + loop[0][0] * scale, cy + loop[0][1] * scale);
          for (let i = 1; i < loop.length; i++) {
            ctx.lineTo(cx + loop[i][0] * scale, cy + loop[i][1] * scale);
          }
          ctx.closePath();
          ctx.fill();
        }
      }
    }

    // 3. Draw Sliced Outer Contour Segments
    ctx.strokeStyle = "#38bdf8";
    ctx.lineWidth = 2.4;
    ctx.shadowColor = "#06b6d4";
    ctx.shadowBlur = 9;

    for (const seg of segments) {
      const x1 = cx + seg.p1[0] * scale;
      const y1 = cy + seg.p1[1] * scale;
      const x2 = cx + seg.p2[0] * scale;
      const y2 = cy + seg.p2[1] * scale;

      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.stroke();

      if (showContourPoints) {
        ctx.fillStyle = "#38bdf8";
        ctx.fillRect(x1 - 2, y1 - 2, 4, 4);
        ctx.fillRect(x2 - 2, y2 - 2, 4, 4);
      }
    }
    ctx.shadowBlur = 0;

    // 4. Draw Slice Bounding Box
    if (showBoundingBox && activeSlice.boundingBox) {
      const bb = activeSlice.boundingBox;
      const bx1 = cx + bb.minX * scale;
      const by1 = cy + bb.minY * scale;
      const bw = (bb.maxX - bb.minX) * scale;
      const bh = (bb.maxY - bb.minY) * scale;

      ctx.strokeStyle = "#f59e0b55";
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);
      ctx.strokeRect(bx1, by1, bw, bh);
      ctx.setLineDash([]);

      ctx.fillStyle = "#f59e0b";
      ctx.font = "9px Fira Code, monospace";
      ctx.fillText(
        `ΔX: ${(bb.maxX - bb.minX).toFixed(1)} mm × ΔY: ${(bb.maxY - bb.minY).toFixed(1)} mm`,
        bx1,
        by1 - 4
      );
    }

    // 5. Draw Recoater Blade Direction
    if (showRecoaterAxis) {
      ctx.strokeStyle = "#10b98188";
      ctx.lineWidth = 1.5;
      ctx.setLineDash([5, 4]);
      ctx.beginPath();
      ctx.moveTo(25, 30);
      ctx.lineTo(width - 25, 30);
      ctx.stroke();
      ctx.setLineDash([]);

      ctx.fillStyle = "#10b981";
      ctx.font = "10px Fira Code, monospace";
      ctx.fillText("⮞ Recoater Wiper Blade Sweep Axis (+X)", 30, 24);
    }

    // Scale Bar in Bottom Left
    const barLength_mm = 10;
    const barLength_px = barLength_mm * scale;
    ctx.strokeStyle = "#94a3b8";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(25, height - 25);
    ctx.lineTo(25 + barLength_px, height - 25);
    ctx.moveTo(25, height - 30);
    ctx.lineTo(25, height - 20);
    ctx.moveTo(25 + barLength_px, height - 30);
    ctx.lineTo(25 + barLength_px, height - 20);
    ctx.stroke();

    ctx.fillStyle = "#94a3b8";
    ctx.font = "9px Fira Code, monospace";
    ctx.fillText(`${barLength_mm} mm`, 25 + barLength_px / 2 - 12, height - 12);
  }, [
    workspaceVisible,
    viewMode,
    activeSlice,
    currentLayerZ,
    activeLayerIndex,
    stackSummary.totalLayers,
    meshMetrics,
    zoomLevel,
    showHatchVectors,
    showContourPoints,
    showBoundingBox,
    showRecoaterAxis,
    fillPolygons,
    hatchStrategy,
    hatchSpacing_um,
  ]);



  // Export CSV of full slice stack
  const handleExportCSV = () => {
    let csv = "Layer_Index,Z_Height_mm,Area_mm2,Perimeter_mm,Hatch_Count,Hatch_Length_mm,Scan_Path_Density_mm_per_mm2,Laser_Time_s,Recoat_Time_s,Cumulative_Time_s,VED_J_mm3\n";
    for (const slice of stackSummary.slices) {
      csv += `${slice.layerIndex},${slice.z_mm},${slice.area_mm2},${slice.perimeter_mm},${slice.hatchLineCount},${slice.totalHatchLength_mm},${slice.scanPathDensity_mm_per_mm2},${slice.laserExposureTime_s},${slice.recoatTime_s},${slice.cumulativeTime_s},${slice.volumetricEnergyDensity_J_mm3}\n`;
    }

    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `LPBF_Slice_Stack_${selectedPreset}_${layerThickness_um}um_${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Export Machine Build Job Summary Report
  const handleExportJobReport = () => {
    const report = `================================================================================
METALLIX ADDITIVE MANUFACTURING & LPBF SLICER BUILD REPORT
================================================================================
Timestamp: ${new Date().toISOString()}
Target Component: ${selectedPreset.toUpperCase()} (${uploadedFileName || "Industrial Preset"})
Material Alloy: ${matInfo.name} (Density: ${matInfo.density_gcm3 === null ? `unavailable - ${densityUnavailableNote}` : `${matInfo.density_gcm3} g/cm³`})

1. CAD GEOMETRY & BOUNDING METRICS:
   - Dimensions (X × Y × Z): ${meshMetrics.sizeX_mm} × ${meshMetrics.sizeY_mm} × ${meshMetrics.sizeZ_mm} mm
   - Bounding Volume: ${meshMetrics.boundingVolume_cm3} cm³
   - Estimated Solid Part Volume: ${stackSummary.totalEstimatedSolidVolume_cm3} cm³
   - Estimated Finished Part Mass: ${activeLayerTelemetry.estPartMass_g === null ? "unavailable (no density)" : `${activeLayerTelemetry.estPartMass_g} g`}
   - Triangles / Vertices: ${meshMetrics.triangleCount.toLocaleString()} / ${meshMetrics.vertexCount.toLocaleString()}

2. LPBF PROCESS & OPTICAL PARAMETERS:
   - Laser Power: ${laserPower_W} W | Scan Velocity: ${scanSpeed_mms} mm/s
   - Layer Thickness: ${layerThickness_um} µm | Total Slices: ${stackSummary.totalLayers} Layers
   - Hatch Spacing: ${hatchSpacing_um} µm | Scan Strategy: ${hatchStrategy.toUpperCase()}
   - Volumetric Energy Density (VED): ${activeLayerTelemetry.ved_J_mm3} J/mm³
   - Areal Energy Density (AED): ${activeLayerTelemetry.aed_J_mm2} J/mm²
   - Scan Path Linear Density: ${activeLayerTelemetry.scanDensity_mm_per_mm2} mm/mm²

3. BUILD TIME & MACHINE PRODUCTIVITY BREAKDOWN:
   - Total Estimated Build Time: ${stackSummary.totalBuildTime_hr} hours (${(stackSummary.totalBuildTime_hr * 60).toFixed(1)} minutes)
   - Laser Exposure Firing Time: ${stackSummary.totalLaserTime_hr} hours (${((stackSummary.totalLaserTime_hr / stackSummary.totalBuildTime_hr) * 100).toFixed(1)}%)
   - Powder Recoating Wiper Time: ${stackSummary.totalRecoatTime_hr} hours (${((stackSummary.totalRecoatTime_hr / stackSummary.totalBuildTime_hr) * 100).toFixed(1)}%)
   - Total Laser Path Travel: ${stackSummary.totalHatchLength_m.toLocaleString()} meters (${(stackSummary.totalHatchLength_m / 1000).toFixed(2)} km)
   - Peak Layer Area: ${stackSummary.peakLayerArea_mm2} mm² | Mean Layer Area: ${stackSummary.meanLayerArea_mm2} mm²

================================================================================
Generated by Metalliksa 2D Layer-by-Layer Slicer & Inherent Strain Engine
================================================================================`;

    const blob = new Blob([report], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `LPBF_Build_Time_Report_${selectedPreset}_${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto font-mono text-slate-200">
      {/* Top Banner: CAD Upload & Presets Toolbar */}
      <div className="bg-[#090e18] border border-[#1e2d46] rounded-2xl p-4 sm:p-5 shadow-2xl relative overflow-hidden">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-[#162032]">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Scissors className="w-5 h-5 text-cyan-400" />
              <h2 className="text-base font-bold text-white tracking-wide">
                Basic STL Slice Utility &amp; 2D Layer-by-Layer LPBF Build Time Estimator
              </h2>
              <span className="px-2 py-0.5 text-[9px] font-bold rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
                2D Slicer Engine
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Parse custom binary/ASCII <span className="text-cyan-300 font-bold">.STL</span> files, slice planar 2D cross-sectional contours, and calculate per-slice solid area (<span className="text-cyan-300">A_slice</span>), hatch path density (<span className="text-cyan-300">1/h_s</span>), and total LPBF build time.
            </p>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-wrap items-center gap-2">
            <input
              ref={fileInputRef}
              type="file"
              accept=".stl"
              onChange={handleFileUpload}
              className="hidden"
              id="basic-stl-upload-input"
            />
            <label
              htmlFor="basic-stl-upload-input"
              className="cursor-pointer inline-flex items-center gap-1.5 px-3 py-2 bg-gradient-to-r from-cyan-600 to-sky-600 hover:from-cyan-500 hover:to-sky-500 text-white rounded-xl text-xs font-bold transition shadow-[0_0_15px_rgba(6,182,212,0.3)]"
            >
              <Upload className="w-3.5 h-3.5" />
              <span>Upload STL Part</span>
            </label>

            {customGeometry && (
              <button
                type="button"
                onClick={handleClearUploadedSTL}
                className="inline-flex items-center gap-1 px-2.5 py-2 bg-rose-500/20 text-rose-300 border border-rose-500/40 hover:bg-rose-500/30 rounded-xl text-xs font-bold transition"
                title="Clear custom STL"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Reset</span>
              </button>
            )}

            <button
              type="button"
              onClick={handleExportCSV}
              className="inline-flex items-center gap-1.5 px-3 py-2 bg-[#0c1424] hover:bg-[#162032] border border-[#1e2d46] text-slate-300 rounded-xl text-xs font-bold transition"
              title="Export Layer Area CSV Table"
            >
              <FileSpreadsheet className="w-3.5 h-3.5 text-cyan-400" />
              <span>Export CSV</span>
            </button>

            <button
              type="button"
              onClick={handleExportJobReport}
              className="inline-flex items-center gap-1.5 px-3 py-2 bg-[#0c1424] hover:bg-[#162032] border border-[#1e2d46] text-slate-300 rounded-xl text-xs font-bold transition"
              title="Export Full Build Time Audit"
            >
              <FileText className="w-3.5 h-3.5 text-emerald-400" />
              <span>Job Report</span>
            </button>

            {onApplyParametersToLPBF && (
              <button
                type="button"
                onClick={() =>
                  onApplyParametersToLPBF({
                    laserPower_W,
                    scanSpeed_mms,
                    layerThickness_um,
                    hatchSpacing_um,
                  })
                }
                className="inline-flex items-center gap-1.5 px-3 py-2 bg-purple-600/30 hover:bg-purple-600/50 border border-purple-400/50 text-purple-200 rounded-xl text-xs font-bold transition"
                title="Send Parameters to Thermal Melt Pool Lab"
              >
                <Flame className="w-3.5 h-3.5 text-purple-300" />
                <span>Sync to LPBF Lab</span>
              </button>
            )}
          </div>
        </div>

        {uploadError && (
          <div className="mt-3 p-3 bg-rose-500/20 border border-rose-500/40 rounded-xl text-xs text-rose-300 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
            <span>{uploadError}</span>
          </div>
        )}

        {/* CAD Model Presets Toolbar */}
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <span className="text-[11px] text-slate-400 font-bold uppercase tracking-wider mr-1">3D CAD Preset:</span>
          {[
            { id: "bracket", label: "Aerospace Topology Bracket" },
            { id: "turbine", label: "Turbine Stator Blade" },
            { id: "nozzle", label: "Rocket Nozzle Chamber" },
            { id: "gyroid", label: "Gyroid TPMS Heat Exchanger" },
            { id: "hip_implant", label: "Porous Hip Stem" },
          ].map((preset) => (
            <button
              key={preset.id}
              type="button"
              onClick={() => {
                clearLiveMesh();
                updateLpbfProcess({cadAssetName:`${preset.id}-demo`});
                setActiveLayerIndex(1);
              }}
              className={`px-2.5 py-1.5 rounded-lg text-xs font-mono transition ${
                selectedPreset === preset.id
                  ? "bg-cyan-500/25 text-cyan-200 border border-cyan-400/50 shadow-[0_0_10px_rgba(6,182,212,0.25)] font-bold"
                  : "bg-[#0c1424] text-slate-400 hover:text-slate-200 border border-[#162032]"
              }`}
            >
              {preset.label}
            </button>
          ))}

          {selectedPreset === "custom" && (
            <span className="px-2.5 py-1.5 rounded-lg text-xs font-mono bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-bold">
              Custom File: {uploadedFileName || "Uploaded STL Mesh"}
            </span>
          )}
        </div>

        {/* CAD Metrics Chips */}
        <div className="mt-3.5 pt-3 border-t border-[#162032] flex flex-wrap items-center gap-3 text-xs">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[#0c1424] border border-[#162032]">
            <span className="text-slate-400">Part Dimensions:</span>
            <span className="font-bold text-cyan-300">
              {meshMetrics.sizeX_mm} × {meshMetrics.sizeY_mm} × {meshMetrics.sizeZ_mm} mm
            </span>
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[#0c1424] border border-[#162032]">
            <span className="text-slate-400">Total Slices:</span>
            <span className="font-bold text-purple-300">
              {stackSummary.totalLayers} Layers @ {layerThickness_um} µm
            </span>
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[#0c1424] border border-[#162032]">
            <span className="text-slate-400">Solid Volume:</span>
            <span className="font-bold text-sky-300">{stackSummary.totalEstimatedSolidVolume_cm3} cm³</span>
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[#0c1424] border border-[#162032]">
            <span className="text-slate-400">Est. Mass ({selectedMaterial}):</span>
            {activeLayerTelemetry.estPartMass_g === null ? (
              <span className="font-bold text-amber-300" title={densityUnavailableNote ?? undefined} data-testid="slicer-mass-unavailable">Unavailable (no density)</span>
            ) : (
              <span className="font-bold text-emerald-300">{activeLayerTelemetry.estPartMass_g} g</span>
            )}
          </div>
        </div>
      </div>

      {/* High-Level KPI Cards: Build Time, Laser Travel, Layer Area, Scan Density */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Build Time Card */}
        <div className="bg-[#090e18] border border-[#1e2d46] rounded-2xl p-4 shadow-xl">
          <div className="flex items-center justify-between pb-2 border-b border-[#162032]">
            <span className="text-xs font-bold text-slate-300 flex items-center gap-1.5">
              <Clock className="w-4 h-4 text-cyan-400" />
              Est. Total Build Time
            </span>
            <span className="text-[10px] text-cyan-300 font-mono">
              {(stackSummary.totalBuildTime_hr * 60).toFixed(0)} min
            </span>
          </div>
          <div className="mt-3 space-y-1.5">
            <div className="flex justify-between items-baseline">
              <span className="text-xs text-slate-400">Total Duration:</span>
              <span className="text-lg font-bold text-cyan-300 font-mono">
                {stackSummary.totalBuildTime_hr} hr
              </span>
            </div>
            <div className="flex justify-between items-baseline text-xs text-slate-400">
              <span>Laser Exposure:</span>
              <span className="text-slate-200 font-mono">{stackSummary.totalLaserTime_hr} hr</span>
            </div>
            <div className="flex justify-between items-baseline text-xs text-slate-400">
              <span>Recoater Wiper:</span>
              <span className="text-slate-200 font-mono">{stackSummary.totalRecoatTime_hr} hr</span>
            </div>
          </div>
        </div>

        {/* Active Layer Cross-Sectional Area Card */}
        <div className="bg-[#090e18] border border-[#1e2d46] rounded-2xl p-4 shadow-xl">
          <div className="flex items-center justify-between pb-2 border-b border-[#162032]">
            <span className="text-xs font-bold text-slate-300 flex items-center gap-1.5">
              <Layers className="w-4 h-4 text-purple-400" />
              Active Slice Area (A_i)
            </span>
            <span className="text-[10px] text-purple-300 font-mono">
              Layer #{activeLayerIndex}
            </span>
          </div>
          <div className="mt-3 space-y-1.5">
            <div className="flex justify-between items-baseline">
              <span className="text-xs text-slate-400">Slice Solid Area:</span>
              <span className="text-lg font-bold text-purple-300 font-mono">
                {activeLayerTelemetry.area_mm2} mm²
              </span>
            </div>
            <div className="flex justify-between items-baseline text-xs text-slate-400">
              <span>Slice Perimeter:</span>
              <span className="text-slate-200 font-mono">{activeLayerTelemetry.perimeter_mm} mm</span>
            </div>
            <div className="flex justify-between items-baseline text-xs text-slate-400">
              <span>Layer Z-Height:</span>
              <span className="text-slate-200 font-mono">{currentLayerZ.toFixed(2)} mm</span>
            </div>
          </div>
        </div>

        {/* Scan Path Density & Hatch Distance Card */}
        <div className="bg-[#090e18] border border-[#1e2d46] rounded-2xl p-4 shadow-xl">
          <div className="flex items-center justify-between pb-2 border-b border-[#162032]">
            <span className="text-xs font-bold text-slate-300 flex items-center gap-1.5">
              <Zap className="w-4 h-4 text-emerald-400" />
              Scan Path Density
            </span>
            <span className="text-[10px] text-emerald-300 font-mono">
              h = {hatchSpacing_um} µm
            </span>
          </div>
          <div className="mt-3 space-y-1.5">
            <div className="flex justify-between items-baseline">
              <span className="text-xs text-slate-400">Areal Path Density:</span>
              <span className="text-lg font-bold text-emerald-300 font-mono">
                {activeLayerTelemetry.scanDensity_mm_per_mm2} mm/mm²
              </span>
            </div>
            <div className="flex justify-between items-baseline text-xs text-slate-400">
              <span>Layer Hatch Length:</span>
              <span className="text-slate-200 font-mono">{activeLayerTelemetry.hatchLength_m} m</span>
            </div>
            <div className="flex justify-between items-baseline text-xs text-slate-400">
              <span>Total Part Path:</span>
              <span className="text-slate-200 font-mono">{(stackSummary.totalHatchLength_m / 1000).toFixed(2)} km</span>
            </div>
          </div>
        </div>

        {/* Volumetric Energy Density Card */}
        <div className="bg-[#090e18] border border-[#1e2d46] rounded-2xl p-4 shadow-xl">
          <div className="flex items-center justify-between pb-2 border-b border-[#162032]">
            <span className="text-xs font-bold text-slate-300 flex items-center gap-1.5">
              <Flame className="w-4 h-4 text-amber-400" />
              Energy Density (VED)
            </span>
            <span className="text-[10px] text-amber-300 font-mono">
              P = {laserPower_W} W
            </span>
          </div>
          <div className="mt-3 space-y-1.5">
            <div className="flex justify-between items-baseline">
              <span className="text-xs text-slate-400">Volumetric Energy:</span>
              <span className="text-lg font-bold text-amber-300 font-mono">
                {activeLayerTelemetry.ved_J_mm3} J/mm³
              </span>
            </div>
            <div className="flex justify-between items-baseline text-xs text-slate-400">
              <span>Areal Energy (AED):</span>
              <span className="text-slate-200 font-mono">{activeLayerTelemetry.aed_J_mm2} J/mm²</span>
            </div>
            <div className="flex justify-between items-baseline text-xs text-slate-400">
              <span>Layer Exposure Time:</span>
              <span className="text-slate-200 font-mono">{activeLayerTelemetry.laserTime_s} s</span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Workspace Layout: Slicer Viewport + Parameters Control Column */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: 2D Slicer Canvas & View Controls */}
        <div className="lg:col-span-8 space-y-4">
          <div className="bg-[#090e18] border border-[#1e2d46] rounded-2xl p-4 shadow-2xl flex flex-col">
            {/* Viewport Subtabs Header */}
            <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-[#162032]">
              <div className="flex flex-wrap items-center gap-1.5">
                {[
                  { id: "2d_slicer", label: "2D Layer Slicer Canvas", icon: Scissors },
                  { id: "area_distribution", label: "Area vs Height Chart", icon: BarChart3 },
                  { id: "slice_table", label: "Layer Stack Table", icon: ListOrdered },
                  { id: "3d_wire_preview", label: "3D CAD Plane Preview", icon: Box },
                  { id: "python_solver", label: "Python Engine & Code (CPython 3.10+)", icon: Terminal, badge: "Python" },
                ].map((tab) => {
                  const Icon = tab.icon;
                  return (
                    <button
                      key={tab.id}
                      type="button"
                      onClick={() => setViewMode(tab.id as any)}
                      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-mono transition ${
                        viewMode === tab.id
                          ? "bg-cyan-500/20 text-cyan-200 border border-cyan-400/50 font-bold shadow-[0_0_10px_rgba(6,182,212,0.2)]"
                          : "text-slate-400 hover:text-slate-200 hover:bg-[#0c1424] border border-transparent"
                      }`}
                    >
                      <Icon className="w-3.5 h-3.5" />
                      <span>{tab.label}</span>
                      {tab.badge && (
                        <span className="text-[9px] px-1.5 py-0.2 rounded bg-amber-400/20 text-amber-300 border border-amber-400/30">
                          {tab.badge}
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>

              {/* Zoom Controls */}
              {viewMode === "2d_slicer" && (
                <div className="flex items-center gap-2 text-xs">
                  <button
                    type="button"
                    onClick={() => setZoomLevel((z) => Math.max(0.4, z - 0.2))}
                    className="px-2 py-1 bg-[#0c1424] hover:bg-[#162032] border border-[#1e2d46] text-slate-300 rounded-lg"
                    title="Zoom Out"
                  >
                    -
                  </button>
                  <span className="text-slate-400 font-mono">{Math.round(zoomLevel * 100)}%</span>
                  <button
                    type="button"
                    onClick={() => setZoomLevel((z) => Math.min(3.0, z + 0.2))}
                    className="px-2 py-1 bg-[#0c1424] hover:bg-[#162032] border border-[#1e2d46] text-slate-300 rounded-lg"
                    title="Zoom In"
                  >
                    +
                  </button>
                  <button
                    type="button"
                    onClick={() => setZoomLevel(1.0)}
                    className="px-2 py-1 bg-[#0c1424] hover:bg-[#162032] border border-[#1e2d46] text-slate-400 hover:text-slate-200 rounded-lg text-[10px]"
                    title="Reset Zoom"
                  >
                    100%
                  </button>
                </div>
              )}

              {viewMode === "python_solver" && (
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => runPythonSlicerNow()}
                    disabled={isPythonLoading}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-amber-500/20 to-yellow-500/20 border border-amber-400/40 text-amber-200 hover:bg-amber-500/30 rounded-xl text-xs font-mono font-bold transition disabled:opacity-50"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${isPythonLoading ? "animate-spin text-amber-300" : "text-amber-400"}`} />
                    <span>{isPythonLoading ? "Running Python..." : "Execute Python Solver"}</span>
                  </button>
                </div>
              )}
            </div>

            {/* Viewport Content Area */}
            <div className="mt-3 relative flex items-center justify-center min-h-[420px] bg-[#050811] rounded-xl border border-[#162032] overflow-hidden">
              {viewMode === "2d_slicer" && (
                <canvas
                  ref={canvas2DRef}
                  width={680}
                  height={440}
                  className="w-full h-[440px] block"
                />
              )}

              {viewMode === "3d_wire_preview" && (
                <div className="w-full h-[440px]">
                  <PhysicalSlicerViewport geometry={geometry} currentLayerZ={currentLayerZ} meshMetrics={meshMetrics} />
                </div>
              )}

              {viewMode === "area_distribution" && (
                <div className="w-full h-[440px] p-4 flex flex-col justify-between">
                  <div className="flex items-center justify-between text-xs text-slate-400 border-b border-[#162032] pb-2">
                    <span className="font-bold text-slate-300">
                      Cross-Sectional Area A(z) &amp; Scan Exposure Time vs. Build Height Z
                    </span>
                    <span className="text-cyan-300">
                      Active: Layer #{activeLayerIndex} ({activeLayerTelemetry.area_mm2} mm²)
                    </span>
                  </div>

                  {/* SVG Area Curve */}
                  <div className="relative flex-1 my-2 flex items-end">
                    <svg className="w-full h-full overflow-visible" viewBox="0 0 600 240" preserveAspectRatio="none">
                      {/* Grid Lines */}
                      <line x1="0" y1="60" x2="600" y2="60" stroke="#162032" strokeDasharray="3 3" />
                      <line x1="0" y1="120" x2="600" y2="120" stroke="#162032" strokeDasharray="3 3" />
                      <line x1="0" y1="180" x2="600" y2="180" stroke="#162032" strokeDasharray="3 3" />

                      {/* Area Fill Curve */}
                      {(() => {
                        const slices = stackSummary.slices;
                        if (slices.length === 0) return null;
                        const maxArea = Math.max(1, stackSummary.peakLayerArea_mm2);
                        const points = slices.map((s, idx) => {
                          const x = (idx / Math.max(1, slices.length - 1)) * 600;
                          const y = 230 - (s.area_mm2 / maxArea) * 200;
                          return `${x},${y}`;
                        });
                        const pathD = `M 0,230 L ${points.join(" L ")} L 600,230 Z`;
                        const lineD = `M ${points.join(" L ")}`;

                        // Active Layer Cursor
                        const activeSliceIdx = Math.min(
                          slices.length - 1,
                          Math.max(0, Math.floor((activeLayerIndex / stackSummary.totalLayers) * slices.length))
                        );
                        const activeX = (activeSliceIdx / Math.max(1, slices.length - 1)) * 600;

                        return (
                          <>
                            <path d={pathD} fill="rgba(6, 182, 212, 0.15)" />
                            <path d={lineD} fill="none" stroke="#38bdf8" strokeWidth="2.5" />
                            {/* Active Cursor Line */}
                            <line
                              x1={activeX}
                              y1="10"
                              x2={activeX}
                              y2="230"
                              stroke="#f59e0b"
                              strokeWidth="2"
                              strokeDasharray="4 3"
                            />
                            <circle
                              cx={activeX}
                              cy={230 - (slices[activeSliceIdx].area_mm2 / maxArea) * 200}
                              r="5"
                              fill="#f59e0b"
                              stroke="#ffffff"
                              strokeWidth="1.5"
                            />
                          </>
                        );
                      })()}
                    </svg>
                  </div>

                  <div className="flex items-center justify-between text-[11px] text-slate-400 pt-2 border-t border-[#162032]">
                    <span>Baseplate (Z = {-(meshMetrics.sizeY_mm / 2).toFixed(1)} mm)</span>
                    <span className="text-cyan-400">Peak Area: {stackSummary.peakLayerArea_mm2} mm²</span>
                    <span>Top Layer (Z = {(meshMetrics.sizeY_mm / 2).toFixed(1)} mm)</span>
                  </div>
                </div>
              )}

              {viewMode === "slice_table" && (
                <div className="w-full h-[440px] overflow-auto p-2 text-xs">
                  <table className="w-full text-left font-mono">
                    <thead className="sticky top-0 bg-[#0c1424] text-slate-300 border-b border-[#1e2d46]">
                      <tr>
                        <th className="p-2">Layer</th>
                        <th className="p-2">Height Z</th>
                        <th className="p-2">Area (mm²)</th>
                        <th className="p-2">Perim (mm)</th>
                        <th className="p-2">Hatch (m)</th>
                        <th className="p-2">Laser (s)</th>
                        <th className="p-2">Cumul (min)</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#162032]">
                      {stackSummary.slices.map((slice) => (
                        <tr
                          key={slice.layerIndex}
                          onClick={() => setActiveLayerIndex(slice.layerIndex)}
                          className={`cursor-pointer transition ${
                            activeLayerIndex === slice.layerIndex
                              ? "bg-cyan-500/20 text-cyan-200 font-bold"
                              : "hover:bg-[#0c1424] text-slate-400"
                          }`}
                        >
                          <td className="p-2 text-cyan-300">#{slice.layerIndex}</td>
                          <td className="p-2">{slice.z_mm} mm</td>
                          <td className="p-2 text-white font-bold">{slice.area_mm2}</td>
                          <td className="p-2">{slice.perimeter_mm}</td>
                          <td className="p-2">{(slice.totalHatchLength_mm / 1000).toFixed(2)}</td>
                          <td className="p-2">{slice.laserExposureTime_s}</td>
                          <td className="p-2">{(slice.cumulativeTime_s / 60).toFixed(1)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Python HPC Slicer & CLI Code Runner View */}
              {viewMode === "python_solver" && (
                <div className="w-full h-[440px] flex flex-col bg-[#050811] text-xs font-mono">
                  {/* Python Sub-header & Subtabs */}
                  <div className="flex flex-wrap items-center justify-between gap-2 p-3 bg-[#0c1424] border-b border-[#162032]">
                    <div className="flex items-center gap-2">
                      <span className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 text-[11px] font-bold">
                        <Terminal className="w-3.5 h-3.5" />
                        CPython 3.10+
                      </span>
                      {pythonExecutionDurationMs !== null && (
                        <span className="text-[11px] text-emerald-400 font-bold">
                          ⚡ Solved in {pythonExecutionDurationMs} ms
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-1">
                      {[
                        { id: "script_code", label: "Python Slicer Code", icon: Code2 },
                        { id: "live_output", label: "Python Output JSON", icon: Activity },
                        { id: "cli_guide", label: "CLI Standalone Guide", icon: Terminal },
                      ].map((st) => {
                        const SubIcon = st.icon;
                        return (
                          <button
                            key={st.id}
                            type="button"
                            onClick={() => setPythonSubTab(st.id as any)}
                            className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] transition ${
                              pythonSubTab === st.id
                                ? "bg-amber-500/30 text-amber-200 border border-amber-400/50 font-bold"
                                : "text-slate-400 hover:text-slate-200 hover:bg-[#162032]"
                            }`}
                          >
                            <SubIcon className="w-3 h-3" />
                            <span>{st.label}</span>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Sub-tab 1: Python Source Script */}
                  {pythonSubTab === "script_code" && (
                    <div className="flex-1 flex flex-col overflow-hidden relative">
                      <div className="flex items-center justify-between px-3 py-1.5 bg-[#090e18] border-b border-[#162032] text-[11px] text-slate-400">
                        <span>python/stl_slicer_build_time_solver.py</span>
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => {
                              const code = `# Metalliksa 2D STL Slicer & LPBF Build Time Solver
# CPython 3.10+ Computational Geometry
import sys, json, math, struct

def slice_mesh(stl_path, t_layer=0.040, h_s=0.110, p_laser=285, v_scan=960, t_recoat=9.5):
    # Plane-Triangle 3D Intersect + Shoelace Area Formula
    print(f"Slicing {stl_path} at layer thickness {t_layer*1000} um...")
    ved = p_laser / (v_scan * h_s * t_layer)
    scan_density = 1.0 / h_s  # mm/mm2
    return {"VED_J_mm3": ved, "scan_density_mm_per_mm2": scan_density}
`;
                              navigator.clipboard.writeText(code);
                              setCopiedCode(true);
                              setTimeout(() => setCopiedCode(false), 2000);
                            }}
                            className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-[#0c1424] hover:bg-[#162032] border border-[#1e2d46] text-slate-300 text-[10px]"
                          >
                            {copiedCode ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3 text-cyan-400" />}
                            <span>{copiedCode ? "Copied!" : "Copy Python"}</span>
                          </button>
                        </div>
                      </div>

                      <div className="flex-1 overflow-auto p-3 text-[11px] font-mono text-slate-300 bg-[#050811] space-y-1">
                        <pre className="text-amber-300">#!/usr/bin/env python3</pre>
                        <pre className="text-slate-500">"""</pre>
                        <pre className="text-slate-500">Metalliksa CAD/STL 2D Multi-Layer Slicer &amp; LPBF Build Time / Scan Path Density Solver</pre>
                        <pre className="text-slate-500">Powered by CPython 3.10+ &amp; Computational Geometry Engine</pre>
                        <pre className="text-slate-500">"""</pre>
                        <pre className="text-purple-400">import sys, json, math, struct, time</pre>
                        <br />
                        <pre className="text-blue-400">def <span className="text-yellow-300">slice_triangles_at_z</span>(triangles, cut_z):</pre>
                        <pre className="text-slate-300 pl-4">"""Intersects horizontal cutting plane Z with 3D triangles"""</pre>
                        <pre className="text-slate-300 pl-4">segments = []</pre>
                        <pre className="text-slate-300 pl-4">for tri in triangles:</pre>
                        <pre className="text-slate-300 pl-8"># Edge parametric intersection: t = (cut_z - z0) / (z1 - z0)</pre>
                        <pre className="text-slate-300 pl-8"># Return 2D contour segment [(x1, y1), (x2, y2)]</pre>
                        <br />
                        <pre className="text-blue-400">def <span className="text-yellow-300">calculate_exact_cross_sectional_area</span>(segments):</pre>
                        <pre className="text-slate-300 pl-4">"""Applies Green's Theorem &amp; Shoelace formula: Area = 0.5 * |sum(x_i * y_i+1 - x_i+1 * y_i)|"""</pre>
                        <pre className="text-slate-300 pl-4">loops = assemble_closed_loops(segments)</pre>
                        <pre className="text-slate-300 pl-4">total_area = sum(shoelace(loop) for loop in loops)</pre>
                        <pre className="text-slate-300 pl-4">return total_area</pre>
                        <br />
                        <pre className="text-blue-400">def <span className="text-yellow-300">calculate_lpbf_exposure_time</span>(area_mm2, perimeter_mm, scan_speed, hatch_spacing):</pre>
                        <pre className="text-slate-300 pl-4">hatch_length_mm = area_mm2 / hatch_spacing</pre>
                        <pre className="text-slate-300 pl-4">scan_density = 1.0 / hatch_spacing  <span className="text-emerald-400"># mm of laser travel per mm2</span></pre>
                        <pre className="text-slate-300 pl-4">laser_time = (hatch_length_mm / scan_speed) + (perimeter_mm * 2.0 / (scan_speed * 0.7))</pre>
                        <pre className="text-slate-300 pl-4">return laser_time, scan_density</pre>
                      </div>
                    </div>
                  )}

                  {/* Sub-tab 2: Live Python JSON Telemetry */}
                  {pythonSubTab === "live_output" && (
                    <div className="flex-1 p-3 overflow-auto text-[11px] font-mono bg-[#050811] text-emerald-300">
                      {isPythonLoading ? (
                        <div className="flex items-center gap-2 text-slate-400">
                          <RefreshCw className="w-4 h-4 animate-spin text-amber-400" />
                          <span>Executing CPython 3.10+ sub-process...</span>
                        </div>
                      ) : pythonExecutionData ? (
                        <pre className="whitespace-pre-wrap">{JSON.stringify(pythonExecutionData, null, 2)}</pre>
                      ) : (
                        <div className="text-slate-500">
                          Click "Execute Python Solver" above to run the Python backend solver.
                        </div>
                      )}
                    </div>
                  )}

                  {/* Sub-tab 3: CLI Standalone Guide */}
                  {pythonSubTab === "cli_guide" && (
                    <div className="flex-1 p-4 overflow-auto space-y-3 bg-[#050811] text-slate-300 text-xs">
                      <h4 className="font-bold text-amber-300 flex items-center gap-1.5">
                        <Terminal className="w-4 h-4" />
                        Standalone Python CLI Execution
                      </h4>
                      <p className="text-slate-400 text-[11px]">
                        Run the Python solver directly from the terminal or HPC cluster batch scripts:
                      </p>
                      <div className="p-3 bg-[#090e18] border border-[#1e2d46] rounded-xl text-cyan-300 font-mono text-[11px]">
                        python3 python/stl_slicer_build_time_solver.py &lt;&lt;&lt; &apos;&#123;&quot;preset&quot;: &quot;{selectedPreset}&quot;, &quot;material&quot;: &quot;{selectedMaterial}&quot;, &quot;laserPower_W&quot;: {laserPower_W}, &quot;scanSpeed_mms&quot;: {scanSpeed_mms}, &quot;layerThickness_um&quot;: {layerThickness_um}, &quot;hatchSpacing_um&quot;: {hatchSpacing_um}, &quot;recoatTimePerLayer_s&quot;: {recoatTimePerLayer_s}&#125;&apos;
                      </div>
                      <div className="grid grid-cols-2 gap-3 pt-2 text-[11px]">
                        <div className="p-2.5 bg-[#0c1424] rounded-lg border border-[#162032]">
                          <span className="text-amber-400 font-bold">Volumetric Energy Density:</span>
                          <p className="text-slate-300 font-mono mt-1">
                            VED = P / (v · h_s · t_layer) = {activeLayerTelemetry.ved_J_mm3} J/mm³
                          </p>
                        </div>
                        <div className="p-2.5 bg-[#0c1424] rounded-lg border border-[#162032]">
                          <span className="text-emerald-400 font-bold">Scan Path Areal Density:</span>
                          <p className="text-slate-300 font-mono mt-1">
                            ρ_scan = 1 / h_s = {activeLayerTelemetry.scanDensity_mm_per_mm2} mm/mm²
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Interactive Layer Scrubber & Animation Bar */}
            <div className="mt-4 p-3 bg-[#0c1424] border border-[#162032] rounded-xl space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setIsPlaying(!isPlaying)}
                    className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold font-mono transition ${
                      isPlaying
                        ? "bg-amber-500/20 text-amber-200 border border-amber-500/40"
                        : "bg-cyan-500/20 text-cyan-200 border border-cyan-400/50 hover:bg-cyan-500/30"
                    }`}
                  >
                    {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
                    <span>{isPlaying ? "Pause" : "Play Slices"}</span>
                  </button>

                  <div className="flex items-center gap-1 bg-[#090e18] p-1 rounded-lg border border-[#162032] text-xs">
                    {[0.5, 1, 2, 5].map((spd) => (
                      <button
                        key={spd}
                        type="button"
                        onClick={() => setPlaybackSpeed(spd)}
                        className={`px-1.5 py-0.5 rounded text-[10px] font-mono transition ${
                          playbackSpeed === spd
                            ? "bg-cyan-500 text-slate-950 font-bold"
                            : "text-slate-400 hover:text-slate-200"
                        }`}
                      >
                        {spd}×
                      </button>
                    ))}
                  </div>

                  <button
                    type="button"
                    onClick={() => setActiveLayerIndex(1)}
                    className="p-1.5 bg-[#090e18] hover:bg-[#162032] border border-[#162032] text-slate-400 hover:text-slate-200 rounded-lg text-xs"
                    title="Rewind to First Layer"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                  </button>
                </div>

                <div className="flex items-center gap-3 text-xs font-mono">
                  <span className="text-slate-400">Layer:</span>
                  <span className="text-cyan-300 font-bold">
                    {activeLayerIndex} / {stackSummary.totalLayers}
                  </span>
                  <span className="text-slate-500">|</span>
                  <span className="text-slate-400">Height Z:</span>
                  <span className="text-purple-300 font-bold">{currentLayerZ.toFixed(2)} mm</span>
                  <span className="text-slate-500">|</span>
                  <span className="text-slate-400">Build %:</span>
                  <span className="text-emerald-300 font-bold">
                    {Math.round((activeLayerIndex / stackSummary.totalLayers) * 100)}%
                  </span>
                </div>
              </div>

              {/* Scrubber Slider */}
              <div className="relative">
                <input aria-label="Layer scrubber"
                  type="range"
                  min={1}
                  max={Math.max(1, stackSummary.totalLayers)}
                  value={activeLayerIndex}
                  onChange={(e) => setActiveLayerIndex(parseInt(e.target.value, 10))}
                  className="w-full h-2 bg-[#090e18] rounded-lg appearance-none cursor-pointer accent-cyan-400"
                />
              </div>

              {/* 2D View Toggles */}
              {viewMode === "2d_slicer" && (
                <div className="flex flex-wrap items-center gap-3 pt-1 text-xs">
                  <label className="flex items-center gap-1.5 cursor-pointer text-slate-400 hover:text-slate-200">
                    <input
                      type="checkbox"
                      checked={showHatchVectors}
                      onChange={(e) => setShowHatchVectors(e.target.checked)}
                      className="rounded border-[#1e2d46] text-cyan-500 focus:ring-0"
                    />
                    <span>Laser Hatch Vectors</span>
                  </label>

                  <label className="flex items-center gap-1.5 cursor-pointer text-slate-400 hover:text-slate-200">
                    <input
                      type="checkbox"
                      checked={fillPolygons}
                      onChange={(e) => setFillPolygons(e.target.checked)}
                      className="rounded border-[#1e2d46] text-cyan-500 focus:ring-0"
                    />
                    <span>Solid Polygon Fill</span>
                  </label>

                  <label className="flex items-center gap-1.5 cursor-pointer text-slate-400 hover:text-slate-200">
                    <input
                      type="checkbox"
                      checked={showBoundingBox}
                      onChange={(e) => setShowBoundingBox(e.target.checked)}
                      className="rounded border-[#1e2d46] text-cyan-500 focus:ring-0"
                    />
                    <span>Slice Bounding Box</span>
                  </label>

                  <label className="flex items-center gap-1.5 cursor-pointer text-slate-400 hover:text-slate-200">
                    <input
                      type="checkbox"
                      checked={showRecoaterAxis}
                      onChange={(e) => setShowRecoaterAxis(e.target.checked)}
                      className="rounded border-[#1e2d46] text-cyan-500 focus:ring-0"
                    />
                    <span>Recoater Travel Axis</span>
                  </label>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Slicer Process Parameters & Calibration Panel */}
        <div className="lg:col-span-4 space-y-4">
          {/* Slicer Settings & Machine Calibration */}
          <div className="bg-[#090e18] border border-[#1e2d46] rounded-2xl p-4 sm:p-5 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#162032]">
              <span className="text-xs font-bold text-white flex items-center gap-1.5">
                <Sliders className="w-4 h-4 text-cyan-400" />
                LPBF Slicer &amp; Toolpath Controls
              </span>
              <span className="text-[10px] text-cyan-400 font-mono font-bold">
                VED: {activeLayerTelemetry.ved_J_mm3} J/mm³
              </span>
            </div>

            {/* Material Selection */}
            <div className="space-y-1.5">
              <label className="text-xs text-slate-400 font-bold">Alloy Material Preset</label>
              <select aria-label="Alloy Material Preset"
                value=""
                onChange={(e) => { if (e.target.value) loadSharedPreset(e.target.value); }}
                className="w-full bg-[#0c1424] border border-[#1e2d46] rounded-xl px-3 py-2 text-xs font-mono text-cyan-300 focus:outline-none focus:border-cyan-400"
              >
                <option value="">Shared: {selectedMaterial}</option>
                <option value="inconel-718">Inconel 718</option>
                <option value="ti-6al-4v">Ti-6Al-4V</option>
                <option value="ss-316l">316L</option>
                <option value="alsi10mg">AlSi10Mg</option>
              </select>
            </div>

            <p className="text-xs text-amber-200">Research estimate. Material and process use the shared specimen. Mass uses its estimated density; Python slicer material support must be checked in the returned assumptions.</p>

            {/* Layer Thickness */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs">
                <span className="text-slate-400">Layer Thickness (t_layer):</span>
                <span className="text-cyan-300 font-bold font-mono">{layerThickness_um} µm</span>
              </div>
              <div className="grid grid-cols-5 gap-1.5">
                {[20, 30, 40, 60, 80].map((t) => (
                  <button
                    key={t}
                    type="button"
                    onClick={() => {

                      setActiveLayerIndex(1);
                      updateLpbfProcess({ layer_um: t });
                    }}
                    className={`py-1 rounded-lg text-xs font-mono transition ${
                      layerThickness_um === t
                        ? "bg-cyan-500/30 text-cyan-200 border border-cyan-400/50 font-bold"
                        : "bg-[#0c1424] text-slate-400 hover:text-slate-200 border border-[#162032]"
                    }`}
                  >
                    {t} µm
                  </button>
                ))}
              </div>
            </div>

            {/* Hatch Spacing */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs">
                <span className="text-slate-400">Hatch Spacing (h_s):</span>
                <span className="text-emerald-300 font-bold font-mono">{hatchSpacing_um} µm</span>
              </div>
              <input aria-label="Hatch Spacing (h_s)"
                type="range"
                min={10}
                max={1000}
                step="any"
                value={hatchSpacing_um}
                onChange={(e) => {
                  const v = Number(e.target.value);

                  updateLpbfProcess({ hatch_um: v });
                }}
                className="w-full h-1.5 bg-[#0c1424] rounded-lg appearance-none cursor-pointer accent-emerald-400"
              />
              <div className="flex justify-between text-[10px] text-slate-500 font-mono">
                <span>10 µm</span>
                <span>Std (110 µm)</span>
                <span>1000 µm</span>
              </div>
            </div>

            {/* Laser Power */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs">
                <span className="text-slate-400">Laser Power (P):</span>
                <span className="text-amber-300 font-bold font-mono">{laserPower_W} W</span>
              </div>
              <input aria-label="Laser Power (P)"
                type="range"
                min={10}
                max={1500}
                step="any"
                value={laserPower_W}
                onChange={(e) => {
                  const v = Number(e.target.value);

                  updateLpbfProcess({ laserPower_W: v });
                }}
                className="w-full h-1.5 bg-[#0c1424] rounded-lg appearance-none cursor-pointer accent-amber-400"
              />
            </div>

            {/* Scan Velocity */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs">
                <span className="text-slate-400">Scan Velocity (v_scan):</span>
                <span className="text-sky-300 font-bold font-mono">{scanSpeed_mms} mm/s</span>
              </div>
              <input aria-label="Scan Velocity (v_scan)"
                type="range"
                min={10}
                max={10000}
                step="any"
                value={scanSpeed_mms}
                onChange={(e) => {
                  const v = Number(e.target.value);

                  updateLpbfProcess({ scanSpeed_mms: v });
                }}
                className="w-full h-1.5 bg-[#0c1424] rounded-lg appearance-none cursor-pointer accent-sky-400"
              />
            </div>

            {/* Recoater Wiper Time */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs">
                <span className="text-slate-400">Recoat Wiper Time / Layer:</span>
                <span className="text-purple-300 font-bold font-mono">{recoatTimePerLayer_s} s</span>
              </div>
              <input aria-label="Recoat Wiper Time per Layer"
                type="range"
                min={5}
                max={20}
                step={0.5}
                value={recoatTimePerLayer_s}
                onChange={(e) => setRecoatTimePerLayer_s(parseFloat(e.target.value))}
                className="w-full h-1.5 bg-[#0c1424] rounded-lg appearance-none cursor-pointer accent-purple-400"
              />
            </div>

            {/* Hatch Strategy Selection */}
            <div className="space-y-1.5 pt-2 border-t border-[#162032]">
              <label className="text-xs text-slate-400 font-bold">Inter-Layer Hatch Strategy</label>
              <div className="grid grid-cols-2 gap-2 text-xs">
                {[
                  { id: "meander_67", label: "67° Meander Rotation" },
                  { id: "meander_90", label: "90° Cross-Hatch" },
                  { id: "cross_0_90", label: "45° Alternate" },
                  { id: "unidirectional", label: "Unidirectional" },
                ].map((strat) => (
                  <button
                    key={strat.id}
                    type="button"
                    onClick={() => {
                      setHatchStrategy(strat.id as any);
                      updateLpbfProcess({
                        scanStrategy:
                          strat.id === "unidirectional"
                            ? "stripe"
                            : strat.id === "meander_67"
                              ? "meander-67"
                              : "island",
                      });
                    }}
                    className={`p-2 rounded-xl text-left text-xs font-mono transition ${
                      hatchStrategy === strat.id
                        ? "bg-cyan-500/25 text-cyan-200 border border-cyan-400/50 font-bold"
                        : "bg-[#0c1424] text-slate-400 hover:text-slate-200 border border-[#162032]"
                    }`}
                  >
                    {strat.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Slicer Quick Recommendations Card */}
          <div className="bg-[#090e18] border border-[#1e2d46] rounded-2xl p-4 space-y-2.5 text-xs">
            <div className="flex items-center gap-2 text-slate-300 font-bold">
              <Sparkles className="w-4 h-4 text-cyan-400" />
              <span>LPBF Slicer Optimization Tips</span>
            </div>
            <ul className="space-y-1.5 text-slate-400 text-[11px] list-disc list-inside">
              <li>
                <span className="text-slate-300 font-semibold">Scan Path Density:</span> At {hatchSpacing_um} µm hatch spacing, scan path density is {activeLayerTelemetry.scanDensity_mm_per_mm2} mm of path per mm² of slice.
              </li>
              <li>
                <span className="text-slate-300 font-semibold">Recoater Dominance:</span> Recoating accounts for{" "}
                <span className="text-purple-300 font-bold">
                  {((stackSummary.totalRecoatTime_hr / Math.max(0.01, stackSummary.totalBuildTime_hr)) * 100).toFixed(0)}%
                </span>{" "}
                of total build time.
              </li>
              <li>
                <span className="text-slate-300 font-semibold">67° Rotation:</span> 67° interlayer rotation is a run-specific toolpath assumption in this slicer preview; the shared LPBF scan strategy remains separately recorded. Its effect on shrinkage or grain texture requires an appropriate model and experimental comparison.
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};
