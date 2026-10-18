# Article number register (2026-10-15)

**Superseded draft (added 2026-10-17).** The published post, https://neeldankar.me/gepa-selection
(published 2026-10-17, home_website commit `7d31a9b`), supersedes the draft `gepa-selection-short.md` that the `D:n`
references in Table A point to. Table A is kept as the audit of that draft. Section R of Table B holds the numbers
added for the post's line-by-line revision (home_website branch `post-revisions`), and each open question below
now says how the published post settled it.

**Purpose.** This register traces every number in the blog draft `~/Downloads/gepa-selection-short.md` (119 lines) to a committed
file:line, and records the new numbers the revision needs. **No verdicts. No edits to the article.** The ledger
(`analysis/findings_summary.md`), every `results.md`, the logs, the runs and the pairs are quoted, never changed.

**Method**
- Every value was recomputed from raw files by `scripts/article_numbers.py compute`, under
  `analysis/state_dep/.venv-armT/bin/python -B` (Python 3.12, numpy only). Student-t quantiles and CDFs come from the
  stdlib helpers `t_cdf`/`t_ppf` in the script, checked against scipy 1.18.0 by `tests/test_t_dist.py`.
- Figures were drawn by `figures` in a throwaway scratchpad venv (matplotlib 3.9.2), which reads only the CSVs below.
- No API calls, no model calls, $0.
- Every value, with its reference, MATCH/MISMATCH status, tag, raw input, the citing doc and the producing
  function, is in `values.csv`: 404 rows, 277 with a reference, **275 MATCH, 2 MISMATCH**. Both MISMATCHes are R13
  rows (see section R); neither number is in the post. `F.frontier_gepa_HEAD` now references `fddd908`, the
  frontier-gepa `post-revisions` HEAD: `dbfbaa3` (register built) → `61c16fb` (adds BASELINE-CHECK) → `5d92514` (v1
  README commit) → `fddd908` (README em dashes). No Part F number changed.
- Two consecutive runs produce byte-identical CSVs.

**Tags**
- **[R]** The value is stated in a committed artifact and was reproduced here from raw data.
- **[C]** New, computed here. It is in no committed artifact until this directory is committed.
- **cited** Stated in a committed artifact, but *not* reproduced here (see OQ 7).

**Statistical conventions**
- Bootstrap CIs are 95% percentile intervals from 10,000 resamples, using `default_rng(20261015 + k)` with k fixed per CI.
- A reference given as a decimal is matched to half a unit of its last printed digit.
- Reference CI bounds quoted as "about" are matched within a declared Monte-Carlo tolerance of 0.005, which is printed in the row.
- "Chance agreement" is the agreement expected if the two verdicts were independent with their observed marginal accept
  rates: pa·pb + (1−pa)(1−pb).

---

## Table A: every number in the draft

`D:n` = `gepa-selection-short.md:n`. "fn" = the function in `scripts/article_numbers.py`.

