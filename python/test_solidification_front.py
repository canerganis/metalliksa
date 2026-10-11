#!/usr/bin/env python3
"""Field G/R on the rear liquidus (PROOF 021; P6 containment 2026-10-11). Does not change Build Job verdict."""
import sys

from lpbf_thermal_solver import calculate_meltpool_physics
from solidification_front import (
    GRADIENT_SOURCE_CONDUCTION_INTERFACE, MODEL_ID, UNAVAILABLE_FEW_SAMPLES, UNAVAILABLE_KEYHOLE_LEG,
    evaluate_solidification, hunt_morphology, pdas_band_um, phase_transformation_note)


def assert_true(cond, msg):
    if not cond:
        raise AssertionError(msg)


def main():
    # Conduction case (316L 200 W / 800 mm/s / 70 um, Goldak): the served depth is the conduction isotherm, so the
    # conduction-field interface is served.
    gk = calculate_meltpool_physics(
        "316L Stainless Steel", 200, 800, 70, 80, 30, 100, heat_source="goldak"
    )
    assert_true(gk["meltPoolGeometry"]["keyholeVaporCavityDepth_um"] == 0.0, "conduction case: no keyhole leg")
    kin = gk["solidificationKinetics"]
    assert_true(kin["modelId"] == MODEL_ID, "solidification model id")
    assert_true(kin["usedFieldMap"] is True, "Goldak uses field G/R")
    assert_true(kin["gradientSource"] == GRADIENT_SOURCE_CONDUCTION_INTERFACE, "labelled conduction-field interface")
    assert_true(kin["unavailableReason"] is None, "available")
    G = kin["thermalGradient_G_K_m"]
    R = kin["solidificationRate_R_m_s"]
    Tdot = kin["coolingRate_K_s"]
    # P7a (2026-10-11): no PDAS scalar; 316L has no sourced PDAS parameters, so the band is null with a reason.
    assert_true(kin["primaryDendriteArmSpacing_PDAS_um"] is None, "no PDAS scalar since P7a")
    assert_true(kin["secondaryDendriteArmSpacing_SDAS_um"] is None, "no SDAS since P7a")
    assert_true(kin["pdasBand_um"] is None and "no sourced PDAS parameters" in kin["pdasUnavailableReason"], "316L: no band")
    # LPBF order of magnitude: G ~ 10^5-10^8 K/m, Tdot ~ 10^4-10^7 K/s.
    assert_true(1.0e5 <= G <= 5.0e8, f"Goldak G {G}")
    assert_true(0.02 <= R <= 1.0, f"Goldak R {R} vs v=0.8 m/s")
    assert_true(1.0e4 <= Tdot <= 2.0e8, f"Goldak cooling {Tdot}")
    band = pdas_band_um(1e6, 0.5, "Inconel 718")["pdasBand_um"]
    assert_true(abs(band["hunt"] - 1.137) < 1e-3 and abs(band["kurzFisher"] - 3.092) < 1e-3, "Ghosh 2017 band at the anchor")
    assert_true(kin["phaseTransformation"]["alloyClass"] == "316L", "316L phase note")
    assert_true(gk["modelId"] == "goldak-half-space-v3", "Goldak half-space power normalization")

    # Keyhole-leg case (IN718 285 W / 960 mm/s / 67 um, Goldak): the served depth is the Fabbro leg, so G/R are null.
    kh = calculate_meltpool_physics("Inconel 718", 285, 960, 67, 23.5, 40, 110, heat_source="goldak")
    assert_true(kh["meltPoolGeometry"]["keyholeVaporCavityDepth_um"] > 0.0, "keyhole-leg case")
    kk = kh["solidificationKinetics"]
    assert_true(kk["thermalGradient_G_K_m"] is None and kk["coolingRate_K_s"] is None, "null on the keyhole leg")
    assert_true(kk["primaryDendriteArmSpacing_PDAS_um"] is None and kk["microstructureMorphology"] is None, "PDAS/morphology null")
    assert_true(kk["unavailableReason"] == UNAVAILABLE_KEYHOLE_LEG, kk["unavailableReason"])
    assert_true(kk["gradientSource"] is None and kk["usedFieldMap"] is False, "no interface label on the keyhole leg")

    slow = calculate_meltpool_physics(
        "316L Stainless Steel", 100, 600, 70, 80, 30, 100, heat_source="goldak"
    )
    fast = calculate_meltpool_physics(
        "316L Stainless Steel", 100, 1600, 70, 80, 30, 100, heat_source="goldak"
    )
    for name, r in (("slow", slow), ("fast", fast)):
        assert_true(r["solidificationKinetics"]["solidificationRate_R_m_s"] is not None, f"{name} case served")
    assert_true(
        fast["solidificationKinetics"]["solidificationRate_R_m_s"]
        > slow["solidificationKinetics"]["solidificationRate_R_m_s"] * 0.9,
        "faster scan not slower R",
    )

    ti = calculate_meltpool_physics(
        "Ti-6Al-4V", 150, 1200, 80, 150, 30, 100, heat_source="eagar-tsai"
    )
    assert_true(ti["meltPoolGeometry"]["keyholeVaporCavityDepth_um"] == 0.0, "Ti64 conduction case")
    note = ti["solidificationKinetics"]["phaseTransformation"]
    assert_true(note["expected"] == "beta_to_alpha_prime_martensite", note)
    assert_true(ti["solidificationKinetics"]["coolingRate_K_s"] >= 410.0, "Ti64 LPBF >> 410 K/s")
    assert_true(note["doi"] == "10.1016/S0921-5093(97)00802-2", "Ahmed & Rack DOI")

    def _cold(_x, _y, _z):
        return 0.0

    # P6: a field without a sampled rear liquidus gives null with a reason; the former tail-length fallback
    # G = (T_surface - T_sol) / x_rear is gone (its keywords are still accepted and ignored).
    fb = evaluate_solidification(
        _cold,
        T_liq=1336.0,
        T_sol=1260.0,
        t_surface=2000.0,
        v_scan=0.96,
        x_rear=2.0e-4,
        x_front=8.0e-5,
        search_depth=2.0e-4,
        r_beam=3.35e-5,
        cos_theta=1.0,
        pdas_A1=75.0,
        sdas_B1=40.0,
        material_name="Inconel 718",
    )
    assert_true(fb["usedFieldMap"] is False, "cold field: no interface")
    assert_true(fb["gradientSource"] is None, "no fallback source id")
    assert_true(fb["thermalGradient_G_K_m"] is None, "no fallback G")
    assert_true(fb["unavailableReason"] == UNAVAILABLE_FEW_SAMPLES, fb["unavailableReason"])
    assert_true("tail-length" in fb["unavailableReason"], "the reason names the removed fallback")

    ros = calculate_meltpool_physics("Inconel 718", 150, 1200, 80, 80, 40, 110)
    assert_true(ros["modelId"] == "rosenthal-screening-v1", "Build Job heat source unchanged")
    assert_true(ros["solidificationKinetics"]["modelId"] == MODEL_ID, "Rosenthal also reports field G")
    assert_true(ros["solidificationKinetics"]["gradientSource"] == GRADIENT_SOURCE_CONDUCTION_INTERFACE, "Rosenthal interface")
    assert_true("solidificationCosTheta" not in ros["solidificationKinetics"], "no incline multiplier key")

    assert_true("Columnar" in hunt_morphology(1.0e8), "Hunt columnar bin")
    mart = phase_transformation_note("Ti-6Al-4V", 1.0e5)
    assert_true(mart["doi"] == "10.1016/S0921-5093(97)00802-2", "Ahmed & Rack DOI helper")
    print("PASS: solidification-front G/R (conduction-field interface, P6)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
