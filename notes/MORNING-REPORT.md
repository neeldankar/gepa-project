# MORNING REPORT — overnight of 2026-07-09 → 07-10

**$0 spent. Zero OpenAI calls. Zero task-LM execution. No test evals, no dose re-derivation.**
Everything below was produced from local compute, the frozen corpora, and PyPI.

Frozen corpora untouched: `probe.py` still hashes `35eb46d4…b28d4`; `analysis/hover_screen/` and
`analysis/ablation/hover_swap/pairs/` are byte-identical to their tags.

**The email does not wait for any of this.** Nothing below blocks it.

---

## Status per task

| task | status | output |
|---|---|---|
| 0a preconditions | **done, flagged** | v1 + review were in `~/Downloads`, not the repo. Copied in, committed. STOP did not fire — they exist. |
| 0b commit notes | **done** | `5cc6aea` |
| 1 D1 read template | **done** | `notes/D1-swap-read.md`, verdict section empty |
| 2 lookups | **done** | all five recomputed from raw; §"Lookups" below |
| 3 design v2 + freeze | **done** | `1f99f5c`, tag `state-dep-design-v2-frozen` |
| 4 ledger drafts | **done** | `notes/ledger-drafts.md` (not `findings_summary.md`) |
| 5 implementation | **done, $0** | arms B/C/T, two acceptance gates **PASS**, count audit **PASS** |
| 5e gated scripts | **done, unrun** | all four refuse without their APPROVED file (exit 2) |
| 6 this report | **done** | |

Commits: `5cc6aea` → `2a9a96d` → `b9ecdea` → `1f99f5c` (tagged) → `1a70893` → `36efde6` → (this).

---

## The three things that matter

### 1. Both acceptance gates passed, and the novelty re-implementation is EXACT

You conditioned the environment move on a cross-venv `allclose`. It came back **bitwise identical** —
max |Δ| = 0.0, min per-row cosine 1.000000000000000 — across Python 3.12.13/numpy 2.5.0 and
3.14.3/2.5.1. torch does the arithmetic; the interpreter and numpy patch level don't touch it.

Then the binding gate: recomputing `knn_emb_fb_min` for every screen event from raw pair bytes and
comparing to the committed `features.csv` gave **max abs diff 0.000e+00 across all 235 scored
events** (tolerance was 1e-12), with the 8 ordinal-0 NaNs reproduced as NaN. Not "within tolerance" —
*exact*. §5's fidelity requirement is met more strongly than an import would have demonstrated,
because it is verified on output rather than assumed from shared code.

### 2. The three-arm count audit passed — threat 8 is closed for the mechanics

Every arm's counter matches the §6a five-site model, and the stronger invariant holds:
`total_num_evals == the number of examples handed to the adapter`.

```
arm skip_scope  ev skip acc  parent child valset counter predict match ctr=ex b==3
B   n/a         35    1   8     108   105     90     303     303  True   True True
C   all6        24    0   8     144    72     90     306     306  True   True True
T   all6        22    0  10     132    66    110     308     308  True   True True
C   chosen3     24    0   8     144    72     90     306     306  True   True True
T   chosen3     22    1  10     138    66    110     314     314  True   True True
```

Also confirmed: the unchosen 3 leak nowhere (acceptance reads only restricted scores; Pareto updates
only from valset; every trace batch has size 3), and the §7a epoch-boundary prediction is exact —
b=3 first reshuffles at `state.i = 34`, b=6 at `state.i = 17`.

One harness bug worth knowing, because it *is* the bug class the audit exists to catch: my first run
enabled `EvaluationCache`, and the counter under-counted, because a child example already seen by
the parent returns `actual_evals_count < 3`. Stage 1 ran with no cache (`gepa.optimize` defaults
`cache_evaluation=False`). Fixed; the audit now matches exactly.

### 3. **NEW FLAG B10 — the endpoint is decided by a tie-break on half the seeds, and is the seed
prompt on a quarter of them.**

This is the one thing tonight that I think should change the design before any money is spent, and
neither v1 nor the review caught it.