| D:line | draft value | recomputed | source file:line (raw → stated) | tag | status | caveat that must travel with it |
|---|---|---|---|---|---|---|
| D:7, 13, 30, 72, 89 | "three examples" per batch | b = 3 in all 382 swap pairs; HoVer `minibatch_size` 3 | `runs/*/config.json` (`minibatch_size`); `batch_swap_v2/calls.csv` | [R] | MATCH | 2 of the 10 IFBench baseline runs used b = 1 (`c_budget_by_run.csv`). Those runs are inside the 73/145 at D:79. |
| D:7 | verdicts agree "about as often as two unrelated coin flips" | κ = −0.0108 (IFBench), +0.0074 (HoVer) | fn `a2_cross_batch`, `b_hover` | [C] | MATCH (qualitative) | "Chance" here means independence at the observed accept rates (≈0.33–0.38). It does not mean 50/50: chance agreement is 0.544, not 0.5. |
| D:13 | "one rewrite GEPA proposed on IFBench" | row 1 of `batch_swap_v2/calls.csv` | `calls.csv:2`; fn `a1_opening` | [R] | MATCH, with caveat | The rewrite comes from the batch-swap experiment: the proposer is replayed at a logged state of P_B. It is not a live GEPA run's proposal. |
| D:17 | batch 1: rewrite 1.00, parent 0.75, kept | 1.0 / 0.75, margin +0.25, keep | `calls.csv:2` | [R] | MATCH | Batch 1 = B, which is **not** the batch the rewrite was written from (arm R_Bp; `batch_swap_v2_run.py:221, 223`). |
| D:18 | batch 2: 1.08 vs 1.33, thrown away | 1.0833 / 1.3333, margin −0.25, reject | `calls.csv:2` | [R] | MATCH | Batch 2 = B′ is the rewrite's **own** batch. The real gate rejected it; it was "kept" only on the batch it was not written from. |
| D:22 | 2,292 rewrites; agree 53.9%; chance 54.4% | 2292; 0.5393; 0.5442 | `calls.csv` → `article_todos_2026-10-08.md:81` (agreement); chance is new; fn `a2_cross_batch` | [R]/[C] | MATCH | IFBench, one-step. The same freshly re-run parent P_B is used on both batches. Zero margins count as rejects (838 on B, 677 on B′). |
| D:30 | "about three examples" | as D:7 | — | [R] | MATCH | as D:7 |
| D:42 | "five ways to score"; "none of the five" | 0/5 survive (not recomputed) | `findings_summary.md:226, 35` | cited | MATCH* (cited only) | IFBench, full-object rescreen (`rescreen_wave1.md`). Not reproduced in this pass (OQ 7). |
| D:44 | kept 34% / 31% / 37% (intact / deleted / generic) | 51/150 = 0.340, 47/150 = 0.313, 55/150 = 0.367; McNemar exact p 0.627 (i vs iii), 0.652 (i vs ii) | `analysis/ablation/calls.csv` → `ablation/results.md:30-32, 36-37`; `findings_summary.md:51`; fn `x_ablation` | [R] | MATCH | One-step keep rate, IFBench, 150 paired batches. 37% is 36.7%. The `accept_today` column's 52 and 56 (arms i and iii) include one float tie each (s6_it4). Removing it gives the committed 51 and 55 (OQ 8, resolved). |
| D:46 | "effects above roughly the size these tests could see" | see D:102 | — | — | — | — |
| D:54 | "three Wikipedia articles", "three search steps" | not checked (task description) | HoVer 3-hop: `gepa_result.json` keys `trainset_threehop_ids` / `valset_threehop_ids` | — | not a result | — |
| D:56 | "+0.027, with an interval that excludes zero" | +0.027435, 8-run cluster CI [+0.0149, +0.0415], perm p 0.0177. **Per example: +0.009145 [+0.00496, +0.01385]** [C] | `hover_swap/pairs/*/draws.jsonl` → `hover_swap/results.md:11`; fn `x_hover_swap` | [R]/[C] | MATCH | One-step specificity, HoVer only. **Units: batch total on a 0–3 scale**, because `hover_swap_analysis.py:131` divides the integer-thirds 3-example margin by 3. Divide by 3 again for a per-example (0–1) value, comparable to the per-claim endpoint. |
| D:56 | carry-over "too close to call" | transfer +0.016918, CI [−0.0040, +0.0367], p 0.31195 | `hover_swap/results.md:12`; `article_todos:59` | [R] | MATCH | The p depends on the RNG chain: with a fresh seed it is 0.30755 (`article_todos:60`). |
| D:58 | 108 candidate scoring rules; p = 0.0013 | 108 cells; p 0.0013, β 0.0379395, CI [0.010447, 0.070305] | `_perm_raw.json` "0" → `hover_screen/results.md:91`; `WEBSITE-2026-09-28.md:178, 188`; fn `e_screen` | [R] | MATCH | The p is the cell's own p, uncorrected for 108 cells. That uncorrected p is exactly what D:62 calibrates. |
| D:58 | three arms, eight paired runs each | 24 runs, one shared seed program (D1) | `analysis/state_dep/runs/{B,C,T}_seed{0..7}` | [R] | MATCH | B = baseline GEPA, C = cost-matched control, T = treatment (`findings_summary.md:245-246`). |
| D:60 | difference −0.001, p = 0.97 | T−C = −0.001111, exact sign-flip p 0.96875 (n = 8) | `runs/*/endpoints.json` → `WEBSITE-2026-09-28.md:69`; fn `d_three_arm` | [R] | MATCH | Endpoint units, 150-claim test split, n = 8. |
| D:62 | "200 times"; "43 of 200"; "about 1 in 5" | 43/200 = 0.215 | `_perm_raw.json` → `article_todos:36` ([C] there); fn `e_screen` | [R] | MATCH | 43 counts \|β\| ≥ observed, either sign. Same sign only: 20/200 (1 in 10). Any survivor: 134/200 (`03_permutation_calibration.md:44`). Comparator: OQ 4. |
| D:64 | the experiment could detect "about 0.063" | MDE 0.063318 (reproduced with `mde_sim.find_mde`, rng 20260709) | `stage1_backfill_endpoints.json` → `state_dep/plan.md:345`; `results.md:10`; fn `x_mde` | [R] | MATCH | Endpoint units; assumes ρ = 0. The ledger's "upper bound" gloss is contested (`findings_summary.md:363`). |
| D:64 | effect it was designed around was "closer to 0.02" | **0.02738** pre-registered (1.4432 × β / 2); 0.02311 with realized D 1.2185. **Per example: 0.009126 pre-registered, 0.007705 realized** [C] | `plan.md:357`; `manipulation_check_2026-09-28.md:178`; fn `d_three_arm` | [R]/[C] | **FIX → 0.027 (batch total), i.e. 0.009 per example** | β, specificity and the planned effect are **batch totals on 0–3** (`hover_swap_analysis.py:131`, `hover_screen/screen_part05_outcomes.py:70`). The 0.063 MDE and the endpoint are **per-claim means on 0–1**. So `plan.md:357`'s "MDE is 2.3x the implied one-step effect" (0.06332 / 0.02738 = 2.31, reproduced) compares across scales. On one per-example scale the MDE is **6.9×** the planned effect (8.2× the realized one). It is still a one-step effect against an endpoint MDE. The pre-registered comparison was MDE 0.06332 vs trigger 3 × (Dβ/2) = 0.08213 (`plan.md:348`), which also crosses scales. Only the post-hoc realized value is "closer to 0.02". |
| D:64 | "In 5 of the 24 runs" the final prompt was the starting prompt | 5/24: B_seed2, C_seed1, C_seed7, T_seed2, T_seed5 | `runs/*/endpoints.json` `sel_returned_seed_prompt`; fn `d_three_arm` | [C] | MATCH | 2 of the 5 (B_seed2, C_seed1) are ties on the selection split, broken toward index 0 (`score_candidates.py:9`). "Best" means the §8b selection-split argmax. |
| D:74 | IFBench 53.9% vs 54.4%; HoVer 54.7% vs 54.3% | 0.5393 / 0.5442; 0.5466 / 0.5433 | `article_todos:81-82` (agreement); chance [C]; fn `a2_cross_batch`, `b_hover` | [R]/[C] | MATCH | HoVer's A-side baseline is the logged Stage-1 parent score; its B-side is a fresh run (`article_todos:113-117`). HoVer verdicts use exact thirds; under the float gate, 792/1458 agree (`article_todos:121`). |
| D:75 | different rewrites, same examples: 72% vs 55% chance | 0.7234 vs 0.5485 | `calls.csv`; 0.7234 = 1 − (2/3)·0.4149 (`verification_postswap.md:51`); 0.5485 from p = 0.3442 (`:13`); fn `a3_siblings` | [C] | MATCH | **IFBench only.** "Different rewrites" = the 3 sibling draws from one reflection prompt, judged on their own batch. HoVer siblings, new here: 0.691 vs 0.532 (B4). |
| D:79 | every kept rewrite later scored on 150 examples | all 145 accepted have a full 150-item valset eval | `logs/baseline_*.jsonl` `valset_evaluated`; fn `c_validation` | [R] | MATCH | IFBench only. |
| D:79 | "Half of them, 73 of 145, were no better" | 73/145 = 0.503 (all 10 runs); **53/115 = 0.461 at b = 3**; 20/30 at b = 1 | `article_todos:148-150`; fn `c_validation` | [R] | **FIX (scope)** | 73/145 pools the 2 b = 1 runs. If the article's frame is three-example batches, the value is 53/115 (46%). No ties ("≤" and "<" agree). |
| D:91 | "Two open issues on the GEPA repo" | — | not in any committed file here (external) | — | NOT FOUND | Out of scope for this repo; cite the issue URLs directly. |
| D:93 | "each round costs about twice the batch size in model calls" | keep-or-discard gate: 2337/397 = 5.89 calls per evaluated iteration at b = 3 (1.77 at b = 1). **All calls**: 53.4 per iteration at b = 3, of which validation is 88.8% | `c_budget_by_run.csv`; fn `c_validation` (C5) | [C] | **FIX (scope)** | The statement is true only for the minibatch gate. Full-valset scoring of kept rewrites is 90.0% of the IFBench budget (23,250 / 25,829). The proposer LM call is not counted. |
| D:101 | swap: within-pair permutation tests; three-arm: exact sign-flip over 8 paired runs; intervals resample the 8 runs | perm_p with 20,000 Monte-Carlo flips (`hover_swap_analysis.py:90-95`); exact 2⁸ sign-flip (D6); swap CIs are 8-run cluster bootstrap | — | [R] | MATCH | The swap permutation test is Monte Carlo, not exact. The three-arm CIs at `WEBSITE:69` are BCa over 8 seeds. |
| D:102 | IFBench swap could see down to 0.033 | 0.033 = Stage-0 constant `MDE_SPEC[3]` | `scripts/batch_swap_v2_analysis.py:22`; `batch_swap_v2/results.md:8, 11` | cited | MATCH* | Not recomputed from data (OQ 7). |
| D:102 | feedback deletion about 10 to 12 points | Stage-0 analytic estimate | `ablation/plan.md:39`; `ablation/results.md:17` | cited | MATCH* | Not recomputed (OQ 7). Units: percentage points of keep rate. |
| D:102 | three-arm about 0.063 | 0.063318 | as D:64 | [R] | MATCH | as D:64 |
| D:103 | three-arm endpoint is a 150-claim held-out test | test_split n = 150 | `runs/*/endpoints.json` `test_split.n` | [R] | MATCH | — |
| D:104 | rejected rewrites never scored on the validation set | true in all 10 runs: valset events exist only for the seed and accepted children (asserted). 342 rejected rewrites (267 at b = 3) have their text in `proposal_end.new_instructions` | fn `c_validation` (C4) | [C] | MATCH | The texts exist, so a comparison point could be built at a cost. Not scored here. |
| D:105 | agreement-beyond-chance −0.01, interval [−0.05, +0.04] | κ −0.0108. Run-cluster CI [−0.046, +0.040] → [−0.05, +0.04]. Per-child [−0.052, +0.030] → [−0.05, +0.03]. Per-pair [−0.062, +0.040] → [−0.06, +0.04] | fn `a2_cross_batch` | [C] | MATCH **if labeled run-cluster** | The interval matches only the 8-run cluster bootstrap. Name the resampling unit; 8 clusters makes it optimistic. |
| D:106 | IFBench: gpt-4.1-mini task, gpt-4.1 rewrites; HoVer: gpt-4.1-mini both | same, from config bytes | `logs/baseline_*.config.json:8-9` → `article_todos:228-237`; `runs/*/config.json` → `WEBSITE:285`; fn `x_models` | [R] | MATCH | These are the configs' declared settings, not an echo of what the API served. |
| D:107 | HotpotQA: +0.062 on "the examples it optimized against", +0.0013 on held-out test | +0.062367 (range +0.0206 to +0.1057) and +0.001291 over the 21 Exp 1/1b cells with ≥ 1 accept; 11/21 above seed on test | per-run `run_log.txt`, `test_eval.json`, `cell_summary.json` in `~/Desktop/frontier-gepa` (all 48 tracked, HEAD dbfbaa3). The numbers are **stated only in untracked** `frontier-gepa/docs/BASELINE-CHECK-2026-09-29.md:201-202`; `git log --all -S/-G` finds no commit on any branch; fn `f_hotpot` | [C] | **FIX (label)** + not cite-safe until the doc is committed | +0.062 is a **max-selected** score on the 75-item D_pareto validation set, the set used to pick the returned program. It is not the set GEPA "optimized against": acceptance runs on A = 20 batches and reflection on D_feedback (`BASELINE-CHECK:168-169, 206-212`). Test: 300 items. Exp 3 is excluded from the 21. |
| D:108 | "One run carries the three-arm result. Without it, the treatment arm looks slightly worse than baseline." | Seed 4 dropped (n = 7): **T−C −0.015556** (p 0.078125); **T−B −0.027302** (p 0.046875). With seed 4: T−C −0.001111, T−B −0.012778 (p 0.484) | `endpoints.json` → `WEBSITE:122, 135, 140-141`; fn `d_three_arm` | [R] | **FIX (label)** | "Baseline" means arm B in the ledger (`findings_summary.md:245`), so "slightly worse than baseline" is −0.027 with p 0.047, and T−B is already negative with seed 4 included. The −0.016 contrast is vs the control C. Seed 4's T−C difference is +0.100. Post hoc. |
| D:109 | "Five kept rewrites on HoVer were exact ties" | 5 = 2 Stage-1 (seed0 i = 31, seed5 i = 23) + 3 three-arm (B_seed0 i = 26, B_seed4 i = 19, C_seed3 i = 7) | `gepa_result.json` `full_program_trace`; Stage-1 → `article_todos:264-269`; fn `d_three_arm` (D7) | [R]+[C] | MATCH | Across 32 HoVer runs (8 Stage-1 + 24). One-step minibatch gate; float sum vs exact thirds. **Also an IFBench float tie:** one batch (s6_it4), three calls (arms i, i_rep, iii), accepted at 1.5 vs 1.5 in the feedback ablation's re-gate. `scripts/run_ablation.py:153-155` sets `accept_today = int(c_sum > p_sum)` on unrounded sums but writes them rounded to 4 dp (`analysis/ablation/calls.csv:380, 382, 383`; fn `x_ablation`). These are not GEPA-run accepts, and the committed ablation rates already exclude them. |
| D:115 | live experiment cost "$188.91" | $188.9143 = test split 3.2336 + smoke 5.1942 + 24 runs and scoring 132.7603 + dose 8.3355 + backfill 39.3907 | `test_pool_summary.json:7`, `markers/SMOKE.DONE:25`, `liverun_ledger.json` (48 rows), `logs/dose_compute.out:145, 574, 739`, `logs/backfill.log:13, 129`, `backfill.out:7` → `WEBSITE-2026-09-28.md:305-313`; fn `x_cost` | [R] | **FIX → "about $189, a lower bound"** | The dose-control pass is unrecorded (`WEBSITE:310`), and the $1.384 backfill term is a last-printed meter. This is the state-dependent HoVer experiment only, not the whole project. |
| D:117 | "Six times a number looked correct while measuring less than it claimed" | — | no committed list found | — | NOT FOUND | OQ 10. |

