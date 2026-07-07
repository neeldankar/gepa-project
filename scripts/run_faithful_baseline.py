"""Faithful baseline validation run — IF-RLVR train (IFEvalG-verified).

Runs gepa's reflective optimization on the paper-faithful TRAIN side: examples sampled
from HF `allenai/IF_multi_constraints_upto5` and scored with the IFEvalG verifier
registry (via IFConstraintEvaluator). Evolves ONE system prompt; SIEventLogger attached.

Scope: ONE small validation run to confirm the faithful data + dual-registry pipeline
works end to end. NOT the 5-run screen; NOT the IFBench OOD test set (that's live-confirm,
a later task); NOT the 2-stage faithfulness agent.

Log-file hygiene (fixes the cross-run append issue from the IFBench baseline): one run =
one fresh file. The log path is unique per run (run_id carries a timestamp passed via the
RUN_ID env var) and we REFUSE to write to an existing file.

Run from repo root:
    RUN_ID=faithful_$(date +%Y%m%d_%H%M%S) .venv/bin/python scripts/run_faithful_baseline.py
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

from gepa_si.ifbench_eval import IFConstraintEvaluator  # noqa: E402
from gepa_si.ifrlvr_data import load_faithful_splits  # noqa: E402
from gepa_si.si_event_logger import SIEventLogger  # noqa: E402

RUN_ID = os.environ.get("RUN_ID", "faithful_baseline_001")
LOG_PATH = f"logs/{RUN_ID}.jsonl"

SEED_CANDIDATE = {
    "system_prompt": (
        "You are a helpful assistant. Read the user's request carefully and follow "
        "every instruction and formatting constraint exactly."
    )
}


def main() -> None:
    # One run = one fresh file: refuse to append to an existing log.
    if os.path.exists(LOG_PATH):
        sys.exit(
            f"ERROR: log file already exists: {LOG_PATH}\n"
            "Use a unique RUN_ID (e.g. RUN_ID=faithful_$(date +%Y%m%d_%H%M%S)) so each "
            "run writes one clean file."
        )

    trainset, valset = load_faithful_splits()
    print(f"Loaded faithful splits: train={len(trainset)} val={len(valset)}")
    print(f"Logging to {LOG_PATH} (run_id={RUN_ID})")

    logger = SIEventLogger(LOG_PATH, run_id=RUN_ID)
    try:
        optimize(
            seed_candidate=SEED_CANDIDATE,
            trainset=trainset,
            valset=valset,
            task_lm="openai/gpt-4.1-mini",
            reflection_lm="openai/gpt-4.1",
            evaluator=IFConstraintEvaluator(),
            reflection_minibatch_size=3,
            max_metric_calls=150,
            display_progress_bar=True,
            callbacks=[logger],
        )
    finally:
        logger.close()
    print(f"\nFaithful baseline complete. Events written to {LOG_PATH}")


if __name__ == "__main__":
    main()
