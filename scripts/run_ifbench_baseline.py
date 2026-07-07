"""First IFBench baseline run — real benchmark, structured SI.

Runs gepa's reflective optimization on the real IFBench benchmark with the
SIEventLogger attached, evolving ONE system prompt. IFBench plugs in as a custom
evaluator (IFBenchEvaluator) passed via optimize(evaluator=...) — gepa's built-in
DefaultAdapter handles the LM calls, so the logger wiring is unchanged.

DEV SIMPLIFICATION (intentional): train/val are split from the LOCAL
../IFBench/data/IFBench_test.jsonl using IFBench's own verifiers. This is NOT the
paper's generalization protocol (train on IF-RLVR HF constraints, test on IFBench OOD).
This run is pipeline-validation + SI inspection only, not a results run. The 2-stage
faithfulness agent (generate_response -> ensure_correct_response) is a TODO, not built here.

Run from repo root with the venv:
    .venv/bin/python scripts/run_ifbench_baseline.py
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

load_dotenv()

_key = os.environ.get("OPENAI_API_KEY", "").strip()
if not _key or _key == "REPLACE_ME":
    sys.exit(
        "ERROR: OPENAI_API_KEY is not set. Paste your real key into the .env file "
        "in the repo root, then re-run. The key is loaded from .env and never hardcoded."
    )

from gepa import optimize  # noqa: E402

from gepa_si.ifbench_data import load_splits  # noqa: E402
from gepa_si.ifbench_eval import IFBenchEvaluator  # noqa: E402
from gepa_si.si_event_logger import SIEventLogger  # noqa: E402

SEED_CANDIDATE = {
    "system_prompt": (
        "You are a helpful assistant. Read the user's request carefully and follow "
        "every instruction and formatting constraint exactly."
    )
}


def main() -> None:
    trainset, valset = load_splits()
    print(f"Loaded IFBench: train={len(trainset)} val={len(valset)}")

    logger = SIEventLogger("logs/ifbench_baseline_001.jsonl", run_id="ifbench_baseline_001")
    try:
        optimize(
            seed_candidate=SEED_CANDIDATE,
            trainset=trainset,
            valset=valset,
            task_lm="openai/gpt-4.1-mini",
            reflection_lm="openai/gpt-4.1",
            evaluator=IFBenchEvaluator(),
            reflection_minibatch_size=3,
            max_metric_calls=150,
            display_progress_bar=True,
            callbacks=[logger],
        )
    finally:
        logger.close()
    print("\nIFBench baseline complete. Events written to logs/ifbench_baseline_001.jsonl")


if __name__ == "__main__":
    main()
