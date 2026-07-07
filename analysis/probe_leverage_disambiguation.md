# Probe — leverage disambiguation (stability × difficulty-residual)

Offline, $0. Characterizes the OBSERVED uniform-sampled matrix only — STABLE+BEYOND would make leverage a CANDIDATE ex-ante feature, NOT proof a non-uniform sampler beats uniform (still a live test).

## Cell: **STABLE × DIFFICULTY-IN-DISGUISE** → EXPLAINED AWAY but ex-ante identifiable — stable, yet it IS difficulty (the prior null covers it)

## Part 1 — stability
- Mean pairwise cross-run Spearman = **0.689** (sd 0.088); observed at **100th pct** of the within-run permutation null.
- ICC(1) = **0.810** (between-example/stable fraction of leverage variance).
- Top-decile mean pairwise Jaccard = **0.550** (100th pct of null); examples top-decile in ≥5 runs: 13, in ≥8 runs: 10.
- **Verdict: STABLE.** The high-leverage set is the same examples across runs (intrinsic).

## Part 2 — novelty vs difficulty (run fixed effects)
- Stagewise R²: runFE 0.00 → +mean-quadratic 0.06 → +variance **0.95** → +peakedness 0.95.
- **Residual R² (unexplained) = 0.055** → **DIFFICULTY-IN-DISGUISE**.
- **Centering caveat:** leverage was computed on column-CENTERED M, so it loads on cross-candidate SPREAD; the variance control (stage ii) is therefore near-definitional — most of the explained variance is leverage's own spread, so 'difficulty-in-disguise' here means *leverage ≈ cross-candidate disagreement (the swingable-cell signal)*, which is a semantic, not purely empirical, identity.

## Part 3 — actionability (LORO)
- LORO mean AUC predicting held-out top-decile leverage from the other 9 runs: **raw 0.965**, **residual 0.636**.
- Raw leverage is ex-ante identifiable; the non-difficulty residual is partly identifiable.

## Bottom line
**STABLE × DIFFICULTY-IN-DISGUISE → EXPLAINED AWAY but ex-ante identifiable — stable, yet it IS difficulty (the prior null covers it).** Leverage is a stable, ex-ante-identifiable property of specific valset examples, but under the centered definition it is largely cross-candidate disagreement (difficulty-flavored); the genuinely NEW (non-difficulty) part is weak/not ex-ante identifiable (residual LORO AUC 0.64). This is a candidate ex-ante feature to consider, NOT proof a sampler wins — that stays the live test.
