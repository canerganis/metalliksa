import * as THREE from "three";
import type { PythonLPBFResult } from "../../services/pythonComputationService";
import { colourScalePeak_C } from "../../utils/peakTemperatureDisplay";

export function interpolateHalfWidth(
  topDown: Array<{ x_um: number; y_um: number }>,
  x_um: number
): number {
  if (!topDown.length) return 0;
  const byX = new Map<number, number>();
  for (const p of topDown) {
    const prev = byX.get(p.x_um) ?? 0;
    byX.set(p.x_um, Math.max(prev, Math.abs(p.y_um)));
  }
  const xs = Array.from(byX.keys()).sort((a, b) => a - b);
  if (x_um <= xs[0]) return byX.get(xs[0]) ?? 0;
  if (x_um >= xs[xs.length - 1]) return byX.get(xs[xs.length - 1]) ?? 0;
  for (let i = 0; i < xs.length - 1; i++) {
    if (x_um >= xs[i] && x_um <= xs[i + 1]) {
      const t = (x_um - xs[i]) / Math.max(1e-6, xs[i + 1] - xs[i]);
      return (byX.get(xs[i]) ?? 0) * (1 - t) + (byX.get(xs[i + 1]) ?? 0) * t;
    }
  }
  return byX.get(xs[0]) ?? 0;
}

export function sampleSliceTemperature(
  slice: { nx: number; nz: number; xMin_um: number; xMax_um: number; zMin_um: number; zMax_um: number; T_C: number[] } | undefined,
  a_um: number,
  z_um: number,
  aIsY = false
): number | null {
  if (!slice || !slice.T_C.length) return null;
  const na = aIsY ? (slice as { ny?: number }).ny ?? slice.nx : slice.nx;
  const aMin = aIsY ? (slice as { yMin_um?: number }).yMin_um ?? slice.xMin_um : slice.xMin_um;
  const aMax = aIsY ? (slice as { yMax_um?: number }).yMax_um ?? slice.xMax_um : slice.xMax_um;
  const ua = (a_um - aMin) / Math.max(1e-6, aMax - aMin);
  const uz = (z_um - slice.zMin_um) / Math.max(1e-6, slice.zMax_um - slice.zMin_um);
  const ia = Math.max(0, Math.min(na - 1, Math.round(ua * (na - 1))));
  const iz = Math.max(0, Math.min(slice.nz - 1, Math.round(uz * (slice.nz - 1))));
  return slice.T_C[ia * slice.nz + iz] ?? null;
}

export function temperatureColor(T: number, Tliq: number, Tsol: number, Thaz: number, Tpeak: number): THREE.Color {
  const color = new THREE.Color();
  if (T >= Tliq + 0.35 * Math.max(200, Tpeak - Tliq)) {
    color.setRGB(1.0, 0.95, 0.85);
  } else if (T >= Tliq) {
    const u = Math.min(1, (T - Tliq) / Math.max(80, Tpeak - Tliq));
    color.setRGB(1.0, 0.42 + 0.4 * u, 0.06 + 0.25 * u);
  } else if (T >= Tsol) {
    color.setRGB(0.98, 0.58, 0.16);
  } else if (T >= Thaz) {
    color.setRGB(0.55, 0.28, 0.72);
  } else {
    color.setRGB(0.22, 0.16, 0.32);
  }
  return color;
}

/** Legacy contour band edge (ΔH/hs). The solver keeps the contour shape change at 30 even though the regime label
 *  now reads "Keyhole" from 20, so the 3D loft uses the same edge to match the solver contours. */
export const LOFT_KEYHOLE_DH_HS_EDGE = 30;

export function isLoftKeyhole(result: PythonLPBFResult): boolean {
  const dh = result.processParameters?.normalizedEnthalpy;
  if (typeof dh === "number" && Number.isFinite(dh)) return dh >= LOFT_KEYHOLE_DH_HS_EDGE;
  // Safe fallback when ΔH/hs is missing: use the regime label.
  return (result.meltPoolGeometry?.regime ?? "").startsWith("Keyhole");
}

