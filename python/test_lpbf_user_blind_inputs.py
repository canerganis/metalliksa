"""Intake tests for the user blind test: metadata, inputs CSV, grades, block issues, labels, design checks.

Spec: docs/research/SPEC_research_hub_data_2026-10-14.md sections 4.1 to 4.3, 6.1, 6.2 and 11.1 item 4.
Every CSV and metadata dict is built here from synthetic, invented numbers; nothing is read from disk. The sentinel
777.123 marks a cell value that must never appear in any refusal text or detail.
"""
from __future__ import annotations

import base64
import json
import unittest

import lpbf_blind_stats as stats
import lpbf_user_blind_inputs as ui
from lpbf_user_blind_protocol import BlindRefusal

SENTINEL = "777.123"
TITLE = "Synthetic test block"          # synthetic title constant, not a real campaign


def meta(**over):
    """A valid synthetic metadata dict (pre-measurement, Ti-6Al-4V, bare plate). Nested keys merge one level deep."""
    md = {
        "schema": "lpbf-user-blind-metadata-1", "blockLabel": TITLE, "mode": "pre-measurement",
        "alloy": "Ti-6Al-4V", "quantity": "melt-pool-depth", "depthBoundary": "etched-fusion-boundary",
        "measurementMethod": "optical-cross-section", "depthDatum": "original-surface",
        "reduction": "per-section-raw", "crossSectionLocation": "steady-state-mid-track", "wavelength_nm": 1070,
        "preheat_C": 25, "preheatBasis": "measured", "atmosphere": "argon", "csvDialect": "comma-dot",
        "targetCommitment": None,
        "beam": {"diameter_um": None, "quantity": "diameter", "definition": "1/e2", "basis": "nominal",
                 "profile": "gaussian", "uncertaintyReleased": False, "u_k1_um": None},
        "power": {"basis": "commanded", "meterNamed": False, "uncertaintyReleased": False, "u_k1_rel": None},
        "substrate": {"kind": "bare-plate", "layerThickness_um": None, "amSubstrate": False, "thickness_mm": 10,
                      "surfacePreparation": "ground", "alsi10mgState": None},
        "replication": {"tracksPerCondition": 1, "sectionsPerTrack": 1, "rowsAreSeparateTracks": False},
        "depthUncertainty": {"basis": "not-released", "u_um": None, "coverageFactor": 1},
        "chemistry": {"basis": "unstated", "sulfur_ppm": None, "oxygen_ppm": None},
        "independence": {"predictionsViewedBeforeFreeze": "no", "dataPreviouslyPublished": "no",
                         "publishedDoi": None, "usedForMachineCalibration": False},
    }
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(md.get(k), dict):
            md[k].update(v)
        else:
            md[k] = v
    return md


def nmeta(**over):
    return ui.normalize_metadata(meta(**over))


def csv_bytes(header, rows, sep=",", eol="\n", bom=False):
    text = eol.join(sep.join(str(c) for c in r) for r in [header] + list(rows)) + eol
    return (b"\xef\xbb\xbf" if bom else b"") + text.encode("utf-8")


HEADER = ["condition_id", "power_W", "speed_mm_s", "spot_um"]
ROWS = [["C1", SENTINEL, "800", "80"], ["C2", "300", "1000", "80"]]


def base_csv(**kw):
    return csv_bytes(HEADER, ROWS, **kw)


class RefusalCase(unittest.TestCase):
    def refused(self, code, fn, *args, **kw):
        with self.assertRaises(BlindRefusal) as cm:
            fn(*args, **kw)
        exc = cm.exception
        self.assertEqual(exc.code, code, f"got {exc.code}: {exc.message}")
        for text in (str(exc), exc.message, json.dumps(exc.detail)):
            self.assertNotIn(SENTINEL, text)
        return exc

    def parse(self, raw, md=None):
        return ui.parse_inputs(raw, md if md is not None else nmeta())

    def refused_parse(self, code, raw, md=None):
        return self.refused(code, ui.parse_inputs, raw, md if md is not None else nmeta())


