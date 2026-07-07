# Phase 1.5 — Scorer failure audit

Adversarial post-mortem of every failed Phase-1 scorer. Offline, $0 (TF-IDF only, no API). Target = LOO unique contribution, partial-Spearman residualizing the 4 controls ['difficulty', 'n2_peakedness', 'parent_dpareto', 'iteration'], b3 pooled. Survival bar (constraint_tractability) = partial-LOO 0.172, LORO 0.171.

## Summary table

| scorer | category | raw_loo | partial_loo | drop | contam_difficulty | loro_mean | ev_frac_zero | ev_n_distinct | defect_found | rescreen_verdict_changed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| valset_prevalence | DIFFICULTY-COLLAPSE | 0.178 | 0.049 | 0.129 | 0.659 | 0.028 | 0.237 | 39 | False | False |
| input_typicality | STRUCTURAL-DEAD | 0.019 | 0.009 | 0.01 | 0.025 | 0.003 | 0.0 | 150 | False | False |
| prevalence_x_headroom | DIFFICULTY-COLLAPSE | 0.117 | -0.032 | 0.084 | 0.666 | -0.017 | 0.244 | 343 | False | False |
| typicality_x_headroom | DIFFICULTY-COLLAPSE | 0.001 | -0.06 | -0.059 | 0.271 | -0.094 | 0.001 | 513 | False | False |
| parent_near_frontier | DIFFICULTY-COLLAPSE | 0.129 | -0.014 | 0.115 | 0.655 | -0.007 | 0.244 | 512 | False | False |
| pool_disagreement_voi | STRUCTURAL-DEAD | 0.014 | 0.025 | -0.01 | -0.036 | 0.03 | 0.0 | 1057 | False | False |
| coverage_gap | DIFFICULTY-COLLAPSE | 0.168 | 0.051 | 0.117 | 0.478 | 0.101 | 0.229 | 14 | True | False |
| coverage_gap_x_prevalence | DIFFICULTY-COLLAPSE | 0.077 | 0.017 | 0.06 | 0.184 | 0.084 | 0.677 | 29 | True | False |
| seed_to_parent_regression | SPARSITY-ARTIFACT | 0.1 | 0.115 | -0.015 | 0.036 | 0.267 | 0.995 | 2 | False | False |
| output_repairability | THRESHOLD-SENSITIVE | 0.054 | 0.035 | 0.019 | 0.05 | 0.013 | 0.0 | 187 | True | False |
| output_n_words | STRUCTURAL-DEAD | 0.085 | 0.061 | 0.024 | 0.078 | 0.062 | 0.0 | 442 | False | False |

## Failure categories

- **CORRECTLY DEAD** (structural or difficulty-collapse, not re-screened): 9 — valset_prevalence, input_typicality, prevalence_x_headroom, typicality_x_headroom, parent_near_frontier, pool_disagreement_voi, coverage_gap, coverage_gap_x_prevalence, output_n_words
- **SPARSITY-ARTIFACT** (data limitation, not a real failure): 1 — seed_to_parent_regression
- **IMPLEMENTATION-DEFECT / THRESHOLD-SENSITIVE that crosses the bar after a fix**: 0 — NONE
- **Batch scorers (coherent-gap, complementary-SI): NOT BUILT in Phase 1** (only a docstring note in scorers_wave3.py) — nothing to post-mortem.

## Defects found (real, but none revive across the bar)

- **coverage_gap matcher** — coarse keyword matcher with false-PRESENTs (generic tokens, wrong-direction cues). Hand-audit on 16 distinct (prompt,type) pairs + re-screen with tightened-keyword and TF-IDF-embedding matchers (5 thresholds): best partial-LOO 0.073, still < bar, LORO unstable, and contamination RISES as the matcher improves. The evolved system prompts are generic meta-instructions enumerating nearly all constraint categories, so type-coverage is near-constant per type -> coverage_gap is collinear with type/difficulty. Root cause = DIFFICULTY-COLLAPSE, not the matcher.
- **output_repairability composite** — arbitrary constants; raw n_words is a better feature (0.061 vs 0.035) but still sub-bar.

## Per-scorer notes

- **valset_prevalence** [DIFFICULTY-COLLAPSE] — raw 0.178->partial 0.049; contam_diff 0.659. Prevalence per se is difficulty-shadowed.
- **input_typicality** [STRUCTURAL-DEAD] — TF-IDF fallback confirmed; swept k+backend, max partial 0.030 (char k20). Embedding choice irrelevant -> robustly dead. Neural embedder untestable offline (low-priority enrichment).
- **prevalence_x_headroom** [DIFFICULTY-COLLAPSE] — contam_diff 0.666; raw 0.117->partial -0.032. Headroom injected difficulty -> WORSE than clean prevalence (0.049).
- **typicality_x_headroom** [DIFFICULTY-COLLAPSE] — contam_diff 0.271; raw 0.001->partial -0.060. Headroom term added difficulty to a no-signal base.
- **parent_near_frontier** [DIFFICULTY-COLLAPSE] — raw 0.129->partial -0.014; contam_diff 0.655. Opportunity weighting collapses to difficulty.
- **pool_disagreement_voi** [STRUCTURAL-DEAD] — Full variance (1057 distinct), contam 0.052. partial|peakedness-alone 0.017, |full 0.025. Peakedness IS a control; genuinely no signal, NOT under-credited.
- **coverage_gap** [DIFFICULTY-COLLAPSE] — Hand-audit: matcher coarse (false-PRESENTs via generic/wrong-direction cues). Re-screen with better matchers: best partial 0.073 (<0.172), LORO unstable; contamination RISES with better matchers (0.48->0.75). Matcher defect real but not the cause -> root cause difficulty. Prompts are generic meta-instructions, so type-coverage is near-constant per type.
- **coverage_gap_x_prevalence** [DIFFICULTY-COLLAPSE] — 68% zero (ABSENT-and-high-prevalence intersection is rare). Inherits coverage_gap's matcher; partial 0.017. Correctly dead.
- **seed_to_parent_regression** [SPARSITY-ARTIFACT] — 99.5% zero at event level; only 6/382 b3 batches nonzero. Where it fires it is CLEAN (contam 0.036). Not a real failure - a data limitation. Revival: dense seed-eval logging (eval the seed on ALL trainset examples) or more runs.
- **output_repairability** [THRESHOLD-SENSITIVE] — Arbitrary composite (120-word cap, structure weights). Raw n_words variant (0.061) beats composite (0.035) but both <0.172 and LORO-unstable. Fix doesn't revive.
- **output_n_words** [STRUCTURAL-DEAD] — Cleanest failure: partial 0.061, contam 0.078, but LORO 0.062+-0.113 (unstable) and far below bar. Weak real signal, sub-threshold.

## Bottom line

Of the 11 built failed scorers: **9 are correctly dead** (difficulty-collapse or structural — real signal absence), **1 is a sparsity artifact** (seed_to_parent_regression: clean where it fires but ~99% degenerate; a data limitation, revivable only by denser seed-eval logging or more runs), and **0 cross the survival bar after a legitimate fix**. Two real defects exist (coverage_gap matcher; output_repairability composite) but fixing them does not revive either scorer. 
**constraint_tractability remains the sole Phase-2 candidate.** No failed scorer is rescued. The one worth revisiting *if the corpus changes* is seed_to_parent_regression — it failed for lack of data, not lack of signal.
