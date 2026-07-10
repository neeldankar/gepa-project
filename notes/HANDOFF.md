# Handoff: GEPA-SI-CURRICULUM — design v2 frozen, arms implemented, spends gated

> **Dated 2026-07-10 08:15 PDT.** Unique doc ID: `gepa-si-statedep-v2-frozen-20260710`.
> Paste into a fresh Claude context cold. Supersedes the previous `notes/HANDOFF.md`
> (`gepa-si-hover-screen-phaseB-20260709`), whose load-bearing facts are carried forward below.
> Written after an overnight run that spent **$0** and made **zero API calls**.

## What this is

Research project asking whether GEPA's reflective prompt-optimization loop has an exploitable
**curriculum over side-information** — does *which examples the proposer reflects on* causally
matter, and can you exploit it?

Three directions have been probed. Two are closed, one is now a live, frozen experiment:

- **Selection** (which single examples): **CLOSED.** Per-example scorers are causally inert at the
  one-step gate (batch-swap v2, IFBench, 2026-07-05).
- **Reflection input channel** (which batch): **NOT inert on HoVer.** Stage-2 batch swap found
  pooled specificity **+0.027434842**, run-cluster CI [+0.0149, +0.0415], MDE 0.0191, perm p 0.0177.
  Transfer +0.016918153, CI [−0.0040, +0.0367] — spans 0, unresolved.
- **State-dependent selection** (draw 6, run the parent, reflect on the 3 with the most novel
  feedback): **the live experiment.** Design frozen at `state-dependent-design-v2.md`,
  tag `state-dep-design-v2-frozen` (`1f99f5c`). Implemented, audited, not yet run.

The chain that motivates the experiment: a $0 heterogeneity screen over 108 scorer cells found
**exactly one survivor**, `knn_emb_fb_min` — batch-minimum embedding novelty of the feedback-only SI
text against the run's strictly-prior archive. It is **Class B** (needs the realized feedback, i.e.
you must run the parent first), so the only deployable form is state-dependent.

## Current state

**Nothing is running. Working tree clean. $0 spent overnight. No `APPROVED` file exists.**

Design **v2 is frozen and tagged**. It absorbs every item of an external adversarial review
(R1–R15, M1–M4, V1–V6; coverage table at v2 §19). Three arms are implemented and audited at $0.
Four live spends are written, committed, and **gated behind `APPROVED-*` files that only Neel
creates**.

### What passed overnight (all $0)

| check | result |
|---|---|
| cross-venv embedding equivalence (`.venv-armT` vs `.venv-screen`) | **bitwise identical**, max\|Δ\| = 0.0 |
| novelty re-implementation vs frozen `features.csv` | **235/235 events, max abs diff 0.000e+00** (tol 1e-12) |
| three-arm counter audit vs the five-site model | **PASS** on all 5 rows |
| `total_num_evals == examples handed to the adapter` | **True**, every arm |
| epoch-boundary prediction (b=3 → i=34; b=6 → i=17) | confirmed empirically |
| unchosen-3 leakage (accept / Pareto / trace) | none; every trace batch size 3 |
| `gap()` order-statistic self-test + sabotage negative control | PASS / correctly FAILS |
| all four live scripts refuse without their gate | exit 2 |

### The three decisions blocking progress

1. **D1 — read Stage-2 against the pre-registered map.** *Neel only; CC must not do this.*
   Everything is staged in `notes/D1-swap-read.md`: the map quoted verbatim from
   `cc-brief-stage2-hover-swap.md:117-124` at commit `5986c1e` (tag `stage2-pre-analysis`), the
   verified numbers beside it, and an **empty VERDICT section**. Two structural facts the map's own
   rules make load-bearing: specificity's CI lower bound (+0.0149) sits *below* its MDE (0.0191),
   and transfer's CI spans 0. The map says: *no verdict if a CI spans a map boundary.*

2. **B10 — the endpoint is tie-break-determined, and is sometimes the seed prompt.**
   The most consequential finding of the overnight run, and neither v1 nor the review caught it.
   Applying v2 §8's endpoint convention (`val-argmax`, ties → lowest index) to the 8 Stage-1 runs:
   the tie-break fires at the top on **4/8 seeds**, and on **2/8 seeds (6 and 7) the returned
   program is the seed prompt**, despite 12 and 13 accepted candidates. Seed 7 is the sharp case:
   all 13 accepted candidates are *strictly worse* on the valset than the prompt GEPA started from.
   Cause: `|D_pareto| = 10` with per-example scores on {0, ⅓, ⅔, 1} yields only 4–7 distinct
   candidate val means per seed. Review R13-a anticipated only *zero-accept* runs; this is worse and
   more common. If it recurs live, `T − C` is **exactly 0** on such seeds and the n=8 sign-flip test
   loses them outright — straight out of the power the design rests on.
   **v2 was NOT silently patched.** It is frozen; this is an amend-and-re-freeze candidate.

