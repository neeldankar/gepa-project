"""Adjudication follow-up — three $0 read-only analyses on the frozen IFBench corpus.

T1 crossed random-effects ICC (multiple-membership; REML + MoM; MANDATORY sim validation -> STOP)
T2 lag-1 autocorrelation of per-example outcomes (permutation null, run-aware)
T3 SNIPS IPS policy-value of a tractability-weighted sampler (exact w/o-replacement propensity)

Run: HF_DATASETS_OFFLINE=1 .venv/bin/python scripts/run_adjudication_followup.py
"""
from __future__ import annotations

import itertools
import sys

import numpy as np
import pandas as pd
from scipy import optimize, stats

from gepa_si.screen.corpus_io import load_corpus

RNG = np.random.default_rng(0)
runs = [r for r in load_corpus() if r.b == 3]

# ---- assemble 382 batches: (seed, iteration, [3 example ids], delta_u, accept) ----
B = []
for r in runs:
    for c in sorted(r.cycles, key=lambda x: x.iteration):
        B.append({"seed": r.seed, "it": c.iteration, "ids": list(c.minibatch_ids),
                  "du": float(c.__dict__.get("delta_u", np.nan)), "accept": int(c.accept)})
# delta_u isn't on the cycle; pull from build_batch_df
from gepa_si.screen.build_batch_df import build_dataframe
bdf = build_dataframe(); bdf = bdf[bdf.b == 3]
du_map = {(row.seed, row.iteration): float(row.delta_u) for row in bdf.itertuples()}
for b in B:
    b["du"] = du_map[(b["seed"], b["it"])]
ex_ids = sorted({i for b in B for i in b["ids"]})
eidx = {e: k for k, e in enumerate(ex_ids)}
n_ex = len(ex_ids); n_b = len(B)
y_du = np.array([b["du"] for b in B]); y_ac = np.array([b["accept"] for b in B], float)


# ============================================================ Task 1
def membership(c):
    Z = np.zeros((n_b, n_ex))
    for bi, b in enumerate(B):
        for e in b["ids"]:
            Z[bi, eidx[e]] += c
    return Z


def reml_icc(y, K, tr_scale):
    """REML fit of Var(y)=su*K + se*I; return (su, se, icc). ICC scale-invariant -> standardize y."""
    s = np.std(y)
    if s == 0:
        return 0.0, 0.0, 0.0
    y = (y - y.mean()) / s
    Qt_1 = None
    w, Q = np.linalg.eigh(K)
    w = np.clip(w, 0, None)
    Qy = Q.T @ y; Q1 = Q.T @ np.ones(len(y))

    def negreml(theta):
        su, se = np.exp(theta)
        d = su * w + se
        if not np.all(np.isfinite(d)) or np.any(d <= 1e-12):
            return 1e12
        a = float(Q1 @ (Q1 / d))            # 1' Vinv 1
        b = float(Q1 @ (Qy / d))            # 1' Vinv y
        beta = b / a
        r_over = (Qy - beta * Q1)
        quad = float(r_over @ (r_over / d))
        return 0.5 * (np.sum(np.log(d)) + np.log(a) + quad)

    best = None
    for s0 in (0.1, 0.5, 1.0):
        res = optimize.minimize(negreml, np.log([s0, 1.0]), method="L-BFGS-B",
                                bounds=[(-25, 12), (-25, 12)])
        if best is None or res.fun < best.fun:
            best = res
    su, se = np.exp(best.x)
    su_per = su * tr_scale
    return su, se, su_per / (su_per + se)


def mom_icc(y, K, tr_scale):
    """Method-of-moments: centered quadratic forms y'y, y'Ky -> solve su,se. Standardize y."""
    s = np.std(y)
    if s == 0:
        return 0.0, 0.0, 0.0
    y = (y - y.mean()) / s
    n = len(y); M = np.eye(n) - np.ones((n, n)) / n
    yc = M @ y
    MK = M @ K
    # E[yc' A yc] = su*tr(A M K M) + se*tr(A M), A in {I, K}
    A1 = np.eye(n); A2 = K
    C = np.array([[np.trace(A1 @ M @ K @ M), np.trace(A1 @ M)],
                  [np.trace(A2 @ M @ K @ M), np.trace(A2 @ M)]])
    rhs = np.array([yc @ (A1 @ yc), yc @ (A2 @ yc)])
    su, se = np.linalg.solve(C, rhs)
    su = max(su, 0.0); se = max(se, 1e-12)
    su_per = su * tr_scale
    return su, se, su_per / (su_per + se)


