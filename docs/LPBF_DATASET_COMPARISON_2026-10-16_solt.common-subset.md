# LPBF dataset comparison: common subset dc6f5fdd -> 13203cac

Schema `lpbf-dataset-common-subset-1`. Rule: per kernel, rows with extentStatus == 'computed' in BOTH records; ratio = model / measured. Comparison against published single-track measurements; not validation; nothing fitted. `experimentalValidation` = false.

| kernel | group | n | W MAPE % | D MAPE % | W bias % | D bias % |
| --- | --- | ---: | --- | --- | --- | --- |
| rosenthal | all-datasets | 790 | 32.3 -> 33.4 | 34.2 -> 34.7 | -31.0 -> -32.1 | -13.1 -> -14.6 |
| rosenthal | hofmann-316l-2026 | 638 | 35.1 -> 36.3 | 33.1 -> 33.7 | -34.9 -> -36.2 | -11.7 -> -13.6 |
| rosenthal | ku-leuven-316l-2021 | 44 | 19.1 -> 20.3 | 39.6 -> 39.9 | -18.7 -> -20.2 | -37.8 -> -38.5 |
| rosenthal | ku-leuven-ti64-2021 | 14 | 13.2 -> 13.2 | 25.8 -> 25.8 | -13.2 -> -13.2 | 10.8 -> 10.8 |
| rosenthal | lane-in625-2020 | 14 | 31.2 -> 31.2 | 37.8 -> 37.8 | -31.2 -> -31.2 | -33.8 -> -33.8 |
| rosenthal | pooled-summary-scope | 718 | 33.5 -> 34.6 | 33.9 -> 34.5 | -32.1 -> -33.2 | -11.6 -> -13.3 |
| rosenthal | totis-ti64-2021 | 80 | 20.9 -> 20.9 | 40.9 -> 40.9 | -9.6 -> -9.6 | -10.8 -> -10.8 |
| eagar-tsai | all-datasets | 837 | 23.7 -> 24.6 | 34.9 -> 35.7 | -21.8 -> -22.7 | -18.0 -> -19.7 |
| eagar-tsai | hofmann-316l-2026 | 676 | 25.4 -> 26.4 | 34.3 -> 35.2 | -25.1 -> -26.2 | -17.1 -> -19.1 |
| eagar-tsai | ku-leuven-316l-2021 | 44 | 17.3 -> 18.5 | 39.6 -> 39.9 | -16.8 -> -18.2 | -37.8 -> -38.5 |
| eagar-tsai | ku-leuven-ti64-2021 | 14 | 10.3 -> 10.3 | 25.8 -> 25.8 | -10.1 -> -10.1 | 10.8 -> 10.8 |
| eagar-tsai | lane-in625-2020 | 23 | 10.6 -> 10.6 | 36.9 -> 36.9 | -0.4 -> -0.4 | -36.9 -> -36.9 |
| eagar-tsai | pooled-summary-scope | 756 | 24.7 -> 25.6 | 34.8 -> 35.6 | -23.0 -> -23.9 | -16.8 -> -18.6 |
| eagar-tsai | totis-ti64-2021 | 80 | 18.5 -> 18.5 | 38.7 -> 38.7 | -4.6 -> -4.6 | -14.1 -> -14.1 |
| goldak | all-datasets | 779 | 32.1 -> 33.2 | 34.0 -> 34.4 | -30.8 -> -31.9 | -12.2 -> -13.8 |
| goldak | hofmann-316l-2026 | 631 | 34.9 -> 36.2 | 32.6 -> 33.1 | -34.7 -> -36.1 | -10.6 -> -12.5 |
| goldak | ku-leuven-316l-2021 | 44 | 18.9 -> 20.2 | 39.6 -> 39.9 | -18.5 -> -20.0 | -37.8 -> -38.5 |
| goldak | ku-leuven-ti64-2021 | 14 | 13.0 -> 13.0 | 25.8 -> 25.8 | -13.0 -> -13.0 | 10.8 -> 10.8 |
| goldak | lane-in625-2020 | 10 | 29.2 -> 29.2 | 48.3 -> 48.3 | -29.2 -> -29.2 | -48.3 -> -48.3 |
| goldak | pooled-summary-scope | 711 | 33.3 -> 34.5 | 33.6 -> 34.0 | -31.9 -> -33.1 | -10.5 -> -12.2 |
| goldak | totis-ti64-2021 | 80 | 20.9 -> 20.9 | 41.1 -> 41.1 | -9.6 -> -9.6 | -10.0 -> -10.0 |

Computed rows in the summary scope (before -> after): rosenthal 722 -> 718, eagar-tsai 756 -> 756, goldak 715 -> 711.
