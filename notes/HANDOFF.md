# Handoff: GEPA-SI-CURRICULUM — HoVer heterogeneity screen complete (2026-07-09)

> Unique doc ID: `gepa-si-hover-screen-phaseB-20260709`. Paste into a fresh Claude context cold.
> Predecessor: the Stage-2 Phase-3 handoff (`gepa-si-hover-swap-phase3-20260709`), superseded;
> its load-bearing facts are carried forward below. Earlier: `notes/HANDOFF_selection-closed_2026-07-05.md`.

## What this is

Research project asking whether GEPA's reflective prompt-optimization loop has an exploitable
**curriculum over side-information** — does *which examples the proposer reflects on* causally
matter? Two directions have been probed:

- **Selection** (which single examples): CLOSED. Per-example scorers are causally inert at the
  one-step gate (batch-swap v2, IFBench, 2026-07-05).
- **Reflection input channel** (which batch): batch-swap v2 on IFBench nulled, but two external
  adjudicators blocked the broad headline on a **generic-target confound** (IFBench's optimal
  prompt is plausibly batch-invariant boilerplate). **HoVer is the discriminating test** — its
  evolved prompts are visibly example-derived.

Stage-2 (HoVer batch swap) found the channel is **not** inert: pooled specificity **+0.0274**,
run-cluster CI [+0.0149, +0.0415], MDE 0.0191, perm p 0.0177. Transfer +0.0169, CI
[−0.0040, +0.0367] (spans 0). **These have not been read against the pre-registered map** — that
read is Neel's (see "Open decision" below).

This session ran the **heterogeneity screen** on top of that: *which* events carry the
specificity effect, and does anything observable predict it?

## Current state

**Both screen phases are complete, committed, and reported.** Nothing is running. $0 spent
(zero API calls throughout — local pip installs + one local HF model download only).

### Screen result (the headline)

Of **108 race cells**, exactly **one survives every pre-registered criterion**:

**`knn_emb_fb_min`** — batch *minimum* of embedding-space kNN novelty (k=3, MiniLM
`all-MiniLM-L6-v2`, local) of the **feedback-only** SI text vs the run's strictly-prior SI archive.

| read | beta (per within-run SD) | 95% BCa CI (8-cluster) | perm p | LORO |
|---|---|---|---|---|
| 4.1 marginal | +0.03794 | [+0.01045, +0.07031] | 0.0013 | 8/8 |
| 4.2 orthogonal (difficulty axis) | +0.03877 | [+0.01068, +0.07011] | 0.0013 | 8/8 |
| sign_i (tie-robust) | +0.19560 | [+0.09344, +0.29185] | 0.0009 | 8/8 |

It is the **only MCB-adjusted survivor** on both the (a) deployable-criteria and (b) orthogonal
lists. Raw (pre-MCB) (a)-list also contains `knn_emb_full_mean`, `knn_emb_full_max` — so the
*family* carries signal, not one lucky cell.

**Negative control (pure-noise scorer, identical pipeline): does not survive** (beta +0.00122,
CI spans 0, p 0.9126, LORO 3/8). Pipeline is sane. Second path (statsmodels vs hand-rolled
lstsq) agrees to 1e-16 on the top-3.

### What this means, stated carefully

- The specificity effect is **not uniform** across events. It concentrates in events whose
  reflection feedback is *semantically novel* relative to the run's own history.
- **Every survivor is Class B** (requires the realized SI — you only have it after running the
  parent on the batch). The pre-registered live-confirm clause keys on a **Class A** (pre-spend,
  deployable) scorer passing criterion (a). **The Class A list is empty.** So the screen's own
  rules trigger **no live-confirm decision**.
- Closest Class A miss: `repr_min` (claim representativeness, batch min) — CI excludes 0, LORO
  8/8, but **perm p = 0.0994**. Fails the leg that matters.
- **TF-IDF versions of the same novelty scorers are null.** Signal lives in semantic, not lexical,
  similarity.
- Nulls everywhere else: actionability, NCD/compression novelty, failure-mode typology,
  fixability, signature novelty, co-failure, claim length, BM25 hardness, static difficulty (A1).
- Softening nuance worth remembering: the **feedback-only** variant needs only the parent's
  *retrieval* results on the batch (cheap, deterministic given the parent) — **not** the LM
  reflection call. A parent-lookahead sampler is conceivable. That is a new design, not what was
  screened.

### Caveats that attach to the above

- The 8-cluster bootstrap runs **anti-conservative**; that caveat sits under the CI leg of every
  survival call and is printed in the results header.
- The rank-based robustness read (4.4, within-run Spearman, Fisher-z pooled) backs **nothing** at
  p < 0.05. `knn_emb_fb_min` tops that table too (+0.1247) but at p = 0.0709. The evidence rests
  on the OLS/bootstrap read.
- Magnitude is modest: ~+0.038 specificity points per within-run SD, against a pooled effect of
  +0.027. Real heterogeneity, not a dominant axis.
