# SOL-C spacing source disposition (2026-10-16)

Scope: spacing only; no served changes, measured melt-pool rows, bands tool, forbidden named source content or `.orchestra/external-data` access. This note supplies the physics owner with bounded admissions; Amendment 5 controls the resulting contract.

## Decision by alloy and observable

| Alloy | PDAS | SDAS |
|---|---|---|
| Ti-6Al-4V | Unavailable: no verified LPBF-domain model; the verified EB-ingot law is outside process, cooling-rate and nominal-Al support. | Unavailable for the same reasons. |
| AlSi10Mg | Unavailable: the verified candidate abstract describes secondary, not primary, spacing. | Unavailable: promising exact-alloy FSC candidate, but full-text units/chemistry, rate definition and fit uncertainty could not be verified. Do not guess micrometres from customary practice. |
| IN718 | Conditional literature screening: existing binary Ni-Nb Hunt and Kurz-Fisher alternatives, only on their admitted fixed-G line with every mask and explicit alloy transfer. No guarantee a served sample qualifies. | Unavailable: no complete source-bound alloy-specific coefficient/domain/definition set verified. |
| IN625 | Same explicitly transferred binary-screen route as IN718; no generic Inconel alias. | Unavailable: no complete source-bound alloy-specific coefficient/domain/definition set verified. |
| 316L | Unavailable: a cellular-spacing relation does not automatically establish primary dendrite spacing or its uncertainty/domain. | Unavailable: no complete source-bound alloy-specific coefficient/domain/definition set verified. |

These are source-review dispositions, not an assertion that no other literature exists. For missing models use the existing `missing-source-bound-model`; for an otherwise admitted model with a failed sample/domain mask use `outside-source-model-domain`; missing numerical coefficients use `missing-source-constant`. Preserve named unresolved inputs and parent reasons.

## S-C1: verified Ni-Nb model constants and bounded transfer

