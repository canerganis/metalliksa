"""Research pin: python/lpbf_research_identity.expected (P8 integration contract 2026-10-15, 3.6 "Research pin").

The pin holds researchImplementationSha256, the canonical-v3 hash of lpbf_research_cache.RESEARCH_SOURCE_FILES under
RESEARCH_VERSION. R-ID-1 (python/test_lpbf_research_identity.py) checks it. A research code change regenerates it
deliberately, in the same commit as the change:

    python -B lpbf_research_identity_pin.py --write      (from python/)
    python -B lpbf_research_identity_pin.py --check

Modelled on lpbf_fingerprint_pin.py (one strict reader). This is the research pin, not the served fingerprint pin
python/lpbf_implementation_fingerprint.expected, and not a guarded path. Research only (prefix lpbf_research_); no
served module imports it, and it is not one of RESEARCH_SOURCE_FILES (tooling, not runtime).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

EXPECTED_RESEARCH_IDENTITY_FILE = Path(__file__).resolve().parent / "lpbf_research_identity.expected"
_PIN = re.compile(rb"([0-9a-f]{64})\r?\n")


def read_pinned_research_identity(path: Path = EXPECTED_RESEARCH_IDENTITY_FILE) -> str:
    """Return the pinned value; the file must be exactly one lowercase sha256 hex line."""
    match = _PIN.fullmatch(Path(path).read_bytes())
    if match is None:
        raise ValueError(f"{Path(path).name} must contain exactly one lowercase sha256 hex line "
                         "(64 characters, LF or CRLF terminated, nothing else)")
    return match.group(1).decode("ascii")


def current_research_identity() -> str:
    import lpbf_research_cache
    return lpbf_research_cache.research_implementation_sha256()


def main(argv: list) -> int:
    if argv == ["--write"]:
        value = current_research_identity()
        EXPECTED_RESEARCH_IDENTITY_FILE.write_bytes(value.encode("ascii") + b"\n")
        print(f"wrote {EXPECTED_RESEARCH_IDENTITY_FILE.name}: {value}")
        return 0
    if argv == ["--check"]:
        pinned, current = read_pinned_research_identity(), current_research_identity()
        print(f"pinned  {pinned}\ncurrent {current}")
        return 0 if pinned == current else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
