# Offline batch — five $0 checks from external review

**Date:** 2026-07-01 · **$0, read-only, no GEPA/LM runs** (frozen corpora untouched: baseline logs
2026-06-26, necrosis 2026-07-01). Script: `scripts/run_offline_batch_checks.py`. Corpora: IFBench
(382 b3 batches / 1146 per-example b3 slots over 150 examples) + HoVer necrosis (33 events / 99 units).
**Multiplicity:** 5 checks (several sub-tests) → marginal results (p~0.05) are *suggestive*, not
confirmed. These are DESIGN gates, not proof any scorer works. HoVer is thin (n=33) — flagged throughout.

## CHECK 1 — ICC (is per-example scoring the right abstraction?)
ICC(1) = between-example / total variance, per scorer.

| scorer | IFBench ICC(1) (150 ex, 1146 obs) | HoVer ICC(1) (12 claims, thin) |
|---|---|---|
| knn_novelty_b | **0.922** | 0.598 |
| ncd_novelty_b | **0.874** | — |
| actionability_b | **0.892** | 0.751 |
| nov_x_act_b | **0.727** | — |
| failure_mode | **0.769** | — |
| constraint_tractability | **0.737** | — |

**GATE → static per-example scoring is TYPE-CORRECT.** Every scorer's variance is majority
between-example (ICC 0.73–0.92 on IFBench; full replication, all 150 examples ≥2 obs). The per-example
score IS mostly a property of the example, not the parent/iteration it's scored under. The §0
deliverable is **not** ill-typed as a static score → proceed as designed (no forced move to
overgenerate-and-filter). HoVer directionally agrees but is thin.

## CHECK 2 — control-block R² (which IFBench story is true?)
OLS of the 20 controls (4 difficulty + constraint_tractability_mean + 15 `ct_*` type-composition) on
each outcome, n=382 b3 batches.

| outcome | R² | adj-R² | nonzero-frac | best single control |
|---|---|---|---|---|
| LOO-unique-contribution | 0.087 | 0.037 | 0.20 | constraint_tractability_mean (R²=0.055) |
| ΔU (comparison) | 0.171 | 0.125 | 0.26 | iteration (R²=0.092) |

**GATE → mostly GLOBAL UNPREDICTABILITY, with a constraint-id tilt.** The full 20-control block explains
only ~9% of LOO variance (adj-R² 4%) — **~90% is unexplained by *anything* we can measure**. So the
honest IFBench story is largely "revision outcomes are barely predictable," which **bounds what any
scorer could have achieved** (the well-posedness question, empirically). The residual signal that *does*
exist is constraint-id-flavored (tractability is the single best LOO predictor), so "id absorbs the
content signal" is directionally true but on a small absolute pie. This *contextualizes* the Wave-1 null:
no semantic scorer survived partly because the outcome is near-a-ceiling of unpredictability, not only
because id ate the signal. (ΔU is a bit more predictable — driven by `iteration` — but still ~83% noise.)

## CHECK 3 — addressable ceiling on HoVer (reasoning-visible vs retrieval-only)
Manual classification of the 33 necrosis events (example_pos 0) — **my judgment on the extracted
reasoning + missed gold docs; shown per-event for audit.** (a) reasoning-visible failure / (b)
retrieval-only failure (reasoning sound; missed doc not surfaced, or entity mentioned but its DOC not
retrieved) / (c) no-failure (full recall).

| ev | cls | why (one clause) |
|--|--|--|
| 1 | **a** | accepts the "more southern" implication without ever locating Greek Fire (the missed entity) |
| 2 | b | Soul Mates reasoning sound; missed 'Beached Az' (3rd-hop show) never surfaced |
| 3 | c | full recall 3/3 |
| 4 | b | reasoning states "Gainesville, Florida" correctly; the DOC just wasn't retrieved |
| 5 | b | reasoning discusses Supergrass; doc not retrieved |
| 6 | b | hedgy but sound; missed 'Ishqbaaaz' deep entity not surfaced |
| 7 | b | sound; 'Shengzhou' never mentioned/needed |
| 8 | b | reasoning correct (1997≠1991); 0/3 is a deep retrieval miss, not a reasoning error |
| 9 | b | planning/verification reasoning, no visible error; entities unresolved |
| 10 | **a** | refers to "a composer" without naming Philip Glass though material supports it (missed inference) |
| 11 | b | names Paras Madaan, uncertain; 'Ishqbaaaz' not surfaced |
| 12 | b | sound; missed deep curling-event doc |
| 13 | b | reasoning names Philip Glass correctly; doc not retrieved |
| 14 | b | reasoning catches the Zee-vs-Star error (sound); 'Ishqbaaaz' not surfaced |
| 15 | b | correct reasoning; 'Gainesville, Florida' doc not retrieved |
| 16 | b | planning reasoning; Jeremy Brock/True Crimes unresolved, no visible error |
| 17 | c | full recall 3/3 |
| 18 | b | reasoning correctly distinguishes Mikael Åkerfeldt; the DOC wasn't retrieved (not a reasoning miss) |
| 19 | b | sound; 'Beached Az' not surfaced |
| 20 | c | full recall 3/3 |
| 21 | b | mentions Supergrass; doc not retrieved |
| 22 | b | planning; unresolved, no error |
| 23 | b | correct reasoning; deep retrieval miss |
| 24 | b | sound; 'Toshi (musician)' not surfaced |
| 25 | b | sound; 'Beached Az' not surfaced |
| 26 | b | "no info linking…" sound; Supergrass doc not retrieved |
| 27 | b | sound; 'Ishqbaaaz' not surfaced |
| 28 | b | reasoning sound on Mikael Åkerfeldt; doc not retrieved |
| 29 | b | names Lisa Lopes; 'Tionne Watkins' is another valid TLC writer, not a clear error |
| 30 | b | reasoning resolves Tim Fain→Philip Glass; doc not retrieved |
| 31 | b | notes the "Christiaan" spelling (sound); 'Beached Az' not surfaced |
| 32 | b | correct reasoning (1997≠1991); 0/3 deep retrieval miss |
| 33 | b | ambiguity flagged (sound); 'Beached Az' not surfaced |

