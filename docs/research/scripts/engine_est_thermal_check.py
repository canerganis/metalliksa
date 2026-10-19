"""Bounded source replay and independent checks for engine estimate groups 1/10.

Run: python -I -B docs/research/scripts/engine_est_thermal_check.py --check
Stdlib only. No served imports, measurements, numerical bands or external data.
Local PDFs are prerequisites, not skipped tests; see engine_est_thermal_flow.md.
"""
from __future__ import annotations

import argparse
import cmath
import hashlib
import math
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[3]
RG = 8.31446261815324
P0 = 101325.0
BETA = 0.2
FABBRO_CONDUCTION = 2.3
TI = dict(Tv=3560.0, Lv=9.255e6, M=0.048)
# Deliberately rounded 27 g/mol matches the independent Gan Al model-species
# convention. It is not represented as the CIAAW atomic weight or an alloy mass.
AL_PROXY = dict(Tv=2743.0, Lv=284000.0 / 0.027, M=0.027)
SOURCES = {
    "engine_est_gan2021_SI.pdf": "22a8d2dc870bbd83f6bd3330899437911733f9335d52758d95a328bd6993d6e5",
    "engine_est_fabbro2020.pdf": "9e7c396b9e4a32f56aad26571a062e50434a889c86a65815551d69e5306ddf1e",
    "engine_est_mondal2023.pdf": "ba9382cea6aec334dafc3f6a9c8350a9b5cca693d980fbe237b2bb704e98d1ce",
    "engine_est_gan2019_in625.pdf": "91dfb844d59ea50f44ade37dc8c44caecfb343b6ccc07fb8d665712b27c5604d",
}


def close(a, b, rtol=1e-9, atol=1e-12):
    assert math.isfinite(a) and math.isfinite(b)
    assert abs(a - b) <= max(atol, rtol * max(abs(a), abs(b))), (a, b)


def source_text(filename, first, last=None, mode="-layout"):
    path = ROOT / "papers" / filename
    assert path.is_file(), f"Restore local source prerequisite: {path}"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == SOURCES[filename], filename
    executable = shutil.which("pdftotext")
    assert executable, "pdftotext is required for independent source transcription checks"
    args = [executable, "-f", str(first), "-l", str(last or first), mode, "-enc", "UTF-8", str(path), "-"]
    return subprocess.run(args, capture_output=True, check=True).stdout.decode("utf-8", errors="replace")


def vaporization_latents(raw_text):
    """Read all three columns from the named Gan row, retaining PDF superscripts.

    Poppler layout puts some exponents on the preceding line. Its raw mode keeps
    them adjacent to their base; use only this bounded row, never nearby fusion
    values. Hash verification still happens before either extraction.
    """
    section = re.search(r"Latent heat of vaporization(.*?)Minimal absorptivity", raw_text, re.S)
    assert section is not None, "Missing vaporization row boundaries"
    values = re.findall(r"(\d+\.\d+)×10\s*(\d+)\b", section[1])
    assert len(values) == 3, "Expected three vaporization columns with exponents"
    return [float(mantissa) * 10 ** int(exponent) for mantissa, exponent in values]


def source_checks():
    text = "\n".join(line.strip() for line in source_text("engine_est_gan2021_SI.pdf", 20).splitlines())
    # Parse physical source rows rather than comparing a hand-entered JSON echo.
    row = next(x for x in text.splitlines() if x.startswith("Vaporization point"))
    numbers = [float(x) for x in re.findall(r"\b\d+(?:\.\d+)?\b", row)]
    assert len(numbers) == 3, row
    close(TI["Tv"], numbers[0])
    massrow = next(x for x in text.splitlines() if x.startswith("Molar mass"))
    masses = [float(x) for x in re.findall(r"\b\d+(?:\.\d+)?\b", massrow)]
    close(TI["M"], masses[0] / 1000)
    close(AL_PROXY["M"], masses[1] / 1000)
    latent_values = vaporization_latents(source_text("engine_est_gan2021_SI.pdf", 20, mode="-raw"))
    close(TI["Lv"], latent_values[0])
    ti_other = ["4420", "3920", "0.1734T+452.72", "830", "0.0136T+1.3097", "33.4", "1933", "2.86", "0.26"]
    assert all(token in text for token in ti_other)
    text = source_text("engine_est_mondal2023.pdf", 3, mode="-raw")
    row = next(x for x in text.splitlines() if re.match(r"Al\s+\d", x))
    _, boiling, latent = row.split()
    close(AL_PROXY["Tv"], float(boiling))
    close(AL_PROXY["Lv"] * AL_PROXY["M"], float(latent) * 1000)
    text = source_text("engine_est_fabbro2020.pdf", 18, 20, mode="-raw")
    # Unit/role/location assertions accompany the raw hash. Full equations were
    # checked on rendered source pages 18/19; PDF math extraction loses symbols.
    assert "Appendix A. Generalized Piston Model" in text
    assert all(f"(A{i})" in text for i in range(1, 13))
    assert "3.6 and 5" in text and "steel" in text
    beta_match = re.search(r"([0-9]+\.[0-9]+)\s+will be used", text)
    assert beta_match
    close(BETA, float(beta_match.group(1)))
    conduction_match = re.search(r"front half-cylinder also show.*?([0-9]+\.[0-9]+)\.\s*\(In fact", text, re.S)
    assert conduction_match
    close(FABBRO_CONDUCTION, float(conduction_match.group(1)))
    assert "18 of 22" in text and "20 of 22" in text
    text = source_text("engine_est_gan2019_in625.pdf", 7)
    for label, expected in (("Solid density", 8440), ("Liquid density", 7640),
                            ("Solidus temperature", 1563), ("Liquidus temperature", 1623),
                            ("Boiling temperature", 3000), ("Liquid specific heat capacity", 709.25),
                            ("Liquid thermal conductivity", 30.078), ("Latent heat of fusion", 290)):
        row = next(x for x in text.splitlines() if x.startswith(label))
        # Require the actual source value in its named property row and column.
        cells = re.split(r"\s{2,}", row.strip())
        close(float(cells[2]), expected)
    assert "0.2441T+338.39" in text and "0.0163T + 4.5847" in text
    assert text.count("Calibrated") >= 2
    return 4


