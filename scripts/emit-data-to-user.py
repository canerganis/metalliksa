"""Read-only UI projections. Never writes measurements, solver inputs, pins or manifests.

Measurements stay in their benchmark folders. This file emits only served model
samples and constant provenance. Run with --check to detect stale projections.
"""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
import four_alloy_materials as fam
import lpbf_material_registry as registry
import lpbf_public_datasets as datasets
import quantity_envelope as qe
from lpbf_thermal_solver import calculate_meltpool_physics, SECONDARY_THERMOPHYSICAL_DB

OUTPUT = ROOT / "src/generated/dataToUser.json"
LEDGER = ROOT / "data/benchmark/spent-ledger-v1.json"
OPEN_LICENCES = {"CC0", "CC BY 4.0", "NIST open data, https://www.nist.gov/open/license"}


def digest(path):
    data = path.read_bytes()
    # Python source identity is independent of Windows checkout line endings.
    if path.suffix == ".py":
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def build():
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    rows = datasets.load_totis_ti64()["rows"] + datasets.load_ku_leuven_316l_ti64()["rows"]
    nist = json.loads((ROOT / "data/benchmark/nist-amb2022-03-optical/table4-aggregate-v2.json").read_text())
    rows += [dict(dataset="nist-amb2022-03-optical", rowId=c["caseNumber"], material="Inconel 718",
                  power_W=c["laserPower_W"], speed_mm_s=c["scanSpeed_mm_s"],
                  beamDiameter_um=c["beamDiameterD4sigma_um"], preheat_C=23.5, layer_um=0)
             for c in nist["cases"]]
    samples = {}
    for entry in ledger["entries"]:
        if entry["licence"] not in OPEN_LICENCES:
            continue
        for row in rows:
            if row["dataset"] != entry["datasetId"]:
                continue
            # Missing substrate temperature stays an explicitly disclosed assumption.
            inputs = dict(material_name=row["material"], laser_power_W=row["power_W"],
                          scan_speed_mm_s=row["speed_mm_s"], beam_diameter_um=row["beamDiameter_um"],
                          preheat_temp_C=row["preheat_C"], layer_thickness_um=row["layer_um"] or 40,
                          hatch_spacing_um=100, heat_source="rosenthal", absorption_model="flat-plate",
                          include_process_map=False)
            with contextlib.redirect_stdout(io.StringIO()):
                result = calculate_meltpool_physics(**inputs)
            geometry = result["meltPoolGeometry"]
            samples[f"{row['dataset']}/{row['rowId']}"] = {
                "inputs": inputs, "modelId": result["modelId"],
                "depth_um": geometry["depth_um"] if geometry["extentStatus"] == "computed" else None,
                "extentStatus": geometry["extentStatus"], "extentNote": geometry["extentNote"],
            }
    alloys = []
    for aid in ("ti6al4v", "alsi10mg", "in625", "in718", "ss316l"):
        name = "Inconel 625" if aid == "in625" else fam.THERMAL_NAME[aid]
        thermal = SECONDARY_THERMOPHYSICAL_DB[name] if aid == "in625" else fam.thermal_props(aid)
        prov = {**fam.PROPERTY_PROVENANCE.get("*", {}), **fam.PROPERTY_PROVENANCE.get(name if aid == "in625" else aid, {})}
        props = []
        for key, value in {**thermal, "emissivity": fam.PROPERTY_PROVENANCE["*"]["emissivity"]["value"]}.items():
            if not isinstance(value, (int, float)):
                continue
            p = prov.get(key, {})
            # A citation for another path/value cannot establish this constant's evidence.
            supported = bool(p.get("source")) and p.get("value") == value and p.get("basis") in (
                "cited-primary", "cited-secondary", "measured-conduction-bare-plate", "measured-conduction-as-built-surface")
            kind = "sourceModelAssumption" if supported else "legacyEstimate"
            status = "inRange"
            # SOL-T: an admitted nominal endpoint convention keeps its admission kind (modelConvention or
            # alloyTransfer, the latter extrapolated); it is a Literature estimate, never a measured specimen pair.
            if (p.get("basis") == "admitted-nominal-convention" and p.get("source") and p.get("value") == value
                    and p.get("admissionKind") in ("modelConvention", "alloyTransfer")):
                supported, kind = True, p["admissionKind"]
                status = "extrapolated" if kind == "alloyTransfer" else "inRange"
            label = qe.input_record(kind, f"served-{aid}-{key}", status=status,
                                    source_locator=(p.get("locator") or p.get("source")) if supported else None,
                                    source=p.get("source") if supported else None)
            scope = p.get("scope", "")
            if key in ("pdas_A1", "sdas_B1"):
                scope = "Retained legacy parameter; unused by the served solver."
            props.append(dict(quantity=key, value=value, source=p.get("source") or "Unresolved",
                              locator=p.get("locator") or (p.get("source") if supported else "Unresolved"),
                              sourceEvidenceKind=label["sourceEvidenceKind"], basis=p.get("basis", "Unresolved"),
                              scope=scope, note=p.get("note", "")))
        catalog = next(c for c in registry.catalog() if c["name"] == name)
        alloys.append(dict(id=aid, name=name, registry=catalog, constants=props))
    paths = ["python/four_alloy_materials.py", "python/lpbf_thermal_solver.py", "python/lpbf_material_registry.py",
             "python/quantity_envelope.py", "data/benchmark/spent-ledger-v1.json",
             "data/benchmark/nist-amb2022-03-optical/table4-aggregate-v2.json",
             "data/benchmark/ku-leuven-316l-ti64-2021/conditions.csv", "data/benchmark/totis-ti64-2021/tracks.csv"]
    return dict(schemaVersion=1, sourceHashes={p: digest(ROOT / p) for p in paths}, samples=samples, alloys=alloys)


if __name__ == "__main__":
    rendered = (json.dumps(build(), ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    if "--check" in sys.argv:
        if not OUTPUT.exists() or OUTPUT.read_bytes().replace(b"\r\n", b"\n") != rendered:
            raise SystemExit("Stale dataToUser.json; run python -B scripts/emit-data-to-user.py")
    else:
        OUTPUT.write_bytes(rendered)
        print(f"Wrote {OUTPUT}")
