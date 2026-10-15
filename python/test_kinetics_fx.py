"""Engine-fix lane fx-kinetics: kinetics_ttt_cct_solver honesty fixes (audit D4).

1. The TTT/CCT/phase-fraction/hardness model is a steel template: for non-steel alloys (Inconel 718,
   Ti-6Al-4V, Al 7075) those outputs are None with an explicit status and the reason
   "kinetics model is steel-only". Registry placeholders (alloy_registry.KINETICS_PLACEHOLDERS) are
   never reported.
2. LSW coarsening (fx-kinetics unit fix, superseded by SOL-K): the unit fix made K_LSW 9.1e4 times larger (the
   audit's r(8 h) = 9.6 nm for AISI 4140 at 720 C); SOL-K (SPEC_solidification section 6.3) then withdrew the
   generic radius and the 280 MPa / 9 nm strengthening curve for every alloy: they are null with a status and
   reason codes (class LswUnavailableTest), and the aging inputs are validated (class AgingInputTest).
3. (superseded by lane kin-li) The steel template with its 1 ms TTT floor is replaced by the Li (1998)
   model (oracle tests: test_kinetics_li1998.py); the tests below keep the steel-only / placeholder / LSW
   behaviour and check that the floor and the cooling-rate-band lookup are gone.

Run from python/: python -B -m unittest test_kinetics_fx
"""

import ast
import hashlib
import json
import math
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

import alloy_registry
import input_validation
import kinetics_ttt_cct_solver as kin

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE / "tools"))
import kinetics_documented_changes as kdc  # noqa: E402 (tools/ module; the independent SOL-K rules)

STUDIO_FIXTURE = HERE.parent / "tests" / "fixtures" / "kinetics-studio-results.json"
# Studio defaults (src/components/PhaseKineticsTTTCCTStudio.tsx ALLOY_OPTIONS): alloy -> (austenitising C, aging C),
# 10 C/s, grain 25 um, aging 8 h. The last two reproduce the former 720 C aging default (LSW above the solvus).
STUDIO_CASES = {
    "aisi4140": ("AISI 4140", 860.0, 720.0), "aisi4340": ("AISI 4340", 845.0, 650.0),
    "aisid2": ("AISI D2", 1020.0, 720.0), "in718": ("Inconel 718", 980.0, 720.0),
    "ti6al4v": ("Ti-6Al-4V", 1050.0, 720.0), "al7075": ("Al 7075", 475.0, 120.0),
    "aisi4340_aging720": ("AISI 4340", 845.0, 720.0), "al7075_aging720": ("Al 7075", 475.0, 720.0),
}


def studio_fixture_results():
    """Real solver output for the Studio render test (tests/phase-kinetics-studio.test.tsx), without timing."""
    out = {}
    for key, (name, aust, aging_c) in STUDIO_CASES.items():
        res = kin.solve_phase_transformation_kinetics(name, 10.0, 25.0, aust, 8.0, aging_c)
        res.pop("computeTimeMs")
        out[key] = res
    return json.loads(json.dumps(out))
STEELS = ("AISI 4140", "AISI 4340", "AISI D2")
NON_STEELS = ("Inconel 718", "Ti-6Al-4V", "Al 7075")
DEFAULT_AUST = {"AISI 4140": 860.0, "AISI 4340": 845.0, "AISI D2": 1020.0,
                "Inconel 718": 980.0, "Ti-6Al-4V": 1050.0, "Al 7075": 475.0}
STEEL_ONLY = "kinetics model is steel-only"


def solve(name, cooling=10.0, grain=25.0, aust=None, aging_h=8.0, aging_c=720.0):
    return kin.solve_phase_transformation_kinetics(
        name, cooling, grain, DEFAULT_AUST[name] if aust is None else aust, aging_h, aging_c)


def string_values(doc):
    if isinstance(doc, dict):
        for v in doc.values():
            yield from string_values(v)
    elif isinstance(doc, list):
        for v in doc:
            yield from string_values(v)
    elif isinstance(doc, str):
        yield doc


ALL_ALLOYS = STEELS + NON_STEELS
NOT_MODELLED = "unavailable-not-modelled"
ABOVE_SOLVUS = "unavailable-aging-temperature-at-or-above-solvus"
LSW_CODES = ["missing-source-bound-model", "missing-source-constant"]
LSW_ABOVE_CODES = ["outside-source-model-domain"] + LSW_CODES
LSW_TIMES = [0.1, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 24.0, 48.0, 100.0]
# Values the generic LSW law and the 280 MPa / 9 nm curve served for Ti-6Al-4V at 720 C before SOL-K (the defect the
# spec names), first row (0.1 h).
OLD_TI64_720C_FIRST_ROW = (5.03, 209.3)


