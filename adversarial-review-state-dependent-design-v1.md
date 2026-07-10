# Adversarial Review: State-Dependent Novelty Selection, Design v1

*Reviewer: Claude (external, no repo access; working only from the design doc). Date: 2026-07-09.
Document under review: `state-dependent-design-v1.md` (pre-freeze draft). Requested attack
surface: §6 budget accounting, §5 selection-rule fidelity, §8 endpoint, §9 map exhaustiveness,
§10-11 inference at n=8, §15 completeness. All are covered; a coverage index is at the end.*

---

## Verdict

The skeleton is sound. The three-arm isolation logic is correct and well argued, fixed-total-budget
is the honest accounting and the doc pre-empts the flattering alternative, and the freeze /
smoke / APPROVED / numbers-only / second-path chain is the right process shape. Nothing here
requires design surgery or new data.

Freeze is blocked on four items, all fixable in the document itself: the interpretation map is
neither exhaustive nor mutually exclusive and is keyed to the wrong inferential instrument
(R1); the planning effect has no dose term, and the §11-2 gate comparison is dimensionally
incoherent as written (R2); budget-exhaustion and crash-resume accounting semantics are
unspecified, which is a pre-registration hole inside the design's self-declared most fragile
joint (R3); and §2 fails its own self-containment standard on the two definitions the whole
deployment logic hinges on (R4).

One structural simplification should go into the same edit pass: the argmax-over-20-subsets
selector reduces exactly to "take the top 3 items by novelty," which changes nothing about
correctness but falsifies the stated M=6 rationale and simplifies both implementation and the
dose computation (R5).

Separately, one repo fact I cannot check from here conditions the §17-B ratification: whether
the screen's archive was actually built from reflected-only feedbacks (V1). If it was not, the
"fidelity to the screened object" argument flips the §17-B default.

### Issue index

| ID | Gate | One-line |
|---|---|---|
| R1 | Blocks freeze | §9 map: missing cell, double-covered cell, undefined anomaly trigger, CI-vs-test inconsistency |
| R2 | Blocks freeze (register) / blocks APPROVED (compute) | Planning effect has no dose term; $0 retrospective dose estimate from the swap corpus; gate comparison crosses units |
| R3 | Blocks freeze | Budget exhaustion mid-event and crash-resume call accounting unspecified |
| R4 | Blocks freeze | §2 self-containment fails: specificity and transfer undefined, split sizes and Stage 1 accept rate missing |
| R5 | Freeze edit pass | Max-min subset selection is exactly top-3-by-novelty; fix the M=6 rationale |
| R6 | Freeze edit pass | DV mismatch: the screened outcome is specificity, not quality; transfer link unresolved; sign of trajectory effect not established |
| R7 | Freeze edit pass | Endogenous archive shifts the estimand relative to the screen (distinct from saturation) |
| R8 | Freeze edit pass | Prevalence-vs-coverage reweighting: persistent-failure starvation is a live cell-5 mechanism; add a descriptive |
| R9 | Freeze edit pass | Accept-rate divergence changes candidate counts and budget composition; endpoint selection-noise differs by arm |
| R10 | Blocks APPROVED | Smoke covers only arm T; counting asymmetry across arms is undetectable by a T-only smoke; smoke-run disposition unspecified |
| R11 | Freeze edit pass / blocks APPROVED | Gate criterion "grossly exceeds" undefined; MDE simulation DGP underspecified |
| R12 | Freeze edit pass | The √2 bound assumes nonnegative cross-arm correlation; Stage 1 SD is B-arm-like |
| R13 | Freeze edit pass | Endpoint edge cases: zero-accept runs, val-aggregate ties, midpoint endpoint should be computed post hoc |
| R14 | Freeze edit pass | Sign-flip exactness holds for H1 exchangeability, not for H2; one-sentence scoping |
| R15 | Freeze edit pass | Pre-register the seed floor: below 6 usable pairs the confirmatory test is arithmetically dead |
| V1-V6 | Blocks APPROVED | Repo verification items for CC, folded with §6's existing five |
| M1-M4 | Minor | Formatting and small statistical hygiene |

---

## Blocking issues

### R1. The interpretation map is not a partition, and it is keyed to the wrong instrument (§9)

§9 instructs that results are read against this map and nothing else. That instruction is only
safe if the map is exhaustive, mutually exclusive, and internally consistent with §10. It is
none of the three.

