# plan.md — state-dependent novelty selection

Design frozen at `state-dependent-design-v2.md`, tag **`state-dep-design-v2.2-frozen`** (amended
2026-07-22, 2026-07-23 and 2026-08-03; all three are logged at the top of the design doc). This
file rewritten 2026-07-23, **§4 from smoke measurements 2026-07-29, §3 for the v2.2 dose
amendment 2026-08-03.**

**Spent to date: $8.4278** — `APPROVED-testsplit` ($3.2336) and `APPROVED-smoke` ($5.1942), both
under projection. `APPROVED-liverun`, `APPROVED-backfill` and `APPROVED-dose` have **not** been
opened. §4 is no longer a projection: it is the smoke's measurement, and §4.5 is what the 24-run
launch decision rests on.

**Decisions taken 2026-07-23 (Neel):**
1. **The midpoint endpoint's test evaluation is not pre-paid** across the 24 runs (−$16.35). It stays
   the §8/§9 conditional it always was; the midpoint *candidate* is still identified for free on
   every run, so the option costs $0.68 on whichever runs §9 later demands.
2. **`APPROVED-backfill` is deferred off the launch path.** It must clear before `results.md` is
   read, not before launch — which is what §11-2's amended timing already permits.
3. **`APPROVED-smoke` is a new gate** (v2.1.1 §13-7), split out of `APPROVED-liverun`. The smoke is
   the measurement the launch is decided *on*, so approving it is no longer the same act as
   approving the launch.