class LswUnavailableTest(unittest.TestCase):
    """SOL-K (SPEC_solidification section 6.3): precipitate size and strength are unavailable for every alloy.

    The generic coarsening law (constants shared by every alloy) and the 280 MPa / 9 nm strengthening curve have no
    source-bound model and no sourced constants. The kinetics model of Ti-6Al-4V is itself unavailable, yet the
    solver used to return 5.03 nm / 209.3 MPa for it at 720 C.
    """

    def test_ti64_at_720_c_no_longer_returns_a_size_or_a_strength(self):
        res = solve("Ti-6Al-4V")
        self.assertEqual(res["kineticsModel"]["status"], "unavailable")
        first = res["lswPrecipitateCoarsening"][0]
        self.assertEqual(first, {"agingTime_h": 0.1, "meanRadius_nm": None, "precipitationHardening_MPa": None,
                                 "strengtheningMechanism": None, "status": NOT_MODELLED, "reasonCodes": LSW_CODES})
        text = json.dumps(res)
        for old in OLD_TI64_720C_FIRST_ROW:
            self.assertNotIn(f": {old},", text)
        for word in ("Weak-Pair", "Orowan", "generic-constants-illustrative"):
            self.assertNotIn(word, text)

    def test_every_alloy_and_aging_input_gives_null_rows_with_a_status_and_codes(self):
        for name in ALL_ALLOYS:
            for aging_c in (25.0, 120.0, 300.0, 550.0, 600.0, 720.0, 1100.0, 5000.0):
                with self.subTest(alloy=name, aging_c=aging_c):
                    res = solve(name, aging_c=aging_c)
                    rows = res["lswPrecipitateCoarsening"]
                    self.assertEqual([r["agingTime_h"] for r in rows], LSW_TIMES)
                    meta = alloy_registry.resolve_alloy(name, alloy_registry.DOMAIN_KINETICS)
                    ae3, ae1 = (meta.value(k, alloy_registry.DOMAIN_KINETICS) for k in ("Ae3_C", "Ae1_C"))
                    above = aging_c >= ae3 or (name in STEELS and aging_c >= ae1)
                    for row in rows:
                        self.assertEqual(list(row), ["agingTime_h", "meanRadius_nm", "precipitationHardening_MPa",
                                                     "strengtheningMechanism", "status", "reasonCodes"])
                        self.assertEqual((row["meanRadius_nm"], row["precipitationHardening_MPa"],
                                          row["strengtheningMechanism"]), (None, None, None))
                        self.assertEqual(row["status"], ABOVE_SOLVUS if above else NOT_MODELLED)
                        self.assertEqual(row["reasonCodes"], LSW_ABOVE_CODES if above else LSW_CODES)
                    block = res["kineticsModel"]["lswPrecipitateCoarsening"]
                    self.assertEqual(block["status"], ABOVE_SOLVUS if above else NOT_MODELLED)
                    self.assertEqual(block["reasonCodes"], LSW_ABOVE_CODES if above else LSW_CODES)
                    self.assertIsNone(block["note"])
                    self.assertEqual(block["reason"] is not None, above)
                    # independent rule of the oracle (tools/kinetics_documented_changes) agrees on the whole document
                    self.assertEqual(kdc.document_violations(json.loads(json.dumps(res))), [])

    def test_reason_codes_are_codes_and_add_no_sentence(self):
        for name in ALL_ALLOYS:
            res = solve(name, aging_c=300.0)  # below every registry limit: the two base codes only
            codes = {c for r in res["lswPrecipitateCoarsening"] for c in r["reasonCodes"]}
            codes |= set(res["kineticsModel"]["lswPrecipitateCoarsening"]["reasonCodes"])
            self.assertEqual(codes, set(LSW_CODES))
            for code in codes:
                self.assertRegex(code, r"^[a-z]+(-[a-z]+)+$")

    def test_nothing_about_the_old_curve_is_left_in_the_solver(self):
        # removed, not hidden: no generic LSW constant and no strengthening constant in the solver source
        tree = ast.parse((HERE / "kinetics_ttt_cct_solver.py").read_text(encoding="utf-8"))
        floats = {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, float)}
        for old in (0.045, 1.1e-5, 1.2e-4, 280.0):
            self.assertNotIn(old, floats)
        for name in ("LSW_NOTE", "STATUS_LSW_ILLUSTRATIVE"):
            self.assertFalse(hasattr(kin, name), name)

    def test_aging_time_is_validated_but_does_not_change_any_row(self):
        # the rows are the fixed time grid, all null: the requested aging time is only echoed
        base = solve("AISI 4140", aging_h=8.0)
        for hours in (0.0, 1e-9, 100.0, 1e9):
            other = solve("AISI 4140", aging_h=hours)
            self.assertEqual(other["lswPrecipitateCoarsening"], base["lswPrecipitateCoarsening"])
            self.assertEqual(other["inputParameters"]["agingTime_h"], hours)


