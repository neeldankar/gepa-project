# Review packet: side-information selection in GEPA reflective optimization

Assembled 2026-08-26. **Self-contained.** Everything needed to check a claim is in this file.
The other 17 files in this folder are the audit trail behind it: raw artifacts, the frozen
design, and the scripts that emitted the results. `MANIFEST.md` lists them with hashes,
`TRACEABILITY.md` maps every number here to a file and line in one of them.

Every number carries an interval or a minimum detectable effect. Nulls are reported as bounded
at their MDE, never as demonstrations of zero.

---

## 1. The question

GEPA is a prompt optimizer that improves a program by reflecting on its own failures. Each
optimization step takes a minibatch of training examples, runs the current program on them,
collects per-example side information (the inputs, the generated outputs, and a textual feedback
string), and hands that bundle to a reflection LM which proposes a new instruction. A gate then
accepts or rejects the child.

The minibatch is sampled uniformly at random. This program asked whether that is leaving value
on the table:

> Does it matter **which** examples get reflected on, and if so, can a cheap scorer over the
> side information pick better ones than random?

The question splits into two regimes that are kept separate throughout this document, because
they got different answers:

- **Static selection (IFBench).** Score candidate examples on their side information and pick a
  better minibatch. Studied offline against logged runs.
- **State-dependent selection (HoVer).** Score against the run's own evolving history, so the
  same example scores differently at different points in the run. Tested live.

---

## 2. What was built

**Instrumentation.** GEPA was run with per-event logging that persists the exact object the
reflection LM receives. This matters more than it sounds. An early version of this work scored a
proxy (the feedback text alone) rather than the real object (the full inputs-plus-outputs-plus-
feedback triple). The two disagree on 92.2% of units, so that result was discarded and rerun.
Everything below is measured on the byte-verified real object, with 219 of 219 sampled fields
confirmed as verbatim substrings of the byte-proven prompt.

**Three instruments.**

1. **Offline scorer screens.** Score candidate examples from logged runs, residualize against a
   difficulty baseline, and ask whether any scorer adds signal over that baseline.
2. **The batch swap**, a causal 2x2. For each reflection event, build a failure-matched partner
   batch, then give the reflection LM either the event's own batch or the partner's, and measure
   the resulting child two ways. **Specificity** is the gain on the batch the reflection input
   came from. **Transfer** is the gain on a batch the reflection input never saw. Both are
   measured on the 3-example minibatches themselves, never on a validation set and never on a
   held-out slice.
3. **A live three-arm paired-seed experiment**, pre-registered, described in section 5.

**Two benchmarks.** IFBench is verifiable instruction following, where side information is a
templated checklist. HoVer is 3-hop claim verification over a local BM25 index, where the program
must generate retrieval queries and the feedback names retrieved and missed gold titles.

---

## 3. Result block A: static selection on IFBench looks closed

Corpus: 10 runs, 487 reflection events, 382 three-example minibatches, 54 constraint ids.

Five independent lines of evidence point the same way.

**Scorer screen.** Re-screening the reopened semantic scorers on the full triple (n = 382
minibatches, 8 runs), **0 of 5 survive** residualization against constraint identity, and the
output channel's marginal contribution over constraint identity is **at or below zero for every
scorer**, on an independent byte-level recompute matching to machine precision.

**Outcome ICC.** Attributing each minibatch's revision value to its three example slots via
crossed random effects, the per-example intraclass correlation is **0.000, 95% CI [0, 0.243]**,
against a null floor of **+0.04**, so below the floor. A secondary per-example acceptance
component is weakly non-zero at **ICC 0.111, 95% CI [0, 0.359]** against a floor of about 0.05,
but it is not identifiable from fine constraint-id composition and its interval is wide. The
per-example target a learned selector would need to predict is very small or absent at this
resolution.

**Persistence.** Lag-1 autocorrelation of an example's outcome across appearances is **r = 0.011,
p = 0.90** (121 pairs, 3 runs). This rules out only **|r| of about 0.2 or larger**, so it is a
bounded null, not a demonstration of independence.

