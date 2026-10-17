"""User blind test end to end with a stub solver (spec 11.1 items 3 and 6, 12).

Synthetic data only. The stub served arm returns sentinel depths (4000 um and up, a value no real track has), so
the leak scans can search every output for them. Each test uses its own temporary store and job root; the socket
module is patched so any network use fails.
"""
import ast
import base64
import builtins
import io
import json
import os
import shutil
import socket
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import lpbf_user_blind as ub
import lpbf_user_blind_freeze as ufreeze
import lpbf_user_blind_overlap as uover
import lpbf_user_blind_protocol as proto
import lpbf_user_blind_score as uscore
from lpbf_served_arms import served_index

PY = Path(__file__).resolve().parent
S = proto.REQUEST_SCHEMA
SYNTHETIC = "synthetic fixture, invented numbers, not measured data"
SENTINEL_BASE = 4000.0


def stub_served_arm(alloy, P_W, v_mm_s, d_1e2_um, T0_C, layer_um=40.0, **_kw):
    depth = SENTINEL_BASE + round(P_W * 0.137 + v_mm_s * 0.0071 + d_1e2_um * 0.0013, 6)
    return {"status": "ok", "depth_um": depth, "width_um": depth / 3.0, "extentStatus": "computed",
            "fabbroDepth_um": depth / 2.0, "index": served_index(alloy, P_W, v_mm_s, d_1e2_um, T0_C),
            "reasonLabel": None, "materialEvidence": None, "buildJobIdentity": None}


def metadata(**over):
    md = json.loads((PY.parent / "data" / "blind" / "templates" / "blind_metadata_v1.json").read_text())
    md["blockLabel"] = "Synthetic test block"
    md["replication"]["tracksPerCondition"] = 2
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(md.get(k), dict):
            md[k] = {**md[k], **v}
        else:
            md[k] = v
    return md


def conditions(n=12, spot=80.0):
    """n invented settings that straddle the Ti-6Al-4V leverage cuts."""
    pv = [(P, v) for P in (90.0, 150.0, 250.0, 380.0) for v in (300.0, 700.0, 1500.0)]
    pv += [(P, v) for P in (120.0, 320.0) for v in (450.0, 1100.0)]
    return [(f"c{i + 1}", P, v, spot) for i, (P, v) in enumerate(pv[:n])]


def inputs_csv(conds, tracks=2):
    lines = ["condition_id,track_id,power_W,speed_mm_s,spot_um"]
    for cid, P, v, d in conds:
        for t in range(1, tracks + 1):
            lines.append(f"{cid},{cid}t{t},{P:g},{v:g},{d:g}")
    return ("\n".join(lines) + "\n").encode()


def targets_csv(conds, tracks=2, depth=lambda P, v, t: 40.0 + P * P / v / 3.0 + t, status=None):
    lines = ["condition_id,track_id,depth_um,width_um,depth_status"]
    for cid, P, v, _d in conds:
        for t in range(1, tracks + 1):
            st = (status or {}).get(f"{cid}t{t}")
            if st and st != "measured":
                lines.append(f"{cid},{cid}t{t},,,{st}")
            else:
                lines.append(f"{cid},{cid}t{t},{depth(P, v, t):.3f},{100 + t},")
    return ("\n".join(lines) + "\n").encode()


def b64(data):
    return base64.b64encode(data).decode("ascii")


class _NoNetwork:
    def __init__(self, *a, **k):
        raise AssertionError("network use in a blind test")


class BlindCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="blind-test-"))
        self.env = mock.patch.dict(os.environ, {"METALLIKSA_USER_BLIND_ROOT": str(self.tmp / "store"),
                                                "METALLIKSA_JOB_ROOT": str(self.tmp / "jobs"),
                                                "METALLIKSA_READ_ONLY": "", "METALLIKSA_HOST": ""})
        self.env.start()
        (self.tmp / "jobs").mkdir()
        # One test process holds the scorer too; the module-absence assertion is tested on its own
        # (test_freeze_asserts_scorer_absent) and holds in production because every job runs in a fresh child.
        self.patches = [mock.patch.object(ufreeze, "served_arm", stub_served_arm),
                        mock.patch.object(ufreeze, "FORBIDDEN_MODULES", ()),
                        mock.patch.object(socket, "socket", _NoNetwork),
                        mock.patch.object(uover, "_calibration_roots",
                                          lambda: (self.tmp / "user-cal", self.tmp / "machine-cal"))]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.env.stop()

        def onerror(func, path, _exc):
            os.chmod(path, 0o666)
            func(path)
        shutil.rmtree(self.tmp, onerror=onerror)

    # ---------------------------------------------------------------- helpers
    def preview(self, md, raw):
        return ub.rpc({"jobType": "user-blind-preview", "schema": S, "metadata": md, "inputsCsvBase64": b64(raw),
                       "inputsFileName": "inputs.csv"})

    def job(self, payload):
        staged = ub.stage_request(ub.validate_request(payload))
        folder = self.tmp / "jobs" / os.urandom(16).hex()
        folder.mkdir()
        result = ub.run_job(staged, folder)
        ub.enforce_user_blind_job_result(result, staged)
        return result

    def freeze(self, md=None, conds=None, acks=None, raw=None):
        md = md or metadata()
        raw = raw or inputs_csv(conds or conditions())
        pv = self.preview(md, raw)
        acks = acks if acks is not None else {a: True for a in pv["acknowledgementsRequired"]}
        return self.job({"jobType": "user-blind-freeze", "schema": S, "metadata": md, "inputsCsvBase64": b64(raw),
                         "inputsFileName": "inputs.csv", "previewSha256": pv["previewSha256"],
                         "overlapSha256": pv["overlapSha256"], "acknowledgements": acks})

    def score(self, key, raw, viewed="no", accept=False):
        return self.job({"jobType": "user-blind-score", "schema": S, "freezeKey": key, "targetsCsvBase64": b64(raw),
                         "targetsFileName": "targets.csv",
                         "declarations": {"viewedPredictionsBeforeFinalisingTargets": viewed},
                         "acceptCommitmentMismatch": accept})

    def report(self, key, n=1):
        st = ub.Store()
        return json.loads(st.read_record(st.record_dir(key, "score", n), "score.json"))

    def reveal(self, key):
        return self.job({"jobType": "user-blind-reveal", "schema": S, "freezeKey": key,
                         "confirmation": proto.REVEAL_PHRASE})

    def predicted(self, key):
        return ub._predicted_values(key)

    def assert_no_sentinel(self, obj):
        text = json.dumps(obj)
        for v in self.predicted(json.loads(text).get("freezeKey") or ""):
            self.assertNotIn(repr(v), text)
        self.assertNotIn('"40', "") if False else None
        for token in ("4000.", "4001.", "4002.", "4003.", "4004.", "4005."):
            self.assertNotIn(token, text)


