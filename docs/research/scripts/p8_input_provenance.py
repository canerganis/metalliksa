"""P8 source metadata and secondary-alloy scenario declarations; no depth data.

This documentation helper imports no solver, paper or target-data runner. The
integration owner passes the already selected immutable registry and tuples.
Run with ``python -B .../p8_input_provenance.py --check`` for metadata checks.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
from pathlib import Path
import subprocess
import types

SPEC = "docs/research/SPEC_p8_research_arm_2026-10-14.md"
LEDGER = "835466fa:python/four_alloy_materials.py"
O8 = "docs/research/scripts/alsi10mg_vapour_o8.py"
KINDS = {"sourceDefault", "sourceModelAssumption", "alloyTransfer",
         "sourcedAlternative", "modelConvention", "declaredAssumption",
         "legacyEstimate", "userInput", "followsInput", "derived"}
PHYSICAL_INPUTS = {
    "cavity": ("K", "cp", "rho", "A", "Tl", "Tv", "Lv", "M"),
    "meltDepthLink": ("K", "cp", "rho", "A", "Tl", "Tv", "Lv", "M"),
    "marangoni": ("kl", "cpl", "rhol", "slope", "mu", "L", "deltaT"),
    "surfaceBalance": ("K", "cp", "rho", "A", "Tv", "Lv", "M",
                       "accommodation", "effectiveNetFactor", "recoil", "emissivity"),
}
# Exact active tuples for local dedup; cavity references are a separate ledger.
ACTIVE_INPUTS = {
    "marangoni": ("kl", "cpl", "rhol", "slope", "mu", "L", "deltaT", "Tref"),
    "surfaceBalance": ("P", "v", "d", "T0", "K", "cp", "rho", "alpha", "A",
                       "Tv", "Lv", "M", "accommodation", "effectiveNetFactor", "recoil", "emissivity"),
}


def _record(kind, source_id, locator=None, *, source=None, phase=None,
            reference=None, source_range=None, evidence=None, scope="",
            follows=None, dependencies=(), status="extrapolated"):
    if evidence is None:
        evidence = ("Unresolved" if kind in {"declaredAssumption", "legacyEstimate"}
                    else "User input" if kind == "userInput" else "Literature estimate")
    return dict(kind=kind, label=kind, sourceId=source_id, source=source,
                sourceLocator=locator, declarationLocator=None, phase=phase,
                referenceTemperature_K=reference, sourceRange_K=source_range,
                sourceEvidenceKind=evidence, scope=scope, status=status,
                defaultValue=None, defaultKind=None, followsInput=follows,
                followState="following" if follows else None,
                dependsOn=list(dependencies))


def _assumption(key, scope, phase=None, reference=None):
    record = _record("declaredAssumption", "p8:assumption:" + key,
                     phase=phase, reference=reference,
                     source=None, scope=scope)
    record["declarationLocator"] = SPEC + " Amendment 2 B3 / A4"
    return record


def arm_provenance(alloy, name):
    """Compatibility summary; authoritative detail is input_provenance()."""
    if name == "srv":
        return _record("legacyEstimate", "p8:former-served-blend:" + alloy,
                       LEDGER + " pre-P7 served blend", source="Former served blend",
                       scope="No independently located source; descriptive diagnostic only")
    if name == "absorptance_0.14":
        return _record("alloyTransfer", "trapp2017:al1100:A0.14", "Trapp 2017 Table 2 / Fig.7",
                       source="Trapp 2017", scope="Al1100 ground to AlSi10Mg constant molten-wall proxy")
    if name == "vapour_o8":
        return _record("derived", "p8:o8:hybrid-local-slope:Mg1383", O8 + " vapour_constants; " + SPEC + " section 6 / B7",
                       source="O8 Mondal/CIAAW/feedstock Raoult calculation", phase="vapour",
                       reference=2477.605213217703, source_range=[600., 1730.],
                       scope="Mg constant-H CC exceeds Mg fit 600-1730 K and 10 atm synthesis ceiling; feedstock transfer, hybrid/local-slope enthalpy, no depletion")
    if name in {"vapour_3360", "vapour_3760"}:
        return _assumption(name, "Ti Gan nominal Tv3560 K plus or minus 200 K; not a literature boiling value", "vapour")
    if name.startswith("onset_"):
        method = name[6:]
        return _record("modelConvention", "p8:onset:" + method,
                       SPEC + " section 4 / Amendment 2 B1-B2; P3 PREDECLARED section 2.5 c4470b01",
                       source={"O1": "Trapp 2017 Eq.3", "O2": "Fabbro 2018 Eq.2", "O3": "P8 steady Gaussian derivation"}[method],
                       scope="O2 piston event differs from recoil inception" if method == "O2" else "Alternate onset diagnostic event")
    if name.startswith(("power_", "beam_", "deltaT_", "length_")):
        return _assumption(name, "One-at-a-time deterministic sensitivity; no measurement distribution")
    if name == "nominal":
        return _record("sourceDefault", "p8:nominal:" + alloy, SPEC + " sections 3 / A2 / A3",
                       source="P8 located presets; inspect each input for transfers and assumptions")
    return _record("sourcedAlternative", "p8:alternative:" + alloy + ":" + name,
                   SPEC + " Amendment 2 B3; " + LEDGER + " PROPERTY_LEDGER",
                   source="Explicit named source/property/convention alternative; inspect each input")


def input_provenance(alloy, name, arm, nominal):
    """Return metadata for every supplied fixture input without changing values.

    Phase and reference temperature belong to each property, independently of
    the solid-kernel temperature interval and diagnostic liquid Tref. Source
    ranges are null when the inspected source record gives no closed range.
    """
    ti = alloy == "ti6al4v"
    tref = arm.get("Tref")
    if tref is None and arm.get("Tl") is not None and arm.get("deltaT") is not None:
        tref = arm["Tl"] + arm["deltaT"] / 2
    t0, tl = arm.get("T0"), arm.get("Tl")
    mean = (t0 + tl) / 2 if t0 is not None and tl is not None else None
    out = {}
    for key in arm:
        out[key] = _record("legacyEstimate", "p8:unlocated:" + alloy + ":" + key,
                           scope="No located source for this input; never fill from another alloy")
    for key in ("P", "v", "d", "T0"):
        if key in arm:
            out[key] = _record("userInput", "p8:request:" + key, phase="process",
                               scope="Process request echo; excluded from physical-coefficient evidence rule")
    for key in ("K", "cp"):
        if key not in arm:
            continue
        if ti:
            out[key] = _record("derived", "gan2021:solid-fit:kirchhoff:" + key,
                               "Gan 2021 SI Table 1 PDF p.20; " + LEDGER + " PROPERTY_LEDGER.ti6al4v.numeric",
                               source="Gan 2021 fit of Mills data", phase="solid", reference=mean,
                               source_range=[293.15, 1933.15], scope="Kirchhoff mean over [T0,Tl]; constant diffusivity approximation")
        elif alloy == "alsi10mg":
            state = name.removeprefix("state_") if name.startswith("state_") else "AB"
            upper = 373.15 if key == "K" and state == "AB_unrelaxed" else 800.15 if key == "K" and state not in {"HT", "HT_low"} else 773.15
            out[key] = _record("derived", "p7b:alsi10mg:" + state + ":kirchhoff:" + key,
                               ("Yang 2018 Figs.1/5; Akwaboa 2023 Fig.2f / Conclusion(3); Fetni 2024 Fig.4a; " + LEDGER + " PROPERTY_LEDGER.alsi10mg"),
                               source="Recorded solid node tables", phase="solid", reference=mean,
                               source_range=[298.15, upper], scope="Piecewise-linear node integral; endpoint holds extend below/above measured nodes; state " + state)
    if "rho" in out and ti:
        out["rho"] = _record("sourceModelAssumption", "nbs61-v:4430:room-density", "NBS61-V Table 4(S1); " + SPEC + " section 3",
                             source="NBS room-density compilation", phase="solid", reference=293.15,
                             scope="Room density held constant through the solid-kernel interval; not molten density")
    elif "rho" in out and alloy == "alsi10mg":
        out["rho"] = _record("sourceDefault", "akwaboa2023:density:sample100-0.2", "Akwaboa 2023 Table 3 PDF p.5",
                             source="Helium pycnometer density", phase="solid", reference=293.15,
                             scope="Sample100-0.2 transferred to current solid; constant density")
    if "Tl" in out:
        out["Tl"] = (_record("sourceModelAssumption", "gan2021:ti64:liquidus", "Gan 2021 SI Table 1 PDF p.20",
                             phase="solid-liquid-mean", reference=tl, source="P8 source-model liquidus") if ti else
                     _assumption("alsi10mg:liquidus", "Supplier/binary proxy convention; not specimen DSC", "solid-liquid-mean", tl))
    if "A" in out:
        source = ("Simonds 2021 Sec.3.2 Fig.3a PDF p.4; NIST mds2-2525" if ti else
                  "Leis, Weber, Graf 2020 Sec.3 Figs.4-6 pp.175-176" if alloy == "alsi10mg" else
                  LEDGER + " ABSORPTIVITY_AUTHORITY." + alloy)
        out["A"] = _record("alloyTransfer", "p7b:optical-wall-proxy:" + alloy, source,
                           source="Conduction surface absorptance authority", phase="liquid",
                           scope="Located conduction absorptance transferred to constant molten-wall A0; not measured wall optics")
    for key in ("Tv", "Lv", "M"):
        if key not in out:
            continue
        if ti:
            out[key] = _record("sourceModelAssumption", "gan2021:ti64:vapour:" + key, "Gan 2021 SI Table 1 PDF p.20",
                               source="Gan model-input tuple", phase="vapour", reference=arm.get("Tv"),
                               scope="Effective model species; not measured alloy vapour")
        elif alloy == "alsi10mg":
            out[key] = _record("alloyTransfer", "mondal2023:ciaaw:pure-Al:" + key,
                               "Mondal 2023 Table 1 PDF p.3; CIAAW aluminium atomic weight",
                               source="Pure Al Tb/H and elemental molar mass", phase="vapour", reference=arm.get("Tv"),
                               scope="Mg-depleted Al-dominated surface hypothesis; Lv=284000/M; not measured AlSi10Mg")
    liquid = {
        "kl": ("Mohr 2020 p.7 Wiedemann-Franz EML resistivity", 1933.15, None),
        "cpl": ("Mohr 2020 Sec.5 p.8 Fig.4a", 1933.15, [1760., 1890.]),
        "rhol": ("Mohr 2020 Eq.21 p.5", 1933.15, None),
        "slope": ("Mohr 2020 Eq.23 p.6", tref, [1700., 1950.]),
        "mu": ("Rai 2007 Table 6 p.5757", None, None),
    } if ti else {
        "kl": ("Sun 2019 Fig.7, binary Al-Si10 mass percent", tl, [1023.15, 1123.15]),
        "cpl": ("Registry liquid cp1180; pure-Al/Al6061 proxy, ledger1170 discrepancy retained", tl, None),
        "rhol": ("Assael 2012 Table 2 Al-Si12 mass percent", tl, [858., 1700.]),
        "slope": ("Seimiya 2026 Table 1 PDF p.16, oxide-free Al-Si10 at.percent", tref, [1476., 1981.]),
        "mu": ("Assael 2012 Eq.2 / Table 5 PDF p.7, binary Al-Si12 mass percent", tref, [860., 1275.]),
    }
    if alloy in {"ti6al4v", "alsi10mg"}:
        for key, (locator, ref, limits) in liquid.items():
            if key not in out:
                continue
            kind = "sourceDefault" if ti and key != "mu" else "sourceModelAssumption" if ti else "alloyTransfer"
            evidence = "Unresolved" if not ti and key == "cpl" else None
            out[key] = _record(kind, "p8:liquid:" + alloy + ":" + key, locator,
                               source=locator, phase="liquid", reference=ref, source_range=limits,
                               evidence=evidence, scope="Constant liquid tuple at stated reference; evaluate source range separately at diagnostic Tref")
    for key in ("L", "deltaT", "Tref"):
        if key in out:
            out[key] = _assumption(key, "Assumed liquid length/hot-rim contrast/reference; no measured field", "liquid", tref)
    if "L" in out and arm.get("L") == arm.get("d") and not name.startswith("length_"):
        out["L"].update(kind="followsInput", followsInput="beamDiameter_m", followState="following", defaultKind="declaredAssumption", dependsOn=["d"])
    if "Tref" in out:
        out["Tref"].update(kind="followsInput", followsInput="deltaTemperature_K", followState="following", defaultKind="declaredAssumption", dependsOn=["Tl", "deltaT"])
    if alloy == "alsi10mg" and "mu" in out:
        out["mu"]["sourceLawProvenance"] = copy.deepcopy(out["mu"])
        out["mu"].update(kind="followsInput", followsInput="referenceTemperature_K", followState="following", defaultKind="alloyTransfer", dependsOn=["Tl", "deltaT"])
        # The sourced binary law and its evaluated value are different objects.
        # Assumed Tl/deltaT determine the evaluation temperature; preserve the
        # literature-law label while propagating their uncertainty to mu.
        out["mu"]["sourceEvidenceKind"] = evidence_kind(out, ("Tl", "deltaT"))[0]
    for key in ("accommodation", "effectiveNetFactor", "recoil"):
        if key in out:
            out[key] = _record("sourceModelAssumption", "fabbro2020:A10-A12:" + key,
                               "Fabbro 2020 Appendix A A10-A12 PDF pp.19-20; P6 section 4.1",
                               source="Paired source-model assumption", phase="vapour",
                               scope="Accommodation1, beta.2/net.8, recoil.6; independent controls can decouple this pair")
    if "emissivity" in out:
        out["emissivity"] = (_record("sourceModelAssumption", "gan2021:ti64:emissivity", "Gan 2021 SI Table 1 PDF p.20", phase="process") if ti else
                             _assumption("emissivity0.35", "P6 synthetic assumption; no grade-specific wall measurement", "process"))
    if "Lm" in out:
        out["Lm"] = (_record("sourceDefault", "boivineau2006:ti64:Lf290000", "Boivineau 2006 p.520 Sec.5.2 Fig.8", phase="solid-liquid-mean", reference=tl) if ti else
                     _record("alloyTransfer", "p8:pure-Al:fusion397000", LEDGER + " PROPERTY_LEDGER.alsi10mg latent_heat_fusion disclosure", phase="solid-liquid-mean", reference=tl, evidence="Unresolved", scope="Pure-Al fusion proxy; specimen latent heat not established"))
    if "onsetMethod" in out:
        out["onsetMethod"] = _record("modelConvention", "p8:onset:dwell", SPEC + " section 4 / B1", scope="Recoil inception; finite-Gaussian dwell a/v")
    # Named changes must not inherit a generic nominal source record.
    summary = arm_provenance(alloy, name)
    if name == "srv":
        for key in ("K", "cp", "rho"):
            if key in out:
                out[key] = {**summary, "phase": "solid-liquid-mean", "referenceTemperature_K": None}
    elif name in {"vapour_3360", "vapour_3760"}:
        out["Tv"] = {**summary, "referenceTemperature_K": arm["Tv"]}
    elif name == "vapour_o8":
        for key in ("Tv", "Lv", "M"):
            out[key] = {**summary, "dependsOn": ["O8.feedstockComposition", "O8.hybridPressureRoute", "O8.MgTb1383", "O8.localSlopeEnthalpy"]}
    elif name.startswith("absorptance_"):
        locators = {
            ("ti6al4v", .26): "Ye 2019 Table 1 Ti64 Am0.26",
            ("ti6al4v", .33): "Simonds 2021 Sec.3.2 Fig.3a PDF p.4 first2.4ms absorption33percent",
            ("alsi10mg", .28): "Leis, Weber, Graf 2020 Sec.3 Figs.4-6 pp.175-176 areaII200um minimum28percent",
            ("alsi10mg", .4): "Leis, Weber, Graf 2020 Sec.3 Figs.4-6 pp.175-176 conduction35um30-40percent",
            ("in625", .28): "Ye 2019 Table 1 IN625 Am0.28",
            ("in625", .4): "Deisenroth 2020 Sec.3.4 Fig.7 PDF p.10 IN62580W coupling0.40",
            ("in718", .28): "Ye 2019 Table 1 IN625 Am0.28 transferred toIN718",
            ("in718", .38): "Deisenroth 2026 IN718 laser reflections Introduction ground-solid coupling0.38",
            ("ss316l", .28): "Ye 2019 Table 1 316L Am0.28",
            ("ss316l", .31): "Trapp 2017 Sec.3.1 Fig.3a regimeI upper0.31",
        }
        locator = "Trapp 2017 Table 2 / Fig.7 Al1100 ground0.14" if name == "absorptance_0.14" else locators[(alloy, arm["A"])]
        transfer = name == "absorptance_0.14" or alloy == "in718" and arm["A"] == .28
        out["A"] = _record("alloyTransfer" if transfer else "sourcedAlternative",
            summary["sourceId"] if name == "absorptance_0.14" else "p7b:optical-alternative:" + alloy + ":" + name,
            locator, source=locator, phase="liquid", scope=out["A"]["scope"] + "; named source absorptance endpoint")
    elif name.startswith("onset_"):
        out["onsetMethod"] = summary
    elif name.startswith(("power_", "beam_", "deltaT_", "length_")):
        key = next(k for prefix, k in (("power_", "P"), ("beam_", "d"), ("deltaT_", "deltaT"), ("length_", "L")) if name.startswith(prefix))
        out[key] = {**summary, "phase": "process" if key in {"P", "d"} else "liquid", "referenceTemperature_K": tref if key in {"L", "deltaT"} else None}
    elif name.startswith("slope_") or name == "viscosity_mohr":
        keys = ("slope", "mu") if name == "slope_viscosity_gan" else ("mu",) if name == "viscosity_mohr" else ("slope",)
        locator = ("Gan 2021 SI Table 1 PDF p.20" if name == "slope_viscosity_gan" else "Mohr 2020 Eq.23/Fig.3b p.6" if ti else
                   "Fukuyama 2023 ADC12 slope (PROPERTY_LEDGER locator only)" if arm.get("slope") == -.0786e-3 else "Gheribi pure-Al slope (PROPERTY_LEDGER locator only)")
        for key in keys:
            out[key] = _record("sourcedAlternative" if ti else "alloyTransfer", "p8:liquid-alternative:" + alloy + ":" + name + ":" + key,
                               locator, source=locator, phase="liquid", reference=1933.15 if name == "viscosity_mohr" else tref,
                               source_range=[1700., 1950.] if ti and key == "slope" and name != "slope_viscosity_gan" else None,
                               scope="Explicit located source-model alternative; range null where no inspected range exists")
    elif name.startswith("accommodation_"):
        out["effectiveNetFactor"] = _record("sourcedAlternative", "anisimov:effective-net0.82", "P8 Amendment 2 B3 / P6 source note: Anisimov effective0.82",
                                            source="Anisimov effective net-evaporation convention", phase="vapour",
                                            scope="Net0.82 with accommodation1; recoil.6 held independently as a decoupled diagnostic")
    if name.startswith("melt_front"):
        for key in ("K", "cp", "rho"):
            out[key].update(kind="derived", phase="solid-liquid-mean", referenceTemperature_K=tl,
                            sourceId="p8:melt-front:" + alloy + ":" + name + ":" + key,
                            sourceLocator=SPEC + " Amendment 2 B3", sourceRange_K=None,
                            dependsOn=[{"K": "ks(Ts)", "cp": "cps(Ts)", "rho": "rho_s"}[key], {"K": "kl", "cp": "cpl", "rho": "rhol"}[key]],
                            scope="Equal solid-at-solidus/liquid mean; explicit model convention, not a liquid property")
        if "adc12" in name:
            out["rhol"] = _record("alloyTransfer", "fukuyama2023:ADC12:density", "Fukuyama 2023 ADC12 density law; " + LEDGER + " PROPERTY_LEDGER",
                                  phase="liquid", reference=tl, scope="ADC12 composition transfer; inspected closed source range unavailable")
        for key in ("kl", "cpl", "rhol"):
            if arm.get(key) != nominal.get(key) and not (key == "rhol" and "adc12" in name):
                alternatives = {
                    ("kl", 28.7): ("Boivineau 2006 Eq.20; PROPERTY_LEDGER.ti6al4v.text.k_l", 1933.15),
                    ("kl", 33.4): ("Mills liquid k33.4 via Gan2021 SI Table1 PDF p.20", 1933.15),
                    ("cpl", 831.): ("Mills liquid cp831 via Gan2021 SI Table1 PDF p.20", 1933.15),
                    ("cpl", 1126.): ("Boivineau 2006 Eq.17; PROPERTY_LEDGER.ti6al4v.text.cp_l", 1933.15),
                    ("rhol", 3920.): ("Mills liquid density3920; PROPERTY_LEDGER.ti6al4v.text.rho_l", 1933.15),
                    ("rhol", 4123.): ("Li, Johnson, Rhim 2006 density4123 at1943K; PROPERTY_LEDGER.ti6al4v.text.rho_l", 1943.),
                }
                locator, reference = alternatives[(key, arm[key])] if ti else (out[key]["sourceLocator"], out[key]["referenceTemperature_K"])
                out[key].update(kind="sourcedAlternative" if ti else "alloyTransfer",
                                sourceId="p8:melt-front-liquid:" + alloy + ":" + name + ":" + key,
                                source=locator, sourceLocator=locator, referenceTemperature_K=reference,
                                sourceRange_K=None if ti else out[key]["sourceRange_K"])
        for derived_key, liquid_key in (("K", "kl"), ("cp", "cpl"), ("rho", "rhol")):
            if out[liquid_key]["sourceEvidenceKind"] == "Unresolved":
                out[derived_key]["sourceEvidenceKind"] = "Unresolved"
    if name.startswith("enthalpy_cp"):
        cpbar = dict(value=nominal["cp"], provenance=copy.deepcopy(out["cp"]))
        applied_latent = 290000. if ti else float(name.removeprefix("enthalpy_cp_"))
        latent_provenance = (copy.deepcopy(out["Lm"]) if applied_latent == arm.get("Lm") else
                            _assumption(name + ":appliedFusionLatentHeat", "Declared500kJ/kg fusion proxy alternative; not current tuple Lm or measured specimen heat", "solid-liquid-mean", tl))
        latent_provenance["defaultValue"] = nominal.get("Lm")
        out["cp"].update(kind="derived", sourceId="p8:enthalpy-convention:" + alloy + ":" + name,
                         sourceLocator=SPEC + " Amendment 2 B3",
                         phase="solid-liquid-mean", dependsOn=["Tl", "T0"],
                         derivationInputs={"nominalSpecificHeat_J_kgK": cpbar,
                             "appliedFusionLatentHeat_J_kg": {"value": applied_latent, "provenance": latent_provenance}},
                         scope="cpbar+Lf/(Tl-T0); descriptive enthalpy convention, not independently validated kernel")
        out["cp"]["sourceEvidenceKind"] = evidence_kind(
            {"cpbar": cpbar["provenance"], "appliedLatent": latent_provenance, "Tl": out["Tl"]},
            ("cpbar", "appliedLatent", "Tl"))[0]
    if name.startswith("liquidus_"):
        out["Tl"] = _assumption(name, "Declared liquidus proxy bracket with K/cp reintegration; not measured DSC", "solid-liquid-mean", tl)
    if name.startswith("rho_s_"):
        out["rho"].update(kind="sourcedAlternative", sourceId="akwaboa2023:density-endpoint:" + name,
                          scope="Akwaboa sample range endpoint; deterministic transfer, not statistical bound")
    if name in {"linear_last_100K", "cp_fetni_end"}:
        for key in ("K", "cp") if name == "linear_last_100K" else ("cp",):
            out[key].update(sourceId="p8:solid-alternative:" + name + ":" + key,
                            sourceLocator=SPEC + " Amendment 2 B3; Fetni 2024 Fig.4c",
                            scope="Explicit last100K linear extrapolation" if name == "linear_last_100K" else "Fetni endpoint addition at800.15 K then held; source alternative")
        if name == "cp_fetni_end":
            out["cp"]["sourceRange_K"] = [298.15, 800.15]
    if "alpha" in out:
        evidence, weak = evidence_kind(out, ("K", "cp", "rho"))
        out["alpha"] = _record("derived", "p8:alpha:" + "|".join(out[k]["sourceId"] for k in ("K", "cp", "rho")),
                               SPEC + " A4 alpha=K/(rho cp)", phase=out["K"]["phase"], reference=mean,
                               evidence=evidence, dependencies=("K", "rho", "cp"), scope="Derived kernel diffusivity, not measured diffusivity")
        out["alpha"]["weakestInputs"] = weak
    for key, record in out.items():
        record["defaultValue"] = nominal.get(key)
        if record["defaultKind"] is None and record["kind"] not in {"legacyEstimate", "userInput", "modelConvention", "derived"}:
            record["defaultKind"] = record["kind"]
    return out


def evidence_kind(provenance, physical_keys):
    """Per-value source labels; software/request/convention leaves stay excluded."""
    weak = [key for key in physical_keys if key not in provenance or provenance[key]["sourceEvidenceKind"] == "Unresolved"]
    if weak:
        return "Unresolved", weak
    if any(provenance[key]["sourceEvidenceKind"] == "User input" for key in physical_keys):
        return "User input", []
    return "Literature estimate", []


def source_evidence_kind(provenance, physical_keys):
    """Convenience label API for the integration owner."""
    return evidence_kind(provenance, physical_keys)[0]


def _exact(value):
    return float(value).hex() if type(value) in (int, float) else value


def deduplicate(records, module):
    """First ID wins; same numbers with different source IDs remain distinct."""
    seen, result = {}, []
    for row in records:
        identity = tuple((k, _exact(row["inputs"].get(k)), row["inputProvenance"][k]["sourceId"])
                         for k in ACTIVE_INPUTS[module])
        if identity in seen:
            result[seen[identity]]["aliasArmIds"].append(row["armId"])
        else:
            seen[identity] = len(result)
            result.append(copy.deepcopy(row))
    return result


def secondary_manifests(registry):
    """Closed IN625/IN718/316L default declarations, without physical fills.

    These are metadata manifests, not successful numerical outputs. Optional
    explicit IN625 vapour selection is a named source arm; it never changes
    the empty nominal nor admits that alloy to the cavity model.
    """
    result = {}
    for alloy, optics in (("in625", [.28, .40]), ("in718", [.28, .38]), ("ss316l", [.28, .31])):
        props = (registry.thermal_props(alloy) or {}) if alloy != "in625" else {}
        kp = (registry.kernel_properties(alloy, 293.15) or {}) if alloy != "in625" else {}
        tl = kp.get("T_liq_K", props.get("liquidus_C") + 273.15 if props.get("liquidus_C") is not None else None)
        k = kp.get("kernel_conductivity_W_mK", props.get("thermal_conductivity_melt_W_mK"))
        cp = kp.get("kernel_specific_heat_J_kgK", props.get("specific_heat_melt_J_kgK"))
        rho = kp.get("kernel_density_kg_m3", props.get("density_kg_m3"))
        alpha = k / (cp * rho) if all(value is not None for value in (k, cp, rho)) else None
        tref = tl + 250 if tl is not None else None
        s = dict(P=200., v=.8, d=80e-6, T0=293.15, Tl=tl,
                 K=k, cp=cp, rho=rho, alpha=alpha,
                 A=props.get("absorptivity_IR"), Tv=None, Lv=None, M=None,
                 kl=props.get("thermal_conductivity_liquid_W_mK"), cpl=props.get("specific_heat_liquid_J_kgK"),
                 rhol=props.get("density_liquid_kg_m3"), slope=-.00089 if alloy == "ss316l" else -.0004,
                 mu=.196 * math.exp(5848 / tref) * 1e-3 if alloy == "in718" and tref else .007 if alloy == "ss316l" else None,
                 L=80e-6, deltaT=500., Tref=tref, accommodation=1., effectiveNetFactor=.8, recoil=.6, emissivity=.35)
        rows = []
        def add(name, family, patch=None):
            state = {**s, **(patch or {})}
            if patch and "d" in patch:
                state["L"] = state["d"]
            if patch and "deltaT" in patch and tl is not None:
                state["Tref"] = tl + state["deltaT"] / 2
                if alloy == "in718":
                    state["mu"] = .196 * math.exp(5848 / state["Tref"]) * 1e-3
            provenance = input_provenance(alloy, name, state, s)
            melt_entries = getattr(registry, "MELT_POINT_PROPERTIES", {})
            melt = melt_entries.get(alloy)
            if melt is not None:
                for key in ("K", "cp"):
                    provenance[key] = _record("sourceDefault" if alloy == "in718" else "alloyTransfer",
                        "p7b:melting-point:" + alloy + ":" + key, melt["source"] + "; " + melt["locator"],
                        source=melt["source"], phase="liquid", reference=melt["evaluationTemperature_C"] + 273.15,
                        scope="Melting-point conduction constant with room density; SS316 to316L transfer, source/repo liquidus differ" if alloy == "ss316l" else "Source melting-point conduction constant with room density")
            provenance["slope"] = _record("sourceModelAssumption", "p8:secondary-slope:" + alloy,
                "Khairallah 2016 p.38 Sec.2.2 sigma=3.282-.00089T" if alloy == "ss316l" else "Mills 2006 p.630 Eq.24",
                phase="liquid", reference=state["Tref"], scope="Source-model assignment" if alloy == "ss316l" else "Clean Ni-alloy zero-O/S assumption; not specimen measurement")
            if alloy == "in718":
                provenance["mu"] = _record("followsInput", "mills2002:in718:viscosity:Eq6", "Mills 2002 p.186 Eq.6",
                    phase="liquid", reference=state["Tref"], follows="referenceTemperature_K", dependencies=("Tref",),
                    scope="Temperature extrapolation; source range not established in inspected record")
                provenance["mu"]["defaultKind"] = "sourceDefault"
            elif alloy == "ss316l":
                provenance["mu"] = _record("alloyTransfer", "mills2002:316:viscosity0.007", "Mills 2002 p.142 Table 1",
                    phase="liquid", reference=1773.15, scope="Estimated 316 value transferred to316L; about30 percent uncertainty, not a viscosity law")
            if name == "slope_commercial_mills":
                provenance["slope"] = _record("sourcedAlternative", "mills2002:in718:commercial-slope", "Mills 2002 p.187 Eq.8; P8 A2",
                    phase="liquid", reference=state["Tref"], scope="Sample preset approximately10ppm totalS, source above1993K; no soluble chemistry inferred")
            if name == "vapour_melt_in625_raoult":
                for key in ("Tv", "Lv", "M"):
                    provenance[key] = _record("derived", "melt:in625:raoult:table-weighted:" + key,
                        "MELT section2.5 source preset; " + SPEC + " A3", phase="vapour", reference=3001.,
                        scope="Explicit IN625 Raoult all-CC/table-weighted research alternative; cavity chain not admitted")
            missing = [key for key in ACTIVE_INPUTS["surfaceBalance"] if state.get(key) is None]
            rows.append(dict(armId=name, family=family, label=name, onsetEvent=None,
                changes=[dict(input=k, value=state[k], nominalAnchor=s[k], provenance=provenance[k])
                         for k in state if state[k] != s[k]], aliasArmIds=[], inputs=state,
                inputProvenance=provenance, prerequisiteNulls=missing))
        add("nominal", "nominal")
        for a in optics:
            add(f"absorptance_{a:g}", "absorptance", {"A": a})
        for factor in [.95, 1.05]:
            add(f"power_{factor:g}", "process", {"P": s["P"] * factor})
            add(f"beam_{factor:g}", "process", {"d": s["d"] * factor})
        for delta in [250., 1000.]:
            add(f"deltaT_{delta:g}", "flow-assumption", {"deltaT": delta})
        for factor in [.5, 2.]:
            add(f"length_{factor:g}", "flow-assumption", {"L": s["d"] * factor})
        if alloy == "in718":
            add("slope_commercial_mills", "property-tuple", {"slope": -.00011})
        add("accommodation_effective_0.82", "flow-assumption", {"effectiveNetFactor": .82})
        if alloy == "in625":
            add("vapour_melt_in625_raoult", "vapour-source", {"Tv": 3001., "Lv": 6479525.6, "M": .0559725})
        marangoni = deduplicate([r for r in rows if r["family"] != "vapour-source"], "marangoni")
        surface = deduplicate([r for r in rows if not r["armId"].startswith(("deltaT_", "length_", "slope_"))], "surfaceBalance")
        for module, entries in (("marangoni", marangoni), ("surfaceBalance", surface)):
            for row in entries:
                row["prerequisiteNulls"] = [k for k in ACTIVE_INPUTS[module] if row["inputs"].get(k) is None]
                row["availability"] = "unavailable" if row["prerequisiteNulls"] else "available"
                row["reasonCode"] = ("MARANGONI_VISCOSITY_INPUT_REQUIRED" if module == "marangoni" and row["inputs"]["mu"] is None else
                    "SURFACE_VAPOUR_INPUT_REQUIRED" if module == "surfaceBalance" and any(row["inputs"][k] is None for k in ("Tv", "Lv", "M")) else
                    "RESEARCH_INPUT_REQUIRED" if row["prerequisiteNulls"] else None)
        result[alloy] = {"marangoni": {"n": len(marangoni), "manifest": marangoni},
                         "surfaceBalance": {"n": len(surface), "manifest": surface},
                         "cavityAdmission": "ALLOY_CONSTANT_CHAIN_NOT_ADMITTED"}
    return result


def check():
    fixture = json.loads(Path(__file__).with_name("p8_amendment1_synthetic.json").read_text(encoding="utf-8"))
    found = 0
    def visit(obj):
        nonlocal found
        if isinstance(obj, dict):
            if "armResults" in obj:
                rows = obj["armResults"]
                nominal = next(r["inputs"] for r in rows if r["armId"] == "nominal")
                # Primary fixture rows are disambiguated by their vapour/solid tuple.
                for row in rows:
                    alloy = "ti6al4v" if nominal["Tv"] == 3560 else "alsi10mg"
                    records = input_provenance(alloy, row["armId"], row["inputs"], nominal)
                    assert set(records) == set(row["inputs"])
                    assert all(r["kind"] in KINDS for r in records.values())
                    assert all(r["sourceId"] and "sourceLocator" in r and "phase" in r and "referenceTemperature_K" in r and "sourceRange_K" in r for r in records.values())
                    assert all("locator" not in r for r in records.values())
                    if row["armId"] in {"vapour_3360", "vapour_3760"}:
                        assert records["Tv"]["kind"] == "declaredAssumption" and records["Tv"]["sourceEvidenceKind"] == "Unresolved"
                    if row["armId"] == "vapour_o8":
                        assert records["Tv"]["sourceRange_K"] == [600., 1730.] and O8 in records["Tv"]["sourceLocator"]
                    found += 1
            for value in obj.values():
                visit(value)
        elif isinstance(obj, list):
            for value in obj:
                visit(value)
    visit(fixture)
    assert found > 0
    class EmptyRegistry:
        def thermal_props(self, alloy):
            return {}
        def kernel_properties(self, alloy, preheat):
            return {}
    # Exercise the exact source-only registry the integration fixture passes.
    # Read only this named source blob; no solver imports, papers or datasets.
    repo = Path(__file__).resolve().parents[3]
    source = subprocess.check_output(["git", "show", LEDGER], cwd=repo, text=True, encoding="utf-8")
    registry = types.ModuleType("p8_provenance_check_registry")
    exec(compile(source, LEDGER, "exec"), registry.__dict__)
    secondary = secondary_manifests(registry)
    for registry_input in (EmptyRegistry(), registry):
        tested = secondary_manifests(registry_input)
        for alloy, n in (("in625", 7), ("in718", 8), ("ss316l", 7)):
            assert tested[alloy]["marangoni"]["n"] == n
            assert tested[alloy]["surfaceBalance"]["n"] == (9 if alloy == "in625" else 8)
            assert tested[alloy]["cavityAdmission"] == "ALLOY_CONSTANT_CHAIN_NOT_ADMITTED"
    assert secondary["in718"]["marangoni"]["manifest"][0]["inputs"]["Tref"] == 1859.15
    assert secondary["ss316l"]["marangoni"]["manifest"][0]["inputs"]["Tref"] == 1923.15
    assert secondary["in625"]["marangoni"]["manifest"][0]["inputs"]["mu"] is None
    assert evidence_kind({"mu": _assumption("mu", "test")}, ("mu",))[0] == "Unresolved"
    user = _record("userInput", "test:user")
    assert source_evidence_kind({"mu": user}, ("mu",)) == "User input"
    assert source_evidence_kind({"mu": user, "cp": _assumption("cp", "test")}, ("mu", "cp")) == "Unresolved"
    assert source_evidence_kind({"mu": _record("sourceDefault", "test:source"), "P": user}, ("mu",)) == "Literature estimate"
    print(f"P8 provenance check PASS: {found} primary arm records; BASE835466fa secondary counts7/8/7 and9/8/8; label precedence and request exclusion; no target data")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check source metadata against the local synthetic fixture")
    args = parser.parse_args()
    if not args.check:
        parser.error("This metadata helper is importable; use --check to verify it")
    check()
