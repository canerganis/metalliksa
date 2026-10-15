"""R-TR: P8 research transport with an injected deterministic fake evaluator, no physics (integration contract
2026-10-15, 3.4 to 3.7, 9.3, 13.9, 13.10, 10.3).

Every test drives the real dispatch script (lpbf_research_models.run) with the fake engine, the stubbed identity and
property providers of test_lpbf_research_harness, and its own cache instance. calculate_meltpool_physics raises while
any test runs.
"""

from __future__ import annotations

import dataclasses
import json
import math
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import lpbf_research_cache as research_cache  # noqa: E402
import lpbf_research_codes as codes  # noqa: E402
import lpbf_research_models as models  # noqa: E402
import persistent_ipc_service as ipc  # noqa: E402
import test_lpbf_research_harness as h  # noqa: E402
from lpbf_source_identity import fingerprint_sources  # noqa: E402
from test_lpbf_research_harness import ResearchTestCase  # noqa: E402

OTHER_SIX = ("keyholeCavity", "meltDepthLink", "alSi10MgIndexDisclosure", "alSi10MgVapourMgAware", "marangoni",
             "unavailablePhysics")


def _dump(value) -> str:
    return json.dumps(value, sort_keys=True, allow_nan=False)


def _band(deps, body):
    parsed, code, text = h.call(deps, body)
    assert code == 0, parsed
    return parsed, text


def _complete(deps=None, options=None, engine=None):
    deps = deps or h.make_dependencies(engine or h.FakeEngine())
    parsed, _ = _band(deps, h.request("band", budget=None, options=options))
    assert parsed["progress"]["complete"], parsed["progress"]
    return parsed