**The calibration rule governs: only smoke-measured numbers enter this file as final.** Every number
marked *(est.)* is a projection from the fitted rate and is superseded on contact with a smoke.
Every number marked **(measured)** was observed, not fitted — at $0 before 2026-07-28, and from the
`APPROVED-testsplit` / `APPROVED-smoke` spends after it. Numbers marked *(derived)* are arithmetic
on measured quantities (e.g. arm B's per-run cost, which no smoke observed directly) and are
labelled as such wherever they appear.

---

## 0. What the amendments changed, and what they cost

§8b makes the endpoint a **selection-split argmax** instead of a val-argmax, because on the 8
Stage-1 runs the val lattice decided the endpoint by tie-break on 4/8 seeds and returned the seed
prompt on 2/8 (B10). Scoring every candidate on a 50-claim split is new spend that no earlier cost
model carried:

| | pre-amendment | v2.1.1 projected | realized |
|---|---|---|---|
| `APPROVED-testsplit` | ~$1.33 (299 claims, one split) | ~$3.13 (700-claim frame, two splits) | **$3.2336 SPENT** |
| `APPROVED-dose` | ~$3.61 | **~$8.6** (v2.2: all 6 re-derived, repriced) | — |
| `APPROVED-smoke` | *(inside liverun)* | ~$6–8 (one arm-T run + its own §8b pass) | **$5.1942 SPENT** |
| `APPROVED-backfill` | ~$5.45 (8 candidates × test) | **~$27.49** (97 candidates × 50, then 8 × 150) | — |
| `APPROVED-liverun` | ~$50–70 | **~$120–150** (24 runs + their §8b pass) | *point est. **$135.83*** |
| **program** | **~$60–80** | **~$160–195** | ***~$180.4*** |

### 0.1 Caps raised on the measured §8b rate — 2026-08-10

`LIVERUN_CAP` **$150.00 → $160.00** (`supervisor.py:83`) and the per-run-dir `SPEND_CAP`
**$6.00 → $8.00** (`score_candidates.py:48`). Both on measurement, not on argument.

The 8 §8b run dirs scored on 2026-08-06 give the first *live* per-call rate: **$0.005897/call**
(`liverun_ledger.json` score entries ÷ 5,050 metric calls). That is 30% above the `$0.004543` fit
the original caps were sized on, and it sits just **under** the `$0.006121` the smoke measured
(§4.3, table at §3.2) — so the live pass corroborates the smoke rather than superseding it. The
conservative bound for planning is $0.006121.

The 16 unscored run dirs are **167 candidates = 10,750 metric calls**:

| rate | remaining 16 | program total |
|---|---|---|
| $0.004543 *(fit, stale)* | $48.84 | $121.48 |
| **$0.005897** *(live §8b, measured)* | **$63.39** | **$136.03** |
| $0.006121 *(smoke, conservative)* | $65.80 | $138.44 |

Against the old $150 cap the conservative bound left **$11.56** — less than one arm-B run dir, so a
single overrun would halt the pass mid-flight with dirs half-scored. $160 leaves **$21.56**, more
than the largest single dir. For the per-dir cap: the 14-candidate arm-B dirs (B_seed4, B_seed7;
850 calls) project to **$5.01–$5.20**, only 13–20% under $6.00, and tripping that cap raises
`RuntimeError` and **discards that dir's completed work**; $8.00 gives 35–38%.

`M = 0.004543` in `score_candidates.py:47` is deliberately **not** re-fitted: it feeds the
pre-spend projection the script prints before asking for the gate, where under-estimating is the
loud failure and over-estimating is the silent one. `EST_SCORE_PER_RUN = 4.63`
(`supervisor.py:361`) likewise stays — it still over-estimates the $3.96 remaining-16 mean, which
is the safe direction for a pre-spawn cap check.

⚠️ The on-disk `APPROVED-liverun` still reads *"Program cap $150.00"*. `gates.py:require()` verifies
existence, not content, so nothing breaks mechanically — but the signed authorization now understates
the cap the code enforces. **CC must not write gate files**; restating it is Neel's.

Context: these raises accompany the fix for the §8b memory blowup that SIGKILLed 8 runs and panicked
the machine on 2026-08-06 — see `notes/PHASE2-DIAGNOSIS.md` and §7 for the `eval_split.py` change.

### 0.2 `SCORE_WIDTH` 2 → 4, on the first real scorer memory measurement — 2026-08-10

`supervisor.py:74` **2 → 4**. The comment there had justified width 2 with *"~1.5 GB each"*, a
number inherited from the **optimization** runs' `peak_rss_mb` — measured at
`run_state_dep.NUM_THREADS = 1`, and compressor-suppressed at that. Scorer RSS had **never** been
measured separately (§10 step 3 said so explicitly). It has been now, `vmmap` on a bootstrapped
scorer after the §8-8 fix:

```
physical footprint   791 M steady, 1.1 G peak
TOTAL                6.3 G virtual ->  1.2 G resident,  570.8 M DIRTY
mapped file          2.6 G virtual -> 13.9 M resident,      0 K dirty   <- the BM25 index
```

**Only the 570.8 MB dirty anonymous multiplies with width.** The index is mmapped *and* is the same
file in every process, so its pages are shared page cache, not per-process copies — the thing that
made §8-8 catastrophic (a private 5–6 GB copy per process, ×8 threads) is now the thing that makes
width cheap.

| width | dirty (multiplies) | API streams | ETA, 16 dirs |
|---|---|---|---|
| 2 *(was)* | 1.1 GB | 16 | 7.3 h |
| 3 | 1.7 GB | 24 | 4.9 h |
| **4** *(now)* | **2.3 GB** | **32** | **3.7 h** |
| 6 | 3.4 GB | 48 | 2.5 h |

**Memory would permit 6. It is not what binds.** What binds is rate-limit behaviour above 16
concurrent streams — which has never been observed, and which the harness **cannot see**:
`rate_hit` (`supervisor.py:397`) greps child stdout for `429`/`rate limit`, but litellm retries
internally and silently, so throttling surfaces as longer `elapsed_s` and higher spend, never as a
flag. `eval_split` has no backoff counter either (`score_candidates.py:170-172`). The only
sustained datum is 16 streams (width 2 × `WORKERS=8`) running ~8 h clean with a per-candidate
spread of 171–331 s and no fat tail. **4 is a 2× extrapolation; 6 would be 3×.**

Width 4 is therefore safe *because a human is watching*, not because the constant is proven — see
the canary in §10 step 3. Neel took that trade knowingly on 2026-08-10.

⚠️ `MEM_MIN_GB = 1.5` (`supervisor.py:63`) may hold the 3rd/4th spawn on a busy desktop:
`avail_gb()` (free + inactive + speculative) read **3.66 GB** with Chrome and Cursor up. It fails
**closed** — logs `MEM HOLD`, runs at effective width 2–3 — so the risk is a silently unrealised
speedup, not an overrun. Free memory before launching. `MEM_MIN_GB` is deliberately **not** changed.

⚠️ Second gate/code divergence: the signed `APPROVED-liverun` reads *"§8b at 2 concurrent
scorers"*, alongside its *"Program cap $150.00"* (§0.1). Neither breaks anything —
`gates.py:require()` verifies existence, not content — but the signed authorization now understates
the code in two places. Restating it is Neel's; the §10 heredoc reproducing it is left verbatim.

### 0.3 §8b COMPLETE, the realized rate, and the backfill cap — 2026-08-11

**The §8b pass finished.** `supervisor.log`: `SCORE COMPLETE done=10 failed=0`. All **24/24**
non-smoke run dirs now hold `endpoints.json`. Ledger: 24 optimization ($46.6905) + 24 score
($86.0698) = **$132.7603 of the $160 cap**. Zero failures at `SCORE_WIDTH = 4`.

**The §8-8 fix is confirmed by the timings, not just by the $0 bench.** Candidate 0 stopped being
special — which is exactly what "the growth was the index-load race, not per-candidate
accumulation" predicts:

| | pre-fix (width 2) | post-fix (width 4) |
|---|---|---|
| candidate 0 | 1917 s (1778–3858) | **176 s** (134–221) |
| candidates 1..n | 234 s (171–331) | **195 s** (147–562) |

Steady state got *faster* at 4× the process count and 32 concurrent API streams, with no fat tail —
**no evidence of throttling at the width raised in §0.2.** The one 562 s outlier is isolated.

**Realized §8b rate: `$0.005681/call`** (231 candidates → 15,150 metric calls for $86.0698). This
supersedes both the $0.004543 fit and the $0.005897 live-8-dir estimate in §0.1, and lands just
under the $0.006121 smoke rate. §0.1's projection was 5% high — the conservative direction.

Two §0.1 decisions were load-bearing, not precautionary:
- **B_seed7 cost $6.1342.** Under the old `SPEND_CAP = 6.00` it would have raised `RuntimeError`
  and discarded a completed 14-candidate dir.
- The 16 dirs cost **$60.12** against a $63.39 projection, so `LIVERUN_CAP` was never approached —
  but at the old $150 the *conservative* bound had left only $11.56, less than B_seed7 alone.

**`backfill_stage1.py` `SPEND_CAP` 32.00 → 44.00.** Same failure, one script over. The backfill is
6,050 calls (97 × 50 + 8 × 150); at the realized rate that is **$34.37**, so the $32 cap — sized on
the fit — would have raised during **test eval ~6 of 8, about 7 h in**, after every selection eval
was already paid for. $44.00 is 28% over realized and 19% over the $37.03 smoke bound. The run was
killed at 09:33 before its first checkpoint (nothing lost but ~21 min) and relaunched under the new
cap.

**Live measurement, seed 0 complete (11 candidates).** $3.261 over 550 metric calls =
**$0.005929/call**, projecting **$35.87** for the full 6,050 — slightly *above* the $34.37 estimate,
not below it. The $44.00 cap is correctly sized, with 23% margin.

*(An earlier 3-candidate reading of $0.005140 → $31.10 was recorded here and was wrong: per-candidate
spend rises with candidate index — 0.231 / 0.264 / 0.276 / 0.280 / 0.317 / 0.331 / 0.322 / 0.280 /
… — because later instructions are longer, so any early-sample mean understates. Superseded by the
full-seed figure above; kept as a note on why partial samples were not trusted.)*

⚠️ Third gate/code divergence: `APPROVED-backfill` (signed 2026-08-11) states *"Projected $27.49.
Cap $32.00."* Neel directed the raise, so it is authorized in substance, but the signed file
understates it — joining `APPROVED-liverun`'s *"$150.00"* and *"2 concurrent scorers"*. Gate files
are not touched by CC.

⚠️ The backfill's cap does **not** span restarts: `Meter.spend()` sums a per-process `lm.history`,
and resumed seeds are skipped without spending, so a fresh process starts the meter at zero. The
backfill is also outside `liverun_ledger.json` entirely. Program total lands ≈ **$167**.

### 0.4 Backfill: `--workers 32`, and the meter that was about to go blind — 2026-08-11

Two changes to `backfill_stage1.py`, both applied at the seed-0 checkpoint seam so nothing paid for
was thrown away.

**A. The spend meter would have stopped working at candidate ~33 of 97 — FIXED.** `run_live()`
opened **one LM for the whole job** (`:128`). The job is 6,050 metric calls × 6 LM calls =
**36,300 history entries** against dspy's `max_history_size = 10000`
(`dspy/dsp/utils/settings.py:35`), and `Meter.spend()` sums `lm.history`
(`eval_split.py:121-127`). Past the window the sum **silently undercounts**: the cap would never
have tripped for two thirds of the run, and the `spend_usd` written to
`stage1_backfill_endpoints.json` would have read ~$10 against a true ~$36 — a number later analysis
would have taken at face value.

This is precisely the hazard `score_candidates.py:88-93` documents and fixes with a per-dir LM.
`backfill_stage1.py` never got it because it was frozen (§7) until this week. Now: **fresh LM +
Meter per seed and per test eval** (largest window 14 × 50 × 6 = 4,200; test 900 — both well under
10,000), with a plain `spent` accumulator carrying the true job total across windows. `SPEND_CAP`
is now **$8.00 per seed** (mirroring the per-run-dir cap) and **`JOB_CAP = $44.00`** guards the
total.

⚠️ **This fixes the rollover, NOT the restart.** `spent` is a plain local (`:143`), so a fresh
process starts `JOB_CAP` at zero, and seeds resumed from checkpoint (`:158-160`) contribute nothing
to it. Both caps are per-process. Repeated kill/restart cycles therefore have no cumulative
tripwire, and each cycle can waste up to one seed's uncheckpointed selection pass (~$4) unnoticed.

**It has already bitten, benignly.** Seed 0's **$3.261** was paid by the process killed at 10:12;
the relaunched process resumed it at $0, so its `spent` excludes it and
`stage1_backfill_endpoints.json` will record **~$32.6 against a true ~$35.9**. Bounded, and inert:
`mde_sim.py` reads only `endpoints` (`:51`, `:59-85`), never `spend_usd`, so this is record-keeping
rather than analysis. The artifact is deliberately **left as written** — it should say what the
process that produced it observed — with the true total recorded here instead.

The durable fix, if the backfill is ever re-run, is the pattern the repo already has:
`supervisor.py:155-172` `ledger_total()`/`ledger_append()`, whose docstring is precisely this
problem — *"Rebuilt from the ledger file rather than held in memory, so it survives a restart."* A
`backfill/spend_ledger.json` appended beside each checkpoint write, summed at startup, would make
both `JOB_CAP` and `spend_usd` restart-durable.

**B. `--workers`, mirroring `score_candidates.py:175`.** The script is one process with serial
seed, candidate and test loops (`:135`, `:144`, `:169`), so `WORKERS = 8` was its *entire*
concurrency — 8 API streams, against the 32 the §8b pass had just sustained for ~9 h. Relaunched at
`--workers 32`. `eval_split.WORKERS` is left at 8: it is the proven per-process default for the
other consumer, which buys concurrency with processes instead.

**Measured, not projected:**

| | 8 workers | 32 workers |
|---|---|---|
| per candidate | 214 s | **80 s** (63–97) |
| speedup | — | **2.7×** |
| per-candidate spend | $0.231–0.331 | $0.234–0.301 — **unchanged** |
| job ETA | 7.2 h | **~2.4 h** |

**The 4× was not delivered — 2.7× was.** Sub-linear, as raising threads in one process usually is:
per-request latency rises with concurrency, and the Python-side work (BM25 retrieval, response
parsing) contends on the GIL. Crucially **cost per candidate did not move**, so the shortfall is
latency, not retry inflation — throttling would have shown up as extra spend for the same work.
Concurrency never changes the token count; only wall clock.

**Spent to date: $8.4278** ($3.2336 testsplit + $5.1942 smoke), both under their projections.
Program total = $8.4278 realized + $135.83 liverun + $27.49 backfill + $8.6 dose ≈ **$180.35**,
inside the ~$160–195 band. Every projected figure above is now derived from smoke measurements —
see §4.5 for the arm-blended arithmetic and why a flat ×24 of the smoke understates.

The backfill's 97 is a **realized count, not an estimate** (`backfill_stage1.py --resolve`,
measured): the 8 Stage-1 runs hold 11, 11, 13, 11, 14, 10, 13, 14 candidates.

