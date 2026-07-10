# plan.md — state-dependent novelty selection

Design frozen at `state-dependent-design-v2.md`, tag `state-dep-design-v2-frozen`.
Written 2026-07-09/10 by CC under the overnight brief. **$0 spent producing it.**

**The calibration rule governs: only smoke-measured numbers enter this file as final.** Every
number below marked *(est.)* is a projection from the fitted rate and is superseded on contact with
a smoke. Every number marked **(measured)** was produced tonight at $0.

---

## 1. Gated spends — the exact list awaiting Neel

| # | Gate file | What it buys | Cost | Blocking |
|---|---|---|---|---|
| 1 | `APPROVED-testsplit` | grade ~299 fresh threehop claims → N=150 imperfect test split | **~$1.33** *(est.)* | the primary endpoint |
| 2 | `APPROVED-dose` | 30-event determinism control (~$0.41) + dose re-derivation (~$3.20) | **~$3.61** *(est.)* | §11-2's gate criterion |
| 3 | `APPROVED-backfill` | 8 Stage-1 final candidates × N test evals | **~$5.45** at N=150 *(est.)* | the MDE |
| 4 | `APPROVED-liverun` | live smoke (arm T seed 0) + the 24 runs | **~$50–70** *(est.)* | everything |

**Gate files are created by Neel only.** CC byte-verifies each on disk (`gates.py:require`) and
exits 2 without it. Verified tonight: all four live scripts refuse to run, exit code 2.

**Two smokes are themselves live spend and wait for morning:** the dose smoke (5 events) and the
backfill smoke (1 candidate). Neither has been run.

### Dependency order

```
APPROVED-testsplit → build_test_split.py → test_split.json (+sha256)
                                              ↓
                                       APPROVED-backfill → backfill_stage1.py
                                              ↓
                                    stage1_backfill_endpoints.json
                                              ↓
APPROVED-dose → dose_control.py --run (30/30 byte-exact, else STOP)
                     ↓
                dose_compute.py --live → D
                     ↓
                mde_sim.py --endpoints ... --dose D  →  MDE + §11-2 gate verdict
                                              ↓
                                       APPROVED-liverun → smoke → 24 runs
```

---

## 2. MDE

**PLACEHOLDER — the MDE cannot be computed tonight.** It requires the backfilled Stage-1 test
scores, which require the test split, which requires `APPROVED-testsplit`. The simulator is written,
committed, and self-tested; it will produce the number within minutes of the backfill landing.

Machinery validated at $0 (`mde_sim.py --selftest`):
- exact sign-flip p on all-positive diffs = **0.00781** = 2/256, as required at n=8;
- power at zero shift = **0.044** ≈ α;
- power monotone in shift.

On a **synthetic** endpoint distribution (sd 0.045, *not* the real backfill): MDE ≈ 0.071 endpoint
points ≈ 1.59 × endpoint sd, and at a hypothetical D = 0.5 the **§11-2 gate bites**. Do not cite
that number; it is a machinery check. But note it is consistent with review R2's ceiling argument,
which predicted the gate is "more likely than not to bite."

**Simulation script hash, cited per R11:**
`mde_sim.py` sha256 `300f7cd96d4fc7c615f8e8e74a7ea82bbb236a7b069de9ed972f0fc495cff626`

---

## 3. Dose

**PLACEHOLDER — gated.** `D` is unknown until `APPROVED-dose`.

Pre-registered definition (v2 §11-0), validated at $0 (`dose_compute.py --selftest`, and a negative
control confirming the self-test *fails* when `gap()` is sabotaged):

```
gap_e = x_(4)  −  (1/20) Σ_{|S|=3} min(x_S)        [x = 6 novelties, ascending]
D_s   = mean_{e∈s} gap_e / sd_s                     [each seed in its own within-run SD]
D     = mean_s D_s
```