---

## Table B: new numbers from Parts A–E (and checks)

All rows are in `values.csv` under the same ids.

### A. IFBench batch-swap v2 (`analysis/ablation/batch_swap_v2/calls.csv`)

| id | value | ref | status | tag | note |
|---|---|---|---|---|---|
| A0 arm semantics | R_B reflects on B's objects, R_Bp on B′'s | — | confirmed | [R] | `scripts/batch_swap_v2_run.py:220-223` |
| A1 row 1 | s4_it63 / s4_it47 / R_Bp / draw 0. On B: 1.0 vs 0.75, keep. On B′: 1.0833 vs 1.3333, reject | as given | MATCH | [R] | Written from **B′**, so it was rejected by its own-batch gate. |
| A2 2×2 (acc,acc / acc,rej / rej,acc / rej,rej) | 272 / 468 / 588 / 964 | same | MATCH | [R] | `article_todos:81` |
| A2 agreement | 0.539267 | 0.5393 | MATCH | [R] | |
| A2 accept rate B / B′ | 0.322862 / 0.375218 | — | — | [C] | |
| A2 chance | 0.544207 | 0.5442 | MATCH | [C] | |
| A2 κ | −0.010839 | −0.0108 | MATCH | [C] | |
| A2 κ CI, children (2292) | [−0.05162, +0.02981] | [−0.052, +0.030] | MATCH | [C] | rng 20261015 |
| A2 κ CI, pairs (382 B_id) | [−0.06172, +0.03953] | [−0.061, +0.040] | MATCH | [C] | rng 20261016 |
| A2 κ CI, runs (8 seeds) | [−0.04578, +0.03968] | [−0.046, +0.040] | MATCH | [C] | rng 20261017 |
| A3 sibling agreement, own batch (764 cells) | 0.723386 | 0.7234 | MATCH | [C] | |
| A3 pooled own-batch accept rate | 0.344241 (789/2292) | 0.3442 | MATCH | [R] | `verification_postswap.md:13` |
| A3 sibling chance, own batch | 0.548522 | 0.5485 | MATCH | [C] | p² + (1−p)² |
| A3 non-unanimous cell share | 0.414921 | 0.4149 | MATCH | [R] | `verification_postswap.md:51` |
| A3 identity | 1 − (2/3)·0.4149 = 0.7234, exact on the unrounded share | 0.7234 | MATCH | [C] | A unanimous cell agrees on 3/3 pairs and a 2–1 cell on 1/3, so the mean is 1 − (2/3)·(non-unanimous share). |
| A3 identity | 0.3442² + 0.6558² = 0.548547 | 0.5485 | MATCH | [C] | |
| A3 sibling agreement / chance, other batch | 0.725131 / 0.542726 (p = 0.353839) | 0.7251 / 0.5427 | MATCH | [C] | |
| A4 zero margins: B / B′ / own batch | 838 / 677 / 769 | same | MATCH | [R]/[R]/[C] | `article_todos:94`. Smallest nonzero \|margin\| is 0.0333. |

**A5: keep rate by the parent's batch total** (`fig_gate_headroom.csv`). [C]

| parent sum bin | own-batch n | own-batch keep | all-verdicts n | all-verdicts keep |
|---|---|---|---|---|
| [0, 0.5) | 90 | 0.756 | 180 | **0.728** (ref 0.728, MATCH) |
| [0.5, 1) | 492 | 0.476 | 984 | 0.492 |
| [1, 1.5) | 732 | 0.361 | 1464 | 0.387 |
| [1.5, 2) | 576 | 0.278 | 1152 | 0.266 |
| [2, 2.5) | 279 | 0.190 | 558 | 0.167 |
| [2.5, 3] | 123 | 0.081 | 246 | **0.073** (ref 0.073, MATCH) |

- Own-batch uses `parent_B_sum` for R_B and `parent_Bp_sum` for R_Bp (2,292 verdicts).
- All-verdicts uses both batches of every row (4,584 verdicts).
- Parent sums repeat across the 6 rows of a pair, so the rows are not independent.

### B. HoVer swap (`analysis/ablation/hover_swap/pairs/*`, exact integer thirds via `hover_swap_analysis.thirds/load`)

| id | value | ref | status | tag |
|---|---|---|---|---|
| B1 2×2 | 184 / 334 / 327 / 613 | same | MATCH | [R] (`article_todos:82`) |
| B1 agreement / chance / κ | 0.546639 / 0.543277 / +0.007362 | 0.5466 / 0.5433 / 0.007 | MATCH | [R]/[C]/[C] |
| B1 κ CI, pairs (243) | [−0.05513, +0.06963] | [−0.057, +0.070] | MATCH | [C] (rng 20261025) |
| B1 κ CI, seeds (8) | [−0.05533, +0.06247] | [−0.055, +0.059] | MATCH (within MC tol; upper bound +0.0035 off) | [C] (rng 20261026) |
| B2 match_exact = true | 708 children (118 pairs): agreement 0.557910, chance 0.565443, κ −0.0173 | 708; 0.558 vs 0.565 | MATCH | [C] |
| B2 match_exact = false | 750 children (125 pairs): agreement 0.536, chance 0.526123, κ +0.0208 | — | — | [C] |
| B3 ties A_e / B_e | 506 / 560 | same | MATCH | [R] (`article_todos:103`) |
| B4 HoVer sibling agreement / chance, own batch | 0.691358 / 0.532200 (486 cells, p = 0.3731) | — | — | [C] (now in `fig_agreement`) |

### C. IFBench validation cost (the 10 completed `max_metric_calls == 2500` baseline runs; `c_budget_by_run.csv`, `fig_budget.csv`)

