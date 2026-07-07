"""Tractability-weighted minibatch sampler for the Phase-2 live A/B.

The Phase-1 survivor `constraint_tractability` as a live curriculum: oversample feedback
examples whose constraints are tractable-type. Selection PRECEDES observing which constraints
fail, so the weight keys off the example's SPEC (its constraint-type composition), not a failed
set. Fail-rates are FROZEN from the baseline corpus (Phase 1, via partial_diag) — never
recomputed from the live run, so the scorer is a fixed property of the constraint types.

    w(e) = mean over c in e.instruction_id_list of (1 - failrate(type(c)))    (+ eps floor)

Each iteration draws `b` ids weighted-without-replacement proportional to w. This intentionally
abandons epoch-coverage (the uniform baseline's behavior) in favor of concentrated re-exposure.
"""

from __future__ import annotations

import numpy as np

from gepa.strategies.batch_sampler import BatchSampler
from gepa_si.screen.scorer_inputs import constraint_type, type_failrate


class TractabilitySampler(BatchSampler):
    def __init__(self, minibatch_size: int, seed: int = 0, eps: float = 1e-3):
        self.minibatch_size = minibatch_size
        self.rng = np.random.default_rng(seed)
        self.eps = eps
        self._weights: np.ndarray | None = None
        self._ids: list | None = None

    def _example_weight(self, item: dict, failrate: dict[str, float]) -> float:
        types = [constraint_type(c) for c in (item.get("instruction_id_list") or [])]
        vals = [1.0 - failrate.get(t, 0.5) for t in types]  # tractability = 1 - failrate
        return float(np.mean(vals)) if vals else 0.5

    def _ensure_weights(self, loader) -> None:
        # static weights: compute once (recompute only if the trainset size changes)
        if self._weights is not None and self._ids is not None and len(self._ids) == len(loader):
            return
        ids = list(loader.all_ids())
        items = loader.fetch(ids)
        failrate = type_failrate()
        w = np.array([self._example_weight(it, failrate) for it in items], dtype=float)
        self._weights = w + self.eps
        self._ids = ids

    def next_minibatch_ids(self, loader, state):
        if len(loader) == 0:
            raise ValueError("Cannot sample a minibatch from an empty loader.")
        self._ensure_weights(loader)
        b = min(self.minibatch_size, len(self._ids))
        p = self._weights / self._weights.sum()
        chosen = self.rng.choice(len(self._ids), size=b, replace=False, p=p)
        return [self._ids[i] for i in chosen]
