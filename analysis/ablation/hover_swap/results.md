# Stage-2 HoVer batch-swap — results

Pairs = 243. Draws/arm K = 3. Run clusters = 8 seeds.
Per-seed pairs: {0: 32, 1: 34, 2: 28, 3: 33, 4: 27, 5: 34, 6: 28, 7: 27}.
Draw rows = 1458. Score support = {0, 1/3, 2/3, 1}; margins computed in integer thirds.

## Pooled estimands

| estimand | point | 95% CI (run cluster-boot) | MDE | SE (clustered) | perm p (within-pair) | 95% CI (naive-pair) |
|---|---|---|---|---|---|---|
| pooled specificity | +0.0274 | [+0.0149, +0.0415] | 0.0191 | 0.0068 | 0.0177 | [+0.0048, +0.0501] |
| pooled transfer | +0.0169 | [-0.0040, +0.0367] | 0.0293 | 0.0104 | 0.3120 | [-0.0149, +0.0489] |

Units: title-recall score points, on v2's scale. Per-example scores lie in {0, 1/3, 2/3, 1}; a margin is the sum over the 3 examples of the batch (range [-3, +3]), matching `batch_swap_v2_run.py:235`. Margins are accumulated internally in integer thirds and divided by 3 to return to score points; they are not averaged per example.

## Second-path recompute

Independent aggregation route (pandas groupby on `(pair, arm)`) vs the primary per-pair dict/numpy route.

| estimand | primary | second path | abs delta |
|---|---|---|---|
| pooled specificity | +0.027434842 | +0.027434842 | 0.00e+00 |
| pooled transfer | +0.016918153 | +0.016918153 | 0.00e+00 |

Baseline-cancellation check: pooled specificity recomputed from child sums alone (parent terms dropped) differs from the baseline-subtracted value by max |diff| = 2.22e-16 across pairs.

## Tie shares

Counted exactly, in integer thirds.

| quantity | share exactly 0 | N |
|---|---|---|
| per-example child-parent deltas (all) | 0.6295 | 8748 |
| per-example child-parent deltas (own batch) | 0.6278 | 4374 |
| per-example child-parent deltas (other batch) | 0.6312 | 4374 |
| batch margins | 0.3656 | 2916 |

## Provenance

Estimand definitions ported from `scripts/batch_swap_v2_analysis.py` without change (v2 `B`->`A_e`, `B'`->`B_e`, arm `R_B`->`SAME`, arm `R_Bp`->`SWAP`):

- margin = sum of the 3 per-example child scores minus the sum of the parent's scores on the same batch (`batch_swap_v2_run.py:222,232-235`).
- pooled specificity = mean of `margin(SAME on A) - margin(SWAP on A)` and `margin(SWAP on B) - margin(SAME on B)`.
- pooled transfer = mean of `margin(SAME on B)` and `margin(SWAP on A)`.
- `draw_avg`, `perm_p`, `cluster_boot`, `NPERM = NBOOT = 20000`, `rng = default_rng(20260703)` taken verbatim from v2.

MDE = `Z80 * SE_clustered`, `Z80 = 2.802` (verbatim, `batch_swap_v2_stage0.py:36`); `SE_clustered` is the standard deviation of the run-level cluster-bootstrap means. v2's `SIG2 = 0.0775` and `MDE_SPEC = {2: 0.040, 3: 0.033}` are single-draw margin variances measured on IFBench and are not carried over; v2 states no transfer MDE.

Components of `batch_swap_v2_analysis.py` not ported:

- Overlap decomposition (`specificity ~ type_jaccard`): HoVer has no constraint types.
- Failure-count sensitivity (`Bprime_fail_underPB`): v2 gated B' on at least 2 of 3 examples failing under the parent; B_e here is selected by parent-score-multiset match.
- Lottery (`accept = margin_on_B > 0`): the brief's Ties section states no strict->0 accept logic in the analysis path.
- `verdict()` and the conditional interpretation cell: the brief's Phase 3 states numbers, CIs and MDEs only.