class RequestChecks(ResearchTestCase):  # R-TR-1
    def setUp(self):
        super().setUp()
        self.deps = h.make_dependencies()

    def refuse(self, body, pointer, rule, limit=None, code="RESEARCH_REQUEST_INVALID"):
        parsed, exit_code, _ = h.call(self.deps, body)
        self.assertEqual(exit_code, 2, parsed)
        self.assertEqual((parsed["success"], parsed["errorKind"], parsed["reasonCode"]), (False, "validation", code))
        hits = [p for p in parsed["problems"] if (p["pointer"], p["rule"]) == (pointer, rule)]
        self.assertEqual(len(hits), 1, parsed["problems"])
        self.assertEqual(hits[0]["limit"], limit)
        for problem in parsed["problems"]:
            self.assertEqual(sorted(problem), ["limit", "message", "pointer", "rule", "value"])
            self.assertLessEqual(len(problem["value"]), 64)
            self.assertNotIn("—", problem["message"])
            self.assertNotIn("–", problem["message"])
        self.assertEqual(self.deps.engine.evaluations, [])
        return parsed

    def test_request_check_table(self):
        base = h.request("nominal")

        def with_(path, value, body=None):
            body = json.loads(json.dumps(body or base))
            node = body
            for key in path[:-1]:
                node = node[key]
            if value is _DELETE:
                del node[path[-1]]
            else:
                node[path[-1]] = value
            return body
        snapshot_ctx = {"kind": "build-job-snapshot", "alloyId": h.SYNTHETIC_ALLOY_ID,
                        "materialPropertySha256": h.synthetic_property_provider().material_snapshot(
                            h.SYNTHETIC_ALLOY_ID)[1]}
        table = [
            (with_(("process", "laserPower_W"), 0), "/process/laserPower_W", "not-positive", 0),
            (with_(("process", "scanSpeed_mm_s"), -800), "/process/scanSpeed_mm_s", "not-positive", 0),
            (with_(("process", "beamDiameter_um"), 0.0), "/process/beamDiameter_um", "not-positive", 0),
            (with_(("process", "laserPower_W"), True), "/process/laserPower_W", "wrong-type", None),
            (with_(("process", "preheatTemp_C"), "20"), "/process/preheatTemp_C", "wrong-type", None),
            (with_(("process", "preheatTemp_C"), False), "/process/preheatTemp_C", "wrong-type", None),
            (with_(("process", "material"), "Unobtainium"), "/process/material", "wrong-type", None),
            (with_(("process", "laserWavelength"), "UV_355nm"), "/process/laserWavelength", "wrong-type", None),
            (with_(("process", "absorptionModel"), "volumetric"), "/process/absorptionModel", "wrong-type", None),
            (with_(("process", "hatch_um"), 100), "/process/hatch_um", "unknown-key", None),
            (with_(("process", "material"), _DELETE), "/process/material", "wrong-type", None),
            (with_(("extra",), 1), "/extra", "unknown-key", None),
            (with_(("schemaVersion",), "p8-research-request-v2"), "/schemaVersion", "wrong-type", None),
            (with_(("stage",), "full"), "/stage", "wrong-type", None),
            (with_(("supersedeKey",), ""), "/supersedeKey", "wrong-type", None),
            (with_(("supersedeKey",), "k" * 129), "/supersedeKey", "wrong-type", None),
            (with_(("clientRequestId",), _DELETE), "/clientRequestId", "wrong-type", None),
            (with_(("timeBudgetMs",), 1000), "/timeBudgetMs", "wrong-type", None),
            (with_(("timeBudgetMs",), 100, h.request("band", budget=1500)), "/timeBudgetMs", "below-min", 250),
            (with_(("timeBudgetMs",), 9000, h.request("band", budget=1500)), "/timeBudgetMs", "above-max", 8000),
            (with_(("timeBudgetMs",), 1500.5, h.request("band", budget=1500)), "/timeBudgetMs", "wrong-type", None),
            (with_(("timeBudgetMs",), True, h.request("band", budget=1500)), "/timeBudgetMs", "wrong-type", None),
            (with_(("timeBudgetMs",), _DELETE, h.request("band", budget=1500)), "/timeBudgetMs", "wrong-type",
             None),
            (with_(("propertyContext",), {"kind": "calibrated"}), "/propertyContext/kind", "wrong-type", None),
            (with_(("propertyContext",), {"kind": "nominal", "alloyId": "x"}), "/propertyContext/alloyId",
             "unknown-key", None),
            (with_(("propertyContext",), {**snapshot_ctx, "materialPropertySha256": "ABC"}),
             "/propertyContext/materialPropertySha256", "wrong-type", None),
            (with_(("propertyContext",), {**snapshot_ctx, "alloyId": "ti6al4v"}), "/propertyContext/alloyId",
             "alloy-material-mismatch", None),
            (with_(("researchOptions",), {"vapour": {}}), "/researchOptions/vapour", "unknown-key", None),
            (with_(("researchOptions",), {"marangoni": {"sulfur_ppm": 3}}), "/researchOptions/marangoni/sulfur_ppm",
             "unknown-key", None),
            (with_(("researchOptions",), {"marangoni": {"slopeMode": "auto"}}),
             "/researchOptions/marangoni/slopeMode", "wrong-type", None),
            (with_(("researchOptions",), {"marangoni": {"length_m": None}}), "/researchOptions/marangoni/length_m",
             "wrong-type", None),
            (with_(("researchOptions",), {"surfaceBalance": {"emissivity": "0.3"}}),
             "/researchOptions/surfaceBalance/emissivity", "wrong-type", None),
            (with_(("researchOptions",), {"ranges": {"surfaceBalance": {"vapourPreset": {"min": 1, "max": 2}}}}),
             "/researchOptions/ranges/surfaceBalance/vapourPreset", "unknown-key", None),
            (with_(("researchOptions",), {"ranges": {"marangoni": {"length_m": {"min": 1e-5}}}}),
             "/researchOptions/ranges/marangoni/length_m/max", "wrong-type", None),
            (with_(("researchOptions",), {"ranges": {"marangoni": {"length_m": {"min": 1e-5, "max": 2e-5,
                                                                                 "step": 1}}}}),
             "/researchOptions/ranges/marangoni/length_m/step", "unknown-key", None),
            ([base], "", "wrong-type", None),
            # Revision 3: sender is a known member with a closed enum (the relay rules are in R-REL-1)
            (with_(("sender",), "served-solver"), "/sender", "wrong-type", None),
            (with_(("sender",), "blind-freeze"), "/supersedeKey", "sender-key-mismatch", None),
        ]
        for body, pointer, rule, limit in table:
            with self.subTest(pointer=pointer, rule=rule):
                self.refuse(body, pointer, rule, limit)

    def test_the_two_new_senders_are_known_members(self):  # Revision 3, 14.7
        for sender, key in (("blind-freeze", "p8-research:blind:" + "0" * 16),
                            ("batch-client", "p8-research:batch:run0001a"), ("research-panel", "p8-research:build-job")):
            with self.subTest(sender=sender):
                body = h.request("nominal")
                body.update(sender=sender, supersedeKey=key)
                parsed, code, _ = h.call(self.deps, body)
                self.assertEqual(code, 0, parsed)

    def test_tampered_snapshot_hash_is_its_own_code(self):
        body = h.request("nominal", property_context={"kind": "build-job-snapshot", "alloyId": h.SYNTHETIC_ALLOY_ID,
                                                      "materialPropertySha256": "f" * 64})
        self.refuse(body, "/propertyContext/materialPropertySha256", "snapshot-hash-mismatch",
                    code="PROPERTY_SNAPSHOT_MISMATCH")

    def test_unparseable_non_finite_and_oversize_bodies(self):
        self.refuse("{not json", "", "wrong-type")
        text = json.dumps(h.request("nominal")).replace('"laserPower_W": 200', '"laserPower_W": NaN')
        self.refuse(text, "/process/laserPower_W", "not-finite")
        big = h.request("nominal", client_id="x")
        big["process"]["material"] = "M" * 70000
        self.refuse(big, "", "too-large", limit=65536)

    def test_every_problem_is_reported_in_check_order(self):
        body = h.request("nominal")
        body["process"]["laserPower_W"] = 0
        body["stage"] = "full"
        parsed = self.refuse(body, "/process/laserPower_W", "not-positive", 0)
        self.assertEqual([p["pointer"] for p in parsed["problems"]], ["/process/laserPower_W", "/stage"])

    def test_a_valid_request_without_the_phase_c_evaluator_fails_at_request_scope(self):
        log = []
        deps = dataclasses.replace(h.make_dependencies(log=log), engine=None)
        parsed, code, _ = h.call(deps, h.request("nominal"))
        self.assertEqual((code, parsed), (0, {"success": False, "errorKind": "research",
                                              "reasonCode": "RESEARCH_EVALUATION_FAILED"}))
        self.assertTrue(any("not installed" in line for line in log))
        parsed, code, _ = h.call(deps, h.request("nominal", process={"laserPower_W": -1}))
        self.assertEqual((code, parsed["reasonCode"]), (2, "RESEARCH_REQUEST_INVALID"))


class _Delete:
    pass


_DELETE = _Delete()


