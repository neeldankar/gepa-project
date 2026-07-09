# HoVer heterogeneity screen — scorer SPEC (frozen pre-outcome)

Frozen 2026-07-09, before any scorer column is joined to any outcome column. Tag:
`screen-spec-frozen`. Every definition, parameter, and format-dependent choice for
`features.csv` lives here. Phase B statistics run only on what this file defines.

Unit of analysis: the EVENT, keyed `(seed, trace_i)` (243 events; child-bearing
`full_program_trace` entries only; seeds 2/6 child-less indices {5,15}/{27} excluded by
construction). Verified 0.4: pair dirs ↔ child-bearing trace entries ↔ reflection events are
one-to-one 243/243; `meta.json:A_e_pos == subsample_ids` 243/243; b = 3
(`stage1_run.py:163` `reflection_minibatch_size=3`, and every trace batch has size 3).

## Locked upstream decisions

1. **Class B SI source (user decision, 2026-07-09):** the event's "current SI" is Stage-2
   `pairs/seed<S>_i<T>/reflect_in_SAME.txt` — the exact bytes that produced the measured
   swap outcome. History archives are the prior events' `reflect_in_SAME.txt` **in the same
   run, in event-ordinal order, strictly before the current event**. No cross-run pooling.
   No future leakage. (Verified 0.2: all 243 objects carry Inputs / Generated Outputs /
   Feedback for all 3 example blocks; verified 2.1: SI example-block order == `A_e_pos`
   order, claim and gold cross-checks 729/729.)
2. **SI item granularity:** the per-example unit is the `# Example k` block. Section
   extraction per `screen_part0.parse_si` (split on `^## (Inputs|Generated Outputs|
   Feedback)$`, MULTILINE; last block cut at the closing code fence).
3. **Text variants (scorers 9–13), computed as three separate columns each:**
   - (a) `fb`: the `## Feedback` section text only.
   - (b) `full`: `Inputs + "\n" + Generated Outputs + "\n" + Feedback` of the block.
   - (c) `delta`: defined per scorer below; unless stated otherwise it is the score-level
     difference `full − fb` (not a text-level operation).
4. **TF-IDF (causal):** at event ordinal `o` in run `r`, vectorizers are **refit from
   scratch** on the archive texts of ordinals `< o` in run `r` only (chosen over
   incremental vocabulary restriction; n ≤ 33 texts per fit makes refitting exact and
   cheap). Two vectorizers — word 1–2-grams and char_wb 3–5-grams (scikit-learn
   `TfidfVectorizer`, default tokenization/lowercasing, `sublinear_tf=True`) — similarity =
   mean of the two cosine similarities. Empty archive (o = 0) → scorer NaN.
5. **Embedding variant:** added only if `sentence-transformers` installs cleanly in the
   dedicated screen venv and runs fully locally (`all-MiniLM-L6-v2`; model download only,
   zero API calls). Applies to scorers 9 and 12 as extra columns (`_emb`). If absent,
   TF-IDF-only is noted in results and no `_emb` columns exist.
6. **Batch aggregation:** every per-example feature yields four event columns —
   `_mean, _max, _min, _std` (population σ, ddof = 0) over the ≤3 non-NaN example values —
   plus `_n` (count of non-NaN example values, the coverage column) where NaN is possible.
   All three NaN → event NaN.
