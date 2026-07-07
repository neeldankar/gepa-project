"""Per-event JSONL logger for GEPA runs.

Implements the gepa GEPACallback protocol (duck-typed; no gepa edits, no fork).
Each callback writes ONE JSON line. Records are assembled OFFLINE from this raw
stream in a later pass, so an assembly bug can never lose data and the schema can
evolve without re-running anything.

Captured fields are whitelisted per event because several events carry whole
GEPAState / DataLoader objects (on_iteration_start/end, on_optimization_end) that
must never be serialized.

Usage:
    from gepa import optimize
    from si_event_logger import SIEventLogger
    logger = SIEventLogger("logs/run_001.jsonl", run_id="run_001")
    optimize(..., callbacks=[logger])
    logger.close()
"""

from __future__ import annotations

import json
import os
import threading
import time
from typing import Any

SCHEMA_VERSION = 1


def _json_default(o: Any) -> Any:
    # numpy scalars (np.float64 etc.) expose .item(); python float/int do not.
    item = getattr(o, "item", None)
    if callable(item):
        try:
            return o.item()
        except Exception:
            pass
    if isinstance(o, (set, tuple)):
        return list(o)
    return str(o)


class SIEventLogger:
    """Writes one JSON line per GEPA event to a JSONL file."""

    def __init__(self, path: str, run_id: str | None = None):
        self.path = path
        self.run_id = run_id or os.path.splitext(os.path.basename(path))[0]
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self._lock = threading.Lock()
        self._fh = open(path, "a", encoding="utf-8")
        self._closed = False
        # Self-describing header line so logs survive schema drift.
        try:
            import gepa  # noqa
            gepa_version = getattr(gepa, "__version__", "unknown")
        except Exception:
            gepa_version = "unknown"
        self._emit("meta", {"schema_version": SCHEMA_VERSION, "gepa_version": gepa_version})

    # -- core writer -------------------------------------------------------
    def _emit(self, event: str, fields: dict[str, Any]) -> None:
        if self._closed:
            return
        rec = {"run_id": self.run_id, "ts": time.time(), "event": event}
        rec.update(fields)
        line = json.dumps(rec, default=_json_default, ensure_ascii=False)
        with self._lock:
            self._fh.write(line + "\n")
            self._fh.flush()  # crash-safe: every emitted line is on disk

    def close(self) -> None:
        with self._lock:
            if not self._closed:
                self._fh.flush()
                self._fh.close()
                self._closed = True

    # -- lifecycle ---------------------------------------------------------
    def on_optimization_start(self, e: dict) -> None:
        self._emit("optimization_start", {
            "trainset_size": e.get("trainset_size"),
            "valset_size": e.get("valset_size"),
            "seed_candidate": e.get("seed_candidate"),
            "config": e.get("config"),
        })

    def on_optimization_end(self, e: dict) -> None:
        # NOTE: e["final_state"] is a GEPAState - do NOT serialize it.
        self._emit("optimization_end", {
            "best_candidate_idx": e.get("best_candidate_idx"),
            "total_iterations": e.get("total_iterations"),
            "total_metric_calls": e.get("total_metric_calls"),
        })

    # -- selection / sampling ---------------------------------------------
    def on_candidate_selected(self, e: dict) -> None:
        self._emit("candidate_selected", {
            "iteration": e.get("iteration"),
            "candidate_idx": e.get("candidate_idx"),
            "score": e.get("score"),
        })

    def on_minibatch_sampled(self, e: dict) -> None:
        self._emit("minibatch_sampled", {
            "iteration": e.get("iteration"),
            "minibatch_ids": e.get("minibatch_ids"),
            "trainset_size": e.get("trainset_size"),
        })

    # -- evaluation --------------------------------------------------------
    def on_evaluation_end(self, e: dict) -> None:
        # Whitelist: skip outputs/trajectories (large, not needed for scoring).
        self._emit("evaluation_end", {
            "iteration": e.get("iteration"),
            "candidate_idx": e.get("candidate_idx"),
            "scores": e.get("scores"),
            "objective_scores": e.get("objective_scores"),
            "parent_ids": e.get("parent_ids"),
            "is_seed_candidate": e.get("is_seed_candidate"),
        })

    def on_valset_evaluated(self, e: dict) -> None:
        # scores_by_val_id is the full D_pareto vector -> any DeltaU definable offline.
        self._emit("valset_evaluated", {
            "iteration": e.get("iteration"),
            "candidate_idx": e.get("candidate_idx"),
            "average_score": e.get("average_score"),
            "scores_by_val_id": e.get("scores_by_val_id"),
            "parent_ids": e.get("parent_ids"),
            "is_best_program": e.get("is_best_program"),
            "num_examples_evaluated": e.get("num_examples_evaluated"),
            "total_valset_size": e.get("total_valset_size"),
        })

    # -- reflection (THE SI) ----------------------------------------------
    def on_reflective_dataset_built(self, e: dict) -> None:
        # e["dataset"] is the SI verbatim, keyed by component -> list[per-example dict].
        # Logged raw; SI-text extraction (adapter-specific key, e.g. "Feedback")
        # happens in the scorer layer, not here.
        self._emit("reflective_dataset_built", {
            "iteration": e.get("iteration"),
            "candidate_idx": e.get("candidate_idx"),
            "components": e.get("components"),
            "dataset": e.get("dataset"),
        })

    def on_proposal_end(self, e: dict) -> None:
        # The actual reflection prompt + raw LM output - useful for later analysis.
        self._emit("proposal_end", {
            "iteration": e.get("iteration"),
            "new_instructions": e.get("new_instructions"),
            "prompts": e.get("prompts"),
            "raw_lm_outputs": e.get("raw_lm_outputs"),
        })

    # -- acceptance --------------------------------------------------------
    def on_candidate_accepted(self, e: dict) -> None:
        self._emit("candidate_accepted", {
            "iteration": e.get("iteration"),
            "new_candidate_idx": e.get("new_candidate_idx"),
            "new_score": e.get("new_score"),
            "parent_ids": e.get("parent_ids"),
        })

    def on_candidate_rejected(self, e: dict) -> None:
        self._emit("candidate_rejected", {
            "iteration": e.get("iteration"),
            "old_score": e.get("old_score"),
            "new_score": e.get("new_score"),
            "reason": e.get("reason"),
        })

    def on_iteration_end(self, e: dict) -> None:
        # NOTE: e["state"] is a GEPAState - do NOT serialize it.
        self._emit("iteration_end", {
            "iteration": e.get("iteration"),
            "proposal_accepted": e.get("proposal_accepted"),
        })