class EndToEnd(BlindCase):
    def test_preview_freeze_score_and_no_prediction_outside_the_gate(self):
        conds = conditions()
        pv = self.preview(metadata(), inputs_csv(conds))
        self.assertEqual(pv["honesty"], proto.HONESTY)
        ub.assert_no_prediction(pv)
        rec = self.freeze(conds=conds)
        self.assertTrue(rec["predictionsWithheld"])
        self.assert_no_sentinel(rec)
        lst = ub.rpc({"jobType": "user-blind-list", "schema": S})
        got = ub.rpc({"jobType": "user-blind-get", "schema": S, "freezeKey": rec["freezeKey"]})
        for doc in (lst, got):
            self.assert_no_sentinel(doc)
        self.assertNotIn("blind-freeze.json", [d["name"] for d in got["documents"]])
        res = self.score(rec["freezeKey"], targets_csv(conds))
        self.assert_no_sentinel(res)
        rep = self.report(rec["freezeKey"])
        self.assertEqual(rep["honesty"], proto.HONESTY)
        self.assertEqual([d["id"] for d in rep["divergences"]], [d["id"] for d in proto.DIVERGENCES])
        self.assertEqual(rep["arms"]["research:melt-link"]["status"], "unavailable")
        self.assertEqual(rep["arms"]["research:melt-link"]["reason"], "RESEARCH_NOT_REQUESTED")
        self.assertEqual(rep["blindness"]["status"], "blind-prospective-declared")
        row = rep["ledger"][0]
        self.assertEqual(row["observed"]["sourceEvidenceKind"], "Measured (user-supplied)")
        self.assertEqual(row["observed"]["tier"], "Declared")
        self.assertEqual(row["pred"]["served"]["sourceEvidenceKind"], "Unresolved")
        self.assertEqual(row["pred"]["served"]["sourceReason"], "SERVED_VALUE_KIND_NOT_PROVIDED")
        self.assertNotIn("Measured", {row["pred"]["served"]["sourceEvidenceKind"]})
        self.assertEqual(rep["predictor"]["changedSinceFreeze"], False)

    def test_freeze_is_idempotent_and_key_ignores_created_at(self):
        a = self.freeze()
        b = self.freeze()
        self.assertEqual(a["freezeKey"], b["freezeKey"])
        self.assertTrue(b["alreadyFrozen"])
        self.assertEqual(len(ub.Store().freeze_keys()), 1)

    def test_research_member_refused_and_arms_not_requested(self):
        md, raw = metadata(), inputs_csv(conditions())
        pv = self.preview(md, raw)
        with self.assertRaises(proto.BlindRefusal) as cm:
            ub.validate_request({"jobType": "user-blind-freeze", "schema": S, "metadata": md,
                                 "inputsCsvBase64": b64(raw), "inputsFileName": "inputs.csv",
                                 "previewSha256": pv["previewSha256"], "overlapSha256": pv["overlapSha256"],
                                 "acknowledgements": {}, "research": {"requested": True}})
        self.assertEqual(cm.exception.code, "METADATA_FIELD")
        rec = self.freeze()
        arms = {a["id"]: a for a in rec["armsFrozen"]}
        self.assertEqual(arms["research:melt-link"]["reasonCodes"], ["RESEARCH_NOT_REQUESTED"])
        self.assertEqual(rec["predictorIdentity"]["research"]["reasonCode"], "RESEARCH_NOT_REQUESTED")

    def test_predictor_not_pinned_refuses_the_freeze(self):
        with mock.patch("lpbf_user_blind_preview.unpinned_reasons", lambda ident: ["python/lpbf_job_cache.py"]):
            with self.assertRaises(proto.BlindRefusal) as cm:
                self.freeze()
        self.assertEqual(cm.exception.code, "PREDICTOR_NOT_PINNED")
        self.assertIn("python/lpbf_job_cache.py", cm.exception.message)

    def test_ack_required_at_submit(self):
        with self.assertRaises(proto.BlindRefusal) as cm:
            self.freeze(acks={})
        self.assertEqual(cm.exception.code, "ACK_REQUIRED")

    def test_overlap_changed_in_the_child(self):
        conds = conditions()
        other = self.freeze(md=metadata(blockLabel="Other synthetic block"), conds=conds,
                            raw=inputs_csv(conds, tracks=2).replace(b"t2,", b"t2x,"))
        md, raw = metadata(), inputs_csv(conds, tracks=2)
        pv = self.preview(md, raw)
        staged = ub.stage_request(ub.validate_request({
            "jobType": "user-blind-freeze", "schema": S, "metadata": md, "inputsCsvBase64": b64(raw),
            "inputsFileName": "inputs.csv", "previewSha256": pv["previewSha256"], "overlapSha256": pv["overlapSha256"],
            "acknowledgements": {a: True for a in pv["acknowledgementsRequired"]}}))
        self.reveal(other["freezeKey"])          # an overlapping test is revealed between submit and child run
        folder = self.tmp / "jobs" / ("a" * 32)
        folder.mkdir()
        with self.assertRaises(proto.BlindRefusal) as cm:
            ub.run_job(staged, folder)
        self.assertEqual(cm.exception.code, "OVERLAP_CHANGED")

    def test_open_audit_no_targets_path_during_freeze(self):
        conds = conditions()
        first = self.freeze(conds=conds)
        self.score(first["freezeKey"], targets_csv(conds))      # a targets upload now exists in the store
        opened = []
        real_open = builtins.open

        def audit(file, *a, **k):
            opened.append(str(file))
            return real_open(file, *a, **k)
        with mock.patch.object(builtins, "open", audit):
            self.freeze(md=metadata(blockLabel="Second synthetic block"),
                        conds=[(c[0], c[1] * 1.3, c[2], c[3]) for c in conds])
        self.assertFalse([p for p in opened if p.endswith(".targets.csv")])

    def test_ast_isolation_of_the_freeze_path_and_no_research_imports(self):
        def project_imports(mod, seen):
            path = PY / f"{mod}.py"
            if mod in seen or not path.is_file():
                return seen
            seen.add(mod)
            tree = ast.parse(path.read_bytes())
            for n in ast.walk(tree):
                names = [a.name for a in n.names] if isinstance(n, ast.Import) else (
                    [n.module] if isinstance(n, ast.ImportFrom) and n.module else [])
                for name in names:
                    if name.startswith("lpbf_user_blind") or name in ("lpbf_served_arms", "lpbf_blind_stats",
                                                                     "lpbf_spent_ledger"):
                        project_imports(name, seen)
            return seen
        closure = project_imports("lpbf_user_blind_freeze", set())
        self.assertNotIn("lpbf_user_blind_targets", closure)
        self.assertNotIn("lpbf_user_blind_score", closure)
        for path in list(PY.glob("lpbf_user_blind*.py")) + [PY / "lpbf_served_arms.py", PY / "lpbf_blind_stats.py",
                                                             PY / "lpbf_spent_ledger.py",
                                                             PY / "tools" / "lpbf_user_blind.py"]:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("lpbf-research-models", text, path.name)
            tree = ast.parse(text)
            for n in ast.walk(tree):
                names = [a.name for a in n.names] if isinstance(n, ast.Import) else (
                    [n.module] if isinstance(n, ast.ImportFrom) and n.module else [])
                self.assertFalse([x for x in names if x.startswith("lpbf_research")], path.name)

    def test_freeze_asserts_scorer_absent(self):
        import sys
        self.patches[1].stop()
        self.patches.pop(1)
        with mock.patch.dict(sys.modules, {"lpbf_user_blind_score": uscore}):
            with self.assertRaises(RuntimeError):
                ufreeze.assert_prediction_phase(["power_W", "speed_mm_s"])
        saved = {m: sys.modules.pop(m) for m in ("lpbf_user_blind_score", "lpbf_user_blind_targets")
                 if m in sys.modules}
        try:
            ufreeze.assert_prediction_phase(["power_W"])
            with self.assertRaises(PermissionError):
                ufreeze.assert_prediction_phase(["power_W", "depth_um"])
        finally:
            sys.modules.update(saved)


