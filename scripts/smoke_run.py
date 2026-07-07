"""Plumbing smoke run: wire SIEventLogger into a real gepa optimize() call.

Runs gepa's real reflective-optimization loop on a trivial no-retrieval
"capital of X" task with the SIEventLogger attached, proving the logger receives
correct events from a LIVE loop making real OpenAI calls.

The task is rigged to FAIL on the seed prompt so reflection actually fires:
each gold answer is wrapped in a § sentinel the model won't produce unprompted,
paired with a deliberately weak seed. The default ContainsAnswerEvaluator scores
by verbatim substring containment, so "Paris" != "§Paris§" until reflection
teaches the prompt to emit the sentinel.

Run from repo root with the venv:
    .venv/bin/python scripts/smoke_run.py
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

load_dotenv()

_key = os.environ.get("OPENAI_API_KEY", "").strip()
if not _key or _key in ("REPLACE_ME", ""):
    sys.exit(
        "ERROR: OPENAI_API_KEY is not set.\n"
        "Paste your real key into the .env file in the repo root "
        "(OPENAI_API_KEY=sk-...), then re-run. The key is loaded from .env "
        "via python-dotenv and is never hardcoded."
    )

from gepa import optimize  # noqa: E402  (import after env load is intentional)

from gepa_si.si_event_logger import SIEventLogger  # noqa: E402

# -- tiny no-retrieval dataset, rigged to fail the seed --------------------
# answer wrapped in § sentinels the model won't emit unprompted -> seed fails
# -> reflection fires -> prompt learns to wrap the capital in §...§.
_CAPITALS = [
    ("France", "Paris"),
    ("Japan", "Tokyo"),
    ("Canada", "Ottawa"),
    ("Brazil", "Brasilia"),
    ("Egypt", "Cairo"),
    ("Norway", "Oslo"),
    ("Kenya", "Nairobi"),
    ("Peru", "Lima"),
    ("Greece", "Athens"),
    ("Thailand", "Bangkok"),
    ("Portugal", "Lisbon"),
    ("Hungary", "Budapest"),
]


def _item(country: str, capital: str) -> dict:
    return {
        "input": f"What is the capital of {country}?",
        "additional_context": {},
        "answer": f"§{capital}§",  # sentinel-wrapped gold string
    }


_dataset = [_item(c, cap) for c, cap in _CAPITALS]
trainset = _dataset[:8]
valset = _dataset[8:]  # 4 items

SEED = {"system_prompt": "Answer the question."}  # deliberately weak


def main() -> None:
    logger = SIEventLogger("logs/smoke_001.jsonl", run_id="smoke_001")
    try:
        optimize(
            seed_candidate=SEED,
            trainset=trainset,
            valset=valset,
            task_lm="openai/gpt-4.1-mini",
            reflection_lm="openai/gpt-4.1",
            reflection_minibatch_size=3,
            max_metric_calls=60,
            display_progress_bar=True,
            callbacks=[logger],
        )
    finally:
        logger.close()
    print("\nSmoke run complete. Events written to logs/smoke_001.jsonl")


if __name__ == "__main__":
    main()