**Exhaustiveness.** Enumerate the 3×3 grid over (ΔTC, ΔTB): (+,+) is cell 1; (+, null) and
(+, −) are cell 2; (null, null) is cell 3; (null, −) is cell 4; (−, +), (−, null), (−, −) are
cell 5. The cell **(null, +) has no entry**. It is not exotic: T beats base at full CI
separation while the T−C contrast straddles, meaning the packaged intervention works but
selection per se is undetected against the matched control. Cell 6 only catches this if C−B
separates "clearly"; if C−B straddles (entirely plausible when T sits between), no cell fires
and the map's own reading rule leaves you with nothing to read.

**Exclusivity.** (−, −) is covered by both cell 4 ("selection at M=2b is dead") and cell 5
("genuine harm finding, report at full strength"), which prescribe different actions. Cell 2's
(+, −) branch can additionally co-fire with cell 6 depending on how C−B lands. Two cells
firing with divergent actions is exactly the post-hoc discretion the map exists to remove.

**Instrument inconsistency.** The map defines positive/null/negative by CI exclusion. §15-10
states that the bootstrap CIs at n=8 are anti-conservative and that the exact sign-flip test
is the confirmatory instrument. These can disagree, and with anti-conservative CIs the
disagreement is biased in one direction: CI excludes zero, sign-flip p > 0.05. As written, the
map would then read "positive" off the instrument the design itself distrusts.

**Fix.** (a) Define the sign categories by the confirmatory instrument: positive means
two-sided sign-flip p < 0.05 with positive mean difference (H1 machinery for ΔTC, the
identical secondary machinery for ΔTB); CIs carry magnitude and the underpowered-null label
only. (b) Write the full 3×3 grid; assign (null, +) its own cell (suggested reading: deployment
gain without detected selection mechanism; action: treat the mechanism claim as unproven,
check the H3 descriptive and the overlap/selection-pressure descriptives before any external
framing). (c) Resolve (−, −) to cell 5 alone; the harm reading is the stronger and more
diagnostic claim, and cell 4's action is subsumed by it. (d) Convert cell 6 into an explicit
anomaly overlay with precedence: evaluate C−B first by the same sign-flip criterion; if it is
positive, enter the anomaly protocol before reading the grid at all. Define "clearly" as that
criterion, nothing looser.

### R2. The planning effect has no dose term, the dose is computable for $0 right now, and the §11-2 gate comparison crosses units (§11, §5)

§11-1 sets the planning effect at half the screened β, i.e. ~0.019 per SD of batch
min-novelty. That number is dimensionally incomplete for planning: β is an effect **per SD of
the selected statistic**, and the intervention delivers some number of SDs, call it D, the
realized uplift in min-novelty from taking the top 3 of 6 draws versus a random 3-of-6. The
implied one-step effect is D × β/2, not β/2. Nothing in the document estimates D.

