# LPBF dataset comparison: common subset cda80143 -> c61ab6a8

Schema `lpbf-dataset-common-subset-1`. Rule: per kernel, rows with extentStatus == 'computed' in BOTH records; ratio = model / measured. Comparison against published single-track measurements; not validation; nothing fitted. `experimentalValidation` = false.

| kernel | group | n | W MAPE % | D MAPE % | W bias % | D bias % |
| --- | --- | ---: | --- | --- | --- | --- |
| rosenthal | all-datasets | 826 | 30.9 -> 15.9 | 56.5 -> 39.9 | 14.1 -> -9.8 | 47.9 -> 20.2 |
| rosenthal | hofmann-316l-2026 | 670 | 26.8 -> 15.4 | 59.1 -> 41.0 | 8.8 -> -11.3 | 55.6 -> 25.8 |
| rosenthal | ku-leuven-316l-2021 | 44 | 57.7 -> 16.1 | 44.0 -> 29.0 | 57.7 -> 10.9 | -8.4 -> -12.9 |
| rosenthal | ku-leuven-ti64-2021 | 14 | 37.0 -> 11.1 | 69.0 -> 28.6 | 37.0 -> -10.7 | 66.8 -> 21.2 |
| rosenthal | lane-in625-2020 | 18 | 18.6 -> 15.0 | 28.0 -> 39.8 | -18.6 -> -15.0 | -6.3 -> -3.8 |
| rosenthal | pooled-summary-scope | 750 | 29.5 -> 16.0 | 57.7 -> 40.7 | 11.9 -> -10.8 | 52.1 -> 22.7 |
| rosenthal | totis-ti64-2021 | 80 | 52.2 -> 20.6 | 46.2 -> 38.8 | 38.0 -> -7.0 | 23.2 -> -3.7 |
| eagar-tsai | all-datasets | 838 | 12.0 -> 12.0 | 36.0 -> 36.0 | -2.7 -> -2.7 | 15.1 -> 15.1 |
| eagar-tsai | hofmann-316l-2026 | 677 | 10.7 -> 10.7 | 36.9 -> 36.9 | -4.2 -> -4.2 | 20.4 -> 20.4 |
| eagar-tsai | ku-leuven-316l-2021 | 44 | 16.7 -> 16.7 | 29.0 -> 29.0 | 12.2 -> 12.2 | -12.9 -> -12.9 |
| eagar-tsai | ku-leuven-ti64-2021 | 14 | 8.4 -> 8.4 | 28.6 -> 28.6 | -7.8 -> -7.8 | 21.2 -> 21.2 |
| eagar-tsai | lane-in625-2020 | 23 | 20.1 -> 20.1 | 25.2 -> 25.2 | 15.3 -> 15.3 | -14.2 -> -14.2 |
| eagar-tsai | pooled-summary-scope | 757 | 11.6 -> 11.6 | 36.8 -> 36.8 | -4.0 -> -4.0 | 17.5 -> 17.5 |
| eagar-tsai | totis-ti64-2021 | 80 | 18.7 -> 18.7 | 36.5 -> 36.5 | -2.2 -> -2.2 | -7.1 -> -7.1 |
| goldak | all-datasets | 829 | 16.0 -> 16.0 | 41.1 -> 41.1 | -9.9 -> -9.9 | 22.2 -> 22.2 |
| goldak | hofmann-316l-2026 | 673 | 15.5 -> 15.5 | 42.5 -> 42.5 | -11.4 -> -11.4 | 28.1 -> 28.1 |
| goldak | ku-leuven-316l-2021 | 44 | 16.1 -> 16.1 | 29.0 -> 29.0 | 11.0 -> 11.0 | -12.9 -> -12.9 |
| goldak | ku-leuven-ti64-2021 | 14 | 11.0 -> 11.0 | 28.6 -> 28.6 | -10.6 -> -10.6 | 21.2 -> 21.2 |
| goldak | lane-in625-2020 | 18 | 16.1 -> 16.1 | 39.1 -> 39.1 | -16.1 -> -16.1 | -2.0 -> -2.0 |
| goldak | pooled-summary-scope | 753 | 16.1 -> 16.1 | 42.1 -> 42.1 | -10.9 -> -10.9 | 24.9 -> 24.9 |
| goldak | totis-ti64-2021 | 80 | 20.6 -> 20.6 | 39.1 -> 39.1 | -6.9 -> -6.9 | -2.9 -> -2.9 |

Computed rows in the summary scope (before -> after): rosenthal 750 -> 754, eagar-tsai 757 -> 757, goldak 753 -> 753.
