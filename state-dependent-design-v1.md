# State-Dependent Novelty Selection — Live Experiment Design (v1, pre-registration draft)

*Direction A of the GEPA SI-curriculum project. Repo: `gepa-si-curriculum`. Status: DRAFT for
external review — no spend authorized, no APPROVED file exists, no code written. This document
is the design + pre-registered interpretation map that must be frozen (committed + tagged)
before the smoke run, per standing discipline. Companion docs: `PROJECT-STATE-2026-07-06.md`,
`HANDOFF-screen-complete-classB.md`, `analysis/findings_summary.md` (ledger of record).*

*Reviewer instructions: this document will be checked for holes by an external reviewer with no
repo access. §2 is self-contained background. Every design choice is either specified exactly,
or explicitly flagged in §17 as an open decision with a default. Please attack: budget
accounting (§6), the fidelity of the deployed selection rule to the screened signal (§5),
endpoint definition (§8), the interpretation map's exhaustiveness (§9), inference validity at
n=8 clusters (§10–11), and the threats list (§15) for anything missing.*

---

## 1. Purpose

Test, live and causally, whether **state-dependent selection of the reflection minibatch by
SI-novelty** improves GEPA optimization outcomes on HoVer, against (a) a cost-matched random
control and (b) unmodified GEPA. This is the first *intervention* of the project's constructive
phase; everything to date is observational or one-step-interventional (batch-swap). It is also
the experiment that, if positive, earns the compute ask to the collaborator (scaling to
expensive benchmarks).

## 2. Background (self-contained; a cold reviewer needs nothing else)

**GEPA** optimizes the prompt of an LLM program by reflective evolution. Each iteration:
(1) select a parent candidate (Pareto selection over a validation set `D_pareto`);
(2) sample a minibatch `M` of `b=3` examples from a disjoint training set `D_feedback`;
(3) run the parent on `M`, producing per-example scores and a textual feedback string
("side information", SI — on HoVer, a rigid template listing retrieved and missed gold
document titles);
(4) a proposer LLM reads the three (Inputs, Outputs, Feedback) triples and writes a revised
prompt;
(5) the revision is accepted iff it beats the parent on the same `M`;
(6) accepted revisions get a full `D_pareto` evaluation and join the candidate pool.
Cost is dominated by evaluations; reflection is cheap. Minibatch evaluations (steps 3, 5) are
cheap per-call; the expensive unit is the accept-triggered full `D_pareto` eval.

**Prior results chain (all in the ledger; numbers cite-safe):**

1. **IFBench closure.** On IFBench (verifiable instruction-following, checklist SI), per-example
   selection is causally closed: no content scorer survives residualization on constraint
   identity; feedback-channel ablation inert (arms within 3pp, p ≥ 0.63); interventional
   batch-swap null (specificity +0.0054, 95% CI [-0.0116, +0.0242], MDE 0.033). Mechanism:
   IFBench SI is nearly a deterministic function of the failed-constraint-id set. Confound
   left open: IFBench's optimal prompt is plausibly batch-invariant boilerplate, predicting a
   swap null even under perfect reflection.
2. **HoVer batch-swap (positive).** Same swap design on HoVer, whose optimal prompt must be
   example-derived: pooled specificity **+0.0274**, run-cluster 95% CI **[+0.0149, +0.0415]**,
   MDE 0.0191 — the CI excludes zero and clears the MDE. Transfer +0.0169, CI [-0.0040,
   +0.0367], below its MDE 0.0293, unresolved. Conclusion: the reflection-input channel is
   causally active on HoVer; the IFBench null was task-scoped. Corpus: 8 seeds, 243 reflection
   events, 100-claim trainset, `max_metric_calls=300`, gpt-4.1-mini, local BM25 retrieval,
   deterministic metric.
