# State-Dependent Novelty Selection — Live Experiment Design (v2, frozen pre-registration)

*Direction A of the GEPA SI-curriculum project. Repo: `gepa-si-curriculum`. Supersedes
`state-dependent-design-v1.md` (sha256 `8079c52c…d936`) after the external adversarial review
(`adversarial-review-state-dependent-design-v1.md`, sha256 `07c36cc1…64b6`). Every blocking issue
(R1–R4), freeze-pass fix (R5–R9, R11–R15), ops blocker (R10), minor (M1–M4), and repo-verification
item (V1–V6) has a landing site in this document; the coverage table is §19.*

**Ratifications recorded in this header, per Neel, 2026-07-09:**

> §17 defaults A–F ratified 2026-07-09 per external review concurrence; test-split and dose-control
> parameters ratified same date.

**Four further rulings made at freeze, each because a repo fact contradicted v1:**

- **§5 fidelity clause amended.** v1 bound CC to *"import/reuse the function, not reimplement"* the
  screen's novelty code. That is impossible: `screen_part3_features.py` instantiates the embedding
  model at module top level (`:35`), the k-NN is three inline lines inside a loop (`:237-243`), and
  `variant_texts` is nested inside `main()` (`:116-119`). Importing runs the model load and exposes
  nothing reusable; refactoring the file is forbidden by the standing do-not list. **Ruling:**
  re-implement, and prove equivalence by output rather than by shared code. §5 now requires a
  byte-verification gate. This substitutes *verified output identity* for *code-path identity*, and
  is stricter in the only sense that matters.
- **Test split.** Only 13 imperfect claims remain unconsumed by Stage 1, all `recall=0.0`. §8a's
  procedure is frozen here; the artifact is gated behind `APPROVED-testsplit` (§8a Amendment).
- **`SD_screen` is not a scalar.** The screen standardizes per-run. The dose is therefore computed
  per seed in that seed's own SD units; §11-0's gate uses `mean(D_s)`.
- **Environment pinned** (new §0), because two `gepa` installs exist on the machine and they
  disagree about how acceptance works.

**Two questions this document deliberately leaves open**, because they are design decisions no
prior document specifies and CC must not improvise them. Both must be resolved before
`APPROVED-liverun`. See §20.

---

## 0. Environment (binding; violations void the run)

**Optimizer.** `gepa==0.0.27`, interpreter `scratch/hover_probe/.venv/bin/python` (Python 3.12.13).
This is the version that ran Stage 1 (`scratch/hover_stage1/run_seeds.sh:7`,
`PY=../hover_probe/.venv/bin/python`). A **decoy editable checkout of `gepa` 0.1.1 exists at
`~/Desktop/gepa`**; its internals differ (it has `strategies/acceptance.py` and a deferred
`ProposalOutput` counter; 0.0.27 has neither and decides acceptance inline at `engine.py:490-493`).
**Every gepa citation in this document is 0.0.27.** Any citation to `strategies/acceptance.py` or
`StrictImprovementAcceptance` for these runs is from the wrong package.

**Arm-T runtime.** No pre-existing venv carries `gepa` + `dspy` + `sentence_transformers` together.
A dedicated venv `analysis/state_dep/.venv-armT` mirrors both donors: Python 3.12.13 and
`numpy==2.5.0` from the probe donor; `sentence_transformers==5.6.0`, `torch==2.13.0`,
`transformers==5.13.0`, `tokenizers==0.22.2`, `huggingface_hub==1.23.0`, `safetensors==0.8.0` from
the screen donor (`analysis/hover_screen/.venv-screen`), plus `gepa==0.0.27`, `dspy==3.2.1`.
Rationale: the screen's novelty numbers came from that embedding stack, and embedding output can
drift across ST/torch versions.

