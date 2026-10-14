"""Emit src/generated/lpbfMaterialAuthority.json from the Python LPBF material authority.

The TypeScript side must not hold its own alloy numbers. This script projects
python/four_alloy_materials.py (four_alloy_thermophysical_db(), LITERATURE_PV_WINDOWS,
canonical_material_source()) and the evidence label that python/lpbf_material_registry.py
attaches to those values into one committed JSON file that the UI reads.
IN625 is not one of the four locked alloys: its constant-property row is projected from
python/lpbf_thermal_solver.py SECONDARY_THERMOPHYSICAL_DB (the table the Rosenthal path
uses), labelled quality "secondary-unreconciled", with the registry catalog label and every
other IN625 value Python holds elsewhere listed next to it. Nothing here fills in a value;
the only arithmetic is the K -> C conversion of one listed boiling point.

Usage (from the repo root, with the locked interpreter):
    python -B scripts/emit-lpbf-material-authority.py           # write the generated file
    python -B scripts/emit-lpbf-material-authority.py --check   # exit 1 when out of date
Equality tests: python/test_lpbf_material_authority_json.py, tests/lpbf-material-authority.test.ts.
"""
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "python"))

import four_alloy_materials as fam  # noqa: E402
import in625_thermal_material as in625  # noqa: E402
import lpbf_material_registry as registry  # noqa: E402
from lpbf_thermal_solver import SECONDARY_THERMOPHYSICAL_DB  # noqa: E402

GENERATED_JSON = REPO_ROOT / "src" / "generated" / "lpbfMaterialAuthority.json"
SCHEMA_VERSION = 1
IN625_THERMAL_NAME = "Inconel 625"
# Not a value: an explicit label saying this row is neither the four-alloy authority nor reconciled.
IN625_QUALITY = "secondary-unreconciled"
IN625_SOURCE = "python/lpbf_thermal_solver.py SECONDARY_THERMOPHYSICAL_DB"


def in625_unreconciled_values():
    """Every IN625 value that Python holds in more than one place, read from the modules themselves."""
    row = SECONDARY_THERMOPHYSICAL_DB[IN625_THERMAL_NAME]
    return [
        {"quantity": "latent heat of fusion", "unit": "J/kg", "values": [
            {"module": IN625_SOURCE, "use": "Rosenthal / build-job path",
             "value": row["latent_heat_fusion_J_kg"]},
            {"module": "python/in625_thermal_material.py LATENT_HEAT_J_KG", "use": "Sabau et al. 2020 fusion-enthalpy screening",
             "value": in625.LATENT_HEAT_J_KG},
            {"module": "python/in625_thermal_material.py IN625_LATENT_HEAT_FUSION_MILLS_J_KG", "use": "transient material spec",
             "value": in625.IN625_LATENT_HEAT_FUSION_MILLS_J_KG},
        ]},
        {"quantity": "boiling point", "unit": "C", "values": [
            {"module": IN625_SOURCE, "use": "Rosenthal / build-job path", "value": row["boiling_C"]},
            {"module": "python/in625_thermal_material.py IN625_BOILING_K", "use": "transient material spec (K - 273.15)",
             "value": round(in625.IN625_BOILING_K - 273.15, 2)},
        ]},
        {"quantity": "IR absorptivity", "unit": "", "values": [
            {"module": IN625_SOURCE, "use": "Rosenthal / build-job path", "value": row["absorptivity_IR"]},
            {"module": "python/in625_thermal_material.py IN625_ABSORPTIVITY_IR", "use": "transient material spec",
             "value": in625.IN625_ABSORPTIVITY_IR},
        ]},
    ]