| quantity | all 10 | b = 3 (8) | b = 1 (2) | tag |
|---|---|---|---|---|
| C1 accepted / did not beat parent (≤) / rate | 145 / 73 / 0.5034 | 115 / 53 / 0.4609 | 30 / 20 / 0.6667 | [R] (`article_todos:148-150`), all MATCH; 0 ties |
| C2 valset calls / total metric calls / share | **23,250 / 25,829 / 0.9002** (MATCH) | 18,450 / 20,787 / 0.8876 | 4,800 / 5,042 / 0.9520 | [C] |
| C3 validation: seed prompt | 1,500 | 1,200 | 300 | [C] |
| C3 validation: kept, beat parent | 10,800 | 9,300 | 1,500 | [C] |
| C3 validation: kept, did not beat | 10,950 | 7,950 | 3,000 | [C] |
| C3 everything else (= Σ `evaluation_end` scores; checked equal) | 2,579 | 2,337 | 242 | [C] |
| C4 rejected children / with text in `proposal_end.new_instructions` | 342 / 342 | **267 / 267** (MATCH) | 75 / 75 | [C] |
| C5 gate calls per evaluated iteration | — | 5.887 (2337/397) | 1.766 (242/137) | [C] |
| C5 all metric calls per `total_iterations` | — | 53.44 (20787/389) | 37.35 (5042/135) | [C] |
| C6 validation of kept rewrites, share of all metric calls | 0.8421 (21,750 / 25,829) | 0.8298 (17,250 / 20,787) | — | [C] |
| C6 validation of kept rewrites that did not beat their parent, share of all metric calls | 0.4239 (10,950 / 25,829) | 0.3825 (7,950 / 20,787) | — | [C] |

**C7: what happened to the 53 b = 3 accepted children that did not beat their parent.** [C] fn `c_validation`. Per-run columns are in `c_budget_by_run.csv`.

| b = 3 accepted children | n | later picked as parent (`candidate_selected`) | selection events | had an accepted child | the run's returned best (`optimization_end.best_candidate_idx`) |
|---|---|---|---|---|---|
| did not beat parent | **53** | **38** | 135 | **25** | **0** (mechanical: see C8) |
| beat parent (comparison) | 62 | 40 | 177 | 27 | 8 |

- 53 + 62 = 115 (asserted). Every selection event counted comes after the child's acceptance (asserted).
- **C8. The "0 returned" is mechanical, not a finding.** In all 8 b = 3 runs (and all 10), `optimization_end.best_candidate_idx` is the unique argmax of the exact valset means. A child scoring at or below its parent has its parent above it, so it can never be returned.
- **C9. Lineage of the returned best** (`c_lineage.csv`: one row per node with its exact valset mean; fn `c_lineage_noise`). Walking each run's returned best back through `parent_ids` to the seed, **4 of 8** b = 3 chains pass through at least one accepted child that did not beat its parent: seeds 1, 3, 6 and 7 (ref 4, MATCH). No b = 1 chain does, so it is 4 of 10 across all runs. Chain lengths in accepted steps:

  | run | b=3 s0 | s1 | s2 | s3 | s4 | s5 | s6 | s7 | b=1 s0 | s1 |
  |---|---|---|---|---|---|---|---|---|---|---|
  | accepted steps, seed → returned | 1 | 4 | 2 | 3 | 2 | 1 | 6 | 3 | 1 | 0 (returned the seed) |
  | contains a did-not-beat child | no | **yes** (2) | no | **yes** (1) | no | no | **yes** (3) | **yes** (1) | no | — |

  Example, seed 6: 0 (0.5393) → 1 (0.5410) → 2 (0.5246, did not beat) → 5 (0.5377) → 6 (0.5296, did not beat) → 8 (0.5057, did not beat) → 11 (0.5581).

- "Beat parent" is decided in exact rationals on the full 150-item valset, as `article_todos` item 4 does.
- `optimization_end.total_iterations` is one fewer than the number of iterations that log gate evaluations, in every run.

### N. IFBench validation noise and kept-rewrite improvement (fn `c_lineage_noise`; 10 baseline runs)

**N1. The seed prompt's valset mean, one evaluation per run.** [C] The seed prompt is identical in all 10 runs (one sha256 of `optimization_start.seed_candidate`), and so are the 150 valset ids. The spread across runs is therefore task-LM resampling noise in a single 150-item valset mean.

| run | b=3 s0 | s1 | s2 | s3 | s4 | s5 | s6 | s7 | b=1 s0 | b=1 s1 |
|---|---|---|---|---|---|---|---|---|---|---|
| seed valset mean | 0.5152 | 0.5404 | 0.5420 | 0.5050 | 0.5352 | 0.5324 | 0.5393 | 0.5251 | 0.5314 | 0.5598 |

| statistic | value | ref | status |
|---|---|---|---|
| mean | 0.53260 | — | — |
| sd (ddof 1) | **0.015136** | 0.015 | MATCH |
| min / max | 0.50500 / 0.55978 | 0.505 / 0.560 | MATCH |

**N2. Kept-rewrite improvement, b = 3 (115 accepted children).** [C] d = exact child valset mean − exact parent valset mean.

| statistic | value | ref | status |
|---|---|---|---|
| mean d | **+0.001196** | +0.001 | MATCH |
| median d | +0.002444 | — | — |
| run-cluster bootstrap 95% CI of the mean (8 runs, 10,000 resamples, rng 20261035) | **[−0.00200, +0.00455]** | [−0.002, +0.005] | MATCH (MC tol 0.005, observed gaps ≤ 0.0005) |
| share with \|d\| < √2 × 0.015136 = 0.02141 | **0.6957** (80/115) | 0.70 | MATCH |

- √2 × sd is the sd of the difference between two independent evaluations of one prompt. So about 70% of kept rewrites differ from their parent by less than a same-prompt re-evaluation typically would.
- Each d is a difference of two single noisy evaluations.
- The parent's valset mean is the one logged in the same run, not a fresh re-evaluation.

### D. HoVer three-arm (`analysis/state_dep/runs/{B,C,T}_seed{0..7}`)

| id | value | ref | status | tag |
|---|---|---|---|---|
| D1 distinct sha256 of `program_candidates[0]` over 24 runs | 1 (e49ddc8e…) | 1 | MATCH | [C] |
| D2 runs returning the seed prompt | B_seed2, C_seed1, C_seed7, T_seed2, T_seed5 | same | MATCH | [C] |
| D2 tie-broken toward index 0 | 2: B_seed2 (tied {0, 5}), C_seed1 | 2 | MATCH | [C] (`score_candidates.py:9`) |
| D2 seed-prompt test mean / sd (ddof 1), n = 5 | 0.575111 / 0.011044 | 0.5751 / 0.0110 | MATCH | [C] (`d2_seed_prompt_runs.csv`) |
| D3 arm B mean | 0.599167 | 0.599167 | MATCH | [R] (`results.md:130`) |
| D3 arm B − seed-prompt mean | **+0.024056** | — | — | [C] |
| D4 `selection_means[0]` over 24 runs: min / max / sd / mean | 0.506667 / 0.613333 / 0.026738 / 0.561389 | 0.5067 / 0.6133 / 0.0267 | MATCH | [C] |
| D4 index 0 scored fresh, cache off | confirmed | — | — | `score_candidates.py:8, 100, 108-110`; `eval_split.py:233-234` |
| D5 planned one-step effect 1.4432 × β / 2 | 0.027377 | 0.02738 | MATCH | [R] (`plan.md:357`) |
| D5 realized-dose version 1.2185 × β / 2 | 0.023115 | — | — | [C] |
| D5 per-example equivalents (÷ 3): planned / realized | 0.009126 / 0.007705 | — | — | [C] |
| D5 MDE / planned effect, as in `plan.md:357` (cross-scale) | 2.3128 | 2.3 | MATCH | [R] |
| D5 MDE / planned and MDE / realized, both per example | 6.938 / 8.218 | — | — | [C] |
| D5 realized gate trigger 3 × 1.2185 × β / 2 | 0.069344 | 0.06934 | MATCH | [R] (`manipulation_check:288`; GATE_K = 3 at `mde_sim.py:35`) |
| D6 T−C, n = 8: mean / exact p | −0.001111 / 0.96875 | same | MATCH | [R] (`WEBSITE:69`) |
| D6 T−C, seed 4 dropped: mean / p (n = 7) | −0.015556 / 0.078125 | same | MATCH | [R] (`WEBSITE:122, 135, 140`) |
| D6 T−B, seed 4 dropped: mean / p | −0.027302 / 0.046875 | same | MATCH | [R] (`WEBSITE:135, 140-141`) |
| D6 C−B, seed 4 dropped: mean / p | −0.011746 / 0.15625 | same | MATCH | [R] |
| D6 T−B / C−B, n = 8: mean / p | −0.012778 / 0.484375; −0.011667 / 0.1328125 | — | — | [C] (C−B is also at `findings_summary.md:275`) |
| D6 seed-4 differences T−C / T−B / C−B | +0.100 / +0.0889 / −0.0111 | +0.100 (T−C) | MATCH | [R]/[C] |
| D7 float-tie accepts: Stage-1 / three-arm / total | 2 / 3 / 5 | 2 / 3 / 5 | MATCH | [R]/[C]/[C] |

