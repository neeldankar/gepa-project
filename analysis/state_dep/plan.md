# plan.md — state-dependent novelty selection

Design frozen at `state-dependent-design-v2.md`, tag **`state-dep-design-v2.1-frozen`** (amended
2026-07-22; the four amendments are logged at the top of the design doc). This file rewritten
2026-07-22 for v2.1. **$0 spent producing it — no `APPROVED-*` file exists on disk.**

**The calibration rule governs: only smoke-measured numbers enter this file as final.** Every number
marked *(est.)* is a projection from the fitted rate and is superseded on contact with a smoke.
Every number marked **(measured)** was produced at $0.

---

## 0. What changed in v2.1, and what it costs

§8b makes the endpoint a **selection-split argmax** instead of a val-argmax, because on the 8
Stage-1 runs the val lattice decided the endpoint by tie-break on 4/8 seeds and returned the seed
prompt on 2/8 (B10). Scoring every candidate on a 50-claim split is new spend that no earlier cost
model carried:

| | pre-amendment | v2.1 |
|---|---|---|
| `APPROVED-testsplit` | ~$1.33 (299 claims, one split) | **~$3.13** (700-claim frame, two splits) |
| `APPROVED-backfill` | ~$5.45 (8 candidates × test) | **~$27.49** (97 candidates × 50, then 8 × 150) |
| `APPROVED-dose` | ~$3.61 | ~$3.61 (unchanged; 235 ratified) |
| `APPROVED-liverun` | ~$50–70 | **~$130–180** |
| **program** | **~$60–80** | **~$165–215** |

The backfill's 97 is a **realized count, not an estimate** (`backfill_stage1.py --resolve`,
measured): the 8 Stage-1 runs hold 11, 11, 13, 11, 14, 10, 13, 14 candidates.

---

## 1. Gated spends — the exact list awaiting Neel

| # | Gate file | What it buys | Cost | Blocks |
|---|---|---|---|---|
| 1 | `APPROVED-testsplit` | grade a fixed 700-claim frame → test (150) + selection (50) | **~$3.13** *(est.)* | everything downstream |
| 2 | `APPROVED-liverun` | live smoke, then 24 runs, then the §8b post-run pass | **~$130–180** *(est.)* | the experiment |
| 3 | `APPROVED-backfill` | 97 candidates × 50 selection, then 8 winners × 150 test | **~$27.49** *(est.)* | the MDE only |
| 4 | `APPROVED-dose` | 30-event determinism control + 235-event re-derivation | **~$3.61** *(est.)* | the §11-2 gate only |

**Gate files are created by Neel only.** Every live script byte-verifies its gate (`gates.py:require`)
and exits 2 without it. **Verified 2026-07-22 (measured): all six live scripts exit 2** —
`build_test_split.py`, `backfill_stage1.py --run`, `dose_control.py --run`, `dose_compute.py --live`,
`score_candidates.py`, `supervisor.py --waves`.

### Dependency order — redrawn for v2.1

The MDE branch **no longer blocks the launch**. §11-2's amended gate timing requires the MDE and its
framing label before `results.md` is read, not before `APPROVED-liverun`:

```
APPROVED-testsplit → build_test_split.py → test_split.json + selection_split.json (+sha256)
                                              ↓
                          APPROVED-liverun → supervisor.py --smoke   (arm T seed 0, alone)
                                              ↓  measurements land in plan.md §4
                                             supervisor.py --waves   (24 runs, width 8)
                                              ↓
                                             score_candidates.py --all   (§8b post-run pass)
                                              ↓
                                             tag pre-analysis snapshot
                                              ↓
  ┌───────────────────────────────────────────┤
  │  APPROVED-backfill → backfill_stage1.py --run → stage1_backfill_endpoints.json
  │  APPROVED-dose     → dose_control.py --run (30/30 byte-exact, else STOP)
  │                    → dose_compute.py --live → D
  │                              ↓
  │                    mde_sim.py --endpoints … --dose D  →  MDE + §11-2 framing label
  └───────────────────────────────────────────┤
                                              ↓
                                        results.md   ← the label must be on disk BEFORE this
                                              ↓
                                        read against §9 → interpretation → second path
```

The two backfill/dose branches may clear before, during, or after the waves. They may **not** clear
after `results.md` is read; if they have not, the run is estimation-only by default.

---

## 2. MDE

**PLACEHOLDER — not yet computed, and by design it does not gate the launch.** It needs the
backfilled Stage-1 endpoints under the §8b estimator, which need `APPROVED-testsplit` then
`APPROVED-backfill`.

**The rule that protects it (v2.1 §11-2):** the MDE and the framing label it implies — confirmatory
vs estimation-only — are computed and written **here**, with the simulator's sha256, **before
`results.md` is read**. Launch proceeds at 8 paired seeds regardless of the number.

