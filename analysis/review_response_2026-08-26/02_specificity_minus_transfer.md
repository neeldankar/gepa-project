# Item 2: paired specificity minus transfer, HoVer swap corpus

Numbers only. No interpretation.

Per-pair `d = specificity - transfer` over 243 pairs, 8 run clusters, K = 3 draws per
arm. Machinery reused unchanged from `hover_swap_analysis.py`: `load()`, `draw_avg()`,
`perm_p()` (within-pair sign-flip, NPERM = 20000), `cluster_boot()` (run-level cluster
bootstrap over seeds, NBOOT = 20000), MDE = Z80 x SE with Z80 = 2.802.

## Result

| estimand | point | 95% CI (run cluster-boot) | SE (clustered) | MDE | perm p (within-pair) |
|---|---|---|---|---|---|
| specificity minus transfer | +0.010516690 | [-0.012037, +0.034314] | 0.011891 | 0.033319 | 0.646400 |

Reference, recomputed here from the same rows:

| estimand | point |
|---|---|
| pooled specificity | +0.027434842 |
| pooled transfer | +0.016918153 |
| difference | +0.010516690 |

Sign split on the 243 per-pair differences: 117 positive, 119 negative, 7 exactly zero.

## Per seed

| seed | pairs | mean d | SD |
|---|---|---|---|
| 0 | 32 | +0.036458 | 0.299877 |
| 1 | 34 | -0.006536 | 0.392305 |
| 2 | 28 | -0.017857 | 0.337103 |
| 3 | 33 | +0.047138 | 0.422213 |
| 4 | 27 | +0.063786 | 0.319404 |
| 5 | 34 | -0.024510 | 0.304349 |
| 6 | 28 | -0.033730 | 0.425614 |
| 7 | 27 | +0.022634 | 0.317374 |

## Provenance

| field | value |
|---|---|
| pairs | 243 |
| draw rows | 1458 |
| hover_swap_analysis.py sha256 | `60bd00c8e97e9347ab82b03a6e8767cf326c302ef71815bcf784c5708228cf7d` |

Mean, permutation p, CI bounds and SE each computed twice by independent implementations and
asserted to 1e-12.

