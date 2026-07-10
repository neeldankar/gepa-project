# Session summary — HoVer heterogeneity screen, Phase B (2026-07-09)

Compiled from the Phase B run (Parts 4–5 of the pre-registered screen). Raw numbers first,
interpretation at the end, clearly separated. Canonical numbers-only output:
`analysis/hover_screen/results.md` (882 lines; machine-readable twin
`screen_stats_cells.csv`). This document is a session record and contains interpretation;
results.md does not.

Commits this session: `15fba55` (AMENDMENTS 1–3 + A1 approval appended to spec.md,
committed **before** any scorer column touched any outcome column), `8be66ac` (Parts 4–5
outputs). Predecessor tag `screen-spec-frozen` = `2fb33dd`. `findings_summary.md` untouched.

**Caveat printed on every CI:** run-clustered bootstrap on only 8 clusters is known to run
anti-conservative; the within-run permutation p is not run-clustered.

---

## Setup (as frozen)

- Events n = 243, clusters = 8 runs. Primary outcome spec_i; secondary sign_i, trans_i.
- Reads: 4.1 = OLS on per-run-z scorer + iteration + parent_pool_score; 4.2 = 4.1 +
  difficulty axis (diffbase_mean, hardworst_mean, hardmean_mean, hard_censored_n;
  self-dropped for control cells) per Amendment 2.
- BCa cluster bootstrap B = 9999 (one shared resample set, rng 20260711); within-run
  permutation P = 9999; MDE = 2.802 × SD(bootstrap betas).
- **Race cells: 108.** COVERAGE-VOID (Amendment 1): 31 columns (within-run difficulty
  family, staleness, visit_count, forgetting — 2/243-event coverage). DEGENERATE
  (Amendment 3): 13 columns (ngold = 3, vt_* = 0, cofail_std = 0, etc.).
- A1 (difficulty_baseline) raced as approved, flagged.

## 4.7 Negative control (per-run permuted diffbase_mean, identical pipeline)

| beta | 95% BCa CI | MDE | perm p | LORO | survives (a) |
|---|---|---|---|---|---|
| +0.00122 | [−0.02408, +0.01908] | 0.03026 | 0.9126 | 3/8 | no — pipeline sane |

## 4.5 / 4.6 survivor lists (primary outcome spec_i, pre-registered criteria)

| list | cells |
|---|---|
| (a) DEPLOYABLE-criteria, raw | knn_emb_fb_min, knn_emb_full_mean, knn_emb_full_max |
| (b) ORTHOGONAL, raw | knn_emb_fb_min, knn_emb_full_mean |
| MCB best set (Hsu, 5th pct) | 6/108 cells |
| (a) MCB-adjusted | **knn_emb_fb_min** |
| (b) MCB-adjusted | **knn_emb_fb_min** |

Survival criteria: (a) BCa CI excludes 0 AND LORO sign-stable ≥7/8 AND within-run perm
p < 0.05; (b) additionally 4.2 CI excludes 0 AND 4.2 perm p < 0.05.

## Survivor and near-miss rows (primary outcome spec_i, verbatim from results.md)

### 4.1 (minimal controls)

| cell | n | beta | 95% BCa CI | SE | MDE | perm p | LORO | held-out ρ |
|---|---|---|---|---|---|---|---|---|
| knn_emb_fb_min | 235 | +0.03794 | [+0.01045, +0.07031] | 0.01531 | 0.04291 | 0.0013 | 8/8 | +0.1152 |
| knn_emb_full_mean | 235 | +0.02674 | [+0.01154, +0.06394] | 0.01200 | 0.03362 | 0.0230 | 8/8 | +0.0041 |
| knn_emb_full_max | 235 | +0.02407 | [+0.00224, +0.05758] | 0.01406 | 0.03939 | 0.0405 | 8/8 | +0.0323 |
| knn_emb_fb_mean | 235 | +0.02356 | [−0.00109, +0.06868] | 0.01657 | 0.04644 | 0.0452 | 8/8 | +0.0300 |
| signov_max | 242 | +0.05923 | [−0.00000, +0.06524] | 0.02824 | 0.07913 | 0.1501 | 8/8 | +0.2800 |
| repr_min | 243 | +0.01915 | [+0.01236, +0.02878] | 0.00411 | 0.01152 | 0.0994 | 8/8 | +0.1203 |
| nxa_emb_fb_min | 235 | +0.02271 | [+0.00198, +0.03979] | 0.00969 | 0.02714 | 0.0532 | 8/8 | +0.1225 |
| nxa_emb_delta_mean | 234 | +0.01376 | [+0.00080, +0.02842] | 0.00699 | 0.01958 | 0.2384 | 8/8 | +0.0468 |
| ncd_delta_std | 235 | −0.02462 | [−0.06525, +0.01099] | 0.01955 | 0.05477 | 0.0347 | 8/8 | −0.0098 |
| cofail_mean | 165 | −0.03455 | [−0.07147, +0.00000] | 0.02369 | 0.06637 | 0.2116 | 8/8 | −0.2105 |