**Causal ablation.** Deleting or genericizing the per-example feedback channel does not move the
one-step accept rate: **0.340 intact, 0.313 deleted, 0.367 generic, all p at or above 0.63, MDE
10 to 12 percentage points**, at a cost of $7.74. The proposer appears to re-derive its diagnosis
from inputs and outputs.

**Causal 2x2 batch swap on IFBench.** Pooled specificity **+0.0054, run-cluster 95% CI
[-0.0116, +0.0242], MDE 0.033**. Pooled transfer **-0.0011, 95% CI [-0.0243, +0.0228]**. 382 of
382 pairs across 8 runs, dual-path verified. No detectable effect of example identity at the
one-step gate on this benchmark at this budget.

**Why these agree.** IFBench side information is a templated checklist, close to a deterministic
function of the failed-constraint-id set. Any content scorer over that text collapses onto
difficulty and constraint identity, and the screen already shows that channel is not beaten. One
mechanism explains all five nulls at once.

**Status.** Treated as **closed**, meaning the program stopped investing here. That is a decision
about where to spend effort, not a proof of zero. Each null is bounded by its stated interval or
MDE, and 8 to 10 runs leave wide upper bounds.

**What stayed live on IFBench: the acceptance gate, not example choice.** On logged rejects,
**6.7% of 267 rejected children flip under at least one aggregate accept rule** (weighted-coverage
variant 6.0%), preferentially fixing harder constraints than they lose. That is not evidence the
gate improves final utility, because rejected children were never validation-scored. Separately,
the gate is measurably unstable: the same input evaluated twice disagrees on the accept decision
at a rate of **0.415** (own-gate batch-sum margin, strict greater-than, n = 764 cells), and
shrinking the minibatch flips the decision relative to b = 3 with probability **0.203 at b' = 1**
and **0.104 at b' = 2**, with within-b' disagreement 0.372 and 0.309. An earlier same-input
disagreement figure that circulated internally was computed under a mixed estimand and is
deprecated for external use; the citable figure is 0.415.

---

## 4. Result block B: on HoVer the reflection input is causally active at one step

Corpus: 8 seeds, 243 reflection events, 100-claim trainset, Pareto set size 10,
max_metric_calls 300, gpt-4.1-mini, local BM25 retrieval, deterministic metric. Stage-2 spend
$74.09. Corpus frozen at tag `stage2-pre-analysis`.

The same 2x2 swap on HoVer gives a different answer than IFBench.

| quantity | estimate | 95% CI (run-cluster) | MDE | p |
|---|---|---|---|---|
| pooled specificity | +0.0274 | [+0.0149, +0.0415] | 0.0191 | 0.0177 |
| pooled transfer | +0.0169 | [-0.0040, +0.0367] | 0.0293 | not resolved |

**Specificity is positive and its interval excludes zero.** Transfer is unresolved: its interval
spans zero and its point estimate sits below its own MDE. Both point estimates were independently
recomputed from the raw per-pair draw records and reproduce the committed values to 9 decimal
places, with a second implementation agreeing exactly.

**What this licenses.** The reflection input channel is causally active on HoVer, so the IFBench
null in block A is **task-scoped, not GEPA-general**. The natural explanation is that HoVer's
optimal prompt must be example-derived (the program has to learn what a good retrieval query
looks like), whereas IFBench's is largely recoverable from the constraint id alone.

**What this does not license.** These are one-step minibatch margins, K = 3 draws, this metric,
this benchmark. Nothing here speaks to downstream utility. Specificity's lower bound (+0.0149)
sits below its MDE (0.0191), which caps how large the effect can be claimed to be without
changing its sign. The 8-cluster bootstrap is anti-conservative, and that caveat travels with
every interval in this block.

**Heterogeneity: one surviving observable.** Of 108 pre-registered race cells, exactly one
survives every criterion, a scorer called `knn_emb_fb_min`:

| read | beta (per within-run SD) | 95% BCa CI | permutation p | leave-one-run-out |
|---|---|---|---|---|
| marginal | +0.03794 | [+0.01045, +0.07031] | 0.0013 | 8 of 8 |
| orthogonal to difficulty | +0.03877 | [+0.01068, +0.07011] | 0.0013 | 8 of 8 |
| tie-robust sign | +0.19560 | [+0.09344, +0.29185] | 0.0009 | 8 of 8 |

