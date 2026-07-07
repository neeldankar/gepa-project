"""Fungibility / frontier-redundancy diagnostic (Task 2) — read-only, no API.

Per run: LOO unique frontier contribution of each final-pool candidate + per-cell redundancy.
Reports pooled + per-run distributions, the headline fraction-of-zero contributions, the
uniquely-vs-redundantly-maxed cell split, a fat-tail check, and a routing verdict.

    .venv/bin/python scripts/run_fungibility.py
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd

from gepa_si.screen.corpus_io import load_corpus
from gepa_si.screen.fungibility import (
    cell_uniqueness, loo_contributions, loo_contributions_bruteforce, pool_matrix,
)

EPS = 1e-6
OUT_PARQUET = "analysis/fungibility.parquet"


def main() -> None:
    runs = load_corpus()
    print(f"runs: {len(runs)}\n")

    rows = []
    per_run = []
    for run in runs:
        contrib = loo_contributions(run)
        # validate the identity against brute force
        bf = loo_contributions_bruteforce(run)
        max_err = max(abs(contrib[k] - bf[k]) for k in contrib)
        assert max_err < 1e-9, f"seed{run.seed}_b{run.b}: identity mismatch {max_err:.2e}"

        cu = cell_uniqueness(run)
        M, idxs = pool_matrix(run)
        U = cu["U"]
        vals = np.array([contrib[k] for k in idxs])
        accept_order = {ci: r for r, ci in enumerate(idxs)}  # 0 = seed

        for ci in idxs:
            rows.append({
                "seed": run.seed, "b": run.b, "idx": ci, "accept_order": accept_order[ci],
                "is_seed": ci == 0, "loo_contribution": contrib[ci],
            })

        per_run.append({
            "run": f"s{run.seed}_b{run.b}", "n_pool": len(idxs), "U": U,
            "sum_contrib": float(vals.sum()),
            "median": float(np.median(vals)), "max": float(vals.max()),
            "frac_zero": float(np.mean(np.abs(vals) <= EPS)),
            "frac_unique_cells": cu["frac_unique"], "frac_redundant_cells": cu["frac_redundant"],
            "mean_achievers": cu["mean_achievers"],
        })

        # sanity: unique contributions never exceed U (no double counting of redundant cells)
        assert vals.sum() <= U + 1e-9, f"seed{run.seed}: sum_contrib {vals.sum()} > U {U}"
        assert (vals >= -1e-9).all(), f"seed{run.seed}: negative contribution"

    df = pd.DataFrame(rows)
    prun = pd.DataFrame(per_run)

    # ---- per-run table ----
    pd.set_option("display.width", 170, "display.max_columns", 30)
    print("=== per-run summary (final pool) ===")
    print(prun.round(5).to_string(index=False))

    # ---- pooled LOO-contribution distribution ----
    c = df["loo_contribution"].to_numpy()
    print("\n=== LOO unique frontier contribution — pooled across all candidates ===")
    print(f"  n candidates (pool members, all runs): {len(c)}")
    print(f"  mean={c.mean():.5f}  median={np.median(c):.5f}  "
          f"IQR=[{np.quantile(c,.25):.5f}, {np.quantile(c,.75):.5f}]  max={c.max():.5f}")
    for q in (0.5, 0.75, 0.9, 0.95, 0.99):
        print(f"    q{int(q*100)}={np.quantile(c, q):.5f}")
    n_zero = int(np.sum(np.abs(c) <= EPS))
    n_exact = int(np.sum(c == 0.0))
    print(f"  fraction ~0 (|c|<=1e-6): {n_zero}/{len(c)} = {n_zero/len(c):.3f}  "
          f"(exact-0: {n_exact})")

    # ---- headline ----
    print("\n=== HEADLINE ===")
    print(f"  fraction of pool candidates with ~0 unique frontier contribution: "
          f"{n_zero/len(c):.3f}")

    # ---- cell redundancy (pooled over the 10 x 150 cells) ----
    fu = prun["frac_unique_cells"].to_numpy()
    fr = prun["frac_redundant_cells"].to_numpy()
    # pooled by averaging per-run fractions (each run has the same 150 cells)
    print("\n=== valset-cell redundancy (per-instance max achievers) ===")
    print(f"  mean fraction UNIQUELY maxed (1 achiever):    {fu.mean():.3f}  "
          f"(per-run range {fu.min():.3f}-{fu.max():.3f})")
    print(f"  mean fraction REDUNDANTLY covered (>=2):      {fr.mean():.3f}  "
          f"(per-run range {fr.min():.3f}-{fr.max():.3f})")
    print(f"  mean achievers per cell: {prun['mean_achievers'].mean():.2f}")

    # ---- fat-tail check ----
    print("\n=== fat-tail check ===")
    nz = c[np.abs(c) > EPS]
    print(f"  nonzero contributions: {len(nz)}/{len(c)} ({len(nz)/len(c):.3f})")
    if len(nz):
        print(f"  among nonzero: median={np.median(nz):.5f}  max={nz.max():.5f}  "
              f"max/median={nz.max()/max(np.median(nz),1e-12):.1f}x")
    # share of total pooled contribution carried by the top-decile candidates
    cs = np.sort(c)[::-1]
    top10 = cs[: max(1, len(cs) // 10)].sum()
    print(f"  top-10% of candidates carry {top10/max(c.sum(),1e-12):.1%} of total unique contribution")

    # ---- verdict ----
    frac_zero = n_zero / len(c)
    print("\n=== VERDICT ===")
    if frac_zero >= 0.5 and fr.mean() >= 0.5:
        print(f"  REDUNDANT frontier: {frac_zero:.0%} of pool members add ~0 unique value and "
              f"{fr.mean():.0%} of valset cells are redundantly covered.")
        print("  => per-example selection is ceilinged; flag the cell-selection / Direction-C pivot.")
    else:
        print(f"  HEADROOM: only {frac_zero:.0%} of members are ~0 and "
              f"{fu.mean():.0%} of cells are uniquely maxed (fat tail present).")
        print("  => selection has room; proceed to scorer screening.")

    os.makedirs("analysis", exist_ok=True)
    df.to_parquet(OUT_PARQUET, index=False)
    print(f"\nwrote {OUT_PARQUET}: {df.shape[0]} rows x {df.shape[1]} cols")


if __name__ == "__main__":
    main()
