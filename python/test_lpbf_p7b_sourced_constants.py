"""P7b sourced constants bump (docs/research/SPEC_p7b_sourced_constants_2026-10-11.md, base sections 8 and Amendment 1
section 7): self-contained tests on pinned literals and a synthetic property set.

Every number below is a literal with its locator in a comment; no test reads a research script, a sweep report or a
record. The 49-cell fixture PRE_P7_FIXTURE was recorded at REV0 (b578da71, pin 0e1599b4) with the locked interpreter
and is pinned data, not a live call. This bump is a sourcing correction (goal G1), never a validation: nothing here
compares a served number with a measured depth.
"""
import copy
import json
import math
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import four_alloy_materials as fam  # noqa: E402
import lpbf_depth_bias as depth_bias  # noqa: E402
import lpbf_material_registry as registry  # noqa: E402
import lpbf_public_datasets as pds  # noqa: E402
import lpbf_regime_absorptivity_kernel as frozen_kernel  # noqa: E402
import lpbf_thermal_solver as ts  # noqa: E402
from eagar_tsai_solver import eagar_tsai_surface_maximum  # noqa: E402
from fabbro_keyhole import fabbro_keyhole_depth_m  # noqa: E402
from in625_thermal_material import IN625_ABSORPTIVITY_BASIS, IN625_ABSORPTIVITY_IR  # noqa: E402
from lpbf_build_job_material_snapshot import _THERMAL_REQUIRED, build_material_property_snapshot  # noqa: E402
from lpbf_defect_diagnostics import BALLING_LW_MODERATE, balling_screen  # noqa: E402
from lpbf_screening_uq import apply_uq_prop_scales  # noqa: E402
from lpbf_thermal_solver import calculate_meltpool_physics  # noqa: E402
from nist_ambench_2018_02 import IN625_VALIDATION_PROPS  # noqa: E402

ROOT = os.path.dirname(HERE)
REGIME_CODE = {"Conduction Mode (Stable)": "C", "Transition Mode": "T",
               "Keyhole Mode (melt-pool D/W > 0.5 screening onset)": "K"}
P_STEPS = (80, 150, 220, 300, 380, 460, 540)
V_STEPS = (300, 600, 900, 1200, 1600, 2000, 2400)

# Synthetic material (spec section 8), labelled synthetic: rho 8000, k_s 10, k_l 30, cp_s 400, cp_l 700, T_liq 1300,
# T_boil 2800, A 0.4, index 0.5, melt keys k 25, cp 650. Applied through prop_overrides on the Inconel 718 base.
SYNTHETIC = {
    "liquidus_C": 1300.0, "solidus_C": 1250.0, "boiling_C": 2800.0, "density_kg_m3": 8000.0,
    "density_liquid_kg_m3": 7500.0, "thermal_conductivity_W_mK": 10.0, "thermal_conductivity_liquid_W_mK": 30.0,
    "specific_heat_J_kgK": 400.0, "specific_heat_liquid_J_kgK": 700.0, "latent_heat_fusion_J_kg": 250000.0,
    "latent_heat_vap_J_kg": 6.0e6, "absorptivity_IR": 0.4, "absorptivity_index_IR": 0.5, "absorptivity_Green": 0.6,
    "surface_tension_N_m": 1.7, "d_gamma_dT_N_mK": -4.0e-4, "viscosity_Pa_s": 0.005, "thermal_expansion_1_K": 1.3e-5,
    "youngs_modulus_GPa": 200.0, "poissons_ratio": 0.3, "M_molar_kg_mol": 0.058,
}
SYNTHETIC_MELT = {**SYNTHETIC, "thermal_conductivity_melt_W_mK": 25.0, "specific_heat_melt_J_kgK": 650.0}

# Authority values (spec section 2.1 and Amendment 1 item 2), pinned with their locators.
AUTHORITY = {
    "in718": (0.32, (0.28, 0.38)),        # Deisenroth 2026: liquid IN718 nominal energy coupling 0.32 (Fig. 11)
    "ss316l": (0.30, (0.28, 0.31)),       # Trapp 2017 Sec. 3.1, Fig. 3a: 0.29 to 0.31 (regime I); Ye 2019 Table 1 0.28
    "ti6al4v": (0.32, (0.26, 0.33)),      # Simonds 2021 Sec. 3.2 PDF p.4, Fig. 3a: 33 percent first 2.4 ms; Ye 0.26
    "alsi10mg": (0.30, (0.28, 0.40)),     # Leis, Weber, Graf 2020 Sec. 3, Figs. 4 to 6: area II minimum 30 percent
    "Inconel 625": (0.34, (0.28, 0.40)),  # Deisenroth 2020 Sec. 3.4, Fig. 7, PDF p.10: about 0.34 at 50 W
}
INDEX = {"in718": 0.38, "ss316l": 0.42, "ti6al4v": 0.35, "alsi10mg": 0.18, "Inconel 625": 0.38}  # pre-P7 served values
# Melting point convention (spec section 3.2): IN718 Mills 2002 b Table 1 liquid row at 1336 C; 316L Mills 2002 a
# Table 1 liquid row at 1450 C; IN625 Weaver 2022 Table 2 (PDF p.33) at T_m 1563.15 K (the repo solidus).
MELT = {"in718": (29.6, 720.0), "ss316l": (28.5, 830.0), "Inconel 625": (28.78, 719.92)}

# Ti-6Al-4V ledger (Amendment 5 item 2 / Amendment 1 item 2.1): Gan 2021 SI Table 1 (PDF p.20) fits of Mills data.
TI64_K_SLOPE, TI64_K_INTERCEPT = 0.0136, 1.3097     # k_s(T) W/(m K), 293 K to 1933 K
TI64_CP_SLOPE, TI64_CP_INTERCEPT = 0.1734, 452.72   # cp_s(T) J/(kg K)
TI64_T_LIQ_K = 1933.15
# AlSi10Mg ledger (Amendment 7 item 2): k_s as built build direction (Yang 2018 Fig. 5; Akwaboa 2023 Conclusion (3),
# Fig. 2f; Fetni 2024 Fig. 4a), cp_s Yang 2018 Fig. 1 second heating, rho_s 2696 (Akwaboa Table 3).
ALSI_K_AB = [(298.15, 114.0), (373.15, 118.2), (473.15, 144.0), (573.15, 165.0), (673.15, 172.0), (800.15, 168.0)]
ALSI_K_HT = [(298.15, 205.5), (373.15, 206.3), (473.15, 201.6), (573.15, 193.6), (673.15, 198.0), (773.15, 192.4)]
ALSI_CP_AB = [(298.15, 893.0), (373.15, 934.0), (423.15, 952.0), (473.15, 965.0), (523.15, 974.0), (573.15, 978.0),
              (673.15, 1074.0), (723.15, 1121.0), (773.15, 1131.0)]
ALSI_T_LIQ_K = 868.15
ALSI_RHO_K = 2696.0
HT_LOW_FACTOR = 173.0 / 205.5   # EOS datasheet 173 W/(m K) via Selo 2020 p.2 over Yang 25 C 205.5

