#!/usr/bin/env python3
"""Build-job verdict must come from Python, not a second TypeScript decision.

Fast suite (default): Phase 0–2 + lazy defaults + cache + Murakami paste.
Slow suite (--slow): UQ Monte Carlo + NIST AM-Bench (opt-in path).
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SOLVER = os.path.join(HERE, "lpbf_build_job_solver.py")
SLOW = "--slow" in sys.argv


def run_job(payload, *, clear_cache=False):
    body = {"enableUq": False, "includeAmbench": False, **payload}
    if clear_cache:
        from lpbf_job_cache import clear_cache as _clear

        _clear()
    # Prefer in-process for cache tests; subprocess for isolation of CLI path.
    if payload.get("_subprocess"):
        body.pop("_subprocess", None)
        proc = subprocess.run(
            [sys.executable, SOLVER],
            input=json.dumps(body),
            capture_output=True,
            text=True,
            cwd=HERE,
        )
        if proc.returncode != 0:
            raise AssertionError(proc.stderr or proc.stdout)
        return json.loads(proc.stdout)

    from lpbf_build_job_solver import solve_lpbf_build_job

    return solve_lpbf_build_job(body)


KINETICS_FIXTURE = os.path.join(HERE, "..", "tests", "fixtures", "build-job-kinetics-blocks.json")
# Real build_job_kinetics output for the UI render test (tests/build-job-kinetics-panel.test.tsx).
# Rates: the four demo builds' reported rates, the degenerate 1 K/s floor, and an in-map 30 C/s.
# The TTT curves, LSW profile and timing are left out (the panel does not read them).
KINETICS_FIXTURE_CASES = (
    ("ss316l_no_model", "ss316l", 1205584.0),
    ("alsi10mg_no_model", "alsi10mg", 2603566.0),
    ("in718_above_map", "in718", 877254.0),
    ("ti6al4v_above_map", "ti6al4v", 1089047.0),
    ("in718_degenerate_floor", "in718", 1.0),
    ("ti6al4v_in_map_30", "ti6al4v", 30.0),
    ("in718_in_map_30", "in718", 30.0),
    # HYPOTHETICAL: no build-job alloy is a steel (the kinetics model is steel-only), so the "selected row"
    # display path is exercised with AISI 4140 mapped in for this fixture only (see kinetics_fixture_blocks).
    ("aisi4140_in_map_30_hypothetical", "aisi4140", 30.0),
)
_KINETICS_FIXTURE_DROP = ("tttIsothermalCurves", "lswPrecipitateCoarsening", "computeTimeMs")


def kinetics_fixture_blocks():
    from unittest import mock

    import lpbf_build_job_solver as bj

    out = {}
    for name, alloy_id, rate in KINETICS_FIXTURE_CASES:
        extra = {"aisi4140": "AISI 4140"} if alloy_id == "aisi4140" else {}
        with mock.patch.dict(bj.BUILD_JOB_KINETICS_ALLOY, extra):
            block = bj.build_job_kinetics(alloy_id, {"solidificationKinetics": {"coolingRate_K_s": rate}})
        out[name] = {k: v for k, v in block.items() if k not in _KINETICS_FIXTURE_DROP}
    return out


MICROSTRUCTURE_FIXTURE = os.path.join(HERE, "..", "tests", "fixtures", "build-job-microstructure-blocks.json")


def microstructure_fixture_blocks():
    """Real project_build_job_microstructure output for the UI render test (tests/build-job-microstructure-panel.test.tsx)."""
    from lpbf_solidification_microstructure import project_build_job_microstructure

    common = {"beamDiameter_um": 80, "layerThickness_um": 40, "hatchSpacing_um": 110, "bypassCache": True}
    available = run_job({"alloyId": "in718", "laserPower_W": 285, "scanSpeed_mm_s": 960, **common})
    # P1 (2026-10-11): the latent-free Rosenthal field resolves the former 20 W / 2000 mm/s case; 10 W / 3000 mm/s
    # is the fallback case now.
    fallback = run_job({"alloyId": "in718", "laserPower_W": 10, "scanSpeed_mm_s": 3000, **common})
    # Wave B KS-1: the clamp-floor state is unreachable on real builds now, so the degenerate block is
    # projected from the real IN718 100/960 thermal result with its kinetics moved onto the floors.
    degenerate = run_job({"alloyId": "in718", "laserPower_W": 100, "scanSpeed_mm_s": 960, **common})
    return {
        "available_in718_285_960": available["microstructure"],
        "screening_fallback_in718_10_3000": fallback["microstructure"],
        "degenerate_floor_synthetic": project_build_job_microstructure(_floored_thermal(degenerate["thermal"])),
        "unavailable_no_kinetics": project_build_job_microstructure({}),
    }


def _floored_thermal(thermal):
    """SYNTHETIC: a real thermal result with R and the cooling rate set to the front-mapper clamp floors."""
    import copy

    floored = copy.deepcopy(thermal)
    floored["solidificationKinetics"].update(
        usedFieldMap=True, solidificationRate_R_mm_s=0.1, solidificationRate_R_m_s=1.0e-4, coolingRate_K_s=1.0)
    return floored


def check_microstructure_fixture():
    with open(MICROSTRUCTURE_FIXTURE, encoding="utf-8") as fh:
        committed = json.load(fh)
    current = json.loads(json.dumps(microstructure_fixture_blocks()))
    assert committed == current, "tests/fixtures/build-job-microstructure-blocks.json is stale: rerun with --write-microstructure-fixture"


def check_kinetics_fixture():
    """The committed UI fixture must equal the current Python output (no hand-made blocks)."""
    with open(KINETICS_FIXTURE, encoding="utf-8") as fh:
        committed = json.load(fh)
    current = json.loads(json.dumps(kinetics_fixture_blocks()))
    assert committed == current, "tests/fixtures/build-job-kinetics-blocks.json is stale: rerun with --write-kinetics-fixture"


def check_build_job_kinetics(ti):
    import math

    from kinetics_ttt_cct_solver import solve_phase_transformation_kinetics
    from lpbf_build_job_solver import (
        BUILD_JOB_KINETICS_ALLOY,
        DEGENERATE_FRONT_REASON,
        build_cooling_rate_cct_row,
        build_job_kinetics,
        build_rate_martensite,
    )

    assert BUILD_JOB_KINETICS_ALLOY == {"in718": "Inconel 718", "ti6al4v": "Ti-6Al-4V"}
    kin = ti["kinetics"]
    rate = ti["thermal"]["solidificationKinetics"]["coolingRate_K_s"]
    assert rate > 2000.0, rate
    # Kinetics model is steel-only (kinetics_ttt_cct_solver kineticsModel): Ti-6Al-4V is not a steel, so
    # the whole block is unavailable with the solver's reason and no steel-template value.
    reference = solve_phase_transformation_kinetics(alloy_name="Ti-6Al-4V", cooling_rate_c_s=float(rate))
    assert reference["kineticsModel"]["status"] == "unavailable"
    assert kin["status"] == "unavailable" and kin["success"] is False
    assert kin["reason"] == "kinetics model is steel-only: Ti-6Al-4V is not a steel", kin["reason"]
    assert kin["alloy"] is None and kin["alloyId"] == "ti6al4v"
    assert kin["buildCoolingRate_C_s"] == float(rate) == kin["reportedCoolingRate_K_s"]
    assert kin["coolingRateSource"] == "thermal.solidificationKinetics.coolingRate_K_s"
    assert kin["cctContinuousCoolingMap"] is None and kin["calphadVsKineticsGap"] is None
    assert kin["buildCoolingRateCctRow"] is None and kin["buildRateMartensite"] is None
    assert "Pearlite" not in json.dumps(kin) and "Martensite_pct" not in json.dumps(kin)

    # The CCT row selection and martensite helpers stay tested on a real CCT map (AISI 4140; the steel
    # template is the only one the solver reports).
    steel = solve_phase_transformation_kinetics(alloy_name="AISI 4140", cooling_rate_c_s=30.0)
    sel = build_cooling_rate_cct_row(steel["cctContinuousCoolingMap"], rate)
    assert sel["status"] == "unavailable" and sel["rowIndex"] is None and sel["rowCoolingRate_C_s"] is None
    assert sel["mapRange_C_s"] == [0.05, 2000.0]
    assert sel["reason"] == (f"build cooling rate {int(rate)} °C/s is above the CCT map maximum 2000 °C/s; "
                             "no row is extrapolated"), sel["reason"]
    mart = build_rate_martensite("aisi4140", "AISI 4140", steel["calphadVsKineticsGap"], sel)
    assert mart["status"] == "unavailable" and mart["predictedMartensite_pct"] is None and mart["verdict"] is None
    assert mart["reason"].startswith(sel["reason"] + "; the steel-type martensite fraction and verdict")

    cct = steel["cctContinuousCoolingMap"]
    inside = build_cooling_rate_cct_row(cct, 30.0)  # log10 nearest: 25 (|0.079|) beats 50 (|0.222|)
    assert inside["status"] == "selected" and inside["rowCoolingRate_C_s"] == 25.0
    assert cct[inside["rowIndex"]]["coolingRate_C_s"] == 25.0 and inside["reason"] is None
    assert build_cooling_rate_cct_row(cct, 0.3)["rowCoolingRate_C_s"] == 0.2
    assert build_cooling_rate_cct_row(cct, 72.0)["rowCoolingRate_C_s"] == 100.0  # log scale; linear-nearest is 50
    assert build_cooling_rate_cct_row(cct, 2000.0)["rowCoolingRate_C_s"] == 2000.0
    assert build_cooling_rate_cct_row(cct, 0.05)["rowCoolingRate_C_s"] == 0.05
    # Exact log-midpoint tie: the first row in map order (the slower rate) wins.
    tie_map = [{"coolingRate_C_s": 1.0}, {"coolingRate_C_s": 100.0}]
    assert build_cooling_rate_cct_row(tie_map, 10.0)["rowCoolingRate_C_s"] == 1.0
    # The range reason states the exact comparison, never a rounded one.
    just_above = build_cooling_rate_cct_row(cct, 2000.0000001)
    assert just_above["status"] == "unavailable"
    assert just_above["reason"] == ("build cooling rate 2000.0000001 °C/s is above the CCT map maximum "
                                    "2000 °C/s; no row is extrapolated"), just_above["reason"]
    below = build_cooling_rate_cct_row(cct, 0.01)
    assert below["status"] == "unavailable" and "below the CCT map minimum 0.05 °C/s" in below["reason"]
    for bad in (None, float("nan"), float("inf"), float("-inf"), -1.0, 0.0, True, False, "30"):
        out = build_cooling_rate_cct_row(cct, bad)
        assert out["status"] == "unavailable" and out["rowIndex"] is None, (bad, out)
    for bad_map in (None, [], [None, "x", {"coolingRate_C_s": float("nan")}, {"coolingRate_C_s": True}]):
        assert build_cooling_rate_cct_row(bad_map, 30.0)["status"] == "unavailable", bad_map
    assert build_cooling_rate_cct_row([None, {"coolingRate_C_s": 25.0}], 25.0)["rowIndex"] == 1

    # No finite cooling rate: unavailable, never the former 1e5 K/s default.
    for thermal in ({}, {"solidificationKinetics": {}},
                    {"solidificationKinetics": {"coolingRate_K_s": float("nan")}},
                    {"solidificationKinetics": {"coolingRate_K_s": float("inf")}},
                    {"solidificationKinetics": {"coolingRate_K_s": True}},
                    {"solidificationKinetics": {"coolingRate_K_s": "1e5"}}):
        missing = build_job_kinetics("in718", thermal)
        assert missing["status"] == "unavailable" and missing["calphadVsKineticsGap"] is None
        assert missing["reason"] == "the build thermal result reports no finite cooling rate", missing
        assert missing["buildCoolingRate_C_s"] is None and missing["reportedCoolingRate_K_s"] is None
    # At or below the 1 K/s floor of a degenerate solidification front (solidification_front.py):
    # not a build rate, whatever produced it.
    for floor_rate in (1.0, 1, 0.5, 0.0, -3.0):
        floor = build_job_kinetics("ti6al4v", {"solidificationKinetics": {"coolingRate_K_s": floor_rate}})
        assert floor["status"] == "unavailable" and floor["reason"] == DEGENERATE_FRONT_REASON, floor
        assert floor["buildCoolingRate_C_s"] is None and floor["reportedCoolingRate_K_s"] == float(floor_rate)
        assert floor["cctContinuousCoolingMap"] is None and floor["buildRateMartensite"] is None
    above_floor = build_job_kinetics("ti6al4v", {"solidificationKinetics": {"coolingRate_K_s": 1.0000001}})
    assert above_floor["reason"] != DEGENERATE_FRONT_REASON and above_floor["buildCoolingRate_C_s"] == 1.0000001

    # In-map rate (synthetic; real builds report ~1e5-1e6 K/s): still unavailable, the model is steel-only.
    for alloy_id, name in (("in718", "Inconel 718"), ("ti6al4v", "Ti-6Al-4V")):
        good = build_job_kinetics(alloy_id, {"solidificationKinetics": {"coolingRate_K_s": 30.0}})
        assert good["status"] == "unavailable", good
        assert good["reason"] == f"kinetics model is steel-only: {name} is not a steel", good["reason"]
        assert good["buildCoolingRate_C_s"] == 30.0 and good["buildCoolingRateCctRow"] is None
    # With a steel the fraction and verdict are reported for a selected row (hypothetical mapping, as in the fixture).
    from unittest import mock
    with mock.patch.dict(BUILD_JOB_KINETICS_ALLOY, {"aisi4140": "AISI 4140"}):
        steel_job = build_job_kinetics("aisi4140", {"solidificationKinetics": {"coolingRate_K_s": 30.0}})
    assert steel_job["status"] == "available" and steel_job["buildCoolingRateCctRow"]["rowCoolingRate_C_s"] == 25.0
    m = steel_job["buildRateMartensite"]
    reality = steel_job["calphadVsKineticsGap"]["kineticRealityAtSelectedCooling"]
    assert m["status"] == "available" and m["reason"] is None
    assert m["predictedMartensite_pct"] == reality["predictedMartensite_pct"] and m["verdict"] == reality["verdict"]
    assert math.isclose(reality["coolingRate_C_s"], 30.0)
    nonfinite_gap = {"kineticRealityAtSelectedCooling": {"predictedMartensite_pct": None, "verdict": "x"}}
    assert build_rate_martensite("ti6al4v", "Ti-6Al-4V", nonfinite_gap, {"status": "selected"})["status"] == "unavailable"
    # The registry placeholder Ms of IN718 is still withheld by the helper (defence in depth).
    placeholder = build_rate_martensite("in718", "Inconel 718", steel["calphadVsKineticsGap"], {"status": "selected"})
    assert placeholder["status"] == "unavailable" and "non-physical placeholder" in placeholder["reason"]

    # B1 regression: IN718 150 W / 1500 mm/s reported the 1 K/s floor until the Wave B bump (LA-2 resolves the
    # pool and KS-1 samples only the solidifying front: about 5.5e6 K/s now). The degenerate-floor path keeps
    # its synthetic coverage above (floor_rate loop).
    fast = run_job({"alloyId": "in718", "laserPower_W": 150, "scanSpeed_mm_s": 1500, "beamDiameter_um": 80,
                    "layerThickness_um": 30, "hatchSpacing_um": 100, "bypassCache": True})
    assert fast["thermal"]["solidificationKinetics"]["coolingRate_K_s"] > 2000.0
    assert fast["kinetics"]["status"] == "unavailable" and fast["kinetics"]["reason"] != DEGENERATE_FRONT_REASON
    assert fast["kinetics"]["buildCoolingRateCctRow"] is None
    # A non-degenerate IN718 build: unavailable because the kinetics model is steel-only.
    slow = run_job({"alloyId": "in718", "laserPower_W": 220, "scanSpeed_mm_s": 900, "beamDiameter_um": 80,
                    "layerThickness_um": 30, "hatchSpacing_um": 100, "bypassCache": True})
    assert slow["thermal"]["solidificationKinetics"]["coolingRate_K_s"] > 2000.0
    assert slow["kinetics"]["status"] == "unavailable"
    assert slow["kinetics"]["reason"] == "kinetics model is steel-only: Inconel 718 is not a steel"
    assert slow["kinetics"]["buildCoolingRateCctRow"] is None and slow["kinetics"]["buildRateMartensite"] is None

    for alloy_id, name, power, speed in (("ss316l", "316L Stainless Steel", 200, 800),
                                         ("alsi10mg", "AlSi10Mg", 330, 1100)):
        job = run_job({"alloyId": alloy_id, "laserPower_W": power, "scanSpeed_mm_s": speed,
                       "beamDiameter_um": 80, "layerThickness_um": 30, "hatchSpacing_um": 100,
                       "bypassCache": True})
        assert job["success"]
        k = job["kinetics"]
        reported = float(job["thermal"]["solidificationKinetics"]["coolingRate_K_s"])
        assert k == {
            "success": False,
            "status": "unavailable",
            "reason": f"no kinetics model for {name}",
            "alloyId": alloy_id,
            "alloy": None,
            "buildCoolingRate_C_s": None if reported <= 1.0 else reported,
            "reportedCoolingRate_K_s": reported,
            "coolingRateSource": "thermal.solidificationKinetics.coolingRate_K_s",
            "cctContinuousCoolingMap": None,
            "calphadVsKineticsGap": None,
            "buildCoolingRateCctRow": None,
            "buildRateMartensite": None,
        }, k
        assert "AISI 4140" not in json.dumps(k) and "7075" not in json.dumps(k)


def check_build_job_microstructure(job):
    """Build-job microstructure is a projection of thermal.solidificationKinetics (no second G/R)."""
    micro = job["microstructure"]
    kin = job["thermal"]["solidificationKinetics"]
    # The 285 W / 960 mm/s IN718 case must use the liquidus field map, not the tail-length
    # heuristic: a G threshold alone cannot tell the two apart (fallback G is ~1.3e5 K/m).
    assert kin["usedFieldMap"] is True and kin["gradientSource"] != "tail-length-fallback", kin
    assert micro["status"] == "available", micro["status"]
    assert micro["usedFieldMap"] is True
    assert micro["gradientSource"] == kin["gradientSource"]
    assert "reason" not in micro
    assert micro["source"] == "thermal.solidificationKinetics"
    assert micro["G_K_m"] == kin["thermalGradient_G_K_m"]
    # R is the more precise R_mm_s / 1e3 when present (R_m_s is rounded to 3 decimals).
    assert micro["R_m_s"] == kin["solidificationRate_R_mm_s"] / 1.0e3
    assert abs(micro["R_m_s"] - kin["solidificationRate_R_m_s"]) <= 5.0e-4
    # Keyhole regime is carried so the panel can say the G/R field is outside its regime.
    assert micro["regime"] == job["thermal"]["meltPoolGeometry"]["regime"]
    assert micro["regime"].startswith("Keyhole"), micro["regime"]
    assert micro["normalizedEnthalpy"] == job["thermal"]["processParameters"]["normalizedEnthalpy"]
    assert micro["regimeNote"] == "Keyhole Mode: outside the conduction regime of the G/R field"
    assert micro["coolingRate_K_s"] == kin["coolingRate_K_s"]
    assert micro["PDAS_um"] == kin["primaryDendriteArmSpacing_PDAS_um"]
    assert micro["SDAS_um"] == kin["secondaryDendriteArmSpacing_SDAS_um"]
    assert micro["morphology"] == kin["microstructureMorphology"]
    assert micro["modelId"] == kin["modelId"]
    assert micro["gradientSource"] == kin["gradientSource"]
    assert micro["usedFieldMap"] == kin["usedFieldMap"]
    assert micro["g_over_r_ratio"] == kin["g_over_r_ratio"]
    assert micro["doi"] == kin["doi"]
    assert micro["disclaimer"].startswith(kin["disclaimer"])
    assert "no second estimate" in micro["disclaimer"]
    # The removed Rosenthal default-constant block (G floor 1e4 K/m) must not reappear.
    assert micro["G_K_m"] > 1.0e5, micro["G_K_m"]

    from lpbf_solidification_microstructure import project_build_job_microstructure

    for bad in ({}, {"solidificationKinetics": None}, {"solidificationKinetics": {}},
                {"solidificationKinetics": {**kin, "thermalGradient_G_K_m": float("nan")}},
                {"solidificationKinetics": {**kin, "solidificationRate_R_m_s": None}},
                # only the cooling rate is bad, with valid G/R: still unavailable
                {"solidificationKinetics": {**kin, "coolingRate_K_s": float("inf")}},
                {"solidificationKinetics": {**kin, "coolingRate_K_s": None}},
                # bool is not a number (True == 1 must not pass as G or R)
                {"solidificationKinetics": {**kin, "thermalGradient_G_K_m": True}},
                {"solidificationKinetics": {**kin, "solidificationRate_R_m_s": True}}):
        unavailable = project_build_job_microstructure(bad)
        assert unavailable["status"] == "unavailable"
        assert unavailable["reason"] == "thermal.solidificationKinetics missing or non-finite"
        for key in ("G_K_m", "R_m_s", "coolingRate_K_s", "PDAS_um", "SDAS_um", "morphology"):
            assert unavailable[key] is None, key

    # usedFieldMap not True (even with a non-fallback gradientSource label) is a screening fallback.
    synthetic = project_build_job_microstructure(
        {"solidificationKinetics": {**kin, "usedFieldMap": False}, "meltPoolGeometry": {"regime": "Conduction Mode (Stable)"}}
    )
    assert synthetic["status"] == "screening-fallback" and synthetic["regimeNote"] is None
    assert synthetic["reason"] == FALLBACK_REASON


FALLBACK_REASON = (
    "thermal.solidificationKinetics used the tail-length heuristic (G = ΔT/x_rear, R = v·cosθ), "
    "not the liquidus field map; treat G/R/PDAS/SDAS as screening only"
)


def check_build_job_microstructure_fallback():
    """Low power / high speed cases fall back to the tail-length heuristic: labelled, not 'available'."""
    cases = (
        # Wave B LA-2/KS-1: 60/2000 (IN718) and 40/1500 (Ti64) resolve the field map now; P1 (2026-10-11,
        # latent-free Rosenthal field) also resolves 20/2000 (IN718), so the cases sit lower.
        {"alloyId": "in718", "laserPower_W": 10, "scanSpeed_mm_s": 3000},
        {"alloyId": "ti6al4v", "laserPower_W": 10, "scanSpeed_mm_s": 2500},
    )
    for case in cases:
        job = run_job({**case, "beamDiameter_um": 80, "layerThickness_um": 40,
                       "hatchSpacing_um": 110, "bypassCache": True})
        kin = job["thermal"]["solidificationKinetics"]
        micro = job["microstructure"]
        assert kin["usedFieldMap"] is False and kin["gradientSource"] == "tail-length-fallback", (case, kin)
        assert micro["status"] == "screening-fallback", (case, micro["status"])
        assert micro["reason"] == FALLBACK_REASON
        assert micro["usedFieldMap"] is False
        assert micro["gradientSource"] == "tail-length-fallback"
        # Numbers are still the thermal block's, never recomputed.
        assert micro["G_K_m"] == kin["thermalGradient_G_K_m"]
        assert micro["coolingRate_K_s"] == kin["coolingRate_K_s"]
        assert micro["PDAS_um"] == kin["primaryDendriteArmSpacing_PDAS_um"]
        assert micro["SDAS_um"] == kin["secondaryDendriteArmSpacing_SDAS_um"]
        assert micro["morphology"] == kin["microstructureMorphology"]
        assert micro["regimeNote"] is None
        print("  fallback", case["alloyId"], case["laserPower_W"], "W /", case["scanSpeed_mm_s"], "mm/s:",
              "G", micro["G_K_m"], "R", micro["R_m_s"], "PDAS", micro["PDAS_um"], micro["status"], micro["gradientSource"])


DEGENERATE_FLOOR_REASON = (
    "solidification front degenerate: floor-clamped R/cooling "
    "(R <= 1e-4 m/s or cooling <= 1 K/s), not a computed value"
)


def check_build_job_microstructure_degenerate_floor():
    """Degenerate-floor labelling. Real case at Tier 2: IN718 100 W / 960 mm/s; after Wave B KS-1 (only
    solidifying n_x > 0 samples) it is available, and the floor state is exercised synthetically."""
    job = run_job({"alloyId": "in718", "laserPower_W": 100, "scanSpeed_mm_s": 960, "beamDiameter_um": 80,
                   "layerThickness_um": 40, "hatchSpacing_um": 110, "bypassCache": True})
    assert job["microstructure"]["status"] == "available", job["microstructure"]["status"]
    from lpbf_solidification_microstructure import project_build_job_microstructure

    floored = _floored_thermal(job["thermal"])
    kin = floored["solidificationKinetics"]
    micro = project_build_job_microstructure(floored)
    assert micro["status"] == "degenerate-floor", micro["status"]
    assert micro["reason"] == DEGENERATE_FLOOR_REASON
    assert micro["usedFieldMap"] is True
    # Numbers are still copied, never recomputed.
    assert micro["R_m_s"] == kin["solidificationRate_R_mm_s"] / 1.0e3 <= 1.0e-4 * (1.0 + 1.0e-9)
    assert micro["coolingRate_K_s"] == kin["coolingRate_K_s"] == 1.0
    assert micro["G_K_m"] == kin["thermalGradient_G_K_m"]
    assert micro["PDAS_um"] == kin["primaryDendriteArmSpacing_PDAS_um"]
    assert micro["SDAS_um"] == kin["secondaryDendriteArmSpacing_SDAS_um"]
    assert micro["morphology"] == kin["microstructureMorphology"]
    assert "not a computed result" in micro["disclaimer"]

    # Synthetic: field map used, R above the floor but cooling on its floor, and vice versa.
    from lpbf_solidification_microstructure import project_build_job_microstructure

    good = {"solidificationKinetics": {**kin, "solidificationRate_R_mm_s": 30.3, "solidificationRate_R_m_s": 0.0303,
                                       "coolingRate_K_s": 5.5e5}}
    assert project_build_job_microstructure(good)["status"] == "available"
    for patch in ({"coolingRate_K_s": 1.0}, {"solidificationRate_R_mm_s": 0.1, "solidificationRate_R_m_s": 0.0}):
        degenerate = project_build_job_microstructure({"solidificationKinetics": {**good["solidificationKinetics"], **patch}})
        assert degenerate["status"] == "degenerate-floor", patch
        assert degenerate["reason"] == DEGENERATE_FLOOR_REASON


SEGREGATION_FIXTURE = os.path.join(HERE, "..", "tests", "fixtures", "build-job-segregation-blocks.json")
# Result keys of revision v13 (before the segregation block). v14 adds exactly "segregation".
V13_RESULT_KEYS = frozenset((
    "success", "engine", "modelId", "solverRevision", "buildJobIdentity", "assumptions", "alloyId",
    "materialPropertySchemaVersion", "materialPropertyRevision", "materialPropertySha256",
    "materialPropertySnapshot", "materialAuthority", "materialAuthorityRevisionSha256",
    "amBenchMaterialPropertySha256", "amBenchMaterialPropertySnapshot", "processSeed", "scanStrategy",
    "computeTimeMs", "thermal", "slicer", "kinematics", "microstructure", "kinetics", "porosity", "verdict",
    "uq", "ambench", "murakami", "qualification", "cache",
))
_SEGREGATION_COMMON = {"beamDiameter_um": 80, "layerThickness_um": 40, "hatchSpacing_um": 110, "bypassCache": True}


def segregation_fixture_blocks():
    """Real segregation blocks for the UI render test (tests/build-job-segregation.test.tsx)."""
    from lpbf_solidification_microstructure import project_build_job_microstructure
    from lpbf_solidification_segregation import build_job_segregation

    available = run_job({"alloyId": "in718", "laserPower_W": 285, "scanSpeed_mm_s": 960, **_SEGREGATION_COMMON})
    floor_src = run_job({"alloyId": "in718", "laserPower_W": 100, "scanSpeed_mm_s": 960, **_SEGREGATION_COMMON})
    steel = run_job({"alloyId": "ss316l", "laserPower_W": 200, "scanSpeed_mm_s": 800, **_SEGREGATION_COMMON})
    return {
        "available_in718_285_960": available["segregation"],
        # SYNTHETIC microstructure state (clamp floors), real composition-only result.
        "in718_degenerate_floor_synthetic": build_job_segregation(
            "in718", project_build_job_microstructure(_floored_thermal(floor_src["thermal"]))),
        # in625 is not a build-job alloy (resolve_alloy_id refuses it); the block is called directly for the UI test.
        "in625_available": build_job_segregation("in625", available["microstructure"]),
        "ss316l_not_applicable": steel["segregation"],
    }


def check_segregation_fixture():
    with open(SEGREGATION_FIXTURE, encoding="utf-8") as fh:
        committed = json.load(fh)
    current = json.loads(json.dumps(segregation_fixture_blocks()))
    assert committed == current, "tests/fixtures/build-job-segregation-blocks.json is stale: rerun with --write-segregation-fixture"


def _without_volatile(job):
    out = json.loads(json.dumps(job))
    for key in ("computeTimeMs", "cache", "segregation"):
        out.pop(key, None)
    out["thermal"].pop("computeTimeMs", None)
    if isinstance(out.get("slicer"), dict):
        out["slicer"].pop("pythonDurationMs", None)
    return out


def check_build_job_segregation():
    """v14 adds the segregation block and changes nothing else in the result."""
    from unittest.mock import patch

    import lpbf_build_job_solver as build_job_solver
    from lpbf_solidification_segregation import EVIDENCE_LABEL, NOT_APPLICABLE_REASON

    payload = {"alloyId": "in718", "laserPower_W": 285, "scanSpeed_mm_s": 960, **_SEGREGATION_COMMON}
    job = run_job(payload)
    assert set(job) == V13_RESULT_KEYS | {"segregation"}, sorted(set(job) ^ (V13_RESULT_KEYS | {"segregation"}))
    seg = job["segregation"]
    assert seg["status"] in ("available", "unavailable"), seg["status"]
    assert seg["status"] == "available"
    assert seg["alloyId"] == "in718"
    assert seg["evidenceLabel"] == EVIDENCE_LABEL
    pc = seg["processCoupling"]
    assert pc["status"] == job["microstructure"]["status"] == "available"
    for key in ("G_K_m", "R_m_s", "coolingRate_K_s", "morphology", "PDAS_um"):
        assert pc[key] == job["microstructure"][key], key
    assert seg["validity"]["outsideSourceRegime"] is True
    # Every other key equals a run whose segregation hook is replaced: the block is purely additive.
    with patch.object(build_job_solver, "build_job_segregation", lambda alloy_id, micro: None):
        stub = run_job(payload)
    assert stub["segregation"] is None
    assert _without_volatile(job) == _without_volatile(stub)

    steel = run_job({"alloyId": "ss316l", "laserPower_W": 200, "scanSpeed_mm_s": 800, **_SEGREGATION_COMMON})
    assert steel["segregation"]["status"] == "not-applicable"
    assert steel["segregation"]["reason"] == NOT_APPLICABLE_REASON
    for alloy_id, power, speed in (("ti6al4v", 200, 900), ("alsi10mg", 330, 1100)):
        other = run_job({"alloyId": alloy_id, "laserPower_W": power, "scanSpeed_mm_s": speed, **_SEGREGATION_COMMON})
        assert other["segregation"]["status"] == "not-applicable", alloy_id
    check_segregation_fixture()


def check_extent_status_consumers():
    """Heuristic / floored / box-limited melt-pool extent must not become a hard verdict."""
    import copy

    from lpbf_build_job_solver import GEOMETRY_DEPENDENT_GATES, compose_verdict
    from nist_ambench_2018_02 import CBM_CASES, run_ambench_validation

    common = {"alloyId": "in718", "beamDiameter_um": 80, "layerThickness_um": 30,
              "hatchSpacing_um": 100, "bypassCache": True}

    # (a) IN718 10 W / 1000 mm/s / d80: the Rosenthal field stays below liquidus even at its axial peak.
    # (200 W / 1000 mm/s was this case before the 2026-10-06 tier-2 bump, 60 W before the Wave B LA-2 bump and
    # 20 W before the P1 bump of 2026-10-11 (latent-free field): all resolve now. 10 W is below the IN718
    # literature box, so literature_pv warns.)
    heur = run_job({**common, "laserPower_W": 10, "scanSpeed_mm_s": 1000})
    geo = heur["thermal"]["meltPoolGeometry"]
    assert geo["extentStatus"] == "heuristic-width-fallback", geo["extentStatus"]
    v = heur["verdict"]
    assert v["verdict"] == "inconclusive", v["verdict"]
    assert v["geometryResolved"] is False and v["extentStatus"] == "heuristic-width-fallback"
    reason = f"melt-pool geometry not resolved (heuristic-width-fallback): {geo['extentNote']}"
    assert v["verdictReason"] == reason
    by_id = {g["id"]: g for g in v["gates"]}
    assert sorted(v["unavailableGates"]) == sorted(GEOMETRY_DEPENDENT_GATES)
    for gid in ("lof_tang", "lof_wh", "lof_dt", "balling"):
        assert by_id[gid]["status"] == "unavailable", (gid, by_id[gid])
        assert by_id[gid]["reason"] == reason and by_id[gid]["measured"] is None
    # Geometry-independent gates keep their result.
    assert by_id["keyhole"]["status"] == "pass" and by_id["keyhole"]["measured"] == heur["thermal"]["processParameters"]["normalizedEnthalpy"]
    assert by_id["literature_pv"]["status"] == "warn" and by_id["downskin"]["status"] == "pass"
    # Parameter-independent alloy/layer advisories: reported, never verdict-driving.
    assert by_id["recoater"]["status"] == "advisory" and by_id["distortion"]["status"] == "advisory"
    assert v["verdict"] not in ("printable", "do-not-print", "risky")
    assert "do-not-print" not in json.dumps(v["headline"]).lower()
    assert not any(r.startswith("Lack of fusion (Tang)") or "Plateau" in r for r in v["reasons"]), v["reasons"]
    assert v["dominantGate"] not in GEOMETRY_DEPENDENT_GATES
    assert len(v["gates"]) == 9  # shape: no gate removed

    # Every non-"computed" status is inconclusive, even with a geometry that would fail Tang.
    for status in ("width-floor-applied", "search-box-limited", "heuristic-width-fallback"):
        th = copy.deepcopy(heur["thermal"])
        th["meltPoolGeometry"].update(extentStatus=status, extentNote=f"note for {status}")
        th["defectDiagnostics"].update(lackOfFusionStatus="Fail",
                                       ballingInstabilityRisk="High Balling Risk (Capillary Pinch-Off & Humping)")
        out = compose_verdict(th, "in718")
        assert out["verdict"] == "inconclusive" and out["extentStatus"] == status, (status, out["verdict"])
        assert out["verdictReason"] == f"melt-pool geometry not resolved ({status}): note for {status}"
        assert sorted(out["unavailableGates"]) == sorted(GEOMETRY_DEPENDENT_GATES)
        assert all(g["status"] != "fail" for g in out["gates"] if g["id"] in GEOMETRY_DEPENDENT_GATES)

    # (b) A computed case keeps its verdict and gate statuses (no unavailable gate, no new reason).
    comp = run_job({**common, "laserPower_W": 285, "scanSpeed_mm_s": 960})
    assert comp["thermal"]["meltPoolGeometry"]["extentStatus"] == "computed"
    cv = comp["verdict"]
    # Tier 1 verdict policy: balling (Eagar-Tsai L/W screen; High > 5.5 risky, Moderate > 3.85 advisory)
    # never blocks; here ET L/W ~5.1 is Moderate -> advisory. Recoater / distortion are advisories. Since the 2026-10-06 tier-2 bump dH uses the flat-plate
    # absorptivity on every machine (~30.8, keyhole warn -> risky), with or without CUDA.
    dh = float(comp["thermal"]["processParameters"]["normalizedEnthalpy"])
    assert comp["thermal"]["processParameters"]["absorptionModel"] == "flat-plate"
    assert abs(dh - 30.8) < 0.05, dh
    keyhole_blocks = dh > 35.0
    assert cv["verdict"] == ("do-not-print" if keyhole_blocks else "risky"), (dh, cv["verdict"])
    assert cv["geometryResolved"] is True and cv["verdictReason"] is None
    assert cv["unavailableGates"] == [] and cv["geometryIndependentFailGates"] == []
    assert {g["id"]: g["status"] for g in cv["gates"]} == {
        "lof_tang": "pass", "lof_wh": "pass", "lof_dt": "pass", "keyhole": "fail" if keyhole_blocks else "warn",
        "balling": "advisory", "literature_pv": "pass", "recoater": "advisory", "distortion": "advisory",
        "downskin": "pass"}, cv["gates"]
    assert cv["dominantGate"] == "keyhole"
    assert cv["blockingGates"] == (["keyhole"] if keyhole_blocks else []), (dh, cv["blockingGates"])
    assert cv["advisoryGates"] == ["balling", "recoater", "distortion"]
    assert comp["thermal"]["defectDiagnostics"]["ballingScreen"]["band"] == "moderate"
    assert all("reason" not in g and g["measured"] is not None or g["id"] == "downskin" for g in cv["gates"])
    assert not any("not resolved" in r for r in cv["reasons"])

    # NIST AM-Bench: only computed rows enter the overall error.
    def stub(statuses):
        by_power = {(c["power_W"], c["speed_mm_s"]): statuses[c["caseId"]] for c in CBM_CASES}

        def fn(p_w, v_mms, beam_um, overrides):
            status = by_power[(p_w, v_mms)]
            return {"meltPoolGeometry": {
                "length_um": 700.0, "width_um": 150.0, "depth_um": 100.0, "extentStatus": status,
                "extentNote": None if status == "computed" else f"{status} note"}}
        return fn

    mixed = run_ambench_validation(stub({"CBM-A": "computed", "CBM-B": "heuristic-width-fallback",
                                         "CBM-C": "width-floor-applied"}))
    rows = {r["caseId"]: r for r in mixed["cases"]}
    assert rows["CBM-A"]["status"] == "computed" and rows["CBM-A"]["extentStatus"] == "computed"
    assert rows["CBM-A"]["mape_pct"]["mean"] is not None
    for cid, status in (("CBM-B", "heuristic-width-fallback"), ("CBM-C", "width-floor-applied")):
        assert rows[cid]["status"] == "not-computed" and rows[cid]["mape_pct"] is None
        assert rows[cid]["extentStatus"] == status and rows[cid]["extentNote"] == f"{status} note"
    assert mixed["overallMeanMape_pct"] == rows["CBM-A"]["mape_pct"]["mean"]
    assert mixed["computedCases"] == 1 and mixed["notComputedCases"] == 2
    assert "not-computed" in mixed["overallNote"]
    none_computed = run_ambench_validation(stub({c["caseId"]: "search-box-limited" for c in CBM_CASES}))
    assert none_computed["overallMeanMape_pct"] is None
    assert none_computed["computedCases"] == 0 and none_computed["notComputedCases"] == 3
    all_computed = run_ambench_validation(stub({c["caseId"]: "computed" for c in CBM_CASES}))
    means = [r["mape_pct"]["mean"] for r in all_computed["cases"]]
    assert all_computed["overallMeanMape_pct"] == round(sum(means) / 3.0, 2)
    assert all_computed["computedCases"] == 3 and all_computed["notComputedCases"] == 0

    # UQ counts report inconclusive verdicts separately (not as "risky").
    from lpbf_screening_uq import run_screening_uq

    uq = run_screening_uq(base_power_W=200.0, base_beam_um=80.0, n_samples=8, seed=1,
                          thermal_runner=lambda p, d, o: heur["thermal"],
                          verdict_fn=lambda th: compose_verdict(th, "in718"))
    assert uq["counts"] == {"printable": 0, "risky": 0, "do_not_print": 0, "inconclusive": 8}, uq["counts"]
    assert uq["P_printable"] == 0.0


def main():
    from lpbf_job_cache import clear_cache
    from murakami_fatigue_screening import parse_defect_sqrt_areas_text

    clear_cache()

    # Paste parser
    assert parse_defect_sqrt_areas_text("40, 55; 62\n48 70") == [40.0, 55.0, 62.0, 48.0, 70.0]
    assert parse_defect_sqrt_areas_text("") == []

    ti = run_job(
        {
            "alloyId": "ti6al4v",
            "laserPower_W": 200,
            "scanSpeed_mm_s": 900,
            "beamDiameter_um": 80,
            "preheatTemp_C": 150,
            "layerThickness_um": 30,
            "hatchSpacing_um": 100,
            "preset": "nozzle",
            "processSeed": 42,
            "scanStrategy": "stripe",
            "stripeWidth_mm": 5,
            "scanRotation_deg": 67,
            "hatchDwell_ms": 0,
            "bypassCache": True,
        }
    )
    assert ti["success"]
    assert ti["engine"] == "lpbf_build_job"
    assert ti["modelId"] == "rosenthal-screening-v1"
    from lpbf_job_cache import BUILD_JOB_SOLVER_REVISION
    assert ti["solverRevision"] == BUILD_JOB_SOLVER_REVISION
    assert BUILD_JOB_SOLVER_REVISION not in (
        "lpbf-build-job-core-peak-field-v2",
        "lpbf-build-job-kinetics-same-alloy-v3",
        "lpbf-build-job-kinetics-steel-only-v4",
        "lpbf-build-job-microstructure-projection-v5",
        "lpbf-build-job-kinetics-li1998-v6",
        "lpbf-build-job-extent-status-v6",
        "lpbf-build-job-kinetics-li1998-extent-v7",
        "lpbf-build-job-kinetics-li1998-extent-v8",
        "lpbf-build-job-flat-absorptivity-peak-extent-v10",
        "lpbf-build-job-waveb-front-field-marangoni-v11",
        "lpbf-build-job-eagar-tsai-balling-screen-v13",
        "lpbf-build-job-eagar-tsai-balling-screen-v14",
        "lpbf-build-job-eagar-tsai-balling-screen-v15",
        "lpbf-build-job-la6-gusarov-v18",
        "lpbf-build-job-in625-regime-v20",
    ), BUILD_JOB_SOLVER_REVISION
    assert BUILD_JOB_SOLVER_REVISION == "lpbf-build-job-p1-sourced-v21"
    assert ti["processSeed"] == 42
    assert ti["scanStrategy"]["id"] == "stripe"
    assert ti["uq"] is None  # lazy default
    assert ti["ambench"] is None  # lazy default
    assert ti["cache"]["hit"] is False
    assert any("Hash cache" in a for a in ti["assumptions"])
    assert any("skips UQ" in a or "Default job skips" in a for a in ti["assumptions"])
    assert ti["murakami"]["status"] == "data_not_supplied"
    assert "pasteHint" in ti["murakami"]
    assert len(ti["assumptions"]) >= 6
    assert any("Goldak" in a for a in ti["assumptions"])
    assert any("King" in a for a in ti["assumptions"])
    assert any("Tang" in a for a in ti["assumptions"])
    assert any("10.1115/1.4031649" in a for a in ti["assumptions"])
    assert "verdict" in ti["verdict"]
    assert ti["verdict"]["verdict"] in ("printable", "risky", "do-not-print")
    assert ti["thermal"]["meltPoolGeometry"]["width_um"] > 0
    assert ti["materialPropertySchemaVersion"] == 1
    assert ti["materialPropertyRevision"] == ti["buildJobIdentity"]["materialPropertyRevision"]
    assert len(ti["materialPropertySha256"]) == 64
    assert ti["materialPropertySnapshot"]["alloyId"] == "ti6al4v"
    from lpbf_build_job_material_snapshot import build_build_job_identity

    assert ti["buildJobIdentity"] == {
        "schemaVersion": 1,
        "alloyId": "ti6al4v",
        "modelId": ti["modelId"],
        "solverRevision": ti["solverRevision"],
        "materialPropertySchemaVersion": ti["materialPropertySchemaVersion"],
        "materialPropertyRevision": "build-job-effective-properties-v1",
        "materialPropertySha256": ti["materialPropertySha256"],
        "sha256": build_build_job_identity(
            "Ti-6Al-4V", ti["modelId"], ti["solverRevision"],
            ti["materialPropertySha256"], ti["materialPropertySchemaVersion"],
        )["sha256"],
    }
    assert len(ti["buildJobIdentity"]["sha256"]) == 64
    assert "gates" in ti["verdict"] and len(ti["verdict"]["gates"]) >= 7

    # Kinetics: only the alloy's own kinetics model, never a substituted alloy (formerly every
    # alloy other than IN718/Ti-6Al-4V silently got AISI 4140 kinetics).
    check_build_job_kinetics(ti)
    check_kinetics_fixture()

    # Same-alloy aliases are accepted but normalized before solver invocation.
    from unittest.mock import patch
    import lpbf_build_job_solver as build_job_solver

    received_materials = {}
    calculate_thermal = build_job_solver.calculate_meltpool_physics
    solve_material_slicer = build_job_solver.solve_slicer

    def capture_thermal_name(name, *args, **kwargs):
        received_materials["thermal"] = name
        return calculate_thermal(name, *args, **kwargs)

    def capture_slicer_name(payload):
        received_materials["slicer"] = payload["material"]
        return solve_material_slicer(payload)

    with patch.object(build_job_solver, "calculate_meltpool_physics", capture_thermal_name), patch.object(
        build_job_solver, "solve_slicer", capture_slicer_name
    ):
        aliased_ti = run_job(
            {
                "alloyId": "ti-6al-4v",
                "thermalMaterial": "Ti-6Al-4V ELI",
                "slicerMaterial": "Ti-6Al-4V",
                "laserPower_W": 200,
                "scanSpeed_mm_s": 900,
                "beamDiameter_um": 80,
                "preheatTemp_C": 150,
                "layerThickness_um": 30,
                "hatchSpacing_um": 100,
                "bypassCache": True,
            }
        )
    assert aliased_ti["success"]
    assert received_materials == {"thermal": "Ti-6Al-4V", "slicer": "Ti-6Al-4V ELI"}
    assert aliased_ti["materialPropertySha256"] == ti["materialPropertySha256"]
    assert aliased_ti["buildJobIdentity"] == ti["buildJobIdentity"]

    # Hash cache hit on identical request
    clear_cache()
    a = run_job(
        {
            "alloyId": "in718",
            "laserPower_W": 285,
            "scanSpeed_mm_s": 960,
            "beamDiameter_um": 80,
            "layerThickness_um": 40,
            "hatchSpacing_um": 110,
        }
    )
    b = run_job(
        {
            "alloyId": "in718",
            "laserPower_W": 285,
            "scanSpeed_mm_s": 960,
            "beamDiameter_um": 80,
            "layerThickness_um": 40,
            "hatchSpacing_um": 110,
        }
    )
    assert a["cache"]["hit"] is False
    assert b["cache"]["hit"] is True
    assert b["verdict"]["verdict"] == a["verdict"]["verdict"]
    assert b["cache"]["stats"]["hits"] >= 1
    assert b["materialPropertySha256"] == a["materialPropertySha256"]
    check_build_job_microstructure(a)
    check_build_job_microstructure_fallback()
    check_build_job_microstructure_degenerate_floor()
    check_microstructure_fixture()
    check_build_job_segregation()

    # The effective thermal input is frozen once per request and changes cache identity.
    from four_alloy_materials import _THERMAL

    old_conductivity = _THERMAL["in718"]["thermal_conductivity_W_mK"]
    try:
        _THERMAL["in718"]["thermal_conductivity_W_mK"] = old_conductivity + 1.0
        changed = run_job({"alloyId": "in718", "laserPower_W": 285,
                           "scanSpeed_mm_s": 960, "beamDiameter_um": 80,
                           "layerThickness_um": 40, "hatchSpacing_um": 110})
        assert changed["cache"]["hit"] is False
        assert changed["materialPropertySha256"] != a["materialPropertySha256"]
        assert changed["buildJobIdentity"]["sha256"] != a["buildJobIdentity"]["sha256"]
        assert changed["materialPropertySnapshot"]["thermal"]["thermal_conductivity_W_mK"] == old_conductivity + 1.0
        assert changed["thermal"]["processParameters"]["effectiveConductivity_W_mK"] != a["thermal"]["processParameters"]["effectiveConductivity_W_mK"]
    finally:
        _THERMAL["in718"]["thermal_conductivity_W_mK"] = old_conductivity

    # Source-only fields are part of the shared authority revision even when the
    # build-job effective-property projection does not consume them.
    old_surface_tension = _THERMAL["in718"]["surface_tension_N_m"]
    try:
        _THERMAL["in718"]["surface_tension_N_m"] = old_surface_tension + 0.01
        source_changed = run_job({"alloyId": "in718", "laserPower_W": 285,
                                  "scanSpeed_mm_s": 960, "beamDiameter_um": 80,
                                  "layerThickness_um": 40, "hatchSpacing_um": 110})
        assert source_changed["cache"]["hit"] is False
        assert source_changed["materialPropertySha256"] == a["materialPropertySha256"]
        assert source_changed["materialAuthorityRevisionSha256"] != a["materialAuthorityRevisionSha256"]
    finally:
        _THERMAL["in718"]["surface_tension_N_m"] = old_surface_tension

    # A legacy or corrupted hit cannot bypass the current snapshot contract.
    with patch.object(build_job_solver, "cache_get", return_value={
        "success": True, "alloyId": "in718", "computeTimeMs": 1,
    }):
        stale = run_job({"alloyId": "in718", "laserPower_W": 285,
                         "scanSpeed_mm_s": 960, "beamDiameter_um": 80,
                         "layerThickness_um": 40, "hatchSpacing_um": 110})
    assert stale["cache"]["hit"] is False
    assert stale["materialPropertySha256"] == a["materialPropertySha256"]

    with patch.object(build_job_solver, "cache_get", return_value={
        **a, "solverRevision": "older-build-job-implementation",
    }):
        revision_stale = run_job({"alloyId": "in718", "laserPower_W": 285,
                                  "scanSpeed_mm_s": 960, "beamDiameter_um": 80,
                                  "layerThickness_um": 40, "hatchSpacing_um": 110})
    assert revision_stale["cache"]["hit"] is False
    assert revision_stale["solverRevision"] == BUILD_JOB_SOLVER_REVISION

    import lpbf_job_cache
    from lpbf_job_cache import build_cache_key, mesh_fingerprint

    mesh_a = [[[-1, 0, 0], [1, 0, 0], [0, 1, 1]]] * 9
    mesh_b = [list(tri) for tri in mesh_a]
    mesh_b[1] = [[-1, 0, 0], [1, 0, 0], [0, 2, 1]]
    assert mesh_fingerprint(mesh_a) != mesh_fingerprint(mesh_b)
    assert build_cache_key({"customTriangles": mesh_a}) != build_cache_key({"customTriangles": mesh_b})
    assert build_cache_key({"recoatTimePerLayer_s": 9.0}) != build_cache_key({"recoatTimePerLayer_s": 12.0})
    revision_key = build_cache_key({"solverRevision": "untrusted-client-value"})
    assert revision_key == build_cache_key({})
    with patch.object(lpbf_job_cache, "BUILD_JOB_SOLVER_REVISION", "next-implementation"):
        assert build_cache_key({}) != revision_key

    base_identity = a["buildJobIdentity"]
    identity_inputs = (
        base_identity["alloyId"], base_identity["modelId"], base_identity["solverRevision"],
        base_identity["materialPropertySha256"], base_identity["materialPropertySchemaVersion"],
    )
    model_identity = build_build_job_identity(
        identity_inputs[0], "next-model", *identity_inputs[2:]
    )
    solver_identity = build_build_job_identity(
        identity_inputs[0], identity_inputs[1], "next-solver", *identity_inputs[3:]
    )
    snapshot_schema_identity = build_build_job_identity(
        *identity_inputs[:4], identity_inputs[4] + 1
    )
    snapshot_revision_identity = build_build_job_identity(
        *identity_inputs[:4], identity_inputs[4], "build-job-effective-properties-v2"
    )
    assert model_identity["materialPropertySha256"] == base_identity["materialPropertySha256"]
    assert solver_identity["materialPropertySha256"] == base_identity["materialPropertySha256"]
    assert len({
        base_identity["sha256"], model_identity["sha256"], solver_identity["sha256"],
        snapshot_schema_identity["sha256"], snapshot_revision_identity["sha256"],
    }) == 5
    keyed = {"buildJobIdentity": base_identity}
    base_identity_key = build_cache_key(keyed)
    for variant in (model_identity, solver_identity, snapshot_schema_identity, snapshot_revision_identity):
        assert build_cache_key({"buildJobIdentity": variant}) != base_identity_key

    # UQ must carry the whole frozen base, even when a sample changes only one
    # property and the live registry changes after the base solve.
    observed_uq_properties = {}

    def inspect_uq_thermal(*, thermal_runner, n_samples, **_kwargs):
        original_cp = _THERMAL["in718"]["specific_heat_J_kgK"]
        try:
            _THERMAL["in718"]["specific_heat_J_kgK"] = original_cp + 100.0

            def capture_uq_thermal(_name, *args, **kwargs):
                observed_uq_properties.update(kwargs["prop_overrides"])
                return a["thermal"]

            with patch.object(build_job_solver, "calculate_meltpool_physics", capture_uq_thermal):
                thermal_runner(285.0, 80.0, {"_uq_k_scale": 1.1})
        finally:
            _THERMAL["in718"]["specific_heat_J_kgK"] = original_cp
        return {
            "P_printable": 0.5, "normalizedEnthalpy": {},
            "dominantUncertainty": "k", "nSamples": n_samples,
            "bands": {"power_rel": 0.03, "absorptivity_rel": 0.15},
            "defectSamples": [],
        }

    with patch.object(build_job_solver, "run_screening_uq", side_effect=inspect_uq_thermal):
        uq_snapshot = run_job({"alloyId": "in718", "enableUq": True, "uqSamples": 8,
                               "bypassCache": True})
    assert uq_snapshot["success"] is True
    assert observed_uq_properties["specific_heat_J_kgK"] == a["materialPropertySnapshot"]["thermal"]["specific_heat_J_kgK"]
    assert observed_uq_properties["thermal_conductivity_W_mK"] == 1.1 * a["materialPropertySnapshot"]["thermal"]["thermal_conductivity_W_mK"]
    assert set(a["materialPropertySnapshot"]["thermal"]).issubset(observed_uq_properties)

    # AM-Bench uses an independent IN625 comparison snapshot, frozen across
    # all cases, and only its own digest changes when those props change.
    from nist_ambench_2018_02 import IN625_VALIDATION_PROPS, run_ambench_validation
    from lpbf_build_job_material_snapshot import build_ambench_material_property_snapshot

    comparison_snapshot, comparison_sha = build_ambench_material_property_snapshot(IN625_VALIDATION_PROPS)
    comparison_calls = []

    def capture_comparison(_power, _speed, _beam, props):
        comparison_calls.append(props)
        return {"meltPoolGeometry": {"length_um": 659.0, "width_um": 171.0, "depth_um": 151.0}}

    run_ambench_validation(capture_comparison, material_props=comparison_snapshot["thermal"])
    assert len(comparison_calls) == 3
    assert all(props == comparison_snapshot["thermal"] for props in comparison_calls)

    def stub_ambench(_thermal_runner, material_props=None):
        assert material_props["base"] == "Ni"
        return {"source": {"doi": "10.1007/s40192-020-00169-1"}, "cases": []}

    comparison_input = {"alloyId": "Ti-6Al-4V", "includeAmbench": True}
    clear_cache()
    with patch.object(build_job_solver, "run_ambench_validation", side_effect=stub_ambench):
        compared = run_job(comparison_input)
        compared_alias = run_job({**comparison_input, "alloyId": "ti6al4v"})
        original_k = IN625_VALIDATION_PROPS["thermal_conductivity_W_mK"]
        try:
            IN625_VALIDATION_PROPS["thermal_conductivity_W_mK"] = original_k + 1.0
            compared_changed = run_job(comparison_input)
        finally:
            IN625_VALIDATION_PROPS["thermal_conductivity_W_mK"] = original_k
    assert compared["cache"]["hit"] is False and compared_alias["cache"]["hit"] is True
    assert compared["amBenchMaterialPropertySha256"] == comparison_sha
    assert compared_alias["amBenchMaterialPropertySha256"] == comparison_sha
    assert compared["amBenchMaterialPropertySnapshot"] == comparison_snapshot
    assert compared_changed["cache"]["hit"] is False
    assert compared_changed["materialPropertySha256"] == compared["materialPropertySha256"]
    assert compared_changed["amBenchMaterialPropertySha256"] != comparison_sha

    # Murakami paste path + alloy HV default
    mur = run_job(
        {
            "alloyId": "in718",
            "laserPower_W": 285,
            "scanSpeed_mm_s": 960,
            "beamDiameter_um": 80,
            "layerThickness_um": 40,
            "hatchSpacing_um": 110,
            "defectSqrtAreasPaste": "40, 55, 62, 48, 70",
            "bypassCache": True,
        }
    )
    assert mur["murakami"]["status"] == "screening_estimate"
    assert mur["murakami"]["hardnessSource"] == "alloy_default"
    assert mur["murakami"]["hardness_HV"] == 380.0
    assert mur["murakami"]["fatigueLimit_internal_MPa"] > 0

    # R = v·cosθ
    flat = run_job(
        {
            "alloyId": "ti6al4v",
            "laserPower_W": 200,
            "scanSpeed_mm_s": 900,
            "beamDiameter_um": 80,
            "preheatTemp_C": 150,
            "layerThickness_um": 30,
            "hatchSpacing_um": 100,
            "inclineAngle_deg": 0,
            "bypassCache": True,
        }
    )
    inclined = run_job(
        {
            "alloyId": "ti6al4v",
            "laserPower_W": 200,
            "scanSpeed_mm_s": 900,
            "beamDiameter_um": 80,
            "preheatTemp_C": 150,
            "layerThickness_um": 30,
            "hatchSpacing_um": 100,
            "inclineAngle_deg": 60,
            "bypassCache": True,
        }
    )
    r0 = flat["thermal"]["solidificationKinetics"]["solidificationRate_R_m_s"]
    r60 = inclined["thermal"]["solidificationKinetics"]["solidificationRate_R_m_s"]
    assert r60 < r0 * 0.6, (r0, r60)

    bloated = [[[0, 0, 0], [1, 0, 0], [0, 1, 0]]] * 15000
    capped = run_job(
        {
            "alloyId": "in718",
            "laserPower_W": 285,
            "scanSpeed_mm_s": 960,
            "beamDiameter_um": 80,
            "layerThickness_um": 40,
            "hatchSpacing_um": 110,
            "customTriangles": bloated,
            "triangleCountNative": 15000,
            "maxTriangles": 12000,
            "preset": "custom",
            "bypassCache": True,
        }
    )
    assert capped["success"]
    assert capped["slicer"]["meshMetrics"]["triangleCount"] <= 12000

    lof = run_job(
        {
            "alloyId": "in718",
            "laserPower_W": 90,
            "scanSpeed_mm_s": 1400,
            "beamDiameter_um": 80,
            "preheatTemp_C": 80,
            "layerThickness_um": 40,
            "hatchSpacing_um": 110,
            "preset": "nozzle",
            "bypassCache": True,
        }
    )
    # 90 W / 1400 mm/s has no resolvable Rosenthal liquidus extent (heuristic W/D/L): the Tang
    # LoF verdict is unavailable rather than a hard do-not-print built on heuristic numbers.
    if lof["thermal"]["meltPoolGeometry"]["extentStatus"] == "computed":
        assert lof["verdict"]["verdict"] in ("risky", "do-not-print"), lof["verdict"]
    else:
        assert lof["verdict"]["verdict"] == "inconclusive", lof["verdict"]
        assert "lof_tang" in lof["verdict"]["unavailableGates"]
    assert lof["verdict"]["suggestedPatch"] is not None

    kh = run_job(
        {
            "alloyId": "ti6al4v",
            "laserPower_W": 400,
            "scanSpeed_mm_s": 400,
            "beamDiameter_um": 80,
            "preheatTemp_C": 80,
            "layerThickness_um": 30,
            "hatchSpacing_um": 100,
            "preset": "nozzle",
            "bypassCache": True,
        }
    )
    assert kh["verdict"]["dominantGate"] == "keyhole", kh["verdict"]

    ds = run_job(
        {
            "alloyId": "ti6al4v",
            "laserPower_W": 200,
            "scanSpeed_mm_s": 900,
            "beamDiameter_um": 80,
            "preheatTemp_C": 150,
            "layerThickness_um": 30,
            "hatchSpacing_um": 100,
            "downskinOverhang_deg": 60,
            "bypassCache": True,
        }
    )
    assert ds["verdict"]["dominantGate"] == "downskin" or any(
        g["id"] == "downskin" and g["status"] == "fail" for g in ds["verdict"]["gates"]
    ), ds["verdict"]

    unsupported = run_job({"alloyId": "Inconel 625", "bypassCache": True})
    assert unsupported["success"] is False
    assert "Unsupported LPBF alloy identity" in unsupported["error"]
    assert "No surrogate alloy" in unsupported["error"]

    thermal_mismatch = run_job(
        {"alloyId": "ss316l", "thermalMaterial": "Inconel 718", "bypassCache": True}
    )
    assert thermal_mismatch["success"] is False
    assert "thermalMaterial" in thermal_mismatch["error"]
    slicer_mismatch = run_job(
        {"alloyId": "ss316l", "slicerMaterial": "CoCrMo", "bypassCache": True}
    )
    assert slicer_mismatch["success"] is False
    assert "slicerMaterial" in slicer_mismatch["error"]

    # A stale successful cache entry must not bypass material identity checks.
    with patch.object(
        build_job_solver,
        "cache_get",
        return_value={"success": True, "alloyId": "ss316l", "computeTimeMs": 1},
    ) as mocked_cache_get:
        cached_mismatch = build_job_solver.solve_lpbf_build_job(
            {"alloyId": "ss316l", "thermalMaterial": "Inconel 718"}
        )
    assert cached_mismatch["success"] is False
    assert "thermalMaterial" in cached_mismatch["error"]
    mocked_cache_get.assert_not_called()

    # Equivalent alloy/material aliases should resolve to one cache identity.
    cache_keys = []
    from lpbf_build_job_material_snapshot import build_material_property_snapshot
    aliased_snapshot, aliased_sha = build_material_property_snapshot(
        "ti6al4v", "Ti-6Al-4V", "Ti-6Al-4V ELI"
    )

    def return_seeded_cache_entry(key):
        cache_keys.append(key)
        return {
            "success": True, "alloyId": "ti6al4v", "computeTimeMs": 1,
            "materialPropertySha256": aliased_sha,
            "materialPropertySnapshot": aliased_snapshot,
        }

    with patch.object(build_job_solver, "cache_get", side_effect=return_seeded_cache_entry):
        alias_cache_a = build_job_solver.solve_lpbf_build_job(
            {
                "alloyId": "ti6al4v",
                "thermalMaterial": "Ti-6Al-4V ELI",
                "slicerMaterial": "Ti-6Al-4V",
            }
        )
        alias_cache_b = build_job_solver.solve_lpbf_build_job(
            {
                "alloyId": "Ti-6Al-4V",
                "thermalMaterial": "Ti-6Al-4V",
                "slicerMaterial": "Ti-6Al-4V ELI",
            }
        )
    assert alias_cache_a["success"] and alias_cache_b["success"]
    assert len(cache_keys) == 2 and cache_keys[0] == cache_keys[1]

    omitted_alloy = run_job({"bypassCache": True})
    assert omitted_alloy["success"] is True
    assert omitted_alloy["alloyId"] == "in718"

    check_extent_status_consumers()

    if not SLOW:
        print("PASS: solve_lpbf_build_job Phase 5 fast (cache, lazy UQ/NIST, Murakami paste)")
        print("HINT: re-run with --slow for UQ + NIST AM-Bench coverage")
        return 0

    # --- SLOW: UQ + NIST ---
    uq = run_job(
        {
            "alloyId": "ti6al4v",
            "laserPower_W": 200,
            "scanSpeed_mm_s": 900,
            "beamDiameter_um": 80,
            "preheatTemp_C": 150,
            "layerThickness_um": 30,
            "hatchSpacing_um": 100,
            "processSeed": 42,
            "enableUq": True,
            "uqSamples": 24,
            "includeAmbench": True,
            "bypassCache": True,
        }
    )
    assert uq["uq"] is not None
    assert uq["uq"]["enabled"] is True
    assert uq["uq"]["nSamples"] == 24
    assert 0.0 <= uq["uq"]["P_printable"] <= 1.0
    assert "absorptivity" in uq["uq"]["sobolProxy"]
    assert uq["uq"].get("sensitivityMethod") == "spearman-proxy"
    assert uq["ambench"] is not None
    assert uq["ambench"]["source"]["doi"] == "10.1007/s40192-020-00169-1"
    assert len(uq["ambench"]["cases"]) == 3
    assert uq["ambench"]["cases"][0]["nist"]["length_um"] == 659.0
    amb_rows = uq["ambench"]["cases"]
    assert all(r["status"] in ("computed", "not-computed") for r in amb_rows)
    assert all((r["status"] == "computed") == (r["extentStatus"] == "computed") for r in amb_rows)
    assert all((r["mape_pct"] is None) == (r["status"] == "not-computed") for r in amb_rows)
    assert uq["ambench"]["computedCases"] + uq["ambench"]["notComputedCases"] == 3
    computed_means = [r["mape_pct"]["mean"] for r in amb_rows if r["status"] == "computed"]
    assert uq["ambench"]["overallMeanMape_pct"] == (
        round(sum(computed_means) / len(computed_means), 2) if computed_means else None)
    assert uq["qualification"]["status"] == "not_executed"

    uq2 = run_job(
        {
            "alloyId": "ti6al4v",
            "laserPower_W": 200,
            "scanSpeed_mm_s": 900,
            "beamDiameter_um": 80,
            "preheatTemp_C": 150,
            "layerThickness_um": 30,
            "hatchSpacing_um": 100,
            "processSeed": 42,
            "enableUq": True,
            "uqSamples": 24,
            "includeAmbench": False,
            "bypassCache": True,
        }
    )
    assert uq2["uq"]["P_printable"] == uq["uq"]["P_printable"]

    print("PASS: solve_lpbf_build_job Phase 5 slow (UQ Spearman-proxy + NIST AMB2018-02)")
    return 0


if __name__ == "__main__":
    if "--write-kinetics-fixture" in sys.argv:
        with open(KINETICS_FIXTURE, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(kinetics_fixture_blocks(), fh, indent=1, ensure_ascii=False)
            fh.write("\n")
        sys.exit(0)
    if "--write-segregation-fixture" in sys.argv:
        with open(SEGREGATION_FIXTURE, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(segregation_fixture_blocks(), fh, indent=1, ensure_ascii=False)
            fh.write("\n")
        sys.exit(0)
    if "--write-microstructure-fixture" in sys.argv:
        with open(MICROSTRUCTURE_FIXTURE, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(microstructure_fixture_blocks(), fh, indent=1, ensure_ascii=False)
            fh.write("\n")
        sys.exit(0)
    sys.exit(main())
