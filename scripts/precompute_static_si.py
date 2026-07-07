"""Static SI precompute over D_feedback (offline-screen corpus, part 1).

For every example in the shared trainset (D_feedback), capture the side-information (SI)
it produces under the FIXED reference system prompt — the same seed prompt the baselines
start from. This is data capture, NOT scoring (no novelty/actionability here).

We reuse gepa's DefaultAdapter rather than re-rolling the LM call, so the captured
`si_feedback` is the IDENTICAL field gepa would turn into the "Feedback" SI in
`on_reflective_dataset_built` (make_reflective_dataset reads trajectory["feedback"]).

`example_id` is the positional index into the trainset (0..N-1). gepa's ListDataLoader
assigns these same ids, and they are exactly what the SIEventLogger records as
`minibatch_ids` for the baselines — so the scorer layer can join static <-> faithful SI
per example.

Run from repo root (key loaded from .env):
    .venv/bin/python scripts/precompute_static_si.py
"""

from __future__ import annotations

import json
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

from gepa.adapters.default_adapter.default_adapter import DefaultAdapter  # noqa: E402

from gepa_si.ifbench_eval import IFConstraintEvaluator  # noqa: E402
from gepa_si.ifrlvr_data import load_faithful_splits  # noqa: E402

TASK_LM = "openai/gpt-4.1-mini"
OUT_PATH = "logs/static_si_precompute.jsonl"

# Same reference / seed prompt the baselines start from.
SEED_CANDIDATE = {
    "system_prompt": (
        "You are a helpful assistant. Read the user's request carefully and follow "
        "every instruction and formatting constraint exactly."
    )
}


def main() -> None:
    trainset, _valset = load_faithful_splits()  # D_feedback = the shared trainset
    print(f"D_feedback (trainset) size: {len(trainset)}")

    adapter = DefaultAdapter(model=TASK_LM, evaluator=IFConstraintEvaluator())
    print(f"Running seed prompt over D_feedback with {TASK_LM} (capture_traces=True)...")
    out = adapter.evaluate(trainset, SEED_CANDIDATE, capture_traces=True)

    trajectories = out.trajectories
    assert trajectories is not None and len(trajectories) == len(trainset)

    os.makedirs("logs", exist_ok=True)
    n_empty = 0
    with open(OUT_PATH, "w", encoding="utf-8") as fh:  # one clean file (overwrites)
        for i, traj in enumerate(trajectories):
            si_feedback = traj["feedback"]
            if not (si_feedback and si_feedback.strip()):
                n_empty += 1
            rec = {
                "example_id": i,  # positional index == baseline minibatch_ids
                "input": trainset[i]["input"],
                "response": traj["full_assistant_response"],
                "si_feedback": si_feedback,
                "score": out.scores[i],
                "objective_scores": out.objective_scores[i] if out.objective_scores else None,
                "registry": trainset[i].get("registry", "ifbench"),
            }
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # -- report ------------------------------------------------------------
    task_cost = getattr(adapter._lm, "total_cost", None)
    tokens_in = getattr(adapter._lm, "total_tokens_in", None)
    tokens_out = getattr(adapter._lm, "total_tokens_out", None)
    mean_score = sum(out.scores) / len(out.scores) if out.scores else 0.0
    print(f"\nWrote {len(trajectories)} records to {OUT_PATH}")
    print(f"  empty si_feedback: {n_empty} (want 0)")
    print(f"  mean seed score over D_feedback: {mean_score:.3f}")
    print(f"  task LM calls: {len(trajectories)} | tokens in/out: {tokens_in}/{tokens_out}")
    if task_cost is not None:
        print(f"  task LM cost: ${task_cost:.4f}")

    print("\n--- sample record (example_id=0) ---")
    print(f"  registry: {trainset[0].get('registry')}")
    print(f"  si_feedback:\n{trajectories[0]['feedback']}")

    assert n_empty == 0, f"{n_empty} examples had empty si_feedback"
    print("\nSTATIC PRECOMPUTE OK")


if __name__ == "__main__":
    main()