# Recorded at REV0 (b578da71, pin 0e1599b4): (P W, v mm/s, dH/hs, regime code, porosity class word, Fabbro
# onset weight) per cell, Rosenthal, 80 um, 80 C, 40 um layer, 100 um hatch; the AM-Bench CBM cases through the
# IN625_VALIDATION_PROPS override at 25 C, 100 um.
PRE_P7_FIXTURE = {
    'Ti-6Al-4V': [
        (80, 300, 18.26, 'T', 'Possible', 0.217333),
        (80, 600, 12.91, 'C', 'Negligible', 0.0),
        (80, 900, 10.54, 'C', 'Negligible', 0.0),
        (80, 1200, 9.13, 'C', 'Negligible', 0.0),
        (80, 1600, 7.91, 'C', 'Negligible', 0.0),
        (80, 2000, 7.07, 'C', 'Negligible', 0.0),
        (80, 2400, 6.46, 'C', 'Negligible', 0.0),
        (150, 300, 34.24, 'K', 'High', 1.0),
        (150, 600, 24.21, 'K', 'Possible', 0.614),
        (150, 900, 19.77, 'T', 'Possible', 0.318),
        (150, 1200, 17.12, 'T', 'Possible', 0.141333),
        (150, 1600, 14.83, 'C', 'Negligible', 0.0),
        (150, 2000, 13.26, 'C', 'Negligible', 0.0),
        (150, 2400, 12.11, 'C', 'Negligible', 0.0),
        (220, 300, 50.22, 'K', 'High', 1.0),
        (220, 600, 35.51, 'K', 'High', 1.0),
        (220, 900, 28.99, 'K', 'Possible', 0.932667),
        (220, 1200, 25.11, 'K', 'Possible', 0.674),
        (220, 1600, 21.75, 'K', 'Possible', 0.45),
        (220, 2000, 19.45, 'T', 'Possible', 0.296667),
        (220, 2400, 17.76, 'T', 'Possible', 0.184),
        (300, 300, 68.48, 'K', 'High', 1.0),
        (300, 600, 48.42, 'K', 'High', 1.0),
        (300, 900, 39.54, 'K', 'High', 1.0),
        (300, 1200, 34.24, 'K', 'High', 1.0),
        (300, 1600, 29.65, 'K', 'Possible', 0.976667),
        (300, 2000, 26.52, 'K', 'Possible', 0.768),
        (300, 2400, 24.21, 'K', 'Possible', 0.614),
        (380, 300, 86.74, 'K', 'High', 1.0),
        (380, 600, 61.34, 'K', 'High', 1.0),
        (380, 900, 50.08, 'K', 'High', 1.0),
        (380, 1200, 43.37, 'K', 'High', 1.0),
        (380, 1600, 37.56, 'K', 'High', 1.0),
        (380, 2000, 33.6, 'K', 'High', 1.0),
        (380, 2400, 30.67, 'K', 'High', 1.0),
        (460, 300, 105.01, 'K', 'High', 1.0),
        (460, 600, 74.25, 'K', 'High', 1.0),
        (460, 900, 60.62, 'K', 'High', 1.0),
        (460, 1200, 52.5, 'K', 'High', 1.0),
        (460, 1600, 45.47, 'K', 'High', 1.0),
        (460, 2000, 40.67, 'K', 'High', 1.0),
        (460, 2400, 37.12, 'K', 'High', 1.0),
        (540, 300, 123.27, 'K', 'High', 1.0),
        (540, 600, 87.16, 'K', 'High', 1.0),
        (540, 900, 71.17, 'K', 'High', 1.0),
        (540, 1200, 61.63, 'K', 'High', 1.0),
        (540, 1600, 53.38, 'K', 'High', 1.0),
        (540, 2000, 47.74, 'K', 'High', 1.0),
        (540, 2400, 43.58, 'K', 'High', 1.0),
    ],
    'AlSi10Mg': [
        (80, 300, 6.39, 'C', 'Negligible', 0.0),
        (80, 600, 4.52, 'C', 'Negligible', 0.0),
        (80, 900, 3.69, 'C', 'Negligible', 0.0),
        (80, 1200, 3.2, 'C', 'Negligible', 0.0),
        (80, 1600, 2.77, 'C', 'Negligible', 0.0),
        (80, 2000, 2.48, 'C', 'Negligible', 0.0),
        (80, 2400, 2.26, 'C', 'Negligible', 0.0),
        (150, 300, 11.99, 'C', 'Negligible', 0.0),
        (150, 600, 8.48, 'C', 'Negligible', 0.0),
        (150, 900, 6.92, 'C', 'Negligible', 0.0),
        (150, 1200, 5.99, 'C', 'Negligible', 0.0),
        (150, 1600, 5.19, 'C', 'Negligible', 0.0),
        (150, 2000, 4.64, 'C', 'Negligible', 0.0),
        (150, 2400, 4.24, 'C', 'Negligible', 0.0),
        (220, 300, 17.58, 'T', 'Possible', 0.172),
        (220, 600, 12.43, 'C', 'Negligible', 0.0),
        (220, 900, 10.15, 'C', 'Negligible', 0.0),
        (220, 1200, 8.79, 'C', 'Negligible', 0.0),
        (220, 1600, 7.61, 'C', 'Negligible', 0.0),
        (220, 2000, 6.81, 'C', 'Negligible', 0.0),
        (220, 2400, 6.22, 'C', 'Negligible', 0.0),
        (300, 300, 23.98, 'K', 'Possible', 0.598667),
        (300, 600, 16.95, 'T', 'Possible', 0.13),
        (300, 900, 13.84, 'C', 'Negligible', 0.0),
        (300, 1200, 11.99, 'C', 'Negligible', 0.0),
        (300, 1600, 10.38, 'C', 'Negligible', 0.0),
        (300, 2000, 9.29, 'C', 'Negligible', 0.0),
        (300, 2400, 8.48, 'C', 'Negligible', 0.0),
        (380, 300, 30.37, 'K', 'High', 1.0),
        (380, 600, 21.48, 'K', 'Possible', 0.432),
        (380, 900, 17.53, 'T', 'Possible', 0.168667),
        (380, 1200, 15.19, 'T', 'Possible', 0.012667),
        (380, 1600, 13.15, 'C', 'Negligible', 0.0),
        (380, 2000, 11.76, 'C', 'Negligible', 0.0),
        (380, 2400, 10.74, 'C', 'Negligible', 0.0),
        (460, 300, 36.77, 'K', 'High', 1.0),
        (460, 600, 26.0, 'K', 'Possible', 0.733333),
        (460, 900, 21.23, 'K', 'Possible', 0.415333),
        (460, 1200, 18.38, 'T', 'Possible', 0.225333),
        (460, 1600, 15.92, 'T', 'Possible', 0.061333),
        (460, 2000, 14.24, 'C', 'Negligible', 0.0),
        (460, 2400, 13.0, 'C', 'Negligible', 0.0),
        (540, 300, 43.16, 'K', 'High', 1.0),
        (540, 600, 30.52, 'K', 'High', 1.0),
        (540, 900, 24.92, 'K', 'Possible', 0.661333),
        (540, 1200, 21.58, 'K', 'Possible', 0.438667),
        (540, 1600, 18.69, 'T', 'Possible', 0.246),
        (540, 2000, 16.72, 'T', 'Possible', 0.114667),
        (540, 2400, 15.26, 'T', 'Possible', 0.017333),
    ],
    'Inconel 718': [
        (80, 300, 15.46, 'T', 'Possible', 0.030667),
        (80, 600, 10.93, 'C', 'Negligible', 0.0),
        (80, 900, 8.93, 'C', 'Negligible', 0.0),
        (80, 1200, 7.73, 'C', 'Negligible', 0.0),
        (80, 1600, 6.7, 'C', 'Negligible', 0.0),
        (80, 2000, 5.99, 'C', 'Negligible', 0.0),
        (80, 2400, 5.47, 'C', 'Negligible', 0.0),
        (150, 300, 28.99, 'K', 'Possible', 0.932667),
        (150, 600, 20.5, 'K', 'Possible', 0.366667),
        (150, 900, 16.74, 'T', 'Possible', 0.116),
        (150, 1200, 14.5, 'C', 'Negligible', 0.0),
        (150, 1600, 12.56, 'C', 'Negligible', 0.0),
        (150, 2000, 11.23, 'C', 'Negligible', 0.0),
        (150, 2400, 10.25, 'C', 'Negligible', 0.0),
        (220, 300, 42.53, 'K', 'High', 1.0),
        (220, 600, 30.07, 'K', 'High', 1.0),
        (220, 900, 24.55, 'K', 'Possible', 0.636667),
        (220, 1200, 21.26, 'K', 'Possible', 0.417333),
        (220, 1600, 18.41, 'T', 'Possible', 0.227333),
        (220, 2000, 16.47, 'T', 'Possible', 0.098),
        (220, 2400, 15.04, 'T', 'Possible', 0.002667),
        (300, 300, 57.99, 'K', 'High', 1.0),
        (300, 600, 41.0, 'K', 'High', 1.0),
        (300, 900, 33.48, 'K', 'High', 1.0),
        (300, 1200, 28.99, 'K', 'Possible', 0.932667),
        (300, 1600, 25.11, 'K', 'Possible', 0.674),
        (300, 2000, 22.46, 'K', 'Possible', 0.497333),
        (300, 2400, 20.5, 'K', 'Possible', 0.366667),
        (380, 300, 73.45, 'K', 'High', 1.0),
        (380, 600, 51.94, 'K', 'High', 1.0),
        (380, 900, 42.41, 'K', 'High', 1.0),
        (380, 1200, 36.73, 'K', 'High', 1.0),
        (380, 1600, 31.81, 'K', 'High', 1.0),
        (380, 2000, 28.45, 'K', 'Possible', 0.896667),
        (380, 2400, 25.97, 'K', 'Possible', 0.731333),
        (460, 300, 88.92, 'K', 'High', 1.0),
        (460, 600, 62.87, 'K', 'High', 1.0),
        (460, 900, 51.34, 'K', 'High', 1.0),
        (460, 1200, 44.46, 'K', 'High', 1.0),
        (460, 1600, 38.5, 'K', 'High', 1.0),
        (460, 2000, 34.44, 'K', 'High', 1.0),
        (460, 2400, 31.44, 'K', 'High', 1.0),
        (540, 300, 104.38, 'K', 'High', 1.0),
        (540, 600, 73.81, 'K', 'High', 1.0),
        (540, 900, 60.26, 'K', 'High', 1.0),
        (540, 1200, 52.19, 'K', 'High', 1.0),
        (540, 1600, 45.2, 'K', 'High', 1.0),
        (540, 2000, 40.43, 'K', 'High', 1.0),
        (540, 2400, 36.9, 'K', 'High', 1.0),
    ],
    '316L Stainless Steel': [
        (80, 300, 12.84, 'C', 'Negligible', 0.0),
        (80, 600, 9.08, 'C', 'Negligible', 0.0),
        (80, 900, 7.42, 'C', 'Negligible', 0.0),
        (80, 1200, 6.42, 'C', 'Negligible', 0.0),
        (80, 1600, 5.56, 'C', 'Negligible', 0.0),
        (80, 2000, 4.97, 'C', 'Negligible', 0.0),
        (80, 2400, 4.54, 'C', 'Negligible', 0.0),
        (150, 300, 24.08, 'K', 'Possible', 0.605333),
        (150, 600, 17.03, 'T', 'Possible', 0.135333),
        (150, 900, 13.9, 'C', 'Negligible', 0.0),
        (150, 1200, 12.04, 'C', 'Negligible', 0.0),
        (150, 1600, 10.43, 'C', 'Negligible', 0.0),
        (150, 2000, 9.33, 'C', 'Negligible', 0.0),
        (150, 2400, 8.51, 'C', 'Negligible', 0.0),
        (220, 300, 35.32, 'K', 'High', 1.0),
        (220, 600, 24.97, 'K', 'Possible', 0.664667),
        (220, 900, 20.39, 'K', 'Possible', 0.359333),
        (220, 1200, 17.66, 'T', 'Possible', 0.177333),
        (220, 1600, 15.29, 'T', 'Possible', 0.019333),
        (220, 2000, 13.68, 'C', 'Negligible', 0.0),
        (220, 2400, 12.49, 'C', 'Negligible', 0.0),
        (300, 300, 48.16, 'K', 'High', 1.0),
        (300, 600, 34.06, 'K', 'High', 1.0),
        (300, 900, 27.81, 'K', 'Possible', 0.854),
        (300, 1200, 24.08, 'K', 'Possible', 0.605333),
        (300, 1600, 20.86, 'K', 'Possible', 0.390667),
        (300, 2000, 18.65, 'T', 'Possible', 0.243333),
        (300, 2400, 17.03, 'T', 'Possible', 0.135333),
        (380, 300, 61.01, 'K', 'High', 1.0),
        (380, 600, 43.14, 'K', 'High', 1.0),
        (380, 900, 35.22, 'K', 'High', 1.0),
        (380, 1200, 30.5, 'K', 'High', 1.0),
        (380, 1600, 26.42, 'K', 'Possible', 0.761333),
        (380, 2000, 23.63, 'K', 'Possible', 0.575333),
        (380, 2400, 21.57, 'K', 'Possible', 0.438),
        (460, 300, 73.85, 'K', 'High', 1.0),
        (460, 600, 52.22, 'K', 'High', 1.0),
        (460, 900, 42.64, 'K', 'High', 1.0),
        (460, 1200, 36.93, 'K', 'High', 1.0),
        (460, 1600, 31.98, 'K', 'High', 1.0),
        (460, 2000, 28.6, 'K', 'Possible', 0.906667),
        (460, 2400, 26.11, 'K', 'Possible', 0.740667),
        (540, 300, 86.69, 'K', 'High', 1.0),
        (540, 600, 61.3, 'K', 'High', 1.0),
        (540, 900, 50.05, 'K', 'High', 1.0),
        (540, 1200, 43.35, 'K', 'High', 1.0),
        (540, 1600, 37.54, 'K', 'High', 1.0),
        (540, 2000, 33.58, 'K', 'High', 1.0),
        (540, 2400, 30.65, 'K', 'High', 1.0),
    ],
    'Inconel 625': [
        (80, 300, 16.74, 'K', 'Possible', 0.116),
        (80, 600, 11.83, 'C', 'Negligible', 0.0),
        (80, 900, 9.66, 'C', 'Negligible', 0.0),
        (80, 1200, 8.37, 'C', 'Negligible', 0.0),
        (80, 1600, 7.25, 'C', 'Negligible', 0.0),
        (80, 2000, 6.48, 'C', 'Negligible', 0.0),
        (80, 2400, 5.92, 'C', 'Negligible', 0.0),
        (150, 300, 31.38, 'K', 'High', 1.0),
        (150, 600, 22.19, 'K', 'Possible', 0.479333),
        (150, 900, 18.12, 'K', 'Possible', 0.208),
        (150, 1200, 15.69, 'K', 'Possible', 0.046),
        (150, 1600, 13.59, 'C', 'Negligible', 0.0),
        (150, 2000, 12.15, 'C', 'Negligible', 0.0),
        (150, 2400, 11.09, 'C', 'Negligible', 0.0),
        (220, 300, 46.03, 'K', 'High', 1.0),
        (220, 600, 32.55, 'K', 'High', 1.0),
        (220, 900, 26.57, 'K', 'Possible', 0.771333),
        (220, 1200, 23.01, 'K', 'Possible', 0.534),
        (220, 1600, 19.93, 'K', 'Possible', 0.328667),
        (220, 2000, 17.83, 'K', 'Possible', 0.188667),
        (220, 2400, 16.27, 'K', 'Possible', 0.084667),
        (300, 300, 62.76, 'K', 'High', 1.0),
        (300, 600, 44.38, 'K', 'High', 1.0),
        (300, 900, 36.24, 'K', 'High', 1.0),
        (300, 1200, 31.38, 'K', 'High', 1.0),
        (300, 1600, 27.18, 'K', 'Possible', 0.812),
        (300, 2000, 24.31, 'K', 'Possible', 0.620667),
        (300, 2400, 22.19, 'K', 'Possible', 0.479333),
        (380, 300, 79.5, 'K', 'High', 1.0),
        (380, 600, 56.21, 'K', 'High', 1.0),
        (380, 900, 45.9, 'K', 'High', 1.0),
        (380, 1200, 39.75, 'K', 'High', 1.0),
        (380, 1600, 34.42, 'K', 'High', 1.0),
        (380, 2000, 30.79, 'K', 'High', 1.0),
        (380, 2400, 28.11, 'K', 'Possible', 0.874),
        (460, 300, 96.24, 'K', 'High', 1.0),
        (460, 600, 68.05, 'K', 'High', 1.0),
        (460, 900, 55.56, 'K', 'High', 1.0),
        (460, 1200, 48.12, 'K', 'High', 1.0),
        (460, 1600, 41.67, 'K', 'High', 1.0),
        (460, 2000, 37.27, 'K', 'High', 1.0),
        (460, 2400, 34.02, 'K', 'High', 1.0),
        (540, 300, 112.97, 'K', 'High', 1.0),
        (540, 600, 79.88, 'K', 'High', 1.0),
        (540, 900, 65.22, 'K', 'High', 1.0),
        (540, 1200, 56.49, 'K', 'High', 1.0),
        (540, 1600, 48.92, 'K', 'High', 1.0),
        (540, 2000, 43.75, 'K', 'High', 1.0),
        (540, 2400, 39.94, 'K', 'High', 1.0),
    ],
}
PRE_P7_AMBENCH = [
    ('CBM-A', 150.0, 400.0, 100.0, 15.7, 'T'),
    ('CBM-B', 195.0, 800.0, 100.0, 14.43, 'C'),
    ('CBM-C', 195.0, 1200.0, 100.0, 11.78, 'C'),
]


