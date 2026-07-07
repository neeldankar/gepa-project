# PROJECT_STATE — GEPA Side-Information Curriculum

> **Clean-slate handoff.** This file assumes zero prior context. It is sufficient on its own to
> pick up the project and start the next phase (scorer screening). Every repo fact below is
> file/field-cited so you can re-verify. Paths are absolute-from-repo-root unless noted; sibling
> repos are at `/Users/neeldankar/Desktop/{gepa,IFBench,open-instruct}`.
>
> **Read-only discipline:** the 10-run baseline corpus in `logs/` is frozen. All analysis so far is
> offline, log-only, $0 (no GEPA re-runs, no API). Keep `analysis/` gitignored.

---

## 1. Project in one paragraph

GEPA optimizes an LLM system's prompt by **reflection**: each cycle (a) selects a parent candidate
prompt, (b) samples a minibatch of ~3 feedback examples (currently **UNIFORM**, via
`EpochShuffledBatchSampler`), (c) collects **side-information (SI)** = per-constraint pass/fail
diagnostics on those examples, and (d) a proposer LLM rewrites the prompt; the child is accepted if
it beats the parent on the minibatch. The **project goal** is a per-example **SELECTION SCORER**
that identifies the most *useful* examples to oversample, then a **curriculum sampler** built on the
best scorer(s), **tested live against uniform** sampling. Task domain is **IFBench-style verifiable
instruction-following** (multi-constraint prompts scored by deterministic verifiers). Stakeholder /
collaborator: **Lakshya (GEPA lead author)**.

The current phase boundary: a diagnostic phase (4 offline probes on the baseline corpus) is
**complete**; the next phase is **scorer screening** (Section 6). No scorer has been built yet.

---

## 2. Corpus + repo facts (each verified — file/field cited)

**Baseline corpus** — `logs/` directory. 10 completed runs, identified by their `*.config.json`
sidecars where `max_metric_calls == 2500` and `results.completed == true`
(`gepa_si/screen/corpus_io.py:discover_runs`). Sidecar fields: `seed`, `b`, `max_metric_calls`,
`log_path`, `results.completed`. Each run is a per-event JSONL (e.g.
`logs/baseline_seed0_b3_20260626_231443.jsonl`).
- **8× b=3** (minibatch size 3), seeds 0–7; **2× b=1**, seeds 0–1.
- **487 reflection cycles** total (per-run b3 = 39, 34, 42, 41, 63, 64, 60, 39 for seeds 0–7; b1 =
  45, 60 for seeds 0–1). A cycle = one iteration with `minibatch_sampled` + `reflective_dataset_built`
  + a before-eval + an accept/reject (`corpus_io.py:parse_run`).
- ⚠️ An **older `seed0_b3` at `max_metric_calls=1000`** also exists in `logs/`; it is correctly
  filtered out by `discover_runs` (keep the `mm==2500` guard if you add tooling).

**Valset (D_pareto) = 150 instances** (val_ids 0–149), constant across runs
(`valset_evaluated.total_valset_size`). Valset score per cell is **fractional** = fraction of that
example's constraints satisfied (11 discrete levels: 0, .2, .25, .333, .4, .5, .6, .667, .75, .8, 1).

**Constraints: 54 distinct ids across 16 type buckets.** Registry:
`open-instruct/open_instruct/IFEvalG/instructions_registry.py` (`INSTRUCTION_DICT`, active entries).
A constraint id is `category:name`; the **category prefix is the type bucket**. The 16 buckets:
`keywords, detectable_format, length_constraints, copy, count, change_case, punctuation,
combination, startend, letters, paragraphs, first_word, last_word, detectable_content, language,
new`.

**Verifier** — `gepa_si/ifbench_eval.py`, class `IFConstraintEvaluator`: per-example
`score = n_satisfied / n_constraints`; per-constraint `objective_scores` are **binary 1.0/0.0**;
`check_following` returns a bool. **Dual registry**: `"ifevalg"` (seen / train-side) and `"ifbench"`
(OOD test-side).

**Data split** — `gepa_si/ifrlvr_data.py`: HF dataset `allenai/IF_multi_constraints_upto5`, shuffle
**seed 0**, `N_TRAIN=150`, `N_VAL=150` (`load_faithful_splits`). **Models** (`scripts/run_baseline.py`):
task LM `openai/gpt-4.1-mini`, reflection LM `openai/gpt-4.1`.

### What IS logged (`gepa_si/si_event_logger.py`)
- **Per-constraint pass/fail at the MINIBATCH/trainset level**, on BOTH the parent (BEFORE) and the
  proposed child (AFTER) evals: `evaluation_end.objective_scores` = list (len b) of
  `{constraint_id: 1.0/0.0}`, aligned by index to `minibatch_sampled.minibatch_ids` and to
  `evaluation_end.scores`. Within an iteration the BEFORE eval has `candidate_idx = parent`, the
  AFTER eval has `candidate_idx = null` — **same minibatch examples**, so parent→child per-constraint
  comparison is exact.
