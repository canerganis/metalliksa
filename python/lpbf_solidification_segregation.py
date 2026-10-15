#!/usr/bin/env python3
"""Nb microsegregation and terminal gamma/Laves screening for Nb-bearing Ni superalloys (stdlib only).

Literature estimate (screening), not CALPHAD. The model is the pseudo-ternary gamma-Nb-C
solidification model of DuPont, Robino and Marder, implemented as written in the source that was
read for this module:

  [D97] J.N. DuPont, C.V. Robino, A.R. Marder, "Solidification modeling of Nb bearing
        superalloys", Superalloys 718, 625, 706 and Derivatives (TMS, Pittsburgh PA,
        June 15-18 1997); Sandia report SAND97-1669C / CONF-970605-3, OSTI 515586.

  [D98] J.N. DuPont, C.V. Robino, A.R. Marder, "Modeling solute redistribution and microstructural
        development in fusion welds of Nb-bearing superalloys", Acta Materialia 46 (1998) 4781-4790,
        doi:10.1016/S1359-6454(98)00123-2 (refereed journal version of the same model).

The solidification constants (k_Nb, k_C, a, b, class II point) are those of [D98] Table 2, read in full
(maintainer decision: refereed journal constants, not the 1997 conference values; they differ, see
docs/LPBF_SCHEIL_LAVES_2026-10-07.md). The equations below are the same in both papers: [D97] Eqs. 1-8 are
[D98] Section 3.2 (negligible Nb diffusion, infinitely fast C diffusion: Eqs. 13c, 14, 2, 4, 21, and 12 for the
forward step). The Weld J 77 (1998) 417s-431s version was NOT read.

Alloy 625 uses a separate, smaller model (binary gamma-Nb Scheil only, D96 Eq. 5
f_e = (C_e / C_0) ** (1 / (k - 1))) from two sources, both read in full:

  [C88] M.J. Cieslak, T.J. Headley, T. Kollie, A.D. Romig Jr., "A melting and solidification study
        of alloy 625", Metall. Trans. A 19A (1988) 2319-2331: low-Fe (about 2.3 wt% Fe) experimental
        alloy 625 heats, GTA welds and DTA. Primary source for k_Nb (Table VIII EPMA, 0.51-0.53;
        Table VII slopes, 0.54), for the measured minor-constituent fractions and for the C/Si effect
        on NbC versus Laves. It gives no eutectic composition.
  [D96] J.N. DuPont, "Solidification of an Alloy 625 Weld Overlay", Metall. Mater. Trans. A 27A
        (1996) 3612-3620: one Fe-diluted (about 28 wt% Fe) GMAW overlay. Source of C_e = 18.9 wt% Nb
        (Section IV-C, built from Alloy 718 data, Table V) and of a cross-check k_Nb = 0.46 (Table IV).

  Neither source gives carbon constants, so no pseudo-ternary model is applied for alloy 625 and the
  phase identity of the terminal constituent (Laves or NbC) is not established. The IN625 Nb band uses
  the Special Metals INCONEL alloy 625 bulletin, Table 1.

Model ([D97] Eqs. 1-8 = [D98] Eqs. 13c, 14, 2, 4, 21, 12):
  * Primary L -> gamma. Nb: Scheil, no diffusion in the solid (Eq. 1)
        f_l = (C_l,Nb / C_0,Nb) ** (1 / (k_Nb - 1)).
    C: equilibrium lever rule, fast diffusion in the solid (Eq. 2). Solidification path Eq. 3.
  * The primary path meets the line of twofold saturation gamma/NbC, C_l,C = a + b C_l,Nb
    (Eqs. 4-6, solved here for C_l,C by bisection).
  * Eutectic-type L -> (gamma + NbC) along that line: Eq. 7, integrated with the forward step of
    Eq. 8 in C_l,Nb. NbC is stoichiometric at 90.5 wt% Nb / 9.5 wt% C, k_NbC,Nb = 90.5 / C_l,Nb.
  * When C_l,Nb reaches the class II point C_Nb,L->(gamma+Laves) the remaining liquid is reported
    as gamma/Laves eutectic-type constituent ([D97] text after Eq. 8). The tabulated class II
    point (23.1 wt% Nb, 0.04 wt% C for the D98 Ni-base set) does not lie exactly on the regressed
    line (a + b * 23.1 = 0.044 wt% C; 0.056 with the D97 constants); this module stops on the Nb coordinate
    and says so.
  * C = 0 limit: the gamma-Nb binary Scheil result f_e = (C_e / C_0) ** (1 / (k - 1)) with
    C_e = C_Nb,L->(gamma+Laves). Carbon ties Nb up as NbC, so the binary value is an upper bound
    on the Laves fraction within this model (stated in the output).

What is NOT modelled in the equilibrium-k result (so those numbers are an upper bound on segregation
only with respect to these effects, which all reduce it): solid-state back-diffusion of Nb, solute
trapping at LPBF solidification rates, dendrite-tip undercooling ([D97] Eq. 1 assumes it negligible).
The constants come from GTA welds and DTA samples of experimental alloys (no Mo, Ti, Al), so LPBF is
always outside the source regime.

Solute trapping is reported separately (rapidSolidification sub-block, screening only): the Aziz
continuous-growth function k(V) = (k_e + V/V_D) / (1 + V/V_D) as written in Ghosh et al. 2017 (G17)
Eq. 12, with V_D carried as the range 0.23-0.31 m/s that G17 fitted to its own Ni-5Nb phase-field
results (1D planar front and 2D cell tips). G17 states that no experimental V_D for Ni-Nb is available
and that part of the trapping in its model is numerical, so V_D is a modelling value, not a
measurement. The equilibrium-k upper bound is never replaced. As-built LPBF IN625 observations from
the NIST studies (Zhang 2018, Lass 2017, Keller 2017) are attached as lpbfObservations for comparison
only; nothing is tuned to them.

Every constant is a CONSTANTS entry {value, unit, source, locator, verified}. An entry that was
not confirmed against a source actually read has verified=False and value None; an alloy that
needs such an entry is reported as "unavailable" (never a guessed number).
"""
from __future__ import annotations

import copy
import math
from typing import Any, Dict, List, Mapping, Optional, Tuple

SCHEMA = "lpbf-solidification-segregation-2"
MODEL_ID = "dupont1997-pseudo-ternary-gamma-nb-c-v1"

EVIDENCE_LABEL = (
    "Literature estimate (screening): Scheil-type pseudo-ternary gamma-Nb-C model, constants from "
    "DuPont, Robino & Marder 1998 (GTA welds of experimental alloys); not CALPHAD; LPBF is outside "
    "the source regime"
)

SOURCES: Dict[str, Dict[str, Any]] = {
    "D97": {
        "citation": ("J.N. DuPont, C.V. Robino, A.R. Marder, 'Solidification modeling of Nb bearing superalloys', "
                     "Superalloys 718, 625, 706 and Derivatives, TMS, Pittsburgh PA, June 15-18 1997; "
                     "Sandia report SAND97-1669C / CONF-970605-3"),
        "url": "https://www.osti.gov/biblio/515586",
        "read": True,
        "note": "full text (scanned report, OSTI servlets/purl/515586) read for this module",
    },
    "D98": {
        "citation": ("J.N. DuPont, C.V. Robino, A.R. Marder, 'Modeling solute redistribution and microstructural "
                     "development in fusion welds of Nb-bearing superalloys', Acta Materialia 46 (1998) 4781-4790, "
                     "doi:10.1016/S1359-6454(98)00123-2"),
        "url": "https://doi.org/10.1016/S1359-6454(98)00123-2",
        "read": True,
        "note": ("full text (journal article) read for this module; Table 2 gives the solidification constants used "
                 "here. Its Section 3.2 (negligible Nb diffusion / infinitely fast C diffusion, Eqs. 13-21) is the "
                 "same model as the equations implemented here (D97 Eqs. 1-8)"),
    },
    "SMC045": {
        "citation": ("Special Metals Corporation, INCONEL alloy 718 technical bulletin, Publication Number SMC-045 "
                     "(2007), Table 1 - Limiting Chemical Composition (conforms to AMS specifications)"),
        "url": "https://www.specialmetals.com/documents/technical-bulletins/inconel/inconel-alloy-718.pdf",
        "read": True,
        "note": ("composition limits for UNS N07718; ASTM F3055 (LPBF IN718) itself was not read, its Table 1 is "
                 "not quoted here"),
    },
    "D96": {
        "citation": ("J.N. DuPont, 'Solidification of an Alloy 625 Weld Overlay', Metall. Mater. Trans. A 27A (1996) "
                     "3612-3620"),
        "url": "https://www.osti.gov/biblio/413291",
        "read": True,
        "note": ("full text (journal article, 9 pages) read for this module; one GMAW overlay of alloy 625 filler on "
                 "2.25Cr-1Mo steel at about 25-28 % dilution (Table II), plus a DTA sample of the same deposit"),
    },
    "C88": {
        "citation": ("M.J. Cieslak, T.J. Headley, T. Kollie, A.D. Romig Jr., 'A melting and solidification study of "
                     "alloy 625', Metall. Trans. A 19A (1988) 2319-2331"),
        "url": "https://doi.org/10.1007/BF02645056",
        "read": True,
        "note": ("full text read for this module; factorial Nb/C/Si heats of alloy 625 with Fe about 2.2-2.6 wt% "
                 "(Table I), GTA welds and DTA"),
    },
    "SM625": {
        "citation": ("Special Metals Corporation, INCONEL alloy 625 technical bulletin (copyright 2013, Aug 13), "
                     "Table 1 - Limiting Chemical Composition"),
        "url": "https://www.specialmetals.com/documents/technical-bulletins/inconel/inconel-alloy-625.pdf",
        "read": True,
        "note": ("composition limits for UNS N06625 (wrought product); no LPBF powder specification (e.g. ASTM F3056) "
                 "was read"),
    },
    "G17": {
        "citation": ("S. Ghosh, L. Ma, N. Ofori-Opoku, J.E. Guyer, 'On the primary spacing and microsegregation of "
                     "cellular dendrites in laser deposited Ni-Nb alloys', Modelling Simul. Mater. Sci. Eng. 25 (2017) "
                     "065002, doi:10.1088/1361-651X/aa7369"),
        "url": "https://doi.org/10.1088/1361-651X/aa7369",
        "read": True,
        "note": ("full text read; binary Ni-5 wt% Nb phase-field (IN718 approximated as binary, k_e 0.48, Table 2) at "
                 "laser-melt-pool G and V; Section 3.2.4 states the Aziz function (Eq. 12) and fits V_D to the "
                 "simulated partitioning"),
    },
    "G18": {
        "citation": ("S. Ghosh, L. Ma, L.E. Levine, R.E. Ricker, M.R. Stoudt, J.C. Heigel, J.E. Guyer, 'Single-track "
                     "melt-pool measurements and microstructures in Inconel 625', JOM (2018), "
                     "doi:10.1007/s11837-018-2771-x"),
        "url": "https://doi.org/10.1007/s11837-018-2771-x",
        "read": True,
        "note": ("full text read; binary Ni-4 wt% Nb phase-field of IN625 single tracks with the anti-trapping flux "
                 "switched off; quotes V_d = 0.23 m/s and k between 0.58 and 0.72 (text with Fig. 4). Its printed "
                 "Aziz expression is inverted (it gives k > 1), so the G17 Eq. 12 form is used"),
    },
    "K17": {
        "citation": ("T. Keller, G. Lindwall, S. Ghosh, L. Ma, B.M. Lane, F. Zhang, U.R. Kattner, E.A. Lass, J.C. Heigel, "
                     "Y. Idell, M.E. Williams, A.J. Allen, J.E. Guyer, L.E. Levine, 'Application of finite element, "
                     "phase-field, and CALPHAD-based methods to additive manufacturing of Ni-based superalloys', "
                     "Acta Materialia (2017), doi:10.1016/j.actamat.2017.05.003"),
        "url": "https://doi.org/10.1016/j.actamat.2017.05.003",
        "read": True,
        "note": ("accepted manuscript read (line-numbered; locators use its line numbers); LPBF IN625, EOS M270, "
                 "195 W, 0.8 m/s; FEA, Scheil/DICTRA and binary Ni-Nb phase-field; as-built TEM and XRD"),
    },
    "L17": {
        "citation": ("E.A. Lass, M.R. Stoudt, M.E. Williams, M.B. Katz, L.E. Levine, T.Q. Phan, T.H. Gnaeupel-Herold, "
                     "D.S. Ng, 'Formation of the Ni3Nb delta-phase in stress-relieved Inconel 625 produced via laser "
                     "powder-bed fusion additive manufacturing', Metall. Mater. Trans. A (2017), "
                     "doi:10.1007/s11661-017-4304-6"),
        "url": "https://doi.org/10.1007/s11661-017-4304-6",
        "read": True,
        "note": "full text read; as-built and stress-relieved LPBF IN625 (EOS M270, 195 W, 800 mm/s)",
    },
    "Z18": {
        "citation": ("F. Zhang, L.E. Levine, A.J. Allen, M.R. Stoudt, G. Lindwall, E.A. Lass, M.E. Williams, Y. Idell, "
                     "C.E. Campbell, 'Effect of heat treatment on the microstructural evolution of a nickel-based "
                     "superalloy additive-manufactured by laser powder bed fusion', Acta Materialia 152 (2018) 200, "
                     "doi:10.1016/j.actamat.2018.03.017"),
        "url": "https://doi.org/10.1016/j.actamat.2018.03.017",
        "read": True,
        "note": "accepted manuscript read; as-built LPBF IN625 EDS line scan and synchrotron XRD (EOS M270, 195 W)",
    },
    "A82": {
        "citation": "M.J. Aziz, 'Model for solute redistribution during rapid solidification', J. Appl. Phys. 53 (1982) 1158",
        "url": None,
        "read": False,
        "note": "original of the continuous-growth function; NOT read here, the function is taken as stated in G17 Eq. 12",
    },
}


