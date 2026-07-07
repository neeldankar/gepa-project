# Batch-swap ablation (arm iv) — plan (Stage 0, $0)

**Date:** 2026-07-03 · Question: does the proposer seeing THE SPECIFIC EXAMPLES the child is gated on
produce better revisions than seeing OTHER same-run examples? Manipulates the whole per-example object
(= example identity). Neel predicts (i) > (iv). k = **3** draws/arm (Neel's choice). Frozen corpus
read-only; all writes under `analysis/ablation/`.

## Stage 0 results ($0)
- **0.1 Pairing PASS.** `batch_swap_pairing.csv`: 382 B→B′ pairs, B′ = distinct batch, same run, same
  iteration-tercile, ZERO example overlap, seed 20260703, near-uniform B′ usage (1–2×). Checks: 382/382,
  0 overlap / 0 diff-run / 0 diff-tercile.
- **0.2 Pipeline.** Both arms' objects via one fresh pipeline: `adapter.evaluate(examples, {system_prompt:
  parent}, capture_traces=True)` → `make_reflective_dataset` → `{Inputs, Generated Outputs, Feedback}`.
  Feedback == `IFConstraintEvaluator` output, **byte-identical to logged Feedback on 6/6** ($0 check);
  template byte-identical (prior Stage 0). Arms differ ONLY in which examples appear (same parent/template/
  model/day). Yesterday's reconstruct-from-logs path retired.
- **0.3 Power (k=3).** Single-draw margin var 0.0775, accept base ~0.34, disagreement 0.32. **PRIMARY
  margin MDE (n=382): k=3 → 0.033** (meets ≤0.04 with buffer; k=2 was 0.040 at the line). **SECONDARY
  accept MDE floors ~7–8pp at every k** — n=382 is the whole corpus, so ≤6pp is unachievable by draws
  (reported, not fixable). Neel chose k=3.
- **0.4 Cost.** proposer 382×6 = 2292 calls ≈ $26 + task 382×24 = 9168 ≈ $10 → **~$36** (< $60 cap).

## Stages 1–2
- **Arms** (paired by B; same parent/template/model/day; randomized call order): (i) matched — reflect on
  B's 3 fresh objects, child gated on B; (iv) swapped — reflect on B′'s 3 fresh objects (same parent),
  child gated on B. k=3 proposer draws each. Gate = child sum > parent-on-B sum (both today).
- **Analysis:** primary = paired gate-margin (i)−(iv), draw-averaged, sign-flip permutation ≥20k + 95% CI;
  secondary = accept McNemar (draw-avg ≥0.5) + per-draw; lottery replication at k=3; heterogeneity by B
  difficulty/stage (descriptive); independent 2nd-path recompute.
- **Interpretation map** (→ results.md): (i)>(iv) CI-excludes-0 → example identity causally matters, closure
  has a hole where Neel predicted; (i)≈(iv) within MDE → revisions generic at the one-step gate, selection
  closed at the root. Report CI not just verdict. Scope: one-step gate (not downstream U), IFBench
  verifiable-constraint regime only.

## Run engineering
`scripts/run_batch_swap.py`: checkpoint-resumable (append; skip batches with 6 rows on restart — no
double-pay), retry ≤3 on API error (log, never drop), $55 in-script tripwire. Launch under
`nohup caffeinate -dims`, tee `logs/batch_swap.log`, report PID. Smoke 1 batch (~$0.10) first.
