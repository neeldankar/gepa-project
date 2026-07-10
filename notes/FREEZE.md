# FREEZE — `state-dependent-design-v1.md`

Date: 2026-07-09. Single source of truth for the freeze: **Part I** is the decision layer
(interpretation, explicitly labelled as such). **Part II** is the evidence layer (raw facts only,
every claim carrying file path + line numbers + verbatim quoted code).

Provenance discipline for Part II: all numerics were recomputed from raw artifacts
(`pairs/*/draws.jsonl`, `gepa_result.json:full_program_trace`, on-disk bytes). No answer is sourced
from `results.md`, `stage1_manifest.md`, `hover_swap_manifest.md`, or `run_summary.json`.
**Nothing in Part II is marked UNVERIFIED.** Producing it involved no spend, no API calls, no
embedding inference, no code changes, and no git write operations.

Status of the external review's blockers: **all repo facts requested are supplied and verified.
One of the review's premises turned out to be false** (D2). **Freeze cannot proceed as drafted.**

---
---

# PART I — DECISIONS

**Nothing here has been decided.** Seven decisions are open. Two block the freeze; the rest are
pin-it-down-before-you-run items that will silently rot the design if left implicit.

| # | Decision | Blocks freeze? | Who | My recommendation |
|---|---|---|---|---|
| D1 | Read Stage-2 numbers against the pre-registered map | **Yes** | **Neel only** | I must not make this call |
| D2 | V2 dose computation: the "$0" premise is false — fund it, shrink it, or drop it | **Yes** | Neel | Fund the ~$3 re-derivation |
| D3 | Accept-rate convention: 89/243 vs 87/243 | No, but pin before analysis | Neel | Use 89/243; document the 2 tie events |
| D4 | Pin the embedding model (no revision, no offline flag) | No, but pin before freeze | Neel | Pin snapshot + sha256 in the design |
| D5 | Pin `gepa==0.0.27` in the design's environment section | No, but pin before freeze | Neel | Pin it; two installs exist |
| D6 | What to do about the empty Class A survivor list | Downstream of D1 | Neel | Phase C (parent-lookahead), needs new prereg |
| D7 | Commit or discard the untracked `notes/` files | No | Neel | Commit; they're the audit trail |

---

## D1 — Read Stage-2 against the map  ⛔ BLOCKING

**Status: yours alone.** Per `notes/HANDOFF.md` and the standing do-not list, I do not make this
read. I state only the verified inputs.

Verified by recomputation (Part II, Task 1):

- pooled specificity `+0.027434842`, run-cluster CI `[+0.0149, +0.0415]`, MDE `0.0191`, perm p `0.0177`
- pooled transfer `+0.016918153`, CI `[−0.0040, +0.0367]`, MDE `0.0293`, perm p `0.3120`

Both reproduce the committed values to 9 decimal places.

What "specificity" and "transfer" *mean* operationally is now nailed down, and is worth registering
before you read the map: **both are evaluated on the two 3-example batches themselves (`A_e`,
`B_e`) — never on the valset, never on `D_pareto`, never on a held-out slice.** Whatever the map
says, it is a statement about one-step minibatch margins, not about downstream utility.

Two structural facts to hold while reading:

- Specificity's CI lower bound (`+0.0149`) sits **below** its MDE (`0.0191`).
- Transfer's CI spans 0.

The map's own rule: **no verdict if the CI spans a map boundary.** Whether either of the above
constitutes a boundary span is the call you have to make.

**What unblocks:** your read, written down somewhere citable.

---

## D2 — The V2 dose computation  ⛔ BLOCKING — its premise is false

**The brief assumed the per-candidate feedback texts for all 6 pairing candidates were already on
disk. They are not, for any of the 243 events.** Full evidence in Part II, Task 5 and C1/C2.

- The parent **is** evaluated on all 6 (`hover_swap_run.py:191`).
- But `make_reflective_dataset` is called only on `ebA` / `ebB` (`:201`), and the only text written
  is two bundled prompt files per event (`:205`).
- Byte-verified: 243/243 pair dirs hold exactly `{draws.jsonl, meta.json, reflect_in_SAME.txt,
  reflect_in_SWAP.txt}`; every reflect file has exactly 3 `# Example` blocks.
- **Events with 6/6 candidate feedback texts: 0 of 243.**
- Recoverable by parsing: **3 of 6** (the failure-matched `B_e`, inside `reflect_in_SWAP.txt`).
- `A_e` does not help: it is **disjoint** from `draw6` in 0/243 records.
- The remaining 3 of 6 have **neither feedback text nor a persisted parent score**.

### What re-deriving the missing 3 per event would cost

729 metric calls (243 × 3). Each HoVer metric call = 3 hops × 2 predictors = 6 LM calls ⇒ **4,374
LM calls**.

**Cost estimate ≈ $3.31.** *This is my estimate, not a measured price.* Derivation: solve two
observed spends for per-metric-call cost `m` and per-reflection-call cost `r`.

```
Stage-1 seed0:  302 metric calls + 32 reflection calls = $1.9078   (run_summary.json)
Swap, per pair:  45 metric calls +  6 reflection calls = $0.3049   (mean pair_cost_usd, n=243)
                 [45 = eb6(6) + ebA(3) + 6 draws × (3+3)]
  ⇒ m ≈ $0.004543 per metric call,  r ≈ $0.016744 per reflection call
  ⇒ 729 × $0.004543 ≈ $3.31
```

Both equations reproduce their observed spends exactly. Assumes linear cost and identical pricing
across the two runs. Treat as order-of-magnitude: **single-digit dollars, not zero and not seventy.**

### Determinism — the part that actually matters

Re-derivation requires **no LM reflection call**: feedback text is a pure function of the parent's
retrieval results. And the task LM is favourable:

```python
hover_swap_run.py:160:    task_lm = dspy.LM(MODEL, max_tokens=3000, cache=False)
```

No `temperature` argument ⇒ dspy's default `temperature=0.0`. So parent execution is
near-deterministic. **But not guaranteed** — temp-0 sampling is not a bitwise contract at the API
level, and `cache=False` means nothing is replayed. Re-derived feedback texts may not be byte-equal
to what the swap would have rendered in-run.

### Options

1. **Fund the re-derivation (~$3.31, 729 metric calls).** Gives all 6 per candidate. Requires a
   pre-registered acceptance rule for the determinism gap: re-execute the 3 *matched* `B_e` too and
   check the re-rendered text against the persisted `reflect_in_SWAP.txt` bytes. That is a free
   built-in control — if the matched 3 reproduce byte-exactly, the unmatched 3 are trustworthy.
   **Recommended.** The control is what makes this worth $3 rather than a coin flip.
2. **Shrink the dose to the 3 recoverable candidates.** $0, no new execution, but the "dose" is now
   over the failure-matched subset — a **biased sample by construction**, since `B_idx = combo` was
   *selected* to match the parent's score profile on `A_e`. Only defensible if the dose metric is
   explicitly redefined as conditional on failure-matching. Do not do this silently.