3. **$0 heterogeneity screen (complete).** 108 scorer cells asked: which pre-computable or
   post-rollout-computable feature of a batch predicts *where* batch identity causally matters
   (i.e., predicts per-event swap specificity)? Pre-registered result cell 3: exactly one
   MCB-adjusted survivor, **`knn_emb_fb_min`** — the batch minimum of embedding-space novelty
   (all-MiniLM-L6-v2, k=3 NN distance) of each member's feedback-only SI text against the
   archive of all feedback texts from the run's prior reflection events. β=+0.03794 per SD,
   CI [+0.01045, +0.07031], permutation p=0.0013, LORO 8/8, held-out ρ=+0.115; difficulty
   controls leave it essentially unchanged (β=+0.03877). Every **Class A** (computable before
   running the parent) feature is null. The survivor is **Class B**: it requires the realized
   feedback, which only exists after the parent has run on the example.
4. **Consequence.** Per the pre-registered spend rule, no static (pre-spend) sampler live test
   is triggered — there is nothing pre-spend to deploy. The only deployable form of the
   surviving signal is **state-dependent**: draw more candidates than `b`, run the parent,
   observe the realized feedback, then choose which `b` to reflect on. This experiment is that
   deployment.

**Caveats inherited by this design** (from the screen, binding on power assumptions and
claims): the survivor's point estimate is below its own MDE (0.0379 vs 0.0429), so conditional
on detection the magnitude is likely winner's-curse inflated — **plan against ~half the point
estimate**; the rank-based analysis channel did not independently confirm it (p=0.071);
the signal is embedding-geometry-specific (TF-IDF variants null); mechanically it is novelty of
the *failure composition* (missed-title sets rendered through a rigid 118–198-byte template),
not prose-content novelty; all screen CIs carry the 8-cluster anti-conservative caveat.

## 3. Hypotheses (pre-registered)

- **H1 (primary, confirmatory).** At equal total metric-call budget, GEPA with state-dependent
  novelty selection of the reflection minibatch (arm T) achieves a higher pre-registered
  endpoint (§8) than a cost-matched random-selection control (arm C). H1 is the *mechanism*
  claim: selection by realized-SI novelty, holding eval cost and pick-3-of-6 mechanics fixed,
  improves outcomes.
- **H2 (secondary).** Arm T achieves a higher endpoint than unmodified GEPA (arm B) at equal
  total budget. H2 is the *deployment* claim: the selection gain survives the overhead of
  observing 6 candidates per event (fewer reflection events at fixed budget).
- **H3 (tertiary, monitored, not a test).** Arm C vs arm B isolates the pure overhead/mechanics
  effect of draw-6-pick-3-at-random. Expected ≤ 0 (overhead with no selection benefit). Reported
  descriptively with CI; no hypothesis test.

Directionality: H1 and H2 are one-sided in expectation but will be tested and reported
two-sided, consistent with prior project practice.

## 4. Arms

All arms: HoVer, same program (HoverMultiHop-style multi-hop retrieval via local BM25), same
task LM (gpt-4.1-mini), same deterministic metric, same 100-claim trainset from
`threehop.jsonl` and identical val/test splits as Stage 1, same `max_metric_calls` per run,
same code version (single commit), contemporaneous execution (all arms launched in the same
window, to neutralize API-side model drift).

- **Arm B — base GEPA.** Unmodified: sample `b=3` uniformly (epoch-shuffled without
  replacement), reflect on those 3, accept on those 3. Fresh runs, not reuse of Stage 1
  (rationale: gpt-4.1-mini is not a frozen artifact and repo code has moved since Stage 1;
  contemporaneous arms are the defensible comparison — see §17-D for the reuse option).
- **Arm C — matched control.** Each reflection event draws `M6` = 6 examples (the next 6 from
  the same epoch-shuffled stream), runs the parent on all 6, then selects 3 of the 6
  **uniformly at random** (seeded, arm-specific RNG stream, logged). Reflection and acceptance
  use the chosen 3 only. The unchosen 3 evaluations are logged but take no further part.
- **Arm T — treatment.** Identical to C except the 3-of-6 choice: compute each member's
  novelty against the run's SI archive (§5), and reflect on the 3-subset that **maximizes the
  minimum member novelty** (argmax over all C(6,3)=20 subsets of min-novelty; exact
  enumeration). Reflection and acceptance use the chosen 3 only.

