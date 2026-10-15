import json
import time
from pathlib import Path

from lpbf_build_job_solver import solve_lpbf_build_job

def run_benchmark():
    results = []
    
    # Test cases: combinations of P and v for two alloys
    cases = [
        # Ti-6Al-4V Conduction / Print Window
        {"alloyId": "Ti-6Al-4V", "laserPower_W": 200, "scanSpeed_mm_s": 1000},
        {"alloyId": "Ti-6Al-4V", "laserPower_W": 250, "scanSpeed_mm_s": 1200},
        # Ti-6Al-4V Slow / Hot
        {"alloyId": "Ti-6Al-4V", "laserPower_W": 300, "scanSpeed_mm_s": 500},
        
        # IN718 Conduction / Print Window
        {"alloyId": "Inconel 718", "laserPower_W": 220, "scanSpeed_mm_s": 900},
        {"alloyId": "Inconel 718", "laserPower_W": 285, "scanSpeed_mm_s": 960},
        # IN718 Fast / Cold (High cooling rate)
        {"alloyId": "Inconel 718", "laserPower_W": 150, "scanSpeed_mm_s": 1500},
    ]
    
    for case in cases:
        req = {
            "alloyId": case["alloyId"],
            "laserPower_W": case["laserPower_W"],
            "scanSpeed_mm_s": case["scanSpeed_mm_s"],
            "beamDiameter_um": 80,
            "layerThickness_um": 40,
            "hatchSpacing_um": 100,
            "bypassCache": True
        }
        t0 = time.time()
        res = solve_lpbf_build_job(req)
        dt = time.time() - t0
        
        if res.get("success"):
            micro = res["microstructure"]
            kin = res["kinetics"]
            
            results.append({
                "condition": f"{case['alloyId']} {case['laserPower_W']}W {case['scanSpeed_mm_s']}mm/s",
                "front": micro,
                # None when the kinetics block is unavailable (the model is steel-only; no build-job alloy is a steel)
                "martensite_pct": ((kin.get("calphadVsKineticsGap") or {}).get("kineticRealityAtSelectedCooling") or {}).get("predictedMartensite_pct"),
                "compute_time_ms": round(dt * 1000, 2)
            })
            
    out_file = Path("docs/LPBF_MICROSTRUCTURE_BENCHMARK_2026-09-21.json")
    out_file.write_text(json.dumps({
        "benchmark": "Phase 7 Microstructure & Kinetics",
        "date": "2026-09-21",
        "runs": results
    }, indent=2), encoding="utf-8")
    print(f"Benchmark written to {out_file}")

if __name__ == '__main__':
    run_benchmark()