- Everything is **one-step-gate** scoped, not downstream utility. K=3, this metric.

## Active hypothesis

No prereg file exists (`notes/prereg/` is empty). The binding pre-registration for this work is
the **task brief itself** plus `analysis/hover_screen/spec.md` (frozen at tag
`screen-spec-frozen` = `2fb33dd`) and its **AMENDMENTS** section (committed `15fba55`, before
any scorer column touched any outcome column).

The Stage-2 interpretation map (from `cc-brief-stage2-hover-swap.md` lines 117-124) is still
**unread by Claude, by design** — Neel reads it:

- Specificity > 0, transfer ≈ 0 → proposer uses batch content; revisions overfit the minibatch;
  input channel NOT inert on HoVer; the IFBench null is task-scoped (generic-target confound real).
- Specificity ≈ transfer > 0 → revisions generalize; batch content matters, example identity less.
- Both ≈ 0 → the selection null replicates; broad headline unblocks (with scope guards).
- Every cell read against its MDE; **no verdict if the CI spans a map boundary.**

## In flight

Branch `main`. **Nothing running. Working tree clean except three untracked notes files:**

- `notes/HANDOFF.md` — this document.
- `notes/SESSION_2026-07-09_hover_screen_phaseA.md` — Phase A session record (numbers + bland
  interpretation).
- `notes/SESSION_2026-07-09_hover_screen_phaseB.md` — Phase B session record (numbers + bland
  interpretation).

These are deliberately untracked pending Neel's call. Nothing else is uncommitted.

### Commits this session (all on `main`, after tag `stage2-pre-analysis` = `5986c1e`)

| commit | what |
|---|---|
| `50af605` | Phase-3 files (`hover_swap_analysis.py`, `results.md`) — committed separately, per Neel's decision, so the pre-analysis boundary stays citable |
| `2fb33dd` | Screen Phase A: spec frozen, features/outcomes extracted, probes run — **pre-join**. Tagged `screen-spec-frozen` |
| `15fba55` | Phase B gate: AMENDMENTS 1-3 + A1 approval appended to spec — **pre-join** |
| `8be66ac` | Phase B: Parts 4-5 — screen statistics, `results.md`, second-path verified |

Tags: `stage2-pre-analysis` (`5986c1e`), `screen-spec-frozen` (`2fb33dd`).

## Load-bearing facts a cold reader will otherwise get wrong

**`scratch/hover_probe/probe.py` is FROZEN.** SHA-256
`35eb46d4589a98f128058f8b9fa3e318ae517130c8b89d55a8df76c3a31b28d4`. Verified unchanged before
and after all screen work. Verify it before and after any change in that tree.

**The BM25 index must be loaded memory-mapped.** `bm25s.BM25.load(..., mmap=False)` is the
default and costs **5.06 GB private RSS per process**; it hung the machine on 2026-07-08. The
fix is a monkeypatch (`_load_index_mmap`, rebinding `probe.load_index`) — **never** an edit to
`probe.py`. The screen's `analysis/hover_screen/screen_bm25.py` replicates this pattern verbatim
and asserts `np.memmap` + `JsonlCorpus` before any query. With mmap the footprint is 0.92 GB.

**Concurrency ceiling is 8** on this 16 GB machine. Never resurrect the old
`RAMP_NEXT = {2:4, 4:8, 8:16}` — the 16 rung is what hung the machine.

**All analysis keys on EVENTS, never `full_program_trace` indices.** Seeds 2 and 6 have
child-less trace entries (seed2 `i ∈ {5,15}`, seed6 `i = 27`) — entries lacking
`new_subsample_scores`. The event key is `(seed, trace_i)`; 243 child-bearing events;
per-seed counts `{0:32, 1:34, 2:28, 3:33, 4:27, 5:34, 6:28, 7:27}`.

**The revisit collapse is the single most consequential coverage fact.** GEPA's sampler sweeps
the 100-example trainset nearly *without replacement* within a run: only **4/725** example-slots
are second visits; **2/243** events contain any revisited example. This is why the entire
within-run difficulty/staleness/visit-count/forgetting family is **COVERAGE-VOID** (Amendment 1)
— excluded from the race and from MCB, reported with n only. They were not disproven; they were
unmeasurable on this corpus. Any future screen wanting them needs a sampler that revisits.

**`accept` is a collider.** It is recorded in `outcomes.csv`/`features.csv` and kept out of every
model, by pre-registration. Do not add it as a regressor.