Machinery validated at $0 (`mde_sim.py --selftest`, re-run 2026-07-22, **measured**):
- exact sign-flip p on all-positive diffs = **0.00781** = 2/256, as required at n=8;
- power at zero shift = **0.044** ≈ α; power monotone in shift.

On a **synthetic** endpoint distribution (sd 0.045, *not* the real backfill): MDE ≈ 0.071 endpoint
points ≈ 1.59 × endpoint sd, and at a hypothetical D = 0.5 the **§11-2 gate bites**. Do not cite that
number; it is a machinery check. It is consistent with review R2's ceiling argument, which predicted
the gate is "more likely than not to bite."

Simulation script hash, cited per R11:
`mde_sim.py` sha256 `300f7cd96d4fc7c615f8e8e74a7ea82bbb236a7b069de9ed972f0fc495cff626`

**MDE value:** _(unfilled)_ — **Framing label:** _(unassigned)_ — **Assigned at:** _(no date)_

---

## 3. Dose

**PLACEHOLDER — gated.** `D` is unknown until `APPROVED-dose`.

Pre-registered definition (v2.1 §11-0), validated at $0 (`dose_compute.py --selftest`, plus a
negative control confirming the self-test *fails* when `gap()` is sabotaged):

```
gap_e = x_(4)  −  (1/20) Σ_{|S|=3} min(x_S)        [x = 6 novelties, ascending]
D_s   = mean_{e∈s} gap_e / sd_s                     [each seed in its own within-run SD]
D     = mean_s D_s
```

`sd_s` per seed (ddof=0, recomputed from `features.csv`):
`[0.021870, 0.024433, 0.029460, 0.023196, 0.028713, 0.025238, 0.025011, 0.026538]`

**Event set: 235** (v2.1 §20-2, ratified 2026-07-22 — ordinal-0 excluded; the frame β was estimated
on). Control 30×3 = 90 calls; re-derivation 3×235 = 705 calls; 795 × $0.004543 ≈ **$3.61**.

**Free degeneracy pre-estimate (measured, $0)** — using the screen's own 3 reflected members per
event, the mean within-event novelty spread (max−min) is **3.06 within-run SD**. Not the dose (that
needs 6 candidates), but it rules out §15-12's degenerate case: there is real selection room.

**Determinism control: the expected side is frozen (measured, $0).** `dose_control.py
--freeze-expected` drew 30 events with `random.Random(20260709)` and committed the sha256 of all 90
persisted `B_e` blocks to `dose_control_expected.json` (sha256 `75d9fe3a…6edd0`). Freezing the
expected side *before any re-execution exists* is what makes the control unfudgeable. **The control
samples all 243 pair dirs, not the dose's 235** — different questions, and re-drawing it now to
"match" would be exactly the tampering it precludes. 30/30 byte-exact → proceed; any mismatch →
STOP, and the pre-registered fallback is to **drop the dose**, never the biased 3-candidate shrink.

---

## 4. Per-run cost and time

**PLACEHOLDER — no live smoke has been run.** The smoke (arm T, seed 0) is inside `APPROVED-liverun`
and is the first thing to run under it: `supervisor.py --smoke` runs it alone, writes
`markers/SMOKE.DONE`, and `--waves` refuses to start without that marker.

Fitted rate, from two independent observed spends:

```
Stage-1 seed0:  302 metric calls + 32 reflection calls = $1.9078
Swap, per pair:  45 metric calls +  6 reflection calls = $0.3049
  ⇒ m ≈ $0.004543 / metric call ,  r ≈ $0.016744 / reflection call
```

Cross-checked against a third independent source: `grade_threehop.py` graded 245 claims for $1.0942
⇒ $0.00447/claim, within 2% of `m`.

| line | quantity | est. |
|---|---|---|
| per-run optimization, arm B | ≈ Stage-1 | ~$2.14 |
| per-run optimization, arms T/C | +~50% minibatch-side calls | ~$2.4–2.9 |
| per-run **selection evals (§8b, new)** | ~10–14 cand × 50 × m | ~$2.3–3.2 |
| per-run test evals | 1 × 150 × m (primary), 2× if §9 demands the midpoint | $0.68–1.36 |
| 24 runs, all in | | **~$130–180** |

**Smoke × 24 projection: _(unfilled — the smoke writes it here)_.**

Wave plan: **width 8**, the proven floor (the swap ran width 8 at ~0.93 GB/process after the mmap
fix). Mixed-arm waves (`wave_manifest.json`, measured deterministic):

```
wave 1: B0  B6  C4  T2  B3  C1  C7  T5     (B3 C3 T2)
wave 2: B2  C0  C6  T4  B5  C3  T1  T7     (B2 C3 T3)
wave 3: B4  C2  T0  T6  B1  B7  C5  T3     (B3 C2 T3)
```

