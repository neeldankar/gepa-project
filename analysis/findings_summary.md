# GEPA side-information curriculum — findings summary

**Corpus:** IFBench reflective-optimization logs — 10 runs, 487 events, 382 b=3 minibatches over 54
constraint ids. All scoring was validated byte-level against the exact object the reflection LM receives —
the per-example `Inputs + Generated Outputs + Feedback` triple (219/219 sampled fields are verbatim
substrings of the byte-proven prompt; full-object vs feedback-only signal differ on 92.2% of units).
Results below are measured on that object, not a proxy.

## Headline
Two things are established, and they point the same way.

**Per-example selection over reflection content is closed on IFBench**, on the byte-verified object
the proposer actually reads: no content scorer beats constraint-identity/difficulty, and the revision
outcome has no stable per-example target for such a scorer to predict. Mechanism is id-determinism —
IFBench SI is nearly a deterministic function of the failed-constraint-id set.

**On HoVer the channel is causally live at one step but does not reach the endpoint.** The batch-swap
shows reflection-input identity matters (specificity +0.0274, CI [+0.0149, +0.0415], 243 events,
8 seeds), so the IFBench null was task-scoped rather than GEPA-general. But the deployable form of the
one surviving signal pros no detectable trajectory-level gain at equal budget: three arms x 8 paired
seeds, T-C -0.0011 and T-B -0.0128, both underpowered nulls, on a non-degenerate selection contrast.

**The boundary, not the absence, is the finding.** A real one-step effect failing to convert to
trajectory outcomes has now been measured two independent ways on the same benchmark. One-step is not
trajectory — that scope guard is a measured result here, not a hedge.