class TargetColumnTests(RefusalCase):
    def test_target_like_headers(self):
        for name, token in (("depth_um", "depth"), ("Width", "width"), ("cap_height", ("cap", "height")),
                            ("d", "d"), ("W", "W"), ("D", "D")):
            with self.subTest(name=name):
                raw = csv_bytes(HEADER + [name], [r + ["5"] for r in ROWS])
                exc = self.refused_parse("INPUTS_TARGET_COLUMN", raw)
                self.assertIn(f"'{name}'", exc.message)
                tokens = token if isinstance(token, tuple) else (token,)
                self.assertTrue(any(f"contains '{t.lower()}'" in exc.message.casefold() for t in tokens),
                                exc.message)

    def test_malformed_second_line_not_reached(self):
        raw = b"condition_id,power_W,speed_mm_s,spot_um,depth_um\nC1,\"unterminated\n"
        self.refused_parse("INPUTS_TARGET_COLUMN", raw)
        raw = b"condition_id,power_W,speed_mm_s,spot_um,depth_um\nC1,1,2\n"
        self.refused_parse("INPUTS_TARGET_COLUMN", raw)

    def test_d_um_not_alias(self):
        for name in ("d_um", "D_um"):
            with self.subTest(name=name):
                raw = csv_bytes(HEADER + [name], [r + ["5"] for r in ROWS])
                with self.assertRaises(BlindRefusal) as cm:
                    self.parse(raw)
                self.assertIn(cm.exception.code, ("INPUTS_TARGET_COLUMN", "INPUTS_UNKNOWN_COLUMN"))
        for aliases in ui.INPUT_ALIASES.values():
            self.assertNotIn("d_um", [a.casefold() for a in aliases])


class HeaderTests(RefusalCase):
    def test_unknown_column(self):
        raw = csv_bytes(HEADER + ["notes"], [r + ["x"] for r in ROWS])
        exc = self.refused_parse("INPUTS_UNKNOWN_COLUMN", raw)
        self.assertIn("'notes'", exc.message)

    def test_column_missing(self):
        raw = csv_bytes(["condition_id", "speed_mm_s", "spot_um"], [["C1", "800", "80"]])
        exc = self.refused_parse("INPUTS_COLUMN_MISSING", raw)
        self.assertIn("power_W", exc.message)

    def test_ambiguous_alias(self):
        raw = csv_bytes(["condition_id", "P", "power_W", "speed_mm_s", "spot_um"],
                        [["C1", SENTINEL, SENTINEL, "800", "80"]])
        exc = self.refused_parse("AMBIGUOUS_ALIAS", raw)
        self.assertIn("'P'", exc.message)
        self.assertIn("'power_W'", exc.message)

    def test_alias_echo(self):
        raw = csv_bytes(["condition_id", "laser_power_W", "speed_mm_s", "spot_um"], [["C1", "300", "800", "80"]])
        parsed = self.parse(raw)
        echo = [e for e in parsed["aliases"] if e["header"] == "laser_power_W"]
        self.assertEqual(len(echo), 1)
        self.assertEqual(echo[0]["canonical"], "power_W")
        self.assertEqual(parsed["rows"][0]["P_W"], 300.0)

    def test_unit_unknown(self):
        raw = csv_bytes(["condition_id", "power_W", "Speed (km/h)", "spot_um"], [["C1", "300", "1", "80"]])
        exc = self.refused_parse("HEADER_UNIT_UNKNOWN", raw)
        self.assertIn("km/h", exc.message)
        self.assertIn("Speed (km/h)", exc.message)

    def test_unit_conversion(self):
        raw = csv_bytes(["condition_id", "Power (kW)", "Speed (m/s)", "spot_um"], [["C1", "0.2", "0.8", "80"]])
        parsed = self.parse(raw)
        row = parsed["rows"][0]
        self.assertAlmostEqual(row["P_W"], 200.0)
        self.assertAlmostEqual(row["v_mm_s"], 800.0)
        self.assertEqual(row["conversion"]["speedFactor"], 1000.0)
        self.assertEqual(row["conversion"]["powerFactor"], 1000.0)
        by_header = {e["header"]: e for e in parsed["aliases"]}
        self.assertEqual(by_header["Speed (m/s)"]["factor"], 1000.0)
        self.assertEqual(by_header["Power (kW)"]["factor"], 1000.0)

    def test_unitless_speed_label(self):
        raw = csv_bytes(["condition_id", "power_W", "speed", "spot_um"], [["C1", "300", "800", "80"]])
        parsed = self.parse(raw)
        self.assertIn("unit not stated, read as mm/s", parsed["labels"])
        raw = csv_bytes(["condition_id", "power_W", "Speed (mm/s)", "spot_um"], [["C1", "300", "800", "80"]])
        self.assertEqual(self.parse(raw)["labels"], [])

    def test_header_dialect_before_unknown_column(self):
        raw = b"condition_id;power_W;speed_mm_s;notes\r\nC1;300;800;x\r\n"
        exc = self.refused_parse("DIALECT_MISMATCH", raw)
        self.assertIn("header", exc.message)
        self.assertIn("semicolons", exc.message)
        raw = b"condition_id,power_W,speed_mm_s,spot_um\nC1,300,800,80\n"
        exc = self.refused_parse("DIALECT_MISMATCH", raw, nmeta(csvDialect="semicolon-dot"))
        self.assertIn("header", exc.message)

    def test_decimal_comma_cell_under_comma_dot(self):
        raw = b"condition_id,power_W,speed_mm_s,spot_um\nC1,\"12,5\",800,80\n"
        exc = self.refused_parse("DIALECT_MISMATCH", raw)
        self.assertEqual(exc.detail["row"], 2)
        self.assertNotIn("12,5", exc.message)

    def test_missing_key_columns(self):
        raw = csv_bytes(["power_W", "speed_mm_s", "spot_um"], [["300", "800", "80"]])
        self.refused_parse("INPUTS_COLUMN_MISSING", raw)


