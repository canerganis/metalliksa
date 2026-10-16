# SOL-T property-source archive

## Engine-estimate research additions, 2026-10-17

For [SPEC_engine_estimates_2026-10-17.md](../docs/research/SPEC_engine_estimates_2026-10-17.md). These source PDFs are local, ignored and never committed. Checkers fail when a required source is absent or its bytes differ. Only the bounded property/method locators were used; no measured melt-pool rows or forbidden measured-depth/width content was read. Equation checks do not establish experimental validity.

| Local PDF | Open primary source | SHA256 | Used locator |
|---|---|---|---|
| `engine_est_gan2021_SI.pdf` | [Gan2021 supplementary information](https://static-content.springer-cdn.com/esm/art%3A10.1038%2Fs41467-021-22704-0/MediaObjects/41467_2021_22704_MOESM1_ESM.pdf) | `22a8d2dc870bbd83f6bd3330899437911733f9335d52758d95a328bd6993d6e5` | PDF2-4 Methods1, PDF20 Table1 |
| `engine_est_fabbro2020.pdf` | [Fabbro2020](https://doi.org/10.3390/app10041487) | `9e7c396b9e4a32f56aad26571a062e50434a889c86a65815551d69e5306ddf1e` | Section3.1, PDF18-20 AppendixA |
| `engine_est_mondal2023.pdf` | [Mondal2023](https://doi.org/10.3390/ma16010050) | `ba9382cea6aec334dafc3f6a9c8350a9b5cca693d980fbe237b2bb704e98d1ce` | PDF3 Table1 pure-Al vapor constants |
| `engine_est_gan2019_in625.pdf` | [Gan2019 primary author full text](https://www.researchgate.net/publication/332389300_Benchmark_Study_of_Thermal_Behavior_Surface_Topography_and_Dendritic_Microstructure_in_Selective_Laser_Melting_of_Inconel_625), [DOI](https://doi.org/10.1007/s40192-019-00130-x) | `91dfb844d59ea50f44ade37dc8c44caecfb343b6ccc07fb8d665712b27c5604d` | PDF5-6 methods, PDF7 Table1 thermophysical functions |
| `engine_est_salsi2018.pdf` | [Salsi2018 author-hosted copy](https://www.scipedia.com/wd/images/1/1b/Draft_Samper_906462519_4543_metals-08-00633-v2.pdf), [publisher](https://doi.org/10.3390/met8080633) | `afd81903615318de59b3f0b853e88c1dde87eab075f9aab0624d0cedccebbc94` | PDF5/9 equations, PDF12 KM parameters, PDF14 Table3 dissolution |

The Salsi author copy has overlapping old/publisher text layers. The final Table3 layer was selected and visually checked; it differs in bytes from the previous A7 publisher PDF and is not passed off as that object. Inherited CET source objects and their exact locators/hashes remain in [sol_c_a7_source_audit.md](../docs/research/sol_c_a7_source_audit.md). Its six PDF/two XML-HTML prerequisites were restored from the existing local SOL-C worktree and replayed successfully. Durga/Gao original-PDF gaps remain explicit; Murakami equation evidence is normalized primary-web text rather than authenticated PDF bytes.

## Earlier SOL-T archive

Added 2026-10-16 for SPEC Amendment 4. Unchanged local-library copies except the separately recorded open downloads. Full PDFs are retained **locally, untracked and ignored**, for byte reproducibility; the check manifests restrict extraction to property/method/reference pages and coordinate crops. This is a subset of the shared workspace library in `../papers/INDEX.md`, not a replacement for that catalogue. No measured-pool validation is admitted.

| File | Source IDs | Raw SHA256 | Verification locator |
|---|---|---|---|
| [3dsystems_alsi10mg_revd.pdf](3dsystems_alsi10mg_revd.pdf) | SOLT-3DS-AL | `bbdb825f1427a30bafdda1974be98f81734930535997fd3209a0f6349edb8613` | source assertions in `docs/research/sol_t_*_checks.json` |
| [boivineau2006.pdf](boivineau2006.pdf) | SOLT-BOIVINEAU-TI | `9f3fc2c89798ea17020e02d762ca93e8432743a6f3c022814ec8d26b15f2e5d8` | source assertions in `docs/research/sol_t_*_checks.json` |
| [brandt2007.pdf](brandt2007.pdf) | SOLT-BRANDT-AL | `505f04de097d31d97ca92a35821233f198ac59aca8ff3ffc27c4ce9cb011d0f7` | source assertions in `docs/research/sol_t_*_checks.json` |
| [cezairliyan1977_ti64_thermophysical_pulse.pdf](cezairliyan1977_ti64_thermophysical_pulse.pdf) | SOLT-CEZAIRLIYAN-TI | `a699c83fd95b17d4425c6d8a73066bd96deb39a461dd1778e9292c501cfb5fa2` | source assertions in `docs/research/sol_t_*_checks.json` |
| [cieslak1990.pdf](cieslak1990.pdf) | CIES718 | `1e2d6337507f04ced317c5b3782a5ed490ff0ec807085411bf35117938f5f3ab` | source assertions in `docs/research/sol_t_*_checks.json` |
| [gan2019_in625_benchmark_thermal_fluid_vaporization.pdf](gan2019_in625_benchmark_thermal_fluid_vaporization.pdf) | GAN625-2019 | `91dfb844d59ea50f44ade37dc8c44caecfb343b6ccc07fb8d665712b27c5604d` | source assertions in `docs/research/sol_t_*_checks.json` |
| [gan2021_SI.pdf](gan2021_SI.pdf) | SOLT-GAN-TI, GAN316 | `22a8d2dc870bbd83f6bd3330899437911733f9335d52758d95a328bd6993d6e5` | source assertions in `docs/research/sol_t_*_checks.json` |
| [knapp2019_in718_ebpbf_solidification_manuscript.pdf](knapp2019_in718_ebpbf_solidification_manuscript.pdf) | KNAPP718 | `9439116db13fcca96f808d9ee49bebe6624992df74a4bb5ee5d8f13a4688284c` | source assertions in `docs/research/sol_t_*_checks.json` |
| [mills2002_a.pdf](mills2002_a.pdf) | MILLS316 | `1acda1c90a17df10b33fff9437a1b60bd728460b39b9bb558b57f99f9a265ad6` | source assertions in `docs/research/sol_t_*_checks.json` |
| [mills2002_b.pdf](mills2002_b.pdf) | MILLS718 | `c8386d2383a0d6260a8722396d638793646897447dcfe1ce2653318d11a23b59` | source assertions in `docs/research/sol_t_*_checks.json` |
| [pottlacher2002.pdf](pottlacher2002.pdf) | POT718 | `4a200f08e598a1457e1597a254e194fd2b37e63ee7f21b8e9af2829772a5422a` | source assertions in `docs/research/sol_t_*_checks.json` |
| [sabau2018_in625_jmatpro_properties.pdf](sabau2018_in625_jmatpro_properties.pdf) | ORNL2018-LINEAGE-ONLY | `2affc131f9e8be886beb85aff6ea615fcd6ef82e570522486efbc8e3cc6cb8e4` | IN625 lineage lead only, PDF23 section3.4; no endpoint transcription; bytes checked |
| [sabau2020_melt_properties_dnb.pdf](sabau2020_melt_properties_dnb.pdf) | MP04 | `726e52b0b58ee77bed424101d4111a0813b7bcce9de0225b346c0c2a065e7377` | source assertions in `docs/research/sol_t_*_checks.json` |
| [solidification_ferrandini2005_afa316l.pdf](solidification_ferrandini2005_afa316l.pdf) | ARES316 | `7225197d0d452afe377a723e582367a31ef721e3db8f9742b2369d2c430774cf` | source assertions in `docs/research/sol_t_*_checks.json` |
| [solidification_pichler2020_srm316l.pdf](solidification_pichler2020_srm316l.pdf) | PICH316 | `ae90ec5c55b1e4145ad8f70f3b77d3656ec6cbcc83c0684bc33e4cfef57266ff` | source assertions in `docs/research/sol_t_*_checks.json` |
| [specialmetals_inconel625_bulletin_2013.pdf](specialmetals_inconel625_bulletin_2013.pdf) | SMC625-2013 | `f5379cccfe1fe760ebdc20e3f590e709e5acd1c0063d212d4ae5fd6568496d98` | source assertions in `docs/research/sol_t_*_checks.json` |
| [specialmetals_inconel718_smc045.pdf](specialmetals_inconel718_smc045.pdf) | SMC718 | `6c9c60dc272cb4f7275091e02779879760afcb1801fc9bd04fbfca239907da90` | source assertions in `docs/research/sol_t_*_checks.json` |

## Local archive and redistribution boundary

Git distributes this index and hash/locator manifests only, not the17 PDF objects. Before `check_sol_t_sources.py --check`, restore lawful local copies under these paths matching the raw SHA256 values above; a missing archive is a hard prerequisite failure, never a skip. The other two source-AST checks do not need PDF bytes. No source checker downloads files.

Possible redistribution candidates for **maintainer review only**: `3dsystems_alsi10mg_revd.pdf` (public manufacturer data sheet) and `knapp2019_in718_ebpbf_solidification_manuscript.pdf` (OSTI1494899 author manuscript). Public access does not establish permission; the maintainer must check the applicable rights/terms. Neither candidate nor any publisher PDF is committed. All existing hashes remain unchanged.

## SOL-C local source archive (2026-10-16)

Source objects below are local-only downloads, not Git deliverables. Restore lawful matching copies for the two source checks; neither script downloads missing files. No source here supplies measured melt-pool depth/width. Exact URLs, version/page locators, physical scope and transcription limits are in [spacing sources](../docs/research/sol_c_spacing_sources.md) and [density sources](../docs/research/sol_c_density_sources.md). The HTML and figure also stay local-only; their presence does not imply redistribution permission.

| Local filename | Source / locator | Raw SHA256 |
|---|---|---|
| `ghosh2017_solc_spacing.pdf` | Ghosh2017 arXiv1705.06669v2; PDF8 Table2, PDF9 fixedG, PDF12 Eq7, PDF13 Eq8, PDF14 Fig6; spacing checker | `446c2a8e16af32377d070d81a5ccf71e6059a58f3b38481951ecafd36463a5dd` |
| `mizukami2020_solc_spacing.html` | Mizukami2020 J-STAGE, sections4.6-4.7 Eq4/5; documentary candidate, not admitted LPBF law | `aa03cefa2f447d68b266bfec4f9787b53854d6590f9633d77d1c1eb0033fdd51` |
| `mizukami2020_solc_fig11.jpg` | Same article Fig11, visually inspected; no coefficient admission | `d06719cce64aff7c1d5f723582428adff6f1836f8b04cf238051f56d4665ed2f` |
| `sol_c_timet_ti64_properties.pdf` | TIMETAL6-4 Properties, PDF6 Density; density checker | `f9bcc879445c07259d5388598bea8b69f667d9180269b40b12dce28b57a7c507` |
| `sol_c_ati718_bar.pdf` | ATI718 NI-105v2, PDF1 Density; density checker | `234b2bc76e5f92e8d98b75f9231949236234fcf35f7c168afaceec82ad2b5855` |
| `sol_c_aksteel316l.pdf` | AKSteel316/316L 2007, PDF2 Density; density checker | `0b3d06f93a882e882822b18ef8aacff30ee6c3448d2ce56627a1332234f2f152` |
| `sol_c_smc625.pdf` | SpecialMetals625 Aug2013, PDF2 Table2 Density; same bytes as SOL-T archive above | `f5379cccfe1fe760ebdc20e3f590e709e5acd1c0063d212d4ae5fd6568496d98` |
| `sol_c_timet_ti64_datasheet.pdf` | TIMET TMC-0150, PDF1 Table2 Density; distinct source alternative, density checker | `824684f7d5603af19e0d0862e1af1289f4ea64ae7fac7f54e649ae0f80040822` |

The scalar checks authenticate source bytes/located declarations and their binding to code, not measurement quality or high-temperature accuracy. Unquantified physical/transfer error remains explicit. SOL-C exports only source notes/check scripts and this index, never PDFs or full article objects.

## SOL-C Amendment 6 local source additions (2026-10-16)

Local-only source objects for [A6 spacing models](../docs/research/sol_c_a6_spacing.md). PDFs and article objects are not staged or redistributed. Missing or changed archives fail the associated `python -I -B ... --check`; no checker downloads or silently skips a source. Existing Ti and Ni-Nb sources retain the A5 hashes above, with new disclosed extrapolation/transfer contracts rather than new measurements.

| Local filename | Source / exact checked locator | Raw SHA256 |
|---|---|---|
| `solc_a6_spacing_al.pdf` | Gandolfi2021, DOI10.3390/met11071019, PDF6 rate definition and PDF13 Eqs1/2 conclusions | `e8bc8ab8b029b5bc9aaf217f5aef167481610b1f04ad30820a6329370d32b1e4` |
| `solc_a6_spacing_steel.pdf` | Bunaziv2023, DOI10.1007/s00170-023-11567-y, SINTEF NVA archive, PDF16 Eq2 and PDF17 Eq6/cooling definition | `7fb5f22ed956c764f2079431101387ef792a86d426335ae4ce202a982ad6ec34` |
| `solc_a6_spacing_ni.pdf` | Mitchell2005, DOI10.7449/2005/Superalloys_2005_299_310, PDF4 Eq1 | `9ceee36095cd4363239a0457f305e65970deeb1c813c2114546c7b63848f9569` |

The separate [A6 morphology/phase source record](../docs/research/sol_c_a6_morph_source_extracts.json) stores bounded normalized primary-browser/table transcriptions, with exact URLs/locators and retrieval limitations. It is committed as a small numeric/equation research record, not a PDF archive or raw source-byte authentication. Its source/transcription checks and independent physical-model arithmetic are described in [sol_c_a6_morph_phase.md](../docs/research/sol_c_a6_morph_phase.md).

## SOL-C Amendment 7 local source additions (2026-10-16)

The [A7 source audit](../docs/research/sol_c_a7_source_audit.md) contains exact download URLs, page locators, SHA256 identities and failed-access limits. Six complete PDFs were obtained and their selected pages inspected as text and rendered images: `solc_a7_salsi2018.pdf`, `solc_a7_ghosh2018.pdf`, `solc_a7_azizi2020.pdf`, `solc_a7_gerstgrasser2021.pdf`, `solc_a7_yaokawa2023.pdf`, `solc_a7_eutectic2022.pdf`. The executable pins are in `docs/research/scripts/sol_c_a7_sources_check.py`; missing or changed source objects fail rather than skip.

Brooke's complete primary JATS XML and PMC HTML are local `solc_a7_brooke_jats.xml` and `solc_a7_brooke_pmc.html`; their hashes and selected MathML agree. This is source-byte authentication of those representations, not of an absent PDF. DOI103802 is Durga and Lindwall (2023), not Mishra; primary indexed text verifies the .0049/.49 true-fraction convention, with no PDF authentication claim. Gao2025's original PDF and the content of its 2026 corrigendum remain unverified. Nucleation assumptions retain Unresolved provenance. Hunt1984/MS1964 originals were sought but not obtained.

All PDFs, XML/HTML objects, metadata, text extracts and page renders remain local-only and are never staged; the commit contains only source notes, specification and checks. No measured-pool validation or redistribution rights are inferred. The preserved A6 transcription JSON is historical and explicitly hash-pinned; new primary verification does not silently rewrite it.
