#!/usr/bin/env python3
"""Offline CLI of the user blind test (research hub spec 3.1), for air-gapped labs. No network.

Subcommands:
  export-protocol [--check]      write or check data/blind/lpbf-user-blind-protocol-v1.json and the wording table
  pin-served-closure [--check]   write or check data/blind/served-closure-pin-v1.json (a change is a reviewed commit)
  templates [--out DIR]          write blind_inputs_v1.csv, blind_targets_v1.csv, blind_metadata_v1.json
  preview  --metadata M --inputs I                       print the preview (no prediction)
  freeze   --metadata M --inputs I [--ack NAME ...]       freeze; prints the receipt (no prediction)
  reveal   --freeze KEY --confirm "<phrase>"             commit a reveal record (ends blind status)
  score    --freeze KEY --targets T [--viewed no|yes|unsure] [--accept-commitment-mismatch]
  list | show --freeze KEY [--reveal "<phrase>"] | bundle --freeze KEY --out FILE [--reveal "<phrase>"]
  verify   --bundle FILE          re-hash, recompute freezeKey and re-score byte for byte

`list` and `verify` print receipts, hashes, statuses and check results only. `show` and `bundle` print or export the
frozen predictions only when a reveal record or a score exists, or with --reveal and the exact phrase, which commits
the reveal first. Run the CLI in the same environment as the worker (both Windows or both WSL): an msvcrt lock and
an flock on a /mnt path do not exclude each other, so the store refuses the other lock domain.
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = HERE.parent
sys.path.insert(0, str(PY))
REPO = PY.parent
DATA = REPO / "data" / "blind"
PROTOCOL_PATH = DATA / "lpbf-user-blind-protocol-v1.json"
WORDING_PATH = DATA / "lpbf-user-blind-wording-v1.json"
TEMPLATES = DATA / "templates"


def _pretty(obj):
    return (json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def _check_or_write(path, data, check):
    if check:
        current = path.read_bytes().replace(b"\r\n", b"\n") if path.is_file() else None
        if current != data:
            print(f"{path.relative_to(REPO).as_posix()}: differs from the generator (run without --check)")
            return False
        print(f"{path.relative_to(REPO).as_posix()}: current")
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    print(f"wrote {path.relative_to(REPO).as_posix()}")
    return True


def cmd_export_protocol(a):
    from lpbf_user_blind_protocol import protocol_record, protocol_sha256, wording_record, wording_sha256
    rec = {**protocol_record(), "protocolSha256": protocol_sha256()}
    wor = {**wording_record(), "wordingSha256": wording_sha256()}
    ok = _check_or_write(PROTOCOL_PATH, _pretty(rec), a.check) & _check_or_write(WORDING_PATH, _pretty(wor), a.check)
    return 0 if ok else 1


CLOSURE_PROBE = r"""
import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import lpbf_served_arms as s
for alloy in s.PROTOCOL_ALLOYS:
    s.served_arm(alloy, 200.0, 800.0, 80.0, 80.0)
    s.sensitivity_arms(alloy, 200.0, 800.0, 80.0, 80.0)
root = Path(sys.argv[1]).resolve()
out = []
for m in list(sys.modules.values()):
    f = getattr(m, "__file__", None)
    if f:
        p = Path(f).resolve()
        if p.is_relative_to(root):
            out.append(p.relative_to(root).as_posix())