export function buildLoftedMeltPoolGeometry(
  result: PythonLPBFResult,
  radialSegs = 36
): THREE.BufferGeometry {
  const longC = result.geometricContours?.longitudinalXZ ?? [];
  const topC = result.geometricContours?.topDownXY ?? [];
  const goldak = result.meltPoolGeometry.goldakParameters;
  const Tliq = result.thermalSlices?.liquidus_C ?? 1336;
  const Tsol = result.thermalSlices?.solidus_C ?? 1260;
  const Thaz = result.thermalSlices?.haz_C ?? Tsol * 0.7;
  // Colour-scale top (D10, P6): the served peak when below the display cap, else the display cap (a display
  // quantity labelled as such in the panel, not a temperature claim; the served peak is null where unsupported).
  const Tpeak = colourScalePeak_C(result, Tliq);
  const xz = result.thermalSlices?.xz;
  const isKeyhole = isLoftKeyhole(result);

  const stations =
    longC.length >= 8
      ? longC
      : Array.from({ length: 25 }, (_, i) => {
          const s = i / 24;
          const x = goldak.semiAxis_af_front_um - (goldak.semiAxis_af_front_um + goldak.semiAxis_ar_rear_um) * s;
          const norm = x >= 0 ? x / Math.max(1, goldak.semiAxis_af_front_um) : Math.abs(x) / Math.max(1, goldak.semiAxis_ar_rear_um);
          const z = goldak.semiAxis_c_depth_um * Math.sqrt(Math.max(0, 1 - norm * norm));
          return { x_um: x, z_depth_um: z, isKeyhole };
        });

  const vertices: number[] = [];
  const colors: number[] = [];
  const indices: number[] = [];

  for (let j = 0; j < stations.length; j++) {
    const st = stations[j];
    const halfW = Math.max(2, interpolateHalfWidth(topC, st.x_um) || goldak.semiAxis_b_halfwidth_um);
    const depth = Math.max(2, st.z_depth_um);
    for (let i = 0; i <= radialSegs; i++) {
      const phi = (i / radialSegs) * Math.PI;
      const exp = isKeyhole ? 0.75 : 1.0;
      const y = -depth * Math.pow(Math.sin(phi), exp);
      const z = halfW * Math.cos(phi);
      vertices.push(st.x_um, y, z);
      const T =
        sampleSliceTemperature(xz, st.x_um, -y) ??
        Tliq + (Tpeak - Tliq) * Math.max(0, 1 + y / depth);
      const c = temperatureColor(T, Tliq, Tsol, Thaz, Tpeak);
      colors.push(c.r, c.g, c.b);
    }
  }

  for (let j = 0; j < stations.length - 1; j++) {
    for (let i = 0; i < radialSegs; i++) {
      const a = j * (radialSegs + 1) + i;
      const b = a + 1;
      const c = (j + 1) * (radialSegs + 1) + i;
      const d = c + 1;
      indices.push(a, c, b);
      indices.push(b, c, d);
    }
  }

  const geom = new THREE.BufferGeometry();
  geom.setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));
  geom.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
  geom.setIndex(indices);
  geom.computeVertexNormals();
  return geom;
}

export function contourToCutFace(
  points: THREE.Vector2[],
  color: number
): THREE.Mesh | null {
  if (points.length < 3) return null;
  const shape = new THREE.Shape(points);
  const geom = new THREE.ShapeGeometry(shape);
  const mat = new THREE.MeshBasicMaterial({
    color,
    transparent: true,
    opacity: 0.42,
    side: THREE.DoubleSide,
    depthWrite: false,
  });
  return new THREE.Mesh(geom, mat);
}

export function disposeObject3D(root: THREE.Object3D) {
  root.traverse((obj) => {
    const mesh = obj as THREE.Mesh;
    if (mesh.geometry) mesh.geometry.dispose();
    const mat = mesh.material;
    if (Array.isArray(mat)) mat.forEach((m) => m.dispose());
    else if (mat) mat.dispose();
  });
}