Against its own **MDE 0.0429**, n = 235 events. A pure-noise scorer through the identical
pipeline does not survive (beta +0.00122, interval spans zero, p 0.9126, leave-one-run-out 3 of
8). The second analysis path agrees with the first to 3.5e-17.

Five caveats travel with that scorer and are load-bearing:

1. **It measures failure-composition novelty, not prose-content novelty.** HoVer feedback is a
   rigid 118 to 198 byte template over retrieved and missed gold titles. Describing any result
   from it as prose novelty would misstate the mechanism.
2. **It is not deployable as a pre-spend sampler.** It needs the realized feedback, which only
   exists after running the program on the example. The pre-spend candidate list is empty, so the
   screen's own live-confirm clause never fired.
3. The point estimate (0.03794) sits below its own MDE (0.0429), so conditional on detection the
   magnitude is likely inflated by the winner's curse. The design plans against roughly half.
4. The rank-based channel confirms nothing at the 0.05 level: the same scorer tops that table at
   +0.1247 but with p 0.0709. The evidence rests on the regression and bootstrap read.
5. The signal is embedding-geometry-specific. Every lexical (TF-IDF) version of the same scorers
   is null.

Closest near-miss on the deployable list: a claim-representativeness scorer whose interval
excludes zero with leave-one-run-out 8 of 8, but permutation p 0.0994.

---

## 5. Result block C: state-dependent selection shows no detectable endpoint effect

This is the experiment the previous two blocks set up. It is reported separately from block B on
purpose; see the estimator warning at the end of this section.

### 5.1 Design

Three arms, 8 paired seeds, HoVer, equal total budget.

- **B**, baseline GEPA: sample 3 examples uniformly.
- **C**, cost-matched control: draw 6 candidates, pick 3 at random.
- **T**, treatment: draw 6 candidates, pick the **3 highest-novelty** of the 6 by
  `knn_emb_fb_min` from block B. The selection **maximizes** novelty. It is implemented as a
  descending sort with a seeded tie-break, which is provably identical to maximizing the
  batch-minimum novelty over all 20 three-subsets, because the score is a fixed per-item
  quantity with no within-batch term. The `_min` in the scorer's name denotes aggregation
  over batch members, not a direction.

C exists so that T is compared against something paying the same observation cost. The primary
contrast is therefore **T minus C**, which holds the draw-6 mechanics fixed and varies only the
selection rule. **T minus B** is the deployment contrast, secondary. **C minus B** isolates the
overhead of the draw-6 mechanics and is monitored, not tested.

**Endpoint.** Each run produces a pool of accepted candidate programs. The endpoint is the pool
member scoring best on a frozen 50-claim selection split, then evaluated on a frozen 150-claim
test split. Both splits are hash-pinned and identical across all 24 runs.

### 5.2 Pre-registration record

Written to disk 2026-08-12 **before the results file was read**, together with the simulator's
hash. This is the most checkable claim in this packet.

| item | value |
|---|---|
| framing label | **CONFIRMATORY** |
| MDE | **0.06332** endpoint points (1.615 times the endpoint SD) |
| measured dose D | 1.4431827353722393 over 235 events |
| gate trigger, 3 x (D x beta/2) | 0.08213 |
| gate outcome | MDE 0.06332 is below trigger 0.08213, so the label did not flip |
| deflated planning effect, D x beta/2 | 0.0273768 |
| simulator | `mde_sim.py` sha256 `6d11de278014b7e7de41cf55cb56cad4f92680f5b5f6159e7c6583bf84bce5cc` |

The gate would have downgraded the framing to estimation-only had the MDE exceeded three times
the deflated planning effect. It did not, so the confirmatory label stands. Note what that does
and does not mean: it is a heuristic screen the design itself twice declines to call a power
calculation, and it juxtaposes endpoint units against one-step specificity units.

### 5.3 The interpretation map, as frozen

Quoted from the frozen design, since the labels below turn on its exact wording:

> Sign determination (all contrasts): 'positive' iff two-sided exact sign-flip p<0.05 with mean>0
> on paired differences; 'negative' iff p<0.05 with mean<0; otherwise 'null'. H1 machinery for
> ΔTC (confirmatory); identical machinery for ΔTB and C−B (secondary, labeled). CIs carry
> magnitude and the underpowered-null label only: any null whose CI cannot exclude the deflated
> planning effect is labeled 'underpowered null', never evidence of absence.