class ModuleScopedOptions(ResearchTestCase):  # R-TR-2
    def test_a_bad_surface_option_blanks_only_surface_balance(self):
        reference = _complete()
        bad = _complete(options={"surfaceBalance": {"emissivity": 1.2}})
        surface = bad["researchModels"]["surfaceBalance"]
        self.assertEqual((surface["status"], surface["reasonCode"]), ("unavailable", "RESEARCH_OPTIONS_INVALID"))
        self.assertEqual([(p["pointer"], p["rule"], p["limit"]) for p in surface["problems"]],
                         [("/researchOptions/surfaceBalance/emissivity", "above-max", 1.0)])
        for module in OTHER_SIX:
            self.assertEqual(_dump(bad["researchModels"][module]), _dump(reference["researchModels"][module]), module)

    def test_range_rules_are_module_scoped(self):
        cases = [
            ({"ranges": {"marangoni": {"deltaTemperature_K": {"min": 600, "max": 300}}}}, "range-inverted",
             "/researchOptions/ranges/marangoni/deltaTemperature_K"),
            ({"ranges": {"marangoni": {"deltaTemperature_K": {"min": 600, "max": 900}}}}, "range-excludes-nominal",
             "/researchOptions/ranges/marangoni/deltaTemperature_K"),
            ({"ranges": {"marangoni": {"deltaTemperature_K": {"min": -1, "max": 900}}}}, "below-min",
             "/researchOptions/ranges/marangoni/deltaTemperature_K/min"),
            ({"marangoni": {"length_m": 0.5}}, "above-max", "/researchOptions/marangoni/length_m"),
            ({"marangoni": {"slopeMode": "fe-s-belton", "surfaceTensionSlope_N_mK": -1e-4}}, "mode-field-ignored",
             "/researchOptions/marangoni/surfaceTensionSlope_N_mK"),
        ]
        reference = _complete()
        for options, rule, pointer in cases:
            with self.subTest(rule=rule):
                out = _complete(options=options)
                mar = out["researchModels"]["marangoni"]
                self.assertEqual(mar["status"], "unavailable")
                self.assertEqual([(p["pointer"], p["rule"]) for p in mar["problems"]], [(pointer, rule)])
                self.assertEqual(_dump(out["researchModels"]["surfaceBalance"]),
                                 _dump(reference["researchModels"]["surfaceBalance"]))

    def test_non_finite_option_is_a_module_problem_not_a_request_refusal(self):
        deps = h.make_dependencies()
        text = json.dumps(h.request("band", budget=None, options={"surfaceBalance": {"emissivity": 0.5}}))
        text = text.replace('"emissivity": 0.5', '"emissivity": Infinity')
        parsed, code, _ = h.call(deps, text)
        self.assertEqual(code, 0)
        surface = parsed["researchModels"]["surfaceBalance"]
        self.assertEqual([(p["pointer"], p["rule"]) for p in surface["problems"]],
                         [("/researchOptions/surfaceBalance/emissivity", "not-finite")])
        self.assertEqual(surface["problems"][0]["value"], "Infinity")


class StageProtocol(ResearchTestCase):  # R-TR-3
    def test_nominal_stage_returns_every_container_with_pending_bands(self):
        parsed, _ = _band(h.make_dependencies(), h.request("nominal"))
        block = parsed["researchModels"]
        self.assertEqual(sorted(block), sorted(("schemaVersion",) + models.CONTAINERS))
        self.assertEqual(block["schemaVersion"], "p8-research-v3")
        self.assertFalse(parsed["progress"]["complete"])
        for module in models.BAND_ORDER:
            for name, field in block[module]["fields"].items():
                band = field["band"]
                if band is None:
                    continue
                self.assertEqual((band["completeness"], band["reasonCode"], band["min"], band["max"],
                                  band["successfulArms"], band["totalArms"], band["failedArms"]),
                                 ("pending", "BAND_PENDING", None, None, None, None, []), (module, name))
        for module in ("alSi10MgIndexDisclosure", "unavailablePhysics"):
            self.assertIsNone(block[module]["band"])

    def test_budgeted_band_loop_progresses_and_matches_one_unbudgeted_run(self):
        clock = h.FakeClock()
        deps = h.make_dependencies(h.FakeEngine(clock=clock, seconds_per_arm=0.1), clock=clock)
        _band(deps, h.request("nominal"))
        done, responses = [], 0
        while True:
            parsed, _ = _band(deps, h.request("band", budget=250))
            responses += 1
            done.append(parsed["progress"]["armsDone"])
            if parsed["progress"]["complete"]:
                break
            self.assertIsNone(parsed["researchModels"])
            self.assertEqual(parsed["labels"], {})
            self.assertGreaterEqual(parsed["cache"]["armsComputed"], 1)
            self.assertLess(responses, 50)
        self.assertEqual(done, sorted(set(done)))  # strictly increasing
        self.assertGreater(responses, 2)
        single = _complete()
        self.assertEqual(_dump(parsed["researchModels"]), _dump(single["researchModels"]))
        self.assertEqual(parsed["labels"], single["labels"])

    def test_every_band_request_computes_at_least_one_arm(self):
        clock = h.FakeClock()
        deps = h.make_dependencies(h.FakeEngine(clock=clock, seconds_per_arm=10.0), clock=clock)
        first, _ = _band(deps, h.request("band", budget=250))
        second, _ = _band(deps, h.request("band", budget=250))
        self.assertEqual((first["cache"]["armsComputed"], second["cache"]["armsComputed"]), (1, 1))
        self.assertEqual(second["progress"]["armsDone"], first["progress"]["armsDone"] + 1)


