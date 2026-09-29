# Manipulation check: did arms T and C realize different treatments? (2026-09-28)

Numbers only, no verdicts. Everything here is computed from the **realized live-run logs**:
`analysis/state_dep/runs/{T,C}_seed{0..7}/event_log.json`, read directly. Nothing comes from
`dose.json`, which is the pre-experiment swap corpus (`review_response_2026-08-26/01_degeneracy_realized.md:7-16`).
Cross-checks use `sampler_draws.json`, `gepa_result.json` (`full_program_trace`) and `run_summary.json` in
the same run directories. All computation was stdin-only Python under
`analysis/state_dep/.venv-armT/bin/python`, with nothing written except this file. Headline
statistics were computed by two independent paths and asserted equal to 1e-12, or asserted against a
second log source where one exists.

Every value below is **computed here** from committed run logs. **None is in a committed analysis artifact yet.**

---

## 1. Repository state

`git status --short` before this file was created:
```
?? analysis/WEBSITE-2026-09-28.md
```
That is the previous task's uncommitted synthesis. HEAD is `f6ae525`. All run logs read here are committed.

---

## 2. Data and integrity

| arm | events | per seed 0..7 | rules |
|---|---|---|---|
| T | 187 | 23, 22, 23, 26, 23, 25, 23, 22 | 179 `top3_by_knn_emb_fb`, 8 `coldstart_random3` |
| C | 208 | 27, 30, 27, 25, 23, 26, 25, 25 | 200 `uniform_random3`, 8 `coldstart_random3` |

Each `event_log.json` event carries `drawn_ids` (6, in draw order), `chosen_slots`, `chosen_ids`,
`novelties` (6), `drawn_scores`, `chosen_scores`, `child_scores`, `rule` and `selection`. Arm B's
`event_log.json` is empty; B has no draw-6 step.

**Terminology.** `novelties[j]` is the **per-member** k-NN score of drawn example j: the mean
(1 − cosine) to the 3 nearest strictly-prior archive feedback blocks of that run. `knn_emb_fb_min` is the
**batch** aggregate, i.e. the min over members (`batch_min`, `analysis/state_dep/novelty.py:96`). The
logged `novelty_min_chosen` equals `min(novelties[chosen_slots])` in 379/379 non-cold-start events. The
per-event appendix (§8) gives all 6 per-member scores. The chosen batch's `knn_emb_fb_min` is the min
over its 3 chosen slots.

**Integrity checks (all pass):**
- `event_log.drawn_ids` == `sampler_draws.json` ids == trace `statedep_drawn_ids`, for all 395 events.
- `chosen_ids == drawn_ids[chosen_slots]` for all 395. Trace `subsample_ids` == `chosen_ids`, and trace
  `statedep_novelties` == `novelties` (to 1e-12), for all 395.
- Every sampler iteration is an event (sampler draw count == event count in all 16 runs), so no draw was
  skipped out of the log.
- **T selected its own novelty top-3 in 179/179 non-cold-start events.** 176 match plain index order. The
  other 3 (T_seed0 i17, T_seed1 i17, T_seed5 i17) are boundary ties broken by the seeded `tiebreak_rng`
  per the design's cascade (`novelty.py:119-136`, `selection.tie_at_boundary = True`). A 4th boundary
  tie (T_seed7 i17) resolved to index order.
- **Padding duplicates.** At iteration 17 (the last draw of epoch 1) every T and C run's draw contains 2
  repeated ids. This is `EpochShuffledBatchSampler` padding 100 ids to 102
  (`.venv-armT/.../gepa/strategies/batch_sampler.py:50-56`; `sampler.py:10-15`). Some picks
  took the same example twice: T_seed2 `[46, 11, 11]`, T_seed6 `[97, 62, 62]`, C_seed0 `[53, 97, 53]`,
  C_seed4 `[50, 13, 13]`, C_seed7 `[6, 19, 19]`. Overlaps below are computed on **slots**, so a duplicated
  id is not double-counted or collapsed.

---

## 3. Primary: T-vs-C overlap on matched draws

### 3.1 Why draws can be matched, and when they stop

- The 6-id draw comes from gepa's **shared** `random.Random(seed)` through `EpochShuffledBatchSampler`
  (`run_state_dep.py:232, 256`). At b = 6 an epoch is 17 draws, and the reshuffle happens at state.i = 17,
  i.e. iteration 18 (`sampler.py:14-15`). Within an epoch the draw at an iteration is a fixed slice of
  that epoch's permutation.
- C's pick uses its own stream `random.Random(f"{seed}|C|pick")`. The event-1 pick of both arms uses the
  shared cold-start stream `random.Random(f"{seed}|coldstart")` (`proposer.py:96-99, 278-287`), so
  **event 1 is identical in T and C by design**.
- `sampler.py:23` states "T vs C are unaffected: both draw 6, so they consume this stream identically."
  The same shared stream also drives the Pareto parent selector (`ParetoCandidateSelector(rng=rng)`,
  `run_state_dep.py:267`), whose consumption depends on each arm's candidate pool.

**Measured, per seed** (`sampler_draws.json`, T vs C, ordered 6-id lists compared by iteration):

| seed | identical draws at iterations | T iterations not matched | C iterations not matched |
|---|---|---|---|
| 0 | 1–17 | 18–23 | 18–27 |
| 1 | **1–22 (all of T's run)** | none | 23–30 (past T's last) |
| 2 | 1–17 | 18–23 | 18–27 |
| 3 | 1–17 | 18–26 | 18–25 |
| 4 | 1–17 | 18–23 | 18–23 |
| 5 | 1–17 | 18–25 | 18–26 |
| 6 | 1–17 | 18–23 | 18–25 |
| 7 | 1–17 | 18–22 | 18–25 |

- In every seed the matched iterations are contiguous from iteration 1. **In 7/8 seeds the draws
  diverge exactly at iteration 18, the epoch-2 reshuffle, and never re-match.** No iteration has the same
  set in a different order. Seed 1's epoch-2 permutation came out identical in both arms.
- The divergence point is the epoch-2 reshuffle, **not the first accept**. First accepts (state.i, T/C):
  s0 6/2, s1 2/9, s2 0/2, s3 3/4, s4 4/1, s5 0/0, s6 0/0, s7 3/5 (trace `new_program_idx`). Draws stay
  matched through all of epoch 1 regardless.

### 3.2 What "matched" does and does not hold constant

Matched draws mean the **same 6 example ids in the same order**. They do **not** mean the same parent or
the same novelty scores:
- **Parent program.** Both arms are on the seed program (candidate 0) only at: s0 i1–3; s1 i1–3, 8–9;
  s2 i1–3, 13, 15, 17 (and 19–20, unmatched); s3 i1–4 (19, 22 unmatched); s4 i1–4, 9, 14, 17;
  s5 i1, 5; s6 i1, 5; s7 i1–4, 6, 8, 11 (trace `selected_program_candidate`). Candidates ≥ 1 are
  different programs in different arms.
- **Parent scores differ even on the same program.** T_seed0 and C_seed0 at iteration 1 have the same
  seed program and the same 6 ids, but `drawn_scores` are `[0, .67, 1, .67, 1, 1]` (T) vs
  `[1, .67, .67, 1, .33, .33]` (C) (`event_log.json` event 0 of each). The task LM is temp-0 with the cache
  off, and it did not reproduce across arms.
- **Archives differ.** Each arm's archive holds the feedback of its own chosen examples, rendered from its
  own parent runs. So the `novelties` vectors of T and C differ on matched draws, including at iteration 2.

### 3.3 Overlap distribution

Overlap = number of shared **slots** between T's chosen 3 and C's chosen 3 on the same draw.

**Event 1 (cold start, identical by design):** overlap 3 in 8/8.

**Matched non-cold-start events: n = 133** (iterations 2–17 in seeds 0, 2–7 = 7 × 16; iterations 2–22
in seed 1 = 21).

| shared ids | 0 | 1 | 2 | 3 | mean |
|---|---|---|---|---|---|
| **observed (n = 133)** | **6** | **59** | **61** | **7** | **1.5188** |
| reference: C uniform and independent of T (hypergeometric 1/20, 9/20, 9/20, 1/20) × 133 | 6.65 | 59.85 | 59.85 | 6.65 | 1.5 |
| subset: both arms on seed program (n = 28) | 0 | 13 | 13 | 2 | 1.6071 |
| subset: parents differ (n = 105) | 6 | 46 | 48 | 5 | 1.4952 |

Per seed (n; distribution; mean):

| seed | n | 0 / 1 / 2 / 3 | mean |
|---|---|---|---|
| 0 | 16 | 2 / 7 / 5 / 2 | 1.4375 |
| 1 | 21 | 1 / 7 / 13 / 0 | 1.5714 |
| 2 | 16 | 2 / 10 / 4 / 0 | 1.1250 |
| 3 | 16 | 0 / 6 / 9 / 1 | 1.6875 |
| 4 | 16 | 0 / 8 / 8 / 0 | 1.5000 |
| 5 | 16 | 1 / 11 / 4 / 0 | 1.1875 |
| 6 | 16 | 0 / 5 / 9 / 2 | 1.8125 |
| 7 | 16 | 0 / 5 / 9 / 2 | 1.8125 |

Overlap was computed by two implementations (set intersection on slots; membership count), which agree.

**Supplementary, same 133 matched events:** overlap of T's actual pick with the top-3 of **C's own**
novelty scores on that draw: 3 shared in **65**, 2 in 66, 1 in 2, 0 in 0. This measures how often
novelty-top-3 under C's archive and parent agrees with T's pick. It is not a property of C's realized
selection.

**Unmatched events:** 46 T events (iterations ≥ 18 in seeds 0, 2–7) and 67 C events (iterations ≥ 18
in seeds 0, 2–7, plus seed 1's iterations 23–30 past T's end). Of the C events, 22 fall past T's last
iteration (per seed: 4, 8, 4, 0, 0, 1, 2, 3). These have no T-vs-C comparison; §4 applies.

---

## 4. Within-arm fallback proxy (unmatched draws, and all events)

**As literally posed:** "how often is T's top-3-by-novelty equal to a uniformly random 3-of-6 from the
same draw". For any fixed 3-subset of 6 distinct slots, a uniform random 3-of-6 equals it with
probability exactly C(6,3)⁻¹ = **1/20 = 0.05**. That holds whatever the novelty values are, so the logs
cannot move this rate. It is stated here and **not reported as a measurement** (OQ 1).

**Variants the logs can move:**

| check | scope | realized | chance / reference | source |
|---|---|---|---|---|
| T's pick == T's own novelty top-3 (tie-aware) | 179 non-cold-start T events | **179/179** | 1/20 if T were random | event_log `novelties`, `chosen_slots` |
| same | the 46 unmatched T events | **46/46** | 1/20 | same |
| C's pick == C's own novelty top-3 | 200 non-cold-start C events | **14/200 = 0.0700** | 0.05 (exact binomial two-sided p = 0.192, descriptive) | same |
| C's pick overlap with C's own top-3: 0 / 1 / 2 / 3 | 200 | 12 / 87 / 87 / 14 | 10 / 90 / 90 / 10 | same |

**Magnitude of the manipulation (realized dose).** This is selected-min minus the expected min of a
uniformly random 3-subset (exact 20-subset enumeration), divided by the seed's within-run SD. It is the
per-event gap as `dose_compute.py` defines it, with SDs from `dose_compute.py:73-77`
(`state-dependent-design-v2.md:722-737`), and D = mean over seeds of the per-seed mean gap.

| quantity | value |
|---|---|
| **arm T realized D** (179 events) | **1.2185** (per seed 1.297, 1.160, 1.184, 1.352, 1.029, 1.178, 1.230, 1.318) |
| arm T, 46 unmatched events only: gap/SD median, mean | 0.9452, 1.0569 |
| arm C, same formula (the gap C *would* have had under top-3; C did not select on it) | 1.4223 |
| design-time D, `dose.json`, 235 events | 1.4432 (`state_dep/plan.md:347`) |

