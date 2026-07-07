"""Held-out IFBench OOD test split loader (Phase-2 primary-endpoint data).

The paper-faithful generalization TEST side: optimize on the IFEvalG "seen" split
(ifrlvr_data), then measure the best program on IFBench OOD constraints. Items are tagged
`registry="ifbench"` so IFConstraintEvaluator picks the OOD checker registry (the pristine
sibling clone at ../IFBench). Source = HF `allenai/if_bench_test` (300 examples, cached).
"""

from __future__ import annotations

from datasets import load_dataset

HF_OOD = "allenai/if_bench_test"


def load_ood_testset() -> list[dict]:
    """300 OOD test items as DefaultAdapter dicts (registry='ifbench')."""
    ds = load_dataset(HF_OOD, split="train")
    items = []
    for row in ds:
        items.append({
            "input": row["prompt"],
            "additional_context": {},
            "answer": "",
            "instruction_id_list": list(row["instruction_id_list"]),
            "kwargs": list(row["kwargs"]),
            "registry": "ifbench",
        })
    return items


if __name__ == "__main__":
    items = load_ood_testset()
    print(f"OOD testset: {len(items)} items (registry=ifbench)")
    print("sample input:", items[0]["input"][:100])
    print("sample constraints:", items[0]["instruction_id_list"])
