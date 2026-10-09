# Article todos: five recomputed numbers (2026-10-08)

Purpose: numbers for the article. Every value below was recomputed from the raw source file named
beside it. None was copied from a summary. **No verdicts.** `analysis/findings_summary.md` (the
ledger) and every `results.md` are quoted, never edited. Decisions are left to §6 OPEN QUESTIONS.

**Method.** All computation was read-only, under `analysis/state_dep/.venv-armT/bin/python -B`
(Python 3.12.13; `analysis/state_dep/.venv-armT/pyvenv.cfg:4`), run from the repo root. The only
file written is this one. The exact code is reproduced in the Appendix, and [C] values cite its
block by line.

Status tags:
- **[R]**: the value exists in a committed artifact and was reproduced here from raw data.
- **[C]**: computed for this document. It exists in no committed artifact and is not cite-safe
  until it is committed.

---

## 1. Calibration, either sign

Source: `analysis/review_response_2026-08-26/_perm_raw.json`. Key `"0"` is the identity pass and
keys `"1"`..`"200"` are the 200 within-seed null permutations (`_perm_calibration.py:46-50`).

The full published rule, reimplemented as in `_perm_calibration.py:80-90`:
- **crit_a:** the read-4.1 BCa CI excludes 0, LORO ≥ 7, and p < 0.05.
- **crit_b:** crit_a, AND the read-4.2 CI excludes 0, AND p < 0.05.
- **AND** the cell is in that permutation's stored `mcb` list (`_perm_calibration.py:64-74`).

β is the read-4.1 beta. Identity pass: survivors = `['knn_emb_fb_min']`, β = 0.0379395028680125.
This matches the published sole survivor (`03_permutation_calibration.md:30, 62`).

| quantity (200 null permutations, full rule, LORO ≥ 7) | count | rate | committed source | status |
|---|---|---|---|---|
| ≥ 1 survivor, any β | 134/200 | 0.6700 | `03_permutation_calibration.md:44` | [R] |
| ≥ 1 survivor with β ≥ +0.03794 (same direction, at least as strong) | 20/200 | 0.1000 | `WEBSITE-2026-09-28.md:176` (itself [C] there) | [R] vs WEBSITE |
| **≥ 1 survivor with \|β\| ≥ 0.03794, either sign** | **43/200** | **0.2150** | none | **[C]** (Appendix, line 316) |
| of those: ≥ 1 survivor with β ≤ −0.03794 | 28/200 | 0.1400 | none | [C] |
| permutations with survivors on both sides (counted in both rows above) | 5/200 | 0.0250 | none | [C] |
| null survivors with \|β\| ≥ 0.03794, pooled over all 200 permutations | 67 | — | none | [C] |

- 20 + 28 − 5 = 43.
- The counts are identical at the threshold 0.03794 and at the unrounded observed β
  0.0379395028680125.

## 2. HoVer swap: transfer p-value

The test is the same one used for specificity: `perm_p` in
`analysis/ablation/hover_swap/hover_swap_analysis.py:90-95`.
- **Statistic:** the mean of the 243 per-pair values.
- **Null:** a within-pair sign flip of each pair's whole value, with 20000 permutations (`:36`).
- **p-value:** two-sided, `|null| ≥ |obs| − 1e-12`.
- **RNG:** one module-level generator, `default_rng(20260703)` (`:40`).
- **Inputs:** per-pair transfer is `((mB_SAME + mA_SWAP)/2)/3` (`:132`) and specificity is `:131`, both
  built from the raw `pairs/*/draws.jsonl` via `load()` and `draw_avg()` (`:53-87`).

| estimand | point | perm p | committed source | status |
|---|---|---|---|---|
| pooled specificity | +0.027434842249657063 | 0.0177 | `hover_swap/results.md:11`; ledger `findings_summary.md:110-111` | [R] |
| **pooled transfer** | +0.016918152720621856 | **0.31195** (prints as 0.3120) | `hover_swap/results.md:12` | **[R]** (Appendix, line 335) |
| pooled transfer, generator freshly seeded 20260703 for this test alone | same | 0.30755 | none | [C] |