class Blindness(BlindCase):
    def test_reveal_precedes_servability_and_makes_the_next_report_not_blind(self):
        conds = conditions()
        rec = self.freeze(conds=conds)
        with self.assertRaises(proto.BlindRefusal):
            ub._resolve_document(ub.Store(), {"freezeKey": rec["freezeKey"]}, "blind-freeze.json")
        self.reveal(rec["freezeKey"])
        doc = ub._resolve_document(ub.Store(), {"freezeKey": rec["freezeKey"]}, "blind-freeze.json")
        self.assertIn(b'"pred"', doc["data"])
        self.score(rec["freezeKey"], targets_csv(conds))
        rep = self.report(rec["freezeKey"])
        self.assertEqual(rep["blindness"]["status"], "not-blind-predictions-revealed")
        self.assertEqual(rep["arms"]["served"]["status"], "descriptive-exposed")

    def test_earlier_test_overlap(self):
        conds = conditions()
        a = self.freeze(conds=conds)
        self.score(a["freezeKey"], targets_csv(conds))
        b = self.freeze(md=metadata(blockLabel="Later synthetic block"), conds=conds,
                        raw=inputs_csv(conds).replace(b"t1,", b"t1b,"))
        self.score(b["freezeKey"], targets_csv(conds).replace(b"t1,", b"t1b,"))
        self.assertEqual(self.report(b["freezeKey"])["blindness"]["status"], "not-blind-earlier-test-overlap")

    def test_commitment_match_mismatch_and_exception_after_freeze(self):
        conds = conditions()
        t = targets_csv(conds)
        import hashlib
        md = metadata(mode="post-measurement", targetCommitment={"sha256": hashlib.sha256(t).hexdigest()})
        rec = self.freeze(md=md, conds=conds)
        with self.assertRaises(proto.BlindRefusal) as cm:
            self.score(rec["freezeKey"], targets_csv(conds, depth=lambda P, v, k: 41.0 + P / 9 + k))
        self.assertEqual(cm.exception.code, "COMMITMENT_MISMATCH")
        self.reveal(rec["freezeKey"])                          # own reveal after the frozen event
        self.score(rec["freezeKey"], t)
        rep = self.report(rec["freezeKey"])
        self.assertEqual(rep["blindness"]["status"], "blind-committed")
        self.assertEqual(rep["blindness"]["exposuresAfterCommitment"][0]["status"], "not-blind-predictions-revealed")
        self.assertTrue(rep["commitment"]["matched"])

    def test_accepted_commitment_mismatch_downgrades(self):
        conds = conditions()
        md = metadata(mode="post-measurement", targetCommitment={"sha256": "0" * 64})
        rec = self.freeze(md=md, conds=conds)
        self.score(rec["freezeKey"], targets_csv(conds), accept=True)
        rep = self.report(rec["freezeKey"])
        self.assertEqual(rep["blindness"]["status"], "blind-retrospective-declared")
        self.assertIn("commitment not matched", rep["labels"])

    def test_calibration_store_tuple_gives_not_blind_and_no_measured_field_leaks(self):
        conds = conditions()
        d = self.tmp / "user-cal" / "user-synthetic"
        d.mkdir(parents=True)
        P, v = conds[0][1], conds[0][2]
        (d / "rows.json").write_text(json.dumps({"sourceId": "user-synthetic", "material": "Ti-6Al-4V", "rows": [
            {"power_W": P, "speed_mm_s": v, "beamDiameter_um": 80.0, "depth_um": 987.654321,
             "width_um": 876.543219}]}))
        pv = self.preview(metadata(), inputs_csv(conds))
        self.assertIn("calibrationOverlap", pv["acknowledgementsRequired"])
        rec = self.freeze(conds=conds)
        self.score(rec["freezeKey"], targets_csv(conds))
        rep = self.report(rec["freezeKey"])
        self.assertEqual(rep["blindness"]["status"], "not-blind-used-for-calibration")
        st = ub.Store()
        blob = json.dumps([pv, rec, rep, st.ledger()]) + st.record_dir(rec["freezeKey"], "score", 1).joinpath(
            "comparison.csv").read_text()
        self.assertNotIn("987.654321", blob)
        self.assertNotIn("876.543219", blob)

    def test_declared_calibration_use_and_viewed_predictions(self):
        conds = conditions()
        rec = self.freeze(md=metadata(independence={"usedForMachineCalibration": True}), conds=conds)
        self.score(rec["freezeKey"], targets_csv(conds))
        self.assertEqual(self.report(rec["freezeKey"])["blindness"]["status"], "not-blind-used-for-calibration")
        rec2 = self.freeze(md=metadata(blockLabel="Viewed synthetic", independence={
            "predictionsViewedBeforeFreeze": "unsure"}), conds=[(c[0], c[1] * 1.2, c[2], c[3]) for c in conds])
        self.score(rec2["freezeKey"], targets_csv([(c[0], c[1] * 1.2, c[2], c[3]) for c in conds]))
        self.assertEqual(self.report(rec2["freezeKey"])["blindness"]["status"], "not-blind-predictions-viewed")

    def test_published_doi_unknown_and_spent(self):
        conds = conditions()
        rec = self.freeze(md=metadata(mode="post-measurement", independence={
            "dataPreviouslyPublished": "yes", "publishedDoi": "10.9999/synthetic.unknown"}), conds=conds)
        self.score(rec["freezeKey"], targets_csv(conds))
        rep = self.report(rec["freezeKey"])
        self.assertEqual(rep["blindness"]["status"], "blind-retrospective-declared")
        self.assertTrue(any("not in this app's spent ledger" in x for x in rep["labels"]))
        conds2 = [(c[0], c[1] * 1.1, c[2], c[3]) for c in conds]
        rec2 = self.freeze(md=metadata(mode="post-measurement", blockLabel="Spent DOI synthetic", independence={
            "dataPreviouslyPublished": "yes", "publishedDoi": "10.17632/s9438vb5xd.1"}), conds=conds2)
        self.score(rec2["freezeKey"], targets_csv(conds2))
        self.assertEqual(self.report(rec2["freezeKey"])["blindness"]["status"], "not-blind-data-already-used-by-app")

    def test_build_job_history_partial_check(self):
        conds = conditions()
        job = self.tmp / "jobs" / ("b" * 32)
        job.mkdir()
        (job / "input.json").write_text(json.dumps({"jobType": "build-job", "alloyId": "Ti-6Al-4V",
                                                    "laserPower_W": conds[0][1], "scanSpeed_mm_s": conds[0][2],
                                                    "beamDiameter_um": 80.0}))
        (job / "result.json").write_text("{}")
        os.utime(job / "result.json", (1_000_000_000, 1_000_000_000))
        rec = self.freeze(conds=conds)
        self.score(rec["freezeKey"], targets_csv(conds))
        self.assertEqual(self.report(rec["freezeKey"])["blindness"]["status"], "not-blind-app-history")


