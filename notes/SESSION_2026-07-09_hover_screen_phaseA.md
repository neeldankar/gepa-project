# Session summary — HoVer heterogeneity screen, Phase A (2026-07-09)

Compiled from the Phase A run (Parts 0–3 of the pre-registered screen spec). Raw numbers
first, interpretation at the end, clearly separated. This document is a session record,
not an analysis output: `results.md`-class files remain numbers-only, and **no scorer
column has been joined to any outcome column** — Phase B has not run.

Commits this session: `50af605` (Phase-3 files, committed separately per decision),
`2fb33dd` (Phase A outputs), tag **`screen-spec-frozen`** = `2fb33dd`.
`scratch/hover_probe/probe.py` SHA-256 verified unchanged before work and before the tag
(`35eb46d4589a98f128058f8b9fa3e318ae517130c8b89d55a8df76c3a31b28d4`).

---

## Part 0 — inventory + byte verification

### 0.1 scorer_portability reconciliation
`analysis/scorer_portability.md` exists (13 IFBench selection scorers). Reconciliation
recorded in `analysis/hover_screen/spec.md`: its four never-implemented stubs
(embedding-kNN novelty, NCD, actionability, novelty×actionability) are scorers 9–12 of
this screen; `input_typicality` reappears as scorer 7; the remaining selection scorers
were not imported.

### 0.2 reflection-object coverage (SAME arm, 243 events × 3 example blocks)
| section | n blocks | bytes min | median | max |
|---|---|---|---|---|
| Inputs | 729 | 114 | 3,434 | 9,726 |
| Generated Outputs | 729 | 312 | 1,143 | 2,761 |
| Feedback | 729 | 118 | 143 | 198 |

Events with all 3 sections in all 3 blocks: **243 / 243** (partial 0, missing 0).

### 0.3
`si_sample.md`: 10 verbatim SAME-arm objects; 7 seeds covered; 5 accepted + 5 rejected
(rng = default_rng(20260709)).

### 0.4 join verification
- Pair dirs = 243; unique (seed, trace_i) keys = 243.
- Pair keys ↔ child-bearing trace entries ↔ reflection events: one-to-one, all 8 seeds;
  per-seed counts {0:32, 1:34, 2:28, 3:33, 4:27, 5:34, 6:28, 7:27}.
- `meta.json:event_ordinal` correct 243/243; `A_e_pos == subsample_ids` 243/243;
  `parent_candidate_idx` 243/243.
- Example-slot byte checks (from 2.1 parsing): SI claim == trainset claim 729/729;
  feedback correct ∪ missed == gold, disjoint, 729/729.
- Child-less trace indices confirmed: seed2 {5, 15}, seed6 {27}.
- **b = 3** (`stage1_run.py` `reflection_minibatch_size=3`; every trace batch size 3).
- `trainset_manifest.json` byte-identical across all 8 seeds.
- Accept inference (`sum(new_subsample_scores) > sum(subsample_scores)`) matches
  `run_summary.json:accepts_inferred` and `candidates_incl_seed = accepts + 1` on all 8 seeds.

### 0.5 checksum recompute (vs committed `analysis/ablation/hover_swap/results.md`)
**PASSED — 26/26 cells identical at reported precision**, run under the same interpreter
(`scratch/hover_probe/.venv`) with the module RNG consumed in the original call order.

| estimand | point | 95% CI (run cluster-boot) | MDE | SE (clust) | perm p | 95% CI (naive-pair) |
|---|---|---|---|---|---|---|
| pooled specificity | +0.0274 | [+0.0149, +0.0415] | 0.0191 | 0.0068 | 0.0177 | [+0.0048, +0.0501] |
| pooled transfer | +0.0169 | [−0.0040, +0.0367] | 0.0293 | 0.0104 | 0.3120 | [−0.0149, +0.0489] |

Second path (pandas groupby): specificity +0.027434842, transfer +0.016918153 (deltas 0.00e+00).
Tie shares: delta_all 0.6295 (N=8,748), delta_own 0.6278 (N=4,374), delta_other 0.6312
(N=4,374), margin_all 0.3656 (N=2,916).

### 0.6 revisit coverage (within-run)
| seed | examples visited | ≥2 visits | events w/ ≥1 revisited example |
|---|---|---|---|
| 0 | 96 | 0 | 0/32 |
| 1 | 100 | 2 | 1/34 |
| 2 | 84 | 0 | 0/28 |
| 3 | 99 | 0 | 0/33 |
| 4 | 81 | 0 | 0/27 |
| 5 | 100 | 2 | 1/34 |
| 6 | 84 | 0 | 0/28 |
| 7 | 81 | 0 | 0/27 |

Pooled visit-count distribution {1: 721, 2: 4}; events with ≥1 revisited example: **2/243**.

---

## Part 1 — outcome table (`outcomes.csv`, 243 rows)

- sign(spec_i): **+127 / 0: 25 / −91**.
- Accepted events: **89/243**.
- Per-event tie shares reproduce the corpus-wide values exactly: delta 0.6295, margin 0.3656.
- Columns: pair_id, seed, trace_i, event_ordinal, iteration, spec_i, trans_i, sign_i,
  tie shares (all/own/other/margin), n counts, accept.

---

## Part 2 — probes

### 2.1 missed-title-set signature ceiling
Corpus-wide (generous grain, instance-weighted):
| grain | instances | distinct | singleton share (instance) | singleton share (distinct) |
|---|---|---|---|---|
| per-example | 729 | 181 | **0.0713** | 0.2873 |
| per-example (empty sigs excluded) | 579 | 180 | 0.0898 | 0.2889 |
| per-batch | 243 | 242 | **0.9918** | 0.9959 |