D3 caveats:
- n = 8 against n = 5.
- The 5 runs are selected precisely because the seed won selection, so their mean is not an unselected seed evaluation.
- Both use the same 150-claim test split.
- The spread among the 5 (sd 0.011) is task-LM resampling of one prompt.
- Endpoint units.

D5 caveat: these are **one-step specificity units**: batch totals on 0–3 (`hover_swap_analysis.py:131`; `hover_screen/screen_part05_outcomes.py:70`). The endpoint and the MDE are per-claim means on 0–1. `plan.md:357`'s 2.3× compares across the two scales; on a single per-example scale it is 6.9×.

### E. Screen calibration (`analysis/review_response_2026-08-26/_perm_raw.json`; `fig_screen_null.csv`)

| id | value | ref | status | tag |
|---|---|---|---|---|
| E0 identity survivor / β | knn_emb_fb_min / 0.0379395028680125 | same | MATCH | [R] |
| E1 ≥ 1 survivor | 134/200 | 134 | MATCH | [R] (`03_permutation_calibration.md:44`) |
| E1 survivor with \|β\| ≥ observed | 43/200 | 43 | MATCH | [R] (vs `article_todos:36`) |
| E1 same-sign survivor ≥ observed | 20/200 | 20 | MATCH | [R] (`WEBSITE:176`) |
| E2 per-permutation max β (108 cells) equals the stored `max_beta` | 200/200 | — | — | [C] |
| E2 null maxima ≥ 0.0379395 | **93/200** | 93 | MATCH | [R] (`03:68`) |
| E2 observed percentile in the null-max distribution | 0.535 (strict < and ≤ agree) | — | — | [C] |
| E2 observed max β across all 108 cells; null maxima ≥ it | 0.059229; 17/200 | 17 | MATCH | [R] (`03:62-67`) |
| E3 shuffles with no full-rule survivor | 66/200 | 66 (= 200 − 134) | MATCH | [C] (`fig_screen_null_survivors.csv`) |
| E3 shuffles whose strongest survivor has \|β\| ≥ observed | 43/200 | 43 | MATCH | [C] (the same count as E1, now per shuffle) |

### R. Revision numbers (fn `r1_hover_gepa_gain` … `r13_gate_power`, `scripts/article_numbers.py:1020-1286`; 2026-10-17)

Every row was checked against the revision briefs' references (v1: R1-R8; v2: R9-R13 and R3's sd of d) to 4 dp, or to
the reference's own precision where it gives fewer digits: 105 rows with a reference, **103 MATCH, 2 MISMATCH** (R13).