Design rationale for the C arm: T differs from B in *three* ways (2× minibatch eval spend,
pick-3-of-6 mechanics, the selection rule). C matches the first two exactly, so T−C isolates
the selection rule — the only pre-registered confirmatory contrast. T−B is the deployment
question and confounds selection with overhead by construction; that is what makes it the
honest deployment estimate.

Why 6 (=2b): the swap's failure-match pairing machinery already evaluates the parent on 6
candidates per event, so the implementation skeleton and the cost profile are proven; and 2b is
the smallest oversampling that gives the subset-selector nontrivial room (20 subsets). Larger M
buys selection room at linear eval cost; out of scope for v1 (§17-A).

## 5. The selection rule — exact specification

**Fidelity requirement (binding):** the novelty computation MUST reuse the screen's
`knn_emb_fb_min` code path — same embedding model and revision (all-MiniLM-L6-v2, local, CPU,
pinned version recorded in the manifest), same text extraction (feedback-only section of the
reflection object, byte-identical extraction code), same distance (the screen's k-NN distance
definition — cosine, k=3, aggregation over the k distances exactly as implemented in
`features` code), same normalization. CC must import/reuse the function, not reimplement.
Any deviation is a silent-proxy-substitution incident.

**Archive definition:** the archive at event `t` contains the feedback texts of the examples
**actually reflected on** (the chosen 3) at events `1..t-1` of the same run. The unchosen 3
per event do NOT enter the archive. Rationale: the screened signal was novelty against
proposer-seen SI; the archive must be the same object. (Alternative — all 6 observed feedbacks
enter — is a different estimand; flagged §17-B.) Arm C maintains and logs the same archive
(from its chosen 3) for descriptive symmetry, but never uses it for selection.

**Edge cases (all deterministic, all logged):**
- *Cold start (archive empty, event 1):* both draw-6 arms select 3 of 6 uniformly at random
  from their arm-specific seeded RNG stream. Arms may diverge from event 1; that is fine —
  pairing is at the seed level (data order, init), not the trajectory level.
- *Archive smaller than k:* use all available neighbors (k' = |archive|).
- *Ties in the subset objective:* break by larger sum of member novelties, then by seeded RNG.
- *Identical feedback strings* (same missed-title set recurring): the embedding distance is 0
  by construction; no special-casing.

**Deliberately out of scope:** within-batch diversity terms (DPP etc.). The screened statistic
is min-novelty-vs-archive with no within-batch term; v1 deploys exactly the screened axis.

## 6. Budget and accounting (the design's most fragile joint — verify, don't assume)

**Budget definition:** all arms run to the same `max_metric_calls` (default: 300, matching
Stage 1; ratify in §17-C). Budget is total metric calls, counting parent minibatch evals,
child accept-test evals, and any valset evals, exactly as the installed gepa version counts
them. The draw-6 arms therefore spend 9 minibatch calls per event (6 parent + 3 child) vs
B's 6 (3+3), and will complete **fewer reflection events per run**. This is intentional:
fixed-total-budget is the deployment-honest comparison, and "fewer but better-selected
reflections" is precisely the trade under test. The alternative accounting (equal reflection
events) mechanically flatters T and C and is not used.

**Verification items (CC, during smoke, before APPROVED):**
1. Report exactly which calls increment the budget counter in the installed gepa version
   (minibatch parent, minibatch child, valset, test), from code reading plus a counted smoke —
   both channels must agree.
2. Confirm the 6 parent evals in draw-6 arms are counted (they are metric calls; if any code
   path exempts them, the arms are not budget-matched and the design breaks).
3. Report realized events/run per arm from the smoke. Expected order: B ≈ Stage 1's 27–34;
   T and C lower. Record the realized ratio; it parameterizes the overhead interpretation of H3.
4. Confirm the final test-set evaluation (§8) is OUTSIDE the optimization budget in all arms
   (post-hoc, identical protocol).
5. Confirm the unchosen 3 evals do not leak anywhere: not into acceptance, not into Pareto
   state, not into any frontier bookkeeping. Their scores exist only in our logs.