**The live lever remains the acceptance gate** (#132), which is where the pre-registered (null, null)
branch routes and where the noise measurements already sit: same-input accept disagreement 0.415,
decision-flip 0.203 at b'=1 and 0.104 at b'=2.

Every null below is bounded by its stated MDE/CI — evidence of a small-or-absent effect, never proof
of zero.

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

---

## (a) HoVer batch-swap — factual layer complete, verdict recorded

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

**Verdict:** cell 1. Specificity is positive: point +0.0274, 95% CI [+0.0149, +0.0415], excludes zero. The lower bound sits just under the MDE (0.0191), which caps how large I claim the effect is but does not change the sign; the map's decision boundary is zero and the CI clears it. Transfer is unresolved: CI [-0.0040, +0.0367] spans zero, no positive verdict, point estimate below its MDE. Reading: the reflection input channel is causally active on HoVer; the IFBench null was task-scoped, not GEPA-general; the generic-target confound was real. Overfit vs generalize is not yet distinguished; the spec-transfer difference is the next read. Scope: one-step, K=3, own-batch specificity, 8-cluster bootstrap anti-conservative.

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

---

## (d) State-dependent novelty selection — three-arm live experiment, (null, null)

**Design.** Three arms x 8 paired seeds on HoVer, equal budget (max_metric_calls 300).
B = baseline GEPA (b=3, uniform). C = cost-matched control (draw 6, pick 3 at random).
T = treatment (draw 6, pick the 3 minimizing knn_emb_fb_min). Endpoint = §8b selection-split
argmax evaluated on the frozen 150-claim test split. gepa 0.0.27, dspy 3.2.1, gpt-4.1-mini
temp 0, cache off. Design state-dependent-design-v2.1.1-frozen.

**Pre-registration.** Framing label CONFIRMATORY, MDE 0.06332 endpoint points, both written
into plan.md §2 on 2026-08-12 BEFORE results.md was read. D = 1.4432 (235 events).
Gate trigger 3 x (D x beta/2) = 0.08213; MDE < trigger, so GATE BITES = False.

**Results.** Paired by seed, exact two-sided sign-flip over all 2^8 patterns, 10,000-resample
paired bootstrap, seed 20260709.

| contrast | paired mean | percentile 95% CI | BCa 95% CI | p | §9 labe---|---|---|---|---|---|
| T - C (H1, confirmatory) | -0.001111 | [-0.025833, +0.031667] | [-0.022500, +0.039722] | 0.9688 | underpowered null |
| T - B (H2, secondary) | -0.012778 | [-0.039444, +0.021118] | [-0.035556, +0.029444] | 0.4844 | underpowered null |
| C - B (H3, anomaly overlay) | -0.011667 | [-0.023611, +0.001667] | [-0.022500, +0.003056] | 0.1328 | null, no label required |

Per-arm endpoint mean (SD, ddof=1), n=8 each: B 0.599167 (0.029118), C 0.587500 (0.023576),
T 0.586389 (0.031144).

**§9 labels — how they were assigned.** Deflated planning effect = D x beta/2 = 0.0273768.
A null is labeled underpowered when its CI cannot exclude that value. T-C fails to exclude on
both intervals. T-B DISAGREES: BCa upper (+0.029444) fails to exclude, percentile upper
(+0.021118) excludes. §9 does not specify which interval decides and §10 requires both be
reported, so the design is silent here. The conservative bound was taken and T-B is labeled an
underpowered null. This was a judgment call, not a egistered rule; the counterargument is
M2's own stated reason for requiring both intervals, that BCa's acceleration constant is
unstable at n=8. Recorded so the choice is visible rather than absorbed into a clean number.

**Anomaly overlay did not fire.** §9 triggers it only on positive C-B by the sign criterion.
C-B = -0.011667, p = 0.133 — null and negative, consistent with H3's pre-registered
expectation of <= 0. No grid cell blocked.

**§15-12 selection-pressure degeneracy — checked, NOT degenerate.** §9 requires this before any
"signal does not transfer" reading. Across 235 events the within-event novelty spread is
substantial: top3 - bottom3 mean gap median 2.28 within-run SD (mean 2.36, min 0.533, max 5.65);
range/within-run-SD median 4.03. Zero events have exact-zero range or exact-zero top3-bottom3 gap.
§15-12 states no numeric threshold ("near-constant" only), so this is a distributional read, not a
criterion that fired. The knob was turned; T and C were selecting different batches.
(analye_dep/degeneracy_descriptive.md)

**§15-4 monitored descriptives — NO TESTS RUN, exploratory only.** Pre-registered as monitoring,
not as a contrast. Per-arm means over 8 seeds:

| arm | accept rate | reflection events | candidates (incl. seed) |
|---|---|---|---|
| B | 0.3456 | 31.25 | 11.50 |
| C | 0.2558 | 26.00 | 7.50 |
| T | 0.3838 | 23.38 | 9.88 |

T's accept rate exceeds C's on 6 of 8 seeds, ties on 1, is lower on 1. T produced more candidates
than C (9.88 vs 7.50) on ~10% fewer reflection events. **No test was run and none is licensed:**
H1 is pre-registered as a policy contrast, not a mechanism contrast (R9). Two live confounds:
accept is measured on the same minibatch the treatment manipulates (the collider, proposition §6),
and high-novelty-feedback examples may be ones the parent scores poorly on, leaving more headroom
to beat — a mechanical route to a higher accept rate with no bearing on revision quality. Any
mechanism claim from these numbers requires a separate designed test.

**Fragil T_seed4 (0.657778) is the largest endpoint in the table and carries +0.100 of the
T-C paired difference. Excluding it moves the T-C mean to about -0.016. Sign pattern on T-C is
3 positive, 5 negative. The flat mean rests on one seed. Stated as characterization; the seed is
NOT excluded from any reported number.

**Scope guards.** 8 paired seeds; max_metric_calls 300; HoVer 3-hop only; gpt-4.1-mini; local BM25;
one benchmark. CONFIRMATORY is not well-powered — the MDE (0.06332) is 2.3x the implied one-step
effect (0.02738), so an effect the size the screen predicts would not be reliably detected at n=8.
The MDE assumes rho = 0 on paired seeds (§11-3 B-arm SD caveat), so it is an upper bound. Exactness
of the sign-flip test covers T-C under the sharp null; for T-B the arms differ mechanically and
exchangeability is an approximation (R14) — this is why H2 is secondary. The 8-cluster
anti-conservative bootstrap caveat travels with every CI above. The endpoint estimator changed
between Stage-1 and v2.1 (DENS.md 2026-07-22): do NOT table these endpoints alongside the
HoVer swap specificity number without that guard.

**Spend.** ~$189 program total across all gates, excluding an unrecorded dose-control pass.
Artifact-recorded figures undercount because per-process spend meters do not span restarts.

**Reading.** The selection channel is causally active on HoVer at one step (swap specificity
+0.0274, CI [+0.0149, +0.0415]) and does not produce a detectable trajectory-level endpoint gain
at this budget. Both T-C and T-B are underpowered nulls, never evidence of absence. The
constructive lane is the acceptance gate (#132), per the pre-registered map's (null, null) branch.

(source: `analysis/state_dep/results.md`, `analysis/state_dep/degeneracy_descriptive.md`,
`analysis/state_dep/plan.md` §2)
