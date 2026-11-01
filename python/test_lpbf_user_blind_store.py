"""Blind store: directory commits, sidecars, ledger chain, OS lock, guards (spec 3.5, 11.1 item 5). Synthetic bytes."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import lpbf_user_blind_protocol as proto
from lpbf_user_blind_store import Store, lock_domain

PY = Path(__file__).resolve().parent


def _rm(path):
    def onerror(func, p, _exc):
        os.chmod(p, 0o666)
        func(p)
    shutil.rmtree(path, onerror=onerror)


class StoreCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="blind-store-"))
        self.env = mock.patch.dict(os.environ, {"METALLIKSA_READ_ONLY": "", "METALLIKSA_HOST": "",
                                                "METALLIKSA_USER_BLIND_SINGLE_USER": ""})
        self.env.start()
        self.store = Store(self.tmp / "store")

    def tearDown(self):
        self.env.stop()
        _rm(self.tmp)

    def test_commit_refuses_an_existing_record_and_writes_only_via_staging(self):
        with self.store.lock() as st:
            d = st.stage({"reveal.json": b"{}"})
            target = st.root / "freezes" / ("a" * 64) / "reveal-1"
            st.commit(d, target)
            d2 = st.stage({"reveal.json": b"{}"})
            with self.assertRaises(FileExistsError):
                st.commit(d2, target)
        self.assertTrue((target / "reveal.json.sha256").is_file())
        self.assertEqual(len(self.store.incomplete_staging()), 1)

    def test_sidecar_verification(self):
        with self.store.lock() as st:
            d = st.stage({"x.json": b'{"a":1}'})
        self.assertEqual(Store.read_record(d, "x.json"), b'{"a":1}')
        os.chmod(d / "x.json", 0o666)
        (d / "x.json").write_bytes(b'{"a":2}')
        with self.assertRaises(proto.BlindRefusal) as cm:
            Store.read_record(d, "x.json")
        self.assertEqual(cm.exception.code, "FREEZE_ALTERED")

    def test_ledger_chain_and_one_byte_tamper(self):
        with self.store.lock() as st:
            for i in range(3):
                st.append("score-refused", freeze_key="b" * 64, hashes={"targets": str(i)}, extra={"code": "X"})
        self.assertTrue(self.store.verify_chain()["ok"])
        raw = self.store.ledger_path.read_bytes()
        i = raw.find(b'"targets":"1"')
        self.store.ledger_path.write_bytes(raw[:i + 11] + b"2" + raw[i + 12:])
        self.assertEqual(self.store.verify_chain()["brokenAt"], 2)

    def test_reconcile_cuts_a_partial_line_and_rebuilds_the_index(self):
        with self.store.lock() as st:
            st.append("score-refused", freeze_key="c" * 64, extra={"code": "X"})
        with open(self.store.ledger_path, "ab") as f:
            f.write(b'{"seq":2,"half')
        (self.store.root / "index" / "conditions.jsonl").write_bytes(b'{"broken')
        with self.store.lock():
            pass
        entries = self.store.ledger()
        self.assertEqual([e["event"] for e in entries], ["score-refused", "reconciled"])
        self.assertTrue(self.store.verify_chain()["ok"])
        self.assertEqual(self.store.index_entries(), [])

    def test_upload_reuse_and_content_address(self):
        self.store.ensure()
        a = self.store.put_upload(b"x,y\n1,2\n", "inputs.csv")
        b = self.store.put_upload(b"x,y\n1,2\n", "inputs.csv")
        self.assertEqual(a, b)
        self.assertEqual(self.store.get_upload(a, "inputs.csv"), b"x,y\n1,2\n")

    def test_read_only_shared_host_and_lock_domain_refusals(self):
        with mock.patch.dict(os.environ, {"METALLIKSA_READ_ONLY": "true"}):
            with self.assertRaises(proto.BlindRefusal) as cm:
                with self.store.lock():
                    pass
            self.assertEqual(cm.exception.code, "STORE_READ_ONLY")
        with mock.patch.dict(os.environ, {"METALLIKSA_HOST": "0.0.0.0"}):
            with self.assertRaises(proto.BlindRefusal) as cm:
                self.store.check_mutation_allowed()
            self.assertEqual(cm.exception.code, "STORE_SHARED_HOST")
        with mock.patch.dict(os.environ, {"METALLIKSA_HOST": "0.0.0.0", "METALLIKSA_USER_BLIND_SINGLE_USER": "true"}):
            self.store.check_mutation_allowed()
        self.store.ensure()
        info = self.store.info()
        p = self.store.root / "store.json"
        os.chmod(p, 0o666)
        other = "posix" if lock_domain() == "windows" else "windows"
        p.write_text(json.dumps({**info, "lockDomain": other}))
        with self.assertRaises(proto.BlindRefusal) as cm:
            self.store.check_mutation_allowed()
        self.assertEqual(cm.exception.code, "STORE_LOCK_DOMAIN")
        self.assertEqual(self.store.ledger(), [])            # reads still work

    def test_lock_released_when_the_holder_is_killed(self):
        self.store.ensure()
        code = ("import sys,time; sys.path.insert(0, sys.argv[1]); from lpbf_user_blind_store import Store\n"
                "s = Store(sys.argv[2])\n"
                "cm = s.lock(); cm.__enter__(); print('locked', flush=True); time.sleep(60)\n")
        child = subprocess.Popen([sys.executable, "-B", "-c", code, str(PY), str(self.store.root)],
                                 stdout=subprocess.PIPE, text=True)
        try:
            self.assertEqual(child.stdout.readline().strip(), "locked")
            with self.assertRaises(proto.BlindRefusal) as cm:
                with self.store.lock(wait_s=0.3):
                    pass
            self.assertEqual(cm.exception.code, "STORE_LOCKED")
            child.kill()
            child.wait(10)
            t = time.monotonic()
            with self.store.lock(wait_s=5):
                pass
            self.assertLess(time.monotonic() - t, 5)
        finally:
            if child.poll() is None:
                child.kill()
            child.stdout.close()

    def test_two_concurrent_reveals_get_distinct_numbers_and_one_chain(self):
        key = "d" * 64
        self.store.ensure()
        fd = self.store.root / "freezes" / key
        fd.mkdir(parents=True)
        (fd / "freeze.json").write_bytes(b"{}")
        (fd / "freeze.json.sha256").write_bytes(b"x\n")
        code = ("import sys; sys.path.insert(0, sys.argv[1]); import lpbf_user_blind as ub\n"
                "from lpbf_user_blind_store import Store\n"
                "ub._store = lambda: Store(sys.argv[2])\n"
                "for i in range(3): ub.reveal(Store(sys.argv[2]), sys.argv[3], None, via='cli')\n")
        procs = [subprocess.Popen([sys.executable, "-B", "-c", code, str(PY), str(self.store.root), key])
                 for _ in range(2)]
        for p in procs:
            self.assertEqual(p.wait(60), 0)
        self.assertEqual(self.store.numbered(key, "reveal"), [1, 2, 3, 4, 5, 6])
        self.assertTrue(self.store.verify_chain()["ok"])
        recs = [e["record"] for e in self.store.ledger() if e["event"] == "revealed"]
        self.assertEqual(len(recs), len(set(recs)))


if __name__ == "__main__":
    unittest.main()