def saturation(t, vapor):
    if not math.isfinite(t) or t <= 0:
        raise ValueError("A finite positive surface temperature is required")
    if not all(math.isfinite(vapor[k]) and vapor[k] > 0 for k in ("Tv", "Lv", "M")):
        raise ValueError("Supply positive vapour temperature, latent heat and molar mass")
    return P0 * math.exp(vapor["Lv"] * vapor["M"] / RG * (1 / vapor["Tv"] - 1 / t))


def evaporation(t, vapor, beta=BETA):
    if not 0 <= beta <= 1:
        raise ValueError("Invalid return fraction")
    return (1 - beta) * saturation(t, vapor) * math.sqrt(vapor["M"] / (2 * math.pi * RG * t))


def recoil(t, vapor, beta=BETA):
    return 0.5 * (1 + beta) * saturation(t, vapor)


def fresnel_absorptance(cos_incidence, index=complex(3.6, 5)):
    if not 0 < cos_incidence <= 1:
        raise ValueError("A front-facing incidence angle is required")
    root = cmath.sqrt(index * index - (1 - cos_incidence * cos_incidence))
    rs = (cos_incidence - root) / (cos_incidence + root)
    rp = (index * index * cos_incidence - root) / (index * index * cos_incidence + root)
    return 1 - (abs(rs) ** 2 + abs(rp) ** 2) / 2


def conical_state(t, v=0.8, d=80e-6):
    """Fabbro A1-A12 candidate using an explicitly declared Gan-Ti tuple.

    A source-model consistency fixture, not a process recommendation or serving.
    The optical tuple is the source steel proxy, thus this route is Tier 2.
    """
    t0, tm = 293.15, 1933.0
    rhos, rhol, cpl, kl, lm = 4420.0, 3920.0, 830.0, 33.4, 2.86e5
    cps = 0.1734 * (tm + t0) / 2 + 452.72
    ks = 0.0136 * (tm + t0) / 2 + 1.3097
    al, ass = kl / (rhol * cpl), ks / (rhos * cps)
    pr, j = recoil(t, TI), evaporation(t, TI)
    if pr <= P0 or t <= tm or min(v, d) <= 0:
        raise ValueError("No evaporatively driven conical branch")
    um = math.sqrt(2 * (pr - P0) / rhol)
    y = math.log1p(rhol * cpl * (t - tm) / (rhos * (cps * (tm - t0) + lm)))
    # Derived by dividing A2 by e and multiplying by cos(theta), using A1.
    c = ((rhol * um / v - rhos) * al * y + j * (1.5 * math.pi / 4) * d) / (0.5 * rhos * v * d)
    if not 0 < c < 1:
        raise ValueError("No admissible inclined half-cone")
    sintheta = math.sqrt(1 - c * c)
    e = d * c / sintheta
    delta = al * y / (v * c)
    sv = (1.5 * math.pi / 4) * d * d / sintheta
    outgoing_liquid = rhol * um * delta * e
    outgoing_vapor = j * sv
    incoming = 0.5 * rhos * v * (d + 2 * delta) * e
    hm = cps * (tm - t0) + lm + cpl * (t - tm) / 2
    hv = cps * (tm - t0) + lm + cpl * (t - tm) + TI["Lv"]
    pm, pv = outgoing_liquid * hm, outgoing_vapor * hv
    pc = ks * (tm - t0) * (0.5 * FABBRO_CONDUCTION * (v * d / (2 * ass)) * (1 + 2 * delta / d) + FABBRO_CONDUCTION) * e
    pk = outgoing_liquid * um * um / 2
    af = fresnel_absorptance(sintheta)
    return dict(t=t, depth=e, theta=math.acos(c), delta=delta, surface_area=sv,
                incoming=incoming, liquid=outgoing_liquid, vapor=outgoing_vapor,
                recoil=pr, speed=um, pm=pm, pv=pv, pc=pc, pk=pk,
                power=(pm + pv + pc + pk) / af, af=af)