- n = 243 pairs.
- The committed transfer p comes from the same `report()` sequence as specificity (`:148-149`). The
  shared generator is consumed in order: spec permutation, spec cluster bootstrap, spec naive
  bootstrap, then transfer permutation.
- Replaying that chain reproduces 0.31195. The second row is the same test without the chain.
- The ledger states specificity's p (`findings_summary.md:111`) but not transfer's
  (`:111-112`).

## 3. Same-child cross-batch gate agreement

- **Gate:** GEPA's strict batch-sum rule, accept iff `sum(child) > sum(parent)`. It rejects on
  `new_sum <= old_sum` at `scratch/hover_probe/.venv/lib/python3.12/site-packages/gepa/core/engine.py:491-493`
  (gepa 0.0.27).
- **"Agree":** the verdict on batch A equals the verdict on batch B, for the same child, each verdict
  taken against that batch's parent baseline.
- In each corpus, every row is one child that was scored on both batches.

| corpus | children n | agree | agreement rate | (A acc, B acc) | (A acc, B rej) | (A rej, B acc) | (A rej, B rej) | status |
|---|---|---|---|---|---|---|---|---|
| IFBench batch-swap v2 | 2292 | 1236 | **0.5393** | 272 | 468 | 588 | 964 | [C] (Appendix, line 353) |
| HoVer swap | 1458 | 797 | **0.5466** | 184 | 334 | 327 | 613 | [C] (Appendix, line 353) |

### What A and B are, per corpus

**IFBench batch-swap v2**
- Source: `analysis/ablation/batch_swap_v2/calls.csv`, one row per child (382 pairs × 2 arms × K = 3).
- A = the event's batch B. Verdict = `margin_on_B > 0`.
- B = the swap batch B′. Verdict = `margin_on_Bp > 0`.
- Parent: always P_B, freshly re-evaluated on both batches (`scripts/batch_swap_v2_run.py:220-222`).
- Children: scored at `:230-231`.
- Margins are `round(sB − pB_sum, 4)`, computed from the unrounded sums (`:232-235`).
- Cross-check: the verdicts from the rounded `child_sum_* > parent_*_sum` columns agree on 2292/2292 rows.
- Exact-zero margins (ties, counted as rejects): 838 on B and 677 on B′.
- The smallest nonzero |margin| is 0.0333.

**HoVer swap**
- Source: `analysis/ablation/hover_swap/pairs/*/draws.jsonl` (243 pairs × 2 arms × K = 3).
- A = A_e. Verdict = `sum(scores_on_A_e) > sum(A_e_parent_scores_logged)`.
- B = B_e. Verdict = `sum(scores_on_B_e) > sum(B_e_parent_scores_fresh)`.
- Sums are compared in exact integer thirds (`thirds()`, `hover_swap_analysis.py:43-50`).
- Children: scored at `hover_swap_run.py:212-213`.
- Exact-zero margins: 506 on A and 560 on B.

By arm:

| arm | agree | rate |
|---|---|---|
| SAME | 408/729 | 0.5597 |
| SWAP | 389/729 | 0.5336 |

### Differences between the two corpora that travel with the numbers
- **Parent baselines.**
  - IFBench: both batches use a fresh P_B evaluation.
  - HoVer: the A baseline is the *logged* Stage-1 parent score (`hover_swap_run.py:181`). The B
    baseline is a fresh parent run on 6 drawn examples, from which the 3 that best match A's score
    multiset are kept (`:139-147, 190-194`).
- **Float vs exact gate.**
  - GEPA's live gate sums floats. The verdicts above compare exact sums: integer thirds for HoVer,
    4-dp-rounded margins for IFBench, so float residue reads as a tie.
  - HoVer under a Python 3.12 float-sum gate: 792/1458 agree (0.5432). 11 individual verdicts
    differ from the exact version. [C] (Appendix, line 377)
  - IFBench cannot be re-run this way, because the unrounded sums were not saved
    (`batch_swap_v2_run.py:232-235`).

## 4. False-accept rate: accepted children whose valset score did not beat their parent's