class AgingInputTest(unittest.TestCase):
    """SOL-K input checks (SPEC_solidification section 6.3): nonphysical aging inputs are refused before arithmetic."""

    BAD_TEMPS = (float("nan"), float("inf"), float("-inf"), -273.15, -273.16, -300.0, -1e308, None, True, False, "720",
                 [720.0], {"C": 720.0})
    GOOD_TEMPS = (math.nextafter(-273.15, math.inf), -273.1499, -200.0, 0.0, 25.0, 720, 720.0, 5000.0, 1e300)
    BAD_TIMES = (float("nan"), float("inf"), float("-inf"), -1e-9, -1.0, -1e308, None, True, "8", [8.0])
    GOOD_TIMES = (0.0, 1e-9, 8, 8.0, 1e9)
    CASES = ("AISI 4140", "AISI D2", "Inconel 718", "Ti-6Al-4V", "Al 7075")  # modelled steel, outside range, non-steels

    def _refused(self, **kwargs):
        with self.assertRaises(input_validation.ValidationError) as ctx:
            kin.solve_phase_transformation_kinetics(**kwargs)
        return ctx.exception

    def test_bad_aging_temperatures_are_refused_with_the_reason_code(self):
        for name in self.CASES:
            for temp in self.BAD_TEMPS:
                with self.subTest(alloy=name, temp=repr(temp)):
                    err = self._refused(alloy_name=name, aging_temp_c=temp)
                    self.assertEqual(err.field, "agingTemp_C")
                    self.assertIn(err.code, (input_validation.NON_FINITE, input_validation.OUT_OF_RANGE))
                    self.assertEqual(err.detail["reasonCode"], "nonphysical-input")
                    self.assertEqual(kdc.aging_input_reason(temp, 8.0), "nonphysical-input")
                    # the envelope is strict JSON: no bare NaN/Infinity token
                    json.dumps(input_validation.validation_envelope(err), allow_nan=False)

    def test_bad_aging_times_are_refused_with_the_reason_code(self):
        for name in self.CASES:
            for hours in self.BAD_TIMES:
                with self.subTest(alloy=name, hours=repr(hours)):
                    err = self._refused(alloy_name=name, aging_time_h=hours)
                    self.assertEqual(err.field, "agingTime_h")
                    self.assertEqual(err.detail["reasonCode"], "nonphysical-input")
                    self.assertEqual(kdc.aging_input_reason(720.0, hours), "nonphysical-input")
                    json.dumps(input_validation.validation_envelope(err), allow_nan=False)

    def test_absolute_zero_is_refused_and_the_next_float_above_it_is_not(self):
        # -273.15 C is 0 K: it used to raise a bare ZeroDivisionError inside the solver
        err = self._refused(alloy_name="Ti-6Al-4V", aging_temp_c=-273.15)
        self.assertEqual(err.code, input_validation.OUT_OF_RANGE)
        self.assertGreater(math.nextafter(-273.15, math.inf) + 273.15, 0.0)
        self.assertEqual(kdc.aging_input_reason(-273.15, 8.0), "nonphysical-input")
        self.assertIsNone(kdc.aging_input_reason(math.nextafter(-273.15, math.inf), 8.0))

    def test_good_aging_inputs_are_accepted_and_echoed_unchanged(self):
        for name in self.CASES:
            for temp in self.GOOD_TEMPS:
                with self.subTest(alloy=name, temp=temp):
                    res = kin.solve_phase_transformation_kinetics(name, aging_temp_c=temp)
                    self.assertEqual(res["inputParameters"]["agingTemp_C"], temp)
                    self.assertIs(type(res["inputParameters"]["agingTemp_C"]), type(temp))
                    self.assertIsNone(kdc.aging_input_reason(temp, 8.0))
                    json.dumps(res, allow_nan=False)
            for hours in self.GOOD_TIMES:
                with self.subTest(alloy=name, hours=hours):
                    res = kin.solve_phase_transformation_kinetics(name, aging_time_h=hours)
                    self.assertEqual(res["inputParameters"]["agingTime_h"], hours)
                    self.assertIsNone(kdc.aging_input_reason(720.0, hours))

    def test_the_oracle_rule_and_the_solver_agree_on_a_grid(self):
        for temp in (-1e9, -273.16, -273.15, math.nextafter(-273.15, math.inf), -273.14, 0.0, 720.0, float("nan")):
            for hours in (-1.0, 0.0, 8.0, float("inf")):
                try:
                    kin.solve_phase_transformation_kinetics("Ti-6Al-4V", aging_temp_c=temp, aging_time_h=hours)
                    refused = False
                except input_validation.ValidationError:
                    refused = True
                self.assertEqual(refused, kdc.aging_input_reason(temp, hours) is not None, (temp, hours))

    def test_a_nonphysical_input_never_reaches_the_output_document(self):
        doc = json.loads(json.dumps(solve("AISI 4140")))
        self.assertEqual(kdc.document_violations(doc), [])
        for params in ({"agingTemp_C": -273.15}, {"agingTemp_C": float("nan")}, {"agingTemp_C": -400.0},
                       {"agingTime_h": -1.0}, {"agingTime_h": float("inf")}):
            bad = json.loads(json.dumps(doc))
            bad["inputParameters"].update(params)
            self.assertTrue(kdc.document_violations(bad), params)

    def test_echoed_inputs_of_an_unmodelled_alloy_must_be_numbers_too(self):
        # the other inputs are only echoed for a non-steel; a NaN there used to reach the JSON as a bare token
        for name in ("Inconel 718", "AISI D2"):
            for field, key in (("grainSize_um", "grain_size_um"), ("austTemp_C", "aust_temp_c")):
                for bad in (float("nan"), float("inf"), None, "25"):
                    with self.subTest(alloy=name, field=field, bad=repr(bad)):
                        err = self._refused(alloy_name=name, **{key: bad})
                        self.assertEqual((err.code, err.field), (input_validation.NON_FINITE, field))

    def test_cli_refuses_nonphysical_aging_with_exit_2_and_strict_json(self):
        def strict(text):
            def refuse(token):
                raise AssertionError(f"bare {token} token in the output")
            return json.loads(text, parse_constant=refuse)

        # `NaN` is a bare token that Python's json parser accepts on stdin
        for raw in ('{"alloy": "Ti-6Al-4V", "agingTemp_C": NaN}', '{"alloy": "Ti-6Al-4V", "agingTemp_C": -273.15}',
                    '{"alloy": "Inconel 718", "agingTime_h": -1}', '{"alloy": "AISI 4140", "agingTemp_C": Infinity}'):
            with self.subTest(raw=raw):
                proc = subprocess.run([sys.executable, "-B", "kinetics_ttt_cct_solver.py"], capture_output=True,
                                      cwd=str(HERE), input=raw.encode())
                self.assertEqual(proc.returncode, 2, proc.stderr)
                out = strict(proc.stdout.decode("utf-8"))
                self.assertEqual((out["success"], out["errorKind"]), (False, "validation"))
                self.assertEqual(out["error"]["detail"]["reasonCode"], "nonphysical-input")
        ok = subprocess.run([sys.executable, "-B", "kinetics_ttt_cct_solver.py"], capture_output=True, cwd=str(HERE),
                            input=json.dumps({"alloy": "Ti-6Al-4V", "agingTemp_C": 720}).encode())
        self.assertEqual(ok.returncode, 0, ok.stderr)
        self.assertIsNone(strict(ok.stdout.decode("utf-8"))["lswPrecipitateCoarsening"][0]["meanRadius_nm"])


