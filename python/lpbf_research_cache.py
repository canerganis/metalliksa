"""P8 research route: process-local cache, canonical keys, code identity and priority (integration contract 2026-10-15,
sections 3.6 and 3.7).

Research only: no served module may import this file (guard R-ISO-1). The cache is a module-level LRU inside the one
research lane process (or one ad-hoc process); it survives between requests because imported modules stay in
sys.modules, it is empty after a daemon restart, a lane recycle and in every ad-hoc spawn, and it is never persisted
or shared with served code. It is never held in the dispatch script, whose namespace is fresh per request.

Code identity: the research implementation hash (RESEARCH_SOURCE_FILES under RESEARCH_VERSION, canonical-v3 framing of
lpbf_source_identity) and the served implementation fingerprint (lpbf_simulation.implementation_fingerprint) are
recorded when this module is imported. Every request checks them again; a live IPC worker keeps old modules in
sys.modules, so a difference refuses the request with RESEARCH_CODE_STALE. Phase B measured a full served rehash at
about 26 to 37 ms per request (above the contract's 20 ms threshold), so a stat gate (mtime_ns and size of every
listed file) decides when to rehash; a rehash that reproduces the import-time hashes re-arms the gate.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import threading
import time
import uuid
from collections import OrderedDict
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

import lpbf_simulation
from lpbf_source_identity import fingerprint_sources

PYTHON_DIR = Path(__file__).resolve().parent

RESEARCH_VERSION = "p8-research-impl-v1"
RESEARCH_SCHEMA_VERSION = "p8-research-v3"
# Contract 3.2: the research runtime modules. Phase C adds lpbf_research_manifest.py and lpbf_research_arm.py here
# and regenerates the research pin (python/lpbf_research_identity_pin.py --write).
RESEARCH_SOURCE_FILES = (
    "lpbf_research_models.py",
    "lpbf_research_context.py",
    "lpbf_research_cache.py",
    "lpbf_research_codes.py",
    "lpbf_research_manifest.py",
    "lpbf_research_arm.py",
)

# Contract 3.6 and 13.13: two complete requests at the 80-arm cap of 5 banded modules plus aggregates
# (2 x (80 x 5 + 5 + 1) = 812) rounded to 1024 entries, and 128 MiB of canonical text.
MAX_ENTRIES = 1024
MAX_BYTES = 128 * 1024 * 1024
STALE_REHASH_THRESHOLD_MS = 20.0


# --- Canonical encoding (contract 3.6) ---------------------------------------------------------------------------

class CanonicalEncodeError(ValueError):
    """A value the canonical encoding refuses (NaN, infinity, an unsupported type, a non-string key)."""


def _encode(value: Any, out: list) -> None:
    if value is None:
        out.append("null")
    elif value is True:
        out.append("true")
    elif value is False:
        out.append("false")
    elif isinstance(value, int):
        out.append(str(int(value)))
    elif isinstance(value, float):
        if not math.isfinite(value):
            raise CanonicalEncodeError(f"non-finite float {value!r} refused by the canonical encoding")
        out.append(value.hex())
    elif isinstance(value, str):
        out.append(_json_string(value))
    elif isinstance(value, (list, tuple)):
        out.append("[")
        for i, item in enumerate(value):
            if i:
                out.append(",")
            _encode(item, out)
        out.append("]")
    elif isinstance(value, Mapping):
        keys = list(value.keys())
        if not all(isinstance(k, str) for k in keys):
            raise CanonicalEncodeError("canonical mapping keys must be strings")
        out.append("{")
        for i, key in enumerate(sorted(keys)):
            if i:
                out.append(",")
            out.append(_json_string(key))
            out.append(":")
            _encode(value[key], out)
        out.append("}")
    else:
        raise CanonicalEncodeError(f"unsupported type {type(value).__name__} in a canonical value")


def _json_string(text: str) -> str:
    return json.dumps(text, ensure_ascii=False)


def canonical(value: Any) -> str:
    """Sorted keys, floats as float.hex (bare token, so a float never equals a string), integers in decimal,
    strings as given (JSON-quoted), null, true, false. NaN and infinity are refused."""
    out: list = []
    _encode(value, out)
    return "".join(out)


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


# --- Code identity and the stale check (contract 3.6 rule 1) -----------------------------------------------------

def research_implementation_sha256(root: Path = PYTHON_DIR) -> str:
    return fingerprint_sources(root, RESEARCH_SOURCE_FILES, RESEARCH_VERSION)


def served_implementation_fingerprint() -> str:
    return lpbf_simulation.implementation_fingerprint()


def _stat_key(path: Path) -> tuple:
    try:
        st = path.stat()
    except OSError:
        return ("missing",)
    return (st.st_mtime_ns, st.st_size)


class IdentityGuard:
    """Import-time code identity plus the per-request stale check.

    ``files`` are the paths whose bytes the two hashes read; their (mtime_ns, size) is the gate. When a stat
    differs, both hashes are recomputed; a difference from the import-time value makes the process stale for good
    (a stale worker is recycled, never un-staled), an equal rehash re-arms the gate with the new stats.
    """

    def __init__(self, research_hash: Callable[[], str], served_hash: Callable[[], str], files: Iterable[Path]):
        self._research_hash = research_hash
        self._served_hash = served_hash
        self._files = tuple(files)
        self._lock = threading.Lock()
        self._verified_stats = self._stats()
        self.research_sha256 = research_hash()
        self.served_fingerprint = served_hash()
        self._stale = False
        self.last_check: dict = {}

    def _stats(self) -> tuple:
        return tuple(_stat_key(p) for p in self._files)

    def identity(self) -> dict:
        return {"researchImplementationSha256": self.research_sha256,
                "servedImplementationFingerprint": self.served_fingerprint}

    def check(self, *, force_rehash: bool = False) -> dict:
        t0 = time.perf_counter()
        with self._lock:
            rehashed = False
            changed: list = []
            if not self._stale:
                stats = self._stats()
                if force_rehash or stats != self._verified_stats:
                    rehashed = True
                    try:
                        research, served = self._research_hash(), self._served_hash()
                    except (OSError, ValueError):
                        research = served = None
                    if research != self.research_sha256:
                        changed.append("researchImplementationSha256")
                    if served != self.served_fingerprint:
                        changed.append("servedImplementationFingerprint")
                    if changed:
                        self._stale = True
                    else:
                        self._verified_stats = stats
            result = {"stale": self._stale, "rehashed": rehashed, "changed": changed,
                      "elapsedMs": (time.perf_counter() - t0) * 1000.0}
            self.last_check = result
            return result


def _identity_files() -> tuple:
    research = [PYTHON_DIR / name for name in RESEARCH_SOURCE_FILES]
    served = [PYTHON_DIR / name for name in lpbf_simulation.IMPLEMENTATION_SOURCE_FILES]
    return tuple(research + served)


IDENTITY = IdentityGuard(research_implementation_sha256, served_implementation_fingerprint, _identity_files())


# --- Process-local LRU (contract 3.6) ----------------------------------------------------------------------------

class ResearchLRU:
    """Arm records and module aggregates, bounded by entry count and by the UTF-8 length of each entry's canonical
    text measured at insert. Values are deep-copied in and out, so no caller shares a mutable object with the cache.
    Only finite values are accepted (canonical refuses NaN and infinity)."""

    def __init__(self, max_entries: int = MAX_ENTRIES, max_bytes: int = MAX_BYTES):
        if max_entries < 1 or max_bytes < 1:
            raise ValueError("cache bounds must be positive")
        self.max_entries = max_entries
        self.max_bytes = max_bytes
        self._data: "OrderedDict[str, tuple]" = OrderedDict()
        self.total_bytes = 0
        self.stats = {"hits": 0, "misses": 0, "inserts": 0, "evictions": 0, "refusedOversize": 0}

    def __len__(self) -> int:
        return len(self._data)

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def keys(self) -> list:
        return list(self._data.keys())

    def get(self, key: str) -> Any:
        entry = self._data.get(key)
        if entry is None:
            self.stats["misses"] += 1
            return None
        self._data.move_to_end(key)
        self.stats["hits"] += 1
        return copy.deepcopy(entry[0])

    def put(self, key: str, value: Any) -> bool:
        size = len(canonical(value).encode("utf-8"))
        if size > self.max_bytes:
            self.stats["refusedOversize"] += 1
            return False
        old = self._data.pop(key, None)
        if old is not None:
            self.total_bytes -= old[1]
        self._data[key] = (copy.deepcopy(value), size)
        self.total_bytes += size
        self.stats["inserts"] += 1
        while len(self._data) > self.max_entries or self.total_bytes > self.max_bytes:
            _, (_, evicted_size) = self._data.popitem(last=False)
            self.total_bytes -= evicted_size
            self.stats["evictions"] += 1
        return True

    def clear(self) -> None:
        self._data.clear()
        self.total_bytes = 0


CACHE = ResearchLRU()
CACHE_INSTANCE_ID = uuid.uuid4().hex


# --- CPU priority (contract 3.7 item 6) --------------------------------------------------------------------------

_PRIORITY_STATE: str | None = None
_BELOW_NORMAL_PRIORITY_CLASS = 0x00004000


def lower_process_priority_once() -> str:
    """Lower this process's own CPU priority once: os.nice(10) on POSIX, BELOW_NORMAL_PRIORITY_CLASS on Windows.
    Returns the state; failures leave the priority unchanged and are reported, never raised."""
    global _PRIORITY_STATE
    if _PRIORITY_STATE is not None:
        return _PRIORITY_STATE
    try:
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.GetCurrentProcess.restype = wintypes.HANDLE
            kernel32.SetPriorityClass.argtypes = (wintypes.HANDLE, wintypes.DWORD)
            kernel32.SetPriorityClass.restype = wintypes.BOOL
            ok = kernel32.SetPriorityClass(kernel32.GetCurrentProcess(), _BELOW_NORMAL_PRIORITY_CLASS)
            _PRIORITY_STATE = "below-normal" if ok else "unchanged"
        else:
            os.nice(10)
            _PRIORITY_STATE = "nice+10"
    except Exception:
        _PRIORITY_STATE = "unchanged"
    return _PRIORITY_STATE
