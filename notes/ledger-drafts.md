# Ledger drafts — for `analysis/findings_summary.md`

**These are DRAFTS. CC must not write to `analysis/findings_summary.md`** — that file is the ledger
of record and is Neel-edited, Desktop-side, after his read. Paste from here.

Written 2026-07-09 under the overnight brief. House style follows the existing ledger: bolded
claim, numbers inline, every caveat that must travel with the number travelling with it.

Three entries. Entry (a) has a hole where the verdict goes; **CC must not fill it**.

---

## (a) HoVer batch-swap — factual layer complete, verdict pending

**Corpus:** HoVer 3-hop claim verification, 8 seeds × ~30 reflection events = **243 events**,
100-claim trainset, `|D_pareto| = 10`, `max_metric_calls = 300`, gpt-4.1-mini, local BM25 retrieval,
deterministic metric. Stage-2 spend $74.09; corpus frozen at tag `stage2-pre-analysis` (`5986c1e`).

**The reflection-input channel is causally active on HoVer.** Pooled specificity **+0.027434842**,
run-cluster 95% CI **[+0.0149, +0.0415]**, MDE 0.0191, within-pair permutation p **0.0177**. Pooled
transfer **+0.016918153**, CI **[−0.0040, +0.0367]** (spans 0), below its own MDE 0.0293 — unresolved.
Both point estimates were independently recomputed from the raw per-pair `draws.jsonl` (243 dirs ×
6 draw rows) and reproduce the committed values to 9 decimal places; the second path (pandas groupby
vs dict/numpy) agrees to 0.00e+00.