An anomaly protocol is evaluated **first** and fires only if C minus B is *positive* by that
criterion, which would mean the draw-6 mechanics were themselves doing work. The relevant grid
cell, for two nulls, reads:

> **(null,null)** No detection. Bounded null at measured MDE. Consult the degeneracy descriptive
> (§15-12) before any 'signal does not transfer' reading. Selection lane closes at trajectory
> level at this budget/power; gate lane becomes the constructive center.

### 5.4 Results

Paired by seed. Exact two-sided sign-flip test over all 2^8 = 256 sign patterns.
10,000-resample paired bootstrap at seed 20260709, both interval families over the same
resample indices.

| contrast | paired mean | 95% CI percentile | 95% CI BCa | p |
|---|---|---|---|---|
| T minus C (primary) | -0.001111 | [-0.025833, +0.031667] | [-0.022500, +0.039722] | 0.9688 |
| T minus B (secondary) | -0.012778 | [-0.039444, +0.021118] | [-0.035556, +0.029444] | 0.4844 |
| C minus B (monitored) | -0.011667 | [-0.023611, +0.001667] | [-0.022500, +0.003056] | 0.1328 |

Per-arm endpoint mean with standard deviation (n = 8 each): **B 0.599167 (0.029118), C 0.587500
(0.023576), T 0.586389 (0.031144)**.

All 24 endpoints, so the paired differences can be recomputed by hand:

| seed | B | C | T | T minus C | T minus B | C minus B |
|---|---|---|---|---|---|---|
| 0 | 0.633333 | 0.628889 | 0.571111 | -0.057778 | -0.062222 | -0.004444 |
| 1 | 0.617778 | 0.593333 | 0.568889 | -0.024444 | -0.048889 | -0.024444 |
| 2 | 0.564444 | 0.591111 | 0.575556 | -0.015556 | +0.011111 | +0.026667 |
| 3 | 0.602222 | 0.566667 | 0.568889 | +0.002222 | -0.033333 | -0.035556 |
| 4 | 0.568889 | 0.557778 | 0.657778 | +0.100000 | +0.088889 | -0.011111 |
| 5 | 0.591111 | 0.584444 | 0.573333 | -0.011111 | -0.017778 | -0.006667 |
| 6 | 0.640000 | 0.608889 | 0.604444 | -0.004444 | -0.035556 | -0.031111 |
| 7 | 0.575556 | 0.568889 | 0.571111 | +0.002222 | -0.004444 | -0.006667 |

### 5.5 Labels, and one judgment call

Both primary and secondary contrasts are 'null' under the sign rule (all p at or above 0.05), so
the (null,null) cell applies. The underpowered-null test is whether each interval can exclude
the deflated planning effect, 0.0273768. All lower bounds sit below that value, so only the
upper bound can decide.

| contrast | percentile upper | excludes 0.0273768 | BCa upper | excludes 0.0273768 |
|---|---|---|---|---|
| T minus C | +0.031667 | no | +0.039722 | no |
| T minus B | +0.021118 | yes | +0.029444 | no |
| C minus B | +0.001667 | yes | +0.003056 | yes |

**T minus C is an underpowered null on both intervals.** Unambiguous.

**T minus B is a judgment call, and is presented as one.** Its BCa upper bound fails to exclude
the planning effect; its percentile upper bound excludes it. The frozen design requires both
intervals to be reported but does not say which one decides a label. The conservative bound was
taken, so T minus B is labeled an underpowered null. **The counterargument is on the record:**
the design's own stated reason for requiring both intervals is that BCa's acceleration constant
comes from a jackknife over 8 points and is unstable at that n, which is an argument for
weighting the percentile bound here. This choice is recorded rather than absorbed into a clean
number, and a reviewer is free to read it the other way.

**The anomaly protocol did not fire.** It triggers only on a positive C minus B. C minus B is
negative and not detectable (mean -0.011667, p 0.1328), consistent with the pre-registered
expectation that the draw-6 overhead is at or below zero.

