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
    # P6 (2026-10-11): the former 285 W / 960 mm/s available case serves null G/R (the served depth comes from the
    # Fabbro keyhole leg), so the available case is the conduction point 150 W / 1200 mm/s; the former
    # "screening-fallback" 10 W / 3000 mm/s case (tail-length heuristic, removed) is unavailable with its reason.
    available = run_job({"alloyId": "in718", "laserPower_W": 150, "scanSpeed_mm_s": 1200, **common})
    keyhole_leg = run_job({"alloyId": "in718", "laserPower_W": 285, "scanSpeed_mm_s": 960, **common})
    few_samples = run_job({"alloyId": "in718", "laserPower_W": 10, "scanSpeed_mm_s": 3000, **common})
    # Wave B KS-1: the clamp-floor state is unreachable on real builds now (P6 removed the floors altogether), so
    # the degenerate block is projected from the real IN718 100/960 thermal result with its kinetics moved onto
    # the former floors (SYNTHETIC).
    degenerate = run_job({"alloyId": "in718", "laserPower_W": 100, "scanSpeed_mm_s": 960, **common})
    return {
        "available_in718_150_1200": available["microstructure"],
        "unavailable_keyhole_leg_in718_285_960": keyhole_leg["microstructure"],
        "unavailable_few_samples_in718_10_3000": few_samples["microstructure"],
        # Historical fixture key retained; SOL-A1 has no floor branch and carries the ordinary null envelope.
        "degenerate_floor_synthetic": project_build_job_microstructure(degenerate["thermal"]),
        "unavailable_no_kinetics": project_build_job_microstructure({}),
    }


def _floored_thermal(thermal):
    """Synthetic archived flat keys must not override the current envelope."""
    import copy
    floored = copy.deepcopy(thermal)
    floored["solidificationKinetics"].update(solidificationRate_R_m_s=1e-4, coolingRate_K_s=1.0)
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
    from lpbf_build_job_solver import build_job_kinetics
    for aid in ("ti6al4v", "in718", "ss316l", "alsi10mg"):
        for thermal in ({}, ti["thermal"], {"solidificationKinetics": {"coolingRate_K_s": 1e6}}):
            kin = build_job_kinetics(aid, thermal)
            assert kin["status"] == "unavailable"
            assert kin["reasons"][0]["code"] == "missing-thermal-history"
            assert kin["buildCoolingRate_C_s"] is None and kin["reportedCoolingRate_K_s"] is None
            assert kin["cctContinuousCoolingMap"] is None
    check_kinetics_fixture()


def check_build_job_microstructure(job):
    from quantity_envelope import envelope_problems
    micro = job["microstructure"]
    kin = job["thermal"]["solidificationKinetics"]
    assert micro["schema"] == "lpbf-solidification-microstructure-2"
    assert micro["status"] == "unavailable"
    assert micro["quantities"] == kin["quantities"]
    assert micro["inputProvenance"] == kin["inputProvenance"]
    assert envelope_problems(micro) == []
    assert "G_K_m" not in micro and "doi" not in micro
    assert job["kinetics"]["reasons"][0]["code"] == "missing-thermal-history"


def check_build_job_microstructure_fallback():
    from lpbf_solidification_microstructure import project_build_job_microstructure
    # Retired flat payloads cannot reintroduce a numeric fallback.
    for old in ({"thermalGradient_G_K_m": 1e6, "solidificationRate_R_m_s": 0.1, "coolingRate_K_s": 1e5}, {}):
        micro = project_build_job_microstructure({"solidificationKinetics": old})
        assert micro["status"] == "unavailable"
        assert all(q["value"] is None for q in micro["quantities"].values())


DEGENERATE_FLOOR_REASON = (
    "solidification front degenerate: floor-clamped R/cooling "
    "(R <= 1e-4 m/s or cooling <= 1 K/s), not a computed value"
)


