# Stage-1 HoVer baselines — plan.md (Phase-1 seed-0 measurement)

## Trainset
- Size: **100 train + 10 val** (N_TRAIN=100, N_VAL=10), imperfect-only (recall<1.0), no cycling
  (imperfect pool = 123 from grading threehop[50:294]). Config otherwise identical to the frozen
  `necrosis/` run: gpt-4.1-mini, BM25 (NUM_DOCS=10, NUM_HOPS=3), title-recall metric,
  max_metric_calls=300, seed 0.
- Exact threehop.jsonl claim ids used —
  - **train (100):** 52, 54, 55, 58, 59, 60, 63, 64, 66, 67, 69, 73, 74, 75, 76, 77, 79, 84, 85,
    86, 95, 97, 99, 101, 102, 103, 104, 114, 115, 116, 117, 118, 120, 121, 123, 124, 125, 126,
    130, 133, 134, 136, 137, 139, 140, 141, 142, 146, 150, 152, 155, 156, 163, 166, 169, 173, 174,
    175, 181, 185, 191, 193, 194, 209, 211, 213, 214, 215, 216, 220, 221, 222, 224, 225, 227, 228,
    230, 231, 234, 235, 237, 239, 244, 248, 250, 252, 254, 256, 262, 268, 269, 270, 271, 272, 276,
    283, 284, 290, 292, 294
  - **val (10):** 62, 92, 182, 198, 251, 257, 275, 280, 282, 289

## Measured seed-0 (real, not estimated)
- Cost: **$1.9078** (cap $5.00; tripwire not hit)
- Wall-clock: **7975.4 s = 132.9 min = 2.22 h**
- Reflection events: **32** (32 trace entries, 1:1 aligned; 11 candidates incl. seed → 10 accepts;
  task_calls=1812, reflection_calls=32)
- Persistence confirmed: per-candidate per-val-instance parent+child score vectors (11×10),
  per-iteration minibatch parent+child score vectors (32×3), 32 child-text files.

## Projection for remaining seeds (measured × N total seeds)
| N total seeds | Cost (seeds) | Wall-clock, sequential | Events |
|---|---|---|---|
| 6 | 6 × $1.9078 = **$11.45** | 6 × 2.22 h = **13.3 h** | 6 × 32 = **192** |
| 8 | 8 × $1.9078 = **$15.26** | 8 × 2.22 h = **17.7 h** | 8 × 32 = **256** |

- One-time Step-A grading (NOT ×N): **$1.0942**, 16.1 min → threehop[50:294], 245 graded, 123 imperfect.
- Stage-1 total = seeds + grading: N=6 → **$12.54**, N=8 → **$16.35** (both within the $15–50 sanity ceiling).
- Wall-clock above is sequential (measured × N). Seeds are independent and can run concurrently to
  compress wall-clock — a decision for the Phase-2 launch, not assumed here.

STOP — awaiting APPROVED