3. **Two smaller pre-registration choices (v2 §20), both cheap, both must be settled before
   `APPROVED-liverun`:**
   - **§20-1 `skip_perfect_score` scope.** The gate at `reflective_mutation.py:204` tests
     `all(s >= perfect_score for s in eval_curr.scores)` — 6 scores in T/C, 3 in B — and sits
     *after* the counter increment, so a skip burns 6 counted parent evals in T/C vs B's 3.
     Quantified from Stage-1's 729 real parent scores (P(score=1) = 0.1866): fires on ~0.65% of
     events with 3 scores, ~0.004% with 6. Real, small. The proposer **has no default and raises**
     if you don't choose.
   - **§20-2 dose event set:** 235 events (ordinal-0 excluded, as §11-0 specifies) vs 243.
     $3.61 vs $3.72. The pre-registration difference is whether the dose is defined on 235 events or
     on 243 with 8 undefined.

## Active hypothesis

No `notes/prereg/` file exists. **The binding pre-registration is `state-dependent-design-v2.md`
itself**, frozen at tag `state-dep-design-v2-frozen` (`1f99f5c`).

- **H1 (primary, confirmatory).** At equal total metric-call budget, arm **T** (state-dependent
  novelty selection of the reflection minibatch) beats arm **C** (cost-matched random 3-of-6) on the
  pre-registered endpoint. Tested by exact sign-flip permutation on 8 paired seed differences.
  *Per review R9, H1 is a **policy** contrast, not a mechanism contrast* — accept-rate divergence is
  downstream of the intervention.
- **H2 (secondary).** T beats **B** (unmodified GEPA). The deployment claim; exchangeability is only
  approximate here (R14), which is why it is secondary.
- **H3 (monitored, not a test).** C vs B isolates pure draw-6 overhead. Expected ≤ 0. **If C−B comes
  back positive, v2 §9's anomaly overlay fires and no grid cell may be read until it is resolved in
  writing.**

Interpretation is governed by v2 §9's 3×3 grid on (ΔTC, ΔTB), which **replaced** v1's non-partition
table entirely. Read `results.md` against §9 and nothing else.

## In flight

Branch `main`, **working tree clean**, nothing running, nothing uncommitted.

Commits this session (all on `main`, after `8be66ac`):

| commit | what |
|---|---|
| `5cc6aea` | notes: freeze evidence, session summaries, handoff |
| `2a9a96d` | design: v1 + adversarial review added as repo artifacts (they were only in `~/Downloads`) |
| `b9ecdea` | notes: D1 swap-read template (map verbatim, verdict empty) |
| `1f99f5c` | **design: freeze `state-dependent-design-v2.md`** — tagged `state-dep-design-v2-frozen` |
| `1a70893` | state_dep: novelty scorer + two $0 acceptance gates, both PASS |
| `36efde6` | state_dep: arms B/C/T + three-arm count audit, AUDIT PASS |
| `6510756` | state_dep: gated scripts, `plan.md`, ledger drafts, morning report |

Tags: `stage2-pre-analysis` (`5986c1e`), `screen-spec-frozen` (`2fb33dd`),
`state-dep-design-v2-frozen` (`1f99f5c`).

## Next steps

1. **Read the Stage-2 numbers against the map** — `notes/D1-swap-read.md`. Neel's, not CC's.
   Gates everything downstream.
2. **Paste the ledger entries** from `notes/ledger-drafts.md` into `analysis/findings_summary.md`.
   Entry (a) has a `[VERDICT — Neel fills…]` hole that follows from step 1.
   **CC must never write to `findings_summary.md`.**
3. **Read `analysis/state_dep/plan.md`** — the four gated spends, their costs, script sha256s, and
   everything measured at $0.
4. **Resolve B10** (endpoint tie-break / seed-prompt endpoint), **§20-1** and **§20-2**. B10 may
   warrant amending and re-freezing v2 *before* any money moves.
