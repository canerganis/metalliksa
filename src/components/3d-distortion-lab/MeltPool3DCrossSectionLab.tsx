import React, { useState, useEffect, useRef, useMemo, useCallback } from "react";
import { LpbfEngineeringSimulation } from "./LpbfEngineeringSimulation";
import { CalibratedMeltpoolPanel } from "./CalibratedMeltpoolPanel";
import { ResearchModelPanel } from "./ResearchModelPanel";
import { researchProcessSignature, type ResearchHostInput } from "../../utils/lpbfResearchPanelModel";
import * as THREE from "three";
import { useVisibleAnimationFrame } from "../../hooks/useVisibleAnimationFrame";
import {
  Flame,
  Activity,
  Layers,
  Zap,
  Sliders,
  Sparkles,
  Maximize2,
  Minimize2,
  Info,
  RotateCcw,
  Compass,
  AlertTriangle,
  CheckCircle2,
  ShieldAlert,
  Download,
  Crosshair,
  Grid,
  Cpu,
  RefreshCw,
  Box,
  Eye,
  Scissors,
  ArrowRight,
  TrendingDown,
  Waves,
  Sun,
  ShieldCheck,
} from "lucide-react";
import {
  pythonComputationService,
  PythonLPBFResult,
} from "../../services/pythonComputationService";
import {
  buildLoftedMeltPoolGeometry,
  contourToCutFace,
  disposeObject3D,
} from "./meltPool3DGeometry";
import { DISPLAY_CAP_LABEL, colourScaleIsDisplayCap, colourScalePeak_C, peakTemperatureBasisLabel, servedTemperatureText, axialFieldMaximumText } from "../../utils/peakTemperatureDisplay";
import {
  MELT_POOL_LITERATURE_CASES,
  isLoadableLiteratureCase,
  matchesLoadableLiteratureCase,
  regimeFamily,
  relativeErrorPct,
} from "../../data/meltPoolLiteratureCases";
import { buildGoldakCaeCard } from "../../utils/goldakCaeCard";
import { literatureErrorUnavailableText } from "../../utils/meltPoolExtentStatus";
import { MeltPoolExtentNotice } from "../MeltPoolExtentNotice";
import { DepthBiasNotice } from "../DepthBiasNotice";
import { STRESS_PROXY_LABEL, STRESS_PROXY_UNIT_NOTE } from "../../utils/residualStressYieldCheck";
import { resolveDepthBiasWarning } from "../../utils/depthBiasWarning";
import { PublishedTrackBands } from "../PublishedTrackBands";
import { HowCalculated } from "../HowCalculated";
import { DISTORTION_HEURISTIC_NOTE } from "../../utils/distortionHeuristic";
import { SolidificationQuantities } from "../SolidificationQuantities";

export interface MeltPool3DCrossSectionProps {
  initialPower_W?: number;
  initialSpeed_mms?: number;
  initialBeamDiameter_um?: number;
  initialPreheat_C?: number;
  initialLayer_um?: number;
  initialHatch_um?: number;
  initialMaterial?: string;
  onParametersChange?: (params: {
    laserPower_W: number;
    scanSpeed_mm_s: number;
    beamDiameter_um: number;
    preheatTemp_C: number;
    layerThickness_um: number;
    hatchSpacing_um: number;
    material: string;
  }) => void;
}

export type SlicingPlane = "longitudinal-xz" | "transverse-yz" | "top-xy" | "isometric-3d" | "quarter-cutaway";