`sd_s` per seed (ddof=0, recomputed from `features.csv`):
`[0.021870, 0.024433, 0.029460, 0.023196, 0.028713, 0.025238, 0.025011, 0.026538]`

**Free degeneracy pre-estimate (measured, $0)** — `dose_compute.py --pre-estimate`. Using the
screen's own 3 reflected members per event, the mean within-event novelty spread (max−min) is
**3.06 within-run SD**. This is *not* the dose (that needs 6 candidates), but it rules out §15-12's
degenerate case: there is real selection room, and with 6 draws the spread can only grow.

**Determinism control: the expected side is already frozen (measured, $0).**
`dose_control.py --freeze-expected` drew the 30 events with `random.Random(20260709)` and committed
the sha256 of all **90** persisted `B_e` feedback blocks to `dose_control_expected.json`
(sha256 `75d9fe3ae498a92153b34ec2187856eecbc4f7c5623953bb4bf413e95676edd0`). Freezing the expected
side *before any re-execution exists* is what makes the control unfudgeable. 30/30 byte-exact →
proceed; any mismatch → STOP, and the pre-registered fallback is to **drop the dose**, never the
biased 3-candidate shrink.

Cost arithmetic: control 30×3 = 90 calls; re-derivation 3 × |event set|. At `m = $0.004543`:
243 events → 819 calls ≈ $3.72; 235 events (ordinal-0 excluded, as §11-0 specifies) → 795 calls ≈
$3.61. **v2 §20 open decision 2 must settle which.**

---

## 4. Per-run cost and time

**PLACEHOLDER — no live smoke has been run.** The live smoke (arm T, seed 0) is inside
`APPROVED-liverun` and is the first thing to run under it.

Fitted rate, from two independent observed spends:

```
Stage-1 seed0:  302 metric calls + 32 reflection calls = $1.9078
Swap, per pair:  45 metric calls +  6 reflection calls = $0.3049
  ⇒ m ≈ $0.004543 / metric call ,  r ≈ $0.016744 / reflection call
```

Cross-check from a third, independent source: `grade_threehop.py` graded 245 claims (1 metric call
each) for $1.0942 ⇒ $0.00447/claim — within 2% of `m`.

| line | quantity | est. |
|---|---|---|
| per-run optimization, arm B | ≈ Stage-1 | ~$2.14 |
| per-run optimization, arms T/C | +~50% minibatch-side calls | ~$2.4–2.9 |
| per-run test evals (**2**: primary + midpoint, M4) | 2 × N × m | ~$1.36 at N=150 |
| 24 runs total | | **$50–70** |

Wave plan: width 8 is the proven floor (the swap ran width 8 at ~0.93 GB/process after the mmap
fix). Mixed-arm waves, never "all of arm T first". Width is re-decided on the smoke's RSS
measurement. **Concurrency ceiling is 8 on this 16 GB machine — never resurrect the 16 rung.**

---

## 5. What was measured tonight, at $0

| check | result |
|---|---|
| cross-venv embedding equivalence (`.venv-armT` vs `.venv-screen`) | **bitwise identical**, max\|Δ\| = 0.0 |
| novelty byte-verify vs frozen `features.csv` | **235/235 events, max abs diff 0.000e+00** (tol 1e-12) |
| three-arm counter audit vs the §6a five-site model | **PASS**, all 5 rows |
| `total_num_evals == examples handed to the adapter` | **True**, every arm |
| epoch-boundary prediction (b=3 → i=34; b=6 → i=17) | **confirmed** |
| unchosen-3 leakage (accept / Pareto / trace) | **none**; trace batch size 3 everywhere |
| `gap()` order-statistic self-test (+ sabotage negative control) | **PASS / correctly FAILS** |
| sign-flip exactness at n=8 | **2/256 = 0.00781** |
| all four live scripts refuse without their gate | **exit 2** |

### Realized events/run under the mocked LM (§6 verification item 3)