| id | value | ref | status | tag | note |
|---|---|---|---|---|---|
| R1 stock GEPA's gain on HoVer (arm B, 8 runs, minus the 5 seed-prompt runs) | +0.024056 | +0.0241 | MATCH | [C] | `runs/B_seed*/endpoints.json`; `d2_seed_prompt_runs.csv` |
| R1 Welch 95% interval | [−0.001495, +0.049607] | [−0.0015, +0.0496] | MATCH | [C] | t from `t_ppf` |
| R1 Welch p / df | 0.062237 / 9.6945 | 0.0622 / 9.69 | MATCH | [C] | two-sided |
| R2 per-run mean of d, s0 … s7 | +0.0074, −0.0038, −0.0041, −0.0030, +0.0031, −0.0011, +0.0014, +0.0090 | same | MATCH (8/8) | [C] | N2's 115 d, grouped by run |
| R2 mean of run means | +0.001116 | +0.0011 | MATCH | [C] | |
| R2 95% t-interval over the 8 run means (df 7) | [−0.003098, +0.005329] | [−0.0031, +0.0053] | MATCH | [C] | replaces N2's run-cluster bootstrap in the post |
| R3 pooled sd of a 150-item mean | 0.013220 | 0.0132 | MATCH | [C] | per-item variance across N1's 10 seed evaluations (ddof 1), sqrt(sum)/150 |
| R3 sd of the 115 d (ddof 1) | 0.021080 | 0.0211 | MATCH | [C] | reference completed by brief v2 |
| R3 √2 × pooled sd; √2 × N1 sd | 0.018696; 0.021406 | 0.0187; 0.0214 | MATCH | [C] | sd of a difference of two scorings |
| R3 share of \|d\| below each | 71/115 = 0.6174; 80/115 = 0.6957 | 0.6174; 0.6957 | MATCH | [C] | |
| R4 first `evaluation_end` per b = 3 iteration is the `candidate_selected` parent | 397/397 | 397/397 | MATCH | [C] | `logs/baseline_seed*_b3_*.jsonl` |
| R4 same parent, same B, logged vs fresh `parent_B_sum` (382 pairs, 1/60 grid): tie / fresh above / fresh below | 174 (0.4555) / 103 (0.2696) / 105 (0.2749) | same | MATCH | [C] | `batch_swap_v2/calls.csv` |
| R4 fresh − logged: mean / sd (ddof 1) | +0.015881 / 0.411538 | +0.0159 / 0.4115 | MATCH | [C] | batch total, 0 to 3 |
| R5 IFBench own-batch margin (2,292, 1/60 grid): above / tie / below | 789 (0.3442) / 769 (0.3355) / 734 (0.3202) | same | MATCH | [C] | R_B: `margin_on_B`, R_Bp: `margin_on_Bp` |
| R5 IFBench own-batch margin: mean / sd | +0.004305 / 0.435091 | +0.0043 / 0.4351 | MATCH | [C] | |
| R5 HoVer own-batch margin (1,458, exact thirds): above / tie / below | 544 (0.3731) / 515 (0.3532) / 399 (0.2737) | same | MATCH | [C] | SAME on A_e vs logged parent; SWAP on B_e vs fresh parent |
| R5 HoVer own-batch margin: mean | +0.044353 | +0.0444 | MATCH | [C] | |
| R6 screen family-wise p | 43/200 = 0.215 | 0.215 | MATCH | [C] | from E1/E3 |
| R6 IFBench swap specificity, naive-pair 95% CI | [−0.0149, +0.0257] | same | MATCH | cited | `analysis/ablation/batch_swap_v2/results.md:8` |
| R6 HoVer swap specificity / transfer, naive-pair 95% CI | [+0.0048, +0.0501] / [−0.0149, +0.0489] | same | MATCH | cited | `analysis/ablation/hover_swap/results.md:11-12` |
| R6 feedback ablation: gate-margin deltas; same-arm repeat flips | −0.016 (p 0.64), −0.013 (p 0.71); 32% | same | MATCH | cited | `analysis/ablation/results.md:39, 43-44` |
| R6 sibling best-of-3: own margin of the selected draw; selection lift; its CI | +0.2298; +0.0059; [−0.0059, +0.0201] | same | MATCH | cited | `analysis/verification_postswap.md:16-18` |
| R7 IFBench setup: n_train / n_val / max_metric_calls / gepa | 150 / 150 / 2500 / 0.1.1 | same | MATCH | [C] | `logs/baseline_seed*_b*.config.json` (10 study runs) |
| R7 HoVer three-arm: n_train / n_val / max_metric_calls / gepa / selection / test | 100 / 10 / 300 / 0.0.27 / 50 / 150 | same | MATCH | [C] | `runs/*/config.json`, `endpoints.json`; `state_dep/results.md:141-146` |
| R7 HoVer Stage-1: max_metric_calls / n_train / n_val | 300 / 100 / 10 | n/a / 100 / 10 | MATCH (n_train, n_val) | [C] | `scratch/hover_stage1/stage1_seed*/run_summary.json` (`mm`) |
| R7 HoVer Stage-1 gepa version | not recorded; implied 0.0.27 | n/a | n/a | [C] | no run file records it; `run_seeds.sh:7` runs `scratch/hover_probe/.venv` (gepa 0.0.27) |
| R8 frontier-gepa Exp 3 runs, committed, non-smoke | 12 (4 arms × 3 seeds) | 12 | MATCH | [C] | `git ls-files experiments/exp3_curriculum` |
| R8 Exp 3 has no validation record | stated | stated | MATCH | cited | frontier-gepa `docs/BASELINE-CHECK-2026-09-29.md:231-235`; the doc does not state the count 12 |
| R9 first kept rewrite minus the seed prompt, per b = 3 run (parent asserted = candidate 0), s0 … s7 | +0.0218, −0.0186, +0.0030, +0.0469, +0.0090, +0.0264, +0.0017, −0.0034 | same | MATCH (8/8) | [C] | exact valset means; the one comparison where the parent was not picked on its own validation score |
| R9 mean / positive / 95% t-interval (df 7) | +0.010847 / 6 of 8 / [−0.006110, +0.027804] | +0.0108 / 6 / [−0.0061, +0.0278] | MATCH | [C] | |
| R10 IFBench, different arms' draws on the same batch (9 pairings per pair): on B | 0.716696 vs chance 0.562681 | 0.7167 / 0.5627 | MATCH | [C] | chance pa·pb + (1−pa)(1−pb) from the two arms' accept rates on that batch |
| R10 IFBench, on B′ | 0.684119 vs 0.530648 | 0.6841 / 0.5306 | MATCH | [C] | |
| R10 IFBench, pooled over B and B′ | 0.700407 vs 0.545340 | 0.7004 / 0.5453 | MATCH | [C] | pooled chance uses each arm's accept rate over both batches |
| R10 HoVer, SAME vs SWAP draws, pooled over A_e and B_e (exact thirds) | 0.700732 vs 0.543260 | 0.7007 / 0.5433 | MATCH | [C] | |
| R11 three-arm leave-one-seed-out paired mean (7 seeds), range: T − C / T − B / C − B | [−0.015556, +0.006984] / [−0.027302, −0.005714] / [−0.017143, −0.008254] | [−0.0156, +0.0070] / [−0.0273, −0.0057] / [−0.0171, −0.0083] | MATCH | [C] | min with seed 4 left out (T − C, T − B); `runs/*/endpoints.json` |
| R12 expected b = 3 lineages containing a not-beat step, if each step fails independently with p = 53/115 | 5.918 of 8 (observed 4, C9) | 5.92 | MATCH | [C] | chain lengths 1,4,2,3,2,1,6,3 rebuilt from the logs (MATCH vs C9) |
| R13 σ per example = sd of the 3-example margin / √3, from R5 | 0.251200 | 0.2512 | MATCH | [C] | normal approximation; examples independent; ties ignored |
| R13 σ per example from R4 (fresh − logged parent) | 0.237602 | none (lost in transmission; inferred from the brief's ranges) | n/a | [C] | |
| R13 pass probability at b = 150 for a rewrite 0.01 better per example, Φ(δ√b/σ): σ from R5 / R4 | 0.6871 / 0.6969 | 0.688 / 0.697 | **MISMATCH** / MATCH | [C] | R5 path: σ matches the reference, so the gap opens at Φ: Φ(0.4876) = 0.6871. 0.688 is what σ = 0.25 gives |
| R13 batch for 80% power at 5% false pass, ((1.6449 + 0.8416)σ/0.01)²: σ from R5 / R4 | 3,901.35 / 3,490.40 | 3,902 / 3,490 | **MISMATCH** (tol 0.5) / MATCH | [C] | R5 path: same σ; the reference appears rounded up, while 3,490 is rounded down |

The post's R13 wording ("about 70% of the time even at 150 examples", "a batch of a few thousand examples") holds for
both σ values, so it does not depend on the two mismatched rows.

**Citation: proposal selection in the current gepa release** (not a computed number; checked 2026-10-17 with
`gh api`; labelled R9 in the v1 register, renamed so R9 is free for the computed row). gepa `v0.1.4` (latest release, published 2026-07-15, tag → `8b0ce6c`) has
`src/gepa/strategies/proposal_selection.py`, added by PR #369 ("ReflectionLM protocol + batch-based parallel
proposals", merged 2026-07-15). `BestImprovement` (lines 46-63) keeps the single passing proposal with the largest
minibatch margin; `TopKImprovements` (lines 66-84) keeps the top k by that margin. The installed copies in this repo
(0.1.1, 0.0.27) predate it.

**Citation: acceptance rules in the current gepa release** (checked 2026-10-17, `gh api`, tag `v0.1.4`).
`src/gepa/strategies/acceptance.py` defines `StrictImprovementAcceptance` (lines 44-53, accepts when
`new_sum > old_sum`) and `ImprovementOrEqualAcceptance` (lines 56-66, `new_sum >= old_sum`), so the second accepts ties.

### P. Every number in the post, in reading order

The post is home_website `app/gepa-selection/page.tsx` on branch `post-revisions` after revision brief v2; its full text
is `gepa-selection-revised.md`. "row" is a `values.csv` id; "cited" means stated in a committed file and not reproduced
here. Units follow the post's Units bullet.

| # | number in the post | source |
|---|---|---|
| 1 | TL;DR: three examples per gate | Table A D:7 (`runs/*/config.json` `minibatch_size`; b = 3 in all 382 swap pairs) |
| 2 | TL;DR: 150 validation examples | R7.ifb_n_val |
| 3 | TL;DR: beat their parent by 0.001 | N2.b3_mean_child_minus_parent (+0.0012); R2.mean_of_run_means (+0.0011) |
| 4 | TL;DR: interval −0.003 to +0.005 | R2.ci95_lo_t_run_means, R2.ci95_hi_t_run_means |
| 5 | card: 0 to 3; 1.08 vs 1.33 (thrown away); 1.00 vs 0.75 (would have been kept) | A1.row1_* (`calls.csv:2`), the first row in the data |
| 6 | 2,292 rewrites; agreed 53.9%; expect 54.4% | A2.n_children, A2.agreement, A2.chance_agreement |
| 7 | IFBench checklist "2/3", "10-th", "26-th"; HoVer "1/3" | quoted example feedback, not a result |
| 8 | five ways to score; none of the five | **cited, not reproduced**: `analysis/rescreen_wave1.md:48-59`; `findings_summary.md:35, 226` (OQ 7) |
| 9 | IFBench swap +0.005, interval −0.012 to +0.024 | **cited**: `analysis/ablation/batch_swap_v2/results.md:8` (+0.0054, run-cluster [−0.0116, +0.0242]) |
| 10 | 150 batches; kept 34% / 31% / 37% | X.ablation_keep_rate_i / _ii / _iii (51, 47, 55 of 150) |
| 11 | roughly 10 to 12 points | **cited, not reproduced**: X.ablation_MDE_pp (`ablation/plan.md:39`) |
| 12 | asking twice flipped the verdict 32% of the time | R6.ablation_same_arm_repeat_flips (`ablation/results.md:43-44`) |
| 13 | three articles, three search steps | task description (Table A D:54) |
| 14 | HoVer swap +0.027, interval +0.015 to +0.042 | X.hover_spec_point, X.hover_spec_ci_lo, X.hover_spec_ci_hi |
| 15 | one more needed article every 12 batches | derived: 1 / (3 × 0.0274) = 12.2 from X.hover_spec_point (one article = 1/3 of an example's score) |
| 16 | +0.017, interval −0.004 to +0.037 | X.hover_transfer_point; interval `hover_swap/results.md:12` |
| 17 | 108 rules; p = 0.0013 | X.screen_cells, X.screen_survivor_p |
| 18 | three arms, eight paired runs; 300 metric calls | Table A D:58; R7.hover_three_arm_max_metric_calls |
| 19 | stock draws three; control and treatment draw six and keep three | `runs/*/config.json` `minibatch_size` (3 for B, 6 for C and T); Table A D:58 |
| 20 | 50 claims; 10-claim validation set; 150 held-out claims | R7.hover_three_arm_selection_n, _n_val, _test_n |
| 21 | treatment vs control −0.001, −0.026 to +0.032, p 0.97 | D6.T-C_n8_mean, D6.T-C_n8_signflip_p; interval **cited** `state_dep/results.md:59` (pre-registered table) |
| 22 | treatment vs stock GEPA −0.013, −0.039 to +0.021, p 0.48 | D6.T-B_n8_mean, D6.T-B_n8_signflip_p; interval **cited** `state_dep/results.md:80` |
| 23 | 200 shuffles; winner in 134; 43, about 1 in 5 | E1.perms_with_any_survivor, E1.perms_with_survivor_abs_beta_ge_obs (E3 the same 43) |
| 24 | p-value about 0.2, not 0.0013 | R6.screen_familywise_p (0.215); X.screen_survivor_p |
| 25 | caption: 200; 43 | E3, `fig_screen_null_survivors.csv` |
| 26 | MDE about 0.063 | X.three_arm_MDE |
| 27 | 0.027 on the three-example total; about 0.009 per example | D5.planned_one_step_effect_1.4432xbeta/2; D5.planned_per_example |
| 28 | about 7 times | D5.MDE_over_planned_per_example (6.94); `state_dep/plan.md:345-357` (GATE BITES: False) |
| 29 | stock GEPA's gain about 0.024, interval −0.002 to +0.050 | R1.hover_gepa_gain, R1.hover_gepa_gain_ci95_lo/hi |
| 30 | more than twice | derived: X.three_arm_MDE / R1.hover_gepa_gain = 2.6 |
| 31 | 5 of the 24 runs | D2.n_seed_prompt_runs |
| 32 | IFBench 53.9% vs 54.4%; HoVer 54.7% vs 54.3% | A2.agreement, A2.chance_agreement; B1.agreement, B1.chance_agreement |
| 33 | siblings 72% (55%) IFBench; 69% (53%) HoVer | A3.sibling_agreement_own_batch, A3.sibling_chance_own_batch; B4.hover_sibling_* |
| 34 | different batches, same batch: 70% on both, about 55% expected | R10.ifb_cross_arm_*_pooled, R10.hover_cross_arm_*_pooled |
| 35 | caption: about 54%, not 50% | A2.chance_agreement, B1.chance_agreement |
| 36 | own batch: 34% higher, 32% lower, 34% tied; HoVer 37%, 27%, 35% | R5.ifb_own_margin_*_share; R5.hover_own_margin_*_share |
| 37 | parent under 0.5 of 3: 76% pass; 2.5 or more: 8% | A5 own-batch keep rates **0.756 and 0.081** (`fig_gate_headroom.csv`), not the all-verdict 0.728 and 0.073 |
| 38 | about a third of verdicts are exact ties | A4.zero_margin_on_own_batch (769/2292 = 0.336) |
| 39 | re-scored parent tied its first score 46% of the time | R4.ties_share |
| 40 | eight IFBench runs | C1.b3_runs |
| 41 | kept rewrites beat their parents by 0.001; 95% interval −0.003 to +0.005 | N2.b3_mean_child_minus_parent; R2.ci95_* |
| 42 | 10 runs; starting prompt 0.505 to 0.560 | N1.seed_valset_mean_min, N1.seed_valset_mean_max |
| 43 | standard deviation 0.021; 0.019 to 0.021 | R3.sd_of_115_d_ddof1; R3.sqrt2_x_pooled_sd, R3.sqrt2_x_run_level_N1_sd |
| 44 | first kept rewrites: 8, by 0.011, 6 of 8, interval −0.006 to +0.028 | R9.mean, R9.n_positive, R9.ci95_lo_t, R9.ci95_hi_t |
| 45 | HoVer gain about 0.024, interval includes zero | R1 |
| 46 | #132, #395 | GitHub issue URLs (external) |
| 47 | best of three: +0.23 out of 3; +0.006, interval −0.006 to +0.020 | R6.best_of_3_own_margin, R6.best_of_3_selection_lift, R6.best_of_3_selection_lift_ci |
| 48 | gate about six metric calls per round; 150 more per kept rewrite; 83% | C5.b3_gate_calls_per_evaluated_iteration (5.89); R7.ifb_n_val; C6.b3_kept_validation_share_of_all_calls (0.830) |
| 49 | a third of verdicts are ties; about half; 0.01 better; about 70% at 150 examples; a few thousand | A4; R13 (normal approximation, ties ignored: Φ(0) = 0.5; pass 0.687 to 0.697; batch 3,490 to 3,901) |
| 50 | earlier study: 20-example batch; F1 0.632 vs 0.639; three runs each; starting prompt 0.632 | **cited**: frontier-gepa `docs/BASELINE-CHECK-2026-09-29.md:103` (`random` 0.6319), `:107` (`vanilla_coupled_gepa` 0.6386); starting prompt F.seed_test_f1_300 (0.6316) |
| 51 | κ −0.01 (−0.06 to +0.04); +0.007 (−0.06 to +0.07) | A2.kappa, A2.kappa_ci95_*_resample_pairs_B_id; B1.kappa, B1.kappa_ci95_*_resample_pairs |
| 52 | 0.033 on the three-example total | **cited, not reproduced**: X.ifb_swap_MDE_constant (`batch_swap_v2_analysis.py:22`) |
| 53 | 10 to 12 points; 0.063; 150-claim test | see 11; X.three_arm_MDE; R7.hover_three_arm_test_n |
| 54 | per-pair intervals −0.015 to +0.026; +0.005 to +0.050; −0.015 to +0.049 | R6.ifb_swap_specificity_naive_pair_ci; R6.hover_swap_specificity_naive_pair_ci; R6.hover_swap_transfer_naive_pair_ci |
| 55 | Setups: 150 / 150 / 2,500 / 0.1.1; 100 / 10 / 300 / 0.0.27 / 50 / 150 | R7 |
| 56 | two one-example IFBench runs; eight three-example runs | C1.b1_runs, C1.b3_runs |
| 57 | seed 4: +0.100; leave-one-out −0.016 to +0.007, −0.027 to −0.006, −0.017 to −0.008 | D6.T-C_seed4_diff; R11 |
| 58 | eight final prompts; 5 runs; two ties | D3; D2.n_seed_prompt_runs, D2.n_tie_broken_toward_index0 |
| 59 | HotpotQA: 21 runs; 3 stock and 18 variants | F.cells_with_accept; split **cited** `BASELINE-CHECK-2026-09-29.md:200-203` and its §5.1 table |
| 60 | a later 12-run study | R8.exp3_runs_committed_non_smoke |
| 61 | 75 validation examples; +0.062; 300 test examples; +0.001; 11 of the 21 | F.mean_best_val_gain (note: 75 items), F.seed_test_f1_300 (300 items), F.mean_test_gain, F.cells_above_seed_on_test |
| 62 | stock GEPA alone gained +0.007 | **cited**: `BASELINE-CHECK-2026-09-29.md:107` (Δ mean +0.0069) |
| 63 | Qwen2.5-7B | frontier-gepa `README.md:7` |
| 64 | five float-tie accepts on HoVer; one IFBench batch | D7.total_float_tie_accepts; X.ablation_float_tie_batches |

---

## Figures

| file | shows | data |
|---|---|---|
| `fig_gate_headroom.{png,svg}` | own-batch keep rate vs the parent's batch total, n per bin. Annotation "IFBench, 2,292 rewrites"; x-label "Parent's score on the batch the rewrite was written from (total over 3 examples, 0 to 3)", on two lines (revised 2026-10-17) | `fig_gate_headroom.csv` (A5) |
| `fig_screen_null.{png,svg}` | histogram of the 200 null max-β, line at the observed 0.0379, "93/200 null maxima ≥ observed"; x-label "Strongest effect among 108 rules, per shuffled dataset" | `fig_screen_null.csv` (E2) |
| `fig_screen_null_survivors.{png,svg}` | per shuffle, the strongest \|β\| among full-rule survivors: a separate bar for the 66 shuffles with no survivor, a histogram of the 134 others, and a line at the observed β annotated "43/200 shuffles ≥ observed". Bins are 0.003 wide with an edge exactly at the observed β, so the bars right of the line sum to 43 (asserted when drawing). | `fig_screen_null_survivors.csv` (E3) |
| `fig_agreement.{png,svg}` | observed vs "expected if independent" agreement: (a) same rewrite, two batches, IFBench and HoVer; (b) sibling rewrites, same batch, IFBench and HoVer | `fig_agreement.csv` |
| `fig_budget.{png,svg}` | IFBench metric calls split into seed / kept-beat / kept-not-beat validation + everything else; all, b = 3, b = 1 | `fig_budget.csv` (C3) |
| `fig_budget_b3.{png,svg}` | the b = 3 bar only, with the two kept-rewrite validation segments merged into one, "validating kept rewrites" (17,250). y tick "Three-example batches (8 runs)" (revised 2026-10-17; the CSV group label is still "b=3 (8 runs)") | `fig_budget.csv` (C3) |

Style: Okabe-Ito palette, no baked-in titles, PNG at 200 dpi plus SVG.

---

## OPEN QUESTIONS

These are for Neel. Nothing here is decided.

1. **κ interval unit (D:105).** The draft's [−0.05, +0.04] matches only the 8-run cluster bootstrap. Per child it would
   be [−0.05, +0.03], and per pair [−0.06, +0.04]. Which unit does the article name? D:101 says intervals resample the
   8 runs, and 8 clusters make a percentile bootstrap optimistic.
   - *Resolved in the post:* it gives the per-pair interval (−0.06 to +0.04) and says agreement intervals resample batch pairs.
2. **"Coin flips" (D:7).** Chance here is independence at the observed accept rates (0.544), not 50/50. Keep the
   metaphor, or say "as if independent"?
   - *Resolved in the post:* "as often as two independent verdicts would", and the agreement caption explains why chance is 54%, not 50%.
3. **B2 reference reading.** I read "0.558 vs 0.565" as agreement vs chance within the exact-match stratum (n = 708),
   and it matches. The other reading, exact-match vs non-exact agreement, gives 0.558 vs 0.536.
   - *Moot:* the post does not use B2.
4. **Calibration comparator (D:62).** This inherits `article_todos` OQ 1: 134/200 (any survivor), 43/200 (\|β\|, either
   sign), 20/200 (same sign). The draft uses 43 with "at least as strong". Should the other two travel with it?
   - *Resolved in the post:* it gives 134/200 (a winner at all) and 43/200 (at least as strong); the same-sign 20 is left out.
5. **Percentile definition (E2).** Strict-below and ≤ both give 0.535 (no null maximum equals the observed value). Which
   one is the article's wording, if it is used at all?
   - *Moot:* the post does not use the percentile.
6. **D:64 "effect it was designed around".** The pre-registered value is 0.02738 (D = 1.4432). The realized-dose 0.0231
   is post hoc. Both are one-step units and do not compare to the 0.063 endpoint MDE. Which value, and should the
   pre-registered trigger (0.08213) be the comparator instead?
   - *Resolved in the post:* the pre-registered 0.027 on the three-example total, "about 0.009 per example", with the units stated; the trigger is not used.
7. **Cited, not reproduced.** Three draft numbers trace to committed documents but were not recomputed here:
   - 0.033 is a Stage-0 constant, `batch_swap_v2_analysis.py:22`.
   - 10–12 pp is a Stage-0 analytic estimate, `ablation/plan.md:39`.
   - "Five scorers, none survive" comes from `rescreen_wave1.md` via the ledger.

   Should they be reproduced before publication?
   - *Still open:* the post uses all three (0.033, 10 to 12 points, five scorers) and they are still cited, not reproduced.
8. **Ablation accept column. RESOLVED (2026-10-15).**
   - **Mechanism.** `scripts/run_ablation.py:153-155` sets `accept_today = int(c_sum > p_sum)` on the unrounded float sums, but writes both sums rounded to 4 dp.
   - **The rows.** Batch s6_it4 ties at 1.5 vs 1.5 in arms i, i_rep and iii (`calls.csv:380, 382, 383`), and float residue accepted all three. These are the only rows in the file where `accept_today` disagrees with the rounded comparison (fn `x_ablation`, `X.ablation_accept_today_disagreements`).
   - **Reconciliation.** 52 − 1 = 51 (arm i) and 56 − 1 = 55 (arm iii) match `ablation/results.md:30, 32`. Arm ii's s6_it4 call (1.8333 vs 1.5) is a genuine accept.
   - Recorded as an IFBench float tie in the D:109 row.
9. **HotpotQA source (D:107).** The +0.062/+0.0013 recompute from committed per-run files in frontier-gepa, but the
   only statement of them is the **untracked** `docs/BASELINE-CHECK-2026-09-29.md`.
   - Commit that doc before citing?
   - Is the definition used here the article's definition? It is the mean over the 21 Exp 1/1b cells with ≥ 1 accept of (best accepted D_pareto val F1 − seed) and of (returned program's test F1 − seed).
   - The draft's label "examples it optimized against" does not match that set.
   - *Resolved:* the doc is now tracked (frontier-gepa `61c16fb`; `F.source_doc_tracked` = yes), the post links it, and the post's label is "the 75 validation examples used to choose it", a best-of score.
10. **"Six times" (D:117).** No committed list of six such incidents was found. Which six? Each would need its own source.
    - *Resolved in the post:* it says "More than once" and names five examples, with no count.
11. **73/145 vs 53/115 (D:79).** Which scope does the article intend: all 10 runs, or the b = 3 runs that match its
    "three examples" framing?
    - *Resolved in the post:* b = 3 scope. The kept-rewrite numbers use only the eight three-example runs (Details).
12. **D:93 per-round cost.** "About twice the batch size" holds for the gate only (5.89 calls per evaluated iteration at
    b = 3). Validation is about 90% of the IFBench budget. Should the sentence say which cost it means?
    - *Resolved in the post:* the gate costs about six metric calls per round, each kept rewrite 150 more, and validation took 83% at b = 3.
13. **D:108 contrast label.** In the ledger, "baseline" is arm B. With seed 4 dropped, T−B is −0.027 (p 0.047, n = 7,
    post hoc), and T−B is already negative with seed 4 included (−0.0128). The −0.016 figure is T−C. Which contrast does
    the sentence mean?
    - *Resolved in the post:* both are named, treatment vs control −0.016 (p 0.08) and treatment vs stock GEPA −0.027 (p 0.047), with the post hoc drop called illegitimate.
14. **D3 (stock GEPA gain over the seed).** The +0.024 compares 8 unselected runs with 5 runs selected because the seed
    won. Report it at all? If so, should it carry a selection-bias caveat, or wait for a dedicated seed-prompt evaluation?
    - *Closed:* No selection bias: those 5 runs were picked on the 50-claim selection split, and their test scores are fresh evaluations on the separate 150-claim test split.
15. **B4.** HoVer sibling agreement (0.691 vs 0.532) is now the fourth group in `fig_agreement`. Should D:75 cite both corpora, or stay IFBench-only?
    - *Resolved in the post:* both corpora (IFBench 72% vs 55%, HoVer 69% vs 53%).
16. **A1 framing.** The opening example's "thrown away" verdict is on the batch the rewrite was written from (the real
    gate). Its "kept" verdict is on the other batch. Should the article say which batch is which?
    - *Resolved in the post:* the card names "the batch it was written from" (thrown away) and "a different batch" (would have been kept).