5. **Create the gate files** you want, in `analysis/state_dep/`: `APPROVED-testsplit` (~$1.33),
   `APPROVED-dose` (~$3.61), `APPROVED-backfill` (~$5.45), `APPROVED-liverun` (~$50–70).
   CC byte-verifies each (`gates.py:require`) and exits 2 without it. **CC must never create one.**
6. **Then CC runs, in order:** dose determinism control (30 events; the *expected* side is already
   frozen and committed) → dose → test split → backfill → MDE. Only then does `APPROVED-liverun`
   make sense.

**The email to the collaborator does not wait for any of this.**

## Load-bearing facts a cold reader will otherwise get wrong

**The `gepa` that matters is `0.0.27`**, at `scratch/hover_probe/.venv/lib/python3.12/site-packages/gepa/`,
selected by `run_seeds.sh:7`. **A decoy editable checkout of `gepa 0.1.1` sits at `~/Desktop/gepa`**
and its internals differ: 0.1.1 has `strategies/acceptance.py` / `StrictImprovementAcceptance`;
**0.0.27 has neither** and decides acceptance inline at `engine.py:490-493`. A subagent cited the
wrong package during this project and was caught only by recomputation. *Every* gepa citation must
be 0.0.27.

**`dspy.GEPA` cannot inject a batch sampler.** Its `__init__` has no such parameter (the docstring
at `dspy/teleprompt/gepa/gepa.py:284` claims one — it lies) and it hard-passes
`reflection_minibatch_size=3`, tripping the assert at `api.py:304`. `gepa.optimize()` exposes
`batch_sampler` but **no proposer**. So all three arms wire `GEPAEngine` directly with
`merge_proposer=None`. (`dspy.GEPA` defaults `use_merge=True`; `gepa.optimize` defaults `False`.)

**gepa's RNG is shared.** One `random.Random(seed)` (`api.py:256`) feeds the batch sampler (`:302`),
the Pareto candidate selector (`:261`), and merge (`:357`). b=6 reshuffles at `state.i = 17, 34, …`
and b=3 at `34, 68, …`, so **parent selection diverges between B and T/C** from the first epoch
boundary — not just batching. **H1 (T−C) is unharmed**: both draw 6 and consume the stream
identically, and arm-specific picks use separate `Random` objects that never touch it. Never draw
the arm-specific pick from gepa's stream.

**No evaluation cache.** Stage 1 ran with `cache_evaluation=False`. Turning the cache on makes a
child example already seen by the parent return `actual_evals_count < 3`, and the budget counter
**silently under-counts**. This bit the count audit on its first run.

**The novelty code path cannot be imported.** `screen_part3_features.py` instantiates the embedding
model at module top level (`:35`), the k-NN is three inline lines (`:237-243`), and `variant_texts`
is nested inside `main()` (`:116-119`). v2 §5 therefore replaced *code-path identity* with
**verified output identity**: `analysis/state_dep/novelty.py` re-implements it and
`verify_novelty.py` must reproduce all 235 non-NaN `knn_emb_fb_min` values from `features.csv`
(currently exact, 0.000e+00). Do not "improve" any function in `novelty.py`.

**`SD_screen` is not a scalar.** The screen standardizes per-run (`screen_part4_stats.py:56-64`,
ddof=0). The 8 within-run SDs are
`[0.021870, 0.024433, 0.029460, 0.023196, 0.028713, 0.025238, 0.025011, 0.026538]`. Ratified
2026-07-09: the dose is computed per seed (`D_s = mean gap_e / sd_s`) and the §11-2 gate consumes
`mean(D_s)`. `beta = 0.0379395028680125`, n = 235.

**The dose's "$0 right now" premise was false.** The swap persisted feedback text for only 3 of the
6 candidates per event (the failure-matched `B_e`), for **0 of 243** events. `A_e` is disjoint from
`draw6`. Re-deriving the missing 3 requires re-executing the parent (~$3.20). The matched 3 are
**not** a usable fallback — `B_idx = combo` was *selected* to match the parent's score profile, so it
is a biased, not uniform, 3-subset. Pre-registered failure mode: **drop the dose**, never shrink it.

**The test split does not exist and costs money.** Only **13** imperfect claims remain unconsumed by
Stage 1, all `recall = 0.0`; §8a's own `N < 100 ⇒ STOP` fired. Grading fresh claims calls
gpt-4.1-mini (`grade_threehop.py:44`), ~$1.33 for ~299 claims. **No test split ⇒ no Stage-1 backfill
⇒ no MDE.** `plan.md` carries an MDE placeholder.

