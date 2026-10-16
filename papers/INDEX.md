# SOL-T property-source archive

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