class Cache(ResearchTestCase):  # R-TR-4
    def test_cold_equals_warm_byte_for_byte(self):
        deps = h.make_dependencies()
        cold, _ = _band(deps, h.request("band", budget=None))
        warm, _ = _band(deps, h.request("band", budget=None))
        self.assertEqual(warm["cache"]["armsComputed"], 0)
        self.assertEqual(warm["cache"]["armsHit"], cold["progress"]["armsTotal"])
        self.assertEqual(_dump(cold["researchModels"]), _dump(warm["researchModels"]))
        self.assertEqual(_dump(cold["labels"]), _dump(warm["labels"]))
        self.assertEqual(cold["requestKey"], warm["requestKey"])

    def test_surface_only_change_reuses_cavity_link_and_marangoni_arms(self):
        engine = h.FakeEngine()
        deps = h.make_dependencies(engine)
        _band(deps, h.request("band", budget=None))
        before = len(engine.evaluations)
        out, _ = _band(deps, h.request("band", budget=None, options={"surfaceBalance": {"emissivity": 0.45}}))
        recomputed = {module for module, _ in engine.evaluations[before:]}
        self.assertEqual(recomputed, {"surfaceBalance"})
        self.assertTrue(out["progress"]["complete"])

    def test_lru_evicts_the_oldest_entry_at_1025(self):
        lru = research_cache.ResearchLRU()
        self.assertEqual((lru.max_entries, lru.max_bytes), (1024, 128 * 1024 * 1024))
        for i in range(1024):
            lru.put(f"k{i}", {"i": i})
        self.assertEqual(len(lru), 1024)
        self.assertIsNotNone(lru.get("k1"))  # touch k1: k0 is now the oldest
        lru.put("k1024", {"i": 1024})
        self.assertEqual(len(lru), 1024)
        self.assertNotIn("k0", lru)
        self.assertIn("k1", lru)
        self.assertEqual(lru.stats["evictions"], 1)

    def test_size_bound_evicts_large_entries(self):
        lru = research_cache.ResearchLRU(max_entries=100, max_bytes=1000)
        payload = "x" * 380
        for i in range(3):
            lru.put(f"k{i}", {"p": payload})
        self.assertNotIn("k0", lru)
        self.assertEqual(lru.keys(), ["k1", "k2"])
        self.assertLessEqual(lru.total_bytes, 1000)
        self.assertFalse(lru.put("huge", {"p": "y" * 2000}))
        self.assertEqual(lru.keys(), ["k1", "k2"])

    def test_cache_hands_out_copies_and_refuses_non_finite_values(self):
        lru = research_cache.ResearchLRU()
        value = {"values": {"a": [1.0, 2.0]}}
        lru.put("k", value)
        value["values"]["a"].append(3.0)
        got = lru.get("k")
        self.assertEqual(got, {"values": {"a": [1.0, 2.0]}})
        got["values"]["a"].clear()
        self.assertEqual(lru.get("k"), {"values": {"a": [1.0, 2.0]}})
        with self.assertRaises(research_cache.CanonicalEncodeError):
            lru.put("bad", {"v": float("nan")})

    def test_band_loop_at_the_per_module_cap_completes(self):
        declared = {table: tuple(arms[:1]) + tuple((f"cap_{i:02d}", {next(iter(arms[1][1])): 1.0 + i / 1000.0})
                                                   for i in range(1, 80))
                    for table, arms in h.DEFAULT_DECLARED_ARMS.items()}
        clock = h.FakeClock()
        engine = h.FakeEngine(declared=declared, clock=clock, seconds_per_arm=0.05)
        deps = h.make_dependencies(engine, clock=clock)
        done = []
        for _ in range(200):
            parsed, _ = _band(deps, h.request("band", budget=250))
            done.append(parsed["progress"]["armsDone"])
            if parsed["progress"]["complete"]:
                break
        self.assertTrue(parsed["progress"]["complete"])
        self.assertEqual(parsed["progress"]["armsTotal"], 4 * 80 + 3)
        self.assertEqual(done, sorted(set(done)))
        self.assertEqual(len(deps.cache), 4 * 80 + 3 + 7)  # every arm record plus the seven aggregates
        self.assertEqual(_dump(parsed["researchModels"]),
                         _dump(_complete(engine=h.FakeEngine(declared=declared))["researchModels"]))

    def test_a_manifest_above_the_cap_makes_only_that_module_unavailable(self):
        declared = dict(h.DEFAULT_DECLARED_ARMS)
        declared["marangoni"] = tuple(declared["marangoni"][:1]) + tuple((f"over_{i}", {"slope": 1.0 + i / 100.0})
                                                                         for i in range(1, 81))
        out = _complete(engine=h.FakeEngine(declared=declared))
        mar = out["researchModels"]["marangoni"]
        self.assertEqual((mar["status"], mar["reasonCode"]), ("unavailable", "RESEARCH_ARM_LIMIT_EXCEEDED"))
        self.assertEqual(out["researchModels"]["surfaceBalance"]["status"], "available")

    def test_transient_failures_are_not_cached_and_deterministic_failures_are(self):
        engine = h.FakeEngine(raise_in_arm={("surfaceBalance", "emissivity_alt")},
                              failures={("marangoni", "length_short", "syntheticVelocity_m_s"):
                                        "MARANGONI_VISCOSITY_INPUT_REQUIRED"})
        deps = h.make_dependencies(engine)
        first = _complete(deps)
        evaluated = len(engine.evaluations)
        second = _complete(deps)
        again = engine.evaluations[evaluated:]
        self.assertEqual(again, [("surfaceBalance", "emissivity_alt")])  # only the transient arm is recomputed
        self.assertEqual(second["cache"]["armsComputed"], 1)
        band = first["researchModels"]["marangoni"]["fields"]["syntheticVelocity_m_s"]["band"]
        self.assertEqual(band["failedArms"], [{"armId": "length_short",
                                               "reasonCode": "MARANGONI_VISCOSITY_INPUT_REQUIRED"}])
        self.assertEqual(band["completeness"], "partial")