---

## 1. Gated spends — the exact list awaiting Neel

| # | Gate file | What it buys | Cost | Blocks | Status |
|---|---|---|---|---|---|
| 1 | `APPROVED-testsplit` | grade a fixed 700-claim frame → test (150) + selection (50) | **$3.2336** *(measured)* | everything downstream | **DONE — both splits committed.** Gate still on disk; see §8-4 |
| 2 | `APPROVED-dose` | 30-event reproducibility control + 235×6 re-derivation | **~$8.6** *(est.)* | the §11-2 gate only | **not opened** — both halves now **implemented**, see §3 |
| 3 | `APPROVED-smoke` | one arm-T seed-0 run + its own §8b post-run pass | **$5.1942** *(measured)* | the launch decision | **DONE 2026-07-28→29** → §4 |
| 4 | `APPROVED-liverun` | the 24 runs + their §8b post-run pass | **~$136.03**, cap **$160** *(raised §0.1)* | the experiment | **partial** — 24 optimized, 8 of 24 scored ($72.64); §8b resume pending |
| 5 | `APPROVED-backfill` | 97 candidates × 50 selection, then 8 winners × 150 test | **~$27.49** *(est.)* | the MDE only | **deferred** — ready to run, but see §8-1 |

**Gate files are created by Neel only.** Every live script byte-verifies its gate (`gates.py:require`)
and exits 2 without it. **Re-verified 2026-07-29 under `.venv-armT` (measured): every live entry
point whose gate is absent still exits 2** — `backfill_stage1.py --run`, `dose_control.py --run`,
`dose_compute.py --live`, `score_candidates.py`, `run_state_dep.py` (both `--smoke` and not), and
`supervisor.py --waves`. `build_test_split.py` and `supervisor.py --smoke` now pass their gate,
because those two gates have been opened and spent — see §8-4 on why `APPROVED-testsplit` being
left on disk is a live hazard. The smoke paths demand `APPROVED-smoke`; the wave paths demand
`APPROVED-liverun`; `score_candidates.py` picks per run directory from its `config.json`, and a
mixed invocation requires **both**.

### Dependency order

The MDE branch **no longer blocks the launch**. §11-2's amended gate timing requires the MDE and its
framing label before `results.md` is read, not before `APPROVED-liverun`:

```
APPROVED-testsplit → build_test_split.py → test_split.json + selection_split.json (+sha256)
                                              ↓
                            APPROVED-smoke → supervisor.py --smoke   (arm T seed 0, alone,
                                              ↓                       run + its own §8b pass)
                                             measurements land in markers/SMOKE.DONE → plan.md §4
                                              ↓
                          APPROVED-liverun → supervisor.py --waves   (24 runs, width 6 — §4.7)
                                              ↓
                          APPROVED-liverun → supervisor.py --score   (§8b, 2 scorers — §4.6)
                                              ↓
                                             tag pre-analysis snapshot
                                              ↓
  ┌───────────────────────────────────────────┤
  │  APPROVED-backfill → backfill_stage1.py --run → stage1_backfill_endpoints.json
  │  APPROVED-dose     → dose_control.py --run (|ΔD_30| ≤ mean → markers/DOSE_CONTROL.PASS,
  │                                             else STOP, drop the dose — v2.2 §11-0)
  │                    → dose_compute.py --live (REFUSES without that marker) → D
  │                              ↓
  │                    mde_sim.py --endpoints … --dose D  →  MDE + §11-2 framing label
  └───────────────────────────────────────────┤
                                              ↓
                                        results.md   ← the label must be on disk BEFORE this
                                              ↓
                                        read against §9 → interpretation → second path
```

The two backfill/dose branches may clear before, during, or after the waves. They may **not** clear
after `results.md` is read; if they have not, the run is estimation-only by default. **`APPROVED-
backfill` is explicitly deferred** (Neel, 2026-07-23): it is off the launch path and gets decided
after the waves, subject to that one hard constraint.

`supervisor.py --smoke` refuses without `APPROVED-smoke` **and** without both split artifacts on
disk — the smoke evaluates its own endpoint, so it has nothing to score against until
`build_test_split.py` has run. `--waves` additionally refuses without `markers/SMOKE.DONE`.

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
`mde_sim.py` sha256 `6d11de278014b7e7de41cf55cb56cad4f92680f5b5f6159e7c6583bf84bce5cc`

*(Moved 2026-07-29 from `300f7cd9…cff626`. The only change was §8-1: `--endpoints` now accepts
either a bare list or the dict `backfill_stage1.py` actually writes. The `--selftest` figures above
were re-run against the new hash and are unchanged — no simulation behaviour moved.)*

**MDE value:** 0.06332 endpoint points   **Framing label:** CONFIRMATORY   **Assigned at:** 2026-08-12, before results.md was read.

D = 1.4431827353722393 (235 events, dose.json sha256 9f39646103a63d7d...); endpoint sd 0.0392, n = 8.
MDE at 80% power, exact sign-flip, alpha = 0.05. Trigger 3 x (D x beta/2) = 0.08213.
MDE 0.06332 < trigger, so the 11-2 default does not flip. GATE BITES: False.
mde_sim.py sha256 6d11de278014b7e7de41cf55cb56cad4f92680f5b5f6159e7c6583bf84bce5cc

Caveats recorded WITH the label, before any result was read:
1. Near miss: MDE is 77% of trigger, on a screen the design itself twice calls heuristic, not a power
   calculation, and which juxtaposes endpoint units against one-step specificity units.
2. The pass is driven by D landing high. R2 (11-1) predicted D well under 1 SD and expected the gate to bite.
   Measured D = 1.4432, about 44% above that ceiling. Any D below 1.112 would have bitten.
3. Confirmatory is not well-powered. MDE is 2.3x the implied one-step effect (0.02738), so an effect the size
   the screen predicts would not be reliably detected at 8 seeds. A null here is MDE-bounded, never proof of zero.
4. Conservatism direction: MDE assumes rho = 0 on paired seeds (B-arm SD, 11-3 caveat). Positive pairing
   correlation shrinks the true MDE, so 0.06332 is an upper bound.

---

## 3. Dose — amended to v2.2, both halves now implemented

**Definition (v2.2 §11-0), validated at $0** (`dose_compute.py --selftest`, plus a negative control
confirming the self-test *fails* when `gap()` is sabotaged):

