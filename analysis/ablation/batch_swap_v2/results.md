# Batch-swap v2 — results (2×2 reflect × gate)

Pairs=382, K=3 draws/arm. Numbers + CIs first; interpretation is conditional on them.

## Headline
| estimand | point | perm p | 95% CI (run cluster-boot) | 95% CI (naive-pair) | MDE bound |
|---|---|---|---|---|---|
| pooled SPECIFICITY | +0.0054 | 0.5975 | [-0.0116,+0.0242] | [-0.0149,+0.0257] | 0.033 |
| pooled TRANSFER | -0.0011 | 0.9277 | [-0.0243,+0.0228] | [-0.0271,+0.0251] | (single margin; wider) |

Specificity verdict: **≈0 (within MDE 0.033)**. Transfer verdict: **≈0 (within MDE 0.033)**.

Pooled specificity = mean over pairs of ((margin_on_B | R_B) - (margin_on_B | R_Bp) + (margin_on_Bp | R_Bp) - (margin_on_Bp | R_B)) / 2, draws averaged within arm first. Pooled transfer = mean over pairs of mismatched-arm margins ((margin_on_B | R_Bp) + (margin_on_Bp | R_B)) / 2.

## Overlap decomposition
specificity ~ type_jaccard OLS: intercept -0.0176, slope +0.0690. Decomposition uninformative: run-cluster bootstrap slope 95% CI [-0.0739, +0.1959]; extrapolated prediction at overlap=1 95% CI [-0.0476, +0.1368]; observed jaccard support max 0.83 (mean 0.335), so overlap=1 is out of support. No masking or example-level residual is supported.

## Lottery
within-arm accept disagreement across draws = 0.382 (higher-n check of the prior 0.32).
Accept rule for this figure: within-arm accept = margin_on_B>0 (batch-sum, strict), applied to margin_on_B for both arms; disagreement = non-unanimity of accept across the 3 draws per (pair,arm) cell, n=764 cells. Sum-margin (own-margin) variants: 0.415 (>0), 0.398 (>=0).

## Interpretation (selected from realized numbers)
both≈0 → example channel inert even same-example → strongest Claim A.

Scope: one-step gate ≠ downstream U; IFBench verifiable-SI regime only. Every cell above carries its MDE/CI; the run-cluster CI is the honest arbiter over the permutation p.
