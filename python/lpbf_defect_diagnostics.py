"""Geometric LPBF screening; these outputs are not defect probabilities.

The overlap criterion assumes identical, aligned semi-elliptical melt pools.
W is full width and D is penetration depth. At the midpoint between tracks,
the ellipse ordinate is D sqrt(1 - (H/W)^2); requiring it to reach the previous
layer gives (H/W)^2 + (T/D)^2 <= 1. Solving for H gives maximumHatch_um.
No material-specific empirical correction is applied.
"""

import math
from numbers import Real


MODEL_ID = "elliptic-overlap-screening-v2"
# v2: balling block semantics changed at d92d1a3a (band only from balling_screen(); risk null otherwise); geometry rule unchanged.

# ---------------------------------------------------------------------------------------------
# Balling / track-instability screen: ONE rule for every LPBF path. It replaces the frozen
# steady-Rosenthal L/W > 3.8 flag, the L/W > pi rules and the process-map Pe > 4 rule.
#
# Input: the liquidus L/W of the Eagar-Tsai kernel (eagar-tsai-v2, beam-size aware; Eagar & Tsai
# 1983). The point-source Rosenthal L/W depends on P*v only (no beam radius).
# Moderate: L/W > pi*sqrt(3/2) = 3.847. Yadroitsev et al. 2010 (J. Mater. Process. Technol. 210:1624, sec. 3.3)
#   derive the capillary stability of a segmental liquid cylinder on a substrate, Eq. (12); for the full
#   cylinder (contact angle pi) Eq. (13) gives pi*D/L > sqrt(2/3), i.e. L/D < pi*sqrt(3/2), with D the
#   CYLINDER diameter and L the disturbance wavelength. Gusarov, Yadroitsev, Bertrand & Smurov 2007
#   (Appl. Surf. Sci. 254:975, sec. 3-4) give the mechanism: the remelted track behaves as a liquid
#   cylinder and breaks up when its length exceeds its circumference (Plateau-Rayleigh, free cylinder,
#   L/D_cyl > pi); substrate contact stabilises it. In their 316L example at the onset (v ~ 20-24 cm/s)
#   the pool is L ~ 300 / W ~ 150 / h 50 um -> D_cyl ~ 100 um: L/circumference ~ 1 while pool L/W ~ 2.
#   The bound is written pi*W/L < sqrt(2/3) in Sheikh et al. 2023 (arXiv 2304.04113, Eq. 7) and tabulated
#   in Katagiri et al. 2023 (Materials 16:1729, Table 2), both of which also cite Gusarov & Smurov 2010
#   (Phys. Procedia 5:381) -- that paper is not in the repo and was not checked against its text.
#   Applied here to the MODEL pool L/W as a proxy for wavelength / cylinder diameter: advisory only.
# High band: REMOVED (P7b, 2026-10-14, G1 audit V09). P7a kept a 316L-only High advisory fitted in sample on the
#   Eagar-Tsai geometry of the fitting commit f3ba9896 (Hofmann et al. 316L single tracks, Zenodo
#   10.5281/zenodo.16979848, 677 tracks, 216 balling-flagged); P7b changes that geometry (the absorptivity authority
#   and the melting-point and kernel-ledger properties move the Eagar-Tsai L/W), so the in-sample edge 5.5 no longer
#   corresponds to the served L/W. No alloy reports High (highBandApplicable False everywhere); Moderate (3.85,
#   Yadroitsev proxy) and Stable stay with their disclosure. The Hofmann balled fractions per L/W bin are kept as
#   recorded evidence (BALLING_SCREEN_EVIDENCE, bins as recorded at the fitting commit), not as a threshold.
# No depth (D/W) exemption: an earlier D/W < 1.2 clause was fitted to two Hofmann rows. KU Leuven tracks
# with a high L/W (regime-labelled, no balling label) are keyhole-mode cells (dH/h_s >= 53), risky by the regime
# classifier since P7a (the former do-not-print edge 35 is gone); not all of them are deep keyholes
# (Ti-6Al-4V 200 W / 2000 mm/s / 37.5 um: measured D/W 62/90 = 0.69).
# ---------------------------------------------------------------------------------------------
BALLING_SCREEN_MODEL_ID = "eagar-tsai-aspect-balling-screen-v1"
BALLING_SCREEN_KERNEL = "eagar-tsai-v2"
BALLING_LW_MODERATE = math.pi * math.sqrt(1.5)
BALLING_LW_RELATIVE_UNCERTAINTY = 0.10
# Evidence bin edges of the recorded Hofmann balled fractions (fitting-commit geometry); not a served threshold.
HOFMANN_EVIDENCE_LW_EDGES = (BALLING_LW_MODERATE, 4.5, 5.5)
BALLING_HIGH_BAND_BASIS = ("no High band since P7b (2026-10-14): the former in-sample 316L edge 5.5 was fitted on the "
                           "Eagar-Tsai geometry of the fitting commit and that geometry changed (absorptivity authority, "
                           "melting-point and kernel-ledger properties); Moderate (3.85, Yadroitsev et al. 2010 Eq. 13 "
                           "proxy) and Stable are the only bands, advisory")