```
gap_e = x_(4)  -  (1/20) SUM_{|S|=3} min(x_S)        [x = 6 novelties, ascending]
D_s   = mean_{e in s} gap_e / sd_s                    [each seed in its own within-run SD]
D     = mean_s D_s
```

`sd_s` per seed (ddof=0, recomputed from `features.csv`):
`[0.021870, 0.024433, 0.029460, 0.023196, 0.028713, 0.025238, 0.025011, 0.026538]`

**Event set: 235** (v2.1 §20-2 - ordinal-0 excluded; the frame beta was estimated on). Enumerated
from `features.csv` rows with a non-empty `knn_emb_fb_min`; verified 243 rows, 235 kept, and the 8
dropped are exactly `event_ordinal == 0`.

### 3.1 What v2.2 changed, and why

**`x6` is now all six candidates re-derived from ONE fresh execution**, not 3 persisted from
2026-07-09 plus 3 re-derived. Two independent reasons:

1. **The old 90/90 byte-exact control could only ever have returned STOP.** Three temp-0
   re-executions of the same parent, same venv, hours apart, are already on disk (`pairs/`,
   `pairs_pre_mmap/`, `pairs_mmap_check/`) and agree on **15 of 24** rendered feedback blocks
   (measured 2026-08-03, $0). P(90/90) is about **4e-19**. Temp-0 is not a bitwise contract at the
   API level, and the 3-hop chain amplifies it - one differing token in the hop-1 query changes the
   BM25 hits, the notes, and every hop after.
2. **The mix it licensed was unsound regardless.** The 3 persisted blocks are `B_e`, and `B_e` was
   **selected** by `multiset_match` to match the parent's score profile on `A_e`
   (`hover_swap_run.py:192-195`). They were never an exchangeable half of the six, yet `x_(4)` sits
   exactly on that boundary.

**The control is replaced, not deleted.** It now measures what actually threatens `D` - this
program's own re-execution noise - on the real dose data: re-derive the same frozen 30-event sample
**twice in one session**, compute `D_30` on each pass, and require

> **|D_30(pass 1) - D_30(pass 2)| <= mean(D_30)**

The bar was fixed before any result existed. Failure carries the unchanged pre-registered response:
**drop the dose**, never the biased 3-candidate shrink, and `results.md` takes the estimation-only
framing. The sample is **not re-drawn** (still `random.Random(20260709)`, frozen 2026-07-09), and
`dose_control_expected.json`'s 90 hashes stay on disk as the record of the superseded bar.

**Acknowledged:** this removes an unconditional STOP in favour of a conditional one. Ratified
explicitly in the design doc's amendment log rather than allowed to happen as a side effect.

### 3.2 Cost - the $3.61 line was doubly wrong

| | v2.1 | **v2.2** |
|---|---|---|
| re-derivation | 3 x 235 = 705 calls | **6 x 235 = 1410 calls** |
| control | 30 x 3 = 90 calls | **30 x 6 x 2 = 360 calls** |
| price/call | $0.004543 *(fit)* | **$0.006121** *(smoke-measured, §4.3)* |
| **total** | **$3.61** | **~$8.6** |

Both factors moved: twice the candidates, and a per-call rate the smoke measured 35% above the fit
the old line used. `SPEND_CAP` is **$11.00** in `dose_compute.py` and **$2.50** in `dose_control.py`
- not $3.61, or the sweep dies mid-run. `gates.py` restated to match.

### 3.3 Implementation (2026-08-03) - both stubs are gone

`dose_acquire.py` is new and shared by both consumers, the same anti-drift discipline `eval_split.py`
applies to the two §8b consumers. It imports the swap harness rather than copying it, which also
installs the `probe.load_index` mmap monkeypatch.

**Acquisition runs under `scratch/hover_probe/.venv`** - the venv the swap itself ran on,
byte-identical to `.venv-armT` on dspy 3.2.1 / gepa 0.0.27 / litellm / openai / numpy / bm25s /
PyStemmer / Python 3.12.13. Library drift is therefore not a variable. **Novelty scoring runs
separately under `.venv-armT`** (sentence-transformers is not in the probe venv) - the same split
`verify_novelty.py` already uses. Verified 2026-08-03: the full import chain bootstraps and the
mmap patch takes.

Two properties of the scorer that are load-bearing:

- **The archive is encoded in its own `encode()` call, the candidates in a second one.**
  sentence-transformers sorts by length within a batch, so folding 1410 new texts into the archive
  call would change the archive's batch composition and break the byte-verified 235/235
  reproduction. Two calls keeps the archive bitwise what the screen committed.
- **Candidates are scored against the archive as of their event and never enter it.** They are
  counterfactual draws, not reflection objects the run produced. `n_arch` is snapshotted before the
  event and the archive advances strictly after - `verify_novelty.py:97-102`.

A **$0 structural check** runs once per acquisition: Feedback is `probe.build_si(gold, predicted)`,
a pure function of the retrieved title set, so it cannot depend on `adapter.rng` - which governs
only which trace instance appears under `## Inputs`. The check re-renders the *same*
`EvaluationBatch` under a different rng seed and asserts the Feedback strings are unchanged. If it
ever fails, the acquisition says so loudly.

**Free degeneracy pre-estimate (measured, $0)** - using the screen's own 3 reflected members per
event, the mean within-event novelty spread (max-min) is **3.06 within-run SD**. Not the dose (that
needs 6 candidates), but it rules out §15-12's degenerate case: there is real selection room.

**The interlock holds.** `dose_control.py` writes `markers/DOSE_CONTROL.PASS` only when the bar
clears; `dose_compute.py --live` refuses without it, after its gate. Order is gate -> marker -> work.

---

## 4. Per-run cost and time — MEASURED

**The live smoke ran 2026-07-28→29 under `APPROVED-smoke`** (v2.1.1 §13-7, its own gate, split out
of `APPROVED-liverun` so that approving the measurement is not the same act as approving the
launch). `supervisor.py --smoke` ran arm T / seed 0 alone, then invoked `score_candidates.py` on
the smoke dir, and wrote `markers/SMOKE.DONE`. `--waves` refuses to start without that marker.

Per the calibration rule (top of this file), everything below is now **(measured)** or explicitly
**(derived)** from measured quantities. Nothing in §4 is a pre-smoke estimate any longer.

### 4.1 Smoke measurements (`markers/SMOKE.DONE`)

| measurement | value |
|---|---|
| optimization spend | **$1.8279** |
| post-run §8b pass spend | **$3.3663** |
| **total smoke spend** | **$5.1942** |
| wall clock — optimization | **6778.2 s = 1.88 h** |
| wall clock — §8b pass | **2348.6 s = 0.65 h** |
| peak RSS per process | **1460.3 MB** |
| rate-limit backoffs | **0** |
| counter vs §6a five-site model | **302 actual = 302 predicted — AUDIT PASS on real scores** |
| events / candidates / accepts | **24 child-bearing events, 8 candidates incl. seed, 7 accepts** |
| task / reflection calls | **1812 / 24** |

The counter row is the one that matters most for §6a: the five-site model was previously verified
only against a mocked LM. It now reproduces the realized call count **exactly** on live scores.

### 4.2 §8b outcome on the smoke — first live evidence bearing on B10

| | |
|---|---|
| `sel_best_idx` | **3** |
| `val_best_idx` | **4** |
| **`agrees_with_val_argmax`** | **false** |
| `sel_tie_broken` / `sel_returned_seed_prompt` | false / false |
| `endpoint_test_mean` | **0.6511** |

On this run the selection-split argmax picked a **different candidate** than val-argmax would
have — consistent with B10, the finding that drove the entire v2.1 amendment. Read it narrowly:
**n = 1, excluded from analysis under §13-5, and not evidence for the hypothesis.** It is evidence
that the amendment *changes the endpoint*, not that it changes it correctly.

### 4.3 Realized rates — the fitted model was wrong about §8b

