"""Faithful train/val loader: IF-RLVR constraints, IFEvalG-verified.

This is the paper-faithful generalization protocol's TRAIN side: examples are sampled
from the HF IF-RLVR set `allenai/IF_multi_constraints_upto5` (the "seen" constraints,
drawn from IFEval + IFBench-train) and scored with the IFEvalG verifier registry. The
held-out TEST side (IFBench OOD constraints) is a separate later task — this module does
NOT touch IFBench data.

Items are tagged `registry="ifevalg"` so `IFConstraintEvaluator` picks the IFEvalG
checkers for them.

Constraint parsing mirrors open-instruct's `IFEvalVerifier` (ground_truth_utils.py):
the `ground_truth` field is a stringified list whose first element is a dict (possibly
itself a JSON string) holding `instruction_id` and `kwargs`.
"""

from __future__ import annotations

import ast
import json

from datasets import load_dataset

HF_DATASET = "allenai/IF_multi_constraints_upto5"
SEED = 0
# Shared corpus split for the offline-screen baselines: ALL runs reuse this one split
# (split seed fixed) so static SI joins across them and leave-one-run-out CV is meaningful.
# The 5 eventual baselines differ ONLY by optimize(seed=...), never by the data split.
# Paper's GEPA-IFBench uses 300 val; we use 150 here to control dev cost — the ΔU ranking
# signal is fine at 150, and 300 is reserved for the live-confirm. Tunable knob.
N_TRAIN = 150
N_VAL = 150


def _parse_constraints(ground_truth: str) -> tuple[list[str], list]:
    """(instruction_id_list, kwargs_list) from a row's ground_truth (IFEvalVerifier recipe)."""
    parsed = ast.literal_eval(ground_truth)  # a list
    cd = parsed[0]
    if isinstance(cd, str):
        cd = json.loads(cd)
    return cd["instruction_id"], cd["kwargs"]


def _user_content(messages: list[dict]) -> str:
    """The user-role message content is the task prompt."""
    return next(m["content"] for m in messages if m["role"] == "user")


def _to_item(row: dict) -> dict:
    instruction_id_list, kwargs_list = _parse_constraints(row["ground_truth"])
    return {
        "input": _user_content(row["messages"]),
        "additional_context": {},
        "answer": "",
        "instruction_id_list": instruction_id_list,
        "kwargs": kwargs_list,
        "registry": "ifevalg",
    }


def load_faithful_splits(
    n_train: int = N_TRAIN, n_val: int = N_VAL, seed: int = SEED
) -> tuple[list[dict], list[dict]]:
    """Return (trainset, valset) as disjoint lists of DefaultAdapter items, deterministically."""
    ds = load_dataset(HF_DATASET, split="train")
    ds = ds.shuffle(seed=seed)
    selected = ds.select(range(n_train + n_val))
    items = [_to_item(row) for row in selected]
    return items[:n_train], items[n_train : n_train + n_val]


if __name__ == "__main__":
    tr, va = load_faithful_splits()
    print(f"train={len(tr)} val={len(va)} (from {HF_DATASET})")
    print("sample input:", tr[0]["input"][:120])
    print("sample constraints:", tr[0]["instruction_id_list"])
    print("sample kwargs:", tr[0]["kwargs"])
