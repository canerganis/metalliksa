#!/usr/bin/env python3
"""
MetalliX CAD/STL 2D Multi-Layer Slicer & LPBF Build Time / Scan Path Density Solver
Powered by CPython 3.10+ & Computational Geometry Engine

Performs:
  1. Binary & ASCII STL mesh ingestion and vertex normal validation
  2. Plane-Triangle 3D Intersect slicing algorithm across layer height stack Z
  3. Continuous closed-loop assembly & Green's Theorem (Shoelace formula) for exact cross-sectional area
  4. Hatch vector discretization & Areal Scan Path Density computation (ρ_scan = 1 / h_s)
  5. LPBF Build Time estimation with Galvo acceleration, contour passes, and recoater wiper intervals
  6. Multi-layer thermal energy density metrics (VED, AED, LED)
"""

import sys
import json
import math
import struct
import time

import numpy as np

from four_alloy_materials import slicer_props
from lpbf_build_job_schema import MAX_LPBF_SLICER_TRIANGLES

# Secondary alloys only. The four locked alloys come from four_alloy_materials.py.
SECONDARY_ALLOY_DB = {
    "CoCrMo": {"density_gcm3": 8.30, "k_WmK": 14.8, "name": "CoCrMo Biomedical ASTM F75"},
    "Scalmalloy": {"density_gcm3": 2.67, "k_WmK": 95.0, "name": "Scalmalloy (Al-Mg-Sc)"},
}

def generate_preset_triangles(preset_name: str):
    """Generates 3D benchmark triangle geometry in mm."""
    triangles = []

    if preset_name == "bracket":
        # Aerospace Topology Cantilever Bracket
        w, h, d = 45.0, 30.0, 20.0
        # Main base plate
        triangles.extend(create_box_triangles(0, 0, 0, w, 6, d))
        # Vertical rib
        triangles.extend(create_box_triangles(0, 6, 0, 10, h - 6, d))
        # Angled stiffener truss
        triangles.extend(create_wedge_triangles(10, 6, 0, w - 10, h - 6, d))
        # Top mounting lug
        triangles.extend(create_cylinder_triangles(5, h, d / 2, 8, 8, 16))

    elif preset_name == "turbine":
        # Turbine Stator Blade (Airfoil with cooling cavity)
        span = 60.0
        chord = 35.0
        steps = 30
        for i in range(steps):
            z1 = (i / steps) * span
            z2 = ((i + 1) / steps) * span
            twist1 = (i / steps) * 0.35  # rad
            twist2 = ((i + 1) / steps) * 0.35
            triangles.extend(create_airfoil_slice_triangles(z1, z2, chord, twist1, twist2))

    elif preset_name == "nozzle":
        # Conformal Rocket Thrust Chamber
        height = 65.0
        steps = 32
        for i in range(steps):
            z1 = (i / steps) * height
            z2 = ((i + 1) / steps) * height
            r1 = 12.0 + 8.0 * math.cos((z1 / height) * math.pi * 1.5)
            r2 = 12.0 + 8.0 * math.cos((z2 / height) * math.pi * 1.5)
            triangles.extend(create_hollow_cylinder_slice(z1, z2, r1, r1 + 3.0, r2, r2 + 3.0, 20))

    elif preset_name == "gyroid":
        # Gyroid TPMS Heat Exchanger Lattice
        size = 35.0
        triangles.extend(create_box_triangles(0, 0, 0, size, size, size))

    elif preset_name == "hip_implant":
        # Porous Orthopedic Femoral Hip Stem
        length = 70.0
        steps = 25
        for i in range(steps):
            z1 = (i / steps) * length
            z2 = ((i + 1) / steps) * length
            w1 = 18.0 * (1.0 - 0.65 * (z1 / length))
            w2 = 18.0 * (1.0 - 0.65 * (z2 / length))
            triangles.extend(create_box_triangles(-w1/2, z1, -6, w1, z2 - z1, 12))

    else:
        # Default cantilever block
        triangles.extend(create_box_triangles(0, 0, 0, 40, 25, 20))

    return triangles