class FileLevelTests(RefusalCase):
    def test_three_dialects(self):
        want = [(777.123, 800.0), (300.0, 1000.0)]
        for dialect, sep, dec in (("comma-dot", ",", "."), ("semicolon-dot", ";", "."), ("semicolon-comma", ";", ",")):
            with self.subTest(dialect=dialect):
                rows = [["C1", SENTINEL.replace(".", dec), "800", "80"], ["C2", "300", "1000", "80"]]
                parsed = self.parse(csv_bytes(HEADER, rows, sep=sep), nmeta(csvDialect=dialect))
                self.assertEqual([(r["P_W"], r["v_mm_s"]) for r in parsed["rows"]], want)
                self.assertEqual(parsed["dialect"], dialect)

    def test_bom_and_crlf(self):
        parsed = self.parse(base_csv(eol="\r\n", bom=True))
        self.assertEqual(parsed["header"][0], "condition_id")
        self.assertEqual(len(parsed["rows"]), 2)
        self.assertEqual([r["ordinal"] for r in parsed["rows"]], [2, 3])

    def test_not_utf8(self):
        self.refused_parse("FILE_NOT_CSV_UTF8", b"PK\x03\x04" + b"\x00" * 30)
        self.refused_parse("FILE_NOT_CSV_UTF8", b"condition_id,power_W\nC1,\xff\xfe\n")

    def test_size_cap_bytes(self):
        raw = b"a" * (256 * 1024 + 1)
        b64 = base64.b64encode(raw).decode()
        self.refused("SIZE_CAP", ui.decode_upload, b64, "inputsCsvBase64")
        self.refused("SIZE_CAP", ui.decode_upload, "A" * 350_001, "inputsCsvBase64")
        self.refused("SIZE_CAP", ui.parse_inputs, raw, nmeta())
        ok = ui.decode_upload(base64.b64encode(b"abc").decode(), "inputsCsvBase64")
        self.assertEqual(ok, b"abc")
        self.refused("FILE_NOT_CSV_UTF8", ui.decode_upload, "***not base64***", "inputsCsvBase64")

    def test_size_cap_rows(self):
        rows = [[f"C{i}", "300", "800", "80"] for i in range(2001)]
        self.refused_parse("SIZE_CAP", csv_bytes(HEADER, rows))

    def test_size_cap_conditions(self):
        rows = [[f"C{i}", str(100 + i), "800", "80"] for i in range(49)]
        self.refused_parse("SIZE_CAP", csv_bytes(HEADER, rows))
        parsed = self.parse(csv_bytes(HEADER, rows[:48]))
        self.assertEqual(parsed["counts"]["conditions"], 48)

    def test_file_empty(self):
        self.refused_parse("FILE_EMPTY", csv_bytes(HEADER, []))

    def test_csv_malformed_row_number(self):
        raw = csv_bytes(HEADER, [["C1", SENTINEL, "800", "80"], ["C2", "300", "1000"], ["C3", "300", "1000", "80"]])
        exc = self.refused_parse("CSV_MALFORMED", raw)
        self.assertEqual(exc.detail["row"], 3)
        self.assertIn("Row 3", exc.message)
        exc = self.refused_parse("CSV_MALFORMED", csv_bytes(HEADER, [["C1", "300", "800", "80", "1"]]))
        self.assertEqual(exc.detail["row"], 2)

    def test_number_invalid(self):
        raw = b"condition_id,power_W,speed_mm_s,spot_um\nC1,\"1,234.5\",800,80\n"
        with self.assertRaises(BlindRefusal) as cm:
            self.parse(raw)
        self.assertIn(cm.exception.code, ("DIALECT_MISMATCH", "NUMBER_INVALID"))
        raw = csv_bytes(HEADER, [["C1", "777.123x", "800", "80"]])
        exc = self.refused_parse("NUMBER_INVALID", raw)
        self.assertEqual(exc.detail, {"row": 2, "column": "power_W"})
        raw = csv_bytes(HEADER, [["C1", SENTINEL, "12.5x7", "80"]])
        self.refused_parse("NUMBER_INVALID", raw)
        for bad in ("-5", "nan", "inf", "1e3", ""):
            with self.subTest(bad=bad):
                self.refused_parse("NUMBER_INVALID", csv_bytes(HEADER, [["C1", SENTINEL, bad, "80"]]))

    def test_out_of_range_with_hint(self):
        exc = self.refused_parse("OUT_OF_RANGE", csv_bytes(HEADER, [["C1", SENTINEL, "0.8", "80"]]))
        self.assertIn("m/s", exc.message)
        self.assertEqual(exc.detail["column"], "speed_mm_s")
        self.refused_parse("OUT_OF_RANGE", csv_bytes(HEADER, [["C1", "5000", "800", "80"]]))
        self.refused_parse("OUT_OF_RANGE", csv_bytes(HEADER, [["C1", SENTINEL, "800", "5"]]))

    def test_id_invalid(self):
        raw = csv_bytes(HEADER, [["=cmd", SENTINEL, "800", "80"]])
        exc = self.refused_parse("ID_INVALID", raw)
        self.assertNotIn("=cmd", exc.message)
        self.refused_parse("ID_INVALID", csv_bytes(HEADER, [["C 1", SENTINEL, "800", "80"]]))
        self.refused_parse("ID_INVALID", csv_bytes(HEADER, [["", SENTINEL, "800", "80"]]))
        self.refused_parse("ID_INVALID", csv_bytes(HEADER, [["x" * 65, SENTINEL, "800", "80"]]))

    def test_synthetic_example_row(self):
        raw = csv_bytes(HEADER, [["C1", SENTINEL, "800", "80"], ["synthetic-example-2", "300", "1000", "80"]])
        exc = self.refused_parse("SYNTHETIC_EXAMPLE_ROW", raw)
        self.assertEqual(exc.detail["row"], 3)

    def test_file_name(self):
        for bad in (".hidden.csv", "=x.csv", "+a.csv", "-a.csv", "@a.csv", "a/b.csv", "", "x" * 121, None):
            with self.subTest(bad=bad):
                self.refused("FILE_NAME_INVALID", ui.check_file_name, bad, "inputsFileName")
        self.assertEqual(ui.check_file_name("My inputs (v2).csv", "inputsFileName"), "My inputs (v2).csv")