def simpson(f, a, b, n=2000):
    dx = (b - a) / n
    return dx / 3 * (f(a) + f(b) + sum((4 if i % 2 else 2) * f(a + i * dx) for i in range(1, n)))


def numerical_checks():
    # Independent integral identity for the proposed IN625 solid polynomial.
    # This catches a Celsius-for-Kelvin substitution and missing linear term.
    lo, hi = 293.15, 1563.0
    cp_int = simpson(lambda t: 0.2441 * t + 338.39, lo, hi)
    cp_exact = (hi - lo) * (0.2441 * (hi + lo) / 2 + 338.39)
    close(cp_int, cp_exact)
    assert cp_int > (hi - lo) * 338.39
    k_int = simpson(lambda t: 0.0163 * t + 4.5847, lo, hi)
    close(k_int, (hi - lo) * (0.0163 * (hi + lo) / 2 + 4.5847))
    assert all(0.2441 * t + 338.39 > 0 and 0.0163 * t + 4.5847 > 0 for t in (lo, hi))
    for vapor in (TI, AL_PROXY):
        for t in (0.8 * vapor["Tv"], vapor["Tv"], 1.08 * vapor["Tv"]):
            # Independent ODE integral of d(ln p)/dT=H/(R T^2).
            integral = simpson(lambda u: vapor["Lv"] * vapor["M"] / (RG * u * u), vapor["Tv"], t)
            close(saturation(t, vapor), P0 * math.exp(integral), 2e-10)
            # Independent positive-velocity Maxwellian number/mass flux integral.
            # x is normal velocity divided by sqrt(R T/M).
            integral = simpson(lambda x: x * math.exp(-x * x / 2) / math.sqrt(2 * math.pi), 0, 10)
            density = saturation(t, vapor) * vapor["M"] / (RG * t)
            oracle = (1 - BETA) * density * math.sqrt(RG * t / vapor["M"]) * integral
            close(evaporation(t, vapor), oracle, 1e-9)
            assert evaporation(t, vapor, beta=1) == 0
        b = vapor["Lv"] * vapor["M"] / RG
        threshold = 1 / (1 / vapor["Tv"] - math.log(2 / (1 + BETA)) / b)
        close(recoil(threshold, vapor), P0)
        assert threshold > vapor["Tv"]
    states = []
    for t in range(3561, 4300):
        try:
            s = conical_state(float(t))
        except ValueError:
            continue
        close(s["incoming"], s["liquid"] + s["vapor"], 2e-12)
        # Definition/smoke checks ONLY: power and pv were constructed above
        # from these same terms. They are not independent energy verification.
        close(s["af"] * s["power"], s["pm"] + s["pv"] + s["pc"] + s["pk"])
        latent_only = s["vapor"] * TI["Lv"]
        assert s["pv"] > latent_only
        assert abs(s["pv"] - latent_only) > 0.05 * s["pv"]
        states.append(s)
    assert len(states) > 5, "No usable conical candidate branch was formed"
    # Independent normal-incidence optical identity for a complex index.
    n, k = 3.6, 5.0
    close(fresnel_absorptance(1), 4 * n / ((n + 1) ** 2 + k * k))
    # No black-box fit or source experimental result is used in these checks.
    # Evaporating moving control volume: E_new=E_old+Qdt-j A(h_l+Lv)dt.
    mass, enthalpy, j, area, dt, power, lv = 1e-6, 2e6, 2.0, 1e-8, 1e-6, 1.0, TI["Lv"]
    dm = j * area * dt
    mnew = mass - dm
    enew = mass * enthalpy + power * dt - dm * (enthalpy + lv)
    # Algebraic ledger smoke check, not a numerical moving-boundary solve.
    close((enew / mnew - enthalpy) * mnew, power * dt - dm * lv)
    assert enew < mass * enthalpy + power * dt
    for bad in (0.0, -1.0, float("nan"), float("inf")):
        try:
            saturation(bad, TI)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid temperature accepted")
    return len(states)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", required=True)
    parser.parse_args()
    files = source_checks()
    states = numerical_checks()
    print(f"PASS: {files} page-bounded source/hash replays; CC ODE and Maxwellian quadrature; {states} conical mass-balance checks; independent normal-incidence optical identity; invalid inputs")
    print("SMOKE ONLY: conical power/enthalpy by construction and receding ledger algebra. No independent energy solver, served calculation or experimental validation.")


if __name__ == "__main__":
    main()