Recomputing the §8 endpoint convention (`val-argmax`, ties → lowest index) on the eight Stage-1 runs:

| seed | candidates | best_idx | agg(best) | agg(seed cand) | best == seed prompt? | accepts |
|---|---|---|---|---|---|---|
| 0 | 11 | 3 | 0.6000 | 0.4000 | no | 10 |
| 1 | 11 | 9 | 0.5667 | 0.4333 | no (tie 9,10) | 10 |
| 2 | 13 | 6 | 0.6000 | 0.5000 | no | 12 |
| 3 | 11 | 4 | 0.5333 | 0.4333 | no | 10 |
| 4 | 14 | 2 | 0.5333 | 0.4667 | no (tie 2,5,8,9) | 13 |
| 5 | 10 | 5 | 0.6333 | 0.5667 | no (tie 5,6) | 9 |
| 6 | 13 | **0** | 0.5667 | 0.5667 | **YES** (tie 0,4,6) | 12 |
| 7 | 14 | **0** | 0.6000 | 0.6000 | **YES** | 13 |

- The tie-break fires at the top on **4 of 8 seeds**.
- On **2 of 8 seeds the returned program is the seed prompt**, despite 12 and 13 accepted candidates.
  Seed 7 is the sharp case: all 13 accepted candidates are *strictly worse* on the valset than the
  prompt GEPA started from.
- Cause: `|D_pareto| = 10` and per-example scores lie on {0, ⅓, ⅔, 1}, so a candidate's mean val
  score takes very few distinct values. Per seed there are 10–14 candidates but only **4–7 distinct
  val means** (5–8 exact collisions).

Why it matters. R13-a anticipated only *zero-accept* runs ending on the seed prompt. The real
situation is worse and more common: runs that accept a dozen candidates and still return the seed
prompt. If that recurs in the live runs, a paired difference `T − C` will be **exactly 0** on such
seeds, which does not merely add noise — it removes the seed's contribution from the sign-flip test
and eats directly into the n=8 power the whole design rests on.

I did **not** amend v2 for this. It is frozen and tagged; amending it silently would defeat the
freeze. **Recommendation:** treat B10 as an amend-and-re-freeze item before `APPROVED-liverun`, and
consider whether the primary endpoint should be the best-valset score (currently §17-F's *secondary*)
or whether `|D_pareto|` needs to grow. That is a design decision and it is yours.

---

## Flags, in full

**B1 — Task 0a's files were not in the repo.** `state-dependent-design-v1.md` and the adversarial
review existed only in `~/Downloads`. The STOP condition is on the review being *absent*; it was
misplaced, not absent, so I copied both in verbatim and committed them (`2a9a96d`) with their
sha256s, rather than halting the night.

**B2 — The test split cannot be built without spend, and that kills the MDE chain tonight.**
Reproducing `stage1_run.py:131-141` exactly: 245 graded → 123 imperfect → 110 consumed →
**13 remain, all `recall = 0.0`**. §8a's own rule (`N < 100` ⇒ STOP-and-flag) fires. Grading fresh
claims calls `dspy.ChainOfThought` on gpt-4.1-mini (`grade_threehop.py:44`) ⇒ **live spend**, ~$1.33
for ~299 claims (1,620 ungraded claims remain in `threehop.jsonl`). Per your ruling, §8a's procedure
is frozen and the artifact is gated behind the new `APPROVED-testsplit`. **The brief's "test-split
construction runs tonight — it is $0, no API" is false.** Cascade: no split → no backfill → no MDE.
`plan.md` carries an MDE placeholder.

**B3 — `dspy.GEPA` cannot inject a batch sampler.** Its `__init__` has no such parameter (the
docstring at `dspy/teleprompt/gepa/gepa.py:284` claims one — it lies), and it hard-passes
`reflection_minibatch_size=3`, tripping the assert at `api.py:304`. `gepa.optimize()` exposes
`batch_sampler` but **no proposer**, and the 6→3 selection must live in the proposer. So all three
arms wire `GEPAEngine` directly with `merge_proposer=None`. Running B through `dspy.GEPA` while T/C
used `GEPAEngine` would have made V3's counter-parity check meaningless. (Also: `dspy.GEPA` defaults
`use_merge=True`; `gepa.optimize` defaults `False`.)