def _solve(mat, P, v, d=80.0, preheat=80.0, layer=40.0, hatch=100.0, **kw):
    return calculate_meltpool_physics(mat, P, v, d, preheat, layer, hatch, kw.pop("laser_wavelength", "IR_1064nm"), **kw)


def _trapezoid_mean(nodes, t0, t1):
    def f(t):
        if t <= nodes[0][0]:
            return nodes[0][1]
        for (a, va), (b, vb) in zip(nodes, nodes[1:]):
            if t <= b:
                return va + (vb - va) * (t - a) / (b - a)
        return nodes[-1][1]
    pts = sorted({t0, t1, *[k for k, _ in nodes if t0 < k < t1]})
    return sum(0.5 * (f(a) + f(b)) * (b - a) for a, b in zip(pts, pts[1:])) / (t1 - t0)


class AbsorptivityAuthority(unittest.TestCase):
    def test_absorptivity_authority_table(self):  # 1
        for key, (value, band) in AUTHORITY.items():
            entry = fam.absorptivity_authority(key)
            self.assertEqual(entry["value"], value, key)
            self.assertEqual(entry["band"], list(band), key)
            self.assertTrue(band[0] <= value <= band[1], key)
            self.assertEqual(entry["wavelength_nm"], 1075.0 if key == "alsi10mg" else 1070.0, key)
            self.assertTrue(entry["locator"] and entry["source"], key)
            self.assertFalse(entry["unsourced"], key)
        for key in ("CoCrMo", "Hastelloy X", "Scalmalloy (Al-Mg-Sc-Zr)", "Pure Copper (Cu-OF)"):
            self.assertTrue(fam.absorptivity_authority(key)["unsourced"], key)
            self.assertEqual(ts.absorptivity_basis_text(key, "IR_1064nm")[0], "no measurement, unsourced estimate")
        for aid in fam.FOUR_ALLOY_IDS:
            self.assertEqual(fam._THERMAL[aid]["absorptivity_IR"], AUTHORITY[aid][0], aid)
            self.assertEqual(fam.marangoni_props(aid)["absorptivity"], AUTHORITY[aid][0], aid)
            self.assertEqual(fam.inherent_strain_props(aid)["absorptivity"], AUTHORITY[aid][0], aid)
            self.assertNotIn("absorptivity", fam._MARANGONI[aid])
            self.assertNotIn("absorptivity", fam._ISM[aid])
        self.assertEqual(ts.SECONDARY_THERMOPHYSICAL_DB["Inconel 625"]["absorptivity_IR"], 0.34)
        self.assertEqual(ts.SECONDARY_THERMOPHYSICAL_DB["Inconel 625"]["absorptivity_index_IR"], 0.38)

    def test_index_convention_constants(self):  # 2 (Amendment 1 item 1.4: AlSi10Mg 0.18 differs from its field 0.30)
        for aid, value in INDEX.items():
            row = fam.thermal_props(aid) or ts.SECONDARY_THERMOPHYSICAL_DB[aid]
            self.assertEqual(row["absorptivity_index_IR"], value, aid)
        for name in ("CoCrMo", "Hastelloy X", "Scalmalloy (Al-Mg-Sc-Zr)", "Pure Copper (Cu-OF)"):
            row = ts.SECONDARY_THERMOPHYSICAL_DB[name]
            self.assertEqual(row["absorptivity_index_IR"], row["absorptivity_IR"], name)
        self.assertIn("convention constant", fam.ABSORPTIVITY_INDEX_BASIS)
        self.assertNotEqual(fam._THERMAL["alsi10mg"]["absorptivity_index_IR"], fam._THERMAL["alsi10mg"]["absorptivity_IR"])
        self.assertIn("convention constant", _solve("AlSi10Mg", 200, 800)["processParameters"]["absorptivityIndexBasis"])

    def test_classification_neutral_grid(self):  # 3 and 19
        for mat, rows in PRE_P7_FIXTURE.items():
            for p, v, dh, code, porosity, blend in rows:
                r = _solve(mat, p, v)
                pp, g = r["processParameters"], r["meltPoolGeometry"]
                self.assertEqual(pp["normalizedEnthalpy"], dh, (mat, p, v))
                self.assertEqual(REGIME_CODE[g["regime"]], code, (mat, p, v))
                self.assertEqual(r["defectDiagnostics"]["keyholePorosityRisk"].split(" ")[0], porosity, (mat, p, v))
                props = fam.thermal_props(mat) or ts.SECONDARY_THERMOPHYSICAL_DB[mat]
                k_s = props["thermal_conductivity_W_mK"]
                alpha_s = k_s / (props["density_kg_m3"] * props["specific_heat_J_kgK"])
                fab = fabbro_keyhole_depth_m(float(p), v * 1e-3, 80e-6, k_s, alpha_s, props["boiling_C"], 80.0,
                                             pp["fabbroAbsorptivity"], pp["normalizedEnthalpy"])
                self.assertEqual(round(fab["blend"], 6), blend, (mat, p, v))
            # Grid cells: index and enthalpy regime label bit equal (Lack of Fusion relabelling excluded).
            cells = _solve(mat, 200, 800)["processWindowMap"]["grid"]
            by_pv = {(row[0], row[1]): row for row in rows}
            for cell in cells:
                p, v, dh, code = by_pv[(cell["power_W"], cell["speed_mm_s"])][:4]
                self.assertEqual(cell["normalizedEnthalpy"], dh, (mat, p, v))
                if cell["regime"] != "Lack of Fusion Zone":
                    self.assertEqual({"Optimal Conduction": "C", "Transition": "T", "Keyhole Mode": "K"}[cell["regime"]],
                                     code, (mat, p, v))
        # AM-Bench CBM cases through the Build Job snapshot path: IN625_VALIDATION_PROPS carries index 0.32.
        for case_id, p, v, d, dh, code in PRE_P7_AMBENCH:
            r = calculate_meltpool_physics("Inconel 718", p, v, d, 25.0, 40.0, 100.0, "IR_1064nm",
                                           prop_overrides=dict(IN625_VALIDATION_PROPS))
            self.assertEqual(r["processParameters"]["normalizedEnthalpy"], dh, case_id)
            self.assertEqual(REGIME_CODE[r["meltPoolGeometry"]["regime"]], code, case_id)
        # Resolution rule 2: a full property set without an index key follows its own absorptivity_IR, stated.
        full = {k: v for k, v in IN625_VALIDATION_PROPS.items() if k != "absorptivity_index_IR"}
        self.assertTrue(all(k in full for k in fam.INDEX_FULL_SET_KEYS))
        r2 = calculate_meltpool_physics("Inconel 718", 150, 400, 100, 25.0, 40.0, 100.0, "IR_1064nm", prop_overrides=full)
        self.assertEqual(r2["processParameters"]["normalizedEnthalpy"], PRE_P7_AMBENCH[0][4])
        self.assertIn("no index key supplied", r2["processParameters"]["absorptivityIndexBasis"])
        # Resolution rule 3: a partial override (the calibration layer, UQ) keeps the base alloy's index.
        base = _solve("Inconel 718", 200, 800)["processParameters"]
        part = _solve("Inconel 718", 200, 800, prop_overrides={"absorptivity_IR": 0.5})["processParameters"]
        self.assertEqual(part["normalizedEnthalpy"], base["normalizedEnthalpy"])
        self.assertEqual(part["indexAbsorptivity"], 0.38)
        self.assertEqual(part["fieldPower_W"], 100.0)

    def test_field_power_and_leg_use_authority(self):  # 4
        r = _solve("Inconel 718", 200, 800, prop_overrides=SYNTHETIC)
        pp = r["processParameters"]
        self.assertEqual(pp["fieldPower_W"], 80.0)
        self.assertEqual(pp["fabbroAbsorptivity"], 0.4)
        self.assertEqual(pp["indexAbsorptivity"], 0.5)
        rho, cp_s, k_s = 8000.0, 400.0, 10.0
        alpha_s = k_s / (rho * cp_s)
        denom = rho * cp_s * (1300.0 - 80.0) * math.sqrt(math.pi * alpha_s * 0.8 * (40e-6 ** 3))
        self.assertEqual(pp["normalizedEnthalpy"], round(0.5 * 200.0 / denom, 2))

    def test_absorptivity_basis_served(self):  # 5
        green = _solve("Inconel 718", 200, 800, laser_wavelength="Green_515nm")["processParameters"]
        self.assertEqual(green["absorptivityBasis"], "no measurement, unsourced estimate")
        self.assertEqual(green["indexAbsorptivity"], 0.58)
        self.assertEqual(_solve("CoCrMo", 200, 800)["processParameters"]["absorptivityBasis"],
                         "no measurement, unsourced estimate")
        in718 = _solve("Inconel 718", 200, 800)["processParameters"]
        self.assertIn("measured conduction-mode value, bare plate, 1070 nm", in718["absorptivityBasis"])
        self.assertIn("0.6 to 0.9", in718["absorptivityBasis"])
        self.assertIn("band 0.28 to 0.38", in718["absorptivityBasis"])
        self.assertIn("Deisenroth", in718["absorptivitySource"])