def check_build_job_microstructure_degenerate_floor():
    from lpbf_solidification_microstructure import project_build_job_microstructure
    job = run_job({"alloyId": "in718", "laserPower_W": 100, "scanSpeed_mm_s": 960, "beamDiameter_um": 80,
                   "layerThickness_um": 40, "hatchSpacing_um": 110, "bypassCache": True})
    projected = project_build_job_microstructure(_floored_thermal(job["thermal"]))
    assert projected["quantities"] == job["microstructure"]["quantities"]
    assert projected["status"] == "unavailable"


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

    # P6 (2026-10-11): the available case is the conduction point 150 W / 1200 mm/s (the former 285 W / 960 mm/s
    # point serves null G/R: Fabbro keyhole leg); its segregation block is kept as the keyhole-leg fixture.
    available = run_job({"alloyId": "in718", "laserPower_W": 150, "scanSpeed_mm_s": 1200, **_SEGREGATION_COMMON})
    keyhole_leg = run_job({"alloyId": "in718", "laserPower_W": 285, "scanSpeed_mm_s": 960, **_SEGREGATION_COMMON})
    floor_src = run_job({"alloyId": "in718", "laserPower_W": 100, "scanSpeed_mm_s": 960, **_SEGREGATION_COMMON})
    steel = run_job({"alloyId": "ss316l", "laserPower_W": 200, "scanSpeed_mm_s": 800, **_SEGREGATION_COMMON})
    return {
        "available_in718_150_1200": available["segregation"],
        "in718_unavailable_keyhole_leg_285_960": keyhole_leg["segregation"],
        # Historical fixture key retained; ordinary SOL-A1 null front, real composition-only result.
        "in718_degenerate_floor_synthetic": build_job_segregation(
            "in718", project_build_job_microstructure(floor_src["thermal"])),
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
    from unittest.mock import patch
    import lpbf_build_job_solver as build_job_solver
    payload = {"alloyId": "in718", "laserPower_W": 150, "scanSpeed_mm_s": 1200, **_SEGREGATION_COMMON}
    job = run_job(payload)
    seg = job["segregation"]
    assert seg["schema"] == "lpbf-solidification-segregation-2"
    assert seg["status"] == "computed"
    assert seg["quantities"]["nominalBinary"]["sourceEvidenceKind"] == "Unresolved"
    assert seg["processCoupling"]["quantities"] == job["microstructure"]["quantities"]
    assert seg["processCoupling"]["usedInCalculation"] is False
    assert seg["rapidSolidification"]["status"] == "unavailable"
    # The composition-only addition cannot change other job decisions.
    with patch.object(build_job_solver, "build_job_segregation", lambda alloy_id, micro: None):
        stub = run_job(payload)
    assert _without_volatile(job) == _without_volatile(stub)
    for aid in ("ss316l", "ti6al4v", "alsi10mg"):
        from lpbf_solidification_segregation import build_job_segregation
        assert build_job_segregation(aid, job["microstructure"])["status"] == "not-requested"
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
    # P7a: recoater and distortion are always listed (no sourced stress model) next to the geometry gates.
    assert sorted(v["unavailableGates"]) == sorted(GEOMETRY_DEPENDENT_GATES + ("recoater", "distortion"))
    for gid in ("lof_tang", "lof_wh", "lof_dt", "balling"):
        assert by_id[gid]["status"] == "unavailable", (gid, by_id[gid])
        assert by_id[gid]["reason"] == reason and by_id[gid]["measured"] is None
    # Geometry-independent gates keep their result.
    assert by_id["keyhole"]["status"] == "pass" and by_id["keyhole"]["measured"] == heur["thermal"]["processParameters"]["normalizedEnthalpy"]
    assert by_id["literature_pv"]["status"] == "advisory" and by_id["downskin"]["status"] == "pass"  # P7a: box is advisory
    # P7a: recoater and distortion are not evaluated (no sourced stress model), never verdict-driving.
    assert by_id["recoater"]["status"] == "not-evaluated" and by_id["distortion"]["status"] == "not-evaluated"
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
        assert sorted(out["unavailableGates"]) == sorted(GEOMETRY_DEPENDENT_GATES + ("recoater", "distortion"))
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
    # P7a: keyhole mode (dH/hs 30.8 >= 20) is risky and never do-not-print; the level 30 is an advisory.
    assert cv["verdict"] == "risky", (dh, cv["verdict"])
    assert cv["verdictBasis"] == "sourced-criteria-only"
    assert cv["geometryResolved"] is True and cv["verdictReason"] is None
    assert cv["unavailableGates"] == ["recoater", "distortion"] and cv["geometryIndependentFailGates"] == []
    # P7b (2026-10-14): the Eagar-Tsai L/W of this case is 3.6 (melting-point k / cp shorten the pool), below the
    # Moderate edge 3.85, so the balling screen is Stable and the gate passes (it was Moderate / advisory at ~5.1).
    assert {g["id"]: g["status"] for g in cv["gates"]} == {
        "lof_tang": "pass", "lof_wh": "pass", "lof_dt": "pass", "keyhole": "warn",
        "balling": "pass", "literature_pv": "pass", "recoater": "not-evaluated", "distortion": "not-evaluated",
        "downskin": "pass"}, cv["gates"]
    assert cv["dominantGate"] == "keyhole"
    assert cv["blockingGates"] == [], (dh, cv["blockingGates"])
    assert cv["advisoryGates"] == []
    assert comp["thermal"]["defectDiagnostics"]["ballingScreen"]["band"] == "stable"
    assert all("reason" not in g and g["measured"] is not None or g["id"] in ("downskin", "recoater", "distortion")
               for g in cv["gates"])
    assert any(a.startswith("Advisory: keyhole porosity legacy level") for a in cv["advisories"])
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
        "lpbf-build-job-p1-sourced-v21",
        "lpbf-build-job-p1-sourced-v22",
        "lpbf-build-job-p6-containment-v23",
        "lpbf-build-job-p7a-rules-and-nulls-v24",
    ), BUILD_JOB_SOLVER_REVISION
    assert BUILD_JOB_SOLVER_REVISION == "lpbf-build-job-sola1-v26"  # P7b (2026-10-14)
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
        # P7b (2026-10-14): IN718 serves the melting-point k (29.6, Mills 2002 b) in the conduction kernel, so a solid
        # k change moves the identity but not the served kernel; the melting-point key moves it (next block).
        assert changed["thermal"]["processParameters"]["effectiveConductivity_W_mK"] == a["thermal"]["processParameters"]["effectiveConductivity_W_mK"]
    finally:
        _THERMAL["in718"]["thermal_conductivity_W_mK"] = old_conductivity
    old_melt_conductivity = _THERMAL["in718"]["thermal_conductivity_melt_W_mK"]
    try:
        _THERMAL["in718"]["thermal_conductivity_melt_W_mK"] = old_melt_conductivity + 1.0
        melt_changed = run_job({"alloyId": "in718", "laserPower_W": 285,
                                "scanSpeed_mm_s": 960, "beamDiameter_um": 80,
                                "layerThickness_um": 40, "hatchSpacing_um": 110})
        assert melt_changed["cache"]["hit"] is False
        assert melt_changed["materialPropertySha256"] != a["materialPropertySha256"]
        assert melt_changed["thermal"]["processParameters"]["effectiveConductivity_W_mK"] == round(old_melt_conductivity + 1.0, 3)
        assert melt_changed["thermal"]["processParameters"]["effectiveConductivity_W_mK"] != a["thermal"]["processParameters"]["effectiveConductivity_W_mK"]
    finally:
        _THERMAL["in718"]["thermal_conductivity_melt_W_mK"] = old_melt_conductivity

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
    # P6 (2026-10-11): the build-surface incline no longer multiplies R (R = v n_x on the conduction-field
    # interface); the angle is echoed and the assumptions say so. A conduction Ti-6Al-4V point is used (the 200 W /
    # 900 mm/s point serves null G/R: Fabbro keyhole leg).
    flat = run_job(
        {
            "alloyId": "ti6al4v",
            "laserPower_W": 150,
            "scanSpeed_mm_s": 1200,
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
            "laserPower_W": 150,
            "scanSpeed_mm_s": 1200,
            "beamDiameter_um": 80,
            "preheatTemp_C": 150,
            "layerThickness_um": 30,
            "hatchSpacing_um": 100,
            "inclineAngle_deg": 60,
            "bypassCache": True,
        }
    )
    r0 = flat["thermal"]["solidificationKinetics"]["quantities"]["normalSpeed"]["value"]
    r60 = inclined["thermal"]["solidificationKinetics"]["quantities"]["normalSpeed"]["value"]
    assert r0 is None and r60 is None, (r0, r60)
    assert "solidificationCosTheta" not in inclined["thermal"]["solidificationKinetics"]
    assert inclined["thermal"]["processParameters"]["inclineAngle_deg"] == 60.0
    assert any("no incline multiplier" in a for a in inclined["assumptions"]), inclined["assumptions"]
    assert not any("no incline multiplier" in a for a in flat["assumptions"])
    assert any("never as pass or fail" in a for a in flat["assumptions"])

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
    # P7b (2026-10-14): with the smaller IN718 pools no point of the 5x5 search grid passes Tang at a 110 um hatch and
    # 40 um layer (a grid property, as the P7a reasons file states for 100 / 40), so no patch is suggested and the
    # note says why; before P7b the grid still held a printable point.
    assert lof["verdict"]["suggestedPatch"] is None, lof["verdict"]["suggestedPatch"]
    assert lof["verdict"]["suggestedPatchNote"].startswith("No parameter patch: no point of a 5x5 power-speed grid"), lof["verdict"]["suggestedPatchNote"]

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
    # P7a: downskin is an advisory (unsourced screening threshold), never dominant, never a fail.
    assert all(g["status"] == "advisory" for g in ds["verdict"]["gates"] if g["id"] == "downskin"), ds["verdict"]
    assert ds["verdict"]["dominantGate"] != "downskin"
    assert any(a.startswith("Advisory: downskin") for a in ds["verdict"]["advisories"])

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
