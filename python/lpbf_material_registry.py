"""Versioned material evidence. Never silently substitute an unknown alloy.

Legacy solid/liquid values are retained, not promoted to measured curves.
Interpolation is an explicitly estimated constitutive law, not new literature data.
Additional alloy identities accept user-supplied, sourced property tables.
"""
import hashlib
import json
import math
import numpy as np
from four_alloy_materials import (
    canonical_material_source, four_alloy_thermophysical_db,
    resolve_alloy_id, THERMAL_NAME,
)
from lpbf_thermal_solver import SECONDARY_THERMOPHYSICAL_DB
from in625_thermal_material import in625_lpbf_thermal_at_kelvin, in625_lpbf_thermal_snapshot

VERSION = "lpbf-materials-1"
LEGACY = {**four_alloy_thermophysical_db(),
          **{name: properties for name, properties in SECONDARY_THERMOPHYSICAL_DB.items()
             if name != "Inconel 625"}}
NAMES = list(dict.fromkeys(["Ti-6Al-4V", "316L Stainless Steel", "AlSi10Mg", "Inconel 718",
                            *SECONDARY_THERMOPHYSICAL_DB,
                            "Inconel 625", "17-4PH", "15-5PH", "Maraging Steel 18Ni300",
                            "AlSi7Mg", "CuCrZr", "Ti-5553"]))


def _require_json_value(value, path="material", active=None):
    """Reject Python-only values before they can enter a persisted identity."""
    if active is None:
        active = set()
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"Invalid non-finite JSON number at {path}")
        return
    if isinstance(value, list):
        identity = id(value)
        if identity in active:
            raise ValueError(f"Invalid cyclic JSON value at {path}")
        active.add(identity)
        try:
            for index, item in enumerate(value):
                _require_json_value(item, f"{path}[{index}]", active)
        finally:
            active.remove(identity)
        return
    if isinstance(value, dict):
        identity = id(value)
        if identity in active:
            raise ValueError(f"Invalid cyclic JSON value at {path}")
        active.add(identity)
        try:
            for key, item in value.items():
                if not isinstance(key, str):
                    raise ValueError(f"Invalid non-string JSON object key at {path}")
                _require_json_value(item, f"{path}.{key}", active)
        finally:
            active.remove(identity)
        return
    raise ValueError(f"Invalid non-JSON value at {path}")


def catalog():
    return [{"name": n, "quality": "estimated" if n in LEGACY else "missing",
             "available": n in LEGACY,
             "thermalOnlyAvailable": n == "Inconel 625",
             "note": ("Legacy solid/liquid endpoints; estimated interpolation, constant viscosity; "
                      "emissivity 0.35 is an assumed screening constant.")
             if n in LEGACY else (
                 "Bounded fusion-enthalpy literature-model screening only; full transient solver unavailable."
                 if n == "Inconel 625" else "Supply a sourced property table; no surrogate alloy is substituted.")}
            for n in NAMES]


def _in625_identity(name):
    return isinstance(name, str) and "".join(name.strip().lower().split()).replace("-", "") in ("in625", "inconel625")


def thermal_screening_material(name):
    """IN625-only bounded thermal snapshot; not a full transient material."""
    if not _in625_identity(name):
        raise ValueError("Thermal-only screening material unavailable for this identity")
    return in625_lpbf_thermal_snapshot()


def thermal_screening_at(name, temperature_k):
    if not _in625_identity(name):
        raise ValueError("Thermal-only screening material unavailable for this identity")
    return in625_lpbf_thermal_at_kelvin(temperature_k)


# Sourced solid conductivity at the solidus where one exists (W/(m K), citation). Otherwise the
# room-temperature solid value is held to the solidus (estimated).
_SOLIDUS_CONDUCTIVITY = {
    # Ho, Powell & Liley, J. Phys. Chem. Ref. Data 1 (1972) 279, doi:10.1063/1.3253100,
    # copper recommended values: solid k at the melting point 1357.6 K = 3.28 W/(cm K).
    "Pure Copper (Cu-OF)": 328.0,
}