**Accept-gate semantics:** acceptance in all arms is the unmodified pointwise GEPA rule on the
chosen 3. The gate lane (issue #132 / aggregate rules) is explicitly NOT part of this
experiment; changing selector and gate simultaneously would unidentify both.

## 7. Seeds, pairing, randomization

- **n = 8 paired seeds** (same 8 as Stage 1 for continuity; ratify §17-E), each seed run in
  all three arms: 24 runs total. Pairing shares per-seed data shuffle, init prompt, and any
  seed-derived program state across arms; arm-specific RNG streams (control's random pick,
  treatment's tie-breaks) are derived as `f(seed, arm)` and logged.
- Sign-flip permutation on 8 paired differences has 2^8 = 256 sign patterns; minimum two-sided
  p = 2/256 ≈ 0.0078 — the design can, in principle, reach conventional significance, unlike
  a 4-seed design. But per project discipline, the CI and the interpretation map carry the
  decision, not the p-value (§10).
- **Task-LM sampling noise is NOT paired across arms** (the proposer lottery, same-input accept
  disagreement 0.415, is a known dominant noise source). Pairing removes seed-level variance
  only. This is the main reason the power section (§11) is conservative.
- Launch protocol: all 24 runs enumerated in a manifest before launch; execution in waves at
  the width the smoke's RSS measurement supports (§13); wave composition mixes arms (never
  "all of arm T first") to keep arms contemporaneous within API drift.

## 8. Endpoints and measurements

- **Primary endpoint (pre-registered):** final test-set score at budget exhaustion, defined as:
  the candidate with the highest `D_pareto` (valset) aggregate score when the budget counter
  exhausts, evaluated once on the held-out test split, identical protocol across arms, outside
  the budget. This matches the project's standing "best held-out test score at fixed budget"
  endpoint and GEPA's own final-selection convention.
- **Secondary endpoints (reported with CIs, labeled non-confirmatory):** best valset score at
  budget exhaustion; test score of the best-valset candidate at 50% budget (trajectory
  midpoint check).
- **Monitored descriptives (no tests):** reflection events/run; accept rate/arm (the coupling
  channel — novelty-selected batches may be systematically harder to beat pointwise, §15-4);
  number of valset evals triggered; chosen-batch min-novelty trajectory over events in T vs C
  (the saturation curve, §15-5); overlap between T's chosen sets and what C's random rule
  would have chosen (realized selection pressure); per-arm cost and wall-clock.

## 9. Pre-registered interpretation map (read results.md against this, nothing else)

Let ΔTC = paired mean (T − C), ΔTB = paired mean (T − B), each with its clustered CI. "Positive"
= CI excludes 0 above; "null" = CI straddles 0; "negative" = CI excludes 0 below. MDEs computed
per §11 accompany every cell; a null with MDE far above the deflated planning effect is
labeled "underpowered null", not evidence of absence.

| Cell | ΔTC | ΔTB | Reading | Action |
|---|---|---|---|---|
| 1 | + | + | Selection works and survives its own overhead. Constructive result; the compute-ask artifact exists. | Draft scaling proposal to Lakshya; consider replication seed-batch before external claims. |
| 2 | + | null/− | Selection works but overhead eats it at this budget. Mechanism validated, deployment not (at M=6, this budget). | Report both honestly; explore cheaper lookahead (smaller M, partial evals) before any scaling claim. |
| 3 | null | null | The screened one-step signal does not move trajectory outcomes at this power. The one-step→trajectory gap is real or the effect is below MDE. | Report bounded null; selection lane closes at trajectory level pending bigger budgets; gate lane (#132) becomes the constructive center. |
| 4 | null/− | − | Lookahead overhead strictly hurts and selection doesn't recover it. | As cell 3, plus: state-dependent selection at M=2b is dead on this benchmark/budget. |
| 5 | − | any | Novelty selection actively harms vs matched control (e.g., novelty chases unfixable outliers, or gate coupling collapses accept rate). | Genuine finding; check accept-rate and fixability descriptives for mechanism; report at full strength. |
| 6 | Discordant with H3 anomaly (C > B clearly) | | Pick-3-of-6 mechanics alone help — a design artifact or a real "screening by parent rollout" effect independent of novelty. | Flag as anomaly; investigate before interpreting ΔTC; do not promote any arm claim until resolved. |

Ambiguity rule: if secondary endpoints disagree in sign with the primary, the primary carries
the map; discordance is reported as a caveat, never used to upgrade a cell.

## 10. Statistical analysis plan

- **Estimator:** per-seed paired differences on the primary endpoint; report mean difference
  with a 95% CI by bias-corrected bootstrap over seeds (n=8 clusters; the standing
  anti-conservative caveat attaches to every CI and travels into any external text).
- **Test:** exact sign-flip permutation on the 8 paired differences (all 256 patterns),
  two-sided, for H1 (T−C). H2 (T−B) identical machinery, labeled secondary.
- **Multiplicity:** H1 is the single confirmatory test. H2 and everything else are reported
  with CIs and explicitly labeled non-confirmatory. No alpha spending scheme is needed with
  one confirmatory contrast.
- **Second path (binding):** all headline numbers recomputed by an independent code path from
  the raw per-run artifacts (per-draw score vectors → endpoint → differences), matching to
  reported precision, per the standing dual-path rule.
- **No interim analyses.** Results.md is numbers-only; interpretation happens only against §9
  after all 24 runs complete (or a wave-failure contingency is invoked, §13).
- **Outlier/failure handling, pre-registered:** a run that crashes and cleanly resumes
  (supervisor restart, no lost events) is a valid run. A run with corrupted/incomplete
  artifacts is rerun with the same seed before analysis; if irrecoverable, the seed is dropped
  from ALL arms (pairing preserved) and the reduced n is reported. No post-hoc exclusions on
  outcome values.

## 11. Power / MDE (honest version)

There is **no rigorous translation** from the screen's effect (β = +0.038 swap-specificity per
SD of batch min-novelty, one-step) to the trajectory endpoint (final test score). Any claimed
translation would be manufactured precision. Therefore:

1. **Planning effect:** per the winner's-curse caveat, plan against ~half the screened point
   estimate as the underlying one-step signal; treat the trajectory effect as unknown but
   plausibly smaller still (selection saturates as the archive grows, §15-5).
2. **MDE, computed not assumed (pre-APPROVED, $0):** from Stage 1's 8 final per-seed scores,
   compute the between-seed SD of the endpoint. Upper-bound the SD of paired differences by
   √2 × that SD (pairing can only help). MDE = the smallest mean paired difference for which
   the sign-flip test at n=8 reaches p < 0.05 with ~80% probability, by simulation from the
   Stage 1 empirical distribution. This number goes in plan.md next to the projected cost, and
   is read against the deflated planning effect *before* the APPROVED file is created — if MDE
   grossly exceeds any plausible effect, the honest options are more seeds or reframing the
   run as estimation-only, decided by Neel at the gate.
3. **Framing:** this experiment is powered as feasible, decided by CI + map. A cell-3 null is
   bounded by its measured MDE, never read as proof of zero.

## 12. Instrumentation and persistence (binding; violations void the run)

Per event, per run, persist: the 6 drawn example IDs (draw order); all 6 parent per-example
scores and full reflection objects (Inputs/Outputs/Feedback, bytes); the 6 novelty scores and
the archive size at scoring time (T; C logs novelty descriptively too); the chosen 3 and the
selection rationale record (subset objective values, tie-break events, RNG states); child
prompt text; child per-example scores on the chosen 3; accept decision; any valset eval
triggered and its per-example vector (`capture_traces=True`, standing persistence rule);
budget counter before/after. Plus per-run: config hash, code commit, embedding model
name+revision+file hash, seeds and derived RNG streams, wall-clock, cost. Manifest: raw facts
only, no interpretive prose. All of this applies to the smoke as well.

## 13. Operational plan (standing discipline, restated as the checklist)

1. Freeze this document: commit + tag (`state-dep-design-frozen`) BEFORE the smoke.
2. CC implements: oversized-draw sampler + post-rollout subset hook + logging. Implementation
   surface note: GEPA's loop is sampler → parent rollout → reflect → accept, so selection must
   intercept *between* parent rollout and reflection. CC identifies the minimal-diff insertion
   point (candidate: oversized minibatch from `next_minibatch_ids`, subset before
   `make_reflective_dataset`), confirms the accept test sees only the chosen 3, and confirms
   §6 verification item 5. CC reuses the screen's novelty code path per §5.
3. **Smoke: 1 full run of arm T, seed 0** (the arm exercising every new code path), measured:
   wall-clock, cost, per-process RSS, any API rate-limit backoffs, budget-counter audit (§6
   items 1–4), full persistence audit (§12). If the smoke reveals a design-breaking fact
   (e.g., budget accounting differs from §6), amend this doc, re-freeze, re-smoke.
4. plan.md: smoke-measured per-run cost and time × 24, MDE from §11-2, wave plan at the width
   the RSS measurement supports (≤ measured-safe; width 8 is the proven floor). Mixed-arm waves.
5. **APPROVED file: created by Neel only**, after reading plan.md. CC byte-verifies it on disk
   before any live spend. No APPROVED, no launch — no exceptions, including "just one more run".
6. Launch waves; supervisor with resume logic; `caffeinate`; no mid-flight analysis.
7. On completion: manifest sanity check, commit, tag pre-analysis snapshot, THEN results.md
   (numbers only), THEN Neel reads against §9, THEN interpretation, THEN second-path recompute
   before anything goes external.

Contingency: if a wave dies partway, resume before rerunning; a seed unrecoverable in any arm
drops that seed from all arms (§10).

## 14. Cost and time (projections — superseded by the smoke, never load-bearing)

Reference points: Stage 1 ≈ $2.14/run at this budget; overnight swap ran width 8 after mmap
fix (~0.93 GB/process). Projection: B ≈ Stage-1 cost; T and C add ~50% minibatch-side calls
but minibatch calls are a minority of spend where valset evals dominate — projected envelope
**$50–70 for all 24 runs**. Wall-clock: runs parallelize; at width 8 → 3 waves ≈ 3× single-run
time; if smoke RSS shows width 16–24 fits and no rate-limit backoffs, 1–2 waves. Expected
overall: an overnight-to-one-day execution once APPROVED. The calibration rule governs: only
smoke-measured numbers enter plan.md.

## 15. Threats to validity (attack this list)

1. **One-step → trajectory gap.** The screen's evidence is one-step (per-event swap
   specificity). Selection compounds over a trajectory in unmodeled ways; a null here does not
   contradict the screen, and a positive here is the first trajectory-level claim of the
   project. Scope every claim accordingly.
