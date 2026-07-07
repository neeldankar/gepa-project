"""Pre-flight for the faithful (IFEvalG-verified) baseline — run BEFORE any paid call.

Confirms:
  1. both verifier registries import in ONE process (prints key counts + IFEvalG source);
  2. the faithful train/val splits load from HF;
  3. IFConstraintEvaluator runs over ALL loaded rows with a dummy response and raises 0
     checker exceptions (a raised checker is usually a missing nltk/spaCy resource — the
     error is surfaced, not swallowed);
  4. the structured SI names real IFEvalG constraint ids.

Run from repo root:
    .venv/bin/python scripts/preflight_faithful.py
"""

from __future__ import annotations

from gepa_si.ifbench_eval import (
    IFBENCH_DICT,
    IFEVALG_DICT,
    IFEVALG_SOURCE,
    IFConstraintEvaluator,
)
from gepa_si.ifrlvr_data import load_faithful_splits

DUMMY = "This is a placeholder response with several words, sentences, and bullet points."


def main() -> None:
    print(f"IFEVALG_DICT keys: {len(IFEVALG_DICT)}")
    print(f"IFBENCH_DICT keys: {len(IFBENCH_DICT)}")
    print(f"IFEvalG import source: {IFEVALG_SOURCE}")

    trainset, valset = load_faithful_splits()
    rows = trainset + valset
    print(f"\nLoaded faithful splits: train={len(trainset)} val={len(valset)}")

    ev = IFConstraintEvaluator()
    exceptions = 0
    sample = None
    for item in rows:
        try:
            res = ev(item, DUMMY)
            if sample is None and item["instruction_id_list"]:
                sample = res
        except Exception as e:
            exceptions += 1
            print(f"  EXC on {item['instruction_id_list']}: {e}")

    print(f"\nEvaluated {len(rows)} rows; checker exceptions: {exceptions}")
    if sample is not None:
        print("\n--- sample IFEvalG SI feedback ---")
        print(sample.feedback)
        print("objective_scores:", sample.objective_scores)

    assert exceptions == 0, f"{exceptions} checker exceptions — fix the resource before running"
    print("\nPRE-FLIGHT OK")


if __name__ == "__main__":
    main()