**B4 — `skip_perfect_score` asymmetry. Flagged, not improvised — v2 §20-1.**
`reflective_mutation.py:204` skips when `all(s >= perfect_score for s in eval_curr.scores)` — that
is 6 scores in T/C and 3 in B, and the gate sits *after* the counter increment, so a skip burns 6
counted parent evals in T/C against B's 3. The proposer therefore **requires** an explicit
`skip_perfect_scope` and has no default; it raises if you don't choose.
**Now quantified**, from Stage-1's 729 real parent per-example scores (P(score = 1) = 0.1866):
gate fires on ~0.65% of events with 3 scores, ~0.004% with 6. Real, and small. Choose and
pre-register; don't agonize.

**B5 — Shared RNG breaks B↔T/C pairing.** One `random.Random(seed)` (`api.py:256`) feeds the batch
sampler (`:302`), the Pareto candidate selector (`:261`), and merge (`:357`). b=6 reshuffles at
`state.i = 17, 34, …` and b=3 at `34, 68, …`, so from the first boundary the shared stream diverges
and **parent selection**, not just batching, differs between B and T/C. **H1 (T−C) is unharmed** —
both draw 6 and consume the stream identically, and the arm-specific picks use separate `Random`
objects that never touch it. Documented in v2 §7a/§15-16; confirmed empirically in the audit.
(Bonus: the sampler's docstring says it is "Deterministic via `state.rng1`". `GEPAState` has no such
attribute. Determinism is real; the stated source doesn't exist.)

**B6 — Dose event set is ambiguous (v2 §20-2).** §11-0 excludes ordinal-0 events (8 of 243, no k=3
archive) ⇒ 705 re-derivation calls; the brief's cost line assumed 729 (all 243). $3.61 vs $3.72.
The pre-registration difference is whether the dose is defined on 235 events or on 243 with 8
undefined. Pick one.

**B7 — The brief arrived with ~12 truncated passages.** Each was reconstructed only where the review
pins it independently, never guessed. The load-bearing one is §11-0's per-event gap, which the brief
garbled ("`…the deployed selector's min) min3-subsets of the subset-min`"). Review **R5(c)** states it
cleanly — *"gap between the 4th order statistic (ascending) of 6 and the expected min of a random
3-subset"* — and **R2** agrees, so v2 §11-0 reads
`gap = x_(4) − E[min over a uniform random 3-subset]`, the latter by exact enumeration over
C(6,3) = 20. Implemented, self-tested, and the self-test correctly **fails** when `gap()` is
sabotaged. Cosmetic reconstructions: `"…continuatiohe 110"`, `"the Goo…"`, `"empirical enbution"`,
`"T/C completplausibly"`, `"composes witthe"`, `"verdiing"`, `"an.md skeleton"`, `"awaitil"`,
`"ancitations"`, `"itseinvestigate"`, `"R13 d §8a"`.

**B8 — `gepa_result.json` is a custom `state_dump`, not gepa's `GEPAResult`.** No
`val_aggregate_scores`, no `best_idx`. The endpoint must be recomputed from
`prog_candidate_val_subscores`. Recorded in v2 §12 (V6).

**B9 — Trace-field contract.** `screen_part0.py:167-168` asserts minibatch size 3, so the proposer
writes the **chosen 3** into `subsample_ids`/`subsample_scores`/`new_subsample_scores` and stashes
the full 6 under `statedep_*` keys. Verified in the audit (`b==3` column).

**B10 — The endpoint tie-break.** See above. The most consequential finding of the night.

---

## Lookups (brief Task 2), all recomputed from raw

**2a.** 245 graded records → 123 imperfect → 110 consumed → **13 remain, all `recall = 0.0`**.
Consumed recall distribution `{2/3: 70, 1/3: 35, 0: 5}`. The sort key `(-recall, claim)` takes the
highest-recall imperfect claims first, so the remainder is the hardest tier only — a sort-order
continuation would be systematically harder than train, which is exactly what §8a forbids. Stable
key: `threehop_idx` (unique, 50–294 contiguous). **≥150 does not remain ⇒ STOP-and-flag (B2).**

**2b.** `EpochShuffledBatchSampler`. Reshuffle at `_update_shuffled` (`batch_sampler.py:46-48`),
triggered at `:64-69`. **Seed-deterministic** via the injected `random.Random(seed)` from
`api.py:256`. Pads the trainset to a multiple of `minibatch_size` (100 → 102 for **both** b=3 and
b=6), and `base_idx` is always a multiple of `minibatch_size`, so **a draw never straddles the
epoch boundary** — it wraps into a freshly reshuffled epoch. 34 minibatches/epoch at b=3, 17 at b=6.
Confirmed empirically in the audit.

**2c.** Endpoint = `GEPAResult.best_idx` (`core/result.py:82-88`) =
`max(range(len(scores)), key=lambda i: scores[i])` over per-candidate **mean** val subscores ⇒
**val-argmax, ties to the lowest index (earliest-accepted candidate)**. Not a Pareto pick, not
last-accepted. `eval_policy.get_best_program` has a different tie-break but is used only for the
end-of-run log event, and agrees here because `FullEvaluationPolicy` gives every candidate identical
coverage (10). **This convention is what produced B10.**

**2d (V6).** The v2 §12 persistence set suffices to recompute, from raw artifacts alone, all 6
novelty scores per event (feedback bytes + archive membership at scoring time + weights hash are all
persisted) and the endpoint chain (per-draw score vectors → val-argmax → test score) — **provided**
the runner persists `prog_candidate_val_subscores`, because of B8. Recorded in v2 §12.

**2e.** `perrun_z` (`screen_part4_stats.py:56-64`), `sd = col[m].std()` (ddof=0) **per seed**. There
is no scalar `SD_screen`. The 8 within-run SDs:
`[0.021870, 0.024433, 0.029460, 0.023196, 0.028713, 0.025238, 0.025011, 0.026538]` (~35% spread).
`beta = 0.0379395028680125`, n = 235 (`screen_stats_cells.csv:434`). Per your ruling the dose is
computed per seed and the gate consumes `mean(D_s)`.

---

## A free result you didn't ask for

`dose_compute.py --pre-estimate` (**$0**, real screen data). Using the 3 reflected members already
scored by the screen, the mean within-event novelty spread (max − min) is **3.06 within-run SD**.
That is *not* the dose — the dose needs all 6 candidates — but it **rules out §15-12's degenerate
case**: there is substantial selection room, and with 6 draws the spread can only grow. The
experiment is not, on this evidence, measuring nothing.

---

## Morning sequence

1. **Read the Stage-2 numbers against the map** — `notes/D1-swap-read.md`. Map quoted verbatim from
   `cc-brief-stage2-hover-swap.md:117-124` at `5986c1e`; verdict section empty and yours to fill.
2. **Paste the ledger entries** from `notes/ledger-drafts.md` into `analysis/findings_summary.md`.
   Entry (a) has a `[VERDICT — Neel fills…]` hole that follows from step 1. CC did not touch
   `findings_summary.md`.
3. **Read `analysis/state_dep/plan.md`** — gated spends, hashes, and what was measured at $0.
4. **Resolve the three non-spend blockers:** B4 (`skip_perfect_scope`), B6 (dose event set), and
   **B10 (the endpoint)**. B10 may warrant amending and re-freezing v2 before any money moves.
5. **Create the gate files** you want: `APPROVED-testsplit`, `APPROVED-dose`, `APPROVED-backfill`.
   CC byte-verifies each and refuses without it (all four scripts verified to exit 2 tonight).
   CC must never create them.
6. **CC runs the smokes, then the gated spends:** dose determinism control (30 events, expected side
   already frozen and committed) → dose → test split → backfill → MDE.
7. **MDE lands**, `plan.md`'s placeholder resolves, and §11-2's gate criterion returns a verdict.
   Only then does `APPROVED-liverun` make sense.

**The email does not wait for any of this.**
