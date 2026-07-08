# Stage-2 HoVer batch-swap — plan.md (Phase-1 5-pair smoke measurement)

## Smoke config
- 5 pairs (seed, event_ordinal): (0,0), (0,1), (6,4), (4,7), (2,10). Spans both components
  (gen_query ×3, append_notes ×2), seed + non-seed parents (candidate idx 0/1/4), 4 seeds incl.
  recovered 2 & 6. Event keying verified (pair 4: ordinal 10 → trace_i 11, skips child-less i=5).
- K=3 draws/arm, M=6 failure-match draw, dspy DspyAdapter + HoverMultiHop, gpt-4.1-mini, title-recall
  metric, NUM_THREADS=4 (eval parallelism only — results thread-independent; affects wall-time only).
- Fidelity: all 10 reflect_in (5 pairs × SAME/SWAP) byte-match the frozen gepa template (10/10);
  reflection inputs built via make_reflective_dataset → prompt_renderer (never hand-assembled).

## Measured per-pair (real, from usage/cost callback + wall clock)
| pair | seed | comp | parent_idx | match | cost USD | wall s |
|---|---|---|---|---|---|---|
| 0 | 0 | gen_query | 0 | L1=1/3 | 0.2736 | 593.4 |
| 1 | 0 | append_notes | 0 | L1=2/3 | 0.2457 | 397.4 |
| 2 | 6 | append_notes | 1 | exact | 0.3284 | 505.6 |
| 3 | 4 | gen_query | 1 | exact | 0.2809 | 443.0 |
| 4 | 2 | gen_query | 4 | L1=1/3 | 0.3567 | 830.0 |
| **total** | | | | | **1.4853** | **2769.4** |

- **Mean per-pair: $0.2971 cost, 553.9 s (9.23 min) wall** (pair 0 wall includes one-time BM25 index
  load; cost has no warmup term).
- Failure-match achieved quality: **2/5 exact multiset (40%)**, 3/5 min-L1 fallback (L1 ∈ {1/3, 2/3}).

## Projections (measured × N)
| target | pairs | cost (× $0.2971) | wall, sequential @4thr (× 553.9 s) |
|---|---|---|---|
| Full census | 243 | **$72.19** | 37.4 h |
| Stratified subsample | 150 | **$44.56** | 23.1 h |

- **Full 243 projects to $72.19, which EXCEEDS the $60 tripwire** (and approaches the $75 hard cap) — a
  Phase-2 full run would halt at the tripwire mid-corpus. Per the pre-registered rule, this activates
  the **150-pair seed-stratified RNG-seeded subsample** ($44.56, under $60), allocated proportionally
  to per-seed event counts (32/34/28/33/27/34/28/27).
- Wall-time is sequential at NUM_THREADS=4; pairs are independent and can run concurrently (as the
  Stage-1 seeds did) to compress wall-clock — cost unchanged.

## Tie shares (from the smoke)
- Child per-example scores (N=180, both batches): 0→3.3%, 1/3→16.7%, 2/3→57.2%, 1→22.8%.
- Own-batch child−parent per-example deltas (N=90): exactly 0 → **54.4%**.
- (Census parent-minibatch tie shares, for reference: 0→4.3%, 1/3→32.2%, 2/3→44.9%, 1→18.7%;
  all-3-equal minibatches 13.2%.)

## Persistence (standing rule — satisfied, incl. smoke)
`smoke_draws.jsonl`: 30 rows = 5 pairs × 2 arms × 3 draws; each row carries per-example score vectors
on BOTH A_e and B_e + full child instruction text + logged A_e parent scores + fresh B_e parent
scores + match metadata. Reflection inputs in `smoke_reflect_inputs/`; per-pair meta in
`smoke_pairs_meta.json`.

STOP — awaiting APPROVED