D is estimable retrospectively for $0, and the corpus for it already exists. The swap
machinery evaluated the parent on 6 candidates per event across 243 events, and the standing
persistence rules should mean all 6 feedback texts per event are on disk. For each event:
score all 6 against that run's archive at that event using the screen's exact code path, take
the gap between the 3rd-largest novelty (the deployed selector's min, per R5) and the expected
min of a uniformly random 3-subset, and express the average gap in units of the screen's
between-batch min-novelty SD. The same computation yields, for free, the expected T-vs-C
choice overlap and the per-event novelty spread, which converts §15-12's degeneracy threat
from monitor-only into a pre-spend estimate.

A ceiling argument says this matters. Under iid scores the top-3-of-6 min sits around one SD
above a random 3-subset min, and within-event novelty scores share an archive and are
positively correlated, so D is realistically well under 1 SD. Even at the frictionless ceiling
of D = 1, the implied one-step effect is ~0.019, roughly the swap experiment's own MDE, before
any one-step-to-trajectory attenuation. If the measured D comes back at 0.5 to 0.8 SD, the
implied one-step effect is ~0.010 to 0.015 and the §11-2 gate is very likely to bite. Better
to know that before CC writes a line of code.

Separately, §11-2's gate read is dimensionally incoherent as written: it compares an MDE in
final-test-score units against a planning effect in one-step swap-specificity units. §11 opens
by correctly refusing to translate between these and then §11-2 quietly performs the
comparison anyway. The honest gate read is: report the MDE in endpoint units; report D × β/2
as the implied one-step effect in specificity units; state that no amplification mechanism is
hypothesized, so trajectory effects of comparable or smaller magnitude are the plausible
range; and let the pre-defined gate criterion (R11) operate on that explicitly caveated
juxtaposition rather than on a silent unit crossing.

**Fix.** Add a §11-0 pre-registering the dose computation (inputs, code path, output
statistics) in the frozen doc; execution lands pre-APPROVED alongside the MDE, and both
numbers plus the overlap descriptor go in plan.md. Rewrite the §11-2 gate sentence per the
above. Conditional: if the swap corpus did not persist all 6 feedback texts per event, CC
reports that (V2) and the dose falls back to the reflected-3-plus-swapped-3 texts per event,
which still supports the order-statistic computation.

### R3. Budget exhaustion and crash-resume accounting are unspecified (§6, §13)

The design's stated most fragile joint is budget matching, and §6's verification items police
the counting of individual calls. Two accounting semantics that determine comparability are
nonetheless unspecified, which means CC will improvise them, which is a pre-registration hole:

**Mid-event exhaustion.** Arms hit the 300-call ceiling at different phase offsets: B's events
cost 6 minibatch calls plus accept-triggered valset evals, T and C cost 9 plus valset evals.
Whether an event may start with fewer remaining calls than its worst case, whether a partially
evaluated event's accept can still fire, whether the counter may overshoot, and at what
counter state the endpoint's "budget exhaustion" is read: all of these change realized events
and the endpoint's timing, differentially by arm. Pre-register one rule. Suggested: an event
may begin only if remaining budget covers its minibatch cost (6 or 9 by arm); valset evals
triggered by an accept always complete and may overshoot the counter; endpoint is read at the
first counter state ≥ 300 after event completion. Any rule is fine; an unwritten rule is not.

**Resume semantics.** §10 declares a crashed-and-cleanly-resumed run valid, but "cleanly" is
undefined. Define it: event-level atomic checkpointing; resume restores budget counter,
archive contents, candidate pool, Pareto state, and all RNG streams exactly; a partially
completed event at crash time is rolled back and replayed. Then pre-register the accounting
for the rolled-back calls: they were burned against the real API but replaying them re-draws
LLM randomness. Recommended: rolled-back calls do not increment the counter (the counter
tracks the optimization the analysis sees, not the wallet), and every rollback event is logged
in the manifest with its burned-call count. The opposite convention is defensible too; pick
one before the smoke, because threat 8 (silently unmatched arms) has a second entry point
here beyond per-call counting.

### R4. §2 fails its own self-containment standard on the load-bearing definitions (§2, §6, §14)

§2 promises a cold reviewer needs nothing else. Four omissions break that, and two of them
sit directly under the deployment logic:

1. **Specificity is never defined.** The prior chain's positive result, the screen's dependent
variable, and therefore the entire justification for deploying novelty selection all rest on
"per-event swap specificity," which appears only as a number. A cold reviewer must be told the
operational definition: what is compared to what (own-batch child versus swapped-batch child,
presumably), and crucially **evaluated on what** (the batch itself, a held-out slice, the
valset). The answer determines how much of R6's DV-mismatch critique bites and cannot be left
implicit in a frozen pre-registration.
2. **Transfer is never defined** either, and it is the unresolved link the whole deployment
inference chains through (R6).
3. **|D_pareto| and |test| are unstated.** Without them the §6 arithmetic (why Stage 1 fits
27-34 events in 300 calls) and the §14 projections cannot be audited from the document, and
the mid-event exhaustion rule in R3 cannot even be sanity-checked for how often it triggers.
4. **Stage 1's accept rate is unstated.** It is the baseline for the gate-coupling
discriminator (§15-4) and for interpreting the realized events-per-run ratio (§6 item 3).

All four are one-line additions. Add them at freeze.

---

## Fix in the freeze edit pass

### R5. The subset argmax is exactly top-3-by-novelty; the M=6 rationale is misstated (§4, §5)

Each member's novelty is computed against the archive only; there is no within-batch term
(explicitly out of scope, §5). The subset objective min over members of fixed per-item scores
is therefore maximized by the 3 highest-novelty items, always: the min of the top 3 dominates
the min of every other 3-subset. The C(6,3) = 20 enumeration is a sort in disguise.

Consequences. (a) Implement it as a sort; fewer lines, fewer bugs, identical output. The
tie-break cascade only activates on exact score ties at the 3rd/4th boundary, which the
identical-feedback-string case makes genuinely possible; keep it. (b) The §4 rationale "2b is
the smallest oversampling that gives the subset-selector nontrivial room (20 subsets)" is
false as stated; the selection room is order-statistic room, top 3 of 6 draws, and the correct
framing of larger M is that it pushes the selected min further into the tail. Fix the wording
so the frozen doc doesn't contain a false rationale. (c) The dose computation in R2 becomes a
one-liner: gap between the 4th order statistic (ascending) of 6 and the expected min of a
random 3-subset.

### R6. The screened outcome is specificity, not quality, and the transfer link is unresolved; say so where it counts (§11-1, §15-1)

Pending R4's definition, swap specificity measures how much the reflection product depends on
batch identity, with the positive sign indicating own-batch advantage, plausibly evaluated
locally. The screen therefore established: novel batches are where batch identity matters
most. It did not establish: novel batches produce better prompts. The link from
batch-specific reflection content to generalizable improvement is the transfer estimate, which
is explicitly unresolved (+0.0169, CI straddling zero, below its MDE). The deployment
inference chains novelty → specificity (established, one-step, local) → generalizable gain
(unresolved) → trajectory outcome (untested), and the second link's sign is not pinned by the
prior chain.

This has two consequences the current text understates. First, §11-1's "treat the trajectory
effect as unknown but plausibly smaller still" should read "unknown in sign as well as
magnitude"; a cell-5 outcome is not a tail risk, it is a live branch of the existing evidence
(local specificity could be local overfitting that the pointwise gate then rewards). Second,
this experiment is a Goodhart test of an observationally screened correlate: selecting on the
feature is a distribution shift under which the screened relation need not persist, LORO and
residualization notwithstanding. That is exactly what a live test is for, so no design change
follows; but §15-1 should own the framing so a cell-3 or cell-5 result reads as the design
anticipating the outcome rather than being ambushed by it.

### R7. The endogenous archive shifts the estimand relative to the screen (add to §15)

Distinct from §15-5's within-run saturation. The screen measured novelty against archives
generated by base-GEPA dynamics. Under T, every archive entry after event 1 is itself a
max-novelty selection, so T's archives are systematically more dispersed in embedding space
than any archive the screen scored against, and k-NN distances against them are compressed
relative to the screened distribution from the second event onward. §5's code-path fidelity
is real but is function-level fidelity; the input distribution the function sees is new. No
design change is possible, this is inherent to any deployment of a state-dependent signal;
add it as a scope caveat so that a null is not over-read as "the screened relation was
spurious" when "the screened relation does not survive its own deployment shift" is the
available reading.

### R8. Novelty selection replaces prevalence weighting with coverage weighting; persistent-failure starvation is a live cell-5 mechanism (add to §15, §8)

HoVer feedback is a rigid template over missed/retrieved title sets, so recurring failure
signatures produce near-identical strings with novelty ~0 against the archive once seen. Under
T, an example class that keeps failing the same way is deprioritized after its first
reflection **whether or not the failure was fixed**. Base GEPA re-reflects on failure modes in
proportion to their prevalence in the stream, which is at least a crude proxy for expected
marginal gain; T substitutes coverage of the failure-mode space for prevalence. That
substitution is the actual bet of the experiment and deserves to be named as such.

It also composes badly with §15-13: the unfixable tail is novel-looking (rare weird failures)
while the fixable core may be common and therefore archive-redundant. Add one monitored
descriptive to §8, computable from the §12 logs: per event, the count of chosen examples whose
feedback string (or missed-title set) already appears in the archive, T versus C. A cell-5 or
cell-3 read should consult it alongside accept rate and fixability.

### R9. Accept-rate divergence changes budget composition and endpoint noise; extend §15-4

Two downstream consequences of gate coupling are worth writing down now. First, budget
composition: a lower accept rate in T means fewer valset evals, which at fixed total budget
means **more** reflection events, partially self-compensating in event count while starving
the candidate pool. The realized events-per-run monitor (§6 item 3) will show it; the
interpretation note belongs in §15-4. Second, endpoint machinery: the primary endpoint is the
test score of the val-argmax, and the argmax is taken over however many candidates got full
valset evals. Arms with more candidates take a max over more draws, which changes the
selection-noise properties of the endpoint (higher expected val max, regression-to-the-mean
penalty on its test score). For H2 this is baked into "deployment honest." For H1 it only
arises through accept-rate divergence, i.e. it is downstream of the intervention and not a
confound, but it does mean H1 as stated ("holding eval cost and pick-3-of-6 mechanics fixed")
is a policy contrast, not a mechanism contrast; the mechanism attribution (better reflections)
must lean on the monitored descriptives. One added line in §15-4 plus candidate-count-per-arm
in the §8 monitored list covers it.

### R11. Define the gate criterion and the MDE simulation DGP now (§11-2)

"If MDE grossly exceeds any plausible effect" is a decision criterion that will be applied by
a motivated party (all of us are) with the numbers already in hand. Define it at freeze, e.g.:
if MDE > k × (D × β/2) for pre-chosen k (suggest k = 3), the default flips to
estimation-only framing or a seed increase, with the choice between those two, but not the
trigger, left to the gate. Per R2, state explicitly that this comparison juxtaposes endpoint
units against one-step specificity units and is a heuristic screen, not a power calculation.

The MDE simulation also needs its DGP pinned: per synthetic replicate, draw 8 paired
differences as X_T − X_C with both margins drawn independently from the Stage 1 empirical
endpoint distribution (independence encodes ρ = 0, consistent with the √2 bound), shift by the
candidate effect, apply the two-sided exact sign-flip at α = 0.05, and define MDE as the
smallest shift reaching 80% rejection. Commit the script and cite its hash in plan.md.
Left unpinned, the MDE is a garden of forking paths sitting exactly where §11 exists to
prevent one.

### R12. The √2 bound is conditional, and Stage 1's SD is a B-arm quantity (§11-2, §7)

"Pairing can only help" is not strictly true: SD(diff) = √(σ_T² + σ_C² − 2ρ σ_T σ_C) exceeds
√2·σ when ρ < 0. Shared seed components (data order, init prompt) make ρ ≥ 0 the sensible
prior, so keep the bound, but state the assumption, and note the likely reality that the
proposer lottery drives ρ toward 0 and the bound toward tight, i.e. pairing buys little here.
Report the realized cross-arm correlation in the analysis. Second caveat: the Stage 1 SD is an
estimate from B-like runs; T and C complete fewer events and plausibly have higher endpoint
variance, so the MDE inherits an unquantified optimism. One sentence each.

### R13. Endpoint edge cases (§8)

Three small pre-registrations: (a) **Zero-accept runs.** At this budget a run can end with the
seed candidate as the only valset-evaluated candidate; the endpoint is then the seed prompt's
test score. Valid, but say so. (b) **Val-aggregate ties** between candidates at exhaustion:
pre-register the tie-break (suggest: earliest accepted candidate, matching GEPA's convention
if it has one; CC confirms, V5). (c) **Midpoint secondary endpoint**: compute it post hoc,
identify the midpoint val-argmax from logs after the run and evaluate it on test in the same
post-run pass as the primary endpoint's test eval. This keeps mid-flight processes free of
test-set contact, protects the no-interim rule from even the appearance of a peek, and puts
both extra test evals visibly into the §14 cost line.

### R14. Sign-flip exactness is an H1 property, not an H2 property (§10)

The exact sign-flip test is exact under within-pair exchangeability. For T versus C that holds
under the sharp null "the selection rule does nothing": the arms are then mechanically
identical processes differing only in independent RNG streams. For T versus B the arms differ
in mechanics regardless of any null, the relevant sharp null is package-level, and
exchangeability is an approximation. H2 is already labeled secondary; add the one sentence so
the labeling has its reason attached.

### R15. Pre-register the seed floor (§10)

The dropped-seed rule can shrink n. Minimum two-sided sign-flip p is 2/2^n: n = 8 gives
0.0078, n = 7 gives 0.0156, n = 6 gives 0.0313, n = 5 gives 0.0625 and the confirmatory test
can no longer reach α = 0.05 at all. Pre-register: with fewer than 6 usable pairs the
confirmatory test is void and the experiment reports as estimation-only.

---

## Repo verification items (CC, pre-APPROVED; additions to §6's five)

**V1. Screen archive semantics (conditions §17-B).** Confirm from the screen's feature code
that the archive against which `knn_emb_fb_min` was computed contained the feedback texts of
**reflected examples only** at prior events. This is nontrivial precisely because the swap
machinery evaluated 6 candidates per event, and swap events may have reflected on both an
original and a swapped batch; whatever the screen actually archived is the object the
deployment must reproduce. If the screen archived something other than chosen-3-only, the
§17-B default flips or the fidelity claim gets rewritten, before freeze if at all possible.

**V2. Swap-corpus feedback persistence for the dose estimate (R2).** Confirm all 6 per-event
feedback texts exist on disk for the 243 events; report which fallback applies if not.

**V3. Counter parity across arms.** §6 items 1-2 verify counting inside the draw-6 path. Add:
verify B's counting on the current code (the code has moved since Stage 1, which is the doc's
own argument for fresh B runs), and verify the initial seed-candidate valset eval increments
identically in all three arms. See R10 for the smoke mechanics of this.