class StructureTests(RefusalCase):
    def test_duplicate_key(self):
        hdr = ["condition_id", "track_id", "power_W", "speed_mm_s", "spot_um"]
        raw = csv_bytes(hdr, [["C1", "T1", SENTINEL, "800", "80"], ["C1", "T1", SENTINEL, "800", "80"]])
        exc = self.refused_parse("DUPLICATE_KEY", raw, nmeta(replication={"tracksPerCondition": 2}))
        self.assertEqual(exc.detail["rows"], [2, 3])

    def test_condition_inconsistent(self):
        raw = csv_bytes(HEADER, [["C1", SENTINEL, "800", "80"], ["C1", "301", "800", "80"]])
        md = nmeta(replication={"rowsAreSeparateTracks": True, "tracksPerCondition": 2})
        exc = self.refused_parse("CONDITION_INCONSISTENT", raw, md)
        self.assertIn("C1", exc.message)

    def test_condition_duplicate_setting(self):
        raw = csv_bytes(HEADER, [["C1", SENTINEL, "800", "80"], ["C2", SENTINEL, "800", "80"]])
        exc = self.refused_parse("CONDITION_DUPLICATE_SETTING", raw)
        self.assertIn("C1", exc.message)
        self.assertIn("C2", exc.message)

    def test_section_without_track(self):
        raw = csv_bytes(["condition_id", "section_id", "power_W", "speed_mm_s", "spot_um"],
                        [["C1", "S1", SENTINEL, "800", "80"]])
        self.refused_parse("SECTION_WITHOUT_TRACK", raw)

    def test_repeated_rows_without_track(self):
        raw = csv_bytes(HEADER, [["C1", SENTINEL, "800", "80"], ["C1", SENTINEL, "800", "80"]])
        self.refused_parse("REPEATED_ROWS_NO_TRACK", raw, nmeta(replication={"tracksPerCondition": 2}))
        parsed = self.parse(raw, nmeta(replication={"tracksPerCondition": 2, "rowsAreSeparateTracks": True}))
        self.assertEqual(parsed["conditions"][0]["nTracks"], 2)
        self.assertEqual(parsed["counts"]["tracks"], 2)

    def test_replication_mismatch(self):
        exc = self.refused_parse("REPLICATION_MISMATCH", base_csv(), nmeta(replication={"tracksPerCondition": 2}))
        self.assertIn("C1", exc.message)
        self.assertIn("C2", exc.message)
        self.refused_parse("REPLICATION_MISMATCH", base_csv(), nmeta(replication={"sectionsPerTrack": 3}))

    def test_derived_conditions_from_track_ids(self):
        hdr = ["track_id", "power_W", "speed_mm_s", "spot_um"]
        rows = [["T1", SENTINEL, "800", "80"], ["T2", SENTINEL, "800", "80"],
                ["T3", "300", "1000", "80"], ["T4", "300", "1000", "80"]]
        parsed = self.parse(csv_bytes(hdr, rows), nmeta(replication={"tracksPerCondition": 2}))
        self.assertEqual(parsed["keyColumns"], ["track_id"])
        self.assertEqual([c["condition"] for c in parsed["conditions"]], ["C001", "C002"])
        self.assertEqual([r["condition"] for r in parsed["rows"]], ["C001", "C001", "C002", "C002"])

    def test_track_with_two_settings(self):
        hdr = ["track_id", "power_W", "speed_mm_s", "spot_um"]
        raw = csv_bytes(hdr, [["T1", SENTINEL, "800", "80"], ["T1", "300", "800", "80"]])
        self.refused_parse("CONDITION_INCONSISTENT", raw)

    def test_key_columns_with_sections(self):
        hdr = ["condition_id", "track_id", "section_id", "power_W", "speed_mm_s", "spot_um"]
        rows = [["C1", "T1", "S1", SENTINEL, "800", "80"], ["C1", "T1", "S2", SENTINEL, "800", "80"]]
        parsed = self.parse(csv_bytes(hdr, rows), nmeta(replication={"sectionsPerTrack": 2}))
        self.assertEqual(parsed["keyColumns"], ["condition_id", "track_id", "section_id"])
        self.assertEqual(parsed["counts"]["sections"], 2)