17. **Other batch-total numbers.** The IFBench swap's +0.0054 specificity and its 0.033 MDE (D:102) are batch totals
    too: IFBench margins are summed over 3 examples (`batch_swap_v2_run.py:232-235`). The same goes for the 0–3 bin axis
    in `fig_gate_headroom`, which is labeled as such. Should D:102 carry per-example equivalents (÷ 3) like D:56 and
    D:64? Not changed here.
    - *Resolved in the post:* a Units bullet in Details, and swap numbers say "on the three-example total".

---

## Reproduce

From the repo root:

```sh
analysis/state_dep/.venv-armT/bin/python -B tests/test_t_dist.py
analysis/state_dep/.venv-armT/bin/python -B scripts/article_numbers.py compute
python3.12 -m venv "$TMPDIR/figvenv" && "$TMPDIR/figvenv/bin/pip" install matplotlib==3.9.2
"$TMPDIR/figvenv/bin/python" -B scripts/article_numbers.py figures
```

- The figures venv needs Python 3.12 or 3.13: matplotlib 3.9.2 has no wheel for 3.14. On 2026-10-17 it was built from
  the uv-managed CPython 3.12.13 that the armT venv uses, and the four unrevised figures came out byte-identical.
- `FRONTIER_GEPA` sets the frontier-gepa checkout that Part F and R8 read. It defaults to `~/Desktop/frontier-gepa`.

- The script does not read the draft. Table A was built by reading `~/Downloads/gepa-selection-short.md` by hand.
- `compute` reads `$FRONTIER_GEPA` (default `~/Desktop/frontier-gepa`) for Part F and R8, running read-only `git log`, `git ls-files` and `git rev-parse` there.
- `compute` writes only `analysis/article_numbers/*.csv`. `figures` writes only `analysis/article_numbers/fig_*.{png,svg}`.