- **Parent OUTPUTS** (the model's generation) per feedback example:
  `reflective_dataset_built.dataset[component][i]["Generated Outputs"]` (Inputs / Generated Outputs /
  Feedback triples; Feedback also carries per-constraint ✓/✗ marks).
- **Per-candidate × valset SCALAR scores**: `valset_evaluated.scores_by_val_id` (150 cells, str
  keys). Fires **once per pool member** = the seed (idx 0) plus one per accepted child. (Rejected
  proposals get no valset eval / no candidate idx — so the final pool = exactly these vectors.)

### What is NOT logged (bounds what scorers can use)
- **Per-constraint pass/fail at the VALSET level** — only the scalar fraction in `scores_by_val_id`.
  ⇒ Valset cells cannot be constraint-diagnosed offline (would need a verifier re-run = API cost).
- **Parent prompt TEXT per event** — reconstructable only: seed from
  `optimization_start.seed_candidate`; accepted children from `proposal_end.new_instructions` /
  `proposal_end.prompts.system_prompt` joined to `candidate_accepted.new_candidate_idx`.
- **Raw verifier MARGINS** — binary only. Continuous measurements (word/char/stopword counts vs
  threshold) are computed *inside* the IFBench checkers but discarded, never returned or logged.

### Sampler plug-in point (where the curriculum goes)
- Interface: `BatchSampler` Protocol, **`next_minibatch_ids(self, loader, state) -> list[DataId]`**
  (`gepa/src/gepa/strategies/batch_sampler.py:13-14`). Returned ids are **positional indices** into
  the trainset, passed to `loader.fetch(ids)`
  (`gepa/src/gepa/proposer/reflective_mutation/reflective_mutation.py:212-213`).
- Default = **`EpochShuffledBatchSampler`** (uniform epoch-shuffle, `rng=random.Random(0)`),
  `batch_sampler.py:17-77`.
- Wire a custom sampler by passing an instance to **`gepa.optimize(batch_sampler=MySampler(...))`**
  (`gepa/src/gepa/api.py:328-333`, forwarded to `ReflectiveMutationProposer` at `:384`). Iteration
  counter available as **`state.i`**. Minibatch size is `reflection_minibatch_size` (default 3);
  `scripts/run_baseline.py:62` exposes it as `--b`.

### Existing analysis modules (REUSE — don't rebuild)
| module | produces |
|---|---|
| `gepa_si/screen/corpus_io.py` | parses logs → `RunData` / `ReflectionCycle` (incl. raw parent/child `objscores`); `load_corpus()`, `discover_runs()` |
| `gepa_si/screen/delta_u.py` | exact **ΔU** = pool-frontier marginal gain per cycle; `final_frontier_mean()` |
| `gepa_si/screen/build_batch_df.py` | per-batch dataframe → `analysis/batch_df.parquet` (keys, controls, accept, delta_u) |
| `gepa_si/screen/ceiling_probe.py` | EB-shrunk `E[ΔU|signature]` table, LORO vs controls, bootstrap CI → `analysis/ceiling_probe_scorer.json`. **Defines `CONTROLS`** |
| `gepa_si/screen/fungibility.py` | LOO frontier contribution (sole-argmax identity), cell-redundancy |
| `gepa_si/screen/coverage.py` | cross-run solve coverage, Jaccard/Hamming, union/intersection/gap |
| `gepa_si/screen/partial_diag.py` | parent→child per-constraint tradeoff test, flip consistency, trajectory |
| `scripts/run_{ceiling_probe,fungibility,coverage,partial_diag}.py` | runners that print each probe + write the parquet |
| `scripts/run_corpus.py`, `scripts/run_baseline.py` | corpus driver (10 jobs, resumable, cost-capped) and the single-run faithful baseline runner |

Gitignored artifacts already on disk: `analysis/{batch_df.parquet, ceiling_probe_scorer.json,
fungibility.parquet, coverage.parquet, partial_diag.parquet}`.

---

## 3. What the diagnostic phase found (4 probes, all log-only, $0)

**Probe 1 — Fungibility (selection-side redundancy of the realized pool).**
Headline: the final pool is **~88% redundant** — each valset cell's per-instance max is tied by **~9
candidates on average**; only **~5% of U is non-redundant** (sum of leave-one-candidate-out unique
contributions ≈ 0.03–0.06 vs U ≈ 0.72; max single contribution ~2% of U, no fat tail).
**Verdict:** the lever "select which *finished* candidate to keep" is **dead** — removing any one
pool member barely moves U. (`run_fungibility.py`)

**Probe 2 — Convergence / coverage divergence across the 10 runs.**
Headline: runs agree on **~80% of cells** (52 solved by all, 68 by none of 150), pairwise
**Jaccard 0.85**; the **swingable territory** (union − intersection of solved cells) is **~14–20%**
(20% across all 10, 14% on the controlled 8× b3 cut).
**Verdict:** reflection is **largely input-insensitive** under uniform sampling — different draws
mostly converge — but a **narrow** real margin (~14–20%) does depend on the draw. (`run_coverage.py`)

**Probe 3 — Coverage structure (what the gap to perfect-U actually is).**
"Solve a cell" = pool per-cell max == 1.0. Headline: the gap is **NOT unreached examples** — only
**4 cells are stuck at 0 across every run**. It is **PARTIAL multi-constraint cells**: the pool
satisfies some-but-not-all constraints (**~50% of all cells; 89% of all misses are partial**, not
fully unreached).
**Verdict:** the only live target is **partial → full conversion**. (`run_coverage.py`)

**Probe 4 — Partial-cell diagnosis: benign (unsampled) vs adversarial (tradeoff).**
⚠️ Ran on **TRAINSET minibatch cells** — per-constraint is not logged at valset level (same dataset
distribution, so structure transfers, but it is not the 150 valset cells).
- **Trajectory:** of re-sampled, not-already-full trainset examples, **64% are flat-stuck (never
  move)**, **only 3% ever reach full**, 16% climb-not-full, 18% oscillate.
- **Tradeoff test (parent→child per-constraint, same cell):** *accepted* moves look clean (4%
  co-regression, +0.46 mean Δsat) — but that's **survivorship from the accept gate**. The **raw
  proposal stream is ~1:1 regress:improve** with **16% of improving proposals simultaneously
  breaking another constraint** ("fix X, break Y"). Tradeoffs are **real but filtered**, not absent.
- **Constraint structure:** failure rates split into **tractable** (`detectable_content, language,
  combination, startend, change_case, punctuation`; fail ≤ 0.30) vs **near-unsatisfiable** (`copy,
  count, first_word, new`; fail 0.71–1.00). High-volume middle: `keywords, detectable_format` (~0.45).
**Verdict:** **MIXED, leaning representational** for the dominant mass; the curriculum-addressable
slice is the tractable-type subset, **~15–30% of partial cells**. (`run_partial_diag.py`)

---

## 4. Critical caveat — do NOT overstate the diagnostics

Every probe characterizes the **UNIFORM baseline corpus only.** They measure what **scattered,
random re-exposure** buys — **NOT** what a scorer's **concentrated, parent-timed re-exposure** would
buy. "Uniform re-exposure doesn't move stuck cells" is **not** the same claim as "targeted
re-exposure won't move them"; that gap is **real** and can only be closed by actually running a
**non-uniform sampler live**. The diagnostics tell us **which scorers have a chance** and **which
slice of the problem is live** — they are **not** a verdict that scorers fail. **The decision is to
proceed to scorer screening**, using the diagnostics as priors (which slice to target, which
families are already ruled out).

---

## 5. The two filters every scorer must pass

A candidate scorer is only interesting if it clears **both**:

1. **Not difficulty-in-disguise.** It must condition on something **beyond the example's own
   before-score / headroom.** Plain difficulty already wins ΔU rank-correlation (Spearman ~0.24)
   **partly through a mechanical headroom → ΔU channel** (a low-scoring example has more room to
   contribute frontier gain). So difficulty is **the bar to beat, not a win.** Score the candidate's
   value *after residualizing the controls* (Section 6).

2. **Not a function of "which constraints failed" alone.** The failed-constraint **signature family**
   (`E[ΔU | signature]`) is **ceilinged-dead**: **335 of 351 signatures are singletons**, and even
   pooled to individual constraint ids the shrunk `E[ΔU]` **clusters at the global mean** — no
   recurrence to learn, beaten by controls out-of-run (see `ceiling_probe.py` / its LORO result).
   Anything isomorphic to the failed-signature lookup is already excluded.

---

## 6. Next phase — scorer screening (Phase 1)  *(record only; do not build in this handoff)*

**Goal:** screen a roster of candidate per-example scorers and pick the **top 1–2** to wire into a
curriculum sampler (Section 2 plug-in point) for a live A/B vs uniform.

**Live scorer roster, in build-cost order:**
- **Computable-now (minibatch SI + valset scalars already logged):**
  - *coverage-gap* — does this example exercise valset cells the current pool under-covers (using
    `valset_evaluated.scores_by_val_id` + the example's constraint set)?
  - *gap-magnitude* — how far below full is the parent on this example's constraints (distance to the
    full conjunction), beyond raw difficulty.
  - *tractable-constraint targeting* — weight examples whose unsatisfied constraints fall in the
    tractable bucket (Section 3, Probe 4) — the slice diagnostics say is live.
  - *tradeoff-risk (avoid)* — examples whose constraints historically co-regress (down-weight), from
    `partial_diag` pair structure.
- **Reconstruction-gated** (needs parent prompt-text reconstruction, Section 2): scorers over the
  parent instruction text (e.g. instruction-coverage of the example's constraints).
- **Output-parsing-gated** (needs `reflective_dataset_built` "Generated Outputs"): scorers over the
  model's actual generation (e.g. how close the output was to satisfying the failed constraint).

**Screening protocol (offline, on the frozen corpus):**
- Rank each scorer by **partial correlation against BOTH outcomes**: (i) per-cycle **ΔU**
  (`delta_u.py`) and (ii) **leave-one-candidate-out unique contribution** (`fungibility.py`) —
  **residualizing the controls** `CONTROLS = {difficulty = mean(1−s), n2_peakedness = mean s(1−s),
  parent_dpareto, iteration}` (`ceiling_probe.CONTROLS`). A scorer must add signal *after* controls
  (Filter 1).
- For any scorer with **aggregate or learned structure** (tables, shrinkage, fitted weights), use
  **leave-one-RUN-out** CV (run = fold) and report **paired per-run differences + bootstrap CI over
  runs** — **no Wald p-values** (matches the ceiling-probe methodology).
- A scorer passes if it beats controls out-of-run on at least one outcome with a CI excluding 0, and
  clears both Section-5 filters.

---

## 7. Dead scorers — do NOT rebuild

- **Semantic text scorers** (embedding-kNN, NCD/compression distance, actionability-as-specificity,
  novelty × actionability): SI is a **templated checklist** with no meaningful text variance — these
  have nothing to bite on.
- **Failed-signature family** (signature novelty, fixability lookup, co-failure tables): **ceilinged-
  dead** per Filter 2 (335/351 singletons; pooled-to-id `E[ΔU]` ≈ global mean).
- **Within-trajectory forgetting** scorers: collapse to **difficulty-in-disguise** (Filter 1) and are
  **singleton-starved** at signature granularity.
- **Verifier-margin / continuous-measurement scorers**: **not buildable** without a verifier re-run
  (margins are discarded, Section 2) — API cost. **Park as an enrichment-gated second wave**, only if
  a re-run with instrumented verifiers is later authorized.

---

*Status: diagnostic phase complete. Next action = execute Section 6 (scorer screening). Do not start
it from this handoff.*
## Leverage/flatness probe (2026-06-30)
- Matrix A pooled b3 (123×150): stable rank 14.4, 90%-energy rank k=47; per-run stable rank ~6 of 16 (candidate redundancy), BUT column-leverage CV 0.95 / Gini 0.53 at 100th pct of within-row null (heavy-tailed).
- Claim 1 (selection futility via FLAT sensitivity): NOT grounded — surprise. Futility is a row/redundancy phenomenon; example leverage is heavy-tailed (swingable cells), not flat.
- Matrix B: antagonism estimable for 210/240 ordered type pairs (N≥5); only 14% exceed base rate; top reliable: fix keywords→break detectable_format (0.12 vs 0.02, n=43).
- Claim 2 (gate is the lever): tradeoffs real but SPARSE not dense; constraints carry moderate entropy (weak dual redundancy). Aggregate gate motivated; per-pair antagonism scorer only on the few dense pairs. Caveat: observed uniform corpus only — not a sampler/gate test.

## Leverage disambiguation probe (2026-06-30)
- Stability: mean cross-run Spearman 0.69 (100th pct of null), ICC(1) 0.81, top-decile Jaccard 0.55 → **STABLE**.
- Novelty: stagewise R² to 0.95 (variance dominates under column-centering), residual R² 0.05 → **DIFFICULTY-IN-DISGUISE**.
- Actionability (LORO AUC): raw 0.97, residual 0.64.
- Cell: **STABLE × DIFFICULTY-IN-DISGUISE** → EXPLAINED AWAY but ex-ante identifiable — stable, yet it IS difficulty (the prior null covers it). Caveat: observed uniform corpus only; centered leverage ≈ cross-candidate spread, so 'difficulty' includes disagreement. NOT a sampler/gate test.

## HoVer viability / scorer portability probe (2026-06-30)
- Scorer portability: 13 implemented signals -> 6 port as-is (text/scalar: input_typicality, typicality_x_headroom, pool_disagreement_voi, output_repairability, output_n_words, leverage), 7 need reimpl (all constraint-keyed, incl. survivor constraint_tractability; all have retrieval analogs), 0 no-analog. 4 'dead semantic' scorers = never coded.
- IFBench SI = templated checklist (confirmed by 10 verbatim failed-example Feedback strings).
- Benchmark: HoVer NOT viable (no GEPA adapter; enwiki corpus absent/multi-GB; retriever needs API). HotpotQA-distractor VIABLE offline $0 (Arrow-direct load; inline passages -> no wiki index; rank_bm25 recall@4 0.72; adapter instantiates with no API).
- GATE (staged, NOT run): scripts/run_hotpot_baseline.py; projected baseline ~$0.35-0.75, smoke <$0.01. Awaiting go-ahead. No API calls made; logs/phase2 untouched.

## HoVer-proper scope (2026-06-30)
- Corpus (Blocker 1): HoVer ships pre-built wiki_wo_links.db SQLite = 2.01 GB (5,486,211 enwiki-2017 abstracts) + TF-IDF JSONs; NOT cached. Disk PASS (286 GB free). Indexing PARTIAL: rank_bm25 in-memory impractical at 5.5M docs/16 GB RAM, Java absent (no pyserini) -> use bm25s (pure-python, no JVM, ~15 min, ~1-3 GB).
- Adapter (Blocker 2): BLOCKED, effort LARGE. No HoVer adapter; GenericRAGAdapter is single-pass, not subclassable to 3-hop; feedback is generic. HoverMultiHop + the 'docs remaining' feedback text must be written from scratch (DSPy not installed; zero refs locally).
- Scorers (Blocker 3): cheap once 1+2 clear — HoVer's recurrent gold-doc-set SI gives the 7 reimpl scorers real signal and makes the 4 never-built semantic scorers worth building.
- Verdict: viable but a real build (~2 GB download + ~15 min bm25s index + ~2-3 days adapter/feedback eng). vs HotpotQA-distractor runnable NOW ~$0.35 but thinner SI. Corpus is no longer the wall; engineering is. $0 dry scope; nothing downloaded/built; logs/phase2+hotpot untouched.

## HoVer SI eyeball probe (2026-06-30, scratch, $0.05)
- Isolated scratch probe (scratch/hover_probe/.venv, dspy 3.2.1) — NOT wired into the harness, no GEPA loop, no scorers. Lifted the DSPy multihop tutorial: 500MB wiki-abstracts corpus (5.23M docs), bm25s index (2.85 GB, built in ~5 min, no OOM on 16 GB), HoVer 3-hop subset (1,866 claims) from vincentkoc/hover-parquet.
- Ran 10 claims through the 3-hop program (gpt-4.1-mini), actual spend $0.0486 (cap $0.50). Captured real 'correct docs retrieved + docs remaining' SI per claim.
- Eyeball verdict: SI VARIES per claim (named gold/remaining Wikipedia title lists — structurally far richer than IFBench's fixed `Satisfied k/n` checklist); docs-remaining non-empty for 4/10 claims.
- HONEST CAVEAT: at n=10, gold titles do NOT recur (30/30 unique) — the curriculum-relevant RECURRENCE is not yet demonstrated; needs a larger sample before committing to the HoVer build. Artifact: scratch/hover_probe/hover_si_sample.md.

## HoVer SI extended eyeball (2026-06-30, scratch, $0.19)
- Isolated scratch probe (scratch/hover_probe/, dspy venv) — NOT wired to harness, no GEPA, no scorers. Ran 40 HoVer 3-hop claims (threehop[10:50]) through the program (gpt-4.1-mini), actual $0.1891 (cap $2). 38 missed gold docs.
- KEY (actionability vs difficulty, $0 structural, no LLM): missed-doc page-type histogram = 28/38 (74%) PLAIN bare names, only 10 (26%) structured (WORK 7, PERSON 2, PLACE 1) — misses do NOT cluster into rule-able types.
- Difficulty-collision: structured misses spread across miss-depth (7 deep / 3 near), not just the hard tail; obscurity ~equal missed 3.43 vs retrieved-gold 3.39 (Δ+0.04) — misses are NOT explained by obscurity either.
- VERDICT: LEAN NO-GO on funding a full HoVer screen — missed-doc actionability has little title-structure a scorer could exploit beyond difficulty; the cheap null is NOT refuted. (A lean, not a decision.) Artifact: scratch/hover_probe/hover_si_eyeball.md.

## Reflection-input exact capture (2026-06-30, capture run $0.04)
- DIRECT-CAPTURED the exact object the reflection LM receives on IFBench (4 reflection calls, ~46 total LM calls, gpt-4.1-mini, $0.0371). Two independent layers + same-run log.
- THREE-WAY BYTE EQUALITY = PASS on all 4 calls: wrapper input == litellm wire payload == logged proposal_end.prompts.system_prompt. The corpus field IS the exact reflection object (proven, not inferred).
- Object = template + current instruction + b=3 examples each {## Inputs, ## Generated Outputs, ## Feedback} + 'write a new instruction'. Predictor = Predict/DefaultAdapter -> NO reasoning/CoT field exists.
- AUDIT: every component is in the 487-corpus at $0 (proposal_end.prompts + reflective_dataset_built). KEY: scorers to date used ONLY Feedback; the proposer also reads Inputs + parent Generated Outputs (never scored, both already logged). BRANCH: usefulness eyeball can re-run on the REAL object for $0 -> PROCEED; no ~$30 re-log needed.

## RAW-vs-PARSED output diff (2026-06-30, $0 read-only)
- Question: was parent-model text (reasoning) stripped before storage as 'Generated Outputs'? Answer: NO.
- Code-proven passthrough (DefaultAdapter L132/139/155/195): 'Generated Outputs' = full_assistant_response VERBATIM, no parse step. Corpus: 0/394 events have any per-example task field beyond {Inputs,Generated Outputs,Feedback}.
- The brief's RAW field (raw_lm_outputs) is the REFLECTION PROPOSER output (1/component), NOT a per-example task completion — invalid per-example join, reported not faked.
- Only raw-vs-parsed delta in the corpus: proposer raw_lm_outputs vs new_instructions = the ```-fence wrapper, MAX delta 9 chars over 394 events (no reasoning/prose). VERDICT: no stripped channel; 'Generated Outputs' is complete; output-usefulness eyeball proceeds on it. Artifacts: analysis/raw_vs_parsed_diff.{md,txt}.

## WAVE 1 re-screen on the CORRECT object (2026-06-30, $0 offline, frozen corpus untouched)
- Re-screened the reopened scorers on the REAL reflection object (full triple Inputs+Generated Outputs+Feedback), not the Feedback string. Screening-level only (LORO + residualization); NO permutation-MAX (that's Wave 2, gated on a survivor). Code: gepa_si/screen/{triples_io,scorers_semantic}.py + scripts/run_rescreen_wave1.py. Artifacts: analysis/rescreen_wave1.{md,parquet}.
- STOP-gate 1 (object) PASS: 1251/1251 per-example {Inputs,Generated Outputs,Feedback} are verbatim substrings of their own event's proposal_end.prompts.system_prompt (the proven byte-exact reflection input; only a trailing space the template trims differs). Object is correct.
- STOP-gate 2 (controls) PASS: re-ran wave1/2/3 vs pre-run snapshot; every [score-control] + [crude-proxy-control] reproduces to float64 ULP (max abs Δ 3.55e-15). Lone 4th-decimal shift in parent_near_frontier partial_loo (−0.0143 vs −0.0144) = rounding-boundary artifact of that ULP noise, not a harness change. constraint_tractability partial_loo = 0.1717 (unchanged).
- THE REAL WORK — 4 never-built semantic scorers (knn_novelty[TF-IDF], ncd_novelty[zlib], actionability, nov_x_act) + NEW output failure-MODE signature, each computed (a) feedback-only / (b) full triple / (c) delta, screened raw / partial(4 difficulty controls) / constid(4 + constraint_tractability + 15 failed-type-composition cols). Survival rule: constid_b>0.05 AND Δconstid(b-a)>0 (output-origin) AND LORO mean−sd>0.
- RESULT — SURVIVORS: NONE. The null HOLDS on the right object (strictly stronger than the prior feedback-string null). Key reads: (1) the only scorer beating the constraint-id bar is kNN-novelty on the FEEDBACK string (partial_loo 0.171 ≈ the 0.172 bar = rare-feedback ≈ rare-constraint-composition); its constid residual ~0.08–0.10 is the rare-exact-combination channel = the DEAD singleton failure-signature in continuous form (LORO 0.10±0.13 straddles 0), and its delta(b−a) is NEGATIVE → the Output dilutes, not adds. (2) ncd_novelty/actionability have positive deltas but sit ≤0 under constid. (3) The NEW output failure-MODE signature is negative under controls (−0.098) — the Output channel that motivated the reopening is empty. (4) [stays-dead-confirm] id-keyed failure-signature reproduces 335/351 singletons (87.7%) → still ceilinged/dead.
- BOTTOM LINE: handing every semantic scorer the full Output the proposer sees, then isolating the Output's marginal contribution, the null holds and the Output channel specifically is empty. constraint_tractability (0.172) remains the sole Phase-2 candidate. No survivor → no Wave 2 hardening for these scorers; next = Phase-2 sampler wiring (constraint_tractability BatchSampler A/B vs uniform).

## HoVer GATE 1 — reflection-object capture + richness (2026-06-30, live $0.142, isolated scratch venv)
- GATE 1 of the HoVer direction: DIRECT-captured what the reflection LM receives on the HoVer multi-hop program (do NOT repeat the feedback-string error). Prior HoVer probes never ran GEPA — they scored the manufactured build_si "docs remaining" string = the thin-object mistake. Code: scratch/hover_probe/gepa_capture.py; artifacts: scratch/hover_probe/{gate1_capture.md, capture/reflect_{1,2,3}.{txt,json,repr}, capture/equality.json}. Main .venv stays dspy-free.
- STEP 1 (capture): minimal dspy.GEPA run (max_metric_calls=24, minibatch=3, round_robin, 6 train/3 val imperfect claims). Two-layer capture (CaptureDSpyLM.__call__ + litellm.success_callback). 3 reflection calls, 144 task calls, 147 total. BYTE-EQUALITY A==B PASS on all 3 (wire payload == wrapper input; two-way not three-way — dspy-GEPA doesn't log the proposal prompt accessibly, but wire IS the API payload so it's sufficient). Spend $0.142 (cap $0.50).
- STEP 2 (map + fork): dspy-GEPA reuses the same gepa proposer (identical wrapper template) but per-example content = the optimized predictor's real input/output dict; both predictors are ChainOfThought (reasoning field exists — IFBench's single Predict had none). Captured BOTH predictors: gen_query {claim, notes → reasoning, query} (reasoning + multi-hop notes, no passages) and append_notes {claim, notes, context → reasoning, new_notes, titles} where context = 10 FULL Wikipedia abstract passages (title+prose, verified by reading bytes, not titles/ids). FORK = RICH (id-determinism collapse does NOT apply) → proceed to Step 3.
- STEP 3 (2×2 eyeball, usefulness vs difficulty): at ~constant recall (2/3), usefulness varies NOT-as-difficulty — Greek Fire (gen_query) shows the reasoning ACCEPTING an unverified implication (actionable flaw); Sonic Youth (append_notes) missed 'Mikael Åkerfeldt' = a spelling/disambiguation miss the reasoning never caught (claim said "Michael Akerfeldt") + model-invented output titles; WCJB/Soul Mates show correct reasoning + pure retrieval miss (low usefulness); Quietdrive recall 3/3 (rich but nothing to fix). LEAN = GO, genuinely-mixed (some rich objects are low-usefulness). Screening eyeball only — variance ≠ usefulness; whether a per-example SELECTION scorer exploits this BEYOND difficulty is the GATE-2 question.
- GATE 2 (the full live-$ scorer screen on HoVer) is a SEPARATE, larger spend — NOT run. GATE 1 cleared: the object is rich by direct capture and usefulness plausibly varies off-difficulty.

## HoVer GATE 2 PRICING — full-screen corpus cost estimate (2026-06-30, $0 no runs/LM calls)
- Priced the GATE 2 corpus BEFORE any spend, pure extrapolation from measured anchors. Artifact: scratch/hover_probe/gate2_pricing.md. Anchors: GATE 1 HoVer probe = $0.00592/metric-call (6 LM calls/rollout + 10-passage context; reflection ~6%, mini); IFBench corpus = $31.73 @ 10 runs × mm=2500, valset=150, ~487 cycles = $0.00127/metric-call. HoVer is 4.7–7.9× IFBench per call (exp 5.9×) — the 6-calls-per-rollout + heavy passage context, as expected.
- Per-metric-call bands (all-in): LOW $0.0060 (GATE1 base) / EXPECTED $0.0075 (+~1.25× evolved-instruction growth over a mature run) / HIGH $0.0100 (+heavier growth + gpt-4.1 reflection). Total ≈ runs × mm × $/call.
- Cost table (EXPECTED): 5×2500=$94, 8×2500=$150, 10×2500=$188; 8×1500=$90, 5×1000=$38. IFBench-matched 10×2500 = $150–250 range. ~$2 kill-switch = 1 lean run mm≈300 ≈ $2.25.
- Dominant error source = context growth over a run (linear UNDER-estimates; GATE1 ran mostly short seed instructions) → trust EXPECTED/HIGH. valset-eval calls are the bulk of mm but already priced in per-call (valset size trades cycles-per-$ not $/mm).
- BOTTOM LINE: GATE 2 corpus ≈ $90–190 for a properly-powered screen (low-hundreds); ~$30–50 lean/underpowered (low-tens). Because a powered screen is low-hundreds AND GATE 1's usefulness signal was genuinely mixed → RUN THE ~$2 KILL-SWITCH FIRST before funding the full corpus. $0 spent this task.


## HoVer necrosis kill-switch (2026-07-01, live $1.9602)
- Lean mm~300 HoVer run + in-sample necrosis check on the rich object. Events 33, accepted candidates 10. Artifacts: scratch/hover_probe/{necrosis_killswitch.md, necrosis_analysis.py, necrosis/}; log logs/necrosis_step1.log.
- PRIMARY ΔU nonzero on 12% of events (SPARSE→leaned on secondary). Scorers (kNN novelty/NCD/actionability/nov×act/reasoning failure-MODE) computed a/b/c, residualized on retrieval controls (recall+n_retrieved). VERDICT: INCONCLUSIVE (not a clean kill). clearly-dead=['knn_novelty', 'ncd_novelty']; inconclusive-underpowered=['actionability', 'nov_x_act', 'failure_mode'] (strongest `failure_mode` resid +0.225, output-origin). ΔU sparse (12% nonzero, n=33) -> CIs wide, exclude 0 for none; the cheap kill-switch did NOT cleanly kill and did NOT prove life. Powered screen = judgment call (needs redundancy-robust LOO, not sparse ΔU). CAN-conclude-dead / CANNOT-conclude-alive framing holds.

## Necrosis pipeline audit (2026-07-01, $0 read-only)
- Audited last night's HoVer necrosis pipeline for silent-substitution bugs (the class of the 3 known bugs). Method: independent byte recompute + 2 audit agents (code + data). Artifact: scratch/hover_probe/necrosis_audit.md.
- BUG-TRUSTWORTHY = YES. keys-vs-values CLEAN (val_subscores are real recalls in [0,1], 407 vals); event->ΔU join CLEAN (0/33 content mismatches parsed-recalls vs trace subsample_scores; trace i==pos; accepts 10=candidates-1); DEAD-collapse CLEAN (verdict3 3-state produced the table); failure_mode feature independent recompute EXACT (0.333/0.444/0.0/0.0/0.667); n_retrieved join 99/99. ΔU independently reproduced (nonzero candidates {1,2,3,5}=0.033/0.067/0.067/0.033).
- ONE FINDING (documentation, not a wrong number): residualization Z = {recall, n_retrieved} (2 controls), not the 5 implied (n_hops const, difficulty=1-recall, overlap~recall*n_gold are constant/collinear -> defensible; writeup should say 2 not 5).
- POWER-TRUSTWORTHY = NO (known, orthogonal to bugs): n=33, ΔU nonzero 12%, CIs ±0.4, (a) baseline non-null. The INCONCLUSIVE necrosis result is bug-clean but underpowered -> trustworthy AS an inconclusive result, not 'resolved'. Proposed cheap runtime guards listed in the audit (for later, not implemented).

## IFBench Wave 1 audit (2026-07-01, $0 read-only)
- Byte-audited the Wave 1 correct-object null (analysis/rescreen_wave1.md) before it headlines to Lakshya, to the necrosis-audit standard. Method: independent recompute + 2 audit agents (code + data). Artifact: analysis/rescreen_wave1_audit.md.
- LOAD-BEARING CHECK PASSED: (b) is genuinely the FULL object (Inputs+Generated Outputs+Feedback), proven 3 ways — 219/219 triple fields are verbatim substrings of the byte-proven system_prompt; (a)≠(b) (knn_a mean 0.0076 vs knn_b 0.199, 92.2% units differ); independent fresh-code TF-IDF kNN reproduces knn_novelty_b to machine precision (r=1.0000000). NOT silently feedback-only.
- Outcome = genuine batch-level LOO unique-frontier-contribution (fungibility.loo_contributions), frontier gains 0.1-1.5% on accepted batches — NOT sparse ΔU (the necrosis binding constraint). LORO folds on run/seed (8 b3). Controls = 4 difficulty + constraint_tractability_mean + 15 ct_ type-composition = 20 (matches writeup). Verdict rule = genuine 3-condition AND (constid_b>0.05 AND Δconstid(b-a)>0 AND LORO μ-σ>0); re-applied to STORED parquet -> SURVIVORS NONE; knn killed by output-origin (Δ=-0.017, output dilutes) + instability, not a CI-collapse label artifact.
- TRUST VERDICT: BUG-trustworthy = YES (no silent substitution; audit surfaced nothing new; no 2-vs-5 control gap). Known design caveats (orthogonal): TF-IDF lexical stand-in not paid embeddings (but output channel Δconstid<=0 so unlikely to reverse); knn's signal lived on the feedback string; LORO high-variance at n=8 -> pooled n=382 constid is the reliable number. Unlike necrosis (bug-clean but underpowered on sparse ΔU), Wave 1 is bug-clean AND adequately powered (n=382, LOO) -> the correct-object null is AUDIT-GRADE and safe to headline to Lakshya with caveats noted.

## Offline batch checks (2026-07-01, $0 read-only, 5 review-gated checks)
- Ran 5 offline checks from external review on the frozen corpora (IFBench 382 b3 batches / 150 examples; HoVer necrosis 33 events). Script scripts/run_offline_batch_checks.py; report analysis/offline_batch_checks.md. Design gates, not headline claims; multiplicity + HoVer-thinness noted.
- CHECK 1 (ICC): all scorers ICC(1) 0.73-0.92 on IFBench (majority between-example) -> static per-example scoring is TYPE-CORRECT; keep design (no forced move to overgenerate+filter).
- CHECK 2 (control-block R2): LOO R2=0.087 (adj 0.037), ΔU R2=0.171; best single = constraint_tractability (LOO) / iteration (ΔU). -> IFBench outcomes ~90% UNPREDICTABLE from anything -> Wave-1 null is partly a well-posedness ceiling, not purely id-absorption (the little predictable signal IS constraint-id).
- CHECK 3 (HoVer addressable ceiling): manual classify of 33 events -> reasoning-visible failures ~7% (2 clear of 30 failures, ~13% generous); ~90% are RETRIEVAL-ONLY (reasoning sound, gold doc just not retrieved), structurally invisible to failure_mode/any SI-content scorer. GATE: addressable ceiling LOW (<<30%) -> powered screen chases a ~10% minority; power-calc on (a)-subset only.
- CHECK 4 (accept-rate by scorer): collider pattern directionally present but WEAK/n.s. (nov_x_act +0.084 p=.10, failure_mode -0.018 ns); the strong accept driver is constraint_tractability +0.251 p<.001 (=difficulty). -> ungated-probe redesign = optional insurance, not compelled; divergence largely unresolved.
- CHECK 5 (batch diversity): TF-IDF dispersion vs outcome ρ=-0.011 ns (partial +0.019); HoVer -0.109 ns. -> NO batch-diversity signal; drop the DPP/aggregation-washout worry.

## Gate flip-rate probe (2026-07-02, $0 read-only, IFBench frozen corpus)
- Pre-qualified the GATE direction before live spend: on 267 logged-REJECTED b3 children (per-constraint parent/child binary), does an aggregate accept rule flip any to accept vs the pointwise gate? Script scripts/run_gate_fliprate_probe.py; report analysis/gate_fliprate_probe.md. IFBench only (HoVer necrosis logs only scalar recall, no per-doc binary).
- FLIP RATES: R1 majority-fix 0.4% (1/267, inert); R2 minimax-lineage 2.6% (7); R3 weighted-coverage 6.0% (16); ANY rule 6.7% (18/267). Rules flip mostly DIFFERENT children (R2∩R3 Jaccard 0.28; all-3=1). Fixes land on HARDER constraints than losses (R2 0.73 vs 0.45; R3 0.57 vs 0.37) but the clean 'fix>=2 stubborn, lose<=1 easy' texture is RARE (3 flips total); most are 1-fix-1-loss washes. R2 can admit net-negative 1-fix-3-loss trades (needs a no-regression guard).
- HONESTY GUARD: corpus CANNOT say flips improve U (rejected children never got a valset eval — acceptance gates the broad eval = collider). Probe answers ONLY 'does aggregate gate behave differently from pointwise' — NOT evidence the gate works.
- VERDICT: flip-rate NOT ~0 (kill threshold not met) -> LEAN GO on DESIGNING the live gate experiment, but effect is SMALL (~1-in-15 rejects, ~2-3 extra accepts/run). Design notes: drop R1 (inert); R3 workhorse, R2 aggressive-minimax needs no-net-regression guard; power the paired-seed run for a ~7%-of-rejects delta; only a live run with UN-GATED valset eval proves it helps.

## Check-3 spot-check (2026-07-02, $0 read-only)
- Verified the offline-batch Check-3 HoVer addressable-ceiling classification before it goes to Lakshya (rested on one model's manual judgment of 30 thin failures). Re-judged 8 stress-selected events on BYTE-COMPLETE reasoning (original used ~300-char trimmed). Artifact: analysis/check3_spotcheck.md. Frozen necrosis capture untouched.
- FINDING: both original 'reasoning-visible' cases (ev1 Greek Fire, ev10 Philip Glass) FLIP to retrieval-only on full reasoning — the trimmed text had hidden the parts where the reasoning correctly named/targeted the missed entity (I mis-read them). All 3 borderline 'reasoning-names-entity' cases (ev4/13/18) + 3 calibration cases HOLD as retrieval-only. Sharpest: ev18 reasoning correctly resolves Michael->Mikael Åkerfeldt misspelling yet doc unfetched -> definitively retrieval-only.
- RESULT: addressable fraction 2/30 -> 0/30 on spot-check. The ~90%-retrieval-only headline SURVIVES and STRENGTHENS (~97-100% on checked subset); content-scorer addressable ceiling <=7%, plausibly ~0-3% — even LOWER than the email states (correction moves AGAINST the content direction, not a rescue). Caveat: re-read 8/30 (the 2 addressable + strongest borderlines + calibration), did not exhaustively re-read the other 22. Methodological note: judge on byte-complete reasoning, not trimmed spans.

## Closeout verification (2026-07-02, $0 read-only, 2 review holes)
- Patched two holes in the scorer-direction closing argument before the external update. Script scripts/run_closeout_verification.py; report analysis/closeout_verification.md. Frozen corpora untouched.
- STEP 1 (routing): gen_query IS in Φ (6 distinct instructions across 11 necrosis candidates) -> H2 LIVE (C3's retrieval-only ceiling is structurally mis-scoped; queries are optimizable).
- STEP 2 (H1 fix, the NEW closing stat replacing R²=0.087): OUTCOME ICC by example — ΔU ICC=-0.003 [-0.034,+0.032], LOO ICC=+0.024 [-0.017,+0.061] -> between-example ≈0 => NO per-example target => per-example content selection CLOSED WITH PREJUDICE (kills learned scorer/LOSO/edit-attribution/rollout-observed in one number). HoVer thin ICC≈0.
- STEP 2b (corrects an overclaim): hurdle split — P(accept)~controls AUC=0.706; ΔU|accept~controls R²=0.50 (adj~0.39). So the outcome is NOT '~90% unpredictable' — it's ~40-50% predictable from DIFFICULTY/CONSTRAINT-ID (top-decile enriches tractability +0.124, difficulty +0.050; content scorers do NOT enrich). Correct close = 'no per-example target', not 'unpredictable'.
- STEP 3 (H2 empirical): 5/10 accepted candidates edit gen_query (full rewrites) BUT valset recall flat/declining (seed 0.433 -> best 0.467 -> 0.367). So C3's ceiling is not structurally airtight but held EMPIRICALLY in this n=1 thin run (GEPA's query edits didn't fix retrieval).
- STEP 4 (H2 named scorer): retrieval-fixability signature (entity named in reasoning/notes, absent from retrieved AND from queries) = 4/30 = 13% prevalence on HoVer (thin). Samples: ev2/ev25 'Beached Az', ev22 'Jeremy Brock'.
- BOTTOM LINE: (b) CLOSED EXCEPT a named untested scorer. Per-example content selection closed with prejudice (ICC≈0). But (1) the '90% unpredictable' framing was wrong (correct it to 'no per-example target'); (2) C3 was mis-scoped (queries in Φ). One named untested candidate remains: the retrieval-fixability scorer (13% prevalence, query surface not reflection-text surface) — only a paired-seed live run could move it. NOT (a) airtight, NOT (c) reopened.

## Adjudication follow-up (2026-07-02, $0 read-only, 3 analyses)
- Adjudication returned: (1) retracted the closing outcome-ICC≈0 as smearing-biased, (2) ordered lag-1 autocorr, (3) ordered IPS policy-value of a tractability sampler. All $0 on frozen IFBench. Script scripts/run_adjudication_followup.py; report analysis/adjudication_followup.md; CSVs task1_sim_validation/task1_icc/task2_pairs/task3_ips.
- TASK 1 (crossed random-effects ICC, multiple-membership REML+MoM; MANDATORY sim-validation PASSED, max bias 0.041; estimator has a +0.041 null-floor at true ICC=0): ΔU corrected ICC = 0.000 [0,0.243] (at/below the null-floor -> STILL ≈0; the smearing did NOT hide a ΔU signal; naive -0.003). accept corrected ICC = 0.086 [0,0.334] vs naive 0.009 -> deflation REAL (~9x) for accept -> a WEAK per-example acceptance component exists. Net: 'no per-example target' HOLDS for revision-value ΔU, SOFTENED for accept. Caveat: CI upper 0.24 -> underpowered to rule out up to ~0.24 (8 runs).
- TASK 2 (lag-1 autocorr; 121 pairs but from only 3 runs >1 epoch): ΔU raw r=+0.011, perm-null p=0.90 (dead center); accept r=+0.054 p=0.51; residualized r=+0.031. NO detectable per-example outcome persistence -> the bandit/decay resampler premise is unsupported. Underpowered (rules out only |r|>~0.2); batch smearing makes raw r a floor.
- TASK 3 (SNIPS IPS, propensity=uniform-over-triples by epoch-shuffle exchangeability, cancels; β=0 identity check PASSED to 9e-19): only β=0.5 usable (ESS=144) -> small +12% one-step ΔU lift but CI overlaps uniform (not significant). β=1 ESS=13, β=2 ESS=2 -> UNUSABLE. One-step sampler value small-or-null; aggressive tilts unevaluable on logged uniform data. Scope: one-step reward under logged states; live run needed for trajectory.
- VERDICT: direction stays closed on the evidence, but honest statement = 'no strong per-example / persistence / sampler signal detected', NOT proof-of-zero (CIs wide at 8 runs). Corrected model surfaced ONE weak positive: accept-ICC 0.086. ΔU (the value target) remains ≈0 even after the smearing fix.

## Adjudication addendum A1-A3 (2026-07-02, $0 read-only): A1 provenance reconciles (10 runs=8 b3+2 b1; 487 events; 382 b3 batches from the 8 b3 runs; 'no problem'). A2: extended crossed-RE accept model with frozen per-example difficulty/constraint-id covariates (sim re-validated, new floor ~0.05) -> residual accept ICC +0.111 [0.000,0.359] SURVIVES (above floor; σ_v² rose 0.092->0.122, σ_ε² held -> not a denominator artifact) => the weak accept component is NOT explained by difficulty, but weak/underpowered (CI reaches floor). ΔU per-example ICC still ≈0 (primary close unchanged). A3: disattenuated lag-1 ≈0.033 (DERIVED, <0.1, conclusion unchanged). Artifacts: scripts/run_adjudication_addendum.py, analysis/addendum_a2_icc.csv.

## Feedback-ablation experiment (2026-07-02, live $7.74)
- Adjudication Q5 causal test: does the reflection proposer USE the Feedback section of the 3-section per-example object, or re-derive from Inputs+Outputs? First channel-manipulation (not correlational). Frozen IFBench, all under analysis/ablation/. Scripts run_ablation.py + run_ablation_analysis.py; deliverables plan.md, selected_batches.csv, calls.csv (500 arm-calls), results.md.
- STAGE 0: byte-fidelity gate PASS (reconstructed proposer input == logged wire bytes 8/8; logged==wire proven in reflection_capture/equality.json). 150 b3 batches stratified (8 runs x iter-terciles, seed 20260702); 3 arms + seed-repeat on 50; gate re-evals parent+child TODAY (drift-clean; parent today 1.587 vs logged 1.617). MDE ~10-12pp (McNemar n=150).
- STAGE 1-2 RESULT: accept rates i=0.340 / ii(Feedback deleted)=0.313 / iii(generic)=0.367 — all within 3pp, NON-SIGNIFICANT (McNemar/perm p>=0.63); gate margins likewise n.s.; point estimates trend OPPOSITE to 'content helps' (within noise). Independent 2nd-path recompute matches. => (i)≈(ii)≈(iii): the Feedback channel is CAUSALLY INERT on IFBench checklist SI (this regime only). Explains why the 20 Feedback-object scorers were poor proxies: they scored a causally-weightless channel.
- KEY: proposer LOTTERY dominates — same arm (i) called twice flips the accept decision 32% of the time; within-arm margin variance (0.078) dwarfs the ~0.027 between-arm effects. Any real feedback effect is an order of magnitude below proposer call-to-call noise.
- SCOPE CAVEATS (verbatim in results.md): IFBench constraints are verifiable from Inputs+Outputs -> nothing generalizes to rich-prose SI (HoVer, unmeasured). Null bounded by MDE ~10-12pp, one-step gate only (not downstream U), model base-names not snapshots. Actual spend $7.74 vs ~$8 projection.

## 2026-07-02 — Batch-swap v1 ABORTED; v2 (2×2 reflect×gate) designed, gated on APPROVED_V2
- v1 KILLED at $0.34 (4/382 batches) on external review: its sole endpoint (reflect-on-B gated-on-B vs
  reflect-on-B′ gated-on-B) is teach-to-the-test — a positive Δ is expected under everyone's null and
  reopens nothing. v1 output preserved read-only in analysis/ablation/batch_swap_v1_ABANDONED/ (unused).
- v2 = 2×2 (reflect × gate): separates SPECIFICITY (matched-example advantage on the gated batch, = a
  within-B child difference so run/batch structure cancels) from TRANSFER (does reflecting on B help on
  UNSEEN, failure-matched B′ — the quantity that connects to selection + downstream U). Corrections
  adopted: B′ failure-matched under B's ACTUAL parent (≥2/3 fail) so Δ isn't difficulty through a side
  door; constraint-type Jaccard logged for an example-vs-type overlap decomposition; inference respects
  run-level clustering (8 runs) via cluster bootstrap + within-run sign-flip permutation.
- TWO GATE VIOLATIONS drove a mechanical fix: (1) v1 launched paid without Neel seeing a plan; (2) it
  answered the uncontested question. v2 has two physical gates: batch_swap_v2_stage0.py is $0-only
  (monkeypatches gepa.lm.LM.__init__→SystemExit; proven to block), and batch_swap_v2_run.py refuses to
  start unless analysis/ablation/APPROVED_V2 exists (Neel-only file; mtime logged).
- Stage 0 ($0, done): projected failure-match 382/382 eligible (base fail-propensity 0.72), 0 drops;
  type-Jaccard median 0.30 (usable leverage for the decomposition, not uniformly high); cost ~$29
  (proposer 1528 + task ~12.6k; cap $60, tripwire $55); ETA ~8h @ ~75s/pair; recommended k=3.
- POWER (honest): pooled-specificity MDE 0.040 (k=2)/0.033 (k=3) at ρ=0, meets ≤0.04 ONLY if the
  within-pair differencing zeroes run-ICC (expected). Adding draws does NOT fix clustering — the Stage-2
  run-cluster bootstrap reports the REALIZED CI as the arbiter. Transfer (single margin) is wider.
- STATUS: AWAITING APPROVED_V2. Scripts written+compiled: batch_swap_v2_{stage0,run,analysis}.py. No paid
  call has run for v2.

## 2026-07-05 — Batch-swap v2 EXECUTED ($38.74, both estimands ≈0 → selection causally inert)
- Neel approved (APPROVED_V2 created 2026-07-04 23:31). Ran the full 2×2 (reflect × gate) on 382
  failure-matched pairs, K=3 draws/arm. proposer gpt-4.1 $22.72 + task gpt-4.1-mini $16.03 = $38.74
  (over the ~$29 Stage-0 projection — actual $0.10/pair vs $0.076 assumed — but under the $55 tripwire).
  Deliverables analysis/ablation/batch_swap_v2/{results.md,calls.csv,pairing.csv}; run-card
  notes/runs/2026-07-05-batch-swap-v2.md.
- RESULT (numbers-first, run-cluster CI is the arbiter): pooled SPECIFICITY +0.0054, perm p=0.60, CI
  [-0.0116,+0.0242]; pooled TRANSFER -0.0011, perm p=0.93, CI [-0.0243,+0.0228]. BOTH ≈0 within MDE
  0.033 → the pre-registered "strongest Claim A" cell: the per-example selection channel is causally
  inert at the one-step acceptance gate EVEN for the same example (specificity) — not just a
  transfer/difficulty artifact. Independent 2nd-path recompute matches to 1e-9.
- SUPPORTING: lottery within-arm accept disagreement 0.382 (n=764; ↑ vs prior 0.32) — proposer
  call-to-call noise dominates, consistent with the feedback-ablation finding. Overlap decomp
  predicted@jac=1 +0.051 but off a ≈0 base (not meaningful). Failure-count stratum B'_fail=2 +0.077 is
  n=20 noise; main n=362 stratum +0.0015.
- SCOPE (in results.md): one-step gate ≠ downstream U; IFBench verifiable-SI regime only; bounded by
  MDE ~0.033 (cannot rule out effects smaller than that). This causally CONFIRMS the correlational
  selection nulls (outcome-ICC≈0, feedback-ablation). Selection direction closed at the causal grain;
  the acceptance-gate lever (gate flip-rate 6.7%) remains the only untested live direction.
- OPS NOTE: run kept dying on laptop sleep (hung SSL reads: API calls had no timeout; and harness
  reaped session-tied background tasks). Fixed by (a) timeout=180 on both LMs so hung sockets raise +
  retry, (b) a detached self-resuming supervisor (scripts/v2_supervisor.sh, nohup→launchd, resumes from
  checkpoint, waits-for-exit so no double-spend). Completed on the first supervised launch, 0 restarts.