Each arm covers seeds 0–7 exactly once; each seed's three arms land in three different waves, so a
wave-level disturbance cannot hit one seed's three arms together. **Width is re-decided on the
smoke's RSS + backoff measurement, by editing `WIDTH`. There is no auto-ramp, and 16 is never
resurrected untested.** Launch under `caffeinate -dims`.

---

## 5. What was measured at $0

### 2026-07-09/10 (unchanged, re-verified where noted)

| check | result |
|---|---|
| cross-venv embedding equivalence (armT vs `.venv-screen`) | **bitwise identical**, max\|Δ\| = 0.0 |
| novelty byte-verify vs frozen `features.csv` | **235/235 events, max abs diff 0.000e+00** (tol 1e-12) |
| three-arm counter audit vs the §6a five-site model | **PASS**, all 5 rows |
| `total_num_evals == examples handed to the adapter` | **True**, every arm |
| epoch-boundary prediction (b=3 → i=34; b=6 → i=17) | **confirmed** |
| unchosen-3 leakage (accept / Pareto / trace) | **none**; trace batch size 3 everywhere |
| `gap()` order-statistic self-test (+ sabotage negative control) | **PASS / correctly FAILS** |
| sign-flip exactness at n=8 | **2/256 = 0.00781** |

### 2026-07-22 (new)

| check | result |
|---|---|
| all six live scripts refuse without their gate | **exit 2**, every one |
| split draw: determinism, disjointness, order-dependence (`--selftest`) | **8/8 PASS** on a synthetic 351-claim pool |
| Stage-1 candidate pool for the backfill (`--resolve`) | **97 candidates**; val tie-break 4/8, seed prompt 2/8 |
| three-arm counter audit, rebuilt venv, `chosen3` | **AUDIT PASS**; `count_audit_result.json` **byte-identical** to the pre-rebuild baseline |
| cross-venv embedding equivalence, **rebuilt venv** | **bitwise identical**, max\|Δ\| = 0.0 |
| novelty byte-verify, **rebuilt venv** | **235/235, max abs diff 0.000e+00** |
| `run_state_dep.py --dry`, all three arms | wiring dump matches `count_audit.build_engine` field for field |
| trainset/valset identity vs Stage 1 | **train and val threehop ids identical** |
| arm C now scores and logs all 6 novelties (§12) | **confirmed**; selection and counters unchanged |
| MDE simulator self-test | **PASS** (2/256 exact, power ≈ α at 0) |

### Realized events/run under the mocked LM (§6 verification item 3)

| arm | events | skipped | accepts | counter |
|---|---|---|---|---|
| B | 35 | 1 | 8 | 303 |
| C | 24 | 0 | 8 | 306 |
| T | 22 | 1 | 10 | 314 |

T/C complete ~0.63–0.69× the events of B at equal budget — the overhead the design intends and that
H3 interprets. *(Mocked scores; the real ratio comes from the live smoke.)*

---

## 6. Environment — rebuilt from a lockfile, 2026-07-22

**The pre-lockfile `.venv-armT` could not run the experiment.** It carried `gepa`, `dspy` and
`sentence_transformers` but **not `bm25s` or `PyStemmer`**, which `probe.py` imports at module load —
so retrieval was impossible and the runner died on import. It had also drifted from the Stage-1
environment on the LM client: `litellm` 1.91.1 vs 1.90.1, `openai` 2.45.0 vs 2.44.0. litellm is where
cost accounting and retry/backoff live, and arm B is supposed to reproduce Stage-1 cost.

Rebuilt per Neel's ruling, from explicit pins (`armT-requirements.in`) resolved and frozen to
**`armT-lock.txt`** (83 distributions), Python 3.12.13:

- **optimization / LM / retrieval path → the probe donor**, the environment Stage 1 ran in:
  `gepa==0.0.27`, `dspy==3.2.1`, `litellm==1.90.1`, `openai==2.44.0`, `numpy==2.5.0`,
  `bm25s==0.3.9`, `PyStemmer==3.1.0`, `orjson==3.11.9`.
- **embedding stack → the screen donor**, at the versions the acceptance gates passed under:
  `sentence-transformers==5.6.0`, `torch==2.13.0`, `transformers==5.13.0`, `tokenizers==0.22.2`,
  `huggingface_hub==1.23.0`, `safetensors==0.8.0`.
- **collision, `tokenizers`:** probe 0.23.1 vs embedding stack 0.22.2 → the embedding stack wins.
  `transformers 5.13.0` constrains it, the 235-row byte-verification ran under it, and litellm's own
  requirement (`>=0.21.0,<1.0`) is satisfied. It is not on the optimization path.