**Definition**
- For each accepted child, compare its full-valset mean with its parent's full-valset mean.
- "Did not beat" means child ≤ parent, so ties count. Ties are also shown separately.
- Means are computed in **exact rationals** from the per-example scores. Every per-example score is
  asserted to be k/d with d ≤ 5 (Appendix, line 307), so float summation order cannot create or break a tie.
- Every child and parent in every row below has a full-valset evaluation
  (`num_examples_evaluated == total_valset_size`, or a full subscore vector).

**Sources**
- IFBench: the `logs/**.jsonl` events.
  - `valset_evaluated` gives `scores_by_val_id`, logged at `gepa_si/si_event_logger.py:124-136`.
  - `candidate_accepted` gives `new_candidate_idx` and `parent_ids` (`:159-165`).
  - The 10 baseline runs are the completed `max_metric_calls == 2500` configs
    (`gepa_si/screen/corpus_io.py:20, 59`).
- HoVer: `gepa_result.json`, keys `parent_program_for_candidate` and `prog_candidate_val_subscores`.
  - Every candidate after index 0 is an accepted child, and every parent list has length 1.
  - All three state_dep arms accept through `GEPAEngine.run()` (`analysis/state_dep/run_state_dep.py:282, 350`).

| corpus | runs | valset size | accepted children | child < parent | child = parent | **did not beat (≤)** | **rate** | status |
|---|---|---|---|---|---|---|---|---|
| IFBench baseline, all 10 | 10 | 150 | 145 | 73 | 0 | **73** | **0.5034** | [C] |
| ↳ b = 3 | 8 | 150 | 115 | 53 | 0 | 53 | 0.4609 | [C] |
| ↳ b = 1 | 2 | 150 | 30 | 20 | 0 | 20 | 0.6667 | [C] |
| IFBench phase 2 (`logs/phase2/`) | 2 | 150 | 29 | 11 | 0 | **11** | **0.3793** | [C] |
| HoVer Stage-1 (`scratch/hover_stage1/stage1_seed0..7`) | 8 | 10 | 89 | 48 | 21 | **69** | **0.7753** | [C] |
| HoVer state_dep arm B | 8 | 10 | 84 | 39 | 18 | **57** | **0.6786** | [C] |
| HoVer state_dep arm C | 8 | 10 | 52 | 24 | 11 | **35** | **0.6731** | [C] |
| HoVer state_dep arm T | 8 | 10 | 71 | 41 | 10 | **51** | **0.7183** | [C] |

Per-run counts (n / child < parent / child = parent):

**IFBench baseline**

| run | n | < | = |
|---|---|---|---|
| seed0 b3 | 15 | 4 | 0 |
| seed1 b3 | 15 | 9 | 0 |
| seed2 b3 | 14 | 6 | 0 |
| seed3 b3 | 14 | 8 | 0 |
| seed4 b3 | 14 | 6 | 0 |
| seed5 b3 | 14 | 9 | 0 |
| seed6 b3 | 14 | 6 | 0 |
| seed7 b3 | 15 | 5 | 0 |
| seed0 b1 | 15 | 10 | 0 |
| seed1 b1 | 15 | 10 | 0 |

**IFBench phase 2**

| run | n | < | = |
|---|---|---|---|
| tractability seed0 | 15 | 7 | 0 |
| uniform seed0 | 14 | 4 | 0 |

**HoVer** (columns are seeds; each cell is n / < / =)

| corpus | s0 | s1 | s2 | s3 | s4 | s5 | s6 | s7 |
|---|---|---|---|---|---|---|---|---|
| Stage-1 | 10/8/0 | 10/3/5 | 12/8/0 | 10/3/4 | 13/8/2 | 9/3/5 | 12/6/4 | 13/9/1 |
| state_dep B | 10/5/1 | 10/4/4 | 8/4/3 | 10/5/2 | 13/9/0 | 8/2/2 | 12/6/1 | 13/4/5 |
| state_dep C | 6/3/0 | 3/1/2 | 6/5/1 | 8/4/1 | 9/4/1 | 6/4/1 | 7/1/4 | 7/2/1 |
| state_dep T | 9/6/2 | 10/7/0 | 9/4/2 | 6/3/1 | 9/4/0 | 8/6/1 | 9/5/2 | 11/6/2 |