# Digests of the Li (1998) TTT/CCT output and everything else outside the LSW rows, taken from the solver at
# fbf68b4c (before SOL-K) and checked equal after it: sha256 of json.dumps(document without computeTimeMs,
# lswPrecipitateCoarsening and kineticsModel.lswPrecipitateCoarsening, ensure_ascii=False), key order included.
# Case i: 0 = defaults, 1 = (cooling 0.3, grain 40, aust 900, aging 4 h, 650 C), 2 = (cooling 2000).
LI_OUTSIDE_LSW_SHA256 = {
    ("AISI 4140", 0): "9851220a3b70cf22669c8d7b0d6c57d154b950e9561861f9b88528c5c181e687",
    ("AISI 4140", 1): "8336b5466673bed173255ecc285fa2c497fb3fa69ce5c6bfc32cfd41cefdd3c2",
    ("AISI 4140", 2): "82ee69e5c5dc2887a439d342e52e30693d762bd8e12d27fc8135d28ab3c4c414",
    ("AISI 4340", 0): "99e555a8a90f4c7426bed15c075de56397d1a544bb1566f54afce0a93946b0ba",
    ("AISI 4340", 1): "64ab85ff7d21aec6dbafc2b3957ce579adc699e9d1d5a59e4fad35d59a150661",
    ("AISI 4340", 2): "5e76cbba83e1fd4271ad3b4fa92e60c001b27de66273a9e31afcdc87e53fadad",
    ("AISI D2", 0): "73277bcb4524e6159b0319671971ce10edaf66d4344116ae89316fda504ce19f",
    ("AISI D2", 1): "da942a78997b573160571b96e36d48d6d832a258fd660f19159d3fc4ba9a3481",
    ("AISI D2", 2): "0c26de2ece4a3713de725ab918e10009454c4f033fb9033ce35b9ce4d2942842",
    ("Inconel 718", 0): "b9ad0b804330c2e230649807a6853c24c0af3209d631b6af9ca44eb6ea4560e2",
    ("Inconel 718", 1): "9bbec141e02591544cbc45dc2e4ca18fdf0680f703d3a24279791971f8e263d6",
    ("Inconel 718", 2): "e7f94c93cc6e673fd63a1f6dada89ca6469556b515f08af83df170a7d83efe58",
    ("Ti-6Al-4V", 0): "7e79cdfad533bdbe2df222c31bdc6db53229261ee6a3843b0cca37144576573d",
    ("Ti-6Al-4V", 1): "6446ab3096aa8e75b51fb1cc8557bfedc63f3f4279f1af96c658ff3f10948182",
    ("Ti-6Al-4V", 2): "a3da0546962f01331f28104cb8166c2714215371b4bcc520068b88d577e4830b",
    ("Al 7075", 0): "9a0c2bf36dfaf7f20b5b0ce21f9739e7c6dce5b8e59fd2c1463137f27a7fa7fa",
    ("Al 7075", 1): "de354ede095b6f8d00956e9fd8884898cad796deeb2c7c4f75b0093aa4fa6b14",
    ("Al 7075", 2): "bd678817c7b083d13e704e74120130cea2d19ca4ffd4f2138e23cd29b2b1a481",
}


