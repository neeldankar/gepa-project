# Adjudication follow-up — three $0 analyses on the frozen IFBench corpus

**Date:** 2026-07-02 · **$0, read-only, no API calls** (frozen baseline logs 2026-06-26 untouched).
Script: `scripts/run_adjudication_followup.py`. Artifacts: `task1_sim_validation.csv`, `task1_icc.csv`,
`task2_pairs.csv`, `task3_ips.csv`. Standing discipline: n/power before every estimate; headline numbers
via an independent second code path; no number read as a verdict.

---

## Task 1 — Crossed random-effects ICC (replaces the retracted smeared ICC)

**Provenance/power.** 382 b3 batches, 150 distinct examples, **7.64 appearances/example (min 4, max 11,
zero appear-once)** → the variance components are well-identified (NOT the degenerate one-appearance
regime). Multiple-membership model `y_b = μ + c·(u_i+u_j+u_k) + ε_b`; headline parameterization **scaled
c=1/3**; ICC = σ_u²/(σ_u²+σ_ε²).

**Method + second path.** REML (headline) AND method-of-moments (centered quadratic forms) — they agree.
**Mandatory estimator validation on the REAL Z (PASSED):** at true ICC ∈ {0, 0.05, 0.15} (se=Var(ΔU),
200 sims each) REML recovers {**+0.041**, +0.085, +0.147}, MoM {+0.042, +0.084, +0.147} (max bias 0.041 ≤
0.05). **Critical reading:** the estimator has a **+0.04 null-floor at true-ICC=0** (variance-component
boundary bias) — real ICCs must be read against that floor.

**Result (REML, scaled; MoM in parens; parametric-bootstrap 95% CI):**

| outcome | crossed ICC | 95% CI | MoM | naive smeared ICC | vs null-floor (0.041) |
|---|---|---|---|---|---|
| **ΔU** (primary) | **0.000** | [0.000, 0.243] | 0.000 | −0.003 | **at/below floor → consistent with true 0** |
| accept (secondary) | **0.086** | [0.000, 0.334] | 0.075 | 0.009 | above floor (excess ~0.045) → weak real component |

**Reading.**
- **ΔU: the corrected number is STILL ≈ 0.** σ_u² collapses to the boundary; the point (0.000) sits *below*
  the estimator's +0.041 null-floor → strongly consistent with a true per-example ΔU ICC of 0. **The
  retraction's deflation concern does NOT rescue ΔU** — there was no per-example ΔU signal for the smearing
  to deflate (naive −0.003 and corrected 0.000 are both ≈0). Caveat: the CI upper is **0.24** — with 8 runs
  we cannot *rule out* an ICC as high as ~0.24; we can only say the point estimate is ~0.
- **accept: the deflation argument IS real here.** Naive 0.009 → corrected **0.086** (~9×), above the null-
  floor → weak evidence of a per-example *acceptance* component (in the adjudication's ~0.1–0.18 ballpark at
  point/upper). But the "signal above noise" is only ~0.045 and the CI reaches 0.
- **Net:** a selection scorer targeting **revision value (ΔU)** still has ≈no per-example target even after
  the smearing fix; one targeting **accept-probability** has a weak (~0.086, CI-wide) one. The unscaled c=1
  parameterization gives much smaller ICCs (ΔU 0.000, accept 0.010) — parameterization-sensitive, headline
  is scaled.

---

## Task 2 — Lag-1 autocorrelation of per-example outcomes

**Provenance/power FIRST.** Within (run, example), consecutive appearances → (ΔU_t, ΔU_{t+1}) pairs.
**121 pairs, but from only 3 runs** (seeds 4/5/6 with >50 cycles = >1 epoch; the five ≤42-cycle runs give
0 pairs each because epoch-shuffle gives each example ~1 appearance/run). 121 ≥ 80 so not auto-labeled
POWER-LIMITED, **but the signal lives in 3 runs — treat with care** and the null is run-aware.

**Method.** Pooled Pearson r; permutation null (within each run permute each example's appearance order,
1000 perms); robustness = residualize ΔU on iteration index. **Raw r stays primary** (what a bandit exploits).

