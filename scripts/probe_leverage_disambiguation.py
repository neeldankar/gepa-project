"""Probe — leverage disambiguation: cross-run STABILITY × difficulty-RESIDUAL (NOVELTY). Offline, $0.

Disambiguates the prior probe's heavy-tailed column leverage: is the high-leverage minority a live
ex-ante lever (STABLE across runs AND beyond difficulty) or explained away? Characterizes the
observed uniform-sampled matrix only — NOT a test of a non-uniform sampler. Never touches logs/phase2/.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from gepa_si.screen.corpus_io import load_corpus  # noqa: E402
from gepa_si.screen.fungibility import pool_matrix  # noqa: E402

RNG = np.random.default_rng(0)
N_PERM = 1000
TOPN = 15  # top decile of 150


def leverage(M: np.ndarray, center: bool):
    A = M - M.mean(axis=0, keepdims=True) if center else M
    U, S, Vt = np.linalg.svd(A, full_matrices=False)
    e = np.cumsum(S ** 2) / np.sum(S ** 2)
    k = int(np.searchsorted(e, 0.90) + 1)
    return (Vt[:k, :] ** 2).sum(axis=0), k


def icc1(L: np.ndarray) -> float:
    """One-way random ICC(1): groups = columns (examples), n raters = rows (runs)."""
    n_runs, n_ex = L.shape
    grand = L.mean()
    col_means = L.mean(axis=0)
    ms_between = n_runs * ((col_means - grand) ** 2).sum() / (n_ex - 1)
    ms_within = ((L - col_means[None, :]) ** 2).sum() / (n_ex * (n_runs - 1))
    return float((ms_between - ms_within) / (ms_between + (n_runs - 1) * ms_within))


def mean_pairwise_spearman(L):
    n = L.shape[0]
    cors = [spearmanr(L[i], L[j]).correlation for i in range(n) for j in range(i + 1, n)]
    return float(np.mean(cors)), float(np.std(cors)), cors


def mean_pairwise_jaccard(L, topn=TOPN):
    n = L.shape[0]
    tops = [set(np.argsort(L[i])[::-1][:topn]) for i in range(n)]
    js = [len(tops[i] & tops[j]) / len(tops[i] | tops[j]) for i in range(n) for j in range(i + 1, n)]
    return float(np.mean(js)), tops


def main():
    runs = load_corpus()
    val_ids = sorted(runs[0].valset_by_candidate[sorted(runs[0].valset_by_candidate)[0]].keys(), key=int)

    # ---------- STEP 0 ----------
    print("=== STEP 0 — INVENTORY ===")
    idsets = [set(r.valset_by_candidate[sorted(r.valset_by_candidate)[0]].keys()) for r in runs]
    shared = set.intersection(*idsets)
    print(f"  runs={len(runs)}  unique example_ids={len(set.union(*idsets))}  shared_across_all={len(shared)}")
    if len(shared) != 150:
        raise SystemExit(f"STOP: valset not shared (shared={len(shared)})")
    print("  150 valset ids SHARED across all runs -> cross-run comparison valid.")

    # build leverage long table (centered = prior method; uncentered = robustness)
    rows, Lc_list, Lu_list, ks = [], [], [], []
    for r in runs:
        M, idxs = pool_matrix(r)
        lc, k = leverage(M, center=True)
        lu, _ = leverage(M, center=False)
        Lc_list.append(lc); Lu_list.append(lu); ks.append(k)
        colmean = M.mean(axis=0); colvar = M.var(axis=0); peak = (M * (1 - M)).mean(axis=0)
        rid = f"seed{r.seed}_b{r.b}"
        for j, vid in enumerate(val_ids):
            rows.append({"run": rid, "example_id": int(vid), "leverage": lc[j], "leverage_unc": lu[j],
                         "c1_meanscore": colmean[j], "c2_meansq": colmean[j] ** 2,
                         "c3_var": colvar[j], "c4_peak": peak[j]})
    df = pd.DataFrame(rows)
    Lc = np.array(Lc_list); Lu = np.array(Lu_list)
    print(f"  per-run k (90% energy): {ks}  -> M was COLUMN-CENTERED before SVD: leverage loads on "
          "cross-candidate SPREAD, not score LEVEL.")
    print("  difficulty controls (per valset example, across candidate axis of M): "
          "c1=mean score, c2=mean^2, c3=variance, c4=mean p(1-p). "
          "(Screen CONTROLS are batch-level, not per-example -> these are the faithful per-example analogs.)")
    print(f"  leverage long table rows: {len(df)} (expect 1500)")

    # sanity vs prior probe
    cv0 = Lc[0].std() / Lc[0].mean()
    print(f"  sanity: seed0_b3 centered leverage CV={cv0:.2f} (prior probe per-run CV ~1.3-1.6)")

    out = {}

    # ---------- PART 1 — STABILITY ----------
    print("\n=== PART 1 — STABILITY ===")
    rc_mean, rc_sd, _ = mean_pairwise_spearman(Lc)
    jac_mean, tops = mean_pairwise_jaccard(Lc)
    icc = icc1(Lc)
    print(f"  a) mean pairwise Spearman = {rc_mean:.3f} (sd {rc_sd:.3f})")
    print(f"  b) ICC(1) = {icc:.3f}  (fraction of leverage variance that is between-example/stable)")
    # concordance: how many examples are top-decile in >=k runs
    topcount = np.zeros(150, int)
    for t in tops:
        for j in t:
            topcount[j] += 1
    conc = {k: int((topcount >= k).sum()) for k in range(2, 11)}
    print(f"  c) top-decile (top-15) mean pairwise Jaccard = {jac_mean:.3f}")
    print(f"     examples top-decile in >=k runs: {conc}")
    # null: permute example ids within each run
    null_rc = np.empty(N_PERM); null_jac = np.empty(N_PERM)
    for t in range(N_PERM):
        Lp = np.array([RNG.permutation(row) for row in Lc])
        null_rc[t] = mean_pairwise_spearman(Lp)[0]
        null_jac[t] = mean_pairwise_jaccard(Lp)[0]
    rc_pct = float((null_rc < rc_mean).mean() * 100)
    jac_pct = float((null_jac < jac_mean).mean() * 100)
    print(f"  d) NULL: rank-corr null mean {null_rc.mean():.3f} -> observed at {rc_pct:.0f}th pct; "
          f"Jaccard null mean {null_jac.mean():.3f} -> observed at {jac_pct:.0f}th pct")
    stable = rc_mean > 0.3 and rc_pct >= 99 and icc > 0.3
    print(f"  VERDICT 1: {'STABLE' if stable else 'RUN-SPECIFIC'}")
    out.update(stable=stable, rc_mean=rc_mean, rc_sd=rc_sd, icc=icc, jac_mean=jac_mean,
               rc_pct=rc_pct, jac_pct=jac_pct, conc=conc, topcount=topcount)

    # ---------- PART 2 — NOVELTY ----------
    print("\n=== PART 2 — NOVELTY vs DIFFICULTY (run fixed effects) ===")
    y = df["leverage"].to_numpy()
    run_dum = pd.get_dummies(df["run"], drop_first=True).to_numpy(dtype=float)

    def r2(X):
        X = np.column_stack([np.ones(len(y)), X])
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        resid = y - np.einsum("ij,j->i", X, beta)
        return 1 - resid.var() / y.var(), resid

    r2_fe, _ = r2(run_dum)
    r2_i, _ = r2(np.column_stack([run_dum, df.c1_meanscore, df.c2_meansq]))
    r2_ii, _ = r2(np.column_stack([run_dum, df.c1_meanscore, df.c2_meansq, df.c3_var]))
    r2_iii, resid = r2(np.column_stack([run_dum, df.c1_meanscore, df.c2_meansq, df.c3_var, df.c4_peak]))
    df["residual_leverage"] = resid
    print(f"  R² runFE only:                 {r2_fe:.3f}")
    print(f"  R² (i)  +mean quadratic:       {r2_i:.3f}  (Δ {r2_i-r2_fe:+.3f})")
    print(f"  R² (ii) +variance:             {r2_ii:.3f}  (Δ {r2_ii-r2_i:+.3f}  <- variance ≈ leverage def under centering)")
    print(f"  R² (iii)+peakedness:           {r2_iii:.3f}  (Δ {r2_iii-r2_ii:+.3f})")
    residual_r2 = 1 - r2_iii
    print(f"  RESIDUAL R² (unexplained) = {residual_r2:.3f}")
    beyond = residual_r2 > 0.10
    print(f"  VERDICT 2: {'BEYOND-DIFFICULTY' if beyond else 'DIFFICULTY-IN-DISGUISE'} "
          f"(residual R² {'>' if beyond else '≤'} 0.10)")
    out.update(r2_fe=r2_fe, r2_i=r2_i, r2_ii=r2_ii, r2_iii=r2_iii, residual_r2=residual_r2, beyond=beyond)

    # ---------- PART 3 — ACTIONABILITY (gated) ----------
    if stable:
        print("\n=== PART 3 — ACTIONABILITY (LORO AUC) ===")
        run_list = [f"seed{r.seed}_b{r.b}" for r in runs]
        resid_mat = df.pivot(index="run", columns="example_id", values="residual_leverage").loc[run_list].to_numpy()
        raw_aucs, res_aucs = [], []
        for h in range(len(runs)):
            others = [i for i in range(len(runs)) if i != h]
            for src, mat, store in [("raw", Lc, raw_aucs), ("res", resid_mat, res_aucs)]:
                pred = mat[others].mean(axis=0)
                lab = np.zeros(150, int)
                lab[np.argsort(mat[h])[::-1][:TOPN]] = 1
                store.append(roc_auc_score(lab, pred))
        raw_auc, res_auc = float(np.mean(raw_aucs)), float(np.mean(res_aucs))
        print(f"  LORO mean AUC — RAW leverage:      {raw_auc:.3f}  (ex-ante identifiable?)")
        print(f"  LORO mean AUC — RESIDUAL leverage: {res_auc:.3f}  (non-difficulty part identifiable?)")
        out.update(raw_auc=raw_auc, res_auc=res_auc)
    else:
        print("\n=== PART 3 skipped (RUN-SPECIFIC) ===")
        out.update(raw_auc=np.nan, res_auc=np.nan)

    _figures(df, Lc, out, runs)
    df.to_parquet("analysis/probe_leverage_disambiguation.parquet", index=False)
    _write_md(out)
    _append_state(out)
    print("\nwrote analysis/probe_leverage_disambiguation.{md,parquet} + 3 figures + PROJECT_STATE")


def _figures(df, Lc, out, runs):
    # 1c concordance bars
    fig, ax = plt.subplots(figsize=(7, 4))
    ks = list(range(2, 11)); vals = [out["conc"][k] for k in ks]
    ax.bar(ks, vals, color="#3b7")
    ax.set_xlabel("top-decile in ≥ k runs"); ax.set_ylabel("# examples")
    ax.set_title(f"Top-decile leverage concordance (Jaccard {out['jac_mean']:.2f}, {out['jac_pct']:.0f}th pct of null)")
    fig.tight_layout(); fig.savefig("analysis/fig_concordance.png", dpi=110); plt.close(fig)

    # 2 leverage vs mean-score scatter + quadratic, colored by run
    fig, ax = plt.subplots(figsize=(7.5, 5))
    runlist = df["run"].unique()
    cmap = plt.cm.tab10(np.linspace(0, 1, len(runlist)))
    for c, rid in zip(cmap, runlist):
        d = df[df.run == rid]
        ax.scatter(d.c1_meanscore, d.leverage, s=8, color=c, alpha=0.5)
    xs = np.linspace(df.c1_meanscore.min(), df.c1_meanscore.max(), 100)
    co = np.polyfit(df.c1_meanscore, df.leverage, 2)
    ax.plot(xs, np.polyval(co, xs), "k-", lw=2, label="pooled quadratic fit")
    ax.set_xlabel("mean candidate score on example (difficulty)"); ax.set_ylabel("leverage (centered)")
    ax.set_title(f"Leverage vs difficulty — residual R²={out['residual_r2']:.2f} "
                 f"({'BEYOND' if out['beyond'] else 'in-disguise'})")
    ax.legend(); fig.tight_layout(); fig.savefig("analysis/fig_leverage_vs_meanscore.png", dpi=110); plt.close(fig)

    # 3 LORO AUC
    if out["stable"]:
        fig, ax = plt.subplots(figsize=(5, 4))
        ax.bar(["raw", "residual"], [out["raw_auc"], out["res_auc"]], color=["#37b", "#b73"])
        ax.axhline(0.5, color="k", ls="--", lw=1)
        ax.set_ylim(0, 1); ax.set_ylabel("LORO mean AUC")
        ax.set_title("Ex-ante identifiability of leverage (LORO)")
        for i, v in enumerate([out["raw_auc"], out["res_auc"]]):
            ax.text(i, v + 0.02, f"{v:.2f}", ha="center")
        fig.tight_layout(); fig.savefig("analysis/fig_loro_auc.png", dpi=110); plt.close(fig)


def _cell(out):
    s = "STABLE" if out["stable"] else "RUN-SPECIFIC"
    b = "BEYOND-DIFFICULTY" if out["beyond"] else "DIFFICULTY-IN-DISGUISE"
    if out["stable"] and out["beyond"]:
        call = "LIVE LEVER (candidate ex-ante feature)"
    elif out["stable"] and not out["beyond"]:
        call = "EXPLAINED AWAY but ex-ante identifiable — stable, yet it IS difficulty (the prior null covers it)"
    elif not out["stable"]:
        call = "NOT A LEVER — run-specific noise"
    else:
        call = "PARTIAL"
    return s, b, call


def _write_md(out):
    s, b, call = _cell(out)
    L = ["# Probe — leverage disambiguation (stability × difficulty-residual)\n",
         "Offline, $0. Characterizes the OBSERVED uniform-sampled matrix only — STABLE+BEYOND would make "
         "leverage a CANDIDATE ex-ante feature, NOT proof a non-uniform sampler beats uniform (still a live test).\n",
         f"## Cell: **{s} × {b}** → {call}\n",
         "## Part 1 — stability",
         f"- Mean pairwise cross-run Spearman = **{out['rc_mean']:.3f}** (sd {out['rc_sd']:.3f}); "
         f"observed at **{out['rc_pct']:.0f}th pct** of the within-run permutation null.",
         f"- ICC(1) = **{out['icc']:.3f}** (between-example/stable fraction of leverage variance).",
         f"- Top-decile mean pairwise Jaccard = **{out['jac_mean']:.3f}** ({out['jac_pct']:.0f}th pct of null); "
         f"examples top-decile in ≥5 runs: {out['conc'][5]}, in ≥8 runs: {out['conc'][8]}.",
         f"- **Verdict: {s}.** The high-leverage set is {'the same examples across runs (intrinsic)' if out['stable'] else 'run-specific'}.\n",
         "## Part 2 — novelty vs difficulty (run fixed effects)",
         f"- Stagewise R²: runFE {out['r2_fe']:.2f} → +mean-quadratic {out['r2_i']:.2f} → +variance "
         f"**{out['r2_ii']:.2f}** → +peakedness {out['r2_iii']:.2f}.",
         f"- **Residual R² (unexplained) = {out['residual_r2']:.3f}** → **{b}**.",
         "- **Centering caveat:** leverage was computed on column-CENTERED M, so it loads on cross-candidate "
         "SPREAD; the variance control (stage ii) is therefore near-definitional — most of the explained "
         "variance is leverage's own spread, so 'difficulty-in-disguise' here means *leverage ≈ cross-candidate "
         "disagreement (the swingable-cell signal)*, which is a semantic, not purely empirical, identity.\n",
         "## Part 3 — actionability (LORO)"]
    if out["stable"]:
        L.append(f"- LORO mean AUC predicting held-out top-decile leverage from the other 9 runs: "
                 f"**raw {out['raw_auc']:.3f}**, **residual {out['res_auc']:.3f}**.")
        L.append(f"- Raw leverage is {'ex-ante identifiable' if out['raw_auc']>0.7 else 'weakly identifiable'}; "
                 f"the non-difficulty residual is {'also identifiable' if out['res_auc']>0.7 else 'NOT well identifiable' if out['res_auc']<0.6 else 'partly identifiable'}.")
    else:
        L.append("- Skipped (RUN-SPECIFIC).")
    L.append(f"\n## Bottom line\n**{s} × {b} → {call}.** "
             + ("Leverage is a stable, ex-ante-identifiable property of specific valset examples, but under "
                "the centered definition it is largely cross-candidate disagreement (difficulty-flavored); "
                "the genuinely NEW (non-difficulty) part is "
                + (f"identifiable (residual LORO AUC {out['res_auc']:.2f})" if out.get('res_auc', 0) > 0.65
                   else f"weak/not ex-ante identifiable (residual LORO AUC {out.get('res_auc', float('nan')):.2f})")
                + ". This is a candidate ex-ante feature to consider, NOT proof a sampler wins — that stays the live test."
                if out["stable"] else
                "Leverage does not replicate across runs, so it is not an identifiable selection target.")
             )
    with open("analysis/probe_leverage_disambiguation.md", "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


def _append_state(out):
    heading = "## Leverage disambiguation probe"
    s, b, call = _cell(out)
    block = "\n".join([
        f"{heading} (2026-06-30)",
        f"- Stability: mean cross-run Spearman {out['rc_mean']:.2f} ({out['rc_pct']:.0f}th pct of null), "
        f"ICC(1) {out['icc']:.2f}, top-decile Jaccard {out['jac_mean']:.2f} → **{s}**.",
        f"- Novelty: stagewise R² to {out['r2_iii']:.2f} (variance dominates under column-centering), "
        f"residual R² {out['residual_r2']:.2f} → **{b}**.",
        f"- Actionability (LORO AUC): raw {out.get('raw_auc', float('nan')):.2f}, "
        f"residual {out.get('res_auc', float('nan')):.2f}.",
        f"- Cell: **{s} × {b}** → {call}. Caveat: observed uniform corpus only; centered leverage ≈ "
        "cross-candidate spread, so 'difficulty' includes disagreement. NOT a sampler/gate test.\n",
    ])
    with open("analysis/PROJECT_STATE.md", encoding="utf-8") as fh:
        text = fh.read()
    idx = text.find(heading)
    text = (text[:idx].rstrip() + "\n") if idx != -1 else (text.rstrip() + "\n\n")
    with open("analysis/PROJECT_STATE.md", "w", encoding="utf-8") as fh:
        fh.write(text + block + "\n")


if __name__ == "__main__":
    main()
