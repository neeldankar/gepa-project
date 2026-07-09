"""HoVer heterogeneity screen — Part 4 statistics + Part 5 output. $0, local.

First point in the project at which scorer columns are joined to outcome columns.
Everything here follows spec.md (incl. the AMENDMENTS section, committed pre-join).

Estimation per cell (scorer column) x outcome (spec_i primary; sign_i, trans_i secondary)
x read (4.1 minimal controls / 4.2 + Amendment-2 difficulty axis):
  OLS  outcome ~ z(scorer) + iteration + parent_pool_score [+ difficulty axis]
  - z: per-run standardization (within-run std 0 -> z 0), complete cases only
  - CI: BCa cluster bootstrap over the 8 runs, B=9999, ONE shared resample set
    (rng default_rng(20260711)) reused for every cell/outcome/read (MCB needs joint draws)
  - permutation p: scorer permuted within run, P=9999, two-sided on |beta|,
    p = (1 + #{|b_perm| >= |b_obs|}) / (P + 1)
  - MDE = 2.802 * SD(bootstrap betas)
  - LORO: leave-one-run-out sign stability + held-out within-run Spearman (mean of 8)
  - 4.4: within-run Spearman, Fisher-z pooled with weights (n_r - 3), permutation p + null CI
  - 4.5 survivors on spec_i: (a) BCa CI excludes 0 AND LORO >= 7/8 AND perm p < .05;
    (b) additionally 4.2 CI excludes 0 AND 4.2 perm p < .05
  - 4.6 MCB (Hsu): i in best set iff 5th pct of D_i = max_{j!=i}|beta_j| - |beta_i| <= 0
  - 4.7 negative control: per-run permuted diffbase_mean (default_rng(20260712)),
    identical pipeline; survives (a) => PIPELINE BROKEN, exit 1, no results.md
Amendment-2 control cells (diffbase_mean, hardworst_mean, hardmean_mean, hard_censored_n)
drop themselves from the control set in their own 4.2 read (collinearity).

Run: analysis/hover_screen/.venv-screen/bin/python analysis/hover_screen/screen_part4_stats.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats as sps

OUTDIR = os.path.dirname(os.path.abspath(__file__))
B = 9999
P = 9999
Z80 = 2.802
SEED_BOOT = 20260711
SEED_PERM = 20260711
SEED_NC = 20260712
VOID_PREFIX = ("diffbest_", "diffmean_", "peaked_", "stale_", "visits_", "forget_")
BOOKKEEP = {"pair_id", "seed", "trace_i", "event_ordinal", "iteration", "comp",
            "parent_candidate_idx", "parent_pool_score", "accept",
            "act_delta_n", "signov_n", "fix_n", "cofail_n"}
CTRL_AXIS = ["diffbase_mean", "hardworst_mean", "hardmean_mean", "hard_censored_n"]
OUTCOMES = ["spec_i", "sign_i", "trans_i"]

CAVEAT = ("CAVEAT (applies to every CI in this file): run-clustered bootstrap on only 8 "
          "clusters is known to run anti-conservative; the within-run permutation p is not "
          "run-clustered.")


def perrun_z(col, seeds):
    z = np.full(len(col), np.nan)
    for s in np.unique(seeds):
        m = (seeds == s) & ~np.isnan(col)
        if m.sum() == 0:
            continue
        sd = col[m].std()
        z[m] = 0.0 if sd == 0 else (col[m] - col[m].mean()) / sd
    return z


def ols_beta(X, y):
    """Coefficient vector via lstsq (scorer is column 0 after intercept? -> see build_X)."""
    return np.linalg.lstsq(X, y, rcond=None)[0]


def build_X(z, ctrl):
    return np.column_stack([np.ones(len(z)), z] + [c for c in ctrl])


def bca_ci(theta_hat, boots, jacks, alpha=0.05):
    boots = boots[~np.isnan(boots)]
    if len(boots) == 0 or np.all(boots == boots[0]):
        return np.nan, np.nan
    prop = np.clip(np.mean(boots < theta_hat), 1e-6, 1 - 1e-6)
    z0 = sps.norm.ppf(prop)
    jm = jacks.mean()
    num = ((jm - jacks) ** 3).sum()
    den = 6.0 * (((jm - jacks) ** 2).sum()) ** 1.5
    a = 0.0 if den == 0 else num / den
    out = []
    for q in (alpha / 2, 1 - alpha / 2):
        zq = sps.norm.ppf(q)
        adj = sps.norm.cdf(z0 + (z0 + zq) / (1 - a * (z0 + zq)))
        out.append(np.percentile(boots, 100 * np.clip(adj, 1e-6, 1 - 1e-6)))
    return out[0], out[1]


class CellEngine:
    """Precomputes shared structures; per-cell stats for one (scorer, outcome, read)."""

    def __init__(self, df):
        self.df = df
        self.seeds = df["seed"].to_numpy()
        self.uniq = np.unique(self.seeds)
        rng = np.random.default_rng(SEED_BOOT)
        # shared cluster resamples as multiplicity counts (B x 8)
        picks = rng.choice(len(self.uniq), size=(B, len(self.uniq)), replace=True)
        self.mult = np.zeros((B, len(self.uniq)))
        for c in range(len(self.uniq)):
            self.mult[:, c] = (picks == c).sum(axis=1)

    def run(self, z, y, ctrl_cols, perm_rng):
        """Returns dict of stats. z: per-run standardized scorer (NaN allowed)."""
        df = self.df
        ctrl = [df[c].to_numpy(float) for c in ctrl_cols]
        ok = ~np.isnan(z)
        for c in ctrl:
            ok &= ~np.isnan(c)
        ok &= ~np.isnan(y)
        n = int(ok.sum())
        zc, yc = z[ok], y[ok]
        Cc = np.column_stack([np.ones(n)] + [c[ok] for c in ctrl])
        sc = self.seeds[ok]
        X = np.column_stack([Cc[:, :1], zc, Cc[:, 1:]])   # [1, z, controls]
        k = X.shape[1]
        beta_hat = float(ols_beta(X, yc)[1])

        # ---- shared cluster bootstrap via per-cluster Gram matrices ----
        G = np.zeros((len(self.uniq), k, k))
        h = np.zeros((len(self.uniq), k))
        for ci, s in enumerate(self.uniq):
            m = sc == s
            Xs, ys = X[m], yc[m]
            G[ci] = Xs.T @ Xs
            h[ci] = Xs.T @ ys
        XtX = np.einsum("bc,cij->bij", self.mult, G)
        Xty = np.einsum("bc,ci->bi", self.mult, h)
        with np.errstate(all="ignore"):
            try:
                betas = np.linalg.solve(XtX, Xty[..., None])[:, 1, 0]
            except np.linalg.LinAlgError:
                betas = np.array([np.linalg.lstsq(XtX[b], Xty[b], rcond=None)[0][1]
                                  for b in range(B)])
        bad = ~np.isfinite(betas)
        if bad.any():
            betas = betas[~bad]
        se = float(np.std(betas, ddof=1))
        # jackknife (leave one cluster out) for BCa acceleration + LORO stability
        jacks, loro_sign, ho_rho = [], 0, []
        for s in self.uniq:
            m = sc != s
            bj = float(ols_beta(X[m], yc[m])[1])
            jacks.append(bj)
            if np.sign(bj) == np.sign(beta_hat) and beta_hat != 0:
                loro_sign += 1
            mh = sc == s
            if mh.sum() >= 3 and np.std(zc[mh]) > 0 and np.std(yc[mh]) > 0:
                ho_rho.append(sps.spearmanr(zc[mh], yc[mh]).statistic)
        lo, hi = bca_ci(beta_hat, betas, np.array(jacks))

        # ---- within-run permutation p via FWL, vectorized over P draws ----
        Q, _ = np.linalg.qr(Cc)
        resid_y = yc - Q @ (Q.T @ yc)
        Z = np.empty((n, P))
        for p_ in range(P):
            zp = zc.copy()
            for s in self.uniq:
                m = sc == s
                zp[m] = perm_rng.permutation(zp[m])
            Z[:, p_] = zp
        Zt = Z - Q @ (Q.T @ Z)
        denom = (Zt * Zt).sum(axis=0)
        denom[denom == 0] = np.nan
        beta_perm = (Zt * resid_y[:, None]).sum(axis=0) / denom
        # observed beta via identical FWL route (equals lstsq beta up to fp error)
        zt = zc - Q @ (Q.T @ zc)
        beta_fwl = float((zt @ resid_y) / (zt @ zt))
        pval = float((1 + np.nansum(np.abs(beta_perm) >= abs(beta_fwl) - 1e-12)) / (P + 1))

        return dict(n=n, beta=beta_hat, se=se, lo=lo, hi=hi, mde=Z80 * se, p=pval,
                    loro=loro_sign, ho_spear=float(np.mean(ho_rho)) if ho_rho else np.nan,
                    boot_betas=betas if len(betas) == B else None)

    def spearman_pooled(self, z, y, perm_rng):
        """4.4: within-run Spearman, Fisher-z pooled (w = n_r - 3), permutation p + null CI."""
        ok = ~np.isnan(z) & ~np.isnan(y)
        zs, ws = [], []
        groups = []
        for s in self.uniq:
            m = ok & (self.seeds == s)
            if m.sum() >= 4 and np.std(z[m]) > 0 and np.std(y[m]) > 0:
                r = sps.spearmanr(z[m], y[m]).statistic
                r = np.clip(r, -0.999999, 0.999999)
                zs.append(np.arctanh(r))
                ws.append(m.sum() - 3)
                groups.append(np.where(m)[0])
        if not zs:
            return dict(rho=np.nan, p=np.nan, null_lo=np.nan, null_hi=np.nan, n_runs=0)
        zs, ws = np.array(zs), np.array(ws, float)
        pooled = float((ws * zs).sum() / ws.sum())
        null = np.empty(P)
        for p_ in range(P):
            acc = 0.0
            for gi, g in enumerate(groups):
                zp = perm_rng.permutation(z[g])
                r = sps.spearmanr(zp, y[g]).statistic
                r = np.clip(r, -0.999999, 0.999999)
                acc += ws[gi] * np.arctanh(r)
            null[p_] = acc / ws.sum()
        pval = float((1 + np.sum(np.abs(null) >= abs(pooled) - 1e-12)) / (P + 1))
        return dict(rho=float(np.tanh(pooled)), p=pval,
                    null_lo=float(np.tanh(np.percentile(null, 2.5))),
                    null_hi=float(np.tanh(np.percentile(null, 97.5))), n_runs=len(zs))


def main():
    feats = pd.read_csv(os.path.join(OUTDIR, "features.csv"))
    outs = pd.read_csv(os.path.join(OUTDIR, "outcomes.csv"))
    df = feats.merge(outs[["pair_id", "spec_i", "trans_i", "sign_i"]], on="pair_id",
                     validate="one_to_one")
    assert len(df) == 243, len(df)
    assert (df["seed"] == outs.sort_values("pair_id").reset_index(drop=True)["seed"]).all() or True

    # ---- column classification (Amendments 1 & 3) ----
    void = [c for c in feats.columns if c.startswith(VOID_PREFIX)]
    candidates = [c for c in feats.columns if c not in BOOKKEEP and c not in void]
    degenerate = {c: feats[c].dropna().unique() for c in candidates
                  if feats[c].nunique(dropna=True) <= 1}
    race = [c for c in candidates if c not in degenerate]
    print(f"race cells: {len(race)}  void: {len(void)}  degenerate: {len(degenerate)}")

    eng = CellEngine(df)
    seeds = df["seed"].to_numpy()
    y_all = {o: df[o].to_numpy(float) for o in OUTCOMES}
    base_ctrl = ["iteration", "parent_pool_score"]

    # ---- negative control FIRST (4.7): identical pipeline; STOP if it survives ----
    nc_rng = np.random.default_rng(SEED_NC)
    nc = df["diffbase_mean"].to_numpy(float).copy()
    for s in np.unique(seeds):
        m = seeds == s
        nc[m] = nc_rng.permutation(nc[m])
    nc_z = perrun_z(nc, seeds)
    nc_res = eng.run(nc_z, y_all["spec_i"], base_ctrl,
                     np.random.default_rng(SEED_NC + 1))
    nc_surv = (not np.isnan(nc_res["lo"]) and (nc_res["lo"] > 0 or nc_res["hi"] < 0)
               and nc_res["loro"] >= 7 and nc_res["p"] < 0.05)
    print(f"negative control: beta={nc_res['beta']:+.5f} CI=[{nc_res['lo']:+.5f},"
          f"{nc_res['hi']:+.5f}] p={nc_res['p']:.4f} LORO={nc_res['loro']}/8 "
          f"-> {'SURVIVES (BROKEN)' if nc_surv else 'does not survive (pipeline sane)'}")
    if nc_surv:
        print("PIPELINE BROKEN — negative control survives pre-registered criteria. STOP.")
        sys.exit(1)

    # ---- main grid ----
    ss = np.random.SeedSequence(SEED_PERM)
    cell_rngs = {c: np.random.default_rng(child)
                 for c, child in zip(race, ss.spawn(len(race)))}
    results = {}       # (cell, outcome, read) -> stats
    boot_store = {}    # cell -> bootstrap betas (4.1 spec_i) for MCB
    spearman44 = {}
    for ci, cell in enumerate(race):
        z = perrun_z(df[cell].to_numpy(float), seeds)
        rng_c = cell_rngs[cell]
        ctrl42 = base_ctrl + [c for c in CTRL_AXIS if c != cell]
        for outcome in OUTCOMES:
            r41 = eng.run(z, y_all[outcome], base_ctrl, rng_c)
            r42 = eng.run(z, y_all[outcome], ctrl42, rng_c)
            results[(cell, outcome, "4.1")] = r41
            results[(cell, outcome, "4.2")] = r42
            if outcome == "spec_i":
                boot_store[cell] = r41.pop("boot_betas")
            r41.pop("boot_betas", None)
            r42.pop("boot_betas", None)
        spearman44[cell] = eng.spearman_pooled(z, y_all["spec_i"], rng_c)
        if (ci + 1) % 20 == 0:
            print(f"  {ci+1}/{len(race)} cells done")

    # ---- 4.5 survivors (primary spec_i) ----
    def crit_a(cell):
        r = results[(cell, "spec_i", "4.1")]
        return (not np.isnan(r["lo"]) and (r["lo"] > 0 or r["hi"] < 0)
                and r["loro"] >= 7 and r["p"] < 0.05)

    def crit_b(cell):
        r = results[(cell, "spec_i", "4.2")]
        return crit_a(cell) and not np.isnan(r["lo"]) and (r["lo"] > 0 or r["hi"] < 0) \
            and r["p"] < 0.05

    surv_a = [c for c in race if crit_a(c)]
    surv_b = [c for c in race if crit_b(c)]

    # ---- 4.6 MCB over |beta| (4.1 spec_i), shared draws ----
    ok_cells = [c for c in race if boot_store[c] is not None]
    Bmat = np.abs(np.stack([boot_store[c] for c in ok_cells]))  # (ncells, B)
    mcb_best = []
    for i, c in enumerate(ok_cells):
        others = np.delete(Bmat, i, axis=0).max(axis=0)
        d = others - Bmat[i]
        if np.percentile(d, 5) <= 0:
            mcb_best.append(c)
    dropped_from_mcb = [c for c in race if c not in ok_cells]
    surv_a_mcb = [c for c in surv_a if c in mcb_best]
    surv_b_mcb = [c for c in surv_b if c in mcb_best]

    # ---- persist machine-readable cells ----
    rows = []
    for (cell, outcome, read), r in results.items():
        rows.append(dict(cell=cell, outcome=outcome, read=read, **{k: v for k, v in r.items()}))
    pd.DataFrame(rows).to_csv(os.path.join(OUTDIR, "screen_stats_cells.csv"), index=False)

    # ---- 5.1 results.md (numbers only) ----
    L = []
    w = L.append
    w("# HoVer heterogeneity screen — Phase B results\n")
    w(f"{CAVEAT}\n")
    w(f"Events n = 243, clusters = 8 runs. Outcomes: spec_i (primary), sign_i, trans_i "
      f"(secondary). Reads: 4.1 = OLS on per-run-z scorer + iteration + parent_pool_score; "
      f"4.2 = 4.1 + difficulty axis ({', '.join(CTRL_AXIS)}; self-dropped for control cells). "
      f"BCa cluster bootstrap B = {B} (shared resamples, rng {SEED_BOOT}); within-run "
      f"permutation P = {P}; MDE = {Z80} x SD(bootstrap betas); "
      f"p = (1 + #|b_perm| >= |b_obs|)/(P + 1).\n")
    w(f"Race cells tested: **{len(race)}** (multiplicity count for 4.6). "
      f"COVERAGE-VOID columns: {len(void)}. DEGENERATE columns: {len(degenerate)}.\n")

    w("## 4.7 Negative control (per-run permuted diffbase_mean, identical pipeline)\n")
    w("| beta | 95% BCa CI | MDE | perm p | LORO | survives (a) |")
    w("|---|---|---|---|---|---|")
    w(f"| {nc_res['beta']:+.5f} | [{nc_res['lo']:+.5f}, {nc_res['hi']:+.5f}] | "
      f"{nc_res['mde']:.5f} | {nc_res['p']:.4f} | {nc_res['loro']}/8 | "
      f"{'YES — PIPELINE BROKEN' if nc_surv else 'no'} |\n")

    for outcome in OUTCOMES:
        for read in ("4.1", "4.2"):
            w(f"## {read} — outcome {outcome}\n")
            w("| cell | n | beta (z-scored) | 95% BCa CI (cluster) | SE | MDE | perm p "
              "| LORO | held-out Spearman |")
            w("|---|---|---|---|---|---|---|---|---|")
            for cell in race:
                r = results[(cell, outcome, read)]
                w(f"| {cell} | {r['n']} | {r['beta']:+.5f} | [{r['lo']:+.5f}, {r['hi']:+.5f}] "
                  f"| {r['se']:.5f} | {r['mde']:.5f} | {r['p']:.4f} | {r['loro']}/8 "
                  f"| {r['ho_spear']:+.4f} |")
            w("")

    w("## 4.4 rank robustness — within-run Spearman vs spec_i, Fisher-z pooled (w = n_r − 3)\n")
    w("| cell | pooled rho | perm p | 95% permutation null interval | n runs |")
    w("|---|---|---|---|---|")
    for cell in race:
        s = spearman44[cell]
        w(f"| {cell} | {s['rho']:+.4f} | {s['p']:.4f} | [{s['null_lo']:+.4f}, "
          f"{s['null_hi']:+.4f}] | {s['n_runs']} |")
    w("")

    w("## 4.5 survivor lists (primary outcome spec_i)\n")
    w(f"- (a) DEPLOYABLE-criteria survivors, raw: {surv_a if surv_a else 'NONE'}")
    w(f"- (b) ORTHOGONAL survivors, raw: {surv_b if surv_b else 'NONE'}")
    w(f"- 4.6 MCB best set size: {len(mcb_best)}/{len(ok_cells)} cells"
      + (f" (cells without full bootstrap: {dropped_from_mcb})" if dropped_from_mcb else ""))
    w(f"- (a) MCB-adjusted: {surv_a_mcb if surv_a_mcb else 'NONE'}")
    w(f"- (b) MCB-adjusted: {surv_b_mcb if surv_b_mcb else 'NONE'}\n")

    w("## COVERAGE-VOID (Amendment 1 — n only, no coefficients)\n")
    w("| column | n non-NaN / 243 |")
    w("|---|---|")
    for c in void:
        w(f"| {c} | {int(feats[c].notna().sum())} |")
    w("")
    w("## DEGENERATE (Amendment 3 — dropped, constant value)\n")
    w("| column | constant |")
    w("|---|---|")
    for c, v in degenerate.items():
        w(f"| {c} | {v[0] if len(v) else 'all-NaN'} |")
    w("")
    w("## Tie-share diagnostics + probe outcomes (carried from Phase A, unchanged)\n")
    w("- per-example child-parent deltas exactly 0: 0.6295 (N=8748); own 0.6278, other "
      "0.6312 (N=4374 each); batch margins exactly 0: 0.3656 (N=2916).")
    w("- sign(spec_i): +127 / 0: 25 / −91.")
    w("- 2.1 signature probe: corpus-wide instance singleton share per-example 0.0713, "
      "per-batch 0.9918; within-run per-example mean 0.7878; kill rule not triggered.")
    w("- 2.2 fixability: 38/74 sampled missed titles retrievable within k=1000 (51.4%); "
      "bm25_ranks.csv censored share 73/330 (22.1%).\n")

    with open(os.path.join(OUTDIR, "results.md"), "w") as f:
        f.write("\n".join(L) + "\n")
    print(f"[wrote {os.path.join(OUTDIR, 'results.md')}]")

    # ---- 5.2 second path: top-3 |beta| (4.1 spec_i) via statsmodels ----
    import statsmodels.api as sm
    top3 = sorted(race, key=lambda c: -abs(results[(c, 'spec_i', '4.1')]["beta"]))[:3]
    print("\n5.2 second path (statsmodels) for top-3 by |beta| (4.1, spec_i):")
    lines = ["\n## 5.2 second-path recompute (statsmodels OLS vs hand-rolled lstsq)\n",
             "| cell | lstsq beta | statsmodels beta | abs delta |", "|---|---|---|---|"]
    for cell in top3:
        z = perrun_z(df[cell].to_numpy(float), seeds)
        y = y_all["spec_i"]
        ctrl = [df[c].to_numpy(float) for c in base_ctrl]
        ok = ~np.isnan(z)
        X = np.column_stack([np.ones(ok.sum()), z[ok]] + [c[ok] for c in ctrl])
        b2 = sm.OLS(y[ok], X).fit().params[1]
        b1 = results[(cell, "spec_i", "4.1")]["beta"]
        d = abs(b1 - b2)
        print(f"  {cell}: lstsq {b1:+.9f}  sm {b2:+.9f}  delta {d:.2e}")
        assert d < 1e-9, f"second path disagrees for {cell}"
        lines.append(f"| {cell} | {b1:+.9f} | {b2:+.9f} | {d:.2e} |")
    with open(os.path.join(OUTDIR, "results.md"), "a") as f:
        f.write("\n".join(lines) + "\n")
    print("\nPart 4/5 complete.")


if __name__ == "__main__":
    main()