D was computed twice (numpy; pure Python) and asserted equal to 1e-12. The per-event gap distribution
for arm T also appears at `01_degeneracy_realized.md:43-44` (median 0.026193 raw, 1.047497 /SD). Those
figures are pooled over events, not averaged per seed, which is why they differ from D.

---

## 5. Within-draw novelty spread

Spread = mean of the top 3 minus mean of the bottom 3 of the 6 sorted per-member novelties, raw and ÷
within-run SD (`dose_compute.py:73-77`).

| scope | n | raw median | raw min | /SD median | /SD mean | /SD min | exact-zero events |
|---|---|---|---|---|---|---|---|
| **realized arm T** | 179 | 0.046508 | 0.006804 | **1.819848** | 1.980984 | **0.311130** | 0 |
| realized arm C | 200 | 0.061610 | 0.008029 | 2.410310 | 2.599998 | 0.367121 | 0 |
| design-time `dose.json` | 235 | 0.058594 | 0.013339 | 2.282464 | 2.357535 | 0.533328 | 0 |

- Realized arm T reproduces `01_degeneracy_realized.md:39, 42, 46` exactly. Arm C reproduces `01:67, 70, 74`.
  Design-time is from `state_dep/degeneracy_descriptive.md:30-37, 43-44` (also `01:95-98`).
- Realized arm-T /SD median is **20.3% below** design-time (1.819848 vs 2.282464). The minimum is 0.311130 vs 0.533328.
- **Design-doc citation.** `state-dependent-design-v2.md` contains **no numeric spread estimate**. It
  defines the pre-estimate as a §11-0 output, "the per-event novelty spread (max−min and SD of the 6) as
  the §15-12 degeneracy pre-estimate" (design:740-741). That output is the `dose.json` row above. The
  design's only numeric design-time expectation about selection strength is R2's ceiling argument: "under
  iid scores the top-3-of-6 min sits around one SD above a random 3-subset min … so D is realistically
  well under 1 SD" (design:772-774). Against that line: realized arm-T D = 1.2185, design-time measured
  D = 1.4432.
- Descriptive only (design §15-5 anticipates within-run decay, design:988-990). The /SD median for arm T
  is 2.0476 in epoch 1 (iterations ≤ 17, n = 128) and 1.3153 in epoch 2 (n = 51). For arm C it is 2.3209
  (n = 128) → 2.5338 (n = 72).

---

## 6. Arm C vs arm B accept rate

**Rates** (`runs/*/run_summary.json`, accepts / reflection_events; means match
`state_dep/degeneracy_descriptive.md:108-109`):

| seed | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | mean |
|---|---|---|---|---|---|---|---|---|---|
| B | .3125 | .3125 | .2286 | .3125 | .4815 | .2222 | .4138 | .4815 | 0.345631 |
| C | .2222 | .1000 | .2222 | .3200 | .3913 | .2308 | .2800 | .2800 | 0.255815 |
| C − B | −.0903 | −.2125 | −.0063 | +.0075 | −.0902 | +.0085 | −.1338 | −.2015 | −0.089816 |

Exact two-sided sign-flip p over 2^8 patterns = **0.054688**. This confirms the figure in the brief.

**What the per-event logs show.** B's per-event data comes from `gepa_result.json` `full_program_trace`
(`subsample_scores` = parent on the 3, `new_subsample_scores` = child, `new_program_idx` present = accepted).
B has 250 child-bearing events plus 2 trace entries with no child (B_seed5 i28, B_seed7 i10). C has 208
and T has 187.

(a) **Headroom of the reflected 3 is the same across arms.** Parent-score sum on the 3 examples
reflected on and gated on (0–3 scale):

| arm | mean parent sum | distribution in thirds (2/3 … 8/3) | mean child sum |
|---|---|---|---|
| B | 1.8440 | 3, 13, 30, 71, 80, 41, 12 | 1.8373 |
| C | 1.8285 | 2, 10, 32, 57, 61, 40, 6 | 1.8061 |
| T | 1.8378 | 1, 8, 30, 53, 55, 30, 10 | 1.8752 |

(b) **C's random pick is unbiased relative to its own draw.** The mean parent per-example score is 0.6095
on C's chosen 3 vs 0.6066 over all 6 drawn (208 events).

(c) **The gap appears within headroom strata.** Accept rate by parent sum (n in parentheses):

| parent sum | B | C |
|---|---|---|
| 1.00 (3/3) | .615 (13) | .600 (10) |
| 1.33 (4/3) | .633 (30) | .406 (32) |
| 1.67 (5/3) | .324 (71) | .246 (57) |
| 2.00 (6/3) | .250 (80) | .197 (61) |
| 2.33 (7/3) | .244 (41) | .125 (40) |
| 2.67 (8/3) | .083 (12) | .000 (6) |

Strata with n < 10 in either arm: 2/3 (B 3/3 accepted, C 2/2).

(d) **The parent-program mix differs.** The parent is the seed program in C 78/208 = 0.375 of events
and B 42/250 = 0.168. Accept rate with a seed-program parent: C 0.333, B 0.405. With other parents:
C 0.200, B 0.322.

(e) **Acceptance rule and a float artifact.** Accept requires `new_sum > old_sum` (gepa
`core/engine.py:491-493`). In 3 events the parent and child sums are both exactly 7/3, but
`sum([1.0, 1/3, 1.0])` evaluates to 2.3333333333333335 and `sum([2/3, 2/3, 1.0])` to 2.333333333333333, so
the tie was accepted: B_seed0 i26, B_seed4 i19, C_seed3 i7 (logged verbatim at `state_dep/logs/B_seed0.log:1492`).
All other accepts match child-sum > parent-sum exactly: B 248/250, C 207/208, T 187/187.

Within these logs, the gap is **not accounted for** by the parent-score composition of the reflected 3
(a, b, c). The logs do show a different parent-program mix (d). Nothing further is claimed.

---

## 7. OPEN QUESTIONS

These are for Neel. No verdict or ledger change is made here.

1. **Item-4 proxy.** As posed it is 0.05 by construction. Are the substituted checks (T picks its own
   top-3 179/179; C hits its own top-3 14/200 = 0.070; realized D 1.2185) the intended fallback? Or did
   you mean a different quantity?
2. **Which "matched" supports the public wording?** Identical draws (133 events). Or identical draws
   *and* both arms on the seed program (28 events). Novelty vectors differ across arms in both cases,
   because parent scores and archives differ.
3. **Wording.** On matched draws the T∩C overlap distribution (6/59/61/7, mean 1.52) is what an
   independent uniform C gives (6.65/59.85/59.85/6.65, mean 1.50). T always took its own novelty top-3
   (179/179), and C hit its own top-3 at 7.0%. How should "T and C realized different treatments" be worded, and with which of these numbers?
4. **Realized dose vs planned.** Realized arm-T D is 1.2185 against the 1.4432 that fed the §11-2 gate
   (plan.md:347-349). Arithmetic only, not applied: 3 × 1.2185 × 0.0379395 / 2 = 0.06934, and the MDE of
   0.06332 is below that too. Should a realized-dose re-statement appear anywhere, or is that out of bounds post hoc?
5. **Within-run decay.** Arm-T spread falls from 2.05 (epoch 1) to 1.32 (epoch 2) /SD, while C's does
   not. Report this as the §15-5 descriptive (design:988-990)?
6. **C vs B gap.** The logs rule out reflected-3 headroom as the account (§6 a–c) and show a
   parent-program mix difference (§6 d). Leave it descriptive, or scope a follow-up?
7. **Design-time comparison.** The design doc has no numeric spread estimate, so §5 compares to
   `dose.json` (design:740-741) and quotes R2's ceiling (design:772-774). Is that the comparison you want cited?
8. **`sampler.py:23`.** Its claim that T and C consume the shared stream identically holds only through
   epoch 1. It fails in 7/8 seeds from iteration 18. Record this anywhere (design errata, ledger)?
9. **Float tie-accepts.** 3 accepts on exact 7/3 ties (§6 e). Note them anywhere?
10. **Padding duplicates at iteration 17.** Some picks took one example twice (§2). Keep, flag, or exclude these events in any reanalysis?

---

## 8. Appendix: every T and C event

Generated directly from `event_log.json`. Columns:
- `matched`: the T and C draws at this iteration are identical.
- `drawn_ids`: the 6 ids, in draw order.
- `novelties`: the per-member scores in the same order, 4 dp, `nan` at cold start.
- `chosen_slots`, `chosen_ids`.
- `batch_min`: `knn_emb_fb_min` of the chosen 3.
- `rule`.