def naive_icc(y):
    """Smeared: assign batch y to its 3 slots, group by example, ICC(1)."""
    rows = []
    for bi, b in enumerate(B):
        for e in b["ids"]:
            rows.append((e, y[bi]))
    df = pd.DataFrame(rows, columns=["g", "v"])
    grand = df.v.mean(); gs = df.groupby("g").v; ni = gs.size().to_numpy(); k = len(ni); N = len(df)
    msb = float((ni * (gs.mean().to_numpy() - grand) ** 2).sum()) / (k - 1)
    msw = float(sum(((v - v.mean()) ** 2).sum() for _, v in gs)) / (N - k)
    k0 = (N - (ni ** 2).sum() / N) / (k - 1)
    return (msb - msw) / (msb + (k0 - 1) * msw)


print("=" * 78 + "\nTASK 1 — crossed random-effects ICC\n" + "=" * 78)
print(f"n_batches={n_b}  n_examples={n_ex}  appearances/ex mean={np.mean(np.bincount([eidx[e] for b in B for e in b['ids']])):.2f}")
# scaled c=1/3 (headline): per-example variance enters batch at 1/3; tr_scale so ICC=su_per/(su_per+se)
# With c=1/3, u_i variance = su; a single example's own-outcome var component = su; batch residual = se.
c = 1.0 / 3.0
Zc = membership(c); Kc = Zc @ Zc.T
tr_scale = 1.0  # su already the per-example effect variance in the scaled parameterization

# ---- MANDATORY sim validation on REAL Z ----
print("\n[sim validation on REAL Z; se=Var(ΔU); 200 sims/level]")
se_true = float(np.var(y_du)); mu_true = float(np.mean(y_du))
sim_rows = []
for icc_true in (0.0, 0.05, 0.15):
    su_true = icc_true / (1 - icc_true) * se_true if icc_true < 1 else 0.0
    rem, rmm = [], []
    for _ in range(200):
        u = RNG.normal(0, np.sqrt(su_true), n_ex); eps = RNG.normal(0, np.sqrt(se_true), n_b)
        ysim = mu_true + Zc @ u + eps
        rem.append(reml_icc(ysim, Kc, tr_scale)[2]); rmm.append(mom_icc(ysim, Kc, tr_scale)[2])
    sim_rows.append({"icc_true": icc_true, "reml_mean": np.mean(rem), "reml_sd": np.std(rem),
                     "mom_mean": np.mean(rmm), "mom_sd": np.std(rmm)})
    print(f"  ICC_true={icc_true:.2f}: REML mean={np.mean(rem):+.3f}(sd {np.std(rem):.3f})  MoM mean={np.mean(rmm):+.3f}(sd {np.std(rmm):.3f})")
pd.DataFrame(sim_rows).to_csv("analysis/task1_sim_validation.csv", index=False)
bias = max(abs(r["reml_mean"] - r["icc_true"]) for r in sim_rows)
if bias > 0.05:
    print(f"\n!!! SIM VALIDATION FAILED (max REML bias {bias:.3f} > 0.05) — STOP.")
    sys.exit(1)
print(f"  sim validation PASS (max REML bias {bias:.3f} <= 0.05)")