class PropertyConvention(unittest.TestCase):
    def test_field_uses_melting_point_properties(self):  # 6
        r = _solve("Inconel 718", 200, 800, prop_overrides=SYNTHETIC_MELT)
        pp = r["processParameters"]
        self.assertEqual(pp["effectiveConductivity_W_mK"], 25.0)
        self.assertEqual(pp["effectiveSpecificHeat_J_kgK"], 650.0)
        self.assertEqual(pp["propertyConvention"], "melting-point")
        k, alpha = 25.0, 25.0 / (8000.0 * 650.0)
        self.assertAlmostEqual(pp["effectiveDiffusivity_m2_s"], alpha, delta=1e-15)
        # Far field at a hand point: T0 + P_field / (2 pi k R) exp(-v (R + x) / 2 alpha), R >> r_reg (regularised 1/R).
        x, y, z, v = -600e-6, 0.0, 0.0, 0.8
        R = math.sqrt(x * x + y * y + z * z)
        r_reg = max(40e-6 / math.sqrt(2.0), 8e-6)
        expected = 80.0 + (80.0 / (2.0 * math.pi * k * math.sqrt(R * R + r_reg * r_reg))) * math.exp(-v * (R + x) / (2.0 * alpha))
        self.assertAlmostEqual(ts.rosenthal_temperature_C(x, y, z, 80.0, 80.0, k, v, alpha, r_reg), expected, delta=1e-9)
        blend = _solve("Inconel 718", 200, 800, prop_overrides=SYNTHETIC)["processParameters"]
        self.assertEqual(blend["effectiveConductivity_W_mK"], 20.0)
        self.assertEqual(blend["effectiveSpecificHeat_J_kgK"], 550.0)
        self.assertEqual(blend["propertyConvention"], "blend")
        self.assertIn("equal-weight solid and liquid blend, unsourced", blend["propertyConventionBasis"])
        in718 = _solve("Inconel 718", 200, 800)["processParameters"]
        self.assertIn("the source diffusivity at the melting point is 5.6e-06 m2/s", in718["propertyConventionBasis"])
        self.assertIn("the served alpha is", in718["propertyConventionBasis"])
        for mat, (k_m, cp_m) in MELT.items():
            pp = _solve(mat, 200, 800)["processParameters"]
            self.assertEqual((pp["effectiveConductivity_W_mK"], pp["effectiveSpecificHeat_J_kgK"]),
                             (round(k_m, 3), round(cp_m, 1)), mat)

    def test_index_and_leg_stay_solid(self):  # 7
        a = _solve("Inconel 718", 200, 800, prop_overrides=SYNTHETIC)
        b = _solve("Inconel 718", 200, 800, prop_overrides=SYNTHETIC_MELT)
        self.assertEqual(a["processParameters"]["normalizedEnthalpy"], b["processParameters"]["normalizedEnthalpy"])
        self.assertEqual(a["keyholeModel"]["fabbroDepth_um"], b["keyholeModel"]["fabbroDepth_um"])
        self.assertEqual(a["processParameters"]["solidConductivity_W_mK"], 10.0)
        self.assertTrue(a["processParameters"]["kingUsesSolidThermophysics"])

    def test_uq_scales(self):  # 8
        out = apply_uq_prop_scales(SYNTHETIC_MELT, {"_uq_k_scale": 1.1})
        self.assertAlmostEqual(out["thermal_conductivity_melt_W_mK"], 27.5, places=12)
        # Gate ruling: the conductivity scale never touches a specific heat (the spec 3.3.4 "two melt keys" was a slip).
        self.assertNotIn("specific_heat_melt_J_kgK", out)
        out = apply_uq_prop_scales(SYNTHETIC_MELT, {"_uq_absorptivity_scale": 1.2})
        self.assertAlmostEqual(out["absorptivity_IR"], 0.48, places=12)
        self.assertNotIn("absorptivity_index_IR", out)
        r = _solve("Inconel 718", 200, 800, prop_overrides={**SYNTHETIC_MELT, **out})
        self.assertEqual(r["processParameters"]["indexAbsorptivity"], 0.5)
        self.assertEqual(r["processParameters"]["effectiveAbsorptivity"], 0.48)


class IndexReadersAndRegistry(unittest.TestCase):
    def test_registry_reads_authority(self):  # 9
        for name, value in (("Inconel 718", 0.32), ("316L Stainless Steel", 0.30), ("Ti-6Al-4V", 0.32), ("AlSi10Mg", 0.30)):
            self.assertEqual(registry.material(name)["absorptivity"], value, name)
        self.assertEqual(IN625_ABSORPTIVITY_IR, 0.40)
        self.assertIn("differs from the screening authority 0.34", IN625_ABSORPTIVITY_BASIS)
        with self.assertRaisesRegex(ValueError, "thermophysical data missing"):
            registry.material("Inconel 625")   # no transient IN625 material; the screening row is in625_thermal_material

    def test_index_readers(self):  # 10
        props = pds.screening_props("316L Stainless Steel")
        self.assertEqual(props["absorptivity_IR"], 0.30)   # physical
        self.assertEqual(props["absorptivity_index_IR"], 0.42)
        rho, k_s, cp_s = 7990.0, 16.3, 500.0
        denom = rho * cp_s * (1400.0 - 20.0) * math.sqrt(math.pi * (k_s / (rho * cp_s)) * 0.8 * (40e-6 ** 3))
        self.assertAlmostEqual(pds.normalized_enthalpy("316L Stainless Steel", 200.0, 800.0, 80.0, 20.0),
                               0.42 * 200.0 / denom, places=9)
        if os.path.join(HERE, "tools") not in sys.path:
            sys.path.append(os.path.join(HERE, "tools"))   # append: tools/ also holds an lpbf_error_bands.py
        import lpbf_keyhole_benchmark as kb
        import lpbf_in625_regime_threshold as irt
        king = kb.king_conversion()
        self.assertEqual(tuple(round(king["kingThresholdInAppUnits"][k], 1) for k in ("low", "mid", "high")),
                         (19.3, 22.2, 25.2))
        self.assertEqual(king["app316lProperties"]["absorptivity_index_IR"], 0.42)
        self.assertEqual(king["app316lProperties"]["absorptivity_IR_physical_not_used"], 0.30)
        ti = kb.ti64_props()
        self.assertEqual((ti["absorptivity_IR"], ti["absorptivity_index_IR"]), (0.32, 0.35))
        # The IN625 threshold tool reads the index constant 0.38 (the 13.6 cut was fitted with it).
        in625 = pds.screening_props("Inconel 625")
        w = irt.WEAVER_CONVENTION
        d_w = w["k_W_mK"] / (w["rho_kg_m3"] * w["cp_J_kgK"])
        a_repo = in625["thermal_conductivity_W_mK"] / (in625["density_kg_m3"] * in625["specific_heat_J_kgK"])
        hs_w = w["rho_kg_m3"] * w["cp_J_kgK"] * (w["Tm_K"] - w["T0_K"])
        hs_r = in625["density_kg_m3"] * in625["specific_heat_J_kgK"] * max(50.0, in625["liquidus_C"] - irt.PREHEAT_C)
        self.assertAlmostEqual(irt.repo_per_weaver_factor(),
                               (0.38 / w["A"]) * (hs_w / hs_r) * math.sqrt(d_w / a_repo) * (0.25 / 0.5) ** 1.5, places=12)
        self.assertAlmostEqual(irt.repo_per_weaver_factor(), 0.7243, places=3)
        # The frozen pre-P1 kernel reproduces its pinned baseline (recorded at 393cdbd1 / pin 0d52d7f7).
        for args, kernel, ref in (
                (("316L Stainless Steel", 300.0, 800.0, 80.0, 20.0, 30.0, 100.0), "rosenthal", (192.5, 152.8)),
                (("Ti-6Al-4V", 150.0, 1200.0, 95.0, 20.0, 30.0, 100.0), "rosenthal", (82.0, 39.6)),
                (("Ti-6Al-4V", 150.0, 1200.0, 95.0, 20.0, 30.0, 100.0), "eagar-tsai", (109.4, 37.9))):
            mine = frozen_kernel.meltpool_wd(*args, kernel=kernel)
            self.assertEqual((mine["W_um"], mine["D_um"]), ref, (args, kernel))
        snap, _ = build_material_property_snapshot("in718", "Inconel 718", "Inconel 718")
        self.assertIn("absorptivity_index_IR", _THERMAL_REQUIRED)
        self.assertEqual(snap["thermal"]["absorptivity_index_IR"], 0.38)
        self.assertEqual(snap["thermal"]["absorptivity_IR"], 0.32)
        green = _solve("316L Stainless Steel", 200, 800, laser_wavelength="Green_515nm")["processParameters"]
        self.assertEqual(green["indexAbsorptivity"], green["effectiveAbsorptivity"])
        self.assertEqual(green["indexAbsorptivity"], 0.62)