export const MeltPool3DCrossSectionLab: React.FC<MeltPool3DCrossSectionProps> = ({
  initialPower_W = 285,
  initialSpeed_mms = 960,
  initialBeamDiameter_um = 80,
  initialPreheat_C = 80,
  initialLayer_um = 40,
  initialHatch_um = 110,
  initialMaterial = "Inconel 718",
  onParametersChange,
}) => {
  // Laser & Process Parameters
  const [laserPower_W, setLaserPower_W] = useState<number>(initialPower_W);
  const [scanSpeed_mms, setScanSpeed_mms] = useState<number>(initialSpeed_mms);
  const [beamDiameter_um, setBeamDiameter_um] = useState<number>(initialBeamDiameter_um);
  const [preheatTemp_C, setPreheatTemp_C] = useState<number>(initialPreheat_C);
  const [layerThickness_um, setLayerThickness_um] = useState<number>(initialLayer_um);
  const [hatchSpacing_um, setHatchSpacing_um] = useState<number>(initialHatch_um);
  const [selectedMaterial, setSelectedMaterial] = useState<string>(initialMaterial);
  const [laserWavelength, setLaserWavelength] = useState<"IR_1064nm" | "Green_515nm" | "Blue_450nm">("IR_1064nm");
  const [heatSource, setHeatSource] = useState<"goldak" | "eagar-tsai" | "rosenthal">("goldak");
  const [sulfurPpm, setSulfurPpm] = useState<number>(15);

  // 3D Visualization Controls
  const [slicingPlane, setSlicingPlane] = useState<SlicingPlane>("quarter-cutaway");
  const [sliceCutOffset, setSliceCutOffset] = useState<number>(0); // -100 to +100 um
  const [showIsotherms, setShowIsotherms] = useState<boolean>(true);
  const [showPowderBed, setShowPowderBed] = useState<boolean>(true);
  const [showLaserRays, setShowLaserRays] = useState<boolean>(true);
  const [wireframeMode, setWireframeMode] = useState<boolean>(false);
  const [autoRotate, setAutoRotate] = useState<boolean>(false);

  // Python Engine State
  const [pyResult, setPyResult] = useState<PythonLPBFResult | null>(null);
  const [isSolving, setIsSolving] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Three.js Mount Ref
  const threeMountRef = useRef<HTMLDivElement | null>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const controlsGroupRef = useRef<THREE.Group | null>(null);
  const contentGroupRef = useRef<THREE.Group | null>(null);
  // Per-frame render callback owned by the scene effect; driven only while the workspace is visible.
  const renderFrameRef = useRef<(() => void) | null>(null);
  useVisibleAnimationFrame(() => renderFrameRef.current?.());
  const autoRotateRef = useRef(autoRotate);
  autoRotateRef.current = autoRotate;

  useEffect(() => {
    setLaserPower_W(initialPower_W);
    setScanSpeed_mms(initialSpeed_mms);
    setBeamDiameter_um(initialBeamDiameter_um);
    setPreheatTemp_C(initialPreheat_C);
    setLayerThickness_um(initialLayer_um);
    setHatchSpacing_um(initialHatch_um);
    setSelectedMaterial(initialMaterial);
  }, [
    initialPower_W,
    initialSpeed_mms,
    initialBeamDiameter_um,
    initialPreheat_C,
    initialLayer_um,
    initialHatch_um,
    initialMaterial,
  ]);

  // Late analytical responses cannot roll back a newer shared process vector.
  const solveGeneration = useRef(0);
  // Research panel (P8 4.6): signature of the inputs that produced pyResult, so a served number is shown beside a research
  // one only when both come from the same inputs. A ref write only; it sends nothing.
  const servedResearchSignatureRef = useRef<string | null>(null);
  const onParametersChangeRef = useRef(onParametersChange);
  onParametersChangeRef.current = onParametersChange;
  const sharedInputSignature = JSON.stringify([initialPower_W, initialSpeed_mms, initialBeamDiameter_um, initialPreheat_C, initialLayer_um, initialHatch_um, initialMaterial]);
  const latestSharedInput = useRef(sharedInputSignature);
  latestSharedInput.current = sharedInputSignature;
  // Execute Python Solver
  const solvePhysics = useCallback(async () => {
    const generation=++solveGeneration.current;
    const sharedAtStart=latestSharedInput.current;
    setIsSolving(true);
    setErrorMsg(null);
    try {
      const res = await pythonComputationService.solveLPBFThermalPhysics({
        material: selectedMaterial,
        laserPower_W,
        scanSpeed_mm_s: scanSpeed_mms,
        beamDiameter_um,
        preheatTemp_C,
        layerThickness_um,
        hatchSpacing_um,
        laserWavelength,
        heatSource,
        sulfur_ppm: sulfurPpm,
      });
      if (!res?.meltPoolGeometry || !res?.processParameters || !res?.hydrodynamicsAndRecoil) {
        throw new Error("Analytical melt pool response is incomplete.");
      }
      if(generation!==solveGeneration.current||sharedAtStart!==latestSharedInput.current)return;
      servedResearchSignatureRef.current = researchProcessSignature({ material: selectedMaterial, laserPower_W, scanSpeed_mm_s: scanSpeed_mms, beamDiameter_um, preheatTemp_C, laserWavelength });
      setPyResult(res);

      if (onParametersChangeRef.current) {
        onParametersChangeRef.current({
          laserPower_W,
          scanSpeed_mm_s: scanSpeed_mms,
          beamDiameter_um,
          preheatTemp_C,
          layerThickness_um,
          hatchSpacing_um,
          material: selectedMaterial,
        });
      }
    } catch (err: any) {
      if(generation!==solveGeneration.current||sharedAtStart!==latestSharedInput.current)return;
      console.warn("Python LPBF Thermal Solver Error:", err);
      setErrorMsg(err.message || "Failed to execute Python thermal solver.");
    } finally {
      if(generation===solveGeneration.current)setIsSolving(false);
    }
  }, [
    selectedMaterial,
    laserPower_W,
    scanSpeed_mms,
    beamDiameter_um,
    preheatTemp_C,
    layerThickness_um,
    hatchSpacing_um,
    laserWavelength,
    heatSource,
    sulfurPpm,
  ]);

  // Request values of the Research model panel: the lab's own process state, no copy kept elsewhere.
  const researchInput = useMemo<ResearchHostInput>(() => ({
    material: selectedMaterial,
    laserPower_W,
    scanSpeed_mm_s: scanSpeed_mms,
    beamDiameter_um,
    preheatTemp_C,
    laserWavelength,
    propertyContext: { kind: "nominal" },
  }), [selectedMaterial, laserPower_W, scanSpeed_mms, beamDiameter_um, preheatTemp_C, laserWavelength]);

  // Debounced execution on parameter changes
  useEffect(() => {
    const timer = setTimeout(() => {
      solvePhysics();
    }, 200);
    return () => {clearTimeout(timer);solveGeneration.current++;};
  }, [solvePhysics]);

  // Regime from the solver only (ΔH/hs 15 / 20, repo convention). Do not recompute a second threshold.
  const regimeInfo = useMemo(() => {
    const enthalpy = pyResult?.processParameters?.normalizedEnthalpy ?? 0;
    const d_over_w = pyResult?.meltPoolGeometry?.depthToWidthRatio_D_over_W ?? 0;
    const family = regimeFamily(pyResult?.meltPoolGeometry?.regime || "Conduction");
    const isKeyhole = family === "Keyhole";
    const isTransition = family === "Transition";
    const isConduction = family === "Conduction";

    const modeName = isKeyhole ? "Keyhole-mode screening indicator" : isTransition ? "Transition screening indicator" : "Conduction assumption (screening)";
    let badgeColor = "bg-emerald-500/20 text-emerald-300 border-emerald-500/40";
    const sourceLabel =
      heatSource === "goldak" ? "Goldak double-ellipsoid" : heatSource === "eagar-tsai" ? "Eagar–Tsai Gaussian" : "regularized Rosenthal";
    // Per-alloy keyhole cut served by the solver (20; Inconel 625 13.6, which leaves no transition band).
    const servedCut = pyResult?.meltPoolGeometry?.regimeKeyholeThreshold;
    const keyholeCut = typeof servedCut === "number" && Number.isFinite(servedCut) ? servedCut : 20;
    let desc = `Analytical conduction estimate. Width and depth from the T = T_liquidus isotherm of a ${sourceLabel} field (ΔH/hs < ${Math.min(15, keyholeCut)}).`;
    let keyRisk = "Low screening indicator — unvalidated";

    if (isKeyhole) {
      badgeColor = "bg-rose-500/20 text-rose-300 border-rose-500/50 shadow-[0_0_12px_rgba(244,63,94,0.3)]";
      const onset = keyholeCut !== 20
        ? `ΔH/hs ≥ ${keyholeCut}, this alloy's own cut, see the alloy note; melt-pool D/W > 0.5`
        : "ΔH/hs ≥ 20, a provisional screening choice; melt-pool D/W > 0.5, King 2014 / Cunningham 2019 converted to this index";
      desc = `Keyhole-mode onset (${onset}). The ${sourceLabel} conduction estimate and Fabbro depth proxy do not resolve a cavity or pore entrapment. Keyhole mode is not keyhole porosity.`;
      keyRisk = "Keyhole-mode screening indicator";
    } else if (isTransition) {
      badgeColor = "bg-amber-500/20 text-amber-300 border-amber-500/40";
      desc = `Transition band (15 ≤ ΔH/hs < 20). ${sourceLabel} conduction estimate; free-surface shape unresolved.`;
      keyRisk = "Moderate / Near Threshold";
    }

    const materialNote = pyResult?.meltPoolGeometry?.regimeMaterialNote;
    if (materialNote) desc += ` Alloy note: ${materialNote}.`;
    const depthBias = resolveDepthBiasWarning(pyResult?.meltPoolGeometry, pyResult?.material, pyResult?.processParameters?.heatSource, pyResult?.processParameters?.normalizedEnthalpy);
    if (depthBias.text) desc += ` ${depthBias.text}`;

    return {
      enthalpy: parseFloat(enthalpy.toFixed(2)),
      d_over_w: parseFloat(Number(d_over_w).toFixed(2)),
      isKeyhole,
      isTransition,
      isConduction,
      modeName,
      badgeColor,
      desc,
      keyRisk,
    };
  }, [pyResult, heatSource]);

  // Persist renderer / camera; only rebuild melt-pool content when results change.
  useEffect(() => {
    const container = threeMountRef.current;
    if (!container) return;

    const width = container.clientWidth || 600;
    const height = container.clientHeight || 450;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x060913);
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(40, width / height, 1, 3000);
    camera.position.set(240, 160, 260);
    camera.lookAt(0, -15, 0);
    cameraRef.current = camera;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.localClippingEnabled = true;
    rendererRef.current = renderer;
    container.innerHTML = "";
    container.appendChild(renderer.domElement);

    scene.add(new THREE.AmbientLight(0xffffff, 0.65));
    const dirLight1 = new THREE.DirectionalLight(0xffeedd, 1.4);
    dirLight1.position.set(200, 300, 150);
    scene.add(dirLight1);
    const dirLight2 = new THREE.DirectionalLight(0x38bdf8, 0.7);
    dirLight2.position.set(-200, -100, -150);
    scene.add(dirLight2);

    const rootGroup = new THREE.Group();
    scene.add(rootGroup);
    controlsGroupRef.current = rootGroup;

    const content = new THREE.Group();
    rootGroup.add(content);
    contentGroupRef.current = content;

    let isDragging = false;
    let prevMouseX = 0;
    let prevMouseY = 0;
    const handleMouseDown = (e: MouseEvent) => {
      isDragging = true;
      prevMouseX = e.clientX;
      prevMouseY = e.clientY;
    };
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging || !controlsGroupRef.current) return;
      controlsGroupRef.current.rotation.y += (e.clientX - prevMouseX) * 0.008;
      controlsGroupRef.current.rotation.x += (e.clientY - prevMouseY) * 0.008;
      prevMouseX = e.clientX;
      prevMouseY = e.clientY;
    };
    const handleMouseUp = () => {
      isDragging = false;
    };
    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
      if (!cameraRef.current) return;
      cameraRef.current.fov = Math.max(15, Math.min(85, cameraRef.current.fov + e.deltaY * 0.04));
      cameraRef.current.updateProjectionMatrix();
    };

    const resizeObserver = new ResizeObserver((entries) => {
      const cr = entries[0]?.contentRect;
      if (!cr || !cameraRef.current || !rendererRef.current) return;
      const w = Math.max(1, cr.width);
      const h = Math.max(1, cr.height);
      cameraRef.current.aspect = w / h;
      cameraRef.current.updateProjectionMatrix();
      rendererRef.current.setSize(w, h);
    });
    resizeObserver.observe(container);

    const domElement = renderer.domElement;
    domElement.addEventListener("mousedown", handleMouseDown);
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    domElement.addEventListener("wheel", handleWheel, { passive: false });

    const animate = () => {
      if (autoRotateRef.current && controlsGroupRef.current) {
        controlsGroupRef.current.rotation.y += 0.006;
      }
      renderer.render(scene, camera);
    };
    renderFrameRef.current = animate;
    animate();

    return () => {
      renderFrameRef.current = null;
      resizeObserver.disconnect();
      domElement.removeEventListener("mousedown", handleMouseDown);
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
      domElement.removeEventListener("wheel", handleWheel);
      if (contentGroupRef.current) disposeObject3D(contentGroupRef.current);
      renderer.dispose();
      if (container.contains(domElement)) container.removeChild(domElement);
    };
  }, []);

  useEffect(() => {
    const content = contentGroupRef.current;
    const renderer = rendererRef.current;
    if (!content || !renderer) return;

    disposeObject3D(content);
    while (content.children.length) content.remove(content.children[0]);

    const geom = pyResult?.meltPoolGeometry;
    const af = geom?.goldakParameters?.semiAxis_af_front_um || beamDiameter_um * 0.9;
    const ar = geom?.goldakParameters?.semiAxis_ar_rear_um || beamDiameter_um * 2.8;
    const b = geom?.goldakParameters?.semiAxis_b_halfwidth_um || beamDiameter_um * 0.75;
    const c = geom?.goldakParameters?.semiAxis_c_depth_um || layerThickness_um * 1.8;

    // Clip axes match the mesh: X = scan, Y = depth (negative down), Z = hatch.
    const localClippingPlanes: THREE.Plane[] = [];
    if (slicingPlane === "longitudinal-xz") {
      localClippingPlanes.push(new THREE.Plane(new THREE.Vector3(0, 0, 1), -sliceCutOffset));
    } else if (slicingPlane === "transverse-yz") {
      localClippingPlanes.push(new THREE.Plane(new THREE.Vector3(1, 0, 0), -sliceCutOffset));
    } else if (slicingPlane === "top-xy") {
      localClippingPlanes.push(new THREE.Plane(new THREE.Vector3(0, -1, 0), sliceCutOffset));
    } else if (slicingPlane === "quarter-cutaway") {
      localClippingPlanes.push(new THREE.Plane(new THREE.Vector3(0, 0, 1), 0));
    }

    // 4. Substrate & Powder Bed Block
    const blockWidth = 360;
    const blockLength = 480;
    const blockHeight = 160;

    // Solid Substrate Base Mesh
    const substrateGeom = new THREE.BoxGeometry(blockLength, blockHeight, blockWidth);
    const substrateMat = new THREE.MeshStandardMaterial({
      color: 0x0f172a,
      roughness: 0.85,
      metalness: 0.35,
      clippingPlanes: localClippingPlanes,
      clipShadows: true,
    });
    const substrateMesh = new THREE.Mesh(substrateGeom, substrateMat);
    substrateMesh.position.set(0, -blockHeight / 2, 0);
    content.add(substrateMesh);

    // Substrate Edge Wireframe
    const subEdges = new THREE.EdgesGeometry(substrateGeom);
    const subLineMat = new THREE.LineBasicMaterial({ color: 0x1e293b });
    const subLine = new THREE.LineSegments(subEdges, subLineMat);
    subLine.position.set(0, -blockHeight / 2, 0);
    content.add(subLine);

    // 5. Powder Layer Top Sheet (z = -layerThickness)
    if (showPowderBed) {
      const powderThickness = layerThickness_um;
      const powderGeom = new THREE.BoxGeometry(blockLength, powderThickness, blockWidth);
      const powderMat = new THREE.MeshStandardMaterial({
        color: 0x334155,
        roughness: 0.95,
        metalness: 0.1,
        transparent: true,
        opacity: 0.65,
        clippingPlanes: localClippingPlanes,
      });
      const powderMesh = new THREE.Mesh(powderGeom, powderMat);
      powderMesh.position.set(0, -powderThickness / 2, 0);
      content.add(powderMesh);

      // Powder Layer Boundary Line
      const layerLineGeom = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(-blockLength / 2, -powderThickness, -blockWidth / 2),
        new THREE.Vector3(blockLength / 2, -powderThickness, -blockWidth / 2),
        new THREE.Vector3(blockLength / 2, -powderThickness, blockWidth / 2),
        new THREE.Vector3(-blockLength / 2, -powderThickness, blockWidth / 2),
      ]);
      const layerLineMat = new THREE.LineBasicMaterial({ color: 0xfbbf24 });
      const layerLine = new THREE.LineLoop(layerLineGeom, layerLineMat);
      content.add(layerLine);
    }

    if (pyResult) {
      const meltPoolGeom = buildLoftedMeltPoolGeometry(pyResult);
      const meltPoolMat = new THREE.MeshStandardMaterial({
        vertexColors: true,
        roughness: 0.3,
        metalness: 0.8,
        wireframe: wireframeMode,
        side: THREE.DoubleSide,
        clippingPlanes: localClippingPlanes,
        clipShadows: true,
      });
      content.add(new THREE.Mesh(meltPoolGeom, meltPoolMat));
    }

    if (showIsotherms && pyResult) {
      const longC = pyResult.geometricContours.longitudinalXZ;
      const transC = pyResult.geometricContours.transverseYZ;
      const scales = [
        { s: 1.0, color: 0xf97316, name: "liquidus" },
        { s: 1.12, color: 0xfbbf24, name: "solidus" },
        { s: 1.28, color: 0xa855f7, name: "haz" },
      ];
      for (const iso of scales) {
        if (longC.length > 2) {
          const pts = longC.map((p) => new THREE.Vector3(p.x_um * iso.s, -p.z_depth_um * iso.s, 0));
          const lg = new THREE.BufferGeometry().setFromPoints(pts);
          content.add(new THREE.Line(lg, new THREE.LineBasicMaterial({ color: iso.color })));
        }
        if (transC.length > 2) {
          const pts = transC.map((p) => new THREE.Vector3(0, -p.z_depth_um * iso.s, p.y_um * iso.s));
          const tg = new THREE.BufferGeometry().setFromPoints(pts);
          content.add(new THREE.Line(tg, new THREE.LineBasicMaterial({ color: iso.color })));
        }
      }
    }

    if (slicingPlane === "longitudinal-xz" && pyResult) {
      const facePts = [
        new THREE.Vector2(pyResult.geometricContours.longitudinalXZ[0]?.x_um ?? -af, 0),
        ...pyResult.geometricContours.longitudinalXZ.map((p) => new THREE.Vector2(p.x_um, -p.z_depth_um)),
        new THREE.Vector2(pyResult.geometricContours.longitudinalXZ.at(-1)?.x_um ?? ar, 0),
      ];
      const face = contourToCutFace(facePts, 0x38bdf8);
      if (face) {
        face.rotation.y = 0;
        content.add(face);
      }
    }
    if (slicingPlane === "transverse-yz" && pyResult) {
      const facePts = [
        new THREE.Vector2(pyResult.geometricContours.transverseYZ[0]?.y_um ?? -b, 0),
        ...pyResult.geometricContours.transverseYZ.map((p) => new THREE.Vector2(p.y_um, -p.z_depth_um)),
        new THREE.Vector2(pyResult.geometricContours.transverseYZ.at(-1)?.y_um ?? b, 0),
      ];
      const face = contourToCutFace(facePts, 0xf59e0b);
      if (face) {
        face.rotation.y = Math.PI / 2;
        content.add(face);
      }
    }

    if ((slicingPlane === "transverse-yz" || slicingPlane === "quarter-cutaway") && pyResult) {
      pyResult.geometricContours.multiTrackHatchOverlap.forEach((track) => {
        if (track.y_center_um === 0) return;
        const pts = track.contour.map((p) => new THREE.Vector3(0, -p.z_depth_um, p.y_um));
        if (pts.length < 2) return;
        const tg = new THREE.BufferGeometry().setFromPoints(pts);
        content.add(new THREE.Line(tg, new THREE.LineBasicMaterial({ color: 0x38bdf8, transparent: true, opacity: 0.45 })));
      });
    }

    // No cavity or trapped pore rendering: free surface is unresolved.

    // 8. LASER BEAM & MULTI-REFLECTION OPTICAL RAYS
    if (showLaserRays) {
      // Main Laser Cylinder Beam
      const r_beam = beamDiameter_um / 2;
      const beamHeight = 180;
      const beamGeom = new THREE.CylinderGeometry(r_beam * 0.8, r_beam, beamHeight, 32, 1, true);
      beamGeom.translate(0, beamHeight / 2, 0);

      const beamMat = new THREE.MeshBasicMaterial({
        color: laserWavelength === "Green_515nm" ? 0x10b981 : laserWavelength === "Blue_450nm" ? 0x38bdf8 : 0xf43f5e,
        transparent: true,
        opacity: 0.35,
        side: THREE.DoubleSide,
      });
      const beamMesh = new THREE.Mesh(beamGeom, beamMat);
      content.add(beamMesh);

      // Central Laser Core Line
      const coreGeom = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(0, beamHeight, 0),
        new THREE.Vector3(0, 0, 0),
      ]);
      const coreMat = new THREE.LineBasicMaterial({
        color: 0xffffff,
        linewidth: 2,
      });
      const coreLine = new THREE.Line(coreGeom, coreMat);
      content.add(coreLine);

    }

    // No velocity field is solved; Marangoni screening remains numerical only.

    // 10. SCAN VELOCITY VECTOR ARROW
    const scanDir = new THREE.Vector3(1, 0, 0);
    const scanOrigin = new THREE.Vector3(af + 25, 0, 0);
    const scanArrow = new THREE.ArrowHelper(scanDir, scanOrigin, 60, 0x10b981, 14, 8);
    content.add(scanArrow);

    // 11. Coordinate Axes Helper & Floor Grid
    const grid = new THREE.GridHelper(blockLength, 20, 0x0284c7, 0x1e293b);
    grid.position.y = -blockHeight;
    content.add(grid);

  }, [
    pyResult,
    slicingPlane,
    sliceCutOffset,
    showIsotherms,
    showPowderBed,
    showLaserRays,
    wireframeMode,
    laserPower_W,
    beamDiameter_um,
    layerThickness_um,
    laserWavelength,
    regimeInfo,
  ]);

  // Preset Configurations
  const applyPreset = (preset: "conduction-safe" | "transition-deep" | "keyhole-danger" | "lack-of-fusion") => {
    if (preset === "conduction-safe") {
      setLaserPower_W(220);
      setScanSpeed_mms(1100);
      setBeamDiameter_um(80);
      setLayerThickness_um(40);
      setHatchSpacing_um(100);
    } else if (preset === "transition-deep") {
      setLaserPower_W(320);
      setScanSpeed_mms(900);
      setBeamDiameter_um(80);
      setLayerThickness_um(40);
      setHatchSpacing_um(105);
    } else if (preset === "keyhole-danger") {
      setLaserPower_W(480);
      setScanSpeed_mms(450);
      setBeamDiameter_um(65);
      setLayerThickness_um(40);
      setHatchSpacing_um(120);
    } else if (preset === "lack-of-fusion") {
      setLaserPower_W(140);
      setScanSpeed_mms(1600);
      setBeamDiameter_um(100);
      setLayerThickness_um(60);
      setHatchSpacing_um(150);
    }
  };

  // Export Goldak FEA DFLUX Card
  const exportGoldakCard = () => {
    if (!pyResult) return;
    const { text: feaCard, filename } = buildGoldakCaeCard(pyResult, "cross-section");

    const blob = new Blob([feaCard], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-4 font-mono text-xs">
      <LpbfEngineeringSimulation input={{ material: selectedMaterial, power_W: laserPower_W, speed_mm_s: scanSpeed_mms, beamDiameter_um, preheat_C: preheatTemp_C, layer_um: layerThickness_um, hatch_um: hatchSpacing_um }} />
      <details className="rounded-xl border border-slate-800 p-4"><summary className="cursor-pointer text-sm font-sans text-slate-300">Analytical screening studio · Rosenthal / Goldak / Eagar–Tsai / Fabbro / Marangoni</summary>
      {/* HEADER BAR & REGIME STATUS */}
      <div className="p-4 rounded-2xl bg-[#090e18] border border-[#1e2d46] space-y-3 shadow-xl relative overflow-hidden">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 relative z-10">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-gradient-to-tr from-amber-500 via-rose-500 to-indigo-600 text-white shadow-[0_0_20px_rgba(245,158,11,0.35)] border border-amber-400/40">
              <Flame className="w-5 h-5 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm sm:text-base font-bold text-white tracking-wide">
                  Analytical Screening Geometry · Melt Pool Studio
                </h3>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-sky-500/20 text-sky-300 border border-sky-500/40 flex items-center gap-1">
                  <Cpu className="w-3 h-3 text-sky-400" />
                  {pyResult?.modelId ||
                    (heatSource === "goldak" ? "goldak-half-space-v3" : heatSource === "eagar-tsai" ? "eagar-tsai-v2" : "rosenthal-screening-v1")}
                </span>
              </div>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Goldak / Eagar–Tsai / Rosenthal. Fabbro keyhole uses the tabulated flat-plate absorptivity (no double-counted trapping). Heiple–Roper Marangoni is screening, not CFD. Build Job stays Rosenthal.
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div className="flex rounded-xl border border-slate-700 overflow-hidden">
              <button
                type="button"
                onClick={() => setHeatSource("goldak")}
                className={`px-2.5 py-2 text-[10px] font-bold ${
                  heatSource === "goldak" ? "bg-sky-600 text-white" : "bg-[#050810] text-slate-300 hover:bg-slate-800"
                }`}
              >
                Goldak
              </button>
              <button
                type="button"
                onClick={() => setHeatSource("eagar-tsai")}
                className={`px-2.5 py-2 text-[10px] font-bold ${
                  heatSource === "eagar-tsai" ? "bg-sky-600 text-white" : "bg-[#050810] text-slate-300 hover:bg-slate-800"
                }`}
              >
                Eagar–Tsai
              </button>
              <button
                type="button"
                onClick={() => setHeatSource("rosenthal")}
                className={`px-2.5 py-2 text-[10px] font-bold ${
                  heatSource === "rosenthal" ? "bg-sky-600 text-white" : "bg-[#050810] text-slate-300 hover:bg-slate-800"
                }`}
              >
                Rosenthal
              </button>
            </div>
            <button
              type="button"
              onClick={solvePhysics}
              disabled={isSolving}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-sky-600 hover:bg-sky-500 text-white font-bold transition shadow-[0_0_15px_rgba(2,132,199,0.3)] disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isSolving ? "animate-spin" : ""}`} />
              <span>{isSolving ? "Computing..." : "Re-Solve (Python)"}</span>
            </button>

            <button
              type="button"
              onClick={exportGoldakCard}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-[#050810] hover:bg-slate-800 text-slate-200 border border-slate-700 transition"
              title="Export Goldak parameter card for a user DFLUX subroutine (not an input deck)"
            >
              <Download className="w-3.5 h-3.5 text-sky-400" />
              <span>Goldak CAE card (.goldak.txt)</span>
            </button>
          </div>
        </div>

        {errorMsg && (
          <div className="p-2.5 rounded-xl border border-rose-500/40 bg-rose-500/10 text-rose-200 text-[11px]">
            Solver error: {errorMsg}
          </div>
        )}

        {/* Dynamic Transition Banner */}
        <div className={`p-2.5 rounded-xl border flex flex-col md:flex-row md:items-center justify-between gap-2 ${regimeInfo.badgeColor}`}>
          <div className="flex items-start gap-2.5">
            <ShieldAlert className="w-5 h-5 shrink-0 mt-0.5" />
            <div>
              <div className="flex items-center gap-2 font-bold text-xs">
                <span>{regimeInfo.modeName}</span>
                <span className="text-[10px] opacity-80">(Normalized Enthalpy ΔH/h_s = {regimeInfo.enthalpy})</span>
              </div>
              <p className="text-[11px] opacity-90 mt-0.5 font-sans leading-relaxed">
                {regimeInfo.desc}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <div className="text-right">
              <span className="text-[10px] opacity-75 block">D/W Ratio:</span>
              <strong className="text-xs">{regimeInfo.d_over_w}</strong>
            </div>
            <div className="text-right border-l border-current/30 pl-2">
              <span className="text-[10px] opacity-75 block">Risk Status:</span>
              <strong className="text-xs">{regimeInfo.keyRisk}</strong>
            </div>
            {pyResult?.keyholeModel?.fabbroDepth_um != null && (
              <div className="text-right border-l border-current/30 pl-2">
                <span className="text-[10px] opacity-75 block">Fabbro e:</span>
                <strong className="text-xs">{pyResult.keyholeModel.fabbroDepth_um} μm</strong>
              </div>
            )}
            {pyResult?.marangoniModel?.flowDirection && (
              <div className="text-right border-l border-current/30 pl-2">
                <span className="text-[10px] opacity-75 block">Marangoni:</span>
                <strong className="text-xs capitalize">{pyResult.marangoniModel.flowDirection}</strong>
              </div>
            )}
          </div>
        </div>

        {pyResult && <HowCalculated explainerId="enthalpy-gates" result={pyResult} />}

        {/* Presets Quick Bar */}
        <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-slate-800/80">
          <span className="text-[10px] text-slate-400">Regime Presets:</span>
          <button
            type="button"
            onClick={() => applyPreset("conduction-safe")}
            className="px-2 py-1 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-[10px] transition"
          >
            Conduction screening
          </button>
          <button
            type="button"
            onClick={() => applyPreset("transition-deep")}
            className="px-2 py-1 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 text-[10px] transition"
          >
            ⚠️ Transition Mode
          </button>
          <button
            type="button"
            onClick={() => applyPreset("keyhole-danger")}
            className="px-2 py-1 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/30 text-[10px] transition"
          >
            Keyhole-mode preset (porosity screen: High)
          </button>
          <button
            type="button"
            onClick={() => applyPreset("lack-of-fusion")}
            className="px-2 py-1 rounded-lg bg-purple-500/10 hover:bg-purple-500/20 text-purple-300 border border-purple-500/30 text-[10px] transition"
          >
            ⚡ Lack of Fusion
          </button>
        </div>
      </div>

      <details className="p-3.5 rounded-xl bg-[#090e18] border border-[#162032]">
        <summary className="cursor-pointer list-none flex items-center justify-between text-[11px] font-bold text-slate-200">
          <span>
            Melt-pool knobs · {selectedMaterial} · {laserPower_W} W · {scanSpeed_mms} mm/s
          </span>
          <span className="text-slate-500 font-normal">expand</span>
        </summary>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-8 gap-3 pt-3">
        {/* Material */}
        <div className="space-y-1">
          <label className="text-[10px] text-slate-400">Alloy Material</label>
          <select
            aria-label="Analytical material"
            value={selectedMaterial}
            onChange={(e) => setSelectedMaterial(e.target.value)}
            className="w-full bg-[#050810] text-slate-200 border border-slate-700 rounded-lg px-2 py-1 text-xs focus:border-sky-500 outline-none"
          >
            <option value="Inconel 718">Inconel 718 (Ni-Cr-Fe)</option>
            <option value="Ti-6Al-4V">Ti-6Al-4V Grade 5</option>
            <option value="316L Stainless Steel">316L Stainless Steel</option>
            <option value="AlSi10Mg">AlSi10Mg (Al-Si)</option>
            <option value="CoCrMo">CoCrMo (Bio/Aero)</option>
            <option value="Scalmalloy (Al-Mg-Sc-Zr)">Scalmalloy (Sc-Zr)</option>
            <option value="Hastelloy X">Hastelloy X (Ni-Cr)</option>
            <option value="Pure Copper (Cu-OF)">Pure Copper (Cu-OF)</option>
          </select>
        </div>

        {/* Laser Power */}
        <div className="space-y-1">
          <div className="flex justify-between text-[10px]">
            <span className="text-slate-400">Power (P)</span>
            <span className="text-rose-400 font-bold">{laserPower_W} W</span>
          </div>
          <input
            type="range"
            min={80}
            max={600}
            step={10}
            aria-label="Analytical laser power in watts"
            value={laserPower_W}
            onChange={(e) => setLaserPower_W(Number(e.target.value))}
            className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-rose-500"
          />
        </div>

        {/* Scan Speed */}
        <div className="space-y-1">
          <div className="flex justify-between text-[10px]">
            <span className="text-slate-400">Speed (v)</span>
            <span className="text-emerald-400 font-bold">{scanSpeed_mms} mm/s</span>
          </div>
          <input
            type="range"
            min={200}
            max={2500}
            step={25}
            aria-label="Analytical scan speed in millimetres per second"
            value={scanSpeed_mms}
            onChange={(e) => setScanSpeed_mms(Number(e.target.value))}
            className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-emerald-500"
          />
        </div>

        {/* Beam Diameter */}
        <div className="space-y-1">
          <div className="flex justify-between text-[10px]">
            <span className="text-slate-400">Beam Diameter (d)</span>
            <span className="text-sky-400 font-bold">{beamDiameter_um} μm</span>
          </div>
          <input
            type="range"
            min={40}
            max={150}
            step={5}
            aria-label="Analytical beam diameter in micrometres"
            value={beamDiameter_um}
            onChange={(e) => setBeamDiameter_um(Number(e.target.value))}
            className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-sky-500"
          />
        </div>

        {/* Layer Thickness */}
        <div className="space-y-1">
          <div className="flex justify-between text-[10px]">
            <span className="text-slate-400">Layer Thickness (t)</span>
            <span className="text-amber-400 font-bold">{layerThickness_um} μm</span>
          </div>
          <input
            type="range"
            min={20}
            max={80}
            step={5}
            aria-label="Analytical layer thickness in micrometres"
            value={layerThickness_um}
            onChange={(e) => setLayerThickness_um(Number(e.target.value))}
            className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-amber-500"
          />
        </div>

        {/* Hatch Spacing */}
        <div className="space-y-1">
          <div className="flex justify-between text-[10px]">
            <span className="text-slate-400">Hatch Spacing (h)</span>
            <span className="text-purple-400 font-bold">{hatchSpacing_um} μm</span>
          </div>
          <input
            type="range"
            min={50}
            max={180}
            step={5}
            aria-label="Analytical hatch spacing in micrometres"
            value={hatchSpacing_um}
            onChange={(e) => setHatchSpacing_um(Number(e.target.value))}
            className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-purple-500"
          />
        </div>

        {/* Laser Wavelength */}
        <div className="space-y-1">
          <label className="text-[10px] text-slate-400">Laser Source</label>
          <select
            aria-label="Analytical laser wavelength"
            value={laserWavelength}
            onChange={(e) => setLaserWavelength(e.target.value as any)}
            className="w-full bg-[#050810] text-slate-200 border border-slate-700 rounded-lg px-2 py-1 text-xs focus:border-sky-500 outline-none"
          >
            <option value="IR_1064nm">IR Fiber (1064 nm)</option>
            <option value="Green_515nm">Green (515 nm - Cu/Al)</option>
            <option value="Blue_450nm" disabled>Blue (450 nm — material absorptivity unavailable)</option>
          </select>
        </div>

        <div className="space-y-1">
          <div className="flex justify-between text-[10px]">
            <span className="text-slate-400">Sulfur (Heiple–Roper)</span>
            <span className="text-teal-300 font-bold">{sulfurPpm} ppm</span>
          </div>
          <input
            type="range"
            min={0}
            max={100}
            step={5}
            aria-label="Sulfur concentration in ppm"
            value={sulfurPpm}
            onChange={(e) => setSulfurPpm(Number(e.target.value))}
            className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-teal-500"
          />
        </div>
        </div>
      </details>

      {/* 3D VIEWPORT & SLICING CONTROLS */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* LEFT: 3D WebGL Canvas Viewport (8 Cols) */}
        <div className="lg:col-span-8 space-y-3">
          <div className="p-3 rounded-2xl bg-[#090e18] border border-[#162032] space-y-3">
            {/* Viewport Slicing Mode Tabs */}
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-2.5">
              <div className="flex items-center gap-1 bg-[#050810] p-1 rounded-xl border border-slate-800">
                <button
                  type="button"
                  onClick={() => setSlicingPlane("quarter-cutaway")}
                  className={`px-2.5 py-1 rounded-lg text-xs transition ${
                    slicingPlane === "quarter-cutaway"
                      ? "bg-sky-500/20 text-sky-300 font-bold border border-sky-500/40"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  Quarter Cutaway (3/4)
                </button>
                <button
                  type="button"
                  onClick={() => setSlicingPlane("longitudinal-xz")}
                  className={`px-2.5 py-1 rounded-lg text-xs transition ${
                    slicingPlane === "longitudinal-xz"
                      ? "bg-sky-500/20 text-sky-300 font-bold border border-sky-500/40"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  Longitudinal Plane (X-Z)
                </button>
                <button
                  type="button"
                  onClick={() => setSlicingPlane("transverse-yz")}
                  className={`px-2.5 py-1 rounded-lg text-xs transition ${
                    slicingPlane === "transverse-yz"
                      ? "bg-sky-500/20 text-sky-300 font-bold border border-sky-500/40"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  Transverse Plane (Y-Z)
                </button>
                <button
                  type="button"
                  onClick={() => setSlicingPlane("top-xy")}
                  className={`px-2.5 py-1 rounded-lg text-xs transition ${
                    slicingPlane === "top-xy"
                      ? "bg-sky-500/20 text-sky-300 font-bold border border-sky-500/40"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  Top Surface (X-Y)
                </button>
              </div>

              {/* Toggles */}
              <div className="flex items-center gap-1.5 text-[11px]">
                <button
                  type="button"
                  onClick={() => setShowIsotherms(!showIsotherms)}
                  className={`px-2 py-1 rounded-lg border transition ${
                    showIsotherms ? "bg-orange-500/10 text-orange-300 border-orange-500/30" : "bg-slate-900 text-slate-500 border-slate-800"
                  }`}
                >
                  Isotherms
                </button>

                <button
                  type="button"
                  onClick={() => setShowLaserRays(!showLaserRays)}
                  className={`px-2 py-1 rounded-lg border transition ${
                    showLaserRays ? "bg-rose-500/10 text-rose-300 border-rose-500/30" : "bg-slate-900 text-slate-500 border-slate-800"
                  }`}
                >
                  Illustrative laser
                </button>
                <button
                  type="button"
                  onClick={() => setWireframeMode(!wireframeMode)}
                  className={`px-2 py-1 rounded-lg border transition ${
                    wireframeMode ? "bg-cyan-500/10 text-cyan-300 border-cyan-500/30" : "bg-slate-900 text-slate-500 border-slate-800"
                  }`}
                >
                  Mesh Wireframe
                </button>
                <button
                  type="button"
                  onClick={() => setAutoRotate(!autoRotate)}
                  className={`px-2 py-1 rounded-lg border transition ${
                    autoRotate ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/30" : "bg-slate-900 text-slate-500 border-slate-800"
                  }`}
                >
                  Auto Rotate
                </button>
              </div>
            </div>

            {/* 3D WebGL Canvas */}
            <div className="relative rounded-xl overflow-hidden border border-sky-500/30 bg-[#060913] shadow-[0_0_40px_rgba(14,165,233,0.12)]">
              <div
                ref={threeMountRef}
                id="melt-pool-3d-canvas"
                className="w-full h-[min(52vh,520px)] min-h-[320px] cursor-grab active:cursor-grabbing"
              />

              {/* Slicing Offset Slider Overlay */}
              {slicingPlane !== "quarter-cutaway" && (
                <div className="absolute bottom-3 left-3 right-3 p-2.5 rounded-xl bg-[#090e18]/90 backdrop-blur-md border border-slate-700/70 flex items-center gap-3">
                  <Scissors className="w-4 h-4 text-sky-400 shrink-0" />
                  <span className="text-[11px] text-slate-300 shrink-0">Section Plane Shift:</span>
                  <input aria-label="Section Plane Shift"
                    type="range"
                    min={-120}
                    max={120}
                    step={2}
                    value={sliceCutOffset}
                    onChange={(e) => setSliceCutOffset(Number(e.target.value))}
                    className="flex-1 h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-sky-500"
                  />
                  <span className="text-[11px] text-sky-300 font-bold font-mono w-16 text-right">
                    {sliceCutOffset > 0 ? `+${sliceCutOffset}` : sliceCutOffset} μm
                  </span>
                </div>
              )}

              {/* Floating Legend */}
              <div className="absolute top-3 left-3 p-2.5 rounded-xl bg-[#090e18]/90 backdrop-blur-md border border-slate-700/60 text-[10px] space-y-1 pointer-events-none">
                <div className="font-bold text-slate-200">Thermal Phase Envelopes</div>
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded bg-gradient-to-r from-rose-500 to-amber-500" />
                  <span className="text-slate-300">Liquid Melt Pool (T &ge; T_L)</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded bg-amber-500" />
                  <span className="text-slate-300">Mushy Solidification Front (T_S &le; T &lt; T_L)</span>
                </div>
                {regimeInfo.isKeyhole && (
                  <div className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded bg-rose-600 animate-pulse" />
                    <span className="text-rose-300 font-bold">Keyhole unresolved · screening indicator</span>
                  </div>
                )}
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded bg-purple-500" />
                  <span className="text-slate-300">Heat-Affected Zone (HAZ)</span>
                </div>
              </div>

              {/* Interactive Help */}
              <div className="absolute top-3 right-3 p-2 rounded-xl bg-[#090e18]/80 backdrop-blur-md border border-slate-800 text-[9px] text-slate-400 pointer-events-none">
                Drag with mouse to rotate 360° • Scroll wheel to zoom
              </div>
            </div>
          </div>
        </div>

        {/* RIGHT: Physics Readouts & Solidification Diagnostics (4 Cols) */}
        <div className="lg:col-span-4 space-y-3">
          {/* Melt Pool Physical Dimensions */}
          <div className="p-3.5 rounded-xl bg-[#090e18] border border-[#162032] space-y-3">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <div className="flex items-center gap-2">
                <Box className="w-4 h-4 text-sky-400" />
                <h4 className="text-xs font-bold text-white">Melt Pool Dimensions</h4>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-sky-500/20 text-sky-300 border border-sky-500/40">
                {pyResult?.heatSourceModel ?? pyResult?.modelId ?? heatSource} · screening
              </span>
            </div>

            {pyResult && (
              <div className="space-y-2 text-xs">
                <div className="grid grid-cols-3 gap-2 p-2 bg-[#050810] rounded-xl border border-slate-800">
                  <div className="text-center">
                    <span className="text-[10px] text-slate-400 block">Length (L)</span>
                    <strong className="text-sm text-sky-300">{pyResult.meltPoolGeometry.length_um} μm</strong>
                  </div>
                  <div className="text-center border-x border-slate-800">
                    <span className="text-[10px] text-slate-400 block">Width (W)</span>
                    <strong className="text-sm text-emerald-300">{pyResult.meltPoolGeometry.width_um} μm</strong>
                  </div>
                  <div className="text-center">
                    <span className="text-[10px] text-slate-400 block">Depth (D)</span>
                    <strong className="text-sm text-amber-300">{pyResult.meltPoolGeometry.depth_um} μm</strong>
                  </div>
                </div>
                <MeltPoolExtentNotice geometry={pyResult.meltPoolGeometry} />
                <DepthBiasNotice geometry={pyResult.meltPoolGeometry} material={pyResult.material} heatSource={pyResult.processParameters?.heatSource} enthalpy={pyResult.processParameters?.normalizedEnthalpy} />
                <PublishedTrackBands thermal={pyResult} />
                <HowCalculated explainerId="meltpool-geometry" result={pyResult} />

                <div className="space-y-1 text-[11px] text-slate-300">
                  <div className="flex justify-between py-0.5 border-b border-slate-800/60">
                    <span className="text-slate-400">Depth-to-Width Ratio (D/W):</span>
                    <span className="font-bold text-white">{pyResult.meltPoolGeometry.depthToWidthRatio_D_over_W}</span>
                  </div>
                  <div className="flex justify-between py-0.5 border-b border-slate-800/60">
                    <span className="text-slate-400">Aspect Ratio (L/W):</span>
                    <span className="font-bold text-white">{pyResult.meltPoolGeometry.aspectRatio_L_over_W}</span>
                  </div>
                  <div className="flex justify-between py-0.5 border-b border-slate-800/60">
                    <span className="text-slate-400">Fabbro depth proxy (screening):</span>
                    <span className="font-bold text-rose-400">{pyResult.meltPoolGeometry.keyholeVaporCavityDepth_um} μm</span>
                  </div>
                  <div className="flex justify-between py-0.5 border-b border-slate-800/60">
                    <span className="text-slate-400">Loss-free surface maximum (Eagar-Tsai):</span>
                    <span className="font-bold text-amber-300" title={pyResult.hydrodynamicsAndRecoil.peakUnavailableReason ?? undefined}>
                      {servedTemperatureText(pyResult.hydrodynamicsAndRecoil.peakTemperature_C)}
                    </span>
                  </div>
                  {pyResult.hydrodynamicsAndRecoil.peakUnavailableReason && (
                    <div className="py-0.5 border-b border-slate-800/60 text-[10px] text-slate-500" data-testid="peak-temperature-reason">
                      Peak not served: {pyResult.hydrodynamicsAndRecoil.peakUnavailableReason}
                    </div>
                  )}
                  {axialFieldMaximumText(pyResult.meltPoolGeometry.axialFieldMaximum_C) && (
                    <div className="py-0.5 border-b border-slate-800/60 text-[10px] text-slate-500" data-testid="axial-field-maximum">
                      Axial field maximum: {axialFieldMaximumText(pyResult.meltPoolGeometry.axialFieldMaximum_C)}.
                    </div>
                  )}
                  {peakTemperatureBasisLabel(pyResult) && (
                    <div className="py-0.5 border-b border-slate-800/60 text-[10px] text-slate-500" data-testid="peak-temperature-basis">
                      Peak basis: {peakTemperatureBasisLabel(pyResult)}; colour scale top {Math.round(colourScalePeak_C(pyResult, pyResult.thermalSlices?.liquidus_C ?? 1336))} °C
                      {colourScaleIsDisplayCap(pyResult, pyResult.thermalSlices?.liquidus_C ?? 1336) ? ` (${DISPLAY_CAP_LABEL})` : ""}.
                    </div>
                  )}
                  <div className="flex justify-between py-0.5 border-b border-slate-800/60">
                    <span className="text-slate-400">Surface T (equals the served peak; no clip):</span>
                    <span className="font-bold text-amber-200" title={pyResult.hydrodynamicsAndRecoil.surfaceTemperatureBasis}>
                      {servedTemperatureText(pyResult.hydrodynamicsAndRecoil.surfaceTemperature_C)}
                    </span>
                  </div>
                  <div className="flex justify-between py-0.5 border-b border-slate-800/60">
                    <span className="text-slate-400">Recoil pressure:</span>
                    <span className="font-bold text-rose-300" title={pyResult.hydrodynamicsAndRecoil.recoilPressureUnavailableReason ?? undefined}>
                      {typeof pyResult.hydrodynamicsAndRecoil.knudsenRecoilPressure_kPa === "number"
                        ? `${pyResult.hydrodynamicsAndRecoil.knudsenRecoilPressure_kPa} kPa (legacy payload)`
                        : "n/a (no wall closure)"}
                    </span>
                  </div>
                  {pyResult.hydrodynamicsAndRecoil.recoilOnsetStatus !== undefined && (
                    <div className="flex justify-between py-0.5 border-b border-slate-800/60">
                      <span className="text-slate-400">Recoil onset (Fabbro 2020 App A):</span>
                      <span className="font-bold text-rose-200 text-right max-w-[58%]" title={pyResult.hydrodynamicsAndRecoil.recoilOnsetBasis}>
                        {pyResult.hydrodynamicsAndRecoil.recoilOnsetStatus ?? `n/a (${pyResult.hydrodynamicsAndRecoil.recoilOnsetUnavailableReason ?? "not evaluated"})`}
                      </span>
                    </div>
                  )}
                  {pyResult.marangoniModel && (
                    <div className="flex justify-between py-0.5 border-b border-slate-800/60">
                      <span className="text-slate-400">Marangoni tendency (screening):</span>
                      <span className="font-bold text-teal-300 capitalize">
                        {pyResult.marangoniModel.flowDirection} @ {pyResult.marangoniModel.sulfur_ppm} ppm S
                      </span>
                    </div>
                  )}
                  <div className="flex justify-between py-0.5 border-b border-slate-800/60">
                    <span className="text-slate-400">Volumetric Energy Density (VED):</span>
                    <span className="font-bold text-sky-400">{pyResult.processParameters.volumetricEnergyDensity_J_mm3} J/mm³</span>
                  </div>
                  <div className="flex justify-between py-0.5">
                    <span className="text-slate-400">Peak Intensity (I0):</span>
                    <span className="font-bold text-rose-300">{pyResult.processParameters.peakIntensity_MW_cm2 ?? "—"} MW/cm²</span>
                  </div>
                  {pyResult.processParameters.absorptivityBasis && (
                    <p className="pt-1 text-[10px] leading-4 text-slate-500" data-testid="absorptivity-basis-3d">
                      Absorptivity (field) {pyResult.processParameters.effectiveAbsorptivity}: {pyResult.processParameters.absorptivityBasis}
                      {pyResult.processParameters.absorptivityIndexBasis ? ` Index ${pyResult.processParameters.indexAbsorptivity}: ${pyResult.processParameters.absorptivityIndexBasis}.` : ""}
                      {pyResult.processParameters.propertyConventionBasis ? ` Conduction k/cp ${pyResult.processParameters.effectiveConductivity_W_mK} W/m·K, ${pyResult.processParameters.effectiveSpecificHeat_J_kgK} J/kg·K: ${pyResult.processParameters.propertyConventionBasis}.` : ""}
                      {" "}Sourcing correction (P7b), not validation.
                    </p>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Opt-in calibrated mode: screening only, not validation; no control is rendered while no cell passes the held-out gate. */}
          <CalibratedMeltpoolPanel
            heatSource={heatSource}
            material={selectedMaterial}
            request={{ laserPower_W, scanSpeed_mm_s: scanSpeed_mms, beamDiameter_um, preheatTemp_C, layerThickness_um, hatchSpacing_um, laserWavelength, sulfur_ppm: sulfurPpm }}
          />

          {/* Research model: separate, collapsed, opt-in. Reads this lab's process values; writes nothing back. */}
          <ResearchModelPanel host="melt-pool" input={researchInput} served={pyResult} servedSignature={servedResearchSignatureRef.current} />

          {/* Solidification Kinetics & Microstructure */}
          <div className="p-3.5 rounded-xl bg-[#090e18] border border-[#162032] space-y-2.5">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4 text-emerald-400" />
                <h4 className="text-xs font-bold text-white">Solidification Kinetics &amp; Microstructure</h4>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                {pyResult?.solidificationKinetics.modelId}
              </span>
            </div>

            {pyResult && <SolidificationQuantities container={pyResult.solidificationKinetics} />}
          </div>

          {/* Multi-Defect Overlap Diagnostics */}
          <div className="p-3.5 rounded-xl bg-[#090e18] border border-[#162032] space-y-2.5">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-sky-400" />
                <h4 className="text-xs font-bold text-white">Defect &amp; Porosity Criteria</h4>
              </div>
            </div>

            {pyResult && (
              <div className="space-y-1.5 text-[10px]">
                <div className="flex items-center justify-between p-1.5 bg-[#050810] rounded-lg border border-slate-800">
                  <span className="text-slate-300">Lack of Fusion (LoF):</span>
                  <span className={`font-bold ${pyResult.defectDiagnostics.lackOfFusionStatus === "Pass" ? "text-emerald-400" : "text-rose-400"}`}>
                    {pyResult.defectDiagnostics.lackOfFusionRisk}
                  </span>
                </div>
                <div className="flex items-center justify-between p-1.5 bg-[#050810] rounded-lg border border-slate-800">
                  <span className="text-slate-300">Keyhole porosity (unresolved; legacy screen):</span>
                  <span className={`font-bold ${pyResult.defectDiagnostics.keyholePorosityRisk.startsWith("High") ? "text-rose-400" : pyResult.defectDiagnostics.keyholePorosityRisk.startsWith("Possible") ? "text-amber-400" : "text-emerald-400"}`}>
                    {pyResult.defectDiagnostics.keyholePorosityRisk}
                  </span>
                </div>
                <div className="flex items-center justify-between p-1.5 bg-[#050810] rounded-lg border border-slate-800">
                  <span className="text-slate-300">Balling Instability:</span>
                  <span className="font-bold text-slate-200">{pyResult.defectDiagnostics.ballingInstabilityRisk}</span>
                </div>
                <div className="flex items-center justify-between p-1.5 bg-[#050810] rounded-lg border border-slate-800">
                  <span className="text-slate-300" title={STRESS_PROXY_UNIT_NOTE}>{STRESS_PROXY_LABEL}:</span>
                  <span className="font-bold text-amber-300 text-right max-w-[58%]">{typeof pyResult.defectDiagnostics.effectiveResidualStress_MPa === "number" ? `${pyResult.defectDiagnostics.effectiveResidualStress_MPa} MPa-eq.` : `n/a (${pyResult.defectDiagnostics.stressUnavailableReason ?? "no sourced stress model"})`}</span>
                </div>
                <p data-testid="distortion-heuristic-note" className="text-[10px] leading-snug text-slate-500">
                  {DISTORTION_HEURISTIC_NOTE}
                </p>
              </div>
            )}
          </div>

          {pyResult && (
            <div className="p-3.5 rounded-xl bg-[#090e18] border border-[#162032] space-y-2">
              <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-sky-400" />
                  <h4 className="text-xs font-bold text-white">Literature Benchmarks</h4>
                </div>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-slate-300 border border-slate-600">
                  Measured DOI catalog
                </span>
              </div>
              <p className="text-[10px] text-slate-500 leading-relaxed">
                Published isolated single-track W/D with DOI (NIST AMB2022-03 Table 4, Guo 2024 Table 3). AlSi10Mg is an honest gap. Solver-echo sweeps are not benchmarks. Goldak/ET depth uses Fabbro with the tabulated flat-plate absorptivity; Marangoni does not refit W/D.
              </p>
              {MELT_POOL_LITERATURE_CASES.map((c) => {
                const loadable = isLoadableLiteratureCase(c);
                const same = matchesLoadableLiteratureCase(c, pyResult.material, pyResult.processParameters);
                const canScore =
                  same && c.publishedWidth_um != null && c.publishedDepth_um != null;
                // Only a computed liquidus isotherm may be scored against a published track.
                const errorExcluded = literatureErrorUnavailableText(pyResult.meltPoolGeometry);
                const wErr = canScore && errorExcluded === null
                  ? relativeErrorPct(pyResult.meltPoolGeometry.width_um, c.publishedWidth_um as number)
                  : 0;
                const dErr = canScore && errorExcluded === null
                  ? relativeErrorPct(pyResult.meltPoolGeometry.depth_um, c.publishedDepth_um as number)
                  : 0;
                const predFam = regimeFamily(pyResult.meltPoolGeometry.regime);
                const regimeOk = c.publishedRegime != null && predFam === c.publishedRegime;
                const kindLabel =
                  c.kind === "measured" ? "measured" : c.kind === "asymptotic" ? "asymptotic" : "no measured track";
                return (
                  <button
                    key={c.id}
                    type="button"
                    disabled={!loadable}
                    onClick={() => {
                      if (!loadable) return;
                      setSelectedMaterial(c.material);
                      setLaserPower_W(c.laserPower_W as number);
                      setScanSpeed_mms(c.scanSpeed_mm_s as number);
                      setBeamDiameter_um(c.beamDiameter_um as number);
                      setPreheatTemp_C(c.preheatTemp_C as number);
                      setLayerThickness_um(c.layerThickness_um as number);
                      setHatchSpacing_um(c.hatchSpacing_um as number);
                    }}
                    className={`w-full text-left p-2 rounded-lg border ${
                      same ? "border-sky-500/50 bg-sky-500/10" : "border-slate-800 bg-[#050810]"
                    } ${!loadable ? "opacity-80 cursor-default" : ""}`}
                  >
                    <div className="flex justify-between gap-2 text-[10px]">
                      <span className="text-slate-200 font-bold">{c.label}</span>
                      <span className={regimeOk && same ? "text-emerald-400" : "text-slate-400"}>
                        {!loadable
                          ? c.processScope === "bare-plate" ? "Bare-plate model unavailable" : "Gap"
                          : same
                            ? regimeOk
                              ? "Regime match"
                              : `Regime ${predFam} vs ${c.publishedRegime}`
                            : "Load case"}
                      </span>
                    </div>
                    <div className="text-[10px] text-slate-500 mt-0.5">
                      {kindLabel}{c.processScope === "bare-plate" ? " · bare plate · D4σ beam" : ""}
                      {loadable
                        ? ` · ${c.material} · ${c.laserPower_W} W · ${c.scanSpeed_mm_s} mm/s · DOI ${c.doi}`
                        : ` · ${c.material} · ${c.source}`}
                    </div>
                    {c.processScope === "bare-plate" && <p className="mt-1 text-[10px] text-slate-400">
                      Optical cross-section, n={c.measurementCount}: W {c.publishedWidth_um} ± {c.widthStdDev_um} µm; D {c.publishedDepth_um} ± {c.depthStdDev_um} µm (mean ± SD).
                    </p>}
                    {canScore && errorExcluded === null && (
                      <div className="mt-1 grid grid-cols-2 gap-1 text-[10px] text-slate-300">
                        <span>W {pyResult.meltPoolGeometry.width_um} vs {c.publishedWidth_um} μm ({wErr >= 0 ? "+" : ""}{wErr.toFixed(0)}%)</span>
                        <span>D {pyResult.meltPoolGeometry.depth_um} vs {c.publishedDepth_um} μm ({dErr >= 0 ? "+" : ""}{dErr.toFixed(0)}%)</span>
                      </div>
                    )}
                    {canScore && errorExcluded !== null && (
                      <div className="mt-1 text-[10px] text-amber-300" data-literature-error="excluded">
                        W / D vs published {c.publishedWidth_um} / {c.publishedDepth_um} μm: {errorExcluded}
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>
      </details>
    </div>
  );
};