**Fitted cost rate:** `m ≈ $0.004543` per metric call, `r ≈ $0.016744` per reflection call (solved
from Stage-1 seed 0 and the swap's per-pair spend). Independently corroborated by
`grade_threehop.py`: 245 claims for $1.0942 ⇒ $0.00447/claim, within 2%.

**`gepa_result.json` is a custom `state_dump`,** not gepa's `GEPAResult`. No `val_aggregate_scores`,
no `best_idx`. Recompute the endpoint from `prog_candidate_val_subscores`.

**Carried from before:** `probe.py` is FROZEN, sha256
`35eb46d4589a98f128058f8b9fa3e318ae517130c8b89d55a8df76c3a31b28d4`. **The BM25 index must be loaded
memory-mapped** (`mmap=False` costs 5.06 GB RSS/process and hung the machine on 2026-07-08); fix by
monkeypatch, **never** by editing `probe.py`. **Concurrency ceiling is 8** on this 16 GB machine.
**All analysis keys on EVENTS, never `full_program_trace` indices** (seeds 2 and 6 have child-less
entries: seed2 `i ∈ {5,15}`, seed6 `i = 27`); 243 child-bearing events, per-seed
`{0:32, 1:34, 2:28, 3:33, 4:27, 5:34, 6:28, 7:27}`. **`accept` is a collider** — never a regressor.
**The revisit collapse:** only 4/725 example-slots are second visits, which is why the whole
within-run difficulty/staleness/visit-count family is COVERAGE-VOID (Amendment 1) — unmeasurable,
not disproven.

**Stage-1 accept rate = 89/243 = 0.3663 as-run.** Two of those accepts (`seed0 i=31`, `seed5 i=23`)
are IEEE-754 one-ULP artifacts: parent and child sum to the same exact rational (7/3), but different
addends give the child a larger double, so the strict `>` fires. Exact arithmetic would give 87/243.
Any simulation of the gate must replicate float summation or drift by 2 events.

## Repo map (what the overnight run added)

- `state-dependent-design-v2.md` — **the binding pre-registration.** Read §0 (environment), §9 (map),
  §11-0 (dose), §19 (review coverage), §20 (open decisions).
- `state-dependent-design-v1.md`, `adversarial-review-state-dependent-design-v1.md` — the inputs.
- `notes/MORNING-REPORT.md` — what happened overnight, every flag B1–B10, full detail.
- `notes/D1-swap-read.md` — the map + numbers, **verdict empty**.
- `notes/ledger-drafts.md` — three entries to paste into `findings_summary.md`. Not the ledger.
- `notes/FREEZE.md` — the byte-level evidence layer (Part II) behind the v2 environment facts.
- `analysis/state_dep/` — the implementation.
  - `plan.md` — gated spends, costs, script hashes, what was measured at $0.
  - `novelty.py` (the scorer), `verify_novelty.py` + `embed_sample.py` (the two $0 gates)
  - `sampler.py`, `proposer.py` (arms C/T), `count_audit.py` (+ `count_audit_result.json`)
  - `gates.py` (APPROVED machinery), `dose_control.py` (+ `dose_control_expected.json`, frozen),
    `dose_compute.py`, `mde_sim.py`, `build_test_split.py`, `backfill_stage1.py`
  - `.venv-armT` (gitignored) — py3.12.13, numpy 2.5.0, gepa 0.0.27, dspy 3.2.1, ST 5.6.0,
    torch 2.13.0. All pins exact.
- `scratch/hover_stage1/`, `scratch/hover_probe/`, `analysis/ablation/hover_swap/pairs/` — frozen.

## Explicit do-not list (still binding)

- Do not modify `scratch/hover_stage1/`, `scratch/hover_probe/probe.py`, `analysis/hover_screen/`,
  or `analysis/ablation/hover_swap/pairs/`.
- Do not re-run Stage-2. The corpus is frozen at `stage2-pre-analysis`.
- Do not key on `full_program_trace` indices.
- Do not put interpretation in `results.md`, `spec.md`, `census.md`, `plan.md`, or any manifest.
- Do not use `accept` as a regressor (collider).
- **Do not create an `APPROVED` file.** Neel only. CC byte-verifies and refuses without one.
- Do not write to `analysis/findings_summary.md` from a Claude session.
- Do not synthesize or splice reflection inputs — real parent execution only.
- Do not cite `~/Desktop/gepa` (0.1.1). The runs used 0.0.27.
- Do not silently amend the frozen v2. Amend, re-freeze, re-tag — visibly.
