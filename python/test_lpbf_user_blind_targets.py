"""Scoring-phase intake tests for the user blind test targets file (spec 4.4, 6.1, 11.1 item 4).

All data is synthetic and built here. The freeze dict is built from `parse_inputs` output as the store does:
{"metadata", "keyColumns", "rows"}. The sentinel 777.123 is a depth or input value that must never appear in any
refusal text or detail.
"""
from __future__ import annotations

import json
import unittest

import lpbf_user_blind_inputs as ui
import lpbf_user_blind_targets as ut
from lpbf_user_blind_protocol import BlindRefusal
from test_lpbf_user_blind_inputs import csv_bytes, meta

SENTINEL = "777.123"
KEYS = ["condition_id", "track_id", "section_id"]
IN_HEADER = KEYS + ["power_W", "speed_mm_s", "spot_um"]
# Two conditions, two tracks each, two sections per track: eight frozen rows (synthetic settings).
IN_ROWS = []
for _c, _p, _v in (("C1", SENTINEL, "800"), ("C2", "300", "1000")):
    for _t in ("1", "2"):
        for _s in ("S1", "S2"):
            IN_ROWS.append([_c, f"T{_c[1]}{_t}", _s, _p, _v, "80"])


def make_freeze(basis="not-released", u_um=None, dialect="comma-dot"):
    md = ui.normalize_metadata(meta(replication={"tracksPerCondition": 2, "sectionsPerTrack": 2},
                                    depthUncertainty={"basis": basis, "u_um": u_um}, csvDialect=dialect))
    sep = "," if dialect == "comma-dot" else ";"
    rows = [[c.replace(".", ",") for c in r] for r in IN_ROWS] if dialect == "semicolon-comma" else IN_ROWS
    parsed = ui.parse_inputs(csv_bytes(IN_HEADER, rows, sep=sep), md)
    return {"metadata": md, "keyColumns": parsed["keyColumns"], "rows": parsed["rows"]}


class Case(unittest.TestCase):
    freeze = None

    @classmethod
    def setUpClass(cls):
        cls.freeze = make_freeze()

    def rows(self, **over):
        """Target rows as dicts keyed like the file; the first row carries the sentinel depth."""
        out = []
        for i, r in enumerate(IN_ROWS):
            out.append({"condition_id": r[0], "track_id": r[1], "section_id": r[2],
                        "depth_um": SENTINEL if i == 0 else str(100 + i), "depth_status": ""})
        return out

    def render(self, rows, header=None, sep=","):
        header = header or list(rows[0].keys())
        return csv_bytes(header, [[r.get(h, "") for h in header] for r in rows], sep=sep)

    def parse(self, raw, freeze=None):
        return ut.parse_targets(raw, freeze or self.freeze)

    def refused(self, code, raw, freeze=None):
        with self.assertRaises(BlindRefusal) as cm:
            ut.parse_targets(raw, freeze or self.freeze)
        exc = cm.exception
        self.assertEqual(exc.code, code, f"got {exc.code}: {exc.message}")
        for text in (str(exc), exc.message, json.dumps(exc.detail)):
            self.assertNotIn(SENTINEL, text)
        return exc