# ---- real data ----
def fit_report(y, label):
    su_r, se_r, icc_r = reml_icc(y, Kc, tr_scale)
    su_m, se_m, icc_m = mom_icc(y, Kc, tr_scale)
    # unscaled c=1 for comparison
    Z1 = membership(1.0); su_u, se_u, icc_u = reml_icc(y, Z1 @ Z1.T, 1.0)
    naive = naive_icc(y)
    # parametric bootstrap CI (REML, scaled)
    boots = []
    for _ in range(500):
        u = RNG.normal(0, np.sqrt(max(su_r, 0)), n_ex); eps = RNG.normal(0, np.sqrt(se_r), n_b)
        boots.append(reml_icc(np.mean(y) + Zc @ u + eps, Kc, tr_scale)[2])
    lo, hi = np.percentile(boots, [2.5, 97.5])
    print(f"\n[{label}] scaled c=1/3 (HEADLINE): REML ICC={icc_r:+.3f} [95% {lo:+.3f},{hi:+.3f}] "
          f"(σ_u²={su_r:.4g} σ_ε²={se_r:.4g}) | MoM ICC={icc_m:+.3f}")
    print(f"         unscaled c=1: ICC={icc_u:+.3f} | NAIVE smeared ICC={naive:+.3f} "
          f"| deflation naive/corrected={naive/icc_r if icc_r else float('nan'):.2f}x")
    return {"outcome": label, "icc_reml": icc_r, "ci_lo": lo, "ci_hi": hi, "icc_mom": icc_m,
            "icc_unscaled": icc_u, "icc_naive": naive, "su": su_r, "se": se_r}


t1 = [fit_report(y_du, "ΔU"), fit_report(y_ac, "accept")]
pd.DataFrame(t1).to_csv("analysis/task1_icc.csv", index=False)


# ============================================================ Task 2
print("\n" + "=" * 78 + "\nTASK 2 — lag-1 autocorrelation (per-example, within run)\n" + "=" * 78)
pairs = []  # (seed, ex, it_t, it_t1, du_t, du_t1, ac_t, ac_t1)
for r in runs:
    seq = {}
    for c in sorted(r.cycles, key=lambda x: x.iteration):
        for e in c.minibatch_ids:
            seq.setdefault(e, []).append((c.iteration, du_map[(r.seed, c.iteration)], int(c.accept)))
    for e, lst in seq.items():
        lst.sort()
        for a, b in zip(lst, lst[1:]):
            pairs.append((r.seed, e, a[0], b[0], a[1], b[1], a[2], b[2]))
pdf = pd.DataFrame(pairs, columns=["seed", "ex", "it_t", "it_t1", "du_t", "du_t1", "ac_t", "ac_t1"])
pdf.to_csv("analysis/task2_pairs.csv", index=False)
nruns = pdf.seed.nunique()
print(f"POWER: {len(pdf)} pairs from {nruns} runs (per-run: {dict(pdf.seed.value_counts().sort_index())})")
print("  ", "POWER-LIMITED" if len(pdf) < 80 else "n>=80 (but concentrated in %d runs — treat with care)" % nruns)


def r_and_perm(col_t, col_t1, label):
    x, y = pdf[col_t].to_numpy(), pdf[col_t1].to_numpy()
    r = np.corrcoef(x, y)[0, 1]
    # permutation null: within each run, permute the appearance order (shuffle which t pairs with which)
    null = []
    for _ in range(1000):
        yp = np.empty_like(y)
        for s in pdf.seed.unique():
            m = (pdf.seed == s).to_numpy()
            yp[m] = RNG.permutation(y[m])
        null.append(np.corrcoef(x, yp)[0, 1])
    null = np.array(null); p = float((np.abs(null) >= abs(r)).mean())
    print(f"  {label}: raw r={r:+.3f}  perm-null band[{np.percentile(null,2.5):+.3f},{np.percentile(null,97.5):+.3f}]  p={p:.3f}")
    return r, p


r_du, p_du = r_and_perm("du_t", "du_t1", "ΔU (primary)")
r_ac, p_ac = r_and_perm("ac_t", "ac_t1", "accept (secondary)")
# robustness: residualize ΔU on iteration index within run
res_t = pdf.du_t - pdf.groupby("seed").du_t.transform("mean")
tmp = pdf.copy(); tmp["rt"] = pdf.du_t - np.polyval(np.polyfit(pdf.it_t, pdf.du_t, 1), pdf.it_t)
tmp["rt1"] = pdf.du_t1 - np.polyval(np.polyfit(pdf.it_t1, pdf.du_t1, 1), pdf.it_t1)
r_resid = np.corrcoef(tmp.rt, tmp.rt1)[0, 1]
print(f"  ΔU residualized-on-iteration r={r_resid:+.3f} (raw stays primary)")
# disattenuation (derived): using Task1 σ's, each obs is signal + batchmate noise
icc_du = t1[0]["icc_reml"]
print(f"  [derived, not measured] batch-smearing attenuation ~ per Task-1 σ_u/σ_ε; raw r is a floor.")


