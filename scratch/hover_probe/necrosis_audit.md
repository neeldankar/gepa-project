# Necrosis pipeline audit — are last night's HoVer results trustworthy?

**Date:** 2026-07-01 · **$0, read-only, no runs, no edits** (this report is the only new artifact).
Method: independent byte-level recompute (fresh code) + two independent audit agents (code
number-path + data files). Looking for ONE class of bug — a silent substitution in the number path
(wrong object / dict-keys-vs-values / wrong column / mis-join / label miscategory) that yields
plausible output and throws no error — the class of all three known bugs. Calibrated: a clean
component is a valid finding.

## Deliverable 1 — byte-level recompute (are the numbers real?)

| check | method | result | verdict |
|---|---|---|---|
| `val_subscores` are per-instance **recalls**, not integer indices | dumped 11×10 dict; printed values + global min/max | values 0.0/0.333/0.667/1.0, **min/max = [0,1]** over 407 values; keys are JSON strings; `vec()` reads values via `d.get(str(i))` | **MATCH** (keys-vs-values bug absent) |
| **ΔU** per event traced from `val_subscores` → accept-inference → recorded ΔU | fresh frontier-order recompute over discovery order | nonzero on candidates {1,2,3,5} = **0.0333 / 0.0667 / 0.0667 / 0.0333**; all others 0; md verbatim event 7 (pos 6) → ΔU 0.0000 reconciles | **MATCH** |
| event↔ΔU **join** (off-by-one / mis-join) | content join: per-event parsed feedback recalls vs `trace[t].subsample_scores` | **0/33 mismatches**; `trace["i"]==position` ∀t; discovery order non-decreasing `[0,46,68,…,298]` | **MATCH** (byte-perfect) |
| `failure_mode` feature (the +0.225 standout) | independent reimplementation from raw bytes vs pipeline fn, idx 7/8/13/1/31 | **0.3333 / 0.4444 / 0.0000 / 0.0000 / 0.6667 — exact match** (both predictors, incl. ΔU>0 events) | **MATCH** |
| **residualization** control columns actually regressed out | read `Z = np.column_stack([...])` | `Z = [recall_evt, n_retrieved_evt]` — **2 columns** (see finding below) | see finding |
| n_retrieved control join coverage | join reflection units → retrieval_log | **99/99 example-units matched** (no silent default-to-0) | **MATCH** |

Counts corroborated independently: `len(trace)=len(reflections)=reflection_events=33`; inferred
accepts (`mean(new)>mean(old)`) `=10=candidates−1=accepts_inferred`; spend `$1.9602`.

**→ Last night's table is trustworthy at the byte level.** Every quantity recomputes to what it claims.

## Deliverable 2 — chain walk (hand-off integrity)

| arrow | status |
|---|---|
| raw reflection bytes → `parse_examples()` fields | ✓ regex extracts claim/notes/context/reasoning/query/new_notes/feedback + recall from `X/N` |
| fields → scorer features (a=feedback, b=full, c=delta) | ✓ knn/ncd/actionability on both variants; failure_mode (b) with zeroed (a); delta=b−a |
| per-example → per-event aggregation | ✓ mean over examples grouped by `ex_event` |
| controls `Z` | ✓ built as `[recall, n_retrieved]` — **2 cols** (finding) |
| ΔU dict→array (**keys-vs-values spot**) | ✓ `d.get(str(i))` reads VALUES; JSON string-key fallback correct |
| ΔU event↔candidate (**mis-join spot**) | ✓ frontier walked in discovery order; `acc` counter maps accepted events→candidate idx; 1:1 via `use_merge=False`; content-join 0/33 |
| partial_spearman → boot_ci | ✓ residualizes ranks of x and y on ranked Z, Pearson of residuals; CI = bootstrap percentiles over events |
| verdict label (**DEAD-collapse spot**) | ✓ `verdict3` is 3-state (NOT-DEAD if lo>0; DEAD if pt≤0.05; else INCONCLUSIVE) — the corrected logic is what produced the final table (2 DEAD, 3 INCONCLUSIVE, 0 NOT-DEAD) |