def balling_high_band_applicable(material_name):
    """Always False since P7b: no alloy reports the removed High band (kept for callers that ask)."""
    return False
BALLING_SCREEN_SOURCES = (
    "Yadroitsev, Gusarov, Yadroitsava & Smurov 2010, J. Mater. Process. Technol. 210:1624 (doi "
    "10.1016/j.jmatprotec.2010.05.010), sec. 3.3 Eq. (12)-(13): segmental-cylinder capillary stability, full-cylinder "
    "limit pi*D/L > sqrt(2/3), i.e. L/D < pi*sqrt(3/2) = 3.85 with D the cylinder diameter (Moderate, advisory)",
    "Gusarov, Yadroitsev, Bertrand & Smurov 2007, Appl. Surf. Sci. 254:975 (doi 10.1016/j.apsusc.2007.08.074), "
    "sec. 3-4: balling above ~20 cm/s (316L, 50 um layer) explained by the Plateau-Rayleigh break-up of the remelted "
    "cylinder when its length exceeds its circumference; substrate contact stabilises (mechanism, no threshold on pool L/W)",
    "Hofmann et al. 316L single tracks, Zenodo 10.5281/zenodo.16979848 (Mater. Des. 262 (2026) 115459): "
    "recorded balled fractions per Eagar-Tsai L/W bin at the fitting commit (evidence only; the former High "
    "threshold derived from them was removed in P7b)",
    "Eagar & Tsai 1983, Welding J. 62:346s: beam-size-aware kernel that supplies L and W",
)
# Hofmann 316L balled fraction per Eagar-Tsai L/W band (Wave B geometry, all layers, 677 tracks).
BALLING_SCREEN_EVIDENCE = {
    "dataset": "hofmann-316l-2026 (10.5281/zenodo.16979848), 677 tracks, 216 balling-flagged",
    "geometryImplementationHash": "f3ba98969a723702d9dbe15ae623d28f1327356441919ffdd6edf4e74a6a150d",
    "aucEagarTsaiLW": 0.873,
    "aucEagarTsaiLWBarePlate": 0.984,
    "bandBalledFraction": {
        "stable (<= 3.85)": "34/361",
        "moderate (3.85-4.5]": "42/130",
        "moderate (4.5-5.5]": "71/115",
        "high (> 5.5)": "69/71",
    },
    "highThresholdCounts": {"truePositive": 69, "falsePositive": 2, "positives": 216, "negatives": 461},
    "moderateThresholdCounts": {"truePositive": 182, "falsePositive": 134, "positives": 216, "negatives": 461},
    "limits": ("calibrated in-sample on one 316L dataset (Aconity Midi, 50-140 um spots); not validated for "
               "IN718, Ti-6Al-4V or other alloys (no labelled balling set in the repo); the NIST AMB2022-03 IN718 "
               "285 W / 960 mm/s track is continuous at Eagar-Tsai L/W ~5.1 (Moderate); low-energy powder-layer "
               "balling is not captured by L/W; experimentalValidation=false"),
}