[Ghosh et al. 2017](https://arxiv.org/pdf/1705.06669), DOI [10.1088/1361-651X/aa7369](https://doi.org/10.1088/1361-651X/aa7369), arXiv v2: **PDF8 Table 2; PDF9 fixed-G sentence; PDF12 Eq.7; PDF13 Eq.8; PDF14 Fig.6**. These archive locators differ from the previously reviewed journal-layout PDF12/printed11; do not conflate versions. Table 2 gives `ke=0.48`, `Gamma=3.65e-7 K m`, `DeltaT0=57 K`, `Dl=3e-9 m²/s`. The paper treats Ni-5 mass%Nb, with IN718 approximated by this binary alloy. Eq.7 uses `2.83*(ke*Gamma*DeltaT0*Dl)^0.25`; Eq.8 uses `4.3*(Gamma*DeltaT0*Dl/ke)^0.25`. Both multiply `G^-0.5*R^-0.25`. The Fig.6 Hunt caption conflicts with its equation; retain the SPEC A3.A2 reconciliation. Source model constants are not measured properties of the two full alloys.

Retain SPEC §5.2's exact masks: `G=1e7 K/m` (relative `1e-12` encoding tolerance only), `x=G^-0.5*R^-0.25` in `[4e-4,1.2e-3]`, `G*R` in `[5e4,3e6] K/s`, and `G*Dl/DeltaT0 < R < 0.98 m/s`. The cooling interval is stated on arXiv PDF12; its §3.2.1 PDF9 absolute-stability formula is `Vab=DeltaT0*Dl/(ke*Gamma)`. The Table2 inputs give `0.976027397260274 m/s`; SPEC's approximately `0.98` is its two-decimal evaluation, whereas this archive's PDF10 continuation prints a coarse `1 m/s`. Do not claim the archive literally prints `0.98`. Do not snap a computed G to that line. No off-line extrapolation is added here.

For a qualifying sample, compute each alternative before aggregation, in metres. Report both alternatives, never their midpoint as an independently selected model. For a positive joint parent enclosure, evaluate each law over the **joint supported set**, retaining G/R correlation and source masks; its extrema form that alternative's conditional input/numerical sensitivity band. If only a rectangle is known, monotonicity gives each model's minimum at `(G_hi,R_hi)` and maximum at `(G_lo,R_lo)`, but the entire rectangle must satisfy the source masks. A nonzero G uncertainty generally leaves the fixed line and therefore refuses default PDAS; do not truncate that uncertainty to manufacture support. A union of the two conditional bands is a model-alternative envelope, **not** a confidence or prediction interval. No source-bound numerical transfer-error or model-discrepancy bound is known; these remain explicitly unquantified. A degenerate numerical/input band must not be described as zero physical uncertainty.

Consistency note when eligible: “Binary Ni-Nb spacing screen transferred to [IN718/IN625]. Two model alternatives are shown. The band covers declared input/numerical variation; alloy-transfer and model error are unquantified.” When refused: “The available front samples do not stay within the spacing source's domain.” Report valid/refused count and spatial support, with the same sample weights used for the thermal summaries. No whole-front median substitution.

## S-C2: verified Ti alloy candidate, refused LPBF transfer

[Mizukami et al. 2020](https://www.jstage.jst.go.jp/article/isijinternational/60/11/60_ISIJINT-2020-089/_html/-char/en), DOI [10.2355/isijinternational.ISIJINT-2020-089](https://doi.org/10.2355/isijinternational.ISIJINT-2020-089), §§4.6–4.7 Eqs.4–5: `lambda1=(-62*CAl+699)*q^-0.39`, `lambda2=(-33*CAl+366)*q^-0.40`, spacing in µm, `CAl` in mass%, `q` in K/s. §4.3 defines q at liquidus passage. §2 concerns electron-beam-remelted ingots, rather than LPBF. Visually read Fig.11 groups are 2.9, 4.0, 4.3, 5.0 and 5.7 mass%Al; its cooling axis spans 1–100 K/s, with data approximately 2–45 K/s. Figure-axis bounds are not a verified rectangular model-validity domain. The paper supplies no regression-error interval in the inspected spacing discussion. Nominal 6 mass%Al and LPBF rates therefore require two unsupported extrapolations. No coefficients from these documentary candidates enter the served contract or executable numerical admission.

## S-C3: AlSi10Mg and 316L leads held, not coefficient admissions

[Takata et al. 2022 publisher abstract](https://www.sciencedirect.com/science/article/pii/S026412752200452X), DOI [10.1016/j.matdes.2022.110830](https://doi.org/10.1016/j.matdes.2022.110830), reports AlSi10Mg FSC and secondary α-Al dendrite spacing against imposed cooling rate. The abstract does not establish spacing units or coefficient uncertainty. Its stated fitted-rate range and the separately described faster sample must not be conflated. Full text returned HTTP403; Crossref's text-mining route returned HTTP429; an exact-title/institutional search yielded no accessible manuscript. No numerical coefficient is admitted or used here. Do not equate imposed FSC cooling with instantaneous front cooling without a declared source-bound surrogate.

[Pham et al. 2020, Fig.2e](https://www.nature.com/articles/s41467-020-14453-3) is a primary lead for 316L **cellular** spacing; publisher-indexed text distinguishes its fitted prefactor from other literature values and links this difference to thermal-field bias. Full source/domain/uncertainty verification was not completed here. No prefactor is admitted; no silent cellular-to-PDAS relabelling.

## Reproduction and local-only source archive

Run `python -I docs/research/scripts/sol_c_spacing_check.py --check` (requires `pypdf`). This reads the actual primary PDF Table 2 and Eqs.7–8, checks version/hash and fixed-G/range locators, verifies the documentary Ti HTML equations, extracts and executes only the actual production spacing functions/constants by AST, and checks the independent fourth-power identities `lambda^4*G²*R = p^4*Gamma*DeltaT0*Dl*(ke or 1/ke)`. No repository import or unrelated material-authority initializer is executed. Every runtime source parameter, source-line/range mask and the SPEC encoding tolerance is bound explicitly; cooling limits are parsed from source prose and the absolute-stability speed is independently derived from its equation. It covers both eligible alloy IDs, all three unsupported alloys, off-line/planar/absolute-stability/invalid refusals and an in-memory caption-coefficient mutation. It does not compare a generated ledger with itself. It neither admits served samples nor validates physical spacing. Missing source/dependency/hash fails, never silently skips.

Local downloads are not staged or distributed by this note. Restore lawful copies at these paths for replay:

| Local path | Retrieval URL | Raw SHA256 |
|---|---|---|
| `papers/ghosh2017_solc_spacing.pdf` | `https://arxiv.org/pdf/1705.06669` | `446c2a8e16af32377d070d81a5ccf71e6059a58f3b38481951ecafd36463a5dd` |
| `papers/mizukami2020_solc_spacing.html` | J-STAGE full-text URL above | `aa03cefa2f447d68b266bfec4f9787b53854d6590f9633d77d1c1eb0033fdd51` |
| `papers/mizukami2020_solc_fig11.jpg` | `https://www.jstage.jst.go.jp/article/isijinternational/60/11/60_ISIJINT-2020-089/_html/-char/Graphics/60_2455_11.jpg` | `d06719cce64aff7c1d5f723582428adff6f1836f8b04cf238051f56d4665ed2f` |