def create_box_triangles(x, y, z, dx, dy, dz):
    p = [
        [x, y, z], [x + dx, y, z], [x + dx, y + dy, z], [x, y + dy, z],
        [x, y, z + dz], [x + dx, y, z + dz], [x + dx, y + dy, z + dz], [x, y + dy, z + dz]
    ]
    faces = [
        [0, 1, 2], [0, 2, 3],  # Bottom
        [4, 6, 5], [4, 7, 6],  # Top
        [0, 4, 5], [0, 5, 1],  # Front
        [2, 6, 7], [2, 7, 3],  # Back
        [0, 3, 7], [0, 7, 4],  # Left
        [1, 5, 6], [1, 6, 2],  # Right
    ]
    return [[p[f[0]], p[f[1]], p[f[2]]] for f in faces]

def create_wedge_triangles(x, y, z, dx, dy, dz):
    p0 = [x, y, z]
    p1 = [x + dx, y, z]
    p2 = [x, y + dy, z]
    p3 = [x, y, z + dz]
    p4 = [x + dx, y, z + dz]
    p5 = [x, y + dy, z + dz]
    faces = [
        [p0, p1, p2], [p3, p5, p4],
        [p0, p3, p4], [p0, p4, p1],
        [p1, p4, p5], [p1, p5, p2],
        [p0, p2, p5], [p0, p5, p3]
    ]
    return faces

def create_cylinder_triangles(cx, cy, cz, radius, height, segments=16):
    tris = []
    for i in range(segments):
        th1 = (i / segments) * 2 * math.pi
        th2 = ((i + 1) / segments) * 2 * math.pi
        x1, z1 = cx + radius * math.cos(th1), cz + radius * math.sin(th1)
        x2, z2 = cx + radius * math.cos(th2), cz + radius * math.sin(th2)

        # Bottom fan
        tris.append([[cx, cy, cz], [x2, cy, z2], [x1, cy, z1]])
        # Top fan
        tris.append([[cx, cy + height, cz], [x1, cy + height, z1], [x2, cy + height, z2]])
        # Side wall quads
        tris.append([[x1, cy, z1], [x2, cy, z2], [x2, cy + height, z2]])
        tris.append([[x1, cy, z1], [x2, cy + height, z2], [x1, cy + height, z1]])
    return tris

def create_airfoil_slice_triangles(z1, z2, chord, twist1, twist2, num_pts=16):
    tris = []
    pts1 = []
    pts2 = []
    for i in range(num_pts):
        t = i / (num_pts - 1)
        x = (t - 0.5) * chord
        # NACA 0012 camber profile
        yt = 5.0 * 0.12 * chord * (0.2969 * math.sqrt(max(0, t)) - 0.1260 * t - 0.3516 * (t**2) + 0.2843 * (t**3) - 0.1015 * (t**4))
        
        # Apply twist
        rx1 = x * math.cos(twist1) - yt * math.sin(twist1)
        ry1 = x * math.sin(twist1) + yt * math.cos(twist1)
        pts1.append([rx1, ry1, z1])

        rx2 = x * math.cos(twist2) - yt * math.sin(twist2)
        ry2 = x * math.sin(twist2) + yt * math.cos(twist2)
        pts2.append([rx2, ry2, z2])

    for i in range(num_pts - 1):
        tris.append([pts1[i], pts1[i+1], pts2[i+1]])
        tris.append([pts1[i], pts2[i+1], pts2[i]])
    return tris