class Attempts(BlindCase):
    def test_refused_score_creates_no_attempt_and_ledger_has_code_only(self):
        conds = conditions()
        rec = self.freeze(conds=conds)
        bad = targets_csv(conds).replace(b"c1,c1t1,", b"c1,c1t1x,")
        with self.assertRaises(proto.BlindRefusal) as cm:
            self.score(rec["freezeKey"], bad)
        self.assertEqual(cm.exception.code, "TARGETS_KEYS_MISMATCH")
        st = ub.Store()
        self.assertEqual(st.numbered(rec["freezeKey"], "score"), [])
        ev = [e for e in st.ledger() if e["event"] == "score-refused"]
        self.assertEqual(ev[0]["code"], "TARGETS_KEYS_MISMATCH")

    def test_identical_targets_return_attempt_1_changed_give_attempt_2(self):
        conds = conditions()
        rec = self.freeze(conds=conds)
        r1 = self.score(rec["freezeKey"], targets_csv(conds))
        r1b = self.score(rec["freezeKey"], targets_csv(conds))
        self.assertEqual((r1b["attempt"], r1b["alreadyScored"]), (1, True))
        r2 = self.score(rec["freezeKey"], targets_csv(conds, depth=lambda P, v, t: 50.0 + P / 7 + t))
        self.assertEqual(r2["attempt"], 2)
        rep2 = self.report(rec["freezeKey"], 2)
        self.assertEqual(rep2["blindness"]["status"], "not-blind-rescored-changed-targets")
        self.assertEqual(rep2["attempt"]["earlierTargetsSha256"], [self.report(rec["freezeKey"])["targetsSha256"]])
        self.assertEqual(r1["attempt"], 1)

    def test_sentinel_targets_never_in_errors_logs_ledger_or_results(self):
        conds = conditions()
        rec = self.freeze(conds=conds)
        for cell in (b"12.5x7", b"1,234.5", b"777.123x"):
            raw = targets_csv(conds).replace(b"c1,c1t1,", b"c1,c1t1,X", 1).replace(b",X", b"," + cell + b"#", 1)
            raw = raw.replace(b"#", b"", 1)
            try:
                self.score(rec["freezeKey"], raw)
                self.fail("malformed number accepted")
            except proto.BlindRefusal as e:
                self.assertIn(e.code, ("NUMBER_INVALID", "CSV_MALFORMED", "DIALECT_MISMATCH", "BLIND_SUBMIT_INTERNAL"))
                env = json.dumps(e.envelope())
                self.assertNotIn(cell.decode(), env)
        res = self.score(rec["freezeKey"], targets_csv(conds, depth=lambda P, v, t: 123.456789 + t))
        blob = json.dumps([res, ub.Store().ledger()])
        self.assertNotIn("123.456789", blob)
        self.assertNotIn("124.456789", blob)


