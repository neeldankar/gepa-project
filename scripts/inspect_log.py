"""Inspect a smoke-run JSONL log and summarize what the SIEventLogger captured.

Run from repo root with the venv:
    .venv/bin/python scripts/inspect_log.py [path]   # default: logs/smoke_001.jsonl
"""

from __future__ import annotations

import json
import sys
from collections import Counter

PATH = sys.argv[1] if len(sys.argv) > 1 else "logs/smoke_001.jsonl"


def _load(path: str) -> list[dict]:
    try:
        with open(path, encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]
    except FileNotFoundError:
        sys.exit(f"ERROR: log file not found: {path}\nRun scripts/smoke_run.py first.")


def main() -> None:
    records = _load(PATH)
    counts = Counter(r.get("event") for r in records)

    print(f"=== {PATH} : {len(records)} records ===\n")
    print("event counts:")
    for event, n in counts.most_common():
        print(f"  {event:28s} {n}")

    # -- sample reflective_dataset_built (the SI) --------------------------
    refl = next((r for r in records if r.get("event") == "reflective_dataset_built"), None)
    print("\n--- sample reflective_dataset_built (SI) ---")
    if refl is None:
        print("  (none captured)")
    else:
        dataset = refl.get("dataset") or {}
        # dataset is keyed component -> list[per-example dict]
        comp = next(iter(dataset), None)
        examples = dataset.get(comp, []) if comp else []
        ex = examples[0] if examples else {}
        print(f"  iteration={refl.get('iteration')} candidate_idx={refl.get('candidate_idx')} "
              f"components={refl.get('components')}")
        print(f"  Inputs:            {ex.get('Inputs')}")
        print(f"  Generated Outputs: {ex.get('Generated Outputs')}")
        print(f"  Feedback:          {ex.get('Feedback')}")

    # -- non-seed valset_evaluated (a child program) ----------------------
    child = next(
        (r for r in records
         if r.get("event") == "valset_evaluated" and r.get("parent_ids")),
        None,
    )
    print("\n--- non-seed valset_evaluated (child program) ---")
    if child is None:
        print("  (none with non-empty parent_ids captured)")
    else:
        sbv = child.get("scores_by_val_id")
        print(f"  iteration={child.get('iteration')} candidate_idx={child.get('candidate_idx')}")
        print(f"  parent_ids={child.get('parent_ids')}  average_score={child.get('average_score')}")
        print(f"  scores_by_val_id present: {sbv is not None}  -> {sbv}")

    # -- pass / warn summary ----------------------------------------------
    meta_n = counts.get("meta", 0)
    refl_n = counts.get("reflective_dataset_built", 0)
    print("\n=== summary ===")
    warn = False
    if meta_n != 1:
        print(f"  WARN: expected exactly 1 meta record, found {meta_n}")
        warn = True
    if refl_n < 1:
        print(f"  WARN: expected >= 1 reflective_dataset_built, found {refl_n}")
        warn = True
    if not warn:
        print(f"  PASS: meta == 1, reflective_dataset_built == {refl_n} (>= 1)")


if __name__ == "__main__":
    main()