2. **Winner's-curse magnitude.** The screened effect is likely inflated (estimate below its
   own MDE). Mitigated by planning against half; residual risk: the true effect is below even
   the deflated figure → cell-3 underpowered null. §11-2's MDE-vs-effect read at the gate is
   the control.
3. **Endpoint coarseness.** HoVer's metric takes values in {0, 1/3, 2/3, 1} per claim;
   aggregate endpoints are means over the test split, so granularity is fine, but per-seed
   endpoint noise is substantial and the proposer lottery (0.415 same-input accept
   disagreement) injects unpaired noise. This is the dominant power threat.
4. **Gate coupling.** Novelty-selected batches may be systematically harder for the child to
   beat pointwise → lower accept rate in T → fewer pool updates → worse endpoint *through the
   gate, not through reflection quality*. This is a real causal path of the intervention (not
   a confound), but it changes the mechanism story. Accept rate/arm is the monitored
   discriminator; a cell-5 result gets read against it.
5. **Self-extinguishing novelty.** The archive grows; later events have less novelty spread to
   select on; the effect should decay within-run. Expected and monitored (novelty trajectory,
   §8). A positive result is a budget-scoped claim (~30 events/run) until tested longer.
6. **Embedding-geometry specificity.** The signal exists in MiniLM space only (TF-IDF null).
   Deployment reuses the exact geometry, so this threatens external validity (other tasks,
   other embedders), not internal validity here. Scope guard on claims.
