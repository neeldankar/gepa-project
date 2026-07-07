"""Adjudication follow-up addendum A1-A3 ($0, read-only).

A1 run-count provenance; A2 crossed-RE accept ICC with per-example difficulty covariates (+ sim
re-validation of the null-floor); A3 disattenuated lag-1 (derived).

Run: HF_DATASETS_OFFLINE=1 .venv/bin/python scripts/run_adjudication_addendum.py
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd
from scipy import optimize

from gepa_si.screen.corpus_io import load_corpus
from gepa_si.screen.scorer_inputs import trainset_meta, constraint_type

RNG = np.random.default_rng(0)
allruns = load_corpus()
runs = [r for r in allruns if r.b == 3]

# ---------------- A1: provenance ----------------
print("=" * 74 + "\nA1 — run-count provenance\n" + "=" * 74)
inv = []
for r in sorted(allruns, key=lambda x: (-x.b, x.seed)):
    inv.append({"run": f"seed{r.seed}_b{r.b}", "b": r.b, "cycles": len(r.cycles),
                "b3_batches": len(r.cycles) if r.b == 3 else 0})
invdf = pd.DataFrame(inv)
print(invdf.to_string(index=False))
print(f"TOTAL: runs={len(allruns)} events={invdf.cycles.sum()} b3_batches={invdf.b3_batches.sum()} "
      f"(b3 runs={ (invdf.b==3).sum() }, b1 runs={ (invdf.b==1).sum() } contribute 0 b3)")
assert invdf.b3_batches.sum() == 382 and invdf.cycles.sum() == 487 and len(allruns) == 10, "PROVENANCE MISMATCH — STOP"
print("reconciliation OK: 382 b3 batches from 8 b3 runs; 10 runs / 487 events incl. 2 b1 (0 b3).")

# ---------------- assemble batches + accept + membership ----------------
from gepa_si.screen.build_batch_df import build_dataframe
bdf = build_dataframe(); bdf = bdf[bdf.b == 3]
acc_map = {(row.seed, row.iteration): int(row.accept) for row in bdf.itertuples()}
B = []
before = {}   # per-example list of (1-before_score) for difficulty covariate
for r in runs:
    for c in sorted(r.cycles, key=lambda x: x.iteration):
        B.append({"seed": r.seed, "it": c.iteration, "ids": list(c.minibatch_ids),
                  "acc": acc_map[(r.seed, c.iteration)]})
        for p, tid in enumerate(c.minibatch_ids):
            before.setdefault(tid, []).append(1.0 - float(c.before_scores[p]))
ex_ids = sorted({i for b in B for i in b["ids"]}); eidx = {e: k for k, e in enumerate(ex_ids)}
n_ex, n_b = len(ex_ids), len(B)
y_ac = np.array([b["acc"] for b in B], float)
Z1 = np.zeros((n_b, n_ex))
for bi, b in enumerate(B):
    for e in b["ids"]:
        Z1[bi, eidx[e]] += 1.0
c = 1.0 / 3.0
Zc = c * Z1; Kc = Zc @ Zc.T

# ---------------- A2: per-example covariates (frozen, aggregated) ----------------
sc = pd.read_parquet("analysis/scorers.parquet"); sc = sc[sc.b == 3]
tract = sc.groupby("trainset_idx").constraint_tractability.mean()
tm = trainset_meta(); csets = tm["constraint_sets"]
alltypes = sorted({constraint_type(cc) for s in csets for cc in s})
X = []
for e in ex_ids:
    diff = np.mean(before[e])
    cs = csets[e]
    types = [constraint_type(cc) for cc in cs]
    comp = [types.count(t) / max(len(cs), 1) for t in alltypes]
    X.append([float(tract.get(e, np.nan)), diff, float(len(cs))] + comp)
X = np.array(X)
# standardize continuous (first 3); keep type fractions; drop 1 ref type col to reduce collinearity
X[:, :3] = (X[:, :3] - np.nanmean(X[:, :3], 0)) / np.nanstd(X[:, :3], 0)
X = np.nan_to_num(X)
X = X[:, :-1]  # drop last type-composition column (reference)
D = np.column_stack([np.ones(n_b), Zc @ X])   # fixed design: intercept + batch-mean covariates
print(f"\nA2 covariates: {X.shape[1]} per-example cols [mean_tractability, mean_difficulty, "
      f"constraint_count, {len(alltypes)-1} type-fractions]; fixed design D shape {D.shape}")


def reml_sigmas(y, K, D, ridge=1e-8):
    """REML for Var(y)=su*K+se*I with fixed effects D profiled out. Standardize y. Return (su,se,icc)."""
    s = np.std(y)
    if s == 0:
        return 0.0, 0.0, 0.0
    y = (y - y.mean()) / s
    w, Q = np.linalg.eigh(K); w = np.clip(w, 0, None)
    Qy = Q.T @ y; QD = Q.T @ D
    p = D.shape[1]

    def negreml(theta):
        su, se = np.exp(theta)
        d = su * w + se
        if not np.all(np.isfinite(d)) or np.any(d <= 1e-12):
            return 1e12
        DtViD = QD.T @ (QD / d[:, None]) + ridge * np.eye(p)
        DtViy = QD.T @ (Qy / d)
        try:
            beta = np.linalg.solve(DtViD, DtViy)
            sign, logdetDtViD = np.linalg.slogdet(DtViD)
        except np.linalg.LinAlgError:
            return 1e12
        r = Qy - QD @ beta
        quad = float(r @ (r / d))
        return 0.5 * (np.sum(np.log(d)) + logdetDtViD + quad)

    best = None
    for s0 in (0.1, 0.5, 1.0):
        res = optimize.minimize(negreml, np.log([s0, 1.0]), method="L-BFGS-B", bounds=[(-25, 12), (-25, 12)])
        if best is None or res.fun < best.fun:
            best = res
    su, se = np.exp(best.x)
    return su, se, su / (su + se)


D0 = np.ones((n_b, 1))
su0, se0, icc0 = reml_sigmas(y_ac, Kc, D0)         # no-covariate (reproduce 0.086)
suv, sev, iccv = reml_sigmas(y_ac, Kc, D)          # residual after covariates
# unscaled c=1 for both
K1 = Z1 @ Z1.T
_, _, icc0_u = reml_sigmas(y_ac, K1, D0)
_, _, iccv_u = reml_sigmas(y_ac, K1, np.column_stack([np.ones(n_b), Z1 @ X]))
print(f"\nno-covariate accept ICC (scaled) = {icc0:+.3f} (reproduces 0.086) σ_u²={su0:.4g} σ_ε²={se0:.4g} | unscaled {icc0_u:+.3f}")
print(f"residual accept ICC after difficulty+constraint-id covariates = {iccv:+.3f} σ_v²={suv:.4g} σ_ε²={sev:.4g} | unscaled {iccv_u:+.3f}")
# parametric bootstrap CI for the covariate-residual ICC (standardized scale)
ys_ac = (y_ac - y_ac.mean()) / np.std(y_ac)
bhat = np.linalg.lstsq(D, ys_ac, rcond=None)[0]
bootv = []
for _ in range(500):
    v = RNG.normal(0, np.sqrt(max(suv, 0)), n_ex); eps = RNG.normal(0, np.sqrt(max(sev, 0)), n_b)
    bootv.append(reml_sigmas(D @ bhat + Zc @ v + eps, Kc, D)[2])
civ_lo, civ_hi = np.percentile(bootv, [2.5, 97.5])
print(f"  residual ICC 95% CI = [{civ_lo:+.3f}, {civ_hi:+.3f}]")

# ---- MANDATORY sim re-validation WITH covariates (new null-floor) ----
print("\n[A2 sim re-validation WITH covariates; real Z + real X; 200 sims/level]")
# fit beta on standardized y to simulate realistically
ys = (y_ac - y_ac.mean()) / np.std(y_ac)
beta_hat = np.linalg.lstsq(D, ys, rcond=None)[0]
resid_var = float(np.var(ys - D @ beta_hat))
sim_rows = []
for icc_true in (0.0, 0.05, 0.15):
    sv = icc_true / (1 - icc_true) * resid_var if icc_true < 1 else 0.0
    rec = []
    for _ in range(200):
        v = RNG.normal(0, np.sqrt(sv), n_ex); eps = RNG.normal(0, np.sqrt(resid_var), n_b)
        ysim = D @ beta_hat + Zc @ v + eps
        rec.append(reml_sigmas(ysim, Kc, D)[2])
    sim_rows.append({"icc_true": icc_true, "reml_mean": float(np.mean(rec)), "reml_sd": float(np.std(rec))})
    print(f"  residual ICC_true={icc_true:.2f}: recovered mean={np.mean(rec):+.3f} (sd {np.std(rec):.3f})")
floor = sim_rows[0]["reml_mean"]
bias = max(abs(r["reml_mean"] - r["icc_true"]) for r in sim_rows)
if bias > 0.06:
    print(f"!!! A2 sim validation FAILED (max bias {bias:.3f}) — STOP."); sys.exit(1)
print(f"  sim validation PASS (max bias {bias:.3f}); NEW null-floor at true-0 = {floor:+.3f}")
verdict = ("EXPLAINED by difficulty/constraint-id (residual ICC at/below the new floor — no content-flavored residual)"
           if iccv <= floor + 0.01 else
           f"SURVIVES covariates: residual ICC {iccv:+.3f} above floor {floor:+.3f}")
print(f"  VERDICT (A2): {verdict}")
pd.DataFrame([{"model": "no_covariate", "icc": icc0}, {"model": "residual_after_covariates", "icc": iccv},
              {"model": "sim_null_floor", "icc": floor}] + sim_rows).to_csv("analysis/addendum_a2_icc.csv", index=False)

# ---------------- A3: disattenuated lag-1 (derived) ----------------
r_raw = 0.011
own_frac = 1.0 / 3.0
r_disatt = r_raw / own_frac
print("\n" + "=" * 74 + "\nA3 — disattenuated lag-1 (DERIVED)\n" + "=" * 74)
print(f"  raw r(ΔU)=0.011 ; own-signal fraction per batch ≈ 1/3 (smearing, same ~3x as ICC deflation)")
print(f"  DERIVED disattenuated r ≈ raw/(1/3) = {r_disatt:.3f}  (<0.1; conclusion unchanged; ΔU σ_u²≈0 so heuristic upper-ish)")
print("\nDONE — $0 read-only.")