class KeyTests(Case):
    def test_happy_path(self):
        res = self.parse(self.render(self.rows()))
        self.assertEqual(len(res["byOrdinal"]), 8)
        first = res["byOrdinal"][self.freeze["rows"][0]["ordinal"]]
        self.assertEqual((first["status"], first["depth_um"], first["row"]), ("measured", 777.123, 2))
        self.assertEqual(res["ignored"], [])

    def test_missing_extra_duplicate(self):
        rows = self.rows()
        exc = self.refused("TARGETS_KEYS_MISMATCH", self.render(rows[:-1]))
        self.assertEqual(exc.detail, {"missing": 1, "extra": 0, "duplicate": 0})
        extra = dict(rows[0], track_id="T99")
        exc = self.refused("TARGETS_KEYS_MISMATCH", self.render(rows + [extra]))
        self.assertEqual(exc.detail, {"missing": 0, "extra": 1, "duplicate": 0})
        exc = self.refused("TARGETS_KEYS_MISMATCH", self.render(rows + [dict(rows[3])]))
        self.assertEqual(exc.detail, {"missing": 0, "extra": 0, "duplicate": 1})
        exc = self.refused("TARGETS_KEYS_MISMATCH", self.render(rows[1:] + [dict(rows[2]), dict(rows[1], track_id="T98")]))
        self.assertEqual(exc.detail, {"missing": 1, "extra": 1, "duplicate": 1})
        self.assertIn("1 missing, 1 extra, 1 duplicate", exc.message)

    def test_column_missing(self):
        rows = self.rows()
        self.refused("TARGETS_COLUMN_MISSING", self.render(rows, header=KEYS))                   # no depth_um
        self.refused("TARGETS_COLUMN_MISSING", self.render(rows, header=["condition_id", "section_id", "depth_um"]))

    def test_id_rules(self):
        rows = self.rows()
        rows[1]["condition_id"] = "=cmd"
        self.refused("ID_INVALID", self.render(rows))
        rows = self.rows()
        rows[1]["track_id"] = "SYNTHETIC-EXAMPLE-1"
        exc = self.refused("SYNTHETIC_EXAMPLE_ROW", self.render(rows))
        self.assertEqual(exc.detail["row"], 3)

    def test_file_level(self):
        self.refused("FILE_EMPTY", csv_bytes(KEYS + ["depth_um"], []))
        self.refused("FILE_NOT_CSV_UTF8", b"PK\x03\x04" + b"\x00" * 20)
        self.refused("SIZE_CAP", b"a" * (256 * 1024 + 1))
        exc = self.refused("CSV_MALFORMED", csv_bytes(KEYS + ["depth_um"], [["C1", "T11", "S1", "5"], ["C1", "T11"]]))
        self.assertEqual(exc.detail["row"], 3)
        self.refused("DIALECT_MISMATCH", b"condition_id;track_id;section_id;depth_um\nC1;T11;S1;5\n")

    def test_dialects(self):
        freeze = make_freeze(dialect="semicolon-comma")
        rows = self.rows()
        rows[0]["depth_um"] = "777,123"
        res = ut.parse_targets(self.render(rows, sep=";"), freeze)
        self.assertEqual(res["byOrdinal"][freeze["rows"][0]["ordinal"]]["depth_um"], 777.123)


class HeaderTests(Case):
    def test_unknown_headers_ignored(self):
        rows = self.rows()
        for r in rows:
            r["notes"] = "hello"
            r["cap_um"] = "5"
        res = self.parse(self.render(rows))
        self.assertEqual(res["ignored"], ["notes", "cap_um"])

    def test_aliases(self):
        rows = self.rows()
        for r in rows:
            r["Depth (um)"] = r.pop("depth_um")
        res = self.parse(self.render(rows))
        self.assertEqual(res["byOrdinal"][self.freeze["rows"][0]["ordinal"]]["depth_um"], 777.123)
        rows = self.rows()
        for r in rows:
            r["depth"] = r.pop("depth_um")
            r["Width (um)"] = "60"
        res = self.parse(self.render(rows))
        self.assertEqual(res["byOrdinal"][self.freeze["rows"][1]["ordinal"]]["width_um"], 60.0)
        rows = self.rows()
        for r in rows:
            r["D_um"] = r.pop("depth_um")
        self.parse(self.render(rows))

    def test_key_alias_columns(self):
        rows = self.rows()
        for r in rows:
            r["condition"] = r.pop("condition_id")
            r["track"] = r.pop("track_id")
            r["section"] = r.pop("section_id")
        self.assertEqual(len(self.parse(self.render(rows))["byOrdinal"]), 8)

    def test_ambiguous_alias(self):
        rows = self.rows()
        for r in rows:
            r["depth"] = "5"
        self.refused("AMBIGUOUS_ALIAS", self.render(rows))


