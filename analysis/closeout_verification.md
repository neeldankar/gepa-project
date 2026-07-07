# Closeout verification — two review holes patched before the external update

**Date:** 2026-07-02 · **$0, read-only** (frozen IFBench baseline 2026-06-26 + HoVer necrosis capture
2026-07-01 untouched). Script: `scripts/run_closeout_verification.py`. Addresses two holes a second
review found in the closing argument: **H1** (R²=0.087 is a lower bound on what features capture, not an
upper bound on predictability) and **H2** (C3's "fix the reasoning" line may be scoped to the wrong module).

## Step 1 — routing fact: gen_query IS in the optimized surface Φ
Code fact (from `necrosis/gepa_result.json` `program_candidates`, 11 candidates): **gen_query.predict has
6 distinct instructions across candidates** (append_notes 6 too); candidate 3 first rewrites the trivial
seed `"Given the fields claim, notes, produce the fields query."` into a full `"Task Description: …"`
instruction. GEPA optimizes **both** predictors. **→ H2 is LIVE:** the module that writes the retrieval
queries is inside Φ, so "retrieval-only" failures are structurally prompt-addressable. Steps 3 & 4 run.

## Step 2 — OUTCOME ICC (the new closing statistic, replacing R²=0.087)
Same machinery as Check 1, applied to the TARGET: each b3 batch's outcome attributed to its 3 example
slots (via `minibatch_ids`), grouped by trainset id (1146 slots / 150 examples), ICC(1) + bootstrap CI.

| outcome | ICC(1) | 95% CI (bootstrap over 150 examples) | reading |
|---|---|---|---|
| ΔU (rejected→0) | **−0.003** | [−0.034, +0.032] | between-example ≈ 0 |
| LOO-unique-contribution | **+0.024** | [−0.017, +0.061] | between-example ≈ 0 |
| HoVer (33 ev / 12 claims, THIN) | ΔU −0.092 · mbi +0.029 | — | ≈ 0 (thin) |

**The outcome has no stable per-example component.** "Which example was reflected on" carries essentially
no information about revision quality — the CIs straddle zero for both targets. This is the upper-bound
statistic H1 asked for, and it is **stronger** than R²=0.087: it's not that a 20-feature linear model was
weak; it's that **the per-example target does not exist**. That single number kills the learned per-example
scorer, LOSO, edit-attribution, and rollout-observed selection at once — they all assume a stable
per-example target. **Verdict on the per-example selection axis: CLOSED WITH PREJUDICE.**

## Step 2b — C2 refinements (and a correction to the "90% unpredictable" framing)
Hurdle split (the pooled R²=0.087 was mechanically capped by the reject zero-mass):

| part | statistic | n |
|---|---|---|
| (i) P(accept) ~ 20 controls | **AUC = 0.706** | 382 |
| (ii) ΔU \| accept ~ 20 controls | **R² = 0.50** (adj ≈ 0.39; 20 feats/115 pts — inflated, report as directional) | 115 |

**This corrects an overclaim:** the outcome is **not** ~90% unpredictable. Acceptance is moderately
predictable (AUC 0.71) and ΔU-given-accept is substantially predictable (R² ~0.4–0.5) — but **from batch
difficulty / constraint-identity, not from a per-example content lever.** Top-decile LOO enrichment
confirms this: top-decile batches enrich `constraint_tractability_mean` (+0.124) and `difficulty` (+0.050),
while the **content scorers do NOT enrich** (`actionability_b` −0.104, `failure_mode` −0.005, `knn_novelty_b`
+0.025). So the honest closing statement is: the outcome IS predictable — from difficulty/constraint-id
(which the Wave-1 null already showed content scorers can't beat) — while the **per-example content angle is
dead (ICC ≈ 0, no top-decile enrichment).** No nonlinear escape hatch for a content scorer.

## Step 3 — HoVer candidate diff + recall trajectory (H2 empirical test)
- **Accepted edits DO touch gen_query: 5/10** accepted candidates changed the gen_query instruction (full
  rewrites — verbatim hunks below). So GEPA does edit the query surface in practice.
- **But retrieval does NOT improve.** Per-candidate valset recall trajectory (cand0→): `[0.433, 0.40,
  0.467, 0.433, 0.367, 0.367, 0.433, 0.40, 0.40, 0.367, 0.433]` — seed 0.433, **best 0.467 (cand 2), then
  it declines to 0.367.** Net movement ≈ +0.03 at best, mostly flat-to-down.

```
ACCEPTED gen_query edit  cand0 -> cand3
  parent: "Given the fields `claim`, `notes`, produce the fields `query`."
  child : "Task Description:\nYou are given two input fields: `claim` and `notes`. Your objective is to
           generate a `query` field. The query should encapsulate the key factual questions that arise …"
ACCEPTED gen_query edit  cand2 -> cand5
  child : "Task Description:\nYou are given two fields as input: `claim` (a factual statement to be
           verified…) and `notes` (a list of fact-supporting or fact-correcting statements…)."
```

**GATE reading:** gen_query IS optimized and IS edited, so C3's ceiling is **not structurally airtight** —
but in this run those edits **did not fix retrieval** (recall flat/declining). **C3's ceiling survives as
an EMPIRICAL matter (n=1 run, 33 events — thin), not a structural one.** Stated at exactly that strength.

## Step 4 — retrieval-fixability prevalence (H2's named candidate scorer)
Signature per event: a gold entity NAMED in reasoning/notes/claim, ABSENT from all retrieved titles, AND
ABSENT from the generated query strings ("model knew what to look for; the query didn't say it").
**Prevalence: 4/30 failures = 13%** (n=33 thin). Verbatim matches:
- **ev2 — `Beached Az`** (named in reasoning as the show Boshier developed) — query: *"who co-starred with
  christian van vuuren in the tv series soul mates? was this co-star also the developer or creator of…"* —
  never names Beached Az.
- **ev22 — `Jeremy Brock`** — query: *"who directed the 2011 drama film adapted from a work by rosemary
  sutcliff, and who directed and wrote the film true crim…"* — the director's name never queried.
- **ev25 — `Beached Az`** — same pattern as ev2.

So ~13% of HoVer failures are query-fixable-in-principle (the exact target of the reviewer's proposed
retrieval-fixability scorer) — real but a minority. Prevalence only; no claim it would help U.

## BOTTOM LINE — (b) closed except a named untested scorer
- **Per-example content selection (IFBench + HoVer): CLOSED WITH PREJUDICE.** Outcome ICC ≈ 0 (no
  per-example target); the predictable part of the outcome is difficulty/constraint-id, which content
  scorers can't beat (Wave-1 null); no content scorer enriches the top decile. This is airtight.
- **But two prior claims are corrected, not confirmed:** (1) the "~90% unpredictable" framing was wrong —
  the outcome is ~40–50% predictable from difficulty/id once the hurdle is split; the correct close is
  "no per-example target," not "unpredictable." (2) C3's "retrieval-only = unfixable by any prompt" was
  **mis-scoped** — gen_query is in Φ, so retrieval-only failures are structurally prompt-addressable; the
  ceiling held only *empirically* (GEPA's gen_query edits didn't improve recall in this one thin run).
- **One named untested scorer remains:** the **retrieval-fixability** signature (13% prevalence). It is not
  a content/SI scorer over reflection text — it targets the query↔retrieval gap, a different surface.

**Verdict: (b) — the scorer direction is closed except for the named, untested retrieval-fixability scorer
(measured 13% prevalence on HoVer).** Not (a) airtight (H2 is structurally live + 13% prevalence), not (c)
reopened (per-example content selection is dead by ICC≈0; GEPA's actual query edits didn't fix retrieval).
Only a live run of the retrieval-fixability scorer — on the query surface, not the reflection-text surface —
could move it, and only a paired-seed run would prove it helps.