class NonFinite(ResearchTestCase):  # R-TR-5
    FIELD = "syntheticRatio"

    def _cavity_band(self, inject, value):
        engine = h.FakeEngine(nonfinite={("keyholeCavity", arm, self.FIELD): value for arm in inject})
        parsed, text = _band(h.make_dependencies(engine), h.request("band", budget=None))
        h.strict_loads(text)  # a strict parser reads the output
        self.assertTrue(h.is_finite_json(parsed))
        return parsed["researchModels"]["keyholeCavity"]["fields"]

    def test_first_middle_and_last_positions_give_the_same_band(self):
        reference = self._cavity_band((), None)[self.FIELD]["band"]
        for arm in ("nominal", "absorptance_high", "diameter_plus5"):
            for bad in (float("nan"), float("inf"), float("-inf")):
                with self.subTest(arm=arm, value=bad):
                    fields = self._cavity_band((arm,), bad)
                    band = fields[self.FIELD]["band"]
                    self.assertEqual((band["min"], band["max"], band["minArmId"], band["maxArmId"],
                                      band["minArmTies"], band["maxArmTies"]),
                                     (reference["min"], reference["max"], reference["minArmId"],
                                      reference["maxArmId"], reference["minArmTies"], reference["maxArmTies"]))
                    self.assertEqual(band["failedArms"], [{"armId": arm, "reasonCode": "NONFINITE_RESULT"}])
                    self.assertEqual((band["completeness"], band["successfulArms"]), ("partial", 5))
                    # field-specific: the other field of the same arm is untouched
                    other = fields["syntheticDepth_um"]["band"]
                    self.assertEqual(other["failedArms"], [])
                    if arm == "nominal":
                        self.assertIsNone(fields[self.FIELD]["value"])
                        self.assertEqual(fields[self.FIELD]["reasonCode"], "NONFINITE_RESULT")
                        self.assertEqual(band["nominalReasonCode"], "NONFINITE_RESULT")

    def test_a_non_finite_extreme_never_becomes_the_extreme(self):
        reference = self._cavity_band((), None)[self.FIELD]["band"]
        band = self._cavity_band(("power_plus5",), float("nan"))[self.FIELD]["band"]
        self.assertNotEqual(band["maxArmId"], "power_plus5")
        self.assertLess(band["max"], reference["max"])
        self.assertTrue(math.isfinite(band["max"]))
        band = self._cavity_band(("power_minus5", "power_plus5", "nominal"), float("inf"))[self.FIELD]["band"]
        self.assertEqual(band["min"], band["max"])
        self.assertEqual(band["minArmTies"], 3)

    def test_every_arm_non_finite_gives_no_band(self):
        arms = [a for a, _ in h.DEFAULT_DECLARED_ARMS["cavity"]]
        band = self._cavity_band(arms, float("nan"))[self.FIELD]["band"]
        self.assertEqual((band["completeness"], band["reasonCode"], band["min"], band["max"]),
                         ("unavailable", "BAND_NO_SUCCESSFUL_ARM", None, None))

    def test_the_serialization_pass_nulls_a_non_finite_container_slot(self):
        class Leaky(h.FakeEngine):
            def aggregate(self, module_id, *args):
                container = super().aggregate(module_id, *args)
                if module_id == "unavailablePhysics":
                    container["fields"]["syntheticClosure"] = {"value": float("nan"), "unit": "1", "reasonCode": None,
                                                               "band": None}
                    container["note"] = [float("inf")]
                return container
        parsed, text = _band(h.make_dependencies(Leaky()), h.request("band", budget=None))
        h.strict_loads(text)
        unavailable = parsed["researchModels"]["unavailablePhysics"]
        self.assertEqual(unavailable["fields"]["syntheticClosure"]["value"], None)
        self.assertEqual(unavailable["fields"]["syntheticClosure"]["reasonCode"], "NONFINITE_RESULT")
        self.assertEqual(unavailable["note"], [None])

    def test_arm_time_pass_marks_nested_paths(self):
        record = models.sanitize_arm_record({"values": {"a": 1.0, "roots": [{"depth_um": float("nan")}]},
                                             "failures": {}, "note": {"x": float("inf")}})
        self.assertEqual(record["failures"], {"roots.0.depth_um": "NONFINITE_RESULT", "note.x": "NONFINITE_RESULT"})
        self.assertIsNone(record["values"]["roots"][0]["depth_um"])
        with self.assertRaises(ValueError):
            models.sanitize_arm_record({"values": {}, "failures": {"a": "NOT_A_CODE"}})


class NominalAcrossStages(ResearchTestCase):  # R-TR-6
    def test_nominal_values_are_identical_in_the_nominal_and_complete_responses(self):
        deps = h.make_dependencies()
        nominal, _ = _band(deps, h.request("nominal"))
        complete, _ = _band(deps, h.request("band", budget=None))
        self.assertEqual(nominal["requestKey"], complete["requestKey"])
        for module in models.CONTAINERS:
            a, b = nominal["researchModels"][module], complete["researchModels"][module]
            for name in a["fields"]:
                self.assertEqual(_dump(a["fields"][name]["value"]), _dump(b["fields"][name]["value"]),
                                 (module, name))
                band = b["fields"][name]["band"]
                if band is not None:
                    self.assertEqual(_dump(band["nominal"]), _dump(a["fields"][name]["value"]))
        for module in ("alSi10MgIndexDisclosure", "unavailablePhysics"):
            self.assertEqual(_dump(nominal["researchModels"][module]), _dump(complete["researchModels"][module]))