### 5.6 The knob was not flat

The frozen design flags that if realized novelty scores are near-constant across the 6
candidates, T and C become the same procedure by construction and the contrast is uninformative.
The (null,null) cell requires this check before any "signal does not transfer" reading.

Across all 235 events:

| statistic | mean | SD | min | p25 | median | p75 | max |
|---|---|---|---|---|---|---|---|
| SD of the 6 | 0.041718 | 0.019122 | 0.009070 | 0.026553 | 0.039240 | 0.053986 | 0.099093 |
| range (max minus min) | 0.111916 | 0.053113 | 0.019604 | 0.069448 | 0.100014 | 0.147389 | 0.281178 |
| top3 minus bottom3 mean | 0.059437 | 0.026932 | 0.013339 | 0.038506 | 0.058594 | 0.074774 | 0.149801 |
| SD / within-run SD | 1.655675 | 0.776979 | 0.351328 | 1.037291 | 1.553828 | 2.142307 | 3.850752 |
| range / within-run SD | 4.444318 | 2.155840 | 0.845162 | 2.676116 | 4.028318 | 5.925279 | 10.595353 |
| (top3 minus bottom3) / within-run SD | 2.357535 | 1.094513 | 0.533328 | 1.534253 | 2.282464 | 3.008203 | 5.650293 |

The normalizing unit is that seed's within-run SD of the scorer, which is the unit beta is
expressed in. Exact-zero counts, which need no threshold: **0 of 235** events have a zero range,
and **0 of 235** have a zero top-3 minus bottom-3 gap. The smallest gap observed anywhere is
0.533 within-run SD.

The design states **no numeric threshold** for this check; its wording is "near-constant". So
this is a distributional report, not a criterion that passed or failed. On these numbers T and C
were selecting materially different minibatches.

For completeness, the expected overlap between the top-3 pick and a random 3-of-6 pick is
**1.500000** by exact enumeration over all 20 subsets, matching the hypergeometric mean, so 1.5
of 3 picks are expected to differ. That is a structural constant of pick-3-of-6, identical in
every arm and event, and does not depend on the scores.

### 5.7 Fragility of the primary contrast

One seed (T at seed 4, endpoint 0.657778) is the largest value in the table and contributes
+0.100000 of the T minus C paired difference. Excluding it moves the T minus C mean to
**-0.015556**. The sign pattern across the 8 paired differences is **3 positive, 5 negative**.
The flat primary mean rests heavily on one seed. That seed is not excluded from any reported
number.

### 5.8 Exploratory descriptives, no tests run

The design pre-registers the following as monitoring only. They are reported because a reviewer
will ask. **They support no mechanism claim.**

Per-arm, over the 8 seeds:

| arm | accept rate | SD | reflection events | SD | candidates incl. seed | SD |
|---|---|---|---|---|---|---|
| B | 0.345631 | 0.102666 | 31.2500 | 3.3700 | 11.5000 | 2.0000 |
| C | 0.255815 | 0.085197 | 26.0000 | 2.0702 | 7.5000 | 1.7728 |
| T | 0.383817 | 0.081259 | 23.3750 | 1.4079 | 9.8750 | 1.4577 |

Per seed, since the arm-level comparison is only checkable against these:

| seed | B events / accepts / rate | C events / accepts / rate | T events / accepts / rate |
|---|---|---|---|
| 0 | 32 / 10 / 0.312500 | 27 / 6 / 0.222222 | 23 / 9 / 0.391304 |
| 1 | 32 / 10 / 0.312500 | 30 / 3 / 0.100000 | 22 / 10 / 0.454545 |
| 2 | 35 / 8 / 0.228571 | 27 / 6 / 0.222222 | 23 / 9 / 0.391304 |
| 3 | 32 / 10 / 0.312500 | 25 / 8 / 0.320000 | 26 / 6 / 0.230769 |
| 4 | 27 / 13 / 0.481481 | 23 / 9 / 0.391304 | 23 / 9 / 0.391304 |
| 5 | 36 / 8 / 0.222222 | 26 / 6 / 0.230769 | 25 / 8 / 0.320000 |
| 6 | 29 / 12 / 0.413793 | 25 / 7 / 0.280000 | 23 / 9 / 0.391304 |
| 7 | 27 / 13 / 0.481481 | 25 / 7 / 0.280000 | 22 / 11 / 0.500000 |