def _balling_band_rate(lw):
    """Recorded Hofmann balled fraction of the evidence bin the L/W falls in (evidence, not a band)."""
    rates = BALLING_SCREEN_EVIDENCE["bandBalledFraction"]
    if lw > HOFMANN_EVIDENCE_LW_EDGES[2]:
        return rates["high (> 5.5)"]
    if lw > HOFMANN_EVIDENCE_LW_EDGES[1]:
        return rates["moderate (4.5-5.5]"]
    if lw > BALLING_LW_MODERATE:
        return rates["moderate (3.85-4.5]"]
    return rates["stable (<= 3.85)"]


def balling_screen(length_um, width_um, depth_um, extent_status, material_name=None):
    """Eagar-Tsai aspect-ratio balling screen (see the block comment above).

    ``length_um``/``width_um``/``depth_um`` are the liquidus extents of the Eagar-Tsai kernel and
    ``extent_status`` its meltPoolGeometry.extentStatus. Returns a JSON-compatible dict whose
    ``band`` is "moderate", "stable", or None when the Eagar-Tsai extent is not a computed isotherm
    (unavailable: no band is assigned). Since P7b no alloy reports "high" (``highBandApplicable`` is
    always False); ``material_name`` is accepted for the callers that pass it.
    """
    status = str(extent_status) if extent_status is not None else "not-reported"
    high_applicable = balling_high_band_applicable(material_name)
    lw = None
    dw = None
    try:
        L, Wd, D = float(length_um), float(width_um), float(depth_um)
        if math.isfinite(L) and math.isfinite(Wd) and math.isfinite(D) and Wd > 0:
            lw = L / Wd
            dw = D / Wd
    except (TypeError, ValueError):
        pass
    out = {
        "modelId": BALLING_SCREEN_MODEL_ID,
        "kernel": BALLING_SCREEN_KERNEL,
        "extentStatus": status,
        "lengthToWidth": None if lw is None else round(lw, 3),
        "depthToWidth": None if dw is None else round(dw, 3),
        "band": None,
        "moderateThreshold": round(BALLING_LW_MODERATE, 3),
        "highThreshold": None,
        "relativeUncertainty": BALLING_LW_RELATIVE_UNCERTAINTY,
        "hofmannBalledFractionInBand": None,
        "verdictEffect": "none",
        "highBandApplicable": high_applicable,
        "highBandBasis": BALLING_HIGH_BAND_BASIS,
        "basis": ("Eagar-Tsai liquidus L/W: Moderate > pi*sqrt(3/2) = 3.85 (Yadroitsev et al. 2010 Eq. 13 cylinder "
                  "bound, mechanism Gusarov et al. 2007; a wavelength/cylinder-diameter bound applied to the model pool "
                  "L/W) -> advisory only; no High band since P7b (the former in-sample 316L edge was fitted on a "
                  "geometry that P7b changed)"),
        "sources": list(BALLING_SCREEN_SOURCES),
        "evidence": BALLING_SCREEN_EVIDENCE,
        "experimentalValidation": False,
        "reason": None,
    }
    if status != "computed" or lw is None:
        out["reason"] = (f"Eagar-Tsai melt-pool extent not resolved ({status}); the balling screen is calibrated on a "
                         "computed Eagar-Tsai liquidus L/W only, so no band is assigned.")
        return out
    out["hofmannBalledFractionInBand"] = _balling_band_rate(lw)
    if lw > BALLING_LW_MODERATE:
        out["band"] = "moderate"
        out["verdictEffect"] = "advisory"
        out["reason"] = (f"Eagar-Tsai L/W {lw:.2f} > pi*sqrt(3/2) = {BALLING_LW_MODERATE:.2f} (Yadroitsev 2010 "
                         f"segmental-cylinder bound; Gusarov 2007 Plateau-Rayleigh mechanism); {out['hofmannBalledFractionInBand']} Hofmann 316L "
                         "tracks in this band balled. Advisory only.")
    else:
        out["band"] = "stable"
        out["reason"] = (f"Eagar-Tsai L/W {lw:.2f} <= pi*sqrt(3/2) = {BALLING_LW_MODERATE:.2f}; "
                         f"{out['hofmannBalledFractionInBand']} Hofmann 316L tracks in this band balled.")
    return out