**Result.** ΔU **raw r = +0.011**, perm-null band [−0.104, +0.228], **p = 0.90** (dead center of null).
accept r = +0.054 (p = 0.51). Residualized-on-iteration r = +0.031.

**Reading.** **No detectable lag-1 persistence** — an example's realized outcome at appearance t does not
predict its outcome at t+1. This is the statistic a bandit/decay resampler needs, and it is ≈0. **Caveats:**
(1) batch smearing attenuates this r the same way it deflated the ICC, so raw r is a *floor* (derived, not
measured); (2) the null band is wide (±~0.2) at 121 pairs / 3 runs, so this rules out only |r| ≳ 0.2 — it is
"no evidence of persistence," not "proven zero."

---

## Task 3 — IPS policy-value of a tractability-weighted sampler

**Provenance/propensity (documented).** Logging policy = `EpochShuffledBatchSampler` (uniform shuffle →
partition into consecutive b-blocks, deterministic). Under a uniform random partition the marginal
probability of any specific unordered triple being a co-sampled block is **identical across triples**
(exchangeability) ⇒ π_log ≡ constant ⇒ it cancels in SNIPS. **Approximation stated:** we use the marginal
per-batch propensity (ignoring within-epoch block-disjointness, which affects variance not the SNIPS point
estimate) and the shuffle *distribution*, not the seeded realization.

**Method.** Target = weighted sampling WITHOUT replacement, `w_i ∝ exp(β·z_i)`, `z_i` = standardized mean
per-example `constraint_tractability` (frozen per-event scores aggregated to a static per-example value —
NOT recomputed; static-vs-per-event aggregation is a caveat). π_target(triple) = exact sum over the 6
orderings. SNIPS; ESS=(Σw)²/Σw²; cluster bootstrap resampling the **8 runs**. **β=0 sanity PASSED:**
SNIPS=0.0040866 = uniform mean ΔU to |Δ|=9e-19 (no bug).

**Result** (uniform mean ΔU = 0.00409):

| β | SNIPS | Δ vs uniform | ESS | 95% CI (cluster-boot over runs) | usable? |
|---|---|---|---|---|---|
| 0.5 | +0.00458 | **+0.00049** (+12% rel) | **144** | [+0.0031, +0.0063] | yes |
| 1.0 | +0.00450 | +0.00042 | **13** | [+0.0016, +0.0076] | **UNUSABLE (ESS<30)** |
| 2.0 | +0.00146 | −0.00263 | **2** | [+0.0001, +0.0026] | **UNUSABLE (ESS<30)** |

**Reading.** Only **β=0.5 is evaluable** (ESS=144). It shows a **small positive one-step lift (+0.0005,
~+12% relative)**, but the CI **[0.0031, 0.0063] overlaps the uniform mean 0.0041 → not distinguishable
from uniform**. Stronger tilts (β≥1) collapse ESS (13, 2) → **UNUSABLE** — the logged uniform data cannot
evaluate an aggressive tractability sampler. **Scope caveat (verbatim):** this estimates the ONE-STEP
reward of the reweighted batch choice under the logged state distribution (parents, iterations); deploying
the sampler would shift future states — only a live run measures the trajectory effect.

---

## Bottom line for the adjudication
1. **ICC≈0 retracted → corrected crossed-RE ICC computed (validated estimator).** For **ΔU (revision
   value), the corrected ICC is still ≈0** (point below the +0.04 null-floor; the deflation did not hide a
   ΔU signal), CI upper 0.24. For **accept, deflation was real** (0.009→0.086) — a weak per-example
   acceptance component exists. So "no per-example target" **holds for revision-value ΔU** and is **softened
   for accept**.
2. **Lag-1 ≈ 0** (r=0.011, p=0.90; underpowered, 3 runs) → no evidence the resample/decay premise has a
   realized-outcome signal to exploit.
3. **IPS:** a mild tractability tilt (β=0.5) buys a small, non-significant one-step ΔU lift; aggressive
   tilts are unevaluable (ESS collapse). Free evidence says the sampler's one-step value is small-or-null.