The pre-smoke fit, retained for provenance:

```
Stage-1 seed0:  302 metric calls + 32 reflection calls = $1.9078
Swap, per pair:  45 metric calls +  6 reflection calls = $0.3049
  ⇒ m ≈ $0.004543 / metric call ,  r ≈ $0.016744 / reflection call
```

What the smoke actually realized:

| rate | value | basis |
|---|---|---|
| optimization-side implied `m` | **$0.004722** / metric call | `(1.8279 − 24×r) / 302` |
| grading (`build_test_split.py`) | **$0.00462** / claim | `test_pool_summary.json`, 700 claims |
| **§8b evaluation** | **$0.006121** / eval | `3.3663 / 550` — **1.35× the fitted `m`** |

The optimization and grading rates land within 4% of the fit. **§8b does not**, and it is 35% high.
Inferred mechanism (**not measured** — the smoke establishes the rate, not the cause): §8b evaluates
*optimized candidate programs*, whose prompts are longer than the base program the fit was derived
from, so each eval carries more input tokens. This is the single largest reason the pre-smoke §8b
line was low, and §8b is the dominant cost of the program.

### 4.4 Per-run cost — candidate count is arm-dependent

The pre-smoke model carried one `~10–14 cand` line for every arm. That is superseded. The
300-metric-call budget is arm-invariant, so a 6-wide minibatch (T, C) burns it in **fewer events**
than a 3-wide one (B) — the smoke produced 24 events / 8 candidates, where the eight Stage-1
(b = 3, arm-B-like) runs realized 11, 11, 13, 11, 14, 10, 13, 14 (mean 12.125). §8b spend scales
directly with candidate count, so **arm B is the expensive arm on §8b even though it is the cheap
arm on optimization.**

| line | arm T/C (b=6) | arm B (b=3) |
|---|---|---|
| per-run optimization | **$1.83** (measured) | ~$1.96 (derived: 302×m + 32 reflection calls) |
| per-run §8b (sel + test) | **$3.37** (measured, 8 cand) | ~$4.63 (derived, 12.125 cand) |
| **per-run total** | **$5.19** | **~$6.59** |

*(midpoint test eval, if §9 demands it on a given run: +1 × 150 × m ≈ +$0.92 at the realized §8b
rate, still unbudgeted and still conditional.)*

### 4.5 The 24-run projection

```
flat ×24 of the smoke (as recorded in SMOKE.DONE) : $124.66   ← LOWER BOUND, arm T only
arm-blended projection                            : $135.83   ← the point estimate
    arm B   8 runs × $6.59 = $52.72
    arm C   8 runs × $5.19 = $41.55
    arm T   8 runs × $5.19 = $41.55
```

**`APPROVED-liverun`'s ~$120–150 band holds**, with $135.83 near its middle.

**The caveat in `SMOKE.DONE` points the wrong way and is corrected here.** It reads "arm T only; B
is cheaper per run and C sits between them", which implies a flat ×24 is an *upper* bound. That is
true of the optimization half and **false of the total**: arm B is cheaper on optimization but more
expensive on §8b, §8b dominates, so a flat ×24 of the T smoke is a **lower bound** on the program.
The marker is left as written (it is the raw measurement record); this file is the corrected one.

### 4.6 Wall clock — the §8b pass dominates, and it is bought with processes

```
optimization, width 6, rolling pool  : 24/6 x 1.88 h  =  ~7.5 h
§8b pass, supervisor.py --score      : ~10.4 h   (2 concurrent scorers)
                                       ---------
program wall clock                     ~17.9 h     (serial would be ~28.3 h)
```

Per-run §8b, refit from the smoke's own timings. Candidate 0 is the **seed prompt** — unoptimized,
verbose, **1166.2 s** against a 168.9 s steady state — and **every run has one**:

```
per-run = 1166.2 (cand 0) + (n-1) x 168.9 + 507 (test) + 32 (bootstrap)
  arm T/C, 8 cand     : 2888 s = 48.1 min    <- reproduces the measured 2888 s exactly
  arm B,  12.125 cand : 3584 s = 59.7 min
serial over 24        : 20.8 h        2 concurrent : 10.4 h        3 : 6.9 h
```

Bootstrap is only ~32 s (the smoke's §8b subprocess ran 2888 s; candidates sum to 2348.6 s and the
150-eval test pass is ~507 s), so a process per run costs ~13 min across all 24.

**SUPERSEDED 2026-08-10 — kept as the record of what the smoke predicted.** The 8 live §8b dirs
measured every term higher than the smoke's refit, and the cand-0 term was not a "verbose seed
prompt" at all — it was the §8-8 index-load race:

```
                        smoke refit    live measured (n=8)     post-fix
cand 0                    1166.2 s     1917 s (1778-3858)      ~= steady state
candidates 1..n            168.9 s      234 s (171-331)        unchanged (API-bound)
test pass (150)              507 s      853 s                  unchanged
bootstrap                     32 s      n/a                    3.9 s (measured)
```

The cand-0 penalty was **~1683 s per run dir**, and the fix deletes it — ~7.5 h of pure waste across
the remaining 16, before counting the 8 dirs that died outright. Revised model:
`per-run = 4 + n x 234 + 853`. For the **16 unscored dirs (167 candidates): 14.7 h serial, 3.7 h at
`SCORE_WIDTH = 4`** (§0.2). The steady-state and test terms are *not* expected to improve on a
healthy machine: they are 8 concurrent `gpt-4.1-mini` round-trips, and network latency does not care
that the machine stopped thrashing.

**Concurrency is bought with processes, not threads.** `eval_split.score_candidate` is *already*
8-way threaded (`ThreadPoolExecutor(max_workers=WORKERS)`, `eval_split.py:42,155-156`), and the
smoke's 168.9 s/candidate already reflects that. 8 is the profile the smoke proved at 0 backoffs;
`eval_split` has no backoff counter of its own (litellm retries invisibly at `num_retries = 3`), so
raising it would be flying blind. Two *processes* at 8 each keeps the proven per-process shape, and
a crash costs one run rather than the pair.

**Not overlapped with the waves.** Doing so would stack 6 optimization processes (~1.46 GB each)
against the scorers, blowing the 8.6 GB budget width 6 was chosen for, and put 22 streams against a
profile proven only to 8.

`SMOKE.DONE` records `wall_clock_h_at_width: 5.65` — the **optimization half at width 8**,
superseded on both counts.

### 4.7 Wave plan — width 8 → **6**

**Width is now 6**, re-decided on the smoke's RSS exactly as this section required. The smoke
measured **1460.3 MB/process** — 57% above the ~0.93 GB/process the width-8 default rested on
(the swap, after the mmap fix). At width 8 that is **11.4 GB resident on a 16 GB machine**; at
width 6 it is **8.6 GB**. Backoffs were **0**, so there is no rate-limit pressure — this is a
memory decision alone, and it moved width **down**, not up.

`supervisor.py` has a pre-spawn hold at `MEM_MIN_GB = 1.5` and never kills a running process, so
width 8 would have degraded by stalling spawns rather than by OOM. Width 6 avoids relying on that.

**The wave manifest is unchanged.** `supervisor.py:250-266` flattens all three waves into one
pending list and runs a **rolling pool** at `WIDTH` with no wave barrier — the wave label is
carried for logging only. So `WIDTH` is concurrency, not a partition, and the manifest's balance
properties survive untouched. Regenerating at `WIDTH = 6` left all 24 run cells **byte-identical**;
only the `width` field and its note changed (verified by diff).

```
wave 1: B0  B6  C4  T2  B3  C1  C7  T5     (B3 C3 T2)
wave 2: B2  C0  C6  T4  B5  C3  T1  T7     (B2 C3 T3)
wave 3: B4  C2  T0  T6  B1  B7  C5  T3     (B3 C2 T3)
```

