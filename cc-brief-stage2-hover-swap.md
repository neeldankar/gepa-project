# CC Brief — Stage 2: batch-swap on the HoVer Stage-1 corpus

**Repo:** `gepa-si-curriculum`
**Depends on:** completed Stage-1 corpus (`scratch/hover_stage1/`, 8 seeds, 243 events, verified
2026-07-07). **Port source:** the IFBench batch-swap v2 harness
(`scripts/batch_swap_v2_run.py`, `scripts/batch_swap_v2_analysis.py`,
`analysis/ablation/batch_swap_v2/`).

## Why this experiment exists (context for a cold reader)

Batch-swap v2 on IFBench found batch identity causally inert (specificity +0.0054, CI
[-0.0116, +0.0242]; transfer -0.0011, CI [-0.0243, +0.0228]). Two external adjudicators signed
that scoped result but blocked the broad headline ("the reflection input channel is causally
inert") on the **generic-target confound**: IFBench's optimal prompt is plausibly batch-invariant
boilerplate, so a swap null is predicted there even if the proposer reads and uses its inputs
perfectly. HoVer is the discriminating test because its evolved prompts are visibly
example-derived (entity linking, birthdate comparisons, award-role structure — see any
`reflect_out_*.txt` in the Stage-1 corpus). If batch identity matters anywhere, it should show
here. If it nulls here too, the null is not an IFBench artifact.

This brief ports the v2 design to the Stage-1 HoVer corpus. **Reuse v2's estimand definitions
verbatim** — they were verified against harness code and adjudicated; do not re-derive them.
Adapt only what HoVer forces (pairing method, metric, event keying).

## The design

For each usable reflection event `e` in the Stage-1 corpus:

- **A_e** = the batch of 3 trainset examples the event actually reflected on (`subsample_ids`),
  with the parent's logged per-example scores.
- **Φ_e** = the parent program at that event (reconstructable from the trace + candidates).
- **B_e** = a matched batch of 3 *different* trainset examples (construction below).

Two arms, K=3 child draws each:
- **Arm SAME**: reflection input built from Φ_e's execution on A_e → 3 children.
- **Arm SWAP**: reflection input built from Φ_e's execution on B_e → 3 children.

Every child is evaluated on **both** A_e and B_e, per-example scores persisted per draw.

Estimands per v2, pooled with run-clustered inference over the 8 seeds:
- **Specificity**: own-batch improvement minus other-batch improvement (child−parent deltas).
- **Transfer**: improvement on the batch the child never saw.

## Matched-batch construction (the HoVer adaptation — "live failure-match")

IFBench v2 matched on constraint-type Jaccard; HoVer has no constraint types. Match on the
parent's failure profile instead, and note the matching evals are NOT overhead — the estimands
require parent scores and reflection inputs on B_e anyway:

1. For each event, sample **M=6** candidate examples from the 100-claim trainset, excluding A_e's
   examples (draw with a fixed per-event RNG seed, logged).
2. Run Φ_e on the 6 candidates **with full trace capture** (outputs + feedback, not just scores —
   the SWAP arm's reflection input must be the real (Inputs, Generated Outputs, Feedback) object
   built from actual execution, never a spliced or synthesized feedback string).
3. Select the 3 candidates whose parent score multiset best matches A_e's parent score multiset
   (exact multiset match preferred; minimum L1 distance as fallback; log which).
4. Those parent runs supply both the parent baseline on B_e and the SWAP arm's reflection input.

Report the achieved match quality (share of exact multiset matches) in the manifest.

## Fidelity requirements

- **Reflection input format**: byte-verify your constructed reflection inputs against the frozen
  `reflect_in_*.txt` format from the Stage-1 runs before any live call. Same builder, same
  sections, same ordering. If the harness builder can't be invoked standalone, stop and flag —
  do not hand-assemble an approximation.
- **Event keying (seeds 2 & 6)**: key on reflection events (`reflections.json` entries with
  children), never on `full_program_trace` indices. Seeds 2 and 6 contain child-less trace
  entries (seed 2: indices 5, 15; seed 6: index 27); any 1:1 event/trace assumption will
  mis-index. Assert per-seed event counts against the Stage-1 manifest (32/34/28/33/27/34/28/27)
  at load time.
- **Persistence (standing rule)**: per-draw, per-example score vectors on both batches, plus full
  child text, for every one of the 2 arms × 3 draws. This is what v2 failed to keep
  (capture_traces=False) and it permanently blocked a sibling analysis. No exceptions, including
  the smoke.
- **Frozen inputs**: `scratch/hover_stage1/` is now frozen — read-only. All Stage-2 writes go
  under `analysis/ablation/hover_swap/`. Never touch `necrosis/`, IFBench corpora, or v2 outputs.

## Ties and the coarse metric (pre-registered handling)

The title-recall metric lives on {0, 1/3, 2/3, 1}; the frozen run showed 76% of per-example
deltas exactly 0 and 39% of batch margins exactly 0. Primary estimands are continuous means, so
ties dilute power but don't bias. Report: the tie shares observed in this corpus, every pooled
estimate with run-clustered 95% CI, and the MDE next to each cell. No strict->0 accept logic
anywhere in the analysis path.

## Phases

### Phase 0 — census + pairing dry-run ($0)
- Census the Stage-1 corpus: usable events per seed (parent scores present + ≥1 child), total
  usable pairs, tie-share stats on logged parent minibatch scores.
- Build the full pairing plan (per-event candidate draws, RNG seeds) WITHOUT any API calls.
- Write `analysis/ablation/hover_swap/census.md` — raw facts only.

### Phase 1 — smoke (live, small): 5 pairs
- Run 5 pairs end-to-end (matching evals + 2 arms × 3 draws + dual-batch child evals),
  full persistence.
- Measure real per-pair cost and time from usage logs.
- Write `plan.md`: measured per-pair cost/time, projected cost/time for the full census count
  and for a 150-pair stratified subsample (stratified by seed, RNG-seeded, pre-registered as the
  fallback if full-corpus cost exceeds $60), tie shares from the smoke, and the line
  `STOP — awaiting APPROVED`.
- **Stop.** No further pairs. Only Neel creates APPROVED.

### Phase 2 — full run (only once APPROVED exists, at the pair count Neel wrote in it)
- Run all approved pairs. Spend cap $75 hard, tripwire at $60 (halt, preserve partials, flag).
- Write `hover_swap_manifest.md` — raw facts only (pairs completed, per-run counts, costs, file
  paths). No interpretation.

### Phase 3 — analysis ($0, separate step, after Neel confirms the manifest)
- Port `batch_swap_v2_analysis.py`; estimand definitions unchanged.
- `results.md`: numbers + CIs + MDEs only. **No interpretation, no verdict language** — Neel
  reads the numbers against the pre-registered map first.
- Second-path recompute of the two pooled estimands via an independent code path (different
  groupby/aggregation route), shown side by side.

## Pre-registered interpretation map (for Neel's read, not CC's)

- Specificity > 0, transfer ≈ 0 → proposer uses batch content; revisions overfit the minibatch;
  input channel NOT inert on HoVer; IFBench null is task-scoped (generic-target confound real).
- Specificity ≈ transfer > 0 → revisions generalize; batch content matters, example identity less.
- Both ≈ 0 → the selection null replicates on an example-derived benchmark; the broad headline
  unblocks (with scope guards: one-step, K=3, this metric).
- Every cell read against its MDE; no verdict if CI spans the map boundary.

## Explicit do-not list

- Do not modify anything under `scratch/hover_stage1/` or any frozen corpus.
- Do not synthesize or splice reflection inputs — real parent execution on B_e only.
- Do not key on trace indices.
- Do not skip the 5-pair smoke or fire past it without APPROVED.
- Do not create APPROVED yourself.
- Do not put interpretation in census, plan, manifest, or results files.
- Do not drop draw-level per-example persistence anywhere, including the smoke.
