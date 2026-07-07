"""Reflection-sensitivity + coverage-structure probe (Step 3).

Proposal-side lever check: do the 10 baseline runs (different random minibatch draws / seeds)
CONVERGE on the same solved valset cells, or DIVERGE? Convergence ⇒ reflection is insensitive
to which examples it's fed ⇒ weak lever. Divergence + reachable unreached territory ⇒ the lever
exists.

Per-cell valset score = fraction of constraints satisfied (FRACTIONAL, 11 levels). A run SOLVES
a cell iff its final-pool per-cell max == 1.0 (all constraints met). 0<best<1 = partial,
best==0 = fully unreached. Final-pool per-cell frontier = M.max(axis=0), M = pool_matrix(run).
"""

from __future__ import annotations

from itertools import combinations

import numpy as np

from gepa_si.screen.corpus_io import RunData
from gepa_si.screen.fungibility import pool_matrix

SOLVE_ATOL = 1e-9


def best_vector(run: RunData) -> np.ndarray:
    """Final-pool per-cell frontier (max over pool), shape (150,)."""
    M, _ = pool_matrix(run)
    return M.max(axis=0)


def solved_vector(run: RunData) -> np.ndarray:
    """Boolean (150,): cell fully solved by the pool (frontier == 1.0)."""
    return np.isclose(best_vector(run), 1.0, atol=SOLVE_ATOL)


def coverage_matrix(runs: list[RunData]) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """(solved bool (n_runs×150), best float (n_runs×150), run labels)."""
    labels = [f"s{r.seed}_b{r.b}" for r in runs]
    best = np.array([best_vector(r) for r in runs])
    solved = np.isclose(best, 1.0, atol=SOLVE_ATOL)
    return solved, best, labels


# ---------- Part A ----------
def per_cell_solve_count(solved: np.ndarray) -> np.ndarray:
    """For each cell, how many runs solve it -> histogram over 0..n_runs."""
    counts = solved.sum(axis=0)
    n = solved.shape[0]
    return np.bincount(counts, minlength=n + 1)  # index k = #cells solved by exactly k runs


def pairwise(solved: np.ndarray) -> dict[str, float]:
    """Mean/min/max/std Jaccard and Hamming over all run pairs on solved-cell sets."""
    jac, ham = [], []
    for a, b in combinations(range(solved.shape[0]), 2):
        sa, sb = solved[a], solved[b]
        inter = np.logical_and(sa, sb).sum()
        union = np.logical_or(sa, sb).sum()
        jac.append(inter / union if union else 1.0)
        ham.append(np.mean(sa != sb))
    jac, ham = np.array(jac), np.array(ham)
    return {
        "n_pairs": len(jac),
        "jaccard_mean": float(jac.mean()), "jaccard_min": float(jac.min()),
        "jaccard_max": float(jac.max()), "jaccard_std": float(jac.std()),
        "hamming_mean": float(ham.mean()), "hamming_min": float(ham.min()),
        "hamming_max": float(ham.max()), "hamming_std": float(ham.std()),
    }


def union_intersection(solved: np.ndarray) -> dict[str, float]:
    union = np.any(solved, axis=0)
    inter = np.all(solved, axis=0)
    per_run = solved.sum(axis=1)
    return {
        "n_cells": solved.shape[1],
        "union": int(union.sum()),
        "intersection": int(inter.sum()),
        "per_run_mean": float(per_run.mean()),
        "per_run_min": int(per_run.min()), "per_run_max": int(per_run.max()),
        "gap": int(union.sum() - inter.sum()),  # swingable territory
    }


# ---------- Part B ----------
def miss_breakdown(run: RunData) -> dict[str, float]:
    """Of cells with best<1: fraction fully unreached (best==0) vs partial (0<best<1)."""
    best = best_vector(run)
    solved = np.isclose(best, 1.0, atol=SOLVE_ATOL)
    miss = ~solved
    unreached = miss & np.isclose(best, 0.0, atol=SOLVE_ATOL)
    partial = miss & ~unreached
    n = len(best)
    return {
        "n_cells": n, "n_solved": int(solved.sum()),
        "n_miss": int(miss.sum()),
        "n_unreached": int(unreached.sum()), "n_partial": int(partial.sum()),
        "frac_solved": float(solved.mean()),
        "frac_unreached": float(unreached.mean()), "frac_partial": float(partial.mean()),
    }


def hard_core(solved: np.ndarray, best: np.ndarray) -> dict[str, object]:
    """Never-solved-by-any vs shifting misses; best-score profile of the stuck core."""
    n_runs = solved.shape[0]
    solve_count = solved.sum(axis=0)
    never = solve_count == 0          # missed by every run
    always = solve_count == n_runs    # solved by every run
    shifting = (solve_count > 0) & (solve_count < n_runs)  # reachable-but-not-always
    # for the never-solved core: is the best any run ever reached 0 (truly stuck) or partial?
    core_best_max = best[:, never].max(axis=0) if never.any() else np.array([])
    core_all_zero = int(np.isclose(core_best_max, 0.0, atol=SOLVE_ATOL).sum())
    core_partial = int((core_best_max > SOLVE_ATOL).sum())
    return {
        "never_solved": int(never.sum()),
        "always_solved": int(always.sum()),
        "shifting": int(shifting.sum()),  # the reachable-but-missed set
        "core_truly_stuck_best0": core_all_zero,   # never-solved cells where no run got ANY traction
        "core_partial_reached": core_partial,      # never fully solved but some run got partial credit
        "core_best_mean": float(core_best_max.mean()) if core_best_max.size else float("nan"),
    }
