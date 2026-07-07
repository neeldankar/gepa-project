# Wave 1 re-screen — reopened scorers on the CORRECT reflection object

**Date:** 2026-06-30 · **Cost:** $0 (pure offline; frozen corpus untouched, no LM/network) ·
**Scope:** WAVE 1 only — establish controls reproduce + triage the reopened semantic scorers at
**screening level** (LORO + residualization). **No permutation-MAX / M-variant hardening** (that
is Wave 2, gated on a survivor). Code: `gepa_si/screen/{triples_io,scorers_semantic}.py`,
`scripts/run_rescreen_wave1.py`. Artifact: `analysis/rescreen_wave1.parquet`.

## What changed vs every prior screen
Prior scorers read only the per-example **Feedback string** (id-determined → the prior collapse).
The proposer actually reads the full **triple** `Inputs + Generated Outputs + Feedback`; the
Generated Outputs are **not** id-determined, so the collapse argument does not transfer. We
re-screen on that object.

## STOP-gate 1 — object assembly (PASS)
`extract_reflection_triples` pulls `{Inputs, Generated Outputs, Feedback}` per
(run, iteration, example_pos) from `reflective_dataset_built`. **All 1251/1251 per-example
fields are verbatim substrings of their own event's `proposal_end.prompts.system_prompt`** (the
object proven 3-way byte-identical to the reflection LM input). The only delta is a trailing
space the prompt template trims (≤1 ws char; content byte-identical). Structure matches
`reflect_1.txt` (`## Inputs / ## Generated Outputs / ## Feedback`, b=3).

## STOP-gate 2 — controls reproduce bit-identically (PASS)
Re-ran `run_scorers_wave{1,2,3}.py` and compared to the pre-run snapshot. Every `[score-control]`
and `[crude-proxy-control]` reproduces **to float64 ULP** (max abs Δ on any per-event value =
3.55e-15, relative 2e-16 — non-associative summation reordering). The lone 4th-decimal display
shift (`parent_near_frontier` partial_loo −0.0143 vs −0.0144) is a rounding-boundary artifact of
that 3.6e-15 noise, **not** a harness change. Receipt confirmed: the harness did not silently change.

| control scorer | tag | partial_loo (prior == new) | bit-identical |
|---|---|---|---|
| constraint_tractability | score-control (prior survivor) | **+0.1717** | ✓ ULP |
| valset_prevalence | score-control | +0.0486 | ✓ ULP |
| prevalence_x_headroom | score-control | −0.0325 | ✓ ULP |
| parent_near_frontier | score-control | −0.0143* | ✓ ULP* |
| pool_disagreement_voi | score-control | +0.0246 | ✓ ULP |
| coverage_gap | score-control | +0.0512 | ✓ ULP |
| coverage_gap_x_prevalence | score-control | +0.0169 | ✓ ULP |
| seed_to_parent_regression | score-control (sparse: nonzero only ~11/382 b3 batches; not screened for survival) | +0.1150 | ✓ ULP |
| output_n_words | crude-proxy-control | +0.0609 | ✓ ULP |
| input_typicality | crude-proxy-control | +0.0089 | ✓ ULP |
| typicality_x_headroom | crude-proxy-control | −0.0599 | ✓ ULP |
| output_repairability | crude-proxy-control | +0.0347 | ✓ ULP |

\* per-event scorer values bit-identical to 15 sig figs; only the rounded summary partial_loo sits on a 4th-decimal boundary.

## The real work — reopened semantic scorers (three-way), vs batch LOO contribution
Headline target = batch-level LOO unique frontier contribution (`fungibility`). Screened on the 8
b3 runs (382 batches). **constid** = residualized on the 4 difficulty controls **+
constraint_tractability + 15 failed-type-composition columns** (the constraint-identity span).

| scorer | tag | (a) feedback partial_loo | (b) full-object raw_loo | (b) full-object partial_loo | (b) **constid_loo** | LORO constid mean±sd | survives? |
|---|---|---|---|---|---|---|---|
| knn_novelty | text-reopen | **+0.171** | +0.125 | +0.124 | +0.079 | +0.101 ± 0.130 | **no** |
| ncd_novelty | text-reopen | −0.038 | +0.006 | −0.010 | −0.042 | +0.043 ± 0.135 | no |
| actionability | text-reopen | −0.055 | +0.014 | −0.005 | −0.048 | −0.068 ± 0.131 | no |
| nov_x_act | text-reopen | +0.175 | +0.087 | +0.072 | +0.006 | +0.000 ± 0.167 | no |
| failure_mode (output-derived) | **new** | — | +0.004 | −0.054 | −0.098 | −0.082 ± 0.116 | no |
| failure-signature (id-keyed) | stays-dead-confirm | — | — | — | — | — | **dead** (335/351 singletons, 87.7%) |

