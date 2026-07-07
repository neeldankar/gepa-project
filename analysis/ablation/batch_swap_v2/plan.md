# Batch-swap v2 — Stage 0 ($0) results

**Date:** 2026-07-02 · $0 read-only. Frozen corpus untouched. Writes under `analysis/ablation/batch_swap_v2/`.

## 0.1 Pairing + PROJECTED failure-match
- per-example corpus fail-propensity: mean **0.72**, frac>0.5 = 0.73
- eligible B (>=2 of B''s examples projected-fail): **382/382**, drops **0**
- B' reuse min/mean/max = 1/1.2/2
- NOTE: proxy only; the PAID run re-verifies ≥2 fails under B's ACTUAL parent, caches (parent,example) scores, and may reassign/drop (reported there).

## 0.2 Overlap leverage (constraint-type Jaccard B,B')
- mean 0.33, median 0.30, p10 0.12, p90 0.50, frac>0.8 0.00 → **usable spread**

## 0.3 Cost (rates $0.011/proposer, $0.001/task)
- pairs 382 | proposer 1528 ($16.8) | task 12606 ($12.6) | **total ~$29** (STOP $60, tripwire $55)

## 0.4 Power — pooled specificity MDE (k draw-avg, run-clustered; 8 clusters)
- k=2 ρ=0.00 DEFF=1.0: MDE=0.040 [<=0.04 OK]
- k=2 ρ=0.05 DEFF=3.3: MDE=0.073 [MISS]
- k=2 ρ=0.15 DEFF=8.0: MDE=0.113 [MISS]
- k=3 ρ=0.00 DEFF=1.0: MDE=0.033 [<=0.04 OK]
- k=3 ρ=0.05 DEFF=3.3: MDE=0.060 [MISS]
- k=3 ρ=0.15 DEFF=8.0: MDE=0.092 [MISS]
- specificity is a WITHIN-B child difference → run/batch structure cancels → ICC≈0 expected; adding draws does NOT fix clustering (only differencing does). Transfer (single margin) is wider.

## 0.5 Runtime
- ~75s/pair × 382 → **ETA ~8.0h** (<12h; caffeinate -dims, tee log).

Recommended **k=3**. Pairing projection → `analysis/ablation/batch_swap_v2/pairing_projection.csv`.

**AWAITING APPROVED_V2** — no paid work runs until Neel creates `analysis/ablation/APPROVED_V2`.

## 0.6 Post-run reconciliation (added 2026-07-06)

- Projected (§0.3 / §0.5): **~$29 / ~8.0h**.
- Actual: **$38.74 / ~14h** (cost breakdown `notes/runs/2026-07-05-batch-swap-v2.md`).
- Cause: point-sample calibration (§0.3 rates and §0.5 ~75s/pair were single-point estimates, not a measured 5-unit smoke).
- Original §0.3 / §0.5 projections above are left unaltered.
