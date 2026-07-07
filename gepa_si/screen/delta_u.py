"""STEP 2 — exact ΔU outcome (pool-frontier marginal gain), reconstructed offline.

U(pool) = mean over val instances of the per-instance pool-best (gepa's
pareto_front_valset with frontier_type='instance'; confirmed from core/state.py).
For an accepted child c added in accept order:
    ΔU_c = mean_i max(0, child[i] - front_before[i]);  then front[i] = max(front[i], child[i])
Rejected children contribute ΔU = 0. One continuous, zero-inflated outcome — NOT split
into accept × magnitude.
"""

from __future__ import annotations

import numpy as np

from gepa_si.screen.corpus_io import RunData


def deltau_per_cycle(run: RunData) -> dict[int, float]:
    """iteration -> ΔU for each reflection cycle in `run`."""
    valset = run.valset_by_candidate
    val_ids = sorted(valset[0].keys(), key=int) if 0 in valset else sorted(
        next(iter(valset.values())).keys(), key=int
    )

    def vec(ci: int) -> np.ndarray:
        sbv = valset[ci]
        return np.array([sbv[k] for k in val_ids], dtype=float)

    # initial frontier = seed (candidate 0)
    front = vec(0).copy()

    # map produced candidate idx -> cycle iteration
    child_to_it = {c.child_idx: c.iteration for c in run.cycles if c.accept and c.child_idx is not None}

    deltau: dict[int, float] = {c.iteration: 0.0 for c in run.cycles}  # rejects default 0

    for ci in sorted(c for c in valset.keys() if c != 0):
        child = vec(ci)
        gain = float(np.maximum(0.0, child - front).mean())
        front = np.maximum(front, child)
        it = child_to_it.get(ci)
        if it is not None:
            deltau[it] = gain
        # else: a valset-evaluated candidate not tied to a reflection cycle (shouldn't happen)

    return deltau


def final_frontier_mean(run: RunData) -> float:
    valset = run.valset_by_candidate
    val_ids = sorted(valset[0].keys(), key=int)
    front = np.array([valset[0][k] for k in val_ids], dtype=float)
    for ci in sorted(c for c in valset if c != 0):
        front = np.maximum(front, np.array([valset[ci][k] for k in val_ids], dtype=float))
    return float(front.mean())