**What those two quantities are, operationally** — the definition the external review demanded, and
the one that scopes every downstream claim. Specificity contrasts SAME-arm children (reflection
input from the parent executing on the event's own batch `A_e`) against SWAP-arm children
(reflection input from the parent on the failure-matched batch `B_e`), symmetrized across the two
batches; the shared parent baseline cancels (max |diff| 2.22e-16). Transfer is the child's
improvement measured on **the batch its reflection input never saw**. **Both are evaluated on the
two 3-example minibatches themselves — never on the valset, never on `D_pareto`, never on a
held-out slice.** So this is a statement about one-step minibatch margins, not downstream utility.

**Scope and caveats that travel with the numbers.** One-step gate only, K=3 draws, this metric,
this benchmark. The 8-cluster bootstrap is anti-conservative (standing caveat, attaches to the CI
leg). Specificity's CI lower bound (+0.0149) sits *below* its MDE (0.0191); transfer's CI spans 0.
The IFBench swap null (+0.0054, CI [−0.0116, +0.0242], MDE 0.033) is therefore **task-scoped**: the
generic-target confound that blocked the broad headline is real, and HoVer — whose optimal prompt
must be example-derived — is the discriminating case.

**Verdict:** [VERDICT — Neel fills from `notes/D1-swap-read.md`]

*(The pre-registered interpretation map is quoted verbatim in `notes/D1-swap-read.md`, from
`cc-brief-stage2-hover-swap.md:117-124` at commit `5986c1e`. Its own rule: every cell is read
against its MDE, and there is **no verdict if a CI spans a map boundary**. Whether either CI above
does is the read, and the read is Neel's.)*

---

## (b) HoVer heterogeneity screen — cell 3, one survivor

**The specificity effect is not uniform across events, and exactly one observable predicts where it
concentrates.** Of **108 pre-registered race cells**, one survives every criterion:
**`knn_emb_fb_min`**.

**Full definition** (the name misleads, so it travels in full): *min over the ≤3 batch members of
(mean over the 3 nearest strictly-prior same-run archive feedback blocks of (1 − cosine)), on
L2-normalized `all-MiniLM-L6-v2` embeddings.* The `_min` is a **batch-level** aggregation over the
members — **not** a min over the k neighbours. The archive holds the `## Feedback` text of the 3
examples **actually reflected on** at strictly-prior events of the same run, and nothing else
(verified in code: swap-arm text is never read by the screen; self-inclusion is excluded because the
archive advances after the event is scored; no cross-run pooling).

| read | β (per within-run SD) | 95% BCa CI (8-cluster) | perm p | LORO |
|---|---|---|---|---|
| 4.1 marginal | +0.03794 | [+0.01045, +0.07031] | 0.0013 | 8/8 |
| 4.2 orthogonal (difficulty axis) | +0.03877 | [+0.01068, +0.07011] | 0.0013 | 8/8 |
| sign_i (tie-robust) | +0.19560 | [+0.09344, +0.29185] | 0.0009 | 8/8 |

n = 235 (the 8 ordinal-0 events have no k=3 archive and are NaN by construction). It is the only
MCB-adjusted survivor on both the deployable-criteria and the orthogonal lists. A pure-noise scorer
run through the identical pipeline does not survive (β +0.00122, CI spans 0, p 0.9126, LORO 3/8).
The second path (statsmodels vs hand-rolled lstsq) agrees to 3.5e-17.

**The six caveats that must travel with it.**
1. **Every survivor is Class B.** It requires the *realized* feedback — you only have it after
   running the parent on the example. **The Class A (pre-spend, deployable) list is empty**, so the
   screen's own pre-registered live-confirm clause **did not fire**. No static sampler test is
   triggered by this result.
2. The point estimate (0.0379) sits **below its own MDE** (0.0429) ⇒ conditional on detection the
   magnitude is likely winner's-curse inflated. Plan against roughly half.
3. **The rank-based channel confirms nothing at p < 0.05.** `knn_emb_fb_min` tops that table too
   (+0.1247) but at p = 0.0709. The evidence rests on the OLS/bootstrap read.
4. The 8-cluster bootstrap is anti-conservative.
5. **Signal is embedding-geometry-specific**: every TF-IDF version of the same novelty scorers is
   null. It lives in semantic, not lexical, similarity.
6. **Mechanically this is failure-composition novelty, not prose novelty.** HoVer feedback is a
   rigid 118–198-byte template over retrieved/missed gold titles. Do not describe any downstream win
   as "prose-content novelty".

Closest Class A miss: `repr_min` (claim representativeness, batch min) — CI excludes 0, LORO 8/8,
but perm p = 0.0994. Fails the leg that matters. Nulls everywhere else: actionability, NCD
/compression novelty, failure-mode typology, fixability, signature novelty, co-failure, claim
length, BM25 hardness, static difficulty.

**Magnitude, stated honestly:** ~+0.038 specificity points per within-run SD, against a pooled
effect of +0.027. Real heterogeneity; not a dominant axis.

---

## (c) The no-revisit claim — corrected

The earlier statement that GEPA's sampler "sweeps the trainset nearly without replacement" was
right about **our** corpus and wrong as a general claim about GEPA or about the HoVer paper. Both
halves, separated by what is verifiable here:

**Repo fact (verified).** In our Stage-1 corpus the epoch-shuffled sampler consumes a 100-example
trainset at b=3 with only **4 / 725 example-slots** being second visits, and only **2 / 243 events**
containing any revisited example. This is a *coverage* fact about a ~1-epoch budget, not a property
of the sampler: `EpochShuffledBatchSampler` pads the id list to a multiple of the minibatch size
(100 → 102) and reshuffles at each epoch boundary, so revisits begin in earnest only in epoch 2.
At `max_metric_calls = 300` and b=3, a run reaches the boundary at iteration 34 — about where the
budget runs out. This is why the entire within-run difficulty/staleness/visit-count/forgetting
family is **COVERAGE-VOID** (Amendment 1): those scorers were not disproven, they were
**unmeasurable on this corpus**. Any future screen wanting them needs a sampler that revisits, or a
budget past one epoch.

**Paper figures (brief-supplied; NOT verifiable from this repo — flagged as such).** The HoVer
trainset in the paper is reported as 150 examples, with training passes ranging from **1.0** (Qwen —
exactly one epoch, zero revisits) to **1.84** (GPT — roughly 84% of examples revisited). If those
numbers are load-bearing for any external claim, they need a citation to the paper, not to us. Our
budget sits at the Qwen end of that range, which is precisely why our corpus shows no revisits.

**A distinction worth keeping.** The novelty archive in this project is the **run's own
reflected-feedback archive over `D_feedback`** — an object GEPA constructs, uses, and discards each
event, which our instrumentation persists. It is **not** the paper's `D_pareto`-side per-instance
score matrix `S`. Conflating the two would make the screen's archive look like a Pareto structure
it has nothing to do with.
