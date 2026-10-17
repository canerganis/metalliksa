"""Local store of the user blind test: layout, OS lock, directory commits with sidecars, hash-chained ledger.

Research hub spec section 3.5. Root: `METALLIKSA_USER_BLIND_ROOT`, default `<repo>/.runtime/user-blind` (gitignored).

Rules kept here:
  * Every record is committed only as a directory holding the record and its `.sha256` sidecar, written and fsynced
    in `.staging/<random>/` and renamed into place; the rename is the commit point. No record file is created in place.
  * Uploads are content addressed (`uploads/<sha256>.<kind>`), created exclusively; identical bytes reuse the file.
  * Ledger events follow their commit point, under the lock. The ledger never holds a measured value, a prediction or
    free text.
  * Reconciliation at the start of every mutation, under the lock: a committed record without its event gets the event
    (marked `reconciled`), a trailing partial ledger line is cut, the condition index is rebuilt when it disagrees.
  * The lock is OS held (msvcrt on Windows, flock elsewhere), released by the OS when the holder dies. `store.json`
    records the lock domain; a process of the other domain may read but never mutate (`STORE_LOCK_DOMAIN`).
  * State gates read committed files, never the ledger.

No delete API. Readers on the estimate RPC see committed records only.
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import secrets
import stat
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from lpbf_user_blind_protocol import CAPS, STORE_SCHEMA, BlindRefusal, canonical_bytes, canonical_sha256

REPO_ROOT = Path(__file__).resolve().parent.parent
ROOT_ENV = "METALLIKSA_USER_BLIND_ROOT"
UPLOAD_KINDS = ("metadata.json", "inputs.csv", "targets.csv")
_HEX = re.compile(r"^[0-9a-f]{64}$")
LOCK_WAIT_S = 10.0
LOOPBACK = ("127.0.0.1", "::1", "localhost", "[::1]")


def _fault(step):
    """Test-only fault hook: tests replace this module-level no-op in a spawned child. Never an env switch."""
    return None


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def lock_domain():
    return "windows" if os.name == "nt" else "posix"


def default_root():
    override = os.environ.get(ROOT_ENV)
    return Path(override) if override else REPO_ROOT / ".runtime" / "user-blind"


def read_only():
    return os.environ.get("METALLIKSA_READ_ONLY", "").strip().lower() == "true"


def shared_host():
    host = os.environ.get("METALLIKSA_HOST", "").strip()
    if not host or host in LOOPBACK:
        return False
    return os.environ.get("METALLIKSA_USER_BLIND_SINGLE_USER", "").strip().lower() != "true"


def _fsync_dir(path):
    if os.name == "nt":
        return
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_exclusive(path, data):
    with open(path, "xb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.chmod(path, stat.S_IREAD)


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def scorer_source_hashes(paths):
    """Canonical source sha256 of files by path (LF and CRLF hash alike), without importing them."""
    from lpbf_source_identity import canonical_source_bytes
    out = {}
    for p in paths:
        p = Path(p)
        rel = p.resolve().relative_to(REPO_ROOT).as_posix()
        out[rel] = sha256_bytes(canonical_source_bytes(rel, p.read_bytes()))
    return out


class Store:
    def __init__(self, root=None):
        self.root = Path(root) if root is not None else default_root()
        self._lock_file = None

    # ------------------------------------------------------------------ layout
    @property
    def ledger_path(self):
        return self.root / "ledger.jsonl"

    def freeze_dir(self, key):
        if not isinstance(key, str) or not _HEX.match(key):
            raise BlindRefusal("FREEZE_UNKNOWN", field="freezeKey")
        return self.root / "freezes" / key

    def info(self):
        """store.json contents, or None when the store was never created."""
        p = self.root / "store.json"
        if not p.is_file():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def ensure(self):
        """Create the layout and store.json (mutations only)."""
        for sub in ("uploads", "freezes", "index", ".staging"):
            (self.root / sub).mkdir(parents=True, exist_ok=True)
        p = self.root / "store.json"
        if not p.exists():
            doc = {"schema": STORE_SCHEMA, "storeId": secrets.token_hex(8), "createdAt": now_iso(),
                   "lockDomain": lock_domain()}
            try:
                _write_exclusive(p, canonical_bytes(doc) + b"\n")
            except FileExistsError:
                pass
        return self.info()

    # ------------------------------------------------------------------ guards
    def check_mutation_allowed(self):
        if read_only():
            raise BlindRefusal("STORE_READ_ONLY")
        if shared_host():
            raise BlindRefusal("STORE_SHARED_HOST")
        info = self.info()
        if info is not None and info.get("lockDomain") != lock_domain():
            raise BlindRefusal("STORE_LOCK_DOMAIN", domain=info.get("lockDomain"))

    def check_caps(self, extra_bytes=0):
        n = len(self.freeze_keys())
        if n >= CAPS["storeFreezes"]:
            raise BlindRefusal("STORE_FULL")
        if self.total_bytes() + extra_bytes > CAPS["storeBytes"]:
            raise BlindRefusal("STORE_FULL")

    def total_bytes(self):
        total = 0
        if not self.root.is_dir():
            return 0
        for dirpath, _dirs, files in os.walk(self.root):
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(dirpath, f))
                except OSError:
                    pass
        return total

    # ------------------------------------------------------------------ lock
    @contextlib.contextmanager
    def lock(self, wait_s=LOCK_WAIT_S):
        self.check_mutation_allowed()
        self.ensure()
        self.check_mutation_allowed()
        f = open(self.root / "store.lock", "a+b")
        deadline = time.monotonic() + wait_s
        while True:
            try:
                if os.name == "nt":
                    import msvcrt
                    f.seek(0)
                    msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    f.close()
                    raise BlindRefusal("STORE_LOCKED") from None
                time.sleep(0.05)
        _fault("after-lock")
        try:
            self.reconcile()
            yield self
        finally:
            try:
                if os.name == "nt":
                    import msvcrt
                    f.seek(0)
                    msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(f, fcntl.LOCK_UN)
            finally:
                f.close()

    def try_lock_once(self):
        """RPC readers: one non-blocking attempt (spec 3.2.1). Returns True when free; never waits."""
        p = self.root / "store.lock"
        if not p.exists():
            return True
        try:
            f = open(p, "a+b")
        except OSError:
            return False
        try:
            if os.name == "nt":
                import msvcrt
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                fcntl.flock(f, fcntl.LOCK_UN)
            return True
        except OSError:
            return False
        finally:
            f.close()

    # ------------------------------------------------------------------ uploads
    def put_upload(self, data, kind):
        """Content-addressed upload (exclusive create; identical bytes reuse the file). Returns the sha256."""
        if kind not in UPLOAD_KINDS:
            raise ValueError("unknown upload kind")
        digest = sha256_bytes(data)
        path = self.root / "uploads" / f"{digest}.{kind}"
        try:
            _write_exclusive(path, data)
        except FileExistsError:
            if sha256_bytes(path.read_bytes()) != digest:
                raise BlindRefusal("FREEZE_ALTERED") from None
        return digest

    def get_upload(self, digest, kind):
        if not isinstance(digest, str) or not _HEX.match(digest) or kind not in UPLOAD_KINDS:
            raise BlindRefusal("FREEZE_UNKNOWN")
        path = self.root / "uploads" / f"{digest}.{kind}"
        if not path.is_file():
            raise BlindRefusal("FREEZE_UNKNOWN")
        data = path.read_bytes()
        if sha256_bytes(data) != digest:
            raise BlindRefusal("FREEZE_ALTERED")
        return data

    # ------------------------------------------------------------------ staging and commit
    def stage(self, files):
        """Write {name: bytes} with sidecars into a fresh staging directory (fsynced). Returns the directory."""
        d = self.root / ".staging" / secrets.token_hex(12)
        d.mkdir(parents=True)
        for name, data in files.items():
            _write_exclusive(d / name, data)
            _write_exclusive(d / f"{name}.sha256", (sha256_bytes(data) + "\n").encode("ascii"))
        _fsync_dir(d)
        _fault("after-staging-write")
        return d

    def commit(self, staging, target):
        """Rename the staging directory to `target` (the commit point). Refuses an existing target."""
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise FileExistsError(str(target))
        os.rename(staging, target)
        _fsync_dir(target.parent)
        _fault("after-rename")

    def incomplete_staging(self):
        d = self.root / ".staging"
        return sorted(p.name for p in d.iterdir()) if d.is_dir() else []

    @staticmethod
    def read_record(directory, name):
        """Bytes of a committed record after its sidecar check; FREEZE_ALTERED on mismatch."""
        path, side = directory / name, directory / f"{name}.sha256"
        if not path.is_file() or not side.is_file():
            raise BlindRefusal("FREEZE_ALTERED")
        data = path.read_bytes()
        if side.read_text(encoding="ascii").strip() != sha256_bytes(data):
            raise BlindRefusal("FREEZE_ALTERED")
        return data

    # ------------------------------------------------------------------ committed records
    def freeze_keys(self):
        d = self.root / "freezes"
        if not d.is_dir():
            return []
        return sorted(p.name for p in d.iterdir() if _HEX.match(p.name) and (p / "freeze.json").is_file())

    def numbered(self, key, prefix):
        d = self.freeze_dir(key) if prefix != "bundle" else self.freeze_dir(key) / "bundles"
        if not d.is_dir():
            return []
        out = []
        for p in d.iterdir():
            m = re.fullmatch(prefix + r"-([1-9][0-9]{0,5})", p.name)
            if m and p.is_dir():
                out.append(int(m.group(1)))
        return sorted(out)

    def record_dir(self, key, prefix, n):
        base = self.freeze_dir(key)
        return (base / "bundles" / f"bundle-{n}") if prefix == "bundle" else base / f"{prefix}-{n}"

    def reveal_or_score_exists(self, key):
        return bool(self.numbered(key, "reveal") or self.numbered(key, "score"))

    def committed_records(self):
        """[(event, freezeKey, relative record path)] from the committed directories."""
        out = []
        for key in self.freeze_keys():
            out.append(("frozen", key, f"freezes/{key}"))
            for n in self.numbered(key, "reveal"):
                out.append(("revealed", key, f"freezes/{key}/reveal-{n}"))
            for n in self.numbered(key, "score"):
                out.append(("scored", key, f"freezes/{key}/score-{n}"))
            for n in self.numbered(key, "bundle"):
                out.append(("bundle-exported", key, f"freezes/{key}/bundles/bundle-{n}"))
        return out

    # ------------------------------------------------------------------ ledger
    def ledger(self, *, tolerate_partial=True):
        """Complete ledger entries. A trailing line without a newline (a killed append) is ignored."""
        p = self.ledger_path
        if not p.is_file():
            return []
        raw = p.read_bytes()
        lines = raw.split(b"\n")
        if lines and lines[-1] == b"":
            lines = lines[:-1]
        elif lines and not tolerate_partial:
            raise ValueError("partial trailing ledger line")
        else:
            lines = lines[:-1]
        return [json.loads(l) for l in lines]

    @staticmethod
    def entry_hash(entry):
        return canonical_sha256({k: v for k, v in entry.items() if k != "entryHash"})

    def verify_chain(self, entries=None):
        entries = self.ledger() if entries is None else entries
        prev = None
        for i, e in enumerate(entries):
            if e.get("seq") != i + 1 or e.get("prevEntryHash") != prev or e.get("entryHash") != self.entry_hash(e):
                return {"ok": False, "brokenAt": i + 1}
            prev = e["entryHash"]
        return {"ok": True, "brokenAt": None, "n": len(entries)}

    def append(self, event, *, freeze_key=None, job_id=None, record=None, hashes=None, extra=None):
        """Append one event (caller holds the lock). Returns the entry."""
        entries = self.ledger()
        prev = entries[-1]["entryHash"] if entries else None
        entry = {"seq": len(entries) + 1, "at": now_iso(), "event": event, "freezeKey": freeze_key,
                 "jobId": job_id, "record": record, "hashes": dict(hashes or {}), "prevEntryHash": prev}
        if extra:
            entry.update(extra)
        entry["entryHash"] = self.entry_hash(entry)
        line = canonical_bytes(entry) + b"\n"
        with open(self.ledger_path, "ab") as f:
            f.write(line[:len(line) // 2])
            _fault("during-ledger-append")
            f.write(line[len(line) // 2:])
            f.flush()
            os.fsync(f.fileno())
        _fault("after-ledger-append")
        return entry

    def reconcile(self):
        """Caller holds the lock. Restore the invariants after a killed mutation (spec 3.5 item 4)."""
        p = self.ledger_path
        if p.is_file():
            raw = p.read_bytes()
            if raw and not raw.endswith(b"\n"):
                keep = raw[:raw.rfind(b"\n") + 1]
                with open(p, "r+b") as f:
                    f.truncate(len(keep))
                    f.flush()
                    os.fsync(f.fileno())
                self.append("reconciled", extra={"restored": "partial-ledger-line-cut"})
        entries = self.ledger()
        recorded = {e.get("record") for e in entries if e.get("record")}
        for event, key, rel in self.committed_records():
            if rel not in recorded:
                self.append(event, freeze_key=key, record=rel, extra={"reconciled": True})
        self.rebuild_index_if_needed()

    # ------------------------------------------------------------------ condition index (derived data)
    def index_path(self):
        return self.root / "index" / "conditions.jsonl"

    def index_entries(self):
        p = self.index_path()
        if not p.is_file():
            return []
        out = []
        for line in p.read_bytes().split(b"\n"):
            if line.strip():
                try:
                    out.append(json.loads(line))
                except ValueError:
                    return None
        return out

    def _derived_index(self):
        out = []
        for key in self.freeze_keys():
            try:
                doc = json.loads(self.read_record(self.freeze_dir(key), "freeze.json"))
            except (BlindRefusal, ValueError, OSError):
                continue
            out.append(index_entry(doc))
        return out

    def rebuild_index_if_needed(self):
        current = self.index_entries()
        derived = self._derived_index()
        if current is not None and sorted(map(canonical_sha256, current)) == sorted(map(canonical_sha256, derived)):
            return False
        (self.root / "index").mkdir(parents=True, exist_ok=True)
        tmp = self.root / "index" / f".conditions.{secrets.token_hex(4)}.tmp"
        tmp.write_bytes(b"".join(canonical_bytes(e) + b"\n" for e in derived))
        os.replace(tmp, self.index_path())
        return True

    def append_index(self, entry):
        with open(self.index_path(), "ab") as f:
            data = canonical_bytes(entry) + b"\n"
            f.write(data[:len(data) // 2])
            _fault("during-index-append")
            f.write(data[len(data) // 2:])
            f.flush()
            os.fsync(f.fileno())


def index_entry(freeze_doc):
    return {"freezeKey": freeze_doc["freezeKey"], "alloy": freeze_doc["metadata"]["alloy"],
            "tuples": sorted({(c["P_W"], c["v_mm_s"], c["d_1e2_um"]) for c in freeze_doc["conditions"]})}


def tuples_match(a, b, rel=0.01):
    """Same setting at the 1 % rule for power, speed and 1/e2 beam."""
    return all(abs(x - y) <= rel * max(abs(x), abs(y)) for x, y in zip(a, b))