**Embedding pin.** `all-MiniLM-L6-v2`, snapshot
`1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, `model.safetensors` sha256
`53aa51172d142c89d9012cce15ae4d6cc0ca6895895114379cacb4fab128d9db`, 90,868,376 bytes. **All future
loads pass `revision=` pinned and `local_files_only=True`.** The screen itself did neither; its
reproducibility rests on the local cache happening to hold that snapshot.

**Scorer definition, verbatim:**

> `knn_emb_fb_min` = min over the ≤3 batch members of (mean over the 3 nearest strictly-prior
> same-run archive feedback blocks of (1 − cosine)), L2-normalized embeddings. The `_min` is
> batch-level aggregation, not a min over the k neighbours.

**Accept-rate convention.** Stage 1 = **89/243 = 0.3663 as-run**. Two accepts (`seed0 i=31`,
`seed5 i=23`) are IEEE-754 one-ULP artifacts that are exact ties on the thirds lattice: parent and
child sum to the same rational (7/3), but different addends give the child a double one ULP larger,
so the strict `>` at `engine.py:493` fires. Any simulation of the gate must replicate float
summation or it will drift by 2 events (exact-arithmetic rate would be 87/243 = 0.3580).

**Two acceptance gates run before any live spend, both $0, both STOP-on-fail** (§13).

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

**Split sizes and rates (R4-3, R4-4; verified in `notes/FREEZE.md`).**
`|D_feedback| = 100` (`stage1_run.py:42`), `|D_pareto| = 10` (`:41`), and **Stage 1 constructed no
test split at all** — `stage1_run.py:141` builds only `trainset` and `valset`. The test split used
by this experiment is constructed in §8a. Stage-1 accept rate = **89/243 = 0.3663**. One acceptance
costs exactly `|D_pareto| = 10` metric calls (§6).

### 2a. Specificity and transfer, defined (R4-1, R4-2)

These are the dependent variable of the screen and the unresolved link of the deployment
inference. Both are defined at `analysis/ablation/hover_swap/hover_swap_analysis.py:125-132`.

**Specificity** compares SAME-arm children (reflection input built from the parent executing on the
event's own batch `A_e`) against SWAP-arm children (reflection input built from the parent executing
on the failure-matched batch `B_e`). Each child is scored on **both** 3-example batches:

```python
spec.append((((mA_SAME - mA_SWAP) + (mB_SWAP - mB_SAME)) / 2) / 3.0)   # :131
```

Component A is evaluated on `A_e`, component B on `B_e`. On any single batch both arms share the
same parent baseline, so the baseline cancels (verified: max |diff| = 2.22e-16).

**Transfer** is the child's improvement over the parent measured on **the batch its reflection input
never saw** — SAME children on `B_e`, SWAP children on `A_e`:

```python
transf.append(((mB_SAME + mA_SWAP) / 2) / 3.0)                          # :132
```

**Both are evaluated on the two 3-example minibatches themselves. Neither touches the valset,
`D_pareto`, a held-out slice, or the test split.** Per-event unit: one reflection event contributes
one scalar to each; pooling is an unweighted mean over 243 events, with clustering entering the CI
only. This is what R6 means when it says the screened outcome is specificity, not quality: the
positive sign indicates own-batch advantage, evaluated locally.

**Prior results chain (all in the ledger; numbers cite-safe):**

1. **IFBench closure.** On IFBench (verifiable instruction-following, checklist SI), per-example
   selection is causally closed: no content scorer survives residualization on constraint
   identity; feedback-channel ablation inert (arms within 3pp, p ≥ 0.63); interventional
   batch-swap null (specificity +0.0054, 95% CI [-0.0116, +0.0242], MDE 0.033). Mechanism:
   IFBench SI is nearly a deterministic function of the failed-constraint-id set. Confound
   left open: IFBench's optimal prompt is plausibly batch-invariant boilerplate, predicting a
   swap null even under perfect reflection.
2. **HoVer batch-swap (positive).** Same swap design on HoVer, whose optimal prompt must be
   example-derived: pooled specificity **+0.027434842**, run-cluster 95% CI **[+0.0149, +0.0415]**,
   MDE 0.0191, perm p 0.0177. Transfer **+0.016918153**, CI [−0.0040, +0.0367], below its MDE
   0.0293, unresolved. Conclusion: the reflection-input channel is causally active on HoVer; the
   IFBench null was task-scoped. Corpus: 8 seeds, 243 reflection events, 100-claim trainset,
   `max_metric_calls=300`, gpt-4.1-mini, local BM25 retrieval, deterministic metric.
   *(Both point estimates independently recomputed from raw `pairs/*/draws.jsonl`; see
   `notes/FREEZE.md`. The map read against these numbers is `notes/D1-swap-read.md`.)*
3. **$0 heterogeneity screen (complete).** 108 scorer cells asked: which pre-computable or
   post-rollout-computable feature of a batch predicts *where* batch identity causally matters
   (i.e., predicts per-event swap specificity)? Pre-registered result cell 3: exactly one
   MCB-adjusted survivor, **`knn_emb_fb_min`** (§0 for the exact definition). β=+0.03794 per
   within-run SD, CI [+0.01045, +0.07031], permutation p=0.0013, LORO 8/8, held-out ρ=+0.115;
   difficulty controls leave it essentially unchanged (β=+0.03877). Every **Class A** (computable
   before running the parent) feature is null. The survivor is **Class B**: it requires the realized
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
  improves outcomes. *(Per R9, H1 is strictly a **policy** contrast, not a mechanism contrast —
  accept-rate divergence is downstream of the intervention. Mechanism attribution leans on the
  monitored descriptives; see §15-4.)*
- **H2 (secondary).** Arm T achieves a higher endpoint than unmodified GEPA (arm B) at equal
  total budget. H2 is the *deployment* claim: the selection gain survives the overhead of
  observing 6 candidates per event (fewer reflection events at fixed budget).
- **H3 (tertiary, monitored, not a test).** Arm C vs arm B isolates the pure overhead/mechanics
  effect of draw-6-pick-3-at-random. Expected ≤ 0 (overhead with no selection benefit). Reported
  descriptively with CI; no hypothesis test. *(C−B is also the trigger of §9's anomaly overlay.)*

Directionality: H1 and H2 are one-sided in expectation but will be tested and reported
two-sided, consistent with prior project practice.

## 4. Arms

All arms: HoVer, same program (HoverMultiHop-style multi-hop retrieval via local BM25), same
task LM (gpt-4.1-mini), same deterministic metric, same 100-claim trainset from
`threehop.jsonl` and identical val split as Stage 1, same `max_metric_calls` per run, same code
version (single commit), contemporaneous execution (all arms launched in the same window, to
neutralize API-side model drift). All three arms run through the **same** `GEPAEngine` wiring
(§13), never `dspy.GEPA`, so that V3's counter-parity check has meaning.

- **Arm B — base GEPA.** Unmodified: sample `b=3` uniformly (epoch-shuffled without
  replacement), reflect on those 3, accept on those 3. Fresh runs, not reuse of Stage 1
  (rationale: gpt-4.1-mini is not a frozen artifact and repo code has moved since Stage 1;
  contemporaneous arms are the defensible comparison — §17-D).
- **Arm C — matched control.** Each reflection event draws `M6` = 6 examples (the next 6 from
  the same epoch-shuffled stream), runs the parent on all 6, then selects 3 of the 6
  **uniformly at random** (seeded, arm-specific RNG stream, logged). Reflection and acceptance
  use the chosen 3 only. The unchosen 3 evaluations are logged but take no further part.
- **Arm T — treatment.** Identical to C except the 3-of-6 choice: compute each member's
  novelty against the run's SI archive (§5), and reflect on the **3 highest-novelty members**.
  Reflection and acceptance use the chosen 3 only.

Design rationale for the C arm: T differs from B in *three* ways (2× minibatch eval spend,
pick-3-of-6 mechanics, the selection rule). C matches the first two exactly, so T−C isolates
the selection rule — the only pre-registered confirmatory contrast. T−B is the deployment
question and confounds selection with overhead by construction; that is what makes it the
honest deployment estimate.

**Why 6 (=2b) (R5-b, corrected).** v1 justified M=6 as "the smallest oversampling that gives the
subset-selector nontrivial room (20 subsets)". That rationale was **false**, and is replaced.
Because each member's novelty is computed against the archive only, with no within-batch term
(§5), the subset objective "maximize the minimum member novelty" over C(6,3) subsets is *always*
maximized by the 3 highest-novelty items: the min of the top 3 dominates the min of every other
3-subset. The C(6,3)=20 enumeration is a sort in disguise. **The real selection room is
order-statistic room:** taking the top 3 of 6 draws pushes the selected min into the tail of the
draw distribution, and larger M pushes it further, at linear eval cost. M is therefore the obvious
v2 lever if the measured dose (§11-0) is small (§16). The swap's failure-match pairing machinery
already evaluates the parent on 6 candidates per event, so the implementation skeleton and cost
profile are proven.

## 5. The selection rule — exact specification

**Fidelity requirement (binding; amended at freeze — see header).** The novelty computation MUST
produce output identical to the screen's `knn_emb_fb_min` code path: same embedding model, snapshot
and revision (§0), same text extraction (the `## Feedback` section only, `screen_part3_features.py:117`),
same distance (1 − cosine on L2-normalized embeddings), same k (3), same aggregation over the k
neighbours (mean, `:241`), same batch-level `_min` (`:51`).

v1 required CC to *import* that code path. This is impossible without refactoring frozen files
(see header). **Instead:** CC re-implements the computation in `analysis/state_dep/novelty.py` and
must pass a **byte-verification gate** before any live spend:

> Recompute `knn_emb_fb_min` for all **235** non-NaN screen events and match
> `analysis/hover_screen/features.csv` to `< 1e-12`. Any mismatch is a STOP.

Plus a **cross-venv gate**: encode a sample of archive texts in `.venv-armT` and in the screen's own
`.venv-screen`, and `allclose`-compare. If those match, the fidelity requirement survives the
environment move. Failing either gate is a silent-proxy-substitution incident and halts the run.

**Selection (R5-a).** Implement as a **sort**, not a C(6,3) enumeration: rank the 6 members by
novelty descending, take the top 3. Identical output, fewer lines, fewer bugs. Keep the tie-break
cascade — exact ties at the 3rd/4th boundary are genuinely possible because identical missed-title
sets render to identical feedback strings, whose embedding distance is 0 by construction.

**Archive definition (V1, confirmed).** The archive at event `t` contains the feedback texts of the
examples **actually reflected on** (the chosen 3) at events `1..t-1` of the same run. The unchosen 3
per event do NOT enter the archive. This is exactly what the screen archived — verified in
`notes/FREEZE.md` Task 4: appended only at `screen_part3_features.py:334/:337` inside the
"STRICTLY after computing this event" block (`:327`), per-seed reset (`:140-145`), swap-arm text
never read anywhere in the screen. §17-B's default therefore stands and the fidelity claim holds.
Arm C maintains and logs the same archive (from its chosen 3) for descriptive symmetry, but never
uses it for selection.

**Edge cases (all deterministic, all logged):**
- *Cold start (archive empty, event 1):* both draw-6 arms select 3 of 6 uniformly at random. Per
  **M3**, T's event-1 pick uses the **same derived RNG substream** as C's picker, so T and C choose
  identically at event 1 given the same seed. No inferential consequence (pairing is at seed level);
  it marginally tightens the pairing and costs nothing.
- *Archive smaller than k:* only **ordinal-0 events** lack a k=3 archive. The archive grows by 3 per
  prior event, so every event with ordinal ≥ 1 has ≥ 3 neighbours. At ordinal 0 the arms fall back
  to the cold-start rule above. (The screen's own `knn_emb_fb_min` is NaN at exactly these 8 events,
  one per seed, out of 243.)
- *Ties in the subset objective:* break by larger sum of member novelties, then by seeded RNG.
- *Identical feedback strings* (same missed-title set recurring): the embedding distance is 0
  by construction; no special-casing.

**Deliberately out of scope:** within-batch diversity terms (DPP etc.). The screened statistic
is min-novelty-vs-archive with no within-batch term; v2 deploys exactly the screened axis.

## 6. Budget and accounting (the design's most fragile joint — verified, not assumed)

**Budget definition:** all arms run to the same `max_metric_calls` (**300**, matching Stage 1;
§17-C). Budget is total metric calls as the installed gepa counts them. The draw-6 arms spend 9
minibatch calls per event (6 parent + 3 child) vs B's 6 (3+3), and will complete **fewer reflection
events per run**. This is intentional: fixed-total-budget is the deployment-honest comparison, and
"fewer but better-selected reflections" is precisely the trade under test. The alternative
accounting (equal reflection events) mechanically flatters T and C and is not used.

### 6a. The counter, verified by code reading (§6 verification item 1, code half **DONE**)

`GEPAState.total_num_evals` is mutated at exactly five sites in gepa 0.0.27:

| # | Category | Site | Increment | This experiment |
|---|---|---|---|---|
| 1 | Seed program eval on full valset | `core/state.py:661` | `len(scores_by_val_id)` = **10** | once per run, all arms |
| 2 | Minibatch eval of the **parent** | `proposer/reflective_mutation/reflective_mutation.py:164` | `len(subsample_ids)` | **3** in B, **6** in T/C |
| 3 | Minibatch eval of the **child** | same file, `:332` | `actual_evals_count` | **3** in all arms |
| 4 | Full valset eval on **acceptance** | `core/engine.py:137` | `num_actual_evals` = **10** | per accept, all arms |
| 5 | Merge-candidate eval | `proposer/merge.py:392` | `actual_evals_count` | **never** — `merge_proposer=None` |

Site 2 is the mechanism by which the draw-6 arms pay for their lookahead: the parent legitimately
rolls out all 6 and all 6 are counted. Site 3 must see only the chosen 3 — the child is evaluated
via `cached_evaluate_full(new_candidate, chosen_ids, …)` (`:310`), and with no cache
`actual_evals_count = len(example_ids)` (`state.py:583`).

**Independent validation of the model** (Stage-1 seed 0, arithmetic only):
`10 + 6×32 + 10×10 = 302` metric calls; each HoVer metric call issues 3 hops × 2 predictors = 6 LM
calls; `302 × 6 = 1812`, which equals the logged `task_calls = 1812` exactly.

**Verification items (CC).**
1. Which calls increment the counter — *code-reading half DONE (above); counted-smoke half is the
   mocked count-audit (§13), executed at $0.*
2. Confirm the 6 parent evals in draw-6 arms are counted. **Verified by code:** site 2 increments
   `len(subsample_ids)`, which is 6. Re-verified in the count-audit.
3. Report realized events/run per arm from the smoke. Expected order: B ≈ Stage 1's 27–34;
   T and C lower. Record the realized ratio; it parameterizes H3's overhead interpretation.
4. Confirm the final test-set evaluation (§8) is OUTSIDE the optimization budget in all arms
   (post-hoc, identical protocol).
5. Confirm the unchosen 3 evals do not leak anywhere. **Verified by code:** acceptance reads only
   `proposal.subsample_scores_before/after` (`engine.py:490-493`), which the proposer restricts to
   the chosen 3; the Pareto frontier is updated **exclusively from valset scores**
   (`state.py:496-532`) and never sees a minibatch. The one place the unchosen 3 *would* be recorded
   is the trace (`subsample_ids`, `subsample_scores`), so the proposer writes the **chosen 3** there
   and stashes the full 6 under a separate key. Re-verified in the count-audit.
6. **(V3)** Verify B's counting on the *current* code, and that the seed-candidate valset eval
   increments identically in all three arms. This is why all arms share one engine wiring (§13).

### 6b. Mid-event exhaustion (R3), verbatim

> An event may begin only if remaining budget ≥ its minibatch cost (6 for B; 9 for T/C).
> Accept-triggered valset evals (10 calls) always complete and may overshoot the counter. The
> endpoint is read at the first counter state ≥ 300 after event completion.

### 6c. Resume semantics (R3), verbatim

> Event-level atomic checkpointing. Resume restores budget counter, archive contents, candidate
> pool, Pareto state, and all RNG streams exactly. A partially completed event is rolled back and
> replayed. Rolled-back calls do not increment the counter; every rollback is logged in the
> manifest with its burned-call count.

**Accept-gate semantics:** acceptance in all arms is the unmodified pointwise GEPA rule on the
chosen 3 (`engine.py:490-493`, strict `new_sum > old_sum`). The gate lane (issue #132 / aggregate
rules) is explicitly NOT part of this experiment; changing selector and gate simultaneously would
unidentify both.

## 7. Seeds, pairing, randomization

- **n = 8 paired seeds** (same 8 as Stage 1; §17-E), each run in all three arms: 24 runs total.
  Arm-specific RNG streams (C's random pick, T's tie-breaks) are derived as `f(seed, arm)`, drawn
  from **separate `random.Random` objects**, and logged.
- Sign-flip permutation on 8 paired differences has 2^8 = 256 sign patterns; minimum two-sided
  p = 2/256 ≈ 0.0078. Per project discipline, the CI and the interpretation map carry the
  decision, not the p-value (§10).

### 7a. What pairing does and does not share (V4, and a correction to v1)

v1 claimed pairing "shares per-seed data shuffle, init prompt, and any seed-derived program state
across arms." **That is false across B vs T/C**, for a reason that only shows up in the code.

`gepa.optimize` constructs **one** `rng = random.Random(seed)` (`api.py:256`) and hands the *same
object* to the batch sampler (`:302`), the Pareto candidate selector (`:261`), and merge (`:357`).
`EpochShuffledBatchSampler` pads the 100-example trainset to a multiple of `minibatch_size`
(100 → 102 for both b=3 and b=6), and `base_idx = state.i * minibatch_size` always lands on a
minibatch boundary — so **a draw never straddles an epoch boundary**; it wraps into a freshly
reshuffled epoch. But the reshuffle *timing* differs: **b=3 reshuffles at `state.i = 34, 68, …`;
b=6 at `state.i = 17, 34, …`**. From the first boundary the arms consume the shared stream
differently, so **parent selection diverges between B and T/C**, not merely batching.

Consequences, pre-registered:
- **T vs C are unaffected** — both draw 6, so they hit reshuffles at identical iterations and
  consume the shared stream identically; their arm-specific picks use separate RNG objects and never
  touch it. **H1, the only confirmatory contrast, is unharmed.**
- **B vs T/C share the seed, the initial prompt, and the first-epoch data order, but not the shared
  RNG stream past `state.i = 17`.** H2 is a package-level contrast anyway (R14), and this is one
  more reason it is secondary. Reported, not repaired.
- (The sampler's docstring claims determinism "via `state.rng1`". `GEPAState` has no such attribute;
  the real source is the injected `random.Random(seed)`. Determinism holds; the stated source does
  not exist.)

- **Task-LM sampling noise is NOT paired across arms** (the proposer lottery, same-input accept
  disagreement 0.415, is a known dominant noise source). Pairing removes seed-level variance
  only. This is the main reason §11 is conservative.
- Launch protocol: all 24 runs enumerated in a manifest before launch; execution in waves at
  the width the smoke's RSS measurement supports (§13); wave composition mixes arms (never
  "all of arm T first") to keep arms contemporaneous within API drift.

## 8. Endpoints and measurements

- **Primary endpoint (pre-registered):** final test-set score at budget exhaustion — the candidate
  with the highest `D_pareto` (valset) aggregate score when the budget counter exhausts (§6b),
  evaluated once on the held-out test split (§8a), identical protocol across arms, outside the
  budget.
- **Tie-break (R13-b, V5, verified).** gepa 0.0.27 returns
  `max(range(len(scores)), key=lambda i: scores[i])` over per-candidate mean val subscores
  (`core/result.py:82-88`). Python's `max` returns the first maximal element and `range` ascends, so
  **ties go to the lowest index = the earliest-accepted candidate.** This is adopted verbatim as the
  endpoint's tie-break. (It is a val-argmax, not a Pareto pick and not the last-accepted candidate.
  `eval_policy.get_best_program` uses a different tie-break but is used only for the end-of-run log
  event, and agrees here because `FullEvaluationPolicy` gives every candidate identical coverage.)
- **Zero-accept runs (R13-a).** At this budget a run can end with the seed candidate as the only
  valset-evaluated candidate. The endpoint is then the **seed prompt's test score**. This is valid
  and is not an excluded run.
- **Midpoint endpoint (R13-c).** Computed **post hoc**: identify the midpoint val-argmax from logs
  after the run, and evaluate it on test in the same post-run pass as the primary. Mid-flight
  processes never touch the test set. It is evaluated **only if a map cell's ambiguity rule demands
  it** (§9).
- **Secondary endpoints (reported with CIs, labeled non-confirmatory):** best valset score at
  budget exhaustion; the midpoint test score above.
- **Monitored descriptives (no tests):** reflection events/run; accept rate/arm (§15-4);
  number of valset evals triggered; **candidate count per arm** (R9 — the val-argmax is taken over
  arm-dependent candidate counts); chosen-batch min-novelty trajectory over events in T vs C (the
  saturation curve, §15-5); overlap between T's chosen sets and what C's random rule would have
  chosen (realized selection pressure); **per-event count of chosen examples whose missed-title set
  already appears in the archive, T vs C** (the coverage-starvation descriptive, §15-14);
  **realized cross-arm endpoint correlation** (R12); per-arm cost and wall-clock.

### 8a. The test split (new), verbatim parameters

> Test split: a seeded uniform sample (`random.Random(20260709)`) of N=150 claims from the graded
> threehop slice's imperfect claims (`recall<1.0`), excluding the 110 consumed by Stage 1
> (identified by reproducing `stage1_run.py:131-141` exactly). If fewer than 150 remain, N = all
> remaining, and **N<100 is a STOP-and-flag**. The sampled split is committed as a JSON artifact
> with sha256 BEFORE any test evaluation exists. Uniform sampling, not sort-order continuation: the
> 110 took the highest-recall imperfect claims, so continuation would yield a systematically harder
> test set. Test evals are post-hoc and outside the optimization budget. Stage-1 backfill: the 8
> Stage-1 final candidates (per the §8 selection convention) are evaluated on this split to provide
> the §11 MDE's endpoint distribution.

**Amendment (2026-07-09, ratified at freeze). The STOP fired.** Reproducing `stage1_run.py:131-141`
exactly: 245 graded records → 123 imperfect → 110 consumed → **13 remain, and all 13 have
`recall = 0.0`**. 13 < 100. The remainder is not merely small, it is the hardest tier only: the sort
key `(-recall, claim)` consumed all 70 claims at recall 2/3 and all 35 at 1/3, then 5 of the 18
zeros. A test split drawn from it would be maximally unrepresentative.

Resolution, pre-registered here:

- The test pool is **freshly graded claims** from `threehop.jsonl` beyond the graded slice
  (indices ≥ 295; the graded file spans 50–294 contiguous, and 1,620 claims remain ungraded).
- Grading is `grade_threehop.py`'s procedure — the same 3-hop program, retrieval, and model — and it
  **calls an LM**, so it is live spend, not $0. Expected: imperfect rate 123/245 = 0.502, so ~299
  claims graded yields ~150 imperfect, at ≈ $0.00447/claim ⇒ **≈ $1.33**.
- This spend is gated behind a new **`APPROVED-testsplit`** file, created by Neel, byte-verified by
  CC before the grading runs.
- The split is then a uniform `random.Random(20260709)` sample of N=150 from the newly graded
  imperfect claims, keyed on `threehop_idx` (unique, stable), committed as JSON with its sha256
  before any test evaluation exists. Disjointness from the 110 is automatic (new indices).
- **Known distributional consequence, recorded now:** a uniform sample of imperfect claims carries
  the natural imperfect mix (~14.6% at recall 0), whereas Stage-1's train split carries ~4.5%. The
  test split will therefore be somewhat harder than train. This is the honest choice and is
  preferred to sort-order continuation, which would be *much* harder. Whether to instead
  recall-stratify the test split to match train's mix is **not** decided here (§20).
- **Cascade:** no test split → no Stage-1 backfill → no MDE. `plan.md` carries an MDE placeholder
  until `APPROVED-testsplit` and `APPROVED-backfill` clear.

## 9. Pre-registered interpretation map (read `results.md` against this, nothing else)

*(Replaces v1 §9 entirely, per R1 and M1. The v1 table was not a partition and its cell-6 row was
structurally broken markdown.)*

Sign determination (all contrasts): 'positive' iff two-sided exact sign-flip p<0.05 with mean>0 on
paired differences; 'negative' iff p<0.05 with mean<0; otherwise 'null'. H1 machinery for ΔTC
(confirmatory); identical machinery for ΔTB and C−B (secondary, labeled). CIs carry magnitude and
the underpowered-null label only: any null whose CI cannot exclude the deflated planning effect is
labeled 'underpowered null', never evidence of absence.

Anomaly overlay, evaluated FIRST: if C−B is positive by the above criterion, enter the anomaly
protocol (pick-3-of-6 mechanics or parent-rollout screening is itself doing work): investigate
overlap, degeneracy, and accept-rate descriptives and document before reading the grid. No grid cell
is read until the anomaly is resolved in writing.

The grid (ΔTC, ΔTB):

- **(+,+)** Selection works and survives its overhead. Constructive result; the compute-scaling
  artifact exists. Consider a replication seed batch before external claims.
- **(+,null)** Mechanism detected; deployment gain undetected. Report both; cheaper lookahead
  (smaller M, partial evals) before any scaling claim.
- **(+,−)** Mechanism detected; package loses to base — overhead strictly dominates at this budget.
  As (+,null), plus overhead diagnosis via the events-per-run ratio.
- **(null,+)** Deployment gain without detected mechanism. Mechanism claim is unproven; consult
  C−B, overlap, and selection-pressure descriptives; external framing limited to the package-level
  claim.
- **(null,null)** No detection. Bounded null at measured MDE. Consult the degeneracy descriptive
  (§15-12) before any 'signal does not transfer' reading. Selection lane closes at trajectory level
  at this budget/power; gate lane becomes the constructive center.
- **(null,−)** Package hurts, selection undetected. As (null,null), plus: lookahead overhead is
  net-negative at M=2b at this budget.
- **(−,+)** Arithmetically implies C>T>B; the anomaly overlay must already have fired. Anomaly
  protocol; no independent reading.
- **(−,null)** Selection harms vs matched control. Full-strength finding; consult accept-rate,
  coverage-starvation, and fixability descriptives for mechanism.
- **(−,−)** Novelty selection actively harms. Full-strength negative finding plus mechanism
  diagnostics as above.

Ambiguity rule: secondary endpoints disagreeing in sign with the primary are reported as caveats
and never upgrade a cell.

## 10. Statistical analysis plan

- **Estimator:** per-seed paired differences on the primary endpoint; report mean difference
  with a 95% CI by bias-corrected bootstrap over seeds (n=8 clusters; the standing
  anti-conservative caveat attaches to every CI and travels into any external text).
  **Per M2, report the percentile bootstrap CI alongside BCa** — BCa's acceleration constant comes
  from a jackknife over 8 points and is unstable at this n.
- **Test:** exact sign-flip permutation on the 8 paired differences (all 256 patterns),
  two-sided, for H1 (T−C). H2 (T−B) identical machinery, labeled secondary.
- **Exactness is an H1 property, not an H2 property (R14).** The sign-flip test is exact under
  within-pair exchangeability. For T vs C that holds under the sharp null "the selection rule does
  nothing": the arms are then mechanically identical processes differing only in independent RNG
  streams. For T vs B the arms differ in mechanics regardless of any null, the relevant sharp null
  is package-level, and exchangeability is an approximation. This is *the* reason H2 is secondary.
- **Seed floor (R15), pre-registered.** Minimum two-sided sign-flip p is 2/2^n: n=8 → 0.0078,
  n=7 → 0.0156, n=6 → 0.0313, n=5 → 0.0625, at which the confirmatory test can no longer reach
  α=0.05 at all. **With fewer than 6 usable pairs the confirmatory test is void and the experiment
  reports as estimation-only.**
- **Multiplicity:** H1 is the single confirmatory test. H2 and everything else are reported
  with CIs and explicitly labeled non-confirmatory.
- **Second path (binding):** all headline numbers recomputed by an independent code path from
  the raw per-run artifacts (per-draw score vectors → val-argmax → endpoint → differences), matching
  to reported precision. *Note (V6/B8): the persisted `gepa_result.json` is a custom `state_dump`,
  not gepa's `GEPAResult` schema — it carries no `val_aggregate_scores` and no `best_idx`. The
  endpoint must be recomputed from `prog_candidate_val_subscores`.*
- **No interim analyses.** `results.md` is numbers-only; interpretation happens only against §9
  after all 24 runs complete (or a wave-failure contingency is invoked, §13).
- **Outlier/failure handling, pre-registered:** a run that crashes and cleanly resumes (§6c) is a
  valid run. A run with corrupted/incomplete artifacts is rerun with the same seed before analysis;
  if irrecoverable, the seed is dropped from ALL arms (pairing preserved) and the reduced n is
  reported, subject to the seed floor above. No post-hoc exclusions on outcome values.

## 11. Power / MDE

There is **no rigorous translation** from the screen's effect (β = +0.03794 swap-specificity per
within-run SD of batch min-novelty, one-step) to the trajectory endpoint (final test score). Any
claimed translation would be manufactured precision. What v1 lacked, and R2 supplied, is that the
intervention delivers some number of SDs — a **dose** — and the implied one-step effect is
`D × β/2`, not `β/2`. Nothing in v1 estimated D. §11-0 does.

### 11-0. Dose computation (pre-registered; executes pre-APPROVED under its own gate)

**Inputs.** For each of the 243 swap events, the parent's feedback texts for all 6 `draw6`
candidates: **3 parsed** from `reflect_in_SWAP.txt` (the matched `B_e`), **3 re-derived** by
re-executing the parent (gepa 0.0.27 venv, temp-0 task LM, `capture_traces=True`, feedback rendered
via the identical `make_reflective_dataset` path as `hover_swap_run.py:201`).

> *Why re-derivation is needed (V2, resolved).* R2 assumed all 6 feedback texts were on disk. They
> are not, for **any** of the 243 events. The parent *is* evaluated on all 6
> (`hover_swap_run.py:191`), but `make_reflective_dataset` is called only on `ebA`/`ebB` (`:201`)
> and only two bundled prompt files are written (`:205`). Verified on bytes: 243/243 pair dirs hold
> exactly `{draws.jsonl, meta.json, reflect_in_SAME.txt, reflect_in_SWAP.txt}`, each reflect file
> holding exactly 3 `# Example` blocks. `A_e` is disjoint from `draw6` in 0/243 records, so it
> covers none of the 6. The 3 unmatched candidates have neither feedback text nor a persisted parent
> score. R2's stated fallback ("reflected-3-plus-swapped-3") is therefore **not** a fallback to the
> full-6 statistic; it is a different, biased statistic (see the STOP rule below).

**Archive per event.** The screen's archive state (reflected-3, strictly prior, same seed), via the
screen's own semantics (§5, V1).

**Novelty per candidate.** The exact screen k-NN computation (§0). **Ordinal-0 events excluded** (no
k=3 archive) — 8 events, one per seed.

**Per-event gap.** Novelty of the 3rd-highest candidate — i.e. the 4th order statistic ascending of
the 6, which *is* the deployed selector's min (R5-c) — **minus** the expected min of a uniformly
random 3-subset, computed by exact enumeration over all C(6,3)=20 subsets:

```
gap_e  =  x_(4)  −  (1/20) · Σ_{S ⊂ {1..6}, |S|=3} min(x_S)        [x ascending]
```

**Dose (ratified 2026-07-09).** `SD_screen` is **not a scalar**: the screen standardizes per-run
(`screen_part4_stats.py:56-64`, `sd = col[m].std()` per seed, ddof=0), and the 8 within-run SDs span
`[0.021870, 0.024433, 0.029460, 0.023196, 0.028713, 0.025238, 0.025011, 0.026538]` — a ~35% spread.
Therefore:

```
D_s  =  mean_{e ∈ seed s} gap_e  /  sd_s          (each seed in its own SD units)
D    =  mean_s D_s                                 (the scalar §11-2's gate consumes)
```

**Outputs.** `D` pooled and per-seed; the per-event gap distribution; the per-event novelty spread
(max−min and SD of the 6) as the §15-12 degeneracy pre-estimate; and, for free, the expected T-vs-C
choice overlap.

**Determinism control, gating execution.** A seeded sample (`random.Random(20260709)`) of 30 events:
re-execute the matched `B_e` and byte-compare each re-rendered feedback block against the persisted
`reflect_in_SWAP.txt` block. **30/30 byte-exact → proceed** to the 3 unmatched re-derivations. Any
failure → **STOP**; Neel decides. Pre-registered fallback: **drop the dose from v2** (the review's
option 3); **never** the biased 3-candidate shrink, because `B_idx = combo` was *selected* to match
the parent's score profile on `A_e` and is not a uniform 3-subset of the 6.

> The control is what makes this worth spending on: it is a free check that the temp-0 task LM
> (`hover_swap_run.py:160`, no `temperature` arg ⇒ dspy default 0.0, `cache=False`) reproduces
> in-run bytes. Temp-0 is not a bitwise contract at the API level; the control converts that
> assumption into a measurement.

**Cost.** Control: 30 events × 3 matched = 90 metric calls. Re-derivation: 3 unmatched × the event
set. At `m ≈ $0.004543/metric call` (§14): **819 calls ≈ $3.72** if the event set is all 243;
**795 calls ≈ $3.61** if ordinal-0 events are excluded as this section specifies. The discrepancy is
flagged in §20; it does not change the order of magnitude. Superseded by the 5-event smoke.
Gated behind **`APPROVED-dose`**.

### 11-1. Planning effect

Per the winner's-curse caveat, plan against ~half the screened point estimate as the underlying
one-step signal: the implied one-step effect is **`D × β/2`**, with `β = +0.03794`. Per **R6**, the
trajectory effect is **unknown in sign as well as magnitude**. The deployment inference chains
novelty → specificity (established, one-step, **local**) → generalizable gain (**unresolved**;
transfer's CI straddles 0) → trajectory outcome (untested), and the second link's sign is not pinned
by the prior chain. A cell-(−,·) outcome is not a tail risk; it is a live branch of the existing
evidence — local specificity could be local overfitting that the pointwise gate then rewards.

R2's ceiling argument, recorded: under iid scores the top-3-of-6 min sits around one SD above a
random 3-subset min, and within-event novelty scores share an archive and are positively correlated,
so D is realistically well under 1 SD. Even at D=1 the implied one-step effect is ~0.019 — roughly
the swap experiment's own MDE — before any one-step-to-trajectory attenuation. **The §11-2 gate is
more likely than not to bite.**

### 11-2. MDE, computed not assumed (pre-APPROVED)

MDE is computed **in endpoint units** from the backfilled Stage-1 test scores (§8a). DGP, verbatim:

> Per synthetic replicate, draw 8 paired differences as X_T − X_C with both margins drawn
> independently from the backfilled Stage-1 empirical endpoint distribution (independence encodes
> ρ=0, consistent with the √2 bound); shift by the candidate effect; apply the two-sided exact
> sign-flip at α=0.05; MDE = smallest shift reaching 80% rejection. The simulation script is
> committed and its hash cited in `plan.md`.

Gate criterion, verbatim:

> If `MDE_endpoint > 3 × (D × β/2)`, in one-step specificity units, the default flips to
> estimation-only framing or a seed increase; the choice between those two, but not the trigger, is
> decided at the gate. This juxtaposes endpoint units against one-step specificity units and is a
> **heuristic screen, not a power calculation**. The seed-increase branch is live: the design scales
> to 16–24 paired seeds under external compute, shrinking MDE by ~√2 at 2× seeds.

### 11-3. Caveats on the bound

- **The √2 bound is conditional (R12).** `SD(diff) = √(σ_T² + σ_C² − 2ρ σ_T σ_C)` exceeds `√2·σ`
  when ρ<0. Shared seed components (data order, init prompt) make ρ≥0 the sensible prior, so the
  bound stands — but the proposer lottery drives ρ toward 0, so **pairing likely buys little here**.
  The realized cross-arm endpoint correlation is reported (§8).
- **Stage-1's SD is a B-arm quantity (R12).** T and C complete fewer events and plausibly have
  higher endpoint variance, so the MDE inherits an **unquantified optimism**.
- **Framing.** This experiment is powered as feasible, decided by CI + map. A (null,null) result is
  bounded by its measured MDE, never read as proof of zero.

## 12. Instrumentation and persistence (binding; violations void the run)

Per event, per run, persist: the 6 drawn example IDs (draw order); all 6 parent per-example
scores and full reflection objects (Inputs/Outputs/Feedback, bytes); the 6 novelty scores and
the archive size at scoring time (T; C logs novelty descriptively too); the chosen 3 and the
selection rationale record (sorted novelty vector, tie-break events, RNG states); child
prompt text; child per-example scores on the chosen 3; accept decision; any valset eval
triggered and its per-example vector (`capture_traces=True`); budget counter before/after; and the
**rollback log** (§6c) with burned-call counts. Plus per-run: config hash, code commit, embedding
model name+revision+file hash, seeds and derived RNG streams, wall-clock, cost. Manifest: raw facts
only, no interpretive prose. All of this applies to the smoke as well.

**Trace-field contract.** `subsample_ids`, `subsample_scores`, `new_subsample_scores` carry the
**chosen 3**; the full 6 are stashed under separate keys. Existing tooling asserts batch size 3
(`screen_part0.py:167-168`).

**V6 (second-path sufficiency), verified.** This set suffices to recompute, from raw artifacts
alone: (a) all 6 novelty scores per event — feedback bytes, archive membership at scoring time, and
the embedding model file hash are all persisted; (b) the endpoint chain — per-draw score vectors →
val-argmax (§8 tie-break) → test score. One gap closed at freeze: because `gepa_result.json` is a
custom `state_dump` without `val_aggregate_scores`/`best_idx` (B8), the runner must persist
`prog_candidate_val_subscores` per candidate, which it does.

## 13. Operational plan

1. Freeze this document: commit + tag (`state-dep-design-v2-frozen`) BEFORE the smoke.
2. **The two $0 acceptance gates (§5), both STOP-on-fail:** cross-venv embedding `allclose`; and
   the 235-row byte-verification of `knn_emb_fb_min` against `features.csv`. Neither costs a cent
   and both must pass before a single live call.
3. CC implements: oversized-draw sampler + post-rollout subset hook + logging.
   **Implementation surface, verified.** `dspy.GEPA` cannot inject a batch sampler — its `__init__`
   has no such parameter (the docstring at `dspy/teleprompt/gepa/gepa.py:284` claims one; it does
   not exist) and it hard-passes `reflection_minibatch_size=3`, which trips the assert at
   `api.py:304`. `gepa.optimize()` exposes `batch_sampler` but **no proposer** parameter, and the
   6→3 selection must live in the proposer, between the parent rollout (`:163`) and
   `make_reflective_dataset` (`:230`). Therefore **all three arms wire `GEPAEngine` directly**
   (`engine.py:59` accepts `reflective_proposer`), replicating `api.py:256-387`, with
   `merge_proposer=None` (note: `dspy.GEPA` defaults `use_merge=True` while `gepa.optimize` defaults
   `False`). Running B through `dspy.GEPA` while T/C use `GEPAEngine` would make V3's counter-parity
   check meaningless.
4. **Micro-smokes of ALL THREE arms in count-audit mode with a mocked task LM ($0) (R10).**
   Acceptance criterion: every arm's counter agrees with the §6a five-site model on every call
   category. This directly closes threat 8 (silently unmatched arms), which a T-only smoke cannot
   detect. The live smoke (arm T, seed 0, real LM) remains post-APPROVED.
5. **The smoke run is excluded from analysis unconditionally**, and seed-0 arm T is rerun inside the
   mixed waves like every other cell.
6. `plan.md`: smoke-measured per-run cost and time × 24, MDE from §11-2, wave plan at the width the
   RSS measurement supports (≤ measured-safe; width 8 is the proven floor). Mixed-arm waves.
7. **APPROVED files: created by Neel only**, after reading `plan.md`. CC byte-verifies each on disk
   before the corresponding spend. Gates: `APPROVED-testsplit`, `APPROVED-dose`,
   `APPROVED-backfill`, `APPROVED-liverun`. No APPROVED, no launch — no exceptions.
8. Launch waves; supervisor with resume logic (§6c); `caffeinate`; no mid-flight analysis.
9. On completion: manifest sanity check, commit, tag pre-analysis snapshot, THEN `results.md`
   (numbers only), THEN Neel reads against §9, THEN interpretation, THEN second-path recompute
   before anything goes external.

Contingency: if a wave dies partway, resume before rerunning; a seed unrecoverable in any arm
drops that seed from all arms (§10), subject to the seed floor.

## 14. Cost and time (projections — superseded by the smokes, never load-bearing)

**Fitted rate.** Solving two observed spends for per-metric-call cost `m` and per-reflection-call
cost `r`:

```
Stage-1 seed0:  302 metric calls + 32 reflection calls = $1.9078   (run_summary.json)
Swap, per pair:  45 metric calls +  6 reflection calls = $0.3049   (mean pair_cost_usd, n=243)
  ⇒  m ≈ $0.004543 / metric call ,  r ≈ $0.016744 / reflection call
```

Independently corroborated: `grade_threehop.py` graded 245 claims (1 metric call each) for $1.0942 ⇒
$0.00447/claim, within 2% of `m`.

| line item | quantity | est. cost | gate |
|---|---|---|---|
| Test-split grading | ~299 claims × m | **~$1.33** | `APPROVED-testsplit` |
| Dose determinism control | 30 events × 3 | ~$0.41 | `APPROVED-dose` |
| Dose re-derivation | 705–729 calls | **~$3.20–3.31** | `APPROVED-dose` |
| Stage-1 backfill | 8 candidates × N × m | **~$5.45** at N=150 | `APPROVED-backfill` |
| Per-run test evals (**2 per run**: primary + midpoint, M4) | 2 × N × m | ~$1.36/run | `APPROVED-liverun` |
| 24 runs, optimization | B ≈ Stage-1 cost; T/C add ~50% minibatch-side calls | **$50–70** envelope | `APPROVED-liverun` |

Wall-clock: runs parallelize; at width 8 → 3 waves ≈ 3× single-run time; if smoke RSS shows width
16–24 fits and no rate-limit backoffs, 1–2 waves. Expected overall: an overnight-to-one-day
execution once APPROVED. **The calibration rule governs: only smoke-measured numbers enter
`plan.md`.** Every figure above is an estimate and is superseded on contact with a smoke.

## 15. Threats to validity

1. **One-step → trajectory gap, sharpened (R6).** The evidence chain is: novelty → **own-batch
   margin** (established, +0.0274, CI excludes 0) → **opposite-batch margin** (unresolved, +0.0169,
   CI straddles 0) → **valset/test outcome** (never measured by anything in the prior chain). The
   second link's sign is not pinned. Further, this experiment is a **Goodhart test of an
   observationally screened correlate**: selecting on the feature is a distribution shift under
   which the screened relation need not persist, LORO and residualization notwithstanding. That is
   exactly what a live test is for, so no design change follows — but a (null,·) or (−,·) result
   reads as the design anticipating the outcome, not being ambushed by it.
2. **Winner's-curse magnitude.** The screened effect is likely inflated (estimate below its
   own MDE). Mitigated by planning against half; residual risk: the true effect is below even
   the deflated figure → underpowered null. §11-2's gate is the control.
3. **Endpoint coarseness.** HoVer's metric takes values in {0, 1/3, 2/3, 1} per claim;
   aggregate endpoints are means over the test split, so granularity is fine, but per-seed
   endpoint noise is substantial and the proposer lottery (0.415 same-input accept
   disagreement) injects unpaired noise. This is the dominant power threat.
4. **Gate coupling, and its budget/endpoint consequences (R9).** Novelty-selected batches may be
   systematically harder for the child to beat pointwise → lower accept rate in T. Two downstream
   consequences: (a) **budget composition** — fewer accepts means fewer valset evals, which at fixed
   total budget means **more** reflection events, partially self-compensating in event count while
   starving the candidate pool; (b) **endpoint machinery** — the primary endpoint is the test score
   of the val-argmax, and the argmax is taken over however many candidates got full valset evals.
   Arms with more candidates take a max over more draws, changing the endpoint's selection-noise
   properties (higher expected val max, regression-to-the-mean penalty on its test score). For H2
   this is baked into "deployment honest". For H1 it arises only through accept-rate divergence,
   i.e. it is *downstream of the intervention, not a confound* — but it does mean H1 as stated is a
   **policy contrast**, not a mechanism contrast. Mechanism attribution leans on the monitored
   descriptives (accept rate/arm, candidate count/arm).
5. **Self-extinguishing novelty.** The archive grows; later events have less novelty spread to
   select on; the effect should decay within-run. Expected and monitored (novelty trajectory, §8).
   A positive result is a budget-scoped claim (~30 events/run) until tested longer.
6. **Embedding-geometry specificity.** The signal exists in MiniLM space only (TF-IDF null).
   Deployment reuses the exact geometry (§0), so this threatens external validity (other tasks,
   other embedders), not internal validity here. Scope guard on claims.
7. **Mechanical identity of the signal.** HoVer feedback is a rigid template over
   missed/retrieved titles; the scorer is effectively smooth failure-composition novelty. Do
   not describe any win as "prose-content novelty".
8. **Budget-accounting error.** If the 6 parent evals were not counted (or counted differently) the
   arms are silently unmatched — the single most damaging implementation bug available. §6a's
   code-reading plus §13's three-arm mocked count-audit exist for this; both channels must agree.
9. **Contemporaneity/API drift.** gpt-4.1-mini is not frozen. Mixed-arm waves in one window
   mitigate; Stage-1-reuse for arm B was rejected for this reason.
10. **8-cluster inference.** Bootstrap CIs at n=8 are anti-conservative (standing caveat);
    the exact sign-flip test does not share this problem and is the confirmatory instrument.
11. **Unchosen-eval leakage.** If the 3 unchosen parent evals touch acceptance or Pareto
    state, arms differ in un-designed ways. Verified impossible by code (§6a item 5); re-verified
    in the count-audit.
12. **Selection-pressure degeneracy.** If realized novelty scores are near-constant across the
    6 (nothing to select on), T ≈ C by construction and the experiment measures nothing.
    Monitored: per-event novelty spread and T-vs-C choice overlap (§8). §11-0 converts this from
    monitor-only into a **pre-spend estimate**. A (null,null) read must check this descriptive
    before concluding "signal doesn't transfer".
13. **Fixability tail.** 51.4% of missed gold titles are retrievable within BM25 k=1000;
    novelty selection may preferentially surface the unfixable tail. Descriptives (§8) plus
    per-event fixability stats (computable from logs) are the diagnostic.
14. **The endogenous archive (R7).** Distinct from §15-5's saturation. The screen measured novelty
    against archives generated by **base-GEPA** dynamics. Under T, every archive entry after event 1
    is *itself a max-novelty selection*, so T's archives are systematically more dispersed in
    embedding space than any archive the screen scored against, and k-NN distances against them are
    **compressed** from event 2 onward. §5's fidelity is real, but it is *function-level* fidelity;
    the input distribution the function sees is new. No design change is possible — this is inherent
    to any deployment of a state-dependent signal. **Consequence for reading a null:** it admits
    "the screened relation does not survive its own deployment shift", which is distinct from "the
    screened relation was spurious". Do not collapse them.
15. **Coverage weighting replaces prevalence weighting (R8).** This is the actual bet of the
    experiment, stated plainly. Base GEPA re-reflects on failure modes **in proportion to their
    prevalence**. Novelty selection deprioritizes a class that keeps failing the same way after its
    first reflection — *whether or not the failure was fixed*. That substitution is what is under
    test. It composes with the fixability tail (§15-13): the unfixable tail looks novel, while the
    fixable core may be archive-redundant. **Diagnostic:** the §8 coverage-starvation descriptive
    (per-event count of chosen examples whose missed-title set already appears in the archive, T vs C).
16. **Shared-RNG divergence between B and T/C (§7a).** Documented, not repaired. H1 is unaffected.

## 16. Scope guards (what this experiment cannot claim, regardless of outcome)

One benchmark (HoVer), one task LM (gpt-4.1-mini), one budget (~300 metric calls, ~1 trainset
pass — the low-budget regime; at the paper's own HoVer budgets, 1.0–1.84 passes, dynamics may
differ), one oversampling factor (M=2b), one embedding geometry, pointwise gate unchanged.
**If the measured dose D (§11-0) is small, M is the obvious v2 lever**, since larger M pushes the
selected min further into the tail at linear eval cost (§4).
"Static per-example selection" remains closed on IFBench and untested as a *sampler* on HoVer
(no Class A signal existed to deploy); this experiment speaks only to the state-dependent
form. Nulls are MDE/CI-bounded, never proof of zero. The static-vs-state-dependent distinction
is preserved in all external text.

## 17. Ratified decisions (were §17 open decisions; ratified 2026-07-09)

- **A. M = 6.** **Ratified**, with the R5 wording fix (§4). M is the v2 lever if D is small (§16).
- **B. Archive membership = chosen-3 only.** **Ratified**, conditional on V1 — and **V1 confirmed
  it** (`notes/FREEZE.md` Task 4: reflected-3-only, not a V1-flip). The fidelity claim to the screen
  stands.
- **C. Budget = 300 metric calls.** **Ratified.** This pins the low-budget scope (§16).
- **D. Fresh arm B, not Stage-1 reuse.** **Ratified**; the ~$17 is cheap insurance, and V3 makes
  fresh B pull extra weight as the counter-parity check.
- **E. Seeds = Stage 1's 8.** **Ratified**, with the R11 gate criterion defined before the numbers
  exist (§11-2), because on R2's ceiling argument the gate is more likely than not to bite.
- **F. Primary endpoint = final-candidate test score.** **Ratified**, with the R13 edge cases
  written in (§8).

## 18. Deliverables

Frozen design (this doc, tagged) → $0 acceptance gates (§13-2) → CC implementation + three-arm
mocked count-audit → `APPROVED-testsplit` → test split + Stage-1 backfill → `APPROVED-dose` → dose
control + dose → `plan.md` (smoke × 24 + MDE) → `APPROVED-liverun` (Neel) → live smoke → 24 runs in
mixed waves → manifest + commit + pre-analysis tag → `results.md` (numbers only) → read against §9 →
interpretation + second-path recompute → ledger entry in `analysis/findings_summary.md` → external
text only after all of the above.

## 19. Review coverage table

| Item | Landing site |
|---|---|
| R1 (map not a partition) | §9, replaced entirely |
| R2 (dose; unit crossing) | §11-0, §11-1, §11-2 |
| R3 (exhaustion, resume) | §6b, §6c |
| R4 (§2 self-containment) | §2 (splits, accept rate), §2a (specificity, transfer) |
| R5 (subset argmax = sort) | §4 (rationale), §5 (implement as sort), §11-0 (gap def) |
| R6 (specificity ≠ quality; Goodhart) | §11-1, §15-1 |
| R7 (endogenous archive) | §15-14 |
| R8 (coverage vs prevalence weighting) | §15-15, §8 descriptive |
| R9 (accept-rate → budget, endpoint) | §15-4, §8 (candidate count), §3 (H1 as policy contrast) |
| R10 (three-arm smoke; smoke disposition) | §13-4, §13-5 |
| R11 (gate criterion; MDE DGP) | §11-2 |
| R12 (√2 conditional; B-arm SD) | §11-3 |
| R13 (endpoint edge cases) | §8 (a,b,c) |
| R14 (sign-flip exactness is H1-only) | §10 |
| R15 (seed floor) | §10 |
| M1 (broken cell-6 markdown) | §9, replaced |
| M2 (BCa unstable at n=8) | §10 |
| M3 (T/C share event-1 substream) | §5 cold start |
| M4 (two post-run test evals; \|test\| auditable) | §14, §8a |
| V1 (screen archive semantics) | §5, confirmed — **not a flip** |
| V2 (swap feedback persistence) | §11-0, **premise false**; re-derivation + control |
| V3 (counter parity across arms) | §6a item 6, §13-3 (one engine wiring) |
| V4 (epoch-boundary semantics) | §7a |
| V5 (endpoint tie-break) | §8 |
| V6 (second-path sufficiency) | §12 |

## 20. Open decisions — MUST be resolved before `APPROVED-liverun`

CC flagged these rather than improvising them. Neither is specified by v1, the review, or the
overnight brief.

1. **`skip_perfect_score` asymmetry.** `reflective_mutation.py:204` skips the event when
   `all(s >= perfect_score for s in eval_curr.scores)`. That is **6 scores in T/C and 3 in B**, so
   the arms skip at different rates, and a skip in T/C burns 6 counted parent evals against B's 3
   (the gate sits *after* the counter increment at `:164`). Options: (i) gate on the **chosen 3**
   post-selection — matches B's semantics, but changes gepa's ordering; (ii) gate on all 6 — keeps
   gepa's ordering, but unmatches the arms. This is a real asymmetry in the design's most fragile
   joint (§15-8) and must be pre-registered, not discovered in the audit.
2. **Dose event set.** §11-0 excludes ordinal-0 events (8 of 243, no k=3 archive), giving 705
   re-derivation calls; the brief's cost line assumed 729 (all 243). Pick one. Cost difference is
   ~$0.11; the pre-registration difference is that the dose is either defined on 235 events or on
   243 with 8 undefined.
3. *(Lower stakes, recorded in §8a.)* Whether the test split is a uniform sample of imperfect claims
   (harder than train: ~14.6% vs ~4.5% at recall 0) or is recall-stratified to match train's mix.