**V4. Epoch-boundary semantics.** T/C consume 6 IDs per event and cross the 100-example epoch
boundary earlier than B; confirm the reshuffle at the boundary is seed-deterministic and
identical in code path across arms.

**V5. Endpoint tie-break convention** in the installed gepa version (R13-b).

**V6. Second-path sufficiency.** Confirm the §12 persistence set suffices to recompute, from
raw artifacts alone, all 6 novelty scores per event (feedback bytes, archive membership at
scoring time, embedding model file hash) and the endpoint chain (per-draw score vectors →
val-argmax → test score). §12 as written appears sufficient; verify rather than assume.

---

## Blocks APPROVED (ops)

### R10. A T-only smoke cannot detect the most damaging bug class, and the smoke run's disposition is unspecified (§13)

Threat 8 names asymmetric budget counting as the single most damaging implementation bug. A
smoke of arm T alone exercises the draw-6 counting path but provides zero evidence about
cross-arm parity: if B's path counts differently on the moved code, a T-only smoke passes and
the arms launch silently unmatched. Add micro-smokes of B and C, either at a tiny
`max_metric_calls` or in a count-audit mode with a mocked task LM, with the acceptance
criterion that all three arms' counters agree with the §6 code-reading on every call category.
Cost is trivial next to the $50-70 envelope; it directly closes the design's own top threat.