def in625_note(conflicts):
    parts = []
    for item in conflicts:
        # Group the paths by value so equal values read as one agreeing group and the differing
        # value stays visible; every label and symbol comes from the listed entries themselves.
        groups = []
        for entry in item["values"]:
            label = f"{entry['use']} [{entry['module'].split()[-1]}]"
            for group in groups:
                if group[0] == entry["value"]:
                    group[1].append(label)
                    break
            else:
                groups.append((entry["value"], [label]))
        unit = f" {item['unit']}" if item["unit"] else ""
        rendered = " vs ".join(f"{value:g}{unit} in {' and '.join(labels)}" for value, labels in groups)
        parts.append(f"{item['quantity']}: {rendered}")
    return (
        "Secondary alloy, outside the four-alloy authority and not labelled by it. Constant properties are "
        f"{IN625_SOURCE}['Inconel 625'] (Rosenthal / build-job path). Python holds other IN625 values in "
        "python/in625_thermal_material.py (Sabau et al. 2020 screening snapshot; Mills-based transient specification) "
        "and the paths that differ are not reconciled (paths holding the same value are grouped): "
        + "; ".join(parts) + ". The material registry catalog does not offer this row as a material."
    )


def build_document():
    db = fam.four_alloy_thermophysical_db()
    alloys = {}
    for aid in fam.FOUR_ALLOY_IDS:
        name = fam.THERMAL_NAME[aid]
        evidence = registry.material(name)
        _snapshot, source_sha256 = fam.canonical_material_source(aid)
        authority = fam.absorptivity_authority(aid)
        alloys[aid] = {
            "thermalName": name,
            "slicerName": fam.SLICER_NAME[aid],
            "quality": evidence["quality"],
            "source": evidence["source"],
            "canonicalSourceSha256": source_sha256,
            "thermal": dict(db[name]),
            "literaturePvWindow": dict(fam.LITERATURE_PV_WINDOWS[aid]),
            # P7b (2026-10-14): the physical absorptivity authority entry (basis, band, source, locator; not a new
            # value, the same number as thermal.absorptivity_IR) and the kernel ledger identity of the ledger alloys
            # (Ti-6Al-4V, AlSi10Mg: the numeric projection that kernel_properties evaluates per call and its sha256).
            "absorptivityAuthority": {key: authority[key] for key in ("basis", "band", "wavelength_nm", "source",
                                                                     "locator", "conditions", "unsourced")},
            "kernelLedgerSha256": fam.kernel_ledger_sha256(aid),
            "kernelLedger": None if aid not in fam.PROPERTY_LEDGER else json.loads(json.dumps(
                fam.PROPERTY_LEDGER[aid]["numeric"], sort_keys=True)),
        }
    in625_catalog = next(entry for entry in registry.catalog() if entry["name"] == IN625_THERMAL_NAME)
    conflicts = in625_unreconciled_values()
    return {
        "_generated": "GENERATED by scripts/emit-lpbf-material-authority.py. Do not edit by hand.",
        "schemaVersion": SCHEMA_VERSION,
        "authority": "python/" + fam.MATERIAL_AUTHORITY,
        "authoritySchemaVersion": fam.MATERIAL_AUTHORITY_SCHEMA_VERSION,
        "alloyIds": list(fam.FOUR_ALLOY_IDS),
        "alloys": alloys,
        "secondary": {
            "in625": {
                "thermalName": IN625_THERMAL_NAME,
                "quality": IN625_QUALITY,
                "source": IN625_SOURCE,
                "registryCatalogQuality": in625_catalog["quality"],
                "registryCatalogNote": in625_catalog["note"],
                "note": in625_note(conflicts),
                "unreconciledPythonValues": conflicts,
                "thermal": dict(SECONDARY_THERMOPHYSICAL_DB[IN625_THERMAL_NAME]),
            },
        },
    }


def render(document=None):
    """Deterministic LF text (the file is pinned to LF in .gitattributes)."""
    document = build_document() if document is None else document
    return json.dumps(document, indent=2, ensure_ascii=False, allow_nan=False) + "\n"


def rendered_bytes():
    return render().encode("utf-8")


def is_current():
    return GENERATED_JSON.exists() and GENERATED_JSON.read_bytes() == rendered_bytes()


def main(argv):
    if "--check" in argv:
        if is_current():
            return 0
        print(f"stale: {GENERATED_JSON} (run python -B scripts/emit-lpbf-material-authority.py)", file=sys.stderr)
        return 1
    GENERATED_JSON.parent.mkdir(parents=True, exist_ok=True)
    GENERATED_JSON.write_bytes(rendered_bytes())
    print(f"wrote {GENERATED_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
