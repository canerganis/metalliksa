"""Fast unit tests of tools/lpbf_validity_envelope.py with a stubbed run() (no solver run)."""

import importlib.util
import json
import queue
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
_SPEC = importlib.util.spec_from_file_location("lpbf_validity_envelope", HERE / "tools" / "lpbf_validity_envelope.py")
envelope = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(envelope)

DEFAULTS = dict(mode="screening", material="Inconel 718", power_W=200., speed_mm_s=800., mesh_um=20., backend="auto")
BOILING = ("Thermal model validity exceeded at or above the material boiling limit "
           "(specific enthalpy 1 J/kg); evaporation/free-surface CFD required")

METRICS = dict(width_um=80., depth_um=20., length_um=200., peakTemperature_K=2500.)


def fake_result(power):
    return dict(
        metrics=dict(width_um=80., depth_um=power / 4, length_um=240., peakTemperature_K=2000. + power,
                     thermalGradient_K_m=1e7, coolingRate_K_s=1e6),
        energyBalance=dict(relativeError=1e-16),
        numericalDiagnostics=dict(peakMeltCellCount=3),
        provenance=dict(implementationHash="h", inputHash="i"),
        label="Unvalidated transient thermal", validationStatus="unvalidated")


def stub_run(boil_from):
    def _run(raw):
        if raw["power_W"] >= boil_from:
            raise ValueError(BOILING)
        return fake_result(raw["power_W"])
    return _run


class ClassificationTest(unittest.TestCase):
    def test_boiling_message_is_boiling_stop(self):
        self.assertEqual(envelope.classify_error(BOILING), "boiling-stop")

    def test_other_message_is_other_error(self):
        self.assertEqual(envelope.classify_error("Invalid power_W"), "other-error")

    def test_run_case_statuses(self):
        done = envelope.run_case(dict(power_W=40.), stub_run(100.))
        self.assertEqual(done["status"], "completed")
        self.assertEqual(done["peakTemperature_K"], 2040.)
        self.assertEqual(done["implementationHash"], "h")
        stop = envelope.run_case(dict(power_W=120.), stub_run(100.))
        self.assertEqual(stop["status"], "boiling-stop")
        self.assertIn("boiling", stop["message"])

        def other(raw):
            raise ValueError("bad input")
        self.assertEqual(envelope.run_case({}, other)["status"], "other-error")

    def test_d13_label_travels_with_the_transient_event_means(self):
        # SOL-T D13: a synthetic container; the summary keeps status, label and label sources per value.
        def labelled(raw):
            out = fake_result(raw["power_W"])
            q = {"status": "computed", "sourceEvidenceKind": "Literature estimate", "labelSources": ["synthetic"]}
            out["transientFrontDiagnostics"] = {"quantities": {"thermalGradient_K_m": q, "coolingRate_K_s": q,
                                                               "solidificationRate_m_s": q}}
            return out
        done = envelope.run_case(dict(power_W=40.), labelled)
        self.assertEqual(set(done["transientFrontEvidence"]), {"thermalGradient_K_m", "coolingRate_K_s"})
        self.assertEqual(done["transientFrontEvidence"]["coolingRate_K_s"]["sourceEvidenceKind"], "Literature estimate")
        self.assertIsNone(envelope.run_case(dict(power_W=40.), stub_run(100.))["transientFrontEvidence"])

        def crash(raw):
            raise RuntimeError("boom")
        crashed = envelope.run_case({}, crash)
        self.assertEqual(crashed["status"], "other-error")
        self.assertIn("RuntimeError", crashed["message"])