Each arm covers seeds 0–7 exactly once; each seed's three arms land in three different waves, so a
wave-level disturbance cannot hit one seed's three arms together. **Raising width again requires a
new RSS measurement, not an argument. There is no auto-ramp, and 16 is never resurrected
untested.** Launch under `caffeinate -dims`.

`supervisor.py`'s `EST_PER_RUN = 2.90` is now known to overestimate optimization by ~50% (measured
$1.83). It was **left high deliberately**: it only feeds the `TRIPWIRE` in-flight guard, where
overestimating stops launching *earlier*, and total optimization (~$45) sits far below `TRIPWIRE`
($80), so it never binds in either direction.

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
| `gates.py` | `cdb95bee187c2715cd27a3ff05bf41d3eb822ebbf0f8cf2af613a45fe439862e` | imported; 5 gates — **moved 2026-08-10**, liverun cap $150 → $160 (§0.1); docstring only |
| `dose_control.py` | `c653965a22cbd4f3cbf6f84bdf06d650de9e45113aa28f0df4f8ae19fa75d20d` | ❌ gated — **moved 2026-08-03**, v2.2 reproducibility control implemented (§3.3) |
| `dose_compute.py` | `0fbd2b9554429da05fd797aea4ead205c91763f51c2b4afe4e874e0b34e04871` | ❌ gated — **moved 2026-08-03**, `live()` + `score_texts()` implemented (§3.3) |
| `mde_sim.py` | `6d11de278014b7e7de41cf55cb56cad4f92680f5b5f6159e7c6583bf84bce5cc` | ✅ selftest — **moved 2026-07-29**, accepts dict-or-list endpoints (§8-1) |
| `dose_acquire.py` | `54e793ac0e0d235a0e3698e0c0df838359d71b2b46366d17fd93d3ca53b23a10` | **NEW 2026-08-03** — shared dose acquisition (§3.3) |
| `eval_split.py` | `de874501d780deaf9fc321291559da5e3a4a9bfaaa432cf2a71135c6ce86407b` | shared evaluator, gated by callers — **moved 2026-08-10, first time**: `bootstrap()` now installs the mmap patch and warms the index (§8-8) |
| `build_test_split.py` | `8eeb575fa434495ad2f616f582a9e20840af31be5168f6316885956a2f5af037` | ❌ gated; `--selftest` PASS — **moved 2026-08-03**, `--force` guard (§8-7) |
| `backfill_stage1.py` | `26ffa79fd85ba223d7d391a78961337e2c7ad272d8cc2cd63bc1ee287a8fff05` | ❌ gated; `--resolve` PASS ($0) — **moved 2026-08-11**, `SPEND_CAP` $32 → $8/seed + `JOB_CAP` $44, per-seed LM, `--workers` (§0.3, §0.4); freeze ended, see note below |
| `run_state_dep.py` | `70d314e4dc521c0f4f6c36cc7c8a2f70b083cf51aede4973215d763f77eca8c5` | ❌ gated (smoke/liverun); `--dry` PASS, 3 arms, writes nothing |
| `score_candidates.py` | `93f90cf5e51483021d70f18ad995544fdc5974188990814111809a127fc4cd83` | ❌ gated per run dir; `--dry-run` PASS ($0) — **moved 2026-08-10**, `SPEND_CAP` $6 → $8 (§0.1) |
| `supervisor.py` | `50cba941ed679882a746fe9ee2aa42bca60e66d4720f2e13e7c8d57050308623` | ❌ gated; `--plan` PASS ($0) — **moved 2026-08-10**, `LIVERUN_CAP` $150 → $160 (§0.1) and `SCORE_WIDTH` 2 → 4 (§0.2) |
| `make_wave_manifest.py` | `1f61a9fae170c97d1948dd8eab0ec8e542cc4701b322057629b567955520916e` | ✅ $0, manifest regenerated — **moved 2026-07-29**, `WIDTH` 8→6; **all 24 run cells byte-identical** |

**2026-07-29:** `supervisor.py` and `make_wave_manifest.py` moved for the width decision (§4.7),
`mde_sim.py` for §8-1, `dose_control.py`/`dose_compute.py` for the §8-2 interlock.

**2026-08-03:** `score_candidates.py` (§8-5, the launch-blocking Meter bug), `supervisor.py` again
(§8-3 `--score`, §8-6 ledger/cap), `build_test_split.py` (§8-7 `--force`), `gates.py` (dose
repriced), `dose_control.py`/`dose_compute.py` (v2.2 implemented), plus new `dose_acquire.py`.
**Verified byte-identical through both passes:** `eval_split.py`, `backfill_stage1.py`,
`novelty.py` — the three files everything else is measured against.

**2026-08-10:** `eval_split.py` **moved for the first time**, breaking the byte-identical streak
above. It had to: `bootstrap()` imported raw `probe`, so the §8b path silently ran without the mmap
patch every sibling path installs, and its 8 worker threads raced `probe.load_index`'s unlocked
check-then-set — ~40 GB per process, 8 SIGKILLs and a kernel panic on 2026-08-06 (§8-8,
`notes/PHASE2-DIAGNOSIS.md`). `bootstrap()` now installs the patch and calls `assert_mmap()`, which
warms the index single-threaded before any executor exists. **`backfill_stage1.py:113` calls the
same `bootstrap()` and inherits the fix without moving** — the anti-drift discipline paying out.
Also moved: `supervisor.py` + `score_candidates.py` + `gates.py` for the §0.1 cap raise. Measured
post-fix: **1.024 GB per scorer process** (peak 1.244 GB), index constructed **once**, 0 threads
entering the loader body vs 8/8 before.

`backfill_stage1.py` was **deliberately left untouched** through 2026-08-03. Its docstring
(`:19-25`) says $27.48 where `resolve()` and `gates.py:10` say $27.49 — a one-cent rounding
artifact with no functional effect. Correcting it would have broken the byte-identical match to its
frozen hash on a script that executes a $27.49 spend, which was worth more than the cent.

**That freeze ended 2026-08-11**, and not for the cent. `SPEND_CAP = 32.00` was sized on the
$0.004543 fit; at the realized $0.005681/call the job costs $34.37 and the cap would have raised
during test eval ~6 of 8, roughly 7 h in, after all 97 selection evals were paid for (§0.3). A cap
that stops the job it is supposed to protect is a functional defect, not a rounding artifact, so
the script moved: `SPEND_CAP` → 44.00 plus a dated REPRICED note in the docstring. `M` at `:50` was
left at the fit deliberately — it feeds the pre-spend estimate `resolve()` prints, where
over-estimating is the silent failure. The one-cent discrepancy is still there, still not worth
fixing. Recorded here instead.

---

## 8. Blocking items that are NOT spend

1. ~~v2 §20-1 `skip_perfect_score` scope~~ — **ratified `chosen3`** (v2.1 §20-1).
2. ~~v2 §20-2 dose event set~~ — **ratified 235** (v2.1 §20-2).
3. ~~B10, the tie-break endpoint~~ — **amended: §8b selection split** (v2.1).
4. ~~§20-3 uniform vs stratified~~ — **resolved by default: uniform, both splits**.
5. ~~`.venv-armT` cannot run the task program~~ — **rebuilt from `armT-lock.txt`; both $0 gates
   re-passed**.

6. ~~midpoint test evals pre-paid across 24 runs~~ — **decided 2026-07-23: not pre-paid.** Stays the
   §9 conditional; the midpoint candidate is still identified free on every run.
7. ~~backfill on the launch path~~ — **decided 2026-07-23: deferred.** Clears before `results.md` is
   read, or the run is estimation-only by default.
8. **`dose_compute.py --live` and `dose_control.py --run` are still stubs past their gate.** See §9
   and the §3 note — that is **two** implementations, not one.