class ProcessMapGrid(unittest.TestCase):
    def test_grid_from_field(self):  # 11
        r = _solve("Ti-6Al-4V", 220, 1600)
        g = r["meltPoolGeometry"]
        cell = next(c for c in r["processWindowMap"]["grid"] if c["power_W"] == 220 and c["speed_mm_s"] == 1600)
        self.assertEqual((cell["width_um"], cell["depth_um"]), (g["width_um"], g["depth_um"]))
        self.assertEqual(cell["extentStatus"], g["extentStatus"])
        d_iso = g["depth_um"] - g["keyholeVaporCavityDepth_um"]
        self.assertAlmostEqual(g["depth_um"], max(d_iso, r["keyholeModel"]["fabbroDepth_um"]), delta=0.11)
        self.assertEqual(r["processWindowMap"]["gridKernel"], "rosenthal-screening-v1")
        self.assertEqual(r["processWindowMap"]["keyholeIndexLackOfFusionCut"], 20.0)
        low = next(c for c in r["processWindowMap"]["grid"] if c["power_W"] == 80 and c["speed_mm_s"] == 2400)
        self.assertIsNone(low["width_um"])
        self.assertIsNone(low["depth_um"])
        self.assertNotEqual(low["extentStatus"], "computed")
        self.assertNotEqual(low["regime"], "Lack of Fusion Zone")
        self.assertFalse(low["keyholeIndexLackOfFusion"])
        self.assertEqual(len(r["processWindowMap"]["grid"]), 49)
        # B19: the IN625 flag uses the per-alloy cut 13.6.
        in625 = _solve("Inconel 625", 200, 800)["processWindowMap"]
        self.assertEqual(in625["keyholeIndexLackOfFusionCut"], 13.6)
        flagged = [c for c in in625["grid"] if c["keyholeIndexLackOfFusion"]]
        self.assertTrue(flagged)
        self.assertTrue(all(c["normalizedEnthalpy"] >= 13.6 and c["regime"] == "Lack of Fusion Zone" for c in flagged))
        self.assertTrue(any(13.6 <= c["normalizedEnthalpy"] < 20.0 for c in flagged))
        # include_process_map=False: no grid, every other served field identical.
        off = _solve("Ti-6Al-4V", 220, 1600, include_process_map=False)
        self.assertIsNone(off["processWindowMap"]["grid"])
        self.assertIn("not computed", off["processWindowMap"]["gridKernelNote"])
        a, b = copy.deepcopy(r), copy.deepcopy(off)
        for d in (a, b):
            d["processWindowMap"].pop("grid")
            d["processWindowMap"].pop("gridKernelNote")
            d.pop("computeTimeMs", None)
        self.assertEqual(a, b)
        # The internal re-runs pass include_process_map=False.
        for rel, needle in (("lpbf_build_job_solver.py", "include_process_map=False"),
                            ("lpbf_process_window.py", "include_process_map=False"),
                            ("lpbf_bayesian_optimizer.py", "include_process_map=False")):
            text = open(os.path.join(HERE, rel), encoding="utf-8").read()
            self.assertIn(needle, text, rel)
        self.assertEqual(open(os.path.join(HERE, "lpbf_build_job_solver.py"), encoding="utf-8").read().count(
            "include_process_map=False"), 2)  # the patch evaluator and the UQ runner; the served call keeps the grid

    def test_balling_high_removed(self):  # 12
        for mat in ("316L Stainless Steel", "Inconel 718", "Ti-6Al-4V", "AlSi10Mg", None):
            s = balling_screen(700.0, 100.0, 40.0, "computed", material_name=mat)
            self.assertEqual(s["band"], "moderate", mat)
            self.assertFalse(s["highBandApplicable"], mat)
            self.assertIsNone(s["highThreshold"], mat)
        self.assertAlmostEqual(BALLING_LW_MODERATE, math.pi * math.sqrt(1.5), places=12)
        self.assertEqual(balling_screen(380.0, 100.0, 40.0, "computed")["band"], "stable")
        r = _solve("316L Stainless Steel", 370, 600, 60, heat_source="goldak")
        self.assertNotEqual(r["defectDiagnostics"]["ballingScreen"]["band"], "high")
        self.assertNotIn("High Balling Risk", r["defectDiagnostics"]["ballingInstabilityRisk"])

    def test_p6_outputs_follow_properties(self):  # 13
        # Eagar-Tsai loss-free surface maximum: in the stationary limit the excess scales as 1/k (hand check).
        lo = eagar_tsai_surface_maximum(80.0, 80.0, 10.0, 10.0 / (8000.0 * 400.0), 40e-6, 1e-4)
        hi = eagar_tsai_surface_maximum(80.0, 80.0, 20.0, 20.0 / (8000.0 * 400.0), 40e-6, 1e-4)
        self.assertAlmostEqual((lo["T_C"] - 80.0) / (hi["T_C"] - 80.0), 2.0, delta=0.02)
        # The null versus sourced T_v decision uses the new peak: 316L (T_v 3086 K) at a synthetic high-k override.
        cold = {**SYNTHETIC, "thermal_conductivity_melt_W_mK": 400.0, "specific_heat_melt_J_kgK": 650.0}
        r = _solve("316L Stainless Steel", 60, 2000, prop_overrides=cold)
        self.assertIsNotNone(r["hydrodynamicsAndRecoil"]["peakTemperature_C"])
        self.assertLess(r["hydrodynamicsAndRecoil"]["peakTemperature_C"], 2813.0)
        hot = _solve("316L Stainless Steel", 300, 800)
        self.assertIsNone(hot["hydrodynamicsAndRecoil"]["peakTemperature_C"])
        self.assertTrue(hot["hydrodynamicsAndRecoil"]["peakExceedsVaporization"])

    def test_labels_unchanged(self):  # 14
        from lpbf_build_job_solver import solve_lpbf_build_job
        job = solve_lpbf_build_job({"alloyId": "ti6al4v", "laserPower_W": 200, "scanSpeed_mm_s": 900,
                                    "beamDiameter_um": 80, "preheatTemp_C": 80, "layerThickness_um": 40,
                                    "hatchSpacing_um": 100, "preset": "nozzle", "bypassCache": True})
        self.assertTrue(job["success"])
        self.assertEqual(job["solverRevision"], "lpbf-build-job-sola1-v26")
        self.assertFalse(job.get("experimentalValidation", False))
        text = json.dumps(job)
        self.assertNotIn('"productionReady": true', text)
        self.assertNotIn('"validationStatus": "validated"', text)
        self.assertTrue(any("sourcing correction" in a for a in job["assumptions"]))


