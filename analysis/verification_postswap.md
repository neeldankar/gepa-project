# Batch-swap v2 — post-run verification (offline, $0)

All values reproduced from the repo's own frozen outputs. No API calls; no corpus file modified.
Reference values from the brief (`cc-brief-postswap-verification.md`) verified to 4dp.

## Task 1 — sibling-ranking probe (source: `scripts/verify_task1_sibling_probe.py`, from `calls.csv`)

Cells = (pair, arm) = 764 (382 pairs × 2 arms, all 3 draws). own-margin = `margin_on_B` for R_B,
`margin_on_Bp` for R_Bp; accept = own-margin > 0; best-of-3 = max own-margin, ties averaged.

| quantity | reproduced | reference | MATCH? |
|---|---|---|---|
| single-draw accept rate | 0.3442 (789/2292) | 0.3443 | **MISMATCH** |
| best-of-3 accept rate | 0.5641 | 0.5641 | MATCH |
| E[own-margin] single | +0.0043 | +0.0043 | MATCH |
| E[own-margin] best-of-3 selected | +0.2298 | +0.2298 | MATCH |
| selection lift | +0.0059 | +0.0059 | MATCH |
| selection lift 95% CI (cluster boot, 8 runs, 4000 it) | [-0.0059, +0.0201] | [-0.0057, +0.0199] | within MC noise |
| within-cell correlation | +0.0010 | +0.0010 | MATCH |

- single-draw accept: exact value 789/2292 = 0.344240837… → 0.3442 (4dp). First divergence at the 4th
  decimal: reference 0.3443 requires ≥0.344245 (≈789.14 draws), unreachable with an integer count.
  Both agree at 3dp (0.344). Not reconciled.
- selection lift CI: point estimate matches exactly; the two bounds differ by ≤2×10⁻⁴, within
  cluster-bootstrap Monte-Carlo noise (RNG-seed dependent; both straddle 0).

Robustness rows (no reference; selection lift, same cells, 8-run cluster-boot CI):

| variant | selection lift | 95% CI |
|---|---|---|
| accept ≥ 0, tie-tolerant (selected = accept set; 666 cells, 98 no-accept cells skipped) | +0.0043 | [-0.0030, +0.0107] |
| selection by max own-batch `child_sum` (not margin) | +0.0059 | [-0.0055, +0.0201] |

## Task 2 — provenance of the 0.382 lottery figure (source: `scripts/verify_task2_lottery.py`)

Code path: `scripts/batch_swap_v2_analysis.py:73-77` (accumulation), `:109-110` (reduction).

1. **Accept rule**: batch-**sum** margin, strict `> 0`. Per draw, accept = `float(r["margin_on_B"]) > 0`
   — the B-batch sum margin (`child_sum_B − parent_B_sum`), applied to `margin_on_B` for **both** arms
   (R_B and R_Bp). Not per-example pointwise; no tie handling, no normalization. Mirrors the native gate
   `StrictImprovementAcceptance.should_accept` (`new_sum > old_sum`) in
   `/Users/neeldankar/Desktop/gepa/src/gepa/strategies/acceptance.py`.
2. **Denominator**: one non-unanimity indicator per (pair, arm) cell with ≥2 draws; every cell has 3
   draws → **n = 764** cells. Indicator = `1` iff `len(set(accept-bools)) != 1`. Statistic = mean over cells.
   No exclusions.
3. **Recompute**: 0.3822 (4dp) → **0.382 (3dp) MATCH**.

| statistic | reproduced | reference | MATCH? |
|---|---|---|---|
| coded lottery (`margin_on_B>0`, both arms) | 0.3822 (0.382 at 3dp) | 0.382 | MATCH |
| own-margin accept, `> 0` | 0.4149 | 0.4149 | MATCH |
| own-margin accept, `>= 0` | 0.3979 | 0.3979 | MATCH |
| coded rule (`margin_on_B>=0`, both arms) — reference-only | 0.4045 | — | — |

The coded 0.382 differs from the 0.4149/0.3979 sum-margin variants because the coded lottery uses
`margin_on_B` for **both** arms, whereas the variants use each arm's **own** batch margin
(`margin_on_B` for R_B, `margin_on_Bp` for R_Bp).

results.md edit (appended under `## Lottery`): `Accept rule for this figure: within-arm accept =
margin_on_B>0 (batch-sum, strict), applied to margin_on_B for both arms; disagreement = non-unanimity
of accept across the 3 draws per (pair,arm) cell, n=764 cells. Sum-margin (own-margin) variants:
0.415 (>0), 0.398 (>=0).`

## Task 3 — results.md corrections (source: `scripts/verify_task3_overlap_boot.py`)

**Definitions verified against harness** (`scripts/batch_swap_v2_analysis.py:61-68`): the brief's
pooled-specificity and pooled-transfer definitions MATCH the code exactly (draws averaged within arm
first via `draw_avg`, then mean over pairs). Recomputed pooled specificity +0.0054 (MATCH),
pooled transfer −0.0011 (MATCH).

Overlap-decomposition values written into results.md, verified:

| value | reproduced | written / reference | MATCH? |
|---|---|---|---|
| OLS intercept | -0.0176 | -0.0176 | MATCH |
| OLS slope | +0.0690 | +0.0690 | MATCH |
| slope 95% CI (run-cluster boot, NBOOT=20000, seed 20260703) | [-0.0756, +0.1980] | [-0.0739, +0.1959] | within MC noise |
| pred@overlap=1 95% CI | [-0.0485, +0.1384] | [-0.0476, +0.1368] | within MC noise |
| type_jaccard max | 0.8333 | 0.83 | MATCH (stated 2dp) |
| type_jaccard mean | 0.3346 | 0.335 | MATCH (stated 3dp) |