class BeamAndMetadataTests(RefusalCase):
    def test_beam_missing(self):
        raw = csv_bytes(["condition_id", "power_W", "speed_mm_s"], [["C1", SENTINEL, "800"]])
        self.refused_parse("BEAM_MISSING", raw)
        parsed = self.parse(raw, nmeta(beam={"diameter_um": 90.0}))
        self.assertEqual(parsed["rows"][0]["d_1e2_um"], 90.0)

    def test_radius_doubles_before_conversion(self):
        raw = csv_bytes(HEADER, [["C1", SENTINEL, "800", "40"]])
        row = self.parse(raw, nmeta(beam={"quantity": "radius"}))["rows"][0]
        self.assertEqual(row["d_declared_um"], 40.0)
        self.assertEqual(row["d_1e2_um"], 80.0)
        self.assertEqual(row["conversion"]["quantityFactor"], 2.0)
        row = self.parse(raw, nmeta(beam={"quantity": "radius", "definition": "FWHM"}))["rows"][0]
        self.assertAlmostEqual(row["d_1e2_um"], 80.0 / stats.FWHM_FACTOR)

    def test_fwhm_conversion(self):
        raw = csv_bytes(HEADER, [["C1", SENTINEL, "800", "50"]])
        row = self.parse(raw, nmeta(beam={"definition": "FWHM"}))["rows"][0]
        self.assertAlmostEqual(row["d_1e2_um"], 50.0 / stats.FWHM_FACTOR)
        self.assertAlmostEqual(row["conversion"]["definitionFactor"], 1.0 / stats.FWHM_FACTOR)
        self.assertEqual(row["d_declared_um"], 50.0)

    def test_preheat_missing(self):
        raw = meta()
        del raw["preheat_C"]
        self.refused("PREHEAT_MISSING", ui.normalize_metadata, raw)
        self.refused("PREHEAT_MISSING", ui.normalize_metadata, meta(preheat_C=None))

    def test_wavelength_out_of_scope(self):
        for nm in (532, 1029.9, 1100.1, 777.123):
            with self.subTest(nm=nm):
                self.refused("WAVELENGTH_OUT_OF_SCOPE", ui.normalize_metadata, meta(wavelength_nm=nm))
        nmeta(wavelength_nm=1030)
        nmeta(wavelength_nm=1100)

    def test_metadata_unknown_key(self):
        exc = self.refused("METADATA_FIELD", ui.normalize_metadata, meta(notes="hello"))
        self.assertIn("notes", exc.message)
        raw = meta()
        raw["beam"]["extra"] = 1
        exc = self.refused("METADATA_FIELD", ui.normalize_metadata, raw)
        self.assertIn("beam.extra", exc.message)

    def test_metadata_missing_required(self):
        for key in ("mode", "alloy", "reduction", "wavelength_nm"):
            with self.subTest(key=key):
                raw = meta()
                del raw[key]
                exc = self.refused("METADATA_FIELD", ui.normalize_metadata, raw)
                self.assertIn("Missing required field", exc.message)
                self.assertIn(key, exc.message)
        raw = meta()
        del raw["beam"]["quantity"]
        exc = self.refused("METADATA_FIELD", ui.normalize_metadata, raw)
        self.assertIn("beam.quantity", exc.message)
        raw = meta()
        del raw["independence"]["predictionsViewedBeforeFreeze"]
        self.refused("METADATA_FIELD", ui.normalize_metadata, raw)

    def test_block_label_rules(self):
        for bad in ("=cmd", "+x", "-x", "@x", "a\tb", "a\nb", "", "x" * 81, "a;b", "a,b"):
            with self.subTest(bad=bad):
                exc = self.refused("METADATA_FIELD", ui.normalize_metadata, meta(blockLabel=bad))
                self.assertIn("blockLabel", exc.message)
        self.assertEqual(nmeta(blockLabel="Plate A (run 2)/b.1")["blockLabel"], "Plate A (run 2)/b.1")

    def test_bool_as_string_refused(self):
        for override in ({"power": {"meterNamed": "false"}}, {"substrate": {"amSubstrate": "false"}},
                         {"replication": {"rowsAreSeparateTracks": "false"}},
                         {"independence": {"usedForMachineCalibration": "false"}},
                         {"power": {"meterNamed": 0}}):
            with self.subTest(override=override):
                self.refused("METADATA_FIELD", ui.normalize_metadata, meta(**override))

    def test_published_in_pre_measurement(self):
        exc = self.refused("METADATA_FIELD", ui.normalize_metadata,
                           meta(independence={"dataPreviouslyPublished": "yes"}))
        self.assertIn("Published data cannot be a pre-measurement test", exc.message)
        md = nmeta(mode="post-measurement", independence={"dataPreviouslyPublished": "yes"})
        self.assertEqual(md["mode"], "post-measurement")

    def test_other_metadata_rules(self):
        self.refused("METADATA_FIELD", ui.normalize_metadata, meta(mode="whenever"))
        self.refused("METADATA_FIELD", ui.normalize_metadata, meta(schema="other"))
        self.refused("METADATA_FIELD", ui.normalize_metadata, meta(wavelength_nm=True))
        self.refused("METADATA_FIELD", ui.normalize_metadata, meta(substrate={"kind": "powder-layer"}))
        self.refused("METADATA_FIELD", ui.normalize_metadata, meta(targetCommitment={"sha256": "a" * 64}))
        self.refused("METADATA_FIELD", ui.normalize_metadata, meta(substrate={"alsi10mgState": "as-built"}))
        self.assertEqual(nmeta(mode="post-measurement", targetCommitment={"sha256": "a" * 64})["targetCommitment"],
                         {"sha256": "a" * 64})
        self.assertEqual(nmeta(alloy="AlSi10Mg", substrate={"alsi10mgState": "as-built"})
                         ["substrate"]["alsi10mgState"], "as-built")
        self.assertEqual(nmeta(alloy="AlSi10Mg")["substrate"]["alsi10mgState"], "unstated")

    def test_defaults_are_conservative(self):
        raw = meta()
        for k in ("depthDatum", "crossSectionLocation", "atmosphere", "csvDialect", "targetCommitment", "preheatBasis",
                  "measurementMethod", "depthBoundary", "quantity"):
            raw.pop(k)
        for k in ("definition", "basis", "profile"):
            raw["beam"].pop(k)
        raw["power"].pop("basis")
        raw["depthUncertainty"] = {}
        md = ui.normalize_metadata(raw)
        self.assertEqual(md["depthDatum"], "unresolved")
        self.assertEqual(md["crossSectionLocation"], "unstated")
        self.assertEqual(md["atmosphere"], "unstated")
        self.assertEqual(md["csvDialect"], "comma-dot")
        self.assertEqual(md["beam"]["definition"], "unstated")
        self.assertEqual(md["beam"]["profile"], "unknown")
        self.assertEqual(md["power"]["basis"], "commanded")
        self.assertEqual(md["depthUncertainty"]["basis"], "not-released")


