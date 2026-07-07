# Probe — leverage-flatness + constraint structure

Offline, $0. Characterizes the OBSERVED uniform-sampled corpus matrices only — it does NOT test what a non-uniform sampler or an aggregate gate would do.

## STEP 0 — inventory
- Matrix A = **per-run** candidate×valset (each ~16×150, fully observed, range [0,1]); pooled b3 = 123×150. NOT a single global matrix.
- Matrix B = partial_diag.parquet: 3302 rows, 1251 (cycle,example) transitions, 256 fix / 235 break events.

## Part 1 — leverage / flatness (Claim 1)
- Pooled b3 (123×150): **stable rank 14.4** (of 123 candidates), 90%-energy rank k=47, 95% k=60. Per-run stable rank ~6 of ~16 candidates → real candidate (row) redundancy.
- Column (example) leverage: **CV 0.95, Gini 0.53**, max/mean 3.0, uniform=0.3133.
- Within-row permutation null (1000 draws): observed leverage-CV at the **100th percentile** (null mean 0.13, p95 0.14) — every run also at the 100th percentile.

**Verdict 1 — SURPRISE, Claim 1's *flat-sensitivity* framing is NOT grounded.** Two things are simultaneously true and must not be conflated: (i) the matrix is **low-rank** (per-run stable rank ~6 of 16) — candidates are redundant, consistent with the fungibility result; but (ii) column **leverage is heavy-tailed and far above the within-row null** (CV 0.95, Gini 0.53, 100th percentile) — a structured minority of examples (the swingable cells) carry the leverage, the rest are near-zero (consensus cells). So 'selection futility' is a **row/redundancy** phenomenon, NOT 'flat example sensitivity': example sensitivity is the opposite of flat. (Observed-matrix claim only — this is not a test of a non-uniform sampler.)

## Part 2 — constraint structure & antagonism (Claim 2)
- **Do constraints distinguish candidates?** Candidate×constraint pass-rate matrix (16-type, 106×16, 62% observed): stable rank 8.1 of 16, mean per-type pass-rate entropy **0.75 bits** (max 1.0). Moderate rank + moderate entropy ⇒ constraints carry real variation — **weak** dual redundancy, not strong. (Caveat: confounded by uneven minibatch coverage.)
- **Antagonism:** estimable ordered pairs **N≥10: 195, N≥5: 210** of 240 (estimability is set by fix-a frequency, not break co-occurrence). Only **14%** of N≥5 pairs show a conditional break-rate ABOVE base rate.
- Top antagonistic pairs (fix a → break b; P(break b|fix a) vs base; n):
  - fix `detectable_content` → break `count`: 0.20 vs 0.02 (n=5)
  - fix `detectable_content` → break `punctuation`: 0.20 vs 0.02 (n=5)
  - fix `detectable_content` → break `keywords`: 0.20 vs 0.04 (n=5)
  - fix `startend` → break `paragraphs`: 0.15 vs 0.02 (n=13)
  - fix `startend` → break `count`: 0.15 vs 0.02 (n=13)
  - fix `last_word` → break `startend`: 0.12 vs 0.01 (n=16)
  - fix `keywords` → break `detectable_format`: 0.12 vs 0.02 (n=43)
  - fix `paragraphs` → break `startend`: 0.11 vs 0.01 (n=19)

**Verdict 2 — tradeoffs are real but SPARSE, not dense.** Breaks-on-fix exceed base rate for only 14% of estimable type pairs, and the reliable lifts are few (e.g. fix `keywords`→break `detectable_format` 0.12 vs 0.02, n=43); most fix-a transitions break nothing. The **aggregate gate is still motivated** — real tradeoffs exist and the accept gate filters them (raw stream: ~256 fixes vs 235 breaks) — but a per-pair *antagonism scorer* would only have signal on the handful of dense pairs, not a dense 16×16 structure. (Observed-stream claim only.)

