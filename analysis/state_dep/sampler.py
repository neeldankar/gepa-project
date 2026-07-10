"""Oversampled batch sampler for arms C and T (design v2 §4, §7a).

Arms C and T draw M=6 example ids per event instead of b=3. gepa 0.0.27 makes this a clean
public-arg injection: `gepa.optimize(batch_sampler=..., reflection_minibatch_size=None)`
(`api.py:301-306`; passing both trips the assert at `:304`).

Two facts about `EpochShuffledBatchSampler` that this experiment depends on, verified in code
(`gepa/strategies/batch_sampler.py`):

1. **A draw never straddles an epoch boundary.** `_update_shuffled` pads the id list to an exact
   multiple of `minibatch_size` (100 -> 102 for BOTH b=3 and b=6), and `base_idx = state.i *
   minibatch_size` is always a multiple of `minibatch_size`. So the slice always fits, and when the
   index wraps, `curr_epoch` has already incremented and the list has been reshuffled.
   b=3 -> 34 minibatches/epoch, reshuffle at state.i = 34, 68, ...
   b=6 -> 17 minibatches/epoch, reshuffle at state.i = 17, 34, ...

2. **The RNG is SHARED.** `api.py:256` builds one `random.Random(seed)` and hands the same object
   to the batch sampler (`:302`), the Pareto candidate selector (`:261`), and merge (`:357`).
   Because b=6 reshuffles at different iterations than b=3, the shared stream diverges between B
   and T/C from the first epoch boundary onward -- so parent selection diverges too, not just
   batching. This is documented in v2 §7a and is why arm-specific picks (C's random choice, T's
   tie-breaks) MUST draw from their own `random.Random` objects and never from this one.
   T vs C are unaffected: both draw 6, so they consume this stream identically.

   (The sampler docstring claims determinism "via state.rng1". `GEPAState` has no such attribute.
   Determinism is real; the stated source is not.)

This module adds only logging on top of the stock sampler. The draw logic is gepa's, untouched.
"""
from __future__ import annotations

import random

from gepa.strategies.batch_sampler import EpochShuffledBatchSampler


class LoggingEpochShuffledBatchSampler(EpochShuffledBatchSampler):
    """Stock epoch-shuffled sampler + a per-event record of what it drew.

    `draws` is consumed by the runner for the v2 §12 persistence set ("the 6 drawn example IDs,
    draw order") and by the count-audit to confirm the epoch-boundary arithmetic above.
    """

    def __init__(self, minibatch_size: int, rng: random.Random | None = None):
        super().__init__(minibatch_size=minibatch_size, rng=rng)
        self.draws: list[dict] = []

    def next_minibatch_ids(self, loader, state):
        epoch_before = self.epoch
        ids = super().next_minibatch_ids(loader, state)
        self.draws.append(
            {
                "iteration": state.i,
                "minibatch_size": self.minibatch_size,
                "ids": list(ids),
                "epoch": self.epoch,
                "reshuffled_this_call": self.epoch != epoch_before,
                "shuffled_len": len(self.shuffled_ids),
            }
        )
        return ids