Near-miss notes (exact): repr_min CI excludes 0 and LORO 8/8 but perm p = 0.0994 → fails
(a) on the permutation leg. knn_emb_fb_mean p = 0.0452 but CI [−0.00109, +0.06868] touches
0 → fails on the CI leg. signov_max fails both (CI lower bound −0.00000, p = 0.1501).
ncd_delta_std p = 0.0347 but CI spans 0 → fails.

### 4.2 (+ difficulty axis, Amendment 2)

| cell | n | beta | 95% BCa CI | SE | MDE | perm p | LORO | held-out ρ |
|---|---|---|---|---|---|---|---|---|
| knn_emb_fb_min | 235 | +0.03877 | [+0.01068, +0.07011] | 0.01520 | 0.04259 | 0.0013 | 8/8 | +0.1152 |
| knn_emb_full_mean | 235 | +0.02657 | [+0.00783, +0.07622] | 0.01477 | 0.04139 | 0.0239 | 8/8 | +0.0041 |
| knn_emb_full_max | 235 | +0.02441 | [−0.00149, +0.06399] | 0.01631 | 0.04570 | 0.0419 | 8/8 | +0.0323 |
| hard_censored_n | 243 | +0.03433 | [−0.00311, +0.06388] | 0.01698 | 0.04759 | 0.0033 | 8/8 | +0.1096 |
| repr_std | 243 | −0.02113 | [−0.04696, −0.00355] | 0.01078 | 0.03020 | 0.0704 | 8/8 | −0.1095 |
| repr_min | 243 | +0.01771 | [+0.00878, +0.03026] | 0.00539 | 0.01511 | 0.1304 | 8/8 | +0.1203 |
| fix_mean | 242 | +0.01174 | [+0.00094, +0.02579] | 0.00626 | 0.01753 | 0.3241 | 8/8 | +0.0491 |
| ncd_delta_std | 235 | −0.02756 | [−0.06846, +0.00706] | 0.01945 | 0.05450 | 0.0209 | 8/8 | −0.0098 |

knn_emb_full_max drops off list (b) here: 4.2 CI [−0.00149, +0.06399] touches 0.

## Secondary outcomes — strongest rows (verbatim; no survival criteria attach)

sign_i, 4.1: knn_emb_fb_min +0.19560 [+0.09344, +0.29185] p=0.0009 LORO 8/8;
nxa_emb_fb_min +0.16235 [+0.09969, +0.25157] p=0.0072; signov_max +0.23754
[+0.00000, +0.26749] p=0.0286; act_fb_min +0.12302 [+0.07293, +0.18863] p=0.0403;
act_fb_std −0.11949 [−0.19547, −0.05404] p=0.0472; repr_min +0.12251 [+0.08437, +0.17449]
p=0.0466; repr_std −0.12223 [−0.25435, +0.03905] p=0.0409; nxa_fb_min +0.12395
[+0.05579, +0.22696] p=0.0458; nxa_fb_std −0.12523 [−0.22716, −0.06193] p=0.0413.

sign_i, 4.2: knn_emb_fb_min +0.20453 [+0.09228, +0.28574] p=0.0008; nxa_emb_fb_min
+0.14716 [+0.06291, +0.26934] p=0.0155; diffbase_max −0.16346 [−0.32656, −0.02007]
p=0.0092; hard_censored_n +0.13182 [−0.02527, +0.28858] p=0.0320.

trans_i, 4.1: ctok_mean −0.04554 [−0.08694, −0.00684] p=0.0049; ctok_max −0.03959
[−0.07474, −0.01431] p=0.0184; repr_mean −0.04618 [−0.08802, +0.00125] p=0.0058;
repr_min −0.03854 [−0.07389, +0.00553] p=0.0193.