class LiOutputUnchangedBySolKTest(unittest.TestCase):
    ARGS = ((), (0.3, 40.0, 900.0, 4.0, 650.0), (2000.0,))

    @staticmethod
    def outside_lsw_sha256(result):
        doc = json.loads(json.dumps(result))
        doc.pop("computeTimeMs", None)
        doc.pop("lswPrecipitateCoarsening")
        doc["kineticsModel"].pop("lswPrecipitateCoarsening")
        return hashlib.sha256(json.dumps(doc, ensure_ascii=False).encode("utf-8")).hexdigest()

    def test_ttt_cct_and_everything_outside_the_lsw_rows_are_byte_equal_to_before_sol_k(self):
        self.assertEqual(len(LI_OUTSIDE_LSW_SHA256), len(ALL_ALLOYS) * len(self.ARGS))
        for (name, i), expected in LI_OUTSIDE_LSW_SHA256.items():
            with self.subTest(alloy=name, case=i):
                res = kin.solve_phase_transformation_kinetics(name, *self.ARGS[i])
                self.assertEqual(self.outside_lsw_sha256(res), expected)

    def test_the_digest_sees_a_changed_li_value(self):
        res = kin.solve_phase_transformation_kinetics("AISI 4140")
        res["tttIsothermalCurves"][0]["tStart_s"] *= 1.000001
        self.assertNotEqual(self.outside_lsw_sha256(res), LI_OUTSIDE_LSW_SHA256[("AISI 4140", 0)])