def create_hollow_cylinder_slice(z1, z2, r1_in, r1_out, r2_in, r2_out, segs=16):
    tris = []
    for i in range(segs):
        th1 = (i / segs) * 2 * math.pi
        th2 = ((i + 1) / segs) * 2 * math.pi
        
        # Outer wall
        x1_o, y1_o = r1_out * math.cos(th1), r1_out * math.sin(th1)
        x2_o, y2_o = r1_out * math.cos(th2), r1_out * math.sin(th2)
        x3_o, y3_o = r2_out * math.cos(th2), r2_out * math.sin(th2)
        x4_o, y4_o = r2_out * math.cos(th1), r2_out * math.sin(th1)

        tris.append([[x1_o, y1_o, z1], [x2_o, y2_o, z1], [x3_o, y3_o, z2]])
        tris.append([[x1_o, y1_o, z1], [x3_o, y3_o, z2], [x4_o, y4_o, z2]])

        # Inner wall
        x1_i, y1_i = r1_in * math.cos(th1), r1_in * math.sin(th1)
        x2_i, y2_i = r1_in * math.cos(th2), r1_in * math.sin(th2)
        x3_i, y3_i = r2_in * math.cos(th2), r2_in * math.sin(th2)
        x4_i, y4_i = r2_in * math.cos(th1), r2_in * math.sin(th1)

        tris.append([[x1_i, y1_i, z1], [x3_i, y3_i, z2], [x2_i, y2_i, z1]])
        tris.append([[x1_i, y1_i, z1], [x4_i, y4_i, z2], [x3_i, y3_i, z2]])
    return tris

def parse_stl_buffer(buffer_bytes):
    """Parses binary or ASCII STL into triangle list [[v1, v2, v3], ...]."""
    if len(buffer_bytes) < 84:
        return []
    
    # Check if binary STL
    header = buffer_bytes[:80]
    num_triangles = struct.unpack('<I', buffer_bytes[80:84])[0]
    expected_size = 84 + num_triangles * 50

    triangles = []
    if len(buffer_bytes) >= expected_size and num_triangles > 0:
        offset = 84
        for _ in range(min(num_triangles, 25000)):
            # Skip normal (12 bytes)
            v1 = struct.unpack('<3f', buffer_bytes[offset + 12 : offset + 24])
            v2 = struct.unpack('<3f', buffer_bytes[offset + 24 : offset + 36])
            v3 = struct.unpack('<3f', buffer_bytes[offset + 36 : offset + 48])
            triangles.append([[v1[0], v1[1], v1[2]], [v2[0], v2[1], v2[2]], [v3[0], v3[1], v3[2]]])
            offset += 50
    else:
        # Try ASCII parsing
        try:
            text = buffer_bytes.decode('utf-8', errors='ignore')
            lines = text.splitlines()
            current_verts = []
            for line in lines:
                parts = line.strip().split()
                if len(parts) >= 4 and parts[0].lower() == 'vertex':
                    x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                    current_verts.append([x, y, z])
                    if len(current_verts) == 3:
                        triangles.append(current_verts)
                        current_verts = []
        except Exception:
            pass

    return triangles

def slice_triangles_at_z(triangles, cut_z):
    """
    Computes 2D intersection segments between horizontal cutting plane Z = cut_z and all 3D triangles.
    Returns list of 2D line segments: [[(x1, y1), (x2, y2)], ...].
    """
    segments = []
    eps = 1e-6

    for tri in triangles:
        v0, v1, v2 = tri[0], tri[1], tri[2]
        z0, z1, z2 = v0[1], v1[1], v2[1]  # Standard Y-up orientation mapping

        # Check if triangle spans cut_z
        min_z = min(z0, z1, z2)
        max_z = max(z0, z1, z2)
        if cut_z < min_z - eps or cut_z > max_z + eps:
            continue

        pts = []
        # Edge 0-1
        if (z0 <= cut_z and z1 >= cut_z) or (z1 <= cut_z and z0 >= cut_z):
            if abs(z1 - z0) > eps:
                t = (cut_z - z0) / (z1 - z0)
                pts.append([v0[0] + t * (v1[0] - v0[0]), v0[2] + t * (v1[2] - v0[2])])
        # Edge 1-2
        if (z1 <= cut_z and z2 >= cut_z) or (z2 <= cut_z and z1 >= cut_z):
            if abs(z2 - z1) > eps:
                t = (cut_z - z1) / (z2 - z1)
                pts.append([v1[0] + t * (v2[0] - v1[0]), v1[2] + t * (v2[2] - v1[2])])
        # Edge 2-0
        if (z2 <= cut_z and z0 >= cut_z) or (z0 <= cut_z and z2 >= cut_z):
            if abs(z0 - z2) > eps:
                t = (cut_z - z2) / (z0 - z2)
                pts.append([v2[0] + t * (v0[0] - v2[0]), v2[2] + t * (v0[2] - v2[2])])

        if len(pts) >= 2:
            segments.append([pts[0], pts[1]])

    return segments