class GradesIssuesLabelsTests(unittest.TestCase):
    def test_grades(self):
        md = nmeta(power={"basis": "measured-at-workpiece", "meterNamed": True, "uncertaintyReleased": True},
                   beam={"basis": "measured-work-plane", "definition": "1/e2", "uncertaintyReleased": True})
        self.assertEqual(ui.grades(md), {"power": "A", "beam": "A", "block": "A"})
        md = nmeta(power={"basis": "measured-at-workpiece", "meterNamed": True, "uncertaintyReleased": True},
                   beam={"basis": "measured-work-plane", "definition": "unstated", "uncertaintyReleased": True})
        g = ui.grades(md)
        self.assertEqual((g["power"], g["beam"], g["block"]), ("A", "C", "C"))
        g = ui.grades(nmeta())
        self.assertEqual((g["power"], g["beam"], g["block"]), ("C", "C", "C"))
        g = ui.grades(nmeta(power={"basis": "measured-elsewhere"}, beam={"basis": "measured-other-plane"}))
        self.assertEqual((g["power"], g["beam"], g["block"]), ("B", "B", "B"))

    def test_clean_block_has_no_issues(self):
        self.assertEqual(ui.block_issues(nmeta()), [])

    def test_beam_profile_issue_vs_label(self):
        self.assertIn("BEAM_PROFILE_NOT_GAUSSIAN", ui.block_issues(nmeta(beam={"profile": "ring"})))
        self.assertIn("BEAM_PROFILE_NOT_GAUSSIAN", ui.block_issues(nmeta(beam={"profile": "top-hat"})))
        unknown = nmeta(beam={"profile": "unknown"})
        self.assertEqual(ui.block_issues(unknown), [])
        label = "beam profile not stated (Gaussian assumed by the served model)"
        self.assertIn(label, ui.labels_from_metadata(unknown))
        self.assertNotIn(label, ui.labels_from_metadata(nmeta()))

    def test_block_issue_list(self):
        md = nmeta(depthDatum="powder-top", reduction="maximum-only", atmosphere="unstated",
                   depthBoundary="unetched-contrast", crossSectionLocation="near-track-start-or-end",
                   substrate={"thickness_mm": None, "surfacePreparation": "unstated"},
                   independence={"dataPreviouslyPublished": "unknown"})
        self.assertEqual(set(ui.block_issues(md)), {
            "DATUM_NOT_ORIGINAL_SURFACE", "REDUCTION_UNUSABLE", "PLATE_THICKNESS_NOT_RELEASED",
            "ATMOSPHERE_UNSTATED", "SURFACE_PREPARATION_UNSTATED", "INDEPENDENCE_NOT_ESTABLISHED",
            "BOUNDARY_NOT_ETCHED", "LOCATION_NEAR_ENDS_OR_UNSTATED"})
        self.assertIn("REDUCTION_UNUSABLE", ui.block_issues(nmeta(reduction="single-selected-section")))
        self.assertIn("LOCATION_NEAR_ENDS_OR_UNSTATED", ui.block_issues(nmeta(crossSectionLocation="unstated")))
        self.assertNotIn("LOCATION_NEAR_ENDS_OR_UNSTATED",
                         ui.block_issues(nmeta(crossSectionLocation="several-locations")))

    def test_sections_without_track_issue(self):
        md = nmeta()
        no_track = ui.parse_inputs(base_csv(), md)
        self.assertIn("SECTIONS_WITHOUT_TRACK", ui.block_issues(md, no_track))
        hdr = ["condition_id", "track_id", "power_W", "speed_mm_s", "spot_um"]
        with_track = ui.parse_inputs(csv_bytes(hdr, [["C1", "T1", "300", "800", "80"]]), md)
        self.assertNotIn("SECTIONS_WITHOUT_TRACK", ui.block_issues(md, with_track))

    def test_labels(self):
        labels = ui.labels_from_metadata(nmeta(beam={"definition": "unstated", "quantity": "radius"},
                                               power={"u_k1_rel": 0.08}, preheatBasis="nominal-ambient"))
        for want in ("beam definition unstated (read as 1/e2)", "beam size declared as radius (doubled)",
                     "declared power uncertainty exceeds the 5 % fragility band",
                     "plate temperature is nominal ambient", "S and O flagged missing",
                     "bare plate: layer argument 40 um passed", "research arm not requested"):
            self.assertIn(want, labels)
        self.assertTrue(any(x.startswith("u_m assumed") for x in labels))
        clean = ui.labels_from_metadata(nmeta(
            beam={"definition": "1/e2"}, depthUncertainty={"basis": "block", "u_um": 4.0},
            chemistry={"basis": "certified-heat-analysis", "sulfur_ppm": 10, "oxygen_ppm": 900}))
        self.assertIn("S and O certified", clean)
        self.assertFalse(any(x.startswith("u_m assumed") for x in clean))
        self.assertNotIn("beam definition unstated (read as 1/e2)", clean)
        al = ui.labels_from_metadata(nmeta(alloy="AlSi10Mg"))
        self.assertIn("plate state differs from the as-built property convention", al)
        self.assertIn("thresholds reused for 316L (registered for Ti-6Al-4V and AlSi10Mg)",
                      ui.labels_from_metadata(nmeta(alloy="316L")))
        self.assertIn("leverage not evaluable (IN625)", ui.labels_from_metadata(nmeta(alloy="IN625")))
        self.assertFalse(any("thresholds reused" in x for x in ui.labels_from_metadata(nmeta(alloy="Ti-6Al-4V"))))


