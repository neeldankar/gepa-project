"""Batch-swap v2 — Stage 2 pre-registered analysis ($0; reads calls.csv + pairing.csv).

Estimands (draw-averaged margins; margin = child - P_B baseline, summed over the 3 gated examples):
  SPECIFICITY_B  = margin(R_B on B)  - margin(R_Bp on B)     (both gated on B  -> P_B cancels)
  SPECIFICITY_Bp = margin(R_Bp on Bp)- margin(R_B on Bp)     (symmetric replication)
  pooled specificity = mean of the two ; pooled transfer = mean(margin(R_B on Bp), margin(R_Bp on B))
Inference: within-run sign-flip permutation (>=20k) AND run-level cluster bootstrap; 95% CIs (report both).
Overlap decomposition, failure-count sensitivity, lottery (draw disagreement), independent 2nd-path recompute.
Numbers + CIs are computed FIRST; the conditional interpretation cell is selected from the realized numbers.

  HF_DATASETS_OFFLINE=1 .venv/bin/python scripts/batch_swap_v2_analysis.py
"""
from __future__ import annotations

import collections
import csv

import numpy as np

OUT = "analysis/ablation/batch_swap_v2"
NPERM, NBOOT = 20000, 20000
MDE_SPEC = {2: 0.040, 3: 0.033}   # pooled-specificity MDE at rho=0 (Stage 0); realized CI is the arbiter
rng = np.random.default_rng(20260703)


def draw_avg(rows, arm, field):
    v = [float(r[field]) for r in rows if r["arm"] == arm]
    return float(np.mean(v)) if v else np.nan


def perm_p(x):
    """Within-pair sign-flip permutation two-sided p for H0 mean=0."""
    x = np.asarray(x); obs = x.mean()
    null = np.array([(x * rng.choice([-1.0, 1.0], len(x))).mean() for _ in range(NPERM)])
    return obs, float((np.abs(null) >= abs(obs) - 1e-12).mean())


