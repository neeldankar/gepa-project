# Phase 2 Pre-registration — tractability sampler vs uniform (LOCKED)

**Locked: 2026-06-28, before any Phase-2 run.** No endpoint, test, or decision rule below may be
changed after seeing results. Any post-hoc analysis is a SEPARATE, newly pre-registered follow-up.

## Hypothesis
A tractability-weighted minibatch sampler (oversampling feedback examples whose constraint-TYPE
composition is more tractable, per the Phase-1 survivor `constraint_tractability`) produces a better
generalizing prompt than the default uniform `EpochShuffledBatchSampler`, at fixed budget.

## Design
Paired A/B. For each seed, run two GEPA optimizations identical in everything EXCEPT the minibatch
sampler:
- **uniform** arm: default `EpochShuffledBatchSampler` (`reflection_minibatch_size=3`).
- **tractability** arm: `TractabilitySampler` — per-example weight `w(e) = mean over c in
  e.instruction_id_list of (1 - failrate(type(c)))`, fail-rates FROZEN from the baseline corpus
  (Phase-1 `partial_diag`); `b=3` weighted-without-replacement, rng seeded from the run seed.
- Held constant: task LM `gpt-4.1-mini`, reflection LM `gpt-4.1`, `load_faithful_splits()`
  (150/150, split seed 0), `max_metric_calls=2500`, seed candidate, `optimize(seed=...)`.
- Both arms run FRESH this session under `scripts/run_phase2.py`.

## Primary endpoint
**Best held-out OOD test U.** For each run: take the best candidate program (`GEPAResult.best_idx`),
generate task-LM responses on the **300 IFBench OOD test prompts** (`allenai/if_bench_test`, scored
with `registry="ifbench"` — constraint types disjoint from the train set), and compute
`test_U = mean over the 300 instances of the per-instance constraint-satisfaction fraction`.
(NOT pool-frontier on OOD; you deploy one prompt, not a pool.)

## Estimand
Paired per-seed difference `d_s = test_U(tractability, s) - test_U(uniform, s)`; report `mean_s d_s`.

## Test (pre-committed)
- **Sign-flip permutation test** (exact, 2^n) on `{d_s}`, two-sided. NOT a t-test, NOT Wald.
- Headline = **mean paired difference** + **bootstrap 95% CI over seeds** (10k resamples).
- Permutation p reported but not leaned on (8 seeds → min two-sided p ≈ 0.008; 6 → ≈ 0.031).

## Sample size
Seeds 0–7 (8 pairs) if budget allows; **minimum 6 pairs** to be decisive.

## Decision rule (pre-committed)
- `mean_s d_s > 0` AND bootstrap CI **excludes 0** → **SCOPED WIN** (targeting fixable examples
  beats uniform on OOD generalization at fixed budget).
- CI **spans 0** → **NULL**: "difficulty is hard to beat on verifiable IF"; the Phase-1 offline
  screen stands as the supporting evidence. (A clean, publishable negative.)
- `mean_s d_s < 0` AND CI excludes 0 → **REVERSE**: the curriculum hurts; report honestly.
- No subgroup re-slicing, no metric swap, no N extension after unblinding.

## Validation-first protocol
Run ONE pair (uniform seed0 + tractability seed0) + OOD eval FIRST. Confirm: both arms completed,
sidecars differ ONLY in `sampler`/`arm`, the tractability arm's sampled ids over-represent
high-weight examples, and the endpoint computes. Then run seeds 1–7.

## Artifacts
Runs: `logs/phase2/` (baseline corpus untouched). Per-run endpoint: `logs/phase2/*.oodtest.json`.
Analysis: `analysis/phase2_results.parquet`. Analysis code: `scripts/analyze_phase2.py` (no API,
reproducible from cached artifacts).
