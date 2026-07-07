# Phase 1.6 — Integrity checks on the survivor (constraint_tractability)

Offline, $0, no API. Target = LOO unique contribution, partial-Spearman residualizing ['difficulty', 'n2_peakedness', 'parent_dpareto', 'iteration'], b3 pooled (n=382). Adversarial toward the survivor.

## Verdict A — permutation-MAX null (winner's-curse)
- Variants entering the max: **M = 43** (12 base × mean/sum + 7 coverage-matcher + 12 typicality). Real max = **0.172** (constraint_tractability_mean).
- Permutation-max null (3000 perms of LOO labels, scorers+controls fixed): mean 0.080, **p95 0.138, p99 0.167**.
- Survivor 0.172 → permutation-max **p = 0.0077**; clears the 99th percentile. Runner-up 0.115 sits **below** p95 (within best-of-M noise).
- **PASS**: 0.172 beats multiplicity-corrected chance; the cliff is not winner's curse. (Notably the runner-up does NOT — consistent with the audit's sparsity/dead verdicts.)

## Verdict B — richer & cross-fit difficulty
- Baseline partial-LOO | 4 controls = **0.172**.
- Per-type fail-rate + n_failed control: R²(scorer ~ control) = **1.000** → partial collapses to **-0.039**. This is an ALGEBRAIC IDENTITY (tractability_mean = mean n_failed − mean Σfailrate), i.e. definitional, NOT empirical evidence — controlling for a quantity that exactly contains the scorer trivially zeroes it.
- Richer OBSERVED difficulty (min/max/std/mean of minibatch scores — non-circular): partial = **0.169** (LORO 0.184±0.165). Essentially unchanged from baseline.
- Cross-fit (LORO) observed-difficulty control: partial = **0.191**.
- **Interpretation**: the survivor is **NOT observed-difficulty-in-disguise** — it survives every richer/cross-fit OBSERVED difficulty control nearly unchanged. It collapses ONLY under the per-type fail-rate control it is *built from* (R²=1.0), which is definitional: tractability's signal **IS the failed-constraint-type composition** (equivalently per-type EXPECTED difficulty). Count stays **1** by the non-circular test; the reviewer's 'it's per-type difficulty' is literally true but is a statement about what the signal *is*, not evidence that it is spurious.

## Verdict C — offline-screen bias + swingable diagnostic
- **Stated limitation**: LOO-contribution is computed on the UNIFORM run's final pool, so the screen can only reward ranking the examples that produced non-fungible children *under uniform draws* — agreement-with-realized-under-uniform-value, itself headroom-correlated. A scorer that would CREATE non-fungibility in a region uniform never explored scores ~0. This is a property of offline-correlational-structure-on-uniform-logs, **NOT of selection-in-deployment** — only the live Phase-2 A/B can earn the deployment claim.
- Only **19.6%** of b3 batches have LOO>0 (valset swingable cells = 14%); the screen is structurally mute on ~80% of batches.
- Top-decile LOO>0 fraction (enrichment over the 0.196 base rate):
  - constraint_tractability: **0.421** (2.1× base)
  - valset_prevalence: **0.342** (1.7× base)
  - coverage_gap: **0.263** (1.3× base)
  - pool_disagreement_voi: **0.184** (0.9× base)
- The survivor concentrates on the **expressible (swingable) slice** (2.1× base) — it is not structurally muzzled — whereas the dead pool_disagreement_voi sits at the base rate.

## Bottom line
**Honest surviving-scorer count = 1.** `constraint_tractability` holds up against all three objections: it beats the multiplicity-corrected permutation-max null (p=0.0077), it is not observed-difficulty-in-disguise (survives richer/cross-fit observed difficulty at ~0.17), and its top-ranked batches are enriched 2× in the slice the screen can actually score. **Caveat that does not lower the count but bounds the claim**: its signal IS the failed-type composition (per-type expected difficulty), a weak (0.172) type-level quantity — real but modest, and only the live Phase-2 test can turn it into a deployment claim. The reportable finding remains *one weak survivor*, now hardened against winner's-curse and difficulty-misspecification, with the type-composition nature stated explicitly.