### (a)/(b)/(c) three-way — does the signal come from the Output?
`(c) = Δ(b−a)` on each screen axis is the signal the Output/Input added:

| scorer | Δraw | Δpartial | **Δconstid** |
|---|---|---|---|
| knn_novelty | −0.041 | −0.047 | **−0.017** |
| ncd_novelty | +0.041 | +0.028 | +0.028 |
| actionability | +0.052 | +0.050 | −0.009 |
| nov_x_act | −0.082 | −0.103 | −0.099 |

The only scorer that clears the constraint-identity bar (knn_novelty, constid +0.079) is the one
whose **delta is negative** — its signal lives in variant (a), the **feedback string**, and the
Output *dilutes* it. The scorers whose delta is positive (ncd_novelty, actionability) start from
and stay **below zero** under constid. So no scorer has *both* a positive constid level *and*
output-origin.

### Survival rule (encoded in the runner)
A reopened scorer survives Wave-1 triage only if, on the full object (b): (1) constid_loo > 0.05
(beyond constraint id), (2) constid_loo(b) − constid_loo(a) > 0 (output-origin — the whole point
of the correction), and (3) LORO mean − sd > 0 (stable). Results:

| scorer | beyond-id | output-origin | stable | verdict |
|---|---|---|---|---|
| knn_novelty | ✓ (0.079) | ✗ (−0.017) | ✗ (0.101−0.130<0) | dead |
| ncd_novelty | ✗ | ✓ | ✗ | dead |
| actionability | ✗ | ✗ | ✗ | dead |
| nov_x_act | ✗ | ✗ | ✗ | dead |
| failure_mode | ✗ | ✗ | ✗ | dead |

**SURVIVORS: NONE.**

## Verdict — the null holds on the RIGHT object (a stronger claim than before)
1. **No semantic scorer adds output-origin signal beyond constraint identity.** The reopening
   premise ("the Output is not id-determined, so it may carry novel signal") is **not** borne out:
   for the novelty scorers the Output channel (Δconstid) is ≤ 0, and the new output-derived
   failure-MODE signature is outright negative under controls (−0.098).
2. **The one scorer that looks alive is constraint-identity in disguise — on the feedback string.**
   kNN novelty on the Feedback string recovers ~the tractability-level correlation (partial_loo
   0.171 ≈ the 0.172 bar) because *novel feedback = rare constraint composition*. constid
   residualization roughly halves it (0.171 → 0.097 on (a); 0.079 on (b)), and the residual is the
   rare-exact-combination channel — i.e. the **dead, singleton-ceilinged failure-signature**
   (335/351 unique) in continuous form, with LORO 0.10 ± 0.13 straddling zero. Not generalizable,
   not output-derived.
3. **failure-signature stays dead, identically** (335/351 singletons reproduced bit-for-bit).

This is strictly stronger than the prior feedback-string null: even after handing every semantic
scorer the full Output the proposer sees, and isolating the Output's marginal contribution, the
null holds — and the Output channel specifically is empty. **constraint_tractability (0.172)
remains the sole Phase-2 candidate. No survivor → no Wave 2 needed for these scorers.**

## Caveats (honest)
- `[score-control]` bit-identity is to float64 ULP, not literal bytes (numpy reduction-order
  nondeterminism); a real harness change would move values by ≫1e-15, so the receipt holds.
- "Embedding"-kNN novelty uses the repo's local **TF-IDF (lexical)**, the $0 model-free stand-in;
  true sentence embeddings (paid) were not run and would be a Wave-2 robustness variant — but
  since the *output channel itself* is empty here (Δconstid ≤ 0), a richer embedding of the same
  channel is unlikely to reverse the verdict.
- Screening-level only: no permutation-MAX null was run (Wave 2). With zero survivors the harder
  significance bar is moot for these scorers.
- LORO with the 21-column constraint-id control on ~48 batches/fold is high-variance; the pooled
  n=382 constid number is the more reliable read (LORO reported for stability only).