trans_i, 4.2: ctok_mean −0.04841 [−0.08752, −0.00801] p=0.0034; ctok_max −0.04130
[−0.07436, −0.01298] p=0.0134; repr_mean −0.04939 [−0.09156, −0.00846] p=0.0032;
repr_min −0.03959 [−0.07140, +0.00253] p=0.0182; hardmean_min −0.04538
[−0.08886, +0.02880] p=0.0094.

## 4.4 rank robustness (within-run Spearman vs spec_i, Fisher-z pooled)

No cell reaches permutation p < 0.05. Largest: knn_emb_fb_min +0.1247 (p=0.0709);
act_delta_max +0.1219 (0.0716); knn_fb_min +0.1220 (0.0778); repr_min +0.1193 (0.0706);
hard_censored_n +0.1178 (0.0761); knn_emb_fb_std −0.1177 (0.0866). Low-coverage rows:
signov_max +0.2800 (1 run), cofail_mean −0.2045 (2 runs), fm_f1_share (3 runs).

## 5.2 second-path recompute (statsmodels vs lstsq, top-3 by |4.1 beta|)

| cell | lstsq | statsmodels | abs delta |
|---|---|---|---|
| signov_max | +0.059228966 | +0.059228966 | 4.16e-17 |
| knn_emb_fb_min | +0.037939503 | +0.037939503 | 3.47e-17 |
| cofail_mean | −0.034547289 | −0.034547289 | 0.00e+00 |

## Anomaly list (Phase B)

1. Verbatim-paste deviation in the report-back: secondary-outcome and full 4.4 tables were
   summarized with notable rows restated exactly (committed file is the verbatim source).
2. First Part-4 run crashed after the negative control on a dead line in
   `spearman_pooled`; removed and rerun. Fixed seeds; negative-control result identical
   across runs; no outcome-dependent choice between runs.
3. `act_full_n` raced (108 includes it) though the amendment's bookkeeping rule should
   have excluded it; survives nothing; inflates the MCB reference set (conservative).
4. cofail_mean/max/min numerically identical (n=165; batches almost always have exactly
   one example with ≥2 missed titles).
5. signov/fm_f1 4.4 cells rest on 1–3 runs; several signov/cofail BCa endpoints are
   exactly ±0.00000 (bootstrap mass at zero from discrete scorer support).
6. Negative control does not survive — pipeline sane; no STOP.
7. Phase A anomalies carry unchanged; `notes/HANDOFF.md` and the two session summaries
   remain untracked.

---

## Interpretation (bland, scoped; survival criteria are the pre-registered ones — no
## reading beyond them)

- The pipeline validates itself: the pure-noise scorer, run through the identical
  machinery, produces a null on every leg. The 5.2 second path agrees to floating-point
  precision. Whatever survives is not a pipeline artifact.
- **One cell survives everything: `knn_emb_fb_min`** — the batch minimum of
  embedding-space novelty of the feedback-only SI text relative to the run's prior SI
  (k=3 nearest archive items). It passes the raw deployable criteria, the orthogonality
  read (difficulty-axis controls barely move it: +0.0379 → +0.0388), and is the only
  MCB-adjusted survivor on both lists. Its sign_i read is concordant and stronger in
  z-units (p ≈ 0.001), which says the association is not purely tie-dilution artifact.
- The effect direction is positive: events whose least-novel batch member is still
  comparatively novel (relative to run history) measured higher swap specificity. Two
  siblings (knn_emb_full_mean, knn_emb_full_max) survive the raw list; the family, not
  just the single cell, carries the signal — though only in embedding space; the TF-IDF
  versions of the same scorers do not survive, and 4.4's rank-based read backs nothing at
  p < 0.05, so the evidence rests on the OLS/bootstrap read.
- **Every survivor is Class B** (requires realized SI). The pre-registered live-confirm
  clause keys on a Class A scorer passing (a); the Class A list is empty (repr_min is the
  closest, failing only the permutation leg), so no live-confirm decision is triggered by
  this screen's own rules.
- Magnitudes are modest: ~0.038 specificity points per within-run SD of the scorer,
  against a pooled specificity of +0.027 — detectable heterogeneity, not a dominant axis.
  The 8-cluster anti-conservatism caveat applies to the CI leg of every survival call.
- The secondary transfer reads (claim length and representativeness negatively predicting
  trans_i at small p) carry no pre-registered criteria and 108-cell multiplicity; they are
  noted, not promoted.
