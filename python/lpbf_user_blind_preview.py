"""Preview of the user blind test (spec 4.5 item 1, 5 step 3): writes nothing, calls no thermal solver, shows no
predicted value. Shared by the estimate RPC, the freeze submit check and the freeze child.
"""
from __future__ import annotations

from lpbf_served_arms import predictor_identity, served_index, unpinned_reasons
from lpbf_user_blind_inputs import (
    ISSUE_TEXT, best_reachable, block_issues, check_file_name, decode_upload, design_checks, grades,
    labels_from_metadata, normalize_metadata, parse_inputs,
)
from lpbf_user_blind_overlap import preview_overlap
from lpbf_user_blind_protocol import (
    CAPS, DIVERGENCES, FREEZE_ESTIMATE_S_PER_CALL, FREEZE_QUEUE_NOTE, HONESTY, PREVIEW_SCHEMA, PROTOCOL_ID,
    REGISTERED_ALLOYS, WORDING, canonical_bytes, canonical_sha256, protocol_sha256, sha256_hex,
)


def applying_divergences(md, issues):
    ids = ["D7", "D9", "D10", "G1"]
    if "BOUNDARY_NOT_ETCHED" in issues:
        ids.append("D2")
    if "LOCATION_NEAR_ENDS_OR_UNSTATED" in issues:
        ids.append("D3")
    if "BEAM_PROFILE_NOT_GAUSSIAN" in issues:
        ids.append("D4")
    if md["preheatBasis"] == "nominal-ambient":
        ids.append("D5")
    if md["alloy"] not in REGISTERED_ALLOYS:
        ids.append("D6")
    order = [d["id"] for d in DIVERGENCES]
    return sorted(set(ids), key=order.index)


def exposure_reasons(md, overlap):
    from lpbf_spent_ledger import spent_dois
    out = []
    ind = md["independence"]
    if ind["predictionsViewedBeforeFreeze"] in ("yes", "unsure"):
        out.append("you declared that you viewed predictions for these conditions")
    if ind["usedForMachineCalibration"]:
        out.append("you declared that these conditions were used for machine calibration")
    doi = (ind["publishedDoi"] or "").strip().lower()
    if doi and doi in spent_dois():
        out.append(f"the DOI is in this app's spent ledger ({spent_dois()[doi]})")
    for e in overlap["earlierTests"]:
        out.append(f"{e['nConditions']} conditions match a test on this computer that was {e['kind']}")
    for e in overlap["publishedSets"]:
        out.append(f"{e['nConditions']} conditions match the published set {e['datasetId']}")
    for e in overlap["calibrationStores"]:
        out.append(f"{e['nConditions']} conditions match calibration store {e['storeId']}")
    for e in overlap["buildJobHistory"]:
        out.append(f"{e['nConditions']} conditions match Build Job history on this computer (partial check)")
    return out


def build_preview(store, metadata_raw, inputs_b64, inputs_file_name):
    """Returns (preview document, context). Context carries the parsed data for the freeze; never served."""
    check_file_name(inputs_file_name, "inputsFileName")
    md = normalize_metadata(metadata_raw)
    raw = decode_upload(inputs_b64, "inputsCsvBase64")
    parsed = parse_inputs(raw, md)
    metadata_bytes = canonical_bytes(md)
    metadata_sha = sha256_hex(metadata_bytes)
    inputs_sha = sha256_hex(raw)
    identity = predictor_identity(md["alloy"])
    unpinned = unpinned_reasons(identity)
    issues = block_issues(md, parsed)
    checks = design_checks(md, parsed, served_index)
    tuples = [(c["P_W"], c["v_mm_s"], c["d_1e2_um"]) for c in parsed["conditions"]]
    overlap = preview_overlap(store, md["alloy"], tuples)
    overlap_sha = canonical_sha256(overlap)
    exposure = exposure_reasons(md, overlap)
    best, acks = best_reachable(md, issues, checks, exposure)
    if overlap["publishedSets"]:
        acks.append("publishedConditionOverlap")
    if overlap["calibrationStores"]:
        acks.append("calibrationOverlap")
    acks = sorted(set(acks))
    labels = labels_from_metadata(md) + parsed["labels"]
    if md["independence"]["dataPreviouslyPublished"] == "yes" and not any("spent ledger" in r for r in exposure):
        doi = md["independence"]["publishedDoi"]
        labels.append(f"published data, not in this app's spent ledger (DOI {doi})" if doi
                      else "published data, not in this app's spent ledger (DOI not given)")
    n = len(parsed["conditions"])
    calls = 5 * n
    columns = parsed["columnsLoaded"]
    psha = protocol_sha256()
    preview_sha = canonical_sha256({"schema": PREVIEW_SCHEMA, "metadataSha256": metadata_sha,
                                    "inputsSha256": inputs_sha, "columns": columns, "protocolSha256": psha,
                                    "predictorIdentity": identity, "bestReachable": best,
                                    "acknowledgementsRequired": acks, "overlapSha256": overlap_sha})
    alias_by_canon = {a["canonical"]: a for a in parsed["aliases"]}
    units = {c: {"header": (alias_by_canon.get(c) or {}).get("header", c),
                 "unitRead": (alias_by_canon.get(c) or {}).get("unit"),
                 "factor": (alias_by_canon.get(c) or {}).get("factor", 1.0)}
             for c in ("power_W", "speed_mm_s", "spot_um") if c in [*parsed["keyColumns"], "power_W", "speed_mm_s",
                                                                        "spot_um"]}
    parsed_inputs = [{"condition": c["condition"], "P_W": c["P_W"], "v_mm_s": c["v_mm_s"],
                      "beamDeclared_um": c["d_declared_um"], "beamQuantity": md["beam"]["quantity"],
                      "beamDefinition": md["beam"]["definition"], "d_1e2_um": c["d_1e2_um"],
                      "tracks": c["nTracks"], "rows": c["nRows"]} for c in parsed["conditions"]]
    preview = {
        "schema": PREVIEW_SCHEMA, "protocolId": PROTOCOL_ID, "previewSha256": preview_sha,
        "metadataSha256": metadata_sha, "inputsSha256": inputs_sha, "protocolSha256": psha,
        "overlapSha256": overlap_sha, "columns": columns, "aliases": parsed["aliases"], "dialect": parsed["dialect"],
        "counts": parsed["counts"], "excludedInputs": [], "grades": grades(md),
        "blockIssues": [{"code": i, "text": ISSUE_TEXT[i], "fix": WORDING["blockIssueFix"][i]} for i in issues],
        "labels": labels, "designChecks": checks, "overlap": overlap, "bestReachable": best,
        "acknowledgementsRequired": acks,
        "budget": {"conditions": n, "solverCalls": calls, "cap": CAPS["conditions"],
                   "estimate_s": round(calls * FREEZE_ESTIMATE_S_PER_CALL, 1), "queueNote": FREEZE_QUEUE_NOTE},
        "divergences": applying_divergences(md, issues), "parsedInputs": parsed_inputs, "units": units,
        "predictorPinned": not unpinned, "predictorUnpinnedFiles": unpinned,
        "research": {"requested": False, "reasonCode": "RESEARCH_NOT_REQUESTED", "text": WORDING["researchReview"]},
        "honesty": HONESTY,
    }
    context = {"metadata": md, "metadataBytes": metadata_bytes, "inputsBytes": raw, "parsed": parsed,
               "identity": identity, "unpinned": unpinned, "issues": issues, "checks": checks, "overlap": overlap,
               "labels": labels, "best": best, "acks": acks, "exposure": exposure}
    return preview, context