**Three v2 analysis components were deliberately NOT ported** (reasons in
`analysis/ablation/hover_swap/results.md` provenance): overlap decomposition (HoVer has no
constraint types), failure-count sensitivity (different B_e construction), lottery statistic
(embeds `margin > 0` accept logic the brief's Ties section forbids). Also not ported: v2's
`verdict()` and its interpretation cell.

**MDE convention:** `Z80 × SE_clustered`, `Z80 = 2.802` carried verbatim from
`batch_swap_v2_stage0.py:36`. v2's `SIG2 = 0.0775` and `MDE_SPEC` are IFBench-measured and do
**not** port; v2 defines no transfer MDE.

**Scorer 8 (`vt_*`) is degenerate at 0** — no trainset example's gold titles appear among valset
gold titles. `ngold` is constant 3. Both dropped under Amendment 3, listed in results.md.

**The screen used a dedicated venv**, `analysis/hover_screen/.venv-screen` (gitignored), to avoid
mutating the project `.venv` or the probe `.venv`. BM25 work runs under
`scratch/hover_probe/.venv` (py3.12, has bm25s). The 0.5 checksum recompute must run under the
probe venv to reproduce the committed RNG streams exactly.

**Known anomaly, unfixed, reported:** `act_full_n` was included in the 108 race cells though the
amendment's bookkeeping rule (`*_n` coverage counts excluded) should have dropped it. It survives
nothing and its inclusion only *inflates* the MCB reference set (conservative direction). Flagged,
not silently removed.

## Repo map (screen only; Stage-2 map is in the predecessor handoff)

- `analysis/hover_screen/` — all screen writes
  - `spec.md` — the frozen scorer spec + AMENDMENTS. **Read this first.**
  - `results.md` — Phase B output, **numbers only, no interpretation** (882 lines)
  - `screen_stats_cells.csv` — machine-readable twin of results.md
  - `features.csv` (243×165), `outcomes.csv` (243 rows), `bm25_ranks.csv`, `events_index.json`
  - `si_sample.md` — 10 verbatim SAME-arm reflection objects (the eyeball file)
  - `probe_2_1_signatures.json`, `probe_2_2_fixability.json`
  - `screen_part0.py`, `screen_part05_outcomes.py`, `screen_part2.py`, `screen_bm25.py`,
    `screen_part3_features.py`, `screen_part4_stats.py`
  - `reports/` — captured stdout of each part
- `analysis/ablation/hover_swap/` — Stage-2 corpus + Phase-3 analysis (243 pairs, `results.md`)
- `analysis/scorer_portability.md` — the older IFBench→HoVer scorer roster (reconciled in spec.md)
- `scratch/hover_stage1/` — frozen Stage-1 corpus. Read-only.
- `scratch/hover_probe/` — frozen `probe.py`, BM25 index (~2.7 GB), threehop.jsonl. Read-only.
- `cc-brief-stage2-hover-swap.md` — the Stage-2 contract (holds the interpretation map)

## Open decision (Neel's, not Claude's)

**The Stage-2 map read has still not been made.** Specificity's CI [+0.0149, +0.0415] excludes 0
and its lower bound sits *below* the MDE of 0.0191; transfer's CI spans 0. Which map cell that
lands in — and whether the CI spans a boundary (in which case: no verdict) — is Neel's call. The
screen does not settle it and was not designed to.

## Next steps

1. **Read the Stage-2 numbers against the map** (above). That read is Neel's. It gates everything
   downstream.
2. **Decide what to do about the empty Class A survivor list.** The screen's pre-registered
   live-confirm clause did not fire. Three coherent options, none pre-registered, each needing a
   new prereg before running:
   - **Accept the channel finding as-is** and write it up: the effect is real and concentrates in
     semantically-novel-feedback events, but nothing pre-spend predicts it.
   - **Phase C: parent-lookahead sampler.** Score candidate batches by running the parent on them
     (retrieval only, no LM reflection — cheap and deterministic) and computing
     `knn_emb_fb_min`. Tests whether the Class B finding converts into a usable sampler.
     This is the natural follow-up and the one the finding actually supports.
   - **Re-screen `repr_min`** (the only near-miss Class A cell, perm p = 0.0994) with more runs.
     Weak motivation; would need a power argument first.
3. **Commit or discard the three untracked `notes/` files.** They were left untracked pending
   Neel's call.
4. **Do not update `findings_summary.md`** from a Claude session — per the brief, that edit
   happens Desktop-side after Neel's read.
5. **Do not re-run Stage-2.** The corpus is frozen at `stage2-pre-analysis`.
6. If the screen result is contested, the honest weak points to attack first: the 8-cluster
   bootstrap anti-conservatism, and the fact that the rank-based read (4.4) backs nothing at
   p < 0.05. A run-clustered permutation test and more seeds would address both.

## Explicit do-not list (still binding)

- Do not modify `scratch/hover_stage1/`, `scratch/hover_probe/probe.py`, or any frozen corpus.
- Do not key on `full_program_trace` indices (seeds 2 and 6 have child-less entries).
- Do not put interpretation in `results.md`, `spec.md`, `census.md`, `plan.md`, or the manifest.
- Do not use `accept` as a regressor (collider).
- Do not create `APPROVED` yourself.
- Do not synthesize or splice reflection inputs — real parent execution only.