7. **Mechanical identity of the signal.** HoVer feedback is a rigid template over
   missed/retrieved titles; the scorer is effectively smooth failure-composition novelty. Do
   not describe any win as "prose-content novelty". (Standing caveat 4 from the screen.)
8. **Budget-accounting error.** If the 6 parent evals were not counted (or counted
   differently) the arms are silently unmatched — the single most damaging implementation bug
   available. §6 verification items 1–2 exist for this; both code-reading and counted-smoke
   channels must agree.
9. **Contemporaneity/API drift.** gpt-4.1-mini is not frozen. Mixed-arm waves in one window
   mitigate; Stage-1-reuse for arm B was rejected for this reason.
10. **8-cluster inference.** Bootstrap CIs at n=8 are anti-conservative (standing caveat);
    the exact sign-flip test does not share this problem and is the confirmatory instrument.
11. **Unchosen-eval leakage.** If the 3 unchosen parent evals touch acceptance or Pareto
    state, arms differ in un-designed ways. §6 item 5.
12. **Selection-pressure degeneracy.** If realized novelty scores are near-constant across the
    6 (nothing to select on), T ≈ C by construction and the experiment measures nothing.
    Monitored: per-event novelty spread and T-vs-C choice overlap (§8). A cell-3 read must
    check this descriptive before concluding "signal doesn't transfer".
