# GEPA side-information curriculum — findings summary

**Corpus:** IFBench reflective-optimization logs — 10 runs, 487 events, 382 b=3 minibatches over 54
constraint ids. All scoring was validated byte-level against the exact object the reflection LM receives —
the per-example `Inputs + Generated Outputs + Feedback` triple (219/219 sampled fields are verbatim
substrings of the byte-proven prompt; full-object vs feedback-only signal differ on 92.2% of units).
Results below are measured on that object, not a proxy.

## Headline
On the object the proposer actually reads, **per-example *selection* over reflection content is closed**:
no content scorer beats constraint-identity/difficulty, and the revision outcome has no stable per-example
target for such a scorer to predict. The remaining live lever is the **acceptance gate**, not which example
gets reflected on.

## Evidence — the closed selection direction
**Correct-object scorer screen.** Re-screening the reopened semantic scorers on the full triple (n=382
batches, 8 runs), **0 of 5 survive** residualization against constraint identity, and the Output channel's
marginal contribution (Δconstid) is **≤ 0 for every scorer** — audit-grade, on an independent byte-level
recompute matching to machine precision.

**Outcome ICC.** Attributing each batch's revision value ΔU to its three example slots (crossed random
effects, estimator validated on the real design), the per-example **ICC = 0.000, 95% CI [0, 0.243]**,
against a **+0.04 null-floor** — i.e. below the floor. The per-example ΔU target essentially does not
exist, which is what kills a learned per-example selector at the root. (A secondary per-example *acceptance*
component is weakly non-zero — ICC 0.111 after coarse difficulty controls, CI [0, 0.359], floor ~0.05 — but
it is unidentifiable from fine constraint-id composition and CI-wide.)

**Persistence.** Lag-1 autocorrelation of an example's outcome across appearances is **r = 0.011, p = 0.90**
(121 pairs, 3 runs) — no signal for a bandit/decay resampler to exploit (rules out only |r| ≳ 0.2).

**Causal ablation.** Deleting or genericizing the per-example Feedback channel does not move one-step accept:
**0.340 / 0.313 / 0.367** (intact / deleted / generic), all **p ≥ 0.63** (MDE 10–12pp, $7.74). The proposer
re-derives its diagnosis from Inputs+Outputs; the Feedback text carries no causal weight here.

**Lottery.** Calling the *same* input twice flips the accept decision **32%** of the time ⇒ ≈29% of accept
variance is batch-stable ⇒ any per-batch predictor is ceilinged at **r ≈ 0.54**. Proposer sampling noise,
not example choice, is the dominant source of one-step outcome variance.