| arm | events | skipped | accepts | counter |
|---|---|---|---|---|
| B | 35 | 1 | 8 | 303 |
| C | 24 | 0 | 8 | 306 |
| T | 22 | 0 | 10 | 308 |

T/C complete ~0.63–0.69× the events of B at equal budget — the overhead the design intends and
that H3 interprets. *(Mocked scores; the real ratio comes from the live smoke.)*

---

## 6. Script inventory and hashes

| file | sha256 | runs tonight? |
|---|---|---|
| `novelty.py` | `158f6acde0b99d16ea400fc5fc4015e043ae2f2f5db6ca4c3145a8b8d67c9e32` | imported |
| `verify_novelty.py` | `e6f34e9cd2689387525f57084397410e4858596384f47472cb4d9b0b2ffd736c` | ✅ $0 gate, PASS |
| `embed_sample.py` | `358088c6c7bd0fc08bea68e41ca595a483dfe47d485db6b91700ed33bed51e6e` | ✅ $0 gate, PASS |
| `sampler.py` | `30387c3f443dd5d4037954752b33e551587851a597270403be9e0360b94ec737` | imported |
| `proposer.py` | `402cbff854da37f5c967fc5f8f8106ccd80a6d2477243c126be96bd2e42bd692` | imported |
| `count_audit.py` | `b827c2cd019ab7df5b17d19a0f02f587c72ea50e1ec228ccb48da4ea5728ee2c` | ✅ $0, AUDIT PASS |
| `gates.py` | `33cabf7b0fa9948fe219b6506c82e8fb053ab1b3bd9466e881350bcb57c5cab6` | imported |
| `dose_control.py` | `7fba73aebb0d92ed61592bdd8f7d840efbb8de1daee426cd2be22b3ca4988056` | ✅ expected side frozen |
| `dose_compute.py` | `6dfaf24461650ad820d8594f5be37b65401bc9f3b9bc8fab26e89c3f42549438` | ✅ selftest + pre-estimate |
| `mde_sim.py` | `300f7cd96d4fc7c615f8e8e74a7ea82bbb236a7b069de9ed972f0fc495cff626` | ✅ selftest |
| `build_test_split.py` | `414b61e6a7d94b022a98ab0bda4a1bc9aa46f4107611cc7a38c2af6297570128` | ❌ gated |
| `backfill_stage1.py` | `bd795afb5ac3dd59c72a80637074dde5b308c171abb84d075d8d5fa719fe8ab1` | `--resolve` only ($0) |
| `dose_control_expected.json` | `75d9fe3ae498a92153b34ec2187856eecbc4f7c5623953bb4bf413e95676edd0` | frozen artifact |

Environment: `analysis/state_dep/.venv-armT` — Python 3.12.13, `numpy 2.5.0`, `gepa 0.0.27`,
`dspy 3.2.1`, `sentence_transformers 5.6.0`, `torch 2.13.0`, `transformers 5.13.0`,
`tokenizers 0.22.2`, `huggingface_hub 1.23.0`, `safetensors 0.8.0`. All pins exact; `pip check`
clean. Embedding snapshot `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, weights sha256
`53aa51172d142c89d9012cce15ae4d6cc0ca6895895114379cacb4fab128d9db`, loaded
`local_files_only=True`.

---

## 7. Blocking items that are NOT spend

These must be resolved before `APPROVED-liverun`, and none of them costs anything:

1. **v2 §20-1 — `skip_perfect_score` scope.** Measured tonight: the gate fires on ~0.65% of events
   with 3 scores and ~0.004% with 6 (from Stage-1's empirical P(score=1) = 0.1866). Real, small.
2. **v2 §20-2 — dose event set**, 235 vs 243. Cost difference ~$0.11.
3. **NEW — the endpoint is tie-break-determined on half the seeds, and returns the seed prompt on a
   quarter of them.** See `notes/MORNING-REPORT.md` flag B10. This one may warrant a v2 amendment
   and re-freeze before any spend, because it bears directly on §11's power.