class StatusAndDepthTests(Case):
    def test_status_unknown(self):
        rows = self.rows()
        rows[2]["depth_status"] = "broken"
        exc = self.refused("TARGET_STATUS_UNKNOWN", self.render(rows))
        self.assertEqual(exc.detail["row"], 4)

    def test_status_words_case_and_blank(self):
        rows = self.rows()
        rows[2]["depth_status"] = "MEASURED"
        rows[3]["depth_status"] = "measured"
        self.parse(self.render(rows))

    def test_measured_needs_positive_depth(self):
        rows = self.rows()
        rows[1]["depth_um"] = ""
        exc = self.refused("TARGET_DEPTH_INVALID", self.render(rows))
        self.assertEqual(exc.detail["row"], 3)
        rows = self.rows()
        rows[1]["depth_um"] = "0"
        self.refused("TARGET_DEPTH_INVALID", self.render(rows))
        rows = self.rows()
        rows[1]["depth_um"] = "0.0"
        rows[1]["depth_status"] = "measured"
        self.refused("TARGET_DEPTH_INVALID", self.render(rows))

    def test_lost_row_with_depth_conflicts(self):
        for status in ("specimen-lost", "section-unreadable", "not-measured", "track-not-formed"):
            with self.subTest(status=status):
                rows = self.rows()
                rows[2]["depth_status"] = status
                rows[2]["depth_um"] = SENTINEL
                exc = self.refused("TARGET_STATUS_CONFLICT", self.render(rows))
                self.assertEqual(exc.detail["row"], 4)

    def test_loss_statuses_accepted_with_blank_depth(self):
        rows = self.rows()
        for i, status in ((2, "specimen-lost"), (3, "section-unreadable"), (5, "not-measured")):
            rows[i]["depth_status"] = status
            rows[i]["depth_um"] = ""
        res = self.parse(self.render(rows))
        got = {o: t["status"] for o, t in res["byOrdinal"].items()}
        self.assertEqual(sorted(set(got.values())), ["measured", "not-measured", "section-unreadable",
                                                     "specimen-lost"])
        self.assertTrue(all(t["depth_um"] is None for t in res["byOrdinal"].values() if t["status"] != "measured"))

    def test_track_not_formed_must_cover_track(self):
        rows = self.rows()
        # frozen rows 0 and 1 are the two sections of track T11
        rows[0]["depth_status"], rows[0]["depth_um"] = "track-not-formed", ""
        exc = self.refused("TARGET_STATUS_CONFLICT", self.render(rows))
        self.assertEqual(exc.detail["row"], 3)
        self.assertIn("track-not-formed must cover every section", exc.message)
        rows[1]["depth_status"], rows[1]["depth_um"] = "track-not-formed", ""
        res = self.parse(self.render(rows))
        self.assertEqual(res["byOrdinal"][self.freeze["rows"][0]["ordinal"]]["status"], "track-not-formed")

    def test_number_invalid_without_cell_text(self):
        rows = self.rows()
        rows[0]["depth_um"] = "777.123x"
        exc = self.refused("NUMBER_INVALID", self.render(rows))
        self.assertEqual(exc.detail, {"row": 2, "column": "depth_um"})
        self.assertNotIn("777", exc.message)
        rows = self.rows()
        rows[1]["width_um"] = "12.5x7"
        for r in rows:
            r.setdefault("width_um", "")
        self.refused("NUMBER_INVALID", self.render(rows))
        rows = self.rows()
        rows[0]["depth_um"] = "\"777,123\""
        self.refused("DIALECT_MISMATCH", self.render(rows))


class RangeTests(Case):
    def test_depth_below_range_millimetre_hint(self):
        rows = self.rows()
        rows[1]["depth_um"] = "0.08"
        exc = self.refused("TARGET_OUT_OF_RANGE", self.render(rows))
        self.assertIn("millimetres", exc.message)
        self.assertNotIn("0.08", exc.message)
        self.assertNotIn("0.08", json.dumps(exc.detail))
        self.assertEqual(exc.detail, {"row": 3, "column": "depth_um"})

    def test_depth_above_range_nanometre_hint(self):
        rows = self.rows()
        rows[1]["depth_um"] = "50000"
        exc = self.refused("TARGET_OUT_OF_RANGE", self.render(rows))
        self.assertIn("nanometres", exc.message)
        self.assertNotIn("50000", exc.message)
        self.assertNotIn("50000", json.dumps(exc.detail))

    def test_range_boundaries(self):
        rows = self.rows()
        rows[1]["depth_um"] = "1"
        rows[2]["depth_um"] = "3000"
        self.parse(self.render(rows))
        rows[2]["depth_um"] = "3000.5"
        self.refused("TARGET_OUT_OF_RANGE", self.render(rows))

    def test_width_and_uncertainty_ranges(self):
        rows = self.rows()
        for r in rows:
            r["width_um"] = "60"
        rows[1]["width_um"] = "2"
        exc = self.refused("TARGET_OUT_OF_RANGE", self.render(rows))
        self.assertEqual(exc.detail["column"], "width_um")
        rows[1]["width_um"] = "4000"
        self.refused("TARGET_OUT_OF_RANGE", self.render(rows))
        rows = self.rows()
        for r in rows:
            r["depth_u_um"] = "5"
        rows[1]["depth_u_um"] = "500"          # not below the row's depth
        exc = self.refused("TARGET_OUT_OF_RANGE", self.render(rows))
        self.assertEqual(exc.detail["column"], "depth_u_um")