**Both $0 acceptance gates were re-run against the rebuilt venv and both PASS** — bitwise-identical
embeddings and 235/235 byte-exact novelty. The counter audit's output is byte-identical to the
pre-rebuild baseline. The old venv is retained at `.venv-armT-pre-lockfile` (gitignored) for
rollback; nothing references it.

Embedding snapshot `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, weights sha256
`53aa5117…8d9db`, 90,868,376 bytes, loaded `revision=` pinned and `local_files_only=True` — verified
on disk at every run start and recorded in each run's `config.json`.

---

## 7. Script inventory and hashes

| file | sha256 | state |
|---|---|---|
| `novelty.py` | `158f6acde0b99d16ea400fc5fc4015e043ae2f2f5db6ca4c3145a8b8d67c9e32` | imported |
| `verify_novelty.py` | `e6f34e9cd2689387525f57084397410e4858596384f47472cb4d9b0b2ffd736c` | ✅ $0 gate, PASS |
| `embed_sample.py` | `358088c6c7bd0fc08bea68e41ca595a483dfe47d485db6b91700ed33bed51e6e` | ✅ $0 gate, PASS |
| `sampler.py` | `30387c3f443dd5d4037954752b33e551587851a597270403be9e0360b94ec737` | imported |
| `proposer.py` | `65fb415e7edb83645e731d6dca6a9ada5ec6fe5d9536529845ac1e5a41d3cd80` | imported (§12 logging extended) |
| `count_audit.py` | `b827c2cd019ab7df5b17d19a0f02f587c72ea50e1ec228ccb48da4ea5728ee2c` | ✅ $0, AUDIT PASS |
| `gates.py` | `01527de9c5709b0760cd411f7039076a1130a2286d25429555e068a04f525628` | imported |
| `dose_control.py` | `b91e02812428073a77b3eb3521829f1faaf4edfc6d9aef313e80fe38a4f9e89e` | ✅ expected side frozen |
| `dose_compute.py` | `dded73a54943963c9803eca3ecf9740f6a5757c9a41d8fe6ae7a1be7faa51651` | ✅ selftest + pre-estimate |
| `mde_sim.py` | `300f7cd96d4fc7c615f8e8e74a7ea82bbb236a7b069de9ed972f0fc495cff626` | ✅ selftest |
| `eval_split.py` | `39edf54c8d19349c10aa981c100b87d4eeae796285c4445258f246f97c5b92fc` | shared evaluator, gated by callers |
| `build_test_split.py` | `453a70e99f0ece0c969fabfb566b7594a88648fa78b1bfb2a3662f8820a0686d` | ❌ gated; `--selftest` PASS |
| `backfill_stage1.py` | `cf0efa17a9ef0d0c9e75da25fdbc7fc7716b2bd2efd1c771c4b39b6a1bc1045e` | ❌ gated; `--resolve` PASS ($0) |
| `run_state_dep.py` | `b50aa495a085015ed67d5db33b354d3e8499140cffe87a82280e3ba084253bde` | ❌ gated; `--dry` PASS, 3 arms, writes nothing |
| `score_candidates.py` | `49b98f8c314fcc8b991cf33e78cae9c653212453ae565a85f235f04e2aaeb570` | ❌ gated |
| `supervisor.py` | `62f768dda387967ce3e3d02598d2b36f4174d0efc1fb6bd79cf2711d601cb2d7` | ❌ gated; `--plan` PASS ($0) |
| `make_wave_manifest.py` | `ba4679205bac7193e3256c2faea0069a5e325c35d9cb628da28df93157231711` | ✅ $0, manifest written |

---

## 8. Blocking items that are NOT spend

1. ~~v2 §20-1 `skip_perfect_score` scope~~ — **ratified `chosen3`** (v2.1 §20-1).
2. ~~v2 §20-2 dose event set~~ — **ratified 235** (v2.1 §20-2).
3. ~~B10, the tie-break endpoint~~ — **amended: §8b selection split** (v2.1).
4. ~~§20-3 uniform vs stratified~~ — **resolved by default: uniform, both splits**.
5. ~~`.venv-armT` cannot run the task program~~ — **rebuilt from `armT-lock.txt`; both $0 gates
   re-passed**.

**Nothing non-spend now blocks `APPROVED-liverun`.** What remains is Neel reading this file and
deciding which gates to open. Two things are worth deciding explicitly before opening gate 2:

- **The midpoint endpoint is conditional** (§9 ambiguity rules). Running `score_candidates.py`
  without `--midpoint` saves ~$16 across 24 runs and forfeits the instrument §9 sometimes calls for.
- **`APPROVED-backfill` at $27.49 buys only the MDE**, which is a heuristic screen and is expected to
  bite. It is off the launch path now, so it can be deferred and decided after the waves — but it
  must clear before `results.md` is read, or the run is estimation-only by default.