def cluster_boot(x, clusters):
    """Run-level cluster bootstrap 95% CI (resample whole runs with replacement)."""
    x = np.asarray(x); clusters = np.asarray(clusters)
    uniq = np.unique(clusters); by = {c: x[clusters == c] for c in uniq}
    means = []
    for _ in range(NBOOT):
        pick = rng.choice(uniq, len(uniq), replace=True)
        means.append(np.concatenate([by[c] for c in pick]).mean())
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def main():
    calls = list(csv.DictReader(open(f"{OUT}/calls.csv")))
    pairmeta = {r["B_id"]: r for r in csv.DictReader(open(f"{OUT}/pairing.csv"))}
    by_pair = collections.defaultdict(list)
    for r in calls:
        by_pair[r["B_id"]].append(r)
    K = max(sum(1 for r in rs if r["arm"] == "R_B") for rs in by_pair.values())
    print(f"pairs={len(by_pair)}  draws/arm K={K}")

    spec, transf, jac, bpfail, clusters, pids = [], [], [], [], [], []
    lot_disagree = []
    for pid, rs in by_pair.items():
        mB_RB = draw_avg(rs, "R_B", "margin_on_B")
        mB_RBp = draw_avg(rs, "R_Bp", "margin_on_B")
        mBp_RB = draw_avg(rs, "R_B", "margin_on_Bp")
        mBp_RBp = draw_avg(rs, "R_Bp", "margin_on_Bp")
        if np.any(np.isnan([mB_RB, mB_RBp, mBp_RB, mBp_RBp])):
            continue
        spec.append(((mB_RB - mB_RBp) + (mBp_RBp - mBp_RB)) / 2)   # pooled specificity
        transf.append((mBp_RB + mB_RBp) / 2)                       # pooled transfer
        jac.append(float(pairmeta[pid]["type_jaccard"]))
        bpfail.append(int(pairmeta[pid]["Bprime_fail_underPB"]))
        clusters.append(int(pairmeta[pid]["seed"]))
        pids.append(pid)
        # lottery: within-arm accept (margin_on_B>0) disagreement across draws
        for arm in ("R_B", "R_Bp"):
            acc = [float(r["margin_on_B"]) > 0 for r in rs if r["arm"] == arm]
            if len(acc) >= 2:
                lot_disagree.append(0 if len(set(acc)) == 1 else 1)

    spec, transf = np.array(spec), np.array(transf)
    clusters = np.array(clusters)
    mde = MDE_SPEC.get(K, 0.033)

    def report(name, x):
        obs, p = perm_p(x)
        lo, hi = cluster_boot(x, clusters)
        nlo, nhi = np.percentile([np.mean(rng.choice(x, len(x))) for _ in range(NBOOT)], [2.5, 97.5])
        print(f"\n== {name} ==")
        print(f"  point={obs:+.4f}  perm p={p:.4f}")
        print(f"  95% CI: cluster-boot(run)=[{lo:+.4f},{hi:+.4f}]  naive-pair=[{nlo:+.4f},{nhi:+.4f}]")
        return dict(point=obs, p=p, clo=lo, chi=hi, nlo=nlo, nhi=nhi)

    S = report("POOLED SPECIFICITY", spec)
    T = report("POOLED TRANSFER", transf)

    # overlap decomposition: specificity ~ type_jaccard (does specificity -> 0 as overlap -> 1?)
    jac = np.array(jac)
    A = np.vstack([np.ones_like(jac), jac]).T
    b0, b1 = np.linalg.lstsq(A, spec, rcond=None)[0]
    print(f"\n== OVERLAP DECOMPOSITION: specificity ~ jaccard ==")
    print(f"  intercept={b0:+.4f}  slope={b1:+.4f}  predicted@jac=1: {b0+b1:+.4f}")

    # failure-count sensitivity
    print(f"\n== FAILURE-COUNT SENSITIVITY (specificity by B' fail count under P_B) ==")
    for fc in sorted(set(bpfail)):
        m = spec[np.array(bpfail) == fc]
        print(f"  B'_fail={fc}: n={len(m)}  mean specificity={m.mean():+.4f}")

    # lottery
    dis = np.mean(lot_disagree) if lot_disagree else float("nan")
    print(f"\n== LOTTERY: within-arm accept disagreement across draws = {dis:.3f}  (n={len(lot_disagree)}) ==")

    # independent 2nd-path recompute
    import pandas as pd
    df = pd.DataFrame(calls).astype({"margin_on_B": float, "margin_on_Bp": float})
    piv = df.groupby(["B_id", "arm"])[["margin_on_B", "margin_on_Bp"]].mean().reset_index()
    def g(pid, arm, col):
        s = piv[(piv.B_id == pid) & (piv.arm == arm)][col]
        return s.iloc[0] if len(s) else np.nan
    spec2 = [(((g(p, "R_B", "margin_on_B") - g(p, "R_Bp", "margin_on_B")) +
               (g(p, "R_Bp", "margin_on_Bp") - g(p, "R_B", "margin_on_Bp"))) / 2) for p in pids]
    match = abs(np.nanmean(spec2) - S["point"]) < 1e-9
    print(f"\n== INDEPENDENT 2nd-path recompute: pooled specificity {np.nanmean(spec2):+.4f} "
          f"(matches: {match}) ==")

    # ---- write results.md: numbers first, THEN select the conditional interpretation cell ----
    def verdict(est, mdeb):
        return "positive" if est["clo"] > 0 else ("negative" if est["chi"] < 0 else f"≈0 (within MDE {mdeb})")
    sv, tv = verdict(S, mde), verdict(T, mde)
    if S["clo"] > 0 and not T["clo"] > 0:
        cell = ("specificity>0 AND transfer≈0 → reflection overfits the minibatch; the gate certifies "
                "teach-to-the-test → feeds the gate-pivot direction.")
    elif (S["clo"] > 0) and (T["clo"] > 0) and abs(T["point"]) >= 0.5 * abs(S["point"]):
        cell = ("transfer≈specificity>0 → revisions generalize; example choice adds little beyond seeing "
                "some failures → selection null reinforced at causal grain.")
    elif (not S["clo"] > 0) and (not T["clo"] > 0) and S["chi"] < mde and T["chi"] < mde:
        cell = ("both≈0 → example channel inert even same-example → strongest Claim A.")
    elif S["clo"] > 0 and T["clo"] > 0:
        cell = (f"specificity>0 AND transfer>0 with specificity≫transfer → mixed; ratio "
                f"transfer/specificity={T['point']/S['point']:.2f}. No verdict language.")
    else:
        cell = "indeterminate at these CIs; report numbers only."

    with open(f"{OUT}/results.md", "w") as f:
        w = f.write
        w("# Batch-swap v2 — results (2×2 reflect × gate)\n\n")
        w(f"Pairs={len(spec)}, K={K} draws/arm. Numbers + CIs first; interpretation is conditional on them.\n\n")
        w("## Headline\n")
        w("| estimand | point | perm p | 95% CI (run cluster-boot) | 95% CI (naive-pair) | MDE bound |\n")
        w("|---|---|---|---|---|---|\n")
        w(f"| pooled SPECIFICITY | {S['point']:+.4f} | {S['p']:.4f} | [{S['clo']:+.4f},{S['chi']:+.4f}] "
          f"| [{S['nlo']:+.4f},{S['nhi']:+.4f}] | {mde} |\n")
        w(f"| pooled TRANSFER | {T['point']:+.4f} | {T['p']:.4f} | [{T['clo']:+.4f},{T['chi']:+.4f}] "
          f"| [{T['nlo']:+.4f},{T['nhi']:+.4f}] | (single margin; wider) |\n\n")
        w(f"Specificity verdict: **{sv}**. Transfer verdict: **{tv}**.\n\n")
        w(f"## Overlap decomposition\nspecificity ~ jaccard: intercept {b0:+.4f}, slope {b1:+.4f}, "
          f"predicted@overlap=1 → {b0+b1:+.4f} "
          f"({'→0: type-level channel' if abs(b0+b1) < mde else 'stays >0: example-level'}).\n\n")
        w(f"## Lottery\nwithin-arm accept disagreement across draws = {dis:.3f} "
          f"(higher-n check of the prior 0.32).\n\n")
        w(f"## Interpretation (selected from realized numbers)\n{cell}\n\n")
        w("Scope: one-step gate ≠ downstream U; IFBench verifiable-SI regime only. Every cell above carries "
          "its MDE/CI; the run-cluster CI is the honest arbiter over the permutation p.\n")
    print(f"\n[wrote {OUT}/results.md]  spec verdict={sv} | transfer verdict={tv}")


if __name__ == "__main__":
    main()