13. **Fixability tail.** 51.4% of missed gold titles are retrievable within BM25 k=1000;
    novelty selection may preferentially surface the unfixable tail. Contributes to cell-5
    mechanisms; descriptives (§8) plus per-event fixability stats (computable from logs) are
    the diagnostic.

## 16. Scope guards (what this experiment cannot claim, regardless of outcome)

One benchmark (HoVer), one task LM (gpt-4.1-mini), one budget (~300 metric calls, ~1 trainset
pass — the low-budget regime; at the paper's own HoVer budgets, 1.0–1.84 passes, dynamics may
differ), one oversampling factor (M=2b), one embedding geometry, pointwise gate unchanged.
"Static per-example selection" remains closed on IFBench and untested as a *sampler* on HoVer
(no Class A signal existed to deploy); this experiment speaks only to the state-dependent
form. Nulls are MDE/CI-bounded, never proof of zero. The static-vs-state-dependent distinction
is preserved in all external text.

## 17. Open decisions to ratify before freeze (defaults stated; Neel decides)

- **A. M = 6.** Default: yes (2b; proven skeleton and cost profile). Alternative M=9 buys
  selection room at +3 evals/event; rejected for v1.
- **B. Archive membership = chosen-3 only.** Default: yes (fidelity to the screened object).
  Alternative (all 6 observed) is a different estimand; if adopted it must be renamed and the
  fidelity claim to the screen dropped.
- **C. Budget = 300 metric calls.** Default: yes (comparability with Stage 1 and the swap
  corpus). Note this pins the low-budget scope (§16).
- **D. Fresh arm B, not Stage-1 reuse.** Default: fresh (~$17 insurance against code/API
  drift). Reuse would save that and break contemporaneity.
- **E. Seeds = Stage 1's 8.** Default: yes. If §11-2's MDE lands far above the deflated
  planning effect, the decision at the gate is more seeds vs estimation-only framing —
  Neel's call with the numbers in front of him.
- **F. Primary endpoint = final-candidate test score.** Default: yes (matches standing
  pre-registration language). Alternative (best-valset score) is secondary.

## 18. Deliverables

Frozen design (this doc, tagged) → CC implementation + smoke report (budget audit, RSS,
persistence audit, measured cost/time) → plan.md (smoke × 24 + MDE) → APPROVED (Neel) →
24 runs in mixed waves → manifest + commit + pre-analysis tag → results.md (numbers only) →
read against §9 → interpretation + second-path recompute → ledger entry in
`analysis/findings_summary.md` → external text (Lakshya) only after all of the above.