class SteelOnlyTest(unittest.TestCase):
    def test_non_steel_outputs_are_unavailable_with_the_reason(self):
        for name in NON_STEELS:
            with self.subTest(alloy=name):
                res = solve(name, cooling=100.0)
                self.assertEqual(res["kineticsModel"]["status"], "unavailable")
                self.assertEqual(res["kineticsModel"]["reason"], STEEL_ONLY)
                self.assertIsNone(res["tttIsothermalCurves"])
                self.assertEqual(res["tttIncubationFloor"]["status"], "unavailable-kinetics-model-steel-only")
                self.assertEqual(len(res["cctContinuousCoolingMap"]), 10)
                for row in res["cctContinuousCoolingMap"]:
                    self.assertEqual(set(row["phaseFractions"]),
                                     {"Martensite_pct", "Bainite_pct", "Pearlite_Ferrite_pct", "RetainedAustenite_pct"})
                    self.assertTrue(all(v is None for v in row["phaseFractions"].values()))
                    for key in ("transformedStartTemp_C", "transformedStartTime_s", "primaryMicrostructure",
                                "predictedHardness_HRC", "predictedHardness_HV"):
                        self.assertIsNone(row[key], key)
                    for key in ("transformedStart_status", "phaseFractions_status", "predictedHardness_HRC_status"):
                        self.assertEqual(row[key], "unavailable-kinetics-model-steel-only")
                    self.assertEqual(row["unavailableReason"], STEEL_ONLY)
                    self.assertEqual(row["predictedHardness_HV_status"], "unavailable-no-verified-table-for-alloy-class")
                gap = res["calphadVsKineticsGap"]
                for block in gap.values():
                    self.assertEqual(block["status"], "unavailable-kinetics-model-steel-only")
                    self.assertEqual(block["reason"], STEEL_ONLY)
                self.assertTrue(all(gap["equilibriumPrediction"][k] is None for k in
                                    ("stablePhasesAtRT", "martensiteFraction", "soluteSupersaturation")))
                reality = gap["kineticRealityAtSelectedCooling"]
                self.assertEqual(reality["coolingRate_C_s"], 100.0)  # the user's own input
                for key in ("criticalCoolingRate_C_s", "isSuppressedEquilibrium", "predictedMartensite_pct",
                            "diffusionSuppressionIndex", "verdict"):
                    self.assertIsNone(reality[key], key)
                crit = res["criticalTransformationTemperatures"]
                self.assertIsNone(crit["CriticalCoolingRate_CCR_C_s"])
                # the steel-template registry echoes are withdrawn in both blocks (fx-kinetics review S3/S4)
                self.assertIsNone(crit["Ae1_C"])
                self.assertEqual(crit["Ae1_C_status"], "unavailable-kinetics-model-steel-only")
                self.assertIsNone(res["alloyMetadata"]["Ae1_C"])
                self.assertIsNone(res["alloyMetadata"]["critical_cooling_rate_C_s"])
                self.assertEqual(crit["CriticalCoolingRate_CCR_status"], "unavailable-kinetics-model-steel-only")
                # the model note does not repeat the reason (the UI prints both)
                self.assertFalse(res["kineticsModel"]["note"].startswith(STEEL_ONLY))
                self.assertFalse(res["tttIncubationFloor"]["note"].startswith(STEEL_ONLY))

    def test_old_audit_claims_are_gone(self):
        # audit: IN718 at 100 C/s gave 63 % "martensite"; "Ferrite + Cementite" for every alloy.
        res = solve("Inconel 718", cooling=100.0)
        self.assertIsNone(res["calphadVsKineticsGap"]["kineticRealityAtSelectedCooling"]["predictedMartensite_pct"])
        for name in NON_STEELS:
            res = solve(name)
            res.pop("alloyMetadata")  # registry labels (real IN718 phases such as Gamma Prime) are not model output
            text = " ".join(string_values(res))
            for word in ("Ferrite", "Cementite", "Pearlite", "Bainite", "Martensite", "Equiaxed Alpha", "Gamma Prime"):
                self.assertNotIn(word, text, f"{name}: steel-template word {word!r} in a value")

    def test_steel_class_is_the_registry_descriptor_type(self):
        for name in STEELS + NON_STEELS:
            rid, _legacy, meta = kin.resolve_kinetics_alloy(name)
            self.assertEqual(kin.is_steel_alloy(meta), rid in kin.E140_NON_AUSTENITIC_STEEL_IDS, name)
            self.assertEqual(kin.is_steel_alloy(meta), name in STEELS)

    def test_steel_values_come_from_the_li_model_with_statuses(self):
        res = solve("AISI 4140", cooling=100.0)
        self.assertEqual(res["kineticsModel"]["status"], "available")
        self.assertIsNone(res["kineticsModel"]["reason"])
        self.assertIs(res["kineticsModel"]["illustrativeOnly"], True)
        self.assertEqual(res["kineticsModel"]["validationStatus"], "unvalidated")
        row = next(r for r in res["cctContinuousCoolingMap"] if r["coolingRate_C_s"] == 100.0)
        # the former lookup (98 % martensite, 58 HRC) is gone: fractions and hardness are not computed
        self.assertIsNone(row["phaseFractions"]["Martensite_pct"])
        self.assertIsNone(row["predictedHardness_HRC"])
        self.assertEqual(row["phaseFractions_status"], "unavailable-fractions-not-computed")
        self.assertEqual(row["predictedHardness_HRC_status"], "unavailable-fractions-not-computed")
        self.assertEqual(row["primaryMicrostructure"], "Martensite (Athermal)")
        self.assertEqual(res["calphadVsKineticsGap"]["equilibriumPrediction"]["status"],
                         "static-text-not-a-calphad-calculation")
        reality = res["calphadVsKineticsGap"]["kineticRealityAtSelectedCooling"]
        self.assertTrue(reality["isSuppressedEquilibrium"])
        self.assertEqual(reality["predictedMartensite_pct"], 96.5)  # Koistinen-Marburger at 25 C from Ms 328.5 C

    def test_registry_placeholders_are_never_reported(self):
        self.assertEqual(alloy_registry.KINETICS_PLACEHOLDERS,
                         {("in718", "Ms_C"), ("in718", "Mf_C"), ("al7075", "Ms_C"), ("al7075", "Mf_C")})
        for name in ("Inconel 718", "Al 7075"):
            res = solve(name)
            crit = res["criticalTransformationTemperatures"]
            self.assertIsNone(crit["Ms_C"])
            self.assertIsNone(crit["Mf_C"])
            self.assertEqual(crit["Ms_C_status"], "unavailable-registry-placeholder")
            self.assertEqual(crit["Mf_C_status"], "unavailable-registry-placeholder")
            self.assertIsNone(res["alloyMetadata"]["Ms_C"])
            self.assertIsNone(res["alloyMetadata"]["Mf_C"])
            self.assertEqual(sorted(res["kineticsModel"]["placeholderParameters"]), ["Mf_C", "Ms_C"])
            self.assertNotIn(-50.0, [res["alloyMetadata"].get("Ms_C"), crit["Ms_C"]])
        # the Ti-6Al-4V Ms/Mf are not flagged: reported as the registry screening value
        ti = solve("Ti-6Al-4V")["criticalTransformationTemperatures"]
        self.assertEqual((ti["Ms_C"], ti["Mf_C"]), (800.0, 650.0))
        self.assertEqual(ti["Ms_C_status"], "registry-screening-value")

    def test_the_flags_drive_the_output(self):
        flags = frozenset(alloy_registry.KINETICS_PLACEHOLDERS | {("aisi4140", "Ms_C")})
        with mock.patch.object(alloy_registry, "KINETICS_PLACEHOLDERS", flags):
            res = solve("AISI 4140")
        # the flagged registry echo is withheld; the Li model's own Ms (composition, Kung-Rayment) is not a
        # registry value and stays
        self.assertIsNone(res["alloyMetadata"]["Ms_C"])
        self.assertEqual(res["kineticsModel"]["placeholderParameters"], ["Ms_C"])
        self.assertEqual(res["criticalTransformationTemperatures"]["Ms_C"], 328.5)
        self.assertEqual(res["alloyMetadata"]["Mf_C"], 180.0)

    def test_every_alloy_serialises_without_nan_or_inf(self):
        for name in STEELS + NON_STEELS:
            for cooling in (0.05, 10.0, 2000.0):
                text = json.dumps(solve(name, cooling=cooling), allow_nan=False)
                self.assertNotIn("NaN", text)