Within-run instance singleton shares: per-example mean **0.7878**
(per seed: 0.760, 0.765, 0.786, 0.818, 0.802, 0.735, 0.845, 0.790); per-batch **1.0000** all seeds.
Empty (no-miss) per-example signatures: 150/729. Most recurrent non-empty signature: ×8.

**Kill rule (>0.85 at BOTH grains): NOT triggered** → scorers 14/16 computed.

### 2.2 fixability feasibility (20-event sample, rng = default_rng(20260710))
74 missed titles; **38/74 (51.4%) retrievable within k = 1000** under the claim as query;
found ranks span 1–935. Full per-title table in `probe_2_2_fixability.json`.

### BM25 rank table (`bm25_ranks.csv`, feeds scorers 6 and 15)
330 (example, gold-title) rows over 110 examples (100 train + 10 val); 73/330 (22.1%)
censored beyond k = 1000 (train 22.3%, val 20.0%); found ranks min/median/max = 1 / 4 / 935.
Memory-mapped index load via the `hover_swap_run.py` monkeypatch pattern; `probe.py` untouched.

---

## Part 3 — spec + features

- `spec.md` written and frozen **before** extraction; every definition, censoring rule
  (−1 → 1001 at k = 1000), NaN code, variant construction, and the actionability
  re-instantiation are recorded there.
- `features.csv`: **243 rows × 165 columns**; per-seed row counts match {32,34,28,33,27,34,28,27}.
- Text scorers 9–13 in three variants (feedback-only / full triple / delta); TF-IDF fit
  per-run on strictly-prior SI texts, refit per event (word 1–2-gram + char_wb 3–5-gram).
- **Embedding variant ON**: sentence-transformers `all-MiniLM-L6-v2`, fully local
  (1,458 block texts embedded, dim 384); 24 `_emb` columns.
- Coverage / degeneracy (numbers): difficulty family (diffbest/diffmean/peaked) and
  forgetting defined for **0.82%** of events (2/243); cofail 67.9%; signov and fix 99.6%;
  knn/ncd NaN only at event ordinal 0 (8 events). Constant columns include ngold (= 3),
  vt_count/vt_any (= 0), visits_min (= 0), and the std aggregates of the ~zero-coverage family.
- Class B SI source (locked decision): current SI and archives both from Stage-2
  `reflect_in_SAME.txt`, per-run, event-ordinal order, strictly-before.
- Flagged addition A1 (pre-outcome, in multiplicity, veto-able): `difficulty_baseline`
  = 1 − pre-run graded recall (static), motivated by the 0.6 revisit collapse.

---

## Anomaly list (nothing fixed silently)

1. Task prompt described Phase-3 results as "committed"; `results.md` and
   `hover_swap_analysis.py` were untracked at session start. Resolved per user decision:
   committed first, separately (`50af605`).
2. Revisit collapse (0.6): scorers 1–3 and 17 have 2/243-event coverage as pre-registered;
   staleness/visit_count near-constant. Computed as defined, not redefined; addition A1 flagged.
3. Feedback template is structurally constant (always names missed titles verbatim, always
   prints the retrieved-vs-remaining contrast); the briefed actionability candidate is
   degenerate in this format; frozen re-instantiation in spec.md §11.
4. Scorer 8 (valset_targeting) constant 0 — no trainset gold title occurs among valset gold
   titles. n_gold constant 3. Both are no-information cells for Phase B.
5. `notes/HANDOFF.md` remains untracked (outside decided commit scope).
6. Prompt typos interpreted: "outcomes.csved" → `outcomes.csv`; "note absee" → "note absence".
7. Class B archive NaNs at ordinal 0 (8 events) by construction.

---

## Interpretation (bland, scoped; the pre-registered map read of specificity/transfer
## remains Neel's and is not made here)

- The Stage-2 numbers are now independently reproduced end-to-end from the raw draw files,
  through the same verified code paths, on all 26 reported cells. Whatever the Phase-3
  numbers mean, they are not an artifact of the analysis script's execution.
- The join fabric is sound. Every event, batch position, parent identity, and feedback
  string checks out against the frozen Stage-1 corpus at the byte level. Phase B can key
  on events without caveats.
- The per-event outcome is noisy but not degenerate: about a tenth of events have an
  exactly-zero specificity, and the positive pooled effect coexists with 91 negative-sign
  events. There is real heterogeneity for a screen to try to explain; whether anything
  observable explains it is exactly the Phase B question and is not answered here.
- The within-run history family (difficulty-from-prior-visits, staleness, visit count,
  forgetting) is effectively unmeasurable on this corpus, not because the scorers are
  wrong but because GEPA's sampler visits each training example about once per run. Any
  Phase B result for those cells will be a statement about 2 events. The static baseline
  difficulty (A1) is the only difficulty-like signal with full coverage, and it is an
  addition — flagged, frozen pre-outcome, veto-able.
- Failure signatures recur enough (per-example grain) that signature-novelty and
  co-failure are computable, but batch-level signatures essentially never repeat, so any
  signal in that family will have to come from the example grain.
- About half of the missed gold titles are findable in the top-1000 BM25 results for the
  claim; the other half are not reachable by that query at all. Fixability therefore has
  genuine spread rather than being uniformly high or low.
- The realized-SI text has real variance across its three sections (Inputs vary by ~two
  orders of magnitude in size; Feedback is a tight 118–198-byte template). The feedback-only
  variants of the text scorers are accordingly operating on a narrow channel; the full-triple
  and delta variants carry most of the textual variation.
- Nothing in Phase A blocks Phase B: coverage gates passed where required, the kill rule
  did not fire, and the spec is frozen at `screen-spec-frozen`.
