"""Fungibility / frontier-redundancy diagnostic (Task 2).

Question: is the final-pool valset frontier carried by a few non-redundant children, or
spread redundantly across cross-covering ones? If redundant (every per-instance max is
achieved by several pool members), NO per-example scorer can move final-U — routing the
project toward cell-selection / Direction-C. A fat tail of large unique contributions means
selection has headroom -> proceed to scorer screening.

Final pool of a run = run.valset_by_candidate (idx 0 = seed, 1..N = accepts), each a
150-vector. U(pool) = mean_i max_k M[k,i] (instance frontier, mean aggregate; confirmed from
gepa core/state.py and matching delta_u.final_frontier_mean).

LOO contribution of candidate k = U(pool) - U(pool \\ {k}). Via the frontier identity, with
best_i = max and second_i = 2nd-highest across the pool at instance i:
    U - U_minus_k = mean_i [ (k is the SOLE argmax at i) * (best_i - second_i) ]
A cell whose max is tied by >=2 candidates contributes 0 to every candidate (redundant).
"""

from __future__ import annotations

import numpy as np

from gepa_si.screen.corpus_io import RunData

TIE_ATOL = 1e-9


def pool_matrix(run: RunData) -> tuple[np.ndarray, list[int]]:
    """(n_pool x n_val) score matrix and the candidate idx order (sorted)."""
    valset = run.valset_by_candidate
    idxs = sorted(valset.keys())
    val_ids = sorted(valset[idxs[0]].keys(), key=int)
    M = np.array([[valset[ci][v] for v in val_ids] for ci in idxs], dtype=float)
    return M, idxs


def _best_second(M: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Per-column best and second-best across the pool (rows = candidates)."""
    part = np.sort(M, axis=0)  # ascending; last = best, second-last = 2nd best
    best = part[-1, :]
    second = part[-2, :] if M.shape[0] >= 2 else np.full(M.shape[1], -np.inf)
    return best, second


def loo_contributions(run: RunData) -> dict[int, float]:
    """idx -> U(pool) - U(pool\\{idx}) via the sole-argmax identity."""
    M, idxs = pool_matrix(run)
    best, second = _best_second(M)
    # sole argmax at column i: exactly one row equals best within tolerance
    at_max = np.isclose(M, best[None, :], atol=TIE_ATOL)  # (n_pool, n_val)
    n_at_max = at_max.sum(axis=0)
    sole = n_at_max == 1                                    # (n_val,)
    drop = np.where(sole, best - second, 0.0)               # marginal loss per cell if its sole holder leaves
    out: dict[int, float] = {}
    for r, ci in enumerate(idxs):
        contrib_cells = at_max[r, :] & sole
        out[ci] = float(np.mean(np.where(contrib_cells, drop, 0.0)))
    return out


def loo_contributions_bruteforce(run: RunData) -> dict[int, float]:
    """Reference: recompute mean(max over pool\\{k}) directly. Used only to validate."""
    M, idxs = pool_matrix(run)
    U = float(M.max(axis=0).mean())
    out: dict[int, float] = {}
    for r, ci in enumerate(idxs):
        Mk = np.delete(M, r, axis=0)
        out[ci] = U - float(Mk.max(axis=0).mean())
    return out


def cell_uniqueness(run: RunData) -> dict[str, float | np.ndarray]:
    """Per-instance redundancy structure: how many pool members tie the per-cell max."""
    M, _ = pool_matrix(run)
    best, _ = _best_second(M)
    at_max = np.isclose(M, best[None, :], atol=TIE_ATOL)
    n_at_max = at_max.sum(axis=0)
    n_val = M.shape[1]
    return {
        "n_val": n_val,
        "n_at_max": n_at_max,                              # per-cell achiever count
        "frac_unique": float(np.mean(n_at_max == 1)),      # exactly one achiever
        "frac_redundant": float(np.mean(n_at_max >= 2)),   # >=2 achievers
        "mean_achievers": float(n_at_max.mean()),
        "U": float(best.mean()),
    }