**Float sensitivity (HoVer only; IFBench has no ties).** Comparing float means instead of exact ones
moves the HoVer "≤" counts, because 10-example means of thirds tie often and float residue breaks
ties in either direction. [C] (Appendix, line 402)

| corpus | exact | Python ≥ 3.12 `sum` (compensated) | Python ≤ 3.11 `sum` (left to right) |
|---|---|---|---|
| Stage-1 | 69 | 69 | 64 |
| state_dep B | 57 | 55 | 51 |
| state_dep C | 35 | 35 | 34 |
| state_dep T | 51 | 51 | 49 |

**Excluded runs.** These are not study corpora; they are shown so nothing is silently dropped.
Each has full valset evaluations.

| run | why excluded | valset | n | < | = |
|---|---|---|---|---|---|
| `logs/baseline_seed0_b3_20260626_214107` | `max_metric_calls` 1000, no results block | 150 | 6 | 4 | 0 |
| `logs/baseline_seed0_b1_20260627_045843` | no results block; partial | 150 | 14 | 7 | 0 |
| `logs/ifbench_baseline_001` | pilot | 30 | 2 | 1 | 0 |
| `logs/faithful_20260626_211111` | pilot | 40 | 2 | 0 | 0 |
| `logs/smoke_001` | smoke | 4 | 2 | 0 | 1 |
| `analysis/reflection_capture/capture` | capture probe | 6 | 2 | 2 | 0 |
| `scratch/hover_stage1/stage1_seed0_dry` | dry run | 4 | 1 | 1 | 0 |
| `analysis/state_dep/runs/smoke_T_seed0` | smoke | 10 | 7 | 4 | 2 |
| `scratch/hover_probe/necrosis` | probe | 10 | 10 | 6 | 3 |
| `scratch/hover_probe/necrosis_dry` | dry run | 4 | 0 | — | — |

Corpora with no valset evaluation, and therefore not applicable: the IFBench batch-swap v2, the
HoVer swap, and the IFBench feedback ablation (`analysis/ablation/calls.csv`). All three are
one-step corpora.

## 5. IFBench: task model and proposer for the 10 baseline runs

Source: each run's sidecar config, `logs/<run>.config.json`. Line 8 is `task_lm` and line 9 is
`reflection_lm` in all ten. The values were re-read from the bytes. [R] (Appendix, line 464)

| run config | task model (:8) | proposer / reflection LM (:9) |
|---|---|---|
| `baseline_seed0_b3_20260626_231443.config.json` | openai/gpt-4.1-mini | openai/gpt-4.1 |
| `baseline_seed1_b3_20260626_234940.config.json` | openai/gpt-4.1-mini | openai/gpt-4.1 |
| `baseline_seed2_b3_20260627_002407.config.json` | openai/gpt-4.1-mini | openai/gpt-4.1 |
| `baseline_seed3_b3_20260627_010912.config.json` | openai/gpt-4.1-mini | openai/gpt-4.1 |
| `baseline_seed4_b3_20260627_014442.config.json` | openai/gpt-4.1-mini | openai/gpt-4.1 |
| `baseline_seed5_b3_20260627_024139.config.json` | openai/gpt-4.1-mini | openai/gpt-4.1 |
| `baseline_seed6_b3_20260627_032222.config.json` | openai/gpt-4.1-mini | openai/gpt-4.1 |
| `baseline_seed7_b3_20260627_041456.config.json` | openai/gpt-4.1-mini | openai/gpt-4.1 |
| `baseline_seed0_b1_20260627_172351.config.json` | openai/gpt-4.1-mini | openai/gpt-4.1 |
| `baseline_seed1_b1_20260627_161711.config.json` | openai/gpt-4.1-mini | openai/gpt-4.1 |

- Driver constants: `scripts/run_baseline.py:45-46` (`TASK_LM`, `REFLECTION_LM`).
- The two phase-2 configs record the same pair (`logs/phase2/*.config.json:10-11`).
- The configs are the runner's declared settings. They are not an echo of the model string the API
  served.