class DesignChecksTests(unittest.TestCase):
    @staticmethod
    def served_index(alloy, p, v, d, t0):
        return p / v * 10.0        # synthetic stand-in for the analytic served index

    def _parsed(self, n, tracks=1):
        hdr = ["condition_id", "track_id", "power_W", "speed_mm_s", "spot_um"]
        rows = [[f"C{i}", f"T{i}_{j}", str(100 + 10 * i), "800", "80"] for i in range(n) for j in range(tracks)]
        md = nmeta(replication={"tracksPerCondition": tracks})
        return md, ui.parse_inputs(csv_bytes(hdr, rows), md)

    @staticmethod
    def _keys(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                yield str(k)
                yield from DesignChecksTests._keys(v)
        elif isinstance(obj, (list, tuple)):
            for v in obj:
                yield from DesignChecksTests._keys(v)

    def test_counts_only(self):
        md, parsed = self._parsed(14)
        checks = ui.design_checks(md, parsed, self.served_index)
        self.assertEqual(checks["nConditions"], 14)
        self.assertTrue(checks["nMinMet"])
        for k in self._keys(checks):
            self.assertNotRegex(k.lower(), r"depth|value_um|width|pred")
        self.assertEqual(set(checks["leverage"]), {"cut", "nBelow", "nAtOrAbove20", "ok"})
        for v in checks["leverage"].values():
            self.assertTrue(v is None or isinstance(v, (int, float, bool, str)))

    def test_small_design_and_leverage_counts(self):
        md, parsed = self._parsed(5)
        checks = ui.design_checks(md, parsed, self.served_index)
        self.assertFalse(checks["nMinMet"])
        self.assertLessEqual(checks["leverage"]["nBelow"] + checks["leverage"]["nAtOrAbove20"], 5)
        self.assertFalse(checks["resolution"]["evaluable"])
        self.assertIn("u_m", checks["uMNote"])
        status, acks = ui.best_reachable(md, ui.block_issues(md, parsed), checks, [])
        self.assertEqual(status["status"], "inconclusive")
        self.assertEqual(acks, ["predeterminedInconclusive"])

    def test_in625_leverage_not_evaluable_but_scored(self):
        md = nmeta(alloy="IN625")
        _md, parsed = self._parsed(14)
        checks = ui.design_checks(md, parsed, self.served_index)
        self.assertEqual(checks["leverage"]["ok"], "not evaluable")
        self.assertIsNone(checks["leverage"]["cut"])
        status, _acks = ui.best_reachable(md, [], checks, [])
        self.assertEqual(status["status"], "inconclusive")
        self.assertTrue(any("leverage not evaluable for IN625" in r for r in status["reasons"]))

    def test_powder_layer_and_exposure(self):
        md = nmeta(substrate={"kind": "powder-layer", "layerThickness_um": 40.0})
        _m, parsed = self._parsed(3)
        checks = ui.design_checks(md, parsed, self.served_index)
        status, acks = ui.best_reachable(md, [], checks, [])
        self.assertEqual((status["status"], acks), ("descriptive-not-scored", ["powderLayerDescriptive"]))
        status, acks = ui.best_reachable(md, [], checks, ["x"])
        self.assertEqual((status["status"], acks), ("descriptive-exposed", ["exposedDescriptive"]))


if __name__ == "__main__":
    unittest.main()