7. **BM25 ranks:** from `bm25_ranks.csv` (built by `screen_bm25.py` under
   `scratch/hover_probe/.venv`, memory-mapped index via the `hover_swap_run.py` monkeypatch
   pattern; `probe.py` untouched, SHA-256 verified). Rank = 1-based position of the title's
   first occurrence in `probe.search(claim, k=1000)` (probe's own tokenizer/stemmer path).
   **Censoring: not found within k = 1000 → recorded as −1 in the CSV, imputed as 1001 for
   all feature arithmetic.** Rank transform used in features: `−log10(rank)`.
8. **Prior-score pool (scorers 1–3):** the recorded within-run evaluations of example `x`
   strictly before event `e`: `subsample_scores[j]` and `new_subsample_scores[j]` at every
   child-bearing event `e' < e` (ordinal order) with `x` at slot `j`. Both parent and child
   scores count as "prior scores on the example". Never-visited → NaN.
9. **Accept flag:** `accept_e = sum(new_subsample_scores) > sum(subsample_scores)`
   (strict), validated per seed against `run_summary.json:accepts_inferred` and
   `candidates_incl_seed = accepts + 1` (all 8 seeds pass). Recorded in `outcomes.csv` and
   `features.csv`; **collider — never a regressor.**

## 0.1 reconciliation vs `analysis/scorer_portability.md`

That roster maps the 13 implemented IFBench **selection** scorers (selection direction since
closed at the causal grain, batch-swap v2 2026-07-05). Divergences from this screen's roster:

- Carried over in spirit: portability's four "never-implemented, worth building on HoVer"
  stubs — embedding-kNN novelty, NCD, actionability-as-specificity, novelty×actionability —
  are exactly scorers 9–12 here, now instantiated.
- `input_typicality` (port-as-is) reappears here as scorer 7 (representativeness), with
  trainset (not valset) as the reference set per this screen's definition.
- Not carried: `typicality_x_headroom`, `pool_disagreement_voi`, `output_repairability`,
  `output_n_words`, `leverage`, and the 7 constraint-keyed reimplementation candidates
  (incl. `constraint_tractability`). They are selection scorers for a closed direction and
  are outside this screen's pre-registered roster; no new scorers are imported from them.

## Coverage facts that bind interpretation (from Part 0/2 probes, pre-outcome)

- **Revisit collapse (0.6):** GEPA's sampler sweeps the 100-example trainset nearly without
  replacement within a run: 4/725 example-slots corpus-wide are second visits; 2/243 events
  contain any revisited example. Scorers 1–5 and 17, as pre-registered (within-run,
  strictly-before), therefore have ≈0 coverage; they are computed as defined and their
  coverage columns carry the fact. **No silent redefinition.**
- **Signature probe (2.1):** corpus-wide instance singleton shares — per-example 0.0713,
  per-batch 0.9918. Kill rule (>0.85 at BOTH grains) NOT triggered → scorers 14/16 computed.
  Within-run per-example instance singleton share mean 0.7878; per-batch 1.0000.
- **Feedback format fact (0.3/si_sample.md):** `build_si` always names every missed gold
  title verbatim and always prints the retrieved-vs-remaining contrast. The briefed
  candidate actionability definition ("share of missed titles named verbatim + presence of
  contrast") is structurally constant in this format; scorer 11 below is the frozen
  re-instantiation against what actually varies.

## Scorer definitions

### Class A — observable at selection time (deployable)

1. **difficulty_inverse_best** — per example: `1 − max(prior-score pool)` (item 8);
   never-visited → NaN. Columns `diffbest_{mean,max,min,std,n}`.
2. **difficulty_mean** — `1 − mean(prior-score pool)`; NaN as above.
   Columns `diffmean_{...}`.
3. **peakedness** — `s̄(1−s̄)`, `s̄` = mean of prior-score pool; NaN as above.
   Columns `peaked_{...}`.
4. **staleness** — `ordinal(e) − ordinal(last prior visit)`; never-visited max-code
   `ordinal(e) + 1` ("stale since before the run"). Columns `stale_{...}` plus
   `stale_never_share` (share of batch never visited).
5. **visit_count** — number of prior visits (0 for never-visited).
   Columns `visits_{...}`.
   *(A1, flagged ADDITION — frozen now, pre-outcome, counted in Phase B multiplicity;
   motivated by the 0.6 revisit collapse, subject to veto at the Phase A gate):*
   **difficulty_baseline** — `1 − recall` from `graded_records.jsonl` (the pre-run grading
   pass; static, observable at time 0). Columns `diffbase_{mean,max,min,std}`.
6. **claim_features** — per example: `claim_tok_len` (whitespace token count of the claim);
   `n_gold` (gold-title count); retrieval hardness from `bm25_ranks.csv`:
   `hard_worst = −log10(max rank over gold titles)`, `hard_mean = mean(−log10 rank)`
   (censored → 1001 per item 7). Columns `ctok_{...}`, `ngold_{...}`, `hardworst_{...}`,
   `hardmean_{...}`, plus `hard_censored_n` (censored gold titles in batch).
7. **representativeness** — mean TF-IDF similarity (item 4 vectorizer pair, but fit ONCE,
   statically, on the 100 shared trainset claims — no leakage: claims are static pre-run
   data) of the example's claim to the other 99 trainset claims. Columns `repr_{...}`.
8. **valset_targeting** — per example: `vt_count = Σ_{t ∈ gold(x)} count(t in valset gold
   multiset)` (10 valset examples × 3 gold titles) and `vt_any = 1[vt_count > 0]`.
   Columns `vt_count_{...}`, `vt_any_{...}`.

### Class B — requires realized SI (channel test, not deployable)

Text variants and archives per items 1–5 above. Ordinal 0 events → NaN (no archive).

9. **knn_novelty** — per example block: `1 − cosine similarity`, averaged over the k = 3
   nearest archive per-example blocks (matched variant text); archive < 3 items → NaN
   (affects ordinals 0 of each run for the event grain; per-example archive has 3 items per
   prior event, so only ordinal 0 is NaN). Variants: `knn_fb`, `knn_full`,
   `knn_delta = knn_full − knn_fb`. Optional `knn_emb_{fb,full,delta}` (item 5).
   Columns: each × `{mean,max,min,std}`.
10. **ncd_novelty** — per example block vs the concatenated archive (matched variant texts,
    ordinal order, `"\n\n"`-joined): `NCD(x, y) = (C(y + x) − min(C(x), C(y))) /
    max(C(x), C(y))`, `C` = `len(zlib.compress(bytes, level=9))`, concatenation order
    archive-then-current (documented choice; zlib's 32 KB window means redundancy is
    detected against the most recent ≈32 KB of archive — recorded as a known limitation of
    the zlib instantiation, faithful to the original NCD definition otherwise).
    Empty archive → NaN. Variants `ncd_fb`, `ncd_full`, `ncd_delta = ncd_full − ncd_fb`;
    each × `{mean,max,min,std}`.
11. **actionability** — frozen re-instantiation (see format fact above). Per example block:
    - C1 = `n_missed / n_gold` (share of gold the feedback names as remaining);
    - C2 = `1[n_correct > 0 AND n_missed > 0]` (a real retrieved-vs-gold contrast:
      both lists non-empty);
    - C3 = share of missed titles whose exact string appears (case-insensitive substring)
      in the block's Inputs or Generated Outputs text — the entity was already surfaced
      upstream but not retrieved (the maximally concrete, nameable miss). n_missed = 0 → C3
      undefined for that example (NaN).
    Variants: `act_fb = (C1 + C2)/2` (feedback-only), `act_full = (C1 + C2 + C3)/3`
    (C3-NaN example → `act_full` NaN), `act_delta = C3` (the full-object increment, per-
    scorer delta definition). Each × `{mean,max,min,std}`; `act_delta_n` coverage.
    Overlap note: C1 = 1 − parent recall on the example; the 4.2 orthogonality read
    (difficulty-family controls) is the pre-registered handling.
12. **novelty_x_actionability** — matched-variant products, computed at the example level
    then aggregated: `nxa_fb = knn_fb × act_fb`, `nxa_full = knn_full × act_full`,
    `nxa_delta = knn_delta × act_delta`. Optional `nxa_emb_* = knn_emb_* × act_*`.
    Each × `{mean,max,min,std}`.
13. **failure_mode** — output-derived typology, per example block, full-object by
    construction (single variant). Precedence:
    - F0 `no_failure`: n_missed = 0;
    - F1 `malformed`: the primary output field is degenerate — for `gen_query.predict`
      events the `### query` text has < 5 whitespace tokens; for `append_notes.predict`
      events `### new_notes` or `### titles` is empty (`[]` or blank);
    - F3 `retrieval_miss`: every missed title's string appears (case-insensitive) in the
      block's Inputs or Generated Outputs — surfaced but not fetched;
    - F2 `entity_miss` (else): ≥1 missed title never surfaced — chain break.
    Event columns: `fm_f1_share`, `fm_f2_share`, `fm_f3_share` (shares over the 3 examples;
    F0 share = 1 − sum).
14. **signature_novelty** — per example: signature = sorted tuple of missed titles;
    `1[signature ∉ in-run archive of prior events' per-example signatures]`; empty
    signature (n_missed = 0) → NaN (no failure to be novel about). Ordinal 0 → 1 where
    defined. Columns `signov_{mean,max,min,std,n}`. [2.1 gate: passed — computed.]
15. **fixability** — per example: `−log10(best rank)` where best rank = min over the
    example's MISSED titles of the `bm25_ranks.csv` rank (censored → 1001); n_missed = 0 →
    NaN. Columns `fix_{mean,max,min,std,n}`. [2.2 feasibility: see probe results.]
16. **co_failure** — per example with n_missed ≥ 2: share of its unordered missed-title
    pairs already present in the in-run archive of prior events' co-missed pairs;
    n_missed < 2 → NaN. Ordinal 0 → 0 where defined. Columns `cofail_{mean,max,min,std,n}`.
    [2.1 gate: passed — computed.]
17. **forgetting** — per example with ≥1 prior visit: `1[best prior score on x >
    current parent score on x at e AND that best prior score was itself an improvement
    (a child new_subsample_score > its same-event parent score, or a later visit scoring
    above an earlier one)]`; never-visited → NaN. Coverage-limited per 0.6 (2/243 events
    have any defined example). Columns `forget_{mean,max,min,std,n}`.

### Controls (in features.csv; used per Part 4 rules)

- `iteration` = event ordinal within run (0-based).
- `parent_pool_score` = mean of `prog_candidate_val_subscores[parent_candidate_idx]`
  (the parent's 10-example valset mean; static per candidate).
- `parent_candidate_idx` (categorical parent identity), `seed` (cluster), `comp`
  (component name, recorded), `accept` (recorded; **collider — kept out of all models**).

## Files

- `features.csv` — one row per event (243), columns as named above plus keys
  `pair_id, seed, trace_i, event_ordinal`.
- `outcomes.csv` — Part 1 outcome table (written before this spec's features; never joined
  to features in Phase A).
- `bm25_ranks.csv` — per (example, gold title) rank table, censoring per item 7.
- Extraction code: `screen_part3_features.py` (screen venv; BM25 columns joined from
  `bm25_ranks.csv`, no index load).
