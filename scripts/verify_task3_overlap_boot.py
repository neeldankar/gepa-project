"""Task 3 — overlap-decomposition verification ($0, reads calls.csv + pairing.csv).

Reproduces the harness OLS specificity ~ type_jaccard (batch_swap_v2_analysis.py:95-100),
then the run-cluster bootstrap of the slope and the extrapolated prediction@overlap=1, and the
type_jaccard support (max, mean). Reports MATCH/MISMATCH against the values in the brief's
replacement text. Also independently recomputes pooled specificity/transfer to confirm the
Task 3.2 definitions match the harness.

    HF_DATASETS_OFFLINE=1 .venv/bin/python scripts/verify_task3_overlap_boot.py
"""
from __future__ import annotations

import collections
import csv

import numpy as np

OUT = "analysis/ablation/batch_swap_v2"
NBOOT = 20000
rng = np.random.default_rng(20260703)  # same seed as harness analysis


def draw_avg(rows, arm, field):
    v = [float(r[field]) for r in rows if r["arm"] == arm]
    return float(np.mean(v)) if v else np.nan


def m(name, got, ref):
    v = "MATCH" if round(got, 4) == round(ref, 4) else "MISMATCH"
    print(f"  {name}: got={got:+.4f} ref={ref:+.4f} -> {v}")


def main():
    calls = list(csv.DictReader(open(f"{OUT}/calls.csv")))
    pairmeta = {r["B_id"]: r for r in csv.DictReader(open(f"{OUT}/pairing.csv"))}
    by_pair = collections.defaultdict(list)
    for r in calls:
        by_pair[r["B_id"]].append(r)

    spec, transf, jac, clusters = [], [], [], []
    for pid, rs in by_pair.items():
        mB_RB = draw_avg(rs, "R_B", "margin_on_B")
        mB_RBp = draw_avg(rs, "R_Bp", "margin_on_B")
        mBp_RB = draw_avg(rs, "R_B", "margin_on_Bp")
        mBp_RBp = draw_avg(rs, "R_Bp", "margin_on_Bp")
        if np.any(np.isnan([mB_RB, mB_RBp, mBp_RB, mBp_RBp])):
            continue
        spec.append(((mB_RB - mB_RBp) + (mBp_RBp - mBp_RB)) / 2)
        transf.append((mBp_RB + mB_RBp) / 2)
        jac.append(float(pairmeta[pid]["type_jaccard"]))
        clusters.append(int(pairmeta[pid]["seed"]))
    spec, transf, jac = np.array(spec), np.array(transf), np.array(jac)
    clusters = np.array(clusters)
    print(f"pairs={len(spec)}")

    # ---- Task 3.2: definitions (pooled specificity / transfer) ----
    print("\n== Task 3.2 definitions (harness recompute) ==")
    m("pooled specificity (mean over pairs)", float(spec.mean()), 0.0054)
    m("pooled transfer (mean over pairs)", float(transf.mean()), -0.0011)
    print("  (definitions match batch_swap_v2_analysis.py:61-68: draws averaged within arm first,"
          " mean over pairs)")

    # ---- Task 3.1: OLS ----
    A = np.vstack([np.ones_like(jac), jac]).T
    b0, b1 = np.linalg.lstsq(A, spec, rcond=None)[0]
    print("\n== Task 3.1 OLS specificity ~ type_jaccard ==")
    m("intercept", float(b0), -0.0176)
    m("slope", float(b1), 0.0690)
    print(f"  predicted@overlap=1 (b0+b1) = {b0 + b1:+.4f}")

    # ---- run-cluster bootstrap of slope and prediction@overlap=1 ----
    uniq = np.unique(clusters)
    idx_by = {c: np.where(clusters == c)[0] for c in uniq}
    slopes, preds = [], []
    for _ in range(NBOOT):
        pick = rng.choice(uniq, len(uniq), replace=True)
        ii = np.concatenate([idx_by[c] for c in pick])
        jj, ss = jac[ii], spec[ii]
        AA = np.vstack([np.ones_like(jj), jj]).T
        c0, c1 = np.linalg.lstsq(AA, ss, rcond=None)[0]
        slopes.append(c1)
        preds.append(c0 + c1)
    slo, shi = np.percentile(slopes, [2.5, 97.5])
    plo, phi = np.percentile(preds, [2.5, 97.5])
    print("\n== run-cluster bootstrap (NBOOT=%d, seed 20260703) ==" % NBOOT)
    print(f"  slope 95% CI: got=[{slo:+.4f},{shi:+.4f}] ref=[-0.0739,+0.1959]")
    print(f"  pred@overlap=1 95% CI: got=[{plo:+.4f},{phi:+.4f}] ref=[-0.0476,+0.1368]")

    # ---- jaccard support ----
    print("\n== type_jaccard support ==")
    m("max jaccard", float(jac.max()), 0.83)
    m("mean jaccard", float(jac.mean()), 0.335)


if __name__ == "__main__":
    main()