All seven arrows clean; the three known-bug-class spots are individually verified absent.

### The one finding (calibrated — a documentation gap, NOT a wrong number)
The residualization regresses out **{recall, n_retrieved}**, not the five controls the brief names
(recall, n_retrieved, n_hops, overlap, difficulty). The three omitted are constant or collinear —
`n_hops≡3` (no variance), `difficulty≡1−recall` (perfectly collinear), `overlap≈recall×n_gold`
(near-collinear at ~constant gold size) — so the reduction is statistically defensible and does not
change the residuals. This is not a silent substitution (recall and n_retrieved are computed
correctly); it is a **claimed-vs-actual documentation mismatch**: the writeup should say "residualized
on 2 controls (recall, n_retrieved)," not imply 5. No number is wrong; the description overstates the
control set. (Adding `overlap` explicitly would be the only non-redundant change, and it is ~collinear.)

## Deliverable 3 — cheap runtime guards (propose, do NOT implement)

| bug/risk (class) | one-line assertion that would auto-catch it |
|---|---|
| feedback-string = wrong object | `assert '### reasoning' in obj_b and len(obj_b) > 3*len(feedback)` — the scored (b) object must carry the reasoning/passage channel |
| val_subscores keys-vs-values | `assert all(isinstance(v,float) and 0<=v<=1 for d in subs for v in d.values()) and [v for v in subs[0].values()] != sorted(int(k) for k in subs[0])` |
| event↔ΔU mis-join / off-by-one | `assert len(trace)==n_events==len(reflections)` and `assert inferred_accepts==len(subs)-1` and `assert per_event_parsed_recalls==trace[t].subsample_scores` (content join) |
| DEAD-collapse label | `assert not any(pt>NOISE and label=='DEAD' for ...)` and `assert label in {DEAD,INCONCLUSIVE,NOT-DEAD,N/A}` |
| power / non-null (a) baseline | `if abs(residual_a) > tol: emit 'POWER-LIMITED'` and `if (du>0).mean() < thresh: emit 'ΔU-SPARSE'` — turn the eyeballed power caveat into an automatic flag |
| control-set claim vs code | `assert set(Z_column_names) == set(DOCUMENTED_CONTROLS)` — catches "said 5, coded 2" |

These convert "caught only if a human eyeballs it" into "throws/flags automatically." For later, not now.

## Deliverable 4 — trust verdict on last night's result

**Two distinct kinds of trust — do not conflate them.**

**BUG-trustworthy: YES.** The numbers compute what they claim. The full number path was verified clean
two independent ways (byte recompute + two agents): `val_subscores` are real recalls in [0,1] (not the
keys-vs-values signature), the event↔ΔU join is byte-perfect (0/33 content mismatches, off-by-one
absent), the standout `failure_mode` feature reproduces exactly, and the DEAD-collapse label bug is
confirmed fixed in the code that produced the final table. The sole finding is cosmetic — the
residualization uses 2 controls (recall, n_retrieved), not the 5 the writeup implies, but the omitted
three are constant/collinear so no residual or correlation changes. **The INCONCLUSIVE table is bug-clean.**

**POWER-trustworthy: NO (already known, and orthogonal to bugs).** n=33 events, ΔU nonzero on only 12%,
bootstrap CIs ~±0.4, and the (a) feedback-only sanity did not reproduce a clean null (`ncd_novelty(a)`
= +0.24) — the run is underpowered. So the result is **bug-clean but too underpowered to conclude from**:
"no silent substitution" does NOT mean "resolved." The INCONCLUSIVE verdict (not a clean kill; failure_mode
the strongest but not proven) stands exactly as reported — trustworthy *as an inconclusive result*, and
no more. Any decision to fund the powered screen rests on judgment about that underpowered signal, not on
a bug in these numbers.