def _legacy_table(p, solidus_k, liquidus_k, boiling_k, name=None):
    """Estimated legacy table: RT solid, solidus, liquidus and boiling rows.

    rho and cp keep the historical straight line from 273.15 K to the liquid endpoint at the
    liquidus (the solidus row lies on that line, so their interpolation is unchanged). Solid k
    follows the same line where it rises with temperature (Ni, Fe, Ti, Co alloys), but never
    drops below its room-temperature value before the solidus: for alloys whose tabulated liquid
    k is below the solid value (Al alloys, Cu) the drop to the liquid value happens across the
    mushy zone, not linearly from 273 K. Estimated shape, not a measured curve (MD-1).
    A pure metal (solidus == liquidus) gets the same 1 K regularisation window as its latent heat.
    """
    t_rt = 273.15
    k_rt, k_liq = p["thermal_conductivity_W_mK"], p["thermal_conductivity_liquid_W_mK"]
    liquid = (p["density_liquid_kg_m3"], k_liq, p["specific_heat_liquid_J_kgK"])
    room = (p["density_kg_m3"], k_rt, p["specific_heat_J_kgK"])
    if k_liq >= k_rt:
        # Rising solid k: the historical three-row table is kept bit-for-bit (no identity drift).
        rows = [(t_rt, room), (liquidus_k, liquid), (boiling_k, liquid)]
        return [[t, rho, k, cp, p["viscosity_Pa_s"]] for t, (rho, k, cp) in rows]
    if solidus_k == liquidus_k:
        solidus_k, liquidus_k = solidus_k - .5, liquidus_k + .5
    f = (solidus_k - t_rt) / (liquidus_k - t_rt)
    line = lambda solid, liquid: solid + (liquid - solid) * f
    solid_at_solidus = (line(p["density_kg_m3"], p["density_liquid_kg_m3"]),
                        _SOLIDUS_CONDUCTIVITY.get(name, k_rt),
                        line(p["specific_heat_J_kgK"], p["specific_heat_liquid_J_kgK"]))
    return [[t, rho, k, cp, p["viscosity_Pa_s"]] for t, (rho, k, cp) in [
        (t_rt, room),
        (solidus_k, solid_at_solidus), (liquidus_k, liquid), (boiling_k, liquid)]]


