"""Depth-bias note for the served melt-pool depth (reporting only, outside the frozen LPBF physics).

The served depth_um is a conduction isotherm depth plus an uncited keyhole increment. On the IN625 held-out checks
(research notes 2026-10-10) it was biased in a direction that depends on the regime label. This module only builds
a plain-text note from the regime label and the alloy name. It reads no solver internals, changes no regime
threshold and no depth number, and claims nothing validated (experimentalValidation stays false).

The TypeScript mirror is src/utils/depthBiasWarning.ts; python/test_lpbf_depth_bias.py pins both texts equal.
"""
from typing import Any, Dict, Optional

UNDER = "likely-underestimated"
OVER = "may-overestimate"

UNDER_TEXT = (
    "Depth is likely underestimated. The served depth is a conduction estimate. On IN625 single tracks in the "
    "Transition band by this label (Lane et al. CBM tracks, 150 W at 400 mm/s and 195 W at 800 mm/s, beam about "
    "100 um, enthalpy index 19.45 and 17.88) the observed depth to half-width ratio was 1.4 to 1.8 and conduction "
    "models gave about 0.5 times the observed depth. This is a screening note from a small held-out check, not a validated correction."
)
UNDER_BASIS = (
    "Held-out IN625 check, Lane et al. CBM tracks (n=2); research notes RESULTS_lane_ab_latent_check_2026-10-10 "
    "and RESULTS_ke_width_n3_2026-10-10. Alloys other than IN625 have no such check."
)
OVER_TEXT = (
    "Depth may be overestimated. In our held-out checks, conduction depth estimates overpredicted conduction-mode "
    "IN625 tracks (AMMT, beam 170 um, enthalpy index about 7.4 to 8.1) by about 1.5 times. This is a screening note "
    "from a small check, not a validated correction."
)
OVER_BASIS = (
    "Held-out IN625 check, AMMT tracks; research notes RESULTS_ke_width_n3_2026-10-10 and "
    "SOURCES_ke_scaling_2026-10-10."
)


def depth_bias_warning(regime: Optional[str], material_name: Optional[str]) -> Dict[str, Any]:
    """{direction, text, basis}; direction is None (text/basis None) when no note applies."""
    r = str(regime or "").lower()
    is_in625 = "625" in str(material_name or "").lower()
    if r.startswith("transition") or r.startswith("keyhole"):
        return {"direction": UNDER, "text": UNDER_TEXT, "basis": UNDER_BASIS}
    if r.startswith("conduction") and is_in625:
        return {"direction": OVER, "text": OVER_TEXT, "basis": OVER_BASIS}
    return {"direction": None, "text": None, "basis": None}


def attach_depth_bias_warning(result: Dict[str, Any]) -> Dict[str, Any]:
    """Add meltPoolGeometry.depthBiasWarning to a solver result dict in place (no other key touched)."""
    geometry = result.get("meltPoolGeometry")
    if isinstance(geometry, dict):
        geometry["depthBiasWarning"] = depth_bias_warning(geometry.get("regime"), result.get("material"))
    return result