class NoFloorTest(unittest.TestCase):
    """The audit's 1 ms incubation floor (32 of 40 AISI 4140 TTT points) is gone with the Li (1998) law."""

    def test_no_point_is_on_a_floor(self):
        for name in ("AISI 4140", "AISI 4340"):
            res = solve(name)
            curves = res["tttIsothermalCurves"]
            self.assertTrue(curves)
            self.assertTrue(all(p["floorHit"] is False for p in curves))
            self.assertEqual(res["tttIncubationFloor"], {
                "status": "no-floor-li-1998-law", "floorValue_s": None, "pointCount": len(curves),
                "floorHitCount": 0, "note": kin.TTT_NO_FLOOR_NOTE})
            self.assertEqual({p["phase"] for p in curves}, {"Ferrite", "Pearlite", "Bainite"})

    def test_point_key_set_is_kept(self):
        res = solve("AISI 4140")
        self.assertEqual(list(res["tttIsothermalCurves"][0]),
                         ["temperature_C", "phase", "tStart_s", "t50_s", "tFinish_s", "avramiExponent_n",
                          "drivingForce_DeltaT_C", "floorHit"])
        self.assertIsNone(res["tttIsothermalCurves"][0]["avramiExponent_n"])  # S(X), not an Avrami exponent

    def test_cct_pearlite_at_770_at_every_rate_is_gone(self):
        # audit: "Pearlite starts at ~770 C" at every cooling rate for AISI 4140 up to 500 C/s.
        res = solve("AISI 4140")
        rows = res["cctContinuousCoolingMap"]
        self.assertFalse(any(r["primaryMicrostructure"] == "Pearlite" and r["transformedStartTemp_C"] >= 760.0
                             for r in rows))
        self.assertEqual([r["primaryMicrostructure"] for r in rows][-3:], ["Martensite (Athermal)"] * 3)

    def test_athermal_row_above_the_critical_cooling_rate(self):
        res = solve("AISI 4140")
        crit = res["criticalTransformationTemperatures"]
        for row in res["cctContinuousCoolingMap"]:
            if row["coolingRate_C_s"] >= crit["CriticalCoolingRate_CCR_C_s"]:
                self.assertEqual((row["transformedStartTemp_C"], row["primaryMicrostructure"]),
                                 (crit["Ms_C"], "Martensite (Athermal)"))
                self.assertEqual(row["transformedStart_status"], "athermal-martensite-no-diffusional-start-above-ms")
                self.assertIsNone(row["unavailableReason"])
            else:
                self.assertEqual(row["transformedStart_status"], "li1998-additivity-first-diffusional-start")


