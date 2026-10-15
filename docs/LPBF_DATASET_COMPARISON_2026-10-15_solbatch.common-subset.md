# LPBF dataset comparison: common subset 36cd9d4a -> dc6f5fdd

Schema `lpbf-dataset-common-subset-1`. Rule: per kernel, rows with extentStatus == 'computed' in BOTH records; ratio = model / measured. Comparison against published single-track measurements; not validation; nothing fitted. `experimentalValidation` = false.

| kernel | group | n | W MAPE % | D MAPE % | W bias % | D bias % |
| --- | --- | ---: | --- | --- | --- | --- |
| rosenthal | all-datasets | 794 | 32.4 -> 32.4 | 34.1 -> 34.1 | -31.1 -> -31.1 | -13.0 -> -13.0 |
| rosenthal | hofmann-316l-2026 | 642 | 35.2 -> 35.2 | 32.9 -> 32.9 | -35.0 -> -35.0 | -11.7 -> -11.7 |
| rosenthal | ku-leuven-316l-2021 | 44 | 19.1 -> 19.1 | 39.6 -> 39.6 | -18.7 -> -18.7 | -37.8 -> -37.8 |
| rosenthal | ku-leuven-ti64-2021 | 14 | 13.2 -> 13.2 | 25.8 -> 25.8 | -13.2 -> -13.2 | 10.8 -> 10.8 |
| rosenthal | lane-in625-2020 | 14 | 31.2 -> 31.2 | 37.8 -> 37.8 | -31.2 -> -31.2 | -33.8 -> -33.8 |
| rosenthal | pooled-summary-scope | 722 | 33.6 -> 33.6 | 33.8 -> 33.8 | -32.2 -> -32.2 | -11.6 -> -11.6 |
| rosenthal | totis-ti64-2021 | 80 | 20.9 -> 20.9 | 40.9 -> 40.9 | -9.6 -> -9.6 | -10.8 -> -10.8 |
| eagar-tsai | all-datasets | 837 | 23.7 -> 23.7 | 34.9 -> 34.9 | -21.8 -> -21.8 | -18.0 -> -18.0 |
| eagar-tsai | hofmann-316l-2026 | 676 | 25.4 -> 25.4 | 34.3 -> 34.3 | -25.1 -> -25.1 | -17.1 -> -17.1 |
| eagar-tsai | ku-leuven-316l-2021 | 44 | 17.3 -> 17.3 | 39.6 -> 39.6 | -16.8 -> -16.8 | -37.8 -> -37.8 |
| eagar-tsai | ku-leuven-ti64-2021 | 14 | 10.3 -> 10.3 | 25.8 -> 25.8 | -10.1 -> -10.1 | 10.8 -> 10.8 |
| eagar-tsai | lane-in625-2020 | 23 | 10.6 -> 10.6 | 36.9 -> 36.9 | -0.4 -> -0.4 | -36.9 -> -36.9 |
| eagar-tsai | pooled-summary-scope | 756 | 24.7 -> 24.7 | 34.8 -> 34.8 | -23.0 -> -23.0 | -16.8 -> -16.8 |
| eagar-tsai | totis-ti64-2021 | 80 | 18.5 -> 18.5 | 38.7 -> 38.7 | -4.6 -> -4.6 | -14.1 -> -14.1 |
| goldak | all-datasets | 783 | 32.2 -> 32.2 | 33.9 -> 33.9 | -30.9 -> -30.9 | -12.1 -> -12.1 |
| goldak | hofmann-316l-2026 | 635 | 35.0 -> 35.0 | 32.6 -> 32.6 | -34.9 -> -34.9 | -10.5 -> -10.5 |
| goldak | ku-leuven-316l-2021 | 44 | 18.9 -> 18.9 | 39.6 -> 39.6 | -18.5 -> -18.5 | -37.8 -> -37.8 |
| goldak | ku-leuven-ti64-2021 | 14 | 13.0 -> 13.0 | 25.8 -> 25.8 | -13.0 -> -13.0 | 10.8 -> 10.8 |
| goldak | lane-in625-2020 | 10 | 29.2 -> 29.2 | 48.3 -> 48.3 | -29.2 -> -29.2 | -48.3 -> -48.3 |
| goldak | pooled-summary-scope | 715 | 33.5 -> 33.5 | 33.5 -> 33.5 | -32.0 -> -32.0 | -10.5 -> -10.5 |
| goldak | totis-ti64-2021 | 80 | 20.9 -> 20.9 | 41.1 -> 41.1 | -9.6 -> -9.6 | -10.0 -> -10.0 |

Computed rows in the summary scope (before -> after): rosenthal 722 -> 722, eagar-tsai 756 -> 756, goldak 715 -> 715.