class KernelLedger(unittest.TestCase):
    def test_ti64_kirchhoff_kernel_pins(self):  # 16
        self.assertAlmostEqual(TI64_K_SLOPE * 1877.0 + TI64_K_INTERCEPT, 26.8, delta=0.05)
        self.assertAlmostEqual(TI64_CP_SLOPE * 1877.0 + TI64_CP_INTERCEPT, 778.2, delta=0.05)
        k0 = fam.kernel_properties("ti6al4v", 293.15)
        self.assertAlmostEqual(k0["kernel_conductivity_W_mK"] / 16.449, 1.0, delta=1e-3)
        self.assertAlmostEqual(k0["kernel_specific_heat_J_kgK"] / 645.74, 1.0, delta=1e-3)
        self.assertAlmostEqual(k0["alpha_m2_s"] / 5.750e-6, 1.0, delta=1e-3)
        self.assertEqual(k0["kernel_density_kg_m3"], 4430.0)
        k80 = fam.kernel_properties("Ti-6Al-4V", 353.15)
        self.assertAlmostEqual(k80["kernel_conductivity_W_mK"] / 16.857, 1.0, delta=1e-3)
        self.assertAlmostEqual(k80["kernel_specific_heat_J_kgK"] / 650.94, 1.0, delta=1e-3)
        self.assertAlmostEqual(k80["alpha_m2_s"] / 5.846e-6, 1.0, delta=1e-3)
        mid = 0.5 * (293.15 + TI64_T_LIQ_K)
        self.assertAlmostEqual(k0["kernel_conductivity_W_mK"], TI64_K_SLOPE * mid + TI64_K_INTERCEPT, places=9)
        self.assertAlmostEqual(k0["kernel_specific_heat_J_kgK"], TI64_CP_SLOPE * mid + TI64_CP_INTERCEPT, places=9)
        # The liquid keys do not enter the kernel.
        base = _solve("Ti-6Al-4V", 200, 800)["processParameters"]
        moved = _solve("Ti-6Al-4V", 200, 800, prop_overrides={"thermal_conductivity_liquid_W_mK": 99.0,
                                                               "specific_heat_liquid_J_kgK": 1.0,
                                                               "density_liquid_kg_m3": 1.0})["processParameters"]
        self.assertEqual(base["effectiveConductivity_W_mK"], moved["effectiveConductivity_W_mK"])
        self.assertEqual(base["effectiveSpecificHeat_J_kgK"], moved["effectiveSpecificHeat_J_kgK"])
        self.assertEqual(base["effectiveConductivity_W_mK"], 16.857)
        self.assertEqual(fam._THERMAL["ti6al4v"]["thermal_conductivity_liquid_W_mK"], 29.8)   # Mohr 2020 p.7
        self.assertEqual(fam._THERMAL["ti6al4v"]["specific_heat_liquid_J_kgK"], 930.0)      # Mohr 2020 Sec. 5 Fig. 4a
        self.assertEqual(fam._THERMAL["ti6al4v"]["density_liquid_kg_m3"], 4087.0)           # Mohr 2020 Eq. 21

    def test_alsi10mg_kirchhoff_kernel_pins(self):  # 17
        k0 = fam.kernel_properties("alsi10mg", 293.15)
        for got, want in ((k0["kernel_conductivity_W_mK"], 152.524), (k0["kernel_specific_heat_J_kgK"], 1020.08),
                          (k0["alpha_m2_s"], 5.546e-5)):
            self.assertAlmostEqual(got / want, 1.0, delta=1e-3)
        self.assertEqual(k0["kernel_density_kg_m3"], ALSI_RHO_K)
        self.assertEqual(k0["state"], "AB")
        k80 = fam.kernel_properties("AlSi10Mg", 353.15)
        self.assertAlmostEqual(k80["kernel_conductivity_W_mK"] / 156.848, 1.0, delta=1e-3)
        self.assertAlmostEqual(k80["kernel_specific_heat_J_kgK"] / 1033.28, 1.0, delta=1e-3)
        self.assertAlmostEqual(fam.kernel_properties("alsi10mg", 473.15)["kernel_conductivity_W_mK"] / 165.352, 1.0,
                               delta=1e-3)
        self.assertAlmostEqual(fam.kernel_properties("alsi10mg", 293.15, state="HT_low")["kernel_conductivity_W_mK"]
                               / 166.910, 1.0, delta=1e-3)
        self.assertAlmostEqual(fam.kernel_properties("alsi10mg", 293.15, state="HT")["kernel_conductivity_W_mK"]
                               / 198.266, 1.0, delta=1e-3)
        self.assertAlmostEqual(fam.kernel_properties("alsi10mg", 293.15, state="AB_unrelaxed")["kernel_conductivity_W_mK"]
                               / 117.890, 1.0, delta=1e-3)
        # The integral equals the trapezoid mean of the pinned nodes; first node held below, last value held above.
        self.assertAlmostEqual(k0["kernel_conductivity_W_mK"], _trapezoid_mean(ALSI_K_AB, 293.15, ALSI_T_LIQ_K), places=9)
        self.assertAlmostEqual(k0["kernel_specific_heat_J_kgK"], _trapezoid_mean(ALSI_CP_AB, 293.15, ALSI_T_LIQ_K), places=9)
        self.assertAlmostEqual(fam.kernel_properties("alsi10mg", 293.15, state="HT_low")["kernel_conductivity_W_mK"],
                               HT_LOW_FACTOR * _trapezoid_mean(ALSI_K_HT, 293.15, ALSI_T_LIQ_K), places=9)
        self.assertEqual(fam._piecewise_hold(ALSI_K_AB, 100.0), 114.0)
        self.assertEqual(fam._piecewise_hold(ALSI_K_AB, 850.0), 168.0)
        self.assertEqual(fam._piecewise_hold(ALSI_CP_AB, 850.0), 1131.0)
        num = fam.PROPERTY_LEDGER["alsi10mg"]["numeric"]
        self.assertEqual(num["hold_above_K"], {"k_AB": 800.15, "k_HT": 773.15, "cp_AB": 773.15, "cp_HT": 773.15})
        self.assertEqual([tuple(n) for n in num["k_s_nodes_W_mK"]["AB"]], ALSI_K_AB)
        self.assertEqual([tuple(n) for n in num["cp_s_nodes_J_kgK"]["AB"]], ALSI_CP_AB)

    def test_kernel_precedence(self):  # 18
        # (i) explicit kernel keys win.
        over = {"kernel_conductivity_W_mK": 50.0, "kernel_specific_heat_J_kgK": 800.0, "kernel_density_kg_m3": 4000.0}
        pp = _solve("Ti-6Al-4V", 200, 800, prop_overrides=over)["processParameters"]
        self.assertEqual((pp["effectiveConductivity_W_mK"], pp["effectiveSpecificHeat_J_kgK"], pp["kernelDensity_kg_m3"]),
                         (50.0, 800.0, 4000.0))
        self.assertEqual(pp["propertyConvention"], "kernel-override")
        # (ii) a full frozen snapshot without kernel keys: the ledger mean for Ti64 and AlSi10Mg (the Build Job case).
        for aid, name, slicer in (("ti6al4v", "Ti-6Al-4V", "Ti-6Al-4V ELI"), ("alsi10mg", "AlSi10Mg", "AlSi10Mg")):
            snap, _ = build_material_property_snapshot(aid, name, slicer)
            self.assertTrue(all(k in snap["thermal"] for k in ("thermal_conductivity_W_mK", "thermal_conductivity_liquid_W_mK",
                                                               "specific_heat_J_kgK", "specific_heat_liquid_J_kgK")))
            self.assertFalse(any(k in snap["thermal"] for k in ("kernel_conductivity_W_mK", "kernel_specific_heat_J_kgK")))
            pp = _solve(name, 200, 800, prop_overrides=snap["thermal"])["processParameters"]
            ledger = fam.kernel_properties(aid, 353.15)
            self.assertEqual(pp["effectiveConductivity_W_mK"], round(ledger["kernel_conductivity_W_mK"], 3), aid)
            self.assertEqual(pp["effectiveSpecificHeat_J_kgK"], round(ledger["kernel_specific_heat_J_kgK"], 1), aid)
            self.assertEqual(pp["kernelDensity_kg_m3"], ledger["kernel_density_kg_m3"], aid)
            self.assertEqual(pp["propertyConvention"], "kernel-ledger-kirchhoff", aid)
            # The blend of the new liquid values (Ti64 18.25 / 728) never reaches the Build Job.
            self.assertNotEqual(pp["effectiveConductivity_W_mK"],
                                0.5 * (snap["thermal"]["thermal_conductivity_W_mK"] + snap["thermal"]["thermal_conductivity_liquid_W_mK"]))
        # (iii) the base rule for the other alloys: melt point keys, else blend.
        snap, _ = build_material_property_snapshot("in718", "Inconel 718", "Inconel 718")
        pp = _solve("Inconel 718", 200, 800, prop_overrides=snap["thermal"])["processParameters"]
        self.assertEqual((pp["effectiveConductivity_W_mK"], pp["propertyConvention"]), (29.6, "melting-point"))
        self.assertEqual(_solve("CoCrMo", 200, 800)["processParameters"]["propertyConvention"], "blend")
        # G1 path parity: the Build Job (both call sites) equals the direct call at the same preheat.
        from lpbf_build_job_solver import solve_lpbf_build_job
        for aid, name in (("ti6al4v", "Ti-6Al-4V"), ("alsi10mg", "AlSi10Mg")):
            job = solve_lpbf_build_job({"alloyId": aid, "laserPower_W": 250, "scanSpeed_mm_s": 1000, "beamDiameter_um": 80,
                                        "preheatTemp_C": 120, "layerThickness_um": 40, "hatchSpacing_um": 100,
                                        "preset": "nozzle", "bypassCache": True, "enableUq": True, "uqSamples": 8})
            self.assertTrue(job["success"], job.get("error"))
            direct = _solve(name, 250, 1000, 80, 120)["processParameters"]
            served = job["thermal"]["processParameters"]
            self.assertEqual(served["effectiveConductivity_W_mK"], direct["effectiveConductivity_W_mK"], aid)
            self.assertEqual(served["effectiveSpecificHeat_J_kgK"], direct["effectiveSpecificHeat_J_kgK"], aid)
            self.assertEqual(served["effectiveConductivity_W_mK"], round(fam.kernel_properties(aid, 393.15)["kernel_conductivity_W_mK"], 3))
            self.assertEqual(job["thermal"]["meltPoolGeometry"]["depth_um"], _solve(name, 250, 1000, 80, 120)["meltPoolGeometry"]["depth_um"])
            self.assertTrue(job["uq"]["nSamples"] >= 8)
        # The UQ call site materialises the kernel at the job preheat and scales it.
        snap, _ = build_material_property_snapshot("ti6al4v", "Ti-6Al-4V", "Ti-6Al-4V ELI")
        kernel = fam.kernel_properties("ti6al4v", 393.15)
        concrete = apply_uq_prop_scales(snap["thermal"], {"_uq_k_scale": 1.1}, kernel=kernel)
        pp = _solve("Ti-6Al-4V", 250, 1000, 80, 120, prop_overrides={**snap["thermal"], **concrete})["processParameters"]
        self.assertEqual(pp["effectiveConductivity_W_mK"], round(1.1 * kernel["kernel_conductivity_W_mK"], 3))
        # kernel_density_kg_m3 changes alpha (and denom_thermal), not the index.
        a = _solve("AlSi10Mg", 200, 800)["processParameters"]
        b = _solve("AlSi10Mg", 200, 800, prop_overrides={"kernel_density_kg_m3": 2500.0})["processParameters"]
        self.assertEqual(a["normalizedEnthalpy"], b["normalizedEnthalpy"])
        self.assertEqual(a["effectiveConductivity_W_mK"], b["effectiveConductivity_W_mK"])
        self.assertAlmostEqual(b["effectiveDiffusivity_m2_s"] / a["effectiveDiffusivity_m2_s"], 2696.0 / 2500.0, places=9)
        self.assertEqual(a["kernelDensity_kg_m3"], 2696.0)
        self.assertIn("the conduction kernel uses 2696", a["densityBasis"])

    def test_fabbro_leg_moves_with_absorptivity_only(self):  # 19 (the leg part; the grid part is test 3)
        for name, old_a, new_a, p, v in (("Ti-6Al-4V", 0.35, 0.32, 350, 1200), ("AlSi10Mg", 0.18, 0.30, 540, 300)):
            props = fam.thermal_props(name)
            k_s = props["thermal_conductivity_W_mK"]
            alpha_s = k_s / (props["density_kg_m3"] * props["specific_heat_J_kgK"])
            r = _solve(name, p, v)
            dh = r["processParameters"]["normalizedEnthalpy"]
            self.assertGreater(dh, 15.0, name)
            old = fabbro_keyhole_depth_m(float(p), v * 1e-3, 80e-6, k_s, alpha_s, props["boiling_C"], 80.0, old_a, dh)
            new = fabbro_keyhole_depth_m(float(p), v * 1e-3, 80e-6, k_s, alpha_s, props["boiling_C"], 80.0, new_a, dh)
            self.assertAlmostEqual(new["depth_m"] / old["depth_m"], new_a / old_a, places=9, msg=name)
            self.assertAlmostEqual(r["keyholeModel"]["fabbroDepth_um"], new["depth_m"] * 1e6, delta=0.06)
            over = _solve(name, p, v, prop_overrides={"kernel_conductivity_W_mK": 99.0, "kernel_specific_heat_J_kgK": 999.0})
            self.assertEqual(over["keyholeModel"]["fabbroDepth_um"], r["keyholeModel"]["fabbroDepth_um"], name)

    def test_served_direction_pins(self):  # 20 (Amendment 1 item 4.2, pinned literals; a regression of the served path)
        import statistics
        pts = [(150, 1000), (200, 800), (280, 700), (200, 1500), (350, 1200)]

        def run(mat, ov):
            out = []
            for p, v in pts:
                g = _solve(mat, p, v, prop_overrides=ov, include_process_map=False)["meltPoolGeometry"]
                out.append((g["width_um"], g["depth_um"], g["length_um"]))
            return out

        def med(a, b):
            return tuple(round(100.0 * (statistics.median(y[i] / x[i] for x, y in zip(a, b)) - 1.0), 1) for i in range(3))

        # Pre-bump literal baselines: Ti64 A 0.35 with the blend 14.85 / 678 (k_s = k_l, cp_s = cp_l), rho 4430;
        # AlSi10Mg A 0.18 with the blend 107.5 / 1045 and density 2680; both through explicit kernel keys.
        ti_base = {"absorptivity_IR": 0.35, "absorptivity_index_IR": 0.35, "kernel_conductivity_W_mK": 14.85,
                   "kernel_specific_heat_J_kgK": 678.0, "kernel_density_kg_m3": 4430.0}
        ti_kernel = {"absorptivity_IR": 0.35, "absorptivity_index_IR": 0.35}
        al_base = {"absorptivity_IR": 0.18, "absorptivity_index_IR": 0.18, "kernel_conductivity_W_mK": 107.5,
                   "kernel_specific_heat_J_kgK": 1045.0, "kernel_density_kg_m3": 2680.0}
        al_a = {**al_base, "absorptivity_IR": 0.30}
        ti_b = run("Ti-6Al-4V", ti_base)
        ti_kernel_alone = med(ti_b, run("Ti-6Al-4V", ti_kernel))
        ti_both = med(ti_b, run("Ti-6Al-4V", None))
        al_b = run("AlSi10Mg", al_base)
        al_a_alone = med(al_b, run("AlSi10Mg", al_a))
        al_both = med(al_b, run("AlSi10Mg", None))
        for got, want in ((ti_both, (-3.1, -8.6, -18.7)), (al_both, (26.0, 26.7, 20.3))):
            for g, w in zip(got, want):
                self.assertAlmostEqual(g, w, delta=1.5, msg=(got, want))
        self.assertAlmostEqual(al_a_alone[1], 43.6, delta=1.5)
        self.assertAlmostEqual(ti_kernel_alone[1], 0.0, delta=1.5)
        # Signs, the hard assertion: Ti64 conduction depth does not rise; AlSi10Mg depth rises.
        self.assertLessEqual(ti_both[1], 0.0)
        self.assertLess(ti_both[0], 0.0)
        self.assertGreater(al_both[1], 0.0)
        self.assertGreater(al_both[0], 0.0)

    def test_ledger_values_and_provenance(self):  # 21
        t = fam._THERMAL
        changed = {"ti6al4v": {"absorptivity_IR": 0.32, "absorptivity_index_IR": 0.35, "thermal_conductivity_liquid_W_mK": 29.8,
                               "specific_heat_liquid_J_kgK": 930.0, "density_liquid_kg_m3": 4087.0,
                               "latent_heat_fusion_J_kg": 290000.0},
                   "alsi10mg": {"absorptivity_IR": 0.30, "absorptivity_index_IR": 0.18, "kernel_density_kg_m3": 2696.0,
                                "thermal_conductivity_liquid_W_mK": 64.0, "density_liquid_kg_m3": 2393.8,
                                "d_gamma_dT_N_mK": -0.000103}}
        for aid, keys in changed.items():
            for key, value in keys.items():
                self.assertEqual(t[aid][key], value, (aid, key))
                prov = fam.PROPERTY_PROVENANCE[aid][key]
                self.assertEqual(prov["value"], value, (aid, key))
                self.assertTrue(prov["source"] and prov["locator"], (aid, key))
        for aid in ("in718", "ss316l", "Inconel 625"):
            for key in fam.MELT_KEYS + ("absorptivity_IR", "absorptivity_index_IR"):
                self.assertTrue(fam.PROPERTY_PROVENANCE[aid][key]["locator"], (aid, key))
        # kernelLedgerSha256 moves on a ledger number and not on a note string.
        sha = fam.kernel_ledger_sha256("alsi10mg")
        saved = copy.deepcopy(fam.PROPERTY_LEDGER["alsi10mg"])
        try:
            fam.PROPERTY_LEDGER["alsi10mg"]["text"]["k_s"] = "edited note"
            self.assertEqual(fam.kernel_ledger_sha256("alsi10mg"), sha)
            fam.PROPERTY_LEDGER["alsi10mg"]["numeric"]["k_s_nodes_W_mK"]["AB"][0][1] = 115.0
            self.assertNotEqual(fam.kernel_ledger_sha256("alsi10mg"), sha)
        finally:
            fam.PROPERTY_LEDGER["alsi10mg"] = saved
        self.assertEqual(fam.kernel_ledger_sha256("alsi10mg"), sha)
        self.assertEqual(fam.canonical_material_source("alsi10mg")[0]["kernelLedgerSha256"], sha)
        self.assertIsNone(fam.canonical_material_source("in718")[0]["kernelLedgerSha256"])
        arms = fam.PROPERTY_LEDGER["ti6al4v"]["numeric"]["arms"]
        self.assertEqual((arms["melt_front_means"]["K_W_mK"], arms["melt_front_means"]["cp_J_kgK"]), (28.3, 854.0))
        self.assertEqual(arms["enthalpy_consistent_cp_J_kgK"], 822.6)
        al = fam.PROPERTY_LEDGER["alsi10mg"]["numeric"]["arms"]
        self.assertEqual((al["AB_unrelaxed_K_W_mK"], al["HT_low_K_W_mK"], al["melt_front_means"]["K_W_mK"]), (117.890, 166.910, 116.0))
        disputed = fam.PROPERTY_LEDGER["ti6al4v"]["numeric"]["disputed"]
        self.assertEqual((disputed["cp_l_J_kgK"], disputed["k_l_W_mK"], disputed["rho_l_kg_m3"]),
                         ([831.0, 1126.0], [28.7, 33.4], [3920.0, 4123.0]))
        self.assertEqual(fam.PROPERTY_LEDGER["alsi10mg"]["numeric"]["disputed"]["absorptivity"], [0.14, 0.40])
        self.assertNotIn("ti6al4v", fam.MELT_POINT_PROPERTIES)
        self.assertNotIn("alsi10mg", fam.MELT_POINT_PROPERTIES)

    def test_basis_strings_p7b_amendment(self):  # 22
        ti = _solve("Ti-6Al-4V", 200, 800)["processParameters"]
        self.assertTrue(ti["propertyConventionBasis"].startswith(
            "conduction k and cp are the Kirchhoff integral mean of the sourced solid k(T) and cp(T) over the isotherm "
            "range from the preheat to the liquidus (Carslaw and Jaeger 1959 sec 1.7); exact only for constant "
            "diffusivity (Ti-6Al-4V alpha varies about 3.3 times over the range, AlSi10Mg as built about 1.3 times); "
            "the liquid k, cp and density do not enter; K 16.857 W/mK, cp 650.94 J/kgK, alpha 5.846e-06 m2/s"))
        self.assertEqual(ti["solidConductivityBasis"], "room temperature value used by the regime index, the keyhole leg "
                                                        "and the transient table; the conduction field uses the kernel mean")
        al = _solve("AlSi10Mg", 200, 800)["processParameters"]
        self.assertIn("K 156.848 W/mK, cp 1033.28 J/kgK, alpha 5.63e-05 m2/s; state as built, build direction, held above "
                      "800.15 K for k and 773.15 K for cp", al["propertyConventionBasis"])
        self.assertTrue(al["absorptivityBasis"].startswith(
            "measured conduction value on an as-built rough AM surface (Sa 22.3 um) in N2 at 1075 nm, Leis 2020 area II "
            "minimum; band 0.28 to 0.40; not a polished or ground plate; not a powder layer value"))
        self.assertIn("0.6 to 0.9", al["absorptivityBasis"])
        self.assertIn("the index uses the convention constant 0.18 while the conduction field absorbs the measured 0.30",
                      al["absorptivityIndexBasis"])
        self.assertIn("may understate the onset", al["absorptivityIndexBasis"])
        for mat in ("Ti-6Al-4V", "AlSi10Mg", "Inconel 718"):
            pp = _solve(mat, 200, 800)["processParameters"]
            text = " ".join(str(pp[k]) for k in ("absorptivityBasis", "absorptivityIndexBasis", "propertyConventionBasis",
                                                 "solidConductivityBasis", "densityBasis", "effectiveAbsorptivityBasis"))
            self.assertFalse(re.search(r"(?<!un)validated", text), mat)
            self.assertNotIn("improved", text, mat)
            self.assertNotIn("closer to measurement", text, mat)
            self.assertNotIn("improved", json.dumps(_solve(mat, 200, 800)), mat)

    def test_alsi10mg_open_items_stay_open(self):  # 23
        t = fam._THERMAL["alsi10mg"]
        self.assertEqual((t["solidus_C"] + 273.15, t["liquidus_C"] + 273.15), (830.15, 868.15))
        self.assertEqual(t["latent_heat_fusion_J_kg"], 397000.0)
        self.assertEqual(t["specific_heat_liquid_J_kgK"], 1180.0)
        self.assertEqual((t["boiling_C"], t["latent_heat_vap_J_kg"], t["M_molar_kg_mol"]), (2470.0, 10500000.0, 0.0270))
        self.assertEqual(t["d_gamma_dT_N_mK"], -0.000103)
        self.assertEqual(fam._MARANGONI["alsi10mg"]["d_gamma_dT_pure_N_mK"], -0.000103)
        self.assertIsNone(ts.sourced_vapor_temperature("AlSi10Mg"))
        for p in (80, 300, 540):
            for v in (300, 1200, 2400):
                h = _solve("AlSi10Mg", p, v)["hydrodynamicsAndRecoil"]
                self.assertIsNone(h["peakTemperature_C"], (p, v))
                self.assertIsNone(h["surfaceTemperature_C"], (p, v))
                self.assertIsNone(h["marangoniNumber"], (p, v))
                self.assertIsNone(h["knudsenRecoilPressure_kPa"], (p, v))
        # The transient marangoniNumber reads the registry dGamma_dT: x0.294 against the former -3.5e-4.
        m = registry.material("AlSi10Mg")
        self.assertEqual(m["dGamma_dT"], -0.000103)
        self.assertAlmostEqual(abs(m["dGamma_dT"]) / 0.00035, 0.294, delta=1e-3)

    def test_registry_reads_new_liquid_and_absorptivity(self):  # 24
        ti = registry.material("Ti-6Al-4V")
        al = registry.material("AlSi10Mg")
        self.assertEqual((ti["absorptivity"], al["absorptivity"]), (0.32, 0.30))
        self.assertEqual(ti["table"][1][1:4], [4087.0, 29.8, 930.0])   # liquidus row: rho_l, k_l, cp_l
        self.assertEqual(al["table"][2][1:4], [2393.8, 64.0, 1180.0])
        # Pre-bump identity digests (recorded at REV0): the material revision moved for both alloys.
        self.assertFalse(ti["materialRevisionSha256"].startswith("a2d15d6c44ec"))
        self.assertFalse(al["materialRevisionSha256"].startswith("1d8fcbd4"))
        self.assertEqual(registry.material("Inconel 718")["absorptivity"], 0.32)
        self.assertEqual(registry.material("316L Stainless Steel")["absorptivity"], 0.30)
        self.assertEqual(IN625_ABSORPTIVITY_IR, 0.40)
        # reidentify: a request absorptivity that differs from the registry value re-hashes the snapshot.
        changed = dict(ti)
        changed["absorptivity"] = 0.35
        again = registry.reidentify(changed)
        self.assertNotEqual(again["materialRevisionSha256"], ti["materialRevisionSha256"])
        self.assertEqual(registry.reidentify(dict(ti))["materialRevisionSha256"], ti["materialRevisionSha256"])

    def test_no_measurement_claims(self):  # 25
        needle = "alsi10mg_kirchhoff_a7"
        for sub in ("python", "src"):
            for dirpath, _dirs, files in os.walk(os.path.join(ROOT, sub)):
                if "node_modules" in dirpath or "golden" in dirpath:
                    continue
                for fn in files:
                    if fn == os.path.basename(__file__) or not fn.endswith((".py", ".ts", ".tsx", ".json")):
                        continue
                    with open(os.path.join(dirpath, fn), encoding="utf-8", errors="ignore") as fh:
                        self.assertNotIn(needle, fh.read(), os.path.join(dirpath, fn))
        from lpbf_material_capabilities import capability_for
        for aid in ("ti6al4v", "alsi10mg"):
            cap = capability_for(aid)
            self.assertEqual(cap["kernelLedger"]["evidenceKind"], "Literature estimate")
            self.assertEqual(cap["kernelLedger"]["evidenceStatus"], "sourcing-correction-not-validation")
            self.assertFalse(cap["fullTransient"].get("experimentalValidation", False))
        r = _solve("Ti-6Al-4V", 200, 800)
        self.assertFalse(r["defectDiagnostics"]["ballingScreen"]["experimentalValidation"])
        self.assertFalse(r["defectDiagnostics"]["keyholePorosityResolved"])

    def test_depth_bias_note_alloy_neutral(self):  # 26
        note = depth_bias.P7B_CONDUCTION_NOTE
        self.assertEqual(note, " After 2026-10-14 (P7b) the conduction absorptivity authority and the conduction property "
                               "convention change conduction width and depth for every alloy that has a sourced value; the "
                               "direction is stated per alloy in the bump record.")
        self.assertNotIn("lower", note)
        self.assertNotIn("shallower", note)
        ts_src = open(os.path.join(ROOT, "src", "utils", "depthBiasWarning.ts"), encoding="utf-8").read()
        m = re.search(r"DEPTH_BIAS_P7B_CONDUCTION_NOTE =\n((?:\s*\".*\"(?: \+|;)?\n)+)", ts_src)
        self.assertIsNotNone(m)
        ts_note = "".join(re.findall(r"\"(.*?)\"", m.group(1)))
        self.assertEqual(ts_note, note)
        warn = depth_bias.depth_bias_warning("Conduction Mode (Stable)", "Inconel 718", "rosenthal", 10.0)
        if warn.get("direction"):
            self.assertTrue(warn["text"].endswith(note))

    def test_uq_kernel_scaling(self):  # 28
        snap, _ = build_material_property_snapshot("alsi10mg", "AlSi10Mg", "AlSi10Mg")
        kernel = fam.kernel_properties("alsi10mg", 353.15)
        out = apply_uq_prop_scales(snap["thermal"], {"_uq_k_scale": 1.1, "_uq_absorptivity_scale": 0.9, "_uq_rho_scale": 1.05},
                                   kernel=kernel)
        self.assertAlmostEqual(out["kernel_conductivity_W_mK"], 1.1 * kernel["kernel_conductivity_W_mK"], places=9)
        # Gate ruling: the kernel specific heat is materialised unscaled (conductivity_rel scales k and alpha only).
        self.assertAlmostEqual(out["kernel_specific_heat_J_kgK"], kernel["kernel_specific_heat_J_kgK"], places=9)
        self.assertAlmostEqual(out["kernel_density_kg_m3"], 1.05 * 2696.0, places=9)
        self.assertAlmostEqual(out["absorptivity_IR"], 0.27, places=12)
        self.assertNotIn("absorptivity_index_IR", out)
        pp = _solve("AlSi10Mg", 200, 800, prop_overrides={**snap["thermal"], **out})["processParameters"]
        self.assertEqual(pp["indexAbsorptivity"], 0.18)
        self.assertEqual(pp["effectiveConductivity_W_mK"], round(1.1 * kernel["kernel_conductivity_W_mK"], 3))
        self.assertEqual(pp["propertyConvention"], "kernel-override")
        self.assertEqual(apply_uq_prop_scales(snap["thermal"], {"_uq_absorptivity_scale": 1.0}, kernel=kernel).keys(),
                         {"absorptivity_IR", "absorptivity_Green"})

    def test_kernel_preheat_guard(self):  # 29
        for t0_c, k_want in ((20.0, 16.449), (80.0, 16.857), (200.0, TI64_K_SLOPE * 0.5 * (473.15 + TI64_T_LIQ_K) + TI64_K_INTERCEPT)):
            got = fam.kernel_properties("ti6al4v", t0_c + 273.15)["kernel_conductivity_W_mK"]
            self.assertAlmostEqual(got / k_want, 1.0, delta=1e-3, msg=t0_c)
        for t0_c, k_want in ((20.0, 152.524), (80.0, 156.848), (200.0, 165.352)):
            got = fam.kernel_properties("alsi10mg", t0_c + 273.15)["kernel_conductivity_W_mK"]
            self.assertAlmostEqual(got / k_want, 1.0, delta=1e-3, msg=t0_c)
        # Within 50 K of the liquidus the floored range of the solver applies: [T_liq - 50, T_liq].
        near = fam.kernel_properties("alsi10mg", ALSI_T_LIQ_K - 10.0)
        self.assertEqual(near["T0_K"], ALSI_T_LIQ_K - 50.0)
        self.assertEqual(near["kernel_conductivity_W_mK"], fam.kernel_properties("alsi10mg", ALSI_T_LIQ_K - 50.0)["kernel_conductivity_W_mK"])
        with self.assertRaisesRegex(ValueError, "at or above the liquidus"):
            fam.kernel_properties("alsi10mg", ALSI_T_LIQ_K)
        with self.assertRaisesRegex(ValueError, "at or above the liquidus"):
            _solve("AlSi10Mg", 200, 800, preheat=595.0)
        # Below 293.15 K the forms are evaluated from 293.15 K (the first value held).
        self.assertEqual(fam.kernel_properties("ti6al4v", 200.0)["kernel_conductivity_W_mK"],
                         fam.kernel_properties("ti6al4v", 293.15)["kernel_conductivity_W_mK"])
        self.assertEqual(fam.kernel_properties("alsi10mg", 100.0)["kernel_specific_heat_J_kgK"],
                         fam.kernel_properties("alsi10mg", 293.15)["kernel_specific_heat_J_kgK"])
        # Served per call: the request preheat moves the kernel (OI-3), the index hs uses its own T0.
        a = _solve("Ti-6Al-4V", 200, 800, preheat=20.0)["processParameters"]
        b = _solve("Ti-6Al-4V", 200, 800, preheat=200.0)["processParameters"]
        self.assertEqual(a["effectiveConductivity_W_mK"], 16.449)
        self.assertGreater(b["effectiveConductivity_W_mK"], a["effectiveConductivity_W_mK"])
        self.assertIn("evaluated at the request preheat 200 C", b["propertyConventionBasis"])

    def test_frozen_regime_kernel_literals(self):  # 30
        frozen = frozen_kernel.PRE_P7B_FROZEN_PROPS
        self.assertEqual(frozen["ti6al4v"], {"thermal_conductivity_W_mK": 6.7, "thermal_conductivity_liquid_W_mK": 23.0,
                                             "specific_heat_J_kgK": 526.0, "specific_heat_liquid_J_kgK": 830.0,
                                             "density_kg_m3": 4430.0, "density_liquid_kg_m3": 3950.0,
                                             "absorptivity_IR": 0.35, "absorptivity_index_IR": 0.35})
        self.assertEqual(frozen["alsi10mg"], {"thermal_conductivity_W_mK": 130.0, "thermal_conductivity_liquid_W_mK": 85.0,
                                              "specific_heat_J_kgK": 910.0, "specific_heat_liquid_J_kgK": 1180.0,
                                              "density_kg_m3": 2680.0, "density_liquid_kg_m3": 2390.0,
                                              "absorptivity_IR": 0.18, "absorptivity_index_IR": 0.18})
        self.assertNotIn("kernel_density_kg_m3", frozen_kernel.resolve_props("AlSi10Mg"))
        # The pinned Ti-6Al-4V numbers of test_lpbf_regime_absorptivity_eval (393cdbd1 / 0d52d7f7) still reproduce.
        args = ("Ti-6Al-4V", 150.0, 1200.0, 95.0, 20.0, 30.0, 100.0)
        for kernel, ref in (("eagar-tsai", (109.4, 37.9)), ("goldak", (88.3, 44.4)), ("rosenthal", (82.0, 39.6))):
            mine = frozen_kernel.meltpool_wd(*args, kernel=kernel)
            self.assertEqual((mine["W_um"], mine["D_um"], mine["status"]), (*ref, "computed"), kernel)
        self.assertAlmostEqual(frozen_kernel.flat_enthalpy("AlSi10Mg", 370.0, 1300.0, 100.0, 150.0),
                               0.18 * 370.0 / (2680.0 * 910.0 * (595.0 - 150.0) * math.sqrt(
                                   math.pi * (130.0 / (2680.0 * 910.0)) * 1.3 * (50e-6 ** 3))), places=9)


if __name__ == "__main__":
    unittest.main()