- Bootstrap CIs: recomputed bounds differ from the written values by ≤2.1×10⁻³ (cluster-bootstrap
  Monte-Carlo noise, RNG-seed dependent); both CIs straddle 0.

**Diff applied to `analysis/ablation/batch_swap_v2/results.md`** (no existing number changed):
1. `## Overlap decomposition` body replaced — deleted the parenthetical `(stays >0: example-level)` and
   the `predicted@overlap=1 → +0.0513` reliance; new body states OLS intercept/slope, run-cluster
   bootstrap slope CI [-0.0739,+0.1959], prediction@overlap=1 CI [-0.0476,+0.1368], jaccard support
   max 0.83 (mean 0.335), out-of-support, "No masking or example-level residual is supported."
2. Definitions line added under the Headline table (pooled specificity / pooled transfer).
3. Lottery provenance line added (Task 2).
Headline table, verdict line, and Interpretation section unchanged.

## Task 4 — gate-size probe (source: `scripts/verify_task4_gatesize.py`)

Accept rule = Task 2 rule: strict `sum(child) > sum(parent)` over the gated examples (ties → reject).

### 4A — decision instability of the ORIGINAL b3 gate, 382 batches

Per-example parent (`before.scores`) and **original GEPA child** (`after.scores`) from the 8 b3 logs
(`logs/baseline_seed{0..7}_b3_*.jsonl`); 382/382 batches mapped, 0 missing. This is the original gate
(parent vs the child GEPA actually proposed), **not** the batch-swap R_B/R_Bp sibling draws. Recomputed
b=3 accept validates **382/382** against the logged accept.

| b′ (gate size) | P(decision ≠ full b=3) | within-b′ disagreement | n subset-gates | n batches |
|---|---|---|---|---|
| 1 | 0.2033 | 0.3717 | 1146 | 382 |
| 2 | 0.1038 | 0.3089 | 1146 | 382 |

(CSV: `analysis/verification_postswap_task4_instability.csv`.)

Per run:

| seed | n batches | P_flip b′=1 | P_flip b′=2 | within b′=1 | within b′=2 |
|---|---|---|---|---|---|
| s0 | 39 | 0.2479 | 0.1197 | 0.4872 | 0.3590 |
| s1 | 34 | 0.3137 | 0.1667 | 0.5588 | 0.5000 |
| s2 | 42 | 0.2063 | 0.0952 | 0.3571 | 0.2857 |
| s3 | 41 | 0.2358 | 0.1220 | 0.4146 | 0.3659 |
| s4 | 63 | 0.1429 | 0.0635 | 0.2857 | 0.1905 |
| s5 | 64 | 0.1562 | 0.0833 | 0.3125 | 0.2500 |
| s6 | 60 | 0.1556 | 0.0944 | 0.2667 | 0.2667 |
| s7 | 39 | 0.2735 | 0.1368 | 0.4615 | 0.4103 |

### 4C — b=1 baselines

| run | n cycles | accept rate | recomputed == logged | same-input repeat disagreement |
|---|---|---|---|---|
| seed0_b1 | 45 | 0.3333 | 1.0000 | none (0 example-ids sampled in ≥2 cycles) |
| seed1_b1 | 60 | 0.2500 | 1.0000 | none (0 example-ids sampled in ≥2 cycles) |

No same-input repeat-draw disagreement statistic exists in the b=1 logs: no minibatch example id is
sampled in ≥2 reflection cycles, so no repeated-input decision pair is present.

### 4B — INFEASIBLE offline (not computed)

Ranking the 3 batch-swap sibling draws (R_B/R_Bp) by own-margin on b′=1/b′=2 subsets requires
per-example scores of the **child draws**. `scripts/batch_swap_v2_run.py:230-235` computed each draw
with `capture_traces=False` and wrote only the batch **sums** (`child_sum_B/Bp`) to `calls.csv`; the
per-example score vectors were discarded and exist in no file. Recovering them requires re-running the
paid proposer + evaluator (live LM calls), which the brief forbids. No 4B numbers are reported.

## Provenance

Scripts (all read-only, $0; run as `HF_DATASETS_OFFLINE=1 .venv/bin/python <script>`):
- `scripts/verify_task1_sibling_probe.py` — cluster bootstrap seed 20260705, 4000 iterations, 8 runs (B_id seed prefix).
- `scripts/verify_task2_lottery.py`
- `scripts/verify_task3_overlap_boot.py` — run-cluster bootstrap seed 20260703, NBOOT 20000.
- `scripts/verify_task4_gatesize.py` — writes `analysis/verification_postswap_task4_instability.csv`.

Inputs (frozen, read-only):
- `analysis/ablation/batch_swap_v2/calls.csv` (2292 draws), `.../pairing.csv` (382 pairs, `type_jaccard`).
- `logs/baseline_seed{0..7}_b3_*.jsonl` (per-example parent/child scores), `logs/baseline_seed{0,1}_b1_*.jsonl`;
  parsed via the same schema as `gepa_si/screen/corpus_io.py` (`discover_runs`: mm=2500 & completed).

Harness references:
- Lottery accept rule + reduction: `scripts/batch_swap_v2_analysis.py:73-77`, `:109-110`.
- Pooled specificity / transfer definitions: `scripts/batch_swap_v2_analysis.py:61-68`.
- Overlap OLS: `scripts/batch_swap_v2_analysis.py:95-100`.
- Native gate (strict-improvement): `/Users/neeldankar/Desktop/gepa/src/gepa/strategies/acceptance.py`.

Edits: `analysis/ablation/batch_swap_v2/results.md` — 3 additions/replacements (Task 2 lottery line,
Task 3 overlap section body, Task 3 Headline definitions line); no existing number changed.