T's accept rate exceeds C's on 6 of 8 seeds, ties on 1, and is lower on 1. No test was run on
this and none is licensed. Two confounds are live and both are sufficient on their own to explain
the pattern:

1. **Collider.** Accept rate is measured on the same minibatch the treatment manipulates.
2. **Headroom.** High-novelty examples may simply be ones the parent scores poorly on, leaving
   more room to improve, which would raise accept rate mechanically with no bearing on revision
   quality.

The primary hypothesis is pre-registered as a policy contrast, not a mechanism contrast. Any
mechanism claim from these numbers needs a separate designed experiment.

### 5.9 Estimator warning, binding

The endpoint estimator used in this section differs from the one used in the Stage-1 corpus that
block B draws on. The endpoints here must **not** be tabled alongside the specificity figure in
block B, and neither can be read as a continuation of the other. This is recorded as a dated
decision in the project's decision log.

---

## 6. What is closed, what is open, what was never run

**Treated as closed.**

- Static per-example selection over reflection content on IFBench. Five bounded nulls with one
  mechanism (id-determinism) that explains all of them. Closed as an investment decision,
  bounded by the stated MDEs, not proven zero.
- State-dependent selection as a **trajectory-level** lever at this budget and this power. No
  detectable endpoint effect; both contrasts labeled underpowered nulls, with the T minus B
  label resting on the judgment call in section 5.5.

**Open and constructive.**

