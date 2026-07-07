# Full scorer re-screen on the real reflection object (IFBench)

**DATE:** 2026-06-30
**Supersedes:** nothing — this is a NEW work item, not a handoff continuation.
**Prior handoffs (remain valid for history; THIS file is the live task):** `analysis/PROJECT_STATE.md`
(canonical project handoff) and the probe/audit reports it indexes —
`analysis/{scorer_portability.md, scorer_audit.md, integrity_checks.md, probe_leverage_flatness.md,
probe_leverage_disambiguation.md, raw_vs_parsed_diff.md, hover_scope.md, hover_viability_summary.md}`
and `analysis/reflection_capture/REPORT.md`.

---

## WHY THIS EXISTS (the correction)
Every scorer/probe to date was computed on the evaluator **Feedback string** only. Direct byte-capture
(`analysis/reflection_capture/`) proved the reflection LM actually receives, PER EXAMPLE:
1. **Inputs** — the task prompt
2. **Generated Outputs** — the parent model's verbatim completion (nothing stripped)
3. **Feedback** — the per-constraint grading checklist  ← the ONLY part ever scored

Program = Predict / DefaultAdapter, task LM (`gpt-4.1-mini`) non-reasoning → NO reasoning/CoT channel
exists; this 3-section object is the whole story, confirmed **3-way byte-identical** (wrapper == litellm
wire == logged `proposal_end.prompts.system_prompt`), and `raw_lm_outputs` is the PROPOSER's fenced
instruction, NOT a per-example task field (`analysis/raw_vs_parsed_diff.md`: 0/394 events have any extra
per-example field; the only delta anywhere is a ≤9-char ``` fence on the proposer output). So prior
scorer results were computed on the wrong (thinnest) object. **We re-screen on the real object.**

## SCORING UNIT (get this right)
The proposer reads a **b=3 minibatch jointly**. The per-example unit we curriculum over is one
example's slice = its **(Inputs, Generated Outputs, Feedback) triple**. Text features are computed on
the FULL triple (or output-conditioned-on-input), NOT any single field in isolation — that is what
"what the proposer sees" means. **Re-confirm the slice structure against
`analysis/reflection_capture/reflect_1.txt` before computing anything** (it shows
`# Example N / ## Inputs / ## Generated Outputs / ## Feedback`).

## THE TASK — re-run the ENTIRE scorer roster on the new object
Do **NOT** skip any scorer on the argument it "can't have changed." Run all of them.

- **[text-reopens]** (read free-text; were null on the id-deterministic Feedback string, but the OUTPUT
  is NOT id-determined so the collapse argument does not transfer — expected to MOVE):
  `input_typicality`, `typicality_x_headroom`, `output_repairability`, `output_n_words`, and the four
  never-built semantic scorers now built on the full triple — `embedding-kNN novelty`,
  `NCD/compression distance`, `actionability-as-specificity`, `novelty×actionability`.
- **[score-control]** (read logged per-example/per-candidate SCORES or constraint identity, not text →
  must return **BIT-IDENTICAL**; run anyway as the receipt that the harness didn't silently change):
  `constraint_tractability` (PRIOR SURVIVOR, partial-LOO 0.172), `valset_prevalence`,
  `prevalence_x_headroom`, `parent_near_frontier`, `pool_disagreement_voi`, `seed_to_parent_regression`,
  `coverage_gap`, `coverage_gap_x_prevalence`, `leverage`, and the id-keyed `failure-signature` family
  (ceilinged-dead, Filter-2). [Note: the original brief lumped `failure-signature` with text scorers; it
  is id-keyed → control. The NEW failure-MODE below is the text version.]
- **[new]** — ADD an **output-derived failure-MODE signature**: the texture visible in rejected/low-score
  outputs (e.g. clumsy constraint near-misses — wrong count, fence/format almost-right, truncated
  postscript), parsed from `Generated Outputs` conditioned on the failed constraint, **distinct from the
  dead id-keyed failure-signature**. Specify it concretely (a small set of output-pathology features),
  then screen it like the rest.

**Canonical roster source** (enumerate from here so nothing is missed): code
`gepa_si/screen/{scorers.py, scorers_wave2.py, scorers_wave3.py}` (12 built scorers →
`analysis/scorers.parquet` columns), `analysis/scorer_portability.md` (full 13 signals incl. `leverage`
+ the 4 never-built semantic), and the leverage probes (`scripts/probe_leverage_*.py`). Prior screen
results to compare against: `analysis/scorer_ranking.parquet`, `analysis/scorer_audit.{parquet,md}`,
`analysis/integrity_checks.md`.

## METHOD (match the prior screen exactly so results compare)
- **Outcome:** leave-one-candidate-out (LOO) unique frontier contribution (redundancy-robust;
  `gepa_si/screen/fungibility.py`). ΔU (`gepa_si/screen/delta_u.py`) is difficulty-confounded via
  headroom — keep as SECONDARY only.
- **Aggregation:** per-event → batch (mean headline + sum secondary), screened on the **8 b3 runs**
  (the 2 b1 runs held aside), matching `gepa_si/screen/screen_scorers.py`.
- **CV / hardening:** leave-one-RUN-out (run = fold); the prior stat protocol
  (`analysis/integrity_checks.md`) = **permutation-MAX null over the full variant set (M=43, ≥3000
  permutations of the LOO labels), the 4 difficulty controls residualized via rank-partial-Spearman,
  LORO mean±sd, bootstrap CI over runs, NO Wald p-values.** Re-use it verbatim and re-run the
  permutation-max null with the new text variants ADDED to M.
- **CONTROL FOR CONSTRAINT IDENTITY (the central methodological point):** the collapse risk is that
  output features are just constraint-id composition in disguise. Evaluate every [text-reopens] scorer
  **BOTH raw AND residualized on the constraint-identity / difficulty controls**
  (`CONTROLS = [difficulty=mean(1−s), n2_peakedness=mean s(1−s), parent_dpareto, iteration]` from
  `gepa_si/screen/ceiling_probe.py`, plus the per-type fail-rate / failed-type-composition control from
  the integrity check). A scorer **survives only if it adds signal beyond constraint identity** —
  variance ≠ usefulness.
- **$0:** pure offline analysis on the FROZEN corpus. No live runs, no LM calls. Confirm the frozen logs
  are untouched: `logs/baseline_*.jsonl` (mm=2500, dated 2026-06-26/27).

## CORPUS FACTS (verified 2026-06-30)
- **10 runs**: 8× b3 (seeds 0–7; cycles 39, 34, 42, 41, 63, 64, 60, 39) + 2× b1 (seeds 0–1; cycles 45,
  60). **487 cycles/events** total. `max_metric_calls=2500`, valset = **150**, **54 constraint ids / 16
  type buckets**. Models: task `openai/gpt-4.1-mini`, reflection `openai/gpt-4.1`, split seed 0.
- Logged per-example: Inputs, Generated Outputs, Feedback (`reflective_dataset_built`), per-constraint
  binary scores parent+child (`evaluation_end.objective_scores`), per-candidate×valset scalars
  (`valset_evaluated.scores_by_val_id`). **`raw_lm_outputs` = the PROPOSER's fenced instruction,
  per-component — NOT a per-example task field.** Do not confuse the two (`analysis/raw_vs_parsed_diff.md`).

## DELIVERABLE
- One results table: `scorer | tag | prior(feedback-string) metric | new(full-object) raw metric |
  new residualized-on-const-id metric | survives?`
- **Explicit equality assertion for every [score-control] scorer (prior == new), bit-for-bit.**
- Short verdict: did ANY text scorer survive residualization on the real object, or does the null hold
  on the RIGHT object now (a much stronger claim than the prior null on the thin object)?
- Write findings to a **new dated `analysis/PROJECT_STATE.md` note** (idempotent; do NOT overwrite prior
  notes) + a standalone `analysis/rescreen_full_object.md`.

## STANDING OPERATING FACTS
- Desktop session writes briefs; CC executes in repo. Neel reviews CC plans before execution.
- $ discipline: offline = $0 (free). Live GEPA runs cost real OpenAI money — flag the figure BEFORE any
  spend, report actual after. **This task is $0; if anything in it would cost money, STOP and flag.**
- Don't hype the output object before the screen confirms signal — the prior error was scoring an object
  without checking it. **Verify, then analyze.**
- NotebookLM (notebook `d642bb7e-9a49-4fb0-ba1c-095bac51be29`): `notebook_query` works;
  `notebook_get` / `source_list_drive` may time out → fall back to `web_fetch` on arXiv/HTML.

## FIRST ACTIONS for the resuming session
1. Read this file fully.
2. Read `analysis/reflection_capture/reflect_1.txt` + `analysis/raw_vs_parsed_diff.md` to load the
   object definition.
3. Pull the canonical prior scorer roster (sources above); enumerate every scorer with a tag.
4. Confirm the frozen corpus is untouched (`logs/baseline_*` mtimes 2026-06-26/27; do not touch
   `logs/phase2/`, `logs/hotpot/`).
5. Propose the re-screen plan back to Neel for review BEFORE executing.