def _c(value, unit, source, locator, verified=True):
    return {"value": value, "unit": unit, "source": source, "locator": locator, "verified": verified}


# Constant sets of [D98] Table 2 (refereed journal version of the [D97] conference paper; the maintainer
# decision is to use the journal constants). "ni-base" (Fe about 10-11 wt%) is the primary set; "fe-base" (Fe about
# 44-47 wt%) is reported for IN718 only as a bracketing sensitivity, never interpolated. NbC stoichiometry is also
# printed in D98 (Table 2 and text after Eq. 11, 90.5 wt% Nb / 9.5 wt% C, identical to D97) and is cited to D98.
CONSTANTS: Dict[str, Dict[str, Dict[str, Any]]] = {
    "ni-base": {
        "k_gamma_Nb": _c(0.45, "-", "D98", "D98 Table 2 (k_gamma,Nb, Ni base alloys)"),
        "k_gamma_C": _c(0.21, "-", "D98", "D98 Table 2 (k_gamma,C, Ni base alloys)"),
        "a_wtC": _c(1.13, "wt% C", "D98", "D98 Table 2 (a, Ni base alloys); Eq. 2"),
        "b_wtC_per_wtNb": _c(-0.047, "wt% C / wt% Nb", "D98", "D98 Table 2 (b, Ni base alloys); Eq. 2"),
        "C_Nb_laves": _c(23.1, "wt% Nb", "D98", "D98 Table 2 (C_Nb,L->(gamma+Laves), Ni base alloys)"),
        "C_C_laves": _c(0.04, "wt% C", "D98", "D98 Table 2 (C_C,L->(gamma+Laves), Ni base alloys)"),
        "C_NbC_Nb": _c(90.5, "wt% Nb", "D98", "D98 Table 2 (C_NbC,Nb); text after Eq. 11"),
        "C_NbC_C": _c(9.5, "wt% C", "D98", "D98 Table 2 (C_NbC,C); text after Eq. 11"),
    },
    "fe-base": {
        "k_gamma_Nb": _c(0.25, "-", "D98", "D98 Table 2 (k_gamma,Nb, Fe base alloys)"),
        "k_gamma_C": _c(0.21, "-", "D98", "D98 Table 2 (k_gamma,C, Fe base alloys)"),
        "a_wtC": _c(1.37, "wt% C", "D98", "D98 Table 2 (a, Fe base alloys); Eq. 2"),
        "b_wtC_per_wtNb": _c(-0.065, "wt% C / wt% Nb", "D98", "D98 Table 2 (b, Fe base alloys); Eq. 2"),
        "C_Nb_laves": _c(20.4, "wt% Nb", "D98", "D98 Table 2 (C_Nb,L->(gamma+Laves), Fe base alloys)"),
        "C_C_laves": _c(0.04, "wt% C", "D98", "D98 Table 2 (C_C,L->(gamma+Laves), Fe base alloys)"),
        "C_NbC_Nb": _c(90.5, "wt% Nb", "D98", "D98 Table 2 (C_NbC,Nb); text after Eq. 11"),
        "C_NbC_C": _c(9.5, "wt% C", "D98", "D98 Table 2 (C_NbC,C); text after Eq. 11"),
    },
    # [D97] constant sets (1997 conference values), kept only so the 1997 worked example can be reproduced.
    "ni-base-d97": {
        "k_gamma_Nb": _c(0.46, "-", "D97", "Table 2 (Ni-Base) and Table 3 (k_gamma,Nb, Ni Base Alloys)"),
        "k_gamma_C": _c(0.27, "-", "D97", "Table 2 (Ni-Base) and Table 3 (k_gamma,C, Ni Base Alloys)"),
        "a_wtC": _c(0.98, "wt% C", "D97", "Table 3 (a, Ni Base Alloys); Eq. 4"),
        "b_wtC_per_wtNb": _c(-0.04, "wt% C / wt% Nb", "D97", "Table 3 (b, Ni Base Alloys); Eq. 4"),
        "C_Nb_laves": _c(23.1, "wt% Nb", "D97", "Table 3 (C_Nb,L->(gamma+Laves), Ni Base Alloys)"),
        "C_C_laves": _c(0.03, "wt% C", "D97", "Table 3 (C_C,L->(gamma+Laves), Ni Base Alloys)"),
        "C_NbC_Nb": _c(90.5, "wt% Nb", "D97", "text after Eq. 7 (NbC stoichiometric, 90.5 wt% Nb)"),
        "C_NbC_C": _c(9.5, "wt% C", "D97", "text after Eq. 7 (NbC stoichiometric, 9.5 wt% C)"),
    },
    "fe-base-d97": {
        "k_gamma_Nb": _c(0.25, "-", "D97", "Table 2 (Fe-Base) and Table 3 (k_gamma,Nb, Fe Base Alloys)"),
        "k_gamma_C": _c(0.27, "-", "D97", "Table 2 (Fe-Base, footnote: estimated from the Ni base alloy data); "
                                          "Table 3"),
        "a_wtC": _c(1.24, "wt% C", "D97", "Table 3 (a, Fe Base Alloys); Eq. 4"),
        "b_wtC_per_wtNb": _c(-0.06, "wt% C / wt% Nb", "D97", "Table 3 (b, Fe Base Alloys); Eq. 4"),
        "C_Nb_laves": _c(20.4, "wt% Nb", "D97", "Table 3 (C_Nb,L->(gamma+Laves), Fe Base Alloys)"),
        "C_C_laves": _c(0.03, "wt% C", "D97", "Table 3 (C_C,L->(gamma+Laves), Fe Base Alloys)"),
        "C_NbC_Nb": _c(90.5, "wt% Nb", "D97", "text after Eq. 7 (NbC stoichiometric, 90.5 wt% Nb)"),
        "C_NbC_C": _c(9.5, "wt% C", "D97", "text after Eq. 7 (NbC stoichiometric, 9.5 wt% C)"),
    },
    # Alloy 625 primary set: k_Nb from Cieslak et al. 1988 (low-Fe alloy 625), C_e from DuPont 1996.
    "in625-c88": {
        "k_gamma_Nb": _c(0.51, "-", "C88", "Table VIII (k = C_core / C_nom by EPMA; 0.53, 0.51, 0.52, 0.51 for alloys "
                                           "5-8; the lowest value is used)"),
        "k_gamma_Nb_slopes": _c(0.54, "-", "C88", "Table VII (k = m_L / m_S, Alloy 625, Nb); Conclusion 2"),
        "C_Nb_laves": _c(18.9, "wt% Nb", "D96", "Section IV-C, text after Eq. 5 (eutectic composition 18.9 wt% Nb, "
                                                "estimated from the Alloy 718 values of Table V: gamma 9.3 wt% Nb, "
                                                "Laves 22.1 wt% Nb, about 25/75 vol% gamma/Laves)"),
    },
    # Alloy 625 overlay (DuPont 1996), cross-check only. Binary gamma-Nb Scheil: D96 gives no carbon constants.
    "in625-d96": {
        "k_gamma_Nb": _c(0.46, "-", "D96", "Table IV (Niobium, 625 overlay deposit k_i; dendrite core C_s,i 0.97 over "
                                           "C_0 2.07 wt% by EPMA); Section IV-C"),
        "C_Nb_laves": _c(18.9, "wt% Nb", "D96", "Section IV-C, text after Eq. 5 (eutectic composition 18.9 wt% Nb, "
                                                "estimated from the Alloy 718 values of Table V: gamma 9.3 wt% Nb, "
                                                "Laves 22.1 wt% Nb, about 25/75 vol% gamma/Laves)"),
    },
}

