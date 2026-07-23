"""§11-0 determinism control for the dose. GATED: APPROVED-dose for the live half (~$0.41).

The control, verbatim from v2 §11-0:

    A seeded sample (random.Random(20260709)) of 30 events: re-execute the matched B_e and
    byte-compare each re-rendered feedback block against the persisted reflect_in_SWAP.txt block.
    30/30 byte-exact -> proceed to the 3 unmatched re-derivations. Any failure -> STOP.

Why it exists: the dose needs feedback texts that do not exist on disk for any of the 243 events
(notes/FREEZE.md C1). They must be re-derived by re-executing the parent. `hover_swap_run.py:160`
builds the task LM with no `temperature` argument, so dspy's default 0.0 applies, and `cache=False`
means nothing is replayed. Temp-0 is NOT a bitwise contract at the API level. This control converts
that assumption into a measurement, using the 3 texts per event that DO exist as a free oracle.

TWO PHASES.

  --freeze-expected   ($0, runs tonight, no gate)
      Draw the 30 events, parse the 3 B_e feedback blocks out of each reflect_in_SWAP.txt, and
      commit their sha256s to dose_control_expected.json. Freezing the expected side BEFORE any
      re-execution exists is what makes the control unfudgeable.

  --run               (live, requires APPROVED-dose)
      Re-execute the parent on those events' B_e, re-render via the identical
      make_reflective_dataset path, and compare against the frozen hashes. 30/30 or STOP.
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
SCREEN = os.path.join(REPO, "analysis", "hover_screen")
PAIRS = os.path.join(REPO, "analysis", "ablation", "hover_swap", "pairs")
EXPECTED = os.path.join(HERE, "dose_control_expected.json")

sys.path.insert(0, HERE)
sys.path.insert(0, SCREEN)

CONTROL_SEED = 20260709  # §11-0, verbatim
N_CONTROL = 30

# The control samples from all 243 pair dirs, NOT from the dose's 235-event set (v2.1 §20-2). Those
# are different questions: the control asks "does the temp-0 task LM reproduce in-run bytes", which
# is true or false of every persisted event including the ordinal-0 ones; the dose asks "how much
# selection room is there", which is undefined without a k=3 archive. Do not "fix" this to 235 --
# the expected side was frozen over 243 on 2026-07-09, before any re-execution existed, and
# re-drawing the sample now is exactly the tampering the control is designed to preclude.


def freeze_expected() -> int:
    from screen_part0 import parse_si  # import-clean

    pids = sorted(os.listdir(PAIRS))
    assert len(pids) == 243, len(pids)
    rng = random.Random(CONTROL_SEED)
    sample = sorted(rng.sample(pids, N_CONTROL))

    out = {
        "control_seed": CONTROL_SEED,
        "n_control": N_CONTROL,
        "sample_rule": "random.Random(20260709).sample(sorted(os.listdir(pairs)), 30)",
        "source_file": "reflect_in_SWAP.txt (the 3 failure-matched B_e feedback blocks)",
        "events": {},
    }
    for pid in sample:
        raw = open(os.path.join(PAIRS, pid, "reflect_in_SWAP.txt"), encoding="utf-8").read()
        blocks = parse_si(raw, pid)
        assert len(blocks) == 3, (pid, len(blocks))
        meta = json.load(open(os.path.join(PAIRS, pid, "meta.json")))
        out["events"][pid] = {
            "B_e_pos": meta["B_e_pos"],
            "feedback_sha256": [
                hashlib.sha256(b["Feedback"].encode()).hexdigest() for b in blocks
            ],
            "feedback_bytes": [len(b["Feedback"].encode()) for b in blocks],
        }

    with open(EXPECTED, "w") as fh:
        json.dump(out, fh, indent=2)

    n_hash = sum(len(v["feedback_sha256"]) for v in out["events"].values())
    print(f"=== dose determinism control: expected side FROZEN ===")
    print(f"  events sampled     : {len(sample)}  (seed {CONTROL_SEED})")
    print(f"  feedback blocks    : {n_hash}  (3 per event)")
    print(f"  wrote              : {EXPECTED}")
    print(f"  file sha256        : {hashlib.sha256(open(EXPECTED,'rb').read()).hexdigest()}")
    print("\n  First 3 events:")
    for pid in sample[:3]:
        e = out["events"][pid]
        print(f"    {pid}: B_e_pos={e['B_e_pos']} bytes={e['feedback_bytes']}")
        for h in e["feedback_sha256"]:
            print(f"      {h}")
    print("\n$0. No API calls. The expected side is now immutable and committed.")
    return 0


def run_live() -> int:
    from gates import require

    gate = require("APPROVED-dose")
    if not os.path.exists(EXPECTED):
        print(f"missing {EXPECTED}; run --freeze-expected first (it is $0)")
        return 1
    exp = json.load(open(EXPECTED))
    raise SystemExit(
        "\nNOT IMPLEMENTED BEYOND THE GATE.\n"
        f"Expected side is frozen for {len(exp['events'])} events "
        f"({sum(len(v['feedback_sha256']) for v in exp['events'].values())} blocks).\n"
        "The live half must, per v2 §11-0:\n"
        "  1. rebuild the parent candidate for each sampled event (meta.json parent_candidate_idx\n"
        "     -> the Stage-1 program_candidates entry),\n"
        "  2. adapter.evaluate(B_e, parent, capture_traces=True) with the temp-0 task LM,\n"
        "  3. adapter.make_reflective_dataset(...) via the identical path as hover_swap_run.py:201,\n"
        "  4. sha256 each rendered Feedback block and compare against dose_control_expected.json,\n"
        "  5. 30/30 byte-exact -> PROCEED; any mismatch -> STOP, and Neel decides.\n"
        "     Pre-registered fallback on failure: DROP the dose (review option 3).\n"
        "     NEVER the biased 3-candidate shrink: B_idx = combo was SELECTED to match the\n"
        "     parent's score profile on A_e, so it is not a uniform 3-subset of the 6.\n"
        f"Gate verified: {gate['sha256'][:16]}...\n"
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--freeze-expected", action="store_true")
    ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    if a.freeze_expected:
        raise SystemExit(freeze_expected())
    if a.run:
        raise SystemExit(run_live())
    ap.error("pick --freeze-expected ($0) or --run (gated)")