### New, found 2026-07-29 in the post-smoke readiness sweep

**8-1. `mde_sim.py` could not read what `backfill_stage1.py` writes — FIXED.**
`backfill_stage1.py:188` writes a dict `{"design", "endpoints", "rows"}`; `mde_sim.py` did
`np.asarray(json.load(...))` and its help string expected a bare list, so it raised on the dict.
The chain at §1 broke on the step **immediately after** the $27.49 backfill spend — the artifact
was correct, its consumer could not parse it. Fixed on the **consumer** side (`mde_sim.py`, now
accepts either shape): `backfill_stage1.py` is byte-identical to its §7 hash and the dict carries
provenance worth keeping. Verified against both shapes at $0.

**8-2. The dose control → compute interlock did not exist — FIXED.** See the §3 note.
`markers/DOSE_CONTROL.PASS`, written only on 30/30, required by `dose_compute.live()`.

**8-3. The §8b pass was serial and was the program's wall-clock bottleneck — FIXED.**
`supervisor.py --score` now runs one `score_candidates.py --run` process per run dir at
`SCORE_WIDTH`, resume-by-artifact on `endpoints.json`. Width raised 2 → **4** on 2026-08-10 on the
first real scorer memory measurement (§0.2): **3.7 h** for the remaining 16 dirs, against 14.7 h
serial. See §4.6 for the superseded smoke model and the live timings that replaced it.

**8-4. `build_test_split.py` idempotence — SUPERSEDED by 8-7 below; kept for the record.** `APPROVED-testsplit` remains in place after the spend, and the script has **no
overwrite or already-done guard**: reaching `main()` past the gate calls `grade_frame()` directly
(`:322-323`), re-spending ~$3.23, then `commit_split()` **overwrites** `test_split.json` and
`selection_split.json` (`:332-334`). The draws are seeded and the frame is fixed, so the splits
would *probably* come back identical — but grading is an LM call, and if any one of the 700 claims
graded differently the `imperfect` pool shifts and both splits move, silently invalidating the
sha256s already recorded in the smoke's `endpoints.json` and everything downstream that hashes
them. Two clean fixes, either sufficient: **(a)** Neel removes `APPROVED-testsplit` now that it is
spent, or **(b)** add an early guard refusing to run when `splits_manifest.json` exists unless
`--force` is passed. `--splits-only` already exists as the $0 redraw path and is unaffected.

**8-5. `score_candidates.py --all` could not have completed 24 runs — FIXED, and it was
launch-blocking.** `main()` built ONE LM and reused it across every run dir, while `Meter.spend()`
(`eval_split.py:121-127`) sums the whole of `lm.history` and a fresh `Meter` per dir does not reset
it. Dir 1 was correct; **dir 2 reported dir 1 + dir 2**, and `SPEND_CAP = 6.00` — documented as
*per run dir* — was therefore checked against a running total, raising `RuntimeError` out of
`ThreadPoolExecutor.map` partway through **dir 2**. Past ~10k calls dspy's
`max_history_size = 10000` window would then have made `spend()` silently *under*count. Never
exercised: the smoke ran `--run` on a single dir, where all three behaviours are correct. It would
have surfaced ~40 minutes into a $135 launch. **Fix:** the LM is now opened inside `process()`, one
per run dir. Demonstrated before and after at $0 with a stubbed history.

**8-6. Nothing enforced a program-level cap — FIXED.** `TRIPWIRE`/`HARDCAP` are optimization-only
and `SPEND_CAP` is per run dir, so the gate's headline number had no mechanism behind it.
`liverun_ledger.json` now accumulates across **both** phases and `LIVERUN_CAP = 150.0` is checked
before every spawn in `--waves` and `--score`. Idempotent on resume, so a re-run never double-counts.

**8-7. `build_test_split.py` idempotence — FIXED (was 8-4).** `--force` is now required to re-grade
once `splits_manifest.json` exists. `APPROVED-testsplit` stays on disk as the record of the spend,
per Neel 2026-08-03; the guard, not the gate, is what protects the frozen splits.

**8-8. The §8b path silently ran without the mmap patch, and raced its own index loader — FIXED
(2026-08-10).** Full evidence in `notes/PHASE2-DIAGNOSIS.md`. Two defects, both live only on
`--score`:

- `eval_split.bootstrap()` imported raw `probe`, so `probe.load_index` stayed the frozen
  non-mmap version — **~6 GB resident per copy** (measured: corpus 4.31 GB + vocab 0.69 + npy 1.07),
  where `hover_swap_run.py:30-46` had proven 0.92 GB mmapped back in July. The §8b path was the one
  path in the repo with no `assert_mmap()`, which is exactly how it regressed unnoticed.
- `probe.load_index` (`probe.py:21-27`) is an unlocked check-then-set, and `score_candidate()` fans
  out to `WORKERS=8` with the global still cold. **Measured 8/8 threads entering the loader body**
  → ~40 GB transient per process, ×`SCORE_WIDTH=2`.

Cost: **8 runs SIGKILLed** (`rc=-9`, all with ≥11 candidates), 2 abandoned, and a kernel watchdog
panic on 2026-08-06. Jetsam recorded two `python3.12` processes at 26.1/24.8 GB **73 seconds after
spawn**. The tell is in the surviving artifacts: `selection_scores.json` `elapsed_s` shows candidate
0 at 1778–3858 s and every later candidate at 170–330 s — a startup event, not accumulation.

Fix: `bootstrap()` installs the patch and calls `assert_mmap()`, which warms the global
single-threaded before any executor exists, making the race unreachable without editing frozen
`probe.py`. Note the race in `probe.py` itself is **unchanged** — a cold threaded call still races;
what changed is that no §8b caller can make one. Verified at $0: **1.024 GB** per scorer process
(peak 1.244 GB), exactly **1** index construction, **0** loader entries under an 8-thread fan-out,
retrieval identical threaded vs serial 8/8.

**Nothing non-spend blocks `APPROVED-liverun`.** 8-4 is a hazard to an *already-committed* artifact,
not a precondition for the launch. 8-8 was a live blocker and is cleared; the §8b resume awaits
Neel's go, not a code change.

---

## 9. The one thing `APPROVED-dose` cannot buy tonight

**Both halves of the dose live path exit with `NOT IMPLEMENTED BEYOND THE GATE`.** This was flagged
at the v2.1 commit and is unchanged, because the brief that produced it said "2c. `APPROVED-dose`
unchanged":

| script | state |
|---|---|
| `dose_control.py --freeze-expected` | ✅ done 2026-07-09; expected side frozen and committed |
| `dose_control.py --run` | ❌ **stub** — verifies the gate, then exits with the spec |
| `dose_compute.py --selftest` / `--pre-estimate` | ✅ both PASS at $0 |
| `dose_compute.py --live` | ❌ **stub** — verifies the gate, then exits with the spec |

Creating `APPROVED-dose` is therefore **harmless but non-productive**: the scripts verify the gate,
print what remains to be built, and exit without an API call. No money moves, and the gate file stays
valid for whenever the path is implemented.

What remains is real work, not glue: rebuild each sampled event's parent candidate from Stage-1's
`program_candidates`, re-execute it through the adapter with `capture_traces=True`, render feedback
through the identical `make_reflective_dataset` path as `hover_swap_run.py:201`, sha256 each block
against the frozen expected side, and only then re-derive the 3 unmatched candidates across 235
events. Getting it subtly wrong yields a *bogus determinism verdict*, which is worse than not having
one — being unfudgeable is the control's entire purpose.

**Recommendation: leave `APPROVED-dose` for a session where that path is implemented and read.** It
is off the launch critical path under §11-2's amended timing and blocks nothing tonight.

---

## 10. Launch handover — every gate and command, in run order