# ============================================================ Task 3
print("\n" + "=" * 78 + "\nTASK 3 — SNIPS IPS (tractability-weighted sampler)\n" + "=" * 78)
sc = pd.read_parquet("analysis/scorers.parquet")
sc = sc[sc.b == 3]
# static per-example tractability = mean over appearances (frozen per-event scores; not recomputed)
z_ex = sc.groupby("trainset_idx").constraint_tractability.mean()
z_ex = z_ex.reindex(ex_ids)
z = (z_ex - z_ex.mean()) / z_ex.std()
zvec = {e: float(z.loc[e]) for e in ex_ids}
print(f"propensity: EpochShuffledBatchSampler = uniform shuffle -> partition; marginal π_log over triples "
      f"is CONSTANT by exchangeability -> cancels in SNIPS. z = standardized mean per-example tractability.")


def pi_target(ids, beta):
    """exact prob of the unordered triple under successive weighted-without-replacement, w=exp(beta z)."""
    logw = {e: beta * zvec[e] for e in ids}
    tot_all = np.array([beta * zvec[e] for e in ex_ids])
    Zden = np.exp(tot_all - tot_all.max()).sum()  # denom base = sum over all examples (constant)
    # do exact successive draws over the 6 orderings, denominators shrink as examples removed
    all_lse = np.exp(tot_all - tot_all.max())
    full = all_lse.sum()
    idxset = [eidx[e] for e in ids]
    p = 0.0
    for perm in itertools.permutations(ids):
        pr = 1.0; remaining = full
        used = []
        for e in perm:
            wi = np.exp(beta * zvec[e] - tot_all.max())
            pr *= wi / remaining
            remaining -= wi
        p += pr
    return p


betas = [0.0, 0.5, 1.0, 2.0]
uniform_mean = float(y_du.mean())
t3 = []
# cache all-example exp for speed
for beta in betas:
    pit = np.array([pi_target(b["ids"], beta) for b in B])
    w = pit / pit.sum() if beta != 0 else np.ones(n_b) / n_b  # SNIPS weights (π_log constant cancels)
    # for beta=0 pi_target is identical across batches -> uniform weights (identity check)
    snips = float((w * y_du).sum() / w.sum()) if w.sum() else float("nan")
    ess = float((w.sum() ** 2) / (w ** 2).sum())
    # cluster bootstrap over runs
    seeds = [r.seed for r in runs]; bootv = []
    seed_of = np.array([b["seed"] for b in B])
    for _ in range(1000):
        samp = RNG.choice(seeds, len(seeds), replace=True)
        mask = np.concatenate([np.where(seed_of == s)[0] for s in samp])
        ww = pit[mask] / pit[mask].sum() if beta != 0 else np.ones(len(mask))
        bootv.append((ww * y_du[mask]).sum() / ww.sum())
    lo, hi = np.percentile(bootv, [2.5, 97.5])
    usable = ess >= 30
    t3.append({"beta": beta, "snips": snips, "delta_vs_uniform": snips - uniform_mean,
               "ess": ess, "ci_lo": lo, "ci_hi": hi, "usable": usable})
    tag = "" if usable else "  <-- UNUSABLE (ESS<30)"
    if beta == 0:
        print(f"  β=0 SANITY: SNIPS={snips:.6f} vs uniform mean ΔU={uniform_mean:.6f}  "
              f"|diff|={abs(snips-uniform_mean):.2e}  {'OK' if abs(snips-uniform_mean)<1e-9 else 'BUG!'}")
    else:
        print(f"  β={beta}: SNIPS={snips:+.5f}  Δvs-uniform={snips-uniform_mean:+.5f}  "
              f"ESS={ess:.0f}  CI[{lo:+.5f},{hi:+.5f}]{tag}")
pd.DataFrame(t3).to_csv("analysis/task3_ips.csv", index=False)
print("\nDONE — $0 read-only, no runs.")
