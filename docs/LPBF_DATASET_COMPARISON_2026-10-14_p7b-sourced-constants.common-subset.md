# LPBF dataset comparison: common subset c61ab6a8 -> 36cd9d4a

Schema `lpbf-dataset-common-subset-1`. Rule: per kernel, rows with extentStatus == 'computed' in BOTH records; ratio = model / measured. Comparison against published single-track measurements; not validation; nothing fitted. `experimentalValidation` = false.

| kernel | group | n | W MAPE % | D MAPE % | W bias % | D bias % |
| --- | --- | ---: | --- | --- | --- | --- |
| rosenthal | all-datasets | 794 | 15.3 -> 32.4 | 38.7 -> 34.1 | -8.9 -> -31.1 | 18.2 -> -13.0 |
| rosenthal | hofmann-316l-2026 | 642 | 14.7 -> 35.2 | 39.5 -> 32.9 | -10.4 -> -35.0 | 23.7 -> -11.7 |
| rosenthal | ku-leuven-316l-2021 | 44 | 16.1 -> 19.1 | 29.0 -> 39.6 | 10.9 -> -18.7 | -12.9 -> -37.8 |
| rosenthal | ku-leuven-ti64-2021 | 14 | 11.1 -> 13.2 | 28.6 -> 25.8 | -10.7 -> -13.2 | 21.2 -> 10.8 |
| rosenthal | lane-in625-2020 | 14 | 14.6 -> 31.2 | 39.7 -> 37.8 | -14.6 -> -31.2 | -16.4 -> -33.8 |
| rosenthal | pooled-summary-scope | 722 | 15.3 -> 33.6 | 39.4 -> 33.8 | -10.0 -> -32.2 | 20.7 -> -11.6 |
| rosenthal | totis-ti64-2021 | 80 | 20.6 -> 20.9 | 38.8 -> 40.9 | -7.0 -> -9.6 | -3.7 -> -10.8 |
| eagar-tsai | all-datasets | 837 | 12.0 -> 23.7 | 35.9 -> 34.9 | -2.7 -> -21.8 | 15.1 -> -18.0 |
| eagar-tsai | hofmann-316l-2026 | 676 | 10.8 -> 25.4 | 36.8 -> 34.3 | -4.2 -> -25.1 | 20.4 -> -17.1 |
| eagar-tsai | ku-leuven-316l-2021 | 44 | 16.7 -> 17.3 | 29.0 -> 39.6 | 12.2 -> -16.8 | -12.9 -> -37.8 |
| eagar-tsai | ku-leuven-ti64-2021 | 14 | 8.4 -> 10.3 | 28.6 -> 25.8 | -7.8 -> -10.1 | 21.2 -> 10.8 |
| eagar-tsai | lane-in625-2020 | 23 | 20.1 -> 10.6 | 25.2 -> 36.9 | 15.3 -> -0.4 | -14.2 -> -36.9 |
| eagar-tsai | pooled-summary-scope | 756 | 11.6 -> 24.7 | 36.8 -> 34.8 | -4.0 -> -23.0 | 17.5 -> -16.8 |
| eagar-tsai | totis-ti64-2021 | 80 | 18.7 -> 18.5 | 36.5 -> 38.7 | -2.2 -> -4.6 | -7.1 -> -14.1 |
| goldak | all-datasets | 783 | 15.1 -> 32.2 | 39.5 -> 33.9 | -8.6 -> -30.9 | 19.5 -> -12.1 |
| goldak | hofmann-316l-2026 | 635 | 14.4 -> 35.0 | 40.6 -> 32.6 | -10.0 -> -34.9 | 25.4 -> -10.5 |
| goldak | ku-leuven-316l-2021 | 44 | 16.1 -> 18.9 | 29.0 -> 39.6 | 11.0 -> -18.5 | -12.9 -> -37.8 |
| goldak | ku-leuven-ti64-2021 | 14 | 11.0 -> 13.0 | 28.6 -> 25.8 | -10.6 -> -13.0 | 21.2 -> 10.8 |
| goldak | lane-in625-2020 | 10 | 14.0 -> 29.2 | 37.0 -> 48.3 | -14.0 -> -29.2 | -37.0 -> -48.3 |
| goldak | pooled-summary-scope | 715 | 15.1 -> 33.5 | 40.4 -> 33.5 | -9.7 -> -32.0 | 22.2 -> -10.5 |
| goldak | totis-ti64-2021 | 80 | 20.6 -> 20.9 | 39.1 -> 41.1 | -6.9 -> -9.6 | -2.9 -> -10.0 |

Computed rows in the summary scope (before -> after): rosenthal 754 -> 722, eagar-tsai 757 -> 756, goldak 753 -> 715.
