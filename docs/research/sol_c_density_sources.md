# SOL-C nominal ambient-density conventions

Prepared 2026-10-16. This closes the **located-source gap**, not the high-temperature physical-density gap, identified in the read-only thermal-parent audit in [sol_c_phase_morphology.md](sol_c_phase_morphology.md). No served constant or source code is changed. Equality to a manufacturer value does not prove the historical ancestry of the original served literal.

## Admission and limits

For the nominal, constant-property conduction-field **model convention only**, retain the four existing densities below. Their primary manufacturer documents explicitly print the same metric density. Source kind is `modelConvention`, per-input source label `Literature estimate`; none is `Measured` for the user specimen or for the model liquidus. These are manufacturer property declarations/compilations, **not newly authenticated primary measurements**. No exact user composition, porosity, powder-packing fraction, thermal-expansion correction or molten-state density is implied. The actual source batch and density measurement method are not declared in these rows.

| Canonical alloy | Retained density, kg/m3 | Manufacturer source and locator | Physical scope and refusal |
|---|---:|---|---|
| `ti6al4v` | 4430 | TIMET, *TIMETAL 6-4 Properties*, **PDF6/printed2, Density paragraph**: 4.43 gm/cc; PDF5/printed1 Introduction repeats it. [Manufacturer PDF](https://www.timet.com/assets/local/documents/technicalmanuals/TIMETAL_6-4_Properties.pdf). | Nominal TIMETAL6-4 wrought-product compilation, ambient reference interpretation; the paragraph does not specify a density measurement temperature. This preserves the literal used by both `_THERMAL` and the Kirchhoff ledger. No claim that it is solid/liquid density at the admitted endpoint. |
| `in718` | 8190 | ATI Allvac, *ATI 718 Alloy*, **NI-105 Version2 (2/25/2011), PDF1, PHYSICAL PROPERTIES, Density row**: 8.19 gm/cm3. [Manufacturer PDF](https://www.atimaterials.com/Products/Documents/datasheets/nickel-cobalt/nickel-based/ati_718_allvac_version_tds_en_v1.pdf). | Nominal manufacturer product property; row does not specify measurement temperature or method. Do not silently substitute an annealed-and-aged product density. SMC-045 Table2 supplies only imperial density; the direct metric ATI row avoids pretending its unit conversion is exact. |
| `ss316l` | 7990 | AK Steel, *316/316L Stainless Steel Data Sheet*, **316/316L-S-08-01-07, PDF2, PHYSICAL PROPERTIES, Density row**: 7.99 g/cm3; footer7100-0096,7/07. [Manufacturer-authored PDF preserved by SpaceMatDB](https://www.spacematdb.com/spacemat/manudatasheets/316_316L_Data_Sheet.pdf). | Manufacturer sheet/strip declaration covering316 and316L; no source-specific density temperature or method supplied. This does not remove the separate SS316-to-316L endpoint transfer, nor establish the as-built porous specimen's bulk density. Host is a mirror; authorship is the manufacturer PDF's own header/footer. |
| `in625` | 8440 | Special Metals, *INCONEL alloy625*, **Aug2013, PDF2/printed2, Table2 Physical Constants, Density gram/cc row**: 8.44. [Manufacturer PDF](https://www.specialmetals.com/documents/technical-bulletins/inconel/inconel-alloy-625.pdf). | Manufacturer typical physical constant; source says bulletin properties are typical and unsuitable for specification. No density measurement temperature or method supplied. This authenticates the ambient-density model convention, not its value at the source's solidus-property evaluation point. |

Conversion is exact dimensional arithmetic: `(g/cm3) * (10^-3 kg/g) / (10^-2 m/cm)^3 = (g/cm3) * 1000 kg/m3`. The manufacturer metric values are rounded declarations; decimal rendering is not their physical uncertainty. Do not convert rounded imperial numbers and then call the disagreement with the metric column a measurement error bar.

**Ti64 alternative must remain visible:** TIMET's shorter TMC-0150 ©2000 datasheet, **PDF1 Table2 Density row at22C**, prints **4.42 g/cm3**, whereas the full manufacturer properties manual prints4.43. [Alternative manufacturer PDF](https://www.timet.com/documents/datasheets/alpha-and-beta-alloys/timetal-6-4.pdf). Their difference is a documented source/rendering alternative, not a statistical confidence interval, exact composition correction, or proof that one is more accurate. Keep the current4430 numerical convention; a future full-field sensitivity may separately use the alternative with its own parent identity. No quiet retuning is authorized.

All four **physical uncertainties remain `not-quantified`**, including applying an ambient constant throughout a high-temperature field and the nominal-family transfer to an actual specimen. Do not borrow `FOUR_ALLOY_U95_BUDGET` values or invent a percentage. Numerical refinement and any enumerated source-alternative full-field band may be reported separately, explicitly conditional on these fixed constants; neither bounds the unquantified physical error. Refuse a claim of measured high-temperature density or a calibrated prediction interval. Arbitrary user chemistry/material state needs its own admission; a nominal-alloy row cannot authenticate it.

The new source route supersedes the density **locator missing** findings of the earlier repository-only audit. It does not change the still valid finding that the old `PROPERTY_PROVENANCE` records do not carry these locators. The architect/installation owner must transport the actual selected source, locator, constant-density assumption, transfer scope and identity to every dependent thermal quantity; a document alone does not modify the served evidence label. Green absorption, overrides and other field models retain independent parent gates.

## Reproducible source-to-code check

Run **`python -I docs/research/scripts/sol_c_density_check.py --check`**. Prerequisites are `pypdf` and the five lawfully downloaded local PDFs below. Missing sources/dependency/hash or extracted row mismatch fails; no online download or silent skip occurs. The checker reads only the identified pages, extracts the actual density cells, independently converts SI units, and compares against the current AST literals in `_THERMAL`, the Ti64 `PROPERTY_LEDGER` kernel density and `SECONDARY_THERMOPHYSICAL_DB`. It imports no served module, solver, bands tool or measured melt-pool data.

It also rejects twelve independent negative mismatches: for each alloy, a changed served density, changed extracted density and changed source-row metric cell. The alternative Ti64 PDF is hash/row checked and required to remain distinct. This proves transcription, source identity and code-value equality; it proves neither material accuracy, unknown temperature dependence nor field validation.

| Local-only PDF under `papers/` | SHA256 |
|---|---|
| `sol_c_timet_ti64_properties.pdf` | `f9bcc879445c07259d5388598bea8b69f667d9180269b40b12dce28b57a7c507` |
| `sol_c_ati718_bar.pdf` | `234b2bc76e5f92e8d98b75f9231949236234fcf35f7c168afaceec82ad2b5855` |
| `sol_c_aksteel316l.pdf` | `0b3d06f93a882e882822b18ef8aacff30ee6c3448d2ce56627a1332234f2f152` |
| `sol_c_smc625.pdf` | `f5379cccfe1fe760ebdc20e3f590e709e5acd1c0063d212d4ae5fd6568496d98` |
| `sol_c_timet_ti64_datasheet.pdf` | `824684f7d5603af19e0d0862e1af1289f4ea64ae7fac7f54e649ae0f80040822` |

These PDFs remain ignored and local-only. Their bytes are not committed; restoring matching lawful copies is required to rerun the source check on a fresh checkout. No redistribution licence is asserted.