- For contrast, the HoVer proposer is gpt-4.1-mini (`WEBSITE-2026-09-28.md:275, 292-293`).

## 6. OPEN QUESTIONS

These are for Neel. Nothing here is decided, and the ledger is untouched.

1. **Calibration comparator.** Three null rates now describe the same survivor:
   - 134/200: any survivor.
   - 43/200: |β| ≥ observed, either sign.
   - 20/200: β ≥ observed, same sign.

   The rule's CI test is two-sided. Which is the article's comparator, and should all three be shown?
2. **Commit before citing?** Every [C] value here (items 1, 3, 4, and the item-2 fresh-seed p) lives
   only in this file. Should they become a committed artifact first, as WEBSITE OQ 2 asked for the
   direction-restricted rates?
3. **Transfer p and RNG chain.** The committed 0.3120 depends on the generator state left by
   specificity's resampling. Under a fresh seed it is 0.30755. Should 0.3120 be quoted, with or
   without that note? And should the ledger, which omits transfer's p, carry it?
4. **Item-3 baselines differ by corpus.** HoVer's A-side parent baseline is the logged Stage-1 score
   and its B-side is a fresh run. IFBench's are both fresh. Is that comparable enough to put the two
   agreement rates side by side?
5. **Exact vs float gate.** GEPA's live gate sums floats. In Stage-1, two exact ties were accepted
   because of float residue:
   - seed 0, trace i = 31: [2/3, 2/3, 1] → [1, 1/3, 1], `new_program_idx` 10
   - seed 5, trace i = 23: [1, 2/3, 2/3] → [1, 1, 1/3], `new_program_idx` 8

   Both are from `scratch/hover_stage1/stage1_seed{0,5}/gepa_result.json` `full_program_trace` [C] (Appendix, line 390).
   Should items 3 and 4 be stated in exact arithmetic (as here) or as GEPA computed them? Under the
   float version, the HoVer numbers move: item 3 goes 797 → 792, and item 4 moves by 0–6 per corpus
   depending on the interpreter.
6. **Ties in "did not beat".** With a 10-example valset, 10–21 accepted children per HoVer corpus tie
   their parent exactly. Is "≤" the article's definition, or "<"? Under "<", the rates are:
   - Stage-1: 48/89
   - state_dep B: 39/84
   - state_dep C: 24/52
   - state_dep T: 41/71
7. **Which corpora count.**
   - Should IFBench phase 2 (2 runs, one of them tractability-sampled) be reported beside the
     10 baselines, or left out?
   - Should the b = 1 runs be pooled with b = 3, or kept separate?
8. **Valset size disparity.** IFBench valset = 150, HoVer = 10. Should the article put the per-corpus
   rates in one table?
9. **Proposer differs across programs.** The IFBench proposer is gpt-4.1 and the HoVer proposer is
   gpt-4.1-mini (item 5; WEBSITE OQ 9). How should the article state this next to the cross-corpus
   numbers in items 3 and 4?

---

## Appendix: reproduction code

Run from the repo root with `analysis/state_dep/.venv-armT/bin/python -B -`, code on stdin. It
writes nothing.

