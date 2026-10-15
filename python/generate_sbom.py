#!/usr/bin/env python3
"""
Generate CycloneDX 1.5 JSON SBOMs for Python (requirements.txt) and Node (package-lock.json).

Usage:
  py -3 python/generate_sbom.py
  npm run sbom
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT_DIR = os.path.join(ROOT, "sbom")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _bom(components: List[Dict[str, Any]], name: str) -> Dict[str, Any]:
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:{uuid.uuid4()}",
        "version": 1,
        "metadata": {
            "timestamp": _now(),
            "tools": [{"vendor": "Metalliksa", "name": "generate_sbom.py", "version": "1.0.0"}],
            "component": {
                "type": "application",
                "name": name,
                "version": "1.0.0",
            },
        },
        "components": components,
    }


def _parse_req_line(line: str) -> Optional[Tuple[str, str]]:
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    # name>=x / name==x / name~=x
    m = re.match(r"^([A-Za-z0-9_.\-]+)\s*([=<>!~]+)\s*([^\s;]+)", line)
    if m:
        return m.group(1), m.group(3)
    m2 = re.match(r"^([A-Za-z0-9_.\-]+)\s*$", line)
    if m2:
        return m2.group(1), "unspecified"
    return None


def python_components() -> List[Dict[str, Any]]:
    path = os.path.join(ROOT, "python", "requirements.txt")
    comps: List[Dict[str, Any]] = []
    if not os.path.isfile(path):
        return comps
    with open(path, encoding="utf-8") as f:
        for line in f:
            parsed = _parse_req_line(line)
            if not parsed:
                continue
            name, ver = parsed
            comps.append(
                {
                    "type": "library",
                    "name": name,
                    "version": ver,
                    "purl": f"pkg:pypi/{name.lower()}@{ver}",
                    "properties": [{"name": "metallix:source", "value": "python/requirements.txt"}],
                }
            )
    return comps


def node_components() -> List[Dict[str, Any]]:
    lock = os.path.join(ROOT, "package-lock.json")
    pkg = os.path.join(ROOT, "package.json")
    comps: List[Dict[str, Any]] = []
    if os.path.isfile(lock):
        with open(lock, encoding="utf-8") as f:
            data = json.load(f)
        packages = data.get("packages") or {}
        for path_key, meta in packages.items():
            if not path_key:
                continue  # root
            name = meta.get("name") or path_key.replace("node_modules/", "").split("node_modules/")[-1]
            ver = meta.get("version") or "unknown"
            comps.append(
                {
                    "type": "library",
                    "name": name,
                    "version": ver,
                    "purl": f"pkg:npm/{name}@{ver}",
                }
            )
        return comps

    # Fallback: package.json deps only
    if os.path.isfile(pkg):
        with open(pkg, encoding="utf-8") as f:
            data = json.load(f)
        for section in ("dependencies", "devDependencies"):
            for name, ver in (data.get(section) or {}).items():
                comps.append(
                    {
                        "type": "library",
                        "name": name,
                        "version": str(ver).lstrip("^~"),
                        "purl": f"pkg:npm/{name}@{str(ver).lstrip('^~')}",
                        "properties": [{"name": "metallix:source", "value": f"package.json:{section}"}],
                    }
                )
    return comps


def write_bom(filename: str, name: str, components: List[Dict[str, Any]]) -> str:
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, filename)
    bom = _bom(components, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(bom, f, indent=2)
        f.write("\n")
    digest = hashlib.sha256(json.dumps(bom, sort_keys=True).encode("utf-8")).hexdigest()[:16]
    print(f"Wrote {path} ({len(components)} components, sha256[:16]={digest})")
    return path


def main() -> int:
    write_bom("python-cyclonedx.json", "metallix-python", python_components())
    write_bom("node-cyclonedx.json", "metallix-node", node_components())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
