"""Read-only parser: corpus run logs -> structured reflection-cycle records.

Discovers completed mm=2500 runs from their sidecars and walks each run's JSONL,
grouping events by `iteration` into one record per reflection cycle. Verified schema
(see plan STEP 0): within a cycle there are TWO evaluation_end events — the BEFORE eval
(parent; candidate_idx is the parent's idx, on the minibatch) and the AFTER eval
(child; candidate_idx is None). We use the BEFORE eval for minibatch scores +
objective_scores. valset_evaluated fires once per accepted candidate (idx = accept order).

No GEPA re-runs, no API calls — pure log reading.
"""

from __future__ import annotations

import glob
import json
import os
from dataclasses import dataclass, field

MAX_METRIC_CALLS = 2500


@dataclass
class ReflectionCycle:
    seed: int
    b: int
    iteration: int
    parent_id: int
    minibatch_ids: list[int]
    before_scores: list[float]              # parent's per-example score on the minibatch
    failed_ids_per_example: list[list[str]] # failed constraint ids per minibatch example
    accept: bool
    child_idx: int | None                   # assigned only on accept
    child_valset: dict[str, float] | None   # child scores_by_val_id on accept
    # raw per-constraint satisfaction on the minibatch (aligned to minibatch_ids), {cid: 1.0/0.0}
    parent_objscores: list[dict] = field(default_factory=list)   # BEFORE eval (parent)
    child_objscores: list[dict] | None = None                    # AFTER eval (proposed child)


@dataclass
class RunData:
    seed: int
    b: int
    log_path: str
    cycles: list[ReflectionCycle]
    # candidate_idx -> scores_by_val_id, in accept order (idx 0 = seed)
    valset_by_candidate: dict[int, dict[str, float]] = field(default_factory=dict)


def discover_runs(mm: int = MAX_METRIC_CALLS) -> list[dict]:
    """Completed run sidecars at the given budget, sorted (b desc, seed)."""
    out = []
    for path in glob.glob("logs/*.config.json"):
        try:
            with open(path, encoding="utf-8") as fh:
                cfg = json.load(fh)
        except (json.JSONDecodeError, OSError):
            continue
        if cfg.get("max_metric_calls") == mm and cfg.get("results", {}).get("completed"):
            out.append(cfg)
    return sorted(out, key=lambda c: (-c["b"], c["seed"]))


def _load(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _failed_ids(objective_scores_example: dict[str, float]) -> list[str]:
    # objective_scores key may carry a "#index" dedup suffix; strip it.
    return sorted(
        k.split("#", 1)[0] for k, v in objective_scores_example.items() if v == 0.0
    )


def parse_run(cfg: dict) -> RunData:
    seed, b, log_path = cfg["seed"], cfg["b"], cfg["log_path"]
    records = _load(log_path)

    # group events by iteration
    by_it: dict[int, list[dict]] = {}
    valset_by_candidate: dict[int, dict[str, float]] = {}
    for rec in records:
        ev = rec.get("event")
        if ev == "valset_evaluated":
            ci = rec.get("candidate_idx")
            if ci is not None:
                valset_by_candidate[ci] = rec.get("scores_by_val_id") or {}
        it = rec.get("iteration")
        if it is None or ev in ("meta", "optimization_start", "optimization_end"):
            continue
        by_it.setdefault(it, []).append(rec)

    cycles: list[ReflectionCycle] = []
    for it, evs in sorted(by_it.items()):
        kinds = {e["event"] for e in evs}
        # a reflection cycle must have sampled a minibatch and built a reflective dataset
        if "minibatch_sampled" not in kinds or "reflective_dataset_built" not in kinds:
            continue

        minibatch = next(e for e in evs if e["event"] == "minibatch_sampled")
        mb_ids = list(minibatch.get("minibatch_ids") or [])

        # BEFORE eval = the evaluation_end whose candidate_idx is not None (parent idx).
        evals = [e for e in evs if e["event"] == "evaluation_end"]
        before = next((e for e in evals if e.get("candidate_idx") is not None), None)
        assert before is not None, f"{log_path} it={it}: no before-eval with a parent idx"
        parent_id = before["candidate_idx"]
        before_scores = list(before.get("scores") or [])
        obj = before.get("objective_scores") or []
        failed = [_failed_ids(o or {}) for o in obj]
        parent_objscores = [dict(o or {}) for o in obj]

        # AFTER eval = the evaluation_end whose candidate_idx is None (the proposed child);
        # same minibatch, same order. Absent in the rare 1-eval iteration anomaly -> None.
        after = next((e for e in evals if e.get("candidate_idx") is None), None)
        child_objscores = (
            [dict(o or {}) for o in (after.get("objective_scores") or [])]
            if after is not None else None
        )

        assert len(before_scores) == len(mb_ids), (
            f"{log_path} it={it}: before.scores ({len(before_scores)}) != "
            f"minibatch_ids ({len(mb_ids)})"
        )

        accepted_ev = next((e for e in evs if e["event"] == "candidate_accepted"), None)
        rejected_ev = next((e for e in evs if e["event"] == "candidate_rejected"), None)
        assert (accepted_ev is None) != (rejected_ev is None), (
            f"{log_path} it={it}: expected exactly one of accept/reject"
        )
        accept = accepted_ev is not None
        child_idx = accepted_ev.get("new_candidate_idx") if accept else None
        child_valset = valset_by_candidate.get(child_idx) if child_idx is not None else None

        cycles.append(ReflectionCycle(
            seed=seed, b=b, iteration=it, parent_id=parent_id, minibatch_ids=mb_ids,
            before_scores=before_scores, failed_ids_per_example=failed,
            accept=accept, child_idx=child_idx, child_valset=child_valset,
            parent_objscores=parent_objscores, child_objscores=child_objscores,
        ))

    return RunData(seed=seed, b=b, log_path=log_path, cycles=cycles,
                   valset_by_candidate=valset_by_candidate)


def load_corpus() -> list[RunData]:
    return [parse_run(cfg) for cfg in discover_runs()]


if __name__ == "__main__":
    runs = load_corpus()
    print(f"runs: {len(runs)}")
    for r in runs:
        acc = sum(c.accept for c in r.cycles)
        print(f"  seed{r.seed}_b{r.b}: cycles={len(r.cycles)} accepts={acc} "
              f"rejects={len(r.cycles)-acc} candidates_valset={len(r.valset_by_candidate)}")