**Failures = 30 (events excl. 3/17/20). Reasoning-visible (a) = 2 clear (ev 1, 10); ~2–3 more are
arguable → (a) fraction ≈ 7% (up to ~13% generous).**

**GATE → addressable ceiling is LOW (≪30%).** The overwhelming majority of HoVer failures are
**retrieval-only**: the reasoning is sound (often *correct*, even naming the missed entity), and the gold
doc simply wasn't retrieved — **structurally invisible to any SI-content scorer, including failure_mode.**
So the powered screen would chase a ~10% minority; failure_mode's max achievable effect is capped
accordingly, and any power calc MUST be on the (a)-only subset. (Consistent with the prior HoVer eyeball
"misses are idiosyncratic retrieval, not rule-able," and with the necrosis run's weak/inconclusive
failure_mode.) Caveat: my judgment, n=30 failures, thin.

## CHECK 4 — accept-rate by scorer (collider / imputation-bias story)
Spearman(accept, per-batch mean scorer); accept-rate by tercile.

| scorer | IFBench ρ(accept) | p | terc lo/mid/hi | HoVer ρ (n=33) |
|---|---|---|---|---|
| knn_novelty_b | +0.080 | 0.12 | 0.25/0.31/0.34 | −0.152 (p .40) |
| ncd_novelty_b | +0.001 | 0.99 | 0.31/0.31/0.28 | — |
| actionability_b | +0.032 | 0.53 | 0.26/0.33/0.31 | +0.305 (p .085) |
| nov_x_act_b | +0.084 | 0.10 | 0.24/0.32/0.34 | — |
| failure_mode | −0.018 | 0.73 | 0.33/0.27/0.30 | — |
| constraint_tractability | **+0.251** | **<0.001** | 0.15/0.31/0.44 | — |

**GATE → the collider pattern is DIRECTIONALLY present but WEAK/mostly non-significant.** The claimed
signs hold (actionable scorers weakly positive — nov_x_act +0.084 marginal; failure_mode ~0/slightly
negative −0.018), but none of the *content* scorers reach significance under multiplicity. The one
strong accept-predictor is **constraint_tractability (+0.25, p<0.001)** — i.e. acceptance is driven by
difficulty/tractability, not by SI actionability. On HoVer (thin) actionability is marginally positive
(+0.305, p=0.085). **Read:** suggestive, not confirmed support for the treatment-correlated
imputation-bias story → the ungated-probe redesign is *reasonable insurance* but NOT compelled by these
logs; note the divergence stays largely unresolved and difficulty is the dominant accept confound.

## CHECK 5 — batch diversity vs outcome (DPP precursor)
Per-batch dispersion = mean pairwise cosine distance of the 3 examples' full-triple TF-IDF vectors;
regress outcome on it.

| corpus | ρ(dispersion, outcome) | p | partial (\|difficulty, mean-knn) |
|---|---|---|---|
| IFBench (n=382, LOO) | −0.011 | 0.83 | +0.019 |
| HoVer (n=33, mbi; thin) | −0.109 | 0.55 | — |

**GATE → NO batch-diversity signal.** Dispersion of the 3 SIs does not predict the outcome, raw or
partial, on either corpus. Mean/max aggregation washout is **not** the issue → drop the DPP/diversity
worry (at least at this cheap TF-IDF-dispersion resolution).

## Bottom line (gates only — not headline claims)
1. **ICC:** static per-example scoring is type-correct — keep the design. 2. **Control R²:** IFBench
outcomes are ~90% unpredictable from anything; the Wave-1 null is partly a well-posedness ceiling, not
purely id-absorption. 3. **Addressable ceiling:** ~90% of HoVer failures are retrieval-only, invisible
to SI-content scorers → the powered screen chases a ~10% minority; power-calc on the (a)-subset only.
4. **Accept-rate:** collider story directionally present but weak/n.s.; difficulty (tractability) is the
real accept driver → ungated probe is optional insurance, not compelled. 5. **Batch diversity:** no
signal → drop the DPP worry. Multiplicity + HoVer thinness noted; nothing here proves a scorer works.
