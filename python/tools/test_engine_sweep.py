"""Standalone sweep tests: stdlib only; never import a served physics module."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import Mock, patch

TOOL = Path(__file__).with_name("engine_sweep.py")
spec = importlib.util.spec_from_file_location("engine_sweep", TOOL)
sweep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sweep)


class EngineSweepTests(unittest.TestCase):
    def test_nested_null_reasons_and_statuses_are_not_lost(self):
        body = {"status": "partial", "reasonCodes": ["MISSING_MODEL"], "q": [
            {"status": "unavailable", "reasonCode": "MISSING_N0", "value": None},
            {"status": "not-requested", "value": None}, {"value": 0},
        ], "optionalMetadata": None}
        found = {x["path"]: x for x in sweep.findings(body)}
        self.assertEqual(found["$.q[0].value"]["reasons"][-1]["reasonCode"], "MISSING_N0")
        self.assertEqual(found["$.q[1].value"]["reasons"][0]["reasonCodes"], ["MISSING_MODEL"])
        self.assertIn("$.q[1].status", found)
        self.assertNotIn("$.q[2].value", found)
        self.assertEqual(found["$.optionalMetadata"]["kind"], "null")

    def test_prose_and_boolean_unavailability_are_preserved(self):
        found = sweep.findings({"available": False, "reason": "no source", "depth": None})
        self.assertEqual(found[0]["kind"], "status-container")
        self.assertEqual(found[-1]["reasons"][0]["reason"], "no source")
        self.assertEqual(sweep.findings({"value": None})[0]["reasons"], [])

    def test_all_route_dispatched_scripts_have_inventory_entries(self):
        import re
        scripts = set()
        for route in (sweep.ROOT / "routes").glob("*.ts"):
            scripts.update(re.findall(r'"python/([a-z_]+)\.py"', route.read_text(encoding="utf-8")))
        targets = {op["target"].split(":")[0] for op in sweep.inventory()}
        self.assertTrue(scripts <= targets, scripts - targets)
        ids = [x["id"] for x in sweep.inventory()]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertNotIn("fatigue-fracture", ids)  # RPC-only; no HTTP/UI route today.

    def test_registry_authorities_are_covered_and_tool_is_outside_manifests(self):
        import ast
        registry = json.loads((sweep.ROOT / "src/generated/moduleRegistry.json").read_text(encoding="utf-8"))
        modules = {op["target"].split(":")[0] for op in sweep.inventory()}
        methods = {op["id"] for op in sweep.inventory()}
        for contract in registry["contracts"]:
            for op in contract.get("operations", []):
                authority = op["authority"]
                if authority["kind"] == "python-ipc":
                    self.assertIn(Path(authority["script"]).stem, modules)
                if authority["kind"] == "lpbf-worker":
                    self.assertIn(authority["workerMethod"], methods)
        for manifest in sweep.PYTHON.glob("*manifest*.py"):
            tree = ast.parse(manifest.read_text(encoding="utf-8-sig"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    self.assertFalse(any("engine_sweep" in name.name for name in node.names), manifest)
                elif isinstance(node, ast.ImportFrom):
                    self.assertNotIn("engine_sweep", node.module or "", str(manifest))
                    self.assertFalse(any("engine_sweep" in name.name for name in node.names), manifest)
            self.assertNotIn("engine_sweep.py", manifest.read_text(encoding="utf-8-sig"))

    def test_data_readers_and_gpu_are_skipped_before_dispatch(self):
        blocked = {"lpbf-process-window", "nist-comparison", "proxy-campaign-validation", "submit:gpu-thermal-pilot"}
        with patch.object(sweep.subprocess, "Popen", side_effect=AssertionError("must not spawn")):
            for op in sweep.inventory():
                if op["id"] in blocked:
                    result = sweep.run_call(op, "IN718" if op["alloy"] else None, "default", 1)
                    self.assertEqual(result["outcome"], "skipped")

    def test_ui_defaults_and_no_invented_in625_composition(self):
        ops = {x["id"]: x for x in sweep.inventory()}
        self.assertIsNone(sweep.payload(ops["calphad-minimize"], "IN625"))
        build = sweep.payload(ops["submit:build-job"], "IN718")
        self.assertEqual((build["laserPower_W"], build["scanSpeed_mm_s"], build["preheatTemp_C"]), (280, 940, 200))
        self.assertFalse(build["includeAmbench"])
        self.assertFalse(build["enableUq"])
        self.assertEqual(sweep.payload(ops["submit"])["backend"], "reference")
        research = sweep.payload(ops["lpbf-research-models"], "IN718", "band")
        self.assertEqual(research["timeBudgetMs"], 1500)

    def test_timeout_kills_owned_windows_process_tree(self):
        proc = Mock(pid=123456)
        proc.communicate.side_effect = [subprocess.TimeoutExpired("sweep", .01), ("", "")]
        op = sweep.operation("test", "test", "json:loads", "test", "test", alloy=False)
        with patch.object(sweep.subprocess, "Popen", return_value=proc), patch.object(sweep.subprocess, "run") as kill:
            result = sweep.run_call(op, None, "default", .01)
        self.assertEqual(result["error"]["className"], "TimeoutError")
        if os.name == "nt":
            self.assertEqual(kill.call_args.args[0], ["taskkill", "/PID", "123456", "/T", "/F"])
        else:
            proc.kill.assert_called_once()
        self.assertEqual(proc.communicate.call_count, 2)

    def test_guards_block_paths_and_network_in_disposable_process(self):
        code = f'''import importlib.util, socket
spec=importlib.util.spec_from_file_location("sweep", {str(TOOL)!r})
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
m.install_guards()
for path in ["leis2021.csv", ".orchestra/external-data/anything.csv", "hyer2020/tracks.json"]:
 try: open(path)
 except m.SweepBlocked: pass
 else: raise AssertionError(path)
try: socket.getaddrinfo("example.com", 443)
except m.SweepBlocked: pass
else: raise AssertionError("network allowed")
'''
        done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_child_preserves_exception_class_and_message(self):
        op = sweep.operation("test", "test", "json:loads", "test", "test", alloy=False)
        result = sweep.run_call(op, None, "default", 15)
        self.assertEqual(result["outcome"], "error")
        self.assertEqual(result["error"]["className"], "TypeError")
        self.assertIn("dict", result["error"]["message"])


if __name__ == "__main__":
    unittest.main()