print(json.dumps(sorted(set(out))))
"""


def loaded_served_modules():
    """Every project module (relative to python/) loaded by running all served paths in a fresh interpreter."""
    import subprocess
    out = subprocess.run([sys.executable, "-I", "-B", "-c", CLOSURE_PROBE, str(PY)], capture_output=True, text=True,
                         check=True, cwd=str(PY))
    return json.loads(out.stdout.strip().splitlines()[-1])


def closure_files():
    """Loaded project modules outside the fingerprint manifest (the served-closure pin members)."""
    from lpbf_simulation import IMPLEMENTATION_SOURCE_FILES
    manifest = set(IMPLEMENTATION_SOURCE_FILES)
    return sorted(f"python/{rel}" for rel in loaded_served_modules() if rel not in manifest)


def cmd_pin(a):
    import lpbf_served_arms as s
    doc = s.closure_pin_document(closure_files())
    return 0 if _check_or_write(s.CLOSURE_PIN_PATH, _pretty(doc), a.check) else 1


def cmd_templates(a):
    from lpbf_user_blind_protocol import METADATA_SCHEMA, TEMPLATE_INPUT_HEADER, TEMPLATE_TARGET_HEADER
    out = Path(a.out) if a.out else TEMPLATES
    out.mkdir(parents=True, exist_ok=True)
    (out / "blind_inputs_v1.csv").write_bytes(
        (",".join(TEMPLATE_INPUT_HEADER) + "\nC-SYNTHETIC-EXAMPLE,T-SYNTHETIC-EXAMPLE-1,S1,200,800,80\n").encode())
    (out / "blind_targets_v1.csv").write_bytes(
        (",".join(TEMPLATE_TARGET_HEADER) + "\nC-SYNTHETIC-EXAMPLE,T-SYNTHETIC-EXAMPLE-1,S1,,,,not-measured\n").encode())
    meta = {"schema": METADATA_SCHEMA, "blockLabel": "Synthetic example block", "mode": "pre-measurement",
            "alloy": "Ti-6Al-4V", "quantity": "melt-pool-depth", "depthBoundary": "etched-fusion-boundary",
            "measurementMethod": "optical-cross-section", "depthDatum": "original-surface",
            "reduction": "per-section-raw", "crossSectionLocation": "steady-state-mid-track", "wavelength_nm": 1070,
            "preheat_C": 25, "preheatBasis": "measured", "atmosphere": "argon", "csvDialect": "comma-dot",
            "targetCommitment": None,
            "beam": {"diameter_um": None, "quantity": "diameter", "definition": "1/e2", "basis": "nominal",
                     "profile": "gaussian", "uncertaintyReleased": False, "u_k1_um": None},
            "power": {"basis": "commanded", "meterNamed": False, "uncertaintyReleased": False, "u_k1_rel": None},
            "substrate": {"kind": "bare-plate", "layerThickness_um": None, "amSubstrate": False, "thickness_mm": 10,
                          "surfacePreparation": "ground", "alsi10mgState": None},
            "replication": {"tracksPerCondition": 1, "sectionsPerTrack": 1, "rowsAreSeparateTracks": False},
            "depthUncertainty": {"basis": "not-released", "u_um": None, "coverageFactor": 1},
            "chemistry": {"basis": "unstated", "sulfur_ppm": None, "oxygen_ppm": None},
            "independence": {"predictionsViewedBeforeFreeze": "no", "dataPreviouslyPublished": "no",
                             "publishedDoi": None, "usedForMachineCalibration": False}}
    (out / "blind_metadata_v1.json").write_bytes(_pretty(meta))
    print(f"wrote templates to {out}")
    return 0


def _req(jt, **kw):
    from lpbf_user_blind_protocol import REQUEST_SCHEMA
    return {"jobType": jt, "schema": REQUEST_SCHEMA, **kw}


def _inputs_payload(a):
    raw = Path(a.inputs).read_bytes()
    return {"metadata": json.loads(Path(a.metadata).read_text(encoding="utf-8")),
            "inputsCsvBase64": base64.b64encode(raw).decode("ascii"), "inputsFileName": Path(a.inputs).name}


def _print_safe(obj):
    from lpbf_user_blind import assert_no_prediction
    assert_no_prediction(obj)
    print(json.dumps(obj, indent=1, sort_keys=True))


def _run_job(p):
    """Same functions as the worker: validate, stage, run in this process (a fresh process per CLI call)."""
    import tempfile
    import lpbf_user_blind as ub
    staged = ub.stage_request(ub.validate_request(p))
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp) / ("cli" + "0" * 29)
        folder.mkdir()
        return ub.run_job(staged, folder)


def cmd_preview(a):
    import lpbf_user_blind as ub
    _print_safe(ub.rpc(_req("user-blind-preview", **_inputs_payload(a))))
    return 0


def cmd_freeze(a):
    import lpbf_user_blind as ub
    payload = _inputs_payload(a)
    preview = ub.rpc(_req("user-blind-preview", **payload))
    acks = {k: True for k in (a.ack or [])}
    r = _run_job(_req("user-blind-freeze", **payload, previewSha256=preview["previewSha256"],
                      overlapSha256=preview["overlapSha256"], acknowledgements=acks))
    _print_safe(r)
    return 0


def cmd_reveal(a):
    _print_safe(_run_job(_req("user-blind-reveal", freezeKey=a.freeze, confirmation=a.confirm or "")))
    return 0


def cmd_score(a):
    raw = Path(a.targets).read_bytes()
    r = _run_job(_req("user-blind-score", freezeKey=a.freeze, targetsCsvBase64=base64.b64encode(raw).decode("ascii"),
                      targetsFileName=Path(a.targets).name,
                      declarations={"viewedPredictionsBeforeFinalisingTargets": a.viewed},
                      acceptCommitmentMismatch=bool(a.accept_commitment_mismatch)))
    _print_safe(r)
    return 0


def cmd_list(a):
    import lpbf_user_blind as ub
    _print_safe(ub.rpc(_req("user-blind-list")))
    return 0


def _gate(a):
    import lpbf_user_blind as ub
    from lpbf_user_blind_protocol import BlindRefusal, REVEAL_PHRASE
    store = ub.Store()
    if store.reveal_or_score_exists(a.freeze):
        return store
    if a.reveal != REVEAL_PHRASE:
        raise BlindRefusal("REVEAL_REQUIRED")
    store.check_mutation_allowed()
    ub.reveal(store, a.freeze, None, via="cli")
    return store


def cmd_show(a):
    store = _gate(a)
    print(store.read_record(store.freeze_dir(a.freeze), "freeze.json").decode("ascii"))
    return 0


def cmd_bundle(a):
    import lpbf_user_blind as ub
    store = _gate(a)
    r = ub.run_bundle(store, {"freezeKey": a.freeze, "jobId": None, "revealConfirmed": True})
    data = store.read_record(store.record_dir(a.freeze, "bundle", r["bundleN"]), "bundle.tar")
    Path(a.out).write_bytes(data)
    _print_safe(r)
    return 0


def verify_bundle(path):
    """Checks of a bundle. Each check is {id, ok (True, False or None), note}. A missing member is ok False, never an
    exception. Statistics are re-computed from the frozen predictions and the targets file: byte for byte when numpy
    and scipy equal the versions recorded at freeze, otherwise compared at a stated relative tolerance and reported
    as a different numerical environment (never as a tamper)."""
    import tarfile
    import numpy
    import scipy
    from lpbf_user_blind_freeze import freeze_key_of, scorer_identity
    from lpbf_user_blind_score import predictions_sha256
    from lpbf_user_blind_store import sha256_bytes
    checks = []

    def check(cid, ok, note=None, **extra):
        checks.append({"id": cid, "ok": ok, **({"note": note} if note else {}), **extra})

    members = {}
    try:
        with tarfile.open(path, mode="r:") as tar:
            for m in tar.getmembers():
                if not m.isreg() or "/" in m.name or "\\" in m.name or m.name.startswith(".") or m.name in members:
                    check("members", False, "unsafe or duplicate member")
                    return checks
                members[m.name] = tar.extractfile(m).read()
    except (tarfile.TarError, OSError):
        check("members", False, "not a readable tar file")
        return checks
    needed = ("bundle-manifest.json", "freeze.json", "freeze.json.sha256", "inputs.csv", "metadata.json")
    missing = [n for n in needed if n not in members]
    if missing:
        check("members", False, "missing members: " + ", ".join(missing))
        return checks
    try:
        manifest = json.loads(members.pop("bundle-manifest.json"))
        freeze = json.loads(members["freeze.json"])
    except ValueError:
        check("members", False, "a JSON member does not parse")
        return checks
    listed = {f["name"] for f in manifest.get("files", [])}
    files_ok = set(members) == listed and all(sha256_bytes(members[f["name"]]) == f["sha256"]
                                              for f in manifest["files"])
    check("member-hashes", files_ok)
    freeze_sha = sha256_bytes(members["freeze.json"])
    check("freeze-sha256", members["freeze.json.sha256"].decode("ascii", "replace").strip() == freeze_sha,
          "compare this value with the freezeSha256 you shared outside this computer", freezeSha256=freeze_sha)
    try:
        key_ok = freeze_key_of(freeze["metadata"], freeze["rows"], freeze["predictorIdentity"]) == freeze["freezeKey"]
        pred_ok = predictions_sha256(freeze) == freeze["predictionsSha256"]
    except (KeyError, TypeError):
        key_ok = pred_ok = False
    check("freeze-key", key_ok)
    check("predictions-sha256", pred_ok, "recomputed from the frozen conditions")
    check("inputs-hash", sha256_bytes(members["inputs.csv"]) == freeze.get("inputsSha256"))
    recorded = freeze.get("scorerIdentity") or {}
    live = scorer_identity()
    same_sources = live["scoreSourcesSha256"] == recorded.get("scoreSourcesSha256")
    same_numerics = numpy.__version__ == recorded.get("numpy") and scipy.__version__ == recorded.get("scipy")
    n = 1
    while f"score-{n}.json" in members:
        try:
            rep = json.loads(members[f"score-{n}.json"])
        except ValueError:
            check(f"report-{n}", False, "the report does not parse")
            n += 1
            continue
        check(f"report-freeze-{n}", rep.get("freezeSha256") == freeze_sha, "the report names this freeze record")
        targets = members.get(f"targets-{n}.csv")
        if targets is None:
            check(f"targets-hash-{n}", False, f"targets-{n}.csv is missing")
            n += 1
            continue
        check(f"targets-hash-{n}", sha256_bytes(targets) == rep.get("targetsSha256"))
        if not same_sources:
            check(f"rescore-statistics-{n}", None, "re-score skipped: different scorer source")
        else:
            ok = _rescore_matches(freeze, members, n, rep, exact=same_numerics)
            env = ("same numerical environment, compared byte for byte" if same_numerics else
                   f"different numerical environment (numpy {numpy.__version__}, scipy {scipy.__version__} here; "
                   f"numpy {recorded.get('numpy')}, scipy {recorded.get('scipy')} at freeze), compared at a relative "
                   f"{RESCORE_REL_TOL:g}")
            check(f"rescore-statistics-{n}", ok, "statistics, per-condition rows, resolution and leverage recomputed "
                  "from the frozen predictions and the targets file; " + env + "; the blindness status depends on "
                  "this computer's history and is not recomputed")
        n += 1
    return checks


STAT_SECTIONS = ("ledger", "resolution", "leverage", "exclusions", "excluded", "notFormed")
RESCORE_REL_TOL = 1e-9


def _close(a, b):
    import math
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_close(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_close(x, y) for x, y in zip(a, b))
    if isinstance(a, float) and isinstance(b, (int, float)) or isinstance(b, float) and isinstance(a, (int, float)):
        return math.isclose(float(a), float(b), rel_tol=RESCORE_REL_TOL, abs_tol=1e-12)
    return a == b


def _rescore_matches(freeze, members, n, rep, exact=True):
    import tempfile
    from lpbf_user_blind_protocol import canonical_bytes
    import lpbf_user_blind_score as sc
    from lpbf_user_blind_store import Store
    with tempfile.TemporaryDirectory() as tmp:
        st = Store(Path(tmp) / "store")
        earlier = [json.loads(members[f"score-{k}.json"])["targetsSha256"] for k in range(1, n)]
        job = {"declarations": {"viewedPredictionsBeforeFinalisingTargets": "no"}}
        new = sc.score(st, job, freeze, members["freeze.json"], members[f"targets-{n}.csv"], rep["targetsSha256"],
                       rep["commitment"]["matched"], n, earlier, None, [])
    pairs = [(new[k], rep[k]) for k in STAT_SECTIONS]
    for arm, a in rep["arms"].items():
        pairs.append((new["arms"][arm]["stats"], a["stats"]))
        pairs.append((new["arms"][arm].get("bootstrap95"), a.get("bootstrap95")))
    if exact:
        return all(canonical_bytes(x) == canonical_bytes(y) for x, y in pairs)
    return all(_close(x, y) for x, y in pairs)


def cmd_verify(a):
    checks = verify_bundle(a.bundle)
    freeze_sha = next((c.get("freezeSha256") for c in checks if c["id"] == "freeze-sha256"), None)
    print(json.dumps({"freezeSha256": freeze_sha, "checks": checks}, indent=1))
    return 0 if all(c["ok"] is not False for c in checks) else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("export-protocol"); s.add_argument("--check", action="store_true"); s.set_defaults(f=cmd_export_protocol)
    s = sub.add_parser("pin-served-closure"); s.add_argument("--check", action="store_true"); s.set_defaults(f=cmd_pin)
    s = sub.add_parser("templates"); s.add_argument("--out"); s.set_defaults(f=cmd_templates)
    for name, f in (("preview", cmd_preview), ("freeze", cmd_freeze)):
        s = sub.add_parser(name); s.add_argument("--metadata", required=True); s.add_argument("--inputs", required=True)
        if name == "freeze":
            s.add_argument("--ack", action="append")
        s.set_defaults(f=f)
    s = sub.add_parser("reveal"); s.add_argument("--freeze", required=True); s.add_argument("--confirm"); s.set_defaults(f=cmd_reveal)
    s = sub.add_parser("score"); s.add_argument("--freeze", required=True); s.add_argument("--targets", required=True)
    s.add_argument("--viewed", default="no", choices=("no", "yes", "unsure"))
    s.add_argument("--accept-commitment-mismatch", action="store_true"); s.set_defaults(f=cmd_score)
    s = sub.add_parser("list"); s.set_defaults(f=cmd_list)
    s = sub.add_parser("show"); s.add_argument("--freeze", required=True); s.add_argument("--reveal"); s.set_defaults(f=cmd_show)
    s = sub.add_parser("bundle"); s.add_argument("--freeze", required=True); s.add_argument("--out", required=True)
    s.add_argument("--reveal"); s.set_defaults(f=cmd_bundle)
    s = sub.add_parser("verify"); s.add_argument("--bundle", required=True); s.set_defaults(f=cmd_verify)
    a = ap.parse_args(argv)
    from lpbf_user_blind_protocol import BlindRefusal
    try:
        return a.f(a)
    except BlindRefusal as e:
        print(json.dumps({"refused": e.code, "message": e.message, "detail": e.detail}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