*Written 2026-08-03. **CC does not create gate files** (`gates.py:33`) — every `cat > APPROVED-*`
block below is for Neel to run. Caps quoted here are the constants actually on disk; they are
re-read from the source on every edit to this section, not retyped from memory.*

### Step 1 — the liverun gate (~$135.83, cap $150)

```bash
cat > /Users/neeldankar/Desktop/gepa-project/analysis/state_dep/APPROVED-liverun <<'EOF'
APPROVED-liverun — Neel, 2026-08-03
The 24 state-dependent runs (3 arms x 8 paired seeds) plus their §8b post-run
selection pass: every candidate scored on the 50-claim selection split, then the
argmax scored on the 150-claim test split.
Projected $135.83 blended from the smoke (arm B $6.59/run, arms C and T $5.19),
NOT the $124.66 flat x24 in SMOKE.DONE, which is arm-T-only and a LOWER bound.
Program cap $150.00 across BOTH phases, enforced by liverun_ledger.json.
Inner guards unchanged: optimization tripwire $80 / hard cap $95; §8b $6.00 per
run dir. Waves at width 6, §8b at 2 concurrent scorers. Projected window ~17.9 h.
Does NOT authorize the backfill ($27.49) or the dose (~$8.6) — separate gates.
EOF
```

### Step 2 — the 24 optimization runs (~7.5 h, width 6)

```bash
cd /Users/neeldankar/Desktop/gepa-project
PY=analysis/state_dep/.venv-armT/bin/python

nohup caffeinate -dims $PY analysis/state_dep/supervisor.py --waves \
      >> analysis/state_dep/logs/supervisor.out 2>&1 &
```

### Step 3 — the §8b pass (~3.7 h for the remaining 16, 4 scorers). ONLY after step 2 logs `COMPLETE`

```bash
nohup caffeinate -dims $PY analysis/state_dep/supervisor.py --score \
      >> analysis/state_dep/logs/supervisor.out 2>&1 &
```

**Do not overlap steps 2 and 3.** `liverun_ledger.json` enforces the $150 cap across both, but
nothing enforces memory: 6 optimization processes (~1.46 GB each) plus scorers exceeds 16 GB.
Step 3 refuses to score any run whose optimization has not finished, and both steps are
resume-by-artifact — re-running either skips completed work at $0.

**Watch the first scorer — the canary is TIMING now, not memory.** Scorer RSS has been measured
(§0.2: 791 MB footprint, 570.8 MB dirty) and `assert_mmap()` fails loudly at bootstrap if the mmap
patch ever regresses, so memory is no longer the thing that can silently go wrong. Rate limiting
is: litellm retries 429s internally and `rate_hit` cannot see them (§0.2), so throttling at
`SCORE_WIDTH = 4` (32 concurrent streams, a 2× extrapolation from the only sustained observation)
would show up as slower work and higher spend, never as an error.

```bash
tail -f analysis/state_dep/logs/score_*.log        # per-candidate: "cand  N/M  sel_mean=... 234s"
```

- **per-candidate `elapsed_s` ≈ 234 s** is the baseline, from the 8 dirs already scored (range
  171–331). Climbing to **400 s+ means you are being throttled and paying for it** — kill, set
  `SCORE_WIDTH = 2`, restart. Step 3 is resume-by-artifact, so the restart costs $0 for finished
  dirs (but a dir killed mid-flight re-runs its test pass; `selection_scores.json` resumes free).
- **`MEM HOLD` lines** mean `avail_gb()` fell under `MEM_MIN_GB = 1.5` and the 3rd/4th spawn is
  being withheld — fails closed, effective width 2–3. Close Chrome/Cursor and it clears.
- **Footprint ~0.8 GB/process.** Well above ~1.2 GB would mean the mmap patch regressed — but
  `assert_mmap()` should have refused to start at all.
- **`$8.00` per-dir `SPEND_CAP`** is the backstop; a dir that trips it raises and loses that dir.

### Step 4 — the dose gate (~$8.6). Off the critical path; may run during steps 2–3

```bash
cat > /Users/neeldankar/Desktop/gepa-project/analysis/state_dep/APPROVED-dose <<'EOF'
APPROVED-dose — Neel, 2026-08-03
Design v2.2 §11-0. Re-derive ALL SIX candidates' feedback per event from ONE fresh
execution (235 x 6 = 1410 metric calls), preceded by the within-session
reproducibility control (30 events x 6 x 2 passes = 360 calls).
Estimated ~$8.6 total, repriced from v2.1's $3.61: twice the candidates, and the
smoke measured §8b at $0.006121/call against the $0.004543 fit that line used.
Caps: $2.50 in dose_control.py, $11.00 in dose_compute.py.
Supersedes v2.1's 90/90 byte-exact determinism bar, which could only ever have
returned STOP — three same-venv temp-0 re-executions on disk agree 15/24.
Control bar: |D_30(pass1) - D_30(pass2)| <= mean(D_30). Fail -> DROP the dose,
never the biased 3-candidate shrink.
EOF
```

Then, in this order — the second command **refuses** without the marker the first writes:

```bash
cd /Users/neeldankar/Desktop/gepa-project
PY=analysis/state_dep/.venv-armT/bin/python

# 4a. reproducibility control, ~$2.0 (cap $2.50), ~15 min.
#     Writes markers/DOSE_CONTROL.PASS only if the bar clears.
$PY analysis/state_dep/dose_control.py --run

# 4b. the dose itself, ~$7.6 (cap $11.00), ~1 h. Refuses without 4a's marker.
$PY analysis/state_dep/dose_compute.py --live
```

Both are launched under `.venv-armT`; each spawns its own acquisition subprocess under
`scratch/hover_probe/.venv` (the swap's venv) and does the novelty scoring back under armT. Both
checkpoint per event — a crash costs one event, and re-running resumes at $0.

**If 4a fails, stop.** The pre-registered response is to drop the dose; `results.md` then carries
the estimation-only framing. Do not retune the bar after seeing the numbers.

### Step 5 — the backfill gate ($27.49). Must clear before `results.md` is read

```bash
cat > /Users/neeldankar/Desktop/gepa-project/analysis/state_dep/APPROVED-backfill <<'EOF'
APPROVED-backfill — Neel, 2026-08-03
Re-select all 97 Stage-1 candidates under the §8b estimator: 97 x 50 selection
evaluations, then the 8 per-seed winners x 150 test evaluations.
97 is a realized count (backfill_stage1.py --resolve), not an estimate:
11, 11, 13, 11, 14, 10, 13, 14.
Estimated $27.49; hard cap $32.00 in backfill_stage1.py.
Feeds the MDE and the §11-2 framing label, which must be on disk BEFORE
results.md is read.
EOF
```

```bash
$PY analysis/state_dep/backfill_stage1.py --run
```

### Step 6 — MDE and the framing label, then `results.md`

```bash
# D comes from step 4b's output; omit --dose if the dose was dropped.
$PY analysis/state_dep/mde_sim.py \
    --endpoints analysis/state_dep/stage1_backfill_endpoints.json \
    --dose <D>
```

Write the MDE, the framing label (confirmatory vs estimation-only) and `mde_sim.py`'s sha256 into
§2 **before** `results.md` is read (v2.1 §11-2). That ordering is the whole point of §11-2 and is
not enforced by any script.

### Cost ledger

| gate | amount | status |
|---|---|---|
| `APPROVED-testsplit` | $3.2336 | **spent** |
| `APPROVED-smoke` | $5.1942 | **spent** |
| `APPROVED-liverun` | ~$136.03 (cap $160, raised §0.1) | step 1 |
| `APPROVED-dose` | ~$8.6 (caps $2.50 / $11.00) | step 4 |
| `APPROVED-backfill` | $27.49 (cap $32.00) | step 5 |
| **program** | **~$180.35** | inside the ~$160–195 band |