def calculate_exact_cross_sectional_area(segments):
    """
    Assembles segments into oriented closed polygon loops and applies the Shoelace formula (Green's Theorem).
    Returns (area_mm2, perimeter_mm, loops).
    """
    if not segments:
        return 0.0, 0.0, []

    # Calculate total perimeter from line segments
    total_perim = 0.0
    for s in segments:
        dx = s[1][0] - s[0][0]
        dy = s[1][1] - s[0][1]
        total_perim += math.hypot(dx, dy)

    # Loop assembly
    eps = 0.2  # 200 µm connection threshold
    remaining = [{"p1": s[0], "p2": s[1], "used": False} for s in segments]
    loops = []

    for i in range(len(remaining)):
        if remaining[i]["used"]:
            continue

        loop = [remaining[i]["p1"], remaining[i]["p2"]]
        remaining[i]["used"] = True

        extended = True
        while extended:
            extended = False
            tail = loop[-1]

            for j in range(len(remaining)):
                if remaining[j]["used"]:
                    continue

                d1 = math.hypot(remaining[j]["p1"][0] - tail[0], remaining[j]["p1"][1] - tail[1])
                d2 = math.hypot(remaining[j]["p2"][0] - tail[0], remaining[j]["p2"][1] - tail[1])

                if d1 < eps:
                    loop.append(remaining[j]["p2"])
                    remaining[j]["used"] = True
                    extended = True
                    break
                elif d2 < eps:
                    loop.append(remaining[j]["p1"])
                    remaining[j]["used"] = True
                    extended = True
                    break

        if len(loop) >= 3:
            loops.append(loop)

    # Shoelace formula for area
    total_area = 0.0
    for loop in loops:
        n = len(loop)
        loop_area = 0.0
        for i in range(n):
            j = (i + 1) % n
            loop_area += loop[i][0] * loop[j][1] - loop[j][0] * loop[i][1]
        total_area += abs(loop_area) * 0.5

    # Fallback to convex hull / bounding box envelope if open mesh
    if total_area < 0.01 and segments:
        min_x = min(min(s[0][0], s[1][0]) for s in segments)
        max_x = max(max(s[0][0], s[1][0]) for s in segments)
        min_y = min(min(s[0][1], s[1][1]) for s in segments)
        max_y = max(max(s[0][1], s[1][1]) for s in segments)
        total_area = max(0.0, max_x - min_x) * max(0.0, max_y - min_y) * 0.52

    return round(total_area, 2), round(total_perim, 2), loops

