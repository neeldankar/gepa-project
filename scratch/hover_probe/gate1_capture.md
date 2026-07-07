# HoVer GATE 1 — reflection-object capture + richness confirmation

**Date:** 2026-06-30 · **Actual spend:** **$0.142** (cap $0.50) · isolated `scratch/hover_probe/`
(dspy 3.2.1 / gepa 0.0.27, bm25s over 5.23M wiki abstracts; main `.venv` untouched).
Code: `scratch/hover_probe/gepa_capture.py`. Captures: `capture/reflect_{1,2,3}.{txt,json,repr}`,
`capture/equality.json`.

## Why this gate
The prior HoVer probes never ran GEPA — they manufactured a "docs remaining" string (`build_si`)
and eyeballed *that*, i.e. the **feedback annotation** = the exact thin-object mistake that
produced the IFBench null. GATE 1 runs GEPA for real and captures **what `reflection_lm` actually
receives at its call boundary**, then confirms richness by reading the bytes — not assuming.

## Step 1 — capture + byte-equality (PASS)
Minimal `dspy.GEPA` run (`max_metric_calls=24`, `reflection_minibatch_size=3`, round_robin over
the 2 predictors, 6 train / 3 val imperfect claims). Two independent capture layers:
- **Layer A** — `CaptureDSpyLM(dspy.LM).__call__` records the prompt string before forwarding.
- **Layer B** — `litellm.success_callback` records the wire `messages[...].content` (what hits the API).

| | value |
|---|---|
| reflection calls (Layer A) | **3** |
| wire reflection msgs (Layer B) | **3** |
| total LM calls | task **144** + reflection **3** = **147** |
| **byte equality A==B** | **PASS** on all 3 calls (lens 7329 / 23806 / 10580) |
| spend | **$0.142** |

**Two-way byte-equality** (`dspy.LM.__call__` input == litellm wire payload). Since Layer B is
literally the API payload and A==B, we know exactly what the reflection LM received. (This is
two-way, not the three-way IFBench had — dspy-GEPA doesn't log the proposal prompt as accessibly;
the wire payload is the ground-truth anchor, so two-way is sufficient here. Stated, not inflated.)

## Step 2 — object inventory + RICH/THIN fork
dspy-GEPA reuses the same `gepa` proposer, so the wrapper template is identical to IFBench
(`"I provided an assistant with the following instructions"` … per-example `## Inputs /
## Generated Outputs / ## Feedback` … `Your task is to write a new instruction`). But the
**per-example content is the optimized predictor's real input/output dict** — and both predictors
are `ChainOfThought`, so a `reasoning` field exists (IFBench's single `Predict` had none).

Captured (round_robin cycled through both, and evolved the gen_query instruction between call 1
and call 3 — confirming the optimization loop actually ran):

| call | predictor | Inputs | Generated Outputs | Feedback | rich channel present? |
|---|---|---|---|---|---|
| reflect_1, reflect_3 | `gen_query` | claim, **notes** | **reasoning**, query | build_si line | reasoning + accumulated multi-hop notes + generated query (no passages) |
| reflect_2 | `append_notes` | claim, notes, **context** | **reasoning**, new_notes, titles | build_si line | **reasoning + 10 FULL retrieved passages (title + abstract prose) + notes** |

**Verified by reading the bytes** (not assumed): `reflect_2`'s `### context` is 10 real Wikipedia
abstracts per example (30 `"title | text"` passages across the 3-example minibatch), e.g.
verbatim: *"Thurston Moore | Thurston Joseph Moore (born July 25, 1958) is an American musician
best known as a singer, songwriter and guitarist of Sonic Youth. …"* — full prose, not titles/ids,
not id-determined by a small label set. `### reasoning` is genuine multi-step CoT synthesizing
notes+context.

**FORK CALL → RICH.** `append_notes` is fully rich (reasoning + full passage text + notes);
`gen_query` is moderately rich (reasoning + multi-hop notes + query, no passages). Both strictly
richer than IFBench's Predict object. The id-determinism collapse argument does **not** apply →
live material for selection → PROCEED to Step 3.

## Step 3 — 2×2 eyeball (usefulness vs difficulty)
Difficulty = per-example recall from the **captured** Feedback line (this fresh run, not the stale
eyeball). Usefulness = does the object plausibly drive a good instruction revision. Evidence:

- **`append_notes` — Sonic Youth claim** (recall 2/3; missing `Mikael Åkerfeldt`). The reasoning
  correctly refutes the claim from the passages, but the missed gold entity is a **spelling
  variant**: the claim says "Michael Akerfeldt", the gold doc is "Mikael Åkerfeldt" (Opeth), and
  the reasoning never disambiguates it ("Michael Angelos was bassist in Plexi, not Michael
  Akerfeldt"). Also the output `titles` are model-invented descriptive strings ("Sonic Youth Band
  Members and Roles"), not real doc titles. **HIGH usefulness** (two actionable, non-difficulty
  signals: entity disambiguation + title-format) at moderate difficulty.
- **`gen_query` — Greek Fire claim** (recall 2/3; missing `Greek Fire (band)`). The reasoning
  **accepts the claim's unverified implication** ("this aligns with the claim … more south of…")
  instead of querying to confirm Greek Fire's location. **HIGH usefulness** (a reasoning-loyalty
  flaw a revised instruction could fix) at the *same* difficulty as the next case.
- **`gen_query` — WCJB-TV / Soul Mates claims** (recall 2/3 each). Reasoning is correct and the
  query is already well-formed; the miss is a common/deep-hop entity (`Gainesville, Florida`,
  `Beached Az`) — mostly retrieval-side. **LOW-MODERATE usefulness** at the same difficulty.
- **`append_notes` — Quietdrive claim** (recall **3/3**, perfect/easy). Object is rich but there is
  little to fix — **LOW marginal usefulness** at low difficulty.

So at essentially **constant difficulty (2/3)** usefulness ranges from low (WCJB, correct-but-
retrieval-miss) to high (Greek Fire reasoning flaw; Sonic Youth disambiguation) — usefulness
varies **not** as difficulty. And the rich channel exposes failure *textures* (reasoning loyalty,
name disambiguation, title formatting) that the recall number alone does not encode.

### LEAN — GO (genuinely-mixed on one axis)
The reflection object is RICH by direct capture, and per-example usefulness plausibly varies
independent of retrieval difficulty, with concrete actionable textures. This clears GATE 1.
**Honest caveat (variance ≠ usefulness):** this is a screening eyeball, n≈handful; some rich
objects are low-usefulness (correct reasoning + pure retrieval miss), so the signal is real but
mixed. Whether a per-example **selection** scorer can exploit it *beyond difficulty* is exactly
the GATE-2 question — that live screen is a separate, larger spend and is NOT run here.

## Deliverable checklist
- Capture files + byte-equality: `capture/reflect_{1,2,3}.{txt,json,repr}`, `capture/equality.json`
  (A==B PASS, 3 calls). ✓
- Step 2 inventory + RICH fork (per predictor). ✓
- Step 3 eyeball, verbatim events (reflect_2 ex1 byte-complete in `capture/`), GO lean. ✓
- Counts: 3 reflection / 144 task / 147 total LM calls; spend $0.142. ✓