```
arm,seed,iter,matched,drawn_ids,novelties,chosen_slots,chosen_ids,batch_min,rule
T,0,1,1,23 8 11 63 48 13,nan nan nan nan nan nan,0 1 4,23 8 48,nan,coldstart_random3
T,0,2,1,1 92 94 54 16 87,0.3783 0.2339 0.1645 0.1583 0.2151 0.2272,0 1 5,1 92 87,0.2272,top3_by_knn_emb_fb
T,0,3,1,69 41 81 2 47 88,0.1785 0.1832 0.2262 0.3250 0.1899 0.1947,2 3 5,81 2 88,0.1947,top3_by_knn_emb_fb
T,0,4,1,78 67 19 6 24 10,0.1423 0.1973 0.1766 0.1846 0.2051 0.1788,1 3 4,67 6 24,0.1846,top3_by_knn_emb_fb
T,0,5,1,73 30 22 29 84 37,0.1966 0.2165 0.1916 0.1409 0.1925 0.1729,0 1 4,73 30 84,0.1925,top3_by_knn_emb_fb
T,0,6,1,3 95 43 49 57 28,0.1628 0.1621 0.1595 0.2009 0.2807 0.1824,3 4 5,49 57 28,0.1824,top3_by_knn_emb_fb
T,0,7,1,34 75 44 14 85 72,0.2225 0.1407 0.1868 0.1421 0.1740 0.2158,0 2 5,34 44 72,0.1868,top3_by_knn_emb_fb
T,0,8,1,4 20 15 21 31 82,0.1465 0.2253 0.3498 0.1690 0.2523 0.1981,1 2 4,20 15 31,0.2253,top3_by_knn_emb_fb
T,0,9,1,59 80 89 50 52 70,0.1535 0.2837 0.1666 0.1829 0.1728 0.1431,1 3 4,80 50 52,0.1728,top3_by_knn_emb_fb
T,0,10,1,25 98 46 99 0 66,0.1614 0.2054 0.2759 0.1672 0.1355 0.2028,1 2 5,98 46 66,0.2028,top3_by_knn_emb_fb
T,0,11,1,35 58 93 7 96 56,0.1588 0.1922 0.1696 0.1388 0.1928 0.2251,1 4 5,58 96 56,0.1922,top3_by_knn_emb_fb
T,0,12,1,91 26 40 55 90 76,0.2100 0.2039 0.1936 0.1646 0.2324 0.2036,0 1 4,91 26 90,0.2039,top3_by_knn_emb_fb
T,0,13,1,71 60 42 9 83 39,0.2159 0.1315 0.1638 0.1680 0.1562 0.1714,0 3 5,71 9 39,0.1680,top3_by_knn_emb_fb
T,0,14,1,18 77 68 32 79 12,0.2083 0.1640 0.1323 0.1848 0.1420 0.2472,0 3 5,18 32 12,0.1848,top3_by_knn_emb_fb
T,0,15,1,86 36 17 64 27 74,0.1686 0.1426 0.1729 0.1282 0.1582 0.1843,0 2 5,86 17 74,0.1686,top3_by_knn_emb_fb
T,0,16,1,45 61 38 51 62 65,0.1662 0.1919 0.1342 0.2742 0.1680 0.1772,1 3 5,61 51 65,0.1772,top3_by_knn_emb_fb
T,0,17,1,33 5 53 97 97 53,0.1627 0.1510 0.1494 0.1466 0.1466 0.1494,0 1 5,33 5 53,0.1494,top3_by_knn_emb_fb
T,0,18,0,7 93 47 81 70 18,0.1294 0.1696 0.1611 0.1270 0.1403 0.1271,1 2 4,93 47 70,0.1403,top3_by_knn_emb_fb
T,0,19,0,27 96 64 8 11 80,0.1388 0.1377 0.1237 0.1117 0.1617 0.1237,0 1 4,27 96 11,0.1377,top3_by_knn_emb_fb
T,0,20,0,3 55 91 23 57 82,0.1444 0.1500 0.1789 0.1157 0.1360 0.1785,1 2 5,55 91 82,0.1500,top3_by_knn_emb_fb
T,0,21,0,37 51 20 88 6 13,0.1651 0.1453 0.1274 0.1094 0.1068 0.1531,0 1 5,37 51 13,0.1453,top3_by_knn_emb_fb
T,0,22,0,29 89 9 73 62 79,0.1158 0.1256 0.1063 0.1104 0.1624 0.1252,1 4 5,89 62 79,0.1252,top3_by_knn_emb_fb
T,0,23,0,34 59 31 33 78 90,0.1098 0.1354 0.1431 0.1016 0.1120 0.1278,1 2 5,59 31 90,0.1278,top3_by_knn_emb_fb
T,1,1,1,84 38 66 52 4 20,nan nan nan nan nan nan,0 3 5,84 52 20,nan,coldstart_random3
T,1,2,1,39 9 10 82 45 36,0.2612 0.2013 0.2196 0.2471 0.2358 0.2340,0 3 4,39 82 45,0.2358,top3_by_knn_emb_fb
T,1,3,1,50 42 98 81 67 16,0.2493 0.1758 0.3135 0.2178 0.2696 0.1949,0 2 4,50 98 67,0.2493,top3_by_knn_emb_fb
T,1,4,1,59 33 24 68 87 17,0.1720 0.1945 0.2145 0.1712 0.1866 0.2121,1 2 5,33 24 17,0.1945,top3_by_knn_emb_fb
T,1,5,1,85 5 44 91 58 80,0.1847 0.1811 0.1913 0.3139 0.2516 0.2366,3 4 5,91 58 80,0.2366,top3_by_knn_emb_fb
T,1,6,1,23 95 30 74 25 51,0.1579 0.1933 0.2022 0.2272 0.1972 0.2612,2 3 5,30 74 51,0.2022,top3_by_knn_emb_fb
T,1,7,1,31 37 47 19 88 92,0.2517 0.1821 0.1701 0.1703 0.1633 0.1881,0 1 5,31 37 92,0.1821,top3_by_knn_emb_fb
T,1,8,1,99 96 21 7 65 46,0.1726 0.2487 0.1577 0.1616 0.2030 0.2587,1 4 5,96 65 46,0.2030,top3_by_knn_emb_fb
T,1,9,1,76 11 6 41 35 53,0.2224 0.1613 0.1965 0.1981 0.1301 0.1641,0 2 3,76 6 41,0.1965,top3_by_knn_emb_fb
T,1,10,1,89 71 18 64 70 61,0.1546 0.3172 0.2470 0.1667 0.1745 0.2567,1 2 5,71 18 61,0.2470,top3_by_knn_emb_fb
T,1,11,1,43 14 22 79 94 56,0.1739 0.1579 0.1812 0.1476 0.1496 0.2410,0 2 5,43 22 56,0.1739,top3_by_knn_emb_fb
T,1,12,1,28 73 54 27 90 1,0.1790 0.1839 0.1517 0.1579 0.2119 0.2839,1 4 5,73 90 1,0.1839,top3_by_knn_emb_fb
T,1,13,1,69 78 2 86 40 13,0.1487 0.1538 0.2490 0.1483 0.2102 0.1363,1 2 4,78 2 40,0.1538,top3_by_knn_emb_fb
T,1,14,1,75 29 34 93 0 77,0.1593 0.1463 0.1806 0.1694 0.1220 0.1862,2 3 5,34 93 77,0.1694,top3_by_knn_emb_fb
T,1,15,1,55 49 3 62 12 26,0.1658 0.1808 0.1559 0.1746 0.2643 0.2004,1 4 5,49 12 26,0.1808,top3_by_knn_emb_fb
T,1,16,1,48 83 60 57 63 15,0.1741 0.1653 0.1484 0.2191 0.1661 0.3105,0 3 5,48 57 15,0.1741,top3_by_knn_emb_fb
T,1,17,1,32 8 97 72 72 97,0.1751 0.1778 0.1538 0.1669 0.1669 0.1538,0 1 4,32 8 72,0.1669,top3_by_knn_emb_fb
T,1,18,1,95 29 19 0 40 47,0.1781 0.1374 0.1553 0.1276 0.1322 0.1473,0 2 5,95 19 47,0.1473,top3_by_knn_emb_fb
T,1,19,1,51 34 33 76 23 61,0.1575 0.1299 0.1194 0.1364 0.1620 0.1077,0 3 4,51 76 23,0.1364,top3_by_knn_emb_fb
T,1,20,1,91 55 14 70 5 64,0.1517 0.1499 0.1487 0.1371 0.1424 0.1457,0 1 2,91 55 14,0.1487,top3_by_knn_emb_fb
T,1,21,1,74 87 2 92 90 15,0.1234 0.1585 0.1523 0.1084 0.1358 0.2145,1 2 5,87 2 15,0.1523,top3_by_knn_emb_fb
T,1,22,1,94 35 30 11 63 44,0.1375 0.1378 0.1191 0.1527 0.1511 0.1755,3 4 5,11 63 44,0.1511,top3_by_knn_emb_fb
T,2,1,1,0 93 62 78 1 51,nan nan nan nan nan nan,0 3 5,0 78 51,nan,coldstart_random3
T,2,2,1,2 6 16 19 13 24,0.3820 0.2870 0.2135 0.2765 0.2247 0.2349,0 1 3,2 6 19,0.2765,top3_by_knn_emb_fb
T,2,3,1,90 12 76 9 68 60,0.2770 0.2972 0.2966 0.1521 0.1928 0.1322,0 1 2,90 12 76,0.2770,top3_by_knn_emb_fb
T,2,4,1,5 42 7 38 70 41,0.1426 0.1929 0.1432 0.1445 0.1579 0.1974,1 4 5,42 70 41,0.1579,top3_by_knn_emb_fb
T,2,5,1,36 44 18 53 14 66,0.1600 0.1769 0.2543 0.1426 0.1435 0.1551,0 1 2,36 44 18,0.1600,top3_by_knn_emb_fb
T,2,6,1,95 72 45 89 79 87,0.1437 0.1785 0.2047 0.1272 0.1288 0.1515,1 2 5,72 45 87,0.1515,top3_by_knn_emb_fb
T,2,7,1,17 31 15 71 82 25,0.1720 0.2329 0.3462 0.2647 0.1900 0.1763,1 2 3,31 15 71,0.2329,top3_by_knn_emb_fb
T,2,8,1,98 52 49 63 37 57,0.2257 0.1532 0.1887 0.1420 0.1559 0.2280,0 2 5,98 49 57,0.1887,top3_by_knn_emb_fb
T,2,9,1,33 84 26 83 28 61,0.1433 0.1600 0.1868 0.1575 0.1499 0.2474,1 2 5,84 26 61,0.1600,top3_by_knn_emb_fb
T,2,10,1,35 43 58 23 73 92,0.1755 0.1908 0.2195 0.1709 0.1852 0.1776,1 2 4,43 58 73,0.1852,top3_by_knn_emb_fb
T,2,11,1,8 99 86 80 75 29,0.1912 0.1742 0.1345 0.2058 0.1336 0.1244,0 1 3,8 99 80,0.1742,top3_by_knn_emb_fb
T,2,12,1,30 22 96 67 54 48,0.2411 0.1502 0.2111 0.1875 0.1378 0.1512,0 2 3,30 96 67,0.1875,top3_by_knn_emb_fb
T,2,13,1,40 59 97 3 88 34,0.1890 0.1474 0.1449 0.1389 0.1302 0.2012,0 1 5,40 59 34,0.1474,top3_by_knn_emb_fb
T,2,14,1,64 56 69 47 65 50,0.1104 0.2438 0.1197 0.1556 0.1742 0.1753,1 4 5,56 65 50,0.1742,top3_by_knn_emb_fb
T,2,15,1,81 55 20 74 4 91,0.1734 0.1398 0.2034 0.1892 0.1390 0.2522,2 3 5,20 74 91,0.1892,top3_by_knn_emb_fb
T,2,16,1,27 77 32 39 85 94,0.1402 0.1511 0.1819 0.1565 0.1358 0.1220,1 2 3,77 32 39,0.1511,top3_by_knn_emb_fb
T,2,17,1,21 46 10 11 11 10,0.1413 0.2424 0.1201 0.1728 0.1728 0.1317,1 3 4,46 11 11,0.1728,top3_by_knn_emb_fb
T,2,18,0,17 93 72 8 16 64,0.1637 0.1197 0.1093 0.1171 0.1377 0.1260,0 4 5,17 16 64,0.1260,top3_by_knn_emb_fb
T,2,19,0,78 28 44 69 25 85,0.0728 0.1338 0.1080 0.1197 0.1398 0.1431,1 4 5,28 25 85,0.1338,top3_by_knn_emb_fb
T,2,20,0,5 38 81 62 71 89,0.1219 0.0939 0.1816 0.1542 0.1680 0.1189,2 3 4,81 62 71,0.1542,top3_by_knn_emb_fb
T,2,21,0,22 15 96 86 77 83,0.1478 0.2083 0.1478 0.1345 0.0975 0.1547,1 2 5,15 96 83,0.1478,top3_by_knn_emb_fb
T,2,22,0,21 60 99 42 95 61,0.1331 0.1280 0.0965 0.1007 0.1400 0.1142,0 1 4,21 60 95,0.1280,top3_by_knn_emb_fb
T,2,23,0,47 55 63 82 36 18,0.1524 0.1312 0.1253 0.1702 0.0926 0.1302,0 1 3,47 55 82,0.1312,top3_by_knn_emb_fb
T,3,1,1,35 42 62 4 90 12,nan nan nan nan nan nan,1 2 4,42 62 90,nan,coldstart_random3
T,3,2,1,0 63 65 11 81 96,0.1733 0.2064 0.2778 0.2367 0.2434 0.2841,2 4 5,65 81 96,0.2434,top3_by_knn_emb_fb
T,3,3,1,7 44 61 15 64 25,0.1732 0.2052 0.2587 0.3989 0.1685 0.2165,2 3 5,61 15 25,0.2165,top3_by_knn_emb_fb
T,3,4,1,9 53 82 57 55 52,0.2101 0.1702 0.2175 0.2616 0.1914 0.1927,0 2 3,9 82 57,0.2101,top3_by_knn_emb_fb
T,3,5,1,41 68 48 18 59 87,0.2519 0.1691 0.1978 0.2649 0.1502 0.2112,0 3 5,41 18 87,0.2112,top3_by_knn_emb_fb
T,3,6,1,30 71 10 17 73 21,0.1962 0.2421 0.1445 0.2018 0.1985 0.1630,1 3 4,71 17 73,0.1985,top3_by_knn_emb_fb
T,3,7,1,14 39 45 37 67 22,0.1473 0.1941 0.2001 0.1893 0.2153 0.1879,1 2 4,39 45 67,0.1941,top3_by_knn_emb_fb
T,3,8,1,99 84 32 26 76 40,0.1687 0.1894 0.1682 0.2178 0.2568 0.2142,3 4 5,26 76 40,0.2142,top3_by_knn_emb_fb
T,3,9,1,27 43 97 13 31 58,0.1534 0.2004 0.1596 0.1376 0.2081 0.2183,1 4 5,43 31 58,0.2004,top3_by_knn_emb_fb
T,3,10,1,2 6 23 56 72 28,0.2959 0.1818 0.1796 0.2490 0.2139 0.1722,0 3 4,2 56 72,0.2139,top3_by_knn_emb_fb
T,3,11,1,36 51 46 79 54 92,0.1938 0.2488 0.2539 0.1580 0.1726 0.1589,0 1 2,36 51 46,0.1938,top3_by_knn_emb_fb
T,3,12,1,93 34 3 38 5 20,0.1774 0.1859 0.1527 0.1317 0.1557 0.2460,0 1 5,93 34 20,0.1774,top3_by_knn_emb_fb
T,3,13,1,91 89 49 66 78 85,0.2094 0.1609 0.1958 0.1711 0.1513 0.1822,0 2 5,91 49 85,0.1822,top3_by_knn_emb_fb
T,3,14,1,19 50 83 86 98 88,0.1993 0.1949 0.1752 0.1527 0.2210 0.1490,0 1 4,19 50 98,0.1949,top3_by_knn_emb_fb
T,3,15,1,24 29 70 33 94 1,0.1584 0.1400 0.1475 0.1452 0.1451 0.2304,0 2 5,24 70 1,0.1475,top3_by_knn_emb_fb
T,3,16,1,95 8 74 80 60 77,0.1228 0.1866 0.1863 0.2058 0.1534 0.1614,1 2 3,8 74 80,0.1863,top3_by_knn_emb_fb
T,3,17,1,47 16 69 75 75 69,0.1622 0.1868 0.1303 0.1547 0.1541 0.1303,0 1 3,47 16 75,0.1547,top3_by_knn_emb_fb
T,3,18,0,22 75 11 31 85 52,0.1551 0.1004 0.1535 0.1204 0.1062 0.1580,0 2 5,22 11 52,0.1535,top3_by_knn_emb_fb
T,3,19,0,6 84 8 38 51 77,0.1742 0.1646 0.1162 0.1016 0.1188 0.1614,0 1 5,6 84 77,0.1614,top3_by_knn_emb_fb
T,3,20,0,25 19 17 50 20 78,0.1023 0.1081 0.1148 0.1255 0.1480 0.1179,3 4 5,50 20 78,0.1179,top3_by_knn_emb_fb
T,3,21,0,49 91 70 5 3 95,0.1127 0.1696 0.0912 0.1429 0.1423 0.1516,1 3 5,91 5 95,0.1429,top3_by_knn_emb_fb
T,3,22,0,54 1 60 97 48 63,0.1424 0.1401 0.1384 0.1391 0.1275 0.1445,0 1 5,54 1 63,0.1401,top3_by_knn_emb_fb
T,3,23,0,82 55 96 46 81 7,0.1224 0.1397 0.1379 0.1392 0.1195 0.1183,1 2 3,55 96 46,0.1379,top3_by_knn_emb_fb
T,3,24,0,64 68 80 47 90 79,0.1269 0.1418 0.1258 0.0932 0.1278 0.1392,1 4 5,68 90 79,0.1278,top3_by_knn_emb_fb
T,3,25,0,62 33 94 29 58 14,0.1049 0.1526 0.1084 0.1279 0.1377 0.1098,1 3 4,33 29 58,0.1279,top3_by_knn_emb_fb
T,3,26,0,45 74 93 32 39 30,0.1178 0.1343 0.0943 0.1688 0.1037 0.1685,1 3 5,74 32 30,0.1343,top3_by_knn_emb_fb
T,4,1,1,74 87 83 23 1 42,nan nan nan nan nan nan,3 4 5,23 1 42,nan,coldstart_random3
T,4,2,1,57 40 77 89 25 62,0.3270 0.3029 0.2702 0.2418 0.3060 0.2671,0 1 4,57 40 25,0.3029,top3_by_knn_emb_fb
T,4,3,1,9 41 71 69 75 97,0.2263 0.2474 0.3104 0.1857 0.1910 0.2067,0 1 2,9 41 71,0.2263,top3_by_knn_emb_fb
T,4,4,1,84 96 80 76 6 73,0.2071 0.2393 0.2888 0.2791 0.1888 0.2117,1 2 3,96 80 76,0.2393,top3_by_knn_emb_fb
T,4,5,1,4 72 85 15 20 63,0.1569 0.2506 0.1903 0.3478 0.2387 0.1691,1 3 4,72 15 20,0.2387,top3_by_knn_emb_fb
T,4,6,1,90 95 29 56 60 91,0.2444 0.1849 0.1838 0.2518 0.1809 0.2320,0 3 5,90 56 91,0.2320,top3_by_knn_emb_fb
T,4,7,1,16 67 14 10 86 44,0.2064 0.2245 0.1650 0.1995 0.1925 0.1966,0 1 3,16 67 10,0.1995,top3_by_knn_emb_fb
T,4,8,1,58 99 78 26 12 32,0.2272 0.1916 0.1569 0.2124 0.2827 0.1804,0 3 4,58 26 12,0.2124,top3_by_knn_emb_fb
T,4,9,1,48 54 45 36 18 0,0.1768 0.1843 0.2001 0.1885 0.2527 0.1339,2 3 4,45 36 18,0.1885,top3_by_knn_emb_fb
T,4,10,1,94 53 82 55 52 59,0.1712 0.1807 0.1905 0.1867 0.1727 0.1552,1 2 3,53 82 55,0.1807,top3_by_knn_emb_fb
T,4,11,1,5 17 30 65 81 31,0.1490 0.1762 0.1833 0.1839 0.1940 0.2181,3 4 5,65 81 31,0.1839,top3_by_knn_emb_fb
T,4,12,1,64 49 43 93 47 88,0.1384 0.1786 0.1994 0.1761 0.1619 0.1821,1 2 5,49 43 88,0.1786,top3_by_knn_emb_fb
T,4,13,1,39 21 24 34 79 3,0.1785 0.1571 0.1721 0.1979 0.1499 0.1552,0 2 3,39 24 34,0.1721,top3_by_knn_emb_fb
T,4,14,1,27 33 98 22 35 46,0.1576 0.1509 0.1879 0.1695 0.1604 0.2216,2 3 5,98 22 46,0.1695,top3_by_knn_emb_fb
T,4,15,1,68 66 28 7 37 70,0.1480 0.1701 0.1587 0.1345 0.1868 0.1464,1 2 4,66 28 37,0.1587,top3_by_knn_emb_fb
T,4,16,1,51 2 8 11 19 61,0.2849 0.2490 0.1693 0.1783 0.1517 0.1845,0 1 5,51 2 61,0.1845,top3_by_knn_emb_fb
T,4,17,1,50 92 13 38 38 13,0.1864 0.1662 0.1507 0.1154 0.1154 0.1526,0 1 5,50 92 13,0.1526,top3_by_knn_emb_fb
T,4,18,0,52 98 4 18 58 29,0.1601 0.1296 0.1390 0.1295 0.1440 0.1412,0 4 5,52 58 29,0.1412,top3_by_knn_emb_fb
T,4,19,0,64 39 13 22 36 46,0.1237 0.0976 0.0994 0.1076 0.1066 0.1346,0 3 5,64 22 46,0.1076,top3_by_knn_emb_fb
T,4,20,0,62 73 44 45 54 66,0.1633 0.1723 0.1652 0.1134 0.1408 0.1137,0 1 2,62 73 44,0.1633,top3_by_knn_emb_fb
T,4,21,0,15 94 77 97 6 93,0.2137 0.1454 0.1743 0.1424 0.1776 0.1244,0 2 4,15 77 6,0.1743,top3_by_knn_emb_fb
T,4,22,0,57 17 92 41 47 11,0.1299 0.1659 0.1144 0.1121 0.1602 0.1770,1 4 5,17 47 11,0.1602,top3_by_knn_emb_fb
T,4,23,0,26 19 68 89 23 61,0.1306 0.1485 0.1236 0.1286 0.1107 0.1059,0 1 3,26 19 89,0.1286,top3_by_knn_emb_fb
T,5,1,1,28 62 54 75 74 25,nan nan nan nan nan nan,0 2 3,28 54 75,nan,coldstart_random3
T,5,2,1,86 85 92 2 57 7,0.1783 0.1720 0.1994 0.3985 0.2823 0.1386,2 3 4,92 2 57,0.1994,top3_by_knn_emb_fb
T,5,3,1,81 41 96 78 51 68,0.2083 0.2202 0.2292 0.1509 0.2458 0.1800,1 2 4,41 96 51,0.2202,top3_by_knn_emb_fb
T,5,4,1,82 50 36 8 97 76,0.2081 0.2112 0.2046 0.2252 0.1836 0.2634,1 3 5,50 8 76,0.2112,top3_by_knn_emb_fb
T,5,5,1,29 53 30 5 42 99,0.1800 0.1486 0.2004 0.1668 0.1813 0.1738,0 2 4,29 30 42,0.1800,top3_by_knn_emb_fb
T,5,6,1,15 33 22 37 39 38,0.3455 0.1520 0.1941 0.1814 0.1662 0.1296,0 2 3,15 22 37,0.1814,top3_by_knn_emb_fb
T,5,7,1,64 46 21 4 66 70,0.1367 0.2532 0.1522 0.1374 0.1596 0.1368,1 2 4,46 21 66,0.1522,top3_by_knn_emb_fb
T,5,8,1,58 63 79 77 19 24,0.2222 0.1588 0.1596 0.1966 0.1554 0.1708,0 3 5,58 77 24,0.1708,top3_by_knn_emb_fb
T,5,9,1,91 44 11 61 40 43,0.2437 0.1683 0.1760 0.2173 0.2074 0.1763,0 3 4,91 61 40,0.2074,top3_by_knn_emb_fb
T,5,10,1,34 12 71 18 84 55,0.1718 0.2454 0.2454 0.3162 0.1670 0.1510,1 2 3,12 71 18,0.2454,top3_by_knn_emb_fb
T,5,11,1,10 80 72 26 65 0,0.1305 0.2677 0.1761 0.2067 0.1874 0.1338,1 3 4,80 26 65,0.1874,top3_by_knn_emb_fb
T,5,12,1,93 16 56 17 9 87,0.1484 0.1989 0.2226 0.1744 0.1890 0.1809,1 2 4,16 56 9,0.1890,top3_by_knn_emb_fb
T,5,13,1,49 23 35 52 27 1,0.1960 0.1791 0.1499 0.2025 0.1355 0.2340,0 3 5,49 52 1,0.1960,top3_by_knn_emb_fb
T,5,14,1,89 73 13 69 48 90,0.1377 0.1742 0.1468 0.1368 0.1376 0.2012,1 2 5,73 13 90,0.1468,top3_by_knn_emb_fb
T,5,15,1,60 47 14 20 6 95,0.1604 0.1806 0.1429 0.2495 0.1827 0.1735,1 3 4,47 20 6,0.1806,top3_by_knn_emb_fb
T,5,16,1,31 59 3 67 83 98,0.2290 0.1431 0.1395 0.1926 0.1621 0.1970,0 3 5,31 67 98,0.1926,top3_by_knn_emb_fb
T,5,17,1,88 45 94 32 32 94,0.1718 0.1954 0.1333 0.1597 0.1597 0.1333,0 1 4,88 45 32,0.1597,top3_by_knn_emb_fb
T,5,18,0,34 87 8 69 23 9,0.1926 0.1708 0.1258 0.1368 0.1627 0.1130,0 1 4,34 87 23,0.1627,top3_by_knn_emb_fb
T,5,19,0,20 90 27 29 16 68,0.1479 0.1278 0.1355 0.0886 0.1266 0.1512,0 2 5,20 27 68,0.1355,top3_by_knn_emb_fb
T,5,20,0,0 50 54 7 24 47,0.1203 0.1166 0.1033 0.1242 0.1070 0.1196,0 3 5,0 7 47,0.1196,top3_by_knn_emb_fb
T,5,21,0,93 63 76 13 98 80,0.1266 0.1314 0.1327 0.0986 0.1301 0.1258,1 2 4,63 76 98,0.1301,top3_by_knn_emb_fb
T,5,22,0,6 15 81 86 31 4,0.1207 0.2145 0.1531 0.1493 0.1025 0.1321,1 2 3,15 81 86,0.1493,top3_by_knn_emb_fb
T,5,23,0,58 3 51 85 30 2,0.1355 0.1199 0.1410 0.1480 0.1103 0.1442,2 3 5,51 85 2,0.1410,top3_by_knn_emb_fb
T,5,24,0,38 14 11 48 28 53,0.1056 0.1041 0.1518 0.1173 0.0963 0.1347,2 3 5,11 48 53,0.1173,top3_by_knn_emb_fb
T,5,25,0,56 12 89 17 40 78,0.1166 0.1584 0.1179 0.1600 0.1259 0.1036,1 3 4,12 17 40,0.1259,top3_by_knn_emb_fb
T,6,1,1,71 20 48 13 30 29,nan nan nan nan nan nan,1 2 5,20 48 29,nan,coldstart_random3
T,6,2,1,3 93 26 28 87 43,0.1907 0.1925 0.2116 0.2118 0.2852 0.2848,3 4 5,28 87 43,0.2118,top3_by_knn_emb_fb
T,6,3,1,14 8 21 78 9 59,0.1384 0.2208 0.1802 0.1517 0.1846 0.1639,1 2 4,8 21 9,0.1802,top3_by_knn_emb_fb
T,6,4,1,99 79 50 66 94 16,0.1929 0.1534 0.2249 0.1860 0.1556 0.2081,0 2 5,99 50 16,0.1929,top3_by_knn_emb_fb
T,6,5,1,51 6 89 95 86 45,0.2646 0.1877 0.1416 0.1708 0.1805 0.2115,0 1 5,51 6 45,0.1877,top3_by_knn_emb_fb
T,6,6,1,82 35 73 17 39 74,0.1968 0.1664 0.2144 0.1698 0.1636 0.2026,0 2 5,82 73 74,0.1968,top3_by_knn_emb_fb
T,6,7,1,76 49 63 7 85 22,0.2472 0.1944 0.1635 0.1247 0.1836 0.1870,0 1 5,76 49 22,0.1870,top3_by_knn_emb_fb
T,6,8,1,19 27 38 15 61 88,0.1611 0.1451 0.1235 0.3631 0.2255 0.1747,3 4 5,15 61 88,0.1747,top3_by_knn_emb_fb
T,6,9,1,1 55 44 58 36 81,0.3400 0.1652 0.1816 0.2355 0.1839 0.1725,0 3 4,1 58 36,0.1839,top3_by_knn_emb_fb
T,6,10,1,90 53 31 23 41 77,0.2798 0.1470 0.2324 0.1784 0.1772 0.1741,0 2 3,90 31 23,0.1784,top3_by_knn_emb_fb
T,6,11,1,64 57 65 5 67 37,0.1283 0.2247 0.1946 0.1534 0.2007 0.1703,1 2 4,57 65 67,0.1946,top3_by_knn_emb_fb
T,6,12,1,92 80 56 32 83 46,0.1700 0.2437 0.2204 0.1732 0.1468 0.2724,1 2 5,80 56 46,0.2204,top3_by_knn_emb_fb
T,6,13,1,91 42 54 11 96 70,0.2140 0.1653 0.1352 0.1645 0.2065 0.1355,0 1 4,91 42 96,0.1653,top3_by_knn_emb_fb
T,6,14,1,72 24 12 69 68 52,0.1905 0.1692 0.3111 0.1348 0.1327 0.1549,0 1 2,72 24 12,0.1692,top3_by_knn_emb_fb
T,6,15,1,25 98 34 2 40 47,0.1535 0.1980 0.1988 0.2646 0.1906 0.1792,1 2 3,98 34 2,0.1980,top3_by_knn_emb_fb
T,6,16,1,60 75 84 18 0 4,0.1388 0.1511 0.1657 0.2226 0.1274 0.1412,1 2 3,75 84 18,0.1511,top3_by_knn_emb_fb
T,6,17,1,33 97 62 10 10 62,0.1461 0.1691 0.1683 0.1373 0.1453 0.1683,1 2 5,97 62 62,0.1683,top3_by_knn_emb_fb
T,6,18,0,41 1 49 50 26 72,0.1700 0.1634 0.1234 0.1273 0.1631 0.1182,0 1 4,41 1 26,0.1631,top3_by_knn_emb_fb
T,6,19,0,19 42 39 88 6 97,0.1818 0.0959 0.1660 0.1112 0.1186 0.0776,0 2 4,19 39 6,0.1186,top3_by_knn_emb_fb
T,6,20,0,14 92 59 18 96 12,0.1331 0.1656 0.1479 0.1369 0.1444 0.1868,1 2 5,92 59 12,0.1479,top3_by_knn_emb_fb
T,6,21,0,82 44 9 86 62 22,0.1111 0.1730 0.0943 0.1406 0.0388 0.1134,1 3 5,44 86 22,0.1134,top3_by_knn_emb_fb
T,6,22,0,51 55 0 95 69 43,0.1499 0.1517 0.1113 0.1627 0.1207 0.1172,0 1 3,51 55 95,0.1499,top3_by_knn_emb_fb
T,6,23,0,32 53 31 29 73 25,0.1679 0.1458 0.1295 0.0875 0.1128 0.1476,0 1 5,32 53 25,0.1458,top3_by_knn_emb_fb
T,7,1,1,33 25 41 85 79 82,nan nan nan nan nan nan,3 4 5,85 79 82,nan,coldstart_random3
T,7,2,1,21 94 97 1 22 0,0.2078 0.1825 0.1793 0.3532 0.1737 0.1468,0 1 3,21 94 1,0.1825,top3_by_knn_emb_fb
T,7,3,1,61 73 24 49 26 44,0.2522 0.2509 0.1554 0.1985 0.2389 0.1830,0 1 4,61 73 26,0.2389,top3_by_knn_emb_fb
T,7,4,1,77 80 47 2 51 38,0.1984 0.2705 0.1705 0.3155 0.3111 0.1284,1 3 4,80 2 51,0.2705,top3_by_knn_emb_fb
T,7,5,1,14 48 10 32 16 95,0.1670 0.1783 0.1766 0.1660 0.2026 0.1753,1 2 4,48 10 16,0.1766,top3_by_knn_emb_fb
T,7,6,1,65 69 42 59 89 99,0.2038 0.1515 0.1433 0.1451 0.1251 0.1909,0 1 5,65 69 99,0.1515,top3_by_knn_emb_fb
T,7,7,1,66 92 57 29 20 88,0.1730 0.1951 0.2467 0.1280 0.1988 0.1591,1 2 4,92 57 20,0.1951,top3_by_knn_emb_fb
T,7,8,1,34 60 31 13 63 3,0.2000 0.1637 0.2284 0.1236 0.1595 0.1674,0 2 5,34 31 3,0.1674,top3_by_knn_emb_fb
T,7,9,1,56 87 45 62 58 23,0.2312 0.1716 0.1840 0.1708 0.2091 0.1646,0 2 4,56 45 58,0.1840,top3_by_knn_emb_fb
T,7,10,1,93 40 36 67 71 81,0.1483 0.2029 0.1510 0.2132 0.2885 0.1654,1 3 4,40 67 71,0.2029,top3_by_knn_emb_fb
T,7,11,1,43 52 35 39 76 18,0.1608 0.1630 0.1550 0.1662 0.2154 0.2773,3 4 5,39 76 18,0.1662,top3_by_knn_emb_fb
T,7,12,1,84 37 17 5 75 96,0.1640 0.1863 0.1683 0.1579 0.1338 0.2246,1 2 5,37 17 96,0.1683,top3_by_knn_emb_fb
T,7,13,1,98 78 91 28 15 72,0.2016 0.1278 0.2303 0.1587 0.3230 0.1942,0 2 4,98 91 15,0.2016,top3_by_knn_emb_fb
T,7,14,1,90 54 70 86 30 8,0.2115 0.1316 0.1452 0.1350 0.1654 0.1637,0 4 5,90 30 8,0.1637,top3_by_knn_emb_fb
T,7,15,1,53 55 11 4 27 64,0.1389 0.1554 0.1554 0.1552 0.1539 0.1356,1 2 3,55 11 4,0.1552,top3_by_knn_emb_fb
T,7,16,1,7 74 46 12 68 9,0.1219 0.1995 0.2263 0.2808 0.1271 0.1536,1 2 3,74 46 12,0.1995,top3_by_knn_emb_fb
T,7,17,1,6 83 50 19 19 50,0.1945 0.1487 0.1808 0.1561 0.1841 0.1808,0 2 4,6 50 19,0.1808,top3_by_knn_emb_fb
T,7,18,0,55 19 8 81 78 4,0.0963 0.1165 0.1026 0.1742 0.1413 0.0882,1 3 4,19 81 78,0.1165,top3_by_knn_emb_fb
T,7,19,0,84 32 9 88 49 53,0.1587 0.1668 0.1332 0.1276 0.1775 0.1389,0 1 4,84 32 49,0.1587,top3_by_knn_emb_fb
T,7,20,0,98 65 7 90 27 93,0.1333 0.1137 0.1208 0.1374 0.1465 0.1464,3 4 5,90 27 93,0.1374,top3_by_knn_emb_fb
T,7,21,0,34 41 15 94 36 79,0.1175 0.1765 0.2050 0.1002 0.1757 0.0946,1 2 4,41 15 36,0.1757,top3_by_knn_emb_fb
T,7,22,0,35 85 57 25 76 87,0.1461 0.0997 0.1361 0.1314 0.1165 0.1598,0 2 5,35 57 87,0.1361,top3_by_knn_emb_fb
C,0,1,1,23 8 11 63 48 13,nan nan nan nan nan nan,0 1 4,23 8 48,nan,coldstart_random3
C,0,2,1,1 92 94 54 16 87,0.3837 0.2343 0.1762 0.1823 0.2094 0.2216,0 1 5,1 92 87,0.2216,uniform_random3
C,0,3,1,69 41 81 2 47 88,0.1851 0.1857 0.2205 0.3275 0.2106 0.1994,1 4 5,41 47 88,0.1857,uniform_random3
C,0,4,1,78 67 19 6 24 10,0.1508 0.1884 0.1573 0.1579 0.1940 0.1916,1 3 4,67 6 24,0.1579,uniform_random3
C,0,5,1,73 30 22 29 84 37,0.1808 0.2170 0.1859 0.1493 0.1846 0.1839,0 1 5,73 30 37,0.1808,uniform_random3
C,0,6,1,3 95 43 49 57 28,0.1770 0.1646 0.1569 0.1889 0.2522 0.1855,0 1 4,3 95 57,0.1646,uniform_random3
C,0,7,1,34 75 44 14 85 72,0.2225 0.1450 0.1980 0.1414 0.1751 0.2325,1 3 4,75 14 85,0.1414,uniform_random3
C,0,8,1,4 20 15 21 31 82,0.1261 0.2524 0.3587 0.1757 0.2428 0.1855,0 3 5,4 21 82,0.1261,uniform_random3
C,0,9,1,59 80 89 50 52 70,0.1273 0.2925 0.1255 0.1713 0.1355 0.1433,3 4 5,50 52 70,0.1355,uniform_random3
C,0,10,1,25 98 46 99 0 66,0.1765 0.3041 0.2668 0.1537 0.1178 0.1567,1 4 5,98 0 66,0.1178,uniform_random3
C,0,11,1,35 58 93 7 96 56,0.1588 0.2250 0.1693 0.1311 0.2436 0.2221,0 2 5,35 93 56,0.1588,uniform_random3
C,0,12,1,91 26 40 55 90 76,0.2786 0.1955 0.1908 0.1361 0.2491 0.2309,1 3 5,26 55 76,0.1361,uniform_random3
C,0,13,1,71 60 42 9 83 39,0.2800 0.1339 0.1527 0.1303 0.1490 0.1528,0 2 5,71 42 39,0.1527,uniform_random3
C,0,14,1,18 77 68 32 79 12,0.2725 0.1669 0.1365 0.1733 0.1331 0.2585,2 3 5,68 32 12,0.1365,uniform_random3
C,0,15,1,86 36 17 64 27 74,0.1487 0.1229 0.1445 0.1138 0.1412 0.1388,1 4 5,36 27 74,0.1229,uniform_random3
C,0,16,1,45 61 38 51 62 65,0.1851 0.1693 0.1087 0.2858 0.1464 0.1605,2 4 5,38 62 65,0.1087,uniform_random3
C,0,17,1,33 5 53 97 97 53,0.1342 0.1215 0.1386 0.1329 0.1329 0.1386,2 4 5,53 97 53,0.1329,uniform_random3
C,0,18,0,7 23 98 79 74 82,0.1268 0.1088 0.1773 0.1223 0.1083 0.1127,0 2 3,7 98 79,0.1223,uniform_random3
C,0,19,0,90 37 46 8 95 11,0.1990 0.1115 0.2668 0.0936 0.0726 0.1478,0 3 5,90 8 11,0.0936,uniform_random3
C,0,20,0,27 3 18 29 91 93,0.0916 0.0845 0.2080 0.1161 0.2575 0.0931,1 2 4,3 18 91,0.0845,uniform_random3
C,0,21,0,92 81 34 20 73 6,0.1085 0.1745 0.1906 0.1826 0.1100 0.1074,0 4 5,92 73 6,0.1074,uniform_random3
C,0,22,0,13 80 55 50 9 51,0.1355 0.1715 0.0870 0.1117 0.1171 0.2418,0 3 4,13 50 9,0.1117,uniform_random3
C,0,23,0,97 41 62 31 33 66,0.0840 0.1075 0.0959 0.2084 0.1342 0.0915,0 3 5,97 31 66,0.0840,uniform_random3
C,0,24,0,54 67 4 64 57 47,0.1332 0.1198 0.0952 0.1138 0.1468 0.1021,2 3 5,4 64 47,0.0952,uniform_random3
C,0,25,0,77 48 89 59 25 2,0.1549 0.0831 0.1211 0.1272 0.1475 0.2582,0 2 4,77 89 25,0.1211,uniform_random3
C,0,26,0,26 75 43 68 24 28,0.1064 0.0769 0.1484 0.0714 0.0944 0.1281,0 1 3,26 75 68,0.0714,uniform_random3
C,0,27,0,40 14 99 63 21 44,0.1893 0.0744 0.1421 0.1127 0.0937 0.1509,0 3 5,40 63 44,0.1127,uniform_random3
C,1,1,1,84 38 66 52 4 20,nan nan nan nan nan nan,0 3 5,84 52 20,nan,coldstart_random3
C,1,2,1,39 9 10 82 45 36,0.2449 0.2233 0.2427 0.2631 0.2435 0.2443,0 2 3,39 10 82,0.2427,uniform_random3
C,1,3,1,50 42 98 81 67 16,0.2433 0.1530 0.2831 0.2041 0.2629 0.1887,1 2 4,42 98 67,0.1530,uniform_random3
C,1,4,1,59 33 24 68 87 17,0.1765 0.1323 0.2135 0.1912 0.1817 0.2124,0 1 3,59 33 68,0.1323,uniform_random3
C,1,5,1,85 5 44 91 58 80,0.1677 0.1780 0.1941 0.2957 0.2233 0.2289,0 1 2,85 5 44,0.1677,uniform_random3
C,1,6,1,23 95 30 74 25 51,0.1689 0.1665 0.1813 0.2381 0.1610 0.2956,0 2 5,23 30 51,0.1689,uniform_random3
C,1,7,1,31 37 47 19 88 92,0.2185 0.1846 0.1621 0.1908 0.1584 0.1773,1 2 5,37 47 92,0.1621,uniform_random3
C,1,8,1,99 96 21 7 65 46,0.1777 0.2176 0.1336 0.1409 0.1739 0.2793,0 3 4,99 7 65,0.1409,uniform_random3
C,1,9,1,76 11 6 41 35 53,0.2145 0.1703 0.1836 0.1886 0.1629 0.1441,1 3 5,11 41 53,0.1441,uniform_random3
C,1,10,1,89 71 18 64 70 61,0.1537 0.2770 0.3014 0.1189 0.1332 0.2201,0 1 2,89 71 18,0.1537,uniform_random3
C,1,11,1,43 14 22 79 94 56,0.1656 0.1284 0.1545 0.1290 0.1369 0.2285,1 3 5,14 79 56,0.1284,uniform_random3
C,1,12,1,28 73 54 27 90 1,0.1544 0.1576 0.1119 0.1383 0.2151 0.2859,1 2 4,73 54 90,0.1119,uniform_random3
C,1,13,1,69 78 2 86 40 13,0.1006 0.1167 0.3172 0.1472 0.1958 0.1413,0 2 3,69 2 86,0.1006,uniform_random3
C,1,14,1,75 29 34 93 0 77,0.1337 0.1177 0.1854 0.1281 0.1066 0.1548,0 2 5,75 34 77,0.1337,uniform_random3
C,1,15,1,55 49 3 62 12 26,0.1322 0.1508 0.1542 0.1609 0.2541 0.1808,1 3 5,49 62 26,0.1508,uniform_random3
C,1,16,1,48 83 60 57 63 15,0.1190 0.1238 0.1454 0.2165 0.1483 0.3695,0 2 3,48 60 57,0.1190,uniform_random3
C,1,17,1,32 8 97 72 72 97,0.1798 0.1531 0.1351 0.1583 0.1814 0.1351,0 1 3,32 8 72,0.1531,uniform_random3
C,1,18,1,95 29 19 0 40 47,0.1449 0.1271 0.1611 0.1065 0.1958 0.1103,1 3 5,29 0 47,0.1065,uniform_random3
C,1,19,1,51 34 33 76 23 61,0.1420 0.1210 0.0805 0.2302 0.0957 0.1735,2 3 5,33 76 61,0.0805,uniform_random3
C,1,20,1,91 55 14 70 5 64,0.2246 0.1295 0.0765 0.1351 0.0732 0.1105,1 2 3,55 14 70,0.0765,uniform_random3
C,1,21,1,74 87 2 92 90 15,0.1631 0.1523 0.2009 0.1101 0.1385 0.3331,0 2 5,74 2 15,0.1631,uniform_random3
C,1,22,1,94 35 30 11 63 44,0.1085 0.1355 0.1025 0.0995 0.1341 0.0999,1 3 4,35 11 63,0.0995,uniform_random3
C,1,23,0,26 52 17 59 56 65,0.1146 0.1009 0.1352 0.0703 0.1466 0.1066,0 2 3,26 17 59,0.0703,uniform_random3
C,1,24,0,8 96 45 89 10 46,0.0971 0.2441 0.1633 0.0803 0.0818 0.2700,3 4 5,89 10 46,0.0803,uniform_random3
C,1,25,0,49 25 75 97 69 72,0.1030 0.1376 0.0767 0.1351 0.0656 0.1307,0 1 4,49 25 69,0.0656,uniform_random3
C,1,26,0,71 18 24 42 60 31,0.1661 0.1299 0.1419 0.0736 0.0960 0.1973,2 3 4,24 42 60,0.0736,uniform_random3
C,1,27,0,62 37 93 43 36 13,0.0973 0.1053 0.1281 0.1656 0.1282 0.1234,0 3 4,62 43 36,0.0973,uniform_random3
C,1,28,0,79 22 12 48 68 21,0.0758 0.1459 0.2780 0.0779 0.0677 0.1242,0 2 4,79 12 68,0.0677,uniform_random3
C,1,29,0,58 85 4 1 81 32,0.2127 0.0914 0.1105 0.2057 0.1679 0.1171,0 1 2,58 85 4,0.0914,uniform_random3
C,1,30,0,53 20 82 78 77 9,0.0828 0.1178 0.1040 0.0974 0.1012 0.1110,0 2 5,53 82 9,0.0828,uniform_random3
C,2,1,1,0 93 62 78 1 51,nan nan nan nan nan nan,0 3 5,0 78 51,nan,coldstart_random3
C,2,2,1,2 6 16 19 13 24,0.3764 0.2994 0.2245 0.2724 0.2233 0.2337,0 3 5,2 19 24,0.2337,uniform_random3
C,2,3,1,90 12 76 9 68 60,0.2791 0.3120 0.2921 0.1531 0.1652 0.1651,1 3 5,12 9 60,0.1531,uniform_random3
C,2,4,1,5 42 7 38 70 41,0.1363 0.1470 0.1064 0.1091 0.1331 0.2021,0 2 3,5 7 38,0.1064,uniform_random3
C,2,5,1,36 44 18 53 14 66,0.1147 0.1734 0.3025 0.1368 0.1029 0.1511,3 4 5,53 14 66,0.1029,uniform_random3
C,2,6,1,95 72 45 89 79 87,0.1287 0.1740 0.1918 0.1155 0.1352 0.1522,2 3 4,45 89 79,0.1155,uniform_random3
C,2,7,1,17 31 15 71 82 25,0.1535 0.2364 0.3770 0.2711 0.1785 0.1608,0 1 5,17 31 25,0.1535,uniform_random3
C,2,8,1,98 52 49 63 37 57,0.2648 0.1705 0.1927 0.1217 0.1617 0.2224,2 3 5,49 63 57,0.1217,uniform_random3
C,2,9,1,33 84 26 83 28 61,0.1557 0.1494 0.1792 0.1531 0.1430 0.2184,0 1 3,33 84 83,0.1494,uniform_random3
C,2,10,1,35 43 58 23 73 92,0.1447 0.1759 0.1998 0.1508 0.1750 0.1727,0 3 4,35 23 73,0.1447,uniform_random3
C,2,11,1,8 99 86 80 75 29,0.1494 0.1340 0.1245 0.2501 0.1156 0.1318,2 3 5,86 80 29,0.1245,uniform_random3
C,2,12,1,30 22 96 67 54 48,0.1638 0.1368 0.2131 0.1811 0.1351 0.1303,1 3 4,22 67 54,0.1351,uniform_random3
C,2,13,1,40 59 97 3 88 34,0.1883 0.1297 0.1330 0.1211 0.1478 0.1973,0 1 2,40 59 97,0.1297,uniform_random3
C,2,14,1,64 56 69 47 65 50,0.1080 0.2185 0.1103 0.1460 0.1502 0.1828,0 2 5,64 69 50,0.1080,uniform_random3
C,2,15,1,81 55 20 74 4 91,0.1615 0.1320 0.2231 0.1554 0.1026 0.2758,3 4 5,74 4 91,0.1026,uniform_random3
C,2,16,1,27 77 32 39 85 94,0.1310 0.1662 0.1600 0.1421 0.1360 0.1088,1 4 5,77 85 94,0.1088,uniform_random3
C,2,17,1,21 46 10 11 11 10,0.1353 0.2580 0.1160 0.1701 0.1542 0.1252,0 4 5,21 11 10,0.1252,uniform_random3
C,2,18,0,5 8 16 98 96 89,0.0681 0.1494 0.1456 0.1892 0.1829 0.0758,0 1 3,5 8 98,0.0681,uniform_random3
C,2,19,0,68 28 78 58 17 69,0.1136 0.1308 0.0663 0.1969 0.0895 0.0696,0 2 5,68 78 69,0.0663,uniform_random3
C,2,20,0,25 40 57 15 55 82,0.0806 0.1224 0.1389 0.3310 0.1320 0.1629,2 3 4,57 15 55,0.1320,uniform_random3
C,2,21,0,74 61 38 76 47 53,0.1181 0.1871 0.0607 0.1869 0.1394 0.0832,0 1 4,74 61 47,0.1181,uniform_random3
C,2,22,0,51 21 80 92 39 59,0.1167 0.0884 0.1256 0.1670 0.1421 0.0663,2 4 5,80 39 59,0.0663,uniform_random3
C,2,23,0,22 18 36 7 93 50,0.0891 0.2392 0.1298 0.0763 0.1266 0.1092,0 1 2,22 18 36,0.0891,uniform_random3
C,2,24,0,81 71 6 72 44 62,0.1579 0.2620 0.1434 0.1390 0.1528 0.1459,0 1 2,81 71 6,0.1434,uniform_random3
C,2,25,0,26 63 45 37 1 84,0.1705 0.0742 0.1019 0.1474 0.2441 0.1000,0 3 4,26 37 1,0.1474,uniform_random3
C,2,26,0,77 64 85 83 48 43,0.0908 0.0712 0.0885 0.0924 0.1211 0.1560,0 1 5,77 64 43,0.0712,uniform_random3
C,2,27,0,73 24 41 34 86 60,0.1136 0.0984 0.1745 0.1806 0.0823 0.0847,1 2 5,24 41 60,0.0847,uniform_random3
C,3,1,1,35 42 62 4 90 12,nan nan nan nan nan nan,1 2 4,42 62 90,nan,coldstart_random3
C,3,2,1,0 63 65 11 81 96,0.1657 0.1983 0.2524 0.2307 0.2643 0.2962,1 4 5,63 81 96,0.1983,uniform_random3
C,3,3,1,7 44 61 15 64 25,0.1576 0.2057 0.2585 0.3935 0.1461 0.2087,0 2 5,7 61 25,0.1576,uniform_random3
C,3,4,1,9 53 82 57 55 52,0.1438 0.1682 0.2001 0.2329 0.1597 0.1835,0 2 5,9 82 52,0.1438,uniform_random3
C,3,5,1,41 68 48 18 59 87,0.2437 0.1436 0.1514 0.2638 0.1288 0.1837,1 2 5,68 48 87,0.1436,uniform_random3
C,3,6,1,30 71 10 17 73 21,0.2288 0.2670 0.1635 0.1703 0.2215 0.1630,0 1 4,30 71 73,0.2215,uniform_random3
C,3,7,1,14 39 45 37 67 22,0.1386 0.1692 0.1954 0.1878 0.2159 0.1715,0 2 5,14 45 22,0.1386,uniform_random3
C,3,8,1,99 84 32 26 76 40,0.1458 0.1566 0.1736 0.1796 0.2413 0.2036,1 2 4,84 32 76,0.1566,uniform_random3
C,3,9,1,27 43 97 13 31 58,0.1576 0.1907 0.1528 0.1629 0.2103 0.2063,1 2 5,43 97 58,0.1528,uniform_random3
C,3,10,1,2 6 23 56 72 28,0.3070 0.1819 0.1594 0.2368 0.1621 0.1498,0 1 2,2 6 23,0.1594,uniform_random3
C,3,11,1,36 51 46 79 54 92,0.1698 0.2782 0.2636 0.1366 0.1409 0.1642,1 4 5,51 54 92,0.1409,uniform_random3
C,3,12,1,93 34 3 38 5 20,0.1301 0.1801 0.1372 0.1124 0.1334 0.1899,0 1 4,93 34 5,0.1301,uniform_random3
C,3,13,1,91 89 49 66 78 85,0.2617 0.1329 0.1662 0.1708 0.1243 0.1568,0 2 5,91 49 85,0.1568,uniform_random3
C,3,14,1,19 50 83 86 98 88,0.1505 0.1917 0.1405 0.1406 0.2194 0.1537,0 4 5,19 98 88,0.1505,uniform_random3
C,3,15,1,24 29 70 33 94 1,0.1438 0.1264 0.1211 0.1557 0.1361 0.2441,0 1 5,24 29 1,0.1264,uniform_random3
C,3,16,1,95 8 74 80 60 77,0.1461 0.1837 0.1755 0.1972 0.1324 0.1850,2 4 5,74 60 77,0.1324,uniform_random3
C,3,17,1,47 16 69 75 75 69,0.1671 0.1615 0.1136 0.1315 0.1315 0.1136,1 3 5,16 75 69,0.1136,uniform_random3
C,3,18,0,49 11 84 19 6 90,0.1092 0.1420 0.1034 0.0878 0.0903 0.1491,1 2 5,11 84 90,0.1034,uniform_random3
C,3,19,0,48 46 20 26 22 88,0.0760 0.2549 0.2194 0.1691 0.1030 0.0821,0 2 4,48 20 22,0.0760,uniform_random3
C,3,20,0,8 41 58 78 69 1,0.1837 0.1730 0.1323 0.1128 0.0727 0.1500,0 3 5,8 78 1,0.1128,uniform_random3
C,3,21,0,13 17 25 70 79 38,0.1465 0.1631 0.1002 0.1205 0.1304 0.1002,0 1 4,13 17 79,0.1304,uniform_random3
C,3,22,0,62 76 5 31 81 93,0.0932 0.1538 0.0850 0.1695 0.1128 0.0793,1 2 5,76 5 93,0.0793,uniform_random3
C,3,23,0,60 3 54 61 55 36,0.0865 0.1352 0.0818 0.1142 0.1357 0.1325,0 3 4,60 61 55,0.0865,uniform_random3
C,3,24,0,50 87 7 63 85 64,0.1752 0.1012 0.0684 0.0882 0.0938 0.1119,0 1 3,50 87 63,0.0882,uniform_random3
C,3,25,0,51 96 71 18 33 42,0.1433 0.1362 0.1411 0.1848 0.1528 0.0887,0 2 4,51 71 33,0.1411,uniform_random3
C,4,1,1,74 87 83 23 1 42,nan nan nan nan nan nan,3 4 5,23 1 42,nan,coldstart_random3
C,4,2,1,57 40 77 89 25 62,0.3250 0.3037 0.2662 0.2338 0.2967 0.2660,2 3 4,77 89 25,0.2338,uniform_random3
C,4,3,1,9 41 71 69 75 97,0.2028 0.2226 0.3116 0.1764 0.1468 0.1760,0 2 5,9 71 97,0.1760,uniform_random3
C,4,4,1,84 96 80 76 6 73,0.1791 0.2630 0.2719 0.2906 0.2180 0.2098,0 3 4,84 76 6,0.1791,uniform_random3
C,4,5,1,4 72 85 15 20 63,0.1576 0.2004 0.1663 0.3737 0.2574 0.1508,0 1 5,4 72 63,0.1508,uniform_random3
C,4,6,1,90 95 29 56 60 91,0.2452 0.1499 0.1348 0.2372 0.1460 0.2363,0 2 3,90 29 56,0.1348,uniform_random3
C,4,7,1,16 67 14 10 86 44,0.1852 0.2021 0.1436 0.1338 0.1558 0.1627,2 3 5,14 10 44,0.1338,uniform_random3
C,4,8,1,58 99 78 26 12 32,0.2317 0.1534 0.1308 0.1740 0.2360 0.1631,0 4 5,58 12 32,0.1631,uniform_random3
C,4,9,1,48 54 45 36 18 0,0.1355 0.1277 0.1907 0.1400 0.2746 0.1091,0 1 4,48 54 18,0.1277,uniform_random3
C,4,10,1,94 53 82 55 52 59,0.1239 0.1303 0.1809 0.1515 0.1539 0.1430,1 2 4,53 82 52,0.1303,uniform_random3
C,4,11,1,5 17 30 65 81 31,0.1358 0.1567 0.1770 0.1791 0.1746 0.2232,1 4 5,17 81 31,0.1567,uniform_random3
C,4,12,1,64 49 43 93 47 88,0.1171 0.1642 0.1739 0.1516 0.1456 0.1213,0 2 3,64 43 93,0.1171,uniform_random3
C,4,13,1,39 21 24 34 79 3,0.1376 0.1254 0.1244 0.1779 0.1319 0.1196,0 2 5,39 24 3,0.1196,uniform_random3
C,4,14,1,27 33 98 22 35 46,0.1317 0.1337 0.2476 0.1420 0.1242 0.2627,1 3 4,33 22 35,0.1242,uniform_random3
C,4,15,1,68 66 28 7 37 70,0.1121 0.1563 0.1373 0.1131 0.1806 0.1021,2 3 5,28 7 70,0.1021,uniform_random3
C,4,16,1,51 2 8 11 19 61,0.2050 0.2613 0.1547 0.1713 0.1526 0.2050,0 1 4,51 2 19,0.1526,uniform_random3
C,4,17,1,50 92 13 38 38 13,0.1773 0.1637 0.1382 0.0942 0.1015 0.1025,0 2 5,50 13 13,0.1025,uniform_random3
C,4,18,0,71 57 4 61 13 44,0.1661 0.2024 0.0800 0.2050 0.0409 0.0951,1 3 4,57 61 13,0.0409,uniform_random3
C,4,19,0,93 18 36 48 97 96,0.0863 0.1483 0.1362 0.0851 0.0982 0.2334,0 1 3,93 18 48,0.0851,uniform_random3
C,4,20,0,65 45 86 92 19 15,0.1598 0.1864 0.1440 0.1637 0.1014 0.3234,1 2 3,45 86 92,0.1440,uniform_random3
C,4,21,0,39 22 46 6 52 55,0.0938 0.0862 0.2699 0.1104 0.1034 0.1339,0 4 5,39 52 55,0.0938,uniform_random3
C,4,22,0,17 66 76 29 11 26,0.0868 0.1586 0.1389 0.0819 0.1407 0.1643,3 4 5,29 11 26,0.0819,uniform_random3
C,4,23,0,89 91 58 23 41 8,0.0922 0.2613 0.1350 0.0995 0.1929 0.1547,0 2 3,89 58 23,0.0922,uniform_random3
C,5,1,1,28 62 54 75 74 25,nan nan nan nan nan nan,0 2 3,28 54 75,nan,coldstart_random3
C,5,2,1,86 85 92 2 57 7,0.1783 0.1720 0.1994 0.3985 0.2679 0.1386,0 4 5,86 57 7,0.1386,uniform_random3
C,5,3,1,81 41 96 78 51 68,0.1940 0.2474 0.1701 0.1224 0.2279 0.1639,0 1 5,81 41 68,0.1639,uniform_random3
C,5,4,1,82 50 36 8 97 76,0.1960 0.2089 0.1706 0.1899 0.1445 0.2716,0 4 5,82 97 76,0.1445,uniform_random3
C,5,5,1,29 53 30 5 42 99,0.1180 0.1453 0.1697 0.1544 0.1705 0.1391,0 1 3,29 53 5,0.1180,uniform_random3
C,5,6,1,15 33 22 37 39 38,0.3605 0.1699 0.1537 0.1980 0.1752 0.1194,1 3 5,33 37 38,0.1194,uniform_random3
C,5,7,1,64 46 21 4 66 70,0.1118 0.2790 0.1331 0.1200 0.1525 0.1239,2 4 5,21 66 70,0.1239,uniform_random3
C,5,8,1,58 63 79 77 19 24,0.2120 0.1253 0.1264 0.1599 0.1913 0.1635,0 1 3,58 63 77,0.1253,uniform_random3
C,5,9,1,91 44 11 61 40 43,0.2351 0.1537 0.1754 0.2068 0.1955 0.1791,1 3 5,44 61 43,0.1537,uniform_random3
C,5,10,1,34 12 71 18 84 55,0.1835 0.2463 0.2630 0.2604 0.1707 0.1266,1 4 5,12 84 55,0.1266,uniform_random3
C,5,11,1,10 80 72 26 65 0,0.1186 0.2580 0.1422 0.1681 0.1782 0.0982,0 2 5,10 72 0,0.0982,uniform_random3
C,5,12,1,93 16 56 17 9 87,0.1127 0.1365 0.2059 0.1649 0.1173 0.1655,0 4 5,93 9 87,0.1127,uniform_random3
C,5,13,1,49 23 35 52 27 1,0.1657 0.1175 0.1510 0.1503 0.1308 0.2930,1 2 5,23 35 1,0.1175,uniform_random3
C,5,14,1,89 73 13 69 48 90,0.1162 0.1658 0.1403 0.1146 0.1218 0.2298,0 1 4,89 73 48,0.1162,uniform_random3
C,5,15,1,60 47 14 20 6 95,0.1379 0.1293 0.0965 0.1879 0.1676 0.1267,0 4 5,60 6 95,0.1267,uniform_random3
C,5,16,1,31 59 3 67 83 98,0.1870 0.1268 0.1212 0.1872 0.1358 0.2513,0 2 5,31 3 98,0.1212,uniform_random3
C,5,17,1,88 45 94 32 32 94,0.1141 0.1427 0.0981 0.1599 0.1599 0.0981,1 2 4,45 94 32,0.0981,uniform_random3
C,5,18,0,80 79 15 23 34 9,0.2172 0.1246 0.3213 0.1125 0.1834 0.0759,2 4 5,15 34 9,0.0759,uniform_random3
C,5,19,0,71 91 4 24 68 5,0.2620 0.2554 0.1252 0.1445 0.0712 0.0743,0 3 5,71 24 5,0.0743,uniform_random3
C,5,20,0,78 16 31 50 13 63,0.0936 0.1222 0.1449 0.1695 0.1401 0.0845,0 2 3,78 31 50,0.0936,uniform_random3
C,5,21,0,51 27 0 29 81 6,0.2620 0.1308 0.0621 0.0791 0.1173 0.0952,0 2 5,51 0 6,0.0621,uniform_random3
C,5,22,0,99 95 19 65 33 69,0.1195 0.0796 0.1369 0.1531 0.0824 0.1146,1 4 5,95 33 69,0.0796,uniform_random3
C,5,23,0,97 26 56 54 76 87,0.0870 0.1658 0.2056 0.0806 0.1166 0.1030,3 4 5,54 76 87,0.0806,uniform_random3
C,5,24,0,20 7 8 3 89 47,0.1838 0.0654 0.1621 0.0748 0.0721 0.1430,0 1 3,20 7 3,0.0654,uniform_random3
C,5,25,0,30 2 58 48 43 14,0.2104 0.2567 0.1380 0.0774 0.0945 0.1115,1 4 5,2 43 14,0.0945,uniform_random3
C,5,26,0,11 94 62 28 37 73,0.1418 0.0612 0.1283 0.0903 0.1115 0.1061,0 3 4,11 28 37,0.0903,uniform_random3
C,6,1,1,71 20 48 13 30 29,nan nan nan nan nan nan,1 2 5,20 48 29,nan,coldstart_random3
C,6,2,1,3 93 26 28 87 43,0.2018 0.2027 0.2179 0.2159 0.2925 0.2949,0 4 5,3 87 43,0.2018,uniform_random3
C,6,3,1,14 8 21 78 9 59,0.1578 0.2182 0.1815 0.1444 0.1670 0.1702,1 2 4,8 21 9,0.1670,uniform_random3
C,6,4,1,99 79 50 66 94 16,0.1925 0.1479 0.2304 0.1613 0.1511 0.1805,2 3 4,50 66 94,0.1511,uniform_random3
C,6,5,1,51 6 89 95 86 45,0.2326 0.1830 0.1416 0.1538 0.1653 0.2074,0 1 5,51 6 45,0.1830,uniform_random3
C,6,6,1,82 35 73 17 39 74,0.1824 0.1704 0.2018 0.1794 0.1644 0.2002,0 3 5,82 17 74,0.1794,uniform_random3
C,6,7,1,76 49 63 7 85 22,0.2580 0.1933 0.1463 0.1303 0.1764 0.1762,1 2 4,49 63 85,0.1463,uniform_random3
C,6,8,1,19 27 38 15 61 88,0.1855 0.1383 0.1321 0.3792 0.2206 0.1193,1 4 5,27 61 88,0.1193,uniform_random3
C,6,9,1,1 55 44 58 36 81,0.3429 0.1555 0.1769 0.2185 0.1355 0.1531,0 2 3,1 44 58,0.1769,uniform_random3
C,6,10,1,90 53 31 23 41 77,0.2704 0.1350 0.2114 0.1748 0.1870 0.1537,1 2 5,53 31 77,0.1350,uniform_random3
C,6,11,1,64 57 65 5 67 37,0.1139 0.2382 0.1702 0.1520 0.2045 0.1684,1 3 5,57 5 37,0.1520,uniform_random3
C,6,12,1,92 80 56 32 83 46,0.1630 0.2783 0.2265 0.1618 0.1350 0.2704,1 2 3,80 56 32,0.1618,uniform_random3
C,6,13,1,91 42 54 11 96 70,0.2854 0.1497 0.1382 0.1428 0.2017 0.1264,0 1 3,91 42 11,0.1428,uniform_random3
C,6,14,1,72 24 12 69 68 52,0.1666 0.1611 0.2711 0.1332 0.1177 0.1424,0 1 3,72 24 69,0.1332,uniform_random3
C,6,15,1,25 98 34 2 40 47,0.1284 0.1892 0.1886 0.2609 0.1946 0.1596,2 3 4,34 2 40,0.1886,uniform_random3
C,6,16,1,60 75 84 18 0 4,0.1368 0.1275 0.1587 0.2665 0.1019 0.1262,0 1 5,60 75 4,0.1262,uniform_random3
C,6,17,1,33 97 62 10 10 62,0.1315 0.1491 0.1530 0.1441 0.1347 0.1624,1 3 5,97 10 62,0.1441,uniform_random3
C,6,18,0,42 1 51 88 26 54,0.0951 0.1543 0.1091 0.0933 0.1813 0.1294,2 4 5,51 26 54,0.1091,uniform_random3
C,6,19,0,19 43 53 85 6 91,0.1637 0.1030 0.0882 0.0900 0.0993 0.1709,0 4 5,19 6 91,0.0993,uniform_random3
C,6,20,0,14 94 62 18 76 12,0.1178 0.0719 0.0901 0.2584 0.1875 0.2711,2 3 4,62 18 76,0.0901,uniform_random3
C,6,21,0,84 58 9 72 30 22,0.1587 0.1394 0.0810 0.0962 0.2179 0.1498,1 3 5,58 72 22,0.0962,uniform_random3
C,6,22,0,41 92 0 97 48 44,0.1742 0.1542 0.0962 0.0824 0.0773 0.0992,2 4 5,0 48 44,0.0773,uniform_random3
C,6,23,0,32 39 31 29 75 65,0.1083 0.1413 0.1317 0.0755 0.0740 0.1508,1 4 5,39 75 65,0.0740,uniform_random3
C,6,24,0,25 7 69 98 93 27,0.1284 0.1028 0.0732 0.1819 0.1346 0.0889,0 1 4,25 7 93,0.1028,uniform_random3
C,6,25,0,13 3 49 68 21 11,0.1147 0.0789 0.1106 0.1091 0.0932 0.0813,1 3 5,3 68 11,0.0789,uniform_random3
C,7,1,1,33 25 41 85 79 82,nan nan nan nan nan nan,3 4 5,85 79 82,nan,coldstart_random3
C,7,2,1,21 94 97 1 22 0,0.2134 0.1965 0.1811 0.3570 0.1785 0.1484,0 1 2,21 94 97,0.1811,uniform_random3
C,7,3,1,61 73 24 49 26 44,0.2539 0.2553 0.1919 0.1972 0.2136 0.1725,0 1 2,61 73 24,0.1919,uniform_random3
C,7,4,1,77 80 47 2 51 38,0.1653 0.2836 0.1728 0.3780 0.3163 0.1433,0 1 2,77 80 47,0.1653,uniform_random3
C,7,5,1,14 48 10 32 16 95,0.1496 0.1738 0.1731 0.1688 0.2006 0.1822,2 3 4,10 32 16,0.1688,uniform_random3
C,7,6,1,65 69 42 59 89 99,0.2037 0.1418 0.1409 0.1428 0.1395 0.1512,2 4 5,42 89 99,0.1395,uniform_random3
C,7,7,1,66 92 57 29 20 88,0.1610 0.1712 0.2403 0.1354 0.2036 0.1645,1 2 3,92 57 29,0.1354,uniform_random3
C,7,8,1,34 60 31 13 63 3,0.1821 0.1612 0.2375 0.1448 0.1558 0.1301,3 4 5,13 63 3,0.1301,uniform_random3
C,7,9,1,56 87 45 62 58 23,0.2276 0.1699 0.1801 0.1635 0.2086 0.1743,0 1 5,56 87 23,0.1699,uniform_random3
C,7,10,1,93 40 36 67 71 81,0.1426 0.2024 0.1676 0.1948 0.2847 0.1590,0 3 5,93 67 81,0.1426,uniform_random3
C,7,11,1,43 52 35 39 76 18,0.1547 0.1471 0.1467 0.1380 0.2457 0.2593,2 4 5,35 76 18,0.1467,uniform_random3
C,7,12,1,84 37 17 5 75 96,0.1475 0.1829 0.1413 0.1546 0.1212 0.2568,1 3 5,37 5 96,0.1546,uniform_random3
C,7,13,1,98 78 91 28 15 72,0.1845 0.1147 0.2708 0.1620 0.3677 0.1926,0 3 4,98 28 15,0.1620,uniform_random3
C,7,14,1,90 54 70 86 30 8,0.2052 0.1274 0.1314 0.1290 0.1716 0.1701,0 4 5,90 30 8,0.1701,uniform_random3
C,7,15,1,53 55 11 4 27 64,0.1370 0.1431 0.1631 0.1404 0.1355 0.1134,1 2 3,55 11 4,0.1404,uniform_random3
C,7,16,1,7 74 46 12 68 9,0.1236 0.2024 0.2656 0.2458 0.1373 0.1410,2 3 5,46 12 9,0.1410,uniform_random3
C,7,17,1,6 83 50 19 19 50,0.1756 0.1594 0.1823 0.1440 0.1693 0.1718,0 3 4,6 19 19,0.1440,uniform_random3
C,7,18,0,8 87 4 9 35 68,0.1096 0.1067 0.0926 0.0894 0.1022 0.1373,2 3 4,4 9 35,0.0894,uniform_random3
C,7,19,0,99 7 86 44 34 37,0.0945 0.1201 0.1290 0.1600 0.1764 0.1082,0 1 4,99 7 34,0.0945,uniform_random3
C,7,20,0,41 24 58 36 27 40,0.1702 0.0910 0.2104 0.1479 0.1355 0.1906,3 4 5,36 27 40,0.1355,uniform_random3
C,7,21,0,75 81 72 83 80 0,0.1192 0.1119 0.1754 0.1461 0.1237 0.0993,0 3 4,75 83 80,0.1192,uniform_random3
C,7,22,0,53 19 65 29 89 32,0.1370 0.0510 0.1746 0.0850 0.0748 0.1045,0 3 5,53 29 32,0.0850,uniform_random3
C,7,23,0,55 93 6 97 5 23,0.0899 0.0870 0.1056 0.0985 0.0989 0.1033,3 4 5,97 5 23,0.0985,uniform_random3
C,7,24,0,94 63 76 73 49 16,0.0762 0.0967 0.1449 0.1192 0.1771 0.1042,1 2 4,63 76 49,0.0967,uniform_random3
C,7,25,0,30 17 74 1 22 31,0.1505 0.1247 0.1649 0.3067 0.1480 0.1606,2 3 5,74 1 31,0.1606,uniform_random3
```