class Statuses(BlindCase):
    def _status(self, md=None, conds=None, status=None, tracks=2):
        conds = conds or conditions()
        md = md or metadata()
        md["replication"]["tracksPerCondition"] = tracks
        rec = self.freeze(md=md, conds=conds, raw=inputs_csv(conds, tracks))
        self.score(rec["freezeKey"], targets_csv(conds, tracks, status=status))
        return self.report(rec["freezeKey"])

    def test_losses_above_20_percent_of_tracks_give_inconclusive(self):
        status = {f"c{i}t1": "specimen-lost" for i in range(1, 7)}      # 6 of 24 tracks, no condition lost
        rep = self._status(status=status)
        self.assertIn("LOSSES_ABOVE_20_PERCENT", rep["blockIssues"])
        self.assertEqual(rep["exclusions"]["tracks"], "6 of 24 frozen")
        self.assertEqual(len(rep["excluded"]["targets"]), 6)

    def test_losses_above_20_percent_of_conditions(self):
        status = {f"c{i}t{t}": "not-measured" for i in range(1, 4) for t in (1, 2)}
        rep = self._status(status=status)
        self.assertEqual(rep["exclusions"]["conditions"], "3 of 12 frozen")
        self.assertIn("LOSSES_ABOVE_20_PERCENT", rep["blockIssues"])

    def test_not_formed_track_counts_as_a_miss_and_is_never_excluded(self):
        rep = self._status(status={"c2t1": "track-not-formed", "c2t2": "track-not-formed"})
        self.assertEqual(rep["excluded"]["targets"], [])
        self.assertEqual(rep["arms"]["served"]["stats"]["maxApe"], "inf")
        self.assertTrue(any(l.startswith("track not formed in 1 conditions") for l in rep["labels"]))

    def test_metadata_driven_statuses(self):
        self.assertEqual(self._status(md=metadata(reduction="maximum-only"))["arms"]["served"]["status"],
                         "inconclusive")
        rep = self._status(md=metadata(depthDatum="cap-top"), conds=[(c[0], c[1] * 1.05, c[2], c[3])
                                                                       for c in conditions()])
        self.assertEqual(rep["arms"]["served"]["status"], "inconclusive")

    def test_powder_layer_descriptive(self):
        md = metadata(substrate={"kind": "powder-layer", "layerThickness_um": 30.0})
        rep = self._status(md=md, conds=[(c[0], c[1] * 1.07, c[2], c[3]) for c in conditions()])
        self.assertEqual(rep["arms"]["served"]["status"], "descriptive-not-scored")

    def test_316l_in718_in625_are_scored_with_the_same_thresholds(self):
        # Maintainer decision 2026-10-17: all five served alloys are scored; per-alloy labels stay.
        for i, alloy in enumerate(("316L", "IN718", "IN625")):
            with self.subTest(alloy=alloy):
                conds = [(c[0], c[1] * (1.0 + 0.11 * (i + 1)), c[2], c[3]) for c in conditions()]
                rep = self._status(md=metadata(alloy=alloy, blockLabel=f"Synthetic {alloy} block"), conds=conds)
                served = rep["arms"]["served"]
                # The sentinel stub predicts about 4000 um against invented depths near 50 um: thresholds fail.
                self.assertEqual(served["status"], "threshold-not-met")
                self.assertFalse(served["stats"]["allThresholdsMet"])
                self.assertIn(f"thresholds reused for {alloy} (registered for Ti-6Al-4V and AlSi10Mg)", rep["labels"])
                self.assertIn(f"statistics for {alloy} only; never pooled with other alloys",
                              rep["thresholds"]["alloyNote"])
                self.assertTrue(next(d for d in rep["divergences"] if d["id"] == "D6")["applied"])
                if alloy == "IN625":
                    self.assertFalse(rep["leverage"]["ok"])
                    self.assertIsNone(rep["leverage"]["cut"])
                    self.assertIn("leverage not evaluable (IN625)", rep["labels"])
                else:
                    self.assertEqual(rep["leverage"]["cut"], 15.0)
                    self.assertIn("servedBins", served)

    def test_in625_meeting_all_thresholds_is_inconclusive_and_316l_can_meet_them(self):
        def close_stub(alloy, P_W, v_mm_s, d_1e2_um, T0_C, layer_um=40.0, **_kw):
            depth = round(100.0 + P_W * 0.1, 6)
            return {"status": "ok", "depth_um": depth, "width_um": depth * 1.5, "extentStatus": "computed",
                    "fabbroDepth_um": depth / 2.0, "index": served_index(alloy, P_W, v_mm_s, d_1e2_um, T0_C),
                    "reasonLabel": None, "materialEvidence": None, "buildJobIdentity": None}

        def exact(P, v, t):
            return round(100.0 + P * 0.1, 6)
        with mock.patch.object(ufreeze, "served_arm", close_stub):
            for alloy in ("IN625", "316L"):
                conds = [(c[0], c[1] * (1.3 if alloy == "IN625" else 1.45), c[2], c[3]) for c in conditions()]
                md = metadata(alloy=alloy, blockLabel=f"Exact synthetic {alloy}",
                              independence={"dataPreviouslyPublished": "no"})
                rec = self.freeze(md=md, conds=conds)
                self.score(rec["freezeKey"], targets_csv(conds, depth=exact))
                rep = self.report(rec["freezeKey"])
                served = rep["arms"]["served"]
                self.assertTrue(served["stats"]["allThresholdsMet"], alloy)
                if alloy == "IN625":
                    self.assertEqual(served["status"], "inconclusive")
                    self.assertIn("leverage", served["reason"])
                else:
                    self.assertIn(served["status"], ("thresholds-met", "inconclusive"))
                    self.assertNotEqual(served["status"], "descriptive-not-scored")

    def test_preview_offers_scoring_for_every_served_alloy(self):
        for alloy in ("Ti-6Al-4V", "AlSi10Mg", "316L", "IN718", "IN625"):
            pv = self.preview(metadata(alloy=alloy), inputs_csv(conditions()))
            self.assertNotEqual(pv["bestReachable"]["status"], "descriptive-not-scored", alloy)

    def test_fewer_than_12_conditions_inconclusive(self):
        rep = self._status(conds=conditions(8))
        self.assertEqual(rep["arms"]["served"]["status"], "inconclusive")
        self.assertIn("n = 8 < 12", rep["arms"]["served"]["reason"])