class Failures(ResearchTestCase):  # R-TR-7
    def test_an_arm_exception_is_a_failed_arm(self):
        log = []
        engine = h.FakeEngine(raise_in_arm={("keyholeCavity", "power_plus5")})
        parsed, _ = _band(h.make_dependencies(engine, log=log), h.request("band", budget=None))
        cavity = parsed["researchModels"]["keyholeCavity"]
        self.assertEqual(cavity["status"], "available")
        for name in ("syntheticDepth_um", "syntheticRatio"):
            band = cavity["fields"][name]["band"]
            self.assertEqual(band["failedArms"], [{"armId": "power_plus5", "reasonCode": "RESEARCH_EVALUATION_FAILED"}])
            self.assertEqual(band["completeness"], "partial")
        link = parsed["researchModels"]["meltDepthLink"]["fields"]["syntheticLinkedDepth_um"]["band"]
        self.assertIn({"armId": "power_plus5", "reasonCode": "RESEARCH_EVALUATION_FAILED"}, link["failedArms"])
        arm_lines = [line for line in log if "arm failed" in line]
        self.assertEqual(len(arm_lines), 1)
        self.assertIn("module=keyholeCavity arm=power_plus5", arm_lines[0])
        self.assertIn("injected failure", arm_lines[0])
        self.assertNotIn("\n", arm_lines[0])

    def test_a_module_assembly_exception_leaves_the_other_six_containers(self):
        reference = _complete()
        out = _complete(engine=h.FakeEngine(raise_in_aggregate={"marangoni"}))
        mar = out["researchModels"]["marangoni"]
        self.assertEqual((mar["status"], mar["reasonCode"]), ("unavailable", "RESEARCH_EVALUATION_FAILED"))
        for module in ("keyholeCavity", "meltDepthLink", "alSi10MgIndexDisclosure", "alSi10MgVapourMgAware",
                       "surfaceBalance", "unavailablePhysics"):
            self.assertEqual(_dump(out["researchModels"][module]), _dump(reference["researchModels"][module]))

    def test_a_bug_outside_any_module_is_a_request_scope_failure_with_stderr_only(self):
        class Broken(h.FakeEngine):
            def controls(self, context, options):
                raise RuntimeError("controls exploded")
        log = []
        parsed, code, text = h.call(h.make_dependencies(Broken(), log=log), h.request("nominal"))
        self.assertEqual((code, parsed), (0, {"success": False, "errorKind": "research",
                                              "reasonCode": "RESEARCH_EVALUATION_FAILED"}))
        self.assertNotIn("Traceback", text)
        self.assertTrue(any("controls exploded" in line for line in log))


