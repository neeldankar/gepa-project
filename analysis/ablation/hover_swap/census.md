# Stage-2 HoVer batch-swap — Phase 0 census (raw facts, no interpretation)

- Source: frozen `scratch/hover_stage1/` (8 seeds). Event keying: child-bearing `full_program_trace` entries (== `reflections.json` == manifest); trace indices NOT used.
- Estimand/design ports IFBench batch-swap v2; pairing adapted to HoVer failure-profile match.

## Usable events per seed (parent scores present + >=1 child)

| seed | usable events | manifest |
|---|---|---|
| 0 | 32 | 32 |
| 1 | 34 | 34 |
| 2 | 28 | 28 |
| 3 | 33 | 33 |
| 4 | 27 | 27 |
| 5 | 34 | 34 |
| 6 | 28 | 28 |
| 7 | 27 | 27 |
| **total** | **243** | **243** |

- Total usable pairs (one A_e vs B_e per event): **243**

## Integrity (all must be 0)

- out_of_range_ids: 0
- missing_fields: 0
- draw_A_e_collision: 0
- wrong_event_count: 0

## Pairing plan (dry-run, $0 — no API)

- 243 rows in `pairing_plan.jsonl`. Per event: RNG seed = `1_000_000*seed + trace_i`; M=6 candidate positions drawn without replacement from the 100-claim trainset excluding A_e's 3 positions.
- Each row: `seed, trace_i, A_e_pos, A_e_threehop_ids, A_e_parent_scores, parent_candidate_idx, ev_rng_seed, draw6_pos, draw6_threehop_ids`.
- Matched-batch SELECTION (pick 3 of 6 by parent-score-multiset match) is deferred to Phase 1 (requires running the parent on the 6 candidates).

## Tie shares — parent minibatch (A_e) per-example scores

- N = 729 scores (243 events x 3). Metric grid {0, 1/3, 2/3, 1}.

| score | count | share |
|---|---|---|
| 0 | 31 | 4.3% |
| 0.333 | 235 | 32.2% |
| 0.667 | 327 | 44.9% |
| 1 | 136 | 18.7% |

- share exactly 0: 4.3%
- all-3-equal (tied) minibatches: 32/243 (13.2%)

## Parent-score multisets (failure-match feasibility, raw counts)

- 15 distinct multisets across 243 events.

| multiset | count |
|---|---|
| (0.333, 0.667, 0.667) | 41 |
| (0.333, 0.667, 1) | 36 |
| (0.333, 0.333, 0.667) | 34 |
| (0.667, 0.667, 1) | 29 |
| (0.667, 0.667, 0.667) | 25 |
| (0.333, 0.333, 1) | 20 |
| (0, 0.333, 0.667) | 14 |
| (0.667, 1, 1) | 12 |
| (0.333, 1, 1) | 9 |
| (0.333, 0.333, 0.333) | 7 |
| (0, 0.667, 0.667) | 6 |
| (0, 0.667, 1) | 4 |
| (0, 0.333, 1) | 4 |
| (0, 0.333, 0.333) | 1 |
| (0, 0, 1) | 1 |
