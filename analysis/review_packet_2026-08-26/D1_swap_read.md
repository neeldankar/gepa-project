# D1 — Stage-2 HoVer batch-swap: the map read

**This document exists so the pre-registered map and the verified numbers sit side by side, in one
place, with nothing between them.** CC assembled it and must not complete it. The verdict is Neel's.

Assembled 2026-07-09 by CC under the overnight brief. Sections 1 and 2 are quotation and verified
fact only; no interpretation appears anywhere above the VERDICT heading.

---

## 1. The pre-registered interpretation map (verbatim)

**Source:** `cc-brief-stage2-hover-swap.md`, lines 117–124
**Commit:** `5986c1e` — *"Stage-2 complete: 243/243 pairs, $74.09, hover_swap_manifest.md — pre-analysis"*
**Tag:** `stage2-pre-analysis`

This is the **only** file at that tag containing the map. Every tracked `.md` at
`stage2-pre-analysis` was searched for the map's signature line (`Specificity ≈ transfer > 0`);
`cc-brief-stage2-hover-swap.md` is the sole hit. `analysis/ablation/hover_swap/plan.md` and
`census.md` contain no map. No synthesis was required, and none was performed.

Quoted verbatim, `git show stage2-pre-analysis:cc-brief-stage2-hover-swap.md | sed -n '117,124p'`:

```
## Pre-registered interpretation map (for Neel's read, not CC's)

- Specificity > 0, transfer ≈ 0 → proposer uses batch content; revisions overfit the minibatch;
  input channel NOT inert on HoVer; IFBench null is task-scoped (generic-target confound real).
- Specificity ≈ transfer > 0 → revisions generalize; batch content matters, example identity less.
- Both ≈ 0 → the selection null replicates on an example-derived benchmark; the broad headline
  unblocks (with scope guards: one-step, K=3, this metric).
- Every cell read against its MDE; no verdict if CI spans the map boundary.
```

The map was committed **before** any Stage-2 analysis code existed. `hover_swap_analysis.py` and
`results.md` first appear at `50af605`, which is a descendant of `5986c1e`.

---

## 2. The verified numbers

Both point estimates below were **recomputed from the raw per-pair artifacts**
(`analysis/ablation/hover_swap/pairs/*/draws.jsonl`, 243 pair dirs × 6 draw rows = 1458 rows), not
read from `results.md`. They reproduce the committed values to 9 decimal places. Full derivation and
code: `notes/FREEZE.md`, Part II, Task 1.

| estimand | point | 95% CI (run cluster-boot) | MDE | SE (clustered) | perm p (within-pair) |
|---|---|---|---|---|---|
| pooled specificity | **+0.027434842** | [+0.0149, +0.0415] | 0.0191 | 0.0068 | 0.0177 |
| pooled transfer | **+0.016918153** | [−0.0040, +0.0367] | 0.0293 | 0.0104 | 0.3120 |

Units: title-recall score points. Per-example scores lie in {0, 1/3, 2/3, 1}; a margin is the sum
over the 3 batch examples (range [−3, +3]), divided by 3 to return to score points.

MDE convention: `MDE = Z80 × SE_clustered`, `Z80 = 2.802` (`hover_swap_analysis.py:37`, carried
verbatim from `batch_swap_v2_stage0.py:36`).

Corpus: 8 seeds, 243 reflection events, per-seed pairs
`{0:32, 1:34, 2:28, 3:33, 4:27, 5:34, 6:28, 7:27}`, K=3 draws per arm.

Standing caveat, carried: the 8-cluster bootstrap runs **anti-conservative**. It attaches to the CI
leg of every read below.

### 2b. What the two quantities operationally are

This is the definition the external review demanded (R4) and CC verified in code
(`analysis/ablation/hover_swap/hover_swap_analysis.py:125–132`). It is a fact about the estimator,
not a reading of it.

**Specificity** compares SAME-arm children (reflection input built from the parent executing on the
event's own batch `A_e`) against SWAP-arm children (reflection input built from the parent executing
on the failure-matched batch `B_e`). Each child is scored on **both** 3-example batches, and the
statistic is symmetrized:

```python
spec.append((((mA_SAME - mA_SWAP) + (mB_SWAP - mB_SAME)) / 2) / 3.0)   # :131
```

Component A is evaluated on `A_e`; component B on `B_e`. On any single batch both arms share the
same parent baseline, so the baseline cancels (verified: max |diff| = 2.22e-16).

**Transfer** is the child's improvement over the parent measured on **the batch its reflection input
never saw** — SAME-arm children scored on `B_e`, SWAP-arm children scored on `A_e`:

```python
transf.append(((mB_SAME + mA_SWAP) / 2) / 3.0)                          # :132
```

**Both quantities are evaluated on the two 3-example minibatches themselves.** Neither touches the
valset, `D_pareto`, a held-out slice, or the test split. Whatever the map yields, it is a statement
about one-step minibatch margins, not about downstream utility.

Per-event unit: one reflection event (one pair) contributes one scalar to each. Pooling is an
unweighted mean over the 243 per-pair values (`obs = x.mean()`, `:92`); clustering enters the CI
only, never the point estimate.

### 2c. Two structural facts the map's own rules make load-bearing

Stated because the map says *"Every cell read against its MDE; no verdict if CI spans the map
boundary."* Whether either constitutes a boundary span is the read, and the read is Neel's.

1. Specificity's CI lower bound (**+0.0149**) sits **below** its MDE (**0.0191**).
2. Transfer's CI (**[−0.0040, +0.0367]**) **spans 0**, and its point estimate (+0.0169) sits below
   its MDE (0.0293).

Also carried from the screen, since it bears on how "transfer ≈ 0" may be read: the rank-based
robustness channel (within-run Spearman, Fisher-z pooled) backs nothing at p < 0.05.

---

## VERDICT (Neel only — CC must not fill this)

<!--
Which map cell do the numbers land in? Or does a CI span a boundary, in which case the map's own
rule returns: no verdict.

Leave this comment in place. Write below it.
-->

Verdict: cell 1. Specificity is positive: point +0.0274, 95% CI [+0.0149, +0.0415],
excludes zero. The lower bound sits just under the MDE (0.0191), which caps how large
I claim the effect is but does not change the sign; the map's decision boundary is
zero and the CI clears it. Transfer is unresolved: CI [-0.0040, +0.0367] spans zero,
no positive verdict, point estimate below its MDE. Reading: the reflection input
channel is causally active on HoVer; the IFBench null was task-scoped, not
GEPA-general; the generic-target confound was real. Overfit vs generalize is not yet
distinguished; the spec-transfer difference is the next read. Scope: one-step, K=3,
own-batch specificity, 8-cluster bootstrap anti-conservative.

[Provenance: verdict text drafted by Desktop Claude, approved verbatim by Neel in
chat, written to file by CC on Neel's explicit override instruction, 2026-07-20. The
Neel-only writing convention was overridden for this entry at Neel's direction.]