**Everything is confirmatory-of-weak, not proof-of-zero:** the CIs (ICC ΔU [0,0.24], lag-1 ±0.2, IPS
overlaps uniform) are wide at 8 runs. The direction stays closed on the evidence, but the honest statement
is "no strong per-example / persistence / sampler signal detected," with the accept-ICC (0.086) the one
weak positive the corrected model surfaced.

---

# Adjudication follow-up — addendum (A1–A3)  ·  2026-07-02, $0 read-only

Three loose ends. Script: `scripts/run_adjudication_addendum.py`. Frozen corpora untouched.

## A1 — Run-count provenance (reconciles; no problem)
| run | b | cycles | b3 batches |
|---|---|---|---|
| seed0_b3 | 3 | 39 | 39 |
| seed1_b3 | 3 | 34 | 34 |
| seed2_b3 | 3 | 42 | 42 |
| seed3_b3 | 3 | 41 | 41 |
| seed4_b3 | 3 | 63 | 63 |
| seed5_b3 | 3 | 64 | 64 |
| seed6_b3 | 3 | 60 | 60 |
| seed7_b3 | 3 | 39 | 39 |
| seed0_b1 | 1 | 45 | 0 |
| seed1_b1 | 1 | 60 | 0 |
| **TOTAL** | | **487** | **382** |

**10 runs / 487 events / 382 b3 batches.** The "8 runs" in the main report = the 8 b3 runs, which
contribute **all** 382 b3 batches; the 2 b1 diagnostic runs contribute **0** b3 batches (the b=3 analyses
filter to b=3). Reconciliation is exactly the expected one — **no provenance problem.**

## A2 — Is the weak accept-ICC (0.086) just the difficulty channel?
Extended the crossed-RE **accept** model with per-example FIXED covariates entering through membership
(`y_b = μ + c·Σγ'x_i + c·Σv_i + ε_b`, c=1/3). Covariates x_i (frozen, aggregated — no feature recompute):
mean `constraint_tractability`, mean difficulty (1−before_score), constraint count, and 15
constraint-**type**-composition fractions. Estimator = REML with fixed effects profiled out; **sim
re-validation WITH covariates PASSED** (recovers residual ICC {0→+0.057, 0.05→+0.080, 0.15→+0.150}; max
bias 0.057) → **new null-floor ≈ 0.05–0.06.**

| model | per-example accept ICC (scaled c=1/3) | σ_v² | σ_ε² |
|---|---|---|---|
| no covariates | **+0.086** | 0.092 | 0.973 |
| residual after difficulty+constraint-id covariates | **+0.111**  (95% CI [0.000, 0.359]) | 0.122 | 0.974 |
| sim null-floor (true ICC=0, with covariates) | ≈ +0.05 | — | — |

**Verdict: the accept component SURVIVES the difficulty/constraint-id adjustment** — residual ICC +0.111
is above the ≈0.05 null-floor (and σ_v² rose while σ_ε² held, so this is not a denominator-shrink
artifact; the covariates did not absorb the per-example effect). **But it is a weak, underpowered
survive:** the 95% CI [0.000, 0.359] reaches the floor/zero at the lower end. So the honest statement is:
the per-example *acceptance* component is **not explained away by the difficulty channel** (it does not
collapse to the floor), but it remains small, binary-outcome (linear-VC approximation), and CI-wide.
This does not change the primary close — **ΔU (revision value) per-example ICC is still ≈0** (Task 1);
A2 concerns only the secondary *accept* outcome.

## A3 — Disattenuated lag-1 (DERIVED)
Raw lag-1 r(ΔU) = 0.011. Batch smearing dilutes each per-example outcome to ~1/3 own-signal (the same
~3× that deflated the naive ICC), attenuating the observed lag-1 ~3×. **DERIVED disattenuated r ≈
0.011 / (1/3) = 0.033** — < 0.1, so the one-line factor suffices; the "no exploitable persistence"
conclusion is unchanged. Caveat: with ΔU σ_u²≈0 (Task 1) there is essentially no per-example ΔU signal,
so this is a heuristic upper-ish adjustment, **not a measured correlation**.