class CodeStale(ResearchTestCase):  # R-TR-8
    def _guard(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        names = ("a.py", "b.py")
        for name in names:
            (tmp / name).write_text(f"# {name}\n", encoding="utf-8")
        guard = research_cache.IdentityGuard(lambda: fingerprint_sources(tmp, names, "v"),
                                             lambda: fingerprint_sources(tmp, ("b.py",), "s"),
                                             [tmp / n for n in names])
        return guard, tmp

    def test_a_changed_file_on_disk_refuses_with_research_code_stale(self):
        guard, tmp = self._guard()
        deps = dataclasses.replace(h.make_dependencies(), identity=guard)
        parsed, code, _ = h.call(deps, h.request("describe"))
        self.assertEqual(code, 0, parsed)
        self.assertEqual(parsed["identity"]["researchImplementationSha256"], guard.research_sha256)
        (tmp / "a.py").write_text("# a.py edited\n", encoding="utf-8")
        parsed, code, _ = h.call(deps, h.request("nominal"))
        self.assertEqual(code, 2)
        self.assertEqual(parsed, {"success": False, "errorKind": "validation", "reasonCode": "RESEARCH_CODE_STALE",
                                  "problems": [], "recycleWorker": True})
        # stale for good, even if the file is restored: the worker is recycled, never un-staled
        (tmp / "a.py").write_text("# a.py\n", encoding="utf-8")
        self.assertTrue(guard.check()["stale"])

    def test_a_touch_without_a_content_change_rehashes_once_and_re_arms(self):
        guard, tmp = self._guard()
        first = guard.check()
        self.assertEqual((first["stale"], first["rehashed"]), (False, False))
        target = tmp / "b.py"
        stat = target.stat()
        import os
        os.utime(target, ns=(stat.st_atime_ns, stat.st_mtime_ns + 10_000_000))
        second = guard.check()
        self.assertEqual((second["stale"], second["rehashed"]), (False, True))
        third = guard.check()
        self.assertEqual((third["stale"], third["rehashed"]), (False, False))

    def test_the_served_fingerprint_is_part_of_the_check(self):
        guard, tmp = self._guard()
        (tmp / "b.py").write_text("# b.py edited\n", encoding="utf-8")
        result = guard.check()
        self.assertTrue(result["stale"])
        self.assertIn("servedImplementationFingerprint", result["changed"])

    def test_the_real_guard_watches_the_research_and_served_files_and_is_cheap_when_unchanged(self):
        guard = research_cache.IDENTITY
        self.assertEqual(guard.research_sha256, research_cache.research_implementation_sha256())
        self.assertEqual(guard.served_fingerprint, research_cache.served_implementation_fingerprint())
        times = []
        for _ in range(20):
            result = guard.check()
            self.assertEqual((result["stale"], result["rehashed"]), (False, False))
            times.append(result["elapsedMs"])
        times.sort()
        self.assertLess(times[len(times) // 2], research_cache.STALE_REHASH_THRESHOLD_MS)


class RequestKey(ResearchTestCase):  # R-TR-9
    def _key(self, body, identity=None):
        deps = h.make_dependencies(identity=identity)
        parsed, code, _ = h.call(deps, body)
        self.assertEqual(code, 0, parsed)
        return parsed["requestKey"]

    def test_every_input_and_identity_hash_changes_the_request_key(self):
        provider = h.synthetic_property_provider()
        sha = provider.material_snapshot(h.SYNTHETIC_ALLOY_ID)[1]
        variants = {
            "base": h.request("describe"),
            "power": h.request("describe", process={"laserPower_W": 201}),
            "speed": h.request("describe", process={"scanSpeed_mm_s": 801}),
            "diameter": h.request("describe", process={"beamDiameter_um": 81}),
            "preheat": h.request("describe", process={"preheatTemp_C": 21}),
            "wavelength": h.request("describe", process={"laserWavelength": "Green_515nm"}),
            "absorption": h.request("describe", process={"absorptionModel": "powder-raytrace"}),
            "material": h.request("describe", material=h.SYNTHETIC_MATERIAL_B),
            "propertyContext": h.request("describe", property_context={
                "kind": "build-job-snapshot", "alloyId": h.SYNTHETIC_ALLOY_ID, "materialPropertySha256": sha}),
            "marangoniOption": h.request("describe", options={"marangoni": {"deltaTemperature_K": 400}}),
            "slopeMode": h.request("describe", options={"marangoni": {"slopeMode": "fe-s-belton"}}),
            "surfaceOption": h.request("describe", options={"surfaceBalance": {"emissivity": 0.31}}),
            "preset": h.request("describe", options={"surfaceBalance": {"vapourPreset": "custom"}}),
            "range": h.request("describe", options={"ranges": {"surfaceBalance": {
                "emissivity": {"min": 0.2, "max": 0.4}}}}),
            "followFlag": h.request("describe", options={"marangoni": {"length_m": 8e-05}}),
        }
        keys = {name: self._key(body) for name, body in variants.items()}
        keys["researchHash"] = self._key(variants["base"], h.StubIdentity(research="1" * 64))
        keys["servedHash"] = self._key(variants["base"], h.StubIdentity(served="2" * 64))
        self.assertEqual(len(set(keys.values())), len(keys), keys)

    def test_transport_members_and_number_spelling_do_not_change_the_key(self):
        base = self._key(h.request("describe"))
        same = [h.request("nominal"), h.request("band", budget=1500), h.request("describe", client_id="other:9"),
                h.request("describe", process={"laserPower_W": 200.0, "preheatTemp_C": 20.0})]
        other = h.request("describe")
        other["supersedeKey"] = "p8-research:build-job"
        same.append(other)
        deps = h.make_dependencies(h.FakeEngine(clock=None))
        for body in same:
            parsed, code, _ = h.call(deps, body)
            self.assertEqual(code, 0, parsed)
            self.assertEqual(parsed["requestKey"], base, body)


class ResponseSize(ResearchTestCase):  # R-TR-10
    def test_an_oversize_block_gives_research_response_too_large(self):
        log = []
        parsed, code, text = h.call(h.make_dependencies(h.FakeEngine(oversize=True), log=log),
                                    h.request("band", budget=None))
        self.assertEqual((code, parsed), (0, {"success": False, "errorKind": "research",
                                              "reasonCode": "RESEARCH_RESPONSE_TOO_LARGE"}))
        self.assertLess(len(text), 200)
        self.assertTrue(any("RESEARCH_RESPONSE_TOO_LARGE" in line for line in log))


class TransportFixture(ResearchTestCase):  # R-TR-11
    def test_cli_output_equals_the_committed_fixture(self):
        expected = json.loads(h.FIXTURE_PATH.read_text(encoding="utf-8"))
        got = h.fixture_response()
        self.assertEqual(got, expected,
                         "transport shape changed: if deliberate, regenerate with "
                         "python -B test_lpbf_research_harness.py --write-fixture")
        self.assertEqual(h.fixture_text(got), h.FIXTURE_PATH.read_text(encoding="utf-8").replace("\r\n", "\n"))

    def test_fixture_shape(self):
        expected = json.loads(h.FIXTURE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(sorted(expected), ["cache", "clientRequestId", "digests", "identity", "labels", "progress",
                                            "requestKey", "researchModels", "schemaVersion", "stage", "success"])
        self.assertEqual(expected["digests"]["researchModelsSha256"],
                         h.hashlib.sha256(codes.canonical_json(expected["researchModels"]).encode("utf-8")).hexdigest())
        self.assertEqual(expected["schemaVersion"], "p8-research-response-v1")
        self.assertEqual(expected["identity"]["researchImplementationSha256"], h.STUB_RESEARCH_SHA256)
        self.assertEqual(expected["cache"], {"cacheInstanceId": h.FIXTURE_CACHE_INSTANCE_ID, "armsHit": 0,
                                             "armsComputed": expected["progress"]["armsTotal"]})
        self.assertTrue(expected["progress"]["complete"])


class Describe(ResearchTestCase):  # R-TR-12
    def test_describe_returns_controls_defaults_provenance_labels_and_problems_without_arms(self):
        engine = h.FakeEngine()
        deps = h.make_dependencies(engine)
        options = {"marangoni": {"deltaTemperature_K": 400}, "surfaceBalance": {"emissivity": 1.2}}
        parsed, code, _ = h.call(deps, h.request("describe", options=options))
        self.assertEqual(code, 0, parsed)
        self.assertEqual(engine.evaluations, [])
        self.assertEqual(sorted(parsed), ["clientRequestId", "controls", "identity", "labels", "moduleAvailability",
                                          "presets", "problems", "requestKey", "schemaVersion", "stage", "success"])
        controls = {c["key"]: c for c in parsed["controls"]}
        self.assertEqual(controls["length_m"]["value"], 8e-05)  # followed default, evaluated in Python
        self.assertEqual(controls["length_m"]["provenance"]["kind"], "followsInput")
        self.assertEqual(controls["referenceTemperature_K"]["value"], 1773.15 + 200.0)
        self.assertEqual(controls["deltaTemperature_K"]["provenance"]["kind"], "userInput")
        self.assertEqual([(p["pointer"], p["rule"]) for p in parsed["problems"]],
                         [("/researchOptions/surfaceBalance/emissivity", "above-max")])
        self.assertEqual(parsed["moduleAvailability"]["surfaceBalance"],
                         {"status": "unavailable", "reasonCode": "RESEARCH_OPTIONS_INVALID"})
        self.assertEqual(parsed["moduleAvailability"]["keyholeCavity"], {"status": "available", "reasonCode": None})
        self.assertEqual(parsed["labels"], dict(sorted(h.FIXED_LABELS.items())))
        nominal, _, _ = h.call(deps, h.request("nominal", options=options))
        self.assertEqual(nominal["requestKey"], parsed["requestKey"])


class StaleRecycle(ResearchTestCase):  # R-TR-13 (script side; the lane side is in test_persistent_ipc_research_lane)
    def test_research_code_stale_asks_the_lane_to_recycle_its_worker(self):
        identity = h.StubIdentity()
        identity.stale = True
        text, code = models.run(json.dumps(h.request("nominal")), h.make_dependencies(identity=identity))
        self.assertEqual(code, 2)
        self.assertTrue(ipc._requests_worker_recycle({"stdout": text + "\n", "exitCode": code}))
        ok_text, ok_code = models.run(json.dumps(h.request("nominal")), h.make_dependencies())
        self.assertEqual(ok_code, 0)
        self.assertFalse(ipc._requests_worker_recycle({"stdout": ok_text, "exitCode": ok_code}))

    def test_the_stale_check_runs_before_anything_else(self):
        identity = h.StubIdentity()
        identity.stale = True
        parsed, code, _ = h.call(h.make_dependencies(identity=identity), "{not json")
        self.assertEqual((code, parsed["reasonCode"]), (2, "RESEARCH_CODE_STALE"))


class CodeRegistry(ResearchTestCase):
    """Phase B skeleton checks of lpbf_research_codes (the full R-CODE suite is phase C)."""

    def test_every_code_the_transport_emits_is_registered(self):
        for code in ("RESEARCH_REQUEST_INVALID", "PROPERTY_SNAPSHOT_MISMATCH", "RESEARCH_CODE_STALE",
                     "RESEARCH_TIMEOUT", "RESEARCH_EVALUATION_FAILED", "RESEARCH_SERIALIZATION_FAILED",
                     "RESEARCH_RESPONSE_TOO_LARGE", "RESEARCH_OPTIONS_INVALID", "RESEARCH_ARM_LIMIT_EXCEEDED",
                     "NONFINITE_RESULT", "BAND_PENDING", "BAND_NO_SUCCESSFUL_ARM", "BAND_MANIFEST_NOT_DECLARED"):
            self.assertIn(code, codes.REASON_CODES)
        self.assertEqual(set(codes.OPTION_RULES), {
            "unknown-key", "wrong-type", "not-finite", "below-min", "above-max", "range-inverted",
            "range-excludes-nominal", "range-without-nominal", "mode-field-ignored", "binary-combination",
            "preset-alloy-mismatch", "not-positive", "too-large", "alloy-material-mismatch",
            "snapshot-hash-mismatch", "sender-key-mismatch", "relay-sender-mismatch", "relay-options-forbidden",
            "relay-required"})

    def test_classes_precedence_and_warnings(self):
        self.assertEqual(len(codes.REASON_CODES), 4 + 3 + 4 + 3 + 8 + 4 + 5 + 13 + 8 + 3)
        self.assertFalse(codes.WARNING_CODES & set(codes.REASON_CODES))
        self.assertEqual(codes.winning_code(["NONFINITE_RESULT", "PECLET_OUTSIDE_NUMERICAL_SCOPE"]),
                         "PECLET_OUTSIDE_NUMERICAL_SCOPE")
        self.assertEqual(codes.winning_code(["CAVITY_RESIDUAL_FAILED", "NONFINITE_RESULT"]), "CAVITY_RESIDUAL_FAILED")
        with self.assertRaises(ValueError):
            codes.winning_code(["LOW_PE_HYDRODYNAMICS_OMITTED"])
        self.assertNotIn("RESEARCH_EVALUATION_FAILED", codes.DETERMINISTIC_CODES)
        self.assertIn("NONFINITE_RESULT", codes.DETERMINISTIC_CODES)

    def test_texts_have_no_em_or_en_dashes(self):
        for rule, spec in codes.OPTION_RULES.items():
            self.assertNotRegex(spec["template"], "[–—]", rule)
        for label in codes.REQUEST_FIELD_LABELS.values():
            self.assertNotRegex(label, "[–—]")


if __name__ == "__main__":
    unittest.main()
