"""Construct the §8a test split. GATED: APPROVED-testsplit. LIVE SPEND (~$1.33).

WHY THIS COSTS MONEY, when the brief expected $0. Reproducing `stage1_run.py:131-141` exactly:
245 graded records -> 123 imperfect (recall<1.0) -> 110 consumed by Stage 1 -> **13 remain, and
all 13 have recall == 0.0**. 13 < 100, so §8a's own `N<100 => STOP-and-flag` rule fires. The
remainder is also the hardest tier only: the sort key `(-recall, claim)` consumed all 70 claims at
recall 2/3 and all 35 at 1/3, then 5 of the 18 zeros. A split drawn from it would be maximally
unrepresentative.

So the test pool is FRESHLY GRADED claims from `threehop.jsonl` beyond the graded slice
(`threehop_idx >= 295`; the graded file spans 50-294 contiguous, 1620 claims remain ungraded).
Grading runs the same 3-hop program via `grade_threehop.py`'s procedure, which calls
`dspy.ChainOfThought` on gpt-4.1-mini (`grade_threehop.py:44`) -- hence live spend.

  imperfect rate  = 123/245 = 0.502
  to reach N=150  ~ 299 claims graded
  measured rate   = $1.0942 / 245 = $0.00447 per claim   (graded_summary.json)
  estimate        ~ $1.33

Disjointness from the Stage-1 110 is automatic (new indices). The split is committed as JSON with
its sha256 BEFORE any test evaluation exists (§8a).

    dry run (no spend, prints the plan):
        analysis/state_dep/.venv-armT/bin/python analysis/state_dep/build_test_split.py --dry-run
    live (requires the gate):
        scratch/hover_probe/.venv/bin/python analysis/state_dep/build_test_split.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

from gates import require  # noqa: E402

GRADED = os.path.join(REPO, "scratch", "hover_stage1", "graded_records.jsonl")
THREEHOP = os.path.join(REPO, "scratch", "hover_probe", "threehop.jsonl")
OUT_SPLIT = os.path.join(HERE, "test_split.json")
OUT_GRADED = os.path.join(HERE, "test_pool_graded.jsonl")

SPLIT_SEED = 20260709  # §8a, verbatim
TARGET_N = 150
MIN_N = 100  # §8a: N < 100 is a STOP-and-flag
IMPERFECT_RATE = 123 / 245
START_IDX = 295  # first ungraded threehop index
SPEND_CAP = 3.00  # hard cap; the estimate is ~$1.33


def stage1_consumed() -> set[int]:
    """Reproduce stage1_run.py:131-141 exactly and return the consumed threehop_idx set."""
    recs = [json.loads(line) for line in open(GRADED, "rb")]
    imperfect = [r for r in recs if r["recall"] < 1.0]
    imperfect.sort(key=lambda r: (-r["recall"], r["claim"]))
    need = 100 + 10
    chosen = imperfect[:need] if len(imperfect) >= need else (imperfect * ((need // len(imperfect)) + 1))[:need]
    return {r["threehop_idx"] for r in chosen}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    consumed = stage1_consumed()
    n_to_grade = int(round(TARGET_N / IMPERFECT_RATE))
    est = n_to_grade * 0.00447

    print("=== §8a test-split construction ===")
    print(f"  Stage-1 consumed         : {len(consumed)} threehop_idx (disjoint by construction)")
    print(f"  already-graded remainder : 13 imperfect, all recall=0.0  -> N<100, STOP fired")
    print(f"  fresh pool               : threehop_idx >= {START_IDX}")
    print(f"  target N                 : {TARGET_N}   (min {MIN_N})")
    print(f"  claims to grade          : ~{n_to_grade}  (imperfect rate {IMPERFECT_RATE:.3f})")
    print(f"  estimated spend          : ~${est:.2f}   (cap ${SPEND_CAP:.2f})")
    print(f"  split seed               : random.Random({SPLIT_SEED})")

    if args.dry_run:
        print("\n[dry-run] no gate check, no grading, no spend. Nothing written.")
        return 0

    gate = require("APPROVED-testsplit")

    # ---- LIVE: grade fresh claims with the SAME procedure as grade_threehop.py -------------
    # Deliberately reuses probe's program/retrieval/model so "imperfect" means imperfect for the
    # exact program GEPA optimizes. Nothing below runs without the gate above.
    raise SystemExit(
        "\nNOT IMPLEMENTED BEYOND THE GATE.\n"
        "Grading is a near-verbatim re-run of scratch/hover_stage1/grade_threehop.py with\n"
        "  START = 295, TARGET_IMPERFECT = 150, CAP = 3.00, and output to test_pool_graded.jsonl.\n"
        "That file is FROZEN (do-not list), so the runner must copy its logic rather than import\n"
        "and mutate it. Wire it at the gate, under Neel's eye, not the night before.\n"
        f"Gate verified: {gate['sha256'][:16]}...\n"
    )


if __name__ == "__main__":
    raise SystemExit(main())