def material(name, supplied=None):
    if not isinstance(name, str):
        raise ValueError("Material identity must be a string")
    if _in625_identity(name):
        name = "Inconel 625"
    aid = resolve_alloy_id(name)
    name = THERMAL_NAME[aid] if aid else name
    if name not in NAMES:
        raise ValueError("Unknown alloy identity")
    if supplied is not None:
        if not isinstance(supplied, dict):
            raise ValueError("Material properties must be an object")
        _require_json_value(supplied)
        allowed = {"source", "solidus_K", "liquidus_K", "boiling_K", "latentHeat_J_kg", "absorptivity", "emissivity",
                   "dGamma_dT", "table", "name", "version", "quality", "physicalMeltingPoint_K", "phaseRegularization_K",
                   "temperatureCoverage_K", "sourceValidityRange_K", "uncertaintyNote", "materialId", "provenanceClass",
                   "materialIdentitySchemaVersion", "materialRevisionSha256"}
        if set(supplied)-allowed:
            raise ValueError("Unknown material property fields")
        m = dict(supplied)
        # Supplied properties are re-identified for the requested alloy below;
        # never trust identity metadata copied from an earlier snapshot.
        for key in ("materialId", "provenanceClass", "materialIdentitySchemaVersion", "materialRevisionSha256"):
            m.pop(key, None)
        if not isinstance(m.get("source"), str) or not m["source"].strip():
            raise ValueError("A property-table source is required")
        m["quality"] = "user-supplied-unverified"
    else:
        if name not in LEGACY:
            raise ValueError(f"{name}: thermophysical data missing; supply sourced properties")
        p = LEGACY[name]
        m = dict(solidus_K=p["solidus_C"]+273.15, liquidus_K=p["liquidus_C"]+273.15,
                 boiling_K=p["boiling_C"]+273.15, latentHeat_J_kg=p["latent_heat_fusion_J_kg"],
                 absorptivity=p["absorptivity_IR"], emissivity=0.35,
                 dGamma_dT=p["d_gamma_dT_N_mK"],
                 source="Existing four_alloy_materials.py / lpbf_thermal_solver.py; endpoint provenance not independently verified",
                 quality="estimated")
        m["table"] = _legacy_table(p, m["solidus_K"], m["liquidus_K"], m["boiling_K"], name)
    for key in ("solidus_K", "liquidus_K", "boiling_K", "latentHeat_J_kg", "absorptivity", "emissivity", "dGamma_dT"):
        if isinstance(m.get(key), bool) or not isinstance(m.get(key), (int, float)) or not math.isfinite(m[key]):
            raise ValueError(f"Invalid material property: {key}")
    if m["solidus_K"] == m["liquidus_K"]:
        m["physicalMeltingPoint_K"] = m["solidus_K"]
        m["phaseRegularization_K"] = 1.
        m["solidus_K"] -= .5; m["liquidus_K"] += .5
        m["source"] += "; pure-metal latent heat regularized over 1 K for numerical inversion"
    if not 0 < m["solidus_K"] < m["liquidus_K"] < m["boiling_K"] <= 10000:
        raise ValueError("Require 0 < solidus < liquidus < boiling <= 10000 K")
    if not 0 < m["latentHeat_J_kg"] <= 2e6 or not 0 < m["absorptivity"] <= 1 or not 0 <= m["emissivity"] <= 1:
        raise ValueError("Invalid latent heat / optical properties")
    raw_table = m.get("table")
    if not isinstance(raw_table, list) or any(not isinstance(row, list) or any(type(v) not in (int,float) for v in row) for row in raw_table):
        raise ValueError("Material table must contain numeric rows, not booleans or strings")
    a = np.asarray(raw_table, dtype=float)
    if a.ndim != 2 or a.shape[1] != 5 or not 2 <= len(a) <= 200 or not np.isfinite(a).all():
        raise ValueError("table rows must be [T_K, rho_kg_m3, k_W_mK, cp_J_kgK, viscosity_Pa_s]")
    if (a <= 0).any() or (np.diff(a[:, 0]) <= 0).any() or a[0, 0] > 273.15 or a[-1, 0] < m["boiling_K"]:
        raise ValueError("Positive properties, increasing temperatures and full temperature coverage required")
    if "sourceValidityRange_K" in m:
        validity = m["sourceValidityRange_K"]
        if (not isinstance(validity, list) or len(validity) != 2
                or any(type(value) not in (int, float) or value <= 0 or value > 10000
                       or not math.isfinite(value) for value in validity)
                or validity[0] > a[0, 0] or validity[1] < max(a[-1, 0], m["boiling_K"])):
            raise ValueError("sourceValidityRange_K must cover the full property table and boiling regime")
    for col, lo, hi in ((1, 100, 30000), (2, .01, 2000), (3, 50, 10000), (4, 1e-5, 10)):
        if (a[:, col] < lo).any() or (a[:, col] > hi).any():
            raise ValueError(f"Property column {col} outside physical model bounds [{lo}, {hi}]")
    if abs(m["dGamma_dT"]) > .01:
        raise ValueError("Surface tension slope outside model bounds")
    m.update(name=name, version=VERSION, table=a.tolist(), temperatureCoverage_K=[float(a[0,0]),float(a[-1,0])],
             uncertaintyNote="Property uncertainties not quantified; source string does not establish validation.")
    m["materialId"] = aid if aid else f"registry:{name}"
    m["provenanceClass"] = "estimated-legacy" if supplied is None else "user-supplied-unverified"
    m["materialIdentitySchemaVersion"] = 1
    if aid is not None and supplied is None:
        source_snapshot, source_revision_sha256 = canonical_material_source(aid)
        m["materialAuthority"] = source_snapshot["authority"]
        m["materialAuthorityRevisionSha256"] = source_revision_sha256
    _require_json_value(m)
    try:
        identity_payload = json.dumps(m, sort_keys=True, separators=(",", ":"),
                                      ensure_ascii=True, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise ValueError(f"Material snapshot is not valid JSON: {exc}") from exc
    m["materialRevisionSha256"] = hashlib.sha256(identity_payload).hexdigest()
    return m


def reidentify(m):
    """Recompute materialRevisionSha256 after a request-level override (absorptivity, emissivity) changed the snapshot.

    P7b (2026-10-14, finding 1.3 f): before the absorptivity authority moved, a request absorptivity equal to the
    registry value left the snapshot unchanged, so the identity never had to be redone; an archived payload or fixture
    that carries an explicit absorptivity (Ti-6Al-4V 0.35, AlSi10Mg 0.18, Inconel 718 0.38) now differs from the
    registry value and must be re-identified, otherwise lpbf_core_contract rejects the result as a revision mismatch.
    The hash rule is exactly the one of material(): sha256 of the canonical JSON of the snapshot without the hash key.
    """
    snapshot = {key: value for key, value in m.items() if key != "materialRevisionSha256"}
    _require_json_value(snapshot)
    identity_payload = json.dumps(snapshot, sort_keys=True, separators=(",", ":"),
                                  ensure_ascii=True, allow_nan=False).encode("utf-8")
    out = dict(snapshot)
    out["materialRevisionSha256"] = hashlib.sha256(identity_payload).hexdigest()
    return out


def property_at(m, temperature, column):
    a = np.asarray(m["table"])
    return np.interp(temperature, a[:, 0], a[:, column])


def enthalpy_table(m):
    """Integrate piecewise-linear cp exactly; resolve latent heat at phase boundaries."""
    t = np.unique(np.r_[np.linspace(273.15, m["boiling_K"], 12000),
                        np.asarray(m["table"])[:, 0], m["solidus_K"], m["liquidus_K"]])
    cp = property_at(m, t, 3)
    h = np.r_[0, np.cumsum(np.diff(t)*(cp[1:]+cp[:-1])/2)]
    h += m["latentHeat_J_kg"]*np.clip((t-m["solidus_K"])/(m["liquidus_K"]-m["solidus_K"]), 0, 1)
    return t, h
