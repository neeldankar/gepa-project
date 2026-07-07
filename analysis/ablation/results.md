# Feedback-ablation experiment — results

**Date:** 2026-07-02 · **Actual spend $7.7399** (proposer gpt-4.1 $5.66 + task gpt-4.1-mini $2.08; vs
~$8 projection). Scripts: `scripts/run_ablation.py` (arms + gate), `scripts/run_ablation_analysis.py`.
Data: `calls.csv` (500 arm-calls), `selected_batches.csv`, `analysis_summary.csv`. Frozen corpus untouched.

## Provenance
Byte-fidelity gate PASSED (Stage 0): the manipulated proposer input reconstructs byte-identical to the
logged wire bytes (8/8; logged==wire proven 3-way in `reflection_capture/equality.json`). 150 b3 batches
stratified over 8 runs × iteration-terciles (seed 20260702); per batch, 3 arms (+ seed-repeat on 50)
called on the **same** parent/examples, same model, same day, randomized arm order. Gate = pointwise
`StrictImprovementAcceptance` (child minibatch sum > parent minibatch sum), both re-evaled **today** via
`DefaultAdapter` + programmatic `IFConstraintEvaluator`. Model-drift cross-check: mean parent sum today
**1.587** vs logged **1.617** (small; internal cross-arm validity holds regardless).

## Power (stated before the result)
McNemar, n=150 paired, baseline accept ≈0.30 → **MDE ≈ 10–12 percentage points** at 80% power. A null
rules out feedback effects **larger** than ~10–12pp; it is not proof of zero.

## Method
Arms: **(i) intact**, **(ii) Feedback deleted**, **(iii) generic** (`"This example's output did not meet
requirements."`), **(i′) seed-repeat**. Primary = accept rate (i)vs(iii) & (i)vs(ii), McNemar + sign-flip
permutation (20k). Secondary = gate margin (child−parent), paired permutation. Lottery = (i)vs(i′).
Accept table recomputed by an independent 2nd code path (matches exactly).

## Result — (i) ≈ (ii) ≈ (iii): the Feedback channel is causally INERT here

| arm | accept rate | mean gate margin |
|---|---|---|
| (i) intact | **0.340** (51/150) | +0.048 |
| (ii) Feedback deleted | **0.313** (47/150) | +0.065 |
| (iii) generic Feedback | **0.367** (55/150) | +0.061 |

| comparison | Δ accept | discordant b/c | McNemar p | perm p |
|---|---|---|---|---|
| (i) vs (iii) — primary content test | **−0.027** | 17/21 | 0.63 | 0.63 |
| (i) vs (ii) — deletion | **+0.027** | 24/20 | 0.65 | 0.65 |

Gate-margin deltas: Δ(i−ii)=−0.016 (p=0.64), Δ(i−iii)=−0.013 (p=0.71). **All arm differences ≤3pp /
≤0.02 margin and non-significant.** Point estimates, if anything, trend *opposite* to "content helps"
(deleting/genericizing Feedback slightly *raised* accepts/margins) — but within noise.

**Proposer lottery dominates.** Calling the **same** arm (i) twice (i vs i′, n=50) flips the accept
decision **32%** of the time; within-arm margin lottery variance (0.078) **dwarfs** the ~0.027 between-arm
accept effects. So the feedback-arm effects are not merely non-significant — they are **an order of
magnitude smaller than the proposer's own call-to-call stochasticity.**

## Interpretation map (verbatim)
- **(i)≈(ii)≈(iii): the Feedback channel is causally inert on IFBench checklist SI — Claim A confirmed IN
  THIS REGIME ONLY.** Mandatory scope caveat: **IFBench constraints are verifiable from Inputs+Outputs;
  nothing here generalizes to rich-prose SI, which is unmeasured.** The proposer re-derives the diagnosis
  from Inputs+Generated Outputs — which is exactly why the twenty scorers of the Feedback-derived object
  were poor proxies: they scored a channel that carries no causal weight in this verifiable-constraint regime.
- A null is bounded by the Stage-0 MDE (~10–12pp) — **not proof of zero.** We can rule out feedback effects
  larger than ~10–12pp on accept rate; a true effect below that (or on rich-prose SI, or on downstream U
  rather than the one-step gate) is unmeasured.

## Caveats
- Model drift: gpt-4.1/gpt-4.1-mini base (no snapshot); today's models may differ from the logged epoch —
  handled by re-evaling both arms today (internal validity); arm (i) not expected to reproduce logged rates.
- One-step gate only (child beats parent on its 3 minibatch examples) — not downstream valset U.
- Arm (ii) additionally introduces a template-mismatch (preamble references feedback that is absent); (iii)
  is the cleaner content-only test and agrees with (ii). n=150 (MDE ~10–12pp); the lottery result argues
  any real effect is small relative to proposer noise.

**Bottom line:** deleting or genericizing the per-example Feedback does **not** measurably change the
proposer's one-step success on IFBench — the diagnosis is re-derived from Inputs+Outputs. This is a causal
confirmation (this regime only) of the correlational scorer-nulls, and it identifies the proposer lottery
(32% same-arm flip) as the dominant source of outcome variance. It says nothing about rich-prose SI (HoVer),
which the whole scorer program could not measure and this experiment does not either.