class UncertaintyTests(Case):
    def test_per_row_missing(self):
        freeze = make_freeze(basis="per-row")
        rows = self.rows()
        for r in rows:
            r["depth_u_um"] = "5"
        rows[3]["depth_u_um"] = ""
        exc = self.refused("U_PER_ROW_MISSING", self.render(rows), freeze)
        self.assertEqual(exc.detail["row"], 5)
        # without the per-row basis a blank uncertainty is fine
        self.parse(self.render(rows))

    def test_per_row_varies_within_condition(self):
        freeze = make_freeze(basis="per-row")
        rows = self.rows()
        for i, r in enumerate(rows):
            r["depth_u_um"] = "5" if i < 4 else "6"          # C1 rows 0..3 constant, C2 rows 4..7 constant
        res = ut.parse_targets(self.render(rows), freeze)
        self.assertEqual(res["byOrdinal"][freeze["rows"][0]["ordinal"]]["u_um"], 5.0)
        rows[1]["depth_u_um"] = "5.5"
        exc = self.refused("U_PER_ROW_VARIES", self.render(rows), freeze)
        self.assertIn("C1", exc.message)

    def test_u_ignored_on_lost_rows_for_constancy(self):
        freeze = make_freeze(basis="per-row")
        rows = self.rows()
        for r in rows:
            r["depth_u_um"] = "5"
        rows[2]["depth_status"], rows[2]["depth_um"], rows[2]["depth_u_um"] = "specimen-lost", "", ""
        res = ut.parse_targets(self.render(rows), freeze)
        self.assertIsNone(res["byOrdinal"][freeze["rows"][2]["ordinal"]]["u_um"])


class RepeatedInputTests(Case):
    def test_repeat_unchanged_accepted(self):
        rows = self.rows()
        for r, src in zip(rows, IN_ROWS):
            r["power_W"], r["speed_mm_s"], r["spot_um"] = src[3], src[4], src[5]
        res = self.parse(self.render(rows))
        self.assertEqual(len(res["byOrdinal"]), 8)

    def test_repeat_with_alias_and_unit_accepted(self):
        rows = self.rows()
        for r, src in zip(rows, IN_ROWS):
            r["Power (kW)"] = str(float(src[3]) / 1000.0)
            r["Speed (mm/s)"] = src[4]
        self.parse(self.render(rows))

    def test_repeat_power_differs(self):
        rows = self.rows()
        for r, src in zip(rows, IN_ROWS):
            r["power_W"], r["speed_mm_s"] = src[3], src[4]
        rows[1]["power_W"] = "778.5"
        exc = self.refused("INPUT_REPEAT_MISMATCH", self.render(rows))
        self.assertEqual(exc.detail, {"row": 3, "column": "power_W"})
        self.assertNotIn("778.5", exc.message)
        rows = self.rows()
        for r, src in zip(rows, IN_ROWS):
            r["spot_um"] = src[5]
        rows[4]["spot_um"] = "81"
        self.refused("INPUT_REPEAT_MISMATCH", self.render(rows))

    def test_input_columns_are_not_targets(self):
        rows = self.rows()
        for r in rows:
            r["power_W"] = ""
        self.parse(self.render(rows))             # blank repeated cells are skipped


if __name__ == "__main__":
    unittest.main()
