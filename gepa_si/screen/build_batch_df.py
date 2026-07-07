"""STEP 1 — per-batch dataframe (unit = the b-example minibatch / one reflection event).

Joins parsed reflection cycles (corpus_io) with the exact ΔU outcome (delta_u) into one
row per reflection event, and writes analysis/batch_df.parquet. Also prints the ΔU
sanity report (distribution + zero decomposition).
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd

from gepa_si.screen.corpus_io import load_corpus
from gepa_si.screen.delta_u import deltau_per_cycle

OUT_PARQUET = "analysis/batch_df.parquet"


def build_dataframe() -> pd.DataFrame:
    runs = load_corpus()
    rows = []
    for run in runs:
        du = deltau_per_cycle(run)
        for c in run.cycles:
            s = np.array(c.before_scores, dtype=float)  # parent per-example minibatch scores
            failed_union = sorted({fid for ex in c.failed_ids_per_example for fid in ex})
            rows.append({
                "seed": run.seed,
                "b": run.b,
                "iteration": c.iteration,
                "parent_id": c.parent_id,
                "minibatch_ids": list(c.minibatch_ids),
                "failed_ids": failed_union,
                "signature": "|".join(failed_union),  # batch failed-constraint signature
                "n_failed_ids": len(failed_union),
                # controls
                "difficulty": float(np.mean(1.0 - s)),          # mean inverse before-score
                "n2_peakedness": float(np.mean(s * (1.0 - s))),  # mean s(1-s)
                "parent_dpareto": _parent_dpareto(run, c.parent_id),
                # outcome + flag
                "accept": bool(c.accept),
                "delta_u": float(du[c.iteration]),
            })
    df = pd.DataFrame(rows)
    return df


def _parent_dpareto(run, parent_id):
    """Parent's D_pareto score = mean of its valset vector (== candidate_selected.score)."""
    sbv = run.valset_by_candidate.get(parent_id)
    if not sbv:
        return float("nan")
    return float(np.mean(list(sbv.values())))


def sanity_report(df: pd.DataFrame) -> None:
    print("=== ΔU sanity ===")
    du = df["delta_u"].to_numpy()
    print(f"  rows (reflection events): {len(df)}")
    print(f"  ΔU  mean={du.mean():.5f}  sd={du.std():.5f}  "
          f"min={du.min():.5f}  median={np.median(du):.5f}  max={du.max():.5f}")
    for q in (0.5, 0.75, 0.9, 0.95, 0.99):
        print(f"    q{int(q*100)}={np.quantile(du, q):.5f}")
    exact_zero = (du == 0.0)
    n_zero = int(exact_zero.sum())
    n_reject = int((~df["accept"]).sum())
    zero_accepts = int((exact_zero & df["accept"]).sum())
    print(f"  exact zeros: {n_zero}/{len(df)} ({100*n_zero/len(df):.1f}%)")
    print(f"    rejects (must be 0): {n_reject}  | reject rows all ΔU==0: "
          f"{bool((df.loc[~df['accept'],'delta_u']==0).all())}")
    print(f"    zero-gain ACCEPTS (accepted on minibatch, no valset frontier gain): {zero_accepts}")
    print(f"    => zeros = {n_reject} rejects + {zero_accepts} zero-gain accepts = {n_reject+zero_accepts}")
    # b3 vs b1 reject counts
    b3 = df[df.b == 3]
    print(f"  b3 reject rows: {int((~b3['accept']).sum())} (corpus reported 267)")
    print(f"  accepts with ΔU>0: {int((df['accept'] & (du>0)).sum())}")


if __name__ == "__main__":
    df = build_dataframe()
    os.makedirs("analysis", exist_ok=True)
    df.to_parquet(OUT_PARQUET, index=False)
    print(f"wrote {OUT_PARQUET}: {df.shape[0]} rows x {df.shape[1]} cols")
    print("columns:", list(df.columns))
    print()
    sanity_report(df)
