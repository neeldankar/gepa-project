# Item 3: permutation calibration of the 108-cell conjunction rule

Numbers only. No interpretation.

## What was permuted

The outcome `spec_i` is permuted **within seed**, holding all 108 scorers fixed. This preserves
the cross-cell correlation structure, which is what makes a maximum over 108 cells a valid null.
Mirrors the negative-control construction at `screen_part4_stats.py:23-30`.

Permutations: **200** plus one identity pass. Full original fidelity, B = P = 9999,
`CellEngine`, `perrun_z` and `bca_ci` reused unchanged.

## The rule, as implemented

From `screen_part4_stats.py:277-284`, verbatim in effect:

- **crit_a**: BCa CI on read 4.1 excludes 0, **LORO >= 7** (not 8), permutation p < 0.05.
- **crit_b**: crit_a AND read 4.2 CI excludes 0 AND read 4.2 p < 0.05. It chains crit_a and does
  not re-check LORO on 4.2.
- **MCB** (`:289-297`): a cell is retained if the 5th percentile of
  `max_others |beta_boot| - |beta_boot|` is <= 0, over shared bootstrap draws.

## Identity-pass validation

| predicate | identity pass | published `screen_stats_cells.csv` | reproduces |
|---|---|---|---|
| crit_a | 3: ['knn_emb_fb_min', 'knn_emb_full_max', 'knn_emb_full_mean'] | 3: ['knn_emb_fb_min', 'knn_emb_full_max', 'knn_emb_full_mean'] | YES |
| crit_b | 2: ['knn_emb_fb_min', 'knn_emb_full_mean'] | 2: ['knn_emb_fb_min', 'knn_emb_full_mean'] | YES |
| crit_b + MCB | 1: ['knn_emb_fb_min'] | published sole survivor: `knn_emb_fb_min` | YES |

The stated conjunction rule alone leaves 3 cells under crit_a and 2 under crit_b. The published
single-survivor status of `knn_emb_fb_min` is reached only after the MCB step.

## Calibration

Fraction of permutations yielding at least one survivor, by predicate and LORO threshold:

| predicate | LORO >= 7 | LORO == 8 |
|---|---|---|
| crit_a | 0.8900 (178/200) | 0.8900 (178/200) |
| crit_b | 0.8250 (165/200) | 0.8250 (165/200) |
| crit_a + MCB | 0.7500 (150/200) | 0.7400 (148/200) |
| crit_b + MCB | 0.6700 (134/200) | 0.6600 (132/200) |

Survivor-count distribution under the null (LORO >= 7):

| predicate | mean | max | 0 survivors | 1 | 2 | 3 or more |
|---|---|---|---|---|---|---|
| crit_a | 5.2050 | 25 | 22 | 22 | 24 | 132 |
| crit_b | 3.8800 | 23 | 35 | 25 | 33 | 107 |
| crit_a + MCB | 1.5300 | 5 | 50 | 63 | 41 | 46 |
| crit_b + MCB | 1.2150 | 5 | 66 | 65 | 41 | 28 |

## Null distribution of the maximum beta across the 108 cells

| statistic | mean | SD | p50 | p90 | p95 | p99 | max |
|---|---|---|---|---|---|---|---|
| max beta | 0.039168 | 0.014869 | 0.037020 | 0.057720 | 0.070407 | 0.094050 | 0.095850 |
| max |beta| | 0.046699 | 0.019325 | 0.040453 | 0.077570 | 0.095902 | 0.103535 | 0.107758 |

Observed `knn_emb_fb_min` beta on read 4.1: **+0.037940**. Observed max beta across the
108 cells on unpermuted data: **+0.059229**.

| comparison | value |
|---|---|
| permutations with max beta >= observed max | 17/200 = 0.0850 |
| permutations with max beta >= 0.03794 | 93/200 = 0.4650 |

## Provenance

| field | value |
|---|---|
| permutations (excluding identity) | 200 |
| cells per race | 108 |
| B (bootstrap), P (within-run permutation) | 9999, 9999 |
| screen_part4_stats.py sha256 | `cd440a9bb8826780e05e5df9d71c634df45babffcfb23b4e541a413d159a2401` |
| features.csv sha256 | `f9c4799aeb37051cfbd4e6e7dc043c466bc206968bfa6c75d49e025bc9e3ad0f` |
| outcomes.csv sha256 | `2f87a7397b4d9de7ac983c66f6402c2e13bc6bd37f9f5aa45b55b3238a84d853` |