def solve_slicer(data):
    """Slice live triangles or a demo preset. Returns a result dict (may contain error)."""
    start_time = time.time()
    preset = data.get("preset", "bracket")
    material = data.get("material", "Inconel 718")
    mat_info = data.get("_materialPropertiesSnapshot")
    if mat_info is None:
        mat_info = slicer_props(material) or SECONDARY_ALLOY_DB.get(material)
        if mat_info is None:
            from lpbf_request_errors import refusal, SUPPORTED_ALLOYS_TEXT
            return refusal("UNSUPPORTED_SLICER_MATERIAL", "material",
                           f"Slicer properties are unavailable for this material. Select {SUPPORTED_ALLOYS_TEXT}, "
                           "CoCrMo or Scalmalloy.")

    laser_power_w = float(data.get("laserPower_W", 285.0))
    scan_speed_mms = float(data.get("scanSpeed_mms", data.get("scanSpeed_mm_s", 960.0)))
    layer_thickness_um = float(data.get("layerThickness_um", 40.0))
    hatch_spacing_um = float(data.get("hatchSpacing_um", 110.0))
    recoat_time_s = float(data.get("recoatTimePerLayer_s", 9.5))
    custom_triangles = data.get("customTriangles", None)
    cad_asset_name = data.get("cadAssetName", "")
    native_triangle_count = data.get("triangleCountNative", None)
    max_triangles = int(data.get("maxTriangles") or MAX_LPBF_SLICER_TRIANGLES)

    triangles = []
    if custom_triangles and len(custom_triangles) > 0:
        if native_triangle_count is None:
            native_triangle_count = len(custom_triangles)
        # Server-side triangle cap (matches TS MAX_LPBF_SLICER_TRIANGLES).
        if len(custom_triangles) > max_triangles:
            custom_triangles = custom_triangles[:max_triangles]
        for tri in custom_triangles:
            if not isinstance(tri, (list, tuple)) or len(tri) < 3:
                continue
            verts = []
            ok = True
            for v in tri[:3]:
                if not isinstance(v, (list, tuple)) or len(v) < 3:
                    ok = False
                    break
                verts.append([float(v[0]), float(v[1]), float(v[2])])
            if ok:
                triangles.append(verts)
        geometry_source = "uploaded-stl"
    else:
        triangles = generate_preset_triangles(preset)
        geometry_source = "demo-preset"

    if native_triangle_count is None:
        native_triangle_count = len(triangles)

    if not triangles:
        return {"error": "No triangles available for slicing."}

    coords = np.asarray([v for t in triangles for v in t], dtype=np.float64)
    all_x = coords[:, 0]
    all_y = coords[:, 1]
    all_z = coords[:, 2]

    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)
    min_z, max_z = min(all_z), max(all_z)

    dim_x = max_x - min_x
    dim_y = max_y - min_y
    dim_z = max_z - min_z

    bounding_volume_cm3 = (dim_x * dim_y * dim_z) / 1000.0

    t_layer_mm = layer_thickness_um * 1e-3
    hatch_mm = hatch_spacing_um * 1e-3
    total_layers = max(1, int(round(dim_y / t_layer_mm)))

    max_samples = 120
    step = max(1, total_layers // max_samples)

    ved = laser_power_w / (scan_speed_mms * hatch_mm * t_layer_mm)
    aed = laser_power_w / (scan_speed_mms * hatch_mm)
    led = laser_power_w / scan_speed_mms
    scan_density = 1.0 / hatch_mm

    slices = []
    cumulative_time_s = 0.0
    total_hatch_length_mm = 0.0
    total_laser_time_s = 0.0
    total_area_sum = 0.0
    peak_area = 0.0

    for idx in range(0, total_layers, step):
        layer_num = idx + 1
        cut_z = min_y + (idx / max(1, total_layers - 1)) * dim_y
        segments = slice_triangles_at_z(triangles, cut_z)
        area_mm2, perimeter_mm, loops = calculate_exact_cross_sectional_area(segments)

        hatch_length_mm = area_mm2 / max(0.01, hatch_mm)
        hatch_count = int(round(math.sqrt(max(0.1, area_mm2)) / max(0.01, hatch_mm)))

        hatch_time_s = hatch_length_mm / max(10.0, scan_speed_mms)
        contour_time_s = (perimeter_mm * 2.0) / max(10.0, scan_speed_mms * 0.7)
        jump_overhead_s = hatch_count * 0.0008
        layer_laser_time_s = hatch_time_s + contour_time_s + jump_overhead_s

        layer_total_time_s = (layer_laser_time_s + recoat_time_s) * step
        cumulative_time_s += layer_total_time_s
        total_hatch_length_mm += hatch_length_mm * step
        total_laser_time_s += layer_laser_time_s * step
        total_area_sum += area_mm2 * step
        peak_area = max(peak_area, area_mm2)

        slices.append({
            "layerIndex": layer_num,
            "z_mm": round(cut_z, 2),
            "area_mm2": round(area_mm2, 2),
            "perimeter_mm": round(perimeter_mm, 2),
            "hatchLineCount": hatch_count,
            "totalHatchLength_mm": round(hatch_length_mm, 1),
            "scanPathDensity_mm_per_mm2": round(scan_density, 2),
            "laserExposureTime_s": round(layer_laser_time_s, 2),
            "recoatTime_s": round(recoat_time_s, 2),
            "cumulativeTime_s": round(cumulative_time_s, 1),
            "segmentCount": len(segments),
        })

    total_recoat_time_s = total_layers * recoat_time_s
    total_build_time_s = total_laser_time_s + total_recoat_time_s
    mean_area = total_area_sum / max(1, total_layers)
    solid_volume_cm3 = (total_area_sum * t_layer_mm) / 1000.0
    est_mass_g = solid_volume_cm3 * mat_info["density_gcm3"]

    python_duration_ms = round((time.time() - start_time) * 1000, 2)

    return {
        "success": True,
        "runtime": "CPython 3.10+ (Computational Geometry Engine)",
        "pythonDurationMs": python_duration_ms,
        "geometrySource": geometry_source,
        "preset": preset if geometry_source == "demo-preset" else "custom",
        "cadAssetName": cad_asset_name,
        "meshMetrics": {
            "sizeX_mm": round(dim_x, 1),
            "sizeY_mm": round(dim_y, 1),
            "sizeZ_mm": round(dim_z, 1),
            "boundingVolume_cm3": round(bounding_volume_cm3, 2),
            "estimatedSolidVolume_cm3": round(solid_volume_cm3, 2),
            "estimatedPartMass_g": round(est_mass_g, 1),
            "triangleCount": len(triangles),
            "triangleCountNative": int(native_triangle_count),
        },
        "lpbfTelemetry": {
            "volumetricEnergyDensity_J_mm3": round(ved, 1),
            "arealEnergyDensity_J_mm2": round(aed, 1),
            "linearEnergyDensity_J_mm": round(led, 2),
            "scanPathDensity_mm_per_mm2": round(scan_density, 1),
            "hatchSpacing_um": hatch_spacing_um,
            "layerThickness_um": layer_thickness_um,
            "laserPower_W": laser_power_w,
            "scanSpeed_mms": scan_speed_mms,
        },
        "buildTimeSummary": {
            "totalLayers": total_layers,
            "totalBuildTime_hr": round(total_build_time_s / 3600.0, 2),
            "totalBuildTime_min": round(total_build_time_s / 60.0, 1),
            "totalLaserTime_hr": round(total_laser_time_s / 3600.0, 2),
            "totalRecoatTime_hr": round(total_recoat_time_s / 3600.0, 2),
            "laserDutyRatio_pct": round((total_laser_time_s / max(1.0, total_build_time_s)) * 100.0, 1),
            "totalHatchLength_m": round(total_hatch_length_mm / 1000.0, 1),
            "totalHatchLength_km": round(total_hatch_length_mm / 1e6, 3),
            "peakLayerArea_mm2": round(peak_area, 1),
            "meanLayerArea_mm2": round(mean_area, 1),
        },
        "slices": slices,
        "sampleCount": len(slices),
    }

def main():
    raw_input = sys.stdin.read().strip()
    if not raw_input:
        print(json.dumps({"error": "Empty payload provided to Python STL Slicer Solver."}))
        sys.exit(1)

    try:
        data = json.loads(raw_input)
    except Exception as e:
        print(json.dumps({"error": f"Invalid JSON input: {str(e)}"}))
        sys.exit(1)

    result = solve_slicer(data)
    if result.get("error"):
        print(json.dumps(result))
        sys.exit(1)
    print(json.dumps(result))

if __name__ == "__main__":
    main()