# Composition limits (wt%) used for the Nb band. "max" only -> min None.
COMPOSITION_LIMITS: Dict[str, Dict[str, Any]] = {
    "in718": {
        "source": "SMC045",
        "locator": "Table 1 - Limiting Chemical Composition, %",
        "limits": {
            "Ni": (50.00, 55.00), "Cr": (17.00, 21.00), "Nb": (4.75, 5.50), "Mo": (2.80, 3.30),
            "Ti": (0.65, 1.15), "Al": (0.20, 0.80), "Co": (None, 1.00), "C": (None, 0.08),
            "Mn": (None, 0.35), "Si": (None, 0.35), "P": (None, 0.015), "S": (None, 0.015),
            "B": (None, 0.006), "Cu": (None, 0.30),
        },
        "balance": "Fe",
        "nbNote": "Niobium (plus Tantalum)",
    },
    "in625": {
        "source": "SM625",
        "locator": "Table 1 - Limiting Chemical Composition, %",
        "limits": {
            "Ni": (58.0, None), "Cr": (20.0, 23.0), "Fe": (None, 5.0), "Mo": (8.0, 10.0), "Nb": (3.15, 4.15),
            "C": (None, 0.10), "Mn": (None, 0.50), "Si": (None, 0.50), "P": (None, 0.015), "S": (None, 0.015),
            "Al": (None, 0.40), "Ti": (None, 0.40), "Co": (None, 1.0),
        },
        "balance": None,
        "nbNote": "Niobium (plus Tantalum); Co maximum applies 'if determined'",
    },
}

# Composition range of the source experiments ([D97] Table 1, wt%), per constant set (the same alloys as [D98]
# Table 1; the ranges were transcribed from D97 and are kept with that locator).
SOURCE_COMPOSITION_RANGE: Dict[str, Dict[str, Any]] = {
    "ni-base": {
        "locator": "D97 Table 1, alloys 1-8 (Ni base)",
        "range": {"Fe": (10.39, 11.12), "Ni": (63.93, 68.53), "Cr": (18.54, 19.30), "Nb": (1.82, 5.17),
                  "Si": (0.03, 0.52), "C": (0.010, 0.170)},
        "absentElements": ["Mo", "Ti", "Al", "Co"],
    },
    "fe-base": {
        "locator": "D97 Table 1, alloys 9-16 (Fe base)",
        "range": {"Fe": (44.05, 47.38), "Ni": (30.03, 33.56), "Cr": (19.31, 19.89), "Nb": (1.66, 4.88),
                  "Si": (0.01, 0.67), "C": (0.003, 0.216)},
        "absentElements": ["Mo", "Ti", "Al", "Co"],
    },
    "in625-c88": {
        "locator": "C88 Table I, alloys 5-8 (Nb-bearing)",
        "range": {"Fe": (2.26, 2.31), "Cr": (21.65, 21.83), "Mo": (9.67, 9.81), "Nb": (3.53, 3.61),
                  "Si": (0.03, 0.46), "C": (0.008, 0.038), "Ti": (0.06, 0.06), "Mn": (0.03, 0.03)},
        "absentElements": [],
    },
    # D96 measured one composition: each range is a single value (min == max).
    "in625-d96": {
        "locator": "D96 Table II (chemical analysis of the all-weld-metal sample)",
        "range": {"Fe": (28.14, 28.14), "Ni": (44.91, 44.91), "Cr": (16.67, 16.67), "Mo": (6.78, 6.78),
                  "Nb": (2.07, 2.07), "Si": (0.24, 0.24), "Ti": (0.17, 0.17), "C": (0.050, 0.050)},
        "absentElements": [],
    },
}

# The app's own alloy_registry composition carries no cited source; the band uses the read specification instead.
APP_NOMINAL_NOTE: Dict[str, str] = {
    "in718": ("The app's alloy_registry in718 composition_wt (Nb 5.1, C 0.04 wt%) has no cited source, so the band "
              "uses the SMC-045 specification limits instead. Nb 5.1 lies inside the band (4.75-5.50) and C 0.04 inside "
              "the C range covered by the C = 0 and C max columns."),
}

SOURCE_PROCESS = ("gas tungsten arc (GTA) autogenous welds and DTA samples of investment-cast experimental alloys "
                  "(D97 Experimental Procedure)")

NB_ALLOYS = ("in718", "in625")
NOT_APPLICABLE_REASON = "no Nb-bearing gamma/Laves model for this alloy"
UNVERIFIED_REASON = "constant not verified against primary source"

# Forward step of D97 Eq. 8 (wt% Nb). The source says "a very small amount"; the step is a numerical
# choice (convergence checked in test_lpbf_solidification_segregation against a 10x finer step).
EUTECTIC_STEP_WT_NB = 0.005
FS_SEGREGATION_POINTS = (0.9, 0.95)

UPPER_BOUND_NOTE = (
    "Upper bound with respect to effects that are not modelled and that all reduce segregation: solid-state "
    "back-diffusion of Nb, solute trapping at high solidification rate and dendrite-tip undercooling. It is not a "
    "bound with respect to the choice of k_Nb (see validity), and it is not an upper bound on measured Laves content "
    "(see sourceAgreementNote)."
)
SOURCE_AGREEMENT_NOTE = (
    "Not conservative against measurement, even in the source's own weld regime: D97 Fig. 9b (measured vs calculated "
    "gamma/Laves) shows several alloys with measured gamma/Laves above the calculated value, including alloys for "
    "which the model predicts no gamma/Laves (measured about 0.5-1.5 vol%, e.g. Ni-base alloy 8 in Fig. 3), and "
    "low-C Ni-base alloys where the model is about 2-3x high (alloys 5 and 7: measured about 2-3 vol% in Fig. 3). "
    "D97 also reports that Fe and Si raise the gamma/Laves amount; IN718 contains about 18 wt% Fe plus Mo, which the "
    "source alloys do not."
)
QUANTITY_NOTE = (
    "fGammaLavesConstituent and fGammaNbCConstituent are fractions of the gamma/Laves and gamma/NbC eutectic-type "
    "constituents (remaining liquid that transforms, eutectic gamma included; D97 terminology), not phase fractions "
    "of Laves or NbC."
)
BINARY_BOUND_NOTE = (
    "Binary gamma-Nb Scheil (C = 0): carbon ties Nb up as NbC, so within this model the binary value is an upper "
    "bound over carbon content on the gamma/Laves constituent fraction (a model statement, not a bound on "
    "measurement)."
)


class SegregationModelError(ValueError):
    """Invalid model input (k outside (0, 1), non-positive composition)."""


def _value(cset: Mapping[str, Dict[str, Any]], key: str) -> float:
    entry = cset[key]
    if not entry.get("verified") or entry.get("value") is None:
        raise LookupError(f"{key}: {UNVERIFIED_REASON}")
    return float(entry["value"])


def _check_k(k: float) -> None:
    if not (isinstance(k, (int, float)) and math.isfinite(k)):
        raise SegregationModelError("k must be finite")
    if abs(k - 1.0) < 1e-9:
        raise SegregationModelError("k = 1: no segregation, the Scheil exponent 1/(k-1) is undefined")
    if not 0.0 < k < 1.0:
        raise SegregationModelError("k must lie in (0, 1) for a solute rejected to the liquid")


def _check_positive(name: str, value: float) -> None:
    if not (isinstance(value, (int, float)) and math.isfinite(value) and value > 0.0):
        raise SegregationModelError(f"{name} must be a finite positive number")


def scheil_liquid_composition(c0: float, k: float, fs: float) -> float:
    """Scheil liquid composition C_L = C0 (1 - fs)^(k - 1) (D97 Eq. 1 rearranged), 0 <= fs < 1."""
    _check_k(k)
    _check_positive("c0", c0)
    if not (0.0 <= fs < 1.0):
        raise SegregationModelError("fs must lie in [0, 1)")
    return c0 * (1.0 - fs) ** (k - 1.0)


def scheil_eutectic_fraction(c0: float, ce: float, k: float) -> float:
    """Remaining liquid when the Scheil liquid reaches the eutectic composition: (Ce/C0)^(1/(k-1)), capped at 1."""
    _check_k(k)
    _check_positive("c0", c0)
    _check_positive("ce", ce)
    if c0 >= ce:
        return 1.0
    return (ce / c0) ** (1.0 / (k - 1.0))


