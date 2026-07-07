# Feedback-ablation experiment — plan (Stage 0 complete, $0)

**Date:** 2026-07-02 · Question (adjudication Q5): does the reflection proposer USE the **Feedback**
section of the 3-section per-example object (Inputs + Generated Outputs + Feedback), or re-derive the
diagnosis from Inputs+Outputs alone? First causal (channel-manipulation) test; all prior results were
correlational. Frozen IFBench corpus read-only; all work under `analysis/ablation/`.

## Stage 0 results (all $0, read-only)

**0.1 Byte-fidelity gate → PASS.** The full proposer input reconstructed from frozen fields
(`reflective_dataset_built` 3 examples + parent instruction) via the exact template
(`gepa/src/gepa/strategies/instruction_proposal.py`; each field `.strip()`-ped, examples joined `\n\n`,
rendered `# Example N / ## Inputs / ## Generated Outputs / ## Feedback`) is **byte-identical to the logged
`proposal_end.prompts.system_prompt` on 8/8 baseline events** (≥5 required). Logged system_prompt == wire
bytes proven 3-way in `analysis/reflection_capture/equality.json` (4 calls, `three_way_equal: true`). ⇒ the
manipulation operates on a proven-faithful object.

**0.2 Template semantics.** The preamble says examples come "…along with the assistant's response for each
of them, **and some feedback on how the assistant's response could be better**"; the task says "**Read all
the assistant responses and the corresponding feedback.**" So **arm (ii)** (Feedback deleted) leaves the
template *referencing* feedback that is absent (a template-mismatch); **arm (iii)** (generic feedback
present) is the cleaner "constraint-specific content removed, structure intact" test. Read (iii) as primary
content test, (ii) as the stronger deletion.

**0.3 Config.** Proposer `openai/gpt-4.1`, task `openai/gpt-4.1-mini` (base names, **no snapshot**);
sampling unset → OpenAI defaults. **Caveat:** today's gpt-4.1 may differ from the logged-epoch model → arm
(i) is NOT expected to reproduce logged accept rates; cross-arm comparison stays internally valid (all arms
same model, same day). Gate re-evaluates BOTH parent and child today (drift-clean) rather than using logged
parent scores; logged parent scores reported as a secondary cross-check.

**0.4 Selection.** 150 of 382 b3 batches, stratified over 8 runs × iteration-terciles (seed **20260702**),
in `selected_batches.csv` (150 batches, terciles 54/48/48, all 8 runs); 50-batch same-stratification subset
flagged for the seed-repeat arm.

**0.5 Cost projection.** ~$8 upper bound (proposer gpt-4.1 500 calls ~$6.2; task gpt-4.1-mini ~1950 calls
~$2). Smoke measured **$0.024/batch** → full run projects **~$4–5**, far below the $60 STOP. Constraint
verification programmatic/free. In-script hard tripwire at $55.

**0.6 Power.** McNemar (paired, n=150, baseline accept ≈0.30): **MDE ≈ 10–12 percentage points** at 80%
power — a null (i)≈(ii)≈(iii) rules out only effects larger than that; never proof of zero.

## Stages 1–2 (executing)
- **Arms** (within batch, same parent/day/model, randomized order): (i) intact, (ii) feedback-deleted,
  (iii) generic (`"This example's output did not meet requirements."`), (i′) seed-repeat on the 50 subset.
- **Gate:** pointwise `StrictImprovementAcceptance` — child minibatch sum > parent minibatch sum (both
  re-evaled today via `DefaultAdapter` + programmatic `IFConstraintEvaluator`).
- **Analysis:** primary = accept rate (i)vs(iii) & (i)vs(ii), McNemar + sign-flip permutation ≥10k;
  secondary = gate margin; lottery share = (i)vs(i′); headline recomputed via an independent 2nd path.
- **Interpretation map** (→ results.md): (i)≈(ii)≈(iii) → Feedback channel causally inert on IFBench
  checklist SI (this regime only; does not generalize to rich-prose SI); (ii)/(iii) worse → content
  matters, selection direction reopens; a null bounded by the ~10–12pp MDE.

Runner: `scripts/run_ablation.py` (smoke-validated: arm(i) byte-identical to log). Outputs: `calls.csv`,
`results.md`. Actual spend reported vs projection.