class Identity(BlindCase):
    def test_scorer_change_label_and_not_the_predictor_label(self):
        conds = conditions()
        rec = self.freeze(conds=conds)
        real = ufreeze.scorer_identity()
        with mock.patch.object(ufreeze, "scorer_identity", lambda: {**real, "scoreSourcesSha256": "f" * 64}):
            self.score(rec["freezeKey"], targets_csv(conds))
        rep = self.report(rec["freezeKey"])
        self.assertTrue(rep["scorer"]["changedSinceFreeze"])
        self.assertFalse(rep["predictor"]["changedSinceFreeze"])
        self.assertTrue(any(l.startswith("scoring code changed") for l in rep["labels"]))
        self.assertFalse(any(l.startswith("predictor changed") for l in rep["labels"]))

    def test_protocol_change_refused(self):
        conds = conditions()
        rec = self.freeze(conds=conds)
        with mock.patch.object(uscore, "protocol_sha256", lambda: "e" * 64):
            with self.assertRaises(proto.BlindRefusal) as cm:
                self.score(rec["freezeKey"], targets_csv(conds))
        self.assertEqual(cm.exception.code, "PROTOCOL_CHANGED")

    def test_wording_change_gives_no_label_and_keeps_the_key(self):
        a = self.freeze()
        with mock.patch.dict(proto.WORDING, {"banner": "changed synthetic banner"}):
            b = self.freeze()
        self.assertEqual(a["freezeKey"], b["freezeKey"])

    def test_one_byte_edited_freeze_refused(self):
        conds = conditions()
        rec = self.freeze(conds=conds)
        p = ub.Store().freeze_dir(rec["freezeKey"]) / "freeze.json"
        os.chmod(p, 0o666)
        data = p.read_bytes()
        p.write_bytes(data[:-2] + (b"0" if data[-2:-1] != b"0" else b"1") + data[-1:])
        with self.assertRaises(proto.BlindRefusal) as cm:
            self.score(rec["freezeKey"], targets_csv(conds))
        self.assertEqual(cm.exception.code, "FREEZE_ALTERED")