def pseudo_ternary_path(c0_nb: float, c0_c: float, cset: Mapping[str, Dict[str, Any]],
                        step_wt_nb: float = EUTECTIC_STEP_WT_NB) -> Dict[str, Any]:
    """D97 Eqs. 1-8 for one composition. Fractions are fraction of the liquid (D97 compares them with volume %)."""
    k_nb = _value(cset, "k_gamma_Nb")
    k_c = _value(cset, "k_gamma_C")
    a = _value(cset, "a_wtC")
    b = _value(cset, "b_wtC_per_wtNb")
    ce_nb = _value(cset, "C_Nb_laves")
    c_nbc_nb = _value(cset, "C_NbC_Nb")
    c_nbc_c = _value(cset, "C_NbC_C")
    _check_k(k_nb)
    _check_k(k_c)
    _check_positive("c0_nb", c0_nb)
    _check_positive("c0_c", c0_c)
    _check_positive("step_wt_nb", step_wt_nb)
    if c0_nb >= ce_nb:
        return {"status": "computed", "primaryEnd": "nominal Nb at or above the gamma/Laves point",
                "fLiquidPrimaryEnd": 1.0, "fGammaNbCConstituent": 0.0, "fGammaLavesConstituent": 1.0, "fEutecticTotal": 1.0,
                "terminatedBy": "nominal-composition"}
    if c0_c >= a + b * c0_nb:
        return {"status": "unavailable", "reasons": [{"code": "outside-source-model-domain", "params": {}, "parent": None}],
                "reason": "nominal composition lies in the primary NbC field of the D97 solidification surface"}

    def path_nb(clc: float) -> float:  # Eq. 3
        return c0_nb * ((c0_c - k_c * clc) / ((1.0 - k_c) * clc)) ** (k_nb - 1.0)

    def gap(clc: float) -> float:  # Eq. 6 as (Eq. 5) - (Eq. 3)
        return (clc - a) / b - path_nb(clc)

    lo, hi = c0_c, c0_c / k_c
    lo_eps, hi_eps = lo * (1.0 + 1e-12), hi * (1.0 - 1e-12)
    g_lo = gap(lo_eps)
    for _ in range(200):
        mid = 0.5 * (lo_eps + hi_eps)
        g_mid = gap(mid)
        if (g_lo > 0) == (g_mid > 0):
            lo_eps, g_lo = mid, g_mid
        else:
            hi_eps = mid
    clc = 0.5 * (lo_eps + hi_eps)
    clnb = (clc - a) / b  # Eq. 5
    if clnb >= ce_nb:
        # The primary path reaches the gamma/Laves point before the gamma/NbC line: no NbC.
        f_laves = scheil_eutectic_fraction(c0_nb, ce_nb, k_nb)
        return {"status": "computed", "primaryEnd": "gamma/Laves point (primary path stays below the NbC line)",
                "fLiquidPrimaryEnd": f_laves, "liquidAtPrimaryEnd": {"Nb_wt": ce_nb, "C_wt": None},
                "fGammaNbCConstituent": 0.0, "fGammaLavesConstituent": f_laves, "fEutecticTotal": f_laves, "terminatedBy": "laves-point"}
    fl = (clnb / c0_nb) ** (1.0 / (k_nb - 1.0))  # Eq. 1
    f_primary_end = fl
    liquid_primary_end = {"Nb_wt": clnb, "C_wt": clc}
    terminated = "laves-point"
    while clnb < ce_nb:
        k_nbc_nb = c_nbc_nb / clnb
        dfl = (-(1.0 / (1.0 - k_nb)) * fl / clnb
               - ((k_nbc_nb - k_nb) / (1.0 - k_nb))
               * ((b * k_c * c0_c - b * c_nbc_c * (fl + k_c * (1.0 - fl))) / (c_nbc_c - k_c * clc) ** 2))  # Eq. 7
        step = min(step_wt_nb, ce_nb - clnb)
        fl_next = fl + dfl * step  # Eq. 8
        clnb += step
        clc = a + b * clnb  # Eq. 4
        if fl_next <= 0.0:
            fl = 0.0
            terminated = "liquid-exhausted-on-NbC-line"
            break
        fl = fl_next
    f_laves = fl if terminated == "laves-point" else 0.0
    return {"status": "computed", "primaryEnd": "gamma/NbC line of twofold saturation",
            "fLiquidPrimaryEnd": f_primary_end, "liquidAtPrimaryEnd": liquid_primary_end,
            "fGammaNbCConstituent": f_primary_end - f_laves, "fGammaLavesConstituent": f_laves, "fEutecticTotal": f_primary_end,
            "terminatedBy": terminated, "stepWtNb": step_wt_nb,
            "liquidAtTermination": {"Nb_wt": clnb, "C_wt": clc}}


def laves_risk_class(f_laves: Optional[float]) -> Optional[str]:
    """Two classes, no fitted threshold: any terminal gamma/Laves fraction > 0 under the Scheil-type model."""
    if f_laves is None:
        return None
    return "eutectic Laves expected (Scheil)" if f_laves > 0.0 else "no terminal eutectic under Scheil"


def _r(x: Optional[float], nd: int = 4) -> Optional[float]:
    return None if x is None else round(float(x), nd)


def _band_point(label: str, nb: float, c_max: Optional[float], cset) -> Dict[str, Any]:
    k_nb = _value(cset, "k_gamma_Nb")
    ce = _value(cset, "C_Nb_laves")
    f_bin = scheil_eutectic_fraction(nb, ce, k_nb)
    point: Dict[str, Any] = {
        "label": label, "Nb_wt": nb,
        "binaryUpperBound": {"C_wt": 0.0, "fGammaLavesConstituent": _r(f_bin), "riskClass": laves_risk_class(f_bin)},
    }
    if c_max is not None:
        tern = pseudo_ternary_path(nb, c_max, cset)
        if tern["status"] == "computed":
            point["pseudoTernaryAtCmax"] = {
                "C_wt": c_max, "fGammaNbCConstituent": _r(tern["fGammaNbCConstituent"]), "fGammaLavesConstituent": _r(tern["fGammaLavesConstituent"]),
                "fEutecticTotal": _r(tern["fEutecticTotal"]), "fLiquidPrimaryEnd": _r(tern["fLiquidPrimaryEnd"]),
                "terminatedBy": tern["terminatedBy"], "riskClass": laves_risk_class(tern["fGammaLavesConstituent"]),
            }
        else:
            point["pseudoTernaryAtCmax"] = {"C_wt": c_max, "status": tern["status"], "reason": tern.get("reason")}
    return point


def _segregation_ratios(nb: float, cset) -> Dict[str, Any]:
    k_nb = _value(cset, "k_gamma_Nb")
    ce = _value(cset, "C_Nb_laves")
    f_e = scheil_eutectic_fraction(nb, ce, k_nb)
    rows = []
    for fs in FS_SEGREGATION_POINTS:
        reached = (1.0 - fs) <= f_e
        cl = ce if reached else scheil_liquid_composition(nb, k_nb, fs)
        rows.append({"fs": fs, "liquidNb_wt": _r(cl, 3), "ratioToNominal": _r(cl / nb, 3),
                     "atEutecticComposition": reached})
    return {
        "Nb_wt": nb, "basis": "binary gamma-Nb Scheil (D97 Eq. 1), C = 0",
        "coreNb_wt": _r(k_nb * nb, 3), "coreRatioToNominal": _r(k_nb, 3),
        "interdendritic": rows,
        "note": ("When the remaining liquid at fs is below the eutectic fraction the liquid has reached the gamma/Laves "
                 "composition and the ratio is capped there (atEutecticComposition = true)."),
    }


def _spec_band(alloy_id: str) -> Tuple[Dict[str, float], Optional[float], Dict[str, Any]]:
    spec = COMPOSITION_LIMITS[alloy_id]
    nb_lo, nb_hi = spec["limits"]["Nb"]
    c_max = spec["limits"]["C"][1]
    others_max = sum(hi for el, (lo, hi) in spec["limits"].items() if hi is not None)
    others_min = sum(lo for el, (lo, hi) in spec["limits"].items() if lo is not None)
    band = {"min": nb_lo, "nominal": round(0.5 * (nb_lo + nb_hi), 4), "max": nb_hi}
    info = {
        "source": SOURCES[spec["source"]]["citation"], "locator": spec["locator"],
        "Nb_wt": {"min": nb_lo, "max": nb_hi, "nominal": band["nominal"],
                  "nominalIs": "midpoint of the specification range (not a measured composition)",
                  "note": spec["nbNote"]},
        "C_wt": {"min": None, "max": c_max, "note": "maximum only; C = 0 is the binary upper-bound end"},
        "balanceElement": spec["balance"],
        "balanceByDifference_wt": {"min": round(100.0 - others_max, 2), "max": round(100.0 - others_min, 2)},
        "appNominalNote": APP_NOMINAL_NOTE.get(alloy_id),
    }
    return band, c_max, info


def _validity(alloy_id: str, spec_info: Dict[str, Any], set_id: str) -> Dict[str, Any]:
    src = SOURCE_COMPOSITION_RANGE[set_id]
    spec = COMPOSITION_LIMITS[alloy_id]["limits"]
    outside: List[str] = []
    fe = spec_info["balanceByDifference_wt"]
    fe_lo, fe_hi = src["range"]["Fe"]
    if fe["min"] < fe_lo or fe["max"] > fe_hi:
        outside.append(f"Fe (balance, {fe['min']}-{fe['max']} wt% by difference) extends outside the source "
                       f"{fe_lo}-{fe_hi} wt%")
    nb_lo, nb_hi = src["range"]["Nb"]
    s_lo, s_hi = spec["Nb"]
    if s_hi > nb_hi or s_lo < nb_lo:
        outside.append(f"Nb specification {s_lo}-{s_hi} wt% extends outside the source {nb_lo}-{nb_hi} wt%")
    for el in src["absentElements"]:
        lo, hi = spec.get(el, (None, None))
        if (lo or 0.0) > 0.0:
            outside.append(f"{el} ({lo}-{hi} wt% in the specification) is absent from the source alloys")
    return {
        "sourceCompositionRange_wt": {el: list(v) for el, v in src["range"].items()},
        "sourceCompositionLocator": src["locator"],
        "sourceAbsentElements": list(src["absentElements"]),
        "outsideSourceComposition": bool(outside),
        "outsideSourceCompositionReasons": outside,
        "sourceRegime": SOURCE_PROCESS,
        "outsideSourceRegime": True,
        "outsideSourceRegimeReason": ("LPBF is not among the source processes (GTA welds, DTA samples); the k values "
                                      "and the Scheil assumption were not established at LPBF solidification rates"),
        "kTransferNote": ("D98 reports k_Nb = 0.45 for its Ni base alloys (Fe about 11 wt%) and 0.25 for its Fe base "
                          "alloys (Fe about 45 wt%) and attributes the drop to Fe. The source gives no k_Nb(Fe) relation "
                          "here, so no interpolation is made; the Fe-base result is shown as a bracketing sensitivity."),
    }


