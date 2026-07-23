"""Shared post-hoc evaluator: score one candidate program on one held-out split.

Used by BOTH §8b consumers, so they cannot drift apart:

    backfill_stage1.py   Stage-1's 97 candidates on the selection split, then 8 winners on test
    score_candidates.py  a live run's candidates on the selection split, then the winner on test

This module performs LIVE SPEND when called. It holds NO gate of its own -- the callers do, because
the gate is per-spend-decision, not per-function. Nothing here runs on import.

WHAT "one metric call" MEANS. A metric call is one claim pushed through the 3-hop program: 3
`gen_query` + 3 `append_notes` ChainOfThought calls, then title recall against gold. That is the
same unit `m = $0.004543` was fitted on (v2 §14), and the same unit gepa's budget counter counts --
except that everything in this module is POST-RUN and OUTSIDE the budget (v2 §8a, §8b).

FIDELITY. The program, retrieval, model and metric are lifted from `scratch/hover_stage1/
stage1_run.py:build_program` + its `metric()`, which is itself byte-identical to the frozen
`hover_probe/necrosis_run.py` reference. A candidate is applied exactly as dspy's own GEPA adapter
applies it (`dspy/teleprompt/gepa/gepa_utils.py:136-143`): `pred.signature.with_instructions(...)`
for every named predictor present in the candidate dict.

THREADS. Per-claim evaluation is independent and the task LM is temp-0, so threading changes wall
clock and nothing else -- the same argument `grade_threehop.py:8-11` makes for the grading pass.
The optimization runs themselves stay `num_threads=1`, identical to Stage 1.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
HOVER_PROBE = os.path.join(REPO, "scratch", "hover_probe")

MODEL = "openai/gpt-4.1-mini"
MAX_TOKENS = 3000
WORKERS = 8
M_PER_CALL = 0.004543  # v2 §14 fitted rate, for projections only; actuals are measured


# --------------------------------------------------------------------------- probe bootstrap
def bootstrap():
    """Import probe with its relative paths resolvable, load the API key, return (dspy, probe)."""
    if HOVER_PROBE not in sys.path:
        sys.path.insert(0, HOVER_PROBE)
    os.chdir(HOVER_PROBE)  # probe resolves bm25s_index/, threehop.jsonl, ../../.env relatively
    import probe  # noqa: PLC0415

    import dspy  # noqa: PLC0415

    probe._load_env()
    return dspy, probe


def build_program(dspy, probe):
    """The Stage-1 HoVer 3-hop program, verbatim (stage1_run.py:66-87)."""

    class HoverMultiHop(dspy.Module):
        def __init__(self):
            super().__init__()
            self.gen_query = dspy.ChainOfThought("claim, notes -> query")
            self.append_notes = dspy.ChainOfThought(
                "claim, notes, context -> new_notes: list[str], titles: list[str]")

        def forward(self, claim):
            notes, per_hop = [], []
            for hop in range(probe.NUM_HOPS):
                q = self.gen_query(claim=claim, notes=notes).query
                ctx = probe.search(q, k=probe.NUM_DOCS)
                ret_titles = [probe.title_of(c) for c in ctx]
                per_hop.append({"hop": hop + 1, "query": q, "retrieved_titles": ret_titles})
                pred = self.append_notes(claim=claim, notes=notes, context=ctx)
                new = pred.new_notes if isinstance(pred.new_notes, list) else [str(pred.new_notes)]
                notes.extend(new)
            all_ret = sorted({t for h in per_hop for t in h["retrieved_titles"]})
            return dspy.Prediction(titles=all_ret, notes=notes, per_hop=per_hop)

    return HoverMultiHop()


def apply_candidate(program, candidate: dict[str, str]):
    """dspy's own candidate application (gepa_utils.py:136-143). Returns a fresh deepcopy."""
    prog = program.deepcopy()
    for name, pred in prog.named_predictors():
        if name in candidate:
            pred.signature = pred.signature.with_instructions(candidate[name])
    return prog


# --------------------------------------------------------------------------- splits
def sha256_file(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def load_split(path: str) -> list[dict]:
    """Read a committed split artifact. Returns its claim records, in committed order."""
    with open(path, "rb") as fh:
        blob = json.load(fh)
    recs = blob["claims"]
    assert recs, f"{path} holds no claims"
    ids = [r["threehop_idx"] for r in recs]
    assert len(set(ids)) == len(ids), f"{path} has duplicate threehop_idx"
    return recs


# --------------------------------------------------------------------------- evaluation
class Meter:
    """Token-derived spend, plus a hard tripwire. Mirrors stage1_run.py:47-64."""

    def __init__(self, lm, probe, cap: float):
        self.lm, self.probe, self.cap = lm, probe, cap
        self.calls = 0
        self._lock = threading.Lock()

    def spend(self) -> float:
        tot = 0.0
        for h in list(self.lm.history):
            u = h.get("usage") or {}
            tot += (u.get("prompt_tokens", 0) * self.probe.PRICE_IN
                    + u.get("completion_tokens", 0) * self.probe.PRICE_OUT)
        return tot

    def tick(self) -> None:
        with self._lock:
            self.calls += 1
        s = self.spend()
        if s > self.cap:
            raise RuntimeError(f"SPEND TRIPWIRE: ${s:.4f} > cap ${self.cap:.2f} — aborting")


def score_candidate(dspy, probe, base_program, candidate: dict[str, str], split: list[dict],
                    lm, meter: Meter, workers: int = WORKERS) -> dict:
    """Evaluate one candidate on one split. Returns per-example scores keyed by threehop_idx.

    Score == title recall, the Stage-1 metric (`stage1_run.py:110-114`). Feedback is not built:
    these evaluations feed an argmax and an endpoint, never a reflection.
    """
    prog = apply_candidate(base_program, candidate)

    def one(rec):
        with dspy.context(lm=lm):
            pred = prog(claim=rec["claim"])
        gold = set(rec["gold"])
        got = set(getattr(pred, "titles", []) or [])
        meter.tick()
        return rec["threehop_idx"], (len(gold & got) / len(gold) if gold else 0.0)

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        pairs = list(ex.map(one, split))
    scores = {str(i): s for i, s in pairs}
    return {
        "n": len(scores),
        "mean": sum(scores.values()) / len(scores),
        "scores": scores,  # per-example vector, per v2 §12 — a mean alone is not recomputable
        "elapsed_s": round(time.time() - t0, 1),
    }


def argmax_lowest_index(means: list[float]) -> tuple[int, list[int]]:
    """v2 §8/§8b tie-break: first maximal element over an ascending range => lowest index wins.

    Written as gepa writes it (`core/result.py:82-88`) rather than as `max(enumerate(...))`, so the
    tie semantics are the same object, not a re-derivation that happens to agree.
    """
    best = max(range(len(means)), key=lambda i: means[i])
    ties = [i for i, v in enumerate(means) if v == means[best]]
    return best, ties


def open_task_lm(dspy):
    """The Stage-1 task LM: temp-0 (dspy default), cache off, so every claim is really evaluated."""
    lm = dspy.LM(MODEL, max_tokens=MAX_TOKENS, cache=False)
    dspy.configure(lm=lm)
    return lm
