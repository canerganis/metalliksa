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
# 10 C/s, grain 25 um, aging 8 h. The last two reproduce the former 720 C aging default.
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
LSW_CODES = ["missing-source-bound-model", "missing-source-constant"]
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
                    for row in rows:
                        self.assertEqual(list(row), ["agingTime_h", "meanRadius_nm", "precipitationHardening_MPa",
                                                     "strengtheningMechanism", "status", "reasonCodes"])
                        self.assertEqual((row["meanRadius_nm"], row["precipitationHardening_MPa"],
                                          row["strengtheningMechanism"]), (None, None, None))
                        self.assertEqual(row["status"], NOT_MODELLED)
                        self.assertEqual(row["reasonCodes"], LSW_CODES)
                    block = res["kineticsModel"]["lswPrecipitateCoarsening"]
                    self.assertEqual(block["status"], NOT_MODELLED)
                    self.assertEqual(block["reasonCodes"], LSW_CODES)
                    self.assertIsNone(block["note"])
                    self.assertIsNone(block["reason"])
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

    def test_reason_codes_belong_to_quantity_envelope_registry(self):
        try:
            import quantity_envelope
        except ModuleNotFoundError as exc:
            if exc.name != "quantity_envelope":
                raise
            self.skipTest("BR-7: Phase 0 quantity_envelope is not in this branch; required after batch merge")
        codes = {value for name, value in vars(kin).items() if name.startswith("REASON_")}
        self.assertLessEqual(codes, set(quantity_envelope.REASON_CODES))

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
                 [720.0], {"C": 720.0}, 10**400)
    GOOD_TEMPS = (math.nextafter(-273.15, math.inf), -273.1499, -200.0, 0.0, 25.0, 720, 720.0, 5000.0, 1e300)
    BAD_TIMES = (float("nan"), float("inf"), float("-inf"), -1e-9, -1.0, -1e308, None, True, "8", [8.0], 10**400)
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

    def test_unmodelled_echoes_are_physical_and_oracle_rejects_mutations(self):
        for name in ("Inconel 718", "AISI D2", "Ti-6Al-4V"):
            base = solve(name, aust=-273.15)
            self.assertEqual(kdc.document_violations(base), [])
            for field, key, output_key, bad_values in (
                ("austTemp_C", "aust_temp_c", "austSolutionTemp_C", (-273.16, -1000.0)),
                ("grainSize_um", "grain_size_um", "priorGrainSize_um", (0, -1)),
                ("coolingRate_C_s", "cooling_rate_c_s", "selectedCoolingRate_C_s", (0, -1)),
            ):
                for value in bad_values:
                    with self.subTest(alloy=name, field=field, value=value):
                        err = self._refused(alloy_name=name, **{key: value})
                        self.assertEqual(err.field, field)
                        mutant = json.loads(json.dumps(base))
                        mutant["inputParameters"][output_key] = value
                        self.assertTrue(kdc.document_violations(mutant))

    def test_temperature_bound_message_is_clean(self):
        for name in self.CASES:
            err = self._refused(alloy_name=name, aging_temp_c=-273.15)
            self.assertEqual(err.message, "must be > -273.15 degC")
        err = self._refused(alloy_name="Ti-6Al-4V", aust_temp_c=-273.16)
        self.assertEqual(err.message, "must be >= -273.15 degC")

    def test_cli_refuses_nonphysical_aging_with_exit_2_and_strict_json(self):
        def strict(text):
            def refuse(token):
                raise AssertionError(f"bare {token} token in the output")
            return json.loads(text, parse_constant=refuse)

        # `NaN` is a bare token that Python's json parser accepts on stdin
        for raw in (json.dumps({"alloy": "Ti-6Al-4V", "agingTemp_C": 10**400}),
                    json.dumps({"alloy": "AISI 4140", "agingTime_h": 10**400}),
                    '{"alloy": "Ti-6Al-4V", "agingTemp_C": NaN}', '{"alloy": "Ti-6Al-4V", "agingTemp_C": -273.15}',
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
# fbf68b4c (before SOL-K) and checked equal after it: sha256 of json.dumps(document without engine, computeTimeMs,
# lswPrecipitateCoarsening and kineticsModel.lswPrecipitateCoarsening, ensure_ascii=False), key order included.
# SOLK-3: engine is excluded; these pins were derived before gate edits after verifying all 18 original pins.
# Case i: 0 = defaults, 1 = (cooling 0.3, grain 40, aust 900, aging 4 h, 650 C), 2 = (cooling 2000).
LI_OUTSIDE_LSW_SHA256 = {
    ("AISI 4140", 0): "a003777f07a271f7d8757d8c0a43f3cbb6989f9e11fcdca837cf675298b4f674",
    ("AISI 4140", 1): "b03fe22bba70128d84070d4281ddadf175719490d60cd2eb35913276ac0f34b4",
    ("AISI 4140", 2): "71c83e2376bf92549d0c1dfd29eb8b725a2a77cda9e2a333578346667eb9087e",
    ("AISI 4340", 0): "d8ced403d26a33d42445406416782d25ca279eb511716642e41e1a093081b1b0",
    ("AISI 4340", 1): "c536c94d68cccf17139bd4479aa68e819fa9686b3dba3fe8db61c89d3bf5df80",
    ("AISI 4340", 2): "7e1f4d469a32ba995ec6c8ddbdf53ce371983344a49ee033213626d4a7ca9d1f",
    ("AISI D2", 0): "fa1804e263a381ee3272c3303726d6d011d0fb7d47792aac8278ed617648cc73",
    ("AISI D2", 1): "db2e9bbacb9d6c256fa5f72553165951942f7e7fb51fb0ff25eeed5cf4fbcebf",
    ("AISI D2", 2): "0ad0768207ad55fb876d8f5a70297530feb61f183ba803e14a237b5c05ce16fd",
    ("Inconel 718", 0): "9393004f32db83189dfdb5b72fcd3b24e3b3b23b1cbb476b8b1b4deb79affdb0",
    ("Inconel 718", 1): "53dea575e3c35d773db57169848daefaa965b3e3420d740503d1098b014cebcd",
    ("Inconel 718", 2): "d2b57ff53f0c12634e2090c2a3ee046acb74a80f508e0a81ad7f9ed515b1bb88",
    ("Ti-6Al-4V", 0): "dfa25530521e1d015df36eebd615b43d8f47f5d48c39fb618170e37a4d8a7893",
    ("Ti-6Al-4V", 1): "321a86fbe20aefc4b1a9f1b53ca91ea657d30c6195da4878e2c8730e59b5fbc7",
    ("Ti-6Al-4V", 2): "6ee6e28578488dda65bda352f97db242ae2e3aad8a90fe2e2cb6d39dff55873b",
    ("Al 7075", 0): "aacebcd15f7d8d03c1bbd094d16ba7388742ef8b5af729cf5a0f52653056b138",
    ("Al 7075", 1): "e9be4c68613acc7f72a9e5ae798765cb8660f0385a44f8fb705008e9ef30c906",
    ("Al 7075", 2): "3789118c2c2a3ab8d9353579c1e816022079b004ec0b991204a3727e3a2b07f2",
}


class LiOutputUnchangedBySolKTest(unittest.TestCase):
    ARGS = ((), (0.3, 40.0, 900.0, 4.0, 650.0), (2000.0,))

    @staticmethod
    def outside_lsw_sha256(result):
        doc = json.loads(json.dumps(result))
        doc.pop("computeTimeMs", None)
        doc.pop("engine")
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


class LswRegistryTemperatureTest(unittest.TestCase):
    def test_registry_transition_temperatures_never_decide_lsw_availability(self):
        for name, limit in {"AISI 4140": 725.0, "AISI 4340": 710.0, "AISI D2": 800.0,
                            "Inconel 718": 1020.0, "Ti-6Al-4V": 995.0, "Al 7075": 480.0}.items():
            for temp in (limit - 0.1, limit, limit + 0.1):
                with self.subTest(alloy=name, temp=temp):
                    result = solve(name, aging_c=temp)
                    self.assertEqual(result["kineticsModel"]["lswPrecipitateCoarsening"],
                                     {"status": NOT_MODELLED, "note": None, "reason": None, "reasonCodes": LSW_CODES})
                    for row in result["lswPrecipitateCoarsening"]:
                        self.assertEqual(row["status"], NOT_MODELLED)
                        self.assertEqual(row["reasonCodes"], LSW_CODES)


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