class LswAboveSolvusTest(unittest.TestCase):
    """fx-kinetics review S2: at or above the registry Ae3 (steels: Ae1) the rows keep their more specific status.

    SOL-K: every row is unavailable anyway; only the status and the reason codes tell the two cases apart.
    """

    LIMIT = {"AISI 4140": 725.0, "AISI 4340": 710.0, "AISI D2": 800.0,  # Ae1 of the steels
             "Inconel 718": 1020.0, "Ti-6Al-4V": 995.0, "Al 7075": 480.0}  # Ae3 of the non-steels

    def test_al7075_studio_default_720_c_is_unavailable(self):
        res = solve("Al 7075")  # 720 C, above its 480 C solvus (and above its liquidus)
        for row in res["lswPrecipitateCoarsening"]:
            self.assertEqual((row["meanRadius_nm"], row["precipitationHardening_MPa"], row["strengtheningMechanism"]),
                             (None, None, None))
            self.assertEqual(row["status"], ABOVE_SOLVUS)
            self.assertEqual(row["reasonCodes"], LSW_ABOVE_CODES)
        block = res["kineticsModel"]["lswPrecipitateCoarsening"]
        self.assertEqual(block["status"], ABOVE_SOLVUS)
        self.assertIn("720 C is at or above the registry Ae3 (solvus/transus) of 480 C", block["reason"])
        self.assertNotIn("1884", json.dumps(res))  # the old 1.88 um "Orowan" value

    def test_boundary_is_at_or_above_the_registry_temperature(self):
        for name, limit in self.LIMIT.items():
            below = solve(name, aging_c=limit - 0.1)["lswPrecipitateCoarsening"]
            at = solve(name, aging_c=limit)["lswPrecipitateCoarsening"]
            self.assertTrue(all(r["status"] == NOT_MODELLED for r in below), name)
            self.assertTrue(all(r["status"] == ABOVE_SOLVUS for r in at), name)
            self.assertTrue(all(r["meanRadius_nm"] is None for r in below + at), name)

    def test_steels_use_ae1_and_non_steels_only_ae3(self):
        # 4340 (Ae1 710 C) is at the old 720 C default: above its limit; Ti-6Al-4V 720 C is above the Ae1 of its
        # registry row (700 C, a steel concept that is withheld) but below its 995 C transus: not above the limit.
        self.assertEqual(solve("AISI 4340")["lswPrecipitateCoarsening"][0]["status"], ABOVE_SOLVUS)
        self.assertIn("Ae1", solve("AISI 4340")["kineticsModel"]["lswPrecipitateCoarsening"]["reason"])
        self.assertEqual(solve("Ti-6Al-4V")["lswPrecipitateCoarsening"][0]["status"], NOT_MODELLED)
        self.assertEqual(solve("AISI 4140", aging_c=600.0)["lswPrecipitateCoarsening"][0]["status"], NOT_MODELLED)

    def test_below_the_limit_the_block_has_no_reason_sentence_and_no_note(self):
        block = solve("AISI 4140", aging_c=600.0)["kineticsModel"]["lswPrecipitateCoarsening"]
        self.assertEqual(block, {"status": NOT_MODELLED, "note": None, "reason": None, "reasonCodes": LSW_CODES})


class SteelTextTest(unittest.TestCase):
    def test_d2_is_outside_the_li_range_and_unavailable(self):
        res = solve("AISI D2")
        self.assertEqual(res["kineticsModel"]["status"], "unavailable")
        self.assertTrue(res["kineticsModel"]["reason"].startswith("composition outside the Li (1998) model range"))
        eq = res["calphadVsKineticsGap"]["equilibriumPrediction"]
        self.assertIsNone(eq["stablePhasesAtRT"])
        self.assertEqual(eq["status"], "unavailable-composition-outside-li-model-range")
        for name in ("AISI 4140", "AISI 4340"):
            self.assertIn("Cementite", solve(name)["calphadVsKineticsGap"]["equilibriumPrediction"]["stablePhasesAtRT"])


class StudioFixtureTest(unittest.TestCase):
    def test_committed_fixture_is_the_current_solver_output(self):
        committed = json.loads(STUDIO_FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(committed, studio_fixture_results(),
                         "tests/fixtures/kinetics-studio-results.json is stale: python -B test_kinetics_fx.py --write-studio-fixture")


class MainEnvelopeTest(unittest.TestCase):
    def test_stdout_json_has_the_new_keys(self):
        proc = subprocess.run([sys.executable, "-B", "kinetics_ttt_cct_solver.py"], capture_output=True, cwd=str(HERE),
                              input=json.dumps({"alloy": "Inconel 718", "coolingRate_C_s": 100.0}).encode())
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = json.loads(proc.stdout.decode("utf-8"))
        self.assertEqual(out["kineticsModel"]["reason"], STEEL_ONLY)
        self.assertIsNone(out["tttIsothermalCurves"])
        self.assertIn("provenance", out)


if __name__ == "__main__":
    if "--write-studio-fixture" in sys.argv:
        STUDIO_FIXTURE.write_text(json.dumps(studio_fixture_results(), indent=1, ensure_ascii=False) + "\n",
                                  encoding="utf-8", newline="\n")
    else:
        unittest.main()