3. **Drop the dose computation** from v1 and freeze the design without it.

**Recommendation: option 1, with the byte-equality control as a pre-registered gate.** If the
matched-3 fail to reproduce, fall back to option 3 — not option 2.

**What unblocks:** your choice, plus (if option 1) a new prereg covering the re-run and the
determinism control. This is new spend and new execution, so it needs one.

---

## D3 — Accept-rate convention: 89/243 or 87/243

Pooled Stage-1 accept rate, recomputed from raw traces: **89/243 = 0.3663**, cross-checked against
`len(program_candidates) − 1` per seed. Per-seed table in Part II, Task 3b.

The wrinkle (Part II, C3): **two of those 89 accepts are IEEE-754 artifacts.** At `seed0 i=31` and
`seed5 i=23`, parent and child minibatch scores sum to the *same exact rational* (7/3), but
different addends give the child a double one ULP larger, so gepa's strict `>` fires:

```
parent [0.6666666666666666, 0.6666666666666666, 1.0] → 2.333333333333333
child  [1.0, 0.3333333333333333, 1.0]                → 2.3333333333333335
thirds: 7 → 7   (exact tie)                            gepa ACCEPT = True
```

On the exact integer-thirds lattice — the one `hover_swap_analysis.py:43-50` *asserts* every HoVer
score lies on — both are ties, and the rate is **87/243 = 0.3580**.

**Recommendation: use 89/243.** It is what the optimizer actually did, and any model of the run's
dynamics must match the run. But state the 2 tie-accepts explicitly in the design, because:

- if the design ever *simulates* the accept gate, it will use exact arithmetic and drift by 2 events;
- the screen's own `accept` column (`screen_part0.py:123`) recomputes the float rule and agrees at 89,
  so nothing downstream is currently inconsistent — but a reimplementation would silently break.

**What unblocks:** one line in the design fixing the convention.

---

## D4 — Pin the embedding model

`knn_emb_fb_min` is the sole surviving scorer, so the whole finding is downstream of one model
load — and that load is **unpinned**:

```python
screen_part3_features.py:35:    _ST = SentenceTransformer("all-MiniLM-L6-v2")
```

No `revision=`. No `local_files_only`. No `HF_HUB_OFFLINE` / `TRANSFORMERS_OFFLINE` anywhere in
`analysis/hover_screen/` (grep: zero matches). It resolved to whatever the local cache held.

What it resolved to, verified on disk:

```
snapshot  1110a243fdf4706b3f48f1d95db1a4f5529b4d41
weights   model.safetensors
sha256    53aa51172d142c89d9012cce15ae4d6cc0ca6895895114379cacb4fab128d9db
bytes     90868376
```

**Recommendation:** paste those four lines into the design's environment section, and add
`revision="1110a243..."` + `local_files_only=True` to any future load. Today the result is
reproducible only because the cache happens to hold that snapshot. That is not a guarantee, it's a
coincidence with a long half-life.

Also worth writing down while you're there, because the name misleads: `knn_emb_fb_min` is
**min over the ≤3 batch members of (mean over the 3 nearest strictly-prior archive blocks of
(1 − cosine))**. The `_min` is a batch-level aggregation, *not* a min over the k neighbours.

**What unblocks:** an environment section in the design.

---

## D5 — Pin `gepa==0.0.27`

**Two different gepa packages are installed on this machine, and they disagree about how acceptance
works.**

- The one that ran: `gepa 0.0.27`, at `scratch/hover_probe/.venv/lib/python3.12/site-packages/gepa/`,
  selected by `run_seeds.sh:7` (`PY=../hover_probe/.venv/bin/python`). Acceptance is **inline** at
  `engine.py:490-493`.
- The decoy: an editable `0.1.1` checkout at `~/Desktop/gepa/src/gepa`, which *does* have
  `strategies/acceptance.py` / `StrictImprovementAcceptance` and a deferred `ProposalOutput` counter.

This is not hypothetical. During this investigation a subagent cited `strategies/acceptance.py:45-48`
as the accept rule for these runs. **That file does not exist in 0.0.27.** The citation would have
entered the freeze document and been wrong. (A second subagent claim — that gepa's recorded accepts
disagree with the score-sum rule on 2 events — was also false; they disagree on **zero**. Both were
caught by recomputation and are logged in Part II under "Rejected claims".)

