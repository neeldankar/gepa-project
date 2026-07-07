"""Reflection-sensitivity + coverage-structure probe (Step 3) — read-only, no API.

Part A: cross-run coverage divergence (solve-count histogram, Jaccard/Hamming, union/inter/gap).
Part B: structure of the unreached territory (unreached vs partial; hard-core vs shifting).
Routes the project: convergent ⇒ weak proposal-side lever; divergent + reachable ⇒ lever exists.

    .venv/bin/python scripts/run_coverage.py
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd

from gepa_si.screen.corpus_io import load_corpus
from gepa_si.screen.coverage import (
    coverage_matrix, hard_core, miss_breakdown, pairwise,
    per_cell_solve_count, union_intersection,
)

OUT_PARQUET = "analysis/coverage.parquet"


def _hist_line(hist: np.ndarray) -> str:
    return "  ".join(f"{k}:{int(c)}" for k, c in enumerate(hist))


def _report_group(runs, title):
    solved, best, labels = coverage_matrix(runs)
    n_runs = solved.shape[0]
    print(f"\n========== {title}  ({n_runs} runs: {', '.join(labels)}) ==========")

    # A1 — per-cell solve-count histogram
    hist = per_cell_solve_count(solved)
    print(f"\n[A1] per-cell solve count (k = #runs solving a cell, value = #cells):")
    print("   " + _hist_line(hist))
    ends = hist[0] + hist[-1]
    print(f"   piled at extremes (0 or {n_runs}): {int(ends)}/{solved.shape[1]} "
          f"({ends/solved.shape[1]:.1%})  |  spread in middle: "
          f"{int(hist[1:-1].sum())} ({hist[1:-1].sum()/solved.shape[1]:.1%})")

    # A2 — pairwise agreement
    pw = pairwise(solved)
    print(f"\n[A2] pairwise agreement over {pw['n_pairs']} run pairs (solved-cell sets):")
    print(f"   Jaccard  mean={pw['jaccard_mean']:.3f}  "
          f"[{pw['jaccard_min']:.3f}, {pw['jaccard_max']:.3f}]  sd={pw['jaccard_std']:.3f}")
    print(f"   Hamming  mean={pw['hamming_mean']:.3f}  "
          f"[{pw['hamming_min']:.3f}, {pw['hamming_max']:.3f}]  sd={pw['hamming_std']:.3f}")

    # A3 — union / intersection / gap
    ui = union_intersection(solved)
    print(f"\n[A3] coverage extent (of {ui['n_cells']} cells):")
    print(f"   union (ANY run solves):        {ui['union']}  ({ui['union']/ui['n_cells']:.1%})")
    print(f"   intersection (EVERY run):      {ui['intersection']}  "
          f"({ui['intersection']/ui['n_cells']:.1%})")
    print(f"   per-run mean solved:           {ui['per_run_mean']:.1f}  "
          f"(range {ui['per_run_min']}-{ui['per_run_max']})")
    print(f"   >> swingable gap (union-inter): {ui['gap']}  "
          f"({ui['gap']/ui['n_cells']:.1%} of cells)")

    # B — hard core vs shifting
    hc = hard_core(solved, best)
    print(f"\n[B] unreached-territory structure:")
    print(f"   never solved by ANY run:       {hc['never_solved']}  "
          f"(of which best==0 everywhere: {hc['core_truly_stuck_best0']}, "
          f"partial somewhere: {hc['core_partial_reached']})")
    print(f"   always solved by EVERY run:    {hc['always_solved']}")
    print(f"   shifting (some solve, some miss): {hc['shifting']}  <-- reachable but not always reached")
    return solved, best, labels, ui, pw, hc


def main() -> None:
    runs = load_corpus()
    all10 = runs
    b3 = [r for r in runs if r.b == 3]
    print(f"loaded {len(runs)} runs ({len(b3)} b3, {len(runs)-len(b3)} b1)")

    # ----- Part B miss breakdown (per run, pooled) -----
    print("\n=== [B4] miss breakdown per run (solve = best==1.0) ===")
    rows_mb = []
    for r in runs:
        mb = miss_breakdown(r)
        rows_mb.append({"run": f"s{r.seed}_b{r.b}", **mb})
    mb_df = pd.DataFrame(rows_mb)
    pd.set_option("display.width", 170, "display.max_columns", 30)
    print(mb_df[["run", "n_solved", "n_miss", "n_unreached", "n_partial",
                 "frac_solved", "frac_unreached", "frac_partial"]].round(3).to_string(index=False))
    print(f"\n  pooled: mean frac_solved={mb_df.frac_solved.mean():.3f}  "
          f"frac_unreached={mb_df.frac_unreached.mean():.3f}  "
          f"frac_partial={mb_df.frac_partial.mean():.3f}")
    print(f"  of MISSED cells: {mb_df.n_unreached.sum()/(mb_df.n_miss.sum()):.1%} fully unreached, "
          f"{mb_df.n_partial.sum()/(mb_df.n_miss.sum()):.1%} partial")

    # ----- Part A + hard-core for both groups -----
    _report_group(all10, "ALL 10 RUNS (primary, mixes b1+b3)")
    _report_group(b3, "b3-ONLY (8 runs, controlled: only seed varies)")

    # ----- verdict (prose from the numbers) -----
    solved10, best10, _ = coverage_matrix(all10)
    ui = union_intersection(solved10)
    pw = pairwise(solved10)
    hc = hard_core(solved10, best10)
    print("\n========== VERDICT ==========")
    print(f"  Jaccard {pw['jaccard_mean']:.2f} | swingable gap {ui['gap']}/150 "
          f"({ui['gap']/150:.0%}) | shifting (reachable-but-missed) {hc['shifting']} | "
          f"hard core {hc['never_solved']} (stuck-at-0: {hc['core_truly_stuck_best0']})")
    convergent = pw["jaccard_mean"] >= 0.75 and ui["gap"] / 150 <= 0.10
    if convergent:
        print("  CONVERGENT: runs agree on solved cells, small swingable gap => reflection is "
              "input-INSENSITIVE => proposal-side lever weak => weight Direction-C pivot.")
    else:
        print("  DIVERGENT: runs disagree on a meaningful swingable territory => reflection IS "
              "sensitive to inputs => lever exists. Reframe around REACHING the shifting/unreached "
              "cells rather than reshuffling a redundant pool.")

    # ----- artifact -----
    rows = []
    solved, best, labels = coverage_matrix(runs)
    for ri, r in enumerate(runs):
        for cell in range(solved.shape[1]):
            rows.append({"run": labels[ri], "seed": r.seed, "b": r.b, "cell": cell,
                         "best": float(best[ri, cell]), "solved": bool(solved[ri, cell])})
    df = pd.DataFrame(rows)
    os.makedirs("analysis", exist_ok=True)
    df.to_parquet(OUT_PARQUET, index=False)
    print(f"\nwrote {OUT_PARQUET}: {df.shape[0]} rows x {df.shape[1]} cols")


if __name__ == "__main__":
    main()