class SweepTest(unittest.TestCase):
    def test_raw_input_is_defaults_with_overrides(self):
        raw = envelope.build_raw(DEFAULTS, "Ti-6Al-4V", 80., 10.)
        self.assertEqual((raw["mode"], raw["backend"], raw["material"], raw["power_W"], raw["mesh_um"]),
                         ("standard", "reference", "Ti-6Al-4V", 80., 10.))
        self.assertEqual(raw["speed_mm_s"], 800.)

    def test_default_plan_matches_specification(self):
        plan = envelope.default_plan()
        self.assertEqual([(a, m) for a, m, _ in plan],
                         [(a, 20.) for a in envelope.ALLOYS] + [("Inconel 718", 10.)])
        self.assertEqual(plan[-1][2], (40., 60., 80., 100.))
        self.assertEqual(envelope.build_plan(quick=True), [("Inconel 718", 20., envelope.POWERS_20)])

    def test_schema_writer_and_monotone_stop(self):
        calls = []

        def runner(raw):
            calls.append(raw["power_W"])
            return envelope.run_case(raw, stub_run(100.))

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "env.json"
            document = envelope.new_document(dict(python="x"), 900.)
            envelope.sweep([("Inconel 718", 20., envelope.POWERS_20)], DEFAULTS, document, out, runner)
            self.assertEqual(calls, [40., 60., 80., 100., 120.])  # two consecutive stops, then skipped
            self.assertNotIn(b"\r\n", out.read_bytes())  # LF on every platform (.gitattributes eol=lf)
            written = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(written["schema"], "lpbf-validity-envelope-1")
            self.assertIn("not a process window, not experimental validation", written["scope"])
            statuses = [c["status"] for c in written["cases"]]
            self.assertEqual(statuses[:3], ["completed"] * 3)
            self.assertEqual(statuses[3:5], ["boiling-stop"] * 2)
            self.assertTrue(all(s.startswith("not-run") for s in statuses[5:]))
            self.assertEqual(written["cases"][0]["input"]["mode"], "standard")
            row = written["summary"][0]
            self.assertEqual((row["highestCompletedPower_W"], row["firstBoilingStopPower_W"]), (80., 100.))
            self.assertEqual(row["depth_um"], 20.)

            # Resume: nothing is recomputed.
            calls.clear()
            envelope.sweep([("Inconel 718", 20., envelope.POWERS_20)], DEFAULTS, written, out, runner)
            self.assertEqual(calls, [])

    def test_completed_case_resets_consecutive_stop_counter(self):
        status_by_power = {40.: "boiling-stop", 60.: "completed", 80.: "boiling-stop", 100.: "completed",
                           120.: "boiling-stop", 150.: "completed", 200.: "boiling-stop"}
        calls = []

        def runner(raw):
            calls.append(raw["power_W"])
            return dict(status=status_by_power[raw["power_W"]], wall_s=0., **METRICS)

        document = envelope.new_document(dict(python="x"), 900.)
        envelope.sweep([("Inconel 718", 20., envelope.POWERS_20)], DEFAULTS, document, None, runner)
        self.assertEqual(calls, list(envelope.POWERS_20))  # never two stops in a row: nothing skipped

    def test_writer_rejects_nan_and_leaves_no_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "env.json"
            with self.assertRaises(ValueError):
                envelope.write_document(out, dict(schema=envelope.SCHEMA, value=float("nan")))
            self.assertFalse(out.exists())

    def test_resume_reuses_only_identical_input_and_current_implementation_hash(self):
        calls = []

        def runner(raw):
            calls.append(raw["power_W"])
            return dict(status="completed", wall_s=1., implementationHash="current", **METRICS)

        plan = [("Inconel 718", 20., (40., 60., 80., 100.))]

        def cached(power, **changes):
            raw = envelope.build_raw(DEFAULTS, "Inconel 718", power, 20.)
            record = dict(alloy="Inconel 718", mesh_um=20., power_W=power, input=raw,
                          status="completed", wall_s=1., implementationHash="current", **METRICS)
            record.update(changes)
            return record

        stale_input = cached(60.)
        stale_input["input"] = dict(stale_input["input"], speed_mm_s=999.)
        document = envelope.new_document(dict(python="x"), 900.)
        document["cases"] = [
            cached(40.),                                         # identical: reused
            stale_input,                                         # different input: recomputed
            cached(80., implementationHash="old-solver"),        # different hash: recomputed
            cached(100., implementationHash=None),               # no recorded hash: recomputed
        ]
        envelope.sweep(plan, DEFAULTS, document, None, runner, fingerprint="current")
        self.assertEqual(calls, [60., 80., 100.])
        by_power = {c["power_W"]: c for c in document["cases"]}
        self.assertEqual(by_power[80.]["implementationHash"], "current")
        self.assertEqual(by_power[100.]["implementationHash"], "current")

        # Without a fingerprint only the input is compared (stub runs without provenance).
        calls.clear()
        document["cases"] = [cached(40., implementationHash="whatever")]
        envelope.sweep([("Inconel 718", 20., (40.,))], DEFAULTS, document, None, runner)
        self.assertEqual(calls, [])

    def test_hashless_boiling_stop_is_recomputed_and_current_one_is_reused(self):
        calls = []

        def runner(raw):
            calls.append(raw["power_W"])
            return dict(status="boiling-stop", wall_s=2.)

        def stop(power, **changes):
            raw = envelope.build_raw(DEFAULTS, "Inconel 718", power, 20.)
            record = dict(alloy="Inconel 718", mesh_um=20., power_W=power, input=raw,
                          status="boiling-stop", wall_s=1.)
            record.update(changes)
            return record

        document = envelope.new_document(dict(python="x"), 900.)
        document["cases"] = [stop(40.), stop(60., implementationHash="current")]
        envelope.sweep([("Inconel 718", 20., (40., 60.))], DEFAULTS, document, None, runner,
                       fingerprint="current")
        self.assertEqual(calls, [40.])  # hash-less stop recomputed; stop with the current hash reused
        by_power = {c["power_W"]: c for c in document["cases"]}
        self.assertEqual(by_power[40.]["implementationHash"], "current")
        self.assertEqual(by_power[40.]["wall_s"], 2.)

    def test_budget_and_error_records_are_always_retried(self):
        for status in (envelope.NOT_RUN_BUDGET, envelope.OTHER_ERROR):
            for fingerprint, recorded in (("current", "current"), (None, None)):
                calls = []

                def runner(raw):
                    calls.append(raw["power_W"])
                    return dict(status="completed", wall_s=1., implementationHash="current", **METRICS)

                raw = envelope.build_raw(DEFAULTS, "Inconel 718", 40., 20.)
                record = dict(alloy="Inconel 718", mesh_um=20., power_W=40., input=raw, status=status,
                              wall_s=900., message="x")
                if recorded is not None:
                    record["implementationHash"] = recorded
                document = envelope.new_document(dict(python="x"), 900.)
                document["cases"] = [record]
                envelope.sweep([("Inconel 718", 20., (40.,))], DEFAULTS, document, None, runner,
                               fingerprint=fingerprint)
                self.assertEqual(calls, [40.], (status, fingerprint))
                self.assertEqual(document["cases"][0]["status"], "completed")

    def test_recomputed_boiling_stop_carries_the_fingerprint(self):
        document = envelope.new_document(dict(python="x"), 900.)
        envelope.sweep([("Inconel 718", 20., (40.,))], DEFAULTS, document, None,
                       lambda raw: dict(status="boiling-stop", wall_s=0.), fingerprint="current")
        self.assertEqual(document["cases"][0]["implementationHash"], "current")