def _process_coupling(microstructure: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    from lpbf_solidification_microstructure import project_build_job_microstructure
    block = (copy.deepcopy(dict(microstructure)) if isinstance(microstructure, Mapping)
             and isinstance(microstructure.get("quantities"), Mapping)
             else project_build_job_microstructure({}))
    block.update(usedInCalculation=False, source="thermal.solidificationKinetics")
    return block


def _unavailable(alloy_id: str, reason: str, status: str = "unavailable") -> Dict[str, Any]:
    return {"schema": SCHEMA, "modelId": MODEL_ID, "status": status, "alloyId": alloy_id, "reason": reason,
            "reasons": [{"code": "not-requested" if status == "not-requested" else "missing-source-bound-model", "params": {}, "parent": None}]}


def _constants_view(set_id: str) -> Dict[str, Any]:
    return {key: dict(entry, sourceCitation=SOURCES[entry["source"]]["citation"])
            for key, entry in CONSTANTS[set_id].items()}


def _segregation_envelope(result: Dict[str, Any]) -> Dict[str, Any]:
    """Attach source-labelled inventories without changing the composition-only calculation."""
    from quantity_envelope import container, input_record, quantity, unavailable, reason, observation, source_ref
    inputs = {
        "composition": input_record("declaredAssumption", "alloy-registry:composition", status="inRange",
                                    declaration_locator="python/alloy_registry.py", scope="nominal-specification-screen"),
        "sourceCoefficients": input_record("sourceDefault", "segregation:source-constants", status="inRange",
                                           source_locator="python/lpbf_solidification_segregation.py#CONSTANTS",
                                           scope="source-alloy-process"),
    }
    quantities = {}
    for point in result.get("band", []):
        for kind in ("binaryUpperBound", "pseudoTernaryAtCmax"):
            row = point.get(kind) or {}
            name = point["label"] + ("Binary" if kind == "binaryUpperBound" else "Ternary")
            if row.get("fGammaLavesConstituent") is None:
                quantities[name] = unavailable("scheil-phase-inventory", [reason("missing-source-bound-model")],
                                               depends_on=("composition", "sourceCoefficients"))
                continue
            inventory = {"gammaLavesConstituent": row["fGammaLavesConstituent"]}
            if row.get("fGammaNbCConstituent") is not None:
                inventory["gammaNbCConstituent"] = row["fGammaNbCConstituent"]
            quantities[name] = quantity("scheil-phase-inventory", inventory, inputs=inputs,
                                        depends_on=("composition", "sourceCoefficients"),
                                        sources=[source_ref("D98" if result["alloyId"] == "in718" else "C88-D96",
                                                            "constant and band locators in this result", "primary-read")],
                                        model_identity=result["modelId"], fraction_basis="microconstituent",
                                        uncertainty={"kind": "not-quantified", "construction": "not-quantified"})
    if not quantities:
        quantities["phaseInventory"] = unavailable("scheil-phase-inventory", result.get("reasons") or
                                                   [reason("missing-source-bound-model")],
                                                   status=result.get("status", "unavailable"),
                                                   depends_on=("composition", "sourceCoefficients"))
    observations = {}
    if result.get("alloyId") == "in625":
        observations["edsNbMassFraction"] = observation(
            "Nb mass fraction along the as-built EDS line scan", {k: v / 100 for k, v in Z18_EDS_NB.items()}, "1",
            "Measured", [source_ref("Z18", "Results Figs. 3 and 4", "primary-read")],
            material_scope="IN625 source batch", process_scope="EOS M270 195 W 800 mm/s", comparability="context-only")
    result.update(container(quantities, input_provenance=inputs, observations=observations))
    return result


def _segregation_estimate(alloy_id: str, microstructure: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """Segregation block for one alloy id. in718: D98 pseudo-ternary; in625: D96 binary Scheil; others n/a."""
    aid = str(alloy_id or "").strip().lower()
    if aid not in NB_ALLOYS:
        return _unavailable(aid, NOT_APPLICABLE_REASON, status="not-requested")
    if aid == "in625":
        return _in625_estimate(microstructure)
    set_id = "ni-base"
    try:
        band, c_max, spec_info = _spec_band(aid)
        points = [_band_point(lbl, band[lbl], c_max, CONSTANTS[set_id]) for lbl in ("min", "nominal", "max")]
        sensitivity = _band_point("nominal", band["nominal"], c_max, CONSTANTS["fe-base"])
        ratios = _segregation_ratios(band["nominal"], CONSTANTS[set_id])
    except LookupError as exc:
        return _unavailable(aid, str(exc))
    any_laves = any((p["binaryUpperBound"]["fGammaLavesConstituent"] or 0) > 0
                    or (p.get("pseudoTernaryAtCmax", {}).get("fGammaLavesConstituent") or 0) > 0 for p in points)
    return {
        "schema": SCHEMA,
        "modelId": MODEL_ID,
        "status": "computed",
        "alloyId": aid,
        "source": SOURCES["D98"],
        "constantSet": set_id,
        "constants": _constants_view(set_id),
        "k_Nb": {"value": CONSTANTS[set_id]["k_gamma_Nb"]["value"],
                 "citation": SOURCES["D98"]["citation"], "locator": CONSTANTS[set_id]["k_gamma_Nb"]["locator"]},
        "composition": spec_info,
        "band": points,
        "bandNote": ("gamma/Laves constituent fraction at C = 0 (binary; model upper bound over C only) and at the "
                     "specification maximum C with the pseudo-ternary model; fractions are of the liquid, which D98 "
                     "compares with measured volume %"),
        "quantity": QUANTITY_NOTE,
        "feBaseSensitivity": {"constantSet": "fe-base", "constants": _constants_view("fe-base"),
                              "point": sensitivity,
                              "note": "bracketing sensitivity with the D98 Fe-base constants; not an interpolation"},
        "segregation": ratios,
        "riskClass": laves_risk_class(1.0 if any_laves else 0.0),
        "riskClassRule": ("gamma/Laves constituent > 0 at any band point under the Scheil-type model; no fitted "
                          "threshold. Binary Scheil without back-diffusion predicts a terminal gamma/Laves eutectic for "
                          "any Nb > 0, so this class is positive by construction for every Nb-bearing composition and "
                          "does not discriminate between compositions."),
        "riskClassPositiveByConstruction": True,
        "processCoupling": _process_coupling(microstructure),
        "upperBoundNote": UPPER_BOUND_NOTE,
        "sourceAgreementNote": SOURCE_AGREEMENT_NOTE,
        "binaryBoundNote": BINARY_BOUND_NOTE,
        "notModelled": ["solid-state back-diffusion of Nb", "solute trapping in the equilibrium-k upper bound (screening k(V) is given separately in rapidSolidification)",
                        "dendrite-tip undercooling", "Mo, Ti, Al and Si effects on the Laves reaction",
                        "mechanical consequences of Laves"],
        "classIINote": ("D98 Table 2 class II point (C_Nb, C_C) is not exactly on the regressed gamma/NbC line "
                        "(a + b * C_Nb gives about 0.044 wt% C at 23.1 wt% Nb, against 0.04 tabulated); the eutectic-type integration stops "
                        "when C_l,Nb reaches C_Nb,L->(gamma+Laves)."),
        "validity": _validity(aid, spec_info, set_id),
        "rapidSolidification": _rapid_solidification(aid, microstructure),
        "lpbfObservations": lpbf_observations(aid),
    }


# ---------------------------------------------------------------------------------------------------------------
# Alloy 625: binary gamma-Nb Scheil. k_Nb from Cieslak et al. 1988 (C88, low-Fe alloy 625), C_e from DuPont 1996
# (D96); D96 overlay values are a second-source cross-check. Separate from the D97 path above so that the IN718
# output is unchanged by construction.

IN625_SET = "in625-c88"
IN625_MODEL_ID = "cieslak1988-dupont1996-binary-gamma-nb-scheil-v1"
IN625_EVIDENCE_LABEL = (
    "Literature estimate (screening): binary gamma-Nb Scheil, k_Nb from Cieslak et al. 1988 (low-Fe alloy 625, GTA "
    "welds and DTA), C_e from DuPont 1996 (taken from Alloy 718 data); not CALPHAD; LPBF is outside the source regime"
)
IN625_SOURCE_PROCESS = ("gas tungsten arc (GTA) welds and DTA samples (20 degC/min) of vacuum-melted experimental "
                        "alloy 625 heats with Fe about 2.3 wt% (C88 Section II)")
C88_ALLOYS = ("5", "6", "7", "8")
# C88 alloys 5-8 (Nb-bearing): Table I composition, Table VIII EPMA k_Nb, Section III-B measured total minor
# constituent (area = volume fraction, rapid-scan DTA specimens; the constituents were not separated), Table IV/IX
# phases in the GTA weld metal.
C88_MEASURED = {
    "5": {"Nb_wt": 3.61, "C_wt": 0.009, "Si_wt": 0.03, "k": 0.53, "fMeasured": 0.003, "fMeasuredSd": 0.001,
          "phases": "Laves (predominant) and a little NbC"},
    "6": {"Nb_wt": 3.60, "C_wt": 0.038, "Si_wt": 0.03, "k": 0.51, "fMeasured": 0.007, "fMeasuredSd": 0.005,
          "phases": "NbC only (no Laves)"},
    "7": {"Nb_wt": 3.57, "C_wt": 0.008, "Si_wt": 0.38, "k": 0.52, "fMeasured": 0.013, "fMeasuredSd": 0.003,
          "phases": "Laves (predominant), NbC, M6C"},
    "8": {"Nb_wt": 3.53, "C_wt": 0.035, "Si_wt": 0.46, "k": 0.51, "fMeasured": 0.009, "fMeasuredSd": 0.004,
          "phases": "NbC (predominant) and Laves"},
}
# D96's own check (Section IV-C, Eq. 5): C_0 2.07, k 0.46, C_e 18.9 -> f_e 1.7 vol%, against 1.3-2.2 vol%
# gamma + Laves measured by QIA in the DTA sample (Section III-A).
D96_CHECK = {"C0_wt": 2.07, "k": 0.46, "Ce_wt": 18.9, "paperValue": 0.017, "measuredRange": (0.013, 0.022)}

IN625_PHASE_IDENTITY_NOTE = (
    "Phase identity not established. In low-Fe alloy 625 (Fe about 2.3 wt%) C88 found the terminal constituent to "
    "depend on C and Si: with 0.038 wt% C and no added Si only gamma/NbC formed (alloy 6, no Laves); with low C and no "
    "added Si a small amount of mostly Laves formed (alloy 5); Si (0.38-0.46 wt%) promoted Laves and, at low C, M6C "
    "(Sections III-B and IV-B, Tables IV and IX). D96 adds that Fe favours Laves over NbC (Section IV-B). The IN625 "
    "specification allows C up to 0.10 and Si up to 0.50 wt%, so the computed number is a gamma/Laves-type estimate "
    "with C_e = 18.9 wt% Nb, not a Laves prediction; the constituent may be gamma/NbC, gamma/Laves or both."
)
IN625_UPPER_BOUND_NOTE = (
    "Upper bound with respect to effects that are not modelled and that all reduce the terminal constituent: "
    "solid-state back-diffusion of Nb, solute trapping at high solidification rate, dendrite-tip undercooling, and Nb "
    "tied up as NbC by carbon (no carbon model for alloy 625). It is not a bound with respect to k_Nb or C_e. Against "
    "the C88 low-Fe measurements the estimate is high (see sourceAgreementNote), but that is one set of four heats at "
    "DTA cooling, not a guarantee."
)
IN625_QUANTITY_NOTE = (
    "fGammaLavesConstituent is the fraction of the liquid that remains when the binary Scheil liquid reaches "
    "C_e = 18.9 wt% Nb (D96 Eq. 5); D96 treats it as the gamma/Laves eutectic-type constituent (eutectic gamma "
    "included) and compares it with volume %. It is not a phase fraction of Laves, and its phase identity is not "
    "established (see validity.phaseIdentityNote)."
)
IN625_NO_CARBON_REASON = ("not modelled: no carbon constants for alloy 625 in C88 or D96 (binary gamma-Nb Scheil "
                          "only)")


def _in625_band() -> Tuple[Dict[str, float], Dict[str, Any]]:
    spec = COMPOSITION_LIMITS["in625"]
    nb_lo, nb_hi = spec["limits"]["Nb"]
    band = {"min": nb_lo, "nominal": round(0.5 * (nb_lo + nb_hi), 4), "max": nb_hi}
    info = {
        "source": SOURCES[spec["source"]]["citation"], "locator": spec["locator"],
        "Nb_wt": {"min": nb_lo, "max": nb_hi, "nominal": band["nominal"],
                  "nominalIs": "midpoint of the specification range (not a measured composition)",
                  "note": spec["nbNote"]},
        "C_wt": {"min": None, "max": spec["limits"]["C"][1],
                 "note": "maximum only; not used: no carbon model for alloy 625"},
        "Fe_wt": {"min": None, "max": spec["limits"]["Fe"][1]},
        "limits_wt": {el: list(v) for el, v in spec["limits"].items()},
        "balanceElement": None,
        "appNominalNote": None,
    }
    return band, info


def _in625_outside(set_id: str) -> List[str]:
    """Specification ranges that extend outside the source composition range (containment, as for D97)."""
    src = SOURCE_COMPOSITION_RANGE[set_id]["range"]
    spec = COMPOSITION_LIMITS["in625"]["limits"]
    out: List[str] = []
    for el, (s_lo, s_hi) in src.items():
        lo, hi = spec.get(el, (None, None))
        # A maximum-only limit is compared on its maximum (the lower end, 0, is not counted as extrapolation).
        if (lo is not None and lo < s_lo) or (hi is not None and hi > s_hi):
            rng = f"{lo}-{hi}" if lo is not None and hi is not None else (f">= {lo}" if lo is not None else f"<= {hi}")
            src_rng = f"{s_lo}" if s_lo == s_hi else f"{s_lo}-{s_hi}"
            out.append(f"{el}: IN625 specification {rng} wt% extends outside the source {src_rng} wt%")
    return out


def _in625_validity() -> Dict[str, Any]:
    src = SOURCE_COMPOSITION_RANGE[IN625_SET]
    d96 = SOURCE_COMPOSITION_RANGE["in625-d96"]
    return {
        "sourceCompositionRange_wt": {el: list(v) for el, v in src["range"].items()},
        "sourceCompositionLocator": src["locator"],
        "sourceAbsentElements": list(src["absentElements"]),
        "outsideSourceComposition": True,
        "outsideSourceCompositionReasons": _in625_outside(IN625_SET),
        "sourceRegime": IN625_SOURCE_PROCESS,
        "outsideSourceRegime": True,
        "outsideSourceRegimeReason": (
            "LPBF is not among the source processes (C88: GTA welds and DTA samples; D96: one GMAW overlay); k_Nb and "
            "the Scheil assumption were not established at LPBF solidification rates"),
        "kTransferNote": (
            "k_Nb = 0.51 is the lowest of the four EPMA dendrite-core values in C88 Table VIII (0.51-0.53, alloys 5-8, "
            "Nb 3.53-3.61 wt%, Fe about 2.3 wt%); C88 Table VII gives 0.54 from liquidus/solidus slopes. The source Nb "
            "is 3.53-3.61 wt%, so the band ends (3.15 and 4.15 wt%) assume a constant k."),
        "ceTransferNote": (
            "C_e = 18.9 wt% Nb is not measured on alloy 625: D96 (Section IV-C) builds it from Alloy 718 data (gamma "
            "9.3 wt% Nb in the gamma/Laves eutectic, Table V) and the Fe-diluted overlay Laves (22.1 wt% Nb, Table III). "
            "C88 gives no eutectic composition; its Laves in low-Fe alloy 625 holds less Nb (16.8-19.2 wt%, Table V), "
            "so C_e for low-Fe IN625 may be lower, which would raise the computed fraction."),
        "d96SourceComposition_wt": {el: v[0] for el, v in d96["range"].items()},
        "d96SourceNote": ("D96 is a single Fe-diluted (28.14 wt% Fe) GMAW overlay (Table II); wrought and LPBF IN625 "
                          "(Fe <= 5 wt%) are outside it, so its k_Nb is used only as a cross-check."),
        "phaseIdentityNote": IN625_PHASE_IDENTITY_NOTE,
    }


def _in625_comparison(ce: float) -> List[Dict[str, Any]]:
    rows = []
    for alloy in C88_ALLOYS:
        m = C88_MEASURED[alloy]
        f = scheil_eutectic_fraction(m["Nb_wt"], ce, m["k"])
        rows.append({"alloy": alloy, "Nb_wt": m["Nb_wt"], "C_wt": m["C_wt"], "Si_wt": m["Si_wt"], "k": m["k"],
                     "fComputed": _r(f), "fMeasured": m["fMeasured"], "fMeasuredSd": m["fMeasuredSd"],
                     "ratioComputedToMeasured": _r(f / m["fMeasured"], 1), "phasesObserved": m["phases"]})
    return rows


def _in625_estimate(microstructure: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    cset = CONSTANTS[IN625_SET]
    try:
        k_nb = _value(cset, "k_gamma_Nb")
        k_slope = _value(cset, "k_gamma_Nb_slopes")
        ce = _value(cset, "C_Nb_laves")
        k_d96 = _value(CONSTANTS["in625-d96"], "k_gamma_Nb")
    except LookupError as exc:
        return _unavailable("in625", str(exc))
    band, spec_info = _in625_band()
    points = []
    for lbl in ("min", "nominal", "max"):
        nb = band[lbl]
        points.append({
            "label": lbl, "Nb_wt": nb,
            "binaryUpperBound": {"C_wt": 0.0, "fGammaLavesConstituent": _r(scheil_eutectic_fraction(nb, ce, k_nb))},
            "pseudoTernaryAtCmax": {"C_wt": spec_info["C_wt"]["max"], "status": "unavailable", "reasons": [{"code": "missing-source-bound-model", "params": {}, "parent": None}],
                                    "reason": IN625_NO_CARBON_REASON},
        })
    ratios = _segregation_ratios(band["nominal"], cset)
    ratios["basis"] = "binary gamma-Nb Scheil (k_Nb C88 Table VIII, C_e D96), C = 0"
    check = scheil_eutectic_fraction(D96_CHECK["C0_wt"], D96_CHECK["Ce_wt"], D96_CHECK["k"])
    comparison = _in625_comparison(ce)
    ratios_lo = min(r["ratioComputedToMeasured"] for r in comparison)
    ratios_hi = max(r["ratioComputedToMeasured"] for r in comparison)

    def kband(k: float) -> List[Dict[str, Any]]:
        return [{"label": lbl, "Nb_wt": band[lbl], "fGammaLavesConstituent": _r(scheil_eutectic_fraction(band[lbl], ce, k))}
                for lbl in ("min", "nominal", "max")]

    return {
        "schema": SCHEMA,
        "modelId": IN625_MODEL_ID,
        "status": "computed",
        "alloyId": "in625",
        "source": SOURCES["C88"],
        "secondarySource": SOURCES["D96"],
        "constantSet": IN625_SET,
        "constants": _constants_view(IN625_SET),
        "k_Nb": {"value": cset["k_gamma_Nb"]["value"], "citation": SOURCES["C88"]["citation"],
                 "locator": cset["k_gamma_Nb"]["locator"]},
        "composition": spec_info,
        "band": points,
        "bandNote": ("terminal eutectic-type constituent fraction from D96 Eq. 5 (binary gamma-Nb Scheil, C = 0) over "
                     "the specification Nb band with k_Nb from C88; fraction of the liquid, which both sources compare "
                     "with measured volume %. Carbon is not modelled for alloy 625."),
        "quantity": IN625_QUANTITY_NOTE,
        "kSensitivity": {
            "note": ("same C_e, other read k_Nb values: C88 Table VII (liquidus/solidus slopes) and the D96 Fe-diluted "
                     "overlay (Table IV); a lower k gives a larger fraction"),
            "c88TableVII": {"k": k_slope, "band": kband(k_slope)},
            "d96Overlay": {"k": k_d96, "band": kband(k_d96)},
        },
        "segregation": ratios,
        "riskClass": None,
        "riskClassRule": ("No Laves risk class for alloy 625: whether the terminal constituent is Laves or NbC depends "
                          "on C and Si and is not established here (see validity.phaseIdentityNote)."),
        "riskClassPositiveByConstruction": None,
        "processCoupling": _process_coupling(microstructure),
        "upperBoundNote": IN625_UPPER_BOUND_NOTE,
        "sourceAgreementNote": (
            "C88 low-Fe alloy 625 (alloys 5-8, Nb 3.53-3.61 wt%, rapid-scan DTA specimens): measured total minor "
            "constituent 0.3-1.3 vol% (Section III-B); this model with each alloy's own k_Nb (Table VIII) and "
            f"C_e 18.9 gives {min(r['fComputed'] for r in comparison) * 100:.1f}-"
            f"{max(r['fComputed'] for r in comparison) * 100:.1f} %, about {ratios_lo:g}-{ratios_hi:g}x the "
            "measurement (high in every case). D96's own check on its Fe-diluted overlay: Eq. 5 with C_0 2.07, k 0.46 "
            f"and C_e 18.9 gives 1.7 vol% (this module: {check * 100:.2f} %) against 1.3-2.2 vol% measured."),
        "sourceComparison": {"c88": comparison,
                             "c88Locator": ("C88 Table I (composition), Table VIII (k), Section III-B (measured "
                                            "fractions, constituents not separated), Tables IV and IX (phases)")},
        "sourceReproduction": {"C0_wt": D96_CHECK["C0_wt"], "k": D96_CHECK["k"], "Ce_wt": D96_CHECK["Ce_wt"],
                               "fComputed": _r(check), "paperValue": D96_CHECK["paperValue"],
                               "measuredRange": list(D96_CHECK["measuredRange"]),
                               "locator": "D96 Section IV-C text after Eq. 5; Section III-A (1.3-2.2 vol%)"},
        "binaryBoundNote": ("Binary gamma-Nb Scheil only. Carbon ties Nb up as NbC (C88 alloy 6: NbC only at 0.038 "
                            "wt% C) and would lower the gamma/Laves estimate; no carbon model is applied because "
                            "neither source gives carbon constants for alloy 625."),
        "notModelled": ["carbon (gamma/NbC): no alloy 625 constants", "silicon (promotes Laves and M6C, C88)",
                        "solid-state back-diffusion of Nb", "solute trapping in the equilibrium-k upper bound (screening k(V) is given separately in rapidSolidification)",
                        "dendrite-tip undercooling", "dependence of k_Nb and C_e on Fe, Mo and Si",
                        "mechanical consequences of Laves"],
        "validity": _in625_validity(),
        "rapidSolidification": _rapid_solidification("in625", microstructure),
        "lpbfObservations": lpbf_observations("in625"),
    }


# ---------------------------------------------------------------------------------------------------------------
# Rapid solidification (screening): velocity-dependent partition coefficient. Reported in a separate sub-block; the
# equilibrium-k upper bound above is never changed by it.

RAPID_MODEL_ID = "aziz-continuous-growth-k-of-v-scheil-screening-v1"
RAPID_EVIDENCE_LABEL = (
    "Literature estimate (screening): Aziz continuous-growth k(V) with V_D 0.23-0.31 m/s, a range Ghosh et al. 2017 "
    "fitted to binary Ni-Nb phase-field results (not measured), applied to this module's equilibrium k_Nb at the build "
    "job's screening R; extrapolates weld-calibrated Scheil formulas; not a prediction of LPBF segregation"
)
AZIZ_EQUATION = "k(V) = (k_e + V/V_D) / (1 + V/V_D)"
V_D_VALUES = (
    _c(0.23, "m/s", "G17", "G17 Section 3.2.4: Eq. 12 fitted to the 1D planar-front phase-field results (k_v = c0/c_max, "
                           "Fig. 13); G18 uses the same 0.23 m/s for IN625 (text with Fig. 4)"),
    _c(0.31, "m/s", "G17", "G17 Section 3.2.4 and Fig. 12: Eq. 12 fitted to the 2D steady-state cell-tip values "
                           "k_v = cs*/c_max"),
)
V_D_NATURE_NOTE = (
    "Modelling range, not a measurement. G17 fitted the Aziz function to the partitioning of its own phase-field model, "
    "in which the anti-trapping current does not remove trapping at these velocities (Section 3.2.4 and Summary), and "
    "states that no experimental V_D for Ni-Nb is available. K17 (lines 385-391) likewise says the diffuse interface "
    "artificially magnifies trapping at LPBF speeds. Both fits use k_e = 0.48 (binary Ni-Nb, G17 Table 2)."
)
RAPID_EXTRAPOLATION_NOTE = (
    "Extrapolation: the eutectic-fraction formulas (D96 Eq. 5; D97/D98 pseudo-ternary) were calibrated on GTA welds "
    "and DTA samples with the equilibrium k. Here k_Nb is replaced by k(R) and held constant over the whole "
    "solidification at the single build-job R, so the numbers show the direction and rough size of the trapping effect, "
    "not a validated LPBF fraction."
)
RAPID_K_TRANSFER_NOTE = (
    "V_D was fitted with k_e = 0.48 (G17, G18); this module applies it with its own equilibrium k_Nb (D98 0.45 for "
    "IN718, C88 0.51 for IN625). No source gives V_D for these k_e or for multicomponent IN718/IN625."
)
RAPID_NOT_MODELLED = [
    "velocity-dependent liquidus slope (G17 Eq. 14) and dendrite-tip undercooling / tip composition (G17 Eqs. 9-10, 15)",
    "curvature correction of k (G17 Eq. 13)",
    "trapping of carbon: k_C stays at its equilibrium value (no source V_D for C)",
    "variation of R along the melt-pool boundary (one mean R from the build job; G17 Section 3.1: 0.01-0.3 m/s, "
    "K17 lines 243-246: 0.01-0.17 m/s)",
    "solid-state back-diffusion of Nb",
]
_RAPID_FS = FS_SEGREGATION_POINTS


def aziz_partition_coefficient(k_e: float, v_m_s: float, v_d_m_s: float) -> float:
    """Aziz continuous-growth k(V) = (k_e + V/V_D) / (1 + V/V_D) as written in G17 Eq. 12."""
    _check_k(k_e)
    _check_positive("v_d_m_s", v_d_m_s)
    if not (isinstance(v_m_s, (int, float)) and math.isfinite(v_m_s) and v_m_s >= 0.0):
        raise SegregationModelError("v_m_s must be a finite number >= 0")
    x = v_m_s / v_d_m_s
    return (k_e + x) / (1.0 + x)


def _with_k(cset: Mapping[str, Dict[str, Any]], k: float) -> Dict[str, Dict[str, Any]]:
    out = dict(cset)
    out["k_gamma_Nb"] = dict(cset["k_gamma_Nb"], value=k, locator="Aziz k(V) from the equilibrium value (G17 Eq. 12)")
    return out


def _v_d_view() -> Dict[str, Any]:
    vals = [float(v["value"]) for v in V_D_VALUES]
    return {"min": min(vals), "max": max(vals), "unit": "m/s",
            "values": [dict(v, sourceCitation=SOURCES[v["source"]]["citation"]) for v in V_D_VALUES],
            "nature": V_D_NATURE_NOTE}


def _rapid_base() -> Dict[str, Any]:
    return {
        "modelId": RAPID_MODEL_ID,
        "model": {"equation": AZIZ_EQUATION, "source": SOURCES["G17"]["citation"],
                  "locator": "G17 Eq. 12 (Section 3.2.4), after Aziz 1982 (G17 ref. 66, not read here)",
                  "originalCitation": SOURCES["A82"]["citation"]},
        "V_D_m_s": _v_d_view(),
        "replacesUpperBound": False,
        "extrapolationNote": RAPID_EXTRAPOLATION_NOTE,
        "kTransferNote": RAPID_K_TRANSFER_NOTE,
        "notModelled": list(RAPID_NOT_MODELLED),
    }


def _rapid_inputs(alloy_id: str):
    """(cset, band, c_max or None) of the equilibrium-k result for this alloy."""
    if alloy_id == "in625":
        band, _ = _in625_band()
        return CONSTANTS[IN625_SET], band, None
    band, c_max, _ = _spec_band(alloy_id)
    return CONSTANTS["ni-base"], band, c_max


def _rapid_point(nb: float, c_max: Optional[float], cset) -> Dict[str, Any]:
    k = _value(cset, "k_gamma_Nb")
    f_bin = scheil_eutectic_fraction(nb, _value(cset, "C_Nb_laves"), k)
    out: Dict[str, Any] = {"binary": {"C_wt": 0.0, "fGammaLavesConstituent": _r(f_bin)}}
    if c_max is not None:
        tern = pseudo_ternary_path(nb, c_max, cset)
        if tern["status"] == "computed":
            out["pseudoTernaryAtCmax"] = {"C_wt": c_max, "fGammaNbCConstituent": _r(tern["fGammaNbCConstituent"]),
                                          "fGammaLavesConstituent": _r(tern["fGammaLavesConstituent"]),
                                          "fEutecticTotal": _r(tern["fEutecticTotal"]),
                                          "terminatedBy": tern["terminatedBy"]}
        else:
            out["pseudoTernaryAtCmax"] = {"C_wt": c_max, "status": tern["status"], "reason": tern.get("reason")}
    return out


def _rapid_solidification(alloy_id: str, microstructure: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    base = _rapid_base()
    from quantity_envelope import container, input_record, reason, reason_text, unavailable
    quantities = microstructure.get("quantities", {}) if isinstance(microstructure, Mapping) else {}
    normal_speed = quantities.get("normalSpeed", {})
    status = normal_speed.get("status")
    r = normal_speed.get("value")
    if status not in ("computed", "partial") or not (isinstance(r, (int, float)) and not isinstance(r, bool)
                                                    and math.isfinite(r) and r > 0):
        return {**base, "status": "unavailable", "reason": reason_text("parent-unavailable"), "R_m_s": None,
                **container({"fraction": unavailable("laves-trapped-scheil-fraction", [reason("parent-unavailable")],
                            depends_on=("interfaceSample",))}, input_provenance={"interfaceSample":
                            input_record("declaredAssumption", "request:interface-sample",
                            status="outOfRange", declaration_locator="python/lpbf_solidification_segregation.py#_rapid_solidification",
                            scope="missing-admitted-normal-speed")})}
    cset, band, c_max = _rapid_inputs(alloy_id)
    k_e = _value(cset, "k_gamma_Nb")
    by_vd = []
    try:
        for v_d in sorted(float(v["value"]) for v in V_D_VALUES):
            k_eff = aziz_partition_coefficient(k_e, float(r), v_d)
            mod = _with_k(cset, k_eff)
            seg_rows = _segregation_ratios(band["nominal"], mod)
            by_vd.append({
                "V_D_m_s": v_d, "kEff": _r(k_eff),
                "band": [{"label": lbl, "Nb_wt": band[lbl], **_rapid_point(band[lbl], c_max, mod)}
                         for lbl in ("min", "nominal", "max")],
                "segregation": {"Nb_wt": band["nominal"], "coreRatioToNominal": seg_rows["coreRatioToNominal"],
                                "coreNb_wt": seg_rows["coreNb_wt"], "interdendritic": seg_rows["interdendritic"]},
            })
    except SegregationModelError as exc:
        return {"status": "unavailable", "reason": f"k(V) estimate not computable: {exc}", "R_m_s": r, **base}
    k_vals = [row["kEff"] for row in by_vd]
    nominal_f = [next(p for p in row["band"] if p["label"] == "nominal")["binary"]["fGammaLavesConstituent"]
                 for row in by_vd]
    result = {
        "status": status,
        "reason": None,
        "R_m_s": r,
        "R_source": "build job microstructure block (screening-field mean R, copied)",
        "k_e": k_e,
        "kEff": {"min": min(k_vals), "max": max(k_vals)},
        "nominalBinaryFGammaLaves": {"min": min(nominal_f), "max": max(nominal_f)},
        "byVD": by_vd,
        "bandNote": ("same formulas and band as the equilibrium-k result with k_Nb replaced by k(R) at each end of the "
                     "V_D range; the lower V_D gives the higher k(R) and the smaller fraction"),
        **base,
    }
    from quantity_envelope import input_record, quantity, source_ref
    inputs = copy.deepcopy(microstructure.get("inputProvenance") or {})
    inputs["sourceCoefficients"] = input_record("sourceDefault", "segregation:rapid-source-constants", status="inRange",
                                                source_locator="python/lpbf_solidification_segregation.py#V_D_VALUES",
                                                scope="source-alloy-process")
    qs = {"normalSpeed": copy.deepcopy(normal_speed)}
    qs["fraction"] = quantity("laves-trapped-scheil-fraction", max(nominal_f), inputs=inputs,
                              depends_on=("normalSpeed", "sourceCoefficients"), quantities=qs,
                              sources=[source_ref("G17", "Eq. 12; V_D_VALUES source locators", "primary-read")],
                              model_identity=RAPID_MODEL_ID, fraction_basis="microconstituent",
                              uncertainty={"kind": "not-quantified", "construction": "not-quantified"})
    result.update(container(qs, input_provenance=inputs))
    return result



# As-built LPBF IN625 observations (NIST builds: EOS M270, 195 W, 800 mm/s). Measured values are copied with their
# locators; nothing in the model is tuned to them.
LPBF_IN625_BUILD = {
    "machine": "EOS M270", "power_W": 195, "scanSpeed_mm_s": 800, "layer_um": 20, "hatch_um": 100,
    "locator": "L17 Section II; Z18 Materials and Methods (Manufacturing of Materials); K17 lines 154-162",
}
LPBF_IN625_POWDER_NB = {"value": 3.75, "unit": "wt%",
                        "locator": "Z18 Table 1; L17 Table I; K17 Table 1 (ICP; the XRF column gives 3.06)"}
LPBF_IN625_VELOCITY = (
    {"source": "K17", "min": 0.01, "max": 0.17, "unit": "m/s",
     "basis": "FEA of this build, melt-pool bottom to trailing edge", "locator": "K17 lines 243-246 and 323-325"},
    {"source": "Z18", "min": 0.001, "max": 0.03, "unit": "m/s",
     "basis": "quoted from an FEA of a binary Ni-Nb model alloy with the same build parameters",
     "locator": "Z18 Materials and Methods (Manufacturing of Materials)"},
)
Z18_EDS_NB = {"min": 2.81, "max": 5.84}
LPBF_IN625_OBSERVATIONS = (
    {"source": "Z18", "kind": "measured", "quantity": "Nb mass fraction along an as-built EDS line scan",
     "Nb_wt": dict(Z18_EDS_NB), "Mo_wt": {"min": 9.35, "max": 10.85},
     "probe": ("2 um step and beam size, 300 s dwell, about 200 um long; Z18 states the values are averages over the "
               "probed volume. Cells are about 1 um apart (L17), so the scan smooths the cell-scale profile: its "
               "minimum overstates the cell-core Nb and its maximum understates the interdendritic peak."),
     "locator": "Z18 Results, 'As-built AM IN625', Figs. 3 and 4"},
    {"source": "Z18", "kind": "measured", "quantity": "phases in as-built material (synchrotron XRD)",
     "result": ("FCC only, fitted as two FCC lattices (3.6009 and 3.6196 Angstrom, attributed to strain and "
                "composition gradients); no secondary phase reported; detection limit not stated"),
     "locator": "Z18 Fig. 2(a) and Table 2"},
    {"source": "L17", "kind": "measured", "quantity": "phases and segregation in as-built material",
     "result": ("laboratory XRD shows only FCC peaks; EDS maps show Nb and Mo enriched between dendrites "
                "(qualitative, no numbers); primary spacing about 1 um, secondary about 300 nm"),
     "locator": "L17 Section III-A, Figs. 2 and 3"},
    {"source": "K17", "kind": "measured", "quantity": "precipitates in as-built material (STEM, synchrotron XRD)",
     "result": ("50-200 nm precipitates near cell/dendrite boundaries that could not be indexed in the as-built state; "
                "XRD of the as-built sample identifies only FCC"),
     "locator": "K17 lines 172-178 (Fig. 3) and 187-188 (Fig. 4)"},
)
LPBF_IN625_SIMULATIONS = (
    {"source": "K17", "kind": "simulation (binary Ni-4Nb phase-field, not measured)",
     "result": ("at V_s = 25 mm/s: cell centreline 3.0 wt% Nb, intercellular liquid midpoint 9.4 wt%, pinched-off "
                "droplets 16 wt%, below the 22.5 wt% eutectic; binary Scheil with k = 0.48 gives 1.9 wt% at the core "
                "and 21 wt% at 1 % liquid"),
     "caveat": "K17 lines 385-391: the diffuse interface artificially lowers the simulated segregation at these speeds",
     "locator": "K17 lines 283-291 (Fig. 9)"},
    {"source": "K17", "kind": "simulation (Scheil-Gulliver with TCNI8, multicomponent)",
     "result": "last liquid at 1250 K holds up to about 29 wt% Nb and 20 wt% Mo",
     "locator": "K17 lines 255-258 (Fig. 7b); quoted again in Z18 Results"},
    {"source": "G18", "kind": "simulation (binary Ni-4Nb phase-field, IN625 single tracks, no anti-trapping flux)",
     "result": "partition coefficient between 0.58 and 0.72 depending on R",
     "locator": "G18 text with Fig. 4"},
)
LPBF_COMPARISON_NOTE = (
    "Non-discriminating. The only quantitative as-built Nb data (Z18 EDS, 2 um probe) average over cells about 1 um "
    "wide, so they bound the cell-scale profile only loosely: both the equilibrium k (0.51) and the k(V) range give a "
    "core ratio below the lowest measured ratio, as they must if the probe averages, and neither can be confirmed or "
    "ruled out by it. No as-built study reports a Laves or NbC fraction: XRD shows FCC only (Z18, L17, K17) without a "
    "stated detection limit, and K17 sees unindexed 50-200 nm precipitates at cell boundaries. The computed terminal "
    "fractions (a few vol% at equilibrium k, less with k(V)) are therefore not tested by these observations."
)


def _in625_lpbf_comparison() -> Dict[str, Any]:
    cset = CONSTANTS[IN625_SET]
    k_e = _value(cset, "k_gamma_Nb")
    ce = _value(cset, "C_Nb_laves")
    c0 = LPBF_IN625_POWDER_NB["value"]
    v_lo = min(v["min"] for v in LPBF_IN625_VELOCITY)
    v_hi = max(v["max"] for v in LPBF_IN625_VELOCITY)
    vd = [float(v["value"]) for v in V_D_VALUES]
    k_min = aziz_partition_coefficient(k_e, v_lo, max(vd))
    k_max = aziz_partition_coefficient(k_e, v_hi, min(vd))
    meas_core = Z18_EDS_NB["min"] / c0
    meas_peak = Z18_EDS_NB["max"] / c0
    return {
        "Nb_wt": c0, "NbBasis": "powder Nb of the observed builds (Z18 Table 1)",
        "velocityRange_m_s": {"min": v_lo, "max": v_hi, "note": "union of the K17 and Z18 ranges"},
        "equilibriumK": {"k": k_e, "coreRatioToNominal": _r(k_e, 3),
                         "fGammaLavesConstituent": _r(scheil_eutectic_fraction(c0, ce, k_e))},
        "kOfV": {"kEff": {"min": _r(k_min), "max": _r(k_max)},
                 "coreRatioToNominal": {"min": _r(k_min, 3), "max": _r(k_max, 3)},
                 "fGammaLavesConstituent": {"min": _r(scheil_eutectic_fraction(c0, ce, k_max)),
                                            "max": _r(scheil_eutectic_fraction(c0, ce, k_min))}},
        "measured": {"lowestRatioToNominal": _r(meas_core, 3), "highestRatioToNominal": _r(meas_peak, 3),
                     "note": "Z18 EDS extremes over the powder Nb; 2 um probe averages (see observations)"},
        "coreBelowLowestMeasured": {"equilibriumK": k_e <= meas_core, "kOfVMax": k_max <= meas_core},
        "discriminating": False,
        "note": LPBF_COMPARISON_NOTE,
    }


def lpbf_observations(alloy_id: str) -> Dict[str, Any]:
    """As-built LPBF observations from the read sources, with a non-tuned comparison to this module's numbers."""
    if alloy_id != "in625":
        return {"status": "unavailable",
                "reason": ("no as-built LPBF IN718 segregation measurement among the sources read: Z18, L17 and K17 "
                           "are LPBF IN625, G17 is a binary Ni-Nb simulation"),
                "observations": []}
    return {
        "status": "computed",
        "alloy": "IN625",

        "sources": {key: SOURCES[key]["citation"] for key in ("Z18", "L17", "K17", "G18")},
        "build": dict(LPBF_IN625_BUILD),
        "powderNb_wt": dict(LPBF_IN625_POWDER_NB),
        "solidificationVelocity": [dict(v) for v in LPBF_IN625_VELOCITY],
        "observations": [copy.deepcopy(o) for o in LPBF_IN625_OBSERVATIONS],
        "literatureSimulations": [dict(s) for s in LPBF_IN625_SIMULATIONS],
        "comparison": _in625_lpbf_comparison(),
    }


def segregation_estimate(alloy_id: str, microstructure: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    return _segregation_envelope(_segregation_estimate(alloy_id, microstructure))


def build_job_segregation(alloy_id: str, microstructure: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    """Build-job entry point: composition-only estimate, G/R copied from the microstructure block, and the R-dependent
    k(V) screening sub-block (rapidSolidification)."""
    return segregation_estimate(alloy_id, microstructure)


if __name__ == "__main__":  # pragma: no cover - manual inspection
    import json
    print(json.dumps(segregation_estimate("in718", None), indent=1))


def binary_laves_inputs(alloy_id: str) -> Dict[str, float]:
    """Equilibrium k_Nb, C_e and nominal Nb of the binary C = 0 upper bound (read-only view of existing constants)."""
    if alloy_id == "in718":
        cset = CONSTANTS["ni-base"]
        nominal = _spec_band("in718")[0]["nominal"]
    elif alloy_id == "in625":
        cset = CONSTANTS[IN625_SET]
        nominal = _in625_band()[0]["nominal"]
    else:
        raise SegregationModelError(f"no binary Laves inputs for alloy '{alloy_id}'")
    return {"k_e": _value(cset, "k_gamma_Nb"), "C_e_wt": _value(cset, "C_Nb_laves"), "Nb_nominal_wt": float(nominal)}
