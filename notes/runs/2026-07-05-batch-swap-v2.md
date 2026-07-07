# batch-swap-v2

- Date: 2026-07-05
- Git sha: no git
- Experiment: 2×2 reflect × gate causal test of per-example selection at the one-step acceptance gate. Pre-registration: `analysis/ablation/batch_swap_v2/plan.md` (Stage 0) + locked conditional-interpretation map in `scripts/batch_swap_v2_analysis.py:126-141`. Supersedes the aborted v1 (`analysis/ablation/batch_swap_v1_ABANDONED/`, teach-to-the-test endpoint).

## Config
- Proposer LM: openai/gpt-4.1 (base name, no snapshot), timeout=180
- Task LM: openai/gpt-4.1-mini, DefaultAdapter + IFConstraintEvaluator, timeout=180
- Dataset: IFBench faithful splits; 382 failure-matched batch pairs (B, B′) over the 8 b3 runs
- Design: 2 reflect arms (R_B, R_B′) × 2 gate targets (B, B′), K=3 draws/arm; margin = child − P_B baseline; failure-match = ≥2/3 of B′ fail under B's actual parent P_B
- Inference: within-run sign-flip permutation (20k) + run-level cluster bootstrap (8 clusters); MDE 0.033
- Seeds: pairing order seed 20260703; per-call draw seeds md5(B_id, arm, draw)
- Runtime: ~19h wall (survived laptop sleeps via detached supervisor + 180s API timeout), 0 restarts

## Result
- Pooled specificity: +0.0054, perm p=0.60, cluster-boot CI [−0.0116, +0.0242] → ≈0 (within MDE 0.033)
- Pooled transfer: −0.0011, perm p=0.93, cluster-boot CI [−0.0243, +0.0228] → ≈0
- Overlap decomp: specificity ~ jaccard slope +0.069, predicted@jac=1 +0.051 (off a ≈0 base — not meaningful)
- Failure-count: B′_fail=2 n=20 mean +0.077; B′_fail=3 n=362 mean +0.0015
- Lottery: within-arm accept disagreement across draws = 0.382 (n=764; ↑ vs prior 0.32)
- Independent 2nd-path recompute matches to 1e-9
- Cost: $38.74 (proposer $22.72 + task $16.03); cap $55

## Takeaway
Both specificity and transfer are ≈0 within MDE — the per-example selection channel is causally inert at the one-step gate even for the same example (pre-registered "strongest Claim A"); scope: one-step gate ≠ downstream U, IFBench verifiable-SI only.