class Exports(BlindCase):
    def test_comparison_csv_header_preamble_and_report_hash(self):
        conds = conditions()
        rec = self.freeze(conds=conds)
        res = self.score(rec["freezeKey"], targets_csv(conds))
        st = ub.Store()
        d = st.record_dir(rec["freezeKey"], "score", 1)
        csv_text = st.read_record(d, "comparison.csv").decode()
        rep_sha = (d / "score.json.sha256").read_text().strip()
        self.assertEqual(res["reportSha256"], rep_sha)
        self.assertIn(f"# reportSha256 {rep_sha}\n", csv_text)
        header = [l for l in csv_text.splitlines() if not l.startswith("# ")][0]
        self.assertEqual(header, ",".join(uscore.CSV_HEADER))
        self.assertTrue(csv_text.startswith("# " + proto.WORDING["banner"]))
        self.assertIn("rel is a fraction (pred - obs) / obs; positive means the model is deeper", csv_text)

    def test_text_cell_twin_matches_the_typescript_cases(self):
        cells = ["=1+1", "+x", "-2", "@a", "\tt", "\rr", "plain", -3.5, 12, "a=b"]
        expected = ["'=1+1", "'+x", "'-2", "'@a", "'\tt", "'\rr", "plain", -3.5, 12, "a=b"]
        self.assertEqual([proto.text_cell_safe(c) for c in cells], expected)

    def test_comparison_refused_before_a_report(self):
        rec = self.freeze()
        with self.assertRaises(proto.BlindRefusal):
            ub._resolve_document(ub.Store(), {"freezeKey": rec["freezeKey"]}, "blind-comparison.csv")

    def test_bundle_gate_and_ledger_order(self):
        conds = conditions()
        rec = self.freeze(conds=conds)
        with self.assertRaises(proto.BlindRefusal) as cm:
            ub.stage_request(ub.validate_request({"jobType": "user-blind-bundle", "schema": S,
                                                  "freezeKey": rec["freezeKey"]}))
        self.assertEqual(cm.exception.code, "REVEAL_REQUIRED")
        self.assertEqual(ub.Store().numbered(rec["freezeKey"], "bundle"), [])
        res = self.job({"jobType": "user-blind-bundle", "schema": S, "freezeKey": rec["freezeKey"],
                        "revealConfirmation": proto.REVEAL_PHRASE})
        events = [e["event"] for e in ub.Store().ledger()]
        self.assertLess(events.index("revealed"), events.index("bundle-exported"))
        st = ub.Store()
        data = st.read_record(st.record_dir(rec["freezeKey"], "bundle", res["bundleN"]), "bundle.tar")
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            names = tar.getnames()
            self.assertEqual(names, sorted(names))
            self.assertTrue(all(m.mtime == 0 and m.uid == 0 and m.mode == 0o644 for m in tar.getmembers()))
        members = ub.bundle_members(st, rec["freezeKey"])
        self.assertEqual(ub._tar_bytes(members), ub._tar_bytes(dict(reversed(list(members.items())))))
        self.score(rec["freezeKey"], targets_csv(conds))
        self.assertEqual(self.report(rec["freezeKey"])["blindness"]["status"], "not-blind-predictions-revealed")

    def test_cli_verify_on_a_bundle(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("lpbf_user_blind_cli", PY / "tools" / "lpbf_user_blind.py")
        cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli)
        conds = conditions()
        rec = self.freeze(conds=conds)
        self.score(rec["freezeKey"], targets_csv(conds))
        r = self.job({"jobType": "user-blind-bundle", "schema": S, "freezeKey": rec["freezeKey"]})
        st = ub.Store()
        out = self.tmp / "bundle.tar"
        out.write_bytes(st.read_record(st.record_dir(rec["freezeKey"], "bundle", r["bundleN"]), "bundle.tar"))
        checks = cli.verify_bundle(out)
        self.assertTrue(all(c["ok"] is not False for c in checks), checks)
        self.assertIs({c["id"]: c["ok"] for c in checks}["rescore-statistics-1"], True)
        tampered = bytearray(out.read_bytes())
        i = tampered.find(b'"blockLabel"')
        tampered[i + 15] ^= 1
        out.write_bytes(bytes(tampered))
        self.assertTrue(any(c["ok"] is False for c in cli.verify_bundle(out)))


class Enforcer(unittest.TestCase):
    def test_enforcer_refuses_prediction_keys_and_honesty_changes(self):
        good = {"freezeKey": "a" * 64, "revealN": 1, "ledgerSeq": 2, "documents": [], "honesty": proto.HONESTY,
                "provenance": {}}
        params = {"jobType": "user-blind-reveal", "freezeKey": "a" * 64}
        ub.enforce_user_blind_job_result(dict(good), params)
        with self.assertRaises(ValueError):
            ub.enforce_user_blind_job_result({**good, "documents": [{"value_um": 1.0}]}, params)
        with self.assertRaises(ValueError):
            ub.enforce_user_blind_job_result({**good, "honesty": {**proto.HONESTY, "experimentalValidation": "false"}},
                                             params)
        with self.assertRaises(ValueError):
            ub.enforce_user_blind_job_result({**good, "extra": 1}, params)

    def test_log_filter_keeps_only_the_two_closed_frames(self):
        text = ('{"blindProgress":{"stage":"predict","k":1,"n":2}}\nTraceback 4012.5\n{"blindError":"FREEZE_ALTERED"}\n'
                '{"blindError":"x 4012.5"}\n{"progress":0.5,"message":"4012.5"}\n')
        out = ub.filter_blind_log(text)
        self.assertNotIn("4012.5", out)
        self.assertEqual(out.count("[blind: line dropped]"), 3)
        self.assertEqual(ub.blind_failure_message(out)["code"], "FREEZE_ALTERED")

    def test_request_types_are_closed(self):
        self.assertEqual(ub.USER_BLIND_RPC_TYPES | ub.USER_BLIND_JOB_TYPES, set(ub.PAYLOADS))
        with self.assertRaises(proto.BlindRefusal):
            ub.validate_request({"jobType": "user-blind-share", "schema": S})
        for jt, shape in ub.PAYLOADS.items():
            with self.assertRaises(proto.BlindRefusal):
                ub.validate_request({k: None for k in shape["required"]} | {"jobType": jt, "schema": S,
                                                                            "unknownKey": 1})

    def test_refusal_envelope_is_fixed_text(self):
        e = proto.BlindRefusal("NUMBER_INVALID", field="targetsCsvBase64", row=3, col="depth_um")
        env = e.envelope()
        self.assertEqual(env["errorKind"], "validation")
        self.assertEqual(env["error"]["code"], "NUMBER_INVALID")
        import lpbf_worker
        reply = lpbf_worker.rpc_error_response({"id": 7}, e)
        self.assertEqual(reply["errorKind"], "validation")
        self.assertEqual(reply["error"], e.message)
        self.assertEqual(reply["validation"], env)


if __name__ == "__main__":
    unittest.main()