Separately: state what happens to the smoke run's data. It is a full arm-T seed-0 run that
will be poked at for audits and possibly invalidated by an amend-refreeze cycle. Cleanest
rule, worth its own line in §13: the smoke run is excluded from analysis unconditionally, and
seed 0 arm T is rerun inside the mixed waves like every other cell.

---

## Minor

**M1.** The §9 table's cell-6 row is structurally broken markdown (the condition spans the
ΔTC/ΔTB columns); the R1 restructure fixes it incidentally.

**M2.** BCa at n = 8 is unstable (the acceleration constant comes from a jackknife over 8
points); report the percentile interval alongside. The anti-conservative caveat already
attaches to both.

**M3.** Cosmetic determinism: at event 1, T's cold-start random pick could reuse the same
derived RNG substream as C's picker so that T and C choose identically at event 1 given the
same seed. No inferential consequence (pairing is at seed level); it marginally tightens the
pairing and costs nothing.

**M4.** §14 should carry the two extra post-run test evals per run (primary endpoint plus
midpoint candidate, R13-c) in the projection line, and the projection wants |test| to be
auditable (R4-3).

---

## What holds

For calibration, the things this review tried to break and could not: the C-arm construction
genuinely isolates the selection rule ex ante, and the doc correctly identifies T−C as the
only confirmatory contrast; fixed-total-budget is the right accounting and the doc pre-rejects
the alternative that would flatter the treatment; the archive-membership default (chosen-3) is
the right fidelity call conditional on V1; the edge-case list in §5 is complete and
deterministic; §12's persistence set is unusually thorough; the no-interim, numbers-only,
map-first, second-path discipline is exactly the shape that made the previous null results
credible. The threats list already contains the two most likely non-positive outcomes (gate
coupling, selection-pressure degeneracy); this review's additions (R6-R9) extend rather than
correct it.

## §17 ratification opinions

**A (M = 6): ratify**, with the R5 wording fix, and note in §16 that if the measured dose D is
small, M is the obvious v2 lever since larger M pushes the selected min further into the tail
at linear cost. **B (chosen-3 archive): ratify conditional on V1.** **C (300 calls): ratify.**
**D (fresh B): ratify**; the $17 is cheap insurance and V3 makes fresh B pull extra weight as
the counter-parity check. **E (8 seeds): ratify**, with the R11 gate criterion defined before
the numbers exist, because on the R2 ceiling argument the gate is more likely than not to
bite. **F (final-candidate test score): ratify**, with the R13 edge cases written in.

## Coverage index against the requested attack surface

Budget accounting (§6): R3, R10, V3, V4. Selection-rule fidelity (§5): R5, R7, V1, V6.
Endpoint (§8): R9, R13, V5. Map exhaustiveness (§9): R1, M1. Inference at n = 8 (§10-11): R2,
R11, R12, R14, R15, M2. Threats completeness (§15): R6, R7, R8, R9.