class _FakeProcess:
    def __init__(self, exitcode=None):
        self.exitcode = exitcode
        self.terminated = False

    def terminate(self):
        self.terminated = True

    def join(self, timeout=None):
        return None


class _FakeQueue:
    def __init__(self, items=()):
        self.items = list(items)

    def get(self, timeout=None):
        if self.items:
            return self.items.pop(0)
        raise queue.Empty


class BudgetTest(unittest.TestCase):
    def test_returns_reported_outcome(self):
        outcome = envelope.collect_outcome(_FakeQueue([dict(status="completed")]), _FakeProcess(),
                                           5., envelope.time.perf_counter(), poll_s=0.01)
        self.assertEqual(outcome["status"], "completed")

    def test_child_crash_is_other_error_with_exit_code_not_budget(self):
        process = _FakeProcess(exitcode=-11)
        started = envelope.time.perf_counter()
        outcome = envelope.collect_outcome(_FakeQueue(), process, 600., started, poll_s=0.01)
        self.assertEqual(outcome["status"], "other-error")
        self.assertIn("-11", outcome["message"])
        self.assertFalse(process.terminated)
        self.assertLess(envelope.time.perf_counter() - started, 30.)  # returns at once, not after 600 s

    def test_result_queued_just_before_exit_is_not_a_crash(self):
        class LateQueue(_FakeQueue):
            def __init__(self):
                super().__init__()
                self.calls = 0

            def get(self, timeout=None):
                self.calls += 1
                if self.calls == 2:
                    return dict(status="completed")
                raise queue.Empty
        outcome = envelope.collect_outcome(LateQueue(), _FakeProcess(exitcode=0), 5.,
                                           envelope.time.perf_counter(), poll_s=0.01)
        self.assertEqual(outcome["status"], "completed")

    def test_true_timeout_is_not_run_budget_and_terminates_the_child(self):
        process = _FakeProcess(exitcode=None)
        outcome = envelope.collect_outcome(_FakeQueue(), process, 0.05, envelope.time.perf_counter(), poll_s=0.01)
        self.assertEqual(outcome["status"], "not-run (budget)")
        self.assertTrue(process.terminated)


class EnvironmentTest(unittest.TestCase):
    @unittest.skipUnless(shutil.which("git"), "git not available")
    def test_tree_dirty_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)

            def git(*args):
                subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
                               cwd=str(repo), check=True, capture_output=True)
            git("init")
            (repo / "a.py").write_text("x = 1\n", encoding="utf-8")
            git("add", "a.py")
            git("commit", "-m", "init")
            self.assertIs(envelope._tree_dirty(repo), False)
            (repo / "a.py").write_text("x = 2\n", encoding="utf-8")
            self.assertIs(envelope._tree_dirty(repo), True)
            git("checkout", "--", "a.py")
            (repo / "new.py").write_text("y = 1\n", encoding="utf-8")  # untracked counts as dirty
            self.assertIs(envelope._tree_dirty(repo), True)
        self.assertIsNone(envelope._tree_dirty(Path(tmp) / "does-not-exist"))


if __name__ == "__main__":
    unittest.main()
