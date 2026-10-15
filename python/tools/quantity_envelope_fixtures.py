"""Synthetic quantity-envelope fixtures shared by the Python and TypeScript validators (test path only).

Usage (repository root):
    python -B python/tools/quantity_envelope_fixtures.py --write   # regenerate tests/fixtures/quantity-envelope/
    python -B python/tools/quantity_envelope_fixtures.py --check   # fail when a committed file differs

Three fixtures, all synthetic, none an admission, none read from a measured dataset or a validation golden:

- synthetic-admitted-liquidus.json: SPEC Amendment 3 A3.A5 (F16). A test-only admitted-liquidus parent with
  co-located finite positive G, R, G R and G/R at full precision, per-value source labels and named inputs, under an
  explicit synthetic engine and parent identity. It restores no served alloy value.
- blanket-null-front.json: the SOL-A1 shape of contract 4.3 item 8. Every default front quantity is null with
  missing-source-constant and the liquidus parent (a declaredAssumption); dependents name their null parents.
- label-cases.json: the decided label rule (decisions 1 and 2) on named input sets, so both validators can be
  checked against the same expected labels.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

PYTHON_DIR = Path(__file__).resolve().parents[1]
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

import quantity_envelope as qe  # noqa: E402

REPO_ROOT = PYTHON_DIR.parent
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "quantity-envelope"

SYNTHETIC_ENGINE = "synthetic-f16-engine-v1 (test fixture, not a served model)"
SYNTHETIC_SOURCE = qe.source_ref("synthetic-f16-relation", "python/tools/quantity_envelope_fixtures.py (synthetic test "
                                 "relation, not a literature source)", "repository-attribution")
SYNTHETIC_LOCATOR = "python/tools/quantity_envelope_fixtures.py (synthetic test record, not a literature source)"


def _front_inputs() -> Dict[str, Any]:
    return {
        "liquidus_K": qe.ledger_input_record(
            "proposed-fixed-front-explicit-family-transfer", source_id="synthetic-f16:liquidus:transfer",
            source_locator=SYNTHETIC_LOCATOR, source="Synthetic F16 endpoint record",
            scope="Synthetic family transfer for the F16 envelope fixture; not an admitted ledger record",
            reference_temperature_K=1610.0, default_value=1610.0),
        "conductivity_W_mK": qe.input_record(
            "sourceDefault", "synthetic-f16:conductivity", status="inRange", source_locator=SYNTHETIC_LOCATOR,
            source="Synthetic F16 property record", scope="Synthetic property for the F16 envelope fixture",
            phase="solid", default_value=25.0, default_kind="sourceDefault"),
        "power_W": qe.process_input_record("power_W"),
        "speed_m_s": qe.process_input_record("speed_m_s"),
    }


def synthetic_admitted_liquidus() -> Dict[str, Any]:
    inputs = _front_inputs()
    g = 12345678.901234567          # K/m, full precision, never rounded in transport
    r = 0.051234567890123456         # m/s
    deps = ["liquidus_K", "conductivity_W_mK", "power_W", "speed_m_s"]
    common = dict(inputs=inputs, sources=[SYNTHETIC_SOURCE], model_identity=SYNTHETIC_ENGINE,
                  uncertainty={"kind": "not-quantified", "construction": None}, input_identity="synthetic-f16-request",
                  assumptions=["synthetic-fixture", "fixed-liquidus-approximation"])
    quantities: Dict[str, Any] = {
        "thermalGradient": qe.quantity("liquidus-front-thermal-gradient", g, depends_on=deps, **common),
        "normalSpeed": qe.quantity("liquidus-front-normal-speed", r, depends_on=deps, **common),
    }
    quantities["coolingRate"] = qe.quantity("liquidus-front-cooling-rate", g * r,
                                            depends_on=["thermalGradient", "normalSpeed"], quantities=quantities,
                                            **common)
    quantities["gOverR"] = qe.quantity("liquidus-front-g-over-r", g / r,
                                       depends_on=["thermalGradient", "normalSpeed"], quantities=quantities, **common)
    return qe.container(quantities, input_provenance=inputs)


def blanket_null_front() -> Dict[str, Any]:
    inputs = {
        "liquidus_K": qe.input_record(
            "declaredAssumption", "synthetic-sol-a1:liquidus:no-provenance", status="inRange",
            declaration_locator="python/tools/quantity_envelope_fixtures.py (synthetic stand-in for a served "
                                "liquidus without a provenance entry)",
            scope="Served liquidus without an admitted source (synthetic stand-in)", phase="solid-liquid-mean"),
        "power_W": qe.process_input_record("power_W"),
        "speed_m_s": qe.process_input_record("speed_m_s"),
    }
    blocked = qe.reason("missing-source-constant", parent=qe.reason_parent("liquidus_K", inputs))
    deps = ["liquidus_K", "power_W", "speed_m_s"]
    quantities: Dict[str, Any] = {
        "thermalGradient": qe.unavailable("liquidus-front-thermal-gradient", [blocked], depends_on=deps),
        "normalSpeed": qe.unavailable("liquidus-front-normal-speed", [blocked], depends_on=deps),
    }
    for name, definition in (("coolingRate", "liquidus-front-cooling-rate"), ("gOverR", "liquidus-front-g-over-r")):
        quantities[name] = qe.unavailable(definition, [
            blocked,
            qe.reason("parent-unavailable", parent=qe.reason_parent("thermalGradient", inputs, quantities)),
            qe.reason("parent-unavailable", parent=qe.reason_parent("normalSpeed", inputs, quantities)),
        ], depends_on=["thermalGradient", "normalSpeed"])
    quantities["pdas"] = qe.unavailable("pdas-model-alternatives", [
        blocked, qe.reason("parent-unavailable", parent=qe.reason_parent("thermalGradient", inputs, quantities)),
        qe.reason("parent-unavailable", parent=qe.reason_parent("normalSpeed", inputs, quantities))],
        depends_on=["thermalGradient", "normalSpeed"])
    quantities["morphology"] = qe.unavailable("front-morphology", [blocked], depends_on=["liquidus_K"])
    return qe.container(quantities, input_provenance=inputs)


def _sourced(name: str, kind: str = "sourceDefault") -> Dict[str, Any]:
    return qe.input_record(kind, f"case:{name}", status="extrapolated" if kind == "alloyTransfer" else "inRange",
                           source_locator=f"Case source for {name}", scope=f"Case scope for {name}",
                           default_kind=kind)


def _declared(name: str) -> Dict[str, Any]:
    return qe.input_record("declaredAssumption", f"case:{name}", status="inRange",
                           declaration_locator=f"Case declaration for {name}")


def _legacy(name: str) -> Dict[str, Any]:
    return qe.input_record("legacyEstimate", f"case:{name}", status="inRange", scope="No located source")


def _user(name: str) -> Dict[str, Any]:
    return qe.input_record("userInput", f"case:user:{name}", status="inRange")


def label_cases() -> Dict[str, Any]:
    sourced_k = _sourced("k")
    cases = [
        ("all-sourced", {"k": sourced_k, "cp": _sourced("cp")}, ["k", "cp"]),
        ("one-user-input", {"k": sourced_k, "cp": _user("cp")}, ["k", "cp"]),
        ("unresolved-takes-precedence", {"k": _declared("k"), "cp": _user("cp"), "rho": _sourced("rho")},
         ["k", "cp", "rho"]),
        ("legacy-estimate", {"k": _legacy("k"), "cp": _sourced("cp")}, ["k", "cp"]),
        ("process-values-excluded", {"k": sourced_k, "P": qe.process_input_record("P"),
                                     "v": qe.process_input_record("v")}, ["P", "v", "k"]),
        ("process-only-never-upgraded", {"P": qe.process_input_record("P"), "d": qe.process_input_record("d")},
         ["P", "d"]),
        ("follows-declared-rule", {"L": qe.input_record("followsInput", "case:L-from-d", status="inRange",
                                                         follows_input="d", default_kind="declaredAssumption",
                                                         declaration_locator="Case rule L = d",
                                                         source_evidence_kind="Unresolved"),
                                   "d": qe.process_input_record("d"), "k": sourced_k}, ["L", "k"]),
        ("follows-sourced-rule-of-user-input", {
            "mu": qe.input_record("followsInput", "case:mu-from-Tref", status="inRange", follows_input="Tref",
                                  default_kind="sourceDefault", source_locator="Case viscosity law",
                                  source_evidence_kind="User input"),
            "Tref": _user("Tref"), "k": sourced_k}, ["mu", "k"]),
        ("derived-from-weakest", {"alpha": qe.input_record("derived", "case:alpha", status="inRange",
                                                           depends_on=("k", "cp"), source_evidence_kind="Unresolved"),
                                  "k": sourced_k, "cp": _legacy("cp")}, ["alpha"]),
        ("typed-equal-to-default-keeps-source", {
            "k": qe.typed_input(sourced_k, 25.0, 25.0, source_id="case:user:k"), "cp": _sourced("cp")}, ["k", "cp"]),
        ("typed-different-is-user-input", {
            "k": qe.typed_input(sourced_k, 25.000000000000004, 25.0, source_id="case:user:k"),
            "cp": _sourced("cp")}, ["k", "cp"]),
        ("transfer-reads-literature-never-measured", {"Tl": _sourced("Tl", "alloyTransfer")}, ["Tl"]),
        ("record-downgrade-is-kept", {"Lf": qe.input_record(
            "alloyTransfer", "case:Lf", status="extrapolated", source_locator="Case pure-Al fusion proxy",
            source_evidence_kind="Unresolved", scope="Pure-Al fusion proxy"), "k": sourced_k}, ["Lf", "k"]),
        ("missing-record-is-unresolved", {"k": sourced_k}, ["k", "Tl"]),
    ]
    # Hand-pinned expectations: never derive the oracle from the rule being tested.
    expected_cases = [
        ("Literature estimate", [], ["Case source for k", "Case source for cp"]),
        ("User input", ["cp"], []),
        ("Unresolved", ["k"], []),
        ("Unresolved", ["k"], []),
        ("Literature estimate", [], ["Case source for k"]),
        ("Unresolved", [], []),
        ("Unresolved", ["L"], []),
        ("User input", ["Tref"], []),
        ("Unresolved", ["cp"], []),
        ("Literature estimate", [], ["Case source for k", "Case source for cp"]),
        ("User input", ["k"], []),
        ("Literature estimate", [], ["Case source for Tl"]),
        ("Unresolved", ["Lf"], []),
        ("Unresolved", ["Tl"], []),
    ]
    out = []
    for (name, inputs, depends_on), (kind, weakest, sources) in zip(cases, expected_cases, strict=True):
        out.append({"name": name, "inputs": inputs, "dependsOn": depends_on,
                    "expected": {"sourceEvidenceKind": kind, "weakestInputs": weakest, "labelSources": sources}})
    return {"rule": "decisions 1 and 2 (2026-10-15); contract 4.3; P8 13.12", "cases": out}


def build_fixtures() -> Dict[str, Any]:
    return {
        "synthetic-admitted-liquidus.json": synthetic_admitted_liquidus(),
        "blanket-null-front.json": blanket_null_front(),
        "label-cases.json": label_cases(),
    }


def render(document: Any) -> str:
    return json.dumps(document, indent=2, ensure_ascii=False, allow_nan=False) + "\n"


def stale() -> list:
    out = []
    for name, document in build_fixtures().items():
        path = FIXTURE_DIR / name
        if not path.is_file() or path.read_text(encoding="utf-8").replace("\r\n", "\n") != render(document):
            out.append(path)
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if args.check:
        paths = stale()
        for path in paths:
            print(f"stale: {path}", file=sys.stderr)
        return 1 if paths else 0
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    for name, document in build_fixtures().items():
        problems = [] if name == "label-cases.json" else qe.envelope_problems(document)
        if problems:
            raise SystemExit(f"{name}: {problems}")
        (FIXTURE_DIR / name).write_text(render(document), encoding="utf-8", newline="\n")
        print(f"wrote {FIXTURE_DIR / name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