- **The acceptance gate.** Where the pre-registered no-detection branch routes. The gate is
  measurably noisy (same-input disagreement 0.415 at n = 764; decision flips 0.203 at b' = 1 and
  0.104 at b' = 2), and 6.7% of 267 logged rejects flip under at least one aggregate rule.
  Whether changing the gate improves final utility is untested, because rejected children were
  never validation-scored.
- **The one-step to trajectory gap.** A real one-step effect on HoVer (specificity +0.0274, CI
  [+0.0149, +0.0415]) coexisting with no detectable trajectory-level endpoint effect is a
  measured boundary, now observed on the same benchmark by two independent routes. Explaining
  that gap is the most substantive open question here.
- **Transfer versus overfit on HoVer.** Transfer is unresolved (+0.0169, CI [-0.0040, +0.0367],
  below its MDE 0.0293), so whether the specificity effect generalizes beyond the batch it was
  derived from is not settled.

**Never run.**

- Any test of whether a modified acceptance gate improves validation utility. The gate work is
  entirely on logged rejects.
- Any designed test of the mechanism behind the arm-level accept-rate differences in section 5.8.
- The midpoint endpoint. Identified for every run, never evaluated on the test split, so no
  budget-sensitivity claim is available.
- A deployable pre-spend sampler test. The surviving scorer needs realized feedback, so the
  screen's live-confirm clause never fired and no static sampler was built or tested.
- Any replication at larger n. The design scales to 16 to 24 paired seeds under external compute,
  which would shrink the MDE by roughly a factor of the square root of 2 at double the seeds.
- The no-side-information mutation baseline. Whether reflection over side information beats blind
  instruction rewriting at all was never tested on either benchmark. Every result in this packet is
  a comparison among reflection variants, so none of them establishes that the reflection channel
  beats no channel.
- Rich-prose side information. Both benchmarks here have templated or semi-templated feedback.

---

## 7. Limitations and scope guards

**Power.** The state-dependent experiment is labeled confirmatory but is not well powered. Its
MDE (0.06332) is about 2.3 times the deflated planning effect the earlier screen predicts
(0.0273768). An effect the size the screen implies would not be reliably detected at 8 paired
seeds. A null here is bounded at the measured MDE and is not evidence of absence.

**Interval construction.** All cluster bootstraps here use 8 clusters and are anti-conservative.
This caveat attaches to every interval in this document. In the state-dependent block both
percentile and BCa intervals are reported, and they disagree on one labeling decision, as
section 5.5 sets out.

**Test exactness.** The sign-flip test is exact for the primary contrast (T minus C) under the
sharp null, because under that null the arms are mechanically identical processes differing only
in random number streams. For the secondary contrast (T minus B) the arms differ mechanically
regardless of any null, so exchangeability is an approximation. That is why it is secondary.

**Conservatism direction of the MDE.** The MDE assumes zero correlation between paired seeds.
Positive pairing correlation would shrink the true MDE, so 0.06332 is an upper bound.

**Benchmark and budget scope.** Everything here is at max_metric_calls 300, on gpt-4.1-mini, with
a deterministic metric. IFBench results are the verifiable instruction-following checklist regime
only. HoVer results are 3-hop claim verification over a local BM25 index only. Two benchmarks is
not a survey.

**One-step versus trajectory.** Blocks A and B measure one-step accept and minibatch margins.
Block C measures a trajectory endpoint. These are different quantities, and no result on one is
treated as a result on the other. That distinction is itself one of the findings.

**Estimator discontinuity.** As stated in section 5.9, the endpoint estimator changed between the
Stage-1 corpus and the state-dependent experiment. Do not table those numbers together.

**Mechanism naming.** The surviving scorer measures failure-composition novelty over a templated
feedback string of 118 to 198 bytes. It is not prose-content novelty.

**Accounting.** Spend figures recorded inside artifacts undercount, because per-process meters
reset when a process restarts. The figures in section 8 are reconstructed from logs.

**Deprecated figures.** One earlier same-input accept-disagreement figure was computed under a
mixed estimand and is deprecated for external use; the citable figure is 0.415 at n = 764. A
separate earlier figure from a different corpus and rule is not comparable to it. An MDE computed
on a synthetic endpoint distribution during machinery validation is not a result and is not cited
here. One local package version present on the authoring machine is not the version any run used.

---

## 8. Provenance

**Software and configuration for the state-dependent experiment.**

| field | value |
|---|---|
| gepa | 0.0.27 |
| dspy | 3.2.1 |
| task LM | openai/gpt-4.1-mini, max_tokens 3000, temperature 0, cache off |
| max_metric_calls | 300 |
| design | state-dependent-design-v2.1.1-frozen |
| run config commit | d963929f3bc43a1754a87a83d78ab895f5bf890c |
| selection split | n = 50, sha256 `b53216962a3efc46799a4871b379330eb3d460c4c9d5598b5e7cbabb03270fcc` |
| test split | n = 150, sha256 `a463c94af0aa65ad5187395c74d6a5060c3a8f7a723ceba3017752f08b7a2430` |

Both split hashes were verified identical across all 24 run directories at emission time.

**Emitters.** `emit_results.py` sha256 `c60cd689821cd8cd0d0c0087f50f4b8107fa2e6d27572c359f35c1aae9c62b8e`;
`emit_descriptives.py` sha256 `a1cfed65d46ee19f4c33dab4a2e14fa6503c9341f09b680feb934892dcfc5f34`;
`mde_sim.py` sha256 `6d11de278014b7e7de41cf55cb56cad4f92680f5b5f6159e7c6583bf84bce5cc`. Both
emitters compute every statistic twice by independent implementations and assert agreement to
1e-12 before writing. Verification performed before emission included: 24 endpoint files, 8 per
arm, seeds 0 through 7 present in every arm; each stored endpoint mean re-derived from its own
150-element score vector; 235 events each carrying exactly 6 novelty scores.

**Spend, state-dependent experiment.** Approximately **$189** across all gates: test split
$3.2336, smoke run $5.1942, the 24 optimization runs plus their 24 scoring passes $132.7603, dose
computation $8.3355, Stage-1 backfill approximately $39.39. One control pass cost was never
recorded, so the total is a lower bound on the true figure. Earlier per-process meters undercount
because they reset across restarts; these are reconstructed from run logs, which are not shipped
in this packet. The dose computation and backfill figures in particular are log-reconstructed and
cannot be checked against any file here; the $132.7603 figure can, from `liverun_ledger.json`.

**Verifying this document.** `TRACEABILITY.md` maps every number above to a file and line among
the 17 supporting files in this folder. `MANIFEST.md` lists those files with sha256 and a
one-line description of each. `mde_sim.py` reruns the MDE from the shipped endpoint distribution
at zero cost with no network or model calls.