```python
import collections, csv, glob, importlib.util, json, linecache, math, os, sys
import numpy as np
from fractions import Fraction

assert sys.version_info[:2] == (3, 12)    # the float-sum columns below are "builtin sum() under 3.12"
DENOMS = set()

def exact_mean(xs):
    """Exact rational mean. Each per-example score must be k/d, d <= 5, to 1e-12 (asserted)."""
    fs = [Fraction(x).limit_denominator(1000) for x in xs]
    assert all(abs(float(f) - x) < 1e-12 and f.denominator <= 5 for f, x in zip(fs, xs))
    DENOMS.update(f.denominator for f in fs)
    return sum(fs) / len(fs)

def naive_mean(xs):
    t = 0.0
    for x in xs: t += x          # left-to-right float sum, as Python <= 3.11 sum() does
    return t / len(xs)

# ---- item 1: calibration, either sign ----
d = json.load(open("analysis/review_response_2026-08-26/_perm_raw.json"))
def excl0(r): return not math.isnan(r["lo"]) and (r["lo"] > 0 or r["hi"] < 0)
def crit_a(rec, c): r = rec[c]["41"]; return excl0(r) and r["loro"] >= 7 and r["p"] < 0.05
def crit_b(rec, c): r = rec[c]["42"]; return crit_a(rec, c) and excl0(r) and r["p"] < 0.05
def survivors(o): return [c for c in o["cells"] if crit_b(o["cells"], c) and c in o["mcb"]]
s0 = survivors(d["0"])
print("I1 identity", s0, repr(d["0"]["cells"][s0[0]]["41"]["beta"]))
for T in (0.03794, d["0"]["cells"]["knn_emb_fb_min"]["41"]["beta"]):
    c = collections.Counter()
    for k, o in d.items():
        if k == "0": continue
        b = [o["cells"][x]["41"]["beta"] for x in survivors(o)]
        c["n"] += 1; c["any"] += bool(b); c["pos"] += any(x > 0 for x in b)
        P = any(x >= T for x in b); N = any(x <= -T for x in b)
        c["pos_ge"] += P; c["neg_ge"] += N; c["abs_ge"] += P or N; c["both"] += P and N
        c["n_surv_abs_ge"] += sum(abs(x) >= T for x in b)
    print("I1 T=%r" % T, dict(c))

# ---- item 2: HoVer swap transfer p, replaying hover_swap_analysis.main()'s RNG chain ----
sp = importlib.util.spec_from_file_location("hs", "analysis/ablation/hover_swap/hover_swap_analysis.py")
m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
by = collections.defaultdict(list)
for r in m.load(): by[r["pair"]].append(r)
S, Tr, C = [], [], []
for pid, rs in sorted(by.items()):
    aS, aW = m.draw_avg(rs, "SAME", "margin_on_A"), m.draw_avg(rs, "SWAP", "margin_on_A")
    bS, bW = m.draw_avg(rs, "SAME", "margin_on_B"), m.draw_avg(rs, "SWAP", "margin_on_B")
    S.append((((aS - aW) + (bW - bS)) / 2) / 3.0); Tr.append(((bS + aW) / 2) / 3.0); C.append(rs[0]["seed"])
S, Tr, C = np.array(S), np.array(Tr), np.array(C)
m.rng = np.random.default_rng(20260703)
so, spv = m.perm_p(S); m.cluster_boot(S, C); [np.mean(m.rng.choice(S, len(S))) for _ in range(m.NBOOT)]
to, tpv = m.perm_p(Tr)
print("I2 n=%d spec=%r p=%r | transfer=%r p(chain)=%r" % (len(S), so, spv, to, tpv))
m.rng = np.random.default_rng(20260703)
print("I2 transfer p(fresh rng 20260703)=%r" % m.perm_p(Tr)[1])

# ---- item 3: same-child cross-batch strict batch-sum gate agreement ----
rows = list(csv.DictReader(open("analysis/ablation/batch_swap_v2/calls.csv")))
cnt = collections.Counter(); zero = collections.Counter(); xchk = 0
for r in rows:
    a, b = float(r["margin_on_B"]) > 0, float(r["margin_on_Bp"]) > 0
    cnt[(a, b)] += 1
    zero["B"] += float(r["margin_on_B"]) == 0; zero["Bp"] += float(r["margin_on_Bp"]) == 0
    xchk += (a == (float(r["child_sum_B"]) > float(r["parent_B_sum"]))
             and b == (float(r["child_sum_Bp"]) > float(r["parent_Bp_sum"])))
ag = cnt[(True, True)] + cnt[(False, False)]
print("I3 IFBench n=%d agree=%d rate=%.4f 2x2=%s zero-margins=%s sum-column cross-check=%d/%d"
      % (len(rows), ag, ag / len(rows), dict(cnt), dict(zero), xchk, len(rows)))
cnt = collections.Counter(); arm = collections.Counter(); ties = collections.Counter()
for f in sorted(glob.glob("analysis/ablation/hover_swap/pairs/*/draws.jsonl")):
    for l in open(f):
        r = json.loads(l)
        mA = sum(m.thirds(r["scores_on_A_e"])) - sum(m.thirds(r["A_e_parent_scores_logged"]))
        mB = sum(m.thirds(r["scores_on_B_e"])) - sum(m.thirds(r["B_e_parent_scores_fresh"]))
        cnt[(mA > 0, mB > 0)] += 1; arm[(r["arm"], (mA > 0) == (mB > 0))] += 1
        ties["A"] += mA == 0; ties["B"] += mB == 0
n = sum(cnt.values()); ag = cnt[(True, True)] + cnt[(False, False)]
print("I3 HoVer n=%d agree=%d rate=%.4f 2x2=%s by-arm=%s zero-margins=%s"
      % (n, ag, ag / n, dict(cnt), dict(arm), dict(ties)))

# ---- item 3, float sensitivity (HoVer): the live gate's float sum, builtin sum() under 3.12 ----
cnt = collections.Counter(); flips = 0
for f in sorted(glob.glob("analysis/ablation/hover_swap/pairs/*/draws.jsonl")):
    for l in open(f):
        r = json.loads(l)
        a = sum(r["scores_on_A_e"]) > sum(r["A_e_parent_scores_logged"])
        b = sum(r["scores_on_B_e"]) > sum(r["B_e_parent_scores_fresh"])
        ea = sum(m.thirds(r["scores_on_A_e"])) > sum(m.thirds(r["A_e_parent_scores_logged"]))
        eb = sum(m.thirds(r["scores_on_B_e"])) > sum(m.thirds(r["B_e_parent_scores_fresh"]))
        cnt[(a, b)] += 1; flips += (a != ea) + (b != eb)
print("I3F HoVer float agree=%d/%d 2x2=%s verdicts differing from exact=%d"
      % (cnt[(True, True)] + cnt[(False, False)], sum(cnt.values()), dict(cnt), flips))

# ---- Stage-1: live gate (float) vs exact on the logged minibatch scores ----
for s in range(8):
    g = json.load(open(f"scratch/hover_stage1/stage1_seed{s}/gepa_result.json"))
    for i, t in enumerate(g["full_program_trace"]):
        if "new_subsample_scores" not in t: continue
        acc = "new_program_idx" in t
        fl = sum(t["new_subsample_scores"]) > sum(t["subsample_scores"])
        ex = sum(m.thirds(t["new_subsample_scores"])) > sum(m.thirds(t["subsample_scores"]))
        if acc != fl or acc != ex:
            print("I3T seed%d i=%d accepted=%s float_gate=%s exact_gate=%s parent=%s child=%s new_program_idx=%s"
                  % (s, i, acc, fl, ex, t["subsample_scores"], t["new_subsample_scores"], t.get("new_program_idx")))

# ---- item 4: false accepts (accepted child's full-valset mean <= parent's) ----
def fa_jsonl(path):
    val, acc = {}, []
    for l in open(path):
        e = json.loads(l)
        if e["event"] == "valset_evaluated": val[e["candidate_idx"]] = e
        elif e["event"] == "candidate_accepted": acc.append(e)
    lt = eq = n = fl_le = 0; full = True
    for a in acc:
        assert len(a["parent_ids"]) == 1, (path, a)
        c, p = val[a["new_candidate_idx"]], val[a["parent_ids"][0]]
        full &= all(x["num_examples_evaluated"] == x["total_valset_size"] == len(x["scores_by_val_id"]) for x in (c, p))
        ce, pe = exact_mean(list(c["scores_by_val_id"].values())), exact_mean(list(p["scores_by_val_id"].values()))
        n += 1; lt += ce < pe; eq += ce == pe; fl_le += c["average_score"] <= p["average_score"]
    vs = {x["total_valset_size"] for x in val.values()}
    return n, lt, eq, full, vs, fl_le, fl_le

def fa_gepa(path):
    g = json.load(open(path)); par, vs = g["parent_program_for_candidate"], g["prog_candidate_val_subscores"]
    sizes = {len(v) for v in vs}
    ex = [exact_mean(list(v.values())) for v in vs]
    fs = [sum(v.values()) / len(v) for v in vs]                # builtin sum(), compensated since 3.12
    nv = [naive_mean(list(v.values())) for v in vs]
    lt = eq = n = f_le = n_le = 0
    for i in range(1, len(par)):
        ps = [x for x in par[i] if x is not None]; assert len(ps) == 1, (path, i, par[i])
        q = ps[0]; n += 1; lt += ex[i] < ex[q]; eq += ex[i] == ex[q]
        f_le += fs[i] <= fs[q]; n_le += nv[i] <= nv[q]
    return n, lt, eq, len(sizes) == 1, sizes, f_le, n_le

def corpus(name, paths, fn):
    tot = collections.Counter()
    for p in paths:
        n, lt, eq, full, vs, f_le, n_le = fn(p)
        print("I4   %-28s %-70s n=%2d lt=%2d eq=%2d full=%s valset=%s float<=: sum312 %d naive %d" % (name, p, n, lt, eq, full, sorted(vs), f_le, n_le))
        tot["n"] += n; tot["lt"] += lt; tot["eq"] += eq; tot["f"] += f_le; tot["v"] += n_le
    r = (tot["lt"] + tot["eq"]) / tot["n"] if tot["n"] else float("nan")
    print("I4 TOTAL %-24s runs=%d n=%d lt=%d eq=%d lt+eq=%d rate=%.4f lt-only=%.4f | float<=: sum312 %d naive %d"
          % (name, len(paths), tot["n"], tot["lt"], tot["eq"], tot["lt"] + tot["eq"], r, tot["lt"] / max(tot["n"], 1), tot["f"], tot["v"]))

ifb = []
for c in sorted(glob.glob("logs/baseline_seed*_b*.config.json")):
    cfg = json.load(open(c))
    if cfg.get("max_metric_calls") == 2500 and cfg.get("results", {}).get("completed"):
        ifb.append(cfg)
ifb_b3 = [c["log_path"] for c in ifb if c["b"] == 3]; ifb_b1 = [c["log_path"] for c in ifb if c["b"] == 1]
corpus("IFBench baseline b3", ifb_b3, fa_jsonl)
corpus("IFBench baseline b1", ifb_b1, fa_jsonl)
corpus("IFBench baseline all10", ifb_b3 + ifb_b1, fa_jsonl)
corpus("IFBench phase2", sorted(glob.glob("logs/phase2/*.jsonl")), fa_jsonl)
corpus("HoVer Stage-1", sorted(glob.glob("scratch/hover_stage1/stage1_seed[0-7]/gepa_result.json")), fa_gepa)
for a in "BCT":
    corpus("HoVer state_dep " + a, sorted(glob.glob(f"analysis/state_dep/runs/{a}_seed[0-7]/gepa_result.json")), fa_gepa)
print("I4 --- non-study runs ---")
corpus("excl jsonl", ["logs/baseline_seed0_b3_20260626_214107.jsonl", "logs/baseline_seed0_b1_20260627_045843.jsonl",
                      "logs/ifbench_baseline_001.jsonl", "logs/faithful_20260626_211111.jsonl", "logs/smoke_001.jsonl",
                      "analysis/reflection_capture/capture.jsonl"], fa_jsonl)
corpus("excl gepa", ["scratch/hover_stage1/stage1_seed0_dry/gepa_result.json", "analysis/state_dep/runs/smoke_T_seed0/gepa_result.json",
                     "scratch/hover_probe/necrosis/gepa_result.json", "scratch/hover_probe/necrosis_dry/gepa_result.json"], fa_gepa)

print("I4 per-example score denominators seen:", sorted(DENOMS))

# ---- item 5: LMs in the 10 IFBench baseline configs, raw bytes of lines 8-9 ----
for c in sorted(glob.glob("logs/baseline_seed*_b*.config.json")):
    if json.load(open(c)) not in ifb: continue
    print("I5", os.path.basename(c), "|", linecache.getline(c, 8).strip(), "|", linecache.getline(c, 9).strip())
```
