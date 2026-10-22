"""Platform-tolerant freshness comparison for committed Python-producer fixtures.

The fixtures are real producer output. The producers' arithmetic is not bit-identical across platforms (libm and
BLAS differ between the Windows development machine and the Linux CI runner), so an exact byte comparison fails
on CI although nothing is stale. Measured Linux (Python 3.10, numpy) against the committed Windows capture over
27322 leaves: no key or structure difference, 34 numeric leaves differ, all but one below 1e-12 relative, plus
``observedOrder`` (a Richardson log-ratio of nearly equal differences, which amplifies 1e-13 input noise) up to
4.2e-5 relative. Content-addressed identity strings (sha256 digests and hex-float encodings of those same floats)
differ with them and cannot be compared by value.

The comparison therefore keeps exact equality for the structure, every key, every non-numeric leaf, every bool and
every integer-typed leaf, and allows only: float leaves within REL_TOL, ``observedOrder`` within ORDER_ABS_TOL,
and, inside strings, hex digests and hex-float literals that differ while the rest of the string is identical.
"""
from __future__ import annotations

import json
import math
import re

REL_TOL = 1e-9
ORDER_ABS_TOL = 1e-3  # observedOrder is about 2; measured cross-platform spread 8.4e-5 absolute
_HEX_NOISE = re.compile(r"0x1\.[0-9a-f]+p[+-]?\d+|[0-9a-f]{32,}")


def _is_num(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def differences(actual, expected, path="", limit=20):
    """Return up to ``limit`` human-readable differences (empty list means equal under the policy above)."""
    out = []

    def walk(a, b, where):
        if len(out) >= limit:
            return
        if isinstance(a, dict) and isinstance(b, dict):
            if set(a) != set(b):
                out.append(f"{where}: keys differ {sorted(set(a) ^ set(b))[:5]}")
                return
            for key in a:
                walk(a[key], b[key], f"{where}/{key}")
        elif isinstance(a, list) and isinstance(b, list):
            if len(a) != len(b):
                out.append(f"{where}: length {len(a)} != {len(b)}")
                return
            for i, (x, y) in enumerate(zip(a, b)):
                walk(x, y, f"{where}[{i}]")
        elif _is_num(a) and _is_num(b):
            if a == b:
                return
            if isinstance(a, int) and isinstance(b, int):
                out.append(f"{where}: {a} != {b}")
            elif where.endswith("/observedOrder"):
                if not abs(a - b) <= ORDER_ABS_TOL:
                    out.append(f"{where}: {a!r} != {b!r}")
            elif not math.isclose(a, b, rel_tol=REL_TOL, abs_tol=0.0):
                out.append(f"{where}: {a!r} != {b!r}")
        elif isinstance(a, str) and isinstance(b, str):
            if a != b and _HEX_NOISE.sub("<hex>", a) != _HEX_NOISE.sub("<hex>", b):
                out.append(f"{where}: string differs outside hex digests")
        elif a != b or type(a) is not type(b):
            out.append(f"{where}: {a!r} != {b!r}")

    walk(actual, expected, path)
    return out


def serialized_equal(actual_text, expected_text):
    """True when two JSON documents agree under the policy above (exactly equal text short-circuits)."""
    if actual_text == expected_text:
        return True
    return not differences(json.loads(actual_text), json.loads(expected_text))


def mapping_differences(actual, expected):
    """Compare {file name: JSON text} mappings: same names, each document equal under the policy."""
    problems = []
    if set(actual) != set(expected):
        problems.append(f"file sets differ: {sorted(set(actual) ^ set(expected))}")
    for name in sorted(set(actual) & set(expected)):
        if not serialized_equal(actual[name], expected[name]):
            problems.append(f"{name}: " + "; ".join(differences(json.loads(actual[name]), json.loads(expected[name]), limit=3)))
    return problems
