#!/usr/bin/env python3
"""Self-contained tests of the group 9 calibration status display (python/lpbf_calibrated_meltpool.py).

The committed artefact data/calibration/lpbf-meltpool-calibration-v1.json is read only. Matching and tampered states
are manufactured in a temporary copy (content hash recomputed with the loader's own function); no fit is run and no
measured row is loaded.
"""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import lpbf_calibrated_meltpool as cm  # noqa: E402
import lpbf_calibration_layer as layer  # noqa: E402

REQUEST = dict(material="AlSi10Mg", laserPower_W=350, scanSpeed_mm_s=1300, beamDiameter_um=80, preheatTemp_C=160,
               layerThickness_um=40, hatchSpacing_um=100, laserWavelength="IR_1064nm", calibrationMode=True,
               heatSource="goldak")
UNKNOWN = "Uncertainty is unknown and may be large. Calibrate to your machine for better accuracy."


def manufactured(edit):
    art = json.loads(Path(layer.DEFAULT_PATH).read_text(encoding="utf-8"))
    edit(art)
    art["contentSha256"] = layer.artefact_content_sha256(art)
    folder = tempfile.mkdtemp(prefix="calib-status-")
    path = Path(folder) / "artefact.json"
    path.write_text(json.dumps(art), encoding="utf-8")
    return path, art


class StatusTests(unittest.TestCase):
    def test_committed_artefact_is_stale_with_zero_enabled_cells(self):
        st = cm.calibration_status("Ti-6Al-4V", "goldak")
        self.assertEqual(st["artifact"]["state"], "stale")
        self.assertEqual(st["artifact"]["text"], cm.STALE_TEXT)
        self.assertEqual(st["enabledCellCount"], 0)
        for quantity in ("width", "depth"):
            cell = st["cells"][quantity]
            self.assertEqual(cell["status"], "rejected")
            self.assertFalse(cell["eligible"])
            self.assertEqual(cell["text"], "This calibration has no eligible %s fit for Ti-6Al-4V and goldak. Import "
                                           "suitable measurements and fit a new calibration." % quantity)

    def test_within_source_only_is_not_promoted(self):
        cell = cm.calibration_status("316L Stainless Steel", "goldak")["cells"]["depth"]
        self.assertEqual(cell["status"], "within-source-only")
        self.assertFalse(cell["eligible"])

    def test_matching_hash_alone_restores_no_cell(self):
        path, art = manufactured(lambda a: None)
        with mock.patch("lpbf_simulation.implementation_fingerprint", return_value=art["implementationHash"]):
            st = cm.calibration_status("Ti-6Al-4V", "goldak", path=path)
        self.assertEqual(st["artifact"]["state"], "ready")
        self.assertFalse(any(c["eligible"] for c in st["cells"].values()))

    def test_enabled_cell_on_matching_artefact_is_eligible(self):
        def enable(a):
            for c in a["cells"]:
                if (c["kernel"], c["material"], c["quantity"]) == ("goldak", "Ti-6Al-4V", "depth"):
                    c["status"] = "enabled"
        path, art = manufactured(enable)
        with mock.patch("lpbf_simulation.implementation_fingerprint", return_value=art["implementationHash"]):
            st = cm.calibration_status("Ti-6Al-4V", "goldak", path=path)
        self.assertTrue(st["cells"]["depth"]["eligible"])
        self.assertIsNone(st["cells"]["depth"]["text"])
        self.assertFalse(st["cells"]["width"]["eligible"])
        # The same enabled cell on a stale artefact stays ineligible: hashes, not toggles, decide.
        stale = cm.calibration_status("Ti-6Al-4V", "goldak", path=path)
        self.assertEqual(stale["artifact"]["state"], "stale")
        self.assertFalse(stale["cells"]["depth"]["eligible"])

    def test_tampered_artefact_is_unavailable_not_stale(self):
        path, art = manufactured(lambda a: None)
        data = json.loads(path.read_text(encoding="utf-8"))
        data["cells"][0]["status"] = "enabled"  # edited without recomputing the content hash
        path.write_text(json.dumps(data), encoding="utf-8")
        st = cm.calibration_status("Ti-6Al-4V", "goldak", path=path)
        self.assertEqual(st["artifact"]["state"], "unavailable")
        self.assertEqual(st["cells"], {})

    def test_not_requested(self):
        self.assertEqual(cm.calibration_status("AlSi10Mg", "goldak", requested=False)["artifact"]["state"],
                         "not-requested")


class ParentTests(unittest.TestCase):
    def test_run_adds_status_without_changing_the_numbers(self):
        out = cm.run(dict(REQUEST))
        spec = layer.solver_kwargs(REQUEST)
        direct = layer._default_solver()(*spec["args"], heat_source="goldak", **spec["kwargs"])
        self.assertEqual(out["screening"]["meltPoolGeometry"], direct["meltPoolGeometry"])
        self.assertFalse(out["calibrated"]["available"])
        self.assertIsNone(out["calibrated"]["depth_um"])
        parent = out["uncalibratedParent"]
        self.assertEqual(parent["estimateTier"], "Physics estimate")
        self.assertEqual(parent["tierLabel"], "Uncalibrated estimate")
        self.assertEqual(parent["depth_um"], direct["meltPoolGeometry"]["depth_um"])
        self.assertTrue(parent["explanation"].startswith("Uncalibrated estimate: about "))
        self.assertTrue(parent["explanation"].endswith(UNKNOWN))
        self.assertEqual(out["calibrationStatus"]["artifact"]["state"], "stale")

    def test_parent_without_computed_extent_has_no_value(self):
        for geometry in ({"extentStatus": "unresolved", "width_um": 100.0, "depth_um": 50.0},
                         {"extentStatus": "computed", "width_um": 0.0, "depth_um": 50.0}, {}):
            parent = cm.uncalibrated_parent({"meltPoolGeometry": geometry}, "goldak")
            self.assertIsNone(parent["width_um"], geometry)
            self.assertEqual(parent["noValueText"], cm.PARENT_REFUSED_TEXT)

    def test_keyhole_parent_warns_first(self):
        parent = cm.uncalibrated_parent({"meltPoolGeometry": {"extentStatus": "computed", "width_um": 110.0,
                                                              "depth_um": 77.0, "regime": "Keyhole Mode"}}, "goldak")
        self.assertTrue(parent["domainWarnings"][0].startswith("Keyhole regime"))

    def test_status_overview_lists_every_cell(self):
        st = cm.status()
        self.assertEqual(st["overview"]["state"], "stale")
        self.assertEqual(st["overview"]["enabledCellCount"], 0)
        self.assertEqual(len(st["overview"]["cells"]), 30)


if __name__ == "__main__":
    unittest.main()
