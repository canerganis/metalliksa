#!/usr/bin/env python3
"""Heiple–Roper Marangoni screening (PROOF 020). Not CFD and not a W/D fit."""
import sys

from lpbf_thermal_solver import calculate_meltpool_physics
from marangoni_screening import heiple_roper_d_gamma_dT, marangoni_screening


def assert_true(cond, msg):
    if not cond:
        raise AssertionError(msg)


def main():
    d_pure = -0.00045
    assert_true(heiple_roper_d_gamma_dT(d_pure, 10.0) < 0.0, "10 ppm stays outward")
    assert_true(heiple_roper_d_gamma_dT(d_pure, 80.0) > 0.0, "80 ppm inverts")
    mid = heiple_roper_d_gamma_dT(d_pure, 45.0)
    assert_true(abs(mid) < abs(d_pure), "45 ppm is inside the inversion band")

    ma = marangoni_screening(d_pure, 0.006, 4e-6, 6980.0, 70e-6, 2000.0, 1400.0, sulfur_ppm=15.0)
    assert_true(ma["modelId"] == "marangoni-heiple-v1", "model id")
    assert_true(ma["flowDirection"] == "outward", "default flow")
    assert_true(ma["geometrySource"] == "thermal", "does not own W/D")

    lo = calculate_meltpool_physics(
        "316L Stainless Steel", 200, 800, 70, 80, 30, 100, heat_source="goldak", sulfur_ppm=10
    )
    hi = calculate_meltpool_physics(
        "316L Stainless Steel", 200, 800, 70, 80, 30, 100, heat_source="goldak", sulfur_ppm=80
    )
    assert_true(lo["marangoniModel"]["flowDirection"] == "outward", "316L low-S outward")
    assert_true(hi["marangoniModel"]["flowDirection"] == "inward", "316L high-S inward")
    # Geometry is thermal — sulfur must not silently refit W/D.
    assert_true(
        abs(lo["meltPoolGeometry"]["width_um"] - hi["meltPoolGeometry"]["width_um"]) < 0.2,
        "sulfur does not change W",
    )

    ros = calculate_meltpool_physics("Inconel 718", 285, 960, 80, 80, 40, 110)
    assert_true(ros["modelId"] == "rosenthal-screening-v1", "Build Job path untouched")
    # P1 (2026-10-11): the Rosenthal increment heuristic was removed; every kernel serves the Fabbro leg.
    assert_true(ros["keyholeModel"]["modelId"] == "fabbro-keyhole-v1", "Rosenthal serves the Fabbro keyhole leg after P1")

    print("PASS: Heiple–Roper Marangoni screening")
    return 0


if __name__ == "__main__":
    sys.exit(main())
