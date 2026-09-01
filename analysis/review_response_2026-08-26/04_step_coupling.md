# Item 4: step-count coupling and endpoint versus steps

**EXPLORATORY. Descriptive only.** None of this was pre-registered. No test below is
confirmatory, no p-value is reported against a decision threshold, and no causal claim is made
or implied. Correlations over 8 seeds are unstable by construction; intervals are shown to make
that width visible, not to support inference.

Numbers only. No interpretation.

## Reflection events versus accepts, within arm

| arm | n | Pearson r | Spearman rho | 95% bootstrap CI on r (resample seeds) |
|---|---|---|---|---|
| B | 8 | -0.996174 | -0.993651 | [-1.0000, -0.9897] |
| C | 8 | -0.973124 | -0.962025 | [-0.9965, -0.8123] |
| T | 8 | -0.948400 | -0.993220 | [-1.0000, -0.8704] |
| all 24 | 24 | -0.054587 | -0.075744 | [-0.3253, +0.2268] |

`candidates_incl_seed == accepts + 1` holds for all 24 runs: **True**. The two are the same
quantity up to a constant, so any correlation involving candidates equals the one involving
accepts.

## Reflection events per arm

| arm | mean | SD | min | max | per-seed values (0..7) |
|---|---|---|---|---|---|
| B | 31.2500 | 3.3700 | 27 | 36 | 32, 32, 35, 32, 27, 36, 29, 27 |
| C | 26.0000 | 2.0702 | 23 | 30 | 27, 30, 27, 25, 23, 26, 25, 25 |
| T | 23.3750 | 1.4079 | 22 | 26 | 23, 22, 23, 26, 23, 25, 23, 22 |

## Endpoint versus reflection events

| scope | n | Pearson r | Spearman rho | 95% bootstrap CI on r |
|---|---|---|---|---|
| arm B | 8 | +0.015367 | -0.036827 | [-0.8926, +0.8444] |
| arm C | 8 | +0.513852 | +0.675164 | [-0.0418, +0.9567] |
| arm T | 8 | -0.149330 | +0.071088 | [-0.6276, +0.6538] |
| all 24 runs | 24 | +0.225156 | +0.297960 | [-0.1567, +0.6716] |

## Endpoint versus accepts

| scope | n | Pearson r | Spearman rho | 95% bootstrap CI on r |
|---|---|---|---|---|
| arm B | 8 | +0.013628 | +0.074125 | [-0.8268, +0.9125] |
| arm C | 8 | -0.497509 | -0.687440 | [-0.9571, +0.0932] |
| arm T | 8 | +0.055067 | -0.044931 | [-0.5995, +0.5786] |
| all 24 runs | 24 | +0.033461 | +0.047411 | [-0.3267, +0.3933] |

## Per-run table

| arm | seed | reflection events | accepts | candidates | total evals | endpoint |
|---|---|---|---|---|---|---|
| B | 0 | 32 | 10 | 11 | 302 | 0.633333 |
| B | 1 | 32 | 10 | 11 | 302 | 0.617778 |
| B | 2 | 35 | 8 | 9 | 300 | 0.564444 |
| B | 3 | 32 | 10 | 11 | 302 | 0.602222 |
| B | 4 | 27 | 13 | 14 | 302 | 0.568889 |
| B | 5 | 36 | 8 | 9 | 309 | 0.591111 |
| B | 6 | 29 | 12 | 13 | 304 | 0.640000 |
| B | 7 | 27 | 13 | 14 | 305 | 0.575556 |
| C | 0 | 27 | 6 | 7 | 313 | 0.628889 |
| C | 1 | 30 | 3 | 4 | 310 | 0.593333 |
| C | 2 | 27 | 6 | 7 | 313 | 0.591111 |
| C | 3 | 25 | 8 | 9 | 315 | 0.566667 |
| C | 4 | 23 | 9 | 10 | 307 | 0.557778 |
| C | 5 | 26 | 6 | 7 | 304 | 0.584444 |
| C | 6 | 25 | 7 | 8 | 305 | 0.608889 |
| C | 7 | 25 | 7 | 8 | 305 | 0.568889 |
| T | 0 | 23 | 9 | 10 | 307 | 0.571111 |
| T | 1 | 22 | 10 | 11 | 308 | 0.568889 |
| T | 2 | 23 | 9 | 10 | 307 | 0.575556 |
| T | 3 | 26 | 6 | 7 | 304 | 0.568889 |
| T | 4 | 23 | 9 | 10 | 307 | 0.657778 |
| T | 5 | 25 | 8 | 9 | 315 | 0.573333 |
| T | 6 | 23 | 9 | 10 | 307 | 0.604444 |
| T | 7 | 22 | 11 | 12 | 318 | 0.571111 |

## Provenance

| field | value |
|---|---|
| runs read | 24 (`run_summary.json` + `endpoints.json`) |
| bootstrap | 10000 resamples, seed 20260709, percentile method |

Pearson r computed twice (numpy vs pure Python) for every scope and asserted to 1e-12.