**Off-policy sampler.** A tractability-weighted batch sampler evaluated by SNIPS (issue #34) gives at most a
**+12% relative one-step ΔU at β=0.5** (ESS 144) with a **CI overlapping uniform**; any stronger tilt (β≥1)
collapses ESS and is unevaluable — the logged data cannot show a real sampler win.

## Mechanism
IFBench side-information is a templated checklist — nearly a deterministic function of the failed-constraint-id
set. So any "content" scorer over the reflection text collapses onto difficulty / constraint-identity, and
the correct-object screen already shows that channel can't be beaten. That single fact explains every null
above at once.

## What's live
**The acceptance gate.** On logged rejects, **6.7% of 267 rejected children flip under ≥1 aggregate accept
rule** (weighted-coverage 6.0%), preferentially fixing *harder* constraints than they lose — enough to
justify a live paired-seed gate experiment, though **not** evidence the gate improves U (rejects were never
valset-scored; only an un-gated run shows that). A causal **2×2 batch-swap** (matched-example *specificity*
vs unseen-batch *transfer*, failure-matched pairs, run-clustered inference) is in flight to test whether
example identity matters at the one-step gate at all.

**HoVer (different regime).** Failures are ~97–100% retrieval-locus (byte-checked); the query-generating
module is inside the optimized surface, so the ceiling is empirical (n=1, thin), not structural; a
retrieval-fixability signature appears at 13% prevalence but is untested.

**Batch-swap v2 (verified).** The causal 2×2 above completed: pooled *specificity* **+0.0054**,
run-cluster 95% CI **[-0.0116, +0.0242]**, MDE **0.033**; pooled *transfer* **-0.0011**, CI
**[-0.0243, +0.0228]** — **382/382 pairs, 8 runs, dual-path verified**. Per-example selection is
causally inert at the one-step gate; only the acceptance gate remains live. (source:
`analysis/verification_postswap.md`)

**Lottery (corrected figure).** The citable same-input accept-disagreement is **0.415** (own-gate
batch-sum margin, strict > 0, n = **764** cells). The previously reported **0.382** is a mixed
estimand (`margin_on_B` applied to both arms, `scripts/batch_swap_v2_analysis.py:73-77`) and is
**deprecated** for external use. The prior **0.32** figure above is from a different corpus/rule and
is **not directly comparable**. (source: `analysis/verification_postswap.md`)

**Gate instability (batch size).** Shrinking the b=3 gate flips the accept decision: **P(flip vs
b=3) = 0.203** at b′=1, **0.104** at b′=2; within-b′ disagreement **0.372 / 0.309**. (source:
`analysis/verification_postswap.md` Task 4A)

## Scope limits
All of the above is the **verifiable instruction-following checklist regime only**; nothing transfers to
rich-prose side-information (unmeasured). Every null is bounded by its stated MDE/CI — evidence of a small-
or-absent effect, **not proof of zero** (8 runs leave wide upper CIs). And every result is the **one-step**
accept/ΔU gate, not the downstream valset U a deployed curriculum would ultimately move.

<!--
TRACEABILITY MAP (number → source doc · section)
- corpus 10 runs / 487 events / 382 b3 / 54 ids → adjudication_followup.md · addendum A1
- byte-verify 219/219 substrings; (a)≠(b) 92.2% → rescreen_wave1_audit.md · Deliverable 1
- screen 0/5 survive, n=382/8 runs, Δconstid ≤ 0 → rescreen_wave1.md · survival table; audit Deliverable 3
- outcome ICC ΔU 0.000, CI [0,0.243], floor +0.04 → adjudication_followup.md · Task 1 (corrob. closeout Step 2)
- accept-ICC 0.111, CI [0,0.359], floor ~0.05, unident. from constraint-id → adjudication_followup.md · addendum A2
- lag-1 r=0.011, p=0.90, 121 pairs/3 runs, rules out |r|≳0.2 → adjudication_followup.md · Task 2
- ablation 0.340/0.313/0.367, p≥0.63, MDE 10–12pp, $7.74 → ablation/results.md · result table
- lottery 32% flip; 29% batch-stable / r≈0.54 ceiling → 32% ablation/results.md · lottery; 29%+r≈0.54 DERIVED from 32%
- SNIPS β=0.5 +12% rel, ESS 144, CI overlaps uniform; β≥1 ESS collapse → adjudication_followup.md · Task 3
- gate flip 6.7% of 267, R3 6.0%, fixes harder than losses → gate_fliprate_probe.md · flip-rate table
- HoVer ~97–100% retrieval-locus; gen_query in Φ (empirical, n=1); 13% retrieval-fixability → closeout_verification.md · Steps 1/3/4
- batch-swap v2 specificity +0.0054 CI [-0.0116,+0.0242] MDE 0.033; transfer -0.0011 CI [-0.0243,+0.0228]; 382/382 pairs, 8 runs, dual-path → verification_postswap.md · Tasks 1-3
- lottery corrected 0.415 (>0, n=764); 0.382 mixed estimand DEPRECATED (batch_swap_v2_analysis.py:73-77); 0.32 diff corpus/rule not comparable → verification_postswap.md · Task 2
- gate flip P=0.203 (b′=1) / 0.104 (b′=2); within-b′ disagree 0.372/0.309 → verification_postswap.md · Task 4A
-->