def _dimension(name, value, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite real number")
    try:
        value = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite real number") from exc
    if not math.isfinite(value) or value < 0 or (positive and value == 0):
        qualifier = "positive" if positive else "nonnegative"
        raise ValueError(f"{name} must be finite and {qualifier}")
    return value


def _finite_ratio(numerator, denominator):
    if denominator == 0:
        return None
    value = numerator / denominator
    return value if math.isfinite(value) else None


def defect_diagnostics(width_um, depth_um, length_um, hatch_um, layer_um, *, aggregate=False, balling=None):
    """Return finite JSON-compatible geometry screens or explicit unresolved values.

    Dimensions are micrometres. Invalid inputs raise ValueError. ``aggregate``
    denotes bounding dimensions of multiple tracks, which cannot be screened as
    a single melt-pool cross-section. Null risks mean physically unresolved.
    ``balling`` is a ``balling_screen()`` result (Eagar-Tsai L/W). Without it no balling
    risk is assigned: the screen is not calibrated on any other geometry.
    """
    width = _dimension("width_um", width_um)
    depth = _dimension("depth_um", depth_um)
    length = _dimension("length_um", length_um)
    hatch = _dimension("hatch_um", hatch_um, positive=True)
    layer = _dimension("layer_um", layer_um, positive=True)
    if not isinstance(aggregate, bool):
        raise ValueError("aggregate must be a boolean")
    if balling is not None and not (isinstance(balling, dict) and balling.get("modelId") == BALLING_SCREEN_MODEL_ID):
        raise ValueError("balling must be a balling_screen() result")

    limitations = [
        "Geometric screening only; no pore probability, porosity estimate, or certification.",
        "Requires local single-track width and penetration depth for an aligned semi-elliptical cross-section.",
        "Ignores local pool fluctuations, track registration, powder packing, and remelting history.",
        "Accuracy depends on supplied geometry; Rosenthal-derived dimensions can fail this screen.",
        "No Ti-6Al-4V-specific correction or universal keyhole/balling threshold is applied.",
    ]
    lof = {
        "status": "unresolved", "ellipseIndex": None, "signedMargin": None,
        "overlapDepth_um": None, "maximumHatch_um": None, "riskScreened": None,
        "reason": None,
    }
    result = {
        "modelId": MODEL_ID,
        "scope": "aggregate-multi-track" if aggregate else "single-track-cross-section",
        "status": "unresolved", "limitations": limitations,
        "lackOfFusion": lof,
        "keyhole": {
            "depthToWidth": None, "risk": None, "kingModeIndicator": None,
            "reason": "Aspect ratio alone cannot resolve vapor depression stability or keyhole pore formation.",
        },
        "balling": {
            "lengthToWidth": None, "risk": None,
            "reason": "Elongation alone cannot resolve capillary breakup, wetting, or track continuity.",
        },
        "gasPore": {"risk": None, "reason": "Gas inventory, transport, and pore nucleation are not resolved."},
        "porosity": {"value": None, "reason": "Geometry screening does not predict volumetric porosity."},
        "provenance": [{
            "title": "Harkin et al. (2023), Equation 5",
            "url": "https://link.springer.com/article/10.1007/s00170-023-11163-0",
            "use": "Semi-elliptical overlap criterion; empirical material-specific correction excluded.",
        }],
    }
    if aggregate:
        lof["reason"] = "Aggregate bounding dimensions do not identify local inter-track or inter-layer overlap."
        return result

    result["keyhole"]["depthToWidth"] = _finite_ratio(depth, width)
    result["balling"]["lengthToWidth"] = _finite_ratio(length, width)
    # Balling: one screen (balling_screen, Eagar-Tsai L/W). The L/W of the geometry given here is
    # reported but not banded: the thresholds are not calibrated on Rosenthal, Goldak or transient L/W.
    if balling is None:
        result["balling"]["reason"] = (
            "No balling risk from this geometry: the balling screen uses the Eagar-Tsai liquidus L/W "
            f"({BALLING_SCREEN_MODEL_ID}), which was not supplied for this result.")
    else:
        result["balling"]["screen"] = balling
        result["balling"]["risk"] = {"high": "high", "moderate": "moderate", "stable": "low"}.get(balling["band"])
        result["balling"]["reason"] = balling["reason"]
        result["provenance"].append({
            "title": "Yadroitsev et al. (2010) Eq. 13; Gusarov et al. (2007); Hofmann et al. 316L tracks (Zenodo 16979848)",
            "url": "https://doi.org/10.1016/j.jmatprotec.2010.05.010",
            "use": ("Eagar-Tsai L/W balling screen: Moderate > pi*sqrt(3/2) = 3.85 (literature bound, advisory), "
                    "Hofmann 316L balled fractions per L/W bin recorded as evidence (no High band since P7b)."),
        })

    # Keyhole: no stability/porosity verdict from D/W alone (see limitations; risk stays None). The
    # King et al. 2014 sec. 5.2 classification (keyhole mode when depth > half-width, D/W > 0.5) is
    # reported as a mode indicator only. The old 1.5 / 1.0 thresholds are in neither King 2014 nor
    # Cunningham 2019.
    aspect_ratio = _finite_ratio(depth, width)
    if aspect_ratio is not None:
        mode = "keyhole-mode" if aspect_ratio > 0.5 else "conduction-mode"
        result["keyhole"]["kingModeIndicator"] = mode
        result["keyhole"]["reason"] = (
            f"D/W {aspect_ratio:.2f} {'>' if aspect_ratio > 0.5 else '<='} 0.5: {mode} by the King et al. 2014 "
            "depth > half-width classification. Aspect ratio alone cannot resolve vapor depression stability "
            "or keyhole pore formation, so no risk is assigned.")
        result["provenance"].append({
            "title": "King et al. (2014), J. Mater. Process. Technol. 214, 2915, sec. 5.2",
            "url": "https://doi.org/10.1016/j.jmatprotec.2014.06.005",
            "use": "Keyhole-mode classification when melt-pool depth exceeds the half-width (D/W > 0.5); label only.",
        })

    if width == 0 or depth == 0:
        lof.update({
            "status": "no-melt" if width == 0 else "inadequate-penetration",
            "overlapDepth_um": 0.0, "maximumHatch_um": 0.0, "riskScreened": True,
            "reason": "Zero width or penetration cannot cover a positive hatch and layer thickness.",
        })
        result["status"] = "geometry-screened"
        return result

    h_ratio = _finite_ratio(hatch, width)
    t_ratio = _finite_ratio(layer, depth)
    # The piecewise form avoids overflow in squares outside the ellipse.
    lof["overlapDepth_um"] = (
        depth * math.sqrt(max(0.0, (1 - h_ratio) * (1 + h_ratio)))
        if h_ratio is not None and h_ratio < 1 else 0.0
    )
    lof["maximumHatch_um"] = (
        width * math.sqrt(max(0.0, (1 - t_ratio) * (1 + t_ratio)))
        if t_ratio is not None and t_ratio < 1 else 0.0
    )
    index = None if h_ratio is None or t_ratio is None else h_ratio * h_ratio + t_ratio * t_ratio
    if index is None or not math.isfinite(index):
        lof["reason"] = "Dimension ratios exceed finite floating-point range; overlap index is unresolved."
        return result
    margin = 1.0 - index
    # Classification uses the reported index, without an empirical safety band.
    marginal = index == 1.0
    lof.update({
        "ellipseIndex": index, "signedMargin": margin,
        "status": "marginal" if marginal else ("lack-of-fusion-screened" if index > 1 else "covered-geometrically"),
        "riskScreened": None if marginal else index > 1,
        "reason": "Only the idealized elliptical overlap condition is evaluated.",
    })
    result["status"] = "geometry-screened"
    return result
