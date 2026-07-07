"""Load + split IFBench examples into gepa DefaultAdapter items.

DEV SIMPLIFICATION (intentional): train/val are both split from the LOCAL file
`../IFBench/data/IFBench_test.jsonl`. This is NOT the paper's generalization protocol
(train on IF-RLVR constraints from HF `allenai/IF_multi_constraints_upto5`, test on
IFBench OOD constraints). This split is for pipeline validation + SI inspection only;
faithful train/test data sourcing is a separate later task.
"""

from __future__ import annotations

import json
import os
import random

_IFBENCH_JSONL = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "IFBench", "data", "IFBench_test.jsonl")
)

SEED = 0
N_TRAIN = 40  # D_feedback
N_VAL = 30    # D_pareto


def _to_item(example: dict) -> dict:
    """Convert one IFBench example to a DefaultAdapter item.

    DefaultAdapter only reads `input` (the user message); the extra keys ride along
    in `data` and are read by IFBenchEvaluator. `answer` is unused (set to "").
    """
    return {
        "input": example["prompt"],
        "additional_context": {},
        "answer": "",
        "instruction_id_list": example["instruction_id_list"],
        "kwargs": example["kwargs"],
    }


def load_splits(
    n_train: int = N_TRAIN, n_val: int = N_VAL, seed: int = SEED
) -> tuple[list[dict], list[dict]]:
    """Return (trainset, valset) as lists of DefaultAdapter items, deterministically."""
    with open(_IFBENCH_JSONL, encoding="utf-8") as fh:
        examples = [json.loads(line) for line in fh if line.strip()]

    items = [_to_item(e) for e in examples]
    random.Random(seed).shuffle(items)

    if n_train + n_val > len(items):
        raise ValueError(
            f"requested {n_train}+{n_val} > {len(items)} available IFBench examples"
        )
    trainset = items[:n_train]
    valset = items[n_train : n_train + n_val]
    return trainset, valset


if __name__ == "__main__":
    tr, va = load_splits()
    print(f"train={len(tr)} val={len(va)} (from {_IFBENCH_JSONL})")
    print("sample input:", tr[0]["input"][:120])
    print("sample constraints:", tr[0]["instruction_id_list"])