Budget facts, all from 0.0.27 and independently validated (`10 + 6×32 + 10×10 = 302`; `302×6 = 1812`
= seed0's logged `task_calls`, exact):

- `max_metric_calls = 300`; `|D_feedback| = 100`; `|D_pareto| = 10`; **no test split exists in Stage 1**
- counter increments: seed valset eval (+10, once), parent minibatch (+3/iter), child minibatch
  (+3/iter), full valset on accept (+10/accept). Merge ruled out — `use_merge=False`.
- **one acceptance costs exactly 10 metric calls.**

**Recommendation:** pin `gepa==0.0.27` in the design and name the interpreter path. Anyone reading
`~/Desktop/gepa` will derive a different engine.

**What unblocks:** one line in the design's environment section.

---

## D6 — The empty Class A survivor list

Downstream of D1; restated from `notes/HANDOFF.md` because D2's outcome changes the calculus.

The screen's pre-registered live-confirm clause keys on a **Class A** (pre-spend, deployable)
scorer passing criterion (a). **The Class A list is empty.** Every survivor is Class B — requires
the realized SI. So the screen's own rules trigger **no live-confirm decision.**

Relevant new fact from D2: the feedback-only variant needs only the parent's *retrieval* results
(no LM reflection call), and the task LM runs at temperature 0. A parent-lookahead sampler is
therefore cheap and near-deterministic — which is exactly the machinery option D2/1 would build and
validate. **If you fund D2, Phase C gets its feasibility check for free.**

Options, none pre-registered, each needing a new prereg:

1. **Accept the channel finding as-is** and write it up: real, concentrated in semantically-novel-
   feedback events, nothing pre-spend predicts it.
2. **Phase C: parent-lookahead sampler.** Score candidate batches by running the parent on them
   (retrieval only) and computing `knn_emb_fb_min`. The natural follow-up; the one the finding
   actually supports. **Recommended.**
3. **Re-screen `repr_min`** (only near-miss Class A, perm p = 0.0994) with more runs. Weak
   motivation; needs a power argument first.

**What unblocks:** D1, then a prereg.

---

## D7 — The untracked `notes/` files

Working tree is clean except the untracked notes files. Nothing else is uncommitted. `probe.py`
verified unchanged (`35eb46d4589a98f128058f8b9fa3e318ae517130c8b89d55a8df76c3a31b28d4`).

```
?? notes/HANDOFF.md
?? notes/SESSION_2026-07-09_hover_screen_phaseA.md
?? notes/SESSION_2026-07-09_hover_screen_phaseB.md
?? notes/FREEZE.md          # this file
```

**Recommendation: commit all of them.** This file is the evidence the external review asked for;
leaving it untracked means the freeze cites facts with no commit to point at.

**What unblocks:** `git add notes/ && git commit`.

---

## Carried do-not list (still binding)

- Do not modify `scratch/hover_stage1/`, `scratch/hover_probe/probe.py`, or any frozen corpus.
- Do not key on `full_program_trace` indices (seeds 2 and 6 have child-less entries).
- Do not put interpretation in `results.md`, `spec.md`, `census.md`, `plan.md`, or the manifest.
  *(Part I of this file is the interpretation layer; Part II holds the same discipline as those files.)*
- Do not use `accept` as a regressor (collider).
- Do not create `APPROVED` yourself.
- Do not synthesize or splice reflection inputs — real parent execution only.
- Do not re-run Stage-2. The corpus is frozen at `stage2-pre-analysis`.
- Do not update `findings_summary.md` from a Claude session.

---

## The short version

Freeze is blocked on two things. **D1 is a read only you can do.** **D2 is a premise that turned
out to be false**: the dose computation was scoped as $0 because the six per-candidate feedback
texts were assumed to be on disk, and they are not — for any of the 243 events. Re-deriving them is
729 metric calls and roughly $3, near-deterministic, with a free byte-equality control available
from the 3 texts that *do* exist. That is a small bill for a premise that would otherwise have been
carried into a frozen design unexamined.

Everything else the review asked for checked out and reproduced exactly.

---
---

# PART II — EVIDENCE

Raw facts only. No interpretation below this line.

## CONTRADICTIONS

### C1 — **V2-BLOCK.** The per-candidate feedback texts for all 6 candidates do not exist on disk.

The brief states: "The swap's failure-match pairing evaluated the parent on 6 candidates per event
(243 events). The planned dose computation needs the per-candidate FEEDBACK TEXTS for all 6."

The parent **is** evaluated on all 6 (`analysis/ablation/hover_swap/hover_swap_run.py:191`):

```python
    eb6 = adapter.evaluate(cand6, parent_cand, capture_traces=True)
```

But feedback **text** is rendered only by `make_reflective_dataset`, which is called only on `ebA`
(the 3 `A_e`) and `ebB` (the 3 failure-matched `B_e`), and the only text writes are the two
`reflect_in_<ARM>.txt` files (`hover_swap_run.py:199-205`):

```python
    for arm, eb in {"SAME": ebA, "SWAP": ebB}.items():
        adapter.rng = random.Random(seed_of(seed, trace_i, arm))
        rd = adapter.make_reflective_dataset(parent_cand, eb, [comp])
        reflect_in = IPS.prompt_renderer({"current_instruction_doc": parent_cand[comp], "dataset_with_feedback": rd[comp]})
        if not byte_verify(reflect_in):
            raise RuntimeError(f"reflect_in byte-verify FAILED seed{seed} trace_i{trace_i} {arm}")
        open(os.path.join(outdir, f"reflect_in_{arm}.txt"), "w", encoding="utf-8").write(reflect_in)
```

**Events with all 6 per-candidate feedback texts on disk: 0 of 243.** See Task 5a.

### C2 — The parent's scores on all 6 candidates are also not persisted.

Only the 3 failure-matched scores survive, as `B_e_parent_scores_fresh` (`hover_swap_run.py:194`,
`:219`, `:225`). The 3 non-matched members of `draw6` leave no per-candidate score artifact and no
feedback text.

### C3 — Two of the 89 Stage-1 accepts are IEEE-754 tie artifacts.

`seed0 i=31` and `seed5 i=23`. In both, parent and child minibatch scores sum to the **same exact
rational** (7/3), but the different addends produce a child double one ULP larger, so the strict
`>` criterion fires:

```
seed0 i=31: parent=[0.6666666666666666, 0.6666666666666666, 1.0]
            child =[1.0, 0.3333333333333333, 1.0]
            sum(parent)=2.333333333333333   sum(child)=2.3333333333333335
            thirds: 7 -> 7  (exact tie)     gepa ACCEPT=True

seed5 i=23: parent=[1.0, 0.6666666666666666, 0.6666666666666666]
            child =[1.0, 1.0, 0.3333333333333333]
            sum(parent)=2.333333333333333   sum(child)=2.3333333333333335
            thirds: 7 -> 7  (exact tie)     gepa ACCEPT=True
```

Under exact arithmetic (the integer-thirds lattice that `hover_swap_analysis.py:43-50` asserts all
HoVer scores lie on), both are ties and the strict rule would reject. Accept rate under the
exact-thirds rule is **87/243 = 0.3580**. **89/243 = 0.3663 is authoritative as-run** and is what
Task 3 states.

### C4 — Two different `gepa` packages exist on this machine. Only 0.0.27 ran.

Stage 1 was launched with `PY=../hover_probe/.venv/bin/python` (`scratch/hover_stage1/run_seeds.sh:7`),
which resolves `gepa` to **0.0.27** at
`scratch/hover_probe/.venv/lib/python3.12/site-packages/gepa/`
(`gepa-0.0.27.dist-info/METADATA`: `Version: 0.0.27`).

A second, unrelated editable checkout exists at `~/Desktop/gepa/src/gepa` (version 0.1.1). Its
internals differ: 0.1.1 has `strategies/acceptance.py` (`StrictImprovementAcceptance`) and a
deferred `ProposalOutput` counter; **0.0.27 has no `strategies/acceptance.py`** and decides
acceptance inline. All code citations in Tasks 2 and 3 below are from 0.0.27.

---

## V1 VERDICT — **NOT a V1-FLIP**

The `knn_emb_fb_min` archive contains **reflected-3-only** feedback texts. Deciding lines in Task 4.

---

## TASK 1 — Operational definitions: specificity and transfer

Source of truth: `analysis/ablation/hover_swap/hover_swap_analysis.py`.

Header docstring, `:10-12`:

```
  SPECIFICITY_A = margin(SAME on A) - margin(SWAP on A)   (both on A -> parent cancels)
  SPECIFICITY_B = margin(SWAP on B) - margin(SAME on B)   (symmetric replication)
  pooled specificity = mean of the two ; pooled transfer = mean(margin(SAME on B), margin(SWAP on A))
```

Per-draw margin construction, `:67-77`:

```python
        for r in rs:
            cA, cB = thirds(r["scores_on_A_e"]), thirds(r["scores_on_B_e"])
            pA, pB = thirds(r["A_e_parent_scores_logged"]), thirds(r["B_e_parent_scores_fresh"])
            rows.append(dict(
                pair=pid, seed=r["seed"], arm=r["arm"], draw=r["draw"],
                margin_on_A=sum(cA) - sum(pA),          # integer thirds
                margin_on_B=sum(cB) - sum(pB),          # integer thirds
                child_A=sum(cA), child_B=sum(cB),
                delta_A=[c - p for c, p in zip(cA, pA)],  # per-example, integer thirds
                delta_B=[c - p for c, p in zip(cB, pB)],
            ))
```

Draw-averaging within arm, `:84-87`:

```python
def draw_avg(rs, arm, field):
    """v2 draw_avg, verbatim (batch_swap_v2_analysis.py:26)."""
    v = [float(r[field]) for r in rs if r["arm"] == arm]
    return float(np.mean(v)) if v else np.nan
```

### 1a. SPECIFICITY

`hover_swap_analysis.py:125-131`:

```python
        mA_SAME = draw_avg(rs, "SAME", "margin_on_A")
        mA_SWAP = draw_avg(rs, "SWAP", "margin_on_A")
        mB_SAME = draw_avg(rs, "SAME", "margin_on_B")
        mB_SWAP = draw_avg(rs, "SWAP", "margin_on_B")
        if np.any(np.isnan([mA_SAME, mA_SWAP, mB_SAME, mB_SWAP])):
            continue
        spec.append((((mA_SAME - mA_SWAP) + (mB_SWAP - mB_SAME)) / 2) / 3.0)  # pooled specificity
```

- **What is compared to what.** SAME-arm children (reflection input built from the parent executing
  on the event's own batch `A_e`) versus SWAP-arm children (reflection input built from the parent
  executing on the failure-matched batch `B_e`). K=3 reflection draws per arm, draw-averaged.
- **Evaluated on WHAT set.** On the two 3-example batches themselves. Component A is evaluated on
  `A_e`; component B is evaluated on `B_e`. Every child is scored on both batches
  (`scores_on_A_e`, `scores_on_B_e`, written at `hover_swap_run.py:212-217`).
  **Not** the valset, **not** `D_pareto`, **not** a held-out slice.
- **Baseline.** `A_e_parent_scores_logged` (Stage-1 logged parent scores on `A_e`) for the A term;
  `B_e_parent_scores_fresh` (parent re-run on `B_e`) for the B term. On any single batch both arms
  share the same parent baseline, so it cancels in the difference.

### 1b. TRANSFER

`hover_swap_analysis.py:132`:

```python
        transf.append(((mB_SAME + mA_SWAP) / 2) / 3.0)                        # pooled transfer
```

Mean of `margin(SAME on B)` and `margin(SWAP on A)`: the child's improvement over the parent
measured on **the batch that the child's reflection input never saw**. Evaluation set is the
opposite 3-example batch. Not the valset, not `D_pareto`.

### 1c. Per-event unit and pooling

- **Per-event unit.** One pair `pid` (= one reflection event, keyed `seed{S}_i{trace_i}`)
  contributes exactly one scalar to `spec` and one to `transf`; both are appended once per pair
  inside `for pid, rs in sorted(by_pair.items())` (`:131-132`). Units are score points: an
  integer-thirds margin over 3 examples, divided by 3.0.
- **Aggregation.** Unweighted arithmetic mean over the 243 per-pair values. The reported point
  estimate is `obs` from `perm_p`, `:90-95`:

```python
def perm_p(x):
    """Within-pair sign-flip permutation two-sided p for H0 mean=0 (v2, verbatim)."""
    x = np.asarray(x)
    obs = x.mean()
    null = np.array([(x * rng.choice([-1.0, 1.0], len(x))).mean() for _ in range(NPERM)])
    return obs, float((np.abs(null) >= abs(obs) - 1e-12).mean())
```

  `obs = x.mean()` — not weighted, not cluster-aware. Clustering enters only the CI/SE
  (`cluster_boot`), never the point estimate.

### Independent recomputation from raw `pairs/*/draws.jsonl`

Keys used per draw row: `arm`, `scores_on_A_e`, `scores_on_B_e`, `A_e_parent_scores_logged`,
`B_e_parent_scores_fresh`, `seed`. 243 pair dirs × 6 rows (2 arms × 3 draws) = 1458 rows.

```python
import os, json, collections, statistics as st
P="analysis/ablation/hover_swap/pairs"
def thirds(xs):
    out=[]
    for v in xs:
        t=round(v*3); assert abs(v*3-t)<1e-9; out.append(int(t))
    return out
spec=[]; transf=[]; per_seed=collections.Counter(); nrows=0
for pid in sorted(os.listdir(P)):
    rs=[json.loads(l) for l in open(os.path.join(P,pid,"draws.jsonl"))]
    nrows+=len(rs); m={}
    for r in rs:
        cA,cB=thirds(r["scores_on_A_e"]),thirds(r["scores_on_B_e"])
        pA,pB=thirds(r["A_e_parent_scores_logged"]),thirds(r["B_e_parent_scores_fresh"])
        m.setdefault((r["arm"],"A"),[]).append(sum(cA)-sum(pA))
        m.setdefault((r["arm"],"B"),[]).append(sum(cB)-sum(pB))
    avg=lambda a,b: st.fmean(m[(a,b)])
    mAS,mAW,mBS,mBW=avg("SAME","A"),avg("SWAP","A"),avg("SAME","B"),avg("SWAP","B")
    spec.append((((mAS-mAW)+(mBW-mBS))/2)/3.0)
    transf.append(((mBS+mAW)/2)/3.0)
    per_seed[rs[0]["seed"]]+=1
```

Output:

```
n_pairs=243 n_rows=1458 per_seed={0: 32, 1: 34, 2: 28, 3: 33, 4: 27, 5: 34, 6: 28, 7: 27}
SPEC   = 0.0274348422  round4=+0.0274
TRANSF = 0.0169181527  round4=+0.0169
```

**Recomputation matches the committed +0.0274 / +0.0169 to 4 decimal places** (and to 9 dp against
`results.md:22-23`, which records `+0.027434842` / `+0.016918153`).

---

## TASK 2 — Split sizes and budget config (Stage 1 HoVer)

### 2a. Split sizes

`scratch/hover_stage1/stage1_run.py:39-42`:

```python
SPEND_CAP = 0.30 if DRY else 5.00
MM = 14 if DRY else 300
N_VAL = 4 if DRY else 10
N_TRAIN = 6 if DRY else 100     # frozen was 12; bigger trainset per Stage-1 brief
```

Split construction, `:131-141`:

```python
    # ---------- imperfect claims from the freshly-graded threehop slice ----------
    recs = [orjson.loads(l) for l in open(GRADED, "rb")]
    imperfect = [r for r in recs if r["recall"] < 1.0]
    imperfect.sort(key=lambda r: (-r["recall"], r["claim"]))   # same key as frozen
    need = N_TRAIN + N_VAL
    if len(imperfect) < need:
        chosen = (imperfect * ((need // len(imperfect)) + 1))[:need]  # frozen cycling fallback
    else:
        chosen = imperfect[:need]
    examples = [dspy.Example(claim=r["claim"], titles=r["gold"]).with_inputs("claim") for r in chosen]
    trainset, valset = examples[:N_TRAIN], examples[N_TRAIN:need]
```

| quantity | value | source |
|---|---|---|
| \|D_feedback\| (GEPA trainset) | **100** | `stage1_run.py:42` `N_TRAIN = 100`; `:141` `trainset = examples[:N_TRAIN]` |
| \|D_pareto\| (valset) | **10** | `:41` `N_VAL = 10`; `:135` `need = 110`; `:141` `valset = examples[100:110]` |
| \|test\| | **does not exist** | `stage1_run.py` constructs only `trainset` and `valset` (`:141`) and passes only those to `gepa.compile(...)` (`:170`). No third split is loaded or sliced anywhere in the run config. |

### 2b. `max_metric_calls` and the counter increment sites

`stage1_run.py:40`, `:160-161`:

```python
MM = 14 if DRY else 300
```
```python
    gepa = dspy.GEPA(
        metric=metric, reflection_lm=reflection_lm, max_metric_calls=MM,
```

→ **`max_metric_calls = 300`** per Stage-1 run.

The counter is `GEPAState.total_num_evals`. In the installed **gepa 0.0.27**, it is mutated at
exactly five sites (exhaustive grep for `increment_evals` / `total_num_evals =` / `+=`):

```
gepa/core/state.py:279                                        self.total_num_evals += count
gepa/core/state.py:661                                        gepa_state.total_num_evals = num_evals_run
gepa/core/engine.py:137                                       state.increment_evals(num_actual_evals)
gepa/proposer/merge.py:392                                    state.increment_evals(actual_evals_count)
gepa/proposer/reflective_mutation/reflective_mutation.py:164  state.increment_evals(len(subsample_ids))
gepa/proposer/reflective_mutation/reflective_mutation.py:332  state.increment_evals(actual_evals_count)
```

(`state.py:279` is the body of `increment_evals` itself, `:273-279`:)

```python
    def increment_evals(self, count: int) -> None:
        """Increment total_num_evals and notify all registered hooks.

        Args:
            count: Number of evaluations to add.
        """
        self.total_num_evals += count
```

**Every call category that hits the counter**, ruled in or out for these runs:

| # | Category | Site | Adds | Fired in Stage 1? |
|---|---|---|---|---|
| 1 | Initial/base (seed) program eval on the full valset | `state.py:661` | `len(scores_by_val_id)` = **10** | **YES**, once |
| 2 | Minibatch eval of the **parent** program | `reflective_mutation.py:164` | `len(subsample_ids)` = **3** | **YES**, per iteration |
| 3 | Minibatch eval of the **child** (proposed) program | `reflective_mutation.py:332` | `actual_evals_count` = **3** | **YES**, per iteration |
| 4 | Full valset / `D_pareto` eval on **acceptance** | `engine.py:137` | `num_actual_evals` = **10** | **YES**, per accept |
| 5 | Merge-candidate eval | `merge.py:392` | `actual_evals_count` | **NO** — `use_merge=False` |

Category 1, `gepa/core/state.py:642-661`:

```python
        num_evals_run = 0

        eval_result = valset_evaluator(seed_candidate)
        ...
        num_evals_run += len(eval_result.scores_by_val_id)
        ...
        gepa_state.num_full_ds_evals = 1
        gepa_state.total_num_evals = num_evals_run
```

Category 2, `gepa/proposer/reflective_mutation/reflective_mutation.py:163-164`:

```python
        eval_curr = self.adapter.evaluate(minibatch, curr_prog, capture_traces=True)
        state.increment_evals(len(subsample_ids))
```

Category 3, same file `:332`:

```python
        state.increment_evals(actual_evals_count)
```

Category 4, `gepa/core/engine.py:132-137`:

```python
        val_ids = self.val_evaluation_policy.get_eval_batch(valset, state)

        outputs_by_val_idx, scores_by_val_idx, objective_by_val_idx, num_actual_evals = state.cached_evaluate_full(
            program, list(val_ids), valset.fetch, self.evaluator
        )
        state.increment_evals(num_actual_evals)
```

Category 5 ruled OUT by config, `stage1_run.py:162-164`:

```python
        reflection_minibatch_size=3, candidate_selection_strategy="pareto",
        component_selector="round_robin", num_threads=1, track_stats=True,
        use_merge=False,
```

**Independent validation of the 5-category model** (arithmetic only, nothing run): for seed 0,
32 events and 10 accepts ⇒ `total_num_evals = 10 + 6×32 + 10×10 = 302`. Each HoVer metric call
issues 3 hops × 2 predictors = 6 LM calls ⇒ `302 × 6 = 1812`, which equals the logged
`task_calls = 1812` in `stage1_seed0/run_summary.json` exactly.

### 2c. Per-accept valset eval size

Accept path, `gepa/core/engine.py:490-493` and `:513-519`:

```python
                # Acceptance: require strict improvement on subsample
                old_sum = sum(proposal.subsample_scores_before or [])
                new_sum = sum(proposal.subsample_scores_after or [])
                if new_sum <= old_sum:
```
```python
                # Accept: full eval + add
                new_idx, _ = self._run_full_eval_and_add(
                    new_program=proposal.candidate,
                    state=state,
                    parent_program_idx=proposal.parent_program_ids,
                )
```

`_run_full_eval_and_add` evaluates on the batch returned by the validation evaluation policy. The
default policy is `FullEvaluationPolicy`, `gepa/strategies/eval_policy.py:34-41`:

```python
class FullEvaluationPolicy(EvaluationPolicy[DataId, DataInst]):
    """Policy that evaluates all validation instances every time."""

    def get_eval_batch(
        self, loader: DataLoader[DataId, DataInst], state: GEPAState, target_program_idx: ProgramIdx | None = None
    ) -> list[DataId]:
        """Always return the full ordered list of validation ids."""
        return list(loader.all_ids())
```

The accepted candidate is new, so its valset cache is empty and `num_actual_evals = len(val_ids)`.

→ **One acceptance triggers exactly |D_pareto| = 10 metric calls.** Corroborated by the
`10 + 6×32 + 10×10 = 302 → 1812` reconciliation above.

---

## TASK 3 — Stage 1 accept rate (recomputed from raw traces)

### 3a. The acceptance field and the rule that sets it

The trace field is **`new_program_idx`**, present on a `full_program_trace` entry iff that event
was accepted. It is written only on the accept path, `gepa/core/engine.py:194`:

```python
        state.full_program_trace[-1]["new_program_idx"] = new_program_idx
```

reached only via `_run_full_eval_and_add`, which is called only after the acceptance check passes
(`engine.py:513-519`, quoted in 2c). The rule itself is inline at `engine.py:490-493`:

```python
                # Acceptance: require strict improvement on subsample
                old_sum = sum(proposal.subsample_scores_before or [])
                new_sum = sum(proposal.subsample_scores_after or [])
                if new_sum <= old_sum:
```

i.e. accept iff the sum of the child's minibatch scores **strictly exceeds** the sum of the
parent's. `subsample_scores_before` is persisted to the trace as `subsample_scores`;
`subsample_scores_after` as `new_subsample_scores`.

(Per C4: gepa 0.0.27 has **no** `strategies/acceptance.py`. The `StrictImprovementAcceptance` class
exists only in the unrelated 0.1.1 checkout, which did not run these seeds.)

### 3b. Per-seed and pooled

An EVENT is a child-bearing trace entry, i.e. one where `new_subsample_scores is not None` — the
same definition used by `analysis/hover_screen/screen_part0.py:44`:

```python
    childbearing = [t for t in trace if t.get("new_subsample_scores") is not None]
```

Script run:

```python
import json
for s in range(8):
    g = json.load(open(f"scratch/hover_stage1/stage1_seed{s}/gepa_result.json"))
    ev = [e for e in g["full_program_trace"] if e.get("new_subsample_scores") is not None]
    a  = sum("new_program_idx" in e for e in ev)
    ncand = len(g["program_candidates"])
    print(s, len(ev), a, a/len(ev), ncand-1)
```

| seed | events | accepts | rate | cross-check `len(program_candidates) − 1` |
|---|---|---|---|---|
| 0 | 32 | 10 | 0.3125 | 10 |
| 1 | 34 | 10 | 0.2941 | 10 |
| 2 | 28 | 12 | 0.4286 | 12 |
| 3 | 33 | 10 | 0.3030 | 10 |
| 4 | 27 | 13 | 0.4815 | 13 |
| 5 | 34 | 9 | 0.2647 | 9 |
| 6 | 28 | 12 | 0.4286 | 12 |
| 7 | 27 | 13 | 0.4815 | 13 |

**Pooled: 89 / 243 = 0.3663.**

Event counts per seed are `{0:32, 1:34, 2:28, 3:33, 4:27, 5:34, 6:28, 7:27}` — **matching** the
established map. Child-less entries confirmed at seed2 `i ∈ {5,15}` and seed6 `i = 27`.

Rule-agreement check across all 243 events: accepts by `new_program_idx` = 89; accepts by
re-applying the float rule `sum(new) > sum(old)` to the persisted trace fields = 89;
**0 disagreements**. Accepts by the exact integer-thirds rule = 87 (see C3).

---

## TASK 4 — Screen archive semantics for `knn_emb_fb_min`

Code integrity: `analysis/hover_screen/screen_part3_features.py` sha256
`36bb15788c730fcffdfdbd99252b8d6100af6319322df6d1743b4d9de6f5e270`, byte-identical to both
`8be66ac` and `2fb33dd` (`git diff --quiet` returns clean against each).

### 4a. The archive-building code, and the IN/OUT ruling

The archive is advanced **strictly after** the current event's row is emitted,
`screen_part3_features.py:325-340`:

```python
            out_rows.append(row)

            # ----- advance archives (STRICTLY after computing this event) -----
            for slot, blk in enumerate(blks):
                pos = ev["subsample_ids"][slot]
                pool[pos].append((o, ev["subsample_scores"][slot], "parent"))
                pool[pos].append((o, ev["new_subsample_scores"][slot], "child"))
                visits[pos].append(o)
                fb_t, full_t = variant_texts(blk)
                arch_items["fb"].append(fb_t)
                arch_items["full"].append(full_t)
                if HAVE_EMB:
                    arch_emb["fb"].append(emb[(pid, slot, "fb")])
                    arch_emb["full"].append(emb[(pid, slot, "full")])
                sig_archive.add(cur_sigs[slot])
                pair_archive |= cur_pairs_all[slot]
```

Per-seed reset and per-seed event filter, `:135-145`:

```python
    for seed in range(8):
        evs = sorted([e for k, e in ev_index.items() if e["seed"] == seed],
                     key=lambda e: e["ordinal"])
        pool = collections.defaultdict(list)      # pos -> [(ordinal, score, kind)]
        visits = collections.defaultdict(list)    # pos -> [ordinal]
        arch_items = {"fb": [], "full": []}       # per-example archive texts, ordinal order
        arch_concat_len = None                    # rebuilt per event from arch_items
        arch_emb = {"fb": [], "full": []}
```

The archive size consumed by the k-NN is snapshotted **before** the per-slot loop, `:203`:

```python
            n_arch = len(arch_items["fb"])
```

**When scoring event `t` of run `r`, the `fb` archive contains the `## Feedback` text of the 3
reflected minibatch members of every strictly-prior event of run `r`, and nothing else.**

| Candidate | Verdict | Deciding line |
|---|---|---|
| The 3 reflected/chosen examples of baseline events `1..t-1`, same run | **IN** | `:334` / `:337`, inside the "STRICTLY after" block at `:327` |
| Swapped-batch feedback texts from the swap machinery | **OUT** | Only `reflect_in_SAME.txt` is ever opened (`:113`). Grep for `reflect_in_SWAP` across `analysis/hover_screen/` returns **zero** references. |
| Any of the 6 pairing candidates beyond the reflected 3 | **OUT** | The archive is keyed to `ev["subsample_ids"]` (= `A_e_pos`, the reflected 3) via `slot` over the 3 blocks of `reflect_in_SAME.txt` (`:328-329`). The `draw6` candidates never enter. |
| Event `t`'s own batch members (self-inclusion / leakage) | **OUT** | The advance block runs after `out_rows.append(row)` (`:325`) and after the k-NN; `n_arch` snapshotted at `:203` |
| Events from other seeds/runs | **OUT** | `arch_items`/`arch_emb` reset inside the `for seed in range(8)` loop (`:140-145`); `evs` filtered to `e["seed"] == seed` (`:136`) |

Provenance trace, backwards, each hop quoted:

1. Output column `knn_emb_fb_min` ← `:313`:
   ```python
                   row.update(agg(knn_e["fb"], "knn_emb_fb", with_n=False))
   ```
   where `agg` emits `_mean/_max/_min/_std`, `:49-52`:
   ```python
        out[f"{prefix}_mean"] = float(v.mean())
        out[f"{prefix}_max"] = float(v.max())
        out[f"{prefix}_min"] = float(v.min())
        out[f"{prefix}_std"] = float(v.std(ddof=0))
   ```
2. Per-member value ← `:237-243` (quoted in 4c).
3. Archive embeddings `arch_emb["fb"]` ← `:337` (quoted above).
4. Embedding table ← `:129-130`:
   ```python
        M = _ST.encode(texts, batch_size=64, show_progress_bar=False, normalize_embeddings=True)
        emb = {k: M[i] for i, k in enumerate(keys)}
   ```
5. Text is feedback-only ← `:116-119`:
   ```python
    def variant_texts(blk):
        fb = blk["Feedback"]
        full = blk["Inputs"] + "\n" + blk["Generated Outputs"] + "\n" + blk["Feedback"]
        return fb, full
   ```
6. Raw source file ← `:111-114`:
   ```python
    blocks_by_pid = {}
    for pid in sorted(os.listdir(PAIRS)):
        text = open(os.path.join(PAIRS, pid, "reflect_in_SAME.txt"), encoding="utf-8").read()
        blocks_by_pid[pid] = parse_si(text, pid)
   ```
   i.e. `analysis/ablation/hover_swap/pairs/seed<S>_i<T>/reflect_in_SAME.txt`.
7. `subsample_ids` ← `events_index.json`, written by `screen_part0.py:120-128` from child-bearing
   Stage-1 trace entries.

### 4b. Event ordering

Ordering is by event **`ordinal`** — position among child-bearing `full_program_trace` entries, in
trace order. Not a timestamp. Assigned at `screen_part0.py:120-125`:

```python
        for ordinal, t in enumerate(cb):
            key = (seed, t["i"])
            b_values.add(len(t["subsample_ids"]))
            accept = sum(t["new_subsample_scores"]) > sum(t["subsample_scores"])
            n_accept += int(accept)
            events[key] = dict(seed=seed, trace_i=t["i"], ordinal=ordinal, idx=ordinal + 1,
```

Consumed by the sort at `screen_part3_features.py:136-137`.

**"Strictly prior" means `< t`, strict.** The archive advance is gated behind the comment
"STRICTLY after computing this event" (`:327`) and executes after the row is emitted (`:325`), and
`n_arch` is read at `:203` before any of event `t`'s members are appended.

### 4c. The exact k-NN computation

`screen_part3_features.py:237-243`:

```python
                    if HAVE_EMB:
                        if n_arch >= 3:
                            A = np.stack(arch_emb[var])
                            s = A @ emb[(pid, slot, var)]
                            knn_e[var].append(float(np.mean(1 - np.sort(s)[-3:])))
                        else:
                            knn_e[var].append(np.nan)
```

| property | value |
|---|---|
| metric | `1 − cosine similarity`. `s = A @ emb[...]` is a dot product of L2-normalized vectors, so it *is* cosine; novelty is `1 - s`. |
| k | **3** — `np.sort(s)[-3:]` takes the 3 largest similarities (3 nearest neighbours). |
| fewer than k prior items | guarded by `if n_arch >= 3:` (`:238`), else `np.nan` (`:243`). `n_arch` grows by 3 per prior event, so only ordinal 0 of each run is NaN. |
| aggregation over the k distances | **mean** — `np.mean(1 - np.sort(s)[-3:])` (`:241`). |
| batch-level aggregation giving `_min` | a **separate** min over the ≤3 batch members: `agg(knn_e["fb"], ...)` (`:313`) → `out[f"{prefix}_min"] = float(v.min())` (`:51`). |
| normalization | **L2**, applied once at encode time via `normalize_embeddings=True` (`:129`). |

So the full definition of `knn_emb_fb_min` is: **min over the ≤3 batch members of (mean over the 3
nearest strictly-prior archive blocks of (1 − cosine))**. The `_min` is *not* a min over the k
neighbours.

Embedding model load, `:33-40`:

```python
try:
    from sentence_transformers import SentenceTransformer
    _ST = SentenceTransformer("all-MiniLM-L6-v2")
    HAVE_EMB = True
except Exception as e:  # noqa: BLE001
    _ST = None
    HAVE_EMB = False
    print(f"[embedding variant OFF: {type(e).__name__}: {e}]")
```

- Model name: `all-MiniLM-L6-v2`.
- **Revision/commit pin: NONE.** No `revision=` argument anywhere.
- **Offline enforcement: NONE.** Grep across `analysis/hover_screen/` for `local_files_only`,
  `HF_HUB_OFFLINE`, `TRANSFORMERS_OFFLINE`, `revision=` returns zero matches. It resolves through
  the standard HF hub path, which uses the local cache when present.
- Resolved snapshot: `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`.
- Local path:
  `~/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2/snapshots/1110a243fdf4706b3f48f1d95db1a4f5529b4d41/model.safetensors`

**Weights file hash (file was hashed, not loaded):**

```
sha256  53aa51172d142c89d9012cce15ae4d6cc0ca6895895114379cacb4fab128d9db
bytes   90868376
```

No `pytorch_model.bin` exists in the snapshot; the single-file `model.safetensors` is the weights.

### 4d. One sentence of fact

**The archive contains reflected-3-only texts** — specifically the `## Feedback` section of each of
the 3 reflected minibatch example-blocks (`ev["subsample_ids"]`) of every strictly-prior, same-seed
event, and nothing else.

**→ This is NOT a V1-FLIP.**

---

## TASK 5 — Swap-corpus feedback persistence

### Premise check

The pairing plan **does** record 6 candidates per event. 243 records; each carries a 6-element
`draw6_pos` / `draw6_threehop_ids`. `analysis/ablation/hover_swap/pairing_plan.jsonl:1`:

```json
{"seed": 0, "trace_i": 0, "A_e_pos": [23, 8, 11], "A_e_threehop_ids": [181, 175, 193], "A_e_parent_scores": [0.3333333333333333, 0.6666666666666666, 1.0], "parent_candidate_idx": 0, "ev_rng_seed": 0, "draw6_pos": [5, 36, 52, 56, 65, 68], "draw6_threehop_ids": [133, 194, 142, 60, 211, 136]}
```

The parent **is** evaluated on all 6, `hover_swap_run.py:183`, `:191-196`:

```python
    A_e = [ex(p) for p in A_pos]; cand6 = [ex(p) for p in draw6]
```
```python
    eb6 = adapter.evaluate(cand6, parent_cand, capture_traces=True)
    combo, l1, exact = multiset_match(A_par_logged, list(eb6.scores))
    B_idx = list(combo); B_pos = [draw6[i] for i in B_idx]
    B_par_fresh = [eb6.scores[i] for i in B_idx]
    ebB = sub_batch(eb6, B_idx, EvaluationBatch); B_e = [cand6[i] for i in B_idx]
    ebA = adapter.evaluate(A_e, parent_cand, capture_traces=True)
```

**But feedback text is never rendered for the 6.** `make_reflective_dataset` is called only on
`ebA` and `ebB`, and the only text write is the two `reflect_in_<ARM>.txt` files (`:199-205`,
quoted in C1). The per-draw writes (`:214-221`) persist scores and `child_instruction` only — no
feedback text.

`B_e ⊂ cand6` (3 of the 6, by `B_idx = combo`). `A_e` is **disjoint** from `draw6`: checked across
all 243 records, `set(A_e_pos) & set(draw6_pos)` is empty in **0/243** cases.

### 5a. On-disk coverage

**Events with all 6 per-candidate feedback texts: 0 of 243.** Events with fewer: **243 of 243.**

Every one of the 243 pair dirs holds exactly the same 4 files:

```bash
for d in analysis/ablation/hover_swap/pairs/*/; do ls "$d" | sort | tr '\n' ','; echo; done | sort | uniq -c
#    243 draws.jsonl,meta.json,reflect_in_SAME.txt,reflect_in_SWAP.txt,

for f in analysis/ablation/hover_swap/pairs/*/reflect_in_SAME.txt; do grep -c '^# Example ' "$f"; done | sort | uniq -c
#    243 3
```

What exists, for all 243 events:

- `reflect_in_SAME.txt` — one bundled reflective prompt containing feedback for the **3 `A_e`**
  examples. `A_e` is not a subset of the 6.
- `reflect_in_SWAP.txt` — one bundled reflective prompt containing feedback for the **3 matched
  `B_e`** examples, which *are* a subset of the 6.
- `draws.jsonl` — scores and child instructions only.
- `meta.json` — the matched-3 scores and bookkeeping.

So per event, feedback text exists for **3 of the 6** candidates (the matched `B_e`, recoverable by
parsing `reflect_in_SWAP.txt` into its 3 blocks). The other 3 of the 6 have **neither feedback text
nor a persisted parent score** (C2). No event has scores-only-for-all-6, and none has the full 6
texts.

Arithmetic for re-deriving the missing 3 per event: re-running
`adapter.evaluate(cand6, parent_cand, capture_traces=True)` for the 3 unmatched candidates is
243 × 3 = **729 metric calls**; each HoVer metric call issues 3 hops × 2 predictors = 6 LM calls ⇒
**4,374 LM calls**. This is not zero-cost.

### 5b. Byte verification, seeded sample

Seed: `random.Random(20260709)`, `rng.sample(sorted(os.listdir(pairs)), 5)`
→ `['seed7_i12', 'seed3_i7', 'seed2_i4', 'seed6_i24', 'seed5_i7']`

| file | bytes | sha256 | `# Example` blocks | HoVer template |
|---|---|---|---|---|
| `seed7_i12/reflect_in_SAME.txt` | 30575 | `25f30b4d4e19081685da5b953aca8568f5c45f8713b15120d11f744e434bd72b` | 3 | yes |
| `seed7_i12/reflect_in_SWAP.txt` | 25812 | `ec6208f438a34cf6f760c13da180e29e7a2f96223c1cd32d89e0988ab4aa451b` | 3 | yes |
| `seed3_i7/reflect_in_SAME.txt` | 11451 | `d875cd7a289d962c0f874829d2b119f36910ece9a866f8591a6b87cea3460eb3` | 3 | yes |
| `seed3_i7/reflect_in_SWAP.txt` | 11709 | `7db87cb31a44888d368c8b21fa4b500064c1fad2fad8de8653cbf63cfaaa14c8` | 3 | yes |
| `seed2_i4/reflect_in_SAME.txt` | 29753 | `bb56c464b4b45cdf70ade308ba0fe42c64265a9169bd317ee60aa97be6388123` | 3 | yes |
| `seed2_i4/reflect_in_SWAP.txt` | 21919 | `9034f37dfbbf11501087521567f35155b33372727cb23a4bde0c7d0b6f38c1a9` | 3 | yes |
| `seed6_i24/reflect_in_SAME.txt` | 24628 | `ac81b66139436c08924c15494312d2e4552c18a3f1c008fe0a719696ebfed7c7` | 3 | yes |
| `seed6_i24/reflect_in_SWAP.txt` | 25722 | `cb9166f3bb4ab19786249cbc499df4990fdfb809f35719c257c1ade66b8c2f82` | 3 | yes |
| `seed5_i7/reflect_in_SAME.txt` | 24580 | `b6ae1f7fea042119d3acce1e4344502d7f6f812d20f03313436f2dddd8a5732d` | 3 | yes |
| `seed5_i7/reflect_in_SWAP.txt` | 22571 | `68dcc65ce60cd5d2eb4445f64c4797935bec7c57ad7869b19864c214e7a9a725` | 3 | yes |

"HoVer template" = the text contains both `Correctly retrieved` and `remaining to be retrieved`.
Verbatim feedback block from `pairs/seed3_i7/reflect_in_SAME.txt`:

```
## Feedback
Correctly retrieved 2/3 gold documents: ["1982 Australian Open – Men's Singles", 'Albert Costa']. Documents remaining to be retrieved: ['Steve Denton'].
```

This matches the template constructed at `scratch/hover_probe/probe.py:54-55`:

```python
    return (f"Correctly retrieved {len(correct)}/{len(gold)} gold documents: {correct}. "
            f"Documents remaining to be retrieved: {remaining}.")
```

### 5c. Directory layout and naming convention

```
analysis/ablation/hover_swap/pairs/seed<SEED>_i<TRACE_I>/
    draws.jsonl          # 2*K = 6 reflection draws (SAME×3, SWAP×3): scores + child_instruction. NO feedback text.
    meta.json            # comp, parent_candidate_idx, A_e_pos, B_e_pos, matched-3 scores, cost, wall
    reflect_in_SAME.txt  # ONE prompt bundling feedback for the 3 A_e examples
    reflect_in_SWAP.txt  # ONE prompt bundling feedback for the 3 matched B_e examples
```

There is exactly one feedback-bearing `.txt` per arm (2 per event), each bundling 3 examples — not
one file per candidate, and never 6. 243 pair dirs total.

Representative dir `pairs/seed0_i0/`:

```
draws.jsonl          24795 bytes
meta.json              523 bytes
reflect_in_SAME.txt   7209 bytes
reflect_in_SWAP.txt   8025 bytes
```

`pairs/seed0_i0/meta.json` verbatim (note `"n_draws": 6` counts reflection draws, 2 arms × K=3 —
**not** the 6 pairing candidates):

```json
{
  "seed": 0,
  "trace_i": 0,
  "event_ordinal": 0,
  "comp": "gen_query.predict",
  "parent_candidate_idx": 0,
  "A_e_pos": [23, 8, 11],
  "B_e_pos": [5, 36, 52],
  "A_e_parent_scores_logged": [0.3333333333333333, 0.6666666666666666, 1.0],
  "B_e_parent_scores_fresh": [0.6666666666666666, 0.6666666666666666, 0.6666666666666666],
  "match_exact": false,
  "match_l1": 0.6666666666666667,
  "n_draws": 6,
  "pair_cost_usd": 0.26857,
  "pair_wall_s": 609.0
}
```

The sibling directories `pairs_pre_mmap/` and `pairs_mmap_check/` are not part of this corpus.

---

## Rejected claims

Two claims produced during this investigation were checked by recomputation and **rejected**. They
are recorded here because a freeze document should show how its facts were established.

1. **Claim:** "The float rule `sum(new) > sum(old)` disagrees with gepa's recorded accept on 2 of
   243 events (`seed0 i=28`, `i=31`)."
   **Rejected.** Recomputed across all 243 events: **0 disagreements**. At `seed0 i=28` both sums
   are `1.9999999999999998` (reject; agrees with gepa). At `seed0 i=31` the child's sum is one ULP
   larger (accept; agrees with gepa). The real anomaly is the exact-rational tie recorded in C3,
   which is a different statement.
2. **Claim:** "The accept rule lives at `strategies/acceptance.py:45-48` (`StrictImprovementAcceptance`)."
   **Rejected — wrong package.** That file does not exist in gepa 0.0.27, the version that ran. It
   exists only in the unrelated 0.1.1 checkout at `~/Desktop/gepa`. See C4.

---

## Provenance of Part II

- Task 1 numbers: recomputed from `analysis/ablation/hover_swap/pairs/*/draws.jsonl`.
- Task 3 numbers: recomputed from `scratch/hover_stage1/stage1_seed*/gepa_result.json`
  → `full_program_trace`.
- Task 5 counts and hashes: computed from on-disk bytes.
- Task 2 and Task 4 code facts: read from the installed **gepa 0.0.27** and from
  `analysis/hover_screen/` at working tree (verified byte-identical to `8be66ac` and `2fb33dd`).
- `results.md` was opened only to *compare against* the independently recomputed values, never as a
  source for them.
